# Commit 1: scenario files for the planning tests

Status: two commits on jmg/SW2-1126/scheduler-scenario-files (Jira SW2-1126, child of epic
SW2-482; PR #1007), on top of main (dd96ed86): b26ea5d6
`test(scheduler): record the planning tests as scenario files` and b62423ca
`feat(scheduler): add a viewer page for the test scenarios`; amended after every review round
(review log items 1 to 150 in `../SW2-482_notes.md`; the PR review feedback is answered item by
item in the section of that name below). This document describes the commit as it stands; it is
rewritten after every change to the code.

## Contents

- [What the commit does, in one paragraph](#what-the-commit-does-in-one-paragraph)
- [The files under src/planner/scheduler/test/](#the-files-under-srcplannerschedulertest)
  - [The support library: scenarios/](#the-support-library-scenarios)
    - [How the comparison works](#how-the-comparison-works)
  - [initial_states.hpp and agv_commands.hpp](#initial_stateshpp-and-agv_commandshpp)
  - [src/stages/](#srcstages)
  - [src/jobs/](#srcjobs)
  - [src/utils/](#srcutils)
  - [Conventions](#conventions)
  - [scenarios/, the data](#scenarios-the-data)
- [How a test run flows, from CMake to the comparison](#how-a-test-run-flows-from-cmake-to-the-comparison)
  - [From CMake to a running binary](#from-cmake-to-a-running-binary)
  - [Inside a binary, before the first test](#inside-a-binary-before-the-first-test)
  - [One plan test, RetrieveJob.FromStall in test/src/jobs/retrieve_job_tests.cpp](#one-plan-test-retrievejobfromstall-in-testsrcjobsretrieve_job_testscpp)
  - [The determinism test of a suite](#the-determinism-test-of-a-suite)
  - [One stage test, TrayAssignment.MovesOneBlocker in test/src/stages/tray_assignment_tests.cpp](#one-stage-test-trayassignmentmovesoneblocker-in-testsrcstagestray_assignment_testscpp)
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
  - [Why did the tests take ten minutes on CI, and what was done about it?](#why-did-the-tests-take-ten-minutes-on-ci-and-what-was-done-about-it)
  - [Why compare YAML text with YAML text instead of data structures?](#why-compare-yaml-text-with-yaml-text-instead-of-data-structures)
- [Review against the Greptile configuration](#review-against-the-greptile-configuration)
- [PR review feedback](#pr-review-feedback)
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
gone. Four new tests cover behaviour the old tests did not reach; eight `Deterministic` tests, one per
job suite, plan every scenario of the suite twice; eight `ScenarioYaml` tests cover the files'
decoders. A Python viewer renders the scenarios as a web page.

## The files under `src/planner/scheduler/test/`

Everything under `test/` lives in the namespace `volley::scheduler::test` (the pattern of
`src/agvhito/test` and `src/core/yasminx/test`), with `scenarios` and `initial_states` as nested
namespaces; the library itself stays in `volley`. Headers sit under `test/include/scheduler/test/`
and are included as `"scheduler/test/..."`, the sources under `test/src/`, the data under
`test/scenarios/`:

```text
test/
  .clang-tidy                            inherits the root config, drops bugprone-unchecked-optional-access:
                                         the dataflow analysis cannot see gtest's ASSERT_TRUE on has_value()
  include/scheduler/test/
    initial_states.hpp                   InitialState {layout_path, state}; Load("<layout>/<name>")
    agv_commands.hpp                     IsAgvLiftRaised / IsAgvLiftLowered, an AGV command's lift flags
    scenarios/                           the support, one header per responsibility (namespace scenarios)
      yaml.hpp                           YAML::convert for pose, job, base-schedule command, params, Request
      file.hpp                           Scenario; PlanPath, StagePath, Load, Read, ExpectOwnTest, AuthoredText
      request.hpp                        BuildRequest: the scenario's request as the scheduler receives it
      recording.hpp                      MessageYaml, Compact, Emit, ExpectSameDocument, ExpectRecorded
      shared_scheduler.hpp               kNow; SharedScheduler, one per layout and parameters per process
      plan.hpp                           Run; Plan (one plan, compared); ExpectDeterministic (a suite twice)
      stage.hpp                          Dag; Stage; ExpectStage
  src/
    initial_states.cpp, scenarios/*.cpp  the support library's sources, one per header
    stages/                              tests that call a stage or a helper of the scheduler directly
      tray_assignment_tests.cpp          suite TrayAssignment, 5 tests
      agv_assignment_tests.cpp           suite AgvAssignment, 7 tests
      assignment_cost_tests.cpp          suite AssignmentCost, 4 tests: the cost functions
      sanity_check_tests.cpp             suite SanityCheck, 3 tests: SanityCheckEvents
      scheduler_state_tests.cpp          suite SchedulerState, 3 tests: readiness ratio, last entity event,
                                         continuous state to schedule
    jobs/                                tests through Scheduler::Plan(), one job type per file, each with a
                                         Deterministic test for its suite's folder
      move_job_tests.cpp                 suite MoveJob, 4 tests (MOVE_AGV, MOVE_TRAY with a base schedule)
      repark_tray_job_tests.cpp          suite ReparkTrayJob, 5 tests
      repark_tray_job_charger_tests.cpp  ReparkTrayJob, 5 tests from or to an EV charger
      retrieve_job_tests.cpp             suite RetrieveJob, 8 tests
      retrieve_job_charger_tests.cpp     RetrieveJob, 3 tests from an EV charger
      charge_payload_job_tests.cpp       suite ChargePayloadJob, 4 tests
      insert_job_tests.cpp               suite InsertJob, 6 tests
      bay_job_tests.cpp                  suite BayJob, 5 tests: readiness and transitions
      agv_charge_job_tests.cpp           suite AgvChargeJob, 5 tests
      clean_garage_job_tests.cpp         suite CleanGarageJob, 4 tests
    utils/                               tests of scheduler/utils.hpp, and of the support's own parsing
      base_state_validation_tests.cpp    suite ValidateBaseState, 4 tests
      empty_tray_count_tests.cpp         suite CountEmptyTrays, 1 test
      bay_rebalancing_tests.cpp          suite BayRebalancing, 8 tests: classification, split, transitions
      scenario_yaml_tests.cpp            suite ScenarioYaml, 8 tests: the YAML::convert decoders
  scenarios/                             60 initial-state files, 58 scenario files and a README
```

92 tests in 19 binaries. Each test file is one gtest suite, named after the file, and one binary,
named after the file too (`build/scheduler/retrieve_job_tests`). `CMakeLists.txt` builds the eight
support sources once, as the static library `${PROJECT_NAME}_test_support` (public: the
`test/include` directory, the scheduler library, yaml-cpp and `GTest::gtest`; private: the define
`SCHEDULER_SCENARIO_DIR`, the absolute path of `test/scenarios` in the source tree), then lists the
test files in `scheduler_tests` and one `foreach` adds each binary with
`volley_add_gtest(<name> test/src/<file>.cpp TIMEOUT 240 LINK_LIBRARIES ${PROJECT_NAME}_test_support)`.
The tests read and write the files in the source tree, never in `build/` or `install/`, so a
recording lands where git sees it and an authored file is read from where it is edited; the README
says why in one sentence. Message types are written out (`interfaces::msg::SchedulerJob`, with
`#include <interfaces/msg/scheduler_job.hpp>`), not through the `*Msg` aliases of the
`*_msgs.hpp` headers.

### The support library: `scenarios/`

Seven headers, each one responsibility, all in `volley::scheduler::test::scenarios`:

| header | responsibility | public names |
| --- | --- | --- |
| `yaml.hpp` | how the files spell the scheduler's types | `Request`; `ExpectKeys`; `YAML::convert<T>::decode` for `interfaces::msg::GaragePose`, `SchedulerJob`, `ActionNode`, `volley::SchedulerParams` and `Request` |
| `file.hpp` | where the running test's file is, and its authored part | `Scenario {path, initial, params, request}`; `PlanPath`, `StagePath`; `Load` (checks the file's `test:` key) and `Read` (does not); `ExpectOwnTest`; `AuthoredText` |
| `request.hpp` | the authored request as the scheduler receives it | `BuildRequest(scenario, now)`: base state, job GUIDs from 1001 up, registration time, request id 1000 |
| `recording.hpp` | the recorded part: message to document, compare, rewrite | `FlowScalarSequences`, `SpellOutFieldNames`, `Compact`, `MessageYaml<T>`, `Emit`, `ExpectSameDocument`, `ExpectRecorded` |
| `shared_scheduler.hpp` | what every test of a binary shares | `kNow` (the ROS epoch); `SharedScheduler(layout_path, params)` |
| `plan.hpp` | a plan scenario, planned and compared | `Run {scenario, scheduler, request, response}`; `Plan(suffix)`; `ExpectDeterministic()` |
| `stage.hpp` | a stage scenario: the DAG before and after | `Dag(ctx)`; `Stage(stage, suffix)`; `ExpectStage(stage, dag_before, ctx, suffix)` |

A plan test calls `scenarios::Plan()` (with a suffix when one test has several scenarios,
`scenarios::Plan("to_insert")`): it finds the file from gtest's current test info,
`plan/<suite in snake case>/<Name>[.<suffix>].yaml`, checks that its `test` key names the running
test, loads the initial state, takes the shared scheduler for the file's layout and parameters,
builds the request, plans once and compares the canonical response with the file's recorded
`output`, or rewrites the recorded part when `RECORD_REFERENCE_OUTPUT` is set. It returns a `Run`
with the scenario, the scheduler, the request and the response, for the test's own assertions.
Each job binary ends with `TEST(<Suite>, Deterministic) { scenarios::ExpectDeterministic(); }`,
which plans every scenario file of the suite's folder twice and expects the same canonical
response: planning must be deterministic, and the recordings rely on it.

A stage test calls `scenarios::Stage("tray_assignment")` for its initial state, builds its
`ScheduleContext` and event DAG in code, takes `scenarios::Dag(*ctx)`, runs the stage and calls
`scenarios::ExpectStage("tray_assignment", dag_before, *ctx)`, which compares `input.dag` and
`output.dag` with the file under `task_planning/<stage>/`. The DAGs are compared the same way: the
events' `ToString()` texts, sorted and numbered, the edges as positions in that list, emitted to
text and compared line by line with the file's `input` and `output` nodes.

The files' types are decoded through `YAML::convert` specialisations (`yaml.hpp`), yaml-cpp's
customisation point, the same design as `std::formatter<T>` for `std::format`: `node.as<T>()`.
The keys are `constexpr std::string_view` constants in `yaml.cpp`'s anonymous namespace, each used
once for the read and once in its map's key table (`kPoseKeys`, `kJobKeys`, `kCommandKeys`,
`kParamsKeys`, `kRequestKeys`; the top-level `kScenarioKeys` sit the same way in `file.cpp`).
`ExpectKeys` checks a map against its table; a decode throws `std::runtime_error` with the reason
(unknown key, unknown job type, bad GUID) and `Read` catches and rethrows with the file's path in
front. `utils/scenario_yaml_tests.cpp` covers the decoders.

#### How the comparison works

Nothing is written to disk when a test compares; only recording writes. In `scenarios::Plan`:

1. The response comes back from `Scheduler::Plan` as a message in memory. `CanonicalResponse`
   (`plan.cpp`) copies it, replaces the GUIDs and sorts the jobs (below), then `MessageYaml`
   (`recording.hpp`) turns the copy into a `YAML::Node` in memory: `to_yaml` prints the message as
   YAML text, yaml-cpp parses that text, and two passes over the node put scalar sequences on one
   line and spell out the acronym field names. `Compact` then reduces the node to what differs
   from the message defaults (below).
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

Recording (`RECORD_REFERENCE_OUTPUT` set) is the only disk write: `AuthoredText` reads the file up
to its first `input:` or `output:` line, that text is kept byte for byte, the whole new text
(authored part plus `Emit(recorded)`) is built first, and only then is the file opened and
rewritten, since opening truncates it and `Emit` can throw. The canonical response: action-node
GUIDs come from a process-wide counter (`CreateActionGuid` in `utils.cpp`), so each is replaced by
the node's position, followed everywhere the GUID was copied; `scheduled_jobs` are sorted by job
GUID; message fields named by an acronym are spelled out (`vexen` to `ev_chargers`,
`vecs_command` to `ev_charger_command`, `vrcs` to `vertical_conveyors`, and so on; the
initial-state loader maps the two list names back). `Compact` (`recording.cpp`) then walks the
node: every GUID map (`bytes: [...]`, recognised by `IsGuid`) becomes one scalar through
`GuidScalar` (its value when only the last four bytes are set, else the 8-4-4-4-12 form through
`std::to_string(interfaces::msg::Guid)` of common_ros, the one the initial-state files use);
every field that `IsDefault` (zero, empty, `false`, an empty sequence, or a sub-message whose every
field is a default) is removed; and a map of at most two scalars, a pose, is set to flow style so
it prints on one line. The rule a reader needs is one sentence: an absent field holds its default.
An action node therefore carries only the command it is about, `parents` only when it has some,
and `lift` only when raised. The comparison runs on the compacted form of both sides, so it is as
complete as a comparison of the messages: a field that changes from its default to a value appears
as an added line in the diff, and a field that changes to its default as a removed one. A DAG is
recorded as its events' `ToString()`, sorted and numbered, with the edges as positions, since the
events have no stable id; it is small and is not compacted.

Guards around the files: `ExpectKeys` refuses a key outside the known set at every level of the
authored part (a mistyped `tray: 2` would otherwise read as the field's default); `ExpectOwnTest`
checks the `test:` key of every file that is compared with or recorded, the second-stage files of a
tray test included, so a file of another test is neither compared nor overwritten; recording never
creates a file (the authored part must exist) and fails when the write fails. `IsDefault` treats a
quoted scalar as a string, default only when empty, so a note of "0" or "false" is kept.

### `initial_states.hpp` and `agv_commands.hpp`

`initial_states::Load("275_sunrise_b/car_at_p2066")` returns an `InitialState`: the layout's file
path (through `GetLayoutPathByName`, the layout being the folder of the name) and the
`DiscreteGarageState` parsed from the file. A missing file, an unknown layout or an invalid state
throws, which fails the test with the message. `IsAgvLiftRaised(command)` and
`IsAgvLiftLowered(command)` (`agv_commands.hpp`) read an AGV command's lift flags, before and
after, for the job tests that inspect lifts.

### `src/stages/`

The stage tests. A typical one (`TrayAssignment.FillsBlankDestination`, the first test):

1. `const auto garage = scenarios::Stage("tray_assignment").initial;`: the layout and the state from
   the scenario's initial-state file.
2. `const auto scheduler = scenarios::SharedScheduler(garage.layout_path, params);`: the one
   scheduler of the binary for that layout and parameters.
3. `ScheduleContext ctx(request_id, garage.state, scenarios::kNow)`, then
   `ctx->events.AddEvent(tray_move)` with hand-built `TrayMove` / `AgvMove` events: the DAG a job
   expansion would have produced, written by hand so the test can start exactly at the stage it
   wants. Events are the scheduler's own objects, which is why they stay in code rather than in the
   file.
4. `scheduler->DoTrayAssignments(ctx)` or `scheduler->DoAgvAssignments(ctx)`: the stage under
   test, called directly (both are public, `const` methods of `Scheduler`).
5. Assertions on `ctx->events`, and the `scenarios::Dag` / `scenarios::ExpectStage` pair around
   step 4.

What the files cover: `tray_assignment_tests.cpp` (4 recorded under `task_planning/tray_assignment/`,
plus one that runs tray and AGV assignment in a row), `agv_assignment_tests.cpp` (7, recorded under
`task_planning/agv_assignment/`, with two more from the tray file), `assignment_cost_tests.cpp` (the
cost functions used by AGV assignment: pure arithmetic, so no scenario file; they load an initial
state directly), `sanity_check_tests.cpp` (`SanityCheckEvents` on 5675_pecos_combined: a move into a
disabled node, the same move twice, a move with no path) and `scheduler_state_tests.cpp` (the
readiness-ratio service, which builds its own scheduler because it mutates it; the
last-entity-event bookkeeping; the continuous to discrete schedule conversion). The stage scenarios
run around bay B2068 of 275_sunrise_b (door W2069, waypoints W2070 and W2064, stalls P2075, P2066,
P2067, P2077; `MovesOneBlocker` puts tray 2 on P2066, the one stall on tray 1's critical path from
P2067 to the bay) and, for the blockers, in the block of stalls east of the lane: three columns
(P2116 to P2119, P2132 to P2135, P2147 to P2150) hanging south of the lane waypoints W2115, W2131
and W2146, with the waypoint column W2100 to W2103 on the block's west side; the stalls connect to
their four neighbours. `ResolvesManyBlockersThenAssignsAgvs` puts the root tray in the south-east
corner P2150 with every stall on its way out occupied, so the critical path leaves along the south
row and two trays (P2135, P2119) must move first. `ResolvesBlockerChainRecursively` closes the block
off from the rest of the garage with `disabled_nodes` so that the chain has nowhere else to go.
The tests carry no narration of their inputs: the scenario file's `description` and the viewer
hold the story, and the comments that remain explain the code (the transitive reduction, the
apply loop, the recursion).

### `src/jobs/`

One file per job type, one test per situation, all through `Scheduler::Plan()`, which is what the
planner node calls. A test is its assertions:

```cpp
TEST(AgvChargeJob, SkipsDisabledChargers) {
  const auto run = scenarios::Plan();
  EXPECT_TRUE(run.response.success) << run.response.message;
  ASSERT_EQ(1u, run.response.scheduled_jobs.size());
  const auto& last_node = run.response.schedule.nodes.back();
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

The 41 scenario tests walk the job types: `MOVE_AGV` and `MOVE_TRAY` (one with a base schedule
that reserves an AGV), `REPARK_TRAY` (plain, through a blocked row of stalls, unplugging a charger;
from or to a ready, unavailable or charging EV charger), `RETRIEVE` (from a stall, a disabled node,
a charger; with a bay transition, back to back, with a clean-garage job; the two blocking-tray
fallbacks), `CHARGE_PAYLOAD`, `INSERT` (with a clean-garage job; from both bays of pecos, tray
straight or reversed), `READY_FOR_RETRIEVE`, `READY_FOR_INSERT` and `TRANSITION_BAY` (unknown bay,
wrong command, both directions, disabled bay), `CHARGE_AGV` (nearest charger, from inside a bay, two
AGVs, disabled chargers), `CLEAN_GARAGE`; the eight `Deterministic` tests, one per suite folder
(`ReparkTrayJob` and `RetrieveJob` span two binaries each; the test is in the main one), make up
the rest. Most run around bay B2068 of 275_sunrise_b; the bay and AGV-charger scenarios on
`5675_pecos_combined`; the EV-charger scenarios on `38_gramercy`, the only current site with EV
chargers (E21, E23, E25). Gramercy's bay is the car lift BL26 on floor 1, so its retrieves go
through the lift: VRC commands around the AGV commands, and the AGV hops from the lift node L2 to
BL26 without a command of its own, which `ExpectRetrieveThroughLift` in
`retrieve_job_charger_tests.cpp` allows for. The retrieval-heading rule (below) does apply on
gramercy, where stalls and lift share heading 90: a reparked car whose payload is reciprocal to the
tray is lowered at the reciprocal heading, so the repark assertions accept it. The two blocking-tray
fallbacks (`RetrieveJob.AdvancesRootTray`, `ParksBlockerOnCriticalPath`) are the one use of the
synthetic tiny_lot left: they need a lot that is full with nowhere to go. The assertion blocks carry
no labels that restate them; the comments left say why (the retrieval-heading rule may turn the
car around, a base-schedule command reserves its nodes).

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

### `src/utils/`

Tests of `scheduler/utils.hpp`, the scheduler's helpers, rewritten from the old `utils_tests.cpp`,
plus the tests of the support's own parsing. `base_state_validation_tests.cpp` checks
`ValidateBaseState` against 275_sunrise_b: a consistent state passes, duplicate tray ids, a car
that does not fit its stall and an AGV on a node the layout does not have fail (the states come
from `initial_states/`; the duplicate ids are set on the message, since the state loader refuses
them). `empty_tray_count_tests.cpp` builds a state event by event and counts the empty, enabled
trays as payloads, trays and nodes are added or disabled. `bay_rebalancing_tests.cpp` covers the
bay classification table, the classification of a whole state, the desired insert / retrieve split
for a range of ratios (a table of cases), the transitions that split requires, and three
end-to-end cases (a ratio of one, a disabled bay, a bay in flight); its states are built in code
with a small `MakeState({bays}, {trays})` helper, since they are abstract (bays 1 to 4, no layout)
rather than a garage. `scenario_yaml_tests.cpp` (suite `ScenarioYaml`) decodes a pose, a job with
defaults and with every field, a base-schedule command, the parameters and a request through the
`YAML::convert` specialisations, and checks that an unknown key in any map, an unknown job type and
a bad GUID are refused.

### Conventions

The test code follows `src/agvhito/src/sm`: the file's own header first, then the `<...>` includes
of other packages in one sorted block, then the `"..."` includes of this package
(`"scheduler/scheduler.hpp"`, `"scheduler/test/..."`); file-local constants and helpers in an
anonymous namespace, constants `k`-prefixed; `const` on every local that is not reassigned, by
reference when it only reads; `_or` suffixes for optional and expected values, `_it` for iterators;
`///` documentation comments with `@p` and `@return` on every declaration in a header and on
helpers, short, saying why; `[[nodiscard]]` on functions whose result is the point; `std::format`
for messages; early returns with `if(!x_or.has_value())`; a comment only where it explains the why,
never a label that restates the assertion under it; `EXPECT_TRUE` rather than `EXPECT_EQ(x, true)`.
The request `note` field, which the old tests filled with "hello", is left empty.

### `scenarios/`, the data

`initial_states/<layout>/<name>.yaml`: 60 files in four layout folders (`275_sunrise_b` 32,
`5675_pecos_combined` 15, `38_gramercy` 11, `tiny_lot` 2), named after what stands in the garage, not
after a test, so that scenarios starting from the same state share one file. `plan/<suite>/<Name>.yaml`:
45 plan scenarios in eight suite folders. `task_planning/<stage>/<Name>.yaml`: 4 tray-assignment and 9
AGV-assignment scenarios. Every file sits two folders below `scenarios/`, which keeps VS Code's
SchemaStore from applying the Crowdsec scenario schema (its pattern is `**/scenarios/*/*.yaml`).
The README there explains both formats, the vocabulary, the layouts to use and avoid, how to build,
run and record, where the support lives, and the viewer. `tools/view_scheduler_tests` (an
executable script without extension; `poe scheduler-test-viewer` runs it; dependency group
`scheduler-dev`) and the package `tools/plan_viewer/` draw the scenarios: the garage to scale, the
initial state with the states of bays, EV chargers and the car lift, and one smooth path per AGV
or tray through the nodes its moves visit, in its own shade, kept to the right of its direction of
travel so that paths stay apart; hovering a step lights the stretch of path it covers; the input
event DAG shows while the solution is off, the output graph with it on.

## How a test run flows, from CMake to the comparison

Paths are relative to `src/planner/scheduler/` unless they start with `src/`. The sections follow
one run in the order things happen, naming the file and the function at each step, so that the
sequence can be followed in an editor.

### From CMake to a running binary

The test targets are declared in `CMakeLists.txt`, inside `if(BUILD_TESTING)`. `volley_package()`
has already found every `test_depend` of `package.xml` (`ament_auto_find_test_dependencies`,
`ament_cmake_gtest` among them). The block calls `ament_find_gtest()`, which runs
`find_package(GTest)` and so defines the imported target `GTest::gtest`, then builds the eight
support sources once: `add_library(${PROJECT_NAME}_test_support STATIC test/src/initial_states.cpp
test/src/scenarios/file.cpp ... yaml.cpp)`, with `test/include` as public include directory, the
scheduler library, yaml-cpp and `GTest::gtest` as public link libraries (the target carries gtest's
include directories), and the private define `SCHEDULER_SCENARIO_DIR="<source tree>/test/scenarios"`,
the one place that says where the files are. The `set(scheduler_tests ...)` list names the nineteen
test files, and a `foreach(test ${scheduler_tests})` loop adds each as
`volley_add_gtest(<name> test/src/<entry>.cpp TIMEOUT 240 LINK_LIBRARIES ${PROJECT_NAME}_test_support)`;
the includes and the scheduler library reach every test through the support library.

`volley_add_gtest()`, in `src/infrastructure/volley_cmake/cmake/volley_add_gtest.cmake`, parses
those arguments and calls `ament_add_gtest(<name> <sources> TIMEOUT 240)`, which creates the
executable `build/scheduler/<name>`, links `gtest` and `gtest_main`, and registers the executable
with CTest under its name; the wrapper then links the support library.

`poe build-pkg scheduler` runs `colcon build --packages-up-to scheduler`: the library, then the
nineteen executables. No scenario file is read at build time; the define bakes in where they are.
`poe test-pkg scheduler` runs `colcon test`, which runs CTest, which runs each executable with
`--gtest_output=xml:build/scheduler/test_results/scheduler/<name>.gtest.xml`, and
`colcon test-result --verbose` reads those files and prints the summary. One executable can be run
alone, as in `build/scheduler/retrieve_job_tests --gtest_filter='RetrieveJob.FromStall'`.

### Inside a binary, before the first test

Before `main`, during static initialisation, every `TEST(Suite, Name)` in the test file expands
(gtest's `TEST` macro, `gtest/gtest.h`) to a class `Suite_Name_Test` whose `TestBody()` is the
test's body, plus a static object whose constructor calls
`testing::internal::MakeAndRegisterTestInfo`, so the tests register themselves in file order with
their suite and name. In the same phase `yaml.cpp` builds its static table `kJobTypes` (job type
name to `SchedulerJob::TYPE_*`) and the `kFieldNames` tables of `recording.cpp` and
`initial_states.cpp` exist as constants.

`main` is gtest's, in `gtest_main.cc` (the first log line reads "Running main() from
./googletest/src/gtest_main.cc"). It calls `testing::InitGoogleTest(&argc, argv)`, which parses the
`--gtest_*` flags, then `RUN_ALL_TESTS()`, which runs every registered test in order in this one
process. There is no gtest environment: the planner's logging is quieted by `SharedScheduler` the
first time a binary builds a scheduler (below). One process for all tests is why the action-node
GUIDs differ with the tests that ran before (`CreateActionGuid` in `src/utils.cpp` draws them from
a process-wide counter), and why the recorded part replaces them by positions.

### One plan test, `RetrieveJob.FromStall` in `test/src/jobs/retrieve_job_tests.cpp`

The test body starts with `const auto run = scenarios::Plan();`. Nothing in that call says which
file to read, and that is the point: the file is found from the test's own identity. gtest keeps
the test it is running in `testing::UnitTest::GetInstance()->current_test_info()`, with the suite
name and the test name that the `TEST` macro registered; `TestName()` in `file.cpp` joins them as
`RetrieveJob.FromStall`. `PlanPath(suffix)` turns the suite into snake case (`SnakeCase`,
`RetrieveJob` to `retrieve_job`) and the test name into a file name (`FileName`, which appends
`.<suffix>` when one is given), and returns
`<SCHEDULER_SCENARIO_DIR>/plan/retrieve_job/FromStall.yaml`. The default empty suffix is the
common case, one scenario per test; a test that plans several scenarios names them, as
`scenarios::Plan("second")` for `FromStall.second.yaml`. So the file is the test's name, and the
`test:` key inside the file names the test back: `Load` refuses a file whose `test:` is not the
running test, which catches a file saved under the wrong name or a test renamed without its file.
The convention is what lets a test consist of the call and its assertions, with no path in the
source, and it is also why a test name cannot repeat within a suite (gtest forbids that anyway).

`Load(path)` is `ExpectOwnTest` followed by `Read(path)`. `Read` parses the whole file with
`YAML::LoadFile`, refuses a key outside `kScenarioKeys` (`ExpectKeys`), and fills the `Scenario`:
`path`, `initial` through `initial_states::Load(doc["initial_state"])`, `params` through
`doc["scheduler"].as<SchedulerParams>()` when present, and `request` through
`doc["request"].as<Request>()` when present, each decode checking its own keys; any exception on
the way is rethrown with the file's path in front. `initial_states::Load` (`initial_states.cpp`)
builds `<SCHEDULER_SCENARIO_DIR>/initial_states/275_sunrise_b/car_at_p2066_bay_ready_to_retrieve.yaml`,
parses it, renames `ev_chargers` to `vexen` and `vertical_conveyors` to `vrcs` (its `kFieldNames`
table) so that the message parser recognises them, resolves the layout through `LayoutPath`
(`GetLayoutPathByName` in `src/config/site_config/src/paths.cpp`, which searches the `layouts/`
folder for the file whose `name` key matches), and parses the state with
`DiscreteGarageState::Set(YAML::Node)` in `src/common_ros/src/discrete_garage_state.cpp`, which
reads each list, fills the defaults (lift false, tray 0, not disabled, hash) and refuses a
duplicate id. The request's decode (`yaml.cpp`) turns each entry of `jobs` into a
`SchedulerJob` with `type` through `kJobTypes`, `type_name` the same word, `STATE_UNPLANNED`,
`note`, `agv_id`, `bay_id`, `tray_id`, `payload` through `ParseGuid`
(`src/common_ros/src/ros_utils.cpp`), `destination` through `as<GaragePose>()` (which uses
`ConstructGaragePose`, `src/common_ros/src/pose_utils.cpp`) and `allow_reciprocal`, and each entry
of `base_schedule` into an `ActionNode` of type `TYPE_AGV_COMMAND` with the AGV and the two poses.

Back in `Plan`, `SharedScheduler(layout_path, params)` (`shared_scheduler.cpp`) hands out the
scheduler. It is built once per process for each layout and parameter set and shared by every test
of the binary, because its construction is what the tests' time went into: `Scheduler::Scheduler`
in `src/scheduler.cpp` builds, in its member initialisers, the `Layout`
(`src/common_ros/src/layout.cpp`: nodes, edges, parking windows, bay prioritisation), the pose
graph and garage graph (`gg_`, `src/common_ros/src/garage_graph.cpp`) and the collision table
(`table_`, `src/common_ros/src/collision_geometry.cpp`), which is loaded from
`~/.cache/volley/<layout>_collision_table_<hash>.json` or computed and cached (the log line
"Loading collision table for layout ..."; a first run on a new layout takes minutes). The cached
table of 275_sunrise_b is 281 MB of JSON and parses in about 5 s here and 13 s on the CI runner;
with a scheduler per test that was 26 parses of it per run. Sharing is safe because every entry
point the tests use (`Plan`, `DoTrayAssignments`, `DoAgvAssignments`, `PlanMotions`,
`ResponseFromTrajectories`, `SanityCheckEvents`, the cost functions) is `const`. The cache key is
the layout path, the readiness ratio and the cost-audit flag, the scalar constructor inputs;
`motion_cost` is left out (no printable identity, never changed by a scenario). On the first cache
miss of the process a function-local static calls `QuietLogging()`, which puts the `scheduler`,
`garage_graph` and `pose_graph` loggers at WARN unless `SCHEDULER_TEST_LOG` is set, so the planner's
INFO narration (critical paths, blocking trays, every planned motion, the collision-table build)
stays out of the output and a failure shows the recorded diff; the one test that builds its own
scheduler (the readiness-ratio service) narrates. The body of the constructor then calls
`InitRetrievalHeadings()`, which caches per stall the heading a car should be parked at for the
fastest retrieve, where the stall allows it.

`BuildRequest(scenario, kNow)` (`request.cpp`) turns the decoded request into the `PlanRequest`
message: the request id is `MakeGuid(0, 1000)`, `base_state` is
`initial.state.GetDiscreteGarageStateMessage()`, the jobs are copied with a GUID numbered from 1001
up (above any node position, so that a recorded `job_id` cannot be read as a node's positional
GUID) and `time_registered = kNow`, and the base-schedule commands become `base_schedule.nodes`.

`run.response = run.scheduler->Plan(run.request, kNow)` is the code under test.
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
`PlanResponse` with `success`, `schedule.nodes` and `scheduled_jobs`.

The response is then put into the canonical form. `CanonicalResponse` (`plan.cpp`) copies it,
replaces each action node's `guid` by `MakeGuid(0, position + 1)` and follows the replacement into
`agv_command.id`, `vecs_command.command_id`, `vrc_command.command_id` and every job's
`bay_arrival_node_guid`, sorts `scheduled_jobs` by job GUID, and calls `MessageYaml`: `to_yaml`
(generated, under `build/interfaces/`) prints the message as text, `YAML::Load` parses it,
`FlowScalarSequences` puts scalar sequences on one line and `SpellOutFieldNames` renames the
acronym fields. `Compact` then turns GUIDs into scalars, drops every field that holds its default
and puts poses on one line.

`ExpectRecorded(path, {output: {response: ...}})` (`recording.cpp`) is the comparison itself. The
file must exist and its `test:` key must name the running test (`ExpectOwnTest`). Without
`RECORD_REFERENCE_OUTPUT` in the environment, `YAML::LoadFile(path)["output"]` is the expected
side and `ExpectSameDocument` compares it with the canonical response: both are emitted with
`Emit` (yaml-cpp's emitter into a string, then parsed and emitted once more so that fresh and
parsed empty collections print the same) and walked line by line with `std::getline`; a difference
is an `ADD_FAILURE()` naming the line and both texts. With the variable set, `AuthoredText` reads
the file up to its first `input:` or `output:` line, the new text is built as that text followed
by `Emit(recorded)`, the file is opened and rewritten, the write is checked, and "Recorded <path>"
is printed. `Plan` finally returns the `Run` (scenario, scheduler, request, response), and the test
body continues with its own assertions on `run.response`, `run.request` and `run.scheduler`:
`EXPECT_TRUE(run.response.success)`, the chain of AGV commands, the lift and the lower, the
`PROCESS_RETRIEVE` command. gtest records every failed `EXPECT_*` and stops the body at a failed
`ASSERT_*`.

### The determinism test of a suite

`TEST(RetrieveJob, Deterministic) { scenarios::ExpectDeterministic(); }` ends `retrieve_job_tests.cpp`.
`ExpectDeterministic` (`plan.cpp`) takes the folder of the running test's file
(`PlanPath().parent_path()`, `plan/retrieve_job/`), lists its `.yaml` files in sorted order and,
for each, reads the scenario with `Read` (no ownership check: the files belong to the suite's other
tests), takes the shared scheduler, builds the request and plans twice; the two canonical
responses, `planned` and `replanned`, go through `ExpectSameDocument` with the file's name in the
message. Only a deterministic scheduler can be recorded, and this is where that is checked, once
per suite, for every file of the suite, including those of the other binary when a suite spans two.
A scenario is therefore planned three times per run: once by its test, twice here; the schedulers
are shared, so the eight tests take 11 to 690 ms each.

### One stage test, `TrayAssignment.MovesOneBlocker` in `test/src/stages/tray_assignment_tests.cpp`

A stage test starts from a file too, through `scenarios::Stage("tray_assignment")`, which is
`Load(StagePath(stage, suffix))` with the path
`<SCHEDULER_SCENARIO_DIR>/task_planning/tray_assignment/MovesOneBlocker.yaml`: the folder is the
stage named in the call and the file name is again the test's name. `Load` runs as for a plan
scenario, except that the file has no `request`; the test takes `.initial` from it, the initial
state and its layout.

The test then builds by hand what a job expansion would have produced: the shared scheduler for
the layout, as above, a `ScheduleContext` (`include/scheduler/scheduler.hpp`) from `garage.state`
at `scenarios::kNow`, and a `TrayMove`
(`src/planner/planner_core/include/planner_core/schedule_events.hpp`) with `SetTrayId(1)` and
`SetDest(ConstructGaragePose(2068, 0))`, added with `ctx->events.AddEvent(tray_move)` to the event
DAG (`src/planner/planner_core/include/planner_core/event_dag.hpp`). Events are the scheduler's
own objects, which is why they stay in code rather than in the file.

`const auto dag_before_tray = scenarios::Dag(*ctx);` takes the picture of the DAG before the stage:
`Dag` (`stage.cpp`) names every vertex by its event's `ToString()` (`std::to_string(*event)`),
numbers repeated strings, sorts them, lists the edges of `ctx.events.GetBaseGraph()` as pairs of
positions in that list, and `ctx.first_tray_event` as tray id to position.
`scheduler->DoTrayAssignments(ctx)` is the stage under test; it fills blank destinations, resolves
blocking trays and adds their moves to the DAG. Here tray 2 at P2066 stands on the critical path,
so the stage adds its move to a free stall and an edge from it to the root move.

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
it reads `two plans of FromStall.yaml differ at line ...`, from the suite's `Deterministic` test. A
scenario file with a key the decoders do not know fails at load with
`<path>: unknown key 'tray' in a job`, before anything is planned.

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

The fix is the static library `${PROJECT_NAME}_test_support` (see the CMake walkthrough): the two files
are compiled once, so clang-tidy analyses them once. Measured with `volley-in-container tidy` on the
same diff, same machine:

| | Analyses | Wall time |
|---|---|---|
| Support files as sources of every binary | 57 | 822 s |
| Support files in `${PROJECT_NAME}_test_support` | 23 | 66 s |

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
| `test/scenarios/<stage>/.../<Name>.yaml` | authored: the test, the description, the initial state, the scheduler's parameters, the request; recorded: `output` (and `input.dag` for a stage) | `scenarios::Plan` / `ExpectStage` (through `Read`, `BuildRequest`, `ExpectRecorded`), to build and compare; the viewer, to draw and tabulate |

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
one is in use, zero headers and timestamps, two-line GUIDs. `Compact` in `test/src/scenarios/recording.cpp`
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

- The 45 plan scenarios (`test/src/jobs/`) go through `Scheduler::Plan` and compare
  the response message only: `success`, `message`, the schedule's action nodes with their
  `parents` indices, durations, AGV, bay, charger and conveyor commands, and the modified
  `scheduled_jobs`. That is the interface of the scheduler as the executor and the fleet see it.
  The `ScheduleContext` that `Plan` builds (the event DAG, `last_entity_event`,
  `first_tray_event`, the disabledness filters) is created and discarded inside `Plan`, and no
  test can see it without a change to the library, which this commit does not make. The
  trajectories of the motion planner are not recorded either; only the discrete commands and
  durations derived from them are.
- The 13 stage tests (`test/src/stages/tray_assignment_tests.cpp`, `agv_assignment_tests.cpp`)
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

### Why did the tests take ten minutes on CI, and what was done about it?

The first CI run of the PR spent 653 s in `colcon test` against 35 s on main, where the job has
taken 2 to 3.8 minutes for sixteen runs. Two causes, measured from the job log. 143 s was a
one-off: CI had no cached collision table for 275_sunrise_b and built it (103 s) and saved it
(40 s); the upload step put it in the S3 cache for every later run. The rest was the per-test
cost of constructing a `Scheduler`: the cached table of 275_sunrise_b is 281 MB of JSON (17
million `{"heading", "node_id"}` objects in four maps), parsed with nlohmann in about 5 s on a
workstation and 13 s on the `arc-test-runners` pods, which are about 2.5 times slower per test
than a workstation across every binary; 26 of the 56 constructions were on that layout. Planning
itself takes 10 to 20 ms per scenario. The old tests on main used tiny_lot, 576_eccles_half and
1355_fulton, whose tables are small.

The fix in the PR is `scenarios::SharedScheduler`: one scheduler per layout and parameter set per
binary (see the walkthrough). Measured locally on the whole package: 67 table loads became 27 (the
20 distinct combinations, plus the readiness-ratio service test, which changes its scheduler and
so owns one, and the layout-only tests), the per-binary gtest totals fell from 203 s to 92 s, and
`poe test-pkg scheduler` from 3 m 26 s to 1 m 36 s. What remains is mostly one sunrise parse per
binary; on the CI runner that should bring `colcon test` from about 8.5 minutes to roughly 4. The binaries still run one after
another, since colcon's parallelism is per package and ctest is given no job count; running them
in parallel is a CI change for later, to be weighed against the memory each parse takes. The size
of the table itself is a common_ros matter: `CollisionTable::SaveTable` and `LoadTable` in
`src/common_ros/src/collision_geometry.cpp` write the table as JSON with a key-named object per
pose, and a compact encoding (a pose as an integer or a pair, or CBOR through the same library)
would shrink the file several times and speed every consumer, the system tests and the scheduler
node's start-up on that site included. That is a ticket, not this PR.

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

## PR review feedback

Feedback on PR #1007, one item per round, with what was wrong and what changed.

### Greptile P2: AGV paths use stale positions (`tools/plan_viewer/paths.py`)

The comment: `StepDrawing.steps()` tracked each AGV apart from the trays it carries, so in
`AgvAssignment.ChainsThreeMovesAcrossTwoAgvs` AGV 1 carried tray 2 to W2064 while its cached
position stayed at W2069, and its next recorded move, 2064 to 2068, was drawn from 2069. Confirmed.
Three things made it so: the drawing walked the steps one agent at a time, so a tray's move could
never update its AGV; the cached position won over the step's own source, so even the AGV move
event's `Src: 2064` was ignored; and a `Step` built from a stage's `TRAY_MOVE` event dropped the
`Agv ID` the stage had assigned, so there was nothing to update with. Plan scenarios were not
affected: a schedule has no tray steps, and every AGV command names its source.

The change: `Step` gains `agv` (the AGV a stage assigned to a tray's move, or 0), which
`Reader.stage_steps` fills from `Event.agv`. `StepDrawing.steps` walks the steps once, in order,
collecting legs per agent; a step's source is its own `src` when it names one, else where the
earlier steps left the agent (a stage's tray move names only its destination); a tray move with an
AGV assigned also moves that AGV. Paths are still drawn agent by agent afterwards, in the same
order, so lane allocation and colours are unchanged; badges at a shared node now stack in step
order instead of agent order.

Verification: every leg and badge the viewer draws, for all 58 scenarios, recorded with the
committed package and with the changed one and diffed. The nine AGV-assignment scenarios change
as intended (legs start where the AGV was carried; lift and lower badges sit at that node). Two
Gramercy plan scenarios (`RetrieveJob.FromReadyCharger`, `RetrieveJob.WhileCharging`) change
too: the AGV's lower after the car-lift ride is now a `▼` at the upper-floor node 26 instead of a
`⇅` at node 2, because the step's own source now wins over the cached lower floor. The ride is the
conveyor step before it, which has no badge in either version, so the `⇅` glyph was labelling the
lower command; the new drawing is the truthful one. The full page builds (58 scenarios).

Amended into the viewer commit (the PR stays at two commits).

### Greptile P2: equipment states are missing (`tools/plan_viewer/reader.py`)

The comment: `node_states()` drops `ev_chargers` and `vertical_conveyors` from the initial state, so
`ChargePayloadJob.WithoutCharger`, which starts with all three chargers disabled, shows that neither
in the drawing nor in the initial-state table. Confirmed: the reader turned only `bays` (state and
disabled flag) and `disabled_nodes` into node states, and `NodeState` had no notion of what stands
at the node (a non-empty state meant "bay"). A charger's id is its parking node (`VecsReport.msg`:
`vecs_id`, "Parking node ID"), so it fits the same shape; a car lift (VRC) has an id of its own and
the layout's `vrcs:` list names its nodes and root node (`38_gramercy`: lift 1 on nodes 2 and 26,
root 2).

The change: `NodeState` gains `kind` (bay, charger, conveyor or node), `id` (the equipment's own id
when it is not the node's) and a `name` (customer bay, EV charger, car lift, node). `records.py`
gains `CHARGER_STATES` (from `VecsReport.msg`) and `CONVEYOR_STATES` (from `VrcState.msg`), the
vocabularies already used as comments in the initial-state files. `Layout` reads the `vrcs` list as
lift id to root node. `Reader.node_states` adds the chargers (state and disabled flag) and the
conveyors (on their root node, "idle at floor 1" or "moving to floor 2"; disabled when the state is
`STATE_DISABLED`), then the disabled nodes as before. The scene labels every node with a state as
"<name> · <state> · disabled", chargers in the charger colour, and stacks labels that share a spot
(a lift's floors), and dashes every disabled node, bays and chargers included (before, a disabled
bay had only the word in its label). The initial-state table's kind column shows the name and the
id column the equipment's own id, so the car lift reads "car lift 1 L2 idle at floor 1".

Verification: node states and initial-state rows of all 58 scenarios recorded with the committed
package and the changed one. Eleven Gramercy scenarios gain charger rows (WithoutCharger: 21, 23
and 25 booting, disabled; the others one charger ready to charge, in hardware validation,
attaching adapter or charging) and three gain the car lift; bay rows only change their kind word
("bay" to "customer bay"). The page builds; mypy and black pass. The drawing was not inspected in
the browser this round (the artifacts folder is off limits to the browser tool).

Amended into the viewer commit.

### Greptile P2: input graphs never appear (`tools/plan_viewer/static/app.js`)

The comment: `show()` always gives the graph section the `output` class, the stylesheet hides that
class while the solution is off, and turning the solution on swaps the input graph for the output
graph, so the input event DAG of a stage scenario is never visible. Confirmed: `updateDag()` chose
the right SVG and hid the box when there was none, but the class was fixed in the markup, so the
rule `#details:not(.solution) .output { display: none; }` hid the box exactly when the input
graph was the one to show.

The change: the markup no longer carries the class; `updateDag()` toggles `output` on the box from
`state.solution`, next to where it picks the SVG. `updateDag()` runs on every path that can change
what the box shows (selecting a scenario, switching the theme, toggling the solution), so the class
always matches the graph. With the solution off, a stage scenario now shows "Event DAG (input)"
after its input tables, and a plan scenario (no input graph) shows no box; with the solution on,
the output graph as before. Not viewed in the browser this round, for the same reason as above.

Amended into the viewer commit.

### Greptile P2: unrecorded stages break the viewer (`tools/plan_viewer/tables.py`)

The comment: an authored-only stage scenario crashes the whole viewer, because `stage_tables()`
indexes `input` and `output` directly, and `step_graph()` does the same for `output`, while `dag()`
already returns an empty graph when the recording is missing. Confirmed: the reader was written to
tolerate a file that awaits its recording (`dag()` with an empty default, `response` through
`field()` with `{}`), and the viewer is the way to look at an authored file before recording it,
but those three places bypassed the helper, so one such file raised `KeyError` and nothing
rendered.

The change: the two event tables and the output graph's edges read through `self.dag(...)`. Three
lines. Verification: a stage file (`AgvAssignment.ChainsThreeMovesAcrossTwoAgvs`) and a plan file
(`RetrieveJob.FromStall`) loaded with their `input` and `output` removed (the YAML loader patched
in a check script, no file touched): both build their tables, steps (none), graphs (none) and
figure. The full page builds; mypy and black pass.

Amended into the viewer commit.

### Greptile P2: comments describe old test inputs (`test/stages/*_tests.cpp`)

The comment: the block comment in `TrayAssignment.ResolvesManyBlockersThenAssignsAgvs` says trays
14 and 12 at P2147 and P2148 block the route, but the re-posed state puts them at P2149 and P2134
and the recording moves trays 10 and 11; the comment in `AgvAssignment.ChainsThreeMovesAcrossTwoAgvs`
names the old tiny_lot destinations (5, 9, 1) and says AGV 1 takes moves 1 and 3, against the
test's own assertions (1 and 2). Confirmed, both. They are left over from before the re-pose and
the migration to 275_sunrise_b.

The decision (the user's): with the scenario files carrying a `description` and the viewer drawing
every input and output, narration inside the tests duplicates a story that is kept current
elsewhere and had already drifted twice. So the narrative comments go rather than get rewritten.
Removed from `agv_assignment_tests.cpp`: the "one tray move, two AGVs" preambles (2), the three-moves
comment, the "one AGV stuck, one disabled" comment, the two bay-transition preambles, and in
`OrdersLiftsAroundBayTransitions` the step-by-step narration ("moves tray 1 to bay 1", "using bay
ID 1", "moves tray 1 to node 8" with no code under it, "apply the new functionality"), leaving one
line at the bay's second transition. Removed from `tray_assignment_tests.cpp`: the nine-line block
with the lane sketch. Kept: comments that explain the code rather than the data (the transitive
reduction, the apply loop, the lift-after-transition check, the recursion test's why), and the
recursion test's "Root tray = the one on P(6)" became "tray 6, at P2117", which the state
`eight_empty_trays_no_agv` confirms (tray 6 at P2117, tray 8 at P2118, tray 11 at P2134). The
trailing value comments (`// Ready to Retrieve`, `// to RFI`) stay. 31 lines removed, 3 added.
Verification: package rebuilt (0 warnings), `tray_assignment_tests` 5/5 and `agv_assignment_tests`
7/7 pass; comments only, so no recording changed. Other test files were checked for the same kind
of drift: the job tests name real 275_sunrise_b nodes in their few comments, and the cost and
state tests' comments describe mechanics, so nothing else was touched.

Amended into the viewer commit (the user's "amend", so it sits there rather than in the
recording commit; moving it would take a fixup and an autosquash rebase).

### Greptile P2: comments repeat the viewer guide (`tools/plan_viewer/scene.py`, `__init__.py`, `paths.py`)

The comment: the module docstring of `scene.py` (15 lines) tours the drawing details, hover
behaviour and module boundaries; the same pattern in `__init__.py` (7 lines) and in
`StepDrawing.steps()` (9 lines); the team wants short comments that say why, with the tour in the
README. Valid, and the user agrees: the team prefers concise documentation in the code; these
notes may stay verbose.

The change: `scene.py` opens with three lines (what the figure is, which class draws it, where the
primitives and the steps live); `__init__.py` with the purpose and a two-line layer list;
`steps()` with what it draws and the one non-obvious rule (walked in order, tracking positions,
because a stage's tray move names only its destination and carries its AGV). 29 lines out, 9 in.
The other module docstrings (four to six lines, each on structure or a convention such as the
local frame of `shapes`) stay. black and mypy pass.

The removed tour, kept here since it is the one place the drawing's legend is written down:
drawn the way the study pack's facility figures are: a metre grid, faint parking stalls labelled
at a corner, blue bays with a door on the garage side, waypoint dots, small yellow charger cabinets
with a bolt, amber trays with rails, pink cars with windows, green AGVs with wheels, a lift plate
and a chevron at the front; goals are flags; steps are thick numbered arrows (moves, offset into
lanes when they share a segment), arcs (rotations) and badges (lifts and lowers). Paths: one per
agent through the nodes its moves visit, straight legs joined by rounded corners, drawn as one
line with an arrowhead at the end of every leg; the stretch a step covers is a hidden thicker
trace shown when the step is hovered; every leg keeps to the right of its direction of travel,
one lane further out for each earlier pass over the same segment in the same direction, by any
agent. The hover traces (outlines, ghosts) are still described in `canvas.py`'s docstring.

Amended into the viewer commit.

### Teammate (dambrosio), `pyproject.toml`: group name, include order, lock

Three nits on the dependency group for the viewer: move its `include-group` line up to the other
include groups (alphabetically); name the group `scheduler-dev`, as `vda5050-interfaces-dev` is
named, and drop the comment that said it is a developer group; regenerate `uv.lock` with poe.
Done: the include sits between `docs` and `vda5050-interfaces-dev` (the two existing includes are
not alphabetical with each other, `runtime` before `docs`, and were left as they are); the group is
`scheduler-dev` with no comment; `poe lock` in the container re-resolved 150 packages, and the
lock's diff is the two lines that name the group. The README's "Viewing" paragraph, the PR
description and the Jira note name the new group. Nothing else installs the group by name (the
devcontainer, CI and scripts were searched).

Amended into the viewer commit.

### Teammate (dambrosio), `CMakeLists.txt`: `${PROJECT_NAME}_test_support`

Suggestion: name the support library `${PROJECT_NAME}_test_support` and reference it that way,
so a package rename does not have to remember the `add_library` and `target_*` entries. Done in the
five places (`add_library`, `target_include_directories`, `target_link_libraries`,
`target_compile_definitions`, the `LINK_LIBRARIES` of `volley_add_gtest`); gersemi left the file
as written. The `scheduler_tests` list is a CMake variable, not a target, and keeps its name. Since
`${PROJECT_NAME}` expands to `scheduler`, the target is unchanged: the rebuild reconfigured and
ninja reported no work to do, which is the proof that the generated build is identical; one test
binary ran green on top. The CMake walkthrough in these notes now spells the library the same way.

Amended into the viewer commit.

### Teammate (dambrosio), comments: scrub the PR for verbose or restating comments

The comment, on the CMake block's two-line explanation: scrub the PR for comments that are
verbose or repeat the implementation; a comment only when necessary to explain the why; the CMake
one could read "Support utilities library used by every test binary for loading, reading and
recording scenario files." Taken as a rule (recorded in review_rules.md) and applied to the whole
PR, after a listing of every comment and docstring in the touched C++, Python and JavaScript.

What went, 22 files, 173 lines out and 43 in:

- Labels that restate the assertion under them, throughout the job, stage and utils tests:
  "Every job was planned", "Every node is an AGV command", "There is one lift and one lower",
  "Consecutive commands chain", "The one node is the bay command", "The job was not planned",
  "Success", "Should have one/two/three events", "Construct the scheduler", and the comments that
  restate the test's own name ("A disabled bay cannot be transitioned" in
  `CannotTransitionDisabledBay`, "Can't plan because Payload is on a disabled node" in
  `FromDisabledNode`, the "charger in a bad state" pair). The broken two-line "Assert that the
  charger command ... after the AGV gets / The tray was lowered" became one line each.
- Narrative preambles cut to their why: the tiny_lot explanation in `retrieve_job_tests.cpp` (six
  lines to three: the blocker has nowhere to go there, on 275_sunrise_b it always has a waypoint,
  closing the garage makes the planner cycle), the insert-from-bay preamble (five to three), the
  Gramercy lift preamble (four to two), the recursion test's two comments (one line each).
- The support library's `///` docs: the file header of `scenarios.hpp` (six lines to three, the
  path layout left to the README), `SharedScheduler` (four to two), `Plan` (six to four, the
  canonical form left to `Canonical` in the .cpp), `Dag` (three to two), `QuietLogging`,
  `IsDefault` and `Compact` in `scenarios.cpp` (each to two).
- The viewer's module docstrings of `canvas`, `page`, `reader` and `theme` (six or seven lines to
  three) and the `StepDrawing` class docstring (four to one; it duplicated `steps()`).
- The CMake comment, in the teammate's words.

What stayed, deliberately: comments that carry a fact the code does not show (the retrieval-heading
rule may turn the car around; an AGV command in the base schedule reserves its nodes; the
transitive reduction drops the direct edges; a test owns its scheduler because it mutates it;
`DiscreteGarageState::Set` refuses a duplicate id), the case labels of the table-style tests
(`bay_rebalancing`, `empty_tray_count`, `assignment_cost`: each names a condition the parameters
alone do not), the `///` one-liners on declarations, the viewer's one-line function docstrings and
field comments, and `app.js`'s why comments (plotly quirks). The README is untouched: it is the
place the tours were moved to.

Verification: clang-format and black in the container, every changed file ends with a newline,
package rebuilt, `test scheduler` 170 tests green (comments only, no recording changed).

Amended into the viewer commit.

### Teammate (dambrosio), `test/.clang-tidy`: no reference to another package

Nit: the comment pointed at `src/agvhito/test/.clang-tidy` as the precedent, a reference that goes
stale when that package moves or is renamed. The reference is gone and the comment, in the spirit
of the previous item, is two lines: the asserts the dataflow analysis cannot see, and why a throw
in a test is acceptable. The setting is unchanged.

Amended into the viewer commit.

### Teammate (dambrosio), namespaces: `volley::scheduler::test`

The comment, on `agv_commands.hpp` sitting in bare `volley`: a developer once stripped the
packages' namespaces, so `volley` holds everything, which invites collisions and longer names;
test code could live in `volley::scheduler::test`, and the predicates could carry names such as
`IsAgvLiftLowered` / `IsAgvLiftRaised`. The user agreed and asked for a design.

The design: everything under `test/` lives in `volley::scheduler::test`, the pattern
`src/agvhito/test` (`volley::agvhito::test`) and `src/core/yasminx/test` already use. The two
support modules keep their own level below it, `volley::scheduler::test::scenarios` and
`volley::scheduler::test::initial_states`, so the call sites keep reading `scenarios::Plan()` and
`initial_states::Load(...)`. The lift predicates sit directly in `volley::scheduler::test` as
`RaisesLift(command)` and `LowersLift(command)`: verbs about what the command does, which is what
the predicate tests (`src.lift` versus `dst.lift`), rather than a state. Every test file opens
`namespace volley::scheduler::test {`, so the library's names (`Scheduler`, `TrayMove`,
`AgvCommandMsg`) resolve through the enclosing `volley` and the support resolves unqualified. The
library itself stays in `volley`: moving it is a change to production code, out of this PR.

Two consequences handled: a local named `test` in `scenarios.cpp` (`ExpectOwnTest`) would have
shadowed the namespace inside it, so it is `owner` now; and the eighteen `using volley::TrayMove;`
lines in the stage tests, redundant since the tests were already inside `volley`, are gone. Local
variables named `scheduler` shadow the namespace `scheduler` inside their block, which is harmless
because nothing there qualifies with `scheduler::`. 24 files, 60 lines changed.

Verification: clang-format; rebuilt (20 objects compiled, 19 targets linked: the library and the
eighteen binaries); `test scheduler` 170 tests green; the clang-tidy hook on the lines changed
since main: 0 findings (the namespace rule is lower_case). The README says where the support and
the tests live.

Amended into the viewer commit, with the predicates renamed `IsAgvLiftRaised` /
`IsAgvLiftLowered` first (the user prefers the `Is` convention, which says the result is a bool).

### Teammate (dambrosio), message aliases: explicit types and includes

The comment, on `PlanRequestMsg` / `PlanResponseMsg` in `scenarios.hpp`: the `*_msgs.hpp` headers
(`scheduler_msgs.hpp`, `common_ros_msgs.hpp`) alias every message type, which hides where a type
comes from and pulls in nearly every interfaces header for two messages; the files should include
and name what they use. The user agreed: phase the aliases out of this PR's code, be explicit
about includes and types.

The change, test code only (the library's headers keep their aliases; changing them is production
code): every `XMsg` became `interfaces::msg::X` and every `XSrv` `interfaces::srv::X`, with
`#include <interfaces/msg/x.hpp>` (rosidl's snake case: `SetFloat32` is `set_float32.hpp`) added
to each file for the types it uses, placed by clang-format's include sorting. 23 distinct types,
208 uses, 20 files; `SchedulerJob` (56 uses) and `ActionNode` (42) are the bulk. The script that
did it checked that `src/interfaces/interfaces/{msg,srv}/<Name>.<kind>` exists for every name.
Fully qualified names rather than per-file `using` declarations, which would be aliases by another
route; the lines grow (296 added, 213 removed), which is the price the teammate's point accepts.
`package.xml` already has `<depend>interfaces</depend>`, so no new dependency.

Verification: clang-format, rebuilt, `test scheduler` 170 green, clang-tidy hook 0 findings.

Amended into the viewer commit.

### Teammate (dambrosio), `tools/view_scheduler_tests.py`: shebang, mode and extension

The comment: a file with a shebang is a binary; make it executable and drop the `.py`. Done:
`tools/view_scheduler_tests`, mode 755, usage line and README now `src/planner/scheduler/tools/
view_scheduler_tests --output ...` (no `uv run python` in front). Precedent in the repo both ways
(`.github/scripts/*` and `tools/clang-tidy-diff-hook` without extension; `tools/*.py` executable
with it); the teammate's convention is the former. The black and mypy hooks select files by
`types = ["python"]`, which `identify` resolves from the shebang for an extensionless file, so the
script stays formatted and type-checked; checked by running the hooks on it in the container, and
the script itself by path.

Amended into the viewer commit.

### Teammate (dambrosio), `uv run` and `from __future__ import annotations`

Two comments on the script. First: `uv run` creates a `.venv` in the workspace, while the team's
convention is the virtual environment the Dockerfile builds, so the usage should be the script's
path, and a poe task would simplify it. The usage line and the README had already moved to the
path in the previous item; now there is also a poe task, `poe scheduler-test-viewer` (kebab-case like
`build-pkg`, placed alphabetically after the `sccache-*` tasks), which the README names as the
short form, with the path and `--output` as the long form. Second: the devcontainer's Python is
3.14 (checked: 3.14.4), where annotations are deferred by the language, so
`from __future__ import annotations` is noise; removed from all fifteen Python files of the
viewer. Verification: the hooks on the changed files (black, mypy, markdownlint, the uv-lock
check) and `poe scheduler-test-viewer` in the container, which renders the 58 scenarios.

Amended into the viewer commit, the task renamed `scheduler-test-viewer` first (the user: it is a
viewer for the tests; a general one can take the short name later).

### Teammate (dambrosio), test includes: `<scheduler/test/scenarios.hpp>`

The comment, on `#include "scenarios.hpp"` in `test/jobs/agv_charge_job_tests.cpp`: a quoted
include reads as relative to the including file's folder, so it looked like `test/jobs/scenarios.hpp`;
either make it `../scenarios.hpp` or move the test headers to `test/include/scheduler/test/` and
add that include directory, so the includes become `<scheduler/test/scenarios.hpp>`. The user
chose the second (relative includes are confusing).

Done: `scenarios.hpp`, `initial_states.hpp` and `agv_commands.hpp` moved to
`test/include/scheduler/test/`; the support library's public include directory is `test/include`
instead of `test`; all 40 includes of the three headers (the tests, the two support sources and
`scenarios.hpp`'s own include of `initial_states.hpp`) are `<scheduler/test/...>`, which
clang-format sorts into the angle-bracket block. The include path mirrors the namespace
(`volley::scheduler::test`), and the library's own headers keep `<scheduler/scheduler.hpp>` from
`include/`. The README names the new paths. Verification: rebuilt, `test scheduler` 170 green,
hooks on the CMake file and the README green. The clang-tidy hook diffs main against HEAD, so
before the amend it looked for the headers at their old paths and errored; clang-tidy run directly
on the three moved headers finds compile flags for them (interpolated from the neighbouring
sources, as for the library's own headers under `include/`), and the hook is re-run after the
amend.
Amended into the viewer commit; the hook then ran on the moved headers: 0 findings.

### `test/src/` for the support sources, and quoted in-package includes

Two more, the first the user's own: with the headers under `test/include/`, the support sources
belong under `test/src/` for the same symmetry as the package's `include/` and `src/`. Done:
`test/src/scenarios.cpp` and `test/src/initial_states.cpp`, the `add_library` sources updated;
the test files themselves stay in `test/jobs`, `test/stages` and `test/utils`. The second, the
teammate's nit: includes of the package's own headers use quotes, angle brackets are for other
packages, as `src/agvhito` and `src/common_ros` do. Done in the test code: 59 includes,
`"scheduler/scheduler.hpp"` and `"scheduler/test/...hpp"`; clang-format puts the quoted block
first. The library's own sources mix the two styles (`src/scheduler.cpp` quotes, the headers use
brackets) and are left alone: production code. Verification: rebuilt, `test scheduler` 170 green;
the tidy hook after the amend, as before, since it diffs main against HEAD.

Then, the user: every C++ test source belongs under `test/src/` too, not only the support
library's. `test/jobs`, `test/stages` and `test/utils` moved to `test/src/`, the gtest loop in
`CMakeLists.txt` reads `test/src/${test}.cpp`, its comment and the README name the new paths; the
viewer's `locate_tests` searches `test/` recursively and needed no change. The layout is now
`test/include/scheduler/test/` (headers), `test/src/` (the two support sources and the three test
folders) and `test/scenarios/` (the data). Built, 170 green, amended, tidy after the amend.
Amended; tidy on the moved sources: 0 findings.

### Teammate (dambrosio), `initial_states.cpp`: why not `ament_index_cpp` for the scenario paths

The question: was it intentional not to resolve the scenario files through `ament_index_cpp`, so
that the test YAMLs need not be installed into the ROS share directory? Evaluation, no change
(the user likes the current solution): yes, intentional, for three reasons. (1) Recording writes
the files back in place (`RECORD_REFERENCE_OUTPUT=1` rewrites the recorded part), so the tests
must know the source path anyway; reading through share would give two paths for one data set,
or write into the install tree, which with symlink-install happens to reach the source and without
it does not. (2) A failure names the file to look at, and that must be the one git diffs and the
reviewer edits: the source file. (3) The share directory is for assets other packages consume;
115 files and 30,000 lines of test data have no consumer but these binaries, and installing them
is a step with no reader. Where ament_index belongs it is still used: the layouts come from
site_config's installed share through `GetLayoutPathByName` (common_ros), which is also where the
old tests' `ament_index_cpp` test_depend went (dropped in this PR because nothing in the tests
calls it directly any more). Precedent both ways: agvhito, cost_functions, common_ros and sim
install one or two test files into `share/<pkg>/test`; none of them writes test data back. The
cost: the binary bakes in an absolute source path, so it cannot run from a copied install tree
without the source tree, which is acceptable for tests that ctest runs in the workspace. The
define is the one place the path lives (`SCHEDULER_SCENARIO_DIR`, private to the support library).

The README's "Building, running and recording" section now opens with that why, in one sentence;
amended.

### Teammate (dambrosio), `InitialState::layout`: unused fields in the test structs

The comment: `InitialState::layout` is not used and can be derived from `layout_path`. The user:
rescan every struct under `test/` and remove what nothing reads. Every field of the three structs
was traced through the support and the tests:

| struct | field | readers | verdict |
| --- | --- | --- | --- |
| `InitialState` | `layout` | only `Load`, to build `layout_path` | removed; a temporary in `Load` |
| `InitialState` | `layout_path`, `state` | the tests and `Plan` | kept |
| `Scenario` | `description` | none (the viewer reads the file itself) | removed |
| `Scenario` | `initial_state` | only `Load`, to call `initial_states::Load` | removed; inlined |
| `Scenario` | `path`, `initial`, `params`, `request` | `BuildRequest`, `Plan`, the stage tests | kept |
| `Run` | `now` | only `Plan` itself; every test uses `scenarios::kNow` | removed; `Plan` uses `kNow` |
| `Run` | `scenario` | `Plan` itself; no test today | kept: the handle to the loaded initial state and path |
| `Run` | `scheduler`, `request`, `response` | the tests | kept |

`Run::scenario` is the one judgement call: nothing reads it today either, but it is the only way a
plan test can reach the initial state it ran from, which the stage tests do through `Stage().initial`;
dropping it would leave the plan tests without that. Flagged for the user. `rclcpp/time.hpp` stays
in the header for `kNow`. Verification: rebuilt, `test scheduler` 170 green; tidy after the amend.

Amended (with `Run::scenario` kept); tidy 0 findings.

### Teammate (dambrosio), `CMakeLists.txt`: gtest wiring

Two suggestions. `find_package(ament_cmake_gtest REQUIRED)` is redundant: `volley_package()` calls
`ament_auto_find_test_dependencies()` under `BUILD_TESTING`, which finds every `test_depend` of
`package.xml`, `ament_cmake_gtest` among them. Dropped. `ament_find_gtest()` stays: it is the call
that runs `find_package(GTest)`, which defines the imported target `GTest::gtest` (CMake's own
FindGTest), and `ament_add_gtest` inside `volley_add_gtest` runs only after the support library is
declared. With the support library linking `GTest::gtest` instead of `${GTEST_LIBRARIES}`, the
target carries its include directories, so `${GTEST_INCLUDE_DIRS}` leaves the include list. No
other package in the workspace links gtest into a library of its own, so there was no precedent
to match. Verification: gersemi, rebuilt, `test scheduler` 170 green.

Amended into the viewer commit.

### Teammate (dambrosio), `scenarios.hpp`: one responsibility per header

The comment: the header has file lookup, request decoding and YAML compare/record in one place;
split it into headers with a fixed responsibility each. The user agreed. The 550-line
`scenarios.cpp` and its header became a folder, `test/include/scheduler/test/scenarios/` with
`test/src/scenarios/`, one header and source per responsibility, all still in
`volley::scheduler::test::scenarios` so that the call sites (`scenarios::Plan()`,
`scenarios::Stage(...)`, `scenarios::ExpectStage`, `scenarios::Dag`, `scenarios::SharedScheduler`,
`scenarios::kNow`) read as before and only the includes change:

| header | responsibility | public names |
| --- | --- | --- |
| `file.hpp` | where the running test's file is, and its authored part | `Scenario`, `PlanPath`, `StagePath`, `Load`, `ExpectKeys`, `ExpectOwnTest`, `AuthoredText` |
| `request.hpp` | the authored request as a `PlanRequest` | `BuildRequest` |
| `recording.hpp` | the recorded part: message to document, compare, rewrite | `FlowScalarSequences`, `SpellOutFieldNames`, `Compact`, `MessageYaml<T>`, `Emit`, `ExpectSameDocument`, `ExpectRecorded` |
| `shared_scheduler.hpp` | what every test of a binary shares | `kNow`, `SharedScheduler` (the quiet-logging environment lives in its .cpp) |
| `plan.hpp` | a plan scenario, planned and compared | `Run`, `Plan` (`CanonicalResponse` internal) |
| `stage.hpp` | a stage scenario: the DAG before and after | `Dag`, `Stage`, `ExpectStage` |

Three helpers that were file-private are public now because two files need them: `ExpectKeys`
(file and request), `ExpectOwnTest` and `AuthoredText` (file and recording). `MessageYaml` is a
template, so it sits in `recording.hpp` and calls the two passes declared there; it finds
`to_yaml` by argument-dependent lookup. The quiet-logging environment stays a global in
`shared_scheduler.cpp`: every binary that plans calls `SharedScheduler`, so the linker keeps that
object file, as it kept `scenarios.o` before; the utils binaries never referenced it either way.

Each test includes what it uses, by a script that looked for the calls: the job tests `plan.hpp`
(and `agv_commands.hpp` where they inspect lifts); the stage tests `shared_scheduler.hpp` with
`stage.hpp` or `initial_states.hpp`; the utils tests are unchanged. The CMake sources list names
the six files; the README's scenario section lists the headers in one sentence.

Amended into the viewer commit; tidy on the new files: 0 findings.

### Teammate (dambrosio), `Plan()`: the determinism check as a test of its own

The comment: move the second planning run out of `Plan()` and make determinism an explicit test,
`TEST(RetrieveJob, Deterministic) {{ scenarios::ExpectDeterministic(); }}`. The user agreed, and
asked for better names than `first` and `second`.

Done: `Plan()` plans once and compares with the recording. `ExpectDeterministic()` (`plan.hpp`)
plans every scenario file of the running test's suite folder twice and expects the same canonical
response, named `planned` and `replanned`, with the file's name in the failure message. It reads
the files with a new `Read(path)` (`file.hpp`), which is `Load` without the ownership check, since
the files of a suite belong to the suite's tests, not to the determinism test. One
`TEST(<Suite>, Deterministic)` sits at the end of each of the eight job binaries that own a suite
folder (`ReparkTrayJob` and `RetrieveJob` span two binaries each; the test is in the main one, so
each folder is checked once). The cost: a scenario is now planned three times per run (once by its
test, twice by the determinism test) instead of twice; 178 tests instead of 170. The README's
recording paragraph says so.

Amended into the viewer commit; tidy 0 findings.

### Teammate (dambrosio), `ExpectRecorded`: build the text before opening the file

The suggestion: `Emit` can throw, so build the text before opening the `ofstream`, not to leave an
open file. Valid, and worse than stated: `std::ofstream out(path)` truncates the file on open, so
a throw in `Emit` after it would have left the scenario file empty, authored part included (the
part recording never creates). Now `const std::string text = authored + Emit(recorded);` comes
first and the stream opens after it, with a one-line comment on the why. The compare path ran green
(`move_job_tests`); the record path (`volley-in-container record-reference`, which rewrites tracked
files and so needs the user's approval) is to be run once to confirm byte-identical output.

Amended into the viewer commit on "amend commit" (no record run); tidy 0 findings.

### Teammate (dambrosio), YAML parsing: `YAML::convert` specializations with key tables

The suggestion: `YAML::convert` specializations with the key tables as constants in anonymous
namespaces, to shrink the file and remove the duplicated key strings, plus tests of the parsing.
The user: a pattern he has used before and meant to call out in the design.

Done, `scenarios/yaml.hpp` and `yaml.cpp`:

- `YAML::convert<T>::decode` for the five types the files spell: `interfaces::msg::GaragePose`
  (`node_id`, `heading`), `interfaces::msg::SchedulerJob` (a job), `interfaces::msg::ActionNode`
  (a base-schedule command: `agv_id`, `from`, `to`), `volley::SchedulerParams`
  (`bay_readiness_ratio`) and a new `scenarios::Request` (`jobs`, `base_schedule`), so the readers
  are `node.as<T>()`.
- The keys are `constexpr std::string_view` constants in `yaml.cpp`'s anonymous namespace, each
  used once for the read and once in its map's key table (`kPoseKeys`, `kJobKeys`, `kCommandKeys`,
  `kParamsKeys`, `kRequestKeys`); the top-level keys (`kScenarioKeys`) sit the same way in
  `file.cpp`. `ExpectKeys(map, allowed, what)` checks a map against its table and is public in
  `yaml.hpp`; a decode throws `std::runtime_error` with the reason (unknown key, unknown job type,
  bad GUID) and `Read` catches and rethrows with the file's path in front, so the message still
  names the file.
- `Scenario::request` is a decoded `Request` instead of a raw `YAML::Node` (explicit types, as the
  alias feedback asked); `BuildRequest` shrinks to the base state, the GUID numbering and the
  registration time. `kJobTypes` moved with the decoding.
- `utils/scenario_yaml_tests.cpp`, suite `ScenarioYaml`, eight tests: a pose; unknown keys
  rejected for all four maps; a job with defaults; a job with every field (payload GUID,
  destination, note, reciprocal); unknown job type and bad GUID rejected; a base-schedule command;
  the parameters; a request with jobs and base schedule, and an empty one. Registered in CMake.

Amended into the viewer commit. The tidy hook then flagged `decode`
(readability-identifier-naming wants CamelCase methods); `decode` is the name yaml-cpp looks up, so
the `YAML` namespace in `yaml.hpp` and `yaml.cpp` is wrapped in `NOLINTBEGIN/NOLINTEND` for that
check, with the reason on the line. The user's question on the pattern: it is yaml-cpp's
customisation point, the same design as `std::formatter<T>` for `std::format` and `std::hash<T>`
(a class template the library leaves open; the repo already specialises `convert` in `sim` and
`agvhito_tools`, and `std::formatter` in `yasminx`); an own `Decode<T>(node)` function template
would lose `as<std::vector<T>>()`, defaults and nested use, and function-template specialisations
cannot be partial. Answered, no change.

### Teammate (dambrosio), `SharedScheduler`: what the cache key is

The question: is the key unique on `cost_audit` too? Yes: the key is the layout path, the
`bay_readiness_ratio` and `cost_audit`, so two tests share a scheduler only when all three match.
What the tests actually vary is the layout and the ratio (0.0 in the files and 0.5 in five stage
tests); no test sets `cost_audit`, so that part of the key never splits the cache today. It is
there because it is a scalar constructor input, cheap to include, and a test that sets it would
otherwise get a scheduler built with the other value. `motion_cost`, the third parameter, is
left out: it is a tree of float structs without `operator==` or a printable identity, and no
scenario changes it. The comment at the key now says exactly that; before it said only that the
files set the ratio. Verification: rebuilt, `scenario_yaml_tests` green, tidy hook re-run.

Amended into the viewer commit.

### Teammate (dambrosio), `QuietLogging`: into `SharedScheduler` instead of a gtest environment

The suggestion: set the logger levels on the scheduler's construction instead of through a
`::testing::Environment`, which removes the class, the owning-memory NOLINT and the link-order
dependency. Assessment: valid. The environment was a global object in a static library's object
file, kept only because every planning binary happens to reference `SharedScheduler` in the same
file, an implicit link dependency that nothing in CMake expresses; and gtest's ownership of the
`new`ed environment needed the NOLINT. The quieting is needed exactly before the first scheduler
is built (the collision-table narration comes from the constructor), which is a point
`SharedScheduler` owns.

Done: `QuietLogging()` is a plain function in the anonymous namespace returning whether it quieted,
called through a function-local `static const bool` on the first cache miss, so it runs once per
process and before the first construction; the gtest include is gone from the file. One
consequence, accepted: `SchedulerState.SetBayReadinessRatioService` builds its own scheduler (it
mutates it) and runs first in its binary, so that one construction narrates at INFO again; it is
one test in one binary, and exposing the function to silence it would add back a public piece.
Verification: rebuilt, `test scheduler` 187 green; tidy first wanted the static constant named
`kQuiet` (done), then 0 findings. The whole run's log holds eight INFO lines, all from that one test
(collision table, initialisation, the three ratio requests); every other binary is silent.
Amended into the viewer commit.

### CI after the rebase: mypy "Duplicate module named `__main__`"

The user rebased onto main (`b26ea5d6` + `c3d19e72`) and pushed; the `pre-static-analysis / prek`
job failed in mypy: `tools/clang-tidy-diff-hook: error: Duplicate module named "__main__" (also at
"src/planner/scheduler/tools/view_scheduler_tests")`. Cause: CI runs the hooks with `--all-files`,
and mypy gives every extensionless script the module name `__main__`; with the viewer script
renamed without its `.py` (item 13) the tree has two such scripts outside the hook's exclusions
(`.github/scripts/*` are excluded, which is how those three never collided), and mypy refuses the
pair. Locally the hook had only ever run on the one file. Fix: `scripts_are_modules = true` in
`[tool.mypy]`, which names a script after its file (no comment: the user wants the setting bare,
the why lives here); then
`prek run mypy --all-files` in the container passes, and `mypy` on the two scripts directly reports
both checked. The rebase itself changed nothing in this area. Alternatives weighed, at the user's
asking: removing the `__main__` guard does nothing (mypy names an extensionless file `__main__`
from its path, not from the guard); restoring `.py` would avoid config but reverse the teammate's
nit; the flag on the prek hook or an exclude only move the change; a `plan_viewer/__main__.py`
entry point would drop the script altogether. The setting stays.

### Greptile P2 (second pass): viewer colours disappear (`theme.py`)

The comment, twice: `Palette.css()` keeps a field when `f.type == "str"`, but without postponed
annotations a dataclass field's `type` is the class `str`, so every colour is skipped and both
palettes emit only `--move`; compare with `str`. Confirmed in the container before the fix: both
palettes produced a 17-character string, the one `--move` token. A regression of item 15, the
removal of `from __future__ import annotations`: under postponed annotations the field types were
the string `"str"` and the test passed; the page was rebuilt after that item but its colours were
not inspected, since the artifacts folder is closed to the browser tool. Now `f.type is str`; each
palette emits its 27 tokens again (26 colours and `--move`), black and mypy pass, the page rebuilds. The only site in
the package that compares an annotation.

### Greptile P2 (second pass): cars face the wrong way; a description names the wrong waypoint

Two more, assessed before applying, since Greptile is right about half the time.

Cars: valid. `DiscretePayloadState.reciprocal_to_tray` says the car faces the opposite way to its
tray; 26 initial states set it (`FromStall`'s among them), the viewer's state loader defaulted the
field and nothing read it, and the car's windows were drawn along the tray's heading, so a
reversed car looked aligned, which is exactly the thing a repark or retrieve reviewer would look at.
Done: `Asset.reciprocal` (named after the message flag, not `reversed`, a builtin), filled by the
reader; the scene draws the windows on a frame turned by 180 degrees when set, the hover says
"reversed" and the initial-state table's payload cell reads "1 (reversed)". Checked
numerically in the container: for `FromStall`'s tray the windshield's centre now lies on the
tray's rear side; black, mypy and the page build pass.

Description: valid. `CleanGarageJob.AgvInTheWay` said AGV 2 drives from W2069 over W2070 to P2075;
the recording goes 2069, 2074, 2075 (W2074 is a waypoint). Fixed. Since the descriptions were
written by hand from the recordings, every plan and stage description was then swept for node
names that appear neither in the file's recorded part, its request nor its initial state: four
hits, of which the other three hold (C16 "free" in `TwoAgvsDistinctChargers` and B2068 in
`FillsBlankDestination` describe the layout, which the files do not list; W2103 in
`ResolvesManyBlockersThenAssignsAgvs` names the critical path, which the stage file does not
record). One wrong waypoint in 58 descriptions.





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
