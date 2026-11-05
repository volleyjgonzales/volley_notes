# Codex review 15 (2026-11-01) and its evaluation

Codex read the tip `d9082d54`: the bay readiness ratio's name, and a clean-up of motion_planner's
`Chugg` (`chugg.hpp` 262 lines, `chugg_common.cpp` 525, `chugg_sequential.cpp` 690, `chugg_cbs.cpp`
128, `chugg_tests.cpp` 446). Checked here; nothing changed (item 244).
Applied in item 245: the commit-1 part (doc comment, `insert_ready_fraction`); tip `ce566d68`. Chugg waits
for the motion_planner clean-up PR.

## 1. bay_readiness_ratio

The meaning is right: the target fraction of usable bays made ready to insert, rounded up, clamped,
capped by empty trays; the rest made ready to retrieve (`CalculateDesiredBaySplit`).

The name is not the scheduler's alone. It is the ROS parameter `scheduler.bay_readiness_ratio`, the
service `/scheduler/set_bay_readiness_ratio`, the `SchedulerReport.bay_readiness_ratio` message field,
central_api's REST resource and report, the simulator's `SET_BAY_READINESS_RATIO` event, the system
tests' `set_bay_readiness_ratio`, launcher params, exerciser scenarios and the scheduler test scenarios'
`scheduler:` key. Renaming only the C++ field and member splits one setting across two names (the
member would be set from a parameter and reported in a field of the old name).

Verdict: keep the name in this PR; say what it means once, at `SchedulerParams::bay_readiness_ratio`
(commit 1), and name the internal parameter of `CalculateDesiredBaySplit` and
`ComputeBayRebalancingActions` (`desired_bay_readiness_ratio`) for what it is there. A system-wide rename
(interfaces, central_api, sim, system tests, params, scenarios) is a ticket of its own.

## 2-8. Chugg

| # | Finding | Check | Verdict |
|---|---|---|---|
| 2 | Name the class for its job: `EventTrajectoryPlanner`, files to match. | The class plans trajectories for the event DAG; the scheduler's only use is `scheduler.cpp:305` (`motion_planner.SolveSequential(...)`). | Agree in a motion_planner PR. Name to settle there (the scheduler says "motion": `PlanMotions`, `motion_planner`). |
| 3 | Header presents CBS as the execution model; commented-out methods, banners. | Confirmed (`chugg.hpp:16-19`). `SolveCbs` has no caller anywhere, tests included. | Agree; in that PR also decide whether `SolveCbs` and `chugg_cbs.cpp` go (dead in this repository). |
| 4 | `geometry_`, `init_traj_`, `EntityCurrentTime`, `GetStaticConstraintsCopy`, `GetUpdatedContinuousState`, `InitializeEventOrder`, `GetBaysMovingAfter`, `GetVexenMovingAfter`; `GetEventEntity` returns the AGV for a tray move. | Plausible, consistent with the code read. | That PR; align with the scheduler's names (`collision_table_`, `initial_state`). |
| 5 | `Node` mixes shared planning state and CBS search state; typed handlers copy shared pointers. | Confirmed in shape. | That PR (rename now, split later). |
| 6 | `SetEventSafeIntervals` returns the old table for manual restore; use `stdx::ScopeExit`; also for `AuditScope`. | Confirmed: restored by hand at `chugg_sequential.cpp:147` and `:283`; `stdx/scope_exit.hpp` exists. | That PR. |
| 7 | `PlanNodeSequential` dispatches AGV, tray, bay and VECS events but not VRC, though a VRC overload exists; an unhandled event plans as success. | Confirmed in code (`chugg_sequential.cpp:51-72`, overload at `:493`). Unreachable today: the scheduler creates no `VrcTransition` (VRC actions come from motions in the action graph). | Ticket; in that PR make an unhandled event fail, or dispatch VRC. |
| 8 | `GetVexenMovingAfter` replays every event into a state it never reads. | Confirmed (`chugg_common.cpp:511-519`; the `ApplyTo` result is ignored too; `GetBaysMovingAfter` has no replay). | That PR. |

Why not SW2-1135: about 2,000 lines of the planner every plan runs through, a class and four file
renames, unrelated to the tray-solver path; the PR is pushed and in review. The deferred items of review
14 (static_graph_filtering extraction, `BlockedGraphLocations`, `IgnoredObstacles`) belong in the same
motion_planner clean-up.

## Proposal

- SW2-1135, commit 1: a doc comment on `SchedulerParams::bay_readiness_ratio`; the bay-rebalancing
  parameter `desired_bay_readiness_ratio` becomes `insert_ready_fraction` (it is the fraction of bays to
  make ready to insert).
- A motion_planner clean-up PR (own ticket): Chugg items 2-6 and 8, review 14's deferred items.
- Tickets: the VRC dispatch gap; optionally the system-wide ratio rename.
