# 08 — Verification: regression parity and benchmarks

This tab says how to prove the refactor in the [Issue & proposal](#doc-proposal) tab changed nothing, and how to measure it. It starts with what the tests cover today (read from `main` at `a468657f`, 2026-11-05), then describes the parity comparison as it is built, the scenario recordings, and the benchmark method, which is still a proposal.

## Two separate goals

**Behavioural equivalence** asks whether the extracted default solver makes the same decisions and adds the same constraints as the old `Scheduler` method. **Performance benchmarking** asks whether run time or resource use changes for comparable inputs. A passing GoogleTest on its own is neither: it shows the code still meets that test's assertions, not that output is identical or equally fast. The recorded part of each scenario file ([section 4](#vr-compare-meaning-not-pointers-or-guids)) answers the first question when it is compared; nothing yet answers the second.

## What the existing tests cover

The `scheduler` package has **99 `TEST` cases in 19 files**, one gtest suite and one binary per file. PR \#1007 (SW2-1126) replaced the four old test files (72 active tests) with them and moved every planning test onto a **scenario file**; PR \#1018 (SW2-1135) added five tests, turned one advanced test into a scenario and removed one test whose function is gone ([Where the old tests went](#vr-where-the-old-tests-went)). [Figure 1](#vr-fig-35_test_entry_points) places each test under the earliest pipeline stage it calls directly.

![Where the existing tests enter the scheduler](figures/35_test_entry_points.svg)

**Test entry points.** Columns follow the `Plan()` pipeline from [section 10](#bg-one-plan-call-step-by-step). A card's colour stripe shows its file; "+n" means the test also calls n later stages directly.

| Folder (under `test/src/`)   | Files (tests)                                                                                                                                                                                                                  | Style                                                                                                                                                                                                                                                                                |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `jobs/`: 10 files, 54 tests  | `move_job` (5), `repark_tray_job` (6), `repark_tray_job_charger` (5), `retrieve_job` (10), `retrieve_job_charger` (3), `charge_payload_job` (4), `insert_job` (6), `bay_job` (5), `agv_charge_job` (6), `clean_garage_job` (4) | Full `Scheduler::Plan` per job type: `scenarios::Plan()` loads the test's plan scenario, plans it and checks the file; the test then asserts job states, commands and poses. Each suite has a `Deterministic` test that plans every scenario of the suite twice. CMake timeout 240 s |
| `stages/`: 5 files, 22 tests | `tray_assignment` (5), `agv_assignment` (7), `assignment_cost` (3), `sanity_check` (3), `scheduler_state` (4)                                                                                                                  | A hand-built `PlanContext` on an initial-state file; one stage or helper called directly. The tray and AGV assignment tests record the event DAG before and after the stage                                                                                                          |
| `utils/`: 4 files, 23 tests  | `bay_rebalancing` (10), `base_state_validation` (4), `empty_tray_count` (1), `scenario_yaml` (8)                                                                                                                               | Pure functions (`ClassifyBay(s)`, `CalculateDesiredBaySplit`, `ComputeBayRebalancingActions`, `ValidateBaseState`, `CountEmptyTrays`) and the scenario files' YAML decoding                                                                                                          |

By stage: 54 tests enter through `Plan()` (eight of them the `Deterministic` checks), 5 through tray assignment (one calls `ResolveBlockingTrays` directly, two continue into AGV assignment and motion planning), 7 through AGV assignment, 3 through the AGV cost helpers (`ComputeTravelDuration`, `ComputeAgvPickupDuration`, `ComputeAgvAssignmentCost`), 3 through `ValidateEventSequence`, 4 through scheduler state (the readiness-fraction service twice, `ChainAfterLastEntityEvent`, and `BuildActionGraph` on a hand-built continuous state), 15 through utilities, and 8 test the scenario loader itself.

**Scenario files.** The inputs live in `test/scenarios/` (its `README.md` is the reference): 50 plan scenarios in `plan/<suite>/<Name>[.<suffix>].yaml`, 13 stage scenarios in `task_planning/{tray_assignment,agv_assignment}/`, and 63 initial states in `initial_states/<layout>/<name>.yaml`, shared between scenarios. A scenario names its test, describes it in a few sentences, names an initial state and holds the request (plan scenarios) or nothing more (stage scenarios, whose test builds the event DAG in code); below that comes the recorded part. The 63 scenario files run on three sites and one synthetic lot: `275_sunrise_b` (30), `5675_pecos_combined` (16: bays, AGV chargers, the sanity checks), `38_gramercy` (14: the EV-charger scenarios; its bay is the car lift BL26 on floor 1, so its retrieves ride the VRC) and `tiny_lot` (3: the two blocking-tray fallbacks, which need a full lot with nowhere to go, and one two-tray move). `576_eccles*`, `1355_fulton` and `triple_pick_lot` are no longer used by these tests. The tool `tools/view_scheduler_tests` (`poe scheduler-test-viewer`) renders every scenario into one HTML page: the garage drawn to scale with the initial state and the goals, the input as tables and the event DAG, and on request the planned moves and the action graph.

**Other packages.** Three more packages test code that a plan call runs, without scenario files:

| Package                    | Tests          | What they cover                                                                                                                                                                                                                                         |
|----------------------------|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `planner_core`             | 22 in 2 files  | `EventDagTests` (10: topological order, `RemoveRedundantEdges`, a cycle rejected, an unknown vertex throws) and `ScheduleEventTests` (12: `ApplyTo` for each event type, VRC teleports)                                                                 |
| `motion_planner`           | 69 in 13 files | Blocking-tray and open-space search (14), static filters (10), safe intervals and SIPP (14), CHUGG (4), AGV hiding (6), trajectories, intervals and coalescing (13), paths and continuous state (8); on `tiny_lot`, `triple_pick_lot` and a test layout |
| `scheduler_advanced_tests` | 3 in 3 files   | Full `Plan()` regressions: `CrossFloorPathing.RetrieveBehindThreeTrays` and `VrcInsertionCycle.CrossFloorRetrieve` on `550_w21st`, `ChokepointPathing.CleanGarage` on `175_e82nd`. Garage states are inline YAML; no recordings                         |

### How a stage-level test is built

Read this before changing a stage; a solver's tests will look the same, with the solver call swapped in.

``` cpp
// test/src/stages/agv_assignment_tests.cpp — TEST(AgvAssignment, ChainsThreeMovesAcrossTwoAgvs) (abridged);
// namespace volley::scheduler::test; all names are test locals
const auto garage = scenarios::Stage("agv_assignment").initial;      // task_planning/agv_assignment/ChainsThreeMovesAcrossTwoAgvs.yaml
                                                                      // names 275_sunrise_b/two_agvs_three_empty_trays
const auto scheduler = scenarios::SharedScheduler(garage.layout_path, SchedulerParams {});  // shared_ptr<const Scheduler>, one per layout per binary
interfaces::msg::Guid request_id = MakeGuid(0, 0xDEADBEEF);
const auto ctx = std::make_shared<PlanContext>(request_id, garage.state, scenarios::kNow);  // PlanContextSPtr

const auto tray_move_1 = std::make_shared<TrayMove>(0u);            // job_index 0
tray_move_1->SetTrayId(2);
interfaces::msg::GaragePose end_pose;                                 // node_id + heading
end_pose.node_id = 2064;
end_pose.heading = 90;
tray_move_1->SetDest(end_pose);
ctx->event_dag.AddEvent(tray_move_1);
// ...tray_move_2 (tray 1 to P2067) and tray_move_3 (tray 2 into B2068), chained with AddDependency

const auto dag_before_agv = scenarios::Dag(*ctx);                     // canonical DAG: the recording's input
const auto agv_assignment = scheduler->AssignAgvs(ctx);               // stdx::Result; mutates ctx->event_dag and the TrayMoves
scenarios::ExpectStage("agv_assignment", dag_before_agv, *ctx);       // checks the file; compares output.dag when asked
EXPECT_TRUE(agv_assignment) << agv_assignment.error();
EXPECT_EQ(tray_move_1->GetAgvId().value(), 1);                        // read results back through the same shared_ptrs
EXPECT_EQ(tray_move_2->GetAgvId().value(), 1);
EXPECT_EQ(tray_move_3->GetAgvId().value(), 8);                        // hand-over to a second AGV
EXPECT_FALSE(ctx->event_dag.HasDependency(tray_move_1, tray_move_2)); // direct edge removed by RemoveRedundantEdges()
```

Note the last line: the test checks that the transitive reduction at the end of `AssignAgvs` *removed* an edge the test added itself, which is exactly the kind of detail a parity check must preserve. The test keeps its own `shared_ptr` to each event, so it can inspect the event after the algorithm has changed it. `scenarios::Dag` turns the context's DAG into the canonical document of [section 4](#vr-compare-meaning-not-pointers-or-guids); `ExpectStage` checks that the file exists, names this test and holds a recorded part, and compares that part when `SCHEDULER_CHECK_RECORDINGS` is set. A job test is shorter still: `const auto run = scenarios::Plan();` builds the request from the file, plans it on the shared scheduler and checks the recorded response, and the test asserts on `run.response`.

### Tests most relevant to the two solvers

The tests below exercise tray assignment and AGV assignment, the two stages that the refactor moves into separate solvers. For each test the table gives the layout and what it asserts; several still assert only that the stage succeeded, but every one with a scenario file also records the stage's output DAG or the whole response, which the comparison checks (gap 1 below).

| Test                                                                           | Layout          | What it asserts                                                                                                                                                                             |
|--------------------------------------------------------------------------------|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `TrayAssignment.FillsBlankDestination`                                         | `275_sunrise_b` | One `TrayMove` with a tray but no destination; asserts only success                                                                                                                         |
| `TrayAssignment.ResolvesManyBlockersThenAssignsAgvs`                           | `275_sunrise_b` | Tray 13 out of a full block into B2068; tray and AGV assignment, motion planning and the action graph all succeed; both stages recorded                                                     |
| `TrayAssignment.MovesOneBlocker`                                               | `275_sunrise_b` | Tray to bay with one blocker; asserts only success (the recording holds the added move and its edge)                                                                                        |
| `TrayAssignment.ResolvesBlockerChainRecursively`                               | `275_sunrise_b` | Calls `ResolveBlockingTrays` directly; ≥ 2 required moves, every move has a destination, all destinations distinct. No scenario file                                                        |
| `TrayAssignment.ThenAgvAssignment`                                             | `275_sunrise_b` | Both stages; topological order exists; `PlanMotions` succeeds                                                                                                                               |
| `AgvAssignment.SkipsDisabledAgv`                                               | `275_sunrise_b` | Closer AGV is disabled; AGV 1 is assigned                                                                                                                                                   |
| `AgvAssignment.FailsWhenDisabledAgvBlocksPath`                                 | `275_sunrise_b` | Disabled AGV blocks the other's path; assignment fails, no AGV set                                                                                                                          |
| `AgvAssignment.ChainsThreeMovesAcrossTwoAgvs`                                  | `275_sunrise_b` | Three chained tray moves get AGVs 1, 1 and 8; the original tray-to-tray edges are gone after the reduction because longer chains imply them; applying all events reaches the expected state |
| `AgvAssignment.FailsWithNoAvailableAgv`                                        | `275_sunrise_b` | No feasible AGV; fails, no edge added, still 2 vertices                                                                                                                                     |
| `AgvAssignment.FailsWhenBayTransitionTrapsAgv` / `UsesAgvFreedByBayTransition` | `275_sunrise_b` | A `BayTransition` root traps or frees the AGV; edge bay → tray move present                                                                                                                 |
| `AgvAssignment.OrdersLiftsAroundBayTransitions`                                | `275_sunrise_b` | The bay transition has the AGV lift move as an out-edge                                                                                                                                     |
| `CleanGarageJob.UnstashesTrayFromWaypoint`                                     | `275_sunrise_b` | Through `Plan()`: one job, `STATE_EXECUTING`, a lifted move from W2070 to a stall exists                                                                                                    |
| `RetrieveJob.AdvancesRootTray` / `ParksBlockerOnCriticalPath`                  | `tiny_lot`      | Through `Plan()`: the two blocking-tray fallbacks (advance the root tray one step; park the blocker on the critical path) succeed; one job, executing                                       |
| `MoveJob.TwoTrayMovesWithAgvUnderOneTray`                                      | `tiny_lot`      | Through `Plan()`: two tray moves that must share and order both AGVs; both jobs executing, each with actions                                                                                |

### Where the old tests went

Older notes, tickets and this pack's figures name the tests as they were before PR \#1007. Each old test became the test on its right, with its inline YAML moved to an initial-state file and, except the four noted, its fixture moved from `tiny_lot`, `triple_pick_lot`, `1355_fulton` or `576_eccles_half` to a current site.

| Old test (file)                                                                                                                                                                                         | Today                                                                                                                                                                                                                                                  |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `TrayAssignmentTest`, `TrayAssignmentTestComplexDag`, `UnblockingTrayMoveTest`, `ResolveBlockingTraysRecursivelyUnblocksChain`, `TrayAndAgvAssignments` (`scheduler_tests.cpp`)                         | `TrayAssignment.` `FillsBlankDestination`, `ResolvesManyBlockersThenAssignsAgvs`, `MovesOneBlocker`, `ResolvesBlockerChainRecursively`, `ThenAgvAssignment`                                                                                            |
| `MiAmigaEsSuAmiga`, `AmigaSaysNo`, `AmigaStash`, `NoAmigas`, `AmigaBaySos`, `AmigaBaySo`, `TrayLiftBayTransitionDependencyTest`                                                                         | `AgvAssignment.` `SkipsDisabledAgv`, `FailsWhenDisabledAgvBlocksPath`, `ChainsThreeMovesAcrossTwoAgvs`, `FailsWithNoAvailableAgv`, `FailsWhenBayTransitionTrapsAgv`, `UsesAgvFreedByBayTransition`, `OrdersLiftsAroundBayTransitions`                  |
| `GetJustMovingCost`, `GetAgvCurrentPoseToTrayMoveCost`, `GetAgvToTrayAssignmentCost`; `GetAgvOccupiedDuration`                                                                                          | `AssignmentCost.` `JustMoving`, `AgvCurrentPoseToTrayMove`, `AgvToTrayAssignment`; the last was removed in PR \#1018 with the function, which always returned 0                                                                                        |
| `SanityCheckEventsDisabledDest`, `SanityCheckEventsCantApply`, `SanityCheckEventsCantFindPathThruOdp`                                                                                                   | `SanityCheck.` `RejectsDisabledDestination`, `RejectsMoveThatCannotApply`, `RejectsMoveWithoutPath`                                                                                                                                                    |
| `SetBayReadinessRatioService`, `UpdateLastEntityEvent`, `ContinuousStateToSchedule`                                                                                                                     | `SchedulerState.` `SetBayReadinessRatioService`, `ChainAfterLastEntityEvent`, `ContinuousStateToSchedule`                                                                                                                                              |
| `CleanGarageAgvInTheWay`, `CleanGarageDontMoveAgvsUnderTrays`, `CleanGarageUnstashesTrayFromWaypoint`                                                                                                   | `CleanGarageJob.` `AgvInTheWay`, `DoesNotMoveAgvsUnderTrays`, `UnstashesTrayFromWaypoint`                                                                                                                                                              |
| `DoubleRetrieveDodgeAgv` (commented out, with the only file in `test/garage_states/`)                                                                                                                   | Removed in PR \#1007 with that folder; no scenario replaces it (`RetrieveJob.BackToBack` plans two retrieves in one call)                                                                                                                              |
| `MoveAgvJob`, `MoveAgvJobAlreadyAtDest` (`scheduler_jobs_tests.cpp`)                                                                                                                                    | `MoveJob.` `AgvToBay`, `AgvAlreadyAtDestination`                                                                                                                                                                                                       |
| `ReparkTrayJob`, `ReparkTrayJobAdvanceToWaypoint`, `ReparkUnplugVecs`, `ReparkUnplugVecsMoveAgvFirst`; `ReparkTrayJobGoodVecs`, `…BadVecs`, `…ChargingVecs`, `…BadVecsDest`, `…GoodVecsAtDest`          | `ReparkTrayJob.` `ToBay`, `AdvancesBlockersToWaypoint`, `UnplugsCharger`, `UnplugsChargerAgvMovesFirst`; `FromReadyCharger`, `FromUnavailableCharger`, `WhileCharging`, `ToUnavailableCharger`, `ToReadyCharger` (`repark_tray_job_charger_tests.cpp`) |
| `RetrieveJob`, `RetrieveJobDisabledNode`, `RetrieveJobBayTransition`, `BackToBackRetrieve`, `WeirdFultonRetrieve`; `RetrieveJobGoodVecs`, `…BadVecs`, `…ChargingVecs`                                   | `RetrieveJob.` `FromStall`, `FromDisabledNode`, `WithBayTransition`, `BackToBack`, `WithCleanGarage`; `FromReadyCharger`, `FromUnavailableCharger`, `WhileCharging` (`retrieve_job_charger_tests.cpp`)                                                 |
| `ChargePayloadJob`, `ChargePayloadJobNoVecs`, `ChargePayloadJobWrongPayload`                                                                                                                            | `ChargePayloadJob.` `FromBayToCharger`, `WithoutCharger`, `WrongPayload`                                                                                                                                                                               |
| `InsertJob`; `FultonInsertBay{1,2}TrayHeading{0,180}` (`scheduler_insert_orientation_tests.cpp`)                                                                                                        | `InsertJob.` `WithCleanGarage`; `FromBay7TrayHeading90`, `FromBay7TrayReversed`, `FromBay21TrayHeading90`, `FromBay21TrayReversed` (Pecos bays 7 and 21 instead of Fulton bays 1 and 2)                                                                |
| `ReadyForRetrieveJob`, `TransitionBay`, `CantTransitionDisabledBay`                                                                                                                                     | `BayJob.` `ReadyForRetrieve`, `Transitions`, `CannotTransitionDisabledBay`                                                                                                                                                                             |
| `AgvChargeJob`, `AgvChargeJobMVP454`, `AgvChargeJobInBay`, `DontGoToDisabledChargeNode`                                                                                                                 | `AgvChargeJob.` `ToNearestCharger`, `TwoAgvsDistinctChargers`, `FromInsideBay`, `SkipsDisabledChargers`                                                                                                                                                |
| `ValidDGS`, `DuplicateTrays`, `PayloadDoesntFit`, `WhatNodeIsThat`, `CountEmptyTrays` (`utils_tests.cpp`)                                                                                               | `ValidateBaseState.` `AcceptsAConsistentState`, `RejectsDuplicateTrayIds`, `RejectsOversizedPayload`, `RejectsAgvOnUnknownNode`; `CountEmptyTrays.CountsEmptyEnabledTrays`                                                                             |
| `ClassifyBay`, `DisabledMeansNotUsable`, `ClassifyBaysViaFullState`, `CalculateDesiredBaySplit`, `ComputeBayRebalancingActions`, `TrivialBayBalancing`, `OneDisabledBay`, `BayInFlightIsNotRecommanded` | `BayRebalancing.*` (10 tests, with the bay classifications renamed in PR \#1018)                                                                                                                                                                       |

New since the old files: `BayJob.ReadyForInsert`, `MoveJob.BaseScheduleReservesAgvAndNodes` and the two `tiny_lot` fallbacks (PR \#1007); a `Deterministic` test per job suite and the eight `ScenarioYaml` tests of the loader; and in PR \#1018 `RetrieveJob.FailedJobReportedOnce`, `RetrieveJob.FailedJobLeavesNoEvents`, `ReparkTrayJob.ReturnsTrayAfterEarlierRepark`, `AgvChargeJob.AlreadyOnCharger` and `SchedulerState.RejectsNonFiniteBayReadinessRatio`, which guard the bugs that PR fixed. PR \#1018 also deleted the four Eccles files of `scheduler_advanced_tests` (six tests on `576_eccles`, `576_eccles_half` and `1355_fulton`); the one test among them on `tiny_lot`, `OverlappingAgvAssignmentFailureTest2`, became `MoveJob.TwoTrayMovesWithAgvUnderOneTray`, and the three remaining files were renamed for what they guard.

### Gaps

The tests still leave several weaknesses that limit how far they can serve as evidence that the refactor preserves behaviour. Each item below names one and, where relevant, what the parity work must add to cover it.

1.  **Assertions are mostly success flags, and the recordings are checked only on request.** Four of the five tray tests do not assert which tray moved where. Their scenario files record it, but CI runs without `SCHEDULER_CHECK_RECORDINGS`, so a behaviour change passes CI unless someone turns the comparison on ([section 4](#vr-compare-meaning-not-pointers-or-guids)). Every refactor pull request must run it.
2.  **No direct tests** for `OrderAgvMovesAfterBlockingAgvs`, `OrderAllTransitionsAroundAgvLifts` or `InsertVrcActionsIntoDag`. They run inside larger tests (`AgvAssignment.OrdersLiftsAroundBayTransitions`, the `38_gramercy` retrieves through the car lift, and the advanced tests `ChokepointPathing`, `CrossFloorPathing` and `VrcInsertionCycle`), so a regression there shows up as a downstream failure or a recording difference.
3.  **A plan scenario records the response only.** The event DAG that a plan call builds is not recorded, so a change in tray or AGV assignment that happens to give the same action graph passes. The stage scenarios record the DAG, but only for the 13 hand-built cases.
4.  **Some decisions depend on hash-map order.** `ExpectDeterministic` shows that a plan repeats within one process, and PR \#1018 made `MotionScheduleOrder` break ties on every field. Choices that iterate an `std::unordered_map` are still fixed only for a given standard library; the chokepoint test checks an invariant instead of one plan for that reason. A recording may therefore move with a toolchain upgrade.
5.  **No benchmark code.** Nothing times the solvers, and no Google Benchmark target exists in any `CMakeLists.txt` of the planner.

Two gaps listed here before PR \#1018 are closed: the commented-out `DoubleRetrieveDodgeAgv` was deleted with its fixture, and the layout-name branch for `576_eccles` (`UseEvChargeHeading`) was removed with the Eccles tests.

## Proposed benchmark dataset (requirements, not completed scenarios)

The parent ticket requires **at least 10 scenarios based on real customer site layouts for each solver**. The matrix below is coverage to aim for, **not** a claim that the cases exist as benchmarks. The scenario files already run on three real sites (`275_sunrise_b`, `5675_pecos_combined`, `38_gramercy`); `tiny_lot` is a test layout and does not count, and `576_eccles*` and `1355_fulton` are decommissioned and not to be used. Each row still needs an approved fixture with recorded provenance.

| ID  | Tray solver characteristic       | AGV solver characteristic                 | Existing test to start from                                                                                              |
|-----|----------------------------------|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| 01  | Low occupancy, short move        | One nearby feasible AGV                   | `TrayAssignment.FillsBlankDestination`, `AgvAssignment.SkipsDisabledAgv`                                                 |
| 02  | Occupied destination, repark     | Several candidates, distance tie          | `ReparkTrayJob.ToBay`                                                                                                    |
| 03  | Single blocking tray             | Candidate with a raised lift              | `TrayAssignment.MovesOneBlocker`                                                                                         |
| 04  | Recursive chain of blockers      | Closer candidate disabled                 | `TrayAssignment.ResolvesBlockerChainRecursively`                                                                         |
| 05  | Narrow aisle with cycles         | AGV trapped in a bay                      | `TrayAssignment.ResolvesManyBlockersThenAssignsAgvs`, `AgvAssignment.FailsWhenBayTransitionTrapsAgv`                     |
| 06  | High occupancy, no repark spot   | AGV route unreachable                     | `RetrieveJob.AdvancesRootTray`, `RetrieveJob.ParksBlockerOnCriticalPath`, `AgvAssignment.FailsWhenDisabledAgvBlocksPath` |
| 07  | Waypoint-stash fallback (tier 2) | Non-tray root gates a tray root           | `CleanGarageJob.UnstashesTrayFromWaypoint` (the reverse step), `AgvAssignment.UsesAgvFreedByBayTransition`               |
| 08  | Different payload footprints     | Node-arrival ordering between AGVs        | `CleanGarageJob.AgvInTheWay`                                                                                             |
| 09  | Several jobs, independent moves  | Bottleneck matching across many roots     | `RetrieveJob.BackToBack`, `MoveJob.TwoTrayMovesWithAgvUnderOneTray`                                                      |
| 10  | One tray moved several times     | Same AGV across a chain, then a hand-over | `AgvAssignment.ChainsThreeMovesAcrossTwoAgvs`                                                                            |

A scenario file already records the layout (through its initial state's folder), the initial `DiscreteGarageState`, the request (`interfaces::msg::PlanRequest` jobs and base schedule) or the hand-built DAG, and the result. A benchmark fixture also needs the layout file hash, the code SHA of its recording, and whether it is anonymized; the scenario files do not record these.

## Compare meaning, not pointers or GUIDs

Events have no stable id across runs: a `shared_ptr` address changes every run, and GUIDs come from a static counter. A comparison therefore needs a canonical description. The recorded part of each scenario file is that description, written by the test support in `test/src/scenarios/` (`stage.cpp`, `plan.cpp`, `recording.cpp`):

- **An event DAG** (stage scenarios: `input.dag` before the stage, `output.dag` after it) has `events`, one string per event, `ScheduleEvent::ToString()` (task index, type, tray or entity, destination, AGV) plus `#n` to number identical strings, sorted; `edges`, `[from, to]` positions in that list, sorted; and `first_event_by_tray`, tray id to position.
- **A response** (plan scenarios: `output.response`) is the `PlanResponse` as `interfaces::msg::to_yaml` prints it, with each action GUID replaced by `MakeGuid(0, position + 1)` (also in the charger and conveyor command ids and in `bay_arrival_node_guid`), `scheduled_jobs` sorted by job GUID, and the document compacted: fields at their default are left out, a GUID is one scalar, short maps go on one line. Action nodes stay in schedule order. The success flag, job states and error messages are part of the response, so they are compared as text.

The comparison runs on the emitted text of both sides and fails with the first differing line. It runs when `SCHEDULER_CHECK_RECORDINGS=1` is set; `RECORD_REFERENCE_OUTPUT=1` rewrites the recorded part instead. It is off by default because a change to what the planner is configured with (a cost, a speed, a site layout) moves every recording, while the assertions must hold across such a change.

Compared with the description this tab proposed before PR \#1007, the recordings leave out three things: reachability between every pair of events, the final `DiscreteGarageState` after applying all events, and, for plan scenarios, the event DAG (gap 3). Edges are compared as the stage left them: `AssignAgvs` ends with `RemoveRedundantEdges()`, so its output is reduced (the transitive reduction is unique for a DAG, [section 2.4](#ad-transitive-reduction)); `AssignTrays` does not reduce, so its output edges are compared as added. Action graphs are compared in schedule order rather than matched by content ([section 6.7](#ad-what-this-means-for-the-refactor)), which relies on `MotionScheduleOrder` being a total order.

For each scenario k\in\\1,\ldots,K\\, where K\in\mathbb N is the number of scenario files (63 today), let e_k\in\\0,1\\ be 1 only when its recorded part matches. The pass proportion p\in\[0,1\] is:

p=\frac{1}{K}\sum\_{k=1}^{K}e_k.

The release gate is p=1, with every deviation investigated: a test run with `SCHEDULER_CHECK_RECORDINGS=1` that passes is p=1. If a stage is non-deterministic, define the accepted equivalence classes **before** measuring, not after a difference appears; `TEST(<Suite>, Deterministic)` in each job binary plans every scenario of its suite twice and expects the same response, whether or not the comparison is on.

For the solver extraction no second harness is needed: the solver goes behind `AssignTrays` or `AssignAgvs`, and the stage and plan scenarios are run with the comparison on. The old path does not have to run in the same test, because its output is stored. Two checks remain **proposed**:

``` cpp
// PROPOSED — test/src/stages/tray_solver_tests.cpp (sketch)
// ctx_a, ctx_b : PlanContextSPtr built independently from the same scenario and the same events
//                (events cloned, not shared — otherwise both calls see the other's changes)
// tray_solver  : tray_assignment::DefaultSolver, built from the scheduler's GarageServices
// dag_before   : scenarios::Dag(*ctx_a), taken before the first Solve
const auto first  = tray_solver.Solve({ctx_a->initial_state, ctx_a->event_dag});   // stdx::Expected<Result>
const auto second = tray_solver.Solve({ctx_b->initial_state, ctx_b->event_dag});
ASSERT_EQ(first.has_value(), second.has_value());
EXPECT_EQ(*first, *second);                                    // Solve is deterministic
EXPECT_EQ(scenarios::Emit(scenarios::Dag(*ctx_a)), scenarios::Emit(dag_before));  // and changes nothing in its input
```

Note the comment on cloning: because the DAG holds `shared_ptr`s ([section 6.5](#pr-why-return-a-result-and-how-it-is-applied)), two contexts must be built independently from the same inputs. The recordings avoid the problem by comparing documents, not objects. The sketch checks invariant 9 ([section 10](#pr-key-invariants-to-maintain)): `Solve` changes nothing, and the stage's apply step is the only writer to the event objects. The second proposed check adds the final `DiscreteGarageState` to the stage recordings, which closes part of gap 3.

## Benchmark method

This section is a proposal; nothing in the repository implements it yet. Time the solver call alone, after fixture construction, and separately time `Scheduler::Plan` end to end. Keep layout loading, the collision-table parse (seconds for `275_sunrise_b`, whose cached table is 281 MB of JSON; `scenarios::SharedScheduler` already does it once per binary), YAML parsing, ROS component start-up and `debug/printdags` output out of solver timings. Use the same optimized build flags, hardware, ROS distribution, dependency versions and thread count for every run.

Let t\_{k,r}\in\mathbb R\_{\ge0} \[ms\] be the duration of scenario k on repetition r\in\\1,\ldots,R\\, where R\in\mathbb N is the repetition count. For each scenario record the median \widetilde t_k\in\mathbb R\_{\ge0} \[ms\], the 95th percentile t\_{k,0.95} \[ms\] when there are enough repetitions, and the baseline median \widetilde t_k^{(0)} \[ms\] from the original code. The runtime ratio q_k\in\mathbb R\_{\ge0} is:

q_k=\frac{\widetilde t_k}{\widetilde t_k^{(0)}}.

q_k is defined only when \widetilde t_k^{(0)}\>0 \[ms\]; a value above 1 means the candidate is slower. Agree on a threshold with the team after measuring run-to-run variance, not before. Save raw timings as CSV or JSON:

``` text
solver,scenario_id,site_fixture,layout_hash,code_sha,build_type,host,iteration,elapsed_ms,success,event_count,edge_count,work_s,span_s,width,semantic_hash
```

`semantic_hash` is a hash of the canonical description from [section 4](#vr-compare-meaning-not-pointers-or-guids) (the emitted recorded part), never of pointer values or hash-map iteration order. `work_s`, `span_s` and `width` describe the parallelism of the action DAG in the response ([section 4.5](#ad-where-parallelism-comes-from)); they show whether a solver change made the plan more or less parallel even when the timing is unchanged.

## Build and run commands

Inside the devcontainer, from the workspace root (`poe build-pkg` is `colcon build --packages-up-to`; `poe test-pkg` is `colcon test --packages-up-to` followed by `colcon test-result --verbose`):

``` bash
poe build-pkg scheduler_advanced_tests                  # builds planner_core, motion_planner and scheduler too
poe test-pkg scheduler                                   # the assertions only, as CI runs them
SCHEDULER_CHECK_RECORDINGS=1 poe test-pkg scheduler      # also compare every recorded part
poe test-pkg scheduler_advanced_tests
poe scheduler-test-viewer                                # artifacts/scheduler-tests.html: every scenario drawn
```

Each test file is its own binary in the build tree; run one directly with gtest's flags, for example `build/scheduler/agv_assignment_tests --gtest_filter=AgvAssignment.ChainsThreeMovesAcrossTwoAgvs`, also under a debugger. The binaries read the scenario files from the source tree (`SCHEDULER_SCENARIO_DIR`), so `RECORD_REFERENCE_OUTPUT=1 build/scheduler/retrieve_job_tests` rewrites the files in place, and `git diff` shows what changed. The binaries print only errors; `SCHEDULER_TEST_LOG=1` brings the log back. A successful build does not mean the tests ran; read `colcon test-result` and the logs.

## System-level checks in simulation

The scenario files test the scheduler on hand-built inputs. The simulator runs the real stack against a simulated garage, and Dispatch already publishes every plan request and response for recording. That gives two more checks, described in the Simulation tab ([section 9](#sm-checking-the-refactor)): **replay**, which feeds recorded plan calls from baseline runs to the refactored scheduler and applies the canonical comparison of [section 4](#vr-compare-meaning-not-pointers-or-guids), on every pull request; and **closed-loop runs** of a scenario catalogue on the candidate, compared with the baseline on collisions, job outcomes and durations, before a stage is merged. Both are proposals.

## Test layers, and how baselines are computed and stored

The 99 scheduler tests are GoogleTest cases in `scheduler/test/src/`. They run as ordinary C++ test binaries, without ROS nodes and without the simulator: each loads an initial-state file, builds a request from its scenario or a context in code, and calls `Plan()` or one stage ([section 2](#vr-what-the-existing-tests-cover)). Their assertions show correctness in their own terms; the recorded parts show that a refactor left the outputs unchanged. Of the four layers below, the first two exist; the last two are proposed, and only the last needs the simulator.

| Layer                                                                                                              | Inputs                                                                                                                      | What is compared                                                                                                           | Simulator                 | When it runs                                                                               |
|--------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|---------------------------|--------------------------------------------------------------------------------------------|
| 1\. Test assertions (99 in `scheduler`, 3 in `scheduler_advanced_tests`, plus `planner_core` and `motion_planner`) | Initial-state files on `275_sunrise_b`, `5675_pecos_combined`, `38_gramercy`, `tiny_lot`; inline YAML in the advanced tests | Per-test assertions                                                                                                        | No                        | Every build (CI)                                                                           |
| 2\. Recorded parts (built, PR \#1007)                                                                              | The 63 scenario files: initial state, request or hand-built DAG                                                             | The canonical result of [section 4](#vr-compare-meaning-not-pointers-or-guids), against the recorded part of the same file | No                        | With `SCHEDULER_CHECK_RECORDINGS=1`: on every refactor pull request (not in CI by default) |
| 3\. Replay (proposed)                                                                                              | Plan requests extracted from simulation recordings, stored as plan scenarios of layer 2                                     | As layer 2, on realistic inputs                                                                                            | Only to record them, once | Every pull request                                                                         |
| 4\. Closed-loop runs (proposed)                                                                                    | The scenario catalogue of the Simulation tab                                                                                | Collisions, job outcomes and durations, over repeated runs                                                                 | Yes                       | Before a phase is merged; nightly                                                          |

Benchmarks ([section 5](#vr-benchmark-method)) would reuse the inputs of layers 2 and 3 and time them; they do not need the simulator either.

### Computing a baseline

A baseline is the canonical result of each scenario as produced by the code before the refactor, stored so that every later commit can be compared with it. PR \#1007 produced it in the way this section proposed, with test-only code and without changing the scheduler sources in `src/`:

1.  **The capture code came first, as test-only code.** The loader, the canonical forms and the comparison (`test/src/scenarios/`) were added as a static library that every test binary links.
2.  **Every scenario was run through the code of that commit** with `RECORD_REFERENCE_OUTPUT=1`: plan scenarios through `Plan()`, stage scenarios through `AssignTrays` or `AssignAgvs` on the DAG their test builds. The results were written into the recorded part of each file, "bugs included".
3.  **The files were committed** next to their inputs, in the same file. From then on any branch can run the same scenarios with the comparison on, and a failure names the file and the first differing line.

The baseline commit is therefore the merge of PR \#1007 (`28f69008`, with the viewer in `6d4ae5b5`). PR \#1018 kept every recording except the new scenarios and the two `FromUnavailableCharger` messages, whose error text it reworded on purpose; the Eccles removal changed behaviour only on decommissioned layouts, which no scenario uses. What is not done: tagging the baseline commit, and recording the code SHA in the files.

### Where fixtures and results are stored

Each scenario keeps its input and its recorded result together in one file of the scheduler package, so that a reviewer sees an input and its expected result side by side. Initial states are separate files, shared between scenarios:

    scheduler/test/scenarios/
    ├── README.md                          # the format, the canonical forms, how to record
    ├── initial_states/
    │   ├── 275_sunrise_b/                 # the folder is the layout's name
    │   │   ├── car_at_p2066_bay_ready_to_retrieve.yaml
    │   │   └── ...                        # 33 files
    │   └── 5675_pecos_combined/, 38_gramercy/, tiny_lot/   # 16, 11 and 3 files
    ├── plan/                              # through Scheduler::Plan; one folder per job test file
    │   ├── retrieve_job/FromStall.yaml    # RetrieveJob.FromStall
    │   ├── bay_job/Transitions.to_insert.yaml   # a suffix tells apart several scenarios of one test
    │   └── ...                            # 50 files
    └── task_planning/                     # one stage alone
        ├── tray_assignment/               # 4 files
        └── agv_assignment/                # 9 files

A recorded part is small and readable, so a changed decision appears as a reviewable diff. A stage scenario, `task_planning/tray_assignment/MovesOneBlocker.yaml`:

``` yaml
test: TrayAssignment.MovesOneBlocker
description: >-
  Scenario: On 275_sunrise_b, AGV 1 waits at P2075 and empty trays stand at P2067, P2066 and
  P2077; ... Expected: The stage adds one move that parks tray 2 out of the way, chains it
  before the root move, and reports success.
initial_state: 275_sunrise_b/empty_trays_at_p2066_p2067_p2077
input:
  dag:
    events:
      - "Task ID: 0 TRAY_MOVE Tray ID: 1 Dest: 2068@0 Agv ID: Unassigned #0"
    edges: []
    first_event_by_tray: {}
output:
  dag:
    events:
      - "Task ID: 0 TRAY_MOVE Tray ID: 1 Dest: 2068@0 Agv ID: Unassigned #0"
      - "Task ID: 0 TRAY_MOVE Tray ID: 2 Dest: 2061@90 Agv ID: Unassigned #0"
    edges:
      - [1, 0]
    first_event_by_tray:
      1: 0
      2: 1
```

What is kept where:

- **In the repository:** scenario files, initial states and their recordings. They are kilobytes each and change only by review.
- **Outside the repository:** the viewer's page (`artifacts/scheduler-tests.html`, generated), simulation recordings (mcap files, often hundreds of megabytes) and raw benchmark timings (the CSV of [section 5](#vr-benchmark-method)), in CI artifacts or a shared bucket, each keyed by commit and host. A replay scenario should name the recording it came from and its hash, so it can be traced back.

### Updating a recording

During the refactor, recordings are not updated: a difference is a defect, and the exit criterion of every phase is that all of them still match. A change that is meant to alter plans (a new solver, a tuned cost, a fix) re-records the scenarios it affects with `RECORD_REFERENCE_OUTPUT=1`, then runs the tests again with `SCHEDULER_CHECK_RECORDINGS=1`. The pull request shows the YAML diff, and says why it is expected; PR \#1018 did this for its two reworded error messages. A new scenario is a file with the authored part only; its first recording adds the rest. The closed-loop runs of layer 4 would show whether new plans are better.

### Testing the algorithm without the simulator

Layers 1 and 2 already do, and layer 3 would. The proposed solver interfaces make it simpler still: a test builds an `Input` (a garage state and an event DAG) directly, without a `Scheduler`, and checks the returned `Result`. Beyond fixed scenarios, the same entry point allows **property tests** on generated inputs, which do not exist yet: random occupancy on a site layout, then checks that hold for any input, such as an acyclic event DAG, every tray move with exactly one AGV, a valid final state, and an unchanged input (the invariants of the Issue & proposal tab, [section 7](#pr-key-invariants-to-maintain)).

### Where the simulator fits

The simulator has two roles. It is a **source of realistic inputs**: a recorded run on a real-site layout contains every plan request Dispatch sent, and those requests could become replay scenarios. And it is the **system check**: the closed-loop runs show the effect of a changed decision on later requests, on collisions and on job durations. Because simulation runs are not repeatable request for request ([Simulation tab, section 8.3](#sm-determinism-and-what-to-compare)), they are compared statistically, never against recordings.

The build commands of [section 6](#vr-build-and-run-commands) also name the `scheduler_advanced_tests` package. Its three tests plan inline garage states on `550_w21st` and `175_e82nd` and have no recordings; turning them into plan scenarios would bring two more sites, and the VRC path on a second site, under the comparison.

## Acceptance checklist

The refactor is accepted when every item below holds. The list gathers the conditions set out in the preceding sections: a captured baseline, parity of both default solvers, ported tests, real-site benchmark scenarios with stored baselines, and the simulation checks of [section 7](#vr-system-level-checks-in-simulation). The first is done.

- Baseline captured: the recorded part of every scenario file (PR \#1007), kept by PR \#1018 apart from two reworded messages.
- Default tray solver behind `AssignTrays`: every `tray_assignment` and plan scenario passes with `SCHEDULER_CHECK_RECORDINGS=1`.
- Default AGV solver does the same, including non-tray root draining (`ApplyNonTrayRootEvents`), node-arrival edges (`OrderArrivalAfterPriorOccupant`), path repair (`OrderAgvMovesAfterBlockingAgvs`) and the AGV-lift dependencies (`OrderAllTransitionsAroundAgvLifts`).
- Both solvers can be constructed in a test without a `Scheduler`.
- Direct tests added for `OrderAgvMovesAfterBlockingAgvs` and `OrderAllTransitionsAroundAgvLifts` (gap 2).
- `Scheduler::Plan` uses only the new interfaces for both assignment phases.
- The 4 direct `AssignTrays` and 9 direct `AssignAgvs` call sites in `test/src/stages/` ported; the stage methods reduced to calls of the solvers.
- At least 10 approved real-site scenarios for **each** solver, with recorded provenance.
- Benchmark baselines from the original code stored with code SHA, environment and raw samples.
- Unit tests, the three advanced tests and applicable system tests pass.
- Plan calls recorded from the simulation scenario catalogue on the baseline replay with p=1 on the candidate.
- Closed-loop simulation runs on the candidate: no collision, the same job outcomes as the baseline, durations within the baseline's spread.

## Evidence limits

The test inventory is read from the live repository on `main` at `a468657f` (2026-11-05): `scheduler/test/` (sources, scenario files and their README), `scheduler_advanced_tests/test/`, `planner_core/test/` and `motion_planner/test/`, counted by reading the files, and the commit messages of PRs \#1007 and \#1018. The `scheduler` snapshot (`sources/repomix-scheduler.xml`) holds the sources, the test sources and the initial states at that commit, but not the plan and stage scenario files; the `planner_core` and `motion_planner` snapshots are at the same commit, without tests. The other snapshots are unchanged: `common_ros` (`sources/repomix-common-ros.xml`, without tests), the message definitions of `interfaces`, and `cost_functions` (the trapezoid model, `MotionCostModel` and motion runs, without tests); the Simulation tab adds `sim` and `vis`. `common` and `task_planner` are referenced but not included, so statements about them come from call sites and need checking. Customer-site geometry and AGV dimensions are not in the snapshots; the 2D figures use illustrative coordinates. No timing in this tab is a measured value, and the recordings were not re-run for this tab.
