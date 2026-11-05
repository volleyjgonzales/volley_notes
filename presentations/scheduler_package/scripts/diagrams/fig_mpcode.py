"""Motion planning code structure: 100 CHUGG classes, 101 search classes, 102 timeline data model,
103 one PlanMotions call (animated sequence), 104 Trajectory storage (animated)."""
from __future__ import annotations

from components import connect, frame, label_pill, note, uml_class
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

DOC3 = "04-motion-planning.html"
M = 12          # member font size
EXT = T.muted   # classes from other packages
CBS = T.faint   # CBS-only members (present, never called)


def _pkg(d: Doc, bb: BBox, label: str, color, *, pad=18, top=30):
    """Package frame drawn under a group of classes."""
    x0, y0, x1, y1 = bb.x0 - pad, bb.y0 - top, bb.x1 + pad, bb.y1 + pad
    d.rect(x0, y0, x1 - x0, y1 - y0, rx=12, fill="none", stroke=T.tint(color, 0.55, T.bg), sw=1.2, dash="7 5",
           layer="under")
    tw = text_width(label, 11.5, "mono", 600) + 18
    d.rect(x0 + 14, y0 - 11, tw, 22, rx=6, fill=T.bg, stroke=T.tint(color, 0.55, T.bg), sw=1.2, layer="under")
    d.text(x0 + 23, y0, label, size=11.5, family="mono", weight=600, fill=color)
    return BBox(x0, y0, x1, y1)


def _union(*bs):
    return BBox(min(b.x0 for b in bs), min(b.y0 for b in bs), max(b.x1 for b in bs), max(b.y1 for b in bs))


# --------------------------------------------------------------------------------------
# 100 — CHUGG and its collaborators
# --------------------------------------------------------------------------------------
@figure("100_uml_chugg_classes", "CHUGG and its collaborators (UML)", DOC3)
def uml_chugg_classes():
    d = Doc("100_uml_chugg_classes", "CHUGG and its collaborators",
            "UML class diagram of Chugg, Chugg::Node, SippAgv and ContinuousState, the inputs Chugg holds by "
            "const reference, and the scheduler method that creates it.")
    SCH, CH, SIP, DAT = T.sky, T.amber, T.green, T.violet
    hl = {"__dim__": ("(CBS)",)}

    sched = uml_class(d, 0, 0, "Scheduler", accent=SCH, stereo="scheduler · abridged", size=M,
                      attrs=["- gg_: GarageGraph", "- table_: CollisionTable", "- cost_model_: MotionCostModel",
                             "- layout_: shared_ptr<Layout>"],
                      methods=["+ PlanMotions(ctx) const", "    : optional<ContinuousState>",
                               "+ ResponseFromTrajectories(ctx, state)", "    : pair<optional<vector<ActionNodeMsg>>,",
                               "      string>"])

    R1 = sched.y1 + 150
    cs = uml_class(d, 0, R1, "ContinuousState", accent=DAT, stereo="motion_planner · continuous_state.hpp",
                   size=M,
                   attrs=["- trajectories_: TrajectoryMap", "    = unordered_map<GarageEntityIdMsg,",
                          "                    Trajectory>",
                          "- initial_state_: DiscreteGarageState", "- table_: const CollisionTable&"],
                   methods=["+ ContinuousState(state, table, layout, now)", "+ GetTrajectories(): const TrajectoryMap&",
                            "+ GetEndState(): optional<DiscreteGarageState>",
                            "+ CheckCollisions(map, table)  static", "+ CheckMotionCollision(a, b, table)  static"])
    chugg = uml_class(d, cs.x1 + 130, R1, "Chugg", accent=CH, stereo="motion_planner · chugg.hpp", size=M,
                      highlight=hl,
                      attrs=["- graph_: const GarageGraph&",
                             "- geometry_: const CollisionTable&",
                             "- event_dag_: const ScheduleEventDag&",
                             "- init_traj_: const ContinuousState&",
                             "- edge_costs_: const EdgeCosts&",
                             "- heuristics_: const HeuristicMap&",
                             "- cost_model_: const MotionCostModel&",
                             "- audit_: cost::CostVector*",
                             "- event_order_: vector<Vertex>",
                             "- constraints_: GraphConstraints",
                             "- planning_start_: Timepoint",
                             "- dynamic_entities_: unordered_set<GarageEntityIdMsg>",
                             "- next_node_id_, n_nodes_pushed_: size_t  (CBS)"],
                      methods=["+ Chugg(graph, geometry, event_dag, initial_trajectories,",
                               "        edge_costs, heuristics, cost_model, logger)",
                               "+ SolveSequential(audit = nullptr): optional<ContinuousState>",
                               "+ SolveCbs(): optional<ContinuousState>  (CBS)",
                               "  // setup",
                               "- InitializeEventOrder()",
                               "- SolveInitialization()",
                               "- MakeRootNode(): Node",
                               "  // the loop",
                               "- PlanNodeSequential(node): bool",
                               "- PlanEventSequential(node, id, event, state): bool  x5",
                               "- SetEventSafeIntervals(node, state, agv, tray)",
                               "    : SafeIntervalTable",
                               "- GetDependencyCompletionTime(node, id): Timepoint",
                               "- EntityCurrentTime(node, entity): Timepoint",
                               "- DeconflictAgvs(node, motion)",
                               "  // finish",
                               "- GetUpdatedContinuousState(node): ContinuousState",
                               "  // CBS only",
                               "- ResolveCollisions(parent, collisions)  (CBS)",
                               "- ResolveAgvAgvCollision(parent, pair)  (CBS)",
                               "- BranchNode(parent): Node  (CBS)"])
    node = uml_class(d, chugg.x1 + 170, R1, "Chugg::Node", accent=CH, stereo="private struct", size=M,
                     attrs=["+ trajectories: TrajectoryMap", "    // new motions only, per dynamic entity",
                            "+ planners: unordered_map<int, SippAgv>", "    // one per movable AGV",
                            "+ makespan: Timepoint", "+ flowtime: Duration", "+ node_id: size_t"],
                     methods=["+ Node(parent, node_id)", "    // copies planners, empty trajectories"])
    agv = uml_class(d, node.x0, node.y1 + 100, "SippAgv", accent=SIP, stereo="motion_planner · sipp_agv.hpp",
                    size=M, highlight=hl,
                    attrs=["- graph_, geometry_, edge_costs_,", "  heuristics_: const refs",
                           "- initial_state_: const DiscreteAgvStateMsg",
                           "- initial_time_: const Timepoint",
                           "- wheel_turn_time_: const Duration",
                           "- motion_params_: const MotionCostParams",
                           "- sit_: SafeIntervalTable",
                           "- all_goals_: vector<pair<SippGoal, size_t>>",
                           "- all_events_: unordered_map<size_t,",
                           "    shared_ptr<const ScheduleEvent>>",
                           "- all_collision_ids_: set<CollisionEntityId_t>"],
                    methods=["+ AddEventGoal(AgvMove, id, collision_id)",
                             "+ AddEventGoal(TrayMove, id, collision_id, recip)",
                             "+ PlanEvents(ids, state, time, constraints)",
                             "    : optional<Trajectory>",
                             "+ AddDeconflictConstraints(motion)",
                             "+ GetSafeIntervalTable(): const SafeIntervalTable&",
                             "+ SetSafeIntervalTable(SafeIntervalTable&&)",
                             "+ PlanTrajectory(constraints)  (CBS)",
                             "+ AddLandmarkGoal(motion)  (CBS)",
                             "+ AddAvoidConstraint(motion)  (CBS)",
                             "- SolutionToTrajectory(solution, events, goals)",
                             "- AddLocationConstraint(type, location, interval)"])
    gfp = uml_class(d, chugg.x0 + 30, max(chugg.y1, agv.y1) + 70, "GraphFilterProperties", accent=SIP,
                    stereo="motion_planner · static_graph_filtering.hpp", size=M,
                    attrs=["- vertex_filter_: VertexVectorPropertyMap<bool>",
                           "- edge_filter_: EdgeVectorPropertyMap<bool>"],
                    methods=["+ IsEnabled(vertex | edge): bool"])
    pkg = _pkg(d, _union(cs, chugg, node, agv, gfp), "package motion_planner", CH, pad=24, top=36)

    # external inputs (other packages), one row under the package
    ext_y = pkg.y1 + 110
    ext = []
    x = 0
    for name, st, mem in (("GarageGraph", "common_ros", ["vertices = poses, edges = moves"]),
                          ("CollisionTable", "common_ros", ["Query(id, my_id, location)", "  : (PoseSet, EdgeSet)"]),
                          ("ScheduleEventDag", "planner_core", ["GetTopologicalOrdering()", "GetInEdges(v)"]),
                          ("MotionCostModel", "cost_functions", ["Params(): speeds, accels,", "  lift and door times"])):
        b = uml_class(d, x, ext_y, name, accent=EXT, stereo=st, size=M, methods=mem)
        ext.append(b)
        x = b.x1 + 40
    ec = uml_class(d, x + 10, ext_y, "EdgeCosts, HeuristicMap", accent=EXT, stereo="type aliases · built per call",
                   size=M, attrs=["EdgeCosts = EdgeVectorPropertyMap<Duration>",
                                  "  // GetEdgeDurations(gg, cost_model)",
                                  "HeuristicMap = vector<vector<Duration>>",
                                  "  // GetAllPairsMinCost: Floyd-Warshall"])

    # ---- relations ----
    note(d, sched.x1 + 60, sched.y0, 420,
         "PlanMotions builds the ContinuousState, EdgeCosts and HeuristicMap as locals, constructs Chugg on the "
         "stack and calls SolveSequential once. Chugg keeps references to all of them, so it must not outlive "
         "that call.", title="Lifetime")
    yS = sched.y0 + 40
    connect(d, [(sched.x1, sched.y1 - 30), (chugg.cx, sched.y1 - 30), (chugg.cx, chugg.y0)], kind="dep", color=SCH,
            label="«create», then SolveSequential()", label_at=(chugg.cx, (sched.y1 + chugg.y0) / 2 - 10))
    connect(d, [(sched.cx, sched.y1), (sched.cx, cs.y0)], kind="dep", color=SCH, label="«create» initial state",
            label_at=(sched.cx, (sched.y1 + cs.y0) / 2))
    # Chugg -> ContinuousState
    connect(d, [(chugg.x0, cs.y0 + 50), (cs.x1, cs.y0 + 50)], kind="assoc", color=DAT, label="init_traj_",
            label_at=((chugg.x0 + cs.x1) / 2, cs.y0 + 36))
    connect(d, [(chugg.x0, cs.y0 + 120), (cs.x1, cs.y0 + 120)], kind="dep", color=DAT, label="«return»",
            label_at=((chugg.x0 + cs.x1) / 2, cs.y0 + 106))
    d.text((chugg.x0 + cs.x1) / 2, cs.y0 + 142, "copy + new motions", size=S.tiny, fill=T.muted, anchor="middle")
    # Chugg -> Node
    yN = node.y0 + 60
    connect(d, [(chugg.x1, yN), (node.x0, yN)], kind="dep", color=CH, label="«create» MakeRootNode",
            label_at=((chugg.x1 + node.x0) / 2, yN - 14))
    connect(d, [(chugg.x1, yN + 50), (node.x0, yN + 50)], kind="dep", color=CH, label="plans into (Node&)",
            label_at=((chugg.x1 + node.x0) / 2, yN + 36))
    connect(d, [(chugg.x1, agv.y0 + 120), (agv.x0, agv.y0 + 120)], kind="dep", color=CH,
            label="DeconflictAgvs", label_at=((chugg.x1 + agv.x0) / 2, agv.y0 + 106))
    connect(d, [(chugg.x1, agv.y0 + 170), (agv.x0, agv.y0 + 170)], kind="dep", color=CH,
            label="PlanEvents", label_at=((chugg.x1 + agv.x0) / 2, agv.y0 + 156))
    connect(d, [(node.cx, node.y1), (node.cx, agv.y0)], kind="comp", color=CH, mult_end="1 per movable AGV",
            label="planners", label_at=(node.cx - 60, (node.y1 + agv.y0) / 2))
    connect(d, [(gfp.x0 + 40, chugg.y1), (gfp.x0 + 40, gfp.y0)], kind="comp", color=CH,
            mult_end="1 per footprint type", label="constraints_", label_at=(gfp.x0 - 6, (chugg.y1 + gfp.y0) / 2))
    connect(d, [(agv.cx, agv.y1), (agv.cx, gfp.cy), (gfp.x1, gfp.cy)], kind="dep", color=SIP,
            label="reads (PlanEvents argument)", label_at=((agv.cx + gfp.x1) / 2, gfp.cy - 14))
    # Chugg -> external inputs: one bus in the gap left of Chugg
    bus_y = ext_y - 40
    bx = chugg.x0 - 40
    xs = [b.cx for b in ext] + [ec.cx]
    d.line(min(xs), bus_y, max(xs), bus_y, stroke=EXT, sw=1.4, layer="edges")
    connect(d, [(chugg.x0, chugg.y1 - 40), (bx, chugg.y1 - 40), (bx, bus_y)], kind="line", color=EXT)
    for xx in xs:
        connect(d, [(xx, bus_y), (xx, ext_y)], kind="assoc", color=EXT)
    label_pill(d, (min(xs) + bx) / 2, bus_y, "const & held by Chugg, every SippAgv and every SippEnvironment",
               color=EXT)
    frame(d, title="CHUGG and its collaborators",
          subtitle="Chugg holds every input by const reference and builds one Node per call: the new motions per entity "
                   "and one SippAgv per movable AGV. SippAgv owns that AGV's safe-interval table and its SIPP goals. "
                   "Grey members exist for the unfinished CBS solver and are not reached from SolveSequential.",
          badge_key="as-built",
          legend=[("box", SCH, "scheduler package"), ("box", CH, "CHUGG (motion_planner)"),
                  ("box", SIP, "per-AGV search state"), ("box", DAT, "timeline data"),
                  ("box", EXT, "other packages"), ("comp", CH, "composition (owns)"),
                  ("assoc", T.fg2, "association (holds a reference)"), ("dep", T.fg2, "dependency (creates, calls)")],
          footnote="Abridged from chugg.hpp, sipp_agv.hpp, continuous_state.hpp and static_graph_filtering.hpp. "
                   "PlanEventSequential has one overload each for AgvMove, TrayMove, BayTransition, VecsTransition "
                   "and VrcTransition; PlanNodeSequential never calls the VrcTransition one.")
    return d


# --------------------------------------------------------------------------------------
# 101 — the search classes: SIPP on top of a generic A*
# --------------------------------------------------------------------------------------
@figure("101_uml_sipp_classes", "SIPP and the generic A* search (UML)", DOC3)
def uml_sipp_classes():
    d = Doc("101_uml_sipp_classes", "SIPP and the generic A* search",
            "UML class diagram: SippAgv builds a SippEnvironment per call and runs the SingleSourceSearch template on "
            "it; SippEnvironment implements the abstract SearchEnvironment for SippState; the safe-interval table "
            "stores an IntervalSet per footprint and location.")
    SIP, GEN, DAT, CH = T.green, T.teal, T.violet, T.amber
    agv = uml_class(d, 0, 0, "SippAgv", accent=SIP, stereo="sipp_agv.hpp · abridged", size=M,
                    attrs=["- sit_: SafeIntervalTable", "- all_goals_: vector<pair<SippGoal, size_t>>"],
                    methods=["+ PlanEvents(ids, state, time, constraints)", "    : optional<Trajectory>",
                             "- SolutionToTrajectory(solution, events, goals)", "    : Trajectory"])
    base = uml_class(d, agv.x1 + 150, 0, "SearchEnvironment<State, Cost>", accent=GEN, abstract=True,
                     stereo="abstract · path_search.hpp", size=M,
                     methods=["+ OnExpansion(state, g, meta): bool = 0", "    // true = stop: goal reached",
                              "+ GetNeighbors(state)", "    : vector<pair<State, Cost>> = 0",
                              "+ GetHeuristic(state): Cost = 0",
                              "+ OnDiscovery(state, g)  virtual, no-op",
                              "+ OnUpdate(state, old_g, new_g)  virtual, no-op",
                              "+ OnTermination()  virtual, no-op"])
    search = uml_class(d, base.x1 + 120, 0, "SingleSourceSearch<State, Cost, Env, Hash>", accent=GEN,
                       stereo="function template · path_search.hpp", size=M,
                       methods=["(source: State, init_cost: Cost, env: Env&)", "    : SearchSolution<State, Cost, Hash>",
                                "  // A*: boost::heap::fibonacci_heap open set,",
                                "  // predecessor map doubles as closed set,",
                                "  // stops after kMaxExpansions = 5,000,000"])
    sol = uml_class(d, search.x1 + 90, 0, "SearchSolution<State, Cost, Hash>", accent=GEN,
                    stereo="path_search.hpp", size=M,
                    attrs=["- source_: State",
                           "- predecessors_: unordered_map<State,", "    tuple<State, Cost, bool>>",
                           "- meta_data_: SearchMetaData", "- target_: optional<State>"],
                    methods=["+ GetPath(goal): optional<vector<pair<State, Cost>>>",
                             "+ GetTarget(): const optional<State>&", "+ GetMetaData()"])
    ry = max(agv.y1, base.y1) + 110
    env = uml_class(d, base.x0 - 60, ry, "SippEnvironment", accent=SIP,
                    stereo="safe_interval_path_planning.hpp · State = SippState, Cost = Duration", size=M,
                    attrs=["- graph_: const GarageGraph&", "- edge_durations_: const EdgeDurations&",
                           "- goals_: const vector<SippGoal>&", "- safe_intervals_: const SafeIntervalTable&",
                           "- heuristics_: const HeuristicMap&", "- constraints_: const GraphConstraints&",
                           "- wheel_turn_time_: Duration", "- motion_params_: MotionCostParams"],
                    methods=["+ GetNeighbors(parent): Neighbors  override",
                             "+ GetHeuristic(state): Duration  override",
                             "+ OnExpansion(state, g, meta): bool  override",
                             "- GetTraversableEdges(parent, goal_idx)",
                             "    : vector<pair<Edge, Interval>>",
                             "- AddTraversalNeighbors(...)", "- AddWaitForTraversalNeighbors(...)",
                             "- AddWaitForGoalNeighbor(...)", "- StateCompletesGoal(state): bool",
                             "- GoalIsCompletable(state): bool", "- FindSafeInterval(loc, type, start, dur)"])
    gge = uml_class(d, env.x1 + 60, ry, "GarageGraphEnvironment", accent=GEN,
                    stereo="garage_graph_pathing.hpp · State = Vertex", size=M,
                    attrs=["- graph_, cost_model_: const refs", "- target_: optional<Vertex>",
                           "- filters_: optional<GraphFilterProperties>"],
                    methods=["+ OnExpansion / GetNeighbors  override", "+ GetHeuristic(): zero  (Dijkstra)"])
    note(d, gge.x0, gge.y1 + 20, gge.w,
         "Used by GetPosePath and the task-planning searches; the same A* template serves both.",
         title="Second implementation")
    sy = env.y1 + 90
    st = uml_class(d, 0, sy, "SippState", accent=SIP, stereo="search node", size=M,
                   attrs=["- source_: Vertex", "- target_: Vertex   // == source_ when waiting",
                          "- interval_: Interval", "- goal_idx_: size_t", "- num_predecessors_: size_t"],
                   methods=["+ operator==", "  std::hash<SippState> specialised"])
    goal = uml_class(d, st.x1 + 50, sy, "SippGoal", accent=SIP, stereo="one per AgvMove / TrayMove step", size=M,
                     attrs=["- collision_id_: CollisionEntityId_t",
                            "- target_opt_: optional<variant<Vertex, Edge>>",
                            "- wait_duration_opt_: optional<Duration>  // lifts",
                            "- landmark_interval_opt_: optional<Interval>  // CBS"])
    sit = uml_class(d, goal.x1 + 60, sy, "SafeIntervalTable", accent=DAT, stereo="safe_interval_table.hpp", size=M,
                    attrs=["- vertex_intervals_: unordered_map<", "    pair<CollisionEntityId_t, Vertex>, IntervalSet>",
                           "- edge_intervals_: unordered_map<", "    pair<CollisionEntityId_t, Edge>, IntervalSet>",
                           "  // no entry = safe at all times"],
                    methods=["+ AddConstraint(key, interval)   // carve", "+ FindSafeInterval(key, start, duration)",
                             "    : optional<Interval>", "+ IsIntervalConstrained(key, interval): bool",
                             "+ GetAllSafeIntervals(id, location): IntervalSet"])
    iset = uml_class(d, sit.x1 + 60, sy, "IntervalSet", accent=DAT, stereo="interval.hpp", size=M,
                     attrs=["- intervals_: std::set<Interval, IntervalSorter>", "    // ordered by begin"],
                     methods=["+ AddInterval(i): bool  // only if no overlap", "+ MergeInterval(i)",
                              "+ CarveInterval(i)  // cut i out", "+ RemoveOverlappingIntervals(i)"])
    itv = uml_class(d, iset.x0, iset.y1 + 60, "Interval", accent=DAT, stereo="interval.hpp", size=M,
                    attrs=["- begin_, end_: Timepoint  (system_clock)"],
                    methods=["+ Before(o): begin_ < o.begin_", "+ StrictlyBefore(o): end_ <= o.begin_",
                             "+ Overlaps(o), Contains(o)"])
    # ---- relations ----
    # SippAgv creates env and calls search
    connect(d, [(agv.cx, agv.y1), (agv.cx, env.y0 + 60), (env.x0, env.y0 + 60)], kind="dep", color=SIP,
            label="«create» per PlanEvents call", label_at=(agv.cx, (agv.y1 + env.y0) / 2 + 30))
    yq = agv.y0 + 50
    connect(d, [(agv.x1, yq), (base.x0 - 40, yq), (base.x0 - 40, base.y0 - 30), (search.cx, base.y0 - 30),
                (search.cx, search.y0)], kind="dep", color=GEN, label="calls SingleSourceSearch(initial, 0, env)",
            label_at=((base.x0 + search.cx) / 2, base.y0 - 30))
    connect(d, [(search.x1, search.y0 + 60), (sol.x0, search.y0 + 60)], kind="dep", color=GEN, label="«return»",
            label_at=((search.x1 + sol.x0) / 2, search.y0 + 46))
    connect(d, [(search.x0, search.y1 - 30), (base.x1, search.y1 - 30)], kind="dep", color=GEN,
            label="calls back", label_at=((search.x0 + base.x1) / 2, search.y1 - 44))
    connect(d, [(sol.cx, sol.y0), (sol.cx, -80), (agv.cx, -80), (agv.cx, agv.y0)],
            kind="dep", color=SIP, label="read by SolutionToTrajectory (GetPath)", label_at=((sol.cx + base.x1) / 2, -80))
    # realization
    for b in (env, gge):
        connect(d, [(b.cx, b.y0), (b.cx, base.y1 + 40), (base.cx, base.y1 + 40), (base.cx, base.y1)], kind="real",
                color=GEN)
    # env references
    connect(d, [(env.x0 + 40, env.y1), (env.x0 + 40, st.y0 - 30), (st.cx, st.y0 - 30), (st.cx, st.y0)], kind="dep",
            color=SIP, label="State", label_at=((env.x0 + 40 + st.cx) / 2, st.y0 - 30))
    connect(d, [(env.cx - 30, env.y1), (env.cx - 30, goal.y0 - 50), (goal.cx, goal.y0 - 50), (goal.cx, goal.y0)],
            kind="assoc", color=SIP, label="goals_", label_at=(goal.cx, goal.y0 - 24))
    connect(d, [(env.x1 - 40, env.y1), (env.x1 - 40, sit.y0 - 30), (sit.cx, sit.y0 - 30), (sit.cx, sit.y0)],
            kind="assoc", color=DAT, label="safe_intervals_  (SippAgv's sit_)", label_at=(sit.cx, sit.y0 - 14))
    connect(d, [(sit.x1, sit.y0 + 60), (iset.x0, sit.y0 + 60)], kind="comp", color=DAT, mult_end="1 per key")
    connect(d, [(iset.cx, iset.y1), (iset.cx, itv.y0)], kind="comp", color=DAT, mult_end="0..*")
    connect(d, [(st.x1 - 30, st.y1), (st.x1 - 30, itv.cy), (itv.x0, itv.cy)], kind="assoc", color=DAT,
            label="interval_", label_at=((st.x1 + itv.x0) / 2, itv.cy - 14))
    frame(d, title="SIPP and the generic A* search",
          subtitle="SingleSourceSearch is one A* function template; the problem is supplied by a SearchEnvironment. "
                   "For CHUGG, SippAgv builds a SippEnvironment for each PlanEvents call: the state is (move or wait, "
                   "time interval, goal index), and the safe-interval table is where other AGVs' motions are carved in.",
          badge_key="as-built",
          legend=[("box", SIP, "SIPP"), ("box", GEN, "generic search"), ("box", DAT, "time and safety data"),
                  ("real", GEN, "implements"), ("comp", DAT, "composition (owns)"),
                  ("assoc", T.fg2, "holds a reference"), ("dep", T.fg2, "creates, calls, returns")],
          footnote="Abridged from path_search.hpp, safe_interval_path_planning.hpp, safe_interval_table.hpp, "
                   "interval.hpp and garage_graph_pathing.hpp. SippEnvironment's neighbour rules and the search "
                   "cost are described in the SIPP subsection.")
    return d


# --------------------------------------------------------------------------------------
# 102 — the timeline data model
# --------------------------------------------------------------------------------------
@figure("102_uml_timeline_data", "ContinuousState, Trajectory and Motion (UML)", DOC3)
def uml_timeline_data():
    d = Doc("102_uml_timeline_data", "ContinuousState, Trajectory and Motion",
            "UML class diagram of the timeline types CHUGG returns: a ContinuousState maps each entity to a "
            "Trajectory, a Trajectory is a std::set of Motions ordered by start time, and a Motion pairs an "
            "Interval with a location, a footprint, an event id and an optional discrete change.")
    DAT, MSG, SCH = T.violet, T.muted, T.sky
    cs = uml_class(d, 0, 0, "ContinuousState", accent=DAT, stereo="continuous_state.hpp", size=M,
                   attrs=["- trajectories_: TrajectoryMap", "- initial_state_: DiscreteGarageState",
                          "- table_: const CollisionTable&"],
                   methods=["+ SetTrajectory(entity, Trajectory)", "+ GetTrajectories(): const TrajectoryMap&",
                            "+ GetTrajectoryMap(): TrajectoryMap&", "+ GetEndState()",
                            "+ CheckCollisions(): vector<pair<Motion, Motion>>"])
    tr = uml_class(d, cs.x1 + 150, 0, "Trajectory", accent=DAT, stereo="trajectory.hpp", size=M,
                   attrs=["- trajectory_: std::set<Motion>", "    // ordered by Motion::operator<"],
                   methods=["+ AddMotion(m): bool   // false if it overlaps",
                            "+ RemoveMotion(m | iterator): bool",
                            "+ FindInInterval(i): std::set<Motion>",
                            "+ RemoveInInterval(i): std::set<Motion>",
                            "+ GetInterval(): optional<Interval>",
                            "    // first begin .. last end",
                            "+ begin(), end(), rbegin(), rend()"])
    mo = uml_class(d, tr.x1 + 150, 0, "Motion", accent=DAT, stereo="trajectory.hpp", size=M,
                   attrs=["- entity_id_: GarageEntityIdMsg", "- interval_: Interval",
                          "- collision_id_: CollisionEntityId_t   // footprint",
                          "- action_id_: size_t   // event vertex (or 999999)",
                          "- delta_: optional<DiscreteGarageEventMsg>",
                          "- location_: variant<Pose, Edge>", "- is_idle_: bool"],
                   methods=["+ Motion(entity, interval, collision, action, X)",
                            "    X = Pose | Edge | AgvPoseChangedMsg |",
                            "        AgvLiftChangedMsg + Pose | BayStateChangedMsg |",
                            "        VecsStateChangedMsg | VrcStateChangedMsg",
                            "+ operator<(o): interval_.Before(o.interval_)",
                            "+ operator==(o): every field equal",
                            "+ WithInterval(i): Motion",
                            "+ GetSourcePose(), GetTargetPose(): const Pose&",
                            "+ GetInterval(), GetEntityId(), GetCollisionId(),",
                            "  GetActionId(), GetDelta(), GetLocation(), IsIdle()"])
    itv = uml_class(d, mo.x0, mo.y1 + 80, "Interval", accent=DAT, stereo="interval.hpp", size=M,
                    attrs=["- begin_, end_: Timepoint"],
                    methods=["+ Before(o): begin_ < o.begin_", "+ StrictlyBefore(o): end_ <= o.begin_"])
    ty = mo.y1 + 80
    pose = uml_class(d, itv.x1 + 50, ty, "Pose, Edge", accent=MSG, stereo="type aliases in Motion", size=M,
                     attrs=["Pose = GaragePoseMsg  {node_id, heading}", "Edge = std::array<GaragePoseMsg, 2>"])
    ev = uml_class(d, pose.x0, pose.y1 + 40, "DiscreteGarageEventMsg", accent=MSG, stereo="interfaces · ROS message",
                   size=M, attrs=["one of: AgvPoseChanged, AgvLiftChanged,", "BayStateChanged, VecsStateChanged,",
                                  "VrcStateChanged  (serialized)"])
    sch = uml_class(d, cs.x1 + 100, tr.y1 + 150, "all_motions", accent=SCH,
                    stereo="scheduler · ResponseFromTrajectories · local", size=M,
                    attrs=["std::set<Motion, MotionScheduleOrder>", "  // start, then action id, then hash"],
                    methods=["CollectAndCollapseTrajectoryMotions(state, layout, all_motions)",
                             "BuildActionDagFromMotions(all_motions, ctx, ...)"])
    # relations
    connect(d, [(cs.x1, cs.y0 + 60), (tr.x0, cs.y0 + 60)], kind="comp", color=DAT, mult_end="0..* by entity",
            label="trajectories_", label_at=((cs.x1 + tr.x0) / 2, cs.y0 + 78))
    connect(d, [(tr.x1, tr.y0 + 60), (mo.x0, tr.y0 + 60)], kind="comp", color=DAT, mult_end="0..* ordered",
            label="trajectory_", label_at=((tr.x1 + mo.x0) / 2, tr.y0 + 78))
    connect(d, [(mo.x0 + 60, mo.y1), (mo.x0 + 60, itv.y0)], kind="comp", color=DAT, mult_end="1")
    connect(d, [(mo.x1 - 60, mo.y1), (mo.x1 - 60, ty - 30), (pose.cx, ty - 30), (pose.cx, pose.y0)], kind="comp",
            color=MSG, mult_end="1", label="location_", label_at=((mo.x1 - 60 + pose.cx) / 2, ty - 30))
    connect(d, [(mo.x1, mo.y0 + 160), (ev.x1 + 50, mo.y0 + 160), (ev.x1 + 50, ev.cy), (ev.x1, ev.cy)],
            kind="comp", color=MSG, mult_end="0..1", label="delta_", label_at=(ev.x1 + 50, (mo.y1 + ev.y0) / 2))
    connect(d, [(sch.x1, sch.y0 + 40), (mo.x0 - 40, sch.y0 + 40), (mo.x0 - 40, mo.y1 - 30), (mo.x0, mo.y1 - 30)],
            kind="dep", color=SCH, label="copies motions with a delta", label_at=((sch.x1 + mo.x0) / 2 - 20, sch.y0 + 56))
    note(d, cs.x0, cs.y1 + 40, cs.w + 60,
         "The ordering key is the start time only. Two motions that start at the same time compare equivalent, "
         "so a Trajectory can hold at most one of them, and RemoveMotion(m) erases whichever motion starts when m "
         "starts. AddMotion additionally rejects any overlap, so stored motions never overlap in time.",
         title="std::set<Motion> and operator<", accent=DAT)
    frame(d, title="ContinuousState, Trajectory and Motion",
          subtitle="What CHUGG reads and returns. Each entity has one Trajectory; a Trajectory keeps its Motions sorted "
                   "by start time and refuses overlaps. The scheduler then merges every trajectory into one set "
                   "with a full tie-break and builds the action DAG from it.",
          badge_key="as-built",
          legend=[("box", DAT, "motion_planner type"), ("box", MSG, "ROS message types"),
                  ("box", SCH, "scheduler (Action graph tab)"), ("comp", DAT, "composition (owns)"),
                  ("dep", T.fg2, "dependency")],
          footnote="Abridged from continuous_state.hpp, trajectory.hpp and interval.hpp; all_motions and "
                   "MotionScheduleOrder are in scheduler.cpp.")
    return d


# --------------------------------------------------------------------------------------
# 103 — one PlanMotions call (animated sequence diagram)
# --------------------------------------------------------------------------------------
@figure("103_seq_plan_motions", "One PlanMotions call: sequence of calls (animated)", DOC3)
def seq_plan_motions():
    d = Doc("103_seq_plan_motions", "One PlanMotions call, call by call",
            "UML sequence diagram, animated: Scheduler::PlanMotions builds the inputs and calls "
            "Chugg::SolveSequential, which sets up one SippAgv per AGV, then for every event in topological order "
            "plans it with SIPP or a fixed duration and carves the result into the other AGVs' tables, and finally "
            "checks collisions and returns the ContinuousState.")
    SCH, CH, SIP, DAT, GEN = T.sky, T.amber, T.green, T.violet, T.teal
    parts = [("sch", ":Scheduler", SCH), ("cs", "init : ContinuousState", DAT),
             ("fn", "garage_graph_pathing", GEN), ("ch", ":Chugg", CH),
             ("a", "planners[a] : SippAgv", SIP), ("env", "env : SippEnvironment", SIP),
             ("astar", "SingleSourceSearch", GEN), ("b", "planners[b] : SippAgv", SIP),
             ("tbl", "table_ : CollisionTable", EXT)]
    sub = {"fn": "free functions", "a": "the event's AGV", "astar": "A*", "b": "every other AGV",
           "tbl": "common_ros"}
    gaps = {"cs": 250, "fn": 230, "ch": 250, "a": 300, "env": 230, "astar": 210, "b": 240, "tbl": 230}
    xs = {}
    x = 70
    for k, _, _ in parts:
        x += gaps.get(k, 0)
        xs[k] = x
    col = {k: c for k, _, c in parts}
    head_h = 50
    for k, label, c in parts:
        w = max(text_width(label, 12.5, "mono", 600), text_width(sub.get(k, ""), 10.5, "sans")) + 28
        d.rect(xs[k] - w / 2, 0, w, head_h, rx=8, fill=T.card, stroke=c, sw=1.5)
        d.text(xs[k], 18 if k in sub else head_h / 2, label, size=12.5, family="mono", weight=600, fill=c,
               anchor="middle")
        if k in sub:
            d.text(xs[k], 36, sub[k], size=10.5, fill=T.muted, anchor="middle")
    x_left, x_right = 0, xs["tbl"] + 120
    y = head_h + 40
    rows: list = []          # (step, y)
    acts: list = []          # (lifeline, y0, y1, step)
    frags: list = []         # (y0, y1, x0, x1, tag, guard, step)
    steps: list = []
    cur = {"k": 0}

    def step(caption):
        k = d.step(caption)
        cur["k"] = k
        steps.append([k, None, None])
        return k

    def mark(yy):
        s = steps[-1]
        s[1] = yy if s[1] is None else min(s[1], yy)
        s[2] = yy if s[2] is None else max(s[2], yy)

    def msg(a, b, text, *, ret=False, dy=40, c=None):
        nonlocal y
        c = c or (T.muted if ret else col[b] if not ret else T.muted)
        with d.at(cur["k"]):
            x1, x2 = xs[a], xs[b]
            off = 7
            xa = x1 + (off if x2 > x1 else -off)
            xb = x2 - (off if x2 > x1 else -off)
            d.line(xa, y, xb, y, stroke=c, sw=1.5, dash="6 4" if ret else None, layer="edges")
            d.arrowhead((xb, y), (xa, y), kind="open" if ret else "filled", color=c, size=9)
            label_pill(d, min(xa, xb) + 16, y - 13, text, color=c if not ret else T.fg2, bg=T.bg, size=11.5,
                       anchor="start")
        mark(y - 26)
        mark(y + 6)
        y += dy

    def selfmsg(a, text, *, dy=46, c=None, sub_text=None):
        nonlocal y
        c = c or col[a]
        with d.at(cur["k"]):
            x0 = xs[a] + 7
            h = 22
            d.polyline([(x0, y - 4), (x0 + 30, y - 4), (x0 + 30, y + h - 4), (x0 + 4, y + h - 4)], stroke=c, sw=1.5,
                       radius=4)
            d.arrowhead((x0, y + h - 4), (x0 + 30, y + h - 4), kind="filled", color=c, size=8)
            d.text(x0 + 40, y + 2, text, size=11.5, family="mono", fill=c if c != T.fg2 else T.fg2)
            if sub_text:
                d.text(x0 + 40, y + 19, sub_text, size=11, fill=T.muted)
        mark(y - 14)
        mark(y + (26 if sub_text else 20))
        y += dy + (8 if sub_text else 0)

    def frag(y0, y1, a, b, tag, guard, k):
        frags.append((y0, y1, xs[a] - 60, xs[b] + 80, tag, guard, k))

    # ---------------- step 0 ----------------
    step("PlanMotions builds CHUGG's inputs: every entity standing still until start_time, the trapezoid time of "
         "every graph edge, and the all-pairs cost table SIPP uses as its A* heuristic (Floyd-Warshall, recomputed "
         "on every call). The Chugg constructor takes a topological order of the event DAG and replays it once.")
    a0 = y
    msg("sch", "cs", "ContinuousState(initial_state, table_, layout, start_time)")
    msg("sch", "fn", "GetEdgeDurations(gg_, cost_model_)")
    msg("fn", "sch", "edge_durations", ret=True)
    msg("sch", "fn", "GetAllPairsMinCost(gg_, edge_durations, 0, max)")
    msg("fn", "sch", "heuristics  (Floyd-Warshall)", ret=True)
    msg("sch", "ch", "Chugg(gg_, table_, ctx->events, init, edge_durations, heuristics, cost_model_)", dy=34)
    selfmsg("ch", "InitializeEventOrder()", sub_text="GetTopologicalOrdering, replay every Apply; throws on failure")
    # ---------------- step 1 ----------------
    step("SolveSequential starts. SolveInitialization finds the movable AGVs and planning_start_, the trays, bays "
         "and VECS that have events, and builds constraints_: per footprint, the vertices and edges blocked by "
         "anything that never moves in this plan.")
    s1 = y
    msg("sch", "ch", "SolveSequential(audit_ptr)")
    selfmsg("ch", "SolveInitialization()",
            sub_text="movable AGVs, planning_start_, dynamic entities, constraints_ = GetAllStaticFilters(...)")
    msg("ch", "cs", "GetEndState()")
    msg("cs", "ch", "DiscreteGarageState at start_time", ret=True)
    # ---------------- step 2 ----------------
    step("MakeRootNode: one SippAgv per movable AGV. Every initial motion that ends after planning_start_, and "
         "every parked tray or closed bay without events, is carved into the other AGVs' safe-interval tables. "
         "Then each AgvMove and TrayMove becomes a SIPP goal of its AGV, in topological order.")
    s2 = y
    y += 26
    msg("ch", "a", "«create» SippAgv(gg, table, edge_costs, heuristics, agv_state, time, ...)")
    msg("ch", "b", "DeconflictAgvs(root, m)  ->  AddDeconflictConstraints(m)")
    msg("b", "tbl", "Query(avoid_id, my_id, location)")
    msg("tbl", "b", "PoseSet, EdgeSet", ret=True)
    selfmsg("b", "sit_.AddConstraint(key, interval)", sub_text="IntervalSet::CarveInterval")
    msg("ch", "a", "AddEventGoal(event, event_id, collision_id)")
    frag(s2 - 30, y - 18, "ch", "tbl", "loop", "[MakeRootNode: per movable AGV, per initial motion, per event]", 2)
    # ---------------- step 3 ----------------
    step("The loop visits every event in topological order. For an AgvMove or TrayMove: the AGV is free when its "
         "last motion ends; the event may start when the last motion of each dependency has ended. If that is "
         "later, a wait motion (with this event's id) fills the gap and is carved into the other AGVs.")
    y += 22
    loop_y0 = y - 26
    alt_y0 = y - 2
    y += 44
    selfmsg("ch", "EntityCurrentTime(node, agv)", sub_text="end of the AGV's last motion")
    selfmsg("ch", "GetDependencyCompletionTime(node, event_id)",
            sub_text="scans each dependency's trajectory for motions with its id")
    selfmsg("ch", "[later] AddMotion(wait_for_deps); DeconflictAgvs(node, wait)")
    # ---------------- step 4 ----------------
    step("SetEventSafeIntervals copies the AGV's safe-interval table, then adds the sequential assumption: every "
         "motion of every other entity, and a resting motion at its last pose until Timepoint::max, is carved in. "
         "Under this assumption nothing planned later can move out of the way.")
    msg("ch", "a", "GetSafeIntervalTable()  ->  orig_sit (copy)")
    msg("ch", "a", "AddDeconflictConstraints(m)  for every other entity's motions + resting motion")
    # ---------------- step 5 ----------------
    step("SIPP plans this one event. PlanEvents builds a SippEnvironment over the AGV's table and runs the generic "
         "A*, which calls back GetHeuristic, OnExpansion and GetNeighbors until a state completes the goal (or "
         "5,000,000 expansions). The path of SippStates becomes Motions in a Trajectory.")
    msg("ch", "a", "PlanEvents({event_id}, agv_state, initial_time, constraints_)")
    msg("a", "env", "«create» SippEnvironment(graph, edge_durations, goals, sit_, heuristics, constraints_, ...)")
    msg("a", "astar", "SingleSourceSearch(initial_state, 0, env)")
    i_y0 = y - 26
    y += 24
    msg("astar", "env", "GetHeuristic(s), OnExpansion(s, g), GetNeighbors(s)")
    selfmsg("env", "GetTraversableEdges -> sit.FindSafeInterval(key, start, duration)")
    frag(i_y0, y - 18, "astar", "env", "loop", "[until a state completes the last goal]", 5)
    msg("astar", "a", "SearchSolution", ret=True)
    selfmsg("a", "SolutionToTrajectory(solution, ...)", sub_text="GetPath(target): SippStates -> Motions")
    msg("a", "ch", "optional<Trajectory>", ret=True)
    # ---------------- step 6 ----------------
    step("Commit. The AGV's table is restored from the copy, each new motion is appended to the node's trajectory "
         "for this AGV and carved into every other AGV's table for good. A lift also ends (pick-up) or starts "
         "(drop) the tray's parked motion.")
    msg("ch", "a", "SetSafeIntervalTable(orig_sit)  (restore)")
    selfmsg("ch", "node.trajectories[agv].AddMotion(m)  for each motion")
    msg("ch", "b", "DeconflictAgvs(node, m)  ->  AddDeconflictConstraints(m)")
    msg("b", "tbl", "Query(...)  ->  sit_.AddConstraint  (carve)")
    selfmsg("ch", "lift: update the tray's parked motion")
    alt_mid = y - 18
    # ---------------- step 7 ----------------
    step("Bay and VECS events need no search: one motion of fixed duration (a closing bay first waits until no "
         "planned motion collides with the bay's overdrive-plate area), carved into every AGV's table. Every event, of any type, "
         "is then applied to the working state before the loop moves on.")
    y += 24
    selfmsg("ch", "BayTransition: wait for deps, wait until ODP area clear,",
            sub_text="AddMotion(transition of fixed duration); DeconflictAgvs(node, transition)")
    selfmsg("ch", "VecsTransition: AddMotion(vecs_transition seconds); DeconflictAgvs")
    alt_y1 = y - 18
    selfmsg("ch", "event->Apply(working_state)")
    loop_y1 = y - 16
    frags.append((loop_y0, loop_y1, xs["ch"] - 80, xs["tbl"] + 100, "loop",
                  "[PlanNodeSequential: for each event in event_order_]", 3))
    frags.append((alt_y0, alt_y1, xs["ch"] - 62, xs["tbl"] + 82, "alt", "[AgvMove or TrayMove]", 3))
    alt_sep = (alt_mid, "[BayTransition | VecsTransition]", 7)
    y += 24
    # ---------------- step 8 ----------------
    step("After the loop: a pairwise collision check over all new motions (any collision means std::nullopt), then "
         "the new motions are appended to a copy of the initial ContinuousState and returned. The scheduler turns "
         "it into the action DAG (Action graph tab).")
    msg("ch", "cs", "CheckCollisions(node.trajectories, geometry_)  static, all pairs")
    msg("cs", "ch", "vector<pair<Motion, Motion>>  (empty = no collision)", ret=True)
    selfmsg("ch", "GetUpdatedContinuousState(node)", sub_text="copy init_traj_, AddMotion every new motion")
    msg("ch", "sch", "optional<ContinuousState>", ret=True)
    a1 = y - 40
    selfmsg("sch", "ResponseFromTrajectories(ctx, state)", sub_text="-> action DAG")
    end_y = y + 10

    # lifelines and activations (always visible)
    for k, _, c in parts:
        d.line(xs[k], head_h, xs[k], end_y, stroke=T.border, sw=1.2, dash="4 5", layer="under")
    for k, y0, y1 in (("sch", a0 - 8, a1 + 8), ("ch", s1 - 8, a1 + 8)):
        d.rect(xs[k] - 6, y0, 12, y1 - y0, rx=2, fill=T.tint(col[k], 0.35, T.bg), stroke=col[k], sw=1, layer="under")
    # step bands: highlight the rows of the current step
    for k, y0, y1 in steps:
        with d.only(k):
            d.rect(x_left, y0 - 8, x_right - x_left, y1 - y0 + 16, rx=8, fill=T.tint(T.sky, 0.07, T.bg),
                   stroke=T.tint(T.sky, 0.35, T.bg), sw=1, layer="under")
        with d.at(k):
            d.text(x_left - 26, y0 + 4, f"{k + 1}", size=13, family="mono", weight=700, fill=T.sky)
    # combined fragments
    for (y0, y1, fx0, fx1, tag, guard, k) in frags:
        with d.at(k):
            d.rect(fx0, y0, fx1 - fx0, y1 - y0, rx=6, fill="none", stroke=T.faint, sw=1.2, layer="under")
            tw = text_width(tag, 11.5, "mono", 700) + 16
            d.path(f"M{fx0} {y0 + 6} Q{fx0} {y0} {fx0 + 6} {y0} L{fx0 + tw + 8} {y0} L{fx0 + tw + 8} {y0 + 12} "
                   f"L{fx0 + tw} {y0 + 20} L{fx0} {y0 + 20} Z", fill=T.muted_bg, stroke=T.faint, sw=1, layer="under")
            d.text(fx0 + 8, y0 + 10, tag, size=11.5, family="mono", weight=700, fill=T.fg2)
            d.text(fx0 + tw + 16, y0 + 10, guard, size=11.5, family="mono", fill=T.muted)
    ym, guard, k = alt_sep
    with d.at(k):
        fx0, fx1 = xs["ch"] - 62, xs["tbl"] + 82
        d.line(fx0, ym, fx1, ym, stroke=T.faint, sw=1.2, dash="6 4", layer="under")
        d.text(fx0 + 8, ym + 12, guard, size=11.5, family="mono", fill=T.muted)
    frame(d, title="One PlanMotions call, call by call",
          subtitle="Step through it: the inputs, CHUGG's setup, one pass of the event loop (search for AGV events, "
                   "fixed durations for bays and VECS), and the final collision check. Messages stay on screen; the "
                   "highlighted band is the current step.",
          badge_key="as-built",
          legend=[("arrow", T.fg2, "synchronous call"), ("dep", T.muted, "return"),
                  ("box", CH, "activation"), ("dashbox", T.faint, "combined fragment (loop / alt)")],
          footnote="From scheduler.cpp (PlanMotions), chugg_common.cpp, chugg_sequential.cpp, sipp_agv.cpp and "
                   "safe_interval_path_planning.cpp. Logging and the cost audit are left out; VrcTransition events "
                   "have no branch in the loop.")
    return d


# --------------------------------------------------------------------------------------
# 104 — how a Trajectory stores its motions (animated)
# --------------------------------------------------------------------------------------
@figure("104_trajectory_storage", "Trajectory storage: std::set<Motion> and a sorted vector (animated)", DOC3)
def trajectory_storage():
    d = Doc("104_trajectory_storage", "How a Trajectory stores its motions",
            "Animated: one AGV's trajectory as a timeline, as the std::set<Motion> it is stored in today (a balanced "
            "tree keyed by start time) and as a sorted std::vector; then three AddMotion calls: an append, an "
            "overlap that is rejected, and a second motion at the same start time, which is also rejected.")
    DAT, OK, BAD, GRY = T.violet, T.green, T.red, T.faint
    TS = 34
    TMAX = 20
    x0 = 0
    # ---------------- timeline ----------------
    d.text(x0, 0, "1  The trajectory: one AGV, motions ordered by start time", size=13.5, weight=600, fill=T.fg)
    ly = 40
    lane_h = 34
    d.text(x0, ly + lane_h / 2, "trajectory_", size=12, family="mono", fill=T.fg2)
    tx0 = x0 + 110
    d.rect(tx0, ly, TMAX * TS, lane_h, rx=5, fill=T.tint(T.card, 0.6, T.bg))
    cy = ly + lane_h + 46
    d.text(x0, cy + lane_h / 2, "AddMotion(...)", size=12, family="mono", fill=T.fg2)
    d.rect(tx0, cy, TMAX * TS, lane_h, rx=5, fill=T.tint(T.card, 0.35, T.bg), stroke=T.border_soft, sw=1, dash="4 4")
    for t in range(0, TMAX + 1, 2):
        xx = tx0 + t * TS
        d.line(xx, ly - 6, xx, cy + lane_h + 6, stroke=T.grid, sw=1, layer="under")
        d.text(xx, cy + lane_h + 20, f"{t}", size=11, family="mono", fill=T.muted, anchor="middle")
    d.text(tx0 + TMAX * TS + 10, cy + lane_h + 20, "s", size=11, family="mono", fill=T.muted)

    def bar(y, t0, t1, label, col, *, dash=None, cross=False):
        xa, xb = tx0 + t0 * TS, tx0 + t1 * TS
        if t1 == t0:
            d.line(xa, y + 3, xa, y + lane_h - 3, stroke=col, sw=3)
            d.text(xa + 6, y - 9, label, size=11, family="mono", weight=600, fill=col)
            return
        d.rect(xa + 1, y + 5, xb - xa - 2, lane_h - 10, rx=4, fill=T.tint(col, 0.30, T.bg), stroke=col, sw=1.3,
               dash=dash)
        d.text((xa + xb) / 2, y + lane_h / 2, label, size=11, family="mono", weight=600, fill=T.fg, anchor="middle")
        if cross:
            d.line(xa + 4, y + 7, xb - 4, y + lane_h - 7, stroke=BAD, sw=2)

    base = [(0, 4, "m0 wait"), (4, 7, "m1 4->9"), (7, 10, "m2 9->10"), (10, 13, "m3 lift")]
    for t0, t1, lab in base:
        bar(ly, t0, t1, lab, DAT)
    k0 = d.step("A trajectory of four motions: a wait, two edges and a lift. On the timeline they abut (one ends "
                "when the next begins). std::set keeps them in a balanced tree keyed by start time, one heap node "
                "per Motion; a sorted vector would keep the same order in one contiguous block.")
    k1 = d.step("AddMotion(m4, 13 s to 16 s), the case every AddMotion in CHUGG's sequential path takes: lower_bound "
                "finds no later motion, the last one (m3) ends at 13 s, so m4 goes at the end. In the tree it is a "
                "new leaf; in a vector it would be a push_back.")
    k2 = d.step("AddMotion(x, 8 s to 12 s) overlaps m2 and m3. lower_bound stops at m3 (the first start at or after "
                "8 s); x does not end before m3 starts, so AddMotion returns false and stores nothing. The callers "
                "in CHUGG ignore the return value, so a rejected motion would vanish silently.")
    k3 = d.step("Same start time. y is a zero-length motion at 16 s and is accepted. z (16 s to 18 s) starts at "
                "the same time: operator< compares only start times, so y and z are equivalent keys, lower_bound "
                "returns y and AddMotion refuses z. SippAgv drops zero-length states, so CHUGG avoids this case.")
    k4 = d.step("Summary: how CHUGG uses a Trajectory. Every insert is an append, the reads are in-order scans and "
                "the last element, and the one function that needs indexes copies the set into a vector first. "
                "The tree's strengths (cheap inserts in the middle, stable iterators) go unused.")
    with d.at(k1):
        bar(ly, 13, 16, "m4 10->11", OK)
    with d.only(k1):
        bar(cy, 13, 16, "m4", OK)
        d.text(tx0 + 16.4 * TS, cy + lane_h / 2, "true: appended", size=11.5, family="mono", weight=600, fill=OK)
    with d.only(k2):
        bar(cy, 8, 12, "x", BAD, dash="4 3", cross=True)
        d.text(tx0 + 12.4 * TS, cy + lane_h / 2, "false: overlaps m2, m3", size=11.5, family="mono", weight=600,
               fill=BAD)
    with d.only(k3):
        bar(ly, 16, 16, "y", OK)
        bar(cy, 16, 18, "z", BAD, dash="4 3", cross=True)
        d.text(tx0 + 18.4 * TS, cy + lane_h / 2, "false: same start as y", size=11.5, family="mono",
               weight=600, fill=BAD)

    # ---------------- tree and vector ----------------
    py = cy + lane_h + 70
    d.text(x0, py, "2  Stored today: std::set<Motion>", size=13.5, weight=600, fill=T.fg)
    d.text(x0, py + 20, "balanced binary tree (red-black), key = interval begin, one allocation per Motion",
           size=11.5, fill=T.muted)
    nw, nh = 92, 40

    def tnode(cx, cyy, key, lab, col):
        d.rect(cx - nw / 2, cyy, nw, nh, rx=8, fill=T.tint(col, 0.22, T.bg), stroke=col, sw=1.4)
        d.text(cx, cyy + 14, f"begin {key} s", size=11, family="mono", weight=600, fill=col, anchor="middle")
        d.text(cx, cyy + 29, lab, size=10.5, family="mono", fill=T.fg2, anchor="middle")
        return (cx, cyy)

    ty0 = py + 50
    root = tnode(250, ty0, 4, "m1", DAT)
    l = tnode(130, ty0 + 80, 0, "m0", DAT)
    r = tnode(370, ty0 + 80, 10, "m3", DAT)
    rl = tnode(290, ty0 + 160, 7, "m2", DAT)

    def tedge(p, c, col=T.border):
        d.line(p[0], p[1] + nh, c[0], c[1], stroke=col, sw=1.4, layer="under")
    tedge(root, l)
    tedge(root, r)
    tedge(r, rl)
    with d.at(k1):
        rr = tnode(450, ty0 + 160, 13, "m4", OK)
        tedge(r, rr, OK)
    with d.only(k3):
        rrr = tnode(530, ty0 + 240, 16, "y", OK)
        tedge(rr, rrr, OK)
        d.text(530, ty0 + 300, "z: equivalent to y -> refused", size=11, family="mono", fill=BAD, anchor="middle")
    with d.only(k2):
        d.text(250, ty0 + 250, "lower_bound(x) -> m3", size=11.5, family="mono", fill=BAD, anchor="middle")
        d.circle(370, ty0 + 100, 52, fill="none", stroke=BAD, sw=1.6, dash="4 3")

    vx = 660
    d.text(vx, py, "3  Alternative: sorted std::vector<Motion>", size=13.5, weight=600, fill=T.fg)
    d.text(vx, py + 20, "same order, one contiguous allocation, index access", size=11.5, fill=T.muted)
    cw, ch_ = 72, 44
    vy = py + 60
    cells = [("0", "m0"), ("4", "m1"), ("7", "m2"), ("10", "m3")]
    for i, (k, lab) in enumerate(cells):
        d.rect(vx + i * cw, vy, cw, ch_, fill=T.tint(DAT, 0.22, T.bg), stroke=DAT, sw=1.3)
        d.text(vx + i * cw + cw / 2, vy + 15, f"{k} s", size=11, family="mono", weight=600, fill=DAT, anchor="middle")
        d.text(vx + i * cw + cw / 2, vy + 31, lab, size=10.5, family="mono", fill=T.fg2, anchor="middle")
        d.text(vx + i * cw + cw / 2, vy + ch_ + 14, f"[{i}]", size=10.5, family="mono", fill=T.muted, anchor="middle")
    for i in range(4, 6):
        d.rect(vx + i * cw, vy, cw, ch_, fill="none", stroke=T.border_soft, sw=1, dash="4 4")
    d.text(vx + 5 * cw + cw / 2, vy + ch_ + 14, "capacity", size=10.5, fill=T.faint, anchor="middle")
    with d.at(k1):
        d.rect(vx + 4 * cw, vy, cw, ch_, fill=T.tint(OK, 0.22, T.bg), stroke=OK, sw=1.3)
        d.text(vx + 4 * cw + cw / 2, vy + 15, "13 s", size=11, family="mono", weight=600, fill=OK, anchor="middle")
        d.text(vx + 4 * cw + cw / 2, vy + 31, "m4", size=10.5, family="mono", fill=T.fg2, anchor="middle")
        d.text(vx + 4 * cw + cw / 2, vy + ch_ + 14, "[4]", size=10.5, family="mono", fill=T.muted, anchor="middle")
    with d.only(k1):
        d.text(vx, vy + ch_ + 40, "push_back: amortised O(1), no search needed", size=11.5, family="mono", fill=OK)
    with d.only(k2):
        d.text(vx, vy + ch_ + 40, "std::lower_bound on begin -> [3]; same check, same false", size=11.5,
               family="mono", fill=BAD)
    with d.only(k3):
        d.text(vx, vy + ch_ + 40, "the rule for equal starts becomes an explicit choice", size=11.5, family="mono",
               fill=T.fg2)

    # ---------------- AddMotion code ----------------
    code = ["bool Trajectory::AddMotion(const Motion& motion) {",
            "  if(trajectory_.empty()) { insert; return true; }",
            "  auto it = trajectory_.lower_bound(motion);  // first begin >= motion's",
            "  if(it == trajectory_.end()) {               // nothing starts later",
            "    --it;                                     // the last motion",
            "    if(it->interval.StrictlyBefore(motion))   // last.end <= motion.begin",
            "      { insert at end; return true; }",
            "    return false;                             // overlaps the last motion",
            "  }",
            "  if(motion.interval.StrictlyBefore(it->interval)) {  // ends before next",
            "    if(previous motion overlaps) return false;",
            "    insert; return true;",
            "  }",
            "  return false;   // overlaps the next motion, or starts at the same time",
            "}"]
    cx0 = 1130
    d.text(cx0, 0, "4  AddMotion (trajectory.cpp, abridged)", size=13.5, weight=600, fill=T.fg)
    cb = BBox(cx0, 24, cx0 + 620, 0)
    from components import code_panel
    pan = code_panel(d, cx0, 24, 640, code, size=11.5)
    lh = 11.5 * 1.5
    top = 24 + 14 + 11.5 / 2

    def hl(lines, col, k):
        with d.only(k):
            for i in lines:
                yy = top + i * lh
                d.rect(cx0 + 6, yy - lh / 2, 628, lh, rx=3, fill=T.tint(col, 0.22, "#0B1222"), layer="main")
    hl([2, 3, 4, 5, 6], OK, k1)
    hl([2, 9, 13], BAD, k2)
    hl([2, 9, 13], BAD, k3)

    # ---------------- usage table ----------------
    uy = max(pan.y1, ty0 + 320) + 50
    d.text(cx0, pan.y1 + 34, "5  What CHUGG and the scheduler do with a Trajectory", size=13.5, weight=600,
           fill=T.fg)
    rows = [("operation", "where", "set today", "sorted vector"),
            ("append after the last motion", "every AddMotion in CHUGG", "O(log n) + allocation", "O(1) amortised"),
            ("insert in the middle", "never in CHUGG", "O(log n)", "O(n) shift"),
            ("last motion", "SetEventSafeIntervals, lifts", "rbegin()", "back()"),
            ("all motions in time order", "everywhere", "in-order walk", "linear scan"),
            ("motion with a given event id", "GetDependencyCompletionTime", "linear scan", "linear scan"),
            ("index access", "CoalesceTrajectory", "copies to a vector", "direct"),
            ("motions overlapping an interval", "FindInInterval (no caller)", "linear find_if", "binary search"),
            ("copy", "Node, results, Plan()", "one allocation each", "one allocation")]
    colw = [210, 205, 150, 120]
    ry = pan.y1 + 54
    for i, row in enumerate(rows):
        xx = cx0
        for j, cell in enumerate(row):
            c = T.fg2 if i else T.muted
            if i and j == 2:
                c = T.fg2
            d.text(xx, ry + i * 22, cell, size=11 if i else 10.5, family="mono" if j >= 2 or i == 0 else "sans",
                   weight=600 if i == 0 else 400, fill=c)
            xx += colw[j]
        if i == 0:
            d.line(cx0, ry + 11, cx0 + sum(colw), ry + 11, stroke=T.border_soft, sw=1)
    with d.only(k4):
        d.rect(cx0 - 8, ry + 22 - 12, sum(colw) + 8, len(rows) * 22 - 6, rx=6, fill="none",
               stroke=T.sky, sw=1.5)
    frame(d, title="How a Trajectory stores its motions",
          subtitle="std::set is an ordered container: it does keep motions in time order. Its key is the start time "
                   "alone, and AddMotion adds the no-overlap rule. Step through three inserts, then compare what "
                   "the code needs with what each container offers.",
          badge_key="as-built",
          legend=[("box", DAT, "stored motion"), ("box", OK, "accepted insert"), ("dashbox", BAD, "rejected insert")],
          footnote="m0 to m4, x, y and z are an illustrative example. The behaviour of AddMotion, operator< "
                   "(Interval::Before) and the call sites are from trajectory.hpp, trajectory.cpp, chugg_common.cpp, "
                   "chugg_sequential.cpp, sipp_agv.cpp and coalesce_trajectory.cpp.")
    return d
