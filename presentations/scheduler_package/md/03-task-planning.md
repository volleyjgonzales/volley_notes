# 03 — Task planning: building the event DAG

*Stages 1–3 of the pipeline: everything that builds the event DAG. Job expansion turns each job into events, tray assignment fills in the trays and parking spots that expansion left open and moves blocking trays out of the way, and AGV assignment chooses an AGV for every tray move and adds its approach, lift and lower. `RemoveRedundantEdges()` and a sanity check (`ValidateEventSequence`) then finish the event DAG, which is the input of motion planning.*

This tab builds on the request messages, the reservation of the running schedule, the event classes, the event DAG and `PlanContext` from the Background tab (sections [6](#bg-ros-messages-and-services) and [11](#bg-event-types-and-polymorphism)–[13](#bg-schedulecontext-the-per-call-workspace) there). It starts with one job followed through all three stages, then takes each stage in turn. The single-agent searches that all three stages call come next, before the stages themselves, and the bay, VECS and VRC rules close the tab. Each stage has its own source file in `src/planner/scheduler/src/`: `job_expansion.cpp`, `tray_assignment.cpp`, `agv_assignment.cpp` and `validation.cpp`; `scheduler.cpp` keeps `Plan()` and `ExpandJob()`. Code and line numbers in this tab are from `main` at `a468657f` (2026-11-05).

## The whole journey of one job

Stages 1–3 of the pipeline ([Figure 1](#bg-fig-01_pipeline)) build the event DAG. All three stages edit the same `ctx->event_dag`, so an event created in one stage is completed or wrapped in another. Before the details of each stage, here is one retrieve followed through all three passes.

![Retrieve walkthrough](figures/26_retrieve_walkthrough.svg)

One `TYPE_RETRIEVE` job on Pecos, stage by stage. Step through it to watch the event DAG grow pass by pass; map numbers match event ids. Band 1: job expansion creates intent, including a move of the empty tray T21 out of the bay with no destination. Band 2: tray assignment gives T21 a destination and inserts a move for blocker T15, which sits on T17's critical path. Band 3: AGV assignment wraps every `TrayMove` in move → lift → carry → lower, and `OrderAllTransitionsAroundAgvLifts` ties the bay transitions to the right lift and lower. The last six steps play the plan on the map: AGV-1 follows each dashed preview arrow in the next step, moving T15 to `P19`, T21 to `P23` and T17 into `B21`, while the band-3 row being executed is outlined. Destinations and AGV order are illustrative.

Read the bands as the order of the next sections: band 1 is job expansion ([section 15](#bg-job-expansion-from-jobs-to-events)), band 2 tray assignment ([section 16](#bg-tray-assignment-dotrayassignments)), band 3 AGV assignment ([section 17](#bg-agv-assignment-doagvassignments)). After band 3, `RemoveRedundantEdges()` and the sanity check ([section 6](#bg-reduce-and-sanitycheckevents)) finish the event DAG. What happens to the finished DAG next is the subject of the [Motion planning](#doc-motion-planning) and [Action graph](#doc-action-graph) tabs; the Action graph tab follows a retrieve of the same shape through those last steps ([Figure 4](#ad-fig-87_adg_in_scheduler)).

## The single-agent searches in `motion_planner`

Task planning does not plan motions, but it needs answers that only a search can give: how long an AGV takes to reach a tray, which trays stand in a tray's way, where a tray can be parked, which empty tray is nearest, and where every AGV can hide. It gets them from single-agent searches in the `motion_planner` package, the same package as CHUGG. They plan for one AGV or tray at a time on a fixed snapshot of the garage and ignore everyone else's timing. The searches, their shared engine `SingleSourceSearch` and the static filters they read are explained with figures in [section 7](#mp-single-agent-searches):

| Search                                                                                      | Used in task planning by                                                                                                                                               | Explained in                            |
|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| `SingleSourceSearch`, the engine                                                            | Every search below                                                                                                                                                     | [section 7.2](#mp-single-source-search) |
| `BuildStaticObstacleFilter`, `BuildKeepOutFilters` and `GraphFilterProperties`              | Every search below; `ctx->keep_out_filter_by_footprint`                                                                                                                | [section 7.3](#mp-static-filters)       |
| `BlockingTraySearchEnvironment`, `OpenSpaceSearchEnvironment`, `EmptyTraySearchEnvironment` | `AssignTrays`, `FindDestinationForRootTray`, `FindBlockingTrayResolution`, `AssignEmptyTrayToMove`                                                                     | [section 7.4](#mp-tray-searches)        |
| `FindPosePath` and `ConvertPosePathToTrajectory`                                            | `ComputeTravelDuration`, `ValidateMoveDestinationAndPath`, `ScheduleAgvMoveToPickup`, `OrderAgvMoveAfterBlockerDeparture`, `StorePreferredPayloadHeadingsForRetrieval` | [section 7.5](#mp-pose-path)            |
| `FindAgvUnderTrayAssignment`                                                                | `ExpandCleanGarageJob`                                                                                                                                                 | [section 7.6](#mp-hide-agvs)            |

CHUGG itself, and the edge-duration and heuristic tables it is built with (`ComputeEdgeDurations`, `ComputeAllPairsShortestPathCosts`), are in the Motion planning tab ([section 2](#bg-chugg-the-motion-planner)).

This split matters for the refactor: tray and AGV assignment choose destinations and agents with single-agent costs that ignore waiting, and only CHUGG discovers the waiting. An assignment that looks cheap can therefore produce a slow plan.

## Job expansion: from jobs to events

**Job expansion** is the first planning stage inside `Plan()`. It turns each line of the request ("retrieve this car", "move this tray") into a handful of `ScheduleEvent` objects in `ctx->event_dag`, connected by dependency edges. The code is in `job_expansion.cpp`, one `Expand<Type>Job` method per job type. It decides **what** has to happen and **in which order**. It does not decide **how** (no paths, no timing) or **by whom** (no AGV is chosen, except in one case).

A useful picture: each job method is a recipe. It writes a few cards (events) onto a shared board (the event DAG) and ties strings (edges) between cards that must happen one after another. Later stages fill in the blanks on the cards and add more cards and strings.

This section is long because every job type has its own recipe. Read it in this order:

| Part                                                                                                                          | What you learn                                                                                |
|-------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| [14.1](#bg-what-a-job-is)–[14.3](#bg-the-shape-of-every-job-method)                                                           | What a job is, the loop in `Plan()` that dispatches it, and the shape every job method shares |
| [14.4](#bg-every-job-sees-the-garage-through-working_state)–[14.5](#bg-where-the-edges-come-from)                             | How a job method sees the garage (`working_state`) and the three helpers that add edges       |
| [14.6](#bg-job-methods-are-built-from-a-few-shared-pieces)                                                                    | Which job methods are built from which others                                                 |
| [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob)–[14.17](#bg-type_rebalance_garage--planrebalancegaragejob) | Every job type, one at a time, each with a 2D garage example                                  |
| [14.18](#bg-gotchas-2)–[14.19](#bg-cheat-sheet-and-self-check)                                                                | Gotchas, a one-page cheat sheet and questions to check yourself                               |

### How to read the job figures

Sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) each have one figure with the same four parts:

1.  **The map** is the Pecos layout, showing the garage as the job method sees it when it starts (`working_state`). Trays, cars and AGVs are hypothetical. **Curved dashed arrows are intent, not routes**: job expansion plans no paths. A `?` bubble means the destination is left empty for `AssignTrays()` to fill. Numbered circles match the event numbers.
2.  **The request card** lists the `SchedulerJob` fields the method reads, the `job_index` it receives and the exact call `Plan()` makes.
3.  **The event column** lists the events the method appends, numbered in creation order. Every arrow is an edge the method adds, drawn in the style of the helper that added it ([14.5](#bg-where-the-edges-come-from)): solid for `ChainAfterLastEntityEvent`, coloured by the asset it chains; dashed for `OrderAfterJobLeafEvents`; dotted for `OrderAfterBayAndChargerEvents`.
4.  **The step table** is the method body as numbered steps, with what happens in this example and the result: `adds n` means event *n* is created, `skipped` means the branch does not apply, red means the job fails there.

### What a job is

A job is one `interfaces/msg/SchedulerJob` message (C++ type `interfaces::msg::SchedulerJob`) in `request_data.pending_jobs`. Which side writes each field, and which arguments each job type reads, is laid out in the Background tab ([section 6.4](#bg-schedulerjob-what-to-do-and-what-happened)). Job expansion needs only `type`, which picks the job method, and the arguments of that type, which become the method's parameters. Each job figure below repeats the fields its method reads in its request card.

On the way out, each job becomes an `interfaces::msg::ScheduledJobData`: the original job plus `node_indices`, the positions of its action nodes in the response schedule. A failed job is a `ScheduledJobData` built by `MakeFailedJob(job, message, is_retryable)`, with `job.state = STATE_ERROR`, `job.note = <message>` and `job.retain_job = is_retryable`, set when Dispatch should keep it and retry.

### The loop in `Plan()`

This section follows the loop in `Plan()` that offers each pending job to its job method, one job at a time. It covers where the loop sits within one `Plan()` call, how every event is tagged with the `job_index` of the job that created it, and why the loop is built this way.

#### What the code does, in order

Job expansion is step 3 of the nine steps of one `Plan()` call (Background, [section 10](#bg-one-plan-call-step-by-step)). By the time it runs, `initial_state` exists, everything the running schedule uses is reserved (`ExcludeCommittedResources`), and `ctx->keep_out_filter_by_footprint` is built by `BuildKeepOutFilters`; after it, all successful jobs are planned together by tray assignment, AGV assignment, the sanity check and motion planning. Each job method writes its events **directly into** `ctx->event_dag` (it does not return them) and returns only success or a `JobFailure`.

The loop itself is in [section 10](#bg-one-plan-call-step-by-step) (`scheduler.cpp:159`). Three details of it matter here. `ExpandJob(ctx, job)` (`scheduler.cpp:251`) switches on `job.type` and calls the job method with `ctx->scheduled_jobs.size()` as its `job_index`. The job is appended to `scheduled_jobs` (`AddScheduledJob`) only if the method succeeds. And before each job, `Plan()` copies `*ctx`; if the job fails, it restores that copy, so **a failed job leaves no events behind**, and reports the job once through `MakeFailedJob`:

``` cpp
// Scheduler::Plan(), scheduler.cpp:159. ctx is a PlanContextSPtr (std::shared_ptr<PlanContext>).
for(const interfaces::msg::SchedulerJob& job : request_data.pending_jobs) {
  // The copy shares the event objects: expansion never changes an existing event.
  const auto context_before_job = *ctx;
  if(const auto expansion = ExpandJob(ctx, job)) {   // job_index = ctx->scheduled_jobs.size()
    ctx->AddScheduledJob(job);
  }
  else {
    *ctx = context_before_job;                       // drop everything the failed job added
    const auto& [message, is_retryable] = expansion.error();
    response.scheduled_jobs.push_back(MakeFailedJob(job, message, is_retryable));
    if(job.type == interfaces::msg::SchedulerJob::TYPE_INSERT && clean_garage_request_fn_) {
      clean_garage_request_fn_();
    }
  }
}
```

#### How `job_index` works

**One job almost always creates several events.** A RETRIEVE creates up to five (stop charging, open the bay, move the tray already in the bay out, move the car's tray in, hand the car over); a REPARK_TRAY creates one (two if the tray must first stop charging); a REBALANCE_GARAGE creates a few per bay it switches. Every one of them belongs to the same job. Sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) list what each job type creates.

So every event needs to remember which job it belongs to, and the response needs to say "this action is part of job X". The code does not store the job's `guid` in the event. Each event is constructed with a small integer, the `job_index`, and the job is looked up from it at the end:

``` cpp
// inside ExpandRetrieveJob(PlanContextSPtr ctx, const interfaces::msg::Guid& payload_id, size_t job_index)
const auto transition = std::make_shared<BayTransition>(job_index, planned_bay, command);  // tagged with job_index
...
ExpandReparkTrayJob(ctx, payload.tray_id, job_index, false, payload_tray_dest);  // its TrayMove: same tag
...
const auto bay_transition = std::make_shared<BayTransition>(job_index, planned_bay,
    MakeBayCommand(interfaces::msg::BayCommand::COMMAND_TYPE_PROCESS_RETRIEVE, kBayProcessPlaceholderId));
                                                                                  // same tag again
```

The relationship is **one job → many events → many actions**:

| Level   | How many                                                                     | How it points to the job                                                                                                                                                                                                                                       |
|---------|------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Job     | one entry in `ctx->scheduled_jobs`                                           | its position in that list is the `job_index`                                                                                                                                                                                                                   |
| Events  | all events the job method creates, **plus** the ones later stages add for it | `event->GetJobIndex()`. Tray assignment builds blocker moves as `MakeTrayMove(move->GetJobIndex(), ...)` and AGV assignment builds approach moves as `MakeAgvPoseMove(root_event->GetJobIndex(), ...)`, so they inherit the index of the move that needed them |
| Actions | one `ActionNode` per motion of those events                                  | `job_id` = the job's `guid`; the job's `node_indices` list their positions                                                                                                                                                                                     |

- **What the number is.** `job_index` is the job's position in `ctx->scheduled_jobs`, the list of jobs that have **succeeded so far**. It is not the loop counter (the job's position in `request_data.pending_jobs`).
- **How it is chosen.** Just before calling the job method, `ExpandJob()` reads `ctx->scheduled_jobs.size()` and passes it on. If the method succeeds, `AddScheduledJob(job)` appends the job at exactly that position, so `scheduled_jobs[job_index]` is now this job. If it fails, nothing is appended, the context is restored, and the next job is offered the same number.
- **How it is used.** When the response is built, `ToActionNode(motion, ctx->scheduled_jobs[event->GetJobIndex()].job.guid, *event)` (`action_graph.cpp`) turns the index back into the job's `guid`. `OrderAfterJobLeafEvents` ([14.5](#bg-where-the-edges-come-from)) also compares indices to decide which events belong to the same job.

A worked example, the same one as in [Figure 27](#bg-fig-36_expansion_loop) below:

| Loop counter `i` | Job in the request    | `scheduled_jobs.size()` before the call = `job_index` | Result                                   | `scheduled_jobs` afterwards |
|------------------|-----------------------|-------------------------------------------------------|------------------------------------------|-----------------------------|
| 0                | RETRIEVE car on T17   | 0                                                     | success: one job, 4 events, all tagged 0 | `[RETRIEVE]`                |
| 1                | INSERT bay B7         | 1                                                     | fails, no events added                   | `[RETRIEVE]` (unchanged)    |
| 2                | REPARK_TRAY T19 → P24 | 1                                                     | success: one job, 1 event, tagged 1      | `[RETRIEVE, REPARK_TRAY]`   |

If the code used `i` instead, the REPARK's event would carry 2, and `scheduled_jobs[2]` would not exist.

![The expansion loop](figures/36_expansion_loop.svg)

The loop, one row per iteration: the code that runs, then `ctx->scheduled_jobs`, `ctx->event_dag` and `response.scheduled_jobs` after it. Step through the loop: each iteration first computes `job_index = scheduled_jobs.size()` and calls the job method, then appends the job (or, on failure, restores the context and pushes a `MakeFailedJob` result into the response). In the events column each box is one event and each dashed group is everything one job-method call created: the RETRIEVE (job index 0) created four events, the REPARK_TRAY (job index 1) one, and the failed INSERT none, which is why the REPARK also gets index 1. The last steps follow the same index through later stages to the response.

If every job fails, `ctx->scheduled_jobs` is empty and `Plan()` returns right after the loop with "No jobs succeeded to plan".

#### Why it is built this way

The code has no design document, so this is a reading of the structure, with the trade-offs it implies.

- **`Plan()` is a pure function of the request.** Nothing survives between calls except the fixed layout, graph and collision table. Dispatch owns the job queue and the live garage state and sends both every time. That keeps the scheduler simple to test (build a request, call `Plan()`, inspect the response) and lets Dispatch replan whenever something changes.
- **Jobs are expanded one at a time, in request order, each seeing the garage that earlier jobs leave behind** ([14.4](#bg-every-job-sees-the-garage-through-working_state)). That is a greedy approach: easy to reason about, and later jobs automatically build on earlier ones (a second move of the same tray starts where the first one ends). The cost is that request order matters and nothing tries another order: an early job can make a later one fail, and the later one is simply reported as failed.
- **Failure is per job during expansion.** One bad job does not sink the others, so Dispatch still gets a plan for everything that was possible. `retain_job` lets RETRIEVE say "try me again later" when no bay is free.
- **After expansion, everything is one problem.** All successful jobs share one DAG, so tray assignment, AGV assignment and motion planning can share AGVs and resolve conflicts across jobs. The flip side is in [section 10](#bg-one-plan-call-step-by-step): if any later stage fails, `fail_all_jobs` fails every job in `ctx->scheduled_jobs`, that is every job that expanded.
- **A small integer instead of a pointer or `guid`.** Events are `planner_core` objects that know nothing about ROS messages. A `size_t` is the cheapest way to tag them and is enough for the "same job?" test in `OrderAfterJobLeafEvents`.

Known issues with this design (details in [14.18](#bg-gotchas-2)):

- **No rollback (fixed).** A job method that failed after adding events used to leave them in the DAG, under an index the next successful job reused. Fixed in PR \#1018: `Plan()` restores the context copied before the job, so a failed job leaves no events (test `RetrieveJob.FailedJobLeavesNoEvents`).
- **Index reuse makes logs confusing.** "Job index 1" means different requests at different moments of one `Plan()` call.
- **Order dependence without a retry.** The plan depends on the order Dispatch lists the jobs, and a failed job is not retried after the others are placed.
- **Duplicate failures (fixed).** When a later stage failed, `Plan()` used to fail every job in `pending_jobs`, including jobs already reported failed by the loop. Fixed in PR \#1018: a later stage fails only `ctx->scheduled_jobs`, so each job is reported once (test `RetrieveJob.FailedJobReportedOnce`).

Possible directions (ideas, not plans): tag events with the job's `guid` instead of a position, or plan each job into a separate small DAG and merge it only on success. The snapshot-and-restore that this list used to suggest is what `Plan()` now does: it copies the whole `PlanContext` (the copy shares the event objects, which expansion never changes) and assigns it back on failure.

### The shape of every job method

All job methods are `const` members of `volley::scheduler::Scheduler`, declared private in `scheduler.hpp` and defined in `job_expansion.cpp`, with the same skeleton. Here it is, assembled from `ExpandBayTransitionJob` and `ExpandInsertJob`, with the types spelled out:

``` cpp
// Shape of stdx::Expected<void, JobFailure> Scheduler::Expand<Type>Job(PlanContextSPtr ctx, <job fields>,
//                                                                     size_t job_index) const
// this : const Scheduler*  (reads layout_, motion_graph_, collision_table_, cost_model_; changes nothing in itself)
// ctx  : the same PlanContextSPtr as ctx in Plan(); the method edits *ctx

// (1) See the garage as all earlier events leave it ("Every job sees the garage ...").
//     ComputeStateAfterPlannedEvents copies ctx->initial_state and replays the whole DAG (ApplyEventsTo).
auto working_state_or = ComputeStateAfterPlannedEvents(*ctx);
if(!working_state_or) {
  return Fail("Failed to apply the planned events: {}", working_state_or.error());
}
auto working_state = std::move(*working_state_or);

// (2) Look up what the job names. Lookups return std::optional<interfaces::msg::...>
auto bay_opt = working_state.GetBay(bay_id);

// (3) Check preconditions; return early with a JobFailure if one fails (Fail formats with std::format)
if(!bay_opt.has_value()) {
  return Fail("Requested to transition {} but bay does not exist in discrete state.", bay_name);
}

// (4) Create events. Fill in what is known now; leave the rest empty for later stages
const auto bay_transition = std::make_shared<BayTransition>(
    job_index, *bay_opt, MakeBayCommand(command_type, kBayTransitionPlaceholderId, target_floor));

// (5) Add each event and wire its edges ("Where the edges come from")
ctx->AddChainedEvent(bay_transition);          // add it, then ChainAfterLastEntityEvent
ctx->OrderAfterJobLeafEvents(bay_transition);  // wait for the job's current leaves

// (6) Or delegate part of the work to another job method, passing the SAME job_index
if(const auto tray_repark = ExpandReparkTrayJob(ctx, tray.id, job_index, true); !tray_repark) {
  return stdx::Unexpected(tray_repark.error());
}

return {};
```

A failure is a `JobFailure {message, is_retryable}` (`job_failure.hpp`); `Fail(...)` builds one with `is_retryable = false`, and only `ExpandRetrieveJob` sets it to `true`. Every expansion is `[[nodiscard]]`, so a caller cannot drop a nested failure by accident.

What the four event types can carry at creation time:

| Event (`planner_core`) | Constructed with                                                                                                                                                                                      | Can be left empty for later                         |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| `TrayMove`             | `job_index` only; then `SetTrayId(id)`, `SetDest(pose)`, and rarely `SetAgvId(id)`. `MakeTrayMove(job_index, tray_id, dest, agv_id)` (`move_events.hpp`) does all four, setting only the fields given | tray id (`? -> B21`), destination (`T21 -> ?`), AGV |
| `AgvMove`              | `job_index`, an `interfaces::msg::AgvPoseChanged` (built by `MakeAgvPoseMove(job_index, agv_id, source, destination)`) or an `AgvLiftChanged`                                                         | nothing                                             |
| `BayTransition`        | `job_index`, the bay's `DiscreteBayState`, a `BayCommand` (built by the file-local `MakeBayCommand`)                                                                                                  | nothing                                             |
| `VecsTransition`       | `job_index`, a `VecsStateChanged` (current and next state, built by the file-local `MakeVecsStateChange`)                                                                                             | nothing                                             |

Only `TrayMove` has blanks. That is why the next stage is called *tray* assignment: it fills the blanks on `TrayMove`s, and [section 16](#bg-tray-assignment-dotrayassignments) explains how.

#### What a job method reads, changes and returns

The signatures make job methods look like functions that take a job and return a yes/no answer. They are not. Most of their output is written **into `*ctx` while they run**, and the return value only reports whether that worked. [Figure 28](#bg-fig-38_job_method_dataflow) shows this for `ExpandRetrieveJob`; every `Expand<Type>Job` follows the same pattern.

![What ExpandRetrieveJob reads, changes and returns](figures/38_job_method_dataflow.svg)

Data flow of one job method. Step through one call: blue, read-only inputs come in; grey, a local copy is built and thrown away at return; amber, members of the shared `PlanContext` that the method (and the job methods it calls) change in place: four new events, five edges and three `last_event_by_entity` entries; green, the return value, which only reports success or a `JobFailure`. Red: requests sent to Dispatch while planning. The last step sketches a pure alternative.

The same information as a table, for `ExpandRetrieveJob(ctx, payload_id, job_index)` called as the first job:

| Item                                                          | Passed as                          | Read | Changed    | What happens                                                                                                                                                                                                       |
|---------------------------------------------------------------|------------------------------------|------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `*this` (`layout_`, `motion_graph_`, `collision_table_`, ...) | implicit, `const` method           | yes  | no         | layout facts and graph lookups                                                                                                                                                                                     |
| `payload_id`                                                  | `const interfaces::msg::Guid&`     | yes  | no         | which car                                                                                                                                                                                                          |
| `job_index`                                                   | `size_t` by value                  | yes  | no         | stored in every new event                                                                                                                                                                                          |
| `ctx`                                                         | `PlanContextSPtr` **by value**     |      |            | copying a `shared_ptr` copies the pointer, not the context: caller and callee share one `PlanContext`                                                                                                              |
| `ctx->initial_state`                                          | through `ctx`                      | yes  | no         | copied into `working_state`                                                                                                                                                                                        |
| `ctx->event_dag`                                              | through `ctx`                      | yes  | **yes**    | replayed, then 4 events and 5 edges added (2 of the events by nested `ExpandReparkTrayJob` calls)                                                                                                                  |
| `ctx->last_event_by_entity`                                   | through `ctx`                      | yes  | **yes**    | `ChainAfterLastEntityEvent` reads and updates it: B21 → e4, T21 → e2, T17 → e3                                                                                                                                     |
| `ctx->keep_out_filter_by_footprint`                           | through `ctx`                      | yes  | no         | read through `ctx->FindKeepOutFilter(collision_id)`, which fails the job if the footprint has no filter. Before PR \#1018 it was read with `operator[]`, which inserted an empty filter for a missing collision id |
| `ctx->scheduled_jobs`                                         | through `ctx`                      | no   | no         | `Plan()` appends the job **after** a successful return                                                                                                                                                             |
| `working_state`, `bay_opt`, ...                               | locals                             |      | local only | `bay_opt->state = READY_TO_RETRIEVE` changes the local copy, not the garage                                                                                                                                        |
| return value                                                  | `stdx::Expected<void, JobFailure>` |      |            | nothing on success; on failure a `JobFailure` with `message` and `is_retryable` (which becomes `retain_job`)                                                                                                       |

Two more effects are easy to miss:

- **`const` does not mean "no changes".** A `const` member function cannot change the `Scheduler`'s own members, but `ctx` points to a separate, non-`const` object, so the method can change it freely ([section 9](#bg-objects-ownership-and-lifetimes)).
- **Some job methods talk to Dispatch.** `ExpandInsertJob` calls `reset_bay_state_request_fn_`, which `SchedulerRos` wired to an asynchronous ROS service request (`TransitionBayToInsert`). It is sent during expansion, before anyone knows whether the whole plan will succeed, and restoring the context after a failed job cannot take it back. `Plan()` itself calls `clean_garage_request_fn_()` when an INSERT fails.

#### Assessment of the design

This is a common C++ style with real reasons behind it, but it makes the code harder to follow, and it is the root of several gotchas in [15.18](#bg-gotchas-2). A fair summary:

**Why it was probably written this way**

- **One growing structure is convenient.** Every step needs the latest DAG and the latest `last_event_by_entity`. Passing one context pointer around is less code than threading inputs and results through every call.
- **Composition is free.** When `ExpandRetrieveJob` calls `ExpandReparkTrayJob`, the inner method simply appends to the same DAG, and its events immediately count as the outer job's leaves for `OrderAfterJobLeafEvents`. With pure functions, the caller has to merge the inner result itself.
- **The later stages really are graph rewrites.** Tray and AGV assignment fill in fields of existing events, add events and add edges across all jobs. In-place editing is natural there, and job expansion uses the same style for consistency.
- **Events are shared objects** (`std::shared_ptr`). Producing a modified copy of a DAG would need deep copies, so mutation is the cheap option. (The refactor proposal, sections [6.1](#pr-the-new-pieces-and-how-they-fit-together) and [6.5](#pr-why-return-a-result-and-how-it-is-applied), show a middle way for tray assignment: return an ordered log of edits and let one function apply it.)

**What it costs**

- **The signature hides the output.** Nothing in `stdx::Expected<void, JobFailure> ExpandRetrieveJob(PlanContextSPtr, const interfaces::msg::Guid&, size_t)` says "adds events and edges". You have to read the body, and the bodies of everything it calls.
- **No transaction inside a job.** A method that fails halfway leaves its partial changes in `*ctx`. Since PR \#1018 `Plan()` wraps every job in a copy-and-restore of the whole context ([14.18](#bg-gotchas-2), gotcha 1), but a nested failure that the outer method only logs, such as one bay of a REBALANCE_GARAGE, still keeps its partial events. A pure function that returns its events would make "discard on failure" automatic at every level.
- **Hidden dependencies between calls.** `OrderAfterJobLeafEvents` looks at the *current* leaves of the whole DAG, and `ChainAfterLastEntityEvent` at the *current* `last_event_by_entity`. The result of a call therefore depends on everything that ran before it, not only on its arguments.
- **Harder to test.** A test has to build a `PlanContext`, call the method, then inspect the context (see the [Verification](#doc-verification) tab). It cannot simply compare a returned value.
- **Effects leave the process.** A callback to Dispatch from inside planning cannot be undone if the plan later fails.

**A purer alternative** (sketched in the figure; not in the code): give each job method a read-only view (`const` working state, DAG, last-entity map) and have it **return** a `JobPlan`: its new events, the edges it wants (with the helper that justified each), and any follow-up requests for Dispatch. `Plan()` then commits a successful `JobPlan` into the context in one place, or drops it on failure. That makes the output visible, makes rollback automatic, and lets a test compare `JobPlan` values directly. The costs are some boilerplate and a `Commit()` step that calls the three edge helpers centrally. Two middle grounds are cheaper:

- keep mutation but pass exactly what is changed (`ScheduleEventDag& event_dag, LastEntityMap& last`) instead of the whole context, so the signature tells the truth;
- keep the current code but snapshot the context before each job and restore it on failure. `Plan()` does this since PR \#1018.

The refactor proposal makes the same trade-off for the tray and AGV solvers: it keeps in-place mutation for the first behaviour-preserving step and suggests a returned result afterwards.

### Every job sees the garage through `working_state`

Before a job method adds any event, it builds its own view of the garage, `working_state`, so that it plans against the garage as earlier jobs in the same request leave it, not as the request describes it. The figure shows how that view is produced from `ctx->initial_state` and the event DAG built so far; the details that matter in practice follow it.

![Working state replay](figures/23_working_state_replay.svg)

Every `Expand<Type>Job` copies `ctx->initial_state` and replays the whole event DAG built so far (`ComputeStateAfterPlannedEvents`, which calls `ctx.event_dag.ApplyEventsTo(state)`). Step through the three lines of code: after the copy, `working_state` still matches the request; after the replay, tray T15 moves on the `working_state` map from P15 to P23, where job 0 will have put it, so job 1 (a retrieve) no longer sees it at P15 as in the request. Only then does job 1 add its own events.

Three details matter in practice:

- **The replay is discrete.** A tray "teleports" to its destination; time and paths do not exist yet. Blank fields are not neutral ([section 11](#bg-event-types-and-polymorphism)): a `TrayMove` with no tray id does nothing, one with no destination **removes** the tray and its payload from `working_state`, and a tray already sitting on a destination is moved to the placeholder pose `{node_id: 0, heading: 0}`. So a later job does not see an empty tray that READY_FOR_INSERT will bring into a bay, and does not see a tray whose destination is still open.
- **Nested calls replay again.** When `ExpandRetrieveJob` calls `ExpandReparkTrayJob`, the inner call copies and replays too, so it already sees the bay transition the outer method has just added.
- **The cost is repeated replay.** Each job method replays the whole DAG, and nested calls replay it again. The code accepts this for simplicity. A replay that fails ends the job with "Failed to apply the planned events: …".

### Where the edges come from

Job methods add not only events but also the edges between them, and those edges decide which events must finish before others may start. During job expansion every edge comes from one of three helpers: `ChainAfterLastEntityEvent`, `OrderAfterJobLeafEvents` and `OrderAfterBayAndChargerEvents`. The figure shows them at work on five events; the definition of each follows it.

![Edge helpers during job expansion](figures/25_dependency_rules.svg)

The three edge helpers used during job expansion. Step through the five events in the order they are created to see which helper adds each edge, and how `last_event_by_entity` and the leaf set change. Solid edges come from `ChainAfterLastEntityEvent` (usually through `AddChainedEvent`), which chains events on the same garage asset (AGV, tray, bay or VECS), even across jobs; the colour is the asset. Dashed edges come from `OrderAfterJobLeafEvents`, which makes a new event wait for the current leaf events of the **same** job. Dotted edges come from `OrderAfterBayAndChargerEvents` (called from `ExpandReparkTrayJob`), which makes a tray move into a bay or VECS wait for that resource's last event.

The three helpers, in one sentence each, then how the code applies them. A **garage asset** is anything an event acts on and that only one event can use at a time: an AGV, a tray, a bay or a VECS. Where each one lives and why it is needed are [listed below](#bg-does-the-code-really-call-them-rule-a-rule-b-and-rule-c).

- **`ChainAfterLastEntityEvent` — one asset, one event at a time, across jobs.** Each new event waits for the previous event on the same garage asset, whichever job created it. The code keeps `ctx->last_event_by_entity`, a map from each asset (`interfaces::msg::GarageEntityId`) to the last event that used it. `ChainAfterLastEntityEvent(id, e)` adds the edge `last[id] -> e` if there is one, then sets `last[id] = e`; `AddChainedEvent(e)` adds `e` to the DAG and calls it with `e`'s own asset. With `OrderAfterBayAndChargerEvents`, it is the only helper that links **different jobs**: if job 0 and job 1 both move tray T19, job 1's move waits for job 0's.
- **`OrderAfterJobLeafEvents` — steps of one job in order.** Each new event of a job waits for the job's open ends: its earlier events that nothing else waits for yet. In DAG terms these are the job's *leaves*, events with no outgoing edge. `OrderAfterJobLeafEvents(e)` adds `leaf -> e` for every leaf other than `e` whose `GetJobIndex()` equals `e->GetJobIndex()`. It never links different jobs.
- **`OrderAfterBayAndChargerEvents` — a tray enters a bay or VECS only after that asset's latest event.** When a `TrayMove`'s destination is a bay or a VECS, it waits for the last event on that bay or VECS, so a tray never enters a bay before the bay's transition. Only `ExpandReparkTrayJob` calls it; it reads `last_event_by_entity` but does not update it.

Not every event goes through every helper, and a few are chained twice or late:

- **Without `ChainAfterLastEntityEvent`:** a `TrayMove` with no tray yet (its tray is unknown; `AddChainedEvent` only adds it), and the `TrayMove` that MOVE_AGV creates for a loaded AGV is chained by tray only, not by AGV. The "stop charging" `VecsTransition` in RETRIEVE and REPARK used to skip it too; since PR \#1018 it is chained after the charger's previous event.
- **Chained after a second asset:** in `ExpandCleanGarageJob` (`job_expansion.cpp:536`) a hide `AgvMove` that ends on a bay node is also chained after that bay's last event, `ctx->ChainAfterLastEntityEvent(BayId(dest.node_id), agv_move)`, so a later transition of that bay waits for the AGV to arrive.
- **Chained once the tray is known:** a READY_FOR_INSERT fill move has no tray when it is created, so `AddChainedEvent` only adds it, and once `AssignEmptyTrayToMove` picks the tray, `AssignTraysToBayFillMoves` chains it after that tray's last event with `ctx->ChainAfterLastEntityEvent(move->GetGarageEntityId().value(), event)` (`job_expansion.cpp:804`); a move it cannot fill is left for `AssignTrays`.
- **Without `OrderAfterJobLeafEvents`:** the "stop charging" `VecsTransition`; RETRIEVE's `TRANSITION_TO_RETRIEVE` (so it does not wait for that stop-charging event); CHARGE_AGV's transition that frees a trapped AGV; and CLEAN_GARAGE's hide `AgvMove`s. Each of these is either the first event of its job or deliberately independent, but later events of the same job still wait for them through it. And none of the helpers knows about geometry: whether tray T15 is *in the way* of T17's path, or whether two AGVs would meet, is discovered and turned into edges by tray and AGV assignment (sections [16](#bg-tray-assignment-dotrayassignments) and [17](#bg-agv-assignment-doagvassignments)).

#### The three edge helpers in the code

Each helper is one function. Where to find it, what it does, and why the edge is there:

| Helper                                         | Signature and file                                                                                                                                                                                               | What it does, and why                                                                                                                                                                                                                                                                  |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ChainAfterLastEntityEvent`, `AddChainedEvent` | `PlanContext::ChainAfterLastEntityEvent(entity, event)` in `plan_context.hpp`, with the map `last_event_by_entity`; `PlanContext::AddChainedEvent(event)` adds the event and calls it with the event's own asset | Adds an edge from the last event on the asset to the new event, then records the new event as the asset's last. An asset can only do one thing at a time, and the next event must start from the state the previous one leaves.                                                        |
| `OrderAfterJobLeafEvents`                      | `PlanContext::OrderAfterJobLeafEvents(event)` in `plan_context.hpp`                                                                                                                                              | Adds an edge from every current leaf of the same job to the new event. A job's steps form a recipe (switch the bay, bring the tray, hand over the car) that must run in the order the job method creates them.                                                                         |
| `OrderAfterBayAndChargerEvents`                | `OrderAfterBayAndChargerEvents(ctx, working_state, dest, tray_move)`, a file-local function in `job_expansion.cpp` that only `Scheduler::ExpandReparkTrayJob` calls                                              | Adds an edge from the last event on the destination bay or VECS to the tray move. A bay must finish its current transition or retrieve before a tray enters it; `ChainAfterLastEntityEvent` does not cover this, because a tray move is chained to its tray, not to the bay it enters. |

**Why each one is needed**, by what would go wrong without it:

- **Without `ChainAfterLastEntityEvent`**, two jobs that touch the same tray, AGV, bay or VECS would be unordered. If job 0 moves T19 from P19 to P24 and job 1 moves it from P24 to P23, nothing would stop the replay, or the robots, from doing job 1's move first, starting from a place the tray is not at yet.
- **Without `OrderAfterJobLeafEvents`**, the steps inside one job would be unordered: the car's tray could be planned into B21 before the bay switches to retrieve mode, or `PROCESS_RETRIEVE` could run before the tray arrives.
- **Without `OrderAfterBayAndChargerEvents`**, a tray could enter a bay before an *earlier job's* bay event finished. `OrderAfterJobLeafEvents` does not help across jobs, and `ChainAfterLastEntityEvent` does not either, because a `TrayMove` is chained to its tray, not to the bay it enters. For example, a READY_FOR_INSERT job bringing an empty tray into B21 must wait for the previous job's `PROCESS_RETRIEVE` on B21; only `OrderAfterBayAndChargerEvents` adds that edge.

The three helpers are not the whole story. They only order what the job methods know about. Geometric conflicts (a tray in the way, two AGVs on one node) are turned into edges later by tray and AGV assignment (sections [16](#bg-tray-assignment-dotrayassignments) and [17](#bg-agv-assignment-doagvassignments)).

### Job methods are built from a few shared pieces

The job methods in sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) are not independent of each other: several create their events by calling other job methods or a few shared helpers. This structure explains the order of those sections and why `ExpandReparkTrayJob` is described first.

![Job building blocks](figures/37_job_building_blocks.svg)

Generated from the job-expansion code: which methods each job method calls, which event types it creates itself, and which edge helpers it calls itself (`AddChainedEvent` or `ChainAfterLastEntityEvent`, `OrderAfterJobLeafEvents`, `OrderAfterBayAndChargerEvents`). `AddBayTransitionToRetrieve` and `ReparkWaypointStashedTrays` are helpers, not job types. Step through it one column group at a time; the last step marks the `ExpandReparkTrayJob` column, the workhorse that six other methods create their `TrayMove`s through.

Two patterns stand out:

- **`ExpandReparkTrayJob` is the workhorse.** Six methods create their `TrayMove`s through it, so the heading policy, the VECS checks and the call to `OrderAfterBayAndChargerEvents` live in one place. That is why it is explained first ([14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob)).
- **Composite jobs pass their own `job_index` down.** When `ExpandRetrieveJob` calls `ExpandReparkTrayJob(ctx, tray, job_index, ...)`, the inner events belong to the retrieve job. `OrderAfterJobLeafEvents` then orders them with the retrieve's other events, and the response reports them as part of the retrieve.

The order of [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) follows that structure: the building blocks first, then the jobs made from them.

### `TYPE_REPARK_TRAY` and `TYPE_MOVE_TRAY` — `ExpandReparkTrayJob`

`ExpandReparkTrayJob` moves one tray to one destination. `ExpandJob()` calls it for `TYPE_REPARK_TRAY` and `TYPE_MOVE_TRAY` jobs, and five other job methods and the helper `ReparkWaypointStashedTrays` call it whenever they need a `TrayMove`, so the destination heading, the VECS checks and the call to `OrderAfterBayAndChargerEvents` are decided here for all of them.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:247
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandReparkTrayJob(PlanContextSPtr ctx,
    std::optional<uint16_t> tray_id, size_t job_index, bool is_reciprocal_heading_allowed,
    std::optional<interfaces::msg::GaragePose> dest = std::nullopt) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name                            | Type                                                                  | Meaning                                                                                                                                                                                                                       | In the example below                                            |
|------------------|---------------------------------|-----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| in               | `this`                          | `const Scheduler*`                                                    | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                  | Pecos layout                                                    |
| in / **changed** | `ctx`                           | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`)                    | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+1 `TrayMove`, maybe a stop-charging `VecsTransition`) and `last_event_by_entity` | job 0 adds T19: P19 → P24                                       |
| in               | `tray_id`                       | `std::optional<uint16_t>`                                             | Tray to move; `std::nullopt` means "any empty tray" (only from internal callers)                                                                                                                                              | `19`                                                            |
| in               | `job_index`                     | `size_t` (by value)                                                   | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                    | `0` and `1`                                                     |
| in               | `is_reciprocal_heading_allowed` | `bool`                                                                | Allow keeping the tray's current heading when the requested one is the same or opposite (parking nodes only)                                                                                                                  | `true` (job 0), `false` (job 1)                                 |
| in               | `dest`                          | `std::optional<interfaces::msg::GaragePose>` (default `std::nullopt`) | Target node and heading; empty means "anywhere, chosen by tray assignment". Always set when called from `ExpandJob()`                                                                                                         | `{node_id: 24, heading: 90}`, then `{node_id: 23, heading: 90}` |
| out              | return                          | `stdx::Expected<void, JobFailure>`                                    | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                        | success for both                                                |

**When Dispatch sends it:** to move a specific tray to a specific node (an operator request, or Dispatch tidying up). Both job types call the same method with `job.tray_id`, `job.allow_reciprocal` and `job.destination`.

![Repark tray job](figures/41_job_repark_tray.svg)

Two jobs move tray T19: P19 → P24, then P24 → P23. `ChainAfterLastEntityEvent` (through `AddChainedEvent`) chains the second move after the first. The last three steps play the plan with an illustrative AGV-1: it drives under T19, carries it to `P24` (1), and then on to `P23` (2).

In words: create one `TrayMove` with `MakeTrayMove(job_index, tray_id, dest)`, its destination (if given) turned to the right heading and checked by `CheckReparkDestination`, and add it with `AddChainedEvent`, then `OrderAfterBayAndChargerEvents` (when there is a destination) and `OrderAfterJobLeafEvents`. Things to remember:

- **Either argument may be missing, not both.** Internal callers use `dest = std::nullopt` ("move this tray out of the way, anywhere") or `tray_id = std::nullopt` ("bring any empty tray here"). From `ExpandJob()` both are always present.
- **The tray is looked up in `working_state`**, the garage after the planned events. Only when an earlier move without a destination has taken the tray out of the planned state does it fall back to `ctx->initial_state`. Before PR \#1018 it always read `ctx->initial_state` ([15.18](#bg-gotchas-2), gotcha 2). A tray on a charging VECS first gets a "stop charging" `VecsTransition` (`AddChargingStopBeforeTrayMove`).
- **Heading policy, in three steps**, for a known tray with a destination. The preferred heading is `FindPreferredTrayHeadingForRetrieval(dest->node_id, payload_opt)`: the node's *retrieval heading* (the heading that makes a later retrieve fastest), reversed if the car sits backwards on the tray, or nothing for an empty tray or a node without one. First, only for a plain parking destination (`IsParkingWithoutBayOrCharger`) with `is_reciprocal_heading_allowed`: a loaded tray takes the preferred heading, and an empty tray keeps its current heading if the requested one is the same or opposite (`KeepTrayHeadingIfEquivalent`). Second, a tray already at the resulting pose needs no move: the method returns success and adds no event. Third, for every destination (parking, bay, VECS or waypoint, whatever `is_reciprocal_heading_allowed` says), the preferred heading is applied if there is one. `StorePreferredPayloadHeadingsForRetrieval` records retrieval headings only for parking nodes, at headings the layout allows there, so the third step changes nothing for a bay, VECS or waypoint. The `576_eccles` EV-charging exception that used to run here (heading 0 on nodes 46 and 47) was deleted in PR \#1018.
- **The destination check** (`CheckReparkDestination`) fails the job if the destination VECS is not `READY_TO_CHARGE`, the pose is not in the graph, the keep-out filter disables it, or the bay there is disabled.

### `TYPE_MOVE_AGV` — `ExpandAgvMoveJob`

`ExpandAgvMoveJob` sends one AGV to a given pose. `ExpandJob()` calls it for `TYPE_MOVE_AGV` jobs and `ExpandAgvChargeJob` calls it to drive an AGV to a charger; it checks the AGV and the destination and decides whether the event it adds is an `AgvMove` or, when the AGV already carries a tray, a `TrayMove`.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:101
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandAgvMoveJob(
    PlanContextSPtr ctx, uint16_t agv_id, interfaces::msg::GaragePose dest, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                               | Meaning                                                                                                                                                                                            | In the example below                                                   |
|------------------|-------------|----------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| in               | `this`      | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                       | Pecos layout                                                           |
| in / **changed** | `ctx`       | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+1 `AgvMove` or `TrayMove`) and `last_event_by_entity` | two jobs, one event each                                               |
| in               | `agv_id`    | `uint16_t`                                         | AGV to move; an unknown or disabled AGV fails the job                                                                                                                                              | `A`, `B`                                                               |
| in               | `dest`      | `interfaces::msg::GaragePose` (by value)           | Target pose in AGV heading                                                                                                                                                                         | `{node_id: 13, heading: 90}` (W13), `{node_id: 24, heading: 90}` (P24) |
| in               | `job_index` | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                         | `0`, `1`                                                               |
| out              | return      | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                             | success for both                                                       |

**When Dispatch sends it:** to drive a named AGV somewhere, for example out of the way for maintenance. `ExpandAgvChargeJob` also uses it.

![Move AGV job](figures/40_job_move_agv.svg)

An empty AGV produces an `AgvMove`; an AGV carrying a tray produces a `TrayMove` with that AGV already assigned. Here AGV-1 is sent to `W13` and AGV-2, which carries T9, to `P24`. The last two steps play the plan: AGV-1 drives to `W13`, then AGV-2 carries T9 to `P24` with no approach drive.

In words: check the AGV (it exists and is enabled; an AGV already at `dest` needs no event), work out the destination, check it (the pose is in the graph and the AGV footprint's keep-out filter allows it), then add one event with `AddChainedEvent` and `OrderAfterJobLeafEvents`. For an AGV carrying a tray, `ResolveCarriedTrayDestination` turns `dest` into the tray's pose, taking the node's retrieval heading for a loaded tray when there is one, and the AGV pose that results is what gets checked. Remember that **this is the only job that can create a `TrayMove` with its AGV already set** (`MakeTrayMove(job_index, agv.tray_id, tray_dest, agv_id)`). The reverse-heading parameter that no caller used was deleted in PR \#1018.

### `TYPE_TRANSITION_BAY_TO_INSERT` / `_TO_RETRIEVE` — `ExpandBayTransitionJob`

`ExpandBayTransitionJob` switches one bay between insert mode and retrieve mode. `ExpandJob()` calls it for the two `TYPE_TRANSITION_BAY_TO_*` job types and `ExpandAgvChargeJob` calls it to return a bay to insert mode; it decides whether the bay may be switched at all before it adds a single `BayTransition`.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:671
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandBayTransitionJob(
    PlanContextSPtr ctx, uint16_t bay_id, uint8_t command_type, size_t job_index) const;
    // command_type = interfaces::msg::BayCommand::COMMAND_TYPE_TRANSITION_TO_{INSERT,RETRIEVE}
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name           | Type                                                                            | Meaning                                                                                                                                                                                    | In the example below                                                                        |
|------------------|----------------|---------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| in               | `this`         | `const Scheduler*`                                                              | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                               | Pecos layout                                                                                |
| in / **changed** | `ctx`          | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`)                              | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+1 `BayTransition`) and `last_event_by_entity` | job 0 adds one event; job 1 none                                                            |
| in               | `bay_id`       | `uint16_t`                                                                      | Bay node id                                                                                                                                                                                | `21`, `7`                                                                                   |
| in               | `command_type` | `uint8_t`: `BayCommand::COMMAND_TYPE_TRANSITION_TO_INSERT` or `..._TO_RETRIEVE` | Which mode to switch to; anything else fails                                                                                                                                               | `TO_RETRIEVE`, `TO_INSERT`                                                                  |
| in               | `job_index`    | `size_t` (by value)                                                             | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                 | `0`, `1`                                                                                    |
| out              | return         | `stdx::Expected<void, JobFailure>`                                              | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                     | job 0 success; job 1 fails with "Requested to transition … but the ODP's area is occupied." |

**When Dispatch sends it:** to switch one bay's mode explicitly. Seen from the code, a bay has two working modes: **insert** (`READY_TO_INSERT`: an empty tray is inside and a customer can drive onto it) and **retrieve** (`READY_TO_RETRIEVE`: trays can be planned into and out of the bay, and a car can be handed over with `PROCESS_RETRIEVE`).

![Bay transition job](figures/49_job_bay_transition.svg)

Job 0 switches B21 to retrieve mode. Job 1 is rejected because AGV-3 stands in B7's ODP collision area (extent drawn for illustration). The last step plays the plan: B21's state changes to `READY_TO_RETRIEVE`, and AGV-3 stays where it is.

In words: validate (bay exists, enabled, its `BAY_ODP` area is clear, the bay is in the right starting state), then add one `BayTransition`. The ODP check is `IsBayOdpAreaClear`, a `BuildStaticObstacleFilter` for the `BAY_ODP` footprint at the bay's inbound pose. Retrieve transitions made here and in `AddBayTransitionToRetrieve` carry the bay's first system floor from `GetFirstSystemFloor`, which fails the job if the bay has none; the ones `ExpandRetrieveJob` and `ExpandAgvChargeJob` build inline use `layout_->GetBayRetrieveFloor(bay).value_or(0)`, the same floor but 0 when the bay has none. Transitions to insert carry floor 0.

### `TYPE_CHARGE_PAYLOAD` — `ExpandChargePayloadJob`

`ExpandChargePayloadJob` brings a car to an EV-charging unit (VECS) and starts charging it. `ExpandJob()` calls it for `TYPE_CHARGE_PAYLOAD` jobs, and the READY_FOR_INSERT and READY_FOR_RETRIEVE job methods use it when the car in a bay has asked for charging; it decides which VECS the car's tray goes to when the tray is not already on a ready one.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:730
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandChargePayloadJob(
    PlanContextSPtr ctx, const interfaces::msg::Guid& payload_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name         | Type                                               | Meaning                                                                                                                                                                                                                                    | In the example below |
|------------------|--------------|----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| in               | `this`       | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                               | Pecos layout         |
| in / **changed** | `ctx`        | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+ a `TrayMove` through `ExpandReparkTrayJob`, + 1 `VecsTransition`) and `last_event_by_entity` | 2 events             |
| in               | `payload_id` | `const interfaces::msg::Guid&`                     | The car to charge                                                                                                                                                                                                                          | car on T20           |
| in               | `job_index`  | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                 | `0`                  |
| out              | return       | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                                     | success              |

**When it runs:** when Dispatch asks for a car to be charged, and inside READY_FOR_INSERT / READY_FOR_RETRIEVE when the car in the bay has `payload.ev_charge_requested`. A VECS is the EV-charging unit at a `TYPE_EV_CHARGE` node; its states include `READY_TO_CHARGE` and `CHARGING`.

![Charge payload job](figures/50_job_charge_payload.svg)

The car on T20 is moved to a VECS (invented here; the Pecos layout has none) and the VECS is switched to CHARGING. The last three steps play the plan: an illustrative AGV-1 drives under T20, carries it onto `V23` (1), and V23 starts charging (2).

In words: if the tray is not already on a ready VECS, borrow the open-space search of `ResolveBlockingTrays(working_state, {.tray_id = tray.id}, job_index)` (explained under tray assignment, [section 4](#bg-tray-assignment-dotrayassignments)) to find one, move the tray there through `ExpandReparkTrayJob`, then add the `VecsTransition` `READY_TO_CHARGE -> CHARGING` with `AddChainedEvent` and `OrderAfterJobLeafEvents`.

### `TYPE_RETRIEVE` — `ExpandRetrieveJob`

`ExpandRetrieveJob` brings a parked car to a bay and hands it over to the customer. `ExpandJob()` calls it for `TYPE_RETRIEVE` jobs; it decides whether the car can be reached and which bay to use, and it is the only job method that can fail with `is_retryable = true`, which becomes `retain_job` and tells Dispatch to keep a failed job and retry it.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:167
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandRetrieveJob(
    PlanContextSPtr ctx, const interfaces::msg::Guid& payload_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name         | Type                                               | Meaning                                                                                                                                                                                                                                                               | In the example below |
|------------------|--------------|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| in               | `this`       | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                                                          | Pecos layout         |
| in / **changed** | `ctx`        | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+2 `BayTransition`s, +1–2 `TrayMove`s through `ExpandReparkTrayJob`, maybe a `VecsTransition`) and `last_event_by_entity` | 4 events, 5 edges    |
| in               | `payload_id` | `const interfaces::msg::Guid&`                     | The car to retrieve                                                                                                                                                                                                                                                   | car on T17           |
| in               | `job_index`  | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                                            | `0`                  |
| out              | return       | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure {message, is_retryable}`. `is_retryable = true` (no bay free, or the car's VECS in a state that cannot stop) becomes `retain_job = true`, which asks Dispatch to keep the job and retry later                            | success              |

**When Dispatch sends it:** a customer wants their car. This is the most important job and the richest method.

![Retrieve job](figures/42_job_retrieve.svg)

Retrieving the car on T17. Bay B21 is chosen, switched to retrieve mode (1), the empty tray inside is planned out (2), T17 is planned in (3), and the bay hands over the car (4). The last eight steps play the plan with AGV-1: the bay opens, T21 goes to `P23`, the blocker T15 is moved to `P19`, T17 is carried into B21, and the bay processes the retrieve. The destinations and the blocker move are illustrative; tray assignment chooses them later.

In words, five decisions in order:

1.  **Is the car reachable?** It must exist and its tray's vertex must be enabled in the payload footprint's keep-out filter. If it sits on a VECS that is charging, add a "stop charging" `VecsTransition` (`AddChargingStopBeforeTrayMove`, `AddChainedEvent` only); a VECS in any other state than charging or ready to charge fails the job with `is_retryable = true`.
2.  **Which bay?** `FindBayForRetrieve` walks `layout_->GetBayPrioritization()` from the back. It skips disabled bays and bays whose resource window is smaller than the car (`IsPayloadWithinBaySizeLimits`), takes the first `READY_TO_RETRIEVE` bay, and otherwise the first `READY_TO_INSERT` or `VEHICLE_INSERTED` bay. None: fail with `is_retryable = true`.
3.  **Open the bay** if it is not in retrieve mode (event 1, built inline, `AddChainedEvent` only).
4.  **Empty the bay** if a tray is inside (event 2, destination left open). The source comment gives the reason this is done here rather than in `ResolveBlockingTrays`: so that AGV assignment clears the bay first.
5.  **Bring the car in, then hand it over** (events 3 and 4). The requested pose is `MakeBayInboundPose(bay)`, reversed unless `payload.reciprocal_to_tray`, so the car ends up facing the way the bay needs. (Inside `ExpandReparkTrayJob`, a retrieval heading would override it, but only parking nodes have one.)

### `TYPE_INSERT` — `ExpandInsertJob`

`ExpandInsertJob` takes a car that a customer has just left in a bay and sends its tray into storage. `ExpandJob()` calls it for `TYPE_INSERT` jobs; it checks the bay, opens it, and leaves the tray's parking spot for tray assignment to choose.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:359
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandInsertJob(
    PlanContextSPtr ctx, uint16_t bay_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name                          | Type                                               | Meaning                                                                                                                                                                                                   | In the example below                      |
|------------------|-------------------------------|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| in               | `this`                        | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                              | Pecos layout                              |
| in / **changed** | `ctx`                         | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+1 `BayTransition`, +1 `TrayMove`) and `last_event_by_entity` | 2 events                                  |
| in               | `bay_id`                      | `uint16_t`                                         | Bay where the customer left the car                                                                                                                                                                       | `21`                                      |
| in               | `job_index`                   | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                | `0`                                       |
| out              | return                        | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                    | success                                   |
| side effect      | `reset_bay_state_request_fn_` | `std::function<void(uint16_t, uint16_t)>` (member) | Asynchronous request to Dispatch for a READY_FOR_INSERT job on this bay                                                                                                                                   | called with `(21, STATE_READY_TO_INSERT)` |

**When Dispatch sends it:** a customer has parked on the tray in a bay that was in insert mode. The car now has to go into storage.

![Insert job](figures/43_job_insert.svg)

The loaded tray T21 leaves bay B21. Its parking spot is chosen later. Refilling the bay is requested as a separate job through a callback. The last three steps play the plan: B21 switches to retrieve mode (1), then an illustrative AGV-1 fetches T21 and parks it at `P19` (2, destination illustrative).

In words: check that the bay exists, is enabled, holds a loaded tray and is `VEHICLE_INSERTED` or `READY_TO_RETRIEVE`, switch it to retrieve mode with `AddBayTransitionToRetrieve` (event 1), move the tray out with no destination (event 2), then call `reset_bay_state_request_fn_` so Dispatch schedules the bay's refill on its own. The source comment says why the refill is a separate job: so that a missing empty tray or an AGV conflict cannot fail this insert.

### `TYPE_READY_FOR_INSERT` — `ExpandReadyForInsertJob`

`ExpandReadyForInsertJob` prepares a bay for the next arriving customer: an empty tray inside and the bay in insert mode. `ExpandJob()` calls it for `TYPE_READY_FOR_INSERT` jobs and `ExpandRebalanceGarageJob` calls it for each bay it wants in insert mode; it decides whether an empty tray must be brought in and, unlike the other job methods, tries to choose that tray itself.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:409
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandReadyForInsertJob(
    PlanContextSPtr ctx, uint16_t bay_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                               | Meaning                                                                                                                                                                                                                                                                                                                     | In the example below               |
|------------------|-------------|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| in               | `this`      | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                                                                                                                | Pecos layout                       |
| in / **changed** | `ctx`       | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+ a `TrayMove` through `ExpandReparkTrayJob`, maybe a charge-payload recipe, +1 `BayTransition`), `last_event_by_entity`, and the tray id of its own new `TrayMove` (fill pass) | 2 events; tray T23 filled in early |
| in               | `bay_id`    | `uint16_t`                                         | Bay to prepare for the next customer                                                                                                                                                                                                                                                                                        | `21`                               |
| in               | `job_index` | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                                                                                                  | `0`                                |
| out              | return      | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                                                                                                                      | success                            |

**When it runs:** to get a bay ready for the next customer: it needs an empty tray inside and insert mode. Sent by Dispatch, and used for each bay that REBALANCE_GARAGE wants in insert mode.

![Ready for insert job](figures/44_job_ready_for_insert.svg)

An empty tray is planned into B21 (chosen early here: T23), then B21 switches to insert mode. The last three steps play the plan: an illustrative AGV-1 drives under T23, carries it into B21 (1), and B21 switches to `READY_TO_INSERT` (2).

In words: the bay must be `READY_TO_RETRIEVE`. If the car in the bay asked for charging, plan `ExpandChargePayloadJob` first. If the bay is empty, or holds a loaded tray, plan "any empty tray → bay" (`ExpandReparkTrayJob(ctx, std::nullopt, job_index, true, MakeBayInboundPose(bay))`, a `TrayMove` with no tray). Then try to pick the empty tray right away with `AssignTraysToBayFillMoves`, and finish with `TRANSITION_TO_INSERT` (`AddChainedEvent` and `OrderAfterJobLeafEvents`).

This is the only job method that **fills a blank itself**. `AssignTraysToBayFillMoves(ctx, job_index)` (`job_expansion.cpp:782`) replays the DAG once more (`fill_state`, because `working_state` predates the reparks just added), walks the events in topological order and, for each of this job's tray moves with a destination but no tray, calls `AssignEmptyTrayToMove` (cheapest to reach: travel time plus 30 s per tray in the way). On success it chains the move after the chosen tray's last event (`ChainAfterLastEntityEvent`, now that the tray is known) and applies it to `fill_state`. If no tray is found, it only logs a warning; `AssignTrays()` will try again with the full picture.

### `TYPE_READY_FOR_RETRIEVE` — `ExpandReadyForRetrieveJob`

`ExpandReadyForRetrieveJob` puts a bay into retrieve mode in advance, so that a later retrieve does not have to wait for the transition. `ExpandJob()` calls it for `TYPE_READY_FOR_RETRIEVE` jobs and `ExpandRebalanceGarageJob` calls it for each bay it wants in retrieve mode; it decides whether the bay must be opened and what happens to a tray left inside.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:463
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandReadyForRetrieveJob(
    PlanContextSPtr ctx, uint16_t bay_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                               | Meaning                                                                                                                                                                                                                                  | In the example below |
|------------------|-------------|----------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| in               | `this`      | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                             | Pecos layout         |
| in / **changed** | `ctx`       | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (maybe a `BayTransition`, a `TrayMove` or a charge-payload recipe) and `last_event_by_entity` | 2 events             |
| in               | `bay_id`    | `uint16_t`                                         | Bay to put into retrieve mode                                                                                                                                                                                                            | `21`                 |
| in               | `job_index` | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                               | `0`                  |
| out              | return      | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                                   | success              |

**When it runs:** to put a bay into retrieve mode ahead of time, so a later retrieve does not wait for the transition. Used mostly by REBALANCE_GARAGE.

![Ready for retrieve job](figures/45_job_ready_for_retrieve.svg)

B21 switches to retrieve mode and the empty tray inside is planned out. There is no final bay event. The last three steps play the plan: the bay opens (1), and an illustrative AGV-1 fetches T21 and parks it at `P23` (2, destination illustrative).

In words: the bay must be in insert or retrieve mode. If in insert mode, open it with `AddBayTransitionToRetrieve` (event 1). If a tray is inside, send an EV car to a VECS with `ExpandChargePayloadJob`, otherwise move the tray out with no destination (event 2).

### `TYPE_CHARGE_AGV` — `ExpandAgvChargeJob`

`ExpandAgvChargeJob` sends an AGV with a low battery to a charger. `ExpandJob()` calls it for `TYPE_CHARGE_AGV` jobs; it decides which free charger is cheapest to reach and, when the AGV is trapped in a bay in insert mode, opens that bay first and restores it afterwards, using `ExpandAgvMoveJob` and `ExpandBayTransitionJob` for those steps.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:605
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandAgvChargeJob(
    PlanContextSPtr ctx, uint16_t agv_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                               | Meaning                                                                                                                                                                                                                                   | In the example below                                                                     |
|------------------|-------------|----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| in               | `this`      | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                              | Pecos layout                                                                             |
| in / **changed** | `ctx`       | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (maybe 2 `BayTransition`s, +1 `AgvMove` through `ExpandAgvMoveJob`) and `last_event_by_entity` | 3 events                                                                                 |
| in               | `agv_id`    | `uint16_t`                                         | AGV whose battery is low                                                                                                                                                                                                                  | `A`                                                                                      |
| in               | `job_index` | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                | `0`                                                                                      |
| out              | return      | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                                    | success; with no free charger it fails with "Caution: No available charge nodes for a… " |

**When Dispatch sends it:** an AGV's battery is low.

![Charge AGV job](figures/48_job_charge_agv.svg)

AGV-1 is trapped in bay B21 (insert mode). The bay opens (1), AGV-1 drives to the cheapest free charger C14 (2), and the bay returns to insert mode (3). Costs are illustrative. The last three steps play the plan on the map.

In words: an AGV already on a charger, at the charger's inbound pose, needs no event. Otherwise free the AGV if a bay in insert mode traps it (an inline `TRANSITION_TO_RETRIEVE`, `AddChainedEvent` only, applied to `working_state`; a bay in any state other than insert or retrieve mode fails the job). `FindUnoccupiedChargerWithShortestTravelTime` then costs every `TYPE_AGV_CHARGE` node with no AGV on it, at `MakeInboundPose(node)` and allowed by the AGV keep-out filter, using `ComputeTravelDuration`; the job moves to the cheapest with `ExpandAgvMoveJob` and puts the bay back with `ExpandBayTransitionJob`. Before PR \#1018 an AGV already on its charger was not recognised when the charger faced reciprocal: `GetInboundHeading` returned an unwrapped 270 and was compared with the AGV's wrapped heading, so the AGV was sent to another charger. `MakeInboundPose` wraps the heading (test `AgvChargeJob.AlreadyOnCharger`).

### `TYPE_CLEAN_GARAGE` — `ExpandCleanGarageJob`

`ExpandCleanGarageJob` tidies the garage: it sends the AGVs to hiding poses and returns trays left on waypoints to parking. `ExpandJob()` calls it for `TYPE_CLEAN_GARAGE` jobs, which Dispatch sends on its own decision or after `Plan()` asks for one following a failed INSERT; it decides which AGVs must move and which trays must leave waypoints.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:514
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandCleanGarageJob(PlanContextSPtr ctx, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                               | Meaning                                                                                                                                                                                                                                                             | In the example below                                                               |
|------------------|-------------|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| in               | `this`      | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`                                                                                                                                                                        | Pecos layout                                                                       |
| in / **changed** | `ctx`       | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (+1 `AgvMove` per AGV to hide when `job_index == 0`, +1 `TrayMove` per waypoint-stashed tray) and `last_event_by_entity` | 3 events                                                                           |
| in               | `job_index` | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                                          | `0`, which enables hiding                                                          |
| out              | return      | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                                                              | success; fails only if hiding, applying a hiding move, or the initial replay fails |

**When it is requested:** Dispatch decides, and `Plan()` asks for one through `clean_garage_request_fn_()` after a failed INSERT ("A failed insert still leaves the garage to clean up").

![Clean garage job](figures/46_job_clean_garage.svg)

AGV-1 and AGV-2 are hidden under trays (1, 2). Tray T9, left on a waypoint by an earlier plan, is planned back into parking (3). The last four steps play the plan: both AGVs drive to their hiding spots, then AGV-2 fetches T9 from `W25` and parks it at `P23`, ending hidden under it (AGV and destination illustrative).

In words: if this is `job_index` 0, ask `FindAgvUnderTrayAssignment(working_state, collision_table_)` (`motion_planner`; [section 7.6](#mp-hide-agvs)) for one pose under a tray per AGV (`std::nullopt` when no assignment exists) and add an `AgvMove` for each AGV that is not already there, chained after the AGV's last event and, if it ends in a bay, after the bay's last event (`AddChainedEvent`, then `ChainAfterLastEntityEvent` with the bay's id; no `OrderAfterJobLeafEvents`), and applied to `working_state`. Then `ReparkWaypointStashedTrays` adds a destination-less `TrayMove` for every enabled tray standing on a `TYPE_WAYPOINT` node; a tray that fails is logged and skipped. Only the hiding step, applying a hiding move (reported since PR \#1018; it was ignored before) or the initial replay of the DAG can fail the job.

### `TYPE_REBALANCE_GARAGE` — `ExpandRebalanceGarageJob`

`ExpandRebalanceGarageJob` adjusts how many bays are ready for insert and how many are ready for retrieve. `ExpandJob()` calls it for `TYPE_REBALANCE_GARAGE` jobs; it decides which bays to switch and builds the work for each of them from the READY_FOR_INSERT and READY_FOR_RETRIEVE job methods.

``` cpp
// scheduler.hpp; defined in job_expansion.cpp:576
[[nodiscard]] stdx::Expected<void, JobFailure> ExpandRebalanceGarageJob(
    PlanContextSPtr ctx, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                               | Meaning                                                                                                                                                                                                                                       | In the example below                      |
|------------------|-------------|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| in               | `this`      | `const Scheduler*`                                 | Fixed planner data, read only: `layout_`, `motion_graph_`, `collision_table_`, `cost_model_`, `target_insert_ready_bay_fraction_`                                                                                                             | Pecos layout                              |
| in / **changed** | `ctx`       | `PlanContextSPtr` (`std::shared_ptr<PlanContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `event_dag`, `keep_out_filter_by_footprint`. Changed: `event_dag` (the READY_FOR_INSERT / READY_FOR_RETRIEVE recipes for each chosen bay) and `last_event_by_entity` | 4 events for 2 bays                       |
| in               | `job_index` | `size_t` (by value)                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                    | `0`, shared by every bay's recipe         |
| out              | return      | `stdx::Expected<void, JobFailure>`                 | nothing on success; on failure a `JobFailure` with the reason (`is_retryable = false`)                                                                                                                                                        | success; per-bay failures are only logged |

**When it is requested:** when the `set_bay_readiness_ratio` service changes the target fraction (`target_insert_ready_bay_fraction_` inside the scheduler; the ROS parameter and the service keep the old name, and since PR \#1018 a non-finite value is rejected), `SchedulerRos` calls `rebalance_garage_request_fn_()` to ask Dispatch for this job; Dispatch can also send it on its own. [Section 20](#bg-bays-vecs-and-vrcs) explains the ratio and how bays are classified.

![Rebalance garage job](figures/47_job_rebalance_garage.svg)

B7 gets an empty tray and insert mode (1, 2); B21 gets retrieve mode and its tray is planned out (3, 4). One job index for both bays makes `OrderAfterJobLeafEvents` run them one after the other. The last six steps play the plan in that order with an illustrative AGV-1: T5 into B7, B7 to insert mode, B21 to retrieve mode, then T21 out to `P23` (destination illustrative).

In words: `ComputeBayRebalancingActions(working_state, bay_prioritization, target_insert_ready_bay_fraction_)` returns a `BayRebalancingActions` with two bay lists; run `ExpandReadyForInsertJob` for each of `bays_to_make_insert_ready` and `ExpandReadyForRetrieveJob` for each of `bays_to_make_retrieve_ready`, all with the same `job_index`. Per-bay failures are only logged; the job fails only if the initial replay of the DAG fails.

### Gotchas

These are behaviours of the code that surprise people. Four of them (1, 2, 3 and 11) were fixed in PR \#1018 and are kept here, marked, because older plans and logs show them; the others are unchanged, and changing them changes plans.

1.  **A failed job could leave events behind (fixed in PR \#1018).** `Plan()` did not remove events when a job method failed, and `FailJob()` carried a TODO about it ("strip all the events which may be in the dag for the now failed job"). It happened when a method had already added something before a later check failed, for example:

    - RETRIEVE adds "stop charging" and then finds no bay;
    - RETRIEVE or INSERT opens a bay and then the repark fails;
    - CHARGE_AGV opens a bay and then finds no charger.

    The leftover events kept the failed job's `job_index`, which the next successful job reused ([14.2](#bg-the-loop-in-plan)), so they were reported and executed as part of that job, and if no later job succeeded, `ctx->scheduled_jobs[event->GetJobIndex()]` read past the end of the vector. `Plan()` now copies the context before each job and restores it when the job fails. One case remains by design: inside REBALANCE_GARAGE a bay recipe that fails is only logged, so its partial events stay under the (successful) rebalance job.

2.  **`ExpandReparkTrayJob` looked the tray up in `ctx->initial_state` (fixed in PR \#1018).** The "already at destination" check therefore compared with the tray's position in the request, not after earlier jobs, and the "is it on a charging VECS" check looked at the request node too. It now reads the tray from `working_state`, falling back to `initial_state` only for a tray that an earlier destination-less move took out of the planned state (test `ReparkTrayJob.ReturnsTrayAfterEarlierRepark`).

3.  **`ExpandReparkTrayJob` with no tray but a destination read an empty optional (fixed in PR \#1018).** The line `if(tray_opt->pose == dest.value())` ran even when `tray_id` was `std::nullopt` (READY_FOR_INSERT's "any empty tray" case), which is undefined behaviour. The check now sits inside `if(tray_opt)`.

4.  **`job_index == 0` means "first successful job".** CLEAN_GARAGE hides AGVs only then. If earlier jobs in the request failed, a later CLEAN_GARAGE can still get index 0.

5.  **Bay transitions are not always necessary ones.** `AddBayTransitionToRetrieve` (INSERT) adds `TRANSITION_TO_RETRIEVE` even when the bay is already `READY_TO_RETRIEVE`.

6.  **CHARGE_PAYLOAD throws away the unblocking moves** that `ResolveBlockingTrays()` returns (`auto [dest_garage_pose_opt, _] = ...`). They are found again in tray assignment.

7.  **"Free charger" only means "no AGV on the node".** The code says so ("Unoccupied means no AGV on the node, not collision free").

8.  **`OrderAfterJobLeafEvents` serialises composite jobs.** REBALANCE_GARAGE's per-bay recipes share one `job_index`, so each bay waits for the previous bay's work.

9.  **Some bay commands skip the disabled check.** `ExpandReadyForInsertJob`, `ExpandReadyForRetrieveJob`, `AddBayTransitionToRetrieve` and CHARGE_AGV's trapped-bay branch never test `bay.disabled` (INSERT and TRANSITION_BAY_TO\_\* do). `Plan()` marks bays that already have a command in `base_schedule` as disabled (`ExcludeCommittedResources`), so those methods can command such a bay again; READY_FOR_INSERT is only stopped indirectly, because the repark into a disabled bay fails.

10. **INSERT's callback fires before the plan is known to succeed.** `reset_bay_state_request_fn_` runs during job expansion, so Dispatch receives the refill request even if tray assignment or motion planning later fails the whole plan.

11. **Late failures duplicated failed jobs (fixed in PR \#1018).** When a later stage failed, `Plan()` called `FailJob` for every entry of `request_data.pending_jobs`, including jobs that had already failed in the loop, so the response could list the same job twice. `fail_all_jobs` now fails only `ctx->scheduled_jobs` (test `RetrieveJob.FailedJobReportedOnce`).

12. **`AssignEmptyTrayToMove` ([under tray assignment](#bg-filling-a-blank-tray-id-assigntrayidforemptymove)) may change the destination heading** to the chosen tray's heading when the two are the same or opposite, to avoid a rotation.

### Cheat sheet and self-check

This section closes job expansion with a one-page summary of the events each job type can create, followed by five questions to check understanding before tray assignment. The figure condenses sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob); the questions draw on the loop, the edge helpers and the job figures.

![Job recipes](figures/24_job_recipes.svg)

Cheat sheet: one row per job type, **not** a sequence of scenarios. Each row lists the events that job method can add, left to right in creation order. Dashed boxes appear only when needed; "+ recipe" means the method calls another job method; "?" is a blank for `AssignTrays()`. Step through the job types family by family: single-entity building blocks first, then customer jobs, bay preparation, charging and housekeeping, which reuse them. The figures in [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) show each row in a garage.

Check yourself before moving on:

1.  A request has `[RETRIEVE (fails), MOVE_AGV, REPARK_TRAY]`. What `job_index` does each successful job get?
2.  Job 0 reparks T19 to P24 and job 1 reparks T19 to P23. Which helper orders the two moves, and why does `OrderAfterJobLeafEvents` not?
3.  In the retrieve figure, why does event 3 have edges from both 1 and 2?
4.  Which job types can leave a `TrayMove` with no destination? With no tray?
5.  Why can a bay's ODP check fail for TRANSITION_BAY_TO_INSERT but not for INSERT?

Answers

1.  MOVE_AGV gets 0 and REPARK_TRAY gets 1; the failed retrieve uses no index, and since PR \#1018 any events it added first are dropped with it (gotcha 1).
2.  `ChainAfterLastEntityEvent` (same tray). `OrderAfterJobLeafEvents` only links events of the same job.
3.  `OrderAfterJobLeafEvents` (2 was the job's only leaf) and `OrderAfterBayAndChargerEvents` (the tray is going into bay B21, whose last event is 1).
4.  No destination: RETRIEVE, INSERT, READY_FOR_RETRIEVE, CLEAN_GARAGE (and REBALANCE through READY_FOR_RETRIEVE). No tray: READY_FOR_INSERT (and REBALANCE through it) when its fill pass (`AssignTraysToBayFillMoves`) finds no empty tray.
5.  The ODP check lives in `ExpandBayTransitionJob`; INSERT uses `AddBayTransitionToRetrieve`, which does not check it.

## Tray assignment: `AssignTrays`

Tray assignment is the second stage of task planning: `AssignTrays(ctx)` (`tray_assignment.cpp:42`, with its helpers in the same file) runs after job expansion and before AGV assignment, on the event DAG that expansion produced. It completes every `TrayMove` that expansion left with a blank tray or destination and adds the moves that take blocking trays out of the way. The subsections below first state the problem, then follow one event through the stage.

### The problem this stage solves

Job expansion ([section 14](#bg-job-expansion-from-jobs-to-events)) turns each job into events, but those events describe *intent*, not a finished plan. Two things are still missing when expansion ends.

**1. Some `TrayMove` events have blank fields.** Every physical tray in the garage has an id, and the scheduler always knows where it is. The blank is not on a tray; it is on an **event**. A `TrayMove` stores its tray id and its destination as `std::optional`s (`GetTrayId()`, `GetDest()`), and a job method leaves one of them empty on purpose when the job's request does not decide it:

| Blank field | Event means                       | Created by                                                                                                                                                                                                                                          | Why the job leaves it blank                                                                                                                                   | Filled by                             |
|-------------|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| tray id     | “*some* empty tray → this pose”   | `READY_FOR_INSERT`: `ExpandReparkTrayJob(ctx, std::nullopt, job_index, true, bay_pose)`                                                                                                                                                             | The customer wants *an* empty tray in the bay; any one will do, and the best one depends on where trays are at that point in the plan                         | `AssignEmptyTrayToMove`               |
| destination | “this tray → *anywhere sensible*” | `RETRIEVE` (an empty tray already in the bay must leave first), `INSERT` (the tray with the new car leaves the bay), `READY_FOR_RETRIEVE` (tray in the bay leaves), `CLEAN_GARAGE` (`ReparkWaypointStashedTrays`: stashed trays go back to parking) | The job only needs the tray *out of the way* or *parked*; which stall is a search over the garage, which `ResolveBlockingTrays()` runs during tray assignment | `AssignDestinationAndUnblockingMoves` |

These fields are filled in here rather than in the job methods because choosing a tray or a stall is a graph search, and the answer can create *extra* moves (a tray in the way must be moved first) plus new DAG edges. That machinery lives here. This stage also walks the events in DAG (topological) order, with a copy of the garage state, `working_state`, that is updated after every move. Each choice therefore sees the garage as it will be *at that point in the plan*, including moves that earlier jobs in the same request already scheduled.

**2. Destinations are often unreachable as the garage stands.** The garage is dense: trays park nose-to-tail, and a tray can only travel through nodes that are free. Two terms are used throughout this section:

- The **root tray** is the tray of the `TrayMove` currently being processed: the tray a job actually asked to move (a car to retrieve, an empty tray for a bay).
- A **blocking tray** is any other tray whose footprint collides with the root tray's path to its destination (collision is decided by the `CollisionTable`, [section 5.4](#bg-collisiontable-precomputed-conflict-sets), not just equal node ids). It must move out of the way first. No job asked for that move; this stage invents it.

When `AssignTrays(ctx)` succeeds (it returns an `stdx::Result`; any failure fails every expanded job), three things hold:

- every `TrayMove` in `ctx->event_dag` has a tray id **and** a destination;
- every blocking tray has its own new `TrayMove`, ordered before the move it unblocks;
- the DAG has edges that keep moves from entering space before it is freed (`occupancy_history`, below), and `ctx->first_event_by_tray` records the first move of each tray for AGV assignment.

The rest of the section follows one event through the stage: the overall flow ([Figure 46](#bg-fig-27_tray_assignment_flow)), the main blocking-tray loop for a move that already has both fields, then the two helpers that fill a blank tray id and a blank destination, and finally how occupancy becomes DAG edges.

![Scene used in the following figures](figures/15_facility_scenario.svg)

The problem in one picture. Step through to build the scene: first the real Pecos geometry, then the job: a job asked for the car on tray R, so **R is the root tray**: it sits at `P17` and must reach bay `B21`. It cannot, because every exit from `P17` is occupied or useless: `P15` holds the empty tray K, `P20` holds T20 (with a car), and charger `C16` is a dead end. K and T20 are therefore **blocking trays**: no job asked to move them, but one of them must move before R can. Tray assignment finds that out and adds the extra move. Bays `B7` and `B21` sit on the customer side; AGV-1 waits at charger `C10`, and T15 (with a payload) is at `P3`. The last step previews what has to happen: AGV-1 drives to `W13`, next to the blockers, and K must move out of the way first (for example to `P19`); [Figure 47](#bg-fig-15_blocking_tray_move) plays that plan. All positions are explanatory stand-ins, not YAML occupancy.

![AssignTrays flow](figures/27_tray_assignment_flow.svg)

Inside `AssignTrays()`. Bay and VECS transitions register their pose with the occupancy history (`TrayAssignmentState::occupancy_history`) and are applied. Missing tray ids come from an empty-tray search; missing destinations from `ResolveBlockingTrays`. Moves with both go through the blocking-tray loop with two fallbacks. Step through the loop to follow concrete events: a bay transition, an untargeted move, and a move whose blocker T15 is resolved and emitted as a new event, then what the fallbacks and the empty-tray branch would do.

The stage keeps its working data in a `TrayAssignmentState` (defined in `tray_assignment.cpp`): `working_state`, a copy of `ctx->initial_state`; `last_event_by_tray`, the latest move of each tray so far; and `occupancy_history`, the events recorded at the poses they use. Per event, in topological order (`tray_assignment.cpp:52`):

1.  **Not a `TrayMove`**: `ApplyBayOrChargerTransition` records a bay or VECS transition at the bay's or charger's inbound pose in `occupancy_history`, applies it to `working_state`, and moves on. Other events (AGV moves) are passed over.
2.  **Tray id blank** → `AssignEmptyTrayToMove` (`:63`) picks a tray; the event then **continues** down this list with both fields set.
3.  **Destination blank** → `AssignDestinationAndUnblockingMoves` (`:70`) picks a destination, emits the blocker moves, and the loop **`continue`s**: the main loop below is skipped for this event.
4.  **Both set** → the main blocking-tray loop.

Three of the searches from [section 3](#bg-the-motion-planner-toolbox) do the work here. All three use the same search routine, `SingleSourceSearch(start_state, Interval::Duration(0), environment)`, which expands the garage graph outward from a source node in order of cost. The routine itself knows nothing about trays. That knowledge comes from its last argument, the **search environment**: a small class that tells the search what each step costs, which nodes may be entered, and when a node is a goal. Swapping the environment turns the same routine into a different search ([section 7.4](#mp-tray-searches), with figures). In the table, the first column is that class, the second the scheduler method that runs the search, and the third what the search returns:

| Search environment (goal and cost rules) | Run by                                                     | What the search returns                                                                                                            |
|------------------------------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `EmptyTraySearchEnvironment`             | `AssignEmptyTrayToMove`                                    | the tray without a payload that is cheapest to bring, searching outward from the destination (travel time + 30 s per tray crossed) |
| `OpenSpaceSearchEnvironment`             | `FindDestinationForRootTray`, `FindBlockingTrayResolution` | a free parking spot (tier 1) or, if `is_waypoint_stash_allowed`, a waypoint (tier 2), plus the trays blocking the way              |
| `BlockingTraySearchEnvironment`          | the main loop                                              | the critical path from the tray to its destination and the trays on it                                                             |

### The blocking-tray loop

The main loop of `AssignTrays` handles every `TrayMove` that has both a tray id and a destination; it is where blocking trays are found and given moves of their own. The figure first shows, on a small example, why a move can be impossible until another tray moves; the five steps of the loop follow it.

![Blocking tray example](figures/15_blocking_tray_move.svg)

Why blocking trays matter. Step through the plan one move at a time: each numbered arrow appears first as a preview, and AGV-1 drives it in the next step, carrying the tray it has lifted. Root tray R at `P17` must reach bay `B21`. In the Pecos graph `P17` connects only to `P15`, `P20` and charger `C16`; with K at `P15` and T20 at `P20`, every exit is occupied. AGV-1 therefore ① drives under K and lifts it, ② reparks K at the free stall `P19`, ③ returns unloaded to lift R, and ④ carries R out; the bay transition at `B21` comes last. The event card being executed is outlined, and the final step shows the whole plan at once, with dashed outlines marking where K and R started. It does **not** claim the current solver would pick this relocation target or route.

This is what happens to a `TrayMove` that has both a tray id and a destination, such as “R: `P17` → `B21`”. The loop body is long in the source (about 240 lines, `tray_assignment.cpp:77`–`:315`), but it does five things in order:

1.  **Check the destination** (`:80`–`:86`). `BuildImmobileTrayFilter(TRAY, working_state, {})` builds a filter that ignores *every* tray and AGV (trays will be moved, AGVs will drive away), and `ResolveDestinationHeading` checks that the destination vertex is enabled. If it is not, the job fails with “… but it's occupied, or not enabled.” “Occupied” here means something that will not move out of the way: a disabled node, a disabled tray or AGV (its node is blocked at the largest footprint even though it is in the ignore set), or a bay that is not `READY_TO_RETRIEVE` (the call passes no bays to ignore, so a closed bay's overdrive-plate (`BAY_ODP`) area is blocked); ordinary trays and AGVs are ignored. A destination whose pose is not in the graph but whose reverse is goes to the reverse pose; before PR \#1018 that case threw (it is unreachable today, because every heading's vertex is created with its reverse).
2.  **Find the critical path** (`:88`–`:132`). Search from the root tray to the destination with `BlockingTraySearchEnvironment`. Unlike a normal path search, this one may pass *through* trays; it records them. The result is the **critical path** (`root_path`, the nodes R will travel over, also kept as `root_path_illegal_poses`) and `blocking_trays`, the trays on it, in path order.
3.  **Resolve blockers one at a time** (`while(!blocking_trays.empty())`, `:134`). For the first blocker, ask `ResolveBlockingTrays` for a new home that is not on the critical path and does not require moving R. Two fallbacks follow if that fails (below).
4.  **Turn the answer into events** (`:211`–`:289`). Add each required move and the blocker's own move to the DAG, chained in order, with occupancy edges along the poses each one occupies, and finally an edge “blocker move → root move”. Then re-scan the rest of the critical path for blockers and repeat step 3.
5.  **Finish the root move** (`:292`–`:315`). Add occupancy edges for the destination and source poses (`OrderAfterPriorOccupants`), register the source pose, apply the move to `working_state`, and chain it after the tray's previous move (`ChainTrayEvent`).

``` cpp
// Where: Scheduler::AssignTrays(PlanContextSPtr ctx) const, tray_assignment.cpp:42,
// inside the per-event loop, once `move` (TrayMove*) has both a tray id and a destination.
//   state                  -> TrayAssignmentState: working_state, last_event_by_tray, occupancy_history
//   tray_opt               -> std::optional<interfaces::msg::DiscreteTrayState>, the root tray in state.working_state
//   root_tray_collision_id -> CollisionEntityId_t for the root tray's footprint (depends on its payload)
//   path_filter            -> BuildImmobileTrayFilter(TRAY, state.working_state, {}): every tray and AGV ignored
BlockingTrayState start_state;                                     // search state: a vertex + trays met so far
start_state.vert = motion_graph_.GetVertexFromPose(tray_opt->pose).value();
const auto dest_vertex = motion_graph_.GetVertexFromPose(move->GetDest().value()).value();
BlockingTraySearchEnvironment blocking_search_env(tray_id, root_tray_collision_id, motion_graph_,
    collision_table_, state.working_state, cost_model_, dest_vertex, path_filter);
auto blocking_solution = SingleSourceSearch(start_state, Interval::Duration(0), blocking_search_env);
auto root_target = blocking_solution.GetTarget().value();          // checked first in the real code
auto root_path = blocking_solution.GetPath(root_target).value();    // the critical path

for(const auto& [path_state, _] : root_path) {                     // collect, in path order:
  root_path_illegal_poses[path_state.vert] = root_tray_collision_id;  //   the nodes R will occupy
  for(auto blocking_tray_id : path_state.blocking_trays) {           //   the trays in the way, once each
    if(blocking_tray_set.insert(blocking_tray_id).second) {
      blocking_trays.push_back(blocking_tray_id);
    }
  }
}

while(!blocking_trays.empty()) {
  auto blocking_tray_id = blocking_trays.front();
  PlannedTrayMoves required_moves;
  // Find a new home for the blocker. The root tray may not move (immobile_trays) and the blocker may not
  // park on the root path or on a spot it was already sent to for this root move (with_prior_dests).
  const auto resolve_blocking_tray = [&](VertexCollisionIdMap illegal_poses) {
    auto [resolved_dest, repark_moves] = ResolveBlockingTrays(state.working_state,
        {.tray_id = blocking_tray_id, .immobile_trays = {tray_id}, .illegal_poses = std::move(illegal_poses)},
        move->GetJobIndex());
    required_moves.insert(required_moves.end(), std::make_move_iterator(repark_moves.begin()),
        std::make_move_iterator(repark_moves.end()));
    return resolved_dest;
  };
  auto dest = resolve_blocking_tray(with_prior_dests(blocking_tray_id, root_path_illegal_poses));
  // fallback 1: advance the root tray one step along its path, then try again
  // fallback 2: allow parking on the root path; if that fails too -> "Failed to find open space for blocking tray t…"
  // emit required_moves + the blocker's own move as events, chained, each before `event` (the root move)
  // recompute blocking_trays for the rest of the path
}
```

The snippet calls seven functions and builds about a dozen local variables. Each function has its own table below, in the order the snippet calls them, followed by one table for the variables. `BlockingTraySearchEnvironment`, `SingleSourceSearch`, `BuildStaticObstacleFilter` (which `BuildImmobileTrayFilter` calls) and the search solution come from `motion_planner`; their declarations are in the hover windows, and [section 7](#mp-single-agent-searches) explains all the searches.

**Function 1 · `motion_graph_.GetVertexFromPose(pose)`**: turn a garage pose into a search-graph vertex. Called twice: once for the start, once for the goal.

| Dir | Name   | Type                                           | Meaning                                                                                                                                                                                                         | In [Figure 47](#bg-fig-15_blocking_tray_move)                                                   |
|-----|--------|------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| in  | `this` | `const volley::GarageGraph&` (`motion_graph_`) | The pose graph ([section 3](#bg-the-physical-garage-and-its-coordinate-system)), read only                                                                                                                      | Pecos graph                                                                                     |
| in  | `pose` | `const GaragePoseMsg&`                         | Node id + heading                                                                                                                                                                                               | `tray_opt->pose` = `{node_id: 17, heading: …}`; `move->GetDest()` = `{node_id: 21, heading: …}` |
| out | return | `std::optional<Vertex>`                        | The vertex for that pose; empty if the node does not allow that heading. The snippet calls `.value()` without checking: the destination was already checked in step 1, and the tray's own pose is assumed valid | `start_state.vert`, `dest_vertex`                                                               |

**Function 2 · `volley::BlockingTraySearchEnvironment(...)` (constructor)**: describe the critical-path search: where to start, where to go, what blocks the way.

| Dir | Name           | Type                                   | Meaning                                                                                                                                                                          | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|-----|----------------|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| in  | `tray_id`      | `uint16_t`                             | The root tray. It is the one moving, so it is not counted as blocking itself                                                                                                     | R                                             |
| in  | `collision_id` | `size_t`                               | The root tray's footprint (`root_tray_collision_id`). A tray with a car is larger than an empty one, so this changes which trays collide                                         | R with a car                                  |
| in  | `graph`        | `const volley::GarageGraph&`           | Graph to search                                                                                                                                                                  | `motion_graph_`                               |
| in  | `table`        | `const volley::CollisionTable&`        | Answers “does footprint A at pose X overlap footprint B at pose Y?” ([section 3](#bg-the-physical-garage-and-its-coordinate-system))                                             | `collision_table_`                            |
| in  | `base_state`   | `const volley::DiscreteGarageState&`   | Where every tray and AGV is right now in the plan                                                                                                                                | `state.working_state`                         |
| in  | `cost_model`   | `const cost::MotionCostModel&`         | Edge cost: the unloaded trapezoid time of the edge, plus 30 s for every tray that the path newly crosses. The heuristic is zero, so this is Dijkstra on that cost                | `cost_model_`                                 |
| in  | `target`       | `std::optional<Vertex>`                | The destination vertex; reaching it ends the search. A further optional argument, `max_blocking_trays`, can cap how many trays a path may cross; tray assignment does not set it | `B21`                                         |
| in  | `filters`      | `std::optional<GraphFilterProperties>` | Edges the tray may not use at all (this search tests edge flags only). Built with every tray and AGV ignored, so only permanent obstacles block the search                       | `path_filter`, from `BuildImmobileTrayFilter` |
| out | object         | `BlockingTraySearchEnvironment`        | Passed to `SingleSourceSearch`. Unlike a normal path search, it lets the path go **through** trays and records each one in the state's `blocking_trays`                          | `blocking_search_env`                         |

**Function 3 · `SingleSourceSearch(source, init_cost, env)`**: run the search.

| Dir | Name        | Type                                                    | Meaning                                                                                                                                                         | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|-----|-------------|---------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| in  | `source`    | `volley::BlockingTrayState`                             | Start state: `.vert` set to the root tray's vertex; `.blocking_trays` starts empty                                                                              | `start_state` at `P17`                        |
| in  | `init_cost` | `volley::Interval::Duration`                            | The starting cost of the search (A\*'s g value at the source), not a clock time. `Duration(0)`: tray assignment ignores time, so only costs and topology matter | `0`                                           |
| in  | `env`       | the environment (here `BlockingTraySearchEnvironment&`) | Decides neighbours, costs and the goal test. The same function runs all three searches in this section; only the environment changes                            | `blocking_search_env`                         |
| out | return      | `SearchSolution<BlockingTrayState, Interval::Duration>` | Holds the explored states; queried with `GetTarget()` and `GetPath()`                                                                                           | `blocking_solution`                           |

**Function 4 · `blocking_solution.GetTarget()`**: did the search reach the goal?

| Dir | Name   | Type                                       | Meaning                                                                                                                                                                                                                                            | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|-----|--------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| in  | `this` | the search solution                        | Result of step 3                                                                                                                                                                                                                                   | `blocking_solution`                           |
| out | return | `std::optional<volley::BlockingTrayState>` | The goal state reached, or empty if no path exists even through trays (or the search hit its cap of 5,000,000 expansions). The real code checks this and fails the job with “Failed to find path for t…”; the snippet calls `.value()` for brevity | the `B21` state                               |

**Function 5 · `blocking_solution.GetPath(target)`**: read back the path to that goal.

| Dir | Name     | Type                                                          | Meaning                                                                                                                                                                                                                                                                                                                                          | In [Figure 47](#bg-fig-15_blocking_tray_move)  |
|-----|----------|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| in  | `this`   | the search solution                                           | Result of step 3                                                                                                                                                                                                                                                                                                                                 | `blocking_solution`                            |
| in  | `target` | `const volley::BlockingTrayState&`                            | The goal state from step 4                                                                                                                                                                                                                                                                                                                       | the `B21` state                                |
| out | return   | `std::optional<std::vector<std::pair<BlockingTrayState, …>>>` | States from start to goal, in order. The second element of each pair (the step cost) is ignored here (`_`). Each state has `.vert` and `.blocking_trays`: the trays collected so far along the path, each added when R's footprint, swept along an edge, overlaps it. States compare by vertex only, so the first set that settles a vertex wins | `P17 → P15 → … → B21`; the `P15` state lists K |

**Function 6 · `ResolveBlockingTrays(base_state, request, job_index)`**: find a new home for one blocker. The snippet calls it through the local lambda `resolve_blocking_tray`, which appends the returned moves to `required_moves` and returns the destination. Full description under `AssignDestinationAndUnblockingMoves` below.

| Dir | Name                                    | Type                                                                                                          | Meaning                                                                                                                                                                         | In [Figure 47](#bg-fig-15_blocking_tray_move)  |
|-----|-----------------------------------------|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| in  | `this`                                  | `const Scheduler*`                                                                                            | Read only: `motion_graph_`, `collision_table_`, `cost_model_`, `layout_`                                                                                                        |                                                |
| in  | `base_state`                            | `const DiscreteGarageState&`                                                                                  | Starting state. Copied inside and never changed; nothing is applied to `state.working_state` yet                                                                                | `state.working_state`                          |
| in  | `request.tray_id`                       | `uint16_t` (in `ResolveRequest`)                                                                              | The tray that needs a home. Here it is the **blocker**, not R                                                                                                                   | K                                              |
| in  | `request.immobile_trays`                | `std::set<uint16_t>` (default `{}`)                                                                           | Trays the search must route around and may never move. Holding R still stops the solver from “solving” the blocker by moving the root tray                                      | `{R}`                                          |
| in  | `request.illegal_poses`                 | `VertexCollisionIdMap` (default `{}`)                                                                         | Vertices the blocker may not park on                                                                                                                                            | `with_prior_dests(K, root_path_illegal_poses)` |
| in  | `request.is_retrieval_heading_enforced` | `bool` (default `false`)                                                                                      | Park facing the node's retrieval heading                                                                                                                                        | `false` (default)                              |
| in  | `request.is_waypoint_stash_allowed`     | `bool` (default `true`)                                                                                       | Allow parking on a waypoint if no stall is reachable                                                                                                                            | `true` (default)                               |
| in  | `job_index`                             | `size_t`                                                                                                      | Stored in every `TrayMove` it creates, so blocker moves count as part of R's job                                                                                                | `move->GetJobIndex()`                          |
| out | `.dest`                                 | `std::optional<interfaces::msg::GaragePose>`                                                                  | The blocker's new pose, or empty if none was found (the fallbacks then run)                                                                                                     | `P19`                                          |
| out | `.required_moves`                       | `PlannedTrayMoves` = `std::vector<PlannedTrayMove>`; each is `{move, occupied_poses, source_pose_if_applied}` | Moves that must happen before the blocker's own move, in order, each with the poses it occupies. The blocker's own move is **not** in this list; the loop creates it afterwards | `[]`                                           |

**Function 7 · `with_prior_dests(blocking_tray_id, illegal_poses)`**: a local lambda in `AssignTrays` (`:113`) that builds the `illegal_poses` field of the request.

| Dir      | Name                           | Type                                                  | Meaning                                                                                                                                  | In [Figure 47](#bg-fig-15_blocking_tray_move)      |
|----------|--------------------------------|-------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------|
| captured | `prior_dests_by_blocking_tray` | `std::unordered_map<uint16_t, VertexCollisionIdMap>&` | For each blocker, every spot it has already been sent to while clearing this root tray's path, recorded with the blocker's own footprint | empty at first                                     |
| in       | `blocking_tray_id`             | `uint16_t`                                            | The blocker                                                                                                                              | K                                                  |
| in       | `illegal_poses`                | `VertexCollisionIdMap` (by value)                     | The starting set of forbidden vertices                                                                                                   | `root_path_illegal_poses` (fallback 2 passes `{}`) |
| out      | return                         | `VertexCollisionIdMap`                                | `illegal_poses` plus the blocker's prior spots. Stops a blocker from bouncing between two spots forever                                  | `root_path_illegal_poses` unchanged                |

**Variables used in the snippet**

| Name                      | Type                                                             | Set where                                                                                                                                                                        | Meaning                                                                                                                 | In [Figure 47](#bg-fig-15_blocking_tray_move)        |
|---------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `move`                    | `TrayMove*`                                                      | `dynamic_cast` of the current event                                                                                                                                              | The root move being processed; both fields are set                                                                      | R: `P17` → `B21`                                     |
| `event`                   | `std::shared_ptr<volley::ScheduleEvent>`                         | loop variable                                                                                                                                                                    | The same object as `move`, as the DAG stores it; blocker moves become its prerequisites                                 | the root move                                        |
| `state.working_state`     | `DiscreteGarageState` (in `TrayAssignmentState`)                 | copy of `ctx->initial_state`, updated after every applied move                                                                                                                   | The garage as it stands at this point in the plan                                                                       | K at `P15`, T20 at `P20`                             |
| `tray_opt`                | `std::optional<interfaces::msg::DiscreteTrayState>`              | `state.working_state.GetTray(tray_id)`                                                                                                                                           | The root tray's current state (pose, payload)                                                                           | R at `P17`                                           |
| `root_tray_collision_id`  | `CollisionEntityId_t`                                            | `CollisionEntityIdFromTrayState(tray_opt.value(), state.working_state, layout)`                                                                                                  | The root tray's footprint, which depends on its payload                                                                 | R with a car                                         |
| `path_filter`             | `GraphFilterProperties`                                          | `BuildImmobileTrayFilter(TRAY, state.working_state, {})`, which calls `BuildStaticObstacleFilter(TRAY, motion_graph_, working_state, collision_table_, all trays, all AGVs, {})` | Usable edges when every tray and AGV is ignored (closed bays and disabled entities still block)                         | all edges except near disabled nodes and closed bays |
| `start_state`             | `BlockingTrayState`                                              | built in the snippet                                                                                                                                                             | Search start: `.vert` = R's vertex                                                                                      | `P17`                                                |
| `blocking_search_env`     | `BlockingTraySearchEnvironment`                                  | function 2                                                                                                                                                                       | The search description                                                                                                  |                                                      |
| `blocking_solution`       | search solution                                                  | function 3                                                                                                                                                                       | The search result                                                                                                       |                                                      |
| `root_path`               | `std::vector<std::pair<BlockingTrayState, …>>`                   | function 5                                                                                                                                                                       | R's **critical path**: the vertices R travels over, each with the trays in the way there                                | `P17 → P15 → … → B21`                                |
| `path_state`              | `const BlockingTrayState&`                                       | loop over `root_path`                                                                                                                                                            | One step of the path                                                                                                    | the `P15` step                                       |
| `root_path_illegal_poses` | `VertexCollisionIdMap` (vertex → `CollisionEntityId_t`)          | filled from `root_path`                                                                                                                                                          | Every vertex of R's path tagged with R's footprint; passed as `illegal_poses` so no blocker is parked where R must pass | `P17`, `P15`, …                                      |
| `blocking_trays`          | `std::vector<uint16_t>`                                          | filled from `path_state.blocking_trays`                                                                                                                                          | Trays in R's way, in path order, each once. The `while` loop works through it from the front                            | `[K]`                                                |
| `blocking_tray_set`       | `std::set<uint16_t>`                                             | alongside `blocking_trays`                                                                                                                                                       | Only for de-duplication                                                                                                 | `{K}`                                                |
| `blocking_tray_id`        | `uint16_t`                                                       | `blocking_trays.front()`                                                                                                                                                         | The blocker being resolved in this iteration                                                                            | K                                                    |
| `dest`, `required_moves`  | `std::optional<interfaces::msg::GaragePose>`, `PlannedTrayMoves` | `resolve_blocking_tray`'s return value, and the moves it appended                                                                                                                | The blocker's new spot and its prerequisite moves                                                                       | `P19`, `[]`                                          |

**The two fallbacks** (`:150` and `:203`). If `ResolveBlockingTrays` returns no destination, the loop first tries to **advance the root tray one step** along its critical path: if no other tray collides with the next pose (`collision_table_.Query(...)`), it creates a one-step `TrayMove` for R, applies it once, removes R's old vertex from `root_path_illegal_poses`, adds the advance to `required_moves` as a `PlannedTrayMove` that occupies the pose before the advance and the next pose (and remembers the pose it started from, since it is already applied), and retries the blocker. Before PR \#1018 the advance move's path was wrong and the move was applied a second time when it was emitted. Advancing frees the node R was on, which can give the blocker somewhere to go. If that still fails, it retries with `with_prior_dests(blocking_tray_id, {})`: the blocker **may now park on the critical path**. That is allowed because the loop re-scans afterwards, so a blocker parked ahead of R is simply found and moved again. If even that fails, the job fails with “Failed to find open space for blocking tray t…”.

**Turning the answer into events.** `required_moves` (any prerequisite moves, possibly an advance of R) plus a new `TrayMove` for the blocker, which occupies the whole root path, are applied to `state.working_state` in order (the advance is not applied again; a move that cannot be applied now fails the tray assignment) and added to `ctx->event_dag`, each depending on the one before (`last_move`). Each also depends on the previous move of the same tray (`ChainTrayEvent`, using `state.last_event_by_tray`) and on whichever earlier events used its occupied poses (`OrderAfterPriorOccupants`, which asks `occupancy_history.GetBlockers`). Each pose is then registered with `occupancy_history.AddOccupant`; since PR \#1018 an error from either call (a location outside the garage graph) fails the stage instead of reading as "no blockers". The blocker's move is then made a prerequisite of the root move: `ctx->event_dag.AddDependency(new_move, event)`. Finally the loop walks the remaining critical path again, asks `collision_table_.Query` which trays still collide with it, and starts over with that list. The loop ends when the path is clear.

### Filling a blank tray id: `AssignEmptyTrayToMove`

Some tray moves are created with a destination but no tray; a `READY_FOR_INSERT` job, for example, asks for “an empty tray into bay B21” without naming one. Before such a move can be planned, tray assignment must choose which empty tray to bring, and `AssignEmptyTrayToMove` makes that choice. `AssignTrays` calls it for every event with a blank tray id, and `ExpandReadyForInsertJob` calls it earlier, during its own fill pass (`AssignTraysToBayFillMoves`).

``` cpp
// tray_assignment.cpp:353. Called from AssignTrays (:63) and from AssignTraysToBayFillMoves
// (job_expansion.cpp:798), ExpandReadyForInsertJob's fill pass.
[[nodiscard]] stdx::Result AssignEmptyTrayToMove(TrayMove& move, const DiscreteGarageState& working_state) const;
```

| Dir              | Name            | Type                         | Meaning                                                                                                                                      | In the example below                                                                                                                 |
|------------------|-----------------|------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| in               | `this`          | `const Scheduler*`           | Fixed planner data, read only: `motion_graph_`, `collision_table_`, `cost_model_`, `layout_`                                                 | Pecos layout                                                                                                                         |
| in / **changed** | `move`          | `TrayMove&`                  | The event with the blank tray id. Must already have a destination. On success its tray id is set and its destination heading may be adjusted | `{tray_id: ?, dest: {node_id: 21, heading: -90}}` becomes `{tray_id: 23, dest: {node_id: 21, heading: -90}}` (tray 23 starts at P23) |
| in               | `working_state` | `const DiscreteGarageState&` | The garage as it will be when this event runs (all earlier events applied). Only read                                                        | T23 (empty) at `P23`, loaded trays elsewhere                                                                                         |
| out              | return          | `stdx::Result`               | nothing on success, or the reason as a string                                                                                                | success                                                                                                                              |

![AssignEmptyTrayToMove](figures/55_assign_tray_id_empty.svg)

`AssignEmptyTrayToMove` on a `READY_FOR_INSERT` job. The job asked for “an empty tray into `B21`”, so its `TrayMove` has a destination but no tray. Step through the method: the helper checks the destination, builds a filter that ignores every tray and AGV, then searches **outward from the destination** (numbers show the order nodes are reached) and stops at the first tray without a payload, T23 at `P23`. Loaded trays such as T20 and T24 are passed over, and T15, also empty, is farther away. It writes T23 into the same event and adds no events or edges. The heading stays as it is, and the main blocking-tray loop then plans T23's path to the bay. The last two steps play the completed event with an illustrative AGV-1, which carries T23 into the bay. Search order is illustrative.

How it works, step by step:

1.  **Require a destination.** A move with neither field set cannot be resolved: “Can't resolve a tray move with no tray id or dest”. A destination pose that is not in the graph fails too.
2.  **Start the search at the destination.** The question is “which empty tray is cheapest to bring *to where one is needed*”, so the source vertex is the destination pose (`{node_id: 21, heading: -90}`, B21: B21 lists heading 90 with `faces_reciprocal: true`, so its inbound heading is −90), not any tray: the open-space search run backwards.
3.  **Ignore everything movable.** `BuildImmobileTrayFilter(TRAY, working_state, {})`, which calls `BuildStaticObstacleFilter(TRAY, motion_graph_, working_state, collision_table_, all trays, all AGVs, {})`, makes every tray and AGV transparent (how the filter is built: [section 7.3](#mp-static-filters)). Only static obstacles (disabled nodes and entities, closed bays, nodes the tray footprint cannot use) block the search, so a buried empty tray can still be chosen; the main loop will clear the way afterwards.
4.  **Search.** `EmptyTraySearchEnvironment(motion_graph_, collision_table_, working_state, cost_model_, path_filter)` treats a vertex as a goal when it holds a tray with no payload. The environment inherits the blocking-tray search's costs: each edge costs its trapezoid time plus 30 s for every tray it crosses. `SingleSourceSearch` expands vertices by cost, so the first goal reached is the cheapest to reach, not necessarily the fewest hops. No goal → “Failed to find empty tray to move to \<dest\>”. The environment and the engine are explained in [section 7.4](#mp-tray-searches).
5.  **Read the tray.** `working_state.GetTrayOnNode(node_id_of(target))` → `move.SetTrayId(tray.id)`.
6.  **Avoid pointless rotation.** If the tray's heading is the destination heading or its reverse (`IsSameOrOppositeHeading`, the scheduler's own wrapper in `utils.hpp`) but not equal, the destination heading is changed to the tray's heading (an empty tray has no front). The `UseEvChargeHeading` step that followed, the `576_eccles` exception, was deleted in PR \#1018.

Three consequences are easy to miss:

- **Nothing is reserved.** The helper does not apply the move or touch `occupancy_history`. T23 is “taken” only because `AssignTrays` continues straight into the main loop and applies the move to `working_state` there; a later event will then see T23 in the bay.
- **Distance is measured from the bay, not from the AGV.** The chosen tray minimises travel time from the destination plus 30 s per tray in the way, so a near tray behind several blockers can lose to a farther free one. Where the AGV is does not matter.
- **The search repeats work.** The main loop runs a second search (the critical path) over roughly the same ground.

### Filling a blank destination: `AssignDestinationAndUnblockingMoves`

Other tray moves are created with a tray but no destination, such as the move that takes an empty tray out of a bay during a `RETRIEVE`, or the move that sends a car's tray into storage after an `INSERT`. `AssignDestinationAndUnblockingMoves` chooses where such a tray goes and adds moves for any trays in its way. `AssignTrays` is its only caller, and once it returns, the main blocking-tray loop is skipped for that event.

``` cpp
// tray_assignment.cpp:398. Called only from AssignTrays (:70); the caller then `continue`s.
[[nodiscard]] stdx::Result AssignDestinationAndUnblockingMoves(
    PlanContextSPtr ctx, TrayAssignmentState& state, const std::shared_ptr<ScheduleEvent>& event) const;
// Inside: auto move = dynamic_cast<TrayMove*>(event.get());
```

| Dir              | Name                       | Type                                                           | Meaning                                                                                                                                                                              | In the example below                                                                                                |
|------------------|----------------------------|----------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| in               | `this`                     | `const Scheduler*`                                             | Fixed planner data, read only: `motion_graph_`, `collision_table_`, `cost_model_`, `layout_`                                                                                         | Pecos layout                                                                                                        |
| in / **changed** | `ctx`                      | `PlanContextSPtr`                                              | Changed: `ctx->event_dag` (new blocker moves and edges) and `ctx->first_event_by_tray`                                                                                               | +1 event, +1 edge                                                                                                   |
| in / **changed** | `state.working_state`      | `DiscreteGarageState`                                          | Every new move and then `move` itself are applied to it                                                                                                                              | T23 now at `P24`, T21 at `P23`                                                                                      |
| in / **changed** | `state.occupancy_history`  | `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>`       | Gains the poses used by the new blocker moves                                                                                                                                        | `P23`, `P24`                                                                                                        |
| in / **changed** | `state.last_event_by_tray` | `std::unordered_map<uint16_t, std::shared_ptr<ScheduleEvent>>` | Per-tray “latest move so far”, updated for each new move and for `move`                                                                                                              | `[23]`, `[21]`                                                                                                      |
| in / **changed** | `event`                    | `const std::shared_ptr<ScheduleEvent>&`                        | The event with the blank destination; the method views it as a `TrayMove*` (`move`). Must have a tray id. On success its destination is set, and it is the target of `AddDependency` | event 1: `{tray_id: 21, dest: ?}` becomes `{tray_id: 21, dest: {node_id: 23, heading: 90}}` (tray 21 starts in B21) |
| out              | return                     | `stdx::Result`                                                 | nothing on success, or the reason as a string                                                                                                                                        | success                                                                                                             |

![AssignDestinationAndUnblockingMoves](figures/56_assign_dest_untargeted.svg)

`AssignDestinationAndUnblockingMoves` on a `RETRIEVE` job. Before the car can come out, the empty tray T21 must leave bay `B21`, but the job did not say where to, so the event is `T21: B21 → ?`. Step through the method: `ResolveBlockingTrays` works on a private copy of the garage and searches for open space from the bay. Its first answer, `P24` (red), is behind T23, so with `W41`, `W22` and `P23` off-limits it moves the blocker T23 one stall **deeper** into `P24` (2), then searches again and finds `P23` free and close (3). The helper writes `P23` into the original event, adds T23's move as a new event, and adds the edge “T23's move → T21's move”. T9, stashed on waypoint `W25` by an earlier plan, is the tier-2 case described below. The last four steps play the result with an illustrative AGV-1: T23 moves to `P24`, then T21 moves from the bay into `P23`. Search results are illustrative; the real cost of a path is its trapezoid travel time plus 30 s per tray crossed ([section 7.4](#mp-tray-searches)).

The helper is a thin wrapper; the real work is done by `ResolveBlockingTrays`. In order:

1.  **Check inputs.** The move must have a tray id, and that tray must exist in `state.working_state`.
2.  **Decide whether heading matters.** `is_retrieval_heading_enforced = payload_opt.has_value()`, the tray's payload in `state.working_state`. A tray with a car must be parked facing the way it will later leave (the node's *retrieval heading*); an empty tray need not.
3.  **Find a destination and the moves needed to reach it**: `ResolveBlockingTrays(state.working_state, {.tray_id = tray_id, .is_retrieval_heading_enforced = payload_opt.has_value()}, move->GetJobIndex())`. No tray is immobile and no pose is illegal, because this tray has no critical path to protect; `is_waypoint_stash_allowed` keeps its default `true`. No destination → “Failed to find open space for t\<id\>”.
4.  **Fix the heading** (only for a plain parking node, `IsParkingWithoutBayOrCharger`; not for bays or VECS). Empty tray: keep its current heading if the destination is on the same axis (`KeepTrayHeadingIfEquivalent`). Loaded tray: `FindPreferredTrayHeadingForRetrieval(dest->node_id, payload_opt)`, if the node has one (the search has usually chosen that heading already). Then `move->SetDest(*dest)`. The `UseEvChargeHeading` step, the `576_eccles` exception, was deleted in PR \#1018.
5.  **Emit the extra moves.** For each `PlannedTrayMove {new_move, occupied_poses, …}` in `required_moves`, in order: apply it to `state.working_state`; `ctx->event_dag.AddEvent(new_move)`; add an edge from the previous required move (`last_move`); `ChainTrayEvent` adds an edge from this tray's previous move (`state.last_event_by_tray`), or records it in `ctx->first_event_by_tray` if it is the tray's first; for every pose in `occupied_poses`, add edges from earlier events that used that pose (`OrderAfterPriorOccupants`) and register the pose (`occupancy_history.AddOccupant`); register the tray's source pose too.
6.  **Finish the original move.** Apply `move` to `state.working_state`, add `last_move → event` so the original move waits for the last blocker move, and chain it with `ChainTrayEvent`.
7.  **Return**, and the caller `continue`s: the main blocking-tray loop does not run for this event, because `ResolveBlockingTrays` already cleared the way.

Two details differ from the main loop. First, step 5's `new_move`s get occupancy edges, but the **original move itself does not**: its source and destination poses are not checked with `OrderAfterPriorOccupants` or registered with `AddOccupant`. Its ordering relies on the chain “last blocker move → event” and on edges the job method already added. Keep this in mind when debugging a missing edge after an untargeted move. Second, a blocker move produced by recursion has no occupied poses (see `BlockingTrayResolution` below), so it gets no path edges either; it is ordered only by the `last_move` chain.

#### Inside `ResolveBlockingTrays`

`ResolveBlockingTrays` (`tray_assignment.cpp:509`, declared public at `scheduler.hpp:118`) answers one question: “where can *this* tray go, and what has to move first?” It is used for a tray with no destination (above) and for a blocker in the main loop. It never changes the caller's state: it copies `base_state` into its own `working_state` and applies its trial moves there.

| Dir | Name                                    | Type                                                                       | Meaning                                                                                                                                     | Main loop passes        | `AssignDest…` passes               |
|-----|-----------------------------------------|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|------------------------------------|
| in  | `base_state`                            | `const DiscreteGarageState&`                                               | Starting state; copied, never changed                                                                                                       | `state.working_state`   | `state.working_state`              |
| in  | `request.tray_id`                       | `uint16_t`                                                                 | The tray that needs a home                                                                                                                  | the blocker             | the move's tray                    |
| in  | `request.immobile_trays`                | `std::set<uint16_t>` (default `{}`)                                        | Trays the search must route around and may never move                                                                                       | `{root}`                | `{}`                               |
| in  | `request.illegal_poses`                 | `VertexCollisionIdMap` (default `{}`)                                      | Vertices the tray may not park on                                                                                                           | root path + prior dests | `{}`                               |
| in  | `request.is_retrieval_heading_enforced` | `bool` (default `false`)                                                   | Park facing the retrieval heading                                                                                                           | `false` (default)       | `true` if the tray has a payload   |
| in  | `request.is_waypoint_stash_allowed`     | `bool` (default `true`)                                                    | Allow tier 2: park on a waypoint if no stall is reachable                                                                                   | `true` (default)        | `true` (default)                   |
| in  | `job_index`                             | `size_t`                                                                   | Stored in every `TrayMove` it creates                                                                                                       | root move's job         | move's job                         |
| out | `.dest`                                 | `std::optional<interfaces::msg::GaragePose>`                               | The tray's new destination, or empty on failure                                                                                             | K → `P19`               | `{node_id: 23, heading: 90}` (P23) |
| out | `.required_moves`                       | `PlannedTrayMoves` (`{move, occupied_poses, source_pose_if_applied}` each) | Moves that must happen first, in order, each with the poses it occupies (none for a blocker resolved by recursion); the caller applies them | `[]`                    | `[{T23 → P24, path}]`              |

It returns a `TrayDestinationPlan {dest, required_moves}` (`scheduler.hpp`), which replaced a `std::pair` in PR \#1018. Its loop, `while(!dest)`:

1.  **Search for open space for the tray**: `FindDestinationForRootTray(working_state, request, collision_entity)` (`:605`). Tier 1 accepts only free parking and EV-charge nodes (“free” meaning no tray on the node). If nothing is found and stashing is allowed, tier 2 retries accepting waypoints (with `is_retrieval_heading_enforced = false`). Like the critical-path search, this search may pass through any tray not in `immobile_trays` and reports the trays it passed through. It also returns `blocking_tray_illegal_poses`: `illegal_poses` plus every intermediate vertex of the tray's path, so the blockers will not be parked in its way. The target itself is left legal on purpose: the source comment says intermediate nodes are blocked so that a blocker cannot park there and make the outer loop cycle, while a blocker parked on the destination only makes the outer loop pick another one. Nothing found → return an empty plan.
2.  **No blockers on the way?** Then this is the destination: `dest = target`, and the loop ends.
3.  **Otherwise move one blocker.** For each blocker of that target, in order, call `FindBlockingTrayResolution(...)` (`:645`) until one succeeds. It searches open space for the blocker (parking first, then waypoints). If the blocker's best spot is free, it returns a `BlockingTrayResolution` with that spot and the path as `occupied_poses`. If the blocker is itself blocked, it **recurses** into `ResolveBlockingTrays` for the blocker with the current tray added to `immobile_trays` (so the chain cannot loop back), and returns the recursion's moves as `prereq_moves` with no `occupied_poses`. No blocker can be resolved → return an empty plan.
4.  **Apply the result to the private copy**: each prerequisite move, then a new `MakeTrayMove(job_index, blocker, spot)`. Append them to `required_moves` and go back to step 1.

Searching again after every single blocker move is what makes the result **dense**. The code comment says it “pushes them deeper instead of reparking them across the garage”. In [Figure 49](#bg-fig-56_assign_dest_untargeted), moving T23 one stall deeper makes `P23` free, and the next search picks it. The test `TrayAssignment.ResolvesBlockerChainRecursively` (`test/src/stages/tray_assignment_tests.cpp`, on `275_sunrise_b`) exercises a chain in which the root tray's only way out passes a blocker that is itself blocked.

A **tier-2 waypoint stash** (T9 on `W25` in [Figure 49](#bg-fig-56_assign_dest_untargeted)) is a deliberate half-solution: the tray is left on a travel node so the current plan can go ahead, and a later `CLEAN_GARAGE` job runs `ReparkWaypointStashedTrays`, which plans an untargeted move for every stashed tray and so comes back through this same helper.

### Occupancy becomes dependencies: `occupancy_history`

Choosing destinations and moving blockers decides where trays go, but not yet when a move may enter space that an earlier event uses. `TrayAssignmentState::occupancy_history` (called `freeing_moves` before PR \#1018) records which events have used each pose, so that tray assignment can add an edge from those events to any later move through a colliding pose. The figure shows how the records fill up and become edges.

![freeing_moves](figures/28_freeing_moves.svg)

`occupancy_history` is a `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>`. Every event that used a pose (a source pose, every pose on a path, a bay pose touched by a transition) is recorded. A later move through a colliding pose gets an edge from each recorded event. The checker uses `collision_table_`, so “colliding” means overlapping footprints, not just equal node ids. Step through to watch the records fill up while each tray glides to its new spot in `working_state` (a dashed arrow previews the move one step earlier), then see `GetBlockers` (called by `OrderAfterPriorOccupants`) turn the records into the three edges into e2, and finally T17 reach `B21` once e2 is applied.

Two pieces of bookkeeping leave this stage:

- `state.last_event_by_tray` (in the stage's `TrayAssignmentState`) chains successive moves of the same tray through `ChainTrayEvent`.
- `ctx->first_event_by_tray[tray_id]`, set by `ChainTrayEvent` for a tray's first move, remembers the **first** move that takes each tray off its initial node. `AssignAgvs` uses it (`OrderAfterTraysOnPath`) so an AGV that must drive through that node waits for the tray to leave. Using the *last* move instead would create a cycle when one AGV moves the same tray twice (the old `scheduler.hpp` said so in a comment).

`AssignTrays` deliberately does **not** call `RemoveRedundantEdges()` at the end; the TODO in `Plan()` says calling it after tray assignment breaks AGV assignment.

## AGV assignment: `AssignAgvs`

Now every `TrayMove` knows *what* moves where. `AssignAgvs(ctx)` (`agv_assignment.cpp:100`, with its helpers in the same file) decides *which AGV* does each one and adds the AGV's own events. Its working data is an `AgvAssignmentState`: `working_state`, the last event of each AGV (`last_event_by_agv`), the last AGV seen on each node (`last_agv_by_node`), and the timing maps `busy_duration_by_agv` and `earliest_start_by_event`. It works on `pending_events`, a copy of `ctx->event_dag` that it consumes from the roots down:

1.  **Drain non-tray roots** (`ApplyNonTrayRootEvents`). Apply every root that is not a `TrayMove` (bay and VECS transitions, pre-existing `AgvMove`s) to `working_state`; for an `AgvMove`, add its duration (`ComputeAgvMoveDuration`) to the AGV's busy time, chain it per AGV (`ChainAgvEvent`) and order its arrival after the node's previous occupant (`OrderArrivalAfterPriorOccupant`); remove them from the copy. Repeat until only `TrayMove` roots remain, so the matcher sees every eligible move at once (the source comment: non-tray roots “can expose tray-move roots that BottleneckAssignment must see together”). Since PR \#1018 an AGV move with no path fails the stage instead of counting as zero time.
2.  **Cost every (AGV, root move) pair** with `ComputeAgvAssignmentEdgeCosts`, which calls `ComputeAgvAssignmentCost`. Pairs are infeasible when the AGV carries a different tray, has no path, or is trapped in a bay that is not `READY_TO_RETRIEVE`.
3.  **Match** with `BottleneckAssignment` and order matched AGVs that stand at each other's pickups with `BuildAgvOrderDag` (`FindAssignedAgvsBlockingPickup`). A cycle in that order now fails the stage (“the assigned AGVs block each other's pickups”); before PR \#1018 it threw, and nothing in `Plan()` caught it.
4.  **Expand** each match into events (`AssignAgvToTrayMove`) and remove the matched `TrayMove` from the copy.
5.  Repeat until the copy is empty, then run `OrderAgvMovesAfterBlockingAgvs`, `RemoveRedundantEdges()`, and `OrderAllTransitionsAroundAgvLifts` for bay and VECS transitions.

![AGV matching](figures/29_agv_matching.svg)

Matching AGVs to root tray moves. Each edge is one feasible pair with its estimated cost; AGV-3 carries another tray, so it has no edges. Bottleneck matching minimises the **worst** single cost, so it can prefer a pairing with a higher total. Step through the cost table entry by entry, then watch the allowed cost rise until both moves are matched. The last two steps play the result: AGV-1 drives to T15 for e4, then AGV-2 drives into `B21` under T21 for e1. Costs are illustrative.

The cost of assigning AGV **i** to tray move **j** is

c\_{ij}=\max\\\left(t_i^{\mathrm{occupied}}-t_j^{\mathrm{ready}},\\0\right)+t\_{ij}^{\mathrm{approach}}+t\_{ij}^{\mathrm{lift}},

where cost **c\_{ij}** \[s\] is the estimated time until the tray is lifted, **t_i^{\mathrm{occupied}}** \[s\] is how long AGV **i** is already busy (`busy_duration_by_agv`), **t_j^{\mathrm{ready}}** \[s\] is the earliest time move **j** can start given its parents (`earliest_start_by_event`, filled by `PropagateEarliestStartToChildren`), **t\_{ij}^{\mathrm{approach}}** \[s\] is `ComputeTravelDuration` from the AGV's pose to the tray's node (at the AGV's heading if it is the same or opposite to the tray's, otherwise the tray's), and **t\_{ij}^{\mathrm{lift}}** \[s\] is the lift-up time when the AGV is not already holding the tray; the last two are `ComputeAgvPickupDuration`. **Caveats:** `busy_duration_by_agv` starts at zero for every AGV (a `TODO(any)`: “Start from the time until the AGV finishes its assigned events”), so the busy term only reflects work assigned earlier in the same call. The approach time is a single-AGV estimate (`FindPosePath` + `ConvertPosePathToTrajectory`; [section 7.5](#mp-pose-path)): it ignores waiting for other AGVs and wheel turns, which only CHUGG accounts for ([section 23.2](#bg-the-cost-model)).

![AGV approach](figures/15_agv_approach_and_pickup.svg)

Approach, lift, carry and lower. Step through as hypothetical AGV-1 at charger `C10` drives, one edge per step, to tray T15 at `P3` via `10 → 9 → 11 → 6 → 3`, passing under the empty stall `P6`; a dashed arrow previews each edge one step before AGV-1 drives it. AGV-1 then lifts T15, carries it (T15 rides along) to an example destination (`P2`) and lowers it. The strip restates each step as a simplified event as it happens. The route is a graph walk, not a recorded run.

![AGV event expansion](figures/30_agv_event_expansion.svg)

What one assignment adds: `ScheduleAgvMoveToPickup` (skipped if the AGV is already on the tray's node at the same or opposite heading), a lift (`ScheduleAgvLiftChange`), `SetAgvId` on the `TrayMove`, and a lower. The first event gets edges from four sources: the AGV's previous event (`ChainAgvEvent`), the first move of any tray parked on its navigation path (`OrderAfterTraysOnPath`), the previous occupant of the destination node (`OrderArrivalAfterPriorOccupant`), and the pickup moves of matched AGVs it must follow (its parents in the AGV order DAG). Step through to see the events created one at a time, then each kind of incoming edge, then the cost that is passed on to the children.

``` cpp
// Where: Scheduler::AssignAgvs(PlanContextSPtr ctx) const, agv_assignment.cpp:100, after BottleneckAssignment.
//   root_event_by_agv -> std::unordered_map<uint16_t, std::optional<ScheduleEventSPtr>>: AGV id -> matched root event
//   agv_order_dag     -> Dag<uint16_t>: matched AGVs, with an edge when one stands at the other's pickup
//   state             -> AgvAssignmentState: working_state, last_event_by_agv, busy_duration_by_agv, ...
for(const auto& vertex : agv_assignment_order_opt.value()) {
  const uint16_t agv_id = *agv_order_dag.GetNode(vertex);
  const auto& root_event_opt = root_event_by_agv.at(agv_id);
  if(!root_event_opt.has_value()) {                 // this AGV got nothing this round
    continue;
  }
  const auto& root_event = *root_event_opt;
  const auto assignment_duration_or = AssignAgvToTrayMove(ctx, state, agv_id, root_event, agv_order_dag);
  if(!assignment_duration_or) {
    return stdx::Unexpected(assignment_duration_or.error());
  }
  pending_events.Remove(root_event);
  PropagateEarliestStartToChildren(root_event, *assignment_duration_or, ctx, state);
  state.busy_duration_by_agv[agv_id] += *assignment_duration_or;
}

// Inside AssignAgvToTrayMove (agv_assignment.cpp:290), error checks and cost sums left out:
if(agv.tray_id != tray.id) {
  if(tray.pose.node_id != agv.pose.node_id || !IsSameOrOppositeHeading(agv.pose.heading, tray.pose.heading)) {
    ScheduleAgvMoveToPickup(ctx, state, agv_id, root_event, agv_order_dag);  // AgvMove (pose) + its edges
  }
  ScheduleAgvLiftChange(ctx, state, agv_id, true, root_event->GetJobIndex());   // AgvMove (lift)
}
tray_move->SetAgvId(agv.id);                        // edits the shared event object
ChainAgvEvent(*ctx, state, agv_id, root_event);      // edge from the AGV's last event
OrderArrivalAfterPriorOccupant(ctx, state, tray_move->GetDest().value().node_id, agv_id, root_event);
root_event->ApplyTo(state.working_state);
ScheduleAgvLiftChange(ctx, state, agv_id, false, root_event->GetJobIndex());    // AgvMove (lower)
```

### Repairing paths after assignment

Once every tray move has an AGV, one more pass checks that each AGV reposition can reach its target in the order in which the DAG will be replayed. `OrderAgvMovesAfterBlockingAgvs` (`agv_assignment.cpp:370`) performs this check, calling `AddNextMissingAgvMoveOrder` once per pass, and adds an edge where another AGV stands in the way; the reason the pass is needed follows the figure.

![AGV path repair](figures/31_agv_path_repair.svg)

`OrderAgvMovesAfterBlockingAgvs` replays the final topological order. When an AGV reposition has no collision-free path only because another AGV's body is in the way, it adds one edge from that AGV's next departure to the blocked move (unless that would form a cycle) and starts over, at most 256 times (`kMaxAgvMoveOrderPasses`). Tray and disabled-node obstructions are left for `ValidateEventSequence` to report. Step through the five checks of `OrderAgvMoveAfterBlockerDeparture()` on one blocked move, then play the repaired order: AGV-2 first leaves `W13` for `P15`, and only then AGV-1 drives through to `W8`.

This pass exists because `AssignAgvs` builds dependencies in its own serial assignment order, which can differ from the order the DAG is eventually replayed in; the declaration says so: “AssignAgvs misses these orderings: it does not know the final topological order.” Since PR \#1018 an event that fails to apply during this replay fails the stage instead of being ignored.

`OrderAllTransitionsAroundAgvLifts(ctx)` runs last and calls `OrderTransitionAroundAgvLifts(ctx, event, node_id)` (`agv_assignment.cpp:644`) for every bay and VECS transition. It moves dependencies from tray moves onto the AGV's lift and lower events: a transition that waited for a tray to arrive now waits for the **lower** after it, and a tray move out of the bay waits for the transition before its **lift**. To find a tray move's source it replays the DAG up to that move (`ComputeStateBefore`); since PR \#1018 a replay that fails is reported instead of returning a partial state.

## `RemoveRedundantEdges()` and `ValidateEventSequence`

Back in `Plan()`, `ctx->event_dag.RemoveRedundantEdges()` (called `Reduce()` before PR \#1018) removes redundant edges. It returns an `stdx::Result` and fails every expanded job with “Failed to reduce the event graph: The graph must be a DAG.” if the graph has a cycle. A `TODO(any)` above the call notes that planning may fail without it, and that calling it after tray assignment instead breaks AGV assignment; [section 21.1](#bg-inside-solvesequential) shows a code path in CHUGG that would explain the first part. Then `ValidateEventSequence(ctx)` (`validation.cpp:18`) replays the DAG in topological order on a fresh copy of `initial_state` and checks each event **before** applying it:

| Event                        | Check                                                                                                                                                                                                                                                              |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `BayTransition`              | the bay's ODP (overdrive plate) area is free (`IsBayOdpAreaClear`: `BuildStaticObstacleFilter` for `BAY_ODP`)                                                                                                                                                      |
| `AgvMove` with a destination | `ValidateMoveDestinationAndPath` (`validation.cpp:72`): destination exists, is not disabled (keep-out filter of the AGV's footprint; a missing filter now fails with its own message), is not occupied, and a path exists (`FindPosePath`), ignoring only this AGV |
| `AgvMove` lift change        | only that `ApplyTo` succeeds                                                                                                                                                                                                                                       |
| `TrayMove`                   | has a destination, and `ValidateMoveDestinationAndPath` with the carrying AGV (`tray.agv_id`) and the tray itself ignored                                                                                                                                          |

The comment at the call in `Plan()` explains the motivation: “The motion planner fails ungracefully on bad event ordering, so check it first”, so a cheap discrete replay catches most problems with a readable message (“Pre-motion planning sanity check failed: …”) first. It is the last step of task planning: from here the event DAG is final, and motion planning hands it to CHUGG ([section 1](#bg-motion-planning-and-the-response)). CHUGG replays it once more in `InitializeEventOrder` and throws, rather than failing gracefully, if that replay breaks.

**Where `RemoveRedundantEdges()` runs matters.** It runs at the end of AGV assignment and again in `Plan()`, and the code does not say why that placement is needed ([section 13](#pr-risks-that-must-not-be-silently-fixed), risk 2); [Section 21.1](#bg-inside-solvesequential) gives a reading of CHUGG's code that would explain the motion-planning case. Risk 3 in the same list gives a likely reason for the tray-assignment case: two AGV-assignment helpers look only at direct edges, which `RemoveRedundantEdges()` may replace with longer paths. A test shows the visible effect: in `AgvAssignment.ChainsThreeMovesAcrossTwoAgvs` (`test/src/stages/agv_assignment_tests.cpp`), after `AssignAgvs` the direct edges `tray_move_1 → tray_move_2` and `tray_move_2 → tray_move_3` that the test added are gone (`EXPECT_FALSE(ctx->event_dag.HasDependency(...))`), because the AGV chains and node-arrival edges now imply them. `HasDependency` checks a direct edge only, so after `RemoveRedundantEdges()` it is the wrong question for “must a finish before b?”.

## Bays, VECS and VRCs

The bay, VECS and VRC rules cut across the stages above: job methods choose bays and stop chargers, tray assignment avoids closed bay doors, and the action graph adds VRC trips. This section collects them in one place.

### Bays and rebalancing

Bays are where customers leave and collect their cars, so the scheduler keeps some bays ready for insert and others ready for retrieve. This subsection covers the bay commands the scheduler issues, how `ClassifyBay` classifies each bay, and how `ComputeBayRebalancingActions` chooses the bays that a `TYPE_REBALANCE_GARAGE` job switches.

![Bay logic](figures/33_bay_logic.svg)

The three bay commands the scheduler issues, the `ClassifyBay` rules from `bay_rebalancing.cpp`, and a worked example of `ComputeBayRebalancingActions`. Step through it: first the commands and the classification rules, then the example one loop at a time. Each loop walks `bay_prioritization` in the direction shown, keeps or picks bays, and updates how many insert-ready and retrieve-ready bays are still wanted. Other bay states are reached through bay or customer activity outside this package.

Bay classification and rebalancing live in `bay_rebalancing.hpp` and `bay_rebalancing.cpp`. `ClassifyBay(planned_bay_state, is_tray_in_bay, is_payload_in_bay)` names what each bay is ready for, still needs or is doing (the names changed in PR \#1018):

| Planned bay state                                                                                                    | Tray and payload in the bay | `BayClassification`           |
|----------------------------------------------------------------------------------------------------------------------|-----------------------------|-------------------------------|
| `READY_TO_INSERT`                                                                                                    | empty tray                  | `INSERT_READY`                |
| `READY_TO_INSERT`                                                                                                    | no tray, or a loaded tray   | `INSERT_NEEDS_EMPTY_TRAY`     |
| `PROCESSING_INSERT`                                                                                                  | loaded tray                 | `INSERT_IN_PROGRESS`          |
| `READY_TO_RETRIEVE`                                                                                                  | no tray                     | `RETRIEVE_READY`              |
| `READY_TO_RETRIEVE`                                                                                                  | any tray                    | `RETRIEVE_NEEDS_TRAY_REMOVAL` |
| `PROCESSING_RETRIEVE`                                                                                                | loaded tray                 | `RETRIEVE_IN_PROGRESS`        |
| any other, a processing state without tray and payload, a payload without a tray, or a disabled bay (`ClassifyBays`) |                             | `NOT_USABLE`                  |

The target fraction of usable bays that should be ready for insert is `target_insert_ready_bay_fraction_` inside the scheduler (the ROS parameter and the `set_bay_readiness_ratio` service keep the name `bay_readiness_ratio`). `CalculateDesiredBaySplit` returns a `DesiredBaySplit`: it rounds up (it biases towards insert because arriving customers cannot be detected), clamps, and never asks for more insert-ready bays than there are empty trays. `ComputeBayRebalancingActions` first counts each `RETRIEVE_IN_PROGRESS` bay as a future insert-ready bay (a finished retrieve leaves it ready to insert onto the tray left behind), then keeps bays already in a wanted state (`INSERT_READY`, `RETRIEVE_READY`), and only then picks bays to change, in `bay_prioritization` order for insert and reverse order for retrieve. Bays still left as `INSERT_NEEDS_EMPTY_TRAY` or `RETRIEVE_NEEDS_TRAY_REMOVAL` are made ready for retrieve. The classification `WILL_BE_RETRIEVE_READY`, which no bay was ever given, was deleted with its branch.

### VECS (EV charging)

A VECS sits on a node of type `TYPE_EV_CHARGE` (6, a node type of its own; its VECS id is the node id). Moving a tray off a VECS that is `CHARGING` first adds `VecsTransition CHARGING -> READY_TO_CHARGE` (`AddChargingStopBeforeTrayMove`, chained after the charger's previous event since PR \#1018); moving onto one is refused unless it is `READY_TO_CHARGE` (`CheckReparkDestination`). `ExpandChargePayloadJob` finds a VECS with `ResolveBlockingTrays`: for a payload with `ev_charge_requested`, the open-space search accepts only `EV_CHARGE` nodes at a heading between 0 and 90 ([section 7.4](#mp-tray-searches)); it does not look at the VECS state, and the job afterwards only checks that the node has a VECS before adding `READY_TO_CHARGE -> CHARGING`. A VECS in another state is therefore caught by the destination check of the `ExpandReparkTrayJob` call that moves the tray there, which fails the job.

### VRCs (lifts between floors)

Task planning creates no VRC events. An AGV move between floors is planned like any other move, and the scheduler adds the VRC commands later, to the action DAG, after motion planning ([section 6.3](#bg-vrcs-lifts-between-floors)). Assignment is not floor-aware either: trays, parking spots and AGVs are chosen by search cost alone, and a VRC ride is just another edge in those searches. The status of VRC support in every stage is summarised in the Layout file tab ([section 7](#ly-vrc-support-status)).
