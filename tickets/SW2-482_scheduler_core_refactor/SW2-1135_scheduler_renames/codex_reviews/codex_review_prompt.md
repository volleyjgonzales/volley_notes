# Independent review of the SW2-1135 branch

You are reviewing a branch of a ROS 2 (C++20) workspace before it becomes a pull request. Another
reviewer has already worked on it; your value is an independent read, so do not assume anything
below is correct because it is stated here. Verify, and report what you find with evidence.

## Where things are

- Repository: `/home/jon-gonzales/volley`. Branch: `jmg/SW2-1135/scheduler-renames-and-cleanups`,
  six commits on base `f3fa775f` (origin/main). Tip: `a3370c4b`. Review the range
  `f3fa775f..HEAD`.
- Packages touched: `src/planner/scheduler` (54 files), `src/planner/planner_core` (7),
  `src/planner/scheduler_advanced_tests` (7), `src/planner/motion_planner` (2),
  `src/agvhito_tools` (1).
- Build tools exist only inside the devcontainer. On this host use the wrapper, never `colcon`,
  `cmake` or test binaries directly:
  - `volley-in-container build <pkg>...`
  - `volley-in-container test <pkg>...` (add `SCHEDULER_CHECK_RECORDINGS=1` in front to compare
    the recorded scenarios byte for byte; a clean `git status` under
    `src/planner/scheduler/test/scenarios/` afterwards is the pass criterion)
  - `volley-in-container gtest <pkg> <binary> [filter]`
  - `volley-in-container tidy` (the team's clang-tidy hook on lines changed since main)
  - `volley-in-container sh '<cmd>'` for anything else in the container
  Each run prints a summary and saves the full log under `~/.cache/volley-in-container/logs/`.
  If the wrapper reports that the container is not running, stop and say so.
- Do not modify, stage, commit, rebase or push anything. Read-only review; a scratch build and
  test runs are fine.
- Style configuration: `.clang-tidy` (bugprone, cppcoreguidelines, clang-analyzer, google,
  modernize, readability-identifier-naming, with the listed exceptions and their reasons),
  `.clang-format`, `.commitlintrc.yaml` (conventional commits), `prek.toml` (pre-commit hooks).
  The team's distilled review rules from the previous PR are in
  `/home/jon-gonzales/repos/volley_notes/tickets/SW2-482_scheduler_core_refactor/review_rules.md`
  (sections 2, 3 and 7 matter most); the house rules are summarised below in case you cannot read it.

## What the branch claims

Read each commit message first (`git log --format='%h %s%n%b' f3fa775f..HEAD`); the messages are
the claims to check.

1. `dea3336a` rename, trim and simplify the scheduler (member, method, PlanContext and bool
   renames; narration logging and comments; dead code, BoolStringPair to stdx::Expected,
   parameter structs)
2. `9912b70f` planner_core event DAG and schedule event API renamed and trimmed; message headers
   per file (scheduler_msgs.hpp deleted)
3. `c2c5ea9b` extract repeated event-building patterns; std::format error texts
4. `04ff7dc2` fix bugs found during the refactor (the intended behaviour changes)
5. `c821cab0` split scheduler.cpp into one file per pipeline stage; scheduler-local heading helpers
6. `a3370c4b` remove the Eccles EV-charging heading exception and its advanced tests, the unused
   reverse-heading mode of ExpandAgvMoveJob and the generic action-graph failures; validate the
   repark destination after its heading is final

Claimed invariant for commits 1, 2, 3 and 5: no change in planning behaviour, every recorded
scenario identical, every error string unchanged. Commit 4 lists its fixes with their reachability
and says the recordings are unchanged; commit 6 changes behaviour only on Eccles layouts and adds
new action-graph failure texts.

## What to review, in priority order

1. **Behaviour neutrality of the refactor commits.** For each commit except 10, look for any
   semantic change hidden in a rename, extraction or simplification: changed evaluation order,
   a condition negated the wrong way, a copy that became a reference to something that mutates,
   an `std::tie` reassignment turned into an `if` initializer that now shadows or narrows a scope
   the later code relied on, a deleted "dead" branch that a caller outside the package reaches,
   a removed log statement whose argument had a side effect, an API deletion in planner_core
   that another package used. Spots worth a careful read: `ChainAgvEvent` (writes the AGV's
   last event before `OrderArrivalAfterPriorOccupant` reads the map), `OrderAfterPriorOccupants`
   (skips the event itself), `AddChainedEvent` chaining before `ApplyTo` at the charge-job bay
   transition, the `Plan()` failure lambda, the split's per-file include lists, and the
   `ApplyPreferredHeading` tray parameter removal.
2. **Commit 4.** Verify each fix is correct and complete, that its stated reachability is true
   (which recorded scenario reaches it, or that no input can), and that it introduces no
   regression. Judge whether the one new test (`RetrieveJob.FailedJobReportedOnce`) is enough and
   which fixes deserve a scenario of their own.
3. **Naming against the house rules.** Functions start with a verb; predicates `Is*`; optionals
   `*_opt`; `_or` for an Expected; bools `is_*`; no abbreviations (`recip`, `vert`, `env`, `cfg`);
   file-local helpers and constants in an anonymous namespace, `kCamel` constants; no misleading
   `Get` that computes or mutates; parameter and local names that say what they hold. Flag names
   on the branch that still mislead, and names the branch introduced that break a rule.
4. **Comments.** A comment says the why, in a line or two; delete anything that restates the code,
   narrates the next lines, carries history or PR discussion, or cites precedent; `///` on
   declarations, used consistently per file; no commented-out code; `TODO`s carry a key. Known and
   accepted: six `TODO(any)` lines were left on purpose, and the numbered-step labels in
   `ComputeBayRebalancingActions` were removed. Report what is still too much or now too little
   (a non-obvious reason that was deleted).
5. **C++ rules as the repo applies them.** `.clang-tidy` as configured; `const` on every local not
   reassigned, by reference when only read; `[[nodiscard]]` on functions returning
   `stdx::Expected` / `stdx::Result`; `.value()` / `has_value()` / `->` only after a check (note:
   `bugprone-unchecked-optional-access` is disabled for the package on purpose, so check by
   reading); `std::format` for every message, `== nullptr` for pointer checks; includes: the
   package's own headers in quotes, others in angle brackets, groups sorted, nothing unused,
   nothing relied on transitively; one responsibility per header; no `using volley::X` inside
   namespace `volley`; no locals named like an enclosing namespace. Also check the new
   `job_failure.hpp`, `format.hpp` and the `std::formatter` specialisations for correctness and
   ODR safety.
6. **What Greptile will flag.** The team's experience with Greptile on the previous PR: it is
   right about half the time; it accepts real defects in error, reconnect and race paths, process
   findings and comment hygiene; it is often wrong about ROS and the build. Anticipate its
   findings on this diff and, for each, say whether it would be right, and the one-line answer
   if not (intentional design and why, out of scope plus ticket, repo convention it does not know).
7. **Commit messages and PR text.** Conventional-commit headers, lower-case summary, lines of at
   most 100 characters, objective register, one topic per commit, and above all accuracy: does
   each message describe its diff, and are claims like "every string unchanged" and "no function
   body changes" true? Check the split with
   `git diff --color-moved=dimmed-zebra b540d866..3a2ba375`.
8. **Tests.** Does the branch's test coverage match its claims? Note that CI runs the scheduler
   tests without the recording comparison (invariants only), so say what the recordings guard
   and what they do not.

Out of scope, do not spend time on: formatting (clang-format is enforced by a hook), proposals
to extend the refactor (free-function job expansions and the motion_planner / cost_functions API
clean-ups are planned as later work), and the ROS node code.

## How to report

A ranked list, most severe first. For each finding: severity (defect, behaviour change,
rule violation, nit); file and line at the tip, and the commit that introduced it; what is wrong
in one sentence; the evidence (what you ran or read, with the command or the lines); the proposed
change; and your confidence (confirmed by running, confirmed by reading, plausible). Keep nits
short and grouped. After the list: the Greptile pre-answers (objective 6), then a verdict in
two sentences (mergeable as is, or what must change first), then anything you could not verify
and why. Quote code sparingly; point at lines instead. Do not restate the commit messages back.
