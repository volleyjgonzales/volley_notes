# 07 — Issue & proposal: the scheduler core refactor

This tab explains *what* the refactor changes and *why*, using the code in `sources/repomix-scheduler.xml` as evidence. It assumes the first four tabs: in particular the plan call and `ScheduleContext` (sections [10](#bg-one-plan-call-step-by-step) and [13](#bg-schedulecontext-the-per-call-workspace) of the [Background](#doc-background) tab), and tray and AGV assignment (sections [4](#bg-tray-assignment-dotrayassignments) and [5](#bg-agv-assignment-doagvassignments) of the [Task planning](#doc-task-planning) tab). Code snippets follow the conventions of the Background tab: every snippet says which class it lives in, what `this` is, and the type of each variable that is not obvious. Snippets marked **proposed** do not exist in the repository.

**How this tab is organised.** [Section 2](#pr-the-pipeline-the-refactor-works-on) places the ticket in that pipeline, sections [3](#pr-where-the-two-algorithms-sit-today)–[5](#pr-current-versus-target-responsibilities) describe the two algorithms and what moves where, [section 6](#pr-module-layout-folders-or-packages) decides how the code is organised by stage (folders or packages), and sections [7](#pr-target-architecture)–[14](#pr-next-actions) design the tray module and the naming boundary, list the invariants, risks and decisions, and lay out the staged plan. Two sections are future work beyond this ticket: [section 15](#pr-swappable-motion-planners) puts motion planning behind the same kind of interface as the tray and AGV solvers, and [section 16](#nm-proposed-future-work-naming) is a catalogue of renames and small struct refactors across the whole stack, of which this refactor adopts only the rows for `scheduler` and `planner_core`.

| Name in snippets                                     | Type                                                                                        | What it is                                                                                                                                                                          |
|------------------------------------------------------|---------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `this` inside `Scheduler::…`                         | `const volley::Scheduler*`                                                                  | The one `Scheduler` object, owned by `SchedulerRos` through `SchedulerSPtr` (`std::shared_ptr<Scheduler>`)                                                                          |
| `plan_ctx`, `ctx`                                    | `ScheduleContextSPtr` = `std::shared_ptr<ScheduleContext>`                                  | Per-`Plan()` scratch state: initial state, event DAG, job list, bookkeeping maps                                                                                                    |
| `ctx->events`                                        | `volley::ScheduleEventDag`                                                                  | The event DAG being built (Boost graph of `std::shared_ptr<ScheduleEvent>`)                                                                                                         |
| `ctx->initial_state`                                 | `volley::DiscreteGarageState`                                                               | Snapshot of the garage at request time; never mutated after `Plan()` builds it                                                                                                      |
| `working_state`                                      | `volley::DiscreteGarageState` (local copy)                                                  | `initial_state` with already-planned events applied, used to answer "where is everything *now*?"                                                                                    |
| `gg_`, `table_`, `cost_model_`, `layout_`, `logger_` | `GarageGraph`, `CollisionTable`, `cost::MotionCostModel`, `LayoutSPtr`, `rclcpp::Logger`    | `Scheduler` data members built once in the constructor                                                                                                                              |
| `stdx::Expected<T>`, `stdx::Result`                  | `tl::expected<T, std::string>`, `tl::expected<void, std::string>` (from the `stdx` package) | A value or an error message; `Result` is success or an error. Proposed replacement for `BoolStringPair` ([section 6.4](#pr-errors-stdxexpected-instead-of-boolstringpair))          |
| `svc`                                                | `const scheduler_core::GarageServices&` (**proposed**)                                      | Bundle of const references to `gg_`, `table_`, `cost_model_`, `*layout_` plus the logger, passed to every pure helper ([section 6.1](#pr-the-new-pieces-and-how-they-fit-together)) |

## Ticket and scope

**Parent Jira initiative:** **Scheduler Core Refactor** (parent key to be confirmed). **Specific tasks:** [SW2-484](https://volleyautomation.atlassian.net/browse/SW2-484) (tray solver interface, in progress), [SW2-769](https://volleyautomation.atlassian.net/browse/SW2-769) (scheduler package reorganization, marked done) and [SW2-487](https://volleyautomation.atlassian.net/browse/SW2-487) (tray benchmark set, To Do). The links follow the usual Jira URL pattern; the base domain and current status have not been verified. Related keys: SW2-677, SW2-652, SW2-593, SW2-488, SW2-496, SW2-514, SW2-663, SW2-18, SW2-686, SW2-776 and SW2-905. **Do not assume all of them block the refactor.**

**Objective:** move tray-move planning and AGV assignment out of large `Scheduler` methods and behind generic, swappable interfaces. Default implementations must reproduce current behaviour, and each solver needs at least **10 real-customer-layout scenarios** with recorded baseline performance. **Out of scope:** changes to CHUGG/SIPP motion planning, a new optimal solver, and adding to active schedules.

**Definition of Done:** two generic interfaces; two behaviour-equivalent default implementations; 10+ site-based benchmark scenarios per solver with saved baselines; every `Scheduler` assignment call site routed through the interfaces; old code paths removed. Source: Jira ticket text, October 2026. This describes the intended state, not the code today.

## The pipeline the refactor works on

The ticket's two algorithms are stages 2 and 3 of the five-stage pipeline the previous tabs walked through ([Figure 1](#bg-fig-01_pipeline)). This section looks at the pipeline from the refactor's side. The other three stages matter for the refactor because the code layout should follow the stages, and because each stage boundary is a natural interface: every stage hands the next one a data structure, not a call into its internals.

| Stage                                                                 | Standard name                                | Input → output                                    | Code today                                                                                                                                                  | Algorithms it calls                                                  |
|-----------------------------------------------------------------------|----------------------------------------------|---------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| 1 · Job expansion                                                     | task planning (decomposition and allocation) | jobs + garage state → event DAG with blanks       | 12 `Plan<Type>Job` members of `Scheduler`                                                                                                                   | searches from `motion_planner`                                       |
| 2 · Tray assignment **(ticket)**                                      |                                              | event DAG → blanks filled, blocker moves added    | `DoTrayAssignments` and helpers, members of `Scheduler`                                                                                                     | blocking-tray, open-space and empty-tray searches (`motion_planner`) |
| 3 · AGV assignment **(ticket)**, then `Reduce()` and the sanity check |                                              | event DAG → AGV events and edges added; final DAG | `DoAgvAssignments`, `SanityCheckEvents`, members                                                                                                            | `BottleneckAssignment` (`task_planner`), `GetPosePath`               |
| 4 · Motion planning                                                   | MAPF                                         | event DAG → `ContinuousState` (timed motions)     | `PlanMotions`, a member, about 60 lines                                                                                                                     | CHUGG (`motion_planner`)                                             |
| 5 · Action DAG                                                        | action dependency graph                      | `ContinuousState` + event DAG → `ActionNode[]`    | `ResponseFromTrajectories` (member) and five **free functions** in an anonymous namespace of `scheduler.cpp`; `InsertVrcActionsIntoDag` (free, `utils.cpp`) | —                                                                    |

Three facts from this table shape the proposal:

- **The algorithms of stages 4 and 5 are already separate.** CHUGG lives in `motion_planner`; the scheduler only adapts its inputs. The action-DAG code is already free functions: they take the context pointer, the layout and the logger as arguments and touch no `Scheduler` member. Only `ResponseFromTrajectories`, the member that calls them, reads members: the collision table and motion graph (for the occupancy checker), the layout, the cost model (for VRC actions) and `printdags_`. Moving them is cheap. The interface work is to pass those services explicitly, narrow the context argument to the three fields the helpers read (the event DAG, the job list, the initial state), and return the per-job action indices that `BuildScheduledActionsArray` writes into `ctx->scheduled_jobs` today.
- **Stages 1–3 are where the coupling is.** All three are `Scheduler` members that share private helpers and edit one context ([section 4](#pr-what-the-two-algorithms-touch)). This is the ticket's work, and the part that needs the solver interfaces.
- **Stages exchange data, not calls.** 1–3 pass the event DAG (`planner_core`), 4 passes a `ContinuousState` (`motion_planner`), 5 produces ROS messages. Each stage can therefore be built and tested on its own once its inputs are those types, which is what makes the module options in [section 7](#pr-module-layout-folders-or-packages) possible.

### Where the code will live

With the three stage folders of [section 6](#pr-module-layout-folders-or-packages), the code of today's `scheduler` package divides as follows (line counts from the snapshot, function code only; the [Background](#doc-background) tab, [Where the code is](#bg-where-the-code-is)):

![Where the code is, by pipeline stage](figures/96_code_by_stage.svg)

**Where the code is, by pipeline stage.** Solid segments are in the `scheduler` package and move into the stage folders; pale segments are in library packages and do not move. Measured on the snapshots, without tests.

| Destination                    | Lines today | Share of the package | Biggest pieces                                                                                                                                 |
|--------------------------------|-------------|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `task_planning/`               | about 3,590 | 78%                  | 12 job methods and `PlanOpenBayDoor` (about 1,060), `DoTrayAssignments` (560), `DoAgvAssignments` (365), the blocking-tray helpers (about 270) |
| `action_graph/`                | about 540   | 12%                  | VRC insertion (153), `ToActionNode` (105), the DAG-building helpers                                                                            |
| orchestrator (`scheduler.hpp`) | about 380   | 8%                   | `Plan` (291)                                                                                                                                   |
| `motion_planning/`             | 63          | 1%                   | `PlanMotions`; the CHUGG code it runs (about 3,870 lines) stays in `motion_planner`                                                            |

So nearly all of the refactored code lives in `task_planning/`, and nearly all of this ticket's work happens there too. Two consequences for the layout: `motion_planning/` is a thin adapter and should stay one (the algorithm already has a package), and `task_planning/` is big enough that its subfolders are the real modules. The boundary inside it that matters most is between **job expansion** (garage rules: what each job type needs) and the **assignment solvers** (algorithms: which tray, which AGV), which is exactly where this ticket puts its interfaces.

**It need not stay this lopsided, and some of it will not.** Each stage grows for its own reasons. Task planning grows with every new job type and site feature. Motion planning grows inside `motion_planner`, where an unfinished second solver (CBS, `chugg_cbs.cpp`) and some unused helpers already sit, about 660 lines the scheduler never calls. The action graph is small because it implements only the basic construction; execution features from the ADG literature, such as absorbing delays or switching the order of two robots at run time ([section 5](#ad-beyond-the-basic-adg)), would make it grow, and that is the main reason to give it its own folder now.

### Necessary and avoidable complexity in task planning

Task planning is expected to be the largest and most intricate stage. Its current size and shape, however, are not all necessary.

**Why it is expected to be the largest.** MAPF and the ADG are general algorithms with compact, well-studied formulations: their code knows about footprints, intervals and graphs, not about cars. Task planning is where the garage's own rules live: twelve job types, bay modes and readiness, VECS charging, parking headings, disabled nodes and size classes. (Floors and VRCs would belong here too, but task planning has no rule for them yet; see [section 7](#ly-vrc-support-status).) Its hardest part, moving blocking trays out of the way, is a rearrangement problem of the sliding-puzzle kind, whose optimal version is NP-hard in general. In multi-robot warehouse systems the domain layer is typically the largest one, and this code follows that pattern.

**What is not necessary.** The evidence in the code points to several sources of size and coupling that the problem does not require:

| Source                                                      | Evidence                                                                                                                                                                                                                                                | Remedy                                                                                                                                                             | When                                              |
|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| Very long functions                                         | `DoTrayAssignments` 560 lines, `DoAgvAssignments` 365, `Plan` 291: a quarter of the package in three functions, with the main loops' logic inline                                                                                                       | Pure helpers and solvers (sections [8.3](#pr-before-and-after-the-tray-call-tree), [8.7](#pr-agv-assignment-same-layout-and-error-type-now-returned-result-later)) | This ticket (C1–F)                                |
| Duplicated code                                             | Two copies of the move-emission code in the tray loop; the twelve job methods repeat a few patterns (the [Task planning](#doc-task-planning) tab, [Job methods are built from a few shared pieces](#bg-job-methods-are-built-from-a-few-shared-pieces)) | Merge the emission copies; build job methods from shared primitives                                                                                                | Emission: this ticket (C1). Job methods: after it |
| Everything is a member of `Scheduler` and edits one context | Helpers read `gg_`, `table_` and the bookkeeping maps directly ([section 4](#pr-what-the-two-algorithms-touch))                                                                                                                                         | `GarageServices`, read-only inputs, one writer per stage                                                                                                           | This ticket                                       |
| Decisions split across stages                               | Job expansion leaves tray ids and destinations blank and tray assignment fills them, so both replay `working_state` and both handle blocking trays                                                                                                      | Keep the split for parity; later, let expansion state a goal and the tray solver own the whole decision                                                            | After the ticket                                  |
| Repair passes after greedy choices                          | AGV path repair after matching (the [Task planning](#doc-task-planning) tab, [Repairing paths after assignment](#bg-repairing-paths-after-assignment)), `AddDepsAfterAmiga`, `Reduce()` run twice with an unexplained `TODO`                            | Turn each repair into an input constraint of the solver that caused it, once benchmarks can show the effect                                                        | After stage G                                     |
| Greedy, one job at a time                                   | Each job is expanded against the garage earlier jobs leave behind, with no search or backtracking, so every corner case needs its own rule                                                                                                              | A search- or optimisation-based tray and AGV solver behind the same interfaces ([section 14](#pr-evaluating-the-event-graph-strategy) evaluates the options)       | Out of scope (a later ticket)                     |

This ticket changes structure, not size: right after it, `task_planning/` will still hold about 3,500 lines, now split into modules with tests. The reductions come afterwards and are what the solver interfaces make possible: each row above can be done inside one module, checked against the parity fixtures and the stage G benchmarks, without touching the other stages.

## Where the two algorithms sit today

Both algorithms are `const` member functions of `Scheduler` that take the per-call context and edit it in place. They return `BoolStringPair` (`std::pair<bool, std::string>`: success flag plus a message). [Section 6](#pr-proposed-layout-and-api-for-tray-assignment) proposes replacing both habits: `stdx::Expected` instead of `BoolStringPair`, and a returned result instead of editing `ctx`.

``` cpp
// include/scheduler/scheduler.hpp — inside class volley::Scheduler (public section)
BoolStringPair DoTrayAssignments(ScheduleContextSPtr ctx) const;  // fills tray ids + destinations, adds blocker moves
BoolStringPair DoAgvAssignments(ScheduleContextSPtr ctx) const;   // picks AGVs, adds approach/lift/lower events
```

`const` here only means the methods do not change `Scheduler`'s own members. The real output is the mutation of `*ctx`, which the `shared_ptr` lets them reach. They are called from the middle of `Scheduler::Plan`:

``` cpp
// src/scheduler.cpp — PlanResponseMsg Scheduler::Plan(const PlanRequestMsg& request_data, const rclcpp::Time& now) const
// this     : const Scheduler*  (the Scheduler that SchedulerRos owns)
// plan_ctx : ScheduleContextSPtr, created earlier in Plan() from the request's garage state
// result   : PlanResponseMsg being built; result.scheduled_jobs is std::vector<ScheduledJobDataMsg>
//   ...every pending job has already been expanded into events by a Plan<Type>Job method...

auto [success, message] = DoTrayAssignments(plan_ctx);   // same as this->DoTrayAssignments(plan_ctx)
if(!success) {
  result.success = true;                                 // the *call* succeeded...
  result.message = "Failed tray assignments: " + message;
  for(const auto& job : request_data.pending_jobs) {     // ...but every pending job is reported failed
    result.scheduled_jobs.push_back(FailJob(job, message));
  }
  return result;
}
std::tie(success, message) = DoAgvAssignments(plan_ctx); // same failure handling as above
// ...then plan_ctx->events.Reduce(), SanityCheckEvents(plan_ctx), PlanMotions(...)
```

Two consequences matter for the refactor:

- **Failure is all-or-nothing.** If either algorithm fails, every pending job fails with the same message, and `success` stays `true`. A new solver must keep that contract or `SchedulerRos` clients will see different responses.
- **Tests already call the algorithms directly.** `test/scheduler_tests.cpp` calls `scheduler.DoTrayAssignments(ctx)` 4 times, `scheduler.DoAgvAssignments(ctx)` 9 times and `scheduler.ResolveBlockingTrays(...)` once. They build a whole `Scheduler` from a layout file to do so:

``` cpp
// test/scheduler_tests.cpp — TEST(Scheduler, ...) ; all objects are locals of the test body
Scheduler scheduler(layout_filepath, logger, params);  // loads the layout, builds gg_, table_, cost_model_
ScheduleContextSPtr ctx = std::make_shared<ScheduleContext>(request_id, state, rclcpp::Time());
auto tray_move = std::make_shared<TrayMove>(0u);       // job_index 0; no destination set
tray_move->SetTrayId(1);
ctx->events.AddEvent(tray_move);                       // hand-built one-event DAG
std::tie(success, msg) = scheduler.DoTrayAssignments(ctx);
```

That pattern is the baseline the refactor improves on: after the change, a test should be able to construct the solver with only the services it needs.

## What the two algorithms touch

[Figure 1](#pr-fig-34_coupling_matrix) is generated from `scheduler.cpp`. Each row is one `Scheduler` method in the tray or AGV call tree. Each column is something its body uses. The right-hand column lists callers outside the two trees: those are the helpers you cannot simply move.

![What the two algorithms touch](figures/34_coupling_matrix.svg)

**Coupling of the tray and AGV call trees.** Filled dots mark a token found in the method body (comment-stripped). A helper that receives the DAG as a parameter rather than through `ctx` shows no `events` dot even though it edits the DAG, so read the dots as "uses directly", not "is independent of".

What the matrix tells you:

1.  **Both trees need the same three services.** `gg_` (graph search), `table_` (collision checks) and `cost_model_` (travel times) appear throughout. `layout_` is used mainly for node types and headings. All four are read-only after construction, which makes constructor injection by `const&` safe as long as the `Scheduler` outlives the solver.
2.  **The tray tree touches three context fields:** it edits `ctx->events`, reads `ctx->initial_state`, and fills `ctx->first_tray_event` (the first move of each tray, keyed by tray id `uint16_t`). The AGV tree reads `first_tray_event` back inside `MoveAgvToTrayPose`. That map is the hand-off between the two solvers and must be part of both contracts.
3.  **Five helpers are shared with job planning.** They must stay reachable from `Scheduler` (or move to a shared utility) after the algorithms leave:

| Helper (all `Scheduler` members) | Also called by                        | Why                                                                                 |
|----------------------------------|---------------------------------------|-------------------------------------------------------------------------------------|
| `ResolveBlockingTrays` (public)  | `PlanChargePayloadJob`, one test      | Finds a VECS node plus unblocking moves when the requested node is not a ready VECS |
| `AssignTrayIdForEmptyMove`       | `PlanReadyForInsertJob`               | Picks an empty tray early, best-effort                                              |
| `UsePreferredHeading`            | `PlanAgvMoveJob`, `PlanReparkTrayJob` | Chooses the parking heading that makes later retrieval fastest                      |
| `UseEvChargeHeading`             | `PlanChargePayloadJob`                | Heading for a VECS node                                                             |
| `GetJustMovingCost`              | `PlanAgvChargeJob`, tests             | Travel-time estimate for an AGV between two poses                                   |

4.  **External algorithms are already separate.** `SingleSourceSearch`, `GetStaticFilter`, `GetPosePath` and `BottleneckAssignment` come from other packages. The default solvers keep calling them; nothing about them changes.
5.  **Some "AGV assignment" work is graph repair, not matching.** `DoAgvAssignments` ends with `EnsureAgvMovePathsClear(ctx)` (up to 256 repair passes), then `ctx->events.Reduce()`, then `AddDepsAfterAmiga(...)`. `Plan` calls `Reduce()` a second time afterwards. Keep all of these in the same order inside the default AGV solver for the first pass; see risk 2 in [section 10](#pr-risks-that-must-not-be-silently-fixed).

### Why the default solver needs graph and collision services

This is the start of today's tray algorithm. Note the two different garage states:

``` cpp
// src/scheduler.cpp — Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const
// this : const Scheduler* ; gg_ and table_ are Scheduler members
auto working_state = ctx->initial_state;               // DiscreteGarageState COPY; updated as moves are assigned
auto total_ordering_opt = ctx->events.GetTopologicalOrdering();  // std::optional<...>: empty if the DAG has a cycle
if(!total_ordering_opt.has_value()) {
  return std::make_pair(false, "Failed to get total ordering");
}

// Remembers which already-planned event vacates each node, so a later move INTO that
// node can depend on it. Needs the graph and collision table to know which nodes overlap.
volley::GarageOccupancyChecker<std::shared_ptr<volley::ScheduleEvent>> freeing_moves(table_, gg_);
```

`ctx->initial_state` stays untouched; `working_state` is the solver's private "garage after everything planned so far". Keeping that distinction is invariant 9 in practice ([section 7](#pr-key-invariants-to-maintain)).

## Current versus target responsibilities

Every concern of `Scheduler::Plan()`, grouped by stage, with where it lives today and where it goes. Folder names are those of [section 6](#pr-module-layout-folders-or-packages); "later" marks moves that are not needed for the ticket's Definition of Done.

| Stage               | Concern                                                                    | Today (in `Scheduler`)                                                                                     | After the refactor                                                                                                                                                                                                                                                                                                 |
|---------------------|----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| orchestrator        | Validate request, build `ScheduleContext`, run the stages, build the reply | `Plan`                                                                                                     | Stays in `Scheduler` (`scheduler.hpp`); context in `plan_context.hpp`                                                                                                                                                                                                                                              |
| 1 · job expansion   | Expand jobs into events                                                    | `Plan<Type>Job` (12 methods)                                                                               | Stays in `Scheduler` for the ticket (renamed `Expand<Type>Job`); later free functions in `task_planning/job_expansion/`                                                                                                                                                                                            |
| 2 · tray assignment | Choose tray and destination for each `TrayMove`                            | `DoTrayAssignments` → `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`                            | `tray_assignment::DefaultSolver` (the loop) + pure `ChooseEmptyTray`, `ChooseParkingSpot` in `task_planning/tray_assignment/` ([section 8.3](#pr-before-and-after-the-tray-call-tree))                                                                                                                             |
|                     | Move blocking trays out of the way                                         | `ResolveBlockingTrays` → `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution`                       | Pure free function `tray_assignment::ResolveBlockingTrays(svc, request)`, public so job expansion can call it too                                                                                                                                                                                                  |
|                     | Write the tray results into `ctx`                                          | (done inside `DoTrayAssignments`)                                                                          | `tray_assignment::ApplyTrayAssignment(ctx, result)`, called by `Plan()` right after `Solve`; the only writer (sections [8.1](#pr-the-new-pieces-and-how-they-fit-together), [8.5](#pr-why-return-a-result-and-how-it-is-applied))                                                                                  |
|                     | Choose parking headings                                                    | `UsePreferredHeading`, `UseRetrievalHeading`, `UseEvChargeHeading`                                         | Pure functions in `core/headings` (job expansion uses them too)                                                                                                                                                                                                                                                    |
| 3 · AGV assignment  | Match AGVs to tray moves                                                   | `DoAgvAssignments` + cost helpers + `BottleneckAssignment`                                                 | `agv_assignment::DefaultSolver` in `task_planning/agv_assignment/`; travel cost in `task_planning/travel_cost`                                                                                                                                                                                                     |
|                     | Add approach, lift and lower events                                        | `MoveAgvToTrayPose`, `AppendAgvLiftEvent`, `AddNodeArrivalDeps`                                            | Default AGV solver                                                                                                                                                                                                                                                                                                 |
|                     | Repair AGV path conflicts, reduce, AMIGA deps                              | `EnsureAgvMovePathsClear`, `Reduce`, `AddDepsAfterAmiga` (end of `DoAgvAssignments`)                       | Default AGV solver, same order (move later only with evidence)                                                                                                                                                                                                                                                     |
| 3 · validation      | Sanity check of the finished event DAG                                     | `SanityCheckEvents`                                                                                        | Renamed `ValidateEvents` (stage H); later a free function in `task_planning/validation/`                                                                                                                                                                                                                           |
| 1–3                 | DAG primitives                                                             | `planner_core::ScheduleEventDag`                                                                           | Unchanged (renamed in stage I)                                                                                                                                                                                                                                                                                     |
| 4 · motion planning | Adapt the event DAG to CHUGG and run it                                    | `PlanMotions` (member, about 60 lines)                                                                     | Free function `motion_planning::PlanMotions(svc, event_dag, state)` in `motion_planning/`; CHUGG itself stays in `motion_planner`, unchanged                                                                                                                                                                       |
| 5 · action DAG      | Turn timed motions into action nodes and edges                             | Five free functions in an anonymous namespace of `scheduler.cpp`; `InsertVrcActionsIntoDag` in `utils.cpp` | `action_graph/`, with inputs narrowed from the context pointer to the event DAG, job list and initial state, the services passed explicitly, and the per-job action indices returned instead of written into `ctx->scheduled_jobs`; names per the naming catalogue ([section 15](#nm-proposed-future-work-naming)) |
|                     | Assemble the reply                                                         | `ResponseFromTrajectories` (member)                                                                        | Stays in `Scheduler` as `BuildPlanResponse`; calls `action_graph::BuildActionDag`                                                                                                                                                                                                                                  |

**Decision needed:** folders or packages for the stages, and therefore where the solver *interfaces* live. [Section 6](#pr-module-layout-folders-or-packages) compares the two and recommends starting with stage folders inside the scheduler package (one library target per stage, still one `CMakeLists.txt`; tree in [section 8.2](#pr-source-tree)), so the interfaces live in `task_planning/tray_assignment/solver.hpp` and `task_planning/agv_assignment/solver.hpp`. Promoting a stage to its own package later means moving its three folders and adding a `package.xml`. A default implementation needs `motion_planner` and `cost_functions`, so putting interfaces and defaults in a low-level package such as `planner_core` would create dependency cycles. Check against `package.xml` and the exported CMake targets before choosing.

## Module layout: stage folders or stage packages

The code should be organised by pipeline stage ([section 2](#pr-the-pipeline-the-refactor-works-on)), not by "everything `Scheduler` does". There are two ways to draw those boundaries: as folders inside the `scheduler` package (Option 1), or as separate ROS packages (Option 2). This section compares them and recommends a path that starts with Option 1 and allows Option 2 one stage at a time.

![Stage folders vs stage packages](figures/95_module_layout.svg)

**Stage folders vs stage packages.** Option 1 (top) keeps one `scheduler` package with one folder per stage and a shared `core/`. Option 2 (bottom) makes the stages packages: stage 4 already is one (`motion_planner`); `task_planning` needs a new `scheduler_core` package for `PlanContext` and `GarageServices`; `action_graph` needs nothing new once its inputs are narrowed. This is a proposal, not existing code.

### Stage names

The folder names say what each stage produces, using the field's standard terms (the [Background](#doc-background) tab, [How to think about the scheduler](#bg-how-to-think-about-the-scheduler)):

| Stages | Folder            | Why                                                                                                                                                                                                                                                                                                                                                                                                      |
|--------|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1–3    | `task_planning`   | Together the three stages decompose jobs into events, allocate trays and AGVs, and add blocker moves (rearrangement). "Task planning" is the usual name for decomposition plus allocation, and the output is a plan (the event DAG). The name is close to the existing `task_planner` package, which holds `BottleneckAssignment`; if that proves confusing, `event_planning` names the output directly. |
| 4      | `motion_planning` | CHUGG plans *timed* trajectories for many agents at once (MAPF with SIPP), so "motion" rather than "path", which has no time. The name matches the package that does the work, `motion_planner`, and the existing method `PlanMotions`.                                                                                                                                                                  |
| 5      | `action_graph`    | The output is a partial order, the action dependency graph ([section 4.5](#ad-where-parallelism-comes-from)): actions of different AGVs run in parallel unless an edge orders them.                                                                                                                                                                                                                      |

Inside `task_planning/` each step is a subfolder: `job_expansion/`, `tray_assignment/`, `agv_assignment/` and `validation/`. The two ticket modules keep the names used in the rest of this tab. The `Plan()` orchestrator, `PlanContext`, the ROS boundary (`ros/`) and the shared `core/` stay at the top of the package because every stage uses them or none owns them.

### Option 1: stage folders in `scheduler`

One package, one folder per stage under `include/scheduler/`, `src/` and `test/` (full tree in [section 8.2](#pr-source-tree)). Each stage folder builds its own CMake library target, and the `scheduler` library links them. That gives most of the enforcement of separate packages at no packaging cost:

- **The linker enforces direction.** `scheduler_task_planning` links `scheduler_core` (the target for `core/`), never `scheduler`; code in it that calls a `Scheduler` member does not link.
- **A CI include check covers what the linker cannot.** A stage folder never includes another stage folder, `scheduler.hpp` or `ros/`. Inside `task_planning/`, `job_expansion/` may call the public functions of `tray_assignment/` (`ResolveBlockingTrays`, `ChooseEmptyTray`), as it does today; `agv_assignment/` must not include `tray_assignment/` (the hand-off is `first_event_by_tray`, a plain map in its `Input`).
- **Moves are cheap and reversible.** Changing a boundary is a `git mv` and a CMake edit in one package, reviewed in one PR.

### Option 2: one package per stage

Each stage becomes a ROS package with its own `package.xml` and CMake. Three facts decide what that means in practice:

- **Stage 4 already is a package.** `motion_planner` holds CHUGG, SIPP and the searches. What remains in `scheduler` is `PlanMotions`, about 60 lines that adapt the event DAG and the garage state to CHUGG's inputs. A `motion_planning` package would hold only that adapter, so it should stay in `scheduler`.
- **`task_planning` needs a lower package first.** Its solvers take `PlanContext`, `GarageServices` and the internal types. Those cannot stay in `scheduler` (a package below `scheduler` cannot include it), so a new `scheduler_core` package must hold them. Today's dependencies leave room for it: `planner_core` depends only on `common`, `common_ros` and `interfaces`; `motion_planner` on those plus `cost_functions`; `scheduler` on all of them plus `task_planner` and `stdx`. A `scheduler_core` between `motion_planner` and `scheduler` creates no cycle.
- **`action_graph` is ready almost as it is.** Its code is already free functions; once their argument is narrowed from the context pointer to the event DAG, job list and initial state, and the collision table, motion graph, layout and cost model are passed as separate references, every type it uses comes from a lower package: `planner_core` (the DAGs), `motion_planner` (`ContinuousState`), `common_ros`, `cost_functions` and `interfaces`.

The cost: every installed header becomes public API that other packages can include, so it falls under the stricter naming tier of the naming catalogue (tier B, [section 15.1](#nm-how-to-read-this-list)) and changes need the owners of every user. Each package adds a `package.xml`, CMake export boilerplate, a `colcon` build step and a place in the release process.

### Comparison

The table sets the two options side by side against the criteria that matter for this ticket. Option 1 is ahead on prerequisites, the naming constraint, risk to behaviour parity and reversibility; Option 2 is ahead on dependency enforcement, isolated builds and reuse outside the scheduler.

| Criterion                                                         | Option 1: stage folders                                       | Option 2: stage packages                                                                                                    |
|-------------------------------------------------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| Dependency enforcement                                            | Per-stage CMake targets (link errors) plus a CI include check | Strongest: `package.xml` and `colcon` refuse undeclared dependencies                                                        |
| Prerequisites                                                     | None; can start with stage C0 of the plan                     | A `scheduler_core` package; narrowed stage inputs; agreed owners                                                            |
| Interface stability                                               | Headers are internal to one package; changes are one PR       | Installed headers are public API; changes cross packages and reviews                                                        |
| Private helpers                                                   | Private headers in `src/<stage>/`, not on any include path    | Same, per package                                                                                                           |
| Build and CI                                                      | One package; incremental builds as today                      | Packages build in parallel and test in isolation; more package boilerplate                                                  |
| Benchmarks (SW2-487)                                              | A benchmark target links only the stage library               | A benchmark package depends only on the stage package                                                                       |
| Reuse outside the scheduler                                       | Not possible without depending on `scheduler`                 | Any package can depend on one stage (for example a planning simulator using `action_graph`)                                 |
| Naming constraint (rename only in `scheduler` and `planner_core`) | Met: all new names live in `scheduler`                        | New package names are new names outside `scheduler`; acceptable because nothing else uses them yet, but each needs approval |
| Risk to behaviour parity                                          | Low: files move, code does not                                | Low for the code, higher for the build: export, install and link errors appear outside the parity tests                     |
| Reversibility                                                     | High                                                          | Low once other packages depend on a stage                                                                                   |

### Recommendation: folders now, packages when proven

**Adopt Option 1 now, and write the code as if it were Option 2.** Each stage folder gets its own CMake target with the dependency rules above, so promoting a stage later is a move of three folders and a new `package.xml`, not a refactor. Then promote stages one at a time, only when they meet the checklist below:

1.  **`action_graph` first.** It is already free functions, its inputs are lower-package types once narrowed, and it is the natural unit to test against the ADG rules of the Action graph tab. It can be promoted as soon as stage C0 has narrowed its inputs (stage J of the plan).
2.  **`task_planning` after the benchmarks.** Its interfaces are what this ticket designs; they should stay internal until stage G's benchmarks and stage H's cleanup show they are stable. Promotion then needs `scheduler_core` as well.
3.  **`motion_planning` never.** The algorithm already lives in `motion_planner`; the adapter belongs to the orchestrator. When motion planners become swappable ([section 15](#pr-swappable-motion-planners)), the solver interface goes into `motion_planner` and the adapter stays here.

A stage folder is ready to become a package when all of these hold:

- It includes nothing from `scheduler.hpp`, `ros/` or another stage folder (the CI check has passed for some time).
- Its public inputs and outputs are types from lower packages, or from `scheduler_core` once that exists.
- Something outside `Scheduler::Plan()` needs it: a second user, or a benchmark that must not link the scheduler.
- Its public interface has not changed for a release.
- An owner for the package is agreed.

## Target architecture

This section shows the proposed design as a whole before [section 8](#pr-proposed-layout-and-api) defines its types and functions. In the figure, note the two different solver contracts: the tray solver returns its edits for `Scheduler` to apply, while the AGV solver edits the event DAG in place for its first version.

![Target design](figures/02_target_architecture.svg)

**Proposed architecture.** Solver contracts separate policy from orchestration. Both default solvers get graph, collision, cost and layout services through one `const GarageServices&`. The tray solver only reads the event DAG and returns its edits, which `Scheduler` applies; the AGV solver edits the DAG in place for the first pass ([section 6.7](#pr-agv-assignment-same-layout-and-error-type-now-returned-result-later)). This is a proposal, not existing code.

### Classes and call sequence

The two figures below are the proposal at a glance; [section 6](#pr-proposed-layout-and-api-for-tray-assignment) then defines each type and function.

![Solver UML](figures/08_uml_solver.svg)

**Proposed class structure.** `Scheduler` owns a `tray_assignment::Solver` and builds the read-only `Input` it passes in. `DefaultSolver` and a test double realize the interface (dashed line, hollow triangle) and return `stdx::Expected<Result>`; `Scheduler` applies the `Result` in one place. `DefaultSolver` delegates to pure free functions that job planning also calls. This is the **Strategy** pattern: `Scheduler` depends on the stable interface, not on the algorithm.

![Solver call sequence](figures/09_sequence_tray.svg)

**Proposed tray solver interaction.** `Scheduler` calls `Solve`. The solver reads the topological event order once, then records (does not apply) tray fills, blocker moves, edges and `first_event_by_tray` in a `Result`, and returns `stdx::Expected<Result>`. `Scheduler` replays the result into `ctx->events` with `ApplyTrayAssignment`, which ends with the cycle check, and AGV assignment continues.

## Proposed layout and API for the assignment stages

The two stages the ticket moves behind interfaces get the same treatment, in two subsections with the same outline: tray assignment ([section 8.1](#pr-proposed-layout-and-api-for-tray-assignment)) and AGV assignment ([section 8.2](#pr-agv-assignment-same-layout-and-error-type-now-returned-result-later)). Each one introduces the new types and how they work with the plan context, then where the files go, which of today's functions turn into what, errors, how the result reaches the context, the remaining signatures and the `Plan()` call site, and finally the names and why they were chosen. The difference between the two is one decision, explained in each subsection: tray assignment **returns** its decisions and one function applies them; AGV assignment **edits the event DAG in place** for its first version, and says so in its signature. Everything here is **proposed**. Code in this section already uses the names from [section 9](#pr-naming-and-the-ros-boundary) (`PlanContext`, `event_dag`, `motion_graph`, `first_event_by_tray`, `Pose`, …); prose about today's code keeps today's names (`ScheduleContext`, `ctx->events`, `gg_`).

### Tray assignment

Tray assignment is the first of the two stages moved behind an interface, and it sets the pattern that AGV assignment follows. The subsections below separate deciding from writing: a solver returns its decisions as a value, and one function applies them to the plan context.

#### The new pieces and how they fit together

Today `DoTrayAssignments(ctx)` does two jobs at once: it **decides** (which tray, which destination, which blockers move where) and it **writes** those decisions into `ctx` as it goes. The proposal separates the two:

- **Deciding** happens in `tray_assignment::DefaultSolver::Solve`. It receives read-only references to the parts of `ctx` it needs and returns its decisions as a value, a `Result`. It never writes `ctx`.
- **Writing** happens in one free function, `tray_assignment::ApplyTrayAssignment(PlanContext&, const Result&)`, which `Plan()` calls right after `Solve` succeeds.

`ctx` is still changed. It has to be, because AGV assignment and motion planning read the blocker moves, filled-in fields and `first_tray_event` from it. What changes is *where*: one function, called once, after all the decisions are made, instead of writes spread through a 560-line loop and its helpers.

![Tray assignment data flow, today vs proposed](figures/58_tray_dataflow.svg)

**How tray assignment reads and writes `ScheduleContext`.** Top: today `DoTrayAssignments` gets a shared, mutable pointer to the context and writes into it throughout the loop, so a failure halfway leaves it half-edited. Bottom: (1) `Plan` passes `Solve` two `const` references; (2) `Solve` keeps its working data in a private `Pass`, calls pure functions to decide, and returns a `Result`; (3) `ApplyTrayAssignment` writes the `Result` into the context. If `Solve` fails, step 3 never runs and the context is unchanged.

The pieces, all in namespace `volley::task_planning::tray_assignment` (folder `task_planning/tray_assignment/`) unless marked `scheduler_core`:

| Piece                                              | What it is                                                                                                     | Declared in                                                                                                        | Lives for                                         | Reads                        | Writes                                                   |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|------------------------------|----------------------------------------------------------|
| `scheduler_core::GarageServices`                   | Struct of `const` references to the graph, collision table, cost model and layout, plus the logger             | `include/scheduler/core/garage_services.hpp`                                                                       | As long as the `Scheduler` (member `services_`)   | —                            | nothing                                                  |
| `Input`                                            | Struct of two `const` references into `plan_ctx`                                                               | `include/scheduler/task_planning/tray_assignment/solver.hpp`                                                       | One `Solve` call (a temporary built in `Plan`)    | `initial_state`, `event_dag` | nothing                                                  |
| `Result`                                           | Plain value: `fills`, ordered `edits`, `first_event_by_tray`                                                   | `solver.hpp`                                                                                                       | From `Solve`'s return until `ApplyTrayAssignment` | —                            | — (it is data)                                           |
| `TrayFill`, `AddEvent`, `AddDependency`, `DagEdit` | The element types inside `Result`                                                                              | `solver.hpp`                                                                                                       | Inside `Result`                                   | —                            | —                                                        |
| `Solver`                                           | Interface with one method, `Solve(const Input&) const`                                                         | `solver.hpp`                                                                                                       | Owned by `Scheduler` (`tray_solver_`)             | —                            | —                                                        |
| `DefaultSolver`                                    | Today's algorithm behind the interface; holds only `const GarageServices&`                                     | `default_solver.hpp`, `src/task_planning/tray_assignment/default_solver.cpp`                                       | Owned by `Scheduler`                              | `Input`, services            | nothing outside itself                                   |
| `DefaultSolver::Pass`                              | **Private nested class**: the loop's working data                                                              | declared in `default_solver.hpp`, defined in `src/task_planning/tray_assignment/pass.hpp`                          | One `Solve` call (a local variable)               | `Input`, services            | only its own members                                     |
| Pure functions                                     | `ChooseEmptyTray`, `ResolveBlockingTrays`, `ChooseParkingSpot`, `FindCriticalPath`, the heading functions, ... | `empty_tray.hpp`, `blocking_trays.hpp`, `src/task_planning/tray_assignment/critical_path.hpp`, `core/headings.hpp` | —                                                 | their arguments              | nothing                                                  |
| `ApplyTrayAssignment`                              | Free function, the only one that takes a mutable `PlanContext&`                                                | `apply.hpp`, `src/task_planning/tray_assignment/apply.cpp`                                                         | —                                                 | `Result`                     | `ctx.event_dag`, event fields, `ctx.first_event_by_tray` |

What happens in `Plan()`, step by step:

1.  **Build the input.** `Input{plan_ctx->initial_state, plan_ctx->event_dag}`: two `const` references, no copies.
2.  **Solve.** `DefaultSolver::Solve` creates a `Pass` on its stack. The `Pass` copies `initial_state` into `working_state_` and starts with an empty occupancy record, per-tray chain and `result_`. For each event in topological order, `Solve` asks pure functions for decisions (which empty tray, which parking spot, the critical path, where each blocker goes) and tells the `Pass` to record them: `Fill` adds a `TrayFill`, `EmitMoveChain` appends `AddEvent` / `AddDependency` entries in today's order, and `CommitRootMove` records the root move's edges. Each recorded move is also applied to `working_state_`, so later decisions see the garage as it will be. At the end, `Solve` returns the `Pass`'s `Result`. On any error it returns `stdx::Unexpected(message)`; the `Pass` is destroyed, and nothing outside `Solve` was touched.
3.  **Apply.** `ApplyTrayAssignment(*plan_ctx, result)` replays `edits` into `plan_ctx->event_dag`, sets the filled fields on the existing `TrayMove`s, copies `first_event_by_tray`, and runs the same cycle check `DoTrayAssignments` ends with today.
4.  **Continue.** AGV assignment runs on `plan_ctx` exactly as today.

The types, in one place:

``` cpp
// PROPOSED — include/scheduler/core/garage_services.hpp
namespace volley::scheduler_core {
struct GarageServices {                       // read-only services every search needs; built once by Scheduler
  const MotionGraph& motion_graph;           // Scheduler::motion_graph_ (today gg_); MotionGraph = GarageGraph
  const CollisionTable& collision_table;     // Scheduler::collision_table_ (today table_)
  const cost::MotionCostModel& cost_model;   // Scheduler::cost_model_
  const Layout& layout;                      // *Scheduler::layout_
  rclcpp::Logger logger;                      // copy of Scheduler::logger_
};
}  // namespace volley::scheduler_core
```

``` cpp
// PROPOSED — include/scheduler/task_planning/tray_assignment/solver.hpp
namespace volley::task_planning::tray_assignment {

struct Input {                                     // everything Solve may read; nothing it may write
  const DiscreteGarageState& initial_state;        // plan_ctx->initial_state
  const EventDag& event_dag;                      // plan_ctx->event_dag, after job expansion
};

// A blank filled on an EXISTING TrayMove of the input DAG. ApplyTrayAssignment calls SetTrayId / SetDestination.
struct TrayFill {
  ScheduleEventSPtr event;   // the TrayMove, as the input DAG holds it (same shared_ptr)
  uint16_t tray_id;          // unchanged if it was already set
  Pose destination;          // unchanged if it was already set; heading may be adjusted
};

// One structural edit, recorded in the order today's code makes it.
struct AddEvent      { ScheduleEventSPtr event; };                       // a NEW TrayMove (blocker, advance)
struct AddDependency { ScheduleEventSPtr from; ScheduleEventSPtr to; };  // from must finish before to
using DagEdit = std::variant<AddEvent, AddDependency>;

struct Result {
  std::vector<TrayFill> fills;                                       // one per TrayMove that had a blank
  std::vector<DagEdit> edits;                                        // replay front to back
  std::unordered_map<uint16_t, ScheduleEventSPtr> first_event_by_tray;  // hand-off to AGV assignment
};

class Solver {
 public:
  virtual ~Solver() = default;
  [[nodiscard]] virtual stdx::Expected<Result> Solve(const Input& input) const = 0;
};

}  // namespace volley::task_planning::tray_assignment
```

``` cpp
// PROPOSED — include/scheduler/task_planning/tray_assignment/default_solver.hpp
namespace volley::task_planning::tray_assignment {
class DefaultSolver final : public Solver {
 public:
  explicit DefaultSolver(const scheduler_core::GarageServices& services);   // services must outlive the solver
  [[nodiscard]] stdx::Expected<Result> Solve(const Input& input) const override;
 private:
  class Pass;                                // defined in src/task_planning/tray_assignment/pass.hpp; no one else can name it
  const scheduler_core::GarageServices& services_;
};
}  // namespace volley::task_planning::tray_assignment
```

``` cpp
// PROPOSED — src/task_planning/tray_assignment/pass.hpp (private header: not under include/, not installed)
class DefaultSolver::Pass {
 public:
  Pass(const scheduler_core::GarageServices& services, const DiscreteGarageState& initial_state);  // copies the state
  stdx::Result RecordStateChange(const ScheduleEventSPtr& event);  // was ApplyTransitionToFreeingMoves
  void Fill(const ScheduleEventSPtr& event, uint16_t tray_id, const Pose& destination);  // → result_.fills
  void EmitMoveChain(std::span<const PlannedTrayMove> moves, const EmitOptions& options);  // → result_.edits
  stdx::Result CommitRootMove(const ScheduleEventSPtr& event, const TrayMove& resolved,
                              const CommitOptions& options);      // root move: edges, apply, chain
  const DiscreteGarageState& State() const { return working_state_; }  // what the pure functions read
  Result TakeResult() && { return std::move(result_); }
 private:
  const scheduler_core::GarageServices& services_;
  DiscreteGarageState working_state_;                                // initial_state + every move so far
  GarageOccupancyChecker<ScheduleEventSPtr> freeing_moves_;          // which event occupies each pose or edge → new edges
  std::unordered_map<uint16_t, ScheduleEventSPtr> last_event_by_tray_;  // per-tray chain
  Result result_;                                                    // what Solve returns
};
```

``` cpp
// PROPOSED — src/task_planning/tray_assignment/default_solver.cpp (shape only)
stdx::Expected<Result> DefaultSolver::Solve(const Input& input) const {
  auto order = input.event_dag.GetTopologicalOrdering();              // the only read of the DAG's structure
  if(!order) return stdx::Unexpected("Failed to get total ordering");
  Pass pass(services_, input.initial_state);
  for(auto vertex : *order) {
    ScheduleEventSPtr event = input.event_dag.GetEventFromVertex(vertex).value();
    if(event->GetType() != ScheduleEventType::TRAY_MOVE) {
      if(auto r = pass.RecordStateChange(event); !r) return stdx::Unexpected(r.error());
      continue;
    }
    // Work on a resolved COPY of the TrayMove; *event itself is never modified (see 'Why return a result').
    // Blank tray id   -> ChooseEmptyTray(services_, pass.State(), dest), then pass.Fill(...)
    // Blank dest      -> ChooseParkingSpot(...), pass.Fill(...), pass.EmitMoveChain(...), pass.CommitRootMove(...)
    // Both set        -> CheckDestinationUsable, FindCriticalPath, blocker loop with ResolveBlockingTrays,
    //                    TryAdvanceRoot and BlockersOnPath; pass.EmitMoveChain(...); pass.CommitRootMove(...)
  }
  return std::move(pass).TakeResult();
}
```

``` cpp
// PROPOSED — include/scheduler/task_planning/tray_assignment/apply.hpp
namespace volley::task_planning::tray_assignment {
// The only function in the module that takes a mutable context. Implementation under 'Why return a result'.
[[nodiscard]] stdx::Result ApplyTrayAssignment(PlanContext& ctx, const Result& result);
}  // namespace volley::task_planning::tray_assignment
```

`EmitOptions` and `CommitOptions` carry the small differences between today's two copies of the emission code ([6.3](#pr-before-and-after-the-tray-call-tree)) so that parity holds; they can disappear once those differences are settled.

#### Source tree

This is Option 1 of [section 6](#pr-module-layout-folders-or-packages): the package root stays `scheduler/` with **one** `CMakeLists.txt`, and `include/scheduler/`, `src/` and `test/` get one folder per pipeline stage. Folders marked *later* are created empty in stage C0 and filled after the ticket's work ([section 10](#pr-staged-plan)); everything else is part of this refactor.

``` text
scheduler/                                       # ROS package root (name unchanged)
├── CMakeLists.txt                               # the only CMakeLists.txt; one library target per stage
├── package.xml                                  # already depends on stdx, motion_planner, task_planner
├── include/
│   └── scheduler/
│       ├── scheduler.hpp                        # orchestrator: Plan() runs the stages; owns services_, tray_solver_
│       ├── plan_context.hpp                     # PlanContext (today ScheduleContext), ScheduledJob
│       ├── scheduler_ros.hpp                    # existing
│       ├── scheduler_msgs.hpp                   # existing
│       ├── utils.hpp                            # existing
│       ├── core/                                # shared by every stage; includes no stage
│       │   ├── vocabulary.hpp                   # translation header: new names for common_ros types (9.2)
│       │   ├── types.hpp                        # AssetId, AssetType: internal types, no ROS includes (9.3)
│       │   ├── garage_services.hpp              # GarageServices
│       │   ├── headings.hpp                     # PreferredHeading, RetrievalHeading, EvChargeHeading
│       │   └── overloaded.hpp                   # Overloaded helper for std::visit
│       ├── ros/
│       │   └── convert.hpp                      # messages <-> internal types (9.3)
│       ├── task_planning/                       # stages 1-3: jobs -> finished event DAG
│       │   ├── travel_cost.hpp                  # GetJustMovingCost (AGV assignment and PlanAgvChargeJob)
│       │   ├── job_expansion/                   # later: ExpandJob as free functions
│       │   ├── tray_assignment/                 # stage 2 (this ticket)
│       │   │   ├── solver.hpp                   # Solver, Input, Result, TrayFill, DagEdit
│       │   │   ├── default_solver.hpp           # DefaultSolver (declares the private nested Pass)
│       │   │   ├── apply.hpp                    # ApplyTrayAssignment
│       │   │   ├── empty_tray.hpp               # ChooseEmptyTray, TrayChoice
│       │   │   └── blocking_trays.hpp           # ResolveBlockingTrays, ChooseParkingSpot, PlannedTrayMove, ...
│       │   ├── agv_assignment/                  # stage 3 (this ticket)
│       │   │   ├── solver.hpp
│       │   │   └── default_solver.hpp
│       │   └── validation/                      # later: ValidateEvents (today SanityCheckEvents)
│       ├── motion_planning/                     # stage 4
│       │   └── plan_motions.hpp                 # PlanMotions(services, event_dag, state) -> ContinuousState
│       └── action_graph/                        # stage 5
│           └── build.hpp                        # BuildActionDag, CopyEventDependencies, InsertVrcActions
├── src/                                         # mirrors include/scheduler/; private headers live here
│   ├── scheduler.cpp                            # existing; shrinks to Plan() + job expansion until "later"
│   ├── scheduler_component.cpp, scheduler_ros.cpp, utils.cpp   # existing
│   ├── core/headings.cpp
│   ├── ros/convert.cpp
│   ├── task_planning/
│   │   ├── travel_cost.cpp
│   │   ├── tray_assignment/
│   │   │   ├── default_solver.cpp               # Solve(): the per-event loop
│   │   │   ├── pass.hpp                         # PRIVATE header: DefaultSolver::Pass
│   │   │   ├── pass.cpp
│   │   │   ├── critical_path.hpp                # PRIVATE header: CheckDestinationUsable, FindCriticalPath, ...
│   │   │   ├── critical_path.cpp
│   │   │   ├── empty_tray.cpp
│   │   │   ├── blocking_trays.cpp               # + detail::FindOpenSpace, detail::TryResolveBlocker
│   │   │   └── apply.cpp
│   │   └── agv_assignment/
│   │       └── default_solver.cpp
│   ├── motion_planning/plan_motions.cpp         # body of today's Scheduler::PlanMotions
│   └── action_graph/build.cpp                   # today's anonymous-namespace helpers + InsertVrcActionsIntoDag
└── test/                                        # mirrors src/
    ├── scheduler_tests.cpp, ...                 # existing end-to-end tests stay at the top
    ├── task_planning/tray_assignment/           # empty_tray, blocking_trays, critical_path, default_solver, apply
    ├── task_planning/agv_assignment/
    └── action_graph/                            # new: ADG rules (Action graph tab) on hand-built inputs
```

The `CMakeLists.txt` declares one library per stage. Today it builds one shared library with `volley_add_library(${PROJECT_NAME} SHARED src/scheduler.cpp src/utils.cpp)` and four `volley_add_gtest` targets; the excerpt below adds the stage targets. Whether `volley_add_library` accepts `STATIC` and `LINK_LIBRARIES` is not visible in this snapshot (it is defined in `volley_cmake`); plain `add_library` and `target_link_libraries` do the same job.

``` cmake
# PROPOSED — CMakeLists.txt (excerpt; the rest of the file is unchanged)
# Shared core: no stage, no scheduler.hpp
add_library(scheduler_core STATIC src/core/headings.cpp)

# Stage libraries: each links scheduler_core and lower packages, never ${PROJECT_NAME}
add_library(scheduler_task_planning STATIC
  src/task_planning/travel_cost.cpp
  src/task_planning/tray_assignment/default_solver.cpp
  src/task_planning/tray_assignment/pass.cpp
  src/task_planning/tray_assignment/critical_path.cpp
  src/task_planning/tray_assignment/empty_tray.cpp
  src/task_planning/tray_assignment/blocking_trays.cpp
  src/task_planning/tray_assignment/apply.cpp
  src/task_planning/agv_assignment/default_solver.cpp
)
target_link_libraries(scheduler_task_planning PUBLIC scheduler_core)

add_library(scheduler_motion_planning STATIC src/motion_planning/plan_motions.cpp)
target_link_libraries(scheduler_motion_planning PUBLIC scheduler_core)

add_library(scheduler_action_graph STATIC src/action_graph/build.cpp)   # services passed one by one: no scheduler_core

# The orchestrator library links the stages
volley_add_library(${PROJECT_NAME} SHARED src/scheduler.cpp src/utils.cpp src/ros/convert.cpp)
target_link_libraries(${PROJECT_NAME} PUBLIC
  scheduler_task_planning scheduler_motion_planning scheduler_action_graph)

if(BUILD_TESTING)
  volley_add_gtest(
    tray_assignment_tests
    test/task_planning/tray_assignment/empty_tray_test.cpp
    test/task_planning/tray_assignment/blocking_trays_test.cpp
    test/task_planning/tray_assignment/critical_path_test.cpp
    test/task_planning/tray_assignment/default_solver_test.cpp
    test/task_planning/tray_assignment/apply_test.cpp
    LINK_LIBRARIES
      yaml-cpp
      scheduler_task_planning                    # not ${PROJECT_NAME}: the test cannot reach Scheduler
  )
endif()
```

(Each stage target also needs the `ament_target_dependencies` on the lower packages it uses, its include directory, and `POSITION_INDEPENDENT_CODE` because it is linked into a shared library.) How the boundaries hold:

- **Public vs private headers.** Headers under `include/scheduler/<stage>/` are the stage's API; code includes them as `#include "scheduler/task_planning/tray_assignment/solver.hpp"`. Headers next to the `.cpp` files in `src/<stage>/` are private. They are not under `include/`, so they are not installed and not on anyone's include path, and only files in the same folder include them (`#include "pass.hpp"`). Check that `volley_add_library` exports only `include/`.
- **`Pass` cannot be used from outside even by accident.** It is a private nested class of `DefaultSolver`, so code outside `DefaultSolver` cannot name it, whatever it includes.
- **The linker enforces the direction between stages and the orchestrator.** No stage target links `${PROJECT_NAME}`, so a stage that calls a `Scheduler` member fails to link, and a test that links only `scheduler_task_planning` proves the solver works without a `Scheduler`.
- **A CI include check covers the rest.** The linker cannot see header-only includes, so a one-line grep checks: no file under a stage folder or `core/` includes `scheduler/scheduler.hpp` or `scheduler/ros/`; no stage folder includes another stage folder; under `task_planning/`, `agv_assignment/` does not include `tray_assignment/` (the hand-off, `first_event_by_tray`, is a plain map in its `Input`), while `job_expansion/` may include `tray_assignment/`'s public headers.

Names: **`tray_assignment` rather than `tray_movement`**, because job expansion also plans tray movement (it creates the `TrayMove`s); this module only fills in what expansion left open (tray ids, destinations, blockers). It matches the stage name in the Task planning tab (`DoTrayAssignments`) and pairs with `agv_assignment`. The stage folder names are explained in [section 6.1](#pr-stage-names). Namespaces follow the folders: `volley::task_planning::tray_assignment`, `volley::task_planning::agv_assignment`, `volley::motion_planning`, `volley::action_graph`, `volley::scheduler_core` for `core/`, and `volley::ros_convert` for `ros/`. `scheduler.cpp` declares `namespace tray_assignment = task_planning::tray_assignment;` (and the same for `agv_assignment`), so the snippets in this tab use the short names. The shared folder is `core/`, not `common/`, because a `volley::common` namespace would break existing code. The `common` package already defines namespace `::common`, and `scheduler.cpp` calls `common::EnumInteger(...)` from inside `namespace volley`. Name lookup would find `volley::common` first and stop there, so those calls would no longer compile. For the same reason no namespace is called `volley::motion_planner`: the stage namespace is `motion_planning`, so it cannot hide the package's own names.

#### Before and after: the tray call tree

Not everything moves into the new class. The two figures below show the same call tree before and after; the question that sorts every function is **what does it write?**

![Tray call tree today](figures/59_tray_tree_before.svg)

**Tray call tree today.** Every function is a `Scheduler` member, and the main loop's six blocks are written inline in `DoTrayAssignments`. The chips show what each one writes: red for something in `ScheduleContext` (the DAG, the hand-off map, or a field of an event in the DAG), amber for an argument passed by reference, green for nothing. Three functions already write nothing, but their signatures do not say so, and four functions are also called by job planning.

![Proposed tray_assignment module](figures/60_tray_tree_after.svg)

**The same call tree after the refactor (UML).** `Pass` is drawn **inside** `DefaultSolver` because it is a private nested class: it exists only during one `Solve` call and holds the only state that changes while solving. Everything green is a pure function, grouped by the header that declares it; `// was ...` names the member or inline block it replaces. `ApplyTrayAssignment` (red) is the only function that takes a mutable `ScheduleContext`, and `Scheduler::Plan` calls it right after `Solve`. Job methods call the public pure functions directly with `services_`.

In short, today's functions fall into four groups:

| Group                              | Functions                                                                                                                                                                                                                                                         | Why there                                                       |
|------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| **Solver class**                   | `DefaultSolver::Solve` (was `DoTrayAssignments`, minus everything below)                                                                                                                                                                                          | The interface method; runs the per-event loop                   |
| **Private, mutable, one per call** | `Pass::RecordTransition`, `Fill`, `EmitMoveChain`, `CommitRootMove` (were `ApplyTransitionToFreeingMoves`, the setters, the two copies of the emission block, the root-move tail)                                                                                 | They update the loop's working data, which only `Solve` can see |
| **Pure**                           | `ChooseEmptyTray`, `ResolveBlockingTrays`, `ChooseParkingSpot`, `detail::FindOpenSpace`, `detail::TryResolveBlocker`, `CheckDestinationUsable`, `FindCriticalPath`, `TryAdvanceRoot`, `BlockersOnPath`, `PreferredHeading`, `RetrievalHeading`, `EvChargeHeading` | They only compute an answer from their arguments                |
| **Writes the context**             | `ApplyTrayAssignment` (new)                                                                                                                                                                                                                                       | Replaces every write that used to happen inside the loop        |

**What “pure” means here.** The function's result depends only on its arguments, and it writes nothing reachable from them: no member state, no `ctx`, no event objects. Inputs come in by `const&` or by value, and the answer comes back as the return value. The read-only services (`GarageGraph`, `CollisionTable`, `MotionCostModel`, `Layout`) are passed as one `const GarageServices&` (`svc`), because they never change after the `Scheduler` constructor. Logging is the one allowed side effect: it does not change what any later call computes.

Why make them pure:

- **They can be tested alone.** `ChooseEmptyTray` needs a layout, a `DiscreteGarageState` and a destination, not a `Scheduler`, not a `ScheduleContext`, not a DAG. Today the only way to test it is through `DoTrayAssignments` or `PlanReadyForInsertJob`.

- **The “shared helper” problem in [section 3](#pr-what-the-two-algorithms-touch) goes away.** Job methods call the same free functions with the `Scheduler`'s `services_`. No back-pointer from the solver to `Scheduler`, and no copy of the helpers on both sides.

- **The recursion is easier to trust.** `ResolveBlockingTrays` ↔ `TryResolveBlocker` already work on private copies of the state; as free functions with no members to touch, that guarantee is visible in the signature.

- **One copy of the emission code.** The two emission blocks differ in three small ways today, and parity means keeping all three:

  - the main loop registers each move's source pose with the generic `TRAY` collision id, while `AssignDestForUntargetedMove` uses the tray's own id → a parameter of `EmitMoveChain`;
  - only the main loop erases the tray from `blocking_tray_set` → stays in the caller;
  - only `AssignDestForUntargetedMove` checks the result of `Apply`. The main loop *cannot* yet: on the fallback-1 path the advance move was already applied before it reaches this block and is applied a second time here (the `TODO(Gunther)` at `:2933` says so). Checking would make that path fail → a parameter for now; fix the double apply as its own reviewed change.

  The root-move tails differ too: the main loop adds `freeing_moves` edges for the root move's destination and source and registers its source (`:3024`–`:3050`); `AssignDestForUntargetedMove` does neither ([section 16](#bg-tray-assignment-dotrayassignments)). `CommitRootMove` keeps both behaviours behind a flag until someone decides whether the second is a bug.

**What stays mutable, and why that is fine.** The loop needs a garage state that changes after every move, an occupancy record and a per-tray “last move” map. Those live in `Pass`, an object created inside `Solve` and destroyed when it returns. Nothing outside can see it. Seen from the caller, `Solve` is still a pure function: same `Input`, same `Result`. This is the usual pattern of “local mutation, pure interface”: rewriting the loop to thread an immutable state through every step would add copying and noise without making the code any safer.

#### Errors: `stdx::Expected` instead of `BoolStringPair`

`BoolStringPair` (`std::pair<bool, std::string>`) and `stdx::Expected` say the same thing (“it worked, or here is why not”), but `Expected` says it in the type: a caller cannot read a value without checking, and there is no meaningless message on success or meaningless value on failure. The project already has `volley::stdx` (`src/core/stdx/include/stdx/expected.hpp`), aliases over `tl::expected`, and **the scheduler package already uses it**: `package.xml` depends on `stdx`, `EnsureAgvMovePathsClear` returns `stdx::Result`, `RunAgvPathRepairPass` returns `stdx::Expected<bool>`, and `utils.cpp`'s `InsertVrcActionsIntoDag` returns `stdx::Result`. So this is finishing a migration that has started, not adding a dependency:

- `stdx::Expected<T, E = std::string>`: a `T` or an error `E`.
- `stdx::Result` = `stdx::Expected<void>`: success or an error string.
- `stdx::Unexpected(msg)` and `stdx::Unexpected(fmt, args...)` (with `std::format`) to build the error.

| Today                                                                                                                    | With `stdx`                                                                                                                                |
|--------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `BoolStringPair F(...)` that only reports success                                                                        | `stdx::Result F(...)`                                                                                                                      |
| `BoolStringPair F(TrayMove& move, ...)` that reports success **and** edits its input                                     | `stdx::Expected<TrayChoice> F(...)`: the edit becomes the return value                                                                     |
| `return std::make_pair(true, "");`                                                                                       | `return {};`                                                                                                                               |
| `return std::make_pair(false, "Failed to find empty tray to move to " + std::to_string(dest));`                          | `return stdx::Unexpected("Failed to find empty tray to move to {}", std::to_string(dest));`                                                |
| `auto [ok, msg] = F(); if(!ok) return std::make_pair(false, msg);`                                                       | `if(auto r = F(); !r) return stdx::Unexpected(r.error());`                                                                                 |
| `std::pair<std::optional<GaragePoseMsg>, std::vector<std::pair<std::shared_ptr<TrayMove>, std::vector<GaragePoseMsg>>>>` | `stdx::Expected<BlockingResolution>` with named fields `dest` and `required_moves` (a `std::vector<PlannedTrayMove>`, each `{move, path}`) |
| test: `std::tie(success, msg) = scheduler.DoTrayAssignments(ctx); EXPECT_TRUE(success) << msg;`                          | `auto r = solver.Solve(input); ASSERT_TRUE(r) << r.error();`                                                                               |

Three rules keep this consistent:

1.  **`stdx::Expected` / `stdx::Result` at every function that can fail for a reason someone should read.** That is every public function in [6.3](#pr-before-and-after-the-tray-call-tree) and every `Pass` method.
2.  **`std::optional` stays for “searched, found nothing”** inside a module, where the caller handles the empty case itself and has no message to pass on: `detail::FindOpenSpace`, `detail::TryResolveBlocker`, `TryAdvanceRoot`. Converting these to `Expected` would invent error strings nobody reads. `ResolveBlockingTrays` is the boundary: today its failures are only logged (`WARNS` / `ERRORS`); as `Expected`, the reason travels to the caller, which still treats it as “try the next fallback”.
3.  **Keep `E = std::string` for the parity pass.** Error text reaches clients through `FailJob(job, message)` and may be matched by tests. A typed error (`struct Error { Code code; std::string message; }`, which `Expected<T, E>` already allows) is a good follow-up once the benchmarks exist.

Two practical notes. `std::format` has no formatter for `GaragePoseMsg`; either pass `std::to_string(pose)` as above (identical text to today) or add a `std::formatter<GaragePoseMsg>` in `core/`. And `tl::expected` has `and_then` / `transform`, which keeps call sites flat (see the `Plan()` snippet in [6.6](#pr-free-function-signatures-and-the-plan-call-site)).

#### Why return a result, and how it is applied

Today `DoTrayAssignments(ctx)` edits three things it does not own: the DAG (`ctx->events`), the hand-off map (`ctx->first_tray_event`) and the `TrayMove` objects inside the DAG (`SetTrayId`, `SetDest`). The proposal: `Solve` takes a read-only `Input` and **returns a description of the edits**; `Plan()` writes them into the context with one call to `ApplyTrayAssignment`.

**Why this is practical for tray assignment.** The tray tree reads the DAG exactly once: `GetTopologicalOrdering()` at the start (plus `GetEventFromVertex` to walk it). After that it only *writes*: `AddEvent`, `AddDependency`, the two setters, and `first_tray_event`. Nothing in the loop reads back an edge it added. So the solver never needs to see its own edits in the DAG, and recording them instead of applying them changes nothing it computes. (The garage *state* the loop does read is `working_state`, which is private to the `Pass` anyway.)

**Why not return a whole new DAG.** `ScheduleEventDag` holds `std::shared_ptr<ScheduleEvent>`. Copying it copies pointers, so a “new DAG” would share event objects with the old one, and the setters would still edit the caller's events. A deep copy needs cloning and an old → new identity map for `first_event_by_tray` and every later stage. `planner_core` has no virtual `Clone()`: events are copy-constructible, but only through their concrete type, so cloning means a `dynamic_cast` (or a switch on `GetType()`) over the five subclasses. An **edit log** avoids both: it refers to existing events by the same `shared_ptr`, adds new events as new objects, and never touches the caller's.

The `Result` type and its parts are defined in [section 8.1](#pr-the-new-pieces-and-how-they-fit-together). An **edit log** means: `fills` for blanks on existing events, `edits` for new events and edges in the order today's code creates them, and the hand-off map.

**Parity depends on the order.** The DAG's vertex indices follow `AddEvent` order (Boost `vecS`). `ScheduleEventDag::GetTopologicalOrdering()` takes the lowest job index first, but breaks ties within a job by heap order, which depends on vertex order and on the order edges were added; `Reduce()` and every replay use that ordering ([section 12.5](#bg-the-operations)). `edits` is therefore an ordered log, and `ApplyTrayAssignment` replays it front to back with the same `AddEvent` / `AddDependency` calls today's code makes, so the resulting DAG is the same graph built in the same order. `AddDependency` returns `false` only when an endpoint is missing or the edge already exists, and tray assignment only logs it, so replaying the same calls gives the same edge set.

**The one subtle part: the loop needs filled values before they are applied.** After `ChooseEmptyTray`, the main loop plans *that* tray's path, and later `Apply`s the move to `working_state`. Today it reads the id back from the mutated event. In the new design the `Pass` makes a resolved copy, `TrayMove resolved = *move; resolved.SetTrayId(choice.tray_id);`, applies the copy to its `working_state`, records a `TrayFill`, and never touches `*move`. Both assumptions hold in `planner_core` (`sources/repomix-planner-core.xml`): `ScheduleEvent`'s copy constructor is public and defaulted, so `TrayMove resolved = *move;` compiles (copy *assignment* is private, so `resolved = *move;` does not), and `Apply` is a `const` member, so it can only change the state it is given. One behaviour to keep in mind: `TrayMove::Apply` with a blank tray id does nothing, and with a blank destination it removes the tray from the state ([section 11](#bg-event-types-and-polymorphism)). The resolved copy always has both fields set, so the `Pass` never hits those branches.

**Applying it.** One function owns every write to the context:

``` cpp
// PROPOSED — src/task_planning/tray_assignment/apply.cpp ; declared in include/scheduler/task_planning/tray_assignment/apply.hpp
stdx::Result ApplyTrayAssignment(PlanContext& ctx, const Result& result) {
  for(const auto& edit : result.edits) {                       // structure first, in recorded order
    stdx::Result applied = std::visit(Overloaded{
        [&](const AddEvent& e) -> stdx::Result {
          if(!ctx.event_dag.AddEvent(e.event)) return stdx::Unexpected("event added twice");  // AddEvent: false if present
          return {};
        },
        [&](const AddDependency& e) -> stdx::Result {
          if(!ctx.event_dag.HasEvent(e.from) || !ctx.event_dag.HasEvent(e.to)) {      // today: a silent no-op
            return stdx::Unexpected("edge to an event that is not in the DAG");
          }
          ctx.event_dag.AddDependency(e.from, e.to);   // false now only means "edge already there", as today
          return {};
        }}, edit);
    if(!applied) return applied;
  }
  for(const auto& fill : result.fills) {                       // then the blanks
    auto* move = dynamic_cast<TrayMove*>(fill.event.get());
    if(move == nullptr) return stdx::Unexpected("TrayFill on a non-TrayMove event");
    move->SetTrayId(fill.tray_id);
    move->SetDestination(fill.destination);
  }
  ctx.first_event_by_tray = result.first_event_by_tray;
  if(!ctx.event_dag.GetTopologicalOrdering()) {                   // same check DoTrayAssignments ends with today
    return stdx::Unexpected("Failed to get new total ordering");
  }
  return {};
}
```

(`Overloaded` is the usual two-line helper for `std::visit`, in `include/scheduler/core/overloaded.hpp`.) The two checks are the only intended difference from today. `AddDependency` returns `false` both for a duplicate edge (harmless, and common) and for an endpoint that was never added (a lost edge, silently). Today's tray code always adds an event before linking it, so the check should never fire; if it does, it has found a bug that today would have shipped as a missing dependency. Applying fills after the edits gives the same DAG: `AddEvent` and `AddDependency` only touch `dag_` and the pointer-keyed `ptr_to_vertex_` map, and the only field the DAG ever reads is the job index (for ordering), which fills do not change. Today the setters run earlier only because that was the convenient place.

**What this buys:**

- **A failed solve leaves `ctx` untouched.** Today a failure halfway through has already added events and edges to `ctx->events`. `Plan` throws the whole response away in that case, so it does not matter yet, but it blocks any future “drop the failing job and retry the rest” ([section 2](#pr-where-the-two-algorithms-sit-today): failure is all-or-nothing).
- **Tests can assert exactly what the solver decided:** “filled tray 23 into event 1, added one move T23 → P24, one edge to event 1”, without diffing whole DAGs.
- **The benchmark (SW2-487) can time `Solve` alone**, with no DAG mutation in the measurement, and compare `Result`s between solvers.
- **A `FakeSolver` is trivial:** it returns a canned `Result`.

**Limits to be honest about.** `const ScheduleEventDag&` stops structural edits, but `GetEventFromVertex` still hands out `std::shared_ptr<ScheduleEvent>` to non-const events, so the compiler does not stop a solver from calling a setter. The rule is enforced by review and by one test: snapshot every event's fields before `Solve`, compare after. Changing `planner_core` to hand out `shared_ptr<const ScheduleEvent>` would make it a compile error, but that is outside this refactor.

#### Free-function signatures and the `Plan()` call site

The types in [6.1](#pr-the-new-pieces-and-how-they-fit-together) cover the solver itself. These are the public pure functions that both `DefaultSolver` and job planning call:

``` cpp
// PROPOSED — include/scheduler/task_planning/tray_assignment/empty_tray.hpp and blocking_trays.hpp
namespace volley::task_planning::tray_assignment {

struct TrayChoice { uint16_t tray_id; Pose destination; };   // heading may follow the tray
[[nodiscard]] stdx::Expected<TrayChoice> ChooseEmptyTray(
    const scheduler_core::GarageServices& services, const DiscreteGarageState& state, const Pose& destination);

struct PlannedTrayMove { std::shared_ptr<TrayMove> move; std::vector<Pose> path; };  // path empty if recursive
struct BlockingResolution { Pose destination; std::vector<PlannedTrayMove> required_moves; };

struct ResolveRequest {                       // named fields replace today's 7 positional parameters
  uint16_t tray_id;
  size_t job_index;
  const DiscreteGarageState& state;
  std::set<uint16_t> immobile_trays = {};
  FootprintIdByVertex illegal_poses = {};      // = VertexCollisionIdMap
  bool enforce_retrieval_heading = false;
  bool allow_waypoint_stash = true;
};
[[nodiscard]] stdx::Expected<BlockingResolution> ResolveBlockingTrays(
    const scheduler_core::GarageServices& services, const ResolveRequest& request);

struct ParkingPlan { Pose destination; std::vector<PlannedTrayMove> required_moves; };  // heading final
[[nodiscard]] stdx::Expected<ParkingPlan> ChooseParkingSpot(
    const scheduler_core::GarageServices& services, const DiscreteGarageState& state, uint16_t tray_id, size_t job_index);

}  // namespace volley::task_planning::tray_assignment
```

`ResolveRequest` is worth its few lines: today's main-loop call is `ResolveBlockingTrays(blocking_tray_id, move->GetJobIndex(), working_state, std::set<uint16_t>{move->GetTrayId().value()}, WithPriorDests(blocking_tray_id, critical_path))`, and the `AssignDestForUntargetedMove` call passes `{}, {}` positionally. With designated initializers the call says what each value is:

``` cpp
// PROPOSED — inside Pass / DefaultSolver
auto resolution = ResolveBlockingTrays(services_, {.tray_id = blocker,
                                             .job_index = root.GetJobIndex(),
                                             .state = pass.State(),
                                             .immobile_trays = {root_tray},
                                             .illegal_poses = WithPriorDests(blocker, critical.vertices)});
if(!resolution) { /* fallback 1, then fallback 2, as today */ }
```

And the call site in `Plan()`, with today's failure contract unchanged ([section 2](#pr-where-the-two-algorithms-sit-today)):

``` cpp
// PROPOSED — src/scheduler.cpp, Scheduler::Plan
// this         : const Scheduler*
// services_    : scheduler_core::GarageServices, new member declared after motion_graph_, collision_table_,
//                cost_model_, layout_
// tray_solver_ : std::unique_ptr<tray_assignment::Solver>, new member declared after services_
auto assigned = tray_solver_->Solve({plan_ctx->initial_state, plan_ctx->event_dag})
                    .and_then([&](const tray_assignment::Result& r) {
                      return tray_assignment::ApplyTrayAssignment(*plan_ctx, r);
                    });
if(!assigned) {
  result.success = true;                                    // unchanged: the call succeeded...
  result.message = "Failed tray assignments: " + assigned.error();
  for(const auto& job : request_data.pending_jobs) {        // ...and every pending job fails
    result.scheduled_jobs.push_back(FailJob(job, assigned.error()));
  }
  return result;
}
```

**Lifetime rule.** `GarageServices` and `DefaultSolver` hold references into the `Scheduler`. Declare `services_` after `motion_graph_`, `collision_table_`, `cost_model_` and `layout_` (today `gg_` and `table_`), and `tray_solver_` after `services_`, so they are destroyed first. A test that builds a solver directly must keep the graph, table, cost model and layout alive for the solver's lifetime.

#### Names in the tray module, and why

Each name follows the naming rules of the catalogue ([section 15.2](#nm-naming-rules)): spell words out, one concept per word, maps named `<value>_by_<key>`, no boolean-sounding names for things that are not booleans. Where reviewers may prefer another name, the table gives the alternatives that were considered and why they were not chosen. None of these names is fixed until review.

| Name                                                                                   | What it names                                                                                                   | Alternatives considered                                          | Why this one                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|----------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `tray_assignment` (folder, namespace)                                                  | Stage 2 of task planning                                                                                        | `tray_movement`, `tray_planning`                                 | Job expansion also plans tray movement (it creates the `TrayMove`s); this stage only assigns what expansion left open. Matches today's `DoTrayAssignments` and pairs with `agv_assignment`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `Solver`, `DefaultSolver`, `Solve`                                                     | The interface, today's algorithm behind it, and its one method                                                  | `TrayAssigner`; `LegacySolver`, `GreedySolver`, `CurrentSolver`  | "Solver" is the ticket's word ("tray solver interface"). `Default` says what `Plan()` uses when nothing else is configured, without judging it: `Legacy` would imply it is to be removed, and `Greedy` describes the algorithm, which may change while the name should not                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `Input`, `Result`                                                                      | What `Solve` reads, and what it returns                                                                         | `TrayAssignmentInput`, `TrayAssignmentResult`                    | The namespace already says "tray assignment": `tray_assignment::Input` reads well, `tray_assignment::TrayAssignmentInput` stutters. The same short names are used in `agv_assignment`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `TrayFill`                                                                             | One blank filled on an **existing** `TrayMove`: a tray id, a destination, or both                               | `TrayAssigned`, `TrayAssignment`, `TrayMoveFill`, `BlankFill`    | Job expansion leaves blanks on some tray moves ("any empty tray", "destination still open"); this record says how one was filled, and the `Result` keeps them in `fills`. `TrayAssigned` is a past participle, which reads as a boolean or an event ("tray was assigned"), and suggests that only the tray is set, while a fill often sets only the destination. `TrayAssignment` repeats the namespace, and the whole `Result` is the assignment, not one entry. `TrayMoveFill` is more exact (the record fills a *move*, not a tray) and is the best alternative if reviewers prefer precision over length. `BlankFill` loses the word "tray" that tells a reader which event type it applies to |
| `fills`, `edits`                                                                       | The two lists in `Result`                                                                                       | `assignments`, `changes`, `operations`                           | Plural nouns for collections; `fills` matches the element type, `edits` matches `DagEdit`. "Changes" would also cover the fills, which are not structural                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `DagEdit`, `AddEvent`, `AddDependency`                                                 | One structural change to the event DAG, recorded instead of applied                                             | `DagOp`, `NewEvent`, `NewEdge`                                   | Named after the `ScheduleEventDag` methods they replay, one for one, so `ApplyTrayAssignment` reads as "call the method named by the record"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `first_event_by_tray`                                                                  | For each tray, the first move in this plan that takes it off its starting node (the hand-off to AGV assignment) | today `first_tray_event`                                         | Map naming rule: `<value>_by_<key>`. Today's name can be read as "the event of the first tray"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `destination` (field of `TrayFill`, `TrayChoice`)                                      | Where the tray goes                                                                                             | today `dest`                                                     | Spell words out; `TrayMove::SetDest` keeps its name until `planner_core` is renamed (stage I)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `ApplyTrayAssignment`                                                                  | The only function that writes a `Result` into the plan context                                                  | `tray_assignment::Apply`, `Commit`, `WriteBack`                  | "Apply" is the verb the event classes already use for "change a state with this" (`ScheduleEvent::Apply`). The longer name keeps the call in `Plan()` readable next to the AGV call, and searchable, at the cost of a small stutter in its qualified form                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `DefaultSolver::Pass`                                                                  | The private working data of one `Solve` call                                                                    | `State`, `Context`, `Workspace`                                  | One object per pass over the DAG. "State" already means the garage state, and "Context" already means `PlanContext`; reusing either would give one word two meanings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `TrayChoice`, `ParkingPlan`, `BlockingResolution`, `PlannedTrayMove`, `ResolveRequest` | Return and argument types of the pure functions                                                                 | today: `std::pair` and nested `std::pair`s, positional arguments | Named fields instead of `.first` / `.second`. Each name says what the function decided: a tray, a parking spot, how blockers are resolved, a move with its path, a request with named parameters                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `scheduler_core::GarageServices`                                                       | The read-only graph, collision table, cost model and layout every search needs                                  | `GarageModel`, `Services`, `Context`                             | "Model" would suggest the garage *state*. They are services the solver calls, and "garage" says which domain; the `scheduler_core` namespace says they are shared by every stage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

### AGV assignment

AGV assignment follows the same outline as tray assignment. It gets the same folder layout, the same `stdx` error types, the same `GarageServices` and the same split into a solver, a private pass and pure functions. One thing differs on purpose: its first version **edits the event DAG in place**, and the signature says so ([section 8.2.5](#pr-agv-why-in-place) explains why). A returned result, like tray assignment's, follows once the benchmarks can prove that nothing changed.

#### The new pieces and how they fit together

Today `DoAgvAssignments(ctx)` decides which AGV performs each tray move, adds the AGV's own events (approach, lift, lower), repairs paths, reduces the DAG and moves bay dependencies, all on the shared context. The proposal keeps the deciding in a `DefaultSolver` and its private `Pass`, moves every computation that only reads into pure functions, and lets `SolveInPlace` write the DAG it is given. It does not write anything else in the context.

The pieces, all in namespace `volley::task_planning::agv_assignment` (folder `task_planning/agv_assignment/`) unless marked otherwise:

| Piece                            | What it is                                                                                                                                             | Declared in                                                                               | Lives for                            | Reads                                                                      | Writes                                           |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|--------------------------------------|----------------------------------------------------------------------------|--------------------------------------------------|
| `scheduler_core::GarageServices` | The same services object as tray assignment                                                                                                            | `include/scheduler/core/garage_services.hpp`                                              | As long as the `Scheduler`           | —                                                                          | nothing                                          |
| `Input`                          | Struct of two `const` references                                                                                                                       | `include/scheduler/task_planning/agv_assignment/solver.hpp`                               | One `SolveInPlace` call              | `initial_state`, `first_event_by_tray` (the hand-off from tray assignment) | nothing                                          |
| `Solver`                         | Interface with one method, `SolveInPlace(const Input&, EventDag&) const`                                                                               | `solver.hpp`                                                                              | Owned by `Scheduler` (`agv_solver_`) | —                                                                          | —                                                |
| `DefaultSolver`                  | Today's algorithm behind the interface; holds only `const GarageServices&`                                                                             | `default_solver.hpp`, `src/task_planning/agv_assignment/default_solver.cpp`               | Owned by `Scheduler`                 | `Input`, services                                                          | the `EventDag&` argument                         |
| `DefaultSolver::Pass`            | **Private nested class**: the loop's working data (garage state, work-queue copy of the DAG, last event per AGV, node occupants, busy and ready times) | declared in `default_solver.hpp`, defined in `src/task_planning/agv_assignment/pass.hpp`  | One `SolveInPlace` call              | `Input`, services                                                          | its own members and the `EventDag&` it was given |
| Pure functions                   | `EstimateTravelTime`, `EstimateTimeToLift`, `EstimateAssignmentCost`, `AgvBusyDuration`, `OrderMatchedAgvs`                                            | `task_planning/travel_cost.hpp`, `agv_assignment/cost.hpp`, `agv_assignment/matching.hpp` | —                                    | their arguments                                                            | nothing                                          |
| Path repair                      | `RepairAgvPaths` and its helpers, today `EnsureAgvMovePathsClear`                                                                                      | `src/task_planning/agv_assignment/path_repair.hpp` (private)                              | —                                    | services, the DAG                                                          | the `EventDag&` (gating edges)                   |
| `volley::BottleneckAssignment`   | The matching itself, from `task_planner`                                                                                                               | unchanged                                                                                 | —                                    | the cost table                                                             | nothing                                          |

There is no `ApplyAgvAssignment`: in the first version the solver's writes go straight into the `EventDag&` it receives. What changes compared with today is that the writes are confined to that one argument, which `Plan()` names at the call, instead of reaching through a shared `ScheduleContextSPtr`.

What happens in `Plan()`, step by step:

1.  **Build the input.** `Input{plan_ctx.initial_state, plan_ctx.first_event_by_tray}`: two `const` references, filled by tray assignment's apply step just before.
2.  **Solve in place.** `DefaultSolver::SolveInPlace` creates a `Pass`, which copies `initial_state` and the DAG's structure (the work queue). Round by round it drains roots that are not tray moves, asks the pure functions for an assignment cost per (AGV, tray move) pair, matches with `BottleneckAssignment`, orders the matched AGVs with `OrderMatchedAgvs`, and tells the `Pass` to emit each AGV's approach, lift and lower and to set the AGV on the tray move. Then, as today and in the same order: path repair, `Reduce()`, and the bay and VECS dependency move (today `AddDepsAfterAmiga`).
3.  **Continue.** `Plan()` runs `Reduce()` again and validation, as today.

``` cpp
// PROPOSED — include/scheduler/task_planning/agv_assignment/solver.hpp
namespace volley::task_planning::agv_assignment {

using FirstEventByTray = std::unordered_map<uint16_t, ScheduleEventSPtr>;   // same type as tray_assignment's

struct Input {                                     // what SolveInPlace may read and must not change
  const DiscreteGarageState& initial_state;        // plan_ctx.initial_state
  const FirstEventByTray& first_event_by_tray;     // plan_ctx.first_event_by_tray, set by ApplyTrayAssignment
};

class Solver {
 public:
  virtual ~Solver() = default;
  // Assigns an AGV to every TrayMove of event_dag and adds the AGVs' events and edges to it.
  // event_dag is edited in place in the first version; the name says so.
  [[nodiscard]] virtual stdx::Result SolveInPlace(const Input& input, EventDag& event_dag) const = 0;
};

}  // namespace volley::task_planning::agv_assignment
```

``` cpp
// PROPOSED — src/task_planning/agv_assignment/pass.hpp (private header)
class DefaultSolver::Pass {
 public:
  Pass(const scheduler_core::GarageServices& services, const Input& input, EventDag& event_dag);
  stdx::Result DrainNonTrayRoots();                                    // bay, VECS and earlier AGV events
  std::vector<ScheduleEventSPtr> TrayMoveRoots() const;               // what the matcher sees this round
  stdx::Result EmitApproach(uint16_t agv_id, const ScheduleEventSPtr& tray_move);   // was MoveAgvToTrayPose
  stdx::Result EmitLift(uint16_t agv_id, size_t job_index);           // was AppendAgvLiftEvent(raised = true)
  stdx::Result EmitLower(uint16_t agv_id, size_t job_index);          // was AppendAgvLiftEvent(raised = false)
  stdx::Result CommitTrayMove(uint16_t agv_id, const ScheduleEventSPtr& tray_move);  // SetAgvId, edges, apply
  const DiscreteGarageState& State() const { return working_state_; }
 private:
  stdx::Result OrderArrivalAfterOccupant(uint32_t node_id, uint16_t agv_id,
                                         const ScheduleEventSPtr& event);   // was AddNodeArrivalDeps
  void PropagateReadyTime(const ScheduleEventSPtr& event, Duration cost);   // was PropagateEventCostToChildren
  const scheduler_core::GarageServices& services_;
  EventDag& event_dag_;                                                 // the caller's DAG: written here
  EventDag work_queue_;                                                 // structural copy, consumed root by root
  DiscreteGarageState working_state_;
  std::unordered_map<uint16_t, ScheduleEventSPtr> last_event_by_agv_;
  std::unordered_map<uint16_t, ScheduleEventSPtr> last_approach_by_agv_;
  std::unordered_map<uint32_t, uint16_t> agv_by_node_;                // was current_node_occupant
  std::unordered_map<uint16_t, Duration> busy_duration_by_agv_;       // was agv_occupied_durations
  std::unordered_map<ScheduleEventSPtr, Duration> ready_time_by_event_;  // was event_occupied_durations
};
```

#### Source tree

The tree is the one of [section 8.1.2](#pr-source-tree); the AGV folder holds:

``` text
include/scheduler/task_planning/
├── travel_cost.hpp                   # EstimateTravelTime (was GetJustMovingCost); also used by job expansion
└── agv_assignment/
    ├── solver.hpp                    # Solver, Input, FirstEventByTray
    ├── default_solver.hpp            # DefaultSolver (declares the private nested Pass)
    ├── cost.hpp                      # EstimateTimeToLift, EstimateAssignmentCost, AgvBusyDuration
    └── matching.hpp                  # OrderMatchedAgvs (was GetEventDag, AgvMatchingEventDeps, DagToVec)
src/task_planning/
├── travel_cost.cpp
└── agv_assignment/
    ├── default_solver.cpp            # SolveInPlace(): the round loop
    ├── pass.hpp, pass.cpp            # PRIVATE: DefaultSolver::Pass
    ├── cost.cpp, matching.cpp
    ├── path_repair.hpp               # PRIVATE: RepairAgvPaths, RepairPass, TryGateBlockedMove, FindDeparture
    ├── path_repair.cpp
    └── transition_deps.cpp           # MoveTransitionDependencies (was AddDepsAfterAmiga)
test/task_planning/agv_assignment/    # cost_test, matching_test, path_repair_test, default_solver_test
```

The boundaries are the same as for tray assignment: the folder is part of the `scheduler_task_planning` target, it never includes `tray_assignment/` (the hand-off is the plain map in `Input`), and its tests link only that target.

#### Before and after: the AGV call tree

The same question sorts every function: **what does it write?**

| Today (all `Scheduler` members)                                                                                | Writes today                                   | Proposed                                                                                         | Group                          |
|----------------------------------------------------------------------------------------------------------------|------------------------------------------------|--------------------------------------------------------------------------------------------------|--------------------------------|
| `DoAgvAssignments`                                                                                             | `ctx->events`, fields of tray moves            | `DefaultSolver::SolveInPlace`                                                                    | Solver class                   |
| `MoveAgvToTrayPose`, `AppendAgvLiftEvent`, `AddNodeArrivalDeps`, `PropagateEventCostToChildren`                | `ctx->events` and five local maps by reference | `Pass::EmitApproach`, `EmitLift`, `EmitLower`, `OrderArrivalAfterOccupant`, `PropagateReadyTime` | Private, mutable, one per call |
| `GetJustMovingCost`, `GetAgvCurrentPoseToTrayMoveCost`, `GetAgvToTrayAssignmentCost`, `GetAgvOccupiedDuration` | nothing                                        | `EstimateTravelTime`, `EstimateTimeToLift`, `EstimateAssignmentCost`, `AgvBusyDuration`          | Pure                           |
| `GetEventDag`, `AgvMatchingEventDeps`, `DagToVec`                                                              | nothing                                        | `OrderMatchedAgvs`                                                                               | Pure                           |
| `EnsureAgvMovePathsClear`, `RunAgvPathRepairPass`, `TryClearBlockedAgvMove`, `FindAgvDepartureFromNode`        | `ctx->events` (gating edges)                   | `RepairAgvPaths` and private helpers, taking the `EventDag&`                                     | Writes the DAG it is given     |
| `AddDepsAfterAmiga`                                                                                            | `ctx->events`                                  | `MoveTransitionDependencies`, taking the `EventDag&`                                             | Writes the DAG it is given     |

Two of today's facts carry over unchanged, because parity depends on them: `GetAgvOccupiedDuration` returns zero (`TODO(isabel)`), and `Reduce()` runs at the end of the stage and again in `Plan()` ([section 13](#pr-risks-that-must-not-be-silently-fixed)). `GetJustMovingCost` is also called by `PlanAgvChargeJob`; as a pure function in `task_planning/travel_cost.hpp` it stays reachable from job expansion without a back-reference.

#### Errors

The rules of [section 8.1.4](#pr-errors-stdxexpected-instead-of-boolstringpair) apply unchanged. Concretely:

| Today                                                                                            | Proposed                                                                                |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `BoolStringPair DoAgvAssignments(ctx)`                                                           | `stdx::Result SolveInPlace(input, event_dag)`                                           |
| `BoolStringPair` from `MoveAgvToTrayPose`, `AppendAgvLiftEvent`, `AddNodeArrivalDeps`            | `stdx::Result` from the `Pass` methods                                                  |
| `throw std::runtime_error("... Failed to topologically sort the DAG")` inside `DoAgvAssignments` | `return stdx::Unexpected(...)`: today an exception escapes `Plan()` from this one place |
| `std::optional<Duration>` from the cost functions ("no path")                                    | unchanged: a searched-and-not-found answer the caller handles itself (rule 2)           |
| `stdx::Result EnsureAgvMovePathsClear`, `stdx::Expected<bool> RunAgvPathRepairPass`              | unchanged types, new names                                                              |

The error texts stay identical for the parity pass, as for tray assignment.

#### Why edit in place first, and how a result can follow

Returning a result is harder for AGV assignment, for reasons visible in the code:

- The AGV loop **reads the DAG it is building.** It consumes `event_dag_copy` root by root (`event_dag_copy.Remove(root_event)`), and `EnsureAgvMovePathsClear` repeatedly inspects edges added earlier in the same stage (up to 256 repair passes), followed by `Reduce()`.
- It **reads back fields it set**: `SetAgvId` on a `TrayMove`, then `GetAgvId()` on candidate moves while building later dependencies.

An edit log could still work, if the solver keeps a private *structural* copy of the DAG (the default copy constructor copies `dag_` and `ptr_to_vertex_`, so the copy shares the events), applies every edit to that copy as it goes, and logs it, including a `Reduce` step. The log must name events by pointer, never by vertex: `Remove` on the work-queue copy renumbers its vertices. The field reads are the real obstacle: they would need either cloned events with an identity map (and `planner_core` has no `Clone()`, see [section 8.1.5](#pr-why-return-a-result-and-how-it-is-applied)), or a side table (`agv_by_event`) replacing every `GetAgvId()` read, which touches parity-sensitive code.

**Recommendation:** for stage F, the same layout and `stdx` types, an `Input` plus an explicitly mutable `EventDag&` named as such in the signature. Convert it to a returned result after the benchmarks exist and can prove nothing changed. The returned form would mirror tray assignment: a `Result` with `fills` (an `AgvFill` per tray move: the AGV id set on an existing `TrayMove`), ordered `edits` (the approach, lift and lower events, their edges, the repair edges and a `Reduce` marker), and an `ApplyAgvAssignment` that replays them.

**What in place still guarantees.** Only the `EventDag&` argument is written: `initial_state` and `first_event_by_tray` are `const`, and nothing reaches the rest of the plan context. A failure halfway leaves that DAG half-edited, as today; `Plan()` discards the whole response in that case, so the contract to Dispatch does not change.

#### Free-function signatures and the `Plan()` call site

The first listing declares the shared travel-time estimate and the cost and ordering functions of the AGV module; each comment names the function it replaces. The second listing shows the call in `Plan()` right after tray assignment: `SolveInPlace` receives the event DAG as a separate, mutable argument, and a failure fails every pending job, as it does for tray assignment.

``` cpp
// PROPOSED — include/scheduler/task_planning/travel_cost.hpp and agv_assignment/cost.hpp, matching.hpp
namespace volley::task_planning {
// Travel time between two poses, without blocking moves; nullopt if there is no path (was GetJustMovingCost).
[[nodiscard]] std::optional<Duration> EstimateTravelTime(const scheduler_core::GarageServices& services,
    const Pose& start, const Pose& end, AssetId agv, bool agv_loaded,
    std::optional<GraphFilterProperties> filters = std::nullopt);
}  // namespace volley::task_planning

namespace volley::task_planning::agv_assignment {
// Travel to the tray plus the lift, if the AGV does not hold it yet (was GetAgvCurrentPoseToTrayMoveCost).
[[nodiscard]] std::optional<Duration> EstimateTimeToLift(const scheduler_core::GarageServices& services,
    const DiscreteGarageState& state, uint16_t agv_id, const TrayMove& move);
// Busy time plus time to lift; nullopt if infeasible (was GetAgvToTrayAssignmentCost).
[[nodiscard]] std::optional<Duration> EstimateAssignmentCost(const scheduler_core::GarageServices& services,
    const DiscreteGarageState& state, uint16_t agv_id, const TrayMove& move, Duration agv_busy);
// Time the AGV is already committed for (was GetAgvOccupiedDuration; returns zero today, kept for parity).
[[nodiscard]] Duration AgvBusyDuration(uint16_t agv_id);
// The order in which matched AGVs are expanded, so that one does not drive into another's path
// (was GetEventDag + AgvMatchingEventDeps + DagToVec).
[[nodiscard]] std::vector<AgvMatch> OrderMatchedAgvs(const scheduler_core::GarageServices& services,
    const DiscreteGarageState& state, const std::unordered_map<uint16_t, ScheduleEventSPtr>& match_by_agv);
}  // namespace volley::task_planning::agv_assignment
```

``` cpp
// PROPOSED — src/scheduler.cpp, Scheduler::Plan, right after tray assignment
// agv_solver_ : std::unique_ptr<agv_assignment::Solver>, new member declared after services_
if(auto assigned = agv_solver_->SolveInPlace({plan_ctx->initial_state, plan_ctx->first_event_by_tray},
                                              plan_ctx->event_dag);
   !assigned) {
  result.success = true;                                    // unchanged failure contract, as for trays
  result.message = "Failed AGV assignments: " + assigned.error();
  for(const auto& job : request_data.pending_jobs) {
    result.scheduled_jobs.push_back(FailJob(job, assigned.error()));
  }
  return result;
}
```

The lifetime rule is the one of tray assignment: `agv_solver_` is declared after `services_`, so it is destroyed first.

#### Names in the AGV module, and why

The module uses the tray module's names wherever the concept is the same (`Solver`, `DefaultSolver`, `Input`, `Pass`, `GarageServices`, `first_event_by_tray`), so a reader who knows one module can read the other. The names that are new:

| Name                                                                 | What it names                                                                      | Alternatives considered                                                              | Why this one                                                                                                                                                                                                                                                                                                      |
|----------------------------------------------------------------------|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `agv_assignment` (folder, namespace)                                 | Stage 3 of task planning                                                           | `agv_matching`, `amiga`                                                              | Matching is one step of the stage, which also adds the AGVs' events and repairs paths. "AMIGA" (the code's nickname, "Arguably More Intelligent aGv Assignment") cannot be guessed by a new reader                                                                                                                |
| `SolveInPlace`                                                       | The interface method                                                               | `Solve`, `Assign`, `Apply`                                                           | The one method that writes its argument should say so where it is called. Keeping `Solve` would make the two interfaces look alike while behaving differently; `InPlace` is the usual suffix for "modifies its input". When the returned result arrives, the method becomes `Solve` and the difference disappears |
| `FirstEventByTray`                                                   | The hand-off map type                                                              | repeating the full `std::unordered_map` type                                         | One alias, named after the field it types, so both modules name the hand-off the same way without including each other                                                                                                                                                                                            |
| `EmitApproach`, `EmitLift`, `EmitLower`                              | Add the AGV's own events for one tray move                                         | `MoveAgvToTrayPose`, `AppendAgvLiftEvent(raised)`                                    | "Emit" is the verb the tray module uses for "add events and edges to the plan". Two functions instead of a `bool raised` argument: a call site reads `EmitLower(...)` instead of `AppendAgvLiftEvent(..., false, ...)`                                                                                            |
| `CommitTrayMove`                                                     | Set the AGV on the tray move, add its edges, apply it to the working state         | inline in today's loop                                                               | Mirrors `CommitRootMove` in the tray module                                                                                                                                                                                                                                                                       |
| `OrderArrivalAfterOccupant`                                          | The edge "the previous occupant leaves before this AGV arrives"                    | `AddNodeArrivalDeps`                                                                 | Says which order the edge enforces. "Deps" is an abbreviation (rule: spell words out)                                                                                                                                                                                                                             |
| `PropagateReadyTime`, `ready_time_by_event_`                         | Earliest time a later event can start                                              | `PropagateEventCostToChildren`, `event_occupied_durations`                           | The value is a time, not a cost and not a duration of occupation; map naming rule                                                                                                                                                                                                                                 |
| `busy_duration_by_agv_`, `AgvBusyDuration`                           | How long an AGV is already committed                                               | `agv_occupied_durations`, `GetAgvOccupiedDuration`                                   | "Occupied" already means "a node is occupied" in the collision code; "busy" avoids the clash                                                                                                                                                                                                                      |
| `agv_by_node_`                                                       | Which AGV stands on each node during the pass                                      | `current_node_occupant`                                                              | Map naming rule; the value is an AGV id                                                                                                                                                                                                                                                                           |
| `EstimateTravelTime`, `EstimateTimeToLift`, `EstimateAssignmentCost` | The three cost functions                                                           | `GetJustMovingCost`, `GetAgvCurrentPoseToTrayMoveCost`, `GetAgvToTrayAssignmentCost` | "Estimate" says they are predictions, not measurements; each name says what is estimated. "Just moving" means "travel only, no blocking moves", which the comment explains and the name does not                                                                                                                  |
| `OrderMatchedAgvs`                                                   | The order in which matched AGVs are expanded                                       | `GetEventDag`, `DagToVec`                                                            | Today's names describe the data structure (a DAG of AGV ids), not the purpose, and `GetEventDag` is easily confused with the event DAG                                                                                                                                                                            |
| `RepairAgvPaths`                                                     | The post-assignment repair                                                         | `EnsureAgvMovePathsClear`                                                            | Shorter and says it changes something; the current name reads like a check                                                                                                                                                                                                                                        |
| `MoveTransitionDependencies`                                         | Moves a bay or VECS transition's edges from tray moves to the AGV's lift and lower | `AddDepsAfterAmiga`                                                                  | Says what the step does (the naming catalogue asks for this, [section 15.4.3](#nm-pipeline-stage-names)); "after AMIGA" says only when it runs                                                                                                                                                                    |
| `AgvFill` (later)                                                    | The AGV id set on an existing `TrayMove`, in the future returned result            | `AgvAssigned`, `AgvAssignment`                                                       | Same reasons as `TrayFill`: not a boolean-sounding participle, and not the stage's own name                                                                                                                                                                                                                       |

## Naming and the ROS boundary

The refactor rewrites most of the code it touches, so it is the cheapest moment to fix names. The naming catalogue ([section 15](#nm-proposed-future-work-naming)) lists the recommendations for the whole stack. This section takes the subset that can be done now, under one constraint: **renames stay inside `scheduler` and `planner_core`**. `common_ros` and the ROS interfaces are used by too many other packages, so their renames come later.

Two mechanisms let the scheduler use the good names before `common_ros` changes:

- **One translation header** (`core/vocabulary.hpp`) gives `common_ros` types and enum values their names from the naming catalogue, as aliases. An alias is the same type, so nothing is converted at run time, and `common_ros` does not change.
- **Internal types at the ROS edge** (`core/types.hpp` and `ros/convert.hpp`). Where the scheduler builds a ROS message for its own bookkeeping, or keys a map with one, it uses a plain C++ struct instead. It converts to and from the message only where it talks to ROS or to `common_ros`.

When `common_ros` or the interfaces later adopt a name, the matching line in the translation header or the matching conversion is deleted, and scheduler code does not change.

### What is renamed, and what is translated

The packages the scheduler uses are treated differently according to how many other packages depend on their names. The table states, per package, whether its names change in this refactor and by which mechanism: only `scheduler` and `planner_core` are renamed, while `common_ros` and the ROS interfaces keep their names and are translated at the scheduler's boundary.

| Package                     | In this refactor                                     | How                                                                                                                                                                                                                                                             |
|-----------------------------|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scheduler`                 | Renamed ([section 7.4](#pr-renames-in-scheduler))    | Directly. Only `scheduler`'s own tests and `scheduler_advanced_tests` see these names                                                                                                                                                                           |
| `planner_core`              | Renamed ([section 7.5](#pr-renames-in-planner-core)) | Every old name stays as a `[[deprecated]]` alias or forwarding method until its other users have moved. List them with `colcon list --packages-above planner_core`                                                                                              |
| `common_ros`                | Not renamed                                          | Translated by aliases and thin wrappers in `core/vocabulary.hpp` ([section 7.2](#pr-the-translation-header))                                                                                                                                                    |
| `interfaces` (ROS messages) | Not renamed                                          | Messages the scheduler builds or keys maps with become internal types, converted in `ros/convert.hpp` ([section 7.3](#pr-internal-types-instead-of-messages)). Messages that are already well named, or that `common_ros` and the events need, stay as they are |

![Naming and the ROS boundary](figures/83_naming_boundary.svg)

**Three layers.** Top: ROS messages and `common_ros`, unchanged. Middle: the boundary inside the scheduler. `scheduler_ros.cpp` (existing) receives the plan request; `ros/convert.hpp` turns messages into internal types and back; `core/vocabulary.hpp` gives `common_ros` names their new spelling. Bottom: scheduler code, the new solver modules and `planner_core`, all using the new names. `DiscreteGarageState` and the event payloads still carry messages and pass through unchanged.

Three rules keep the boundary in place. Each one can be checked in CI with the same kind of one-line grep as the dependency rules in [section 6.2](#pr-source-tree):

1.  **Only `core/vocabulary.hpp` spells a `common_ros` name that the naming catalogue renames.** The check: `rg -nw 'GarageGraph|PoseGraph|CollisionEntityId|CollisionEntityId_t|VertexCollisionIdMap|GarageNodeFromVertex|GetFromGarageRep|LOCOMOTE|STRAFE' include src --glob '!include/scheduler/core/vocabulary.hpp'` must print nothing. Start it as a report of remaining uses, and make it fail the build once the count reaches zero.
2.  **Only `ros/` and `scheduler_ros.cpp` convert messages.** No file under `tray_assignment/`, `agv_assignment/` or `core/` includes `ros/convert.hpp`.
3.  **The solver modules include no `rclcpp` header.** The logger reaches them through `GarageServices`, as already proposed.

### The translation header

`core/vocabulary.hpp` is the only scheduler file that spells the `common_ros` names the naming catalogue would change; every other scheduler file uses the names it declares, and `common_ros` itself is not modified. The listing has three parts: type aliases, renamed enum values, and thin inline wrappers for functions whose `common_ros` name or shape is misleading.

``` cpp
// PROPOSED — include/scheduler/core/vocabulary.hpp
// The one scheduler header that spells common_ros names the naming catalogue would change. Scheduler code uses the names
// declared here. When common_ros adopts a name, delete its line here; no other scheduler file changes.
#pragma once
#include "common_ros/collision_geometry.hpp"
#include "common_ros/garage_graph.hpp"
#include "common_ros/pose_graph.hpp"

namespace volley::scheduler_core {

// ---- types: aliases, so no conversion and no run-time cost
using Pose                = GaragePoseMsg;                        // the word is right; only the suffix goes
using MotionGraph         = ::volley::GarageGraph;                // catalogue: GarageGraph -> MotionGraph
using PoseLattice         = ::volley::PoseGraph;                  // catalogue: PoseGraph -> PoseLattice
using Vertex              = MotionGraph::Vertex;
using FootprintType       = ::volley::CollisionEntityId;          // catalogue: CollisionEntityId -> FootprintType
using FootprintId         = ::volley::CollisionEntityId_t;
using FootprintIdByVertex = ::volley::VertexCollisionIdMap;
using Segment             = ::volley::CollisionTable::Edge;       // two poses, as a collision-table key
using PoseOrSegment       = ::volley::CollisionTable::PoseOrEdge;

// ---- enum values whose common_ros spelling is misleading
namespace transition_type {
inline constexpr TransitionType TRANSLATE_LONGITUDINAL = TransitionType::LOCOMOTE;
inline constexpr TransitionType TRANSLATE_LATERAL      = TransitionType::STRAFE;
inline constexpr TransitionType ROTATE                 = TransitionType::ROTATION;
inline constexpr TransitionType RIDE_VRC               = TransitionType::VRC_TRANSITION;
}  // namespace transition_type

// ---- functions whose common_ros name or shape is misleading: thin and inline
inline std::optional<GarageNodeMsg> GetNodeFromVertex(const MotionGraph& graph, Vertex v) {
  return graph.GarageNodeFromVertex(v);
}
// Transition::length is metres for translations and VRC rides, radians for rotations (naming catalogue).
inline double DistanceM(const Transition& t) { return t.type == TransitionType::ROTATION ? 0.0 : t.length; }
inline double AngleRad(const Transition& t)  { return t.type == TransitionType::ROTATION ? t.length : 0.0; }

}  // namespace volley::scheduler_core
```

Why aliases and not wrapper classes: an alias is the same type, so a `const MotionGraph&` can be passed to any `common_ros` function that takes a `const GarageGraph&`, and the parity tests cannot see a difference. The cost is that compiler errors and debuggers print the real name (`volley::GarageGraph`); the header comment is the map back. Functions are wrapped only where the `common_ros` name or shape misleads. `GetFromGarageRep` is not wrapped: it duplicates `GetVertexFromPose(pose).value()`, so the CI check above simply forbids it.

### Internal types instead of messages

Today the scheduler uses ROS messages for its own bookkeeping, not only at its interface. `ScheduleContext::scheduled_jobs` is a vector of `ScheduledJobDataMsg` built during planning, `last_entity_event` is keyed by `GarageEntityIdMsg`, and the context's constructor takes an `rclcpp::Time`. These are the places where a plain struct is clearer, and where the conversion happens once, at the edge:

| Used inside today                                                                                                                  | Internal type                                                                                            | Converted where                                                                                     | When                                                                                                          |
|------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `GarageEntityIdMsg`: keys of `last_entity_event`; returned by `ScheduleEvent::GetGarageEntityId()`                                 | `AssetId {AssetType type; uint16_t id;}`, with `AssetType` an enum of the six letters                    | `ToAssetId` where an event or `common_ros` hands over the message; `ToMsg` where one is handed back | Stage B2, with the `PlanContext` rename                                                                       |
| `ScheduledJobDataMsg`: `scheduled_jobs`                                                                                            | `ScheduledJob` (below): the job plus the fields planning adds, with `std::optional` for "retrieves only" | `ToMsg` in `BuildPlanResponse` (today `ResponseFromTrajectories`)                                   | Stage B2                                                                                                      |
| `rclcpp::Time` in the context constructor                                                                                          | `volley::Interval::Timepoint`, already the type of `start_time`                                          | `Plan()`'s caller                                                                                   | Stage B2                                                                                                      |
| `SchedulerJobMsg` as the input to job expansion. Its fields are "only set if the job is of the correct type", so `0` means "unset" | A `Job` with `std::optional` fields, or one struct per job type                                          | Once, at the start of `Plan()`                                                                      | Later: it touches all eleven expansion methods, so it is a separate change                                    |
| `GaragePoseMsg`                                                                                                                    | none; alias `Pose`                                                                                       | —                                                                                                   | Keep: the name is right, and every `common_ros` graph and collision call takes it                             |
| `DiscreteGarageState` and the messages inside events (`DiscreteBayStateMsg`, `BayCommandMsg`, `AgvLiftChangedMsg`, …)              | none                                                                                                     | —                                                                                                   | Keep: `Apply` hands them to `DiscreteGarageState` (in `common_ros`), so converting would mean converting back |

``` cpp
// PROPOSED — include/scheduler/core/types.hpp (no ROS or rclcpp includes)
namespace volley::scheduler_core {
enum class AssetType : uint8_t { AGV = 'a', BAY = 'b', TRAY = 't', VECS = 'v', VRC = 'r', SYSTEM = 's' };
struct AssetId {
  AssetType type;
  uint16_t id;
  friend bool operator==(const AssetId&, const AssetId&) = default;
};
struct AssetIdHash {
  std::size_t operator()(const AssetId& a) const noexcept {
    return (static_cast<std::size_t>(a.type) << 16) | a.id;   // exact: 8 + 16 bits, no collisions
  }
};
}  // namespace volley::scheduler_core

// PROPOSED — include/scheduler/plan_context.hpp (split out of scheduler.hpp)
struct ScheduledJob {                                   // one expanded job; a ScheduledJobDataMsg in the response
  SchedulerJobMsg job;                                  // the request's job, as received
  std::vector<uint32_t> action_indices;                 // today node_indices
  std::optional<uint16_t> bay_id;                       // retrieves only
  std::optional<GuidMsg> bay_arrival_action_id;         // retrieves only; today bay_arrival_node_guid
};

// PROPOSED — include/scheduler/ros/convert.hpp, src/ros/convert.cpp
namespace volley::ros_convert {
[[nodiscard]] stdx::Expected<scheduler_core::AssetId> ToAssetId(const GarageEntityIdMsg& msg);  // error on an unknown letter
GarageEntityIdMsg ToMsg(const scheduler_core::AssetId& id);
ScheduledJobDataMsg ToMsg(const ScheduledJob& job);     // empty optionals become today's zeros
}  // namespace volley::ros_convert
```

`ToMsg(const ScheduledJob&)` writes `0` and an all-zero `Guid` where an optional is empty, which is what the response holds today, so clients see no change. `ToAssetId` returns `stdx::Expected` because the message's `entity_type` is a one-character string that can hold any letter. `AssetIdHash` packs the two fields into one number with no collisions; today's `std::hash<GarageEntityIdMsg>` combines two hashes and has to read the letter out of a string.

**Limits.** This is a boundary for the scheduler's *own* data, not a full separation from ROS. The state engine (`DiscreteGarageState`), the graph API and the event classes still take messages, because they live in `common_ros` and `planner_core` and other packages share them. Separating those is a `common_ros` project. When it happens, the boundary files are where the work goes, and scheduler code stays as it is.

### Renames in `scheduler`

The rows of the naming catalogue ([section 15](#nm-proposed-future-work-naming)) for the scheduler package. Each rename is its own commit with no logic change, and the parity tests of the [Verification](#doc-verification) tab confirm it.

| Current                                                                   | New                                                                                                                                                  | Stage                                   |
|---------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| `gg_`, `table_`, `GetGarageGraph()`                                       | `motion_graph_`, `collision_table_`, `GetMotionGraph()`                                                                                              | B2                                      |
| `pg_`                                                                     | a local in the constructor (only used to build `gg_`)                                                                                                | B2                                      |
| `costaudit_`, `printdags_`, `PrintDags()`                                 | `cost_audit_`, `print_dags_`, `TogglePrintDags()`                                                                                                    | B2                                      |
| `ScheduleContext`, `ScheduleContextSPtr`                                  | `PlanContext`, `PlanContextSPtr`                                                                                                                     | B2                                      |
| `events`, `request_id_str`                                                | `event_dag`; remove `request_id_str`                                                                                                                 | B2                                      |
| `disabledness_filters` (`CollistionFilterMap`)                            | `keep_out_filter_by_footprint` (`KeepOutFilterByFootprint`)                                                                                          | B2                                      |
| The `base_schedule` loop inline in `Plan()`                               | `ReserveBaseScheduleAssets(const ScheduleMsg&, DiscreteGarageState&) -> BaseScheduleReservation`, kept in the context as `reserved_by_base_schedule` | B2                                      |
| `last_entity_event` (`GarageEntityEventMap`), `first_tray_event`          | `last_event_by_asset` (`AssetEventMap`, keyed by `AssetId`), `first_event_by_tray`                                                                   | B2                                      |
| `PushBackScheduledJob`, `UpdateLastEntityEvent`, `UpdateLeafDependencies` | `AddScheduledJob`, `AppendToAssetChain`, `AddAfterJobLeaves`                                                                                         | B2                                      |
| `Plan<Type>Job` (11 methods)                                              | `Expand<Type>Job`                                                                                                                                    | B2                                      |
| `DoTrayAssignments`, `DoAgvAssignments`                                   | replaced by `tray_assignment::Solve` and `agv_assignment::SolveInPlace`                                                                              | D, F                                    |
| `SanityCheckEvents`, `ResponseFromTrajectories`                           | `ValidateEvents`, `BuildPlanResponse`                                                                                                                | H                                       |
| `AddDepsAfterAmiga`                                                       | a name that says what it does, agreed with its author                                                                                                | F                                       |
| `BoolStringPair` returns                                                  | `stdx::Result` / `stdx::Expected` ([section 6.4](#pr-errors-stdxexpected-instead-of-boolstringpair))                                                 | C1 onwards, as each function is touched |

### The base-schedule reservation and the keep-out map

The Background tab explains why `Plan()` marks everything the running schedule uses as disabled, where the flags are read and what `disabledness_filters` is for ([section 11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters) there). The recommended changes:

All of them stay inside `scheduler`; the `common_ros` setters and flags are unchanged.

1.  **Extract and name the loop (no behaviour change).** A free function states the intent and returns a record of what it reserved:

    ``` cpp
    // include/scheduler/core/base_schedule_reservation.hpp (proposed)
    struct BaseScheduleReservation {
      std::set<uint16_t> agvs, bays, vecs;   // assets with actions in base_schedule
      std::set<uint32_t> nodes;              // sources and destinations of its AGV commands
      bool HoldsAgv(uint16_t agv_id) const { return agvs.count(agv_id) > 0; }
    };

    // Marks every reserved asset disabled in `state` (as today) and returns what it marked.
    BaseScheduleReservation ReserveBaseScheduleAssets(const interfaces::msg::Schedule& base_schedule,
                                                      volley::DiscreteGarageState& state);
    ```

    `Plan()` keeps the record in the context as `reserved_by_base_schedule`.

2.  **Say why a job failed.** Where a check finds `disabled`, consult the record first: “AGV-2 is reserved by the running schedule” instead of “Tried to move a disabled agv 2”. Only messages change; tests that match the old text need updating.

3.  **Rename the keep-out map** to `keep_out_filter_by_footprint` ([section 16.4.2](#nm-schedulecontext)), and build it through `BuildKeepOutFilters`, which returns a type with a checked lookup.

4.  **Reserve VRCs.** Add `TYPE_VRC_COMMAND` to the loop once task planning supports VRCs ([section 8](#ly-vrc-support-status)); until then it changes nothing.

5.  **Later, time-bounded reservations (behaviour change).** CHUGG already starts from a `ContinuousState` whose trajectories have end times, and it starts each AGV when its initial trajectory ends. Seeding those trajectories with the base actions (where each busy AGV goes, and until when) would let a busy AGV take new work after its last base action and free reserved nodes once they are vacated. This is the persistent-planning idea of the Action graph tab. Task planning would then have to start a busy AGV at its base-schedule end pose, and Dispatch would have to agree how a plan that continues a busy AGV's queue is joined. It is listed as a review decision ([section 12](#pr-decisions-to-resolve-in-review)).

### Renames in `planner_core`

`planner_core` is the second package renamed in this refactor. Unlike `scheduler`, it has other users, so each old name remains available as a `[[deprecated]]` alias or forwarding method until those users have moved; the table lists the renames, and the excerpt after it shows how the old names stay usable.

| Current                                                                | New                                                                | Note                                                                                                                                                 |
|------------------------------------------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ScheduleEventDag`                                                     | `EventDag`                                                         | "Schedule" is the response's DAG of actions, a different graph                                                                                       |
| `BayTransition`, `VecsTransition`, `VrcTransition`                     | `BayStateChange`, `VecsStateChange`, `VrcStateChange`              | Frees "transition" for the motion graph; matches the `*StateChanged` messages they apply                                                             |
| `ScheduleEventType::{BAY_TRANSITION, VECS_TRANSITION, VRC_TRANSITION}` | `{BAY_STATE_CHANGE, VECS_STATE_CHANGE, VRC_STATE_CHANGE}`          | Old enumerators kept as deprecated duplicates. Check that `common::EnumNameString`, which prints them in `ToString`, handles two names for one value |
| `job_idx_`; `ToString()` prints `"Task ID: "`                          | `job_index_`; `"job_index="`                                       | Log text changes: search tests and log tooling for `Task ID` first                                                                                   |
| `TrayMove::dest_`, `SetDest`, `GetDest`                                | `destination_`, `SetDestination`, `GetDestination`                 | Same word as `SchedulerJob.destination`                                                                                                              |
| `BayTransition::src_state_`, `SetSourceState`                          | `from_state_`, `SetFromState`                                      | from/to for state changes                                                                                                                            |
| `AgvMove::discrete_change_`                                            | `change_`                                                          | Private member; no alias needed                                                                                                                      |
| `GetGarageEntityId()`                                                  | `GetAssetId()`, still returning `std::optional<GarageEntityIdMsg>` | The message type stays; the scheduler converts with `ToAssetId`                                                                                      |

How the old names stay usable for `planner_core`'s other users:

``` cpp
// PROPOSED — planner_core/include/planner_core/schedule_events.hpp (excerpt)
class BayStateChange : public ScheduleEvent { /* was BayTransition */ };
using BayTransition [[deprecated("use BayStateChange")]] = BayStateChange;

class TrayMove : public ScheduleEvent {
 public:
  void SetDestination(GaragePoseMsg destination) { destination_ = std::move(destination); }
  std::optional<GaragePoseMsg> GetDestination() const { return destination_; }
  [[deprecated("use SetDestination")]] void SetDest(GaragePoseMsg d) { SetDestination(std::move(d)); }
  [[deprecated("use GetDestination")]] std::optional<GaragePoseMsg> GetDest() const { return destination_; }
  // ...
};

// event_dag.hpp
class EventDag : public DagBase<ScheduleEvent> { /* was ScheduleEventDag */ };
using ScheduleEventDag [[deprecated("use EventDag")]] = EventDag;
```

One trap: if any dependent package builds with `-Werror`, a deprecation warning fails its build. Either add `-Wno-error=deprecated-declarations` to those packages during the migration, or update them in the same change. Remove the aliases once `colcon list --packages-above planner_core` shows no package that still uses an old name.

### What waits for `common_ros` and the interfaces

Everything else in the naming catalogue, done later in those packages. The scheduler is already insulated from each change:

- **`common_ros` class and member names** (`GarageGraph`, `PoseGraph`, `CollisionEntityId`, `gg_` inside `CollisionTable`, `ppmap_`, the `Layout` map names): delete the matching line in `core/vocabulary.hpp`.
- **The `Transition` struct split** (`distance_m`, `angle_rad`) and **bundled edge properties** instead of `boost::property<edge_index_t, …>` (the [Background](#doc-background) tab, [reading the type](#bg-reading-the-boost-adjacency-list-type)): delete `DistanceM` and `AngleRad`; their callers switch to the fields.
- **Message renames** (`GarageEntityId` → `AssetId`, the id widths, `from`/`to` on state changes, the command fields): only `ros/convert.*` and `scheduler_ros.cpp` change.

## Key invariants to maintain

The refactor must move code without changing what `Scheduler::Plan` produces, so every stage of the plan has to preserve the properties listed below. Most of them describe behaviour the scheduler has today; the last three are contracts that the new tray solver and `ApplyTrayAssignment` introduce.

1.  Every `TrayMove` that will execute has a tray id and a destination after tray assignment.
2.  The DAG stays acyclic; `GetTopologicalOrdering()` must succeed after each solver.
3.  Each tray's moves form a chain in physical order, and `first_tray_event[tray_id]` (`first_event_by_tray` after the rename in [section 7](#pr-naming-and-the-ros-boundary)) is that tray's first move (not its last; using the last creates cycles when one AGV moves a tray twice).
4.  Blocking-tray moves are created in recursive prerequisite order, and a tray already being moved is not chosen to move again in the same resolution.
5.  AGV matches respect disabled AGVs, AGVs trapped in a bay that is not `STATE_READY_TO_RETRIEVE`, reachability, collisions, lift state and AGVs already busy.
6.  Arrival ordering never puts two AGVs on one node: `AddNodeArrivalDeps` and `EnsureAgvMovePathsClear` keep doing their jobs.
7.  `Scheduler::Plan` output is unchanged, apart from log text. The DAG side is deterministic for a given build order (job index first, then heap order); remaining variation comes from `unordered_map` iteration elsewhere, for example the order of `result.scheduled_jobs` ([section 13](#bg-schedulecontext-in-depth-job-indices-and-bookkeeping-maps)).
8.  `Reduce()` and path-repair placement stay where they are during extraction.
9.  `tray_assignment::Solver::Solve` changes nothing reachable from its `Input`; `ApplyTrayAssignment` is the only place tray assignment writes `ctx`. A test snapshots every event's fields before `Solve` and compares after.
10. `ApplyTrayAssignment` replays `Result::edits` in recorded order, so vertex indices, edge sets **and the order of each vertex's out-edges** match what `DoTrayAssignments` builds today. The last one matters: `ScheduleEventDag::GetTopologicalOrdering()` breaks ties inside a job by heap order, which follows push order, which follows out-edge order ([section 12.5](#bg-the-operations)).
11. Every event is in the DAG once. `AddEvent` refuses a pointer that is already present, so a solver must never record `AddEvent` for an event of the input DAG.

Invariant 4 in a picture (illustrative; real graphs and paths depend on the layout):

![Garage setup](figures/03_garage_xy.svg)

**Top-down garage setup.** AGV-1 faces +x and carries tray T1 toward the goal. Trays T2 and T3 sit on the route, so two prerequisite tray moves (T2 → S3, T3 → S4) must finish first; they are independent of each other. Coordinates are schematic, not a customer layout.

## Staged plan

A move-only refactor is risky because the helpers in [section 3](#pr-what-the-two-algorithms-touch) are shared with job planning. Moving them blindly either breaks those callers or recreates the coupling through a back-pointer to `Scheduler`.

| Stage                              | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Exit criterion                                                                                                                                             |
|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A — baseline                       | Pin the commit, build, run the 72 active tests; record output DAGs (`debug/printdags`) and `ScheduledJobDataMsg` lists for curated fixtures                                                                                                                                                                                                                                                                                                                                                         | Reproducible behaviour captured                                                                                                                            |
| B — dependency map                 | Confirm [Figure 1](#pr-fig-34_coupling_matrix) against the branch; decide where the five shared helpers live                                                                                                                                                                                                                                                                                                                                                                                        | Ownership design written down                                                                                                                              |
| B2 — names and boundary            | Add `core/vocabulary.hpp`, `core/types.hpp` and `ros/convert.*`; make the scheduler renames marked B2 in [section 7.4](#pr-renames-in-scheduler), one mechanical commit per group (members, `PlanContext`, `Expand<Type>Job`); switch `last_event_by_asset` and `scheduled_jobs` to `AssetId` and `ScheduledJob`; start the vocabulary check as a report                                                                                                                                            | All tests and DAG snapshots identical; response messages byte-identical on the baseline fixtures                                                           |
| C0 — stage folders                 | Create the stage folders of [section 8.2](#pr-source-tree) (`core/`, `task_planning/`, `motion_planning/`, `action_graph/`) with one CMake target each and the CI include check. Move the action-DAG helpers and `InsertVrcActionsIntoDag` into `action_graph/`, narrowing their argument from the context pointer to the event DAG, job list and initial state, passing the services explicitly and returning the per-job action indices (`ResponseFromTrajectories` writes them into the context) | Response messages byte-identical on the baseline fixtures; `scheduler_action_graph` links without `${PROJECT_NAME}`; first `test/action_graph/` tests pass |
| C1 — pure helpers in place         | Still inside `scheduler.cpp`: turn the heading helpers, `AssignTrayIdForEmptyMove` (→ `ChooseEmptyTray`), `ResolveBlockingTrays` and the inline main-loop blocks into free functions over `GarageServices` returning `stdx::Expected`; job planning calls them too. Merge the two emission blocks                                                                                                                                                                                                   | All tests and DAG snapshots identical; new unit tests for each pure function                                                                               |
| C2 — tray module                   | Fill `core/` and `task_planning/tray_assignment/` ([section 8.2](#pr-source-tree)) and add the files to the stage targets; move the pure functions; add `Solver`, `Input`, `Result`, `Pass`, `DefaultSolver`, `ApplyTrayAssignment`. Now that `GarageServices` exists, move `PlanMotions` into `motion_planning/` as a free function                                                                                                                                                                | A test that links only `scheduler_task_planning` constructs `DefaultSolver`; invariant 9 test passes                                                       |
| D — tray migration                 | `Plan` calls `Solve` + `ApplyTrayAssignment`; keep `DoTrayAssignments` temporarily for side-by-side comparison of the two DAGs                                                                                                                                                                                                                                                                                                                                                                      | All tests and DAG snapshots identical                                                                                                                      |
| E — tray cleanup                   | Delete `DoTrayAssignments` and the old members; port the 4 direct `DoTrayAssignments` tests and the `ResolveBlockingTrays` test to `test/task_planning/tray_assignment/`                                                                                                                                                                                                                                                                                                                            | No production call to the old methods                                                                                                                      |
| F — AGV module                     | `task_planning/agv_assignment/` with the same layout and `stdx` types; pure cost helpers; `SolveInPlace(input, events)` ([section 6.7](#pr-agv-assignment-same-layout-and-error-type-now-returned-result-later)); port the 9 direct tests                                                                                                                                                                                                                                                           | Same behaviour and coverage                                                                                                                                |
| G — benchmarks                     | ≥10 real-site scenarios per solver, timed in a pinned environment                                                                                                                                                                                                                                                                                                                                                                                                                                   | Results stored with metadata, no regressions                                                                                                               |
| H — final cleanup                  | Remove legacy code; remaining scheduler renames (`ValidateEvents`, `BuildPlanResponse`); vocabulary check fails the build; run full system and advanced suites. Optional, after the Definition of Done: move `Expand<Type>Job` into `task_planning/job_expansion/` and `ValidateEvents` into `task_planning/validation/` as free functions over `GarageServices`                                                                                                                                    | Definition of Done demonstrable                                                                                                                            |
| I — `planner_core` names           | The renames in [section 7.5](#pr-renames-in-planner-core), with deprecated aliases; update `scheduler` to the new names                                                                                                                                                                                                                                                                                                                                                                             | `planner_core`, `scheduler` and every package above `planner_core` build and pass their tests                                                              |
| J — first stage package (optional) | When `action_graph/` meets the promotion checklist of [section 6.5](#pr-recommendation-folders-now-packages-when-proven), move its three folders into a new `action_graph` package. `task_planning` follows only after G and H, together with a `scheduler_core` package                                                                                                                                                                                                                            | Same tests and parity fixtures pass; `scheduler` depends on the new package                                                                                |

**Ticket mapping:** check SW2-769's package structure against the current branch. SW2-484 is the natural first implementation ticket. B2, C0 and C1 are good first PRs inside it: both are mechanical, and the parity tests review them. SW2-487 can start as soon as baseline capture is deterministic. No AGV-specific child ticket is listed; stage F needs one.

## Decisions to resolve in review

Several choices in this proposal need the team's agreement before implementation, among them the solver input and output style, error reporting, the folder and package layout, the naming scope and base-schedule reservations. For each, the table gives the recommendation of this document and the evidence that would confirm or change it.

| Decision                        | Initial recommendation                                                                                                                                                                                                                                                                                                                                                                                     | Evidence needed                                                                                                                                                                                                                      |
|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Input/output style              | Tray: read-only `Input`, returned `stdx::Expected<Result>` (edit log) applied by `Scheduler` ([6.5](#pr-why-return-a-result-and-how-it-is-applied)). AGV: explicit `ScheduleEventDag&` for the first pass ([6.7](#pr-agv-assignment-same-layout-and-error-type-now-returned-result-later))                                                                                                                 | Confirmed in `planner_core`: `TrayMove` copy-constructible, `Apply` is `const`; replay order gives identical DAG snapshots                                                                                                           |
| Error reporting                 | `stdx::Expected<T>` / `stdx::Result` with `std::string` errors; `std::optional` only for internal “found nothing” searches ([6.4](#pr-errors-stdxexpected-instead-of-boolstringpair))                                                                                                                                                                                                                      | Tests that match error text; `std::to_string` vs a `std::formatter<GaragePoseMsg>`                                                                                                                                                   |
| Which functions stay members    | Only the solver's `Solve` and the private `Pass`; everything else becomes a pure free function over `GarageServices` ([6.3](#pr-before-and-after-the-tray-call-tree))                                                                                                                                                                                                                                      | Each pure function's unit test passes without a `Scheduler`                                                                                                                                                                          |
| Folder layout and names         | One folder per pipeline stage (`task_planning/` with `tray_assignment/`, `agv_assignment/`, `job_expansion/`, `validation/`; `motion_planning/`; `action_graph/`; shared `core/`) under `include/scheduler/`, `src/` and `test/`; one `CMakeLists.txt` with one library target per stage; private headers in `src/<stage>/`; namespaces to match (sections [6.1](#pr-stage-names), [8.2](#pr-source-tree)) | `volley_add_library` exports only `include/`; stage targets link without `${PROJECT_NAME}`; CI include check for the rest; whether `task_planning` clashes in people's minds with the `task_planner` package (else `event_planning`) |
| Stage folders or stage packages | Folders now, written so that each can become a package; promote `action_graph` first (stage J), `task_planning` after the benchmarks with a `scheduler_core` package, `motion_planning` never ([section 6](#pr-module-layout-folders-or-packages))                                                                                                                                                         | Owners for any new package; whether anything outside the scheduler needs a stage                                                                                                                                                     |
| Virtual interface vs templates  | Virtual `Solve`, owned by `Scheduler` through `std::unique_ptr`                                                                                                                                                                                                                                                                                                                                            | Existing code style, whether plugins must swap solvers at runtime                                                                                                                                                                    |
| Where interfaces live           | In the stage folders of `scheduler` now (`task_planning/<module>/solver.hpp`); in stage packages only when a stage meets the promotion checklist ([6.5](#pr-recommendation-folders-now-packages-when-proven))                                                                                                                                                                                              | `colcon graph`, `package.xml`, exported CMake targets; a second user of a stage                                                                                                                                                      |
| Where default solvers live      | Next to their interfaces, in the same stage folder; never in `planner_core`                                                                                                                                                                                                                                                                                                                                | Avoid new package-level dependency cycles (defaults need `motion_planner` and `cost_functions`)                                                                                                                                      |
| Benchmarks                      | Direct solver benchmark plus optional end-to-end `Plan` benchmark                                                                                                                                                                                                                                                                                                                                          | Fixtures, harness, timing environment                                                                                                                                                                                                |
| What "same result" means        | Same tray/AGV assignments, same edge set after `Reduce`, same final state and errors                                                                                                                                                                                                                                                                                                                       | Stable event identifiers. Tie-breaking: identical `AddEvent`/`AddDependency` sequences give identical orders; otherwise compare orders per job index                                                                                 |
| Naming scope                    | Rename in `scheduler` and `planner_core` only; translate `common_ros` names in `core/vocabulary.hpp`; replace messages used for internal bookkeeping with internal types at the edge ([section 7](#pr-naming-and-the-ros-boundary))                                                                                                                                                                        | The naming catalogue's ([section 15](#nm-proposed-future-work-naming)) names accepted for these rows; the list of packages above `planner_core`                                                                                      |
| Shared folder and namespace     | `core/` and `volley::scheduler_core`, not `common` ([8.2](#pr-source-tree))                                                                                                                                                                                                                                                                                                                                | A build with the new namespace and today's `common::EnumInteger` calls                                                                                                                                                               |
| `planner_core` changes          | None for parity; renames in stage I, after parity ([7.5](#pr-renames-in-planner-core)). Later candidates: `[[nodiscard]]` on `AddDependency` (or an error for missing endpoints), a virtual `Clone()` on `ScheduleEvent`, `shared_ptr<const ScheduleEvent>` accessors for read-only users                                                                                                                  | Agreement from the `planner_core` owners; every other planner package depends on it                                                                                                                                                  |
| Base-schedule reservations      | Keep the whole-plan reservation for parity, but build it in `ReserveBaseScheduleAssets` and keep the record, so job failures say "reserved by the running schedule" instead of "disabled". Time-bounded reservations (a busy AGV becomes free when its last base action ends) are a later behaviour change ([section 14.6](#pr-base-schedule-reservation))                                                 | How often pending jobs fail or wait because of a busy asset in recorded requests; Dispatch's rules for joining a new schedule onto the running one; whether VRC commands in the base schedule should reserve their VRC               |

## Risks that must not be silently "fixed"

These are behaviours a reviewer may want to change. Changing them during extraction breaks parity.

1.  `GetAgvOccupiedDuration` always returns `Duration::zero()` (`// TODO(isabel) implement!`). The matching costs depend on that.
2.  `Reduce()` runs inside `DoAgvAssignments` *and* again in `Plan`. The `TODO` above the second call says planning may fail without it; nobody has confirmed why.
3.  `DoTrayAssignments` postpones DAG reduction until after AGV assignment (“Reduce here breaks the AgvAssignments for some reason”); moving it earlier is high risk. A likely reason, from the code of `Reduce()`: AGV assignment has code that looks only at **direct** edges. `PropagateEventCostToChildren` passes a matched tray move's cost to its direct children only, and only tray moves propagate; if `Reduce()` replaces a direct edge “tray move A → tray move C” with the path “A → bay transition → C”, C never sees A's cost and the matching changes. `AddDepsAfterAmiga` also inspects only direct in- and out-edges (and already runs after the reduction at the end of `DoAgvAssignments`). Treat this as a hypothesis to test, not a fix.
4.  `TrayMove::Apply` treats blank fields specially (`planner_core/src/schedule_events.cpp`): no tray id → no-op; no destination → the tray and its payload are **removed** from the state; a tray already on the destination is moved to `{node_id: 0, heading: 0}`. Later jobs' `working_state` depends on this; a solver that replays half-specified moves must reproduce it exactly.
5.  `ScheduleEventDag` uses pointer identity and Boost `vecS` vertex indices. Removing a vertex shifts every later index down by one (the comment in `RemoveVertexHelper` says so), and CHUGG maps motions back to events by vertex index, so never remove from `ctx->events` and never cache vertex descriptors across `Remove`.
6.  `AddDependency` never checks for cycles and returns `false` silently when an endpoint is missing; `WouldCreateCycle` returns `false` ("safe") in the same case. A refactor that reorders `AddEvent` and `AddDependency` calls can drop edges without any error.
7.  Test names such as `576_eccles_half` and `1355_fulton` suggest real sites, but `tiny_lot` and `triple_pick_lot` are synthetic. Record which layouts are real before counting them toward the 10-scenario goal; the Simulation tab lists the likely place of each layout ([section 1.1](#sm-where-the-layouts-are)).
8.  SW2-905 (insert fails when an AGV collides with the chosen parking node) is in the parent ticket; that does not mean the refactor causes it.
9.  In fallback 1 (“advance the root tray”), the path recorded for the advance move is `std::vector<GaragePoseMsg>{gg_.GetVertexFromPose(tray_opt->pose).value(), advance_move->GetDest().value()}` (`:2842`–`:2844`). Its first element is a graph *vertex* converted to a `GaragePoseMsg`, and `tray_opt` was already refreshed to the post-advance pose. The `freeing_moves` edges built from that path may therefore be wrong. Reproduce it with a test before touching it; when `TryAdvanceRoot` returns a `PlannedTrayMove`, keep the same path until then.

## Next actions

The first steps establish a baseline before any code moves: a recorded test run in the ROS container, a check that the branch matches the snapshot this document describes, and a map of where the affected symbols are used.

1.  In the ROS container, build and run `colcon test --packages-select planner_core scheduler scheduler_advanced_tests`, then `colcon test-result --verbose` to capture the baseline.
2.  Confirm the branch matches this snapshot; keep edits in small reviewable commits.
3.  Map symbol use from the repository root: `rg -n 'ResolveBlockingTrays|DoTrayAssignments|DoAgvAssignments|first_tray_event|BottleneckAssignment'`. Compare with [Figure 1](#pr-fig-34_coupling_matrix), and rebuild [Figure 1](#pr-fig-34_coupling_matrix) (`python3 scripts/diagrams/build.py 34`) after replacing `sources/repomix-scheduler.xml` with a newer snapshot.

## Evaluating the event-graph strategy

The refactor keeps the scheduler's strategy: build an event DAG, then plan motions for it, then turn the motions into an action DAG. This section steps back and asks whether that strategy fits the problem. It covers what the problem actually is, what the event DAG represents, where it helps and where it costs, and which other formulations from the literature could take its place or improve it. It is an analysis to inform future tickets, not part of this ticket's scope.

### The problem the scheduler solves

Stated without reference to the code, one `Plan()` call solves this:

> Given the garage now (where every AGV, tray and car is, and the state of every bay, VECS and VRC), the work already running, and a list of jobs, each a desired outcome such as “this car is handed over in some bay” or “this tray is parked”, choose the physical actions that achieve as many jobs as possible, decide which machine does each one, and order them so that the fleet can execute them without collision, whatever the actual speeds turn out to be. Do it within about a second, again and again as jobs arrive.

A job is a **goal condition**, not a sequence of moves. A retrieve does not say “move T21 out of B21, then move T17 in”; it says “the car is in a bay that is processing a retrieve”. Everything between the condition and the moves is the planner's choice. The domain shapes that choice through the following requirements:

| Requirement                                | In this garage                                                                                                                             | Consequence for any formulation                                                                                                                         |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| Goals are conditions with open choices     | Which bay, which empty tray, which parking spot, which AGV, which charger are all free; only the outcome is fixed                          | Task allocation and goal selection are part of the problem, not inputs to it                                                                            |
| Dense storage with passive obstacles       | Trays (with or without cars) stand on parking nodes and block each other; reaching one may require moving others                           | A rearrangement problem: blockers create extra tasks, and the set of tasks depends on routes (puzzle-based storage, navigation among movable obstacles) |
| Carry by lifting                           | An AGV drives under a tray, lifts it, carries it and lowers it; with the lift down it can pass under trays whose legs allow                | Agents change footprint and capability during a plan; pickup and delivery are separate goals of one agent                                               |
| Large agents, headings, motion types       | Footprints overlap several nodes; heading matters; locomote, strafe and rotate have different durations; rotation only on some nodes       | Conflicts are footprint overlaps (large-agent MAPF), states are poses, not vertices; time is continuous                                                 |
| Stateful non-AGV resources                 | Bays switch modes and process cars, VECS charge, VRCs carry AGVs between floors; a bay's overdrive plate blocks traffic in some states     | Resources with state machines and durations, some of them unbounded (a patron's insert), and some that change the map                                   |
| Hard precedence from the domain            | A bay must be in retrieve mode before a tray enters; the car must be in the bay before the hand-over; a tray cannot enter an occupied node | Some orderings are real constraints and must be kept in every plan                                                                                      |
| Execution is uncertain                     | Speeds, acceleration, patron behaviour and reports vary; actions are released by Dispatch when their parents finish                        | The output must be an *order* that is safe at any speed (an ADG), not a timetable                                                                       |
| Online and persistent                      | Jobs arrive continuously; Dispatch plans every 850 ms when allowed; the fleet keeps moving                                                 | Lifelong planning: new plans must fit around running ones, and planning time is bounded                                                                 |
| Objectives are about people and throughput | A patron waits for a retrieve; bays must be ready for inserts; trays and AGVs must be balanced and charged                                 | The main cost is retrieve waiting time and bay readiness, not makespan or sum of costs alone                                                            |
| Safety, determinism, explainability        | No collision is acceptable; failures must be reported per job; operators and engineers must understand why a plan looks the way it does    | Sound (never unsafe) beats optimal; deterministic, inspectable intermediate results are valuable                                                        |

### What the event DAG is

Seen from the motion planner, the event DAG is a set of goal sequences with ordering constraints between them. In the literature that input defines a *problem*, multi-agent path finding with precedence constraints (MAPF-PC; Zhang et al., AAMAS 2022): each agent has a sequence of goals, and some goals must be reached before goals of other agents. MAPF-PC is a problem statement, not an algorithm. The same paper gives two algorithms for it, CBS-PC (conflict-based search with precedence constraints) and PBS-PC (priority-based search with precedence constraints).

CHUGG takes a MAPF-PC instance as its input, extended with large footprints, continuous time and non-AGV events, but it implements neither of those algorithms. Its algorithm is **prioritized planning**: it fixes one topological order of the events and plans them one at a time, each against everything already planned. The single-agent search inside each step is SIPP (safe interval path planning), which finds the fastest collision-free route for one AGV through the time windows the earlier plans leave free. So: MAPF-PC is the input, prioritized planning is the multi-agent strategy, and SIPP is the single-agent search inside it (Motion planning tab, [section 7.3](#mp-chuggs-problem-in-symbols)). Each AGV gets a sequence of goals (poses to reach, lifts to perform), and the edges become precedence constraints between goals of different agents:

\text{MAPF-PC: } \big(G,\\ \\s_i\\,\\ \\(g_i^1, \dots, g_i^{m_i})\\,\\ \mathcal{P}\big), \qquad (g_i^a, g_j^b) \in \mathcal{P} \\\Rightarrow\\ t(g_i^a) \le t(g_j^b).

But the goal sequences and the precedence set are the *end* of the task-planning layer, not its purpose. Before anything reaches CHUGG, the event DAG has already been used to make every discrete decision of the problem: which bay, which tray, which parking spot, which blockers to move, which AGV. A more complete description is:

- **It is a partial-order plan.** Each event is an action with a precondition and an effect on the discrete garage state (checked by `OnEvent`), and the edges are a partial order \prec on the events. The intended invariant is that every linear extension of \prec replays without a failed precondition and ends in a state where every planned job's goal condition holds. This is the classical partial-order causal-link (POCL) plan of AI planning (Ghallab, Nau and Traverso, *Automated Planning*, 2004), built by hand-written rules instead of a generic planner.
- **It is the common workspace of three decision stages.** Job expansion writes intent with open slots (HTN-style methods: each job method is a recipe that decomposes a goal into events). Tray assignment fills the slots and adds blocker moves (a rearrangement subproblem). AGV assignment binds events to agents and adds approach, lift and lower events (a task-allocation subproblem). The DAG is how these stages talk to each other.
- **It is the interface to the motion planner.** Only at the end is it read as goal sequences plus precedence.

So the high-level goal of the strategy is: **decide what must happen and who does it, and fix enough ordering that the discrete plan is causally valid, before any timing or geometry is planned**. The weak point is the last clause. The DAG's edges do not only record the orders the problem requires.

### Four kinds of edge

Every edge of the event DAG becomes a hard precedence constraint in CHUGG, but the edges exist for different reasons. Classifying them by reason shows what the current strategy gives away:

![Four kinds of edge in the event DAG](figures/125_event_dag_edge_kinds.svg)

**Four kinds of edge in the event DAG.** Step through one small example. Causal edges are needed in every valid plan. A path-dependent edge exists only because a route was chosen before motion planning. A resource-order edge needs some order, but its direction is free. A conservative edge is not needed at all. Today all four reach CHUGG as hard precedence.

| Kind           | Meaning                                                                                                                  | Created by (today)                                                                                                             | Where it belongs                                                                                                                                        |
|----------------|--------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| Causal         | An effect of one event is a precondition of the other (POCL causal link)                                                 | Job recipes (bay mode before a tray enters: rule C; car in bay before the hand-over); destination occupancy in tray assignment | Hard precedence in every formulation                                                                                                                    |
| Path-dependent | Needed only for the route fixed during task planning (a tray must leave a node the chosen route crosses)                 | `freeing_moves` occupancy edges, blocking-path edges in AGV assignment, path repairs                                           | Space-time conflicts for the path planner, or soft hints                                                                                                |
| Resource order | Two events need the same AGV, tray, bay or VECS, so one goes first; either direction is valid (a disjunctive constraint) | Rule A (same entity, in request order), AGV chains from assignment                                                             | A choice for the solver: \mathrm{end}(\varepsilon) \le \mathrm{start}(\varepsilon') \\\vee\\ \mathrm{end}(\varepsilon') \le \mathrm{start}(\varepsilon) |
| Conservative   | Not required by the domain                                                                                               | Rule B (a new event waits for all current leaves of its job)                                                                   | Dropped, or kept only as a tie-break                                                                                                                    |

Because ordering is fixed before timing and geometry exist, the motion planner cannot recover parallelism that the task layer gave away, and a bad order cannot be undone: CHUGG either finds a plan in that order or fails. In POCL terms, the current code resolves every *threat* (two actions that could interfere) by committing to one order immediately, using request order and greedy assignment, instead of leaving the choice open.

### Strengths and costs of the current strategy

With the problem and the kinds of edge defined, the current strategy can be weighed. The table lists what the event-DAG strategy does well and what it costs; most of the costs follow from the early commitment described in the previous subsection, where order is fixed before timing and geometry are known.

| Strengths                                                                                                                                                         | Costs                                                                                                                                                                                               |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Standard layering.** Task planning, path planning and execution are separated the way most warehouse systems separate them; each layer can be tested alone      | **Early commitment.** Orders, routes and assignments are fixed before their cost is known; later stages can only fail, not revise (greedy, no backtracking across stages)                           |
| **The right interfaces.** Goal sequences plus precedence (MAPF-PC) and an action DAG (ADG) are well-studied representations with solvers and execution guarantees | **Over-constraint.** Path-dependent, resource-order and conservative edges all become hard constraints, which serialises work and lengthens retrieve times                                          |
| **Cheap validation.** Discrete replay through `OnEvent` catches most inconsistencies in microseconds and with readable messages                                   | **Geometry is approximated twice.** Task planning uses static filters and discrete teleports; real conflicts appear only in CHUGG, which can throw                                                  |
| **Explainable.** Every event and edge can be printed and traced to a rule; per-job failures are natural                                                           | **No objective.** Only AGV matching minimises something (the bottleneck cost); nothing optimises retrieve waiting time, and CHUGG returns its first plan                                            |
| **Fast enough** for the 850 ms planning cadence on the garages it runs on                                                                                         | **Not lifelong yet.** Each call plans from scratch; the base-schedule path is a coarse reservation, and Dispatch plans only when the fleet is idle (Dispatch tab, [section 6](#ds-interface-notes)) |

### Related formulations

Each part of the problem has a well-studied formulation. None covers all of it, which is why real systems combine several:

| Formulation                                                                                                                                                        | What it models                                                                                          | Fit to this garage                                                                                                                 | What it leaves out                                                                       |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| **MAPF-PC** (Zhang et al., AAMAS 2022), solved by CBS-PC and PBS-PC (conflict-based and priority-based search with precedence constraints)                         | Goal sequences per agent and precedence between goals of different agents                               | Exactly CHUGG's input; PBS-PC searches over the priority order that CHUGG fixes once                                               | Assignment, goal selection, blockers, non-AGV resources: all decided before              |
| **Large-agent and continuous-time MAPF** (Li et al., AAAI 2019; CCBS, Andreychuk et al., AIJ 2022)                                                                 | Footprints that cover several places; real durations                                                    | Matches the collision table and the cost model                                                                                     | Task layer                                                                               |
| **TAPF and CBS-TA**: target assignment and path finding; conflict-based search with task assignment (Ma and Koenig, AAMAS 2016; Hönig et al., AAMAS 2018)          | Assignment of goals to agents inside the path search                                                    | Replaces greedy AGV matching with assignment that sees conflicts                                                                   | Precedence, multi-goal sequences, rearrangement (extensions exist but are research code) |
| **MAPD and lifelong MAPF**: multi-agent pickup and delivery (Ma et al., AAMAS 2017: token passing; Li et al., AAAI 2021: rolling-horizon collision resolution)     | A stream of pickup-and-delivery tasks, planned continuously over a window                               | Matches Dispatch's online loop and the base-schedule problem; windowed planning bounds time                                        | Precedence between tasks, stateful resources, blockers                                   |
| **Puzzle-based storage and NAMO** (navigation among movable obstacles) (Gue and Kim, Naval Research Logistics 2007; Stilman and Kuffner, 2005)                     | Retrieving items from dense grids by moving the items in the way                                        | Automated parking garages are a textbook case of puzzle-based storage; this is the blocking-tray problem                           | Multi-agent timing; usually one retrieval at a time                                      |
| **POCL and temporal planning**: partial-order causal-link planning (PDDL 2.1 durative actions; simple temporal networks, STNs, Dechter, Meiri and Pearl, AIJ 1991) | Actions with preconditions and effects; minimal causal ordering; flexible timing                        | Events already have preconditions and effects; a POCL view yields only the causal edges and keeps threats open                     | Geometry and paths; general planners are slow at this scale                              |
| **HTN planning** (hierarchical task networks)                                                                                                                      | Goals decomposed by methods into subtasks                                                               | Job methods are HTN methods written in C++                                                                                         | Search over method choices (the code takes the first that applies)                       |
| **Scheduling: RCPSP (resource-constrained project scheduling), flexible job shop with transport robots** (constraint programming, CP, for example OR-Tools CP-SAT) | Tasks with durations, precedence, disjunctive resources and objectives such as weighted completion time | Natural for bays, VECS, VRCs, AGV sequencing and patron waiting time; disjunctive constraints are exactly the resource-order edges | Collision-free paths (needs travel-time estimates and a MAPF stage after it)             |

### Alternative architectures

The alternatives differ mainly in **which layer owns which decision**. Today every decision except paths and times is owned by task planning:

| Approach                                                                            | Goals and blockers                                   | Assignment                          | Order                                                                        | Paths and times                                 | Main trade-off                                                                                                                       |
|-------------------------------------------------------------------------------------|------------------------------------------------------|-------------------------------------|------------------------------------------------------------------------------|-------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **Today**: event DAG, then prioritized MAPF-PC                                      | task planning (greedy)                               | task planning (bottleneck matching) | task planning (all edges hard)                                               | CHUGG (fixed priority)                          | Fast and explainable; over-constrained, no recovery from early choices                                                               |
| **A. Typed event DAG + PBS-PC** (priority-based search with precedence constraints) | task planning                                        | task planning                       | causal edges in task planning; resource and path orders chosen by the solver | priority-based search over the remaining orders | Smallest change; keeps the IR and the refactor's interfaces; recovers parallelism and fixes bad priorities; still greedy above       |
| **B. Assignment inside the search** (CBS-TA style)                                  | task planning                                        | MAPF solver                         | solver                                                                       | solver                                          | Better AGV choices; search cost grows with candidates; research-grade with precedence                                                |
| **C. Schedule first** (CP model of jobs, bays, VECS, AGVs; then MAPF)               | task planning or CP                                  | CP                                  | CP, with an explicit objective (retrieve waiting time)                       | MAPF-PC on the chosen order                     | Optimises what matters to patrons; needs travel-time estimates, and a path stage that can still fail                                 |
| **D. Lifelong rolling horizon** (MAPD / windowed planning)                          | per task as it arrives                               | online (token passing or matching)  | within a window                                                              | windowed MAPF, replanned continuously           | Natural fit for Dispatch and the running schedule; plans only a short horizon, so long rearrangements need care                      |
| **E. Integrated search over discrete states**                                       | search over `DiscreteGarageState` (already hashable) | search                              | search                                                                       | MAPF-PC afterwards                              | Finds blocker sequences greedy rules miss; only tractable for small subproblems (the blocking-tray search already does this locally) |

The approaches combine. A realistic end state is A plus D, with C for the bay and charging decisions that matter most to patrons.

### Recommendation

The event DAG is a sound intermediate representation for this domain and should stay; the problem is how much is decided before it reaches the solver. In order of cost:

1.  **Make the representation explicit** (fits the refactor's solver interfaces). Store each edge with its kind (causal, path, resource, conservative) and the rule that created it. Nothing else changes; parity tests stay valid, and the motion-solver interface ([section 15](#pr-swappable-motion-planners)) can carry the kinds to any solver.
2.  **Measure the cost of over-constraint.** On the benchmark set (Verification tab), compare CHUGG's makespan and retrieve arrival times with all edges against causal edges only plus a conflict check. If the gap is small, stop here.
3.  **Let the solver choose the free orders** (approach A). Pass resource-order edges as disjunctions and path-dependent edges as hints to a priority-based search (PBS-PC) that keeps the causal edges hard. CHUGG's sequential planner is already PBS's inner step.
4.  **Make planning lifelong** (approach D, with Dispatch). Seed the motion planner with the running schedule as fixed motions and return edges from it into the new plan, so overlapping planning can be turned on (Background, [section 11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)).
5.  **Give the planner an objective** (approach C for the decisions that matter). Start with bay choice and job ordering, scored by predicted retrieve waiting time, behind the tray and AGV solver interfaces of this refactor.

Questions to settle before step 3: what the primary objective is (retrieve waiting time, throughput, or a weighted mix); how long a planning call may take; whether durations of bay and patron actions can be bounded; and how far ahead Dispatch should plan once overlapping planning is on.

## Future work: swappable motion planners

The tray and AGV solvers of this ticket put task planning behind interfaces. Motion planning is the natural next step: keep CHUGG, but make it one implementation of a common interface, so that other solvers (CBS, priority-based search, newer large-scale MAPF solvers, a learned planner) can be tried, benchmarked and swapped without touching the scheduler. This section is future work beyond SW2-484. It builds on the comparison of CHUGG's inputs with the standard MAPF problem in the Motion planning tab ([section 5](#mp-solver-inputs-and-outputs)).

![Swappable motion planners](figures/99_motion_solver_interface.svg)

**Swappable motion planners.** The scheduler's `motion_planning/` folder builds a solver-neutral `MotionProblem` from the event DAG, selects a solver, and validates the returned `MotionPlan` before the action graph is built. The problem types and the interface live in `motion_planner`, next to the solvers that implement them. This is a proposal, not existing code.

### Why this is harder than the task-planning interfaces

Putting CHUGG behind an interface is not a repeat of the tray and AGV work: the motion planner's input, part of its problem definition and its output are all tied to the scheduler's event classes or to decisions made inside CHUGG. The four points below describe each obstacle; the interface in the next subsection is designed around them.

- **The input is the scheduler's task vocabulary.** CHUGG takes the `ScheduleEventDag` and has one planning routine per event class, so a second solver would have to understand `planner_core` events, or the events have to be translated into something neutral first.
- **Part of the problem is hidden inside CHUGG.** The start-state replay, the static obstacles, the footprint changes when an AGV lifts a tray, the “an arrival counts only if the AGV can stay there” rule and the bay-door wait are decisions made inside CHUGG and `SippAgv`. A new solver must make the same decisions, or the problem description must state them.
- **The output feeds the action graph.** The action DAG maps every motion back to its event (today through the event's vertex index in `Motion`), so any solver must tag its motions with the goal they serve.
- **The scheduler steers CHUGG through the DAG.** Node-arrival edges, path repair and `Reduce()` exist partly to make prioritized planning succeed. A solver that searches over orders (CBS) may not need them, and may do worse with them, so the problem should separate real precedence from edges added only to guide CHUGG.

### The interface

The four parts of the problem description (world, start, tasks, settings) become one value type, and the solver contract mirrors the tray solver's: a `const` function from a read-only problem to an `stdx::Expected` result.

``` cpp
// PROPOSED — motion_planner/include/motion_planner/motion_problem.hpp
namespace volley::motion {

using GoalId = std::size_t;

struct Capabilities {                          // what a solver can be given, or what a problem uses
  bool goal_sequences, precedence, load_dependent_footprints, device_actions, continuous_time;
};

struct Goal {                                  // one thing one entity must achieve
  GoalId id;
  GarageEntityIdMsg entity;                    // which AGV, bay or VECS
  std::variant<DriveTo, PickUp, PutDown, DeviceChange> what;  // pose, tray, or a timed state change
};

struct MotionProblem {
  // world: fixed per site
  const MotionGraph& graph;                    // poses and transitions (GarageGraph today)
  const CollisionTable& conflicts;             // which footprint at which vertex or edge overlaps which other
  const cost::MotionCostModel& timing;         // edge, turn, lift and device durations
  // start: per plan call
  Interval::Timepoint start_time;
  std::vector<AgentStart> agents;              // pose, footprint, carried tray, available or not
  StaticObstacles blocked;                     // parked trays, disabled nodes and entities
  // tasks: per plan call
  std::vector<Goal> goals;                     // per entity, in the order that entity must do them
  std::vector<std::pair<GoalId, GoalId>> precedence;  // a must finish before b starts (across entities)
  // settings
  Objective objective = Objective::kFirstFeasible;     // or sum of costs, makespan
  std::optional<std::chrono::milliseconds> time_budget;

  [[nodiscard]] Capabilities Needs() const;    // which features this problem uses (precedence, devices, ...)
};

struct MotionPlan {
  ContinuousState timeline;                    // timed motions per entity
  std::unordered_map<GoalId, std::vector<MotionRef>> motions_by_goal;  // which motions serve which goal
};

class Solver {
public:
  virtual ~Solver() = default;
  [[nodiscard]] virtual Capabilities GetCapabilities() const = 0;
  [[nodiscard]] virtual stdx::Expected<MotionPlan> Solve(const MotionProblem& problem) const = 0;
};

// one validator for every solver: goals reached, precedence respected, no conflicts
[[nodiscard]] stdx::Result Validate(const MotionProblem& problem, const MotionPlan& plan);

}  // namespace volley::motion
```

A classic MAPF instance is the case with one `DriveTo` goal per agent, no precedence, and footprints that conflict only on the same vertex or edge. That makes the standard MAPF benchmarks (Stern et al. 2019) usable as tests for every solver, alongside the site scenarios of SW2-487.

### Where the pieces live

The interface divides the code between two packages: the problem types and the solvers belong in `motion_planner`, and the translation from events to goals belongs in the scheduler. The table names the package for each piece and the reason, which follows the dependency direction of [section 6](#pr-module-layout-folders-or-packages): solvers must implement the interface without depending on `scheduler`.

| Piece                                                          | Package and folder                          | Why there                                                                                                                                                                                                                                                                                                  |
|----------------------------------------------------------------|---------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `MotionProblem`, `MotionPlan`, `Solver`, `Validate`            | `motion_planner`                            | Solvers live there and must implement the interface without depending on `scheduler`. The types use only `common_ros`, `cost_functions`, `interfaces` and `motion_planner`'s own timeline types, so `motion_planner` stops needing `planner_core`'s event classes once CHUGG reads goals instead of events |
| `ChuggSolver`                                                  | `motion_planner`                            | Wraps today's `Chugg`; first by rebuilding a `ScheduleEventDag` from the goals, later by planning goals directly                                                                                                                                                                                           |
| New solvers (`CbsSolver`, ...)                                 | `motion_planner`, or a package of their own | A solver with heavy dependencies (a MILP solver, a learned model) can live in its own package that depends on `motion_planner`                                                                                                                                                                             |
| `BuildMotionProblem`, solver selection, the call to `Validate` | `scheduler`, `motion_planning/`             | Only the scheduler knows the event classes; this is the adapter of [section 6](#pr-module-layout-folders-or-packages), which grows from 60 lines to the translation between the two vocabularies                                                                                                           |

The adapter maps each event class to goals: an `AgvMove` to one `DriveTo`; a `TrayMove` to `DriveTo` (under the tray), `PickUp`, `DriveTo` (destination) and `PutDown` for its AGV; a `BayTransition` or `VecsTransition` to one `DeviceChange` with its duration from the cost model. Event edges become precedence between the last goal of one event and the first goal of the next, exactly as they become action-DAG edges today.

### Solvers that support less than the full problem

`MotionProblem::Needs()` (what this problem uses) is compared with the solver's `GetCapabilities()` before calling it. When a solver lacks something, there are three options, in order of preference:

1.  **Refuse and fall back.** Return an error naming the missing capability; the scheduler falls back to CHUGG. Always safe.
2.  **Decompose.** Split the goals into waves: a wave holds the goals whose predecessors are all in earlier waves, at most one goal per agent. Each wave is a classic MAPF instance that starts where the previous one ended. This handles precedence and goal sequences with a solver that knows neither, at the cost of optimality across waves.
3.  **Extend the solver.** Add the capability (CBS with precedence constraints, multi-goal CBS, a `CollisionTable`-based conflict test, continuous-time CBS). The literature has a version of each.

### A staged plan for motion planning

Like the main refactor ([section 11](#pr-staged-plan)), the motion-planning work proceeds in small stages, each with an exit criterion checked against recorded baseline plans. The first stages wrap CHUGG without changing its results; a second solver and solver selection follow only once a solver-neutral problem exists.

| Stage                | Change                                                                                                                                                                                                                 | Exit criterion                                                                                    |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| M0 — capture         | Record CHUGG's `ContinuousState` and the action DAG for the stage A baseline fixtures; add the solver-independent `Validate` and run it on every recorded plan                                                         | Every baseline plan validates                                                                     |
| M1 — wrap            | `motion_planning::PlanMotions` (stage C2) calls CHUGG through a `Solver` interface whose input is still today's (event DAG, start state, services): `ChuggSolver`                                                      | Byte-identical `ContinuousState` on the fixtures; exceptions from CHUGG become `stdx` errors      |
| M2 — neutral problem | Add `MotionProblem` and `BuildMotionProblem`; `ChuggSolver` rebuilds the event DAG from the goals internally; separate real precedence from guide-only edges (mark the edges `AddNodeArrivalDeps` and path repair add) | Same `ContinuousState` as M1; a round-trip test event DAG → problem → event DAG                   |
| M3 — second solver   | A `CbsSolver` on `SippAgv` (its landmark and avoid constraints already exist), first for problems without precedence, with wave decomposition for the rest                                                             | Passes `Validate` on the MAPF benchmarks and the site scenarios; results recorded next to CHUGG's |
| M4 — selection       | A ROS parameter chooses the solver; capability check and fallback to CHUGG; per-solver metrics in the benchmark CSV ([section 5](#vr-benchmark-method) of the Verification tab)                                        | Switching solvers is a configuration change                                                       |
| M5 — CHUGG on goals  | CHUGG reads goals instead of events; `motion_planner` drops its dependency on `planner_core`'s event classes                                                                                                           | Same results as M1; dependency removed from `package.xml`                                         |

M0 and M1 fit naturally into this ticket's stage C2, when `PlanMotions` moves into `motion_planning/`. The rest is separate work and does not block the Definition of Done.

### Decisions for the motion-planning work

Comparing or replacing solvers raises questions that a single solver never had to answer, because CHUGG has no objective beyond feasibility in priority order. The points below list those questions and the considerations that bear on each.

- **Objective.** CHUGG has none beyond feasibility in priority order. Comparing solvers needs one: sum of arrival times, makespan, or the action DAG's critical path ([section 4.4](#ad-timing-critical-path-and-slack) of the Action graph tab), which is what execution actually waits for.
- **Determinism.** Parity tests and replays need the same plan for the same input. Randomized or time-budgeted solvers need a seed and a deterministic fallback.
- **Time budget.** CHUGG has no time limit beyond the 5,000,000-expansion cap per search. An anytime solver needs a budget per `Plan()` call, and the scheduler needs to know what to do when it runs out.
- **Guide edges.** Whether edges added only to make prioritized planning succeed should be passed to other solvers at all; leaving them out may let a solver find better plans, at the risk of different behaviour.
- **Timeline storage.** `MotionPlan` reuses `ContinuousState`, so every solver will fill `Trajectory` objects. Settle their storage and rules first: a sorted `std::vector` instead of `std::set`, an explicit rule for motions that start at the same time, and an `AddMotion` whose refusal cannot be ignored ([section 4.1](#mp-why-trajectory-is-a-set)).

## Future work: performance instrumentation and evaluation

Improving the planners requires knowing how long each stage takes, how that time grows with the size of the garage and the request, and which inputs make it grow sharply. Nothing in the package measures this today beyond the optional cost audit and the DAG dumps. The proposal below is an initial outline, to be refined when the work is scheduled.

### Instrumentation in layers

Each layer answers a different question, and the first is enough to start:

1.  **Stage timers and work counters, always on.** A scoped timer around each stage of `Plan()` fills a small per-call record: the duration of each stage, and counts that explain the time (jobs, events, edges, searches run, nodes expanded, blocking trays resolved, CHUGG events). The search engine already counts its expansions (`SearchMetaData`). The record is logged or published with the scheduler's report, so every simulation recording carries it.
2.  **Call-level detail, on demand.** A sampling profiler (`perf` with flame graphs, or Hotspot) on the replay tests needs no code changes. An instrumenting profiler such as Tracy shows nested scopes on a timeline when finer detail is needed.
3.  **Fleet monitoring, later.** OpenTelemetry traces and metrics with a Grafana dashboard become useful once planning time must be followed across sites and over weeks. They add a dependency and infrastructure, so they are not the starting point.

All layers can share one scope macro in the code, for example `SCHED_SCOPE("tray_assignment")`, whose backend is chosen at build time; call sites then do not change when a layer is added.

### A structured evaluation

- **A time budget.** Dispatch may call the planner every 850 ms; the budget for the median, the 95th percentile and the worst case is agreed first, and every measurement is judged against it.
- **Size parameters.** Jobs per call, events and edges, trays and occupancy, AGVs, graph size (poses, not nodes), blocking trays per move, and the length of the running schedule. Each is varied alone, and time is plotted against it on log-log axes to read the growth rate.
- **Known suspects.** The tray-search step checks every tray in the garage; the blocking-tray loop searches again per blocker; every job method replays the event DAG; filters are rebuilt per working state; `HideAgvs` backtracks; CHUGG's heuristic table is cubic in the number of poses.
- **Blow-up cases.** Constructed stress cases (a full garage, every route blocked, few hiding trays), generated states with a time limit, and slow plans captured in the field: a plan call over the threshold saves its `PlanRequest`, which becomes a replayable fixture.
- **Gates.** The runtime ratio of the benchmark method (Verification tab) and a threshold on work counters, which are stable across machines, run in CI. Plan quality is measured separately, so that a faster planner producing worse plans is not mistaken for an improvement.

## Proposed future work: the naming catalogue and small struct refactors

This section is future work beyond this ticket: a catalogue of names to keep open while refactoring. It covers the whole stack the scheduler touches: the ROS messages in `interfaces`, the garage model in `common_ros`, the events and DAG in `planner_core`, and the `scheduler` package itself. Each row gives the current name, the proposed one, where it lives, how expensive the change is, and why. The rules in [section 2](#nm-naming-rules) produce the proposals, so a name not listed here can be decided the same way.

> **Scope.** This refactor adopts only the rows for `scheduler` and `planner_core` ([section 9](#pr-naming-and-the-ros-boundary)). Rows for `common_ros` and the ROS interfaces wait: the scheduler reaches them through one translation header and its own internal types, so its code can use the good names now and drop the translation when `common_ros` catches up.

These are recommendations, not decisions. The few that need a team decision are collected in [section 9](#nm-decisions-for-review). Everything is taken from the six source snapshots (`sources/repomix-*.xml`: `scheduler`, `planner_core`, `common_ros`, `interfaces`, `motion_planner`, `cost_functions`); where the snapshots do not show something, the row says so.

### How to read the catalogue

Every recommendation carries a **tier**: how far the change reaches, and so how much it costs.

| Tier | Scope                                                           | Cost of the rename                                                                                                                                                                                                                                                                                                                                                                 | When to do it                                                                                       |
|------|-----------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| A    | Private members, locals, and types used only inside `scheduler` | One package, one pull request, no other team affected                                                                                                                                                                                                                                                                                                                              | In the same change that moves or rewrites the code (the staged plan, [section 11](#pr-staged-plan)) |
| B    | Public C++ API in `common_ros` and `planner_core`               | Every package that includes the header. Keep the old name as a deprecated alias for one release                                                                                                                                                                                                                                                                                    | Batch per header, after the refactor lands                                                          |
| C    | ROS messages and services in `interfaces`                       | Every node, tool, test fixture and stored event that uses the message. Renaming a field keeps the serialized byte layout, but breaks every source file that names the field, and anything that reads messages by field name (YAML fixtures, bag and database tools). Changing a type, or adding or reordering fields, also breaks the byte layout, so stored events need migrating | Once, as one versioned interface change, never piecemeal                                            |
| keep | Names that are already right, or not worth the churn            | None                                                                                                                                                                                                                                                                                                                                                                               | Document the meaning instead                                                                        |

The scheduler's own state is filled from messages (`DiscreteGarageState` stores `DiscreteAgvStateMsg` values directly), so a tier C rename also shows up in C++. Where a message name is wrong but the change is not worth it yet, the row says *keep* and the C++ side uses the right word in its own variables.

The proposals agree with the vocabulary the Background tab already teaches: node, heading, pose, vertex, asset type and footprint type (the [Background](#doc-background) tab, [the words for places](#bg-node-heading-pose-vertex-the-words-for-places) and [asset types](#bg-asset-types-and-the-other-kinds-of-type)).

### Naming rules

Ten rules. Most come from the Google C++ Style Guide (which the codebase already follows for casing), ROS REP 103 (units) and the robotics and graph literature (vocabulary).

#### Spell words out

Write `motion_graph_`, not `gg_`; `pose_vs_pose_`, not `ppmap_`; `job_index_`, not `job_idx_`. The Google style guide's test is whether a reader outside the project would understand the name, and two-letter members fail it: `gg_` appears 82 times in `scheduler.cpp` and every one needs the class definition to decode.

Abbreviations that stay, because they are the standard names of things: **AGV**, **VRC** (vertical reciprocating conveyor, the industry term), **VECS**, **DAG**, **GUID**, **id**, **ROS**, and `ctx` for a context parameter. The `Msg`, `Srv` and `SPtr` suffixes also stay; they are used consistently.

#### One concept, one word

Today several concepts have three to five names each, and several names mean three or four things. [Figure 1](#nm-fig-82_naming_today) shows the worst cases. The table below fixes one word per concept. The rest of this section applies it.

![One concept, many names: the worst cases today](figures/82_naming_today.svg)

**One concept, many names.** Each card is one concept, with the spellings it has today across messages and C++ (left) and the proposed single word (right). From the six source snapshots.

| Concept                                                            | Use                                         | Instead of                                                                                          | Reference                                                                                           |
|--------------------------------------------------------------------|---------------------------------------------|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| A place in the layout                                              | **node**                                    | "fixed vertex" (comment in `GarageNode.msg`), "waypoint" as a generic word (it is also a node type) | Graph theory; Open-RMF uses *waypoint* for the same thing, but here waypoint is already a node type |
| A discrete facing, integer degrees                                 | **heading**                                 | "orientation" (`DisallowedEdgeOrientation`), "yaw" for degrees                                      | —                                                                                                   |
| A continuous facing, radians                                       | **yaw**                                     | "heading" for radians                                                                               | ROS REP 103: angles in radians                                                                      |
| (node, heading)                                                    | **pose** (`GaragePose`)                     | "garage rep" (`GetFromGarageRep`)                                                                   | —                                                                                                   |
| A pose's number in the motion graph                                | **vertex**                                  | "pose index" when the motion graph is meant                                                         | Boost Graph Library                                                                                 |
| An allowed AGV move from one pose to another                       | **transition**                              | "edge" in prose, "move", "Edge" (`CollisionTable`)                                                  | State-transition graph; state-lattice planning                                                      |
| A transition's two endpoints, as a collision-table key             | **segment**                                 | `CollisionTable::Edge`                                                                              | "Path segment"                                                                                      |
| An undirected connection between two nodes in the layout YAML      | **edge** (layout edge)                      | —                                                                                                   | Only place "edge" stays as a data name; in Boost code, `Edge` is the library's descriptor           |
| "u must finish before v" in a DAG                                  | **dependency**                              | "edge" in prose about the event DAG                                                                 | Already the method name (`AddDependency`)                                                           |
| A physical thing the scheduler plans for                           | **asset**, and **asset type**               | "entity" (`GarageEntityId`, `entity_type`, `last_entity_event`)                                     | Fleet and facility management; "entity" is generic                                                  |
| The rectangle class a footprint is sized by (COMPACT, …, XL, TRAY) | **size class**                              | "parking window", "resource window", "resource size", "max_resource_size"                           | Vehicle size classes                                                                                |
| Which footprint shape a collision query uses                       | **footprint type**                          | `CollisionEntityId`, "collision id"                                                                 | —                                                                                                   |
| The extra clearance added around a footprint                       | **footprint margin**                        | "buffer", "parking window buffer"                                                                   | Safety margin / clearance                                                                           |
| What a client asks for                                             | **job**                                     | "task" (`ScheduleEvent::ToString` prints `Task ID`)                                                 | —                                                                                                   |
| The planner's unit in the event DAG                                | **event**                                   | "node" when talking about the event DAG                                                             | —                                                                                                   |
| The dispatched unit in the response                                | **action** (the message stays `ActionNode`) | "node" alone (`Schedule.nodes`, `node_indices`)                                                     | Avoids ROS 2 "actions" by keeping the type name                                                     |
| The garage before the plan                                         | **initial state**                           | `base_state` (wire), "initial state" (C++)                                                          | AI planning: initial state and goal                                                                 |
| Vertical conveyor                                                  | **VRC**                                     | "lift" for the conveyor (`TYPE_LIFT`, `IsLiftNode`); "lift" stays for the AGV's lifting deck        | ASME B20.1 "vertical reciprocating conveyor"                                                        |

#### Endpoint pairs: one pair per kind

Today endpoints are spelled `src`/`dst`, `src`/`dest`, `_curr`/`_next`, `current_`/`next_`, `from_`/`to_` and `fixed`/`queried`. Use one pair for each kind of thing:

- **Graph edges: `source`, `target`.** Boost's own words (`boost::source(e, g)`, `boost::target(e, g)`).
- **Motions and commands: `start`, `goal`.** Motion-planning vocabulary, and `AgvGoal.msg` already uses *goal*.
- **State changes: `from`, `to`.** `VrcTransition` already has `from_vrc_node_id_` and `to_vrc_node_id_`.
- **A job's target: `destination`.** As in `SchedulerJob.destination`; not `dest`.

#### Units in the name when they are not obvious

Put the unit last in the name: `_m`, `_rad`, `_deg`, `_s`, `_kg`. `Payload.msg` and `ParkingWindow.msg` already do (`length_m`, `width_m`). A name needs a unit when the type alone does not say it: `ActionNode.duration` (seconds), `Transition.length` (metres *or* radians), `GarageFloor.z` (metres). `GaragePose.heading` and `GeometricPose.yaw` stay as they are: they are the defined words for degrees and radians, so the word carries the unit.

#### Ids, indices and their types

Ids are where the current names are least consistent: the same word can mean an object's identity, a reference to another object or a position in an array, and the same id can have different integer widths in different messages. The rules below separate these meanings.

- **`id` is the object's own identity; `<asset>_id` refers to another object.** So `SchedulerJob.guid` becomes `id`, and `ActionNode.job_id` stays as it is.
- **Generated ids are `Guid`.** Command ids are "unique GUID strings" today (`AgvCommand.id`, `BayCommand.command_id`); make them `Guid` like every other generated id.
- **`_index` is a position in an array; `_id` is never an index.** `Edge.msg` fields hold node *ids* but are commented "node index".
- **One integer type per id, everywhere.** Today the same id has different widths in different messages; see [Figure 1](#nm-fig-82_naming_today) and [section 6.1](#nm-ids-and-integer-widths).

#### Maps are named `<value>_by_<key>`

`Layout::node_ids_by_type_` already follows this. Apply it to the rest: `pose_to_vertex_` becomes `vertex_by_pose_`, `node_id_to_index_` becomes `index_by_node_id_`, `last_entity_event` becomes `last_event_by_asset`. The name then says what you get back and what you look it up with, in that order. A map keyed by the object's own id can keep the plural (`trays_`, `vrcs_`).

#### Booleans

In messages, a boolean field is an adjective or participle without a prefix: `disabled`, `charging`, `lift_raised`. `DiscreteGarageState.is_faulted` is the one field with an `is_` prefix. In C++, functions that return a boolean start with `Is`, `Has` or `Can` (`HasVertex`, `IsMovePossible` already do).

#### State versus status

**state** is an asset's state-machine value (an AGV's, a bay's, a VECS's, a VRC's). **status** is how far a job or an action has progressed. Today `ActionNode` uses `STATUS_*` but `SchedulerJob` uses `STATE_*` for the same kind of thing (unplanned, executing, success, error).

#### The same object has the same name at every layer

The collision table is `table_` in `Scheduler`, `collision_table_` in `GarageOccupancyChecker`, and `collisions` in the proposed `GarageServices`. Pick one name and use it for the member, the struct field, the parameter and the local: `collision_table`, `motion_graph`, `cost_model`, `layout`.

#### "Plan" means the `Plan()` call, and nothing else

The word is on `Plan()`, `PlanRequest`, `PlanResponse` and `PlanMotions`, and also on eleven job-expansion methods (`PlanRetrieveJob`, …) that do not plan anything: they expand a job into events. The Task planning tab calls that step *job expansion*. Name the methods after it (`ExpandRetrieveJob`).

### The headline renames

If you only do a few, do these. They are the names that appear most often in the code being refactored, or that cause the most confusion. Each is detailed in a later section.

| Current                                              | Proposed                                                                            | Tier              | Why                                                                                                 |
|------------------------------------------------------|-------------------------------------------------------------------------------------|-------------------|-----------------------------------------------------------------------------------------------------|
| `gg_` (class `GarageGraph`)                          | `motion_graph_` (class `MotionGraph`); if the class keeps its name, `garage_graph_` | A member, B class | 82 uses in `scheduler.cpp`; "garage graph" does not tell it apart from the layout's own node graph  |
| `table_`                                             | `collision_table_`                                                                  | A                 | Matches `GarageOccupancyChecker::collision_table_`                                                  |
| `pg_`                                                | remove the member: a local in the constructor                                       | A                 | Used once, to build `gg_`; `GarageGraph` keeps no pointer to it                                     |
| `ScheduleContext`, `ScheduleContextSPtr`             | `PlanContext`, `PlanContextSPtr`                                                    | A                 | It is the context of one `Plan()` call, and the variable is already `plan_ctx`                      |
| `BayTransition`, `VecsTransition`, `VrcTransition`   | `BayStateChange`, `VecsStateChange`, `VrcStateChange`                               | B                 | "Transition" is also the motion-graph edge type; these events wrap `BayStateChanged`-style messages |
| `Plan<Type>Job`                                      | `Expand<Type>Job`                                                                   | A                 | Rule in [section 2.10](#nm-rule-plan-word)                                                          |
| `CollisionEntityId`, `CollisionEntityId_t`           | `FootprintType`, `FootprintId`                                                      | B                 | It selects a footprint shape; "entity" collides with `GarageEntityId`, which means something else   |
| `GarageEntityId`                                     | `AssetId`                                                                           | C                 | Matches "asset type"; frees "entity"                                                                |
| `Transition.length` (m or rad)                       | `distance_m` and `angle_rad`                                                        | B                 | One field, two units                                                                                |
| "parking window", "resource window", "resource size" | "size class" everywhere                                                             | B C++, C messages | Five words for one concept                                                                          |
| `BoolStringPair`                                     | `stdx::Result`                                                                      | A then B          | Already proposed ([section 6.4](#pr-errors-stdxexpected-instead-of-boolstringpair))                 |

**On `gg_` specifically:** `garage_graph_` is a correct mechanical fix, but it keeps a vague class name. The garage has three graphs (the layout's node graph, the pose-expanded motion graph, and the event DAG), and "garage graph" could be any of them. Its vertices are poses and its edges are the transitions an AGV can make, which is what *motion graph* says. Rename the member once, after the class decision ([section 9](#nm-decisions-for-review)), so it does not change twice.

### The `scheduler` package

All tier A: these names are private to the package, so rename them in the same change that moves the code.

#### Scheduler members

The members of the `Scheduler` class; most changes spell abbreviations out or give one object the same name everywhere it appears.

| Current                                                     | Proposed                             | Where                                 | Why                                                                                                      |
|-------------------------------------------------------------|--------------------------------------|---------------------------------------|----------------------------------------------------------------------------------------------------------|
| `gg_`                                                       | `motion_graph_` (or `garage_graph_`) | `scheduler.hpp`                       | Spell words out; see [section 3](#nm-the-headline-renames)                                               |
| `pg_`                                                       | constructor local `pose_graph`       | `scheduler.hpp`, `scheduler.cpp:1324` | Only read by `gg_(pg_)`. Build the motion graph with a helper that takes the layout, and drop the member |
| `table_`                                                    | `collision_table_`                   | `scheduler.hpp`                       | Same object, same name                                                                                   |
| `costaudit_`                                                | `cost_audit_`                        | `scheduler.hpp`                       | The parameter it mirrors is already `SchedulerParams::cost_audit`                                        |
| `printdags_`, `PrintDags()`                                 | `print_dags_`, `TogglePrintDags()`   | `scheduler.hpp`                       | Word break; the method toggles, it does not print                                                        |
| `layout_`, `cost_model_`, `logger_`, `bay_readiness_ratio_` | keep                                 | `scheduler.hpp`                       | Already clear                                                                                            |
| `GetGarageGraph()`, `GetCollisionTable()`                   | `GetMotionGraph()`, keep             | `scheduler.hpp`                       | Follows the class name                                                                                   |

#### ScheduleContext

The per-call context and its fields, starting with the class itself, which becomes `PlanContext`.

| Current                                                       | Proposed                                                                                       | Why                                                                                                                                                                                                                                                                                               |
|---------------------------------------------------------------|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ScheduleContext`, `ScheduleContextSPtr`                      | `PlanContext`, `PlanContextSPtr`                                                               | One per `Plan()` call; the variable is already `plan_ctx`                                                                                                                                                                                                                                         |
| `request_id_str`                                              | remove; format `request_id` where it is logged                                                 | A cached copy of another member                                                                                                                                                                                                                                                                   |
| `events`                                                      | `event_dag`                                                                                    | It is the DAG, not a list of events. Short enough to keep if the team prefers                                                                                                                                                                                                                     |
| `disabledness_filters`, type `CollistionFilterMap`            | `keep_out_filter_by_footprint`, type `KeepOutFilterByFootprint`                                | "Disabledness" is not a word and "Collistion" is a typo. The value is a keep-out mask built once from reserved and disabled assets, which tells it apart from the per-state filters of `GetStaticFilter`; the key is a footprint type ([section 14.4](#bg-disabledness-filters-the-keep-out-map)) |
| The `base_schedule` loop inline in `Plan()`                   | `ReserveBaseScheduleAssets(...)` returning `BaseScheduleReservation {agvs, bays, vecs, nodes}` | Names the intent (reserve for the running schedule) and keeps a record that error messages can use, while still calling the `common_ros` setters for parity ([section 14.6](#pr-base-schedule-reservation))                                                                                       |
| `last_entity_event`, type `GarageEntityEventMap`              | `last_event_by_asset`, type `AssetEventMap`                                                    | Map rule; asset, not entity                                                                                                                                                                                                                                                                       |
| `first_tray_event`                                            | `first_event_by_tray`                                                                          | Map rule; reads the same way as its sibling                                                                                                                                                                                                                                                       |
| `PushBackScheduledJob`                                        | `AddScheduledJob`                                                                              | Says what, not how                                                                                                                                                                                                                                                                                |
| `UpdateLastEntityEvent(entity, event)`                        | `AppendToAssetChain(asset, event)`                                                             | It adds a dependency on the asset's previous event, then records the new one: the asset's events form a chain                                                                                                                                                                                     |
| `UpdateLeafDependencies(event, job_index)`                    | `AddAfterJobLeaves(event, job_index)`                                                          | The new event depends on the current leaves of the same job                                                                                                                                                                                                                                       |
| `initial_state`, `scheduled_jobs`, `request_id`, `start_time` | keep                                                                                           | `initial_state` is the standard term; the message should move to it ([section 6.4](#nm-jobs-plans-and-schedules))                                                                                                                                                                                 |

#### Pipeline stages: folders and namespaces

The refactor organises the `scheduler` package by pipeline stage ([section 6](#pr-module-layout-folders-or-packages)): one folder, one CMake target and one namespace per stage, and possibly one package per stage later. These are names people will say every day, and they may become package names. All of them are tier A while they stay folders.

| Stage                           | Folder · namespace                                                          | Why                                                                                                                                                                                                                                                                                                                                 |
|---------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1–3 · jobs → finished event DAG | `task_planning/` · `volley::task_planning`                                  | The stages decompose jobs into events, allocate trays and AGVs, and add blocker moves: decomposition plus allocation is what "task planning" means. Close to the existing `task_planner` package (which holds `BottleneckAssignment`, used by stage 3); if reviewers find that confusing, `event_planning` names the output instead |
| 1 · job expansion               | `task_planning/job_expansion/`                                              | "Expand" is the stage's verb (`Expand<Type>Job`); "plan" is reserved for `Plan()` ([section 2.10](#nm-rule-plan-word))                                                                                                                                                                                                              |
| 2 · tray assignment             | `task_planning/tray_assignment/` · `volley::task_planning::tray_assignment` | Job expansion also moves trays; this step only fills in what expansion left open ([section 8.2](#pr-source-tree))                                                                                                                                                                                                                   |
| 3 · AGV assignment              | `task_planning/agv_assignment/` · `volley::task_planning::agv_assignment`   | Pairs with `tray_assignment`; matching is one step inside it                                                                                                                                                                                                                                                                        |
| 3 · validation                  | `task_planning/validation/`                                                 | Matches `ValidateEvents`                                                                                                                                                                                                                                                                                                            |
| 4 · timed motions               | `motion_planning/` · `volley::motion_planning`                              | CHUGG plans timed trajectories for all agents together. Matches the package that does the work (`motion_planner`) and `PlanMotions`. The namespace must not be `motion_planner`, so it cannot hide the package's names                                                                                                              |
| 5 · action DAG                  | `action_graph/` · `volley::action_graph`                                    | The output is a partial order: actions of different AGVs run in parallel unless an edge orders them (Action graph tab). Spelled out rather than the acronym                                                                                                                                                                         |
| shared                          | `core/` · `volley::scheduler_core`                                          | A `volley::common` namespace would hide `::common` and break today's `common::EnumInteger` calls ([section 8.2](#pr-source-tree))                                                                                                                                                                                                   |

The stage functions follow. The refactor already moves tray and AGV assignment behind `tray_assignment::Solve` and `agv_assignment::SolveInPlace`. The remaining functions along `Plan()` read better as verb phrases, and the action-DAG helpers can drop words their folder now says.

| Stage | Current                                            | Proposed                                                  | Why                                                                                                                                                                                           |
|-------|----------------------------------------------------|-----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1     | `PlanRetrieveJob`, `PlanInsertJob`, … (12 methods) | `ExpandRetrieveJob`, `ExpandInsertJob`, …                 | Job expansion; rule in [section 2.10](#nm-rule-plan-word)                                                                                                                                     |
| 2–3   | `DoTrayAssignments`, `DoAgvAssignments`            | `AssignTrays`, `AssignAgvs` (or the proposed solvers)     | "Do" adds nothing                                                                                                                                                                             |
| 3     | `SanityCheckEvents`                                | `ValidateEvents`                                          | Standard verb                                                                                                                                                                                 |
| 3     | `AddDepsAfterAmiga` (and the `Amiga*` test names)  | a name that says what the step does                       | A project nickname; a new reader cannot guess it. What it does is in the call trace in the Background tab                                                                                     |
| 4     | `Scheduler::PlanMotions`                           | `motion_planning::PlanMotions`                            | Keep the name: it does plan motions. It becomes a free function                                                                                                                               |
| 5     | `ResponseFromTrajectories`                         | `BuildPlanResponse`                                       | Verb first; stays in `Scheduler` and calls the `action_graph` functions                                                                                                                       |
| 5     | `CollectAndCollapseTrajectoryMotions`              | `action_graph::CollectMotions`                            | The collapsing of floor-traversal runs is documented in the comment; the name keeps the verb                                                                                                  |
| 5     | `BuildActionDagFromMotions`                        | `action_graph::BuildActionDag`                            | The argument type says "from motions"                                                                                                                                                         |
| 5     | `TransferEventDagDepsToActionDag`                  | `action_graph::CopyEventDependencies`                     | "Dependency" spelled out (sections [2.1](#nm-rule-spell-words-out), [2.2](#nm-rule-one-concept-one-word)); "copy" says the event DAG is unchanged; the namespace says which DAG receives them |
| 5     | `InsertVrcActionsIntoDag`                          | `action_graph::InsertVrcActions`                          | The namespace says which DAG                                                                                                                                                                  |
| 5     | `BuildScheduledActionsArray`, `ToActionNode`       | `action_graph::FlattenActionDag`, keep `ToActionNode`     | It flattens the DAG, in topological order, into the indexed message list Dispatch reads, with parent indices; "array" names the container, not the job                                        |
| 5     | `DagBase<ActionNodeMsg>`, `final_actions_dag`      | `using ActionDag = DagBase<ActionNodeMsg>;`, `action_dag` | Pairs with `EventDag`; "final" says nothing once the variable lives in one function                                                                                                           |
| —     | `Plan`                                             | keep                                                      | It is the plan call                                                                                                                                                                           |

#### Names seen in `motion_planner`

Not part of this refactor: `motion_planner` is outside the scheduler and `planner_core`, so these are tier B rows for its owners, listed because the scheduler code reads them.

| Current                                        | Proposed                                              | Tier | Why                                                                                                                                                                                                     |
|------------------------------------------------|-------------------------------------------------------|------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Motion::action_id`, `GetActionId()`           | `event_index`, `GetEventIndex()`                      | B    | It holds the event DAG vertex index the motion came from, not an action: actions only exist after stage 5. Static motions use `999999` as "no event"; an `std::optional` or named constant would say so |
| `kMagicPredecessorCost`                        | `kPerPredecessorPenalty`                              | B    | Say what the 3 s is: a penalty per predecessor state in SIPP (the [Motion planning](#doc-motion-planning) tab, [SIPP](#bg-sipp-the-single-agv-search))                                                  |
| `GetEdgeDurations`, `GetEdgeMarginalDurations` | `GetEdgeTrapezoidDurations`, `GetEdgeCruiseDurations` | B    | Two kinds of duration per edge; the name should say which model each uses                                                                                                                               |

### planner_core: events and the DAG

The event classes and the DAG in `planner_core`; this refactor adopts these tier B rows and keeps the old names as deprecated aliases for the package's other users ([section 9.5](#pr-renames-in-planner-core)).

| Current                                                                                                 | Proposed                                                                       | Tier | Why                                                                                                              |
|---------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|------|------------------------------------------------------------------------------------------------------------------|
| `BayTransition`, `VecsTransition`, `VrcTransition`                                                      | `BayStateChange`, `VecsStateChange`, `VrcStateChange`                          | B    | Frees "transition" for the motion graph; matches the `*StateChanged` messages they apply                         |
| `ScheduleEventType::{AGV_MOVE, BAY_TRANSITION, TRAY_MOVE, VECS_TRANSITION, VRC_TRANSITION}`             | `{AGV_MOVE, TRAY_MOVE, BAY_STATE_CHANGE, VECS_STATE_CHANGE, VRC_STATE_CHANGE}` | B    | Follows the classes. `VRC_TRANSITION` is also a `TransitionType` value with a different meaning                  |
| `ScheduleEvent::job_idx_`                                                                               | `job_index_`                                                                   | B    | Matches `GetJobIndex()` and the constructor parameter                                                            |
| `ToString()` prints `"Task ID: "`                                                                       | `"job_index="`                                                                 | B    | It is a job index, not a task id; logs are searched for this                                                     |
| `TrayMove::dest_`, `SetDest`, `GetDest`                                                                 | `destination_`, `SetDestination`, `GetDestination`                             | B    | Same word as `SchedulerJob.destination`                                                                          |
| `BayTransition::src_state_`, `SetSourceState`                                                           | `from_state_`, `SetFromState`                                                  | B    | State-change endpoint rule                                                                                       |
| `AgvMove::discrete_change_`                                                                             | `change_`                                                                      | B    | Everything in planner_core is discrete; the type (`variant<AgvLiftChangedMsg, AgvPoseChangedMsg>`) says the rest |
| `ScheduleEventDag`                                                                                      | `EventDag`                                                                     | B    | Shorter; "schedule" is the response's DAG of actions, a different graph                                          |
| `DagBase<T>`, `AddEvent`, `AddDependency`, `GetEventFromVertex`, `ScheduleEvent`, `AgvMove`, `TrayMove` | keep                                                                           | keep | Already clear and consistent                                                                                     |

### common_ros: the garage model

The garage model in `common_ros` is public API used by many other packages, so these rows are not adopted in this refactor; the scheduler uses the proposed names through the translation header ([section 9.2](#pr-the-translation-header)) until `common_ros` adopts them.

#### GarageGraph and Transition

The garage graph is the motion graph every search runs on: its vertices are poses and its edges are AGV transitions. The rows below propose clearer names for the class, its underlying Boost graph and the way edge properties are stored.

| Current                                                                         | Proposed                                                                                                                                                   | Tier | Why                                                                                                                                                                                                                                                             |
|---------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `GarageGraph`                                                                   | `MotionGraph`                                                                                                                                              | B    | Vertices are poses, edges are AGV transitions. Decision in [section 9](#nm-decisions-for-review)                                                                                                                                                                |
| `BoostPoseGraph`, `base_graph_`                                                 | `BoostMotionGraph`, `boost_graph_`                                                                                                                         | B    | "Base" already means something else (`base_state`, `base_schedule`); this is the Boost object                                                                                                                                                                   |
| Edge properties `boost::property<boost::edge_index_t, std::size_t, Transition>` | a bundled struct `TransitionEdge {std::size_t index; Transition transition;}`, with `EdgeVectorPropertyMap<T>` built over `get(&TransitionEdge::index, g)` | B    | The current Boost style; one mechanism instead of two. Changes the public `EdgeVectorPropertyMap` type and `base_graph_[e]`, so every caller is affected (the [Background](#doc-background) tab, [reading the type](#bg-reading-the-boost-adjacency-list-type)) |
| `pose_to_vertex_`                                                               | `vertex_by_pose_`                                                                                                                                          | B    | Map rule                                                                                                                                                                                                                                                        |
| `edge_index_to_vertices_`                                                       | `endpoints_by_edge_index_`                                                                                                                                 | B    | Map rule                                                                                                                                                                                                                                                        |
| `node_retrieval_heading_`                                                       | `retrieval_heading_by_node_`                                                                                                                               | B    | Map rule                                                                                                                                                                                                                                                        |
| `GetFromGarageRep(pose)`                                                        | remove; call `GetVertexFromPose(pose).value()`                                                                                                             | B    | A second name for the same lookup, with an unexplained word ("rep")                                                                                                                                                                                             |
| `GarageNodeFromVertex`                                                          | `GetNodeFromVertex`                                                                                                                                        | B    | Same `Get…From…` pattern as its siblings                                                                                                                                                                                                                        |
| `LocomoteOrStrafe`                                                              | `ClassifyTranslation`                                                                                                                                      | B    | Says what it does; follows the enum rename below                                                                                                                                                                                                                |
| `TransitionType::{LOCOMOTE, STRAFE, ROTATION, VRC_TRANSITION}`                  | `{TRANSLATE_LONGITUDINAL, TRANSLATE_LATERAL, ROTATE, RIDE_VRC}`                                                                                            | B    | "Strafe" is game slang and "locomote" is vague. Longitudinal (along the heading) and lateral (across it) are the vehicle-dynamics terms. `AgvCommand.msg` already calls both "translate". `RIDE_VRC` ends the clash with the event type                         |
| `Transition::length`                                                            | `distance_m`, `angle_rad`                                                                                                                                  | B    | Struct refactor in [section 7.1](#nm-transition-units)                                                                                                                                                                                                          |
| `Vertex`, `Edge`, `HasVertex`, `GetOutEdges`                                    | keep                                                                                                                                                       | keep | Boost's vocabulary; the Background tab teaches it                                                                                                                                                                                                               |

#### PoseGraph and Layout

The pose lattice and the layout class, where most proposals apply the map naming rule or use "size class" as the one word for parking windows, resource windows and resource sizes.

| Current                                                                                  | Proposed                                                                       | Tier | Why                                                                                                                                                                                                                        |
|------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PoseGraph`                                                                              | `PoseLattice`                                                                  | B    | In robotics, "pose graph" means the SLAM graph of robot poses and measurements, so the name misleads. This class lists the poses, each with up to eight neighbour slots, which is a lattice (as in state-lattice planning) |
| `pose_indices_`                                                                          | `index_by_pose_`                                                               | B    | Map rule                                                                                                                                                                                                                   |
| `pose_neighbors_` (flat `vector<int>`, 8 per pose, −1 = none)                            | `neighbors_`, a `vector<NeighborSlots>`                                        | B    | Struct refactor in [section 7.4](#nm-neighbor-slots)                                                                                                                                                                       |
| `overlapping_sized_poses_`                                                               | `overlaps_by_pose_and_size_class_`                                             | B    | Says what the two outer indices are                                                                                                                                                                                        |
| typedef `graph`, member `graph_`                                                         | `NodeGraph`, `node_graph_`                                                     | B    | Type names are UpperCamelCase; says which graph                                                                                                                                                                            |
| `node_id_to_index_`, `floor_id_to_index_`                                                | `index_by_node_id_`, `index_by_floor_id_`                                      | B    | Map rule                                                                                                                                                                                                                   |
| `resource_windows_`, `resource_name_to_index_`, `GetResourceWindow(resource_size_index)` | `size_classes_`, `size_class_index_by_name_`, `GetSizeClass(size_class_index)` | B    | One word for the concept                                                                                                                                                                                                   |
| `kResourceSizeIndexAgv`, `kResourceSizeIndexTray`                                        | `kSizeClassAgv`, `kSizeClassTray`                                              | B    | Same                                                                                                                                                                                                                       |
| `parking_window_buffer_`, `GetBufferedResourceWindow`                                    | `footprint_margin_`, `GetSizeClassWithMargin`                                  | B    | "Margin" is the usual word for added clearance                                                                                                                                                                             |
| `bay_insert_floors_`, `bay_system_floors_`                                               | `insert_floor_by_bay_`, `system_floors_by_bay_`                                | B    | Map rule                                                                                                                                                                                                                   |
| `IsLiftNode` (VRC stops)                                                                 | `IsVrcNode`                                                                    | B    | VRC is the conveyor; "lift" is the AGV's deck                                                                                                                                                                              |
| `Layout`, `nodes_`, `floors_`, `node_ids_by_type_`, `vrcs_`, `Vrc`                       | keep                                                                           | keep | Already clear; `node_ids_by_type_` is the model for the map rule                                                                                                                                                           |

#### CollisionTable and footprints

The collision table and its footprint types, where the main problems are abbreviated map names and the overloaded word "edge".

| Current                                                                 | Proposed                                                                       | Tier | Why                                                                                                                                                                         |
|-------------------------------------------------------------------------|--------------------------------------------------------------------------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CollisionEntityId` (enum), `CollisionEntityId_t` (`uint8_t`)           | `FootprintType`, `FootprintId`                                                 | B    | The value picks a footprint shape: `PAYLOAD + k` is the payload footprint of size class *k*, so the integer is an id, not just a type. The `_t` suffix is reserved by POSIX |
| `VertexCollisionIdMap`                                                  | `FootprintIdByVertex`                                                          | B    | Map rule                                                                                                                                                                    |
| `CollisionTable::Edge` (`std::array<Pose, 2>`), `PoseOrEdge`, `EdgeSet` | `Segment` (a struct), `PoseOrSegment`, `SegmentSet`                            | B    | "Edge" means three things; struct refactor in [section 7.3](#nm-segment-struct)                                                                                             |
| `ppmap_`, `pemap_`, `epmap_`, `eemap_`, types `PosePoseMap`, …          | `pose_vs_pose_`, `pose_vs_segment_`, `segment_vs_pose_`, `segment_vs_segment_` | B    | Spell words out                                                                                                                                                             |
| `ResMap`                                                                | `ConflictMap`                                                                  | B    | "Res" could be resource, result or resolution; the map holds conflicts                                                                                                      |
| `gg_` (in `CollisionTable` and `GarageOccupancyChecker`)                | `motion_graph_`                                                                | B    | Same object, same name                                                                                                                                                      |
| `BAY_ODP`                                                               | `BAY_OVERDRIVE_PLATE`                                                          | B    | ODP is the overdrive plate, the bay's sliding plate that stops a car from driving over the bay's edge; an unexplained acronym in a public enum                              |
| `CollisionTable`, `Query`, `collision_table_`, `occupancy_state_`       | keep                                                                           | keep | Clear                                                                                                                                                                       |

#### DiscreteGarageState and asset ids

The discrete garage state is mostly well named; the rows below change only the VECS plural and the helper functions that build asset ids.

| Current                                                                           | Proposed                                 | Tier  | Why                                                                                 |
|-----------------------------------------------------------------------------------|------------------------------------------|-------|-------------------------------------------------------------------------------------|
| `vexen_` (and `DiscreteGarageState.vexen`)                                        | `vecs_` (and `vecs`)                     | B / C | A joke plural nobody searches for. `vecs` reads as the plural, like "series"        |
| `AgvId()`, `TrayId()`, `BayId()`, `VecsId()`, `VrcId()`, `SystemId()`             | `AgvAssetId()`, …, or `AssetId::Agv(id)` | B     | They build a `GarageEntityIdMsg`, not a number; `TrayId(5)` reads like a `uint16_t` |
| `DiscreteGarageState`, `agvs_`, `trays_`, `bays_`, `payloads_`, `disabled_nodes_` | keep                                     | keep  | Clear; pairs with `ContinuousState`                                                 |

### ROS interfaces

All tier C. Do these as one versioned interface change, after the C++ refactor. Field renames alone keep the serialized layout. Type changes (the id widths in [section 6.1](#nm-ids-and-integer-widths)) and restructuring ([section 7](#nm-struct-refactors)) change it, so stored events (`DiscreteGarageEvent.buffer` holds serialized messages) need a migration or a reader for the old version.

#### Ids and integer widths

The same id is stored with different integer widths in different messages today; the table gives the current widths and the single width proposed for each id.

| Id                     | Today                                                                                                                                                                                               | Proposed                                                  |
|------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| AGV, bay, VECS, VRC id | `uint16` in the state and event messages; `uint32` in `ActionNode` (`agv_id`, `bay_id`, `vecs_id`, `vrc_id`); `uint32_t` in `Vrc`                                                                   | `uint16` everywhere                                       |
| Floor id               | `uint8` (`GarageFloor.id`, `GarageNode.floor`, `BayCommand.floor`); `uint16` (`DiscreteVrcState.current_floor`, `VrcCommand.requested_floor`); `uint32` (`GarageTray.floor`, `GaragePayload.floor`) | `uint8` everywhere, and the field names end in `floor_id` |
| Command id             | `string` "unique GUID string" (`AgvCommand.id`, `BayCommand.command_id`, `VecsCommand.command_id`, `VrcCommand.command_id`)                                                                         | `Guid id`                                                 |
| Node id, tray id       | `uint32`, `uint16`                                                                                                                                                                                  | keep                                                      |

#### Garage model messages

The messages that describe the garage layout and its assets, including the replacement of `GarageEntityId` by `AssetId`.

| Message.field                                                                                      | Proposed                                                                  | Why                                                                                                                                                 |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `GarageEntityId` (`string<=1 entity_type`, `uint16 id`)                                            | `AssetId` (`uint8 asset_type` with `TYPE_AGV = 97` ('a'), …, `uint16 id`) | "Asset type"; a one-character string becomes an enumerated byte. Keeping the character codes as values keeps log names like `a8` unchanged          |
| `GarageNode.floor`                                                                                 | `floor_id`                                                                | It is an id (rule in [section 2.5](#nm-rule-ids-and-indices))                                                                                       |
| `GarageNode.max_resource_size` (string) and `max_resource_size_index`                              | `max_size_class_index` only                                               | Two fields hold the same fact; the name is derivable from the layout                                                                                |
| `GarageNode.bay_prioritization`                                                                    | `bay_insert_preference`                                                   | The comment defines it: high positive means "prefer ready for insert"                                                                               |
| `GarageNode.TYPE_LIFT`, `TYPE_BLIFT`                                                               | `TYPE_VRC`, and a name for BLift that the layout owners agree             | VRC is the conveyor. The YAML strings ("Lift", "BLift") can stay as input spellings                                                                 |
| `SizedPose.resource_size_index`                                                                    | `size_class_index`                                                        | One word for the concept                                                                                                                            |
| `ParkingWindow`; `GarageLayout.resource_windows`, `buffer`                                         | `SizeClass`; `size_classes`, `footprint_margin`                           | Same                                                                                                                                                |
| `Edge.src`, `Edge.dst` ("node index")                                                              | `node_id_a`, `node_id_b`                                                  | Layout edges are undirected (`GarageLayout.msg` says so), and the values are ids                                                                    |
| `DisallowedEdgeOrientation` (`src`, `dst`, `heading`)                                              | a `disallowed_headings` list on `Edge`                                    | Struct refactor in [section 7.6](#nm-lane-headings); "orientation" means heading                                                                    |
| `GarageFloor.z`                                                                                    | `z_m`                                                                     | Unit rule                                                                                                                                           |
| `GaragePose`, `GeometricPose`, `heading`, `yaw`, `Guid`, `GarageNode.headings`, `faces_reciprocal` | keep                                                                      | Correct and everywhere. Fix the comment on `GarageNode.headings` instead: it lists base headings in \[0, 179\], and each also allows its reciprocal |

#### State and event messages

The messages that carry asset state and its changes, where the proposals give one spelling to each fact and apply the state-change and boolean rules.

| Message.field                                                                                            | Proposed                                           | Why                                                             |
|----------------------------------------------------------------------------------------------------------|----------------------------------------------------|-----------------------------------------------------------------|
| `DiscreteGarageState.is_faulted`, `vexen`                                                                | `faulted`, `vecs`                                  | Boolean rule; plural                                            |
| `DiscreteAgvState.lift`, `AgvGoal.lift`, `AgvLiftChanged.raised`                                         | `lift_raised` in all three                         | Three spellings of one fact; `lift` alone reads like a noun     |
| `AgvPoseChanged`, `TrayPoseSetManually` (`node_id_curr`, `heading_curr`, `node_id_next`, `heading_next`) | `GaragePose from`, `GaragePose to`                 | Struct refactor in [section 7.2](#nm-nested-poses)              |
| `AgvStateChanged`, `BayStateChanged`, `VecsStateChanged` (`state_curr`, `state_next`)                    | `from_state`, `to_state`                           | State-change rule                                               |
| `VrcStateChanged` (`current_discrete_state`, `next_discrete_state`)                                      | `from_state`, `to_state`                           | Same pair as its siblings                                       |
| `DiscreteVrcState.current_floor`, `requested_floor`                                                      | `current_floor_id`, `requested_floor_id` (`uint8`) | Id rule and width                                               |
| `*DisablednessChanged`, `SetResourceDisabledness.srv`                                                    | `*DisabledChanged`, `SetAssetDisabled.srv`         | "Disabledness" is not a word; "resource" here means asset       |
| `DiscretePayloadState.reciprocal_to_tray`, `charging`; `*ExistenceChanged`                               | keep                                               | Clear; "reciprocal" is the defined house word for heading + 180 |

#### Jobs, plans and schedules

The messages that carry plan requests, jobs and the resulting schedule; several fields named after nodes or GUIDs actually hold action indices or ids.

| Message.field                                                                                                                           | Proposed                                              | Why                                                                                                                       |
|-----------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `PlanRequest.base_state`                                                                                                                | `initial_state`                                       | The C++ side already says `initial_state`; "base" also means the committed schedule                                       |
| `SchedulerJob.guid`, `ActionNode.guid`                                                                                                  | `id`                                                  | Id rule; the type already says GUID                                                                                       |
| `SchedulerJob.state`, `STATE_*`                                                                                                         | `status`, `STATUS_*`                                  | State-versus-status rule, matching `ActionNode.status`                                                                    |
| `SchedulerJob.type_name`, `state_name`                                                                                                  | remove; tools format the constants                    | Copies of other fields that can disagree with them                                                                        |
| `ScheduledJobData.node_indices`                                                                                                         | `action_indices`                                      | They index `Schedule.nodes`, which are actions, not garage nodes                                                          |
| `ScheduledJobData.bay_arrival_node_guid`                                                                                                | `bay_arrival_action_id`                               | Id rule; action, not node                                                                                                 |
| `ActionNode.parents`                                                                                                                    | `parent_indices`                                      | They are indices into `Schedule.nodes`                                                                                    |
| `ActionNode.duration`                                                                                                                   | `duration_s`                                          | Unit rule                                                                                                                 |
| `ActionNode.outside_split`                                                                                                              | `after_split` (or a name the dispatcher team prefers) | "Outside" does not say which side                                                                                         |
| `ActionNode`, `Schedule.nodes`, `PlanRequest.base_schedule`, `pending_jobs`, `seconds_to_bay_arrival`, `allow_reciprocal`, `retain_job` | keep                                                  | `Action` alone would collide with ROS 2 actions; the others are clear (`seconds_to_bay_arrival` already carries its unit) |

#### Command messages

The commands for AGVs, bays, VECS and VRCs, where the proposals remove redundant prefixes and apply the id rule.

| Message.field                                                                                 | Proposed                   | Why                                                                              |
|-----------------------------------------------------------------------------------------------|----------------------------|----------------------------------------------------------------------------------|
| `AgvCommand.src`, `dst` (both `AgvGoal`)                                                      | `start`, `goal`            | Motion rule; the type is already called a goal                                   |
| `BayCommand`, `VecsCommand`, `VrcCommand`: `command_type` with `COMMAND_TYPE_*`, `command_id` | `type` with `TYPE_*`, `id` | Inside a command, "command" is redundant; matches `ActionNode.type` and `TYPE_*` |
| `VrcCommand.requested_floor`, `BayCommand.floor`                                              | `floor_id`                 | Id rule                                                                          |

### Small struct refactors

Each of these changes a field's shape, not just its name. They are small enough to do one at a time.

#### Transition: one unit per field

`Transition::length` holds metres for translations and radians for rotations; the proposal splits it into two fields, each with its unit in the name.

``` cpp
// today: common_ros/garage_graph.hpp
struct Transition {
  double length = 0.0;  // [m] for strafes and locomotes, [rad] for rotations
  TransitionType type = TransitionType::LOCOMOTE;
};

// proposed
struct Transition {
  TransitionType type = TransitionType::TRANSLATE_LONGITUDINAL;
  double distance_m = 0.0;  // translations: floor distance; RIDE_VRC: floor-to-floor height
  double angle_rad = 0.0;   // ROTATE only
};
```

Any code that turns a transition into a duration or a cost has to know that `length` means radians when the type is `ROTATION`. With two fields, a mix-up between metres and radians becomes a wrong field name, which code review can see.

#### Pose-change messages nest the pose

`AgvPoseChanged` and `TrayPoseSetManually` spell two poses out as four flat fields; the proposal nests two `GaragePose` values instead.

``` text
# today: AgvPoseChanged.msg (TrayPoseSetManually.msg is the same with tray_id)
uint16 agv_id
uint32 node_id_curr
int16 heading_curr # in degrees, [-179:180]
uint32 node_id_next
int16 heading_next # in degrees, [-179:180]

# proposed
uint16 agv_id
GaragePose from
GaragePose to
```

The flat fields repeat the pose definition and its range comment twice per message. The nested form is the same four numbers (the serialized layout does not change), and code can pass `msg.to` to anything that takes a `GaragePoseMsg`.

#### CollisionTable::Edge becomes a named struct

`CollisionTable::Edge` is a two-element array of poses whose order is only a convention; the proposal turns it into a struct with named endpoints.

``` cpp
// today: common_ros/collision_geometry.hpp
using Edge = std::array<Pose, 2u>;          // edge[0] is the start, edge[1] the end, by convention

// proposed
struct Segment {                            // the two poses of one transition, as a table key
  Pose source;
  Pose target;
  bool operator==(const Segment&) const = default;
};
```

Named fields replace `[0]` and `[1]`, and the name stops colliding with `GarageGraph::Edge` (a Boost descriptor) and the layout's `Edge.msg`. It needs a `std::hash` specialization, like the one `common_ros` defines for `std::array<GaragePoseMsg, 2>` today.

#### PoseGraph neighbour slots

`PoseGraph` stores the eight neighbour slots of every pose in one flat vector, with −1 for an empty slot; the proposal gives each pose a fixed array of optional slots.

``` cpp
// today: common_ros/pose_graph.hpp
std::vector<int> pose_neighbors_;   // 8 entries per pose, indexed by PoseNeighbor; -1 (kInvalidIndex) = none

// proposed
using NeighborSlots = std::array<std::optional<uint32_t>, 8>;   // indexed by PoseNeighbor
std::vector<NeighborSlots> neighbors_;                            // indexed by pose index
```

Today, finding pose *i*'s left neighbour means computing `i * 8 + LEFT` and comparing the result to −1. With the proposed type it is `neighbors_[i][LEFT]`, and an empty slot is an empty `optional`.

#### AssetId with an enumerated type

`GarageEntityId` names the asset type with a one-character string; the proposal replaces it with an enumerated byte whose constants list all six asset types.

``` text
# today: GarageEntityId.msg
string<=1 entity_type # 'a' AGV, 'b' bay, 't' tray, 'v' VECS (and 'r' VRC, 's' system, set in common_ros)
uint16 id

# proposed: AssetId.msg
uint8 TYPE_AGV = 97     # 'a'
uint8 TYPE_BAY = 98     # 'b'
uint8 TYPE_SYSTEM = 115 # 's'
uint8 TYPE_TRAY = 116   # 't'
uint8 TYPE_VECS = 118   # 'v'
uint8 TYPE_VRC = 114    # 'r'
uint8 asset_type
uint16 id
```

The comment in today's message lists four of the six letters; the other two exist only in `common_ros`. Constants put all six in the definition, and hashing or comparing a byte is cheaper than a string. Payloads are named by a `Guid` and have no letter; that stays as it is.

#### Disallowed headings live on the edge

The layout message keeps disallowed headings in a separate list that refers to edges by their end nodes; the proposal stores them on the edge itself.

``` text
# today: GarageLayout.msg
Edge[] edges                                              # Edge: src, dst
DisallowedEdgeOrientation[] disallowed_edge_orientations  # src, dst, heading

# proposed
Edge[] edges   # Edge: node_id_a, node_id_b, int16[] disallowed_headings (0:179, reciprocal implied)
```

`Layout` already joins the two lists into one map keyed by the node pair (`disallowed_edge_orientations_`). Storing the headings on the edge removes the join, and with it the chance of a disallowed heading that names an edge that does not exist.

### Keep as they are

Renames have a cost, so these stay. Most are already right, and the rest are too widespread to be worth changing.

- **`GaragePose` and `heading`, `GeometricPose` and `yaw`.** They pair correctly (degrees, radians), and they are in every message.
- **`Vertex`, `Edge` (in Boost code), `DagBase`.** Boost's vocabulary, and the Background tab teaches it.
- **`Layout`, `DiscreteGarageState`, `ScheduleEvent`, `AgvMove`, `TrayMove`, `CollisionTable`.** Clear and consistent.
- **`ActionNode`.** `Action` would collide with ROS 2 actions. Say "action" in field names instead.
- **"Reciprocal".** A house word, but defined once (heading + 180) and used consistently: `faces_reciprocal`, `allow_reciprocal`, `IsAngleOrReciprocal`.
- **The `Msg`, `Srv` and `SPtr` suffixes, and UPPER_CASE enum values.** The codebase is consistent here. Switching to the Google style's `kValue` would touch every enum and gain nothing.

### Decisions for review

Most rows of the catalogue are recommendations that can be applied as they stand; the items below need agreement from the team or from the owners of the affected names first.

1.  **`GarageGraph` → `MotionGraph`, and `PoseGraph` → `PoseLattice`?** Inside the scheduler this is settled by the translation header ([section 9.2](#pr-the-translation-header)), and members are `motion_graph_`. The `common_ros` class rename itself is still open; when it happens, the alias line is deleted and no scheduler code changes.
2.  **`TransitionType` values.** `TRANSLATE_LONGITUDINAL` and `TRANSLATE_LATERAL`, or shorter `DRIVE` and `CRAB`? Pick whatever the AGV team says out loud.
3.  **"Size class" for parking windows, resource windows and resource sizes.** Confirm with the layout owners, who write these in YAML.
4.  **The interface version.** Which tier C items go into it, and how stored `DiscreteGarageEvent` buffers are migrated or read.
5.  **Stage folder names.** Tracked with the folder layout in [section 12](#pr-decisions-to-resolve-in-review).
6.  **What `BAY_ODP` and `TYPE_BLIFT` should be called.** A BLift is a bay whose carriage is also a VRC terminal (`layout.cpp`: “A BLift is a Bay that is also a Lift (VRC) terminal”; Dispatch sends it `BayCommand.COMMAND_TYPE_MOVE_LIFT_TO_FLOOR` instead of a VRC command). The names should say that; `BAY_ODP` is the bay's overdrive plate (the sliding plate that stops a car from driving over the bay's edge), so `BAY_OVERDRIVE_PLATE` says it in full.

### Rollout

The tiers of [section 15.1](#nm-how-to-read-this-list) determine when each rename is made; the steps below give the order, from tier A renames during the refactor to one versioned interface change, and how to keep the names from drifting back.

1.  **Tier A with the refactor**, as in [section 9.4](#pr-renames-in-scheduler). When the staged plan ([section 11](#pr-staged-plan)) moves a function, rename what it touches in the same change, as a separate commit with no logic change. The parity tests of the [Verification](#doc-verification) tab then show the rename changed nothing.
2.  **Tier B after the refactor, one header at a time.** Add the new name. Keep the old one as a deprecated alias (`using GarageGraph [[deprecated("use MotionGraph")]] = MotionGraph;`), or as a forwarding method for functions, for one release. Then remove it.
3.  **Tier C once.** Collect the accepted rows into one interface change with a version bump. Update every consumer in the same release, and migrate or version-read stored events.
4.  **Keep it from drifting back.** Add a `clang-tidy` `readability-identifier-naming` configuration for the casing rules. Add the vocabulary table in [section 2.2](#nm-rule-one-concept-one-word) to the contributor guide, so review has a reference to point at.
