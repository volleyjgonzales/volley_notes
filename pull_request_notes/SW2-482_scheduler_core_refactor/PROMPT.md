# Claude Code prompt: scheduler core refactor (SW2-484), the tray solver

> **How to use this file.** It lives at
> `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/PROMPT.md`,
> outside the volley repo. Open `~/volley` in the Code tab of the desktop app (local session, Worktree
> off, Accept edits) with the devcontainer running, on `main` freshly pulled.
>
> 1. **Design review (Phase R)**: done on 2026-10-22; the user's answers to its questions are at the end of
>    `DESIGN-REVIEW.md` next to this file. The survey is in the notes file. This file is the plan that came
>    out of it.
> 2. **Stage A (commit 1)**: done. Merged on 2026-10-29 as PR #1007 (`[SW2-1126] Record the scheduler
>    planning tests as scenario files`, main `61e7b0d7`). What landed differs from the original step A1/A2
>    text (scenario files instead of reference files, an opt-in comparison); section 5 "Phase A" and
>    section 6.4 describe the real state, and `SW2-1126_scenario_files/code_notes.md` describes it in full.
> 3. **Stage 2 (phase B2, commits 2 and 3)**, in a new session:
>    `Read /home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/PROMPT.md, review_rules.md and SW2-482_notes.md, then start commit 2.`
>    Claude prepares one commit at a time and stops before committing so you can review it (rule 12).
>    `review_rules.md` holds the team's review conventions as learned in PR #1007; they are part of the
>    ground rules (rule 8).

---

## 1. Your role and the goal

You are implementing the first part of the **scheduler core refactor** in the `scheduler` ROS 2 package
(C++20, colcon, GoogleTest). The goal of this PR is Jira **SW2-484**: put tray assignment behind a
generic, swappable solver interface. You will also do the preparatory work the interface needs:

- parity references for the existing planning tests (**done**: stage A, PR #1007);
- the renames of stage B2 that the user kept: `Scheduler` members, the expansion methods, and the
  per-call context with its fields;
- pure helper functions in a tray-assignment module with its own library target;
- one merged copy of the move-emission code.

The work runs through stages **A**, **B2**, **C1** and **C2** of the plan in section 5 (eight commits),
**one PR per stage**, each PR a sub-ticket of the epic SW2-482 that the user creates (stage A was
SW2-1126). The ROS-boundary types of the old stage B2 (`AssetId`, `ros/convert`, `ScheduledJob`, a `Timepoint`
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

> After every commit, the package builds, every existing test passes, and every recorded scenario
> output matches when the comparison is turned on, except outputs that commit deliberately re-records
> (rule 6).

**Scenario files (stage A, as merged).** Every planning test runs from a scenario file under
`src/planner/scheduler/test/scenarios/`: `plan/<suite>/<Name>[.<suffix>].yaml` for a test through
`Scheduler::Plan` (45 files) and `task_planning/<stage>/<Name>.yaml` for a test that calls
`DoTrayAssignments` or `DoAgvAssignments` directly (13 files). The authored part of a file names the test,
the initial state (`initial_states/<layout>/<name>.yaml`, 60 files) and the request; the recorded part
holds the scheduler's response (or the event DAG before and after the stage) in a canonical, compacted
form. `test/scenarios/README.md` in the repo documents the format and the commands.

The comparison with the recorded part is **opt-in**: a test always asserts its own properties and checks
that its file exists and holds a recording, and it compares with the recording only when
`SCHEDULER_CHECK_RECORDINGS=1` is set. CI runs the property assertions only. That was the team's decision
(Justin Abel, Dan Ambrosio; review log item 156): a change to a planner configuration input (a cost, a
speed, a site layout) moves every recording and must not force a re-record. **For this refactor, parity
is checked with the variable set** (rule 5): a refactor commit is green only when that run passes and
`git status` shows no change under `test/scenarios/`.

A recording records **today's behaviour, including its bugs**. It is not ground truth. It changes only
when a commit changes behaviour on purpose, and then the diff of each scenario file shows reviewers
exactly which behaviour changed (rule 6).

Each stage is a PR of a few commits (the table in section 5), reviewed commit by commit, and each commit
must:

- have **one scoped objective**, stated in its title;
- compile;
- pass all tests;
- pass the parity check with the comparison on.

## 2. Reference material

- **This plan's review:** `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/DESIGN-REVIEW.md`: what changed from the original plan and why, the
  parity decisions, and the user's answers to the open questions.
- **The notes file** (rule 11): `/home/jon-gonzales/repos/volley_notes/pull_request_notes/SW2-482_scheduler_core_refactor/SW2-482_notes.md`. It holds the Phase 0 survey: the baseline
  numbers, where every symbol is, the assumption checks, a list of bugs found but not fixed (B1 to
  B11), and the review log of stage A (items 1 to 157). Read its Status section and the log's last
  items at the start of every session.
- **The review rules:** `review_rules.md` next to this file, what the team's reviewers and Greptile check
  and what PR #1007 taught (its section 7 is the list from that PR). Apply it to every line you write.
- **Stage A as merged:** `SW2-1126_scenario_files/code_notes.md` (the test support library, how a test
  run flows, the comparison, the review items and their answers) and, in the repo,
  `src/planner/scheduler/test/scenarios/README.md`. Read the code notes' sections "The files under
  src/planner/scheduler/test/" and "How a test run flows" before touching the tests.

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
   - accompanied by re-recorded scenario files in the same commit (rule 6), with the commit body and
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
   - run the scheduler tests twice: once as CI runs them, once with the comparison on;
   - run `planner_core` and `scheduler_advanced_tests` at the end of commits 3, 5 and 8, or more often
     if you touched anything they see (`scheduler_advanced_tests` sees only `Scheduler(layout, logger,
     params)`, `SchedulerParams::bay_readiness_ratio` and `Plan()`).

   You run on the host; the toolchain is in the devcontainer. Run every build and test through the
   `volley-in-container` wrapper described in `CLAUDE.local.md`. It prints a short summary and keeps the
   full log on disk:
   ```bash
   volley-in-container build scheduler scheduler_advanced_tests
   volley-in-container test scheduler
   SCHEDULER_CHECK_RECORDINGS=1 volley-in-container test scheduler   # the parity check
   volley-in-container test planner_core scheduler_advanced_tests
   ```
   `test` prints `colcon test-result` per package. A green build does not mean the tests ran: check the
   test counts in that summary (baseline on main `61e7b0d7`: scheduler 187 as `colcon test-result` counts
   them, which is 92 `TEST` cases in 19 binaries; planner_core 23; scheduler_advanced_tests 16). One test
   binary can be run directly, for example
   `volley-in-container gtest scheduler retrieve_job_tests 'RetrieveJob.FromStall'`; the wrapper passes
   `SCHEDULER_CHECK_RECORDINGS=1` through to `test` and `gtest`. The parity check is green when the run
   with the variable passes **and** `git status` shows nothing changed under `test/scenarios/`.
6. **Scenario files and test data.**
   - Re-record only through `volley-in-container record-reference scheduler <binary>` (it sets
     `RECORD_REFERENCE_OUTPUT=1`, which rewrites the recorded part of every scenario file the binary
     runs, and asks the user for approval; the wrapper refuses that variable in any other command). Any of
     the 19 binaries under `build/scheduler/` can be recorded; the `jobs/` binaries hold the plan
     scenarios, `tray_assignment_tests` and `agv_assignment_tests` the stage scenarios. Record only in a
     commit that makes a deliberate behaviour change (rule 3), then run the parity check in a fresh
     process. Never re-record to make an unexpected difference go away.
   - Never hand-edit a recorded part: the format (`Compact`, `Emit` in the test support) is fixed, and
     recording rewrites it anyway. The authored part is hand-written and kept byte for byte.
   - A new planning test is a new scenario file with its authored part only (`test`, `description`,
     `initial_state`, `scheduler`, `request`); its first recording adds the rest. A new initial state is a
     file under `initial_states/<layout>/`, named after what stands in the garage, shared by the scenarios
     that start from it. `test/scenarios/README.md` has the key tables.
   - Every test data file you add is YAML with the `.yaml` extension (the team's hooks reject `.yml`).
     Read and write it with `yaml-cpp`, which the test support already links. Do not add a JSON library or
     JSON files.
7. **Git hygiene.**
   - One branch per stage, created from `main` on the host with `git switch -c`, named
     `jmg/SW2-<ticket>/<slug>` where the ticket is the stage's sub-ticket under the epic, which the user
     creates and names (stage A: `jmg/SW2-1126/scheduler-scenario-files`). The pre-push hook
     `scripts/check_branch_name.sh` checks the form; the Jira integration links the branch by its key, so
     commit messages carry no key.
   - Stage files by name with `git add <files>` on the host, never `git add -A` or `.`. Commit only with
     `volley-in-container git commit ...`, so the team's prek and commitlint hooks run (they are installed
     in the container, not on the host).
   - Never push: the user pushes, and force-pushes with lease after an amend. Amend or rebase only when
     the user says so for that change ("amend", "approved"); the wrapper's `ALLOW_AMEND` / `ALLOW_REBASE`
     flags exist for that and for nothing else. Never reset, never force, never skip hooks. Do not touch
     the working tree while the user is pushing.
   - Commit messages must pass commitlint (`@commitlint/config-conventional`, see `.commitlintrc.yaml`),
     in the form the team accepted in PR #1007:
     - header: `<type>(scheduler): <imperative summary in lower case>`, at most 100 characters, no
       step tag and no ticket key. The summary must not start with a capital letter.
     - type: as listed in the commit table in section 5. Allowed types: build, chore, ci, docs, feat,
       fix, perf, refactor, revert, style, test, wip.
     - body: a blank line after the header, paragraphs of lines at most 100 characters, saying what
       changed and why, in an objective tone (no judgement on earlier authors, no colloquialisms:
       "decommissioned", not "defunct"); the parity check and the test counts go in the PR body, not here.
     - no footer; the PR body ends with `Refs: SW2-<ticket>`.
     - Example header: `refactor(scheduler): merge the two tray move-emission blocks`.
   - Use the titles in the commit table in section 5. The bracketed titles on the steps (`[B2] ...`)
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
   - At the end of commits 3, 5 and 8, and before every push the user makes, run
     `volley-in-container tidy` (the team's clang-tidy hook on lines changed since `main`; CI runs the
     same check on push). Fix findings in code you added or moved. Record findings in code you only
     renamed or did not touch, without fixing them.
   - **Follow `review_rules.md`**, section 7 in particular: comments say only the why, and briefly (two
     drafts in PR #1007 were sent back as too verbose); explicit `interfaces::msg::X` types with their
     includes, no `*Msg` aliases in new code; the package's own headers in quotes, other packages' in
     angle brackets; `volley::scheduler` for new code in the library, `volley::scheduler::test` for test
     code; `Is...` for bool predicates; `== nullptr` where the neighbouring code compares that way. Assess
     each Greptile finding before applying it: in PR #1007 about half were right.
   - Keep the footprint small (objective 2): prefer one clear function over several thin ones, standard
     algorithms over hand-written loops where they read better, and deleting dead code over keeping it.
     Report lines added and removed per commit in the review packet (`git diff --stat`).
   - C++20 with GCC 13 (objective 3). Use the standard library where it fits; no C++23 features.
   - Add `[[nodiscard]]` to new functions that return `stdx::Expected` / `stdx::Result`.
   - Do not add new dependencies to `package.xml`. `stdx`, `motion_planner`, `task_planner`, `planner_core`,
     `common_ros`, `cost_functions`, `yaml-cpp` (test) and `ament_index_cpp` (test) are already declared
     (verified in Phase 0).
9. **Tests come with extractions.** Every function declared in a public header of the tray module gets a
   test in the module's own binary (section 10 names it) that constructs no `Scheduler` and no
   `ScheduleEventDag`. File-local helpers (anonymous namespace) are tested through the function that
   calls them. Tests follow the conventions of stage A: one file per suite under `test/src/<folder>/`,
   one binary per file, registered in the `scheduler_tests` list of `CMakeLists.txt` (the module test
   is the exception: it must not link `${PROJECT_NAME}_test_support`, which links the scheduler, so it
   gets its own `volley_add_gtest` call); namespace `volley::scheduler::test`; names of at most five
   words. Use the layouts stage A settled on, found with `GetLayoutPathByName`: `275_sunrise_b` by
   default, `38_gramercy` for EV chargers (the only current site with them), `5675_pecos_combined` for
   bays and AGV chargers, `tiny_lot` only where a full lot is needed (the blocking-tray fallbacks);
   `576_eccles*` and `1355_fulton` are decommissioned and not to be used. Garage states come from files
   under `test/scenarios/initial_states/<layout>/`, loaded with `initial_states::Load("<layout>/<name>")`
   (`test/include/scheduler/test/initial_states.hpp`), never from YAML literals in the source.
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
    6. **After the PR is open**, the same loop runs on the reviewers' items (Greptile first, then the
       teammates), as in PR #1007: the user pastes one item at a time; assess it (say whether it is
       right, and why), propose the patch, verify it in the container, write it into the stage's code
       notes and the review log, and amend it **only on the user's word** into the commit the user
       names; the user force-pushes. The PR keeps its commit count. Before every amend: formatter,
       rebuild with 0 warnings, both test runs of rule 5, the prek hooks on the touched files
       (`volley-in-container sh 'prek run --files <files>'`), and `volley-in-container tidy` once the
       amend is in (the hook diffs `main..HEAD`, so run it after, not before). Draft replies to the
       reviewers when asked; the user posts them.

    If you disagree with a feedback item, say why and ask; don't silently skip it. At the last commit of
    a phase, also meet the phase's exit criteria (including `scheduler_advanced_tests` and
    `volley-in-container tidy`) before posting the review packet. At the end of a stage, draft the PR
    text (title `[SW2-<ticket>] ...`, body `# What`, `# Why`, `# Testing`, `Refs:`) and the sub-ticket
    text into the stage's folder, as `SW2-1126_scenario_files/` has them.

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

**Tests that call stages directly** (after stage A; all under `src/planner/scheduler/test/src/`).
`stages/tray_assignment_tests.cpp` calls `scheduler.DoTrayAssignments(ctx)` 4 times and
`DoAgvAssignments` twice; `stages/agv_assignment_tests.cpp` calls `DoAgvAssignments` 8 times;
`ResolveBlockingTrays` is called once in `stages/tray_assignment_tests.cpp` and once in
`jobs/clean_garage_job_tests.cpp`. They build the context as `std::make_shared<ScheduleContext>(...)`
and add events with `ctx->events.AddEvent / AddDependency` (about 60 uses of `ctx->events` across the
four stage files). The test support reads the context too: `scenarios::Dag(const ScheduleContext&)` in
`test/src/scenarios/stage.cpp` (declared in `test/include/scheduler/test/scenarios/stage.hpp`) reads
`ctx.events` and `first_tray_event`. There are 92 `TEST` cases in 19 binaries (one file, one suite, one
binary each: `scheduler_tests`, five under `stages/`, ten under `jobs/`, four under `utils/`), the
support library `${PROJECT_NAME}_test_support`, no fixtures, and no test reads the clock
(`scenarios::kNow`). Tests use `GetGarageGraph()` (3, `stages/sanity_check_tests.cpp`),
`disabledness_filters` (3, same file), `last_entity_event` (18) and `UpdateLastEntityEvent` (4, both in
`stages/scheduler_state_tests.cpp`); none uses `gg_`, `table_`, `PrintDags`, `PushBackScheduledJob` or
`UpdateLeafDependencies`. Outside the tests, `src/scheduler_ros.cpp` sets `scheduler_->printdags_`
directly (line 20) and calls `PrintDags()` from the `debug/printdags` service (line 55); nothing outside
the package uses the renamed members (the `GetGarageGraph` hits in `motion_planner`'s tests are those
tests' own helpers).

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
positions. Job GUIDs are fixed by the scenario loader (request 1000, jobs 1001 upwards).
`BuildScheduledActionsArray` refills `scheduled_jobs` from an `unordered_map`, so the canonical response
sorts that list by GUID (review log item 155).

## 5. The plan: phases and commits

Stage letters match the study pack's staged plan. Each phase lists **steps** that describe the work in
detail. Commits group the steps as follows:

| # | Commit header (after `<type>(scheduler): `) | Type | Steps | Objective | Est. size (+/−) |
|---|---|---|---|---|---|
| 1 | **done**, PR #1007: `record the planning tests as scenario files` + `add a viewer page for the test scenarios` | test, feat | A | Record today's behaviour before any change. | 58 scenario files, 60 initial states, the support library, the viewer |
| 2 | `rename scheduler members and expansion methods` | refactor | B2-1, B2-2 | Purely mechanical renames inside `Scheduler`; no logic change. | +400 / −400 |
| 3 | `rename ScheduleContext to PlanContext and its fields` | refactor | B2-3 | The per-call context in its own header, with the catalogue's names. | +300 / −280 |
| 4 | `add garage services and the tray heading and empty-tray helpers` | refactor | C1-1 to C1-3 | `GarageServices`, the module's library and test targets, the first pure helpers. | +330 / −120 |
| 5 | `make blocking-tray resolution a free function with plain results` | refactor | C1-4 | `ResolveBlockingTrays` and its two searches leave `Scheduler`; results are plain data. | +320 / −300 |
| 6 | `extract the main-loop decisions of tray assignment` | refactor | C1-5 | Destination check, critical path, blocker scan, parking-spot choice as pure functions. | +260 / −200 |
| 7 | `merge the two tray move-emission blocks` | refactor | C1-6 | One emission function and one root-commit function; the riskiest change, alone. | +120 / −160 |
| 8 | `put tray assignment behind a solver interface` | refactor | C2-1 to C2-4 | `Solver`, `DefaultSolver`, adapter, `Scheduler::AssignTrays`, injection; legacy members deleted. | +500 / −450 |

Stages map to PRs: stage A was commit 1 (PR #1007); stage 2 is phase B2, commits 2 and 3, one PR; C1
and C2 follow, each its own PR unless the user groups them. Each commit goes through the review gate
in rule 12. Two named split points keep the count within ten:
commit 3 may become "type rename" then "field renames"; commit 8 may become "module added, not yet used"
then "switch `Plan()` and delete the legacy members" (the first half then keeps the old loop alive for one
commit).

### Phase R: design review

Done on 2026-10-22; report and the user's answers in `DESIGN-REVIEW.md`. Phase 0 (the survey) was done as
part of it; its findings are in the notes file.

### Phase A: parity baseline (done, PR #1007)

What was planned as `test/parity.hpp` and `test/reference/` landed as **scenario files** and a test
support library, after the design was reworked during the review rounds (review log items 1 to 157).
The state to build on:

- `test/scenarios/`: 45 plan scenarios (`plan/<suite>/`), 13 stage scenarios
  (`task_planning/tray_assignment/`, `task_planning/agv_assignment/`), 60 initial states
  (`initial_states/<layout>/`), a README with the formats and commands.
- `test/include/scheduler/test/` and `test/src/`: `initial_states.{hpp,cpp}`, `agv_commands.hpp`, and
  `scenarios/{yaml,file,request,recording,shared_scheduler,plan,stage}.{hpp,cpp}`, compiled into the
  static library `${PROJECT_NAME}_test_support`. The entry points a test calls: `scenarios::Plan()`
  (plans the running test's scenario once, checks the file, returns scenario, scheduler, request and
  response), `scenarios::ExpectDeterministic()` (one `TEST(<Suite>, Deterministic)` per job binary: plans
  every file of the suite twice and compares the two runs; never gated), `scenarios::Stage("<stage>")`
  and `scenarios::ExpectStage(...)` with `scenarios::Dag(ctx)` for the stage tests,
  `scenarios::SharedScheduler(layout_path, params)` (one scheduler per layout and parameter set per
  binary), `scenarios::kNow`.
- 19 test binaries, one per file under `test/src/{stages,jobs,utils}/` plus `scheduler_tests`, 92
  `TEST` cases, all in `volley::scheduler::test`.
- `tools/view_scheduler_tests` and `tools/plan_viewer/` (`poe scheduler-test-viewer`): the HTML viewer of
  the scenario files, the review aid for recording diffs.
- The comparison is opt-in (`SCHEDULER_CHECK_RECORDINGS=1`); recording is `RECORD_REFERENCE_OUTPUT=1`
  through the wrapper's `record-reference`.

Known gaps and points the notes record: REBALANCE_GARAGE, `planned_jobs` and `active_jobs` are still
never covered end to end; the insert-heading rule (`InitRetrievalHeadings`) is exercised by no test on
the sites; `ReparkTrayJob.UnplugsChargerAgvMovesFirst` duplicates `UnplugsCharger`; the two blocking-tray
fallbacks stay on `tiny_lot`. Details: `SW2-1126_scenario_files/scenario_selection.md`, section 8.

### Phase B2: names (mechanical; commits 2 and 3)

No planning logic changes. Parity must stay green **without** touching any scenario file: run the
scheduler tests with `SCHEDULER_CHECK_RECORDINGS=1` after every step and confirm `git status` is clean
under `test/scenarios/`. If the test support reads a renamed type or field (`scenarios::Dag` does),
update it in the same commit; that is allowed. Error strings that spell an old method name stay as they
are (rule 1); log lines may follow the new names. This stage is a PR of its own: the user creates the
sub-ticket under SW2-482 and the branch `jmg/SW2-<ticket>/<slug>` from `main` at `61e7b0d7` or later.

- **B2-1** `[B2] Rename Scheduler members` (commit 2)
  - `gg_` → `motion_graph_`, `table_` → `collision_table_`, `GetGarageGraph()` → `GetMotionGraph()`
    (three uses in `test/src/stages/sanity_check_tests.cpp`).
  - `pg_` becomes a local in the constructor (Phase 0 verified it is used only to build `gg_`).
  - `costaudit_` → `cost_audit_`, `printdags_` → `print_dags_`, `PrintDags()` → `TogglePrintDags()`.
  - Update the callers in `src/scheduler_ros.cpp`: it assigns `scheduler_->printdags_` from the
    `printdags` parameter (line 20) and calls `PrintDags()` in the `debug/printdags` service (line 55);
    check `scheduler_component.cpp` with `rg`. `scheduler_advanced_tests` uses none of them.
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
    `UpdateLeafDependencies` → `AddAfterJobLeaves`. The tests in `test/src/stages/scheduler_state_tests.cpp`
    that name `UpdateLastEntityEvent` and `last_entity_event` follow the new names (they have no scenario
    files; a test that has one keeps its name or renames the file with it).
  - `request_id_str` stays: it labels the `PrintGraph` output under `print_dags_`. The constructor keeps
    taking `rclcpp::Time` (the `Timepoint` constructor is a later PR).
  - Update the test support: `scenarios::Dag(const PlanContext&)` and `ExpectStage` in
    `test/src/scenarios/stage.cpp` and `test/include/scheduler/test/scenarios/stage.hpp` read `events`
    and `first_tray_event`; the recorded key is already `first_event_by_tray`, so no scenario file
    changes. Update the ~60 `ctx->events` uses in the four stage test files.
  - Split point: the type rename and header move first, then the field and method renames, if one commit
    is too large to review.

Exit criteria for phase B2: all tests pass as CI runs them and with `SCHEDULER_CHECK_RECORDINGS=1`, with
every scenario file unchanged (`git status` shows no change under `test/scenarios/`);
`scheduler_advanced_tests` and `planner_core` build and pass; `volley-in-container tidy` is clean on
the changed lines; the stage's PR text is drafted.

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
    `${PROJECT_NAME}`) and the module's gtest (section 10 names it; `tray_assignment_tests` is taken by
    the stage tests of `test/src/stages/`), which links `scheduler_tray_assignment` and `yaml-cpp` but
    **not** `${PROJECT_NAME}` nor `${PROJECT_NAME}_test_support`, so it is added with its own
    `volley_add_gtest` call outside the `scheduler_tests` loop. Check that the static target receives the
    package's dependencies (`ament_auto_add_library` calls `ament_target_dependencies`); if not, add them
    explicitly.
  - In `test/src/task_planning/<module test>.cpp`, a small helper that builds the services from a
    layout name the way `Scheduler::Scheduler` does (`Layout` from file, `PoseGraph`, `GarageGraph`,
    `CollisionTable`, `cost::MotionCostModel` from default params, a logger) and owns them for the test's
    lifetime. Garage states for these tests come from `initial_states::Load` (rule 9), which the module
    test may use: `initial_states.cpp` depends on `common_ros` only, not on the scheduler; if linking it
    without the support library is awkward, compile it into the module test directly.
- **C1-2** `[C1] Move the heading helpers to tray_assignment/headings` (commit 4)
  - `EvChargeHeading`, `RetrievalHeading`, `PreferredHeading` as in section 6.3: they return the adjusted
    pose instead of editing a reference, and `PreferredHeading` drops the unused tray argument.
  - Update the callers: `ExpandAgvMoveJob`, `ExpandReparkTrayJob`, `ExpandChargePayloadJob`,
    `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`, `DoTrayAssignments` (two places). Delete
    the three members.
  - Tests: `EvChargeHeading` on the EV-charger stalls of `38_gramercy` (the rule was written for
    `576_eccles`, which is decommissioned: check on the branch which layouts it still engages on, and
    use a site) and empty elsewhere and on other layouts; `RetrievalHeading` with and without a payload,
    and with `reciprocal_to_tray` (stage A found the rule caches no heading for the stalls of
    `5675_pecos_combined` and cannot apply on `275_sunrise_b`: see `scenario_selection.md`).
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
  - Move the `ResolveBlockingTrays` test of `test/src/stages/tray_assignment_tests.cpp` to the module
    test (no `Scheduler`), asserting on the plain fields. Add a test for the waypoint-stash tier
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
  - Tests on `275_sunrise_b` (a `tiny_lot` state only where a full lot is needed): a disabled destination fails with the exact text; the critical
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
  - This is the riskiest commit of the phase. Run the full scheduler suite with the comparison on; every
    recording must match unchanged.

Exit criterion for phase C1: all tests pass, every recording matches unchanged, the module test covers
every public function of the module, `volley-in-container tidy` run after commits 5 and 7.

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
    `test/src/scheduler_tests.cpp`: a `FakeSolver` injected through the constructor whose `Solve` returns
    `stdx::Unexpected("nope")` makes `Plan()` report `"Failed tray assignments: nope"` and fail every
    pending job.
  - Split point: C2-1 to C2-3 with their module tests first (the old loop still runs), then C2-4.

Exit criteria for phase C2 (and for the PR):

- no production call to the removed methods; `rg DoTrayAssignments` finds nothing in `src/` or `test/`;
- all tests pass and every recording matches unchanged (or changed only by the deliberate difference of
  section 8, recorded in the same commit with its diff);
- the module test links without `${PROJECT_NAME}` and constructs a `DefaultSolver`;
- `scheduler_advanced_tests` and `planner_core` pass;
- `volley-in-container tidy` is clean on added and moved code;
- the notes file is finished (decisions, deviations, deferred bugs) and the PR description is drafted from
  it into the stage's folder next to this file (`SW2-<ticket>_<slug>/pr_description.md`, not committed).

## 6. Specifications

### 6.1 Source tree (target state after this PR)

```
scheduler/
├── CMakeLists.txt                     # + scheduler_tray_assignment (static) and the module test; the scheduler_tests list and ${PROJECT_NAME}_test_support exist since stage A
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
└── test/                              # stage A's layout; see SW2-1126_scenario_files/code_notes.md
    ├── .clang-tidy                    # disables bugprone-unchecked-optional-access for the tests
    ├── include/scheduler/test/        # initial_states.hpp, agv_commands.hpp, scenarios/{yaml,file,request,recording,shared_scheduler,plan,stage}.hpp
    ├── src/
    │   ├── initial_states.cpp, scenarios/*.cpp          # ${PROJECT_NAME}_test_support
    │   ├── scheduler_tests.cpp
    │   ├── stages/{tray_assignment,agv_assignment,assignment_cost,sanity_check,scheduler_state}_tests.cpp
    │   ├── jobs/<job>_tests.cpp (10), utils/<topic>_tests.cpp (4)
    │   └── task_planning/<module test>.cpp              # new in C1; links only scheduler_tray_assignment
    └── scenarios/                     # README.md, initial_states/<layout>/*.yaml, plan/<suite>/*.yaml, task_planning/<stage>/*.yaml
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
  # ${PROJECT_NAME}_test_support (SCHEDULER_SCENARIO_DIR, GTest::gtest, yaml-cpp) and the
  # scheduler_tests loop exist since stage A; the module test stays outside that loop
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

### 6.4 The test support (stage A, as merged)

The support library under `test/include/scheduler/test/` and `test/src/`, namespace
`volley::scheduler::test` with the nested `scenarios` and `initial_states`. What a refactor commit needs
to know:

- `scenarios::Dag(const ScheduleContext& ctx)` (`stage.hpp`): the context's event DAG as a document:
  `events` (one string per vertex, `ScheduleEvent::ToString()` plus ` #n` for repeats, sorted),
  `edges` (`[from, to]` positions, sorted) and `first_event_by_tray` (tray id to position). This is the
  function commit 3 updates for the renamed type and fields; the keys do not change.
- `CanonicalResponse(const interfaces::msg::PlanResponse&)` (`plan.cpp`): action-node GUIDs replaced by
  `MakeGuid(0, position + 1)` (also in the charger and conveyor command ids and `bay_arrival_node_guid`),
  `scheduled_jobs` stable-sorted by `std::to_string(job.guid)`, then `MessageYaml` and `Compact`
  (default-valued fields left out, GUIDs as one scalar, short maps on one line).
- `ExpectRecorded(path, recorded)` (`recording.cpp`): the file must exist, name the running test and
  hold a recorded part; with `SCHEDULER_CHECK_RECORDINGS` set it compares line by line (`ExpectSameDocument`,
  first differing line in the failure message); with `RECORD_REFERENCE_OUTPUT` set it rewrites the
  recorded part, building the whole text before opening the file.
- `scenarios::ExpectDeterministic()`: plans every scenario of the suite twice in one process and compares
  the two canonical responses with each other; it does not read the files and is never gated.
- The YAML decoders are `YAML::convert<T>` specialisations with key tables (`yaml.hpp`); an unknown key
  fails the load with the file name and the key.

Nothing in the plan's old `test/parity.hpp` exists; do not add it.

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

## 7. Invariants (the recorded scenarios and reviewers will check these)

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
  builds with a test in commit 6; fix in a follow-up with its own recording diff.
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
  affected scenario files in the same commit, show the diff in the review packet, and record it in the notes.
  If it never surfaces, nothing changes.
- The error text `"... TrayId=<id>does not exist in working_state"` lacks a space (B6). **Keep.**

## 9. After this PR (do not implement; for orientation only)

- **Rest of B2, the ROS boundary** (deferred from this PR): `AssetId` / `AssetType` in `core/types.hpp`
  and `ros/convert.hpp` (`ToAssetId`, `ToMsg`), `last_event_by_asset` keyed by `AssetId`, `ScheduledJob`
  instead of `ScheduledJobDataMsg` inside the context, a `Timepoint` context constructor,
  `ReserveBaseScheduleAssets`, the `common_ros` vocabulary aliases and their report. Each is one
  mechanical commit guarded by the recordings of stage A.
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
  `BuildPlanResponse`; `stdx` for the remaining `BoolStringPair` members; fix B1/B3 with recording diffs;
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
| Parity mechanism | Landed in stage A as scenario files named after the test, with an opt-in comparison (`SCHEDULER_CHECK_RECORDINGS=1`); CI runs the property assertions only. (Team decision in PR #1007.) |
| Renames kept in this PR | `Scheduler` members, `Expand*Job`, `PlanContext` and its fields and methods (commits 2 and 3). `stdx` conversion of the tray tree happens inside commits 4 to 8; no separate commit. Deferred: `AssetId`, `ros/convert`, `ScheduledJob`, `Timepoint`, `ReserveBaseScheduleAssets`, vocabulary aliases. (User's choice.) |
| Occupancy-edge order | A deliberate difference if it surfaces; re-record in that commit with the diff. (User: accepted.) |
| B1 (fallback-1 path expression) | Keep for parity; document with a test; follow-up ticket. |
| `scheduler_advanced_tests` | Not touched. (User: leave alone.) |
| Formatter for `GaragePoseMsg` in errors | `std::to_string(pose)`, identical to today. |
| `request_id_str` | Stays (used for `PrintGraph` labels). |
| Scripts (vocabulary, include check) | None in this PR. The module test's link line and one review rule replace the include check. |
| Direct tray tests | Stay in `test/src/stages/tray_assignment_tests.cpp` through `AssignTrays`; the module tests cover the solver without a `Scheduler`. |
| Module test binary name | `tray_assignment_tests` is taken by the stage tests since stage A. Default: `tray_assignment_module_tests` at `test/src/task_planning/tray_assignment_module_tests.cpp`, suite `TrayAssignmentModule`; the user may pick another name at commit 4's review gate. |
| Stage A's open points | The duplicate `ReparkTrayJob.UnplugsChargerAgvMovesFirst`, the two `tiny_lot` fallback scenarios, the uncovered insert-heading rule and REBALANCE_GARAGE stay as they are until the user decides (`scenario_selection.md`, section 8); not this stage's work. |
| `blocking_tray_set.erase` inside the main loop's emission | Dropped in commit 7 as dead code (both containers are cleared right after the loop); stated in the commit body. |

## 11. What to send me at each review gate

The review packet for a commit (rule 12):

- the proposed commit message (header, body, footer);
- the files changed, grouped as logic changes and mechanical changes (renames, moves, call-site updates);
- a short walkthrough of the logic changes: what to look at first and why; for a moved function, what
  changed inside it;
- build and test results: counts of tests run, passed and failed per package, for both runs of rule 5;
  `git status` under `test/scenarios/` after the run with the comparison on;
- size: lines added and removed (`git diff --stat`), against the estimate in the commit table;
- for a deliberate behaviour change: which scenario files changed and a summary of their diff;
- deviations from this plan, and why;
- open questions, and the exact decision you need from me.

At the last commit of a phase, add the phase summary: the phase's commits (SHA, title, one line each),
the exit criteria with their results, and the `tidy` findings.

Start with **commit 2** (step B2-1) once the user has created the stage's sub-ticket and branch, or
tells you the names to use. Do not modify anything in `~/volley`, or commit anything, until then.
