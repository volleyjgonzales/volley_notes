"""Tiny SVG toolkit for the AGV requirement figures.

Design tokens come from the UI UX Pro Max design system
(design-system/agv-spec/MASTER.md): Minimalism & Swiss Style,
"tracking blue + delivery orange", IBM Plex Sans / JetBrains Mono.
"""
import math
from xml.sax.saxutils import escape

# ---- design tokens (from MASTER.md) ----
C = {
    "primary": "#2563EB",
    "secondary": "#3B82F6",
    "accent": "#EA580C",
    "bg": "#EFF6FF",
    "fg": "#1E40AF",
    "card": "#FFFFFF",
    "muted": "#E9EFF8",
    "mutedfg": "#475569",
    "border": "#BFDBFE",
    "red": "#DC2626",
    # status-only additions (kept within the same cool/neutral family)
    "green": "#15803D",
    "teal": "#0E7490",
    "slate": "#64748B",
    "ink": "#0F172A",
    "tape": "#94A3B8",
}
SANS = "'IBM Plex Sans', 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"

# status vocabulary: (label, color, letter) - letter so meaning never relies on color alone
STATUS = {
    "works":       ("Works today",                 C["green"],   "W"),
    "implement":   ("Will implement",              C["primary"], "I"),
    "conditional": ("Conditional / to discuss",    C["accent"],  "C"),
    "rejected":    ("Not feasible",                C["red"],     "R"),
    "blocked":     ("Needs hardware / clarification", C["slate"], "B"),
    "duplicate":   ("Closed as duplicate",         C["teal"],    "D"),
    "process":     ("Process / outside AGV",       "#93A4BF",    "P"),
}


# ---- real-world scale used by every plan view ----
PX = 40.0          # pixels per metre in plan views
AGV_L, AGV_W = 1.8, 1.1   # assumed AGV footprint in metres (source gives none)
TAPE_W = 0.05      # magnetic tape width in metres


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


class SVG:
    def __init__(self, w, h, title, subtitle=None, card=True):
        self.w, self.h = w, h
        self.el = []
        self.title, self.subtitle = title, subtitle
        if card:
            self.el.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" '
                           f'fill="{C["card"]}" stroke="{C["border"]}" stroke-width="1.5"/>')
            self.text(28, 40, title, size=19, weight=600, color=C["fg"])
            if subtitle:
                self.text(28, 62, subtitle, size=12.5, color=C["mutedfg"])

    # ---------- primitives ----------
    def raw(self, s):
        self.el.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1.5, rx=0, dash=None, opacity=None, extra=""):
        s = f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        if opacity is not None:
            s += f' opacity="{opacity}"'
        self.el.append(s + f' {extra}/>')

    def line(self, x1, y1, x2, y2, color=None, sw=1.5, dash=None, arrow=None, cap="round"):
        color = color or C["ink"]
        s = (f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{color}" '
             f'stroke-width="{sw}" stroke-linecap="{cap}"')
        if dash:
            s += f' stroke-dasharray="{dash}"'
        if arrow:
            s += f' marker-end="url(#ah-{arrow})"'
        self.el.append(s + "/>")

    def arrow(self, x1, y1, x2, y2, color="ink", sw=1.8, dash=None):
        self.line(x1, y1, x2, y2, C[color], sw, dash, arrow=color)

    def path(self, d, color=None, sw=1.8, fill="none", dash=None, arrow=None, opacity=None):
        color = color or C["ink"]
        s = f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        if arrow:
            s += f' marker-end="url(#ah-{arrow})"'
        if opacity is not None:
            s += f' opacity="{opacity}"'
        self.el.append(s + "/>")

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=1.5, dash=None):
        s = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        self.el.append(s + "/>")

    def text(self, x, y, t, size=13, color=None, weight=400, anchor="start", mono=False, italic=False):
        color = color or C["ink"]
        fam = MONO if mono else SANS
        st = ' font-style="italic"' if italic else ""
        self.el.append(f'<text x="{f(x)}" y="{f(y)}" font-family="{fam}" font-size="{size}" '
                       f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}" style="white-space:pre" xml:space="preserve"{st}>{escape(str(t))}</text>')

    def lines(self, x, y, rows, size=13, lh=None, **kw):
        lh = lh or size * 1.4
        for i, r in enumerate(rows):
            self.text(x, y + i * lh, r, size=size, **kw)

    # ---------- composites ----------
    def chip(self, x, y, status, text=None, size=12):
        label, color, letter = STATUS[status]
        text = text or label
        w = 30 + len(text) * size * 0.56
        self.rect(x, y, w, 22, fill=color, rx=11, opacity=0.12)
        self.rect(x, y, w, 22, fill="none", stroke=color, rx=11, sw=1)
        self.circle(x + 11, y + 11, 7, fill=color)
        self.text(x + 11, y + 15, letter, size=9.5, color="#FFFFFF", weight=700, anchor="middle", mono=True)
        self.text(x + 23, y + 15.5, text, size=size, color=color if status != "process" else C["mutedfg"], weight=500)
        return w

    def tag(self, x, y, req, color=None):
        """Small requirement id badge, e.g. 1.1"""
        color = color or C["fg"]
        w = 12 + len(req) * 7.6
        self.rect(x, y, w, 20, fill=C["bg"], stroke=C["border"], rx=4, sw=1)
        self.text(x + w / 2, y + 14.5, req, size=11.5, color=color, weight=600, anchor="middle", mono=True)
        return w

    def note(self, x, y, w, rows, color=None, size=12.5, title=None):
        color = color or C["primary"]
        h = 16 + len(rows) * size * 1.45 + (size * 1.6 if title else 0)
        self.rect(x, y, w, h, fill=C["bg"], rx=6)
        self.rect(x, y, 4, h, fill=color, rx=2)
        yy = y + 8 + size * 1.15
        if title:
            self.text(x + 14, yy, title, size=size, weight=600, color=color)
            yy += size * 1.6
        self.lines(x + 14, yy, rows, size=size, color=C["ink"])
        return h

    def tape(self, x1, y1, x2, y2, w=None):
        """Magnetic tape at true width (50 mm), never thinner than 2.5 px so it stays visible."""
        w = w or max(2.5, TAPE_W * PX)
        self.line(x1, y1, x2, y2, C["tape"], sw=w, cap="butt")
        if w >= 6:
            self.line(x1, y1, x2, y2, "#CBD5E1", sw=1, cap="butt", dash="2 6")

    def scale_bar(self, x, y, metres=1.0, px_per_m=None, label=None):
        px_per_m = px_per_m or PX
        L = metres * px_per_m
        self.rect(x, y - 3, L / 2, 6, fill=C["ink"])
        self.rect(x + L / 2, y - 3, L / 2, 6, fill=C["card"], stroke=C["ink"], sw=1)
        lab = label or (f"{metres:g} m" if metres >= 1 else f"{metres*1000:g} mm")
        self.text(x + L + 8, y + 4, lab, size=11.5, color=C["mutedfg"], mono=True)

    def magnifier(self, cx, cy, r, box):
        """Circle marking a zoomed area, with leader lines to an inset box (x, y, w, h)."""
        bx, by, bw, bh = box
        self.circle(cx, cy, r, fill="none", stroke=C["accent"], sw=1.8)
        corners = [(bx, by), (bx + bw, by)] if by > cy else [(bx, by + bh), (bx + bw, by + bh)]
        for (qx, qy) in corners:
            ang = math.atan2(qy - cy, qx - cx)
            self.line(cx + r * math.cos(ang), cy + r * math.sin(ang), qx, qy, C["accent"], 1, dash="3 3")
        self.rect(bx, by, bw, bh, fill=C["card"], stroke=C["accent"], sw=1.8, rx=6)

    def node(self, x, y, label=None, color=None, r=5, filled=True, label_dy=-12):
        color = color or C["fg"]
        self.circle(x, y, r, fill=color if filled else C["card"], stroke=color, sw=2)
        if label:
            self.text(x, y + label_dy, label, size=12, anchor="middle", color=color, weight=600, mono=True)

    def rfid(self, x, y):
        self.rect(x - 5, y - 5, 10, 10, fill=C["card"], stroke=C["accent"], sw=1.5, rx=1)

    def robot(self, cx, cy, heading=0, L=AGV_L * PX, W=AGV_W * PX, ghost=False, color=None, label=None, scale=1.0):
        """Top-down rectangular AGV.

        heading: degrees, SVG convention (0 = facing right, +90 = facing down).
        Orientation cues: orange front bumper, solid chevron pointing forward,
        lidar dome at the front, two wheel slots at the sides.
        """
        L, W = L * scale, W * scale
        color = color or C["fg"]
        op = ' opacity="0.45"' if ghost else ""
        dash = ' stroke-dasharray="5 4"' if ghost else ""
        hl, hw = L / 2, W / 2
        g = [f'<g transform="translate({f(cx)} {f(cy)}) rotate({f(heading)})"{op}>']
        # wheels
        for sx in (-L * 0.18, L * 0.18):
            for sy in (-hw - 3, hw - 3):
                g.append(f'<rect x="{f(sx - 8*scale)}" y="{f(sy)}" width="{f(16*scale)}" height="6" rx="2" fill="{C["ink"]}"/>')
        # body
        g.append(f'<rect x="{f(-hl)}" y="{f(-hw)}" width="{f(L)}" height="{f(W)}" rx="{f(5*scale)}" '
                 f'fill="{C["card"]}" stroke="{color}" stroke-width="2"{dash}/>')
        # rear marking: two short lines (back = "ventilation slots")
        for dy in (-hw * 0.35, hw * 0.35):
            g.append(f'<line x1="{f(-hl + 6*scale)}" y1="{f(dy)}" x2="{f(-hl + 14*scale)}" y2="{f(dy)}" '
                     f'stroke="{C["slate"]}" stroke-width="2" stroke-linecap="round"/>')
        # front bumper
        g.append(f'<rect x="{f(hl - 7*scale)}" y="{f(-hw + 2)}" width="{f(7*scale)}" height="{f(W - 4)}" '
                 f'rx="2" fill="{C["accent"]}"/>')
        # chevron
        cl = L * 0.2
        g.append(f'<path d="M {f(-cl*0.6)} {f(-hw*0.5)} L {f(cl)} 0 L {f(-cl*0.6)} {f(hw*0.5)} Z" '
                 f'fill="{color}"/>')
        g.append("</g>")
        self.el.append("".join(g))
        if label:
            self.text(cx, cy + W / 2 + 22, label, size=12, anchor="middle", color=C["mutedfg"])

    def arc(self, cx, cy, r, a1, a2, color="primary", sw=2, dash=None, arrow=True):
        """Arc from angle a1 to a2 (degrees, SVG convention, clockwise positive)."""
        x1 = cx + r * math.cos(math.radians(a1))
        y1 = cy + r * math.sin(math.radians(a1))
        x2 = cx + r * math.cos(math.radians(a2))
        y2 = cy + r * math.sin(math.radians(a2))
        large = 1 if abs(a2 - a1) > 180 else 0
        sweep = 1 if a2 > a1 else 0
        self.path(f"M {f(x1)} {f(y1)} A {r} {r} 0 {large} {sweep} {f(x2)} {f(y2)}",
                  color=C[color], sw=sw, dash=dash, arrow=color if arrow else None)

    def okx(self, x, y, ok=True, r=10):
        col = C["green"] if ok else C["red"]
        self.circle(x, y, r, fill=col)
        if ok:
            self.path(f"M {x-5} {y} L {x-1.5} {y+4} L {x+5} {y-4}", color="#FFFFFF", sw=2.2)
        else:
            self.path(f"M {x-4} {y-4} L {x+4} {y+4} M {x+4} {y-4} L {x-4} {y+4}", color="#FFFFFF", sw=2.2)

    def axes(self, x, y, w, h, xlabel, ylabel):
        self.line(x, y + h, x + w, y + h, C["mutedfg"], 1.3, arrow="mutedfg")
        self.line(x, y + h, x, y, C["mutedfg"], 1.3, arrow="mutedfg")
        self.text(x + w, y + h + 20, xlabel, size=12, anchor="end", color=C["mutedfg"])
        self.text(x + 6, y - 6, ylabel, size=12, color=C["mutedfg"])

    # ---------- output ----------
    def render(self):
        defs = ["<defs>"]
        for name, col in C.items():
            defs.append(f'<marker id="ah-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                        f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
        defs.append(f'<pattern id="hatch-red" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                    f'<rect width="8" height="8" fill="{C["red"]}" opacity="0.08"/>'
                    f'<line x1="0" y1="0" x2="0" y2="8" stroke="{C["red"]}" stroke-width="2" opacity="0.35"/></pattern>')
        defs.append("</defs>")
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
                f'<title>{escape(self.title)}</title>')
        return head + "".join(defs) + "".join(self.el) + "</svg>"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render())
