"""Reusable 'how to read this figure' keys, so every symbol in every figure is explained on the
figure itself."""
from __future__ import annotations

from components import connect
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T
import example as ex

AR = "→"


def key_panel(d: Doc, x, y, w, title, rows, *, accent=T.border):
    """rows: list of (term, explanation, color). Two-column glossary in a framed panel.
    Returns its bbox."""
    pad = 14
    tw = max(text_width(t, 12, "mono", 600) for t, _, _ in rows) + 16
    lines = []
    for term, expl, col in rows:
        lines.append((term, wrap(expl, w - 2 * pad - tw, 12, "sans"), col))
    h = pad + 22 + sum(len(l) * 17 + 6 for _, l, _ in lines) + pad - 6
    d.rect(x, y, w, h, rx=10, fill=T.tint(T.card, 0.7, T.bg), stroke=accent, sw=1.1, layer="under")
    d.text(x + pad, y + pad + 4, title.upper(), size=10.5, family="mono", weight=600, fill=T.muted,
           letter_spacing=0.8)
    yy = y + pad + 26
    for term, ls, col in lines:
        d.text(x + pad, yy + 6, term, size=12, family="mono", weight=600, fill=col or T.fg)
        for i, ln in enumerate(ls):
            d.text(x + pad + tw, yy + 6 + i * 17, ln, size=12, fill=T.fg2)
        yy += len(ls) * 17 + 6
    return BBox(x, y, x + w, y + h)


def names_rows(robots=True, vertices=True):
    rows = []
    if vertices:
        rows += [("W18", "a waypoint (W) on the aisle; P = parking stall, B = customer bay, C = AGV charger. "
                         "The number is just the place's id.", T.fg2),
                 ("W22", "the junction: the only place all four routes share", T.teal)]
    if robots:
        rows += [("AGV-1, 3, 4", "three AGVs driving north up the aisle in a convoy", T.fg2),
                 ("AGV-2", "an AGV crossing the junction, carrying a customer's car on its tray", T.violet)]
    return rows


def action_rows(wait=True, t1=True, t2=True):
    rows = [("A3-2", "an action: AGV-3's step number 2 of the plan (t = 2); A = AGV, then AGV number, then step", T.green),
            (f"W18 {AR} W22", "inside a box: where that step starts and where it ends", T.fg2)]
    if wait:
        rows.append(("wait W18", "a wait action (dashed box): start = goal, the AGV stays put", T.fg2))
    if t1:
        rows.append((f"A3-0 {AR} A3-2", "type-1 edge (lane colour): the same AGV does its steps in order", T.green))
    if t2:
        rows.append((f"A2-2 {AR} A3-2", "type-2 edge (light): A3-2 may start only after A2-2 has completed. The pill "
                                    "names the place handed over: A2-2 leaves it, A3-2 enters it", T.fg2))
    return rows
