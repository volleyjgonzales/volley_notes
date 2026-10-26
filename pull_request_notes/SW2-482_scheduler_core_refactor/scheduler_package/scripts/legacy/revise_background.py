from pathlib import Path
p=Path(__file__).resolve().parent.parent/'01-software-background.md'
s=p.read_text()
s=s.replace('**Figure 3 — Top-down garage setup.** AGV 1 faces the positive $x$ direction. Trays T2 and T3 lie along the illustrative route to the goal. Coordinates are schematic; node IDs and distances are not an actual customer layout.','**Figure 3 — Parking-structure overview.** A top-down schematic shows an AGV in the drive aisle, striped parking bays, a customer access bay, a vertical reciprocating conveyor (VRC), an EV charging station (VECS), and a blocked parking position. The parking-space ID labels sit above each stall, while `GOAL` sits below its stall so labels do not overlap. The graphics demonstrate topology, not any specific installed garage dimensions or actual collision geometry.')
s=s.replace('AGV 1 faces the positive $x$ direction. Trays T2 and T3 lie along the illustrative route to the goal.','An AGV travels along an aisle to reach a tray or destination.')
extra=r'''

---

# Part II — The existing software, explained from first principles

> **Reading strategy:** Sections 12–20 introduce the physical garage, ROS data contracts, classes, control/data flow, and failure modes *as implemented today*. This part is intentionally descriptive rather than a proposal. Class names and methods here are observed in the uploaded source; the corresponding implementation file is provided in the tables. Examples labeled **excerpt** are shortened for explanation.

## 12. Think of the software as four layers

A user asks for work, such as retrieving a vehicle from a parking space and delivering it to a customer bay. The system's responsibilities split across four abstraction levels: (1) external requests and resource status, (2) scheduling jobs into abstract event constraints, (3) producing continuous vehicle motions, and (4) issuing entity-specific actuator commands. The provided code establishes the Scheduler's middle two layers and the generated ROS message contracts; it does **not** include full Dispatcher, AGV firmware, or bay-device implementations. Those modules are described below only where the interfaces justify the relationship.

![Parking structure schematic](figures/10_parking_structure.svg)

**Figure 10 — Physical garage and software resources.** The schematic draws parking slots with trays, a drive aisle for an AGV, a customer-facing bay `b1`, a VRC connecting floors, and a VECS charge area. The dashed bay and VRC entrances represent controlled transfer boundaries. The arrow colors distinguish unloaded repositioning and tray-carrying movement. This is illustrative geometry, **not** a faithful customer installation or a collision-accurate map.

| Physical item | Scheduler concept | Represented in source | What is important |
|---|---|---|---|
| Autonomous guided vehicle (AGV) | `DiscreteAgvState`, `AgvMove`, `AgvCommand` | `msg/DiscreteAgvState.msg`, `planner_core/schedule_events.hpp`, `msg/AgvCommand.msg` | An AGV can move, rotate, raise/lower its lift, and carry a tray. |
| Tray | `DiscreteTrayState`, `TrayMove` | `msg/DiscreteTrayState.msg`, `planner_core/schedule_events.hpp` | Tray transport may begin without a chosen tray ID, destination, or AGV. |
| Payload (customer vehicle) | `Payload`, `DiscretePayloadState` | `msg/Payload.msg`, `msg/DiscretePayloadState.msg` | Size, mass and charging needs influence feasibility. |
| Customer bay | `DiscreteBayState`, `BayTransition`, `BayCommand` | `msg/DiscreteBayState.msg`, `planner_core/schedule_events.hpp`, `msg/BayCommand.msg` | Bay readiness and door/vehicle access must be sequenced with tray movement. |
| Vertical reciprocating conveyor (VRC) | `DiscreteVrcState`, `VrcTransition` | `msg/DiscreteVrcState.msg`, `planner_core/schedule_events.hpp` | Represents a floor transfer and changes floor-associated state. |
| EV charging system (VECS) | `DiscreteVecsState`, `VecsTransition` | `msg/DiscreteVecsState.msg`, `planner_core/schedule_events.hpp` | Charging actions require explicit state transitions and dependencies. |
| Parking stall / waypoint | `GarageNode` and `GaragePose` | `msg/GarageNode.msg`, `msg/GaragePose.msg` | Node types, accepted headings, geometry, floor, and resource-size windows matter. |

### Two kinds of location

The *continuous* geometric position $\mathbf p=[x,y]^\mathsf T\in\mathbb R^2$ uses coordinates $x,y\in\mathbb R$ in meters. The planar geometric pose $\mathbf q=[x,y,\theta]^\mathsf T\in\mathbb R^3$ adds the heading $\theta\in\mathbb R$ in radians (as modeled in `GeometricPose.msg`). In contrast, a logical `GaragePose.msg` contains a `node_id` and an integer `heading` in **degrees**. A `GarageNode.msg` supplies coordinates and floor index. **Do not conflate the `node_id` with a metric coordinate or a heading with an edge direction.** The ROS interface states headings are relative to garage-local north, with positive rotation counterclockwise (heading 90 points west).

```text
GeometricPose.msg                GaragePose.msg
--------------------             --------------------
float32 x  # meters             uint32 node_id
float32 y  # meters             int16 heading # degrees
float32 yaw # radians
```

The graph topology controls which pose-to-pose transitions are possible. Two adjacent physical parking spaces need not have a valid graph edge, and a nominally valid node may reject a particular heading or resource footprint.

## 13. Source map: the classes you should recognize immediately

A defining-file column distinguishes class definitions from mere mentions or generated message aliases. The shorthand `src/planner/` is expanded in the paths shown.

| Class / type | Responsibility | Defined in | Key API or fields | Why it matters |
|---|---|---|---|---|
| `Scheduler` | Orchestrates planning phases | `src/planner/scheduler/include/scheduler/scheduler.hpp` | `Plan`, `DoTrayAssignments`, `DoAgvAssignments`, `PlanMotions` | Entry point for this refactor; currently owns too many algorithms. |
| `ScheduleContext` | Mutable state of one planning attempt | `src/planner/scheduler/include/scheduler/scheduler.hpp` | `initial_state`, `events`, `scheduled_jobs`, `first_tray_event` | Carries results between phases; not a ROS message. |
| `SchedulerParams` | Constructor options | `src/planner/scheduler/include/scheduler/scheduler.hpp` | `motion_cost`, `bay_readiness_ratio` | Configures constructed graph/cost dependencies. |
| `DagBase<T>` | Directed acyclic graph operations using Boost | `src/planner/planner_core/include/planner_core/event_dag.hpp` | `Add`, `AddDependency`, `GetParents`, `GetChildren`, `Reduce` | Owns graph topology and maps shared pointers to vertices. |
| `ScheduleEventDag` | Specialization for schedule events | `src/planner/planner_core/include/planner_core/event_dag.hpp` | `AddEvent`, `GetTopologicalOrdering`, `Apply` | Supplies job-aware topological order. |
| `ScheduleEvent` | Abstract base for scheduled work | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | virtual `Apply`, `GetGarageEntityId` | Polymorphic element in the event DAG. |
| `TrayMove` | Abstract tray relocation | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `GetTrayId`, `GetDest`, `GetAgvId`, setters | Has optional, progressively resolved fields. |
| `AgvMove` | AGV motion or lift-change event | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `GetDiscreteChange`, `GetAgvId` | Uses `std::variant` to distinguish action types. |
| `BayTransition` | Bay state transition event | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `GetSourceState`, `GetCommand` | Must be ordered against tray arrival/departure. |
| `VecsTransition` | Charging state transition event | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `GetStateChange` | Models charging resource state. |
| `VrcTransition` | VRC movement between floors | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `GetFromVrcNodeId`, `GetToVrcNodeId`, `Apply` | Its `Apply` updates floor/resource state and transfers riders. |
| `DiscreteGarageState` | Current simulated discrete occupancy and resource state | `src/common_ros/include/common_ros/discrete_garage_state.hpp` *(header included by Scheduler; body not uploaded)* | `GetAgv`, `GetTray`, `OnEvent` | Methods used widely; complete class internals require the source. |
| `GarageGraph` | Heading-aware navigation graph | `src/common_ros/include/common_ros/garage_graph.hpp` *(included, not supplied)* | `GetVertexFromPose`, `GetPoseFromVertex` | Maps logical poses into search vertices. |
| `PoseGraph` | Intermediate graph associated with layout | `src/common_ros/include/common_ros/pose_graph.hpp` *(included, not supplied)* | Constructed from `Layout` | Precise semantics need its source. |
| `CollisionTable` | Occupancy/conflict queries | Declaration location **not established** by snapshots | `Query` | Blocks invalid moves; avoid inferring its full algorithms. |
| `GarageOccupancyChecker<T>` | Tracks occupancy and freeing dependencies | `src/common_ros/include/common_ros/garage_occupancy_checker.hpp` *(included, not supplied)* | `GetBlockers`, `AddOccupant` | Adds DAG edges for previous occupants. |
| `MotionCostModel` | Path and motion-cost parameters | `src/planner/cost_functions/include/cost_functions/motion_cost_model.hpp` *(inferred from include path; body not supplied)* | `Params()` | AGV cost estimates depend on this. |
| `Layout` | Layout graph and resource definitions | `src/common_ros/include/common_ros/layout.hpp` *(included, not supplied)* | `GetNodes`, `GetMD5Sum` | Converts site layout data into useful planning structures. |
| `ContinuousState` | Represents resulting timed trajectories | `src/planner/motion_planner/include/motion_planner/continuous_state.hpp` *(included, not supplied)* | `GetTrajectories` | Output of motion-planning phase. |

**Evidence limitation:** The newly supplied `repomix-interfaces.xml` covers ROS `.msg` and `.srv` definitions, not implementations of `GarageGraph`, `CollisionTable`, or the Dispatcher. The names in the final rows identify files included by Scheduler, not independently verified full class declarations.

![As-built core relationships](figures/11_uml_existing_core.svg)

**Figure 11 — Existing Scheduler, context, DAG and event relationships.** This UML-style structural drawing is **as built**, not the proposed `TrayMoveSolver` hierarchy. The `Scheduler` creates/passes planning context; the context contains the event DAG and initial state; the DAG stores `ScheduleEvent` objects through shared pointers. Attribute visibility follows the accessible source; the arrows communicate reference/containment dependencies, not ownership guarantees of each pointer.

## 14. The `ScheduleEvent` hierarchy (existing C++ inheritance)

![As-built event classes](figures/12_uml_event_hierarchy.svg)

**Figure 12 — Existing polymorphic event classes.** All five listed concrete types derive publicly from `ScheduleEvent`. `TrayMove` can be partially specified, `AgvMove` packages a lift change or pose change, and transitions represent bay, charger, and VRC state changes. This is an overview of names and relevant fields; method lists are selective rather than exhaustive.

An excerpt of actual source (`planner_core/schedule_events.hpp`) shows what makes `ScheduleEvent` abstract:

```cpp
class ScheduleEvent {
 public:
  virtual ~ScheduleEvent() = default;
  virtual BoolStringPair Apply(DiscreteGarageState& state) const = 0;
  virtual std::optional<GarageEntityIdMsg> GetGarageEntityId() const = 0;
  unsigned int GetJobIndex() const { return job_idx_; }
  ScheduleEventType GetType() const { return type_; }
 private:
  ScheduleEventType type_;
  unsigned int job_idx_;
};
```

The `= 0` syntax means a *pure virtual function*: you cannot instantiate `ScheduleEvent` directly. A `std::shared_ptr<ScheduleEvent>` can point to a `TrayMove`, `AgvMove`, or any transition, and calling `event->Apply(state)` dispatches to the dynamic type. This pattern is **runtime polymorphism**, distinct from compile-time templates. In the current implementation, `dynamic_cast<TrayMove*>(event.get())` appears after checking an event's type. That cast is safe only if the type tag and actual C++ dynamic type remain consistent.

`TrayMove::Assigned()` is implemented as `return tray_id_ && dest_;`, and notably **does not require an AGV ID**. This is intentional separation of the *tray-resolution* and *AGV-assignment* phases. Before tray assignment, the tray ID or destination may be absent; after tray assignment those should be resolved; after AGV assignment the assigned AGV should be known for transport events.

`AgvMove` stores a `std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg>`, representing **one of** two alternative message types in a type-safe union. Its `Apply` uses `std::visit` to apply the active message to the working garage state.

## 15. ROS message/service model: how jobs become executable actions

![ROS message contracts](figures/13_uml_ros_messages.svg)

**Figure 13 — Existing generated ROS message relationships.** The `PlanRequest` message supplies the base garage state, previous immutable schedule, and pending jobs; the `PlanResponse` carries an updated `Schedule` and associated job metadata. A `Schedule` is an array of `ActionNode` messages; an `ActionNode` records action type, IDs, and parent indices. These are **ROS data messages**, not inheriting C++ classes.

The new `repomix-interfaces.xml` confirms that `srv/Plan.srv` wraps a `PlanRequest` and `PlanResponse`:

```text
# srv/Plan.srv — actual source
PlanRequest request_data
---
PlanResponse response_data
```

The request includes `base_state`, `base_schedule`, `planned_jobs`, `active_jobs`, and `pending_jobs`. The `base_schedule` is documented as the **immutable portion** of the currently executing schedule. This is relevant to concurrent planning, but the solver-extraction task should not attempt to redesign additive scheduling.

An `ActionNode` has a `type`, a `parents` array, a unique `guid`, and a `duration`. For each type, the message contains fields such as `agv_command`, `bay_command`, `vecs_command`, or `vrc_command`. Parent entries are **indices** into the `Schedule.nodes` array rather than raw pointers. The `.msg` contract states that schedule nodes are provided in a topological order.

```text
# Excerpts from actual .msg definitions
# msg/Schedule.msg
ActionNode[] nodes

# msg/ActionNode.msg
uint32[] parents
uint8 type
AgvCommand agv_command
BayCommand bay_command
VecsCommand vecs_command
VrcCommand vrc_command
```

An `AgvCommand` specifies *full* source and destination `AgvGoal` values, each with a pose and lift state. Its `.msg` comments distinguish translate (node differs), rotate (heading differs), and lift (lift bit differs). **The output `AgvCommand` is a concrete actuator-level contract, whereas an intermediate `TrayMove` is still a request for higher-level transportation.**

### A concrete end-to-end trace

Take a `SchedulerJob::TYPE_MOVE_TRAY` requested through `MoveTray.srv`. The `.srv` fields include a tray ID and target `GaragePose`. The Scheduler builds a `TrayMove` in its event DAG; tray assignment resolves feasibility and possible blockers; AGV assignment determines which AGV moves the tray and inserts reposition/lift events; motion planning builds trajectories; `ResponseFromTrajectories()` constructs the final `ActionNode` DAG. **The actual wire-level service route between request-producing components is not established by the supplied source**, so this trace begins at the documented service contract and the observed Scheduler planning API rather than claiming a verified service call stack.

## 16. Building a schedule DAG in C++

```cpp
// Based on code idioms present in scheduler_tests.cpp; simplified example.
auto ctx = std::make_shared<volley::ScheduleContext>(
    request_id, initial_state, rclcpp::Time{});

auto a = std::make_shared<volley::TrayMove>(0u);
a->SetTrayId(7);
a->SetDest(volley::ConstructGaragePose(12, 0));

auto b = std::make_shared<volley::TrayMove>(0u);
b->SetTrayId(8);
b->SetDest(volley::ConstructGaragePose(14, 0));

ctx->events.AddEvent(a);
ctx->events.AddEvent(b);
ctx->events.AddDependency(a, b);  // a must precede b

const auto order = ctx->events.GetTopologicalOrdering();
if (!order) {
  throw std::runtime_error("The event DAG contains a cycle");
}
```

The shared ownership matters. `DagBase<T>` stores shared pointers to event objects; copying the graph does **not** automatically deep-copy event objects. If one solver changes `a->SetDest(...)`, another reference to `a` sees that change. This matters for test fixture isolation and for using both old and new solvers on separate copies of the same logical problem.

The C++ syntax `auto [success, message] = scheduler.DoTrayAssignments(ctx);` is a **structured binding**: it destructures a `std::pair<bool, std::string>` (`BoolStringPair`) into named local variables. `std::optional<T>` models missing information without a sentinel value, and `std::move` may transfer ownership or avoid copies depending on the type and overload; it does not guarantee a move actually occurs.

## 17. DAG algorithms and the actual output contract

The event DAG $\mathcal G=(\mathcal V,\mathcal E)$ contains event vertices $v\in\mathcal V$ and prerequisite edges $e=(u,v)\in\mathcal E$. The topological order $\boldsymbol\pi\in\mathbb N^{n}$, for event count $n\in\mathbb N$, must satisfy $\pi(u)<\pi(v)$ for every edge $e=(u,v)$. The numeric event order is not necessarily the order in which edges or vertices were inserted. The code prioritizes currently available events by job index.

```cpp
// Real DagBase<T>::AddDependency() behavior, abbreviated.
bool AddDependency(const Vertex& parent, const Vertex& child) {
  if (!HasVertex(parent) || !HasVertex(child)) return false;
  if (HasDependency(parent, child)) return false;
  boost::add_edge(parent, child, dag_);
  return true;
}
```

**Important:** The abbreviated function checks vertex existence and duplicate edges but does not check for a cycle. The separate `WouldCreateCycle()` helper exists, and the code checks `GetTopologicalOrdering()` for failure later. A returned `true` from `AddDependency` means an edge was added, not that the *whole graph is acyclic*.

`Reduce()` removes transitively redundant dependencies after AGV assignment. Suppose we have `A -> B -> C` and also `A -> C`; the direct `A -> C` edge can be removed without changing reachability. The existing tray-assignment implementation explicitly comments that calling `Reduce()` early may break AGV assignment; the reason should be covered by regression tests rather than presumed fixed by moving code.

## 18. Why a parking structure needs more than ordinary shortest-path routing

![Blocked parking lane](figures/03_garage_xy.svg)

**Figure 3 revisited — Blocker relocation inside a parking structure.** A requested tray cannot always reach its destination simply because an empty stall exists. A blocking tray may occupy a necessary aisle-side waypoint or have a collision footprint covering the route. The amber and green arrows represent *different logical dependencies*, not collision-tested trajectories. The label for stall `P8` is above the stall and the label `GOAL` is below the target stall, eliminating the previous overlap.

The graph route $\boldsymbol\gamma=(v_0,v_1,\ldots,v_k)$ has $k+1\in\mathbb N$ pose vertices. Each vertex $v_j\in\mathcal V_g$ represents a graph pose and each adjacent pair $(v_j,v_{j+1})$ must be a feasible graph edge; the actual graph $\mathcal G_g=(\mathcal V_g,\mathcal E_g)$ is heading-aware. A collision test depends on the entity's envelope and the pose, not just whether another tray's center lies at the same node. The exact `CollisionTable` representation has not been provided.

A blockage may create a dependency chain: first move a rear blocker, then a front blocker, then the requested tray. In the existing implementation this is handled by `ResolveBlockingTrays`, including recursion and a fallback that may temporarily stash trays at waypoint nodes. The test `ResolveBlockingTraysRecursivelyUnblocksChain` in `scheduler_tests.cpp` supplies a concrete fixture designed for this behavior.

### An AGV executing a tray move

An abstract `TrayMove` does not say how the AGV reaches the tray. The AGV assignment stage may add an `AgvMove` to reposition the robot and another `AgvMove` to lift, then connect those actions with the tray move. The state simulation requires the AGV to be at the tray pose with its lift raised and carrying that tray before the assigned `TrayMove::Apply` can succeed. Actual moving/rotating/lifting constraints are spelled out in `AgvCommand.msg`.

## 19. Multiple floors and VRC transitions

![Two garage floors connected by a VRC](figures/14_vrc_floors.svg)

**Figure 14 — Multi-floor structure.** The left rectangle depicts one floor, the right another. They are shown side-by-side solely for clarity. The VRC transfers its contents between floors; this is not a claim that a vehicle drives through the horizontal connector in physical space. Floor IDs in the drawing are illustrative.

`VrcTransition` is particularly instructive because it has a concrete `Apply()` implementation in `planner_core/src/schedule_events.cpp`. It first advances the VRC from `IDLE` to `MOVING`, then to `IDLE` at the requested floor. It then updates AGVs present at the source VRC node using pose-change events and updates trays that remain on that node using manual tray pose changes. If a tray is being carried, the AGV pose-change machinery is expected to move it with the AGV. This is **discrete state simulation**, not a claim about the exact VRC motor controller's state machine.

The `DiscreteVrcState.msg` interface includes an ID, current floor, requested floor, a VRC state, and gate reports. `GarageNode.msg` includes `floor`, `TYPE_LIFT`, and `TYPE_BLIFT` among supported node types. A `BayCommand.msg` also includes `COMMAND_TYPE_MOVE_LIFT_TO_FLOOR` for BLift-type bays. Those details are essential when interpreting a multi-floor schedule or investigating why a topologically valid sequence might still violate a floor/gate constraint.

## 20. C++ and ROS patterns: a compact reference for navigating the repository

| Pattern / idiom | Meaning | Concrete usage | Pitfall for this refactor |
|---|---|---|---|
| Inheritance and virtual dispatch | Different concrete events satisfy the same base API | `ScheduleEvent`, `TrayMove`, `AgvMove` | Solver replacement must preserve event semantics. |
| `std::variant<A,B>` | Holds exactly one of two alternatives | `AgvMove::discrete_change_` | Use `std::visit` or `holds_alternative`; cannot assume pose change. |
| `std::optional<T>` | Value may be absent | `TrayMove::GetDest()` / `GetTrayId()` | `nullopt` is expected before assignment, not necessarily an error. |
| `std::shared_ptr<T>` | Shared lifetime and aliasing | DAG vertex bundle and event references | Shallow copying a DAG aliases event objects. |
| `std::dynamic_pointer_cast` / `dynamic_cast` | Runtime downcast with failure detection | Scheduler casts a generic event to `TrayMove` | Check that actual dynamic type agrees with type tags. |
| `std::tie` / structured bindings | Unpack tuples or pairs | Solver `(success, message)` return values | Failure message should remain available after extraction. |
| `const` member function | Method cannot mutate ordinary members through `this` | `DoTrayAssignments(...) const` | It **can** mutate objects reached via a mutable pointer argument. |
| Templates | Compile-time generalization | `DagBase<T>`, `GarageOccupancyChecker<T>` | Place template definitions where instantiation can see them. |
| `rosidl_generate_interfaces` | Generates C++/ROS types from `.msg` and `.srv` | `interfaces/CMakeLists.txt` | Message names and field types are wire contracts, not arbitrary structs. |
| `rclcpp::Logger` | ROS logging handle | Scheduler constructor and helper logs | Avoid making the generic contract dependent on a specific logger unless required. |
| `ament_cmake` and package manifests | ROS package build/dependency graph | `planner_core/package.xml`, `scheduler/package.xml` | New dependencies must not create cycles. |
| `Boost.Graph` | Graph storage/traversal library | `DagBase<T>` | Vertex IDs can shift after removal; use graph APIs carefully. |

### What is established vs still unknown

The provided source establishes Scheduler phase ordering, the context fields, event hierarchy, DAG implementation, current tests, package manifests, and the ROS interface contracts listed above. It does not establish the full Dispatcher implementation, the true site layout geometry, exact collision-envelope algorithms, the internals of `BottleneckAssignment`, full CHUGG/SIPP details, or device-firmware behavior. Those must be read from their own source packages before confidently documenting internal execution details.

### Reading checkpoint

Before opening the issue proposal, you should be able to explain: (1) why a `SchedulerJob` is not an `ActionNode`, (2) why `GaragePose` is different from `GeometricPose`, (3) what it means for a `TrayMove` to be partly assigned, (4) why a DAG dependency is directed from prerequisite to dependent, (5) what `VrcTransition::Apply()` changes in discrete state, (6) why `ScheduleContext` is mutable even though solver methods are declared `const`, and (7) why assigning an AGV is separate from finding a route for its tray.
'''
s+=extra
p.write_text(s)
print('background chars',len(s))
