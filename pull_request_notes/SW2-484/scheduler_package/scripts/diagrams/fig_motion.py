"""Motion planning figures for doc 01 (Part IV, motion planning): where CHUGG sits between the two DAGs, and what a
ContinuousState holds (the ContinuousStateToSchedule test, drawn as a timeline)."""
from __future__ import annotations

from components import connect, frame, label_pill, note
from registry import figure
from svgkit import BBox, Doc
from theme import T

DOC1 = "01-software-background.html"


def _stage(d: Doc, x, y, w, h, title, lines, color, *, dashed=False, title_mono=False):
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=color, sw=1.5, dash="6 4" if dashed else None)
    d.text(x + 14, y + 20, title, size=13, weight=600, family="mono" if title_mono else "sans", fill=color)
    for i, ln in enumerate(lines):
        mono = ln.startswith("`")
        d.text(x + 14, y + 44 + i * 18, ln.strip("`"), size=11 if mono else 11.5, family="mono" if mono else "sans",
               fill=T.fg2)
    return BBox(x, y, x + w, y + h)


# --------------------------------------------------------------------------------------
# 91 — which graph is which
# --------------------------------------------------------------------------------------

@figure("91_planning_pipeline", "Event DAG, CHUGG, action DAG: the order of the pipeline", DOC1)
def planning_pipeline():
    d = Doc("91_planning_pipeline", "Two DAGs around one motion planner",
            "The textbook pipeline (task assignment, MAPF, ADG, executor) above the scheduler's: the event DAG is "
            "a task graph built before any timing, CHUGG plans timed motions from it, and only then is the action "
            "DAG (the ADG) built from CHUGG's trajectories.")
    W, H, GAP = 250, 150, 120
    xs = [i * (W + GAP) for i in range(4)]
    # textbook row
    d.text(0, -40, "Textbook pipeline (ADG papers and most MAPF execution work)", size=13, weight=600, fill=T.muted)
    book = [
        ("1  Tasks / goals", ["who goes where;", "for MAPF-PC also a", "precedence order between", "goals of different agents"]),
        ("2  MAPF", ["timed, collision-free paths", "for all agents at once", "(CBS, prioritized + SIPP, ...)"]),
        ("3  ADG", ["actions + Type 1 / Type 2", "edges, from the paths"]),
        ("4  Executor", ["dispatch an action when", "all its parents are done"]),
    ]
    bb = []
    for x, (t, ls) in zip(xs, book):
        bb.append(_stage(d, x, 0, W, H - 20, t, ls, T.faint))
    for a, b in zip(bb, bb[1:]):
        connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=T.faint, size=8)
    # ours
    Y = 230
    d.text(0, Y - 40, "The scheduler (Scheduler::Plan)", size=13, weight=600, fill=T.fg)
    ours = [
        ("1  Event DAG", ["`ctx->events : ScheduleEventDag`", "built by Plan*Job, tray and", "AGV assignment, Reduce()",
                          "WHAT happens, in which order;", "no times, no paths"], T.violet),
        ("2  CHUGG", ["`Chugg::SolveSequential`", "prioritized planning: events", "one at a time in a topological",
                      "order, each timed against the", "motions already planned (SIPP)"], T.amber),
        ("3  Action DAG = ADG", ["`ResponseFromTrajectories`", "one ActionNode per motion with", "a delta; same-entity,",
                                 "occupancy and event edges", "`-> PlanResponse.schedule.nodes`"], T.green),
        ("4  Dispatch", ["runs Schedule.nodes by", "parents (not in the", "snapshots)"], T.sky),
    ]
    ob = []
    for x, (t, ls, c) in zip(xs, ours):
        ob.append(_stage(d, x, Y, W, H + 20, t, ls, c, dashed=(c == T.sky)))
    labels = ["ScheduleEventDag", "ContinuousState", "PlanResponse"]
    for (a, b), lab in zip(zip(ob, ob[1:]), labels):
        connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=T.fg2, size=8)
        label_pill(d, (a.x1 + b.x0) / 2, a.cy - 16, lab, color=T.fg2, size=10)
    # correspondences
    for a, b in zip(bb, ob):
        d.line(a.cx, a.y1 + 4, b.cx, b.y0 - 52, stroke=T.border_soft, sw=1.2, dash="3 4")
    # event edges copied into the ADG
    e, adg = ob[0], ob[2]
    yb = e.y1 + 46
    connect(d, [(e.cx, e.y1), (e.cx, yb), (adg.cx, yb), (adg.cx, adg.y1)], kind="flow", color=T.violet, size=8,
            dash="6 4")
    label_pill(d, (e.cx + adg.cx) / 2, yb, "event edges copied in (TransferEventDagDepsToActionDag)", color=T.violet,
               size=10.5)
    note(d, 0, yb + 34, 4 * W + 3 * GAP,
         "Why it can look like ADG -> MAPF: the event DAG is also a DAG of discrete changes with "
         "\"must happen before\" edges, and a few of its edges are spatial (AddNodeArrivalDeps, path repair). "
         "But it is a task-level precedence graph made before any timing. The ADG in the textbook sense is "
         "step 3, built from CHUGG's output, and it inherits the event edges.", color=T.muted)
    frame(d, title="Two DAGs around one motion planner",
          subtitle="Order of the pipeline is MAPF -> ADG -> executor, as in the literature. What is different is "
                   "step 1: CHUGG's input is a precedence graph between events of many entities, not one goal per robot.",
          badge_key="as-built",
          legend=[("box", T.violet, "task level: what, in which order"), ("box", T.amber, "motion planning: when, where"),
                  ("box", T.green, "execution graph (ADG)"), ("dashbox", T.sky, "outside the scheduler")],
          footnote="Stages 1 and 3 are in scheduler.cpp (Plan, ResponseFromTrajectories); stage 2 is motion_planner "
                   "(chugg_common.cpp, chugg_sequential.cpp), called from PlanMotions. Dispatch is not in the snapshots.")
    return d


# --------------------------------------------------------------------------------------
# 92 — a ContinuousState drawn as a timeline
# --------------------------------------------------------------------------------------

@figure("92_continuous_state", "What a ContinuousState holds", DOC1)
def continuous_state():
    d = Doc("92_continuous_state", "A ContinuousState is a timeline per entity",
            "The ContinuousStateToSchedule test drawn as swimlanes: AGV 1 drives 10->9->11 in six seconds; AGV 2 "
            "waits at 6, then drives 6->9->12. Each bar is one Motion. The action DAG built from it orders AGV 2's "
            "entry into node 9 after AGV 1 has left it.")
    X0, PX, LANE = 150, 52, 74
    T_MAX = 12
    # axis
    ay = 2 * LANE + 26
    d.line(X0, ay, X0 + T_MAX * PX, ay, stroke=T.border, sw=1.2)
    for t in range(0, T_MAX + 1, 3):
        x = X0 + t * PX
        d.line(x, -8, x, ay, stroke=T.grid, sw=1)
        d.text(x, ay + 16, f"{t} s", size=11, family="mono", fill=T.muted, anchor="middle")
    d.text(X0 + T_MAX * PX + 14, ay, "time", size=11, fill=T.muted)
    lanes = [
        ("AgvId(1)", T.green, [(0, 3, "10 -> 9", "edge", 0), (3, 6, "9 -> 11", "edge", 0)]),
        ("AgvId(2)", T.sky, [(0, 6, "wait @ 6", "pose", 1), (6, 9, "6 -> 9", "edge", 1), (9, 12, "9 -> 12", "edge", 1)]),
    ]
    bars = {}
    for k, (name, col, ms) in enumerate(lanes):
        y = k * LANE
        d.text(0, y + 22, name, size=12.5, family="mono", weight=700, fill=col)
        d.text(0, y + 40, "Trajectory", size=10.5, family="mono", fill=T.muted)
        for (t0, t1, lab, kind, act) in ms:
            x0, x1 = X0 + t0 * PX + 2, X0 + t1 * PX - 2
            wait = kind == "pose"
            d.rect(x0, y + 6, x1 - x0, 44, rx=7, fill=T.bg if wait else T.tint(col, 0.18, T.bg), stroke=col, sw=1.3,
                   dash="4 3" if wait else None)
            d.text((x0 + x1) / 2, y + 22, lab, size=11.5, family="mono", weight=600, fill=T.fg if not wait else T.muted,
                   anchor="middle")
            d.text((x0 + x1) / 2, y + 39, f"action {act}", size=10, family="mono", fill=T.muted, anchor="middle")
            bars[(k, lab)] = BBox(x0, y + 6, x1, y + 50)
    # occupancy dependency: AGV1 leaves 9 (9 -> 11 ends at 6) before AGV2 enters 9 (6 -> 9 starts at 6)
    a, b = bars[(0, "9 -> 11")], bars[(1, "6 -> 9")]
    connect(d, [(a.x1 - 30, a.y1), (a.x1 - 30, (a.y1 + b.y0) / 2), (b.x0 + 30, (a.y1 + b.y0) / 2), (b.x0 + 30, b.y0)],
            kind="flow", color=T.amber, size=8)
    label_pill(d, X0 + 12.4 * PX + 120, LANE - 2, "occupancy edge in the action DAG:", color=T.amber, size=10.5,
               family="sans")
    label_pill(d, X0 + 12.4 * PX + 120, LANE + 16, "AGV 2 enters 9 after AGV 1 left it", color=T.amber, size=10.5,
               family="sans")
    # legend-ish explanation of one Motion
    my = ay + 46
    rows = ["Motion(entity, Interval(begin, length), collision_id, action_id, location)",
            "  entity        AgvId(2)",
            "  interval      [6 s, 9 s]            GetInterval().GetTimes()",
            "  collision_id  AGV (bare footprint)  AGV + tray of a size when loaded",
            "  action_id     1                     vertex of the AgvMove in ctx->events",
            "  location      Edge{6, 9}            a Pose for waits, lifts, state changes"]
    d.rect(0, my, 760, 22 + 18 * len(rows), rx=10, fill="#0B1222", stroke=T.border_soft, sw=1)
    for i, r in enumerate(rows):
        d.text(14, my + 20 + i * 18, r, size=11, family="mono", fill=T.fg if i == 0 else T.fg2)
    frame(d, title="A ContinuousState is a timeline per entity",
          subtitle="DiscreteGarageState is one snapshot. ContinuousState is every entity's Trajectory over continuous "
                   "time: back-to-back Motions, each a wait at a pose or a move along an edge.",
          badge_key="as-built",
          legend=[("box", T.green, "AGV 1's motions"), ("box", T.sky, "AGV 2's motions"),
                  ("dashbox", T.sky, "wait (no delta: dropped from the action DAG)")],
          footnote="Values from TEST(Scheduler, ContinuousStateToSchedule) in scheduler_tests.cpp. The test's comment "
                   "calls the fourth argument \"JobId\"; ResponseFromTrajectories reads it as the event vertex.")
    return d


# --------------------------------------------------------------------------------------
# 93 — SolveSequential step by step, and what a safe-interval table holds
# --------------------------------------------------------------------------------------

@figure("93_chugg_sequential", "SolveSequential step by step", DOC1)
def chugg_sequential():
    d = Doc("93_chugg_sequential", "SolveSequential: prioritized planning over the event DAG",
            "Setup once, then one pass over the events in topological order. AGV and tray events are planned by "
            "SIPP on the AGV's safe-interval table with every other entity frozen at its last pose; bay and VECS "
            "events get fixed durations. A final pairwise collision check returns the ContinuousState or nullopt.")
    W = 520
    # setup
    setup = ["InitializeEventOrder: topological order (= priority); replay checks",
             "every non-disabled AGV gets a SippAgv planner",
             "static filters: entities that never move block the graph",
             "initial motions carved into every AGV's safe-interval table",
             "one SIPP goal per AgvMove / TrayMove, in that order"]
    h0 = 34 + 19 * len(setup)
    d.rect(0, 0, W, h0, rx=10, fill=T.card, stroke=T.violet, sw=1.5)
    d.text(14, 18, "Setup  (constructor, SolveInitialization, MakeRootNode)", size=12.5, weight=600, fill=T.violet)
    for i, ln in enumerate(setup):
        d.text(14, 42 + i * 19, ln, size=11, fill=T.fg2)
    # loop
    y1 = h0 + 40
    connect(d, [(W / 2, h0), (W / 2, y1)], kind="flow", color=T.fg2, size=8)
    steps = [
        (T.amber, "for each event in the order", ["start = the entity's current end time"]),
        (T.amber, "wait for dependencies", ["GetDependencyCompletionTime: latest end of a",
                                            "dependency's motions; fill the gap with a wait"]),
    ]
    y = y1
    lh = 19
    boxes = []
    for col, title, lines in steps:
        h = 30 + lh * len(lines)
        d.rect(0, y, W, h, rx=8, fill=T.card, stroke=col, sw=1.3)
        d.text(14, y + 17, title, size=12, weight=600, fill=col)
        for i, ln in enumerate(lines):
            d.text(14, y + 38 + i * lh, ln, size=11, fill=T.fg2)
        boxes.append(BBox(0, y, W, y + h))
        y += h + 26
    connect(d, [(W / 2, boxes[0].y1), (W / 2, boxes[1].y0)], kind="flow", color=T.fg2, size=8)
    # branch
    bw = (W - 20) / 2
    by = y + 10
    agv = ["1  freeze every other dynamic entity", "    at its last pose, forever",
           "2  SippAgv::PlanEvents: SIPP for this", "    one event on the AGV's table",
           "3  unfreeze; append the motions",
           "4  DeconflictAgvs: carve them into", "    every other AGV's table for good"]
    bay = ["bay: door close / open + wait /", "    PROCESS_RETRIEVE 60 s; a closing", "    door first waits for the area",
           "VECS: vecs_transition seconds", "VRC: no branch (never created)"]
    hb = 34 + lh * max(len(agv), len(bay))
    d.rect(0, by, bw, hb, rx=8, fill=T.card, stroke=T.sky, sw=1.3)
    d.text(14, by + 17, "AgvMove / TrayMove", size=12, weight=600, family="mono", fill=T.sky)
    for i, ln in enumerate(agv):
        d.text(14, by + 40 + i * lh, ln, size=11, fill=T.fg2)
    d.rect(bw + 20, by, bw, hb, rx=8, fill=T.card, stroke=T.pink, sw=1.3)
    d.text(bw + 34, by + 17, "BayTransition / VecsTransition", size=12, weight=600, family="mono", fill=T.pink)
    for i, ln in enumerate(bay):
        d.text(bw + 34, by + 40 + i * lh, ln, size=11, fill=T.fg2)
    mid = boxes[1].y1 + (by - boxes[1].y1) / 2
    connect(d, [(W / 2, boxes[1].y1), (W / 2, mid), (bw / 2, mid), (bw / 2, by)], kind="flow", color=T.sky, size=8)
    connect(d, [(W / 2, mid), (bw + 20 + bw / 2, mid), (bw + 20 + bw / 2, by)], kind="flow", color=T.pink, size=8)
    # loop-back
    lx = -36
    yl = by + hb + 18
    connect(d, [(bw / 2, by + hb), (bw / 2, yl), (lx, yl), (lx, boxes[0].cy), (0, boxes[0].cy)], kind="flow",
            color=T.amber, size=8, dash="5 4")
    connect(d, [(bw + 20 + bw / 2, by + hb), (bw + 20 + bw / 2, yl), (bw / 2, yl)], kind="line", color=T.amber,
            dash="5 4")
    label_pill(d, lx, (yl + boxes[0].cy) / 2, "next event", color=T.amber, size=10, family="sans")
    # end
    ye = yl + 40
    d.rect(0, ye, W, 64, rx=8, fill=T.card, stroke=T.green, sw=1.4)
    d.text(14, ye + 18, "after the last event", size=12, weight=600, fill=T.green)
    d.text(14, ye + 40, "CheckCollisions over every pair of new motions: any hit -> nullopt;", size=11, fill=T.fg2)
    d.text(14, ye + 57, "else initial ContinuousState + new motions (GetUpdatedContinuousState)", size=11, fill=T.fg2)
    gx = bw + 20 + bw / 2
    connect(d, [(gx, yl), (gx, ye)], kind="flow", color=T.green, size=8)
    label_pill(d, gx + 10, (yl + ye) / 2, "order exhausted", color=T.green, size=10, family="sans", anchor="start")

    # right: safe-interval table rows
    X0, PX = W + 150, 30
    ty = 0
    d.text(X0 - 60, ty + 10, "AGV 2's SafeIntervalTable while planning its 6 -> 9 -> 12 move", size=12.5, weight=600,
           fill=T.fg)
    d.text(X0 - 60, ty + 30, "(the Figure 92 example; key = footprint AGV + vertex)", size=11, fill=T.muted)
    rows = [("vertex 9", [(0, 6, "AGV 1 passes: carved for good", "res")], "safe from 6 s on"),
            ("vertex 11", [(6, 13, "AGV 1 parked: frozen while planning", "tmp")], "safe until 6 s"),
            ("vertex 12", [], "always safe (no entry)")]
    ry = ty + 66
    for name, blocks, verdict in rows:
        d.text(X0 - 80, ry + 14, name, size=11.5, family="mono", fill=T.fg2)
        d.rect(X0, ry, 13 * PX, 28, rx=4, fill=T.tint(T.green, 0.16, T.bg), stroke=T.green, sw=1)
        for (t0, t1, lab, kind) in blocks:
            col = T.red if kind == "res" else T.amber
            d.rect(X0 + t0 * PX, ry, (t1 - t0) * PX, 28, rx=4, fill=T.tint(col, 0.3, T.bg), stroke=col, sw=1.2,
                   dash="4 3" if kind == "tmp" else None)
            d.text(X0 + 13 * PX + 12, ry + 14, lab, size=10.5, fill=col)
        d.text(X0 + 13 * PX + 12, ry + 14 + (16 if blocks else 0), verdict, size=10.5, fill=T.green)
        ry += 58
    for t in (0, 3, 6, 9, 12):
        d.text(X0 + t * PX, ry - 10, f"{t} s", size=10, family="mono", fill=T.muted, anchor="middle")
    note(d, X0 - 60, ry + 14, 560,
         "AGV 2 may enter 9 only after 6 s. Its goal is 12, and reaching 12 counts only because 12 stays safe "
         "forever afterwards. That rule plus the freeze is why an AGV that has not yet been planned to leave a "
         "node blocks it for every event planned before its departure (AddNodeArrivalDeps).",
         color=T.muted)
    frame(d, title="SolveSequential: prioritized planning over the event DAG",
          subtitle="One pass in topological order, never revisited. Only AGV moves are searched; everything else gets "
                   "a fixed duration. Safety comes from safe-interval tables, then a final pairwise check.",
          badge_key="as-built",
          legend=[("box", T.violet, "once per call"), ("box", T.amber, "per event"), ("box", T.sky, "SIPP search"),
                  ("box", T.pink, "fixed-duration events"), ("box", T.red, "reservation (permanent)"),
                  ("dashbox", T.amber, "sequential assumption (removed after the event)")],
          footnote="From chugg_common.cpp (InitializeEventOrder, SolveInitialization, MakeRootNode, "
                   "GetDependencyCompletionTime) and chugg_sequential.cpp (PlanNodeSequential, PlanEventSequential, "
                   "SetEventSafeIntervals). The table on the right is illustrative.")
    return d


# --------------------------------------------------------------------------------------
# 94 — trapezoid profiles, and three ways to time one straight run
# --------------------------------------------------------------------------------------

def _trap(d, v, a):
    import math
    return 2 * math.sqrt(d / a) if d < v * v / a else v / a + d / v


def _profile(t0, d, v, a):
    """Velocity profile points (t, v) of one rest-to-rest move."""
    import math
    if d < v * v / a:
        tp = math.sqrt(d / a)
        return [(t0, 0), (t0 + tp, a * tp), (t0 + 2 * tp, 0)]
    t1 = v / a
    T_ = _trap(d, v, a)
    return [(t0, 0), (t0 + t1, v), (t0 + T_ - t1, v), (t0 + T_, 0)]


@figure("94_trapezoid_runs", "Trapezoid profiles and three ways to time a run", DOC1)
def trapezoid_runs():
    import math
    d = Doc("94_trapezoid_runs", "How cost_functions times a move",
            "Left: trapezoidal and triangular velocity profiles. Right: three 2.29 m driving edges in a line with "
            "the default parameters, timed by stopping at every node (20.3 s), as one run (11.9 s), by SIPP's "
            "run-extension rule (11.3 s) and by cruise time only (6.9 s).")
    # ---- left panel: the two shapes (schematic)
    LX, LY, LW, LH = 0, 0, 380, 150

    def axes(x0, y0, w, h, xl, yl):
        d.line(x0, y0 + h, x0 + w, y0 + h, stroke=T.border, sw=1.2)
        d.line(x0, y0, x0, y0 + h, stroke=T.border, sw=1.2)
        d.text(x0 + w, y0 + h + 16, xl, size=10.5, fill=T.muted, anchor="end")
        d.text(x0 - 6, y0 - 8, yl, size=10.5, fill=T.muted)

    axes(LX, LY, LW, LH, "time", "speed")
    pts = [(LX, LY + LH), (LX + 90, LY + 30), (LX + 290, LY + 30), (LX + 380, LY + LH)]
    d.polyline(pts, stroke=T.green, sw=2.2, radius=0)
    d.line(LX, LY + 30, LX + 380, LY + 30, stroke=T.border_soft, sw=1, dash="3 4")
    d.text(LX + 190, LY + 18, "cruise at v", size=11, fill=T.green, anchor="middle")
    d.text(LX + 62, LY + 104, "slope a", size=10.5, fill=T.muted)
    d.text(LX + 190, LY + LH + 36, "d >= v*v/a :  T = v/a + d/v", size=11.5, family="mono", fill=T.fg, anchor="middle")
    ty = LY + LH + 90
    axes(LX, ty, LW, LH, "time", "speed")
    tri = [(LX, ty + LH), (LX + 140, ty + 70), (LX + 280, ty + LH)]
    d.polyline(tri, stroke=T.amber, sw=2.2, radius=0)
    d.line(LX, ty + 30, LX + 380, ty + 30, stroke=T.border_soft, sw=1, dash="3 4")
    d.text(LX + 300, ty + 22, "v never reached", size=11, fill=T.amber)
    d.text(LX + 190, ty + LH + 36, "d < v*v/a :  T = 2*sqrt(d/a)", size=11.5, family="mono", fill=T.fg, anchor="middle")
    d.text(LX, ty + LH + 70, "v²/a with defaults: drive 5.0 m, strafe 1.8 m,", size=11, fill=T.fg2)
    d.text(LX, ty + LH + 88, "turn 0.83 rad (47°), VRC 0.32 m", size=11, fill=T.fg2)

    # ---- right panel: three edges of 2.29 m
    v, a, L = 1.0, 0.2, 2.286
    RX, RY, RW, RH = 500, 0, 720, 210
    TMAX, VMAX = 21.0, 1.1
    sx = lambda t: RX + t / TMAX * RW
    sy = lambda u: RY + RH - u / VMAX * RH
    axes(RX, RY, RW, RH, "time [s]", "speed [m/s]")
    for t in range(0, 19, 3):
        d.text(sx(t), RY + RH + 14, str(t), size=10, family="mono", fill=T.muted, anchor="middle")
    for u in (0.5, 1.0):
        d.text(RX - 8, sy(u), f"{u:.1f}", size=10, family="mono", fill=T.muted, anchor="end")
        d.line(RX, sy(u), RX + RW, sy(u), stroke=T.grid, sw=1)
    # stop at every node
    stop = []
    t0 = 0
    for _ in range(3):
        stop += _profile(t0, L, v, a)
        t0 += _trap(L, v, a)
    d.polyline([(sx(t), sy(u)) for t, u in stop], stroke=T.red, sw=1.8, radius=0, dash="6 4")
    # one run
    run = _profile(0, 3 * L, v, a)
    d.polyline([(sx(t), sy(u)) for t, u in run], stroke=T.green, sw=2.4, radius=0)
    # node crossings on the run (TimeAtDistance)
    def tad(s, D):
        da = 0.5 * v * v / a
        if s <= da:
            return math.sqrt(2 * s / a)
        if s <= D - da:
            return v / a + (s - da) / v
        return _trap(D, v, a) - math.sqrt(2 * (D - s) / a)
    for k in (1, 2):
        t = tad(k * L, 3 * L)
        d.line(sx(t), sy(0), sx(t), sy(1.0) - 6, stroke=T.green, sw=1, dash="2 3")
        d.text(sx(t), sy(1.0) - 14, f"node {k}: {t:.1f} s", size=10, fill=T.green, anchor="middle")
    # bars: time charged by each rule
    by = RY + RH + 50
    bars = [("stop at every node: one trapezoid per edge (heuristic)", 3 * _trap(L, v, a), T.red),
            ("one trapezoid over the run (ConvertPosePathToTrajectory)", _trap(3 * L, v, a), T.green),
            ("SIPP: trapezoid for edge 1, then length / speed", _trap(L, v, a) + 2 * L / v, T.sky),
            ("cruise time only (GetEdgeMarginalDurations)", 3 * L / v, T.violet)]
    for i, (lab, t, col) in enumerate(bars):
        y = by + i * 34
        d.rect(RX, y, sx(t) - RX, 20, rx=4, fill=T.tint(col, 0.35, T.bg), stroke=col, sw=1.2)
        d.text(sx(t) + 8, y + 10, f"{t:.1f} s", size=11, family="mono", fill=col)
        d.text(sx(t) + 62, y + 10, lab, size=11, fill=T.fg2)
    frame(d, title="How cost_functions times a move",
          subtitle="Every edge, run and turn is a rest-to-rest trapezoid. Short moves never reach full speed, so the "
                   "way edges are grouped into runs changes the estimate a lot.",
          badge_key="as-built",
          legend=[("box", T.green, "one run (what the AGV does)"), ("box", T.red, "stop at every node"),
                  ("box", T.sky, "SIPP's charge"), ("box", T.violet, "admissible lower bound")],
          footnote="Formulas from cost_functions.cpp (Trapezoid, TimeAtDistance); parameters are the MotionCostParams "
                   "defaults (locomote 1.0 m/s, 0.2 m/s²); 2.29 m is the most common edge length in the Pecos layout.")
    return d
