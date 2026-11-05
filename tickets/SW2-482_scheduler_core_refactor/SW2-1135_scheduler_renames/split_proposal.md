# Proposal: split scheduler.cpp by pipeline stage (commit 11 of stage 2)

Written 2026-10-30 on `jmg/SW2-1135/scheduler-renames-and-cleanups` at `cb8a8b0d`. **Applied the same
day:** section 5 folded into commits 3 to 10 (TODOs and the step labels kept), sections 1 to 4 as
commit 11 `aa651a6f`; see `code_notes.md`, "Comment clean-up and the stage split".

`scheduler.cpp` is 3251 lines: 455 lines of file-local helpers, then the `Scheduler` members in
roughly historical order. `Plan()` already runs the pipeline as five stage calls (job expansion,
tray assignment, AGV assignment, validation, motion planning + action graph), and `PROMPT.md`
section 9 (C0) names the folders those stages end up in: `task_planning/job_expansion/`,
`task_planning/tray_assignment/` (C1/C2), `task_planning/agv_assignment/` (F), `validation/`,
`motion_planning/`, `action_graph/`. The design review (DESIGN-REVIEW.md row 106) dropped stage
folders and per-stage targets *for the solver PR*; it did not rule out one translation unit per
stage, which is the cheap half of C0: no new targets, no new namespaces, no include-boundary check,
every function keeps its body and its `Scheduler::` prefix.

## 1. What moves where

One `.cpp` per stage under `src/`, flat (the C0 folders come with their targets; a flat file moves
into its folder in one `git mv` later). Same header, same library target: `CMakeLists.txt` lists
the new sources, nothing else changes. Sizes are from the current function map and approximate.

| file | ~lines | members and file-local helpers |
|---|---|---|
| `src/scheduler.cpp` | 390 | constructor, `InitRetrievalHeadings`, `Plan`, `ExpandJob`, `PlanMotions`, `MakeFailedJob`, `SetBayReadinessRatioCallback`; the layout queries several stages share: `GetBayInboundPose`, `IsBayOdpAreaClear`, `IsPlainParkingSpot`, `GetFirstSystemFloor` |
| `src/job_expansion.cpp` | 880 | the twelve `Expand*Job`, `ApplyReparkHeadingPreference`, `CheckReparkDestination`, `AddBayTransitionToRetrieve`, `ReparkWaypointStashedTrays`, `AssignTraysToBayFillMoves`, `DoesPayloadFitBay`, `FindBayForRetrieve`, `FindNearestFreeCharger`; file-local `MakeBayCommand` + the two placeholder-id constants, `IsEvChargeRequested`, `OrderAfterBayAndChargerEvents`, `UnplugEvChargerBeforeTrayMove` |
| `src/tray_assignment.cpp` | 780 | `AssignTrays`, `AssignDestinationAndUnblockingMoves`, `ResolveBlockingTrays`, `FindDestinationForRootTray`, `FindBlockingTrayResolution`, `BuildImmobileTrayFilter`, `ApplyTransitionAndRegisterOccupant`, `PickEmptyTrayForMove`, `OrderAfterFreeingMoves`, `FindUsableDestination`, `ComputeTrayCollisionId`, the three heading methods (`ApplyPreferredHeading`, `ApplyEvChargeHeading`, `ApplyRetrievalHeading`: their C1 home is `tray_assignment/headings`); file-local `ChainTrayEvent` |
| `src/agv_assignment.cpp` | 860 | `AssignAgvs`, `ApplyNonTrayRootEvents`, `ComputeAgvAssignmentEdgeCosts`, `AssignAgvToTrayMove`, `AppendAgvMoveToTrayEvent`, `AppendAgvLiftEvent`, `OrderAfterTraysOnPath`, `OrderArrivalAfterPriorOccupant`, `PropagateEarliestStartToChildren`, `FindAgvsAtPickupPose`, `BuildAgvOrderDag`, `FindAgvDepartureFromNode`, `OrderAgvMoveAfterBlockerDeparture`, `RunAgvPathRepairPass`, `RepairAgvMovePaths`, `OrderAllTransitionsAroundAgvLifts`, `OrderTransitionAroundAgvLifts`, the five `Compute*Duration` / `ComputeAgvAssignmentCost`; file-local `ChainAgvEvent`, `PickupHeading`, `ComputeStateBefore`, `FindAgvLiftChange`, `kMaxAgvPathRepairPasses` |
| `src/validation.cpp` | 120 | `SanityCheckEvents`, `CheckMovePossible` (its only caller) |
| `src/action_graph.cpp` | 400 | `BuildActionGraph`; file-local `IsLiftedMotion`, `ToActionNode`, `CollectAndCollapseTrajectoryMotions`, `BuildActionDagFromMotions`, `TransferEventDagDepsToActionDag`, `BuildScheduledActionsArray` |

Helpers that two stages share leave the anonymous namespace, unchanged in body:

- `Fail` / `RetryableFail` (job expansion, `ExpandJob`, `AssignTraysToBayFillMoves`) go with the
  struct they build into a new `include/scheduler/job_failure.hpp` (namespace `volley::scheduler`,
  included by `scheduler.hpp`). `JobFailure` moves out of `scheduler.hpp` with them.
- `MakeVecsStateChange` (job expansion, action graph), `MakeAgvPoseChange` (job expansion, AGV
  assignment), `MakeTrayMove` (job expansion, tray assignment) and `KeepTrayHeadingIfEquivalent`
  (job expansion, tray assignment) go to `utils.hpp` / `utils.cpp`, next to `IsCarryingTray` and
  `HasPayload`. C1 takes `KeepTrayHeadingIfEquivalent` into the headings module from there.

Every other helper is used by one stage and moves with it. `PrintDagIfEnabled` stays a template in
the header.

Optional, same commit: reorder the declarations in `scheduler.hpp` into the same six groups with a
one-line `///` heading each, so the header reads in the order of the files. It is a pure move in
the header, but it makes that file's diff all noise; a separate `docs`-type commit, or leave it.

## 2. Why this is the right intermediate step

- Each stage's file is now the unit C0, C1 and F start from: C1 carves the solver out of
  `tray_assignment.cpp` alone; F does the same to `agv_assignment.cpp`; C0 moves files into
  folders and adds targets without touching function bodies.
- Reviewers of the solver PR read a 780-line tray file instead of a 3251-line one.
- The move is verifiable to the byte: every recording must match (`SCHEDULER_CHECK_RECORDINGS=1`),
  and `git diff --color-moved=dimmed-zebra` shows the commit as moves only, with the new includes
  and the two header changes as the only "real" lines.
- `scheduler_advanced_tests`, `scheduler_ros.cpp` and `scheduler_component.cpp` include
  `scheduler.hpp` only; nothing outside the package notices.

## 3. Risks and what to check

- **clang-tidy on whole files.** The pre-push tidy hook analyses lines changed since `main`; every
  line of a new file counts, so the move exposes old code that the branch never touched (the
  previous commits only touched the lines they changed). Expect findings. Fix the trivial ones in
  the same commit and say so in the body; anything larger is a follow-up with a ticket, not scope
  creep in a move commit.
- **Blame.** `git log --follow` does not follow a split; `git blame -C -C -C` does. Worth a line in
  the PR body.
- **Include lists.** Each new file gets only what it uses (the rule: package headers in quotes,
  others in angle brackets, groups sorted). `scheduler.cpp`'s 47 includes shrink; the stage files
  get `"scheduler/scheduler.hpp"`, `"scheduler/format.hpp"` and their own.
- **Order of definitions inside a file** is free to change at a move, but keep each stage's
  functions in the order the header declares them; it is what a reviewer diffs against.
- **The header's one-responsibility rule** (section 7) is not satisfied by this commit: `Scheduler`
  still declares everything. That is C0/C1's job; the commit body should say the header is
  unchanged on purpose.

## 4. Commit

Last on the branch (commit 11), after the fix commit, so the earlier diffs stay readable:

```
refactor(scheduler): split scheduler.cpp into one file per pipeline stage

Moves the Scheduler members and file-local helpers of scheduler.cpp into
job_expansion.cpp, tray_assignment.cpp, agv_assignment.cpp, validation.cpp
and action_graph.cpp, one per stage of Plan(); scheduler.cpp keeps the
constructor, Plan(), ExpandJob(), PlanMotions() and the layout queries
several stages use. The helpers two stages share move to utils.hpp
(MakeVecsStateChange, MakeAgvPoseChange, MakeTrayMove,
KeepTrayHeadingIfEquivalent) and to the new job_failure.hpp (JobFailure,
Fail, RetryableFail). No function body changes; the header is unchanged
apart from the JobFailure move. The recorded scenarios are unchanged.
```

Checks before the amend-free commit: build 0 warnings, scheduler 188 both ways with a clean tree
under `test/scenarios/`, planner_core and scheduler_advanced_tests, prek on the touched files,
`volley-in-container tidy` (see 3), `git diff --color-moved` read once end to end.

## 5. Comments to remove or shorten (review against review_rules.md sections 2 and 7)

Scan by a subagent over the eight touched headers and sources, spot-checked here. No commented-out
code, no debug output. 54 items: 31 delete, 12 shorten, 6 `TODO(any)` without a Jira key, 5
style or placement fixes. "new" = added or reworded on the branch.

### Style and placement (5)

- `scheduler.cpp` 67, 73, 130, 162, 175, 186: the new file-local helpers use `///`; everything
  else in the file is `//`. Use `//` (anonymous namespace, not API docs). Commit 9.
- `scheduler.hpp` 58, 71-72, 79-80, 106: `//` docs on struct members in a file whose class docs
  are `///`. Make them `///`. Commit 5 / 6 (where the structs got their docs).
- `scheduler.hpp` 282 "Finds a destination via ResolveBlockingTrays and adds its unblocking moves"
  sits on `OrderAfterFreeingMoves`; it describes `AssignDestinationAndUnblockingMoves` (312, no
  doc). Move it there. Commit 9.
- `utils.hpp`: three styles (`//`, `///` at 25, `//!` at 68 and 73). Use `///` for every
  declaration doc. Commit 9 (where 25 was added).
- `utils.hpp` 36-41: clang-format split the trailing enum comments so each second half reads as
  the next enumerator's doc. Put each comment above its enumerator. Commit 3.

### Delete (restates the code, narrates the next lines, or duplicates a header doc)

- `event_dag.hpp` 219 "Vertices without children", 230 "Vertices without parents", 301 "Prints
  the DAG in dot format to the log" (new, commit 8).
- `schedule_events.hpp` 41 "Changes `state` as this event would" (new); 89-90, 127-128, 151,
  156-157, 177, 212 (pre-existing restatements of the class or member names; commit 8).
- `scheduler.hpp` 299 (PrintDagIfEnabled, body is three lines below), 334 (ComputeAgvMoveDuration),
  362 (PropagateEarliestStartToChildren), 424 (CheckMovePossible, or `/// The destination is
  enabled and reachable.`).
- `scheduler.cpp` 522 (restates the early return), 1002 ("consider adding a transition": a
  keyless TODO in disguise), 2096-2097 (floating; duplicates RepairAgvMovePaths' header doc),
  2141 and 2149 ("Move any empty tray" / "Move specific tray anywhere": the `if` says it), 2225
  (restates the lambda's name), 2306 ("entirely sequential": narrates the loop), 2489 (duplicates
  ComputeAgvPickupDuration's doc), 2690, 2753 (keep 2754, the why), 2794-2795 ("end for" / "end
  while"), 2797-2798 (restates RepairAgvMovePaths' doc), 2945 ("This shouldn't really happen"),
  3104 (restates the ternary), 3144 (describes the alias at its use).
- `utils.cpp` 135 ("Clamp in case"), 138 (restates `std::min` and the header doc), 319 (bug-fix
  history; floating).

### Shorten (keep the why, drop the rest)

- `schedule_events.hpp` 59-60 → "A lift/lower, or a move whose path is left to the motion
  planner."; 181-182 → "Keeps the from/to VRC nodes so the discrete simulation can move the
  entities riding the VRC."
- `scheduler.hpp` 237 → the precondition it records: "Needs AGV assignment done: the lifts are
  reached through the parent tray moves' AGVs."
- `scheduler.cpp` 466 → "Written back to ctx->scheduled_jobs once done." ("refs didn't compile" is
  history); 1408 → "Hard-coded for the headquarters EV-charging demo." (the design-discussion
  recap goes to the notes); 1792 → "The path may still not exist." ("MVP 454" is an old ticket);
  2673-2674 → "The order changed, so every later occupancy is stale."; 2677 → "ApplyTo only
  updates positions for these events."
- `utils.hpp` 34-35: drop "Currently, we don't use this" (history); 63 → "The overload the
  Scheduler calls."

### Judgement calls (user decides)

- The six `TODO(any)` (scheduler.cpp 645, 689, 1626, 2241, 2453, 3221) are the branch's rewording
  of base TODOs; section 2 says a TODO carries a ticket key or goes. 689 (fail the job instead of
  reporting it executing) and 3221 (strip a failed job's partial events) are the two known bugs
  of item 204: they deserve tickets, then `TODO(SW2-xxxx)`. 645 (RemoveRedundantEdges placement),
  1626, 2241, 2453 are design notes: a key each, or delete and keep the text in the notes.
- `utils.cpp` 161-240, the six numbered step labels of ComputeBayRebalancingActions: they narrate
  the loops, but the why at 173-174 refers to them by number and the function is 100 lines.
  Recommendation: keep; strict reading of the rule says delete and reword 173-174.

### Where to fold them

Pre-existing comments into commit 3 (`3431e97f`, "remove narration logging and condense
comments"), planner_core headers into commit 8, the new ones into the commit that added them
(mostly 9), by the same exec-amend rebase as the review fold-in; or, if the sequence matters less
than the effort, one `docs(scheduler): cut restating comments` commit before the split (the split
then moves the cleaned text). Either way the recordings cannot change; build and tests prove the
move.
