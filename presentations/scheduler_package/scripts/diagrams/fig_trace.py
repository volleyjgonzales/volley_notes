"""Call-trace figures: time runs downwards, each nested call is indented one step to the right.

Every row names the function with its signature, the file and line where it is defined, and the line it is
called from. Line numbers are computed from the files in sources/repomix-*.xml (main at a468657f) by snapshot.py.
"""
from __future__ import annotations

from pathlib import Path

import snapshot
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
    "sched": (T.sky, "Scheduler method (src/<stage>.cpp)"),
    "free": (T.tint(T.sky, 0.6, T.bg), "file-local function or state struct (src/<stage>.cpp)"),
    "ctx": (T.green, "PlanContext (plan_context.hpp)"),
    "utils": (T.violet, "utils.cpp / move_events.cpp"),
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


# Every location below is computed from the snapshots in sources/ (see snapshot.py): `L(name)` is where a function is
# defined, `C(caller, regex)` the line(s) in the caller's file where the regex matches inside the caller's body.
L = snapshot.loc
C = snapshot.call


def F(path: str, pattern: str, pkg: str = "scheduler", nth: int = 0) -> str:
    """'file:line' of the nth match of `pattern` anywhere in a snapshot file."""
    return f"{Path(path).name}:{snapshot.line_of(path, pattern, pkg, nth)}"


def LX(name: str, pkg: str) -> str:
    return f"{snapshot.loc(name, pkg)}"


def lines(caller: str, pattern: str, labels: list[str]) -> str:
    """'file.cpp:12 (a), :30 (b)' for the matches of `pattern` in the caller, one label each."""
    ls = snapshot.calls(caller, pattern)
    f = snapshot.fn(caller).file
    return f + ", ".join(f":{ln} ({lab})" for ln, lab in zip(ls, labels))


COMP = "src/scheduler_component.cpp"
ROS = "src/scheduler_ros.cpp"
PCH = "include/scheduler/plan_context.hpp"
DAGH = "include/planner_core/event_dag.hpp"


def _part1():
    return [
        {"section": "Start-up: once, when the ROS 2 component is loaded"},
        dict(depth=0, kind="ros", sig="explicit SchedulerComponent::SchedulerComponent(const rclcpp::NodeOptions& "
             "options)", loc=F(COMP, r"explicit SchedulerComponent\("), note="Component entry point "
             "(RCLCPP_COMPONENTS_REGISTER_NODE, volley::SchedulerComponent). Reads parameters and creates SchedulerRos."),
        dict(depth=1, kind="ros", sig="static void ReadMotionCostParams(cost::MotionCostParams& motion_cost, NodeSPtr "
             "node)", loc=L("ReadMotionCostParams"), call=F(COMP, r"ReadMotionCostParams\(params"),
             note="AGV, VRC, bay and VECS speeds and times -> params.motion_cost"),
        dict(depth=1, kind="ext", sig="GetLayoutPathByName(layout_name)", loc="common_ros",
             call=F(COMP, r"GetLayoutPathByName\("), note="'layout' parameter -> path of the layout YAML"),
        dict(depth=1, kind="ros", sig="SchedulerRos::SchedulerRos(const SchedulerParams& params, std::string "
             "layout_filepath, NodeSPtr node)", loc=L("SchedulerRos::SchedulerRos"),
             call=F(COMP, r"make_unique<scheduler::SchedulerRos>") + " (make_unique)",
             note="Owns every ROS object and the Scheduler"),
        dict(depth=2, kind="sched", sig="Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger, "
             "const SchedulerParams& params)", loc=L("Scheduler::Scheduler"),
             call=C("SchedulerRos::SchedulerRos", r"make_shared<Scheduler>") + " (make_shared)"),
        dict(depth=3, kind="ext", sig="Layout(layout_filepath) -> motion_graph_(PoseGraph(layout_)) -> "
             "collision_table_(motion_graph_, logger)", loc="common_ros",
             note="member initialisers, in this order; the PoseGraph is a temporary"),
        dict(depth=3, kind="sched", sig="void Scheduler::StorePreferredPayloadHeadingsForRetrieval()",
             loc=L("StorePreferredPayloadHeadingsForRetrieval"),
             call=C("Scheduler::Scheduler", r"StorePreferredPayloadHeadingsForRetrieval\("),
             note="store a retrieval heading on every parking node that allows it"),
        dict(depth=4, kind="ext", sig="FindPosePath(motion_graph_, parking_pose, preferred_bay_pose, cost_model_)",
             loc=LX("FindPosePath", "motion_planner"),
             call=C("StorePreferredPayloadHeadingsForRetrieval", r"\bFindPosePath\("),
             note="can a tray at this pose reach the preferred retrieve bay?"),
        dict(depth=4, kind="ext", sig="motion_graph_.SetRetrievalHeading(node.id, preferred_retrieval_heading)",
             loc="common_ros", call=C("StorePreferredPayloadHeadingsForRetrieval", r"SetRetrievalHeading\(")),
        dict(depth=2, kind="ros", sig="rclcppx::CreateService<interfaces::srv::Plan>(node_, \"plan\", [this](...) "
             "{...})", loc=C("SchedulerRos::SchedulerRos", r"CreateService<interfaces::srv::Plan>"),
             note="Registers the plan lambda below. Also: timers, debug/printdags, /central clients, the "
                  "*_request_fn_ callbacks."),
        {"section": "Every plan request: one TYPE_RETRIEVE job, following the success path"},
        dict(depth=0, kind="ros", sig="[this](interfaces::srv::Plan::Request::SharedPtr request, "
             "interfaces::srv::Plan::Response::SharedPtr response)",
             loc=C("SchedulerRos::SchedulerRos", r"\[this\]\(interfaces::srv::Plan::Request"),
             note="the /plan service callback"),
        dict(depth=1, kind="sched", sig="interfaces::msg::PlanResponse Scheduler::Plan(const interfaces::msg::"
             "PlanRequest& request_data, const rclcpp::Time& now) const", loc=L("Scheduler::Plan"),
             call=C("SchedulerRos::SchedulerRos", r"scheduler_->Plan\("), note="One Plan() call, step by step"),
        dict(depth=2, kind="utils", sig="stdx::Expected<DiscreteGarageState> ValidateBaseState(const "
             "interfaces::msg::DiscreteGarageState& state, const Layout& layout)", loc=L("ValidateBaseState"),
             call=C("Scheduler::Plan", r"\bValidateBaseState\("),
             note="request.base_state -> DiscreteGarageState; failure returns success = false"),
        dict(depth=2, kind="free", sig="DiscreteGarageState ExcludeCommittedResources(DiscreteGarageState state, "
             "std::span<const interfaces::msg::ActionNode> committed_actions)", loc=L("ExcludeCommittedResources"),
             call=C("Scheduler::Plan", r"\bExcludeCommittedResources\("),
             note="SetAgvDisabled / SetNodeDisabled / SetBayDisabled / SetVecsDisabled for what base_schedule uses"),
        dict(depth=2, kind="ctx", sig="PlanContext::PlanContext(const interfaces::msg::Guid& request_id, "
             "DiscreteGarageState initial_state, const rclcpp::Time& now)", loc=F(PCH, r"^  PlanContext\("),
             call=C("Scheduler::Plan", r"make_shared<PlanContext>") + " (make_shared)",
             note="ctx: the per-call context"),
        dict(depth=2, kind="ext", sig="BuildKeepOutFilters(motion_graph_, ctx->initial_state, collision_table_)",
             loc=LX("BuildKeepOutFilters", "motion_planner"), call=C("Scheduler::Plan", r"\bBuildKeepOutFilters\("),
             note="-> ctx->keep_out_filter_by_footprint"),
        dict(depth=2, loop="for(const interfaces::msg::SchedulerJob& job : request_data.pending_jobs)   "
             "copy *ctx, then ExpandJob   " + C("Scheduler::Plan", r"for\(const interfaces::msg::SchedulerJob& job")
             + "   (job expansion)"),
        dict(depth=3, kind="sched", sig="stdx::Expected<void, JobFailure> Scheduler::ExpandJob(PlanContextSPtr ctx, "
             "const interfaces::msg::SchedulerJob& job) const", loc=L("ExpandJob"),
             call=C("Scheduler::Plan", r"\bExpandJob\("), note="switch(job.type); job_index = "
             "ctx->scheduled_jobs.size()"),
        dict(depth=4, kind="sched", sig="stdx::Expected<void, JobFailure> Scheduler::ExpandRetrieveJob("
             "PlanContextSPtr ctx, const interfaces::msg::Guid& payload_id, size_t job_index) const",
             loc=L("ExpandRetrieveJob"), call=C("ExpandJob", r"\bExpandRetrieveJob\(")),
        dict(depth=5, kind="free", sig="ComputeStateAfterPlannedEvents(const PlanContext& ctx)  ->  "
             "ctx.event_dag.ApplyEventsTo(state)", loc=L("ComputeStateAfterPlannedEvents"),
             call=C("ExpandRetrieveJob", r"\bComputeStateAfterPlannedEvents\("),
             note="replay the DAG on a copy of initial_state"),
        dict(depth=5, kind="sched", sig="std::optional<interfaces::msg::DiscreteBayState> Scheduler::"
             "FindBayForRetrieve(const DiscreteGarageState& working_state, const "
             "interfaces::msg::DiscretePayloadState& payload) const", loc=L("FindBayForRetrieve"),
             call=C("ExpandRetrieveJob", r"\bFindBayForRetrieve\(")),
        dict(depth=5, kind="ctx", sig="void PlanContext::AddChainedEvent(const ScheduleEventSPtr& event)",
             loc=F(PCH, r"void AddChainedEvent\("), call=C("ExpandRetrieveJob", r"AddChainedEvent\(", nth=0),
             note="AddEvent + ChainAfterLastEntityEvent for TRANSITION_TO_RETRIEVE (only when the bay is not ready to retrieve)"),
        dict(depth=5, kind="sched", sig="stdx::Expected<void, JobFailure> Scheduler::ExpandReparkTrayJob("
             "PlanContextSPtr ctx, std::optional<uint16_t> tray_id, size_t job_index, bool "
             "is_reciprocal_heading_allowed, std::optional<interfaces::msg::GaragePose> dest) const   x2",
             loc=L("ExpandReparkTrayJob"),
             call=lines("ExpandRetrieveJob", r"\bExpandReparkTrayJob\(", ["tray out", "car in"])),
        dict(depth=6, kind="sched", sig="std::optional<int16_t> Scheduler::FindPreferredTrayHeadingForRetrieval("
             "uint32_t node_id, const std::optional<interfaces::msg::DiscretePayloadState>& payload_opt) const",
             loc=L("FindPreferredTrayHeadingForRetrieval"),
             call=C("ExpandReparkTrayJob", r"\bFindPreferredTrayHeadingForRetrieval\("),
             note="the node's retrieval heading for this payload, or nullopt; the caller assigns it"),
        dict(depth=6, kind="sched", sig="stdx::Expected<void, JobFailure> Scheduler::CheckReparkDestination("
             "PlanContext& ctx, const DiscreteGarageState& working_state, ...) const",
             loc=L("CheckReparkDestination"), call=C("ExpandReparkTrayJob", r"\bCheckReparkDestination\("),
             note="VECS ready, vertex exists, FindKeepOutFilter, bay not disabled"),
        dict(depth=6, kind="utils", sig="std::shared_ptr<TrayMove> MakeTrayMove(size_t job_index, "
             "std::optional<uint16_t> tray_id, std::optional<interfaces::msg::GaragePose> dest, ...)",
             loc=L("MakeTrayMove"), call=C("ExpandReparkTrayJob", r"\bMakeTrayMove\(")),
        dict(depth=6, kind="ctx", sig="ctx->AddChainedEvent(tray_move); OrderAfterBayAndChargerEvents(...); "
             "ctx->OrderAfterJobLeafEvents(tray_move)", loc=F(PCH, r"void AddChainedEvent\(") + ", "
             + L("OrderAfterBayAndChargerEvents"),
             call=C("ExpandReparkTrayJob", r"AddChainedEvent\(|\bOrderAfterBayAndChargerEvents\(|"
                    r"OrderAfterJobLeafEvents\("), note="called in this order"),
        dict(depth=5, kind="ctx", sig="void PlanContext::OrderAfterJobLeafEvents(const ScheduleEventSPtr& event)",
             loc=F(PCH, r"void OrderAfterJobLeafEvents\("),
             call=C("ExpandRetrieveJob", r"OrderAfterJobLeafEvents\("), note="edges from job 0's leaves to PROCESS_RETRIEVE"),
        dict(depth=3, kind="ctx", sig="void PlanContext::AddScheduledJob(const interfaces::msg::SchedulerJob& job)",
             loc=F(PCH, r"void AddScheduledJob\("), call=C("Scheduler::Plan", r"AddScheduledJob\("),
             note="success: the job takes its job_index. On failure *ctx is restored (no events left) and "
                  "MakeFailedJob reports the job."),
        dict(depth=2, kind="sched", sig="[[nodiscard]] stdx::Result Scheduler::AssignTrays(PlanContextSPtr ctx) "
             "const", loc=L("AssignTrays"), call=C("Scheduler::Plan", r"\bAssignTrays\("),
             note="tray assignment; expanded in the next figure"),
        dict(depth=2, kind="sched", sig="[[nodiscard]] stdx::Result Scheduler::AssignAgvs(PlanContextSPtr ctx) const",
             loc=L("AssignAgvs"), call=C("Scheduler::Plan", r"\bAssignAgvs\("),
             note="AGV assignment; expanded in the next figure"),
        dict(depth=2, kind="ext", sig="ctx->event_dag.RemoveRedundantEdges()  ->  stdx::Result",
             loc=F(DAGH, r"RemoveRedundantEdges\(", "planner_core"),
             call=C("Scheduler::Plan", r"RemoveRedundantEdges\("),
             note="drop implied edges; a cycle fails every job"),
        dict(depth=2, kind="sched", sig="[[nodiscard]] stdx::Result Scheduler::ValidateEventSequence(PlanContextSPtr "
             "ctx) const", loc=L("ValidateEventSequence"), call=C("Scheduler::Plan", r"\bValidateEventSequence\("),
             note="replay in topological order; check every move before CHUGG sees it"),
        dict(depth=3, kind="sched", sig="stdx::Result Scheduler::ValidateMoveDestinationAndPath(PlanContextSPtr ctx, "
             "const DiscreteGarageState& working_state, const CandidateMove& move) const",
             loc=L("ValidateMoveDestinationAndPath"),
             call=C("ValidateEventSequence", r"\bValidateMoveDestinationAndPath\(")),
        dict(depth=2, kind="sched", sig="std::optional<ContinuousState> Scheduler::PlanMotions(PlanContextSPtr ctx) "
             "const", loc=L("PlanMotions"), call=C("Scheduler::Plan", r"\bPlanMotions\("),
             note="motion planning (Motion planning tab)"),
        dict(depth=3, kind="ext", sig="ComputeEdgeDurations(motion_graph_, cost_model_); "
             "ComputeAllPairsShortestPathCosts(motion_graph_, edge_durations, ...)",
             loc=LX("ComputeEdgeDurations", "motion_planner"),
             call=C("PlanMotions", r"\bComputeEdgeDurations\(|\bComputeAllPairsShortestPathCosts\(")),
        dict(depth=3, kind="ext", sig="Chugg motion_planner(motion_graph_, collision_table_, ctx->event_dag, ...); "
             "motion_planner.SolveSequential(audit_ptr)", loc=LX("Chugg::SolveSequential", "motion_planner"),
             call=C("PlanMotions", r"Chugg motion_planner\(|SolveSequential\("),
             note="CHUGG: timed trajectories for every entity"),
        dict(depth=2, kind="sched", sig="stdx::Expected<std::vector<interfaces::msg::ActionNode>> "
             "Scheduler::BuildActionGraph(PlanContextSPtr ctx, const ContinuousState& final_state) const",
             loc=L("BuildActionGraph"), call=C("Scheduler::Plan", r"\bBuildActionGraph\("),
             note="the action DAG (Action graph tab); every step's failure is logged and returned"),
        dict(depth=3, kind="free", sig="stdx::Result CollectAndCollapseTrajectoryMotions(const ContinuousState& "
             "final_state, const Layout& layout, std::set<Motion, MotionScheduleOrder>& all_motions)",
             loc=L("CollectAndCollapseTrajectoryMotions"),
             call=C("BuildActionGraph", r"\bCollectAndCollapseTrajectoryMotions\(")),
        dict(depth=3, kind="free", sig="stdx::Result BuildActionDagFromMotions(all_motions, ctx, final_actions_dag, "
             "occupancy_history, action_span_by_event)", loc=L("BuildActionDagFromMotions"),
             call=C("BuildActionGraph", r"\bBuildActionDagFromMotions\(")),
        dict(depth=4, kind="free", sig="stdx::Expected<interfaces::msg::ActionNode> ToActionNode(const Motion& "
             "motion, interfaces::msg::Guid job_id, const ScheduleEvent& event)", loc=L("ToActionNode"),
             call=C("BuildActionDagFromMotions", r"\bToActionNode\("),
             note="job_id = ctx->scheduled_jobs[event->GetJobIndex()].job.guid"),
        dict(depth=3, kind="ext", sig="final_actions_dag.RemoveRedundantEdges()   after each of the next steps",
             loc=F(DAGH, r"RemoveRedundantEdges\(", "planner_core"),
             call=C("BuildActionGraph", r"RemoveRedundantEdges\(")),
        dict(depth=3, kind="free", sig="stdx::Result TransferEventDagDepsToActionDag(PlanContextSPtr ctx, const "
             "ActionSpanByEvent& action_span_by_event, Dag<interfaces::msg::ActionNode>& final_actions_dag)",
             loc=L("TransferEventDagDepsToActionDag"),
             call=C("BuildActionGraph", r"\bTransferEventDagDepsToActionDag\(")),
        dict(depth=3, kind="free", sig="stdx::Result InsertVrcActionsIntoDag(Dag<interfaces::msg::ActionNode>& "
             "actions_dag, const Layout& layout, const DiscreteGarageState& initial_state, const "
             "cost::MotionCostModel& cost_model)", loc=L("InsertVrcActionsIntoDag"),
             call=C("BuildActionGraph", r"\bInsertVrcActionsIntoDag\(")),
        dict(depth=3, kind="free", sig="std::vector<interfaces::msg::ActionNode> BuildScheduledActionsArray(const "
             "Dag<interfaces::msg::ActionNode>& final_actions_dag, const std::vector<...::Vertex>& final_ordering)",
             loc=L("BuildScheduledActionsArray"), call=C("BuildActionGraph", r"\bBuildScheduledActionsArray\("),
             note="topological order + parents -> Schedule.nodes, as local copies"),
        dict(depth=3, kind="free", sig="void WriteJobActionIndices(PlanContextSPtr ctx, const "
             "std::vector<interfaces::msg::ActionNode>& scheduled_actions)", loc=L("WriteJobActionIndices"),
             call=C("BuildActionGraph", r"\bWriteJobActionIndices\("), note="each job's node_indices"),
        dict(depth=2, kind="sched", sig="for(auto& scheduled_job : ctx->scheduled_jobs) { state = "
             "STATE_EXECUTING; FindPayloadDeliveryAction(...) for a retrieve; } return response;",
             loc=C("Scheduler::Plan", r"for\(auto& scheduled_job : ctx->scheduled_jobs\)"),
             note="successful jobs appended to response.scheduled_jobs in request order, after any failed ones"),
        dict(depth=1, kind="ros", sig="job_data.job.time_planned = now; response->response_data = "
             "std::move(response_msg);",
             loc=C("SchedulerRos::SchedulerRos", r"time_planned = now|response->response_data ="),
             note="back in the service callback"),
    ]


def _part2():
    TA, AA = "AssignTrays", "AssignAgvs"
    return [
        {"section": "Tray assignment"},
        dict(depth=0, kind="sched", sig="[[nodiscard]] stdx::Result Scheduler::AssignTrays(PlanContextSPtr ctx) "
             "const", loc=L(TA), call=C("Scheduler::Plan", r"\bAssignTrays\(")),
        dict(depth=1, kind="free", sig="TrayAssignmentState state {.working_state = ctx->initial_state, "
             ".occupancy_history = {collision_table_, motion_graph_}}",
             loc=F("src/tray_assignment.cpp", r"^struct TrayAssignmentState"),
             note="working_state, last_event_by_tray, occupancy_history (GarageOccupancyChecker of events)"),
        dict(depth=1, kind="ext", sig="ctx->event_dag.GetEventsInTopologicalOrder()",
             loc=LX("ScheduleEventDag::GetEventsInTopologicalOrder", "planner_core"),
             call=C(TA, r"GetEventsInTopologicalOrder\(")),
        dict(depth=1, loop="for each event in topological order"),
        dict(depth=2, kind="sched", sig="stdx::Result Scheduler::ApplyBayOrChargerTransition(TrayAssignmentState& "
             "state, const std::shared_ptr<ScheduleEvent>& event) const", loc=L("ApplyBayOrChargerTransition"),
             call=C(TA, r"\bApplyBayOrChargerTransition\("), note="bay / VECS transitions -> occupancy_history"),
        dict(depth=2, kind="sched", sig="stdx::Result Scheduler::AssignEmptyTrayToMove(TrayMove& move, const "
             "DiscreteGarageState& working_state) const", loc=L("AssignEmptyTrayToMove"),
             call=C(TA, r"\bAssignEmptyTrayToMove\("),
             note="'? -> dest': nearest empty tray (BuildImmobileTrayFilter + SingleSourceSearch)"),
        dict(depth=2, kind="sched", sig="stdx::Result Scheduler::AssignDestinationAndUnblockingMoves("
             "PlanContextSPtr ctx, TrayAssignmentState& state, const std::shared_ptr<ScheduleEvent>& event) const",
             loc=L("AssignDestinationAndUnblockingMoves"), call=C(TA, r"\bAssignDestinationAndUnblockingMoves\("),
             note="'tray -> ?': find a parking spot"),
        dict(depth=3, kind="sched", sig="TrayDestinationPlan Scheduler::ResolveBlockingTrays(const "
             "DiscreteGarageState& base_state, const ResolveRequest& request, size_t job_index) const",
             loc=L("ResolveBlockingTrays"), call=C("AssignDestinationAndUnblockingMoves", r"\bResolveBlockingTrays\("),
             note="returns TrayDestinationPlan {dest, required_moves (PlannedTrayMove)}"),
        dict(depth=4, kind="sched", sig="std::optional<OpenSpaceSearchResult> Scheduler::FindDestinationForRootTray("
             "const DiscreteGarageState& working_state, const ResolveRequest& request, CollisionEntityId_t "
             "collision_entity) const", loc=L("FindDestinationForRootTray"),
             call=C("ResolveBlockingTrays", r"\bFindDestinationForRootTray\("),
             note="tier 1 parking, tier 2 waypoint stash"),
        dict(depth=4, kind="sched", sig="std::optional<BlockingTrayResolution> Scheduler::FindBlockingTrayResolution("
             "const DiscreteGarageState& working_state, const ResolveRequest& root_request, uint16_t "
             "blocking_tray_id, ...) const", loc=L("FindBlockingTrayResolution"),
             call=C("ResolveBlockingTrays", r"\bFindBlockingTrayResolution\("),
             note="may call ResolveBlockingTrays again (recursion, "
                  + C("FindBlockingTrayResolution", r"\bResolveBlockingTrays\(", file=False) + ")"),
        dict(depth=3, kind="sched", sig="std::optional<int16_t> Scheduler::FindPreferredTrayHeadingForRetrieval("
             "uint32_t node_id, ...) const", loc=L("FindPreferredTrayHeadingForRetrieval"),
             call=C("AssignDestinationAndUnblockingMoves", r"\bFindPreferredTrayHeadingForRetrieval\(")),
        dict(depth=2, kind="sched", sig="BuildImmobileTrayFilter(...); ResolveDestinationHeading(path_filter, "
             "tray_id, dest)", loc=L("BuildImmobileTrayFilter") + ", :" + str(snapshot.fn("ResolveDestinationHeading").line),
             call=C(TA, r"\bBuildImmobileTrayFilter\(|\bResolveDestinationHeading\("),
             note="'tray -> dest': a destination usable only reversed goes to the reverse pose"),
        dict(depth=2, kind="ext", sig="SingleSourceSearch(start_state, ..., BlockingTraySearchEnvironment)",
             loc="motion_planner (path_search.hpp)", call=C(TA, r"\bSingleSourceSearch\("),
             note="critical path of the root tray and the trays blocking it"),
        dict(depth=2, kind="sched", sig="ResolveBlockingTrays(state.working_state, {.tray_id = blocking_tray_id, "
             "...}, move->GetJobIndex()) const   per blocking tray", loc=L("ResolveBlockingTrays"),
             call=C(TA, r"\bResolveBlockingTrays\("),
             note="fallbacks: advance the root tray, then allow parking on the critical path"),
        dict(depth=2, kind="ext", sig="advance_move / unblock_move / event ->ApplyTo(state.working_state)",
             loc=LX("TrayMove::ApplyTo", "planner_core"), call=C(TA, r"ApplyTo\("),
             note="each planned move applied once; one that cannot apply fails the stage"),
        dict(depth=2, kind="sched", sig="ChainTrayEvent(*ctx, state, tray_id, event); "
             "OrderAfterPriorOccupants(*ctx, state, pose, collision_id, event)",
             loc=L("ChainTrayEvent") + ", :" + str(snapshot.fn("OrderAfterPriorOccupants").line),
             call=C(TA, r"\bChainTrayEvent\(|\bOrderAfterPriorOccupants\("),
             note="per-tray chain (first_event_by_tray) and occupancy edges from occupancy_history"),
        {"section": "AGV assignment"},
        dict(depth=0, kind="sched", sig="[[nodiscard]] stdx::Result Scheduler::AssignAgvs(PlanContextSPtr ctx) const",
             loc=L(AA), call=C("Scheduler::Plan", r"\bAssignAgvs\(")),
        dict(depth=1, kind="free", sig="AgvAssignmentState state {.working_state = ctx->initial_state}",
             loc=F("src/agv_assignment.cpp", r"^struct AgvAssignmentState"),
             note="busy_duration_by_agv starts at zero for every enabled AGV (TODO); pending_events = copy of "
                  "ctx->event_dag"),
        dict(depth=1, loop="while(!pending_events.GetRootEvents().empty())   drain non-tray roots, then match"),
        dict(depth=2, kind="sched", sig="stdx::Result Scheduler::ApplyNonTrayRootEvents(PlanContextSPtr ctx, "
             "AgvAssignmentState& state, ScheduleEventDag& pending_events) const",
             loc=L("ApplyNonTrayRootEvents"), call=C(AA, r"\bApplyNonTrayRootEvents\(")),
        dict(depth=3, kind="sched", sig="stdx::Result Scheduler::OrderArrivalAfterPriorOccupant(PlanContextSPtr ctx, "
             "AgvAssignmentState& state, uint32_t dest_node_id, uint16_t arriving_agv_id, ...) const",
             loc=L("OrderArrivalAfterPriorOccupant"),
             call=C("ApplyNonTrayRootEvents", r"\bOrderArrivalAfterPriorOccupant\(")),
        dict(depth=2, kind="sched", sig="AgvAssignmentEdgeCosts Scheduler::ComputeAgvAssignmentEdgeCosts(const "
             "AgvAssignmentState& state, const std::vector<ScheduleEventSPtr>& root_events, ...) const",
             loc=L("ComputeAgvAssignmentEdgeCosts"), call=C(AA, r"\bComputeAgvAssignmentEdgeCosts\("),
             note="one cost per (AGV, root tray move)"),
        dict(depth=3, kind="sched", sig="std::optional<Interval::Duration> Scheduler::ComputeAgvAssignmentCost("
             "uint16_t agv_id, const TrayMove& move, const DiscreteGarageState& working_state, ...) const",
             loc=L("ComputeAgvAssignmentCost"),
             call=C("ComputeAgvAssignmentEdgeCosts", r"\bComputeAgvAssignmentCost\(")),
        dict(depth=4, kind="sched", sig="std::optional<Interval::Duration> Scheduler::ComputeAgvPickupDuration("
             "uint16_t agv_id, const TrayMove& move, ...) const", loc=L("ComputeAgvPickupDuration"),
             call=C("ComputeAgvAssignmentCost", r"\bComputeAgvPickupDuration\(")),
        dict(depth=5, kind="sched", sig="std::optional<Interval::Duration> Scheduler::ComputeTravelDuration(const "
             "interfaces::msg::GaragePose& start_pose, const interfaces::msg::GaragePose& end_pose, ...) const",
             loc=L("ComputeTravelDuration"), call=C("ComputeAgvPickupDuration", r"\bComputeTravelDuration\("),
             note="FindPosePath + cost model"),
        dict(depth=2, kind="ext", sig="BottleneckAssignment(edge_costs, available_agv_ids, root_events, ...)",
             loc="task_planner", call=C(AA, r"\bBottleneckAssignment\("), note="minimise the largest assigned cost"),
        dict(depth=2, kind="sched", sig="Dag<uint16_t> Scheduler::BuildAgvOrderDag(const std::unordered_map<uint16_t, "
             "std::optional<ScheduleEventSPtr>>& root_event_by_agv, const DiscreteGarageState& working_state) const",
             loc=L("BuildAgvOrderDag"), call=C(AA, r"\bBuildAgvOrderDag\("),
             note="order of the matched AGVs; a cycle fails the stage"),
        dict(depth=3, kind="sched", sig="std::vector<uint16_t> Scheduler::FindAssignedAgvsBlockingPickup(const ...& "
             "root_event_by_agv, const DiscreteGarageState& working_state, const uint16_t agv_id) const",
             loc=L("FindAssignedAgvsBlockingPickup"),
             call=C("BuildAgvOrderDag", r"\bFindAssignedAgvsBlockingPickup\("),
             note="collision_table_.Query: AGV vs AGV"),
        dict(depth=2, loop="for each matched (AGV, tray move), in that order"),
        dict(depth=3, kind="sched", sig="stdx::Expected<Interval::Duration> Scheduler::AssignAgvToTrayMove("
             "PlanContextSPtr ctx, AgvAssignmentState& state, uint16_t agv_id, const "
             "std::shared_ptr<ScheduleEvent>& root_event, const Dag<uint16_t>& agv_order_dag) const",
             loc=L("AssignAgvToTrayMove"), call=C(AA, r"\bAssignAgvToTrayMove\(")),
        dict(depth=4, kind="sched", sig="stdx::Expected<Interval::Duration> Scheduler::ScheduleAgvMoveToPickup("
             "PlanContextSPtr ctx, AgvAssignmentState& state, uint16_t agv_id, ...) const",
             loc=L("ScheduleAgvMoveToPickup"), call=C("AssignAgvToTrayMove", r"\bScheduleAgvMoveToPickup\("),
             note="AgvMove to the tray; OrderArrivalAfterPriorOccupant "
                  + C("ScheduleAgvMoveToPickup", r"\bOrderArrivalAfterPriorOccupant\(", file=False)
                  + ", OrderAfterTraysOnPath "
                  + C("ScheduleAgvMoveToPickup", r"\bOrderAfterTraysOnPath\(", file=False)),
        dict(depth=4, kind="sched", sig="stdx::Expected<Interval::Duration> Scheduler::ScheduleAgvLiftChange("
             "PlanContextSPtr ctx, AgvAssignmentState& state, uint16_t agv_id, bool is_raising, size_t job_index) "
             "const   x2", loc=L("ScheduleAgvLiftChange"),
             call=lines("AssignAgvToTrayMove", r"\bScheduleAgvLiftChange\(", ["lift", "lower"])),
        dict(depth=4, kind="free", sig="ChainAgvEvent(*ctx, state, agv_id, root_event)", loc=L("ChainAgvEvent"),
             call=C("AssignAgvToTrayMove", r"\bChainAgvEvent\("),
             note="the tray move itself is now this AGV's (state.last_event_by_agv)"),
        dict(depth=3, kind="sched", sig="void Scheduler::PropagateEarliestStartToChildren(const "
             "std::shared_ptr<ScheduleEvent>& root_event, Interval::Duration event_duration, ...) const",
             loc=L("PropagateEarliestStartToChildren"), call=C(AA, r"\bPropagateEarliestStartToChildren\("),
             note="-> state.earliest_start_by_event"),
        dict(depth=1, kind="sched", sig="stdx::Result Scheduler::OrderAgvMovesAfterBlockingAgvs(PlanContextSPtr ctx) "
             "const", loc=L("OrderAgvMovesAfterBlockingAgvs"), call=C(AA, r"\bOrderAgvMovesAfterBlockingAgvs\("),
             note="up to kMaxAgvMoveOrderPasses (256) passes"),
        dict(depth=2, kind="sched", sig="stdx::Expected<bool> Scheduler::AddNextMissingAgvMoveOrder(PlanContextSPtr "
             "ctx) const", loc=L("AddNextMissingAgvMoveOrder"),
             call=C("OrderAgvMovesAfterBlockingAgvs", r"\bAddNextMissingAgvMoveOrder\(")),
        dict(depth=3, kind="sched", sig="bool Scheduler::OrderAgvMoveAfterBlockerDeparture(PlanContextSPtr ctx, const "
             "std::vector<ScheduleEventDag::Vertex>& ordering, size_t position, const ScheduleEventSPtr& event, "
             "...) const", loc=L("OrderAgvMoveAfterBlockerDeparture"),
             call=C("AddNextMissingAgvMoveOrder", r"\bOrderAgvMoveAfterBlockerDeparture\(")),
        dict(depth=4, kind="sched", sig="ScheduleEventSPtr Scheduler::FindAgvDepartureFromNode(PlanContextSPtr ctx, "
             "const std::vector<ScheduleEventDag::Vertex>& ordering, size_t after_position, uint16_t agv_id, "
             "uint32_t node) const", loc=L("FindAgvDepartureFromNode"),
             call=C("OrderAgvMoveAfterBlockerDeparture", r"\bFindAgvDepartureFromNode\(")),
        dict(depth=1, kind="ext", sig="ctx->event_dag.RemoveRedundantEdges()",
             loc=F(DAGH, r"RemoveRedundantEdges\(", "planner_core"), call=C(AA, r"RemoveRedundantEdges\(")),
        dict(depth=1, kind="sched", sig="stdx::Result Scheduler::OrderAllTransitionsAroundAgvLifts(PlanContextSPtr "
             "ctx) const", loc=L("OrderAllTransitionsAroundAgvLifts"),
             call=C(AA, r"\bOrderAllTransitionsAroundAgvLifts\(")),
        dict(depth=2, kind="sched", sig="stdx::Result Scheduler::OrderTransitionAroundAgvLifts(PlanContextSPtr ctx, "
             "std::shared_ptr<ScheduleEvent> event, uint16_t node_id) const",
             loc=L("OrderTransitionAroundAgvLifts"),
             call=C("OrderAllTransitionsAroundAgvLifts", r"\bOrderTransitionAroundAgvLifts\(")),
    ]


@figure("39_call_trace_plan", "Call trace: start-up and one Plan() call", DOC1)
def call_trace_plan():
    d = Doc("39_call_trace_plan", "Call trace: start-up and one Plan() call",
            "Time runs downwards; every call is indented under the call that made it. Each row gives the "
            "signature, where the function is defined and the line it is called from.")
    _trace(d, _part1())
    frame(d, title="Call trace: start-up and one Plan() call",
          subtitle="Read from top to bottom. Indentation is call depth; the grey line under a call spans the calls "
                   "it makes. File:line numbers are those of main at a468657f (sources/repomix-*.xml).",
          badge_key="as-built", legend=_legend(),
          footnote="Only the calls that matter for understanding are shown: logging, getters and message "
                   "conversions are left out. Failure branches (each returns an error that Plan() reports as failed jobs; see 'One Plan() call') are not drawn.")
    return d


@figure("39_call_trace_assignment", "Call trace: tray and AGV assignment", DOC1)
def call_trace_assignment():
    d = Doc("39_call_trace_assignment", "Call trace: inside tray and AGV assignment",
            "The two calls collapsed in the previous figure, expanded the same way.")
    _trace(d, _part2())
    frame(d, title="Call trace: inside tray and AGV assignment",
          subtitle="Continuation of the previous figure: AssignTrays() and AssignAgvs(), with the "
                   "helpers they call in the order they first call them.",
          badge_key="as-built", legend=_legend(),
          footnote="Loops are shown once (amber 'loop:' rows). Inside a loop the listed calls repeat per event or per matched AGV; "
                   "some only on certain branches.")
    return d
