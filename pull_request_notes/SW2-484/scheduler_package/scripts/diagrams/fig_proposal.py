"""Doc 02 proposal figures for tray_assignment: data flow (today vs proposed), the call tree before
(UML of the Scheduler members) and after (UML of the proposed module, Pass nested in DefaultSolver)."""
from __future__ import annotations

import math

from components import card, chip, class_size, connect, frame, label_pill, note, uml_class
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S

DOC2 = "02-issue-and-proposal.html"
CTX, SOLVE, PASS, PURE, WRITE, ARG = T.sky, T.amber, T.violet, T.green, T.red, T.amber
M = 12


def _lane(d: Doc, x, y, w, h, title, color):
    d.rect(x, y, w, h, rx=12, fill=T.tint(color, 0.05, T.bg), stroke=T.tint(color, 0.55, T.bg), sw=1.3,
           layer="under")
    chip(d, x + 16, y + 20, title, color, size=12)


# --------------------------------------------------------------------------------------
# 58 — data flow: how ScheduleContext is read and written, today vs proposed
# --------------------------------------------------------------------------------------

@figure("58_tray_dataflow", "Tray assignment data flow, today vs proposed", DOC2)
def tray_dataflow():
    d = Doc("58_tray_dataflow", "How tray assignment reads and writes ScheduleContext",
            "Today DoTrayAssignments writes ctx throughout its loop. Proposed: Solve reads an Input, returns a "
            "Result, and ApplyTrayAssignment writes ctx once.")
    W = 1440
    ctx_lines = ["initial_state", "events  (the DAG)", "first_tray_event"]

    # ---- lane 1: today ----
    y0 = 0
    _lane(d, 0, y0, W, 210, "today", T.muted)
    c1 = card(d, 24, y0 + 48, 230, 140, title="ScheduleContext", accent=CTX, lines=ctx_lines,
              sub="plan_ctx, owned by Plan()")
    s1 = card(d, 580, y0 + 48, 340, 140, title="DoTrayAssignments(ctx)", accent=SOLVE, sub="Scheduler member",
              lines=["~560-line loop + 9 helpers", "returns BoolStringPair"], mono_lines=False)
    connect(d, [(c1.x1, c1.y0 + 50), (s1.x0, c1.y0 + 50)], kind="flow", color=CTX,
            label="ScheduleContextSPtr (shared, mutable)", label_at=((c1.x1 + s1.x0) / 2, c1.y0 + 34))
    connect(d, [(s1.x0, c1.y0 + 104), (c1.x1, c1.y0 + 104)], kind="flow", color=WRITE,
            label="writes during the loop", label_at=((c1.x1 + s1.x0) / 2, c1.y0 + 88))
    note(d, s1.x1 + 30, y0 + 48, W - s1.x1 - 54,
         "AddEvent, AddDependency, SetTrayId / SetDest on events, first_tray_event[...] happen inside the loop "
         "and inside AssignDestForUntargetedMove. A failure halfway leaves ctx half-edited.",
         title="Writes are spread out", accent=WRITE)

    # ---- lane 2: proposed ----
    y1 = 250
    H2 = 330
    _lane(d, 0, y1, W, H2, "proposed", SOLVE)
    c2 = card(d, 24, y1 + 52, 230, 140, title="ScheduleContext", accent=CTX, lines=ctx_lines,
              sub="plan_ctx, owned by Plan()")
    # Solve box with nested Pass
    sx, sy, sw_, sh = 440, y1 + 52, 330, 232
    d.rect(sx, sy, sw_, sh, rx=10, fill=T.card, stroke=SOLVE, sw=1.5)
    d.text(sx + 16, sy + 20, "DefaultSolver::Solve(input) const", size=13, family="mono", weight=600, fill=SOLVE)
    d.text(sx + 16, sy + 40, "reads only; never writes ctx", size=S.small, fill=T.muted)
    px, py = sx + 16, sy + 56
    d.rect(px, py, sw_ - 32, 98, rx=8, fill=T.tint(PASS, 0.10, T.bg), stroke=PASS, sw=1.3)
    d.text(px + 12, py + 16, "Pass  (private, one per call)", size=12, family="mono", weight=600, fill=PASS)
    for i, ln in enumerate(["working_state_", "freeing_moves_, last_event_by_tray_", "result_  (built up here)"]):
        d.text(px + 12, py + 38 + i * 19, ln, size=11.5, family="mono", fill=T.fg2)
    d.text(sx + 16, py + 116, "calls pure functions:", size=S.small, fill=T.muted)
    cx = sx + 16
    for i, nm in enumerate(["ChooseEmptyTray", "ResolveBlockingTrays", "FindCriticalPath", "..."]):
        if i == 2:
            cx = sx + 16
        b = chip(d, cx, py + 140 + (i // 2) * 26, nm, PURE, size=11)
        cx = b.x1 + 8
    s2 = BBox(sx, sy, sx + sw_, sy + sh)
    r2 = card(d, 930, y1 + 52, 190, 140, title="Result", accent=SOLVE,
              lines=["fills", "edits  (ordered)", "first_event_by_tray"], sub="returned by value")
    a2 = card(d, 1170, y1 + 52, 246, 140, title="ApplyTrayAssignment(ctx, result)", accent=WRITE,
              lines=["replay edits", "set fills", "cycle check"], mono_lines=False)
    # arrows
    connect(d, [(c2.x1, c2.y0 + 50), (s2.x0, c2.y0 + 50)], kind="flow", color=CTX, label="Input{const&, const&}",
            label_at=((c2.x1 + s2.x0) / 2, c2.y0 + 34))
    connect(d, [(s2.x1, r2.y0 + 50), (r2.x0, r2.y0 + 50)], kind="flow", color=SOLVE, label="Expected<Result>",
            label_at=((s2.x1 + r2.x0) / 2, r2.y0 + 34))
    connect(d, [(r2.x1, r2.y0 + 50), (a2.x0, r2.y0 + 50)], kind="flow", color=SOLVE)
    yb = y1 + H2 - 26
    connect(d, [(a2.cx, a2.y1), (a2.cx, yb), (c2.cx, yb), (c2.cx, c2.y1)], kind="flow", color=WRITE,
            label="the only write to ctx", label_at=((a2.cx + s2.x1) / 2 + 40, yb))
    connect(d, [(r2.cx, r2.y1), (r2.cx, r2.y1 + 44)], kind="flow", color=T.muted, dash="5 4")
    d.text(r2.cx + 8, r2.y1 + 30, "on error: Plan fails", size=S.small, fill=T.muted)
    d.text(r2.cx + 8, r2.y1 + 46, "every job, ctx untouched", size=S.small, fill=T.muted)
    for n, (x, y) in enumerate([((c2.x1 + s2.x0) / 2, c2.y0 + 64), ((s2.x1 + r2.x0) / 2, r2.y0 + 64),
                                 ((r2.x1 + a2.x0) / 2, r2.y0 + 64)], 1):
        d.circle(x, y + 4, 10, fill=T.fg2, layer="top")
        d.text(x, y + 4.5, str(n), size=11, family="mono", weight=700, fill=T.bg, anchor="middle", layer="top")
    frame(d, title="How tray assignment reads and writes ScheduleContext",
          subtitle="Same work, different place for the writes. (1) Plan builds a read-only Input from plan_ctx. "
                   "(2) Solve returns everything it decided as a Result. (3) ApplyTrayAssignment writes it into "
                   "plan_ctx in one step.",
          badge_key="proposed",
          legend=[("box", CTX, "ScheduleContext (owned by Plan)"), ("box", SOLVE, "solver / its return value"),
                  ("box", PASS, "private mutable state"), ("box", PURE, "pure function"),
                  ("arrow", WRITE, "writes ctx")])
    return d


# --------------------------------------------------------------------------------------
# 59 — before: the tray call tree as Scheduler members, with what each one writes
# --------------------------------------------------------------------------------------

BEFORE = [
    # (signature, [(write, color)], note, indent)
    ("DoTrayAssignments(ScheduleContextSPtr ctx) const : BoolStringPair",
     [("ctx->events", WRITE), ("ctx->first_tray_event", WRITE), ("TrayMove fields", WRITE)],
     "the per-event loop; these blocks are written inline:", 0),
    ("destination check", [], "", 1),
    ("critical-path search", [], "", 1),
    ("fallback 1: advance the root tray", [("working_state", ARG), ("critical_path", ARG)], "", 1),
    ("blocker re-scan", [("blocking_trays", ARG)], "", 1),
    ("emit blocker moves  (2nd copy in AssignDest...)", [("ctx->events", WRITE), ("first_tray_event", WRITE)], "", 1),
    ("root-move tail", [("ctx->events", WRITE), ("working_state", ARG)], "", 1),
    ("ApplyTransitionToFreeingMoves(event, DiscreteGarageState& ws, GarageOccupancyChecker& freeing)",
     [("working_state", ARG), ("freeing_moves", ARG)], "", 0),
    ("AssignTrayIdForEmptyMove(TrayMove& move, const DiscreteGarageState& ws) : BoolStringPair",
     [("TrayMove tray id, dest", WRITE)], "also called by PlanReadyForInsertJob", 0),
    ("AssignDestForUntargetedMove(TrayMove* move, ScheduleContextSPtr ctx, const ScheduleEventSPtr& event,",
     [], "", 0),
    ("    DiscreteGarageState& ws, GarageOccupancyChecker& freeing, map& last_tray_event) : BoolStringPair",
     [("ctx->events", WRITE), ("first_tray_event", WRITE), ("TrayMove dest", WRITE), ("working_state", ARG),
      ("freeing_moves", ARG), ("last_tray_event", ARG)], "", 0),
    ("ResolveBlockingTrays(tray_id, job_index, const DiscreteGarageState& base_state, immobile, illegal, ...)",
     [("nothing (copies base_state)", PURE)], "also called by PlanChargePayloadJob", 0),
    ("FindOpenSpaceForRootTray(...) const : optional<OpenSpaceSearchResult>", [("nothing", PURE)], "", 0),
    ("TryFindBlockingTrayResolution(...) const : optional<BlockingTrayResolution>", [("nothing", PURE)], "", 0),
    ("UsePreferredHeading(GaragePoseMsg& dest, payload, tray) const : void", [("dest", ARG)],
     "also PlanAgvMoveJob, PlanReparkTrayJob", 0),
    ("UseRetrievalHeading(GaragePoseMsg& dest, payload) const : void", [("dest", ARG)], "", 0),
    ("UseEvChargeHeading(GaragePoseMsg& dest) const : bool", [("dest", ARG)], "also PlanChargePayloadJob", 0),
]


@figure("59_tray_tree_before", "Tray call tree today (UML)", DOC2)
def tray_tree_before():
    d = Doc("59_tray_tree_before", "Tray call tree today",
            "All functions are Scheduler members; chips show what each one writes: ScheduleContext (red), "
            "an argument passed by reference (amber) or nothing (green).")
    W = 1180
    # ScheduleContext + TrayMove on top
    ctx = uml_class(d, 0, 0, "ScheduleContext", accent=CTX, stereo="struct · existing", size=M,
                    attrs=["+ initial_state: DiscreteGarageState", "+ events: ScheduleEventDag",
                           "+ first_tray_event: unordered_map<uint16_t, ScheduleEventSPtr>"])
    tm = uml_class(d, ctx.x1 + 60, 0, "TrayMove", accent=CTX, stereo="planner_core · event in ctx->events", size=M,
                   methods=["+ SetTrayId(uint16_t)", "+ SetDest(GaragePoseMsg)"])
    # Scheduler box
    y0 = max(ctx.y1, tm.y1) + 90
    head = 46
    rows = []
    y = y0 + head + 14
    for sig, writes, nt, ind in BEFORE:
        rows.append((y, sig, writes, nt, ind))
        y += 24 if not writes and not nt else 48
    h = y - y0 + 6
    d.rect(0, y0, W, h, rx=8, fill=T.card, stroke=CTX, sw=1.5)
    d.path(f"M0 {y0 + head} L0 {y0 + 8} Q0 {y0} 8 {y0} L{W - 8} {y0} Q{W} {y0} {W} {y0 + 8} L{W} {y0 + head} Z",
           fill=T.tint(CTX, 0.16))
    d.text(W / 2, y0 + 14, "«existing · tray call tree only, abridged»", size=S.tiny, fill=T.muted, anchor="middle")
    d.text(W / 2, y0 + 32, "Scheduler", size=S.h, family="mono", weight=700, fill=CTX, anchor="middle")
    for yy, sig, writes, nt, ind in rows:
        x = 16 + ind * 28
        if ind:
            d.text(x - 14, yy, "•", size=12, fill=T.faint)
        d.text(x, yy, sig, size=12, family="mono", weight=600 if not ind else 400,
               fill=T.fg if not ind else T.fg2)
        if writes or nt:
            cx = x + 16
            if writes:
                d.text(cx, yy + 24, "writes", size=S.small, fill=T.muted)
                cx += 46
            for wtxt, col in writes:
                b = chip(d, cx, yy + 24, wtxt, col, size=10.5)
                cx = b.x1 + 6
            if nt:
                d.text(cx + 10, yy + 24, nt, size=S.small, fill=T.sky, style="italic")
    sched = BBox(0, y0, W, y0 + h)
    connect(d, [(ctx.cx, sched.y0), (ctx.cx, ctx.y1)], kind="dep", color=WRITE, label="«writes»  (red chips)",
            label_at=(ctx.cx, (ctx.y1 + sched.y0) / 2))
    connect(d, [(tm.cx, sched.y0), (tm.cx, tm.y1)], kind="dep", color=WRITE, label="«writes»  (red chips)",
            label_at=(tm.cx, (tm.y1 + sched.y0) / 2))
    note(d, tm.x1 + 40, 0, W - tm.x1 - 40,
         "Nothing in the signatures separates the 3 green helpers from the rest: all are members, all can reach "
         "every Scheduler field, and 4 of them are also called by job planning.", title="What the shape hides")
    frame(d, title="Tray call tree today",
          subtitle="Every function is a Scheduler member. Chips list what each one writes. Red: something in "
                   "ScheduleContext (the DAG, the hand-off map, or an event's fields). Amber: an argument passed by "
                   "reference. Green: nothing.",
          badge_key="as-built",
          legend=[("box", WRITE, "writes ScheduleContext"), ("box", ARG, "writes an argument / local"),
                  ("box", PURE, "writes nothing"), ("dep", WRITE, "«writes»")],
          footnote="Signatures abridged. Line numbers and full parameter lists: doc 01, Tray assignment and AGV assignment.")
    return d


# --------------------------------------------------------------------------------------
# 60 — after: proposed tray_assignment module (Pass nested inside DefaultSolver)
# --------------------------------------------------------------------------------------

def _nested_class(d: Doc, x, y, outer: dict, inner: dict, *, pad=16):
    """UML class box with a nested classifier drawn inside its lower compartment."""
    iw, ih = class_size(inner["name"], stereo=inner.get("stereo"), attrs=inner.get("attrs", ()),
                        methods=inner.get("methods", ()), size=M)
    lh = M * 1.55
    blank = math.ceil((ih + pad + 22) / lh)
    ow, _ = class_size(outer["name"], stereo=outer.get("stereo"), attrs=outer.get("attrs", ()),
                       methods=list(outer.get("methods", ())), size=M)
    w = max(ow, iw + 2 * pad)
    o = uml_class(d, x, y, outer["name"], accent=outer["accent"], stereo=outer.get("stereo"),
                  attrs=outer.get("attrs", ()), methods=list(outer.get("methods", ())) + [""] * blank, w=w, size=M)
    iy = o.y1 - 10 - ih - pad + 4
    d.text(o.x0 + pad, iy - 12, "nested:", size=S.tiny, fill=T.muted)
    i = uml_class(d, o.x0 + pad, iy, inner["name"], accent=inner["accent"], stereo=inner.get("stereo"),
                  attrs=inner.get("attrs", ()), methods=inner.get("methods", ()), w=w - 2 * pad, size=M)
    return o, i


def _package(d: Doc, x, y, w, h, name, color, sub=""):
    d.rect(x, y, w, h, rx=10, fill=T.tint(color, 0.04, T.bg), stroke=T.tint(color, 0.6, T.bg), sw=1.3,
           layer="under")
    tw = text_width(name, 12.5, "mono", 700) + 28
    d.rect(x, y, tw, 26, rx=10, fill=T.tint(color, 0.22, T.bg), layer="under")
    d.text(x + 14, y + 13, name, size=12.5, family="mono", weight=700, fill=color)
    if sub:
        d.text(x + tw + 12, y + 13, sub, size=S.small, fill=T.muted)


@figure("60_tray_tree_after", "Tray call tree after (UML)", DOC2)
def tray_tree_after():
    d = Doc("60_tray_tree_after", "Proposed tray_assignment module",
            "UML of the proposed module: Solver interface, DefaultSolver with Pass nested inside, Input and Result, "
            "pure free functions grouped by header, and ApplyTrayAssignment as the only writer of PlanContext.")
    GAP = 40
    # ---- outside the module: Scheduler and ScheduleContext ----
    sched = uml_class(d, 0, 0, "Scheduler", accent=CTX, stereo="existing · abridged", size=M,
                      attrs=["- services_: scheduler_core::GarageServices", "- tray_solver_: unique_ptr<tray_assignment::Solver>"],
                      methods=["+ Plan(request): PlanResponse", "  // Solve(), then ApplyTrayAssignment()",
                               "- Expand<Type>Job(...)  (today Plan<Type>Job)"])
    ctx = uml_class(d, sched.x1 + 60, 0, "PlanContext", accent=CTX, stereo="struct · today ScheduleContext", size=M,
                    attrs=["+ initial_state: DiscreteGarageState", "+ event_dag: EventDag  // today events",
                           "+ first_event_by_tray: unordered_map<uint16_t, ScheduleEventSPtr>"])
    top = max(sched.y1, ctx.y1) + 80

    # ---- package tray_assignment ----
    px0 = 0
    y = top + 44
    iface = uml_class(d, 24, y, "Solver", accent=SOLVE, stereo="interface · solver.hpp", abstract=True, size=M,
                      methods=["+ Solve(input: const Input&) const", "    : stdx::Expected<Result> = 0"])
    inp = uml_class(d, iface.x1 + GAP, y, "Input", accent=SOLVE, stereo="struct · solver.hpp", size=M,
                    attrs=["+ initial_state: const DiscreteGarageState&", "+ event_dag: const EventDag&"])
    res = uml_class(d, inp.x1 + GAP, y, "Result", accent=SOLVE, stereo="struct · solver.hpp", size=M,
                    attrs=["+ fills: vector<TrayFill>", "+ edits: vector<DagEdit>  // ordered",
                           "+ first_event_by_tray: unordered_map<...>"])
    y2 = max(iface.y1, inp.y1, res.y1) + 60
    dflt, pas = _nested_class(
        d, 24, y2,
        dict(name="DefaultSolver", accent=SOLVE, stereo="class · default_solver.hpp",
             attrs=["- services_: const GarageServices&"],
             methods=["+ Solve(input) const : stdx::Expected<Result>", "  // was DoTrayAssignments(ctx)"]),
        dict(name="Pass", accent=PASS, stereo="private nested class · src/task_planning/tray_assignment/pass.hpp",
             attrs=["- working_state_: DiscreteGarageState  // copy", "- freeing_moves_: GarageOccupancyChecker<...>",
                    "- last_event_by_tray_: unordered_map<...>", "- result_: Result  // returned by Solve"],
             methods=["+ RecordStateChange(event): stdx::Result", "  // was ApplyTransitionToFreeingMoves",
                      "+ Fill(event, tray_id, destination)", "  // was SetTrayId / SetDest on the input",
                      "+ EmitMoveChain(moves, ...)", "  // was the 2 copies of the emission block",
                      "+ CommitRootMove(event, resolved): stdx::Result", "  // was the root-move tail",
                      "+ TakeResult() &&: Result"]))
    app = uml_class(d, dflt.x1 + GAP, y2, "apply.hpp", accent=WRITE, stereo="free function", size=M,
                    methods=["+ ApplyTrayAssignment(PlanContext& ctx,", "    const Result& r): stdx::Result",
                             "  // new: the only function that", "  // takes a mutable context"])
    fx = dflt.x1 + GAP
    fy = app.y1 + 30
    et = uml_class(d, fx, fy, "empty_tray.hpp", accent=PURE, stereo="public · pure", size=M,
                   methods=["+ ChooseEmptyTray(services, state, destination)", "    : stdx::Expected<TrayChoice>",
                            "  // was AssignTrayIdForEmptyMove"])
    bt = uml_class(d, fx, et.y1 + 20, "blocking_trays.hpp", accent=PURE, stereo="public · pure", size=M,
                   methods=["+ ResolveBlockingTrays(services, request)", "    : stdx::Expected<BlockingResolution>",
                            "+ ChooseParkingSpot(services, state, tray, job)", "    : stdx::Expected<ParkingPlan>",
                            "  // was 1st half of AssignDestForUntargetedMove",
                            "- detail::FindOpenSpace(...)  // was FindOpenSpaceForRootTray",
                            "- detail::TryResolveBlocker(...)", "  // was TryFindBlockingTrayResolution"])
    cp = uml_class(d, fx, bt.y1 + 20, "critical_path.hpp", accent=PURE, stereo="private (src/) · pure", size=M,
                   methods=["+ CheckDestinationUsable(...): stdx::Result", "+ FindCriticalPath(...)",
                            "    : stdx::Expected<CriticalPath>", "+ TryAdvanceRoot(...): optional<PlannedTrayMove>",
                            "+ BlockersOnPath(...): vector<uint16_t>", "  // all four were inline in the main loop"])
    right = max(res.x1, app.x1, et.x1, bt.x1, cp.x1) + 24
    bottom = max(dflt.y1, cp.y1) + 24
    _package(d, px0, top, right - px0, bottom - top, "task_planning/tray_assignment", SOLVE)
    d.text(right - 24, top + 13, "namespace volley::task_planning::tray_assignment", size=S.small, fill=T.muted,
           anchor="end")

    # ---- package common ----
    cy0 = bottom + 50
    gs = uml_class(d, 24, cy0 + 44, "GarageServices", accent=T.teal, stereo="struct · garage_services.hpp", size=M,
                   attrs=["+ motion_graph: const MotionGraph&", "+ collision_table: const CollisionTable&",
                          "+ cost_model: const MotionCostModel&", "+ layout: const Layout&", "+ logger: rclcpp::Logger"])
    hd = uml_class(d, gs.x1 + GAP, cy0 + 44, "headings.hpp", accent=PURE, stereo="public · pure · shared", size=M,
                   methods=["+ PreferredHeading(services, destination, payload): Pose", "  // was UsePreferredHeading",
                            "+ RetrievalHeading(services, destination, payload): Pose", "  // was UseRetrievalHeading",
                            "+ EvChargeHeading(layout, node): optional<int16_t>", "  // was UseEvChargeHeading"])
    cbottom = max(gs.y1, hd.y1) + 24
    _package(d, 0, cy0, right, cbottom - cy0, "scheduler/core", T.teal, "namespace volley::scheduler_core")

    # ---- relations ----
    ax = min(iface.x1 - 30, sched.x1 - 120)
    connect(d, [(ax, sched.y1), (ax, iface.y0)], kind="assoc", color=CTX, mult_end="1",
            label="tray_solver_", label_at=(ax, (sched.y1 + top) / 2))
    gx = (inp.x1 + res.x0) / 2
    connect(d, [(sched.x1 - 40, sched.y1), (sched.x1 - 40, top - 30), (gx, top - 30), (gx, app.y0)],
            kind="dep", color=CTX, label="«call»  after Solve", label_at=((sched.x1 + gx) / 2, top - 30))
    connect(d, [(app.x1, app.cy), (right + 40, app.cy), (right + 40, ctx.y1 + 40), (ctx.x1 - 60, ctx.y1 + 40),
                (ctx.x1 - 60, ctx.y1)], kind="dep", color=WRITE, label="«writes»",
            label_at=(right + 40, (app.cy + ctx.y1 + 40) / 2))
    # realization DefaultSolver -> Solver
    d.arrowhead((iface.cx, iface.y1), (iface.cx, iface.y1 + 30), kind="triangle", color=SOLVE, size=11, sw=1.5)
    d.line(iface.cx, iface.y1 + 13, iface.cx, dflt.y0, stroke=SOLVE, sw=1.5, dash="6 4", layer="edges")
    label_pill(d, iface.cx, (iface.y1 + dflt.y0) / 2 + 4, "realizes", color=SOLVE)
    connect(d, [(iface.x1, iface.y0 + 54), (inp.x0, iface.y0 + 54)], kind="dep", color=SOLVE, label="«read»",
            label_at=((iface.x1 + inp.x0) / 2, iface.y0 + 40))
    connect(d, [(inp.x1, inp.y0 + 54), (res.x0, inp.y0 + 54)], kind="dep", color=SOLVE, label="«return»",
            label_at=((inp.x1 + res.x0) / 2, inp.y0 + 40))
    # DefaultSolver calls the pure functions (bus on the left of the header boxes)
    bx = fx - GAP / 2
    d.line(dflt.x1, dflt.y0 + 90, bx, dflt.y0 + 90, stroke=PURE, sw=1.4, dash="6 4", layer="edges")
    d.line(bx, dflt.y0 + 90, bx, cp.cy, stroke=PURE, sw=1.4, dash="6 4", layer="edges")
    for b in (et, bt, cp):
        connect(d, [(bx, b.cy), (b.x0, b.cy)], kind="dep", color=PURE)
    label_pill(d, bx, (dflt.y0 + 90 + et.cy) / 2, "«call»", color=PURE)
    connect(d, [(dflt.cx, dflt.y1), (dflt.cx, cy0 - 24), (hd.cx, cy0 - 24), (hd.cx, hd.y0)], kind="dep",
            color=PURE, label="«call»", label_at=((dflt.cx + hd.cx) / 2, cy0 - 24))
    # job planning also calls the public pure functions
    note(d, ctx.x1 + 40, 0, 320,
         "Scheduler's job methods call ChooseEmptyTray, ResolveBlockingTrays and the heading functions directly "
         "with services_. No back-pointer to Scheduler.", title="Shared with job planning")
    frame(d, title="Proposed tray_assignment module",
          subtitle="Pass is a private nested class of DefaultSolver: it is created inside Solve and holds the only "
                   "state that changes during a solve. ApplyTrayAssignment is the only function that writes "
                   "PlanContext. Everything green is a pure function.",
          badge_key="proposed",
          legend=[("box", CTX, "existing"), ("box", SOLVE, "solver types"), ("box", PASS, "private mutable state"),
                  ("box", PURE, "pure functions"), ("box", WRITE, "writes PlanContext"),
                  ("real", SOLVE, "realizes"), ("dep", T.fg2, "dependency")],
          footnote="// was ... names the Scheduler member or inline block (previous figure) that each item replaces. "
                   "'services' is a const GarageServices&. Names follow doc 02, Naming and the ROS boundary (MotionGraph and Pose are aliases in core/vocabulary.hpp).")
    return d


# --------------------------------------------------------------------------------------
# 83 — naming and the ROS boundary: what is renamed, what is translated
# --------------------------------------------------------------------------------------

def _box(d: Doc, x, y, w, title, sub, lines, color, *, mono=True):
    lh = 19
    h = 58 + lh * len(lines) + 10
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=color, sw=1.5)
    d.text(x + 16, y + 20, title, size=13.5, family="mono", weight=700, fill=T.fg)
    d.text(x + 16, y + 40, sub, size=11.5, fill=T.muted)
    for i, ln in enumerate(lines):
        if "//" in ln:
            j = ln.index("//")
            d.rich(x + 16, y + 64 + i * lh, [(ln[:j], "mono", 400, T.fg2), (ln[j:], "mono", 400, T.faint)], size=11.5)
        else:
            d.text(x + 16, y + 64 + i * lh, ln, size=11.5, family="mono" if mono else "sans", fill=T.fg2)
    return BBox(x, y, x + w, y + h)


@figure("83_naming_boundary", "Naming and the ROS boundary", DOC2)
def naming_boundary():
    d = Doc("83_naming_boundary", "Naming and the ROS boundary",
            "Three layers: ROS messages and common_ros keep their names; a boundary inside the scheduler translates "
            "them; scheduler and planner_core code uses the new names and internal types.")
    OUT, BND, INS = T.faint, T.amber, T.green
    W = 1500
    # ---- band 1: outside ----
    def lane_for(y, boxes, title, color):
        _lane(d, 0, y, W, max(bx.y1 for bx in boxes) - y + 24, title, color)
        return max(bx.y1 for bx in boxes) + 24
    y1 = 0
    b_if = _box(d, 24, y1 + 46, 700, "interfaces  (ROS messages)", "used by every node; renames wait for one versioned change",
                ["GaragePoseMsg, GarageEntityIdMsg, GuidMsg",
                 "SchedulerJobMsg, ScheduledJobDataMsg",
                 "PlanRequest / PlanResponse, ActionNodeMsg",
                 "DiscreteAgvStateMsg, BayCommandMsg, ...  // inside DGS and events"], T.sky)
    b_cr = _box(d, 760, y1 + 46, 716, "common_ros", "used by many packages; renames deferred",
                ["GarageGraph, PoseGraph, CollisionTable, Layout",
                 "CollisionEntityId(_t), VertexCollisionIdMap",
                 "TransitionType::LOCOMOTE / STRAFE / ...",
                 "DiscreteGarageState                     // stores messages"], T.teal)
    e1 = lane_for(y1, [b_if, b_cr], "outside the scheduler · unchanged in this refactor", OUT)
    # ---- band 2: boundary ----
    y2 = e1 + 70
    b_sr = _box(d, 24, y2 + 46, 340, "scheduler_ros.cpp", "existing ROS node: services, timers",
                ["Plan service -> Scheduler::Plan()", "the only rclcpp code besides", "  the logger"], BND)
    b_cv = _box(d, 388, y2 + 46, 440, "ros/convert.hpp", "messages <-> internal types; edge code only",
                ["ToAssetId(GarageEntityIdMsg)", "ToMsg(AssetId) -> GarageEntityIdMsg",
                 "ToMsg(ScheduledJob) -> ScheduledJobDataMsg", "rclcpp::Time -> Interval::Timepoint"], BND)
    b_vo = _box(d, 852, y2 + 46, 624, "core/vocabulary.hpp", "aliases and thin wrappers; zero run-time cost",
                ["using MotionGraph = GarageGraph;", "using Pose = GaragePoseMsg;",
                 "using FootprintId = CollisionEntityId_t;", "transition_type::RIDE_VRC = VRC_TRANSITION"], BND)
    e2 = lane_for(y2, [b_sr, b_cv, b_vo], "boundary · new files in scheduler", BND)
    # ---- band 3: inside ----
    y3 = e2 + 70
    b_sc = _box(d, 24, y3 + 46, 804, "scheduler", "renamed now (doc 04 rows for scheduler)",
                ["PlanContext   // was ScheduleContext", "motion_graph_, collision_table_",
                 "Expand<Type>Job, last_event_by_asset", "ScheduledJob, AssetId  // core/types.hpp"], INS)
    b_ta = _box(d, 852, y3 + 46, 384, "tray_ / agv_assignment", "new modules, written with the new names",
                ["GarageServices{motion_graph, ...}", "Input{initial_state, event_dag}",
                 "Result{fills, edits,", "       first_event_by_tray}", "no ros/ include"], INS)
    b_pc = _box(d, 1260, y3 + 46, 216, "planner_core", "renamed, [[deprecated]] aliases",
                ["EventDag", "BayStateChange, ...", "SetDestination", "others migrate later"], INS)
    lane_for(y3, [b_sc, b_ta, b_pc], "inside · new names and internal types", INS)
    # ---- arrows ----
    connect(d, [(b_sr.cx, b_if.y1), (b_sr.cx, b_sr.y0)], kind="flow", color=T.sky, size=8,
            label="requests", label_at=(b_sr.cx + 8, (b_if.y1 + b_sr.y0) / 2), label_anchor="start")
    connect(d, [(b_cv.cx, b_if.y1), (b_cv.cx, b_cv.y0)], kind="flow", color=T.sky, size=8,
            label="messages", label_at=(b_cv.cx + 8, (b_if.y1 + b_cv.y0) / 2), label_anchor="start")
    connect(d, [(b_vo.x0 + 300, b_cr.y1), (b_vo.x0 + 300, b_vo.y0)], kind="flow", color=T.teal, size=8,
            label="old names", label_at=(b_vo.x0 + 308, (b_cr.y1 + b_vo.y0) / 2), label_anchor="start")
    connect(d, [(b_sr.cx, b_sr.y1), (b_sr.cx, b_sc.y0)], kind="flow", color=BND, size=8,
            label="Plan()", label_at=(b_sr.cx + 8, (b_sr.y1 + b_sc.y0) / 2), label_anchor="start")
    connect(d, [(b_cv.cx, b_cv.y1), (b_cv.cx, b_sc.y0)], kind="flow", color=BND, size=8,
            label="internal types", label_at=(b_cv.cx + 8, (b_cv.y1 + b_sc.y0) / 2), label_anchor="start")
    connect(d, [(b_ta.cx, b_vo.y1), (b_ta.cx, b_ta.y0)], kind="flow", color=BND, size=8,
            label="new names", label_at=(b_ta.cx + 8, (b_vo.y1 + b_ta.y0) / 2), label_anchor="start")
    frame(d, title="Naming and the ROS boundary",
          subtitle="Renames stay inside scheduler and planner_core. common_ros names are translated by aliases in one "
                   "header; messages the scheduler builds or keys maps with become internal types at the edge. "
                   "DiscreteGarageState and the event payloads still carry messages: they pass through unchanged.",
          badge_key="proposed",
          legend=[("box", OUT, "unchanged packages"), ("box", BND, "boundary (new)"), ("box", INS, "new names"),
                  ("arrow", T.fg2, "data or names flow")],
          footnote="Proposed in doc 02, Naming and the ROS boundary; the full list of names is doc 04. File paths are under "
                   "scheduler/include/scheduler/ (headers) and scheduler/src/ (sources).")
    return d


# --------------------------------------------------------------------------------------
# 95 — module layout: Option 1 (stage folders in scheduler) vs Option 2 (one package per stage)
# --------------------------------------------------------------------------------------

@figure("95_module_layout", "Stage folders vs stage packages", DOC2)
def module_layout():
    d = Doc("95_module_layout", "Stage folders vs stage packages",
            "Option 1 keeps one scheduler package with a folder per pipeline stage. Option 2 makes each stage a "
            "package; motion planning already is one (motion_planner), and a scheduler_core package is needed first.")
    W, G = 1500, 50
    ORC, TP, MP, AG, CORE, LOW = T.amber, T.violet, T.sky, T.green, T.teal, T.faint

    def lane_for(y, boxes, title, color):
        _lane(d, 0, y, W, max(bx.y1 for bx in boxes) - y + 24, title, color)
        return max(bx.y1 for bx in boxes) + 24

    def down(a, b, x, label=None, kind="flow", color=T.fg2):
        connect(d, [(x, a.y1), (x, b.y0)], kind=kind, color=color, size=8,
                label=label, label_at=(x + 8, (a.y1 + b.y0) / 2) if label else None, label_anchor="start")

    # ---------------- Option 1 ----------------
    y = 0
    o1 = _box(d, 24, y + 46, 1452, "scheduler/  scheduler.hpp, plan_context.hpp, ros/",
              "orchestrator: Scheduler::Plan() runs the five stages in order and applies their results",
              ["owns GarageServices and the two solvers; PlanContext lives in plan_context.hpp",
               "ros/convert.hpp: messages <-> internal types, used only here and by scheduler_ros.cpp"], ORC)
    ry = o1.y1 + G
    t1 = _box(d, 24, ry, 600, "task_planning/", "stages 1-3: jobs -> finished event DAG",
              ["job_expansion/     // Expand<Type>Job, one file per type",
               "tray_assignment/   // Solver, DefaultSolver, ChooseEmptyTray",
               "agv_assignment/    // Solver, DefaultSolver, travel cost",
               "validation/        // ValidateEvents",
               "uses planner_core, motion_planner searches,",
               "     task_planner (BottleneckAssignment)"], TP)
    m1 = _box(d, 688, ry, 380, "motion_planning/", "stage 4: adapter around CHUGG",
              ["PlanMotions(event_dag, state, ...)", "  -> ContinuousState", "about 60 lines today",
               "uses motion_planner (CHUGG)"], MP)
    a1 = _box(d, 1092, ry, 384, "action_graph/", "stage 5: timed motions -> action DAG",
              ["BuildActionDag(...)", "CopyEventDependencies", "InsertVrcActions",
               "uses planner_core, common_ros, cost_functions"], AG)
    cy = max(t1.y1, m1.y1, a1.y1) + G
    c1 = _box(d, 24, cy, 1452, "core/", "shared by every stage; includes no stage and no scheduler.hpp",
              ["GarageServices, types.hpp (AssetId, ...), vocabulary.hpp (aliases for common_ros names), headings"],
              CORE)
    for b in (t1, m1, a1):
        down(o1, b, b.cx, "calls")
        down(b, c1, b.cx, kind="dep", color=CORE)
    d.text(24, c1.y1 + 26, "Rule, checked by a CI include grep: a stage folder never includes another stage folder, "
           "scheduler.hpp or ros/. Inside task_planning, job_expansion may call tray_assignment's public functions.",
           size=S.small, fill=T.red)
    e1 = lane_for(y, [o1, t1, m1, a1, c1, BBox(24, c1.y1, 1476, c1.y1 + 36)],
                  "Option 1 · one package, one folder per stage (recommended now)", ORC)

    # ---------------- Option 2 ----------------
    y = e1 + 70
    o2 = _box(d, 24, y + 46, 1452, "scheduler  (package)", "orchestrator and ROS node; keeps the stage-4 adapter",
              ["Scheduler::Plan(), scheduler_ros, ros/convert",
               "PlanMotions stays here: the stage-4 algorithm already is a package (motion_planner)"], ORC)
    ry = o2.y1 + G
    t2 = _box(d, 24, ry, 600, "task_planning  (new package)", "stages 1-3; installed headers become public API",
              ["job_expansion, tray_assignment, agv_assignment,", "validation as folders inside",
               "needs PlanContext and GarageServices", "  -> scheduler_core must exist first"], TP)
    m2 = _box(d, 688, ry, 380, "motion_planner  (exists)", "CHUGG, SIPP, searches, filters",
              ["already its own package", "nothing to move"], MP)
    a2 = _box(d, 1092, ry, 384, "action_graph  (new package)", "stage 5",
              ["inputs: event DAG, ContinuousState,", "  job list, initial state",
               "no PlanContext needed once", "  the inputs are narrowed"], AG)
    ly = max(t2.y1, m2.y1, a2.y1) + G
    c2 = _box(d, 24, ly, 600, "scheduler_core  (new package)", "PlanContext, GarageServices, types, vocabulary",
              ["a new package with its own CMake, package.xml", "and review owners"], CORE)
    l2 = _box(d, 688, ly, 788, "existing lower packages", "unchanged",
              ["planner_core, cost_functions, task_planner, common_ros, interfaces"], LOW)
    for b in (t2, m2, a2):
        down(o2, b, b.cx, "depends on", kind="dep")
    down(t2, c2, t2.cx, kind="dep", color=CORE)
    down(m2, l2, m2.cx, kind="dep", color=LOW)
    down(a2, l2, a2.cx, kind="dep", color=LOW)
    connect(d, [(t2.x1, t2.y0 + 40), (m2.x0, t2.y0 + 40)], kind="dep", color=MP, size=8,
            label="searches", label_at=((t2.x1 + m2.x0) / 2, t2.y0 + 30))
    connect(d, [(c2.x1, c2.cy), (l2.x0, c2.cy)], kind="dep", color=LOW, size=8)
    lane_for(y, [o2, t2, m2, a2, c2, l2], "Option 2 · one package per stage (target for proven stages)", TP)

    frame(d, title="Stage folders vs stage packages",
          subtitle="Both options follow the five pipeline stages. Option 1 draws the boundaries as folders inside "
                   "scheduler; Option 2 makes them packages, which needs a scheduler_core package first. Recommended: "
                   "Option 1 now, promote action_graph first, task_planning only after its interfaces are stable.",
          badge_key="proposed",
          legend=[("box", ORC, "orchestrator"), ("box", TP, "task planning (stages 1-3)"),
                  ("box", MP, "motion planning (stage 4)"), ("box", AG, "action graph (stage 5)"),
                  ("box", CORE, "shared core"), ("arrow", T.fg2, "calls"), ("dep", T.fg2, "depends on")],
          footnote="Proposed in doc 02 (module layout section). Folder paths are under scheduler/include/scheduler/, "
                   "scheduler/src/ and scheduler/test/.")
    return d
