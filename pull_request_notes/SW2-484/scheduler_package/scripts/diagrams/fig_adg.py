"""Doc 05 (action dependency graph primer): figures 84-87.

84 why timestamps are not enough (delay), 85 building an ADG from a timed plan (Hönig et al. 2019
construction), 86 timing on an ADG: earliest start, critical path, slack, 87 the ADG the scheduler
builds in ResponseFromTrajectories (illustrative example, edge kinds as in src/scheduler.cpp).
"""
from __future__ import annotations

import math

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
            "Three Gantt panels for two AGVs crossing cell b: the plan, execution by the clock after a delay "
            "(both AGVs in b), and execution by dependencies (AGV 2 waits).")
    px = 110
    x0 = 170
    panels = [
        ("1  The plan", [(A1, "AGV 1", [(0, 1, "a->b"), (1, 2, "b->c")]),
                         (A2, "AGV 2", [(2, 3, "d->b"), (3, 4, "b->e")])], None, None),
        ("2  Execute by the clock: AGV 1's first move takes 2.5 instead of 1", [
            (A1, "AGV 1", [(0, 2.5, "a->b (slow)"), (2.5, 3.5, "b->c")]),
            (A2, "AGV 2", [(2, 3, "d->b"), (3, 4, "b->e")])], (2.5, 3.0), None),
        ("3  Execute by dependencies: d->b may start only after b->c has finished", [
            (A1, "AGV 1", [(0, 2.5, "a->b (slow)"), (2.5, 3.5, "b->c")]),
            (A2, "AGV 2", [(3.5, 4.5, "d->b"), (4.5, 5.5, "b->e")])], None, (3.5, 2.0)),
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
            d.text(x0 + 4.1 * px, ry + 20, "AGV 1 is still in b (until b->c ends)", size=11.5, fill=RED)
            d.text(x0 + 4.1 * px, ry + 36, "while AGV 2 drives into b", size=11.5, fill=RED)
        if wait:
            t_end, t_plan = wait
            d.line(x0 + t_plan * px, ry + 40, x0 + t_end * px, ry + 40, stroke=T2, sw=2, dash="4 3")
            d.text(x0 + (t_plan + t_end) / 2 * px, ry + 40 - 18, "waits 1.5", size=11, fill=T2, anchor="middle")
            connect(d, [(x0 + 3.5 * px - 2, ry + 13), (x0 + 3.5 * px - 2, ry + 27)], kind="flow", color=T2, size=7)
        _axis(d, x0, ry + 70, px, 0, 6, label="t [s]")
        y = ry + 130
    # map
    mx, my = x0 + 6 * px + 120, 90
    pos = {"a": (0, 1), "b": (1, 1), "c": (2, 1), "d": (1, 0), "e": (1, 2)}
    s = 70
    for k, (gx, gy) in pos.items():
        for k2, (hx, hy) in pos.items():
            if k < k2 and abs(gx - hx) + abs(gy - hy) == 1:
                d.line(mx + gx * s, my + gy * s, mx + hx * s, my + hy * s, stroke=T.border, sw=2)
    for k, (gx, gy) in pos.items():
        d.circle(mx + gx * s, my + gy * s, 16, fill=T.card, stroke=T.fg2 if k != "b" else RED, sw=1.6)
        d.text(mx + gx * s, my + gy * s, k, size=13, family="mono", weight=700, fill=T.fg, anchor="middle")
    d.text(mx - 20, my - 66, "Map: AGV 1 goes a -> b -> c,", size=11.5, fill=A1)
    d.text(mx - 20, my - 50, "AGV 2 goes d -> b -> e", size=11.5, fill=A2)
    frame(d, title="Why a timed plan is not enough",
          subtitle="A planner hands out times. Real AGVs are late or early. Executing by the clock lets a late "
                   "robot collide with one that is on time; executing by dependencies keeps the planned order "
                   "and lets the times slide.",
          badge_key="illustrative",
          legend=[("box", A1, "AGV 1"), ("box", A2, "AGV 2"), ("dashbox", RED, "both in cell b"),
                  ("dash", T2, "waiting for a dependency")],
          footnote="Unit-time moves on a five-cell map; an AGV occupies its start cell until its move ends.")
    return d


# ======================================================================================
# 85 — building an ADG from a timed plan
# ======================================================================================

@figure("85_adg_construction", "Building an ADG", DOC5)
def adg_construction():
    d = Doc("85_adg_construction", "Building an action dependency graph",
            "Three AGVs on a six-cell map with timed plans; the ADG has a Type 1 chain per AGV and two Type 2 "
            "edges from the location rule. Inset: three AGVs rotating at the same time give a cycle.")
    # map
    pos = {"a": (0, 1), "b": (1, 1), "c": (2, 1), "f": (3, 1), "d": (1, 0), "e": (1, 2)}
    s = 80
    mx, my = 30, 70
    for k, (gx, gy) in pos.items():
        for k2, (hx, hy) in pos.items():
            if k < k2 and abs(gx - hx) + abs(gy - hy) == 1:
                d.line(mx + gx * s, my + gy * s, mx + hx * s, my + hy * s, stroke=T.border, sw=2)
    for k, (gx, gy) in pos.items():
        d.circle(mx + gx * s, my + gy * s, 17, fill=T.card, stroke=T.fg2, sw=1.6)
        d.text(mx + gx * s, my + gy * s, k, size=13, family="mono", weight=700, fill=T.fg, anchor="middle")
    d.text(0, 0, "1  The map and the plans", size=14, weight=600, fill=T.fg)
    # plan table
    tx, ty = 330, 34
    rows = [("AGV 1", A1, ["(t=0, a -> b)", "(t=1, b -> c)"]),
            ("AGV 2", A2, ["(t=2, d -> b)", "(t=3, b -> e)"]),
            ("AGV 3", A3, ["(t=0, c -> f)"])]
    d.text(tx, ty, "plan p_i = sequence of (start time t, start s, goal g)", size=11.5, fill=T.muted)
    for i, (name, col, acts) in enumerate(rows):
        yy = ty + 30 + i * 30
        d.text(tx, yy, name, size=12.5, family="mono", weight=600, fill=col)
        d.text(tx + 80, yy, ",  ".join(acts), size=12, family="mono", fill=T.fg2)
    # ADG
    gy0 = 350
    d.text(0, gy0 - 40, "2  The ADG", size=14, weight=600, fill=T.fg)
    cols = [120, 340, 560, 780]
    r = {1: gy0 + 40, 3: gy0 + 140, 2: gy0 + 240}
    n11 = vnode(d, cols[0], r[1], "a[1,1]", "a -> b @0", A1)
    n12 = vnode(d, cols[1], r[1], "a[1,2]", "b -> c @1", A1, hl=True)
    n31 = vnode(d, cols[0], r[3], "a[3,1]", "c -> f @0", A3)
    n21 = vnode(d, cols[2], r[2], "a[2,1]", "d -> b @2", A2, hl=True)
    n22 = vnode(d, cols[3], r[2], "a[2,2]", "b -> e @3", A2)
    for nm, yy, col in (("AGV 1", r[1], A1), ("AGV 3", r[3], A3), ("AGV 2", r[2], A2)):
        d.text(cols[0] - 120, yy + 4, nm, size=12, family="mono", weight=600, fill=col)
    arrow(d, n11, n12, T1, label="Type 1", label_at=((n11.x1 + n12.x0) / 2, r[1] - 14))
    arrow(d, n21, n22, T1, label="Type 1", label_at=((n21.x1 + n22.x0) / 2, r[2] - 14))
    arrow(d, n31, n12, T2, dash="7 4", label="AGV 3 leaves c before AGV 1 enters",
          label_at=(cols[1] + 10, (r[3] + r[1]) / 2 + 6))
    arrow(d, n12, n21, T2, dash="7 4", label="AGV 1 leaves b before AGV 2 enters",
          label_at=((cols[1] + cols[2]) / 2 + 60, (r[1] + r[2]) / 2 + 8))
    # rule
    nx = 980
    note(d, nx, gy0 - 10, 420,
         "Type 1: consecutive actions of the same AGV, a[i,k] -> a[i,k+1]. "
         "Type 2: for AGVs i != j, an edge a[i,k] -> a[j,l] when s(i,k) = g(j,l) and t(i,k) <= t(j,l): "
         "the action that leaves a location must finish before the action that enters it may start.",
         title="The two edge rules (Hönig et al. 2019)", accent=T1, size=12)
    # cycle inset
    cx, cy = nx + 210, gy0 + 230
    d.text(nx, cy - 70, "3  A cycle: three AGVs rotate at t = 0", size=13, weight=600, fill=T.fg)
    tri = [(cx - 110, cy + 40), (cx, cy - 30), (cx + 110, cy + 40)]
    labs = [("x -> y", A1), ("y -> z", A2), ("z -> x", A3)]
    bs = [vnode(d, px_, py_, f"t=0", lab, col, w=110, h=44) for (px_, py_), (lab, col) in zip(tri, labs)]
    # x->y leaves x; z->x enters x : edge (x->y) -> (z->x); similarly
    arrow(d, bs[0], bs[2], RED, dash="7 4")
    arrow(d, bs[2], bs[1], RED, dash="7 4")
    arrow(d, bs[1], bs[0], RED, dash="7 4")
    d.text(cx, cy + 92, "each waits for another to leave: a cycle,", size=11.5, fill=RED, anchor="middle")
    d.text(cx, cy + 108, "only safe with perfectly synchronous moves", size=11.5, fill=RED, anchor="middle")
    frame(d, title="Building an action dependency graph",
          subtitle="Each action of each AGV is a vertex. Type 1 edges keep each AGV's own order; Type 2 edges "
                   "say who must clear a location before someone else enters it. The ADG keeps the plan's "
                   "order and forgets its exact times.",
          badge_key="illustrative",
          legend=[("arrow", T1, "Type 1 (same AGV)"), ("dasharrow", T2, "Type 2 (location hand-over)"),
                  ("dasharrow", RED, "cycle"), ("box", A1, "AGV 1"), ("box", A2, "AGV 2"), ("box", A3, "AGV 3")],
          footnote="a[i,k] is the k-th action of AGV i (a^i_k in the text); @t is its planned start time. "
                   "Construction as in Algorithm 1 of Hönig et al., RA-L 2019.")
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
        B[v] = vnode(d, xs[v], ys[v], f"{v}  d={dur[v]}", f"S={S[v]}  C={C[v]}", col[v], w=190, h=52,
                     hl=v in crit, sw=2.4 if v in crit else 1.4)
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
            _bar(d, x0, px, yy, S[v], C[v], v, T.green if v in crit else col[v], fill_a=0.3 if v in crit else 0.18)
        if nm == "AGV 3":
            _bar(d, x0, px, yy, C[v], LF[v], "slack", T.amber, dash="4 3", fill_a=0.06)
    _axis(d, x0, gy + 20 + 3 * 38 - 10, px, 0, M, label="t [s]")
    note(d, x0 + M * px + 60, gy - 10, 380,
         f"S(v) = max over predecessors u of C(u);  C(v) = S(v) + d(v). Makespan = max C = {M}. "
         "A delay on a critical action delays the end by the same amount. A delay on a[3,1] is absorbed up to "
         f"its slack ({slack['a[3,1]']}); beyond that, a[1,2] starts late and the end moves.",
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
