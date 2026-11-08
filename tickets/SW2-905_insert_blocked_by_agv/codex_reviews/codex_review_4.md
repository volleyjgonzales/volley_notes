# Codex review 4 of PR #1036 (tip `e9f799bb`), 2026-11-06: Greptile's loaded-AGV finding, and #1031

Source inspection only; neither the loaded-eviction failure nor a combined-branch test was run.

## The assessment, condensed

1. **Greptile's P1 is substantiated.** `ResolveByEvictingAgvs` excludes disabled AGVs and the root tray's
   carrier but not an AGV carrying another tray. Such an AGV is moved with a bare `AgvMove`: applying the
   pose change carries the tray along, the charger search uses the empty-AGV footprint, `IsTrayPlanFeasible`
   checks the tray plan but not the loaded eviction's own path, and validation then checks the loaded
   footprint without excluding the carried tray, so it can reject the eviction and fail every job of the
   request instead of keeping the stash. Narrow fix: exclude `IsCarryingTray(agv)` from eviction candidates
   (an AGV under a lowered tray is a different state and stays eligible), keep excluded AGVs and their
   trays as obstacles, preserve the stash when eviction yields nothing. Do not fix it by ignoring the carried
   tray in validation; supporting loaded eviction properly needs tray-move semantics. Regression: a loaded
   blocking AGV with an available stash; the fixture must actually reach the eviction attempt.
2. **#1031 integration.** Unassignable AGVs are eligible only for jobs naming them; an eviction is implicit
   work even though its `AgvMove` names the AGV. After integration: carrier choice, hiding during Clean and
   eviction candidates all exclude unassignable AGVs; occupancy and collisions keep them as obstacles;
   explicit charge or move jobs keep #1031's exception. Filtering carrier assignment alone is not enough.
   Do not mark them disabled or remove them from the state.
3. **Port #1031's policy into the current scheduler**: request → `PlanContext::unassignable_agvs`;
   `DoAgvAssignments` → `AssignAgvs`; `PlanCleanGarageJob` / `HideAgvs` → `ExpandCleanGarageJob` /
   `FindAgvUnderTrayAssignment`; plus `ResolveByEvictingAgvs`. Keep the `unassignable_agvs` name; no generic
   "available AGV" helper. Integration tests: an unassignable blocker stays, the fallback is valid, an
   explicit charge job still works, clearing the restriction restores eviction.
4. **Merge recommendation.** Fix loaded-AGV eviction in #1036 now; the unassignable guard stays a tracked
   requirement until #1031's field exists, and the two must not ship together without it. #1031's retry does
   not replace the guard; respecting the guard means some low-battery blockers stay put until they recover,
   so #1036 must not claim to resolve all charging-related blockage.

## Evaluation

| # | Verdict | Notes |
|---|---|---|
| 1 | **Accepted, defect.** | Confirmed by reading: `IsCarryingTray` is `agv.tray_id != 0`; the blocker loop tests only `disabled` and `agv_id != tray.agv_id`. A carrying AGV on C14 would be "evicted" with its tray. The narrow fix is right; the AGV under a lowered tray (tray_id 0) stays eligible, which is the common case at Pecos. One addition for parity with validation: `CollectIllegalPosesOfParkedAgvs` should register a carrying AGV with its tray's footprint (`CollisionEntityIdFromTrayState`), not the bare AGV footprint, since validation sees the carried tray as an obstacle at that pose. |
| 2, 3 | **Accepted as a requirement, not as work for this PR.** | The field does not exist on `main`; the mapping of #1031's patch onto the renamed scheduler is Jesse's rebase, and the eviction guard is one line in the blocker loop of whichever PR lands second. The table of decisions is the right contract and goes into the PR text and the notes. |
| 4 | **Accepted.** | The PR text is softened: a disabled AGV, or one carrying a tray, is never moved; low-battery AGVs on the unassignable list will stay put once #1031 lands. |

## Plan

1. **Solution commit (amend):** skip `IsCarryingTray(agv)` in `ResolveByEvictingAgvs`'s blocker loop; in
   `CollectIllegalPosesOfParkedAgvs`, use the carried tray's footprint for a carrying AGV.
2. **Tests commit (amend):** `InsertJob.StallBlockedByLoadedAgvOnCharger`: AGV 1 on C14 with its lift raised
   carrying empty tray 28 (`lift: true`, tray `agv_id: 1`), AGV 2 at P5. Expected: no eviction, AGV 7-style
   stash on W31 by AGV 2, no command for AGV 1, tray 28 untouched; the test asserts the plan executes (so
   validation accepted it) and that the eviction was attempted and declined rather than never reached (the
   stall search must still reject P15: the recording shows the stash, and the resolver stage test covers the
   policy).
3. **PR text:** the sentence on who is never moved; the #1031 contract in "Not in this PR" (exclude from
   carrier choice, hiding and eviction; keep as obstacles; explicit jobs unchanged), and no claim about
   charging-related blockage in general.
4. **Greptile reply** (drafted for the user, who posts it): accepted, fixed in the solution commit, regression
   scenario added.
5. **With Jesse:** send the mapping list of item 3 and offer the guard line; agree that whichever PR lands
   second carries it, with the four integration tests.

## Applied (2026-11-06)

- `ResolveByEvictingAgvs` skips `IsCarryingTray(agv)`; `CollectIllegalPosesOfParkedAgvs` registers a carrying
  AGV with its tray's footprint. `InsertJob.StallBlockedByLoadedAgvOnCharger` recorded: AGV 2 stashes on
  W31, AGV 1 and tray 28 untouched, the plan executes. `scheduler` 202, `planner_core` 24,
  `scheduler_advanced_tests` 15 with recording checks.

## Drafts for the user

**Reply to Greptile's comment on `tray_assignment.cpp`** (the user posts it):

> Right, thanks. An AGV carrying a tray is now skipped as an eviction candidate, so the search keeps the
> waypoint stash, and its tray's footprint counts among the illegal poses the stall search sees. The new
> scenario `InsertJob.StallBlockedByLoadedAgvOnCharger` records it: AGV 1 holds a tray on C14, the car is
> stashed on W31, AGV 1 and its tray do not move. Moving a loaded AGV as a proper tray move is deliberately
> out of scope.

**Note to Jesse (#1031):**

> #1036 and #1031 touch the same scheduler files, but every conflict your branch shows today comes from
> #1018 (the renames and the scheduler.cpp split), not from #1036: a dry-run merge of your branch with mine
> conflicts in the same four files as with main and no other. When you rebase onto the renamed code, the
> mapping is: the request field into `PlanContext::unassignable_agvs`, `DoAgvAssignments` → `AssignAgvs`,
> `PlanCleanGarageJob` / `HideAgvs` → `ExpandCleanGarageJob` / `FindAgvUnderTrayAssignment`. One new
> place needs the list once both are in: the eviction in `ResolveByEvictingAgvs` (tray_assignment.cpp)
> must skip unassignable AGVs as candidates while keeping them as obstacles, otherwise an insert could pull
> a recovering AGV off its charger. Whichever PR lands second carries that line; happy to write it either
> way.
