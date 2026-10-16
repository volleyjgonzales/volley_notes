"""Motion planning figures for doc 01 section 20: where CHUGG sits between the two DAGs, and what a
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
        ("2  CHUGG", ["`Chugg::SolveSequential`", "MAPF with precedence:", "events in a topological order,",
                      "each timed against the motions", "already planned (SIPP, A*)"], T.amber),
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
          badge_key="concept",
          legend=[("box", T.violet, "task level: what, in which order"), ("box", T.amber, "motion planning: when, where"),
                  ("box", T.green, "execution graph (ADG)"), ("dashbox", T.sky, "outside the scheduler")],
          footnote="Stages 1-3 are in scheduler.cpp (Plan, PlanMotions, ResponseFromTrajectories). CHUGG's internals "
                   "are inferred from comments; motion_planner is not in the snapshots.")
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
          badge_key="concept",
          legend=[("box", T.green, "AGV 1's motions"), ("box", T.sky, "AGV 2's motions"),
                  ("dashbox", T.sky, "wait (no delta: dropped from the action DAG)")],
          footnote="Values from TEST(Scheduler, ContinuousStateToSchedule) in scheduler_tests.cpp. The test's comment "
                   "calls the fourth argument \"JobId\"; ResponseFromTrajectories reads it as the event vertex.")
    return d
