# PR text (paste into GitHub)

Same form as PR #1007 (`# What`, `# Why`, `# Testing`, a `Refs:` line; GitHub renders a newline as a
line break, so one line per paragraph and per bullet). Condensed on 2026-11-02 for the six commits at
`a3370c4b`; the details live in the commit messages. The testing lines carry the counts of that tip.

Title: `[SW2-1135] Rename, clean up and split the scheduler before the tray solver`

---

# What

Six commits that rename, clean up and split the scheduler before the tray solver (SW2-484). Every recorded scenario is unchanged; behaviour changes are limited to the bug fixes of commit 4 and the Eccles removal of commit 6. Each commit message has the details.

1. **Renames, logging, comments, dead code.** `Plan<Type>Job` → `Expand<Type>Job`, `ScheduleContext` → `PlanContext`, verb-first methods (`AssignTrays`, `AssignAgvs`, `BuildActionGraph`), `is_` bools, and names that no longer need a comment to explain them. Inside the scheduler the bay readiness ratio is `target_insert_ready_bay_fraction`; the ROS parameter, service and report field keep their names. Narration logging and stale comments go (every ERROR stays); `BoolStringPair` becomes `stdx::Expected` / `stdx::Result`.
2. **`planner_core` / `motion_planner` APIs and message headers.** The event DAG API is renamed and trimmed (`Dag`, `GetNode`, `GetEvent`, `RemoveRedundantEdges`, `ApplyEventsTo`, `ApplyTo`); motion_planner's filter and search functions are named for what they do; `scheduler_msgs.hpp` gives way to fully qualified types and per-file includes.
3. **Extractions.** Repeated event-building sequences and the state replay become helpers; long functions hand named blocks to methods; error texts use `std::format`, unchanged.
4. **Bug fixes**, below.
5. **`scheduler.cpp` split** into one file per pipeline stage, no function body changed; scheduler-local heading helpers replace common's reciprocal functions.
6. **Eccles exception and dead paths removed** (with the four Eccles advanced tests); action-graph failures get specific errors; the repark heading is applied before validation.

### Behaviour changes (commit 4)

- A job that fails expanding is reported once and leaves no events behind.
- Repark reads the tray's planned pose, not its initial one; the response lists jobs in request order.
- An AGV already on its charger is recognised as there.
- Non-finite bay readiness ratios are rejected.
- Tray assignment: the advance move's path is right and applied once; a destination usable only reversed no longer throws; occupancy errors propagate.
- Failures that were ignored, thrown or counted as zero are reported: event applications, AGV move durations, state replay, a missing keep-out filter, and a cycle in the AGV pickup order (its throw would have crashed the node).
- Motion ordering breaks hash ties on every field, so colliding hashes no longer drop a motion.
- Error texts: 35 that named functions that no longer exist are reworded; four become whole sentences (the two `FromUnavailableCharger` recordings change in the message only); one missing space.

Five new tests cover the reachable ones; commit 4's message states each change's reachability.

# Why

The solver PRs of SW2-482 should show logic changes and nothing else, starting from code that already uses the catalogue's names and one file per stage.

# Testing

- [x] `scheduler`, `scheduler_advanced_tests`, `agvhito_tools`, `motion_planner` build with 0 warnings; `prek` and the pre-push `clang-tidy` pass
- [x] `scheduler` 194 tests (187 on main, eight new, one stub's removed), `planner_core` 22, `motion_planner` 82, `scheduler_advanced_tests` 12 (four Eccles scenarios removed)
- [x] `SCHEDULER_CHECK_RECORDINGS=1`: every recording identical except the renamed `scheduler:` key and the two `FromUnavailableCharger` messages; one new scenario (`MoveJob.TwoTrayMovesWithAgvUnderOneTray`, the tiny_lot test moved out of the deleted Eccles test file)

Refs: SW2-1135
