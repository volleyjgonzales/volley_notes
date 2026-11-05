# Jira work item SW2-1135 for the B2 renames and clean-ups (child of epic SW2-482 Scheduler Core Refactor)

https://volleyautomation.atlassian.net/browse/SW2-1135 (created 2026-10-29). The description below
was rewritten on 2026-10-30 and last updated on 2026-11-02 for what the branch contains at
`a3370c4b`: paste "Scope", "Definition
of Done" and "Out of scope" again, and update the Summary if the ticket still has the first title.

## Title

Rename, clean up and split the scheduler before the tray solver

(The first title, "Rename the scheduler's members, expansion methods and plan context", still
describes the first renames; the branch grew to sixteen commits, squashed to six.)

## How to create and fill the work item

1. Open the epic SW2-482 and, under *Child work items*, click **+** (or **Create** at the top and
   set *Parent* to SW2-482). Work type: **Task**.
2. *Summary*: the title above.
3. *Description*: paste the Markdown under "Description" below. The Jira Cloud editor converts
   pasted Markdown (headings, bullets, code spans); check that the headings came through as
   headings. For the Definition of Done, turn the bullets into a checklist with the editor's
   action-item button.
4. *Assignee*: Jon M Gonzales. *Priority*: Medium. *Labels*: Scheduler_and_Dispatcher (the epic's
   label).
5. *Start date*: the day the branch is opened. *Due date*: the review target.
6. *Development*: the branch is `jmg/SW2-1135/scheduler-renames-and-cleanups` (created from `main`
   at `61e7b0d7` on 2026-10-29); the PR title is
   `[SW2-1135] Rename, clean up and split the scheduler before the tray solver`.
7. *Linked work items*: is blocked by SW2-1126 (merged); blocks SW2-484 (the tray solver builds on
   the renamed context and the stage files).

## Description (paste into the Description field)

## Objective

Give the scheduler the names and the file layout the Scheduler Core Refactor (SW2-482) catalogue
uses, and remove the clutter the refactor would otherwise carry along, before any logic moves:
renames first, then one clean-up per commit, then one file per pipeline stage. The solver work of
SW2-484 then starts from code whose names say what things are, and its diffs show logic changes
and nothing else.

## Scope

Six commits, each one group of related changes, in the `scheduler` package unless said
otherwise. Every recorded scenario of SW2-1126 stays byte-identical; the only behaviour changes
are the bug fixes of commit 4 and the Eccles removal of commit 6, listed under Definition of Done.

- Renames: `Scheduler` members and the `Plan<Type>Job` methods (to `Expand<Type>Job`);
  `ScheduleContext` to `PlanContext` in `plan_context.hpp` with its fields and methods; methods
  named verb first for what they do (`AssignTrays`, `AssignAgvs`, `BuildActionGraph`,
  `Compute*Duration`, and others); every bool with an `is_` prefix; a name that needed a comment
  to explain it says it itself. Callers in `scheduler_ros.cpp`, the tests and the plan viewer
  follow.
- Narration logging removed (INFO, DEBUG and per-attempt WARN); comments reduced to the reason;
  commented-out code and stale TODOs deleted.
- Dead code deleted and `BoolStringPair` replaced by `stdx::Expected` / `stdx::Result` throughout;
  no method with more than five parameters.
- `scheduler_msgs.hpp` deleted: fully qualified message types and per-file message includes
  (`agvhito_tools`' move planner adjusts one include).
- `planner_core`: the event DAG and schedule event APIs renamed (`Dag`, `GetNode`, `GetEvent`,
  `RemoveRedundantEdges`, `ApplyEventsTo`, `ApplyTo`) and their unused parts deleted;
  `motion_planner` follows the `ApplyTo` rename.
- Repeated event-building sequences extracted into helpers; long functions split into named
  methods; error texts built with `std::format`, every string unchanged.
- Bugs found during the refactor fixed, in one commit, each with its reachability stated.
- `scheduler.cpp` split into `job_expansion.cpp`, `tray_assignment.cpp`, `agv_assignment.cpp`,
  `validation.cpp` and `action_graph.cpp`, no function body changed; `JobFailure` and `Fail` in
  `job_failure.hpp`.
- Scheduler-local heading helpers (`ReverseHeading`, `ReversePoseHeading`,
  `IsSameOrOppositeHeading`) in place of common's reciprocal functions.
- The `576_eccles` EV-charging heading exception removed with the four advanced tests that ran on
  Eccles layouts (decommissioned site).
- Follow-ups from the independent reviews: the unused reverse-heading mode of ExpandAgvMoveJob
  deleted; action-graph failures reported with specific errors (`stdx::Expected` /
  `stdx::Result`); the repark destination validated after its heading is final.

## Definition of Done

- `poe test-pkg scheduler` passes, and `SCHEDULER_CHECK_RECORDINGS=1 poe test-pkg scheduler` passes
  with every recording identical (the scenario files' authored `scheduler:` key is renamed).
- `planner_core`, `motion_planner`, `scheduler_advanced_tests` and `agvhito_tools` build and pass.
- Behaviour changes are limited to commit 4 and listed in its message and the PR: a failed job
  reported once; the advance move's path and single apply, and a failed unblocking apply failing
  the tray assignment; the reverse-heading destination; the empty-optional read in
  `ExpandReparkTrayJob`; `ExpandAgvMoveJob` keeping the heading only; the stop-charging event
  chained after the charger's previous event; a failed expansion leaving no events behind;
  non-finite readiness ratios rejected; failures propagated from the AGV move duration and the
  state replay instead of zero or a partial state; a repark reading the tray's planned pose; an
  AGV already on its charger recognised (wrapped inbound heading); occupancy errors propagated in
  tray assignment; jobs returned in request order; a missing keep-out filter reported as such; a
  cycle in the AGV pickup order failing the plan instead of throwing; four failure texts rewritten
  as whole sentences; one error-string space; 35 error and log texts that named functions that no
  longer exist reworded, the 13 replay failures among them sharing one text. Commit 6 removes the
  Eccles heading exception. Each states which recorded
  scenario reaches it or that no input does today.
- No other error string changed (`MakeFailedJob` messages are client-visible); commit 4's message
  lists the ones that did.
- `rg` finds no use of the old names in `src/planner/scheduler/`, error and log texts included.
- The pre-push clang-tidy hook is clean on the changed lines; prek hooks pass.
- Each commit is one group of related changes, named for what it does, with the reason in its
  body; the bug fixes are a commit of their own.

## Out of scope

- Free-function job expansions and a `GarageServices` struct: SW2-484, phase C1.
- The clean-ups in `motion_planner` and `cost_functions` that the scheduler would profit from
  (pose-based blocking-tray searches, `BuildKeepOutFilter`, `ComputePathDuration`, optional
  returns, typed durations): a work item of their own before SW2-484, listed in the stage notes.
- The ROS-boundary types (`AssetId`, `ros/convert`, `ScheduledJob`, a `Timepoint` constructor,
  `ReserveBaseScheduleAssets`): later work items.
- Any further change in planning output: a later ticket with a re-recording.

## Review

Read commit by commit; each message says what changed and why it is behaviour-neutral, and commit
4 says what it changes. The two test runs (plain and with the comparison on) and a clean
`git status` under `test/scenarios/` are the evidence. For the split commit, `git diff
--color-moved=dimmed-zebra` shows the moves; `git blame -C -C -C` follows them.
