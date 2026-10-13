"""Code-walkthrough figures, part 1: node context, runtime objects, Plan() control flow, job recipes."""
from __future__ import annotations

from components import (EVENT_COLOR, chip, class_size, code_panel, connect, event_box, flow, frame, label_pill,
                        note, num_badge, uml_class)
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC1 = "01-software-background.md"
TRAY, AGV, BAYC, VECS = T.amber, T.green, T.violet, T.pink


# --------------------------------------------------------------------------------------
# 20 — the scheduler node in its ROS context
# --------------------------------------------------------------------------------------

@figure("20_system_context", "The scheduler node and its ROS interfaces", DOC1)
def system_context():
    d = Doc("20_system_context", "The scheduler node and its ROS interfaces",
            "Dispatch calls the plan service; SchedulerRos forwards to Scheduler::Plan. The scheduler calls back "
            "into /central services to request follow-up jobs and publishes version info and a report every 5 s.")
    H_ROW = 40
    rows = [
        # (direction, name, type, note, color)
        ("in", "plan", "interfaces/srv/Plan", "PlanRequest -> PlanResponse", T.sky),
        ("in", "set_bay_readiness_ratio", "interfaces/srv/SetFloat32", "0.0 .. 1.0; may trigger a rebalance", T.sky),
        ("in", "debug/printdags", "std_srvs/srv/Trigger", "engineering toggle", T.faint),
        ("out", "/central/clean_garage", "std_srvs/srv/Trigger", "after a failed INSERT", T.amber),
        ("out", "/central/rebalance_garage", "std_srvs/srv/Trigger", "after the ratio changes", T.amber),
        ("out", "/central/transition_bay_to_insert", "interfaces/srv/TransitionBayToInsert", "after an INSERT",
         T.amber),
        ("out", "/central/transition_bay_to_retrieve", "interfaces/srv/TransitionBayToRetrieve", "(supported)",
         T.amber),
        ("pub", "version_info", "VersionInfo · every 5 s", "release, git SHA, layout md5", T.green),
        ("pub", "report", "SchedulerReport · every 5 s", "bay_readiness_ratio", T.green),
    ]
    ext_w = 168
    gap = 240
    node_x = ext_w + gap
    top = 110
    # external column
    ext_h = top + len(rows) * H_ROW + 40
    d.text(ext_w / 2, 26, "Dispatch", size=15, weight=600, fill=T.fg, anchor="middle")
    d.text(ext_w / 2, 46, "(central node)", size=12, fill=T.muted, anchor="middle")
    for i, ln in enumerate(wrap("Owns the job queue; calls plan and executes the returned schedule.", ext_w - 28,
                               11.5)):
        d.text(14, 72 + i * 16, ln, size=11.5, fill=T.muted)
    # node frame
    nx1 = node_x + 660
    d.text(node_x + 18, 24, "scheduler node", size=15, weight=600, fill=T.sky)
    d.text(node_x + 18, 44, "component volley::SchedulerComponent · executable scheduler_node", size=11,
           family="mono", fill=T.muted)
    # SchedulerRos column inside the node
    ros_x, ros_w = node_x + 18, 230
    d.rect(ros_x, top - 34, ros_w, len(rows) * H_ROW + 50, rx=10, fill=T.card, stroke=T.border, sw=1.2)
    d.text(ros_x + 12, top - 16, "SchedulerRos", size=13, family="mono", weight=700, fill=T.fg)
    d.text(ros_x + 128, top - 16, "scheduler_ros.cpp", size=10.5, family="mono", fill=T.faint)
    # Scheduler box
    sx = ros_x + ros_w + 130
    sch = uml_class(d, sx, top - 34, "Scheduler", accent=T.sky, stereo="planning core · scheduler.cpp", size=11.5,
                    w=nx1 - 18 - sx,
                    methods=["+ Plan(request, now)", "+ SetBayReadinessRatioCallback()", "+ GetVersionInfo()",
                             "+ GetSchedulerReport()", "+ PrintDags()"],
                    attrs=["- clean_garage_request_fn_", "- rebalance_garage_request_fn_",
                           "- reset_bay_state_request_fn_"])
    for i, (dirn, name, typ, nt, col) in enumerate(rows):
        y = top + i * H_ROW + 8
        # port on SchedulerRos
        d.text(ros_x + 12, y, name, size=11.5, family="mono", weight=600, fill=col)
        d.text(ros_x + 12, y + 15, typ, size=10, family="mono", fill=T.muted)
        lx0, lx1 = ext_w, ros_x
        if dirn == "in":
            connect(d, [(lx0, y + 6), (lx1 - 2, y + 6)], kind="flow", color=col, size=8, sw=1.5)
            d.text(lx0 + 12, y - 4, "service call", size=10, fill=T.faint)
        elif dirn == "out":
            connect(d, [(lx1, y + 6), (lx0 + 2, y + 6)], kind="flow", color=col, size=8, sw=1.5)
            d.text(lx0 + 12, y - 4, "async client request", size=10, fill=T.faint)
        else:
            connect(d, [(lx1, y + 6), (lx0 + 2, y + 6)], kind="flow", color=col, size=8, sw=1.5, dash="5 4")
            d.text(lx0 + 12, y - 4, "topic publish", size=10, fill=T.faint)
        d.text(lx1 - 8, y + 20, nt, size=10, fill=T.muted, anchor="end")
    # forwarding arrows Ros <-> Scheduler
    ay = sch.y0 + 74
    connect(d, [(ros_x + ros_w, ay), (sch.x0, ay)], kind="flow", color=T.sky, size=8,
            label="Plan(...)", label_at=((ros_x + ros_w + sch.x0) / 2, ay - 14), sw=1.5)
    by = sch.y1 - 30
    connect(d, [(sch.x0, by), (ros_x + ros_w, by)], kind="flow", color=T.amber, size=8, dash="5 4", sw=1.5)
    label_pill(d, (ros_x + ros_w + sch.x0) / 2, by - 14, "*_request_fn_()", color=T.amber)
    n1 = note(d, sx, sch.y1 + 18, nx1 - 18 - sx,
              "SchedulerRos stores lambdas in the three *_request_fn_ members (friend class). Scheduler calls them "
              "while planning, so it can ask Dispatch for follow-up jobs without knowing about ROS clients.",
              title="Callbacks instead of ROS clients")
    n2 = note(d, sx, n1.y1 + 14, nx1 - 18 - sx,
              "Timers run in their own MutuallyExclusive callback group, so a long Plan() call cannot delay the "
              "version_info heartbeat or the report.", title="Callback groups")
    fh = max(ext_h, n2.y1 + 18)
    d.rect(node_x, 0, nx1 - node_x, fh, rx=14, fill=T.tint(T.sky, 0.04, T.bg), stroke=T.sky, sw=1.4, layer="bg")
    d.rect(0, 0, ext_w, fh, rx=12, fill=T.bg, stroke=T.border, sw=1.4, dash="6 5", layer="bg")
    # params / layout inputs on top of node
    frame(d, title="The scheduler node and its ROS interfaces",
          subtitle="SchedulerComponent reads ROS parameters (layout name, cost-model limits, bay readiness ratio), "
                   "builds SchedulerRos, which owns the Scheduler. Arrows show who initiates each exchange.",
          badge_key="as-built",
          legend=[("arrow", T.sky, "called by Dispatch"), ("arrow", T.amber, "scheduler asks Dispatch"),
                  ("dasharrow", T.green, "published every 5 s")])
    return d


# --------------------------------------------------------------------------------------
# 21 — runtime objects, ownership and lifetimes
# --------------------------------------------------------------------------------------

@figure("21_runtime_objects", "Runtime objects and lifetimes", DOC1)
def runtime_objects():
    d = Doc("21_runtime_objects", "Who owns what, and for how long",
            "Node-lifetime objects (component, SchedulerRos, Scheduler and its graph/collision/cost members) versus "
            "the per-call ScheduleContext created inside Plan().")
    W = 1000
    # band 1: node lifetime
    b1y, b1h = 0, 440
    d.rect(0, b1y, W, b1h, rx=12, fill=T.tint(T.sky, 0.03, T.bg), stroke=T.tint(T.sky, 0.4, T.bg), sw=1, dash="6 5")
    d.text(16, b1y + 20, "lives as long as the ROS node", size=12, family="mono", weight=600, fill=T.sky)
    comp = uml_class(d, 20, 44, "SchedulerComponent", accent=T.fg2, stereo="rclcpp component", size=11.5,
                     attrs=["- scheduler_node_: unique_ptr<SchedulerRos>"], compact=True)
    ros = uml_class(d, 20, comp.y1 + 44, "SchedulerRos", accent=T.fg2, stereo="ROS adapter", size=11.5,
                    attrs=["- node_: NodeSPtr", "- scheduler_: SchedulerSPtr", "- plan_srv_, timers, clients"],
                    compact=True)
    connect(d, [(comp.x0 + 40, comp.y1), (ros.x0 + 40, ros.y0)], kind="comp", color=T.fg2)
    sch = uml_class(d, max(ros.x1, comp.x1) + 70, 44, "Scheduler", accent=T.sky, stereo="const planning service", size=11.5,
                    attrs=["- layout_: LayoutSPtr", "- pg_: PoseGraph", "- gg_: GarageGraph", "- table_: CollisionTable",
                           "- cost_model_: cost::MotionCostModel", "- bay_readiness_ratio_: atomic<float>",
                           "- logger_: rclcpp::Logger"],
                    methods=["+ Plan(request, now) const", "+ DoTrayAssignments(ctx) const",
                             "+ DoAgvAssignments(ctx) const"])
    connect(d, [(ros.x1, ros.y0 + 50), (sch.x0, ros.y0 + 50)], kind="comp", color=T.fg2, label="shared_ptr",
            label_at=((ros.x1 + sch.x0) / 2, ros.y0 + 36))
    # construction order strip
    cx = sch.x1 + 40
    d.text(cx, 52, "constructor initialiser order", size=12, weight=600, fill=T.fg)
    steps = [("layout_", "Layout(layout_filepath)", "parse layout YAML"),
             ("pg_", "PoseGraph(layout_)", "node x heading poses"),
             ("gg_", "GarageGraph(pg_)", "search graph"),
             ("table_", "CollisionTable(gg_, logger)", "pairwise conflicts"),
             ("cost_model_", "MotionCostModel(params)", "speeds, lift, doors"),
             ("gg_", "InitRetrievalHeadings()", "caches best parking heading")]
    y = 72
    prev = None
    for i, (mem, ctor, why) in enumerate(steps, start=1):
        bb = BBox(cx, y, W - 16, y + 46)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.card, stroke=T.border, sw=1)
        num_badge(d, bb.x0, bb.y0 + 2, i, T.sky if i < 6 else T.amber, r=9)
        d.text(bb.x0 + 16, y + 17, ctor, size=11.5, family="mono", fill=T.fg)
        d.text(bb.x0 + 16, y + 35, why, size=11, fill=T.muted)
        if prev:
            connect(d, [(prev.x0 + 30, prev.y1), (bb.x0 + 30, bb.y0)], kind="flow", color=T.faint, size=7)
        prev = bb
        y = bb.y1 + 12
    d.text(cx, y + 8, "each member is built from the one before it", size=11, fill=T.muted)
    # band 2: per call
    b2y = b1h + 30
    b2h = 300
    d.rect(0, b2y, W, b2h, rx=12, fill=T.tint(T.green, 0.03, T.bg), stroke=T.tint(T.green, 0.4, T.bg), sw=1,
           dash="6 5")
    d.text(16, b2y + 20, "lives for one Plan() call", size=12, family="mono", weight=600, fill=T.green)
    ctx = uml_class(d, 20, b2y + 44, "ScheduleContext", accent=T.green, stereo="held as ScheduleContextSPtr ctx",
                    size=11.5, attrs=["+ request_id: GuidMsg", "+ initial_state: DiscreteGarageState",
                                      "+ start_time: Interval::Timepoint",
                                      "+ disabledness_filters: map<CollisionEntityId_t, ...>",
                                      "+ events: ScheduleEventDag", "+ scheduled_jobs: vector<ScheduledJobDataMsg>",
                                      "+ last_entity_event: map<GarageEntityIdMsg, EventSPtr>",
                                      "+ first_tray_event: map<uint16_t, EventSPtr>"], compact=True)
    connect(d, [(sch.cx, sch.y1), (sch.cx, b2y + 30), (ctx.cx, b2y + 30), (ctx.cx, ctx.y0)], kind="dep",
            color=T.green, label="«create» make_shared in Plan()", label_at=((sch.cx + ctx.cx) / 2, b2y + 30))
    nx = ctx.x1 + 40
    note(d, nx, b2y + 50, W - nx - 20,
         "Scheduler's planning methods are const: they never change the Scheduler. Everything that changes "
         "during planning lives in *ctx. A const method may still modify the object a shared_ptr argument "
         "points to, which is how DoTrayAssignments(ctx) const edits ctx->events.", title="Why const methods can still plan")
    note(d, nx, b2y + 172, W - nx - 20,
         "The context is created at the start of Plan() and released when Plan() returns. Nothing persists "
         "between plan calls except the Scheduler members above.", title="No hidden state between calls")
    frame(d, title="Who owns what, and for how long",
          subtitle="Two lifetimes matter. The node keeps one Scheduler with its graphs and cost model; every plan "
                   "request gets a fresh ScheduleContext that holds all mutable planning data.",
          badge_key="as-built",
          legend=[("comp", T.fg2, "owns (member)"), ("dep", T.green, "creates per call"),
                  ("box", T.sky, "node-lifetime object"), ("box", T.green, "per-call object")])
    return d


# --------------------------------------------------------------------------------------
# 22 — Plan() control flow and failure semantics
# --------------------------------------------------------------------------------------

@figure("22_plan_control_flow", "Scheduler::Plan control flow", DOC1)
def plan_flow():
    d = Doc("22_plan_control_flow", "Scheduler::Plan() step by step",
            "Flowchart of Scheduler::Plan with each early return and what the PlanResponse contains in that case.")
    cw = 470
    x0 = 0
    steps = [
        ("ValidateBaseState(request_data.base_state, *layout_)", "build DiscreteGarageState; check poses + payload sizes",
         "bad", "success = false · \"Invalid base state\" · no jobs touched"),
        ("disable resources used by request_data.base_schedule", "AGVs, their src/dst nodes, bays, VECS in running actions",
         None, None),
        ("plan_ctx = make_shared<ScheduleContext>(...)", "plus disabledness_filters from the initial state", None, None),
        ("for each job in pending_jobs: Plan<Type>Job(plan_ctx, ...)", "adds events to plan_ctx->events",
         "job", "FailJob(job): STATE_ERROR, other jobs continue"),
        ("plan_ctx->scheduled_jobs empty?", None, "empty", "success = true · \"No jobs succeeded to plan\""),
        ("DoTrayAssignments(plan_ctx)", "every TrayMove gets a tray id and a destination", "all", None),
        ("DoAgvAssignments(plan_ctx)", "AGVs matched; move / lift / lower events added", "all", None),
        ("plan_ctx->events.Reduce()", "drop redundant edges", None, None),
        ("SanityCheckEvents(plan_ctx)", "replay in topological order; every move must have a path", "all", None),
        ("PlanMotions(plan_ctx)", "CHUGG: timed trajectories for every entity", "all", None),
        ("ResponseFromTrajectories(plan_ctx, ...)", "action DAG -> ActionNode[] with parent indices", "all", None),
        ("mark jobs STATE_EXECUTING; fill schedule.nodes", "RETRIEVE jobs get bay_id + bay_arrival_node_guid", "ok",
         "success = true · schedule returned"),
    ]
    y = 0
    boxes = []
    for i, (code, why, kind, out) in enumerate(steps):
        h = 54 if why else 38
        stage_col = T.amber if "Tray" in code else T.green if "Agv" in code else T.sky if "Motions" in code or \
            "Response" in code else T.fg2
        if kind == "empty" or code.endswith("?"):
            stage_col = T.fg2
        bb = BBox(x0, y, x0 + cw, y + h)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.card, stroke=stage_col if stage_col != T.fg2 else T.border,
               sw=1.3)
        num_badge(d, bb.x0, bb.y0 + 2, i + 1, stage_col if stage_col != T.fg2 else T.muted, r=10)
        d.text(bb.x0 + 18, y + 18, code, size=11.5, family="mono", fill=T.fg)
        if why:
            d.text(bb.x0 + 18, y + 37, why, size=11, fill=T.muted)
        boxes.append((bb, kind, out))
        y = bb.y1 + 18
    for (a, _, _), (b, _, _) in zip(boxes, boxes[1:]):
        connect(d, [(a.x0 + 40, a.y1), (b.x0 + 40, b.y0)], kind="flow", color=T.faint, size=7)
    # outcomes column
    ox = x0 + cw + 120
    ow = 330
    bus_x = x0 + cw + 50
    all_boxes = [b for b, k, _ in boxes if k == "all"]
    for bb, kind, out in boxes:
        if kind in ("bad", "job", "empty", "ok"):
            col = {"bad": T.red, "job": T.amber, "empty": T.fg2, "ok": T.green}[kind]
            oy = bb.cy
            connect(d, [(bb.x1, oy), (ox, oy)], kind="flow", color=col, size=8, sw=1.4,
                    dash=None if kind == "ok" else "5 4")
            lines = wrap(out, ow - 24, 11.5, "sans")
            hh = 14 + len(lines) * 16
            d.rect(ox, oy - hh / 2, ow, hh, rx=8, fill=T.tint(col, 0.10, T.bg), stroke=col, sw=1.2)
            for j, ln in enumerate(lines):
                d.text(ox + 12, oy - hh / 2 + 15 + j * 16, ln, size=11.5, fill=T.fg)
    # shared failure bus for later stages
    for bb in all_boxes:
        d.line(bb.x1, bb.cy, bus_x, bb.cy, stroke=T.red, sw=1.4, dash="5 4", layer="edges")
        d.circle(bus_x, bb.cy, 2.5, fill=T.red)
    y0, y1 = all_boxes[0].cy, all_boxes[-1].cy
    d.line(bus_x, y0, bus_x, y1, stroke=T.red, sw=1.4, dash="5 4", layer="edges")
    my = (y0 + y1) / 2
    connect(d, [(bus_x, my), (ox, my)], kind="flow", color=T.red, size=8, sw=1.4, dash="5 4")
    lines = wrap("Every pending job -> FailJob(job, message). PlanResponse.success stays TRUE; the stage name is in "
                 "message. No partial schedule is returned.", ow - 24, 11.5)
    hh = 14 + len(lines) * 16
    d.rect(ox, my - hh / 2, ow, hh, rx=8, fill=T.tint(T.red, 0.10, T.bg), stroke=T.red, sw=1.2)
    for j, ln in enumerate(lines):
        d.text(ox + 12, my - hh / 2 + 15 + j * 16, ln, size=11.5, fill=T.fg)
    note(d, ox, boxes[1][0].y0 - 6, ow,
         "success = false only means the request itself was unusable. Check each ScheduledJobData.job.state "
         "(STATE_EXECUTING vs STATE_ERROR) and job.note to see what really happened.",
         title="Reading a PlanResponse", accent=T.amber)
    frame(d, title="Scheduler::Plan() step by step",
          subtitle="Job expansion fails jobs one at a time. Any failure after expansion fails every pending job "
                   "at once, because the shared event DAG is no longer trustworthy.",
          badge_key="as-built",
          legend=[("box", T.amber, "tray stage"), ("box", T.green, "AGV stage"), ("box", T.sky, "motion stage"),
                  ("dasharrow", T.red, "early return")])
    return d


# --------------------------------------------------------------------------------------
# 24 — job type -> event recipe
# --------------------------------------------------------------------------------------

@figure("24_job_recipes", "Job types and the events they create", DOC1)
def job_recipes():
    d = Doc("24_job_recipes", "What each job type adds to the event DAG",
            "For each SchedulerJob type, the ScheduleEvents its Plan<Type>Job method creates, in order. Dashed "
            "events are conditional.")
    T_ = TRAY
    rows = [
        ("TYPE_MOVE_AGV", "PlanAgvMoveJob",
         [("AgvMove", "pose -> dest", "s"), ("or", "", ""), ("TrayMove", "carried tray -> dest", "o")],
         "TrayMove if the AGV is already carrying a tray"),
        ("TYPE_RETRIEVE", "PlanRetrieveJob",
         [("VecsTransition", "stop charging", "o"), ("BayTransition", "TO_RETRIEVE", "o"),
          ("TrayMove", "bay tray -> ?", "o"), ("TrayMove", "payload tray -> bay", "s"),
          ("BayTransition", "PROCESS_RETRIEVE", "s")], "bay chosen from GetBayPrioritization(), back first"),
        ("TYPE_REPARK_TRAY / MOVE_TRAY", "PlanReparkTrayJob",
         [("VecsTransition", "stop charging", "o"), ("TrayMove", "tray -> dest or ?", "s")],
         "heading may change to the cached retrieval heading"),
        ("TYPE_INSERT", "PlanInsertJob",
         [("BayTransition", "TO_RETRIEVE (open door)", "s"), ("TrayMove", "loaded tray -> ?", "s"),
          ("async", "ask /central for READY_FOR_INSERT", "a")], "bay must be VEHICLE_INSERTED or READY_TO_RETRIEVE"),
        ("TYPE_READY_FOR_INSERT", "PlanReadyForInsertJob",
         [("recipe", "CHARGE_PAYLOAD", "o"), ("TrayMove", "? empty tray -> bay", "s"),
          ("BayTransition", "TO_INSERT", "s")], "bay must be READY_TO_RETRIEVE"),
        ("TYPE_READY_FOR_RETRIEVE", "PlanReadyForRetrieveJob",
         [("BayTransition", "TO_RETRIEVE", "o"), ("TrayMove", "bay tray -> ?", "o"), ("or", "", ""),
          ("recipe", "CHARGE_PAYLOAD", "o")], "charge if the payload asked for EV charging"),
        ("TYPE_CLEAN_GARAGE", "PlanCleanGarageJob",
         [("AgvMove", "hide AGVs (x n)", "o"), ("TrayMove", "unstash waypoint tray -> ? (x n)", "o")],
         "AGVs are hidden only when this is job index 0"),
        ("TYPE_REBALANCE_GARAGE", "PlanRebalanceGarageJob",
         [("recipe", "READY_FOR_INSERT per bay", "o"), ("recipe", "READY_FOR_RETRIEVE per bay", "o")],
         "bays chosen by ComputeBayRebalancingActions(); never fails"),
        ("TYPE_CHARGE_AGV", "PlanAgvChargeJob",
         [("BayTransition", "TO_RETRIEVE", "o"), ("AgvMove", "-> fastest free charger", "s"),
          ("BayTransition", "TO_INSERT", "o")], "bay transitions only if the AGV is trapped in a bay"),
        ("TYPE_TRANSITION_BAY_TO_*", "PlanBayTransitionJob", [("BayTransition", "TO_INSERT or TO_RETRIEVE", "s")],
         "rejected if the bay ODP area is occupied"),
        ("TYPE_CHARGE_PAYLOAD", "PlanChargePayloadJob",
         [("TrayMove", "tray -> VECS", "o"), ("VecsTransition", "start charging", "s")],
         "VECS picked with ResolveBlockingTrays if the tray is not on one"),
    ]
    lw = 268
    rh = 86
    W = 1060
    for i, (jt, fn, chips, note_) in enumerate(rows):
        y = i * rh
        if i % 2 == 0:
            d.rect(-8, y - 6, W + 16, rh - 4, rx=8, fill=T.tint(T.card, 0.45, T.bg), layer="bg")
        d.text(0, y + 16, jt, size=12, family="mono", weight=700, fill=T.fg)
        d.text(0, y + 34, fn + "()", size=11, family="mono", fill=T.muted)
        x = lw
        prev = None
        for kind, txt, st in chips:
            if kind == "or":
                d.text(x + 4, y + 25, "or", size=12, fill=T.muted)
                x += 30
                prev = None
                continue
            if kind == "async":
                bb = BBox(x, y, x + text_width(txt, 11, "sans") + 24, y + 50)
                d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.bg, stroke=T.faint, sw=1.2, dash="2 4")
                d.text(bb.x0 + 12, y + 15, "after planning", size=10.5, family="mono", weight=600, fill=T.faint)
                d.text(bb.x0 + 12, y + 34, txt, size=11, fill=T.muted)
                if prev:
                    connect(d, [(prev.x1 + 2, prev.cy), (bb.x0 - 2, bb.cy)], kind="flow", color=T.faint, size=7,
                            dash="3 3")
                prev = bb
                x = bb.x1 + 22
                continue
            label = kind if kind != "recipe" else "+ recipe"
            bb = event_box(d, x, y, label, txt, style="optional" if st == "o" else "solid", size=11.5,
                           color=EVENT_COLOR.get(kind, T.fg2) if kind != "recipe" else T.fg2)
            if prev:
                connect(d, [(prev.x1 + 2, prev.cy), (bb.x0 - 2, bb.cy)], kind="flow", color=T.faint, size=7)
            prev = bb
            x = bb.x1 + 22
        d.text(lw, y + 66, note_, size=11, fill=T.muted)
    frame(d, title="What each job type adds to the event DAG",
          subtitle="Plan() dispatches on SchedulerJob.type. Each Plan<Type>Job appends ScheduleEvents to ctx->events. "
                   "A \"?\" means the tray or destination is left empty for DoTrayAssignments() to fill.",
          badge_key="as-built",
          legend=[("box", TRAY, "TrayMove"), ("box", AGV, "AgvMove"), ("box", BAYC, "BayTransition"),
                  ("box", VECS, "VecsTransition"), ("dashbox", T.fg2, "only when needed"),
                  ("arrow", T.faint, "creation order")])
    return d
