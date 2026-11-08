# Codex review 1 of PR #1036 (tip `2008ca0a`), 2026-11-05

Run with `codex_review_prompt.md`. The review as received is quoted first; the evaluation follows.

## The review

> **Keep this in draft: I reproduced an eviction that makes the insert fail validation.** The existing suite
> passes (198 scheduler, 24 planner-core, 15 advanced) with recording comparison enabled; zero warnings;
> clang-tidy, Black and mypy pass; the repository remains clean.
>
> 1. **Defect, high priority: an eviction can block the tray's only route** (`tray_assignment.cpp:645`,
>    `2008ca0a`). Charger selection checks the evicted AGV's journey and clearance from the destination
>    stall, but the final tray search still ignores AGVs along its path. Evidence: from
>    `StallBlockedByAgvOnCharger`, remove tray 7 from P5, add AGV 2 at B7, disable W4. The scheduler moves
>    AGV 7 from P5 to C10, then selects P5 for tray 27; validation returns "Cannot find path from 7@90 to
>    5@90"; zero actions, job errored, `response.success == true`. With AGV 7 initially at C16 the insert
>    succeeds through W9. Change: before accepting an eviction, establish that the resulting tray moves
>    remain reachable with the relocated AGVs as obstacles; try another charger or keep the stash.
>    Confidence: confirmed by running (probe modes 8 and 9).
> 2. **Defect, incomplete fix: AGV exclusions do not cover every blocking-tray search**
>    (`tray_assignment.cpp:436`, `4d7401c7`). Contrary to the commit and PR descriptions,
>    `ResolveBlockingTrays` itself does not add AGV poses; only `AssignDestinationAndUnblockingMoves`
>    supplies them. The fixed-destination blocker search at line 179 supplies root-path exclusions without
>    AGV poses; `ExpandChargePayloadJob` also calls the resolver without them. A scratch call on the
>    reproduction state (B7 ready to retrieve) still returns P15 while AGV 1 occupies C14. Change:
>    centralise the policy in the resolver with an explicit exception for the eviction candidate search.
>    Confidence: confirmed by reading and running.
> 3. **Defect in regression coverage: array order does not prove execution order**
>    (`insert_job_tests.cpp:133`, `2008ca0a`). The "AGV 1 still moves after the car is parked" check only
>    examines positions in `schedule.nodes`. The recording makes the loaded move depend on the eviction's
>    final action (action 10 has parents `[8, 6]`), but the test would not detect the loss of that edge,
>    and CI does not compare recordings. Change: assert dependency ancestry from the eviction's final action
>    to the loaded departure, and that its actions belong to the insert job. Add scenarios for the route
>    failure, two blocking AGVs competing for chargers, free chargers unreachable by the evicted AGV, and a
>    blocking-tray repark whose destination overlaps an AGV.
> 4. **Defect, low: a same-scenario URL without a step retains the previous selection** (`app.js:313`,
>    `8fa8a934`). Opening `#scenario` after `#scenario@5` keeps step 5. Confirmed by reading.
> 5. **Naming and rules.** `IllegalPosesOfParkedAgvs` → `CollectAgvParkingExclusions` (verb-first);
>    `carrier_agv_id` → `attached_agv_id`; `RegisterTransition` → `RecordTransitionOccupancy`;
>    `AgvEvictionPlan::plan` → `tray_plan`; `stall` → `candidate_destination_opt`; `overlaps_stall` →
>    `is_overlapping_destination`. `[[nodiscard]]` on `ApplyToWorkingState` and the new value-returning
>    helpers including `ResolveByEvictingAgvs`. `_opt` names and `.value()` for the new optionals.
>    `ExpectStashWithoutEviction` into the anonymous namespace; include `<optional>` in the test file.
> 6. **Nits.** The scenario comments at `insert_job_tests.cpp:110` and `:123` repeat the YAML; the viewer
>    introduction in `app.js:1` is long; keep the TRAY-id transition comment. The PR text says the viewer
>    is the last commit (it is first) and claims every resolver caller gets AGV exclusions.
>
> Greptile pre-answers: crossing the freed stall is not a defect; two evicted AGVs cannot take one charger
> (each move is applied to `evicted_state` first); the eviction keeps its job (job index → GUID 1001);
> C10 is not always invalid; the evicted AGV can become the carrier (documented inefficiency); the search's
> AGV-vs-payload query and validation's AGV-vs-TRAY query are not equivalent in general though they agree
> on this payload; #1031's unassignable AGVs must be excluded from eviction while staying obstacles; **the
> C1 extraction is not mechanical: `NewMove` is tray-only and `StepsFromDag` skips AGV events, so the
> module API needs AGV relocation results and eligibility inputs before this feature fits it**; recording
> comparison stays opt-in, so dependency invariants belong in ordinary assertions.
>
> Verdict: keep in draft until eviction preserves tray-route feasibility and the ordering test checks
> dependencies; resolve or narrow the resolver coverage; then the naming and rule corrections. Not
> verified: the viewer's interactive behaviour (browser policy refused the `file://` URL); intermediate
> commits; multi-AGV and recursive eviction.

## Evaluation

| # | Verdict | Notes |
|---|---|---|
| 1 | **Accepted, defect.** | Reproduced by the probe (mode 8 fails, mode 9 passes). Cause: `FindDestinationForRootTray` searches with `BuildImmobileTrayFilter`, which ignores every AGV, so the rerun after the eviction cannot see that the relocated AGV closes the tray's route; validation then can. The charger choice must be checked against the tray's route. |
| 2 | **Accepted, regression introduced by commit 4.** | Commit 3 added the exclusions inside `ResolveBlockingTrays`; commit 4 moved them to the one caller that needed a search without them, and dropped the other two callers (`AssignTrays` line 179, the fixed-destination blocker reparks; `ExpandChargePayloadJob` at `job_expansion.cpp:755`) and the recursion's own entry. Commit 4's message and the PR text are wrong about this. |
| 3 | **Accepted.** | The recording carries the edge; the test does not. `ActionNode.parents` are indices into `schedule.nodes`, so an ancestry walk is a few lines. The four extra scenarios are worth adding; the route-failure one doubles as the regression test for finding 1. |
| 4 | **Accepted, viewer.** | Goes to the viewer session that owns `app.js`, with the `app.js:1` nit. |
| 5 | **Mostly accepted.** | Verb-first for the helper: `CollectIllegalPosesOfParkedAgvs` keeps the planner's own word for the concept (`illegal_poses`) rather than "exclusions". `carrying_agv_id` instead of `attached_agv_id`, after `DiscreteTrayState.agv_id` ("the AGV this tray is being carried by"). `RecordTransitionOccupancy`, `tray_plan`, `destination_opt`, `charger_pose_opt`, `[[nodiscard]]` everywhere named, `<optional>` include, the test helper into the anonymous namespace: all accepted. **Rejected:** `is_overlapping_destination` for the lambda; `is_*` marks a bool value, and a predicate lambda reads better as a verb (`overlaps_destination`), the same convention the file uses for `resolve_blocking_tray`. |
| 6 | **Accepted.** | Both test comments go; the PR text gets the commit order and the resolver claim corrected. |

The C1 remark matters beyond this PR: the planned tray-module `Result` has no AGV moves and `StepsFromDag` drops AGV events, so the solver interface of `PROMPT.md` 6.3 needs an AGV-relocation output before stage C1 moves this code. Recorded in `SW2-905_notes.md` section 9.

## Fix plan (applied on the user's go)

1. **Exclusions back in the resolver.** `ResolveRequest` gains `bool is_parking_over_agvs_allowed = false`;
   `ResolveBlockingTrays` adds `CollectIllegalPosesOfParkedAgvs(working_state, tray.agv_id)` unless the
   flag is set; `ResolveByEvictingAgvs` sets it for its candidate search only. The three callers and the
   recursion are covered without touching them. Recordings may move for charge-payload scenarios with an
   AGV beside a VECS; the comparison run says.
2. **Route feasibility.** `FindUnoccupiedChargerWithShortestTravelTime` becomes a thin wrapper over
   `FindUnoccupiedChargersByTravelTime` (sorted). For each blocking AGV the eviction tries the chargers in
   that order and keeps the first whose placement leaves the destination reachable: the check applies the
   candidate plan's tray moves to a copy of the evicted state and runs `FindPosePath` with validation's
   filter (`BuildStaticObstacleFilter(payload footprint, state, ignore_trays = {tray}, ignore_agvs =
   {tray.agv_id}, {})`). No charger passes: the stash stays. The search cost grows by one path search per
   candidate; chargers are few.
3. **Test.** `StallBlockedByAgvOnCharger` asserts, through `parents`, that the first loaded move of AGV 7
   descends from AGV 1's last move, and that every AGV 1 node carries the insert job's GUID. New
   scenarios: `StallBlockedByAgvEvictedAwayFromRoute` (the probe's mode 8: tray 7 removed from P5, AGV 2
   in B7, W4 disabled; expected after the fix: AGV 7 goes to C16 and the car parks on P5),
   `StallBlockedByTwoAgvs` (AGV 2 idle on P15 and AGV 1 on C14: two evictions to distinct chargers, both
   ordered before the loaded move), `StallBlockedByAgvChargersUnreachable` (W9 and P17 disabled: no
   charger reachable, stash on W31), and a stage test on `ResolveBlockingTrays` for a blocking tray whose
   nearest open stall is P15 beside AGV 1 (finding 2).
4. **Names and rules** as in the table; comments in the tests removed.
5. **PR text**: commit order and the resolver claim.
6. **Viewer**: the hash and the introduction, by the viewer session.
