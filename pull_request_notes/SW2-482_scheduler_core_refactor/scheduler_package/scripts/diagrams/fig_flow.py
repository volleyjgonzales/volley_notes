"""Process / architecture figures: 01 pipeline, 02 target architecture, 04 dependency DAG."""
from __future__ import annotations

from components import (Box, card, chip, connect, frame, label_pill, note, num_badge, uml_class, class_size)
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

TRAY, AGV, BAY, ACT = T.amber, T.green, T.violet, T.sky


def _mini_dag(doc: Doc, x0, y0, w, h, nodes, edges, *, square=False):
    """Small glyph DAG inside a panel. nodes: id -> (fx, fy, color, style) with style in
    solid | hollow | new ; coordinates are fractions of the panel."""
    P = {}
    for k, (fx, fy, col, style) in nodes.items():
        P[k] = (x0 + fx * w, y0 + fy * h, col, style)
    r = 8
    for a, b, *rest in edges:
        ax, ay, *_ = P[a]
        bx, by, *_ = P[b]
        dashed = bool(rest and rest[0] == "dashed")
        import math
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        p = (ax + ux * (r + 2), ay + uy * (r + 2))
        q = (bx - ux * (r + 3), by - uy * (r + 3))
        doc.line(*p, *q, stroke=T.faint, sw=1.3, dash="3 3" if dashed else None, layer="edges")
        doc.arrowhead(q, p, kind="filled", color=T.faint, size=6, layer="edges")
    for k, (x, y, col, style) in P.items():
        if style == "new":
            doc.circle(x, y, r + 5, fill="none", stroke=col, sw=1.2, opacity=0.6)
        if square:
            doc.rect(x - r, y - r, 2 * r, 2 * r, rx=3, fill=col)
        elif style == "hollow":
            doc.circle(x, y, r, fill=T.bg, stroke=col, sw=1.6, dash="3 2.2")
        else:
            doc.circle(x, y, r, fill=col)


@figure("01_pipeline", "Scheduler::Plan pipeline", "01-software-background.html")
def pipeline():
    d = Doc("01_pipeline", "Scheduler::Plan: from jobs to an action DAG",
            "PlanRequest flows through job expansion, tray assignment and AGV assignment, which build the event DAG "
            "(task level); CHUGG plans timed motions from it (MAPF); the response builds a new graph, the action "
            "DAG (an action dependency graph), which Dispatch executes.")
    cw, gap, ch = 210, 38, 178
    stages = [
        ("Job expansion", "Validate the base state, create ScheduleContext, expand each pending job into events.",
         ["Plan<Type>Job()", "+ rule A/B/C edges"], ACT),
        ("Tray assignment", "Fill missing tray ids and destinations; insert moves for blocking trays.",
         ["DoTrayAssignments(ctx)", "+ freeing_moves edges"], TRAY),
        ("AGV assignment", "Match AGVs to tray moves; add approach, lift and lower events; Reduce + check.",
         ["DoAgvAssignments(ctx)", "Reduce(), SanityCheck"], AGV),
        ("Motion planning", "CHUGG: plan every event in topological order with SIPP, collision-free in time.",
         ["PlanMotions(ctx)", "-> ContinuousState"], BAY),
        ("Action DAG", "One action per motion that changes something; order shared space; copy event edges.",
         ["ResponseFromTrajectories", "-> Schedule.nodes"], T.green),
    ]
    top = 96
    boxes = []
    for i, (title, sub, lines, col) in enumerate(stages):
        x = i * (cw + gap)
        boxes.append(card(d, x, top, cw, ch, title=title, accent=col, lines=lines, sub=sub, num=i + 1,
                          line_size=12))
    for i in range(4):
        a, b = boxes[i], boxes[i + 1]
        connect(d, [(a.x1 + 6, a.cy), (b.x0 - 4, a.cy)], kind="flow", color=T.muted, sw=2, size=11)
    # dispatcher (outside the package)
    dx = boxes[-1].x1 + gap
    d.rect(dx, top, 170, ch, rx=10, fill=T.card, stroke=T.sky, sw=1.5, dash="6 4")
    d.text(dx + 16, top + 26, "Dispatch", size=15, weight=600, fill=T.fg)
    for j, ln in enumerate(["executes actions", "whose parents are", "done (the executor;", "not in this package)"]):
        d.text(dx + 16, top + 54 + j * 19, ln, size=S.small + 0.5, fill=T.muted)
    connect(d, [(boxes[-1].x1 + 6, boxes[-1].cy), (dx - 4, boxes[-1].cy)], kind="flow", color=T.muted, sw=2,
            size=11)
    label_pill(d, (boxes[-1].x1 + dx) / 2, boxes[-1].y1 + 22, "PlanResponse", color=T.green, size=11, bg=T.bg)
    # research vocabulary brackets
    def bracket(x0, x1, text, col):
        y = top - 22
        d.line(x0, y, x1, y, stroke=col, sw=2)
        d.line(x0, y, x0, y + 8, stroke=col, sw=2)
        d.line(x1, y, x1, y + 8, stroke=col, sw=2)
        label_pill(d, (x0 + x1) / 2, y - 14, text, color=col, size=12, bg=T.bg, family="sans")
    bracket(boxes[0].x0, boxes[2].x1, "build the event DAG: WHAT happens, in which order (task planning)", ACT)
    bracket(boxes[3].x0, boxes[3].x1, "MAPF: WHEN and WHERE", BAY)
    bracket(boxes[4].x0, boxes[4].x1, "ADG: safe execution order", T.green)
    bracket(dx, dx + 170, "executor", T.sky)
    chip(d, boxes[0].x0, 18, "PlanRequest", T.sky, size=12.5)
    connect(d, [(boxes[0].x0 + 12, 32), (boxes[0].x0 + 12, top - 2)], kind="flow", color=T.muted, sw=2, size=10)

    # representation strip
    sy = top + ch + 46
    sh = 142
    d.text(0, sy - 20, "what exists after each stage", size=12.5, family="mono", fill=T.muted)
    dags = [
        ({"b0": (.18, .3, BAY, "solid"), "t0": (.5, .3, TRAY, "hollow"), "b1": (.82, .3, BAY, "solid"),
          "t1": (.5, .78, TRAY, "hollow")},
         [("b0", "t0"), ("t0", "b1")], "event DAG: abstract events; some TrayMoves incomplete"),
        ({"b0": (.18, .3, BAY, "solid"), "t0": (.5, .3, TRAY, "solid"), "b1": (.82, .3, BAY, "solid"),
          "t1": (.5, .78, TRAY, "solid"), "x": (.18, .78, TRAY, "new")},
         [("b0", "t0"), ("t0", "b1"), ("x", "t0"), ("x", "t1")], "same DAG: ids and destinations filled; blocker added"),
        ({"b0": (.12, .3, BAY, "solid"), "t0": (.58, .3, TRAY, "solid"), "b1": (.88, .3, BAY, "solid"),
          "t1": (.58, .78, TRAY, "solid"), "x": (.35, .78, TRAY, "solid"), "a0": (.12, .78, AGV, "new"),
          "a1": (.35, .3, AGV, "new")},
         [("b0", "a1"), ("a1", "t0"), ("t0", "b1"), ("x", "t0"), ("x", "t1"), ("a0", "x")],
         "same DAG: AgvMoves and occupancy edges added, then reduced"),
    ]
    for i, (nodes, edges, cap) in enumerate(dags):
        x = boxes[i].x0
        d.rect(x, sy, cw, sh, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
        _mini_dag(d, x + 14, sy + 14, cw - 28, 64, nodes, edges)
        for j, ln in enumerate(wrap(cap, cw - 24, S.small, "sans")):
            d.text(x + cw / 2, sy + 96 + j * 16, ln, size=S.small, fill=T.muted, anchor="middle")
    # stage 4: timeline
    x = boxes[3].x0
    d.rect(x, sy, cw, sh, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    lanes = [(AGV, [(0.00, 0.35, False), (0.35, 0.55, True), (0.55, 0.9, False)]),
             (AGV, [(0.00, 0.25, True), (0.25, 0.6, False), (0.6, 0.8, False)]),
             (BAY, [(0.00, 0.6, True), (0.6, 0.75, False)])]
    for k, (col, segs) in enumerate(lanes):
        y = sy + 16 + k * 22
        for (f0, f1, wait) in segs:
            bx0 = x + 14 + f0 * (cw - 28)
            bw = (f1 - f0) * (cw - 28) - 3
            d.rect(bx0, y, bw, 15, rx=3, fill=T.bg_deep if wait else T.tint(col, 0.35, T.bg), stroke=col, sw=1,
                   dash="3 2" if wait else None)
    for j, ln in enumerate(wrap("ContinuousState: a timed trajectory per entity", cw - 24, S.small, "sans")):
        d.text(x + cw / 2, sy + 96 + j * 16, ln, size=S.small, fill=T.muted, anchor="middle")
    # stage 5: action DAG
    x = boxes[4].x0
    d.rect(x, sy, cw, sh, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    _mini_dag(d, x + 14, sy + 14, cw - 28, 64,
              {f"n{i}": (.1 + i * .16, .3 if i % 2 == 0 else .78, T.green, "solid") for i in range(6)},
              [("n0", "n1"), ("n1", "n2"), ("n0", "n2"), ("n2", "n3"), ("n3", "n4"), ("n4", "n5")], square=True)
    for j, ln in enumerate(wrap("a NEW graph: ActionNode[] with parent indices", cw - 24, S.small, "sans")):
        d.text(x + cw / 2, sy + 96 + j * 16, ln, size=S.small, fill=T.muted, anchor="middle")
    frame(d, title="Scheduler::Plan: from jobs to an action DAG",
          subtitle="Stages 1-3 build one event DAG; CHUGG turns it into timed trajectories; the response builds a second "
                   "DAG, of actions, from those trajectories. Simplified: checks and failure paths are omitted.",
          badge_key="as-built",
          legend=[("dot", BAY, "BayTransition"), ("dot", TRAY, "TrayMove"), ("dot", AGV, "AgvMove"),
                  ("hollow", TRAY, "incomplete TrayMove"), ("ring", T.muted, "added in this stage"),
                  ("fill", T.green, "ActionNode"), ("arrow", T.faint, "must precede")],
          legend_title="Graphs")
    return d


@figure("02_target_architecture", "Proposed solver boundary", "02-issue-and-proposal.html")
def target_architecture():
    d = Doc("02_target_architecture", "Proposed solver interface boundary",
            "Scheduler delegates tray and AGV assignment to swappable solver interfaces; default "
            "implementations reproduce current behaviour.")
    W = 960
    EX, NEW, CORE = T.sky, T.amber, T.violet
    sched = uml_class(d, W / 2, 0, "Scheduler", accent=EX, stereo="orchestrator · existing",
                      attrs=["- tray_solver_: tray_assignment::Solver", "- agv_solver_: agv_assignment::Solver",
                             "- gg_, table_, cost_model_, layout_  (owned)", "- services_: GarageServices"],
                      methods=["+ Plan(request): PlanResponse", "  keeps validation, job expansion,", "  ApplyTrayAssignment(),",
                               "  Reduce(), sanity checks, PlanMotions"], center_x=True)
    iy = sched.y1 + 70
    iw = 330
    lx, rx = 40, W - 40 - iw
    ti = uml_class(d, lx, iy, "tray_assignment::Solver", accent=NEW, stereo="interface", abstract=True, w=iw,
                   methods=["+ Solve(const Input&) const", "    : stdx::Expected<Result>  = 0"])
    ai = uml_class(d, rx, iy, "agv_assignment::Solver", accent=NEW, stereo="interface", abstract=True, w=iw,
                   methods=["+ SolveInPlace(const Input&,", "    ScheduleEventDag&) const", "    : stdx::Result  = 0"])
    dy = ti.y1 + 70
    td = uml_class(d, lx, dy, "tray_assignment::DefaultSolver", accent=NEW, stereo="default implementation", w=iw,
                   attrs=["- services_: const GarageServices&"],
                   methods=["+ Solve(input) const  // today:", "    DoTrayAssignments + helpers"])
    ad = uml_class(d, rx, dy, "agv_assignment::DefaultSolver", accent=NEW, stereo="default implementation", w=iw,
                   attrs=["- services_: const GarageServices&"],
                   methods=["+ SolveInPlace(input, events) const", "    // today: DoAgvAssignments + helpers"])
    # planner_core package
    py = max(td.y1, ad.y1) + 64
    ph = 96
    d.rect(0, py, W, ph, rx=10, fill=T.tint(CORE, 0.07, T.bg), stroke=CORE, sw=1.4)
    d.rect(0, py, 150, 26, rx=10, fill=T.tint(CORE, 0.25, T.bg))
    d.text(14, py + 13, "planner_core", size=12.5, family="mono", weight=700, fill=CORE)
    items = ["ScheduleEventDag", "ScheduleEvent", "TrayMove", "AgvMove", "DiscreteGarageState"]
    cx = 40
    for it in items:
        b = chip(d, cx, py + 58, it, CORE, size=12.5)
        cx = b.x1 + 18
    d.text(W - 16, py + 13, "unchanged in the first refactor", size=S.small, fill=T.muted, anchor="end")

    # relations
    connect(d, [(sched.x0 + 40, sched.y1), (sched.x0 + 40, sched.y1 + 30), (ti.cx, sched.y1 + 30), (ti.cx, ti.y0)],
            kind="assoc", color=T.fg2, label="Solve(input)", label_at=((sched.x0 + 40 + ti.cx) / 2, sched.y1 + 30))
    connect(d, [(sched.x1 - 40, sched.y1), (sched.x1 - 40, sched.y1 + 30), (ai.cx, sched.y1 + 30), (ai.cx, ai.y0)],
            kind="assoc", color=T.fg2, label="SolveInPlace(...)", label_at=((sched.x1 - 40 + ai.cx) / 2, sched.y1 + 30))
    connect(d, [(td.cx, td.y0), (ti.cx, ti.y1)], kind="real", color=NEW, label="implements",
            label_at=(td.cx, (td.y0 + ti.y1) / 2))
    connect(d, [(ad.cx, ad.y0), (ai.cx, ai.y1)], kind="real", color=NEW, label="implements",
            label_at=(ad.cx, (ad.y0 + ai.y1) / 2))
    connect(d, [(td.cx, td.y1), (td.cx, py)], kind="dep", color=CORE,
            label="reads events; returns Result", label_at=(td.cx, (td.y1 + py) / 2))
    connect(d, [(ad.cx, ad.y1), (ad.cx, py)], kind="dep", color=CORE,
            label="edits events (first pass)", label_at=(ad.cx, (ad.y1 + py) / 2))
    # middle notes
    nx = ti.x1 + 26
    nw = ai.x0 - 26 - nx
    note(d, nx, iy + 6, nw, "A test fake or a future optimal solver implements the same interface.",
         title="Strategy pattern")
    note(d, nx, dy + 30, nw, "Benchmarks (SW2-487) can drive a solver directly — no full Scheduler needed.",
         title="Benchmarkable")
    frame(d, title="Proposed solver interface boundary",
          subtitle="Solver contracts separate assignment policy from orchestration. Both default solvers get graph, "
                   "collision, cost and layout services through one const GarageServices&. The tray solver returns its "
                   "edits; the AGV solver edits the DAG in place until benchmarks allow the same change.",
          badge_key="proposed",
          legend=[("box", EX, "existing class"), ("box", NEW, "proposed type"), ("box", CORE, "existing package"),
                  ("assoc", T.fg2, "calls"), ("real", NEW, "realizes interface"), ("dep", CORE, "reads / edits")])
    return d


@figure("04_dependencies", "Dependency ordering", "01-software-background.html")
def dependencies():
    d = Doc("04_dependencies", "Dependency ordering, not geometric adjacency",
            "Example event DAG: an AGV must lift a blocking tray and repark it before the root tray can be "
            "moved to the bay. Columns give one valid topological order.")
    lane_w = 92
    nw, nh, gx = 162, 64, 26
    lanes = [("AGV A1", AGV), ("Trays", TRAY), ("Bay B7", BAY)]
    lane_h = 104
    x0 = lane_w + 16
    ncols = 5
    W = x0 + ncols * nw + (ncols - 1) * gx
    for i, (nm, col) in enumerate(lanes):
        y = i * lane_h
        d.rect(0, y, W, lane_h - 8, rx=10, fill=T.tint(col, 0.05, T.bg), stroke=T.tint(col, 0.3, T.bg), sw=1)
        d.text(16, y + (lane_h - 8) / 2, nm, size=13, weight=600, fill=col)
    ev = {
        "e0": (0, 0, "AgvMove", "A1 to T2, lift"),
        "e1": (1, 1, "TrayMove", "T2 (blocker) -> P20"),
        "e2": (2, 0, "AgvMove", "A1 to T1, lift"),
        "e3": (3, 1, "TrayMove", "T1 (root) -> B7"),
        "e4": (4, 2, "BayTransition", "B7: retrieve ready"),
    }
    B = {}
    for k, (col, lane, typ, txt) in ev.items():
        x = x0 + col * (nw + gx)
        y = lane * lane_h + (lane_h - 8 - nh) / 2
        c = lanes[lane][1]
        d.rect(x, y, nw, nh, rx=8, fill=T.card, stroke=c, sw=1.5)
        d.text(x + 10, y + 18, typ, size=11, family="mono", weight=600, fill=c)
        d.text(x + 10, y + 42, txt, size=12, family="mono", fill=T.fg)
        B[k] = BBox(x, y, x + nw, y + nh)

    def e(a, b, **kw):
        A, Bb = B[a], B[b]
        mx = (A.x1 + Bb.x0) / 2
        connect(d, [(A.x1, A.cy), (mx, A.cy), (mx, Bb.cy), (Bb.x0, Bb.cy)], kind="flow", size=9, **kw)

    e("e0", "e1", color=T.fg2)
    e("e1", "e2", color=T.fg2)
    e("e2", "e3", color=T.fg2)
    e("e3", "e4", color=T.fg2)
    # redundant transitive edge e1 -> e3, removed by Reduce()
    A, Bb = B["e1"], B["e3"]
    yb = A.y1 + 14
    connect(d, [(A.cx, A.y1), (A.cx, yb), (Bb.cx, yb), (Bb.cx, Bb.y1)], kind="flow", size=9, color=T.faint,
            dash="4 4", label="redundant: removed by Reduce()", label_at=((A.cx + Bb.cx) / 2, yb),
            label_color=T.muted)
    # topological order axis
    ay = len(lanes) * lane_h + 14
    d.line(x0, ay, W, ay, stroke=T.border, sw=1)
    for i in range(ncols):
        cx = x0 + i * (nw + gx) + nw / 2
        d.line(cx, ay - 4, cx, ay + 4, stroke=T.border, sw=1)
        d.text(cx, ay + 18, f"order {i}", size=S.small, family="mono", fill=T.muted, anchor="middle")
    d.text(16, ay + 18, "topological", size=S.small, fill=T.muted)
    frame(d, title="Dependency ordering, not geometric adjacency",
          subtitle="An edge u -> v means event u must complete before v may start. It says nothing about "
                   "distance or travel time. Any order that respects every edge is a valid replay order.",
          badge_key="illustrative",
          legend=[("arrow", T.fg2, "dependency (DAG edge)"), ("dasharrow", T.faint, "implied by a path; pruned"),
                  ("box", AGV, "AgvMove"), ("box", TRAY, "TrayMove"), ("box", BAY, "BayTransition")])
    return d


# --------------------------------------------------------------------------------------
# 96 — where the code is: lines per pipeline stage, in the scheduler and in library packages
# --------------------------------------------------------------------------------------

CODE_BY_STAGE = [
    # (row label, sub label, [(segment label, lines, color, in_scheduler)])
    ("Task planning", "stages 1-3", [("job expansion", 1430, "tp", 1.0), ("tray assignment", 1039, "tp", 0.72),
                                     ("AGV assignment", 1004, "tp", 0.5), ("validation", 113, "tp", 0.34),
                                     ("searches, filters (motion_planner)", 1420, "tp", None)]),
    ("Motion planning", "stage 4", [("PlanMotions", 63, "mp", 1.0),
                                    ("CHUGG sequential, SIPP, timeline (motion_planner)", 3870, "mp", None),
                                    ("not called: CBS solver, coalescing, debug printers", 660, "mp", -1)]),
    ("Action graph", "stage 5", [("motions -> action DAG", 544, "ag", 1.0)]),
    ("Orchestrator", "Plan(), errors", [("Plan()", 381, "orc", 1.0)]),
    ("Shared", "all stages", [("planner_core", 1454, "core", None), ("cost_functions", 501, "core", None)]),
]


@figure("96_code_by_stage", "Where the code is, by pipeline stage", "01-software-background.html")
def code_by_stage():
    d = Doc("96_code_by_stage", "Where the code is, by pipeline stage",
            "Lines of C++ per stage. Inside the scheduler package almost everything is task planning; the motion "
            "planner's size is in the motion_planner package, most of which the scheduler uses; the action graph is small.")
    col = {"tp": T.violet, "mp": T.sky, "ag": T.green, "orc": T.amber, "core": T.teal}
    LW, X0, K, H, GAP = 250, 270, 0.215, 36, 34
    y = 20
    d.text(X0, y - 4, "solid: scheduler package    pale, dashed outline: library package", size=S.small, fill=T.muted)
    y += 22
    for label, sub, segs in CODE_BY_STAGE:
        d.text(0, y + H / 2 - 7, label, size=13.5, weight=600, fill=T.fg)
        d.text(0, y + H / 2 + 10, sub, size=S.small, fill=T.muted)
        x = X0
        below = []
        for name, n, c, a in segs:
            w = max(n * K, 3)
            base = col[c]
            if a == -1:
                d.rect(x, y, w, H, rx=4, fill="none", stroke=T.faint, sw=1.2, dash="2 3")
                tcol = T.muted
            elif a is None:
                d.rect(x, y, w, H, rx=4, fill=T.tint(base, 0.16, T.bg), stroke=base, sw=1.2, dash="5 3")
                tcol = T.fg
            else:
                d.rect(x, y, w, H, rx=4, fill=T.tint(base, 0.25 + 0.6 * a, T.bg))
                tcol = T.bg if a >= 0.5 else T.fg
            txt = name if len(segs) == 1 else f"{name}  {n:,}"
            if text_width(txt, S.small, "sans", 600) + 16 < w:
                d.text(x + 8, y + H / 2, txt, size=S.small, weight=600 if a != -1 else 400, fill=tcol)
            else:
                below.append((x + w / 2, txt))
            x += w + 2
        total = sum(s[1] for s in segs if s[3] != -1)
        d.text(x + 8, y + H / 2, f"{total:,}", size=13, weight=700, family="mono", fill=T.fg2)
        for i, (cx, txt) in enumerate(below):
            d.line(cx, y + H, cx, y + H + 8, stroke=T.faint, sw=1)
            d.text(cx, y + H + 16, txt, size=S.small, fill=T.fg2, anchor="start" if cx < X0 + 600 else "end")
        y += H + GAP + (14 if below else 0)
    frame(d, title="Where the code is, by pipeline stage",
          subtitle="Lines of C++ (headers and sources, without tests). In the scheduler package, task planning is "
                   "about 3,590 of 4,570 lines (78%), the motion-planning adapter 63, the action graph about 540. "
                   "Counting the library code the scheduler actually calls, task planning is about 5,000 lines and motion "
                   "planning about 3,900; about 660 lines of motion_planner are never called. The action graph stays small.",
          badge_key="as-built",
          legend=[("box", T.violet, "task planning"), ("box", T.sky, "motion planning"), ("box", T.green, "action graph"),
                  ("box", T.amber, "orchestrator"), ("box", T.teal, "shared libraries"),
                  ("dashbox", T.fg2, "in a library package"), ("dashbox", T.faint, "in motion_planner, never called")],
          footnote="Scheduler: function definitions in scheduler.cpp and utils.cpp, grouped by the stage that calls "
                   "them (4,574 of 4,721 lines; the rest is includes and namespaces). Libraries: every .hpp and .cpp "
                   "in the motion_planner, planner_core and cost_functions snapshots; 'never called' = no call path from the "
                   "scheduler's code (found by tracing calls from its sources). Not counted: task_planner "
                   "(BottleneckAssignment, not in the snapshots), common_ros (the garage model, about 9,800 lines, used "
                   "by every stage) and tests (6,546 lines in scheduler, mostly end-to-end).")
    return d
