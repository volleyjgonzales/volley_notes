# Codex review 2 (2026-10-30) and its evaluation

Codex read the tip `43f88f6f` (before its findings were applied) (source only; no build, tests or recordings). Seven findings, all
checked here by reading; the user's instruction: Eccles is deprecated and is to be removed.

| # | Finding | Check | Verdict |
|---|---|---|---|
| 1 | A failed expansion leaves its events in the plan, and they take the next successful job's identity: `job_index = ctx->scheduled_jobs.size()` is taken before expanding, `AddScheduledJob` runs only on success (scheduler.cpp 118-119, 212), so the leftover events of a failed job and the events of the next successful job share an index; `action_graph.cpp:199` indexes `scheduled_jobs` by it. Example path: ExpandRetrieveJob adds the stop-charging event (via UnplugEvChargerBeforeTrayMove) before "No Bay available for retrieve" fails the job. | Confirmed. This is the open `TODO(any)` at scheduler.cpp:297 ("strip the failed job's events"); Codex adds the consequence: misattribution, not only extra planning. Inherited. | Real defect, worth fixing in this PR's fix commit: make expansion transactional by restoring the PlanContext on failure (copy before `ExpandJob`, assign back on error; the DAG copies pointers to shared events, the maps are small), plus a scenario: a retrieve of a charging tray with no bay available, followed by a job that succeeds, asserting the stop-charging event is absent and the next job's events carry its own index. Behaviour change, so the recordings decide: if any recorded plan contained leftover events it changes, and that is reported before the commit. |
| 2 | `ApplyEvChargeHeading` hard-codes a `576_eccles` layout-name substring and node ids 46/47 (tray_assignment.cpp 46-57); six call sites, one of which reads the return value (ApplyPreferredHeading). | Confirmed. The scheduler's recorded scenarios use no Eccles layout (the README lists it as decommissioned). Eccles remains in: `scheduler_advanced_tests` 01-04 (01 and 04 are charging tests), eight layout files under `src/config/site_config/layouts`, 14 exerciser scenarios under `src/scenario`, and common_ros collision tests. | Remove, per the user: one commit deleting `ApplyEvChargeHeading` and its six call sites, and the four Eccles advanced tests (01-04) that would otherwise change meaning; the recordings must stay unchanged (no Eccles scenario). The rest of the Eccles retirement (layouts, exerciser scenarios, common_ros tests, CI entries) is cross-package and gets its own ticket. Note that `ReparkTrayJob`'s "EV charge" branches stay: they key on VECS state, not on the layout. |
| 3 | `ComputeAgvMoveDuration` returns zero when `ComputeTravelDuration` has no result or the change variant is unknown (agv_assignment.cpp 600-622); the zero feeds AGV availability. | Confirmed. | Real weakness, inherited; propagating failure changes which plans succeed, with no known reachable input. Defer to the AGV-module ticket (plan stage F) with the note; not a silent change in a readability PR. |
| 4 | `ComputeStateBefore` discards every `ApplyTo` result and unwraps the topological order (agv_assignment.cpp 42-53); used by OrderTransitionAroundAgvLifts. | Confirmed. | Same category as 3: defer, same ticket. SanityCheckEvents replays the whole DAG afterwards and fails on a bad apply, so the damage is bounded to lift ordering of an already-failing plan. |
| 5 | `SetBayReadinessRatioCallback` accepts NaN: both range comparisons are false (scheduler.cpp 305-308). | Confirmed. No test covers the setter. | Fix in the fix commit: reject non-finite values with `std::isfinite` before the range check, and a unit test (NaN rejected, 0.5 accepted, change detection). Small and client-visible only for NaN. The constructor's `bay_readiness_ratio` parameter comes from ROS params and is left alone. |
| 6 | `ComputeAgvOccupiedDuration` ignores its arguments and returns zero (agv_assignment.cpp 251-255, `TODO(any)`); its call makes the initialisation look dependent on the AGV and the plan; a test asserts the zero. | Confirmed. | Behaviour-neutral readability: delete the stub and its test, initialise `agv_occupied_durations[agv_id]` to zero at the call site with the same `TODO(any)` text. Fold into commit 5 (dead code). |
| 7 | Each expansion copies `initial_state` and replays the DAG; nested expansions repeat it; `ComputeStateBefore` sorts and replays per transition. | Confirmed as repeated work; cost unmeasured. | Defer: measure on large requests first (plan stage G benchmarks); the transactional expansion of item 1 is the natural place for a maintained working state later. |

Also from Codex: `PlanContextSPtr` by value in synchronous helpers hides that they only borrow;
references would say so. Agreed and behaviour-neutral, but it touches about forty signatures and
every stage test; a mechanical commit of its own, best done when C0 moves the stages into their
folders. Codex's priorities (explicit failure results and honest contracts over syntax
modernisation) match the stage's rules.

## Proposed work, in order

1. Commit 5 fold-in: delete the `ComputeAgvOccupiedDuration` stub and its test (item 6).
2. Fix commit additions (behaviour changes, each with a test): transactional expansion (item 1)
   and the NaN check (item 5). Recordings compared before and after; any change is reported, not
   absorbed.
3. New commit 13: remove the Eccles EV-charging heading exception and the four Eccles advanced
   tests (item 2). Recordings unchanged by construction.
4. Tickets: items 3, 4 and 7 (AGV module / benchmarks), the repo-wide Eccles retirement, and
   `PlanContext&` instead of the shared pointer.
