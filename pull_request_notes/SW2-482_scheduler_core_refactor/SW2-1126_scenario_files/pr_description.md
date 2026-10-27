# PR text (paste into GitHub)

The repo's PRs are titled `[SW2-xxxx] Description` and their bodies use `# What`, `# Why` and
`# Testing` (17 of the last 40 merged PRs; #973, #968, #980), with a `Refs:` line at the end;
the other common form is `## Summary` with `### Changes` and `## Fix` (#1003, #993). This follows the first. GitHub renders a newline inside a PR body as a line break, so
the body below keeps one line per paragraph and per bullet: paste it as is.

Title: `[SW2-1126] Record the scheduler planning tests as scenario files`

---

# What

Every planning test of the scheduler now runs from a scenario file under `src/planner/scheduler/test/scenarios/`. The authored part of a file names the test, the initial state and the request; the recorded part holds the scheduler's response in a canonical, compacted form (action-node GUIDs by position, jobs sorted by GUID, acronym field names spelled out, default-valued fields left out). A test compares its response with the recorded part and fails on any difference; recording is explicit (`RECORD_REFERENCE_OUTPUT=1`) and rewrites only the recorded part. These files are gtest inputs and recordings, not simulation scenarios: those live under `src/scenario/scenarios/` and none of the exerciser's workload conventions apply here.

Two commits: the tests and scenario files, then the viewer.

### Tests and scenario files

- Initial states as files, `test/scenarios/initial_states/<layout>/<name>.yaml`, replacing the YAML literals embedded in the test sources; one file per state, shared by the scenarios that start from it.
- The three test files split into one file per stage, job type or utility (`test/stages/`, `test/jobs/`, `test/utils/`), one gtest suite and one binary each, built from one CMake list; the scenario and initial-state loaders are compiled once into a static library every binary links. Test code follows the conventions of `src/agvhito/src/sm`.
- 58 scenarios: 45 through `Scheduler::Plan`, 4 tray-assignment and 9 AGV-assignment stage scenarios. They run on 275_sunrise_b (most), 5675_pecos_combined (bays, AGV chargers, sanity checks) and 38_gramercy (EV chargers; its bay is the car lift BL26, so retrieves go through the lift) instead of the decommissioned 576_eccles and 1355_fulton sites and three synthetic lots. Two blocking-tray fallback scenarios keep the synthetic tiny_lot: a closed-off region of a site either leaves the tray no path or makes the planner cycle for minutes.
- Four new tests: an insert-readiness job, a base schedule that reserves an AGV, and the two tray-assignment fallbacks (advance the root tray; park the blocker on the critical path).
- A plan scenario is planned twice in one process and both runs must agree before the comparison.
- `src/planner/scheduler/test/.clang-tidy` disables `bugprone-unchecked-optional-access` for the test folder, as `src/agvhito/test/.clang-tidy` does: the check cannot see gtest's assertions.
- `test/scenarios/README.md` documents the file formats, the vocabulary, the layouts to use, and how to build, run, record and view.

### Viewer

`tools/view_scheduler_tests` (package `tools/plan_viewer/`, dev dependency group `scheduler-dev`: plotly, rich) renders every scenario as one HTML page: the garage to scale with the initial state, the request and the schedule as tables, the planned paths and the action graph. It is the review aid for the recorded files: a change in a recording is read on the drawing rather than in the YAML diff. Nothing of it ships in the runtime images.

### Behaviour and expectation changes

No change to the scheduler library. The recorded files capture its behaviour as it is, bugs included; what the recordings showed is listed in the ticket for follow-up.

- `AgvChargeJob.TwoAgvsDistinctChargers` now plans two jobs: the old test gave both jobs the same GUID, so the scheduler saw one job and one AGV charged.
- On the sites the retrieval-heading rule (`InitRetrievalHeadings`) caches no heading for the stalls of 5675_pecos_combined and cannot apply on 275_sunrise_b, so no test exercises it any more; the assertions on the lowered heading accept the heading or its reciprocal.
- Requests are numbered: request id 1000, job GUIDs from 1001, action nodes by position from 1.
- `ament_index_cpp` is dropped from the package's test dependencies; nothing used it.
- Test names are shortened where they ran long.

# Why

The Scheduler Core Refactor (SW2-482) moves tray-move planning and AGV assignment behind the `TrayMoveSolver` and `AgvAssignmentSolver` interfaces. That work needs a baseline it can be checked against: with the complete result of every planning test recorded, a solver's default implementation can be verified to give the same results as `Scheduler::DoTrayAssignments` and `Scheduler::DoAgvAssignments`, and any later change in behaviour is a deliberate re-recording that shows in the review diff. The scenarios are also the seed of the benchmark suites the epic asks for: they run on the current customer site layouts.

# Testing

- [x] `poe build-pkg scheduler`
- [x] `poe test-pkg scheduler` (170 tests), `planner_core` and `scheduler_advanced_tests` pass
- [x] `prek` hooks and the pre-push `clang-tidy` pass (0 findings)
- [x] Every scenario re-recorded and compared on the current scheduler; no recording changed on the final rebase
- [x] The viewer renders all 58 scenarios

Coverage note: octocov reports -1.3% against main, with `collision_geometry.cpp` and the scheduler files among the affected ones. The unit-test coverage report shows `scheduler.cpp` up (2,019 to 2,026 covered lines) and the other scheduler files level. The delta is the collision-table builder: push runs on main skip the collision-table cache, so all 27 jobs build the tables and cover the builder, while PR runs download the cache and only the three jobs that build small tables cover it. The comparison is between two CI configurations, not between the tests.

Refs: SW2-1126
