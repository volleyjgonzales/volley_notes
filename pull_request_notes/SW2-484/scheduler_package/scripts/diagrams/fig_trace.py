"""Call-trace figures: time runs downwards, each nested call is indented one step to the right.

Every row names the function with its signature, the file and line where it is defined, and the line it is
called from. Line numbers are those of the files in sources/repomix-scheduler.xml.
"""
from __future__ import annotations

from components import connect, frame, label_pill, num_badge
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T

DOC1 = "01-software-background.html"
W = 1120
IND = 26
BOX_R = 800          # right edge of every call box
LOC_X = 816          # location column

KIND = {   # fill, stroke, label
    "ros": (T.teal, "ROS / component"),
    "sched": (T.sky, "Scheduler method (scheduler.cpp)"),
    "free": (T.tint(T.sky, 0.6, T.bg), "free function (scheduler.cpp)"),
    "ctx": (T.green, "ScheduleContext (scheduler.hpp)"),
    "utils": (T.violet, "utils.cpp"),
    "ext": (T.faint, "other package (file:line where a snapshot has it)"),
}


def _trace(d: Doc, rows, *, y0=0):
    """rows: dicts with depth, sig, loc, call, note, kind; or {'section': text}; or {'loop': text, depth}."""
    y = y0
    placed = []   # (index, depth, y_top, y_bottom)
    step = 0
    d.text(36, y, "time (down)   call (indented = called from the row above it)", size=11, family="mono",
           weight=600, fill=T.muted)
    d.text(LOC_X, y, "defined at   ·   called from", size=11, family="mono", weight=600, fill=T.muted)
    y += 18
    for r in rows:
        if "section" in r:
            y += 10
            d.rect(0, y, W, 28, rx=7, fill=T.tint(T.card, 0.8, T.bg), layer="bg")
            d.text(12, y + 14, r["section"], size=12.5, weight=600, fill=T.fg)
            y += 36
            continue
        depth = r["depth"]
        x = 36 + depth * IND
        if "loop" in r:
            d.text(x + 4, y + 9, "loop: " + r["loop"], size=10.5, family="mono", fill=T.amber)
            placed.append((None, depth, y, y + 18))
            y += 20
            continue
        step += 1
        col, _ = KIND[r["kind"]]
        bw = BOX_R - x
        sig = wrap(r["sig"], bw - 20, 10.5, "mono")[:3]
        note = wrap(r.get("note", ""), bw - 20, 10.5, "sans")[:2] if r.get("note") else []
        h = 8 + len(sig) * 14 + len(note) * 13 + 6
        dash = "4 3" if r["kind"] == "ext" else None
        d.rect(x, y, bw, h, rx=6, fill=T.tint(col, 0.13, T.bg), stroke=col, sw=1.3, dash=dash)
        for k, ln in enumerate(sig):
            d.text(x + 10, y + 12 + k * 14, ln, size=10.5, family="mono", fill=T.fg)
        for k, ln in enumerate(note):
            d.text(x + 10, y + 12 + len(sig) * 14 + k * 13, ln, size=10.5, fill=T.fg2)
        d.text(8, y + 11, str(step), size=10, family="mono", fill=T.faint)
        loc = r.get("loc", "")
        d.text(LOC_X, y + 11, loc, size=10.5, family="mono", weight=600,
               fill=T.fg if r["kind"] != "ext" else T.muted)
        if r.get("call"):
            for k, ln in enumerate(wrap("called from " + r["call"], W - LOC_X, 10, "mono")[:2]):
                d.text(LOC_X, y + 25 + k * 13, ln, size=10, family="mono", fill=T.muted)
        placed.append((len(placed), depth, y, y + h))
        y += h + 5
    # lifetime lines: from each call down to its last descendant
    for i, (idx, depth, yt, yb) in enumerate(placed):
        if idx is None:
            continue
        last = None
        for j in range(i + 1, len(placed)):
            if placed[j][1] <= depth:
                break
            last = placed[j]
        if last:
            x = 36 + depth * IND + 7
            d.line(x, yb, x, last[3] - 4, stroke=T.border, sw=2, layer="under")
            d.line(x, last[3] - 4, x + 8, last[3] - 4, stroke=T.border, sw=2, layer="under")
    # time arrow
    d.line(24, y0 + 26, 24, y - 8, stroke=T.faint, sw=1.2, layer="under")
    d.arrowhead((24, y - 4), (24, y - 14), kind="filled", color=T.faint, size=8)
    return y


def _legend():
    return [("box", KIND[k][0], KIND[k][1]) for k in KIND if k != "ext"] + \
           [("dashbox", KIND["ext"][0], KIND["ext"][1]), ("line", T.border, "call still running (its children)")]


S = "scheduler.cpp"
H = "scheduler.hpp"

PART1 = [
    {"section": "Start-up: once, when the ROS 2 component is loaded"},
    dict(depth=0, kind="ros", sig="explicit SchedulerComponent::SchedulerComponent(const rclcpp::NodeOptions& options)",
         loc="scheduler_component.cpp:35", note="Component entry point (RCLCPP_COMPONENTS_REGISTER_NODE). Reads "
         "parameters and creates SchedulerRos."),
    dict(depth=1, kind="ros", sig="static void ReadParams(cost::MotionCostParams& mc, NodeSPtr node)",
         loc="scheduler_component.cpp:10", note="AGV, VRC, bay and VECS speeds and times -> params.motion_cost"),
    dict(depth=1, kind="ext", sig="GetLayoutPathByName(layout_name)", loc="common_ros",
         note="'layout' parameter -> path of the layout YAML"),
    dict(depth=1, kind="ros", sig="SchedulerRos::SchedulerRos(const SchedulerParams& params, std::string "
         "layout_filepath, NodeSPtr node)", loc="scheduler_ros.cpp:14", note="Owns every ROS object and the Scheduler"),
    dict(depth=2, kind="sched", sig="Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger, "
         "const SchedulerParams& params)", loc=f"{S}:388", call="scheduler_ros.cpp:19 (make_shared)"),
    dict(depth=3, kind="ext", sig="Layout(layout_filepath) -> PoseGraph(layout_) -> GarageGraph(pg_) -> "
         "CollisionTable(gg_, logger)", loc="common_ros", note="member initialisers, in this order"),
    dict(depth=3, kind="sched", sig="void Scheduler::InitRetrievalHeadings()", loc=f"{S}:342", call=f"{S}:399",
         note="cache one retrieval heading per parking node"),
    dict(depth=4, kind="ext", sig="GetPosePath(gg_, candidate_pose, bay_pose, cost_model_)", loc="motion_planner",
         call=f"{S}:378", note="can a tray at this pose reach the bay?"),
    dict(depth=4, kind="ext", sig="gg_.SetRetrievalHeading(node.id, retrieval_heading)", loc="common_ros",
         call=f"{S}:384"),
    dict(depth=2, kind="ros", sig="rclcppx::CreateService<PlanSrv>(node_, \"plan\", [this](...) {...})",
         loc="scheduler_ros.cpp:36", note="Registers the plan lambda below. Also: timers, debug/printdags, "
         "/central clients, the *_request_fn_ callbacks."),
    {"section": "Every plan request: one TYPE_RETRIEVE job, following the success path"},
    dict(depth=0, kind="ros", sig="[this](PlanSrv::Request::SharedPtr request, PlanSrv::Response::SharedPtr "
         "response)", loc="scheduler_ros.cpp:38", note="the /plan service callback"),
    dict(depth=1, kind="sched", sig="PlanResponseMsg Scheduler::Plan(const PlanRequestMsg& request_data, const "
         "rclcpp::Time& now) const", loc=f"{S}:404", call="scheduler_ros.cpp:39", note="One Plan() call, step by step"),
    dict(depth=2, kind="utils", sig="std::pair<std::optional<volley::DiscreteGarageState>, std::string> "
         "ValidateBaseState(const DiscreteGarageStateMsg& state, const volley::Layout& layout)",
         loc="utils.cpp:12", call=f"{S}:412", note="request.base_state -> DiscreteGarageState; failure returns "
         "success = false"),
    dict(depth=2, kind="ext", sig="initial_state.SetAgvDisabled / SetNodeDisabled / SetBayDisabled / "
         "SetVecsDisabled(...)", loc="common_ros (discrete_garage_state.cpp)", call=f"{S}:427-438", note="entities used by base_schedule"),
    dict(depth=2, kind="ctx", sig="ScheduleContext::ScheduleContext(const GuidMsg& reqid, volley::DiscreteGarageState "
         "initial_state, const rclcpp::Time& now)", loc=f"{H}:59", call=f"{S}:443 (make_shared)",
         note="plan_ctx: the per-call context"),
    dict(depth=2, kind="ext", sig="GetDisabledEntitiesFilters(gg_, plan_ctx->initial_state, table_)",
         loc="motion_planner (static_graph_filtering.cpp)", call=f"{S}:447", note="-> plan_ctx->disabledness_filters"),
    dict(depth=2, loop="for(const SchedulerJobMsg& job : request_data.pending_jobs)   switch(job.type)   "
         f"{S}:454   (job expansion)"),
    dict(depth=3, kind="sched", sig="std::tuple<bool, std::string, bool> Scheduler::PlanRetrieveJob("
         "ScheduleContextSPtr ctx, const GuidMsg& payload_id, size_t job_index) const", loc=f"{S}:783",
         call=f"{S}:468", note="PlanRetrieveJob"),
    dict(depth=4, kind="ext", sig="ctx->events.Apply(working_state)", loc="event_dag.cpp:8", call=f"{S}:786",
         note="replay the DAG on a copy of initial_state"),
    dict(depth=4, kind="ctx", sig="void ScheduleContext::UpdateLastEntityEvent(const GarageEntityIdMsg& entity_id, "
         "ScheduleEventSPtr new_event)", loc=f"{H}:72", call=f"{S}:893", note="rule A for TRANSITION_TO_RETRIEVE"),
    dict(depth=4, kind="sched", sig="BoolStringPair Scheduler::PlanReparkTrayJob(ScheduleContextSPtr ctx, "
         "std::optional<uint16_t> tray_id, size_t job_index, bool allow_recip, std::optional<GaragePoseMsg> dest) "
         "const   x2", loc=f"{S}:937", call=f"{S}:904 (tray out), :918 (car in)", note="PlanReparkTrayJob"),
    dict(depth=5, kind="sched", sig="void Scheduler::UsePreferredHeading(GaragePoseMsg& dest, const "
         "std::optional<DiscretePayloadStateMsg>& payload_opt, const std::optional<DiscreteTrayStateMsg>& tray_opt) "
         "const", loc=f"{S}:1771", call=f"{S}:1058", note="-> UseEvChargeHeading :1781, UseRetrievalHeading :1805"),
    dict(depth=5, kind="ctx", sig="UpdateLastEntityEvent(...); events.AddDependency(...); "
         "UpdateLeafDependencies(...)", loc=f"{H}:72, :83", call=f"{S}:1066, :1075, :1091", note="rules A, C, B"),
    dict(depth=4, kind="ctx", sig="void ScheduleContext::UpdateLeafDependencies(const ScheduleEventSPtr& childevent, "
         "size_t job_index)", loc=f"{H}:83", call=f"{S}:932", note="rule B for PROCESS_RETRIEVE"),
    dict(depth=3, kind="ctx", sig="void ScheduleContext::PushBackScheduledJob(const SchedulerJobMsg& job)",
         loc=f"{H}:65", call=f"{S}:473", note="success: the job takes its job_index"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const",
         loc=f"{S}:2533", call=f"{S}:580", note="tray assignment; expanded in the next figure"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::DoAgvAssignments(ScheduleContextSPtr ctx) const",
         loc=f"{S}:3475", call=f"{S}:594", note="AGV assignment; expanded in the next figure"),
    dict(depth=2, kind="ext", sig="plan_ctx->events.Reduce()", loc="event_dag.hpp:318", call=f"{S}:608",
         note="drop redundant edges"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::SanityCheckEvents(ScheduleContextSPtr ctx) const",
         loc=f"{S}:3841", call=f"{S}:617", note="Reduce() and SanityCheckEvents"),
    dict(depth=3, kind="sched", sig="BoolStringPair Scheduler::IsMovePossible(ScheduleContextSPtr ctx, const "
         "volley::DiscreteGarageState& working_state, const volley::CollisionEntityId_t& collision_id, ...) const",
         loc=f"{S}:4131", call=f"{S}:3886, :3905"),
    dict(depth=2, kind="sched", sig="std::optional<volley::ContinuousState> Scheduler::PlanMotions("
         "ScheduleContextSPtr ctx) const", loc=f"{S}:4005", call=f"{S}:631", note="motion planning (Motion planning tab)"),
    dict(depth=3, kind="ext", sig="GetEdgeDurations(gg_, cost_model_); GetAllPairsMinCost(gg_, edge_durations, ...)",
         loc="motion_planner", call=f"{S}:4017, :4020"),
    dict(depth=3, kind="ext", sig="volley::Chugg motion_planner(gg_, table_, ctx->events, ...); "
         "motion_planner.SolveSequential(audit_ptr)", loc="motion_planner", call=f"{S}:4023, :4031",
         note="CHUGG: timed trajectories for every entity"),
    dict(depth=2, kind="sched", sig="std::pair<std::optional<std::vector<ActionNodeMsg>>, std::string> "
         "Scheduler::ResponseFromTrajectories(ScheduleContextSPtr ctx, const volley::ContinuousState& final_state) "
         "const", loc=f"{S}:4069", call=f"{S}:656", note="the action DAG (Action graph tab)"),
    dict(depth=3, kind="free", sig="std::optional<std::string> CollectAndCollapseTrajectoryMotions(const "
         "volley::ContinuousState& final_state, const volley::Layout& layout, std::set<volley::Motion, "
         "MotionScheduleOrder>& all_motions)", loc=f"{S}:151", call=f"{S}:4072"),
    dict(depth=3, kind="free", sig="std::optional<std::string> BuildActionDagFromMotions(all_motions, ctx, "
         "final_actions_dag, freeing_moves, event_start_end, logger)", loc=f"{S}:196", call=f"{S}:4081"),
    dict(depth=4, kind="free", sig="std::shared_ptr<ActionNodeMsg> ToActionNode(const volley::Motion& motion, "
         "GuidMsg job_id, const std::shared_ptr<volley::ScheduleEvent>& event)", loc=f"{S}:28", call=f"{S}:208",
         note="job_id = ctx->scheduled_jobs[event->GetJobIndex()].job.guid"),
    dict(depth=3, kind="free", sig="std::optional<std::string> TransferEventDagDepsToActionDag(ctx, "
         "event_start_end, final_actions_dag, logger)", loc=f"{S}:251", call=f"{S}:4097"),
    dict(depth=3, kind="utils", sig="stdx::Result InsertVrcActionsIntoDag(DagBase<ActionNodeMsg>& actions_dag, "
         "const Layout& layout, const DiscreteGarageState& initial_state, const cost::MotionCostModel& cost_model)",
         loc="utils.cpp:366", call=f"{S}:4111"),
    dict(depth=3, kind="free", sig="std::vector<ActionNodeMsg> BuildScheduledActionsArray(ScheduleContextSPtr ctx, "
         "volley::DagBase<ActionNodeMsg>& final_actions_dag, const std::vector<...::Vertex>& final_ordering)",
         loc=f"{S}:283", call=f"{S}:4128", note="topological order + parents -> Schedule.nodes"),
    dict(depth=2, kind="sched", sig="for(auto& scheduled_job : plan_ctx->scheduled_jobs) { state = "
         "STATE_EXECUTING; ... } return result;", loc=f"{S}:667", note="successful jobs appended to "
         "result.scheduled_jobs"),
    dict(depth=1, kind="ros", sig="job_data.job.time_planned = now; response->response_data = "
         "std::move(response_msg);", loc="scheduler_ros.cpp:42-44", note="back in the service callback"),
]

PART2 = [
    {"section": "Tray assignment"},
    dict(depth=0, kind="sched", sig="BoolStringPair Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const",
         loc=f"{S}:2533", call=f"{S}:580"),
    dict(depth=1, kind="ext", sig="ctx->events.GetTopologicalOrdering()", loc="event_dag.cpp:50", call=f"{S}:2540"),
    dict(depth=1, kind="ext", sig="GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>> freeing_moves(table_, gg_)",
         loc="common_ros"),
    dict(depth=1, loop="for each event in topological order"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::ApplyTransitionToFreeingMoves(const "
         "std::shared_ptr<ScheduleEvent>& event, DiscreteGarageState& working_state, GarageOccupancyChecker<...>& "
         "freeing_moves) const", loc=f"{S}:2124", call=f"{S}:2565", note="bay / VECS transitions"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::AssignTrayIdForEmptyMove(volley::TrayMove& move, "
         "const volley::DiscreteGarageState& working_state) const", loc=f"{S}:2159", call=f"{S}:2575",
         note="'? -> dest': nearest empty tray (GetStaticFilter + SingleSourceSearch)"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::AssignDestForUntargetedMove(volley::TrayMove* move, "
         "ScheduleContextSPtr ctx, const std::shared_ptr<ScheduleEvent>& event, DiscreteGarageState& working_state, "
         "...) const", loc=f"{S}:2222", call=f"{S}:2584", note="'tray -> ?': find a parking spot"),
    dict(depth=3, kind="sched", sig="ResolveBlockingTrays(uint16_t tray_id, size_t job_index, const "
         "DiscreteGarageState& base_state, const std::set<uint16_t>& immobile_trays, ...) const",
         loc=f"{S}:1984", call=f"{S}:2237", note="returns {destination, prerequisite moves}"),
    dict(depth=4, kind="sched", sig="std::optional<OpenSpaceSearchResult> Scheduler::FindOpenSpaceForRootTray("
         "uint16_t tray_id, CollisionEntityId_t collision_entity, const DiscreteGarageState& working_state, ...) "
         "const", loc=f"{S}:1850", call=f"{S}:2027, :2036", note="tier 1 parking, tier 2 waypoint stash"),
    dict(depth=4, kind="sched", sig="std::optional<BlockingTrayResolution> Scheduler::TryFindBlockingTrayResolution("
         "uint16_t blocking_tray_id, uint16_t root_tray_id, size_t job_index, ...) const", loc=f"{S}:1895",
         call=f"{S}:2061", note="may call ResolveBlockingTrays again (recursion, :1969)"),
    dict(depth=3, kind="sched", sig="void Scheduler::UsePreferredHeading(GaragePoseMsg& dest, ...) const",
         loc=f"{S}:1771", call=f"{S}:2259"),
    dict(depth=2, kind="ext", sig="volley::GetStaticFilter(...); volley::SingleSourceSearch(source, ..., "
         "BlockingTraySearchEnvironment)", loc="motion_planner", call=f"{S}:2622, :2664",
         note="critical path of the root tray and the trays blocking it"),
    dict(depth=2, kind="sched", sig="ResolveBlockingTrays(blocking_tray_id, move->GetJobIndex(), working_state, ...) "
         "const   per blocking tray", loc=f"{S}:1984", call=f"{S}:2728, :2850, :2865",
         note="fallbacks: advance the root tray, then allow parking on the critical path"),
    dict(depth=2, kind="ext", sig="tray_move->Apply(working_state)", loc="schedule_events.cpp:187", call=f"{S}:2833, :2931, :3053"),
    {"section": "AGV assignment"},
    dict(depth=0, kind="sched", sig="BoolStringPair Scheduler::DoAgvAssignments(ScheduleContextSPtr ctx) const",
         loc=f"{S}:3475", call=f"{S}:594"),
    dict(depth=1, kind="sched", sig="volley::Interval::Duration Scheduler::GetAgvOccupiedDuration(uint16_t, "
         "ScheduleContextSPtr) const", loc=f"{S}:3202", call=f"{S}:3509", note="always returns zero (TODO)"),
    dict(depth=1, loop="while(event_dag_copy.GetRootEvents().size() > 0)   drain non-tray roots, then match"),
    dict(depth=2, kind="sched", sig="BoolStringPair Scheduler::AddNodeArrivalDeps(uint32_t dest_node_id, uint16_t "
         "arriving_agv_id, const std::shared_ptr<ScheduleEvent>& new_event, ScheduleContextSPtr ctx, ...) const",
         loc=f"{S}:2392", call=f"{S}:3596"),
    dict(depth=2, kind="sched", sig="std::optional<Interval::Duration> Scheduler::GetAgvToTrayAssignmentCost("
         "uint16_t agv_id, const volley::TrayMove& move, const DiscreteGarageState& working_state, ...) const",
         loc=f"{S}:3208", call=f"{S}:3636", note="one cost per (AGV, root tray move)"),
    dict(depth=3, kind="sched", sig="std::optional<Interval::Duration> Scheduler::GetAgvCurrentPoseToTrayMoveCost("
         "uint16_t agv_id, const volley::TrayMove& move, ...) const", loc=f"{S}:3171", call=f"{S}:3243"),
    dict(depth=4, kind="sched", sig="std::optional<Interval::Duration> Scheduler::GetJustMovingCost(const "
         "GaragePoseMsg& start_pose, const GaragePoseMsg& end_pose, const GarageEntityIdMsg& agv_id, ...) const",
         loc=f"{S}:3094", call=f"{S}:3188", note="GetPosePath + cost model"),
    dict(depth=2, kind="ext", sig="volley::BottleneckAssignment(edge_costs, ...)", loc="task_planner",
         call=f"{S}:3657", note="minimise the largest assigned cost"),
    dict(depth=2, kind="sched", sig="volley::DagBase<uint16_t> Scheduler::GetEventDag(const std::unordered_map<"
         "uint16_t, std::optional<ScheduleEventSPtr>>& event_map, const DiscreteGarageState& working_state) const",
         loc=f"{S}:3296", call=f"{S}:3669", note="order of the matched AGVs"),
    dict(depth=3, kind="sched", sig="std::vector<uint16_t> Scheduler::AgvMatchingEventDeps(const ...& event_map, "
         "const DiscreteGarageState& working_state, const uint16_t agv_id) const", loc=f"{S}:3250",
         call=f"{S}:3313", note="table_.Query: AGV vs AGV"),
    dict(depth=2, loop="for each matched (AGV, tray move), in that order"),
    dict(depth=3, kind="sched", sig="BoolStringPair Scheduler::MoveAgvToTrayPose(uint16_t agv_id, const "
         "DiscreteAgvStateMsg& agv, const DiscreteTrayStateMsg& tray, const std::shared_ptr<ScheduleEvent>& "
         "root_event, ... (11 parameters)) const", loc=f"{S}:2414", call=f"{S}:3723",
         note="AgvMove to the tray; AddNodeArrivalDeps :2462, GetPosePath :2475"),
    dict(depth=3, kind="sched", sig="BoolStringPair Scheduler::AppendAgvLiftEvent(uint16_t agv_id, bool raised, "
         "size_t job_index, ScheduleContextSPtr ctx, ...) const", loc=f"{S}:2340", call=f"{S}:3730 (lift)"),
    dict(depth=3, kind="ext", sig="ctx->events.AddDependency(last_agv_event[agv_id], root_event)",
         loc="event_dag.hpp:142", note="the tray move itself is now this AGV's"),
    dict(depth=3, kind="sched", sig="AppendAgvLiftEvent(agv_id, false, ...) const", loc=f"{S}:2340",
         call=f"{S}:3779 (lower)"),
    dict(depth=3, kind="sched", sig="void Scheduler::PropagateEventCostToChildren(const "
         "std::shared_ptr<ScheduleEvent>& root_event, Interval::Duration event_cost, ...) const",
         loc=f"{S}:2369", call=f"{S}:3785"),
    dict(depth=1, kind="sched", sig="stdx::Result Scheduler::EnsureAgvMovePathsClear(ScheduleContextSPtr ctx) const",
         loc=f"{S}:3458", call=f"{S}:3797", note="up to 256 repair passes"),
    dict(depth=2, kind="sched", sig="stdx::Expected<bool> Scheduler::RunAgvPathRepairPass(ScheduleContextSPtr ctx) "
         "const", loc=f"{S}:3437", call=f"{S}:3463"),
    dict(depth=3, kind="sched", sig="bool Scheduler::TryClearBlockedAgvMove(ScheduleContextSPtr ctx, const "
         "ScheduleEventDag::VertexVec& topo, size_t idx, const ScheduleEventSPtr& event, ...) const",
         loc=f"{S}:3362", call=f"{S}:3447"),
    dict(depth=4, kind="sched", sig="ScheduleEventSPtr Scheduler::FindAgvDepartureFromNode(ScheduleContextSPtr ctx, "
         "const VertexVec& topo, size_t after_idx, uint16_t agv_id, uint32_t node) const", loc=f"{S}:3339",
         call=f"{S}:3424"),
    dict(depth=1, kind="ext", sig="ctx->events.Reduce()", loc="event_dag.hpp:318", call=f"{S}:3804"),
    dict(depth=1, kind="sched", sig="void Scheduler::AddDepsAfterAmiga(ScheduleContextSPtr ctx, "
         "std::shared_ptr<ScheduleEvent> event, uint16_t node_id) const", loc=f"{S}:3924", call=f"{S}:3831"),
]


@figure("39_call_trace_plan", "Call trace: start-up and one Plan() call", DOC1)
def call_trace_plan():
    d = Doc("39_call_trace_plan", "Call trace: start-up and one Plan() call",
            "Time runs downwards; every call is indented under the call that made it. Each row gives the "
            "signature, where the function is defined and the line it is called from.")
    _trace(d, PART1)
    frame(d, title="Call trace: start-up and one Plan() call",
          subtitle="Read from top to bottom. Indentation is call depth; the grey line under a call spans the calls "
                   "it makes. File:line numbers are those of the snapshot in sources/repomix-scheduler.xml.",
          badge_key="as-built", legend=_legend(),
          footnote="Only the calls that matter for understanding are shown: logging, getters and message "
                   "conversions are left out. Failure branches (each returns early; see 'One Plan() call') are not drawn.")
    return d


@figure("39_call_trace_assignment", "Call trace: tray and AGV assignment", DOC1)
def call_trace_assignment():
    d = Doc("39_call_trace_assignment", "Call trace: inside tray and AGV assignment",
            "The two calls collapsed in the previous figure, expanded the same way.")
    _trace(d, PART2)
    frame(d, title="Call trace: inside tray and AGV assignment",
          subtitle="Continuation of the previous figure: DoTrayAssignments() and DoAgvAssignments(), with the "
                   "helpers they call in the order they first call them.",
          badge_key="as-built", legend=_legend(),
          footnote="Loops are shown once (amber 'loop:' rows). Inside a loop the listed calls repeat per event or per matched AGV; "
                   "some only on certain branches.")
    return d
