"""Tiny, dependency-light SVG authoring kit used by every figure in this study pack.

Why hand-written SVG instead of Matplotlib?
  * Text is measured with the *actual* embedded font metrics, so labels never get clipped.
  * The canvas (viewBox) is computed from everything that was drawn, so nothing can run past
    the border of the image.
  * The used glyphs of each font are subset and embedded (WOFF2, base64). The figure renders
    identically in VS Code, GitHub, a browser, or any <img> tag - no font fallbacks.
  * A small script is embedded that turns the file into a pan/zoom viewer when the .svg is
    opened directly in a browser. Inside an <img> (Markdown previews) scripts never run, so the
    figure stays a clean static image there.

Only fontTools (+ brotli for WOFF2) is required.
"""
from __future__ import annotations

import base64
import io
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape

from fontTools.ttLib import TTFont
from fontTools import subset as ft_subset

from theme import T, FONT_DIR

# --------------------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------------------

FACES = {
    # key: (css family, weight, style, file)
    ("mono", 400, "normal"): ("JetBrains Mono", "jetbrains-mono-full-400-normal.woff2"),
    ("mono", 600, "normal"): ("JetBrains Mono", "jetbrains-mono-full-600-normal.woff2"),
    ("mono", 700, "normal"): ("JetBrains Mono", "jetbrains-mono-full-700-normal.woff2"),
    ("mono", 400, "italic"): ("JetBrains Mono", "jetbrains-mono-full-400-italic.woff2"),
    ("sans", 400, "normal"): ("IBM Plex Sans", "ibm-plex-sans-full-400-normal.woff2"),
    ("sans", 500, "normal"): ("IBM Plex Sans", "ibm-plex-sans-full-500-normal.woff2"),
    ("sans", 600, "normal"): ("IBM Plex Sans", "ibm-plex-sans-full-600-normal.woff2"),
    ("sans", 400, "italic"): ("IBM Plex Sans", "ibm-plex-sans-full-400-italic.woff2"),
}
FALLBACK = {
    "mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace",
    "sans": "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
}


class _Face:
    def __init__(self, path: Path):
        self.path = path
        self.font = TTFont(str(path))
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"].metrics
        hhea = self.font["hhea"]
        self.ascent = hhea.ascent / self.upm
        self.descent = -hhea.descent / self.upm

    def width(self, s: str, size: float) -> float:
        total = 0
        for ch in s:
            g = self.cmap.get(ord(ch))
            if g is None:
                raise ValueError(f"glyph {ch!r} (U+{ord(ch):04X}) missing from {self.path.name}: {s!r}")
            total += self.hmtx[g][0]
        return total * size / self.upm


_face_cache: dict = {}


def face(family: str, weight: int, style: str = "normal") -> _Face:
    key = (family, weight, style)
    if key not in FACES:
        raise KeyError(f"no font face {key}")
    if key not in _face_cache:
        _face_cache[key] = _Face(FONT_DIR / FACES[key][1])
    return _face_cache[key]


def text_width(s: str, size: float, family: str = "sans", weight: int = 400, style: str = "normal") -> float:
    return face(family, weight, style).width(s, size)


def wrap(s: str, max_w: float, size: float, family="sans", weight=400, style="normal") -> list[str]:
    """Greedy word wrap using real font metrics."""
    out: list[str] = []
    for para in s.split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            cand = w if not line else line + " " + w
            if text_width(cand, size, family, weight, style) <= max_w or not line:
                line = cand
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


# --------------------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------------------

@dataclass
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    def union(self, o: "BBox") -> "BBox":
        return BBox(min(self.x0, o.x0), min(self.y0, o.y0), max(self.x1, o.x1), max(self.y1, o.y1))

    def pad(self, p: float) -> "BBox":
        return BBox(self.x0 - p, self.y0 - p, self.x1 + p, self.y1 + p)

    def intersects(self, o: "BBox", tol: float = 0.0) -> bool:
        return not (self.x1 <= o.x0 + tol or o.x1 <= self.x0 + tol or self.y1 <= o.y0 + tol or o.y1 <= self.y0 + tol)

    # anchor helpers (frac 0..1 along the edge)
    def top(self, f=0.5):
        return (self.x0 + f * self.w, self.y0)

    def bottom(self, f=0.5):
        return (self.x0 + f * self.w, self.y1)

    def left(self, f=0.5):
        return (self.x0, self.y0 + f * self.h)

    def right(self, f=0.5):
        return (self.x1, self.y0 + f * self.h)


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pts_to_path(pts: Sequence[tuple[float, float]], radius: float = 0.0) -> str:
    """Polyline path with optional rounded corners (for orthogonal connectors)."""
    if len(pts) < 2:
        return ""
    if radius <= 0 or len(pts) == 2:
        return "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
    d = [f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"]
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1 = math.hypot(x1 - x0, y1 - y0)
        l2 = math.hypot(x2 - x1, y2 - y1)
        r = min(radius, l1 / 2, l2 / 2)
        if r < 0.5:
            d.append(f"L{fmt(x1)} {fmt(y1)}")
            continue
        ax, ay = x1 - (x1 - x0) / l1 * r, y1 - (y1 - y0) / l1 * r
        bx, by = x1 + (x2 - x1) / l2 * r, y1 + (y2 - y1) / l2 * r
        d.append(f"L{fmt(ax)} {fmt(ay)} Q{fmt(x1)} {fmt(y1)} {fmt(bx)} {fmt(by)}")
    d.append(f"L{fmt(pts[-1][0])} {fmt(pts[-1][1])}")
    return " ".join(d)


# --------------------------------------------------------------------------------------
# Document
# --------------------------------------------------------------------------------------

@dataclass
class TextRec:
    bbox: BBox
    text: str
    layer: str
    allow_overlap: bool = False


class Doc:
    """Accumulates SVG elements in layers, tracks bounds and glyph usage."""

    LAYERS = ("bg", "under", "main", "edges", "over", "labels", "top")

    def __init__(self, name: str, title: str, desc: str = ""):
        self.name = name
        self.title = title
        self.desc = desc
        self.layers: dict[str, list[str]] = {k: [] for k in self.LAYERS}
        self.bounds: BBox | None = None
        self.glyphs: dict[tuple, set] = {}
        self.texts: list[TextRec] = []
        self.defs: list[str] = []
        self._ids = 0
        self._clip: tuple[str, BBox] | None = None
        self._clips: dict = {}

    # ---- clipping ----------------------------------------------------------------------
    def clip_on(self, bb: BBox, rx: float = 10):
        key = (round(bb.x0, 2), round(bb.y0, 2), round(bb.x1, 2), round(bb.y1, 2))
        if key not in self._clips:
            cid = f"clip-{self.name}-{len(self._clips)}"
            self._clips[key] = cid
            self.defs.append(f'<clipPath id="{cid}"><rect x="{fmt(bb.x0)}" y="{fmt(bb.y0)}" width="{fmt(bb.w)}" '
                             f'height="{fmt(bb.h)}" rx="{fmt(rx)}"/></clipPath>')
        self._clip = (self._clips[key], bb)

    def clip_off(self):
        self._clip = None

    # ---- bookkeeping -----------------------------------------------------------------
    def uid(self, prefix="e"):
        self._ids += 1
        return f"{prefix}{self._ids}"

    def grow(self, bb: BBox):
        self.bounds = bb if self.bounds is None else self.bounds.union(bb)

    def raw(self, s: str, layer="main", bbox: BBox | None = None):
        if self._clip is not None:
            cid, cb = self._clip
            i = s.find(" ")
            s = s[:i] + f' clip-path="url(#{cid})"' + s[i:]
            if bbox is not None:
                bbox = BBox(max(bbox.x0, cb.x0), max(bbox.y0, cb.y0), min(bbox.x1, cb.x1), min(bbox.y1, cb.y1))
                if bbox.x1 < bbox.x0 or bbox.y1 < bbox.y0:
                    bbox = None
        self.layers[layer].append(s)
        if bbox:
            self.grow(bbox)

    @staticmethod
    def _attrs(**kw) -> str:
        out = []
        for k, v in kw.items():
            if v is None or v is False:
                continue
            k = k.rstrip("_").replace("_", "-")
            if isinstance(v, float):
                v = fmt(v)
            out.append(f'{k}="{escape(str(v), {chr(34): "&quot;"})}"')
        return " ".join(out)

    # ---- primitives ------------------------------------------------------------------
    def rect(self, x, y, w, h, *, rx=0, fill="none", stroke=None, sw=1.0, dash=None, opacity=None,
             layer="main", extra=""):
        a = self._attrs(x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=fmt(rx) if rx else None,
                        fill=fill, stroke=stroke, stroke_width=fmt(sw) if stroke else None,
                        stroke_dasharray=dash, opacity=opacity)
        self.raw(f"<rect {a} {extra}/>", layer, BBox(x, y, x + w, y + h).pad(sw / 2))
        return BBox(x, y, x + w, y + h)

    def circle(self, cx, cy, r, *, fill="none", stroke=None, sw=1.0, dash=None, opacity=None, layer="main"):
        a = self._attrs(cx=fmt(cx), cy=fmt(cy), r=fmt(r), fill=fill, stroke=stroke,
                        stroke_width=fmt(sw) if stroke else None, stroke_dasharray=dash, opacity=opacity)
        self.raw(f"<circle {a}/>", layer, BBox(cx - r, cy - r, cx + r, cy + r).pad(sw / 2))

    def line(self, x1, y1, x2, y2, *, stroke=T.border, sw=1.0, dash=None, cap="round", opacity=None, layer="main"):
        a = self._attrs(x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=fmt(sw),
                        stroke_dasharray=dash, stroke_linecap=cap, opacity=opacity)
        self.raw(f"<line {a}/>", layer, BBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)).pad(sw))

    def path(self, d, *, fill="none", stroke=None, sw=1.0, dash=None, join="round", cap="round",
             opacity=None, layer="main", bbox: BBox | None = None, extra=""):
        a = self._attrs(d=d, fill=fill, stroke=stroke, stroke_width=fmt(sw) if stroke else None,
                        stroke_dasharray=dash, stroke_linejoin=join if stroke else None,
                        stroke_linecap=cap if stroke else None, opacity=opacity)
        if bbox is None:
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", d)]
            xs, ys = nums[0::2], nums[1::2]
            bbox = BBox(min(xs), min(ys), max(xs), max(ys))
        self.raw(f"<path {a} {extra}/>", layer, bbox.pad(sw))

    def polyline(self, pts, *, stroke=T.border, sw=1.4, dash=None, radius=6, layer="edges", opacity=None):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.path(pts_to_path(pts, radius), stroke=stroke, sw=sw, dash=dash, layer=layer, opacity=opacity,
                  bbox=BBox(min(xs), min(ys), max(xs), max(ys)))

    def polygon(self, pts, *, fill="none", stroke=None, sw=1.0, layer="main", opacity=None, join="miter"):
        d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + " Z"
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.path(d, fill=fill, stroke=stroke, sw=sw, layer=layer, opacity=opacity, join=join,
                  bbox=BBox(min(xs), min(ys), max(xs), max(ys)))

    # ---- text --------------------------------------------------------------------------
    def text(self, x, y, s, *, size=13, family="sans", weight=400, style="normal", fill=T.fg,
             anchor="start", baseline="middle", layer="labels", halo: str | None = None, halo_w=4.0,
             letter_spacing: float = 0.0, allow_overlap=False, opacity=None) -> BBox:
        """Draw single-line text. (x, y) is the anchor; `baseline` is 'middle', 'top' or 'alphabetic'.
        Returns the measured bounding box."""
        if s == "":
            return BBox(x, y, x, y)
        f = face(family, weight, style)
        w = f.width(s, size) + letter_spacing * max(0, len(s) - 1)
        asc, desc = f.ascent * size, f.descent * size
        cap = 0.72 * size  # visual cap height used for vertical centring
        if baseline == "middle":
            by = y + cap / 2
        elif baseline == "top":
            by = y + cap
        else:
            by = y
        if anchor == "middle":
            x0 = x - w / 2
        elif anchor == "end":
            x0 = x - w
        else:
            x0 = x
        bb = BBox(x0, by - cap - 0.12 * size, x0 + w, by + 0.24 * size)
        self.glyphs.setdefault((family, weight, style), set()).update(s)
        css_family = f"'{FACES[(family, weight, style)][0]}', {FALLBACK[family]}"
        style_attr = []
        if halo:
            style_attr.append(f"paint-order:stroke;stroke:{halo};stroke-width:{fmt(halo_w)}px;stroke-linejoin:round")
        a = self._attrs(x=fmt(x), y=fmt(by), fill=fill, font_family=css_family, font_size=fmt(size),
                        font_weight=weight if weight != 400 else None,
                        font_style=style if style != "normal" else None,
                        text_anchor=anchor if anchor != "start" else None,
                        letter_spacing=fmt(letter_spacing) if letter_spacing else None,
                        style=";".join(style_attr) if style_attr else None, opacity=opacity)
        self.raw(f"<text {a} xml:space=\"preserve\">{escape(s)}</text>", layer, bb.pad(halo_w / 2 if halo else 0))
        if self._clip is None or self._clip[1].intersects(bb):
            self.texts.append(TextRec(bb, s, layer, allow_overlap))
        return bb

    def text_lines(self, x, y, lines: Iterable[str], *, size=13, lh=1.35, **kw) -> BBox:
        bb = None
        for i, ln in enumerate(lines):
            b = self.text(x, y + i * size * lh, ln, size=size, baseline="top", **kw)
            bb = b if bb is None else bb.union(b)
        return bb

    def rich(self, x, y, runs: Sequence[tuple], *, size=13, baseline="middle", layer="labels", anchor="start",
             halo=None):
        """Render runs [(text, family, weight, fill), ...] on one line, starting at x."""
        widths = [text_width(r[0], size, r[1], r[2]) for r in runs]
        total = sum(widths)
        cx = x - total / 2 if anchor == "middle" else (x - total if anchor == "end" else x)
        bb = None
        for (s, fam, wt, fill), w in zip(runs, widths):
            b = self.text(cx, y, s, size=size, family=fam, weight=wt, fill=fill, baseline=baseline, layer=layer,
                          halo=halo)
            bb = b if bb is None else bb.union(b)
            cx += w
        return bb

    # ---- arrowheads --------------------------------------------------------------------
    def arrowhead(self, tip, frm, *, kind="open", color=T.fg, size=11, fill=None, layer="over", sw=1.4):
        """kind: open | filled | triangle (hollow, UML generalisation) | diamond | odiamond"""
        tx, ty = tip
        fx, fy = frm
        L = math.hypot(tx - fx, ty - fy) or 1
        ux, uy = (tx - fx) / L, (ty - fy) / L
        px, py = -uy, ux
        if kind in ("open", "filled"):
            a = size
            b = size * 0.48
            p1 = (tx - ux * a + px * b, ty - uy * a + py * b)
            p2 = (tx - ux * a - px * b, ty - uy * a - py * b)
            if kind == "open":
                self.path(pts_to_path([p1, tip, p2]), stroke=color, sw=sw, layer=layer)
            else:
                self.polygon([p1, tip, p2], fill=color, stroke=color, sw=1, layer=layer, join="round")
        elif kind == "triangle":
            a = size * 1.2
            b = size * 0.62
            p1 = (tx - ux * a + px * b, ty - uy * a + py * b)
            p2 = (tx - ux * a - px * b, ty - uy * a - py * b)
            self.polygon([p1, tip, p2], fill=fill or T.bg, stroke=color, sw=sw, layer=layer)
        elif kind in ("diamond", "odiamond"):
            a = size * 1.55
            b = size * 0.5
            mid = (tx - ux * a / 2, ty - uy * a / 2)
            back = (tx - ux * a, ty - uy * a)
            p1 = (mid[0] + px * b, mid[1] + py * b)
            p2 = (mid[0] - px * b, mid[1] - py * b)
            self.polygon([tip, p1, back, p2], fill=color if kind == "diamond" else (fill or T.bg), stroke=color,
                         sw=sw, layer=layer)

    # ---- output ------------------------------------------------------------------------
    def _font_css(self) -> str:
        css = []
        for key, chars in sorted(self.glyphs.items()):
            fam, file = FACES[key]
            data = _subset_woff2(FONT_DIR / file, "".join(sorted(chars)) + " ")
            css.append("@font-face{font-family:'%s';font-weight:%d;font-style:%s;src:url(data:font/woff2;base64,%s) format('woff2');}"
                       % (fam, key[1], key[2], data))
        return "".join(css)

    def render(self, *, pad=28, bg=T.bg, radius=14, interactive=True) -> str:
        b = self.bounds.pad(pad)
        x0, y0 = math.floor(b.x0), math.floor(b.y0)
        w, h = math.ceil(b.x1 - x0), math.ceil(b.y1 - y0)
        self.canvas = BBox(x0, y0, x0 + w, y0 + h)
        body = []
        body.append(f'<rect class="bg" x="{x0}" y="{y0}" width="{w}" height="{h}" rx="{radius}" fill="{bg}"/>')
        content = []
        for k in self.LAYERS:
            if self.layers[k]:
                content.append(f'<g data-layer="{k}">' + "".join(self.layers[k]) + "</g>")
        script = PANZOOM_JS if interactive else ""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t-{self.name} d-{self.name}" data-figure="{self.name}">\n'
            f'<title id="t-{self.name}">{escape(self.title)}</title>\n'
            f'<desc id="d-{self.name}">{escape(self.desc)}</desc>\n'
            f'<defs><style>{self._font_css()}text{{font-kerning:normal;}}</style>{"".join(self.defs)}</defs>\n'
            + f'<g id="viewport">\n' + "\n".join(body) + "\n" + "\n".join(content) + "\n</g>\n"
            + script
            + "</svg>\n"
        )

    # ---- QA ----------------------------------------------------------------------------
    def text_overlaps(self, tol=0.5):
        issues = []
        ts = [t for t in self.texts if not t.allow_overlap]
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = ts[i], ts[j]
                if a.bbox.intersects(b.bbox, tol):
                    issues.append((a.text, b.text))
        return issues


_subset_cache: dict = {}


def _subset_woff2(path: Path, chars: str) -> str:
    key = (path, chars)
    if key in _subset_cache:
        return _subset_cache[key]
    opts = ft_subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt"] if "plex" in path.name else ["kern"]
    opts.name_IDs = []
    opts.notdef_outline = True
    font = TTFont(str(path))
    sub = ft_subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    _subset_cache[key] = data
    return data


# --------------------------------------------------------------------------------------
# Pan / zoom - runs only when the SVG is the top-level document (opened directly in a
# browser) or embedded with <object>/<iframe>. <img> never executes scripts.
# --------------------------------------------------------------------------------------
PANZOOM_JS = r"""<script><![CDATA[
(function(){
  var svg=document.documentElement;
  if(!svg||svg.namespaceURI!=='http://www.w3.org/2000/svg'||!svg.getScreenCTM) return;
  var NS='http://www.w3.org/2000/svg', vp=document.getElementById('viewport');
  if(!vp) return;
  var vb=svg.viewBox.baseVal, X0=vb.x, Y0=vb.y, W=vb.width, H=vb.height;
  svg.setAttribute('width','100%'); svg.setAttribute('height','100%');
  svg.style.background='#020617'; svg.style.cursor='grab'; svg.style.touchAction='none'; svg.style.userSelect='none'; svg.style.webkitUserSelect='none';
  var k=1, tx=0, ty=0;
  function apply(){ vp.setAttribute('transform','translate('+tx+' '+ty+') scale('+k+')'); hudZoom.textContent=Math.round(k*100)+'%'; }
  function toUser(e){ var p=svg.createSVGPoint(); p.x=e.clientX; p.y=e.clientY; return p.matrixTransform(svg.getScreenCTM().inverse()); }
  function zoomAt(px,py,f){ var nk=Math.min(16,Math.max(0.25,k*f)); f=nk/k; tx=px-(px-tx)*f; ty=py-(py-ty)*f; k=nk; apply(); }
  function reset(){ k=1; tx=0; ty=0; apply(); }
  // --- HUD (created only in interactive mode, so static renders stay clean) ---
  var hud=document.createElementNS(NS,'g'); hud.setAttribute('font-family',"'IBM Plex Sans','Segoe UI',sans-serif");
  var bw=30, gap=6, n=3, hx=-(bw*n+gap*(n-1)), hy=0;
  function btn(i,label,fn,title){
    var g=document.createElementNS(NS,'g'); g.style.cursor='pointer';
    var r=document.createElementNS(NS,'rect'); r.setAttribute('x',hx+i*(bw+gap)); r.setAttribute('y',hy); r.setAttribute('width',bw); r.setAttribute('height',bw); r.setAttribute('rx',7);
    r.setAttribute('fill','#1B2336'); r.setAttribute('stroke','#475569');
    var t=document.createElementNS(NS,'text'); t.setAttribute('x',hx+i*(bw+gap)+bw/2); t.setAttribute('y',hy+bw/2+5); t.setAttribute('text-anchor','middle'); t.setAttribute('fill','#F8FAFC'); t.setAttribute('font-size','16'); t.textContent=label;
    var tt=document.createElementNS(NS,'title'); tt.textContent=title; g.appendChild(tt);
    g.appendChild(r); g.appendChild(t);
    g.addEventListener('pointerdown',function(e){e.stopPropagation();});
    g.addEventListener('click',function(e){e.stopPropagation(); fn();});
    g.addEventListener('mouseenter',function(){r.setAttribute('fill','#272F42');});
    g.addEventListener('mouseleave',function(){r.setAttribute('fill','#1B2336');});
    hud.appendChild(g);
  }
  btn(0,'+',function(){zoomAt(X0+W/2,Y0+H/2,1.25);},'Zoom in (+)');
  btn(1,'–',function(){zoomAt(X0+W/2,Y0+H/2,0.8);},'Zoom out (-)');
  btn(2,'↺',reset,'Reset view (0 / double-click)');
  var hudZoom=document.createElementNS(NS,'text'); hudZoom.setAttribute('x',hx-10); hudZoom.setAttribute('y',hy+bw/2+5); hudZoom.setAttribute('text-anchor','end'); hudZoom.setAttribute('fill','#94A3B8'); hudZoom.setAttribute('font-size','13');
  hud.appendChild(hudZoom);
  var hint=document.createElementNS(NS,'text'); hint.setAttribute('fill','#64748B'); hint.setAttribute('font-size','12');
  hint.textContent='scroll / pinch to zoom · drag to pan · double-click or 0 to reset';
  var hintG=document.createElementNS(NS,'g'); hintG.setAttribute('font-family',"'IBM Plex Sans','Segoe UI',sans-serif"); hintG.appendChild(hint);
  svg.appendChild(hud); svg.appendChild(hintG);
  // keep the HUD a constant on-screen size, pinned to the window corners
  function place(){ var m=svg.getScreenCTM(); if(!m) return; var s=1/m.a;
    var tr=toUser({clientX:window.innerWidth-14,clientY:14}), bl=toUser({clientX:14,clientY:window.innerHeight-14});
    hud.setAttribute('transform','translate('+tr.x+' '+tr.y+') scale('+s+')');
    hintG.setAttribute('transform','translate('+bl.x+' '+bl.y+') scale('+s+')'); }
  window.addEventListener('resize',place); window.addEventListener('load',place); setTimeout(place,50); place(); apply();
  svg.addEventListener('wheel',function(e){ e.preventDefault(); var p=toUser(e); var d=e.deltaMode===1?e.deltaY*16:e.deltaY; zoomAt(p.x,p.y,Math.exp(-d*0.0015*(e.ctrlKey?4:1))); },{passive:false});
  var drag=null, pts={};
  svg.addEventListener('pointerdown',function(e){ pts[e.pointerId]=toUser(e); svg.setPointerCapture(e.pointerId); svg.style.cursor='grabbing'; drag={x:tx,y:ty,p:toUser(e)}; });
  svg.addEventListener('pointermove',function(e){
    if(!(e.pointerId in pts)) return;
    var ids=Object.keys(pts);
    if(ids.length===2){ var a=pts[ids[0]], b=pts[ids[1]], d0=Math.hypot(a.x-b.x,a.y-b.y); pts[e.pointerId]=toUser(e); a=pts[ids[0]]; b=pts[ids[1]]; var d1=Math.hypot(a.x-b.x,a.y-b.y); if(d0>0) zoomAt((a.x+b.x)/2,(a.y+b.y)/2,d1/d0); return; }
    if(!drag) return; var p=toUser(e); tx=drag.x+(p.x-drag.p.x); ty=drag.y+(p.y-drag.p.y); apply();
  });
  function up(e){ delete pts[e.pointerId]; drag=null; svg.style.cursor='grab'; }
  svg.addEventListener('pointerup',up); svg.addEventListener('pointercancel',up);
  svg.addEventListener('dblclick',reset);
  document.addEventListener('keydown',function(e){ if(e.key==='+'||e.key==='=') zoomAt(X0+W/2,Y0+H/2,1.25); else if(e.key==='-') zoomAt(X0+W/2,Y0+H/2,0.8); else if(e.key==='0') reset(); });
})();
]]></script>
"""
