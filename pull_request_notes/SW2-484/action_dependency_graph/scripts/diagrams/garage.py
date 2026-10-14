"""Top-down garage scene for the worked example, drawn with the reference pack's assets.

The drawing primitives (floor grid, corridors, parking stalls, customer bay with door, charger
bolt, AGV with wheels / lift plate / heading chevron, tray with rails, car silhouette, routes)
are adapted from the reference `facility.py`. The layout itself is SCHEMATIC: the Pecos YAML was
not part of the reference material, so node positions are invented in the Pecos naming style
(P = parking stall, W = waypoint, B = customer bay, C = AGV charger), using the Pecos XL stall
size (5.79 m x 2.21 m).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from components import chip, num_badge
from svgkit import BBox, Doc, pts_to_path
from theme import T, S

STALL_L, STALL_W = 5.79, 2.21          # Pecos XL parking window (m)
BAY_L, BAY_W = 5.79, 3.11              # bay = stall + 0.9 m, as in the reference drawing
C_PARK, C_BAY, C_CHG, C_WP = "#8FA3BF", T.teal, "#FACC15", T.fg2
CAR = "#CBD5E1"
TRAY = T.amber


@dataclass
class Node:
    id: str          # "W13", "P19", ...
    x: float
    y: float
    type: str        # Parking | Waypoint | Bay | AgvCharge
    axis: str = "x"  # long axis of a stall / bay
    door: str = ""   # bay door side: n | s | e | w
    used: bool = True   # part of the worked example graph?


# --------------------------------------------------------------------------------------
# Layout: the nine example vertices + a few context stalls that the example does not use
# --------------------------------------------------------------------------------------
NODES = {n.id: n for n in [
    Node("C10", 0.0, 0.0, "AgvCharge"),
    Node("W11", 4.0, 0.0, "Waypoint"),
    Node("W12", 8.0, 0.0, "Waypoint"),
    Node("W13", 12.0, 0.0, "Waypoint"),
    Node("W14", 16.0, 0.0, "Waypoint"),
    Node("P19", 21.2, 0.0, "Parking", axis="x"),
    Node("W8", 12.0, 4.0, "Waypoint"),
    Node("B7", 12.0, 8.9, "Bay", axis="y", door="s"),
    Node("P23", 12.0, -4.9, "Parking", axis="y"),
    # context only (not part of the example graph)
    Node("P21", 4.0, -4.9, "Parking", axis="y", used=False),
    Node("P22", 8.0, -4.9, "Parking", axis="y", used=False),
    Node("P24", 16.0, -4.9, "Parking", axis="y", used=False),
    Node("P20", 21.2, 2.4, "Parking", axis="x", used=False),
    Node("C14", 16.0, 4.0, "AgvCharge", used=False),
]}
EDGES = [("C10", "W11"), ("W11", "W12"), ("W12", "W13"), ("W13", "W14"), ("W14", "P19"),
         ("B7", "W8"), ("W8", "W13"), ("W13", "P23")]
CONTEXT_EDGES = [("W11", "P21"), ("W12", "P22"), ("W14", "P24"), ("W14", "C14")]
CORRIDORS = [("C10", "W14"), ("W8", "W13")]
XLIM, YLIM = (-2.6, 24.8), (-8.6, 12.9)


class Garage:
    def __init__(self, doc: Doc, ox: float, oy: float, scale: float, xlim=XLIM, ylim=YLIM):
        self.d, self.ox, self.oy, self.s = doc, ox, oy, scale
        self.xmin, self.xmax = xlim
        self.ymin, self.ymax = ylim

    def X(self, x):
        return self.ox + (x - self.xmin) * self.s

    def Y(self, y):
        return self.oy + (self.ymax - y) * self.s

    def P(self, v):
        if isinstance(v, str):
            n = NODES[v]
            return self.X(n.x), self.Y(n.y)
        return self.X(v[0]), self.Y(v[1])

    @property
    def box(self):
        return BBox(self.X(self.xmin), self.Y(self.ymax), self.X(self.xmax), self.Y(self.ymin))

    def visible(self, n, m=0.0):
        return self.xmin - m <= n.x <= self.xmax + m and self.ymin - m <= n.y <= self.ymax + m

    # ---- static scene -------------------------------------------------------------------
    def floor(self, *, axes=False, grid=True):
        d, b = self.d, self.box
        d.rect(b.x0, b.y0, b.w, b.h, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
        d.clip_on(b, rx=10)
        if grid:
            for gx in range(math.ceil(self.xmin), math.floor(self.xmax) + 1):
                major = gx % 5 == 0
                d.line(self.X(gx), b.y0 + 1, self.X(gx), b.y1 - 1, stroke="#253247" if major else T.grid,
                       sw=1 if major else 0.6, layer="bg", cap="butt")
            for gy in range(math.ceil(self.ymin), math.floor(self.ymax) + 1):
                major = gy % 5 == 0
                d.line(b.x0 + 1, self.Y(gy), b.x1 - 1, self.Y(gy), stroke="#253247" if major else T.grid,
                       sw=1 if major else 0.6, layer="bg", cap="butt")
        d.clip_off()
        if axes:
            d.line(b.x1 - 5 * self.s - 12, b.y1 + 14, b.x1 - 12, b.y1 + 14, stroke=T.muted, sw=1.4)
            for xx in (b.x1 - 5 * self.s - 12, b.x1 - 12):
                d.line(xx, b.y1 + 10, xx, b.y1 + 18, stroke=T.muted, sw=1.4)
            d.text(b.x1 - 2.5 * self.s - 12, b.y1 + 28, "5 m", size=S.tiny, family="mono", fill=T.muted,
                   anchor="middle")

    def corridors(self):
        w = STALL_W * self.s
        self.d.clip_on(self.box, rx=10)
        for a, b in CORRIDORS:
            (x0, y0), (x1, y1) = self.P(a), self.P(b)
            self.d.path(f"M{x0} {y0} L{x1} {y1}", stroke="#18233A", sw=w, cap="square", layer="bg",
                        bbox=BBox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        self.d.clip_off()

    def _rect_of(self, n, L, W):
        if n.axis == "x":
            w, h = L * self.s, W * self.s
        else:
            w, h = W * self.s, L * self.s
        x, y = self.P(n.id)
        return x - w / 2, y - h / 2, w, h

    def stalls(self, *, labels=True, highlight=()):
        d = self.d
        for n in NODES.values():
            if n.type != "Parking":
                continue
            x0, y0, w, h = self._rect_of(n, STALL_L, STALL_W)
            dim = not n.used
            hl = n.id in highlight
            d.rect(x0 + 1.5, y0 + 1.5, w - 3, h - 3, rx=4, fill=T.tint(C_PARK, 0.06 if dim else 0.10, T.bg_deep),
                   stroke=C_PARK if hl else T.tint(C_PARK, 0.32 if dim else 0.55, T.bg_deep), sw=2 if hl else 1.2,
                   layer="under")
            if labels:
                d.text(x0 + 8, y0 + 12, n.id, size=11, family="mono", weight=600,
                       fill=T.tint(C_PARK, 0.55 if dim else 0.9, T.bg_deep), layer="labels", halo=T.bg_deep, halo_w=3)

    def bays(self, *, labels=True):
        d = self.d
        for n in NODES.values():
            if n.type != "Bay":
                continue
            x0, y0, w, h = self._rect_of(n, BAY_L, BAY_W)
            d.rect(x0, y0, w, h, rx=8, fill=T.tint(C_BAY, 0.12, T.bg_deep), stroke=C_BAY, sw=1.6, layer="under")
            if n.door == "s":
                d.line(x0 + 6, y0 + h, x0 + w - 6, y0 + h, stroke=C_BAY, sw=4.5, layer="under")
            elif n.door == "e":
                d.line(x0 + w, y0 + 6, x0 + w, y0 + h - 6, stroke=C_BAY, sw=4.5, layer="under")
            if labels:
                d.text(x0 + 8, y0 + 13, n.id, size=12, family="mono", weight=700, fill=C_BAY, layer="labels",
                       halo=T.bg_deep, halo_w=3)

    def edges(self, *, color="#55657F", sw=1.5, context=True):
        for a, b in EDGES:
            (x0, y0), (x1, y1) = self.P(a), self.P(b)
            self.d.line(x0, y0, x1, y1, stroke=color, sw=sw, layer="edges")
        if context:
            for a, b in CONTEXT_EDGES:
                (x0, y0), (x1, y1) = self.P(a), self.P(b)
                self.d.line(x0, y0, x1, y1, stroke="#334155", sw=1.1, dash="3 4", layer="edges")

    def nodes(self, *, labels=True, highlight=(), wp_below=False):
        d = self.d
        for n in NODES.values():
            x, y = self.P(n.id)
            dim = not n.used
            if n.type == "Waypoint":
                hl = n.id in highlight
                d.circle(x, y, 6.5 if hl else 4.5, fill=T.teal if hl else C_WP, stroke=T.bg_deep, sw=1.5, layer="over")
                if labels and wp_below and n.id != "W8":
                    d.text(x, y + 1.45 * self.s, n.id, size=10.5, family="mono", weight=600 if hl else 400,
                           fill=T.teal if hl else T.muted, anchor="middle", halo=T.bg_deep, halo_w=3.5, layer="labels")
                elif labels:
                    d.text(x - 8, y - 11, n.id, size=10.5, family="mono", weight=600 if hl else 400,
                           fill=T.teal if hl else T.muted, anchor="end", halo=T.bg_deep, halo_w=3.5, layer="labels")
            elif n.type in ("Parking", "Bay"):
                d.circle(x, y, 2.8, fill=T.tint(C_BAY if n.type == "Bay" else C_PARK, 0.4 if dim else 0.85,
                                                  T.bg_deep), layer="over")
            elif n.type == "AgvCharge":
                r = max(9, 0.36 * self.s)
                op = 0.5 if dim else None
                d.circle(x, y, r, fill=T.tint(C_CHG, 0.25, T.bg_deep), stroke=C_CHG, sw=1.6, layer="over", opacity=op)
                bolt = [(x + 0.12 * r, y - 0.62 * r), (x - 0.38 * r, y + 0.1 * r), (x - 0.02 * r, y + 0.1 * r),
                        (x - 0.14 * r, y + 0.62 * r), (x + 0.38 * r, y - 0.12 * r), (x + 0.02 * r, y - 0.12 * r)]
                d.polygon(bolt, fill=C_CHG, layer="over", join="round", opacity=op)
                if labels:
                    d.text(x - 1.25 * self.s, y + 4, n.id, size=11, family="mono", weight=600, fill=C_CHG, anchor="end",
                           halo=T.bg_deep, halo_w=3.5, layer="labels", opacity=op)

    def base(self, *, labels=True, highlight=(), axes=True, context=True, wp_below=False):
        self.floor(axes=axes)
        self.corridors()
        self.d.clip_on(self.box, rx=10)
        self.stalls(labels=labels, highlight=highlight)
        self.bays(labels=labels)
        self.edges(context=context)
        self.nodes(labels=labels, highlight=highlight, wp_below=wp_below)
        self.d.clip_off()

    # ---- entities -----------------------------------------------------------------------
    def tray(self, at, label=None, *, axis="x", color=TRAY, payload=False, dim=False):
        d = self.d
        x, y = self.P(at)
        L, W = (STALL_L - 0.5) * self.s, (STALL_W - 0.32) * self.s
        w, h = (L, W) if axis == "x" else (W, L)
        op = 0.55 if dim else None
        d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill=T.tint(color, 0.20, T.bg_deep), stroke=color, sw=1.6,
               layer="main", opacity=op)
        for f in (-0.28, 0.28):
            if axis == "x":
                d.line(x - w / 2 + 6, y + f * h, x + w / 2 - 6, y + f * h, stroke=T.tint(color, 0.45, T.bg_deep),
                       sw=1, layer="main", opacity=op)
            else:
                d.line(x + f * w, y - h / 2 + 6, x + f * w, y + h / 2 - 6, stroke=T.tint(color, 0.45, T.bg_deep),
                       sw=1, layer="main", opacity=op)
        if payload:
            self.car(x, y, w * (0.78 if axis == "x" else 0.72), h * (0.72 if axis == "x" else 0.78), axis=axis,
                     dim=dim)
        if label:
            chip(d, x - w / 2 + 2, y + h / 2 + 10, label, color, anchor="start", size=10,
                 fill=T.tint(color, 0.3, T.bg_deep), layer="labels")

    def car(self, x, y, w, h, *, axis="x", color=CAR, dim=False):
        d = self.d
        op = 0.55 if dim else None
        r = (h if axis == "x" else w) * 0.42
        d.rect(x - w / 2, y - h / 2, w, h, rx=r, fill=T.tint(color, 0.28, T.bg_deep), stroke=color, sw=1.3,
               layer="main", opacity=op)
        if axis == "x":
            d.rect(x - w / 2 + w * 0.2, y - h / 2 + h * 0.16, w * 0.14, h * 0.68, rx=3,
                   fill=T.tint(color, 0.55, T.bg_deep), layer="main", opacity=op)
        else:
            d.rect(x - w / 2 + w * 0.16, y - h / 2 + h * 0.2, w * 0.68, h * 0.14, rx=3,
                   fill=T.tint(color, 0.55, T.bg_deep), layer="main", opacity=op)

    def agv(self, at, label=None, *, heading="e", color=T.green, label_side="below", lifted=False, ghost=False,
            size=1.0):
        """Top-down AGV (2.2 m x 1.1 m). heading: e | w | n | s (direction of travel)."""
        d = self.d
        x, y = self.P(at)
        L, Wd = 2.2 * self.s * size, 1.1 * self.s * size
        ang = {"e": 0, "w": 180, "n": -90, "s": 90}[heading]
        hx, hy = L / 2, Wd / 2
        ww = max(3.0, 0.11 * self.s * size)
        wheel = "".join(f'<rect x="{px:.1f}" y="{py:.1f}" width="{0.2 * L:.1f}" height="{ww:.1f}" rx="1.5" fill="#CBD5E1"/>'
                        for px in (-hx + 0.16 * L, hx - 0.36 * L) for py in (-hy - ww * 0.6, hy - ww * 0.4))
        fill = T.tint(color, 0.22, T.bg_deep)
        body = (f'<rect x="{-hx:.1f}" y="{-hy:.1f}" width="{L:.1f}" height="{Wd:.1f}" rx="{Wd * 0.28:.1f}" '
                f'fill="{fill}" stroke="{color}" stroke-width="2"/>')
        plate = (f'<rect x="{-hx + 0.3 * L:.1f}" y="{-hy + 0.22 * Wd:.1f}" width="{0.4 * L:.1f}" height="{0.56 * Wd:.1f}" '
                 f'rx="3" fill="{T.tint(color, 0.5 if lifted else 0.3, T.bg_deep)}" '
                 f'stroke="{T.tint(color, 0.7, T.bg_deep)}" stroke-width="1"/>')
        chev = (f'<path d="M{hx - 0.2 * L:.1f} {-0.26 * Wd:.1f} L{hx - 0.06 * L:.1f} 0 L{hx - 0.2 * L:.1f} {0.26 * Wd:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
        dash = ' stroke-dasharray="4 3"' if ghost else ""
        if lifted:   # carrying a tray: the AGV is underneath, draw it as an outline so the load stays visible
            body = (f'<rect x="{-hx:.1f}" y="{-hy:.1f}" width="{L:.1f}" height="{Wd:.1f}" rx="{Wd * 0.28:.1f}" '
                    f'fill="none" stroke="{color}" stroke-width="2.4"/>')
            wheel = plate = ""
        if ghost:
            body = (f'<rect x="{-hx:.1f}" y="{-hy:.1f}" width="{L:.1f}" height="{Wd:.1f}" rx="{Wd * 0.28:.1f}" '
                    f'fill="none" stroke="{color}" stroke-width="1.6"{dash}/>')
            wheel = plate = ""
        d.raw(f'<g transform="translate({x:.2f} {y:.2f}) rotate({ang})">{wheel}{body}{plate}{chev}</g>', "top",
              BBox(x - L / 2 - 4, y - L / 2 - 4, x + L / 2 + 4, y + L / 2 + 4))
        if label:
            off = {"below": (0, Wd / 2 + 16 if heading in "ew" else L / 2 + 14),
                   "above": (0, -(Wd / 2 + 16 if heading in "ew" else L / 2 + 14)),
                   "left": (-(L / 2 + 8 if heading in "ew" else Wd / 2 + 10), 0),
                   "right": ((L / 2 + 8 if heading in "ew" else Wd / 2 + 10), 0)}[label_side]
            anchor = {"below": "middle", "above": "middle", "left": "end", "right": "start"}[label_side]
            chip(d, x + off[0], y + off[1], label, color, anchor=anchor, size=10.5, fill=T.tint(color, 0.25, T.bg_deep),
                 layer="top")
        return x, y

    def route(self, verts, color, *, sw=3.2, dash=None, offset=0.0, head=True, layer="over"):
        """Route along vertices, offset sideways by `offset` px (positive = right of travel)."""
        pts = [self.P(v) for v in verts]
        if offset:
            pts = offset_poly(pts, offset)
        d = self.d
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
        Lh = math.hypot(xb - xa, yb - ya)
        hl = 12
        end = (xb - (xb - xa) / Lh * hl * 0.8, yb - (yb - ya) / Lh * hl * 0.8) if head else pts[-1]
        body = pts[:-1] + [end]
        d.path(pts_to_path(body, 8), stroke=T.bg_deep, sw=sw + 3.5, layer=layer, opacity=0.85)
        d.path(pts_to_path(body, 8), stroke=color, sw=sw, dash=dash, layer=layer)
        if head:
            d.arrowhead((xb, yb), (xa, ya), kind="filled", color=color, size=hl, layer=layer)
        return pts


def offset_poly(pts, o):
    segs = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        dx, dy = (x1 - x0) / L, (y1 - y0) / L
        segs.append(((x0 - dy * o, y0 + dx * o), (x1 - dy * o, y1 + dx * o), (dx, dy)))
    out = [segs[0][0]]
    for (a0, a1, da), (b0, b1, db) in zip(segs, segs[1:]):
        if abs(da[0] * db[1] - da[1] * db[0]) < 1e-6:
            out.append(a1)
        elif abs(da[0]) > 0.5:
            out.append((b0[0], a0[1]))
        else:
            out.append((a0[0], b0[1]))
    out.append(segs[-1][1])
    return out


def heading_between(u, v):
    a, b = NODES[u], NODES[v]
    if abs(b.x - a.x) >= abs(b.y - a.y):
        return "e" if b.x > a.x else "w"
    return "n" if b.y > a.y else "s"


def node_axis(v):
    n = NODES[v]
    return n.axis if n.type in ("Parking", "Bay") else "x"
