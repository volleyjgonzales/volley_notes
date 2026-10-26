# SW2-482 notes (running log; not committed)

## Status

- **Layout of this folder:** see `README.md`; the sub-ticket's code notes, ticket and PR texts are under
  `SW2-1126_scenario_files/`.
- **Phase R (design review) done on 2026-10-22.** Report: `DESIGN-REVIEW.md` in this folder, with the user's
  answers to its eight questions at the end. The plan is `PROMPT.md` (rewritten by Phase R, eight commits).
- **Plan approved by the user on 2026-10-22** (after the eight review questions were answered; see the end of
  `DESIGN-REVIEW.md`).
- **Branch** `jmg/SW2-1126/scheduler-scenario-files` since 2026-10-26 (Jira SW2-1126, created by the user as a Task under epic SW2-482); before that `jmg/SW2-484/scheduler-core-refactor`, created on 2026-10-23 as `jg/SW2-484/scheduler-core-refactor`
  branch point; two merges after the study pack's `703bfe7c`: `#996` motion_planner perf, `#998` launcher
  fix. `scheduler`, `planner_core` and `common_ros` are unchanged between the two, so the study pack's line
  numbers still hold.)
- **In progress: commit 1** (steps A1, A2). Work done, unstaged, review packet posted on 2026-10-22;
  waiting for the user's feedback. See "Commit 1" below.
- **Next:** address feedback, commit on approval, then commit 2 (B2-1, B2-2 renames) when the user says so.

## Commit 1: parity references (A1, A2)

Files (all under `src/planner/scheduler/`): `test/parity.hpp` (44 lines), `test/parity.cpp` (176),
`CMakeLists.txt` (+12), `test/scheduler_tests.cpp` (+18), `test/scheduler_insert_orientation_tests.cpp` (+6),
`test/scheduler_jobs_tests.cpp` (+265: 34 reference calls, 4 new tests, one helper), 58 files under
`test/reference/` (23,039 lines). Code size +521 versus the +400 estimate; references 58 versus ~45.
After the review rounds (see the review log): references 58 files / 28,805 lines in three stage folders
with `test/reference/README.md`; `tools/view_references.py` + `tools/reference_viewer/` (1,260 lines);
`pyproject.toml` / `uv.lock` add `plotly==7.1.0` to the dev group (the one change outside the package,
asked for by the user).

Decisions and deviations:

1. `agv_command.id` is **never set** by the scheduler (empty in every reference), contrary to the plan's
   description. `ToActionNode` copies the node GUID into `vecs_command.command_id` and
   `vrc_command.command_id`; `Canonical(response)` rewrites those two and `agv_command.id` (harmless, and
   right if it ever gets set). `bay_arrival_node_guid` is rewritten through the same old-to-positional map.
2. `Emit` normalises through a load/emit round trip: yaml-cpp emits a freshly built empty collection as
   `key:` + `  []` on the next line but a loaded one as `key: []`, so the first fresh-process compare run
   failed 7 references (empty edge sets and empty `first_tray_event`). Files are written in the loaded form.
3. Format: sequences of scalars in the response (GUID `bytes`, `parents`, `node_indices`) and the
   `[from, to]` edge pairs are flow style (one line each); everything else is block style. Event strings
   get a ` #n` suffix (n = earlier identical strings in vertex order) and are sorted; their position is the
   canonical index. Floats come out of rosidl's `to_yaml` (`std::showpoint`, 6 digits).
4. The `ExpectReference(F&& produce, ...)` overload is constrained with `std::invocable`: unconstrained, it
   captured `YAML::Node` prvalues. It plans twice (plus the test's own plan): record runs took 4.5 s
   (`scheduler_tests`), 7.6 s (`scheduler_jobs_tests`), 0.7 s (`scheduler_insert_orientation_tests`).
5. Suffixes: `ReadyForRetrieveJob` empty_bay / tray_in_bay; `TransitionBay` unknown_bay / wrong_command /
   to_retrieve / to_insert (round 2: the stage folder replaced the tray / agv suffixes). The
   `ResolveBlockingTraysRecursivelyUnblocksChain` test and the commented-out `DoubleRetrieveDodgeAgv` are
   not instrumented. `test/reference/` is recorded with the three binaries in the order scheduler_tests,
   scheduler_jobs_tests, scheduler_insert_orientation_tests (the order does not matter: GUIDs are canonical).
6. All four requested scenarios were built (none skipped), as `SchedulerJobs` tests:
   - `ReadyForInsertJob`: tiny_lot, bay 1 READY_TO_RETRIEVE and empty, AGV at 8, empty trays at 6 and 9.
     The fill pass in `PlanReadyForInsertJob` resolves the blank tray id; 8 nodes, bay transition last.
   - `BaseScheduleReservesAgvAndNodes`: triple_pick_lot, AGVs 1 (node 5) and 2 (node 9), tray 2 at 8;
     base schedule holds one AGV command for AGV 2 from 9 to 12; MOVE_TRAY tray 2 to 11. AGV 1 does the
     job (asserted); 4 nodes.
   - `RetrieveAdvancesRootTray` (fallback 1): tiny_lot full: root tray 1 (payload) at 9, blocker 4 on
     waypoint 3, trays 5, 8, 11 on nodes 5, 8, 11, AGV at 2, retrieve to bay 1. Log: "Advancing t1 to 6@0",
     then the blocker is resolved through recursion (t4 -> 9 after t5 -> 9... chain). 35 nodes, executing.
   - `RetrieveParksBlockerOnCriticalPath` (fallback 2): same with blocker 4 on parking 6 (the next step).
     Log: "Found open space for blocking tray t4 at 3@0 allowing parking on critical path", then the
     re-scan finds t4 again and fallback 1 advances t1 to 6. 39 nodes, executing. Both share the helper
     `RetrieveFromFullTinyLot(scheduler, blocker_node)` (state string with a `{blocker_node}` placeholder).
7. Determinism: every lambda reference compared equal between its two in-process runs and in the fresh
   compare process (`volley-in-container test scheduler`: 80 tests, 0 failures). B4 (pointer-hash edge
   order) did **not** surface in this suite.
8. Test counts after commit 1: scheduler 80 (76 + 4 new), planner_core 23, scheduler_advanced_tests 16;
   all pass. Hooks (`prek run --files` on every touched file): all pass; clang-tidy is a push-stage hook
   and was not run (first due at commit 3).

Reference files (`<stage>/<Suite>.<Name>[.<suffix>].yaml`; "ctx" = a stage reference under
`task_planning/tray_assignment` or `task_planning/agv_assignment` (the `.tray` / `.agv` names below are
the folders now); "plan" = `action_graph/` with the node count):

| File | Kind | Covers |
|---|---|---|
| Scheduler.TrayAssignmentTest | ctx | tray stage: blank destination filled (2 events) |
| Scheduler.TrayAssignmentTestComplexDag.tray / .agv | ctx | tray stage (3 events) then AGV stage (12 events) on one DAG |
| Scheduler.UnblockingTrayMoveTest | ctx | tray stage: one blocker move added |
| Scheduler.TrayAndAgvAssignments.tray / .agv | ctx | tray (2) then AGV (8) stages |
| Scheduler.MiAmigaEsSuAmiga, AmigaSaysNo, AmigaStash, NoAmigas, AmigaBaySos, AmigaBaySo | ctx | AGV stage only (AmigaSaysNo is the failure path: 1 event, no edges) |
| Scheduler.TrayLiftBayTransitionDependencyTest | ctx | AGV stage with a bay transition (8 events, 10 edges) |
| Scheduler.CleanGarageAgvInTheWay / DontMoveAgvsUnderTrays / UnstashesTrayFromWaypoint | plan | CLEAN_GARAGE (2 / 0 / 5 nodes; the last is the waypoint unstash) |
| Scheduler.FultonInsertBay{1,2}TrayHeading{0,180} | plan | INSERT on 1355_fulton (12 to 14 nodes) |
| SchedulerJobs.MoveAgvJob / MoveAgvJobAlreadyAtDest | plan | MOVE_AGV (5 / 0 nodes) |
| SchedulerJobs.ReparkTrayJob, ...GoodVecs, ...GoodVecsAtDest, ...ChargingVecs, ...AdvanceToWaypoint, ReparkUnplugVecs, ReparkUnplugVecsMoveAgvFirst | plan | REPARK_TRAY (9 / 9 / 9 / 10 / 101 / 5 / 5 nodes) |
| SchedulerJobs.ReparkTrayJobBadVecs / BadVecsDest | plan | REPARK_TRAY failure paths (STATE_ERROR, no nodes) |
| SchedulerJobs.RetrieveJob, ...GoodVecs, ...ChargingVecs, ...BayTransition, BackToBackRetrieve, WeirdFultonRetrieve | plan | RETRIEVE (10 / 10 / 11 / 11 / 29 (2 jobs) / 18 (with CLEAN_GARAGE)) |
| SchedulerJobs.RetrieveJobDisabledNode / RetrieveJobBadVecs | plan | RETRIEVE failure paths |
| SchedulerJobs.RetrieveAdvancesRootTray / RetrieveParksBlockerOnCriticalPath | plan | **new**: tray-assignment fallbacks 1 and 2 (35 / 39 nodes) |
| SchedulerJobs.ChargePayloadJob | plan | CHARGE_PAYLOAD (9 nodes); ...NoVecs, ...WrongPayload: failure paths |
| SchedulerJobs.InsertJob | plan | INSERT + CLEAN_GARAGE (16 nodes, 2 jobs) |
| SchedulerJobs.ReadyForRetrieveJob.empty_bay / .tray_in_bay | plan | READY_FOR_RETRIEVE (1 / 7 nodes) |
| SchedulerJobs.ReadyForInsertJob | plan | **new**: READY_FOR_INSERT, blank tray id (8 nodes) |
| SchedulerJobs.BaseScheduleReservesAgvAndNodes | plan | **new**: non-empty base_schedule (4 nodes) |
| SchedulerJobs.AgvChargeJob, ...MVP454, ...InBay, DontGoToDisabledChargeNode | plan | CHARGE_AGV (2 / 6 / 6 / 14 nodes) |
| SchedulerJobs.TransitionBay.unknown_bay / .wrong_command / .to_retrieve / .to_insert, CantTransitionDisabledBay | plan | TRANSITION_BAY_* (two failures, two successes with 1 node, one failure) |

Still never covered end to end: REBALANCE_GARAGE, `planned_jobs`, `active_jobs`.

## Baseline (Phase 0, step 2)

- Branch `main` at `703bfe7caa28af5be4175528d4cd98a2db5b8e59` (2026-10-22 10:57 -0600, "Merge pull request #995
  from VolleyAutomation/pvc/SW2-1111/fix-sim-event-handling"). Working tree clean.
- `volley-in-container build scheduler scheduler_advanced_tests`: OK, 14 packages, 0 compiler warnings
  (cached build, 6 s).
- `volley-in-container test scheduler`: 76 tests as `colcon test-result` counts them, 0 failures, 0 skipped,
  25 s. The four gtest binaries hold **72 `TEST` cases**: `scheduler_tests` 25, `scheduler_jobs_tests` 30,
  `scheduler_insert_orientation_tests` 4, `utils_tests` 13. None is `DISABLED_`; one is commented out
  (`Scheduler.DoubleRetrieveDodgeAgv`, `scheduler_tests.cpp:1940-2002`, "TODO(Joe) revisit"). No `TEST_F`
  or `TEST_P`; there are no fixture classes or shared test helpers.
- `volley-in-container test planner_core scheduler_advanced_tests`: planner_core 23 tests,
  scheduler_advanced_tests 16 (9 `TEST` cases in 7 binaries, 2 more commented out), 0 failures, 111 s.
- Logs: `~/.cache/volley-in-container/logs/20261022-1115*-build-*.log`, `20261022-111559-test-scheduler.log`,
  `20261022-111627-test-planner_core_scheduler_advanced_tests.log`.
- No test reads the clock: every test uses `rclcpp::Time(0)` or `rclcpp::Time()`. Only `scheduler_ros.cpp`
  calls `now()`.

## Branch versus study pack (Phase 0, step 3)

- **The scheduler package is byte-identical to the snapshot** `sources/repomix-scheduler.xml` (all 15 files)
  except `package.xml`, where `launcher` became `site_config` (exec and test depend). So the study pack's
  line numbers for `scheduler.cpp` are valid on this branch at `703bfe7c`. Still find code by symbol.
- SW2-769 ("move scheduler dir to planner and reorg pkgs", `6664181d`) happened before the snapshot. The
  package is at `src/planner/scheduler`; siblings: `cost_functions`, `motion_planner`, `planner_core`,
  `scheduler_advanced_tests`, `task_planner`. Layouts moved to `src/config/site_config/layouts/`
  (`a719d4ab`); tests find them with `GetLayoutPathByName(name)` (common_ros → site_config → ament index).
  `common_ros/test/test_layout.yaml` is a second layout source used by `utils_tests` and four jobs tests.
- Files (lines): `scheduler.hpp` 456, `scheduler.cpp` 4200, `utils.hpp` 97, `utils.cpp` 520,
  `scheduler_ros.cpp` 125, `scheduler_component.cpp` 71, tests 2004 + 2817 + 951 + 774.
- Tray call tree on the branch (all `Scheduler` members, `const`; line = definition in `scheduler.cpp`):
  `DoTrayAssignments` 2533–3092 (560 lines), `AssignTrayIdForEmptyMove` 2159, `AssignDestForUntargetedMove`
  2222–2338, `ResolveBlockingTrays` 1982–2119 (public), `FindOpenSpaceForRootTray` 1850,
  `TryFindBlockingTrayResolution` 1895, `ApplyTransitionToFreeingMoves` 2124, `UsePreferredHeading` 1771,
  `UseEvChargeHeading` 1781, `UseRetrievalHeading` 1805. `WithPriorDests` is a **lambda** inside
  `DoTrayAssignments` (2687), not a member. Private structs `OpenSpaceSearchResult` and
  `BlockingTrayResolution` are in `scheduler.hpp:388-402`.
- AGV tree: `DoAgvAssignments` 3475–3839, `GetJustMovingCost` 3094. `PlanMotions` 4005–4067,
  `ResponseFromTrajectories` 4069–4129. Anonymous namespace of `scheduler.cpp` (26–340): `ToActionNode`,
  `MotionScheduleOrder`, `CollectAndCollapseTrajectoryMotions`, `BuildActionDagFromMotions`,
  `TransferEventDagDepsToActionDag`, `BuildScheduledActionsArray`. `InsertVrcActionsIntoDag` is a free
  function in `utils.cpp:366`. `GetTopologicalOrdering` and `Reduce` are DAG methods (planner_core).
- Symbol use outside `scheduler` (rg over the workspace): `task_planner` (`BottleneckAssignment`, its own
  header and test), `scheduler_advanced_tests/test07.cpp` (2 mentions in comments),
  `system_tests/.../system_clean_garage_unstashes_waypoint.py` (1). Nothing outside `scheduler` calls the
  tray tree.
- `scheduler_advanced_tests`: 7 binaries, each one source, `LINK_LIBRARIES yaml-cpp` only (the scheduler
  library comes in through `ament_auto_depend_on_packages`). It uses only `Scheduler(layout, logger,
  params)`, `SchedulerParams::bay_readiness_ratio`, `Plan()`, `GetLayoutPathByName`,
  `DiscreteGarageState::Set/GetDiscreteGarageStateMessage`, `MakeGuid`, message fields. No member names,
  no `ScheduleContext`, no stage calls. Layouts: 576_eccles, 576_eccles_half, 576_eccles_mini,
  576_eccles_under_vcr, 1355_fulton, 550_w21st, 175_e82nd. Comment in `test07.cpp:23-26`: AGV assignment
  tie-breaking "depends on hash-map iteration order and so varies between builds".
- Callers of the shared helpers: `ResolveBlockingTrays` ← `PlanChargePayloadJob` (1732, **uses only the
  destination and discards the required moves**), `AssignDestForUntargetedMove`, `DoTrayAssignments` (3
  calls), itself via `TryFindBlockingTrayResolution` (recursion), test
  `ResolveBlockingTraysRecursivelyUnblocksChain`. `AssignTrayIdForEmptyMove` ← `PlanReadyForInsertJob`
  (1271, best-effort fill pass) and `DoTrayAssignments`. `UsePreferredHeading` ← `PlanAgvMoveJob`,
  `PlanReparkTrayJob`, `AssignDestForUntargetedMove`. `UseEvChargeHeading` ← `PlanChargePayloadJob`,
  `UsePreferredHeading`, `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`, `DoTrayAssignments`
  (2). `UseRetrievalHeading` ← `UsePreferredHeading` only. `first_tray_event` is written only by the tray
  tree (2284, 2333, 2952, 3064) and read once in the AGV tree (2487).
- `ApplyTransitionToFreeingMoves` handles **only `BAY_TRANSITION` and `VECS_TRANSITION`**: it registers the
  bay / VECS inbound pose with the generic `TRAY` footprint and applies the event. AGV and VRC events are
  skipped entirely (not applied to `working_state`).
- Direct stage calls in tests: `DoTrayAssignments` 4 (`scheduler_tests.cpp` 70, 165, 245, 378),
  `DoAgvAssignments` 9 (178, 381, 749, 810, 895, 996, 1063, 1129, 1287), `ResolveBlockingTrays` 1 (301).
  Context built as `std::make_shared<ScheduleContext>(MakeGuid(0, 0xDEADBEEF), state, rclcpp::Time())`,
  events added with `ctx->events.AddEvent/AddDependency`, result read with `std::tie(success, msg)`.
- `Plan` coverage by job type (end to end): MOVE_AGV, REPARK_TRAY, RETRIEVE, CHARGE_PAYLOAD, INSERT,
  READY_FOR_RETRIEVE, CHARGE_AGV, TRANSITION_BAY_*, CLEAN_GARAGE, MOVE_TRAY (advanced only). **Never
  covered: READY_FOR_INSERT, REBALANCE_GARAGE. No test sets `base_schedule`, `planned_jobs` or
  `active_jobs`.** Failure cases (jobs end in `STATE_ERROR`): 9 tests in `scheduler_jobs_tests.cpp`.
- `Scheduler` members: `layout_` (LayoutSPtr), `pg_` (used only in the constructor), `gg_`, `table_`,
  `logger_`, `cost_model_`, `bay_readiness_ratio_` (atomic), public mutable `costaudit_`, `printdags_`.
  No params member. `ScheduleContext` (`scheduler.hpp:57-117`): ctor takes `rclcpp::Time`; fields
  `request_id`, `request_id_str` (only used for `PrintGraph` labels under `printdags_`), `initial_state`,
  `start_time`, `disabledness_filters`, `events`, `scheduled_jobs`, `last_entity_event`,
  `first_tray_event`. `BoolStringPair` is `common/types.hpp:7`. `stdx` is namespace **`volley::stdx`**
  (`src/core/stdx/include/stdx/expected.hpp`, aliases over `tl::expected`, `E = std::string`;
  `Unexpected(msg)`, `Unexpected(fmt, args...)`, `AllHaveValues`). The scheduler already uses `stdx::Result`
  (`EnsureAgvMovePathsClear`, `InsertVrcActionsIntoDag`) and `stdx::Expected<bool>` (`RunAgvPathRepairPass`).
- No golden-file or reference-output test exists anywhere under `src/`. yaml-cpp is used in tests only as
  `YAML::Load(R"YML(...)YML")` into `DiscreteGarageState::Set`. Closest precedent:
  `motion_planner/test/continuous_state_tests.cpp:131-140` (loads a state YAML, compares messages).
  `interfaces::msg::to_yaml(msg)` (rosidl) serialises any message; `DiscreteGarageState::GetYaml()` uses it.
- Action-node GUIDs come from a **static counter** (`utils.cpp:307 CreateActionGuid`), so they depend on
  how many actions earlier tests in the same binary produced. Bay command ids are
  `std::to_string(MakeGuid(0, 1u))` constants; AGV command ids are `std::to_string(node guid)`.

## Design assumptions (Phase 0, step 4)

| Assumption | Result | Evidence |
|---|---|---|
| `ScheduleEvent` copy ctor public and defaulted | confirmed, with a caveat | `planner_core/schedule_events.hpp:36-51`: copy and move ctors public defaulted, assignment operators private, default ctor deleted. `TrayMove resolved = *move;` compiles only with a `TrayMove*`/`TrayMove&`, not through `ScheduleEventSPtr`. (The new design no longer needs resolved copies; it builds temporary `TrayMove`s from plain fields.) |
| `ScheduleEvent::Apply` is `const` | confirmed | base line 53, `TrayMove` line 153 |
| `AddEvent` returns false for a present pointer | confirmed | `event_dag.hpp:131-133, 574` |
| `AddDependency` returns false for a missing endpoint or duplicate edge | confirmed; never checks cycles; accepts self-loops | `event_dag.hpp:143-156` |
| `GetTopologicalOrdering` tie-break | **different from the prompt's wording**: a min-heap on job index only (`event_dag.cpp:56-60`); equal job indices come out in `std::priority_queue` order, which depends on push order, which depends on out-edge order. Vertex id is never used. | |
| `volley_add_library` exports only `include/`; accepts `STATIC` | confirmed (via `ament_auto_add_library`); accepts `STATIC`, `SHARED`, `MODULE`, `INTERFACE`, `LINK_LIBRARIES`; `NO_TARGET_LINK_LIBRARIES` is the default and dependencies come through `ament_target_dependencies` | `volley_cmake/cmake/volley_add_library.cmake` |
| Packages above `planner_core` | `agvhito_tools`, `motion_planner`, `scheduler`, `scheduler_advanced_tests` | `colcon list --packages-above planner_core` |
| `GarageOccupancyChecker` | in **common_ros**, template on `OccupantT` with hash/eq params; `OccupantSet = std::unordered_set<OccupantT, Hash, Eq>`; `GetBlockers` returns `stdx::Expected<OccupantSet>` | `garage_occupancy_checker.hpp:17-37` |
| `GarageEntityId.msg` letters | no constants in the message; letters in `common_ros/src/ros_utils.cpp:176-215` ('a','b','t','v','r','s') | |
| `check_branch_name.sh` | `jg/SW2-484/scheduler-core-refactor` passes (`^[a-z]+/([A-Z][A-Z0-9]*-[0-9]+)/[a-z0-9][a-z0-9-]*$`) | `scripts/check_branch_name.sh:28` |
| `.clang-tidy` naming | types/functions CamelCase, variables/members lower_case, private/protected members `_` suffix, constants `k` prefix CamelCase, enum constants UPPER_CASE; `modernize-use-designated-initializers` is **disabled** (designated initialisers are allowed, not required; the code already uses them) | `.clang-tidy:117-215` |
| `std::to_string(GaragePoseMsg)` | exists, `common_ros/print_utils.hpp:33` | |

## Decisions taken in Phase R (details and reasons in DESIGN-REVIEW.md; user's answers at its end)

1. Solver input is plain data without the DAG: `Input{initial_state, steps}` where a step is a
   `MoveRequest` (job index, optional tray id, optional destination) or a `StateChange` (a bay or VECS
   transition event, `shared_ptr<const ScheduleEvent>`, applied to the working state when reached).
   Result: `fills`, `new_moves`, `edges` (by step/new-move id), `first_move_by_tray`. An adapter in the
   module (`StepsFromDag`, `ApplyResult`) is the only code that touches `ScheduleEventDag`. (User: yes.)
2. `Solver::Solve(const GarageServices&, const Input&)`: services per call, so `DefaultSolver` is
   stateless, default-constructible and injectable through a `Scheduler` constructor parameter. (User: yes.)
3. Parity by instrumenting the existing tests (`test/parity.hpp`): each planning test records / compares
   a canonical YAML of its result in `test/reference/<Suite>.<Name>[.<suffix>].yaml`. No fixture loader,
   no separate suite. Reference inputs are the tests themselves. (User: yes.)
4. Renames kept in this PR (user's choice): `Scheduler` members (`motion_graph_`, `collision_table_`,
   `GetMotionGraph`, `pg_` local, `cost_audit_`, `print_dags_`, `TogglePrintDags`); `Plan*Job` →
   `Expand*Job`; `ScheduleContext` → `PlanContext` in `plan_context.hpp` with `event_dag`,
   `first_event_by_tray`, `keep_out_filter_by_footprint`, `last_event_by_asset` (still keyed by
   `GarageEntityIdMsg`), `AddScheduledJob`, `AppendToAssetChain`, `AddAfterJobLeaves`; `stdx` for the
   tray tree (falls out of the module work, no extra commit). Deferred: `AssetId`, `ros/convert`,
   `ScheduledJob`, `Timepoint`, `ReserveBaseScheduleAssets`, vocabulary aliases and report, stage folders
   and targets for other stages, include-check script, action-graph and motion-planning moves,
   side-by-side test, edit-replay machinery, private headers.
5. Module folder `include/scheduler/task_planning/tray_assignment/` (user's choice), namespace
   `volley::task_planning::tray_assignment`, alias `tray_assignment` in `scheduler.cpp`; `GarageServices`
   in `include/scheduler/garage_services.hpp`, namespace `volley`. One static library target
   `scheduler_tray_assignment`, linked into `scheduler`; one gtest `tray_assignment_tests`
   (`test/task_planning/tray_assignment_tests.cpp`) that links only the module.
6. Eight commits (table in PROMPT.md section 5). Commit 3 may be split (type, then fields) and commit 8
   at "module added, not yet used" / "Plan() switched"; worst case ten.
7. Heading helpers become value-returning: `EvChargeHeading` returns `std::optional<GaragePoseMsg>`,
   `RetrievalHeading` and `PreferredHeading` return the adjusted pose. The unused `tray_opt` parameter of
   `UsePreferredHeading` is dropped.
8. Section-8 quirks: all **keep**, except that the order in which `freeing_moves` blockers are turned into
   edges becomes id order instead of pointer-hash order (a deliberate, explained difference, visible only
   when one pose has two or more recorded occupants and only through tie-breaking; user accepted). See B4.
9. `scheduler_advanced_tests` is not touched (user's choice).
10. Error strings that spell a method name (`"PlanReadyForInsertJob ..."`) stay verbatim after the
    `Expand*Job` rename (rule 1).

## Bugs and oddities found, not fixed (report at review gates; none fixed silently)

- **B1 (fallback 1 path).** `scheduler.cpp:2842-2844` builds the advance move's path as
  `std::vector<GaragePoseMsg>{gg_.GetVertexFromPose(tray_opt->pose).value(), advance_move->GetDest().value()}`.
  The first element is a `Vertex` (`size_t`); `GaragePoseMsg` has only explicit constructors, so the
  initializer-list constructor is not viable and overload resolution picks `vector(size_type n, const T&)`:
  the path is **n copies of the destination pose**, with n = the vertex index of the tray's post-advance
  pose. Hypothesis from overload resolution; confirm with a one-line test in commit 4. Also `tray_opt` was
  refreshed after the advance was applied, so the advance move's `source_pose` in the emission loop
  (2929) and the root move's source (3037, 3050) are both the post-advance pose: the root tray's original
  pose is never registered in `freeing_moves` on this path. Keep exactly for parity; propose a follow-up.
- **B2.** The advance move is applied at 2833 and again at 2931 (`TODO(Gunther)`). The second `Apply` is a
  same-pose change (tray already at its destination) and its result is ignored. Keep.
- **B3.** `AssignDestForUntargetedMove` never registers the original move's source or destination in
  `freeing_moves` and never queries blockers for them (only the required moves get path edges). Keep.
- **B4.** `freeing_moves` is `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>`; `GetBlockers`
  returns an `unordered_set` hashed on the pointer, so when a pose has two or more occupants the order of
  the `AddDependency` calls (and so each vertex's out-edge order, and so topological tie-breaking among
  equal job indices) depends on heap addresses and can differ between processes. The new solver keys
  occupancy by step id, which is deterministic. The record / compare split of the parity harness
  (separate processes) will show whether today's output is stable.
- **B5.** `Plan()`: a job that already failed during expansion is pushed with `FailJob` again by the
  tray / AGV / sanity failure loops, which iterate `request_data.pending_jobs`. Verify; out of scope.
- **B6.** Error text `"DoTrayAssignments TrayMove with TrayId=<id>does not exist in working_state"` lacks a
  space. Keep (rule 1).
- **B7.** `DagBase::ToDotFormatString` has no `VRC_TRANSITION` case (planner_core; out of scope).
- **B8.** `assigned_events` in `DoTrayAssignments` is written and never read (dead; disappears with the loop).
- **B9.** `UsePreferredHeading`'s `tray_opt` parameter is unused (`(void)tray_opt`).
- **B10.** Commented-out `UsePreferredHeading` calls at 2820 and 2912 ("FIX: Does this break triple pick
  test?"). Keep commented out; do not resurrect.
- **B11.** `scheduler_advanced_tests/test07.cpp:23-26` says AGV assignment tie-breaking varies between
  builds. AGV assignment is untouched; it may limit how strict end-to-end references can be on that layout.

## Things a reviewer should know

- Error strings tray assignment can return (keep verbatim; they reach clients through `FailJob`):
  "Failed to get total ordering"; "Requested to move tray to <dest> but it's occupied, or not enabled.";
  "Requested to move tray <id> to <dest> but it's occupied, or not enabled."; "Requested to move tray to
  <dest> but could not get a valid vertex from the pose <pose>"; "Failed to find path for t<id> from <pose>
  to <dest>"; "Failed to find blocking tray resolution. Logic error, we advanced to dest without having
  resolved all blocking trays."; "Failed to apply advance move: <event>: <msg>"; "Failed to find open space
  for blocking tray t<id>"; "Failed to apply event during tray assignment: <event>: <msg>"; "Failed to get
  new total ordering"; "Failed to apply event in TrayAssignments: <msg>"; "Can't resolve a tray move with no
  tray id or dest"; "Tray pose does not exist in garage graph"; "Failed to find empty tray to move to
  <dest>"; "DoTrayAssignments TrayMove with TrayId=<id>does not exist in working_state"; "Failed to find
  open space for t<id>"; "Failed to apply unblocking move required: <msg>"; the raw `Apply` message. Plan()
  prefixes "Failed tray assignments: ".
- `ResolveBlockingTrays` failures are only logged (`WARNS`/`ERRORS`) and returned as `nullopt`; callers
  treat them as "try the next fallback". The free function keeps `std::optional`-like semantics through
  `stdx::Expected` whose error is only logged by callers.
- The `TRAY` footprint id is used for bay/VECS occupancy and for the root move's source/destination
  queries; the tray's own footprint (`CollisionEntityIdFromTrayState`) for required moves' paths. Keep.

## Review log

(Per commit: numbered feedback items with status open / done / discussed, and the final SHA.)

- Commit 1 `test(scheduler): add parity references to the planning tests (SW2-484 A)`: review packet
  posted 2026-10-22. SHA: not committed. After round 7: scheduler 80 tests pass with all 58 references
  re-recorded and compared in a fresh process. Feedback items (2026-10-22):
  1. `done` Give the reference files a filesystem structure by pipeline stage: task_planning
     (tray_assignment / agv_assignment), motion_planning, action_graph. Done as
     `test/reference/{task_planning/tray_assignment,task_planning/agv_assignment,action_graph}/`; no
     `motion_planning/` folder because no test observes that stage on its own (open point for the user).
  2. `done` The inputs and outputs of a reference are not clear; add a brief, clear markdown file.
     Every reference now carries `layout`, `input` and `output`; `test/reference/README.md` explains them.
  3. `done` Draft a Python script (container's uv environment) that renders every test case's problem
     setup into one standalone plotly HTML with a left navbar to browse them. Done as
     `src/planner/scheduler/tools/view_references.py` (plotly JSON built by hand, plotly.js from the CDN:
     plotly is not in `uv.lock`, so no dependency was added; open point for the user).

  4. `done` Use plotly if it makes the viewer simpler (less code, lower maintenance); adding the
     dependency is worthwhile. `plotly==7.1.0` added to the `dev` group of `pyproject.toml` (`uv lock`
     run in the container; `uv.lock` updated; the dev image installs the dev group at build time, so
     `uv run` installs it into the workspace `.venv` until the image is rebuilt). The script uses
     `plotly.graph_objects` and embeds plotly.js with `plotly.offline.get_plotlyjs()`, so the page is
     standalone (about 6 MB).
  5. `done` The viewer's icons and theme don't look good. Follow
     https://github.com/nextlevelbuilder/ui-ux-pro-max-skill for the theme, and draw the garage assets the
     way the study pack's diagram scripts do. Theme: the skill's "Developer Tool / IDE" palette (dark slate
     surfaces, green accent) and "Developer Mono" typography (JetBrains Mono + IBM Plex Sans, via Google
     Fonts with system fallbacks), with the study pack site's tokens (`site/src/styles/site.css`) and its
     categorical colours (sky trays, amber cars, teal AGVs, violet bays, green EvCharge, red disabled).
     Assets are drawn to scale as rotated footprints: node windows from the layout's `parking_windows`
     (tray size as fallback for TRAY-sized nodes), trays 14 ft x 7 ft and AGVs 157.5 in x 73.5 in from
     `common/constants.hpp`, cars from the payload's `length_m` / `width_m`; heading 0 = +y, 90 = -x.
     **Not done:** `scheduler_package/scripts/diagrams` and `figures/` are denied by the Read rules in
     `.claude/settings.local.json`, so the exact glyph conventions of `theme.py` were not consulted;
     remove the two deny lines if the drawings should match those figures more closely.

  Round 4 (2026-10-22, on the viewer):
  6. `done` Draw the origin and label the coordinate frame (x and y axes). Muted arrows from (0, 0)
     along +x and +y, 3 m long, labelled x / y; the origin dot says "origin (0, 0) m" on hover.
  7. `done` Say where the layout file is (path relative to the repo root) and where the test input is.
     A source line above the tables: layout path, `TEST(Suite, Name)` with its source file and line
     (found by scanning `test/*.cpp`), and the reference file path, all relative to the repo root.
  8. `done` EV charger as an icon with a yellow lightning bolt, like the study pack diagrams. A yellow
     (#facc15) bolt polygon 1.2 m tall at every EvCharge node, with a legend entry. **The example SVG
     (`deck/figures/d01_scenario.svg`) is denied by the same Read rules as `scripts/` and `figures/`**, so
     the glyph is a standard bolt, not a copy of the diagram's.
  9. `done` Labels overlap. Node names (`P6`, `W2`) now sit at the far end of each window instead of the
     centre; tray labels at the centre; AGV labels behind the AGV's rear; bay state text beyond the window.
  10. `done` Scrollbar: thin, slate thumb on a transparent track (`scrollbar-width` / `-webkit-scrollbar`).
  11. `done` Tables with fields. Under the figure: the source line; for an action graph the request's
      jobs (type, state, tray, AGV, bay, payload, destination, note), the initial trays / AGVs / bays /
      disabled nodes, the response (success, message, scheduled jobs with their action nodes) and the
      schedule (# | agent | action | from | to | detail | duration | after); for a stage the state, the
      input and output DAG events (index, job, event, agent, action, destination, AGV) with the edges and
      first_event_by_tray, and the moves in topological order. Agents read `AGV 2`, `tray 6`, `bay 1`,
      `VECS 1`; poses `W2 @ 180°` (node letter + id + heading); actions `move`, `move (carrying)`,
      `rotate`, `lift`, `lower`, `center`, bay / VECS command names.
  12. `done` Hovering a step row turns its arrow and number green and thick (`Plotly.relayout` on the
      annotations); hovering an arrow's midpoint highlights and scrolls to its row.
  13. `done` Package `tools/reference_viewer/`: `theme.py` (colours, fonts, footprint sizes), `garage.py`
      (layouts by name, node names, footprint geometry, bolt), `references.py` (files, test locations,
      the `Step` / `Event` model for both reference kinds), `scene.py` (the plotly figure), `page.py`
      (HTML, tables, hover linking); `view_references.py` is a 46-line CLI. 1,258 lines in all after
      black (the old single file was 626).

  Round 5 (2026-10-22, on the viewer; the study pack's `scripts/diagrams` are now readable):
  14. `done` Draw AGVs, trays, bays and the rest with the shapes of the diagram scripts, at the
      geometry sizes set in the repo. New `shapes.py` builds SVG paths (plotly path shapes) in each
      node's frame: parking stalls as rounded sky rectangles labelled at a corner (window minus 0.1 m),
      bays as blue rounded rectangles (window length, width + 0.9 m) with a thick door line on the side
      facing the garage, waypoints as dots, AgvCharge nodes as yellow circles with the diagrams' bolt,
      EvCharge stalls yellow with a bolt in a corner, trays 14 ft x 7 ft (`kTrayLength`, `kTrayWidth`)
      amber with two rails and a corner chip, cars from the payload's `length_m` / `width_m` pink with
      windshield and rear window, AGVs 157.5 in x 73.5 in (`kAgvLength`, `kAgvWidth`) green with four
      wheels, a lift plate (filled stronger when raised) and a chevron at the front, a floor with
      corridors under waypoint edges, and thick numbered route arrows. Colour roles follow
      `facility.py` (sky / blue / yellow / amber / pink / green); the pack's AGV is schematic 2.2 x 1.1 m,
      ours is the real size.
  15. `done` plotly moved from `dev` to a new group `scheduler` ("developer tools of
      src/planner/scheduler; not in the runtime images"), included by `dev`; `uv lock` re-run.
  16. `done` The source block is a three-row table: layout, test, reference.
  17. `done` Cause: `Plotly.react` mutates the layout object it is given, so the "original" annotation
      colours used to restore were already the highlighted ones. The page now hands plotly deep copies
      (`structuredClone`) and restores from the pristine figure. Verified by dispatching mouseenter /
      mouseleave in the page: arrow width 3 -> 5 -> 3.
  18. `done` Row highlight: accent-tinted background (`color-mix` 22 %), accent left border, bold.
  19. `done` Light mode: `Palette` dataclass with `DARK` and `LIGHT` (light colours from the pack's light
      theme), one figure per theme per reference (page 8.6 MB), CSS variables generated from the
      palette, toggle button in the navbar, default from `prefers-color-scheme`, remembered in
      localStorage.
  20. `done` Origin: red x and green y arrows (2.5 m) with bold labels and a ring at (0, 0); plotly
      grid: minor lines every 1 m, major every 5 m, zero lines stronger, ticks in metres on both axes.

  Round 6 (2026-10-22, on the viewer):
  21. `done` Misplaced items on pan / zoom. The geometry was plotly `layout.shapes` (SVG paths), which
      plotly re-renders on pan and zoom through its own code path; the floating stall and bolt were
      shapes left behind. All geometry is now scatter traces (filled polygons, rounded corners sampled
      as 6-segment arcs), added in drawing order, so it pans and zooms with the data. Checked by
      dragging and wheel-zooming in the browser: nothing detaches.
  22. `done` "grid off / on" button in the navbar (remembered in localStorage): hides the 1 m and 5 m
      gridlines; the x = 0 and y = 0 lines and the ticks stay.
  23. `done` Chargers are a 0.3 m cabinet with a bolt: at the node for AgvCharge nodes, just beyond the
      far end of the stall for EvCharge nodes, whose stall is drawn like any parking stall.
  24. `done` The navbar is a tree: test source file (`scheduler_tests.cpp (16)`) > `TEST` > its
      references, each leaf labelled by stage and suffix (`action_graph · to_insert`,
      `tray_assignment`, `agv_assignment`). Files open, the first test open.
  25. `done` Yes, both are output. Headings now say so: "output: response · scheduled jobs (the jobs
      as returned, with their action nodes)" and "output: response · schedule (the action nodes)";
      the inputs are "input: request · pending jobs" and "input: initial state".
  26. `done` One "input: initial state" table: kind | id | pose | state | lift | payload | disabled, with
      trays, AGVs, bays and disabled nodes as rows.
  27. `done` Package renamed `plan_viewer` (it draws plans: an initial state and the planned moves);
      the script stays `view_references.py`. Alternatives if preferred: `parity_viewer` (ties to
      `parity.hpp`), `garage_viewer`.

  Round 7 (2026-10-22):
  28. `done` Tree: stage folders as under test/reference (action_graph; task_planning > agv_assignment,
      tray_assignment), then, for action graphs, the request's job types (`RETRIEVE`,
      `INSERT + CLEAN_GARAGE`, ...), then the references by test name.
  29. `done` Every reference now starts with `description:` (one paragraph: "Scenario: ... Test: ...
      Expected: ..."), passed by the test to `TrayAssignment` / `AgvAssignment` / `ExpectPlanReference`
      (new `std::string_view description` parameter); the viewer shows it as a Scenario / Test /
      Expected block. 58 descriptions written from the test sources. Renamed tests (references renamed
      with them, all re-recorded): TrayAssignmentTest -> TrayAssignmentFillsBlankDestination,
      TrayAssignmentTestComplexDag -> TrayAssignmentResolvesManyBlockersThenAssignsAgvs,
      UnblockingTrayMoveTest -> TrayAssignmentMovesOneBlocker, MiAmigaEsSuAmiga ->
      AgvAssignmentSkipsDisabledAgv, AmigaSaysNo -> AgvAssignmentFailsWhenDisabledAgvBlocksPath,
      AmigaStash -> AgvAssignmentChainsThreeMovesAcrossTwoAgvs, NoAmigas ->
      AgvAssignmentFailsWithNoAvailableAgv, AmigaBaySos -> AgvAssignmentFailsWhenBayTransitionTrapsAgv,
      AmigaBaySo -> AgvAssignmentUsesAgvFreedByBayTransition, TrayLiftBayTransitionDependencyTest ->
      AgvAssignmentOrdersLiftsAroundBayTransitions, WeirdFultonRetrieve -> FultonRetrieveWithCleanGarage,
      AgvChargeJobMVP454 -> AgvChargeJobTwoAgvsDistinctChargers. ("Amiga" = Arguably More Intelligent aGv
      Assignment, the AGV-assignment stage's nickname in scheduler.hpp.) Found while describing:
      `ReparkUnplugVecsMoveAgvFirst` has exactly the same state and job as `ReparkUnplugVecs` (noted in
      its description; not changed).
  30. `done` "hello" is the job's `note` field as the tests fill it (input data, echoed back by the
      response); the column now reads "note (from the request)". The numbers are the job's action nodes,
      1-based positions in the schedule table; the column reads "action nodes (# in the schedule)" and
      shows ranges (`#1–#14`).
  31. `done` New `dag.py`: Graphviz `dot` (14.1.2 in the devcontainer; no Python dependency added)
      draws the DAG left to right as SVG, one per theme: for an action graph the schedule with its
      parent edges, for a stage the input event DAG and the output event DAG. Nodes are coloured by
      agent; hovering a node highlights its table row and arrow, and vice versa.
  32. `discussed` Kept `view_references.py`: the script names what it reads (references), the package
      what it draws (plans). Will rename on request.
  33. `done` "show solution" button: input only by default (no move arrows, no output tables, the input
      DAG for a stage); on, the arrows, the output tables and the output DAG / action graph appear.
  34. `done` Legend with glyphs drawn in the figure's style and explicit labels: parking stall
      (outline), customer bay (door on the garage side), waypoint, charger cabinet, tray (with rails),
      car on a tray (payload), AGV (chevron at the front), disabled node (dashed), planned move
      (numbered), origin with x (red) and y (green) axes. The "purple lines" were the bay outlines
      (blue in the dark palette), the green boxes the AGVs, the dashed red boxes disabled nodes.

  Round 8 (2026-10-22, on the viewer):
  35. `done` `rich==14.2.0` added to the `scheduler` group (`uv lock` re-run); `rich.progress.track`
      wraps the reference loop ("Drawing references", 12 s for 58).
  36. `done` Flags: `references.goals()` reads the goals from the input (MOVE_AGV / MOVE_TRAY /
      REPARK_TRAY destinations, the bay of INSERT / READY_FOR_* / TRANSITION_BAY_* jobs, every bay for a
      RETRIEVE, every VECS for a CHARGE_PAYLOAD, and for a stage the input DAG's tray-move
      destinations); `Scene.flags()` draws a pole with a pennant in the colour of what must get there
      and a label ("goal: tray 1", "goal: payload 1 to a bay"), shown in both views.
  37. `done` Axes are thin (1.5 px) with open heads (plotly arrowhead 4); moves are thick with filled
      heads and a numbered badge; and move colours no longer use the AGV body green (teal, sky, violet,
      pink by AGV id; amber for trays), so nothing green is a move.
  38. `done` A rotation draws a quarter / half circle arrow around the node from the old heading to
      the new (radius 1.1 m, grown for repeated rotations at the same node), with its number badge.
  39. `discussed` Yes: the response schedule (the action graph) has one `ActionNode` per AGV command
      (translate, rotate, lift, lower, centre) plus one per bay / VECS / VRC command;
      `ResponseFromTrajectories` emits one node per motion of the planned trajectories. The viewer
      shows it as is.
  40. `done` Origin entry removed from the legend.
  41. `done` `highlight(step, scroll)`: the row scrolls into view only when the hover comes from the
      figure; DAG and row hovers highlight without scrolling.
  42. `done` Every action now has a visible label: moves that share a segment take lanes 0.4 m apart
      (badges with them), rotations are arcs, lifts and lowers are numbered badges (▲ / ▼) stacked
      beside the node. The arcs are traces, so they are hidden with the solution like the arrows.

  Round 9 (2026-10-22, on the viewer):
  43. `done` Cause: the solution toggle restyled the step arc traces with `Plotly.restyle(plot,
      {visible}, current.step_traces)`; for a reference with no rotation arcs the list is empty, and
      plotly reads an empty trace list as "every trace", so the garage's traces were hidden (only the
      annotations, i.e. the labels, stayed). The call is now skipped when the list is empty. Verified:
      19 of 19 traces visible in the input view of CleanGarageAgvInTheWay.
  44. `done` Cause: the axes autoranged over the visible traces, so hiding or showing traces rescaled
      the view. The axis ranges are now fixed to the floor's bounds (`autorange=False`). Verified:
      identical ranges before and after toggling the solution.

  Round 10 (2026-10-22):
  45. `done` All 58 descriptions rewritten as complete sentences ("Scenario: On tiny_lot, ... Test: The
      test plans ... Expected: ...") and checked against the test sources once more; the bay remark now
      reads "the state lists no bay, so B1 is drawn without a bay state" (the layout has the bay node;
      the discrete state has no entry for it). All references re-recorded; 80 tests pass.
  46. `done` `JOB_GLOSSARY` (one sentence per job type, from the study pack's job chapter) shown as
      "what the jobs mean" under the request table for the job types in the request; a collapsed
      "terms used above" section at the bottom explains the actions (move, rotate, lift / lower,
      center, bay / VECS commands, "after") for action graphs and the event types, edges and
      first event by tray for stages.
  47. `done` `html, body { overflow: hidden }` (the page itself never scrolls; the panes do) and 12 px
      of right padding on the plot, so the mode bar is clear of any scrollbar.
  48. `done` README section "Building, running and recording": `poe build-pkg scheduler`,
      `poe test-pkg scheduler`, running one binary with gtest flags, `planner_core` and
      `scheduler_advanced_tests`, and recording with `RECORD_REFERENCE_OUTPUT=1`.
  49. `done` Badges now name their entity (`3 t2`, `5 a1`, `2 ▲ a1`); AGV-assignment references draw a
      dotted link from each AGV's start to the tray it was assigned to with a chip "AGV 1 → tray 2
      (#3)", shown with the solution, and get an "output: assignments" table (# | AGV | tray | to)
      whose rows highlight the move. Tray moves' badges carry the tray id, and the arrow's head is the
      bay or stall it goes to.

  Round 11 (2026-10-23):
  50. `done` Headers are now nouns: Request, Base schedule, Initial state, Response, Scheduled jobs,
      Schedule (plan); Initial state, Input events, Output events, Steps, Assignments (stages); the
      DAG box is "Action graph" / "Event DAG (input|output)". The glossary sections are gone.
  51. `done` Every table cell or header whose text is a known term (job types, job states, actions,
      event kinds, "after", "edges", "first event by tray") is dotted-underlined and shows its
      definition in a hover window (CSS, from a `data-tip` attribute); the definitions live in
      `references.py` as the scenario's `terms`.
  52. `done` `<hr>` dividers labelled INPUT and OUTPUT separate the description and provenance from
      the input tables and the output tables.
  53. `done` Stalls are a faint dotted outline only (no fill), and a "stalls off / on" button in the
      navbar hides them (remembered in localStorage).
  54. `done` The assignment links and chips are gone. Every asset and node has a hidden highlight
      outline; hovering a row shows the outlines of what the row describes: a step row its agent and
      destination node, an assignment row the AGV, the tray and the destination, a job row its tray,
      AGV, bay or destination. The arrow highlight stays for step rows.
  55. `done` `plan_viewer/static/page.html`, `style.css`, `app.js`; `page.py` inlines them, so the
      output is still one file.
  56. `done` Layered: `model.py` is a neutral `Scenario` (assets, node states, goals, steps, tables
      with highlight keys, graphs, terms); `references.py` is the only module that knows the
      reference format, the scheduler's messages, job types, event strings and method names;
      `scene.py`, `dag.py` and `page.py` consume the model only; `garage.py` reads layouts (the
      site_config format) and owns the geometry; `theme.py` the palettes. A different planner or
      file format needs a different adapter only.
  57. `done` Initial-state rows highlight their asset (covered by 54).
  58. `discussed` Yes: those references record `Scheduler::Plan`, i.e. the whole pipeline (job
      expansion, tray and AGV assignment, motion planning, action graph), and only the response is
      compared. Renamed: folder `test/reference/plan/`, stage "plan", parity function
      `Plan(scheduler, request, response, description)`; references re-recorded; README updated.
  59. `done` A "code under test" row in the provenance table: for a plan reference
      `Scheduler::Plan: <the Plan*Job method of each job type>, DoTrayAssignments, DoAgvAssignments,
      PlanMotions, ResponseFromTrajectories`; for a stage `Scheduler::DoTrayAssignments` or
      `DoAgvAssignments`. The method map is in `references.py` (it will follow the commit 2 renames).
  60. `done` The stray file was my own `artifacts/scheduler_references.html` from earlier runs, next
      to the user's `artifacts/planner_tests.html`; removed. The default output is now
      `artifacts/scheduler_tests.html` (not the current directory).
  61. `done` Sidebar title and page title: "scheduler tests".
  Also seen: `artifacts/.keep` shows as deleted in the working tree; not done by this session.

  Round 12 (2026-10-23):
  62. `done` A highlight is the asset's own outline emboldened (3.5 px) and filled stronger in its own
      colour: amber trays, green AGVs, sky-blue stalls, blue bays. No accent overlay (and the
      "highlighted on hover" legend entry is gone).
  63. `done` Hovering a step row (or its arrow or DAG node) dims the initial state's assets to 30 %
      opacity and shows a ghost of the step's agent at the pose the step leaves it in (a tray with
      rails, an AGV with its chevron), plus the destination stall or bay emboldened.
  64. `done` Assignment rows highlight the (AGV, tray) pair where they stand; they no longer carry a
      step, so no arrow or ghost.
  65. `done` Tray-stage step rows embolden the tray's ghost at the stall and the stall itself in blue
      (covered by 62 and 63).
  66. `done` The floor polygon is gone; the bounds still size the axes.
  67. `done` Script renamed `tools/view_scheduler_tests.py`, default output
      `artifacts/scheduler-tests.html`; README example updated.
  Found while checking: with `scaleanchor` and fixed ranges, plotly kept the aspect ratio by
  widening the ranges on every resize, and a zero-sized (hidden) tab blew them up to thousands of
  metres, garbling the drawing until a reload. Fixed with `constrain="domain"` on both axes: the
  plotting area shrinks instead, the ranges never change.
  Also seen: `artifacts/` now holds only the generated page; `.keep` and the user's
  `planner_tests.html` are gone, not through this session.

  Round 13 (2026-10-23):
  68. `done` The drawing should use the full width of the plot area; it sits in the middle and crops
      assets.
  69. `done` No parking-stall highlight on hover in the action table, nor in general; at most in tray
      assignment.
  70. `done` A notes folder in the SW2-484 folder, one subfolder per stage / commit with a markdown
      file of explanation and Q/A for the code, starting with: the C++ files under scheduler/test,
      the YAML under reference/plan and how it pairs with the site_config layout (and what `vexen`
      is), and why the tests hold YAML string literals instead of reading files.

  Round 25 (2026-10-26):
  104. `done` The force push failed at clang-tidy: 36 findings in the test files, two kinds.
       (a) bugprone-unchecked-optional-access on every `.value()` / `->` after an ASSERT_TRUE or
       EXPECT_TRUE on has_value(), in agv_assignment, assignment_cost, tray_assignment,
       agv_charge_job tests and scenarios.cpp (Dag): the check's dataflow cannot see gtest's
       macros. The team's precedent is src/agvhito/test/.clang-tidy, which disables that check for
       the folder with a justification; the same file now sits in src/planner/scheduler/test/
       (InheritParentConfig, covers stages/, jobs/, utils/ and the support sources).
       (b) readability-identifier-naming on the two local constexpr in
       TrayAssignment.ResolvesBlockerChainRecursively: locals take `k_` plus lower_case
       (LocalConstantPrefix / LocalConstantCase in .clang-tidy), so kRootTrayId -> k_root_tray_id,
       kJobIndex -> k_job_index; the kCamel form is for file-scope constants only.
       The "N warnings generated" lines are clang-tidy's per-unit totals over the headers, filtered
       out by clang-tidy-diff; only the listed findings count. `volley-in-container tidy` run after
       the fix: 0 findings in 822 s (14 min; the log is
       ~/.cache/volley-in-container/logs/20261026-102045-tidy-main.log). tray_assignment_tests
       rebuilt and passing (5 tests); commit-stage hooks green. Amended into commit 1, now
       0b22bba6 on top of 83569373; code notes updated (file table, clang-tidy section). The user
       force-pushes (`git push --force-with-lease`); the remote still holds f47bbb61.

  105. `done` Four review questions answered in the code notes, new section "Questions and
       answers" (commit size by kind: 73% recorded output, 2.1k authored, 6k code; how the
       recorded part could shrink 62% by omitting default-valued fields, measured; plan tests
       compare the response only, stage tests the event DAG; YAML-vs-struct comparison, with the
       one place the text is less exact: float32 durations at six significant digits).
  106. `done` Found while answering: `TrayAssignment.MovesOneBlocker` and
       `TrayAssignment.ResolvesManyBlockersThenAssignsAgvs` exercised no blocker on 275_sunrise_b
       (critical paths free; scheduler log confirmed). Re-posed, as the user chose: tray 2 now on
       P2066, the one stall on tray 1's path (new state empty_trays_at_p2066_p2067_p2077, AGV 1
       at P2075); tray 13 in the south-east corner P2150 of the block with P2149, P2148, P2135,
       P2134, P2133, P2119, P2118 occupied (new state two_agvs_eight_empty_trays_tray_13_at_p2150,
       replacing two_agvs_eight_empty_trays, which nothing else used). Recorded: one blocker move
       (tray 2 to P2061) chained before the root; two blocker moves (tray 10 to P2087, tray 11 to
       P2086) chained before the root, AGV 1 taking both and AGV 2 the root. The test's block map
       comment was wrong (the block is 3 columns x 4 rows of stalls, each column behind a lane
       waypoint, W2100-W2103 on the west side) and is redrawn. Descriptions rewritten.
  107. `done` The second force push failed with "files were modified by this hook" and no
       finding: I edited the two scenario descriptions (item 106) while the user's push was in
       the clang-tidy hook, and prek fails a hook whose files changed under it. Rule for me: no
       working-tree edits while the user pushes. Noted in the code notes.
  108. `done` Why clang-tidy took 14-20 min and looked single-threaded: scenarios.cpp and
       initial_states.cpp were sources of all 18 test binaries, so compile_commands.json had 18
       entries each and clang-tidy analysed each 18 times sequentially in one process (the two
       cumulative "N warnings generated" runs in the output). Fixed in CMake: static library
       scheduler_test_support (ament_find_gtest first, so the gtest targets exist), linked by every
       test binary. Measured: 822 s -> 66 s, 57 -> 23 analyses, 0 findings. Build 25 s, 170
       scheduler tests pass, hooks green. Code notes: build paragraph, walkthrough step 1-2,
       tidy section rewritten with the cause, the table and the no-edits-during-push rule.
       Amended into commit 1, now fe0550d8 on top of 83569373; tree clean; the remote still holds
       f47bbb61 until the user force-pushes.

  109. `done` Size of the PR, as the user asked: the recorded part of the plan scenarios
       compacted. `Compact` in scenarios.cpp after CanonicalResponse: GUID maps become one scalar
       (value when only the last four bytes are set, else 8-4-4-4-12), every default-valued field
       is dropped (zero, empty, false, empty sequence, all-default sub-message), maps of at most
       two scalars (poses) in flow style. Rule for readers: an absent field holds its default
       (README, "The recorded part"). Viewer: `field(message, *keys, default)` helper in
       scenarios.py, guid_text accepts an int, schedule_steps and the response tables use it; the
       page renders all 58 scenarios. Measured: recorded lines 22,257 -> 5,795 (-74%); the diff
       against main 164 files +30,601/-6,688 -> +14,259/-6,688. All twelve scenario binaries
       re-recorded; hooks green (clang-format and black reformatted once).
       170 scheduler tests pass. Amended into commit 1, now 9f1d4022 on top of 83569373; tree clean;
       the remote still holds f47bbb61 until the user force-pushes. Not done, as options for the
       user: the viewer (13 files, 2,900 lines) in a PR of its own; flow style per action node.

  110. `done` The user keeps the viewer in this PR ("it should be paired with this PR").
       Rebased onto the tip of main, e24b8e16 (one commit since 83569373, SW2-1000 central_api
       schema, no file overlap; clean). Commit 1 is now 0c041424. Scheduler rebuilt and its tests
       re-run on the rebased branch: 170 tests pass, tree clean. The remote still holds f47bbb61 until the user
       force-pushes.

  111. `done` Fetched and rebased again at the user's request: main moved five commits
       (PR #999, agvhito recovery and stdx scope-exit; no file overlap), rebase clean onto
       2cfd657a. Commit 1 is now c18425e7. Scheduler rebuilt, 170 tests pass, tree clean; remote still f47bbb61.

  112. `done` Pre-PR review against the Greptile configuration (the user pasted it). My hygiene
       scan plus two reviewer subagents (C++ and viewer, independent, no conclusions given). All
       fixes amended into commit 1, now fbbba8a2; details in the code notes' new section "Review
       against the Greptile configuration". Highlights: narrative/history comments cut, four
       TODOs without tickets resolved, three DrawGraph debug dumps removed, dead layout_test branch
       removed, README example and Load example corrected, wrapper mentions replaced by the env
       var; ASSERT before every schedule index / optional deref (crash -> clean failure);
       recording guards (ExpectOwnTest on every file, no file creation, write checked) and
       ExpectKeys on authored keys; quoted strings kept by IsDefault; GUIDs uppercase; jobs from
       1001 and request id 1000 (re-recorded all 45); viewer: lift/lower badges, corner control
       point (was the node centre), BLift bay, authored-only files, hover gating, layout link,
       outside paths, payload label. Commit message updated (compact form, support library, tidy
       exception). PR title to use: [SW2-484] Record the scheduler planning tests as scenario
       files. Verified: build, 170 tests, hooks, viewer renders 58 (105 lift / 101 lower badges).
       Diff vs main 164 files +14,284 -6,688. Remote still f47bbb61.

  113. `done` Three requests. (a) Rebased onto main a1c385f1 (four agvhito commits, no
       overlap, clean); commit 1 is now 632701c6; scheduler rebuilt, 170 tests pass, tree
       clean; remote still f47bbb61. (b) jira_ticket.md rewritten: title "Record the scheduler planning tests as
       scenario files", step-by-step instructions to create it as a Task under epic SW2-482 (the
       screenshot shows SW2-484 "Create interface for generic tray move solver" and SW2-487
       "Create benchmark set..." as the existing children), description in Markdown for the Jira
       editor, note that the branch name carries SW2-484 and should be renamed to the new key
       before the PR. (c) Code notes: "How a test run flows" rewritten as paragraphs; the plan
       test section now explains how `scenarios::Plan()` finds its file with no argument (gtest's
       current_test_info -> suite in snake case as the folder, test name as the file, optional
       suffix for a test with several scenarios, and the `test:` key checked back).

  114. `done` Assessed the other agent's implicit-guidelines report against the branch; plan in
       pr_prep_plan.md (nothing implemented). Recommended: drop the unused ament_index_cpp
       test_depend; shorten seven test names of 7+ words (mostly utils); split the viewer into a
       second commit of the same PR; PR description with the traceability list; one sentence
       that test/scenarios are gtest inputs, not simulation scenarios (Greptile's knowledge-base
       checks). Taste items: reuse volley::to_string for GUIDs, a shared kNow instead of fifteen
       rclcpp::Time(), split the two 800-line viewer modules, stale deprecated docs. Checked and
       fine: optional access, nodiscard, includes, no main/sleeps, comments, stage-test design.

  115. `done` Applied A1-A5, B6, B7 of pr_prep_plan.md: ament_index_cpp test_depend dropped;
       nine utils test names shortened; viewer split out as commit 2 (git rm --cached tools,
       index of pyproject/uv.lock restored from origin/main, amend, then add + commit); PR
       description drafted in pr_description.md; README first sentence says gtest inputs, not
       simulation scenarios; GuidScalar via std::to_string(GuidMsg); scenarios::kNow
       {0, 0, RCL_ROS_TIME} in scenarios.hpp used by the stage tests and Plan. Build, 170 tests,
       hooks green, no recording changed. The user had rebased the branch onto 6d656e15 (PR
       #1006) from the terminal; commits: 92deb897 (test, 150 files) + 00ca841b (feat viewer,
       15 files), branch +14,286/-6,689 over 165 files. Remote still f47bbb61.

  116. `done` B8 and B9. Viewer split: scenarios.py (875) -> records.py 307, reader.py 319,
       tables.py 241, scenarios.py 70; scene.py (830) -> canvas.py 295, paths.py 231, scene.py 356
       (line counts before black). Linear class chains (Reader <- Tables <- Adapter; Canvas <-
       StepDrawing <- Scene) so every method uses only its base: mypy green with no stubs. Page
       byte-identical before and after (filecmp). Deprecated docs: the two scheduler_jobs_tests
       entries removed; folded into commit 1 via detached amend + `git rebase --onto` (the wrapper
       allows rebase for this stage). Commits now 80535545 (test, 152 files) + 3162844b (viewer,
       20 files); tree clean; remote still f47bbb61. Note for me: `md5sum` and `cmp` are denied
       by the permission rules here; python's filecmp works.

  117. `done` The user created Jira SW2-1126 "Record the scheduler planning tests as scenario
       files" (Task under SW2-482, To Do, assignee/reporter Jon, label Scheduler_and_Dispatcher,
       start 2026-10-22, due 2026-10-30, Medium). Branch renamed locally to
       jmg/SW2-1126/scheduler-scenario-files (matches check_branch_name.sh); upstream still points
       at origin/jmg/SW2-484/scheduler-core-refactor (f47bbb61) until the user pushes the new name
       and deletes the old remote branch. Notes, PR description title and Jira draft updated.
       Ticket check: status should be In Progress; start date earlier than the work (commit 1's
       author date is 2026-10-23, the rounds began before); "is blocked by" picker left open
       empty (suggest "blocks" SW2-484 and SW2-487 instead); no sprint; the Development panel says
       "Connect development tools", so the GitHub app may not be connected for the project.

  118. `done` Notes folder regrouped at the user's request: the sub-ticket's files moved into
       `SW2-1126_scenario_files/` (jira_ticket.md, pr_description.md, pr_prep_plan.md, and the
       code notes as `code_notes.md`, formerly `code_notes/01-parity-references/notes.md`); the
       `code_notes/` index folder is gone, replaced by a README in the sub-ticket folder and a
       README at the epic level that maps PROMPT.md, this log, DESIGN-REVIEW.md, the sub-ticket
       folder, action_dependency_graph/ and scheduler_package/. PROMPT.md and this log stay at the
       root because CLAUDE.local.md names them. All of these are untracked in the notes repo
       (nothing committed). PROMPT.md section 5 names `SW2-482_pr_description.md` at the root for
       the epic-level PR text at the end of the stages; the sub-ticket's PR text is the one under
       its folder.

  119. `done` Three requests. (a) Epic folder renamed `pull_request_notes/SW2-484/` ->
       `pull_request_notes/SW2-482_scheduler_core_refactor/` (git mv, so the tracked
       action_dependency_graph files are staged renames in the notes repo; nothing committed) and
       the log `SW2-484_notes.md` -> `SW2-482_notes.md`; every path updated: CLAUDE.local.md
       (paths only; its section heading still says "SW2-484 refactor", the user's wording),
       PROMPT.md (paths, and `SW2-482_pr_description.md` for the epic-level PR text),
       DESIGN-REVIEW.md, both READMEs, code_notes.md. (b) `review_rules.md` at the epic level:
       the Greptile and reviewer rules distilled, with what was applied and a pre-PR checklist.
       (c) PR format surveyed with gh over the last 40 merged PRs: titles `[SW2-xxxx] ...`
       throughout; bodies `# What` / `# Why` / `# Testing` in 17 (incl. the user's #973), or
       `## Summary` / `### Changes` / `## Fix`; `Refs:` line; no PR template in .github.
       pr_description.md rewritten in the What/Why/Testing form with the traceability list under
       What.

  Round 24 (2026-10-26):
  103. `done` Jon's force push is slow at the clang-tidy pre-push hook; where does the output go,
       and a code-notes section on it. Answer: tools/clang-tidy-diff-hook (prek.toml, stage
       pre-push) pipes `git diff -U0 origin/main...HEAD` into clang-tidy-diff, which analyses every
       changed translation unit whole (clang-analyzer-* included) and filters to changed lines;
       output is captured and printed only at the end, and prek shows it only on failure; no log
       file unless `--output-log`. 27 C++ files in this commit, each pulling scheduler.hpp, hence
       the time. I never ran `volley-in-container tidy` on the rewritten tests: an omission, noted
       in the code notes; findings, if any, go into the next amend.

  Round 23 (2026-10-26):
  100. `done` Paths: each leg is a straight line beside its segment, cut 1 m short at both ends, and
       consecutive legs are joined by a quadratic Bezier corner whose control point is where the two
       legs' lines meet (a hairpin past the node when the path turns back, straight on when it
       continues). Lanes: every leg sits 0.3 m to the right of travel plus 0.25 m per earlier pass
       over the same directed segment by any agent (`Scene.lanes`, cycling after seven), so the
       repeated passes of AdvancesRootTray fan out instead of stacking. Arrowheads end each straight
       leg; the hover stretch of a leg is its straight part plus half of each adjacent corner.
       Catmull-Rom and the per-agent offset are gone. Checked in-process (finite curves, lane counts
       up to 3 passes); the browser pane still refuses the page, so the look is Jon's to judge.
  101. `done` Code notes: "How a test run flows" rewritten as four parts (from CMake to a binary,
       inside a binary before the first test, one plan test RetrieveJob.FromStall, one stage test
       TrayAssignment.MovesOneBlocker, plus what a failure looks like), every step naming the file
       and the function; a table of contents at the top, generated from the headings.
  102. `done` Jira sub-ticket drafted in `jira_ticket.md` (summary, objective, scope, definition of
       done, out of scope, observations for follow-up, review guide), to paste into SW2-484.
       Amended: commit 1 is b7d4a3d5 (viewer only this round), tree clean; remote still f47bbb61.

  Round 22 (2026-10-26):
  97. `done` Rebase onto the tip of main: 83569373 (data-race fixes merge), two new commits, none
      touching the scheduler package; no conflicts; commit 1 is ebc0a2b8. Jon had pushed f47bbb61
      himself on 2026-10-23 (origin/jmg/SW2-484/scheduler-core-refactor), so the remote is now
      behind the rewritten branch and needs a force push, which stays Jon's.
  98. `done` Viewer paths: `Scene.steps` takes all steps and draws one path per agent (AGV or tray):
      a Catmull-Rom curve through the nodes of its moves (12 samples per leg), shifted to the right
      of its direction of travel by 0.3 m plus 0.3 m per agent, so a return leg over the same
      segment and other agents' paths stay apart; an arrowhead (plotly marker `arrow` with
      `angleref: previous`) ends each leg; one hidden thicker trace per leg lights up on hover
      (`segments` in the entry data; app.js shows it with the badge highlight, only while the
      solution is shown); rotations, lifts, lowers and lift rides are numbered badges (⟳ ▲ ▼ ⇅).
      AGV colours are shades of green (dark theme #4ADE80, #15803D, #A7F3D0, #22C55E; light
      #15803D, #4ADE80, #14532D, #65A30D), trays amber. The old per-step arrows, lanes and arcs are
      gone. Checked in-process (paths, colours, stretches hidden, badges, arrowheads per leg); the
      browser pane refused the page this session, so the look is for Jon to judge.
  99. `done` Code notes: "How a test run flows, from CMake to the comparison": CMake (`scheduler_tests`
      list, `volley_add_gtest` -> `ament_add_gtest`, the define), build, `colcon test` / CTest /
      the result files, gtest's `main` and static registration, the order inside `scenarios::Plan`
      (path from test info, file parse, initial state, Scheduler constructor and the cached
      collision table, request, two plans, canonicalisation, comparison or recording), a stage
      test, and what a failure prints.
      Post-rebase run: 170 + 23 + 16 tests pass; hooks green. Amended: commit 1 is 01c3edb0, 162
      files on 83569373; local branch ahead 3 / behind 1 of the pushed f47bbb61 (force push is Jon's).

  Round 21 (2026-10-23):
  96. `done` Rebase onto the tip of main again: 3d4048e0 (showcase nightly merge), eight new commits,
      none touching the scheduler package or the dependency files; no conflicts. Commit 1 is
      f47bbb61. Build and tests re-run on the rebased branch (see below).

  Round 20 (2026-10-23):
  95. `done` The commit message still read as subjective in its first sentences; keep it objective,
      no mention of previous authors, no indirect criticism. The first paragraph now states what the
      change is and what it guarantees, without a judgement on the existing tests; "defunct" became
      "decommissioned". Amended: commit 1 is 1c9d4236, 162 files, working tree clean.

  Round 19 (2026-10-23):
  92. `done` The commit message sounds too casual; make it more professional. Rewritten: the problem
      (a refactor is due, the tests assert only what each author chose), the change, the layout
      moves and the viewer, in three paragraphs without colloquialisms.
  93. `done` utils_tests.cpp -> test/utils/{base_state_validation,empty_tray_count,bay_rebalancing}
      _tests.cpp, suites ValidateBaseState (4), CountEmptyTrays (1), BayRebalancing (8). The YAML
      literals became initial states on 275_sunrise_b (two new files: a car too long for its stall,
      an AGV on an unknown node) or, for the abstract bay states (bays 1 to 4, no layout), a small
      MakeState({bays}, {trays}) helper; the 14 split cases are a table; the event-by-event tray
      count uses four helpers. Added to the CMake list (now `scheduler_tests`); the old block and
      file are gone. CountEmptyTrays lives in common_ros/discrete_garage_state_utils.hpp.
  94. `done` Style of src/agvhito/src/sm (read: executing_order_state, context_utils, booting_state,
      idle_state, root, two headers, test_layout_utils). Rules derived and applied, by script for
      the 15 stage and job files (scratchpad/style.py) and by hand for the support files: includes
      limited to what the file uses, grouped gtest / <...> sorted / "..." sorted; anonymous
      namespace for file-local helpers and constants (kLayoutName, InsertExpectation, ExpectInsert,
      ExpectRetrieveThroughLift); const on every local not reassigned (by reference when it only
      reads); _opt -> _or, iterators _it; /// doc comments with @p and @return in the headers and on
      helpers, [[nodiscard]] on value-returning functions; std::format for every message; comments
      as full sentences stating what holds ("Every job was planned") instead of "make sure it was
      planned"; EXPECT_TRUE instead of EXPECT_EQ(x, true); dead locals removed; the request note
      "hello" dropped from every scenario (all 58 re-recorded: the note echoes in the response).
      Listed in the code notes under "Conventions".
      Result: hooks green, scheduler 170 (15 planning binaries + 3 utils), planner_core 23,
      scheduler_advanced_tests 16 tests pass; viewer regenerated. Amended: commit 1 is ea53f390,
      162 files on top of 5ad693dc, working tree clean.

  Round 18 (2026-10-23):
  88. `done` Keep tiny_lot for the two blocking-tray fallback scenarios.
  89. `done` Remove all dead code: the commented-out DoubleRetrieveDodgeAgv (with its TODO line) and
      a commented-out SetDest line in tray_assignment_tests.cpp are gone; the ASCII diagram of the
      blocker block was rewritten with the sunrise node names (a drawing, not code). Nothing else
      commented out remains in the test files (rg for comment lines ending in ; { } or starting
      with a call).
  90. `done` Code notes: a "How the comparison works" section. Nothing touches the disk when
      comparing: the response is canonicalised in memory (message -> to_yaml text -> YAML node ->
      GUID / sort / field-name passes), the file's `output` node is parsed, both are emitted to
      strings and compared line by line; only recording writes the file.
  91. `done` Branch renamed locally (`git branch -m`) to jmg/SW2-484/scheduler-core-refactor; it had
      no upstream, so nothing to rename on the remote.
      Amended after the dead-code removal: commit 1 is 5b965186, 156 files on top of 5ad693dc,
      working tree clean, hooks green, retrieve_job_tests and tray_assignment_tests re-run.

  Round 17 (2026-10-23):
  81. `done` (two exceptions) Remove layout_test and tiny_lot; use 275_sunrise_b. Jon: EV-charger
      scenarios on 38_gramercy, the rest on 275_sunrise_b, triple_pick_lot too.
      Done: 27 scenarios moved to 275_sunrise_b (around bay B2068: W2069 door, W2070, W2064,
      stalls P2075, P2066, P2067, P2077; the triple_pick block as the 3x3 stalls P2116 to P2149
      with the waypoints W2100 to W2102 beside them), 13 to 38_gramercy (car on charger E23, AGV at
      P19; chargers E21, E23, E25; the bay is the car lift BL26 on floor 1, VRC 1 idle there).
      Exceptions: RetrieveJob.AdvancesRootTray and ParksBlockerOnCriticalPath stay on tiny_lot. On
      sunrise with the garage open the blocker drives off to a waypoint and no fallback fires; with
      everything outside a region disabled, either no path is found (a disabled waypoint 0.8 m
      from the door node, W2063, counts as a disabled area; an AGV on the rotation node W2064 blocks
      the tray's path) or, once the fallbacks do fire, the planner cycles (log of 4.6 million lines,
      killed after ten minutes). Jon to decide: keep tiny_lot for these two, or drop them.
  82. `done` "I thought the jobs would be provided and parsed from the YAML file rather than hard
      coded in the source": they are now; see the changes below.
  83. `discussed` "Are we testing against hardcoded expected values?": both. The EXPECT_* lines in a
      test are the hand-written expectations of the properties its author cared about; the recorded
      `output` of the scenario file is the complete result, compared on every run, so nothing changes
      silently. Explained in the code notes.
  84. `done` Reorganise the test folder: `test/scenarios/garages` -> `test/scenarios/initial_states`;
      `test/garage_states/` (one dead file) removed with its CMake install line; the commented-out
      DoubleRetrieveDodgeAgv that loaded it stays commented (it names 576_eccles_half too).
  85. `pushed back` Delete utils_tests.cpp? It tests production code in scheduler/utils.hpp (garage
      state validation, bay classification and rebalancing), 13 tests, nothing to do with the
      scenarios; deleting it loses coverage the refactor may rely on. Kept, pending Jon's answer.
  86. `done` VS Code shows Crowdsec schema errors on the YAML: SchemaStore maps
      `**/scenarios/*/*.yaml` to the Crowdsec scenario schema. Every scenario file now sits two
      folders below `scenarios/` (`plan/<suite>/`, `task_planning/<stage>/`, `initial_states/<layout>/`),
      which that pattern does not match. No VS Code setting needed.
  87. `done` Commit message without Jira references, one to four paragraphs with context; rebase onto
      the tip of main (done first, no conflicts: main's five new commits touch nothing of ours).

  Round 17 (2026-10-23) changes:
  - 87: `volley-in-container` allows `git rebase` for this stage (ALLOW_REBASE=1 next to ALLOW_AMEND);
    rebased onto 5ad693dc (pecos showcase layout merge) cleanly.
  - 82 and 84: the scenario file is now authored: `test` (Suite.Name; the loader refuses another
    test's file), `description`, `initial_state` (`<layout>/<name>`), `scheduler` (params that differ
    from the defaults), `request` (`jobs`: type and the ids, payload GUID, destination, note the job
    needs; `base_schedule`: reserved AGV commands), then the recorded `output` (and `input.dag` for
    stage scenarios). Recording rewrites only the part from the first `input:`/`output:` line on.
    C++: `test/scenarios.hpp/.cpp` replaces parity.hpp (`scenarios::Plan(suffix)` loads the running
    test's file from gtest's test info, builds scheduler and request, plans twice, compares or
    records, returns the Run with scenario, scheduler, request, response; `scenarios::Stage` /
    `ExpectStage` for the stage tests), `test/initial_states.hpp/.cpp` replaces garages.hpp. A plan
    test is now `const auto run = scenarios::Plan();` plus its assertions. Files:
    `plan/<suite_snake>/<Name>[.<suffix>].yaml`, `task_planning/<stage>/<Name>[.<suffix>].yaml`.
    Conversion by script (scratchpad/to_scenarios.py) for 44 scenarios, by hand for 14 (multi-request
    tests, base schedule, the insert helper, the retrieve fallbacks, state mutations -> three new
    initial states: agv_at_w8_chargers_10_14_disabled, agv_and_empty_tray_in_bay_ready_to_insert,
    agv_in_bay_7_ready_to_retrieve). Equivalence check against the committed recordings: 57 of 58
    outputs identical apart from job GUIDs (now numbered 32, 33, ... in order) and the normalised
    type_name / state_name / note. The one difference is a fix: AgvChargeJob.TwoAgvsDistinctChargers
    gave both jobs GUID 32 in the old test, so the scheduler planned one job; with distinct GUIDs both
    AGVs charge. BackToBack's second job had been merged by the script (same variable name in two
    blocks) and was fixed by hand; same for the two charge jobs.
  - Viewer: reads the authored keys, the initial-state file (defaults filled in) and the compact jobs;
    the tree is plan -> suite folder -> scenarios; the source table names the initial-state file.
  - README rewritten for the authored format. Hooks green. 155 + 23 + 16 tests pass.
  - Commit message rewritten (three paragraphs of at most 92 columns; commitlint rejected a 101-column
    line on the first try; no ticket references) and amended: commit 1 is b8725fcc, 157 files on top
    of 5ad693dc, working tree clean.
  - Round 18 (the move): mapping by script (scratchpad/port_layouts.py: node and heading maps
    tiny_lot -> sunrise {1: 2068, 2: 2069, 3: 2070, 5: 2064, 6: 2075, 8: 2066, 9: 2067, 11: 2077},
    headings rotated by 90 degrees; triple_pick_lot -> the sunrise block), gramercy states and
    scenarios written by hand (scratchpad/port_gramercy.py). Findings while re-recording:
    - the retrieval-heading rule does apply on gramercy (stalls and lift share heading 90): a
      reparked car is lowered at the reciprocal heading because its payload is reciprocal_to_tray,
      so the repark assertions accept the reciprocal heading (IsAngleOrReciprocal);
    - retrieves on gramercy go through the lift: VRC move commands around the AGV commands and the
      AGV hops from L2 to BL26 without a command; the retrieve-from-charger tests share a helper
      (ExpectRetrieveThroughLift) that checks that;
    - the chain-recursion stage test needs its 3x3 block closed off (disabled_nodes), else the
      block's open edges make blockers unnecessary;
    - on sunrise the car retrieved from P2066 enters the bay at 2068@0 (inbound heading 0).
    - the two layout-only tests (readiness ratio, last entity event) load 275_sunrise_b.
    - the viewer draws a move between two nodes at the same spot (the lift's floors L2 / BL26) as a
      badge instead of dividing by a zero edge length.
    Result: 155 + 23 + 16 tests pass, hooks green, viewer checked (layouts: sunrise 28, gramercy 13,
    pecos 15, tiny_lot 2). Amended: commit 1 is addab96c, 156 files on top of 5ad693dc, message
    updated for the layouts, working tree clean. Code notes rewritten for the layouts.
  - 81 before the move: the port of the tiny_lot (36), layout_test (4) and maybe triple_pick_lot (3)
    scenarios to 275_sunrise_b waits for Jon's answer on the 13 EV-charger scenarios (no EV charge
    node on pecos or sunrise; 175_e82nd, 38_gramercy and CambridgesideV8 have them) and on
    triple_pick_lot.

  Round 16 (2026-10-23):
  78. `done` Viewer: a collapsible section near the top of the nav listing every layout the scenarios
      use, to check whether others should go.
  79. `done` The C++ test files are still very large; decompose them into smaller files, perhaps with a
      file layout, without over-engineering: files of a few hundred lines at most.
  80. `done` Commit now to save the work; afterwards every feedback iteration of this stage is a
      `git commit --amend` until the stage is complete.
      2026-10-23: Jon allowed `--amend` for this stage: `volley-in-container` lets
      `git commit --amend` through (ALLOW_AMEND=1 in the script, to set back to 0 after stage A)
      and Jon removed the deny rule from .claude/settings.local.json. Round 16 amended in: commit 1
      is now cbac1ccd, 153 files against main, hooks green (log 20261023-130835). From here on,
      every round of stage A is staged by name and amended with
      `volley-in-container git commit --amend --no-edit`.

  Round 16 (2026-10-23) changes:
  - 80: committed as instructed, before 78 and 79, with the state of round 15:
    `test(scheduler): add parity references to the planning tests (SW2-484 A)`, 137 files, hooks
    green (volley-in-container git commit, log 20261023-125147). The rounds that follow must be
    amended into it, but `volley-in-container` refuses `--amend` (and CLAUDE.local.md forbids it): the
    user's call how to lift that for this stage. Until then the round-16 work stays unstaged.
  - 78: the nav starts with a "layouts" section (collapsible, open): one row per layout with the
    number of scenarios on it and its file; a click shows the first scenario on that layout. Entry
    data carries `layout` and `layout_file` (page.py); app.js builds the section before the tree.
  - 79: the three planning test files became fifteen, one gtest suite and one binary each, under
    `test/stages/` (tray_assignment, agv_assignment, assignment_cost, sanity_check, scheduler_state:
    tests that call the scheduler's internals) and `test/jobs/` (move, repark_tray, repark_tray_
    charger, retrieve, retrieve_charger, charge_payload, insert, bay, agv_charge, clean_garage: tests
    through Plan()). Sizes 123 to 463 lines (retrieve_job_tests carries the dead commented-out
    DoubleRetrieveDodgeAgv, 60 lines). Suites are named after the file (TrayAssignment, RetrieveJob,
    BayJob, ...) and the test names lost the suite's prefix (RetrieveJob.FromReadyCharger,
    AgvChargeJob.SkipsDisabledChargers, MoveJob.AgvToBay, ...), so every recorded file was renamed
    and re-recorded (58 files, same content apart from descriptions that name other tests).
    `IsLift` / `IsLower` moved to `test/agv_commands.hpp`. CMake: a `planning_tests` list and one
    `foreach` that adds each binary with parity.cpp and garages.cpp, `test/` as include dir and the
    scenario define. The viewer locates tests with `rglob`. Split done by a script
    (scratchpad/split.py) from the committed sources; no hand fixes needed, build green with no
    warnings, hooks green.
  - uv keeps recreating `.venv` on the host (host Python 3.14.8 vs the container's 3.14.4): the two
    sides ping-pong. Harmless so far (packages come from the cache); worth running the viewer in the
    container instead if it bothers.

  Round 15 (2026-10-23):
  76. `done` Test layouts: we need 5675_pecos full (eng + qa); 275_sunrise_b is recommended; avoid
      576_eccles (the former HQ, defunct) and 1355_fulton (a defunct lot).
  77. `done` Update the code notes every time, especially after C++ changes; rewrite the document and
      drop sections, questions and content that are no longer relevant.

  Round 15 (2026-10-23) changes:
  - 76: the 13 tests on 576_eccles_half (3 sanity checks, ReparkTrayJobAdvanceToWaypoint,
    AgvChargeJobTwoAgvsDistinctChargers, DontGoToDisabledChargeNode) and 1355_fulton (AgvChargeJob,
    AgvChargeJobInBay, TransitionBay, CantTransitionDisabledBay, FultonRetrieveWithCleanGarage, the four
    insert tests) now run on `5675_pecos_combined` (28 nodes: the eng and qa sandboxes together, bays
    B7 and B21, AGV chargers C10, C14, C16, ten stalls, no EV charger). Nine new garage files under
    `garages/5675_pecos_combined/`; the eccles and fulton folders and the old recorded files are gone.
    Renames: FultonRetrieveWithCleanGarage -> RetrieveWithCleanGarage; FultonInsertBay{1,2}TrayHeading
    {0,180} -> InsertFromBay{7,21}Tray{Heading90,Reversed}. Node ids in assertions follow (charger C16
    instead of 60, C10 instead of 20140/20150, bay 7 instead of 1, bay 21 instead of 2). The nine
    ported job and sanity tests passed with the expectations carried over unchanged.
  - 76, the insert tests: the four fulton tests checked the V2 rule "lower the inserted car at the
    heading that makes the retrieve fastest" (`InitRetrievalHeadings`: the reciprocal of the
    highest-priority retrieve bay's inbound heading, cached for the stalls whose headings allow it and
    that can reach the bay pose). That rule yields nothing on 275_sunrise_b by construction (bays at
    heading 0, stalls at 90: 180 is never an allowed stall heading) and nothing on 5675_pecos_combined
    either (the run logs "UseRetrievalHeading, No retrieval heading for dest node 5/6"; the headings
    pass the first check, so the path check from stall@90 to bay@90 must fail; not investigated: not
    this PR's job). A first port to sunrise (busy garage, cars in B2052 / B2068) confirmed: the
    planner just minimises rotation and the two insert headings ended at different stall headings.
    So the tests moved to pecos with the expectations that hold there: the nearest AGV does the job,
    it enters the bay at heading 90 (also for a reversed tray), lifts, lowers outside the bay. The
    rest is in the recorded file. Observed and worth a look by the team: on pecos the planner parks
    the inserted car on W31 / W41, the waypoint in front of the bay, not in the free stall P15.
    The four tests share one helper (`ExpectInsert`, `InsertExpectation`) instead of four copies.
  - `k576EcclesHalfLayoutName` stays in scheduler_tests.cpp: the commented-out DoubleRetrieveDodgeAgv
    references it. Dead with the test.
  - Scenarios README names the layouts to use and the ones to avoid.
  - 77: `code_notes/01-parity-references/notes.md` rewritten as a description of the commit as it
    stands (no history, resolved questions dropped); to be redone after every C++ change.
  - uv recreated `.venv` on the host during a `uv run` (host Python 3.14.8); the container's hooks run
    on the system Python and were unaffected (prek 0.3.8 checked).

  Round 14 (2026-10-23):
  71. `done` Plotly's home / reset buttons drop the full-width fit; the drawing must always use the
      full width.
  72. `discussed` "How does the plan YAML pair with the site_config YAML and the built-in YAML?" is moot
      now that the states live in files (item 73): a scenario names its layout and its garage file.
  73. `done` Move the YAML out of the C++ tests for this stage, even if it breaks the original design:
      too much coupling between scenario config and test code, and files too big to review.
  74. `done` No unclear acronyms (vecs, vexen) in our YAMLs, even if the message schema uses them;
      standard acronyms like AGV are fine.
  75. `done` Rename test/reference to something like test/scenarios or test/cases.

  Round 14 (2026-10-23) changes:
  - 71: Plotly's own "reset axes" and "autoscale" buttons are removed from the modebar and a "Fit the
    drawing" button (home icon) calls `refit`; a double click refits too (`plotly_doubleclick`).
    Verified: after a forced autorange the fit button restores full domains and the area's aspect.
  - 75: `test/reference` -> `test/scenarios`; the define is `SCHEDULER_SCENARIO_DIR`; the viewer's
    adapter module is `plan_viewer/scenarios.py` and the script flag `--scenarios`.
  - 73: every inline state (60 literals, 54 distinct) became a file `test/scenarios/garages/<layout>/
    <name>.yaml` (55 files: 54 plus the two fillings of the `{blocker_node}` template, minus one
    shared) loaded by `garages::Load("<layout>/<name>")` (new `test/garages.hpp/.cpp`, in the three
    planning binaries). The folder is the layout (`layout_test` resolves to common_ros's
    test_layout.yaml, the others through `GetLayoutPathByName`), so the tests' layout constants and
    the `GetLayoutPathByName` boilerplate went too (two tests without a state keep it). Garage files
    drop fields at their default (lift, tray_id, agv_id, disabled, empty payload GUID, charging,
    reciprocal_to_tray, hash, is_faulted), print GUIDs as `00000000-0000-0000-0000-000000000001`
    strings (what `ParseGuid` reads) and `pose: {node_id, heading}` on one line, and comment every
    numeric `state` with its meaning. Names describe the garage (`tiny_lot/car_on_ready_charger_8`),
    not the test, so shared states are shared: `empty_trays_at_p9_p6_e11` (2 tests), `agv_at_p9` (2),
    `agv_lifting_tray_in_bay` (2), `576_eccles_half/agv_at_51` (3), `layout_test/car_charging_at_e11`
    (2). Migration done by a script (scratchpad/migrate.py) from backed-up sources; three spots fixed
    by hand (a `[set, set_msg]` capture, two `EXPECT_TRUE(success)` left before their declaration).
    Line counts: scheduler_tests.cpp 2101 -> 1310, scheduler_jobs_tests.cpp 3229 -> 2056,
    scheduler_insert_orientation_tests.cpp 977 -> 411. Test counts unchanged (26, 34, 4).
  - 74: in the garage files and the recorded files, `vexen` -> `ev_chargers`, `vrcs` ->
    `vertical_conveyors`, `vecs_id` / `vecs_command` -> `ev_charger_id` / `ev_charger_command`,
    `vrc_id` / `vrc_command` -> `vertical_conveyor_id` / `vertical_conveyor_command`. The garage
    loader maps the two list names back before `DiscreteGarageState::Set`; `parity.cpp`
    (`SpellOutFieldNames`) renames the keys of every message dump. Event strings in the DAGs
    (`VECS_TRANSITION`) come from the C++ `ToString` and stay; the viewer's glossary explains them.
    Descriptions say "charger 8" instead of "VECS 8". Eleven tests renamed so that no file name says
    Vecs: ReparkTrayJob{GoodVecs,BadVecs,ChargingVecs,BadVecsDest,GoodVecsAtDest} ->
    ReparkTrayJob{FromReadyCharger,FromUnavailableCharger,WhileCharging,ToUnavailableCharger,
    ToReadyCharger}; RetrieveJob{GoodVecs,BadVecs,ChargingVecs} -> RetrieveJob{FromReadyCharger,
    FromUnavailableCharger,WhileCharging}; ReparkUnplugVecs -> ReparkTrayJobUnplugsCharger;
    ReparkUnplugVecsMoveAgvFirst -> ReparkTrayJobUnplugsChargerAgvMovesFirst; ChargePayloadJobNoVecs
    -> ChargePayloadJobWithoutCharger. The C++ message constants (TYPE_VECS_COMMAND, vecs_command)
    stay as they are in the test assertions: code, not YAML.
  - Decision taken without asking (say so if wrong): the garage file holds the state only; the jobs,
    base schedule and event DAGs stay in C++ because there is no YAML reader for the job messages and
    they are the part of a test a reviewer reads with its assertions.
  - All 58 recorded files re-recorded (every one changes: the field names). Build green, no
    warnings; scheduler 80, planner_core 23, scheduler_advanced_tests 16 tests pass; hooks green
    (clang-format reformatted the new C++ once, then rebuilt and retested).
  - The scenarios README now documents the garages (format, example, vocabulary table).

  Round 13 (2026-10-23) changes:
  - 68: the page now computes the axis ranges itself (`fittedRanges` in app.js): the drawing's bounds,
    centred, with the narrower side widened to the plot area's aspect ratio, applied on draw and again
    after a resize (ResizeObserver, 50 ms debounce). `refit` calls `Plotly.Plots.resize` first because
    plotly only measures the container on window resizes; the stale size was why `constrain="domain"`
    left the drawing in the middle. The entry data carries `bounds`. Verified: x and y domains [0, 1]
    at 1160x457 and after the details pane changes height; the aspect of the ranges equals the area's.
  - 69: `Step.assets` became `Step.destination` (model.py) and step rows pass no asset keys unless the
    table asks for destinations; `stage_tables` asks only for the tray-assignment stage. Event rows
    highlight the agent only; job rows keep the tray, AGV and bay, not the destination stall. Verified:
    a schedule row lights no outline (ghost only); tray-assignment step rows carry `node:` keys.
  - 70: `code_notes/README.md` (index) and `code_notes/01-parity-references/notes.md`: the files under
    scheduler/test one by one, the anatomy of a stage test and of a jobs test, the layout YAML versus
    the garage state (`initial_conditions.yaml` is the simulator's placement, not the scheduler's),
    `vexen` = the `DiscreteVecsState[]` field (VECS = Volley EV Charging System, src/vecs/README.md),
    why the inline YAML fixtures stay (and what a file-fixture PR would look like), why outputs are
    recorded, and three open points (dead `DoubleRetrieveDodgeAgv` + its YAML, the duplicate
    `ReparkUnplugVecsMoveAgvFirst` reference, the unused `agv_command.id` replacement).
  - Facts checked for the notes: `DoTrayAssignments` / `DoAgvAssignments` are public; action GUIDs come
    from a process-wide counter (`CreateActionGuid`, utils.cpp:307), not a random source; the three
    planning files hold 23 + 33 + 4 inline states; `double_retrieve_garage_state.yaml` is used only by
    the commented-out `DoubleRetrieveDodgeAgv`.
  - README "Viewing" paragraph updated for the new highlight rules. Hooks green on the touched files
    (black, mypy, markdownlint). No C++ change this round, so no rebuild.

  Round 2 (2026-10-22) changes: `parity.hpp` API is now `Dag(ctx)`, `TrayAssignment` / `AgvAssignment`
  (scheduler, dag_before, ctx) and `ActionGraph(scheduler, request, response)` returning a `Reference`
  {stage folder, doc}; `ExpectReference(reference, suffix)` and `ExpectPlanReference(scheduler, request,
  now, suffix)` (plans twice, no lambda, no template). Stage call sites take `const auto dag_before_<stage>
  = parity::Dag(*ctx);` before the stage. The `.tray` / `.agv` suffixes are gone (the folder tells).
  The retrieve-fallback helper became `FullTinyLotRetrieveRequest(blocker_node)` returning the request.
  Reference sizes: tray_assignment 4 files / 318 lines, agv_assignment 9 / 706, action_graph 45 / 27,781
  (the `input.request` carries the whole base state). Recorded and compared again: scheduler 80 tests
  pass in a fresh process; planner_core and scheduler_advanced_tests were not re-run (no production code
  changed since their last green run). Hooks pass on every touched file (markdownlint, black, mypy
  included). The viewer was run in the container (`uv run python ...`, 58 references) and checked in
  the browser: navbar grouped by stage folder, layout graph with trays / AGVs / bays / disabled nodes,
  numbered move arrows in topological order, input and output text under the plot.
