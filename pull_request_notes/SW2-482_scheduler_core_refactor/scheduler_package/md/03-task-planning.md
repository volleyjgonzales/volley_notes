# 03 — Task planning: building the event DAG

*Stages 1–3 of the pipeline: everything that builds the event DAG. Job expansion turns each job into events, tray assignment fills in the trays and parking spots that expansion left open and moves blocking trays out of the way, and AGV assignment chooses an AGV for every tray move and adds its approach, lift and lower. `Reduce()` and a sanity check then finish the event DAG, which is the input of motion planning.*

This tab builds on the request messages, the reservation of the running schedule, the event classes, the event DAG and `ScheduleContext` from the Background tab (sections [6](#bg-ros-messages-and-services) and [11](#bg-event-types-and-polymorphism)–[13](#bg-schedulecontext-the-per-call-workspace) there). It starts with one job followed through all three stages, then takes each stage in turn. The single-agent searches that all three stages call come next, before the stages themselves, and the bay, VECS and VRC rules close the tab.

## The whole journey of one job

Stages 1–3 of the pipeline ([Figure 1](#bg-fig-01_pipeline)) build the event DAG. All three stages edit the same `ctx->events`, so an event created in one stage is completed or wrapped in another. Before the details of each stage, here is one retrieve followed through all three passes.

![Retrieve walkthrough](figures/26_retrieve_walkthrough.svg)

One `TYPE_RETRIEVE` job on Pecos, stage by stage. Step through it to watch the event DAG grow pass by pass; map numbers match event ids. Band 1: job expansion creates intent, including a move of the empty tray T21 out of the bay with no destination. Band 2: tray assignment gives T21 a destination and inserts a move for blocker T15, which sits on T17's critical path. Band 3: AGV assignment wraps every `TrayMove` in move → lift → carry → lower, and `AddDepsAfterAmiga` ties the bay transitions to the right lift and lower. The last six steps play the plan on the map: AGV-1 follows each dashed preview arrow in the next step, moving T15 to `P19`, T21 to `P23` and T17 into `B21`, while the band-3 row being executed is outlined. Destinations and AGV order are illustrative.

Read the bands as the order of the next sections: band 1 is job expansion ([section 15](#bg-job-expansion-from-jobs-to-events)), band 2 tray assignment ([section 16](#bg-tray-assignment-dotrayassignments)), band 3 AGV assignment ([section 17](#bg-agv-assignment-doagvassignments)). After band 3, `Reduce()` and the sanity check ([section 6](#bg-reduce-and-sanitycheckevents)) finish the event DAG. What happens to the finished DAG next is the subject of the [Motion planning](#doc-motion-planning) and [Action graph](#doc-action-graph) tabs; the Action graph tab follows a retrieve of the same shape through those last steps ([Figure 4](#ad-fig-87_adg_in_scheduler)).

## The single-agent searches in `motion_planner`

Task planning does not plan motions, but it needs answers that only a search can give: how long an AGV takes to reach a tray, which trays stand in a tray's way, where a tray can be parked, which empty tray is nearest, and where every AGV can hide. It gets them from single-agent searches in the `motion_planner` package, the same package as CHUGG. They plan for one AGV or tray at a time on a fixed snapshot of the garage and ignore everyone else's timing. The searches, their shared engine `SingleSourceSearch` and the static filters they read are explained with figures in [section 7](#mp-single-agent-searches):

| Search                                                                                      | Used in task planning by                                                                                      | Explained in                            |
|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| `SingleSourceSearch`, the engine                                                            | Every search below                                                                                            | [section 7.2](#mp-single-source-search) |
| `GetStaticFilter` and `GraphFilterProperties`                                               | Every search below; `ctx->disabledness_filters`                                                               | [section 7.3](#mp-static-filters)       |
| `BlockingTraySearchEnvironment`, `OpenSpaceSearchEnvironment`, `EmptyTraySearchEnvironment` | `DoTrayAssignments`, `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution`, `AssignTrayIdForEmptyMove`  | [section 7.4](#mp-tray-searches)        |
| `GetPosePath` and `ConvertPosePathToTrajectory`                                             | `GetJustMovingCost`, `IsMovePossible`, `MoveAgvToTrayPose`, `TryClearBlockedAgvMove`, `InitRetrievalHeadings` | [section 7.5](#mp-pose-path)            |
| `HideAgvs`                                                                                  | `PlanCleanGarageJob`                                                                                          | [section 7.6](#mp-hide-agvs)            |

CHUGG itself, and the edge-duration and heuristic tables it is built with (`GetEdgeDurations`, `GetAllPairsMinCost`), are in the Motion planning tab ([section 2](#bg-chugg-the-motion-planner)).

This split matters for the refactor: tray and AGV assignment choose destinations and agents with single-agent costs that ignore waiting, and only CHUGG discovers the waiting. An assignment that looks cheap can therefore produce a slow plan.

## Job expansion: from jobs to events

**Job expansion** is the first planning stage inside `Plan()`. It turns each line of the request ("retrieve this car", "move this tray") into a handful of `ScheduleEvent` objects in `plan_ctx->events`, connected by dependency edges. It decides **what** has to happen and **in which order**. It does not decide **how** (no paths, no timing) or **by whom** (no AGV is chosen, except in one case).

A useful picture: each job method is a recipe. It writes a few cards (events) onto a shared board (the event DAG) and ties strings (edges) between cards that must happen one after another. Later stages fill in the blanks on the cards and add more cards and strings.

This section is long because every job type has its own recipe. Read it in this order:

| Part                                                                                                                          | What you learn                                                                                |
|-------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| [14.1](#bg-what-a-job-is)–[14.3](#bg-the-shape-of-every-job-method)                                                           | What a job is, the loop in `Plan()` that dispatches it, and the shape every job method shares |
| [14.4](#bg-every-job-sees-the-garage-through-working_state)–[14.5](#bg-where-the-edges-come-from)                             | How a job method sees the garage (`working_state`) and the three rules that add edges         |
| [14.6](#bg-job-methods-are-built-from-a-few-shared-pieces)                                                                    | Which job methods are built from which others                                                 |
| [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob)–[14.17](#bg-type_rebalance_garage--planrebalancegaragejob) | Every job type, one at a time, each with a 2D garage example                                  |
| [14.18](#bg-gotchas-2)–[14.19](#bg-cheat-sheet-and-self-check)                                                                | Gotchas, a one-page cheat sheet and questions to check yourself                               |

### How to read the job figures

Sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) each have one figure with the same four parts:

1.  **The map** is the Pecos layout, showing the garage as the job method sees it when it starts (`working_state`). Trays, cars and AGVs are hypothetical. **Curved dashed arrows are intent, not routes**: job expansion plans no paths. A `?` bubble means the destination is left empty for `DoTrayAssignments()` to fill. Numbered circles match the event numbers.
2.  **The request card** lists the `SchedulerJob` fields the method reads, the `job_index` it receives and the exact call `Plan()` makes.
3.  **The event column** lists the events the method appends, numbered in creation order. Every arrow is an edge the method adds, labelled with the rule that added it (A, B or C, see [14.5](#bg-where-the-edges-come-from)).
4.  **The step table** is the method body as numbered steps, with what happens in this example and the result: `adds n` means event *n* is created, `skipped` means the branch does not apply, red means the job fails there.

### What a job is

A job is one `interfaces/msg/SchedulerJob` message (C++ alias `SchedulerJobMsg`) in `request_data.pending_jobs`. Which side writes each field, and which arguments each job type reads, is laid out in the Background tab ([section 6.4](#bg-schedulerjob-what-to-do-and-what-happened)). Job expansion needs only `type`, which picks the job method, and the arguments of that type, which become the method's parameters. Each job figure below repeats the fields its method reads in its request card.

On the way out, each job becomes a `ScheduledJobDataMsg`: the original job plus `node_indices`, the positions of its action nodes in the response schedule. A failed job is a `ScheduledJobDataMsg` built by `FailJob()`, with `job.state = STATE_ERROR`, `job.note = <message>` and `job.retain_job` set when Dispatch should keep it and retry.

### The loop in `Plan()`

This section follows the loop in `Plan()` that offers each pending job to its job method, one job at a time. It covers where the loop sits within one `Plan()` call, how every event is tagged with the `job_index` of the job that created it, and why the loop is built this way.

#### What the code does, in order

Job expansion is step 3 of the nine steps of one `Plan()` call (Background, [section 10](#bg-one-plan-call-step-by-step)). By the time it runs, `initial_state` exists, everything the running schedule uses is reserved, and `disabledness_filters` is built; after it, all successful jobs are planned together by tray assignment, AGV assignment, the sanity check and motion planning. Each job method writes its events **directly into** `plan_ctx->events` (it does not return them) and returns only success or failure.

The loop itself is in [section 10](#bg-one-plan-call-step-by-step). Two details of it matter here: each job method is called with `plan_ctx->scheduled_jobs.size()` as its `job_index`, and the job is pushed onto `scheduled_jobs` only if the method succeeds; a failed job is reported at once through `FailJob`.

#### How `job_index` works

**One job almost always creates several events.** A RETRIEVE creates up to five (stop charging, open the bay, move the tray already in the bay out, move the car's tray in, hand the car over); a REPARK_TRAY creates one (two if the tray must first stop charging); a REBALANCE_GARAGE creates a few per bay it switches. Every one of them belongs to the same job. Sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) list what each job type creates.

So every event needs to remember which job it belongs to, and the response needs to say "this action is part of job X". The code does not store the job's `guid` in the event. Each event is constructed with a small integer, the `job_index`, and the job is looked up from it at the end:

``` cpp
// inside PlanRetrieveJob(ScheduleContextSPtr ctx, const GuidMsg& payload_id, size_t job_index)
auto bay_transition = std::make_shared<BayTransition>(job_index, *bay_opt, cmd);  // tagged with job_index
...
PlanReparkTrayJob(ctx, payload_opt->tray_id, job_index, false, dest_pose);        // its TrayMove: same tag
...
auto process = std::make_shared<BayTransition>(job_index, *bay_opt, cmd);         // same tag again
```

The relationship is **one job → many events → many actions**:

| Level   | How many                                                                     | How it points to the job                                                                                                                                                                                                                      |
|---------|------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Job     | one entry in `plan_ctx->scheduled_jobs`                                      | its position in that list is the `job_index`                                                                                                                                                                                                  |
| Events  | all events the job method creates, **plus** the ones later stages add for it | `event->GetJobIndex()`. Tray assignment builds blocker moves as `TrayMove(move->GetJobIndex())` and AGV assignment builds approach moves as `AgvMove(root_event->GetJobIndex(), ...)`, so they inherit the index of the move that needed them |
| Actions | one `ActionNode` per motion of those events                                  | `job_id` = the job's `guid`; the job's `node_indices` list their positions                                                                                                                                                                    |

- **What the number is.** `job_index` is the job's position in `plan_ctx->scheduled_jobs`, the list of jobs that have **succeeded so far**. It is not the loop counter (the job's position in `request_data.pending_jobs`).
- **How it is chosen.** Just before calling the job method, `Plan()` passes `plan_ctx->scheduled_jobs.size()`. If the method succeeds, `PushBackScheduledJob(job)` appends the job at exactly that position, so `scheduled_jobs[job_index]` is now this job. If it fails, nothing is appended and the next job is offered the same number.
- **How it is used.** When the response is built, `ToActionNode(motion, ctx->scheduled_jobs[event->GetJobIndex()].job.guid, event)` turns the index back into the job's `guid`. Rule B ([14.5](#bg-where-the-edges-come-from)) also compares indices to decide which events belong to the same job.

A worked example, the same one as in [Figure 27](#bg-fig-36_expansion_loop) below:

| Loop counter `i` | Job in the request    | `scheduled_jobs.size()` before the call = `job_index` | Result                                   | `scheduled_jobs` afterwards |
|------------------|-----------------------|-------------------------------------------------------|------------------------------------------|-----------------------------|
| 0                | RETRIEVE car on T17   | 0                                                     | success: one job, 4 events, all tagged 0 | `[RETRIEVE]`                |
| 1                | INSERT bay B7         | 1                                                     | fails, no events added                   | `[RETRIEVE]` (unchanged)    |
| 2                | REPARK_TRAY T19 → P24 | 1                                                     | success: one job, 1 event, tagged 1      | `[RETRIEVE, REPARK_TRAY]`   |

If the code used `i` instead, the REPARK's event would carry 2, and `scheduled_jobs[2]` would not exist.

![The expansion loop](figures/36_expansion_loop.svg)

The loop, one row per iteration: the code that runs, then `plan_ctx->scheduled_jobs`, `plan_ctx->events` and `result.scheduled_jobs` after it. Step through the loop: each iteration first computes `job_index = scheduled_jobs.size()` and calls the job method, then appends the job (or, on failure, pushes a `FailJob` into the result). In the events column each box is one event and each dashed group is everything one job-method call created: the RETRIEVE (job index 0) created four events, the REPARK_TRAY (job index 1) one, and the failed INSERT none, which is why the REPARK also gets index 1. The last steps follow the same index through later stages to the response.

If every job fails, `plan_ctx->scheduled_jobs` is empty and `Plan()` returns right after the loop with "No jobs succeeded to plan".

#### Why it is built this way

The code has no design document, so this is a reading of the structure, with the trade-offs it implies.

- **`Plan()` is a pure function of the request.** Nothing survives between calls except the fixed layout, graph and collision table. Dispatch owns the job queue and the live garage state and sends both every time. That keeps the scheduler simple to test (build a request, call `Plan()`, inspect the response) and lets Dispatch replan whenever something changes.
- **Jobs are expanded one at a time, in request order, each seeing the garage that earlier jobs leave behind** ([14.4](#bg-every-job-sees-the-garage-through-working_state)). That is a greedy approach: easy to reason about, and later jobs automatically build on earlier ones (a second move of the same tray starts where the first one ends). The cost is that request order matters and nothing tries another order: an early job can make a later one fail, and the later one is simply reported as failed.
- **Failure is per job during expansion.** One bad job does not sink the others, so Dispatch still gets a plan for everything that was possible. `retain_job` lets RETRIEVE say "try me again later" when no bay is free.
- **After expansion, everything is one problem.** All successful jobs share one DAG, so tray assignment, AGV assignment and motion planning can share AGVs and resolve conflicts across jobs. The flip side is in [section 10](#bg-one-plan-call-step-by-step): if any later stage fails, every pending job is failed.
- **A small integer instead of a pointer or `guid`.** Events are `planner_core` objects that know nothing about ROS messages. A `size_t` is the cheapest way to tag them and is enough for rule B's "same job?" test.

Known issues with this design (details in [14.18](#bg-gotchas-2)):

- **No rollback.** A job method that fails after adding events leaves them in the DAG. They keep the failed job's index, which the next successful job reuses, so they are executed as part of that job (or, if no later job succeeds, `scheduled_jobs[index]` reads past the end). `FailJob()` carries a TODO to strip them.
- **Index reuse makes logs confusing.** "Job index 1" means different requests at different moments of one `Plan()` call.
- **Order dependence without a retry.** The plan depends on the order Dispatch lists the jobs, and a failed job is not retried after the others are placed.
- **Duplicate failures.** When a later stage fails, `Plan()` fails every job in `pending_jobs`, including jobs already reported failed by the loop.

Possible directions (ideas, not plans): tag events with the job's `guid` instead of a position; take a snapshot of `events`, `last_entity_event` and `first_tray_event` before each job and restore it on failure; or plan each job into a separate small DAG and merge it only on success.

### The shape of every job method

All job methods are `const` members of `Scheduler` with the same skeleton. Here it is, with the types spelled out:

``` cpp
// Shape of BoolStringPair Scheduler::Plan<Type>Job(ScheduleContextSPtr ctx, <job fields>, size_t job_index) const
// this : const Scheduler*  (reads layout_, gg_, table_, cost_model_; changes nothing in itself)
// ctx  : the same ScheduleContextSPtr as plan_ctx in Plan(); the method edits *ctx

// (1) See the garage as all earlier events leave it ("Every job sees the garage ...")
volley::DiscreteGarageState working_state = ctx->initial_state;     // a copy
auto [success, message] = ctx->events.Apply(working_state);         // replay the whole DAG

// (2) Look up what the job names. Lookups return std::optional<...Msg>
std::optional<DiscreteBayStateMsg> bay_opt = working_state.GetBay(bay_id);

// (3) Check preconditions; return early with a message if one fails
if(!bay_opt.has_value() || bay_opt->disabled) {
  return std::make_pair(false, "...");
}

// (4) Create events. Fill in what is known now; leave the rest empty for later stages
auto bay_transition = std::make_shared<volley::BayTransition>(job_index, *bay_opt, cmd);  // cmd: BayCommandMsg

// (5) Add each event and wire its edges ("Where the edges come from")
ctx->events.AddEvent(bay_transition);
ctx->UpdateLastEntityEvent(bay_transition->GetGarageEntityId().value(), bay_transition);  // rule A
ctx->UpdateLeafDependencies(bay_transition, job_index);                                   // rule B

// (6) Or delegate part of the work to another job method, passing the SAME job_index
std::tie(success, message) = PlanReparkTrayJob(ctx, tray_id, job_index, /*allow_recip=*/true);

return std::make_pair(true, "");
```

What the four event types can carry at creation time:

| Event (`planner_core`) | Constructed with                                                                   | Can be left empty for later                         |
|------------------------|------------------------------------------------------------------------------------|-----------------------------------------------------|
| `TrayMove`             | `job_index` only; then `SetTrayId(id)`, `SetDest(pose)`, and rarely `SetAgvId(id)` | tray id (`? -> B21`), destination (`T21 -> ?`), AGV |
| `AgvMove`              | `job_index`, an `AgvPoseChangedMsg` (or a lift change)                             | nothing                                             |
| `BayTransition`        | `job_index`, the bay's `DiscreteBayStateMsg`, a `BayCommandMsg`                    | nothing                                             |
| `VecsTransition`       | `job_index`, a `VecsStateChangedMsg` (current and next state)                      | nothing                                             |

Only `TrayMove` has blanks. That is why the next stage is called *tray* assignment: it fills the blanks on `TrayMove`s, and [section 16](#bg-tray-assignment-dotrayassignments) explains how.

#### What a job method reads, changes and returns

The signatures make job methods look like functions that take a job and return a yes/no answer. They are not. Most of their output is written **into `*ctx` while they run**, and the return value only reports whether that worked. [Figure 28](#bg-fig-38_job_method_dataflow) shows this for `PlanRetrieveJob`; every `Plan<Type>Job` follows the same pattern.

![What PlanRetrieveJob reads, changes and returns](figures/38_job_method_dataflow.svg)

Data flow of one job method. Step through one call: blue, read-only inputs come in; grey, a local copy is built and thrown away at return; amber, members of the shared `ScheduleContext` that the method (and the job methods it calls) change in place: four new events, five edges and three `last_entity_event` entries; green, the return value, which only reports success. Red: requests sent to Dispatch while planning. The last step sketches a pure alternative.

The same information as a table, for `PlanRetrieveJob(ctx, payload_id, job_index)` called as the first job:

| Item                                      | Passed as                             | Read | Changed    | What happens                                                                                              |
|-------------------------------------------|---------------------------------------|------|------------|-----------------------------------------------------------------------------------------------------------|
| `*this` (`layout_`, `gg_`, `table_`, ...) | implicit, `const` method              | yes  | no         | layout facts and graph lookups                                                                            |
| `payload_id`                              | `const GuidMsg&`                      | yes  | no         | which car                                                                                                 |
| `job_index`                               | `size_t` by value                     | yes  | no         | stored in every new event                                                                                 |
| `ctx`                                     | `ScheduleContextSPtr` **by value**    |      |            | copying a `shared_ptr` copies the pointer, not the context: caller and callee share one `ScheduleContext` |
| `ctx->initial_state`                      | through `ctx`                         | yes  | no         | copied into `working_state`                                                                               |
| `ctx->events`                             | through `ctx`                         | yes  | **yes**    | replayed, then 4 events and 5 edges added (2 of the events by nested `PlanReparkTrayJob` calls)           |
| `ctx->last_entity_event`                  | through `ctx`                         | yes  | **yes**    | rule A reads and updates it: B21 → e4, T21 → e2, T17 → e3                                                 |
| `ctx->disabledness_filters`               | through `ctx`                         | yes  | rarely     | read with `operator[]`, which inserts a default entry if the collision id is missing                      |
| `ctx->scheduled_jobs`                     | through `ctx`                         | no   | no         | `Plan()` appends the job **after** a successful return                                                    |
| `working_state`, `bay_opt`, ...           | locals                                |      | local only | `bay_opt->state = READY_TO_RETRIEVE` changes the local copy, not the garage                               |
| return value                              | `std::tuple<bool, std::string, bool>` |      |            | success, message, `retain_job`                                                                            |

Two more effects are easy to miss:

- **`const` does not mean "no changes".** A `const` member function cannot change the `Scheduler`'s own members, but `ctx` points to a separate, non-`const` object, so the method can change it freely ([section 9](#bg-objects-ownership-and-lifetimes)).
- **Some job methods talk to Dispatch.** `PlanInsertJob` calls `reset_bay_state_request_fn_`, which `SchedulerRos` wired to an asynchronous ROS service request (`TransitionBayToInsert`). It is sent during expansion, before anyone knows whether the whole plan will succeed. `Plan()` itself calls `clean_garage_request_fn_()` when an INSERT fails.

#### Assessment of the design

This is a common C++ style with real reasons behind it, but it makes the code harder to follow, and it is the root of several gotchas in [15.18](#bg-gotchas-2). A fair summary:

**Why it was probably written this way**

- **One growing structure is convenient.** Every step needs the latest DAG and the latest `last_entity_event`. Passing one context pointer around is less code than threading inputs and results through every call.
- **Composition is free.** When `PlanRetrieveJob` calls `PlanReparkTrayJob`, the inner method simply appends to the same DAG, and its events immediately take part in rule B for the outer job. With pure functions, the caller has to merge the inner result itself.
- **The later stages really are graph rewrites.** Tray and AGV assignment fill in fields of existing events, add events and add edges across all jobs. In-place editing is natural there, and job expansion uses the same style for consistency.
- **Events are shared objects** (`std::shared_ptr`). Producing a modified copy of a DAG would need deep copies, so mutation is the cheap option. (The refactor proposal, sections [6.1](#pr-the-new-pieces-and-how-they-fit-together) and [6.5](#pr-why-return-a-result-and-how-it-is-applied), show a middle way for tray assignment: return an ordered log of edits and let one function apply it.)

**What it costs**

- **The signature hides the output.** Nothing in `std::tuple<bool, std::string, bool> PlanRetrieveJob(ScheduleContextSPtr, const GuidMsg&, size_t)` says "adds events and edges". You have to read the body, and the bodies of everything it calls.
- **No transaction.** A method that fails halfway leaves its partial changes in `*ctx` ([14.18](#bg-gotchas-2), gotcha 1). A pure function that returns its events would make "discard on failure" automatic.
- **Hidden dependencies between calls.** Rule B looks at the *current* leaves of the whole DAG, and rule A at the *current* `last_entity_event`. The result of a call therefore depends on everything that ran before it, not only on its arguments.
- **Harder to test.** A test has to build a `ScheduleContext`, call the method, then inspect the context (see the [Verification](#doc-verification) tab). It cannot simply compare a returned value.
- **Effects leave the process.** A callback to Dispatch from inside planning cannot be undone if the plan later fails.

**A purer alternative** (sketched in the figure; not in the code): give each job method a read-only view (`const` working state, DAG, last-entity map) and have it **return** a `JobPlan`: its new events, the edges it wants (with the rule that justified each), and any follow-up requests for Dispatch. `Plan()` then commits a successful `JobPlan` into the context in one place, or drops it on failure. That makes the output visible, makes rollback automatic, and lets a test compare `JobPlan` values directly. The costs are some boilerplate and a `Commit()` step that applies rules A, B and C centrally. Two middle grounds are cheaper:

- keep mutation but pass exactly what is changed (`ScheduleEventDag& events, LastEntityMap& last`) instead of the whole context, so the signature tells the truth;
- keep the current code but snapshot `events` and `last_entity_event` before each job and restore them on failure.

The refactor proposal makes the same trade-off for the tray and AGV solvers: it keeps in-place mutation for the first behaviour-preserving step and suggests a returned result afterwards.

### Every job sees the garage through `working_state`

Before a job method adds any event, it builds its own view of the garage, `working_state`, so that it plans against the garage as earlier jobs in the same request leave it, not as the request describes it. The figure shows how that view is produced from `ctx->initial_state` and the event DAG built so far; the details that matter in practice follow it.

![Working state replay](figures/23_working_state_replay.svg)

Every `Plan<Type>Job` copies `ctx->initial_state` and replays the whole event DAG built so far. Step through the three lines of code: after the copy, `working_state` still matches the request; after `Apply()`, tray T15 moves on the `working_state` map from P15 to P23, where job 0 will have put it, so job 1 (a retrieve) no longer sees it at P15 as in the request. Only then does job 1 add its own events.

Three details matter in practice:

- **`Apply()` is discrete.** A tray "teleports" to its destination; time and paths do not exist yet. Blank fields are not neutral ([section 11](#bg-event-types-and-polymorphism)): a `TrayMove` with no tray id does nothing, one with no destination **removes** the tray and its payload from `working_state`, and a tray already sitting on a destination is moved to the placeholder pose `{node_id: 0, heading: 0}`. So a later job does not see an empty tray that READY_FOR_INSERT will bring into a bay, and does not see a tray whose destination is still open.
- **Nested calls replay again.** When `PlanRetrieveJob` calls `PlanReparkTrayJob`, the inner call copies and replays too, so it already sees the bay transition the outer method has just added.
- **The cost is repeated replay.** Each job method replays the whole DAG, and nested calls replay it again. The code accepts this for simplicity.

### Where the edges come from

Job methods add not only events but also the edges between them, and those edges decide which events must finish before others may start. During job expansion every edge comes from one of three rules, called A, B and C in this guide. The figure shows the rules at work on five events; the definition of each rule follows it.

![Edge rules during job expansion](figures/25_dependency_rules.svg)

The three edge rules used during job expansion. Step through the five events in the order they are created to see which rule adds each edge, and how `last_entity_event` and the leaf set change. Rule A (`UpdateLastEntityEvent`) chains events on the same garage asset (AGV, tray, bay or VECS), even across jobs. Rule B (`UpdateLeafDependencies`) makes a new event wait for the current leaf events of the **same** job. Rule C (in `PlanReparkTrayJob`) makes a tray move into a bay or VECS wait for that resource's last event.

The three rules, in one sentence each, then how the code applies them. A **garage asset** is anything an event acts on and that only one event can use at a time: an AGV, a tray, a bay or a VECS. The letters A, B and C are this guide's shorthand; the function names the code uses are [listed below](#bg-does-the-code-really-call-them-rule-a-rule-b-and-rule-c).

- **Rule A — one asset, one event at a time, across jobs.** Each new event waits for the previous event on the same garage asset, whichever job created it. The code keeps `ctx->last_entity_event`, a map from each asset (`GarageEntityIdMsg`) to the last event that used it. `UpdateLastEntityEvent(id, e)` adds the edge `last[id] -> e` if there is one, then sets `last[id] = e`. This is the only rule that links **different jobs**: if job 0 and job 1 both move tray T19, job 1's move waits for job 0's.
- **Rule B — steps of one job in order.** Each new event of a job waits for the job's open ends: its earlier events that nothing else waits for yet. In DAG terms these are the job's *leaves*, events with no outgoing edge. `UpdateLeafDependencies(e, job_index)` adds `leaf -> e` for every leaf whose `GetJobIndex() == job_index`. It never links different jobs.
- **Rule C — a tray enters a bay or VECS only after that asset's latest event.** When a `TrayMove`'s destination is a bay or a VECS, it waits for the last event on that bay or VECS, so a tray never enters a bay before the bay's transition. Only `PlanReparkTrayJob` applies it; it reads `last_entity_event` but does not update it.

Not every event goes through every rule:

- **Without rule A:** a `TrayMove` with no tray yet (its tray is unknown); the "stop charging" `VecsTransition` in RETRIEVE and REPARK; and the `TrayMove` that MOVE_AGV creates for a loaded AGV is chained by tray only, not by AGV.
- **Without rule B:** the "stop charging" `VecsTransition`; RETRIEVE's `TRANSITION_TO_RETRIEVE` (so it does not wait for that stop-charging event); CHARGE_AGV's transition that frees a trapped AGV; and CLEAN_GARAGE's hide `AgvMove`s. Each of these is either the first event of its job or deliberately independent, but later events of the same job still wait for them through rule B. And none of the rules knows about geometry: whether tray T15 is *in the way* of T17's path, or whether two AGVs would meet, is discovered and turned into edges by tray and AGV assignment (sections [16](#bg-tray-assignment-dotrayassignments) and [17](#bg-agv-assignment-doagvassignments)).

#### Rule A, rule B and rule C in the code

The code does not use these names; the letters keep the figures readable. The functions to search for:

| Guide  | In the code                                                                                                         | What it does, and why                                                                                                                                                                                                                                             |
|--------|---------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rule A | `ScheduleContext::UpdateLastEntityEvent(entity_id, new_event)` in `scheduler.hpp`, with the map `last_entity_event` | Adds an edge from the last event on the asset to the new event, then records the new event as the asset's last. An asset can only do one thing at a time, and the next event must start from the state the previous one leaves.                                   |
| Rule B | `ScheduleContext::UpdateLeafDependencies(child, job_index)` in `scheduler.hpp`                                      | Adds an edge from every current leaf of the same job to the new event. A job's steps form a recipe (switch the bay, bring the tray, hand over the car) that must run in the order the job method creates them.                                                    |
| Rule C | Two inline blocks at the end of `Scheduler::PlanReparkTrayJob`                                                      | Adds an edge from the last event on the destination bay or VECS to the tray move. A bay must finish its current transition or retrieve before a tray enters it; rule A does not cover this, because a tray move is chained to its tray, not to the bay it enters. |

**Why each one is needed**, by what would go wrong without it:

- **Without rule A**, two jobs that touch the same tray, AGV, bay or VECS would be unordered. If job 0 moves T19 from P19 to P24 and job 1 moves it from P24 to P23, nothing would stop the replay, or the robots, from doing job 1's move first, starting from a place the tray is not at yet.
- **Without rule B**, the steps inside one job would be unordered: the car's tray could be planned into B21 before the bay switches to retrieve mode, or `PROCESS_RETRIEVE` could run before the tray arrives.
- **Without rule C**, a tray could enter a bay before an *earlier job's* bay event finished. Rule B does not help across jobs, and rule A does not either, because a `TrayMove` is chained to its tray, not to the bay it enters. For example, a READY_FOR_INSERT job bringing an empty tray into B21 must wait for the previous job's `PROCESS_RETRIEVE` on B21; only rule C adds that edge.

The three rules are not the whole story. They only order what the job methods know about. Geometric conflicts (a tray in the way, two AGVs on one node) are turned into edges later by tray and AGV assignment (sections [16](#bg-tray-assignment-dotrayassignments) and [17](#bg-agv-assignment-doagvassignments)).

### Job methods are built from a few shared pieces

The job methods in sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) are not independent of each other: several create their events by calling other job methods or a few shared helpers. This structure explains the order of those sections and why `PlanReparkTrayJob` is described first.

![Job building blocks](figures/37_job_building_blocks.svg)

Generated from `scheduler.cpp`: which methods each job method calls, which event types it creates itself, and whether it applies rules A and B itself. `PlanOpenBayDoor` and `PlanUnstashWaypointTraysJob` are helpers, not job types. Step through it one column group at a time; the last step marks the `PlanReparkTrayJob` column, the workhorse that six other methods create their `TrayMove`s through.

Two patterns stand out:

- **`PlanReparkTrayJob` is the workhorse.** Six methods create their `TrayMove`s through it, so the heading policy, the VECS checks and rule C live in one place. That is why it is explained first ([14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob)).
- **Composite jobs pass their own `job_index` down.** When `PlanRetrieveJob` calls `PlanReparkTrayJob(ctx, tray, job_index, ...)`, the inner events belong to the retrieve job. Rule B then orders them with the retrieve's other events, and the response reports them as part of the retrieve.

The order of [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) follows that structure: the building blocks first, then the jobs made from them.

### `TYPE_REPARK_TRAY` and `TYPE_MOVE_TRAY` — `PlanReparkTrayJob`

`PlanReparkTrayJob` moves one tray to one destination. `Plan()` calls it for `TYPE_REPARK_TRAY` and `TYPE_MOVE_TRAY` jobs, and six other job methods call it whenever they need a `TrayMove`, so the destination heading, the VECS checks and rule C are decided here for all of them.

``` cpp
BoolStringPair PlanReparkTrayJob(ScheduleContextSPtr ctx, std::optional<uint16_t> tray_id, size_t job_index,
    bool allow_recip, std::optional<GaragePoseMsg> dest = std::nullopt) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name          | Type                                                       | Meaning                                                                                                                                                                                                      | In the example below                                            |
|------------------|---------------|------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| in               | `this`        | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                     | Pecos layout                                                    |
| in / **changed** | `ctx`         | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+1 `TrayMove`, maybe a stop-charging `VecsTransition`) and `last_entity_event` | job 0 adds T19: P19 → P24                                       |
| in               | `tray_id`     | `std::optional<uint16_t>`                                  | Tray to move; `std::nullopt` means "any empty tray" (only from internal callers)                                                                                                                             | `19`                                                            |
| in               | `job_index`   | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                   | `0` and `1`                                                     |
| in               | `allow_recip` | `bool`                                                     | Allow keeping the tray's current heading when the requested one is the same or opposite (parking nodes only)                                                                                                 | `true` (job 0), `false` (job 1)                                 |
| in               | `dest`        | `std::optional<GaragePoseMsg>` (default `std::nullopt`)    | Target node and heading; empty means "anywhere, chosen by tray assignment". Always set when called from `Plan()`                                                                                             | `{node_id: 24, heading: 90}`, then `{node_id: 23, heading: 90}` |
| out              | return        | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                        | `{true, ""}` for both                                           |

**When Dispatch sends it:** to move a specific tray to a specific node (an operator request, or Dispatch tidying up). Both job types call the same method with `job.tray_id`, `job.allow_reciprocal` and `job.destination`.

![Repark tray job](figures/41_job_repark_tray.svg)

Two jobs move tray T19: P19 → P24, then P24 → P23. Rule A chains the second move after the first. The last three steps play the plan with an illustrative AGV-1: it drives under T19, carries it to `P24` (1), and then on to `P23` (2).

In words: create one `TrayMove`, set its tray and (if given) its destination with the right heading, and add it with rules A, C and B. Things to remember:

- **Either argument may be missing, not both.** Internal callers use `dest = std::nullopt` ("move this tray out of the way, anywhere") or `tray_id = std::nullopt` ("bring any empty tray here"). From `Plan()` both are always present.
- **Heading policy, in two steps.** First, only for a plain parking destination with `allow_recip`: an empty tray keeps its current heading if the requested one is the same or opposite; a loaded tray gets the node's *retrieval heading* (the heading that makes a later retrieve fastest), flipped if the car sits backwards on the tray. Second, for every destination of a known tray (parking, bay, VECS or waypoint, whatever `allow_recip` says), `UsePreferredHeading` runs: the `576_eccles` EV-charging exception (nodes 46 and 47), then `UseRetrievalHeading`, which changes the heading only if the tray is loaded and `gg_.GetRetrievalHeading(node)` gives a heading the node allows.
- **The tray is looked up in `ctx->initial_state`**, not in `working_state`. See [15.18](#bg-gotchas-2).

### `TYPE_MOVE_AGV` — `PlanAgvMoveJob`

`PlanAgvMoveJob` sends one AGV to a given pose. `Plan()` calls it for `TYPE_MOVE_AGV` jobs and `PlanAgvChargeJob` calls it to drive an AGV to a charger; it checks the AGV and the destination and decides whether the event it adds is an `AgvMove` or, when the AGV already carries a tray, a `TrayMove`.

``` cpp
BoolStringPair PlanAgvMoveJob(ScheduleContextSPtr ctx, std::optional<uint16_t> agv_id, GaragePoseMsg dest,
    bool allow_recip, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name          | Type                                                       | Meaning                                                                                                                                                                           | In the example below                                                   |
|------------------|---------------|------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| in               | `this`        | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                          | Pecos layout                                                           |
| in / **changed** | `ctx`         | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+1 `AgvMove` or `TrayMove`) and `last_entity_event` | two jobs, one event each                                               |
| in               | `agv_id`      | `std::optional<uint16_t>`                                  | AGV to move; empty is rejected ("not yet supported")                                                                                                                              | `A`, `B`                                                               |
| in               | `dest`        | `GaragePoseMsg` (by value; may be edited locally)          | Target pose in AGV heading                                                                                                                                                        | `{node_id: 13, heading: 90}` (W13), `{node_id: 24, heading: 90}` (P24) |
| in               | `allow_recip` | `bool`                                                     | Keep the current pose if the heading is the same or opposite. `Plan()` and `PlanAgvChargeJob` pass `false`                                                                        | `false`                                                                |
| in               | `job_index`   | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                        | `0`, `1`                                                               |
| out              | return        | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                             | `{true, ""}` for both                                                  |

**When Dispatch sends it:** to drive a named AGV somewhere, for example out of the way for maintenance. `PlanAgvChargeJob` also uses it.

![Move AGV job](figures/40_job_move_agv.svg)

An empty AGV produces an `AgvMove`; an AGV carrying a tray produces a `TrayMove` with that AGV already assigned. Here AGV-1 is sent to `W13` and AGV-2, which carries T9, to `P24`. The last two steps play the plan: AGV-1 drives to `W13`, then AGV-2 carries T9 to `P24` with no approach drive.

In words: check the AGV and destination, then add one event. Remember that **this is the only job that can create a `TrayMove` with its AGV already set**, and that the `allow_recip` branch is never used (both callers pass `false`).

### `TYPE_TRANSITION_BAY_TO_INSERT` / `_TO_RETRIEVE` — `PlanBayTransitionJob`

`PlanBayTransitionJob` switches one bay between insert mode and retrieve mode. `Plan()` calls it for the two `TYPE_TRANSITION_BAY_TO_*` job types and `PlanAgvChargeJob` calls it to return a bay to insert mode; it decides whether the bay may be switched at all before it adds a single `BayTransition`.

``` cpp
BoolStringPair PlanBayTransitionJob(ScheduleContextSPtr ctx, uint16_t bay_id, uint8_t command_type,
    size_t job_index) const;   // command_type = BayCommandMsg::COMMAND_TYPE_TRANSITION_TO_{INSERT,RETRIEVE}
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name           | Type                                                                               | Meaning                                                                                                                                                                   | In the example below                                                   |
|------------------|----------------|------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| in               | `this`         | `const Scheduler*`                                                                 | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                  | Pecos layout                                                           |
| in / **changed** | `ctx`          | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`)                         | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+1 `BayTransition`) and `last_entity_event` | job 0 adds one event; job 1 none                                       |
| in               | `bay_id`       | `uint16_t`                                                                         | Bay node id                                                                                                                                                               | `21`, `7`                                                              |
| in               | `command_type` | `uint8_t`: `BayCommandMsg::COMMAND_TYPE_TRANSITION_TO_INSERT` or `..._TO_RETRIEVE` | Which mode to switch to; anything else fails                                                                                                                              | `TO_RETRIEVE`, `TO_INSERT`                                             |
| in               | `job_index`    | `size_t` (by value)                                                                | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                | `0`, `1`                                                               |
| out              | return         | `BoolStringPair` = `std::pair<bool, std::string>`                                  | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                     | job 0 `{true, ""}`; job 1 `{false, "... the ODP's area is occupied."}` |

**When Dispatch sends it:** to switch one bay's mode explicitly. Seen from the code, a bay has two working modes: **insert** (`READY_TO_INSERT`: an empty tray is inside and a customer can drive onto it) and **retrieve** (`READY_TO_RETRIEVE`: trays can be planned into and out of the bay, and a car can be handed over with `PROCESS_RETRIEVE`).

![Bay transition job](figures/49_job_bay_transition.svg)

Job 0 switches B21 to retrieve mode. Job 1 is rejected because AGV-3 stands in B7's ODP collision area (extent drawn for illustration). The last step plays the plan: B21's state changes to `READY_TO_RETRIEVE`, and AGV-3 stays where it is.

In words: validate (bay exists, enabled, its `BAY_ODP` area is clear, the bay is in the right starting state), then add one `BayTransition`. Retrieve transitions made here and in `PlanOpenBayDoor` carry a floor number (`GetBaySystemFloors(bay)[0]`); the ones `PlanRetrieveJob` and `PlanAgvChargeJob` build inline leave `cmd.floor` at 0.

### `TYPE_CHARGE_PAYLOAD` — `PlanChargePayloadJob`

`PlanChargePayloadJob` brings a car to an EV-charging unit (VECS) and starts charging it. `Plan()` calls it for `TYPE_CHARGE_PAYLOAD` jobs, and the READY_FOR_INSERT and READY_FOR_RETRIEVE job methods use it when the car in a bay has asked for charging; it decides which VECS the car's tray goes to when the tray is not already on a ready one.

``` cpp
BoolStringPair PlanChargePayloadJob(ScheduleContextSPtr ctx, const GuidMsg& payload_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name         | Type                                                       | Meaning                                                                                                                                                                                                                 | In the example below |
|------------------|--------------|------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| in               | `this`       | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                                | Pecos layout         |
| in / **changed** | `ctx`        | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+ a `TrayMove` through `PlanReparkTrayJob`, + 1 `VecsTransition`) and `last_entity_event` | 2 events             |
| in               | `payload_id` | `const GuidMsg&`                                           | The car to charge                                                                                                                                                                                                       | car on T20           |
| in               | `job_index`  | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                              | `0`                  |
| out              | return       | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                                   | `{true, ""}`         |

**When it runs:** when Dispatch asks for a car to be charged, and inside READY_FOR_INSERT / READY_FOR_RETRIEVE when the car in the bay has `payload.ev_charge_requested`. A VECS is the EV-charging unit at a `TYPE_EV_CHARGE` node; its states include `READY_TO_CHARGE` and `CHARGING`.

![Charge payload job](figures/50_job_charge_payload.svg)

The car on T20 is moved to a VECS (invented here; the Pecos layout has none) and the VECS is switched to CHARGING. The last three steps play the plan: an illustrative AGV-1 drives under T20, carries it onto `V23` (1), and V23 starts charging (2).

In words: if the tray is not already on a ready VECS, borrow the open-space search of `ResolveBlockingTrays()` (explained under tray assignment, [section 4](#bg-tray-assignment-dotrayassignments)) to find one, move the tray there through `PlanReparkTrayJob`, then add the `VecsTransition`.

### `TYPE_RETRIEVE` — `PlanRetrieveJob`

`PlanRetrieveJob` brings a parked car to a bay and hands it over to the customer. `Plan()` calls it for `TYPE_RETRIEVE` jobs; it decides whether the car can be reached and which bay to use, and it is the only job method whose signature returns a third value, `retain_job`, which tells Dispatch to keep a failed job and retry it.

``` cpp
std::tuple<bool, std::string, bool> PlanRetrieveJob(ScheduleContextSPtr ctx, const GuidMsg& payload_id,
    size_t job_index) const;   // {success, message, retain_job}
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name         | Type                                                       | Meaning                                                                                                                                                                                                                                            | In the example below |
|------------------|--------------|------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| in               | `this`       | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                                                           | Pecos layout         |
| in / **changed** | `ctx`        | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+2 `BayTransition`s, +1–2 `TrayMove`s through `PlanReparkTrayJob`, maybe a `VecsTransition`) and `last_entity_event` | 4 events, 5 edges    |
| in               | `payload_id` | `const GuidMsg&`                                           | The car to retrieve                                                                                                                                                                                                                                | car on T17           |
| in               | `job_index`  | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                         | `0`                  |
| out              | return       | `std::tuple<bool, std::string, bool>`                      | `{success, message, retain_job}`. `retain_job = true` asks Dispatch to keep a failed job and retry later                                                                                                                                           | `{true, "", false}`  |

**When Dispatch sends it:** a customer wants their car. This is the most important job and the richest method.

![Retrieve job](figures/42_job_retrieve.svg)

Retrieving the car on T17. Bay B21 is chosen, switched to retrieve mode (1), the empty tray inside is planned out (2), T17 is planned in (3), and the bay hands over the car (4). The last eight steps play the plan with AGV-1: the bay opens, T21 goes to `P23`, the blocker T15 is moved to `P19`, T17 is carried into B21, and the bay processes the retrieve. The destinations and the blocker move are illustrative; tray assignment chooses them later.

In words, five decisions in order:

1.  **Is the car reachable?** It must exist and its node must not be disabled. If it sits on a VECS that is charging, add a "stop charging" `VecsTransition`.
2.  **Which bay?** Walk `layout_->GetBayPrioritization()` from the back. Skip disabled bays and bays whose resource window is smaller than the car. Take the first `READY_TO_RETRIEVE` bay; otherwise the first `READY_TO_INSERT` or `VEHICLE_INSERTED` bay. None: fail with `retain_job = true`.
3.  **Open the bay** if it is not in retrieve mode (event 1).
4.  **Empty the bay** if a tray is inside (event 2, destination left open).
5.  **Bring the car in, then hand it over** (events 3 and 4). The requested heading is the bay's inbound heading, reversed unless `payload.reciprocal_to_tray`, so the car ends up facing the way the bay needs. (Inside `PlanReparkTrayJob`, `UsePreferredHeading` would still override it if the bay node had a retrieval heading.)

### `TYPE_INSERT` — `PlanInsertJob`

`PlanInsertJob` takes a car that a customer has just left in a bay and sends its tray into storage. `Plan()` calls it for `TYPE_INSERT` jobs; it checks the bay, opens it, and leaves the tray's parking spot for tray assignment to choose.

``` cpp
BoolStringPair PlanInsertJob(ScheduleContextSPtr ctx, uint16_t bay_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name                          | Type                                                       | Meaning                                                                                                                                                                                  | In the example below                      |
|------------------|-------------------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| in               | `this`                        | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                 | Pecos layout                              |
| in / **changed** | `ctx`                         | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+1 `BayTransition`, +1 `TrayMove`) and `last_entity_event` | 2 events                                  |
| in               | `bay_id`                      | `uint16_t`                                                 | Bay where the customer left the car                                                                                                                                                      | `21`                                      |
| in               | `job_index`                   | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                               | `0`                                       |
| out              | return                        | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                    | `{true, ""}`                              |
| side effect      | `reset_bay_state_request_fn_` | `std::function<void(uint16_t, uint16_t)>` (member)         | Asynchronous request to Dispatch for a READY_FOR_INSERT job on this bay                                                                                                                  | called with `(21, STATE_READY_TO_INSERT)` |

**When Dispatch sends it:** a customer has parked on the tray in a bay that was in insert mode. The car now has to go into storage.

![Insert job](figures/43_job_insert.svg)

The loaded tray T21 leaves bay B21. Its parking spot is chosen later. Refilling the bay is requested as a separate job through a callback. The last three steps play the plan: B21 switches to retrieve mode (1), then an illustrative AGV-1 fetches T21 and parks it at `P19` (2, destination illustrative).

In words: check that the bay holds a loaded tray and is `VEHICLE_INSERTED` or `READY_TO_RETRIEVE`, switch it to retrieve mode with `PlanOpenBayDoor` (event 1), move the tray out with no destination (event 2), then call `reset_bay_state_request_fn_` so Dispatch schedules the bay's refill on its own.

### `TYPE_READY_FOR_INSERT` — `PlanReadyForInsertJob`

`PlanReadyForInsertJob` prepares a bay for the next arriving customer: an empty tray inside and the bay in insert mode. `Plan()` calls it for `TYPE_READY_FOR_INSERT` jobs and `PlanRebalanceGarageJob` calls it for each bay it wants in insert mode; it decides whether an empty tray must be brought in and, unlike the other job methods, tries to choose that tray itself.

``` cpp
BoolStringPair PlanReadyForInsertJob(ScheduleContextSPtr ctx, uint16_t bay_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                                       | Meaning                                                                                                                                                                                                                                                                                                  | In the example below               |
|------------------|-------------|------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| in               | `this`      | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                                                                                                                 | Pecos layout                       |
| in / **changed** | `ctx`       | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+ a `TrayMove` through `PlanReparkTrayJob`, maybe a charge-payload recipe, +1 `BayTransition`), `last_entity_event`, and the tray id of its own new `TrayMove` (fill pass) | 2 events; tray T23 filled in early |
| in               | `bay_id`    | `uint16_t`                                                 | Bay to prepare for the next customer                                                                                                                                                                                                                                                                     | `21`                               |
| in               | `job_index` | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                                                                               | `0`                                |
| out              | return      | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                                                                                                                    | `{true, ""}`                       |

**When it runs:** to get a bay ready for the next customer: it needs an empty tray inside and insert mode. Sent by Dispatch, and used for each bay that REBALANCE_GARAGE wants in insert mode.

![Ready for insert job](figures/44_job_ready_for_insert.svg)

An empty tray is planned into B21 (chosen early here: T23), then B21 switches to insert mode. The last three steps play the plan: an illustrative AGV-1 drives under T23, carries it into B21 (1), and B21 switches to `READY_TO_INSERT` (2).

In words: the bay must be `READY_TO_RETRIEVE`. If it is empty, or holds a loaded tray, plan "any empty tray → bay" (a `TrayMove` with no tray). If the car in the bay asked for charging, plan `PlanChargePayloadJob` first. Then try to pick the empty tray right away with `AssignTrayIdForEmptyMove`, and finish with `TRANSITION_TO_INSERT`.

This is the only job method that **fills a blank itself**. It replays the DAG once more (`fill_state`), walks the events in topological order and, for its own trays-to-be, picks an empty tray with the same search as `AssignTrayIdForEmptyMove` (cheapest to reach: travel time plus 30 s per tray in the way). If that fails, it only logs a warning; `DoTrayAssignments()` will try again with the full picture.

### `TYPE_READY_FOR_RETRIEVE` — `PlanReadyForRetrieveJob`

`PlanReadyForRetrieveJob` puts a bay into retrieve mode in advance, so that a later retrieve does not have to wait for the transition. `Plan()` calls it for `TYPE_READY_FOR_RETRIEVE` jobs and `PlanRebalanceGarageJob` calls it for each bay it wants in retrieve mode; it decides whether the bay must be opened and what happens to a tray left inside.

``` cpp
BoolStringPair PlanReadyForRetrieveJob(ScheduleContextSPtr ctx, uint16_t bay_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                                       | Meaning                                                                                                                                                                                                                 | In the example below |
|------------------|-------------|------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| in               | `this`      | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                                | Pecos layout         |
| in / **changed** | `ctx`       | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (maybe a `BayTransition`, a `TrayMove` or a charge-payload recipe) and `last_entity_event` | 2 events             |
| in               | `bay_id`    | `uint16_t`                                                 | Bay to put into retrieve mode                                                                                                                                                                                           | `21`                 |
| in               | `job_index` | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                              | `0`                  |
| out              | return      | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                                   | `{true, ""}`         |

**When it runs:** to put a bay into retrieve mode ahead of time, so a later retrieve does not wait for the transition. Used mostly by REBALANCE_GARAGE.

![Ready for retrieve job](figures/45_job_ready_for_retrieve.svg)

B21 switches to retrieve mode and the empty tray inside is planned out. There is no final bay event. The last three steps play the plan: the bay opens (1), and an illustrative AGV-1 fetches T21 and parks it at `P23` (2, destination illustrative).

In words: the bay must be in insert or retrieve mode. If in insert mode, open it (event 1). If a tray is inside, send an EV car to a VECS, otherwise move the tray out with no destination (event 2).

### `TYPE_CHARGE_AGV` — `PlanAgvChargeJob`

`PlanAgvChargeJob` sends an AGV with a low battery to a charger. `Plan()` calls it for `TYPE_CHARGE_AGV` jobs; it decides which free charger is cheapest to reach and, when the AGV is trapped in a bay in insert mode, opens that bay first and restores it afterwards, using `PlanAgvMoveJob` and `PlanBayTransitionJob` for those steps.

``` cpp
BoolStringPair PlanAgvChargeJob(ScheduleContextSPtr ctx, uint16_t agv_id, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                                       | Meaning                                                                                                                                                                                                                | In the example below                                                                   |
|------------------|-------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| in               | `this`      | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                               | Pecos layout                                                                           |
| in / **changed** | `ctx`       | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (maybe 2 `BayTransition`s, +1 `AgvMove` through `PlanAgvMoveJob`) and `last_entity_event` | 3 events                                                                               |
| in               | `agv_id`    | `uint16_t`                                                 | AGV whose battery is low                                                                                                                                                                                               | `A`                                                                                    |
| in               | `job_index` | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                             | `0`                                                                                    |
| out              | return      | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                                  | `{true, ""}`; with no free charger `{false, "Caution: No available charge nodes ..."}` |

**When Dispatch sends it:** an AGV's battery is low.

![Charge AGV job](figures/48_job_charge_agv.svg)

AGV-1 is trapped in bay B21 (insert mode). The bay opens (1), AGV-1 drives to the cheapest free charger C14 (2), and the bay returns to insert mode (3). Costs are illustrative. The last three steps play the plan on the map.

In words: free the AGV if a bay in insert mode traps it, cost every `TYPE_AGV_CHARGE` node with no AGV on it using `GetJustMovingCost`, move to the cheapest with `PlanAgvMoveJob`, and put the bay back with `PlanBayTransitionJob`.

### `TYPE_CLEAN_GARAGE` — `PlanCleanGarageJob`

`PlanCleanGarageJob` tidies the garage: it sends the AGVs to hiding poses and returns trays left on waypoints to parking. `Plan()` calls it for `TYPE_CLEAN_GARAGE` jobs, which Dispatch sends on its own decision or after `Plan()` asks for one following a failed INSERT; it decides which AGVs must move and which trays must leave waypoints.

``` cpp
BoolStringPair PlanCleanGarageJob(ScheduleContextSPtr ctx, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                                       | Meaning                                                                                                                                                                                                                                            | In the example below                                             |
|------------------|-------------|------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| in               | `this`      | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`                                                                                                                                                                           | Pecos layout                                                     |
| in / **changed** | `ctx`       | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (+1 `AgvMove` per AGV to hide when `job_index == 0`, +1 `TrayMove` per waypoint-stashed tray) and `last_entity_event` | 3 events                                                         |
| in               | `job_index` | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                                         | `0`, which enables hiding                                        |
| out              | return      | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                                                              | `{true, ""}`; fails only if hiding (or the initial replay) fails |

**When it is requested:** Dispatch decides (the comment in `PlanInsertJob` says it can be deferred until inserts and retrieves are done), and `Plan()` asks for one through `clean_garage_request_fn_()` after a failed INSERT.

![Clean garage job](figures/46_job_clean_garage.svg)

AGV-1 and AGV-2 are hidden under trays (1, 2). Tray T9, left on a waypoint by an earlier plan, is planned back into parking (3). The last four steps play the plan: both AGVs drive to their hiding spots, then AGV-2 fetches T9 from `W25` and parks it at `P23`, ending hidden under it (AGV and destination illustrative).

In words: if this is `job_index` 0, ask `volley::HideAgvs` (`motion_planner`; [section 7.6](#mp-hide-agvs)) for one hiding pose per AGV and add an `AgvMove` for each AGV that is not already there. Then `PlanUnstashWaypointTraysJob` adds a destination-less `TrayMove` for every tray standing on a `TYPE_WAYPOINT` node. Only the hiding step (or the initial replay of the DAG) can fail the job.

### `TYPE_REBALANCE_GARAGE` — `PlanRebalanceGarageJob`

`PlanRebalanceGarageJob` adjusts how many bays are ready for insert and how many are ready for retrieve. `Plan()` calls it for `TYPE_REBALANCE_GARAGE` jobs; it decides which bays to switch and builds the work for each of them from the READY_FOR_INSERT and READY_FOR_RETRIEVE job methods.

``` cpp
BoolStringPair PlanRebalanceGarageJob(ScheduleContextSPtr ctx, size_t job_index) const;
```

**API** (*Dir*: `in` is read only, `changed` is modified in place through `ctx`, `out` is returned):

| Dir              | Name        | Type                                                       | Meaning                                                                                                                                                                                                                      | In the example below                           |
|------------------|-------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| in               | `this`      | `const Scheduler*`                                         | Fixed planner data, read only: `layout_`, `gg_`, `table_`, `cost_model_`, `bay_readiness_ratio_`                                                                                                                             | Pecos layout                                   |
| in / **changed** | `ctx`       | `ScheduleContextSPtr` (`std::shared_ptr<ScheduleContext>`) | The per-`Plan()` context, shared with the caller. Read: `initial_state`, `events`, `disabledness_filters`. Changed: `events` (the READY_FOR_INSERT / READY_FOR_RETRIEVE recipes for each chosen bay) and `last_entity_event` | 4 events for 2 bays                            |
| in               | `job_index` | `size_t` (by value)                                        | Position the job will take in `ctx->scheduled_jobs` (when called from another job method, that job's index); stored in every event created                                                                                   | `0`, shared by every bay's recipe              |
| out              | return      | `BoolStringPair` = `std::pair<bool, std::string>`          | `{true, ""}` on success, `{false, reason}` on failure                                                                                                                                                                        | `{true, ""}`; per-bay failures are only logged |

**When it is requested:** when the `set_bay_readiness_ratio` service changes `bay_readiness_ratio_`, `SchedulerRos` calls `rebalance_garage_request_fn_()` to ask Dispatch for this job; Dispatch can also send it on its own. [Section 20](#bg-bays-vecs-and-vrcs) explains the ratio and how bays are classified.

![Rebalance garage job](figures/47_job_rebalance_garage.svg)

B7 gets an empty tray and insert mode (1, 2); B21 gets retrieve mode and its tray is planned out (3, 4). One job index for both bays makes rule B run them one after the other. The last six steps play the plan in that order with an illustrative AGV-1: T5 into B7, B7 to insert mode, B21 to retrieve mode, then T21 out to `P23` (destination illustrative).

In words: `ComputeBayRebalancingActions()` returns two bay lists; run `PlanReadyForInsertJob` for the first and `PlanReadyForRetrieveJob` for the second, all with the same `job_index`. Per-bay failures are only logged; the job fails only if the initial replay of the DAG fails.

### Gotchas

These are behaviours of the current code that surprise people. They are not fixed here; changing them changes plans.

1.  **A failed job can leave events behind.** `Plan()` does not remove events when a job method fails, and `FailJob()` carries a TODO about it ("strip all the events which may be in the dag for the now failed job"). It happens when a method has already added something before a later check fails, for example:

    - RETRIEVE adds "stop charging" and then finds no bay;
    - RETRIEVE or INSERT opens a bay and then the repark fails;
    - CHARGE_AGV opens a bay and then finds no charger.

    The leftover events keep the failed job's `job_index`, which the next successful job reuses ([14.2](#bg-the-loop-in-plan)), so they are reported and executed as part of that job. Because they share the index, they also count as that job's leaves, so its first events get rule B edges from them. If an earlier job succeeded but no job from the failed one onward does, `ctx->scheduled_jobs[event->GetJobIndex()]` reads past the end of the vector when the response is built. Other places it can happen: CHARGE_AGV when the final bay transition fails, READY_FOR_INSERT when the charge-payload recipe succeeds and the empty-tray repark fails, READY_FOR_RETRIEVE when the door opens and the repark fails, and inside REBALANCE, where a bay recipe's partial events stay under the (always successful) rebalance job.

2.  **`PlanReparkTrayJob` looks the tray up in `ctx->initial_state`.** The "already at destination" check therefore compares with the tray's position in the request, not after earlier jobs, and the "is it on a charging VECS" check looks at the request node too.

3.  **`PlanReparkTrayJob` with no tray but a destination reads an empty optional.** The line `if(tray_opt->pose == dest.value())` runs even when `tray_id` is `std::nullopt` (READY_FOR_INSERT's "any empty tray" case). That is undefined behaviour; it should test `tray_opt` first.

4.  **`job_index == 0` means "first successful job".** CLEAN_GARAGE hides AGVs only then. If earlier jobs in the request failed, a later CLEAN_GARAGE can still get index 0.

5.  **Bay transitions are not always necessary ones.** `PlanOpenBayDoor` (INSERT) adds `TRANSITION_TO_RETRIEVE` even when the bay is already `READY_TO_RETRIEVE`.

6.  **CHARGE_PAYLOAD throws away the unblocking moves** that `ResolveBlockingTrays()` returns (`auto [dest, _] = ...`). They are found again in tray assignment.

7.  **"Free charger" only means "no AGV on the node".** The code says so, with a TODO to check for other conflicts.

8.  **Rule B serialises composite jobs.** REBALANCE_GARAGE's per-bay recipes share one `job_index`, so each bay waits for the previous bay's work.

9.  **Some bay commands skip the disabled check.** `PlanReadyForInsertJob`, `PlanReadyForRetrieveJob`, `PlanOpenBayDoor` and CHARGE_AGV's trapped-bay branch never test `bay.disabled` (INSERT and TRANSITION_BAY_TO\_\* do). `Plan()` marks bays that already have a command in `base_schedule` as disabled, so those methods can command such a bay again; READY_FOR_INSERT is only stopped indirectly, because the repark into a disabled bay fails.

10. **INSERT's callback fires before the plan is known to succeed.** `reset_bay_state_request_fn_` runs during job expansion, so Dispatch receives the refill request even if tray assignment or motion planning later fails the whole plan.

11. **Late failures duplicate failed jobs.** When a later stage fails, `Plan()` calls `FailJob` for every entry of `request_data.pending_jobs`, including jobs that already failed in the loop, so `result.scheduled_jobs` can list the same job twice.

12. **`AssignTrayIdForEmptyMove` ([under tray assignment](#bg-filling-a-blank-tray-id-assigntrayidforemptymove)) may change the destination heading** to the chosen tray's heading when the two are the same or opposite, to avoid a rotation.

### Cheat sheet and self-check

This section closes job expansion with a one-page summary of the events each job type can create, followed by five questions to check understanding before tray assignment. The figure condenses sections [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob); the questions draw on the loop, the edge rules and the job figures.

![Job recipes](figures/24_job_recipes.svg)

Cheat sheet: one row per job type, **not** a sequence of scenarios. Each row lists the events that job method can add, left to right in creation order. Dashed boxes appear only when needed; "+ recipe" means the method calls another job method; "?" is a blank for `DoTrayAssignments()`. Step through the job types family by family: single-entity building blocks first, then customer jobs, bay preparation, charging and housekeeping, which reuse them. The figures in [14.7](#bg-type_repark_tray-and-type_move_tray--planreparktrayjob) to [14.17](#bg-type_rebalance_garage--planrebalancegaragejob) show each row in a garage.

Check yourself before moving on:

1.  A request has `[RETRIEVE (fails), MOVE_AGV, REPARK_TRAY]`. What `job_index` does each successful job get?
2.  Job 0 reparks T19 to P24 and job 1 reparks T19 to P23. Which rule orders the two moves, and why does rule B not?
3.  In the retrieve figure, why does event 3 have edges from both 1 and 2?
4.  Which job types can leave a `TrayMove` with no destination? With no tray?
5.  Why can a bay's ODP check fail for TRANSITION_BAY_TO_INSERT but not for INSERT?

Answers

1.  MOVE_AGV gets 0 and REPARK_TRAY gets 1; the failed retrieve uses no index (but see gotcha 1 if it added events first).
2.  Rule A (same tray). Rule B only links events of the same job.
3.  Rule B (2 was the job's only leaf) and rule C (the tray is going into bay B21, whose last event is 1).
4.  No destination: RETRIEVE, INSERT, READY_FOR_RETRIEVE, CLEAN_GARAGE (and REBALANCE through READY_FOR_RETRIEVE). No tray: READY_FOR_INSERT (and REBALANCE through it) when `AssignTrayIdForEmptyMove` finds nothing.
5.  The ODP check lives in `PlanBayTransitionJob`; INSERT uses `PlanOpenBayDoor`, which does not check it.

## Tray assignment: `DoTrayAssignments`

Tray assignment is the second stage of task planning: `DoTrayAssignments(ctx)` runs after job expansion and before AGV assignment, on the event DAG that expansion produced. It completes every `TrayMove` that expansion left with a blank tray or destination and adds the moves that take blocking trays out of the way. The subsections below first state the problem, then follow one event through the stage.

### The problem this stage solves

Job expansion ([section 14](#bg-job-expansion-from-jobs-to-events)) turns each job into events, but those events describe *intent*, not a finished plan. Two things are still missing when expansion ends.

**1. Some `TrayMove` events have blank fields.** Every physical tray in the garage has an id, and the scheduler always knows where it is. The blank is not on a tray; it is on an **event**. A `TrayMove` stores its tray id and its destination as `std::optional`s (`GetTrayId()`, `GetDest()`), and a job method leaves one of them empty on purpose when the job's request does not decide it:

| Blank field | Event means                       | Created by                                                                                                                                                                                                                                           | Why the job leaves it blank                                                                                                                                                                                                                                 | Filled by                     |
|-------------|-----------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| tray id     | “*some* empty tray → this pose”   | `READY_FOR_INSERT`: `PlanReparkTrayJob(ctx, std::nullopt, job_index, true, bay_pose)`                                                                                                                                                                | The customer wants *an* empty tray in the bay; any one will do, and the best one depends on where trays are at that point in the plan                                                                                                                       | `AssignTrayIdForEmptyMove`    |
| destination | “this tray → *anywhere sensible*” | `RETRIEVE` (an empty tray already in the bay must leave first), `INSERT` (the tray with the new car leaves the bay), `READY_FOR_RETRIEVE` (tray in the bay leaves), `CLEAN_GARAGE` (`PlanUnstashWaypointTraysJob`: stashed trays go back to parking) | The job only needs the tray *out of the way* or *parked*; which stall is a search over the garage, and the comment in `PlanInsertJob` says so: “After PlanInsertJob() returns, DoTrayAssignments() will call ResolveBlockingTrays() to find a destination.” | `AssignDestForUntargetedMove` |

These fields are filled in here rather than in the job methods because choosing a tray or a stall is a graph search, and the answer can create *extra* moves (a tray in the way must be moved first) plus new DAG edges. That machinery lives here. This stage also walks the events in DAG (topological) order, with a copy of the garage state, `working_state`, that is updated after every move. Each choice therefore sees the garage as it will be *at that point in the plan*, including moves that earlier jobs in the same request already scheduled.

**2. Destinations are often unreachable as the garage stands.** The garage is dense: trays park nose-to-tail, and a tray can only travel through nodes that are free. Two terms are used throughout this section:

- The **root tray** is the tray of the `TrayMove` currently being processed: the tray a job actually asked to move (a car to retrieve, an empty tray for a bay).
- A **blocking tray** is any other tray whose footprint collides with the root tray's path to its destination (collision is decided by the `CollisionTable`, [section 5.4](#bg-collisiontable-precomputed-conflict-sets), not just equal node ids). It must move out of the way first. No job asked for that move; this stage invents it.

When `DoTrayAssignments(ctx)` returns `{true, ""}`, three things hold:

- every `TrayMove` in `ctx->events` has a tray id **and** a destination;
- every blocking tray has its own new `TrayMove`, ordered before the move it unblocks;
- the DAG has edges that keep moves from entering space before it is freed (`freeing_moves`, below), and `ctx->first_tray_event` records the first move of each tray for AGV assignment.

The rest of the section follows one event through the stage: the overall flow ([Figure 46](#bg-fig-27_tray_assignment_flow)), the main blocking-tray loop for a move that already has both fields, then the two helpers that fill a blank tray id and a blank destination, and finally how occupancy becomes DAG edges.

![Scene used in the following figures](figures/15_facility_scenario.svg)

The problem in one picture. Step through to build the scene: first the real Pecos geometry, then the job: a job asked for the car on tray R, so **R is the root tray**: it sits at `P17` and must reach bay `B21`. It cannot, because every exit from `P17` is occupied or useless: `P15` holds the empty tray K, `P20` holds T20 (with a car), and charger `C16` is a dead end. K and T20 are therefore **blocking trays**: no job asked to move them, but one of them must move before R can. Tray assignment finds that out and adds the extra move. Bays `B7` and `B21` sit on the customer side; AGV-1 waits at charger `C10`, and T15 (with a payload) is at `P3`. The last step previews what has to happen: AGV-1 drives to `W13`, next to the blockers, and K must move out of the way first (for example to `P19`); [Figure 47](#bg-fig-15_blocking_tray_move) plays that plan. All positions are explanatory stand-ins, not YAML occupancy.

![DoTrayAssignments flow](figures/27_tray_assignment_flow.svg)

Inside `DoTrayAssignments()`. Non-tray events register their pose with `freeing_moves` and are applied. Missing tray ids come from an empty-tray search; missing destinations from `ResolveBlockingTrays`. Moves with both go through the blocking-tray loop with two fallbacks. Step through the loop to follow concrete events: a bay transition, an untargeted move, and a move whose blocker T15 is resolved and emitted as a new event, then what the fallbacks and the empty-tray branch would do.

Per event, in topological order (`scheduler.cpp:2533`):

1.  **Not a `TrayMove`** (bay / VECS transitions, AGV events): `ApplyTransitionToFreeingMoves` records the bay or VECS pose as occupied by that event, applies it to `working_state`, and moves on.
2.  **Tray id blank** → `AssignTrayIdForEmptyMove` (`:2575`) picks a tray; the event then **continues** down this list with both fields set.
3.  **Destination blank** → `AssignDestForUntargetedMove` (`:2584`) picks a destination, emits the blocker moves, and the loop **`continue`s**: the main loop below is skipped for this event.
4.  **Both set** → the main blocking-tray loop.

Three of the searches from [section 3](#bg-the-motion-planner-toolbox) do the work here. All three use the same search routine, `volley::SingleSourceSearch(source, Interval::Duration(0), environment)`, which expands the garage graph outward from a source node in order of cost. The routine itself knows nothing about trays. That knowledge comes from its last argument, the **search environment**: a small class that tells the search what each step costs, which nodes may be entered, and when a node is a goal. Swapping the environment turns the same routine into a different search ([section 7.4](#mp-tray-searches), with figures). In the table, the first column is that class, the second the scheduler method that runs the search, and the third what the search returns:

| Search environment (goal and cost rules) | Run by                                                      | What the search returns                                                                                                            |
|------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `EmptyTraySearchEnvironment`             | `AssignTrayIdForEmptyMove`                                  | the tray without a payload that is cheapest to bring, searching outward from the destination (travel time + 30 s per tray crossed) |
| `OpenSpaceSearchEnvironment`             | `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution` | a free parking spot (tier 1) or, if `allow_waypoint_stash`, a waypoint (tier 2), plus the trays blocking the way                   |
| `BlockingTraySearchEnvironment`          | the main loop                                               | the critical path from the tray to its destination and the trays on it                                                             |

### The blocking-tray loop

The main loop of `DoTrayAssignments` handles every `TrayMove` that has both a tray id and a destination; it is where blocking trays are found and given moves of their own. The figure first shows, on a small example, why a move can be impossible until another tray moves; the five steps of the loop follow it.

![Blocking tray example](figures/15_blocking_tray_move.svg)

Why blocking trays matter. Step through the plan one move at a time: each numbered arrow appears first as a preview, and AGV-1 drives it in the next step, carrying the tray it has lifted. Root tray R at `P17` must reach bay `B21`. In the Pecos graph `P17` connects only to `P15`, `P20` and charger `C16`; with K at `P15` and T20 at `P20`, every exit is occupied. AGV-1 therefore ① drives under K and lifts it, ② reparks K at the free stall `P19`, ③ returns unloaded to lift R, and ④ carries R out; the bay transition at `B21` comes last. The event card being executed is outlined, and the final step shows the whole plan at once, with dashed outlines marking where K and R started. It does **not** claim the current solver would pick this relocation target or route.

This is what happens to a `TrayMove` that has both a tray id and a destination, such as “R: `P17` → `B21`”. The loop is long in the source (about 450 lines), but it does five things in order:

1.  **Check the destination** (`:2622`–`:2648`). Build a filter that ignores *every* tray and AGV (trays will be moved, AGVs will drive away) and check that the destination vertex is enabled. If it is not, the job fails with “… but it's occupied, or not enabled.” “Occupied” here means something that will not move out of the way: a disabled node, a disabled tray or AGV (its node is blocked at the largest footprint even though it is in the ignore set), or a bay that is not `READY_TO_RETRIEVE` (the call passes no bays to ignore, so a closed bay's overdrive-plate (`BAY_ODP`) area is blocked); ordinary trays and AGVs are ignored.
2.  **Find the critical path** (`:2660`–`:2706`). Search from the root tray to the destination with `BlockingTraySearchEnvironment`. Unlike a normal path search, this one may pass *through* trays; it records them. The result is the **critical path** (the nodes R will travel over) and `blocking_trays`, the trays on it, in path order.
3.  **Resolve blockers one at a time** (`while(!blocking_trays.empty())`, `:2717`). For the first blocker, ask `ResolveBlockingTrays` for a new home that is not on the critical path and does not require moving R. Two fallbacks follow if that fails (below).
4.  **Turn the answer into events** (`:2928`–`:2990`). Add each required move and the blocker's own move to the DAG, chained in order, with `freeing_moves` edges along their paths, and finally an edge “blocker move → root move”. Then re-scan the rest of the critical path for blockers and repeat step 3.
5.  **Finish the root move** (`:3024` onwards). Add `freeing_moves` edges for the destination and source poses, register the source pose, apply the move to `working_state`, and chain it after the tray's previous move.

``` cpp
// Where: Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const, scheduler.cpp:2533,
// inside the per-event loop, once `move` (volley::TrayMove*) has both a tray id and a destination.
//   tray_opt              -> std::optional<DiscreteTrayStateMsg>, the root tray in working_state
//   root_collision_entity -> CollisionEntityId_t for the root tray's footprint (depends on its payload)
//   filters               -> GetStaticFilter(...) ignoring every tray and AGV (they can be moved)
volley::BlockingTrayState source;                                   // search state: a vertex + trays met so far
source.vert = gg_.GetVertexFromPose(tray_opt->pose).value();
volley::BlockingTraySearchEnvironment blocking_search_env(move->GetTrayId().value(), root_collision_entity,
    gg_, table_, working_state, cost_model_, gg_.GetVertexFromPose(move->GetDest().value()).value(), filters);
auto blocking_solution = volley::SingleSourceSearch(source, volley::Interval::Duration(0), blocking_search_env);
auto path = blocking_solution.GetPath(blocking_solution.GetTarget().value()).value();   // the critical path

for(const auto& [path_state, _] : path) {              // collect, in path order:
  critical_path[path_state.vert] = root_collision_entity;   //   the nodes R will occupy
  for(auto id : path_state.blocking_trays) { /* push id into blocking_trays once */ }   // the trays in the way
}

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

The snippet calls seven functions and builds about a dozen local variables. Each function has its own table below, in the order the snippet calls them, followed by one table for the variables. `BlockingTraySearchEnvironment`, `SingleSourceSearch`, `GetStaticFilter` and the search solution come from `motion_planner`; their declarations are in the hover windows, and [section 7](#mp-single-agent-searches) explains all the searches.

**Function 1 · `gg_.GetVertexFromPose(pose)`**: turn a garage pose into a search-graph vertex. Called twice: once for the start, once for the goal.

| Dir | Name   | Type                                 | Meaning                                                                                                                                                                                                         | In [Figure 47](#bg-fig-15_blocking_tray_move)                                                   |
|-----|--------|--------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| in  | `this` | `const volley::GarageGraph&` (`gg_`) | The pose graph ([section 3](#bg-the-physical-garage-and-its-coordinate-system)), read only                                                                                                                      | Pecos graph                                                                                     |
| in  | `pose` | `const GaragePoseMsg&`               | Node id + heading                                                                                                                                                                                               | `tray_opt->pose` = `{node_id: 17, heading: …}`; `move->GetDest()` = `{node_id: 21, heading: …}` |
| out | return | `std::optional<Vertex>`              | The vertex for that pose; empty if the node does not allow that heading. The snippet calls `.value()` without checking: the destination was already checked in step 1, and the tray's own pose is assumed valid | `source.vert`, the goal vertex                                                                  |

**Function 2 · `volley::BlockingTraySearchEnvironment(...)` (constructor)**: describe the critical-path search: where to start, where to go, what blocks the way.

| Dir | Name         | Type                                       | Meaning                                                                                                                                                                          | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|-----|--------------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| in  | `tray_id`    | `uint16_t`                                 | The root tray. It is the one moving, so it is not counted as blocking itself                                                                                                     | R                                             |
| in  | `entity`     | `size_t` (the parameter is `collision_id`) | The root tray's footprint (`root_collision_entity`). A tray with a car is larger than an empty one, so this changes which trays collide                                          | R with a car                                  |
| in  | `gg`         | `const volley::GarageGraph&`               | Graph to search                                                                                                                                                                  | `gg_`                                         |
| in  | `table`      | `const volley::CollisionTable&`            | Answers “does footprint A at pose X overlap footprint B at pose Y?” ([section 3](#bg-the-physical-garage-and-its-coordinate-system))                                             | `table_`                                      |
| in  | `state`      | `const volley::DiscreteGarageState&`       | Where every tray and AGV is right now in the plan                                                                                                                                | `working_state`                               |
| in  | `cost_model` | `const cost::MotionCostModel&`             | Edge cost: the unloaded trapezoid time of the edge, plus 30 s for every tray that the path newly crosses. The heuristic is zero, so this is Dijkstra on that cost                | `cost_model_`                                 |
| in  | `goal`       | `std::optional<Vertex>` (`target`)         | The destination vertex; reaching it ends the search. A further optional argument, `max_blocking_trays`, can cap how many trays a path may cross; tray assignment does not set it | `B21`                                         |
| in  | `filters`    | `std::optional<GraphFilterProperties>`     | Edges the tray may not use at all (this search tests edge flags only). Built with every tray and AGV ignored, so only permanent obstacles block the search                       | from `GetStaticFilter`                        |
| out | object       | `BlockingTraySearchEnvironment`            | Passed to `SingleSourceSearch`. Unlike a normal path search, it lets the path go **through** trays and records each one in the state's `blocking_trays`                          | `blocking_search_env`                         |

**Function 3 · `volley::SingleSourceSearch(source, start_time, env)`**: run the search.

| Dir | Name         | Type                                                        | Meaning                                                                                                                                                         | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|-----|--------------|-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| in  | `source`     | `volley::BlockingTrayState`                                 | Start state: `.vert` set to the root tray's vertex; `.blocking_trays` starts empty                                                                              | `P17`                                         |
| in  | `start_time` | `volley::Interval::Duration` (the parameter is `init_cost`) | The starting cost of the search (A\*'s g value at the source), not a clock time. `Duration(0)`: tray assignment ignores time, so only costs and topology matter | `0`                                           |
| in  | `env`        | the environment (here `BlockingTraySearchEnvironment&`)     | Decides neighbours, costs and the goal test. The same function runs all three searches in this section; only the environment changes                            | `blocking_search_env`                         |
| out | return       | `SearchSolution<BlockingTrayState, Interval::Duration>`     | Holds the explored states; queried with `GetTarget()` and `GetPath()`                                                                                           | `blocking_solution`                           |

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

**Function 6 · `ResolveBlockingTrays(...)`**: find a new home for one blocker. Full description under `AssignDestForUntargetedMove` below.

| Dir | Name                         | Type                                                                                    | Meaning                                                                                                                                                                            | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|-----|------------------------------|-----------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| in  | `this`                       | `const Scheduler*`                                                                      | Read only: `gg_`, `table_`, `cost_model_`, `layout_`                                                                                                                               |                                               |
| in  | `tray_id`                    | `uint16_t`                                                                              | The tray that needs a home. Here it is the **blocker**, not R                                                                                                                      | K                                             |
| in  | `job_index`                  | `size_t`                                                                                | Stored in every `TrayMove` it creates, so blocker moves count as part of R's job                                                                                                   | `move->GetJobIndex()`                         |
| in  | `base_state`                 | `const volley::DiscreteGarageState&`                                                    | Starting state. Copied inside and never changed; nothing is applied to `working_state` yet                                                                                         | `working_state`                               |
| in  | `immobile_trays`             | `const std::set<uint16_t>&` (default `{}`)                                              | Trays the search must route around and may never move. Holding R still stops the solver from “solving” the blocker by moving the root tray                                         | `{R}`                                         |
| in  | `illegal_poses`              | `const VertexCollisionIdMap&` (default `{}`)                                            | Vertices the blocker may not park on                                                                                                                                               | `WithPriorDests(K, critical_path)`            |
| in  | `enforce_retrieval_heading`  | `bool` (default `false`)                                                                | Park facing the node's retrieval heading                                                                                                                                           | `false` (default)                             |
| in  | `allow_waypoint_stash`       | `bool` (default `true`)                                                                 | Allow parking on a waypoint if no stall is reachable                                                                                                                               | `true` (default)                              |
| out | `.first` (`dest`)            | `std::optional<GaragePoseMsg>`                                                          | The blocker's new pose, or empty if none was found (the fallbacks then run)                                                                                                        | `P19`                                         |
| out | `.second` (`required_moves`) | `std::vector<std::pair<std::shared_ptr<volley::TrayMove>, std::vector<GaragePoseMsg>>>` | Moves that must happen before the blocker's own move, in order, each with the poses it passes over. The blocker's own move is **not** in this list; the loop creates it afterwards | `[]`                                          |

**Function 7 · `WithPriorDests(for_tray, base)`**: a local lambda in `DoTrayAssignments` (`:2687`) that builds the `illegal_poses` argument.

| Dir      | Name                        | Type                                                  | Meaning                                                                                       | In [Figure 47](#bg-fig-15_blocking_tray_move) |
|----------|-----------------------------|-------------------------------------------------------|-----------------------------------------------------------------------------------------------|-----------------------------------------------|
| captured | `blocking_tray_prior_dests` | `std::unordered_map<uint16_t, VertexCollisionIdMap>&` | For each blocker, every spot it has already been sent to while clearing this root tray's path | empty at first                                |
| in       | `for_tray`                  | `uint16_t`                                            | The blocker                                                                                   | K                                             |
| in       | `base`                      | `VertexCollisionIdMap` (by value)                     | The starting set of forbidden vertices                                                        | `critical_path` (fallback 2 passes `{}`)      |
| out      | return                      | `VertexCollisionIdMap`                                | `base` plus `for_tray`'s prior spots. Stops a blocker from bouncing between two spots forever | `critical_path` unchanged                     |

**Variables used in the snippet**

| Name                     | Type                                                    | Set where                                                                    | Meaning                                                                                                                 | In [Figure 47](#bg-fig-15_blocking_tray_move)        |
|--------------------------|---------------------------------------------------------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `move`                   | `volley::TrayMove*`                                     | `dynamic_cast` of the current event                                          | The root move being processed; both fields are set                                                                      | R: `P17` → `B21`                                     |
| `event`                  | `std::shared_ptr<volley::ScheduleEvent>`                | loop variable                                                                | The same object as `move`, as the DAG stores it; blocker moves become its prerequisites                                 | the root move                                        |
| `working_state`          | `volley::DiscreteGarageState`                           | copy of `ctx->initial_state`, updated after every applied move               | The garage as it stands at this point in the plan                                                                       | K at `P15`, T20 at `P20`                             |
| `tray_opt`               | `std::optional<DiscreteTrayStateMsg>`                   | `working_state.GetTray(tray_id)`                                             | The root tray's current state (pose, payload)                                                                           | R at `P17`                                           |
| `root_collision_entity`  | `volley::CollisionEntityId_t`                           | `CollisionEntityIdFromTrayState(*tray_opt, working_state, layout)`           | The root tray's footprint, which depends on its payload                                                                 | R with a car                                         |
| `filters`                | `volley::GraphFilterProperties`                         | `GetStaticFilter(TRAY, gg_, working_state, table_, all trays, all AGVs, {})` | Usable edges when every tray and AGV is ignored (closed bays and disabled entities still block)                         | all edges except near disabled nodes and closed bays |
| `source`                 | `volley::BlockingTrayState`                             | built in the snippet                                                         | Search start: `.vert` = R's vertex                                                                                      | `P17`                                                |
| `blocking_search_env`    | `volley::BlockingTraySearchEnvironment`                 | function 2                                                                   | The search description                                                                                                  |                                                      |
| `blocking_solution`      | search solution                                         | function 3                                                                   | The search result                                                                                                       |                                                      |
| `path`                   | `std::vector<std::pair<BlockingTrayState, …>>`          | function 5                                                                   | R's **critical path**: the vertices R travels over, each with the trays in the way there                                | `P17 → P15 → … → B21`                                |
| `path_state`             | `const volley::BlockingTrayState&`                      | loop over `path`                                                             | One step of the path                                                                                                    | the `P15` step                                       |
| `critical_path`          | `VertexCollisionIdMap` (vertex → `CollisionEntityId_t`) | filled from `path`                                                           | Every vertex of R's path tagged with R's footprint; passed as `illegal_poses` so no blocker is parked where R must pass | `P17`, `P15`, …                                      |
| `blocking_trays`         | `std::vector<uint16_t>`                                 | filled from `path_state.blocking_trays`                                      | Trays in R's way, in path order, each once. The `while` loop works through it from the front                            | `[K]`                                                |
| `blocking_tray_set`      | `std::set<uint16_t>`                                    | alongside `blocking_trays`                                                   | Only for de-duplication                                                                                                 | `{K}`                                                |
| `blocking_tray_id`       | `uint16_t`                                              | `blocking_trays.front()`                                                     | The blocker being resolved in this iteration                                                                            | K                                                    |
| `dest`, `required_moves` | see function 6                                          | structured binding of `ResolveBlockingTrays`'s result                        | The blocker's new spot and its prerequisite moves                                                                       | `P19`, `[]`                                          |

**The two fallbacks** (`:2796` and `:2865`). If `ResolveBlockingTrays` returns no destination, the loop first tries to **advance the root tray one step** along its critical path: if no other tray collides with the next pose (`table_.Query(...)`), it creates a one-step `TrayMove` for R, applies it, removes R's old vertex from `critical_path`, and retries the blocker. Advancing frees the node R was on, which can give the blocker somewhere to go (the source comment draws three such cases). If that still fails, it retries with `WithPriorDests(blocking_tray_id, {})`: the blocker **may now park on the critical path**. That is allowed because the loop re-scans afterwards, so a blocker parked ahead of R is simply found and moved again. If even that fails, the job fails with “Failed to find open space for blocking tray t…”.

**Turning the answer into events.** `required_moves` (any prerequisite moves, possibly an advance of R) plus a new `TrayMove` for the blocker are applied to `working_state` in order and added to `ctx->events`, each depending on the one before (`last_move`). Each also depends on the previous move of the same tray (`last_tray_event`) and on whichever earlier events used poses along its path (`freeing_moves.GetBlockers`). The blocker's move is then made a prerequisite of the root move: `ctx->events.AddDependency(new_move, event)`. Finally the loop walks the remaining critical path again, asks `table_.Query` which trays still collide with it, and starts over with that list. The loop ends when the path is clear.

### Filling a blank tray id: `AssignTrayIdForEmptyMove`

Some tray moves are created with a destination but no tray; a `READY_FOR_INSERT` job, for example, asks for “an empty tray into bay B21” without naming one. Before such a move can be planned, tray assignment must choose which empty tray to bring, and `AssignTrayIdForEmptyMove` makes that choice. `DoTrayAssignments` calls it for every event with a blank tray id, and `PlanReadyForInsertJob` calls it earlier, during its own fill pass.

``` cpp
// scheduler.cpp:2159. Called from DoTrayAssignments (:2575) and from PlanReadyForInsertJob's fill pass (:1271).
BoolStringPair Scheduler::AssignTrayIdForEmptyMove(
    volley::TrayMove& move, const volley::DiscreteGarageState& working_state) const;
```

| Dir              | Name            | Type                                              | Meaning                                                                                                                                      | In the example below                                                                                                                 |
|------------------|-----------------|---------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| in               | `this`          | `const Scheduler*`                                | Fixed planner data, read only: `gg_`, `table_`, `cost_model_`, `layout_`                                                                     | Pecos layout                                                                                                                         |
| in / **changed** | `move`          | `volley::TrayMove&`                               | The event with the blank tray id. Must already have a destination. On success its tray id is set and its destination heading may be adjusted | `{tray_id: ?, dest: {node_id: 21, heading: -90}}` becomes `{tray_id: 23, dest: {node_id: 21, heading: -90}}` (tray 23 starts at P23) |
| in               | `working_state` | `const volley::DiscreteGarageState&`              | The garage as it will be when this event runs (all earlier events applied). Only read                                                        | T23 (empty) at `P23`, loaded trays elsewhere                                                                                         |
| out              | return          | `BoolStringPair` (`std::pair<bool, std::string>`) | `{true, ""}`, or `{false, reason}`                                                                                                           | `{true, ""}`                                                                                                                         |

![AssignTrayIdForEmptyMove](figures/55_assign_tray_id_empty.svg)

`AssignTrayIdForEmptyMove` on a `READY_FOR_INSERT` job. The job asked for “an empty tray into `B21`”, so its `TrayMove` has a destination but no tray. Step through the method: the helper checks the destination, builds a filter that ignores every tray and AGV, then searches **outward from the destination** (numbers show the order nodes are reached) and stops at the first tray without a payload, T23 at `P23`. Loaded trays such as T20 and T24 are passed over, and T15, also empty, is farther away. It writes T23 into the same event and adds no events or edges. The heading stays as it is, and the main blocking-tray loop then plans T23's path to the bay. The last two steps play the completed event with an illustrative AGV-1, which carries T23 into the bay. Search order is illustrative.

How it works, step by step:

1.  **Require a destination.** A move with neither field set cannot be resolved: `{false, "Can't resolve a tray move with no tray id or dest"}`.
2.  **Start the search at the destination.** The question is “which empty tray is cheapest to bring *to where one is needed*”, so the source vertex is the destination pose (`{node_id: 21, heading: -90}`, B21: B21 lists heading 90 with `faces_reciprocal: true`, so its inbound heading is −90), not any tray. The code calls this “basically the inverse OpenSpaceSearch”.
3.  **Ignore everything movable.** `GetStaticFilter(TRAY, gg_, working_state, table_, all trays, all agvs, {})` makes every tray and AGV transparent (how the filter is built: [section 7.3](#mp-static-filters)). Only static obstacles (disabled nodes and entities, closed bays, nodes the tray footprint cannot use) block the search, so a buried empty tray can still be chosen; the main loop will clear the way afterwards.
4.  **Search.** `EmptyTraySearchEnvironment(gg_, table_, working_state, cost_model_, filters)` treats a vertex as a goal when it holds a tray with no payload. The environment inherits the blocking-tray search's costs: each edge costs its trapezoid time plus 30 s for every tray it crosses. `SingleSourceSearch` expands vertices by cost, so the first goal reached is the cheapest to reach, not necessarily the fewest hops. No goal → `{false, "Failed to find empty tray to move to <dest>"}`. The environment and the engine are explained in [section 7.4](#mp-tray-searches).
5.  **Read the tray.** `working_state.GetTrayOnNode(node_id_of(target))` → `move.SetTrayId(tray.id)`.
6.  **Avoid pointless rotation.** If the tray's heading is the destination heading or its reciprocal (`IsAngleOrReciprocal`) but not equal, the destination heading is changed to the tray's heading (an empty tray has no front), then `UseEvChargeHeading` restores the heading if the destination is an EV-charging spot that needs a specific one.

Three consequences are easy to miss:

- **Nothing is reserved.** The helper does not apply the move or touch `freeing_moves`. T23 is “taken” only because `DoTrayAssignments` continues straight into the main loop and applies the move to `working_state` there; a later event will then see T23 in the bay.
- **Distance is measured from the bay, not from the AGV.** The chosen tray minimises travel time from the destination plus 30 s per tray in the way, so a near tray behind several blockers can lose to a farther free one. Where the AGV is does not matter. A TODO in the code suggests preferring a tray that will be a blocker anyway.
- **The search repeats work.** The main loop runs a second search (the critical path) over roughly the same ground; the source comment calls this a future optimisation.

### Filling a blank destination: `AssignDestForUntargetedMove`

Other tray moves are created with a tray but no destination, such as the move that takes an empty tray out of a bay during a `RETRIEVE`, or the move that sends a car's tray into storage after an `INSERT`. `AssignDestForUntargetedMove` chooses where such a tray goes and adds moves for any trays in its way. `DoTrayAssignments` is its only caller, and once it returns, the main blocking-tray loop is skipped for that event.

``` cpp
// scheduler.cpp:2222. Called only from DoTrayAssignments (:2584); the caller then `continue`s.
BoolStringPair Scheduler::AssignDestForUntargetedMove(volley::TrayMove* move, ScheduleContextSPtr ctx,
    const std::shared_ptr<volley::ScheduleEvent>& event, volley::DiscreteGarageState& working_state,
    volley::GarageOccupancyChecker<std::shared_ptr<volley::ScheduleEvent>>& freeing_moves,
    std::unordered_map<uint16_t, std::shared_ptr<volley::ScheduleEvent>>& last_tray_event) const;
```

| Dir              | Name              | Type                                                            | Meaning                                                                                                              | In the example below                                                                                       |
|------------------|-------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| in               | `this`            | `const Scheduler*`                                              | Fixed planner data, read only: `gg_`, `table_`, `cost_model_`, `layout_`                                             | Pecos layout                                                                                               |
| in / **changed** | `move`            | `volley::TrayMove*`                                             | The event with the blank destination, viewed as a `TrayMove`. Must have a tray id. On success its destination is set | `{tray_id: 21, dest: ?}` becomes `{tray_id: 21, dest: {node_id: 23, heading: 90}}` (tray 21 starts in B21) |
| in               | `event`           | `const std::shared_ptr<volley::ScheduleEvent>&`                 | The **same** object as `move`, as the DAG knows it; needed for `AddDependency`                                       | event 1                                                                                                    |
| in / **changed** | `ctx`             | `ScheduleContextSPtr`                                           | Changed: `ctx->events` (new blocker moves and edges) and `ctx->first_tray_event`                                     | +1 event, +1 edge                                                                                          |
| in / **changed** | `working_state`   | `volley::DiscreteGarageState&`                                  | Every new move and then `move` itself are applied to it                                                              | T23 now at `P24`, T21 at `P23`                                                                             |
| in / **changed** | `freeing_moves`   | `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>&`       | Gains the poses used by the new blocker moves                                                                        | `P23`, `P24`                                                                                               |
| in / **changed** | `last_tray_event` | `std::unordered_map<uint16_t, std::shared_ptr<ScheduleEvent>>&` | Per-tray “latest move so far”, updated for each new move and for `move`                                              | `[23]`, `[21]`                                                                                             |
| out              | return            | `BoolStringPair`                                                | `{true, ""}`, or `{false, reason}`                                                                                   | `{true, ""}`                                                                                               |

![AssignDestForUntargetedMove](figures/56_assign_dest_untargeted.svg)

`AssignDestForUntargetedMove` on a `RETRIEVE` job. Before the car can come out, the empty tray T21 must leave bay `B21`, but the job did not say where to, so the event is `T21: B21 → ?`. Step through the method: `ResolveBlockingTrays` works on a private copy of the garage and searches for open space from the bay. Its first answer, `P24` (red), is behind T23, so with `W41`, `W22` and `P23` off-limits it moves the blocker T23 one stall **deeper** into `P24` (2), then searches again and finds `P23` free and close (3). The helper writes `P23` into the original event, adds T23's move as a new event, and adds the edge “T23's move → T21's move”. T9, stashed on waypoint `W25` by an earlier plan, is the tier-2 case described below. The last four steps play the result with an illustrative AGV-1: T23 moves to `P24`, then T21 moves from the bay into `P23`. Search results are illustrative; the real cost of a path is its trapezoid travel time plus 30 s per tray crossed ([section 7.4](#mp-tray-searches)).

The helper is a thin wrapper; the real work is done by `ResolveBlockingTrays`. In order:

1.  **Check inputs.** The move must have a tray id, and that tray must exist in `working_state`.
2.  **Decide whether heading matters.** `enforce_retrieval_heading = working_state.GetPayload(tray->payload_id).has_value()`. A tray with a car must be parked facing the way it will later leave (the node's *retrieval heading*); an empty tray need not.
3.  **Find a destination and the moves needed to reach it**: `ResolveBlockingTrays(tray_id, job_index, working_state, {}, {}, enforce_retrieval_heading)`. No tray is immobile and no pose is illegal, because this tray has no critical path to protect; `allow_waypoint_stash` keeps its default `true`. No destination → `{false, "Failed to find open space for t<id>"}`.
4.  **Fix the heading** (not for bays or VECS; only for `TYPE_PARKING` nodes). Empty tray: keep its current heading if the destination is on the same axis. Loaded tray: `UsePreferredHeading(dest, payload, tray)` (the retrieval heading was already chosen by the search; this mostly handles EV charging). Then `UseEvChargeHeading(dest)` and `move->SetDest(dest)`.
5.  **Emit the extra moves.** For each `(new_move, path)` in `required_moves`, in order: apply it to `working_state`; `ctx->events.AddEvent(new_move)`; add an edge from the previous required move (`last_move`) and from this tray's previous move (`last_tray_event`), or record it in `ctx->first_tray_event` if it is the tray's first; for every pose on `path`, add edges from earlier events that used that pose (`freeing_moves.GetBlockers`) and register the pose (`AddOccupant`); register the tray's source pose too.
6.  **Finish the original move.** Apply `move` to `working_state`, add `last_move → event` so the original move waits for the last blocker move, and chain it into `last_tray_event`.
7.  **Return**, and the caller `continue`s: the main blocking-tray loop does not run for this event, because `ResolveBlockingTrays` already cleared the way.

Two details differ from the main loop. First, step 5's `new_move`s get `freeing_moves` edges, but the **original move itself does not**: its source and destination poses are not checked with `GetBlockers` or registered with `AddOccupant`. Its ordering relies on the chain “last blocker move → event” and on edges the job method already added. Keep this in mind when debugging a missing edge after an untargeted move. Second, a blocker move produced by recursion has an empty path (see `BlockingTrayResolution` below), so it gets no path edges either; it is ordered only by the `last_move` chain.

#### Inside `ResolveBlockingTrays`

`ResolveBlockingTrays` (`scheduler.cpp:1984`, declared at `scheduler.hpp:299`) answers one question: “where can *this* tray go, and what has to move first?” It is used for a tray with no destination (above) and for a blocker in the main loop. It never changes the caller's state: it copies `base_state` into its own `working_state` and applies its trial moves there.

| Dir | Name                        | Type                                                                            | Meaning                                                                                                | Main loop passes            | `AssignDest…` passes               |
|-----|-----------------------------|---------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|-----------------------------|------------------------------------|
| in  | `tray_id`                   | `uint16_t`                                                                      | The tray that needs a home                                                                             | the blocker                 | the move's tray                    |
| in  | `job_index`                 | `size_t`                                                                        | Stored in every `TrayMove` it creates                                                                  | root move's job             | move's job                         |
| in  | `base_state`                | `const DiscreteGarageState&`                                                    | Starting state; copied, never changed                                                                  | `working_state`             | `working_state`                    |
| in  | `immobile_trays`            | `const std::set<uint16_t>&` (default `{}`)                                      | Trays the search must route around and may never move                                                  | `{root}`                    | `{}`                               |
| in  | `illegal_poses`             | `const VertexCollisionIdMap&` (default `{}`)                                    | Vertices the tray may not park on                                                                      | critical path + prior dests | `{}`                               |
| in  | `enforce_retrieval_heading` | `bool` (default `false`)                                                        | Park facing the retrieval heading                                                                      | `false` (default)           | `true` if the tray has a payload   |
| in  | `allow_waypoint_stash`      | `bool` (default `true`)                                                         | Allow tier 2: park on a waypoint if no stall is reachable                                              | `true` (default)            | `true` (default)                   |
| out | `.first`                    | `std::optional<GaragePoseMsg>`                                                  | The tray's new destination, or empty on failure                                                        | K → `P19`                   | `{node_id: 23, heading: 90}` (P23) |
| out | `.second`                   | `std::vector<std::pair<std::shared_ptr<TrayMove>, std::vector<GaragePoseMsg>>>` | Moves that must happen first, in order, each with the poses it travels over (empty for recursive ones) | `[]`                        | `[(T23 → P24, path)]`              |

Its loop, `while(!dest)`:

1.  **Search for open space for the tray**: `FindOpenSpaceForRootTray(...)` (`:1850`). Tier 1 accepts only free parking and EV-charge nodes (“free” meaning no tray on the node). If nothing is found and stashing is allowed, tier 2 retries accepting waypoints (with `enforce_retrieval_heading = false`). Like the critical-path search, this search may pass through any tray not in `immobile_trays` and reports the trays it passed through. It also returns `blocking_tray_illegal_poses`: `illegal_poses` plus every intermediate vertex of the tray's path, so the blockers will not be parked in its way. The target itself is left legal on purpose (the source comment explains it avoids a cycle). Nothing found → return `{nullopt, {}}`.
2.  **No blockers on the way?** Then this is the destination: `dest = target`, and the loop ends.
3.  **Otherwise move one blocker.** For each blocker of that target, in order, call `TryFindBlockingTrayResolution(...)` (`:1895`) until one succeeds. It searches open space for the blocker (parking first, then waypoints). If the blocker's best spot is free, it returns that spot and the path. If the blocker is itself blocked, it **recurses** into `ResolveBlockingTrays` for the blocker with the current tray added to `immobile_trays` (so the chain cannot loop back), and returns the recursion's moves as `prereq_moves` with an empty `path`. No blocker can be resolved → return `{nullopt, {}}`.
4.  **Apply the result to the private copy**: each prerequisite move, then a new `TrayMove(job_index)` for the blocker to its spot. Append them to `required_moves` and go back to step 1.

Searching again after every single blocker move is what makes the result **dense**. The code comment says the aim is to “push them deeper and park in a good spot” instead of “reparking blocking trays halfway across the garage”. In [Figure 49](#bg-fig-56_assign_dest_untargeted), moving T23 one stall deeper makes `P23` free, and the next search picks it. The unit test `ResolveBlockingTraysRecursivelyUnblocksChain` exercises a chain of three trays.

A **tier-2 waypoint stash** (T9 on `W25` in [Figure 49](#bg-fig-56_assign_dest_untargeted)) is a deliberate half-solution: the tray is left on a travel node so the current plan can go ahead, and a later `CLEAN_GARAGE` job runs `PlanUnstashWaypointTraysJob`, which plans an untargeted move for every stashed tray and so comes back through this same helper.

### Occupancy becomes dependencies: `freeing_moves`

Choosing destinations and moving blockers decides where trays go, but not yet when a move may enter space that an earlier event uses. `freeing_moves` records which events have used each pose, so that tray assignment can add an edge from those events to any later move through a colliding pose. The figure shows how the records fill up and become edges.

![freeing_moves](figures/28_freeing_moves.svg)

`freeing_moves` is a `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>`. Every event that used a pose (a source pose, every pose on a path, a bay pose touched by a transition) is recorded. A later move through a colliding pose gets an edge from each recorded event. The checker uses `table_`, so “colliding” means overlapping footprints, not just equal node ids. Step through to watch the records fill up while each tray glides to its new spot in `working_state` (a dashed arrow previews the move one step earlier), then see `GetBlockers` turn the records into the three edges into e2, and finally T17 reach `B21` once e2 is applied.

Two pieces of bookkeeping leave this stage:

- `last_tray_event` (a local map) chains successive moves of the same tray.
- `ctx->first_tray_event[tray_id]` remembers the **first** move that takes each tray off its initial node. `DoAgvAssignments` uses it so an AGV that must drive through that node waits for the tray to leave. Using the *last* move instead would create a cycle when one AGV moves the same tray twice (see the comment in `scheduler.hpp`).

`DoTrayAssignments` deliberately does **not** call `Reduce()` at the end; a source comment says doing so breaks the following AGV assignment.

## AGV assignment: `DoAgvAssignments`

Now every `TrayMove` knows *what* moves where. `DoAgvAssignments(ctx)` decides *which AGV* does each one and adds the AGV's own events. It works on `event_dag_copy`, a copy of `ctx->events` that it consumes from the roots down:

1.  **Drain non-tray roots.** Apply every root that is not a `TrayMove` (bay and VECS transitions, pre-existing `AgvMove`s) to `working_state`, chain AGV moves per AGV, add node-arrival dependencies, and remove them from the copy. Repeat until only `TrayMove` roots remain, so the matcher sees every eligible move at once (the SW2-377 comment explains why).
2.  **Cost every (AGV, root move) pair** with `GetAgvToTrayAssignmentCost`. Pairs are infeasible when the AGV carries a different tray, has no path, or is trapped in a bay that is not `READY_TO_RETRIEVE`.
3.  **Match** with `volley::BottleneckAssignment` and order matched AGVs that would collide with `GetEventDag`.
4.  **Expand** each match into events and remove the matched `TrayMove` from the copy.
5.  Repeat until the copy is empty, then run `EnsureAgvMovePathsClear`, `Reduce()`, and `AddDepsAfterAmiga` for bay and VECS transitions.

![AGV matching](figures/29_agv_matching.svg)

Matching AGVs to root tray moves. Each edge is one feasible pair with its estimated cost; AGV-3 carries another tray, so it has no edges. Bottleneck matching minimises the **worst** single cost, so it can prefer a pairing with a higher total. Step through the cost table entry by entry, then watch the allowed cost rise until both moves are matched. The last two steps play the result: AGV-1 drives to T15 for e4, then AGV-2 drives into `B21` under T21 for e1. Costs are illustrative.

The cost of assigning AGV **i** to tray move **j** is

c\_{ij}=\max\\\left(t_i^{\mathrm{occupied}}-t_j^{\mathrm{ready}},\\0\right)+t\_{ij}^{\mathrm{approach}}+t\_{ij}^{\mathrm{lift}},

where cost **c\_{ij}** \[s\] is the estimated time until the tray is lifted, **t_i^{\mathrm{occupied}}** \[s\] is how long AGV **i** is already busy (`agv_occupied_durations`), **t_j^{\mathrm{ready}}** \[s\] is the earliest time move **j** can start given its parents (`event_occupied_durations`, filled by `PropagateEventCostToChildren`), **t\_{ij}^{\mathrm{approach}}** \[s\] is `GetJustMovingCost` from the AGV's pose to the tray's pose, and **t\_{ij}^{\mathrm{lift}}** \[s\] is the lift-up time when the AGV is not already holding the tray. **Caveats:** `GetAgvOccupiedDuration()` returns zero (a `TODO(isabel)`), so the occupied term only reflects work assigned earlier in the same call. The approach time is a single-AGV estimate (`GetPosePath` + `ConvertPosePathToTrajectory`; [section 7.5](#mp-pose-path)): it ignores waiting for other AGVs and wheel turns, which only CHUGG accounts for ([section 23.2](#bg-the-cost-model)).

![AGV approach](figures/15_agv_approach_and_pickup.svg)

Approach, lift, carry and lower. Step through as hypothetical AGV-1 at charger `C10` drives, one edge per step, to tray T15 at `P3` via `10 → 9 → 11 → 6 → 3`, passing under the empty stall `P6`; a dashed arrow previews each edge one step before AGV-1 drives it. AGV-1 then lifts T15, carries it (T15 rides along) to an example destination (`P2`) and lowers it. The strip restates each step as a simplified event as it happens. The route is a graph walk, not a recorded run.

![AGV event expansion](figures/30_agv_event_expansion.svg)

What one assignment adds: `MoveAgvToTrayPose` (skipped if the AGV is already there), a lift, `SetAgvId` on the `TrayMove`, and a lower. The first event gets edges from four sources: the AGV's previous event, the first move of any tray parked on its navigation path, the previous occupant of the destination node, and matched AGVs it must follow. Step through to see the events created one at a time, then each kind of incoming edge, then the cost that is passed on to the children.

``` cpp
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

Once every tray move has an AGV, one more pass checks that each AGV reposition can reach its target in the order in which the DAG will be replayed. `EnsureAgvMovePathsClear` performs this check and adds an edge where another AGV stands in the way; the reason the pass is needed follows the figure.

![AGV path repair](figures/31_agv_path_repair.svg)

`EnsureAgvMovePathsClear` replays the final topological order. When an AGV reposition has no collision-free path only because another AGV's body is in the way, it adds one edge from that AGV's next departure to the blocked move (unless that would form a cycle) and starts over, at most 256 times. Tray and disabled-node obstructions are left for `SanityCheckEvents` to report. Step through the five checks of `TryClearBlockedAgvMove()` on one blocked move, then play the repaired order: AGV-2 first leaves `W13` for `P15`, and only then AGV-1 drives through to `W8`.

This pass exists because `DoAgvAssignments` builds dependencies in its own serial assignment order, which can differ from the order the DAG is eventually replayed in. The source comments in `MoveAgvToTrayPose` describe an earlier, proactive attempt that both missed real blockers and added spurious edges.

`AddDepsAfterAmiga(ctx, event, node_id)` runs last for every bay and VECS transition. It moves dependencies from tray moves onto the AGV's lift and lower events: a transition that waited for a tray to arrive now waits for the **lower** after it, and a tray move out of the bay waits for the transition before its **lift**.

## `Reduce()` and `SanityCheckEvents`

Back in `Plan()`, `plan_ctx->events.Reduce()` removes redundant edges (a `TODO(any)` notes that planning may fail without it; [section 21.1](#bg-inside-solvesequential) shows a code path in CHUGG that would explain this). Then `SanityCheckEvents(ctx)` replays the DAG in topological order on a fresh copy of `initial_state` and checks each event **before** applying it:

| Event                        | Check                                                                                                             |
|------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `BayTransition`              | the bay's ODP (overdrive plate) area is free (`GetStaticFilter` for `BAY_ODP`)                                    |
| `AgvMove` with a destination | `IsMovePossible`: destination exists, is not disabled, is not occupied, and a path exists, ignoring only this AGV |
| `AgvMove` lift change        | only that `Apply` succeeds                                                                                        |
| `TrayMove`                   | has a destination, and `IsMovePossible` with the carrying AGV and the tray itself ignored                         |

The comment explains the motivation: “The motion planner doesn't fail in the most graceful ways”, so a cheap discrete replay catches most problems with a readable message first. It is the last step of task planning: from here the event DAG is final, and motion planning hands it to CHUGG ([section 1](#bg-motion-planning-and-the-response)). CHUGG replays it once more in `InitializeEventOrder` and throws, rather than failing gracefully, if that replay breaks.

**Where `Reduce()` runs matters.** It runs at the end of AGV assignment and again in `Plan()`, and the code does not say why that placement is needed ([section 13](#pr-risks-that-must-not-be-silently-fixed), risk 2); [Section 21.1](#bg-inside-solvesequential) gives a reading of CHUGG's code that would explain the motion-planning case. Risk 3 in the same list gives a likely reason for the tray-assignment case: two AGV-assignment helpers look only at direct edges, which `Reduce()` may replace with longer paths. A test shows the visible effect: after `DoAgvAssignments`, the direct edges `tray_move_1 → tray_move_2` that the test added are gone (`EXPECT_FALSE(ctx->events.HasDependency(...))`), because the AGV chains now imply them. `HasDependency` checks a direct edge only, so after `Reduce()` it is the wrong question for “must a finish before b?”.

## Bays, VECS and VRCs

The bay, VECS and VRC rules cut across the stages above: job methods choose bays and stop chargers, tray assignment avoids closed bay doors, and the action graph adds VRC trips. This section collects them in one place.

### Bays and rebalancing

Bays are where customers leave and collect their cars, so the scheduler keeps some bays ready for insert and others ready for retrieve. This subsection covers the bay commands the scheduler issues, how `ClassifyBay` classifies each bay, and how `ComputeBayRebalancingActions` chooses the bays that a `TYPE_REBALANCE_GARAGE` job switches.

![Bay logic](figures/33_bay_logic.svg)

The three bay commands the scheduler issues, the `ClassifyBay` rules from `utils.cpp`, and a worked example of `ComputeBayRebalancingActions`. Step through it: first the commands and the classification rules, then the example one loop at a time. Each loop walks `bay_prioritization` in the direction shown, keeps or picks bays, and updates how many insert-ready and retrieve-ready bays are still wanted. Other bay states are reached through bay or customer activity outside this package.

`bay_readiness_ratio` is the fraction of usable bays that should be ready for insert. `CalculateDesiredBaySplit` rounds up (it biases towards insert because arriving customers cannot be detected), clamps, and never asks for more insert-ready bays than there are empty trays. `ComputeBayRebalancingActions` first counts bays already moving towards a state (`WILL_BE_*`), then keeps bays already in a wanted state, and only then picks bays to change, in `bay_prioritization` order for insert and reverse order for retrieve. Bays left in an invalid state fall back to ready-for-retrieve.

### VECS (EV charging)

A VECS sits on a node of type `TYPE_EV_CHARGE` (6, a node type of its own; its VECS id is the node id). Moving a tray off a VECS that is `CHARGING` first adds `VecsTransition CHARGING -> READY_TO_CHARGE`; moving onto one is refused unless it is `READY_TO_CHARGE`. `PlanChargePayloadJob` finds a VECS with `ResolveBlockingTrays`: for a payload with `ev_charge_requested`, the open-space search accepts only `EV_CHARGE` nodes at a heading between 0 and 90 ([section 7.4](#mp-tray-searches)); it does not look at the VECS state, and the job afterwards only checks that the node has a VECS before adding `READY_TO_CHARGE -> CHARGING`. A VECS in another state is therefore caught only when the events are replayed (the move onto it is refused).

### VRCs (lifts between floors)

Task planning creates no VRC events. An AGV move between floors is planned like any other move, and the scheduler adds the VRC commands later, to the action DAG, after motion planning ([section 6.3](#bg-vrcs-lifts-between-floors)). Assignment is not floor-aware either: trays, parking spots and AGVs are chosen by search cost alone, and a VRC ride is just another edge in those searches. The status of VRC support in every stage is summarised in the Layout file tab ([section 7](#ly-vrc-support-status)).
