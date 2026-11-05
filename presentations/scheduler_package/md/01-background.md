# 01 — Background: the scheduler and its data

*A ground-up guide to the `scheduler` ROS 2 package for engineers who are new to the team. This tab gives the picture of the whole system and the data it works on; the Task planning, Motion planning and Action graph tabs (03–05) follow a plan call through its stages.*

> **Scope and evidence.** This guide documents the *existing* implementation, not the proposed solver refactor (that is the [Issue & proposal](#doc-proposal) tab). It was checked against six source snapshots in `sources/`: the `scheduler` package itself (`repomix-scheduler.xml`: headers, sources, tests and their scenario initial states, CMake), `planner_core` (events and the event DAG), `common_ros` (`DiscreteGarageState`, `Layout`, `PoseGraph`, `GarageGraph`, `CollisionTable`, `GarageOccupancyChecker`), `motion_planner` (CHUGG, SIPP, `ContinuousState`, the single-agent searches and filters), `cost_functions` (the timing model and parameter defaults), and every `.msg` and `.srv` of the interface packages. The `scheduler`, `planner_core` and `motion_planner` snapshots are `main` at `a468657f` (2026-11-05), after PR \#1007 (scenario-file tests) and PR \#1018 (renames, the split of `scheduler.cpp` by stage, bug fixes); the others are from 2026-10-13. The other packages' tests were not included. `task_planner` (`BottleneckAssignment`), `common`/`stdx` and Dispatch were **not** available; where this guide describes them, it does so from call sites and says so. The Pecos figures use real node positions and edges from `5675_pecos_combined.yaml`, but **AGV, tray and payload occupancy is hypothetical**. The Pecos YAML has bays and chargers but **no VRC**.
>
> **Also not in the snapshots:** the `common` utilities this code calls (`stdx`, `BoolStringPair` (still returned by `planner_core` and `common_ros`), `common/types.hpp`, `volley::Wrap`, `AreSameDirection`, footprint dimensions; their hover windows show sketches reconstructed from call sites), AGV firmware and the Pecos garage's real occupancy. Do not infer those details from a schematic figure.

> **Viewing the figures.** Click a figure to open it full screen with pan and zoom; "Pan / zoom viewer" under each caption opens the gallery of all figures ([`figures/viewer.html`](figures/viewer.html)). Every figure carries a status badge: **AS-BUILT**, **PROPOSED**, **ILLUSTRATIVE**, **SCHEMATIC**, **CONCEPTUAL**, or **YAML GEOMETRY · HYPOTHETICAL OCCUPANCY**.

## How to use this study pack

The study pack has eight tabs. The first five describe the scheduler as it is: the whole, the site layout it is built from, then the stages in the order a plan call runs; the sixth outlines Dispatch, the scheduler's only client; the last two describe the refactor. Each tab assumes the ones before it.

| Tab                                          | Covers                                                                                                                                                                                    | You will be able to                                                                                                                                  |
|----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| 01 · Background (this tab)                   | The pipeline as a whole, the garage model, the data structures of one plan call, and how to build, test and read the code                                                                 | Name the five stages and the four representations of a plan, the main types and who owns them, and follow one `Plan()` call from request to response |
| 02 · [Layout file](#doc-layout-file)         | The site layout YAML, key by key: what each field means, which code reads it, what the parser checks and accepts silently, VRC support across the pipeline, and improvements              | Read and edit a layout file, predict the poses and edges it creates, and spot the mistakes the parser lets through                                   |
| 03 · [Task planning](#doc-task-planning)     | Stages 1–3: job expansion, the single-agent searches and graph filters, tray assignment, AGV assignment, the final checks, and the bay and VECS rules, which together build the event DAG | Explain how each job becomes events, how trays, parking spots and AGVs are chosen, and the bay, VECS and VRC rules                                   |
| 04 · [Motion planning](#doc-motion-planning) | Stage 4: CHUGG and SIPP, the timing model, and the `ContinuousState` timeline                                                                                                             | Explain how the event DAG becomes timed, collision-free motions and how long each move is assumed to take                                            |
| 05 · [Action graph](#doc-action-graph)       | Stage 5: action dependency graphs from first principles, the action DAG the scheduler sends to Dispatch, and a review of the whole pipeline                                               | Explain why execution is safe when robots run early or late, and how the response is built                                                           |
| 06 · [Dispatch](#doc-dispatch)               | An outline of the `central` package: the job queue, when Dispatch calls the scheduler, how it fills the request, what it checks in the response and how it executes the schedule          | Explain where each `PlanRequest` field comes from, why `base_schedule` is empty today, and what Dispatch accepts back                                |
| 07 · [Issue & proposal](#doc-proposal)       | The refactor: where the code is, what changes, the module layout, the solver interfaces, the staged plan, and proposed naming work                                                        | Review the design and pick up a stage of the plan                                                                                                    |
| 08 · [Verification](#doc-verification)       | Parity tests and benchmarks for the extracted solvers                                                                                                                                     | Show that a refactoring step changed no behaviour                                                                                                    |

This tab has four parts. Part I (sections [1](#bg-what-problem-does-this-software-solve)–[4](#bg-vocabulary), about 30 minutes) gives the picture the rest fills in. Part II (sections [5](#bg-the-garage-model-in-code)–[7](#bg-discretegaragestate-the-bridge-between-the-garage-and-the-planner), about an hour) covers what a plan call works on: the static garage model, the request and response messages field by field, and the garage snapshot built from the request. Part III (sections [8](#bg-package-anatomy-files-and-classes)–[15](#bg-schedulecontext-the-per-call-workspace), about 90 minutes) follows one `Plan()` call: the objects it creates, its steps, the reservation of the running schedule, the events and how they are replayed, the event DAG and the context that ties them together. Part IV (sections [16](#bg-packages-build-system-and-dependencies)–[19](#bg-reading-the-c-code-a-call-trace-and-a-route-through-the-source)) is reference material for when you open the code: building and testing, C++ idioms, and a call trace through one plan call. The call trace and its reading route cover the code behind tabs 03–05 as well; come back to them after reading those.

### How to read the code snippets

Every snippet starts with a **Where** line that names the function it comes from and what each variable is. Snippets are abridged (logging and some error handling removed) but keep the real names. These names recur everywhere, so learn them once:

| Name in the code                    | Type                                                                                  | What it is                                                                        |
|-------------------------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `this` inside `Scheduler::...`      | `const volley::scheduler::Scheduler*`                                                 | The one long-lived planner object owned by `SchedulerRos`. Its members end in `_` |
| `layout_`                           | `LayoutSPtr` (`std::shared_ptr<Layout>`)                                              | Parsed layout YAML: nodes, edges, bays, floors, resource windows                  |
| `motion_graph_`                     | `volley::GarageGraph`                                                                 | Search graph over (node, heading) poses; used by every path query                 |
| `collision_table_`                  | `volley::CollisionTable`                                                              | Answers “do these two footprints at these two poses collide?”                     |
| `cost_model_`                       | `cost::MotionCostModel`                                                               | Speeds, accelerations, lift and door times from ROS parameters                    |
| `request_data`                      | `const interfaces::msg::PlanRequest&`                                                 | The incoming `interfaces/msg/PlanRequest`                                         |
| `ctx`                               | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`)                                    | All mutable data for **one** plan call                                            |
| `ctx->event_dag`                    | `volley::ScheduleEventDag`                                                            | The event DAG that every stage reads and extends                                  |
| `working_state`                     | `volley::DiscreteGarageState` (a value, not a reference)                              | A scratch copy of the garage, advanced by replaying events                        |
| `event`                             | `std::shared_ptr<volley::ScheduleEvent>`                                              | One vertex of `ctx->event_dag`                                                    |
| `move`, `tray_move`                 | `volley::TrayMove*` (from `dynamic_cast`)                                             | The same event viewed as its concrete subclass                                    |
| `*_opt`                             | `std::optional<...>`                                                                  | Lookups that may fail, for example `working_state.GetTray(id)`                    |
| `stdx::Result`, `stdx::Expected<T>` | Success, or an error message (`stdx::Expected<void, JobFailure>` for a job expansion) | The return convention of every planning step; all are `[[nodiscard]]`             |
| `job_index`                         | `size_t`                                                                              | Position of the job in `ctx->scheduled_jobs`; stored in every event it creates    |

## What the scheduler does: the big picture

A customer vehicle sits on a **tray** inside an automated parking facility. An **AGV** (automated guided vehicle) drives under a tray, raises its lift, and carries the tray. A **bay** is the customer-facing handoff room; a **waypoint** is a navigation node; a **parking node** is where trays are stored; an **AGV charge** node is where robots recharge. Some installations have a **VECS** (an EV charging station, on a node of its own type, `TYPE_EV_CHARGE`) or a **VRC** (vertical reciprocating conveyor, a lift between floors). These are different resources with different rules.

A job such as **retrieve this payload** does not say how to do it. The Scheduler decides which tray moves are needed, which AGV does each one, which operations must happen first, and how long everything takes. It then returns a schedule of discrete commands that Dispatch executes. The scheduler never drives a motor and never talks to an AGV directly, and it keeps nothing between calls: each request carries the current garage state, and each answer is a complete new schedule.

### The pipeline in one picture

One call to `Scheduler::Plan()` turns a request into a schedule in five stages. The first three build one graph, the **event DAG**; the fourth plans motion in time; the fifth builds a second graph, the **action DAG**, which is what Dispatch executes.

![Planning stages](figures/01_pipeline.svg)

The five stages of `Scheduler::Plan`, from `PlanRequest` to the schedule Dispatch runs. The strip underneath shows what exists after each stage: the same event DAG (`ctx->event_dag`) is enriched by stages 1–3; CHUGG turns it into a timeline per entity; the response builds a new graph of actions from that timeline. The brackets give the standard names for each step. This is not a ROS thread or executor schedule.

1.  **Job expansion** turns each requested job into `ScheduleEvent`s, the discrete changes it needs (“move tray 17 into bay 21”, “open bay 21”), and adds “must finish before” edges between them. Some events are left incomplete on purpose: a tray move may not yet know which tray or where to ([section 15](#bg-job-expansion-from-jobs-to-events)).
2.  **Tray assignment** fills those blanks and adds moves for trays that are in the way, with edges that keep them in order ([section 16](#bg-tray-assignment-dotrayassignments)).
3.  **AGV assignment** decides which AGV carries each tray and adds its approach, lift and lower events; then `RemoveRedundantEdges()` removes redundant edges and `ValidateEventSequence` replays the whole DAG once (sections [17](#bg-agv-assignment-doagvassignments)–[18](#bg-reduce-and-sanitycheckevents)).
4.  **Motion planning.** CHUGG plans every event, one at a time in the DAG's topological order, as timed, collision-free motions along the garage graph. The result is a `ContinuousState`: a timeline of motions per AGV, bay and VECS (sections [21](#bg-chugg-the-motion-planner)–[24](#bg-continuousstate-the-timeline)).
5.  **The action DAG.** The response turns every motion that changes something into an `ActionNode`, orders actions that use the same space, copies the event DAG's edges across, adds VRC commands, and writes the graph as `Schedule.nodes` with parent indices ([section 25](#ad-how-the-action-dag-is-built)).

**Dispatch**, outside this package, starts each action as soon as all its parents are done. To react to anything new, it sends a new `PlanRequest` with the current garage state and the actions already running ([A request is not a plan](#bg-a-request-is-not-a-plan)).

### A request is not a plan

A `PlanRequest` describes a moment in a schedule that is already running: the garage now (`base_state`), the actions that keep running during the call (`base_schedule`) and the jobs still to plan (`pending_jobs`). Only the pending jobs are planned; everything `base_schedule` uses is reserved so the new plan cannot touch it. [Section 6.2](#bg-planrequest-one-moment-in-a-running-schedule) lays the request out on a time line, and [section 12](#bg-the-base-schedule-reserved-assets-and-keep-out-filters) explains the reservation.

### Four representations of one plan

The key distinction is **what** should happen versus **how and when** it happens. The same plan exists in four forms, each produced by one stage and consumed by the next:

| Layer  | Question                                                   | Example                                                    | Where it lives                                   | Structure                                           |
|--------|------------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------|-----------------------------------------------------|
| Job    | What outcome is requested?                                 | Retrieve a payload                                         | `SchedulerJob.msg` in `PlanRequest.pending_jobs` | a list                                              |
| Event  | What discrete state change is needed, and after what?      | Move tray 17 into bay 21, after bay 21 opens               | `ScheduleEvent` subclasses in `ctx->event_dag`   | the **event DAG** (`ScheduleEventDag`), no times    |
| Motion | When, and along which poses, does each thing move?         | AGV-2 waits at node 6 until 6 s, then drives 6 → 9 → 12    | `Motion`s in a `ContinuousState` from CHUGG      | a timeline per entity                               |
| Action | What command is sent to which machine, after which others? | `TYPE_AGV_COMMAND` from node 13 to node 15, after action 4 | `ActionNode.msg` inside `Schedule.msg`           | the **action DAG**, as an array with parent indices |

Events and actions are both discrete changes, and both graphs mean “must finish before”, so the two DAGs are easy to confuse. They are different graphs with different jobs: the event DAG is the planner's *input*, built before any time exists; the action DAG is its *output*, built from the planned motions, and it inherits the event DAG's edges rather than being converted from it ([section 20](#bg-motion-planning-and-the-response)).

### How to think about the scheduler

In the vocabulary of multi-robot planning, the five stages are three standard steps and an executor:

| Standard step                                                    | Here                                               | What it decides                                                                                         | What it ignores                                                                        |
|------------------------------------------------------------------|----------------------------------------------------|---------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| **Task planning and allocation**                                 | Stages 1–3: job expansion, tray and AGV assignment | Which discrete changes are needed, which tray and AGV do each, and which change must come first         | Time. Choices use single-AGV travel-time estimates that assume nobody else is moving   |
| **Multi-agent path finding (MAPF)**, with precedence constraints | Stage 4: CHUGG (prioritized planning with SIPP)    | When each event happens and which poses each AGV passes through, without any two footprints overlapping | Changing the plan's content: it cannot reorder, reassign or add events, only time them |
| **Action dependency graph (ADG)**                                | Stage 5: the response                              | Which action must wait for which, so that robots running early or late still never collide              | The planned times themselves, which are dropped except as each action's `duration`     |
| **Executor**                                                     | Dispatch (not in this package)                     | When to start each action: as soon as its parents are done                                              | Planning; anything new means a new `PlanRequest`                                       |

The scheduler follows the standard order MAPF → ADG → executor (the [Action graph](#doc-action-graph) tab builds the ADG from scratch). What is particular here is the MAPF input: not one goal per robot, but a precedence graph of events for many entities. Four ideas make the code much easier to read:

- **Discrete state, replayed.** Until CHUGG, the garage is a `DiscreteGarageState` snapshot and an event is applied to it in one step. Every stage that needs “where is everything now?” copies `ctx->initial_state` and replays the events so far ([section 15.4](#bg-every-job-sees-the-garage-through-working_state)).
- **Edges are added from many places.** Job rules, tray conflicts, AGV occupancy and path repair all add “must finish before” edges to the same event DAG, and `RemoveRedundantEdges()` removes the redundant ones ([section 12.7](#bg-how-the-dag-grows-during-plan)).
- **The topological order is a priority order.** Stages replay, and CHUGG plans, events in one deterministic topological order that prefers lower job indices. An event earlier in that order gets first claim on space and time ([section 21.1](#bg-inside-solvesequential)).
- **Time appears late and leaves early.** Before CHUGG, durations are only cost estimates; CHUGG assigns real start times; the response keeps only each action's duration and the order between actions.

### Where the code is

The five stages are very different in size, and where their code lives depends on whether you count only the `scheduler` package or also the libraries it calls:

- **Inside `scheduler`, almost everything is task planning.** Since PR \#1018 each stage has its own source file, so the split can be read off the file list ([section 8](#bg-package-anatomy-files-and-classes)). Of the 3,799 lines in its source files (without the ROS node), 2,771 (73%) are stages 1–3: job expansion 1,125 (`job_expansion.cpp` with the bay-rebalancing and event-builder files it uses), tray assignment 709 (`tray_assignment.cpp`), AGV assignment 830 (`agv_assignment.cpp`), the final check 107 (`validation.cpp`). The largest function is `AssignTrays` (284 lines); `Plan` is 112 and `AssignAgvs` 88. Before PR \#1018 the same code was 4,720 lines in two files (`scheduler.cpp` 4,200, `utils.cpp` 520); the narration logging it removed and the helpers it extracted account for most of the difference.
- **Motion planning is large, but it lives in `motion_planner`.** The scheduler's part is `PlanMotions`, 26 lines. Behind it, CHUGG's sequential solver, SIPP, the safe-interval table and the timeline types are about 3,870 lines of `motion_planner` that the scheduler actually runs.
- **The scheduler calls a narrow interface, but one solver uses most of the package.** `PlanMotions` makes three calls (`ComputeEdgeDurations`, `ComputeAllPairsShortestPathCosts`, then `Chugg::SolveSequential`), and task planning calls a handful of searches. Tracing calls from the scheduler's sources, about 660 lines of `motion_planner` are never reached: the unfinished CBS solver (`SolveCbs` and its helpers, [section 23.1](#bg-what-can-be-configured)), `CoalesceTrajectory` (CHUGG's comments say it is deliberately not used), debug printers only referenced from commented-out code, and a few helpers. Everything else, about 89% of the package, runs on a normal plan call. The library is still built and linked whole (`volley_add_library(... DIRECTORY src)`), and its own tests may exercise the unused parts.
- **Task planning also uses `motion_planner`.** The searches and filters that job expansion and tray assignment call (blocking-tray, open-space and empty-tray searches, AGV hiding, graph filters and path finding; [section 7](#mp-single-agent-searches)) are another 1,420 lines there, and `BottleneckAssignment` lives in `task_planner` (not in the snapshots). With them, task planning is about 4,000 lines.
- **The action graph is small.** About 460 lines, all in `action_graph.cpp`: `BuildActionGraph`, its helpers and the VRC insertion.

Counting the library code that actually runs, task planning (about 4,000 lines) and motion planning (about 3,900) are about the same size, and the action graph (about 460) is a small fraction of either. The difference in kind matters more than the line counts: motion planning and the action graph are general algorithms that know nothing about cars, bays or VECS, while task planning is where every garage rule lives (twelve job types, bay modes, headings, EV charging, blocking trays). Floors and VRCs are the exception: task planning has no rule for them yet ([section 7](#ly-vrc-support-status)). [Section 2.1](#pr-where-the-code-will-live) discusses what that means for the refactor.

![Where the code is, by pipeline stage](figures/96_code_by_stage.svg)

**Where the code is, by pipeline stage.** Solid segments are in the `scheduler` package, pale segments with a dashed outline are in library packages, and the empty dotted segment is `motion_planner` code the scheduler never calls. Task planning dominates the scheduler; motion planning's size is in `motion_planner`, most of which runs; the action graph is small. Counts are lines of C++ without tests, measured on the snapshots; `common_ros` and `task_planner` are not counted.

### A map of the study pack by stage

The table below connects each pipeline stage to the code that implements it and to the parts of this study pack that explain it. Use it as an index: find the stage under study, note its entry point in the source, and follow the links to the relevant sections and figures.

| Stage                                                                     | Entry point                                                                           | Where                                                                                                                                                                                                                                                     | Key figures                                                                                                                                                                                 |
|---------------------------------------------------------------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Request and context                                                       | `Scheduler::Plan`, `ValidateBaseState`                                                | This tab, sections [6](#bg-ros-messages-and-services), [9](#bg-objects-ownership-and-lifetimes), [10](#bg-one-plan-call-step-by-step), [11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters), [13](#bg-schedulecontext-the-per-call-workspace) | [Figure 1](#bg-fig-118_plan_request_timeline), [Figure 1](#bg-fig-22_plan_control_flow), [Figure 1](#bg-fig-116_base_schedule_reservation), [Figure 1](#bg-fig-61_schedule_context_anatomy) |
| The event DAG as a data structure                                         | `ScheduleEventDag`                                                                    | This tab, sections [11](#bg-event-types-and-polymorphism), [12](#bg-directed-acyclic-graphs-then-scheduleeventdag)                                                                                                                                        | [Figure 1](#bg-fig-63_event_dag_classes), [Figure 1](#bg-fig-68_topological_priority)                                                                                                       |
| 1–3 · Task planning: job expansion, tray and AGV assignment, final checks | `ExpandJob` → `Expand<Type>Job`, `AssignTrays`, `AssignAgvs`, `ValidateEventSequence` | The [Task planning](#doc-task-planning) tab                                                                                                                                                                                                               | [Figures 1](#bg-fig-26_retrieve_walkthrough), [1](#bg-fig-27_tray_assignment_flow) and [1](#bg-fig-29_agv_matching) there                                                                   |
| 4 · Motion planning                                                       | `PlanMotions`, `Chugg::SolveSequential`                                               | The [Motion planning](#doc-motion-planning) tab                                                                                                                                                                                                           | [Figures 1](#bg-fig-91_planning_pipeline), [1](#bg-fig-93_chugg_sequential) and [1](#bg-fig-94_trapezoid_runs) there                                                                        |
| 5 · The action DAG                                                        | `BuildActionGraph`                                                                    | The [Action graph](#doc-action-graph) tab                                                                                                                                                                                                                 | [Figures 1](#ad-fig-84_adg_delay), [1](#bg-fig-32_motions_to_actions) and [1](#ad-fig-87_adg_in_scheduler) there                                                                            |

## Where the scheduler runs: the node and its interfaces

The package builds one shared library (`libscheduler`: `scheduler.cpp`, one file per pipeline stage and four helper files; [section 8](#bg-package-anatomy-files-and-classes)) and one ROS 2 component (`scheduler_component.cpp`, `scheduler_ros.cpp`) that is also installed as the executable `scheduler_node`. Three layers wrap each other:

1.  **`SchedulerComponent`** reads ROS parameters (`layout`, `scheduler.cost_audit`, `scheduler.bay_readiness_ratio`, and the AGV / VRC / bay / VECS performance limits in `ReadMotionCostParams`) into a `SchedulerParams`, finds the layout file with `GetLayoutPathByName`, and builds a `SchedulerRos`. Missing parameters exit the process. It is the only one of the three left in namespace `volley`: `volley::SchedulerComponent` is the plugin name the launcher loads.
2.  **`SchedulerRos`** owns every ROS object: the `plan` service, the `set_bay_readiness_ratio` service, the `debug/printdags` toggle, two 5 s publishers, and four clients into `/central`. It owns the `Scheduler` through a `shared_ptr`.
3.  **`Scheduler`** (`volley::scheduler::Scheduler`, like `SchedulerRos`) is the planning core. Apart from a logger and `rclcpp::Time`, it knows nothing about ROS transport, which is why tests can construct it directly.

![Scheduler node context](figures/20_system_context.svg)

The scheduler node and its ROS interfaces. Dispatch (in the central node) calls `plan` and executes the schedule it gets back. The scheduler calls back into `/central` to ask for follow-up jobs; it does this through three `std::function` members that `SchedulerRos` fills in, so `Scheduler` itself never holds a ROS client. Timers run in their own callback group so a long `Plan()` cannot starve them. The caller's identity (Dispatch) is inferred from comments and client topic names.

The whole service handler is a few lines. This is the only place where ROS hands a request to the planner:

``` cpp
// Where: SchedulerRos::SchedulerRos(...) in src/scheduler_ros.cpp:44, the "plan" service callback.
//   this        -> volley::scheduler::SchedulerRos (the ROS adapter, not the planner)
//   scheduler_  -> SchedulerSPtr (std::shared_ptr<Scheduler>), created in this constructor
//   request     -> interfaces::srv::Plan::Request::SharedPtr; request->request_data is an
//                  interfaces::msg::PlanRequest
plan_srv_ = rclcppx::CreateService<interfaces::srv::Plan>(
    node_, "plan",
    [this](interfaces::srv::Plan::Request::SharedPtr request,
        interfaces::srv::Plan::Response::SharedPtr response) {
      auto response_msg = scheduler_->Plan(request->request_data, node_->now());
      rclcpp::Time now = node_->now();
      for(auto& job_data : response_msg.scheduled_jobs) {
        job_data.job.time_planned = now;          // stamp every job, failed or not
      }
      response->response_data = std::move(response_msg);
      return response;
    },
    1u);
```

Two side channels matter when you debug: `set_bay_readiness_ratio` stores a new ratio in the `std::atomic<float> target_insert_ready_bay_fraction_` (it rejects values outside \[0, 1\] and, since PR \#1018, non-finite ones) and, if it changed, asks `/central/rebalance_garage` for a `REBALANCE_GARAGE` job; and a failed `INSERT` job triggers `/central/clean_garage` from inside `Plan()`.

## The physical garage and its coordinate system

The supplied **Pecos** layout has **28 nodes and 37 undirected edges** in two YAML sections (`sandbox_eng` and `sandbox_qa`). It defines **two bays** (`B7`, `B21`), **three AGV charging nodes** (`C10`, `C14`, `C16`), plus parking and waypoint nodes. It does not define a VRC. Node positions come from the YAML; connectivity comes from the `edges` list, not from visual distance.

![Pecos facility graph](figures/15_facility_topology.svg)

Pecos facility graph drawn from the YAML coordinates in metres. Blue rectangles are **parking nodes**, drawn with the layout's XL parking window (5.79 m along x by 2.21 m along y) centred on the node; teal rectangles are **bays** with the customer door on the garage side; violet circles are **AGV chargers**; grey dots are **waypoints**; thin lines are **garage-graph edges**; shaded bands mark waypoint corridors; dashed outlines are the two YAML sections. No AGVs or trays are drawn: the YAML contains no occupancy.

Notice how dense the parking block is: stalls touch along x, so a tray at `P17` can only leave through `P15` or `P20`. That is why **blocking trays** ([section 16](#bg-tray-assignment-dotrayassignments)) are a core problem rather than an edge case.

### Geometric versus logical position

The continuous position vector **\mathbf p=\[x,y\]^\mathsf T\in\mathbb R^2** holds the horizontal coordinate **x** and vertical coordinate **y**, both in metres. A planar configuration **\mathbf q=\[x,y,\theta\]^\mathsf T\in\mathbb R^3** adds the heading **\theta**. In `GeometricPose.msg` the yaw **\theta** is in radians. `GaragePose.msg` is different: it holds a node identifier **i\in\mathbb N** and an integer heading **h\in\mathbb Z** in degrees. The planner works almost entirely in `GaragePose`.

``` text
# msg/GeometricPose.msg          # msg/GaragePose.msg
float32 x       # metres        uint32 node_id
float32 y       # metres        int16 heading   # degrees, +CCW from local north; 90 = west
float32 yaw     # radians
```

### Node, heading, pose, vertex: the words for places

Four words name a place in this code, and they are easy to mix up because they nest. Each has one type and one owner:

| Word        | What it is                                                                                                                                                                                                                                                                               | C++ type (owner)                                                                                                                                       | W22 on Pecos                                                                                                            |
|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| **node**    | A place in the layout: a point on the floor with an id, a type and the headings it allows. Edges between nodes say which places are adjacent                                                                                                                                             | `GarageNodeMsg`, stored in `Layout::nodes_` ([section 6.1](#bg-layout-places-in-sorted-vectors-and-ordered-maps))                                      | node 22: x 30.88 m, y 21.74 m, Waypoint, `headings: [0, 90]`                                                            |
| **heading** | The direction something at a node faces, in whole degrees: 0 along +y (garage north), counter-clockwise positive ([Figure 4](#bg-fig-78_heading_convention)). For an AGV it is the direction of its body x axis, which runs along its long side ([section 3](#ly-agv-coordinate-system)) | `int16` field of `GaragePoseMsg`, in \[-179, 180\] (`GaragePose.msg`); the YAML lists 0–179 and each also allows its reciprocal, so 90 also allows −90 | −90, 0, 90, 180                                                                                                         |
| **pose**    | A node plus a heading: where something is *and* which way it faces. Almost every API in the planner takes poses, not nodes                                                                                                                                                               | `GaragePoseMsg {node_id, heading}`; listed by `PoseGraph::poses_` ([section 6.2](#bg-posegraph-from-nodes-to-poses))                                   | `{node_id: 22, heading: -90}`, `{node_id: 22, heading: 0}`, `{node_id: 22, heading: 90}`, `{node_id: 22, heading: 180}` |
| **vertex**  | The number the search graph `motion_graph_` gives one pose. It stores nothing but that pose and its edges                                                                                                                                                                                | `GarageGraph::Vertex` = `std::size_t`, in `motion_graph_`, a `volley::GarageGraph` ([section 6.3](#bg-garagegraph-and-its-vertex))                     | 42, 43, 44, 45                                                                                                          |

![Headings: what the number means](figures/78_heading_convention.svg)

The heading convention. Left: 0 points along +y and angles grow counter-clockwise, so 90 faces −x and −90 faces +x. Headings are stored in \[-179, 180\]: 270 is never a valid value. `GeometricPoseMsg.yaw` is the same angle in radians. Middle: a tray (or AGV) footprint is a centred rectangle with its long side along the heading, so h and h+180 cover the same floor; only the facing differs. Right: how YAML headings become poses.

![Node, pose, vertex](figures/79_node_pose_vertex.svg)

One place, several names. W22 is one node, four poses (one per allowed heading) and four vertices (42–45). The two arrows are the only conversions the code makes: `GetAllowedHeadings` (node → poses) and `motion_graph_.GetVertexFromPose` (pose → vertex). The table lists the other structures that name the same place.

The rule of thumb: **the layout talks in nodes, the planner in poses, the search graph in vertices.** Converting is one-way and lossy in one place only: from a vertex you can always get its pose (`motion_graph_.GetPoseFromVertex`) and its node (`motion_graph_.GarageNodeFromVertex`); from a node you get several poses; from a pose you get a vertex only if the node allows that heading. `motion_graph_.GetVertexFromPose(pose)` returns `std::optional<Vertex>`; an empty optional (an unknown node, a heading the node does not allow, or a heading written in a different form) is the usual cause of “does not exist in garage graph” errors.

The same words also mean other things in this code base. When you read one, check which structure it belongs to:

| Word    | Meaning here                                                     | Other meanings you will meet                                                                                                                                                                                   |
|---------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| node    | A layout place (`GarageNodeMsg`)                                 | a ROS node (`SchedulerRos`'s process, [section 2](#bg-where-the-scheduler-runs-the-node-and-its-interfaces)); an `ActionNode`, one command in the output schedule ([section 7](#bg-ros-messages-and-services)) |
| vertex  | A pose's index in `motion_graph_` (`GarageGraph::Vertex`)        | an event's index in the event DAG (`ScheduleEventDag::Vertex`, [section 12.4](#bg-what-is-stored-vertices-edges-and-shared-events)); a node's index in `Layout::graph_` (its position in `nodes_`, not its id) |
| edge    | A move between two poses in `motion_graph_`, with a `Transition` | an undirected link between two node ids in the YAML; `CollisionTable::Edge`, a pair of poses used as a table key; a dependency "u before v" in the event DAG                                                   |
| heading | An integer angle in a `GaragePoseMsg`                            | `yaw`, the same angle in radians in `GeometricPoseMsg`; a bay's *inbound heading*, the heading a car faces when it enters (`GetInboundHeading`)                                                                |
| pose    | A `GaragePoseMsg` (node + heading)                               | a `GeometricPoseMsg` (metres + radians); a `SizedPoseMsg` (a pose plus a footprint size)                                                                                                                       |

### Asset types, and the other kinds of “type”

The scheduler plans for six kinds of physical thing. This guide calls them **asset types**: the AGV, the tray, the payload (the customer's car), the bay, the VECS (EV charger) and the VRC (vehicle lift). Three of them move and have a pose; three are fixed and are layout nodes themselves.

![Asset types](figures/80_asset_types.svg)

The six asset types. For each: its id (a `uint16` plus a one-letter `GarageEntityId.entity_type`, except the payload, which has a `Guid`), the message that holds its state in `DiscreteGarageState`, where it sits in the layout, the `ScheduleEvent` that changes it in a plan, the `ActionNode` command that executes it, and its footprint type in the collision table.

“Type” appears in many other places in this code, each with its own enum. When this guide says one of these words, it means exactly this field:

| This guide says     | Meaning                                     | Field or enum                               | Values                                                                                                 |
|---------------------|---------------------------------------------|---------------------------------------------|--------------------------------------------------------------------------------------------------------|
| **asset type**      | Which kind of physical thing                | `GarageEntityId.entity_type` (`string<=1`)  | `'a'` AGV, `'t'` tray, `'b'` bay, `'v'` VECS, `'r'` VRC (`'s'` system); a payload has a `Guid` instead |
| **node type**       | What a layout place is for                  | `GarageNodeMsg.type` (`uint8`)              | `TYPE_PARKING` 1, `WAYPOINT` 2, `LIFT` 3, `BAY` 4, `AGV_CHARGE` 5, `EV_CHARGE` 6, `BLIFT` 7            |
| **footprint type**  | Which shape the collision table checks      | `CollisionEntityId` (`CollisionEntityId_t`) | `BAY_ODP` 0, `TRAY_LEGS` 1, `TRAY` 2, `AGV` 3, `PAYLOAD` 4 + parking-window index                      |
| **job type**        | What a request asks for                     | `SchedulerJob.type` (`uint8`)               | `TYPE_MOVE_AGV` 1 … `TYPE_REBALANCE_GARAGE` 13 ([section 15](#bg-job-expansion-from-jobs-to-events))   |
| **event type**      | Which `ScheduleEvent` subclass              | `ScheduleEventType`                         | `AGV_MOVE` 1, `BAY_TRANSITION` 2, `TRAY_MOVE` 3, `VECS_TRANSITION` 4, `VRC_TRANSITION` 5               |
| **action type**     | Which machine executes an output action     | `ActionNode.type` (`uint8`)                 | `TYPE_AGV_COMMAND` 1, `BAY_COMMAND` 2, `VECS_COMMAND` 3, `VRC_COMMAND` 4                               |
| **transition type** | What kind of move a `motion_graph_` edge is | `TransitionType`                            | `LOCOMOTE`, `STRAFE`, `ROTATION`, `VRC_TRANSITION`                                                     |

### How values are written in this guide

Numbers in this code mean different things depending on the field they sit in, so this guide writes the field names:

- **A pose** is written `{node_id: 22, heading: 90}`, a `GaragePoseMsg`. The heading is in degrees, in \[-179, 180\].
- **A geometric pose** is written `{x: 30.88, y: 21.74, yaw: 1.571}` (metres, metres, radians).
- **A vertex** is written “Vertex 44” in text and `v44` on maps (a `GarageGraph::Vertex`).
- **Map labels** are a node-type letter plus the `node_id`: `P17` is the parking node with `node_id` 17, `W22` a waypoint, `B21` a bay, `C14` an AGV charger.
- **Assets on maps**: `T17` is the tray with `tray_id` 17, and `A`, `B` are AGVs.
- **Compact labels**: where space is tight, figures write `W18@90` for `{node_id: 18, heading: 90}`; every map figure repeats this key in its footnote.

### Layout, GarageGraph and CollisionTable: three views of the same garage

The scheduler builds three static objects from the layout file, once, in its constructor, and uses them for every plan:

``` cpp
// src/scheduler.cpp:86 — Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger,
//                                             const SchedulerParams& params)
layout_(std::make_shared<Layout>(layout_filepath)),   // LayoutSPtr: the parsed YAML
motion_graph_(PoseGraph(layout_)),                    // volley::GarageGraph, the search graph, built from
                                                      //   a temporary volley::PoseGraph of the Layout
collision_table_(motion_graph_, logger),              // volley::CollisionTable, built from the graph
// ...then StorePreferredPayloadHeadingsForRetrieval() stores one retrieval heading per parking node
// in motion_graph_
```

They are easy to confuse because all three "describe the garage". The difference is the question each one answers.

- **`Layout` (`layout_`) is about places.** It is the YAML file in memory: nodes with an id, a type, a position in metres, the headings they allow and whether an AGV may rotate there; undirected edges between node ids; parking-window sizes; bay facts (inbound heading, prioritisation, floors). You ask it "what is node 22?" with `layout_->GetNodeById(22)`, which returns `std::optional<GarageNodeMsg>`.
- **`GarageGraph` (`motion_graph_`) is about motion.** Its vertices are **poses**, a node *plus* a heading, and its edges are the moves between poses. Every heading a node lists in the YAML gives two poses, the heading and its reciprocal, so most nodes are two vertices and `W22`, which lists headings 0 and 90, is four; a heading the node does not allow has no vertex at all. Every path search runs on `motion_graph_`. You translate between the two worlds with `motion_graph_.GetVertexFromPose(GaragePoseMsg) -> std::optional<Vertex>` and back with `motion_graph_.GetPoseFromVertex(v)` or `motion_graph_.GarageNodeFromVertex(v)`.

![Layout vs GarageGraph](figures/51_layout_vs_garage_graph.svg)

The same corner of the Pecos garage seen as a Layout (left: nodes, positions, YAML fields) and as a GarageGraph (right: one vertex per pose, numbered with its `Vertex` value, edges are moves). Each YAML heading gives two poses, so W22's headings 0 and 90 become vertices 42–45, and rotations exist only at W22, the one node here with `rotation_allowed`. [Section 6](#bg-the-garage-model-in-code) shows the rules.

- **`CollisionTable` (`collision_table_`) is about space.** It answers one question: would footprint *A* at pose *a* overlap footprint *B* at pose *b*? The scheduler's direct calls use `collision_table_.Query(fixed_id, queried_id, fixed_pose, queried_pose) -> bool`; other overloads take edges (moves), or return every conflicting pose and edge at once. The footprint is picked by a **collision id** (`CollisionEntityId_t`), computed from the entity's state by `CollisionEntityIdFromAgvState`, `...FromTrayState` or `...FromPayloadState`, so an empty AGV, an AGV carrying a tray and a tray with a large car get the right shapes. Because it depends on poses, not just nodes, the same two nodes can conflict at one heading and be fine at another.

![CollisionTable](figures/52_collision_table.svg)

Two `Query` calls for a tray at W22 against a tray parked at W18: heading 90 is clear, heading 0 overlaps. The grid on the right shows the idea of a table built once and then looked up (overlaps computed here from schematic rectangles; the real footprint sizes are constants in the `common` package). The real storage, four nested hash maps, is in [section 6.5](#bg-collisiontable-precomputed-conflict-sets).

Most code does not call `Query` directly. It asks `volley::BuildStaticObstacleFilter(id, motion_graph_, working_state, collision_table_, ...)` (`GetStaticFilter` before PR \#1018), which uses the table to mark which graph vertices and edges a given footprint cannot use given everything in `working_state`, and then tests `filters.IsEnabled(vertex)` or `IsEnabled(edge)` (the [section 7.3](#mp-static-filters), explains every filter rule). `ctx->keep_out_filter_by_footprint`, built once per `Plan()`, works the same way for disabled nodes and entities. The direct `Query` calls are in `AssignTrays` (is another tray in the way of the root tray's next pose?) and `FindAssignedAgvsBlockingPickup` (would two AGVs conflict at a pickup?).

The fourth structure is the one that changes: `DiscreteGarageState` ([section 5](#bg-discretegaragestate-the-bridge-between-the-garage-and-the-planner)) records **who is where right now**. Layout, graph and table never change after start-up; the state is different in every plan request. [Section 6](#bg-the-garage-model-in-code) opens up the first three: their containers, their lookups and what each costs.

## Vocabulary

The scheduler code and this study pack use a small set of terms with precise, and sometimes easily confused, meanings. The table gives each term, its meaning and the distinction most likely to cause a misreading; consult it whenever a later section uses a word in an unfamiliar way.

| Term                                               | Meaning                                                                                                                                                                                                     | Important distinction                                                                                                                                                |
|----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `SchedulerJob`                                     | A requested outcome, such as `TYPE_RETRIEVE`                                                                                                                                                                | Arrives in `PlanRequest.pending_jobs`                                                                                                                                |
| `DiscreteGarageState` (DGS)                        | Where every AGV, tray, payload, bay, VECS and VRC is, and its state                                                                                                                                         | A snapshot, not a trajectory                                                                                                                                         |
| [node](#bg-term-node), [heading](#bg-term-heading) | A node is a place in the layout (`GarageNodeMsg`); a heading is the direction something there faces, in degrees ([Figure 4](#bg-fig-78_heading_convention))                                                 | A node lists its headings in the YAML; each also allows its reciprocal (h+180)                                                                                       |
| [asset type](#bg-term-asset-type)                  | Which kind of physical thing: AGV, tray, payload, bay, VECS or VRC ([Figure 6](#bg-fig-80_asset_types))                                                                                                     | Not the same as node type, footprint type, job type, event type or action type: [the kinds of “type”](#bg-asset-types-and-the-other-kinds-of-type)                   |
| [pose](#bg-term-pose), [`Vertex`](#bg-term-vertex) | A pose is a node plus a heading (`GaragePoseMsg`); a `Vertex` is that pose's index in `motion_graph_`, the search graph, a `volley::GarageGraph` ([section 6.3](#bg-garagegraph-and-its-vertex))            | A `Vertex` is a `std::size_t`, not a node: W22 is one node, four poses and four vertices ([the words for places](#bg-node-heading-pose-vertex-the-words-for-places)) |
| `ScheduleEvent`                                    | One discrete state change, e.g. a `TrayMove`                                                                                                                                                                | Abstract C++ base class in `planner_core`, not a ROS message                                                                                                         |
| `TrayMove`                                         | Move one tray to one pose                                                                                                                                                                                   | May start with no tray id, no destination, and no AGV                                                                                                                |
| `AgvMove`                                          | One AGV pose change **or** one lift change                                                                                                                                                                  | Holds `std::variant<interfaces::msg::AgvLiftChanged, interfaces::msg::AgvPoseChanged>`                                                                               |
| `BayTransition`, `VecsTransition`                  | Commands for bays and EV chargers                                                                                                                                                                           | Created by job expansion                                                                                                                                             |
| `ScheduleEventDag`                                 | The **event DAG**: events with edges u → v meaning u must finish before v starts. Built by stages 1–3; CHUGG's input                                                                                        | Lives in `ctx->event_dag`; has no times. Not the action DAG                                                                                                          |
| `PlanContext`                                      | All mutable data for one plan call: `initial_state`, the event DAG, the job list and two bookkeeping maps                                                                                                   | Created in `Plan()`, dies when `Plan()` returns; every field in [section 13](#bg-schedulecontext-the-per-call-workspace)                                             |
| working state                                      | `ctx->initial_state` plus a replay of events                                                                                                                                                                | Recomputed many times, never stored                                                                                                                                  |
| critical path                                      | The graph path a tray takes to its destination                                                                                                                                                              | Trays on it are **blocking trays**                                                                                                                                   |
| `occupancy_history`                                | A `GarageOccupancyChecker` in `TrayAssignmentState` mapping poses to the events that used them (`freeing_moves` before PR \#1018)                                                                           | How “shared space” becomes DAG edges                                                                                                                                 |
| AMIGA                                              | “Arguably More Intelligent aGv Assignment”: the cost functions in `AssignAgvs`                                                                                                                              | Bottleneck matching of AGVs to tray moves                                                                                                                            |
| MAPF                                               | Multi-agent path finding: collision-free paths in time for many robots. Here with precedence constraints between events of different entities                                                               | The step CHUGG performs; it times events, it does not choose them                                                                                                    |
| CHUGG                                              | The motion planner, `volley::Chugg` in `motion_planner/chugg.hpp` (“Constrained Huge Unknown Graph alGorithm”; [section 21](#bg-chugg-the-motion-planner))                                                  | Plans the event DAG's events one at a time, in topological order (prioritized planning)                                                                              |
| SIPP                                               | Safe Interval Path Planning: CHUGG's search for one AGV over (place, safe time window) states ([section 21.2](#bg-sipp-the-single-agv-search))                                                              | Avoids every motion already planned; never moves them                                                                                                                |
| `ContinuousState`, `Motion`                        | CHUGG's output: per entity, a timeline of motions; a motion is a wait at a pose or a move along one edge, with a time interval and the event it implements ([section 24](#bg-continuousstate-the-timeline)) | “Continuous” means continuous time; the discrete counterpart is `DiscreteGarageState`                                                                                |
| action DAG (ADG)                                   | An action dependency graph: one action per motion that changes something, with edges that order shared space and copied event edges ([section 6.2](#ad-how-the-action-dag-is-built))                        | Built after CHUGG, from its motions; the output                                                                                                                      |
| `ActionNode`                                       | One action of the action DAG: an executable command with parent indices into `Schedule.nodes`                                                                                                               | The only thing Dispatch executes                                                                                                                                     |

### Acronyms and abbreviations

Every acronym in this pack, with its expansion. In the text, the first mention of an acronym in each section links to the section that explains it, and hovering it shows the expansion.

| Acronym | Stands for                                                                                                                                                                         | Where                                                                                   |
|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| AAAI    | AAAI Conference on Artificial Intelligence (Association for the Advancement of Artificial Intelligence)                                                                            | —                                                                                       |
| AAMAS   | International Conference on Autonomous Agents and Multiagent Systems                                                                                                               | —                                                                                       |
| ADG     | Action dependency graph: the order in which robots use shared space                                                                                                                | [explained here](#ad-why-a-timed-plan-is-not-enough)                                    |
| AGV     | Automated guided vehicle: the robot that drives under a tray, lifts it and carries it                                                                                              | [explained here](#bg-what-problem-does-this-software-solve)                             |
| AIJ     | Artificial Intelligence (journal)                                                                                                                                                  | —                                                                                       |
| AMIGA   | Arguably More Intelligent aGv Assignment: the cost model of AGV assignment                                                                                                         | [explained here](#bg-agv-assignment-doagvassignments)                                   |
| API     | Application programming interface                                                                                                                                                  | —                                                                                       |
| BGL     | Boost Graph Library                                                                                                                                                                | —                                                                                       |
| CAD     | Computer-aided design: the drawing that defines garage north                                                                                                                       | —                                                                                       |
| CBS     | Conflict-based search: plans agents alone, then branches on each conflict with constraints                                                                                         | [explained here](#mp-the-standard-mapf-problem)                                         |
| CBS-PC  | Conflict-based search with precedence constraints (a MAPF-PC solver)                                                                                                               | [explained here](#pr-related-formulations)                                              |
| CBS-TA  | Conflict-based search with task assignment: assigns goals to agents inside the search                                                                                              | [explained here](#pr-related-formulations)                                              |
| CCBS    | Continuous-time conflict-based search                                                                                                                                              | [explained here](#mp-from-chugg-to-standard-solvers)                                    |
| CCW     | Counter-clockwise                                                                                                                                                                  | —                                                                                       |
| CHUGG   | Constrained Huge Unknown Graph alGorithm: the motion planner                                                                                                                       | [explained here](#bg-chugg-the-motion-planner)                                          |
| CI      | Continuous integration: the automated build and test runs                                                                                                                          | —                                                                                       |
| CP      | Constraint programming                                                                                                                                                             | [explained here](#pr-related-formulations)                                              |
| CP-SAT  | Google OR-Tools' constraint-programming solver built on a SAT solver                                                                                                               | [explained here](#pr-related-formulations)                                              |
| DAG     | Directed acyclic graph                                                                                                                                                             | [explained here](#bg-directed-acyclic-graphs-then-scheduleeventdag)                     |
| DGS     | DiscreteGarageState (this pack's shorthand)                                                                                                                                        | [explained here](#bg-discretegaragestate-the-bridge-between-the-garage-and-the-planner) |
| ECBS    | Enhanced conflict-based search: bounded-suboptimal CBS                                                                                                                             | [explained here](#mp-from-chugg-to-standard-solvers)                                    |
| EV      | Electric vehicle                                                                                                                                                                   | —                                                                                       |
| GUID    | Globally unique identifier, 128 bits (interfaces/msg/Guid)                                                                                                                         | —                                                                                       |
| HTN     | Hierarchical task network: goals decomposed into subtasks by methods                                                                                                               | [explained here](#pr-related-formulations)                                              |
| ICAPS   | International Conference on Automated Planning and Scheduling                                                                                                                      | —                                                                                       |
| IEEE    | Institute of Electrical and Electronics Engineers                                                                                                                                  | —                                                                                       |
| MAPD    | Multi-agent pickup and delivery: a stream of pickup and delivery tasks planned online                                                                                              | [explained here](#pr-related-formulations)                                              |
| MAPF    | Multi-agent path finding: collision-free paths for several agents on a shared graph                                                                                                | [explained here](#mp-the-standard-mapf-problem)                                         |
| MAPF-PC | Multi-agent path finding with precedence constraints: each agent has a goal sequence, and some goals must be reached before others                                                 | [explained here](#mp-chuggs-problem-in-symbols)                                         |
| NAMO    | Navigation among movable obstacles                                                                                                                                                 | [explained here](#pr-related-formulations)                                              |
| ODP     | Overdrive plate: a sliding plate at the edge of a bay that stops the customer's car from driving over the edge. `BAY_ODP` is the collision entity for the space the plate takes up | —                                                                                       |
| PBS     | Priority-based search: searches over priority orders between agents, planning each with prioritized planning                                                                       | [explained here](#mp-from-chugg-to-standard-solvers)                                    |
| PBS-PC  | Priority-based search with precedence constraints (a MAPF-PC solver)                                                                                                               | [explained here](#pr-related-formulations)                                              |
| PDDL    | Planning Domain Definition Language                                                                                                                                                | [explained here](#pr-related-formulations)                                              |
| POCL    | Partial-order causal-link planning: plans as partially ordered actions with causal links                                                                                           | [explained here](#pr-related-formulations)                                              |
| RA-L    | IEEE Robotics and Automation Letters                                                                                                                                               | —                                                                                       |
| RCPSP   | Resource-constrained project scheduling problem                                                                                                                                    | [explained here](#pr-related-formulations)                                              |
| RMF     | Robotics Middleware Framework (Open-RMF), an open-source fleet-management framework                                                                                                | —                                                                                       |
| ROS     | Robot Operating System (ROS 2): the middleware the scheduler runs on                                                                                                               | [explained here](#bg-ros-messages-and-services)                                         |
| SHA     | Secure Hash Algorithm: here, a git commit hash                                                                                                                                     | —                                                                                       |
| SIPP    | Safe interval path planning: single-agent search over (place, safe time interval) states                                                                                           | [explained here](#bg-sipp-the-single-agv-search)                                        |
| SOC     | Sum of costs: the sum of all agents' arrival times                                                                                                                                 | [explained here](#mp-the-standard-mapf-problem)                                         |
| SoCS    | Symposium on Combinatorial Search                                                                                                                                                  | —                                                                                       |
| STN     | Simple temporal network: time points with difference constraints                                                                                                                   | [explained here](#pr-related-formulations)                                              |
| SVG     | Scalable Vector Graphics: the format of this pack's figures                                                                                                                        | —                                                                                       |
| TAPF    | Combined target assignment and path finding                                                                                                                                        | [explained here](#pr-related-formulations)                                              |
| UML     | Unified Modeling Language: the class and sequence diagram notation                                                                                                                 | —                                                                                       |
| VECS    | Volley EV charging station: a parking spot whose charger connects to the car on the tray parked there                                                                              | [explained here](#bg-bays-vecs-and-vrcs)                                                |
| VRC     | Vertical reciprocating conveyor: the lift that carries AGVs (and their trays) between floors                                                                                       | [explained here](#ly-floors-and-vrcs)                                                   |
| YAML    | YAML Ain't Markup Language: the text format of the site layout file                                                                                                                | [explained here](#ly-what-the-layout-file-is)                                           |

## The garage model in code: `Layout`, `PoseGraph`, `GarageGraph` and `CollisionTable`

[Section 3](#bg-the-physical-garage-and-its-coordinate-system) introduced three views of the garage. This section opens them up: what each class stores, in which container, how each query is answered and what it costs. All four classes are in `common_ros` (`sources/repomix-common-ros.xml`). The `Scheduler` constructor builds them once, in a chain, and nothing changes them afterwards, so every call below is a read of a fixed structure. A plan never pays to build them.

![The static garage model: four classes](figures/75_garage_model_classes.svg)

The four classes with their real members (abridged). `Layout` stores places; `PoseGraph` expands every node into poses and works out each pose's neighbours; `GarageGraph` copies that into a Boost graph that every search runs on; `CollisionTable` holds precomputed conflict sets. Solid arrows are members that point at another object; the dashed arrow is "built from" (the `GarageGraph` constructor reads the `PoseGraph` and keeps no pointer to it). Below them are the value types the four classes are made of: the ROS messages `GaragePoseMsg`, `GarageNodeMsg`, `GeometricPoseMsg`, `SizedPoseMsg`, `ParkingWindowMsg` and `GarageFloorMsg`, and the C++ types `Vrc`, `Transition`, `PoseNeighbor`, `Vertex`/`Edge`, the `CollisionTable` key aliases and `CollisionEntityId`. Each box says which member holds it. Message fields and types are from the `.msg` files ([section 7](#bg-ros-messages-and-services) lists them).

After the constructor ([section 9.1](#bg-constructing-the-scheduler)), only `StorePreferredPayloadHeadingsForRetrieval()` writes to them, storing one retrieval heading per parking node in `motion_graph_`.

### `Layout`: places in sorted vectors and ordered maps

`Layout(file)` reads the YAML with yaml-cpp and keeps everything in plain containers. Nodes live in one vector sorted by id; every other structure either indexes into that vector or is keyed by id.

| Member                                                         | Container                                                                         | What it holds                                                                                                                                                                                                                                                                                                                                                                                                   | Filled from                                      |
|----------------------------------------------------------------|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| `nodes_`                                                       | `std::vector<GarageNodeMsg>`                                                      | Every node, sorted by id (`GarageNode.msg`): `id` (uint32), `x`, `y` (float32, metres, east-north-up), `floor` (uint8), `type` (uint8: `TYPE_PARKING` 1, `WAYPOINT` 2, `LIFT` 3, `BAY` 4, `AGV_CHARGE` 5, `EV_CHARGE` 6, `BLIFT` 7), `headings` (int16\[\], 0–179, ascending), `rotation_allowed`, `faces_reciprocal`, `max_resource_size` and its index, `bay_prioritization`, `insert_floor`, `system_floors` | `nodes:`                                         |
| `node_id_to_index_`                                            | `std::map<uint32_t, uint32_t>`                                                    | Node id → position in `nodes_` (ids need not be contiguous: Pecos skips 12 and ends with 31 and 41)                                                                                                                                                                                                                                                                                                             | after sorting                                    |
| `node_ids_by_type_`                                            | `std::map<type, std::vector<uint32_t>>`                                           | Ids of each node type (parking, waypoint, bay, charger, ...)                                                                                                                                                                                                                                                                                                                                                    | node `type`                                      |
| `graph_`                                                       | `boost::adjacency_list<listS, vecS, undirectedS>`                                 | Node connectivity. Its vertices are **positions in `nodes_`**, not node ids                                                                                                                                                                                                                                                                                                                                     | `edges:`, plus edges between adjacent VRC floors |
| `disallowed_edge_orientations_`                                | `std::map<std::pair<uint32_t, uint32_t>, int16_t>`                                | Per edge (smaller id first), a heading that may not travel along it (it and its reciprocal)                                                                                                                                                                                                                                                                                                                     | edge field                                       |
| `resource_windows_`, `resource_name_to_index_`                 | `std::vector<ParkingWindowMsg>` sorted by area, `std::map<std::string, uint32_t>` | Parking windows. A `"TRAY"` window is always added; it must be the smallest and the windows must nest, or the constructor throws                                                                                                                                                                                                                                                                                | `parking_windows:`                               |
| `bay_prioritization_`                                          | `std::vector<uint16_t>`                                                           | Bay ids, the bay that should most be ready for insert first                                                                                                                                                                                                                                                                                                                                                     | `prioritization_value` through a priority queue  |
| `floors_`, `bay_insert_floors_`, `bay_system_floors_`, `vrcs_` | vector + map, `std::unordered_map`                                                | Floors (a single floor 0 if none), per-bay floors, VRCs and their nodes                                                                                                                                                                                                                                                                                                                                         | floor, bay and VRC fields                        |

| Call                                                             | How it is answered                                                                     | Cost                                                                 |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| `GetNodeById(id) -> std::optional<GarageNodeMsg>`                | `nodes_[node_id_to_index_.at(id)]`, returned **by value**                              | O(\log n) plus a copy of the node message (with its heading vectors) |
| `GetNodes()`, `GetNodeIdsOfType(type)`, `GetBayPrioritization()` | `const&` to the stored vector (a static empty vector for an unknown type)              | O(1), O(\log k)                                                      |
| `GetNeighboringNodes(id)`                                        | `boost::adjacent_vertices` on `graph_`, then copies of the neighbour nodes             | O(\deg) copies                                                       |
| `HasEdge(a, b)`                                                  | `boost::edge` on `graph_`; `a == b` counts as an edge only if the node allows rotation | O(\deg)                                                              |
| `HasGaragePose(pose)`                                            | Scans the node's YAML headings with `IsAngleOrReciprocal`                              | O(\text{headings}); tolerant of reciprocals, unlike `GarageGraph`    |
| `GetGeometricPoseAtPose(pose)`                                   | Node x, y and the heading in radians                                                   | O(\log n)                                                            |
| `GetPoseAtGeometricPose(geo)`                                    | Scans every node (the header says it is inefficient)                                   | O(n)                                                                 |

### `PoseGraph`: from nodes to poses

A YAML node lists headings in 0–179. `PoseGraph` turns each one into two poses, the heading and its reciprocal, because a centred rectangular footprint covers the same area either way:

``` cpp
// common_ros/src/pose_utils.cpp
std::vector<int16_t> GetAllowedHeadings(const GarageNodeMsg& node) {
  std::vector<int16_t> headings;
  for(uint16_t heading : node.headings) {           // YAML headings, 0..179
    headings.emplace_back(volley::Wrap(heading));
    headings.emplace_back(volley::Wrap(heading + 180));
  }
  std::sort(headings.begin(), headings.end());
  return headings;
}
```

So a node with one YAML heading (most Pecos nodes list `[90]`) has two poses, −90 and 90, and `W22`, which lists `[0, 90]`, has four: −90, 0, 90 and 180. Pecos's 28 nodes give 60 poses. `GaragePose.msg` fixes the range: a heading is an `int16` in \[-179, 180\], so `Wrap(90 + 180)` is −90, not 270 (a scheduler test expects `ConstructGaragePose(1, -90)`). Because the list is sorted, −90 comes first at each node.

`PoseGraph` stores the poses in three containers:

- **`poses_`**, a `std::vector<GaragePoseMsg>` ordered by node id, then heading. A pose's **pose index** is its position here.
- **`pose_indices_`**, a `std::map<GaragePoseMsg, int, GaragePoseComparator>` from pose to index (`GetPoseIndex` returns `kInvalidIndex`, −1, when it is missing).
- **`pose_neighbors_`**, a flat `std::vector<int>` with **eight slots per pose**, one per `PoseNeighbor`: `FORWARD`, `RIGHT`, `BACK`, `LEFT`, `ROT_RIGHT`, `ROT_LEFT`, `VRC_UP`, `VRC_DOWN`. Slot *k* of pose *i* is at `8 * i + k` and holds the neighbour's pose index, or −1. (The header comment still says "six"; the VRC slots were added later.)
- `overlapping_sized_poses_`, per pose and resource size, the smallest conflicting sized poses.

The neighbour slots are filled by three rules:

1.  **Translations.** For each `Layout` neighbour of the node, the destination must allow the *same* heading, and the edge must not have a disallowed orientation equal to that heading or its reciprocal. The slot is chosen from the bearing to the neighbour relative to the heading, within 0.1 rad (about 5.7°) of 0°, ±90° or 180°. Any other angle throws "invalid translation connection" when the scheduler starts.
2.  **Rotations**, only where `rotation_allowed` is true: the nearest other heading clockwise and counter-clockwise. With only h and h+180 both slots point at the same pose.
3.  **VRC moves**: nodes of the same VRC on adjacent floors, classified by floor (up or down), not by bearing.

### `GarageGraph` and its `Vertex`

The `GarageGraph` constructor walks `pg.GetPoses()` in order and calls `boost::add_vertex(pose, base_graph_)` for each, recording `pose_to_vertex_[pose] = vert`. A second loop adds one directed edge for every neighbour slot that is not −1. `AddEdge` gives each edge a `Transition`:

- a rotation, with its length in radians;
- a VRC transition, with its length the floor-to-floor height;
- otherwise `LOCOMOTE` or `STRAFE`, depending on whether the motion is mostly along or across the heading, with its length in metres.

Each edge also gets an edge index (the order it was added).

``` cpp
// common_ros/include/common_ros/garage_graph.hpp (abridged)
using BoostPoseGraph = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, GaragePoseMsg,
    boost::property<boost::edge_index_t, std::size_t, Transition>>;

class GarageGraph {
public:
  using Vertex = BoostPoseGraph::vertex_descriptor;   // std::size_t
  using Edge = BoostPoseGraph::edge_descriptor;
  bool HasVertex(const Vertex& vertex) const { return vertex < NumVertices(); }  // "contiguous [0, N)"
  std::optional<Vertex> GetVertexFromPose(const GaragePoseMsg& pose) const;
  std::optional<GaragePoseMsg> GetPoseFromVertex(const Vertex& vertex) const;
  // ...
private:
  LayoutSPtr layout_;
  BoostPoseGraph base_graph_;
  std::unordered_map<GaragePoseMsg, Vertex> pose_to_vertex_;          // hash: node_id, heading
  std::vector<std::pair<Vertex, Vertex>> edge_index_to_vertices_;
  std::unordered_map<uint32_t, int16_t> node_retrieval_heading_;     // StorePreferredPayloadHeadingsForRetrieval()
};
```

#### Reading the `boost::adjacency_list` type

`boost::adjacency_list` is a class template from the Boost Graph Library (BGL) with seven template parameters. `BoostPoseGraph` passes the first five and takes Boost's defaults for the last two. The names in the first column are Boost's own; they are worth learning because Boost's documentation and error messages use them.

| \#  | Parameter (Boost's name) | `BoostPoseGraph` passes                                         | What it decides                                                                                                                                                                                                    |
|-----|--------------------------|-----------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | OutEdgeList              | `boost::vecS`                                                   | The container for each vertex's list of out-edges: a `std::vector`.                                                                                                                                                |
| 2   | VertexList               | `boost::vecS`                                                   | The container for the vertices: a `std::vector`. This choice is what makes `vertex_descriptor`, and so `Vertex`, a `std::size_t` index. With `listS` it would be an opaque pointer instead.                        |
| 3   | Directed                 | `boost::bidirectionalS`                                         | Edges are one-way, and each vertex keeps an in-edge list as well as an out-edge list, so `in_edges` and `in_degree` are cheap. `directedS` would keep only out-edges; `undirectedS` would make every edge two-way. |
| 4   | VertexProperties         | `GaragePoseMsg`                                                 | The data stored *with* each vertex (Boost calls it the bundled vertex property), read with `base_graph_[v]`. It is the vertex's payload, not the vertex.                                                           |
| 5   | EdgeProperties           | `boost::property<boost::edge_index_t, std::size_t, Transition>` | The data stored with each edge: an edge index and a `Transition`. Explained below.                                                                                                                                 |
| 6   | GraphProperties          | not passed: `boost::no_property`                                | Data stored once for the whole graph: none.                                                                                                                                                                        |
| 7   | EdgeList                 | not passed: `boost::listS`                                      | The container for the graph-wide edge list: a `std::list`. In a bidirectional graph each edge, with its properties, is stored here once; a vertex's out- and in-edge lists hold iterators into it.                 |

**Why the vertex is not a `GaragePoseMsg`.** The fourth argument is not the vertex type. Boost calls it *VertexProperties*: the data stored with each vertex. The graph names its vertices with a separate type, `vertex_descriptor`, which Boost derives from parameter 2. With `VertexList = boost::vecS` it is a `std::size_t`, and the valid vertices are exactly the contiguous range \[0, \text{num\\vertices}(g)). So a vertex and its pose are two different things:

``` cpp
using Vertex = BoostPoseGraph::vertex_descriptor;   // std::size_t
Vertex v = 44;                                       // a descriptor: just a number, not a pose
GaragePoseMsg& pose = base_graph_[v];               // the payload stored with it: {node_id: 22, heading: 90}
```

This is how BGL works for every graph, not a Volley choice. It has five practical consequences:

1.  **Algorithms work on descriptors.** `breadth_first_search`, `dijkstra_shortest_paths` and `topological_sort` take descriptors, not application payloads. They keep their working data (distance, predecessor, colour) per vertex, and with `vecS` a descriptor can index a plain vector directly: `dist[v]`. `MakeVertexVectorPropertyMap<T>()` builds such a vector.
2.  **Finding a vertex from its payload needs a separate lookup.** BGL builds no index from a `GaragePoseMsg` to a descriptor. `GarageGraph` therefore keeps `pose_to_vertex_`, a `std::unordered_map` from pose to vertex.
3.  **Descriptors are cheap, but they are stable only while no vertex is removed.** A descriptor is 8 bytes on a 64-bit build. With `vecS`, removing a vertex renumbers every later vertex, which invalidates stored descriptors and any table built from them (`pose_to_vertex_` included). `GarageGraph` never removes a vertex after construction, so its descriptors are safe to keep. `ScheduleEventDag` does remove vertices, and the same renumbering applies there ([section 12.4](#bg-what-is-stored-vertices-edges-and-shared-events)).
4.  **The payload type and the graph shape are independent.** `Dag<T>` uses `adjacency_list<vecS, vecS, bidirectionalS, std::shared_ptr<T>>`. Its vertices are also `std::size_t` descriptors, and the payload is the event pointer ([section 12.3](#bg-the-class-dagbaset-and-scheduleeventdag)).
5.  **Edges have their own identity and their own properties.** An edge is named by an `edge_descriptor` (the `Edge` alias). `GarageGraph` stores two things with each edge: a tagged edge index and a `Transition` payload. Unlike vertex numbers, edge indices are not assigned by BGL; the application has to maintain them, and `AddEdge` does.

A summary of what represents what:

| Concept         | Representation                              | What it is for                                              |
|-----------------|---------------------------------------------|-------------------------------------------------------------|
| Vertex identity | `Vertex` = `std::size_t`                    | Names a vertex within this graph                            |
| Vertex payload  | `GaragePoseMsg`, read with `base_graph_[v]` | The physical pose                                           |
| Edge identity   | `Edge` = `edge_descriptor`                  | Names one directed transition                               |
| Edge payload    | `Transition`, read with `base_graph_[e]`    | The transition's type and length                            |
| Edge index      | `std::size_t`, read with `edge_index_[e]`   | Numbers edges 0 to E-1 so per-edge data can live in vectors |
| Pose lookup     | `pose_to_vertex_`                           | Physical pose → vertex                                      |
| Edge lookup     | `edge_index_to_vertices_`                   | Edge index → its two endpoint vertices                      |

**The edge argument.** The fifth parameter is the data stored with each edge. BGL has two ways to write it, and `BoostPoseGraph` combines them:

- **Bundled properties** (the current Boost documentation's recommended style). An ordinary struct holds the edge's data, and you read it with member access: `g[e].index`, `g[e].transition`. BGL can also build a property map from a pointer to a member, `get(&EdgeProperties::index, g)`, so algorithms read bundled data directly. Bundled properties are not new: they have been in BGL for about two decades.
- **Tagged (interior) properties**, the older style. `boost::property<Tag, T, Base>` stores a value of type `T` under a tag. Here `Tag = boost::edge_index_t` (a tag Boost predefines to mean "edge index"), `T = std::size_t`, and `Base = Transition`. When the last link of the chain is a plain struct rather than another `property<...>`, Boost treats it as the bundled payload. So `get(boost::edge_index, g)` reads the index, and `g[e]` returns the `Transition&`.

In memory each edge carries roughly `{m_value: std::size_t, m_base: Transition}`, and the two parts are read in two different ways:

``` cpp
// common_ros/src/garage_graph.cpp, GarageGraph::AddEdge (abridged)
size_t next_edge_index = boost::num_edges(base_graph_);   // edges are numbered 0, 1, 2, ... as they are added
std::tie(e, added) = boost::add_edge(pose_to_vertex_[src], pose_to_vertex_[dst],
                                     {next_edge_index, transition},    // {m_value, m_base}
                                     base_graph_);
boost::put(edge_index_, e, next_edge_index);              // writes the same index again

// reading an edge e
std::size_t i = edge_index_[e];           // the tagged part: edge_index_ = boost::get(boost::edge_index, base_graph_)
Transition& t = base_graph_[e];          // the bundled part; for edge 44 -> 59: {type: LOCOMOTE, length: 2.857}
```

**Why an edge index at all.** An `edge_descriptor` is a small struct, `{m_source, m_target, m_eproperty}`: the two vertex numbers and a pointer to the edge's stored properties. That is enough to read the edge, but it cannot index a vector. `AddEdge` therefore stores `num_edges()` at insertion time as the edge's index, so edges are numbered 0 to E-1 in the order they were added. `MakeEdgeVectorPropertyMap<T>()` and `edge_index_to_vertices_` use that number to keep per-edge data in plain vectors, the same pattern as for vertices.

**The modern equivalent, and why it is not a drop-in change here.** Written in the bundled style, the same graph is:

``` cpp
// the bundled-property style (not what common_ros does today)
struct TransitionEdge {
  std::size_t index;       // maintained by AddEdge, exactly as now
  Transition transition;
};
using BoostPoseGraph = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS,
                                             GaragePoseMsg, TransitionEdge>;

auto [e, added] = boost::add_edge(u, v, TransitionEdge{.index = next_edge_index, .transition = t}, g);
std::size_t i = g[e].index;                              // or get(&TransitionEdge::index, g)[e]
const Transition& tr = g[e].transition;
auto index_map = get(&TransitionEdge::index, g);         // a property map from a member pointer
boost::vector_property_map<double, decltype(index_map)> per_edge(boost::num_edges(g), index_map);
```

The two styles look up the index through different mechanisms: `get(boost::edge_index, g)` only exists with the tagged property. `GarageGraph` exposes the tagged form in its public API: `EdgeVectorPropertyMap<T>` is defined as a `vector_property_map` over `property_map<BoostPoseGraph, boost::edge_index_t>::type`, and `MakeEdgeVectorPropertyMap<T>()` returns it. Switching to the bundled struct therefore changes a public `common_ros` type, and every caller outside the snapshots (the motion planner, for example) has to be checked. It also changes `base_graph_[e]` from a `Transition&` to the struct, so readers would write `base_graph_[e].transition`. It is a sensible cleanup, but one for `common_ros`; the naming catalogue lists it ([section 15.6.1](#nm-garagegraph)).

![Inside BoostPoseGraph: template parameters and storage](figures/81_boost_pose_graph.svg)

Inside `BoostPoseGraph`. Top: the seven template parameters, with Boost's names and what `BoostPoseGraph` passes; 6 and 7 are defaults. Middle: what Boost stores for Vertex 44 (`{node_id: 22, heading: 90}`). `m_vertices[44]` holds the pose and two lists of edge iterators. The edge 44 → 59 (to `{node_id: 41, heading: 90}`) is one node in the graph-wide `m_edges` list, holding the edge index and the `Transition`. Vertex 44's out-edge list and Vertex 59's in-edge list both point at that node. Bottom: the public calls that read each part. Boost member names are simplified.

![What a GarageGraph Vertex is](figures/76_garage_graph_vertex.svg)

What a `Vertex` is, on Pecos around W22. Top: the type definitions and the poses around W22, each ring one vertex, labelled with its `Vertex` value (`v44` = Vertex 44). Bottom, left to right: `pose_to_vertex_` turns `{node_id: 22, heading: 90}` into 44; entry 44 of the Boost vertex vector holds the pose and the out- and in-edge lists; each out-edge carries a `Transition` (how Boost stores these is in [Figure 12](#bg-fig-81_boost_pose_graph)). Moves along a row (W22 to W41, W22 to P23) are `LOCOMOTE`, because heading 90 faces −x; moves between rows are `STRAFE`; turns in place are `ROTATION`. How the poses of neighbouring nodes are connected, rotations included, is built up step by step in [section](#ly-vertices-and-edges).

**What a vertex actually is:**

- **A number.** With `vecS` as the vertex container, a Boost `vertex_descriptor` is a `std::size_t` index into the graph's internal vector of vertices. A `Vertex` is valid when it is less than `NumVertices()`; that is all `HasVertex` checks.
- **What is stored at that index:** one entry of Boost's vertex vector (`m_vertices[v]`, [Figure 12](#bg-fig-81_boost_pose_graph)) with three members:
  - the bundled `GaragePoseMsg`, read with `base_graph_[v]` (template parameter 4);
  - the out-edge list, a `std::vector` (parameter 1);
  - the in-edge list, present because the graph is `bidirectionalS` (parameter 3).

  The edge lists hold the target vertex and an iterator into the graph-wide edge list; each edge's index and `Transition` are stored there once, not in the vertex. Nothing else is stored: there is no node type, no position and no occupancy at a vertex. Node facts come from the `Layout` (`GarageNodeFromVertex` looks the node up and copies it), and occupancy comes from `DiscreteGarageState`.
- **The numbering is the `PoseGraph` order:** vertex *i* is pose index *i*, that is, node id ascending, then heading ascending. On Pecos, W22's poses `{node_id: 22, heading: -90}`, `{node_id: 22, heading: 0}`, `{node_id: 22, heading: 90}` and `{node_id: 22, heading: 180}` are vertices 42, 43, 44 and 45.
- **Numbers are stable.** Nothing adds or removes vertices after construction, so a `Vertex` stays valid for the scheduler's lifetime. Compare `ScheduleEventDag`, where `Remove` renumbers later vertices ([section 12.4](#bg-what-is-stored-vertices-edges-and-shared-events)). A `Vertex` means nothing outside one layout: never store one, or compare one across layouts or builds.
- **Per-vertex data lives outside the graph.** `MakeVertexVectorPropertyMap<T>()` returns a vector indexed by `Vertex`, and `MakeEdgeVectorPropertyMap<T>()` a vector indexed by edge index. That is the pattern for anything a search needs per vertex or per edge. `GraphFilterProperties` (in `motion_planner`) uses exactly this pattern: two `vector_property_map<bool>`s, one per vertex and one per edge, and `IsEnabled(vertex)` / `IsEnabled(edge)` are unchecked lookups into them (“These functions offer no bounds checking”).

| Call                                               | Data structure                                                                   | Cost                      | When the answer does not exist         |
|----------------------------------------------------|----------------------------------------------------------------------------------|---------------------------|----------------------------------------|
| `GetVertexFromPose(pose)`                          | `pose_to_vertex_` (`std::unordered_map`, hash of `node_id` and `heading`)        | O(1) average              | `std::nullopt`                         |
| `GetPoseFromVertex(v)`                             | `base_graph_[v]`                                                                 | O(1)                      | `std::nullopt` if `v >= NumVertices()` |
| `GarageNodeFromVertex(v)`                          | `base_graph_[v].node_id`, then `layout_->GetNodeById`                            | O(\log n) plus a copy     | `std::nullopt`                         |
| `GetVerticesAtGarageNode(node)`                    | `GetAllowedHeadings` plus `pose_to_vertex_`                                      | O(\text{headings})        | empty vector                           |
| `GetOutEdges(v)`, `GetInEdges(v)`                  | the vertex's edge vectors (iterator pair)                                        | O(1); at most 8 out-edges | **throws** `std::invalid_argument`     |
| `EdgeFromPoses(a, b)`, `GetTransition(e)`          | two hash lookups and `boost::edge` (a scan of *a*'s out-edges); `base_graph_[e]` | O(1)                      | `std::nullopt`                         |
| `SetRetrievalHeading`, `GetRetrievalHeading(node)` | `node_retrieval_heading_`                                                        | O(1)                      | `std::nullopt` if not cached           |

#### When `GetVertexFromPose` returns nothing

A pose is a vertex of `motion_graph_` only if the node allows that heading, and the lookup is an **exact** hash match on `(node_id, heading)`: nothing normalises the heading first. An empty optional therefore means one of three things:

- the node id is not in the layout;
- the heading is not one of the node's YAML headings or their reciprocals;
- the heading is outside \[-179, 180\], so it does not match the stored value (for example 270 instead of the stored −90).

Any of these produces the "does not exist in garage graph" errors.

Reciprocals deserve care. `PoseGraph` always adds h and h+180 together, so `(n, h)` and `(n, h+180)` are either both vertices or both missing. When `AssignTrays` checks a requested destination, `ResolveDestinationHeading` retries the reverse heading after an empty lookup (`tray_assignment.cpp:487`–`:507`). That retry cannot find a vertex the first lookup missed, unless the first heading was outside \[-179, 180\] (say 270) and the reverse comes back wrapped (90). The scheduler's `ReverseHeading` (`utils.cpp:58`) wraps `common`'s `ReciprocalAngle`, which is not in the snapshots. Before PR \#1018 a destination found only through the retry threw; it now goes to the reverse pose. Reciprocals matter for **footprints and turns**, not for vertex existence:

- A tray or AGV is a centred rectangle, so h and h+180 cover the same floor.
- `IsSameOrOppositeHeading` (`utils.cpp:68`) compares headings up to reversal; AGV assignment uses it to keep an AGV's heading at a pickup when it already lines up with the tray (`ChoosePickupHeading`, `agv_assignment.cpp:54`). `ExpandAgvMoveJob` used `common`'s `IsAngleOrReciprocal` to skip a rotation; PR \#1018 removed that branch, which no caller reached.
- `ExpandAgvMoveJob` converts a destination into tray coordinates when the tray sits reversed on the AGV (`ResolveCarriedTrayDestination`, `job_expansion.cpp:157`, called at `:122`–`:124`).
- `CollisionTable` still stores h and h+180 as separate keys (a TODO in `BuildTable`).

### `CollisionTable`: precomputed conflict sets

The table answers one question: if something of [footprint type](#bg-term-footprint-type) *F* stands at location *a*, may something of footprint type *Q* be at location *b*? A location is a pose or an edge (a move), and a footprint type is a `CollisionEntityId`:

- `BAY_ODP`, `TRAY_LEGS`, `TRAY` and `AGV`;
- one `PAYLOAD` id per parking window.

Nothing is computed geometrically during planning. Every answer was precomputed into four nested hash maps:

![CollisionTable storage](figures/77_collision_table_storage.svg)

The `ResMap` type, one lookup through `ppmap_`, and how the table is filled.

- Building it compares every vertex with every vertex and edge, for every pair of footprint types. Each test checks bounding circles first, then polygons; an edge's polygon is the convex hull of the footprints at both ends.
- Every conflict is stored in both directions.
- The result is cached as JSON under `~/.cache/volley/`, keyed by the layout's name and md5.

| Overload                                                          | Reads                             | Returns                                                                            |
|-------------------------------------------------------------------|-----------------------------------|------------------------------------------------------------------------------------|
| `Query(fixed_id, queried_id, pose)`                               | `ppmap_`, `pemap_`                | `std::tuple<PoseSet, EdgeSet>`: every pose and edge the queried entity may not use |
| `Query(fixed_id, queried_id, edge)`                               | `epmap_`, `eemap_`                | the same, for an entity moving along an edge                                       |
| `Query(fixed_id, queried_id, location, queried_location) -> bool` | one of the four maps, then `find` | `true` if they conflict (four overloads: pose or edge on each side)                |

Things to know when you use it:

- **A missing key means "no conflict".** The table cannot tell an impossible query (an id or pose that does not exist) from a pair that does not overlap; two TODOs say so.
- **Every query copies a set.** Even the `bool` overloads copy the whole `unordered_set` out of the map before calling `find`, so a check inside a hot loop is not free.
- **The cache can go stale.** The cache file name contains only the layout's name and md5. Editing the YAML forces a rebuild, but changing footprint code does not; delete `~/.cache/volley/<layout>_collision_table_<md5>.json` after changing collision geometry.
- **Who calls it.**
  - `volley::BuildStaticObstacleFilter` uses it to disable vertices around occupants.
  - `GarageOccupancyChecker::AddOccupant` spreads each occupant to every location it blocks, using the one-location overloads.
  - `AssignTrays` and `FindAssignedAgvsBlockingPickup` call the `bool` overload directly.

### Which structure answers which question

Each of the structures described above answers a different kind of question about the garage. The table lists common questions, the call that answers each one, the member that holds the answer and the cost of asking, so that a reader can tell at a glance which structure a given piece of code depends on.

| Question                                                         | Ask                                                                                                                                                                   | Answered by                                                                                                                                | Cost                  |
|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
| What is node 22: type, position, headings?                       | `layout_->GetNodeById(22)`                                                                                                                                            | `Layout::nodes_` via `node_id_to_index_`                                                                                                   | O(\log n) plus a copy |
| Is `{node_id: 22, heading: -90}` a pose, and which vertex is it? | `motion_graph_.GetVertexFromPose({node_id: 22, heading: -90})` → 42 (`{node_id: 22, heading: 270}` → empty)                                                           | `GarageGraph::pose_to_vertex_`                                                                                                             | O(1)                  |
| Where can I go from vertex 44, and how long is each move?        | `motion_graph_.GetOutEdges(44)`, `motion_graph_.GetTransition(e)`                                                                                                     | Boost out-edge vector, edge property                                                                                                       | O(1) per edge         |
| Which path from A to B is quickest?                              | `FindPosePath(motion_graph_, a, b, cost_model_, filters)`                                                                                                             | `FindPosePath` in `motion_planner`: Dijkstra over `motion_graph_`, each edge weighted by its trapezoid time ([section 7.5](#mp-pose-path)) | a graph search        |
| Would a tray at *a* block an AGV at *b*?                         | `collision_table_.Query(TRAY_LEGS, AGV, a, b)`: an empty AGV drives under a parked tray, so only the tray's legs can block it (`BuildStaticObstacleFilter` does this) | `CollisionTable::ppmap_`                                                                                                                   | O(1) plus a set copy  |
| Which vertices and edges may tray 17 not use right now?          | `BuildStaticObstacleFilter(...)`, then `filters.IsEnabled(v)` or `IsEnabled(e)`                                                                                       | `GraphFilterProperties` in `motion_planner`: two bool vectors, built from `collision_table_` and `working_state`                           | built per call        |
| Where is tray 17 now?                                            | `working_state.GetTray(17)`                                                                                                                                           | `DiscreteGarageState::trays_` (`std::map`)                                                                                                 | O(\log n)             |

## ROS messages and services

The `interfaces` package defines the wire contracts under `msg/` and `srv/`. `rosidl_generate_interfaces` turns them into C++ structs. The scheduler names them by their full type (`interfaces::msg::PlanRequest`, `interfaces::srv::Plan`) and each file includes the message headers it uses; PR \#1018 deleted `scheduler_msgs.hpp`, which gave each a short alias ending in `Msg`. `common_ros` and `motion_planner` keep such aliases (`GaragePoseMsg = interfaces::msg::GaragePose`, …), so when you see `...Msg` in those packages you are looking at a generated ROS struct. When one message appears inside another, the relationship is **composition**, not inheritance.

Read the interfaces from the outside in: `srv/Plan.srv`, then `PlanRequest` and `PlanResponse`, then `DiscreteGarageState`, `Schedule`, `ActionNode` and `SchedulerJob`, and only then the utility types. The subsections below follow that order: an overview, then the request field by field, the garage snapshot, the job message, the schedule and its commands, the response, and the small shared types. Every field table says whether the scheduler actually reads or writes the field, because several are only Dispatch's bookkeeping. The full `.msg` text of any type is one hover away: type names in code blocks open a popup with the definition.

### The `Plan` call at a glance

The `Plan` service is the single boundary between the scheduler and the rest of the system. The table lists the interfaces involved, from `srv/Plan.srv` inward, with what each contains and why it matters; the subsections that follow examine each of them in turn.

| Interface                     | What it contains                                                                       | Why it matters                                  |
|-------------------------------|----------------------------------------------------------------------------------------|-------------------------------------------------|
| `srv/Plan.srv`                | One `PlanRequest` and one `PlanResponse` (`request_data` / `response_data`)            | The service boundary `SchedulerRos` exposes     |
| `msg/PlanRequest.msg`         | Request id, current `DiscreteGarageState`, immutable `base_schedule`, three job arrays | What the world looks like now, and what to plan |
| `msg/PlanResponse.msg`        | Success flag, message, id, output `Schedule`, `ScheduledJobData[]`                     | The schedule plus per-job bookkeeping           |
| `msg/SchedulerJob.msg`        | Type, state, ids for AGV / bay / tray / payload, optional destination                  | User or dispatcher intent                       |
| `msg/DiscreteGarageState.msg` | Arrays of AGVs, bays, VECS (`vexen`), trays, payloads, VRCs, disabled nodes, hash      | The snapshot at the start of the call           |
| `msg/GaragePose.msg`          | Node id and discrete heading                                                           | The pose type used almost everywhere            |
| `msg/Schedule.msg`            | A topologically ordered array of `ActionNode`s                                         | What Dispatch executes                          |
| `msg/ActionNode.msg`          | Type, parent indices, duration, status, one command payload per machine type           | The final executable unit                       |

![ROS message relationships](figures/13_uml_ros_messages.svg)

As-built ROS service and message composition. A **filled diamond** means “contains as a field or array element”; each connector leaves the owning message at the field that holds the value. Blue boxes are the **request / intent** side, violet the **garage-state snapshot**, green the **response / schedule** side, amber the **command payloads**, and teal the **`GaragePose` utility type** (teal type names show where else it is used).

Three conventions hold in every message:

- **Links are values, not pointers.** `ActionNode.parents` and `ScheduledJobData.node_indices` are indices into `Schedule.nodes`; records in `DiscreteGarageState` point at each other by id; `bay_arrival_node_guid` names a node by its guid.
- **Optional fields are flattened.** `SchedulerJob` and `ActionNode` carry the fields of every variant; `type` says which ones mean something.
- **Ids have different widths.** AGV, tray, bay and VECS ids are `uint16` in state and job messages but `uint32` in `ActionNode` and `GarageNode`. A heading is an `int16` in degrees in \[-179, 180\], so the reciprocal of 90 is −90.

### `PlanRequest`: one moment in a running schedule

A request is easiest to read against the schedule Dispatch is already executing. The interface is designed so that Dispatch does not have to stop the fleet to plan: it sends what is still running, and asks the scheduler to plan new jobs around it. Every field of `PlanRequest` describes one piece of that picture. How Dispatch (the `central` package) fills each field is read from `Dispatch::GetPlannerServiceRequest`; the Dispatch tab gives the wider context ([section 3](#ds-what-goes-into-a-planrequest)).

![A PlanRequest on the time line](figures/118_plan_request_timeline.svg)

**A `PlanRequest` on the time line.** Step through it: the schedule Dispatch is running, how it fills `base_state`, `base_schedule` and the three job lists, what it expects back, and why, with today's settings, a call is only made once no job is active. The scenario is the one of the reservation figure in [section 10](#bg-the-base-schedule-reserved-assets-and-keep-out-filters).

| Field           | Type                  | Meaning                                                                                                                                                                                                                                                                                                                                                                   | How `Plan()` uses it                                                                                                                                                                                                    |
|-----------------|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `id`            | `Guid`                | Identifies this call                                                                                                                                                                                                                                                                                                                                                      | Copied into `PlanResponse.id` so Dispatch can match the reply; also names debug output                                                                                                                                  |
| `base_state`    | `DiscreteGarageState` | The garage **now**, as a discrete snapshot: where every AGV, tray and car is, each bay's and VECS's state, and what is out of service. Dispatch sends `GetLatest()`, its own copy of the garage advanced by completion events, not the state at the end of its schedule                                                                                                   | `ValidateBaseState` turns it into `initial_state`; an invalid snapshot is the only case that returns `success = false`                                                                                                  |
| `base_schedule` | `Schedule`            | “The immutable portion of the current schedule”; the scheduler “is to assume that all of these actions will be completed”. Dispatch fills it with **every action of its schedule that is not completed**, parents renumbered. A split that would keep back actions beyond a 30 s command horizon (`SplitSchedule`, `outside_split`) exists, but its call is commented out | Read once, by the reservation loop: every AGV, bay and VECS it uses, and every AGV command's source and destination node, become unavailable ([section 10](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)) |
| `planned_jobs`  | `SchedulerJob[]`      | By the message comment, jobs that `base_schedule` finishes. **Never filled** by Dispatch: always empty                                                                                                                                                                                                                                                                    | Not read                                                                                                                                                                                                                |
| `active_jobs`   | `SchedulerJob[]`      | By the message comment, jobs with actions in `base_schedule` that it does not finish. Dispatch sends its whole `jobs_active_` list: every job whose actions are still in its schedule, which are exactly the jobs of the `base_schedule` nodes                                                                                                                            | Not read; the scheduler works from `base_schedule` instead                                                                                                                                                              |
| `pending_jobs`  | `SchedulerJob[]`      | Queued jobs that pass `ShouldPendingJobBePlanned`, in queue order, capped by Dispatch's current request strategy                                                                                                                                                                                                                                                          | Planned one by one, in order; each gets an entry in `PlanResponse.scheduled_jobs`                                                                                                                                       |

How the fields relate to each other:

- **`base_schedule` and `active_jobs` describe the same work.** One lists the remaining actions, the other the jobs they belong to (every `ActionNode.job_id` in `base_schedule` is the `guid` of an active job). `planned_jobs` would split that list by whether `base_schedule` finishes the job, but Dispatch never fills it. `pending_jobs` are disjoint from both: jobs with no actions yet.
- **The snapshot and the running schedule disagree on purpose.** `base_state` shows AGV-2 at P15, but `base_schedule` will take it to P23. The scheduler does not replay `base_schedule` onto the snapshot; it reserves what the schedule touches instead ([section 11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)). Dispatch chose this deliberately: a comment in `GetPlannerServiceRequest` says that sending the end state instead would make the planner assume everything is there at time 0, and would lose the dependencies between the running part and the new part.
- **Dispatch expects the base schedule back.** `PlanClientCallback` rejects a response unless it contains every `base_schedule` node, field for field, and it rebuilds its schedule from the response alone. The intended contract is therefore “return the base schedule plus the new actions, with edges from old to new”. Today's scheduler returns only the new actions, with no edges into `base_schedule`.
- **In practice both lists are empty.** `enable_overlapping_planning_` is `false` and no parameter sets it, so `ShouldCallPlanner` makes no call while any job is active. Every call made today has an empty `base_schedule` and empty `active_jobs`, so the mismatch above never shows and the reservation loop never fires. Turning overlapping planning on would need the scheduler to return the base nodes (and ideally edges into them) first.

### `base_state`: the garage snapshot

`DiscreteGarageState` lists every asset in flat arrays. Records point at each other by id, and at the layout by node id. The scheduler does not use the message directly: `ValidateBaseState` rebuilds a `DiscreteGarageState` object from it by replaying one existence event per record through `OnEvent` ([section 12.3](#bg-what-onevent-is)), then checks it against the layout.

![base_state records and links](figures/119_base_state_records.svg)

**`base_state`, record by record.** Step through `DiscreteGarageState::Set`: AGVs (with `tray_id` zeroed), bays, VECS and VRCs, trays (re-attached to their AGV through `tray.agv_id`), payloads (put on their tray through `payload.tray_id`), disabled nodes, then the layout checks of `ValidateBaseState`. The arrows are the two id links `Set` follows. T24's record is omitted.

What each record means, and which fields the scheduler reads:

| Record                 | Field                                                      | Meaning                                                                                                                                           | Used by the scheduler                                                                                                                                                                                                        |
|------------------------|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DiscreteGarageState`  | `is_faulted`                                               | The garage is in a fault state                                                                                                                    | Replayed as a `FaultStateChanged` event; no planning check reads it                                                                                                                                                          |
|                        | `agvs`, `bays`, `vexen`, `trays`, `payloads`, `vrcs`       | One record per asset (`vexen` is the plural of VECS)                                                                                              | Become the ordered maps `agvs_`, `bays_`, … keyed by id                                                                                                                                                                      |
|                        | `disabled_nodes`                                           | Node ids closed to all traffic                                                                                                                    | Become `disabled_nodes_`; the reservation loop adds to the same set                                                                                                                                                          |
|                        | `hash`, `header`                                           | The sender's hash of the state; ROS header                                                                                                        | Not checked by `Set` or `ValidateBaseState`                                                                                                                                                                                  |
| `DiscreteAgvState`     | `id`, `pose`                                               | AGV id; node and heading (`GaragePose`)                                                                                                           | Everywhere; the pose must exist in the layout                                                                                                                                                                                |
|                        | `lift`                                                     | Lift raised                                                                                                                                       | Lift and carry rules; a tray can only be attached to a lifted AGV                                                                                                                                                            |
|                        | `tray_id`                                                  | Tray carried, 0 if none                                                                                                                           | Ignored on load and rebuilt from `tray.agv_id`                                                                                                                                                                               |
|                        | `disabled`                                                 | Out of service (operator or fault)                                                                                                                | Never assigned or moved; also set by the reservation loop                                                                                                                                                                    |
|                        | `state`                                                    | AGV state code                                                                                                                                    | Not read by planning                                                                                                                                                                                                         |
| `DiscreteTrayState`    | `id`, `pose`                                               | Tray id; where it stands (or rides)                                                                                                               | Everywhere; the pose must exist in the layout                                                                                                                                                                                |
|                        | `agv_id`                                                   | AGV carrying it, 0 if parked                                                                                                                      | **Authoritative**: attaches the tray to that AGV, which must be lifted, on the same node and parallel                                                                                                                        |
|                        | `payload_id`                                               | Car on it, empty Guid if none                                                                                                                     | Ignored on load and rebuilt from `payload.tray_id`                                                                                                                                                                           |
|                        | `disabled`                                                 | Out of service                                                                                                                                    | Not a candidate tray; its node becomes a static obstacle                                                                                                                                                                     |
| `DiscretePayloadState` | `payload.id`                                               | The car's Guid                                                                                                                                    | What RETRIEVE and CHARGE_PAYLOAD jobs name                                                                                                                                                                                   |
|                        | `payload.length_m`, `width_m`, `height_m`                  | Car size                                                                                                                                          | Picks the smallest resource window that encloses the car; that window is its footprint (Layout file tab, [section 6](#ly-parking-windows-and-the-buffer)). A car that fits no window rejects the request. `mass` is not read |
|                        | `payload.ev_charge_requested`                              | The customer asked for charging                                                                                                                   | When a bay holding such a car is cleared, the car is sent to a VECS (`ExpandChargePayloadJob`)                                                                                                                               |
|                        | `tray_id`, `reciprocal_to_tray`, `charging`                | Tray it is on; car faces the other way on the tray; car is charging                                                                               | `tray_id` is authoritative; `reciprocal_to_tray` decides the heading a retrieve needs at the bay; `charging` is not read (the VECS state is used instead)                                                                    |
| `DiscreteBayState`     | `id`                                                       | Bay id, which is also its node id                                                                                                                 | Position and heading come from the layout node                                                                                                                                                                               |
|                        | `state`, `disabled`                                        | A `BayReport.STATE_*` value (`READY_TO_RETRIEVE`, `READY_TO_INSERT`, `PROCESSING_*`, `TRANSITIONING_TO_*`, `VEHICLE_INSERTED`, …); out of service | `ClassifyBays` sorts bays by state; a bay that is not `READY_TO_RETRIEVE` blocks traffic with its overdrive-plate (`BAY_ODP`) area                                                                                           |
| `DiscreteVecsState`    | `id`, `state`, `disabled`                                  | VECS id (its parking node id); a `VecsReport` state (`READY_TO_CHARGE`, `CHARGING`, …); out of service                                            | A car on a charging VECS gets a stop-charging event before it moves                                                                                                                                                          |
| `DiscreteVrcState`     | `id`, `state`, `gates`, `current_floor`, `requested_floor` | Vertical lift: idle or moving, door reports, the floor it is on and the floor it is going to                                                      | Only by the action-graph VRC code (Layout file tab, [section 8](#ly-vrc-support-status))                                                                                                                                     |

Two rules make the snapshot easier to trust. **Each link has one owner:** `tray.agv_id` and `payload.tray_id` are read, their mirrors `agv.tray_id` and `tray.payload_id` are rebuilt, so a message whose mirrors disagree is loaded from the owners without complaint. **Any inconsistency rejects the call:** a tray on an AGV that is not lifted, two cars on one tray, a car that fits no window or a pose missing from the layout makes `ValidateBaseState` fail, and `Plan()` returns `success = false` with no job results.

### `SchedulerJob`: what to do, and what happened

A `SchedulerJob` is one request for work. The same message goes out in `pending_jobs` and comes back, with its status filled in, inside `PlanResponse.scheduled_jobs`. Its fields fall into groups that are written by different sides:

![SchedulerJob field groups](figures/120_scheduler_job_round_trip.svg)

**Who writes which `SchedulerJob` field.** Dispatch writes the identity and the arguments and sends the job as `STATE_UNPLANNED`. The scheduler returns it as `STATE_EXECUTING` or `STATE_ERROR`, with a note and `retain_job` on failure; `SchedulerRos` stamps `time_planned`. Three fields are never written by the scheduler.

The argument fields are shared by all job types; each type reads only some of them. `Plan()`'s job loop hands each pending job to `ExpandJob` (`scheduler.cpp:251`), and this is its whole dispatch table:

| `type`                                           | Reads                                        | Expanded by                                        | What it asks for                                                                                                       |
|--------------------------------------------------|----------------------------------------------|----------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `TYPE_MOVE_AGV`                                  | `agv_id`, `destination`                      | `ExpandAgvMoveJob`                                 | Drive an AGV to a pose. `allow_reciprocal` is not read (the call passed `false` until PR \#1018 removed the parameter) |
| `TYPE_MOVE_TRAY`, `TYPE_REPARK_TRAY`             | `tray_id`, `destination`, `allow_reciprocal` | `ExpandReparkTrayJob`                              | Move a tray to a pose, or to a sensible parking spot                                                                   |
| `TYPE_RETRIEVE`                                  | `payload_id`                                 | `ExpandRetrieveJob`                                | Bring a car to a bay and hand it over; may fail with `retain_job = true`                                               |
| `TYPE_INSERT`                                    | `bay_id`                                     | `ExpandInsertJob`                                  | Take the car just driven into a bay and park it                                                                        |
| `TYPE_READY_FOR_INSERT`                          | `bay_id`                                     | `ExpandReadyForInsertJob`                          | Prepare a bay to receive a car (empty tray in, door state)                                                             |
| `TYPE_READY_FOR_RETRIEVE`                        | `bay_id`                                     | `ExpandReadyForRetrieveJob`                        | Clear a bay so a car can be delivered to it                                                                            |
| `TYPE_TRANSITION_BAY_TO_INSERT` / `_TO_RETRIEVE` | `bay_id`                                     | `ExpandBayTransitionJob`                           | Switch a bay's mode                                                                                                    |
| `TYPE_CHARGE_AGV`                                | `agv_id`                                     | `ExpandAgvChargeJob`                               | Send an AGV to the cheapest free charger                                                                               |
| `TYPE_CHARGE_PAYLOAD`                            | `payload_id`                                 | `ExpandChargePayloadJob`                           | Move a car onto a VECS and start charging                                                                              |
| `TYPE_CLEAN_GARAGE`, `TYPE_REBALANCE_GARAGE`     | none                                         | `ExpandCleanGarageJob`, `ExpandRebalanceGarageJob` | Garage-wide housekeeping: put trays and bays into a better state                                                       |
| anything else                                    | —                                            | `Fail`, reported by `MakeFailedJob`                | “Unknown job type”                                                                                                     |

The Task planning tab describes each method (for example [section 2.8](#bg-type_retrieve--planretrievejob)). The order of `pending_jobs` matters: each job is planned on top of the events of the jobs before it, so an earlier job can take the AGV, tray or bay a later job wanted.

### `Schedule` and `ActionNode`: commands in, commands out

A `Schedule` is a DAG of commands stored as an array: `nodes` is in topological order, and each node's `parents` are indices of earlier nodes. The same message type is used twice, with different roles: `PlanRequest.base_schedule` (read by the reservation loop) and `PlanResponse.schedule` (built from CHUGG's motions, Action graph tab).

![ActionNode and AgvCommand](figures/121_action_node_anatomy.svg)

**An `ActionNode` array and the four kinds of `AgvCommand`.** Left: the end of a retrieve as six nodes; `PROCESS_RETRIEVE` waits for the lower (index 3) and for the bay transition (index 0). Right: an AGV command always carries a full source and destination `AgvGoal` (pose and lift); the AGV accepts it only if exactly one thing changes (translate, rotate, lift) or nothing does (center).

| `ActionNode` field         | Meaning                                                                                                                                                            | Read in `base_schedule`                                  | Written in the response                                                    |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|----------------------------------------------------------------------------|
| `guid`                     | The action's identity                                                                                                                                              | no                                                       | fresh on every call (`GenerateNextActionGuid`)                             |
| `job_id`                   | Guid of the job the action serves                                                                                                                                  | no                                                       | the job's `guid`; how `node_indices` and `bay_arrival_node_guid` are found |
| `type`                     | Which machine: `TYPE_AGV_COMMAND`, `_BAY_`, `_VECS_`, `_VRC_`                                                                                                      | yes                                                      | from the motion's discrete change                                          |
| `parents`                  | Indices of nodes that must finish (or be queued, on the same AGV) first                                                                                            | no                                                       | from the action DAG                                                        |
| `duration`                 | Planned seconds; some actions have no end                                                                                                                          | no                                                       | the CHUGG motion's duration                                                |
| `agv_id` + `agv_command`   | The AGV and its `src` / `dst` goals                                                                                                                                | `agv_id`, `src.pose.node_id`, `dst.pose.node_id`         | for AGV moves and lifts; `agv_command.id` is left empty                    |
| `bay_id` + `bay_command`   | The bay and `TRANSITION_TO_INSERT` / `PROCESS_RETRIEVE` / `TRANSITION_TO_RETRIEVE` / `MOVE_LIFT_TO_FLOOR`                                                          | `bay_id`                                                 | for bay transitions                                                        |
| `vecs_id` + `vecs_command` | The VECS and `START_CHARGING` / `STOP_CHARGING`                                                                                                                    | `vecs_id`                                                | from the VECS state change                                                 |
| `vrc_id` + `vrc_command`   | The VRC and `MOVE` to `requested_floor`                                                                                                                            | no ([section 10.1](#bg-what-the-reservation-loop-marks)) | VRC trips added by the action-graph code                                   |
| `status`, `outside_split`  | Dispatch's progress tracking: not received / received / completed; `outside_split` would mark actions held back during a plan call, but the split is never applied | no                                                       | left at defaults                                                           |

Only the fields of the node's `type` are meaningful; the other id/command pairs keep default values. This is why the reservation loop switches on `type` before reading `agv_id`, `bay_id` or `vecs_id`.

### `PlanResponse` and `ScheduledJobData`: what comes back

`PlanResponse` has five fields. `id` echoes the request. `success` is `false` only when `base_state` is invalid; every other failure, including a failed motion plan, returns `success = true` with every pending job marked `STATE_ERROR`, so Dispatch must read the per-job results. `message` carries the reason for a call-wide failure. `schedule` holds the new actions (the previous subsection), and `scheduled_jobs` one entry per pending job: first the jobs that failed expanding, then the planned jobs, each group in request order (before PR \#1018 the planned jobs came back in hash-map order).

`interfaces::msg::ScheduledJobData` is the ROS message for one job's result (`ScheduledJobDataMsg` in the code before PR \#1018). The response carries one per pending job, in `PlanResponse.scheduled_jobs`. (How `Plan()` builds these entries, and the internal `ctx->scheduled_jobs` list it builds them from, is in [section 13](#bg-schedulecontext-in-depth-job-indices-and-bookkeeping-maps).) Each entry answers three questions for Dispatch: **which job is this and how did it go** (`job`), **which actions in the schedule belong to it** (`node_indices`), and, for a retrieve, **which action is the car arriving at the bay** (`bay_id`, `bay_arrival_node_guid`).

![ScheduledJobData UML](figures/73_scheduled_job_data_uml.svg)

`ScheduledJobData` and the messages around it. `PlanResponse` contains the `Schedule` (whose `nodes` are the `ActionNode`s in topological order) and one `ScheduledJobData` per pending job. Each entry **contains** a full copy of the request's `SchedulerJob` and **refers to** the schedule by value: `node_indices` are positions in `Schedule.nodes`, and `bay_arrival_node_guid` is the `guid` of one of those nodes. Nothing is a pointer; every link is an index or a guid.

| Field                         | Type              | Written by                                                                                  | When                                       | Meaning                                                                                                                                                                                                                        |
|-------------------------------|-------------------|---------------------------------------------------------------------------------------------|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `job`                         | `SchedulerJob`    | `AddScheduledJob` (planned) or `MakeFailedJob` (failed) copy `request_data.pending_jobs[i]` | during the job loop                        | the request's job, unchanged, plus the status fields below                                                                                                                                                                     |
| `job.state`, `job.state_name` | `uint8`, `string` | `MakeFailedJob`; the final loop in `Plan()`                                                 | on failure; after motion planning succeeds | in: `STATE_UNPLANNED`; out: `STATE_ERROR` or `STATE_EXECUTING`                                                                                                                                                                 |
| `job.note`                    | `string`          | `MakeFailedJob`                                                                             | on failure                                 | the failure message                                                                                                                                                                                                            |
| `job.retain_job`              | `bool`            | `MakeFailedJob`                                                                             | on failure                                 | asks Dispatch to keep the job and retry it later (default `false`)                                                                                                                                                             |
| `job.time_planned`            | `Time`            | `SchedulerRos`, after `Plan()` returns                                                      | once per response                          | the same timestamp on every entry, failed or not                                                                                                                                                                               |
| `node_indices`                | `uint32[]`        | `WriteJobActionIndices`                                                                     | after motion planning                      | positions in `response.schedule.nodes` of this job's actions, ascending; empty for a failed job. The `.msg` notes that the job's final actions would be enough (their ancestors are implied); the scheduler lists every action |
| `bay_id`                      | `uint16`          | final loop in `Plan()`, `TYPE_RETRIEVE` only                                                | after motion planning                      | the bay of the job's `PROCESS_RETRIEVE` action; `0` otherwise (an error is logged if a retrieve has none)                                                                                                                      |
| `bay_arrival_node_guid`       | `Guid`            | same                                                                                        | same                                       | the `guid` of that `PROCESS_RETRIEVE` `ActionNode`                                                                                                                                                                             |

`node_indices` is filled by matching guids, not indices: each `ActionNode` carries `job_id = scheduled_jobs[event->GetJobIndex()].job.guid` (set in `BuildActionDagFromMotions`); `BuildScheduledActionsArray` writes the nodes in the final ordering, and `WriteJobActionIndices` (`action_graph.cpp:487`) then walks that array and appends each node's position to the entry whose `job.guid` equals that `job_id`. The bay fields are found the same way: `FindPayloadDeliveryAction` (`scheduler.cpp:54`) scans the nodes for a `TYPE_BAY_COMMAND` with `COMMAND_TYPE_PROCESS_RETRIEVE` and the job's guid.

![ScheduledJobData on the Pecos map](figures/74_scheduled_job_data_map.svg)

What the entries hold for a concrete request. AGV-1 retrieves the car on T17 to bay B21 (job A); AGV-2 moves out of the way (job B); an INSERT fails (job C). The badges on the map are positions in `Schedule.nodes`. Job A's `node_indices` skip 3 because job B's move was ordered between job A's actions; its `bay_arrival_node_guid` points at node 11, the `PROCESS_RETRIEVE`. Job C has no actions: only its `job` status fields say anything.

### Places, ids and garage events

The remaining message types are small and shared:

| Type                                                                                                                                                        | Fields                                          | Meaning                                                                                                                                                                                                  |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `GaragePose`                                                                                                                                                | `node_id`, `heading`                            | A discrete place: a layout node and a heading in degrees, counter-clockwise from garage north (90 faces −x; [section 3](#ly-agv-coordinate-system) of the Layout file tab)                               |
| `GeometricPose`                                                                                                                                             | `x`, `y`, `yaw`                                 | A continuous place in metres and radians, same heading convention; not used by the planners                                                                                                              |
| `SizedPose`                                                                                                                                                 | `resource_size_index`, `pose`                   | A pose plus a resource-window index                                                                                                                                                                      |
| `GarageNode`                                                                                                                                                | id, position, floor, type, windows, headings, … | One node of the layout file (Layout file tab, [section 4](#ly-nodes))                                                                                                                                    |
| `GarageEntityId`                                                                                                                                            | `entity_type`, `id`                             | Which asset: `'a'` AGV, `'b'` bay, `'t'` tray, `'v'` VECS, `'r'` VRC ([asset type](#bg-term-asset-type)). Used by `ScheduleEvent::GetGarageEntityId` and the trajectory maps                             |
| `Guid`                                                                                                                                                      | `bytes[16]`                                     | A 128-bit id for calls, jobs, actions and payloads                                                                                                                                                       |
| Garage events: `AgvPoseChanged`, `AgvLiftChanged`, `BayStateChanged`, `VecsStateChanged`, `VrcStateChanged`, `*ExistenceChanged`, `*DisablednessChanged`, … | the asset, its current value and its next value | One change to a `DiscreteGarageState`. The planner's events are translated into these and applied with `OnEvent` ([section 12.3](#bg-what-onevent-is)); `Set` loads a snapshot with the existence events |

## `DiscreteGarageState`: the bridge between the garage and the planner

The previous section described `base_state` as a message. This section is about the C++ class of the same name that `Plan()` builds from it. `DiscreteGarageState` is the most important type in the system. The Scheduler never plans over geometry directly; it plans over this structured snapshot of AGVs, trays, bays, payloads, VECS, VRCs and disabled nodes. The ROS message carries them as arrays; inside the class they are `std::map`s keyed by id (`agvs_`, `trays_`, `bays_`, `vexen_`, `vrcs_`; `payloads_` by GUID) plus a `std::set` of disabled node ids. Ordered maps are deliberate: the state's hash depends on iteration order. Every physical fact the planner cares about must be expressible in it.

![DiscreteGarageState bridge](figures/16_discrete_garage_state_bridge.svg)

`DiscreteGarageState` ties the floor layout to the planner's data structures. The left side reuses the Pecos drawing: ① AGV-4 parked at charger `C10`, ② tray 15 at parking node `P3`, ③ the payload riding on tray 15, and ④ bay 7 in `READY_TO_RETRIEVE`. Each number points to the matching record on the right; the filled diamond marks containment inside the single snapshot. Values are illustrative.

How it is used in the scheduler:

- **Built once per call** by `ValidateBaseState(request_data.base_state, *layout_)` in `utils.cpp`, which replays one existence event per record and then checks the result against the layout ([section 6.3](#bg-base-state-the-garage-snapshot)). It does **not** check that entities overlap.
- **Copied freely.** It is a value type. `working_state = ctx->initial_state` makes an independent copy that a function can mutate without affecting anyone else.
- **Advanced by events.** `event->ApplyTo(working_state)` returns a `BoolStringPair` (still, in `planner_core`) and moves entities discretely (a tray simply appears at its destination); the scheduler turns a failure into a `stdx::Result`.
- **Queried constantly** with `GetAgv(id)`, `GetTray(id)`, `GetTrayOnNode(node)`, `GetPayload(guid)`, `GetBay(id)`, `GetVecs(vecs_id)` (a VECS id is its node id), each returning `std::optional`. Each is a `std::map` lookup, O(\log n); `GetTrayOnNode` scans the trays.
- **Not quite atomic.** The header promises that a failed event leaves the state unchanged, but `OnEvent(AgvPoseChangedMsg)` moves a carried tray before its last check ([section 12.3](#bg-what-onevent-is)). Discard a state whose replay failed.

## Package anatomy: files and classes

Part III follows one `Plan()` call through the code. It starts with where that code lives: the files of the `scheduler` package and the classes they define. Since PR \#1018 each stage of `Plan()` has its own source file, and each stage file starts with its entry point, followed by what it calls in call order.

| File                                                               | Lines                 | What to look for                                                                                                                                                                                    |
|--------------------------------------------------------------------|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `include/scheduler/scheduler.hpp`                                  | 342                   | The `Scheduler` class, `SchedulerParams`, and the tray-assignment result types `PlannedTrayMove`, `TrayDestinationPlan` and `ResolveRequest`. Read this first; private methods are grouped by stage |
| `include/scheduler/plan_context.hpp`                               | 80                    | `PlanContext`, the per-call workspace ([section 15](#bg-schedulecontext-the-per-call-workspace))                                                                                                    |
| `include/scheduler/job_failure.hpp`, `format.hpp`                  | 20, 31                | `JobFailure` and `Fail(...)`, a job expansion's error; `std::formatter`s for a pose, a GUID and an entity id, used in error texts                                                                   |
| `src/scheduler.cpp`                                                | 384                   | The constructor, `StorePreferredPayloadHeadingsForRetrieval`, `Plan()`, `ExpandJob`, `PlanMotions`, `MakeFailedJob`, the bay-readiness callback and the layout queries several stages use           |
| `src/job_expansion.cpp`                                            | 903                   | Stage 1: every `Expand<Type>Job` and its helpers                                                                                                                                                    |
| `src/tray_assignment.cpp`                                          | 709                   | Stage 2a: `AssignTrays`, `TrayAssignmentState`, blocking-tray resolution                                                                                                                            |
| `src/agv_assignment.cpp`                                           | 830                   | Stage 2b: `AssignAgvs`, `AgvAssignmentState`, the AGV ordering passes                                                                                                                               |
| `src/validation.cpp`                                               | 107                   | Stage 3: `ValidateEventSequence` and `ValidateMoveDestinationAndPath`                                                                                                                               |
| `src/action_graph.cpp`                                             | 566                   | Stage 5: `BuildActionGraph`, `ToActionNode`, `MotionScheduleOrder`, VRC action insertion, `GenerateNextActionGuid`                                                                                  |
| `include/scheduler/bay_rebalancing.hpp`, `src/bay_rebalancing.cpp` | 45, 189               | Bay classification (`ClassifyBays`) and the rebalancing plan (`CalculateDesiredBaySplit`, `ComputeBayRebalancingActions`)                                                                           |
| `include/scheduler/move_events.hpp`, `src/move_events.cpp`         | 16, 33                | `MakeAgvPoseMove`, `MakeTrayMove`: the event builders                                                                                                                                               |
| `include/scheduler/utils.hpp`, `src/utils.cpp`                     | 31, 78                | `ValidateBaseState`, state and pose helpers (`ReverseHeading`, `ReversePoseHeading`, `IsSameOrOppositeHeading`, `MakeInboundPose`); namespace `volley`                                              |
| `src/scheduler_ros.cpp`, `include/scheduler/scheduler_ros.hpp`     | 133, 42               | ROS services, publishers, clients                                                                                                                                                                   |
| `src/scheduler_component.cpp`                                      | 71                    | Parameter reading, component registration                                                                                                                                                           |
| `test/`                                                            | ~3 700 C++, plus YAML | 99 GoogleTest cases in 19 binaries, each driven by a scenario file ([section 19](#bg-debugging-and-testing)); see the [Verification](#doc-verification) tab for a map                               |
| `tools/view_scheduler_tests`, `tools/plan_viewer/`                 | —                     | A viewer that renders every scenario as a page                                                                                                                                                      |
| `CMakeLists.txt`, `package.xml`                                    | —                     | Build targets and package dependencies ([section 21](#bg-packages-build-system-and-dependencies))                                                                                                   |

The scheduler's own types are in namespace `volley::scheduler` (`Scheduler`, `PlanContext`, `SchedulerRos`, …); the libraries it uses, and the helpers in `utils.hpp`, are in `volley`. `scheduler_msgs.hpp`, which held the `...Msg` aliases, is gone.

| Class / type                                          | What it does                                                                                                                                    | Declared in                                                                                                    | Key members / methods                                                                                                                                                                                                         |
|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Scheduler`                                           | The planner. Validates requests, expands jobs into events, assigns trays and AGVs, checks the result, runs motion planning, builds the response | `scheduler.hpp`                                                                                                | `Plan`, `ExpandJob` → `Expand*Job`, `AssignTrays`, `AssignAgvs`, `ValidateEventSequence`, `PlanMotions`, `BuildActionGraph`                                                                                                   |
| `SchedulerParams`                                     | Constructor-time settings                                                                                                                       | `scheduler.hpp`                                                                                                | `target_insert_ready_bay_fraction`, `is_cost_audit_enabled`, `motion_cost`                                                                                                                                                    |
| `PlanContext`                                         | Mutable working set for one plan call                                                                                                           | `plan_context.hpp`                                                                                             | `initial_state`, `event_dag`, `scheduled_jobs`, `last_event_by_entity`, `first_event_by_tray`, `keep_out_filter_by_footprint`, `AddChainedEvent`, `ChainAfterLastEntityEvent`, `OrderAfterJobLeafEvents`, `FindKeepOutFilter` |
| `ScheduleEvent` and subclasses                        | Discrete state changes that can be replayed against a DGS                                                                                       | `planner_core/schedule_events.hpp`, `src/schedule_events.cpp`                                                  | `ApplyTo`, `GetGarageEntityId`, `GetJobIndex`, `GetType`                                                                                                                                                                      |
| `Dag<T>`, `ScheduleEventDag`                          | Boost-graph DAG of `shared_ptr<T>`, and its event specialisation                                                                                | `planner_core/event_dag.hpp`, `src/event_dag.cpp`                                                              | `AddEvent`, `AddDependency`, `GetTopologicalOrdering`, `GetRootEvents`, `GetLeafEvents`, `WouldCreateCycle`, `RemoveRedundantEdges`, `Remove`, `ApplyEventsTo`                                                                |
| `DiscreteGarageState`                                 | Garage snapshot with typed accessors                                                                                                            | `common_ros/discrete_garage_state.hpp`                                                                         | `Set`, `GetAgv`, `GetTray`, `GetTrayOnNode`, `GetPayload`, `GetBay`, `GetVecs`                                                                                                                                                |
| `GarageGraph`, `PoseGraph`                            | Pose graph for searches ([section 6](#bg-the-garage-model-in-code))                                                                             | `common_ros/garage_graph.hpp`, `common_ros/pose_graph.hpp`                                                     | `GetVertexFromPose`, `GetPoseFromVertex`, `GetOutEdges`, `SetRetrievalHeading`                                                                                                                                                |
| `CollisionTable`                                      | Precomputed footprint conflicts between footprint types at poses and edges                                                                      | `common_ros/collision_geometry.hpp`                                                                            | `Query(fixed_id, queried_id, location[, queried_location])`                                                                                                                                                                   |
| `GarageOccupancyChecker<T>`                           | For each pose or edge, which occupants block it and for which footprint types                                                                   | `common_ros/garage_occupancy_checker.hpp`                                                                      | `AddOccupant`, `GetBlockers`                                                                                                                                                                                                  |
| `MotionCostModel`                                     | Durations from speeds, accelerations and event times                                                                                            | `cost_functions/motion_cost_model.hpp`                                                                         | `Params()`, `Duration(transition | run, is_agv_loaded)`, `VelocityLimitsFor` ([section 23.2](#bg-the-cost-model))                                                                                                             |
| `Chugg`                                               | The motion planner: plans every event of the event DAG into timed, collision-free motions                                                       | `motion_planner/chugg.hpp`                                                                                     | `SolveSequential` (used), `SolveCbs` (unfinished) ([section 21](#bg-chugg-the-motion-planner))                                                                                                                                |
| `ContinuousState`, `Trajectory`, `Motion`, `Interval` | CHUGG's output: a timeline of motions per entity                                                                                                | `motion_planner/continuous_state.hpp`, `trajectory.hpp`, `interval.hpp`                                        | `GetTrajectories`, `SetTrajectory`, `Motion::GetDelta`, `GetActionId` ([section 24](#bg-continuousstate-the-timeline))                                                                                                        |
| `SchedulerRos`, `SchedulerComponent`                  | ROS adapter and component wrapper                                                                                                               | `scheduler_ros.hpp`, `scheduler_component.cpp` (`SchedulerComponent` stays in `volley`: it is the plugin name) | see [section 2](#bg-where-the-scheduler-runs-the-node-and-its-interfaces)                                                                                                                                                     |

![Current class relationships](figures/11_uml_existing_core.svg)

Existing core-class relationships. `Scheduler` creates one `PlanContext` per `Plan()` call; the context owns the `initial_state` and the `event_dag`. `ScheduleEventDag` specialises the Boost-based `Dag<T>` template and holds its `ScheduleEvent` vertices through `shared_ptr` (shared, not exclusive, ownership). Each event's `ApplyTo()` mutates a `DiscreteGarageState` during replay.

Shortest possible mental model: **`Scheduler` is the conductor, `PlanContext` is the score being annotated, `ScheduleEventDag` is the dependency structure of the work, and `DiscreteGarageState` is the simulated world the work is replayed on.**

## Objects, ownership and lifetimes

Two lifetimes matter in one call: one `Scheduler` per node, built at start-up with the static garage model, and one `PlanContext` per `Plan()` call, holding everything that call creates.

![Runtime objects and lifetimes](figures/21_runtime_objects.svg)

Two lifetimes. The node keeps one `Scheduler` whose members are built in a fixed order, each from the one before it. Every plan request gets a fresh `PlanContext` that holds all mutable planning data and is released when `Plan()` returns.

### Constructing the Scheduler

The `Scheduler` is built once, when the node starts, and its constructor creates the static garage model in a fixed chain: layout, pose graph, garage graph, collision table. In the code below, note that each member is built from the one initialised before it, which is why declaration order matters.

``` cpp
// Where: Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger,
//                             const SchedulerParams& params) in src/scheduler.cpp:86.
// Called once, from SchedulerRos's constructor: std::make_shared<Scheduler>(layout_filepath, logger, params).
// C++ initialises members in DECLARATION order (see scheduler.hpp), which here matches this list:
Scheduler::Scheduler(std::string layout_filepath, rclcpp::Logger logger, const SchedulerParams& params) :
    layout_(std::make_shared<Layout>(layout_filepath)),   // LayoutSPtr: parse the layout YAML
    motion_graph_(PoseGraph(layout_)),        // GarageGraph: search graph built from a temporary PoseGraph
                                              //   (every allowed (node, heading)); no PoseGraph member
    collision_table_(motion_graph_, logger),  // CollisionTable: precomputed footprint conflicts
    logger_(logger),
    cost_model_(params.motion_cost),          // cost::MotionCostModel from ROS parameters
    target_insert_ready_bay_fraction_(params.target_insert_ready_bay_fraction),  // std::atomic<float>,
                                                                                //   changed by a service
    is_cost_audit_enabled_(params.is_cost_audit_enabled) {
  StorePreferredPayloadHeadingsForRetrieval();   // writes a preferred parking heading into motion_graph_
}
```

`StorePreferredPayloadHeadingsForRetrieval()` (`scheduler.cpp:97`) takes the bay at the **back** of `layout_->GetBayPrioritization()` (the bay a retrieve reaches for first), computes the heading a tray must face to drive into it, and caches that heading on every parking node that allows it and can still reach the bay. Later, `FindPreferredTrayHeadingForRetrieval` returns that heading (reversed for a car that faces the other way on its tray) and the job expansions park loaded trays facing that way, so retrieves need fewer rotations.

### Creating the per-call context

This is the snippet that confuses most new readers, so here it is with every name explained:

``` cpp
// Where: interfaces::msg::PlanResponse Scheduler::Plan(const interfaces::msg::PlanRequest& request_data,
//                                                      const rclcpp::Time& now) const
//        (src/scheduler.cpp:138)
//   this          -> the Scheduler. There is no variable called "scheduler" here: layout_, motion_graph_
//                    and collision_table_ are its members. The method is const, so it cannot change them.
//   request_data  -> the PlanRequest from Dispatch (see "ROS messages and services")
//   now           -> node time when the service call arrived
interfaces::msg::PlanResponse response;
response.id = request_data.id;                        // echo the id so Dispatch can match the reply

// ValidateBaseState is a free function in utils.cpp. It returns
// stdx::Expected<DiscreteGarageState>: the state, or an error message.
const auto validated_state = ValidateBaseState(request_data.base_state, *layout_);
if(!validated_state) {
  response.success = false;                           // the ONLY path that returns success == false
  response.message = "Invalid base state in plan request! " + validated_state.error();
  return response;
}
// Already-running actions: their AGVs, start and end nodes, bays and VECS become unavailable.
// ExcludeCommittedResources is a file-local function in scheduler.cpp:31; it takes the state by value.
const auto& committed_actions = request_data.base_schedule.nodes;
auto initial_state = ExcludeCommittedResources(validated_state.value(), committed_actions);

// ctx is a PlanContextSPtr == std::shared_ptr<PlanContext>. Every later stage
// receives this same pointer and edits the object it points to.
const auto ctx = std::make_shared<PlanContext>(request_data.id, std::move(initial_state), now);

// For each footprint (collision id): which graph vertices and edges are unusable because of
// disabled AGVs / nodes / bays. A free function in motion_planner (static_graph_filtering.cpp).
ctx->keep_out_filter_by_footprint =
    BuildKeepOutFilters(motion_graph_, ctx->initial_state, collision_table_);
```

The exclusion and the filters are explained in [section 14](#bg-the-base-schedule-reserved-assets-and-keep-out-filters). [Section 7](#bg-schedulecontext-the-per-call-workspace) describes each field of the new `PlanContext` and which stage reads or changes it.

Why can a `const` method change anything at all? `Plan()` cannot modify `*this`, but `ctx` is a local `shared_ptr` to a **non-const** `PlanContext`. The same holds for `AssignTrays(PlanContextSPtr ctx) const` and friends: the Scheduler's graphs and tables stay fixed, and all planning state lives in `*ctx`. Do not read `const` as “thread-safe”, though: `is_dag_printing_enabled_` is a plain `bool` that the `debug/printdags` service flips through the non-const `ToggleDagPrinting()`, and `GenerateNextActionGuid()` uses a plain static counter. The `plan` service runs in the node's default callback group, so plan calls are handled one at a time today.

## One `Plan()` call, step by step

This section follows a single `Plan()` call from request to response. The figure shows the control flow with every early return; the numbered list then summarises the nine steps, and the code that follows shows the job loop that expands each pending job into events.

![Plan control flow](figures/22_plan_control_flow.svg)

`Scheduler::Plan()` step by step with every early return. Job expansion fails jobs one at a time. Any failure after expansion fails **every** pending job at once and returns no schedule, but `PlanResponse.success` stays `true`; only an invalid base state returns `false`. Not drawn: CHUGG can also *throw* ([section 21](#bg-chugg-the-motion-planner)), and nothing in the scheduler catches it.

In order, one call does nine things:

1.  **Validate and construct.** `ValidateBaseState` builds `initial_state` from `base_state`; an invalid snapshot is the only way to get `success = false`.
2.  **Reserve and filter.** `ExcludeCommittedResources` marks everything `base_schedule` uses as disabled, the `PlanContext` is created and `keep_out_filter_by_footprint` is built.
3.  **Job expansion.** The job loop below hands each pending job to `ExpandJob`, which turns it into events; a failing job is reported once and leaves no events. If no job succeeds, the call returns here with the message “No jobs succeeded to plan”.
4.  **Tray assignment.** `AssignTrays` fills blank trays and destinations and moves blocking trays.
5.  **AGV assignment.** `AssignAgvs` picks an AGV for every tray move and adds its approach, lift and lower.
6.  **Remove redundant edges and check.** `RemoveRedundantEdges()` drops redundant edges (it fails on a cycle); `ValidateEventSequence` replays the DAG and checks every move.
7.  **Motion planning.** `PlanMotions` runs CHUGG and returns timed trajectories.
8.  **Build the action graph.** `BuildActionGraph` turns motions into the action DAG and returns the `Schedule`'s nodes; it also writes each job's `node_indices`.
9.  **Fill the response.** Planned jobs become `STATE_EXECUTING`, and a retrieve gets its bay fields; a failure in steps 4–8 fails every planned job instead (the local lambda `fail_all_jobs`).

Steps 3 to 6 are the Task planning tab, step 7 the Motion planning tab and step 8 the Action graph tab. Step 2, reserving everything the running schedule uses, has its own section next ([section 11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)). Every stage returns `stdx::Result` (or `stdx::Expected`), and `Plan()` is the one place that turns a failure into job results. The job loop copies the context, expands, and either keeps the job or restores the copy. `ExpandJob` is a plain `switch`; each case calls one `Expand<Type>Job` method with the index the job **will** have if it succeeds:

``` cpp
// Where: Scheduler::Plan(...) const, src/scheduler.cpp:159, after ctx has been created.
//   job                -> const interfaces::msg::SchedulerJob&, one element of request_data.pending_jobs
//   context_before_job -> a PlanContext value: a copy of *ctx, sharing its event objects
//   expansion          -> stdx::Expected<void, JobFailure>; JobFailure is {message, is_retryable}
for(const interfaces::msg::SchedulerJob& job : request_data.pending_jobs) {
  const auto context_before_job = *ctx;
  if(const auto expansion = ExpandJob(ctx, job)) {
    ctx->AddScheduledJob(job);              // now job_index really is this job's position
  }
  else {
    *ctx = context_before_job;              // drop every event the failed expansion added
    const auto& [message, is_retryable] = expansion.error();
    response.scheduled_jobs.push_back(MakeFailedJob(job, message, is_retryable));   // STATE_ERROR
    if(job.type == interfaces::msg::SchedulerJob::TYPE_INSERT && clean_garage_request_fn_) {
      clean_garage_request_fn_();           // a failed insert still leaves the garage to clean up
    }
  }
}

// Where: Scheduler::ExpandJob(PlanContextSPtr ctx, const interfaces::msg::SchedulerJob& job) const,
//        src/scheduler.cpp:251.
//   job_index -> ctx->scheduled_jobs.size(): the position this job takes if expansion succeeds.
//                Every event created for the job stores it (event->GetJobIndex()).
const auto job_index = ctx->scheduled_jobs.size();
switch(job.type) {
case interfaces::msg::SchedulerJob::TYPE_RETRIEVE:
  return ExpandRetrieveJob(ctx, job.payload_id, job_index);
// ... one case per job type, see "Job expansion" in the Task planning tab
default:
  return Fail("Unknown job type {}({})", job.type, job.type_name);
}
```

Two consequences are easy to miss:

- **A failed job leaves no events behind.** An expansion can add events before its last check fails; restoring the copy removes them. The copy shares the event objects, which is safe because expansion never changes an existing event. Before PR \#1018 the events stayed in the DAG and, carrying a job index the next job then took, became that job's events; a job could also be reported twice.
- **Reading a response:** check `scheduled_jobs[i].job.state` (`STATE_EXECUTING` or `STATE_ERROR`) and `job.note`, not just `success`.

The methods of each stage file, in file order, form a useful map (file-local helpers in *italics* are not `Scheduler` members):

| File                                                       | Functions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scheduler.cpp`: construction, entry point, shared queries | *`ExcludeCommittedResources`*, *`FindPayloadDeliveryAction`*, *`LogMotionCostAudit`*, `Scheduler::Scheduler`, `StorePreferredPayloadHeadingsForRetrieval`, `Plan`, `ExpandJob`, `PlanMotions`, `MakeFailedJob`, `SetBayReadinessRatioCallback`, `MakeBayInboundPose`, `IsBayOdpAreaClear`, `IsParkingWithoutBayOrCharger`, `GetFirstSystemFloor`, `GetVersionInfo`                                                                                                                                                                                                                                                                                                                             |
| `job_expansion.cpp`: stage 1                               | *`ComputeStateAfterPlannedEvents`*, *`AddChargingStopBeforeTrayMove`* and other event helpers, `ExpandAgvMoveJob`, `ResolveCarriedTrayDestination`, `ExpandRetrieveJob`, `ExpandReparkTrayJob`, `CheckReparkDestination`, `AddBayTransitionToRetrieve`, `ExpandInsertJob`, `ExpandReadyForInsertJob`, `ExpandReadyForRetrieveJob`, `ExpandCleanGarageJob`, `ReparkWaypointStashedTrays`, `ExpandRebalanceGarageJob`, `ExpandAgvChargeJob`, `ExpandBayTransitionJob`, `ExpandChargePayloadJob`, `AssignTraysToBayFillMoves`, `IsPayloadWithinBaySizeLimits`, `FindBayForRetrieve`, `FindUnoccupiedChargerWithShortestTravelTime`                                                                |
| `tray_assignment.cpp`: stage 2a                            | *`ChainTrayEvent`*, `AssignTrays`, `ApplyBayOrChargerTransition`, `AssignEmptyTrayToMove`, `AssignDestinationAndUnblockingMoves`, `BuildImmobileTrayFilter`, `ResolveDestinationHeading`, `ResolveBlockingTrays`, `ComputeTrayCollisionId`, `OrderAfterPriorOccupants`, `FindPreferredTrayHeadingForRetrieval` (the heading policy), `FindDestinationForRootTray`, `FindBlockingTrayResolution`                                                                                                                                                                                                                                                                                                |
| `agv_assignment.cpp`: stage 2b                             | *`ChainAgvEvent`*, *`ComputeStateBefore`*, `AssignAgvs`, `ApplyNonTrayRootEvents`, `ComputeAgvAssignmentEdgeCosts`, `BuildAgvOrderDag`, `AssignAgvToTrayMove`, `PropagateEarliestStartToChildren`, `OrderAgvMovesAfterBlockingAgvs`, `OrderAllTransitionsAroundAgvLifts`, `ComputeAgvMoveDuration`, `OrderArrivalAfterPriorOccupant`, `ComputeAgvAssignmentCost`, `FindAssignedAgvsBlockingPickup`, `ScheduleAgvMoveToPickup`, `ScheduleAgvLiftChange`, `ComputeTravelDuration`, `AddNextMissingAgvMoveOrder`, `OrderTransitionAroundAgvLifts`, `ComputeAgvLiftDuration`, `ComputeAgvPickupDuration`, `OrderAfterTraysOnPath`, `OrderAgvMoveAfterBlockerDeparture`, `FindAgvDepartureFromNode` |
| `validation.cpp`: stage 3                                  | `ValidateEventSequence`, `ValidateMoveDestinationAndPath`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `action_graph.cpp`: stage 5                                | *`GenerateNextActionGuid`*, *`IsAgvMotionBetweenFloors`*, *`ComputeVrcFloorTransitSeconds`*, *`InsertVrcActionsIntoDag`*, *`MotionScheduleOrder`*, *`ToActionNode`*, *`CollectAndCollapseTrajectoryMotions`*, *`BuildActionDagFromMotions`*, *`TransferEventDagDepsToActionDag`*, *`BuildScheduledActionsArray`*, *`WriteJobActionIndices`*, `BuildActionGraph`                                                                                                                                                                                                                                                                                                                                |

## The base schedule: reserved assets and keep-out filters

Before any job is planned, `Plan()` takes out of play everything the already-running schedule uses. It does this with the same `disabled` flags that mark an asset as out of service, and it then builds `keep_out_filter_by_footprint`, which turns those flags into graph vertices and edges that no new motion may use. This section explains why the scheduler does this, what the flags mean, and where every later stage reads them.

**Status in today's configuration.** Dispatch only calls `Plan()` when no job is active, so `base_schedule` is empty in every real call and this loop does nothing ([section 6.2](#bg-planrequest-one-moment-in-a-running-schedule)). It matters as soon as overlapping planning is turned on, and that is the case this section explains.

![Reserving what the running schedule uses](figures/116_base_schedule_reservation.svg)

**Reserving what the running schedule uses.** Step through one request. AGV-2 has two moves and bay B21 one command in `base_schedule`. The loop marks AGV-2 and B21 disabled and adds every source and destination node to `disabled_nodes_`; the keep-out filters follow. A pending MOVE_AGV for AGV-2 then fails, a repark of T24 succeeds, AGV assignment skips AGV-2, and in the last two steps both schedules run side by side without sharing an asset.

### What the loop marks

The reservation loop, in the file-local function `ExcludeCommittedResources` (`scheduler.cpp:31`), walks every `ActionNode` in `base_schedule` and, depending on its type, marks an AGV, bay, VECS or node as disabled in `initial_state`. The table lists, for each action type, the setter that is called and the field it changes; note that VRC commands reserve nothing.

| `ActionNode.type` in `base_schedule` | Call                                                                     | Field set in `initial_state`                                                                               |
|--------------------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `TYPE_AGV_COMMAND`                   | `SetAgvDisabled(agv_id)`, `SetNodeDisabled(src)`, `SetNodeDisabled(dst)` | `agvs_[agv_id].disabled = true`; the command's source and destination node ids go into `disabled_nodes_`   |
| `TYPE_BAY_COMMAND`                   | `SetBayDisabled(bay_id)`                                                 | `bays_[bay_id].disabled = true`, and `bay_id` goes into `disabled_nodes_` (a bay's id is its node id)      |
| `TYPE_VECS_COMMAND`                  | `SetVecsDisabled(vecs_id)`                                               | `vexen_[vecs_id].disabled = true`, and `vecs_id` goes into `disabled_nodes_` (a VECS's id is its node id)  |
| `TYPE_VRC_COMMAND`                   | none                                                                     | nothing: a VRC with commands in the running schedule stays available ([section 8](#ly-vrc-support-status)) |

Three details of the setters (common_ros `discrete_garage_state.cpp`):

- **Unknown ids are ignored silently.** `SetAgvDisabled`, `SetBayDisabled` and `SetVecsDisabled` look the id up and change nothing if it is missing. A node id always goes into `disabled_nodes_`, even if the layout has no such node; `BuildStaticObstacleFilter` later throws on that (“a disabled node that does not exist in the layout”).
- **Only the ends of each AGV command are reserved**, but for a schedule this scheduler built that covers the whole route, edges included; a command that spans several nodes leaves a gap ([section 11.2](#bg-what-closing-a-node-does)).
- **Trays are not reserved by name.** A tray carried by a busy AGV stays usable in the bookkeeping, but it stands on a reserved node (the AGV's source), so the keep-out filters treat it as an obstacle and `IsTrayAvailable` does not count it as an empty tray.

### What closing a node does to the graph

The loop reserves the source and destination of every AGV command, not the path between them. Whether that leaves part of the route open depends on how long one command is, and on what “closing” a node actually changes.

**For schedules this scheduler builds, the whole route is closed.** CHUGG plans one motion per graph edge, and the response turns every motion that changes something into its own `ActionNode`. Only VRC floor rides are merged into one motion (`CollectAndCollapseTrajectoryMotions`); chains of ground moves are left as they are. A route W26 → W27 → P24 therefore arrives as two commands, W26→W27 and W27→P24. Every stop is the destination of one command and the source of the next, so every stop is reserved, and every edge of the route ends at a reserved stop. Lifts and rotations have the same source and destination node and close that node.

**Closing a node edits no graph.** `Layout`, `PoseGraph`, `GarageGraph` and `CollisionTable` are built once per `Scheduler` and never change. Closing a node adds its id to a set, and every filter built from the state afterwards switches off poses and edges near it. [Figure 1](#bg-fig-122_closing_a_node) follows one example through each data structure.

![What closing a node does](figures/122_closing_a_node.svg)

**What closing a node does, data structure by data structure.** Two one-edge commands of AGV-1 put W26, W27 and P24 into `disabled_nodes_`. `BuildStaticObstacleFilter` turns each closed node into the footprint of its largest window, asks the `CollisionTable` which AGV poses and edges overlap it, and builds boolean masks with those entries set to `false`. The last step is a different request: one command that passes through W26 reserves only its two ends and leaves W26 open. Overlaps are drawn with plain rectangles; the real sets come from the `CollisionTable`.

| Data structure                                            | Owner and type                                                                                            | What closing W27 does to it                                                                                                                                                                                                 |
|-----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `disabled_nodes_`                                         | `DiscreteGarageState` (common_ros), `std::set<uint32_t>`                                                  | Gets the id 27. A busy AGV's own flag is `agvs_[id].disabled`; a bay or VECS gets its flag and its id in this set                                                                                                           |
| `disabled_node_ids`                                       | local of `BuildStaticObstacleFilter` (motion_planner), `std::set<uint32_t>`                               | A copy of `disabled_nodes_` plus the node of every disabled AGV, tray and bay. AGV-1's own node is closed this way even if no command starts there                                                                          |
| footprint of the closed node                              | `CollisionEntityId_t`                                                                                     | The largest window W27 allows (`max_resource_size_index`; XL in Pecos), as `PAYLOAD + index`, or `TRAY` if the node allows no car. A closed node is treated as if the largest possible car stood on it                      |
| `CollisionTable::Query(footprint, collision_id, {27, h})` | `CollisionTable` (common_ros), returns `PoseSet`, `EdgeSet`                                               | Called once per heading of the node: every pose and every edge where the filter's footprint (an AGV here) would overlap that window. Nothing is computed geometrically at this point; the table was precomputed at start-up |
| `blocked_poses`, `blocked_edges`                          | locals of `BuildStaticObstacleFilter`, `unordered_set<GaragePose>`, `unordered_set<array<GaragePose, 2>>` | Collect the query results of every closed node, every obstacle entity and, for payload footprints, every pose too small for the car                                                                                         |
| `vertex_filter_`, `edge_filter_`                          | `GraphFilterProperties`, `VertexVectorPropertyMap<bool>`, `EdgeVectorPropertyMap<bool>`                   | One boolean per vertex and per edge of the `GarageGraph`, all `true`, then `false` for each listed pose and edge. `IsEnabled(v)` is an unchecked index into them                                                            |
| `ctx->keep_out_filter_by_footprint`                       | `PlanContext`, `unordered_map<CollisionEntityId_t, GraphFilterProperties>`                                | One mask pair per footprint (`AGV`, `TRAY`, each car size present), built once in `Plan()`. Every other `BuildStaticObstacleFilter` call, including CHUGG's `constraints_`, builds masks with the same closed nodes         |

So a closed node switches off more than the node: in the figure, closing W26, W27 and P24 also switches off the edges W25–W26, P23–W26 and P23–P24, because an AGV on them would reach into a closed window. Searches that read the masks (`FindPosePath`, SIPP's `GetTraversableEdges`) never enter those poses or edges, for the whole plan.

**The gap.** The interface allows one command to cover several nodes: `AgvCommand.msg` says “There may be other poses between src and dst”. Such a command reserves only its two ends. The nodes in between stay open unless a reserved window happens to cover them; on a long straight run, the middle of the run can stay open too. In the last step of the figure, W26 and the edge P23–W26 stay on, so a new plan could send an AGV to W26 while AGV-1 is still passing through. Commands the scheduler builds never span several nodes. Whether Dispatch merges commands, or receives them from elsewhere, is not visible in the snapshots. If it can, the loop should reserve every node on the path between `src` and `dst`, not just the two ends.

### Why reserve the assets that still have to move

The assets in `base_schedule` are not idle; they are busy. They move during the call, under commands Dispatch released before it. In this loop, “disabled” does not mean “broken”: it means **owned by the running schedule, do not use**. Reading `SetAgvDisabled` as “reserve this AGV” is accurate. Reservation serves the goal of a `Plan()` call rather than working against it, for four reasons:

- **A call plans only `pending_jobs`.** (The request's fields are laid out on a time line in [section 7.2](#bg-planrequest-one-moment-in-a-running-schedule).) The request says `base_schedule` is “the immutable portion of the current schedule” and that the scheduler “is to assume that all of these actions will be completed”. The jobs it serves are listed in `planned_jobs` and `active_jobs` and are not planned again. The busy assets already have their work; reserving them protects it.
- **Each asset follows one command queue.** An AGV runs its actions in order (Type 1 edges, [section 7.3](#ad-our-edges-versus-type-1-and-type-2)). If the new plan also gave AGV-2 commands, Dispatch would hold two schedules for one robot with no order between them. A bay or VECS could likewise receive a second command while its first transition is still running.
- **The snapshot is not advanced.** `base_state` is the garage now, before the base actions finish. They are `ActionNode`s, not `ScheduleEvent`s, so the scheduler does not replay them, and their timing is Dispatch's. It therefore does not know where a busy AGV will be at a given moment. Keeping the AGV's current footprint and reserving both ends of each of its commands covers every place it can be while the new plan runs.
- **The two schedules share no edges.** The scheduler adds no dependency from a base action to a new one ([section 7.5](#ad-persistent-planning-base-schedule-and-the-split)). Excluding every shared asset is what makes that safe: two schedules that use different AGVs, bays, VECS and nodes cannot conflict, whatever their relative timing.

The price is conservatism. A busy AGV is unavailable for the *whole* new plan, even if its last base action ends seconds after the call. A pending job that needs a reserved asset fails instead of waiting for it, and Dispatch must send it again in a later request.

### One flag, two meanings

`disabled` already means something before the loop runs. `base_state` carries assets taken out of service by an operator or by the fault system, and nodes closed off. They are set through `SetResourceDisabledness.srv` and recorded as `AgvDisablednessChanged`, `BayDisablednessChanged`, `VecsDisablednessChanged`, `TrayDisablednessChanged` and `NodeDisablednessChanged` events, each with its own `OnEvent` handler. The loop writes the same fields, so after it runs nothing in `initial_state` tells the two apart:

- **Failure messages name the wrong cause.** A MOVE_AGV job for a busy AGV fails with “Tried to move a disabled agv 2”, and CHARGE_AGV with “Can't charge \<AGV\> because it's disabled.” Whoever reads the job's error sees “disabled”, not “busy”.
- **Duration is lost.** An out-of-service asset is unavailable until someone re-enables it; a reserved one is free once its last base action ends. The flag has no room for that difference.
- **Logs hide the running schedule.** The logged `initial_state` lists reserved assets as disabled, so how much of the garage the running schedule holds is not visible.

### Where the flags are read

The flags are read in two ways: directly (`agv.disabled`, `bay.disabled`, `GetDisabledNodes()`) and through filters built from them. Every stage of `Plan()` sees them.

| Stage             | Function                                                                                         | Reads                                                                                       | Effect on a reserved asset                                                                                                                                  |
|-------------------|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Job expansion     | `ExpandAgvMoveJob`                                                                               | `agv.disabled`; `keep_out_filter_by_footprint` at the destination                           | “Tried to move a disabled agv”; a reserved destination is “a disabled location”                                                                             |
| Job expansion     | `ExpandAgvChargeJob`                                                                             | `agv.disabled`; the AGV's keep-out filter (`FindKeepOutFilter`, looked up once) per charger | The job fails; reserved chargers are skipped                                                                                                                |
| Job expansion     | `ExpandRetrieveJob`, `ClassifyBays`                                                              | `keep_out_filter_by_footprint` at the payload's tray; `bay.disabled`                        | A payload in reserved space fails (“in a disabled area”); a reserved bay is `NOT_USABLE`                                                                    |
| Job expansion     | `ExpandReparkTrayJob`, `ExpandInsertJob`, `ExpandBayTransitionJob`, `ReparkWaypointStashedTrays` | `tray.disabled`, `bay.disabled`, `keep_out_filter_by_footprint` at the destination          | The job fails or the asset is skipped (some bay commands skip the check, [section 4.16](#bg-gotchas-2))                                                     |
| Bay rebalancing   | `ComputeBayRebalancingActions` via `CountEmptyTrays`                                             | `IsTrayAvailable`: tray on a disabled node, or disabled                                     | Not counted as an empty tray                                                                                                                                |
| AGV assignment    | `AssignAgvs`, `OrderAgvMoveAfterBlockerDeparture`                                                | `agv_state.disabled`                                                                        | Never a candidate; never counted as an AGV that could move out of the way                                                                                   |
| Sanity check      | `ValidateMoveDestinationAndPath`, called by `ValidateEventSequence`                              | `keep_out_filter_by_footprint`, then `BuildStaticObstacleFilter` on the working state       | A move onto a reserved destination fails the check before any path search                                                                                   |
| Every path search | `BuildStaticObstacleFilter`                                                                      | disabled AGVs, trays and bays (their node joins `disabled_node_ids`); `GetDisabledNodes()`  | Each disabled node blocks the volume of its largest window at every heading                                                                                 |
| Motion planning   | `Chugg::GetMovableAgvs`, `FindAgvUnderTrayAssignment`                                            | `agv.disabled`                                                                              | No `SippAgv`: the AGV is a static obstacle at its current pose for the whole plan                                                                           |
| Action graph      | `BuildActionGraph`                                                                               | —                                                                                           | Nothing: base actions are not part of the response, although Dispatch requires them to be ([section 6.2](#bg-planrequest-one-moment-in-a-running-schedule)) |

### `keep_out_filter_by_footprint`: the keep-out map

Right after the reservation, `Plan()` calls `volley::BuildKeepOutFilters(motion_graph_, ctx->initial_state, collision_table_)` (motion_planner, `static_graph_filtering.cpp`):

``` cpp
// motion_planner/src/static_graph_filtering.cpp (abridged)
std::unordered_map<volley::CollisionEntityId_t, GraphFilterProperties> BuildKeepOutFilters(
    const volley::GarageGraph& motion_graph, const volley::DiscreteGarageState& state,
    const volley::CollisionTable& collision_table) {
  std::unordered_set<uint16_t> ignore_agvs;
  std::unordered_set<uint16_t> ignore_trays;
  std::unordered_set<uint16_t> ignore_bays;

  // An entity is ignored when it is enabled and not on a disabled node.
  const auto& disabled_nodes = state.GetDisabledNodes();
  for(const auto& [agv_id, agv_state] : state.GetAgvs()) {
    if(!disabled_nodes.contains(agv_state.pose.node_id) && !agv_state.disabled) {
      ignore_agvs.insert(static_cast<uint16_t>(agv_id));
    }
  }
  // ... the same for trays (tray_state.pose.node_id) and bays (the bay id is its node id)
  return BuildStaticObstacleFilters(
      motion_graph, state, collision_table, ignore_trays, ignore_agvs, ignore_bays);
}
```

Read it from the return statement backwards. `BuildStaticObstacleFilters` is the general tool: for the AGV footprint, the empty-tray footprint and every payload window found on a tray, it calls `BuildStaticObstacleFilter`, which switches off each vertex and edge where that footprint would collide with an entity that is not ignored, with every disabled node, or (for payloads) with a pose too small for the payload. `BuildKeepOutFilters` ignores every entity that is neither disabled nor on a disabled node. What remains as an obstacle is exactly the set of things the new plan may never use:

- disabled AGVs, trays and bays, at their current pose: AGV-2 at P15 in [Figure 1](#bg-fig-116_base_schedule_reservation);
- any entity standing on a disabled node: T15, under AGV-2;
- every disabled node, as the volume of the largest window the node allows (`max_resource_size_index`), at every heading the node has.

The value type, `GraphFilterProperties`, holds two boolean property maps, one per vertex and one per edge, and `IsEnabled(v)` is an unchecked index into them. The map is keyed by `CollisionEntityId_t`, the footprint type, because whether a place is usable depends on the size of what goes there.

**Why it is needed.** Planning asks two different questions about a place, and the code keeps one structure for each:

| Question                                                  | Answered by                                                                                       | Built from                                                                 | Built                               |
|-----------------------------------------------------------|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|-------------------------------------|
| Is this place usable at all in this plan?                 | `ctx->keep_out_filter_by_footprint[footprint]`                                                    | reserved and out-of-service assets and nodes only                          | once per call, from `initial_state` |
| Is this place free now, after the events replayed so far? | `BuildStaticObstacleFilter(footprint, motion_graph_, working_state, collision_table_, ignore...)` | every entity in `working_state` except the ones the caller expects to move | on demand, many times per call      |

The first answer is fixed for the whole call, so it is built once and read in constant time. Job methods use it to reject a job early with a precise reason (a payload in reserved space, a repark onto a reserved node) before any path search, and the sanity check’s `ValidateMoveDestinationAndPath` uses it to tell “never usable” from “occupied for now”. The second answer changes with every replayed event, so it is rebuilt where it is needed. Without the keep-out map, each check would have to rebuild a filter with the right ignore sets just to make that distinction. The per-state filters also block reserved assets and nodes, so later path searches respect the reservation as well.

**The name.** Until PR \#1018 the field was `disabledness_filters`, of type `CollistionFilterMap` (misspelt), filled by `GetDisabledEntitiesFilters`: “disabledness” is not a word, the entries are usability masks rather than degrees of disabledness, and the name hid that most entries come from the running schedule. PR \#1018 adopted the naming catalogue's proposal ([section 15.4.2](#nm-schedulecontext)): `keep_out_filter_by_footprint`, since “keep-out area” is the usual robotics term for space a robot must not enter and the `<value>_by_<key>` rule ([section 15.2.6](#nm-rule-maps)) names the key; the type is a plain `std::unordered_map`, and the producer in motion_planner became `BuildKeepOutFilters`. Lookups go through `PlanContext::FindKeepOutFilter(collision_id)`, which returns `stdx::Expected` and fails with “No keep-out filter for footprint …”. The old lookups used `operator[]`, which inserted an empty filter for a missing footprint, and an empty filter reads every location as disabled (not reached in practice).

Recommended changes to the reservation and the keep-out map (naming, a record of what was reserved, time-bounded reservations) are in the Issue & proposal tab ([section 7.5](#pr-base-schedule-reservation)).

## Event types and polymorphism

The job loop of [section 10](#bg-one-plan-call-step-by-step) fills `ctx->event_dag` with `ScheduleEvent`s, and every later stage reads them back by replaying them. This section opens up those events; the next one the DAG that holds them. Replaying means applying the events in an order where every dependency comes first, a *topological order* ([section 13.2](#bg-what-a-topological-ordering-is-in-plain-words)).

A `ScheduleEvent` is an in-memory C++ object for one discrete state change that can be replayed against a `DiscreteGarageState`. The classes are in `planner_core/schedule_events.hpp` and `src/schedule_events.cpp` (in `sources/repomix-planner-core.xml`).

The design idea is **runtime polymorphism**. `ctx->event_dag` stores `std::shared_ptr<ScheduleEvent>`, but each pointer actually points to a `TrayMove`, `AgvMove`, `BayTransition`, `VecsTransition` or `VrcTransition`. When the Scheduler replays the DAG, virtual dispatch runs the right `ApplyTo` (`Apply` before PR \#1018). When it needs subclass-specific data it checks `event->GetType()` and then downcasts:

``` cpp
// Where: the loop at the top of Scheduler::AssignTrays(PlanContextSPtr ctx) const
//        (src/tray_assignment.cpp:42).
//   events -> std::optional<std::vector<ScheduleEventSPtr>> from
//             ctx->event_dag.GetEventsInTopologicalOrder(); empty only for a cyclic graph
//   event  -> std::shared_ptr<volley::ScheduleEvent>
for(const auto& event : *events) {
  if(event->GetType() != ScheduleEventType::TRAY_MOVE) { /* handle bay/VECS events */ continue; }
  auto move = dynamic_cast<TrayMove*>(event.get());   // non-owning raw pointer; event keeps it alive
  if(!move->GetTrayId()) { /* std::optional<uint16_t> is empty: no tray chosen yet */ }
  // ...
}
```

![Existing event inheritance](figures/12_uml_event_hierarchy.svg)

The `ScheduleEvent` hierarchy from `planner_core/schedule_events.hpp`. The single **hollow triangle** under `ScheduleEvent` means public inheritance; every branch reads “`TrayMove` **is a** `ScheduleEvent`”, not “`ScheduleEvent` contains a `TrayMove`”. Blue marks the abstract base type, green the movement / assignment events, violet the other resource-state transitions.

Two confusions to avoid: inheritance says nothing about execution order, and the subclasses are siblings, not phases. A `TrayMove` never “turns into” an `AgvMove`; AGV assignment adds separate `AgvMove` events around it.

### The base class

Every event type derives from the abstract class `ScheduleEvent`, which defines the interface that the rest of the scheduler relies on when it replays events. The abridged declaration below shows that interface; the points that follow it explain the details later tabs depend on.

``` cpp
// planner_core/schedule_events.hpp (abridged)
enum class ScheduleEventType : uint8_t {
  AGV_MOVE = 1, BAY_TRANSITION = 2, TRAY_MOVE = 3, VECS_TRANSITION = 4, VRC_TRANSITION = 5,
};

class ScheduleEvent {
public:
  explicit ScheduleEvent(ScheduleEventType type, unsigned int job_index);
  ScheduleEvent() = delete;
  ScheduleEvent(ScheduleEvent const&) = default;        // copy-constructible ...
  virtual ~ScheduleEvent() = default;

  virtual BoolStringPair ApplyTo(volley::DiscreteGarageState& state) const = 0;  // const: never changes the event
  virtual std::optional<interfaces::msg::GarageEntityId> GetGarageEntityId() const = 0;  // AGV / tray / bay / ...
  unsigned int GetJobIndex() const;                     // set once, in the constructor
  ScheduleEventType GetType() const;
  virtual std::string ToString() const;                 // "Task ID: <job> <TYPE>" + subclass details
private:
  ScheduleEvent& operator=(ScheduleEvent const&) = default;   // ... but NOT copy-assignable
  ScheduleEventType type_;
  unsigned int job_index_;
};
using ScheduleEventSPtr = std::shared_ptr<ScheduleEvent>;
```

Four facts the next tabs rely on:

- **`ApplyTo` is `const`.** Replaying an event changes only the `DiscreteGarageState` passed in, never the event. That is why the same event objects can be replayed by every job method and every stage.
- **The job index is fixed at construction.** There is no setter. Blocker moves get their index by being constructed with the root move's `GetJobIndex()`.
- **Events can be copy-constructed but not assigned.** `TrayMove copy = *move;` compiles; `copy = *move;` does not (the base copy assignment is private). The refactor proposal (the [Issue & proposal](#doc-proposal) tab) relies on the first.
- **`GetGarageEntityId()` drives rule A** (an event waits for the previous event on the same AGV, tray, bay or VECS). It returns the entity whose last event a new event must wait for. A `TrayMove` with no tray yet returns `std::nullopt`, which is why such moves skip rule A ([section 14.5](#bg-where-the-edges-come-from)).

### The subclasses, and what `ApplyTo` does

The five subclasses of `ScheduleEvent` differ in the data they carry and in what their `ApplyTo` method does to a `DiscreteGarageState`. The table summarises each subclass; pay particular attention to `TrayMove`, whose behaviour depends on which of its optional fields are set, as the figure and list after the table explain.

| Event            | Data                                                                                                                | `GetGarageEntityId()`                                     | What `ApplyTo(state)` does                                                                                                                                                                                                                                                                                                                                                                                                       |
|------------------|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `TrayMove`       | `tray_id_`, `dest_`, `agv_id_`: all `std::optional`, each with a getter and a setter                                | `TrayId(tray)`, or `std::nullopt` while the tray is blank | Five cases, see the next figure                                                                                                                                                                                                                                                                                                                                                                                                  |
| `AgvMove`        | `std::variant<interfaces::msg::AgvLiftChanged, interfaces::msg::AgvPoseChanged> discrete_change_`                   | `AgvId(agv)`                                              | `state.OnEvent(change)`: lift or lower, or move the AGV (and any tray it carries) from `node_id_curr@heading_curr` to `node_id_next@heading_next`                                                                                                                                                                                                                                                                                |
| `BayTransition`  | `src_state_` (`interfaces::msg::DiscreteBayState`, includes the bay id), `command_` (`interfaces::msg::BayCommand`) | `BayId(src_state_.id)`                                    | Fails unless the bay's current state equals `src_state_.state`; then `ApplyBayCommand`: `TRANSITION_TO_INSERT` READY_TO_RETRIEVE → READY_TO_INSERT; `PROCESS_RETRIEVE` needs a tray with a payload on the bay's node (looked up with the bay id as node id), sets READY_TO_RETRIEVE → READY_TO_INSERT and removes the payload (the car leaves); `TRANSITION_TO_RETRIEVE` READY_TO_INSERT or VEHICLE_INSERTED → READY_TO_RETRIEVE |
| `VecsTransition` | `state_change_` (`interfaces::msg::VecsStateChanged`: VECS id, current and next state)                              | `VecsId(vecs)`                                            | `state.OnEvent(state_change_)`                                                                                                                                                                                                                                                                                                                                                                                                   |
| `VrcTransition`  | `state_change_` (`interfaces::msg::VrcStateChanged`), `from_vrc_node_id_`, `to_vrc_node_id_`                        | `VrcId(vrc)`                                              | IDLE → MOVING → IDLE on the new floor, then teleports every AGV and every loose tray on `from_vrc_node_id_` to `to_vrc_node_id_`                                                                                                                                                                                                                                                                                                 |

![What TrayMove::ApplyTo does](figures/67_traymove_apply.svg)

`TrayMove::ApplyTo`, branch by branch. A blank tray id makes it a no-op. A blank destination **removes** the tray (and its payload) from the state. Otherwise any other tray already on the destination node is moved to the placeholder pose `{node_id: 0, heading: 0}`, and the tray is either teleported (no AGV yet) or carried by its AGV, which must be at the tray's pose, lifted and holding that tray.

`TrayMove::ApplyTo` matters because job methods replay half-specified moves:

- **Blank tray id → nothing happens.** `READY_FOR_INSERT`'s “some empty tray → bay” leaves no trace in a later job's `working_state`: the bay still looks empty. The source comment admits this “might cause issues with blocking tray calculations”.
- **Blank destination → the tray disappears.** “T21 → ?” removes T21 and its payload from `working_state` (a TODO suggests parking it at `{node_id: 0, heading: 0}` instead). A later job in the same request cannot see or reuse that tray, and its old node looks free.
- **Destination occupied → the occupant goes to `{node_id: 0, heading: 0}`.** The discrete replay never fails because two trays want one node; the earlier occupant is parked at the placeholder node. Tray assignment is what later makes such a move physically possible.
- **With an AGV → strict checks.** After AGV assignment, `ApplyTo` fails unless the AGV is at the tray's pose (same or opposite heading), lifted, and carrying that tray. This is why AGV assignment adds the approach and lift events **before** the `TrayMove`.

What each event looks like when it is created (as the scheduler's sources create it; `move_events.cpp` holds the two builders for the common cases):

| Event            | Created with                                                                                                                                                                                         | Filled in later                                                |
|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| `TrayMove`       | `MakeTrayMove(job_index, tray_id, dest, agv_id)`, each argument a `std::optional` that is set when known (it calls `std::make_shared<TrayMove>(job_index)`, then `SetTrayId`, `SetDest`, `SetAgvId`) | tray id / destination by `AssignTrays`, AGV id by `AssignAgvs` |
| `AgvMove`        | `MakeAgvPoseMove(job_index, agv_id, source, destination)`, or `std::make_shared<AgvMove>(job_index, interfaces::msg::AgvLiftChanged)` for a lift                                                     | —                                                              |
| `BayTransition`  | `std::make_shared<BayTransition>(job_index, DiscreteBayState, BayCommand)`; the command comes from `MakeBayCommand` in `job_expansion.cpp`                                                           | —                                                              |
| `VecsTransition` | `std::make_shared<VecsTransition>(job_index, VecsStateChanged)`, built by `MakeVecsStateChange`                                                                                                      | —                                                              |
| `VrcTransition`  | never created by the scheduler package: VRC trips are added to the action DAG instead ([section 20](#bg-bays-vecs-and-vrcs))                                                                         | —                                                              |

A `TrayMove` is **not** an AGV command. Before assignment it may mean “bring *some* empty tray to this bay” (no tray id) or “put this tray *somewhere* sensible” (no destination). `AgvMove` has getters only (`GetSrc`, `GetDest`); its declared but never implemented `SetSrc` and `SetDest` were deleted in PR \#1018.

### Inside `AgvMove::ApplyTo`

Every subclass's `ApplyTo` does the same job: translate a planner event into one or more garage event messages and hand each one to `DiscreteGarageState::OnEvent`. `AgvMove::ApplyTo` is the shortest example, and it packs several C++ features into three lines:

``` cpp
// planner_core/src/schedule_events.cpp
//   state            -> the working copy being advanced, never ctx->initial_state
//   discrete_change_ -> std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg> (common_ros aliases of
//                       interfaces::msg::AgvLiftChanged and AgvPoseChanged)
// Overrides the pure-virtual ScheduleEvent::ApplyTo.
BoolStringPair AgvMove::ApplyTo(volley::DiscreteGarageState& state) const {
  return std::visit(
      [this, &state](auto&& arg) -> BoolStringPair { return state.OnEvent(arg); }, discrete_change_);
}
```

| Feature                              | In this code                      | What it means here                                                                                                                                                                                                                                                                                                                                                |
|--------------------------------------|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `const` member function              | `ApplyTo(...) const`              | Inside, `this` is a `const AgvMove*`: the method may read `discrete_change_` but not change it. It must be `const` because the base declares `virtual BoolStringPair ApplyTo(DiscreteGarageState&) const = 0`, and that is what lets every stage replay the same shared events. Only the argument `state` changes.                                                |
| `std::variant`                       | `discrete_change_`                | A type-safe union: it holds exactly one of `AgvLiftChangedMsg` (raise or lower) or `AgvPoseChangedMsg` (drive or rotate), plus an index that says which.                                                                                                                                                                                                          |
| `std::visit`                         | `std::visit(f, discrete_change_)` | Reads the index at run time and calls `f` with the alternative the variant holds. It is the variant's equivalent of a virtual call.                                                                                                                                                                                                                               |
| Lambda and capture list              | `[this, &state](...) { ... }`     | An unnamed function object written in place. `&state` captures the caller's state by reference, so the lambda changes the real working copy and copies nothing. `this` is captured but never used; it can be dropped (clang flags it with `-Wunused-lambda-capture`). The lambda lives only for the duration of the `visit` call, so the reference cannot dangle. |
| Generic lambda, forwarding reference | `auto&& arg`                      | `auto` in a parameter makes the lambda a template: the compiler writes one body per alternative. `auto&&` is a forwarding (“universal”) reference: it binds to whatever `visit` passes without copying. Here the method is `const`, so `visit` passes `const AgvLiftChangedMsg&` or `const AgvPoseChangedMsg&`, and `arg` has exactly that type.                  |
| Trailing return type                 | `-> BoolStringPair`               | States the lambda's return type instead of letting the compiler deduce it from `return`. `std::visit` requires every alternative's call to return the same type; all `OnEvent` overloads already return `BoolStringPair`, so here the annotation documents the contract and turns any future mismatch into a compile error at the lambda.                         |
| Overload resolution                  | `state.OnEvent(arg)`              | In each copy of the lambda, `arg` has a different static type, so the compiler picks a different `OnEvent` overload in each: no run-time cost. If an alternative had no matching overload, the code would not compile.                                                                                                                                            |
| `BoolStringPair`                     | return value                      | `std::pair<bool, std::string>`: success and, on failure, a reason. `FailedEvent(msg)` and `SucceededEvent()` in common_ros build it with `std::make_pair`.                                                                                                                                                                                                        |

Written out by hand, the same method reads:

``` cpp
BoolStringPair AgvMove::ApplyTo(volley::DiscreteGarageState& state) const {
  if(const auto* lift = std::get_if<AgvLiftChangedMsg>(&discrete_change_)) {
    return state.OnEvent(*lift);         // OnEvent(const AgvLiftChangedMsg&)
  }
  // OnEvent(const AgvPoseChangedMsg&)
  return state.OnEvent(std::get<AgvPoseChangedMsg>(discrete_change_));
}
```

The behaviour is identical. The `visit` form needs no edit when a third alternative is added, and it fails to compile if that alternative has no `OnEvent`; the hand-written form would silently send it down the last branch. `AgvMove::GetAgvId()` and `ToString()` use the same pattern, and `GetSrc()` / `GetDest()` use the explicit `std::holds_alternative` form.

### What `OnEvent` is

`OnEvent` is a family of overloaded member functions of `DiscreteGarageState` in common_ros, one per garage event message: `FaultStateChanged`; `Agv{Existence, Disabledness, Lift, Pose, State}Changed`; `Bay{Disabledness, Existence, State}Changed`; `Vecs{Disabledness, Existence, State}Changed`; `Vrc{Existence, State}Changed`; `Tray{Existence, Disabledness}Changed`; `TrayPoseSetManually`; `PayloadExistenceChanged`; `NodeDisablednessChanged`. A twentieth overload takes the generic `DiscreteGarageEventMsg`, deserializes it according to its `type` string and forwards to the typed one, so a state can be fed a stream of garage events as they arrive. Inside the scheduler, the typed overloads are called directly by `ApplyTo`.

Every overload has the same shape: **check, then change, then report**. The checks compare the message with the state; the change happens only after them; the result is a `BoolStringPair`. For the two messages an `AgvMove` carries:

- **`OnEvent(const AgvPoseChangedMsg&)`.** The AGV must exist and be at `node_id_curr@heading_curr`, and the move must change something. If it carries a tray, the tray moves to `node_id_next` too, keeping its reciprocal heading if it had one. If another AGV is on `node_id_next`, the event fails. Then the AGV's pose becomes `node_id_next@heading_next`.
- **`OnEvent(const AgvLiftChangedMsg&)`.** The lift must be in the other position. Raising attaches any tray on the AGV's node, and fails if that tray is not parallel or reciprocal to the AGV; lowering detaches the carried tray.

Two limits matter when reading the planner. The handlers check **consistency, not geometry**: the source says “We do not check for intersections, pose validity, etc.”; footprints and paths are the job of the filters and of CHUGG. And a few handlers **change state before a later check fails**: the pose handler moves a carried tray before it looks for another AGV on the destination, so that failure leaves the tray moved and the AGV not. A state on which `ApplyTo` failed should be discarded, not reused.

The other events send these messages:

| Event            | Messages passed to `OnEvent`                                                                                                                                                                                                                                                                           |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `AgvMove`        | `AgvLiftChangedMsg` or `AgvPoseChangedMsg`                                                                                                                                                                                                                                                             |
| `TrayMove`       | blank destination: `PayloadExistenceChangedMsg` and `TrayExistenceChangedMsg` (removal); no AGV: `TrayPoseSetManuallyMsg` (a teleport; planner_core aliases it as `TrayPoseChangedMsg`), also for an occupant pushed to the placeholder pose; with an AGV: `AgvPoseChangedMsg`, which carries the tray |
| `BayTransition`  | through `ApplyBayCommand`: `BayStateChangedMsg`, plus `PayloadExistenceChangedMsg` for `PROCESS_RETRIEVE`                                                                                                                                                                                              |
| `VecsTransition` | `VecsStateChangedMsg`                                                                                                                                                                                                                                                                                  |
| `VrcTransition`  | two `VrcStateChangedMsg` (IDLE → MOVING → IDLE), then `AgvPoseChangedMsg` per AGV and `TrayPoseSetManuallyMsg` per loose tray on the platform                                                                                                                                                          |

### Why the code is structured this way

One replayed `AgvMove` passes through three choices before any state changes ([Figure 2](#bg-fig-117_apply_call_chain)). Each answers a different question and is owned by a different package:

| Question                                       | Mechanism                                  | Decided                              | Owner        |
|------------------------------------------------|--------------------------------------------|--------------------------------------|--------------|
| Which kind of planner event is this?           | virtual `ScheduleEvent::ApplyTo`           | run time, from the object's class    | planner_core |
| Which change did this `AgvMove` record?        | `std::visit` over `discrete_change_`       | run time, from the variant's index   | planner_core |
| Which rule updates the garage for that change? | overload of `DiscreteGarageState::OnEvent` | compile time, from the argument type | common_ros   |

The split has three benefits. **The rules live in one place.** How a lift attaches a tray, or what makes a move invalid, is written once in `DiscreteGarageState`, and every user of a state gets the same answer. **Planned and reported changes use one vocabulary.** A planner event is translated into the same messages that report changes in the garage, so a replayed plan and a state fed with real events are updated by the same code, and the messages already have `std::to_string` and YAML support for logs and tests. **Events stay data.** An `AgvMove` is an `AGV_MOVE` event for the DAG rules (its `GetGarageEntityId()` is the AGV, whichever alternative it holds), and the variant keeps one class for lifts and drives instead of two subclasses that every `GetType()` switch would have to handle.

The costs are indirection (three hops for a one-line change) and a habit of ignoring the result. Before PR \#1018 five `Apply` calls in the scheduler discarded the returned pair; the scheduler now checks every `ApplyTo` and turns a failure into a `stdx::Result` (the clean-garage AGV moves, the charge job's bay transition and the AGV move-order replay now fail instead of carrying on). Four calls in motion_planner (CHUGG) still discard it, and `ApplyTo` itself still returns `BoolStringPair`. `ScheduleEventDag::ApplyEventsTo`, which replays a whole DAG, returns `stdx::Result` marked `[[nodiscard]]`, as the refactor proposal suggests for new code ([section 6.4](#pr-errors-stdxexpected-instead-of-boolstringpair)).

![Replaying one AgvMove, call by call](figures/117_apply_call_chain.svg)

**Replaying one `AgvMove`.** Step through the calls: a caller copies `initial_state` and asks the DAG to replay itself; the DAG walks its topological order; the virtual call, `std::visit` and overload resolution choose the code; `OnEvent` checks and changes the state; the pair travels back, and the first failure stops the replay.

### A mental model: events are checked deltas, a state is a replay

Think of each event as a **delta with a precondition**: an `AgvPoseChangedMsg` says “AGV-1 is at W26@90 and goes to W27@90”, and `OnEvent` refuses it unless the first half is true. A garage state at any point of the plan is the initial state with every earlier delta applied in order:

s_0 = s\_{\text{init}}, \qquad s_k = \operatorname{apply}(e\_{\pi(k)},\\ s\_{k-1}), \quad k = 1, \dots, n

where \pi is a topological order of the event DAG. If any precondition fails, the DAG does not describe a possible sequence, and the replay stops. This is why messages carry both the current and the next value (`node_id_curr` and `node_id_next`): the current half is the check, the next half the change.

The calls that use this model, in the order a `Plan()` call makes them:

1.  **Build the start once.** `ValidateBaseState` and the reservation loop produce `initial_state` ([section 14](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)). Nothing changes it afterwards.
2.  **Job expansion.** Each job method calls `ComputeStateAfterPlannedEvents(*ctx)` (`job_expansion.cpp:28`), which copies `initial_state` and calls `ctx.event_dag.ApplyEventsTo(state)` to reach the state after all earlier jobs, decides on new events from that state, and often applies each new event to `working_state` as it adds it.
3.  **Tray and AGV assignment.** The same replay, one event at a time in topological order, with decisions in between: fill a blank `TrayMove`, choose an AGV, then apply the completed event (`ApplyTo`) before moving on.
4.  **Sanity check.** `ValidateEventSequence` replays the finished DAG once; any failure fails every pending job ([section 18](#bg-reduce-and-sanitycheckevents)).
5.  **Motion planning.** CHUGG's `InitializeEventOrder` replays once and throws on failure; `PlanNodeSequential` applies each event after planning its motions, so the next event is planned against the right discrete state.

Two rules follow. Always replay onto a **copy**, never onto `ctx->initial_state` (the tests do the latter on purpose). And treat a copy whose replay **failed** as spoiled.

## Directed acyclic graphs, then `ScheduleEventDag`

`ctx->event_dag`, a `ScheduleEventDag`, *is* the plan while `Plan()` runs. Job expansion writes intent into it, tray and AGV assignment extend it, `RemoveRedundantEdges()` thins it, the sanity check replays it, CHUGG plans timed motions from it, and the response builds a *second* graph, the action DAG, from those motions, copying the event edges into it ([section 20](#bg-motion-planning-and-the-response)). This section starts with the graph theory ([12.1](#bg-graph-theory-in-one-paragraph), [12.2](#bg-what-a-topological-ordering-is-in-plain-words)), then goes inside the class: its type family ([12.3](#bg-the-class-dagbaset-and-scheduleeventdag)), what it stores ([12.4](#bg-what-is-stored-vertices-edges-and-shared-events)), each operation ([12.5](#bg-the-operations)), how copies behave ([12.6](#bg-copies-share-events-event_dag_copy-as-a-work-queue)), how the DAG grows during `Plan()` ([12.7](#bg-how-the-dag-grows-during-plan)), what `RemoveRedundantEdges()` does ([12.8](#bg-reduce-fewer-edges-same-order)), and the traps ([12.9](#bg-gotchas)).

### Graph theory in one paragraph

**Graph theory first.** A directed graph **\mathcal G=(\mathcal V,\mathcal E)** has vertices **\mathcal V** and directed edges **\mathcal E\subseteq\mathcal V\times\mathcal V**. Here an edge **(u,v)\in\mathcal E** means event **u** must finish before event **v** may start. A DAG has no directed cycle; otherwise some event would have to finish before itself.

An ordering function **\pi:\mathcal V\to\\0,\ldots,n-1\\** assigns each vertex an index, where **n=\|\mathcal V\|** is the number of events. A topological order satisfies:

(u,v)\in\mathcal E\quad\Longrightarrow\quad\pi(u)\<\pi(v).

### What a topological ordering is, in plain words

The DAG says *what must come before what*, but not *in which single sequence* to do things. A **topological ordering** is such a sequence: a list of all events in which every edge points forward, so each event appears after everything it depends on. Usually there are many valid lists, because independent events (two different jobs, say) can be interleaved in any way. If the graph has a cycle, there is no valid list at all: some event would have to come before itself.

To compute one by hand, repeatedly take any event whose prerequisites have all been taken already. "Replaying the DAG" (`event_dag.ApplyEventsTo(working_state)`) means applying events in exactly such an order.

![Topological ordering](figures/53_topological_ordering.svg)

A retrieve (four events; worked through in [section 14](#bg-job-expansion-from-jobs-to-events)) plus two reparks of another tray. One hand computation, two valid orders, one invalid order (an edge points backwards) and a cycle, for which `GetTopologicalOrdering()` returns an empty optional.

Two consequences for the code: a pass that walks the order should not depend on which valid order it gets (`ScheduleEventDag` puts lower job indices first, but leaves ties within a job to a heap, [12.5](#bg-the-operations)), and any edge that would close a cycle makes every later pass fail (“Failed to get total ordering”, “The graph must be a DAG.” and similar). That is why risky edges are guarded with `WouldCreateCycle(a, b)`.

![Dependencies](figures/04_dependencies.svg)

Abstract prerequisite ordering. Swimlanes group events by resource; the columns give one valid topological order. The arrows express dependencies, not geometric movement or travel time. The dashed edge is implied by a longer path, which is the kind of redundant edge `RemoveRedundantEdges()` removes.

### The class: `Dag<T>` and `ScheduleEventDag`

Both classes are in `planner_core/event_dag.hpp` (with five methods in `src/event_dag.cpp`), in namespace `volley`; the code is in `sources/repomix-planner-core.xml`. `Dag<T>` (`DagBase<T>` before PR \#1018) is a header-only template that wraps a Boost graph; `ScheduleEventDag` derives from `Dag<ScheduleEvent>` and adds six methods (one of them overrides the topological sort). PR \#1018 deleted the API nothing used (`AddDependent`, `DrawGraph`, `HasEvent`, `GetVertexFromEvent`, `RemoveVertex`, `DagToVec` and others).

![ScheduleEventDag and the Dag family](figures/63_event_dag_classes.svg)

`Dag<T>` holds a Boost `adjacency_list` whose vertices store `std::shared_ptr<T>`, plus a map from pointer to vertex. `ScheduleEventDag` inherits everything and adds the event-specific methods; it overrides `GetTopologicalOrdering()` to put lower job indices first. The scheduler uses four DAG objects: `ctx->event_dag` (the plan), `pending_events` (a work queue inside AGV assignment; `event_dag_copy` before PR \#1018), `agv_order_dag` (a `Dag<uint16_t>` of AGV ids: which matched AGV goes first in one round) and `final_actions_dag` (the response's action nodes).

``` cpp
// planner_core/event_dag.hpp (abridged)
template <typename T>
class Dag {
public:
  using Graph  = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, std::shared_ptr<T>>;
  using Vertex = typename Graph::vertex_descriptor;   // vecS: an index 0 .. n-1 (std::size_t)
  using Edge   = typename Graph::edge_descriptor;     // what GetInEdges / GetOutEdges iterate over
  Dag(Dag const&) = default;                 // copies graph_ and vertex_by_node_: same shared_ptrs
  virtual ~Dag() = default;
  // ... about 25 methods, listed under "The operations" ...
  virtual std::optional<std::vector<Vertex>> GetTopologicalOrdering() const;   // Boost DFS version
  [[nodiscard]] stdx::Result RemoveRedundantEdges();
protected:
  Graph graph_;                                                    // vertices + edges
  std::unordered_map<std::shared_ptr<T>, Vertex> vertex_by_node_;  // pointer -> vertex, kept in sync
};

class ScheduleEventDag : public Dag<ScheduleEvent> {
public:
  [[nodiscard]] stdx::Result ApplyEventsTo(DiscreteGarageState& state) const;   // replay every event, in order
  bool AddEvent(const ScheduleEventSPtr& event) { return Add(event).has_value(); }
  ScheduleEventSPtr GetEvent(const Vertex& vertex) const { return GetNode(vertex); }   // throws if absent
  std::optional<std::vector<ScheduleEventSPtr>> GetEventsInTopologicalOrder() const;
  std::vector<ScheduleEventSPtr> GetLeafEvents() const;        // vertex order
  std::vector<ScheduleEventSPtr> GetRootEvents() const;        // sorted by job index
  std::optional<std::vector<Vertex>> GetTopologicalOrdering() const override;  // job-index priority
};
```

Three design choices explain most of the behaviour in the rest of this section:

- **`boost::vecS` for vertices.** Vertices are plain indices `0 … n−1`, so lookups by vertex are array accesses and `HasVertex(v)` is just `v < NumVertices()`. The price: removing a vertex shifts every later index down by one.
- **`bidirectionalS`.** Each vertex stores both its in-edges and its out-edges, so `GetInEdges`, `GetParents` and in-degree checks are cheap. Rule B's leaf search and the root search both use the degrees.
- **A side map `vertex_by_node_`.** Boost only maps vertex → value. `Dag` keeps the reverse map itself, so “where is this event?” is a hash lookup. Every pointer-taking method goes through it, and it is why the same event cannot be added twice: `Add(ptr)` returns `std::nullopt` if `ptr` is already a key.

### What is stored: vertices, edges and shared events

A `ScheduleEventDag` stores events as vertices of a Boost graph, keeps a reverse map from event pointer to vertex, and shares the event objects with every other structure that refers to them. The figure shows this layout in memory; the table after it sets out the different ways the code refers to one event and how to convert between them.

![ScheduleEventDag storage and event identity](figures/64_event_dag_storage.svg)

The example DAG from the topological-ordering figure, as it sits in memory. `graph_` stores one vertex per event (an index holding a `shared_ptr`) and the edges between indices; `vertex_by_node_` maps each pointer back to its index. The bookkeeping maps in `PlanContext` and the AGV-assignment copy point at the same event objects. Bottom: the three ways the code names an event, and the calls that convert between them.

The code refers to one event in three different ways, and much confusion comes from mixing them up:

| Name              | Type                                                   | What it identifies                              | Where you meet it                                                                                                                                                       | Convert with                                                                                                                                         |
|-------------------|--------------------------------------------------------|-------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| The event pointer | `ScheduleEventSPtr` (`std::shared_ptr<ScheduleEvent>`) | The object itself; equality is pointer identity | `AddDependency(a, b)`, `WouldCreateCycle(a, b)`, `Remove(e)`, keys and values of `last_event_by_entity`, `first_event_by_tray`, the tray-assignment `occupancy_history` | → vertex: `GetVertex(e)`, a lookup in `vertex_by_node_`, `std::nullopt` if absent; → job: `e->GetJobIndex()`                                         |
| The vertex        | `Dag<ScheduleEvent>::Vertex` (`std::size_t`)           | The event's position in **this** DAG            | `GetTopologicalOrdering()` results, `GetSourceVertex(edge)` / `GetTargetVertex(edge)`, CHUGG's `motion.GetActionId()`                                                   | → event: `GetEvent(v)` = `GetNode(v)`, which throws `std::invalid_argument` if `v >= NumVertices()` (it returned an empty optional before PR \#1018) |
| The job index     | `unsigned int`, stored in the event                    | Which job the event belongs to                  | `scheduled_jobs[k]`, rule B, `GetRootEvents()` sorting, topological tie-breaking                                                                                        | Many events share one index; there is no index → event lookup                                                                                        |

The vertex is the fragile one. It is only meaningful for one DAG object, and the comment above `Remove` says plainly what happens on removal: “Every vertex after it moves down by one, so vertices held by the caller are invalid afterwards.” `Remove` keeps `vertex_by_node_` correct, but any `Vertex` you saved elsewhere is now wrong. `ctx->event_dag` never has a vertex removed, and the code depends on that: CHUGG reports each motion with the vertex index of the event it came from, and `BuildActionDagFromMotions` maps it back with `GetEvent`.

### The operations

The scheduler builds, queries, orders, replays and rewrites the event DAG through a fixed set of public methods. The figure applies the main operations to a small example DAG, and the table that follows lists every method by group (build, look up, structure, order and replay, rewrite, debug) with its exact behaviour and where the scheduler calls it.

![ScheduleEventDag operations](figures/65_event_dag_operations.svg)

Each panel applies one operation to the same six-event DAG. (1) `AddEvent` adds an unconnected vertex. (2) `AddDependency(d, g)` adds the edge d → g. (3) Roots are events with no incoming edge (returned sorted by job index), leaves events with no outgoing edge. (4) A topological ordering is a list of vertex indices, lower job indices first. (5) `ApplyEventsTo` replays all events in that order onto a garage state. (6) `WouldCreateCycle(d, a)` is true because a already reaches d. (7) `RemoveRedundantEdges()` removes edges implied by longer paths. (8) `Remove` is only ever called on a copy.

Every public method, grouped by purpose. “Used in” names representative call sites in the scheduler; methods marked *unused* exist but the scheduler package never calls them (PR \#1018 deleted the ones nothing called at all).

| Group                | Call                                                 | Returns                                         | Exact behaviour (from `event_dag.hpp` / `.cpp`)                                                                                                                                                            | Used in                                                                                                                                                                                                                                                                                  |
|----------------------|------------------------------------------------------|-------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **build**            | `AddEvent(e)` (`ScheduleEventDag`)                   | `bool`                                          | `Add(e).has_value()`: `true` if added, `false` if `e` was already in the DAG                                                                                                                               | `PlanContext::AddChainedEvent` (12 calls in job expansion), tray and AGV assignment (4 direct calls)                                                                                                                                                                                     |
|                      | `Add(ptr)`                                           | `std::optional<Vertex>`                         | The new vertex, or `std::nullopt` if `ptr` is already present                                                                                                                                              | `BuildAgvOrderDag`; the action DAG in `BuildActionDagFromMotions` and VRC insertion                                                                                                                                                                                                      |
|                      | `AddDependency(parent, child)`                       | `bool`                                          | Adds parent → child. `false` if either endpoint is not in the DAG, or the edge already exists. **No cycle check.** Overloads take two pointers or two vertices                                             | about 20 calls on the event DAG, 2 of them in `PlanContext`; `OrderAfterPriorOccupants` only logs the result, `BuildAgvOrderDag` throws on `false`, `OrderAgvMoveAfterBlockerDeparture` uses it (“an edge was added”), everything else ignores it                                        |
| **look up**          | `Has(ptr)` / `HasVertex(v)`                          | `bool`                                          | Pointer in `vertex_by_node_`; `v < NumVertices()`                                                                                                                                                          | `Has` in `PropagateEarliestStartToChildren`                                                                                                                                                                                                                                              |
|                      | `GetVertex(ptr)`                                     | `std::optional<Vertex>`                         | Lookup in `vertex_by_node_`                                                                                                                                                                                | `OrderTransitionAroundAgvLifts`                                                                                                                                                                                                                                                          |
|                      | `GetNode(v)` / `GetEvent(v)`                         | `std::shared_ptr<T>`                            | The pointer stored at `v`; throws `std::invalid_argument("Vertex does not exist: …")` if out of range                                                                                                      | everywhere a vertex order is walked                                                                                                                                                                                                                                                      |
|                      | `NumVertices()` / `NumEdges()`                       | `unsigned int`                                  | Boost counts                                                                                                                                                                                               | tests and `RemoveRedundantEdges`                                                                                                                                                                                                                                                         |
| **structure**        | `GetRootEvents()`                                    | `std::vector<ScheduleEventSPtr>`                | In-degree 0, then `std::sort` by job index (ties in unspecified order)                                                                                                                                     | AGV assignment's work queue                                                                                                                                                                                                                                                              |
|                      | `GetLeafEvents()`                                    | `std::vector<ScheduleEventSPtr>`                | Out-degree 0, in vertex order                                                                                                                                                                              | rule B (`OrderAfterJobLeafEvents`)                                                                                                                                                                                                                                                       |
|                      | `GetRootVertices()` / `GetLeafVertices()`            | `std::vector<Vertex>`                           | The same, as vertices                                                                                                                                                                                      | via the two above                                                                                                                                                                                                                                                                        |
|                      | `GetInEdges(v)` / `GetOutEdges(v)`                   | Boost edge-iterator pair                        | Throws `std::invalid_argument("Vertex does not exist: …")` if `v` is out of range                                                                                                                          | `TransferEventDagDepsToActionDag`, the topological sort                                                                                                                                                                                                                                  |
|                      | `GetSourceVertex(e)` / `GetTargetVertex(e)`          | `Vertex`                                        | The two ends of an edge                                                                                                                                                                                    | `TransferEventDagDepsToActionDag`                                                                                                                                                                                                                                                        |
|                      | `GetParents(x)` / `GetChildren(x)`                   | `std::vector<std::shared_ptr<T>>`               | Direct predecessors / successors; empty if `x` is absent. Overloads take a pointer or a vertex                                                                                                             | `OrderTransitionAroundAgvLifts`, `PropagateEarliestStartToChildren`, `ScheduleAgvMoveToPickup` (on the AGV order DAG), the response                                                                                                                                                      |
|                      | `GetVertices()`                                      | iterator pair                                   | All vertices                                                                                                                                                                                               | the “any `TrayMove`s?” check in AGV assignment (`HasTrayMoveEvents`)                                                                                                                                                                                                                     |
|                      | `HasDependency(parent, child)`                       | `bool`                                          | Is there a **direct** edge? `false` if either endpoint is absent                                                                                                                                           | tests                                                                                                                                                                                                                                                                                    |
|                      | `GetBaseGraph()`                                     | `const Graph&`                                  | The Boost graph itself                                                                                                                                                                                     | the topological sort                                                                                                                                                                                                                                                                     |
| **order and replay** | `GetTopologicalOrdering()`                           | `std::optional<std::vector<Vertex>>`            | `ScheduleEventDag`: Kahn's algorithm with a min-priority queue on job index (below). `Dag<T>`: Boost `topological_sort` (DFS), reversed. `std::nullopt` on a cycle                                         | on `ctx->event_dag`: the end-of-stage checks of tray and AGV assignment, `AddNextMissingAgvMoveOrder`, `TransferEventDagDepsToActionDag`, and CHUGG's `InitializeEventOrder`, which makes this order CHUGG's planning priority; `agv_order_dag` and the action DAG use the Boost version |
|                      | `GetEventsInTopologicalOrder()` (`ScheduleEventDag`) | `std::optional<std::vector<ScheduleEventSPtr>>` | The same order, as event pointers                                                                                                                                                                          | tray assignment, `ValidateEventSequence`, `ComputeStateBefore`, `AssignTraysToBayFillMoves`, `ApplyEventsTo`                                                                                                                                                                             |
|                      | `WouldCreateCycle(parent, child)`                    | `bool`                                          | Breadth-first search from `child` along out-edges; `true` if it reaches `parent` or `parent == child`. **`false` if either endpoint is absent**                                                            | the path-blocking edge in `OrderAfterTraysOnPath`; path repair in `OrderAgvMoveAfterBlockerDeparture`; VRC insertion on the action DAG                                                                                                                                                   |
|                      | `ApplyEventsTo(state)` (`ScheduleEventDag`)          | `stdx::Result`                                  | `GetEventsInTopologicalOrder()`, then `event->ApplyTo(state)` for each; stops at the first failure with `"Event <event>: <error>"`, leaving `state` partly advanced; “The graph must be a DAG.” on a cycle | `ComputeStateAfterPlannedEvents`, the one helper through which every job expansion gets its `working_state`                                                                                                                                                                              |
| **rewrite**          | `RemoveRedundantEdges()`                             | `stdx::Result`                                  | Transitive reduction ([12.8](#bg-reduce-fewer-edges-same-order)). “The graph must be a DAG.” on a cycle                                                                                                    | end of `AssignAgvs`; again in `Plan()`; three times in `BuildActionGraph`. All propagate a failure                                                                                                                                                                                       |
|                      | `Remove(ptr)`                                        | —                                               | Removes the vertex and its edges; later vertices shift down by one; `vertex_by_node_` is updated                                                                                                           | only `pending_events.Remove(...)`                                                                                                                                                                                                                                                        |
|                      | `Replace(old, new)`                                  | `bool`                                          | Stores `new` at the vertex of `old`, updating `vertex_by_node_`                                                                                                                                            | only on the action DAG (VRC insertion)                                                                                                                                                                                                                                                   |
| **debug**            | `PrintGraph(label, logger)`                          | —                                               | Logs a Graphviz string (built by the private `ToDotFormatString()`); vertices are labelled `<job><type>`, e.g. `0TM`, `1BT`                                                                                | `PrintDagIfEnabled`, when `is_dag_printing_enabled_` is set                                                                                                                                                                                                                              |

**Edges, roots, leaves.** An edge u → v reads “u must finish before v starts”, nothing more: not “u is near v” and not “the same AGV does both”. A root can start as soon as the plan starts; a leaf is something nothing else waits for. Rule B ([section 14.5](#bg-where-the-edges-come-from)) is built on leaves: a new event of job k waits for every current leaf of job k, which is “everything job k has done so far that nothing else is waiting for”.

**How `ScheduleEventDag` orders events.** It overrides the Boost DFS sort with Kahn's algorithm:

``` cpp
// planner_core/src/event_dag.cpp — ScheduleEventDag::GetTopologicalOrdering (abridged)
// Min-heap on job index: of the vertices ready at each step, the earliest job's comes first.
const auto later_job_first = [this](Vertex left, Vertex right) {
  return GetEvent(left)->GetJobIndex() > GetEvent(right)->GetJobIndex();
};
std::priority_queue<Vertex, std::vector<Vertex>, decltype(later_job_first)> ready_vertices(later_job_first);
// push every vertex with in-degree 0; then repeatedly:
//   u = lowest job index among the ready vertices; append u; decrement the in-degree of u's children;
//   push each child that reaches in-degree 0
// A cycle leaves its vertices unvisited.
if(ordering.size() != NumVertices()) {
  return std::nullopt;
}
```

![How ScheduleEventDag orders events](figures/68_topological_priority.svg)

`ScheduleEventDag::GetTopologicalOrdering()` on the example DAG, one pop at a time. Step through it: the ready events wait on a min-heap keyed by job index, and the one with the lowest index is taken, so job 0's events come out before job 1's wherever the edges allow. Among events of the same job, the heap decides, which depends on the order the vertices were pushed (vertex order for the first roots, then out-edge insertion order). A cycle leaves some vertices never ready, and the method returns `std::nullopt`.

So the order is **deterministic** for a given DAG built in a given order, and it **prefers earlier jobs**. That is a property callers may rely on (replays and walks process job 0 first), but it is not a promise about events *within* one job: the priority queue only compares job indices, so among equal indices the heap's internal order decides.

**Replay.** `ApplyEventsTo(state)` is how a stage answers “where is everything after the events planned so far?” It does not change the DAG or the events (`ScheduleEvent::ApplyTo` is `const`); it advances the `DiscreteGarageState` it is given, discretely. What each event type does to the state is in [section 11](#bg-event-types-and-polymorphism). Every job method starts with the same helper:

``` cpp
// Where: file-local in src/job_expansion.cpp:28; ctx is the PlanContext.
[[nodiscard]] stdx::Expected<DiscreteGarageState> ComputeStateAfterPlannedEvents(const PlanContext& ctx) {
  auto state = ctx.initial_state;                              // a fresh copy of the request's garage
  if(const auto applied = ctx.event_dag.ApplyEventsTo(state); !applied) {   // every event so far, in order
    return stdx::Unexpected(applied.error());
  }
  return state;
}
```

Tray assignment, AGV assignment, path repair and `ValidateEventSequence` do the same replay by hand (walk `GetEventsInTopologicalOrder()` or `GetTopologicalOrdering()` and call `event->ApplyTo(working_state)` per event), because they need to stop or act between events.

### Copies share events: `pending_events` as a work queue

`Dag` declares its copy constructor `= default`, so copying copies `graph_` and `vertex_by_node_`: new vertices and edges, but each vertex holds the same `shared_ptr` as the original. Changing the structure of the copy (removing a vertex) does not affect the original; changing an **event** through either one changes it for both. `AssignAgvs` uses exactly that combination: `auto pending_events(ctx->event_dag);` (`agv_assignment.cpp:121`; `event_dag_copy` before PR \#1018).

![pending_events as a work queue](figures/66_event_dag_copy_queue.svg)

`AssignAgvs` processes the DAG in rounds. Step through them: on the left, the copy loses its roots (phase 1 applies and removes non-tray roots such as the bay transition a; phase 2 matches AGVs to the `TrayMove` roots, calls `SetAgvId` and removes them); on the right, `ctx->event_dag` only grows, because the AGV's approach, lift and lower events are added there, never to the copy. Both DAGs hold the same objects, so the AGV ids set through the copy's roots are what `ctx->event_dag` ends up with.

The copy is a work queue: `AssignAgvs` consumes it root by root, in rounds, while adding events only to `ctx->event_dag`. [Section 17](#bg-agv-assignment-doagvassignments) walks through that loop.

### How the DAG grows during `Plan()`

The same object, `ctx->event_dag`, is extended by three stages and read by three more. Each stage adds its own kinds of edges:

| Stage                                                                                                                                                                | Adds events                                                                      | Adds edges                                                                                                                                                                                                                                                                                                                                                                               | Reads                                                                                                                                                                                                                                            |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Job expansion ([section 14](#bg-job-expansion-from-jobs-to-events))                                                                                                  | `TrayMove`, `AgvMove`, `BayTransition`, `VecsTransition`: the intent of each job | Rule A (same garage asset, across jobs), rule B (leaves of the same job), rule C (into a bay or VECS), plus a few direct `AddDependency` calls in individual job methods                                                                                                                                                                                                                 | `ApplyEventsTo` for `working_state`                                                                                                                                                                                                              |
| Tray assignment ([section 16](#bg-tray-assignment-dotrayassignments))                                                                                                | Blocker `TrayMove`s (and advance moves of the root tray)                         | Chain of required moves; per-tray chain (`TrayAssignmentState::last_event_by_tray`, `ChainTrayEvent`); blocker → root move; `occupancy_history` edges from earlier users of each pose (`OrderAfterPriorOccupants`)                                                                                                                                                                       | `GetEventsInTopologicalOrder` once at the start, `GetTopologicalOrdering` once at the end                                                                                                                                                        |
| AGV assignment ([section 17](#bg-agv-assignment-doagvassignments))                                                                                                   | Approach `AgvMove`s, lift and lower `AgvMove`s                                   | Per-AGV chain (`AgvAssignmentState::last_event_by_agv`, `ChainAgvEvent`); node-arrival order (`OrderArrivalAfterPriorOccupant`); “wait for the blocking tray's first move” (`first_event_by_tray`, cycle-checked, in `OrderAfterTraysOnPath`); path repair (`OrderAgvMovesAfterBlockingAgvs`, cycle-checked); bay / VECS transitions against lifts (`OrderAllTransitionsAroundAgvLifts`) | the copy as a work queue; `GetTopologicalOrdering` for repair and the final check                                                                                                                                                                |
| `RemoveRedundantEdges()` (sections [17](#bg-agv-assignment-doagvassignments), [18](#bg-reduce-and-sanitycheckevents))                                                | —                                                                                | **removes** edges implied by longer paths, at the end of AGV assignment and again in `Plan()`                                                                                                                                                                                                                                                                                            | —                                                                                                                                                                                                                                                |
| Sanity check, motion planning, response (sections [18](#bg-reduce-and-sanitycheckevents), [21](#bg-chugg-the-motion-planner), [25](#ad-how-the-action-dag-is-built)) | —                                                                                | —                                                                                                                                                                                                                                                                                                                                                                                        | `ValidateEventSequence` replays it; CHUGG receives `ctx->event_dag` and plans its events in `GetTopologicalOrdering()` order; `TransferEventDagDepsToActionDag` turns each edge u → v into an action edge “last action of u → first action of v” |

No `VrcTransition` is ever added by the scheduler package; VRC trips are inserted later, at the action level ([section 20](#bg-bays-vecs-and-vrcs)). Two end-of-stage checks catch mistakes: tray assignment finishes, and AGV assignment's last pass (`OrderAllTransitionsAroundAgvLifts`) starts, with `GetTopologicalOrdering()`, and each fails with “Failed to get new total ordering” (logged as “… introduced a loop!!!!”) if a cycle was created. `RemoveRedundantEdges()` now also reports a cycle, before the second check.

### `RemoveRedundantEdges()`: fewer edges, same order

`RemoveRedundantEdges()` (`Reduce()` before PR \#1018) computes the **transitive reduction**: it removes every edge u → v for which another path u → … → v exists. The set of valid orders does not change, but the graph becomes smaller and easier to read, and the response's parent lists get shorter. The stages above add edges liberally, so this matters. (The response code relies on the same idea for its action DAG: “Every move into a space depends on every earlier occupant; RemoveRedundantEdges() prunes the excess”; [section 6.2](#ad-how-the-action-dag-is-built). The theory, and why the reduction is unique, is in [section 2.4](#ad-transitive-reduction).)

The implementation is hand-written:

1.  Get a topological order (the job-priority one, since `GetTopologicalOrdering` is virtual) and each vertex's position in it. On a cycle, return `stdx::Unexpected("The graph must be a DAG.")` without changing anything.
2.  Build a `V × V` reachability matrix of `bool`s, filling it in reverse topological order: u reaches each child v, and everything v reaches.
3.  Mark edge u → v redundant if u has another child w that comes before v and reaches v.
4.  Remove the marked edges.

Memory is `V²` bits and time is roughly `O(V · E)`, which is fine for the tens to low hundreds of events one plan has.

Where it runs, and where it doesn't:

- **Not after tray assignment.** The TODO in `Plan()` (`scheduler.cpp:201`) records why: “Planning may fail without RemoveRedundantEdges() here; calling it after tray assignment instead breaks AGV assignment.”
- **At the end of AGV assignment**, before `OrderAllTransitionsAroundAgvLifts`.
- **Again in `Plan()`**, before `ValidateEventSequence`, under that TODO.

Both calls propagate the returned `stdx::Result`, so a cyclic DAG at that point fails the plan with “The graph must be a DAG.” (new test `EventDagTests.ReduceRejectsCycle`). Before PR \#1018 both discarded the result, and the next `GetTopologicalOrdering()` caught the cycle instead. Why the placement of each call matters is discussed with the final checks in [section 18](#bg-reduce-and-sanitycheckevents).

### Gotchas

The behaviours described above lead to several mistakes that are easy to make when changing code that uses the event DAG. The list below collects them, each with the reason it occurs.

- **Never remove a vertex from `ctx->event_dag`.** Vertex indices are how CHUGG's motions find their events again, and removal shifts every later index. Removing from a copy is fine; that is what the copy is for.
- **A copy is not a snapshot of the events.** `auto copy(ctx->event_dag)` shares every event object. To compare “before” and “after” a stage (as the parity tests in the [Verification](#doc-verification) tab must), build two contexts independently.
- **`AddDependency` fails silently.** It returns `false` when either endpoint was never added (a forgotten `AddEvent`) or the edge exists, and almost every caller ignores the result. A missing `AddEvent` therefore means a missing edge, not an error.
- **Not every edge is cycle-checked, and the check needs both events present.** `AddDependency` never checks for cycles. Only the two risky AGV-assignment edges ask `WouldCreateCycle` first, and it answers `false` (safe) if either endpoint is missing. Everything else relies on the stage-end `GetTopologicalOrdering()` check, which reports *that* there is a cycle, not *which edge* closed it. When debugging one, dump the graph with `debug/printdags` ([section 22](#bg-debugging-and-testing)).
- **Order is by job index, then heap order.** `GetTopologicalOrdering()` and `GetRootEvents()` both prefer lower job indices. Within one job, `GetRootEvents()` uses `std::sort` (not stable) and the topological sort uses a heap, so code must not assume anything about the order of same-job events beyond what the edges force. The same order is CHUGG's planning priority ([section 21.1](#bg-inside-solvesequential)), so it decides which event gets space and time first.
- **`ApplyEventsTo` stops at the first failing event.** The state has then been advanced by every event before it. `ComputeStateAfterPlannedEvents` returns only the error, so a job method never sees the partly replayed state, but a caller that passes its own state must discard it.
- **Replays are repeated, not cached.** Each job method copies `initial_state` and replays the whole DAG, nested calls replay again, and `OrderTransitionAroundAgvLifts` replays from scratch (`ComputeStateBefore`) for each tray move it inspects. This is simple and correct, but cost grows with the square of the number of events.
- **Lookups assume membership.** `GetEvent(v)`, `GetNode(v)`, `GetInEdges` and `GetOutEdges` throw `std::invalid_argument` for an out-of-range vertex, and nothing in `Plan()` catches it. `PropagateEarliestStartToChildren` throws its own `std::runtime_error("Failed to get AGV vertex in DAG")` when an event is missing.

## `PlanContext`: the per-call workspace

`DiscreteGarageState` describes the garage. `PlanContext` (`ScheduleContext` before PR \#1018) describes **one planning attempt**: the garage it started from, the events planned so far, the jobs they belong to, and the maps that link those events together. Every stage of `Plan()` after request validation reads it, and most of them change it. When the Task planning tab says “the job method adds an edge” or “tray assignment fills the destination”, the thing being changed is a field of this object. Learning its eight fields once makes tabs 03–05 much easier to follow.

Key facts:

- **One per `Plan()` call.** `Plan()` creates it with `std::make_shared<PlanContext>(...)` right after the request passes validation, and it is freed when `Plan()` returns. Nothing in it survives to the next request; the only output is the `PlanResponse` built from it.
- **Shared, not copied, with one exception.** Every stage receives the same `PlanContextSPtr` (`std::shared_ptr<PlanContext>`). Passing the pointer by value copies the pointer, so all stages edit one object ([section 9](#bg-objects-ownership-and-lifetimes) explains why `const` methods can still do that). The exception is the job loop, which copies `*ctx` before each job and assigns the copy back when the expansion fails ([section 10](#bg-one-plan-call-step-by-step)).
- **A plain bag of public fields.** It is a `struct` in its own header, `include/scheduler/plan_context.hpp` (`:24`–`:76`), in namespace `volley::scheduler`, and it enforces no invariants. Five small helper methods exist; everything else is direct field access (`ctx->event_dag.AddDependency(...)`).

![PlanContext anatomy](figures/61_schedule_context_anatomy.svg)

`PlanContext`, field by field. Left: `Plan()` owns the `shared_ptr` and hands the same pointer to every stage. Centre: the fields in four groups, and the helper methods. Right: the types the fields hold. `initial_state`, `event_dag` and `scheduled_jobs` are held by value; the two bookkeeping maps hold `shared_ptr`s to events that also live in `event_dag`, so a map entry and the DAG vertex are the same object.

### The definition, annotated

The definition is short, and reading it field by field is the quickest way to understand what a planning attempt carries. The declaration below is the real one, in its real order, with this guide's comments marking four groups; the table that follows records who sets and who reads every field.

``` cpp
// include/scheduler/plan_context.hpp:24 (the helper methods are shown further below)
namespace volley::scheduler {

struct PlanContext {
  PlanContext(
      const interfaces::msg::Guid& request_id, DiscreteGarageState initial_state, const rclcpp::Time& now) :
      request_id(request_id),                                   // the PlanRequest's id
      initial_state(std::move(initial_state)),                  // moved in: Plan() built and adjusted it
      start_time(std::chrono::nanoseconds(now.nanoseconds())) { }   // time the request arrived

  // ---- identity ------------------------------------------------------------------------------
  interfaces::msg::Guid request_id;        // only used to name DAG dumps (debug/printdags)
  // ---- fixed inputs: written at the start of Plan(), then only read ----------------------------
  DiscreteGarageState initial_state;       // garage at request time, with base_schedule users disabled
  Interval::Timepoint start_time;          // t = 0 for PlanMotions' trajectories
  std::unordered_map<CollisionEntityId_t, GraphFilterProperties> keep_out_filter_by_footprint;
                                           // which graph vertices and edges each footprint may not use
  // ---- the plan being built ---------------------------------------------------------------------
  ScheduleEventDag event_dag;              // the event DAG ("Directed acyclic graphs"); grows in every stage
  std::vector<interfaces::msg::ScheduledJobData> scheduled_jobs;   // one entry per job that planned;
                                                                   //   index = job_index
  // ---- bookkeeping: links between events -------------------------------------------------------
  std::unordered_map<interfaces::msg::GarageEntityId, ScheduleEventSPtr> last_event_by_entity;
                                           // last event that touched each AGV/tray/bay/VECS
  std::unordered_map<uint16_t, ScheduleEventSPtr> first_event_by_tray;    // first move of each tray
};

using PlanContextSPtr = std::shared_ptr<PlanContext>;

}  // namespace volley::scheduler
```

PR \#1018 renamed three fields (`events` → `event_dag`, `last_entity_event` → `last_event_by_entity`, `first_tray_event` → `first_event_by_tray`), renamed `disabledness_filters` to `keep_out_filter_by_footprint`, deleted `request_id_str` and the two type aliases `CollistionFilterMap` and `GarageEntityEventMap`, and moved the type from `scheduler.hpp` into this header. The field names follow the naming catalogue ([section 15.4.2](#nm-schedulecontext)).

| Field                          | Type                                                                     | Group       | Set by                                                                                                                 | Read by                                                                                                                                                                             | What to remember                                                                                                                                                             |
|--------------------------------|--------------------------------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `request_id`                   | `interfaces::msg::Guid`                                                  | identity    | constructor                                                                                                            | `PrintDagIfEnabled`, in `Plan()` and `BuildActionGraph`                                                                                                                             | Only matters when DAG dumps are on (`is_dag_printing_enabled_`); `Plan()` copies the id into the response directly from the request                                          |
| `start_time`                   | `Interval::Timepoint`                                                    | fixed input | constructor, from `now`                                                                                                | `PlanMotions` (`ContinuousState(..., ctx->start_time)`)                                                                                                                             | The time origin of every trajectory in the response                                                                                                                          |
| `initial_state`                | `DiscreteGarageState`                                                    | fixed input | constructor (moved in)                                                                                                 | every job method, tray and AGV assignment, `ValidateEventSequence`, `PlanMotions`, VRC insertion                                                                                    | Never changed after construction; every stage that needs “the garage now” copies it and replays events ([section 14.4](#bg-every-job-sees-the-garage-through-working_state)) |
| `keep_out_filter_by_footprint` | `std::unordered_map<CollisionEntityId_t, GraphFilterProperties>`         | fixed input | `Plan()`, right after construction, via `BuildKeepOutFilters(motion_graph_, initial_state, collision_table_)`          | through `FindKeepOutFilter`: job methods and `ValidateMoveDestinationAndPath` (from `ValidateEventSequence`); the full list is in [section 11.4](#bg-where-the-reservation-is-read) | Answers “is this vertex unusable for this footprint because something is disabled?”                                                                                          |
| `event_dag`                    | `ScheduleEventDag`                                                       | plan        | job methods, tray assignment, AGV assignment, `RemoveRedundantEdges()`                                                 | every later stage                                                                                                                                                                   | The plan itself: vertices are `shared_ptr<ScheduleEvent>`, an edge u → v means u finishes first                                                                              |
| `scheduled_jobs`               | `std::vector<interfaces::msg::ScheduledJobData>`                         | plan        | `Plan()` via `AddScheduledJob` after each job that planned; `node_indices` written in place by `WriteJobActionIndices` | `ExpandJob` (its `size()` is the next `job_index`), `BuildActionDagFromMotions`, final response loop                                                                                | Entry k is the job whose events have `GetJobIndex() == k`, from expansion to the response                                                                                    |
| `last_event_by_entity`         | `std::unordered_map<interfaces::msg::GarageEntityId, ScheduleEventSPtr>` | bookkeeping | `ChainAfterLastEntityEvent` (rule A), usually through `AddChainedEvent`                                                | `ChainAfterLastEntityEvent`; rule C in `OrderAfterBayAndChargerEvents` (from `ExpandReparkTrayJob`)                                                                                 | Maintained only during job expansion                                                                                                                                         |
| `first_event_by_tray`          | `std::unordered_map<uint16_t, ScheduleEventSPtr>`                        | bookkeeping | tray assignment (`ChainTrayEvent`)                                                                                     | AGV assignment (`OrderAfterTraysOnPath`, from `ScheduleAgvMoveToPickup`)                                                                                                            | Empty until tray assignment; keyed by tray id                                                                                                                                |

### The four groups

**Identity** says which request this is; it only names the DAG dumps. The response keeps no absolute times, only each action's `duration`.

**Fixed inputs** are settled before any job is expanded. `initial_state` is the validated `base_state`, with every AGV, node, bay and VECS used by the already-running `base_schedule` marked disabled, that is, reserved ([section 11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)). `start_time` is the moment the request arrived: `PlanMotions` builds its `ContinuousState` from `initial_state` at `start_time`, so CHUGG's timeline starts there. `keep_out_filter_by_footprint` is the keep-out map built from `initial_state` ([section 11.5](#bg-disabledness-filters-the-keep-out-map)).

**The plan being built** is the output in progress. `event_dag` starts empty; job expansion adds intent, tray assignment adds blocker moves, AGV assignment adds approach, lift and lower events, and `RemoveRedundantEdges()` removes redundant edges. `scheduled_jobs` lists the jobs that planned successfully, in request order, so that an event's `job_index` can be turned back into the job it belongs to.

**Bookkeeping** maps hold pointers into `event_dag` so that a stage can find “the last event for this AGV” or “the first move of this tray” without searching the DAG. They point at the same objects as the DAG (`shared_ptr` copies), so following a map entry gives you the actual vertex's event.

Of the eight fields, three link events and jobs together and are where most bugs hide: `scheduled_jobs`, which turns an event's `job_index` back into a job, and the bookkeeping maps that the job methods and assignment stages use to add edges. The rest of this section looks at them in detail.

### Job indices and bookkeeping maps

This section explains `scheduled_jobs`; the helper methods, three of which add edges while jobs are expanded (rules A and B; the Task planning tab defines all three edge rules in [section 15.5](#bg-where-the-edges-come-from)); and the two bookkeeping maps, `last_event_by_entity` and `first_event_by_tray`. It ends with the context's life cycle across one `Plan()` call and its gotchas.

### `scheduled_jobs` in detail

There are **two** vectors of `interfaces::msg::ScheduledJobData` in `Plan()`, and [Figure 23](#bg-fig-69_scheduled_jobs) tracks both:

- `ctx->scheduled_jobs`. `ctx` is a `PlanContextSPtr` (`std::shared_ptr<PlanContext>`), created at the top of `Plan()`. Its `scheduled_jobs` holds **only the jobs that planned successfully**, in request order. This is the internal table that turns an event's `job_index` back into a job.
- `response.scheduled_jobs`. `response` is the `interfaces::msg::PlanResponse` that `Plan()` declares as a local at its top and returns at the end; `SchedulerRos` copies it into the service response. Its `scheduled_jobs` is the output list.

During the job loop each `request_data.pending_jobs[i]` goes to **exactly one** of the two: to `ctx->scheduled_jobs` if its expansion succeeds, to `response.scheduled_jobs` (via `MakeFailedJob`) if it fails. After motion planning, the final loop copies every planned entry into `response.scheduled_jobs` as well, so the response ends with every job, failures first.

“Expanding” a job means `ExpandJob` calling its job method, `Expand<Type>Job(ctx, <job's arguments>, job_index)` (`ExpandRetrieveJob`, `ExpandInsertJob`, `ExpandReparkTrayJob`, ...). The method replays `ctx->event_dag` onto a copy of `initial_state` to find where everything is, then **adds new `ScheduleEvent`s and dependency edges directly into `ctx->event_dag`** (and updates `last_event_by_entity`). It returns only `stdx::Expected<void, JobFailure>`: nothing, or `{message, is_retryable}`. It does not touch either `scheduled_jobs` vector; `Plan()` does that from the return value.

![scheduled_jobs through one Plan() call](figures/69_scheduled_jobs.svg)

Four pending jobs through one `Plan()` call. Top: the three objects involved and their types (`request_data` is `Plan()`'s parameter, `ctx` the shared context, `response` the local response). Middle: one row per job. Each job method gets `job_index = ctx->scheduled_jobs.size()` and adds its events to `ctx->event_dag`; on success the job is pushed onto `ctx->scheduled_jobs`, on failure (B) the context is restored and `MakeFailedJob` pushes the job onto `response.scheduled_jobs` instead. B is not pushed to the context, so C gets the same index B had; since PR \#1018 B leaves no events that could look like C's. Bottom: after the loop, the action DAG is labelled through `scheduled_jobs[event->GetJobIndex()]`, `WriteJobActionIndices` fills `node_indices` in place, and the final loop marks each planned job `STATE_EXECUTING` and appends it to `response` after the failures.

Every `ScheduleEvent` stores a `job_index`, set when the event is constructed (`MakeTrayMove(job_index, ...)`). `ExpandJob` passes `ctx->scheduled_jobs.size()` as the `job_index` of the job it is about to expand, and `Plan()` pushes the job onto `scheduled_jobs` only if expansion succeeds. The job loop in [section 10](#bg-one-plan-call-step-by-step) shows both halves: the method is called with `ctx->scheduled_jobs.size()` as its `job_index`, and `AddScheduledJob(job)` runs only on success, after which `scheduled_jobs[job_index].job == job`.

So `scheduled_jobs[k]` is the job whose events carry `job_index == k`. Four places rely on that:

| Where                             | What it does with the index                                                                                                               |
|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Job methods                       | Stamp every event they create with their `job_index`; nested calls (`ExpandRetrieveJob` → `ExpandReparkTrayJob`) pass the same index down |
| Rule B, `OrderAfterJobLeafEvents` | Only links leaves whose `GetJobIndex()` equals the new event's                                                                            |
| Tray assignment                   | Builds every blocker move with the root move's `GetJobIndex()`, so blockers belong to the job they unblock                                |
| `BuildActionDagFromMotions`       | Labels each action with `ctx->scheduled_jobs[event->GetJobIndex()].job.guid`, which is how Dispatch learns which job an action serves     |

Three consequences:

- **Composite jobs share one index.** The repark inside a retrieve, and every blocker move tray assignment adds for it, report as part of the retrieve ([section 14.6](#bg-job-methods-are-built-from-a-few-shared-pieces)).
- **A failed job's index is reused, safely.** The failed job is not pushed, so the next job gets the same index. Before PR \#1018 the events a failed job left behind then appeared to belong to the next job ([section 14.18](#bg-gotchas-2), gotcha 1), and a `TODO(Joe)` in `FailJob` said it should remove them. `Plan()` now restores the context copied before the job, so no such events remain. `MakeFailedJob` only builds the response entry (`state = STATE_ERROR`, `note = message`, `retain_job = is_retryable`).
- **The correspondence holds to the end.** `WriteJobActionIndices` (`action_graph.cpp:487`) maps each job guid to its position in `scheduled_jobs` and appends each action's position to that entry's `node_indices`, in place. Before PR \#1018 `BuildScheduledActionsArray` rebuilt the vector from an `unordered_map` keyed by job guid, so the planned jobs reached the response in hash-map order; they now come back in request order, after the failed ones.

### The helper methods

`PlanContext` has five methods. Three of them add dependency edges to `event_dag` while jobs are expanded, one wraps a job, and one looks up a keep-out filter. The code below shows all five; note which edge rule each of `ChainAfterLastEntityEvent` and `OrderAfterJobLeafEvents` implements.

``` cpp
// include/scheduler/plan_context.hpp, inside PlanContext (comments are this guide's)

void AddScheduledJob(const interfaces::msg::SchedulerJob& job) {   // node_indices filled at the end
  scheduled_jobs.emplace_back().job = job;
}

// Rule A ("Where the edges come from", Task planning tab): chain events on the same garage asset, across jobs.
void ChainAfterLastEntityEvent(
    const interfaces::msg::GarageEntityId& entity, const ScheduleEventSPtr& event) {
  auto& last_event = last_event_by_entity[entity];
  if(last_event != nullptr) {
    event_dag.AddDependency(last_event, event);   // previous event -> new event
  }
  last_event = event;                             // new event is now the last
}

// Adds the event and applies rule A; a tray move without a tray yet has no entity and is only added.
void AddChainedEvent(const ScheduleEventSPtr& event) {
  event_dag.AddEvent(event);
  if(const auto entity = event->GetGarageEntityId()) {
    ChainAfterLastEntityEvent(*entity, event);
  }
}

// Rule B ("Where the edges come from", Task planning tab): the new event waits for every current leaf of the SAME job.
void OrderAfterJobLeafEvents(const ScheduleEventSPtr& event) {
  for(const auto& leaf : event_dag.GetLeafEvents()) {               // leaf = no outgoing edge
    if(leaf != event && leaf->GetJobIndex() == event->GetJobIndex()) {
      event_dag.AddDependency(leaf, event);
    }
  }
}

// The one way to read keep_out_filter_by_footprint: fails instead of inserting an empty filter.
[[nodiscard]] stdx::Expected<std::reference_wrapper<const GraphFilterProperties>> FindKeepOutFilter(
    CollisionEntityId_t collision_id) const {
  const auto it = keep_out_filter_by_footprint.find(collision_id);
  if(it == keep_out_filter_by_footprint.end()) {
    return stdx::Unexpected("No keep-out filter for footprint {}", collision_id);
  }
  return std::cref(it->second);
}
```

`ChainAfterLastEntityEvent` (was `UpdateLastEntityEvent`), `AddChainedEvent` (new in PR \#1018, which replaced a repeated add-then-chain pattern) and `OrderAfterJobLeafEvents` (was `UpdateLeafDependencies`, which took the job index as a second argument) are the only code in `PlanContext` that adds edges. The last two assume the event has already been added to `event_dag`; if it has not, `AddDependency` returns `false` and the edge is silently lost ([section 12.5](#bg-the-operations)). `AddChainedEvent` removes that trap for rule A. `interfaces::msg::GarageEntityId` is a ROS message holding an [asset type](#bg-term-asset-type) letter and an id; the code builds keys with `AgvId(id)`, `TrayId(id)`, `BayId(id)` and `VecsId(id)`.

### `last_event_by_entity` in detail

`last_event_by_entity` is a `std::unordered_map<interfaces::msg::GarageEntityId, ScheduleEventSPtr>`: for each AGV, tray, bay and VECS, the **last event added so far** that touches it. It exists for one purpose, rule A: when a job method adds an event for entity X, that event must wait for whatever X was last asked to do, even if a different job asked. Without it, two jobs that both move tray T19 could run in either order.

![last_event_by_entity during job expansion](figures/70_last_entity_event.svg)

The six events of the topological-ordering example, added in order. For each one the table shows the rule A lookup (an edge only when the key is already in the map), the rule B edges (current leaves of the same job), the rule C edge (a tray move into a bay waits for the bay's last event) and the map afterwards. The DAG below colours each edge by the rule that added it: only rule A links the two T19 moves of jobs 1 and 2.

How it is keyed, written and read:

- **Keys** are `interfaces::msg::GarageEntityId` values (asset type letter plus id) built with `AgvId(id)`, `TrayId(id)`, `BayId(id)`, `VecsId(id)`. `AddChainedEvent` takes the key from `event->GetGarageEntityId()`: a `TrayMove` gives its tray, an `AgvMove` its AGV, a `BayTransition` its bay, a `VecsTransition` its VECS. A `TrayMove` with no tray yet has no key (`std::nullopt`) and skips rule A.
- **Written** only by `ChainAfterLastEntityEvent(key, e)`, mostly through `AddChainedEvent(e)`: add the edge `last[key] → e` if `key` is present, then set `last[key] = e`. The entry always moves forward; nothing ever removes one.
- **Read** in two places: inside `ChainAfterLastEntityEvent` (rule A), and by rule C in `OrderAfterBayAndChargerEvents` (`job_expansion.cpp:68`, called from `ExpandReparkTrayJob`), which looks up `BayId(...)` / `VecsId(...)` and adds `last[bay] → tray_move` without updating the map (so the bay's chain is not moved forward by a tray entering it).

Why later stages do not use it: tray assignment adds blocker moves and AGV assignment adds approach, lift and lower moves, and neither calls `ChainAfterLastEntityEvent`. The map is therefore only correct while jobs are being expanded. Tray assignment keeps its own `last_event_by_tray` (in `TrayAssignmentState`, written by `ChainTrayEvent`) and AGV assignment its own `last_event_by_agv` (in `AgvAssignmentState`, written by `ChainAgvEvent`), each built from scratch as that stage walks the DAG. Reading `ctx->last_event_by_entity` after job expansion would give an answer that ignores every event those stages added.

### `first_event_by_tray` in detail

`first_event_by_tray` is a `std::unordered_map<uint16_t, ScheduleEventSPtr>`, keyed by tray id: for each tray that moves at all, **the first move that takes it off the node it started on**. It is the only hand-off between tray assignment and AGV assignment, and it answers one question for AGV assignment: “when is this tray gone from its starting node?”

![first_event_by_tray: why the first move](figures/71_first_tray_event.svg)

Left: tray assignment walks the tray moves in topological order and records each tray's first move (m1 for T15, m2 for T17); T15's second move m3 is chained after m1 through `last_event_by_tray` but does not change the map. Right: AGV-1 carries T15 out (m1), then drives through P15 to fetch X, and later carries T15 again (m3). Waiting for the first move is correct and harmless. Waiting for the last move would add m3 → approach, while AGV-1's own chain already has approach → … → m3: a cycle.

**Written** by tray assignment, in one file-local helper that every tray move it processes goes through (the main loop, `AssignDestinationAndUnblockingMoves` and the unblocking moves, four call sites), including the blocker moves it creates:

``` cpp
// Where: file-local in src/tray_assignment.cpp:28, called from AssignTrays and its helpers.
//   state -> TrayAssignmentState: the stage's working state, last_event_by_tray, occupancy_history
void ChainTrayEvent(
    PlanContext& ctx, TrayAssignmentState& state, uint16_t tray_id, const ScheduleEventSPtr& event) {
  if(const auto it = state.last_event_by_tray.find(tray_id); it != state.last_event_by_tray.end()) {
    ctx.event_dag.AddDependency(it->second, event);   // later move of the same tray: chain it
  }
  else {
    ctx.first_event_by_tray[tray_id] = event;          // the first move of this tray in the plan
  }
  state.last_event_by_tray[tray_id] = event;
}
```

**Read** by AGV assignment, in `OrderAfterTraysOnPath` (called from `ScheduleAgvMoveToPickup`), when an AGV has to drive to a tray it will carry:

``` cpp
// Where: Scheduler::OrderAfterTraysOnPath(PlanContext& ctx, agv, tray, move_to_tray, root_event) const,
//        src/agv_assignment.cpp:715 (comments abridged)
auto nav_path = FindPosePath(motion_graph_, agv.pose, tray.pose, cost_model_);   // the AGV's route to the tray
for(size_t path_index = 1; path_index < nav_path.size(); ++path_index) {
  const uint16_t path_node = nav_path[path_index].node_id;
  if(path_node == tray.pose.node_id) continue;                // the destination itself is fine
  for(const auto& [blocker_tray_id, blocker_tray] : ctx.initial_state.GetTrays()) {
    if(blocker_tray.pose.node_id != path_node) continue;       // a tray STARTED on this node
    auto it = ctx.first_event_by_tray.find(blocker_tray_id);
    if(it == ctx.first_event_by_tray.end()) break;             // it never moves: nothing to wait for
    if(!ctx.event_dag.WouldCreateCycle(it->second, root_event)) {
      ctx.event_dag.AddDependency(it->second, move_to_tray);  // drive through only after it left
    }
    break;
  }
}
```

Three details:

- **Starting nodes come from `initial_state`.** The map only knows when a tray *leaves* its original node. A tray that moves *onto* the AGV's path later is not covered by this rule; if that makes the route impossible, `ValidateEventSequence` rejects the plan ("Cannot find path ...", [section 18](#bg-reduce-and-sanitycheckevents)).
- **Why the first move, not the last.** Using the last move would create a cycle when the same AGV moves a tray more than once in one plan (the comment that said so went with PR \#1018's comment clean-up). The figure shows the case: the AGV that must wait is the same AGV that later moves the tray again.
- **The cycle check uses the root event.** `move_to_tray` has no children yet when the edge is added, so `WouldCreateCycle(first, move_to_tray)` would always say “safe”. The code asks about `root_event` (the tray move this approach leads to) instead, because `move_to_tray` will reach it through the task-chain edges added next (the lift, then the tray move itself).

### Life cycle across one `Plan()` call

Each field of the context is created, changed and read at particular steps of `Plan()`, and knowing which step touches which field makes the later tabs easier to follow. The figure maps fields against steps, and the numbered list then describes what each step does with the context.

![PlanContext lifecycle](figures/62_schedule_context_lifecycle.svg)

Which step of `Plan()` touches which field. Read along a row for one field's life, down a column for what one step reads and changes. `event_dag` is the only field that every step from job expansion to the response touches. `last_event_by_entity` is used only during job expansion, `first_event_by_tray` connects tray and AGV assignment, and `scheduled_jobs` is written during job expansion, given its `node_indices` when the action graph is built and copied into the response at the end.

The columns are the nine steps listed in [section 10](#bg-one-plan-call-step-by-step) (they are not the five pipeline stages). What each step does with the context:

1.  **Construct.** `request_id`, `start_time` and `initial_state` are set; `event_dag`, `scheduled_jobs` and the maps start empty.
2.  **Filters.** `keep_out_filter_by_footprint` is computed from `initial_state`.
3.  **Job expansion** ([section 14](#bg-job-expansion-from-jobs-to-events)). For each pending job: copy the context; copy `initial_state`, replay `event_dag` to get `working_state`, add events, add edges through rules A, B and C, then push the job onto `scheduled_jobs`, or restore the copied context if the expansion failed.
4.  **Tray assignment** ([section 16](#bg-tray-assignment-dotrayassignments)). Copies `initial_state`, walks `event_dag` in topological order, fills blank fields, adds blocker moves and edges, and records `first_event_by_tray`.
5.  **AGV assignment** ([section 17](#bg-agv-assignment-doagvassignments)). Copies `initial_state`, matches AGVs, adds AGV events and edges, using `first_event_by_tray` to wait for blocking trays to leave.
6.  **Remove redundant edges and check** ([section 18](#bg-reduce-and-sanitycheckevents)). `event_dag.RemoveRedundantEdges()` drops redundant edges; `ValidateEventSequence` replays the DAG on a copy of `initial_state` and checks each move with `ValidateMoveDestinationAndPath`, which reads `keep_out_filter_by_footprint`.
7.  **Motion planning** ([section 19](#bg-motion-planning-and-the-response)). `PlanMotions` builds timed trajectories from `initial_state`, `start_time` and `event_dag`.
8.  **Build the action graph** ([section 6.2](#ad-how-the-action-dag-is-built)). `BuildActionGraph` turns trajectories into action nodes, labels them through `scheduled_jobs`, and writes each entry's `node_indices`.
9.  **Fill the response.** `Plan()` copies each `scheduled_jobs` entry into `response.scheduled_jobs` with state `STATE_EXECUTING`. Then `ctx` goes out of scope and the context is freed.

### Gotchas

Because `PlanContext` enforces no invariants, its correct use depends on conventions that the compiler does not check. The list below records the pitfalls that follow from this, including fields that are valid only during certain stages.

- **`last_event_by_entity` is stale after job expansion.** Tray and AGV assignment add many events (blocker moves, AGV moves, lifts) without updating it. Code in those stages that needs “the last event of X” keeps its own map instead (`last_event_by_tray` in `TrayAssignmentState`, `last_event_by_agv` in `AgvAssignmentState`). Do not read `ctx->last_event_by_entity` after job expansion.
- **`first_event_by_tray` is empty until tray assignment.** A job method that read it would always find nothing.
- **Read `keep_out_filter_by_footprint` through `FindKeepOutFilter`.** `operator[]` on the map would insert a default-constructed `GraphFilterProperties` for a missing footprint, and such a filter reports every vertex and edge as **disabled** (its property maps are empty and grow with `false` on access). Entries exist only for `AGV`, `TRAY` and the footprint of each tray in `initial_state` (`BuildStaticObstacleFilters`). Before PR \#1018 every lookup used `operator[]`; `FindKeepOutFilter` fails with “No keep-out filter for footprint …” instead, and the charger search now finds no charger without its filter.
- **Nothing is `const`, nothing is private.** Any function with the pointer can change `initial_state` or `scheduled_jobs`. The code base keeps to the conventions above, but the compiler does not check them. The refactor proposal (sections [6.1](#pr-the-new-pieces-and-how-they-fit-together) and [6.5](#pr-why-return-a-result-and-how-it-is-applied)) narrows this for tray assignment by passing `const` references and returning a result.
- **A failure inside a stage leaves partial changes, except in job expansion.** A failed expansion is undone by restoring the context copied before it. That copy shares the event objects, so it is enough only because expansion never changes an event it did not create; a future expansion that edits an earlier job's event would break that. Tray or AGV assignment failing halfway leaves `event_dag` partly edited; `Plan()` handles that by failing every job and returning, so the half-edited context is simply discarded.

## Packages, build system and dependencies

The `scheduler` package builds a shared library, a ROS component with its executable, a static test-support library and one test binary per test file. The table lists each target and the sources it is built from; the dependencies declared in `package.xml` follow it.

| Target                                                | Built from                                                                                                                                                                                                | Notes                                                                                                                             |
|-------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `scheduler` (shared library)                          | `src/scheduler.cpp`, the five stage files (`job_expansion.cpp`, `tray_assignment.cpp`, `agv_assignment.cpp`, `validation.cpp`, `action_graph.cpp`), `bay_rebalancing.cpp`, `move_events.cpp`, `utils.cpp` | Everything the tests link against                                                                                                 |
| `scheduler_component` (+ executable `scheduler_node`) | `src/scheduler_component.cpp`, `src/scheduler_ros.cpp`                                                                                                                                                    | Plugin `volley::SchedulerComponent`                                                                                               |
| `scheduler_test_support` (static library)             | `test/src/initial_states.cpp`, `test/src/scenarios/*.cpp`                                                                                                                                                 | Loads, reads and records the scenario files; links `yaml-cpp`, GoogleTest and the library; compiled with `SCHEDULER_SCENARIO_DIR` |
| gtests (19 binaries)                                  | one per file under `test/src/stages/` (5), `test/src/jobs/` (10) and `test/src/utils/` (4), named after the file (`retrieve_job_tests`, `tray_assignment_tests`, …)                                       | Each links `scheduler_test_support`; 240 s timeout each                                                                           |

`package.xml` lists these dependencies: `common`, `common_ros`, `cost_functions`, `interfaces`, `motion_planner`, `planner_core`, `task_planner`, `vrc_interfaces`, `rclcpp`, `rclcpp_components`, `rclcppx`, `std_srvs`, `stdx`, `backward_ros` and Boost, and for the tests `site_config` (the layouts) and `yaml-cpp`. The build uses ROS 2 `ament_cmake` with the repository's `volley_cmake` macros (`volley_package`, `volley_add_library`, `volley_add_component`, `volley_add_gtest`, `volley_ament_auto_package`). The dependency direction is `scheduler → planner_core, motion_planner, task_planner, cost_functions, common_ros`; nothing in the snapshots depends on `scheduler`. Of these, `planner_core`, `common_ros`, `motion_planner`, `cost_functions` and the interface packages are in the snapshots; `task_planner` (`BottleneckAssignment`), `common` and `stdx` are not.

### Source index

The list below indexes the source files of the `scheduler` package and the source snapshots under `sources/` from which the code in this study pack was read. Use it to locate the file that holds a class or function named elsewhere in the guide.

- `include/scheduler/scheduler.hpp`: `Scheduler`, `SchedulerParams` and the tray-assignment result types
- `include/scheduler/plan_context.hpp`: `PlanContext`; `job_failure.hpp`: `JobFailure`, `Fail`; `format.hpp`: `std::formatter`s for error texts
- `src/scheduler.cpp`: constructor, `Plan()`, `ExpandJob`, `PlanMotions` and the shared layout queries
- `src/job_expansion.cpp`, `src/tray_assignment.cpp`, `src/agv_assignment.cpp`, `src/validation.cpp`, `src/action_graph.cpp`: one file per stage
- `include/scheduler/bay_rebalancing.hpp`, `src/bay_rebalancing.cpp`: bay classification and rebalancing
- `include/scheduler/move_events.hpp`, `src/move_events.cpp`: `MakeAgvPoseMove`, `MakeTrayMove`
- `include/scheduler/utils.hpp`, `src/utils.cpp`: base-state validation, state and heading helpers
- `include/scheduler/scheduler_ros.hpp`, `src/scheduler_ros.cpp`, `src/scheduler_component.cpp`: ROS wiring and parameters
- `test/src/{stages,jobs,utils}/*_tests.cpp`: 99 tests; `test/scenarios/`: their scenario and initial-state YAML files; `test/include/scheduler/test/`, `test/src/scenarios/`: the support library
- `tools/view_scheduler_tests`, `tools/plan_viewer/`: the scenario viewer
- `CMakeLists.txt`, `package.xml`: targets and dependencies
- `sources/repomix-scheduler.xml`: the snapshot the files above were read from (sources, headers, tests and initial states; not the plan scenario files or the viewer)
- `sources/repomix-planner-core.xml`: `planner_core`, the event classes and the event DAG
- `sources/repomix-common-ros.xml`: `common_ros`, the garage state, layout, pose graph, garage graph and collision table
- `sources/repomix-motion-planner.xml`: `motion_planner`, CHUGG, SIPP and the safe-interval table, `ContinuousState`, `Trajectory`, the single-agent searches and static filters
- `sources/repomix-cost-functions.xml`: `cost_functions`, the trapezoid model, `MotionCostModel` with its parameter defaults, motion runs
- `sources/repomix-interfaces.xml`: every `.msg` and `.srv` of `interfaces`, `vrc_interfaces`, `bay_interfaces` and `agv_interfaces`
- `sources/5675_pecos_combined.yaml`: coordinates, node metadata and edges for the Pecos figures

## Debugging and testing

Several tools help when a plan is wrong or a change needs checking: logging, DAG dumps, the cost audit, the scenario tests and their viewer. The list below describes each, and the commands that follow build the package and run its tests.

- **Logs.** Since PR \#1018 the scheduler logs little: every error as an ERROR, each failed job as a WARN (“Failed job: … with message: …”), and the cost audit. The narration (the initial DGS, each job as it was planned, the topological orders, every trajectory at DEBUG) is gone, so a failing plan is read from the job's `note` and the ERROR lines. Logging goes through rclcppx's `LOG_*` macros with `std::format` arguments. CHUGG (in `motion_planner`) still logs the events it plans at INFO.
- **DAG pictures.** Call the `debug/printdags` service (or set the `printdags` parameter) to log the event DAG after tray and after AGV assignment, and the action DAG after each step of `BuildActionGraph` (`PrintDagIfEnabled`); it needs `libgraph-easy-perl`.
- **Cost audit.** `scheduler.cost_audit` (default `true`) prints a CSV breakdown of CHUGG's cost per segment (`LogMotionCostAudit`): one row per AGV motion, wheel-turn gap, bay door, VECS and VRC event ([section 23.1](#bg-what-can-be-configured)). SIPP logs its goals when a search fails.
- **Tests.** 99 GoogleTest cases in 19 binaries, one binary and one test suite per file: `test/src/jobs/` (one file per job type, through `Plan()`), `test/src/stages/` (tray assignment, AGV assignment, assignment costs, the sanity check, scheduler state) and `test/src/utils/` (base-state validation, empty-tray count, bay rebalancing, the scenario YAML decoder). Since PR \#1007 every planning test is driven by a **scenario file**: `test/scenarios/plan/<suite>/<Name>.yaml` for a test through `Plan()` (50 files; `plan/retrieve_job/FromStall.yaml` for `RetrieveJob.FromStall`), `test/scenarios/task_planning/{tray_assignment,agv_assignment}/` for a test of one stage, whose DAG the test builds in code. A scenario names its garage in `test/scenarios/initial_states/<layout>/<name>.yaml`, on the sites `275_sunrise_b` (most), `5675_pecos_combined` and `38_gramercy` (EV chargers); two blocking-tray fallbacks still use the synthetic `tiny_lot`. The old `576_eccles` and `1355_fulton` layouts are no longer used. A test calls `scenarios::Plan()` (or `scenarios::Stage("tray_assignment")`) and asserts what the result must satisfy. Each file also holds a recorded part (`output`), what the scheduler produced when it was recorded; it is compared only with `SCHEDULER_CHECK_RECORDINGS=1`, which a refactor that must not change the output turns on. `SCHEDULER_TEST_LOG=1` shows the scheduler's log again. `~/volley/src/planner/scheduler/test/scenarios/README.md` describes the files. The [Verification](#doc-verification) tab maps every test to the stage it exercises.
- **Scenario viewer.** `src/planner/scheduler/tools/view_scheduler_tests` (with the modules in `tools/plan_viewer/`) renders every scenario, its garage, DAG and recorded response, into one standalone HTML page (default `artifacts/scheduler-tests.html`).

``` bash
colcon build --packages-up-to scheduler
colcon test --packages-select scheduler --ctest-args -R retrieve_job_tests
colcon test-result --verbose
SCHEDULER_CHECK_RECORDINGS=1 poe test-pkg scheduler    # also compare every recorded output
src/planner/scheduler/tools/view_scheduler_tests       # writes artifacts/scheduler-tests.html
```

A good first exercise: open `test/scenarios/plan/retrieve_job/FromStall.yaml` and its page in the viewer, run `RetrieveJob.FromStall` (`retrieve_job_tests`) under a debugger, break in `Scheduler::AssignTrays` and `Scheduler::AssignAgvs`, and print `ctx->event_dag` at each stop.

## C++ concepts and idioms in context

The scheduler relies on a small number of modern C++ idioms, and misreading one of them is a common source of confusion for readers new to the code. The table names each idiom, its meaning, where it appears in the scheduler and the pitfall to watch for.

| Idiom                                                    | Meaning                                                                                                                                                                              | Where you meet it                                                                                                                                                                                                                                                                                                 | Pitfall                                                                                                                                                                               |
|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `std::shared_ptr<T>`                                     | Shared lifetime                                                                                                                                                                      | DAG vertices, `PlanContextSPtr`, `LayoutSPtr`                                                                                                                                                                                                                                                                     | Copying a DAG aliases the same events                                                                                                                                                 |
| `std::optional<T>`                                       | A value that may be missing                                                                                                                                                          | `TrayMove::GetDest()`, every `GetTray(id)`                                                                                                                                                                                                                                                                        | `.value()` throws if empty; many call sites assume it is set                                                                                                                          |
| Structured bindings                                      | Unpack a pair / struct                                                                                                                                                               | `auto [success, message] = event->ApplyTo(state)` (a `BoolStringPair`); `const auto& [message, is_retryable] = expansion.error()` (a `JobFailure`)                                                                                                                                                                | `success` here is the event's result, not `PlanResponse.success`                                                                                                                      |
| `stdx::Expected<T, E>`, `stdx::Result`                   | A value or an error (`std::expected`-style; `stdx::Result` is the `void` case with a `std::string` error). `stdx::Unexpected("fmt {}", args...)` builds the error with `std::format` | Every stage and helper (`AssignTrays`, `AssignAgvs`, `ValidateEventSequence`, `RemoveRedundantEdges`, `ApplyEventsTo`); `stdx::Expected<void, JobFailure>` for each `Expand<Type>Job`; `stdx::Expected<std::vector<ActionNode>>` from `BuildActionGraph`. Replaced `BoolStringPair` in the scheduler in PR \#1018 | All are `[[nodiscard]]`; test with `if(!result)`, read `result.error()`. `stdx` is not in the snapshots                                                                               |
| `JobFailure`, `Fail(...)`                                | A job expansion's error: `{message, is_retryable}`; `Fail("fmt {}", args...)` returns `stdx::Unexpected(JobFailure{std::format(...)})`                                               | `job_failure.hpp`; every `Expand<Type>Job`. `is_retryable` becomes the job's `retain_job`                                                                                                                                                                                                                         | `Fail` always sets `is_retryable = false`; a retrieve that may be retried builds the `JobFailure` itself                                                                              |
| `std::format`, `std::formatter`                          | Type-safe string formatting (C++20)                                                                                                                                                  | Error texts and log messages (`LOG_ERROR(logger_, "{}", ...)`); `format.hpp` specialises `std::formatter` for `GaragePose`, `Guid` and `GarageEntityId`                                                                                                                                                           | A type without a formatter does not compile in a format string; older code still uses `std::to_string`                                                                                |
| `BoolStringPair`                                         | `std::pair<bool, std::string>` (from `common`)                                                                                                                                       | Still returned by `ScheduleEvent::ApplyTo` and `DiscreteGarageState::OnEvent`                                                                                                                                                                                                                                     | Nothing forces a caller to check it; the scheduler turns it into a `stdx::Result` at once                                                                                             |
| `virtual` / `dynamic_cast`                               | Runtime polymorphism and checked downcast                                                                                                                                            | `ScheduleEvent` and subclasses                                                                                                                                                                                                                                                                                    | Check `GetType()` first, as the code does                                                                                                                                             |
| `std::variant` / `std::visit` / `std::holds_alternative` | One of several alternatives                                                                                                                                                          | `AgvMove` holds a lift **or** a pose change                                                                                                                                                                                                                                                                       | Lift changes have no destination (`GetDest()` empty)                                                                                                                                  |
| Generic lambda, `auto&&`, trailing return type           | A lambda template; a forwarding reference; an explicit return type                                                                                                                   | `[this, &state](auto&& arg) -> BoolStringPair { ... }` in `AgvMove::ApplyTo` ([section 15.3](#bg-inside-agvmove-apply))                                                                                                                                                                                           | All `std::visit` branches must return the same type                                                                                                                                   |
| Overloaded member functions                              | Same name, chosen by argument type at compile time                                                                                                                                   | `DiscreteGarageState::OnEvent`, 20 overloads ([section 15.4](#bg-what-onevent-is))                                                                                                                                                                                                                                | A message with no overload does not compile; a `using` alias (`TrayPoseChangedMsg`) picks the aliased overload                                                                        |
| `const` member functions                                 | Cannot modify `*this`                                                                                                                                                                | Every planning method                                                                                                                                                                                                                                                                                             | Can still modify `*ctx` through a pointer                                                                                                                                             |
| `std::atomic<float>`                                     | A member several threads read and write                                                                                                                                              | `target_insert_ready_bay_fraction_`, changed by the `set_bay_readiness_ratio` service                                                                                                                                                                                                                             | `const` does not mean thread-safe here: `GenerateNextActionGuid` uses a plain static counter                                                                                          |
| `std::function` members + `friend`                       | Injected callbacks                                                                                                                                                                   | `*_request_fn_` set by `SchedulerRos`                                                                                                                                                                                                                                                                             | Empty in unit tests; the code checks before calling                                                                                                                                   |
| Templates                                                | Generic code                                                                                                                                                                         | `Dag<T>`, `GarageOccupancyChecker<T>`                                                                                                                                                                                                                                                                             | `Dag` is also used with `T = interfaces::msg::ActionNode` and `T = uint16_t`; `GarageOccupancyChecker` with `shared_ptr<ScheduleEvent>` and `shared_ptr<interfaces::msg::ActionNode>` |
| ROS IDL types                                            | Generated structs                                                                                                                                                                    | `interfaces::msg::PlanRequest` in the scheduler; `...Msg` aliases (`GaragePoseMsg`) in `common_ros`, `planner_core` and `motion_planner`                                                                                                                                                                          | Field names are a wire contract                                                                                                                                                       |

## Reading the C++ code: a call trace and a route through the source

This section is for the moment you open the code. It shows **who calls whom, in what order**, with the signature and the file and line of every function, so you can jump straight to it.

### How to read the call-trace figures

The two call-trace figures in this section show, row by row, which functions run during start-up and one `Plan()` call. The conventions listed below explain how time, call depth, location and loops are drawn, and should be read before the figures themselves.

- **Time runs downwards.** Row 12 happens after row 11.
- **Indentation is call depth.** A row indented under another is called *from* it. The grey line under a call runs down past all the calls it makes, like the bars in a flame chart turned on their side.
- **Each row is one function.** The box holds its signature (as written in the source, long parameter lists shortened with `...`) and a one-line note. The right column gives **where it is defined** (`file:line`) and **where it is called from**.
- **Colours say where the code lives.** Teal for the ROS layer, blue for `Scheduler` methods, light blue for file-local free functions, green for `PlanContext` (`plan_context.hpp`), violet for `utils.cpp`. Dashed grey boxes are in other packages (`planner_core`, `common_ros`, `motion_planner`, `task_planner`); of these, only `task_planner` is not in the snapshots.
- **Amber "loop:" rows** mark loops; the calls under them repeat.

Line numbers are those of `main` at `a468657f`, the files inside `sources/repomix-scheduler.xml`. Since PR \#1018 the `Scheduler` methods are spread over `scheduler.cpp` and the five stage files, so a `file:line` names the file as well. If your branch has moved on, search for the signature instead of trusting the number.

![Call trace: start-up and one Plan() call](figures/39_call_trace_plan.svg)

Start-up (rows 1–10) and one `/plan` request with a single RETRIEVE job (rows 11 onward), success path only. `AssignTrays` and `AssignAgvs` are collapsed here and expanded in the next figure.

![Call trace: tray and AGV assignment](figures/39_call_trace_assignment.svg)

Inside `AssignTrays` and `AssignAgvs`, with the helpers in the order they are first called.

### Where to start: a reading route

Read in this order. Each step is small enough for one sitting and builds on the one before. Steps 1–3 and 9 need only this tab; steps 4–6 follow the Task planning tab, step 7 also the Motion planning and Action graph tabs, step 8 the Task planning and Action graph tabs, and step 10 the Motion planning tab.

| \#  | Read                                                                       | Where                                                                                                                                                                                                                                                                                                                       | What to look for                                                                                                                                                                                               |
|-----|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | `PlanContext` and the `Scheduler` class declaration                        | `plan_context.hpp:24`, `scheduler.hpp:71`                                                                                                                                                                                                                                                                                   | The per-call state ([section 7](#bg-schedulecontext-the-per-call-workspace)) and the list of methods (the `private:` section, grouped by stage, starts at `scheduler.hpp:121`)                                 |
| 2   | Start-up wiring                                                            | `scheduler_component.cpp:33`, `scheduler_ros.cpp:23`                                                                                                                                                                                                                                                                        | Parameters (`ReadMotionCostParams`, `scheduler_component.cpp:10`), the `plan` service lambda (`scheduler_ros.cpp:44`), the `*_request_fn_` callbacks                                                           |
| 3   | `Scheduler::Plan`, then `ExpandJob`                                        | `scheduler.cpp:138`–`249`, `:251`                                                                                                                                                                                                                                                                                           | The whole pipeline in one function: validation, the job loop (`:159`), the stage calls (`:192`–`:226`), every early return                                                                                     |
| 4   | One job method, then the workhorse                                         | `job_expansion.cpp`: `ExpandRetrieveJob` `:167`, `ExpandReparkTrayJob` `:247`                                                                                                                                                                                                                                               | Section [14.11](#bg-type_retrieve--planretrievejob) and [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) side by side with the code                                                          |
| 5   | Tray assignment                                                            | `tray_assignment.cpp`: `AssignTrays` `:42`, then `AssignDestinationAndUnblockingMoves` `:398`, `ResolveBlockingTrays` `:509`                                                                                                                                                                                                | [Section 16](#bg-tray-assignment-dotrayassignments); the blocking-tray `while` loop (from `:134`) is long, read its comments first                                                                             |
| 6   | AGV assignment                                                             | `agv_assignment.cpp`: `AssignAgvs` `:100`, then `AssignAgvToTrayMove` `:290`, `ScheduleAgvMoveToPickup` `:526`, `OrderAgvMovesAfterBlockingAgvs` `:370`                                                                                                                                                                     | [Section 17](#bg-agv-assignment-doagvassignments); the `while` loop at `:123` is the core                                                                                                                      |
| 7   | The last stages                                                            | `ValidateEventSequence` `validation.cpp:18`, `PlanMotions` `scheduler.cpp:287`, `BuildActionGraph` `action_graph.cpp:501` and its helpers `:35`–`:499`                                                                                                                                                                      | Sections [18](#bg-reduce-and-sanitycheckevents), [21](#bg-chugg-the-motion-planner) and [25](#ad-how-the-action-dag-is-built)                                                                                  |
| 8   | Utilities                                                                  | `utils.cpp`: `ValidateBaseState` `:12`; `bay_rebalancing.cpp` `:14`–`:189`; `InsertVrcActionsIntoDag` `action_graph.cpp:76`                                                                                                                                                                                                 | [Section 20](#bg-bays-vecs-and-vrcs) (bays); [section 6.3](#bg-vrcs-lifts-between-floors) (VRC commands)                                                                                                       |
| 9   | The event classes and the DAG (`planner_core`)                             | `schedule_events.hpp`: `ScheduleEvent` `:31`, `TrayMove` `:96`; `schedule_events.cpp`: `TrayMove::ApplyTo` `:130`; `event_dag.hpp`: `Dag` `:23`, `ScheduleEventDag` `:366`; `event_dag.cpp`: `GetTopologicalOrdering` `:51`                                                                                                 | Sections [11](#bg-event-types-and-polymorphism) and [12](#bg-directed-acyclic-graphs-then-scheduleeventdag); `RemoveRedundantEdges` (`event_dag.hpp:243`) and `Remove` (`:76`) have the comments worth reading |
| 10  | The motion planner and the cost model (`motion_planner`, `cost_functions`) | `chugg_common.cpp` (`InitializeEventOrder`, `MakeRootNode`, `GetDependencyCompletionTime`), `chugg_sequential.cpp` (`PlanNodeSequential`, `SetEventSafeIntervals`), `sipp_agv.cpp`, `safe_interval_path_planning.cpp` (`GetNeighbors`), `continuous_state.cpp`; `motion_cost_model.cpp`, `cost_functions.cpp` (`Trapezoid`) | Sections [21](#bg-chugg-the-motion-planner), [23](#bg-timing-parameters-and-the-cost-model) and [24](#bg-continuousstate-the-timeline); read `chugg.hpp`'s member list first                                   |

Where things are in `scheduler.cpp` (384 lines; it held all of the package's planning code, 4 202 lines, before PR \#1018). The other files' functions are listed, in file order, in [section 10](#bg-one-plan-call-step-by-step):

| Lines   | Contents                                                                                                                                                  |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| 27–84   | File-local helpers: `ExcludeCommittedResources`, `FindPayloadDeliveryAction`, `LogMotionCostAudit`                                                        |
| 86–136  | Constructor, `StorePreferredPayloadHeadingsForRetrieval`                                                                                                  |
| 138–249 | `Plan`                                                                                                                                                    |
| 251–285 | `ExpandJob`, the dispatch to the job methods in `job_expansion.cpp`                                                                                       |
| 287–312 | `PlanMotions`                                                                                                                                             |
| 314–342 | `MakeFailedJob`, `SetBayReadinessRatioCallback`                                                                                                           |
| 344–382 | Layout queries several stages use (`MakeBayInboundPose`, `IsBayOdpAreaClear`, `IsParkingWithoutBayOrCharger`, `GetFirstSystemFloor`) and `GetVersionInfo` |

### Following the calls yourself

The figures and the reading route give a static view of the calls; tracing them in a running program confirms that view and shows the data at each step. The list below describes four practical ways to do this: a debugger on a test, editor navigation, text search and the DAG dumps.

- **Use a debugger on a test.** `TEST(RetrieveJob, FromStall)` (`test/src/jobs/retrieve_job_tests.cpp:22`, scenario `plan/retrieve_job/FromStall.yaml`) runs the same kind of request as [Figure 59](#bg-fig-39_call_trace_plan), through `Plan()`. `TEST(TrayAssignment, ThenAgvAssignment)` (`test/src/stages/tray_assignment_tests.cpp:126`) calls the two assignment stages directly. Put breakpoints on the rows of the figures and step.
- **Let the editor jump for you.** Build with `--cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON` and point clangd (or your IDE) at `build/compile_commands.json`; "go to definition" then also works into `planner_core` and `motion_planner`.
- **Search by name.** `rg -n "Scheduler::ExpandRetrieveJob\("` finds a definition; `rg -n "ExpandReparkTrayJob\(" src` lists every call site.
- **Turn on the DAG dumps.** The `debug/printdags` service ([section 22](#bg-debugging-and-testing)) prints the event DAG after tray and after AGV assignment, which shows what the calls in the second figure built.
