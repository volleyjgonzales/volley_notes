"""Reusable diagram components: header/badge, legend, UML class boxes, connectors, notes, cards."""
from __future__ import annotations

import math
from typing import Sequence

from svgkit import BBox, Doc, text_width, wrap, pts_to_path
from theme import T, S

# --------------------------------------------------------------------------------------
# Header / footer framing
# --------------------------------------------------------------------------------------

BADGES = {
    "as-built": ("AS-BUILT", T.green),
    "proposed": ("PROPOSED · NOT IMPLEMENTED", T.amber),
    "illustrative": ("ILLUSTRATIVE", T.sky),
    "yaml": ("GEOMETRY FROM PECOS YAML", T.green),
    "yaml+hyp": ("YAML GEOMETRY · HYPOTHETICAL OCCUPANCY", T.amber),
    "conceptual": ("CONCEPTUAL · NOT IN PECOS YAML", T.violet),
    "schematic": ("SCHEMATIC · NOT TO SCALE", T.sky),
    "concept": ("CONCEPTUAL · INTERNALS NOT IN SNAPSHOT", T.violet),
    "yaml+concept": ("YAML GEOMETRY · CONCEPTUAL INTERNALS", T.violet),
}


def badge(doc: Doc, x_right: float, y: float, key: str) -> BBox:
    label, color = BADGES[key]
    size = 10.5
    w = text_width(label, size, "mono", 600) + 0.6 * (len(label) - 1)
    pad = 10
    dot = 7
    total = pad + dot + 7 + w + pad
    x0 = x_right - total
    doc.rect(x0, y, total, 24, rx=12, fill=T.tint(color, 0.12, T.bg), stroke=T.tint(color, 0.55, T.bg), sw=1,
             layer="labels")
    doc.circle(x0 + pad + dot / 2, y + 12, dot / 2, fill=color, layer="labels")
    doc.text(x0 + pad + dot + 7, y + 12, label, size=size, family="mono", weight=600, fill=color,
             letter_spacing=0.6, layer="top")
    return BBox(x0, y, x_right, y + 24)


def frame(doc: Doc, *, title: str, subtitle: str | None = None, badge_key: str | None = None,
          legend: Sequence | None = None, legend_title: str | None = "Legend", footnote: str | None = None,
          min_width: float = 0):
    """Add header (title, subtitle, status badge), a footer legend and a footnote around the
    already-drawn content. Everything is laid out from the measured content bounds, so the
    legend can never overlap the drawing and nothing can leave the canvas."""
    cb = doc.bounds
    x0 = cb.x0
    width = max(cb.w, min_width)
    x1 = x0 + width

    # ---- footer: legend + footnote -------------------------------------------------------
    y = cb.y1 + 26
    if legend:
        y = legend_block(doc, x0, y, width, legend, title=legend_title) + 14
    if footnote:
        lines = wrap(footnote, width, S.small, "sans", 400)
        doc.text_lines(x0, y, lines, size=S.small, fill=T.muted, lh=1.45)

    # ---- header ---------------------------------------------------------------------------
    bw = 0
    if badge_key:
        label, _ = BADGES[badge_key]
        bw = text_width(label, 10.5, "mono", 600) + 0.6 * len(label) + 34 + 20
    t_lines = wrap(title, width - bw, S.title, "sans", 600)
    s_lines = wrap(subtitle, width, S.subtitle, "sans", 400) if subtitle else []
    h_title = len(t_lines) * S.title * 1.25
    h_sub = len(s_lines) * S.subtitle * 1.45
    gap = 8 if s_lines else 0
    header_h = h_title + gap + h_sub
    top = cb.y0 - 22 - header_h - 16
    doc.text_lines(x0, top, t_lines, size=S.title, weight=600, fill=T.fg, lh=1.25)
    if s_lines:
        doc.text_lines(x0, top + h_title + gap, s_lines, size=S.subtitle, fill=T.muted, lh=1.45)
    if badge_key:
        badge(doc, x1, top - 3, badge_key)
    rule_y = top + header_h + 14
    doc.line(x0, rule_y, x1, rule_y, stroke=T.border_soft, sw=1, layer="under")


# --------------------------------------------------------------------------------------
# Legend
# --------------------------------------------------------------------------------------

def legend_glyph(doc: Doc, kind: str, color: str, x: float, cy: float) -> float:
    """Draw a legend glyph whose left edge is x, centred on cy. Returns glyph width."""
    L = "labels"
    if kind == "box":
        doc.rect(x, cy - 7, 22, 14, rx=3, fill=T.tint(color, 0.18, T.bg), stroke=color, sw=1.4, layer=L)
        return 22
    if kind == "fill":
        doc.rect(x, cy - 7, 22, 14, rx=3, fill=color, layer=L)
        return 22
    if kind == "dashbox":
        doc.rect(x, cy - 7, 22, 14, rx=3, fill="none", stroke=color, sw=1.4, dash="4 3", layer=L)
        return 22
    if kind == "dot":
        doc.circle(x + 6, cy, 5, fill=color, layer=L)
        return 12
    if kind == "hollow":
        doc.circle(x + 7, cy, 6, fill=T.bg, stroke=color, sw=1.5, dash="3 2.2", layer=L)
        return 14
    if kind == "ring":
        doc.circle(x + 8, cy, 7, fill=T.tint(color, 0.2, T.bg), stroke=color, sw=1.6, layer=L)
        return 16
    if kind in ("line", "dash"):
        doc.line(x, cy, x + 28, cy, stroke=color, sw=2.2, dash="5 4" if kind == "dash" else None, layer=L)
        return 28
    if kind in ("arrow", "dasharrow", "route"):
        sw = 3 if kind == "route" else 1.6
        doc.line(x, cy, x + 24, cy, stroke=color, sw=sw, dash="5 4" if kind == "dasharrow" else None, layer=L)
        doc.arrowhead((x + 32, cy), (x, cy), kind="filled", color=color, size=9 if kind == "route" else 8, layer=L)
        return 32
    if kind == "assoc":
        doc.line(x, cy, x + 30, cy, stroke=color, sw=1.4, layer=L)
        doc.arrowhead((x + 32, cy), (x, cy), kind="open", color=color, size=9, layer=L)
        return 32
    if kind == "dep":
        doc.line(x, cy, x + 30, cy, stroke=color, sw=1.4, dash="5 4", layer=L)
        doc.arrowhead((x + 32, cy), (x, cy), kind="open", color=color, size=9, layer=L)
        return 32
    if kind in ("comp", "agg"):
        doc.line(x + 16, cy, x + 36, cy, stroke=color, sw=1.4, layer=L)
        doc.arrowhead((x, cy), (x + 36, cy), kind="diamond" if kind == "comp" else "odiamond", color=color,
                      size=10, layer=L)
        return 36
    if kind in ("inh", "real"):
        doc.line(x, cy, x + 22, cy, stroke=color, sw=1.4, dash="5 4" if kind == "real" else None, layer=L)
        doc.arrowhead((x + 34, cy), (x, cy), kind="triangle", color=color, size=10, layer=L)
        return 34
    raise ValueError(kind)


def legend_block(doc: Doc, x0: float, y0: float, width: float, items: Sequence, title: str | None = "Legend") -> float:
    """Horizontal, wrapping legend. items: (kind, color, label). Returns bottom y."""
    size = S.small + 0.5
    row_h = 24
    col_gap = 26
    pad = 14
    entries = []
    for kind, color, label in items:
        gw = {"box": 22, "fill": 22, "dashbox": 22, "dot": 12, "ring": 16, "hollow": 14, "line": 28, "dash": 28, "arrow": 32,
              "dasharrow": 32, "route": 32, "assoc": 32, "dep": 32, "comp": 36, "agg": 36, "inh": 34,
              "real": 34}[kind]
        entries.append((kind, color, label, gw + 9 + text_width(label, size, "sans", 400)))
    inner_w = width - 2 * pad
    title_w = (text_width(title.upper(), 10.5, "mono", 600) + 0.8 * len(title) + 18) if title else 0
    rows: list[list] = [[]]
    cur = title_w
    for e in entries:
        need = e[3] + (col_gap if rows[-1] else 0)
        if cur + need > inner_w and rows[-1]:
            rows.append([])
            cur = title_w
            need = e[3]
        rows[-1].append(e)
        cur += need
    h = pad * 2 + len(rows) * row_h - 4
    doc.rect(x0, y0, width, h, rx=10, fill=T.tint(T.card, 0.55, T.bg), stroke=T.border_soft, sw=1, layer="under")
    if title:
        doc.text(x0 + pad, y0 + pad + row_h / 2 - 2, title.upper(), size=10.5, family="mono", weight=600,
                 fill=T.muted, letter_spacing=0.8)
    for r, row in enumerate(rows):
        cx = x0 + pad + title_w
        cy = y0 + pad + r * row_h + row_h / 2 - 2
        for kind, color, label, w in row:
            gw = legend_glyph(doc, kind, color, cx, cy)
            doc.text(cx + gw + 9, cy, label, size=size, fill=T.fg2)
            cx += w + col_gap
    return y0 + h


# --------------------------------------------------------------------------------------
# UML class box
# --------------------------------------------------------------------------------------

class Box(BBox):
    """BBox plus a name; created by uml_class / card."""

    def __init__(self, bb: BBox, name: str = ""):
        super().__init__(bb.x0, bb.y0, bb.x1, bb.y1)
        self.name = name


def _member_runs(line: str, accent: str, highlight: dict | None = None):
    """Very small syntax colouring for UML member lines: visibility, name, ': Type' / '= value'."""
    if line.startswith("  "):
        return [(line, "mono", 400, T.muted)]
    vis = ""
    rest = line
    if line[:2] in ("+ ", "- ", "# ", "~ "):
        vis, rest = line[:2], line[2:]
    runs = []
    if vis:
        runs.append((vis, "mono", 600, accent))
    # split name from type
    cut = None
    for sep in (": ", " = "):
        i = rest.find(sep)
        if i > 0 and (cut is None or i < cut[0]):
            cut = (i, sep)
    if cut and "(" not in rest[:cut[0]]:
        i, sep = cut
        runs.append((rest[:i], "mono", 400, T.fg))
        tail = rest[i:]
        col = T.muted
        for key, c in (highlight or {}).items():
            if key in tail:
                col = c
        runs.append((tail, "mono", 400, col))
    elif "(" in rest:
        j = rest.find("(")
        runs.append((rest[:j], "mono", 400, T.fg))
        runs.append((rest[j:], "mono", 400, T.muted))
    else:
        runs.append((rest, "mono", 400, T.fg2))
    return runs


def uml_class(doc: Doc, x: float, y: float, name: str, *, accent: str = T.sky, stereo: str | None = None,
              attrs: Sequence[str] = (), methods: Sequence[str] = (), w: float | None = None,
              abstract: bool = False, size: float = S.body, name_size: float = S.h, center_x: bool = False,
              compact: bool = False, highlight: dict | None = None) -> Box:
    """UML class box. (x, y) = top-left (or top-centre when center_x). Width auto-fits."""
    padx = 12
    lh = size * 1.55
    name_style = "italic" if abstract else "normal"
    name_w = text_width(name, name_size, "mono", 400 if abstract else 700, name_style)
    stereo_txt = f"«{stereo}»" if stereo else None
    st_w = text_width(stereo_txt, S.tiny, "sans", 400) if stereo else 0
    mem_w = max([sum(text_width(r[0], size, r[1], r[2]) for r in _member_runs(m, accent, highlight)) for m in
                 list(attrs) + list(methods)] or [0])
    need = max(name_w, st_w, mem_w) + 2 * padx
    w = max(w or 0, need)
    if center_x:
        x = x - w / 2
    head_h = (16 if stereo else 0) + name_size + 20
    sec_pad = 8
    a_h = (len(attrs) * lh + sec_pad * 2) if attrs else (0 if compact else 10)
    m_h = (len(methods) * lh + sec_pad * 2) if methods else (0 if compact else 10)
    h = head_h + a_h + m_h
    accent_dim = T.tint(accent, 0.45)
    # body
    doc.rect(x, y, w, h, rx=6, fill=T.card, layer="main")
    # header band
    doc.path(f"M{x} {y + head_h} L{x} {y + 6} Q{x} {y} {x + 6} {y} L{x + w - 6} {y} Q{x + w} {y} {x + w} {y + 6} "
             f"L{x + w} {y + head_h} Z", fill=T.tint(accent, 0.16), layer="main")
    doc.rect(x, y, w, h, rx=6, fill="none", stroke=accent, sw=1.5, layer="main")
    cy = y + 10
    if stereo:
        doc.text(x + w / 2, cy + 6, stereo_txt, size=S.tiny, fill=T.muted, anchor="middle")
        cy += 16
    doc.text(x + w / 2, cy + name_size / 2 + 4, name, size=name_size, family="mono",
             weight=400 if abstract else 700, style=name_style, fill=accent if not abstract else T.fg,
             anchor="middle")
    yy = y + head_h
    for sec in (attrs, methods):
        if not sec and compact:
            continue
        doc.line(x, yy, x + w, yy, stroke=accent_dim, sw=1, cap="butt", layer="main")
        yy += sec_pad if sec else 0
        for m in sec:
            doc.rich(x + padx, yy + lh / 2, _member_runs(m, accent, highlight), size=size)
            yy += lh
        yy += sec_pad if sec else 10
    return Box(BBox(x, y, x + w, y + h), name)


def class_size(name: str, *, stereo=None, attrs=(), methods=(), size=S.body, name_size=S.h, abstract=False,
               w=None, compact=False):
    """Measure a class box without drawing it (for layout)."""
    tmp = Doc("tmp", "")
    b = uml_class(tmp, 0, 0, name, stereo=stereo, attrs=attrs, methods=methods, size=size, name_size=name_size,
                  abstract=abstract, w=w, compact=compact)
    return b.w, b.h


# --------------------------------------------------------------------------------------
# Connectors
# --------------------------------------------------------------------------------------

def label_pill(doc: Doc, x: float, y: float, s: str, *, color=T.fg2, size=S.small, family="mono", weight=400,
               bg=T.bg, border: str | None = None, anchor="middle", padx=6, pady=3, layer="labels") -> BBox:
    w = text_width(s, size, family, weight)
    if anchor == "middle":
        x0 = x - w / 2 - padx
    elif anchor == "start":
        x0 = x
    else:
        x0 = x - w - 2 * padx
    h = size + 2 * pady + 2
    doc.rect(x0, y - h / 2, w + 2 * padx, h, rx=h / 2 if border else 4, fill=bg, stroke=border,
             sw=1 if border else 1, layer=layer)
    doc.text(x0 + padx, y, s, size=size, family=family, weight=weight, fill=color, layer="top")
    return BBox(x0, y - h / 2, x0 + w + 2 * padx, y + h / 2)


def _shorten(pts, d0, d1):
    pts = [tuple(p) for p in pts]
    if d0:
        (x0, y0), (x1, y1) = pts[0], pts[1]
        L = math.hypot(x1 - x0, y1 - y0)
        pts[0] = (x0 + (x1 - x0) / L * d0, y0 + (y1 - y0) / L * d0)
    if d1:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        L = math.hypot(x1 - x0, y1 - y0)
        pts[-1] = (x1 - (x1 - x0) / L * d1, y1 - (y1 - y0) / L * d1)
    return pts


def connect(doc: Doc, pts, *, kind="assoc", color=T.fg2, sw=1.4, label: str | None = None,
            label_at: tuple | None = None, label_color: str | None = None, mult_start: str | None = None,
            mult_end: str | None = None, radius=8, size=10, dash=None, label_anchor="middle"):
    """UML-ish connector along explicit orthogonal waypoints.
    kind: assoc (open arrow at end) | dep (dashed, open arrow) | comp (filled diamond at START)
          | agg (hollow diamond at START) | inh (hollow triangle at END) | real (dashed, hollow
          triangle at END) | flow (filled arrow) | line"""
    pts = [tuple(p) for p in pts]
    dashed = dash or ("6 4" if kind in ("dep", "real") else None)
    start_cut = end_cut = 0
    if kind in ("comp", "agg"):
        start_cut = size * 1.55
    if kind in ("inh", "real"):
        end_cut = size * 1.2
    if kind in ("assoc", "dep"):
        end_cut = 1
    if kind == "flow":
        end_cut = size * 0.9
    body = _shorten(pts, start_cut, end_cut)
    doc.polyline(body, stroke=color, sw=sw, dash=dashed, radius=radius)
    if kind in ("comp", "agg"):
        doc.arrowhead(pts[0], pts[1], kind="diamond" if kind == "comp" else "odiamond", color=color, size=size,
                      sw=sw)
    if kind in ("assoc", "dep"):
        doc.arrowhead(pts[-1], pts[-2], kind="open", color=color, size=size, sw=sw)
    if kind in ("inh", "real"):
        doc.arrowhead(pts[-1], pts[-2], kind="triangle", color=color, size=size, sw=sw)
    if kind == "flow":
        doc.arrowhead(pts[-1], pts[-2], kind="filled", color=color, size=size, sw=sw)
    if label:
        if label_at is None:
            # midpoint of the longest segment
            best = max(range(len(pts) - 1), key=lambda i: math.hypot(pts[i + 1][0] - pts[i][0],
                                                                     pts[i + 1][1] - pts[i][1]))
            label_at = ((pts[best][0] + pts[best + 1][0]) / 2, (pts[best][1] + pts[best + 1][1]) / 2)
        label_pill(doc, label_at[0], label_at[1], label, color=label_color or color, anchor=label_anchor)
    for txt, (p, q) in ((mult_start, (pts[0], pts[1])), (mult_end, (pts[-1], pts[-2]))):
        if not txt:
            continue
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        off = 26 if kind in ("comp", "agg") and p == pts[0] else 16
        mx, my = p[0] + ux * off, p[1] + uy * off
        # put the multiplicity to the right of vertical segments / above horizontal ones
        if abs(ux) < 0.5:
            doc.text(mx + 7, my, txt, size=S.tiny, family="mono", fill=T.muted, anchor="start")
        else:
            doc.text(mx, my - 9, txt, size=S.tiny, family="mono", fill=T.muted, anchor="middle")


# --------------------------------------------------------------------------------------
# Notes, chips, cards
# --------------------------------------------------------------------------------------

def note(doc: Doc, x: float, y: float, w: float, text: str, *, color=T.muted, size=S.small + 0.5,
         title: str | None = None, accent=T.border) -> BBox:
    """UML note (folded corner)."""
    pad = 12
    lines = wrap(text, w - 2 * pad, size, "sans", 400)
    th = (size * 1.45 + 4) if title else 0
    h = pad * 2 + th + len(lines) * size * 1.45 - (size * 0.45)
    f = 12
    doc.path(f"M{x} {y} L{x + w - f} {y} L{x + w} {y + f} L{x + w} {y + h} L{x} {y + h} Z",
             fill=T.tint(T.card, 0.7, T.bg), stroke=accent, sw=1.2, layer="main")
    doc.path(f"M{x + w - f} {y} L{x + w - f} {y + f} L{x + w} {y + f}", stroke=accent, sw=1.2, layer="main")
    yy = y + pad
    if title:
        doc.text(x + pad, yy, title, size=size, weight=600, fill=T.fg, baseline="top")
        yy += th
    doc.text_lines(x + pad, yy, lines, size=size, fill=color, lh=1.45)
    return BBox(x, y, x + w, y + h)


def chip(doc: Doc, x, y, s, color, *, size=S.small, anchor="start", family="mono", weight=600, fill=None,
         layer="labels") -> BBox:
    w = text_width(s, size, family, weight)
    padx = 8
    h = size + 10
    x0 = x if anchor == "start" else (x - w / 2 - padx if anchor == "middle" else x - w - 2 * padx)
    doc.rect(x0, y - h / 2, w + 2 * padx, h, rx=h / 2, fill=fill or T.tint(color, 0.16, T.bg),
             stroke=T.tint(color, 0.6, T.bg), sw=1, layer=layer)
    doc.text(x0 + padx, y, s, size=size, family=family, weight=weight, fill=color, layer="top")
    return BBox(x0, y - h / 2, x0 + w + 2 * padx, y + h / 2)


def num_badge(doc: Doc, cx, cy, n, color, *, r=11, layer="top"):
    doc.circle(cx, cy, r, fill=color, layer=layer)
    doc.text(cx, cy + 0.5, str(n), size=12 if len(str(n)) < 2 else 10, family="mono", weight=700, fill=T.bg, anchor="middle", layer=layer)


def card(doc: Doc, x, y, w, h, *, title: str, accent: str, lines: Sequence[str] = (), sub: str | None = None,
         num: int | None = None, mono_lines=True, title_size=15, line_size=S.body, dashed=False) -> Box:
    doc.rect(x, y, w, h, rx=10, fill=T.card, stroke=accent, sw=1.5, dash="6 4" if dashed else None)
    tx = x + 18
    ty = y + 18
    if num is not None:
        num_badge(doc, tx + 10, ty + 9, num, accent)
        tx += 28
    for i, ln in enumerate(wrap(title, w - (tx - x) - 14, title_size, "sans", 600)):
        doc.text(tx, ty + 9 + i * title_size * 1.25, ln, size=title_size, weight=600, fill=T.fg)
        last = ty + 9 + i * title_size * 1.25
    yy = last + 14
    if sub:
        for ln in wrap(sub, w - 32, S.small + 0.5, "sans"):
            doc.text(x + 18, yy + 6, ln, size=S.small + 0.5, fill=T.muted)
            yy += 18
        yy += 4
    for ln in lines:
        if mono_lines:
            doc.text(x + 18, yy + 10, ln, size=line_size, family="mono", fill=T.fg2)
        else:
            doc.text(x + 18, yy + 10, ln, size=line_size, fill=T.fg2)
        yy += line_size * 1.65
    return Box(BBox(x, y, x + w, y + h), title)


# --------------------------------------------------------------------------------------
# Event chips (shared by the code-walkthrough figures)
# --------------------------------------------------------------------------------------

EVENT_COLOR = {
    "TrayMove": T.amber, "AgvMove": T.green, "BayTransition": T.violet, "VecsTransition": T.pink,
    "ActionNode": T.sky, "recipe": T.fg2,
}


def event_box(doc: Doc, x, y, kind: str, text: str, *, w: float | None = None, n=None, style="solid",
              h=50, size=12, color: str | None = None, sub: str | None = None) -> BBox:
    """Rounded event card: kind label (coloured) above a mono text line.
    style: solid | optional (dashed border) | faded (applied / past) | new (glow ring)."""
    col = color or EVENT_COLOR.get(kind.split(" ")[0], T.fg2)
    tw = max(text_width(text, size, "mono"), text_width(kind, 10.5, "mono", 600) + (16 if n is not None else 0))
    if sub:
        tw = max(tw, text_width(sub, 10.5, "sans"))
    w = w or tw + 24
    if sub:
        h = max(h, 64)
    if style == "new":
        doc.rect(x - 4, y - 4, w + 8, h + 8, rx=11, fill="none", stroke=T.tint(col, 0.5, T.bg), sw=1.2,
                 dash="2 3")
    op = 0.45 if style == "faded" else None
    doc.rect(x, y, w, h, rx=8, fill=T.card if style != "faded" else T.bg, stroke=col, sw=1.4,
             dash="5 4" if style == "optional" else None, opacity=op)
    kx = x + 12 + (14 if n is not None else 0)
    doc.text(kx, y + 15, kind, size=10.5, family="mono", weight=600, fill=col, opacity=op)
    doc.text(x + 12, y + 34, text, size=size, family="mono", fill=T.fg if style != "faded" else T.muted,
             opacity=op)
    if sub:
        doc.text(x + 12, y + 52, sub, size=10.5, fill=T.muted, opacity=op)
    if n is not None:
        num_badge(doc, x + 2, y + 2, n, col, r=10)
    return BBox(x, y, x + w, y + h)


def flow(doc: Doc, a: BBox, b: BBox, *, color=T.muted, label=None, dash=None, sw=1.5, side="h", label_at=None):
    """Arrow from box a to box b. side='h' (right->left edges) or 'v' (bottom->top)."""
    if side == "h":
        if abs(a.cy - b.cy) < 2:
            pts = [(a.x1, a.cy), (b.x0, b.cy)]
        else:
            mx = (a.x1 + b.x0) / 2
            pts = [(a.x1, a.cy), (mx, a.cy), (mx, b.cy), (b.x0, b.cy)]
    else:
        if abs(a.cx - b.cx) < 2:
            pts = [(a.cx, a.y1), (b.cx, b.y0)]
        else:
            my = (a.y1 + b.y0) / 2
            pts = [(a.cx, a.y1), (a.cx, my), (b.cx, my), (b.cx, b.y0)]
    connect(doc, pts, kind="flow", color=color, size=8, sw=sw, dash=dash, label=label, label_at=label_at)


def code_panel(doc: Doc, x, y, w, lines, *, title: str | None = None, size=12, comment_color=T.faint) -> BBox:
    """Monospace code block. Lines starting with // are comments; '«...»' segments are highlighted."""
    pad = 14
    lh = size * 1.5
    th = 24 if title else 0
    h = pad * 2 + th + len(lines) * lh - (lh - size)
    doc.rect(x, y, w, h, rx=10, fill="#0B1222", stroke=T.border_soft, sw=1)
    if title:
        doc.text(x + pad, y + pad + 6, title, size=11, family="mono", weight=600, fill=T.muted)
    yy = y + pad + th + size / 2
    for ln in lines:
        stripped = ln.lstrip()
        if stripped.startswith("//"):
            doc.text(x + pad, yy, ln, size=size, family="mono", fill=comment_color)
        elif "//" in ln:
            i = ln.index("//")
            doc.rich(x + pad, yy, [(ln[:i], "mono", 400, T.fg), (ln[i:], "mono", 400, comment_color)], size=size)
        else:
            doc.text(x + pad, yy, ln, size=size, family="mono", fill=T.fg)
        yy += lh
    return BBox(x, y, x + w, y + h)
