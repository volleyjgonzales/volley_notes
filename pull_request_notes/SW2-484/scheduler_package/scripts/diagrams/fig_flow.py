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


@figure("01_pipeline", "Scheduler::Plan pipeline", "01-software-background.md")
def pipeline():
    d = Doc("01_pipeline", "Scheduler::Plan — four principal stages",
            "PlanRequest flows through job expansion, tray assignment, AGV assignment and motion planning; "
            "each stage enriches the same ScheduleContext event DAG.")
    cw, gap, ch = 218, 40, 178
    stages = [
        ("Job expansion", "Validate base state, create ScheduleContext, expand each pending job.",
         ["PlanInsertJob()", "PlanRetrieveJob()", "PlanCleanGarageJob()"], ACT),
        ("Tray assignment", "Fill missing tray IDs and destinations; insert blocker relocations.",
         ["DoTrayAssignments(ctx)", "ResolveBlockingTrays()", "+ DAG dependencies"], TRAY),
        ("AGV assignment", "Pick a feasible AGV per tray move; add reposition and lift events.",
         ["DoAgvAssignments(ctx)", "cost: occupied+approach", "+ occupancy edges"], AGV),
        ("Motion planning", "Reduce and sanity-check, then plan timed motions and emit actions.",
         ["Reduce()", "PlanMotions(ctx)", "ResponseFromTrajectories"], BAY),
    ]
    top = 70
    boxes = []
    for i, (title, sub, lines, col) in enumerate(stages):
        x = i * (cw + gap)
        boxes.append(card(d, x, top, cw, ch, title=title, accent=col, lines=lines, sub=sub, num=i + 1,
                          line_size=12))
    for i in range(3):
        a, b = boxes[i], boxes[i + 1]
        connect(d, [(a.x1 + 6, a.cy), (b.x0 - 4, a.cy)], kind="flow", color=T.muted, sw=2, size=11)
    # request / response rails
    rail = 22
    total_w = boxes[-1].x1
    d.line(boxes[0].cx, rail + 14, boxes[0].cx, top - 4, stroke=T.muted, sw=2)
    d.arrowhead((boxes[0].cx, top - 2), (boxes[0].cx, rail), kind="filled", color=T.muted, size=10)
    chip(d, boxes[0].cx, rail, "PlanRequest", T.sky, anchor="middle", size=12.5)
    d.line(boxes[-1].cx, top - 2, boxes[-1].cx, rail + 16, stroke=T.muted, sw=2)
    d.arrowhead((boxes[-1].cx, rail + 13), (boxes[-1].cx, top), kind="filled", color=T.muted, size=10)
    chip(d, boxes[-1].cx, rail, "PlanResponse · Schedule", T.green, anchor="middle", size=12.5)
    mid_x0 = boxes[0].cx + 70
    mid_x1 = boxes[-1].cx - 110
    d.line(mid_x0, rail, mid_x1, rail, stroke=T.border, sw=1.2, dash="2 4")
    label_pill(d, (mid_x0 + mid_x1) / 2, rail, "Scheduler::Plan(request)", color=T.fg2, size=12.5, bg=T.bg)

    # DAG evolution strip
    sy = top + ch + 46
    sh = 128
    d.text(0, sy - 20, "ctx->events  ·  the same ScheduleEventDag, enriched stage by stage", size=12.5,
           family="mono", fill=T.muted)
    dags = [
        ({"b0": (.18, .3, BAY, "solid"), "t0": (.5, .3, TRAY, "hollow"), "b1": (.82, .3, BAY, "solid"),
          "t1": (.5, .78, TRAY, "hollow")},
         [("b0", "t0"), ("t0", "b1")], "abstract events; some TrayMoves are incomplete"),
        ({"b0": (.18, .3, BAY, "solid"), "t0": (.5, .3, TRAY, "solid"), "b1": (.82, .3, BAY, "solid"),
          "t1": (.5, .78, TRAY, "solid"), "x": (.18, .78, TRAY, "new")},
         [("b0", "t0"), ("t0", "b1"), ("x", "t0"), ("x", "t1")], "IDs + destinations filled; blocker inserted"),
        ({"b0": (.12, .3, BAY, "solid"), "t0": (.58, .3, TRAY, "solid"), "b1": (.88, .3, BAY, "solid"),
          "t1": (.58, .78, TRAY, "solid"), "x": (.35, .78, TRAY, "solid"), "a0": (.12, .78, AGV, "new"),
          "a1": (.35, .3, AGV, "new")},
         [("b0", "a1"), ("a1", "t0"), ("t0", "b1"), ("x", "t0"), ("x", "t1"), ("a0", "x")],
         "AgvMove reposition / lift + occupancy edges"),
        ({f"n{i}": (.1 + i * .16, .3 if i % 2 == 0 else .78, ACT, "solid") for i in range(6)},
         [("n0", "n1"), ("n1", "n2"), ("n0", "n2"), ("n2", "n3"), ("n3", "n4"), ("n4", "n5")],
         "ActionNode[] with integer parent indices"),
    ]
    for i, (nodes, edges, cap) in enumerate(dags):
        x = boxes[i].x0
        d.rect(x, sy, cw, sh, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
        _mini_dag(d, x + 14, sy + 14, cw - 28, 64, nodes, edges, square=(i == 3))
        for j, ln in enumerate(wrap(cap, cw - 24, S.small, "sans")):
            d.text(x + cw / 2, sy + 96 + j * 16, ln, size=S.small, fill=T.muted, anchor="middle")
    frame(d, title="Scheduler::Plan — four principal stages",
          subtitle="Every stage refines the result of the previous one. Simplified: several checks and branches "
                   "are omitted, and this is not a ROS executor or thread schedule.",
          badge_key="as-built",
          legend=[("dot", BAY, "BayTransition"), ("dot", TRAY, "TrayMove"), ("dot", AGV, "AgvMove"),
                  ("fill", ACT, "ActionNode"), ("hollow", TRAY, "incomplete TrayMove"), ("ring", T.muted, "added in this stage"),
                  ("arrow", T.faint, "must precede")],
          legend_title="Event DAG")
    return d


@figure("02_target_architecture", "Proposed solver boundary", "02-issue-and-proposal.md")
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


@figure("04_dependencies", "Dependency ordering", "01-software-background.md")
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
