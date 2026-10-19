"""Doc 05 (action dependency graph primer): figures 84-87.

84 why timestamps are not enough (delay), 85 building an ADG from a timed plan (Hönig et al. 2019
construction), 86 timing on an ADG: earliest start, critical path, slack, 87 the ADG the scheduler
builds in ResponseFromTrajectories (illustrative example, edge kinds as in src/scheduler.cpp).
"""
from __future__ import annotations

import math
import re

from components import connect, frame, label_pill, note
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S

DOC5 = "05-adg-primer.html"
A1, A2, A3 = T.sky, T.pink, T.violet          # agents
T1, T2, TE, RED = T.green, T.amber, T.violet, T.red   # type 1, type 2, event-level, conflict


def vnode(d: Doc, cx, cy, title, sub, color, *, w=150, h=50, fill=None, sw=1.6, hl=False):
    x, y = cx - w / 2, cy - h / 2
    d.rect(x, y, w, h, rx=9, fill=fill or (T.tint(color, 0.16, T.bg) if hl else T.card), stroke=color, sw=sw)
    d.text(cx, cy - 9, title, size=12.5, family="mono", weight=700, fill=T.fg, anchor="middle")
    d.text(cx, cy + 10, sub, size=11, family="mono", fill=T.fg2, anchor="middle")
    return BBox(x, y, x + w, y + h)


def _edge_pt(b: BBox, tx, ty):
    """Point on the border of b along the ray from its centre towards (tx, ty)."""
    cx, cy = b.cx, b.cy
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (b.w / 2) / abs(dx) if dx else math.inf
    sy = (b.h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def arrow(d: Doc, a: BBox, b: BBox, color, *, dash=None, sw=1.7, label=None, label_at=None, via=None):
    if via:
        p0 = _edge_pt(a, *via[0])
        p1 = _edge_pt(b, *via[-1])
        pts = [p0, *via, p1]
    else:
        p0 = _edge_pt(a, b.cx, b.cy)
        p1 = _edge_pt(b, a.cx, a.cy)
        pts = [p0, p1]
    connect(d, pts, kind="flow", color=color, sw=sw, dash=dash, size=9, label=label, label_at=label_at)


def _axis(d: Doc, x0, y, px, t0, t1, step=1, label="t"):
    d.line(x0, y, x0 + (t1 - t0) * px, y, stroke=T.border, sw=1)
    t = t0
    while t <= t1 + 1e-9:
        x = x0 + (t - t0) * px
        d.line(x, y, x, y + 5, stroke=T.border, sw=1)
        d.text(x, y + 16, f"{t:g}", size=10.5, family="mono", fill=T.muted, anchor="middle")
        t += step
    d.text(x0 + (t1 - t0) * px + 14, y + 4, label, size=11, family="mono", fill=T.muted)


def _bar(d: Doc, x0, px, row_y, t0, t1, text, color, *, h=26, dash=None, fill_a=0.22):
    x = x0 + t0 * px
    w = (t1 - t0) * px
    d.rect(x, row_y - h / 2, w, h, rx=5, fill=T.tint(color, fill_a, T.bg), stroke=color, sw=1.3, dash=dash)
    if text_width(text, 11, "mono") < w - 8:
        d.text(x + w / 2, row_y, text, size=11, family="mono", fill=T.fg, anchor="middle")
    else:
        d.text(x + w / 2, row_y - h / 2 - 8, text, size=11, family="mono", fill=T.fg2, anchor="middle")


# ======================================================================================
# 84 — why timestamps are not enough
# ======================================================================================

@figure("84_adg_delay", "Why a timed plan needs an ADG", DOC5)
def adg_delay():
    d = Doc("84_adg_delay", "Why a timed plan needs an ADG",
            "Three Gantt panels for two AGVs crossing cell B: the plan, execution by the clock after a delay "
            "(both AGVs in B), and execution by dependencies (AGV 2 waits).")
    px = 110
    x0 = 170
    panels = [
        ("1  The plan", [(A1, "AGV 1", [(0, 1, "A->B"), (1, 2, "B->C")]),
                         (A2, "AGV 2", [(2, 3, "D->B"), (3, 4, "B->E")])], None, None),
        ("2  Execute by the clock: AGV 1's first move takes 2.5 instead of 1", [
            (A1, "AGV 1", [(0, 2.5, "A->B (slow)"), (2.5, 3.5, "B->C")]),
            (A2, "AGV 2", [(2, 3, "D->B"), (3, 4, "B->E")])], (2.5, 3.0), None),
        ("3  Execute by dependencies: D->B may start only after B->C has finished", [
            (A1, "AGV 1", [(0, 2.5, "A->B (slow)"), (2.5, 3.5, "B->C")]),
            (A2, "AGV 2", [(3.5, 4.5, "D->B"), (4.5, 5.5, "B->E")])], None, (3.5, 2.0)),
    ]
    y = 0
    for title, rows, conflict, wait in panels:
        d.text(0, y, title, size=14, weight=600, fill=T.fg)
        ry = y + 40
        for i, (col, name, bars) in enumerate(rows):
            yy = ry + i * 40
            d.text(0, yy, name, size=12.5, family="mono", weight=600, fill=col)
            d.line(x0, yy, x0 + 6 * px, yy, stroke=T.grid, sw=1)
            for t0, t1, lab in bars:
                _bar(d, x0, px, yy, t0, t1, lab, col)
        if conflict:
            cx0, cx1 = x0 + conflict[0] * px, x0 + conflict[1] * px
            d.rect(cx0, ry - 22, cx1 - cx0, 84, fill=T.tint(RED, 0.22, T.bg), stroke=RED, sw=1.4, dash="4 3",
                   layer="over")
            d.text(x0 + 4.1 * px, ry + 20, "AGV 1 is still in B (until B->C ends)", size=11.5, fill=RED)
            d.text(x0 + 4.1 * px, ry + 36, "while AGV 2 drives into B", size=11.5, fill=RED)
        if wait:
            t_end, t_plan = wait
            d.line(x0 + t_plan * px, ry + 40, x0 + t_end * px, ry + 40, stroke=T2, sw=2, dash="4 3")
            d.text(x0 + (t_plan + t_end) / 2 * px, ry + 40 - 18, "waits 1.5", size=11, fill=T2, anchor="middle")
            connect(d, [(x0 + 3.5 * px - 2, ry + 13), (x0 + 3.5 * px - 2, ry + 27)], kind="flow", color=T2, size=7)
        _axis(d, x0, ry + 70, px, 0, 6, label="t [s]")
        y = ry + 130
    # map
    mx, my = x0 + 6 * px + 120, 90
    pos = {"A": (0, 1), "B": (1, 1), "C": (2, 1), "D": (1, 0), "E": (1, 2)}
    s = 70
    for k, (gx, gy) in pos.items():
        for k2, (hx, hy) in pos.items():
            if k < k2 and abs(gx - hx) + abs(gy - hy) == 1:
                d.line(mx + gx * s, my + gy * s, mx + hx * s, my + hy * s, stroke=T.border, sw=2)
    for k, (gx, gy) in pos.items():
        d.circle(mx + gx * s, my + gy * s, 16, fill=T.card, stroke=T.fg2 if k != "B" else RED, sw=1.6)
        d.text(mx + gx * s, my + gy * s, k, size=13, family="mono", weight=700, fill=T.fg, anchor="middle")
    d.text(mx - 20, my - 66, "Map: AGV 1 goes A -> B -> C,", size=11.5, fill=A1)
    d.text(mx - 20, my - 50, "AGV 2 goes D -> B -> E", size=11.5, fill=A2)
    frame(d, title="Why a timed plan is not enough",
          subtitle="A planner hands out times. Real AGVs are late or early. Executing by the clock lets a late "
                   "robot collide with one that is on time; executing by dependencies keeps the planned order "
                   "and lets the times slide.",
          badge_key="illustrative",
          legend=[("box", A1, "AGV 1"), ("box", A2, "AGV 2"), ("dashbox", RED, "both in cell B"),
                  ("dash", T2, "waiting for a dependency")],
          footnote="Unit-time moves on a five-cell map; an AGV occupies its start cell until its move ends.")
    return d


# ======================================================================================
# 85 — building an ADG from a timed plan
# ======================================================================================

def sym(d: Doc, x, y, base, sup=None, sub=None, *, size=15, fill=T.fg, anchor="start", sup_italic=True,
        sub_italic=True, layer="labels"):
    """A math symbol drawn like TeX: italic base, superscript and subscript stacked on the right."""
    bw = text_width(base, size, "sans", 400, "italic")
    scr = size * 0.66
    ws = max(text_width(sup or "", scr, "sans", 400, "italic" if sup_italic else "normal"),
             text_width(sub or "", scr, "sans", 400, "italic" if sub_italic else "normal"))
    total = bw + (2 + ws if (sup or sub) else 0)
    x0 = x - total / 2 if anchor == "middle" else (x - total if anchor == "end" else x)
    d.text(x0, y, base, size=size, style="italic", fill=fill, layer=layer)
    if sup:
        d.text(x0 + bw + 2, y - size * 0.36, sup, size=scr, style="italic" if sup_italic else "normal", fill=fill,
               layer=layer, allow_overlap=True)
    if sub:
        d.text(x0 + bw + 2, y + size * 0.32, sub, size=scr, style="italic" if sub_italic else "normal", fill=fill,
               layer=layer, allow_overlap=True)
    return BBox(x0, y - size * 0.7, x0 + total, y + size * 0.6)


def mathline(d: Doc, x, y, parts, *, size=14, fill=T.fg, layer="labels"):
    """Draw a sequence of plain-text runs ("text") and symbols (("sym", base, sup, sub)) left to right."""
    cx = x
    for p in parts:
        if isinstance(p, str):
            d.text(cx, y, p, size=size, fill=fill, layer=layer)
            cx += text_width(p, size, "sans")
        elif p[0] == "op":
            # glyphs the latin font subset lacks, drawn as vectors: -> (arrow), <= , !=
            w = size * 0.9
            if p[1] == "to":
                d.line(cx + 2, y, cx + w * 1.3 - 6, y, stroke=fill, sw=1.3, layer=layer)
                d.arrowhead((cx + w * 1.3, y), (cx, y), kind="filled", color=fill, size=size * 0.45, layer=layer)
                cx += w * 1.3 + 3
            else:
                ch = "<" if p[1] == "le" else "="
                d.text(cx + 2, y, ch, size=size, fill=fill, layer=layer)
                cw = text_width(ch, size, "sans")
                if p[1] == "le":
                    d.line(cx + 3, y + size * 0.42, cx + 2 + cw, y + size * 0.42, stroke=fill, sw=1.2, layer=layer)
                else:
                    d.line(cx + 2 + cw * 0.7, y - size * 0.38, cx + 2 + cw * 0.3, y + size * 0.38, stroke=fill,
                           sw=1.2, layer=layer)
                cx += cw + 5
        else:
            _, base, sup, sub = p[:4]
            bb = sym(d, cx, y, base, sup, sub, size=size, fill=fill, layer=layer,
                     sup_italic=not (sup or "").isdigit(), sub_italic=not (sub or "").isdigit())
            cx = bb.x1 + 1
    return cx


def mtext(d: Doc, x, y, s, *, size=12, fill=T.fg2):
    """Plain text in which every a[i,k] is drawn as the symbol a with superscript i and subscript k."""
    parts = []
    pos = 0
    for m in re.finditer(r"a\[(\d+),(\d+)\]", s):
        if m.start() > pos:
            parts.append(s[pos:m.start()])
        parts.append(("sym", "a", m.group(1), m.group(2)))
        pos = m.end()
    if pos < len(s):
        parts.append(s[pos:])
    return mathline(d, x, y, parts, size=size, fill=fill)


def anode(d: Doc, cx, cy, i, k, move, t, color, *, w=150, h=56, hl=False, sw=1.6, status=None):
    """An ADG vertex: the action symbol a^i_k on top, 'start -> goal, t = ..' below."""
    x, y = cx - w / 2, cy - h / 2
    fill = T.tint(color, 0.16, T.bg) if hl else T.card
    if status:
        fill = {"staged": T.card, "enqueued": T.tint(T.amber, 0.22, T.bg), "finished": T.tint(T.green, 0.25, T.bg)}[status]
    d.rect(x, y, w, h, rx=9, fill=fill, stroke=color, sw=sw)
    sym(d, cx, cy - 10, "a", str(i), str(k), size=17, anchor="middle", sup_italic=False, sub_italic=False)
    d.text(cx, cy + 15, f"{move}, t = {t}", size=11, family="mono", fill=T.fg2, anchor="middle")
    return BBox(x, y, x + w, y + h)


CELLS = {"A": (0, 1), "B": (1, 1), "C": (2, 1), "F": (3, 1), "D": (1, 0), "E": (1, 2)}
PLANS = {1: [(0, "A", "B"), (1, "B", "C")], 2: [(2, "D", "B"), (3, "B", "E")], 3: [(0, "C", "F")]}
ACOL = {1: A1, 2: A2, 3: A3}


def _cell_map(d: Doc, mx, my, s, *, paths=True):
    for k, (gx, gy) in CELLS.items():
        for k2, (hx, hy) in CELLS.items():
            if k < k2 and abs(gx - hx) + abs(gy - hy) == 1:
                d.line(mx + gx * s, my + gy * s, mx + hx * s, my + hy * s, stroke=T.border, sw=2)
    if paths:
        offs = {1: (0, -9), 2: (-9, 0), 3: (0, 9)}
        for i, acts in PLANS.items():
            ox, oy = offs[i]
            for k, (t, s0, g0) in enumerate(acts, 1):
                (ax_, ay_), (bx_, by_) = CELLS[s0], CELLS[g0]
                p0 = (mx + ax_ * s + ox, my + ay_ * s + oy)
                p1 = (mx + bx_ * s + ox, my + by_ * s + oy)
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                L = math.hypot(dx, dy)
                ux, uy = dx / L, dy / L
                q0 = (p0[0] + ux * 20, p0[1] + uy * 20)
                q1 = (p1[0] - ux * 20, p1[1] - uy * 20)
                connect(d, [q0, q1], kind="flow", color=ACOL[i], sw=2.2, size=8)
    for k, (gx, gy) in CELLS.items():
        d.circle(mx + gx * s, my + gy * s, 17, fill=T.card, stroke=T.fg2, sw=1.6, layer="over")
        d.text(mx + gx * s, my + gy * s, k, size=13, weight=600, fill=T.fg, anchor="middle", layer="top")


@figure("85_adg_construction", "Building an ADG", DOC5)
def adg_construction():
    d = Doc("85_adg_construction", "Building an action dependency graph",
            "Three AGVs on a six-cell map with timed plans; how to read one ADG vertex; the ADG with a Type 1 "
            "chain per AGV and two Type 2 edges from the location rule; a rotation that gives a cycle.")
    # ---- 1. map and plans ----
    d.text(0, 0, "1  The map and the timed plans", size=14, weight=600, fill=T.fg)
    s = 84
    mx, my = 40, 74
    _cell_map(d, mx, my, s)
    d.text(0, my + 2 * s + 40, "Cells A to F are places on the floor (garage nodes).", size=11.5, fill=T.muted)
    d.text(0, my + 2 * s + 56, "Arrows: each AGV's moves, in its colour.", size=11.5, fill=T.muted)
    tx, ty = 380, 40
    mathline(d, tx, ty, ["Plan of AGV ", ("sym", "i", None, None), ":  ",
                         ("sym", "p", "i", None), " = (", ("sym", "a", "i", "1"), ", ", ("sym", "a", "i", "2"),
                         ", ...),  each action ", ("sym", "a", "i", "k"), " = (start time ",
                         ("sym", "t", "i", "k"), ", start cell ", ("sym", "s", "i", "k"), ", goal cell ",
                         ("sym", "g", "i", "k"), ")"], size=13.5, fill=T.fg2)
    d.step("Start from the timed plans: one row per action. The ADG gets one vertex per action, placed in a lane "
           "per robot. No edges yet.")
    d.step("Type 1 edges: each robot's actions stay in order. AGV 1 does A -> B before B -> C; AGV 2 does D -> B "
           "before B -> E. AGV 3 has one action, so no Type 1 edge.")
    d.step("Type 2, cell C: AGV 3 leaves C at t = 0 and AGV 1 enters C at t = 1. The earlier action must finish "
           "first, so the edge points from AGV 3's action to AGV 1's.")
    d.step("Type 2, cell B: AGV 1 leaves B at t = 1 and AGV 2 enters B at t = 2, so AGV 1's B -> C must finish "
           "before AGV 2's D -> B starts. That is every edge: the ADG is done, and it keeps only these orders.")
    d.step("The times only decided each edge's direction. When two robots swap or rotate at the same instant, the "
           "rule gives a cycle (inset): such a plan is safe only with perfectly synchronous moves.")
    hx = [tx, tx + 110, tx + 200, tx + 320, tx + 430]
    for h, lab in zip(hx, ["AGV", "action", "start time", "start cell", "goal cell"]):
        d.text(h, ty + 36, lab, size=11.5, weight=600, fill=T.muted)
    yy = ty + 62
    hl_rows = {2: {(3, 1), (1, 2)}, 3: {(1, 2), (2, 1)}}
    for i, acts in PLANS.items():
        for k, (t, s0, g0) in enumerate(acts, 1):
            d.rect(tx - 10, yy - 13, 540, 26, rx=4, fill=T.tint(ACOL[i], 0.08, T.bg))
            for stp, keys in hl_rows.items():
                if (i, k) in keys:
                    with d.only(stp):
                        d.rect(tx - 10, yy - 13, 540, 26, rx=4, fill="none", stroke=T2, sw=1.8)
            d.text(hx[0], yy, f"AGV {i}", size=12, family="mono", weight=600, fill=ACOL[i])
            sym(d, hx[1], yy, "a", str(i), str(k), size=15, sup_italic=False, sub_italic=False)
            d.text(hx[2], yy, f"{t}", size=12.5, family="mono", fill=T.fg)
            d.text(hx[3], yy, s0, size=12.5, family="mono", fill=T.fg)
            d.text(hx[4], yy, g0, size=12.5, family="mono", fill=T.fg)
            yy += 30
    # ---- 2. anatomy of a vertex ----
    ay = 330
    d.text(0, ay, "2  How to read a vertex", size=14, weight=600, fill=T.fg)
    big = BBox(80, ay + 40, 330, ay + 140)
    d.rect(big.x0, big.y0, big.w, big.h, rx=12, fill=T.tint(A1, 0.14, T.bg), stroke=A1, sw=2)
    sym(d, big.cx, big.y0 + 36, "a", "1", "2", size=30, anchor="middle", sup_italic=False, sub_italic=False)
    d.text(big.cx, big.y0 + 76, "B -> C, t = 1", size=15, family="mono", fill=T.fg, anchor="middle")
    notes = [
        (big.y0 + 22, ["a  =  an ", "action", ": one move, lift or command by one robot"]),
        (big.y0 + 44, ["superscript 1  =  which robot: AGV 1"]),
        (big.y0 + 66, ["subscript 2  =  which of that robot's actions: its 2nd, counting from 1"]),
        (big.y0 + 88, ["B -> C  =  start cell ", ("sym", "s", "1", "2"), " = B,  goal cell ", ("sym", "g", "1", "2"), " = C"]),
        (big.y0 + 110, ["t = 1  =  planned start time ", ("sym", "t", "1", "2"),
                        ": used only to decide edge directions, not to time execution"]),
    ]
    for y_, parts in notes:
        connect(d, [(big.x1 + 6, y_), (big.x1 + 40, y_)], kind="line", color=T.border)
        mathline(d, big.x1 + 48, y_, parts, size=13, fill=T.fg2)
    # ---- 3. the ADG ----
    gy0 = ay + 230
    d.text(0, gy0 - 40, "3  The ADG: one vertex per action, two kinds of edge", size=14, weight=600, fill=T.fg)
    cols = [140, 380, 620, 860]
    r = {1: gy0 + 40, 3: gy0 + 145, 2: gy0 + 250}
    N = {}
    N[(1, 1)] = anode(d, cols[0], r[1], 1, 1, "A -> B", 0, A1)
    N[(1, 2)] = anode(d, cols[1], r[1], 1, 2, "B -> C", 1, A1, hl=True)
    N[(3, 1)] = anode(d, cols[0], r[3], 3, 1, "C -> F", 0, A3)
    N[(2, 1)] = anode(d, cols[2], r[2], 2, 1, "D -> B", 2, A2, hl=True)
    N[(2, 2)] = anode(d, cols[3], r[2], 2, 2, "B -> E", 3, A2)
    for nm, yy_, col in (("AGV 1", r[1], A1), ("AGV 3", r[3], A3), ("AGV 2", r[2], A2)):
        d.text(0, yy_ + 4, nm, size=12, family="mono", weight=600, fill=col)
    with d.at(1):
        arrow(d, N[(1, 1)], N[(1, 2)], T1, label="Type 1", label_at=((N[(1, 1)].x1 + N[(1, 2)].x0) / 2, r[1] - 16))
        arrow(d, N[(2, 1)], N[(2, 2)], T1, label="Type 1", label_at=((N[(2, 1)].x1 + N[(2, 2)].x0) / 2, r[2] - 16))
    with d.at(2):
        arrow(d, N[(3, 1)], N[(1, 2)], T2, dash="7 4")
        label_pill(d, N[(3, 1)].x0, r[3] + 50, "Type 2: AGV 3 leaves C before AGV 1 enters C", color=T2,
                   anchor="start")
    with d.at(3):
        arrow(d, N[(1, 2)], N[(2, 1)], T2, dash="7 4")
        label_pill(d, cols[2] - 60, r[1] + 44, "Type 2: AGV 1 leaves B before AGV 2 enters B", color=T2,
                   anchor="start")
    # rules
    nx = 1040
    d.rect(nx, gy0 - 20, 470, 250, rx=10, fill=T.tint(T.card, 0.7, T.bg), stroke=T.border_soft)
    d.text(nx + 16, gy0, "The two edge rules (Hönig et al. 2019)", size=13, weight=600, fill=T.fg)
    mathline(d, nx + 16, gy0 + 34, ["Type 1:  ", ("sym", "a", "i", "k"), " ", ("op", "to"), " ", ("sym", "a", "i", "k+1")],
             size=14, fill=T1)
    d.text(nx + 16, gy0 + 58, "the same robot's actions, in order", size=12, fill=T.fg2)
    mathline(d, nx + 16, gy0 + 96, ["Type 2:  ", ("sym", "a", "i", "k"), " ", ("op", "to"), " ", ("sym", "a", "j", "l"),
                                    "   if  ", ("sym", "i", None, None), " ", ("op", "ne"), " ", ("sym", "j", None, None),
                                    ",  ", ("sym", "s", "i", "k"), " = ", ("sym", "g", "j", "l"),
                                    ",  ", ("sym", "t", "i", "k"), " ", ("op", "le"), " ", ("sym", "t", "j", "l")],
             size=14, fill=T2)
    d.text(nx + 16, gy0 + 122, "robot i leaves a cell that robot j enters later:", size=12, fill=T.fg2)
    d.text(nx + 16, gy0 + 140, "the leaving action must finish before the", size=12, fill=T.fg2)
    d.text(nx + 16, gy0 + 158, "entering action may start", size=12, fill=T.fg2)
    d.text(nx + 16, gy0 + 194, "Times decide only the direction of each edge.", size=12, fill=T.muted)
    d.text(nx + 16, gy0 + 212, "Execution then ignores them.", size=12, fill=T.muted)
    # cycle inset
    cx, cy = nx + 235, gy0 + 345
    _inset = d.at(4)
    _inset.__enter__()
    d.text(nx, cy - 75, "4  A cycle: three robots rotate at the same instant", size=13, weight=600, fill=T.fg)
    tri = [(cx - 120, cy + 40), (cx, cy - 30), (cx + 120, cy + 40)]
    labs = [("X -> Y", A1, 1), ("Y -> Z", A2, 2), ("Z -> X", A3, 3)]
    bs = [anode(d, px_, py_, i, 1, lab, 0, col, w=120, h=52) for (px_, py_), (lab, col, i) in zip(tri, labs)]
    arrow(d, bs[0], bs[2], RED, dash="7 4")
    arrow(d, bs[2], bs[1], RED, dash="7 4")
    arrow(d, bs[1], bs[0], RED, dash="7 4")
    d.text(cx, cy + 92, "each waits for another to leave: a cycle,", size=11.5, fill=RED, anchor="middle")
    d.text(cx, cy + 108, "safe only with perfectly synchronous moves", size=11.5, fill=RED, anchor="middle")
    _inset.__exit__(None, None, None)
    frame(d, title="Building an action dependency graph",
          subtitle="Each action of each robot becomes a vertex. Type 1 edges keep each robot's own order; Type 2 "
                   "edges say who must clear a cell before someone else enters it. The ADG keeps the plan's order "
                   "and forgets its exact times.",
          badge_key="illustrative",
          legend=[("arrow", T1, "Type 1 (same robot)"), ("dasharrow", T2, "Type 2 (cell hand-over)"),
                  ("dasharrow", RED, "cycle"), ("box", A1, "AGV 1"), ("box", A2, "AGV 2"), ("box", A3, "AGV 3")],
          footnote="Construction as in Algorithm 1 of Hönig et al., RA-L 2019. In the inset the cells are X, Y, Z "
                   "and each robot's only action is its first.")
    return d


# ======================================================================================
# 88 — executing the ADG: statuses over time
# ======================================================================================

@figure("88_adg_statuses", "Executing an ADG: statuses over time", DOC5)
def adg_statuses():
    d = Doc("88_adg_statuses", "Executing an ADG: statuses over time",
            "The status life cycle (staged, enqueued, finished) and five snapshots of the example ADG being "
            "dispatched, with each robot's command queue and the rule that let each action through.")
    ST, EN, FI = T.faint, T.amber, T.green
    # ---- life cycle ----
    d.text(0, 0, "1  The life of one action", size=14, weight=600, fill=T.fg)
    y = 60
    boxes = []
    for i, (name, col, desc, msg) in enumerate([
            ("staged", ST, "in the ADG, not sent yet", "ActionNode STATUS_NOT_RECEIVED"),
            ("enqueued", EN, "sent to the robot's command queue", "STATUS_RECEIVED (acknowledged)"),
            ("finished", FI, "the robot reported completion", "STATUS_COMPLETED")]):
        x = i * 470
        fill = {0: T.card, 1: T.tint(EN, 0.22, T.bg), 2: T.tint(FI, 0.25, T.bg)}[i]
        d.rect(x, y - 30, 300, 74, rx=12, fill=fill, stroke=col, sw=2)
        d.text(x + 18, y - 8, name, size=16, weight=600, fill=T.fg)
        d.text(x + 18, y + 14, desc, size=12, fill=T.fg2)
        d.text(x + 18, y + 32, msg, size=11, family="mono", fill=T.muted)
        boxes.append(BBox(x, y - 30, x + 300, y + 44))
    connect(d, [(boxes[0].x1, y), (boxes[1].x0, y)], kind="flow", color=EN, sw=2)
    d.text((boxes[0].x1 + boxes[1].x0) / 2, y - 44, "dispatcher: the enqueue rule holds", size=11.5, fill=EN,
           anchor="middle")
    connect(d, [(boxes[1].x1, y), (boxes[2].x0, y)], kind="flow", color=FI, sw=2)
    d.text((boxes[1].x1 + boxes[2].x0) / 2, y - 44, "robot: done", size=11.5, fill=FI, anchor="middle")
    d.text(0, y + 74, "Enqueue rule: the previous action of the same robot (Type 1) is enqueued or finished, AND every "
                      "action of another robot it depends on (Type 2) is finished.", size=12.5, fill=T.fg2)
    # ---- snapshots ----
    preds1 = {(1, 2): (1, 1), (2, 2): (2, 1)}
    preds2 = {(1, 2): [(3, 1)], (2, 1): [(1, 2)]}
    snaps = [
        ("t = 0  start", {(1, 1): "enqueued", (3, 1): "enqueued", (1, 2): "staged", (2, 1): "staged", (2, 2): "staged"},
         "a11 and a31 have no predecessors: sent at once. a12 waits: its Type 2 predecessor a31 is not finished."),
        ("AGV 3 reports a31 done", {(1, 1): "enqueued", (3, 1): "finished", (1, 2): "enqueued", (2, 1): "staged",
                                    (2, 2): "staged"},
         "a12 is sent: a11 (Type 1) is only enqueued, which is enough; a31 (Type 2) is finished. It queues behind a11."),
        ("AGV 1 reports a11 done", {(1, 1): "finished", (3, 1): "finished", (1, 2): "enqueued", (2, 1): "staged",
                                    (2, 2): "staged"},
         "AGV 1 starts a12 from its own queue; the dispatcher does nothing."),
        ("AGV 1 reports a12 done", {(1, 1): "finished", (3, 1): "finished", (1, 2): "finished", (2, 1): "enqueued",
                                    (2, 2): "enqueued"},
         "a21 is sent (its Type 2 predecessor a12 is finished), and a22 with it (Type 1 predecessor enqueued)."),
        ("AGV 2 reports a21, a22 done", {k: "finished" for k in [(1, 1), (3, 1), (1, 2), (2, 1), (2, 2)]},
         "All finished. Each robot drove as fast as it could; only the order was enforced."),
    ]
    move = {(1, 1): ("A -> B", 0), (1, 2): ("B -> C", 1), (3, 1): ("C -> F", 0), (2, 1): ("D -> B", 2),
            (2, 2): ("B -> E", 3)}
    sy = y + 140
    d.text(0, sy - 10, "2  Dispatching the example ADG (from the construction figure), one event at a time", size=14,
           weight=600, fill=T.fg)
    rowh = 200
    y0 = sy + 30
    d.rect(0, y0, 1400, rowh - 40, rx=10, fill=T.tint(T.card, 0.45, T.bg), stroke=T.border_soft)

    def ak(t):
        return (t.replace("a11", "a[1,1]").replace("a12", "a[1,2]").replace("a31", "a[3,1]")
                .replace("a21", "a[2,1]").replace("a22", "a[2,2]"))

    def uk(t):   # plain-text form for the step captions under the figure
        for s_, u_ in (("a11", "a¹₁"), ("a12", "a¹₂"), ("a31", "a³₁"), ("a21", "a²₁"), ("a22", "a²₂")):
            t = t.replace(s_, u_)
        return t
    for n, (title, st, why) in enumerate(snaps):
        d.step(f"{uk(title)}. {uk(why)}")
    for n, (title, st, why) in enumerate(snaps):
        with d.only(n):
            mtext(d, 16, y0 + 22, f"{n + 1}.  {ak(title)}", size=13, fill=T.fg)
            pos = {(1, 1): (110, 60), (1, 2): (290, 60), (3, 1): (110, 112), (2, 1): (470, 112), (2, 2): (650, 112)}
            B = {}
            for key, (px_, py_) in pos.items():
                i, k = key
                B[key] = anode(d, px_, y0 + py_, i, k, move[key][0], move[key][1], ACOL[i], w=150, h=46,
                               status=st[key], sw=1.4)
            for v, u in preds1.items():
                arrow(d, B[u], B[v], T1, sw=1.5)
            for v, us in preds2.items():
                for u in us:
                    arrow(d, B[u], B[v], T2, dash="6 4", sw=1.5)
            # queues
            qx = 820
            d.text(qx, y0 + 22, "command queues (front first)", size=11.5, weight=600, fill=T.muted)
            for j, i in enumerate((1, 2, 3)):
                qy = y0 + 52 + j * 36
                d.text(qx, qy, f"AGV {i}", size=12, family="mono", weight=600, fill=ACOL[i])
                items = [key for key in sorted(st) if key[0] == i and st[key] == "enqueued"]
                cx_ = qx + 70
                if not items:
                    d.text(cx_, qy, "empty", size=11.5, fill=T.faint)
                for key in items:
                    w_ = 64
                    d.rect(cx_, qy - 13, w_, 26, rx=6, fill=T.tint(EN, 0.22, T.bg), stroke=EN, sw=1.2)
                    sym(d, cx_ + w_ / 2, qy, "a", str(key[0]), str(key[1]), size=13, anchor="middle",
                        sup_italic=False, sub_italic=False)
                    cx_ += w_ + 8
    frame(d, title="Executing an ADG: statuses over time",
          subtitle="The dispatcher sends an action when its rule holds; the robot runs its queue in order and "
                   "reports each completion; each report may release more actions.",
          badge_key="illustrative",
          legend=[("box", ST, "staged"), ("fill", EN, "enqueued"), ("fill", FI, "finished"),
                  ("arrow", T1, "Type 1"), ("dasharrow", T2, "Type 2")],
          footnote="Enqueue rule from Hönig et al., RA-L 2019. The ActionNode status names are the closest fields "
                   "in interfaces/msg/ActionNode.msg; how the dispatcher maps them is not in the snapshots.")
    return d


# ======================================================================================
# 86 — timing on an ADG
# ======================================================================================

@figure("86_adg_critical_path", "Earliest start, critical path and slack", DOC5)
def adg_critical_path():
    d = Doc("86_adg_critical_path", "Earliest start, critical path and slack",
            "The ADG of the previous figure with durations; each vertex shows its earliest start S and "
            "completion C; the critical path is highlighted; a delay on a slack action does not move the end.")
    dur = {"a[1,1]": 3, "a[1,2]": 3, "a[3,1]": 2, "a[2,1]": 2, "a[2,2]": 2}
    preds = {"a[1,1]": [], "a[3,1]": [], "a[1,2]": ["a[1,1]", "a[3,1]"], "a[2,1]": ["a[1,2]"], "a[2,2]": ["a[2,1]"]}
    order = ["a[1,1]", "a[3,1]", "a[1,2]", "a[2,1]", "a[2,2]"]
    S, C = {}, {}
    for v in order:
        S[v] = max([C[u] for u in preds[v]], default=0)
        C[v] = S[v] + dur[v]
    M = max(C.values())
    succ = {v: [w for w in order if v in preds[w]] for v in order}
    LF = {}
    for v in reversed(order):
        LF[v] = min([LF[w] - dur[w] for w in succ[v]], default=M)
    slack = {v: LF[v] - C[v] for v in order}
    crit = [v for v in order if slack[v] == 0]
    col = {"a[1,1]": A1, "a[1,2]": A1, "a[3,1]": A3, "a[2,1]": A2, "a[2,2]": A2}
    xs = {"a[1,1]": 110, "a[3,1]": 110, "a[1,2]": 370, "a[2,1]": 630, "a[2,2]": 890}
    ys = {"a[1,1]": 40, "a[3,1]": 150, "a[1,2]": 95, "a[2,1]": 95, "a[2,2]": 95}
    B = {}
    for v in order:
        i_, k_ = v[2], v[4]
        w_, h_ = 200, 56
        x_, y_ = xs[v] - w_ / 2, ys[v] - h_ / 2
        d.rect(x_, y_, w_, h_, rx=9, fill=T.tint(col[v], 0.16, T.bg) if v in crit else T.card, stroke=col[v],
               sw=2.4 if v in crit else 1.4)
        mathline(d, x_ + 18, ys[v] - 10, [("sym", "a", i_, k_), f"   duration d = {dur[v]}"], size=14, fill=T.fg)
        d.text(xs[v], ys[v] + 15, f"start S = {S[v]},  completion C = {C[v]}", size=11, fill=T.fg2, anchor="middle")
        B[v] = BBox(x_, y_, x_ + w_, y_ + h_)
    for v in order:
        for u in preds[v]:
            same = col[u] == col[v]
            arrow(d, B[u], B[v], T.green if (u in crit and v in crit) else T.fg2,
                  dash=None if same else "7 4", sw=2.6 if (u in crit and v in crit) else 1.5)
    d.text(B["a[3,1]"].cx, B["a[3,1]"].y1 + 20, f"slack {slack['a[3,1]']}: may finish as late as {LF['a[3,1]']}",
           size=11.5, fill=T.amber, anchor="middle")
    # gantt
    gy = 280
    px = 80
    x0 = 120
    d.text(0, gy - 24, "Earliest-start schedule (critical path in green)", size=13, weight=600, fill=T.fg)
    rows = [("AGV 1", ["a[1,1]", "a[1,2]"]), ("AGV 3", ["a[3,1]"]), ("AGV 2", ["a[2,1]", "a[2,2]"])]
    for i, (nm, vs) in enumerate(rows):
        yy = gy + 20 + i * 38
        d.text(0, yy, nm, size=12, family="mono", weight=600, fill=col[vs[0]])
        for v in vs:
            _bar(d, x0, px, yy, S[v], C[v], "", T.green if v in crit else col[v], fill_a=0.3 if v in crit else 0.18)
            sym(d, x0 + (S[v] + C[v]) / 2 * px, yy, "a", v[2], v[4], size=14, anchor="middle", sup_italic=False,
                sub_italic=False)
        if nm == "AGV 3":
            _bar(d, x0, px, yy, C[v], LF[v], "slack", T.amber, dash="4 3", fill_a=0.06)
    _axis(d, x0, gy + 20 + 3 * 38 - 10, px, 0, M, label="t [s]")
    note(d, x0 + M * px + 60, gy - 10, 380,
         f"S(v) = max over predecessors u of C(u);  C(v) = S(v) + d(v). Makespan = max C = {M}. "
         "A delay on a critical action delays the end by the same amount. A delay on AGV 3's action is absorbed "
         f"up to its slack ({slack['a[3,1]']}); beyond that, AGV 1's second action starts late and the end moves.",
         title="The recurrence", accent=T.green, size=12)
    frame(d, title="Timing on an ADG: earliest start, critical path, slack",
          subtitle="Given durations, the earliest each action can start is the latest completion of its "
                   "predecessors. The longest path fixes the makespan; everything off it has slack.",
          badge_key="illustrative",
          legend=[("box", T.green, "critical path"), ("arrow", T.fg2, "Type 1"), ("dasharrow", T.fg2, "Type 2"),
                  ("dashbox", T.amber, "slack")],
          footnote="Durations are made up for the example; S, C and slack are computed by the figure script with "
                   "the recurrence shown.")
    return d


# ======================================================================================
# 87 — the ADG the scheduler builds
# ======================================================================================

@figure("87_adg_in_scheduler", "The action DAG the scheduler builds", DOC5)
def adg_in_scheduler():
    d = Doc("87_adg_in_scheduler", "The action DAG the scheduler builds",
            "Illustrative retrieve: the event DAG, CHUGG's timed motions per entity, the action DAG with "
            "same-entity, occupancy and event-level edges before and after Reduce, and the Schedule array.")
    EV, CH = T.teal, T.sky
    # ---- 1. event DAG ----
    d.text(0, 0, "1  Event DAG (ctx->events): what, and in which order", size=14, weight=600, fill=T.fg)
    e0 = vnode(d, 90, 60, "e0 AgvMove", "A -> P1", EV, w=160)
    e1 = vnode(d, 300, 60, "e1 TrayMove", "T5 P1 -> B4 by A", EV, w=180)
    e3 = vnode(d, 520, 60, "e3 BayTransition", "B4 PROCESS_RETRIEVE", EV, w=190)
    e2 = vnode(d, 90, 135, "e2 AgvMove", "B W2 -> W3", EV, w=160)
    arrow(d, e0, e1, EV)
    arrow(d, e1, e3, EV)
    # ---- 2. CHUGG output ----
    gy = 200
    d.text(0, gy, "2  CHUGG's motions (waits dropped), sorted by start time", size=14, weight=600, fill=T.fg)
    px, x0 = 34, 90
    motions = {
        "AGV A": [(0, 3, "a1 W1->P1", "e0"), (3, 5, "a2 lift", "e1"), (5, 8, "a3 P1->W2", "e1"),
                  (8, 11, "a4 W2->B4", "e1"), (11, 13, "a5 lower", "e1")],
        "AGV B": [(0, 2, "b1 W2->W3", "e2")],
        "bay B4": [(13, 20, "c1 retrieve", "e3")],
    }
    colm = {"AGV A": A1, "AGV B": A2, "bay B4": A3}
    for i, (ent, ms) in enumerate(motions.items()):
        yy = gy + 40 + i * 44
        d.text(0, yy, ent, size=12, family="mono", weight=600, fill=colm[ent])
        for t0, t1, lab, ev in ms:
            _bar(d, x0, px, yy, t0, t1, lab, colm[ent], h=28)
    _axis(d, x0, gy + 40 + 3 * 44 - 12, px, 0, 20, step=2, label="t [s]")
    # ---- 3. action DAG ----
    ay = 470
    d.text(0, ay, "3  Action DAG (final_actions_dag): three kinds of edge, then Reduce()", size=14,
           weight=600, fill=T.fg)
    yA, yB = ay + 90, ay + 200
    xs = [90, 260, 430, 600, 770, 940]
    a1 = vnode(d, xs[0], yA, "a1", "A W1->P1", A1, w=120, h=46)
    a2 = vnode(d, xs[1], yA, "a2", "A lift P1", A1, w=120, h=46)
    a3 = vnode(d, xs[2], yA, "a3", "A P1->W2", A1, w=120, h=46)
    a4 = vnode(d, xs[3], yA, "a4", "A W2->B4", A1, w=120, h=46)
    a5 = vnode(d, xs[4], yA, "a5", "A lower B4", A1, w=120, h=46)
    c1 = vnode(d, xs[5], yA, "c1", "B4 retrieve", A3, w=120, h=46)
    b1 = vnode(d, xs[1], yB, "b1", "B W2->W3", A2, w=120, h=46)
    for u, v in ((a1, a2), (a2, a3), (a3, a4), (a4, a5)):
        arrow(d, u, v, T1)
    arrow(d, b1, a3, T2, dash="7 4", via=[(b1.x1 + 30, b1.cy), (a3.cx, b1.cy)], label="occupancy: W2",
          label_at=((b1.x1 + a3.cx) / 2 + 20, b1.cy - 14))
    arrow(d, a5, c1, TE, dash="3 3", label="event e1 -> e3", label_at=((a5.x1 + c1.x0) / 2, yA - 40))
    # redundant edge a1 -> a3 (occupancy, same entity), removed by Reduce
    connect(d, [(a1.cx, a1.y0), (a1.cx, yA - 52), (a3.cx - 20, yA - 52), (a3.cx - 20, a3.y0)], kind="flow",
            color=RED, dash="4 3", size=8, sw=1.4)
    d.text(a3.cx, yA - 46, "a1 -> a3 occupancy (P1), implied by a1 -> a2 -> a3: removed by Reduce()",
           size=11, fill=RED)
    # ---- 4. Schedule ----
    sy = yB + 70
    d.text(0, sy, "4  Schedule.nodes: a topological order, parents as indices", size=14, weight=600, fill=T.fg)
    order = [("a1", "AGV_COMMAND", "[]"), ("b1", "AGV_COMMAND", "[]"), ("a2", "AGV_COMMAND", "[0]"),
             ("a3", "AGV_COMMAND", "[2, 1]"), ("a4", "AGV_COMMAND", "[3]"), ("a5", "AGV_COMMAND", "[4]"),
             ("c1", "BAY_COMMAND", "[5]")]
    cw = 150
    for i, (nm, ty, par) in enumerate(order):
        x = i * (cw + 6)
        yy = sy + 24
        d.rect(x, yy, cw, 62, rx=6, fill=T.card, stroke=T.border, sw=1)
        d.text(x + 10, yy + 16, f"[{i}] {nm}", size=12, family="mono", weight=700, fill=T.fg)
        d.text(x + 10, yy + 34, f"TYPE_{ty}", size=10.5, family="mono", fill=T.muted)
        d.text(x + 10, yy + 50, f"parents {par}", size=11, family="mono", fill=T.fg2)
    frame(d, title="The action DAG the scheduler builds",
          subtitle="ResponseFromTrajectories turns CHUGG's timed motions into an ADG: a chain per entity (Type 1), "
                   "an edge from every earlier occupant of an overlapping footprint (Type 2), and an edge from the "
                   "last action of each event to the first action of every event that depends on it. Reduce() "
                   "removes implied edges; the result is sent as Schedule.nodes.",
          badge_key="illustrative",
          legend=[("arrow", T1, "same entity (last_entity_action)"), ("dasharrow", T2, "occupancy (freeing_moves)"),
                  ("dasharrow", TE, "event-level (TransferEventDagDepsToActionDag)"),
                  ("dasharrow", RED, "redundant, removed")],
          footnote="Illustrative names and times, not a Pecos run. Edge rules from src/scheduler.cpp: "
                   "BuildActionDagFromMotions, TransferEventDagDepsToActionDag, BuildScheduledActionsArray. The "
                   "event-level edge e0 -> e1 maps to a1 -> a2, which already exists. The order shown is one valid "
                   "topological order.")
    return d


# ======================================================================================
# 89 — where parallelism comes from
# ======================================================================================

def _par_panel(d: Doc, x0, y0, title, verts, edges, redundant=(), *, w=330):
    """verts: name -> (robot, duration, (dx, dy)); edges kept after reduction; redundant edges drawn dashed red."""
    d.text(x0, y0, title, size=13.5, weight=600, fill=T.fg)
    preds = {v: [u for u, w_ in edges if w_ == v] for v in verts}
    order, seen = [], set()
    while len(order) < len(verts):
        for v in verts:
            if v not in seen and all(u in seen for u in preds[v]):
                order.append(v)
                seen.add(v)
    S, C = {}, {}
    for v in order:
        S[v] = max([C[u] for u in preds[v]], default=0)
        C[v] = S[v] + verts[v][1]
    L = max(C.values())
    W = sum(dv for _, dv, _ in verts.values())
    # width: brute force largest set of pairwise unordered vertices
    reach = {v: set() for v in verts}
    for v in reversed(order):
        for u, w_ in edges:
            if u == v:
                reach[v] |= {w_} | reach[w_]
    names = list(verts)
    width = 1
    from itertools import combinations
    for r in range(2, len(names) + 1):
        for comb in combinations(names, r):
            if all(b not in reach[a] and a not in reach[b] for a, b in combinations(comb, 2)):
                width = r
    B = {}
    for v, (rb, dv, (dx, dy)) in verts.items():
        cx, cy = x0 + dx, y0 + 50 + dy
        bb = BBox(cx - 34, cy - 20, cx + 34, cy + 20)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.card, stroke=ACOL[rb], sw=1.5)
        mathline(d, bb.x0 + 10, cy, [("sym", v, None, None), f"  d={dv}"], size=13, fill=T.fg)
        B[v] = bb
    for u, v in edges:
        arrow(d, B[u], B[v], T.fg2, sw=1.5)
    for u, v in redundant:
        arrow(d, B[u], B[v], RED, dash="4 3", sw=1.3,
              via=[(B[u].x1 + 18, B[u].cy), (B[u].x1 + 18, B[v].cy)])
    # gantt
    gy = y0 + 330
    px = (w - 70) / max(L, 1)
    robots = sorted({rb for rb, _, _ in verts.values()})
    for j, rb in enumerate(robots):
        yy = gy + j * 32
        d.text(x0, yy, f"AGV {rb}", size=11.5, family="mono", weight=600, fill=ACOL[rb])
        for v, (r_, dv, _) in verts.items():
            if r_ == rb:
                bx = x0 + 62 + S[v] * px
                d.rect(bx, yy - 12, dv * px, 24, rx=5, fill=T.tint(ACOL[rb], 0.24, T.bg), stroke=ACOL[rb], sw=1.2)
                sym(d, bx + dv * px / 2, yy, v, size=13, anchor="middle")
    ay = gy + len(robots) * 32 - 6
    d.line(x0 + 62, ay, x0 + 62 + L * px, ay, stroke=T.border)
    for t in range(0, L + 1, 2):
        d.text(x0 + 62 + t * px, ay + 13, str(t), size=10, family="mono", fill=T.muted, anchor="middle")
    sy = gy + 110
    rows = [f"work W = sum of d = {W}", f"span L = critical path = {L}",
            f"average parallelism W / L = {W / L:.2f}", f"width (most at once) = {width}"]
    for k, r_ in enumerate(rows):
        d.text(x0, sy + k * 18, r_, size=12, fill=T.green if (k >= 2 and width > 1) else T.fg2)
    return W, L, width


@figure("89_adg_parallelism", "Where parallelism comes from", DOC5)
def adg_parallelism():
    d = Doc("89_adg_parallelism", "Where parallelism comes from",
            "Four small ADGs: a single chain, a fork and join, two independent chains, and a graph whose extra "
            "edge only looks like a fork. Each has its earliest-start Gantt chart, work, span and width.")
    P = 380
    _par_panel(d, 0, 0, "1  One chain: nothing runs in parallel",
               {"u": (1, 2, (40, 0)), "v": (2, 2, (40, 60)), "w": (1, 2, (40, 120)), "x": (2, 2, (40, 180))},
               [("u", "v"), ("v", "w"), ("w", "x")])
    _par_panel(d, P, 0, "2  Fork and join",
               {"r": (1, 2, (130, 0)), "p": (1, 3, (50, 80)), "q": (2, 2, (210, 80)), "j": (2, 2, (130, 160))},
               [("r", "p"), ("r", "q"), ("p", "j"), ("q", "j")])
    _par_panel(d, 2 * P, 0, "3  Two roots, no shared space",
               {"p": (1, 3, (50, 20)), "q": (1, 3, (50, 120)), "m": (2, 2, (210, 20)), "n": (2, 2, (210, 120))},
               [("p", "q"), ("m", "n")])
    _par_panel(d, 3 * P, 0, "4  Looks like a fork, is a chain",
               {"a": (1, 2, (60, 0)), "b": (2, 2, (60, 80)), "c": (1, 2, (60, 160))},
               [("a", "b"), ("b", "c")], redundant=[("a", "c")])
    d.text(3 * P + 150, 80, "a has two children,", size=11.5, fill=RED)
    d.text(3 * P + 150, 96, "but a -> c is implied", size=11.5, fill=RED)
    d.text(3 * P + 150, 112, "by a -> b -> c:", size=11.5, fill=RED)
    d.text(3 * P + 150, 128, "Reduce() removes it", size=11.5, fill=RED)
    frame(d, title="Where parallelism comes from",
          subtitle="Two actions can run at the same time only if neither reaches the other. A graph whose "
                   "transitive reduction is one chain is a strict sequence, however many robots it involves.",
          badge_key="illustrative",
          legend=[("box", A1, "AGV 1"), ("box", A2, "AGV 2"), ("arrow", T.fg2, "dependency"),
                  ("dasharrow", RED, "implied edge (removed by Reduce)")],
          footnote="Durations invented. Gantt charts are earliest-start schedules (every action starts as soon as "
                   "its predecessors finish). Width = largest set of pairwise unordered actions, computed by brute force.")
    return d


# ======================================================================================
# 90 — topological orders do not remove parallelism
# ======================================================================================

@figure("90_adg_topo_vs_parallel", "Topological orders and parallelism", DOC5)
def adg_topo_vs_parallel():
    d = Doc("90_adg_topo_vs_parallel", "Topological orders and parallelism",
            "The example ADG, its two topological orders as arrays with parent indices, execution by "
            "dependencies (parallel) versus executing the array one entry at a time (serial), and the ready "
            "sets as the dispatcher sees them.")
    dur = {(1, 1): 3, (3, 1): 2, (1, 2): 3, (2, 1): 2, (2, 2): 2}
    preds = {(1, 1): [], (3, 1): [], (1, 2): [(1, 1), (3, 1)], (2, 1): [(1, 2)], (2, 2): [(2, 1)]}
    move = {(1, 1): "A -> B", (1, 2): "B -> C", (3, 1): "C -> F", (2, 1): "D -> B", (2, 2): "B -> E"}
    # ---- 1. the ADG ----
    d.text(0, 0, "1  One ADG (the example)", size=14, weight=600, fill=T.fg)
    pos = {(1, 1): (80, 60), (3, 1): (80, 140), (1, 2): (250, 100), (2, 1): (250, 190), (2, 2): (250, 270)}
    B = {}
    for key, (x, y) in pos.items():
        B[key] = BBox(x - 52, y - 22, x + 52, y + 22)
        d.rect(B[key].x0, B[key].y0, B[key].w, B[key].h, rx=8, fill=T.card, stroke=ACOL[key[0]], sw=1.5)
        mathline(d, B[key].x0 + 12, y, [("sym", "a", str(key[0]), str(key[1])), f"  d = {dur[key]}"], size=13)
    for v, us in preds.items():
        for u in us:
            arrow(d, B[u], B[v], T1 if u[0] == v[0] else T2, dash=None if u[0] == v[0] else "6 4", sw=1.5)
    mtext(d, 0, 330, "a[1,1] and a[3,1] are unordered:", size=12, fill=T.fg2)
    d.text(0, 346, "no path between them", size=12, fill=T.fg2)
    # ---- 2. two topological orders ----
    ox = 400
    d.text(ox, 0, "2  Its two topological orders, written as arrays", size=14, weight=600, fill=T.fg)
    orders = [[(1, 1), (3, 1), (1, 2), (2, 1), (2, 2)], [(3, 1), (1, 1), (1, 2), (2, 1), (2, 2)]]
    for oi, order in enumerate(orders):
        y = 70 + oi * 150
        d.text(ox, y - 38, f"order {oi + 1}", size=12, weight=600, fill=T.muted)
        idx = {key: n for n, key in enumerate(order)}
        cw = 92
        for n, key in enumerate(order):
            x = ox + n * (cw + 10)
            d.rect(x, y - 20, cw, 40, rx=6, fill=T.card, stroke=ACOL[key[0]], sw=1.3)
            sym(d, x + 22, y, "a", str(key[0]), str(key[1]), size=14, sup_italic=False, sub_italic=False)
            par = sorted(idx[u] for u in preds[key])
            d.text(x + 46, y - 6, f"[{n}]", size=10.5, family="mono", fill=T.muted)
            d.text(x + 46, y + 9, "p=" + (",".join(map(str, par)) if par else "-"), size=10.5, family="mono",
                   fill=T.fg2)
            for p_ in par:
                x0_ = ox + p_ * (cw + 10) + cw / 2
                x1_ = x + cw / 2
                # dependency edge parent -> child: always points forward (left to right) in a topological order
                connect(d, [(x0_ + 6, y + 20), (x0_ + 6, y + 36 + 8 * (n - p_)), (x1_ - 6, y + 36 + 8 * (n - p_)),
                            (x1_ - 6, y + 20)], kind="flow", color=T.fg2, sw=1.1, size=6, radius=4)
    d.text(ox, 340, "Edges (arrows) run parent -> child, always left to right. Each entry also stores p = its parents' indices,",
           size=12, fill=T.fg2)
    d.text(ox, 356, "all smaller than its own (ActionNode.parents). The order of unordered actions is arbitrary.",
           size=12, fill=T.fg2)
    # ---- 3. execution ----
    gx = 0
    gy = 430
    d.text(gx, gy, "3  Executing it", size=14, weight=600, fill=T.fg)
    px = 52
    x0 = 150

    def gantt(y, title, sched, color_title):
        d.text(gx, y, title, size=12.5, weight=600, fill=color_title)
        rows = [1, 3, 2]
        for j, rb in enumerate(rows):
            yy = y + 30 + j * 30
            d.text(gx, yy, f"AGV {rb}", size=11.5, family="mono", weight=600, fill=ACOL[rb])
            for key, (s0, c0) in sched.items():
                if key[0] == rb:
                    d.rect(x0 + s0 * px, yy - 11, (c0 - s0) * px, 22, rx=5, fill=T.tint(ACOL[rb], 0.24, T.bg),
                           stroke=ACOL[rb], sw=1.2)
                    sym(d, x0 + (s0 + c0) / 2 * px, yy, "a", str(key[0]), str(key[1]), size=13, anchor="middle",
                        sup_italic=False, sub_italic=False)
        end = max(c for _, c in sched.values())
        ay = y + 30 + 3 * 30 - 8
        d.line(x0, ay, x0 + 12 * px, ay, stroke=T.border)
        for t in range(0, 13, 2):
            d.text(x0 + t * px, ay + 13, str(t), size=10, family="mono", fill=T.muted, anchor="middle")
        d.line(x0 + end * px, y + 14, x0 + end * px, ay, stroke=color_title, sw=1.6, dash="4 3")
        d.text(x0 + end * px + 6, y + 18, f"done at {end}", size=11.5, fill=color_title)

    S, C = {}, {}
    for key in orders[0]:
        S[key] = max([C[u] for u in preds[key]], default=0)
        C[key] = S[key] + dur[key]
    gantt(gy + 30, "By dependencies: start each action when its parents are done", {k: (S[k], C[k]) for k in S},
          T.green)
    t = 0
    ser = {}
    for key in orders[0]:
        ser[key] = (t, t + dur[key])
        t += dur[key]
    gantt(gy + 190, "Wrong: run the array one entry at a time", ser, RED)
    # ---- 4. ready sets ----
    rx = 830
    d.text(rx, gy, "4  The ready set (actions whose parents are all finished)", size=14, weight=600, fill=T.fg)
    steps = [
        ("t = 0", "ready: a(1,1), a(3,1)", "both start: two robots move at once"),
        ("t = 2: a(3,1) done", "ready: (none new)", "a(1,2) still waits for a(1,1)"),
        ("t = 3: a(1,1) done", "ready: a(1,2)", ""),
        ("t = 6: a(1,2) done", "ready: a(2,1)", ""),
        ("t = 8: a(2,1) done", "ready: a(2,2)", ""),
    ]
    for n, (when, ready, note_) in enumerate(steps):
        yy = gy + 40 + n * 46
        mtext(d, rx, yy, when.replace("a(", "a[").replace(")", "]"), size=12.5, fill=T.fg)
        mtext(d, rx + 170, yy, ready.replace("a(", "a[").replace(")", "]"), size=12.5, fill=T.green)
        if note_:
            mtext(d, rx + 170, yy + 18, note_.replace("a(", "a[").replace(")", "]"), size=11.5, fill=T.muted)
    d.text(rx, gy + 280, "This is Kahn's algorithm run live: \"remove a vertex\" happens when a robot", size=12,
           fill=T.fg2)
    d.text(rx, gy + 296, "reports completion, and every vertex whose last parent was removed joins", size=12,
           fill=T.fg2)
    d.text(rx, gy + 312, "the ready set. Its size is the parallelism available at that moment.", size=12,
           fill=T.fg2)
    frame(d, title="Topological orders do not remove parallelism",
          subtitle="A topological order is a way to list a DAG, not a way to run it. The list keeps every edge "
                   "(as parent indices); execution follows the edges, so unordered actions still run together.",
          badge_key="illustrative",
          legend=[("arrow", T1, "Type 1"), ("dasharrow", T2, "Type 2"), ("arrow", T.fg2, "dependency (parent -> child)"),
                  ("line", T.green, "by dependencies"), ("line", RED, "array order (wrong)")],
          footnote="Durations as in the critical-path figure. The serial chart is what would happen if a consumer "
                   "ignored parents and ran Schedule.nodes in index order.")
    return d
