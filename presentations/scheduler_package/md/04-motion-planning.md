# 04 — Motion planning: from the event DAG to timed motions

*Stage 4 of the pipeline: CHUGG turns the finished event DAG into timed, collision-free motions for every AGV, bay and VECS (VRC commands are added later, in the action DAG). This is the multi-agent path finding (MAPF) step.*

This tab builds on the finished event DAG from the Task planning tab. It first places motion planning between the two DAGs of the pipeline and shows how the planner is packaged and called, then opens CHUGG and SIPP, then derives the timing model behind every duration, then `ContinuousState`, the timeline CHUGG returns and the Action graph tab starts from, then the code itself as UML class and sequence diagrams, and ends by comparing CHUGG's inputs with the standard multi-agent path finding problem, as groundwork for swappable motion planners.

## Where motion planning sits: two DAGs around one planner

Motion planning sits between the two DAGs of the pipeline (besides the working copies some stages make). The first, the event DAG, is its input; the second, the action DAG, is built from its output, and only that second one is an action dependency graph. The order is the one in the literature: motion planning first, then the ADG, then execution.

![Event DAG, CHUGG, action DAG](figures/91_planning_pipeline.svg)

Textbook pipeline above, the scheduler below. The event DAG (step 1) is the planner's *input*: a precedence graph of events, with no times and no paths. CHUGG (step 2) turns it into timed trajectories. The action DAG (step 3) is the ADG, built from those trajectories; it also inherits every event-DAG edge.

1.  **Event DAG: what, and in which order.** `Plan*Job`, tray assignment and AGV assignment add `ScheduleEvent`s and edges to `ctx->events` (the class in [section 12](#bg-directed-acyclic-graphs-then-scheduleeventdag); how it is built in the [Task planning](#doc-task-planning) tab). A vertex is a discrete change (“AGV-3 drives from node 10 to node 9”, “bay 1 opens”); an edge says one change must finish before another starts. Nothing in it says *when*, or which intermediate poses a move passes through.
2.  **CHUGG: when and where.** `PlanMotions` hands the event DAG to `Chugg::SolveSequential`, which returns a `ContinuousState`: for every entity, a timeline of motions. This is the multi-agent path finding (MAPF) step.
3.  **Action DAG: the ADG.** `ResponseFromTrajectories` cuts the timelines into actions (one per motion that changes something), orders actions that use the same space, copies the event-DAG edges across, and writes the result to `Schedule.nodes`. The Action graph tab builds this step from first principles ([section 7.1](#ad-two-dags-two-jobs)).
4.  **Dispatch** starts each action of `Schedule.nodes` as soon as all its `parents` are done. It is outside the snapshots; the Action graph tab explains the rule and why it is safe ([section 4](#ad-executing-an-adg)) and what happens to a schedule that is still running when the next plan arrives ([section 7.5](#ad-persistent-planning-base-schedule-and-the-split)).

**The event DAG is not an ADG.** It resembles one: its vertices are discrete changes and its edges mean “before”, and a few of its edges are spatial (`AddNodeArrivalDeps` orders two AGVs that use the same node; path repair adds edges for AGVs in the way). But it is built before any timing exists, and its edges come from the jobs (“the tray must arrive before the bay opens”), not from the planned paths. Its job is to be the *task* input of the motion planner.

**The MAPF input is unusual.** Classic MAPF gives each robot one start and one goal and asks for collision-free paths. CHUGG's input instead is a set of goals for many entities (AGVs, bays, VECS) with a partial order *across* entities: AGV-2 may only pick up the tray after the bay has closed, and so on. The research name for this is MAPF with precedence constraints, MAPF-PC (Zhang, Chen, Li, Williams and Koenig, “[Multi-Agent Path Finding for Precedence-Constrained Goal Sequences](https://idm-lab.org/bib/abstracts/Koen22c.html)”, AAMAS 2022). CHUGG solves it the simple way: it takes the events in one topological order of the event DAG and plans each one against everything already planned, never revising earlier choices (prioritized planning, with SIPP as the single-AGV search; [section 21.1](#bg-inside-solvesequential)). The ADG afterwards makes the result robust to delays, exactly as in the textbook.

**The event edges reach execution twice.** CHUGG respects them when it picks start times, and the action DAG copies them again ([section 6.2](#ad-how-the-action-dag-is-built)).

The single-agent searches from the same package, which task planning uses, are explained later in this tab ([section 7](#mp-single-agent-searches)).

## How the motion planner is packaged and called

**A library, not a node.** `motion_planner` is a ROS 2 package that builds one shared C++ library and nothing else (`volley_add_library(motion_planner SHARED DIRECTORY src)`). It has no node, no component, no service, topic or action, and keeps no state between calls; it depends on `rclcpp` only for `rclcpp::Logger`. The one ROS node is the scheduler's: `scheduler_node`, the component `volley::SchedulerComponent` ([section 1.6](#bg-where-the-scheduler-runs-the-node-and-its-interfaces)).

**Called synchronously, in process, once per plan.** When a client calls the scheduler's `plan` service, the service callback runs `Scheduler::Plan` on its own thread. Task planning already calls into the library (the single-agent searches of the Task planning tab, [section 3](#bg-the-motion-planner-toolbox)). After task planning, `Scheduler::PlanMotions` builds the per-call inputs, constructs a `volley::Chugg` on the stack, calls `SolveSequential`, and returns the `ContinuousState` to `Plan`, which builds the action DAG and the response. Nothing runs in parallel with it, and nothing survives the call except what the scheduler keeps (the layout, graph, collision table and cost model, built once in the `Scheduler` constructor).

![Process diagram of scheduler_node: Dispatch calls the plan service in SchedulerRos, which calls Scheduler::Plan, which calls the motion_planner shared library for searches and CHUGG; below are the package dependencies and a library-versus-node comparison table.](figures/113_motion_planner_deployment.svg)

**How the motion planner is packaged and called.** One OS process, `scheduler_node` (the rclcpp component `volley::SchedulerComponent`), holds `SchedulerRos`: the `plan` service, `set_bay_readiness_ratio` and `debug/printdags`, two 5 s publishers in their own callback group, and four clients into `/central`. Dispatch (in the central node) calls `plan`. The callback runs `Scheduler::Plan` synchronously on the same thread. Task planning calls the motion_planner single-agent searches directly, and `PlanMotions` builds a new `Chugg` for each call and gets back an `optional<ContinuousState>` from `SolveSequential`. `ResponseFromTrajectories` builds the `PlanResponse`. `motion_planner` is a plain shared library (`volley_add_library(motion_planner SHARED DIRECTORY src)`): it has no node and no ROS interfaces, and uses rclcpp only for logging. The table compares keeping it a library with making it a separate node.

What this means in practice:

- **The interface is C++.** The inputs are references to the scheduler's own objects (`GarageGraph`, `CollisionTable`, `ScheduleEventDag`, `ContinuousState`, cost tables), not messages. Nothing is serialised, so a call costs no copying, but nothing outside the process can call the planner either.
- **A slow plan blocks the service.** Planning time is service latency; the scheduler's publishers run in their own callback group so that a long plan does not stop the heartbeat.
- **The planner and the scheduler ship together.** They are built and versioned as one deployment; there is no protocol between them to keep compatible.
- **A swappable solver is a C++ interface first** ([section 15](#pr-swappable-motion-planners)). A solver in another language, or on another machine, would need the problem serialised into a message, which the solver-neutral problem description ([section 7.4](#mp-a-solver-neutral-problem)) would make possible; the figure's table lists the trade-offs.

VRC rides are part of this library's input (as graph edges), but its support for them is partial; the Layout file tab summarises what each stage does with VRCs ([section 7](#ly-vrc-support-status)).

## CHUGG, the motion planner

**The name.** `chugg.hpp` spells it out: “CHUGG (Constrained Huge Unknown Graph alGorithm) uses conflict-based search to deconflict agents and their motions. The low-level motion planner it uses, SIPP (Safe Interval Path Planning), keeps track of the when locations are free or not free by computing and updating safe time intervals.” The header describes the intended design. What runs today is the simpler of its two solvers: the scheduler calls `SolveSequential`, which logs “CHUGG: Solving with sequential planning (not CBS)”. The conflict-based search (CBS) solver, `SolveCbs`, is unfinished ([section 23.1](#bg-what-can-be-configured)).

**What it does.** Everything before it decides *what* must happen and *in which order*: the event DAG. CHUGG decides *when* and *where along the graph*: for every AGV (and every bay and VECS) it produces a timed trajectory, a sequence of motions with start and end times, such that the event order is respected and no two bodies overlap at the same time (overlap as defined by the `CollisionTable`, [section 3](#bg-the-physical-garage-and-its-coordinate-system)).

![CHUGG inputs and outputs](figures/72_chugg_io.svg)

`PlanMotions` builds seven inputs and calls `volley::Chugg::SolveSequential`. The result is a `ContinuousState`: per-entity trajectories of `Motion`s, each tagged with the vertex of the event it implements. The amber box summarises `SolveSequential`; the next subsection walks through it.

``` cpp
// Scheduler::PlanMotions (src/scheduler.cpp:4005), abridged
volley::ContinuousState initial_trajectories(ctx->initial_state, table_, *layout_, ctx->start_time);
auto edge_durations = volley::GetEdgeDurations(gg_, cost_model_);         // time to traverse each graph edge
auto heuristics = volley::GetAllPairsMinCost(gg_, edge_durations,
                                             Interval::Duration(0), Interval::Duration::max());  // for A*
// This is CHUGG v0.1
volley::Chugg motion_planner(gg_, table_, ctx->events, initial_trajectories, edge_durations, heuristics,
                             cost_model_, logger_);
auto trajectories_opt = motion_planner.SolveSequential(audit_ptr);       // std::optional<ContinuousState>
```

| Input                  | Built from                                                   | Role                                                                                                                                        |
|------------------------|--------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `gg_`                  | `Scheduler` member                                           | Where entities can go: poses and the moves between them                                                                                     |
| `table_`               | `Scheduler` member                                           | Which footprints at which poses overlap: what “collision” means                                                                             |
| `ctx->events`          | the reduced event DAG                                        | What must happen, and in which order; each vertex index becomes a motion's action id                                                        |
| `initial_trajectories` | `ContinuousState(initial_state, table_, layout, start_time)` | Every entity standing still where the request says, from `start_time`                                                                       |
| `edge_durations`       | `GetEdgeDurations(gg_, cost_model_)`                         | Time for each edge from rest to rest: the “full Trapezoid” profile (accelerate, cruise, decelerate), from `cost_model.Duration(transition)` |
| `heuristics`           | `GetAllPairsMinCost(gg_, edge_durations, ...)`               | Cost-to-go between every pair of graph vertices (Floyd–Warshall over `edge_durations`), SIPP's A\* heuristic                                |
| `cost_model_`          | `Scheduler` member (from ROS parameters)                     | Speeds, accelerations, lift and bay/VECS event durations                                                                                    |

The scheduler shapes its DAG for CHUGG in three places, all covered in the Task planning tab: node-arrival edges (`AddNodeArrivalDeps`), AGV path repair (`EnsureAgvMovePathsClear`), and `Reduce()` right before the sanity check (sections [17](#bg-agv-assignment-doagvassignments) and [18](#bg-reduce-and-sanitycheckevents)). A test comment adds a known limit: “CHUGG can't handle rando AGVs strewn about yet”.

**Output.** `ContinuousState::GetTrajectories()` maps each entity to its list of `Motion`s. The response code uses these accessors: `GetEntityId()`, `GetInterval()` (start and end time), `GetCollisionId()` (which footprint: a bare AGV, an AGV carrying a tray of some size, ...), `GetActionId()` (the vertex of the event in `ctx->events` that the motion implements), `GetSourcePose()` / `GetLocation()`, `GetDelta()` (the discrete change, if the motion has one) and `IsIdle()`. `CollectAndCollapseTrajectoryMotions` merges all trajectories into one set ordered by start time, then action id, and collapses multi-step VRC floor traversals into one motion.

**Failure.** `SolveSequential` returning `std::nullopt` means no collision-free timing exists for this DAG; every job fails with “CHUGG failed to find a solution, event dag may be infeasible”. Some problems are not reported that way: the constructor and the planning loop *throw* `std::logic_error` for a DAG they cannot replay (no topological order, a `TrayMove` whose AGV is not under the tray, a dependency without any motion), and `PlanMotions` does not catch exceptions. With `cost_audit` on (the default), `PlanMotions` also logs one CSV row per cost segment (`audit_csv,index,seconds,cumulative,description`) so the time breakdown can be pasted into a spreadsheet.

How CHUGG uses these inputs, and why the scheduler has to prepare the event DAG carefully, is the subject of the next two subsections.

### Inside SolveSequential: one event at a time

`SolveSequential` is *prioritized planning*: it plans one event at a time, each against everything planned before it, and never goes back. The priority order is not a ranking of robots, as in most prioritized MAPF planners, but the topological order of the event DAG.

![Prioritized planning with safe intervals](figures/97_prioritized_planning.svg)

**Prioritized planning on a small example.** Two AGVs cross at vertex 3, and the event order puts AGV-1's event first. Step through it: AGV-1 is planned alone, its motions are carved into AGV-2's safe-interval table, and SIPP then plans AGV-2, which waits at vertex 6 until vertex 3 is safe. The figure below shows the real loop with all its event types.

![SolveSequential step by step](figures/93_chugg_sequential.svg)

`SolveSequential` from `chugg_common.cpp` and `chugg_sequential.cpp`. Setup runs once. The loop visits every event in one topological order; an AGV or tray event is planned by SIPP on that AGV's safe-interval table, while bays and VECS just get a fixed duration. Committed motions are carved out of every other AGV's table. A pairwise collision check over all new motions closes the call.

**Setup** (constructor, `SolveInitialization`, `MakeRootNode`):

1.  **Event order.** `InitializeEventOrder` takes `event_dag.GetTopologicalOrdering()` and replays every event on the start state, checking a few invariants (a `TrayMove` has a tray, an AGV and a destination, and the AGV is under the tray) and that every `Apply` succeeds. Any failure throws.
2.  **Who moves.** Every AGV that is not disabled is *movable* and gets its own planner, a `SippAgv`, even if no event mentions it. Trays, bays and VECS that appear in an event are *dynamic*. `planning_start_` is the earliest time a movable AGV is free, which is `ctx->start_time`.
3.  **Static obstacles.** `GetAllStaticFilters` builds, per footprint type, a `GraphFilterProperties` that switches off every vertex and edge blocked by something that never moves in this plan (parked trays not in any event, disabled AGVs, bays without events) or disabled in the layout state.
4.  **Initial reservations.** Every motion of the initial `ContinuousState` is carved out of each AGV's safe-interval table. A closed bay or parked tray without events is reserved from its last motion until the end of time.
5.  **Goals.** Walking the order once, each `AgvMove` and `TrayMove` becomes a SIPP goal for its AGV: “arrive at this vertex” for a move, “wait this long” for a lift. The footprint is chosen from the state at that point (bare AGV, or the tray's size class when loaded).

**The loop** (`PlanNodeSequential`), for each event in the order:

| Event                 | What CHUGG does                                                                                                                                                                                                                                                                                                                                                                                                              |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| every event           | Start at the entity's current end time. `GetDependencyCompletionTime` finds, for each in-edge, the end of the dependency's last motion with that event's id; if the latest is later, a wait motion (tagged with this event's id) fills the gap.                                                                                                                                                                              |
| `AgvMove`, `TrayMove` | `SetEventSafeIntervals` adds the **sequential assumption**: every other dynamic entity stays at the end of what has been planned for it, forever. SIPP then plans this one event on the AGV's table (`SippAgv::PlanEvents`). The assumption is removed again, the new motions are appended, and `DeconflictAgvs` carves them out of every other AGV's table for good. A lift also ends or starts the tray's “parked” motion. |
| `BayTransition`       | One motion with a fixed duration ([section 23.1](#bg-what-can-be-configured)). A closing transition (or `PROCESS_RETRIEVE`) first waits until the last already-planned motion that would collide with the bay's overdrive-plate area (`BAY_ODP`; the code names the resulting motion `bay_door_is_closed`) has ended.                                                                                                        |
| `VecsTransition`      | One motion of `vecs_transition` seconds. VECS never collide with anything (`CheckMotionCollision` skips them).                                                                                                                                                                                                                                                                                                               |
| `VrcTransition`       | An overload exists, but the loop has no branch for it, and nothing in the supplied packages creates such events. AGVs ride VRCs as ordinary graph edges (`VRC_TRANSITION`), and the scheduler inserts VRC commands into the action DAG afterwards (`InsertVrcActionsIntoDag`).                                                                                                                                               |

After the loop, `ContinuousState::CheckCollisions` compares every pair of new motions (all pairs across all trajectories). Any collision means `std::nullopt`; otherwise the new motions are appended to the initial state and returned.

**What follows from this design.**

- **The event order is the priority order.** CHUGG calls `ScheduleEventDag`'s own `GetTopologicalOrdering`, which is deterministic: among the events that are ready, the one with the lowest job index goes first ([section 12.5](#bg-the-operations)). An event planned earlier gets first claim on space and time, so earlier jobs in the request get priority, and adding or removing an edge, which changes when an event becomes ready, can change the whole plan or make it fail.
- **No backtracking.** If SIPP finds no path for an event, the whole call fails; earlier events are not re-planned to make room. Prioritized planning is incomplete in exactly this way.
- **Why `AddNodeArrivalDeps` is needed.** Under the sequential assumption an AGV that has not yet been planned to leave a node sits there forever. If AGV-2's arrival at that node comes before AGV-1's departure in the order, AGV-2's goal can never be completed: an arrival counts only if the vertex stays safe forever afterwards. The scheduler's edge “AGV-1 leaves before AGV-2 arrives” forces the order that works. The scheduler's own comment gives the other half of the reason: without the edge, `InitializeEventOrder`'s replay can try to apply AGV-2's arrival while AGV-1 is still on the node, which fails with “two AGVs at the same node” and throws.
- **The `Reduce()` TODO.** The scheduler suspects `GetDependencyCompletionTime`. In the code, a redundant edge only adds one more term to a maximum. What does throw is a dependency that left no motion with its id, for example an `AgvMove` to the pose the AGV is already at (SIPP returns an empty path). `Reduce()` can remove such an edge when it is redundant, which would explain the observation. This is a reading of the code, not a reproduced failure.
- **Waits belong to the next event.** A wait for dependencies carries the id of the event it precedes, so in `Motion` terms an AGV “works on” an event while it waits for it.

### SIPP, the single-AGV search

Safe Interval Path Planning (Phillips and Likhachev, ICRA 2011) searches over *safe intervals* instead of time steps: for each place, the maximal stretches of time during which nothing else is there. An AGV can wait inside one safe interval, so the search only needs one state per (place, interval) pair rather than one per time step.

- **The table.** Each `SippAgv` owns a `SafeIntervalTable`: for each (footprint type, vertex) and (footprint type, edge), an `IntervalSet` of safe times. A missing entry means “always safe”. `AddDeconflictConstraints(motion)` asks the collision table which poses and edges conflict with that motion's footprint and carves the motion's interval out of each, for every footprint this AGV will use.
- **The state.** `SippState` holds the source and target vertex (equal when waiting), the time interval of the move or wait, the index of the goal being worked on, and the number of steps so far.
- **Neighbors.** From a state, each out-edge whose target fits the footprint and is enabled by the static filters is tried. If the edge and its target are safe now, the move is a neighbor; otherwise a wait-then-move neighbor is added for the next safe window. Waits are not chained.
- **Edge time.** A move from rest pays the full trapezoid time from `edge_durations` (the cost model, [section 3.2](#bg-the-cost-model) below). A move that continues the previous one in the same direction (same-direction locomote or strafe, same-sign rotation at a node, same-direction VRC ride) pays only cruise time, `length / speed` (the “run-extension” cost, “Ring 3b” in the comments); this is exact only when the run's first edge reached full speed. Any change among locomote, strafe and rotate adds `agv_wheel_turn` seconds before the move.
- **Goals.** An arrival goal is met only if the AGV can stay at the target *forever* afterwards (the comment explains: otherwise an AGV could “complete” a goal by parking in the path of an already planned event). A lift is a wait goal of `agv_lift_up` or `agv_lift_down` seconds.
- **Search cost is not travel time.** Each move costs its duration plus wheel-turn time plus 3 s × (steps so far) (`kMagicPredecessorCost`); a wait costs half its duration plus the same 3 s × (steps so far). The extra term grows with path length, so A\* prefers short paths in steps even when they arrive later. The heuristic sums all-pairs travel times over the remaining goals.
- **A\* engine.** `SingleSourceSearch` is a generic A\* with a Fibonacci-heap open list and a closed set, capped at 5,000,000 expansions (`kMaxExpansions`). Every other search in this package uses the same function.

## Timing: parameters and the cost model

Every duration in a plan, from an AGV crossing one edge to a bay door closing, comes from one parameter set and one timing model. This section lists what can be configured and then derives the timing model with worked numbers.

### What can be configured

**Two solvers, one usable.** `Chugg` has `SolveSequential` and `SolveCbs`. `SolveCbs` plans sequentially first, then returns `std::nullopt` on any collision; the branching code after that point is unreachable, only handles AGV-against-AGV conflicts, and never re-plans its branches (“TODO (mark): remove this when cbs is done”). No parameter selects between them; `PlanMotions` calls `SolveSequential`.

**ROS parameters.** `SchedulerComponent` reads these into `SchedulerParams`; the motion ones go through `ReadParams` into `cost::MotionCostParams` and from there into the `cost::MotionCostModel` that CHUGG and the single-agent searches use. Linear speeds are m/s and accelerations m/s²; rotation uses rad/s and rad/s²; event times are seconds. The defaults are the struct's initialisers, which its comment says “match the values in launcher/params/params.yaml” (that file is not in the snapshots, so a site may override them).

| ROS parameter                                                  | Field                                             | Default                                                    | Used for                                                                                                                                                                     |
|----------------------------------------------------------------|---------------------------------------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `agv.performance_limits.locomote.{speed, loaded_speed, accel}` | `motion_cost.locomote`                            | 1.0 / 0.8 m/s, 0.2 m/s²                                    | Driving along the heading (`LOCOMOTE` edges)                                                                                                                                 |
| `agv.performance_limits.strafe.*`                              | `motion_cost.strafe`                              | 0.6 / 0.32 m/s, 0.2 m/s²                                   | Sideways moves (`STRAFE` edges)                                                                                                                                              |
| `agv.performance_limits.rotate.*`                              | `motion_cost.rotate`                              | 0.17 / 0.136 rad/s (about 9.7° / 7.8° per s), 0.035 rad/s² | Turning in place (`ROTATION` edges)                                                                                                                                          |
| `vrc.performance_limits.transit.{speed, accel}`                | `motion_cost.vrc_transit`                         | 0.254 m/s, 0.2 m/s² (no loaded speed)                      | Riding a VRC between floors (`VRC_TRANSITION` edges)                                                                                                                         |
| `agv.lift.up_time`, `agv.lift.down_time`                       | `motion_cost.events.agv_lift_up`, `agv_lift_down` | 6.0 s, 5.5 s                                               | SIPP wait goals for lifts; also AGV assignment costs                                                                                                                         |
| `bay.door.close_time`                                          | `motion_cost.events.bay_door_close`               | 4.0 s                                                      | `COMMAND_TYPE_TRANSITION_TO_INSERT`                                                                                                                                          |
| `bay.door.open_time` + `bay.door.wait_to_open_time`            | `bay_door_open` + `bay_wait_to_open`              | 4.0 s + 10.0 s                                             | `COMMAND_TYPE_TRANSITION_TO_RETRIEVE` (the two are added)                                                                                                                    |
| `vecs.transition_time`                                         | `motion_cost.events.vecs_transition`              | 120 s                                                      | Start / stop charging                                                                                                                                                        |
| `vrc.door.open_time`, `close_time`                             | `motion_cost.events.vrc_door_*`                   | 3.0 s each                                                 | Only in the unused VRC event handler and `InsertVrcActionsIntoDag`                                                                                                           |
| `agv.wheel_turn_time`                                          | `motion_cost.events.agv_wheel_turn`               | 1.5 s (“90 deg at 60 deg/s”)                               | Delay when an AGV changes drive mode (three different rules, [section 23.2](#bg-the-cost-model))                                                                             |
| `scheduler.cost_audit`                                         | `SchedulerParams::cost_audit`                     | `true`                                                     | Pass a `cost::CostVector` to `SolveSequential`, which records one row per AGV motion, wheel-turn gap, bay door, VECS and VRC event; logged as CSV. Does not change the plan. |

**Loaded speeds.** CHUGG never uses `loaded_speed`; every planned move is timed as if the AGV were empty ([section 23.2](#bg-the-cost-model) quantifies this).

`scheduler.bay_readiness_ratio` and `layout` are read in the same place but are not motion settings: the first feeds bay rebalancing, the second selects the layout file that `gg_` and `table_` are built from.

**Fixed in code.** These values change plans but are not parameters:

| Constant               | Where                                         | Effect                                                                                   |
|------------------------|-----------------------------------------------|------------------------------------------------------------------------------------------|
| 60 s                   | `PlanEventSequential(BayTransition)`          | Duration of `COMMAND_TYPE_PROCESS_RETRIEVE` (“TODO(someone) make this legit”)            |
| 3 s per step           | `kMagicPredecessorCost`, SIPP                 | Step penalty in SIPP's search cost ([section 21.2](#bg-sipp-the-single-agv-search))      |
| 5,000,000              | `kMaxExpansions`, `SingleSourceSearch`        | Expansion cap for every A\* search; hitting it looks like “no path”                      |
| 30 s per blocking tray | `BlockingTraySearchEnvironment::GetNeighbors` | Trade-off between moving a blocking tray and driving around it (“No more magic numbers”) |
| `TRAY_LEGS` footprint  | VECS and VRC motions                          | Placeholder collision id; neither occupies real space in planning                        |

**Choices made in `PlanMotions`.**

- **The heuristic.** `GetAllPairsMinCost` (Floyd–Warshall, cubic in the number of vertices, recomputed on every `Plan()` call) over the full trapezoid edge times. Because a run of edges costs less than the sum of their trapezoids, this overestimates (20.3 s instead of 11.9 s for three short edges in a line), so SIPP may return paths that are not the fastest. The admissible alternative, `GetEdgeMarginalDurations` (cruise time only, 6.9 s for the same run), exists but is “too loose”, which makes the search slow.
- **The start state.** Everything stands still until `ctx->start_time`. Actions still running from an earlier plan are not in the timeline; instead `Plan()` disables the AGVs, bays, VECS and nodes that `base_schedule` uses ([section 7.5](#ad-persistent-planning-base-schedule-and-the-split)), so CHUGG treats them as static obstacles.
- **The event DAG's shape.** The order CHUGG plans in comes from the DAG, so node-arrival edges, path repair and `Reduce()` are, in effect, how the scheduler steers the planner.

### The cost model: how long a move takes

Every duration in the planner comes from `cost_functions`, which calls itself the “single source of truth for all cost and duration estimates used in motion planning and simulation”. The basic unit is a **trapezoidal velocity profile**: start at rest, accelerate at a up to speed v, cruise, decelerate to rest. Covering a distance d (metres, or radians for a turn) takes

T(d) = \frac{v}{a} + \frac{d}{v} \quad \text{if } d \ge \frac{v^2}{a}, \qquad T(d) = 2\sqrt{\frac{d}{a}} \quad \text{otherwise (a triangle: } v \text{ is never reached)}

(`Trapezoid(distance, vmax, amax)`). The threshold v^2/a is the distance needed to reach full speed and stop again. With the default parameters it is 5.0 m for driving, 1.8 m for strafing, 0.83 rad (47°) for turning and 0.32 m for a VRC. The most common edge in the Pecos layout is 2.29 m long, so **a single driving edge never reaches full speed**: its time is set by acceleration alone.

![Trapezoid profiles and three ways to time a run](figures/94_trapezoid_runs.svg)

Left: the two profile shapes. Right: three 2.29 m driving edges in a straight line, timed three ways with the default parameters. Stopping at every node (the heuristic's assumption) takes 20.3 s; one trapezoid over the whole run (what the AGV does, and what `ConvertPosePathToTrajectory` computes) takes 11.9 s; SIPP's run-extension rule charges 11.3 s, slightly too little, because after a triangular first edge the AGV is not yet at full speed.

**Example durations** (defaults, from `T(d)` above):

| Move                              | Empty                | Loaded | Profile                                           |
|-----------------------------------|----------------------|--------|---------------------------------------------------|
| Drive 2.29 m (one short edge)     | 6.8 s                | 6.8 s  | triangle: the loaded speed limit is never reached |
| Drive 5.79 m (one long edge)      | 10.8 s               | 11.2 s | trapezoid                                         |
| Strafe 2.29 m                     | 6.8 s                | 8.7 s  | trapezoid                                         |
| Turn 90°                          | 14.1 s               | 15.4 s | trapezoid                                         |
| Turn 180°                         | 23.3 s               | 27.0 s | trapezoid                                         |
| Lift up / down, change drive mode | 6.0 s / 5.5 s, 1.5 s |        | fixed                                             |

Turning is slow: a 90° turn takes about as long as driving 9 m. That is why the SIPP step penalty and the wheel-turn delay both push the planner towards paths with fewer, straighter moves.

**Runs.** `CoalesceMotionRuns` groups consecutive edges of one path into `MotionRun`s that the AGV executes without stopping: same transition type and same direction (driving or strafing within about 0.6°), same-sign rotation at one node, or the same VRC moving in the same vertical direction. A run is timed as one trapezoid over its total length, and `TimeAtDistance` slices that time back into per-edge intervals so collision checks at intermediate nodes stay exact.

**Three estimates of the same path.** The same physics is approximated differently in three places:

| Where                                                        | Rule                                                                                    | Three 2.29 m edges | Consequence                                                                                                                                        |
|--------------------------------------------------------------|-----------------------------------------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `GetEdgeDurations` → `GetAllPairsMinCost` (SIPP's heuristic) | one full trapezoid per edge, as if stopping at every node                               | 20.3 s             | overestimates straight runs (by 70 % here, more for longer runs): the heuristic is inadmissible, so SIPP can return paths that are not the fastest |
| SIPP's edge cost (“Ring 3b”)                                 | full trapezoid for an edge from rest, `length / speed` for an edge that continues a run | 11.3 s             | exact when the first edge reaches full speed; slightly short when it does not, which is the common case for driving here                           |
| `ConvertPosePathToTrajectory`                                | one trapezoid per `MotionRun`, sliced with `TimeAtDistance`                             | 11.9 s             | matches the motion profile; used for AGV assignment costs                                                                                          |
| `GetEdgeMarginalDurations` (unused alternative)              | `length / speed` for every edge                                                         | 6.9 s              | never overestimates, but is too far below the truth to guide the search well                                                                       |

**Loaded speeds are not used by CHUGG.** `MotionCostModel::Duration(transition, is_agv_loaded = false)` defaults to empty, and `GetEdgeDurations` does not pass the flag; SIPP's run-extension cost also reads `speed`, never `loaded_speed`. So every move in the plan is timed as if the AGV were empty. From the table above, a loaded strafe takes 28 % longer than planned and a loaded 180° turn 16 % longer; short driving edges are unaffected because they never reach either speed limit. Only `ConvertPosePathToTrajectory(..., is_agv_loaded)` uses the loaded speeds. Execution stays safe because the ADG keeps the order, not the times (see the [Action graph](#doc-action-graph) tab), but the plan's timing, and with it which of two conflicting AGVs SIPP lets go first, is based on optimistic durations.

**Three wheel-turn rules.** The drive wheels must be reoriented when an AGV changes between driving, strafing and turning, and the code charges for it in three different ways:

| Where                                            | Charged on                                                                                                                                  |
|--------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `SippEnvironment` (CHUGG)                        | any change among locomote, strafe and rotate                                                                                                |
| `MotionCostModel::WheelTurnDuration`             | only changes to or from locomote; strafe ↔ rotate is free (“5 degree turn … essentially no cost”). Not called by any code in the snapshots. |
| `ConvertPosePathToTrajectory` (assignment costs) | never                                                                                                                                       |

So CHUGG charges 1.5 s for a strafe-then-turn that the cost model says is free, and the assignment stage ignores wheel turns entirely. Each difference is small, but they add up along paths with many mode changes, and they make the assignment cost and CHUGG's timing disagree in a consistent direction. A refactor that moves cost estimation behind one interface would be the natural place to pick one rule.

## `ContinuousState`: the timeline CHUGG reads and writes

“Continuous” refers to time, not space. A `DiscreteGarageState` is one snapshot: where every AGV, tray, bay, VECS and VRC is *now*. A `ContinuousState` is a `Trajectory` per entity (a `std::unordered_map<GarageEntityIdMsg, Trajectory>`), and a trajectory is a time-ordered `std::set` of `Motion`s that may not overlap (`AddMotion` returns `false` if one would; why a set, and what it implies, is in [section 4.1](#mp-why-trajectory-is-a-set)). Times are `std::chrono::system_clock` time points.

![ContinuousState, Trajectory and Motion](figures/102_uml_timeline_data.svg)

**The timeline types.** A `ContinuousState` owns one `Trajectory` per entity; a `Trajectory` owns its `Motion`s in a `std::set` ordered by start time; a `Motion` owns an `Interval`, a location (a pose or an edge) and, for motions that change something, a serialized `DiscreteGarageEventMsg`. The scheduler later merges all trajectories into one set with a full tie-break to build the action DAG.

**What a `Motion` is.** An entity, an `Interval`, a footprint (`collision_id`), an `action_id`, a location (a `Pose` or an `Edge` of two poses), and optionally a *delta*, the serialized discrete change it causes. The constructor decides which:

| Constructed with                                                  | Location                                               | Delta                                 | `IsIdle()`                                                        |
|-------------------------------------------------------------------|--------------------------------------------------------|---------------------------------------|-------------------------------------------------------------------|
| a `Pose`                                                          | that pose                                              | none                                  | true: a plain wait                                                |
| an `Edge` or an `AgvPoseChangedMsg`                               | the edge                                               | `AgvPoseChanged`, built from the edge | false                                                             |
| `AgvLiftChangedMsg` and a pose                                    | the pose                                               | `AgvLiftChanged`                      | false                                                             |
| `BayStateChangedMsg`, `VecsStateChangedMsg`, `VrcStateChangedMsg` | a pseudo-pose whose node id is the bay / VECS / VRC id | that message                          | true if the state does not change (an idle bay still has a delta) |

![ContinuousState as a timeline](figures/92_continuous_state.svg)

The `ContinuousStateToSchedule` test drawn as swimlanes. AGV-2 waits at node 6 until AGV-1 has passed through node 9. In the action DAG the wait disappears (it changes nothing) and becomes an occupancy edge instead: AGV-2's move into 9 depends on AGV-1's move out of it. This is how an ADG keeps the plan's safety without its timing.

**Its life in one `Plan()` call:**

1.  **Built from the snapshot.** The constructor gives every AGV, bay, VECS and VRC, and every *placed* tray, one stationary motion from the beginning of time (`Timepoint::min()`) to `start_time` (or `system_clock::now()` if none is given), with the placeholder action id 999999. A tray on an AGV has no trajectory; the AGV's footprint covers it. VECS and VRCs use the `TRAY_LEGS` footprint as a placeholder.
2.  **Read by CHUGG.** `GetEndState()` replays every delta in order of end time to get the state after the initial trajectories; every initial motion becomes a reservation in the AGVs' safe-interval tables. The `ContinuousState` is the record of the plan; the `SafeIntervalTable`s derived from it are what SIPP searches.
3.  **Extended by CHUGG.** The new motions are planned in a separate per-entity map and appended to a copy of the initial state at the end (`GetUpdatedContinuousState`).
4.  **Read by the response code.** `CollectAndCollapseTrajectoryMotions` walks `GetTrajectories()`, drops motions without a delta and idle ones, merges consecutive floor-traversal motions of a VRC ride into one, and orders everything with `MotionScheduleOrder` (start time, then action id). `BuildActionDagFromMotions` turns each remaining motion into an `ActionNode`; `GetActionId()` is cast back to a `ScheduleEventDag::Vertex` to find the event and therefore the job.
5.  **Thrown away.** Only `Schedule.nodes` leaves the scheduler; the times survive only as each `ActionNode.duration`.

Tests skip CHUGG and write the state by hand, which shows the whole API the scheduler needs:

``` cpp
// scheduler_tests.cpp, TEST(Scheduler, ContinuousStateToSchedule), abridged
volley::ContinuousState cont_state(state, scheduler.GetCollisionTable(), *(scheduler.GetLayout()));
Trajectory a1_traj;
Interval::Timepoint start_time {};
a1_traj.AddMotion(Motion(volley::AgvId(1), Interval(start_time, 3s),              // [0 s, 3 s]
    common::EnumInteger(volley::CollisionEntityId::AGV),                          // bare AGV footprint
    0u,                                                                           // event vertex 0
    volley::CollisionTable::Edge {ConstructGaragePose(10, 0), ConstructGaragePose(9, 0)}));
// a waiting motion: a single pose instead of an edge, so no delta
a2_traj.AddMotion(Motion(volley::AgvId(2), Interval(start_time, 6s),
    common::EnumInteger(volley::CollisionEntityId::AGV), 1u, ConstructGaragePose(6, 0)));
cont_state.SetTrajectory(volley::AgvId(1u), a1_traj);
cont_state.SetTrajectory(volley::AgvId(2u), a2_traj);
auto [action_nodes_opt, message] = scheduler.ResponseFromTrajectories(ctx, cont_state);
```

Two details worth knowing. The test's comment calls the fourth argument `JobId`, but everywhere in CHUGG and the response code it is the event's vertex in the event DAG; with one event per job in this test the two coincide. And because a `Motion` stores the footprint (`GetCollisionId()`), the response code can tell a loaded AGV from an empty one without replaying the discrete state.

### Why a `Trajectory` is a `std::set`, and the alternative

A trajectory is naturally an ordered list of motions, and it is stored as one: `std::set` is an *ordered* container (a balanced binary tree, usually red-black), not a hash set. Iterating a `std::set<Motion>` visits the motions in the order given by `Motion::operator<`, and that operator compares start times only:

``` cpp
// trajectory.hpp
bool operator<(const Motion& other) const { return interval_.Before(other.GetInterval()); }
// interval.hpp
bool Before(const Interval& other) const { return begin_ < other.begin_; }
bool StrictlyBefore(const Interval& other) const { return end_ <= other.begin_; }
```

So time is the ordering key, as it should be. What the set adds, and what it does not, follows from that key:

- **Uniqueness means one motion per start time.** A set treats two elements as the same when neither is less than the other. Two motions that start at the same instant are therefore one key, whatever else differs; a `Trajectory` can hold only one of them. `Motion::operator==` compares every field, but the set never uses it: `RemoveMotion(m)` erases whichever stored motion starts when `m` starts.
- **No overlap is a rule of `AddMotion`, not of the set.** `AddMotion` uses `lower_bound` to find the first motion starting at or after the new one, and accepts the new motion only if it ends no later than that motion starts and starts no earlier than the previous one ends. Touching is allowed (`end_ <= begin_`), so consecutive motions abut. Anything else returns `false` and stores nothing.
- **The return value is ignored.** Every `AddMotion` call in CHUGG, in `SippAgv::SolutionToTrajectory` and in `GetUpdatedContinuousState` discards the `bool`. If a bug ever produced an overlapping motion, it would disappear from the plan without an error; the final `CheckCollisions` would not notice, because the motion is no longer there.
- **Zero-length motions are avoided on purpose.** `SolutionToTrajectory` skips SIPP states of zero duration. A zero-length motion at time *t* would block any other motion starting at *t* (the same key), which is the case step 4 of the figure shows.

![How a Trajectory stores its motions](figures/104_trajectory_storage.svg)

**How a `Trajectory` stores its motions.** Step through three `AddMotion` calls on one AGV's trajectory, shown as a timeline, as today's `std::set` tree and as a sorted `std::vector`: an append (the only case CHUGG uses), an overlapping motion that is refused, and a second motion at the same start time, also refused. The last step highlights how the code uses a trajectory.

**How the code uses a trajectory.** The tree's strengths are cheap inserts anywhere, an automatic order whatever the insertion order, and iterators that survive inserts and erases. The code uses none of them:

| Operation                       | Where                                                                                                                                                                                             | `std::set` today                        | Sorted `std::vector` |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|----------------------|
| Append after the last motion    | Every `AddMotion` in the sequential solver: each entity's time only moves forward, and the one edit (a tray's open-ended parked motion shortened at pick-up) removes and re-adds the last element | O(log n) plus one allocation            | Amortised O(1)       |
| Insert in the middle            | Nowhere in the sequential solver                                                                                                                                                                  | O(log n)                                | O(n) shift           |
| Last (or first) motion          | `SetEventSafeIntervals`, lifts, `GetInterval`, `MakeRootNode`                                                                                                                                     | `rbegin()`, `begin()`                   | `back()`, `front()`  |
| All motions in time order       | Deconfliction, collision checks, the response code, logging                                                                                                                                       | In-order walk                           | Linear scan          |
| The motion of a given event     | `GetDependencyCompletionTime`                                                                                                                                                                     | Linear scan                             | Linear scan          |
| Access by position              | `CoalesceTrajectory` (copies the set into a `std::vector` first)                                                                                                                                  | Not available                           | Direct               |
| Motions overlapping an interval | `FindInInterval`, `RemoveInInterval` (no callers in the snapshots)                                                                                                                                | Linear `find_if` (the tree is not used) | Binary search        |
| Copy                            | Initial state into every result, the result out of `PlanMotions` and again in `Plan()`                                                                                                            | One allocation per motion               | One allocation       |

The API (`FindInInterval`, `RemoveInInterval`, `RemoveMotion(iterator)`) and the landmark goals of `SippAgv` suggest the type was designed for editing trajectories in the middle, as the unfinished CBS solver would. In the code that runs, a trajectory is built front to back and read front to back, which is the access pattern of a `std::vector`. A `std::list` would add nothing: it keeps the iterator stability of the set, which nothing needs, and loses both binary search and indexing.

**Recommendation.** Keep `Trajectory`'s interface and change its storage to a `std::vector<Motion>` kept sorted by start time:

- `AddMotion` appends when the new motion starts at or after the last one ends, and otherwise binary-searches the insert position (`std::upper_bound` on the start time) with the same overlap check. Mark it `[[nodiscard]]`, so callers either handle a refusal or say why they ignore it.
- Decide the rule for equal start times explicitly (for example: allowed only when the earlier motion has zero length), instead of inheriting it from the set's equivalence.
- Add `Front()`, `Back()` and `Size()`, so `rbegin()` / `rend()` (already marked “get rid of these eventually”) can go; `begin()` / `end()` stay, so range-`for` loops in the scheduler do not change.
- Rewrite `FindInInterval` with `std::partition_point`, or delete it with `RemoveInInterval` if nothing needs them.

The change is local to `motion_planner` and renames nothing. The gain is clarity and fewer surprises, more than speed: trajectories are short, and SIPP dominates CHUGG's run time. It is worth doing before other solvers start filling trajectories ([section 15.6](#pr-motion-decisions)), and the parity tests of the refactor cover it, because the motion order does not change.

## The code: classes and the call sequence

The previous sections describe what CHUGG does. This section shows how the code is organised: which classes exist, who owns what, and the order of calls in one `PlanMotions` call. Read it with `chugg_sequential.cpp` open; the diagrams are abridged but use the real names.

### Where the classes live

All of it is in the `motion_planner` package, namespace `volley`. For motion planning the scheduler includes `chugg.hpp` and `garage_graph_pathing.hpp`, plus `continuous_state.hpp`, `trajectory.hpp` and `interval.hpp` to read the result; task planning includes the search headers (`blocking_tray_search.hpp`, `agv_hiding_search.hpp`, `static_graph_filtering.hpp`).

| Header                                                                             | Main types and functions                                                          | Role in a plan call                                                                                     |
|------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `chugg.hpp` (sources: `chugg_common.cpp`, `chugg_sequential.cpp`, `chugg_cbs.cpp`) | `Chugg`, `Chugg::Node`                                                            | The multi-agent planner: event order, setup, the per-event loop. `chugg_cbs.cpp` is never reached.      |
| `sipp_agv.hpp`                                                                     | `SippAgv`                                                                         | One AGV's planner: its goals, its safe-interval table, and the conversion from SIPP states to `Motion`s |
| `safe_interval_path_planning.hpp`                                                  | `SippState`, `SippGoal`, `SippEnvironment`                                        | The SIPP search problem: states, goals, neighbours, heuristic                                           |
| `path_search.hpp`                                                                  | `SearchEnvironment<State, Cost>`, `SingleSourceSearch`, `SearchSolution`          | The generic A\* used by SIPP and by the single-agent searches of task planning                          |
| `safe_interval_table.hpp`, `interval.hpp`                                          | `SafeIntervalTable`, `IntervalSet`, `Interval`                                    | When each vertex and edge is safe, per footprint type                                                   |
| `static_graph_filtering.hpp`                                                       | `GraphFilterProperties`, `GetAllStaticFilters`                                    | Vertices and edges blocked for the whole plan                                                           |
| `continuous_state.hpp`, `trajectory.hpp`                                           | `ContinuousState`, `Trajectory`, `Motion`                                         | The timeline CHUGG reads and returns ([section 4](#bg-continuousstate-the-timeline))                    |
| `garage_graph_pathing.hpp`                                                         | `GetEdgeDurations`, `GetAllPairsMinCost`, `GarageGraphEnvironment`, `GetPosePath` | The per-call inputs (edge times, heuristic table) and plain shortest paths                              |

### CHUGG and its collaborators

The classes listed above meet in one object, `Chugg`, which a single `PlanMotions` call creates and discards. The figure shows what `Chugg` holds and how it reaches the per-AGV planners; the notes after it explain the ownership and lifetime rules that a refactor has to respect.

![CHUGG and its collaborators](figures/100_uml_chugg_classes.svg)

**CHUGG and its collaborators.** `Scheduler::PlanMotions` creates the initial `ContinuousState` and a `Chugg`, then calls `SolveSequential`. `Chugg` holds its seven inputs by const reference, keeps the event order and the static filters (`constraints_`), and plans into one `Chugg::Node`: the new motions per entity and one `SippAgv` per movable AGV. Grey members belong to the unfinished CBS solver.

- **Ownership is by reference, lifetime by scope.** `Chugg`, every `SippAgv` and every `SippEnvironment` hold const references to the graph, collision table, cost model and the two per-call tables. That is safe because `PlanMotions` creates all of them as locals and `Chugg` lives only for that call; any refactor that keeps a planner longer must keep its inputs alive too.
- **`Chugg::Node` is a CBS search node used by the sequential solver.** The header says so (“Node is really for CBS, but it is used in the sequential planning functions because it was convenient”). It holds the plan being built: `trajectories` (new motions only) and `planners`. Its cost fields (`makespan`, `flowtime`) are computed but never read by the sequential path.
- **Each `SippAgv` carries its AGV's whole view of the world.** Its `sit_` holds every reservation made by other entities so far, and its goal list holds every AgvMove and TrayMove of that AGV in order. `PlanEvents` plans one of those goals at a time.
- **Five overloads, one loop.** `PlanNodeSequential` casts each event to its concrete type and calls the matching `PlanEventSequential` overload; there are overloads for AgvMove, TrayMove, BayTransition, VecsTransition and VrcTransition, and the loop has no branch for the last one.

### The search classes: SIPP on a generic A\*

Each `SippAgv` plans with SIPP, which in this code is one instance of a generic A\* search rather than a separate algorithm. The figure shows the search template, the two environments that implement it and the safe-interval table that SIPP reads; the notes explain how these pieces are bound together and what survives a search.

![SIPP and the generic A\* search](figures/101_uml_sipp_classes.svg)

**SIPP and the generic A\* search.** `SingleSourceSearch` is one A\* function template that calls back into a `SearchEnvironment`. `SippEnvironment` implements it for `SippState` (a move or wait with its time interval and goal index) and reads the AGV's `SafeIntervalTable`, which keeps an `IntervalSet` of safe times per footprint and vertex or edge. `GarageGraphEnvironment` is the second implementation, for plain shortest paths.

- **Strategy by template, not by virtual call.** `SingleSourceSearch` is a template over the environment type, so the A\* loop is compiled once per environment and the callbacks can be inlined; `SearchEnvironment`'s virtual functions document the contract and are checked with a `static_assert`.
- **The environment is rebuilt for each event.** `PlanEvents` constructs a `SippEnvironment` over references to the current goals and table, runs the search, and discards it. Nothing about a search survives except the motions it returns.
- **Safety is stored per footprint.** The table key is (footprint type, vertex) or (footprint type, edge). A bare AGV and an AGV carrying a large tray conflict with different places, so carving one motion touches every footprint the AGV will use (`all_collision_ids_`).

### One `PlanMotions` call, call by call

With the classes in place, this subsection follows the order of calls in a single `PlanMotions` call, from building the inputs to the final collision check. The figure gives the sequence step by step, and the abridged code after it shows the same calls in `SolveSequential` and in the `AgvMove` overload of `PlanEventSequential`.

![One PlanMotions call, call by call](figures/103_seq_plan_motions.svg)

**One `PlanMotions` call.** Step through it: the scheduler builds the inputs; `SolveSequential` sets up the static filters and one `SippAgv` per AGV, carving every existing motion into the other AGVs' tables; the loop then plans each event (SIPP for AGV events, a fixed duration for bays and VECS) and carves the result into everyone else; a pairwise collision check closes the call.

The same sequence in code, abridged to the calls the figure shows:

``` cpp
// chugg_sequential.cpp, abridged
std::optional<ContinuousState> Chugg::SolveSequential(cost::CostVector* audit) {
  SolveInitialization();                       // movable AGVs, planning_start_, constraints_
  Node solution_node = MakeRootNode();         // one SippAgv per AGV, initial reservations, goals
  if(!PlanNodeSequential(solution_node)) return std::nullopt;
  if(!ContinuousState::CheckCollisions(solution_node.trajectories, geometry_).empty()) return std::nullopt;
  return GetUpdatedContinuousState(solution_node);   // initial state + new motions
}

// PlanEventSequential(AgvMove), abridged
initial_time = max(EntityCurrentTime(node, agv), GetDependencyCompletionTime(node, event_id));
auto orig_sit = SetEventSafeIntervals(node, working_state, agv_id, tray_id);   // copy, then freeze others
auto traj_segment = node.planners.at(agv_id).PlanEvents({event_id}, agv_state, initial_time, constraints_);
node.planners.at(agv_id).SetSafeIntervalTable(std::move(orig_sit));            // restore
for(auto& motion : *traj_segment) {
  node.trajectories[agv_ent].AddMotion(motion);
  DeconflictAgvs(node, motion);                // carve into every other AGV's table
}
```

### What the structure means for a refactor

The class structure and call sequence above have consequences for running time, failure handling and the types a refactor inherits. The points below identify work that grows with the size of the plan, work that could be done once per layout, and code that exists only for the unfinished CBS solver.

- **Per-event work grows with the plan.** For every AGV or tray event, `SetEventSafeIntervals` copies the AGV's whole `SafeIntervalTable`, carves in *every* motion of every other entity planned so far (most of which `DeconflictAgvs` has already carved), and the table is copied back afterwards: `SetSafeIntervalTable(SafeIntervalTable&& sit)` assigns `sit_ = sit`, which copies, because a named rvalue reference is an lvalue. The total work is roughly quadratic in the number of motions. Carving only the resting motions, and `sit_ = std::move(sit)`, are small changes to measure with the benchmarks.
- **The heuristic table does not depend on the request.** `GetAllPairsMinCost` runs Floyd–Warshall over the whole graph on every call ([section 3.2](#bg-the-cost-model)), although its inputs are only the graph and the cost model. It can be computed once when the layout or parameters change, like `gg_` and `table_`.
- **Looking up an event's motions is a scan.** `GetDependencyCompletionTime` walks each dependency's whole trajectory to find motions with that event's id. A map from event id to its last motion's end time, filled when motions are committed, makes it constant time and gives the response code the same lookup.
- **Failures take two routes.** An infeasible event returns `false` and ends as `std::nullopt`; an inconsistent DAG throws `std::logic_error` from the constructor or the loop. A solver interface ([section 15.2](#pr-the-motion-solver-interface)) should return both as errors with the event that failed.
- **The CBS code shapes the types.** `Node`, landmark goals, avoid constraints and the editing functions of `Trajectory` exist for CBS. If CBS is pursued, they are its starting point; if not, removing them makes the sequential solver's types match what it does.

## The single-agent searches and static filters

CHUGG is the only *multi-agent* planner in `motion_planner`, but it is not the only search. While task planning builds the event DAG (Task planning tab), it calls smaller searches from the same package: to time an AGV's drive, to find the trays in a tray's way, to find a free parking spot or an empty tray, and to send every AGV under a tray before a clean-up. All of them plan for one AGV or one tray at a time, see the garage as a fixed snapshot, and ignore when anything else moves. This section explains how they are built and then each one in turn; the Task planning tab links here wherever a scheduler method calls one of them.

Four terms are used throughout. They name parts of one design, shown as a class diagram in [section 7.1](#mp-search-class-design):

**The search engine: `SingleSourceSearch`**  
One C++ function template, `SingleSourceSearch<State, Cost, Env>(source, init_cost, env)` in `path_search.hpp`. It is an A\* search: it keeps an open set of states ordered by cost, repeatedly takes the cheapest, and returns a `SearchSolution` holding the predecessor of every state it reached. It knows nothing about garages, trays or AGVs. Everything problem-specific comes from the third argument.

**A search environment**  
A class derived from the abstract template `SearchEnvironment<State, Cost>` that defines one search problem. It fixes the *state* type (what one node of the search is: a graph vertex, a vertex plus the trays crossed, a pose, or a SIPP state with a time interval) and implements three callbacks the engine calls: `GetNeighbors(state)` returns the states reachable in one step and the cost of each step; `OnExpansion(state, g, meta)` is called when a state is taken from the open set and returns `true` to stop the search, so it is the goal test; `GetHeuristic(state)` estimates the remaining cost (zero in every search used by task planning). An environment holds references to the data it needs (the garage graph, the collision table, the garage state, the cost model) and, usually, a static filter. There are six: `GarageGraphEnvironment`, `BlockingTraySearchEnvironment` and its subclasses `OpenSpaceSearchEnvironment` and `EmptyTraySearchEnvironment`, `AgvSearchEnvironment`, and `SippEnvironment` (CHUGG's, [section 3.2](#bg-sipp-the-single-agv-search)).

**A search function**  
A free function that answers one question by building an environment, running the engine on it and converting the result into what the caller wants. `GetPosePath` builds a `GarageGraphEnvironment` and returns a vector of poses; `HideAgvs` builds one `AgvSearchEnvironment` per AGV and returns a pose per AGV. The three tray environments have no wrapper: scheduler methods such as `AssignTrayIdForEmptyMove` construct the environment and call `SingleSourceSearch` themselves, then read the target and the tray set from the solution.

**A static filter**  
A `GraphFilterProperties` object: two boolean masks, one over the graph's vertices and one over its edges, saying where a given footprint may go in a given garage state. `GetStaticFilter` builds one; an environment tests it in `GetNeighbors` before offering a step ([section 7.4](#mp-static-filters)).

![The single-agent searches in motion_planner](figures/140_search_toolbox.svg)

**The single-agent searches.** Read left to right: the scheduler method, the search function it calls, the environment that gives the search its goal and step cost, and the engine every environment runs on. `GetStaticFilter` supplies each search with the poses and edges it may use.

Three properties hold for all of them, and they explain most of what follows:

- **Static.** A search sees the garage as one `DiscreteGarageState`. Other AGVs neither move nor wait during the search; only CHUGG, after task planning, discovers waiting ([section 3](#bg-chugg-the-motion-planner)).
- **Uninformed.** Every environment used by task planning returns a heuristic of zero, so the engine runs as Dijkstra's algorithm: states are closed in order of their cost from the source. `BlockingTraySearchEnvironment` carries a TODO to add a distance heuristic.
- **The environment is the algorithm.** The engine only orders the work. What a state is, what a step costs and when the search stops are all decided by the environment object passed in.

### The class design: engine, environments and states

The searches form a small class hierarchy around one abstract template. The diagram shows every environment, the state type each binds, the subclass relation between the three tray environments, and the objects the engine returns; a second diagram in [section 7.4](#mp-static-filters) shows the filter functions.

![Engine, environments and states (UML)](figures/145_uml_search_environments.svg)

**Engine, environments and states.** Each concrete environment realises `SearchEnvironment<State, Cost>` with its own state type; the cost is always `Interval::Duration`. `OpenSpaceSearchEnvironment` and `EmptyTraySearchEnvironment` inherit from `BlockingTraySearchEnvironment`. `SingleSourceSearch` calls back into whichever environment it is given and returns a `SearchSolution`. `SippEnvironment` is shown in outline; its own diagram is [Figure 101](#mp-fig-101_uml_sipp_classes).

The template parameters are abstract in the diagram. The figure below fills them in: for each environment, the concrete `State` type, one example state on the Pecos layout, one entry that `GetNeighbors` returns, and what makes two states equal. `Cost` is the same type in all of them.

![State and Cost, environment by environment](figures/147_state_and_cost.svg)

**State and Cost, environment by environment.** `Cost` is always `Interval::Duration`, a `std::chrono` duration, and the engine adds step costs to get *g*. `State` differs: a bare vertex index for `GarageGraphEnvironment`, a vertex with the set of trays crossed for the tray searches, a ROS pose message for `AgvSearchEnvironment`, and a move or wait with its time interval for SIPP. The last column matters as much as the type: it decides when the engine treats two states as one.

The design intent, as the code expresses it:

- **Strategy, bound at compile time.** The search algorithm is written once and the problem is plugged in. `SingleSourceSearch` takes the environment as a template parameter, so the A\* loop is compiled separately for each environment and its callbacks can be inlined; the pure virtual functions of `SearchEnvironment` document and enforce the contract, checked by a `static_assert`. Adding a new kind of search means writing one environment class, not another search loop.
- **The state type decides what "the same node" is.** The engine deduplicates states through `std::hash<State>` and `operator==`. `GarageGraphEnvironment` searches over plain vertices; `AgvSearchEnvironment` over poses; `SippEnvironment` over (move, time interval, goal index) so that the same place at different times is different; `BlockingTrayState` carries the trays crossed but hashes and compares only its vertex, deliberately collapsing routes that differ only in which trays they cross (the comment: "We have no preferences for which blocking tray to move at this point").
- **Subclassing for a shared cost model.** The three tray searches must agree on what a route costs, so the cost lives in one place, `BlockingTraySearchEnvironment::GetNeighbors`, and the subclasses override only `OnExpansion` (and restate the zero heuristic). Protected getters give them read access to the graph, table and state. `EmptyTraySearchEnvironment` adds no members at all.
- **The goal test doubles as a visitor.** `OnExpansion` sees every state in cost order, so `AgvSearchEnvironment` uses it to record every tray pose and always returns `false`: the search then runs to exhaustion and the environment's list is the answer. The optional hooks (`OnDiscovery`, `OnUpdate`, `OnTermination`) exist for the same kind of instrumentation; no task-planning environment uses them.
- **Cheap, short-lived objects.** Environments hold `const` references to the graph, collision table, garage state and cost model, and a copy of the filter. Building one is cheap, it is discarded after one search, and the referenced objects must outlive it. The tray and AGV environments delete copy and move to make the one-object-per-search use explicit.
- **Where the design is thin.** Results come back in two shapes: the engine's `SearchSolution`, which callers unpack themselves, or a side list inside the environment (`GetSortedDestinations`). The tray environments read the tray set out of the target state, which is the first-found set ([section 7.5](#mp-tray-searches)). A refactor that adds a typed result per search, as proposed for tray and AGV assignment, would make these contracts explicit.

### Who calls which search

The table maps each search to the scheduler methods that call it. The subsections below take the searches in the order a reader needs them: the engine, the filter, the tray searches, the AGV path search and the hiding search.

| Search function and environment                                                 | Answers                                                                             | Called from (scheduler)                                                                                                              | Explained in                      |
|---------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------|
| `GetPosePath` with `GarageGraphEnvironment`, then `ConvertPosePathToTrajectory` | The quickest pose path for one AGV over the filtered graph, then its timing         | `GetJustMovingCost` (AGV assignment costs), `IsMovePossible`, `MoveAgvToTrayPose`, `TryClearBlockedAgvMove`, `InitRetrievalHeadings` | [section 7.5](#mp-pose-path)      |
| `SingleSourceSearch` with `BlockingTraySearchEnvironment`                       | The cheapest route for a tray to a target pose, and the trays on it                 | `DoTrayAssignments` (the blocking-tray loop)                                                                                         | [section 7.4](#mp-tray-searches)  |
| `SingleSourceSearch` with `OpenSpaceSearchEnvironment`                          | The nearest free parking or EV-charge node a tray fits, optionally a waypoint stash | `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution` (blocking-tray resolution, reparking, EV charging)                       | [section 7.4](#mp-tray-searches)  |
| `SingleSourceSearch` with `EmptyTraySearchEnvironment`                          | The empty tray cheapest to bring to a pose                                          | `AssignTrayIdForEmptyMove`                                                                                                           | [section 7.4](#mp-tray-searches)  |
| `HideAgvs` with `AgvSearchEnvironment`                                          | A pose under a tray for every enabled AGV                                           | `PlanCleanGarageJob`                                                                                                                 | [section 7.6](#mp-hide-agvs)      |
| `GetStaticFilter`, `GetAllStaticFilters`, `GetDisabledEntitiesFilters`          | Which poses and edges a footprint may use                                           | All of the above; `ctx->disabledness_filters`; CHUGG's static obstacles                                                              | [section 7.3](#mp-static-filters) |

### `SingleSourceSearch`: the shared engine

Every search in the package, SIPP included ([section 3.2](#bg-sipp-the-single-agv-search)), is one call to the function template `SingleSourceSearch(source, init_cost, env)` in `path_search.hpp`. It is a textbook A\*; with the zero heuristic used by every scheduler search it behaves as Dijkstra's algorithm. The figure runs it on a six-node graph so that each callback into the environment is visible.

![SingleSourceSearch step by step](figures/141_single_source_search.svg)

**`SingleSourceSearch`, step by step.** Step through the search from S. Each step pops the cheapest open node, asks `OnExpansion` whether it is a goal, closes it and asks `GetNeighbors` for its neighbors. At the second step, A is reached more cheaply through B (3 instead of 4), so its cost and predecessor are updated. The search stops when the goal G is popped; C and D are never expanded. The highlighted lines on the right are the code that runs at each step.

**About the name.** "Single source" is the standard graph-algorithm term: the search grows from one source state, as in "single-source shortest paths" (Dijkstra's algorithm). It says nothing about agents. A name such as `SingleAgentSearch` would mislead in the other direction, because the engine does not know what an agent is: it searches tray states, poses and SIPP time intervals alike. If the function is renamed, a name for the algorithm fits best, for example `AStarSearch` or `BestFirstSearch`, with the result type renamed to match. The function lives in `motion_planner`, outside the packages this refactor renames (`scheduler` and `planner_core`), so the rename belongs to later work on that package.

How the engine works:

- **The contract.** An environment derives from `SearchEnvironment<State, Cost>` and implements three callbacks: `OnExpansion(state, g, meta)` returns `true` to stop (this is the goal test); `GetNeighbors(state)` returns the next states with the cost of each step; `GetHeuristic(state)` estimates the cost to go. `OnDiscovery`, `OnUpdate` and `OnTermination` are optional hooks. A `static_assert` checks the base class; the template is compiled once per environment type.
- **The open set** is a Boost Fibonacci heap ordered by *f* = *g* + heuristic, ties broken towards the larger *g*. A second map from state to heap handle lets the engine find a state already in the open set and lower its cost in place (decrease key).
- **One map is both the closed set and the result.** `predecessors` maps each state reached to (predecessor, cost of the last step, closed flag). A closed neighbor is skipped. The source is its own predecessor, which is how `SearchSolution::GetPath(goal)` knows where to stop when it walks the map backwards.
- **Two ways to end.** If `OnExpansion` returns `true`, the result carries that state as `target`. If the open set runs empty, or after 5,000,000 expansions (`kMaxExpansions`), the result has no target, and the caller must ask `GetPath` for the state it wanted. Hitting the expansion cap is not reported separately: it looks the same as "not found".
- **What "the same state" means is the state type's choice.** The maps use the state's `std::hash` and `operator==`. `BlockingTrayState`, for example, hashes and compares only its vertex, so two routes to one vertex with different trays crossed are one state ([section 7.4](#mp-tray-searches)).

### Static filters: `GetStaticFilter` and `GraphFilterProperties`

A search must know which places it may not enter: a parked tray, another AGV, a bay with its overdrive plate in the way, a closed node. The package never edits the graph for this. Instead, `GetStaticFilter` builds a `GraphFilterProperties`: two boolean masks, one over the graph's vertices (poses) and one over its edges, true where the footprint fits. One filter is built per footprint type, because a bare AGV, an empty tray and a tray carrying a large car conflict with different places.

![GetStaticFilter source by source](figures/142_static_filter.svg)

**`GetStaticFilter`, source by source.** Step through the four passes for a TRAY footprint: parked trays (except the ignored, moving tray T17), AGVs, a bay that is not ready to retrieve, and a disabled node. Each pass switches off the poses and edges where a tray would overlap something; the last step shows the resulting vertex mask. Rectangles stand in for the CollisionTable's real footprints.

The filter is produced by three free functions and read in four places. The diagram shows who calls whom, what the functions read and where each kind of filter is stored:

![Static filters: functions, data and consumers (UML)](figures/146_uml_static_filters.svg)

**Static filters: functions, data and consumers.** `GetDisabledEntitiesFilters` calls `GetAllStaticFilters`, which calls `GetStaticFilter` once per footprint type; each call reads the garage graph, the garage state and the collision table and creates one `GraphFilterProperties`. The scheduler stores the disabled-entity map in `ScheduleContext::disabledness_filters`; CHUGG stores its map as `constraints_` and hands it to every `SippEnvironment`; the task-planning environments hold a copy of one filter.

The rules of `GetStaticFilter`, in the order of the code:

1.  **Parked trays.** For every tray not in `ignore_trays`, `CollisionTable::Query(tray footprint, collision_id, tray pose)` returns the poses and edges where this footprint would overlap the tray, and all of them are switched off. For an AGV footprint the tray counts only with its legs (`TRAY_LEGS`), so an AGV may drive under parked trays.
2.  **AGVs.** Every AGV not in `ignore_agvs` switches off the places where it would collide with this footprint. For a payload footprint the query uses `TRAY`, because an AGV meets a tray's outer frame before its payload.
3.  **Bays.** A bay that is not `READY_TO_RETRIEVE` and not in `ignore_bays` has its overdrive plate (the sliding plate that stops a car from driving over the bay's edge) in the way, so its `BAY_ODP` volume at the inbound heading is switched off.
4.  **Disabled nodes.** Nodes listed in `disabled_nodes_`, plus the nodes of disabled trays, AGVs and bays, are blocked for every heading at the node's largest window, whatever really stands there. This is how the running schedule's reservations reach every search ([Figure 122](#bg-fig-122_closing_a_node)).
5.  **Node size.** For a payload footprint only, every pose whose node's largest window is smaller than the payload is switched off, with all edges into and out of it.

Two wrappers build whole sets of filters. `GetAllStaticFilters` returns one filter for AGV, one for TRAY and one for each payload size present in the state. `GetDisabledEntitiesFilters` calls it with every tray, AGV and bay ignored unless it is disabled or stands on a disabled node, so only disabled things block; this is what fills `ctx->disabledness_filters` in `Plan()`. CHUGG builds its static constraints with `GetAllStaticFilters`. The scheduler calls `GetStaticFilter` directly when it needs a particular view, for example all trays and AGVs ignored in `AssignTrayIdForEmptyMove`.

Points to keep in mind:

- **Not every search reads both masks.** The tray searches test only the edge mask; `GarageGraphEnvironment` and `AgvSearchEnvironment` test the edge and the vertex it leads to.
- **`IsEnabled` does no bounds checking**, and a filter built for one graph must not be used with another. `GetStaticFilter` throws if the collision table was built for a different layout (MD5 check) or if the state names a disabled node the layout does not have.
- **A filter is a snapshot.** It is computed from one state; a search that runs after events have been applied to a working state needs a new filter, which is why several scheduler methods build their own.

### The tray searches: `BlockingTraySearchEnvironment` and its two subclasses

Tray assignment needs three answers about a tray: which trays stand on its way to a target, where it could be parked, and which empty tray is cheapest to bring somewhere. One environment class and two subclasses provide them. They share the state and the step cost, and differ only in the source of the search and in the goal test, so one expansion shows all three.

![One expansion, three goal tests](figures/143_blocking_tray_search.svg)

**One expansion, three goal tests.** Tray T17 at stall P17 searched outward. Every route out of P17 crosses a parked tray, so the first nodes cost 30 s more than their travel time. Step through the nodes in the order they are closed: the open-space goal test would stop at the first free parking node, P23 (or earlier, at waypoint W13, if a waypoint stash is allowed); the blocking-tray search continues to its target, bay B21, and returns the path with `blocking_trays = {K}`. Travel times are illustrative; the 30 s per crossed tray is the code's constant.

- **State.** `BlockingTrayState` is a graph vertex plus the set of trays crossed so far. Its hash and equality use only the vertex.
- **Step cost.** `GetNeighbors` follows each out-edge allowed by the filter's edge mask. The step costs the edge's trapezoid time from the cost model ([section 4.2](#bg-the-cost-model)) plus 30 s for each tray, other than the moving one, whose footprint the edge newly overlaps (a `CollisionTable::Query` against every tray in the state). The 30 s carries a TODO: it stands for "moving a tray is worth about this much detour" and is not measured. An optional `max_blocking_trays` drops neighbors that would cross too many trays.
- **Parked trays are paid for, not filtered.** The filter passed in usually ignores the trays, so the search may route through them; each one crossed is collected in the state and returned to the caller, which then plans its move.

| Environment                     | Source               | Goal test (`OnExpansion`)                                                                                                                                                                                                                                                                                                       | Used for                                                                                                     |
|---------------------------------|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `BlockingTraySearchEnvironment` | The tray's pose      | The vertex is the target pose                                                                                                                                                                                                                                                                                                   | The critical path of the blocking-tray loop and the trays on it ([Figure 15](#bg-fig-15_blocking_tray_move)) |
| `OpenSpaceSearchEnvironment`    | The tray's pose      | A parking or EV-charge node with no tray on it that does not overlap an illegal pose; at the retrieval heading if asked; for a car that requested charging, an EV-charge node at a heading of 0 to 90 (the VECS state itself is not checked); tall enough for the car. With `allow_waypoint_stash`, a free waypoint also counts | A new home for a blocking tray or a reparked tray ([Figure 56](#bg-fig-56_assign_dest_untargeted))           |
| `EmptyTraySearchEnvironment`    | The destination pose | The node holds a tray without a payload                                                                                                                                                                                                                                                                                         | Choosing the tray for an empty-tray move ([Figure 55](#bg-fig-55_assign_tray_id_empty))                      |

Details that affect results:

- **The first-found tray set is kept.** Because two states at one vertex are equal, a cheaper route found later lowers the cost and replaces the predecessor, but the state in the open set keeps the tray set of the route that reached the vertex first. The set returned can therefore differ from the trays on the path returned; the blocking-tray loop re-queries the path, which limits the effect.
- **The empty tray found is itself crossed.** In `EmptyTraySearchEnvironment` the moving tray id is 0, so the tray at the goal also adds 30 s on the last edge. Every candidate pays it, except a tray already standing at the source.
- **Open space is checked when a node is closed, not when it is reached.** The illegal-pose, heading, charging and height checks reject a node as a goal but still let the search pass through it.
- **The cost is a proxy.** Travel time plus a constant per tray ignores AGVs, waiting and the time to move the blockers, so the cheapest answer here need not give the quickest plan; only CHUGG and the benchmark set can show that.

### `GetPosePath` and `ConvertPosePathToTrajectory`

When the scheduler needs to know how long an AGV takes to drive somewhere, or whether it can get there at all, it does not run SIPP. It runs a plain shortest-path search and times the result. This is the cheapest of the searches and the one AGV assignment uses for its costs.

- **The search.** `GetPosePath(graph, source, target, cost_model, filters)` converts both poses to vertices and runs `SingleSourceSearch` with `GarageGraphEnvironment`. States are vertices, that is poses: a node with two headings is two vertices joined by rotation edges. A step costs the edge's own trapezoid time, as if the AGV stopped at every node, and is allowed only if both the edge and its target vertex are enabled. The goal is the target vertex. An empty vector means "no path" (or an unknown pose).
- **Why the step cost may be crude.** A comment in the code states that the search is used "only to discover topology". The chosen path is re-timed by `ConvertPosePathToTrajectory`, which groups consecutive edges of the same kind and direction into runs and gives each run one trapezoid, loaded or unloaded ([Figure 94](#bg-fig-94_trapezoid_runs)). Each edge still becomes its own `Motion`, with a sub-interval of the run, so later collision checks see every node passed.
- **The consequence.** Stopping at every node overprices long straight runs, so the path chosen can differ from the quickest one when a route with fewer, longer runs exists. The time reported is that of the chosen path, timed properly.

### `HideAgvs`: a tray for every AGV

A CLEAN_GARAGE job first moves every AGV out of the aisles, under a parked tray ([section 14.16](#bg-type_clean_garage--plancleangaragejob)). `HideAgvs` chooses those poses. It is the only search here that is called repeatedly inside a backtracking loop.

![HideAgvs AGV by AGV](figures/144_hide_agvs.svg)

**`HideAgvs`, AGV by AGV.** Step through two AGVs. Each search explores the whole reachable graph at 1 s per edge and lists the tray poses it closes, nearest first. AGV-1 takes stall P23; AGV-2 then searches again with AGV-1 at P23 and takes stall P15. Positions are hypothetical.

- **One search per AGV.** `HideOneAgv` builds the AGV filter with only this AGV ignored (other AGVs block it; trays block only with their legs) and runs `SingleSourceSearch` with `AgvSearchEnvironment`. Every step costs 1 s ("TODO: Use graph edge costs"), and `OnExpansion` never returns `true`, so the search closes every reachable pose. Each closed pose on a node with a tray, at the tray's heading or its reciprocal, is appended to the candidate list. An AGV already under a tray finds its own pose first, at cost 0.
- **Greedy with backtracking.** For each candidate in order, the AGV's move is applied to a copy of the state, and the function recurses for the remaining AGVs, which search again in the changed copy. The first complete assignment is returned. If an AGV has no candidate left, the caller tries its next candidate; if every candidate of every first AGV fails, the result is `{false, {}}`.
- **What it does not optimise.** The header promises "the least amount of AGV moves", but the result is the first assignment found, AGV order follows an `unordered_set`, and distance counts edges, not time. In the worst case the backtracking tries every order of every candidate list.

## Solver inputs and outputs: CHUGG and the standard MAPF problem

CHUGG is the only motion planner the scheduler has, and its interface was shaped by the scheduler's data rather than by a standard problem definition: it takes the event DAG itself. This section compares its inputs with the textbook multi-agent path finding (MAPF) problem that solvers such as conflict-based search (CBS) expect, asks whether either can take the other's input, and ends with a solver-neutral description of the problem. The [Issue & proposal](#doc-proposal) tab turns that description into an interface ([section 15](#pr-swappable-motion-planners)).

### The standard MAPF problem, and CBS

A classic MAPF instance (Stern et al., “Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks”, SoCS 2019) has three parts:

- **A graph** G = (V, E): the places agents can be, and the moves between them.
- **Agents** 1, \ldots, k, each with a **start** s_i \in V and a **goal** g_i \in V.
- **Rules**: time advances in unit steps; at each step an agent moves along one edge or waits. Two agents conflict if they are on the same vertex at the same step (vertex conflict) or swap along one edge (edge conflict).

Formally, a solution assigns each agent a path \pi_i, a sequence of vertices indexed by time step, that starts at s_i, ends at g_i and moves along at most one edge per step:

\pi_i : \\0, 1, \ldots, T_i\\ \to V, \qquad \pi_i(0) = s_i, \quad \pi_i(T_i) = g_i, \quad \pi_i(t+1) \in \\\pi_i(t)\\ \cup N\big(\pi_i(t)\big),

where N(v) is the set of neighbours of v and an agent waits at its goal after T_i. Two agents i \ne j are in conflict at step t if

\underbrace{\pi_i(t) = \pi_j(t)}\_{\text{vertex conflict}} \qquad \text{or} \qquad \underbrace{\pi_i(t) = \pi_j(t+1) \\\wedge\\ \pi_i(t+1) = \pi_j(t)}\_{\text{edge (swap) conflict}},

and the two usual objectives are

\mathrm{SOC} = \sum\_{i=1}^{k} T_i \quad \text{(sum of costs)}, \qquad \mathrm{MS} = \max\_{i} T_i \quad \text{(makespan)}.

A solution is one path per agent, from s_i to g_i, with no conflicts; the usual objectives are the sum of arrival times (sum of costs) or the latest arrival (makespan). Solvers differ in how they search: **prioritized planning** plans agents one at a time in a fixed order, each avoiding the ones before it (fast, but neither complete nor optimal); **CBS** (Sharon et al., Artificial Intelligence 2015) plans every agent alone, then resolves conflicts by branching on which agent must avoid the contested place and time, and is optimal for sum of costs. Both use a single-agent planner underneath, and SIPP is a common choice for it.

![Conflict-based search on the same example](figures/98_cbs_example.svg)

**CBS on the example of [Figure 1](#mp-fig-97_prioritized_planning).** Step through the constraint tree: the root plans each AGV alone and finds the conflict at vertex 3; each branch forbids one AGV from vertex 3 while the other is there and replans only that AGV; the cheaper conflict-free node is the solution. CBS finds a total of 12 s where prioritized planning, committed to e1 first, needed 16 s.

The literature has extended this core in the directions the garage needs: goal *sequences* per agent (multi-goal MAPF and pickup-and-delivery), precedence constraints between goals of different agents (MAPF-PC, Zhang et al., AAMAS 2022), large agents whose footprint covers several places, and continuous time with real durations (CCBS, Andreychuk et al., Artificial Intelligence 2022). Each extension changes the input, not the idea.

### What CHUGG receives instead

The seven arguments of the `Chugg` constructor ([section 2](#bg-chugg-the-motion-planner)) cover the same three parts, each in a richer form:

| Part                | Classic MAPF                                 | CHUGG today                                                                                                                                         | Why it is richer                                                             |
|---------------------|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| Graph               | G = (V, E)                                   | `GarageGraph`: vertices are poses (node + heading), edges carry a transition type (drive, strafe, rotate, ride a VRC) and a length                  | An AGV's heading matters, and turning in place is a move of its own          |
| Time                | Unit steps                                   | Continuous time: `edge_durations` and the cost model (trapezoid profiles, run extension, wheel-turn delays, lift times)                             | Moves take very different times (a 90° turn takes as long as 9 m of driving) |
| Conflicts           | Same vertex or swapped edge at the same step | `CollisionTable`: which footprint at which vertex or edge overlaps which other; the footprint depends on what the AGV carries                       | Bodies are rectangles of different sizes, and a move sweeps an area          |
| Agents and starts   | s_i per agent                                | The initial `ContinuousState`: every AGV, tray, bay and VECS standing still from `start_time`; disabled and unused entities become static obstacles | Trays are carried, not driven; bays and VECS change state but never move     |
| Goals               | One g_i per agent                            | The event DAG: per AGV, a *sequence* of goals (drive to a pose, lift, carry a tray, lower), plus timed state changes for bays and VECS              | One plan call moves many trays with few AGVs                                 |
| Order between goals | None                                         | The event DAG's edges, across entities (“the tray arrives before the bay processes the retrieve”)                                                   | Task logic: bays, VECS and trays depend on each other                        |
| Objective           | Sum of costs or makespan                     | None stated: the first feasible plan in the priority order; SIPP's own cost adds a 3 s penalty per step                                             | A design choice: one fast pass, with no search over who goes first           |
| Output              | One path per agent                           | `ContinuousState`: timed motions per entity, each tagged with the event it implements                                                               | The action DAG needs to know which motion belongs to which event             |

Two things about the form of the input matter more than its content. First, the goals arrive as `planner_core` event objects (`AgvMove`, `TrayMove`, `BayTransition`, ...), and CHUGG has one planning routine per event class, so `motion_planner` depends on the scheduler's task vocabulary. Second, some inputs are not arguments at all but rules inside CHUGG: the start state is replayed from the event DAG, the static obstacles are derived from it, and the goal of a `TrayMove` (approach, lift, carry, lower, and the footprint at each step) is decided inside `SippAgv::AddEventGoal`. The code's own comments ask for a simpler input: “Simplify inputs with schedule context object” on the constructor, and “a simpler AgvEvents struct that contains events and constraints for a single agv” above `SippAgv`.

### CHUGG's problem in the same notation

Writing CHUGG's input in the notation above shows exactly where it departs from the classic problem, and therefore which parts of the MAPF literature apply. Each item maps to a part of the code.

- **Graph.** The vertices are poses P = \\(v, \theta)\\ and the edges are typed transitions E_P \subseteq P \times P (locomote, strafe, rotate, ride a VRC), each with a duration \tau(e) \> 0 from the cost model: the `GarageGraph` and `edge_durations`.
- **Motions instead of steps.** An agent's plan is a sequence of motions m = (e, \[a, b), f): a transition or a wait e, a time interval with b - a \ge \tau(e), and a footprint f (bare AGV, or AGV with a tray of some size class). Consecutive motions abut: b_k = a\_{k+1}. This is a `Trajectory` of `Motion`s.
- **Conflicts by footprint overlap.** With \mathcal{C}(e, f) the set of (location, footprint) pairs that the collision table says overlap footprint f on e, two motions of different agents conflict when
  \[a, b) \cap \[a', b') \ne \varnothing \quad \wedge \quad (e', f') \in \mathcal{C}(e, f).

  With unit footprints and \mathcal{C}(e) = “the same vertex, or the same edge reversed” this reduces to the vertex and swap conflicts above; with real footprints it is the large-agent conflict of Li et al. (“Multi-Agent Path Finding for Large Agents”, AAAI 2019).
- **Goals with precedence.** The events \mathcal{E} of the event DAG, partially ordered by its edges \prec. Each event \varepsilon belongs to one entity \alpha(\varepsilon) and has a goal g(\varepsilon): a pose to reach, a lift to perform, or a fixed-duration state change. A plan is feasible only if every event starts after its predecessors have finished:
  \mathrm{start}(\varepsilon') \\\ge\\ \mathrm{end}(\varepsilon) \qquad \forall\\ \varepsilon \prec \varepsilon'.

  This is MAPF with precedence constraints (MAPF-PC), with goal sequences per agent.
- **Arrival is “stay forever”.** A pose goal is met at time t only if the pose is safe on \[t, \infty) given everything planned so far ([section 3.2](#bg-sipp-the-single-agv-search)), the usual rule in prioritized planning.
- **No objective.** CHUGG returns the first feasible plan it finds; nothing is minimised across agents.

**How `SolveSequential` solves it.** It fixes one topological order \sigma of (\mathcal{E}, \prec) (lowest job index first) and plans one event at a time against a growing set of reservations \mathcal{R}\_k, the motions already committed plus every other entity frozen at its last pose:

\begin{aligned} t_0(\sigma_k) &= \max\Big(\\ \mathrm{end}\big(\text{last motion of } \alpha(\sigma_k)\big),\\ \max\_{\varepsilon \prec \sigma_k} \mathrm{end}(\varepsilon) \Big),\\ \pi\_{\sigma_k} &= \mathrm{SIPP}\big(\alpha(\sigma_k),\\ g(\sigma_k),\\ t_0(\sigma_k),\\ \mathcal{R}\_k\big), \qquad \mathcal{R}\_{k+1} = \mathcal{R}\_k \cup \pi\_{\sigma_k}. \end{aligned}

SIPP searches over (location, safe interval) pairs. For a location \ell (a pose or a transition) and the footprint f the AGV will have there, the safe set is what the reservations leave free,

S_f(\ell) = \[t_0, \infty) \setminus \bigcup\_{\substack{m \in \mathcal{R}\_k \\ (\ell, f) \in \mathcal{C}(m)}} \[a_m, b_m),

split into maximal intervals; that is a `SafeIntervalTable` entry. A\* expands states with F = G + H, where H sums the all-pairs travel times d(\cdot,\cdot) (Floyd–Warshall over \tau) along the remaining goals, and each move to a state with n predecessors costs \tau(e) + \tau\_{\text{turn}} + 3n seconds (the step penalty of [section 3.2](#bg-sipp-the-single-agv-search)). In the literature's terms this is **prioritized planning with SIPP** on a **MAPF-PC instance with large agents and continuous time**, with the priority order fixed by the event DAG. It is fast and incomplete: if \mathrm{SIPP} fails for some \sigma_k, nothing earlier is replanned.

### Can CHUGG take a CBS-style input, and can CBS take CHUGG's?

With the classic MAPF problem ([section](#mp-the-standard-mapf-problem)) and CHUGG's problem ([section](#mp-chuggs-problem-in-symbols)) stated in the same notation, the question is whether an instance of one can be given to a solver for the other. The answer differs by direction, and it determines what a common solver input must be able to express.

- **Classic instance into CHUGG: yes, through an adapter.** A classic instance is a special case of CHUGG's: one `AgvMove` per agent to its goal pose, no edges in the event DAG, a start state with each AGV on its start pose and nothing else in the garage. CHUGG would then run prioritized planning over the agents in the event order (job index, then insertion order). Two of its rules still apply and differ from classic MAPF: a goal counts only if the AGV can stay there forever, and moves are timed by the cost model, not in unit steps.
- **CHUGG's input into a classic CBS: not without extensions.** A textbook CBS has no goal sequences, no precedence across agents, no load-dependent footprints and no fixed-duration actions for bays and VECS. Each gap has a known extension (multi-goal CBS, CBS with precedence constraints, a pluggable conflict test that asks the `CollisionTable`, continuous-time CBS), and CHUGG's low level is already prepared for one: `SippAgv` accepts CBS-style landmark and avoid constraints, which the unfinished `SolveCbs` uses.
- **So standardize on the richer problem.** If the common input can express goal sequences, precedence, footprints and timed actions, a classic instance is just the case with one goal per agent and no edges, and a solver that cannot handle the full problem can say so, or be given a sub-problem it can handle.

### From CHUGG towards the standard solvers

Each family of MAPF solvers relaxes one of CHUGG's simplifications. In the notation above, the differences are small and concrete:

| Direction                                                                                                                       | What changes in the formulation                                                                                                                                                                         | What it buys                                                                                                             | Where CHUGG already has a hook                                                                                              |
|---------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| **Search over priorities** (PBS: Ma et al., “Searching with Consistent Prioritization for Multi-Agent Path Finding”, AAAI 2019) | Replace the fixed order \sigma by a priority relation \prec_P \supseteq \prec grown lazily: when i and j conflict, branch on i \prec_P j or j \prec_P i                                                 | Recovers from a bad order; the event DAG stays a hard part of \prec_P, only the job-index tie-break is searched          | `SolveSequential` is PBS's leaf step; the order is the one choice it would search                                           |
| **Conflict-based search** with continuous time (CBS; CCBS: Andreychuk et al., Artificial Intelligence 2022)                     | Plan every agent alone, then resolve a conflict between m_i and m_j by branching on constraints \langle i, \ell, \[a, b) \rangle (“i may not use \ell during \[a, b)”) for one agent or the other       | Optimal for \mathrm{SOC}; a bounded-suboptimal variant (ECBS: Barer et al., SoCS 2014) trades a factor w \ge 1 for speed | `SolveCbs`, `Chugg::Node`, `AddAvoidConstraint` and `AddLandmarkGoal` (unfinished); SIPP already takes interval constraints |
| **Precedence-aware search** (CBS-PC and PBS-PC: Zhang et al., AAMAS 2022)                                                       | Keep \mathrm{start}(\varepsilon') \ge \mathrm{end}(\varepsilon) as explicit constraints inside the search instead of baking them into one order                                                         | Complete (CBS-PC) for the problem CHUGG actually has                                                                     | The event DAG is already the precedence input                                                                               |
| **Large agents** (Li et al., AAAI 2019)                                                                                         | Conflicts are footprint overlaps \mathcal{C}(e, f), not equal vertices                                                                                                                                  | Correct conflicts for rectangles of different sizes                                                                      | The `CollisionTable` is exactly \mathcal{C}                                                                                 |
| **Large neighbourhood search** (MAPF-LNS2: Li et al., AAAI 2022)                                                                | Start from a plan (CHUGG's, or one with conflicts), then repeatedly remove a subset A' \subset A of agents or events and replan it against the rest, keeping the result if J improves or conflicts drop | Anytime improvement within a time budget, and repair when prioritized planning fails                                     | `SolveSequential` as the initial solver; `SetEventSafeIntervals` already plans one event against all others                 |

All of these need an objective J, which CHUGG does not have. The natural candidates are \mathrm{SOC} over event completion times, \mathrm{MS}, or the length of the action DAG's critical path, J = \max\_{\text{paths } p \text{ in the ADG}} \sum\_{a \in p} \mathrm{duration}(a), which is what execution actually waits for ([section 4.4](#ad-timing-critical-path-and-slack)). A sensible order of work is: an explicit J and a validator (so that solvers can be compared), then PBS over the job-index tie-break (the smallest change to CHUGG, and it keeps every DAG edge), then LNS for anytime improvement, and CBS-PC only if completeness matters more than speed. The interface that makes these swappable is in the Issue & proposal tab ([section 15](#pr-swappable-motion-planners)).

### A solver-neutral description of the problem

Everything a motion planner needs here falls into four parts, none of which has to be a scheduler type:

1.  **World**, fixed per site: the motion graph, the conflict model (which footprint at which vertex or edge overlaps which other) and the timing model (edge, turn, lift and device durations).
2.  **Start**, per plan call: the start time; each agent's pose, footprint and what it carries; the places that are blocked for this call (parked trays, disabled AGVs and nodes); devices (bays, VECS) and their states.
3.  **Tasks**, per plan call: a set of goals, each for one entity (drive to a pose, pick up or put down a tray, a device state change of known duration), and precedence edges between goals. This is the event DAG without the scheduler's classes.
4.  **Settings**: the objective, a time budget, and whether a partial or suboptimal answer is acceptable.

The output is a timeline per entity in which every motion names the goal it serves, so that the action DAG can be built the same way whichever solver produced it. Any output, from any solver, can be checked by one solver-independent validator: every goal reached, every precedence edge respected, and no two motions in conflict according to the conflict model. CHUGG already ends with such a check (`CheckCollisions`); the validator would make it a shared contract rather than one solver's last step.
