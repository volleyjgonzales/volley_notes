# 01 — Scheduler software background

*A ground-up guide to the `scheduler` ROS 2 package for engineers who are new to the team. It is written against the package snapshot in `sources/repomix-scheduler.xml` (headers, sources, tests, CMake and `package.xml`), the ROS interface definitions, and the `5675_pecos_combined.yaml` facility layout.*

> **Scope and evidence.** This guide documents the *existing* implementation, not the proposed solver refactor (that is [02](02-issue-and-proposal.md)). Everything labelled **AS-BUILT** was checked against `scheduler.hpp`, `scheduler.cpp`, `utils.cpp`, `scheduler_ros.cpp` and `scheduler_component.cpp`. Code from other packages (`planner_core`, `common_ros`, `motion_planner`, `task_planner`) was **not** in the snapshot; where this guide describes it, it does so from call sites and says so. The Pecos figures use real node positions and edges, but **AGV, tray and payload occupancy is hypothetical**. The Pecos YAML has bays and chargers but **no VRC**.

> **Viewing the figures.** Markdown previews (VS Code, GitHub) show SVGs as static images, so the figures are drawn to be readable at preview width. For pan and zoom, open [`figures/viewer.html`](figures/viewer.html) in a browser (all figures, scroll to zoom, drag to pan, arrow keys to switch), or open any `.svg` file directly in a browser. Every figure carries a status badge: **AS-BUILT**, **PROPOSED**, **ILLUSTRATIVE**, **SCHEMATIC**, **CONCEPTUAL**, or **YAML GEOMETRY · HYPOTHETICAL OCCUPANCY**.

## How to use this guide

Read it in three passes. Each pass is useful on its own.

| Pass | Read | You will be able to |
|---|---|---|
| 1 · Orientation (30 min) | Sections 1–5 | Say what the scheduler is for, where it sits in the ROS system, and how it models the garage |
| 2 · Data and objects (1 h) | Sections 6–11 | Name the main types, who owns them, and follow one `Plan()` call from request to response |
| 3 · Algorithms (2 h, with the code open) | Sections 12–18 | Explain job expansion, tray assignment, AGV assignment, motion planning and bay rebalancing |

Then work through the checkpoint questions in section 22, run one test from section 20 under a debugger, and keep section 21 (C++ idioms) open as a reference.

### How to read the code snippets

Every snippet starts with a **Where** line that names the function it comes from and what each variable is. Snippets are abridged (logging and some error handling removed) but keep the real names. These names recur everywhere, so learn them once:

| Name in the code | Type | What it is |
|---|---|---|
| `this` inside `Scheduler::...` | `const volley::Scheduler*` | The one long-lived planner object owned by `SchedulerRos`. Its members end in `_` |
| `layout_` | `LayoutSPtr` (`std::shared_ptr<Layout>`) | Parsed layout YAML: nodes, edges, bays, floors, resource windows |
| `gg_` | `volley::GarageGraph` | Search graph over (node, heading) poses; used by every path query |
| `table_` | `volley::CollisionTable` | Answers “do these two footprints at these two poses collide?” |
| `cost_model_` | `cost::MotionCostModel` | Speeds, accelerations, lift and door times from ROS parameters |
| `request_data` | `const PlanRequestMsg&` | The incoming `interfaces/msg/PlanRequest` |
| `plan_ctx`, `ctx` | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | All mutable data for **one** plan call |
| `ctx->events` | `volley::ScheduleEventDag` | The event DAG that every stage reads and extends |
| `working_state` | `volley::DiscreteGarageState` (a value, not a reference) | A scratch copy of the garage, advanced by replaying events |
| `event` | `std::shared_ptr<volley::ScheduleEvent>` | One vertex of `ctx->events` |
| `move`, `tray_move` | `volley::TrayMove*` (from `dynamic_cast`) | The same event viewed as its concrete subclass |
| `*_opt` | `std::optional<...>` | Lookups that may fail, for example `working_state.GetTray(id)` |
| `[success, message]` | `BoolStringPair` (a `bool` plus a `std::string`) | The return convention of almost every planning method |
| `job_index` | `size_t` | Position of the job in `ctx->scheduled_jobs`; stored in every event it creates |

## 1. What problem does this software solve?

A customer vehicle sits on a **tray** inside an automated parking facility. An **AGV** (automated guided vehicle) drives under a tray, raises its lift, and carries the tray. A **bay** is the customer-facing handoff room; a **waypoint** is a navigation node; a **parking node** is where trays are stored; an **AGV charge** node is where robots recharge. Some installations have a **VECS** (EV charging station under a parking node) or a **VRC** (vertical reciprocating conveyor, a lift between floors). These are different resources with different rules.

A job such as **retrieve this payload** does not say how to do it. The Scheduler decides which tray moves are needed, which AGV does each one, which operations must happen first, and how long everything takes. It then returns a schedule of discrete commands that Dispatch executes. The scheduler never drives a motor and never talks to an AGV directly.

The key distinction is **what** should happen versus **how and when** it happens:

| Layer | Question | Example | Where it lives |
|---|---|---|---|
| Job | What outcome is requested? | Retrieve a payload | `SchedulerJob.msg` |
| Event | What discrete state change is needed? | Move tray 17 into bay 21 | `ScheduleEvent` subclasses, `ctx->events` |
| Motion | How does an AGV get there over time? | Timed pose changes along graph edges | `ContinuousState` from CHUGG |
| Action | What command is sent to which machine? | `TYPE_AGV_COMMAND` from node 13 to node 15 | `ActionNode.msg` inside `Schedule.msg` |

![Planning stages](figures/01_pipeline.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#01_pipeline) · [standalone SVG](figures/01_pipeline.svg)</sub>

*Figure 1 — The four principal stages of `Scheduler::Plan`, from `PlanRequest` to `PlanResponse`. The strip underneath shows the same `ctx->events` DAG being enriched: incomplete tray moves get IDs and destinations, blocker moves and AGV events are added, and finally the reduced DAG becomes `ActionNode[]` with parent indices. This is not a ROS thread or executor schedule.*

## 2. Where the scheduler runs: the node and its interfaces

The package builds one shared library (`libscheduler`: `scheduler.cpp`, `utils.cpp`) and one ROS 2 component (`scheduler_component.cpp`, `scheduler_ros.cpp`) that is also installed as the executable `scheduler_node`. Three layers wrap each other:

1. **`SchedulerComponent`** reads ROS parameters (`layout`, `scheduler.cost_audit`, `scheduler.bay_readiness_ratio`, and the AGV / VRC / bay / VECS performance limits in `ReadParams`), finds the layout file with `GetLayoutPathByName`, and builds a `SchedulerRos`. Missing parameters exit the process.
2. **`SchedulerRos`** owns every ROS object: the `plan` service, the `set_bay_readiness_ratio` service, the `debug/printdags` toggle, two 5 s publishers, and four clients into `/central`. It owns the `Scheduler` through a `shared_ptr`.
3. **`Scheduler`** is the planning core. Apart from a logger and `rclcpp::Time`, it knows nothing about ROS transport, which is why tests can construct it directly.

![Scheduler node context](figures/20_system_context.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#20_system_context) · [standalone SVG](figures/20_system_context.svg)</sub>

*Figure 2 — The scheduler node and its ROS interfaces. Dispatch (in the central node) calls `plan` and executes the schedule it gets back. The scheduler calls back into `/central` to ask for follow-up jobs; it does this through three `std::function` members that `SchedulerRos` fills in, so `Scheduler` itself never holds a ROS client. Timers run in their own callback group so a long `Plan()` cannot starve them. The caller's identity (Dispatch) is inferred from comments and client topic names.*

The whole service handler is a few lines. This is the only place where ROS hands a request to the planner:

```cpp
// Where: SchedulerRos::SchedulerRos(...) in src/scheduler_ros.cpp, the "plan" service callback.
//   this        -> SchedulerRos (the ROS adapter, not the planner)
//   scheduler_  -> std::shared_ptr<volley::Scheduler>, created in this constructor
//   request     -> PlanSrv::Request::SharedPtr; request->request_data is a PlanRequestMsg
plan_srv_ = rclcppx::CreateService<PlanSrv>(node_, "plan",
    [this](PlanSrv::Request::SharedPtr request, PlanSrv::Response::SharedPtr response) {
      PlanResponseMsg response_msg = scheduler_->Plan(request->request_data, node_->now());
      rclcpp::Time now = node_->now();
      for(auto& job_data : response_msg.scheduled_jobs) {
        job_data.job.time_planned = now;          // stamp every job, failed or not
      }
      response->response_data = std::move(response_msg);
      return response;
    }, 1u);
```

Two side channels matter when you debug: `set_bay_readiness_ratio` stores a new ratio in the `std::atomic<float> bay_readiness_ratio_` and, if it changed, asks `/central/rebalance_garage` for a `REBALANCE_GARAGE` job; and a failed `INSERT` job triggers `/central/clean_garage` from inside `Plan()`.

## 3. The physical garage and its coordinate system

The supplied **Pecos** layout has **28 nodes and 37 undirected edges** in two YAML sections (`sandbox_eng` and `sandbox_qa`). It defines **two bays** (`B7`, `B21`), **three AGV charging nodes** (`C10`, `C14`, `C16`), plus parking and waypoint nodes. It does not define a VRC. Node positions come from the YAML; connectivity comes from the `edges` list, not from visual distance.

![Pecos facility graph](figures/15_facility_topology.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#15_facility_topology) · [standalone SVG](figures/15_facility_topology.svg)</sub>

*Figure 3 — Pecos facility graph drawn from the YAML coordinates in metres. Blue rectangles are **parking nodes**, drawn with the layout's XL parking window (5.79 m along x by 2.21 m along y) centred on the node; teal rectangles are **bays** with the customer door on the garage side; violet circles are **AGV chargers**; grey dots are **waypoints**; thin lines are **garage-graph edges**; shaded bands mark waypoint corridors; dashed outlines are the two YAML sections. No AGVs or trays are drawn: the YAML contains no occupancy.*

Notice how dense the parking block is: stalls touch along x, so a tray at `P17` can only leave through `P15` or `P20`. That is why **blocking trays** (section 13) are a core problem rather than an edge case.

### Geometric versus logical position

The continuous position vector **$\mathbf p=[x,y]^\mathsf T\in\mathbb R^2$** holds the horizontal coordinate **$x$** and vertical coordinate **$y$**, both in metres. A planar configuration **$\mathbf q=[x,y,\theta]^\mathsf T\in\mathbb R^3$** adds the heading **$\theta$**. In `GeometricPose.msg` the yaw **$\theta$** is in radians. `GaragePose.msg` is different: it holds a node identifier **$i\in\mathbb N$** and an integer heading **$h\in\mathbb Z$** in degrees. The planner works almost entirely in `GaragePose`.

```text
# msg/GeometricPose.msg          # msg/GaragePose.msg
float32 x       # metres        uint32 node_id
float32 y       # metres        int16 heading   # degrees, +CCW from local north; 90 = west
float32 yaw     # radians
```

A pose is a vertex of `gg_` only if the node allows that heading. `gg_.GetVertexFromPose(pose)` returns `std::optional<Vertex>`; an empty optional means “this node cannot hold this heading”, a common cause of “does not exist in garage graph” errors. Several code paths try the **reciprocal** heading (±180°) before giving up, because a tray facing the opposite way occupies the same footprint.

## 4. Vocabulary

| Term | Meaning | Important distinction |
|---|---|---|
| `SchedulerJob` | A requested outcome, such as `TYPE_RETRIEVE` | Arrives in `PlanRequest.pending_jobs` |
| `DiscreteGarageState` (DGS) | Where every AGV, tray, payload, bay, VECS and VRC is, and its state | A snapshot, not a trajectory |
| `ScheduleEvent` | One discrete state change, e.g. a `TrayMove` | Abstract C++ base class in `planner_core`, not a ROS message |
| `TrayMove` | Move one tray to one pose | May start with no tray id, no destination, and no AGV |
| `AgvMove` | One AGV pose change **or** one lift change | Holds `std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg>` |
| `BayTransition`, `VecsTransition` | Commands for bays and EV chargers | Created by job expansion |
| `ScheduleEventDag` | DAG of events; edge u → v means u must finish first | Lives in `ctx->events` |
| `ScheduleContext` | All mutable data for one plan call | Created in `Plan()`, dies when `Plan()` returns |
| working state | `ctx->initial_state` plus a replay of events | Recomputed many times, never stored |
| critical path | The graph path a tray takes to its destination | Trays on it are **blocking trays** |
| `freeing_moves` | A `GarageOccupancyChecker` mapping poses to the events that used them | How “shared space” becomes DAG edges |
| AMIGA | “Arguably More Intelligent aGv Assignment”: the cost functions in `DoAgvAssignments` | Bottleneck matching of AGVs to tray moves |
| CHUGG | The motion planner in `motion_planner/chugg.hpp` | Turns the event DAG into timed trajectories |
| `ActionNode` | One executable command with parent indices | The only thing Dispatch executes |

### A request is not a plan

```text
PlanRequest                                   PlanResponse
  ├── id: Guid                                  ├── success: bool, message: string, id: Guid
  ├── base_state: DiscreteGarageState           ├── schedule: Schedule -> ActionNode[]
  ├── base_schedule: Schedule (already running) └── scheduled_jobs: ScheduledJobData[]
  └── planned_jobs / active_jobs / pending_jobs: SchedulerJob[]
```

Only `pending_jobs` are planned. `base_schedule` is the immutable part of a schedule that is already executing: `Plan()` marks every AGV, node, bay and VECS used by it as **disabled** in the initial state, so the new plan cannot reuse them.

## 5. `DiscreteGarageState`: the bridge between the garage and the planner

`DiscreteGarageState` is the most important type in the system. The Scheduler never plans over geometry directly; it plans over this structured snapshot of arrays (AGVs, trays, bays, payloads, VECS, VRCs and disabled nodes). Every physical fact the planner cares about must be expressible in it.

![DiscreteGarageState bridge](figures/16_discrete_garage_state_bridge.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#16_discrete_garage_state_bridge) · [standalone SVG](figures/16_discrete_garage_state_bridge.svg)</sub>

*Figure 4 — `DiscreteGarageState` ties the floor layout to the planner's data structures. The left side reuses the Pecos drawing: ① AGV 4 parked at charger `C10`, ② tray 15 at parking node `P3`, ③ the payload riding on tray 15, and ④ bay 7 in `READY_TO_RETRIEVE`. Each number points to the matching record on the right; the filled diamond marks containment inside the single snapshot. Values are illustrative.*

How it is used in the scheduler:

- **Built once per call** by `ValidateBaseState(request_data.base_state, *layout_)` in `utils.cpp`. It rejects duplicate entities, payloads that fit no resource window, and AGVs or trays on poses that do not exist in the layout. It does **not** check that entities overlap.
- **Copied freely.** It is a value type. `working_state = ctx->initial_state` makes an independent copy that a function can mutate without affecting anyone else.
- **Advanced by events.** `event->Apply(working_state)` returns a `BoolStringPair` and moves entities discretely (a tray simply appears at its destination).
- **Queried constantly** with `GetAgv(id)`, `GetTray(id)`, `GetTrayOnNode(node)`, `GetPayload(guid)`, `GetBay(id)`, `GetVecs(node)`, each returning `std::optional`.

## 6. ROS messages and services

The `interfaces` package defines the wire contracts under `msg/` and `srv/`. `rosidl_generate_interfaces` turns them into C++ structs. `scheduler_msgs.hpp` gives every one of them a short alias ending in `Msg` (`PlanRequestMsg = interfaces::msg::PlanRequest`, `GaragePoseMsg = interfaces::msg::GaragePose`, …), so when you see `...Msg` in the scheduler you are looking at a generated ROS struct. When one message appears inside another, the relationship is **composition**, not inheritance.

Read the interfaces from the outside in: `srv/Plan.srv`, then `PlanRequest` and `PlanResponse`, then `DiscreteGarageState`, `Schedule`, `ActionNode` and `SchedulerJob`, and only then the utility types.

| Interface | What it contains | Why it matters |
|---|---|---|
| `srv/Plan.srv` | One `PlanRequest` and one `PlanResponse` (`request_data` / `response_data`) | The service boundary `SchedulerRos` exposes |
| `msg/PlanRequest.msg` | Request id, current `DiscreteGarageState`, immutable `base_schedule`, three job arrays | What the world looks like now, and what to plan |
| `msg/PlanResponse.msg` | Success flag, message, id, output `Schedule`, `ScheduledJobData[]` | The schedule plus per-job bookkeeping |
| `msg/SchedulerJob.msg` | Type, state, ids for AGV / bay / tray / payload, optional destination | User or dispatcher intent |
| `msg/DiscreteGarageState.msg` | Arrays of AGVs, bays, VECS (`vexen`), trays, payloads, VRCs, disabled nodes, hash | The snapshot at the start of the call |
| `msg/GaragePose.msg` | Node id and discrete heading | The pose type used almost everywhere |
| `msg/Schedule.msg` | A topologically ordered array of `ActionNode`s | What Dispatch executes |
| `msg/ActionNode.msg` | Type, parent indices, duration, status, one command payload per machine type | The final executable unit |

![ROS message relationships](figures/13_uml_ros_messages.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#13_uml_ros_messages) · [standalone SVG](figures/13_uml_ros_messages.svg)</sub>

*Figure 5 — As-built ROS service and message composition. A **filled diamond** means “contains as a field or array element”; each connector leaves the owning message at the field that holds the value. Blue boxes are the **request / intent** side, violet the **garage-state snapshot**, green the **response / schedule** side, amber the **command payloads**, and teal the **`GaragePose` utility type** (teal type names show where else it is used).*

Reading notes:

- `ActionNode.parents` are **integer indices** into `Schedule.nodes`, not pointers. The conversion from event objects to indices happens at the very end of `Plan()` (section 17).
- `ActionNode` is wide: it has a command field for every machine type, but only the one matching `type` is meaningful.
- `ScheduledJobData.node_indices` tells Dispatch which actions belong to which job; for `TYPE_RETRIEVE`, `bay_arrival_node_guid` names the `PROCESS_RETRIEVE` action.

## 7. Package anatomy: files and classes

| File | Lines | What to look for |
|---|---|---|
| `include/scheduler/scheduler.hpp` | ~460 | `SchedulerParams`, `ScheduleContext`, the `Scheduler` class. Read this first: every method has a comment |
| `src/scheduler.cpp` | ~4 200 | Everything in `Scheduler`. Use the function list in section 9 as a map |
| `include/scheduler/utils.hpp`, `src/utils.cpp` | ~600 | `ValidateBaseState`, bay classification and rebalancing, VRC action insertion |
| `include/scheduler/scheduler_msgs.hpp` | ~60 | The `...Msg` / `...Srv` aliases |
| `src/scheduler_ros.cpp`, `include/scheduler/scheduler_ros.hpp` | ~170 | ROS services, publishers, clients |
| `src/scheduler_component.cpp` | ~70 | Parameter reading, component registration |
| `test/*.cpp` | ~6 500 | 72 active GoogleTest cases (one more is commented out); see [03](03-verification-plan.md) for a map |
| `CMakeLists.txt`, `package.xml` | — | Build targets and package dependencies (section 19) |

| Class / type | What it does | Declared in | Key members / methods |
|---|---|---|---|
| `Scheduler` | The planner. Validates requests, expands jobs into events, assigns trays and AGVs, checks the result, runs motion planning, builds the response | `scheduler.hpp` | `Plan`, `Plan*Job`, `DoTrayAssignments`, `DoAgvAssignments`, `SanityCheckEvents`, `PlanMotions`, `ResponseFromTrajectories` |
| `SchedulerParams` | Constructor-time settings | `scheduler.hpp` | `bay_readiness_ratio`, `cost_audit`, `motion_cost` |
| `ScheduleContext` | Mutable working set for one plan call | `scheduler.hpp` | `initial_state`, `events`, `scheduled_jobs`, `last_entity_event`, `first_tray_event`, `disabledness_filters`, `UpdateLastEntityEvent`, `UpdateLeafDependencies` |
| `ScheduleEvent` and subclasses | Discrete state changes that can be replayed against a DGS | `planner_core/schedule_events.hpp` (not in snapshot) | `Apply`, `GetGarageEntityId`, `GetJobIndex`, `GetType` |
| `DagBase<T>`, `ScheduleEventDag` | Boost-graph DAG of `shared_ptr<T>`, and its event specialisation | `planner_core/event_dag.hpp` (not in snapshot) | `AddEvent`, `AddDependency`, `GetTopologicalOrdering`, `GetRootEvents`, `GetLeafEvents`, `WouldCreateCycle`, `Reduce`, `Remove`, `Apply` |
| `DiscreteGarageState` | Garage snapshot with typed accessors | `common_ros/discrete_garage_state.hpp` (not in snapshot) | `Set`, `GetAgv`, `GetTray`, `GetTrayOnNode`, `GetPayload`, `GetBay`, `GetVecs` |
| `GarageGraph`, `PoseGraph` | Pose graph for searches | `common_ros/garage_graph.hpp` (not in snapshot) | `GetVertexFromPose`, `GetPoseFromVertex`, `SetRetrievalHeading` |
| `CollisionTable` | Pairwise footprint conflicts between entity types at poses | `common_ros` (not in snapshot) | `Query(id_a, id_b, pose_a, pose_b)` |
| `GarageOccupancyChecker<T>` | Remembers which T occupied which pose | `common_ros/garage_occupancy_checker.hpp` (not in snapshot) | `AddOccupant`, `GetBlockers` |
| `MotionCostModel` | Durations from speeds, accelerations and event times | `cost_functions/motion_cost_model.hpp` (not in snapshot) | `Params()`, `Duration(transition)` |
| `SchedulerRos`, `SchedulerComponent` | ROS adapter and component wrapper | `scheduler_ros.hpp`, `scheduler_component.cpp` | see section 2 |

![Current class relationships](figures/11_uml_existing_core.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#11_uml_existing_core) · [standalone SVG](figures/11_uml_existing_core.svg)</sub>

*Figure 6 — Existing core-class relationships. `Scheduler` creates one `ScheduleContext` per `Plan()` call; the context owns the `initial_state` and the `events` DAG. `ScheduleEventDag` specialises the Boost-based `DagBase<T>` template and holds its `ScheduleEvent` vertices through `shared_ptr` (shared, not exclusive, ownership). Each event's `Apply()` mutates a `DiscreteGarageState` during replay.*

Shortest possible mental model: **`Scheduler` is the conductor, `ScheduleContext` is the score being annotated, `ScheduleEventDag` is the dependency structure of the work, and `DiscreteGarageState` is the simulated world the work is replayed on.**

## 8. Objects, ownership and lifetimes

![Runtime objects and lifetimes](figures/21_runtime_objects.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#21_runtime_objects) · [standalone SVG](figures/21_runtime_objects.svg)</sub>

*Figure 7 — Two lifetimes. The node keeps one `Scheduler` whose members are built in a fixed order, each from the one before it. Every plan request gets a fresh `ScheduleContext` that holds all mutable planning data and is released when `Plan()` returns.*

### Constructing the Scheduler

```cpp
// Where: Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger,
//                             const SchedulerParams& params) in src/scheduler.cpp.
// Called once, from SchedulerRos's constructor: std::make_shared<Scheduler>(layout_filepath, logger, params).
// C++ initialises members in DECLARATION order (see scheduler.hpp), which here matches this list:
Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger, const SchedulerParams& params) :
    layout_(std::make_shared<Layout>(layout_filepath)),   // LayoutSPtr: parse the layout YAML
    pg_(layout_),                                         // PoseGraph: every allowed (node, heading)
    gg_(pg_),                                             // GarageGraph: search graph built on pg_
    table_(gg_, logger),                                  // CollisionTable: precomputed footprint conflicts
    logger_(logger),
    cost_model_(params.motion_cost),                      // cost::MotionCostModel from ROS parameters
    bay_readiness_ratio_(params.bay_readiness_ratio),     // std::atomic<float>, changed by a service
    costaudit_(params.cost_audit) {
  InitRetrievalHeadings();   // writes a preferred parking heading into gg_ for each parking node
}
```

`InitRetrievalHeadings()` takes the bay at the **back** of `layout_->GetBayPrioritization()` (the bay a retrieve reaches for first), computes the heading a tray must face to drive into it, and caches that heading on every parking node that allows it and can still reach the bay. Later, `UseRetrievalHeading()` parks loaded trays facing that way so retrieves need fewer rotations.

### Creating the per-call context

This is the snippet that confuses most new readers, so here it is with every name explained:

```cpp
// Where: PlanResponseMsg Scheduler::Plan(const PlanRequestMsg& request_data,
//                                        const rclcpp::Time& now) const   (src/scheduler.cpp)
//   this          -> the Scheduler. There is no variable called "scheduler" here: layout_, gg_
//                    and table_ are its members. The method is const, so it cannot change them.
//   request_data  -> the PlanRequest from Dispatch (see section 4)
//   now           -> node time when the service call arrived
PlanResponseMsg result;
result.id = request_data.id;                          // echo the id so Dispatch can match the reply

// ValidateBaseState is a free function in utils.cpp. It returns
// std::pair<std::optional<DiscreteGarageState>, std::string>; the structured binding unpacks it.
auto [initial_state_opt, validate_message] = ValidateBaseState(request_data.base_state, *layout_);
if(!initial_state_opt.has_value()) {
  result.success = false;                             // the ONLY path that returns success == false
  result.message = "Invalid base state in plan request! " + validate_message;
  return result;
}
volley::DiscreteGarageState initial_state = initial_state_opt.value();   // our own copy

for(const ActionNodeMsg& node : request_data.base_schedule.nodes) {      // already-running actions
  if(node.type == ActionNodeMsg::TYPE_AGV_COMMAND) {
    initial_state.SetAgvDisabled(node.agv_id);        // that AGV is busy: do not assign it
    initial_state.SetNodeDisabled(node.agv_command.src.pose.node_id);
    initial_state.SetNodeDisabled(node.agv_command.dst.pose.node_id);
  }
  // ... TYPE_BAY_COMMAND -> SetBayDisabled, TYPE_VECS_COMMAND -> SetVecsDisabled
}

// plan_ctx is a ScheduleContextSPtr == std::shared_ptr<ScheduleContext>. Every later stage
// receives this same pointer and edits the object it points to.
ScheduleContextSPtr plan_ctx =
    std::make_shared<ScheduleContext>(request_data.id, std::move(initial_state), now);

// For each collision-entity type: which graph vertices and edges are unusable because of
// disabled AGVs / nodes / bays. A free function from another package (not in this snapshot).
plan_ctx->disabledness_filters =
    volley::GetDisabledEntitiesFilters(gg_, plan_ctx->initial_state, table_);
```

Why can a `const` method change anything at all? `Plan()` cannot modify `*this`, but `plan_ctx` is a local `shared_ptr` to a **non-const** `ScheduleContext`. The same holds for `DoTrayAssignments(ScheduleContextSPtr ctx) const` and friends: the Scheduler's graphs and tables stay fixed, and all planning state lives in `*ctx`. Do not read `const` as “thread-safe”, though: `costaudit_` and `printdags_` are `mutable`, and `CreateActionGuid()` uses a plain static counter. The `plan` service runs in the node's default callback group, so plan calls are handled one at a time today.

## 9. One `Plan()` call, step by step

![Plan control flow](figures/22_plan_control_flow.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#22_plan_control_flow) · [standalone SVG](figures/22_plan_control_flow.svg)</sub>

*Figure 8 — `Scheduler::Plan()` step by step with every early return. Job expansion fails jobs one at a time. Any failure after expansion fails **every** pending job at once and returns no schedule, but `PlanResponse.success` stays `true`; only an invalid base state returns `false`.*

The job loop is a plain `switch`. Each case calls one `Plan<Type>Job` method with the index the job **will** have if it succeeds:

```cpp
// Where: Scheduler::Plan(...) const, after plan_ctx has been created.
//   job       -> const SchedulerJobMsg&, one element of request_data.pending_jobs
//   job_index -> plan_ctx->scheduled_jobs.size(): the position this job takes if planning succeeds.
//                Every event created for the job stores it (event->GetJobIndex()).
for(const SchedulerJobMsg& job : request_data.pending_jobs) {
  switch(job.type) {
  case SchedulerJobMsg::TYPE_RETRIEVE: {
    // PlanRetrieveJob returns std::tuple<bool, std::string, bool>: success, message, retain_job
    auto [success, message, retain_job] =
        PlanRetrieveJob(plan_ctx, job.payload_id, plan_ctx->scheduled_jobs.size());
    if(!success) {
      result.scheduled_jobs.push_back(FailJob(job, message, retain_job));   // STATE_ERROR, keep going
      break;
    }
    plan_ctx->PushBackScheduledJob(job);      // now job_index really is this job's position
  } break;
  // ... one case per job type, see section 12
  }
}
```

Two consequences are easy to miss:

- **A failed job leaves its partial events behind.** `FailJob` only marks the job; it does not remove events that `Plan<Type>Job` already added to `plan_ctx->events` (a `TODO(Joe)` in `FailJob` says so). Most job methods validate before adding events, so this is rare, but keep it in mind when a later stage fails mysteriously.
- **Reading a response:** check `scheduled_jobs[i].job.state` (`STATE_EXECUTING` or `STATE_ERROR`) and `job.note`, not just `success`.

The methods in `scheduler.cpp`, in file order, form a useful map:

| Group | Methods |
|---|---|
| Response helpers (anonymous namespace) | `ToActionNode`, `CollectAndCollapseTrajectoryMotions`, `BuildActionDagFromMotions`, `TransferEventDagDepsToActionDag`, `BuildScheduledActionsArray` |
| Construction | `InitRetrievalHeadings`, `Scheduler::Scheduler` |
| Entry point | `Plan` |
| Job expansion | `PlanAgvMoveJob`, `PlanRetrieveJob`, `PlanReparkTrayJob`, `PlanOpenBayDoor`, `PlanInsertJob`, `PlanReadyForInsertJob`, `PlanReadyForRetrieveJob`, `PlanCleanGarageJob`, `PlanUnstashWaypointTraysJob`, `PlanRebalanceGarageJob`, `PlanAgvChargeJob`, `PlanBayTransitionJob`, `PlanChargePayloadJob` |
| Heading policy | `UsePreferredHeading`, `UseEvChargeHeading`, `UseRetrievalHeading` |
| Tray assignment | `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution`, `ResolveBlockingTrays`, `ApplyTransitionToFreeingMoves`, `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`, `DoTrayAssignments` |
| AGV assignment | `AppendAgvLiftEvent`, `PropagateEventCostToChildren`, `AddNodeArrivalDeps`, `MoveAgvToTrayPose`, `GetJustMovingCost`, `GetAgvCurrentPoseToTrayMoveCost`, `GetAgvOccupiedDuration`, `GetAgvToTrayAssignmentCost`, `AgvMatchingEventDeps`, `GetEventDag`, `FindAgvDepartureFromNode`, `TryClearBlockedAgvMove`, `RunAgvPathRepairPass`, `EnsureAgvMovePathsClear`, `DoAgvAssignments`, `AddDepsAfterAmiga` |
| Checks, motion, response | `SanityCheckEvents`, `PlanMotions`, `ResponseFromTrajectories`, `IsMovePossible`, `FailJob`, `SetBayReadinessRatioCallback` |

## 10. Event types and polymorphism

A `ScheduleEvent` is an in-memory C++ object for one discrete state change that can be replayed against a `DiscreteGarageState`. The base class is small: a virtual destructor, a pure virtual `Apply(DiscreteGarageState&)`, and queries such as `GetGarageEntityId()`, `GetJobIndex()` and `GetType()`.

The design idea is **runtime polymorphism**. `ctx->events` stores `std::shared_ptr<ScheduleEvent>`, but each pointer actually points to a `TrayMove`, `AgvMove`, `BayTransition`, `VecsTransition` or `VrcTransition`. When the Scheduler replays the DAG, virtual dispatch runs the right `Apply`. When it needs subclass-specific data it checks `event->GetType()` and then downcasts:

```cpp
// Where: the loop at the top of Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const.
//   event_vert -> a vertex id from ctx->events.GetTopologicalOrdering() (a std::vector of vertices)
//   event      -> std::shared_ptr<volley::ScheduleEvent>; GetEventFromVertex returns an optional
auto event = ctx->events.GetEventFromVertex(event_vert).value();
if(event->GetType() != volley::ScheduleEventType::TRAY_MOVE) { /* handle bay/VECS events */ }
auto* move = dynamic_cast<volley::TrayMove*>(event.get());   // non-owning raw pointer; event keeps it alive
if(!move->GetTrayId()) { /* std::optional<uint16_t> is empty: no tray chosen yet */ }
```

![Existing event inheritance](figures/12_uml_event_hierarchy.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#12_uml_event_hierarchy) · [standalone SVG](figures/12_uml_event_hierarchy.svg)</sub>

*Figure 9 — Existing C++ inheritance hierarchy. The single **hollow triangle** under `ScheduleEvent` means public inheritance; every branch reads “`TrayMove` **is a** `ScheduleEvent`”, not “`ScheduleEvent` contains a `TrayMove`”. Blue marks the abstract base type, green the movement / assignment events, violet the other resource-state transitions. Members are abridged from `planner_core/schedule_events.hpp`.*

Two confusions to avoid: inheritance says nothing about execution order, and the subclasses are siblings, not phases. A `TrayMove` never “turns into” an `AgvMove`; AGV assignment adds separate `AgvMove` events around it.

What each event looks like when it is created (constructor arguments as used in `scheduler.cpp`):

| Event | Created with | Filled in later |
|---|---|---|
| `TrayMove` | `std::make_shared<TrayMove>(job_index)`, then `SetTrayId`, `SetDest` as known | tray id / destination by `DoTrayAssignments`, AGV id by `DoAgvAssignments` |
| `AgvMove` | `std::make_shared<AgvMove>(job_index, AgvPoseChangedMsg)` or `(job_index, AgvLiftChangedMsg)` | — |
| `BayTransition` | `std::make_shared<BayTransition>(job_index, DiscreteBayStateMsg, BayCommandMsg)` | — |
| `VecsTransition` | `std::make_shared<VecsTransition>(job_index, VecsStateChangedMsg)` | — |

A `TrayMove` is **not** an AGV command. Before assignment it may mean “bring *some* empty tray to this bay” (no tray id) or “put this tray *somewhere* sensible” (no destination).

## 11. Directed acyclic graphs, then `ScheduleEventDag`

**Graph theory first.** A directed graph **$\mathcal G=(\mathcal V,\mathcal E)$** has vertices **$\mathcal V$** and directed edges **$\mathcal E\subseteq\mathcal V\times\mathcal V$**. Here an edge **$(u,v)\in\mathcal E$** means event **$u$** must finish before event **$v$** may start. A DAG has no directed cycle; otherwise some event would have to finish before itself.

An ordering function **$\pi:\mathcal V\to\{0,\ldots,n-1\}$** assigns each vertex an index, where **$n=|\mathcal V|$** is the number of events. A topological order satisfies:

$$
(u,v)\in\mathcal E\quad\Longrightarrow\quad\pi(u)<\pi(v).
$$

![Dependencies](figures/04_dependencies.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#04_dependencies) · [standalone SVG](figures/04_dependencies.svg)</sub>

*Figure 10 — Abstract prerequisite ordering. Swimlanes group events by resource; the columns give one valid topological order. The arrows express dependencies, not geometric movement or travel time. The dashed edge is implied by a longer path, which is the kind of redundant edge `Reduce()` removes.*

**Now the implementation.** `DagBase<T>` wraps a Boost `adjacency_list` whose vertices hold `std::shared_ptr<T>`; `ScheduleEventDag` is `DagBase<ScheduleEvent>` plus event helpers. The operations the scheduler uses, all seen at call sites:

| Call | Returns | Used for |
|---|---|---|
| `events.AddEvent(ev)` | — | add a vertex |
| `events.AddDependency(a, b)` | `bool` (false if it already existed) | edge a → b; does **not** check for cycles |
| `events.WouldCreateCycle(a, b)` | `bool` | ask before adding a risky edge |
| `events.GetTopologicalOrdering()` | `std::optional<VertexVec>` | empty optional means there is a cycle |
| `events.GetRootEvents()`, `GetLeafEvents()` | `std::vector<ScheduleEventSPtr>` | no in-edges / no out-edges |
| `events.Apply(state)` | `BoolStringPair` | replay every event in topological order |
| `events.Reduce()` | — | transitive reduction: drop edges implied by longer paths |
| `events.Remove(ev)` | — | used on the copy `event_dag_copy` in `DoAgvAssignments` |

The custom topological ordering favours lower job indices among events that are ready at the same time, so job order still influences replay order. Because vertices hold `shared_ptr`s, **copying a DAG does not copy the events**: `auto event_dag_copy(ctx->events);` in `DoAgvAssignments` shares every event object with `ctx->events`, which is exactly what that loop relies on when it calls `tray_move->SetAgvId(...)`.

## 12. Job expansion: from jobs to events

Job expansion is the loop in `Plan()` that calls one `Plan<Type>Job` per pending job. Each method checks preconditions against the garage **as earlier jobs will leave it**, appends events to `ctx->events`, and wires a few dependency edges. Nothing is routed and no AGV is chosen yet.

![Job recipes](figures/24_job_recipes.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#24_job_recipes) · [standalone SVG](figures/24_job_recipes.svg)</sub>

*Figure 11 — What each job type adds to the event DAG, read directly from the `Plan<Type>Job` methods. Dashed events are conditional. A “?” means the tray or destination is left empty for `DoTrayAssignments()`. “+ recipe” means the method calls another job method (for example `PlanReadyForInsertJob` calls `PlanChargePayloadJob` when the payload in the bay asked for EV charging).*

### Every job sees the garage through `working_state`

![Working state replay](figures/23_working_state_replay.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#23_working_state_replay) · [standalone SVG](figures/23_working_state_replay.svg)</sub>

*Figure 12 — Every `Plan<Type>Job` copies `ctx->initial_state` and replays the whole event DAG built so far. Job 1 (a retrieve) therefore sees tray T15 at P23, where job 0 will have put it, not at P15 as in the request.*

This copy-and-replay pattern appears at the top of every job method and again inside the later stages. It is simple and always correct, at the cost of replaying the DAG many times per plan call.

### Where the edges come from

![Edge rules during job expansion](figures/25_dependency_rules.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#25_dependency_rules) · [standalone SVG](figures/25_dependency_rules.svg)</sub>

*Figure 13 — The three edge rules used during job expansion. Rule A (`UpdateLastEntityEvent`) chains events that touch the same AGV, tray, bay or VECS, even across jobs. Rule B (`UpdateLeafDependencies`) makes a new event wait for the current leaf events of the **same** job. Rule C (in `PlanReparkTrayJob`) makes a tray move into a bay or VECS wait for that resource's last event.*

### A job method, annotated

`PlanRetrieveJob` is the richest job method and a good one to read first:

```cpp
// Where: std::tuple<bool, std::string, bool>
//        Scheduler::PlanRetrieveJob(ScheduleContextSPtr ctx, const GuidMsg& payload_id, size_t job_index) const
//   returns (success, message, retain_job). retain_job = true asks Dispatch to keep the job and retry later,
//   e.g. when no bay is free; it ends up in ScheduledJobData.job.retain_job via FailJob().
volley::DiscreteGarageState working_state = ctx->initial_state;          // copy ...
auto [success, message] = ctx->events.Apply(working_state);              // ... and replay earlier jobs

std::optional<DiscretePayloadStateMsg> payload_opt = working_state.GetPayload(payload_id);
DiscreteTrayStateMsg tray = working_state.GetTray(payload_opt->tray_id).value();

// 1. If the payload sits on a VECS that is CHARGING, add VecsTransition CHARGING -> READY_TO_CHARGE.
// 2. Pick a bay: walk layout_->GetBayPrioritization() from the BACK, skip disabled bays and bays whose
//    resource window is too small; prefer READY_TO_RETRIEVE, else READY_TO_INSERT / VEHICLE_INSERTED.
// 3. If that bay is not READY_TO_RETRIEVE, add BayTransition TRANSITION_TO_RETRIEVE.
// 4. If a tray already sits in the bay, PlanReparkTrayJob(ctx, that_tray_id, job_index, true)   // dest = ?
// 5. Move the payload's tray into the bay, facing so the car drives out forwards:
GaragePoseMsg bay_pose;                                   // node id = bay id, heading = bay inbound heading
bay_pose.node_id = bay_opt->id;
bay_pose.heading = static_cast<int16_t>(layout_->GetBayInboundHeading(bay_opt->id).value());
GaragePoseMsg dest_pose = payload_opt->reciprocal_to_tray ? bay_pose : volley::ReciprocalGaragePose(bay_pose);
std::tie(success, message) = PlanReparkTrayJob(ctx, payload_opt->tray_id, job_index, false, dest_pose);
// 6. Finally the BayTransition PROCESS_RETRIEVE, ordered after the job's other events (rule B):
auto bay_transition = std::make_shared<BayTransition>(job_index, *bay_opt, cmd);   // cmd = PROCESS_RETRIEVE
ctx->events.AddEvent(bay_transition);
ctx->UpdateLastEntityEvent(bay_transition->GetGarageEntityId().value(), bay_transition);   // rule A
ctx->UpdateLeafDependencies(bay_transition, job_index);                                    // rule B
```

Things worth knowing about specific job types:

- **`PlanReparkTrayJob` is the workhorse.** Retrieve, insert, ready-for-insert/retrieve, unstash and charge-payload all call it. With a destination it applies the heading policy (`UsePreferredHeading`: the EV-charging special case first, then the cached retrieval heading for loaded trays); without one it leaves `dest` empty.
- **`PlanInsertJob` never puts the bay back into insert mode itself.** It calls `reset_bay_state_request_fn_(bay_id, STATE_READY_TO_INSERT)`, which asks Dispatch for a separate job, so a missing empty tray cannot make the insert fail.
- **`PlanCleanGarageJob` hides AGVs only when it is job index 0** (`volley::HideAgvs` assigns each AGV a hiding pose, usually under a tray), then reparks trays left on waypoints by an earlier tier-2 stash.
- **`PlanRebalanceGarageJob` never fails.** It plans `READY_FOR_INSERT` / `READY_FOR_RETRIEVE` recipes for the bays chosen in section 18 and only logs per-bay failures.
- **`PlanAgvChargeJob`** picks the free charger with the lowest `GetJustMovingCost`, freeing the AGV from a `READY_TO_INSERT` bay first if needed. Note the code comment: “empty” only means no AGV is on the node.
- **`UseEvChargeHeading`** contains a site-specific rule for the `576_eccles` layout (nodes 46 and 47 park at heading 0).

## 13. The whole journey of one job

Before the details of each stage, here is one retrieve followed through all three passes over the event DAG.

![Retrieve walkthrough](figures/26_retrieve_walkthrough.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#26_retrieve_walkthrough) · [standalone SVG](figures/26_retrieve_walkthrough.svg)</sub>

*Figure 14 — One `TYPE_RETRIEVE` job on Pecos, stage by stage. Map numbers match event ids. Band 1: job expansion creates intent, including a move of the empty tray T21 out of the bay with no destination. Band 2: tray assignment gives T21 a destination and inserts a move for blocker T15, which sits on T17's critical path. Band 3: AGV assignment wraps every `TrayMove` in move → lift → carry → lower, and `AddDepsAfterAmiga` ties the bay transitions to the right lift and lower. Destinations and AGV order are illustrative.*

## 14. Tray assignment: `DoTrayAssignments`

After expansion, some `TrayMove`s lack a tray id or a destination, and many destinations are not reachable because other trays are in the way. `DoTrayAssignments(ctx)` fixes both in one pass over the DAG in topological order. When it returns, **every `TrayMove` has a tray id and a destination**, and every blocking tray has its own `TrayMove`.

![Scene used in the following figures](figures/15_facility_scenario.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#15_facility_scenario) · [standalone SVG](figures/15_facility_scenario.svg)</sub>

*Figure 15 — The hypothetical scene reused by the next figures. Bays `B7` and `B21` sit on the customer side; AGV A at `C10`, tray T15 with a payload at `P3`, blocker K at `P15`, root tray R at `P17` and tray T20 at `P20` are explanatory stand-ins, not YAML occupancy.*

![DoTrayAssignments flow](figures/27_tray_assignment_flow.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#27_tray_assignment_flow) · [standalone SVG](figures/27_tray_assignment_flow.svg)</sub>

*Figure 16 — Inside `DoTrayAssignments()`. Non-tray events register their pose with `freeing_moves` and are applied. Missing tray ids come from an empty-tray search; missing destinations from `ResolveBlockingTrays`. Moves with both go through the blocking-tray loop with two fallbacks.*

The three searches all come from `motion_planner` and run through `volley::SingleSourceSearch(source, Interval::Duration(0), environment)`; the environment object decides what counts as a goal:

| Environment | Used by | Finds |
|---|---|---|
| `EmptyTraySearchEnvironment` | `AssignTrayIdForEmptyMove` | the nearest tray without a payload, searching outward from the destination |
| `OpenSpaceSearchEnvironment` | `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution` | a free parking spot (tier 1) or, if `allow_waypoint_stash`, a waypoint (tier 2), plus the trays blocking the way |
| `BlockingTraySearchEnvironment` | the main loop | the critical path from the tray to its destination and the trays on it |

### The blocking-tray loop

![Blocking tray example](figures/15_blocking_tray_move.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#15_blocking_tray_move) · [standalone SVG](figures/15_blocking_tray_move.svg)</sub>

*Figure 17 — Why blocking trays matter. Root tray R at `P17` must reach bay `B21`. In the Pecos graph `P17` connects only to `P15`, `P20` and charger `C16`; with K at `P15` and T20 at `P20`, every exit is occupied. AGV A therefore ① drives under K and lifts it, ② reparks K at the free stall `P19`, ③ returns unloaded to lift R, and ④ carries R out. It does **not** claim the current solver would pick this relocation target or route.*

```cpp
// Where: Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const, inside the per-event loop,
// once `move` (volley::TrayMove*) has both a tray id and a destination.
//   tray_opt              -> std::optional<DiscreteTrayStateMsg>, the tray in working_state
//   root_collision_entity -> CollisionEntityId_t for this tray's footprint (depends on its payload)
//   filters               -> GetStaticFilter(...) ignoring every tray and AGV (they can be moved)
volley::BlockingTraySearchEnvironment blocking_search_env(move->GetTrayId().value(), root_collision_entity,
    gg_, table_, working_state, cost_model_, gg_.GetVertexFromPose(move->GetDest().value()).value(), filters);
auto blocking_solution = volley::SingleSourceSearch(source, volley::Interval::Duration(0), blocking_search_env);
auto path = blocking_solution.GetPath(blocking_solution.GetTarget().value()).value();   // the critical path

while(!blocking_trays.empty()) {
  uint16_t blocking_tray_id = blocking_trays.front();
  // Find a new home for the blocker. The root tray may not move (immobile set) and the blocker may not
  // park on the critical path or on a spot it already used during this pass (WithPriorDests).
  auto [dest, required_moves] = ResolveBlockingTrays(blocking_tray_id, move->GetJobIndex(), working_state,
      std::set<uint16_t>{move->GetTrayId().value()}, WithPriorDests(blocking_tray_id, critical_path));
  // fallback 1: advance the root tray one step along its path, then try again
  // fallback 2: allow parking on the critical path; if that fails too -> return {false, "..."}
  // emit required_moves + the blocker's own move as events, chained, each before `event` (the root move)
  // recompute blocking_trays for the rest of the path
}
```

`ResolveBlockingTrays(tray_id, job_index, base_state, immobile_trays, illegal_poses, enforce_retrieval_heading, allow_waypoint_stash)` returns `std::pair<std::optional<GaragePoseMsg>, std::vector<std::pair<std::shared_ptr<TrayMove>, std::vector<GaragePoseMsg>>>>`: an optional destination for the tray, and the ordered list of extra tray moves (each with its path) needed to get there. It **recurses** when a blocker is itself blocked, marking the parent tray immobile to avoid cycles; the test `ResolveBlockingTraysRecursivelyUnblocksChain` exercises a chain of three. Two tiers apply: first parking nodes only, then (tier 2) a waypoint “stash” that a later `CLEAN_GARAGE` job undoes through `PlanUnstashWaypointTraysJob`.

### Occupancy becomes dependencies: `freeing_moves`

![freeing_moves](figures/28_freeing_moves.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#28_freeing_moves) · [standalone SVG](figures/28_freeing_moves.svg)</sub>

*Figure 18 — `freeing_moves` is a `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>`. Every event that used a pose (a source pose, every pose on a path, a bay pose touched by a transition) is recorded. A later move through a colliding pose gets an edge from each recorded event. The checker uses `table_`, so “colliding” means overlapping footprints, not just equal node ids.*

Two pieces of bookkeeping leave this stage:

- `last_tray_event` (a local map) chains successive moves of the same tray.
- `ctx->first_tray_event[tray_id]` remembers the **first** move that takes each tray off its initial node. `DoAgvAssignments` uses it so an AGV that must drive through that node waits for the tray to leave. Using the *last* move instead would create a cycle when one AGV moves the same tray twice (see the comment in `scheduler.hpp`).

`DoTrayAssignments` deliberately does **not** call `Reduce()` at the end; a source comment says doing so breaks the following AGV assignment.

## 15. AGV assignment: `DoAgvAssignments`

Now every `TrayMove` knows *what* moves where. `DoAgvAssignments(ctx)` decides *which AGV* does each one and adds the AGV's own events. It works on `event_dag_copy`, a copy of `ctx->events` that it consumes from the roots down:

1. **Drain non-tray roots.** Apply every root that is not a `TrayMove` (bay and VECS transitions, pre-existing `AgvMove`s) to `working_state`, chain AGV moves per AGV, add node-arrival dependencies, and remove them from the copy. Repeat until only `TrayMove` roots remain, so the matcher sees every eligible move at once (the SW2-377 comment explains why).
2. **Cost every (AGV, root move) pair** with `GetAgvToTrayAssignmentCost`. Pairs are infeasible when the AGV carries a different tray, has no path, or is trapped in a bay that is not `READY_TO_RETRIEVE`.
3. **Match** with `volley::BottleneckAssignment` and order matched AGVs that would collide with `GetEventDag`.
4. **Expand** each match into events and remove the matched `TrayMove` from the copy.
5. Repeat until the copy is empty, then run `EnsureAgvMovePathsClear`, `Reduce()`, and `AddDepsAfterAmiga` for bay and VECS transitions.

![AGV matching](figures/29_agv_matching.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#29_agv_matching) · [standalone SVG](figures/29_agv_matching.svg)</sub>

*Figure 19 — Matching AGVs to root tray moves. Each edge is one feasible pair with its estimated cost; AGV C carries another tray, so it has no edges. Bottleneck matching minimises the **worst** single cost, so it can prefer a pairing with a higher total. Costs are illustrative.*

The cost of assigning AGV **$i$** to tray move **$j$** is

$$
c_{ij}=\max\!\left(t_i^{\mathrm{occupied}}-t_j^{\mathrm{ready}},\,0\right)+t_{ij}^{\mathrm{approach}}+t_{ij}^{\mathrm{lift}},
$$

where cost **$c_{ij}$** [s] is the estimated time until the tray is lifted, **$t_i^{\mathrm{occupied}}$** [s] is how long AGV **$i$** is already busy (`agv_occupied_durations`), **$t_j^{\mathrm{ready}}$** [s] is the earliest time move **$j$** can start given its parents (`event_occupied_durations`, filled by `PropagateEventCostToChildren`), **$t_{ij}^{\mathrm{approach}}$** [s] is `GetJustMovingCost` from the AGV's pose to the tray's pose, and **$t_{ij}^{\mathrm{lift}}$** [s] is the lift-up time when the AGV is not already holding the tray. **Caveat:** `GetAgvOccupiedDuration()` returns zero (a `TODO(isabel)`), so the occupied term only reflects work assigned earlier in the same call.

![AGV approach](figures/15_agv_approach_and_pickup.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#15_agv_approach_and_pickup) · [standalone SVG](figures/15_agv_approach_and_pickup.svg)</sub>

*Figure 20 — Unloaded approach example. A hypothetical AGV at charger `C10` approaches tray T15 at `P3` via `10 → 9 → 11 → 6 → 3`, driving under the empty stall `P6`. The strip restates the intent as simplified events. The route is a graph walk, not a recorded run.*

![AGV event expansion](figures/30_agv_event_expansion.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#30_agv_event_expansion) · [standalone SVG](figures/30_agv_event_expansion.svg)</sub>

*Figure 21 — What one assignment adds: `MoveAgvToTrayPose` (skipped if the AGV is already there), a lift, `SetAgvId` on the `TrayMove`, and a lower. The first event gets edges from four sources: the AGV's previous event, the first move of any tray parked on its navigation path, the previous occupant of the destination node, and matched AGVs it must follow.*

```cpp
// Where: Scheduler::DoAgvAssignments(ScheduleContextSPtr ctx) const, after BottleneckAssignment.
//   ordered_matching -> std::vector<std::pair<uint16_t, std::optional<ScheduleEventSPtr>>>: (agv id, root event)
//   working_state    -> local DiscreteGarageState advanced as events are created
for(const auto& [agv_id, root_event_opt] : ordered_matching) {
  if(!root_event_opt.has_value()) continue;                       // this AGV got nothing this round
  auto root_event = root_event_opt.value();                       // std::shared_ptr<ScheduleEvent>
  auto* tray_move = dynamic_cast<volley::TrayMove*>(root_event.get());
  const DiscreteTrayStateMsg tray = working_state.GetTray(tray_move->GetTrayId().value()).value();
  const DiscreteAgvStateMsg agv = working_state.GetAgv(agv_id).value();
  if(agv.tray_id != tray.id) {
    MoveAgvToTrayPose(agv_id, agv, tray, root_event, ...);        // AgvMove (pose) + its dependencies
    AppendAgvLiftEvent(agv_id, /*raised=*/true, ...);             // AgvMove (lift)
  }
  tray_move->SetAgvId(agv.id);                                     // edits the shared event object
  ctx->events.AddDependency(last_agv_event[agv_id], root_event);
  AddNodeArrivalDeps(tray_move->GetDest()->node_id, agv_id, root_event, ...);
  root_event->Apply(working_state);
  event_dag_copy.Remove(root_event);
  AppendAgvLiftEvent(agv_id, /*raised=*/false, ...);              // AgvMove (lower)
  PropagateEventCostToChildren(root_event, event_cost, ctx, event_occupied_durations);
  agv_occupied_durations[agv_id] += event_cost;
}
```

### Repairing paths after assignment

![AGV path repair](figures/31_agv_path_repair.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#31_agv_path_repair) · [standalone SVG](figures/31_agv_path_repair.svg)</sub>

*Figure 22 — `EnsureAgvMovePathsClear` replays the final topological order. When an AGV reposition has no collision-free path only because another AGV's body is in the way, it adds one edge from that AGV's next departure to the blocked move (unless that would form a cycle) and starts over, at most 256 times. Tray and disabled-node obstructions are left for `SanityCheckEvents` to report.*

This pass exists because `DoAgvAssignments` builds dependencies in its own serial assignment order, which can differ from the order the DAG is eventually replayed in. The source comments in `MoveAgvToTrayPose` describe an earlier, proactive attempt that both missed real blockers and added spurious edges.

`AddDepsAfterAmiga(ctx, event, node_id)` runs last for every bay and VECS transition. It moves dependencies from tray moves onto the AGV's lift and lower events: a transition that waited for a tray to arrive now waits for the **lower** after it, and a tray move out of the bay waits for the transition before its **lift**.

## 16. `Reduce()` and `SanityCheckEvents`

Back in `Plan()`, `plan_ctx->events.Reduce()` removes redundant edges (a `TODO(any)` notes that planning may fail without it, probably inside CHUGG). Then `SanityCheckEvents(ctx)` replays the DAG in topological order on a fresh copy of `initial_state` and checks each event **before** applying it:

| Event | Check |
|---|---|
| `BayTransition` | the bay's ODP (operator door) area is free (`GetStaticFilter` for `BAY_ODP`) |
| `AgvMove` with a destination | `IsMovePossible`: destination exists, is not disabled, is not occupied, and a path exists, ignoring only this AGV |
| `AgvMove` lift change | only that `Apply` succeeds |
| `TrayMove` | has a destination, and `IsMovePossible` with the carrying AGV and the tray itself ignored |

The comment explains the motivation: “The motion planner doesn't fail in the most graceful ways”, so a cheap discrete replay catches most problems with a readable message first.

## 17. Motion planning and the response

`PlanMotions(ctx)` builds the initial `ContinuousState` (everything stays where it is until `ctx->start_time`), precomputes edge durations and an all-pairs heuristic, and runs **CHUGG** (`volley::Chugg`, “v0.1” in a comment) with `SolveSequential`. With `cost_audit` on, it logs one CSV row per cost segment (`audit_csv,index,seconds,cumulative,description`). A failure returns `std::nullopt` and fails every job with “CHUGG failed to find a solution, event dag may be infeasible”.

`ResponseFromTrajectories(ctx, final_state)` then turns trajectories into the wire format:

![Motions to actions](figures/32_motions_to_actions.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#32_motions_to_actions) · [standalone SVG](figures/32_motions_to_actions.svg)</sub>

*Figure 23 — From timed trajectories to `ActionNode[]`. Every motion with a delta (pose change, lift change, bay / VECS / VRC state change) becomes one `ActionNode`; waits are dropped. Actions are chained per entity, ordered by occupancy, given the event-level dependencies, reduced, extended with VRC commands, and finally written out in topological order with integer parent indices. Times are illustrative; the shape matches the `RetrieveJob` test.*

```cpp
// Where: anonymous-namespace helper ToActionNode(const volley::Motion& motion, GuidMsg job_id,
//        const std::shared_ptr<ScheduleEvent>& event) in src/scheduler.cpp
//   motion.GetDelta() -> optional serialized discrete change; its .type names the ROS message type
if(delta->type == "AgvPoseChanged") {
  result->type = ActionNodeMsg::TYPE_AGV_COMMAND;
  // An AGV motion whose collision id is NOT the bare AGV is carrying a tray, so lift = true on both ends.
  result->agv_command.src.lift = motion.GetCollisionId() != common::EnumInteger(volley::CollisionEntityId::AGV);
}
// "AgvLiftChanged" -> AGV command with src.lift != dst.lift; "BayStateChanged" -> TYPE_BAY_COMMAND using the
// BayTransition's own command; "VecsStateChanged" -> start/stop charging; "VrcStateChanged" -> VRC move.
```

Finally `Plan()` marks every planned job `STATE_EXECUTING`, and for `TYPE_RETRIEVE` jobs records the bay and the `PROCESS_RETRIEVE` action in `bay_id` and `bay_arrival_node_guid`.

## 18. Bays, VECS and VRCs

### Bays and rebalancing

![Bay logic](figures/33_bay_logic.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#33_bay_logic) · [standalone SVG](figures/33_bay_logic.svg)</sub>

*Figure 24 — The three bay commands the scheduler issues, the `ClassifyBay` rules from `utils.cpp`, and a worked example of `ComputeBayRebalancingActions`. Other bay states are reached through bay or customer activity outside this package.*

`bay_readiness_ratio` is the fraction of usable bays that should be ready for insert. `CalculateDesiredBaySplit` rounds up (it biases towards insert because arriving customers cannot be detected), clamps, and never asks for more insert-ready bays than there are empty trays. `ComputeBayRebalancingActions` first counts bays already moving towards a state (`WILL_BE_*`), then keeps bays already in a wanted state, and only then picks bays to change, in `bay_prioritization` order for insert and reverse order for retrieve. Bays left in an invalid state fall back to ready-for-retrieve.

### VECS (EV charging)

A VECS sits under a parking node of type `TYPE_EV_CHARGE`. Moving a tray off a VECS that is `CHARGING` first adds `VecsTransition CHARGING -> READY_TO_CHARGE`; moving onto one is refused unless it is `READY_TO_CHARGE`. `PlanChargePayloadJob` finds a VECS with `ResolveBlockingTrays` (the open-space search knows about VECS nodes) and then adds `READY_TO_CHARGE -> CHARGING`.

### VRCs (lifts between floors)

![VRC conceptual transfer](figures/14_vrc_floors.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#14_vrc_floors) · [standalone SVG](figures/14_vrc_floors.svg)</sub>

*Figure 25 — Conceptual VRC connecting two floors, as a side elevation. The Pecos YAML has no VRC; this shows general code-supported behaviour.*

In this package VRCs are handled at the **action** level, after motion planning: `InsertVrcActionsIntoDag` (in `utils.cpp`) walks AGV actions in topological order, simulates the carriage floor per VRC, and inserts a `TYPE_VRC_COMMAND` *approach* when the carriage is on the wrong floor for the AGV's next action, plus a *move* command that replaces each cross-floor AGV action. Each command's duration is door close + carriage transit + door open. Consecutive cross-floor motions are first collapsed into one motion in `CollectAndCollapseTrajectoryMotions`. `VrcTransition` events and their `Apply` live in `planner_core` and were not in the snapshot.

## 19. Packages, build system and dependencies

| Target | Built from | Notes |
|---|---|---|
| `scheduler` (shared library) | `src/scheduler.cpp`, `src/utils.cpp` | Everything the tests link against |
| `scheduler_component` (+ executable `scheduler_node`) | `src/scheduler_component.cpp`, `src/scheduler_ros.cpp` | Plugin `volley::SchedulerComponent` |
| gtests | `scheduler_tests`, `scheduler_insert_orientation_tests`, `scheduler_jobs_tests` (240 s timeout), `utils_tests` | Link `yaml-cpp` and the library |

`package.xml` lists these dependencies: `common`, `common_ros`, `cost_functions`, `interfaces`, `motion_planner`, `planner_core`, `task_planner`, `vrc_interfaces`, `rclcpp`, `rclcpp_components`, `rclcppx`, `std_srvs`, `stdx`, `backward_ros` and Boost. The build uses ROS 2 `ament_cmake` with the repository's `volley_cmake` macros (`volley_package`, `volley_add_library`, `volley_add_component`, `volley_add_gtest`, `volley_ament_auto_package`). The dependency direction is `scheduler → planner_core, motion_planner, task_planner, cost_functions, common_ros`; nothing in the snapshot depends on `scheduler`.

## 20. Debugging and testing

- **Logs.** `Plan()` logs the initial DGS, each job as it is planned, the topological order after tray and after AGV assignment, and why things fail. Set the logger to DEBUG to also get every planned trajectory.
- **DAG pictures.** Call the `debug/printdags` service (or set the `printdags` parameter) to log the event DAG after each stage and the action DAG after each `Reduce()`; it needs `libgraph-easy-perl`.
- **Cost audit.** `scheduler.cost_audit` (default `true`) prints a CSV breakdown of CHUGG's cost per segment.
- **Tests.** 72 active GoogleTest cases in four files (`DoubleRetrieveDodgeAgv` is commented out). Unit tests build a `DiscreteGarageState` from inline YAML, construct a `Scheduler` with a named test layout (`tiny_lot`, `triple_pick_lot`, `576_eccles_half`, `1355_fulton`), and call one stage directly. Job tests build a full `PlanRequestMsg` and call `Plan()`. [03](03-verification-plan.md) maps every test to the stage it exercises.

```bash
colcon build --packages-up-to scheduler
colcon test --packages-select scheduler --ctest-args -R scheduler_tests
colcon test-result --verbose
```

A good first exercise: run `SchedulerJobs.RetrieveJob` under a debugger, break in `Scheduler::DoTrayAssignments` and `Scheduler::DoAgvAssignments`, and print `ctx->events` at each stop.

## 21. C++ concepts and idioms in context

| Idiom | Meaning | Where you meet it | Pitfall |
|---|---|---|---|
| `std::shared_ptr<T>` | Shared lifetime | DAG vertices, `ScheduleContextSPtr`, `LayoutSPtr` | Copying a DAG aliases the same events |
| `std::optional<T>` | A value that may be missing | `TrayMove::GetDest()`, every `GetTray(id)` | `.value()` throws if empty; many call sites assume it is set |
| Structured bindings | Unpack a pair / tuple | `auto [success, message] = ...` | `success` here is the stage result, not `PlanResponse.success` |
| `std::tie` | Assign into existing variables | `std::tie(success, message) = DoAgvAssignments(plan_ctx);` | Reuses the variables declared earlier |
| `virtual` / `dynamic_cast` | Runtime polymorphism and checked downcast | `ScheduleEvent` and subclasses | Check `GetType()` first, as the code does |
| `std::variant` / `std::visit` / `std::holds_alternative` | One of several alternatives | `AgvMove` holds a lift **or** a pose change | Lift changes have no destination (`GetDest()` empty) |
| `const` member functions | Cannot modify `*this` | Every planning method | Can still modify `*ctx` through a pointer |
| `mutable`, `std::atomic<float>` | Members changeable from const methods / threads | `costaudit_`, `printdags_`, `bay_readiness_ratio_` | `const` does not mean thread-safe here |
| `std::function` members + `friend` | Injected callbacks | `*_request_fn_` set by `SchedulerRos` | Empty in unit tests; the code checks before calling |
| Templates | Generic code | `DagBase<T>`, `GarageOccupancyChecker<T>` | Also used with `T = ActionNodeMsg` and `T = uint16_t` |
| ROS IDL aliases | Generated structs | `PlanRequestMsg`, `GaragePoseMsg` | Field names are a wire contract |

## 22. Known limitations and reading checkpoint

Limits of this guide: `GarageGraph`, `CollisionTable`, `GarageOccupancyChecker`, the search environments, `BottleneckAssignment`, CHUGG, `DiscreteGarageState` and the event classes live in other packages and were not in the snapshot. Dispatch, AGV firmware and the Pecos garage's real occupancy were not supplied. Do not infer those details from a schematic figure.

Limits of the code worth remembering: `GetAgvOccupiedDuration` returns zero; failed jobs can leave events in the DAG; any failure after expansion fails all jobs in the request; `Reduce()` placement is load-bearing; `UseEvChargeHeading` contains a hard-coded site rule.

**Before reading [02](02-issue-and-proposal.md), check you can answer:**

1. What is the difference between a job, an event, a motion and an action?
2. In `Scheduler::Plan`, what is `this`, what is `plan_ctx`, and why can a `const` method still change the plan?
3. Why does every `Plan<Type>Job` start by copying `ctx->initial_state` and calling `ctx->events.Apply`?
4. What makes a `TrayMove` incomplete, and which stage completes each missing part?
5. What does an edge in `ScheduleEventDag` mean, and which three rules add edges during job expansion?
6. Why is `first_tray_event` recorded in tray assignment and read in AGV assignment?
7. What does bottleneck matching optimise, and why might it not pick the lowest total cost?
8. When does `Plan()` return `success == false`, and how do you tell which jobs really failed?
9. How does a bay differ from a VECS and from a VRC in this code?

### Source index

- `include/scheduler/scheduler.hpp`: `SchedulerParams`, `ScheduleContext`, `Scheduler` declarations with comments
- `src/scheduler.cpp`: everything in `Scheduler`, plus the response-building helpers
- `include/scheduler/utils.hpp`, `src/utils.cpp`: base-state validation, bay classification and rebalancing, VRC actions
- `include/scheduler/scheduler_ros.hpp`, `src/scheduler_ros.cpp`, `src/scheduler_component.cpp`: ROS wiring and parameters
- `test/*.cpp`, `test/garage_states/double_retrieve_garage_state.yaml`: 72 active tests and one fixture
- `CMakeLists.txt`, `package.xml`: targets and dependencies
- `sources/repomix-scheduler.xml`: the snapshot all of the above was read from
- `sources/5675_pecos_combined.yaml`: coordinates, node metadata and edges for the Pecos figures
