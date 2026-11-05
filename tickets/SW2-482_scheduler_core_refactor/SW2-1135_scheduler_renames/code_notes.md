# Stage 2: the B2 renames (SW2-1135)

Status (2026-10-29): rebased onto main `5d5d7b39` (bay only; scheduler tree unchanged): `8576aa48`, `20884e57`,
`1ffabb36`, `4393c88c`, `a5ea1fcf` (#5 with groups 2-4, the BoolStringPair removal, optional
access and signatures), `400b521c` (#6), `2706dc55` (#7, group 5). Seven commits, tree clean.

| # | SHA | Commit | Made of (old SHAs) |
|---|---|---|---|
| 1 | `ecb5d9d8` | refactor: rename scheduler members and expansion methods | `ef6b0732` + clang-tidy config `52c78d0d` |
| 2 | `2e04696b` | refactor: rename ScheduleContext to PlanContext and its fields | `cac77ea0` |
| 3 | `d0a62a0a` | refactor: remove narration logging and condense comments | `43868463` + `2127d506` (TODO keys to come as fixups) |
| 4 | `7c8e6c84` | refactor: rename misleading methods and locals | `d606ab1b`, rebuilt without the dead-code deletions |
| 5 | `b8866c62` | refactor: delete dead code and simplify | `d0c50173` + std::tie `beb09aac` (groups 2-4 to come as fixups) |
| 6 | `400b521c` | refactor: give booleans an is_ prefix | item 190-191 renames |
| 7 | `2706dc55` | refactor: include the message headers each file uses | group 5, `scheduler_msgs.hpp` |

Seven commits at most (user, item 191); every edit belongs to one of them. Mapping of open work:
group 4 helpers and the dropped JobFailure / ExpandJob comments go to #5; every bool rename to #6,
including MakeFailedJob's `retain_job` > `is_retryable` (moved out of #5) and `lifted` > `is_lifted`
(#5 keeps `lifted`); JobFailure::is_retryable stays in #5, where the struct is born; group 6 (TODO
keys) is a fixup into #3; the `[ok, msg]` leftover in ReparkWaypointStashedTrays goes to #4. Split
at commit time: the #5 tree is the working tree with the renames reversed, built and tested on its
own before the amend; #6 is then the rest.

The sections below were written per old commit; their SHAs are the old ones in the right-hand column.

This document is rewritten after every change to the code, as `../SW2-1126_scenario_files/code_notes.md`
was: the commits as they stand, what each touched, how parity was checked, the review items and
their answers. Sections to fill:

## Commit 2: `refactor(scheduler): rename scheduler members and expansion methods`

Committed 2026-10-29 as `9eb12865`, rebased onto main `4c281d86` (a central_api change only) as
`cdd973f8`; amended 2026-10-29 (item 168) as `ef6b0732`: `cost_audit_` and `print_dags_` moved to the
private section (the trailing `public:` removed), body says so. 5 files, +216 / -206.

- Library: `include/scheduler/scheduler.hpp` (+22 / -24), `src/scheduler.cpp` (+175 / -161; the
  rest of the line count is clang-format reflowing lines the longer names pushed past 110 columns;
  both files were clang-format clean on main, so every reflow is on a renamed line).
- ROS node: `src/scheduler_ros.cpp` (2 lines).
- Tests: `test/src/stages/sanity_check_tests.cpp` (3 x `GetMotionGraph()`).
- Viewer: `tools/plan_viewer/records.py`, `JOB_METHODS` (job type to expanding method, shown on the
  page) follows the new names; its "(today's names)" remark dropped.

| Old | New |
|---|---|
| `gg_` | `motion_graph_` |
| `table_` | `collision_table_` |
| `GetGarageGraph()` | `GetMotionGraph()` |
| `pg_` (member) | temporary `volley::PoseGraph(layout_)` in the `motion_graph_` initialiser |
| `costaudit_` | `cost_audit_` |
| `printdags_` | `print_dags_` |
| `PrintDags()` | `TogglePrintDags()` |
| `Plan<Type>Job` (12), `PlanOpenBayDoor`, `PlanUnstashWaypointTraysJob` | `Expand...` |

- `pg_`: `GarageGraph(const PoseGraph&)` copies the layout pointer and builds its own Boost graph
  (`common_ros/src/garage_graph.cpp:9`), keeping no reference, so a temporary is safe. A constructor
  local cannot precede the member initialisers, hence the temporary. `#include
  <common_ros/pose_graph.hpp>` moved from `scheduler.hpp` to `scheduler.cpp` (include what you use).
- Not renamed, deliberately: `Plan()`, `PlanMotions()`; 16 error strings and 7 log lines that spell
  an old method name (rule 1 for the errors; the logs kept so each method's errors and logs carry
  the same prefix and the commit stays a pure rename); `GetCollisionTable()` (already matches); the
  ROS parameter `printdags`, the service `debug/printdags`, `SchedulerRos::debug_printdags_srv_`
  and the local `printdags` in `scheduler_ros.cpp` (external interface names);
  `docs/deprecated/{scheduler,tech-debt}.md` (outside the package, deprecated).
- Renamed by hand: comments naming the methods (`scheduler.hpp` the unstash doc,
  `scheduler.cpp` the bay-priority note, "After ExpandInsertJob() returns", the unstash snapshot).
- Mechanics: sed on `\bgg_\b` etc. (scheduler.cpp has no free function using those names) and on
  `\bPlan(<names>)\(`, so string literals (never followed by `(`) were untouched.
- Build 0 warnings. Parity: `volley-in-container test scheduler` 187 tests, 0 failures;
  `SCHEDULER_CHECK_RECORDINGS=1` the same, 187, 0 failures; `git status` clean under
  `test/scenarios/`. `prek run --files` on the five files: all passed. planner_core and
  scheduler_advanced_tests not run (rule 5: commits 3, 5, 8; the advanced tests use none of the
  renamed names and built green).

## Commit 3: `refactor(scheduler): rename ScheduleContext to PlanContext and its fields`

Committed 2026-10-29 as `4e58915b`, after review items 164 to 167. 10 files, +391 / -398
(estimate +300 / -280); split point not used.

- New `include/scheduler/plan_context.hpp` (57 lines; the class was 63 in `scheduler.hpp`): a
  `struct` (every member public), one-line purpose doc and no other comment (item 167).
  Includes what it uses; `*Msg` aliases kept (the library's convention; explicit `interfaces::msg`
  types are a possible clean-up). `scheduler.hpp` includes it (`"scheduler/plan_context.hpp"`).
- Renames: `ScheduleContext` to `PlanContext`, `ScheduleContextSPtr` to `PlanContextSPtr`; fields
  `events` to `event_dag`, `first_tray_event` to `first_event_by_tray`, `disabledness_filters` to
  `keep_out_filter_by_footprint`, `last_entity_event` to `last_event_by_asset`; methods
  `PushBackScheduledJob` to `AddScheduledJob`, `UpdateLastEntityEvent` to `AppendToAssetChain`,
  `UpdateLeafDependencies` to `OrderAfterJobLeaves` (it adds edges only, never the event).
- Deleted: the map aliases `CollistionFilterMap` / `GarageEntityEventMap` (nothing else used them);
  `request_id_str` (the 7 `PrintGraph` labels under `print_dags_` use `std::to_string(request_id)`;
  `request_id` itself was read nowhere else); `OrderAfterJobLeaves`' `job_index` parameter (all 7
  callers passed the index their event was built with, and no event's index ever changes; the
  method reads `event->GetJobIndex()`); redundant `volley::` qualifiers; the second `public:`.
- Bodies rewritten, same `AddDependency` calls in the same order: `AddScheduledJob` is
  `scheduled_jobs.emplace_back().job = job`; `AppendToAssetChain` binds `last_event_by_asset[asset]`
  once (an absent key gets a null entry that is overwritten at once, the same final map);
  `OrderAfterJobLeaves` iterates `GetLeafEvents()` directly (it returns a copy, so adding edges
  inside the loop is safe).
- Renames anchored on the accessor (`->events`, `ctx.events`), so the cost model's
  `Params().events` / `mc.events` are untouched. Tests: `SchedulerState.UpdateLastEntityEvent` became
  `SchedulerState.AppendToAssetChain` (no scenario file), its locals `last_event`. Test support:
  `scenarios::Dag` / `ExpectStage` take `const PlanContext&`; `stage.hpp` includes `plan_context.hpp`
  instead of `scheduler.hpp`. No scenario file changes.
- Kept: the `rclcpp::Time` constructor (the `Timepoint` one is a later PR).
- Namespace (items 172, 173; folded in by `amend!` + `rebase --autosquash origin/main`, same tree): `PlanContext` and `PlanContextSPtr` in `volley::scheduler`
  (`namespace volley::scheduler {`, closing comment to match, as the test code's
  `volley::scheduler::test`). `Scheduler` stays in `volley` (other packages use it), so its 64
  signatures and the one construction in `Plan()` say `scheduler::PlanContext[SPtr]`; that line became
  `const auto plan_ctx = std::make_shared<scheduler::PlanContext>(...)`. Tests unchanged: from
  `volley::scheduler::test` the unqualified name resolves through the enclosing namespace.
  scheduler.cpp names it through file-scope `using volley::scheduler::PlanContext;` and
  `using volley::scheduler::PlanContextSPtr;` (item 173); scheduler.hpp qualifies, pending the
  user's answer, then kept by the user (the whole Scheduler may move to `volley::scheduler` later).
- Build 0 warnings. scheduler 187 / 0 failures plain and with `SCHEDULER_CHECK_RECORDINGS=1`,
  `test/scenarios/` clean; planner_core 23 / 0; scheduler_advanced_tests 16 / 0. prek green on the
  10 files. clang-tidy over the new header (by hand; the hook skips headers): clean.
- Tidy (see review log item 163): the hook diffs `origin/main...HEAD`, so it ran on commit 2 only:
  7 findings. Over commits 2 and 3 with the working tree (clang-tidy-diff by hand): 36, of which 34
  `bugprone-unchecked-optional-access` on lines only renamed, 1 `bugprone-optional-value-conversion`
  (scheduler.cpp `GetVertexFromPose(...).value()` into an optional parameter, DoTrayAssignments), and
  2 `readability-identifier-naming` on the public `cost_audit_` / `print_dags_` (commit 2's names; a
  public member takes no trailing `_`). The pre-push hook checks `.cpp` files only, so it did not see
  the header ones; it also reported a missing-braces finding (`if(!edge_opt.has_value()) continue;`
  in GetJustMovingCost).

## Clean-up commits (B2-4)

### `chore(scheduler): turn off the unchecked-optional check for the package`

Committed 2026-10-29 as `720a378e`, replayed as `52c78d0d` by the fold-in rebase. +8 / -7.

- `src/planner/scheduler/.clang-tidy` (new): inherits the root config, `-bugprone-unchecked-
  optional-access`. Replaces `test/.clang-tidy` (deleted), which did the same for the tests only.
  Precedent: `src/agvhito/src/sm/.clang-tidy` (library code).
- Why: the pre-push hook and CI fail on any finding on a changed line; the renames touched 33 lines
  with an unchecked `value()` (rule 8 says record, not fix, and the team's convention is `value()`,
  which throws). Every C1/C2 move would hit the same.
- `DoTrayAssignments`: `const auto dest_vertex = motion_graph_.GetVertexFromPose(dest).value();` before
  the `BlockingTraySearchEnvironment`, instead of the inline `value()` that
  `bugprone-optional-value-conversion` flagged. Not dropped: the destination check accepts a pose whose
  reciprocal is a vertex, so this `value()` can throw (B12); passing the optional would change that.
- Tidy by hand over `origin/main` versus the working tree (the hook's command): 0 findings (was 34 in
  the hook at `4e58915b`: 33 unchecked, 1 conversion). Build 0 warnings; 187 / 0 both ways;
  scenarios clean; prek green.

### `refactor(scheduler): remove the planner's narration logging`

Committed 2026-10-29 as `43868463`. 3 files, +6 / -228. Item 161's policy, applied to all 129 log
statements of scheduler.cpp (inventory by a scratch parser that extracted each full statement with
its neighbours and flagged `.value()`, `++` and assignments in the arguments).

- Deleted (85): every INFO / DEBUG narration statement (plan request, per-job, stage names, event
  lists before and after each stage, critical path, blocking trays, freeing-move registrations,
  heading choices, the Debug-only trajectory dump), the per-attempt WARNs of the fallbacks ("Failed
  to find open space ...", "Failed to recursively resolve ...", "ResolveBlockingTrays selected garage
  pose"), and the empty-path diagnostic block of `GetJustMovingCost` (an unfiltered re-search, path
  and out-edge dumps). Blocks and loops that only logged went with them (the immobile / illegal pose
  dumps, the waypoint-stash note, three event-list loops, the AGV matching dump, an `else`), and the
  local `trajectories` that only fed the Debug dump. The topological-order checks beside the event
  dumps stay: they return "Failed to get new total ordering", a client-visible error.
- Side effects: 13 deleted statements called `.value()`; each reads a value checked or used just
  before (the tray id, `dest` after `if(!dest) return`, `best_charger`), a vertex a search returned,
  or a vertex of a topological order; one (`GetTray(immobile_tray).value()`) reads the root tray,
  which exists. None could throw where today's code would not.
- Kept (44): every ERROR; WARNs for what happened to a request (`Failed job`, invalid base state,
  rejected bay readiness ratio, rebalance of a bay failed, clean-garage unstash failed or a stashed
  tray skipped, ready-for-insert deferring a fill) and for inputs that should not occur (the AMIGA
  cost guards, `AddDepsAfterAmiga`, node not in layout, retrieval heading impossible, empty
  interval); the CHUGG cost-audit CSV (INFO, behind `cost_audit`, an operator feature; note
  `SchedulerParams::cost_audit` defaults to true). `scheduler_ros.cpp` and `scheduler_component.cpp`
  (node start-up, service wiring) untouched.
- Tests: `QuietLogging` sets the three loggers to ERROR (was WARN), so expected `Failed job` warnings
  stay out; doc comment and `test/scenarios/README.md` updated. Output: retrieve_job_tests and
  agv_assignment_tests print 0 log lines (were 62 and 8); the whole suite 5, all from
  `SchedulerState`, which builds its own Scheduler before `QuietLogging` runs (collision-table load,
  two expected rejected-ratio warnings).
- Build 0 warnings (one unused local caught and removed); 187 / 0 plain and with
  `SCHEDULER_CHECK_RECORDINGS=1`, no scenario YAML changed (the README is the only change under
  `test/scenarios/`); planner_core 23, advanced 16; prek green; tidy 0.

### `docs(scheduler): condense the library's comments`

Committed 2026-10-29 as `2127d506`. 6 files, +174 / -777. Comment lines: scheduler.cpp 606 to ~208,
scheduler.hpp 131 to 46, utils.cpp 100 to 26, utils.hpp 53 to 24, scheduler_ros.* 19 to 5.
Tests untouched (already cut in PR #1007); plan_context.hpp already done.

- Done by two subagents in parallel (scheduler.cpp; the headers, utils and ROS files), each owning
  its files, under the review rules: why only, a line or two; header docs only for a contract the
  signature does not state; no restating, banners, narrative or history; commented-out code
  deleted (the two `FIX: Does this break triple pick test?` blocks with dead `UsePreferredHeading`
  calls, the dead `// ctx->event_dag.Reduce();` at the end of DoTrayAssignments); the one-line
  `TODO(Gunther): Reduce here breaks ...` kept; every TODO line verbatim (the TODO commit handles
  them; one now refers to a deleted diagram, "the above case", and says "I'm just tired rn").
- Proof of comment-only: `g++ -fpreprocessed -dD -E -P` (strips comments, expands nothing) on HEAD
  and working tree, whitespace collapsed, compared: identical for all six files, after clang-format
  too. Negative test: HEAD~1 versus HEAD of scheduler.cpp reports a difference.
- Reviewed by hand: every added comment line read against the code. Changed two: the
  ExpandAgvMoveJob heading comment deleted (it described B13 as intended), the EV-demo line
  reworded to the original's meaning ("a script or config file was judged no better").
  `scheduler.hpp` still mixes `//` and `///` per declaration, as it did.
- A stale doc fixed: InsertVrcActionsIntoDag's said floor crossings only; it also handles
  same-floor visits. The `cost_audit` doc no longer names the removed `verbose` parameter.
- Build 0 warnings; 187 / 0 both ways; scenarios clean; prek green; tidy 0.

### `refactor(scheduler): delete dead code`

Committed 2026-10-29 as `d0c50173`. 4 files, +9 / -41. Survey group 1 (item 177).

- K1 `UsePreferredHeading`'s tray parameter (`(void)tray_opt`), declaration, definition and three
  callers: C1-2 (commit 4) no longer needs to drop it.
- K2 `assigned_events` in DoTrayAssignments: written, never read; the moved `event` is a local copy.
- K3 `blocking_tray_set.erase(...)` inside the move emission: both containers are cleared right
  after the loop and nothing reads the set in between. PROMPT section 10 put this in commit 7; done
  here, so commit 7 skips it.
- C24 `next_node` in the advance fallback: never read; its `.value()` cannot fail for a vertex of the
  search path.
- C9 the second `agvs_to_assign.size() == 0` check in DoAgvAssignments: the function returned
  already when it was empty, and the vector is only read afterwards.
- C7 `IsFloorTraversalAction` (utils.cpp/hpp): no caller in the workspace. C8 `DagToVec`: declared,
  never defined or called.
- C31 `cost_audit_` const (set once in the constructor), `print_dags_` not mutable (written only by
  TogglePrintDags and the friend SchedulerRos).
- Build 0 warnings; 187 / 0 both ways; scenarios clean; planner_core 23, advanced 16; prek green;
  tidy 0.

### `refactor(scheduler): rename misleading methods and locals`

Committed 2026-10-29 as `d606ab1b` (five rounds, 25 files, +788 / -776). Item 179's survey (N1-N12) plus the user's rule
(item 180): a method name starts with a verb unless it is an accessor named after its field.

- Methods: GetEventDag -> BuildAgvOrderDag; AgvMatchingEventDeps -> FindAgvsBlockingAssignedTray (round 2: FindAgvsAtPickupPose);
  AddDepsAfterAmiga -> OrderTransitionAroundAgvLifts; ResponseFromTrajectories -> BuildActionGraph
  (returns the action nodes; PROMPT's stage-H name BuildPlanResponse would mislead the same way);
  VrcFloorTransitDuration -> ComputeVrcFloorTransitDuration (utils.cpp, file-local). Kept: ToActionNode
  (conversion), MotionScheduleOrder (a comparator type), SanityCheckEvents, Do*Assignments, the
  Use*Heading / AssignTrayIdForEmptyMove / FindOpenSpaceForRootTray / TryFindBlockingTrayResolution
  that C1 renames.
- Locals and parameters: event_map -> matching, agv_event_dag -> agv_order_dag,
  event_occupied_durations -> event_earliest_starts, adjusted_cost -> agv_wait; the second loop of
  OrderTransitionAroundAgvLifts dependency/dependency_event/tray_dependent(_event) -> dependent /
  dependent_event / tray_dependency(_event) (they were inverted); Plan(): plan_ctx -> ctx, message2 ->
  response_message, final_trajectories(_opt) -> final_state(_opt), schedule_opt -> action_nodes_opt;
  dst (2 sites), dst_opt, dstpose, garagepose -> dest_pose / dest_opt; inbound_heading_or,
  retrieval_angle_or, retrieval_heading_or -> *_opt; WithPriorDests -> with_prior_dests;
  open_space_result -> target; tray_event_id replaced by tray_id (same scope, same value, neither
  reassigned in between; the block's braces dropped).
- Shadowing: inner `[success, message]` bindings renamed for what they call (repark_ok, charge_ok,
  clear_ok, insert_ok, retrieve_ok and their messages), `dest_vecs_opt`, `reciprocal_vertex_opt`
  (renamed, not std::tie, so the outer variables are never overwritten).
- Method: a script rewrote identifiers outside string literals only (regex on `"..."` spans), with
  Plan's locals confined to Plan's body; collisions checked first (`target` at 1783 is a comment,
  `dest_pose` at 825 another function). Strings kept: "ResponseFromTrajectories failed  " (client)
  and the two "AddDepsAfterAmiga got ..." WARNs. Viewer: reader.py's stage list follows.
- Not changeable here: scheduler_advanced_tests test06 comments name ResponseFromTrajectories (rule 2).
- Round 2 (item 181): every local and parameter reviewed. 433 names extracted by a scratch script
  (declarations, bindings, range-for variables) and judged one by one; 66 renamed: VECS locals to
  `ev_charger_*` (stage A's word for a VECS in the test data), FindAgvsBlockingAssignedTray ->
  FindAgvsAtPickupPose with source -> pickup_pose, fixed/queried_* -> agv/other_*, conflicting_agvs /
  dependencies -> agvs_at_pickup, event_ptr -> assigned_event_opt, res -> added; dep_* ->
  dependent_*; event_dep_cost -> child_earliest_start; feasible_ignoring -> is_feasible_ignoring;
  abbreviations spelled out (cmd, cand_*, curr*, traj, pl/pw/ph, mc, e, path_i, *_idx, vert ->
  vertex, topo -> ordering, idx -> position); `*_msg` strings -> `*_message` (Msg marks ROS types);
  `*_success` flags -> `*_ok`; printdags -> print_dags. Kept: i, j, it, id, _, err, the src/dst pairs
  in utils.cpp (they mirror agv_command.src/dst), event_and_id (group 2 deletes it), the exception
  `e` in scheduler_component.cpp.
- Safety: the renamer skipped string literals and anything after `.` or `->` (fields such as
  `.vert`, `->vecs_command`); a per-function check (functions split at column-0 `}`) found no
  rename whose target name already occurs in the same function, so nothing can be rebound by
  shadowing; every string literal in the 7 C++ files is identical to HEAD (compared as lists).
- Round 3 (item 182): the user found `delta` and `result` unclear; every declaration of a generic name
  (result, delta, source, solution, best, path, node, command, filters, msg, ...) re-read in context,
  renamed per function: delta -> garage_event_opt (it is the optional DiscreteGarageEventMsg a motion
  causes; none for a wait); result -> action_node (ToActionNode), response (Plan), open_space
  (FindOpenSpaceForRootTray), root_target (DoTrayAssignments); path -> root_path; search start
  `source`/`tray_source` -> start_state; bare `solution` -> search_solution; best -> target; node ->
  charge_node / tray_node / base_node / action_node; BayCommandMsg `command` -> bay_command;
  filters -> path_filter (one GraphFilterProperties; params of the pathing cost functions follow); msg
  -> error_message; running -> running_seconds; assignment -> assignment_opt; duration(_opt) ->
  travel_duration(_opt); cost -> move_cost; utils `events` -> event_durations; BuildAgvOrderDag's
  `dag` -> order_dag. Kept: entry in BuildAgvOrderDag (structured bindings, next commit).
- Mistakes caught and fixed in round 3: the renamer also rewrote English words in comments (rounds 2
  and 3: "critical path", "dependencies", "node", "source", "running total", "cost functions",
  "assignment"), including TODO lines; all restored by hand from the HEAD text, and the TODO lines
  verified identical to HEAD. It also rewrote `volley::cost::SecondsF` (a namespace after `::`) to
  `move_cost::`; the build failed and the qualifier was restored. Comment mentions of renamed
  parameters (`agv_order_dag`, `after_position`, `position` in `ordering`) follow on purpose.
- Round 4 (item 183): every function described from its body by a read-only subagent (what it
  returns, mutates, adds to the DAG), checked by hand where a rename depends on it; 21 renamed:
  OrderAfterJobLeaves -> OrderAfterJobLeafEvents ("Leaves" read as a verb); ExpandOpenBayDoor ->
  AddBayTransitionToRetrieve (it issues TRANSITION_TO_RETRIEVE, not a door command, and is a helper,
  not a job type); ExpandUnstashWaypointTraysJob -> ReparkWaypointStashedTrays (a step of CLEAN_GARAGE);
  Use*Heading -> Apply*Heading; FindOpenSpaceForRootTray -> FindDestinationForRootTray (the target may
  still hold blockers); TryFindBlockingTrayResolution -> FindBlockingTrayResolution;
  ApplyTransitionToFreeingMoves -> ApplyTransitionAndRegisterOccupant; AssignDestForUntargetedMove ->
  AssignDestAndUnblockingMoves; AddNodeArrivalDeps -> OrderArrivalAfterPriorOccupant (adds at most
  one edge and updates the occupancy map); MoveAgvToTrayPose -> AppendAgvMoveToTrayEvent;
  GetJustMovingCost -> ComputeTravelDuration; GetAgvCurrentPoseToTrayMoveCost ->
  ComputeAgvPickupDuration; GetAgvOccupiedDuration -> ComputeAgvOccupiedDuration;
  GetAgvToTrayAssignmentCost -> ComputeAgvAssignmentCost; TryClearBlockedAgvMove ->
  GateAgvMoveOnBlockerDeparture (it only adds an ordering edge; true iff it did);
  EnsureAgvMovePathsClear -> RepairAgvMovePaths (capped, so "Ensure" overpromised); IsMovePossible ->
  CheckMovePossible (returns a pair, not a bool); FailJob -> MakeFailedJob (builds the record, changes
  nothing); ReadParams -> ReadMotionCostParams. Kept with reason: ValidateBaseState,
  ComputeBayRebalancingActions, SanityCheckEvents, BuildActionGraph, GetVersionInfo,
  GetSchedulerReport, ExpandReparkTrayJob and the other Expand*Job, FindAgvsAtPickupPose.
  Open for the user: DoTrayAssignments, DoAgvAssignments (named in the authored descriptions of 14
  scenario YAML files and the scenarios README) and ResolveBlockingTrays (named in comments in
  scheduler_advanced_tests and system_tests). Stale outside the package: scheduler_advanced_tests
  test05/test07 comments name MoveAgvToTrayPose / EnsureAgvMovePathsClear (rule 2: not edited).
- Totals for the commit: 10 files, +748 / -736 (all four rounds). Build 0 warnings; 187 / 0 both ways; scenarios
  clean; planner_core 23, advanced 16; prek green; tidy 0 (merge-base diff; origin/main moved to
  `5d5d7b39`, a bay-only merge). The last change before posting was clang-format on a line the
  namespace fix shortened; rebuilt, tests not re-run for that formatting-only change.
- Build 0 warnings; 187 / 0 both ways; scenarios clean; planner_core 23, advanced 16; prek green;
  tidy 0.

- Round 5 (item 184): DoTrayAssignments -> AssignTrays, DoAgvAssignments -> AssignAgvs (the names the
  solvers keep: the module folders are tray_assignment / agv_assignment and PROMPT's commit 8 adds
  `Scheduler::AssignTrays` as the solver adapter, which is now this method). The 13 stage scenario
  YAML files change only in `description` (checked by loading old and new YAML and comparing every
  key); recordings identical; the scenarios README and the plan viewer's labels follow. Error
  strings that spell DoTrayAssignments / DoAgvAssignments stay.

### `refactor(scheduler): replace std::tie with if-scoped structured bindings`

Prepared 2026-10-29, unstaged. 1 file, +27 / -43 (item 182).

- The 12 `std::tie(success, message) = X(...)` sites (Plan, ExpandRetrieveJob, ExpandInsertJob,
  ExpandReadyForInsertJob, ExpandReadyForRetrieveJob, ExpandAgvChargeJob, ExpandChargePayloadJob)
  become `if(const auto [success, message] = X(...); !success)`; the first binding of each of those
  functions (the DAG Apply, AssignTrays in Plan) moves into an if the same way, so no binding shadows
  another; ExpandInsertJob's pre-declared `bool success; std::string message;` deleted.
- Checked first: after each check nothing reads the outer pair (every use listed per function).
  SanityCheckEvents' failure: the prefixed text is built once into `response.message` and passed to
  MakeFailedJob, the same string as before. ExpandAgvChargeJob keeps its combined condition
  (`!success || !trapping_bay_opt.has_value()`) and returns the pair. The job-dispatch bindings in
  Plan's switch already sit in their own case scopes: unchanged.
- Kept: `std::tie(dest, repark_moves)` twice in AssignTrays (outer `dest` read after the loop).
- Build 0 warnings; 187 / 0 both ways; scenarios clean; planner_core 23, advanced 16; prek green;
  strings identical; tidy 0.

### Group 2 (small idioms), amended into #5

Amended 2026-10-29: #5 is `d8720537`. 3 files, +67 / -119.

- C5 ResolveBlockingTrays: four `std::make_pair(std::nullopt, std::vector<...>{})` -> `return {};`.
- C14 ExpandReparkTrayJob: the two `if(tray_move->GetDest())` blocks merged; bay edge still before the
  charger edge; one `find` each. C15: five more find-then-`[]` (AppendAgvLiftEvent,
  AppendAgvMoveToTrayEvent twice, AssignAgvs twice) use the iterator. The four in the tray emission
  code are left for commit 7 of the next stage (one helper there).
- C16: `ApplyPreferredHeading(dest.value(), ...)` instead of copy, apply, copy back (2 sites).
- C17 FindAgvsAtPickupPose: no copy of the AGV map; this AGV's collision id computed once (it exists:
  matched AGVs come from the state's AGVs); the other AGV's id and pose from the loop variable.
- C19: `const auto& matching = assignment_opt.value().first;` (no map copy, unused threshold gone).
- C20: OrderTransitionAroundAgvLifts called in each branch; the staging optional pair gone.
- C21: ApplyRetrievalHeading uses `std::ranges::none_of`; AssignAgvs' "no tray moves" scan uses
  `std::none_of` (same order, same short-circuit). AssignTrays' `is_blocking` loop left: commit 6
  extracts that block.
- C22 ClassifyBay: the unreachable `else` gone (one ternary). C23 rebalancing: the map by const
  reference (never mutated), redundant empty-vector assignments gone, `contains`, `views::reverse`.
- C28 PropagateEventCostToChildren: `map[key]` zero-initialises a chrono duration, so the explicit
  insert goes; `std::max` for the child's earliest start.
- C29: no `std::move` on the GetDisabledEntitiesFilters prvalue; `const auto&` for the final state;
  action nodes moved out of the optional. C13: no `std::move` into Replace (const ref).
- C30: ReparkWaypointStashedTrays' early return equal to the fall-through and the trailing
  `continue`s gone; FindAgvDepartureFromNode compares the optional directly; ExpandRetrieveJob reuses
  `tray` (no state change in between); SetBayReadinessRatioCallback computes `changed` once (atomic
  still read before the write), its stale "publish" comment gone.
- Includes: `<algorithm>` in scheduler.cpp, `<ranges>` in utils.cpp.
- Build 0 warnings; 187 / 0 both ways; scenarios clean; planner_core 23, advanced 16; prek green;
  string literals the same set (one redundant `""` return removed); tidy 0.
- Left for later: a `[ok, msg]` binding in ReparkWaypointStashedTrays still uses `msg` (naming, #4).

### Group 3 (Plan() duplication), amended into #5 as `037b5c29`

Prepared 2026-10-29, unstaged. 2 files, +68 / -141.

- New private `ExpandJob(ctx, job)` returns `stdx::Expected<void, scheduler::JobFailure>` (item 188:
  no tuples; `JobFailure {message, retain_job}` in scheduler.hpp, `volley::scheduler`), as does
  `ExpandRetrieveJob`, whose tuple it replaces: the 12-case switch moved out of Plan() as returns;
  pair-returning expansions go through `to_expected` with retain_job false (MakeFailedJob's default
  before); `job_index` is still `ctx->scheduled_jobs.size()` at expansion; the unknown-type message
  unchanged. Plan(): on success AddScheduledJob, else MakeFailedJob(job, message, retain_job) and, for
  INSERT, clean_garage_request_fn_ after it, as before.
- The five stage failures (tray, AGV, sanity, CHUGG, action graph) share `fail_all_jobs(response
  message, job message)`: same strings as before (tray and AGV keep the unprefixed message for jobs,
  the other three the full text for both); the lambda returns a copy of the response.
- Strings: the same set; "ResponseFromTrajectories failed  ", the CHUGG text and `""` now each once
  fewer. `<tuple>` include dropped from scheduler.hpp (no use left).
- Coverage: 9 plan scenarios record expansion failures (including retain_job through
  retrieve_job/FromUnavailableCharger) and compare equal; no plan scenario reaches the five stage
  failures, so their equivalence rests on reading the code.
- Build 0 warnings; 187 / 0 both ways; scenarios clean; planner_core 23, advanced 16; prek green;
  tidy 0.

## Questions and answers

## PR review feedback

One subsection per item, as in stage A: the finding, the assessment (right or not, and why), what
changed, how it was verified, which commit it was amended into.

### Group 4 (small helpers outside the tray code), amended into #5 as `8d3d2398`

Prepared 2026-10-29, unstaged. 3 files, +109 / -129.

- C25 `UnplugEvChargerBeforeTrayMove(ctx, ev_charger, job_index)` (file-local; the tests' word,
  `UnplugsCharger`; was StopVecsForTrayDeparture, item 190): the charging-VECS stop event
  ExpandRetrieveJob and ExpandReparkTrayJob each built; false for a VECS state the tray cannot leave,
  and each caller keeps its own failure text (retrieve stays retryable).
- C26 `IsLiftedMotion(motion)` (ToActionNode's src/dst lift, the freeing-moves occupancy; `lifted`
  local now `is_lifted`) and `FindAgvLiftChange(event, agv_id)`, the AGV's lift change or nullptr (the
  two checks in OrderTransitionAroundAgvLifts; no bool argument).
- C27 `ComputeAgvLiftDuration(is_raising)`: AppendAgvLiftEvent, ComputeAgvAssignmentCost and the
  non-tray roots in AssignAgvs (now `std::get_if`).
- C11 the AGV path filter is built once per assignment round in AssignAgvs (was per event-AGV pair)
  and once before the charger loop in ExpandAgvChargeJob (was per charger); GetStaticFilter reads only
  its arguments, none of which change inside those loops.
- C10 AppendAgvMoveToTrayEvent finds the AGV vertex with `std::find_if`; the always-true
  `!= end` check after the throw is gone.
- C12 InsertVrcActionsIntoDag: `make_vrc_move_action(from, to)` and `order_after_last_vrc_action`
  lambdas replace the two copies of the VRC command builder and the cycle-guarded edge; action GUIDs
  are still created in the same order.
- Strings: the same set; `"VrcCommand"` once fewer. prek green, tidy 0.
- Item 190: no new comments. JobFailure, ExpandJob and ComputeAgvLiftDuration lost theirs; the
  IsLiftedMotion and VRC-edge comments are the old ones, moved. One `/*is_raising=*/true` label left.

### Bool renames (items 190-191), commit #6 `e7fbfaee`

`is_` prefix for every bool the package names (src, include, ROS node, three test files):
enforce_retrieval_heading > is_retrieval_heading_enforced, allow_waypoint_stash >
is_waypoint_stash_allowed, allow_recip > is_reciprocal_allowed, AppendAgvLiftEvent's raised >
is_raising, print_dags_ > is_dag_printing_enabled_ (and the ROS local), cost_audit_ >
is_cost_audit_enabled_ and SchedulerParams::cost_audit > is_cost_audit_enabled (ROS parameter
`scheduler.cost_audit` unchanged), applied_any_non_tray > is_non_tray_event_applied, agv_loaded >
is_agv_loaded, added > is_dependency_added, changed > is_ratio_changed (scheduler and ROS node),
tray_in_bay / payload_in_bay (bools in utils) > is_tray_in_bay / is_payload_in_bay,
occupied_indefinitely > is_occupied_indefinitely, cross_floor > is_cross_floor. The optional
`tray_in_bay` in ExpandRetrieveJob and the message fields (`.raised`, `retain_job`) keep their
names; `added`/`changed` renamed in code only (three comments use the words). Test bools too (item 191):
found_unstash_move, agv_lowered, agv_lifted, agv_command / bay_command (retrieve test locals),
unplugs > is_unplug_expected, stopped_charging > is_charging_stopped, found_agv_move_lift,
scalars_only > is_scalar_only, more_expected / more_actual > is_expected_line_read /
is_actual_line_read, kQuiet > kIsQuiet, the bay test structs' disabled / loaded. `has_` names kept.
Group 4 + renames: 16 files, +237 / -256. Build 0 warnings, 187 both ways, scenarios clean,
planner_core 23, advanced 16, prek green, tidy 0, literals unchanged but one "VrcCommand".

Split (item 192): the #5 tree was the full tree with the renames reversed (MakeFailedJob's
parameter back to `retain_job`, `lifted` kept); built, 187 with recordings, planner_core 23,
advanced 16, prek green; amended. #6 restored the saved full tree (byte-identical, tested before
the split); every added line carries an `is_` name.

### Group 5 (message headers), commit #7, unstaged

`scheduler_msgs.hpp` deleted. Its 34 global aliases were also defined in common_ros_msgs.hpp,
planner_core_msgs.hpp and motion_planner_msgs.hpp, so deleting the header alone would leave them in
reach: every `*Msg` / `*Srv` alias the scheduler package and scheduler_advanced_tests use is now
`interfaces::msg::X` / `interfaces::srv::X` / `std_srvs::srv::Trigger` (TrayPoseChangedMsg >
TrayPoseSetManually), and each touched file includes the headers of the types it names (header
names by the rosidl snake-case rule, each checked in the install tree). Outside the package:
agvhito_tools' move_planner.cpp included the header directly; it now includes plan_request.hpp and
uses its own `imsg::` alias. Reverse dependencies of scheduler: agvhito_tools and
scheduler_advanced_tests only. 16 files (one deleted), +465 / -416 before the move_planner tweak.
Build of the three packages 0 warnings; 187 both ways, scenarios clean; planner_core 23, advanced
16; prek green; tidy 0; literals unchanged but the two removed include lines.

### BoolStringPair removal (item 193), unstaged on top of #6; group 5 set aside

Group 5 saved (patch and file copies in the session scratchpad, group5/) and re-generated later by
its script; the tree went back to #6 so this change reviews alone. Every BoolStringPair in the
package is gone (22 Scheduler methods): the ten Expand*Job methods return
`stdx::Expected<void, scheduler::JobFailure>` like ExpandRetrieveJob, so ExpandJob's switch returns
them directly (the `to_expected` wrapper is deleted); the twelve helpers and stages return
`stdx::Result`. ValidateBaseState (a pair of optional state and message) returns
`stdx::Expected<volley::DiscreteGarageState>`. All of them and ExpandJob / ExpandRetrieveJob are
`[[nodiscard]]` (team rule; no call ignored a result, the build has no warnings). Call sites bind
one named result (tray_assignment, tray_repark, retrieve_transition, arrival_order, ...) instead of
`[ok, message]`; this removes the `[ok, msg]` leftover in ReparkWaypointStashedTrays. Where an
expansion passes on another expansion's failure unchanged it returns `Unexpected(x.error())`
(is_retryable kept; only ExpandRetrieveJob sets it and nothing calls it, so no change); a prefixed
message builds a new JobFailure. ExpandAgvChargeJob returns the AGV-move result as is. Tests: stage
and sanity tests check the result (`EXPECT_TRUE(r) << r.error()`; other lines stop streaming the
empty success message). Not changed: `Apply()` of planner_core / common_ros still returns
BoolStringPair (20 bindings in scheduler.cpp); other pairs: CalculateDesiredBaySplit,
ComputeBayRebalancingActions, AgvAssignmentEdgeKey, BlockingTrayResolution::prereq_moves.
8 files, +431 / -418. Build 0 warnings, 187 both ways, scenarios clean, planner_core 23, advanced
16, prek green, tidy 0; literals: only 26 `""` success messages gone.
Commit: proposed as part of #5 (it replaces #5's wrapper). Mechanics: #5' = this tree with the bool
renames reversed; check that the forward rename scripts on #5' give this tree byte for byte; rebase
with `edit` on #5, amend #5', resolve #6 by writing the regenerated files; then re-run group 5's
script for #7.

### Fold-in of the BoolStringPair removal (item 194)

Done 2026-10-29. split56.py (scratchpad) reverses #6's renames by name (scoped: AppendAgvLiftEvent's
raised, MakeFailedJob's retain_job, ComputeTravelDuration's and AssignAgvs' agv_loaded). Check:
format(reverse(old #6)) == old #5 byte for byte, so format(reverse(final)) is the final tree
without the renames. That tree differed from old #5 in exactly the 8 conversion files (+431/-418),
built, 187 with recordings, planner_core 23, advanced 16, prek green. Rebase -i with `edit` on #5
and #6 dropped from the todo; amended #5 (message: "binds its own result", new BoolStringPair
paragraph), committed the saved final tree as #6, continued. Branch tree == tested final tree.
Group 5 re-run by qualify_msgs.py: identical to the earlier version in every file the conversion did
not touch; 3 packages build, 187 both ways, planner_core 23, advanced 16, prek, tidy 0.

### Remaining objectives (user, item 194)

1. agvhito_tools without scheduler: MovePlanner (agvctl CLI, no ROS node) builds a Scheduler and calls
   Plan() for one MOVE_AGV job in a garage holding only that AGV, then keeps the AGV commands
   (fails on any VRC command). Options: (a) plan with motion_planner directly (GarageGraph,
   CollisionTable, edge durations + all-pairs heuristics, one AgvMove event in a ScheduleEventDag,
   Chugg::SolveSequential, non-idle motions to AgvCommands, refuse VRC nodes); package deps become
   motion_planner / planner_core / common_ros / cost_functions; verify with a throwaway harness that
   compares old and new commands over many src/dst pairs on the test layouts. (b) call the scheduler
   node's `plan` service: needs a ROS node in agvctl and a running scheduler. Recommended (a).
2. std::optional access: 21 `.value().` / `.value()->` member accesses vs 97 `->`; rule: `->` when
   the optional is checked in scope or already accessed with `->`; an unchecked `.value()` that is
   the only guard stays (throws instead of UB).
3. Signatures over 5 parameters: AppendAgvMoveToTrayEvent 11, FindDestinationForRootTray 8,
   FindBlockingTrayResolution 8, CheckMovePossible 7, AppendAgvLiftEvent 7,
   OrderArrivalAfterPriorOccupant 6, AssignDestAndUnblockingMoves 6 (six more at 5). Plan: an AGV
   assignment state struct (working state, last AGV event, last move-to-tray event, node occupants)
   owned by AssignAgvs, cost returned instead of an out-parameter; request structs for the tray
   destination searches (as C1's ResolveRequest).
Buckets: 2 and 3 into #5 (same set-aside / fold / regenerate machinery); 1 with #7.

### Objectives 2 and 3 (item 195), unstaged on top of #6; group 5 set aside again (group5b/)

User: skip agvhito_tools (keep its scheduler dependency); do optional access and signatures.

- std::optional: the 20 member accesses through `.value().` / `.value()->` on a named optional
  become `->` (18 in scheduler.cpp, 6 hits in utils.cpp incl. both sides of two comparisons, one in
  tray_assignment_tests after its ASSERT); every one is checked first (has_value / `!opt` return /
  ternary / ASSERT). `audit.value()` is CostVector, not an optional. `.value()` on a call result
  (the throwing guard) stays.
- Signatures: no method over 5 parameters (was 7 over, 6 at 5; now 10 at 5).
  - `AgvAssignmentState` {working_state, last_agv_event, last_move_to_tray_event,
    current_node_occupant} owned by AssignAgvs; AppendAgvMoveToTrayEvent(ctx, state, agv_id,
    root_event, agv_order_dag) and AppendAgvLiftEvent(ctx, state, agv_id, is_raising, job_index)
    return their duration (`stdx::Expected<Duration>`) instead of adding to `event_cost`; the move
    reads the AGV and tray from the state (same values the caller passed: nothing changes the state
    in between); OrderArrivalAfterPriorOccupant(ctx, state, dest_node_id, arriving_agv_id,
    new_event).
  - `TrayAssignmentState` {working_state, last_tray_event, freeing_moves} owned by AssignTrays;
    AssignDestAndUnblockingMoves(ctx, state, event) (move from the event) and
    ApplyTransitionAndRegisterOccupant(state, event).
  - `ResolveRequest` {tray_id, immobile_trays, illegal_poses, is_retrieval_heading_enforced,
    is_waypoint_stash_allowed} (C1's shape): ResolveBlockingTrays(base_state, request, job_index);
    FindDestinationForRootTray(working_state, request, collision_entity) runs both tiers itself (as
    FindBlockingTrayResolution does); FindBlockingTrayResolution(working_state, root_request,
    blocking_tray_id, blocking_tray_illegal_poses, job_index). The AGV-id set and the movable-tray
    filter both searches built are one member, BuildImmobileTrayFilter (AGV ids cannot change with
    tray moves, so building it per search gives the same set).
  - `CandidateMove` {collision_id, agv_id, tray_id (optional), start_pose, dest}:
    CheckMovePossible(ctx, working_state, move).
  - Two existing comments moved onto the struct fields they describe; no new comments. Struct
    members default-initialized where callers leave them out (-Wmissing-field-initializers,
    cppcoreguidelines-pro-type-member-init).
  - SearchSolution holds no reference to its environment (path_search.hpp), so building the
    environment in a lambda (as FindBlockingTrayResolution already did) is safe.
- Not done: ResolveBlockingTrays still returns a pair (C1's BlockingResolution); the 10 methods at 5.
- 4 files, +321 / -307. Build 0 warnings, 187 both ways, scenarios clean, planner_core 23, advanced
  16, prek green, tidy 0, literals unchanged.
- Commit: into #5 by the same machinery as item 194 (reverse #6 renames, check reverse(#6) == #5,
  rebase edit #5, re-commit #6, regenerate #7 from its script).

### Fold-in of objectives 2 and 3 (item 196)

Done 2026-10-29 as in item 194: format(reverse(old #6 `a4a12fc0`)) == old #5 `c6478ebb`; new #5
tree = format(reverse(final)) differs from old #5 in exactly the 4 objective files (+320/-307; the
only `is_` token on added lines is the existing `is_recip`); ResolveRequest there has
enforce_retrieval_heading / allow_waypoint_stash (renamed in #6). Built, 187 with recordings,
planner_core 23, advanced 16, prek. Rebase: amended #5 `ff9e0677` (new paragraph), committed the
saved final tree as #6 `b9ee836b` (message: "parameters and request fields"); branch tree == tested
final tree. Group 5 regenerated: identical to group5b/ except the three objective files.
#7 (unstaged, 16 files incl. the deleted header, +456 / -409): 3 packages build 0 warnings, 187 both
ways, scenarios clean, planner_core 23, advanced 16, prek green, tidy 0, no `scheduler_msgs` left.

### TODO review (item 198), recommendation only, nothing changed

25 markers (scheduler.cpp 23, scheduler.hpp 1, scheduler_advanced_scenario_test04.cpp 1), at HEAD
`0c2f1dc1` line numbers.
Remove, done or obsolete: 543 failed-jobs output (Plan already records each failed expansion);
1368 charger conflicts (AGV-on-node skip, path filter blocks trays/AGVs, keep-out filter disabled
nodes); 3153 re-add Reduce + commented call (Plan calls Reduce right after AssignAgvs); 2521
"Isabel's magic function" (TRAY id is deliberate, matches ApplyTransitionAndRegisterOccupant);
622 any-AGV move (unreachable: both callers pass a uint16, the optional is always set; drop the
branch and make the parameter uint16_t); 1611 DGS member.
Remove, vague: 288 bay transitions (event deps carried by TransferEventDagDepsToActionDag;
`lifted` only matters for tray entities); 3357 CHUGG diagnostics; 1799 lift transitions "when they
exist" (no such event type; VRC is action-level).
Remove, ideas for the backlog: 1745 park on occupied node, 1844 empty-tray choice by future paths,
2393 recompute critical path, 2546 collapse move chains.
Merge: 2556 into 512 (Reduce ordering); 2888, 3047, scheduler.hpp:199 into 2615
(ComputeAgvOccupiedDuration stub).
Keep, need ticket keys: 3461 failed job's partial events stay in the DAG (bug); 2431 unblocking
move Apply result ignored (drop the commented-out code); 2310 critical-path fallback (reword);
559 retrieve without PROCESS_RETRIEVE still EXECUTING (bug); 512 Reduce ordering; 2615 AGV
availability; 1783 ApplyPreferredHeading not applied to blocking-tray moves.
Test: test04 lines 14-248 two commented-out tests (keyboard noise; charge jobs covered by
plan/agv_charge_job/*) -> delete.
Buckets: comment removals and rewordings -> #3; dead code (622 branch, 3153 commented Reduce, 2431
commented block, test04 block) -> #5.

### TODO edits applied (item 199)

User: apply, comments into #3, dead code into #5, the seven kept as TODO(any). Commented-out code is
comment text, so it went to #3 with the rest (Reduce calls, the disabled Apply check, test04's two
disabled tests); #5 got the one code change: ExpandAgvMoveJob takes a plain uint16_t agv id and
its unreachable unassigned-AGV branch is gone. todo_edits.py (scratchpad) applies the edits by
pattern to any commit's text (the NOTE/TODO block and the FIX line name methods that #4 renamed).
Rebuilt by script, no cherry-picks: rebase -i stopping at #3; each later commit written as its old
tree with the three edited files replaced, formatted and committed with its old message (#5 with
a new bullet). Checks: #3 and #4 differ from the old ones only in comments (g++ -fpreprocessed);
#5 built and tested (187 with recordings, planner_core 23, advanced 16); #6's diff equals the old
one except the ExpandAgvMoveJob signature; #7 built (3 packages), 187 both ways, planner_core 23,
advanced 16; tidy 0. Commits: #3 `1ffabb36`, #4 `4393c88c`, #5 `a5ea1fcf`, #6 `400b521c`, #7
`2706dc55`. Final tree vs old #7: 3 files, +22 / -317. Seven TODO(any) left in scheduler.cpp.

### Commit 8 (proposed): the event DAG API (item 200), unstaged on `2706dc55`

User: review event_dag.hpp (naming, unused API) for scheduler readability; a new commit.
Users of event_dag.hpp: scheduler, motion_planner (CHUGG), planner_core tests; dependents of
planner_core: motion_planner, scheduler, scheduler_advanced_tests, agvhito_tools.
- `DagBase<T>` > `Dag<T>` (used directly for action and AGV-order DAGs); `DagT` > `Graph`, `dag_` >
  `graph_`, `ptr_to_vertex_` > `vertex_by_node_`, `ptr` params > `node`; abbreviated locals spelled
  out (Reduce, WouldCreateCycle, topological ordering, Remove).
- `GetFromVertex` > `GetNode`; `GetEventFromVertex` > `GetEvent`; both return the node and throw
  std::invalid_argument for a missing vertex (as GetInEdges/GetOutEdges), instead of an optional
  every caller `.value()`'d (29 `.value()` gone; three defensive checks on vertices from the same DAG
  removed, incl. the unreachable "Couldn't get event from vertex" in SanityCheckEvents).
- Deleted, unused: RemoveVertex, AddDependent, DrawGraph, Replace(vertex, node), HasEvent (tests use
  Has), GetVertexFromEvent (GetVertex), VertexVec (std::vector<Vertex>), the `to_str` overloads
  (private static DotLabel; ToDotFormatString private, its unused left_right parameter gone),
  commented-out code, `<stdio.h>` and the file-level NOLINT lines that did nothing, unused includes
  (boost/function, transitive_reduction, roslog), the "thx clang"/"Thanks boost" notes.
- `Reduce()` > `RemoveRedundantEdges()` (transitive reduction), void: no caller used its
  {true, "Success"}; a test that did now just calls it.
- `ScheduleEventDag::Apply` returns stdx::Result; the scheduler's 13 call sites bind one result
  (`applied`) in an if-initializer. planner_core now depends on stdx (package.xml).
- Scheduler call sites walk GetParents / GetChildren (now used) instead of edges and boost's
  `m_source` / `m_target` (6 loops + 1 test), GetTargetVertex where the vertex is needed. Two of
  those loops added edges into the list they iterated; the added edges are AGV moves the loops skip,
  so the snapshot gives the same result without the invalidation risk.
- Kept as is: GetVertices / GetInEdges / GetOutEdges still return iterator pairs, like GarageGraph's.
- Error strings: unchanged except DrawGraph's / to_str's labels and the unreachable one.

### Semantic scan (item 201), recommendation only

- DAG `Apply(state)`: applies every event, in dependency order, to a caller's state (always a copy of
  the initial state). Proposed `ApplyEventsTo(state)`; "Replay" suggests re-running recorded
  history, these are planned events. Per event, `ScheduleEvent::Apply` -> `ApplyTo(state)`
  (5 overrides; scheduler, motion_planner, planner_core tests).
- Sentinels: `tray_id == 0` = AGV carries no tray (DiscreteAgvState.msg), 7 inline checks -> a
  predicate `IsCarryingTray(agv)`; `scheduled_job.bay_id == 0` = no PROCESS_RETRIEVE node found ->
  find_if and branch on found; `payload_id != kEmptyGuid` -> `HasPayload(tray)`.
- schedule_events.hpp: ScheduleEvent comment says "Action DAG" (it is the event DAG); `job_idx_` and
  "The ID of the task" / ToString "Task ID" are the job index; TrayMove's comment describes
  expansion it does not have; apologetic comment in TrayMove::GetGarageEntityId; AgvMove holds lifts
  too (type AGV_MOVE). Unused: AgvMove::SetSrc/SetDest (declared, never defined), TrayMove::Assigned,
  VecsTransition::SetStateChange, VrcTransition getters (requested floor, from/to node), enum
  UNDEFINED; test-only: ApplyCommand x3, SetDiscreteChange, SetSourceState, SetCommand. Larger:
  split AgvMove into lift and move events (removes the variant handling in scheduler and CHUGG).
- Correction to item 198: VrcTransition exists and CHUGG plans it; nothing in production creates
  one, so the deleted TODO at ApplyTransitionAndRegisterOccupant has no effect today, but the
  reason given ("no such event type") was wrong.

### Commit 8 additions (item 202), unstaged

- ScheduleEventDag::Apply > ApplyEventsTo; ScheduleEvent::Apply > ApplyTo (5 overrides; callers in
  scheduler, motion_planner, planner_core tests).
- IsCarryingTray(agv) and HasPayload(tray) in scheduler utils replace `tray_id != 0` (7) and
  `payload_id != kEmptyGuid` (3); the retrieve-bay loop uses ranges::find_if and branches on found
  instead of `bay_id == 0`.
- schedule_events.hpp: ScheduleEvent / TrayMove / GetGarageEntityId comments now describe the code;
  job_idx_ > job_index_ (ToString keeps "Task ID": it is in error texts and 7 recordings); deleted
  AgvMove::SetSrc/SetDest (never defined), TrayMove::Assigned, VecsTransition::SetStateChange,
  VrcTransition's three getters, UNDEFINED, SetDiscreteChange / SetSourceState / SetCommand and their
  test blocks, ApplyCommand for AGV commands and for action nodes (test-only) and the ApplyAgvCommand
  test. Correction: the bay-command overload is used by BayTransition::ApplyTo; kept as
  ApplyBayCommand with its test. Correction 2: the AGV-command overload was not a stub (it applied
  the command), it was only test-only.
- Checks: 5 packages build 0 warnings; planner_core 22 (one test removed), motion_planner 81,
  advanced 16, scheduler 187 both ways, recordings unchanged, prek green, tidy 0. 16 files,
  +471 / -974.

### scheduler.cpp pattern scan (item 203), recommendation

Commit 8 is `70ba93ea`. Subagent scan of all of scheduler.cpp, spot-checked here. Proposed now (behaviour
neutral, new commit 9): PlanContext::AddChainedEvent (AddEvent + AppendToAssetChain, 11 sites; not
the VECS stop at :89, see B16); ExpandAgvMoveJob with the positive branch first and no cast;
ChainTrayEvent (4) / ChainAgvEvent (4); DependOnFreeingMoves (5); message builders MakeBayCommand,
MakeVecsStateChange, MakeAgvPoseChange; ComputeTrayCollisionId, GetBayInboundPose,
IsBayOdpAreaClear, IsEvChargeRequested, BuildImmobileTrayFilter reused at 2 sites;
`if(auto* x = dynamic_cast<...>)` instead of type check + cast; get_if instead of
holds_alternative + get; negated-else swaps, else-after-return, empty(), const& instead of copies,
`*`/`->` instead of repeated .value(); GetEventsInTopologicalOrder; PrintDagIfEnabled.
Later (C1 / AGV-solver territory): AssignTrays block extractions, AssignAgvs phase extraction,
ComputeCurrentState prologue (each caller keeps a different error prefix), an ApplyEvent wrapper.


### Review fold-in (item 205), history rewritten on 2026-10-30

The stage-A session implemented `review_stage2.md` at the tip (validated: 3 packages 0 warnings,
scheduler 188 both ways with recordings unchanged, planner_core 22, advanced 16, tidy clean after one
emplace_back) and folded the changes into the ten commits by an interactive rebase onto `5d5d7b39`.
Old tip kept as `jmg/SW2-1135/backup-ec2785b3`; not pushed (the user force-pushes with lease).

| # | old | new | what was folded in |
|---|---|---|---|
| 1 | `8576aa48` | `991502ec` | `TogglePrintDags` > `ToggleDagPrinting` (scheduler_ros, tests); message updated |
| 2 | `20884e57` | `a005b90d` | `last_event_by_asset` > `last_event_by_entity`, `AppendToAssetChain` > `ChainAfterLastEntityEvent`, `asset` > `entity`; message updated |
| 3 | `1ffabb36` | `891dc19f` | renames only |
| 4 | `4393c88c` | `828f4bfb` | `AssignDestAndUnblockingMoves` > `AssignDestinationAndUnblockingMoves`, `GateAgvMoveOnBlockerDeparture` > `OrderAgvMoveAfterBlockerDeparture`, `AssignTrayIdForEmptyMove` > `PickEmptyTrayForMove`, `PropagateEventCostToChildren` > `PropagateEarliestStartToChildren`, `matching` > `root_event_by_agv`; message updated |
| 5 | `a5ea1fcf` | `98bbc0fe` | `last_agv_event` > `last_event_by_agv`, `last_move_to_tray_event` > `last_move_to_tray_event_by_agv`, `current_node_occupant` > `occupant_by_node`, `last_tray_event` > `last_event_by_tray` |
| 6 | `400b521c` | `b1a85516` | `is_reciprocal_allowed` > `is_reciprocal_heading_allowed` |
| 7 | `2706dc55` | `04c5ca33` | renames only (4 clang-format wraps of lines the `interfaces::msg::` qualifiers lengthened) |
| 8 | `70ba93ea` | `5fc0e120` | renames only |
| 9 | `8e976f18` | `bfc23e67` | everything below; message gains a paragraph |
| 10 | `ec2785b3` | `ebb9de58` | same seven fixes in the refactored form; message rewritten (see below) |

Commit 9 additions (scheduler.cpp anonymous namespace unless said otherwise):
- `Fail(fmt, args...)` / `RetryableFail(fmt, args...)` return `stdx::Unexpected(JobFailure{...})`
  from a `std::format` string; 93 `JobFailure` sites and 3 string concatenations in utils.cpp use
  them or `stdx::Unexpected(fmt, args...)`. `include/scheduler/format.hpp` (new) gives
  `std::formatter` for `GaragePose`, `Guid` and `GarageEntityId` through `std::to_string`
  (common_ros/print_utils). Every string is byte-for-byte unchanged.
- `MakeTrayMove(job_index, tray_id, dest, agv_id = nullopt)` at the five `TrayMove` sites;
  `PickupHeading(agv, tray)` (the AGV's heading when on the tray's axis, else the tray's) at
  AppendAgvMoveToTrayEvent and ComputeAgvPickupDuration; `OrderAfterBayAndChargerEvents(ctx,
  working_state, dest, tray_move)`; constants `kBayTransitionPlaceholderId` (1),
  `kBayProcessPlaceholderId` (2) at the MakeBayCommand sites, `kMaxAgvPathRepairPasses` (256).
- Private methods `ApplyReparkHeadingPreference(dest, working_state, tray) const` and
  `CheckReparkDestination(ctx, working_state, tray_opt, dest) const` split out of
  ExpandReparkTrayJob; `ExpandAgvMoveJob` binds `const auto& agv`, checks first, then one branch
  for a carried tray (`IsTrayReversedOnAgv` > `ReciprocalGaragePose`, `MakeTrayMove`) and one for
  a bare AGV move.
- utils: `IsTrayReversedOnAgv(agv, tray)` = `volley::IsReciprocal(agv.pose.heading,
  tray.pose.heading)`, next to `IsCarryingTray` / `HasPayload`.
- Reference bindings (`const auto& payload / bay / tray = *x_opt;`) in the retrieve, insert and
  ready-for-* expansions; `required_moves.emplace_back`; parameters `event_cost` > `event_duration`
  and `agv_id` > `agv_entity` (ComputeTravelDuration); `//` > `///` inside `class Scheduler`;
  neutrality notes at `ChainTrayEvent` / `ChainAgvEvent` / `AddChainedEvent` (review 1.2).

Commit 10's message now says, per fix, which recorded scenario reaches it (AdvancesRootTray,
ReadyForInsert, UnplugsCharger* / WhileCharging), that a failed unblocking apply now fails the tray
assignment (fix 2), that fix 5's path is unreachable (both callers pass false) and so is fix 3
(`GetAllowedHeadings` adds each heading with its reciprocal; the scenario written to reach it
failed and was dropped), and that the recordings are unchanged under SCHEDULER_CHECK_RECORDINGS=1.

How the fold-in was done (for the next time): todo with `pick X` + `exec bash log/stage.sh <stage>
[msg]` after each commit that owns a rename stage (the exec runs in the container: rename script,
clang-format, `git add` by name, `git commit --amend`), `break` after commits 9 and 10 (tree
replaced by the prepared one, amended with the message file). Pick conflicts were resolved
mechanically: take theirs, apply the renames owned by the commits already rewritten, format, add,
continue. Lesson: an `edit` entry whose pick conflicts does not stop again after
`git rebase --continue`, so an `edit`-based first attempt amended only commits 1 and 2 and was
aborted; `exec` amends regardless. Scripts: `log/stage.sh`, `log/rename.py`, `log/rebase-todo2.txt`
in the repo's gitignored `log/`, drivers in the session scratchpad.

Checks on the rewritten tip: tree identical to the validated snapshot; `git range-diff` pairs all
ten commits; commits 7 and 8 touch the same file sets as before; build of scheduler,
scheduler_advanced_tests and agvhito_tools 0 warnings (19 s). Tests on the first rewritten tip: scheduler 188
with SCHEDULER_CHECK_RECORDINGS=1 and plain, planner_core 22, scheduler_advanced_tests 16, tree
clean; tidy found one `bugprone-optional-value-conversion` (`dest.value()` passed to MakeTrayMove's
optional parameter, #9's code), fixed as `dest` and folded into #9 by a second rebase (`edit` on #9,
#10 re-applied cleanly): #9 `bfc23e67`, #10 `ebb9de58`. On that tip: build 0 warnings, scheduler 188
with recordings unchanged, tidy 0.

### Comment clean-up and the stage split (item 206), 2026-10-30

Both approved by the user ("yes, both"; TODOs left alone). Eleven commits now; the shas of commits
3 to 10 changed again because the comment edits were amended in (the sections above use the new
ones: #3 `891dc19f`, #4 `828f4bfb`, #5 `98bbc0fe`, #6 `b1a85516`, #7 `04c5ca33`, #8 `5fc0e120`,
#9 `bfc23e67`, #10 `ebb9de58`); #1 and #2 are untouched. #11 is `aa651a6f`.

Comment clean-up (`split_proposal.md` section 5): 47 of the 54 items, as idempotent text edits
(`log/comments.py`) run as a rebase `exec` after each pick from #3 on, so each comment goes in the
first commit where it exists: 29 deletions / 58 removed lines land in #3 ("condense comments"),
the planner_core ones in #8, the `///` > `//` restyle of the file-local helpers and the misplaced
`AssignDestinationAndUnblockingMoves` doc in #9. Skipped on the user's word: the six `TODO(any)`
and the "consider adding a transition" line (1002); kept by choice: the six numbered step labels
in ComputeBayRebalancingActions and the same-floor carriage note in InsertVrcActionsIntoDag (a why).
Net on the tip: 46 insertions, 90 deletions across six files. Note for next time: the first attempt
ran the exec after every pick, which put most deletions into #1; the second ran it from #3.

Commit 11 `aa651a6f`, the split (`split_proposal.md` sections 1 to 4, as proposed): scheduler.cpp
3251 lines > scheduler.cpp 356 (constructor, Plan, ExpandJob, PlanMotions, MakeFailedJob,
SetBayReadinessRatioCallback, GetBayInboundPose, IsBayOdpAreaClear, IsPlainParkingSpot,
GetFirstSystemFloor), job_expansion.cpp 866, tray_assignment.cpp 752, agv_assignment.cpp 837,
validation.cpp 98, action_graph.cpp 372; utils.{hpp,cpp} gain MakeVecsStateChange,
MakeAgvPoseChange, MakeTrayMove, KeepTrayHeadingIfEquivalent; the new job_failure.hpp holds
JobFailure (out of scheduler.hpp), Fail and RetryableFail, now reached through
`using volley::scheduler::Fail;` in scheduler.cpp and job_expansion.cpp. CMakeLists lists the five
new sources. Includes per file by a token heuristic (`split.py` in the session scratchpad; two
misses fixed by the build: HideAgvs, Deserialize<T>); clang-format puts `"scheduler/scheduler.hpp"`
first only in scheduler.cpp, its main file. Header declaration order unchanged (the optional
reorder of section 1 was not done). Verified: sorted line multisets of the old file and the new
ones differ only by the moved JobFailure struct and MakeTrayMove's default argument (declaration
only); build 0 warnings; scheduler 188 both ways, recordings unchanged; planner_core 22; advanced
16; tidy 0 (the whole-file tidy wave feared in section 3 did not happen). Not pushed.

### Commit 12 `1a76c027`: the heading helpers (item 207), 2026-10-30

User: rename and possibly reimplement `ReciprocalGaragePose` and `IsAngleOrReciprocal`, in a commit
that is easy to amend. Their common implementations are one-liners (`Wrap(a) == Wrap(b) ||
Wrap(a) == Wrap(b + 180)`; node kept, heading `Wrap(h + 180)`), used across common_ros (9),
motion_planner and planner_core, so, as with `IsTrayReversedOnAgv` (review 5), the scheduler gets
its own names in `utils.{hpp,cpp}` and common is untouched: `OppositeHeading(int) -> int16_t`
(was `ReciprocalAngle`, 4 sites), `WithOppositeHeading(pose)` (was `ReciprocalGaragePose`, 2
sites, plus the two-line copy in FindUsableDestination), `IsSameOrOppositeHeading(a, b)` (was
`IsAngleOrReciprocal`, 7 sites). They delegate to the common functions (equivalent by
construction; a local re-implementation would only repeat `Wrap`). Locals `reciprocal_dest` /
`reciprocal_vertex_opt` > `opposite_*`; two docs reworded. Kept: the parameter
`is_reciprocal_heading_allowed` and the message field `reciprocal_to_tray` (the message's word).
Also in this commit: `static_cast<int>(CountEmptyTrays(state))` at utils.cpp:271, a 2025 line the
tidy hook started flagging once utils.cpp changed around it (narrowing unsigned > int). Checks:
build 0 warnings, scheduler 188 with recordings unchanged, planner_core 22, advanced 16, tidy 0.
Twelve commits; not pushed.

### Verb-first names, professional messages, second comment sweep (item 208), 2026-10-30

User: functions start with a verb; commit messages too casual; another comment sweep; and an
estimate for pure-function job expansions. All twelve commits were rewritten in one rebase
(`reword` each, `exec` sweep from #3; backup `jmg/SW2-1135/backup-6d965062`), so every sha in the
sections above is the new one: #1 `991502ec`, #2 `a005b90d`, #3 `891dc19f`, #4 `828f4bfb`,
#5 `98bbc0fe`, #6 `b1a85516`, #7 `04c5ca33`, #8 `5fc0e120`, #9 `bfc23e67`, #10 `ebb9de58`,
#11 `aa651a6f`, #12 `1a76c027`.

- Renames (land where the name first appears): OppositeHeading > ReverseHeading,
  WithOppositeHeading > ReversePoseHeading (#12), PickupHeading > ChoosePickupHeading,
  RetryableFail > FailRetryable (#9). Left: ToActionNode (on main) and common_ros's
  CollisionEntityIdFromAgvState.
- Messages: rewritten in an objective register, shorter (the #5 body from 48 lines to 32, #9 from
  31 to 31 with the new helper names), facts kept; `log/newmsg/<n>.txt` applied by `reword.sh`.
- Sweep (`sweep.py`, 117 edits at the tip, net -139 lines): header docs reduced to the contract a
  signature cannot show (scheduler.hpp from 69 comment lines to 30), the new helpers' docs
  deleted, the numbered step labels in ComputeBayRebalancingActions removed and their why
  reworded, planner_core's "Throws if" / "nullopt if" contracts deleted, restating comments in the
  stage files deleted. TODO(any) lines untouched.
- Pure-function expansions, estimate (not done): job_expansion.cpp reads layout_ (14),
  motion_graph_ (6), collision_table_ (2), logger_ (8), bay_readiness_ratio_ and the
  reset-bay callback, and calls ten members of other stages (ApplyPreferredHeading,
  ApplyEvChargeHeading, ResolveBlockingTrays x2, PickEmptyTrayForMove, AssignTrays x2,
  ComputeTravelDuration, GetBayInboundPose, GetFirstSystemFloor, IsBayOdpAreaClear,
  IsPlainParkingSpot). Free functions need a services struct (PROMPT C1-1 GarageServices) and
  those ten made free first, i.e. phase C1 plus AssignTrays: days, not hours. Recommended for the
  solver PR; no test calls Expand*Job directly, so the signature change itself is cheap later.

### FailRetryable removed (item 210), 2026-10-30

User: apply the recommendation of `upstream_cleanup_assessment.md` section 0; defer the rest for
review. `Fail` stays; `FailRetryable` and its doc are deleted and the two retryable sites in
ExpandRetrieveJob spell the initializer out (`stdx::Unexpected(JobFailure {.message = ...,
.is_retryable = true})`). Folded into the commits from #9 on by `log/fail.py` as a rebase exec
(the `using volley::scheduler::FailRetryable;` line of the split commit goes with it); messages
9 and 11 reworded. Commits 1 to 8 unchanged; #9 `bfc23e67`, #10 `ebb9de58`, #11 `aa651a6f`,
#12 `1a76c027` (the shas above are updated). Backup `jmg/SW2-1135/backup-04fe81d7`. Checks: build
0 warnings, scheduler 188 with recordings unchanged, planner_core 22, advanced 16, tidy 0.

### Codex review 1 applied (item 213), 2026-10-30

Both findings of `codex_reviews/codex_review_1.md` applied by `log/planned.py` as a rebase exec from commit 5
(backup `jmg/SW2-1135/backup-270fcb24`); commits 1 to 4 unchanged, #5 to #12 now `98bbc0fe`,
`b1a85516`, `04c5ca33`, `5fc0e120`, `bfc23e67`, `ebb9de58`, `aa651a6f`, `1a76c027` (the shas above
are updated).
- #5: `AgvAssignmentState::occupant_by_node` > `last_occupant_by_node` (never erased on departure;
  OrderArrivalAfterPriorOccupant reads it as the AGV last placed on the node).
- #10: `PlannedTrayMove {move, path, applied_from}` replaces the `TrayMovesWithPaths` pair
  (`std::vector<PlannedTrayMove>` is `PlannedTrayMoves`) and the `applied_move_sources` map:
  an advance move already applied carries the pose it started from; the emission loop reads
  `applied_from` instead of a membership test. ResolveBlockingTrays builds the records with
  designated initializers; the recursive-resolution test destructures three fields. Message 10
  gains a sentence. This is the struct PROMPT C1-4 plans.
- Checks: build 0 warnings, scheduler 188 with recordings unchanged, planner_core 22, advanced 16,
  tidy 0 (results of the final run in item 213 of the log).

### Codex review 2 applied (item 215), 2026-10-30

User: fix findings 1, 2, 5 and 6 now; 3 and 4 if small (they were: one caller each); defer 7 and
the PlanContext reference. Thirteen commits now; #5 to #12 re-created by the fold-in (`98bbc0fe`,
`b1a85516`, `04c5ca33`, `5fc0e120`, `bfc23e67`, `ebb9de58`, `aa651a6f`, `1a76c027`), #13 new
`04de7078`. Backup `jmg/SW2-1135/backup-43f88f6f`.
- #5 (`log/stub.py`, exec from #5): ComputeAgvOccupiedDuration deleted with its declaration and
  test; AssignAgvs starts each AGV's occupied time from zero with the TODO at that line.
- #10 (`log/fix2.py`, exec from #10): Plan() copies the PlanContext before each ExpandJob and
  restores it on failure (the open TODO in MakeFailedJob is resolved and deleted);
  SetBayReadinessRatioCallback rejects non-finite values (`std::isfinite`, message unchanged);
  ComputeAgvMoveDuration returns `stdx::Expected<Duration>` and ApplyNonTrayRootEvents propagates
  it; ComputeStateBefore returns `stdx::Expected<DiscreteGarageState>`, OrderTransitionAroundAgvLifts
  returns `stdx::Result` and OrderAllTransitionsAroundAgvLifts propagates it. Tests:
  `RetrieveJob.FailedJobLeavesNoEvents` (new scenario `plan/retrieve_job/FailedJobLeavesNoEvents.yaml`
  on `38_gramercy/car_charging_at_23`: a retrieve that adds the stop-charging event and then fails
  for lack of a bay, followed by a repark of the same tray; the recording holds one charger command,
  two before the fix) and `SchedulerState.RejectsNonFiniteBayReadinessRatio`. No tracked recording
  changed, so no recorded plan contained leftover events or reached the two propagated failures.
- #13 (`eccles.py` once at the tip): ApplyEvChargeHeading and its six call sites deleted (the early
  return in ApplyPreferredHeading with them); scheduler_advanced_tests 01-04 and their CMake targets
  deleted (12 advanced tests remain, on 550_w21st and 175_e82nd). Recordings unchanged.
- Counts on the tip: scheduler 189 (188 + 2 new - the stub's), planner_core 22, advanced 12; build
  0 warnings; tidy 0 (results in item 215 of the log). Deferred to tickets: the replay cost (7),
  PlanContext by reference, the repo-wide Eccles retirement (layouts, exerciser scenarios,
  common_ros tests).

### Codex review 3 applied (item 217), 2026-10-30

Sixteen commits now; tip `7629d9f7`. #9 to #13 re-created by the fold-in (`bfc23e67`, `ebb9de58`,
`aa651a6f`, `1a76c027`, `04de7078`; the shas above are updated), backups
`jmg/SW2-1135/backup-5c764d8c` (and the earlier ones).
- #9 (`log/tray.py`): ExpandAgvMoveJob names the carried tray's destination `tray_dest` instead of
  re-using `dest`, which is the requested AGV pose.
- #10 (`log/fix3.py`): MotionScheduleOrder keys on start time, action id, hash and then the
  motion's own fields (end, collision id, entity, location, change type, idle), so a hash collision
  no longer makes two distinct motions compare equal; the hash stays third, so every existing
  ordering is preserved (recordings unchanged). A second line at the context restore in Plan() says
  the copy shares the event objects because expansion never changes an existing event.
- #13 (`log/wrap.py`): ApplyPreferredHeading, a one-line delegate since the Eccles removal, is
  deleted; its three callers call ApplyRetrievalHeading, which takes its doc. Message 13 says so.
- #14 `f9a55640`: ExpandAgvMoveJob's `is_reciprocal_heading_allowed` parameter and the branch it
  guarded are deleted (both callers passed false). Message 10 keeps its bullet: it describes that
  commit's diff.
- #15 `886bbd6f`: ToActionNode returns `stdx::Expected<ActionNode>` with one message per failure,
  `std::get_if` for the lift pose, the event by reference, the DAG builder makes the shared node;
  CollectAndCollapseTrajectoryMotions, BuildActionDagFromMotions and TransferEventDagDepsToActionDag
  return `stdx::Result` and no longer take a logger; BuildActionGraph logs and propagates each
  failure. The failure texts are new; no recorded scenario reaches one.
- #16 `7629d9f7`: the precedence experiment. ExpandReparkTrayJob applies ApplyRetrievalHeading before
  CheckReparkDestination (the tray-already-there check stays first); the recordings are unchanged,
  so it landed. The first variant, preference before the already-there check, also left the
  recordings unchanged but could turn a no-op repark into a rotation, so the minimal one was kept.
  The contract (is a requested heading authoritative) stays a ticket.
- Rebase lesson: `log/reword.sh` must know every subject it may see; commit 13's was missing, git
  stopped after creating the commit with its old message, fixed by amending and continuing.
- Checks on the tip: build 0 warnings, scheduler 189 with recordings unchanged (checked after each
  of #14, #15 and #16), planner_core 22, advanced 12, tidy (see item 217).

### Squashed to six commits (item 219), 2026-10-30

Carried out `squash_plan.md`: sixteen commits squashed into six adjacent groups with one
non-interactive `rebase -i` in the container; nothing reordered, no code changed. Tip `2bae4ff6`,
tree identical to `7629d9f7` (`git diff 7629d9f7 HEAD` empty; the tree shas are equal). Each new
commit's tree also equals the tree of the last old commit in its group.

| new | sha | old | old shas | summary |
|---|---|---|---|---|
| 1 (A) | `012e4955` | 1-6 | `991502ec` `a005b90d` `891dc19f` `828f4bfb` `98bbc0fe` `b1a85516` | rename, trim and simplify the scheduler |
| 2 (B) | `99c3f9a5` | 7-8 | `04c5ca33` `5fc0e120` | trim the planner_core event API; message headers per file |
| 3 (C) | `1438d791` | 9 | `bfc23e67` | extract repeated patterns; std::format error texts |
| 4 (D) | `71efa85d` | 10 | `ebb9de58` | the bug fixes |
| 5 (E) | `ba47ce80` | 11-12 | `aa651a6f` `1a76c027` | split by pipeline stage; scheduler-local heading helpers |
| 6 (F) | `2bae4ff6` | 13-16 | `04de7078` `f9a55640` `886bbd6f` `7629d9f7` | Eccles removal, dead paths, specific action-graph failures, repark heading order |

- Messages: the six texts of `squash_plan.md`, unchanged (`log/squashmsg/A.txt` .. `F.txt`); each
  body matches its file, no line over 100 characters.
- Editor script fix: the plan's `log/squash-msg.sh` took the first non-`#` line as the subject,
  but git's squash file has a blank line after its header comments, so every squash group would
  have stopped the rebase. Before the rebase the line became
  `grep -m1 -v -e '^#' -e '^[[:space:]]*$'`; tested on a squash-format and a reword-format file
  for each of the six groups.
- Checks on `2bae4ff6`: build of scheduler, scheduler_advanced_tests and agvhito_tools 0 warnings;
  `SCHEDULER_CHECK_RECORDINGS=1` scheduler 189 tests pass, `git status` clean under
  `test/scenarios/`; planner_core 22, scheduler_advanced_tests 12; `volley-in-container tidy` 0
  findings.
- Backups: `jmg/SW2-1135/backup-7629d9f7` was created and verified before the rebase; after every
  check passed, all seven local backup branches (`ec2785b3`, `6d965062`, `04fe81d7`, `270fcb24`,
  `43f88f6f`, `5c764d8c`, `7629d9f7`) were deleted. None had been pushed. Only
  `jmg/SW2-1135/scheduler-renames-and-cleanups` remains. Not pushed.

### Codex review 4 applied (item 220), 2026-10-30

Six commits still; findings in `codex_reviews/codex_review_4.md`. Commits 1 and 2 unchanged; 3 to 6 rebuilt, tip
`9eea90ce`. New shas: 1 `012e4955`, 2 `99c3f9a5`, 3 `8db6ab49`, 4 `9fe822d8`, 5 `1fdff98f`,
6 `9eea90ce`. Backup `jmg/SW2-1135/backup-2bae4ff6`, deleted after review.
- #3: `MakeAgvPoseMove(job_index, agv_id, source, destination)` replaces MakeAgvPoseChange (three
  callers); `StopChargingBeforeTrayMove` returns `stdx::Result` (error completes the callers'
  "...that is on a " messages, texts unchanged).
- #4: ExpandReparkTrayJob reads the tray from `working_state`, falling back to `initial_state` for a
  tray a dest-less move took out; MotionScheduleOrder keys on `delta.has_value()` and the payload
  buffer after the type. New test ReparkTrayJob.ReturnsTrayAfterEarlierRepark (fails on the old
  lookup: one lowering instead of two). Message 4 has two new/changed bullets and the test.
- #6: `FindRetrievalTrayHeading(node_id, payload_opt)` replaces ApplyRetrievalHeading and
  ApplyReparkHeadingPreference; layout checks dropped (InitRetrievalHeadings invariant). Message 6
  has a new paragraph.
- Mechanics: edits written as pattern scripts that find their file (`log/fold/fix_c.py`, `fix_d.py`,
  `fix_f.py`, `fold_lib.py`), dry-run on exported trees of each old commit first, then one rebase in
  the container whose exec lines rebuild 3 to 6 from their old trees plus the cumulative edits
  (`log/fold/rebuild.sh`, `todo.txt`), hooks running on each commit. Each new commit equals its
  dry-run tree; the tip equals the tested working tree byte for byte.
- Checks: commit 3 and 4 built and tested on detached checkouts (0 warnings; 186 and 190 tests with
  recordings unchanged); tip: build 0 warnings, scheduler 190 with recordings unchanged,
  planner_core 22, advanced 12, tidy 0.

### Codex review 5 applied (item 222), 2026-10-30

Six commits still; findings in `codex_reviews/codex_review_5.md` (#5, the alias rename, skipped by the user's
choice). Commits 1 and 2 unchanged; tip `276bd6a4`. Shas: 1 `012e4955`, 2 `99c3f9a5`, 3 `60a05953`,
4 `a730f895`, 5 `93c9c725`, 6 `276bd6a4`. Backup `jmg/SW2-1135/backup-9eea90ce`, deleted after review.
- #3: ExpandRetrieveJob's TRANSITION_TO_RETRIEVE in named steps on `planned_bay`;
  IsPayloadWithinBaySizeLimits, FindUnoccupiedChargerWithShortestTravelTime.
- #4: `GetInboundPose(node)` in utils (wrapped); the docked-AGV check, the charger search and the
  EV-charger transition pose use it. New test AgvChargeJob.AlreadyOnCharger with initial state
  `5675_pecos_combined/agv_on_charger_14` (old code: three commands to another charger).
  OrderAfterFreeingMoves returns `stdx::Result`; tray assignment checks every GetBlockers and
  AddOccupant.
- #6: ResolveCarriedTrayDestination; ExpandAgvMoveJob validates the resulting AGV pose. The action
  graph keeps skipping locations outside the occupancy graph (16 recorded plans reach them: bay
  and VECS motions have no heading; two AGV edges near pecos charger 14), named and explained.
- Tidy caught `*tray_dest` passed to MakeTrayMove's optional parameter; passes the optional now.
- Same mechanics as item 220 (`log/fold/fix_c2.py`, `fix_d2.py`, `fix_f2.py`, `rebuild2.sh`,
  `todo2.txt`). The tip equals the tested working tree; commits 3 and 4 built and tested on their
  own (0 warnings; 186 and 191 tests, recordings unchanged); tip: scheduler 191, planner_core 22,
  advanced 12, tidy 0.

### Codex review 6 applied (item 224), 2026-10-30

All six commits rebuilt (commit 1 took edits); details and deviations in `codex_reviews/codex_review_6.md`. Shas:
1 `836191b7`, 2 `0a43d398`, 3 `539ee717`, 4 `84f798e1`, 5 `f409be2e`, 6 `280339f9`. Backup
`jmg/SW2-1135/backup-276bd6a4`, deleted after review.
- #1: stale comments (one deleted, one reworded), the stashed-tray loop without its copy.
- #3: `ActionSpan {first_action, last_action}` / `ActionSpanByEvent`; the placeholder-id comment
  points at central.
- #4: lazy MotionScheduleOrder (no payload copy); BuildScheduledActionsArray keeps request order and
  leaves the DAG alone (order check added to ReparkTrayJob.ReturnsTrayAfterEarlierRepark, fails on
  the old code); StopChargingBeforeTrayMove and GetFirstSystemFloor return whole sentences (two
  FromUnavailableCharger recordings re-recorded, message only).
- #5: utils.hpp direct includes; scheduler.hpp includes it with quotes.
- #6: TrayDestinationPlan, DesiredBaySplit, BayRebalancingActions; AssignAgvs without the pair vector.
- Mechanics: `log/fold/fix_a3.py` .. `fix_f3.py`, `rebuild3.sh`, `todo3.txt` (exec lines only, from
  the base); dry-run on all six; the scripts reproduce the tested tree byte for byte; the tip equals
  it. Every commit built and tested on its own: 0 warnings; scheduler 186, 186, 186, 191, 191, 191
  with recordings matching; tip planner_core 22, advanced 12, tidy 0.

### Codex review 7 applied (item 226), 2026-10-30

All six commits rebuilt; what went where in `codex_reviews/codex_review_7.md`. Shas: 1 `952fcd4f`, 2 `b774213c`,
3 `6a6eeb83`, 4 `4e07be76`, 5 `6024be5e`, 6 `7166af0e`. Backup `jmg/SW2-1135/backup-280339f9`, deleted after review.
- Renames in the commit that introduced each name; comments in 1 and 6.
- Commit 5: utils.cpp keeps only shared helpers (ValidateBaseState, IsCarryingTray, HasPayload, the
  heading helpers, MakeInboundPose, MakeAgvPoseMove, MakeTrayMove, KeepTrayHeadingIfEquivalent);
  bay_rebalancing.hpp/.cpp (CMake, test include); VRC insertion local to action_graph.cpp; two event
  helpers local to job_expansion.cpp; stage members ordered breadth first from the entry point.
- Mechanics: `log/fold/fix_a4.py` .. `fix_f4.py` (fold_lib gained `rename_token`), `rebuild4.sh`,
  `todo4.txt`, `dryrun4.sh` (exports the advanced tests too). Body-by-body comparison: 103 functions
  before and after, only the three intended edits differ. Every commit built and tested on its own
  (scheduler 186, 186, 186, 191, 191, 191; advanced 16 through commit 5, 12 at the tip; recordings
  matching); tip planner_core 22, tidy 0.

### Codex review 8 applied (item 228), 2026-10-30

All six commits rebuilt; what went where in `codex_reviews/codex_review_8.md`. Shas: 1 `d0d77bbd`, 2 `da8d0c31`,
3 `bd44fea1`, 4 `bb3228d0`, 5 `a8b1f9fc`, 6 `f756a7cc`. Backup `jmg/SW2-1135/backup-7166af0e`, deleted after review.
- Commit 1: StorePreferredRetrievalHeadings and its locals.
- Commit 3: DisableBaseScheduleEntities, FindProcessRetrieveAction, LogMotionCostAudit (file-local in
  the file defining Plan()), HasTrayMoveEvents; AssignAgvs' setup in one loop, locals renamed. Commit
  3's message names the new functions.
- Commit 6's message still said InitRetrievalHeadings; amended after the rebuild (tree unchanged).
- Mechanics: `log/fold/fix_a5.py`, `fix_c5.py` (fold_lib gained `rename_in_function_code`, which skips
  string literals, and `add_local_helpers`), `rebuild5.sh`, `todo5.txt`, `dryrun5.sh`. Every commit
  built and tested on its own (0 warnings; scheduler 186, 186, 186, 191, 191, 191; advanced 16 through
  commit 5, 12 at the tip; recordings matching); tip planner_core 22, tidy 0.

### Codex review 9 applied (item 230), 2026-10-31

All six commits rebuilt; what went where in `codex_reviews/codex_review_9.md`. Shas: 1 `64336ef9`, 2 `4d76c328`,
3 `a42b3ab9`, 4 `54c49cb0`, 5 `d90b25ca`, 6 `dca15cf9`. Backup `jmg/SW2-1135/backup-f756a7cc`, deleted after review.
- Commit 1: IsAgvMotionBetweenFloors (+ locals), StorePreferredPayloadHeadingsForRetrieval,
  ScheduleAgvLift, ScheduleAgvMoveToPickup, with contracts.
- Commit 3: ExcludeCommittedResources (+ `committed_actions`, contract); AddChainedEvent's comment.
- Commit 6: FindPreferredTrayHeadingForRetrieval (+ contract). Messages 3 and 6 use the new names.
- Mechanics: `log/fold/fix_a6.py`, `fix_c6.py`, `fix_f6.py`, `rebuild6.sh`, `todo6.txt`, `dryrun6.sh`.
  Every commit built and tested on its own (0 warnings; scheduler 186, 186, 186, 191, 191, 191;
  advanced 16 through commit 5, 12 at the tip; recordings matching); tip planner_core 22, tidy 0.

### Codex review 10 applied (item 233), 2026-10-31

Commit 1 unchanged; 2 to 6 rebuilt. Shas: 1 `64336ef9`, 2 `2a35cad1`, 3 `d96a9a88`, 4 `1522675e`,
5 `6332be76`, 6 `e6976369`. Backups `jmg/SW2-1135/backup-dca15cf9` (before the round) and
`backup-86305d35` (before the test fix-up), both deleted after review.
- Commit 2: motion_planner renames (BuildKeepOutFilters, BuildStaticObstacleFilter(s),
  ComputeEdgeDurations, ComputeEdgeMarginalDurations, ComputeAllPairsShortestPathCosts, FindPosePath);
  HideAgvs to FindAgvUnderTrayAssignment returning std::optional (recursion
  FindRemainingAgvUnderTrayAssignment, file-local; empty success stays engaged); contract without the
  fewest-moves claim; dead edge-cost code removed; new test NoEnabledAgvs. Scheduler callers follow.
  Commit 2's message has a paragraph listing the renames.
- Commit 3: FindPayloadDeliveryAction with its contract.
- Tidy at the tip found bugprone-unchecked-optional-access in the hiding tests: the check does not
  follow gtest's ASSERT_TRUE (it wraps the condition in an AssertionResult), and value() is flagged
  too. The four reads now follow `if(!destinations_opt.has_value()) { FAIL() << ...; }`, which the
  check understands; folded into commit 2 by a second rebuild of 2 to 6 (`fix_b8.py`, `rebuild8.sh`).
- Checks: every commit built and tested on its own (scheduler 186, 186, 186, 191, 191, 191; advanced
  16 through commit 5, 12 at the tip; motion_planner 82 from commit 2; recordings matching); tip
  planner_core 22, tidy 0.

### Codex review 11 applied (item 236), 2026-10-31

All six commits rebuilt (plan and refinements in `codex_reviews/codex_review_11.md`). Shas: 1 `644e2297`,
2 `0b0130fb`, 3 `af0f5fe1`, 4 `044516b8`, 5 `17d031fe`, 6 `30b014aa`. Backup
`jmg/SW2-1135/backup-e6976369`, deleted after review.
- Commit 1: `occupancy_history` (with the occupants-are-events comment), debug DAG labels
  `after_occupancy_ordering`; ApplyBayOrChargerTransition with its contract; `tray_collision_id`,
  `root_tray_collision_id`; `root_path_illegal_poses`, `root_path_vertex`/`root_path_pose`, "root
  path" in comments; `prior_dests_by_blocking_tray` and the lambda's parameters.
- Commit 3: OrderAfterPriorOccupants; one `tray_collision_id` before AssignTrays' loop; the timing maps
  in AgvAssignmentState (ComputeAgvAssignmentEdgeCosts takes `const AgvAssignmentState&` and reads the
  earliest start without inserting); every log call on rclcppx LOG_* (a converter for the stream and
  printf macros; messages as arguments); `common_ros/roslog.hpp` gone from the scheduler; the audit CSV
  with `{:g}` and the index counted outside the log call. Message updated.
- Commit 6: the occupancy-skip comment says it is a policy.
- Audit CSV compared before and after on RetrieveJob.FromStall and BackToBack with
  SCHEDULER_TEST_LOG=1: 60 lines, identical.
- Checks: every commit built and tested on its own (scheduler 186, 186, 186, 191, 191, 191; advanced
  16 through commit 5, 12 at the tip; motion_planner 81 at commit 1, 82 after; recordings matching);
  tip planner_core 22, tidy 0. Ticket to raise: the occupancy graph lacks some AGV edges.

### Codex review 12 applied (item 239), 2026-10-31

All six commits rebuilt. Shas: 1 `5243fef5`, 2 `8e536aab`, 3 `fa68eb08`, 4 `e1212de8`, 5 `0b2d0973`,
6 `9bc62155`. Backup `jmg/SW2-1135/backup-30b014aa`.
- Commit 1: BuildAgvOrderDag with `vertex_by_agv` (plain vertices, Add checked once); ClassifyBay as a
  guard plus switch (commit 1's version used BayReportMsg and DagBase; the scripts replace each body
  with the tree's names); ClassifyBays' bools `const`; the bay-split comment.
- Commit 4: the clean-garage AGV move, the charge job's bay transition and the path-repair replay check
  their ApplyTo result. Message has a bullet.
- Commit 5: `#include <algorithm>` in bay_rebalancing.cpp.
- Checks: every commit built and tested on its own (0 warnings; scheduler 186, 186, 186, 191, 191,
  191; advanced 16 through commit 5, 12 at the tip; motion_planner 81 at commit 1, 82 after;
  recordings matching); tip planner_core 22, tidy 0. Origin still has `30b014aa` until the user
  force-pushes.

### Codex review 13 follow-ups and the comment sweep (item 241), 2026-10-31

All six commits rebuilt (`log/fold/rebuild11.sh`, `todo11.txt`; scripts `fix_a11.py`, `fix_b11.py`,
`comment_edits.py`). Shas: 1 `18a64c84`, 2 `4b70d6d2`, 3 `4bd1cceb`, 4 `07812ad4`, 5 `ecfc2be3`,
6 `72599b1f`. Backup `jmg/SW2-1135/backup-9bc62155`. Messages unchanged.
- Commit 1: AssignTrays' `new_move_path` is `root_path_poses`, with "Unordered: the blocking tray's move
  claims the whole root path."
- Commit 2: utils.cpp drops `common_ros/common_ros_msgs.hpp` (the scheduler's last use).
- Comment sweep (user: minimal footprint, no context): 35 rewrites or deletions in the scheduler sources
  and one in motion_planner (`garage_graph_pathing.hpp`, "Ring 3b's" dropped). Matched by words, so
  each lands in the commit that wrote the comment (commits 1 to 4; none in 5). Deleted: restatements
  of the code ("This is our root path...", "Best effort: log repark failures", the two "Optimal
  retrieval heading..." lines). Context removed: callers named for orientation, "nightly triple-pick
  test", "Chugg's GetDependencyCompletionTime()", "Central's", "Phase 1", "NOTE:". Corrected: the
  fallback advances the root tray one step (it said "step by step"); the ApplyPreferredHeading TODO
  named a function that no longer exists. Commit 1 gets the `Reduce()` spellings, commit 2's rename
  turns them into `RemoveRedundantEdges()`.
- Extraction of AssignTrays deferred to C1 (note at the top of PROMPT.md phase C1).
- Checks: tip byte-identical to the tested tree; every commit built and tested on its own (0 warnings;
  scheduler 186, 186, 186, 191, 191, 191; advanced 16 through commit 5, 12 at the tip; motion_planner
  81 at commit 1, 82 after; recordings matching); tip planner_core 22, tidy 0.

### Codex review 14 subset in commit 2 (item 243), 2026-10-31

Commits 2 to 6 rebuilt on the unchanged commit 1 (`log/fold/rebuild12.sh`, `todo12.txt`; the three
tested files copied from `log/fold/c2files/`). Shas: 1 `18a64c84`, 2 `c2d3e456`, 3 `d45a0289`,
4 `97825853`, 5 `93d73177`, 6 `d9082d54`. Backup `jmg/SW2-1135/backup-72599b1f`. Commit 2's message
gains a static-graph-filtering paragraph; the others are unchanged.
- `static_graph_filtering.{hpp,cpp}` and `chugg_common.cpp` (two `SetEnabled` calls); the three files
  change only in commit 2, so commits 3 to 6 carry the same content.
- Names follow the scheduler's: `motion_graph`, `state`, `collision_table`, `collision_id` and
  `other_collision_id` (as in tray and AGV assignment), `filter_by_footprint` (as
  `keep_out_filter_by_footprint`), `ignore_trays/agvs/bays` (as validation and AGV assignment; the
  bulk builder's `ignored_*` unified). Codex's `moving_`/`obstacle_` prefixes not used for that reason;
  `effective_collision_id`, `bay_inbound_heading`, `max_resource_size_index`, `resource_size_index`,
  `disabled_node_ids`, `disabled_node_collision_id`, `blocked_poses`/`blocked_edges`.
- Header comments in `//` (motion_planner's style).
- Checks: tip byte-identical to the tested tree; commits 2 to 5 built and tested on their own (0
  warnings; scheduler 186, 186, 191, 191; advanced 16; motion_planner 82; recordings matching); tip
  scheduler 191, planner_core 22, advanced 12, motion_planner 82, tidy 0.

### Codex review 15 commit-1 part, and commit 2's tidy findings (item 245), 2026-11-01

All six commits rebuilt (`log/fold/rebuild14.sh`, `todo14.txt`; `fix_a13.py` everywhere, the
commit-2 files from `log/fold/c2files/` from commit 2 on). Shas: 1 `5ab1d57d`, 2 `f8c02917`,
3 `7102f82f`, 4 `0656faef`, 5 `4658dcfa`, 6 `ce566d68`. Backup `jmg/SW2-1135/backup-d9082d54`.
- Commit 1: `/// Target fraction of usable bays made ready to insert, rounded up and capped by the empty
  trays; the other usable bays are made ready to retrieve.` on `SchedulerParams::bay_readiness_ratio`;
  `desired_bay_readiness_ratio` to `insert_ready_fraction` (CalculateDesiredBaySplit,
  ComputeBayRebalancingActions). Message unchanged.
- Commit 2: the round-14 renames made five old optional reads count as changed lines, and tidy (which
  reads committed changes only) reported them once folded: `chugg_common.cpp` (two SetEnabled calls)
  and `static_graph_filtering.cpp` (bay inbound heading, vertex pose, layout node). Each now checks and
  throws `std::invalid_argument` with a message; nothing catches `bad_optional_access` in the planner.
  The message says so.
- Lesson: run `volley-in-container tidy` after folding, on the committed tip.
- Checks: tip byte-identical to the tested tree; tidy 0 at the tip; every commit built and tested on
  its own (0 warnings; scheduler 186, 186, 186, 191, 191, 191; advanced 16 through commit 5, 12 at
  the tip; motion_planner 81 at commit 1, 82 after; recordings matching); tip planner_core 22.

### The bay readiness ratio renamed inside the scheduler (item 246), 2026-11-01

User: "Rename it inside the scheduler only. I don't want to rely on comments." All six commits rebuilt
(`log/fold/rebuild15.sh`, `todo15.txt`, `fix_a14.py`). Shas: 1 `ea34e836`, 2 `1dbda0c5`, 3 `530762cf`,
4 `affbae1f`, 5 `170ccc7f`, 6 `36288c0a`. Backup `jmg/SW2-1135/backup-ce566d68`. Commit 1's message
gains a paragraph; the others are unchanged.
- `target_insert_ready_bay_fraction`: the `SchedulerParams` field, the member (`_`), the bay-rebalancing
  parameters (was `insert_ready_fraction`), `is_fraction_changed`, the scenario loader's key
  (`kTargetInsertReadyBayFraction`) and the `scheduler:` key of 45 scenario files and the README,
  the advanced tests, agvhito_tools' move planner. The doc comment is gone.
- Kept, as the system's names: the ROS parameter string, the `set_bay_readiness_ratio` service, its
  handler `SetBayReadinessRatioCallback` and handle `set_bay_readiness_ratio_srv_`, the
  `SchedulerReport.bay_readiness_ratio` field, the service tests' names.
- Survey of other names that lean on comments: `names_covered_by_comments.md` (17 proposals, not
  applied; `BayClassification::WILL_BE_RETRIEVE_READY` is never produced).
- Checks: tip byte-identical to the tested tree; tidy 0 on the committed tip; every commit built and
  tested on its own (0 warnings; scheduler 186, 186, 186, 191, 191, 191; advanced 16 through commit 5,
  12 at the tip; motion_planner 81, then 82; recordings matching); tip planner_core 22, agvhito_tools built.
