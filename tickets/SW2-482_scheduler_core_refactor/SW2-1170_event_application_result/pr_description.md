# PR text (as posted to VolleyAutomation/volley#1056)

Title: `[SW2-1170] Return stdx::Result from event application and remove DiscreteGarageState::OnEvent`

---

# What

Six commits that move event application onto `stdx::Result` and remove `DiscreteGarageState::OnEvent`. Failure texts are unchanged and every recorded scenario is identical; the behaviour changes are listed below. Each commit message has the details.

1. **Event application returns `stdx::Result`.** `DiscreteGarageState` gains `ApplyEvent` for every event type; `ScheduleEvent::ApplyTo` and `ApplyBayCommand` return `stdx::Result` and call it. No `BoolStringPair` is left in planner_core's headers.
2. **planner_core names spelled out.** `ScheduleEventDag` → `EventDag`, `TrayMove::GetDest`/`SetDest` → `GetDestination`/`SetDestination`, `AgvMove::GetSrc`/`GetDest` → `GetSource`/`GetDestination`. The old names are removed rather than deprecated, since every caller is in this repository.
3. **`DiscreteGarageState::OnEvent` removed; `Set` returns `stdx::Result`.** About 500 call sites in common_ros, central, motion_planner, scheduler, scheduler_advanced_tests and agvhito_tools use `ApplyEvent`. `Set(DiscreteGarageStateMsg)` and `Set(YAML::Node)` are `[[nodiscard]]`; `Set(DiscreteGarageState)` still replays every event and carries on past a failure.
4. **`DiscreteGarageState` event application tidied.** Failure messages use `std::format`; the event dispatch is a table from event type to handler; the `memset` of each new entity is removed (the message constructors zero every field, each handler assigns them all, and `Hash` combines fields one at a time); comments that restated the code are removed.
5. **Test-only `.clang-tidy`** for common_ros and planner_core, turning off `bugprone-unchecked-optional-access` as `src/agvhito/test/.clang-tidy` does.
6. **`std::format` for the failure messages on the lines this PR changes** in central, planner_core, scheduler and motion_planner.

### Behaviour changes

- Tests that ignored the result of `Set` now assert it. This exposed invalid YAML in `TinyLotContinuousStateTest.TestTrayCollision`, which had always run on an empty state; its data now matches the test's description.
- `Dispatch::DiscreteGarageStateCallback` logs why `Set` failed before its existing hash check.

# Why

`ApplyTo` and `ApplyBayCommand` were the last `BoolStringPair` returns in the planner, and they went through `DiscreteGarageState::OnEvent`, which central and the planner share. Moving that class to `stdx::Result` removes `BoolStringPair` from it and from planner_core's API.

# Testing

- [x] common_ros, planner_core, scheduler, motion_planner, central, agvhito_tools, scheduler_advanced_tests, bay, vecs, lift, cost_functions and agvhito build with 0 warnings; `prek` and the pre-push `clang-tidy` pass
- [x] common_ros 233 tests, planner_core 24, scheduler 206, motion_planner 82, central 215, agvhito_tools 15, scheduler_advanced_tests 15
- [x] `SCHEDULER_CHECK_RECORDINGS=1`: every recording identical
- [x] Garage test at 5675 Pecos with `8d106cc`: one insert and one retrieve, no issues observed
- [x] CI passes, including the sim and vis builds

Refs: SW2-1170
