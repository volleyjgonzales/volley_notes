# SW2-484 design review (Phase R), 2026-10-22

Reviewed against: the objectives in `PROMPT.md` section 1, the code on `main` at `703bfe7c`, and the study
pack (`07-issue-and-proposal.md`, `08-verification.md`, `03-task-planning.md`). The survey findings are in
`SW2-482_notes.md`. The rewritten plan is `PROMPT.md`. Nothing in `~/volley` was changed.

## Summary of the main changes to the plan

1. **The solver's input no longer contains the event DAG.** `Input` is the initial garage state plus an
   ordered list of *steps*: a `MoveRequest` (job index, optional tray id, optional destination) for each
   `TrayMove`, and a `StateChange` for each bay or VECS transition in between. `Result` is plain data:
   fills, new moves, edges between step ids, and the first move of each tray. A two-function adapter
   (`StepsFromDag`, `ApplyResult`) is the only tray-assignment code that touches `ScheduleEventDag`.
   The `TrayFill` / `DagEdit` / `Overloaded` edit-replay machinery and the "resolved copy" trick disappear.
2. **Parity by instrumenting the existing tests, not a separate fixture suite.** Each of the ~45 planning
   tests records or compares a canonical YAML of its result (`test/reference/<Suite>.<Name>.yaml`). No
   fixture loader, no YAML job schema, no parallel copies of the test states. The 4 direct tray-stage and
   9 AGV-stage tests become stage references for free.
3. **Everything that does not serve the tray solver is deferred.** All stage-B2 renames and boundary types
   (`vocabulary.hpp`, `types.hpp`, `ros/convert`, `PlanContext`, `Expand*Job`, `ScheduledJob`, `Timepoint`,
   `ReserveBaseScheduleAssets`), the stage folders and CMake targets for stages that this PR does not
   touch, the action-graph and motion-planning moves, the include-check and vocabulary scripts, the
   side-by-side test, and the private `pass.hpp` / `critical_path.hpp`. One static library target and one
   test binary for the tray module remain, because they are what proves "testable without a `Scheduler`".
4. **Services are passed per call** (`Solve(const GarageServices&, const Input&)`), so `DefaultSolver` is
   stateless, default-constructible and injectable through a `Scheduler` constructor parameter with no
   lifetime rule.
5. **Six commits instead of thirteen**, each extracting straight into the module's files (no "in place
   first, move later" double churn), with the parity references as the safety net.

## Each change, and why

### 1. Plain-data solver input and output (objective 1)

What `DoTrayAssignments` reads from the DAG, on the branch: the topological order once
(`GetTopologicalOrdering`, `GetEventFromVertex`), and for each event its type and, for tray moves, tray id,
destination and job index. It applies **bay and VECS transitions only** to its working state and registers
their inbound pose as occupied (`ApplyTransitionToFreeingMoves`; AGV and VRC events are skipped). It
writes: `SetTrayId` / `SetDest` on existing moves, `AddEvent` for new moves, `AddDependency` (chain edges,
per-tray edges, occupancy edges from earlier occupants of a pose, blocker → root), and `first_tray_event`.

So the input a solver needs is: the initial state, the tray moves in plan order with their blanks, and the
bay/VECS state changes interleaved in that order (a tray decision depends on the bay state *at that point
in the plan*: a closed bay blocks). The state changes cannot be pre-applied by the adapter because they
interleave with the solver's own moves, and reimplementing `BayTransition::Apply` / `VecsTransition::Apply`
as plain data would duplicate `planner_core`. The design therefore keeps the event object for those steps
only, as `std::shared_ptr<const ScheduleEvent>`: `Apply` is `const`, so the solver cannot change it, and a
test builds one the way today's tests do (`std::make_shared<BayTransition>(job, bay_state, cmd)`). A test
whose scenario has only tray moves needs no event at all. **This is the one place where the input is not
"plain" in the strictest sense; it is a question for the user (Q1).**

Output by id instead of by pointer: step ids are positions in `Input::steps`; a new move's id is
`steps.size() + its index in Result::new_moves`. `ApplyResult` creates the new `TrayMove`s in order (same
vertex numbering as today), then adds the edges in recorded order (same per-vertex out-edge order, so the
same `GetTopologicalOrdering` tie-breaking), then sets the fills, copies `first_tray_event`, and runs
today's final topological check. Occupancy inside the solver is `GarageOccupancyChecker<size_t>`, which the
template already allows.

Consequences for the rest of the design: invariants 8–10 simplify (section 7 of the plan); `Pass` shrinks to
a file-local struct holding the working state, the occupancy checker, the per-tray chain and the `Result`;
`ResolveBlockingTrays` returns `PlannedTrayMove{tray_id, destination, path}` without creating events, which
suits `PlanChargePayloadJob`, which on the branch discards the moves and uses only the destination.

### 2. Parity by instrumentation (objectives 2 and 5)

The original plan: a `test/parity/` suite with a YAML input format (layout, state, jobs, base schedule,
plan time, fixture kind), a loader, a canonicaliser with a reduced edge set, reachability relation, final
state hash, and 30+ fixture folders. On the branch there is no YAML job or event loader to reuse, and every
state would be a copy of one that already sits inline in a test.

The replacement: `test/parity.{hpp,cpp}` with `Canonical(const ScheduleContext&)`,
`Canonical(const PlanResponseMsg&)` and `ExpectReference(...)`. A planning test adds one line after its
`Plan()` or stage call. The reference file is named after the gtest suite and test name; `RECORD_REFERENCE_OUTPUT=1`
(only through `volley-in-container record-reference`) writes it, otherwise the test compares and prints
the first differing lines. The end-to-end overload runs the plan twice in one process and compares the two
(determinism). Canonical content: event identities from `planner_core`'s `ToString()` (unchanged in this
PR) plus an occurrence number, sorted; the **raw** edge set as index pairs (stricter than the reduced set,
and no `Reduce()` on a copy); `first_tray_event`; for responses, the message itself through rosidl
`to_yaml` after replacing the counter-generated action GUIDs and the ids derived from them by positions,
and sorting `scheduled_jobs` by job GUID. Dropped as diagnostics only: the reachability relation and the
final-state hash (the events and fills determine the final state).

Coverage: the 40-odd `Plan()` tests cover every job type except READY_FOR_INSERT and REBALANCE_GARAGE, and
no test uses a base schedule. Commit 1 adds ordinary tests (with references) for READY_FOR_INSERT, a base
schedule with one AGV command, and, if they can be built on the test layouts in reasonable size, fallback 1
and fallback 2 of the blocker loop. The waypoint stash is already covered
(`CleanGarageUnstashesTrayFromWaypoint`).

Cost: roughly 250 lines of canonicaliser and helper, 10 lines of CMake, ~60 one-line insertions, a few new
tests, and the reference files (data). Versus the original: no fixture loader (~200 lines), no fixture
inputs (~1500 lines of duplicated YAML), no separate target.

### 3. Footprint cuts (objective 2)

| Item | Decision | Reason |
|---|---|---|
| `core/vocabulary.hpp` aliases, `check_vocabulary.sh` | drop | No line of the solver needs an alias; aliases make compiler errors and debuggers print other names; a report script is tooling nothing checks. The naming catalogue can be applied in a later PR. |
| `core/types.hpp` (`AssetId`), `ros/convert`, `ScheduledJob`, `Timepoint` constructor, `last_event_by_asset` | drop | ROS-boundary work for the orchestrator, unrelated to tray assignment. |
| `ScheduleContext` → `PlanContext`, field and helper renames, `Plan<Type>Job` → `Expand<Type>Job`, member renames (`gg_`, `table_`, …) | drop | Mechanical churn across 4200 lines with no effect on the solver's testability. The solver reads the context through the adapter only. |
| `ReserveBaseScheduleAssets` | drop | Orchestrator; no base-schedule test exists today (commit 1 adds a reference for one). |
| Stage folders `core/`, `task_planning/`, `motion_planning/`, `action_graph/`, `.gitkeep`/README files, per-stage targets | drop; keep one folder and one target for the tray module | A folder that holds one file or nothing, and a target with no sources, are structure for later stages. Adding them later is a `git mv` plus a CMake line. |
| `scripts/check_includes.sh` | drop | The module's test binary links only the module library; a module file that uses `Scheduler` fails to link. Header-only reach is a review item (one rule: nothing under `tray_assignment/` includes `scheduler/scheduler.hpp`). |
| Action-DAG builders → `action_graph/`, `PlanMotions` → `motion_planning/` | drop | Stages 4 and 5 are not part of SW2-484. |
| Side-by-side test (D-1) | drop | The parity references on every tray-stage and end-to-end test prove the switch. |
| `TrayFill` / `DagEdit` / `Overloaded`, resolved-copy technique | drop | Gone with the plain-data result (change 1). |
| `Pass` as a nested class with its own private header and `.cpp` | drop | A file-local struct in `default_solver.cpp`. |
| Private `critical_path.hpp` in `src/` | keep the functions, make the header public under `include/scheduler/tray_assignment/` | So the module test can include them without `../../src` paths. |
| `TryAdvanceRoot` as a function | drop | The fallback-1 block is `BlockersOnPath` on one vertex plus `EvChargeHeading`; a six-line inline block. |
| `WithPriorDests` as a free function | drop | Stays the six-line lambda it is. |
| Direct tray tests ported to the module (E-1) | drop | The four tests keep calling the `Scheduler` through `AssignTrays`; the new module tests cover the solver without a `Scheduler`. Porting them would duplicate coverage. |
| `scheduler_tray_assignment` static library + `tray_assignment_tests` | **keep** | The only build-level proof of "no `Scheduler` needed". About 15 lines of CMake. |
| `GarageServices` | **keep** | Every pure function needs the graph, collision table, cost model, layout and logger; a struct of references is the smallest way to pass them. |

### 4. Parity decisions (section 8 of the plan)

All items are **keep**, with one deliberate difference that may surface:

| Quirk | Decision | Reason |
|---|---|---|
| `GetAgvOccupiedDuration` returns zero | keep | AGV stage, untouched. |
| `Reduce()` twice (AGV stage and `Plan()`) | keep | Untouched. |
| No `Reduce()` at the end of tray assignment | keep | The hypothesis in the study pack (direct-edge-only cost propagation) is untested; not this PR. |
| `TrayMove::Apply` blank-field behaviour | keep | `planner_core`; the solver applies moves through temporary `TrayMove`s with both fields set, exactly as today's copies. |
| Fallback-1 path (`std::vector<GaragePoseMsg>{vertex, dest}`) and the double apply | keep | See B1/B2 in the notes: the expression most likely builds *n* copies of the destination; keeping the expression keeps the edges. Confirm with a test in commit 4; fix in a follow-up with its own reference diff. |
| `AddDependency` silent `false` | keep | `ApplyResult` adds all new moves before any edge, so a missing endpoint cannot happen; a duplicate edge is a no-op as today. No new checks (they would never fire). |
| `vecS` vertex indices | keep | Never remove from the plan's DAG. |
| `DoAgvAssignments` throws on a failed sort | keep | Stage F. |
| Floyd–Warshall per `Plan()` | keep | Untouched. |
| **Order of occupancy edges when a pose has several occupants** | **fix (deterministic by id) if it shows up** | Today the order comes from an `unordered_set` of `shared_ptr`s (pointer hash), so it can differ between processes; it influences out-edge order and thus tie-breaking among events of one job. The new solver's order is a function of insertion order. If the record/compare split or the switch in commit 6 shows a difference traceable to this, record it as a deliberate difference with the reference diff; it is the only candidate. |
| `AssignDestForUntargetedMove` registers no occupancy for the original move | keep | Behind `CommitOptions`; a candidate for a later fix. |

Where exact parity would cost a lot of code: nowhere, with the plain result. Reproducing out-edge order
needs no edit log, only "new moves first, then edges in recorded order". Topological tie-breaking is
preserved for free as long as the recorded order equals today's call order, which the emission functions
of commit 5 keep.

### 5. C++ (objective 3)

- `std::variant<MoveRequest, StateChange>` for steps; `std::visit` with two lambdas in `Solve` (no
  `Overloaded` helper: `if(const auto* move = std::get_if<MoveRequest>(&step))` reads better for two cases).
- `std::span<const PlannedTrayMove>` for `EmitMoveChain`; `std::span<const Vertex>` for `BlockersOnPath`.
- Designated initialisers for `ResolveRequest` (already used in the code for `BlockingTrayResolution`;
  `.clang-tidy` allows them).
- `std::ranges::any_of` for the "does any other tray collide with this pose" loops; `std::ranges::find`.
- `= default` `operator==` on the result structs, so tests can compare whole `Result`s.
- `stdx::Expected` / `stdx::Result` everywhere a reason travels; `std::optional` for found-nothing
  searches inside `blocking_trays.cpp`. Error text stays `std::string` with `std::to_string(pose)`.
- `[[nodiscard]]` on every function returning `Expected` / `Result`.
- Heading helpers return values (`std::optional<GaragePoseMsg>` / `GaragePoseMsg`) instead of mutating a
  reference parameter.
- Namespace note from the study pack kept: no `volley::common`, no `volley::motion_planner`.

### 6. Risks the original plan missed, and contradictions found

- **Non-tray events are needed by the solver** (change 1). The prompt's suggested input ("initial state
  plus the list of tray moves") would drop bay/VECS transitions and change decisions.
- **Blocker iteration order is pointer-hash order** (B4). Today's output may not be reproducible across
  processes; this is also the one place where the plain-data solver can legitimately differ.
- **Action GUIDs are a static counter per test binary**, so reference content must be position-based, and
  reference files change whenever tests are reordered unless GUIDs are canonicalised (they are).
- **`GetTopologicalOrdering` tie-breaking is heap order among equal job indices**, not "job index, then
  vertex id" as the prompt's wording suggested. Out-edge order matters; the adapter preserves it.
- **`ResolveBlockingTrays` is also used by `PlanChargePayloadJob` for its destination only.** The plain
  return makes that caller simpler, not harder.
- **`scheduler_advanced_tests/test07`** says AGV assignment tie-breaking varies between builds. It is
  outside this PR's scope (no reference files there), but it caps how far "parity" can be pushed on real
  layouts later.
- **No test covers READY_FOR_INSERT, REBALANCE_GARAGE or a base schedule**; commit 1 adds references for
  the first and third. REBALANCE_GARAGE depends on bay readiness and is left out unless cheap.
- The study pack's `Scheduler::WithPriorDests` is a lambda, `InsertVrcActionsIntoDag` is a free function,
  and `stdx` lives in `volley::stdx`; the plan now says so.
- `PlanReadyForInsertJob`'s best-effort fill pass calls `AssignTrayIdForEmptyMove` and then
  `UpdateLastEntityEvent`; with `ChooseEmptyTray` returning a value, the caller sets both fields and keeps
  the rest. Watch the deferral `WARNS` path: a failed choice must still leave the move blank.

## The new commit plan

| # | Header (after `<type>(scheduler): `) | Type | Steps | Objective | Est. size |
|---|---|---|---|---|---|
| 1 | `add parity references to the planning tests (SW2-484 A)` | test | A1, A2 | Record today's behaviour before any change | +400 code; ~45 reference YAML files |
| 2 | `add garage services and the tray heading and empty-tray helpers (SW2-484 C1)` | refactor | C1-1 to C1-3 | Services struct, module target and test, first pure helpers | +330 / −120 |
| 3 | `make blocking-tray resolution a free function with plain results (SW2-484 C1)` | refactor | C1-4 | `ResolveBlockingTrays` and its two searches out of `Scheduler` | +320 / −300 |
| 4 | `extract the main-loop decisions of tray assignment (SW2-484 C1)` | refactor | C1-5 | `CheckDestinationUsable`, `FindCriticalPath`, `BlockersOnPath`, `ChooseParkingSpot` | +260 / −200 |
| 5 | `merge the two tray move-emission blocks (SW2-484 C1)` | refactor | C1-6 | One emission function, one root-commit function, options for the differences | +120 / −160 |
| 6 | `put tray assignment behind a solver interface (SW2-484 C2)` | refactor | C2-1 to C2-4 | `Solver`, `DefaultSolver`, adapter, `Scheduler::AssignTrays`, injection; legacy members deleted | +500 / −450 |

Total: about +1930 / −1230 lines of code (net +700, of which roughly 550 are tests and the parity helper),
plus reference data. Commit 6 may be split at the boundary "module added, `Plan()` not yet switched" /
"switch and delete" if the diff is too large to review; that keeps the count at 7.

## Open questions for the user

1. **`StateChange` steps carry the bay/VECS event** (`shared_ptr<const ScheduleEvent>`) so the solver can
   apply them in order. Accept this as "plain enough", or require a message-level representation (which
   means reimplementing two `Apply`s in the scheduler)?
2. **Parity by instrumenting the existing tests** (one line per test, references named after the test)
   instead of a separate fixture suite with YAML inputs. Accept?
3. **Defer every B2 rename and boundary type**, the stage folders for other stages, the two script checks,
   and the action-graph / motion-planning moves to later PRs. Accept? (If you want some renames in this
   PR, say which; each is one mechanical commit under the 10-commit cap.)
4. **Module location:** `include/scheduler/tray_assignment/` (flat) now, `task_planning/` grouping when a
   second task-planning module exists. Or create `task_planning/tray_assignment/` right away?
5. **Services per call** (`Solve(services, input)`) rather than at construction. Accept?
6. **The deliberate difference** on occupancy-edge order (section 4): accept it as the one allowed
   difference if it surfaces, with the reference diff in the commit?
7. **B1 (fallback-1 path expression):** keep for parity and open a follow-up ticket, as proposed?
8. **`scheduler_advanced_tests`** is not in the list of packages this PR must not touch. Add
   `ExpectReference` lines there too (real-site layouts), or leave that package alone?

## Answers from the user (2026-10-22)

| Q | Answer | Effect on the plan |
|---|---|---|
| 1 | Bay/VECS transitions travel as `shared_ptr<const ScheduleEvent>` steps | As proposed. |
| 2 | Parity by instrumenting the existing tests | As proposed. |
| 3 | **Keep four rename groups**: `Scheduler` members; `Plan*Job` → `Expand*Job`; `ScheduleContext` → `PlanContext` with its fields and methods; `stdx` for the `BoolStringPair` members this PR touches. Defer `AssetId`, `ros/convert`, `ScheduledJob`, `Timepoint`, `ReserveBaseScheduleAssets`, vocabulary aliases. | Two mechanical commits come back (commits 2 and 3 of the final plan). The `stdx` conversion of the tray tree already happens as each function leaves `Scheduler`, so it costs no commit; expansion and the AGV tree keep `BoolStringPair`. |
| 4 | `task_planning/tray_assignment/` now | Folder and namespace `volley::task_planning::tray_assignment`; `scheduler.cpp` declares the short alias. |
| 5 | Services per `Solve` call | As proposed. |
| 6 | Accept the occupancy-edge-order difference if it surfaces | As proposed. |
| 7 | (not asked separately) | Default applied: B1 kept for parity, documented with a test, follow-up ticket. |
| 8 | Leave `scheduler_advanced_tests` alone | Added to the do-not-modify list. |

**Final commit plan (supersedes the table above):**

| # | Header (after `<type>(scheduler): `) | Type | Steps | Est. size |
|---|---|---|---|---|
| 1 | `add parity references to the planning tests (SW2-484 A)` | test | A1, A2 | +400 code, ~45 reference files |
| 2 | `rename scheduler members and expansion methods (SW2-484 B2)` | refactor | B2-1, B2-2 | +400 / −400 |
| 3 | `rename ScheduleContext to PlanContext and its fields (SW2-484 B2)` | refactor | B2-3 | +300 / −280 |
| 4 | `add garage services and the tray heading and empty-tray helpers (SW2-484 C1)` | refactor | C1-1 to C1-3 | +330 / −120 |
| 5 | `make blocking-tray resolution a free function with plain results (SW2-484 C1)` | refactor | C1-4 | +320 / −300 |
| 6 | `extract the main-loop decisions of tray assignment (SW2-484 C1)` | refactor | C1-5 | +260 / −200 |
| 7 | `merge the two tray move-emission blocks (SW2-484 C1)` | refactor | C1-6 | +120 / −160 |
| 8 | `put tray assignment behind a solver interface (SW2-484 C2)` | refactor | C2-1 to C2-4 | +500 / −450 |

Eight commits, about +2630 / −1910 lines of code plus reference data. Commits 3 and 8 have named split
points, which keeps the worst case at ten.
