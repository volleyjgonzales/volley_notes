# Follow-up tickets from Dan's review of PR #1018 (created 2026-11-03)

Three tickets promised in the replies to Dan (`codex_reviews/dan_review_1.md`, items 9-11). Each is a
**Task** under epic SW2-482 (Scheduler Core Refactor), label `Scheduler_and_Dispatcher`, priority
Medium, assignee Jon M Gonzales, linked "is blocked by" SW2-1135. Create them the way
`jira_ticket.md` describes; paste each "Description" into the Description field.

---

## 1. Return stdx::Result from event application (`ApplyTo`, `ApplyBayCommand`, `DiscreteGarageState`)

https://volleyautomation.atlassian.net/browse/SW2-1170

### Description

#### Objective

`ScheduleEvent::ApplyTo` and `ApplyBayCommand` are the last `BoolStringPair` returns in the planner.
They call `DiscreteGarageState::OnEvent`, which central, bay and vecs also use. Give
`DiscreteGarageState` a `stdx::Result` method next to `OnEvent`, so the planner can use it without
migrating every caller at once.

#### Scope

- `common_ros`: add `stdx::Result ApplyEvent(...)` to `DiscreteGarageState` for each `OnEvent`
  overload, with the same failure texts. `OnEvent` becomes a thin wrapper around it. `SucceededEvent`
  is never called with a message, so no caller loses a success text.
- `planner_core`: `ApplyTo` and `ApplyBayCommand` return `stdx::Result` and call `ApplyEvent`;
  `ScheduleEventDag::ApplyEventsTo` drops its conversion.
- Callers in `scheduler` and `motion_planner` follow.

#### Definition of Done

- No `BoolStringPair` left in `planner_core`'s headers.
- The failure texts are unchanged. The scheduler's recorded scenarios are identical
  (`SCHEDULER_CHECK_RECORDINGS=1`).
- `common_ros`, `planner_core`, `scheduler`, `motion_planner` and `central` tests pass.

#### Out of scope

- Migrating central, bay and vecs off `OnEvent`, and deprecating it: a later ticket.
- Removing `common/types.hpp` from planner_core, which also needs a home for `EnumNameString` in stdx.

---

## 2. Report why motion planning failed

https://volleyautomation.atlassian.net/browse/SW2-1171

### Description

#### Objective

When motion planning fails, `Plan()` reports "CHUGG failed to find a solution, event dag may be
infeasible" for every job. The real reason (a colliding solution, an AGV move with no trajectory, a
tray move that could not be planned) is only logged inside `motion_planner`. Carry it to the plan
response, so operators and tests see why.

#### Scope

- `motion_planner`: `Chugg::SolveSequential` returns `stdx::Expected<ContinuousState>`. The
  per-node and per-event planning (`PlanNodeSequential`, `PlanEventSequential`) return `stdx::Result`
  with the texts they log today.
- `scheduler`: `PlanMotions` returns `stdx::Expected<ContinuousState>`, and `Plan()` reports the
  reason in place of the generic text.
- The four `SolveSequential` calls in `chugg_tests.cpp` follow.

#### Definition of Done

- A failed plan's message names the event or collision that failed.
- The changed failure messages in the recorded scenarios are reviewed as a diff, not re-recorded
  blindly. Successful plans are unchanged.
- `motion_planner`, `scheduler` and `scheduler_advanced_tests` tests pass.

#### Out of scope

- Restructuring CHUGG or its search.
- `SolveCbs`, which nothing calls.
- Moving `PlanMotions` into its own module (phase C0 of SW2-482).

---

## 3. Move the scheduler's node, component and parameters to rclcppx

https://volleyautomation.atlassian.net/browse/SW2-1172

### Description

#### Objective

The scheduler logs and creates its services through `rclcppx`, but its node, component and
parameter reads still come from `common_ros` (`common_ros/node.hpp`, `common_ros/component.hpp`,
`node->Param<T>`). Move them to `rclcppx` (`node.hpp`, `component.hpp`, `parameter.hpp`), so the
package uses one ROS layer.

#### Scope

- `scheduler_component.cpp`: the component and the 20 motion-cost parameter reads.
- `scheduler_ros.hpp` and `scheduler_ros.cpp`: the node handle and the `printdags` parameter.
- Any other `common_ros` ROS wrapper the scheduler uses.

#### Definition of Done

- The scheduler includes no `common_ros` node, component or parameter header.
- Parameter names, defaults and the handling of a missing parameter are unchanged.
- Checked in simulation: the node starts, reads its parameters, and answers the `plan` and
  `set_bay_readiness_ratio` services. CI's simulated system tests pass.

#### Out of scope

- Domain types that live in `common_ros` (`DiscreteGarageState`, `GarageGraph`, `Layout`).
- Other packages' use of the `common_ros` wrappers.
