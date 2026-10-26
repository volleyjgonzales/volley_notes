# Claude Code prompt: scheduler core refactor (SW2-484), the tray solver

> **How to use this file.** Installed by `claude-setup/install.py` at
> `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/PROMPT.md`. See "Running the refactor" in `HOW-IT-WORKS.md`. In short: open `~/volley` in the
> Code tab of the desktop app (local session, Worktree off, Accept edits) with the devcontainer running.
>
> 1. **Design review (Phase R)**: done on 2026-10-22; the user's answers to its questions are at the end of
>    `DESIGN-REVIEW.md` next to this file. The survey is in the notes file. This file is the plan that came
>    out of it.
> 2. **Implementation**, in a new session, after the user approves the plan:
>    `Read the file /home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/PROMPT.md and the notes file, then start commit 1.`
>    Claude prepares one commit at a time and stops before committing so you can review it (rule 12).

---

## 1. Your role and the goal

You are implementing the first part of the **scheduler core refactor** in the `scheduler` ROS 2 package
(C++20, colcon, GoogleTest). The goal of this PR is Jira **SW2-484**: put tray assignment behind a
generic, swappable solver interface. You will also do the preparatory work the interface needs:

- parity references for the existing planning tests;
- the renames of stage B2 that the user kept: `Scheduler` members, the expansion methods, and the
  per-call context with its fields;
- pure helper functions in a tray-assignment module with its own library target;
- one merged copy of the move-emission code.

The work runs through stages **A**, **B2**, **C1** and **C2** of the plan in section 5 (eight commits).
The ROS-boundary types of the old stage B2 (`AssetId`, `ros/convert`, `ScheduledJob`, a `Timepoint`
constructor, `ReserveBaseScheduleAssets`, the `common_ros` vocabulary aliases), stage folders for the other
pipeline stages (C0), AGV assignment (F), the benchmarks (G), the final cleanup (H) and the `planner_core`
renames (I) come in later PRs. Section 9 lists them so that you can see where your work leads. **Do not
start them.**

**Objectives**, in priority order. They override anything later in this file that conflicts with them.

1. **A swappable tray-assignment solver** (SW2-484), testable without a `Scheduler` or an event DAG.
   The solver's input does **not** include the event DAG: it takes plain data (section 6.3).
2. **A small code footprint.** Fewer lines are better than more, but never at the expense of
   readability. Delete code freely. Don't add scaffolding, abstraction layers, helper types, scripts
   or build targets that nothing in this PR needs; a design for later stages must not cost lines now.
3. **Modern, standard C++.** C++20 as supported by GCC 13 on Ubuntu 24.04. Use the standard library
   where it fits: `<algorithm>` and `<ranges>`, `std::span`, `std::optional`, `std::variant`,
   `std::string_view`, `<format>`, designated initializers. No C++23 features (`std::expected` is
   C++23, so keep using `stdx::Expected` / `stdx::Result`).
4. **At most 10 commits** for this initial phase, each compiling, passing, and with one scoped
   objective. The plan uses eight.
5. **Parity as the default, not an absolute.** The team wants to move fast on improving quality.
   Preserving behaviour is the goal, but a *deliberate* behaviour change is fine when it makes the code
   simpler or fixes a known problem (rules 1, 3 and 6 say how). An *unexpected* difference in planning
   output is always a defect in your change.

The single most important rule:

> After every commit, the package builds, every existing test passes, and every reference output
> matches, except outputs that commit deliberately re-records (rule 6).

**Reference outputs.** Every planning test (a test that calls `Scheduler::Plan`, `DoTrayAssignments` /
`AssignTrays` or `DoAgvAssignments`) ends by comparing a canonical description of its result with a
recorded file, `test/reference/<Suite>.<Name>[.<suffix>].yaml`, recorded once by the first commit on code
that is still identical to the branch point. The test's own inputs (inline YAML state, jobs, hand-built
events) are the fixture; there is no separate input file.

A reference output records **today's behaviour, including its bugs**. It is not ground truth. It
changes only when a commit changes behaviour on purpose, and then the diff of each reference file shows
reviewers exactly which behaviour changed, so keep the format easy to diff (rule 6).

The PR must be reviewable as a **sequence of at most 10 commits** (the table in section 5), and each
commit must:

- have **one scoped objective**, stated in its title;
- compile;
- pass all tests;
- pass the parity check.

Reviewers will read it commit by commit.

## 2. Reference material

- **This plan's review:** `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/DESIGN-REVIEW.md`: what changed from the original plan and why, the
  parity decisions, and the user's answers to the open questions.
- **The notes file** (rule 11): `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/SW2-482_notes.md`. It holds the Phase 0 survey: the baseline
  numbers, where every symbol is, the assumption checks, and a list of bugs found but not fixed (B1 to
  B11). Read it at the start of every session.

A study pack documents the current code and the original design in detail. It is at `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/scheduler_package`.
The chapters were converted to Markdown in `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/scheduler_package/md/`; `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/scheduler_package/md/INDEX.md` lists every heading with its
file and line number, so read a section with `Read` and an offset instead of a whole chapter.

- **How tray assignment works today** (read when you touch the loop): `md/03-task-planning.md`, section
  "Tray assignment: `DoTrayAssignments`" (line 667 onwards).
- **Original design** (for background; this file supersedes it where they differ):
  `md/07-issue-and-proposal.md`, sections "Proposed layout and API for the assignment stages", "Renames in
  `scheduler`", "Key invariants to maintain", "Risks that must not be silently fixed".
- **Verification ideas:** `md/08-verification.md`, "Compare meaning, not pointers or GUIDs".
- **Background on the classes** (`ScheduleContext`, `ScheduleEventDag`, `GarageGraph`, `CollisionTable`,
  `DiscreteGarageState`): `md/01-background.md` and `md/02-layout-file.md`.
- **Code snapshots:** `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/scheduler_package/sources/repomix-*.xml`. The scheduler snapshot is
  byte-identical to the branch at `703bfe7c` except `package.xml`, so the study pack's `scheduler.cpp`
  line numbers are valid there. Still find code by symbol name: the numbers shift after commit 2, and the
  names after commits 2 and 3.
- Use only `md/`, `sources/`, `examples/`, `README.md` and, as a fallback, `site/src/`. The slide deck
  (`deck/`), the SVG figures (`figures/`), the diagram scripts (`scripts/`) and the rest of `site/` repeat
  the same content or are build tooling; they are blocked for reading.

Where this prompt and the study pack disagree, this prompt wins. Where either disagrees with the **actual
code on the branch**, the code is the truth: stop and report the difference (section 3, rule 10).

## 3. Ground rules (apply to every commit)

1. **Parity by default.**
   - Planning output does not change, except through a deliberate behaviour change (rule 3).
   - Error message text does not change unless that is the deliberate change: it reaches clients
     through `FailJob`. The notes file lists every tray-assignment error string. **This includes error
     strings that spell a method name** (for example `"PlanReadyForInsertJob Failed to apply event: "`):
     when the method is renamed, the string stays.
   - Log text may change where the code that prints it is rewritten.
2. **Scope.** Change only the `scheduler` package.
   - **Do not modify** `common_ros`, `interfaces`, `motion_planner`, `cost_functions`, `task_planner`,
     `common`, `stdx`, `planner_core`, `site_config` or `scheduler_advanced_tests`.
   - Use `common_ros` names as they are (`GarageGraph`, `CollisionTable`, `CollisionEntityId`, …). No
     alias header in this PR.
3. **Behaviour changes are deliberate, never incidental.** A change in planning output is allowed only
   when it is:
   - listed in section 8 as **fix**, or proposed at a review gate and approved by the user;
   - in its own commit, or clearly separated inside one, never mixed silently into a refactor;
   - accompanied by re-recorded reference outputs in the same commit (rule 6), with the commit body and
     the notes file explaining what changed and why.

   If you find a bug that isn't in the plan, write it down in the notes file with a reproducing test
   marked `DISABLED_` if practical, and propose the fix at the next review gate. Don't fix it silently.
4. **One scoped objective per commit.**
   - Follow the commit table in section 5. A commit groups several steps that serve one objective; it
     never mixes unrelated goals.
   - Keep renames and moves free of logic changes. A function that moves out of `Scheduler` into the
     module keeps its body; the commit body lists what did change inside it (signature, services, return
     type, nothing else where possible), so reviewers can read the two side by side.
   - Build and test at each step boundary inside a commit, so a failure is easy to locate; commit once
     the whole objective is done and green.
   - If a commit gets too large to keep green or to review, split it at a step boundary and say so in the
     review packet. Commits 3 and 8 have named split points.
   - If you notice something else worth doing, note it and keep going.
5. **Every commit compiles and passes.** Before each commit:
   - build `scheduler` and its tests;
   - run the scheduler tests (which include the parity references);
   - run `planner_core` and `scheduler_advanced_tests` at the end of commits 1, 3, 5 and 8, or more often
     if you touched anything they see (`scheduler_advanced_tests` sees only `Scheduler(layout, logger,
     params)`, `SchedulerParams::bay_readiness_ratio` and `Plan()`).

   You run on the host; the toolchain is in the devcontainer. Run every build and test through the
   `volley-in-container` wrapper described in `CLAUDE.local.md`. It prints a short summary and keeps the
   full log on disk:
   ```bash
   volley-in-container build scheduler scheduler_advanced_tests
   volley-in-container test scheduler
   volley-in-container test planner_core scheduler_advanced_tests
   ```
   `test` prints `colcon test-result` per package. A green build does not mean the tests ran: check the
   test counts in that summary (baseline: scheduler 76, planner_core 23, scheduler_advanced_tests 16, as
   `colcon test-result` counts them). One test binary can be run directly, for example
   `volley-in-container gtest scheduler scheduler_tests 'Scheduler.AmigaStash'`.
6. **Reference outputs and test data.**
   - Record reference outputs only through `volley-in-container record-reference scheduler <binary>` (it
     sets `RECORD_REFERENCE_OUTPUT=1` and asks the user for approval; the wrapper refuses that variable in
     any other command). Three binaries hold planning tests: `scheduler_tests`, `scheduler_jobs_tests`,
     `scheduler_insert_orientation_tests`. Recording happens in commit 1, and again only in a commit that
     makes a deliberate behaviour change (rule 3). Never re-record to make an unexpected difference go
     away.
   - Every test data file you add is YAML with the `.yaml` extension (the team's hooks reject `.yml`).
     Read and write it with `yaml-cpp`, which the test targets already link. Do not add a JSON library or
     JSON files.
   - Write reference outputs so their diffs are readable: block style, one value per line, keys in the
     order section 6.4 defines, lists in the order it defines, no trailing whitespace and a final newline
     (`YAML::Emitter` does not add one), so the end-of-file-fixer and trailing-whitespace hooks never
     rewrite them.
7. **Git hygiene.**
   - Work on a branch named `jg/SW2-484/scheduler-core-refactor`, created from `main`. Phase 0 confirmed
     that the name passes the team's pre-push hook `scripts/check_branch_name.sh`.
   - Create the branch on the host with `git switch -c`. Stage files by name with `git add <files>` on
     the host. Commit only with `volley-in-container git commit ...`, so the team's prek and commitlint
     hooks run (they are installed in the container, not on the host).
   - Do not rebase, squash, amend or force-push. Do not push at all.
   - Commit messages must pass commitlint (`@commitlint/config-conventional`, see `.commitlintrc.yaml`):
     - header: `<type>(scheduler): <imperative summary in lower case> (SW2-484 <step>)`, at most 100
       characters. The summary must not start with a capital letter.
     - type: as listed in the commit table in section 5. Allowed types: build, chore, ci, docs, feat,
       fix, perf, refactor, revert, style, test, wip.
     - body: a blank line after the header, lines of at most 100 characters, saying what changed, why,
       and how parity was checked (tests run, number of reference files compared).
     - footer: `Refs: SW2-484`.
     - Example header: `refactor(scheduler): merge the two tray move-emission blocks (SW2-484 C1)`.
   - Use the titles in the commit table in section 5. The bracketed titles on the steps (`[A] ...`)
     describe steps, not commits.
   - If a hook fails, read its message, fix the cause, re-stage and commit again. If a formatter hook
     changed files, re-stage them and commit again. Never skip hooks.
8. **Style.**
   - Follow the repository's existing formatting (`.clang-format`, column limit 110). Run the formatter
     only on files you touch, inside the container, before staging:
     `volley-in-container sh 'clang-format -i <files>'`. The pre-commit hooks also run clang-format,
     gersemi (CMake), shellcheck, end-of-file-fixer and trailing-whitespace on staged files, so new CMake
     must already pass gersemi.
   - Follow the naming rules in `.clang-tidy` (`readability-identifier-naming`): types and functions
     CamelCase; variables and members lower_case; private and protected members end in `_`;
     namespace-scope and static constants `kCamelCase`; enum constants UPPER_CASE; namespaces lower_case.
     Designated initializers are allowed (the check that would forbid them is disabled) and the code
     already uses them.
   - At the end of commits 3, 5 and 8, run `volley-in-container tidy` (the team's clang-tidy hook on
     lines changed since `main`; CI runs the same check on push). Fix findings in code you added or
     moved. Record findings in code you only renamed or did not touch, without fixing them.
   - Keep the footprint small (objective 2): prefer one clear function over several thin ones, standard
     algorithms over hand-written loops where they read better, and deleting dead code over keeping it.
     Report lines added and removed per commit in the review packet (`git diff --stat`).
   - C++20 with GCC 13 (objective 3). Use the standard library where it fits; no C++23 features.
   - Add `[[nodiscard]]` to new functions that return `stdx::Expected` / `stdx::Result`.
   - Do not add new dependencies to `package.xml`. `stdx`, `motion_planner`, `task_planner`, `planner_core`,
     `common_ros`, `cost_functions`, `yaml-cpp` (test) and `ament_index_cpp` (test) are already declared
     (verified in Phase 0).
9. **Tests come with extractions.** Every function declared in a public header of the tray module gets a
   test in `tray_assignment_tests` that constructs no `Scheduler` and no `ScheduleEventDag`. File-local
   helpers (anonymous namespace) are tested through the function that calls them. Use the existing test
   layouts (`tiny_lot`, `triple_pick_lot`, `576_eccles_half`, `1355_fulton`, found with
   `GetLayoutPathByName`) and inline YAML states loaded with `DiscreteGarageState::Set(YAML::Load(...))`,
   as the existing tests do.
10. **Stop and ask** (do not guess) when:
    - the branch differs from this plan in a way that affects it;
    - parity fails and the cause is not an obvious mistake in your own change (section 8 names the one
      difference that is expected);
    - a step would need a change outside `scheduler`;
    - a step needs a decision that section 10 does not cover.

    For the decisions in section 10, apply the default, record it in the notes file, and list it in the
    review packet. Do not stop for them.
11. **Keep a running log** in `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/SW2-482_notes.md`. It lives outside the volley repo: never copy it into the repo and
    never commit it. Update it as you go. Record:
    - decisions taken;
    - differences between the branch and this plan;
    - bugs found but not fixed;
    - anything a reviewer should know;
    - a **review log**: for each commit, the feedback items (numbered, with status `open` / `done` /
      `discussed`) and the final SHA, and at the top, which commit is in progress and what is next.

    It is also how the next session picks up where this one stopped, so keep it current. The PR
    description will be assembled from it.
12. **Review gate: one commit at a time.** Work on one commit from the table in section 5, and stop
    **before committing** it:
    1. Do the work, build, run the tests and parity (rule 5), and format the touched files. Leave the
       changes **unstaged** so the user sees them as the working-tree diff.
    2. Post a review packet (section 11) and end your turn. Do not start the next commit.
    3. The user replies with feedback: chat messages and/or comments on lines of the diff, often
       several items at once. Number the items, add them to the review log in the notes file
       (rule 11), and address **all** of them. Re-run the build, tests and parity. Reply with the list
       of items and what you changed for each, and stop again. Repeat until the user approves.
    4. Commit only when the user says so explicitly (for example "commit" or "approved"). Stage the
       files by name, commit with `volley-in-container git commit`, and report the SHA. The user's
       permission prompt for the commit is the final check.
    5. Then stop. Start the next commit only when the user says so (for example "next").

    If you disagree with a feedback item, say why and ask; don't silently skip it. At the last commit of
    a phase, also meet the phase's exit criteria (including `scheduler_advanced_tests` and
    `volley-in-container tidy`) before posting the review packet.

## 4. Context you need in your head

The names in this section are **today's** names (branch `703bfe7c`). Commits 2 and 3 rename many of them
(Phase B2 in section 5); from commit 4 on, use the new names.

**The pipeline.** `Scheduler::Plan()` runs five stages over one `ScheduleContext` (pointer `ctx`):

| # | Stage | Code today | Output |
|---|---|---|---|
| 1 | Job expansion | 12 `Plan<Type>Job` members, plus `PlanOpenBayDoor` and `PlanUnstashWaypointTraysJob` | Event DAG with blanks (tray ids, destinations) |
| 2 | Tray assignment | `DoTrayAssignments` (560 lines) and helpers | Blanks filled, blocker moves added, `first_tray_event` |
| 3 | AGV assignment | `DoAgvAssignments` (365 lines) and helpers, then `Reduce()`, then `SanityCheckEvents` | AGV events and edges |
| 4 | Motion planning | `PlanMotions` (63 lines), which calls CHUGG in `motion_planner` | `ContinuousState` |
| 5 | Action graph | `ResponseFromTrajectories` and free functions in an anonymous namespace of `scheduler.cpp`; `InsertVrcActionsIntoDag` in `utils.cpp` | `PlanResponse` |

Only stage 2 changes in logic in this PR; stage 1 is renamed.

**Today's tray call tree.** All of these are `const` `Scheduler` members in `src/scheduler.cpp` (line
numbers valid at `703bfe7c`):

- `DoTrayAssignments` (2533–3092)
  - `ApplyTransitionToFreeingMoves` (2124): for **bay and VECS transitions only**, registers the bay / VECS
    inbound pose in `freeing_moves` with the generic `TRAY` footprint and applies the event to
    `working_state`. AGV and VRC events are skipped (not applied).
  - `AssignTrayIdForEmptyMove` (2159): fills a blank tray id (empty-tray search from the destination), may
    adjust the destination heading. Also called by `PlanReadyForInsertJob` (1271).
  - `AssignDestForUntargetedMove` (2222–2338): fills a blank destination through `ResolveBlockingTrays`,
    fixes the heading, emits the required moves (**copy A** of the emission code, 2267–2318), applies and
    chains the move. Its original move gets no `freeing_moves` edges or registration.
  - `ResolveBlockingTrays` (1982–2119, public): a parking spot for one tray plus the moves needed first,
    computed on a private copy of the state. Calls `FindOpenSpaceForRootTray` (1850) and
    `TryFindBlockingTrayResolution` (1895), which recurses into `ResolveBlockingTrays`. Also called by
    `PlanChargePayloadJob` (1732), which **uses only the destination and discards the moves**, and by one
    test.
  - `WithPriorDests`: a lambda inside `DoTrayAssignments` (2687).
  - the heading helpers `UsePreferredHeading` (1771; also `PlanAgvMoveJob`, `PlanReparkTrayJob`),
    `UseEvChargeHeading` (1781; also `PlanChargePayloadJob`) and `UseRetrievalHeading` (1805; only from
    `UsePreferredHeading`). `UsePreferredHeading`'s `tray_opt` parameter is unused.
  - inline blocks of the main loop: the destination check (2603–2650), the critical path (2656–2710), the
    blocker loop with two fallbacks (2717–2896; fallback 1 "advance the root" 2777–2856, fallback 2 "allow
    parking on the critical path" 2858–2886), **copy B** of the emission code (2901–2988), the blocker
    re-scan (2994–3021), and the root-move tail (3024–3067).

**Services.** `gg_` (`GarageGraph`), `table_` (`CollisionTable`), `cost_model_` (`cost::MotionCostModel`),
`layout_` (`LayoutSPtr`) and `logger_` are built once in the constructor and are read-only afterwards.
`pg_` is used only to build `gg_`. The tray tree uses only these, plus three fields of `ctx`:

- it **edits** `ctx->events`;
- it **reads** `ctx->initial_state` (and copies it into `working_state`);
- it **writes** `ctx->first_tray_event` (its only writer; read once in the AGV tree, 2487). This is the
  hand-off to AGV assignment: for each tray, its **first** move.

**Tests that call stages directly.** `test/scheduler_tests.cpp` calls `scheduler.DoTrayAssignments(ctx)` 4
times (lines 70, 165, 245, 378), `scheduler.DoAgvAssignments(ctx)` 9 times and
`scheduler.ResolveBlockingTrays(...)` once (301). They build the context as
`std::make_shared<ScheduleContext>(MakeGuid(0, 0xDEADBEEF), state, rclcpp::Time())` and add events with
`ctx->events.AddEvent / AddDependency`. There are 72 active `TEST` cases in four binaries
(`scheduler_tests` 25, `scheduler_jobs_tests` 30, `scheduler_insert_orientation_tests` 4, `utils_tests`
13), no fixtures, no shared helpers, and no test reads the clock. `Scheduler.DoubleRetrieveDodgeAgv` is
commented out. Tests use `GetGarageGraph()` (3), `disabledness_filters` (3), `last_entity_event` (15),
`UpdateLastEntityEvent` (4); none uses `gg_`, `table_`, `PrintDags`, `first_tray_event`,
`PushBackScheduledJob` or `UpdateLeafDependencies`.

**Failure contract.** If tray or AGV assignment fails, `Plan()` sets:

- `result.success = true`;
- `result.message = "Failed tray assignments: " + message` (or the AGV equivalent);
- every pending job to `FailJob(job, message)`.

It then returns. Keep this exactly.

**Errors.**

- `BoolStringPair` (`std::pair<bool, std::string>`, from `common/types.hpp`) is being replaced by
  `stdx::Expected<T>` / `stdx::Result` (aliases over `tl::expected` in namespace **`volley::stdx`**,
  `src/core/stdx/include/stdx/expected.hpp`; `stdx::Unexpected(msg)` and `stdx::Unexpected(fmt, args...)`).
  The scheduler already uses them in `EnsureAgvMovePathsClear`, `RunAgvPathRepairPass` and
  `InsertVrcActionsIntoDag`. In this PR every function of the tray tree that leaves `Scheduler` returns
  `stdx` types; job expansion and the AGV tree keep `BoolStringPair` (their turn comes with stages F and H).
- `std::optional` stays for internal "searched, found nothing" results.
- Keep error strings identical.

**The DAG.** `ScheduleEventDag` (`planner_core`) stores `std::shared_ptr<ScheduleEvent>` on a Boost `vecS`
graph. `AddEvent` returns false for a pointer already present; `AddDependency` returns false for a missing
endpoint or a duplicate edge and never checks cycles. `GetTopologicalOrdering` is a min-heap on job index;
events with equal job index come out in heap order, which follows push order, which follows each vertex's
out-edge order, which follows `AddDependency` order. So **the order of `AddEvent` and `AddDependency` calls
is part of the behaviour.** `TrayMove::Apply` is `const`; with no tray id it does nothing, with no
destination it removes the tray from the state, and when another tray sits on the destination it moves that
tray to node 0.

**Occupancy.** `freeing_moves` is a `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>` (common_ros,
template on the occupant type). `GetBlockers` returns an `unordered_set` of occupants, hashed on the
pointer, so the order in which several occupants of one pose become edges is address-dependent today.

**GUIDs.** Action-node GUIDs come from a static counter in `utils.cpp` (`CreateActionGuid`), so they depend
on how many actions earlier tests in the same binary produced; the canonical response replaces them by
positions.

## 5. The plan: phases and commits

Stage letters match the study pack's staged plan. Each phase lists **steps** that describe the work in
detail. Commits group the steps as follows:

| # | Commit header (after `<type>(scheduler): `) | Type | Steps | Objective | Est. size (+/−) |
|---|---|---|---|---|---|
| 1 | `add parity references to the planning tests (SW2-484 A)` | test | A1, A2 | Record today's behaviour before any change. | +400 code, ~45 reference files |
| 2 | `rename scheduler members and expansion methods (SW2-484 B2)` | refactor | B2-1, B2-2 | Purely mechanical renames inside `Scheduler`; no logic change. | +400 / −400 |
| 3 | `rename ScheduleContext to PlanContext and its fields (SW2-484 B2)` | refactor | B2-3 | The per-call context in its own header, with the catalogue's names. | +300 / −280 |
| 4 | `add garage services and the tray heading and empty-tray helpers (SW2-484 C1)` | refactor | C1-1 to C1-3 | `GarageServices`, the module's library and test targets, the first pure helpers. | +330 / −120 |
| 5 | `make blocking-tray resolution a free function with plain results (SW2-484 C1)` | refactor | C1-4 | `ResolveBlockingTrays` and its two searches leave `Scheduler`; results are plain data. | +320 / −300 |
| 6 | `extract the main-loop decisions of tray assignment (SW2-484 C1)` | refactor | C1-5 | Destination check, critical path, blocker scan, parking-spot choice as pure functions. | +260 / −200 |
| 7 | `merge the two tray move-emission blocks (SW2-484 C1)` | refactor | C1-6 | One emission function and one root-commit function; the riskiest change, alone. | +120 / −160 |
| 8 | `put tray assignment behind a solver interface (SW2-484 C2)` | refactor | C2-1 to C2-4 | `Solver`, `DefaultSolver`, adapter, `Scheduler::AssignTrays`, injection; legacy members deleted. | +500 / −450 |

Each commit goes through the review gate in rule 12. Two named split points keep the count within ten:
commit 3 may become "type rename" then "field renames"; commit 8 may become "module added, not yet used"
then "switch `Plan()` and delete the legacy members" (the first half then keeps the old loop alive for one
commit).

### Phase R: design review

Done on 2026-10-22; report and the user's answers in `DESIGN-REVIEW.md`. Phase 0 (the survey) was done as
part of it; its findings are in the notes file.

### Phase A: parity baseline (test-only; `src/` untouched)

Goal: every planning test compares a **canonical description** of its result with a recorded reference
file. Everything lives in `scheduler/test/`.

**Step A1: `[A] Add the parity helper (canonicalise, record or compare)`**

Add `test/parity.hpp` and `test/parity.cpp`, namespace `volley::parity`, compiled into the three planning
test binaries (section 6.4 has the function list and the canonical format):

- `YAML::Node Canonical(const ScheduleContext& ctx)`: the events, the raw edge set and `first_tray_event`
  (under the key `first_event_by_tray`, its name after commit 3, so the files never change for a rename).
- `YAML::Node Canonical(const PlanResponseMsg& response)`: the response with GUIDs replaced by positions and
  `scheduled_jobs` sorted.
- `void ExpectReference(const YAML::Node& actual, std::string_view suffix = {})`: compares `actual` with
  `test/reference/<Suite>.<Name>[.<suffix>].yaml` (suite and name from gtest's `current_test_info()`), or
  writes it when `RECORD_REFERENCE_OUTPUT` is set. On a mismatch it fails the test and prints the first
  differing lines of the two emitted documents. A missing file fails with a message naming the record
  command.
- `template <class F> void ExpectReference(F&& produce, std::string_view suffix = {})`: calls `produce()`
  twice, asserts the two canonical documents are equal (the determinism check), then compares the first
  with the reference.
- CMake: add `test/parity.cpp` to `scheduler_tests`, `scheduler_jobs_tests` and
  `scheduler_insert_orientation_tests`, and give each
  `target_compile_definitions(<target> PRIVATE SCHEDULER_REFERENCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test/reference")`
  so recording and comparing use the source tree. No install step.

**Step A2: `[A] Instrument the planning tests and record the references`**

- After every `scheduler.Plan(request_data, now)` in the three binaries, add
  `parity::ExpectReference([&] { return parity::Canonical(scheduler.Plan(request_data, now)); });`.
  Where a test plans more than once (`ReadyForRetrieveJob`, `TransitionBay`, …), pass a suffix. Where the
  test already stores the response, reuse it for the test's own assertions and let the lambda plan again.
- After each of the 4 `DoTrayAssignments` and 9 `DoAgvAssignments` calls, add
  `parity::ExpectReference(parity::Canonical(*ctx));` with suffix `"tray"` / `"agv"` in the two tests
  that run both stages (`TrayAssignmentTestComplexDag`, `TrayAndAgvAssignments`). Skip the
  `ResolveBlockingTrays` test (its own assertions pin the result).
- Add ordinary tests, each with a reference, for scenarios no test covers today: a `READY_FOR_INSERT`
  request on `tiny_lot` (blank tray id through `Plan()`); a request with a non-empty `base_schedule` (one
  `TYPE_AGV_COMMAND` node, so an AGV and two nodes are reserved); and, if each can be built on a test
  layout in under about 60 lines, a scenario that reaches fallback 1 (advance the root) and one that reaches
  fallback 2 (park on the critical path). Report which of these you could not build. The waypoint stash
  is already covered (`CleanGarageUnstashesTrayFromWaypoint`).
- Record with `volley-in-container record-reference scheduler scheduler_tests`, then the same for
  `scheduler_jobs_tests` and `scheduler_insert_orientation_tests`. Then run `volley-in-container test
  scheduler` (a new process) and confirm every comparison passes. Record the commit SHA of the branch
  point in the notes file (the reference files carry no SHA field: the commit that adds them is the
  record).

If a reference differs between the record run and the compare run, or between the two in-process runs,
**stop and report**: define the equivalence (for example, sort a list) in the canonicaliser before you
commit, and record why. The one known candidate is the occupancy-edge order of section 8.

Exit criteria for phase A:

- every test passes;
- every reference compares equal in a fresh process;
- the notes file lists the reference files with what each covers (job types, stages, failure paths).

### Phase B2: names (mechanical; commits 2 and 3)

No planning logic changes. Parity must stay green **without** touching any reference file. If the parity
helper reads a renamed type or field, update the helper in the same commit; that is allowed. Error strings
that spell an old method name stay as they are (rule 1); log lines may follow the new names.

- **B2-1** `[B2] Rename Scheduler members` (commit 2)
  - `gg_` → `motion_graph_`, `table_` → `collision_table_`, `GetGarageGraph()` → `GetMotionGraph()`
    (three uses in `scheduler_tests.cpp`).
  - `pg_` becomes a local in the constructor (Phase 0 verified it is used only to build `gg_`).
  - `costaudit_` → `cost_audit_`, `printdags_` → `print_dags_`, `PrintDags()` → `TogglePrintDags()`.
  - Update callers in `scheduler_ros.cpp` and `scheduler_component.cpp` if they use any of these (check
    with `rg`). `scheduler_advanced_tests` uses none of them.
- **B2-2** `[B2] Rename Plan<Type>Job to Expand<Type>Job` (commit 2)
  - All twelve expansion methods, plus `PlanOpenBayDoor` → `ExpandOpenBayDoor` and
    `PlanUnstashWaypointTraysJob` → `ExpandUnstashWaypointTraysJob`.
  - **Do not** rename `Plan()`, `PlanMotions()` or anything else starting with `Plan` that is not a job
    expansion. Do not change error strings that contain the old names.
- **B2-3** `[B2] Move ScheduleContext to plan_context.hpp as PlanContext and rename its fields` (commit 3)
  - `ScheduleContext` → `PlanContext`, `ScheduleContextSPtr` → `PlanContextSPtr`, in a new header
    `include/scheduler/plan_context.hpp` that `scheduler.hpp` includes.
  - Fields: `events` → `event_dag`; `first_tray_event` → `first_event_by_tray`; `disabledness_filters`
    (`CollistionFilterMap`) → `keep_out_filter_by_footprint` (`KeepOutFilterByFootprint`);
    `last_entity_event` (`GarageEntityEventMap`) → `last_event_by_asset` (`AssetEventMap`, still keyed by
    `GarageEntityIdMsg`: the `AssetId` type is a later PR).
  - Methods: `PushBackScheduledJob` → `AddScheduledJob`, `UpdateLastEntityEvent` → `AppendToAssetChain`,
    `UpdateLeafDependencies` → `AddAfterJobLeaves`. The test `Scheduler.UpdateLastEntityEvent` is renamed
    to match (its reference file, if it has one, is renamed with it).
  - `request_id_str` stays: it labels the `PrintGraph` output under `print_dags_`. The constructor keeps
    taking `rclcpp::Time` (the `Timepoint` constructor is a later PR).
  - Update the parity helper's `Canonical(const PlanContext&)`.
  - Split point: the type rename and header move first, then the field and method renames, if one commit
    is too large to review.

Exit criteria for phase B2: all tests pass with every reference file unchanged (`git status` shows no
change under `test/reference/`); `scheduler_advanced_tests` builds and passes.

### Phase C1: pure helpers, extracted straight into the module

Turn helpers into free functions over `const GarageServices&` (section 6.2) in
`include/scheduler/task_planning/tray_assignment/` and `src/task_planning/tray_assignment/` (section 6.1),
namespace `volley::task_planning::tray_assignment` (`scheduler.cpp` declares
`namespace tray_assignment = task_planning::tray_assignment;`). They return `stdx::Expected` /
`stdx::Result` where a reason must travel, and `std::optional` where "found nothing" is all the caller
needs. Job expansion calls the same functions through `services_`. Each function keeps its body; the
commit body lists every change inside it. Each commit adds unit tests for the functions it creates.

- **C1-1** `[C1] Add GarageServices, Scheduler::services_, and the module's library and test targets`
  (commit 4)
  - Add `include/scheduler/garage_services.hpp` (section 6.2), namespace `volley`.
  - Add the member `GarageServices services_` to `Scheduler`, declared **after** `layout_`,
    `motion_graph_`, `collision_table_`, `logger_` and `cost_model_`, initialised as
    `services_{motion_graph_, collision_table_, cost_model_, *layout_, logger_}`.
  - CMake (section 6.2): the static library `scheduler_tray_assignment` (position-independent, linked into
    `${PROJECT_NAME}`) and the gtest `tray_assignment_tests`, which links `scheduler_tray_assignment` and
    `yaml-cpp` but **not** `${PROJECT_NAME}`. Check that the static target receives the package's
    dependencies (`ament_auto_add_library` calls `ament_target_dependencies`); if not, add them explicitly.
  - In `test/task_planning/tray_assignment_tests.cpp`, a small helper that builds the services from a
    layout name the way `Scheduler::Scheduler` does (`Layout` from file, `PoseGraph`, `GarageGraph`,
    `CollisionTable`, `cost::MotionCostModel` from default params, a logger) and owns them for the test's
    lifetime.
- **C1-2** `[C1] Move the heading helpers to tray_assignment/headings` (commit 4)
  - `EvChargeHeading`, `RetrievalHeading`, `PreferredHeading` as in section 6.3: they return the adjusted
    pose instead of editing a reference, and `PreferredHeading` drops the unused tray argument.
  - Update the callers: `ExpandAgvMoveJob`, `ExpandReparkTrayJob`, `ExpandChargePayloadJob`,
    `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`, `DoTrayAssignments` (two places). Delete
    the three members.
  - Tests: `EvChargeHeading` on `576_eccles_half` nodes 46 and 47 gives heading 0 and is empty elsewhere
    and on other layouts; `RetrievalHeading` with and without a payload, and with `reciprocal_to_tray`.
- **C1-3** `[C1] Extract ChooseEmptyTray from AssignTrayIdForEmptyMove` (commit 4)
  - `stdx::Expected<TrayChoice> ChooseEmptyTray(services, state, destination)` (section 6.3). It returns
    the choice (tray id and possibly adjusted destination) instead of mutating the move; the error texts
    are today's. The caller applies it: `move->SetTrayId(choice.tray_id); move->SetDest(choice.destination)`.
  - Update `ExpandReadyForInsertJob`'s fill pass (a failed choice still leaves the move blank and logs the
    deferral) and `DoTrayAssignments`. Delete the member.
  - Tests on `tiny_lot`: the nearest empty tray is chosen; a loaded tray is skipped; no empty tray gives
    `"Failed to find empty tray to move to <dest>"`.
- **C1-4** `[C1] Make ResolveBlockingTrays a free function with plain results` (commit 5)
  - `stdx::Expected<BlockingResolution> ResolveBlockingTrays(services, state, const ResolveRequest&)`
    (section 6.3), with designated initialisers at call sites. `job_index` is no longer a parameter: the
    result holds no events, and `Apply` does not read it. Inside, trial moves are applied to the private
    state copy through a temporary `TrayMove`.
  - `FindOpenSpaceForRootTray` → file-local `FindOpenSpace` and `TryFindBlockingTrayResolution` →
    file-local `TryResolveBlocker` in the anonymous namespace of `blocking_trays.cpp`, both returning
    `std::optional`, mutually recursive with `ResolveBlockingTrays` as today. Their private structs
    (`OpenSpaceSearchResult`, `BlockingTrayResolution`) move with them; `prereq_moves` becomes
    `std::vector<PlannedTrayMove>`.
  - Today, failures are only logged and callers treat them as "try the next fallback". Keep that: the
    `Expected`'s error carries the logged text, and callers only log or ignore it.
  - Callers: `ExpandChargePayloadJob` uses `resolution->destination` (its error text unchanged);
    `AssignDestForUntargetedMove` and the two copies of the emission code create the `TrayMove`s from
    `PlannedTrayMove`s (`std::make_shared<TrayMove>(move->GetJobIndex())`, `SetTrayId`, `SetDest`) at the
    point where today they receive ready-made events. Delete the three members and the two structs.
  - Move `Scheduler.ResolveBlockingTraysRecursivelyUnblocksChain` to `tray_assignment_tests` (no
    `Scheduler`), asserting on the plain fields. Add a test for the waypoint-stash tier
    (`allow_waypoint_stash`) and one for `immobile_trays`.
- **C1-5** `[C1] Extract the main-loop decisions` (commit 6)
  - In `critical_path.{hpp,cpp}`: `CheckDestinationUsable` (the three error texts of 2622–2648),
    `FindCriticalPath` (2656–2706: the search and the collection of the path's vertices and its trays in
    first-appearance order), `BlockersOnPath` (the re-scan of 2994–3021; the fallback-1 "is the next pose
    blocked" check of 2800–2814 is the same query on a one-vertex span). Section 6.3 has the signatures.
  - In `blocking_trays.hpp`: `ChooseParkingSpot(services, state, tray_id)`: the decision part of
    `AssignDestForUntargetedMove` (the existence check with its exact error text, `ResolveBlockingTrays`
    with `enforce_retrieval_heading = payload present`, the heading fix for parking nodes,
    `EvChargeHeading`). The caller keeps the blank-tray-id check and does the emission.
  - `WithPriorDests` stays a lambda. Fallback 1 stays inline (`BlockersOnPath` on the next vertex, then
    `EvChargeHeading`, then the advance move); keep the recorded path expression and the double apply
    exactly (section 8, B1 and B2 in the notes), and add a one-line test or `static_assert`-style check
    that documents what `std::vector<GaragePoseMsg>{vertex, pose}` constructs.
  - Preserve call order and the exact paths recorded.
  - Tests on `tiny_lot` / `triple_pick_lot`: a disabled destination fails with the exact text; the critical
    path lists the trays in path order; `BlockersOnPath` finds a tray that collides by footprint, not only
    by node id; `ChooseParkingSpot` for an empty and a loaded tray.
- **C1-6** `[C1] Merge the two move-emission blocks` (commit 7)
  - Still in `scheduler.cpp`, still writing `ctx->event_dag`: one `EmitMoveChain(...)` that applies, adds
    and chains a span of `PlannedTrayMove`s and returns the last emitted event, and one
    `CommitRootMove(...)` for the root move's tail. Private members or file-local functions taking the
    loop's state explicitly; they become `Pass` methods in C2.
  - Keep the emission differences behind `EmitOptions`:
    - `check_apply`: only `AssignDestForUntargetedMove` checks `Apply`'s result (text `"Failed to apply
      unblocking move required: " + msg`); the main loop cannot yet because of the double apply (B2);
    - `source_footprint`: the tray's own footprint in `AssignDestForUntargetedMove`, the generic `TRAY`
      in the main loop.
    - The main loop's `blocking_tray_set.erase(...)` inside the loop is dead (both containers are cleared
      right after the loop): drop it, and say so in the commit body.
  - Keep the root-tail difference behind `CommitOptions`: the main loop adds `freeing_moves` edges for the
    root move's destination and source and registers its source; `AssignDestForUntargetedMove` does
    neither. The two apply-failure texts differ too (`"Failed to apply event during tray assignment: " +
    ToString() + ": " + msg` versus the raw message): keep both. The caller adds the `last emitted move →
    root move` edge itself, at the point where today's code adds it (per blocker round in the main loop,
    after `Apply` in `AssignDestForUntargetedMove`), so the order of DAG writes stays identical.
  - This is the riskiest commit of the phase. Run the full scheduler suite; every reference must match
    unchanged.

Exit criterion for phase C1: all tests pass, every reference matches unchanged, `tray_assignment_tests`
covers every public function of the module, `volley-in-container tidy` run after commits 5 and 7.

### Phase C2: the solver (commit 8)

- **C2-1** `[C2] Add the solver interface`
  - `include/scheduler/task_planning/tray_assignment/solver.hpp` exactly as in section 6.3:
    `MoveRequest`, `StateChange`, `Step`, `Input`, `Fill`, `NewMove`, `Edge`, `Result`, `Solver`. Structs
    get `friend bool operator==(...) = default;` so tests can compare results.
- **C2-2** `[C2] Add DefaultSolver`
  - `default_solver.{hpp,cpp}`: `DefaultSolver::Solve` is today's `DoTrayAssignments` loop moved, over
    the pure functions of C1 and a file-local `Pass` struct (section 6.3). It walks `input.steps` in
    order: a `StateChange` is applied to the working state and its bay / VECS pose registered (was
    `ApplyTransitionToFreeingMoves`); a `MoveRequest` goes through `ChooseEmptyTray`, `ChooseParkingSpot`
    or the main loop as today, with `EmitMoveChain` / `CommitRootMove` now **recording** `NewMove`s and
    `Edge`s by id instead of calling the DAG, and `Fill`s instead of the setters. Moves are applied to the
    working state through temporary `TrayMove`s with both fields set. Occupancy is
    `GarageOccupancyChecker<size_t>` keyed by step and new-move ids.
  - The recorded order of new moves and edges equals today's order of `AddEvent` and `AddDependency`
    calls (invariant 9).
- **C2-3** `[C2] Add the adapter`
  - `adapter.{hpp,cpp}`: `StepsFromDag` and `ApplyResult` (section 6.3). `ApplyResult` creates the new
    `TrayMove`s and adds them in order, then adds the edges in order (ignoring a `false` as today), then
    sets the fills, then `first_event_by_tray`, then runs today's final `GetTopologicalOrdering` check
    with its text `"Failed to get new total ordering"`.
- **C2-4** `[C2] Route the Scheduler through the solver and delete the legacy members`
  - `Scheduler` gains `std::unique_ptr<tray_assignment::Solver> tray_solver_` (declared after
    `services_`) and a trailing constructor parameter `std::unique_ptr<tray_assignment::Solver>
    tray_solver = nullptr`, which defaults to `std::make_unique<tray_assignment::DefaultSolver>()`.
    Existing callers do not change.
  - `DoTrayAssignments` is replaced by `[[nodiscard]] stdx::Result AssignTrays(PlanContextSPtr ctx)
    const` (public): `StepsFromDag` → `tray_solver_->Solve(services_, …)` → `ApplyResult`. `Plan()` calls
    it and keeps the failure contract and the `"Failed tray assignments: "` prefix verbatim. The four
    direct tests switch to `auto r = scheduler.AssignTrays(ctx); EXPECT_TRUE(r) << r.error();`.
  - Delete `DoTrayAssignments`, `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`,
    `ApplyTransitionToFreeingMoves`, `EmitMoveChain` / `CommitRootMove` of commit 7 (moved into `Pass`),
    and every member only they used. The dead `assigned_events` goes with them.
  - Tests in `tray_assignment_tests` (no `Scheduler`, no DAG): `DefaultSolver` on a hand-built `Input`
    for (a) a move with both fields and a clear path (no new moves, no fills, one `first_move_by_tray`
    entry); (b) a blank destination (one fill); (c) a blank tray id (one fill with the chosen tray);
    (d) a blocker on the path (the states of `UnblockingTrayMoveTest`) with the expected new move and the
    expected edges in order; (e) a `StateChange` (bay transition) before a move into that bay gives an
    edge from the transition's step; (f) `Solve` twice on the same `Input` gives equal `Result`s. In
    `scheduler_tests`: a `FakeSolver` injected through the constructor whose `Solve` returns
    `stdx::Unexpected("nope")` makes `Plan()` report `"Failed tray assignments: nope"` and fail every
    pending job.
  - Split point: C2-1 to C2-3 with their module tests first (the old loop still runs), then C2-4.

Exit criteria for phase C2 (and for the PR):

- no production call to the removed methods; `rg DoTrayAssignments` finds nothing in `src/` or `test/`;
- all tests pass and every reference matches unchanged (or changed only by the deliberate difference of
  section 8, recorded in the same commit with its diff);
- `tray_assignment_tests` links without `${PROJECT_NAME}` and constructs a `DefaultSolver`;
- `scheduler_advanced_tests` and `planner_core` pass;
- `volley-in-container tidy` is clean on added and moved code;
- the notes file is finished (decisions, deviations, deferred bugs) and the PR description is drafted from
  it into `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/SW2-482_pr_description.md` (not committed).

## 6. Specifications

### 6.1 Source tree (target state after this PR)

```
scheduler/
├── CMakeLists.txt                     # + scheduler_tray_assignment (static), tray_assignment_tests, parity sources
├── package.xml                        # unchanged
├── include/scheduler/
│   ├── scheduler.hpp                  # Scheduler: Plan(), Expand*Job, AGV assignment …; owns services_, tray_solver_
│   ├── plan_context.hpp               # PlanContext (was ScheduleContext in scheduler.hpp)
│   ├── garage_services.hpp            # GarageServices (namespace volley)
│   ├── scheduler_msgs.hpp, scheduler_ros.hpp, utils.hpp     # existing, untouched
│   └── task_planning/                 # stages 1-3; only tray_assignment/ exists in this PR
│       └── tray_assignment/           # namespace volley::task_planning::tray_assignment; never includes scheduler/scheduler.hpp
│           ├── solver.hpp             # MoveRequest, StateChange, Step, Input, Fill, NewMove, Edge, Result, Solver
│           ├── default_solver.hpp     # DefaultSolver
│           ├── adapter.hpp            # StepsFromDag, ApplyResult: the only tray code that touches ScheduleEventDag
│           ├── headings.hpp           # EvChargeHeading, RetrievalHeading, PreferredHeading
│           ├── empty_tray.hpp         # ChooseEmptyTray, TrayChoice
│           ├── blocking_trays.hpp     # ResolveBlockingTrays, ChooseParkingSpot, PlannedTrayMove, BlockingResolution, ResolveRequest
│           └── critical_path.hpp      # CheckDestinationUsable, FindCriticalPath, BlockersOnPath, CriticalPath
├── src/
│   ├── scheduler.cpp, utils.cpp, scheduler_ros.cpp, scheduler_component.cpp   # existing
│   └── task_planning/tray_assignment/ # one .cpp per header above; default_solver.cpp holds the file-local Pass
└── test/
    ├── scheduler_tests.cpp, scheduler_jobs_tests.cpp, scheduler_insert_orientation_tests.cpp, utils_tests.cpp
    ├── parity.hpp, parity.cpp         # Canonical(), ExpectReference()
    ├── reference/<Suite>.<Name>[.<suffix>].yaml   # recorded canonical results (commit 1)
    ├── task_planning/tray_assignment_tests.cpp    # links only scheduler_tray_assignment
    └── garage_states/double_retrieve_garage_state.yaml   # existing, used by a commented-out test
```

No other folders: no `core/`, `ros/`, `job_expansion/`, `agv_assignment/`, `validation/`,
`motion_planning/` or `action_graph/` in this PR. **Do not create a namespace named `common` or
`motion_planner`** inside `volley`: it would hide `::common` (breaking `common::EnumInteger(...)`) and the
package's own names.

### 6.2 Services and build

```cpp
// include/scheduler/garage_services.hpp
namespace volley {
struct GarageServices {                       // read-only services every search needs; built once
  const GarageGraph& graph;                   // Scheduler::motion_graph_
  const CollisionTable& collision_table;      // Scheduler::collision_table_
  const cost::MotionCostModel& cost_model;    // Scheduler::cost_model_
  const Layout& layout;                       // *Scheduler::layout_
  rclcpp::Logger logger;                      // copy of Scheduler::logger_
};
}  // namespace volley
```

```cmake
# CMakeLists.txt (excerpt; the rest is unchanged)
volley_add_library(
  scheduler_tray_assignment
  STATIC
  src/task_planning/tray_assignment/headings.cpp
  src/task_planning/tray_assignment/empty_tray.cpp
  src/task_planning/tray_assignment/blocking_trays.cpp     # commit 5
  src/task_planning/tray_assignment/critical_path.cpp      # commit 6
  src/task_planning/tray_assignment/default_solver.cpp     # commit 8
  src/task_planning/tray_assignment/adapter.cpp            # commit 8
)
set_target_properties(scheduler_tray_assignment PROPERTIES POSITION_INDEPENDENT_CODE ON)

volley_add_library(${PROJECT_NAME} SHARED src/scheduler.cpp src/utils.cpp LINK_LIBRARIES scheduler_tray_assignment)

if(BUILD_TESTING)
  volley_add_gtest(
    tray_assignment_tests
    test/task_planning/tray_assignment_tests.cpp
    LINK_LIBRARIES
      yaml-cpp
      scheduler_tray_assignment              # not ${PROJECT_NAME}: the test cannot reach Scheduler
  )
  # the three planning test targets also list test/parity.cpp and get SCHEDULER_REFERENCE_DIR (commit 1)
endif()
```

The module includes `rclcpp/logger.hpp` and the logging macros the scheduler already uses
(`common_ros/roslog.hpp`, `rclcppx/logging.hpp`) through `services.logger`; nothing else from `rclcpp`.
Nothing under `task_planning/` includes `scheduler/scheduler.hpp`, `scheduler/plan_context.hpp` or
`scheduler_msgs.hpp` (review item; the module test's link line enforces the rest). The adapter includes
`planner_core/event_dag.hpp` only.

### 6.3 Tray module API

```cpp
// include/scheduler/task_planning/tray_assignment/solver.hpp
namespace volley::task_planning::tray_assignment {

struct MoveRequest {                          // a TrayMove of the plan, as job expansion left it
  size_t job_index;
  std::optional<uint16_t> tray_id;            // blank: "any empty tray" (ChooseEmptyTray)
  std::optional<GaragePoseMsg> destination;   // blank: "anywhere sensible" (ChooseParkingSpot)
};
struct StateChange {                          // a bay or VECS transition between tray moves
  std::shared_ptr<const ScheduleEvent> event; // applied to the working state when reached; its pose is registered as occupied
};
using Step = std::variant<MoveRequest, StateChange>;

struct Input {
  const DiscreteGarageState& initial_state;
  std::vector<Step> steps;                    // plan (topological) order; a step's index is its id
};

struct Fill    { size_t step; uint16_t tray_id; GaragePoseMsg destination; };   // both fields of a MoveRequest, completed
struct NewMove { size_t job_index; uint16_t tray_id; GaragePoseMsg destination; };  // id = steps.size() + index in new_moves
struct Edge    { size_t before; size_t after; };                                 // ids; "before" finishes first

struct Result {
  std::vector<Fill> fills;
  std::vector<NewMove> new_moves;             // in creation order
  std::vector<Edge> edges;                    // in creation order
  std::unordered_map<uint16_t, size_t> first_move_by_tray;   // hand-off to AGV assignment (PlanContext::first_event_by_tray)
};

class Solver {
 public:
  virtual ~Solver() = default;
  [[nodiscard]] virtual stdx::Expected<Result> Solve(const GarageServices& services, const Input& input) const = 0;
};

}  // namespace volley::task_planning::tray_assignment

// default_solver.hpp
class DefaultSolver final : public Solver {
 public:
  [[nodiscard]] stdx::Expected<Result> Solve(const GarageServices& services, const Input& input) const override;
};
// default_solver.cpp holds, in an anonymous namespace, the loop's working data:
//   struct Pass { DiscreteGarageState working_state; GarageOccupancyChecker<size_t> occupancy;
//                 std::unordered_map<uint16_t, size_t> last_move_by_tray; Result result; ... }
// with RecordStateChange, Fill, EmitMoveChain (std::span<const PlannedTrayMove>, EmitOptions) and
// CommitRootMove (CommitOptions), and a helper that applies a (tray, destination) to working_state
// through a temporary TrayMove with both fields set.

// adapter.hpp: the only tray-assignment code that touches ScheduleEventDag
struct DagSteps {
  std::vector<ScheduleEventSPtr> events;      // events[i] is the event behind steps[i]
  std::vector<Step> steps;
};
[[nodiscard]] stdx::Expected<DagSteps> StepsFromDag(const ScheduleEventDag& dag);   // "Failed to get total ordering"
[[nodiscard]] stdx::Result ApplyResult(const Result& result, const DagSteps& steps, ScheduleEventDag& dag,
                                       std::unordered_map<uint16_t, ScheduleEventSPtr>& first_event_by_tray);

// headings.hpp
[[nodiscard]] std::optional<GaragePoseMsg> EvChargeHeading(const GarageServices&, const GaragePoseMsg& dest);  // engaged when the 576_eccles rule applied
[[nodiscard]] GaragePoseMsg RetrievalHeading(const GarageServices&, GaragePoseMsg dest, const std::optional<DiscretePayloadStateMsg>& payload);
[[nodiscard]] GaragePoseMsg PreferredHeading(const GarageServices&, GaragePoseMsg dest, const std::optional<DiscretePayloadStateMsg>& payload);  // EvChargeHeading, else RetrievalHeading

// empty_tray.hpp
struct TrayChoice { uint16_t tray_id; GaragePoseMsg destination; };   // heading may follow the tray
[[nodiscard]] stdx::Expected<TrayChoice> ChooseEmptyTray(const GarageServices&, const DiscreteGarageState&, const GaragePoseMsg& destination);

// blocking_trays.hpp
struct PlannedTrayMove { uint16_t tray_id; GaragePoseMsg destination; std::vector<GaragePoseMsg> path; };  // path empty when produced by recursion
struct BlockingResolution { GaragePoseMsg destination; std::vector<PlannedTrayMove> required_moves; };   // moves first, in order
struct ResolveRequest {
  uint16_t tray_id;
  std::set<uint16_t> immobile_trays = {};
  VertexCollisionIdMap illegal_poses = {};
  bool enforce_retrieval_heading = false;
  bool allow_waypoint_stash = true;
};
[[nodiscard]] stdx::Expected<BlockingResolution> ResolveBlockingTrays(const GarageServices&, const DiscreteGarageState&, const ResolveRequest&);
[[nodiscard]] stdx::Expected<BlockingResolution> ChooseParkingSpot(const GarageServices&, const DiscreteGarageState&, uint16_t tray_id);  // destination heading final

// critical_path.hpp
struct CriticalPath { std::vector<GarageGraph::Vertex> vertices; std::vector<uint16_t> blocking_trays; };  // path order; trays in first-appearance order
[[nodiscard]] stdx::Result CheckDestinationUsable(const GarageServices&, const GraphFilterProperties& filters, uint16_t tray_id, const GaragePoseMsg& destination);
[[nodiscard]] stdx::Expected<CriticalPath> FindCriticalPath(const GarageServices&, const DiscreteGarageState&, const GraphFilterProperties& filters,
                                                            uint16_t tray_id, CollisionEntityId_t root_footprint, const GaragePoseMsg& from, const GaragePoseMsg& to);
[[nodiscard]] std::vector<uint16_t> BlockersOnPath(const GarageServices&, const DiscreteGarageState&, uint16_t tray_id, CollisionEntityId_t root_footprint,
                                                   std::span<const GarageGraph::Vertex> path);
```

`filters` is the static filter the loop builds once per root move (`GetStaticFilter(TRAY, …)` with every
tray and AGV ignored); it is passed in rather than rebuilt. Check every signature against the branch
before fixing it; the notes file lists today's parameters.

**`ApplyResult`** replays the result in this order, which gives the same graph as today's interleaved
calls (same vertex indices, same per-vertex out-edge order):

1. for each `NewMove`, in order: `std::make_shared<TrayMove>(job_index)`, `SetTrayId`, `SetDest`,
   `dag.AddEvent`; the event's id is `steps.size() + i`;
2. for each `Edge`, in order: `dag.AddDependency(event(before), event(after))`, ignoring a `false` result
   (duplicate edge) as today;
3. for each `Fill`: `dynamic_cast<TrayMove&>(*events[step])`, `SetTrayId`, `SetDest` (today's
   `planner_core` setter names);
4. `first_event_by_tray[tray] = event(id)` for each entry;
5. if `dag.GetTopologicalOrdering()` fails, return `"Failed to get new total ordering"`.

**`StepsFromDag`** walks `GetTopologicalOrdering()` (error `"Failed to get total ordering"`): a
`TRAY_MOVE` becomes a `MoveRequest`, a `BAY_TRANSITION` or `VECS_TRANSITION` a `StateChange`, any other
event is skipped (today's loop does nothing with it).

**`Plan()` call site** (through `AssignTrays`):

```cpp
stdx::Result Scheduler::AssignTrays(PlanContextSPtr ctx) const {
  auto steps = tray_assignment::StepsFromDag(ctx->event_dag);
  if(!steps) return stdx::Unexpected(steps.error());
  auto result = tray_solver_->Solve(services_, {ctx->initial_state, steps->steps});
  if(!result) return stdx::Unexpected(result.error());
  return tray_assignment::ApplyResult(*result, *steps, ctx->event_dag, ctx->first_event_by_tray);
}

// in Plan():
if(auto assigned = AssignTrays(plan_ctx); !assigned) {
  result.success = true;
  result.message = "Failed tray assignments: " + assigned.error();
  for(const auto& job : request_data.pending_jobs) result.scheduled_jobs.push_back(FailJob(job, assigned.error()));
  return result;
}
```

**Pure means:**

- the result depends only on the arguments;
- nothing reachable from the arguments is written (`Input` is `const`; a `StateChange` holds a pointer to
  `const`, and `Apply` is `const`);
- inputs come by `const&` or by value;
- logging is the only allowed side effect.

The mutable loop state lives in the file-local `Pass`, created inside `Solve`, so `Solve` is pure from the
caller's point of view.

### 6.4 The parity helper

`test/parity.hpp`, namespace `volley::parity`:

- `YAML::Node Canonical(const ScheduleContext& ctx)` (`PlanContext` after commit 3), a map with keys in
  this order:
  - `events`: a sequence of strings, one per vertex of the context's event DAG: `std::to_string(*event)`
    (the `planner_core` `ToString()`, unchanged in this PR) followed by `#<n>` where n counts earlier
    identical strings; **sorted**. Each string's position is the event's canonical index.
  - `edges`: a sequence of `[from, to]` canonical index pairs for every edge of the DAG (the **raw** edge
    set, not reduced; no copy, no `Reduce()`); sorted.
  - `first_event_by_tray`: a map tray id → canonical index, keys sorted numerically (the key is named
    after the field's post-rename name so the files survive commit 3).
- `YAML::Node Canonical(const PlanResponseMsg& response)`: a copy of the message with every action node's
  `guid` replaced by `MakeGuid(0, position + 1)`, every `agv_command.id` (today `std::to_string(guid)`)
  and `scheduled_jobs[].bay_arrival_node_guid` rewritten to the same positional value, and
  `scheduled_jobs` sorted by `std::to_string(job.guid)`; then `YAML::Load(interfaces::msg::to_yaml(copy))`.
  Actions stay in schedule order. Job GUIDs and bay `command_id`s are deterministic already (they come
  from the request or from constants).
- `ExpectReference(actual, suffix)` and `ExpectReference(produce, suffix)` as in step A1. The file is
  written with `YAML::Emitter` in block style plus a final newline, and compared after loading and
  emitting both sides the same way, so formatting never causes a difference.

### 6.5 Error-handling rules

| Today | Proposed |
|---|---|
| `BoolStringPair F()` | `stdx::Result F()` |
| `BoolStringPair F(TrayMove& m, …)` that edits `m` | `stdx::Expected<TrayChoice> F(…)` |
| `return std::make_pair(false, "…" + x);` | `return stdx::Unexpected("…" + x);`: **same text** |
| `auto [ok, msg] = F(); if(!ok) return …` | `if(auto r = F(); !r) return stdx::Unexpected(r.error());` |
| `return {std::nullopt, {}}` after a log line (`ResolveBlockingTrays`) | `return stdx::Unexpected(<the logged text>)`; callers log or ignore |

Keep `E = std::string`. Use `std::to_string(pose)` where today's text does, so the strings stay
identical. `std::format` is fine inside `LOG_*` macros and `stdx::Unexpected(fmt, …)`, but not for strings
that must match today's text byte for byte unless you check the result. The conversion applies to the
tray tree only; `Expand*Job`, `DoAgvAssignments` and `SanityCheckEvents` keep `BoolStringPair` in this PR.

## 7. Invariants (the parity references and reviewers will check these)

1. Every `TrayMove` that will execute has a tray id and a destination after tray assignment.
2. The DAG stays acyclic; `GetTopologicalOrdering()` succeeds after `ApplyResult`.
3. Each tray's moves form a chain in physical order. `first_event_by_tray[tray]` (today
   `first_tray_event`) is that tray's **first** move, never its last (using the last creates cycles).
4. Blocking-tray moves are created in recursive prerequisite order. A tray already being moved is not
   chosen again in the same resolution.
5. AGV matching and arrival ordering are unchanged (untouched in this PR).
6. `Plan()` output is unchanged, except for deliberate behaviour changes listed in section 8.
7. `Reduce()` and path-repair placement stay where they are.
8. `Solver::Solve` writes nothing reachable from its `Input`. `ApplyResult` is the only writer of the
   context, and `StepsFromDag` the only reader of the DAG, in the tray module.
9. `ApplyResult` adds the new moves in creation order and then the edges in creation order, and the
   solver records them in the order today's code calls `AddEvent` and `AddDependency`, so vertex indices,
   edge sets and each vertex's out-edge order match today's. `GetTopologicalOrdering`'s tie-breaking
   depends on out-edge order.
10. Every event is in the DAG once. The solver never sees event pointers for tray moves, so it cannot add
    an input event twice; new moves are created by `ApplyResult` only.

## 8. Known quirks: keep or fix

Behaviour that looks wrong in today's code. Each is marked **keep** (preserve it exactly) or **fix**
(a deliberate behaviour change under rule 3). Reasons are in `DESIGN-REVIEW.md`, section 4.

- `GetAgvOccupiedDuration` always returns `Duration::zero()` (`TODO(isabel)`). **Keep** (AGV stage).
- `Reduce()` runs inside `DoAgvAssignments` **and** again in `Plan()`. **Keep.**
- `DoTrayAssignments` does not reduce: the call is commented out with "Reduce here breaks the
  AgvAssignments for some reason". **Keep**; do not add it.
- `TrayMove::Apply` treats blanks specially (no tray id: no-op; no destination: the tray and its payload
  are removed; another tray on the destination: moved to node 0). **Keep** (planner_core). The solver
  applies moves through temporary `TrayMove`s with both fields set, so it never hits the blank branches.
- Fallback 1 ("advance the root tray"): the recorded path is
  `std::vector<GaragePoseMsg>{gg_.GetVertexFromPose(tray_opt->pose).value(), advance_move->GetDest().value()}`,
  taken after the state was refreshed; by overload resolution this most likely builds *n* copies of the
  destination pose (B1 in the notes). The advance move is applied twice (B2). **Keep** the same expression
  and the double apply; `EmitOptions::check_apply` is false on this path. Confirm what the expression
  builds with a test in commit 6; fix in a follow-up with its own reference diff.
- `AssignDestForUntargetedMove` never registers the original move's source or destination in
  `freeing_moves` (B3). **Keep** behind `CommitOptions`.
- `AddDependency` never checks cycles and silently returns false for a missing endpoint. **Keep**;
  `ApplyResult` adds every new move before any edge, so the missing-endpoint case cannot arise.
- `ScheduleEventDag` vertex indices are `vecS` positions, and removing a vertex renumbers later ones.
  **Never remove from the plan's DAG, and never cache descriptors across a `Remove`.**
- `DoAgvAssignments` throws on a failed topological sort instead of returning. **Keep** (stage F).
- `GetAllPairsMinCost` runs Floyd–Warshall on every `Plan()`. **Keep.**
- **The order in which several occupants of one pose become edges** comes today from an `unordered_set`
  of `shared_ptr`s (pointer hash) and can differ between processes (B4). The solver keys occupancy by id,
  so its order is deterministic. **Fix, if it surfaces** (approved by the user in the design review): this
  is the one difference a parity failure may legitimately trace back to. When it does, re-record the
  affected references in the same commit, show the diff in the review packet, and record it in the notes.
  If it never surfaces, nothing changes.
- The error text `"... TrayId=<id>does not exist in working_state"` lacks a space (B6). **Keep.**

## 9. After this PR (do not implement; for orientation only)

- **Rest of B2, the ROS boundary** (deferred from this PR): `AssetId` / `AssetType` in `core/types.hpp`
  and `ros/convert.hpp` (`ToAssetId`, `ToMsg`), `last_event_by_asset` keyed by `AssetId`, `ScheduledJob`
  instead of `ScheduledJobDataMsg` inside the context, a `Timepoint` context constructor,
  `ReserveBaseScheduleAssets`, the `common_ros` vocabulary aliases and their report. Each is one
  mechanical commit guarded by the references of commit 1.
- **C0, stage folders**: `task_planning/job_expansion/` and `validation/`, `motion_planning/`
  (`PlanMotions` as a free function), `action_graph/` (the anonymous-namespace builders and
  `InsertVrcActionsIntoDag`, with narrowed inputs), one library target each, and an include-boundary
  check.
- **F, AGV module** (new ticket): `task_planning/agv_assignment/` with the same layout, `stdx` types and
  pure cost functions; `SolveInPlace(const Input&, EventDag&)` first; port the 9 direct tests; add direct
  tests for path repair and `AddDepsAfterAmiga`.
- **G, benchmarks** (SW2-487): at least 10 real-site scenarios per solver, timed. The `Solve(services,
  input)` entry point can be timed without a DAG.
- **H, final cleanup:** `SanityCheckEvents` → `ValidateEvents`, `ResponseFromTrajectories` →
  `BuildPlanResponse`; `stdx` for the remaining `BoolStringPair` members; fix B1/B3 with reference diffs;
  optionally move job expansion into `task_planning/job_expansion/`.
- **I, `planner_core` renames** with `[[deprecated]]` aliases: `ScheduleEventDag` → `EventDag`,
  `SetDest` → `SetDestination`, and others.
- **Later:** a swappable motion-planner interface; per-goal heuristic tables instead of Floyd–Warshall;
  `shared_ptr<const ScheduleEvent>` accessors in `planner_core`.

Design `task_planning/tray_assignment/` so that none of these needs the PR's structure undone: the module
depends on `planner_core` only through the adapter and the `StateChange` events.

## 10. Decisions (resolved by Phase R and the user; apply them, record deviations)

| Decision | Resolution |
|---|---|
| Solver injection | Trailing constructor parameter `std::unique_ptr<tray_assignment::Solver>` defaulting to `DefaultSolver`; services passed per `Solve` call, so no lifetime rule. (User: per call.) |
| Module folder and namespace | `include/scheduler/task_planning/tray_assignment/`, `volley::task_planning::tray_assignment`; `scheduler.cpp` declares `namespace tray_assignment = task_planning::tray_assignment;`. (User's choice.) |
| Non-tray events in the input | Bay and VECS transitions travel as `StateChange{shared_ptr<const ScheduleEvent>}`; AGV and VRC events are not steps. (User: accepted.) |
| Parity mechanism | Instrument the existing tests with `ExpectReference`; references named after the test. (User: accepted.) |
| Renames kept in this PR | `Scheduler` members, `Expand*Job`, `PlanContext` and its fields and methods (commits 2 and 3). `stdx` conversion of the tray tree happens inside commits 4 to 8; no separate commit. Deferred: `AssetId`, `ros/convert`, `ScheduledJob`, `Timepoint`, `ReserveBaseScheduleAssets`, vocabulary aliases. (User's choice.) |
| Occupancy-edge order | A deliberate difference if it surfaces; re-record in that commit with the diff. (User: accepted.) |
| B1 (fallback-1 path expression) | Keep for parity; document with a test; follow-up ticket. |
| `scheduler_advanced_tests` | Not touched. (User: leave alone.) |
| Formatter for `GaragePoseMsg` in errors | `std::to_string(pose)`, identical to today. |
| `request_id_str` | Stays (used for `PrintGraph` labels). |
| Scripts (vocabulary, include check) | None in this PR. The module test's link line and one review rule replace the include check. |
| Direct tray tests | Stay in `scheduler_tests` through `AssignTrays`; the module tests cover the solver without a `Scheduler`. |
| `blocking_tray_set.erase` inside the main loop's emission | Dropped in commit 7 as dead code (both containers are cleared right after the loop); stated in the commit body. |

## 11. What to send me at each review gate

The review packet for a commit (rule 12):

- the proposed commit message (header, body, footer);
- the files changed, grouped as logic changes and mechanical changes (renames, moves, call-site updates);
- a short walkthrough of the logic changes: what to look at first and why; for a moved function, what
  changed inside it;
- build and test results: counts of tests run, passed and failed per package; the number of reference
  files compared; the result of the determinism check;
- size: lines added and removed (`git diff --stat`), against the estimate in the commit table;
- for a deliberate behaviour change: which reference files changed and a summary of their diff;
- deviations from this plan, and why;
- open questions, and the exact decision you need from me.

At the last commit of a phase, add the phase summary: the phase's commits (SHA, title, one line each),
the exit criteria with their results, and the `tidy` findings. For phase A, add the list of reference
files with what each covers.

Start with **commit 1** when the user has approved this plan. Do not modify anything in `~/volley`, or
commit anything, until then.
