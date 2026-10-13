# 01 — Scheduler software background

*A ground-up guide to the current Volley scheduling code, using the provided C++ snapshots, ROS interface definitions, tests, and the `5675_pecos_combined.yaml` facility layout.*

> **Scope and evidence.** This guide documents the *existing* implementation, not the proposed solver refactor. The Scheduler and `planner_core` classes were inspected in `scheduler-core-analysis.md`; package dependencies and tests in `scheduler-refactor-tests.md`; message fields in `repomix-interfaces.xml`; spatial topology in `5675_pecos_combined.yaml`. The figures use real Pecos node positions and edges, but **AGV/tray occupancy is hypothetical**. The YAML has bays and charging nodes but **no VRC**; multi-floor VRC behavior is documented from the code and messages separately.

## Table of contents

- [1. What problem does this software solve?](#1-what-problem-does-this-software-solve)
- [2. The physical garage and its coordinate system](#2-the-physical-garage-and-its-coordinate-system)
- [3. Vocabulary and data representations](#3-vocabulary-and-data-representations)
- [4. ROS messages and services](#4-ros-messages-and-services)
- [5. C++ classes: orientation and source map](#5-c-classes-orientation-and-source-map)
- [6. Objects and ownership: the Scheduler and ScheduleContext](#6-objects-and-ownership-the-scheduler-and-schedulecontext)
- [7. Event types and polymorphism](#7-event-types-and-polymorphism)
- [8. Directed acyclic graphs, then ScheduleEventDag](#8-directed-acyclic-graphs-then-scheduleeventdag)
- [9. The complete planning pipeline](#9-the-complete-planning-pipeline)
- [10. Tray assignment and blocking trays](#10-tray-assignment-and-blocking-trays)
- [11. Annotated AGV scenes from the Pecos layout](#11-annotated-agv-scenes-from-the-pecos-layout)
- [12. AGV assignment, timing, and dependency repair](#12-agv-assignment-timing-and-dependency-repair)
- [13. Motion planning and final ActionNode messages](#13-motion-planning-and-final-actionnode-messages)
- [14. VRC, bays, and charging resources](#14-vrc-bays-and-charging-resources)
- [15. Packages, build system, and dependencies](#15-packages-build-system-and-dependencies)
- [16. C++ concepts and idioms in context](#16-c-concepts-and-idioms-in-context)
- [17. Known limitations and reading checkpoint](#17-known-limitations-and-reading-checkpoint)

## 1. What problem does this software solve?

A customer vehicle sits on a **tray** inside an automated parking facility. An **AGV** (automated guided vehicle) drives under a tray, raises its lift, and transports the tray. A **bay** is the customer-facing handoff area; a **waypoint** is a navigation node; a **parking node** is a place where trays can be stored; an **AGV charge** node provides a robot charging destination. Some installations may have a **VRC** (vertical reciprocating conveyor) to move equipment between floors. These are *different resources with different constraints*.

An incoming job such as **retrieve the payload** does not directly specify every robot command. The Scheduler decides which movements are necessary, which AGV can do them, and which operations must occur first. It then invokes motion planning and packages the result into actions that another part of the system can execute. This code does **not** directly control wheel motors.

The essential distinction is **what** should happen versus **how and when** it happens:

| Layer | Question | Example | Source |
|---|---|---|---|
| Job | What outcome is requested? | Retrieve a payload | `msg/SchedulerJob.msg` |
| Abstract schedule event | What state transition is necessary? | Move a tray into a bay | `planner_core/schedule_events.hpp` |
| Motion | How does an AGV get there over time? | Follow a timed path, lift, rotate | `Scheduler::PlanMotions`; motion-planner types |
| Action | What discrete command is published to an entity? | `AGV_COMMAND`, `BAY_COMMAND` | `msg/ActionNode.msg` |

![Planning stages](figures/01_pipeline.svg)

*Figure 1 — Scheduler's principal phases, from input jobs to output actions. Each stage refines or constrains the result of the prior stage; the diagram does not represent a ROS thread or executor schedule.*

## 2. The physical garage and its coordinate system

The supplied **Pecos** layout has **28 nodes and 37 undirected edges**. It defines **two bays** (`B7`, `B21`), **three AGV charging nodes** (`C10`, `C14`, `C16`), plus parking and waypoint nodes. It does not define a VRC. Node positions come from the YAML; connectivity comes from the `edges` list. The graph is not inferred from visual distance between stalls.

![Pecos facility graph](figures/15_facility_topology.svg)

*Figure 2 — Pecos facility graph reconstructed from YAML coordinates in meters. Rectangular outlines indicate parking locations, green outlines indicate customer bays, violet circles indicate AGV chargers, and grey circles indicate waypoints. The illustrated trays and AGV are hypothetical; they are **not** initial states supplied by the YAML. The edges depict allowed node connections, not physical aisle width or measured collision envelopes.*

### Geometric versus logical position

The continuous position vector **$\mathbf p=[x,y]^\mathsf T\in\mathbb R^2$** contains the horizontal coordinate **$x\in\mathbb R$** and vertical coordinate **$y\in\mathbb R$**, both in meters. A planar configuration **$\mathbf q=[x,y,\theta]^\mathsf T\in\mathbb R^3$** adds the heading **$\theta\in\mathbb R$**. In `GeometricPose.msg`, the yaw **$\theta$** is in radians. In contrast, `GaragePose.msg` contains a node identifier **$i\in\mathbb N$** and an integer heading **$h\in\mathbb Z$** in degrees. These are not interchangeable types.

```text
# msg/GeometricPose.msg          # msg/GaragePose.msg
float32 x       # meters        uint32 node_id
float32 y       # meters        int16 heading # degrees
float32 yaw     # radians
```

The interface defines positive headings counterclockwise from local north (90° points west). `GarageNode.msg` also declares floor, valid headings, rotation permission, resource-size limits, and node type. A nearby node is **not necessarily reachable**: the YAML must contain an edge, and the pose/heading and collision constraints must permit traversing it.

## 3. Vocabulary and data representations

Learn these terms **before** reading the C++ algorithms:

| Term | Meaning | Example / important distinction |
|---|---|---|
| `SchedulerJob` | High-level requested outcome | `TYPE_RETRIEVE` or `TYPE_MOVE_TRAY` |
| `DiscreteGarageState` | In-memory model of which resources exist, their node poses, and states | Not a timed trajectory |
| `ScheduleEvent` | Abstract, potentially incomplete state-changing operation | Base C++ class; not a ROS `.msg` |
| `TrayMove` | A schedule event representing a tray relocation | May lack tray ID, target pose, and AGV ID |
| `AgvMove` | An AGV pose change or lift change | One alternative in `std::variant` |
| DAG | Directed acyclic graph | Dependencies say which events must precede others |
| `ScheduleEventDag` | C++ graph container for schedule events | Stores shared event objects and graph edges |
| `ScheduleContext` | Mutable data for one planning attempt | Includes initial state, DAG, jobs, first tray events |
| `Motion` / `ContinuousState` | Time-related movement representation | Used *after* abstract assignment |
| `ActionNode` | Final executable action and parent indices | Generated ROS message, placed inside `Schedule` |
| `GarageGraph` | Heading-aware graph used for movement search | Not identical to a drawn 2D floorplan |
| `CollisionTable` | Checks collision/occupancy compatibility | Implementation body not in snapshots |

### A request is not a plan

```text
PlanRequest
  ├── base_state: DiscreteGarageState message
  ├── base_schedule: Schedule
  ├── planned_jobs / active_jobs
  └── pending_jobs: SchedulerJob[]

PlanResponse
  ├── success, message, id
  ├── schedule: Schedule → ActionNode[]
  └── scheduled_jobs: ScheduledJobData[]
```

The base schedule is described by its `.msg` as the immutable part of an existing schedule. The Scheduler's observed `Plan()` marks certain resources from base actions disabled in its planning initial state. This matters when trying to understand why apparently available nodes or AGVs cannot be reused.

## 4. ROS messages and services

The `interfaces` package defines the wire contracts under `msg/` and `srv/`. `rosidl_generate_interfaces` turns those text definitions into generated C++ structs, introspection support, and serialization code. This is **data exchange**, not C++ inheritance. In other words, when one ROS message appears inside another, the relationship is **composition**: one struct contains another struct or an array of such structs as a field.

For a new engineer, the most useful way to read these interfaces is from **outside in**:

1. Start with `srv/Plan.srv`, because it is the service boundary for the Scheduler.
2. Open `PlanRequest.msg` and `PlanResponse.msg` to see the request/response payloads.
3. Then expand the nested messages that matter most: `DiscreteGarageState`, `Schedule`, `ActionNode`, and `SchedulerJob`.
4. Only after that should you drill into utility types such as `GaragePose`, `AgvGoal`, or the resource-specific command messages.

| Interface | What it contains | Why it matters to the Scheduler |
|---|---|---|
| `srv/Plan.srv` | A `PlanRequest` and a `PlanResponse`. | This is the ROS service contract that `SchedulerRos` exposes. When another node “calls the Scheduler”, this is the exact boundary crossing. |
| `msg/PlanRequest.msg` | A planning ID, the current `DiscreteGarageState`, the immutable `base_schedule`, and three job arrays: `planned_jobs`, `active_jobs`, and `pending_jobs`. | This message tells the Scheduler both **what the world looks like now** and **what work still needs to be planned**. |
| `msg/PlanResponse.msg` | A success flag, human-readable message, plan-call ID, an output `Schedule`, and `ScheduledJobData[]`. | This is how the Scheduler returns both the executable schedule and job-level bookkeeping information back to the caller. |
| `msg/SchedulerJob.msg` | A high-level job request, including job type, state, IDs for AGV/bay/tray/payload, and an optional destination. | This message expresses user or dispatcher intent. It is still much more abstract than the final action schedule. |
| `msg/DiscreteGarageState.msg` | Arrays of AGVs, bays, VECS, trays, payloads, VRCs, plus disabled nodes and a hash. | This is the Scheduler’s snapshot of the garage at the beginning of a plan call. The in-process C++ `DiscreteGarageState` class is built around this same conceptual information. |
| `msg/GarageLayout.msg` | Layout name, nodes, floors, edges, disallowed orientations, and resource windows. | This message defines the static topology over which AGVs, trays, and payloads move. |
| `msg/GarageNode.msg` | Node geometry, node type, floor, allowed headings, rotation permission, and bay-specific metadata. | This tells the rest of the software what a particular node ID actually means in physical and operational terms. |
| `msg/GaragePose.msg` | A node ID and a discrete heading. | This is the canonical discrete pose type used throughout scheduling, assignment, and action generation. |
| `msg/Schedule.msg` | A topologically ordered array of `ActionNode`s. | This is the output execution DAG that downstream execution software consumes. |
| `msg/ActionNode.msg` | An action type, dependency indices, timing/status fields, and type-specific command payloads. | This is the final bridge from in-memory planning logic to executable ROS-level commands. |

![ROS message relationships](figures/13_uml_ros_messages.svg)

*Figure 3 — As-built ROS service and message composition derived from the `.msg` and `.srv` definitions. A **filled diamond** means “contains as a field or array element.” Blue boxes sit on the **request / intent** side, violet boxes describe the **garage-state snapshot**, green boxes describe the **response / schedule** side, and amber boxes are **nested command or utility messages**. The dashed outer frame marks the `Plan.srv` boundary.*

A few important reading notes help prevent confusion:

- `PlanRequest` and `PlanResponse` are ROS message **types**, not C++ service handler classes.
- `Schedule.nodes` is a topologically ordered array of `ActionNode` messages, so dependencies in the serialized schedule are represented by **integer parent indices**, not pointers.
- `ActionNode` is intentionally wide: it contains several command fields, but only the field corresponding to the node’s `type` is semantically active.
- `SchedulerJob.destination` and `DiscreteAgvState.pose` both use `GaragePose`, which keeps the discrete graph interpretation consistent across request, state, and output data.

`ActionNode.parents` therefore contains **indices** into the output schedule, not `shared_ptr` references to `ScheduleEvent` objects. The transition from in-process event objects to serialized action indices happens near the end of planning.

## 5. C++ classes: orientation and source map

Once the ROS interfaces are clear, the next question is: **which C++ objects hold, transform, and emit those data?** The table below is deliberately more descriptive than a quick reference sheet, because these classes are the vocabulary of the rest of the guide.

Read the rows in three passes:

1. First, identify the *orchestrator* types such as `Scheduler` and `ScheduleContext`.
2. Next, identify the *domain-model* types such as `ScheduleEvent`, `TrayMove`, `AgvMove`, and `DiscreteGarageState`.
3. Finally, identify the *infrastructure* types such as `ScheduleEventDag`, `GarageGraph`, `GarageOccupancyChecker`, and the collision / cost helpers.

| Class / type | What it does | Declared in | Key members / methods |
|---|---|---|---|
| `Scheduler` | The main planner object. It validates requests, expands jobs into abstract events, performs tray and AGV assignment, checks the resulting plan, and invokes motion planning. In other words, this is the *orchestrator* of the entire pipeline. | `src/planner/scheduler/include/scheduler/scheduler.hpp` | `Plan`, `DoTrayAssignments`, `DoAgvAssignments`, `PlanMotions` |
| `SchedulerParams` | A bundle of constructor-time configuration and planning parameters. It lets the planner be configured without encoding every setting as a separate constructor argument. | Same `scheduler.hpp` | `motion_cost`, `bay_readiness_ratio`, `cost_audit` |
| `ScheduleContext` | The mutable working set for a single plan call. It carries the initial garage state, the evolving event DAG, scheduled-job metadata, and several helper maps used to preserve dependency relationships. | Same `scheduler.hpp` | `initial_state`, `events`, `scheduled_jobs`, `first_tray_event` |
| `ScheduleEvent` | The abstract base class for in-memory schedule events. Each concrete subclass represents a state-changing operation that can be replayed against a `DiscreteGarageState`. | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `Apply`, `GetGarageEntityId`, `GetJobIndex`, `GetType` |
| `TrayMove` | A partially or fully assigned tray-relocation event. Before assignment, it may be missing the tray ID, destination, or AGV ID; after assignment, it becomes much more concrete. | Same `schedule_events.hpp` | `GetTrayId`, `SetTrayId`, `GetDest`, `SetDest`, `SetAgvId` |
| `AgvMove` | A concrete AGV movement or lift-change event. Unlike `TrayMove`, this represents *robot* motion rather than abstract tray intent. | Same `schedule_events.hpp` | `GetDiscreteChange`, `GetAgvId`, `Apply` |
| `BayTransition` | A state transition or command affecting a bay. It captures the bay-side operations required for insert/retrieve workflows. | Same `schedule_events.hpp` | `GetSourceState`, `GetCommand`, `Apply` |
| `VecsTransition` | A state transition for EV charging equipment. This is the scheduler-facing representation of charging-resource state changes. | Same `schedule_events.hpp` | `GetStateChange`, `Apply` |
| `VrcTransition` | A transition involving a VRC, including floor movement and gate-related state changes. It matters in multi-floor garages even though the Pecos YAML used in the figures has no VRC node. | Same `schedule_events.hpp` | `GetFromVrcNodeId`, `GetToVrcNodeId`, `Apply` |
| `DagBase<T>` | A reusable directed-graph template implemented with Boost Graph. It provides graph storage and generic algorithms such as adding edges and obtaining a topological order. | `src/planner/planner_core/include/planner_core/event_dag.hpp` | `Add`, `AddDependency`, `Reduce`, `GetTopologicalOrdering` |
| `ScheduleEventDag` | The Scheduler-specific DAG specialization whose vertices are `ScheduleEvent` objects. This is where abstract event dependencies are stored before action generation. | Same `event_dag.hpp` | `AddEvent`, `GetTopologicalOrdering`, `Apply` |
| `DiscreteGarageState` | The in-memory state model that answers questions like “where is tray 19?” or “is AGV 4 disabled?” It is replayed and mutated repeatedly during planning. | `src/common_ros/include/common_ros/discrete_garage_state.hpp` (included; implementation not supplied) | `GetAgv`, `GetTray`, `OnEvent` |
| `GarageGraph` / `PoseGraph` | Graph structures used to map between node/heading poses and search vertices. These help the Scheduler and motion planner reason about movement feasibility. | `src/common_ros/include/common_ros/garage_graph.hpp` and `pose_graph.hpp` (included; bodies not supplied) | `GetVertexFromPose`, `GetPoseFromVertex` |
| `GarageOccupancyChecker<T>` | An occupancy/dependency helper that remembers who currently blocks a pose and which event would free it. This helper is especially relevant when tray moves and AGV arrivals must wait on one another. | `src/common_ros/include/common_ros/garage_occupancy_checker.hpp` (included; body not supplied) | `GetBlockers`, `AddOccupant` |
| `CollisionTable` | A geometry / compatibility helper used by the Scheduler to reject incompatible co-occupancy and movement combinations. The exact class definition was not included in the uploaded snapshots, but its role is visible through its use sites. | Exact class declaration not established by snapshots | `Query` (used by Scheduler) |
| `MotionCostModel` | A cost / duration model for estimating travel- and action-related costs. It supplies the timing assumptions that later influence assignment and scheduling. | `cost_functions/motion_cost_model.hpp` (included; body not supplied) | `Params` |

![Current class relationships](figures/11_uml_existing_core.svg)

*Figure 4 — Existing core-class relationships. `Scheduler` orchestrates planning, `ScheduleContext` packages one plan attempt’s mutable working data, `ScheduleEventDag` stores abstract event dependencies, and `DiscreteGarageState` models the world that those events mutate. The diagram is intentionally compact, so it shows the dominant ownership / usage relationships rather than every helper member.*

If you are looking for the shortest possible mental model, use this one: **`Scheduler` is the conductor, `ScheduleContext` is the score currently being annotated, `ScheduleEventDag` is the dependency structure of abstract work, and `DiscreteGarageState` is the simulated world on which the work is replayed.**

## 6. Objects and ownership: the Scheduler and ScheduleContext

A `Scheduler` is constructed with a layout path, an ROS logger, and parameters. It constructs layout, pose/garage graphs, collision table, and motion cost model. Its `Plan()` creates **a new context for one planning request**:

```cpp
// From scheduler.cpp, simplified to show essential ownership.
auto [initial_state_opt, validate_message] =
    ValidateBaseState(request_data.base_state, *layout_);
// ... error handling and base-schedule resource filtering ...
ScheduleContextSPtr plan_ctx =
    std::make_shared<ScheduleContext>(request_data.id,
                                      std::move(initial_state), now);
plan_ctx->disabledness_filters =
    volley::GetDisabledEntitiesFilters(gg_, plan_ctx->initial_state, table_);
```

`ScheduleContext` is **not** a ROS message or a template. It holds the planning request ID, the initial discrete state, a mutable event DAG, scheduled jobs, and several maps that help maintain dependencies. A `const` Scheduler method can still mutate the object referenced by a non-const shared pointer argument.

```cpp
// From scheduler.hpp, abridged — member names preserved.
class ScheduleContext {
 public:
  volley::DiscreteGarageState initial_state;
  volley::ScheduleEventDag events;
  std::vector<ScheduledJobDataMsg> scheduled_jobs;
  GarageEntityEventMap last_entity_event;
  std::unordered_map<uint16_t, ScheduleEventSPtr> first_tray_event;
};
```

**Why does `first_tray_event` exist?** The tray solver records the first event that clears a tray's *initial* node, so a later AGV navigation move can depend on that departure. Depending on the last move instead can create a dependency cycle when the same tray moves multiple times.

## 7. Event types and polymorphism

At this point we can finally explain `ScheduleEventDag` cleanly, because we now know what a **schedule event** is. A `ScheduleEvent` is an in-memory C++ object representing an abstract operation that can be replayed against a `DiscreteGarageState`. The base class is intentionally small: it provides a virtual destructor, a virtual `Apply(...)`, and query functions such as `GetGarageEntityId()`.

The key design idea is **runtime polymorphism**. The DAG stores `std::shared_ptr<ScheduleEvent>`, but at runtime those pointers may actually point to `TrayMove`, `AgvMove`, `BayTransition`, `VecsTransition`, or `VrcTransition` objects. When the Scheduler replays the DAG, the correct subclass implementation of `Apply(...)` runs through virtual dispatch.

![Existing event inheritance](figures/12_uml_event_hierarchy.svg)

*Figure 5 — Existing C++ inheritance hierarchy, not proposed solver architecture. A **hollow triangle** means public inheritance and points toward the base class. Blue marks the abstract base type, green marks movement / assignment events, and violet marks other resource-transition events. The arrow therefore reads as “`TrayMove` **is a** `ScheduleEvent`,” not “`ScheduleEvent` contains a `TrayMove`.”*

This figure often causes two kinds of confusion:

1. The inheritance arrow does **not** mean execution order. It only expresses the C++ type relationship.
2. The subclasses are **siblings**, not phases. For example, a `TrayMove` does not “turn into” an `AgvMove`; rather, both appear as separate event objects in the overall event DAG.

```cpp
// Abridged from planner_core/schedule_events.hpp.
class ScheduleEvent {
 public:
  virtual ~ScheduleEvent() = default;
  virtual BoolStringPair Apply(DiscreteGarageState& state) const = 0;
  virtual std::optional<GarageEntityIdMsg> GetGarageEntityId() const = 0;
};

class TrayMove : public ScheduleEvent {
 public:
  bool Assigned() const { return tray_id_ && dest_; }
  std::optional<uint16_t> GetTrayId() const { return tray_id_; }
  void SetTrayId(uint16_t id) { tray_id_ = id; }
  std::optional<GaragePoseMsg> GetDest() const { return dest_; }
  void SetDest(GaragePoseMsg dest) { dest_ = dest; }
  std::optional<uint16_t> GetAgvId() const { return agv_id_; }
  void SetAgvId(uint16_t id) { agv_id_ = id; }
};
```

A `TrayMove` is therefore **not an AGV command**. Before assignment, it may mean “find an empty tray for this bay” or “find somewhere to repark this specified tray.” `AgvMove` differs: it owns a `std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg>` and uses `std::visit` to apply one concrete discrete change. `BayTransition`, `VecsTransition`, and `VrcTransition` encapsulate other resource changes. The common base class lets all of them coexist inside the same `ScheduleEventDag`.

## 8. Directed acyclic graphs, then ScheduleEventDag

**First, ordinary graph theory.** A directed graph **$\mathcal G=(\mathcal V,\mathcal E)$** consists of vertices **$\mathcal V$** and directed edges **$\mathcal E\subseteq\mathcal V\times\mathcal V$**. An edge **$(u,v)\in\mathcal E$** means event **$u\in\mathcal V$** must precede event **$v\in\mathcal V$**. A DAG has no directed cycle; otherwise some operation would eventually require itself to complete first.

An ordering function **$\pi:\mathcal V\to\{0,\ldots,n-1\}$** assigns each vertex an index, where event count **$n=|\mathcal V|\in\mathbb N$**. A topological order satisfies:

$$
(u,v)\in\mathcal E\quad\Longrightarrow\quad\pi(u)<\pi(v).
$$

![Dependencies](figures/04_dependencies.svg)

*Figure 6 — Abstract prerequisite ordering. The arrows express dependencies, not geometric movement and not wall-clock travel time.*

**Now the implementation.** `DagBase<T>` is a C++ template implemented on a Boost `adjacency_list`; its vertices hold `std::shared_ptr<T>`. The specialized subclass `ScheduleEventDag : DagBase<ScheduleEvent>` stores abstract event objects and dependency edges between them. In practical terms, this means the Scheduler can ask questions such as “which work has no unsatisfied prerequisites yet?” or “if I add this dependency, would I create a cycle?” The custom topological ordering also biases earlier job indices among currently eligible events, so job grouping influences the replay order when multiple events are otherwise ready.

```cpp
// Representative of the existing scheduler_tests.cpp style.
auto ctx = std::make_shared<ScheduleContext>(request_id, state, rclcpp::Time{});
auto first = std::make_shared<TrayMove>(0u);
first->SetTrayId(15);
first->SetDest(ConstructGaragePose(19, 90));
auto second = std::make_shared<TrayMove>(0u);
second->SetTrayId(19);
second->SetDest(ConstructGaragePose(23, 90));
ctx->events.AddEvent(first);
ctx->events.AddEvent(second);
ctx->events.AddDependency(second, first); // move blocker before root
```

This **illustrative event graph is not a validated Pecos plan**. `AddDependency` checks for nonexistent vertices and duplicate edges but does not itself guarantee acyclicity; callers can use `WouldCreateCycle`, and a later topological sort fails when the graph has a cycle. `Reduce()` removes redundant dependency edges while retaining reachability. Because DAG vertices hold `shared_ptr`s, copying the DAG structure alone does **not** deep-clone event objects.

## 9. The complete planning pipeline

Only after the event types and graph are familiar does `Scheduler::Plan()` become straightforward:

1. Validate a `PlanRequestMsg` base state and account for resources in the base schedule.
2. Create `ScheduleContext`, then iterate `pending_jobs`, expanding supported job types into abstract event objects.
3. Run `DoTrayAssignments(ctx)` to complete missing tray IDs/destinations and insert prerequisite tray moves.
4. Run `DoAgvAssignments(ctx)` to choose AGVs, add reposition/lift events, and attach dependencies.
5. Reduce the event DAG, then sanity-check topological replay and feasibility.
6. Run motion planning, generating continuous trajectories, and convert those trajectories to a final action DAG and ROS `Schedule`.

The two assignment calls are ordered **tray first, AGV second**. `DoTrayAssignments` does *not* reduce dependencies at its own end: a source comment warns that reducing there can break subsequent AGV assignment.

## 10. Tray assignment and blocking trays

The tray assignment function does more than choose an ID: it modifies event objects **and** changes the DAG topology. It starts from a copy of `initial_state`, visits events in topological order, applies non-tray transitions, fills missing tray IDs or destinations, searches a critical tray route, and inserts blocking-tray relocations when necessary.

```cpp
// Source-derived excerpt; logging/error handling omitted.
auto working_state = ctx->initial_state;
auto total_ordering_opt = ctx->events.GetTopologicalOrdering();
GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>> freeing_moves(table_, gg_);

for (const auto& vertex : *total_ordering_opt) {
  auto event = ctx->events.GetEventFromVertex(vertex).value();
  if (event->GetType() != ScheduleEventType::TRAY_MOVE) {
    ApplyTransitionToFreeingMoves(event, working_state, freeing_moves);
    continue;
  }
  auto* move = dynamic_cast<TrayMove*>(event.get());
  if (!move->GetTrayId()) AssignTrayIdForEmptyMove(*move, working_state);
  if (!move->GetDest()) /* AssignDestForUntargetedMove(...) */;
  // For targeted moves: find critical path, resolve blockers, add DAG edges.
}
```

`ResolveBlockingTrays` can recursively relocate a blocker that is itself blocked; fallback behavior can advance the root tray and, under constraints, use waypoint stashing. A map of prior destinations prevents a blocking tray from oscillating endlessly between spots. The tests include `ResolveBlockingTraysRecursivelyUnblocksChain` and `TrayAssignmentTestComplexDag` as useful entry points.

## 11. Annotated AGV scenes from the Pecos layout

These three views replace the earlier generic AGV scenes. **Every node position and graph edge comes from the attached YAML**, while the shown AGV/tray occupancies and movement intents are *teaching examples*. Routes are graph walks, **not** asserted collision-free, trajectory-feasible schedules. For readability, labels appear outside objects, and location markers use prefixes `P` (parking), `W` (waypoint), `B` (bay), and `C` (AGV charge).

![Pecos overview with robot](figures/15_facility_topology.svg)

*Figure 7 — Facility overview. Bays `B7` and `B21` appear at the customer side of the graph. Parking positions and charger nodes are located at their YAML coordinates. The AGV and trays shown are explanatory stand-ins rather than measured occupancy.*

![Pecos AGV approach](figures/15_agv_approach_and_pickup.svg)

*Figure 8 — Unloaded approach example. A hypothetical AGV begins at charge node `C10` and approaches a hypothetical tray at `P3` via the connected sequence `10 → 9 → 11 → 6 → 3`. The green arrows depict required navigation through graph nodes. The eventual lift and tray-carrying segment are separate scheduling concerns, not represented as an actual recorded run.*

![Pecos blocker scenario](figures/15_blocking_tray_move.svg)

*Figure 9 — Blocking-tray reasoning example. A hypothetical root tray is at `P15`, a hypothetical blocker is at `P19`, and the amber and green routes show distinct proposed graph walks. This figure illustrates **why relocation decisions and dependencies must be jointly reasoned about**. It does **not** claim `P19` is necessarily a collision blocker in this layout or that the displayed route is accepted by the current solver.*

The reason the planner uses pose graphs rather than simple straight-line geometry is that valid transitions depend on graph edges, headings, and collision footprints. For two planar positions **$\mathbf p_a,\mathbf p_t\in\mathbb R^2$**, the displacement **$\Delta\mathbf p=\mathbf p_t-\mathbf p_a\in\mathbb R^2$** is useful to draw, but its Euclidean length **$d=\|\Delta\mathbf p\|_2\in\mathbb R_{\ge0}$** does *not* establish that a valid AGV path exists.

## 12. AGV assignment, timing, and dependency repair

`DoAgvAssignments` starts with a copy of the initial state and returns early when there are no tray moves. It identifies candidate AGVs, estimates move costs, assigns robots to eligible tray moves, and adds positioning/lifting and resource-occupancy dependencies. Cost helper methods include `GetJustMovingCost`, `GetAgvCurrentPoseToTrayMoveCost`, and `GetAgvToTrayAssignmentCost`.

The direct helper cost relation in the supplied source is:

$$
c_{ij}=t_i^{\mathrm{occupied}}+t_{ij}^{\mathrm{approach}}+t_{ij}^{\mathrm{lift}},
$$

where cost **$c_{ij}\in\mathbb R_{\ge0}$** estimates assignment of AGV **$i\in\{1,\ldots,m\}$** to tray move **$j\in\{1,\ldots,n\}$**, with AGV count **$m\in\mathbb N$**, move count **$n\in\mathbb N$**, occupied time **$t_i^{\mathrm{occupied}}\in\mathbb R_{\ge0}$**, approach time **$t_{ij}^{\mathrm{approach}}\in\mathbb R_{\ge0}$**, and lift time **$t_{ij}^{\mathrm{lift}}\in\mathbb R_{\ge0}$**, all durations in seconds. **Caveat:** `GetAgvOccupiedDuration` currently returns zero by implementation comment, so this is not a complete predictive queueing model.

Separate code tries to prevent one AGV from reaching a node before its previous AGV occupant has departed. The source's `EnsureAgvMovePathsClear` and related methods address cases where the assignment-time serial order differs from eventual DAG topological replay. A graph can be acyclic yet still have physically invalid operations; hence the later sanity check.

## 13. Motion planning and final ActionNode messages

`PlanMotions` consumes the assigned, ordered event plan. `ResponseFromTrajectories` converts motions into `ActionNodeMsg` values, relates their first and last actions to originating events, transfers event-DAG dependencies, and emits a topologically ordered action list with `parents` indices. `ActionNode.msg` defines separate command fields for AGVs, bays, VECS, and VRCs. The scheduler implementation does not itself verify real hardware acknowledgments or control motor dynamics.

## 14. VRC, bays, and charging resources

A bay and VRC are not interchangeable: bay commands orchestrate customer handoff and state transitions, while `VrcTransition` models a vertical transfer between floor-specific nodes. In `schedule_events.cpp`, `VrcTransition::Apply` simulates VRC idle→moving→idle, then updates AGVs and remaining trays at the source node. This is **discrete-state simulation**, not the complete lift/door-controller implementation.

![VRC conceptual transfer](figures/14_vrc_floors.svg)

*Figure 10 — Conceptual VRC connecting two floors. The Pecos YAML does not contain a VRC; the diagram represents general code-supported functionality and is not placed on the Pecos map.*

The Pecos YAML does include two `Bay` nodes and three `AgvCharge` nodes. The ROS types also define VECS charging state and `TYPE_EV_CHARGE` nodes, but no such explicit node appears in this particular YAML. Do not infer a VECS station or VRC from the mere presence of a generic interface.

## 15. Packages, build system, and dependencies

| Package | Source of truth | Verified responsibilities and dependencies |
|---|---|---|
| `interfaces` | `msg/`, `srv/`, `CMakeLists.txt` | Generates ROS messages/services, references `vrc_interfaces`, `geometry_msgs`, and `std_msgs` |
| `planner_core` | `src/planner/planner_core/{include,src}` | Event hierarchy and event DAG; depends on `common`, `common_ros`, `interfaces`, `rclcpp`, `vrc_interfaces` |
| `scheduler` | `src/planner/scheduler/{include,src}` | Job expansion, assignments, motion planning orchestration; depends on `planner_core`, `motion_planner`, `task_planner`, `cost_functions` and other ROS packages |
| `scheduler_advanced_tests` | `src/planner/scheduler_advanced_tests` | Scenario-oriented `Scheduler::Plan` test executables |

The build uses CMake and ROS 2 `ament_cmake`, with repository-specific `volley_cmake` macros (`volley_package`, `volley_add_library`, `volley_add_component`, `volley_add_gtest`). The build files establish `scheduler → planner_core`. **`planner_core` is not ROS-free**, since its manifest already names ROS dependencies. Moving implementation between packages requires checking CMake and package dependency direction.

## 16. C++ concepts and idioms in context

| Idiom | Meaning | Concrete source usage | Key pitfall |
|---|---|---|---|
| `std::shared_ptr<T>` | Shared lifetime of an object | DAG vertices hold shared event objects | Copying DAG structures aliases event objects |
| `std::optional<T>` | An explicitly missing value | Unresolved `TrayMove::GetDest()` | `nullopt` is an expected planning state |
| Inheritance / `virtual` / `override` | Runtime polymorphism | `ScheduleEvent` and subclasses | Preserve concrete event semantics |
| `dynamic_cast` | Runtime-checked downcast | `Scheduler` retrieves `TrayMove*` from a base event | Check type before using subtype members |
| `std::variant` / `std::visit` | One of several distinct message alternatives | `AgvMove` contains lift **or** pose change | The alternatives have different fields |
| Structured bindings | Unpack pair/tuple results | `auto [success, message] = ...` | Success flag and response `success` have different semantics |
| `const` method | Cannot mutate ordinary members through `this` | `DoTrayAssignments(ctx) const` | Can mutate `*ctx` reached via pointer |
| Templates | Generic code instantiated for concrete type | `DagBase<T>` and `GarageOccupancyChecker<T>` | C++ headers must expose necessary definitions |
| `std::move` | Enables move semantics | Moving `initial_state` into context | Does not deep-copy shared event objects |
| ROS IDL generation | Compiles `.msg` / `.srv` into language types | `rosidl_generate_interfaces` | Field names and wire types are contracts |

## 17. Known limitations and reading checkpoint

The available sources establish the Scheduler's high-level planning pipeline, event hierarchy, DAG implementation, helper signatures, ROS contracts, and the actual Pecos layout topology. They do **not** provide the complete implementations of `GarageGraph`, `CollisionTable`, `GarageOccupancyChecker`, `BottleneckAssignment`, motion-planner search, Dispatcher, AGV firmware, or the Pecos garage's current occupancy. Those details must not be inferred from a schematic figure.

**Before reading `02-issue-and-proposal.md`, verify you can answer:** What is the distinction between job/event/motion/action? Why is `GaragePose` not a geometric pose? What makes a `TrayMove` incomplete? What does an edge in `ScheduleEventDag` signify? Why is `first_tray_event` passed from tray assignment to AGV assignment? How does a bay differ from a VRC? And why does `Scheduler::Plan` need both discrete-state replay and motion planning?

### Source index

- `src/planner/scheduler/include/scheduler/scheduler.hpp` — Scheduler, context, helper declarations
- `src/planner/scheduler/src/scheduler.cpp` — orchestration, tray and AGV assignment, motion conversion
- `src/planner/planner_core/include/planner_core/schedule_events.hpp` — event hierarchy
- `src/planner/planner_core/include/planner_core/event_dag.hpp` — Boost DAG container
- `src/planner/planner_core/src/{event_dag,schedule_events}.cpp` — event order and state-change behavior
- `src/planner/scheduler/test/scheduler_tests.cpp` — existing illustrative and regression fixtures
- `src/interfaces/msg/*.msg`, `src/interfaces/srv/*.srv` — generated interface definitions (supplied as Repomix XML)
- `5675_pecos_combined.yaml` — coordinates, node metadata, and graph edges for figures 2, 7–9
