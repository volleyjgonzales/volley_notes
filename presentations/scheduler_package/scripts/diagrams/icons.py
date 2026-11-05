"""Small line icons for the diagrams (centred at x, y; s = nominal size in px).

Each icon is drawn with one colour so it can follow the figure's colour roles. Shapes:
file (config file on disk), process (a running OS process / window), node (a ROS node), person (patron),
agv (top view), bay (bay with a door), clock, bolt (charger), lift (VRC), gear (software), record (recording),
eye (watch), terminal (command line), launch (rocket-like launch file), warn (problem).
"""
from __future__ import annotations

from svgkit import BBox, Doc
from theme import T


def file(d: Doc, x, y, s=22, col=T.fg2, fill=None):
    w, h, f = s * 0.78, s, s * 0.28
    x0, y0 = x - w / 2, y - h / 2
    d.path(f"M{x0} {y0} L{x0 + w - f} {y0} L{x0 + w} {y0 + f} L{x0 + w} {y0 + h} L{x0} {y0 + h} Z",
           fill=fill or T.tint(col, 0.14, T.bg), stroke=col, sw=1.4)
    d.path(f"M{x0 + w - f} {y0} L{x0 + w - f} {y0 + f} L{x0 + w} {y0 + f}", stroke=col, sw=1.2)
    for i in range(3):
        yy = y0 + h * (0.45 + 0.17 * i)
        d.line(x0 + w * 0.2, yy, x0 + w * (0.8 if i < 2 else 0.55), yy, stroke=col, sw=1.1)


def process(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 1.15, s * 0.9
    x0, y0 = x - w / 2, y - h / 2
    d.rect(x0, y0, w, h, rx=3, fill=T.tint(col, 0.14, T.bg), stroke=col, sw=1.4)
    d.line(x0, y0 + h * 0.28, x0 + w, y0 + h * 0.28, stroke=col, sw=1.2)
    for i in range(3):
        d.circle(x0 + 4 + i * 4.5, y0 + h * 0.14, 1.2, fill=col)
    # running indicator: a play triangle
    cx, cy = x, y0 + h * 0.64
    d.polygon([(cx - 3.5, cy - 4.5), (cx - 3.5, cy + 4.5), (cx + 5, cy)], fill=col)


def node(d: Doc, x, y, s=14, col=T.fg2):
    r = s / 2
    d.circle(x, y, r, fill=T.tint(col, 0.18, T.bg), stroke=col, sw=1.5)
    d.circle(x, y, r * 0.38, fill=col)


def person(d: Doc, x, y, s=22, col=T.fg2):
    d.circle(x, y - s * 0.25, s * 0.18, fill="none", stroke=col, sw=1.5)
    d.path(f"M{x - s * 0.32} {y + s * 0.42} Q{x - s * 0.3} {y - s * 0.02} {x} {y - s * 0.02} "
           f"Q{x + s * 0.3} {y - s * 0.02} {x + s * 0.32} {y + s * 0.42}", stroke=col, sw=1.5)


def agv(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 1.2, s * 0.62
    d.rect(x - w / 2, y - h / 2, w, h, rx=3, fill=T.tint(col, 0.16, T.bg), stroke=col, sw=1.4)
    for dx in (-w * 0.32, w * 0.18):
        d.rect(x + dx, y - h / 2 - 2.5, w * 0.16, 2.5, fill=col)
        d.rect(x + dx, y + h / 2, w * 0.16, 2.5, fill=col)
    d.path(f"M{x - 2} {y - h * 0.22} L{x + 4} {y} L{x - 2} {y + h * 0.22}", stroke=col, sw=1.5)


def bay(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 1.1, s * 0.85
    x0, y0 = x - w / 2, y - h / 2
    d.path(f"M{x0} {y0 + h} L{x0} {y0} L{x0 + w} {y0} L{x0 + w} {y0 + h}", stroke=col, sw=1.5)
    d.rect(x0 + w * 0.22, y0 + h * 0.3, w * 0.56, h * 0.7, fill=T.tint(col, 0.16, T.bg), stroke=col, sw=1.2)
    d.line(x0 - 2, y0 + h, x0 + w + 2, y0 + h, stroke=col, sw=1.5)


def clock(d: Doc, x, y, s=22, col=T.fg2):
    r = s * 0.45
    d.circle(x, y, r, fill=T.tint(col, 0.12, T.bg), stroke=col, sw=1.5)
    d.line(x, y, x, y - r * 0.62, stroke=col, sw=1.5)
    d.line(x, y, x + r * 0.45, y + r * 0.2, stroke=col, sw=1.5)


def bolt(d: Doc, x, y, s=22, col=T.fg2):
    k = s / 20
    pts = [(x + 2 * k, y - 10 * k), (x - 6 * k, y + 1 * k), (x - 0.5 * k, y + 1 * k), (x - 3 * k, y + 10 * k),
           (x + 6 * k, y - 2 * k), (x + 0.5 * k, y - 2 * k)]
    d.polygon(pts, fill=col, join="round")


def lift(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 0.8, s
    d.rect(x - w / 2, y - h / 2, w, h, rx=2, fill=T.tint(col, 0.12, T.bg), stroke=col, sw=1.4)
    d.line(x, y - h * 0.3, x, y + h * 0.3, stroke=col, sw=1.4)
    d.arrowhead((x, y - h * 0.36), (x, y), kind="filled", color=col, size=6)
    d.arrowhead((x, y + h * 0.36), (x, y), kind="filled", color=col, size=6)


def gear(d: Doc, x, y, s=22, col=T.fg2):
    import math
    r0, r1 = s * 0.32, s * 0.46
    pts = []
    for i in range(16):
        a = i * math.pi / 8
        r = r1 if i % 2 == 0 else r0
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    d.polygon(pts, fill=T.tint(col, 0.16, T.bg), stroke=col, sw=1.3, join="round")
    d.circle(x, y, s * 0.13, fill=T.bg, stroke=col, sw=1.3)


def record(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 0.8, s
    e = h * 0.16
    x0, y0 = x - w / 2, y - h / 2
    d.path(f"M{x0} {y0 + e} L{x0} {y0 + h - e} A{w / 2} {e} 0 0 0 {x0 + w} {y0 + h - e} L{x0 + w} {y0 + e}",
           fill=T.tint(col, 0.14, T.bg), stroke=col, sw=1.4, bbox=BBox(x0, y0, x0 + w, y0 + h))
    d.path(f"M{x0} {y0 + e} A{w / 2} {e} 0 0 0 {x0 + w} {y0 + e} A{w / 2} {e} 0 0 0 {x0} {y0 + e}",
           fill=T.tint(col, 0.25, T.bg), stroke=col, sw=1.4, bbox=BBox(x0, y0, x0 + w, y0 + 2 * e))


def eye(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 0.55, s * 0.3
    d.path(f"M{x - w} {y} Q{x} {y - h * 2} {x + w} {y} Q{x} {y + h * 2} {x - w} {y} Z",
           fill=T.tint(col, 0.12, T.bg), stroke=col, sw=1.4)
    d.circle(x, y, s * 0.13, fill=col)


def terminal(d: Doc, x, y, s=22, col=T.fg2):
    w, h = s * 1.15, s * 0.85
    d.rect(x - w / 2, y - h / 2, w, h, rx=3, fill=T.tint(col, 0.12, T.bg), stroke=col, sw=1.4)
    d.path(f"M{x - w * 0.3} {y - h * 0.18} L{x - w * 0.12} {y} L{x - w * 0.3} {y + h * 0.18}", stroke=col, sw=1.4)
    d.line(x - w * 0.02, y + h * 0.2, x + w * 0.28, y + h * 0.2, stroke=col, sw=1.4)


def launch(d: Doc, x, y, s=22, col=T.fg2):
    """A launch file: a document with a play mark."""
    file(d, x, y, s, col)
    d.polygon([(x - 2, y + s * 0.02), (x - 2, y + s * 0.3), (x + 5, y + s * 0.16)], fill=col)


def warn(d: Doc, x, y, s=20, col=T.red):
    d.polygon([(x, y - s * 0.45), (x + s * 0.5, y + s * 0.4), (x - s * 0.5, y + s * 0.4)],
              fill=T.tint(col, 0.2, T.bg), stroke=col, sw=1.4, join="round")
    d.line(x, y - s * 0.12, x, y + s * 0.12, stroke=col, sw=1.6)
    d.circle(x, y + s * 0.26, 1.3, fill=col)


DRAW = {"file": file, "process": process, "node": node, "person": person, "agv": agv, "bay": bay,
        "clock": clock, "bolt": bolt, "lift": lift, "gear": gear, "record": record, "eye": eye,
        "terminal": terminal, "launch": launch, "warn": warn}


def icon(d: Doc, kind: str, x, y, s=22, col=T.fg2):
    DRAW[kind](d, x, y, s, col)
