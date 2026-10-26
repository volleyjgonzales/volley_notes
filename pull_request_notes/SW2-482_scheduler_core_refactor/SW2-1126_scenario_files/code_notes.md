# Commit 1: scenario files for the planning tests

Status: two commits on jmg/SW2-1126/scheduler-scenario-files (Jira SW2-1126, child of epic
SW2-482), on top of main (6d656e15): 80535545
`test(scheduler): record the planning tests as scenario files` (152 files) and 3162844b
`feat(scheduler): add a viewer page for the test scenarios` (20 files: tools/, pyproject.toml,
uv.lock); amended after every review round (review log items 1 to 118 in `../SW2-482_notes.md`). This
document describes the commit as it stands; it is rewritten after every change to the code.

## Contents

- [What the commit does, in one paragraph](#what-the-commit-does-in-one-paragraph)
- [The files under src/planner/scheduler/test/](#the-files-under-srcplannerschedulertest)
  - [scenarios.hpp and scenarios.cpp](#scenarioshpp-and-scenarioscpp)
    - [How the comparison works](#how-the-comparison-works)
  - [initial_states.hpp and initial_states.cpp](#initial_stateshpp-and-initial_statescpp)
  - [stages/](#stages)
  - [jobs/](#jobs)
  - [utils/](#utils)
  - [Conventions](#conventions)
  - [scenarios/](#scenarios)
- [How a test run flows, from CMake to the comparison](#how-a-test-run-flows-from-cmake-to-the-comparison)
  - [From CMake to a running binary](#from-cmake-to-a-running-binary)
  - [Inside a binary, before the first test](#inside-a-binary-before-the-first-test)
  - [One plan test, RetrieveJob.FromStall in test/jobs/retrieve_job_tests.cpp](#one-plan-test-retrievejobfromstall-in-testjobsretrieve_job_testscpp)
  - [One stage test, TrayAssignment.MovesOneBlocker in test/stages/tray_assignment_tests.cpp](#one-stage-test-trayassignmentmovesoneblocker-in-teststagestray_assignment_testscpp)
  - [What a failure looks like](#what-a-failure-looks-like)
- [clang-tidy on this branch](#clang-tidy-on-this-branch)
  - [What runs, from which files](#what-runs-from-which-files)
  - [Where the output goes](#where-the-output-goes)
  - [Why this branch took so long, and what fixed it](#why-this-branch-took-so-long-and-what-fixed-it)
  - [How to think about it](#how-to-think-about-it)
- [The three kinds of YAML and how they fit](#the-three-kinds-of-yaml-and-how-they-fit)
- [What is tested against what](#what-is-tested-against-what)
- [Questions and answers](#questions-and-answers)
  - [Why is the commit so large, and is it mainly configuration?](#why-is-the-commit-so-large-and-is-it-mainly-configuration)
  - [Can the recorded part be made smaller?](#can-the-recorded-part-be-made-smaller)
  - [What do the scenario tests compare: the request and response only, or intermediate state too?](#what-do-the-scenario-tests-compare-the-request-and-response-only-or-intermediate-state-too)
  - [Why compare YAML text with YAML text instead of data structures?](#why-compare-yaml-text-with-yaml-text-instead-of-data-structures)
- [Review against the Greptile configuration](#review-against-the-greptile-configuration)
- [Open points for your review](#open-points-for-your-review)

## What the commit does, in one paragraph

Nothing in the scheduler's library changes. Every planning test now runs from a scenario file under
`src/planner/scheduler/test/scenarios/`: the authored part names the test, describes the scenario,
names the initial state and, for a plan test, holds the request; the recorded part is what the
scheduler produced on the day it was recorded, in a canonical form. A later commit that refactors
the scheduler reruns the same tests; a test fails if its output differs from the file, and the diff
of the file shows the reviewer exactly what changed. The initial states live in files of their own,
shared by the scenarios that start from them. The scenarios run on the sites 275_sunrise_b,
5675_pecos_combined and 38_gramercy (two blocking-tray fallbacks still on the synthetic tiny_lot);
the defunct 576_eccles and 1355_fulton sites and the synthetic layout_test and triple_pick_lot are
gone. Four new tests cover
behaviour the old tests did not reach. A Python viewer renders the scenarios as a web page.

## The files under `src/planner/scheduler/test/`

```text
test/
  .clang-tidy                          new: inherits the root config, drops bugprone-unchecked-optional-access
                                       for the test folder (as src/agvhito/test/.clang-tidy does)
  scenarios.hpp, scenarios.cpp         new: loads the running test's scenario file, builds the request, plans,
                                       records or compares
  initial_states.hpp, initial_states.cpp   new: loads an initial-state file into a DiscreteGarageState
  agv_commands.hpp                     new: IsLift / IsLower, read an AGV command's lift flags
  stages/                              tests that call a stage or a helper of the scheduler directly
    tray_assignment_tests.cpp          suite TrayAssignment, 5 tests
    agv_assignment_tests.cpp           suite AgvAssignment, 7 tests
    assignment_cost_tests.cpp          suite AssignmentCost, 4 tests: the cost functions
    sanity_check_tests.cpp             suite SanityCheck, 3 tests: SanityCheckEvents
    scheduler_state_tests.cpp          suite SchedulerState, 3 tests: readiness ratio, last entity event,
                                       continuous state to schedule
  jobs/                                tests through Scheduler::Plan(), one job type per file
    move_job_tests.cpp                 suite MoveJob, 3 tests (MOVE_AGV, MOVE_TRAY with a base schedule)
    repark_tray_job_tests.cpp          suite ReparkTrayJob, 4 tests
    repark_tray_job_charger_tests.cpp  ReparkTrayJob, 5 tests from or to an EV charger
    retrieve_job_tests.cpp             suite RetrieveJob, 7 tests
    retrieve_job_charger_tests.cpp     RetrieveJob, 3 tests from an EV charger
    charge_payload_job_tests.cpp       suite ChargePayloadJob, 3 tests
    insert_job_tests.cpp               suite InsertJob, 5 tests
    bay_job_tests.cpp                  suite BayJob, 4 tests: readiness and transitions
    agv_charge_job_tests.cpp           suite AgvChargeJob, 4 tests
    clean_garage_job_tests.cpp         suite CleanGarageJob, 3 tests
  utils/                               tests of scheduler/utils.hpp, the scheduler's helpers
    base_state_validation_tests.cpp    suite ValidateBaseState, 4 tests
    empty_tray_count_tests.cpp         suite CountEmptyTrays, 1 test
    bay_rebalancing_tests.cpp          suite BayRebalancing, 8 tests: classification, split, transitions
  scenarios/                           new: 60 initial-state files, 58 scenario files and a README
```

Each planning file is one gtest suite, named after the file, and one binary, named after the file
too (`build/scheduler/retrieve_job_tests`). `CMakeLists.txt` first builds `scenarios.cpp` and
`initial_states.cpp` once, as the static library `scheduler_test_support` (public: the `test/`
include directory, the scheduler library, yaml-cpp and gtest; private: the define
`SCHEDULER_SCENARIO_DIR`, the absolute path of `test/scenarios` in the source tree), then lists the
test files in `scheduler_tests` and one `foreach` adds each binary with
`volley_add_gtest(<name> test/<file>.cpp TIMEOUT 240 LINK_LIBRARIES scheduler_test_support)`. The
tests read and write the files in the source tree, never in `build/` or `install/`, so a recording
lands where git sees it and an authored file is read from where it is edited.

### `scenarios.hpp` and `scenarios.cpp`

The whole API is in the header. A plan test calls `scenarios::Plan()` (with a suffix when one test
has several scenarios, `scenarios::Plan("to_insert")`): it finds the file from gtest's current test
info, `plan/<suite in snake case>/<Name>[.<suffix>].yaml`, checks that its `test` key names the
running test, loads the initial state, builds a `Scheduler` with the file's parameters and a
`PlanRequestMsg` from the file's `request` (jobs numbered from GUID 1001 up and the request id 1000, above any node position, registered at time 0, in
the order listed; `base_schedule` entries as AGV commands), plans twice (both responses must agree:
planning is deterministic), and compares the canonical response with the file's recorded `output`,
or rewrites the recorded part when `RECORD_REFERENCE_OUTPUT` is set. It returns a `Run` with the
scenario, the scheduler, the request and the response, for the test's own assertions.

A stage test calls `scenarios::Stage("tray_assignment")` for its initial state, builds its
`ScheduleContext` and event DAG in code, takes `scenarios::Dag(*ctx)`, runs the stage and calls
`scenarios::ExpectStage("tray_assignment", dag_before, *ctx)`, which compares `input.dag` and
`output.dag` with the file under `task_planning/<stage>/`. The DAGs are compared the same way: the
events' `ToString()` texts, sorted and numbered, the edges as positions in that list, emitted to
text and compared line by line with the file's `input` and `output` nodes.

#### How the comparison works

Nothing is written to disk when a test compares; only recording writes. In `scenarios::Plan`:

1. The response comes back from `Scheduler::Plan` as a message in memory. `CanonicalResponse`
   copies it, replaces the GUIDs and sorts the jobs (below), then `MessageYaml` turns the copy into
   a `YAML::Node` in memory: `interfaces::msg::to_yaml` prints the message as YAML text, yaml-cpp
   parses that text, and two passes over the node put scalar sequences on one line and spell out
   the acronym field names. `Compact` then reduces the node to what differs from the message
   defaults (below).
2. The scenario file is parsed with `YAML::LoadFile`, and its `output` node is the expected side.
3. `ExpectSameDocument` emits both nodes to text with `Emit` (yaml-cpp's emitter, block style,
   into a string, not a file) and walks the two strings line by line with `std::getline`. The first
   line that differs, or the first document that ends early, fails the test with the line number
   and both lines: `recorded output of FromStall.yaml and the result differ at line 42`. Lines
   rather than node equality so that the failure says where, in the same text a reviewer sees in
   the file.

`Emit` round-trips through a load (emit, parse, emit again) because yaml-cpp prints a freshly
built empty collection and a parsed one differently; after the round trip both sides print the
same way. The in-memory text of the actual result is therefore exactly what recording would have
written, which is why recording cannot change what comparison sees.

Recording (`RECORD_REFERENCE_OUTPUT` set) is the only disk write: the file is read up to its first
`input:` or `output:` line, that authored text is kept byte for byte, and the recorded part is
emitted after it. The canonical response: action-node GUIDs
come from a process-wide counter (`CreateActionGuid` in `utils.cpp`), so each is replaced by the
node's position, followed everywhere the GUID was copied; `scheduled_jobs` are sorted by job GUID;
message fields named by an acronym are spelled out (`vexen` to `ev_chargers`, `vecs_command` to
`ev_charger_command`, `vrcs` to `vertical_conveyors`, and so on; the initial-state loader maps the
two list names back). `Compact` (`test/scenarios.cpp`) then walks the node: every GUID map
(`bytes: [...]`, recognised by `IsGuid`) becomes one scalar through `GuidScalar` (its value when only
the last four bytes are set, else the 8-4-4-4-12 form through `std::to_string(GuidMsg)` of
common_ros, the one the initial-state files use); every field that
`IsDefault` (zero, empty, `false`, an empty sequence, or a sub-message whose every field is a
default) is removed; and a map of at most two scalars, a pose, is set to flow style so it prints on
one line. The rule a reader needs is one sentence: an absent field holds its default. An action
node therefore carries only the command it is about, `parents` only when it has some, and `lift`
only when raised. The comparison runs on the compacted form of both sides, so it is as complete as a
comparison of the messages: a field that changes from its default to a value appears as an added
line in the diff, and a field that changes to its default as a removed one. A DAG is recorded as
its events' `ToString()`, sorted and numbered, with the edges as positions, since the events have
no stable id; it is small and is not compacted.

Guards around the files: `ExpectKeys` refuses a key outside the known set at every level of the
authored part (a mistyped `tray: 2` would otherwise read as the field's default); `ExpectOwnTest`
checks the `test:` key of every file that is compared with or recorded, the second-stage files of a
tray test included, so a file of another test is neither compared nor overwritten; recording never
creates a file (the authored part must exist) and fails when the write fails. `IsDefault` treats a
quoted scalar as a string, default only when empty, so a note of "0" or "false" is kept.

### `initial_states.hpp` and `initial_states.cpp`

`initial_states::Load("tiny_lot/car_at_p8")` returns the layout's name (the folder), the layout's
file path (through `GetLayoutPathByName`, or common_ros's `test_layout.yaml` for `layout_test`) and
the `DiscreteGarageState` parsed from the file. A missing file, an unknown layout or an invalid
state throws, which fails the test with the message.

### `stages/`

The stage tests. A typical one (`TrayAssignment.FillsBlankDestination`, the first test):

1. `const auto garage = scenarios::Stage("tray_assignment").initial;`: the layout and the state from
   the scenario's initial-state file.
2. `Scheduler scheduler(garage.layout_path, logger, params)`: the scheduler loads the layout file.
3. `ScheduleContext ctx(request_id, garage.state, now)`, then `ctx->events.AddEvent(tray_move)` with
   hand-built `TrayMove` / `AgvMove` events: the DAG a job expansion would have produced, written by
   hand so the test can start exactly at the stage it wants. Events are the scheduler's own objects,
   which is why they stay in code rather than in the file.
4. `scheduler.DoTrayAssignments(ctx)` or `scheduler.DoAgvAssignments(ctx)`: the stage under test,
   called directly (both are public methods of `Scheduler`).
5. Assertions on `ctx->events`, and the `scenarios::Dag` / `scenarios::ExpectStage` pair around
   step 4.

What the files cover: `tray_assignment_tests.cpp` (4 recorded under `task_planning/tray_assignment/`,
plus one that runs tray and AGV assignment in a row), `agv_assignment_tests.cpp` (7, recorded under
`task_planning/agv_assignment/`, with two more from the tray file), `assignment_cost_tests.cpp` (the
cost functions used by AGV assignment: pure arithmetic, so no scenario file; they load an initial
state directly), `sanity_check_tests.cpp` (`SanityCheckEvents` on 5675_pecos_combined: a move into a
disabled node, the same move twice, a move with no path) and `scheduler_state_tests.cpp` (the
readiness-ratio service, the last-entity-event bookkeeping, the continuous to discrete schedule
conversion; the only tests left that load a layout without an initial state). The stage scenarios
run around bay B2068 of 275_sunrise_b (door W2069, waypoints W2070 and W2064, stalls P2075, P2066,
P2067, P2077; `MovesOneBlocker` puts tray 2 on P2066, the one stall on tray 1's critical path from
P2067 to the bay) and, for the blockers, in the block of stalls east of the lane: three columns
(P2116 to P2119, P2132 to P2135, P2147 to P2150) hanging south of the lane waypoints W2115, W2131
and W2146, with the waypoint column W2100 to W2103 on the block's west side; the stalls connect to
their four neighbours. `ResolvesManyBlockersThenAssignsAgvs` puts the root tray in the south-east
corner P2150 with every stall on its way out occupied, so the critical path leaves along the south
row and two trays (P2135, P2119) must move first. `ResolvesBlockerChainRecursively` closes the block
off from the rest of the garage with `disabled_nodes` so that the chain has nowhere else to go.

### `jobs/`

One file per job type, one test per situation, all through `Scheduler::Plan()`, which is what the
planner node calls. A test is now its assertions:

```cpp
TEST(AgvChargeJob, SkipsDisabledChargers) {
  const auto run = scenarios::Plan();
  EXPECT_EQ(run.response.success, true) << run.response.message;
  ASSERT_EQ(1u, run.response.scheduled_jobs.size());
  auto last_node = run.response.schedule.nodes[run.response.schedule.nodes.size() - 1];
  EXPECT_EQ(16u, last_node.agv_command.dst.pose.node_id);
}
```

and its scenario file holds the rest:

```yaml
test: AgvChargeJob.SkipsDisabledChargers
description: >-
  Scenario: On 5675_pecos_combined, AGV 1 stands at W8 and the two nearest AGV chargers, C10 and
  C14, are disabled. Test: ... Expected: The AGV drives to C16, ...
initial_state: 5675_pecos_combined/agv_at_w8_chargers_10_14_disabled
scheduler:
  bay_readiness_ratio: 0.5
request:
  jobs:
  - type: CHARGE_AGV
    agv_id: 1
output:
  response: ...
```

The 38 tests walk the job types: `MOVE_AGV` and `MOVE_TRAY` (one with a base schedule that reserves
an AGV), `REPARK_TRAY` (plain, through a blocked row of stalls, unplugging a charger; from or to a
ready, unavailable or charging EV charger), `RETRIEVE` (from a stall, a disabled node, a charger;
with a bay transition, back to back, with a clean-garage job; the two blocking-tray fallbacks),
`CHARGE_PAYLOAD`, `INSERT` (with a clean-garage job; from both bays of pecos, tray straight or
reversed), `READY_FOR_RETRIEVE`, `READY_FOR_INSERT` and `TRANSITION_BAY` (unknown bay, wrong command,
both directions, disabled bay), `CHARGE_AGV` (nearest charger, from inside a bay, two AGVs, disabled
chargers), `CLEAN_GARAGE`. Most run around bay B2068 of 275_sunrise_b; the bay and AGV-charger
scenarios on `5675_pecos_combined`; the EV-charger scenarios on `38_gramercy`, the only current site
with EV chargers (E21, E23, E25). Gramercy's bay is the car lift BL26 on floor 1, so its retrieves
go through the lift: VRC commands around the AGV commands, and the AGV hops from the lift node L2
to BL26 without a command of its own, which `ExpectRetrieveThroughLift` in
`retrieve_job_charger_tests.cpp` allows for. The retrieval-heading rule (below) does apply on
gramercy, where stalls and lift share heading 90: a reparked car whose payload is reciprocal to the
tray is lowered at the reciprocal heading, so the repark assertions accept it. The two blocking-tray
fallbacks (`RetrieveJob.AdvancesRootTray`, `ParksBlockerOnCriticalPath`) are the one use of the
synthetic tiny_lot left: they need a lot that is full with nowhere to go. `IsLift` and `IsLower`
(`agv_commands.hpp`) read an AGV command's lift flags.

The insert tests from both pecos bays came from 1355_fulton, where they checked a V2 rule: the
inserted car is lowered at the heading that makes a later retrieve fastest (`InitRetrievalHeadings`
caches, per stall, the reciprocal of the highest-priority retrieve bay's inbound heading, when the
stall's headings allow it and the pose can reach the bay). On the layouts in use that rule has no
effect: on 275_sunrise_b by construction (bays at heading 0, stalls at 90, so 180 is never allowed
in a stall), and on 5675_pecos_combined because the planner logs "No retrieval heading for dest node
5 / 6" for the stalls (the heading check passes, so the path check must fail; not investigated
here). The four tests check what holds (the nearest AGV does the job, enters the bay at heading 90
also for a reversed tray, lifts, lowers outside the bay) and the file records the rest. Also
recorded, and worth a look by the team: on pecos the car is lowered on W31 / W41, the waypoint in
front of the bay, rather than in the free stall P15.

### `utils/`

Tests of `scheduler/utils.hpp`, the scheduler's helpers, rewritten from the old `utils_tests.cpp`.
`base_state_validation_tests.cpp` checks `ValidateBaseState` against 275_sunrise_b: a consistent
state passes, duplicate tray ids, a car that does not fit its stall and an AGV on a node the layout
does not have fail (the states come from `initial_states/`; the duplicate ids are set on the
message, since the state loader refuses them). `empty_tray_count_tests.cpp` builds a state event by
event and counts the empty, enabled trays as payloads, trays and nodes are added or disabled.
`bay_rebalancing_tests.cpp` covers the bay classification table, the classification of a whole
state, the desired insert / retrieve split for a range of ratios (a table of cases), the transitions
that split requires, and three end-to-end cases (a ratio of one, a disabled bay, a bay in flight);
its states are built in code with a small `MakeState({bays}, {trays})` helper, since they are
abstract (bays 1 to 4, no layout) rather than a garage.

### Conventions

The test code follows `src/agvhito/src/sm`: the file's own header first, then the `<...>` includes
the file uses in one sorted block, then the `"..."` includes; file-local constants and helpers in an
anonymous namespace, constants `k`-prefixed; `const` on every local that is not reassigned, by
reference when it only reads; `_or` suffixes for optional and expected values, `_it` for iterators;
`///` documentation comments with `@p` and `@return` on every declaration in a header and on
helpers, `[[nodiscard]]` on functions whose result is the point; `std::format` for messages; early
returns with `if(!x_or.has_value())`; comments as full sentences that say what holds, not what the
test "should" do; `EXPECT_TRUE` rather than `EXPECT_EQ(x, true)`. The request `note` field, which
the old tests filled with "hello", is left empty.

### `scenarios/`

`initial_states/<layout>/<name>.yaml`: 57 files in four layout folders (`275_sunrise_b` 29,
`5675_pecos_combined` 15, `38_gramercy` 11, `tiny_lot` 2), named after what stands in the garage, not
after a test, so that scenarios starting from the same state share one file. `plan/<suite>/<Name>.yaml`:
45 plan scenarios in ten suite folders. `task_planning/<stage>/<Name>.yaml`: 4 tray-assignment and 9
AGV-assignment scenarios. Every file sits two folders below `scenarios/`, which keeps VS Code's
SchemaStore from applying the Crowdsec scenario schema (its pattern is `**/scenarios/*/*.yaml`).
The README there explains both formats, the vocabulary, the layouts to use and avoid, how to build,
run and record, and the viewer. `tools/view_scheduler_tests.py` and the package `tools/plan_viewer/`
draw the scenarios: the garage to scale, the initial state, and one smooth path per AGV or tray
through the nodes its moves visit, in its own shade, kept to the right of its direction of travel
so that paths stay apart; hovering a step lights the stretch of path it covers.

## How a test run flows, from CMake to the comparison

Paths are relative to `src/planner/scheduler/` unless they start with `src/`. The sections follow
one run in the order things happen, naming the file and the function at each step, so that the
sequence can be followed in an editor.

### From CMake to a running binary

The test targets are declared in `CMakeLists.txt`, inside `if(BUILD_TESTING)`. The block first
calls `ament_find_gtest()`, so that the gtest targets and the `GTEST_INCLUDE_DIRS` and
`GTEST_LIBRARIES` variables exist, and then builds the two support sources once:
`add_library(scheduler_test_support STATIC test/scenarios.cpp test/initial_states.cpp)`, with
`test/` and the gtest headers as public include directories, the scheduler library, yaml-cpp and
gtest as public link libraries, and the private define
`SCHEDULER_SCENARIO_DIR="<source tree>/test/scenarios"`, the one place that says where the files
are. The `set(scheduler_tests ...)` list names the eighteen test files, and a
`foreach(test ${scheduler_tests})` loop adds each as
`volley_add_gtest(<name> test/<entry>.cpp TIMEOUT 240 LINK_LIBRARIES scheduler_test_support)`;
the includes and the scheduler library reach every test through the support library.

`volley_add_gtest()`, in `src/infrastructure/volley_cmake/cmake/volley_add_gtest.cmake`, parses
those arguments and calls `ament_add_gtest(<name> <sources> TIMEOUT 240)`, which creates the
executable `build/scheduler/<name>`, links `gtest` and `gtest_main`, and registers the executable
with CTest under its name; the wrapper then links the support library.

`poe build-pkg scheduler` runs `colcon build --packages-up-to scheduler`: the library, then the
eighteen executables. No scenario file is read at build time; the define bakes in where they are.
`poe test-pkg scheduler` runs `colcon test`, which runs CTest, which runs each executable with
`--gtest_output=xml:build/scheduler/test_results/scheduler/<name>.gtest.xml`, and
`colcon test-result --verbose` reads those files and prints the summary. One executable can be run
alone, as in `build/scheduler/retrieve_job_tests --gtest_filter='RetrieveJob.FromStall'`.

### Inside a binary, before the first test

Before `main`, during static initialisation, every `TEST(Suite, Name)` in the test file expands
(gtest's `TEST` macro, `gtest/gtest.h`) to a class `Suite_Name_Test` whose `TestBody()` is the
test's body, plus a static object whose constructor calls
`testing::internal::MakeAndRegisterTestInfo`, so the tests register themselves in file order with
their suite and name. In the same phase `test/scenarios.cpp` builds its static table `kJobTypes`
(job type name to `SchedulerJobMsg::TYPE_*`) and the two `kFieldNames` tables
(`test/scenarios.cpp`, `test/initial_states.cpp`).

`main` is gtest's, in `gtest_main.cc` (the first log line reads "Running main() from
./googletest/src/gtest_main.cc"). It calls `testing::InitGoogleTest(&argc, argv)`, which parses the
`--gtest_*` flags, then `RUN_ALL_TESTS()`, which runs every registered test in order in this one
process. One process for all tests is why the action-node GUIDs differ with the tests that ran
before (`CreateActionGuid` in `src/utils.cpp` draws them from a process-wide counter), and why the
recorded part replaces them by positions.

### One plan test, `RetrieveJob.FromStall` in `test/jobs/retrieve_job_tests.cpp`

The test body starts with `const auto run = scenarios::Plan();`. Nothing in that call says which
file to read, and that is the point: the file is found from the test's own identity. gtest keeps
the test it is running in `testing::UnitTest::GetInstance()->current_test_info()`, with the suite
name and the test name that the `TEST` macro registered; `TestName()` in `test/scenarios.cpp` joins
them as `RetrieveJob.FromStall`. `PlanPath(suffix)` turns the suite into snake case (`SnakeCase`,
`RetrieveJob` to `retrieve_job`) and the test name into a file name (`FileName`, which appends
`.<suffix>` when one is given), and returns
`<SCHEDULER_SCENARIO_DIR>/plan/retrieve_job/FromStall.yaml`. The default empty suffix is the
common case, one scenario per test; a test that plans several scenarios names them, as
`scenarios::Plan("second")` for `FromStall.second.yaml`. So the file is the test's name, and the
`test:` key inside the file names the test back: `Load` refuses a file whose `test:` is not the
running test, which catches a file saved under the wrong name or a test renamed without its file.
The convention is what lets a test consist of the call and its assertions, with no path in the
source, and it is also why a test name cannot repeat within a suite (gtest forbids that anyway).

`Load(path)` parses the whole file with `YAML::LoadFile`, checks the `test:` key as described,
refuses a key outside the known set (`ExpectKeys`), and fills the `Scenario`: `description`,
`initial_state`, `scheduler.bay_readiness_ratio`, and the `request` node kept as YAML for later.
It then calls `initial_states::Load(initial_state)` in `test/initial_states.cpp`, which builds
`<SCHEDULER_SCENARIO_DIR>/initial_states/275_sunrise_b/car_at_p2066_bay_ready_to_retrieve.yaml`,
parses it, renames `ev_chargers` to `vexen` and `vertical_conveyors` to `vrcs` (the `kFieldNames`
table) so that the message parser recognises them, resolves the layout through `LayoutPath`
(`GetLayoutPathByName` in `src/config/site_config/src/paths.cpp`, which searches the `layouts/`
folder for the file whose `name` key matches), and parses the state with
`DiscreteGarageState::Set(YAML::Node)` in `src/common_ros/src/discrete_garage_state.cpp`, which
reads each list, fills the defaults (lift false, tray 0, not disabled, hash) and refuses a
duplicate id.

Back in `Plan`, `std::make_unique<Scheduler>(layout_path, logger, params)` constructs the scheduler.
`Scheduler::Scheduler` in `src/scheduler.cpp` builds, in its member initialisers, the `Layout`
(`src/common_ros/src/layout.cpp`: nodes, edges, parking windows, bay prioritisation), the pose
graph and garage graph (`gg_`, `src/common_ros/src/garage_graph.cpp`) and the collision table
(`table_`, `src/common_ros/src/collision_geometry.cpp`), which is loaded from
`~/.cache/volley/<layout>_collision_table_<hash>.json` or computed and cached (the log line
"Loading collision table for layout ..."; a first run on a new layout takes seconds). The body then
calls `InitRetrievalHeadings()`, which caches per stall the heading a car should be parked at for
the fastest retrieve, where the stall allows it.

`BuildRequest(scenario, now)` turns the file's `request` into the `PlanRequestMsg`: the request id
is `MakeGuid(0, 1000)`, `base_state` is `initial.state.GetDiscreteGarageStateMessage()`, and each
entry of `request.jobs` becomes a `SchedulerJobMsg` with `type` through `kJobTypes`, `type_name`
the same word, `STATE_UNPLANNED`, a GUID numbered from 1001 up (above any node position, so that a
recorded `job_id` cannot be read as a node's positional GUID), `time_registered = now`, `note`,
`agv_id`, `bay_id`, `tray_id`, `payload` through `ParseGuid` (`src/common_ros/src/ros_utils.cpp`),
`destination` through `ConstructGaragePose` (`src/common_ros/src/pose_utils.cpp`) and
`allow_reciprocal`; each entry of `base_schedule` becomes an `ActionNodeMsg` of type
`TYPE_AGV_COMMAND` with the AGV and the two poses. A job entry with a key outside that list is
refused.

`run.response = run.scheduler->Plan(run.request, run.now)` is the code under test.
`Scheduler::Plan` in `src/scheduler.cpp` first runs `ValidateBaseState` (`src/utils.cpp`: duplicate
ids, cars that do not fit, nodes not in the layout; a failure returns `success = false`), builds a
`ScheduleContext` from the validated state and the base schedule, and then expands every pending
job through one `case` per type: `PlanAgvMoveJob`, `PlanRetrieveJob`, `PlanReparkTrayJob` (also for
`MOVE_TRAY`), `PlanInsertJob`, `PlanReadyForInsertJob`, `PlanReadyForRetrieveJob`,
`PlanCleanGarageJob`, `PlanRebalanceGarageJob`, `PlanAgvChargeJob`, `PlanBayTransitionJob` and
`PlanChargePayloadJob`, all in `src/scheduler.cpp`. Each appends events (`TrayMove`, `AgvMove`,
`BayTransition` and the others in
`src/planner/planner_core/include/planner_core/schedule_events.hpp`) to the context's event DAG,
or fails the job (`FailJob`: `STATE_ERROR` and the message in `note`). The stages then run on the
DAG: `DoTrayAssignments` chooses a stall for every tray move without one and resolves blocking
trays (`ResolveBlockingTrays`, `FindOpenSpaceForRootTray`); `DoAgvAssignments` picks an AGV for
every tray move (`GetAgvToTrayAssignmentCost` and the other cost functions); `events.Reduce()`
drops the edges that other edges imply; `SanityCheckEvents` applies every event in order to the
state; `PlanMotions` (in `src/scheduler.cpp` and the motion planner under
`src/planner/motion_planner/`) produces trajectories with times and lifts; and
`ResponseFromTrajectories` turns them into action nodes with durations and parents
(`InsertVrcActionsIntoDag` in `src/utils.cpp` adds the lift commands). The result is the
`PlanResponseMsg` with `success`, `schedule.nodes` and `scheduled_jobs`.

The response is then put into the canonical form. `CanonicalResponse` copies it, replaces each
action node's `guid` by `MakeGuid(0, position + 1)` and follows the replacement into
`agv_command.id`, `vecs_command.command_id`, `vrc_command.command_id` and every job's
`bay_arrival_node_guid`, sorts `scheduled_jobs` by job GUID, and calls `MessageYaml`:
`interfaces::msg::to_yaml` (generated, under `build/interfaces/`) prints the message as text,
`YAML::Load` parses it, `FlowScalarSequences` puts scalar sequences on one line and
`SpellOutFieldNames` renames the acronym fields. `Compact` then turns GUIDs into scalars, drops
every field that holds its default and puts poses on one line.

`Plan` plans a second time and canonicalises that response too, and
`ExpectSameDocument(first, second, "two planning runs of the same scenario")` compares the two:
both are emitted with `Emit` (yaml-cpp's emitter into a string, then parsed and emitted once more
so that fresh and parsed empty collections print the same) and walked line by line with
`std::getline`; a difference is an `ADD_FAILURE()` naming the line and both texts. Only a
deterministic scheduler can be recorded, so this check comes before the comparison with the file.

`ExpectRecorded(path, {output: {response: first}})` is the comparison itself. The file must exist
and its `test:` key must name the running test (`ExpectOwnTest`). Without
`RECORD_REFERENCE_OUTPUT` in the environment, `YAML::LoadFile(path)["output"]` is the expected
side and `ExpectSameDocument` compares it with the canonical response in the same way. With the
variable set, `AuthoredText` reads the file up to its first `input:` or `output:` line, the file is
rewritten as that text followed by `Emit(recorded)`, the write is checked, and "Recorded <path>" is
printed. `Plan` finally returns the `Run` (scenario, scheduler, now, request, response), and the
test body continues with its own assertions on `run.response`, `run.request` and `run.scheduler`:
`EXPECT_TRUE(run.response.success)`, the chain of AGV commands, the lift and the lower, the
`PROCESS_RETRIEVE` command. gtest records every failed `EXPECT_*` and stops the body at a failed
`ASSERT_*`.

### One stage test, `TrayAssignment.MovesOneBlocker` in `test/stages/tray_assignment_tests.cpp`

A stage test starts from a file too, through `scenarios::Stage("tray_assignment")`, which is
`Load(StagePath(stage, suffix))` with the path
`<SCHEDULER_SCENARIO_DIR>/task_planning/tray_assignment/MovesOneBlocker.yaml`: the folder is the
stage named in the call and the file name is again the test's name. `Load` runs as for a plan
scenario, except that the file has no `request`; the test takes `.initial` from it, the initial
state and its layout.

The test then builds by hand what a job expansion would have produced: a
`Scheduler scheduler(garage.layout_path, logger, params)` as above, a `ScheduleContext`
(`include/scheduler/scheduler.hpp`) from `garage.state`, and a `TrayMove`
(`src/planner/planner_core/include/planner_core/schedule_events.hpp`) with `SetTrayId(1)` and
`SetDest(ConstructGaragePose(2068, 0))`, added with `ctx->events.AddEvent(tray_move)` to the event
DAG (`src/planner/planner_core/include/planner_core/event_dag.hpp`). Events are the scheduler's
own objects, which is why they stay in code rather than in the file.

`const auto dag_before_tray = scenarios::Dag(*ctx);` takes the picture of the DAG before the stage:
`Dag` names every vertex by its event's `ToString()` (`std::to_string(*event)`), numbers repeated
strings, sorts them, lists the edges of `ctx.events.GetBaseGraph()` as pairs of positions in that
list, and `ctx.first_tray_event` as tray id to position. `scheduler.DoTrayAssignments(ctx)` is the
stage under test; it fills blank destinations, resolves blocking trays and adds their moves to the
DAG. Here tray 2 at P2066 stands on the critical path, so the stage adds its move to a free stall
and an edge from it to the root move.

`scenarios::ExpectStage("tray_assignment", dag_before_tray, *ctx)` takes a second `Dag(ctx)` and
calls `ExpectRecorded(StagePath(...), {input: {dag: before}, output: {dag: after}})`, which compares
both parts with the file's `input` and `output` or records them, exactly as for a plan scenario.
The test's own assertions follow (`EXPECT_TRUE(success) << msg`). A test that runs two stages in a
row, as `ResolvesManyBlockersThenAssignsAgvs` does, calls `ExpectStage` once per stage, and the
second call writes to or compares with the file of the same name under the second stage's folder;
`ExpectOwnTest` checks that this file names the running test too.

### What a failure looks like

gtest prints the file and line of the failing assertion. For a recorded-part mismatch the message
reads `recorded output of FromStall.yaml and the result differ at line 42`, with the expected and the
actual line, so the next step is to open the scenario file at that line; for a determinism failure
it reads `two planning runs of the same scenario differ at line ...`.

## clang-tidy on this branch

### What runs, from which files

- `prek.toml`, hook `clang-tidy`: stage `pre-push`, so it runs on `git push`, after the quick hooks;
  `entry = tools/clang-tidy-diff-hook`, `args = ["--base-ref=main"]`, `pass_filenames = false`
  (the script finds the files itself), `require_serial = true` (prek runs no other hook alongside).
- `tools/clang-tidy-diff-hook`, `main()`: checks that `clang-tidy-diff` is on the PATH (the
  container's; this is why pushes go through the container) and that `build/compile_commands.json`
  exists (written by `poe build`; without it the hook fails at once with "Run 'poe build' first").
  `resolve_merge_base` fetches `origin/main` and deepens history until a merge base resolves.
  `run_clang_tidy_diff` takes `git diff -U0 --diff-filter=ACMR origin/main...HEAD -- src/*.cpp
  src/*.hpp ...` and pipes it into `clang-tidy-diff -p1 -path build -j <cpu count> -quiet`.
- `clang-tidy-diff` (LLVM's script, in the container): for every file in the diff it runs
  `clang-tidy` on the whole translation unit, with the compile command from
  `build/compile_commands.json`, and keeps only the diagnostics whose line is in the diff. Whole
  translation units, because clang-tidy has to parse and analyse the file to say anything about
  a line.
- `.clang-tidy`: the checks, `bugprone-*`, `cppcoreguidelines-*`, `clang-analyzer-*`, `google-*`,
  `modernize-*` and `readability-identifier-naming`, minus the listed exceptions, each with a
  justification in the file (and `docs/guides/cpp-style.md` for the conventions tidy does not
  cover). `readability-identifier-naming` is what enforces the `kConstant`, `member_`,
  `FunctionName` naming.

### Where the output goes

Nowhere while it runs: the hook collects clang-tidy's stdout and stderr into one string and prints
it only at the end, as an error when the exit code is non-zero or the text contains `warning:` or
`error:`, as plain output otherwise. prek shows a hook's output only when the hook fails, so a
clean run prints nothing beyond "Passed", and a failing run prints the findings under the hook's
name, each as `<file>:<line>:<column>: warning: <message> [<check>]`. The script has an
`--output-log <file>` option that also writes the text to a file, but prek does not pass it. To
run it by hand and keep the text (in the container, from the workspace root):

```bash
tools/clang-tidy-diff-hook --base-ref=main --output-log /tmp/clang-tidy.log
```

or `prek run --hook-stage pre-push clang-tidy`. From the host, `volley-in-container tidy` runs the
same hook on the lines changed since `main` and saves the full output under
`~/.cache/volley-in-container/logs/`.

### Why this branch took so long, and what fixed it

The first runs of the hook on this branch took 14 to 20 minutes, and they looked single-threaded
after the first minute or two. The cause was in the test `CMakeLists.txt`, not in clang-tidy:
`scenarios.cpp` and `initial_states.cpp` were listed as sources of every one of the 18 test
binaries, so `build/compile_commands.json` held 18 compile commands for each of them. clang-tidy
analyses a file once per compile command, in one process, one after the other; the hook's output
showed it as two runs of 18 cumulative `N warnings generated` lines (109,303 per pass for one
file, 190,054 for the other). The 21 other translation units finished in parallel on the 24 cores
in about a minute, then those two single processes ground through 18 analyses each.

The fix is the static library `scheduler_test_support` (see the CMake walkthrough): the two files
are compiled once, so clang-tidy analyses them once. Measured with `volley-in-container tidy` on the
same diff, same machine:

| | Analyses | Wall time |
|---|---|---|
| Support files as sources of every binary | 57 | 822 s |
| Support files in `scheduler_test_support` | 23 | 66 s |

What remains is the genuine cost: 23 translation units, each including `scheduler/scheduler.hpp`
(the ROS message headers, the Boost graph of the event DAG, the motion planner, yaml-cpp), with
`clang-analyzer-*` doing path-sensitive analysis over everything reached through the headers.
That is the roughly 190,000 header warnings per unit that `clang-tidy-diff` filters out, and about
a minute of wall time with the units in parallel. A typical PR touches two or three units and pays
a few seconds. The time is spent only on pushes (and on `volley-in-container tidy`); commits run
clang-format, not clang-tidy.

The same pattern is worth a look wherever a source file is listed in several test targets of one
package: it multiplies both the build and the tidy cost by the number of targets.

### How to think about it

- It gates the lines this branch changed, not the files: a diagnostic on an untouched line of a
  touched file is dropped. On this branch almost every line of the test files is changed, so for
  practical purposes the whole test folder is under review.
- The findings to expect on test code are naming (`readability-identifier-naming`), `modernize`
  suggestions and `bugprone` ones; `cppcoreguidelines` on the gtest macros is mostly excepted in
  `.clang-tidy`. Fix a finding in the code when it is right; when a check misfires on a test
  idiom, a `// NOLINT(<check>)` on the line with a reason is the team's escape hatch, and a new
  file-wide exception belongs in a `.clang-tidy` with a justification, not in the test.
- The first run over the rewritten files (the push of 2026-10-26) reported two kinds of finding,
  both now resolved in the commit:
  - `bugprone-unchecked-optional-access` on every `.value()` or `->` that follows an
    `ASSERT_TRUE(x.has_value())` or `EXPECT_TRUE(...)`: the check's dataflow analysis does not
    see through the gtest macros, so it reports a value as unchecked that the test has just
    checked. A test that dereferences an empty optional throws, which is an acceptable failure
    mode for a test, so the check earns nothing here. `src/agvhito/test/.clang-tidy` already
    carries that exception for the agvhito tests; `src/planner/scheduler/test/.clang-tidy` is the
    same file (`InheritParentConfig: true`, `Checks: -bugprone-unchecked-optional-access`, with the
    reason as a comment). clang-tidy takes the nearest `.clang-tidy` up the directory tree, so it
    covers `stages/`, `jobs/`, `utils/` and the support sources, and nothing under `src/`.
  - `readability-identifier-naming` on two `constexpr` locals inside a test body: the root
    `.clang-tidy` has `LocalConstantCase: lower_case` with `LocalConstantPrefix: k_`, while
    `GlobalConstantCase: CamelCase` with prefix `k` is the `kConstant` form. A constant that is
    local to a function is `k_root_tray_id`; the same constant at file scope (in the anonymous
    namespace) would be `kRootTrayId`. The two in `TrayAssignment.ResolvesBlockerChainRecursively`
    are renamed.
  - The `N warnings generated` lines in the hook's output are clang-tidy's per-unit totals,
    almost all from the included headers and filtered out by `clang-tidy-diff`; only the listed
    `<file>:<line>` findings count.
- Run it before a push that touches many files, so that the push itself is quick:
  `volley-in-container tidy`. And do not edit the working tree while a push runs: prek checks
  whether any file changed during a hook and fails the push with "files were modified by this
  hook" even when clang-tidy found nothing. The second push of 2026-10-26 failed that way (two
  scenario descriptions were edited in this session while the hook ran), with no finding listed.
- The same cost returns on every push of a rewritten history, since the diff against `origin/main`
  is recomputed; once the branch is merged, later PRs pay only for their own changes.

## The three kinds of YAML and how they fit

| File | Holds | Who reads it |
|---|---|---|
| `src/config/site_config/layouts/<name>.yaml` | the static garage: `nodes` (id, type, x, y, allowed headings, size), `edges`, `parking_windows`; nothing about what stands where | `Scheduler`'s constructor, through the initial state's layout path; the viewer, to draw |
| `test/scenarios/initial_states/<layout>/<name>.yaml` | what stands in the garage when the scenario starts: AGVs, trays, bays, EV chargers, payloads, disabled nodes, each with pose and state; fields at their default left out, numeric states commented | `initial_states::Load`, into a `DiscreteGarageState` |
| `test/scenarios/<stage>/.../<Name>.yaml` | authored: the test, the description, the initial state, the scheduler's parameters, the request; recorded: `output` (and `input.dag` for a stage) | `scenarios::Plan` / `ExpectStage`, to build and compare; the viewer, to draw and tabulate |

`src/config/site_config/layouts/initial_conditions.yaml`, which also places AGVs and trays, is the
simulator's initial placement; the scheduler and its tests never read it.

## What is tested against what

Two things, on every run. The `EXPECT_*` lines of a test are hand-written expectations of the
properties its author cared about (the last command ends at the destination, there is a lift before
the move, the job is returned as executing); they are the specification as far as it was written
down. The recorded `output` of the scenario file is the complete result, compared line by line, so
that a refactor cannot change a detail nobody thought to assert. A recorded file is not a claim
that the output is right; it is a claim that it is what the scheduler produced before the refactor.
Where it is wrong, the fix is a later commit that changes behaviour on purpose and re-records the
file, and the diff is the evidence.

## Questions and answers

### Why is the commit so large, and is it mainly configuration?

It was mainly recorded output, not configuration, and the recorded output has since been compacted.
The diff against main is now 165 files in two commits, about 14,300 lines added and 6,700 removed
(it was 30,600 added before the compaction); the viewer is the second commit. By kind:

| Kind | Files | Lines added | Lines removed |
|---|---|---|---|
| Plan scenario files, recorded part (`output:`) | 45 | 5,795 | |
| Plan scenario files, authored part | 45 | 604 | |
| Stage scenario files (`task_planning/`) | 13 | 381 | |
| Initial-state files | 59 | 1,159 | |
| Test C++ (the split test files and the four support files) | 27 | 3,176 | 6,546 |
| Viewer (`tools/plan_viewer/`, Python, JS, CSS, HTML) | 18 | 3,016 | |
| `scenarios/README.md` | 1 | 181 | |
| CMake, `.clang-tidy`, `pyproject.toml`, `uv.lock`, the deleted `garage_states/` file | 5 | 63 | 142 |

The recorded responses are 41% of the added lines; the authored material (initial states plus the
authored part of every scenario) is about 2,100 lines; the code is about 6,100 lines, of which the
test C++ is a net removal (the YAML literals leave the sources). What is left to review by hand is
the authored material, the test C++ and the viewer; the recorded part is read through the viewer or
through a diff when a later commit changes it.

### Can the recorded part be made smaller?

It has been, by 74%: from 22,257 recorded lines to 5,795, measured on the same 45 scenarios. The
response message is emitted whole by `to_yaml`: four command sub-messages per action node of which
one is in use, zero headers and timestamps, two-line GUIDs. `Compact` in `test/scenarios.cpp`
(see "How the comparison works") now leaves out every field that holds its default, writes a GUID
as one scalar and a pose on one line. The rule for a reader is that an absent field holds its
default; `scenarios/README.md` states it. The comparison is as complete as before, because both
sides are compacted by the same function.

What remains is proportional to the decisions: 435 action nodes at about 13 lines each. Two
further steps are possible and not taken:

- Flow style for whole action nodes (one line per node) would halve it again at the cost of diff
  granularity: a changed heading and a changed duration would then share a line.
- Moving the recorded part into a file of its own next to the authored one would keep the files
  that are read by hand short, but not reduce the line count.

### What do the scenario tests compare: the request and response only, or intermediate state too?

Both, in two different families of test.

- The 45 plan tests (`test/jobs/`, plus the move tests) go through `Scheduler::Plan` and compare
  the response message only: `success`, `message`, the schedule's action nodes with their
  `parents` indices, durations, AGV, bay, charger and conveyor commands, and the modified
  `scheduled_jobs`. That is the interface of the scheduler as the executor and the fleet see it.
  The `ScheduleContext` that `Plan` builds (the event DAG, `last_entity_event`,
  `first_tray_event`, the disabledness filters) is created and discarded inside `Plan`, and no
  test can see it without a change to the library, which this commit does not make. The
  trajectories of the motion planner are not recorded either; only the discrete commands and
  durations derived from them are.
- The 13 stage tests (`test/stages/tray_assignment_tests.cpp`, `agv_assignment_tests.cpp`)
  build a `ScheduleContext` by hand, call `DoTrayAssignments` or `DoAgvAssignments` directly and
  record the event DAG before and after the stage (`input.dag`, `output.dag`): every event by its
  `ToString` (job index, type, tray, destination, AGV, discrete change, bay state and command),
  the edges, and `first_tray_event`. That is the intermediate structure the refactor's solvers
  will produce, so these files are the parity check for `TrayMoveSolver` and
  `AgvAssignmentSolver` on their own output. Not recorded: `scheduled_jobs`,
  `last_entity_event`, the working state, and the fields of an event that `ToString` does not
  print (its interval and cost).
- The remaining tests (`assignment_cost_tests`, `sanity_check_tests`, `scheduler_state_tests`,
  `utils/`) assert on the return values of helpers directly, without a recording.

The imbalance (45 end-to-end scenarios, 13 stage scenarios) is the one to keep in mind. Every
plan scenario does pass through both stages, and a solver that changes a stage's output changes
the response, so the plan files catch the change; they do not say which stage changed. The
precise tool for that is commit 2's solver interface: once `Plan` goes through it, a test can
record the DAG after each stage for every plan scenario without hand-built contexts.

### Why compare YAML text with YAML text instead of data structures?

The reference has to live on disk, survive rebuilds and be readable in a review, so it is
serialized either way; the choice is only whether the comparison runs on the text or on a
deserialized structure. The text was chosen because:

- The emitted text is a deterministic function of the message: `interfaces::msg::to_yaml` writes
  every field in declaration order, and `Emit` normalises the yaml-cpp style, so equal text is
  equal messages and vice versa, with one exception below.
- The exactness lives in the canonical form, not in the medium. GUIDs are replaced by node
  positions and jobs are sorted before emission, because the scheduler draws GUIDs from a
  process-wide counter and the raw structures differ between runs. A comparison on structures
  would need the same canonicalisation first, at which point it compares the same thing.
- A text diff reports the field and the line (`output.response.schedule.nodes[3].agv_command.dst`
  reads off the file), where the generated `operator==` of a message reports a bool, and a
  field-walking diff printer would have to be written for every message type.
- The event DAG has no `operator==` at all (polymorphic events behind shared pointers in a Boost
  graph, with vertex numbering that depends on insertion order), so a canonical, order-independent
  form has to be defined to compare it; `Dag()` is that form, and once it exists, comparing its
  text is the simplest thing to do with it.
- The same file is what the viewer draws and what the review diff shows; one artefact, no
  second representation to keep in step.

Where the text is less exact than the structure: floating point. The response tree has two float
fields, `ActionNode.duration` and `SchedulerJob.seconds_to_bay_arrival`, and `to_yaml` prints
them with the stream's default six significant digits (`11.3033`, `6.81000`). A refactor that
changed a duration below that resolution (a different summation order in the motion planner,
say) would pass the comparison. Everything else in the messages is integer, enum, bool or
string and compares exactly. If that resolution matters for the parity check, `CanonicalResponse`
can overwrite the two fields with their full-precision text before emission (the message is still
in hand there); it is a few lines and a re-recording, and it is left out because a sub-microsecond
drift in a duration is not a difference the refactor is meant to preserve. It is not possible to
be more exact than the structure, and this is the only place where the text is less.

## Review against the Greptile configuration

Done on 2026-10-26 before the PR, with the team's Greptile custom instructions (commit and PR
hygiene, comments and documentation) as the checklist, plus two independent correctness reviews of
the C++ and of the viewer. Everything found is fixed in the commit except the items under "left".

Commit and PR hygiene: one commit, Conventional Commits header, body updated to name the compact
recorded form, the support library and the tidy exception. PR title convention in this repo is
`[SW2-484] <description>` (see PR #994); suggested: `[SW2-484] Record the scheduler planning tests as
scenario files`.

Comments and documentation, fixed:

- The 15-line narrative in `tray_assignment_tests.cpp` (a history of the recursion, "before /
  after") is gone; the test keeps a three-line why. The "ordering should now be" list in
  `agv_assignment_tests.cpp` is one line; the six-line reduction comment is three.
- TODOs without a ticket: `TODO (Rayne)` on `RetrieveJob.WithCleanGarage` said the test fails, but
  it passes and is recorded, so it is removed (and the sentence in the scenario's description);
  `TODO(joe) add this to params` twice in the cost tests is a comment naming the cost model's
  default the constant repeats; `TODO(isabel)` had no action and is removed.
- Debug output: three `DrawGraph` calls wrote `/tmp/*.dot` on every run of the tray tests; removed
  with the unused topological orderings around them.
- Dead code: the `layout_test` branch of `initial_states.cpp` (no state uses it) and its include.
- Stale documentation: the README's example scenario was the tiny_lot version of `FromStall`,
  and its `initial_states::Load` example named a file that does not exist; both now match real
  files. `scenarios.hpp` and the "No recorded output" message named the author's local wrapper;
  they name `RECORD_REFERENCE_OUTPUT=1` instead. The `pyproject.toml` comment named the tool's old
  file name. A clean-garage failure message said "waypoint 3" for W2070.

Correctness, fixed:

- Every test that indexed the schedule (`schedule[size - 2]`, `.back()`, a loop bound of
  `size() - 1` that wraps when empty) or dereferenced an optional or an iterator after an `EXPECT`
  now has an `ASSERT` first, so a regression fails with the recorded diff instead of a crash of the
  binary. `std::get` on the discrete-change variant is `std::get_if`.
- Recording guards and the unknown-key check (above). The GUID string form prints uppercase, as
  `volley::to_string` does. Job GUIDs are numbered from 1001 and the request id is 1000, so a
  recorded `job_id` cannot be read as a node's positional GUID (a schedule of 32 nodes showed
  `guid: 32` and `job_id: 32` on one node).
- Viewer: every lift and lower of a plan scenario was drawn with the lift-ride badge, since the
  same-node branch ran before the action was looked at; the corner control point collapsed onto
  the node centre for every turn (the two lines were both drawn through the node), so corners cut
  through nodes and lanes converged there; the car-lift bay `BLift` of 38_gramercy was drawn as a
  stall named N26 with its coincident `Lift` node on top; a scenario file that awaits its first
  recording crashed the page build; hover effects of hidden steps lit ghosts while the solution
  was hidden; the layout index found a tree entry by name, which repeats across folders; paths
  outside the workspace raised in `relative_to`; a job without a payload read "payload none".

Done afterwards, from the implicit-guidelines report of 2026-10-26 (`pr_prep_plan.md`): the
unused `ament_index_cpp` test dependency dropped; nine test names shortened to five words or
fewer (all in `test/utils/`, no scenario files involved); the viewer split into a second commit of
the same PR; the PR description drafted with the traceability list (`pr_description.md`); the
README and the description say that the files are gtest inputs, not simulation scenarios, for
Greptile's knowledge-base checks; `GuidScalar` prints through `std::to_string(GuidMsg)`; one
`scenarios::kNow` (the epoch in ROS time) replaces fifteen default-constructed `rclcpp::Time()`
values and `Plan`'s `rclcpp::Time(0)`.

Then B8 and B9 of the same plan: the viewer's two 800-line modules are split along their layers,
each a class that only uses what its base defines, so mypy needs no stubs: `records.py` (the
scheduler's vocabulary and the parsing of its recorded data), `reader.py` (`Reader`: one file's
state, request, response, steps and graphs), `tables.py` (`Tables(Reader)`), `scenarios.py`
(`Adapter(Tables)`, which assembles the `Scenario`, plus `load`); and `canvas.py` (`Canvas`: the
figure, its bookkeeping and the drawing primitives), `paths.py` (`StepDrawing(Canvas)`: the AGVs'
paths, corners, badges), `scene.py` (`Scene(StepDrawing)`: the garage and the initial state).
The page built after the split is byte-identical to the one before. The two stale entries about
`scheduler_jobs_tests.cpp:2244` in `docs/deprecated/` are removed (that test is
`RetrieveJob.WithCleanGarage`, recorded and passing).

Left, as review points rather than changes:

- `StagePath` has no suite component, so `TrayAssignment.X` and `AgvAssignment.X` would share
  `task_planning/agv_assignment/X.yaml`; `ExpectOwnTest` now makes such a collision a loud failure
  instead of a silent one. Likewise `retrieve_job_tests` and `retrieve_job_charger_tests` share the
  suite `RetrieveJob`, so a duplicate test name across the two binaries would share one recording.
- The description parser of the page drops text before the first "Scenario:".

## Open points for your review

- The two blocking-tray fallback scenarios stay on tiny_lot. On 275_sunrise_b with the garage
  open the blocker drives off to a waypoint and no fallback fires; with everything outside a region
  disabled, either the tray finds no path (a disabled waypoint 0.8 m from the bay's door node counts
  as a disabled area, and an AGV on the only rotation node blocks the tray) or, once the fallbacks do
  fire, the planner cycles for minutes. Keep tiny_lot for these two, or drop them? The cycling itself
  may be worth a look.
- The retrieval-heading rule is exercised by no test any more (see the insert tests above).
- The inserted car parked on the waypoint in front of the bay (W31 / W41) instead of the free stall.
- `AgvChargeJob.TwoAgvsDistinctChargers` gave both jobs the same GUID in the old test, so the
  scheduler planned a single job; the scenario file numbers them 1001 and 1002 and both AGVs now charge,
  which changed that recording.
- `ReparkTrayJob.UnplugsChargerAgvMovesFirst` is the same scenario as `ReparkTrayJob.UnplugsCharger`.
  Kept because deleting a test is a coverage decision.
- The `agv_command.id` field of an action node is never set by the scheduler, so the GUID
  replacement there does nothing today; it is in place in case a later commit starts setting it.
