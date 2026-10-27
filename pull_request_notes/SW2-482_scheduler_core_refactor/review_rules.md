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
