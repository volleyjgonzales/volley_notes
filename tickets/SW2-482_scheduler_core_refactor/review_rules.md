# Review rules distilled for the refactor's PRs

What Greptile and the team's reviewers check in VolleyAutomation/volley, distilled from the
Greptile configuration (its custom instructions), the implicit-guidelines report over 53 PRs
(2026-09-23 to 2026-10-26) and what was applied to SW2-1126. Each rule says what to do and, where
it was learned the hard way, what it cost. The checklist at the end is the pre-PR pass.

## 1. Commits and the PR

- **Conventional Commits header**, `type(scope): summary`, summary in lower case, header and body
  lines at most 100 characters (commitlint enforces this). `fix` only for defects that already exist
  on main; `test`, `refactor`, `feat`, `chore`, `docs`, `ci` otherwise.
- **One coherent change per commit.** A commit that mixes unrelated concerns is flagged; a later
  commit that only corrects an earlier one in the same PR is squashed into it. The team regroups
  commits on request. Applied: the viewer is its own commit next to the tests.
- **The summary says what the diff does**, specifically enough to read without the diff. No `wip`,
  `fixes`, `cleanup`, `address review comments`. Flagged: a message that describes something other
  than the diff.
- **PR title** `[SW2-xxxx] Description`, never a key alone or a type alone. Branch
  `<initials>/SW2-xxxx/<slug>` (`scripts/check_branch_name.sh`), which is also how the Jira
  integration links the branch; commit messages carry no key.
- **PR body** in the repo's form: `# What`, `# Why`, `# Testing` (checkboxes of what was run), a
  `Refs: SW2-xxxx` line. Alternative: `## Summary`, `### Changes`, `## Fix`.
- **Traceability.** The body lists every behaviour change, changed constant, dropped or added
  check, incidental bug fix, and why any tool or unrelated-looking piece belongs in the PR. Flag
  from jlessner: "call them out in the PR description". Unrelated changes go to their own PR or a
  ticket.
- **Scope.** Greptile flags anything outside the stated ticket. State the scope in the body and
  answer a scope finding with the reason the piece is needed.

## 2. Comments and documentation

- **A comment says why, in a line or two.** Delete comments that restate the code. Flagged:
  narrative blocks, history ("before X was added ... after"), recaps of PR discussion, comments that
  go stale on the next change. Applied: a 15-line history block and an "ordering should now be"
  list cut to one or three lines each.
- **Comment only when necessary to explain the why** (dambrosio, PR #1007, on generated comments):
  verbose comments and comments that repeat the implementation are "human context overload". A
  label over an assertion that reads the same as the assertion goes; a module docstring is a
  purpose statement, not a tour; the tour belongs in the README. Applied across the PR: 130 comment
  lines cut to 43 in 22 files.
- **`///` doxygen on headers**, used the same way throughout a file; no mixing of `//` and `///` for
  docs. Omit `@brief` when the name already says it. One-line docstrings in Python; no
  Args/Returns blocks that repeat the signature.
- **No commented-out code, no leftover debug output, no disabled `LOG_DEBUG`**, in C++, Python,
  JS or YAML. Applied: three `DrawGraph` calls that wrote `/tmp/*.dot` on every test run.
- **`TODO`/`FIXME` carry a ticket key**, or are resolved or removed. Applied: four without a key,
  one of which claimed a test fails that passes.
- **Stale docs.** A change that invalidates a nearby comment, docstring, README, help text or
  example updates it. Grep for renamed files, flags, examples and docs pages. Applied: a README
  example that named a file that no longer existed; the `pyproject` comment with the tool's old
  name; deprecated docs that listed a resolved test.
- **Context at the usage site**, not at the definition; constants and helpers live where they are
  used.

## 3. C++ rules the reviewers apply most

- **Optionals and `Expected`: `.has_value()` and `.value()`, never `*x` or `x->`**, so a failure
  gives a stack trace instead of undefined behaviour (dambrosio, 21 comments). Early return with
  `Unexpected`; `[[nodiscard]]` on every `Expected`- or value-returning function. The test folder
  may disable `bugprone-unchecked-optional-access` (agvhito precedent) because the check cannot
  see gtest's assertions, but that covers `.value()` only: `->` on an optional still has to be
  guarded.
- **Reuse before writing** (20 comments): look in `stdx`, `yasminx`, `rclcppx`, `common`,
  `common_ros` and the existing test utilities. Never keep two copies of a definition. Applied:
  `std::to_string(GuidMsg)` instead of a hand-rolled hex loop.
- **Include what you use, nothing more**; no aggregator headers; every used package is a
  `<depend>` in package.xml and every unused one is removed (`volley_add_library` links from
  package.xml, so a missing `<depend>` is the real failure mode). Test targets link only what they
  use. Applied: `ament_index_cpp` dropped once its one use was gone.
- **Clocks and time**: the ROS steady/sim clock (`rclcppx::GetSteadyOrSimClock`), `std::chrono`
  durations, `std::optional<rclcpp::Time>` for an unset time. A default-constructed `rclcpp::Time`
  is `RCL_SYSTEM_TIME` and comparing it with a ROS stamp throws (a "Blocker" from dambrosio).
  Applied: one `scenarios::kNow {0, 0, RCL_ROS_TIME}` instead of fifteen `rclcpp::Time()`.
- **Naming**: one vocabulary per concept (`Timeout` vs `Period`), names that say what the thing
  is, the `.clang-tidy` naming rules (`kConstant` at file scope, `k_constant` for a local
  constant, `member_`, `FunctionName`), new code in a `volley::` namespace.
- **`std::format`** for string building, concise log lines, `inline constexpr auto` for
  constants.
- **Simplify**: no redundant defensive checks, no overrides that repeat the base, no locks that
  guard nothing, a `Config` struct instead of a long list of same-typed parameters, explicit
  defaults rather than a default that hides a behaviour change.
- **Ownership and threads**: `RCPPUTILS_TSA_GUARDED_BY` on shared members, no raw pointers into
  data that gets replaced, no blocking in `Step()`.

- **Namespaces: `volley::<package>` for a package, `volley::<package>::test` for its test helpers**
  (dambrosio, PR #1007): a developer once stripped the packages' namespaces, so much code sits in
  bare `volley`, which invites collisions and longer names; new code goes under the package's
  namespace. Precedent: `volley::agvhito::test`, `volley::yasminx::test`. Applied: the scheduler's
  test support and tests moved to `volley::scheduler::test`.

- **No `*Msg` / `*Srv` aliases from the `*_msgs.hpp` headers in new code** (dambrosio, PR #1007,
  user agreed): the aliases hide where a type comes from (`interfaces::msg::PlanRequest`) and the
  alias header drags in every interfaces header for two messages. Write the `interfaces::msg::X`
  type and `#include <interfaces/msg/x.hpp>` for what the file uses. Applied to the scheduler's
  test code (208 uses, 20 files); the library's own headers were left as they are.

## 4. Tests

- **Names of four or five words**; Claude-style long names are called out. Applied: nine names
  of seven to eleven words shortened.
- **Paths mirror the source** (`test/sm/` for `src/sm/`). No `main()` under the test helpers;
  `rclcpp::init`/`shutdown` wherever ROS time or `Rate` is used.
- **Deterministic**: no fixed sleeps or tick counts that only hold on a fast runner; bounded waits
  on a condition or a fake clock; durations, not counts.
- **Fail cleanly**: `ASSERT_*` before indexing a container or dereferencing an optional or
  iterator that an `EXPECT_*` only reported on, so a regression fails with the message instead of a
  crash (applied across the moved tests). `std::get_if` rather than `std::get` on a variant under
  test.
- **Bind a shared value once** (`const auto`) and use it in setup and assert; drive the production
  wiring rather than a hand-maintained copy of it (a hand-built input is fine when the test isolates
  one stage on purpose: say so); no dependence on repo assets a refactor may delete; a regression
  test for the fix unless coverage is indirect or the test would only exercise the framework.
- **Unused includes in tests** are flagged like anywhere else.

## 5. YAML, data and tools

- **YAML under a name Greptile knows** (`scenarios`, params, layouts) gets its knowledge-base
  checks, all P1: supported event types, capacity, drains, companion `*_events_*` files. Say in the
  README and the PR what a folder is when it is not that; the finding is then answered in a line.
- No commented-out blocks in YAML; short YAML comments; explicit file names; flat params.
- **Engineering-only tools** get leniency on robustness edge cases (read-only output dirs,
  running outside the install) but not on correctness. `argparse` or click help documents the
  inputs; defaults come from the package, not hard-coded in the script; f-strings; library
  features over hand-rolled parsing; no `sys.path.insert` in tests; focused modules (an 800-line
  module reads as a "god file" to the Python reviewer). Applied: the viewer split into seven
  modules along its layers.

## 6. Answering Greptile

Every dismissal the team made came with a reason or a ticket link. Reply in one line: intentional
design (and why), out of scope plus the ticket, dev-only tool, covered elsewhere, a repo convention
Greptile did not know. Real defects in error, reconnect and race paths, process findings and
comment hygiene are accepted and fixed; findings that are factually wrong about ROS or the build
are answered with the fact.

## 7. What PR #1007 taught (apply from stage 2 on)

The conventions below came out of the review of SW2-1126 (Greptile, Dan Ambrosio, Justin Abel; review
log items 1 to 157). They are the house style for every later stage. Where a rule above already says
it, this section only adds the specific form the team asked for.

### C++

- **Comments say only the why, briefly.** Two drafts in that PR came back as "too verbose". A doc
  comment on a switch states what runs by default and what the switch adds, in one clause. Do not
  narrate test data in comments (the scenario `description` carries the story); never cite another
  package's file as precedent in a comment. Config settings stay bare (`scripts_are_modules = true`),
  the why lives in these notes. Verbose explanation belongs in `volley_notes`.
- **Namespaces:** `volley::scheduler` for new library code, `volley::scheduler::test` for test code,
  nested `scenarios` / `initial_states` in the support so call sites read `scenarios::Plan()`. No
  `using volley::X` inside `volley`; no locals named like an enclosing namespace (`test`, `scheduler`).
- **Types and includes:** `interfaces::msg::X` written out with `#include <interfaces/msg/x.hpp>`, never
  the `*Msg` aliases of the `*_msgs.hpp` headers in new code (the library's existing headers are left
  as they are in a test PR). The package's own headers in quotes, other packages' in angle brackets;
  groups gtest / `<...>` / `"..."`, each sorted; no `../` includes. rosidl include names are snake_case.
- **Naming:** `Is...` for bool predicates (`IsAgvLiftRaised`); a flag named after the message field it
  mirrors (`reciprocal`), never after a builtin (`reversed`); `_or` for an `Expected`, `_it` for an
  iterator; `kCamel` file-scope constants, `k_lower_case` local and function-local static constants
  (`kQuiet` for a static is what tidy accepted); file-local helpers, constants and key tables
  (`constexpr std::string_view`) in an anonymous namespace, each key string once.
- **Library customisation points over hand-rolled generics:** `YAML::convert<T>` specialisations, as
  `std::formatter` would be; when the required name breaks `readability-identifier-naming`, wrap the
  block in `NOLINTBEGIN/END` with the reason.
- **Small things the reviewers asked for:** `const` on every local not reassigned, by reference when only
  read; `std::format` for every message; `EXPECT_TRUE(x)` rather than `EXPECT_EQ(x, true)`; build a
  string fully before opening an `ofstream` (opening truncates); a function-local `static const` over a
  gtest `Environment` global; `== nullptr` where the neighbouring reads compare that way; remove struct
  fields nothing reads, derive instead of storing, and flag the judgement calls.
- **One responsibility per header.** A support header that grew past one topic is split along
  responsibilities, same namespace; each test includes only what it uses.

### Tests and test support

- **Layout:** headers under `test/include/scheduler/test/` (the path mirrors the namespace), sources
  under `test/src/<folder>/`, data under `test/scenarios/`. One file, one suite, one binary; the suite
  named after the file; test names without the suite's words and at most five words; files of a few
  hundred lines.
- **Shared sources go in a static library** (`${PROJECT_NAME}_test_support`), never into every binary:
  clang-tidy once analysed the same sources 18 times. `ament_find_gtest()` before the library, link
  `GTest::gtest`, no `find_package(ament_cmake_gtest)` (`volley_package` finds test depends), no
  `GTEST_INCLUDE_DIRS`. Target names `${PROJECT_NAME}_...`; CMake variables plain.
- **Expensive fixtures shared per binary** (`SharedScheduler`: one scheduler per layout and parameter
  set); a test that mutates owns its own. Library logging quiet in tests unless `SCHEDULER_TEST_LOG` is
  set.
- **Determinism is an explicit test** (`TEST(<Suite>, Deterministic)` calling `ExpectDeterministic`),
  not a hidden second run; the two runs are named `planned` / `replanned`, not `first` / `second`.
- **Brittle comparisons are gated** behind an environment variable, off by default; the determinism
  test is never gated; CI runs the invariant properties only (Justin Abel, Dan Ambrosio).
- **Garage states are files** (`initial_states/<layout>/<name>.yaml`, named after what stands in the
  garage, not after the test); no YAML literals in test sources; no acronyms (`vecs`, `vexen`) in the
  files, the spelled-out names instead. Layouts: `275_sunrise_b` default, `38_gramercy` for EV chargers,
  `5675_pecos_combined` for bays and AGV chargers, `tiny_lot` only where a full lot is needed;
  `576_eccles*` and `1355_fulton` are decommissioned.
- **A parsing layer gets unit tests** (`utils/scenario_yaml_tests`). One helper instead of copies
  (`ExpectInsert`). Scenario files sit two folders below `scenarios/`, which keeps Greptile's
  knowledge-base checks for the exerciser's scenarios off them.
- **Test data is never installed to `share/`** unless another package consumes it; tests that record in
  place keep the source-tree define (`SCHEDULER_SCENARIO_DIR`).

### Python tooling

- A script with a shebang is executable and has no `.py`; run it by path or through a poe task, never
  with `uv run`. `scripts_are_modules = true` in `[tool.mypy]` (CI runs `--all-files`, and extensionless
  scripts collide as `__main__`). No `from __future__ import annotations` (Python 3.14); compare dataclass
  field types with `is str`. Dependency groups named `<package>-dev`, `include-group` lines together, no
  comment, `poe lock` in the container. poe tasks kebab-case, alphabetical, named for what they do; no
  task where a README one-liner suffices.

### The review loop

- **Assess every finding before applying it.** Greptile was right about half the time in that PR;
  reproduce in the container, then write what was wrong, what changed and how it was verified. Answer
  the rest with the fact or the reason, in a line.
- **One item at a time, amended on the user's word.** The PR keeps its commit count; each round is
  amended into the commit the user names; moving a change into an earlier commit is a fixup plus a
  non-interactive autosquash rebase, with approval. The user pushes (force-with-lease); never touch the
  working tree while the user pushes.
- **Before every amend:** clang-format or black on the touched files, rebuild with 0 warnings, the
  package tests both ways (plain, and with `SCHEDULER_CHECK_RECORDINGS=1`), `prek run --files` on the
  touched files, and the tidy hook after the amend (it diffs `main..HEAD`, so a run before an amend
  that moves files errors). Check the build's exit code explicitly; a pipe through `tail` once hid a
  failure.
- **A record run rewrites tracked files** and needs the user's approval each time.
- **Output changes (viewer, recordings) are verified by diffing before and after** across every
  scenario, not by looking at one.
- **Replies to reviewers are drafted, not posted.** A teammate question gets the evaluation and a
  draft; say when a decision was taken without asking. Commit bodies and PR text in an objective tone:
  no judgement on earlier authors, no colloquialisms ("decommissioned", not "defunct"), no Jira keys in
  commit messages, a `Refs:` line in the PR body. Add a coverage note to the PR body when octocov drops.

### Rejected in that PR; do not re-apply

- `ament_index_cpp` for the scenario paths (intentional: recording writes in place; the share tree has
  no reader).
- Comparing `scheduled_jobs` in the scheduler's order (an `unordered_map`'s iteration order carries
  nothing; the canonical form sorts by GUID).
- "Overfitting" of the recordings: they are characterisation tests for the refactor by design; the
  `EXPECT_*` lines stay the correctness checks; the comparison is opt-in.
- A poe task and a CI matrix entry for the recording check: dropped (the README command is enough; CI
  runs the invariants only; the files may move or go later).
- Deleting `utils_tests.cpp` (pushed back); a decode template instead of `YAML::convert` (answered,
  kept); `!getenv` over `== nullptr` (kept); `Run::scenario` as unused (kept deliberately).
- After removing postponed annotations, re-inspect rendered output: Greptile's palette finding was a
  regression that the tests did not catch.

## Pre-PR checklist

1. One coherent change per commit; conventional header; no correction-only commits.
2. Title `[SW2-xxxx] ...`; body `# What`, `# Why`, `# Testing`, `Refs:`; every behaviour change and
   changed constant listed; scope stated.
3. No restating, narrative or history comments; `///` docs consistent; no commented-out code,
   debug output or keyless TODOs; nearby docs, examples and help text updated.
4. `.value()`/`.has_value()` everywhere; `ASSERT` before indexing or dereferencing in tests;
   `[[nodiscard]]`; reuse of existing helpers; includes and package.xml trimmed.
5. Test names of five words or fewer; deterministic; no `main()`; ROS clock, not system time.
6. YAML and tools: say what the data is; no dead blocks; defaults as arguments; focused modules.
7. Replies planned for the findings that will come anyway.
8. Section 7 applied: comments brief and why-only; explicit message types and includes;
   `volley::scheduler[::test]`; test files one suite per binary under `test/src/`; parity run with
   `SCHEDULER_CHECK_RECORDINGS=1` and no change under `test/scenarios/`; `tidy` clean.
