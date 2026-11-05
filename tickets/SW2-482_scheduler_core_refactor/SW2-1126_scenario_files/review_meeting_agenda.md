# PR #1007 walkthrough: a 30-minute script for the review session

For the reviewers of `[SW2-1126] Record the scheduler planning tests as scenario files`, who have
little or no prior contact with the scheduler. Each block gives the points to make and the full
answer to each, so the session can be read from this page; the times add up to 30 minutes and the
last block is a buffer. After the session each reviewer should know what the PR is for, how a
scenario file and its test fit together, what to read closely and what to read through the viewer,
and where the decisions worth questioning are.

## Before the meeting

- Share the PR link, the Jira ticket SW2-1126 (child of epic SW2-482) and the path
  `src/planner/scheduler/test/scenarios/README.md`.
- Have open: the PR's "Files changed" filtered to `src/planner/scheduler/test/jobs/` and
  `test/scenarios.cpp`; the viewer page built from the branch
  (`uv run python src/planner/scheduler/tools/view_scheduler_tests`, then
  `artifacts/scheduler-tests.html`); the file pair
  `test/scenarios/plan/retrieve_job/FromStall.yaml` and `test/jobs/retrieve_job_tests.cpp`.
- The numbers: 58 scenarios (45 through `Scheduler::Plan`, 4 tray-assignment and 9
  AGV-assignment stage scenarios), 60 initial-state files, 18 test binaries, 170 tests, 172 files
  changed, about 14,500 added lines of which 5,800 are recorded output; `poe test-pkg scheduler`
  in 1 m 36 s locally.

## 1. Why this PR exists (3 min)

**The epic.** The Scheduler Core Refactor (SW2-482) moves the two hardest parts of planning,
tray-move planning and AGV assignment, behind two interfaces, `TrayMoveSolver` and
`AgvAssignmentSolver`, each with a default implementation that must give the same results as
today's `Scheduler::DoTrayAssignments` and `Scheduler::DoAgvAssignments`. Once they exist, new
solvers can be swapped in and compared against today's behaviour on benchmark suites drawn from
real sites.

**The gap this PR closes.** Today's tests assert a few properties of a plan: the last command ends
at the bay, there was a lift and a lower, the job comes back as executing. A refactor can change
the plan in ways none of those assertions notice: a different stall for a blocker, a different
AGV, a different order of commands, a different duration. "Same results as before" is not
checkable against a handful of properties. It is checkable against the complete result, so this
PR records the complete result of every planning test in a file and makes every test compare its
result with that file. Any later change in behaviour is then a deliberate re-recording that shows
up as a diff of the scenario file in a review.

**What it is not.** It changes nothing in the scheduler library. The recordings capture what the
scheduler does today, bugs included, and a few things they revealed are listed for follow-up
rather than fixed. The tests also move from decommissioned layouts to current customer sites,
which the epic asks for because the benchmarks will run on those sites.

## 2. The scheduler in two minutes, for those who have not read it (3 min)

**One call.** `Scheduler::Plan(PlanRequest) -> PlanResponse`. The request carries the discrete
garage state (AGVs, trays, bays, cars on trays, chargers, lifts, disabled nodes) and the pending
jobs: retrieve a car, insert a car, repark a tray, charge a car, charge an AGV, make a bay ready,
clean the garage. The response is a schedule: a DAG of action nodes, each an AGV command (drive
from pose to pose, raise or lower the lift), a bay command, a charger command or a lift command,
with a duration and the indices of the nodes it depends on, plus the jobs with their new state.

**Four stages inside.** Job expansion turns each job into events on an event DAG: tray moves,
bay transitions, charger transitions. Tray assignment (`DoTrayAssignments`) decides where each
tray goes when the job left it open, finds the critical path of each move, and when another tray
stands on that path adds a move for the blocker first, chained before the root move; when the
blocker has nowhere to go it falls back to advancing the root tray or parking the blocker on the
path. AGV assignment (`DoAgvAssignments`) picks an AGV for each tray move by cost and inserts the
lift and lower events around it. Motion planning turns the DAG into trajectories with times and
builds the response. The refactor targets the two middle stages; the PR records the output of
all four through `Plan`, and of the two middle ones directly in the stage tests.

**The vocabulary in the files.** Nodes are named by type and id: P2067 is a parking stall, W2070
a waypoint, B2068 a bay, C10 an AGV charger, E23 an EV charger; a pose is a node and a heading in
degrees, `2068@0`. AGVs and trays have small integer ids; cars are payloads with GUIDs. The
response's acronym fields (`vexen`, `vecs_command`, `vrcs`) are spelled out in the files as
`ev_chargers`, `ev_charger_command`, `vertical_conveyors`.

## 3. A scenario file next to its test (7 min)

Walk `FromStall.yaml` and `TEST(RetrieveJob, FromStall)` side by side.

**The authored part, written by hand.** `test: RetrieveJob.FromStall` names the gtest that runs
the file; the loader refuses a file whose `test` key is not the running test, which catches a file
saved under the wrong name. `description` has three sentences in a fixed shape, scenario, test,
expected, and the viewer shows them. `initial_state: 275_sunrise_b/car_at_p2066_bay_ready_to_retrieve`
names a file under `initial_states/<layout>/`: the folder is the layout, found under
`src/config/site_config/layouts/`, and the file lists what stands in the garage, with defaults
left out. One state file is shared by every scenario that starts from it; there are 60 of them.
`scheduler` holds the parameters the file sets (today only `bay_readiness_ratio`); `request` holds
the jobs in the message's vocabulary. A key outside the known set is refused, because a mistyped
key would otherwise read as the field's default and produce a plausible-looking recording.

**The recorded part, written by the test.** `output.response` is the scheduler's response in a
canonical, compacted form. Three normalisations, and why each:

1. *Action-node GUIDs become positions.* The scheduler draws node GUIDs from a process-wide
   counter, so they differ with the tests that ran before in the same binary. Each node's GUID is
   replaced by its position in the schedule, and the replacement is followed everywhere the GUID
   was copied: the command ids of charger and lift commands and each job's `bay_arrival_node_guid`.
   The request id is 1000 and job GUIDs start at 1001, so no recorded id can be read as a node
   position.
2. *Scheduled jobs are sorted by GUID.* The scheduler returns them in a container order that is
   not part of the contract; sorting makes the file stable.
3. *Default-valued fields are left out.* `to_yaml` prints every field of the message: four command
   sub-messages per action node of which one is in use, zero headers and timestamps, two-line
   GUIDs; about 45 lines per node of which 15 carry information. The compacted form drops every
   field that holds its default (zero, empty, false, an all-default sub-message), writes a GUID
   as one scalar and a pose on one line. The one rule a reader needs: an absent field holds its
   default. It took the recorded part from 22,000 lines to 5,800, and the comparison is as complete
   as before because both sides go through the same function.

**The test.** `const auto run = scenarios::Plan();` followed by a few assertions on
`run.response`. `Plan` takes no path because the file is found from the test's own identity:
gtest knows the running suite and test, the suite becomes the folder in snake case
(`RetrieveJob` to `retrieve_job`), the test name becomes the file name, so `RetrieveJob.FromStall`
reads `plan/retrieve_job/FromStall.yaml`; a test that plans several scenarios names them with a
suffix. What `Plan` does, in order: load the file and the initial state, build the request
message, construct or fetch the scheduler for that layout, plan, plan a second time and require
both canonical responses to be identical (only a deterministic scheduler can be recorded, and a
non-deterministic one would otherwise produce a file that fails on the next run), then compare
the canonical response with the file's `output` line by line, or, when `RECORD_REFERENCE_OUTPUT`
is set, rewrite the file's recorded part under its untouched authored part. Recording never creates
a file and refuses a file that names another test.

**What a failure looks like.** gtest reports `recorded output of FromStall.yaml and the result
differ at line 42` with the expected and the actual line, so the next step is to open the file at
that line; a determinism failure reads `two planning runs of the same scenario differ at line ...`.
A deliberate behaviour change is re-recorded on purpose by running the binary with the variable
set, and the review of that change is the diff of the scenario file, read on the viewer.

**The stage tests.** `test/stages/tray_assignment_tests.cpp` and `agv_assignment_tests.cpp` do
the same one level down: they build a `ScheduleContext` by hand with the events a job expansion
would have produced, call `DoTrayAssignments` or `DoAgvAssignments` directly, and record the
event DAG before and after the stage: every event by its string form, the edges as positions,
and the first event of each tray. These 13 files are what the solvers' default implementations
will be checked against; the 45 plan files check the whole pipeline.

## 4. How the test folder is put together (4 min)

**The tree.** `test/scenarios.{hpp,cpp}` loads a scenario, builds the request, plans, records or
compares; `test/initial_states.{hpp,cpp}` loads a state file into a `DiscreteGarageState`;
`test/agv_commands.hpp` has two helpers that read a command's lift flags. The tests sit in
`test/stages/` (five files: tray assignment, AGV assignment, assignment costs, sanity checks,
scheduler state), `test/jobs/` (ten files, one per job type, charger variants apart) and
`test/utils/` (three files for the helpers in `utils.hpp`). The data sits in `test/scenarios/`:
`initial_states/<layout>/`, `plan/<suite>/`, `task_planning/<stage>/`, and the README that
documents the formats, the vocabulary, the layouts to use, and how to build, run, record and view.

**Why the split.** Three files of 1,500 lines became eighteen of a few hundred, one gtest suite
and one binary each, in the style of the agvhito state-machine tests: a failure names the file,
a binary can be run alone, and the CMake block is one list and one loop. The two loader sources
are compiled once into a static library that every binary links; before that they were compiled
eighteen times, which made the pre-push clang-tidy hook analyse them eighteen times each, twenty
minutes instead of one.

**Two things added for CI.** Constructing a `Scheduler` parses the layout's cached collision
table; for 275_sunrise_b that is 281 MB of JSON and five seconds locally, thirteen on the CI
runner. Every planning entry point the tests call is `const`, so the support keeps one scheduler
per layout and parameter set per binary and hands it to each test; the package went from
3 m 26 s to 1 m 36 s locally. And the planner narrates every plan at INFO (the critical path, the
blocking trays, every planned motion, the garage state), nine thousand lines for the package; the
binaries set those loggers to WARN before the first test, and `SCHEDULER_TEST_LOG=1` brings the
narration back when a failure needs it.

**The layouts.** 275_sunrise_b carries most scenarios; 5675_pecos_combined the bays, the AGV
chargers and the sanity checks; 38_gramercy the EV-charger scenarios, and since its bay is the
car lift BL26 the retrieves there go through the lift and carry lift commands. The decommissioned
576_eccles and 1355_fulton and the synthetic lots are gone, except tiny_lot for the two
blocking-tray fallbacks: on a site the blocker always has a waypoint to drive off to, and closing
a site down with `disabled_nodes` either leaves the tray no path or makes the planner cycle for
minutes.

## 5. The viewer (5 min, demo)

**What it is.** One HTML page built from the scenario files by `tools/view_scheduler_tests`,
a Python package under `tools/plan_viewer/` using plotly and rich from a dev dependency group;
nothing of it ships in the runtime images. It is the second commit of the PR.

**The demo.** The tree on the left lists the scenarios by stage and job type, and a layouts
section lists the sites with their file. Open a plan scenario: the garage drawn to scale with the
initial state (stalls, bays with their door, waypoints, chargers, trays, cars, AGVs), the
description and provenance, the request and the schedule as tables, and the paths: one per AGV in
its own shade of green, straight legs with curved corners, a lane per pass when paths share a
segment, an arrowhead per leg, badges for lifts, lowers and rotations. Hover a step in the drawing
or in a table row and it lights up everywhere, with a ghost of the agent where the step leaves it.
Toggle the solution off to see the problem alone. Open
`TrayAssignment.ResolvesManyBlockersThenAssignsAgvs`: the DAG before and after the stage, the two
blocker moves chained before the root move, then the AGV stage splitting them across two AGVs.

**The point for review.** The recorded parts are 5,800 lines of YAML across 45 files. Nobody
should read them in the diff; this page is how they are read, and how a future re-recording is
reviewed: the drawing of the new plan next to the description of the old one.

## 6. What the recordings showed, and what is deliberately not fixed (3 min)

The library is unchanged; these are in the PR description and the ticket as observations.

- `AgvChargeJob.TwoAgvsDistinctChargers`: the old test gave both jobs the same GUID, so the
  scheduler saw one job and one AGV charged; with distinct GUIDs both AGVs charge, and the
  recording shows the two.
- The retrieval-heading rule (`InitRetrievalHeadings`) caches no heading for the stalls of
  5675_pecos_combined and cannot apply on 275_sunrise_b, so no test exercises it any more; the
  assertions on the lowered heading accept the heading or its reciprocal.
- On 5675_pecos_combined an inserted car is lowered on the waypoint in front of the bay rather
  than in the free stall; recorded as it is.
- `ReparkTrayJob.UnplugsChargerAgvMovesFirst` plans the same request as `UnplugsCharger`; kept,
  because deleting a test is a coverage decision for the owners.
- Closing a site down to a region with `disabled_nodes` makes the planner cycle for minutes in
  the blocking-tray fallbacks, which is why those two scenarios keep tiny_lot.
- The collision table of 275_sunrise_b is 281 MB of JSON, 17 million pose objects with spelled-out
  keys, parsed in seconds on every construction, and its build logs one line per vertex and
  edge. Both are common_ros matters for a ticket; the test support works around the first.

## 7. How to review it (4 min)

**Reading order.** `test/scenarios/README.md` first; then one scenario next to its test
(`FromStall`); then `test/scenarios.cpp`, where the canonical form and the comparison live, the
heart of the PR; then the four new tests: `InsertJob` readiness, `MoveJob.BaseScheduleReservesAgvAndNodes`,
and the two tray-assignment fallbacks `RetrieveJob.AdvancesRootTray` and
`RetrieveJob.ParksBlockerOnCriticalPath`; then the CMake block. The other test files are the old
tests moved and split, with the YAML literals replaced by file names and `ASSERT`s added where an
index or an optional followed an `EXPECT`; skim them.

**Read through the viewer, not the diff.** The 45 recorded parts and the 60 initial-state files.

**Where a second opinion is wanted.**
- The compacted recorded form: absent means default. The alternative was the full message at
  four times the size.
- Float durations are recorded at six significant digits, `to_yaml`'s default; a drift below
  that would pass. Easy to tighten if the parity check needs it.
- Stage files are keyed by test name without the suite, so a tray test and an AGV test of the
  same name would share a file; the loader makes that a loud failure rather than a silent one.
- The shared scheduler across tests of a binary: safe because the entry points are `const` and
  the one test that mutates a scheduler owns its own.
- The test folder's `.clang-tidy` disables `bugprone-unchecked-optional-access`, as the agvhito
  tests do, because the check cannot see gtest's assertions.

**CI notes to expect.** The first run built the three sites' collision tables, minutes each, once;
they are in the cache now. Octocov reports coverage down 1.3%: the per-line comparison of the
unit-test reports shows the scheduler files level or up (`scheduler.cpp` 2,019 to 2,026 covered
lines); the delta is the collision-table builder, which push runs on main cover in every job
because they skip the table cache, while PR runs download it.

**Commits and Greptile.** Two commits: the tests and scenario files, then the viewer. Greptile
has reviewed; its remaining findings, if any, get a one-line reply each.

## 8. Buffer and questions (1 min, or whatever is left)

Likely questions, with the answers:

- *Why YAML files rather than comparing data structures?* The reference has to live on disk,
  survive rebuilds and be readable in a review, so it is serialised either way; the only choice is
  where the comparison runs. The emitted text is a deterministic function of the message, the
  exactness lives in the canonicalisation that a structure comparison would need just the same, a
  text diff names the field and the line where the generated equality operator returns a bool, and
  the event DAG has no equality operator at all. The one place the text is coarser than the
  structure is the six-digit floats.
- *Why so many files?* One initial state per situation, shared by the scenarios that start from
  it; one scenario per test, named after it; the recorded part is the product the PR exists for.
  Of the 14,500 added lines, 5,800 are recordings, 2,100 authored data, 3,200 test C++ against
  6,500 removed, 3,000 viewer.
- *Why real sites rather than a small test lot?* The epic asks for benchmarks on real sites, and
  a parity check on the layouts the solvers will run on is worth more than on a toy lot. The cost
  is the collision table of 275_sunrise_b, handled by the shared scheduler.
- *Why is the stage DAG built by hand instead of going through `Plan`?* The stage tests isolate
  one stage on an input the test controls; the 45 plan scenarios drive the production wiring end
  to end. Once the solver interface exists, a stage can be recorded inside `Plan` for every
  scenario without hand-built contexts.
- *Can a reviewer run it?* `poe build-pkg scheduler` and `poe test-pkg scheduler`; one binary
  alone from `build/scheduler/`; to re-record a binary, run it with `RECORD_REFERENCE_OUTPUT=1`;
  the viewer with the `uv run` line at the top.
- *What comes next?* SW2-484: the `TrayMoveSolver` interface with a default implementation
  verified against these recordings; then the AGV-assignment counterpart; the benchmark suites
  grow from these scenarios. A common_ros ticket for the collision-table format and logging.
