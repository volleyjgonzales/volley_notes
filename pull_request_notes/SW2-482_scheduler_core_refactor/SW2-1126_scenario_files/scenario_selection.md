# How the scenarios were chosen

For review: which scenarios the PR records, where each comes from, why it runs where it runs, and
what the selection leaves out. Numbers are from the branch as of 2026-10-28 (commits b26ea5d6 and
396ca448). Section 8 lists the points worth a decision.

## Contents

- [1. The rule](#1-the-rule)
- [2. What the old tests were](#2-what-the-old-tests-were)
- [3. Did the port expand the coverage?](#3-did-the-port-expand-the-coverage)
- [4. Old test to new scenario, one by one](#4-old-test-to-new-scenario-one-by-one)
- [5. The four scenarios that are new](#5-the-four-scenarios-that-are-new)
- [6. Why the layouts changed](#6-why-the-layouts-changed)
- [7. The initial states](#7-the-initial-states)
- [8. What the selection does not cover, and the points to decide](#8-what-the-selection-does-not-cover-and-the-points-to-decide)

## 1. The rule

The PR is the parity baseline for the scheduler refactor: it must record what the scheduler does
today, for every situation a test already exercised, so that a later commit which changes the
output is caught by a diff. So the selection rule was: **every test on main that plans becomes a
scenario, no test is dropped for being inconvenient, and nothing is added except where an existing
code path had no test at all.** The scenarios are not a test plan designed from the scheduler's
features; they are the existing tests, ported one to one, plus four gaps closed. Where a test's
inputs had to change (a layout that no longer exists, a bug in the test itself), the change is
recorded here and the recorded output is the scheduler's answer to the new inputs, not a hand-edited
expectation.

Three consequences to keep in mind when judging the selection:

- Coverage is as uneven as the old tests were: eleven retrieve scenarios, one insert scenario on
  the production site, no rebalance scenario (section 8).
- A recorded file says what the scheduler produced, not that it is right. Two recordings show
  behaviour worth a look (section 8); they are recorded as they are, since changing behaviour is
  not this PR's job.
- The descriptions were written by hand from the recordings and checked against them (one
  wrong waypoint found and fixed in review); they are the human-readable claim, the recording is
  the evidence.

## 2. What the old tests were

Four gtest binaries on main, 72 `TEST` cases:

| binary | tests | layouts | what they did |
| --- | --- | --- | --- |
| `scheduler_jobs_tests` | 30 | tiny_lot (24), 1355_fulton (4), 576_eccles_half (2) | one job through `Scheduler::Plan`, YAML state as a string literal in the source |
| `scheduler_tests` | 25 | tiny_lot (17), triple_pick_lot (2), 576_eccles_half (2), layout_test (4, the clean-garage and dependency tests) | stage calls on a hand-built DAG (15), cost functions (4), scheduler state (3), clean-garage plans (3) |
| `scheduler_insert_orientation_tests` | 4 | 1355_fulton | INSERT from each of two bays, tray straight or reversed |
| `utils_tests` | 13 | none (abstract states) | `ValidateBaseState`, `CountEmptyTrays`, bay classification and rebalancing |

Plus one test commented out with a "revisit" TODO (`Scheduler.DoubleRetrieveDodgeAgv`, which
loaded a dead `garage_states/` file on 576_eccles_half); it is deleted with the file.

## 3. Did the port expand the coverage?

Only marginally in breadth; substantially in depth. Before, on main, 37 of the 72 tests went through
`Scheduler::Plan` (the 30 in the jobs file, the 4 insert-orientation tests, the 3 clean-garage
tests); two held several cases in one body, so they amounted to 41 planned situations. 15 called a
stage or a helper on a hand-built DAG; the rest were cost, state and utils tests. Every state was a
YAML string literal in the source, and the checks were hand-written assertions on a handful of
properties per test (the last node's destination, one lift and one lower, the job returned as
executing); nothing compared the full response, so a change outside the asserted properties passed
silently.

After: 45 plan scenarios and 13 stage scenarios, plus 31 tests without a file, 89 in all. That is the
41 old plan situations and the 13 old stage situations carried over one to one, plus the four new
scenarios of section 5. In coverage terms:

- The four new scenarios are the only new ground in the library: the two tray-assignment fallbacks
  in `ResolveBlockingTrays`, READY_FOR_INSERT with a blank tray id, and a non-empty base schedule.
  In the per-job coverage report that is the whole of the expansion: 2,019 to 2,026 covered lines of
  `scheduler.cpp`.
- One old test was broken (TwoAgvsDistinctChargers gave both jobs the same GUID, so only one was
  planned); its scenario exercises the two-job path it was meant to.
- The other 16 tests added during review (8 `Deterministic`, 8 `ScenarioYaml`) test the support code
  and the recordings' premise, not the scheduler.
- The aggregate figure on the PR fell from 72.7% to 71.4%; that was traced to CI's cache policy on
  push runs dropping the collision-table builder's lines from the system jobs, not to the scheduler.

What did change is the depth of each check, the layouts and the form of the data. Every plan
scenario compares the complete response, every action node and every job, against a recording, so a
refactor cannot change a detail nobody thought to assert; the stage scenarios compare the whole
event DAG before and after. The inputs moved from four synthetic or defunct layouts to three real
sites, which surfaced real behaviour (retrieves through the gramercy car lift). The states and
requests moved from string literals into files the viewer draws. So the breadth is the old suite's,
retrieve-heavy and without a rebalance scenario (section 8); what the PR made is a baseline that is
exact rather than partial, which is what a parity check needs. Widening it is now a state file and a
request per scenario.

## 4. Old test to new scenario, one by one

Every old test appears below; the new name is the file under `test/scenarios/` and the suite in
`test/src/`. "Same inputs" means the situation is the same, not the numbers: the layout changed, so
every node id and heading changed with it, but each thing stands in the same place relative to the
others (the same stall beside the same door, the same blocker on the same critical path), the bay is
in the same state, the job asks for the same thing, and the parameters are the same. How that was
achieved is in section 6. The last column says what, if anything, changed beyond that.

### Plans through `Scheduler::Plan` (`scheduler_jobs_tests`, 30)

| old test | new scenario | layout now | changed |
| --- | --- | --- | --- |
| MoveAgvJob | MoveJob.AgvToBay | 275_sunrise_b | same inputs |
| MoveAgvJobAlreadyAtDest | MoveJob.AgvAlreadyAtDestination | 275_sunrise_b | same inputs |
| ReparkTrayJob | ReparkTrayJob.ToBay | 275_sunrise_b | same inputs |
| ReparkTrayJobGoodVecs | ReparkTrayJob.ToReadyCharger | 38_gramercy | EV charger: moved to the one site that has them |
| ReparkTrayJobBadVecs | ReparkTrayJob.ToUnavailableCharger | 38_gramercy | as above |
| ReparkTrayJobChargingVecs | ReparkTrayJob.WhileCharging | 38_gramercy | as above |
| ReparkTrayJobBadVecsDest | ReparkTrayJob.FromUnavailableCharger | 38_gramercy | as above |
| ReparkTrayJobGoodVecsAtDest | ReparkTrayJob.FromReadyCharger | 38_gramercy | as above |
| ReparkTrayJobAdvanceToWaypoint | ReparkTrayJob.AdvancesBlockersToWaypoint | 5675_pecos_combined | was 576_eccles_half (defunct site); eight trays in a row of stalls, same shape |
| ReparkUnplugVecs | ReparkTrayJob.UnplugsCharger | 38_gramercy | as the charger tests |
| ReparkUnplugVecsMoveAgvFirst | ReparkTrayJob.UnplugsChargerAgvMovesFirst | 38_gramercy | **identical inputs and output to UnplugsCharger** (section 8) |
| RetrieveJob | RetrieveJob.FromStall | 275_sunrise_b | same inputs |
| RetrieveJobDisabledNode | RetrieveJob.FromDisabledNode | 275_sunrise_b | same inputs |
| RetrieveJobGoodVecs | RetrieveJob.FromReadyCharger | 38_gramercy | charger; the retrieve now goes through the car lift BL26 (section 6) |
| RetrieveJobBadVecs | RetrieveJob.FromUnavailableCharger | 38_gramercy | as above |
| RetrieveJobChargingVecs | RetrieveJob.WhileCharging | 38_gramercy | as above |
| RetrieveJobBayTransition | RetrieveJob.WithBayTransition | 275_sunrise_b | same inputs |
| BackToBackRetrieve | RetrieveJob.BackToBack | 275_sunrise_b | same inputs (two jobs in one request) |
| WeirdFultonRetrieve | RetrieveJob.WithCleanGarage | 5675_pecos_combined | was 1355_fulton (defunct); a retrieve with a clean-garage job in the same request |
| ChargePayloadJob | ChargePayloadJob.FromBayToCharger | 38_gramercy | charger |
| ChargePayloadJobNoVecs | ChargePayloadJob.WithoutCharger | 38_gramercy | charger; every charger disabled |
| ChargePayloadJobWrongPayload | ChargePayloadJob.WrongPayload | 38_gramercy | charger |
| InsertJob | InsertJob.WithCleanGarage | 275_sunrise_b | same inputs (insert plus clean garage) |
| ReadyForRetrieveJob (two cases in one test) | BayJob.ReadyForRetrieve.empty_bay, .tray_in_bay | 275_sunrise_b | split into two scenarios with suffixes; same inputs |
| AgvChargeJob | AgvChargeJob.ToNearestCharger | 5675_pecos_combined | was 1355_fulton; pecos has AGV chargers C10, C14, C16 |
| AgvChargeJobMVP454 | AgvChargeJob.TwoAgvsDistinctChargers | 5675_pecos_combined | was 576_eccles_half; **the old test gave both jobs the same GUID, so only one was planned; with distinct GUIDs both AGVs charge** (a fix of the test, section 8) |
| AgvChargeJobInBay | AgvChargeJob.FromInsideBay | 5675_pecos_combined | was 1355_fulton |
| DontGoToDisabledChargeNode | AgvChargeJob.SkipsDisabledChargers | 5675_pecos_combined | was 576_eccles_half |
| TransitionBay (four cases in one test) | BayJob.Transitions.unknown_bay, .wrong_command, .to_retrieve, .to_insert | 5675_pecos_combined | was 1355_fulton; split into four scenarios |
| CantTransitionDisabledBay | BayJob.CannotTransitionDisabledBay | 5675_pecos_combined | was 1355_fulton |

### Stage calls, helpers and state (`scheduler_tests`, 25)

| old test | new test / scenario | layout now | changed |
| --- | --- | --- | --- |
| TrayAssignmentTest | TrayAssignment.FillsBlankDestination | 275_sunrise_b | same inputs |
| TrayAssignmentTestComplexDag | TrayAssignment.ResolvesManyBlockersThenAssignsAgvs (tray stage, then the AGV stage recorded under agv_assignment) | 275_sunrise_b | was triple_pick_lot; **the blockers were re-posed** so that the 3 x 3 block of stalls P2116 to P2150 is full on the root tray's way out (section 6) |
| UnblockingTrayMoveTest | TrayAssignment.MovesOneBlocker | 275_sunrise_b | same inputs |
| ResolveBlockingTraysRecursivelyUnblocksChain | TrayAssignment.ResolvesBlockerChainRecursively | 275_sunrise_b | was triple_pick_lot; the block is closed off with `disabled_nodes` so the chain has nowhere else to go; calls `ResolveBlockingTrays` directly, no scenario file |
| TrayAndAgvAssignments | TrayAssignment.ThenAgvAssignment (tray, then AGV stage) | 275_sunrise_b | same inputs |
| MiAmigaEsSuAmiga | AgvAssignment.SkipsDisabledAgv | 275_sunrise_b | same inputs |
| AmigaSaysNo | AgvAssignment.FailsWhenDisabledAgvBlocksPath | 275_sunrise_b | same inputs |
| AmigaStash | AgvAssignment.ChainsThreeMovesAcrossTwoAgvs | 275_sunrise_b | same inputs |
| NoAmigas | AgvAssignment.FailsWithNoAvailableAgv | 275_sunrise_b | same inputs |
| AmigaBaySos | AgvAssignment.FailsWhenBayTransitionTrapsAgv | 275_sunrise_b | same inputs |
| AmigaBaySo | AgvAssignment.UsesAgvFreedByBayTransition | 275_sunrise_b | same inputs |
| TrayLiftBayTransitionDependencyTest | AgvAssignment.OrdersLiftsAroundBayTransitions | 275_sunrise_b | was layout_test |
| GetJustMovingCost, GetAgvCurrentPoseToTrayMoveCost, GetAgvOccupiedDuration, GetAgvToTrayAssignmentCost | AssignmentCost (4 tests) | 275_sunrise_b | no scenario file: pure arithmetic on a loaded state |
| SanityCheckEventsDisabledDest, SanityCheckEventsCantApply, and the third sanity check | SanityCheck (3 tests) | 5675_pecos_combined | were 576_eccles_half; no scenario file |
| SetBayReadinessRatioService, UpdateLastEntityEvent, ContinuousStateToSchedule | SchedulerState (3 tests) | 275_sunrise_b | no scenario file; the first builds its own scheduler (it mutates it) |
| CleanGarageAgvInTheWay, CleanGarageDontMoveAgvsUnderTrays, CleanGarageUnstashesTrayFromWaypoint | CleanGarageJob.AgvInTheWay, .DoesNotMoveAgvsUnderTrays, .UnstashesTrayFromWaypoint | 275_sunrise_b | were layout_test |
| DoubleRetrieveDodgeAgv (commented out) | deleted | | dead code with a TODO; its state file is gone too |

### Insert orientation (`scheduler_insert_orientation_tests`, 4)

| old test | new scenario | layout now | changed |
| --- | --- | --- | --- |
| FultonInsertBay1TrayHeading0 / 180, FultonInsertBay2TrayHeading0 / 180 | InsertJob.FromBay7TrayHeading90, .FromBay7TrayReversed, .FromBay21TrayHeading90, .FromBay21TrayReversed | 5675_pecos_combined | were 1355_fulton; the V2 retrieval-heading rule they checked has no effect on pecos (section 8) |

### Helpers (`utils_tests`, 13)

All 13 kept with the same inputs, renamed into three suites: ValidateBaseState (4, now on
275_sunrise_b states from `initial_states/`), CountEmptyTrays (1), BayRebalancing (8, abstract
states built in code). No scenario files: they assert on return values.

Totals: 72 old tests became 45 plan scenarios, 13 stage scenarios and 31 tests without a file
(cost, sanity, state, utils, the recursion test), 89 in all; plus the eight `Deterministic` tests
and the eight `ScenarioYaml` tests added during review make the 92 `TEST` cases in 19 binaries
(some old tests became several scenarios through suffixes; `ResolvesManyBlockersThenAssignsAgvs`
and `ThenAgvAssignment` each record two files).

## 5. The four scenarios that are new

Added because a code path had no test; each was agreed before it was written (review log items
6 and 48 to 57):

| scenario | path it covers | why it was missing |
| --- | --- | --- |
| BayJob.ReadyForInsert | `PlanReadyForInsertJob` with a blank tray id, which the fill pass resolves (8 nodes, bay transition last) | the old tests had READY_FOR_RETRIEVE only |
| MoveJob.BaseScheduleReservesAgvAndNodes | a request whose `base_schedule` is not empty: the command's AGV and its two nodes are reserved, so the other AGV does the job | every old test sent an empty base schedule |
| RetrieveJob.AdvancesRootTray | tray-assignment fallback 1: the lot is full, the blocker on the critical path has nowhere to go, so the root tray is advanced along the path while the next step is free | the fallbacks in `ResolveBlockingTrays` had no test |
| RetrieveJob.ParksBlockerOnCriticalPath | fallback 2: the next step is taken too, so the blocker is allowed to park on the critical path | as above |

The two fallback scenarios are the only ones left on the synthetic `tiny_lot` (section 6).

## 6. Why the layouts changed

Decisions taken with Jon on 2026-10-23 (log items 76 and 81): the tests must run on sites that
exist, `5675_pecos_combined` is needed (the engineering and QA sandboxes together), `275_sunrise_b`
is the recommended production layout, `576_eccles` (the former HQ) and `1355_fulton` are defunct
and to be avoided, and the synthetic `tiny_lot`, `triple_pick_lot` and `layout_test` go. EV
chargers exist on 38_gramercy, 175_e82nd and CambridgesideV8 only; gramercy was chosen.

| layout | scenarios | role |
| --- | --- | --- |
| 275_sunrise_b | 32 (plus the stage and state tests) | the default: everything around bay B2068 (door W2069, waypoints W2070 and W2064, stalls P2075, P2066, P2067, P2077), the blocker tests in the 3 x 3 block of stalls P2116 to P2150 east of the lane |
| 5675_pecos_combined | 15 | the bay and AGV-charger scenarios (bays B7 and B21, chargers C10, C14, C16), the insert-orientation scenarios, the sanity checks |
| 38_gramercy | 11 | every EV-charger scenario (chargers E21, E23, E25; the bay is the car lift BL26 on floor 1) |
| tiny_lot | 2 | the two tray-assignment fallbacks |

How the port was done: the tiny_lot scenarios were mapped by script, node to node (1 to 2068, 2 to
2069, 3 to 2070, 5 to 2064, 6 to 2075, 8 to 2066, 9 to 2067, 11 to 2077, headings turned by 90
degrees), so that each keeps its shape: the same stall, the same door, the same blocker. The
triple_pick_lot scenarios went to the sunrise block. The gramercy and pecos scenarios were written
by hand. Every ported scenario was re-recorded; the recorded output is the scheduler's answer on
the new layout. Before the port, the 44 scenarios converted by script from the old string literals
were checked against the old recordings: 57 of 58 outputs identical apart from job GUIDs and
normalised names, the one difference being the TwoAgvsDistinctChargers fix above.

### How a ported state was designed

A ported state keeps the old state's shape. tiny_lot has a bay (1), its door waypoint (2), two more
waypoints (3 and 5), three stalls (6, 8, 9) and a charger (11). Around sunrise's bay B2068 the same
roles exist: the door waypoint W2069, the waypoints W2070 and W2064 (the rotation node), and the
stalls P2075, P2066, P2067, P2077 one step off the door. The map is role to role, so that every
relation an old test relied on holds in the new state: a tray "one stall from the door" is still
one stall from the door, a blocker "on the critical path" is still on it. The headings turn by 90
degrees because sunrise's bays face heading 0 and its stalls heading 90, where tiny_lot had them at
0; a tray facing into the bay still faces into the bay. The old `RetrieveJob` is the plain case:

| | old (tiny_lot) | new (275_sunrise_b, `car_at_p2066_bay_ready_to_retrieve`) |
| --- | --- | --- |
| AGV 1 | stopped at 9 @ 0 | stopped at P2067 @ 90 |
| tray 1, carrying payload 1 | at 8 @ 0 | at P2066 @ 90 |
| bay 1 / B2068 | ready to retrieve | ready to retrieve |
| the job | RETRIEVE payload 1 to the bay | RETRIEVE payload 1 to B2068 |

The script applied that map to the 36 tiny_lot scenarios; the triple_pick_lot block went to the
3 x 3 block of sunrise stalls the same way. The gramercy and pecos states were written by hand to
the same principle: the car on a charger with the AGV on the stall beside it, as the old charger
tests had it on tiny_lot's node 11; the pecos bay states with the AGV in the bay as the fulton
tests had it. Where the shape could not be kept, the state was redesigned and the reason recorded:
the many-blockers block had to be filled (a grid always offers a blocker a neighbour, where
triple_pick_lot did not), the recursion block had to be closed with `disabled_nodes`, and the two
fallbacks could not be reproduced at all. The four new scenarios got states of their own, built for
the path they cover (a full lot with the blocker on the waypoint or on the next stall; a bay ready
to retrieve with no tray and two empty trays nearby; two AGVs with a reserved one). Every state is
named after what stands in it, and every ported scenario was re-recorded on the new layout: the
recording is the scheduler's answer to the new state, never the old recording relabelled.

What the move changed in behaviour, all recorded as found:

- **Gramercy retrieves go through the car lift**: VRC commands around the AGV commands, and the
  AGV hops from the lift node L2 to BL26 without a command of its own. The three retrieve-from-
  charger tests share a helper (`ExpectRetrieveThroughLift`) that allows for it.
- **The retrieval-heading rule fires on gramercy** (stalls and lift share heading 90): a reparked
  car whose payload is reciprocal to the tray is lowered at the reciprocal heading, so the repark
  assertions accept either heading (`IsAngleOrReciprocal`).
- **The two fallbacks could not be reproduced on sunrise.** With the garage open the blocker
  drives off to a waypoint and no fallback fires; with everything outside a region disabled,
  either no path is found (a disabled waypoint 0.8 m from the door counts as a disabled area, an
  AGV on the rotation node blocks the tray) or, once the fallbacks fire, the planner cycles (a
  4.6-million-line log, killed after ten minutes). Jon's decision: keep tiny_lot for these two.
- **The many-blockers scenario was re-posed twice** before the block was really full: on a grid
  of stalls a blocker always has a neighbour to slip into, so the root tray went to the south-east
  corner P2150 with every stall on its way out occupied; the recording then shows two blockers
  moving (trays 10 and 11) where the triple_pick version showed two others.
- **The recursion test needed the block closed off** with `disabled_nodes`, else the open edges
  of the sunrise grid make the blockers unnecessary.

## 7. The initial states

60 files under `initial_states/<layout>/`, one per distinct garage state, named after what stands
in the garage (`car_at_p2066_bay_ready_to_retrieve`, `two_agvs_eight_empty_trays_tray_13_at_p2150`),
never after a test, so that scenarios starting from the same state share one file: 58 scenarios
use 60 states because most states serve one scenario and a few serve several (the readiness and
transition scenarios of a pecos bay share `agv_in_bay_7`; the three charging scenarios share
`car_charging_at_23`), while three states exist only for tests that mutate a state in code
(`agv_at_w8_chargers_10_14_disabled`, `agv_and_empty_tray_in_bay_ready_to_insert`,
`agv_in_bay_7_ready_to_retrieve`) and one serves the utils tests. Fields at their default are left
out; numeric states carry their meaning as a comment. Eight states use `disabled_nodes`.

## 8. What the selection does not cover, and the points to decide

Gaps inherited from the old tests, listed so that they are chosen rather than overlooked:

- **REBALANCE_GARAGE has no scenario** (`PlanRebalanceGarageJob`); the bay-rebalancing helpers are
  unit-tested in `BayRebalancing`, the job expansion is not. The refactor will touch it blind.
- **`allow_reciprocal` is never set**, `note` only three times; the request's `planned_jobs` and
  `active_jobs` are never filled. `base_schedule` is used once (the new scenario).
- **Parameters**: `bay_readiness_ratio` is 0.5 in 34 scenarios, 1.0 in 5 and the default 0.0 in 6;
  `cost_audit` and `motion_cost` are never varied.
- **Multi-job requests**: four scenarios (BackToBack, TwoAgvsDistinctChargers, the two
  WithCleanGarage). Everything else is one job per request; interactions between jobs are thin.
- **INSERT on the production site**: one scenario on sunrise (WithCleanGarage); the four
  orientation scenarios are on pecos, where the V2 rule they were written for has no effect (by
  construction on sunrise: bays at heading 0, stalls at 90; on pecos the planner logs "No retrieval
  heading for dest node 5 / 6", which was not investigated).
- **Stage coverage is thin next to plan coverage**: 13 stage scenarios against 45 plans. Every plan
  passes through both stages, so a solver change shows in the plans, but not which stage changed.
  Commit 2's solver interface is the place to fix that, by recording the DAG after each stage of
  every plan scenario.

Points to decide:

1. **ReparkTrayJob.UnplugsChargerAgvMovesFirst** is an exact duplicate of UnplugsCharger: same
   state, same job, identical recording. Its name suggests a case where the AGV must move before
   the charger is unplugged, which the inputs never set up. Delete it, or give it the state its
   name describes (the AGV not beside the tray) and re-record.
2. **AgvChargeJob.TwoAgvsDistinctChargers** records different behaviour from the old test: the
   old test gave both jobs the same GUID by mistake, so the scheduler planned one; the scenario
   gives distinct GUIDs and both AGVs charge. The recording is the correct behaviour, but it is a
   change relative to main's test, which is worth knowing when the parity diff is read.
3. **tiny_lot stays for two scenarios.** The alternative is to drop the fallback scenarios, which
   would leave `ResolveBlockingTrays`'s two fallbacks untested through `Plan`.
4. **Two recordings show behaviour the team may not want**: on pecos the inserted car is lowered
   on the waypoint in front of the bay (W31 / W41) rather than in the free stall P15; and the
   retrieval-heading rule yields no heading for pecos stalls 5 and 6. Both are recorded as they
   are; a change is a later commit with its own re-recording.
5. **The eleven retrieve scenarios against one plain insert on sunrise** reflect the old tests'
   weight, not the job mix in production. If the refactor's risk is elsewhere (insert, rebalance,
   multi-job requests), scenarios there are cheap to add now that a scenario is a state file and
   a request.
