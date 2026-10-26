# 06 — Dispatch: the scheduler's only client

*The `central` package runs the garage: it queues jobs, decides when to plan, calls the scheduler, checks the answer and sends commands to the machines. This tab outlines it from the scheduler's side: what Dispatch sends, what it expects back and what it does with the result. It is an overview, meant to be expanded.*

The earlier tabs read the scheduler as a pure function of one `PlanRequest`. This tab is about where that request comes from. Read it after the Background tab's message sections ([section 6](#bg-ros-messages-and-services)) and before the proposal: several proposal items depend on what Dispatch accepts.

## The `central` package at a glance

`central` is a set of ROS 2 components. Only one of them, the dispatcher, talks to the scheduler, through one service call.

![The central package around the scheduler](figures/123_central_components.svg)

**The central package around the scheduler.** Jobs come in through the dispatcher's services; the garage tracker is the source of truth for the garage; the dispatcher sends a `PlanRequest` to `/scheduler/plan`, turns the response into commands for the machines, and watches their reports. The monitors check versions, batteries and status.

| Component                                                                      | What it does                                                                                                                                                      | Link to the scheduler                                                                                                     |
|--------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `dispatcher` (`Dispatch`, `DispatchRos`)                                       | Holds the job queue and the executing schedule; calls the planner; sends commands; publishes the schedule, job lists and reports                                  | The only client of `/scheduler/plan`. Also publishes each request and response on a topic so they can be recorded in bags |
| `garage_tracker`                                                               | The source of truth for the garage: turns machine reports into `DiscreteGarageState`, discrete events and continuous info; owns the `set_*_disabledness` services | Indirect: `PlanRequest.base_state` is Dispatch's copy of this state                                                       |
| `consistency_monitor`                                                          | Compares the git hash and layout checksum reported by every component                                                                                             | The scheduler's version info is checked too; a mismatch stops the dispatcher                                              |
| `agv_monitor`                                                                  | Disables AGVs whose battery is low                                                                                                                                | Shows up as `agv.disabled` in `base_state`                                                                                |
| `garage_monitor`, `metrics_recorder`, `mqtt_bridge`, `safety_hardware_monitor` | Garage status, metrics, cloud bridge, logging                                                                                                                     | None                                                                                                                      |

## Jobs in Dispatch

Dispatch keeps every job as a `Job` object (one subclass per `SchedulerJob` type) and moves its guid between three lists:

- **`jobs_pending_`**: registered, not yet planned, in arrival order. These become `pending_jobs`.
- **`jobs_active_`**: planned; their actions are in the executing schedule. Each job stores the guids of the actions that must complete (from `ScheduledJobData.node_indices`). These become `active_jobs`.
- **`jobs_completed_`**: finished with SUCCESS (all its actions complete) or ERROR.

Jobs come from the dispatcher's services (retrieve, move AGV, move or repark a tray, charge a payload, transition a bay, clean, rebalance), from bay events (a car driven into a bay creates an INSERT), and from Dispatch itself: a clean and a rebalance when it starts in automatic mode or when the last active job finishes, charge jobs for idle AGVs, and a periodic clean while idle. `READY_FOR_INSERT` and `READY_FOR_RETRIEVE` jobs exist as classes but are never created by Dispatch.

## The plan loop and what goes into a `PlanRequest`

Dispatch does not call the scheduler for each new job; it plans from a timer, under a set of conditions, and assembles each request from its own job lists and garage state. This section covers when a plan call is made, what each field of the `PlanRequest` contains, and how the request is reduced when a response fails; the figure shows the whole call as Dispatch sees it.

![One plan call seen from Dispatch](figures/124_plan_call_sequence.svg)

**One plan call seen from Dispatch.** Step through it: the timer decides to plan, the request is built and sent, the scheduler answers, Dispatch checks the answer, builds a new execution state, updates the jobs, sends ready commands and completes jobs as the machines report.

**When Dispatch plans.** A timer fires every 850 ms and calls `ShouldCallPlanner()`. It returns true only if all of these hold:

1.  the dispatcher is RUNNING;
2.  no plan call is in flight (there is never more than one);
3.  no job is active, because `enable_overlapping_planning_` is `false` and nothing sets it;
4.  at least one enabled, active AGV has no remaining move in the schedule;
5.  some pending job is worth planning (a RETRIEVE that is waiting for a bay is skipped until a bay will be ready).

**What it sends.** `GetPlannerServiceRequest` fills the request:

| Field           | Filled with                                                                                                                                                                                                         |
|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `id`            | A new Guid, remembered with the call                                                                                                                                                                                |
| `base_state`    | `GetLatest()`: Dispatch's copy of the garage, advanced by completion events. Not the state at the end of the schedule                                                                                               |
| `base_schedule` | Only if some job is active: every incomplete node of the current schedule, parents renumbered, also remembered with the call. The split that would hold back nodes beyond the 30 s command horizon is commented out |
| `active_jobs`   | Every job in `jobs_active_`                                                                                                                                                                                         |
| `planned_jobs`  | Never filled                                                                                                                                                                                                        |
| `pending_jobs`  | Pending jobs marked worth planning, in queue order, capped by the request strategy. While jobs are active, the loop stops at the first CLEAN_GARAGE                                                                 |

With condition 3 in place, every call made today has an empty `base_schedule` and empty `active_jobs`. The fields and the scheduler's reservation logic are ready for overlapping planning, but it is switched off (Background, [section 6.2](#bg-planrequest-one-moment-in-a-running-schedule)).

**Request strategy.** By default every worth-planning job is sent. When a response comes back with more than one job and all of them failed, Dispatch rejects it and steps down to a smaller request: at most as many jobs as active AGVs, then as many as free AGVs, then one job at a time. The strategy resets to unlimited when no job is active.

## What Dispatch does with the response

`PlanClientCallback` checks the response in this order; any failure rejects the whole response (`RejectPlanResponse`) and the jobs stay pending:

1.  an execution state exists, and the response `id` matches the call in flight;
2.  `success` is true (the scheduler returns `false` only for an invalid `base_state`);
3.  the execution state has not diverged from the garage;
4.  every node of the `base_schedule` it sent is in the response, **field for field unchanged**;
5.  if more than one job was sent, not all of them failed (otherwise: retry counter, smaller strategy, reject).

It then builds a new `ExecutionState` from the **response nodes alone**: nodes already completed are skipped, parents are renumbered, AGV command source and destination fields are rewritten from Dispatch's future state (the lift flags of a move, the poses of a lift), and every node is applied to the future state. Each returned job is then moved:

- **STATE_EXECUTING**: pending to active, with the guids of its `node_indices` as the actions to complete; a RETRIEVE also stores `bay_id` and `bay_arrival_node_guid`, and Dispatch computes `seconds_to_bay_arrival` itself from the schedule.
- **STATE_ERROR**: completed with an error, except a RETRIEVE, which stays pending if `retain_job` is set, or is moved to the back of the queue up to ten times.

## Executing the schedule

An `ExecutionState` holds the schedule (the action DAG as an array, with a status per node) and two garage states: *latest*, advanced as actions complete, and *future*, the garage after the whole schedule. Appending a node requires that it depends on the previous action of the same machine, so every machine's actions form a chain.

Commands are sent when an action is ready (its parents are complete), it is expected to start within the 30 s command horizon, and the safety checker (`GarageSafetyChecker`, common_ros) accepts it. Consecutive AGV moves are chained into one command list. As the garage tracker reports discrete events, each one completes the matching action and advances the latest state; a job whose actions are all complete becomes SUCCESS. If an event does not match the schedule, the execution state is marked diverged, and the dispatcher stops (it also stops on stale reports, a garage fault or an inconsistent version report), which errors out every pending and active job.

## What this means for the scheduler

Read from Dispatch's side, the interface has these properties and gaps:

- **Plans happen only when the fleet has no active job.** The reservation of `base_schedule` (Background, [section 11](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)) never fires today.
- **Overlapping planning needs a scheduler change first.** Dispatch expects the response to contain every `base_schedule` node unchanged, plus the new nodes; the scheduler returns only the new nodes. Turning the flag on today would reject every response made while jobs are active.
- **The intended design is to append, with dependencies.** A comment in `GetPlannerServiceRequest` explains why the running schedule is sent rather than the end state: the planner should build dependencies between the existing part of the schedule and the new part. That matches the time-bounded reservation idea in the proposal ([section 7.5](#pr-base-schedule-reservation)).
- **Some fields are ignored or overwritten.** `planned_jobs` is never sent; `seconds_to_bay_arrival` is computed by Dispatch; AGV command ids and parts of `src` / `dst` are rewritten when nodes are appended.
- **`success = false` is rare by design**, and Dispatch relies on per-job states. A job missing from `scheduled_jobs` silently stays pending.
- **Dispatch-side issues seen while reading** (for the central owners): no timeout on a lost plan response, so planning stops until the next mismatched response; the CLEAN_GARAGE `break` blocks every job queued behind it (only while jobs are active); the free-AGV count used by one request strategy is reset to 0, so that strategy always sends one job.

## To expand

Topics this outline leaves for later:

- The `Job` classes and the services that create them, one by one.
- `ExecutionState` and `Schedule` in depth: motion batches, chaining, the safety checker, completion matching for each event type.
- The garage tracker: how reports become discrete events, recovery from MySQL, disabledness services.
- Charging mode (`ChargeAgvs`), garage dirtiness and the idle clean and rebalance jobs.
- The split (`SplitSchedule`, `outside_split`) and what overlapping planning would need on both sides.
- Stop, pause and restart behaviour, and what happens to jobs and the schedule.
