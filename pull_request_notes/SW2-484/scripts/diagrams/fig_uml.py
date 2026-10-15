"""UML figures: 08 solver classes, 09 tray-solver sequence, 11 core classes, 12 event hierarchy,
13 ROS message composition."""
from __future__ import annotations

from components import (Box, chip, class_size, connect, frame, label_pill, note, uml_class)
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

M = 12  # member font size for dense UML figures


def gen_tree(doc: Doc, parent: BBox, children: list[BBox], color: str, bus_y: float | None = None, *,
             px: float | None = None):
    """UML generalisation drawn as one shared hollow triangle on the superclass ('tree style')."""
    px = parent.cx if px is None else px
    tri_h = 13
    if bus_y is None:
        bus_y = (parent.y1 + min(c.y0 for c in children)) / 2
    doc.arrowhead((px, parent.y1), (px, parent.y1 + 30), kind="triangle", color=color, size=11, sw=1.5)
    doc.line(px, parent.y1 + tri_h, px, bus_y, stroke=color, sw=1.5, layer="edges")
    xs = [c.cx for c in children] + [px]
    doc.line(min(xs), bus_y, max(xs), bus_y, stroke=color, sw=1.5, layer="edges")
    for c in children:
        doc.line(c.cx, bus_y, c.cx, c.y0, stroke=color, sw=1.5, layer="edges")


# --------------------------------------------------------------------------------------
# 11 — existing core classes
# --------------------------------------------------------------------------------------

@figure("11_uml_existing_core", "Existing core planner classes", "01-software-background.md")
def uml_core():
    d = Doc("11_uml_existing_core", "Existing core planner relationships",
            "UML class diagram of Scheduler, ScheduleContext, ScheduleEventDag, DagBase, DiscreteGarageState "
            "and the ScheduleEvent hierarchy.")
    ORCH, DATA, GRAPH, EV = T.sky, T.green, T.amber, T.violet
    gap = 92
    spec = dict(
        sched=("Scheduler", dict(stereo="orchestrator", accent=ORCH,
                                 attrs=["- layout_: GarageLayout", "- gg_: GarageGraph", "- table_: CollisionTable",
                                        "- motion_cost_: MotionCostModel", "- logger_: rclcpp::Logger"],
                                 methods=["+ Plan(request): PlanResponse", "+ DoTrayAssignments(ctx) const",
                                          "+ DoAgvAssignments(ctx) const", "+ PlanMotions(ctx)"])),
        ctx=("ScheduleContext", dict(stereo="mutable per-plan state", accent=DATA,
                                     attrs=["+ initial_state: DiscreteGarageState", "+ events: ScheduleEventDag",
                                            "+ scheduled_jobs: vector<ScheduledJobDataMsg>",
                                            "+ last_entity_event: GarageEntityEventMap",
                                            "+ first_tray_event: unordered_map<…>"],
                                     methods=["+ PushBackScheduledJob(job)"])),
        dag=("ScheduleEventDag", dict(stereo="event dependency graph", accent=GRAPH,
                                      methods=["+ AddEvent(event)", "+ GetEventFromVertex(v)", "+ Apply(state)"])),
        base=("DagBase<T>", dict(stereo="Boost adjacency_list template", accent=GRAPH,
                                 attrs=["  vertices hold shared_ptr<T>"],
                                 methods=["+ Add(v)", "+ AddDependency(a, b)", "+ WouldCreateCycle(a, b)",
                                          "+ Reduce()", "+ GetTopologicalOrdering()"])),
        state=("DiscreteGarageState", dict(stereo="world-state model", accent=DATA,
                                           attrs=["+ agvs, bays, trays, payloads, vrcs", "+ disabled_nodes, hash"],
                                           methods=["+ GetAgv(id)", "+ GetTray(id)", "+ OnEvent(change)"])),
        ev=("ScheduleEvent", dict(stereo="abstract base class", accent=EV, abstract=True,
                                  attrs=["# type_: ScheduleEventType", "- job_idx_: size_t"],
                                  methods=["+ Apply(state) const = 0", "+ GetGarageEntityId() const = 0"])),
    )
    size = {k: class_size(n, size=M, **{kk: vv for kk, vv in kw.items() if kk != "accent"}) for k, (n, kw) in spec.items()}
    colA = max(size["ctx"][0], size["state"][0], size["sched"][0])
    colB = max(size["dag"][0], size["ev"][0])
    colC = size["base"][0]
    xA, xB = 0, colA + gap
    xC = xB + colB + gap + 24
    W = xC + colC

    def draw(k, x, y, w):
        n, kw = spec[k]
        return uml_class(d, x, y, n, size=M, w=w, **kw)

    sched = draw("sched", xA, 0, colA)
    # mental-model note to the right of Scheduler
    note(d, xB, 14, W - xB,
         "Scheduler is the conductor, ScheduleContext the score being annotated, ScheduleEventDag the "
         "dependency structure of abstract work, and DiscreteGarageState the simulated world on which "
         "that work is replayed.", title="Shortest mental model", accent=T.border)
    y2 = sched.y1 + 76
    ctx = draw("ctx", xA, y2, colA)
    dag = draw("dag", xB, y2, colB)
    base = draw("base", xC, y2, colC)
    y3 = max(ctx.y1, dag.y1, base.y1) + 70
    state = draw("state", xA, y3, colA)
    ev = draw("ev", xB, y3, colB)
    # subclasses
    subs = ["TrayMove", "AgvMove", "BayTransition", "VecsTransition", "VrcTransition"]
    sw_ = [class_size(s, compact=True)[0] for s in subs]
    sgap = (W - sum(sw_)) / (len(subs) - 1)
    y4 = max(state.y1, ev.y1) + 74
    kids = []
    x = 0
    for s, w in zip(subs, sw_):
        kids.append(uml_class(d, x, y4, s, accent=EV, compact=True, w=w))
        x += w + sgap
    gen_tree(d, ev, kids, EV, bus_y=y4 - 30)
    d.text(W, y4 - 44, "members: see the ScheduleEvent hierarchy figure", size=S.small, fill=T.muted, anchor="end")

    # relations
    my = (sched.y1 + ctx.y0) / 2
    connect(d, [(sched.cx, sched.y1), (sched.cx, ctx.y0)], kind="dep", color=ORCH,
            label="«create» one per Plan()", label_at=(sched.cx, my))
    connect(d, [(ctx.x1, dag.y0 + 60), (dag.x0, dag.y0 + 60)], kind="comp", color=DATA, mult_end="1",
            label="events", label_at=((ctx.x1 + dag.x0) / 2 + 4, dag.y0 + 40))
    connect(d, [(ctx.cx, ctx.y1), (state.cx, state.y0)], kind="comp", color=DATA,
            label="initial_state", label_at=(ctx.cx, (ctx.y1 + state.y0) / 2))
    connect(d, [(dag.x1, dag.y0 + 60), (base.x0, dag.y0 + 60)], kind="inh", color=GRAPH,
            label="T=ScheduleEvent", label_at=((dag.x1 + base.x0) / 2, dag.y0 + 86))
    connect(d, [(dag.cx, dag.y1), (ev.cx, ev.y0)], kind="agg", color=GRAPH, mult_end="0..*",
            label="shared_ptr vertices", label_at=(dag.cx, (dag.y1 + ev.y0) / 2))
    connect(d, [(ev.x0, ev.cy), (state.x1, ev.cy)], kind="dep", color=EV,
            label="Apply() mutates", label_at=((ev.x0 + state.x1) / 2, ev.cy - 20))
    frame(d, title="Existing core planner relationships",
          subtitle="What Scheduler::Plan works with today. Attributes are abridged; names follow scheduler.hpp, "
                   "event_dag.hpp and schedule_events.hpp.",
          badge_key="as-built",
          legend=[("comp", DATA, "composition (owns member)"), ("agg", GRAPH, "shared ownership"),
                  ("inh", EV, "inheritance (is-a)"), ("dep", T.fg2, "dependency / «create»")])
    return d


# --------------------------------------------------------------------------------------
# 12 — event hierarchy
# --------------------------------------------------------------------------------------

@figure("12_uml_event_hierarchy", "ScheduleEvent hierarchy", "01-software-background.md")
def uml_events():
    d = Doc("12_uml_event_hierarchy", "Existing ScheduleEvent inheritance hierarchy",
            "ScheduleEvent abstract base class with TrayMove and AgvMove (assignment-oriented) and BayTransition, "
            "VecsTransition, VrcTransition (resource-state transitions).")
    BASE, MOVE, RES = T.sky, T.green, T.violet
    base_spec = dict(stereo="abstract base class", accent=BASE, abstract=True,
                     attrs=["- type_: ScheduleEventType", "- job_idx_: unsigned int  // set once"],
                     methods=["+ Apply(state) const = 0", "+ GetGarageEntityId() const = 0", "+ GetType() const",
                              "+ GetJobIndex() const", "+ ToString() const  virtual", "+ ~ScheduleEvent()  virtual",
                              "  copy-constructible, not copy-assignable"])
    left = [
        ("TrayMove", ["- tray_id_: optional<uint16_t>", "- dest_: optional<GaragePoseMsg>",
                      "- agv_id_: optional<uint16_t>"],
         ["+ Assigned() const", "+ Get/SetTrayId(id)", "+ Get/SetDest(dest)", "+ Get/SetAgvId(id)",
          "+ Apply(state) const"]),
        ("AgvMove", ["- discrete_change_: variant<", "    AgvLiftChangedMsg,", "    AgvPoseChangedMsg>"],
         ["+ GetAgvId() const", "+ Get/SetDiscreteChange()", "+ GetSrc() / GetDest() const  // nullopt for lifts",
          "+ Apply(state) const  // std::visit"]),
    ]
    right = [
        ("BayTransition", ["- src_state_: DiscreteBayStateMsg", "- command_: BayCommandMsg"],
         ["+ GetBayId() / Get/SetSourceState()", "+ Get/SetCommand()", "+ Apply(state) const"]),
        ("VecsTransition", ["- state_change_: VecsStateChangedMsg"],
         ["+ GetVecsId() / Get/SetStateChange()", "+ Apply(state) const"]),
        ("VrcTransition", ["- state_change_: VrcStateChangedMsg", "- from_vrc_node_id_: uint32_t",
                           "- to_vrc_node_id_: uint32_t"],
         ["+ GetVrcId() / GetRequestedFloor()", "+ GetFromVrcNodeId() / GetToVrcNodeId()", "+ Apply(state) const",
          "  // not created by the scheduler package"]),
    ]
    lw = max(class_size(n, attrs=a, methods=m, size=M)[0] for n, a, m in left)
    rw = max(class_size(n, attrs=a, methods=m, size=M)[0] for n, a, m in right)
    gutter = 120
    gp = 18  # group padding
    W = gp + lw + gp + gutter + gp + rw + gp
    spine_x = gp + lw + gp + gutter / 2
    bw, bh = class_size("ScheduleEvent", size=M, **{k: v for k, v in base_spec.items() if k != "accent"})
    base = uml_class(d, spine_x - bw / 2, 0, "ScheduleEvent", size=M, **base_spec)
    note(d, base.x1 + 30, 6, W - base.x1 - 30,
         "The DAG stores shared_ptr<ScheduleEvent>. During replay the concrete subclass's Apply(...) runs "
         "through virtual dispatch and mutates a DiscreteGarageState.", title="Runtime polymorphism")
    gy = base.y1 + 64
    # groups
    lx0, rx0 = 0, spine_x + gutter / 2 - gp
    lkids, rkids = [], []
    y = gy + 40
    for n, a, m in left:
        b = uml_class(d, lx0 + gp, y, n, accent=MOVE, attrs=a, methods=m, size=M, w=lw)
        lkids.append(b)
        y = b.y1 + 22
    lh = y - 22 + gp - gy
    y = gy + 40
    for n, a, m in right:
        b = uml_class(d, rx0 + gp, y, n, accent=RES, attrs=a, methods=m, size=M, w=rw)
        rkids.append(b)
        y = b.y1 + 22
    rh = y - 22 + gp - gy
    for x0_, w_, h_, col, lab in ((lx0, lw + 2 * gp, lh, MOVE, "assignment-oriented events"),
                                  (rx0, rw + 2 * gp, rh, RES, "resource-state transitions")):
        d.rect(x0_, gy, w_, h_, rx=12, fill=T.tint(col, 0.04, T.bg), stroke=T.tint(col, 0.45, T.bg), sw=1,
               dash="6 5", layer="under")
        d.text(x0_ + 16, gy + 20, lab, size=12, family="mono", weight=600, fill=col)
    # spine with shared triangle
    d.arrowhead((spine_x, base.y1), (spine_x, base.y1 + 30), kind="triangle", color=BASE, size=11, sw=1.5)
    last = max(b.y0 + 34 for b in lkids + rkids)
    d.line(spine_x, base.y1 + 13, spine_x, last, stroke=BASE, sw=1.5, layer="edges")
    for b in lkids:
        d.polyline([(spine_x, b.y0 + 34), (b.x1, b.y0 + 34)], stroke=BASE, sw=1.5, radius=0)
        d.circle(spine_x, b.y0 + 34, 3, fill=BASE)
    for b in rkids:
        d.polyline([(spine_x, b.y0 + 34), (b.x0, b.y0 + 34)], stroke=BASE, sw=1.5, radius=0)
        d.circle(spine_x, b.y0 + 34, 3, fill=BASE)
    frame(d, title="Existing ScheduleEvent inheritance hierarchy",
          subtitle="A hollow triangle marks public inheritance and points to the base class: \"TrayMove is a "
                   "ScheduleEvent\". It does not express execution order, and the subclasses are siblings, not phases.",
          badge_key="as-built",
          legend=[("inh", BASE, "public inheritance (is-a)"), ("box", BASE, "abstract base class"),
                  ("box", MOVE, "movement / assignment event"), ("box", RES, "resource-state transition")])
    return d


# --------------------------------------------------------------------------------------
# 08 — proposed solver UML
# --------------------------------------------------------------------------------------

@figure("08_uml_solver", "Proposed tray_assignment classes", "02-issue-and-proposal.md")
def uml_solver():
    d = Doc("08_uml_solver", "Proposed tray_assignment class structure",
            "Strategy pattern: Scheduler holds a tray_assignment::Solver; DefaultSolver and a test fake realize it; "
            "Solve takes a read-only Input and returns stdx::Expected<Result>; Scheduler applies the Result.")
    EX, NEW, TEST, PURE = T.sky, T.amber, T.teal, T.green
    gap = 110
    sched = uml_class(d, 0, 0, "Scheduler", accent=EX, stereo="existing · abridged", size=M,
                      attrs=["- services_: GarageServices", "- tray_solver_:", "    unique_ptr<tray_assignment::Solver>"],
                      methods=["+ Plan(request): PlanResponse", "  // Solve(), then tray_assignment::",
                               "  // ApplyTrayAssignment(*ctx, result)"])
    req = uml_class(d, sched.x1 + gap, 0, "Input", accent=NEW, stereo="struct · proposed · read-only", size=M,
                    attrs=["+ initial_state: const DiscreteGarageState&", "+ events: const ScheduleEventDag&"])
    res = uml_class(d, req.x1 + 60, 0, "Result", accent=NEW, stereo="struct · proposed · returned", size=M,
                    attrs=["+ fills: vector<TrayFill>", "+ edits: vector<DagEdit>  (ordered)",
                           "+ first_tray_event:", "    unordered_map<uint16_t, ScheduleEventSPtr>"])
    iy = max(sched.y1, req.y1, res.y1) + 90
    iface = uml_class(d, sched.x0 + 30, iy, "Solver", accent=NEW, stereo="interface · tray_assignment",
                      abstract=True, size=M, center_x=False,
                      methods=["+ Solve(input: const Input&) const", "    : stdx::Expected<Result> = 0",
                               "+ ~Solver()  virtual"])
    dy = iface.y1 + 90
    dflt = uml_class(d, 0, dy, "DefaultSolver", accent=NEW, stereo="default implementation", size=M,
                     attrs=["- services_: const GarageServices&"],
                     methods=["+ Solve(input) const", "    : stdx::Expected<Result>",
                              "  (per-event loop over a private Pass)"])
    fake = uml_class(d, dflt.x1 + 70, dy, "FakeSolver", accent=TEST, stereo="test double", size=M,
                     attrs=["+ canned: stdx::Expected<Result>"],
                     methods=["+ Solve(input) const", "    : stdx::Expected<Result>"])
    fy = max(dflt.y1, fake.y1) + 80
    free = uml_class(d, 0, fy, "tray_assignment (free functions)", accent=PURE, stereo="namespace · pure", size=M,
                     methods=["+ ChooseEmptyTray(svc, state, dest)", "    : stdx::Expected<TrayChoice>",
                              "+ ResolveBlockingTrays(svc, request)", "    : stdx::Expected<BlockingResolution>",
                              "+ ChooseParkingSpot(svc, state, tray, job)", "    : stdx::Expected<ParkingPlan>",
                              "+ FindCriticalPath(svc, state, tray, dest)", "    : stdx::Expected<CriticalPath>"])
    # relations
    connect(d, [(sched.cx, sched.y1), (sched.cx, iface.y0)], kind="assoc", color=EX, mult_end="1",
            label="tray_solver_", label_at=(sched.cx, (sched.y1 + iface.y0) / 2))
    connect(d, [(sched.x1, sched.y0 + 50), (req.x0, sched.y0 + 50)], kind="dep", color=EX,
            label="«create»", label_at=((sched.x1 + req.x0) / 2, sched.y0 + 34))
    connect(d, [(iface.x1, iface.y0 + 50), (req.cx, iface.y0 + 50), (req.cx, req.y1)], kind="dep", color=NEW,
            label="«read»", label_at=(req.cx, (req.y1 + iface.y0 + 50) / 2))
    connect(d, [(iface.x1, iface.y0 + 84), (res.cx, iface.y0 + 84), (res.cx, res.y1)], kind="dep", color=NEW,
            label="«return»", label_at=(res.cx, (res.y1 + iface.y0 + 84) / 2))
    top = min(sched.y0, req.y0, res.y0) - 40
    connect(d, [(sched.cx + 60, sched.y0), (sched.cx + 60, top), (res.cx + 60, top), (res.cx + 60, res.y0)],
            kind="dep", color=EX, label="«apply» via ApplyTrayAssignment: the only write to ctx", label_at=((sched.cx + res.cx) / 2 + 60, top))
    bus = dy - 40
    d.arrowhead((iface.cx, iface.y1), (iface.cx, iface.y1 + 30), kind="triangle", color=NEW, size=11, sw=1.5)
    d.line(iface.cx, iface.y1 + 13, iface.cx, bus, stroke=NEW, sw=1.5, dash="6 4", layer="edges")
    d.line(min(dflt.cx, iface.cx), bus, max(fake.cx, iface.cx), bus, stroke=NEW, sw=1.5, dash="6 4", layer="edges")
    for b in (dflt, fake):
        d.line(b.cx, bus, b.cx, b.y0, stroke=NEW, sw=1.5, dash="6 4", layer="edges")
    label_pill(d, (iface.cx + fake.cx) / 2 + 30, bus, "realize", color=NEW)
    connect(d, [(dflt.cx, dflt.y1), (dflt.cx, free.y0)], kind="dep", color=PURE, label="«call»",
            label_at=(dflt.cx, (dflt.y1 + free.y0) / 2))
    note(d, free.x1 + 50, free.y0, 330,
         "Scheduler's job methods (PlanReadyForInsertJob, PlanChargePayloadJob, ...) call the same free "
         "functions with services_. No back-pointer to Scheduler is needed.", title="Shared with job planning")
    note(d, free.x1 + 50, free.y0 + 120, 330,
         "GarageServices holds const references to gg_, table_, cost_model_ and the layout. Scheduler owns "
         "them and must outlive every solver.", title="Lifetime rule")
    frame(d, title="Proposed tray_assignment class structure",
          subtitle="Scheduler calls a stable interface. The solver reads an Input, returns stdx::Expected<Result>, "
                   "and never edits the caller's context; Scheduler applies the Result in one place.",
          badge_key="proposed",
          legend=[("box", EX, "existing class"), ("box", NEW, "proposed type"), ("box", PURE, "pure free functions"),
                  ("box", TEST, "test double"), ("assoc", EX, "association"), ("real", NEW, "realization"),
                  ("dep", T.fg2, "dependency")])
    return d


# --------------------------------------------------------------------------------------
# 09 — sequence
# --------------------------------------------------------------------------------------

@figure("09_sequence_tray", "Tray solver sequence", "02-issue-and-proposal.md")
def seq_tray():
    d = Doc("09_sequence_tray", "Proposed tray-solver interaction",
            "Sequence: Scheduler builds Input, calls Solve; the solver reads the topological order, records blocker "
            "moves and dependencies in a Result and returns it; Scheduler applies the Result to the DAG.")
    parts = [("caller", ":SchedulerRos", T.muted), ("sched", ":Scheduler", T.sky),
             ("solver", "tray_solver_ : tray_assignment::Solver", T.amber), ("dag", "ctx->events : ScheduleEventDag", T.violet)]
    xs = {"caller": 40, "sched": 230, "solver": 560, "dag": 960}
    head_y = 0
    for k, label, col in parts:
        w = text_width(label, 12.5, "mono", 600) + 28
        d.rect(xs[k] - w / 2, head_y, w, 38, rx=8, fill=T.card, stroke=col, sw=1.5)
        d.text(xs[k], head_y + 19, label, size=12.5, family="mono", weight=600, fill=col, anchor="middle")
    y = 70
    rows = []
    step = 46
    end_y = 0

    def msg(a, b, text, *, ret=False, y_=None, col=T.fg2):
        yy = y_
        x1, x2 = xs[a], xs[b]
        off = 6
        xa = x1 + (off if x2 > x1 else -off)
        xb = x2 - (off if x2 > x1 else -off)
        d.line(xa, yy, xb, yy, stroke=col, sw=1.5, dash="6 4" if ret else None, layer="edges")
        d.arrowhead((xb, yy), (xa, yy), kind="open" if ret else "filled", color=col, size=9)
        tx = (xa + xb) / 2
        label_pill(d, tx, yy - 13, text, color=col if not ret else T.muted, bg=T.bg, size=12)

    def selfmsg(a, text, y_, col=T.fg2, h=26):
        x = xs[a] + 6
        d.polyline([(x, y_), (x + 34, y_), (x + 34, y_ + h), (x + 6, y_ + h)], stroke=col, sw=1.5, radius=4)
        d.arrowhead((x + 2, y_ + h), (x + 34, y_ + h), kind="filled", color=col, size=8)
        d.text(x + 44, y_ + h / 2, text, size=12, family="mono", fill=col)

    # activations (drawn first, under messages)
    y = 80
    msg("caller", "sched", "Plan(request)", y_=y, col=T.sky)
    a_sched0 = y
    y += step
    selfmsg("sched", "validate, expand jobs into ctx", y)
    y += step + 6
    msg("sched", "solver", "Solve(Input{initial_state, events})", y_=y, col=T.amber)
    a_solver0 = y
    y += step
    msg("solver", "dag", "GetTopologicalOrdering()  const", y_=y, col=T.violet)
    a_dag = [(y, y + 34)]
    y += 34
    msg("dag", "solver", "ordering", ret=True, y_=y)
    y += 40
    loop_y0 = y - 18
    selfmsg("solver", "fill tray id / destination (pure helpers)", y)
    y += step + 2
    opt_y0 = y - 14
    selfmsg("solver", "record AddEvent(blocker move) in result.edits", y + 8)
    y += 40
    selfmsg("solver", "record AddDependency(blocker, root)", y + 6)
    y += 28
    opt_y1 = y + 14
    y += 40
    selfmsg("solver", "result.first_tray_event[tray] = first move", y)
    y += 40
    loop_y1 = y
    y += 30
    msg("solver", "sched", "stdx::Expected<Result>", ret=True, y_=y)
    a_solver1 = y
    y += step
    msg("sched", "dag", "ApplyTrayAssignment: replay edits, set fills", y_=y, col=T.violet)
    a_dag.append((y, y + 34))
    y += 34
    msg("dag", "sched", "stdx::Result (cycle check)", ret=True, y_=y)
    y += step
    selfmsg("sched", "AGV assignment (next stage)", y)
    y += step
    msg("sched", "caller", "PlanResponse", ret=True, y_=y)
    a_sched1 = y
    end_y = y + 30
    # lifelines + activation bars (under layer)
    for k, _, col in parts:
        d.line(xs[k], 38, xs[k], end_y, stroke=T.border, sw=1.2, dash="4 5", layer="under")
    for k, y0, y1, col in (("sched", a_sched0, a_sched1, T.sky), ("solver", a_solver0, a_solver1, T.amber)):
        d.rect(xs[k] - 6, y0, 12, y1 - y0, rx=2, fill=T.tint(col, 0.35, T.bg), stroke=col, sw=1, layer="under")
    for y0, y1 in a_dag:
        d.rect(xs["dag"] - 6, y0, 12, y1 - y0, rx=2, fill=T.tint(T.violet, 0.35, T.bg), stroke=T.violet, sw=1,
               layer="under")
    # combined fragments
    fx0, fx1 = xs["solver"] - 120, xs["dag"] + 130
    for (y0, y1, tag, guard, inset) in ((loop_y0, loop_y1, "loop", "[for each event in topological order]", 0),
                                         (opt_y0, opt_y1, "opt", "[route to target is blocked]", 14)):
        d.rect(fx0 + inset, y0, fx1 - fx0 - 2 * inset, y1 - y0, rx=6, fill="none", stroke=T.faint, sw=1.2,
               layer="under")
        tw = text_width(tag, 11.5, "mono", 700) + 16
        d.path(f"M{fx0 + inset} {y0 + 6} Q{fx0 + inset} {y0} {fx0 + inset + 6} {y0} L{fx0 + inset + tw + 8} {y0} "
               f"L{fx0 + inset + tw + 8} {y0 + 12} L{fx0 + inset + tw} {y0 + 20} L{fx0 + inset} {y0 + 20} Z",
               fill=T.muted_bg, stroke=T.faint, sw=1, layer="under")
        d.text(fx0 + inset + 8, y0 + 10, tag, size=11.5, family="mono", weight=700, fill=T.fg2)
        d.text(fx0 + inset + tw + 16, y0 + 10, guard, size=11.5, family="mono", fill=T.muted)
    frame(d, title="Proposed tray-solver interaction",
          subtitle="The solver only reads the DAG. Blocker moves and edges are recorded in the returned Result; "
                   "Scheduler replays them into ctx->events in one step, so a failed Solve leaves ctx untouched.",
          badge_key="proposed",
          legend=[("arrow", T.fg2, "synchronous call"), ("dep", T.muted, "return"),
                  ("box", T.amber, "activation (executing)"), ("dashbox", T.faint, "combined fragment (loop / opt)")])
    return d


# --------------------------------------------------------------------------------------
# 13 — ROS service / message composition
# --------------------------------------------------------------------------------------

@figure("13_uml_ros_messages", "ROS service and message composition", "01-software-background.md")
def uml_ros():
    d = Doc("13_uml_ros_messages", "As-built ROS service and message composition",
            "Composition of srv/Plan.srv: PlanRequest (state, base schedule, jobs) and PlanResponse "
            "(Schedule of ActionNodes with command payloads, ScheduledJobData).")
    REQ, STATE, RESP, CMD, UTIL = T.sky, T.violet, T.green, T.amber, T.teal
    sz = 11.5
    HL = {"GaragePose": UTIL}
    msgs = {
        "PlanRequest": (REQ, ["+ id: Guid", "+ base_state: DiscreteGarageState", "+ base_schedule: Schedule",
                              "+ planned_jobs: SchedulerJob[]", "+ active_jobs: SchedulerJob[]",
                              "+ pending_jobs: SchedulerJob[]"]),
        "SchedulerJob": (REQ, ["+ type, type_name", "+ state, state_name", "+ guid: Guid", "+ note: string",
                               "+ agv_id, bay_id, tray_id", "+ payload_id: Guid", "+ destination: GaragePose",
                               "+ allow_reciprocal: bool", "+ seconds_to_bay_arrival: float32",
                               "+ retain_job: bool", "+ needs_bay_in_retrieve: bool",
                               "+ time_planned: builtin_interfaces/Time"]),
        "DiscreteGarageState": (STATE, ["+ header: std_msgs/Header", "+ is_faulted: bool",
                                        "+ agvs: DiscreteAgvState[]", "+ bays: DiscreteBayState[]",
                                        "+ vexen: DiscreteVecsState[]", "+ trays: DiscreteTrayState[]",
                                        "+ payloads: DiscretePayloadState[]", "+ vrcs: DiscreteVrcState[]",
                                        "+ disabled_nodes: uint32[]", "+ hash: uint64"]),
        "DiscreteAgvState": (STATE, ["+ id: uint16", "+ state: uint8", "+ pose: GaragePose", "+ lift: bool",
                                     "+ tray_id: uint16", "+ disabled: bool"]),
        "DiscreteTrayState": (STATE, ["+ id: uint16", "+ pose: GaragePose", "+ agv_id: uint16",
                                      "+ payload_id: Guid", "+ disabled: bool"]),
        "GaragePose": (UTIL, ["+ node_id: uint32", "+ heading: int16"]),
        "PlanResponse": (RESP, ["+ success: bool", "+ message: string", "+ id: Guid", "+ schedule: Schedule",
                                "+ scheduled_jobs: ScheduledJobData[]"]),
        "ScheduledJobData": (RESP, ["+ job: SchedulerJob", "+ node_indices: uint32[]", "+ bay_id: uint16",
                                    "+ bay_arrival_node_guid: Guid"]),
        "Schedule": (RESP, ["+ header: std_msgs/Header", "+ nodes: ActionNode[]"]),
        "ActionNode": (RESP, ["+ guid: Guid", "+ job_id: Guid", "+ type: uint8", "+ parents: uint32[]",
                              "+ duration: float32", "+ status: uint8", "+ outside_split: bool",
                              "+ agv_id: uint32", "+ agv_command: AgvCommand", "+ bay_id: uint32",
                              "+ bay_command: BayCommand", "+ vecs_id: uint32", "+ vecs_command: VecsCommand",
                              "+ vrc_id: uint32", "+ vrc_command: VrcCommand"]),
        "AgvCommand": (CMD, ["+ id: string", "+ src: AgvGoal", "+ dst: AgvGoal"]),
        "AgvGoal": (CMD, ["+ pose: GaragePose", "+ lift: bool"]),
        "BayCommand": (CMD, ["+ command_type: uint8", "+ command_id: string", "+ floor: uint8"]),
        "VecsCommand": (CMD, ["+ header", "+ command_id: string", "+ command_type: uint8"]),
        "VrcCommand": (CMD, ["+ header", "+ command_id: string", "+ command_type: uint8",
                             "+ requested_floor: uint16"]),
    }

    def size_of(n):
        return class_size(n, attrs=msgs[n][1], size=sz, name_size=13, compact=True)

    colL = max(size_of(n)[0] for n in ("PlanRequest", "DiscreteGarageState", "DiscreteAgvState",
                                       "DiscreteTrayState", "GaragePose"))
    colM = max(size_of(n)[0] for n in ("SchedulerJob", "Schedule", "ActionNode"))
    colR = max(size_of(n)[0] for n in ("PlanResponse", "ScheduledJobData", "AgvCommand", "AgvGoal", "BayCommand",
                                       "VecsCommand", "VrcCommand"))
    g1, g2 = 100, 132
    xL, xM = 0, colL + g1
    xR = xM + colM + g2
    B = {}

    def put(n, x, y, w):
        col, attrs = msgs[n]
        B[n] = uml_class(d, x, y, n, accent=col, attrs=attrs, size=sz, name_size=13, compact=True, w=w,
                         highlight=HL)
        return B[n]

    # service box
    sv = uml_class(d, xM + colM / 2, 0, "Plan", accent=T.fg2, stereo="service · srv/Plan.srv", size=sz,
                   name_size=13, compact=True, center_x=True,
                   attrs=["request: PlanRequest", "response: PlanResponse"])
    y1 = sv.y1 + 56
    put("PlanRequest", xL, y1, colL)
    put("SchedulerJob", xM, y1, colM)
    put("PlanResponse", xR, y1, colR)
    put("ScheduledJobData", xR, B["PlanResponse"].y1 + 62, colR)
    put("DiscreteGarageState", xL, B["PlanRequest"].y1 + 62, colL)
    put("Schedule", xM, B["SchedulerJob"].y1 + 78, colM)
    put("ActionNode", xM, B["Schedule"].y1 + 56, colM)
    ya = B["ActionNode"].y0
    yy = max(B["ScheduledJobData"].y1 + 70, ya)
    for n in ("AgvCommand", "AgvGoal", "BayCommand", "VecsCommand", "VrcCommand"):
        put(n, xR + 26 if n == "AgvGoal" else xR, yy, colR - 26 if n == "AgvGoal" else colR)
        yy = B[n].y1 + (24 if n == "AgvCommand" else 30)
    put("DiscreteAgvState", xL + 30, B["DiscreteGarageState"].y1 + 56, colL - 30)
    put("DiscreteTrayState", xL + 30, B["DiscreteAgvState"].y1 + 30, colL - 30)
    put("GaragePose", xL + 30, B["DiscreteTrayState"].y1 + 56, colL - 30)

    def row_y(n, field):
        """y of a member row inside class n."""
        b = B[n]
        attrs = msgs[n][1]
        i = [a.split(":")[0].strip("+ ").strip() for a in attrs].index(field)
        head_h = 13 + 20
        return b.y0 + head_h + 8 + (i + 0.5) * sz * 1.55

    Pq, Pr, SJ = B["PlanRequest"], B["PlanResponse"], B["SchedulerJob"]
    # service -> request/response
    connect(d, [(sv.x0, sv.cy), (Pq.cx, sv.cy), (Pq.cx, Pq.y0)], kind="comp", color=REQ, label="request",
            label_at=((sv.x0 + Pq.cx) / 2 + 20, sv.cy))
    connect(d, [(sv.x1, sv.cy), (Pr.cx, sv.cy), (Pr.cx, Pr.y0)], kind="comp", color=RESP, label="response",
            label_at=((sv.x1 + Pr.cx) / 2 - 20, sv.cy))
    # request side
    # three job arrays -> one SchedulerJob type (merged composition lines)
    jx = Pq.x1 + 22
    ys_ = [row_y("PlanRequest", f) for f in ("planned_jobs", "active_jobs", "pending_jobs")]
    for yv in ys_:
        connect(d, [(Pq.x1, yv), (jx, yv)], kind="comp", color=REQ, size=7)
    d.line(jx, ys_[0], jx, ys_[-1], stroke=REQ, sw=1.4, layer="edges")
    yj = ys_[1]
    d.line(jx, yj, SJ.x0, yj, stroke=REQ, sw=1.4, layer="edges")
    d.text(SJ.x0 - 6, yj - 9, "0..*", size=S.tiny, family="mono", fill=T.muted, anchor="end")
    connect(d, [(Pq.x0 + 40, Pq.y1), (Pq.x0 + 40, B["DiscreteGarageState"].y0)], kind="comp", color=REQ,
            label="base_state", label_at=(Pq.x0 + 40 + 44, (Pq.y1 + B["DiscreteGarageState"].y0) / 2))
    gx1 = Pq.x1 + g1 / 2
    ys = B["Schedule"].y0 + 30
    yb = row_y("PlanRequest", "base_schedule")
    connect(d, [(Pq.x1, yb), (gx1, yb), (gx1, ys), (B["Schedule"].x0, ys)], kind="comp", color=REQ)
    # state side
    G = B["DiscreteGarageState"]
    bus_x = xL + 12
    d.arrowhead((bus_x, G.y1), (bus_x, G.y1 + 30), kind="diamond", color=STATE, size=10)
    yA = B["DiscreteAgvState"].y0 + 18
    yT = B["DiscreteTrayState"].y0 + 18
    d.line(bus_x, G.y1 + 15, bus_x, yT, stroke=STATE, sw=1.4, layer="edges")
    for yv, nm in ((yA, "DiscreteAgvState"), (yT, "DiscreteTrayState")):
        d.line(bus_x, yv, B[nm].x0, yv, stroke=STATE, sw=1.4, layer="edges")
    d.text(bus_x + 8, G.y1 + 26, "agvs[], trays[]", size=10.5, family="mono", fill=STATE)
    gp = B["GaragePose"]
    pb = gp.x1 + 22
    for nm in ("DiscreteAgvState", "DiscreteTrayState"):
        yv = row_y(nm, "pose")
        connect(d, [(B[nm].x1, yv), (pb, yv), (pb, gp.cy), (gp.x1, gp.cy)], kind="comp", color=UTIL, radius=6)
    # response side
    SD = B["ScheduledJobData"]
    connect(d, [(Pr.cx, Pr.y1), (Pr.cx, SD.y0)], kind="comp", color=RESP, mult_end="0..*",
            label="scheduled_jobs", label_at=(Pr.cx, (Pr.y1 + SD.y0) / 2))
    yjob = row_y("ScheduledJobData", "job")
    if not (SJ.y0 + 30 < yjob < SJ.y1 - 10):
        yjob = SJ.y1 - 24
    connect(d, [(SD.x0, yjob), (SJ.x1, yjob)], kind="comp", color=RESP)
    gx2 = SJ.x1 + g2 / 2
    ysch = B["Schedule"].y0 + 30
    ysc = row_y("PlanResponse", "schedule")
    connect(d, [(Pr.x0, ysc), (gx2 + 14, ysc), (gx2 + 14, ysch), (B["Schedule"].x1, ysch)], kind="comp",
            color=RESP)
    S_, A_ = B["Schedule"], B["ActionNode"]
    connect(d, [(S_.cx, S_.y1), (S_.cx, A_.y0)], kind="comp", color=RESP, mult_end="0..*", label="nodes",
            label_at=(S_.cx + 40, (S_.y1 + A_.y0) / 2))
    # ActionNode -> commands: one connector per command field, each in its own lane
    lanes = {"agv_command": 92, "bay_command": 68, "vecs_command": 44, "vrc_command": 20}
    for n, field in (("AgvCommand", "agv_command"), ("BayCommand", "bay_command"), ("VecsCommand", "vecs_command"),
                     ("VrcCommand", "vrc_command")):
        yr = row_y("ActionNode", field)
        lx = A_.x1 + lanes[field]
        yt = B[n].y0 + 17
        connect(d, [(A_.x1, yr), (lx, yr), (lx, yt), (B[n].x0, yt)], kind="comp", color=CMD, radius=6)
    ac, ag = B["AgvCommand"], B["AgvGoal"]
    connect(d, [(ac.x0 + 13, ac.y1), (ac.x0 + 13, ag.cy), (ag.x0, ag.cy)], kind="comp", color=CMD, radius=4)
    d.text(ac.x0 + 22, ac.y1 + 12, "src, dst", size=10.5, family="mono", fill=CMD)
    # other uses of GaragePose
    note(d, gp.x0 - 30, gp.y1 + 26, colL,
         "GaragePose is also the type of SchedulerJob.destination and AgvGoal.pose (teal type names). "
         "Other DiscreteGarageState arrays (bays, vexen, payloads, vrcs) are not expanded here.",
         title="Not drawn")
    frame(d, title="As-built ROS service and message composition",
          subtitle="Generated from the .msg / .srv definitions. A filled diamond means \"contains as a field or "
                   "array element\" — composition of wire structs, not C++ inheritance. Connectors leave the owner at "
                   "the field that holds the value. ActionNode.parents are integer indices into Schedule.nodes.",
          badge_key="as-built",
          legend=[("comp", T.fg2, "contains field / array"), ("box", REQ, "request / intent"),
                  ("box", STATE, "garage-state snapshot"), ("box", RESP, "response / schedule"),
                  ("box", CMD, "command payload"), ("box", UTIL, "utility type")])
    return d
