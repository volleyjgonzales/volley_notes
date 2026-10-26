# Jira work item SW2-1126 for the parity baseline (child of epic SW2-482 Scheduler Core Refactor)

## Title

Record the scheduler planning tests as scenario files

## How to create and fill the work item

1. Open the epic SW2-482 and, under *Child work items*, click **+** (or **Create** at the top and
   set *Parent* to SW2-482). Work type: **Task** (it is test infrastructure, not a user story).
2. *Summary*: the title above.
3. *Description*: paste the Markdown under "Description" below. The Jira Cloud editor converts
   pasted Markdown (headings, bullets, code spans); check that the three headings came through as
   headings. For the Definition of Done, turn the bullets into a checklist with the editor's
   action-item button (`[]` typed at the start of a line also makes one).
4. *Assignee*: Jon M Gonzales. *Reporter*: as created. *Priority*: Medium. *Labels*:
   Scheduler_and_Dispatcher (the epic's label).
5. *Start date*: the day the branch was opened. *Due date*: the review target. Story points as
   the team sizes it; the epic has none.
6. *Development*: the branch is `jmg/SW2-1126/scheduler-scenario-files`, named with the key so
   the GitHub integration links it once pushed; the PR title is
   `[SW2-1126] Record the scheduler planning tests as scenario files`.
7. Optionally add a *Linked work item* "is blocked by / blocks": this work item blocks SW2-484
   (the interface needs the baseline to be verified against) and SW2-487 (the benchmark set grows
   from these scenarios).

## Description (paste into the Description field)

## Objective

Give the Scheduler Core Refactor (SW2-482) a baseline it can be checked against. Every planning test
of the scheduler records the complete result it produces today in a scenario file, so that the
`TrayMoveSolver` and `AgvAssignmentSolver` work that follows can be verified to give the same
results as `Scheduler::DoTrayAssignments` and `Scheduler::DoAgvAssignments`, and so that any later
behaviour change is deliberate and visible in a review diff. The scenarios are also the seed of the
benchmark suites the epic asks for: they run on the current customer site layouts.

## Scope

- Scenario files under `src/planner/scheduler/test/scenarios/`: an authored part (the test, a
  description, the initial state, the scheduler parameters, the request) and a recorded part (the
  scheduler's response in a canonical, compacted form: GUIDs by position, jobs sorted, acronym
  field names spelled out, default-valued fields left out). A test compares its response with the
  recorded part and fails on any difference; recording is explicit (`RECORD_REFERENCE_OUTPUT`) and
  rewrites only the recorded part.
- Initial states as files, `test/scenarios/initial_states/<layout>/<name>.yaml`, replacing the YAML
  literals embedded in the test sources.
- The three planning test files split into one file per stage or job type (`test/stages/`,
  `test/jobs/`) and the utils tests into `test/utils/`, one gtest suite and one binary each, built
  from one CMake list, with the loaders compiled once into a static library. The test code follows
  the conventions of `src/agvhito/src/sm`.
- Scenarios moved from the decommissioned 576_eccles and 1355_fulton layouts and the synthetic lots
  to the sites 275_sunrise_b, 5675_pecos_combined and 38_gramercy (EV-charger scenarios, through
  its car lift); two blocking-tray fallback scenarios stay on the synthetic tiny_lot.
- Four new tests: an insert-readiness job, a base schedule that reserves an AGV, and the two
  tray-assignment fallbacks (advance the root tray, park the blocker on the critical path).
- `tools/view_scheduler_tests.py` (package `tools/plan_viewer/`, dev dependency group
  `scheduler`: plotly, rich): one HTML page with every scenario drawn to scale, the request and the
  schedule as tables, the planned paths and the action graph.

## Definition of Done

- Every planning test (58 scenarios: 45 through `Scheduler::Plan`, 4 tray-assignment and 9
  AGV-assignment stage scenarios) compares with a recorded scenario file and passes on the current
  scheduler.
- No YAML literal remains in the test sources; every initial state is a file shared by the
  scenarios that start from it.
- Recording is deterministic: a plan scenario is planned twice in one process and both runs must
  agree before the comparison.
- The scenarios run on current site layouts only, except the two fallback scenarios documented as
  needing a closed synthetic lot.
- `test/scenarios/README.md` documents the file formats, the vocabulary, the layouts to use, and
  how to build, run, record and view.
- The viewer renders every scenario and is the review aid for the refactor's diffs.
- `poe test-pkg scheduler`, `planner_core` and `scheduler_advanced_tests` pass; hooks pass.

## Out of scope

- Any change to the scheduler library: the recorded files capture today's behaviour, bugs
  included, and a fix is a later commit that re-records on purpose.
- The solver interfaces and their default implementations (SW2-484 and its sibling for AGV
  assignment).
- Benchmark timing; the scenarios record results, not durations.

## Observations recorded for follow-up (not fixed here)

- The retrieval-heading rule (`InitRetrievalHeadings`) caches no heading for the stalls of
  5675_pecos_combined ("No retrieval heading for dest node ...") and cannot apply on 275_sunrise_b
  by construction; no test exercises it any more.
- On 5675_pecos_combined an inserted car is lowered on the waypoint in front of the bay (W31 /
  W41) rather than in the free stall.
- Closing a site layout down to a small region with `disabled_nodes` makes the planner cycle for
  minutes in the blocking-tray fallbacks.
- `AgvChargeJob.TwoAgvsDistinctChargers` had given both jobs the same GUID; with distinct GUIDs
  both AGVs now charge.
- `ReparkTrayJob.UnplugsChargerAgvMovesFirst` plans the same request as
  `ReparkTrayJob.UnplugsCharger`.

## Review

Start with `test/scenarios/README.md`, then one scenario file next to its test (for example
`test/scenarios/plan/retrieve_job/FromStall.yaml` and `test/jobs/retrieve_job_tests.cpp`), then the
viewer page (`uv run python src/planner/scheduler/tools/view_scheduler_tests.py`). Two commits on
top of main: the tests and scenario files, then the viewer.
