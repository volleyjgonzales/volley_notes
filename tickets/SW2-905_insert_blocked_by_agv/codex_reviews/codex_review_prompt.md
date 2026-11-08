# Independent review of PR #1036 (SW2-905)

You are reviewing a draft pull request of a ROS 2 (C++20) workspace. Another reviewer wrote the
branch; your value is an independent read, so do not assume anything below is correct because it
is stated here. Verify, and report what you find with evidence.

## Where things are

- Repository: `/home/jon-gonzales/volley`. Branch: `jmg/SW2-905/insert-stall-blocked-by-agv`, four
  commits on base `a468657f` (origin/main). Tip: `2008ca0a`. Review the range `a468657f..HEAD`.
  PR: https://github.com/VolleyAutomation/volley/pull/1036 (draft; read its body, it is the claim
  to check).
- Files: 28. Scheduler library: `src/planner/scheduler/include/scheduler/scheduler.hpp`,
  `src/tray_assignment.cpp`, `src/job_expansion.cpp`. Scheduler tests: `test/src/jobs/insert_job_tests.cpp`,
  nine scenario YAMLs under `test/scenarios/` (four initial states, four insert scenarios, one
  re-recorded tray-assignment stage scenario) and the scenarios README. Test viewer:
  `src/planner/scheduler/tools/plan_viewer/` (Python and JavaScript, 14 files).
- Build tools exist only inside the devcontainer. On this host use the wrapper, never `colcon`,
  `cmake`, `poe` or test binaries directly:
  - `volley-in-container build <pkg>...`
  - `volley-in-container test <pkg>...` (put `SCHEDULER_CHECK_RECORDINGS=1` in front to compare
    the recorded scenarios byte for byte; a clean `git status` under
    `src/planner/scheduler/test/scenarios/` afterwards is the pass criterion)
  - `volley-in-container gtest <pkg> <binary> [filter]`
  - `volley-in-container tidy` (the team's clang-tidy hook on lines changed since main)
  - `volley-in-container sh '<cmd>'` for anything else in the container, including
    `poe scheduler-test-viewer`, which renders the scenarios into `artifacts/scheduler-tests.html`
  Each run prints a summary and saves the full log under `~/.cache/volley-in-container/logs/`.
  If the wrapper reports that the container is not running, stop and say so.
- Do not modify, stage, commit, rebase or push anything. Read-only review; a scratch build and
  test runs are fine. Never run a test binary with `RECORD_REFERENCE_OUTPUT=1`.
- Style configuration: `.clang-tidy`, `.clang-format`, `.commitlintrc.yaml` (conventional
  commits), `prek.toml` (pre-commit hooks: clang-format, black, mypy, yamllint among others). The
  team's review rules are in
  `/home/jon-gonzales/repos/volley_notes/tickets/SW2-482_scheduler_core_refactor/review_rules.md`
  (sections 2, 3 and 7 matter most). The analysis behind the fix, with figures, is in
  `/home/jon-gonzales/repos/volley_notes/tickets/SW2-905_insert_blocked_by_agv/SW2-905_notes.md`;
  read sections 2.5, 2.7, 4 and 7 if you need the planner's vocabulary (keep-out filter, static
  obstacle filter, illegal poses, moving footprint).

## The bug and what the branch claims

A car is inserted in bay B7 of the Pecos layout. Tray assignment chooses the parking stall with a
search whose path filter ignores every AGV and whose acceptance test only rejects stalls holding a
tray, so it picked P15 while an idle AGV charged on C14, a dead-end charger pose 0.6 m from P15.
Validation (`ValidateMoveDestinationAndPath`, which ignores only the carrier) rejected the
destination, every job of the request failed, and the dispatcher dropped the insert with the car
shut in the bay. Read each commit message first (`git log --format='%h %s%n%b' a468657f..HEAD`).

1. `8fa8a934` test viewer: step scrubber, click-to-select, tabs, failed-plan banner, URL hash.
   Tooling only; the author is its only user and it ships here to avoid a second PR.
2. `7cf5f666` tests: `InsertJob.StallBlockedByAgvOnCharger` (the reproduction) and
   `InsertJob.FromBay7StallFree` (the control, C14 enabled and empty: the car parks on P15), plus a
   corrected comment above `ExpectInsert`. In this commit the blocked scenario records today's
   failed plan.
3. `4d7401c7` fix: `ResolveBlockingTrays` gets every enabled non-carrier AGV's pose as an illegal
   parking pose (`IllegalPosesOfParkedAgvs`); tray assignment's working state applies AGV moves;
   `AssignTrays` dispatches on the event type; `RegisterTransition` only records occupancy;
   eight apply blocks share `ApplyToWorkingState`. Claims: the blocked scenario now plans (a stash
   on W31 at that commit); `TrayAssignment.FillsBlankDestination` changes from P2066 to P2062 and
   nothing else changes.
4. `2008ca0a` feat: when the search ends in a waypoint stash, `ResolveByEvictingAgvs` reruns it
   without the AGV poses, finds the AGVs overlapping the stall it would take, sends each to the
   nearest free charger whose occupant would not overlap the stall, reruns the search with the AGVs
   moved, and adds the AGV moves to the DAG before every tray move of the plan. Claims: the blocked
   scenario now parks on P15 with AGV 1 sent from C14 to C16; two new last-resort scenarios stash
   on W31 (no free charger; disabled AGV); nothing else changes; the carrier's approach to the bay
   runs in parallel with the eviction.

## What to review, in priority order

1. **Correctness of the eviction (commit 4).** `ResolveByEvictingAgvs` in `tray_assignment.cpp`.
   Check: the rerun without AGV poses and without a stash really finds the stall the AGV blocks,
   and not a stall blocked for another reason; `chargers_overlapping_stall` uses the charger's
   inbound pose the AGV would actually take; `FindUnoccupiedChargerWithShortestTravelTime` with the
   new exclusion set still serves the charge job unchanged; the AGV move is applied to
   `evicted_state` before the next AGV is placed, so two evicted AGVs cannot take the same charger;
   the final rerun uses the moved poses and refuses a stash; the AGV moves get an edge to every
   tray move of the plan (`AssignDestinationAndUnblockingMoves`), including the blocking-tray
   reparks, and are applied to the stage's working state before them. Then follow the AGV move
   through the later stages: it is a DAG root with no job chain, so check what AGV assignment
   (`ApplyNonTrayRootEvents`, `ChainAgvEvent`, `OrderArrivalAfterPriorOccupant`), validation and
   CHUGG do with it, and whether the action graph assigns it to the insert job correctly. Look
   for a plan that validation would reject: the evicted AGV's path through the stall it frees,
   an AGV parked on C10 blocking W9 for the loaded tray, the evicted AGV being the one AGV
   assignment then picks as carrier.
2. **Correctness of the fix (commit 3).** `IllegalPosesOfParkedAgvs` exempts only the AGV under
   the root tray; is that the right set, and is the AGV footprint against the payload footprint
   the right query compared with what validation asks (AGV against TRAY, via the substitution in
   `BuildStaticObstacleFilter`)? The working state now applies AGV moves: check that applying a
   lift event or a pose move there cannot fail where validation would succeed, and that the
   explicit skip of VRC transitions preserves the old behaviour. Judge the `FillsBlankDestination`
   change: the scenario's only AGV stands idle on P2066 and used to receive the tray; is P2062
   acceptable, and is the explanation in the commit message right?
3. **Behaviour neutrality where claimed.** With `SCHEDULER_CHECK_RECORDINGS=1`, every recording
   other than the five scenarios the messages name must be identical. Run it. Also judge what
   the recordings do and do not guard: CI runs the scheduler tests without the comparison.
4. **Tests.** Are the four insert scenarios and the stage scenario enough? In particular: no
   test exercises two AGVs blocking one stall, an eviction whose charger search fails for path
   reasons, or an eviction inside a blocking-tray recursion. Say which of these deserve a
   scenario and sketch the initial state. Check the assertions of `StallBlockedByAgvOnCharger`
   (AGV 1 must end on node 10 or 16 and move only before the car is parked) against the
   recording, and the `ExpectStashWithoutEviction` carrier argument.
5. **Interplay with open work.** PR #1031 (`jpl/SW2-1164/agv-very-low-soc-charging`, not merged)
   adds `PlanRequest.unassignable_agvs`: AGVs the scheduler must neither assign nor hide. Say
   what the eviction must do with that list once #1031 lands and whether anything in this branch
   makes that harder. The C1 stage of the scheduler refactor
   (`tickets/SW2-482_scheduler_core_refactor/PROMPT.md`, section 5, commit 5) will move
   `ResolveBlockingTrays` into a tray module with the API of section 6.3; say whether the new
   function and the `AgvEvictionPlan` struct fit that API or will need rework.
6. **Naming, comments and C++ rules as the repo applies them.** Functions verb-first, predicates
   `Is*`, optionals `*_opt`, bools `is_*`, no abbreviations; file-local helpers in an anonymous
   namespace. The author wants few comments: flag any comment that restates code, and any place
   where a missing comment leaves a non-obvious rule unexplained. `.clang-tidy` as configured
   (`bugprone-unchecked-optional-access` is disabled for the package on purpose, so check
   `.value()` and `->` on optionals by reading); `const` on every local not reassigned;
   `[[nodiscard]]` on `stdx::Result` / `stdx::Expected` returns (`ResolveByEvictingAgvs` returns
   an optional: should it be marked?); includes in the package's own quotes versus angle brackets,
   nothing unused or transitive. Also the unified failure text of `ApplyToWorkingState`
   ("Failed to apply <event> while assigning trays: <reason>"): is any recording or test relying
   on the old texts?
7. **The viewer commit (commit 1).** Python and JavaScript. Check the hooks' tools pass
   (`black`, `mypy`), that the page renders (`poe scheduler-test-viewer` inside the container,
   then open `artifacts/scheduler-tests.html`), that the scrubber, arrow keys, row click and tabs
   work for a plan scenario and for a failed plan, and that nothing regressed for stage scenarios.
   Keep this to functional defects; design opinions on the page are out of scope.
8. **What Greptile will flag.** The team's experience: Greptile is right about half the time; it
   accepts real defects in error and ordering paths and comment hygiene; it is often wrong about
   ROS and the build. Anticipate its findings on this diff and, for each, say whether it would be
   right, and the one-line answer if not.
9. **Commit messages and PR text.** Conventional-commit headers, lower-case summary, lines of at
   most 100 characters, one topic per commit, and accuracy: does each message describe its diff,
   and are the claims about recordings true?

Out of scope: formatting (clang-format is enforced by a hook), the dispatcher's handling of a
dropped insert (PR #1031 re-queues it while a low-battery AGV charges), the `TRAY`-for-`AGV`
footprint substitution in `motion_planner` (a separate item from the refactor review), and
proposals to extend the eviction beyond chargers (a hiding pose under an empty tray as a second
choice is a known gap, noted in the PR).

## How to report

A ranked list, most severe first. For each finding: severity (defect, behaviour change, rule
violation, nit); file and line at the tip, and the commit that introduced it; what is wrong in
one sentence; the evidence (what you ran or read, with the command or the lines); the proposed
change; and your confidence (confirmed by running, confirmed by reading, plausible). Keep nits
short and grouped. After the list: the Greptile pre-answers (objective 8), then a verdict in two
sentences (ready to leave draft as is, or what must change first), then anything you could not
verify and why. Quote code sparingly; point at lines instead. Do not restate the commit messages
back.
