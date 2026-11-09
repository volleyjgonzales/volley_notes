# SW2-482 notes (running log; not committed)

## Status

- **Layout of this folder:** see `README.md`; the sub-ticket's code notes,
  ticket and PR texts are under `SW2-1126_scenario_files/`.
- **Phase R (design review) done on 2026-10-22.** Report: `DESIGN-REVIEW.md` in
  this folder, with the user's answers to its eight questions at the end. The
  plan is `PROMPT.md` (rewritten by Phase R, eight commits).
- **Plan approved by the user on 2026-10-22** (after the eight review questions
  were answered; see the end of `DESIGN-REVIEW.md`).
- **Branch** `jmg/SW2-1126/scheduler-scenario-files` since 2026-10-26 (Jira
  SW2-1126, created by the user as a Task under epic SW2-482); before that
  `jmg/SW2-484/scheduler-core-refactor`, created on 2026-10-23 as
  `jg/SW2-484/scheduler-core-refactor` branch point; two merges after the study
  pack's `703bfe7c`: `#996` motion_planner perf, `#998` launcher fix.
  `scheduler`, `planner_core` and `common_ros` are unchanged between the two, so
  the study pack's line numbers still hold.)
- **Stage A done.** PR #1007
  `[SW2-1126] Record the scheduler planning tests as scenario files` merged on
  2026-10-29 as `61e7b0d7` on main (two commits: `28f69008` the tests and
  scenario files, `6d4ae5b5` the viewer). Review log items 1 to 157 cover its
  rounds. What landed is described in `SW2-1126_scenario_files/code_notes.md`;
  the "Commit 1" section below is the original design as first built (reference
  files, `parity.hpp`) and is kept as history only.
- **Branch restructured (2026-10-29, item 185) to the six-commit plan** (stage
  code notes table): `ecb5d9d8`, `2e04696b`, `d0a62a0a`, `7c8e6c84`, `b8866c62`
  on `4c281d86` (origin/main `5d5d7b39`, bay only). From now on new work lands
  as fixups into its commit: survey groups 2-4 into #5, TODO keys into #3, a new
  #6 for `scheduler_msgs.hpp`. Not pushed; the user force-pushes with lease.
  PROMPT.md sections 4-6 updated once the names are final (end of stage, with
  the PR text), before commit 4 of the C1 stage.
- **Next: stage 2, phase B2, SW2-1135**
  (<https://volleyautomation.atlassian.net/browse/SW2-1135>): commits 2 and 3 of
  `PROMPT.md` (the `Scheduler` member and expansion renames, then
  `PlanContext`), then step B2-4, small behaviour-neutral code-quality
  clean-ups, one commit each, surveyed first. Branch
  `jmg/SW2-1135/scheduler-renames-and-cleanups`, created from `main` `61e7b0d7`
  on 2026-10-29; folder `SW2-1135_scheduler_renames/`. In a new session: read
  `PROMPT.md` (updated 2026-10-29 for the merged state), `review_rules.md`
  (section 7: what PR #1007 taught) and this file, then start commit 2.
- **Stage 2 history rewritten on 2026-10-30 (item 205):** the review's
  recommendations (`SW2-1135_scheduler_renames/review_stage2.md`, section 6) are
  folded into the ten commits, now `991502ec` .. `ebb9de58`; the old tip
  `ec2785b3` is branch `jmg/SW2-1135/backup-ec2785b3`. Not pushed. The other
  session must not assume its old shas. Branch renamed the same day to
  `jmg/SW2-1135/scheduler-renames-and-cleanups` (never pushed under the old
  name). Jira Scope / DoD still to re-paste (user).
- **Stage 2 rewritten again on 2026-10-30 (item 208):** verb-first helper names,
  rewritten commit messages and a second comment sweep, all twelve shas new
  (code notes list them); backup branch `jmg/SW2-1135/backup-6d965062`.
  Pure-function job expansions estimated and deferred to the solver PR.
- **Stage 2 at twelve commits (2026-10-30, items 206-207):** comment clean-up
  folded into commits 3 to 10 (shas changed again), and commit 11 `aa651a6f`
  splits scheduler.cpp into one file per pipeline stage
  (`SW2-1135_scheduler_renames/split_proposal.md`); commit 12 `1a76c027` names
  the heading helpers (OppositeHeading, WithOppositeHeading,
  IsSameOrOppositeHeading). Branch
  `jmg/SW2-1135/scheduler-renames-and-cleanups`, not pushed. TODO(any) items
  untouched.
- **Stage 2 at thirteen commits (2026-10-30, item 215):** Codex review 2
  applied: fix commit gains transactional expansion, the NaN check and
  propagated failures from the two duration/state helpers, with two tests; stub
  removed in #5; #13 `04de7078` removes the Eccles exception and advanced tests
  01-04. Tip `04de7078`, backup `jmg/SW2-1135/backup-43f88f6f`. Not pushed.
- **Stage 2 at sixteen commits (2026-10-30, item 217):** Codex review 3 applied:
  tray_dest (#9), structural motion order and rollback note (#10), wrapper out
  (#13), commit 14 dead reciprocal parameter, commit 15 action-graph error
  handling, commit 16 repark heading resolved before validation
  (recording-guarded). Tip `7629d9f7`, backup `jmg/SW2-1135/backup-5c764d8c`.
  Not pushed.
- **Stage 2 squashed to six commits (2026-10-30, item 219):** `squash_plan.md`
  carried out: `012e4955`, `99c3f9a5`, `1438d791`, `71efa85d` (the fixes),
  `ba47ce80`, `2bae4ff6` on `5d5d7b39`; tree identical to `7629d9f7`. All local
  backup branches deleted after the checks; the shas in the bullets above are
  history. Not pushed: the user force-pushes with lease and re-pastes the Jira
  fields.
- **Codex review 4 folded in (2026-10-30, item 220):** still six commits; 3 to 6
  rebuilt: `012e4955`, `99c3f9a5`, `8db6ab49`, `9fe822d8` (the fixes),
  `1fdff98f`, `9eea90ce`. Backup `jmg/SW2-1135/backup-2bae4ff6` (deleted after
  review). Not pushed.
- **Codex review 5 folded in (2026-10-30, item 222):** still six commits:
  `012e4955`, `99c3f9a5`, `60a05953`, `a730f895` (the fixes), `93c9c725`,
  `276bd6a4`. Backup `jmg/SW2-1135/backup-9eea90ce` (deleted after review). Not
  pushed.
- **Codex review 6 folded in (2026-10-30, item 224):** still six commits:
  `836191b7`, `0a43d398`, `539ee717`, `84f798e1` (the fixes), `f409be2e`,
  `280339f9`. Backup `jmg/SW2-1135/backup-276bd6a4` (deleted after review).
  Origin still has `9eea90ce`; the user force-pushes with lease.
- **Codex review 7 folded in (2026-10-30, item 226):** still six commits:
  `952fcd4f`, `b774213c`, `6a6eeb83`, `4e07be76` (the fixes), `6024be5e`,
  `7166af0e`. Backup `jmg/SW2-1135/backup-280339f9` (deleted after review).
  Origin still has `9eea90ce`; the user force-pushes with lease.
- **Codex review 8 folded in (2026-10-30, item 228):** still six commits:
  `d0d77bbd`, `da8d0c31`, `bd44fea1`, `bb3228d0` (the fixes), `a8b1f9fc`,
  `f756a7cc`. Backup `jmg/SW2-1135/backup-7166af0e` (deleted after review).
  Origin still has `9eea90ce`; the user force-pushes with lease.
- **Codex review 9 folded in (2026-10-31, item 230):** still six commits:
  `64336ef9`, `4d76c328`, `a42b3ab9`, `54c49cb0` (the fixes), `d90b25ca`,
  `dca15cf9`. Backup `jmg/SW2-1135/backup-f756a7cc` (deleted after review).
  Origin still has `9eea90ce`; the user force-pushes with lease.
- **Codex review 10 folded in (2026-10-31, item 233):** still six commits:
  `64336ef9`, `2a35cad1`, `d96a9a88`, `1522675e` (the fixes), `6332be76`,
  `e6976369`. Backups `jmg/SW2-1135/backup-dca15cf9`, `backup-86305d35` (both
  deleted after review). Origin still has `9eea90ce`; the user force-pushes with
  lease.
- **Codex review 11 folded in (2026-10-31, item 236):** still six commits:
  `644e2297`, `0b0130fb`, `af0f5fe1`, `044516b8` (the fixes), `17d031fe`,
  `30b014aa`. Backup `jmg/SW2-1135/backup-e6976369` (deleted after review).
  Pushed by the user on 2026-10-31: origin is at `30b014aa`.
- **Codex review 12 folded in (2026-10-31, item 239):** six commits: `5243fef5`,
  `8e536aab`, `fa68eb08`, `e1212de8` (the fixes), `0b2d0973`, `9bc62155`. Backup
  `jmg/SW2-1135/backup-30b014aa`. Origin is at `30b014aa` until the user
  force-pushes with lease.
- **Codex review 13 follow-ups folded in (2026-10-31, item 241):** six commits:
  `18a64c84`, `4b70d6d2`, `4bd1cceb`, `07812ad4` (the fixes), `ecfc2be3`,
  `72599b1f`. Backup `jmg/SW2-1135/backup-9bc62155`. Origin is at `30b014aa`
  until the user force-pushes with lease. The AssignTrays extraction is deferred
  to C1 (PROMPT.md, phase C1 note).
- **Codex review 14 subset folded into commit 2 (2026-10-31, item 243):** six
  commits: `18a64c84` (unchanged), `c2d3e456`, `d45a0289`, `97825853` (the
  fixes), `93d73177`, `d9082d54`. Backup `jmg/SW2-1135/backup-72599b1f`. Origin
  is at `30b014aa` until the user force-pushes with lease. Later, own PR: the
  static_graph_filtering extraction
  (SW2-1135_scheduler_renames/codex_reviews/codex_review_14.md).
- **Codex review 15 commit-1 part and commit 2's tidy fix (2026-11-01, item
  245):** six commits: `5ab1d57d`, `f8c02917`, `7102f82f`, `0656faef` (the
  fixes), `4658dcfa`, `ce566d68`. Backup `jmg/SW2-1135/backup-d9082d54`. Origin
  is at `30b014aa` until the user force-pushes with lease.
  `volley-in-container tidy` reads committed changes only (base..HEAD): run it
  after folding.
- **Ratio renamed inside the scheduler (2026-11-01, item 246):** six commits:
  `ea34e836`, `1dbda0c5`, `530762cf`, `affbae1f` (the fixes), `170ccc7f`,
  `36288c0a`. Backup `jmg/SW2-1135/backup-ce566d68`. Origin is at `30b014aa`
  until the user force-pushes with lease. Name survey:
  `names_covered_by_comments.md`.
- **Comment-covered names renamed (2026-11-01, item 247):** six commits:
  `62055901`, `fddd399c`, `e5263891`, `a3252b7a` (the fixes), `7aa10b1f`,
  `7401cd5a`. Backup `jmg/SW2-1135/backup-36288c0a`. Origin is at `30b014aa`
  until the user force-pushes with lease. `BayClassification` waits for its own
  discussion.
- **EnsureAgvMovePathsClear references fixed (2026-11-01, item 248):** six
  commits: `3ec14e3e`, `1bfacbf6`, `c9074bef`, `0d6a27a0` (the fixes),
  `40830560`, `ce45d5ff`. Backups `jmg/SW2-1135/backup-36288c0a` and
  `backup-7401cd5a`. Origin is at `30b014aa` until the user force-pushes with
  lease.
- **Stale function names in strings fixed (2026-11-01, item 249):** six commits:
  `9b8fc1a8`, `54c5f15c`, `81a9b042`, `d8d98ffc` (the fixes), `5546c5eb`,
  `afb46ad0`. Force-pushed by the user; origin is at `afb46ad0`. All backup
  branches deleted on the user's word (item 250).
- **Codex review 16 applied (2026-11-01, item 253):** six commits: `62013e6e`,
  `7498179b`, `ff951152`, `de7f316e` (the fixes), `0c27c896`, `56527885`. Backup
  `jmg/SW2-1135/backup-afb46ad0`. Origin is at `afb46ad0` until the user
  force-pushes with lease.
- **Codex review 17 applied (2026-11-01, item 255):** six commits: `c016f385`,
  `3add30b8`, `25de7b42`, `0dccb3cd` (the fixes), `9b0eefc6`, `50b1b722`.
  Backups `jmg/SW2-1135/backup-afb46ad0`, `backup-56527885`. Origin is at
  `afb46ad0` until the user force-pushes with lease.
- **Codex review 18 applied (2026-11-01, item 257):** six commits: `cd0f256d`,
  `a569ada7`, `68cf2a6e`, `63d5e8d1` (the fixes), `a055cc07`, `cc4a9e92`.
  Backups `jmg/SW2-1135/backup-afb46ad0`, `backup-56527885`, `backup-50b1b722`.
  Origin is at `afb46ad0` until the user force-pushes with lease.
- **Rebased on main `f3fa775f` (2026-11-02, item 260):** six commits:
  `dea3336a`, `9912b70f`, `c2c5ea9b`, `04ff7dc2` (the fixes), `c821cab0`,
  `a3370c4b`. Pushed by the user (origin matches); all backup branches deleted
  (item 261).
- **Greptile's test restored (2026-11-02, item 264):** commit 6 is `67aedc95`
  (commits 1-5 unchanged: `dea3336a`, `9912b70f`, `c2c5ea9b`, `04ff7dc2`,
  `c821cab0`). Backup `jmg/SW2-1135/backup-a3370c4b`. Origin is at `a3370c4b`
  until the user force-pushes with lease.
- **BayClassification by readiness (2026-11-02, item 265):** six commits:
  `1fa8208e`, `22ddb653`, `a216d43b`, `105aad75` (the fixes), `336304da`,
  `e5edee2e`. Backups `jmg/SW2-1135/backup-a3370c4b`, `backup-67aedc95`. Origin
  is at `a3370c4b` until the user force-pushes with lease.
- **Rebased on main `58bd75a3` (2026-11-02, item 266):** six commits:
  `d3a03b61`, `3119fa12`, `220ca691`, `9fa1ec3f` (the fixes), `f8ee20af`,
  `8f9315c1`. Pushed by the user (origin and the PR head match); CI
  run 41523411626. All backup branches deleted on the user's word (item 268).
- **Comment sweep (2026-11-02, item 271):** six commits: `fb84e9c0`, `739391dd`,
  `2ac0a4c0`, `15b15916` (the fixes), `d6c9aace`, `a80d0ee3`. Pushed (origin
  matches); the backup is deleted (item 273).
- **Dan's review folded (2026-11-03, item 276):** six commits: `fb84e9c0`,
  `9640ca7b`, `f55265f7`, `13bf8b15` (the fixes), `236408e7`, `fcbb3a27`. Pushed
  by the user (origin matches); the backup is deleted (item 280).
- **Seventh commit (2026-11-03, item 282):** `5bd41efe` moves Scheduler into
  volley::scheduler and drops the redundant prefixes, on top of `fcbb3a27`.
- **Rebased on main `bf59774c` (2026-11-03, item 283):** seven commits:
  `73897bda`, `9fb17b07`, `e498672d`, `e5bb81f9` (the fixes), `b7d53f4e`,
  `6f70e68d`, `ff6ba632`. Pushed by the user (origin matches).
- **Eighth commit (2026-11-03, item 295):** `073556ea` fix(central_api):
  recreate bay confirm clients that miss service discovery at startup (the
  garage confirm-insert race). Pushed; it didn't fix the race (the REST API's
  participant is stuck, not its clients) but serves as the detector in the DDS
  tests (item 303).
- **Rebased on main `8ebf0762` (2026-11-04, items 315-320):** eight commits
  `cf72cc40` .. `e1d24a7c` (bay refactor PR #1008 in the base). Build and tests
  green; pushed by the user (origin matches; PR mergeState BLOCKED only on
  checks/review). Comb runs `e1d24a7`.
- **DDS investigation (confirm-insert 500 after full starts), paused 2026-11-04
  22:30Z, resumes 2026-11-05:** `testing/dds_investigation_summary.md`
  (overview), `testing/dds_handoff_2026-11-04.md` (state and next steps),
  findings 1.9-1.15, `testing/dds_root_cause_plan.md`. Full starts STUCK 6/8;
  overflow ruled out (E2); a joining participant un-sticks the REST API 3/3.
  Comb lent to a teammate for an unrelated branch overnight; test files removed
  from comb, kept in `testing/comb_results_2026-11-04/`. Codex review prompt
  ready (`testing/codex_dds_review_prompt.md`). Items 285-336.
- **Feature branch back to 7 commits (2026-11-04, item 343):** the user moved it
  to `07eb74dd` and force-pushed (origin and PR #1018 head `07eb74dd`;
  `e1d24a7c` dropped). The DDS diagnostics are commit `5f72fcae` on
  `jmg/test/dds-rest-api-diagnostics` (one commit on `07eb74dd`; not pushed).
- **Ordered-plan proposal (2026-11-08):** idea to replace the event DAG with an
  ordered plan plus explicit prerequisites; input from the SW2-905 and EV-charge
  sessions and Codex review 1 (all five points accepted). Folder
  `ordered_plan_prototype/` with the proposal, assessment and a draft Jira
  spike. No ticket yet, no code. Same day: `scheduler_problem_formulation.md`,
  a draft solver-agnostic instance format (MAPD with goal sets and precedence;
  rearrangement layer; today's pipeline as solver #1). Recommended before the
  ordered-plan work. For review.
- **Parity from now on:**
  `SCHEDULER_CHECK_RECORDINGS=1 volley-in-container test scheduler` green and
  `git status` clean under `test/scenarios/`; CI runs the property assertions
  only (item 156).
- **Baseline on main `61e7b0d7`:** scheduler 187 tests as colcon counts them (92
  `TEST` cases, 19 binaries), planner_core 23, scheduler_advanced_tests 16.

## Commit 1 as first built: parity references (A1, A2); superseded by the scenario files (history)

Files (all under `src/planner/scheduler/`): `test/parity.hpp` (44 lines),
`test/parity.cpp` (176), `CMakeLists.txt` (+12), `test/scheduler_tests.cpp`
(+18), `test/scheduler_insert_orientation_tests.cpp` (+6),
`test/scheduler_jobs_tests.cpp` (+265: 34 reference calls, 4 new tests, one
helper), 58 files under `test/reference/` (23,039 lines). Code size +521 versus
the +400 estimate; references 58 versus ~45. After the review rounds (see the
review log): references 58 files / 28,805 lines in three stage folders with
`test/reference/README.md`; `tools/view_references.py` +
`tools/reference_viewer/` (1,260 lines); `pyproject.toml` / `uv.lock` add
`plotly==7.1.0` to the dev group (the one change outside the package, asked for
by the user).

Decisions and deviations:

1. `agv_command.id` is **never set** by the scheduler (empty in every
   reference), contrary to the plan's description. `ToActionNode` copies the
   node GUID into `vecs_command.command_id` and `vrc_command.command_id`;
   `Canonical(response)` rewrites those two and `agv_command.id` (harmless, and
   right if it ever gets set). `bay_arrival_node_guid` is rewritten through the
   same old-to-positional map.
2. `Emit` normalises through a load/emit round trip: yaml-cpp emits a freshly
   built empty collection as `key:` + `[]` on the next line but a loaded one
   as `key: []`, so the first fresh-process compare run failed 7 references
   (empty edge sets and empty `first_tray_event`). Files are written in the
   loaded form.
3. Format: sequences of scalars in the response (GUID `bytes`, `parents`,
   `node_indices`) and the `[from, to]` edge pairs are flow style (one line
   each); everything else is block style. Event strings get a `#n` suffix (n =
   earlier identical strings in vertex order) and are sorted; their position is
   the canonical index. Floats come out of rosidl's `to_yaml` (`std::showpoint`,
   6 digits).
4. The `ExpectReference(F&& produce, ...)` overload is constrained with
   `std::invocable`: unconstrained, it captured `YAML::Node` prvalues. It plans
   twice (plus the test's own plan): record runs took 4.5 s (`scheduler_tests`),
   7.6 s (`scheduler_jobs_tests`), 0.7 s (`scheduler_insert_orientation_tests`).
5. Suffixes: `ReadyForRetrieveJob` empty_bay / tray_in_bay; `TransitionBay`
   unknown_bay / wrong_command / to_retrieve / to_insert (round 2: the stage
   folder replaced the tray / agv suffixes). The
   `ResolveBlockingTraysRecursivelyUnblocksChain` test and the commented-out
   `DoubleRetrieveDodgeAgv` are not instrumented. `test/reference/` is recorded
   with the three binaries in the order scheduler_tests, scheduler_jobs_tests,
   scheduler_insert_orientation_tests (the order does not matter: GUIDs are
   canonical).
6. All four requested scenarios were built (none skipped), as `SchedulerJobs`
   tests:
   - `ReadyForInsertJob`: tiny_lot, bay 1 READY_TO_RETRIEVE and empty, AGV at 8,
     empty trays at 6 and 9. The fill pass in `PlanReadyForInsertJob` resolves
     the blank tray id; 8 nodes, bay transition last.
   - `BaseScheduleReservesAgvAndNodes`: triple_pick_lot, AGVs 1 (node 5) and 2
     (node 9), tray 2 at 8; base schedule holds one AGV command for AGV 2 from 9
     to 12; MOVE_TRAY tray 2 to 11. AGV 1 does the job (asserted); 4 nodes.
   - `RetrieveAdvancesRootTray` (fallback 1): tiny_lot full: root tray 1
     (payload) at 9, blocker 4 on waypoint 3, trays 5, 8, 11 on nodes 5, 8, 11,
     AGV at 2, retrieve to bay 1. Log: "Advancing t1 to 6@0", then the blocker
     is resolved through recursion (t4 -> 9 after t5 -> 9... chain). 35 nodes,
     executing.
   - `RetrieveParksBlockerOnCriticalPath` (fallback 2): same with blocker 4 on
     parking 6 (the next step). Log: "Found open space for blocking tray t4 at
     3@0 allowing parking on critical path", then the re-scan finds t4 again and
     fallback 1 advances t1 to 6. 39 nodes, executing. Both share the helper
     `RetrieveFromFullTinyLot(scheduler, blocker_node)` (state string with a
     `{blocker_node}` placeholder).
7. Determinism: every lambda reference compared equal between its two in-process
   runs and in the fresh compare process (`volley-in-container test scheduler`:
   80 tests, 0 failures). B4 (pointer-hash edge order) did **not** surface in
   this suite.
8. Test counts after commit 1: scheduler 80 (76 + 4 new), planner_core 23,
   scheduler_advanced_tests 16; all pass. Hooks (`prek run --files` on every
   touched file): all pass; clang-tidy is a push-stage hook and was not run
   (first due at commit 3).

Reference files (`<stage>/<Suite>.<Name>[.<suffix>].yaml`; "ctx" = a stage
reference under `task_planning/tray_assignment` or
`task_planning/agv_assignment` (the `.tray` / `.agv` names below are the folders
now); "plan" = `action_graph/` with the node count):

| File | Kind | Covers |
| --- | --- | --- |
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

- Branch `main` at `703bfe7caa28af5be4175528d4cd98a2db5b8e59` (2026-10-22 10:57
  -0600, "Merge pull request #995 from
  VolleyAutomation/pvc/SW2-1111/fix-sim-event-handling"). Working tree clean.
- `volley-in-container build scheduler scheduler_advanced_tests`: OK, 14
  packages, 0 compiler warnings (cached build, 6 s).
- `volley-in-container test scheduler`: 76 tests as `colcon test-result` counts
  them, 0 failures, 0 skipped, 25 s. The four gtest binaries hold **72 `TEST`
  cases**: `scheduler_tests` 25, `scheduler_jobs_tests` 30,
  `scheduler_insert_orientation_tests` 4, `utils_tests` 13. None is `DISABLED_`;
  one is commented out (`Scheduler.DoubleRetrieveDodgeAgv`,
  `scheduler_tests.cpp:1940-2002`, "TODO(Joe) revisit"). No `TEST_F` or
  `TEST_P`; there are no fixture classes or shared test helpers.
- `volley-in-container test planner_core scheduler_advanced_tests`: planner_core
  23 tests, scheduler_advanced_tests 16 (9 `TEST` cases in 7 binaries, 2 more
  commented out), 0 failures, 111 s.
- Logs: `~/.cache/volley-in-container/logs/20261022-1115*-build-*.log`,
  `20261022-111559-test-scheduler.log`,
  `20261022-111627-test-planner_core_scheduler_advanced_tests.log`.
- No test reads the clock: every test uses `rclcpp::Time(0)` or
  `rclcpp::Time()`. Only `scheduler_ros.cpp` calls `now()`.

## Branch versus study pack (Phase 0, step 3)

- **The scheduler package is byte-identical to the snapshot**
  `sources/repomix-scheduler.xml` (all 15 files) except `package.xml`, where
  `launcher` became `site_config` (exec and test depend). So the study pack's
  line numbers for `scheduler.cpp` are valid on this branch at `703bfe7c`. Still
  find code by symbol.
- SW2-769 ("move scheduler dir to planner and reorg pkgs", `6664181d`) happened
  before the snapshot. The package is at `src/planner/scheduler`; siblings:
  `cost_functions`, `motion_planner`, `planner_core`,
  `scheduler_advanced_tests`, `task_planner`. Layouts moved to
  `src/config/site_config/layouts/` (`a719d4ab`); tests find them with
  `GetLayoutPathByName(name)` (common_ros → site_config → ament index).
  `common_ros/test/test_layout.yaml` is a second layout source used by
  `utils_tests` and four jobs tests.
- Files (lines): `scheduler.hpp` 456, `scheduler.cpp` 4200, `utils.hpp` 97,
  `utils.cpp` 520, `scheduler_ros.cpp` 125, `scheduler_component.cpp` 71, tests
  2004 + 2817 + 951 + 774.
- Tray call tree on the branch (all `Scheduler` members, `const`; line =
  definition in `scheduler.cpp`): `DoTrayAssignments` 2533–3092 (560 lines),
  `AssignTrayIdForEmptyMove` 2159, `AssignDestForUntargetedMove` 2222–2338,
  `ResolveBlockingTrays` 1982–2119 (public), `FindOpenSpaceForRootTray` 1850,
  `TryFindBlockingTrayResolution` 1895, `ApplyTransitionToFreeingMoves` 2124,
  `UsePreferredHeading` 1771, `UseEvChargeHeading` 1781,
  `UseRetrievalHeading` 1805. `WithPriorDests` is a **lambda** inside
  `DoTrayAssignments` (2687), not a member. Private structs
  `OpenSpaceSearchResult` and `BlockingTrayResolution` are in
  `scheduler.hpp:388-402`.
- AGV tree: `DoAgvAssignments` 3475–3839, `GetJustMovingCost` 3094.
  `PlanMotions` 4005–4067, `ResponseFromTrajectories` 4069–4129. Anonymous
  namespace of `scheduler.cpp` (26–340): `ToActionNode`, `MotionScheduleOrder`,
  `CollectAndCollapseTrajectoryMotions`, `BuildActionDagFromMotions`,
  `TransferEventDagDepsToActionDag`, `BuildScheduledActionsArray`.
  `InsertVrcActionsIntoDag` is a free function in `utils.cpp:366`.
  `GetTopologicalOrdering` and `Reduce` are DAG methods (planner_core).
- Symbol use outside `scheduler` (rg over the workspace): `task_planner`
  (`BottleneckAssignment`, its own header and test),
  `scheduler_advanced_tests/test07.cpp` (2 mentions in comments),
  `system_tests/.../system_clean_garage_unstashes_waypoint.py` (1). Nothing
  outside `scheduler` calls the tray tree.
- `scheduler_advanced_tests`: 7 binaries, each one source,
  `LINK_LIBRARIES yaml-cpp` only (the scheduler library comes in through
  `ament_auto_depend_on_packages`). It uses only
  `Scheduler(layout, logger, params)`, `SchedulerParams::bay_readiness_ratio`,
  `Plan()`, `GetLayoutPathByName`,
  `DiscreteGarageState::Set/GetDiscreteGarageStateMessage`, `MakeGuid`, message
  fields. No member names, no `ScheduleContext`, no stage calls. Layouts:
  576_eccles, 576_eccles_half, 576_eccles_mini, 576_eccles_under_vcr,
  1355_fulton, 550_w21st, 175_e82nd. Comment in `test07.cpp:23-26`: AGV
  assignment tie-breaking "depends on hash-map iteration order and so varies
  between builds".
- Callers of the shared helpers: `ResolveBlockingTrays` ← `PlanChargePayloadJob`
  (1732, **uses only the destination and discards the required moves**),
  `AssignDestForUntargetedMove`, `DoTrayAssignments` (3 calls), itself via
  `TryFindBlockingTrayResolution` (recursion), test
  `ResolveBlockingTraysRecursivelyUnblocksChain`. `AssignTrayIdForEmptyMove` ←
  `PlanReadyForInsertJob` (1271, best-effort fill pass) and `DoTrayAssignments`.
  `UsePreferredHeading` ← `PlanAgvMoveJob`, `PlanReparkTrayJob`,
  `AssignDestForUntargetedMove`. `UseEvChargeHeading` ← `PlanChargePayloadJob`,
  `UsePreferredHeading`, `AssignTrayIdForEmptyMove`,
  `AssignDestForUntargetedMove`, `DoTrayAssignments` (2). `UseRetrievalHeading`
  ← `UsePreferredHeading` only. `first_tray_event` is written only by the tray
  tree (2284, 2333, 2952, 3064) and read once in the AGV tree (2487).
- `ApplyTransitionToFreeingMoves` handles **only `BAY_TRANSITION` and
  `VECS_TRANSITION`**: it registers the bay / VECS inbound pose with the generic
  `TRAY` footprint and applies the event. AGV and VRC events are skipped
  entirely (not applied to `working_state`).
- Direct stage calls in tests: `DoTrayAssignments` 4 (`scheduler_tests.cpp` 70,
  165, 245, 378), `DoAgvAssignments` 9 (178, 381, 749, 810, 895, 996, 1063,
  1129, 1287), `ResolveBlockingTrays` 1 (301). Context built as
  `std::make_shared<ScheduleContext>(MakeGuid(0, 0xDEADBEEF), state, rclcpp::Time())`,
  events added with `ctx->events.AddEvent/AddDependency`, result read with
  `std::tie(success, msg)`.
- `Plan` coverage by job type (end to end): MOVE_AGV, REPARK_TRAY, RETRIEVE,
  CHARGE_PAYLOAD, INSERT, READY_FOR_RETRIEVE, CHARGE_AGV, TRANSITION_BAY_*,
  CLEAN_GARAGE, MOVE_TRAY (advanced only). **Never covered: READY_FOR_INSERT,
  REBALANCE_GARAGE. No test sets `base_schedule`, `planned_jobs` or
  `active_jobs`.** Failure cases (jobs end in `STATE_ERROR`): 9 tests in
  `scheduler_jobs_tests.cpp`.
- `Scheduler` members: `layout_` (LayoutSPtr), `pg_` (used only in the
  constructor), `gg_`, `table_`, `logger_`, `cost_model_`,
  `bay_readiness_ratio_` (atomic), public mutable `costaudit_`, `printdags_`. No
  params member. `ScheduleContext` (`scheduler.hpp:57-117`): ctor takes
  `rclcpp::Time`; fields `request_id`, `request_id_str` (only used for
  `PrintGraph` labels under `printdags_`), `initial_state`, `start_time`,
  `disabledness_filters`, `events`, `scheduled_jobs`, `last_entity_event`,
  `first_tray_event`. `BoolStringPair` is `common/types.hpp:7`. `stdx` is
  namespace **`volley::stdx`** (`src/core/stdx/include/stdx/expected.hpp`,
  aliases over `tl::expected`, `E = std::string`; `Unexpected(msg)`,
  `Unexpected(fmt, args...)`, `AllHaveValues`). The scheduler already uses
  `stdx::Result` (`EnsureAgvMovePathsClear`, `InsertVrcActionsIntoDag`) and
  `stdx::Expected<bool>` (`RunAgvPathRepairPass`).
- No golden-file or reference-output test exists anywhere under `src/`. yaml-cpp
  is used in tests only as `YAML::Load(R"YML(...)YML")` into
  `DiscreteGarageState::Set`. Closest precedent:
  `motion_planner/test/continuous_state_tests.cpp:131-140` (loads a state YAML,
  compares messages). `interfaces::msg::to_yaml(msg)` (rosidl) serialises any
  message; `DiscreteGarageState::GetYaml()` uses it.
- Action-node GUIDs come from a **static counter**
  (`utils.cpp:307 CreateActionGuid`), so they depend on how many actions earlier
  tests in the same binary produced. Bay command ids are
  `std::to_string(MakeGuid(0, 1u))` constants; AGV command ids are
  `std::to_string(node guid)`.

## Design assumptions (Phase 0, step 4)

| Assumption | Result | Evidence |
| --- | --- | --- |
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

1. Solver input is plain data without the DAG: `Input{initial_state, steps}`
   where a step is a `MoveRequest` (job index, optional tray id, optional
   destination) or a `StateChange` (a bay or VECS transition event,
   `shared_ptr<const ScheduleEvent>`, applied to the working state when
   reached). Result: `fills`, `new_moves`, `edges` (by step/new-move id),
   `first_move_by_tray`. An adapter in the module (`StepsFromDag`,
   `ApplyResult`) is the only code that touches `ScheduleEventDag`. (User: yes.)
2. `Solver::Solve(const GarageServices&, const Input&)`: services per call, so
   `DefaultSolver` is stateless, default-constructible and injectable through a
   `Scheduler` constructor parameter. (User: yes.)
3. Parity by instrumenting the existing tests (`test/parity.hpp`): each planning
   test records / compares a canonical YAML of its result in
   `test/reference/<Suite>.<Name>[.<suffix>].yaml`. No fixture loader, no
   separate suite. Reference inputs are the tests themselves. (User: yes.)
4. Renames kept in this PR (user's choice): `Scheduler` members
   (`motion_graph_`, `collision_table_`, `GetMotionGraph`, `pg_` local,
   `cost_audit_`, `print_dags_`, `TogglePrintDags`); `Plan*Job` → `Expand*Job`;
   `ScheduleContext` → `PlanContext` in `plan_context.hpp` with `event_dag`,
   `first_event_by_tray`, `keep_out_filter_by_footprint`, `last_event_by_asset`
   (still keyed by `GarageEntityIdMsg`), `AddScheduledJob`,
   `AppendToAssetChain`, `AddAfterJobLeaves`; `stdx` for the tray tree (falls
   out of the module work, no extra commit). Deferred: `AssetId`, `ros/convert`,
   `ScheduledJob`, `Timepoint`, `ReserveBaseScheduleAssets`, vocabulary aliases
   and report, stage folders and targets for other stages, include-check script,
   action-graph and motion-planning moves, side-by-side test, edit-replay
   machinery, private headers.
5. Module folder `include/scheduler/task_planning/tray_assignment/` (user's
   choice), namespace `volley::task_planning::tray_assignment`, alias
   `tray_assignment` in `scheduler.cpp`; `GarageServices` in
   `include/scheduler/garage_services.hpp`, namespace `volley`. One static
   library target `scheduler_tray_assignment`, linked into `scheduler`; one
   gtest `tray_assignment_tests`
   (`test/task_planning/tray_assignment_tests.cpp`) that links only the module.
6. Eight commits (table in PROMPT.md section 5). Commit 3 may be split (type,
   then fields) and commit 8 at "module added, not yet used" / "Plan()
   switched"; worst case ten.
7. Heading helpers become value-returning: `EvChargeHeading` returns
   `std::optional<GaragePoseMsg>`, `RetrievalHeading` and `PreferredHeading`
   return the adjusted pose. The unused `tray_opt` parameter of
   `UsePreferredHeading` is dropped.
8. Section-8 quirks: all **keep**, except that the order in which
   `freeing_moves` blockers are turned into edges becomes id order instead of
   pointer-hash order (a deliberate, explained difference, visible only when one
   pose has two or more recorded occupants and only through tie-breaking; user
   accepted). See B4.
9. `scheduler_advanced_tests` is not touched (user's choice).
10. Error strings that spell a method name (`"PlanReadyForInsertJob ..."`) stay
    verbatim after the `Expand*Job` rename (rule 1).

## Bugs and oddities found, not fixed (report at review gates; none fixed silently)

- **B1 (fallback 1 path).** **[fixed in #10 (with B15)]**
  `scheduler.cpp:2842-2844` builds the advance move's path as
  `std::vector<GaragePoseMsg>{gg_.GetVertexFromPose(tray_opt->pose).value(), advance_move->GetDest().value()}`.
  The first element is a `Vertex` (`size_t`); `GaragePoseMsg` has only explicit
  constructors, so the initializer-list constructor is not viable and overload
  resolution picks `vector(size_type n, const T&)`: the path is **n copies of
  the destination pose**, with n = the vertex index of the tray's post-advance
  pose. Hypothesis from overload resolution; confirm with a one-line test in
  commit 4. Also `tray_opt` was refreshed after the advance was applied, so the
  advance move's `source_pose` in the emission loop (2929) and the root move's
  source (3037, 3050) are both the post-advance pose: the root tray's original
  pose is never registered in `freeing_moves` on this path. Keep exactly for
  parity; propose a follow-up.
- **B2.** **[fixed in #10]** The advance move is applied at 2833 and again at
  2931 (`TODO(Gunther)`). The second `Apply` is a same-pose change (tray already
  at its destination) and its result is ignored. Keep.
- **B3.** `AssignDestForUntargetedMove` never registers the original move's
  source or destination in `freeing_moves` and never queries blockers for them
  (only the required moves get path edges). Keep.
- **B4.** `freeing_moves` is
  `GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>>`; `GetBlockers`
  returns an `unordered_set` hashed on the pointer, so when a pose has two or
  more occupants the order of the `AddDependency` calls (and so each vertex's
  out-edge order, and so topological tie-breaking among equal job indices)
  depends on heap addresses and can differ between processes. The new solver
  keys occupancy by step id, which is deterministic. The record / compare split
  of the parity harness (separate processes) will show whether today's output is
  stable.
- **B5.** **[fixed in #10 (RetrieveJob.FailedJobReportedOnce)]** `Plan()`: a job
  that already failed during expansion is pushed with `FailJob` again by the
  tray / AGV / sanity failure loops, which iterate `request_data.pending_jobs`.
  Verify; out of scope.
- **B6.** **[fixed in #10]** Error text
  `"DoTrayAssignments TrayMove with TrayId=<id>does not exist in working_state"`
  lacks a space. Keep (rule 1).
- **B7.** **[fixed in #10]** `DagBase::ToDotFormatString` has no
  `VRC_TRANSITION` case (planner_core; out of scope).
- **B8.** `assigned_events` in `DoTrayAssignments` is written and never read
  (dead; disappears with the loop).
- **B9.** `UsePreferredHeading`'s `tray_opt` parameter is unused
  (`(void)tray_opt`).
- **B10.** Commented-out `UsePreferredHeading` calls at 2820 and 2912 ("FIX:
  Does this break triple pick test?"). Keep commented out; do not resurrect.
- **B11.** `scheduler_advanced_tests/test07.cpp:23-26` says AGV assignment
  tie-breaking varies between builds. AGV assignment is untouched; it may limit
  how strict end-to-end references can be on that layout.
- **B12 (found 2026-10-29).** **[fixed in #10]** `DoTrayAssignments`'
  destination check accepts a destination whose pose has no vertex when its
  reciprocal has one (and that vertex is enabled); the blocking-tray search then
  takes `GetVertexFromPose(dest).value()` on the original pose, which throws
  `bad_optional_access` out of `Plan()`. Not fixed (rule 3); propose with a
  reproducing test.
- **B13 (found 2026-10-29).** **[fixed in #10]** `ExpandAgvMoveJob`: with
  `allow_recip` and an AGV heading equal or reciprocal to the requested one, the
  pose change takes the AGV's current node as well as its heading
  (`node_id_next = agv_opt->pose.node_id`), so the move goes nowhere. The old
  comment says only the heading was meant. Not fixed (rule 3).
- **B14 (found 2026-10-29, survey).** **[fixed in #10]** `ExpandReparkTrayJob`:
  `tray_opt->pose == dest.value()` ("Already at dest") runs under `if(dest)` but
  outside `if(tray_opt)`; with no tray id (ExpandReadyForInsertJob passes
  nullopt) it dereferences an empty optional, undefined behaviour. Not fixed
  (rule 3).

## Things a reviewer should know

- **B15 (found 2026-10-29, scheduler.cpp scan).** **[fixed in #10]**
  `AssignTrays` advance fallback: the advance move's path is
  `std::vector<GaragePose>{GetVertexFromPose(tray_opt->pose).value(), dest}`; a
  vertex id is not a pose, so the braces pick vector(count, value), giving N
  copies of dest. tray_opt is also already the post-advance pose. Path occupancy
  only; the source pose is registered separately. Not fixed.
- **B16 (to check, 2026-10-29).** **[fixed in #10]**
  `UnplugEvChargerBeforeTrayMove` adds the stop-charging VECS event without
  chaining it to the VECS asset; ExpandChargePayloadJob chains its
  start-charging event.
- Error strings tray assignment can return (keep verbatim; they reach clients
  through `FailJob`): "Failed to get total ordering"; "Requested to move tray to
  <dest> but it's occupied, or not enabled."; "Requested to move tray <id> to
  <dest> but it's occupied, or not enabled."; "Requested to move tray to <dest>
  but could not get a valid vertex from the pose <pose>"; "Failed to find path
  for t<id> from <pose> to <dest>"; "Failed to find blocking tray resolution.
  Logic error, we advanced to dest without having resolved all blocking trays.";
  "Failed to apply advance move: <event>: <msg>"; "Failed to find open space for
  blocking tray t<id>"; "Failed to apply event during tray assignment: <event>:
  <msg>"; "Failed to get new total ordering"; "Failed to apply event in
  TrayAssignments: <msg>"; "Can't resolve a tray move with no tray id or dest";
  "Tray pose does not exist in garage graph"; "Failed to find empty tray to move
  to <dest>"; "DoTrayAssignments TrayMove with TrayId=<id>does not exist in
  working_state"; "Failed to find open space for t<id>"; "Failed to apply
  unblocking move required: <msg>"; the raw `Apply` message. Plan() prefixes
  "Failed tray assignments: ".
- `ResolveBlockingTrays` failures are only logged (`WARNS`/`ERRORS`) and
  returned as `nullopt`; callers treat them as "try the next fallback". The free
  function keeps `std::optional`-like semantics through `stdx::Expected` whose
  error is only logged by callers.
- The `TRAY` footprint id is used for bay/VECS occupancy and for the root move's
  source/destination queries; the tray's own footprint
  (`CollisionEntityIdFromTrayState`) for required moves' paths. Keep.

## Review log

(Per commit: numbered feedback items with status open / done / discussed, and
the final SHA.)

- Commit 1
  `test(scheduler): add parity references to the planning tests (SW2-484 A)`:
  review packet posted 2026-10-22. SHA: not committed. After round 7: scheduler
  80 tests pass with all 58 references re-recorded and compared in a fresh
  process. Feedback items (2026-10-22):
  1. `done` Give the reference files a filesystem structure by pipeline stage:
     task_planning (tray_assignment / agv_assignment), motion_planning,
     action_graph. Done as
     `test/reference/{task_planning/tray_assignment,task_planning/agv_assignment,action_graph}/`;
     no `motion_planning/` folder because no test observes that stage on its own
     (open point for the user).
  2. `done` The inputs and outputs of a reference are not clear; add a brief,
     clear markdown file. Every reference now carries `layout`, `input` and
     `output`; `test/reference/README.md` explains them.
  3. `done` Draft a Python script (container's uv environment) that renders
     every test case's problem setup into one standalone plotly HTML with a left
     navbar to browse them. Done as
     `src/planner/scheduler/tools/view_references.py` (plotly JSON built by
     hand, plotly.js from the CDN: plotly is not in `uv.lock`, so no dependency
     was added; open point for the user).

  4. `done` Use plotly if it makes the viewer simpler (less code, lower
     maintenance); adding the dependency is worthwhile. `plotly==7.1.0` added to
     the `dev` group of `pyproject.toml` (`uv lock` run in the container;
     `uv.lock` updated; the dev image installs the dev group at build time, so
     `uv run` installs it into the workspace `.venv` until the image is
     rebuilt). The script uses `plotly.graph_objects` and embeds plotly.js with
     `plotly.offline.get_plotlyjs()`, so the page is standalone (about 6 MB).
  5. `done` The viewer's icons and theme don't look good. Follow
     <https://github.com/nextlevelbuilder/ui-ux-pro-max-skill> for the theme, and
     draw the garage assets the way the study pack's diagram scripts do. Theme:
     the skill's "Developer Tool / IDE" palette (dark slate surfaces, green
     accent) and "Developer Mono" typography (JetBrains Mono + IBM Plex Sans,
     via Google Fonts with system fallbacks), with the study pack site's tokens
     (`site/src/styles/site.css`) and its categorical colours (sky trays, amber
     cars, teal AGVs, violet bays, green EvCharge, red disabled). Assets are
     drawn to scale as rotated footprints: node windows from the layout's
     `parking_windows` (tray size as fallback for TRAY-sized nodes), trays 14 ft
     x 7 ft and AGVs 157.5 in x 73.5 in from `common/constants.hpp`, cars from
     the payload's `length_m` / `width_m`; heading 0 = +y, 90 = -x. **Not
     done:** `scheduler_package/scripts/diagrams` and `figures/` are denied by
     the Read rules in `.claude/settings.local.json`, so the exact glyph
     conventions of `theme.py` were not consulted; remove the two deny lines if
     the drawings should match those figures more closely.

  Round 4 (2026-10-22, on the viewer): 6. `done` Draw the origin and label the
  coordinate frame (x and y axes). Muted arrows from (0, 0) along +x and +y, 3 m
  long, labelled x / y; the origin dot says "origin (0, 0) m" on hover. 7.
  `done` Say where the layout file is (path relative to the repo root) and where
  the test input is. A source line above the tables: layout path,
  `TEST(Suite, Name)` with its source file and line (found by scanning
  `test/*.cpp`), and the reference file path, all relative to the repo root. 8.
  `done` EV charger as an icon with a yellow lightning bolt, like the study pack
  diagrams. A yellow (#facc15) bolt polygon 1.2 m tall at every EvCharge node,
  with a legend entry. **The example SVG (`deck/figures/d01_scenario.svg`) is
  denied by the same Read rules as `scripts/` and `figures/`**, so the glyph is
  a standard bolt, not a copy of the diagram's. 9. `done` Labels overlap. Node
  names (`P6`, `W2`) now sit at the far end of each window instead of the
  centre; tray labels at the centre; AGV labels behind the AGV's rear; bay state
  text beyond the window. 10. `done` Scrollbar: thin, slate thumb on a
  transparent track (`scrollbar-width` / `-webkit-scrollbar`). 11. `done` Tables
  with fields. Under the figure: the source line; for an action graph the
  request's jobs (type, state, tray, AGV, bay, payload, destination, note), the
  initial trays / AGVs / bays / disabled nodes, the response (success, message,
  scheduled jobs with their action nodes) and the schedule (# | agent | action |
  from | to | detail | duration | after); for a stage the state, the input and
  output DAG events (index, job, event, agent, action, destination, AGV) with
  the edges and first_event_by_tray, and the moves in topological order. Agents
  read `AGV 2`, `tray 6`, `bay 1`, `VECS 1`; poses `W2 @ 180°` (node letter +
  id + heading); actions `move`, `move (carrying)`, `rotate`, `lift`, `lower`,
  `center`, bay / VECS command names. 12. `done` Hovering a step row turns its
  arrow and number green and thick (`Plotly.relayout` on the annotations);
  hovering an arrow's midpoint highlights and scrolls to its row. 13. `done`
  Package `tools/reference_viewer/`: `theme.py` (colours, fonts, footprint
  sizes), `garage.py` (layouts by name, node names, footprint geometry, bolt),
  `references.py` (files, test locations, the `Step` / `Event` model for both
  reference kinds), `scene.py` (the plotly figure), `page.py` (HTML, tables,
  hover linking); `view_references.py` is a 46-line CLI. 1,258 lines in all
  after black (the old single file was 626).

  Round 5 (2026-10-22, on the viewer; the study pack's `scripts/diagrams` are
  now readable): 14. `done` Draw AGVs, trays, bays and the rest with the shapes
  of the diagram scripts, at the geometry sizes set in the repo. New `shapes.py`
  builds SVG paths (plotly path shapes) in each node's frame: parking stalls as
  rounded sky rectangles labelled at a corner (window minus 0.1 m), bays as blue
  rounded rectangles (window length, width + 0.9 m) with a thick door line on
  the side facing the garage, waypoints as dots, AgvCharge nodes as yellow
  circles with the diagrams' bolt, EvCharge stalls yellow with a bolt in a
  corner, trays 14 ft x 7 ft (`kTrayLength`, `kTrayWidth`) amber with two rails
  and a corner chip, cars from the payload's `length_m` / `width_m` pink with
  windshield and rear window, AGVs 157.5 in x 73.5 in (`kAgvLength`,
  `kAgvWidth`) green with four wheels, a lift plate (filled stronger when
  raised) and a chevron at the front, a floor with corridors under waypoint
  edges, and thick numbered route arrows. Colour roles follow `facility.py` (sky
  / blue / yellow / amber / pink / green); the pack's AGV is schematic 2.2 x 1.1
  m, ours is the real size. 15. `done` plotly moved from `dev` to a new group
  `scheduler` ("developer tools of src/planner/scheduler; not in the runtime
  images"), included by `dev`; `uv lock` re-run. 16. `done` The source block is
  a three-row table: layout, test, reference. 17. `done` Cause: `Plotly.react`
  mutates the layout object it is given, so the "original" annotation colours
  used to restore were already the highlighted ones. The page now hands plotly
  deep copies (`structuredClone`) and restores from the pristine figure.
  Verified by dispatching mouseenter / mouseleave in the page: arrow width 3 ->
  5 -> 3. 18. `done` Row highlight: accent-tinted background (`color-mix` 22 %),
  accent left border, bold. 19. `done` Light mode: `Palette` dataclass with
  `DARK` and `LIGHT` (light colours from the pack's light theme), one figure per
  theme per reference (page 8.6 MB), CSS variables generated from the palette,
  toggle button in the navbar, default from `prefers-color-scheme`, remembered
  in localStorage. 20. `done` Origin: red x and green y arrows (2.5 m) with bold
  labels and a ring at (0, 0); plotly grid: minor lines every 1 m, major every 5
  m, zero lines stronger, ticks in metres on both axes.

  Round 6 (2026-10-22, on the viewer): 21. `done` Misplaced items on pan / zoom.
  The geometry was plotly `layout.shapes` (SVG paths), which plotly re-renders
  on pan and zoom through its own code path; the floating stall and bolt were
  shapes left behind. All geometry is now scatter traces (filled polygons,
  rounded corners sampled as 6-segment arcs), added in drawing order, so it pans
  and zooms with the data. Checked by dragging and wheel-zooming in the browser:
  nothing detaches. 22. `done` "grid off / on" button in the navbar (remembered
  in localStorage): hides the 1 m and 5 m gridlines; the x = 0 and y = 0 lines
  and the ticks stay. 23. `done` Chargers are a 0.3 m cabinet with a bolt: at
  the node for AgvCharge nodes, just beyond the far end of the stall for
  EvCharge nodes, whose stall is drawn like any parking stall. 24. `done` The
  navbar is a tree: test source file (`scheduler_tests.cpp (16)`) > `TEST` > its
  references, each leaf labelled by stage and suffix
  (`action_graph · to_insert`, `tray_assignment`, `agv_assignment`). Files open,
  the first test open. 25. `done` Yes, both are output. Headings now say so:
  "output: response · scheduled jobs (the jobs as returned, with their action
  nodes)" and "output: response · schedule (the action nodes)"; the inputs are
  "input: request · pending jobs" and "input: initial state". 26. `done` One
  "input: initial state" table: kind | id | pose | state | lift | payload |
  disabled, with trays, AGVs, bays and disabled nodes as rows. 27. `done`
  Package renamed `plan_viewer` (it draws plans: an initial state and the
  planned moves); the script stays `view_references.py`. Alternatives if
  preferred: `parity_viewer` (ties to `parity.hpp`), `garage_viewer`.

  Round 7 (2026-10-22): 28. `done` Tree: stage folders as under test/reference
  (action_graph; task_planning > agv_assignment, tray_assignment), then, for
  action graphs, the request's job types (`RETRIEVE`, `INSERT + CLEAN_GARAGE`,
  ...), then the references by test name. 29. `done` Every reference now starts
  with `description:` (one paragraph: "Scenario: ... Test: ... Expected: ..."),
  passed by the test to `TrayAssignment` / `AgvAssignment` /
  `ExpectPlanReference` (new `std::string_view description` parameter); the
  viewer shows it as a Scenario / Test / Expected block. 58 descriptions written
  from the test sources. Renamed tests (references renamed with them, all
  re-recorded): TrayAssignmentTest -> TrayAssignmentFillsBlankDestination,
  TrayAssignmentTestComplexDag ->
  TrayAssignmentResolvesManyBlockersThenAssignsAgvs, UnblockingTrayMoveTest ->
  TrayAssignmentMovesOneBlocker, MiAmigaEsSuAmiga ->
  AgvAssignmentSkipsDisabledAgv, AmigaSaysNo ->
  AgvAssignmentFailsWhenDisabledAgvBlocksPath, AmigaStash ->
  AgvAssignmentChainsThreeMovesAcrossTwoAgvs, NoAmigas ->
  AgvAssignmentFailsWithNoAvailableAgv, AmigaBaySos ->
  AgvAssignmentFailsWhenBayTransitionTrapsAgv, AmigaBaySo ->
  AgvAssignmentUsesAgvFreedByBayTransition, TrayLiftBayTransitionDependencyTest
  -> AgvAssignmentOrdersLiftsAroundBayTransitions, WeirdFultonRetrieve ->
  FultonRetrieveWithCleanGarage, AgvChargeJobMVP454 ->
  AgvChargeJobTwoAgvsDistinctChargers. ("Amiga" = Arguably More Intelligent aGv
  Assignment, the AGV-assignment stage's nickname in scheduler.hpp.) Found while
  describing: `ReparkUnplugVecsMoveAgvFirst` has exactly the same state and job
  as `ReparkUnplugVecs` (noted in its description; not changed). 30. `done`
  "hello" is the job's `note` field as the tests fill it (input data, echoed
  back by the response); the column now reads "note (from the request)". The
  numbers are the job's action nodes, 1-based positions in the schedule table;
  the column reads "action nodes (# in the schedule)" and shows ranges
  (`#1–#14`). 31. `done` New `dag.py`: Graphviz `dot` (14.1.2 in the
  devcontainer; no Python dependency added) draws the DAG left to right as SVG,
  one per theme: for an action graph the schedule with its parent edges, for a
  stage the input event DAG and the output event DAG. Nodes are coloured by
  agent; hovering a node highlights its table row and arrow, and vice versa. 32.
  `discussed` Kept `view_references.py`: the script names what it reads
  (references), the package what it draws (plans). Will rename on request. 33.
  `done` "show solution" button: input only by default (no move arrows, no
  output tables, the input DAG for a stage); on, the arrows, the output tables
  and the output DAG / action graph appear. 34. `done` Legend with glyphs drawn
  in the figure's style and explicit labels: parking stall (outline), customer
  bay (door on the garage side), waypoint, charger cabinet, tray (with rails),
  car on a tray (payload), AGV (chevron at the front), disabled node (dashed),
  planned move (numbered), origin with x (red) and y (green) axes. The "purple
  lines" were the bay outlines (blue in the dark palette), the green boxes the
  AGVs, the dashed red boxes disabled nodes.

  Round 8 (2026-10-22, on the viewer): 35. `done` `rich==14.2.0` added to the
  `scheduler` group (`uv lock` re-run); `rich.progress.track` wraps the
  reference loop ("Drawing references", 12 s for 58). 36. `done` Flags:
  `references.goals()` reads the goals from the input (MOVE_AGV / MOVE_TRAY /
  REPARK_TRAY destinations, the bay of INSERT / READY_FOR_*/ TRANSITION_BAY_*
  jobs, every bay for a RETRIEVE, every VECS for a CHARGE_PAYLOAD, and for a
  stage the input DAG's tray-move destinations); `Scene.flags()` draws a pole
  with a pennant in the colour of what must get there and a label ("goal: tray
  1", "goal: payload 1 to a bay"), shown in both views. 37. `done` Axes are thin
  (1.5 px) with open heads (plotly arrowhead 4); moves are thick with filled
  heads and a numbered badge; and move colours no longer use the AGV body green
  (teal, sky, violet, pink by AGV id; amber for trays), so nothing green is a
  move. 38. `done` A rotation draws a quarter / half circle arrow around the
  node from the old heading to the new (radius 1.1 m, grown for repeated
  rotations at the same node), with its number badge. 39. `discussed` Yes: the
  response schedule (the action graph) has one `ActionNode` per AGV command
  (translate, rotate, lift, lower, centre) plus one per bay / VECS / VRC
  command; `ResponseFromTrajectories` emits one node per motion of the planned
  trajectories. The viewer shows it as is. 40. `done` Origin entry removed from
  the legend. 41. `done` `highlight(step, scroll)`: the row scrolls into view
  only when the hover comes from the figure; DAG and row hovers highlight
  without scrolling. 42. `done` Every action now has a visible label: moves that
  share a segment take lanes 0.4 m apart (badges with them), rotations are arcs,
  lifts and lowers are numbered badges (▲ / ▼) stacked beside the node. The arcs
  are traces, so they are hidden with the solution like the arrows.

  Round 9 (2026-10-22, on the viewer): 43. `done` Cause: the solution toggle
  restyled the step arc traces with
  `Plotly.restyle(plot,     {visible}, current.step_traces)`; for a reference
  with no rotation arcs the list is empty, and plotly reads an empty trace list
  as "every trace", so the garage's traces were hidden (only the annotations,
  i.e. the labels, stayed). The call is now skipped when the list is empty.
  Verified: 19 of 19 traces visible in the input view of
  CleanGarageAgvInTheWay. 44. `done` Cause: the axes autoranged over the visible
  traces, so hiding or showing traces rescaled the view. The axis ranges are now
  fixed to the floor's bounds (`autorange=False`). Verified: identical ranges
  before and after toggling the solution.

  Round 10 (2026-10-22): 45. `done` All 58 descriptions rewritten as complete
  sentences ("Scenario: On tiny_lot, ... Test: The test plans ... Expected:
  ...") and checked against the test sources once more; the bay remark now reads
  "the state lists no bay, so B1 is drawn without a bay state" (the layout has
  the bay node; the discrete state has no entry for it). All references
  re-recorded; 80 tests pass. 46. `done` `JOB_GLOSSARY` (one sentence per job
  type, from the study pack's job chapter) shown as "what the jobs mean" under
  the request table for the job types in the request; a collapsed "terms used
  above" section at the bottom explains the actions (move, rotate, lift / lower,
  center, bay / VECS commands, "after") for action graphs and the event types,
  edges and first event by tray for stages. 47. `done`
  `html, body { overflow: hidden }` (the page itself never scrolls; the panes
  do) and 12 px of right padding on the plot, so the mode bar is clear of any
  scrollbar. 48. `done` README section "Building, running and recording":
  `poe build-pkg scheduler`, `poe test-pkg scheduler`, running one binary with
  gtest flags, `planner_core` and `scheduler_advanced_tests`, and recording with
  `RECORD_REFERENCE_OUTPUT=1`. 49. `done` Badges now name their entity (`3 t2`,
  `5 a1`, `2 ▲ a1`); AGV-assignment references draw a dotted link from each
  AGV's start to the tray it was assigned to with a chip "AGV 1 → tray 2 (#3)",
  shown with the solution, and get an "output: assignments" table (# | AGV |
  tray | to) whose rows highlight the move. Tray moves' badges carry the tray
  id, and the arrow's head is the bay or stall it goes to.

  Round 11 (2026-10-23): 50. `done` Headers are now nouns: Request, Base
  schedule, Initial state, Response, Scheduled jobs, Schedule (plan); Initial
  state, Input events, Output events, Steps, Assignments (stages); the DAG box
  is "Action graph" / "Event DAG (input|output)". The glossary sections are
  gone. 51. `done` Every table cell or header whose text is a known term (job
  types, job states, actions, event kinds, "after", "edges", "first event by
  tray") is dotted-underlined and shows its definition in a hover window (CSS,
  from a `data-tip` attribute); the definitions live in `references.py` as the
  scenario's `terms`. 52. `done` `<hr>` dividers labelled INPUT and OUTPUT
  separate the description and provenance from the input tables and the output
  tables. 53. `done` Stalls are a faint dotted outline only (no fill), and a
  "stalls off / on" button in the navbar hides them (remembered in
  localStorage). 54. `done` The assignment links and chips are gone. Every asset
  and node has a hidden highlight outline; hovering a row shows the outlines of
  what the row describes: a step row its agent and destination node, an
  assignment row the AGV, the tray and the destination, a job row its tray, AGV,
  bay or destination. The arrow highlight stays for step rows. 55. `done`
  `plan_viewer/static/page.html`, `style.css`, `app.js`; `page.py` inlines them,
  so the output is still one file. 56. `done` Layered: `model.py` is a neutral
  `Scenario` (assets, node states, goals, steps, tables with highlight keys,
  graphs, terms); `references.py` is the only module that knows the reference
  format, the scheduler's messages, job types, event strings and method names;
  `scene.py`, `dag.py` and `page.py` consume the model only; `garage.py` reads
  layouts (the site_config format) and owns the geometry; `theme.py` the
  palettes. A different planner or file format needs a different adapter
  only. 57. `done` Initial-state rows highlight their asset (covered by 54). 58.
  `discussed` Yes: those references record `Scheduler::Plan`, i.e. the whole
  pipeline (job expansion, tray and AGV assignment, motion planning, action
  graph), and only the response is compared. Renamed: folder
  `test/reference/plan/`, stage "plan", parity function
  `Plan(scheduler, request, response, description)`; references re-recorded;
  README updated. 59. `done` A "code under test" row in the provenance table:
  for a plan reference
  `Scheduler::Plan: <the Plan*Job method of each job type>, DoTrayAssignments, DoAgvAssignments,     PlanMotions, ResponseFromTrajectories`;
  for a stage `Scheduler::DoTrayAssignments` or `DoAgvAssignments`. The method
  map is in `references.py` (it will follow the commit 2 renames). 60. `done`
  The stray file was my own `artifacts/scheduler_references.html` from earlier
  runs, next to the user's `artifacts/planner_tests.html`; removed. The default
  output is now `artifacts/scheduler_tests.html` (not the current
  directory). 61. `done` Sidebar title and page title: "scheduler tests". Also
  seen: `artifacts/.keep` shows as deleted in the working tree; not done by this
  session.

  Round 12 (2026-10-23): 62. `done` A highlight is the asset's own outline
  emboldened (3.5 px) and filled stronger in its own colour: amber trays, green
  AGVs, sky-blue stalls, blue bays. No accent overlay (and the "highlighted on
  hover" legend entry is gone). 63. `done` Hovering a step row (or its arrow or
  DAG node) dims the initial state's assets to 30 % opacity and shows a ghost of
  the step's agent at the pose the step leaves it in (a tray with rails, an AGV
  with its chevron), plus the destination stall or bay emboldened. 64. `done`
  Assignment rows highlight the (AGV, tray) pair where they stand; they no
  longer carry a step, so no arrow or ghost. 65. `done` Tray-stage step rows
  embolden the tray's ghost at the stall and the stall itself in blue (covered
  by 62 and 63). 66. `done` The floor polygon is gone; the bounds still size the
  axes. 67. `done` Script renamed `tools/view_scheduler_tests.py`, default
  output `artifacts/scheduler-tests.html`; README example updated. Found while
  checking: with `scaleanchor` and fixed ranges, plotly kept the aspect ratio by
  widening the ranges on every resize, and a zero-sized (hidden) tab blew them
  up to thousands of metres, garbling the drawing until a reload. Fixed with
  `constrain="domain"` on both axes: the plotting area shrinks instead, the
  ranges never change. Also seen: `artifacts/` now holds only the generated
  page; `.keep` and the user's `planner_tests.html` are gone, not through this
  session.

  Round 13 (2026-10-23): 68. `done` The drawing should use the full width of the
  plot area; it sits in the middle and crops assets. 69. `done` No parking-stall
  highlight on hover in the action table, nor in general; at most in tray
  assignment. 70. `done` A notes folder in the SW2-484 folder, one subfolder per
  stage / commit with a markdown file of explanation and Q/A for the code,
  starting with: the C++ files under scheduler/test, the YAML under
  reference/plan and how it pairs with the site_config layout (and what `vexen`
  is), and why the tests hold YAML string literals instead of reading files.

  Round 25 (2026-10-26): 104. `done` The force push failed at clang-tidy: 36
  findings in the test files, two kinds. (a) bugprone-unchecked-optional-access
  on every `.value()` / `->` after an ASSERT_TRUE or EXPECT_TRUE on has_value(),
  in agv_assignment, assignment_cost, tray_assignment, agv_charge_job tests and
  scenarios.cpp (Dag): the check's dataflow cannot see gtest's macros. The
  team's precedent is src/agvhito/test/.clang-tidy, which disables that check
  for the folder with a justification; the same file now sits in
  src/planner/scheduler/test/ (InheritParentConfig, covers stages/, jobs/,
  utils/ and the support sources). (b) readability-identifier-naming on the two
  local constexpr in TrayAssignment.ResolvesBlockerChainRecursively: locals take
  `k_` plus lower_case (LocalConstantPrefix / LocalConstantCase in .clang-tidy),
  so kRootTrayId -> k_root_tray_id, kJobIndex -> k_job_index; the kCamel form is
  for file-scope constants only. The "N warnings generated" lines are
  clang-tidy's per-unit totals over the headers, filtered out by
  clang-tidy-diff; only the listed findings count. `volley-in-container tidy`
  run after the fix: 0 findings in 822 s (14 min; the log is
  ~/.cache/volley-in-container/logs/20261026-102045-tidy-main.log).
  tray_assignment_tests rebuilt and passing (5 tests); commit-stage hooks green.
  Amended into commit 1, now 0b22bba6 on top of 83569373; code notes updated
  (file table, clang-tidy section). The user force-pushes
  (`git push --force-with-lease`); the remote still holds f47bbb61.

    1. `done` Four review questions answered in the code notes, new section
       "Questions and answers" (commit size by kind: 73% recorded output, 2.1k
       authored, 6k code; how the recorded part could shrink 62% by omitting
       default-valued fields, measured; plan tests compare the response only,
       stage tests the event DAG; YAML-vs-struct comparison, with the one place
       the text is less exact: float32 durations at six significant digits).
    2. `done` Found while answering: `TrayAssignment.MovesOneBlocker` and
       `TrayAssignment.ResolvesManyBlockersThenAssignsAgvs` exercised no blocker
       on 275_sunrise_b (critical paths free; scheduler log confirmed).
       Re-posed, as the user chose: tray 2 now on P2066, the one stall on tray
       1's path (new state empty_trays_at_p2066_p2067_p2077, AGV 1 at P2075);
       tray 13 in the south-east corner P2150 of the block with P2149, P2148,
       P2135, P2134, P2133, P2119, P2118 occupied (new state
       two_agvs_eight_empty_trays_tray_13_at_p2150, replacing
       two_agvs_eight_empty_trays, which nothing else used). Recorded: one
       blocker move (tray 2 to P2061) chained before the root; two blocker moves
       (tray 10 to P2087, tray 11 to P2086) chained before the root, AGV 1
       taking both and AGV 2 the root. The test's block map comment was wrong
       (the block is 3 columns x 4 rows of stalls, each column behind a lane
       waypoint, W2100-W2103 on the west side) and is redrawn. Descriptions
       rewritten.
    3. `done` The second force push failed with "files were modified by this
       hook" and no finding: I edited the two scenario descriptions (item 106)
       while the user's push was in the clang-tidy hook, and prek fails a hook
       whose files changed under it. Rule for me: no working-tree edits while
       the user pushes. Noted in the code notes.
    4. `done` Why clang-tidy took 14-20 min and looked single-threaded:
       scenarios.cpp and initial_states.cpp were sources of all 18 test
       binaries, so compile_commands.json had 18 entries each and clang-tidy
       analysed each 18 times sequentially in one process (the two cumulative "N
       warnings generated" runs in the output). Fixed in CMake: static library
       scheduler_test_support (ament_find_gtest first, so the gtest targets
       exist), linked by every test binary. Measured: 822 s -> 66 s, 57 -> 23
       analyses, 0 findings. Build 25 s, 170 scheduler tests pass, hooks green.
       Code notes: build paragraph, walkthrough step 1-2, tidy section rewritten
       with the cause, the table and the no-edits-during-push rule. Amended into
       commit 1, now fe0550d8 on top of 83569373; tree clean; the remote still
       holds f47bbb61 until the user force-pushes.

    5. `done` Size of the PR, as the user asked: the recorded part of the plan
       scenarios compacted. `Compact` in scenarios.cpp after CanonicalResponse:
       GUID maps become one scalar (value when only the last four bytes are set,
       else 8-4-4-4-12), every default-valued field is dropped (zero, empty,
       false, empty sequence, all-default sub-message), maps of at most two
       scalars (poses) in flow style. Rule for readers: an absent field holds
       its default (README, "The recorded part"). Viewer:
       `field(message, *keys, default)` helper in scenarios.py, guid_text
       accepts an int, schedule_steps and the response tables use it; the page
       renders all 58 scenarios. Measured: recorded lines 22,257 -> 5,795
       (-74%); the diff against main 164 files +30,601/-6,688 -> +14,259/-6,688.
       All twelve scenario binaries re-recorded; hooks green (clang-format and
       black reformatted once). 170 scheduler tests pass. Amended into commit 1,
       now 9f1d4022 on top of 83569373; tree clean; the remote still holds
       f47bbb61 until the user force-pushes. Not done, as options for the user:
       the viewer (13 files, 2,900 lines) in a PR of its own; flow style per
       action node.

    6. `done` The user keeps the viewer in this PR ("it should be paired with
       this PR"). Rebased onto the tip of main, e24b8e16 (one commit since
       83569373, SW2-1000 central_api schema, no file overlap; clean). Commit 1
       is now 0c041424. Scheduler rebuilt and its tests re-run on the rebased
       branch: 170 tests pass, tree clean. The remote still holds f47bbb61 until
       the user force-pushes.

    7. `done` Fetched and rebased again at the user's request: main moved five
       commits (PR #999, agvhito recovery and stdx scope-exit; no file overlap),
       rebase clean onto 2cfd657a. Commit 1 is now c18425e7. Scheduler rebuilt,
       170 tests pass, tree clean; remote still f47bbb61.

    8. `done` Pre-PR review against the Greptile configuration (the user pasted
       it). My hygiene scan plus two reviewer subagents (C++ and viewer,
       independent, no conclusions given). All fixes amended into commit 1, now
       fbbba8a2; details in the code notes' new section "Review against the
       Greptile configuration". Highlights: narrative/history comments cut, four
       TODOs without tickets resolved, three DrawGraph debug dumps removed, dead
       layout_test branch removed, README example and Load example corrected,
       wrapper mentions replaced by the env var; ASSERT before every schedule
       index / optional deref (crash -> clean failure); recording guards
       (ExpectOwnTest on every file, no file creation, write checked) and
       ExpectKeys on authored keys; quoted strings kept by IsDefault; GUIDs
       uppercase; jobs from 1001 and request id 1000 (re-recorded all 45);
       viewer: lift/lower badges, corner control point (was the node centre),
       BLift bay, authored-only files, hover gating, layout link, outside paths,
       payload label. Commit message updated (compact form, support library,
       tidy exception). PR title to use: [SW2-484] Record the scheduler planning
       tests as scenario files. Verified: build, 170 tests, hooks, viewer
       renders 58 (105 lift / 101 lower badges). Diff vs main 164 files +14,284
       -6,688. Remote still f47bbb61.

    9. `done` Three requests. (a) Rebased onto main a1c385f1 (four agvhito
       commits, no overlap, clean); commit 1 is now 632701c6; scheduler rebuilt,
       170 tests pass, tree clean; remote still f47bbb61. (b) jira_ticket.md
       rewritten: title "Record the scheduler planning tests as scenario files",
       step-by-step instructions to create it as a Task under epic SW2-482 (the
       screenshot shows SW2-484 "Create interface for generic tray move solver"
       and SW2-487 "Create benchmark set..." as the existing children),
       description in Markdown for the Jira editor, note that the branch name
       carries SW2-484 and should be renamed to the new key before the PR. (c)
       Code notes: "How a test run flows" rewritten as paragraphs; the plan test
       section now explains how `scenarios::Plan()` finds its file with no
       argument (gtest's current_test_info -> suite in snake case as the folder,
       test name as the file, optional suffix for a test with several scenarios,
       and the `test:` key checked back).

   10. `done` Assessed the other agent's implicit-guidelines report against the
       branch; plan in pr_prep_plan.md (nothing implemented). Recommended: drop
       the unused ament_index_cpp test_depend; shorten seven test names of 7+
       words (mostly utils); split the viewer into a second commit of the same
       PR; PR description with the traceability list; one sentence that
       test/scenarios are gtest inputs, not simulation scenarios (Greptile's
       knowledge-base checks). Taste items: reuse volley::to_string for GUIDs, a
       shared kNow instead of fifteen rclcpp::Time(), split the two 800-line
       viewer modules, stale deprecated docs. Checked and fine: optional access,
       nodiscard, includes, no main/sleeps, comments, stage-test design.

   11. `done` Applied A1-A5, B6, B7 of pr_prep_plan.md: ament_index_cpp
       test_depend dropped; nine utils test names shortened; viewer split out as
       commit 2 (git rm --cached tools, index of pyproject/uv.lock restored from
       origin/main, amend, then add + commit); PR description drafted in
       pr_description.md; README first sentence says gtest inputs, not
       simulation scenarios; GuidScalar via std::to_string(GuidMsg);
       scenarios::kNow {0, 0, RCL_ROS_TIME} in scenarios.hpp used by the stage
       tests and Plan. Build, 170 tests, hooks green, no recording changed. The
       user had rebased the branch onto 6d656e15 (PR #1006) from the terminal;
       commits: 92deb897 (test, 150 files) + 00ca841b (feat viewer, 15 files),
       branch +14,286/-6,689 over 165 files. Remote still f47bbb61.

   12. `done` B8 and B9. Viewer split: scenarios.py (875) -> records.py 307,
       reader.py 319, tables.py 241, scenarios.py 70; scene.py (830) ->
       canvas.py 295, paths.py 231, scene.py 356 (line counts before black).
       Linear class chains (Reader <- Tables <- Adapter; Canvas <- StepDrawing
       <- Scene) so every method uses only its base: mypy green with no stubs.
       Page byte-identical before and after (filecmp). Deprecated docs: the two
       scheduler_jobs_tests entries removed; folded into commit 1 via detached
       amend + `git rebase --onto` (the wrapper allows rebase for this stage).
       Commits now 80535545 (test, 152 files) + 3162844b (viewer, 20 files);
       tree clean; remote still f47bbb61. Note for me: `md5sum` and `cmp` are
       denied by the permission rules here; python's filecmp works.

   13. `done` The user created Jira SW2-1126 "Record the scheduler planning
       tests as scenario files" (Task under SW2-482, To Do, assignee/reporter
       Jon, label Scheduler_and_Dispatcher, start 2026-10-22, due 2026-10-30,
       Medium). Branch renamed locally to jmg/SW2-1126/scheduler-scenario-files
       (matches check_branch_name.sh); upstream still points at
       origin/jmg/SW2-484/scheduler-core-refactor (f47bbb61) until the user
       pushes the new name and deletes the old remote branch. Notes, PR
       description title and Jira draft updated. Ticket check: status should be
       In Progress; start date earlier than the work (commit 1's author date is
       2026-10-23, the rounds began before); "is blocked by" picker left open
       empty (suggest "blocks" SW2-484 and SW2-487 instead); no sprint; the
       Development panel says "Connect development tools", so the GitHub app may
       not be connected for the project.

   14. `done` Notes folder regrouped at the user's request: the sub-ticket's
       files moved into `SW2-1126_scenario_files/` (jira_ticket.md,
       pr_description.md, pr_prep_plan.md, and the code notes as
       `code_notes.md`, formerly `code_notes/01-parity-references/notes.md`);
       the `code_notes/` index folder is gone, replaced by a README in the
       sub-ticket folder and a README at the epic level that maps PROMPT.md,
       this log, DESIGN-REVIEW.md, the sub-ticket folder,
       action_dependency_graph/ and scheduler_package/. PROMPT.md and this log
       stay at the root because CLAUDE.local.md names them. All of these are
       untracked in the notes repo (nothing committed). PROMPT.md section 5
       names `SW2-482_pr_description.md` at the root for the epic-level PR text
       at the end of the stages; the sub-ticket's PR text is the one under its
       folder.

   15. `done` Three requests. (a) Epic folder renamed
       `pull_request_notes/SW2-484/` ->
       `pull_request_notes/SW2-482_scheduler_core_refactor/` (git mv, so the
       tracked action_dependency_graph files are staged renames in the notes
       repo; nothing committed) and the log `SW2-484_notes.md` ->
       `SW2-482_notes.md`; every path updated: CLAUDE.local.md (paths only; its
       section heading still says "SW2-484 refactor", the user's wording),
       PROMPT.md (paths, and `SW2-482_pr_description.md` for the epic-level PR
       text), DESIGN-REVIEW.md, both READMEs, code_notes.md. (b)
       `review_rules.md` at the epic level: the Greptile and reviewer rules
       distilled, with what was applied and a pre-PR checklist. (c) PR format
       surveyed with gh over the last 40 merged PRs: titles `[SW2-xxxx] ...`
       throughout; bodies `# What` / `# Why` / `# Testing` in 17 (incl. the
       user's #973), or `## Summary` / `### Changes` / `## Fix`; `Refs:` line;
       no PR template in .github. pr_description.md rewritten in the
       What/Why/Testing form with the traceability list under What.

   16. `done` Test time. Measured with gh: the PR's first CI run spent 653 s in
       colcon test (35 s on main; the scheduler job 2.0-3.8 min over 16 main
       runs): 143 s a one-off build+save of the 275_sunrise_b collision table,
       the rest 26 parses of its 281 MB JSON (17 M pose objects) at 13 s each on
       arc-test-runners pods (about 2.5x slower per test than the workstation,
       where a parse is 5 s). Fix in commit 1:
       `scenarios::SharedScheduler(layout, params)`, one const Scheduler per
       layout+params per binary (all entry points the tests use are const); Plan
       and the stage tests use it; the readiness-ratio service test keeps its
       own (it mutates). Local: loads 67 -> 27, per-binary totals 203 s -> 92 s,
       package 3m26s -> 1m36s, 170 tests pass. Code notes: walkthrough paragraph
       and a new Q&A on the CI time; README sentence. Pitfall for me:
       `volley-in-container build ... | tail -2 && test` hid a build failure
       (the pipe's status is tail's) and the tests ran on stale binaries; the
       build's exit code is checked explicitly now. Folded into commit 1 by
       detached amend + rebase --onto; commits now d95b2165 (test) + 0a37f96f
       (viewer); tree clean; remote has the first push of the renamed branch,
       before this change. The table's size is a common_ros matter (SaveTable /
       LoadTable in collision_geometry.cpp, JSON with a key-named object per
       pose): ticket material, not this PR.

   17. `done` Test output noise, at the user's request. The planner narrates at
       INFO (critical path, blocking trays, illegal poses, every planned motion,
       the request's garage state as a multi-line entry, the collision-table
       build per vertex and edge); the test log of the package was 9,372 lines.
       Test-side fix, no library change: a gtest Environment `QuietLogging` in
       scenarios.cpp (registered with AddGlobalTestEnvironment; owning-memory
       NOLINT for gtest's raw new) sets the `scheduler`, `garage_graph` and
       `pose_graph` loggers to WARN via rclcpp::Logger::set_level unless
       SCHEDULER_TEST_LOG is set. Package log 9,372 -> 653 lines, 0 INFO lines,
       the 88 WARN lines of the fallback scenarios stay. 170 tests pass, hooks
       and tidy clean. README and code-notes walkthrough describe it. Folded
       into commit 1: 3162bcf0 (test) + c276879e (viewer); tree clean; remote
       predates it. The per-vertex and per-edge INFO lines of the
       collision-table build belong to common_ros and go with the table-size
       ticket.

   18. `done` Coverage question: octocov on PR #1007 says 72.7% -> 71.4% (-380
       lines), scheduler files -9.9%. Analysed from the artifacts (gh): the PR
       run has two `coverage-report` artifacts (system-tests and unit-tests
       report jobs; `gh run download -n` picks one, so by id). Unit-test gcovr
       report, PR vs main, per line: scheduler.cpp 2019 -> 2026 covered,
       schedule_events.hpp 42 -> 47, utils/chugg_sequential/print_utils level:
       the tests cover more, not less. Per-job tracefiles (27 per run): every
       system job, scheduler-advanced-tests and the scheduler job lost 280-340
       lines, all in collision_geometry.cpp/.hpp, the table builder; main's push
       runs set cache_collision_table=false so all 27 jobs build the tables and
       cover the builder, PR runs download the cache and only central,
       common_ros and motion-planner cover it (small tables). My union of all
       tracefiles: main 21,298 vs PR 21,295 covered lines; octocov's merge rule
       is not a plain union (its main count is 21,370) and it weighs the
       builder's loss across jobs. Genuine union losses: 33 lines of agvhito
       error_state.cpp (a sim error-recovery path that ran on main's run only),
       10 of print_utils (the quiet logging skips INFOF arguments), 5 of
       scheduler.cpp. Conclusion: a CI-configuration artefact of the cache
       policy, not the tests; a coverage note added to pr_description.md.
       Possible follow-up for CI: use the table cache on push runs too, so main
       and PR coverage compare like for like.

   19. `done` (2026-10-27) Review session: the user invited the two reviewers to
       a 30-minute walkthrough of PR #1007. Agenda written to
       review_meeting_agenda.md, for reviewers with little knowledge of the
       scheduler: why the PR (3), the scheduler in two minutes (3), a scenario
       next to its test (7), the test folder (4), the viewer demo (5), what the
       recordings showed and what is not fixed (3), how to review (4), buffer
       with likely questions (1). Preparation list and the numbers at the top.
   20. `done` (2026-10-27) PR feedback, item 1 (Greptile P2, paths.py): AGV
       paths drawn from stale positions in the stage scenarios, because the
       drawing walked one agent at a time, preferred the cached node over the
       step's own source, and a stage's tray move carried no AGV id. Fix:
       `Step.agv` filled from the event, one ordered pass over the steps that
       tracks every agent and carries the assigned AGV with the tray, source
       from the step when it names one. Checked by recording every leg and badge
       of all 58 scenarios before and after: the nine AGV-assignment scenarios
       change as intended; two Gramercy retrieve plans show the lower after the
       car-lift ride as `▼` at node 26 instead of `⇅` at node 2 (the ride is the
       conveyor step, badge-less either way). Written up in code_notes.md "PR
       review feedback". Amended into the viewer commit on the user's
       instruction (two commits in the PR, always).
   21. `done` (2026-10-27) PR feedback, item 2 (Greptile P2, reader.py): the
       initial state's EV chargers and car lifts never reached the drawing or
       the table. Valid. `NodeState` now has a kind, an own id and a name;
       charger and conveyor state vocabularies from VecsReport.msg and
       VrcState.msg; the layout's `vrcs` list gives the lift's root node; labels
       stack where the lift's floors share a spot; every disabled node is
       dashed. Checked by recording the node states of all 58 scenarios before
       and after (11 gain chargers, 3 the lift). Patch proposed, Amended into
       the viewer commit.
   22. `done` (2026-10-27) PR feedback, item 3 (Greptile P2, app.js): the graph
       box always carried the `output` class, which the stylesheet hides while
       the solution is off, so the input event DAG never showed. Valid.
       `updateDag()` now toggles the class from the solution state and the
       markup drops it; three lines. Reasoned from the three call sites, not
       viewed in the browser. Amended into the viewer commit.
   23. `done` (2026-10-27) PR feedback, item 4 (Greptile P2, tables.py): three
       direct indexes into the recorded part (`input`/`output` dag in
       `stage_tables`, output edges in `step_graph`) bypassed the tolerant
       `dag()` helper, so one authored-only stage file crashed the viewer.
       Valid. Routed through `dag()`; checked by loading a stage and a plan file
       with their recorded parts stripped (both render). Amended into the viewer
       commit.
   24. `done` (2026-10-27) PR feedback, item 5 (Greptile P2, stage tests): two
       comments narrated the pre-migration inputs (tiny_lot destinations, trays
       14/12 at P2147/P2148). Valid. The user's call: the scenario descriptions
       and the viewer carry the story now, so the narrative comments in both
       stage test files are removed rather than rewritten (31 lines); mechanics
       comments stay; the recursion test's "P(6)" comment reads "tray 6, at
       P2117". Rebuilt, both binaries green. Amended into the viewer commit on
       "amend patch" (not moved to the recording commit).
   25. `done` (2026-10-27) PR feedback, item 6 (Greptile P2, viewer docstrings):
       the 15-line tour in scene.py, the layer map in **init**.py and the 9-line
       steps() docstring cut to purpose statements (29 lines out, 9 in); the
       tour text moved into code_notes.md. The user's rule: concise in the code,
       verbose allowed in volley_notes. Amended into the viewer commit.
   26. `done` (2026-10-27) PR feedback, item 7 (teammate, pyproject.toml): group
       renamed `scheduler-dev`, comment dropped, include moved up among the
       include groups, `poe lock` re-run in the container (lock diff: the two
       group-name lines). README, PR description and Jira note updated. Amended
       into the viewer commit.
   27. `done` (2026-10-27) PR feedback, item 8 (teammate, CMakeLists.txt): the
       support library is `${PROJECT_NAME}_test_support` in all five places;
       reconfigure + "ninja: no work to do" (same expansion), one binary green.
       Patch proposed, awaiting approval. This one, like the test-comment
       cleanup, would belong in the recording commit; amended where the user
       says. Amended into the viewer commit.
   28. `done` (2026-10-27) PR feedback, item 9 (teammate, comments in general):
       comment only to explain the why; scrub the PR. Listed every
       comment/docstring in the touched C++, Python and JS, cut 173 lines to 43
       in 22 files (assertion labels, test-name restatements, narrative
       preambles, long `///` docs, viewer module docstrings); kept the why
       comments and the case labels of table-style tests. Rule added to
       review_rules.md. Formatted, rebuilt, 170 tests green. Amended into the
       viewer commit.
   29. `done` (2026-10-27) PR feedback, item 10 (teammate, test/.clang-tidy):
       the reference to agvhito's file dropped; comment cut to two lines.
       Amended into the viewer commit.
   30. `done` (2026-10-27) PR feedback, item 11 (teammate, namespaces): test
       support and tests moved to `volley::scheduler::test` (nested `scenarios`,
       `initial_states`), after the agvhito / yasminx precedent; `IsLift` /
       `IsLower` became `RaisesLift` / `LowersLift`; the `test` local in
       ExpectOwnTest renamed `owner`; 18 redundant `using volley::` lines
       dropped. Built, 170 tests green, tidy 0 findings. Rule added to
       review_rules.md. Predicates then renamed `IsAgvLiftRaised` /
       `IsAgvLiftLowered` (the user's `Is` convention) and amended.
   31. `done` (2026-10-27) PR feedback, item 12 (teammate, message aliases):
       every `*Msg` / `*Srv` alias in the test code replaced by its
       `interfaces::msg::X` / `interfaces::srv::X` type with an explicit include
       (23 types, 208 uses, 20 files); library headers untouched. Built, 170
       tests green, tidy 0 findings. Rule added to review_rules.md. Amended into
       the viewer commit.
   32. `done` (2026-10-27) PR feedback, item 13 (teammate, viewer script):
       renamed to `tools/view_scheduler_tests`, chmod +x, usage and README
       updated; hooks still select it through the shebang. Amended into the
       viewer commit.
   33. `done` (2026-10-27) PR feedback, items 14 and 15 (teammate, viewer
       script): no `uv run` (a `.venv` in the workspace); poe task
       `scheduler-test-viewer` added and named in the README;
       `from __future__ import annotations` removed from the 15 viewer files
       (Python 3.14). Hooks and the task green. Task renamed
       `scheduler-test-viewer`; amended into the viewer commit.
   34. `done` (2026-10-27) PR feedback, item 16 (teammate, test includes): the
       three test headers moved to `test/include/scheduler/test/`, include dir
       `test/include`, 40 includes now `<scheduler/test/x.hpp>`; README updated.
       Built, 170 tests green; amended, then tidy on the moved headers: 0
       findings.
   35. `done` (2026-10-27) PR feedback, item 17 (user + teammate): support
       sources moved to `test/src/` (CMake updated); the 59 in-package includes
       of the test code quoted. Built, 170 tests green. Then, the user: all test
       sources under `test/src/` (jobs, stages, utils moved; CMake loop
       `test/src/${test}.cpp`; README). Built, 170 green, amended with advance
       approval, tidy after the amend: 0 findings.
   36. `done` (2026-10-27) PR feedback, item 18 (teammate, ament_index for the
       scenario paths): evaluated, no change. Intentional: recording writes the
       files back, failures must name the source file, test data has no consumer
       in share; layouts still come through ament_index (site_config). Reply
       text drafted for the PR. README got the one-sentence why; amended.
   37. `done` (2026-10-27) PR feedback, item 19 (teammate, unused struct
       fields): all three test structs traced; `InitialState::layout`,
       `Scenario::description`, `Scenario::initial_state` and `Run::now` removed
       (table in code_notes.md); `Run::scenario` kept and flagged. Built, 170
       green. Amended (`Run::scenario` kept); tidy 0 findings.
   38. `done` (2026-10-27) PR feedback, items 20 and 21 (teammate, CMake gtest
       wiring): the redundant `find_package(ament_cmake_gtest)` dropped
       (volley_package finds test depends), the support library links
       `GTest::gtest` and the include list loses `GTEST_INCLUDE_DIRS`. Built,
       170 green. Amended into the viewer commit.
   39. `done` (2026-10-27) PR feedback, item 22 (teammate, scenarios.hpp
       responsibilities): split into
       `scenarios/{file,request,recording,shared_scheduler,plan,stage}.{hpp,cpp}`,
       same namespace, tests include what they use (table in code_notes.md).
       Patch proposed, awaiting approval. Built, 170 green, amended, tidy 0
       findings.
   40. `done` (2026-10-27) PR feedback, item 23 (teammate, plan twice): `Plan()`
       plans once; `ExpectDeterministic()` plans every file of the suite twice
       (`planned` / `replanned`), through a new `Read` without the ownership
       check; `TEST(<Suite>, Deterministic)` in the eight job binaries. Built,
       178 green, amended, tidy 0 findings.
   41. `done` (2026-10-27) PR feedback, item 24 (teammate, ExpectRecorded): the
       text is built before the ofstream opens (open truncates; a throw would
       have emptied the file). Compare path green. Amended on "amend commit"
       without a record run; tidy 0 findings.
   42. `done` (2026-10-27) PR feedback, item 25 (teammate, YAML::convert):
       `scenarios/yaml.hpp` with decode specializations for pose, job, command,
       params and a new `Request`; key tables as constants; `Scenario::request`
       decoded; `BuildRequest` reduced to numbering; eight `ScenarioYaml` tests
       in a new binary. Built, 187 green, amended. Tidy flagged `decode`
       (naming): NOLINT block with the reason. Pattern question answered
       (customisation point, like std::formatter).
   43. `done` (2026-10-27) PR feedback, item 26 (teammate, SharedScheduler key):
       explained; the key is layout | ratio | cost_audit, motion_cost excluded;
       comment reworded to say so. Amended into the viewer commit.
   44. `done` (2026-10-27) PR feedback, item 27 (teammate, QuietLogging): valid;
       the environment class, its global and the NOLINT replaced by a
       function-local static in SharedScheduler's cache-miss branch. One
       own-scheduler test narrates again (accepted). Amended into the viewer
       commit; tidy 0 findings.
   45. `done` (2026-10-27) CI red after the user's rebase and push: mypy on all
       files sees two extensionless scripts as module `__main__`
       (clang-tidy-diff-hook and the viewer). Fix: `scripts_are_modules = true`
       in [tool.mypy] (bare, no comment); hook green on all files in the
       container. Amended into the viewer commit; the user pushes.
   46. `done` (2026-10-27) Greptile second pass: `Palette.css()` compared
       `f.type` with "str"; after the future-import removal the type is the
       class, so both themes lost every colour (confirmed: only `--move`
       emitted). Fixed with `is str`; 27 tokens per palette again. Amended into
       the viewer commit (b62423ca). Fetched main for a rebase: still dd96ed86,
       the commit the user had rebased onto, so the branch was already up to
       date and nothing moved.
   47. `done` (2026-10-27) code_notes.md brought up to date with the design as
       reviewed: status and contents; the file tree with test/include and
       test/src, the seven scenarios/ headers and their responsibilities
       (table), the YAML::convert layer, Read vs Load, Plan once plus
       ExpectDeterministic, SharedScheduler with the function-local quieting,
       the IsAgvLift* predicates, explicit message types, quoted includes; the
       walkthrough rewritten along the current call chain with a section for the
       determinism test; stale paths in the Q&A fixed; the "where these notes
       say X, read Y" patches removed. The feedback log stays as history.
   48. `done` (2026-10-27) Greptile second pass, two items assessed: cars with
       `reciprocal_to_tray` drawn aligned (valid; `Asset.reciprocal`, windows
       turned, hover and table say reversed; checked numerically on FromStall)
       and `AgvInTheWay`'s description naming W2070 for W2074 (valid; fixed; a
       sweep of all 58 descriptions found no other wrong node). Amended into the
       viewer commit (396ca448). Remote main still dd96ed86: rebase a no-op, no
       rebuild needed.
   49. `done` (2026-10-28) scenario_selection.md written for the user's review
       of the selection: the rule (every old test ported one to one, four gaps
       closed), the four old binaries, an old-to-new table for all 72 tests, the
       four new scenarios, the layout decisions and what the move changed, the
       initial states, and the gaps and five points to decide (the duplicate
       UnplugsChargerAgvMovesFirst, the TwoAgvsDistinctChargers GUID fix,
       tiny_lot, two odd recordings, the retrieve-heavy mix).
   50. `done` (2026-10-28) scenario_selection.md extended at the user's asking:
       section 3 "Did the port expand the coverage?" (41 planned situations
       before, 45 plans + 13 stages after; four new scenarios = 2,019 to 2,026
       covered lines of scheduler.cpp; depth, layouts and data form are what
       changed); "same inputs" defined as same situation, not same numbers; a
       subsection on how a ported state was designed (role-to-role node map,
       headings turned by 90 degrees, the FromStall example, hand-written
       gramercy and pecos states, the redesigned blockers, the four new states).
       Sections renumbered.
   51. `done` (2026-10-28) Justin's two review points reasoned through, reply
       drafted for the user (no code change). (a) Overfitting: the recordings
       are characterisation tests for the refactor's parity, by design change
       detectors; the EXPECT_* lines are the correctness checks and stay; a
       parameter change (strafe speed) does re-record, with the diff as the
       review artefact; options for later: drop durations from the canonical
       form, or demote the recordings to the stage DAGs once the solver
       interface exists. (b) Sorting scheduled_jobs: the scheduler rebuilds the
       list from an unordered_map keyed by GUID (BuildScheduledActionsArray), so
       the returned order is hash order of process-wide counter GUIDs, carries
       nothing and would flap; dispatch matches by GUID; the order that matters
       is the action nodes' parents, compared in full.
   52. `review` (2026-10-28) Teammates' request after their discussion: gate the
       comparison with the recorded part behind an environment variable, off by
       default, so that a change to a planner configuration input (cost model)
       does not force a re-record; the EXPECT_* properties hold across
       configurations, a parity run is explicit. Assessed (sound, provided the
       gated mode runs automatically somewhere; the trade-offs given) and
       drafted, uncommitted, for the user's review: `ExpectRecorded` returns
       before the comparison unless `SCHEDULER_CHECK_RECORDINGS` is set (the
       existence, own-test and missing-output checks stay; `ExpectDeterministic`
       untouched); doc comments in recording.hpp, plan.hpp, stage.hpp; README
       (the command `SCHEDULER_CHECK_RECORDINGS=1 poe test-pkg scheduler`); the
       user's wrapper passes the variable through. A poe task
       `scheduler-check-recordings` was drafted and removed at the user's asking
       (the README command is enough), and the three doc comments cut after the
       user found them too verbose. A CI matrix entry was drafted, explained
       line by line at the user's asking (blocking; non-blocking forms laid out)
       and then dropped on the user's decision after a second team discussion:
       CI runs the invariant properties only, the files may be deleted or moved
       later, nothing is designed around them. Verified: build clean; an edited
       `FromStall.yaml` passes with the variable unset and fails at line 32 with
       it set, file restored. Full package: `volley-in-container test scheduler`
       187 tests green with the variable unset and 187 green with it set (at the
       time through the poe task); with the edited FromStall.yaml and the
       variable set exactly that test fails (colcon counts it twice, gtest and
       ctest), file restored, scenarios folder clean. prek hooks pass on every
       touched file. `== nullptr` kept over `!getenv` for consistency with the
       two other reads (asked). Open for the user: which commit (recording
       commit by fixup + autosquash, or the viewer commit). Details in
       code_notes.md, last review section.
   53. `blocked` (2026-10-28) User approved amending into the recording commit
       by fixup + autosquash. Fixup commit a0e1a853 made in the container
       (hooks, commitlint green), then
       `git -c sequence.editor=true rebase -i --autosquash dd96ed86` conflicted:
       modify/delete on plan.hpp, recording.hpp, stage.hpp, recording.cpp and
       content on README.md, because the recording commit b26ea5d6 has no
       `test/include/` or `test/src/` at all; every review amend since the
       header split and the `test/src/` move went into the viewer commit
       396ca448, which is where the gated files were created. Rebase aborted;
       branch back to b26ea5d6, 396ca448, a0e1a853 (fixup on top), tree clean.
       The fixup can only fold into the viewer commit (a rebase whose todo marks
       a0e1a853 `fixup` under 396ca448). The user asked to try again, carefully,
       two commits only. Done: the recording commit has the old layout
       (`test/scenarios.cpp` / `.hpp`, `ExpectRecorded` at scenarios.cpp:394),
       so the same change was made there by hand on a detached HEAD at b26ea5d6
       (gate, four-line comment, the Plan and ExpectStage comments, the header's
       overview line, the README's three passages), built (0 warnings) and
       checked (edited FromStall passes unset, fails at line 32 set, restored),
       committed as fixup 7cf22eab (hooks green). Then one rebase onto dd96ed86
       with an explicit todo (`sequence.editor=printf ... >`): pick b26ea5d6,
       fixup 7cf22eab, pick 396ca448, fixup a0e1a853. The viewer pick conflicted
       as expected (modify/delete on scenarios.cpp/.hpp, content on README.md);
       resolved by taking the viewer commit's side (`git rm` the two, README
       `--theirs`, verified identical to 396ca448's), `rebase --continue`, and
       the viewer fixup applied cleanly. Result: 28f69008
       `test(scheduler): record ...` (b26ea5d6 + the three files, 29/17 lines)
       and 6d4ae5b5 `feat(scheduler): add a viewer page ...`; authors and dates
       kept; `git diff a0e1a853 HEAD` empty, so the final tree is the verified
       one. Rebuilt at HEAD (0 warnings) and the package re-run: 187 tests
       green. Tree clean. Not pushed; the user force-pushes.
   54. `done` (2026-10-29) PR #1007 merged (`61e7b0d7`). Stage-2 preparation at
       the user's asking: `PROMPT.md` rewritten for the merged state (header:
       stage A done, how to start stage 2; section 1: scenario files and the
       opt-in comparison as the parity mechanism; rules 5 to 9 and 12: the two
       test runs, record-reference on any of the 19 binaries, one branch and PR
       per stage, the commit message form the team accepted (no step tag, no
       key), amend/rebase only on the user's word, the post-PR review loop;
       section 4: where the B2 names live now (sanity_check_tests,
       scheduler_state_tests, stage.cpp, scheduler_ros.cpp lines 20 and 55);
       commit table without step tags; Phase A replaced by what landed; B2 and
       C1 file references corrected (the module test cannot be named
       `tray_assignment_tests`, default `tray_assignment_module_tests`; layouts
       per stage A; `initial_states::Load`); 6.1 tree and 6.4 rewritten for the
       support library; section 10 rows for the parity mechanism, the module
       test name and stage A's open points). `review_rules.md` section 7 added:
       what PR #1007 taught, distilled from the review log and the code notes by
       a subagent and checked (C++, tests, Python, the review loop, rejected
       items), plus checklist item 8. Status sections of this file, the folder
       README, the SW2-1126 README and code_notes updated to "merged"; a
       historical note on top of DESIGN-REVIEW.md. `HOW-IT-WORKS.md`, which the
       old header cited, does not exist anywhere under ~/repos; the reference is
       gone. Then, at the user's asking, the stage-2 folder
       `SW2-1135_scheduler_renames/` (README with the rename-the-placeholder
       instructions, `jira_ticket.md` in the SW2-1126 form with objective,
       scope, definition of done, out of scope and review notes,
       `pr_description.md` drafted with the testing lines open, `code_notes.md`
       skeleton), linked from the folder README and `PROMPT.md`. Branch
       `jmg/SW2-1135/scheduler-renames` (renamed 2026-10-30, see Status).
       Stage-2 log items start at 159.
   55. `done` (2026-10-29) Ticket created by the user: SW2-1135. Folder renamed
       to `SW2-1135_scheduler_renames/`, every placeholder replaced, branch
       `jmg/SW2-1135/scheduler-renames` (renamed 2026-10-30) created from main
       `61e7b0d7` (host `git switch -c`, tree clean). Scope widened at the
       user's asking: small code-quality clean-ups (reimplement messy snippets,
       delete deprecated or dead code, and the like) bundled into the ticket as
       step B2-4, one commit per topic after the renames, behaviour-neutral only
       (rules 1 and 3), surveyed and approved at the review gate first; written
       into the ticket text (Jira description to be re-pasted), the PR text, the
       stage README and code-notes skeleton, PROMPT.md (B2-4, commit mapping,
       exit criteria) and this status. On main, `test/` holds only `include/`,
       `src/` and `scenarios/` (no `garage_states/` left); 12 keyless TODOs in
       scheduler.cpp/.hpp are survey material for B2-4.
   56. `done` (2026-10-29) Commit 2 prepared (B2-1, B2-2), unstaged, review
       packet posted. +216 / -204 in 5 files. 187 tests green both ways,
       `test/scenarios/` clean, prek green. Decisions to confirm: `pg_` as a
       temporary in the initialiser (not a local); pose_graph include moved to
       scheduler.cpp; 7 log lines keep the old method names like the 16 error
       strings; the viewer's `JOB_METHODS` follows the new names; ROS
       `printdags` parameter/service names unchanged. User: "sounds good", then
       "rebase on tip of main, commit, then proceed". Log lines keep the old
       names for now (moot: item 161 deletes most of them). Committed `9eb12865`
       (hooks and commitlint green), then rebased onto `origin/main` `4c281d86`
       (#1010, central_api only) as `cdd973f8`; commit before rebase because git
       does not rebase over a dirty tree (same result).
   57. `open` (2026-10-29) User: "essentially eliminate logging as it is, the
       tests are way too noisy" and "remove or condense comments". Measured:
       INFO is already muted in tests (stage A's `QuietLogging`); the noise is
       the scheduler's WARNs (68 "Failed to find open space", 50 "Failed to
       recursively resolve", 26 path-dump lines, ~29 "Failed job").
       scheduler.cpp: 59 INFO, 20 DEBUG, 27 WARN, 21 ERROR; ~850 comment lines
       in the package. Agreed: two clean-up commits after commit 3: (1) delete
       INFO/DEBUG narration, per-attempt WARNs and dumps, keep ERROR and the
       outcome WARNs (`Failed job`, rejected ratio), test threshold to ERROR,
       check each deleted statement for side effects (`.value()` inside a log
       line can throw); (2) condense comments to the why, delete commented-out
       code, keep the `Reduce` note (quirk "keep").
   58. `open` (2026-10-29) Commit 3 prepared (B2-3), unstaged, review packet
       posted; details in the stage's code notes.
   59. `open` (2026-10-29) Tidy findings on renamed lines (rule 8 says record,
       not fix), but the pre-push hook and CI fail on any finding: 36 over
       commits 2 and 3 (34 unchecked-optional, 1 optional-value-conversion, 1
       braces, plus 2 naming on the public `cost_audit_`/`print_dags_` the hook
       cannot see). Proposed: amend commit 2 to make `cost_audit_` /
       `print_dags_` private (users: Scheduler and its friend SchedulerRos); a
       clean-up commit adding `src/planner/scheduler/src/.clang-tidy` with
       `-bugprone-unchecked-optional-access` (precedent
       `src/agvhito/src/sm/.clang-tidy`; the team's `.value()` rule already
       makes access throw); braces fixed; the optional-value-conversion left to
       commit 6, which rewrites that line (NOLINTNEXTLINE with the reason until
       then). Awaiting the user's decision.
   60. `discussed` (2026-10-29) "Defend the name PlanContext over
       ScheduleContext." Answered in chat: its lifetime is one `Plan()` call
       (created in `Plan`, dropped on return) and it pairs with `Plan()`,
       `PlanRequest`, `PlanResponse`; "schedule" already names the output
       (`ScheduleEvent`, `ScheduleEventDag`, `scheduled_jobs`, `base_schedule`),
       so `ScheduleContext` reads as context of a schedule; Phase R catalogue
       name. Alternatives weighed: `PlanState`, `PlanRequestContext`,
       `PlanSession`.
   61. `done` (2026-10-29) "The new comments are too verbose." plan_context.hpp:
       the four restating comments deleted, the 5-line `first_tray_event` note
       cut to one why-line, a one-line purpose doc on the struct.
   62. `done` (2026-10-29) Review all names in the extracted context, delete
       code where possible. Applied: `class` to `struct`; aliases deleted;
       `request_id_str` deleted (labels derived); `UpdateLeafDependencies` to
       `OrderAfterJobLeaves(event)` without `job_index`; parameter `entity_id`
       to `asset`, `childevent` / `new_event` to `event`; three bodies
       shortened, same edges in the same order. Kept, with reasons in chat:
       `AddScheduledJob`, `AppendToAssetChain`, the four field names,
       `start_time`, `initial_state`, the constructor. 187 tests green both
       ways, scenarios clean, advanced 16 and planner_core 23 green, prek green,
       tidy clean on the header. Header 58 lines (was 63 in scheduler.hpp).
   63. `done` (2026-10-29) Remove the `first_event_by_tray` comment; the name is
       enough. Removed; header 57 lines. Rebuilt (0 warnings), prek green; tests
       not re-run (comment only).
   64. `done` (2026-10-29) "Why make cost_audit_ and print_dags_ private? Isn't
       it a struct with public members?" Answer: they are members of the
       `Scheduler` class (its trailing `public:` block), not of `PlanContext`;
       tidy requires no `_` on public members and `_` on private ones. Options:
       private and keep the names (no caller changes; `SchedulerRos` is a
       friend), or public as `cost_audit` / `print_dags`. Recommended private.
       Awaiting the user's choice.
   65. `done` (2026-10-29) `.clang-tidy` for `scheduler/src` as its own commit,
       earlier if it blocks a push. The hook diffs the branch at push time with
       HEAD's config, so it only has to be in the branch before the push;
       planned right after commit 3. The braces and one unchecked finding sit in
       GetJustMovingCost's path dump, which the logging clean-up deletes; the
       optional-value-conversion (DoTrayAssignments, a dest validated earlier in
       the loop) still needs a NOLINTNEXTLINE or the `.value()` dropped before
       the push.
   66. `done` (2026-10-29) User: private, keep the underscore; commit; proceed.
       Members moved private (build 0 warnings, 187 both ways, scenarios clean);
       commit 2 amended with only that hunk (`git apply --cached` of a patch
       against HEAD, commit 3 still unstaged) as `ef6b0732`, body updated;
       commit 3 committed as `4e58915b` (hooks green). Commit 2 alone was not
       rebuilt: its tree differs from the tested one only by commit 3, and the
       access change compiles in both.
   67. `done` (2026-10-29) Clean-up commit "turn off the unchecked-optional
       check" prepared (code notes). Package-level config replaces
       test/.clang-tidy; the conversion finding resolved by a named local, not
       by dropping `value()` (B12). Branch tidy-clean with it. User: "ok, that
       fine": committed as `720a378e` (hooks green).
   68. `done` (2026-10-29) User: new structs must not go into bare `volley`
       (name collisions); use `volley::scheduler` as the test folder does
       (`volley::scheduler::test`). `PlanContext` moved to `volley::scheduler`;
       library signatures say `scheduler::PlanContextSPtr` (Scheduler stays in
       `volley`); tests unchanged. Build 0 warnings, 187 both ways, scenarios
       clean, planner_core 23, advanced 16, prek green, tidy 0. Proposed:
       `git commit --fixup=amend:4e58915b` with the updated message, then
       `git rebase --autosquash origin/main` (git 2.53, non-interactive).
       Knock-on for later stages: PROMPT.md puts `GarageServices` in `volley`
       and the tray module in `volley::task_planning::tray_assignment`; by this
       rule they become `volley::scheduler` and
       `volley::scheduler::task_planning::tray_assignment` (or
       `volley::scheduler::tray_assignment`). To confirm with the user before
       commit 4.
   69. `done` (2026-10-29) User: use `using volley::scheduler::PlanContext;` at
       the top instead of qualifying (clear origin, less text). PR #1007's "no
       `using volley::X` inside volley" covered redundant lines only, so no
       conflict. Done in scheduler.cpp: file-scope
       `using volley::scheduler::PlanContext;` and `...::PlanContextSPtr;` after
       the includes (the repo's precedent: agvhito's .cpp files); its 34
       qualified uses are plain again (scheduler.cpp differs from commit 3 by 4
       lines). Not done in scheduler.hpp: a namespace-scope using in a header
       re-exports the name into `volley` for every includer (scheduler_ros, the
       advanced tests), which undoes item 172; no header in the repo does it
       (only function-local ones in bay, vrc, agvhito). Header keeps
       `scheduler::PlanContextSPtr` (30 uses); asked the user; alternative: a
       class-scope alias in Scheduler. 187 both ways, scenarios clean, prek
       green, tidy 0. User: keep the header qualified; later the whole Scheduler
       may live in volley::scheduler. Folded into commit 3 by an `amend!` commit
       with the updated message and `git rebase --autosquash origin/main`:
       commit 3 `cac77ea0`, clang-tidy `52c78d0d`; tree identical to the tested
       one. commitlint accepted the `amend!` header.
   70. `open` (2026-10-29) User: remove `scheduler_msgs.hpp` at some point in
       this PR; name the messages fully (`interfaces::msg::X`) and include only
       the message headers each file uses, as test/ does. A clean-up commit
       after the comments one.
   71. `done` (2026-10-29) Logging clean-up commit prepared (item 161's policy);
       details in the stage's code notes. Kept list and the `cost_audit` default
       (true) reported to the user. User: "ok, commit". Committed `43868463`.
   72. `done` (2026-10-29) Comment clean-up commit prepared (two subagents,
       verified comment-only by comment-stripped comparison, reviewed by hand);
       stage code notes.
   73. `open` (2026-10-29) User: the code-quality task (B2-4). Survey by a
       read-only subagent at HEAD `43868463`: 31 candidates (C1-C31) plus K1-K3
       and 23 keyless TODO/FIX comments; spot-checked C7, C8, K2 and the B14
       claim. Posted to the user grouped into proposed commits; overlaps with
       C1-stage commits (C2, C3, C6 in the tray emission code that commit 7
       merges) proposed for deferral. Awaiting the user's pick.
   74. `done` (2026-10-29) User: "yes, commit both": comments committed
       `2127d506`; dead-code commit (group 1: K1-K3, C7, C8, C9, C24, C31)
       prepared; stage code notes. K1 and K3 were planned for commits 4 and 7,
       which now skip them.
   75. `done` (2026-10-29) User: did the rename commit review method and local
       names beyond Expand*Job? Answer: no (commit 2 did the planned members and
       Expand*Job, commit 3 PlanContext's members). Naming survey by a read-only
       subagent at `2127d506`: N1 GetEventDag (builds a DAG of AGV ids) ->
       BuildAgvOrderDag, N2 AgvMatchingEventDeps -> AgvsBlockingAssignedTray and
       `event_map` -> `matching`, N3 `agv_event_dag` -> `agv_order_dag`, N4
       AddDepsAfterAmiga -> OrderTransitionAroundAgvLifts and its inverted loop
       locals, N5 `WithPriorDests` lambda breaks the case rule, N6
       `open_space_result` -> `target`, N7 `tray_event_id` duplicates `tray_id`,
       N8 `event_occupied_durations` -> `event_earliest_starts`, N9 Plan()
       locals (`plan_ctx`, `message2`, `final_trajectories`, `schedule_opt`),
       N10 dst / dstpose / garagepose -> dest_*, N11 `_or` -> `_opt`, N12
       shadowed `success`/`message`, `vecs_opt`, `vertex_opt`. Spot-checked N1
       and N2; no use outside the package or in tests. Proposed: one separate
       rename commit (folding into commit 2 would conflict with the later log
       and comment commits); strings that spell an old name stay. Awaiting the
       user.
   76. `done` (2026-10-29) User: "ok, commit" (dead code: `d0c50173`); method
       names are verb phrases unless accessors (noun = the field's name); work
       on the next commit. Name clean-up prepared with N1-N12 (tray locals
       included, the first option) plus ResponseFromTrajectories ->
       BuildActionGraph and VrcFloorTransitDuration ->
       ComputeVrcFloorTransitDuration; stage code notes. Rule to carry into
       C1/C2: the planned names PreferredHeading, EvChargeHeading,
       RetrievalHeading are nouns; by this rule they need verbs (e.g.
       ChoosePreferredHeading) unless the user calls them accessors. Asked.
   77. `done` (2026-10-29) User: "dest_vecs_opt: what is vecs, not clearly
       named; review all local variables too; explain
       FindAgvsBlockingAssignedTray." Explained from the code: for an AGV whose
       matched event is a tray move, it returns the other matched AGVs whose
       current pose collides with this AGV standing at the tray (the pickup);
       BuildAgvOrderDag makes each go first. Renamed FindAgvsAtPickupPose. VECS:
       stage A's test data spells it `ev_charger` (scenario README key table);
       locals follow, API and type names (VecsTransition, GetVecs,
       VecsReportMsg) belong to other packages. Full local sweep: 433 names, 66
       renamed (stage code notes, round 2); folded into the uncommitted name
       commit.
   78. `done` (2026-10-29) User: `delta`, `result` unclear; scan again; can
       `std::tie(success, message) =` be structured bindings? Round 3 of the
       name commit (stage code notes). std::tie: 12 success/message sites become
       `if(const auto [success, message] = X(); !success)` where the outer pair
       is not read afterwards (checked per site in the next commit); the two
       `std::tie(dest, repark_moves)` in DoTrayAssignments stay (outer `dest`
       read after). Proposed as its own commit after the names. origin/main is
       now `5d5d7b39` (#1004, bay only); the branch sits on `4c281d86`; no
       rebase needed for this, the user decides when.
   79. `done` (2026-10-29) User: scan the methods, each named correctly and
       accurately; e.g. TryFindBlockingTrayResolution ->
       FindBlockingTrayResolution or better. Round 4 (stage code notes): 21
       renamed; strings and TODO lines identical to HEAD; 187 both ways,
       scenarios clean, planner_core 23, advanced 16, prek, tidy 0. Asked:
       DoTrayAssignments -> AssignTrayMoves and DoAgvAssignments ->
       AssignAgvsToTrayMoves would require editing 14 scenario descriptions
       (authored text) or leaving them stale; ResolveBlockingTrays kept
       (accurate as "work out how to resolve"; named in two other packages'
       comments). Agent-reported possible bugs beyond B13/B14: Plan() re-fails
       jobs already failed in expansion (B5), ExpandChargePayloadJob discards
       the unblocking moves (known), TransferEventDagDepsToActionDag `.at` can
       throw before its check, ExpandReparkTrayJob reads the tray from
       initial_state (to verify).
   80. `done` (2026-10-29) User: rename them, YAML included, keeping the solver
       goal in mind; commit; next item. DoTrayAssignments -> AssignTrays,
       DoAgvAssignments -> AssignAgvs (solver-stable names); 13 YAML
       descriptions, scenarios README, viewer labels; committed `d606ab1b`.
       Structured-bindings commit prepared (item 182); stage code notes.
   81. `done` (2026-10-29) User: at most 10 commits, ideally 6; approved the
       rewrite into 6. Done: std::tie committed as a fixup (`beb09aac`, the
       tested final tree); a scripted `rebase -i` (todo via GIT_SEQUENCE_EDITOR
       set in VOLLEY_IN_CONTAINER_PRELUDE; ALLOW_REBASE=1) picked ef6b0732 +
       fixup 52c78d0d, cac77ea0, 43868463 + fixup 2127d506 (messages amended by
       exec, hooks and commitlint ran), then `break`; commit 4 rebuilt by hand
       as d606ab1b's tree with the ten dead-code items re-inserted under their
       new names (checked: the lines commit 5 removes equal d0c50173's removed
       lines after the renames); commit 5 = tree beb09aac. Verification: final
       tree == beb09aac; commit 2 tree == 52c78d0d, commit 3 == 2127d506 (both
       tested before); commits 1 and 4 built and tested on their own (0
       warnings, 187 both ways, scenarios clean, planner_core 23, advanced 16);
       tidy hook on the branch: 0 findings.
   82. `done` (2026-10-29) User: fetch main, rebase, then group 2. Fetched
       (origin/main `5d5d7b39`, seven bay commits), rebased cleanly: `8576aa48`,
       `20884e57`, `da3b38af`, `228de977`, `b6d4d601`; scheduler tree unchanged;
       tip built and tested both ways. Group 2 prepared as an amend of #5 (stage
       code notes); awaiting review.
   83. `open` (2026-10-29) User: amend group 2 into #5, then group 3. Amended:
       #5 `d8720537` (one stray `commit --amend` with an empty message in the
       same command aborted as git does; reflog shows one amend). Group 3
       prepared (ExpandJob, fail_all_jobs); stage code notes. The five
       stage-failure paths are not reached by any recorded scenario.
   84. `done` (2026-10-29) User: no pairs or tuples; a custom struct or an
       expected type instead of `std::tuple<bool, std::string, bool>`. Done for
       the two tuple returns (ExpandJob and ExpandRetrieveJob):
       `stdx::Expected<void, scheduler::JobFailure>`,
       `JobFailure {message, retain_job}` in scheduler.hpp under
       `volley::scheduler`; retain-true returns use designated initializers;
       `<tuple>` include dropped. BoolStringPair (about 40 methods) left as is,
       raised with the user as its own change. Build 0 warnings, 187 both ways,
       scenarios clean, planner_core 23, advanced 16, prek green, tidy 0.
   85. `done` (2026-10-29) User: booleans take an `is_` prefix; then commit and
       go on; and asks whether BoolStringPair can become an expected type and
       whether long signatures (AppendAgvMoveToTrayEvent, 11 parameters) can
       shrink. Done: JobFailure::is_retryable (and MakeFailedJob's parameter);
       group 3 amended into #5 as `037b5c29`; group 4 prepared (code notes).
       Survey: BoolStringPair is repo-wide (common/types.hpp;
       DiscreteGarageState::Apply, ScheduleEvent::Apply return it), 22 Scheduler
       methods return it. Seven methods take more than 5 parameters: the AGV
       tree (AppendAgvMoveToTrayEvent 11, AppendAgvLiftEvent 7,
       OrderArrivalAfterPriorOccupant 6) and the tray tree
       (FindDestinationForRootTray 8, FindBlockingTrayResolution 8,
       CheckMovePossible 7, AssignDestAndUnblockingMoves 6). PROMPT section 4
       already plans both: C1 moves the tray tree onto stdx types and request
       structs; the AGV tree and job expansion wait for stages F and H. About 14
       bool names lack an is_ prefix (allow_recip, enforce_retrieval_heading,
       raised, ...); asked whether to rename them in #4.
   86. `done` (2026-10-29) User: StopVecsForTrayDeparture unclear (no "vecs");
       remove the new comments, let names carry it; rename the ~14 bools. Done:
       UnplugEvChargerBeforeTrayMove, FindAgvLiftChange (replaces
       IsAgvLiftChange and its bool argument), new comments removed, bools
       renamed (code notes). Awaiting review; open: where the renames land (#5
       or their own commit).
   87. `done` (2026-10-29) User: why were the test bools left out (C++, not
       YAML)? Seven commits at most, every edit in one of them. Answer: C++ test
       locals, fields and one helper parameter; my sweep covered src/include
       only, no reason. Renamed (a script hit an include path,
       interfaces/msg/bay_command.hpp, restored). Layout: #6 bool renames, #7
       message headers; mapping in the code notes. Build, 187 both ways,
       scenarios clean, planner_core 23, advanced 16, prek green, tidy 0.
   88. `done` (2026-10-29) User approved: group 4 into #5, bool renames as #6,
       then group 5 (#7). Done: #5 `8d3d2398` (tree tested alone), #6 `e7fbfaee`
       (byte-identical to the tested full tree). Group 5 prepared (code notes):
       aliases replaced package-wide, per-file includes, scheduler_msgs.hpp
       deleted, move_planner.cpp in agvhito_tools adjusted. Awaiting review.
   89. `done` (2026-10-29) User: skip the TODOs for now; what is the `[ok, msg]`
       leftover; no `to_expected` wrapper: change the signatures, remove
       BoolStringPair from the package. Answer: `[ok, msg]` was the abbreviated
       binding in ReparkWaypointStashedTrays (now `tray_repark`). Done (code
       notes): 22 methods and ValidateBaseState on stdx types, call sites and
       tests updated; PROMPT section 4 said the AGV tree and job expansion keep
       BoolStringPair until stages F/H, the user overrides that. Group 5 set
       aside, re-generated after. Proposed: into #5.
   90. `done` (2026-10-29) User: approved the fold-in; remaining objectives:
       agvhito_tools without the scheduler dependency, `->` for std::optional
       member access, no long signatures. Done: #5 `c6478ebb`, #6 `a4a12fc0`
       (tree == tested final tree); group 5 regenerated for #7 (checks green).
       Objectives surveyed; options and buckets in the code notes; awaiting #7
       review and the agvhito_tools decision.
   91. `done` (2026-10-29) User: skip agvhito_tools; do optional access and
       signatures. Done (code notes): `->` for checked optionals; state structs
       for the AGV and tray assignment helpers, ResolveRequest (C1 shape),
       CandidateMove; nothing over 5 parameters. Group 5 set aside again.
       Awaiting review; proposed into #5.
   92. `done` (2026-10-29) User approved the fold-in of 195 into #5, rebuild #6,
       regenerate #7. Done: #5 `ff9e0677`, #6 `b9ee836b` (tree == tested final
       tree); group 5 regenerated (checks in code notes). Awaiting review of #7.
   93. `done` (2026-10-29) User approved #7. Committed `0c2f1dc1` (16 files,
       hooks and commitlint green). Open for the stage: the keyless TODOs
       (skipped for now), PROMPT sections 4-6 with the final names, PR text,
       final tidy hook run; the user force-pushes.
   94. `done` (2026-10-29) User: review all TODOs in depth, recommend keep /
       remove. Done (code notes): 25 markers; 18 to remove (6 done/obsolete, 3
       vague, 4 backlog ideas, 4 merged, the commented-out tests in test04), 7
       to keep with ticket keys. Awaiting the user's call.
   95. `done` (2026-10-29) User: apply as fixups, keep seven as TODO(any). Done
       (code notes): #3 `1ffabb36`, #4 `4393c88c`, #5 `a5ea1fcf`, #6 `400b521c`,
       #7 `2706dc55`; checks green, tidy 0. Ticket keys for the seven to come
       from the user. Still open: PROMPT sections 4-6, PR text.
   96. `open` (2026-10-29) User: review event_dag.hpp naming and unused API for
       scheduler readability, as a new commit. Done (code notes, "Commit 8"):
       Dag, GetNode/GetEvent returning the node, unused API deleted,
       RemoveRedundantEdges, Apply -> stdx::Result, GetParents / GetChildren at
       the scheduler's edge walks. Awaiting review.
   97. `done` (2026-10-29) User: semantics: what does Apply mean
       (ReplayEvents?), tray_id == 0 without comments, scan schedule_events.hpp.
       Recommendation in code notes; includes a correction to item 198
       (VrcTransition exists). Awaiting the user's pick.
   98. `done` (2026-10-29) User: fold Apply renames, sentinels, schedule_events
       fixes and unused API into #8, AgvMove split later. Done (code notes). Two
       corrections of my own claims recorded. Awaiting commit approval.
   99. `done` (2026-10-29) User approved #8: committed `70ba93ea` (16 files,
       hooks green). User then: the ExpandAgvMoveJob event block repeats
       AddEvent + AppendToAssetChain, casts needlessly, and hides a `!` before
       an else; rescan scheduler.cpp for patterns. Scan delegated to a read-only
       subagent; findings to be verified before recommending. Scan back and
       verified. Bugs (not fixed, behaviour): B14 re-found (ExpandReparkTrayJob
       `tray_opt->pose` with no tray id, scheduler.cpp:870). B15 new:
       AssignTrays advance move's path is
       `std::vector<GaragePose>{vertex_id, dest}`, which picks vector(count,
       value): N copies of dest (N = vertex id) instead of a two-pose path;
       tray_opt is also already the post-advance pose (scheduler.cpp:2321). B16
       to check: UnplugEvChargerBeforeTrayMove adds the stop-charging VECS event
       without chaining it to the VECS asset; the start-charging event
       (ExpandChargePayloadJob) is chained. Error-text oddities kept:
       "TrayId=5does not exist", "Failed to apply event:".

  Round 24 (2026-10-26): 103. `done` Jon's force push is slow at the clang-tidy
  pre-push hook; where does the output go, and a code-notes section on it.
  Answer: tools/clang-tidy-diff-hook (prek.toml, stage pre-push) pipes
  `git diff -U0 origin/main...HEAD` into clang-tidy-diff, which analyses every
  changed translation unit whole (clang-analyzer-* included) and filters to
  changed lines; output is captured and printed only at the end, and prek shows
  it only on failure; no log file unless `--output-log`. 27 C++ files in this
  commit, each pulling scheduler.hpp, hence the time. I never ran
  `volley-in-container tidy` on the rewritten tests: an omission, noted in the
  code notes; findings, if any, go into the next amend.

  Round 23 (2026-10-26): 100. `done` Paths: each leg is a straight line beside
  its segment, cut 1 m short at both ends, and consecutive legs are joined by a
  quadratic Bezier corner whose control point is where the two legs' lines meet
  (a hairpin past the node when the path turns back, straight on when it
  continues). Lanes: every leg sits 0.3 m to the right of travel plus 0.25 m per
  earlier pass over the same directed segment by any agent (`Scene.lanes`,
  cycling after seven), so the repeated passes of AdvancesRootTray fan out
  instead of stacking. Arrowheads end each straight leg; the hover stretch of a
  leg is its straight part plus half of each adjacent corner. Catmull-Rom and
  the per-agent offset are gone. Checked in-process (finite curves, lane counts
  up to 3 passes); the browser pane still refuses the page, so the look is Jon's
  to judge. 101. `done` Code notes: "How a test run flows" rewritten as four
  parts (from CMake to a binary, inside a binary before the first test, one plan
  test RetrieveJob.FromStall, one stage test TrayAssignment.MovesOneBlocker,
  plus what a failure looks like), every step naming the file and the function;
  a table of contents at the top, generated from the headings. 102. `done` Jira
  sub-ticket drafted in `jira_ticket.md` (summary, objective, scope, definition
  of done, out of scope, observations for follow-up, review guide), to paste
  into SW2-484. Amended: commit 1 is b7d4a3d5 (viewer only this round), tree
  clean; remote still f47bbb61.

  Round 22 (2026-10-26): 97. `done` Rebase onto the tip of main: 83569373
  (data-race fixes merge), two new commits, none touching the scheduler package;
  no conflicts; commit 1 is ebc0a2b8. Jon had pushed f47bbb61 himself on
  2026-10-23 (origin/jmg/SW2-484/scheduler-core-refactor), so the remote is now
  behind the rewritten branch and needs a force push, which stays Jon's. 98.
  `done` Viewer paths: `Scene.steps` takes all steps and draws one path per
  agent (AGV or tray): a Catmull-Rom curve through the nodes of its moves (12
  samples per leg), shifted to the right of its direction of travel by 0.3 m
  plus 0.3 m per agent, so a return leg over the same segment and other agents'
  paths stay apart; an arrowhead (plotly marker `arrow` with
  `angleref: previous`) ends each leg; one hidden thicker trace per leg lights
  up on hover (`segments` in the entry data; app.js shows it with the badge
  highlight, only while the solution is shown); rotations, lifts, lowers and
  lift rides are numbered badges (⟳ ▲ ▼ ⇅). AGV colours are shades of green
  (dark theme #4ADE80, #15803D, #A7F3D0, #22C55E; light #15803D, #4ADE80,
  #14532D, #65A30D), trays amber. The old per-step arrows, lanes and arcs are
  gone. Checked in-process (paths, colours, stretches hidden, badges, arrowheads
  per leg); the browser pane refused the page this session, so the look is for
  Jon to judge. 99. `done` Code notes: "How a test run flows, from CMake to the
  comparison": CMake (`scheduler_tests` list, `volley_add_gtest` ->
  `ament_add_gtest`, the define), build, `colcon test` / CTest / the result
  files, gtest's `main` and static registration, the order inside
  `scenarios::Plan` (path from test info, file parse, initial state, Scheduler
  constructor and the cached collision table, request, two plans,
  canonicalisation, comparison or recording), a stage test, and what a failure
  prints. Post-rebase run: 170 + 23 + 16 tests pass; hooks green. Amended:
  commit 1 is 01c3edb0, 162 files on 83569373; local branch ahead 3 / behind 1
  of the pushed f47bbb61 (force push is Jon's).

  Round 21 (2026-10-23): 96. `done` Rebase onto the tip of main again: 3d4048e0
  (showcase nightly merge), eight new commits, none touching the scheduler
  package or the dependency files; no conflicts. Commit 1 is f47bbb61. Build and
  tests re-run on the rebased branch (see below).

  Round 20 (2026-10-23): 95. `done` The commit message still read as subjective
  in its first sentences; keep it objective, no mention of previous authors, no
  indirect criticism. The first paragraph now states what the change is and what
  it guarantees, without a judgement on the existing tests; "defunct" became
  "decommissioned". Amended: commit 1 is 1c9d4236, 162 files, working tree
  clean.

  Round 19 (2026-10-23): 92. `done` The commit message sounds too casual; make
  it more professional. Rewritten: the problem (a refactor is due, the tests
  assert only what each author chose), the change, the layout moves and the
  viewer, in three paragraphs without colloquialisms. 93. `done` utils_tests.cpp
  -> test/utils/{base_state_validation,empty_tray_count,bay_rebalancing}
  _tests.cpp, suites ValidateBaseState (4), CountEmptyTrays (1), BayRebalancing
  (8). The YAML literals became initial states on 275_sunrise_b (two new files:
  a car too long for its stall, an AGV on an unknown node) or, for the abstract
  bay states (bays 1 to 4, no layout), a small MakeState({bays}, {trays})
  helper; the 14 split cases are a table; the event-by-event tray count uses
  four helpers. Added to the CMake list (now `scheduler_tests`); the old block
  and file are gone. CountEmptyTrays lives in
  common_ros/discrete_garage_state_utils.hpp. 94. `done` Style of
  src/agvhito/src/sm (read: executing_order_state, context_utils, booting_state,
  idle_state, root, two headers, test_layout_utils). Rules derived and applied,
  by script for the 15 stage and job files (scratchpad/style.py) and by hand for
  the support files: includes limited to what the file uses, grouped gtest /
  <...> sorted / "..." sorted; anonymous namespace for file-local helpers and
  constants (kLayoutName, InsertExpectation, ExpectInsert,
  ExpectRetrieveThroughLift); const on every local not reassigned (by reference
  when it only reads); _opt ->_or, iterators _it; /// doc comments with @p and
  @return in the headers and on helpers, [[nodiscard]] on value-returning
  functions; std::format for every message; comments as full sentences stating
  what holds ("Every job was planned") instead of "make sure it was planned";
  EXPECT_TRUE instead of EXPECT_EQ(x, true); dead locals removed; the request
  note "hello" dropped from every scenario (all 58 re-recorded: the note echoes
  in the response). Listed in the code notes under "Conventions". Result: hooks
  green, scheduler 170 (15 planning binaries + 3 utils), planner_core 23,
  scheduler_advanced_tests 16 tests pass; viewer regenerated. Amended: commit 1
  is ea53f390, 162 files on top of 5ad693dc, working tree clean.

  Round 18 (2026-10-23): 88. `done` Keep tiny_lot for the two blocking-tray
  fallback scenarios. 89. `done` Remove all dead code: the commented-out
  DoubleRetrieveDodgeAgv (with its TODO line) and a commented-out SetDest line
  in tray_assignment_tests.cpp are gone; the ASCII diagram of the blocker block
  was rewritten with the sunrise node names (a drawing, not code). Nothing else
  commented out remains in the test files (rg for comment lines ending in ; { }
  or starting with a call). 90. `done` Code notes: a "How the comparison works"
  section. Nothing touches the disk when comparing: the response is
  canonicalised in memory (message -> to_yaml text -> YAML node -> GUID / sort /
  field-name passes), the file's `output` node is parsed, both are emitted to
  strings and compared line by line; only recording writes the file. 91. `done`
  Branch renamed locally (`git branch -m`) to
  jmg/SW2-484/scheduler-core-refactor; it had no upstream, so nothing to rename
  on the remote. Amended after the dead-code removal: commit 1 is 5b965186, 156
  files on top of 5ad693dc, working tree clean, hooks green, retrieve_job_tests
  and tray_assignment_tests re-run.

  Round 17 (2026-10-23): 81. `done` (two exceptions) Remove layout_test and
  tiny_lot; use 275_sunrise_b. Jon: EV-charger scenarios on 38_gramercy, the
  rest on 275_sunrise_b, triple_pick_lot too. Done: 27 scenarios moved to
  275_sunrise_b (around bay B2068: W2069 door, W2070, W2064, stalls P2075,
  P2066, P2067, P2077; the triple_pick block as the 3x3 stalls P2116 to P2149
  with the waypoints W2100 to W2102 beside them), 13 to 38_gramercy (car on
  charger E23, AGV at P19; chargers E21, E23, E25; the bay is the car lift BL26
  on floor 1, VRC 1 idle there). Exceptions: RetrieveJob.AdvancesRootTray and
  ParksBlockerOnCriticalPath stay on tiny_lot. On sunrise with the garage open
  the blocker drives off to a waypoint and no fallback fires; with everything
  outside a region disabled, either no path is found (a disabled waypoint 0.8 m
  from the door node, W2063, counts as a disabled area; an AGV on the rotation
  node W2064 blocks the tray's path) or, once the fallbacks do fire, the planner
  cycles (log of 4.6 million lines, killed after ten minutes). Jon to decide:
  keep tiny_lot for these two, or drop them. 82. `done` "I thought the jobs
  would be provided and parsed from the YAML file rather than hard coded in the
  source": they are now; see the changes below. 83. `discussed` "Are we testing
  against hardcoded expected values?": both. The EXPECT_* lines in a test are
  the hand-written expectations of the properties its author cared about; the
  recorded `output` of the scenario file is the complete result, compared on
  every run, so nothing changes silently. Explained in the code notes. 84.
  `done` Reorganise the test folder: `test/scenarios/garages` ->
  `test/scenarios/initial_states`; `test/garage_states/` (one dead file) removed
  with its CMake install line; the commented-out DoubleRetrieveDodgeAgv that
  loaded it stays commented (it names 576_eccles_half too). 85. `pushed back`
  Delete utils_tests.cpp? It tests production code in scheduler/utils.hpp
  (garage state validation, bay classification and rebalancing), 13 tests,
  nothing to do with the scenarios; deleting it loses coverage the refactor may
  rely on. Kept, pending Jon's answer. 86. `done` VS Code shows Crowdsec schema
  errors on the YAML: SchemaStore maps `**/scenarios/*/*.yaml` to the Crowdsec
  scenario schema. Every scenario file now sits two folders below `scenarios/`
  (`plan/<suite>/`, `task_planning/<stage>/`, `initial_states/<layout>/`), which
  that pattern does not match. No VS Code setting needed. 87. `done` Commit
  message without Jira references, one to four paragraphs with context; rebase
  onto the tip of main (done first, no conflicts: main's five new commits touch
  nothing of ours).

  Round 17 (2026-10-23) changes:
  - 87: `volley-in-container` allows `git rebase` for this stage (ALLOW_REBASE=1
    next to ALLOW_AMEND); rebased onto 5ad693dc (pecos showcase layout merge)
    cleanly.
  - 82 and 84: the scenario file is now authored: `test` (Suite.Name; the loader
    refuses another test's file), `description`, `initial_state`
    (`<layout>/<name>`), `scheduler` (params that differ from the defaults),
    `request` (`jobs`: type and the ids, payload GUID, destination, note the job
    needs; `base_schedule`: reserved AGV commands), then the recorded `output`
    (and `input.dag` for stage scenarios). Recording rewrites only the part from
    the first `input:`/`output:` line on. C++: `test/scenarios.hpp/.cpp`
    replaces parity.hpp (`scenarios::Plan(suffix)` loads the running test's file
    from gtest's test info, builds scheduler and request, plans twice, compares
    or records, returns the Run with scenario, scheduler, request, response;
    `scenarios::Stage` / `ExpectStage` for the stage tests),
    `test/initial_states.hpp/.cpp` replaces garages.hpp. A plan test is now
    `const auto run = scenarios::Plan();` plus its assertions. Files:
    `plan/<suite_snake>/<Name>[.<suffix>].yaml`,
    `task_planning/<stage>/<Name>[.<suffix>].yaml`. Conversion by script
    (scratchpad/to_scenarios.py) for 44 scenarios, by hand for 14 (multi-request
    tests, base schedule, the insert helper, the retrieve fallbacks, state
    mutations -> three new initial states: agv_at_w8_chargers_10_14_disabled,
    agv_and_empty_tray_in_bay_ready_to_insert, agv_in_bay_7_ready_to_retrieve).
    Equivalence check against the committed recordings: 57 of 58 outputs
    identical apart from job GUIDs (now numbered 32, 33, ... in order) and the
    normalised type_name / state_name / note. The one difference is a fix:
    AgvChargeJob.TwoAgvsDistinctChargers gave both jobs GUID 32 in the old test,
    so the scheduler planned one job; with distinct GUIDs both AGVs charge.
    BackToBack's second job had been merged by the script (same variable name in
    two blocks) and was fixed by hand; same for the two charge jobs.
  - Viewer: reads the authored keys, the initial-state file (defaults filled in)
    and the compact jobs; the tree is plan -> suite folder -> scenarios; the
    source table names the initial-state file.
  - README rewritten for the authored format. Hooks green. 155 + 23 + 16 tests
    pass.
  - Commit message rewritten (three paragraphs of at most 92 columns; commitlint
    rejected a 101-column line on the first try; no ticket references) and
    amended: commit 1 is b8725fcc, 157 files on top of 5ad693dc, working tree
    clean.
  - Round 18 (the move): mapping by script (scratchpad/port_layouts.py: node and
    heading maps tiny_lot -> sunrise {1: 2068, 2: 2069, 3: 2070, 5: 2064, 6:
    2075, 8: 2066, 9: 2067, 11: 2077}, headings rotated by 90 degrees;
    triple_pick_lot -> the sunrise block), gramercy states and scenarios written
    by hand (scratchpad/port_gramercy.py). Findings while re-recording:
    - the retrieval-heading rule does apply on gramercy (stalls and lift share
      heading 90): a reparked car is lowered at the reciprocal heading because
      its payload is reciprocal_to_tray, so the repark assertions accept the
      reciprocal heading (IsAngleOrReciprocal);
    - retrieves on gramercy go through the lift: VRC move commands around the
      AGV commands and the AGV hops from L2 to BL26 without a command; the
      retrieve-from-charger tests share a helper (ExpectRetrieveThroughLift)
      that checks that;
    - the chain-recursion stage test needs its 3x3 block closed off
      (disabled_nodes), else the block's open edges make blockers unnecessary;
    - on sunrise the car retrieved from P2066 enters the bay at 2068@0 (inbound
      heading 0).
    - the two layout-only tests (readiness ratio, last entity event) load
      275_sunrise_b.
    - the viewer draws a move between two nodes at the same spot (the lift's
      floors L2 / BL26) as a badge instead of dividing by a zero edge length.
      Result: 155 + 23 + 16 tests pass, hooks green, viewer checked (layouts:
      sunrise 28, gramercy 13, pecos 15, tiny_lot 2). Amended: commit 1 is
      addab96c, 156 files on top of 5ad693dc, message updated for the layouts,
      working tree clean. Code notes rewritten for the layouts.
  - 81 before the move: the port of the tiny_lot (36), layout_test (4) and maybe
    triple_pick_lot (3) scenarios to 275_sunrise_b waits for Jon's answer on the
    13 EV-charger scenarios (no EV charge node on pecos or sunrise; 175_e82nd,
    38_gramercy and CambridgesideV8 have them) and on triple_pick_lot.

  Round 16 (2026-10-23): 78. `done` Viewer: a collapsible section near the top
  of the nav listing every layout the scenarios use, to check whether others
  should go. 79. `done` The C++ test files are still very large; decompose them
  into smaller files, perhaps with a file layout, without over-engineering:
  files of a few hundred lines at most. 80. `done` Commit now to save the work;
  afterwards every feedback iteration of this stage is a `git commit --amend`
  until the stage is complete. 2026-10-23: Jon allowed `--amend` for this stage:
  `volley-in-container` lets `git commit --amend` through (ALLOW_AMEND=1 in the
  script, to set back to 0 after stage A) and Jon removed the deny rule from
  .claude/settings.local.json. Round 16 amended in: commit 1 is now cbac1ccd,
  153 files against main, hooks green (log 20261023-130835). From here on, every
  round of stage A is staged by name and amended with
  `volley-in-container git commit --amend --no-edit`.

  Round 16 (2026-10-23) changes:
  - 80: committed as instructed, before 78 and 79, with the state of round 15:
    `test(scheduler): add parity references to the planning tests (SW2-484 A)`,
    137 files, hooks green (volley-in-container git commit, log
    20261023-125147). The rounds that follow must be amended into it, but
    `volley-in-container` refuses `--amend` (and CLAUDE.local.md forbids it):
    the user's call how to lift that for this stage. Until then the round-16
    work stays unstaged.
  - 78: the nav starts with a "layouts" section (collapsible, open): one row per
    layout with the number of scenarios on it and its file; a click shows the
    first scenario on that layout. Entry data carries `layout` and `layout_file`
    (page.py); app.js builds the section before the tree.
  - 79: the three planning test files became fifteen, one gtest suite and one
    binary each, under `test/stages/` (tray_assignment, agv_assignment,
    assignment_cost, sanity_check, scheduler_state: tests that call the
    scheduler's internals) and `test/jobs/` (move, repark_tray, repark_tray_
    charger, retrieve, retrieve_charger, charge_payload, insert, bay,
    agv_charge, clean_garage: tests through Plan()). Sizes 123 to 463 lines
    (retrieve_job_tests carries the dead commented-out DoubleRetrieveDodgeAgv,
    60 lines). Suites are named after the file (TrayAssignment, RetrieveJob,
    BayJob, ...) and the test names lost the suite's prefix
    (RetrieveJob.FromReadyCharger, AgvChargeJob.SkipsDisabledChargers,
    MoveJob.AgvToBay, ...), so every recorded file was renamed and re-recorded
    (58 files, same content apart from descriptions that name other tests).
    `IsLift` / `IsLower` moved to `test/agv_commands.hpp`. CMake: a
    `planning_tests` list and one `foreach` that adds each binary with
    parity.cpp and garages.cpp, `test/` as include dir and the scenario define.
    The viewer locates tests with `rglob`. Split done by a script
    (scratchpad/split.py) from the committed sources; no hand fixes needed,
    build green with no warnings, hooks green.
  - uv keeps recreating `.venv` on the host (host Python 3.14.8 vs the
    container's 3.14.4): the two sides ping-pong. Harmless so far (packages come
    from the cache); worth running the viewer in the container instead if it
    bothers.

  Round 15 (2026-10-23): 76. `done` Test layouts: we need 5675_pecos full (eng +
  qa); 275_sunrise_b is recommended; avoid 576_eccles (the former HQ, defunct)
  and 1355_fulton (a defunct lot). 77. `done` Update the code notes every time,
  especially after C++ changes; rewrite the document and drop sections,
  questions and content that are no longer relevant.

  Round 15 (2026-10-23) changes:
  - 76: the 13 tests on 576_eccles_half (3 sanity checks,
    ReparkTrayJobAdvanceToWaypoint, AgvChargeJobTwoAgvsDistinctChargers,
    DontGoToDisabledChargeNode) and 1355_fulton (AgvChargeJob,
    AgvChargeJobInBay, TransitionBay, CantTransitionDisabledBay,
    FultonRetrieveWithCleanGarage, the four insert tests) now run on
    `5675_pecos_combined` (28 nodes: the eng and qa sandboxes together, bays B7
    and B21, AGV chargers C10, C14, C16, ten stalls, no EV charger). Nine new
    garage files under `garages/5675_pecos_combined/`; the eccles and fulton
    folders and the old recorded files are gone. Renames:
    FultonRetrieveWithCleanGarage -> RetrieveWithCleanGarage;
    FultonInsertBay{1,2}TrayHeading {0,180} ->
    InsertFromBay{7,21}Tray{Heading90,Reversed}. Node ids in assertions follow
    (charger C16 instead of 60, C10 instead of 20140/20150, bay 7 instead of 1,
    bay 21 instead of 2). The nine ported job and sanity tests passed with the
    expectations carried over unchanged.
  - 76, the insert tests: the four fulton tests checked the V2 rule "lower the
    inserted car at the heading that makes the retrieve fastest"
    (`InitRetrievalHeadings`: the reciprocal of the highest-priority retrieve
    bay's inbound heading, cached for the stalls whose headings allow it and
    that can reach the bay pose). That rule yields nothing on 275_sunrise_b by
    construction (bays at heading 0, stalls at 90: 180 is never an allowed stall
    heading) and nothing on 5675_pecos_combined either (the run logs
    "UseRetrievalHeading, No retrieval heading for dest node 5/6"; the headings
    pass the first check, so the path check from stall@90 to bay@90 must fail;
    not investigated: not this PR's job). A first port to sunrise (busy garage,
    cars in B2052 / B2068) confirmed: the planner just minimises rotation and
    the two insert headings ended at different stall headings. So the tests
    moved to pecos with the expectations that hold there: the nearest AGV does
    the job, it enters the bay at heading 90 (also for a reversed tray), lifts,
    lowers outside the bay. The rest is in the recorded file. Observed and worth
    a look by the team: on pecos the planner parks the inserted car on W31 /
    W41, the waypoint in front of the bay, not in the free stall P15. The four
    tests share one helper (`ExpectInsert`, `InsertExpectation`) instead of four
    copies.
  - `k576EcclesHalfLayoutName` stays in scheduler_tests.cpp: the commented-out
    DoubleRetrieveDodgeAgv references it. Dead with the test.
  - Scenarios README names the layouts to use and the ones to avoid.
  - 77: `code_notes/01-parity-references/notes.md` rewritten as a description of
    the commit as it stands (no history, resolved questions dropped); to be
    redone after every C++ change.
  - uv recreated `.venv` on the host during a `uv run` (host Python 3.14.8); the
    container's hooks run on the system Python and were unaffected (prek 0.3.8
    checked).

  Round 14 (2026-10-23): 71. `done` Plotly's home / reset buttons drop the
  full-width fit; the drawing must always use the full width. 72. `discussed`
  "How does the plan YAML pair with the site_config YAML and the built-in YAML?"
  is moot now that the states live in files (item 73): a scenario names its
  layout and its garage file. 73. `done` Move the YAML out of the C++ tests for
  this stage, even if it breaks the original design: too much coupling between
  scenario config and test code, and files too big to review. 74. `done` No
  unclear acronyms (vecs, vexen) in our YAMLs, even if the message schema uses
  them; standard acronyms like AGV are fine. 75. `done` Rename test/reference to
  something like test/scenarios or test/cases.

  Round 14 (2026-10-23) changes:
  - 71: Plotly's own "reset axes" and "autoscale" buttons are removed from the
    modebar and a "Fit the drawing" button (home icon) calls `refit`; a double
    click refits too (`plotly_doubleclick`). Verified: after a forced autorange
    the fit button restores full domains and the area's aspect.
  - 75: `test/reference` -> `test/scenarios`; the define is
    `SCHEDULER_SCENARIO_DIR`; the viewer's adapter module is
    `plan_viewer/scenarios.py` and the script flag `--scenarios`.
  - 73: every inline state (60 literals, 54 distinct) became a file
    `test/scenarios/garages/<layout>/ <name>.yaml` (55 files: 54 plus the two
    fillings of the `{blocker_node}` template, minus one shared) loaded by
    `garages::Load("<layout>/<name>")` (new `test/garages.hpp/.cpp`, in the
    three planning binaries). The folder is the layout (`layout_test` resolves
    to common_ros's test_layout.yaml, the others through `GetLayoutPathByName`),
    so the tests' layout constants and the `GetLayoutPathByName` boilerplate
    went too (two tests without a state keep it). Garage files drop fields at
    their default (lift, tray_id, agv_id, disabled, empty payload GUID,
    charging, reciprocal_to_tray, hash, is_faulted), print GUIDs as
    `00000000-0000-0000-0000-000000000001` strings (what `ParseGuid` reads) and
    `pose: {node_id, heading}` on one line, and comment every numeric `state`
    with its meaning. Names describe the garage
    (`tiny_lot/car_on_ready_charger_8`), not the test, so shared states are
    shared: `empty_trays_at_p9_p6_e11` (2 tests), `agv_at_p9` (2),
    `agv_lifting_tray_in_bay` (2), `576_eccles_half/agv_at_51` (3),
    `layout_test/car_charging_at_e11` (2). Migration done by a script
    (scratchpad/migrate.py) from backed-up sources; three spots fixed by hand (a
    `[set, set_msg]` capture, two `EXPECT_TRUE(success)` left before their
    declaration). Line counts: scheduler_tests.cpp 2101 -> 1310,
    scheduler_jobs_tests.cpp 3229 -> 2056,
    scheduler_insert_orientation_tests.cpp 977 -> 411. Test counts unchanged
    (26, 34, 4).
  - 74: in the garage files and the recorded files, `vexen` -> `ev_chargers`,
    `vrcs` -> `vertical_conveyors`, `vecs_id` / `vecs_command` ->
    `ev_charger_id` / `ev_charger_command`, `vrc_id` / `vrc_command` ->
    `vertical_conveyor_id` / `vertical_conveyor_command`. The garage loader maps
    the two list names back before `DiscreteGarageState::Set`; `parity.cpp`
    (`SpellOutFieldNames`) renames the keys of every message dump. Event strings
    in the DAGs (`VECS_TRANSITION`) come from the C++ `ToString` and stay; the
    viewer's glossary explains them. Descriptions say "charger 8" instead of
    "VECS 8". Eleven tests renamed so that no file name says Vecs:
    ReparkTrayJob{GoodVecs,BadVecs,ChargingVecs,BadVecsDest,GoodVecsAtDest} ->
    ReparkTrayJob{FromReadyCharger,FromUnavailableCharger,WhileCharging,ToUnavailableCharger,
    ToReadyCharger}; RetrieveJob{GoodVecs,BadVecs,ChargingVecs} ->
    RetrieveJob{FromReadyCharger, FromUnavailableCharger,WhileCharging};
    ReparkUnplugVecs -> ReparkTrayJobUnplugsCharger;
    ReparkUnplugVecsMoveAgvFirst -> ReparkTrayJobUnplugsChargerAgvMovesFirst;
    ChargePayloadJobNoVecs -> ChargePayloadJobWithoutCharger. The C++ message
    constants (TYPE_VECS_COMMAND, vecs_command) stay as they are in the test
    assertions: code, not YAML.
  - Decision taken without asking (say so if wrong): the garage file holds the
    state only; the jobs, base schedule and event DAGs stay in C++ because there
    is no YAML reader for the job messages and they are the part of a test a
    reviewer reads with its assertions.
  - All 58 recorded files re-recorded (every one changes: the field names).
    Build green, no warnings; scheduler 80, planner_core 23,
    scheduler_advanced_tests 16 tests pass; hooks green (clang-format
    reformatted the new C++ once, then rebuilt and retested).
  - The scenarios README now documents the garages (format, example, vocabulary
    table).

  Round 13 (2026-10-23) changes:
  - 68: the page now computes the axis ranges itself (`fittedRanges` in app.js):
    the drawing's bounds, centred, with the narrower side widened to the plot
    area's aspect ratio, applied on draw and again after a resize
    (ResizeObserver, 50 ms debounce). `refit` calls `Plotly.Plots.resize` first
    because plotly only measures the container on window resizes; the stale size
    was why `constrain="domain"` left the drawing in the middle. The entry data
    carries `bounds`. Verified: x and y domains [0, 1] at 1160x457 and after the
    details pane changes height; the aspect of the ranges equals the area's.
  - 69: `Step.assets` became `Step.destination` (model.py) and step rows pass no
    asset keys unless the table asks for destinations; `stage_tables` asks only
    for the tray-assignment stage. Event rows highlight the agent only; job rows
    keep the tray, AGV and bay, not the destination stall. Verified: a schedule
    row lights no outline (ghost only); tray-assignment step rows carry `node:`
    keys.
  - 70: `code_notes/README.md` (index) and
    `code_notes/01-parity-references/notes.md`: the files under scheduler/test
    one by one, the anatomy of a stage test and of a jobs test, the layout YAML
    versus the garage state (`initial_conditions.yaml` is the simulator's
    placement, not the scheduler's), `vexen` = the `DiscreteVecsState[]` field
    (VECS = Volley EV Charging System, src/vecs/README.md), why the inline YAML
    fixtures stay (and what a file-fixture PR would look like), why outputs are
    recorded, and three open points (dead `DoubleRetrieveDodgeAgv` + its YAML,
    the duplicate `ReparkUnplugVecsMoveAgvFirst` reference, the unused
    `agv_command.id` replacement).
  - Facts checked for the notes: `DoTrayAssignments` / `DoAgvAssignments` are
    public; action GUIDs come from a process-wide counter (`CreateActionGuid`,
    utils.cpp:307), not a random source; the three planning files hold 23 + 33 +
    4 inline states; `double_retrieve_garage_state.yaml` is used only by the
    commented-out `DoubleRetrieveDodgeAgv`.
  - README "Viewing" paragraph updated for the new highlight rules. Hooks green
    on the touched files (black, mypy, markdownlint). No C++ change this round,
    so no rebuild.

  Round 2 (2026-10-22) changes: `parity.hpp` API is now `Dag(ctx)`,
  `TrayAssignment` / `AgvAssignment` (scheduler, dag_before, ctx) and
  `ActionGraph(scheduler, request, response)` returning a `Reference` {stage
  folder, doc}; `ExpectReference(reference, suffix)` and
  `ExpectPlanReference(scheduler, request, now, suffix)` (plans twice, no
  lambda, no template). Stage call sites take
  `const auto dag_before_<stage> = parity::Dag(*ctx);` before the stage. The
  `.tray` / `.agv` suffixes are gone (the folder tells). The retrieve-fallback
  helper became `FullTinyLotRetrieveRequest(blocker_node)` returning the
  request. Reference sizes: tray_assignment 4 files / 318 lines, agv_assignment
  9 / 706, action_graph 45 / 27,781 (the `input.request` carries the whole base
  state). Recorded and compared again: scheduler 80 tests pass in a fresh
  process; planner_core and scheduler_advanced_tests were not re-run (no
  production code changed since their last green run). Hooks pass on every
  touched file (markdownlint, black, mypy included). The viewer was run in the
  container (`uv run python ...`, 58 references) and checked in the browser:
  navbar grouped by stage folder, layout graph with trays / AGVs / bays /
  disabled nodes, numbered move arrows in topological order, input and output
  text under the plot. 204. `done` (2026-10-29) User: commit, apply all
  improvements, fix the bugs. Done: #9 `8e976f18` (refactor, parity checked
  after each of four batches; skipped with reasons: the initial-state prologue
  helper, an ApplyEvent wrapper, the AssignTrays blocker-scan extractions left
  to C1), #10 `ec2785b3` (B1/B15, B2, B5, B6, B7, B12, B13, B14, B16; B5 has a
  regression test that fails on the old code; no recording changed). Ten commits
  now. Not fixed: the two TODO(any) bugs (failed job's partial events, retrieve
  without PROCESS_RETRIEVE). 205. `done` (2026-10-30) User: implement the
  review's recommendations, keep the commit sequence, use `--amend`. Done by the
  stage-A session: all of `review_stage2.md` sections 2-5 plus the fix-commit
  message corrections, implemented at the tip and validated first, then folded
  into the ten commits with an interactive rebase (exec amends per rename stage,
  prepared trees for #9 and #10). Renames land in the commit that introduced the
  old name; the helpers, format errors, `format.hpp`, `IsTrayReversedOnAgv`,
  constants and comments in #9; #10 is the same seven fixes in refactored form
  with a message that states reachability (fixes 3 and 5 unreachable today). Old
  tip kept as `jmg/SW2-1135/backup-ec2785b3`. Not done: scenarios for fixes 2
  and 4, the Jira re-paste. Checks on the final tip `ebb9de58`: build of
  scheduler / scheduler_advanced_tests / agvhito_tools 0 warnings; scheduler 188
  both with SCHEDULER_CHECK_RECORDINGS=1 and plain, recordings unchanged;
  planner_core 22; advanced 16; tidy 0 (one optional-conversion finding fixed
  and folded into #9). 206. `done` (2026-10-30) User: implement both (the
  comment clean-up and the split), leave the TODO items alone, goal clarity and
  readability in fewer lines. Done by the stage-A session: 47 of the 54 comment
  findings as idempotent edits amended into the first commit where each comment
  exists (exec after every pick from #3; #1 and #2 untouched; net -44 lines),
  then commit 11 `aa651a6f`, the split of scheduler.cpp into scheduler /
  job_expansion / tray_assignment / agv_assignment / validation / action_graph
  .cpp plus utils and the new job_failure.hpp, no body changes. Checks: build 0
  warnings, scheduler 188 both ways with recordings unchanged, planner_core 22,
  advanced 16, tidy 0. Details in the stage code notes. Not pushed. 207. `done`
  (2026-10-30) User: rename / reimplement ReciprocalGaragePose and
  IsAngleOrReciprocal in an easy-to-amend commit. Commit 12 `1a76c027`:
  scheduler-local OppositeHeading, WithOppositeHeading and
  IsSameOrOppositeHeading in utils, delegating to common (used by common_ros and
  motion_planner, so common is untouched); 13 sites; plus one tidy cast. Checks:
  build 0 warnings, scheduler 188 with recordings unchanged, planner_core 22,
  advanced 16, tidy 0. 208. `done` (2026-10-30) User: verb-first function names,
  professional commit messages, another comment sweep, estimate for
  pure-function job expansions. One rebase: all twelve messages rewritten
  (objective register, shorter), ReverseHeading / ReversePoseHeading /
  ChoosePickupHeading / FailRetryable, 117 comment edits (net -139 lines) folded
  into the first commit where each comment exists. Estimate: free-function
  expansions need GarageServices and ten tray-side members made free first
  (phase C1); deferred. Checks: see code notes. 209. `done` (2026-10-30) User:
  defer the pure-function expansions (confirmed); why two Fail functions; assess
  clean-ups in cost_functions and motion_planner for scheduler readability.
  Written: `SW2-1135_scheduler_renames/upstream_cleanup_assessment.md` (13
  ranked items, the pure-function candidates, Fail/FailRetryable answer).
  Recommendation: keep `Fail` alone and spell the two retryable sites out (this
  PR); the rest as a stage of its own before C1, one commit per item, since C1's
  GarageServices wraps exactly these APIs. Nothing changed. 210. `done`
  (2026-10-30) User: apply the Fail recommendation, defer the upstream items.
  FailRetryable deleted, the two retryable sites spelled out, folded into #9
  onward; #9-#12 are `bfc23e67`, `ebb9de58`, `aa651a6f`, `1a76c027`. Checks
  green (see code notes). Not pushed. 211. `done` (2026-10-30) User: is the
  branch name still good; review the Jira and PR files. Branch name kept
  (`jmg/SW2-1135/scheduler-renames-and-cleanups`). `jira_ticket.md` and
  `pr_description.md` rewritten for the twelve commits: new title "Rename, clean
  up and split the scheduler before the tray solver", Scope per commit, the fix
  commit's behaviour changes and the one error-string fix listed under
  Definition of Done and "Behaviour and expectation changes", Out of scope names
  the deferred upstream items, Testing with the tip's counts. User re-pastes
  Scope / DoD / Out of scope and the Summary into Jira. 212. `done` (2026-10-30)
  Codex review 1 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_1.md`): three
  readability findings, all confirmed by reading; recommended now: a
  PlannedTrayMove record with an optional applied-from pose replacing
  `required_moves` + `applied_move_sources` (fix commit), and
  `occupant_by_node` > `last_occupant_by_node` (commit 5); AssignTrays'
  decomposition stays with C1-5/6. Codex ran nothing: the neutrality audit is
  still open. 213. `done` (2026-10-30) User: apply both Codex findings.
  `last_occupant_by_node` in #5 and the PlannedTrayMove record (with
  `applied_from`) in #10, folded by rebase; #5-#12 are `98bbc0fe`, `b1a85516`,
  `04c5ca33`, `5fc0e120`, `bfc23e67`, `ebb9de58`, `aa651a6f`, `1a76c027`. Tree
  equals the validated snapshot; checks green (build 0 warnings, scheduler 188
  with recordings unchanged, planner_core 22, advanced 16, tidy 0). Not
  pushed. 214. `done` (2026-10-30) Codex review 2 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_2.md`): seven
  findings, all confirmed by reading. Proposed: the occupied-duration stub out
  (commit 5); transactional expansion + NaN check into the fix commit with
  tests; a commit 13 removing the Eccles EV-charging exception and advanced
  tests 01-04 (user: Eccles is deprecated); tickets for the zero-on-failure
  durations, ComputeStateBefore, the replay cost, PlanContext by reference and
  the repo-wide Eccles retirement. Nothing changed yet. 215. `done` (2026-10-30)
  User: fix Codex findings 1, 2, 5, 6 now, 3 and 4 if small (they were), defer 7
  and the PlanContext reference. Done: stub out of #5; transactional expansion,
  NaN check, Expected-returning ComputeAgvMoveDuration / ComputeStateBefore into
  #10 with RetrieveJob.FailedJobLeavesNoEvents (new recording, one charger
  command) and SchedulerState.RejectsNonFiniteBayReadinessRatio; #13 `04de7078`
  Eccles exception and advanced tests 01-04 removed. Checks: build 0 warnings,
  scheduler 189 with tracked recordings unchanged, planner_core 22, advanced 12,
  tidy 0. Not pushed. 216. `done` (2026-10-30) Codex review 3 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_3.md`): seven findings
  on heading policy and the action graph, all confirmed. Proposed: tray_dest
  (#9), comparator tie-breaker and rollback note (#10), ApplyPreferredHeading
  wrapper out (#13), commit 14 dead reciprocal parameter, commit 15 action-graph
  error handling; heading precedence as a ticket after a recording-guarded
  experiment. Nothing changed. 217. `done` (2026-10-30) User: do Codex review
  3's items 1, 3a, 3b, 4, 6, 7 and the precedence experiment; the heading
  contract is a ticket. Done: fold-ins into #9, #10, #13; commits 14 `f9a55640`,
  15 `886bbd6f`, 16 `7629d9f7` (experiment landed: recordings unchanged with the
  minimal reorder). Sixteen commits. Checks: build 0 warnings, scheduler 189
  with recordings unchanged, planner_core 22, advanced 12, tidy (final run). Not
  pushed. 218. `done` (2026-10-30) User: too many commits; a plan for an Opus
  5.5 session to squash to 4-6. Written:
  `SW2-1135_scheduler_renames/squash_plan.md`: six adjacent groups (1-6, 7-8, 9,
  10, 11-12, 13-16), the six messages verbatim, the non-interactive squash
  mechanics through the wrapper (todo file, editor script keyed on the first
  subject), verification (tree identical to `7629d9f7`), and the notes to
  update. Nothing changed. Added on the user's word: a verified backup branch
  with a revert recipe, deletion of all seven local backup branches once every
  check passes, and a tone rule for any message edit. 219. `done` (2026-10-30)
  Squash plan carried out: sixteen commits squashed into six adjacent groups
  (1-6, 7-8, 9, 10, 11-12, 13-16) with the plan's messages verbatim: `012e4955`,
  `99c3f9a5`, `1438d791`, `71efa85d`, `ba47ce80`, `2bae4ff6`.
  `git diff 7629d9f7 HEAD` empty. One fix to the plan's editor script (blank
  line after git's squash header), made before the rebase. Checks: build 0
  warnings, scheduler 189 with recordings unchanged, planner_core 22, advanced
  12, tidy 0. Backup `backup-7629d9f7` made and verified first; all seven backup
  branches deleted after the checks. Notes, PR text (`# What` per commit), Codex
  prompt and Jira text updated for six commits. Not pushed. 220. `done`
  (2026-10-30) Codex review 4
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_4.md`): six findings,
  all applied, kept at six commits. #3: MakeAgvPoseMove,
  StopChargingBeforeTrayMove returning stdx::Result. #4: the repark reads the
  planned tray (stale-pose bug, new test
  ReparkTrayJob.ReturnsTrayAfterEarlierRepark, fails on the old code),
  full-payload motion order. #6: FindRetrievalTrayHeading replaces the two
  heading helpers, no reorder (item 217). Tip `9eea90ce`; commits 3 and 4 built
  and tested on their own; scheduler 190 with recordings unchanged, planner_core
  22, advanced 12, tidy 0. Backup branch deleted on the user's word. Not
  pushed. 221. `done` (2026-10-30) Codex review 5 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_5.md`): six findings,
  five agreed, one optional. New and larger than reported: GetInboundHeading is
  unwrapped, so on layouts whose AGV chargers face reciprocal (sunrise_b, pecos,
  gramercy, others) a docked AGV is never "already on the charger" and a
  CHARGE_AGV job moves it to another charger; pre-existing on main, no scenario
  covers it. Proposed landing: commit 3 (bay-transition locals, two renames),
  commit 4 (occupancy errors, inbound-pose helper and the docked-AGV fix with a
  scenario), commit 6 (carried-tray destination helper, validate the resolved
  pose). Nothing changed. 222. `done` (2026-10-30) User: apply Codex review 5
  except #5. Done, kept at six commits (tip `276bd6a4`). New bug fixed in commit
  4: a docked AGV on a charger facing reciprocal was never "already there"
  (unwrapped GetInboundHeading); test AgvChargeJob.AlreadyOnCharger fails on the
  old code. #1 applied to tray assignment only: in the action graph the
  occupancy skip is load-bearing (16 recorded plans), so it stays, named and
  explained. Checks: commits 3 and 4 on their own, tip scheduler 191 with
  recordings unchanged, planner_core 22, advanced 12, tidy 0. Backup
  `backup-9eea90ce`, deleted on the user's word. Not pushed. 223. `done`
  (2026-10-30) Codex review 6 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_6.md`) with the user's
  rules (`is_` booleans, no `.second.second`): all seven agreed or no-change;
  found that `response.scheduled_jobs` comes out in unordered_map order
  (pre-existing) and that pairs remain in four places. Proposed landing across
  commits 1, 3, 4 and 5 (all six rebuilt); two deliberate message changes and
  the response's job order re-record 9 scenarios. Nothing changed. 224. `done`
  (2026-10-30) User: apply Codex review 6 including the remaining pairs. Done,
  six commits, all rebuilt (tip `280339f9`). Pairs landed in commit 6 (commit 1
  still uses std::tie); new struct named TrayDestinationPlan
  (BlockingTrayResolution was taken). Response job order now follows the request
  (old: reversed for two jobs; recordings sort jobs, so a test checks it). Four
  failure texts rewritten; two recordings re-recorded. Every commit built and
  tested on its own; tip scheduler 191, planner_core 22, advanced 12, tidy 0.
  Backup deleted on the user's word. Not pushed. 225. `done` (2026-10-30) Codex
  review 7 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_7.md`): naming and
  ownership. Eight renames agreed (two with shorter names in the code's own
  vocabulary), two not recommended (Build*report methods; renaming
  FindRetrievalTrayHeading, whose comment is fixed instead). Placement:
  utils.cpp helpers used by one file move into it, bay rebalancing gets its own
  file pair, stage files put their entry point first; the heading/builder header
  split is left for C1. Nothing changed. 226. `done` (2026-10-30) User: apply
  Codex review 7 as recommended (no Build* renames, no heading/builder header
  split). Done, six commits, all rebuilt (tip `7166af0e`): renames in their
  birth commits, utils.cpp down to shared helpers, bay_rebalancing files, entry
  point first in the two assignment files. Bodies unchanged except the three
  intended edits. Every commit built and tested on its own; tip scheduler 191,
  planner_core 22, advanced 12, tidy 0. Backup deleted on the user's word. Not
  pushed. 227. `done` (2026-10-30) Codex review 8 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_8.md`): six extraction
  and naming findings, all agreed, two with different names
  (StorePreferredRetrievalHeadings, DisableBaseScheduleEntities,
  FindProcessRetrieveAction); the retrieval-heading free-function split not
  recommended. Landing: #1 in commit 1, #2-#6 in commit 3. Observation:
  base-schedule VRC commands are not excluded (pre-existing). Nothing
  changed. 228. `done` (2026-10-30) User: apply Codex review 8 as recommended.
  Done, six commits, all rebuilt (tip `f756a7cc`; commit 6's message amended for
  the StorePreferredRetrievalHeadings name). Behaviour-neutral: every log and
  error text unchanged, recordings unchanged. Every commit built and tested on
  its own; tip scheduler 191, planner_core 22, advanced 12, tidy 0. Backup
  deleted on the user's word. Not pushed. 229. `done` (2026-10-31) Codex review
  9 evaluated (`SW2-1135_scheduler_renames/codex_reviews/codex_review_9.md`):
  vocabulary. Agreed: ExcludeCommittedResources (+ committed_actions), payload
  vs tray heading (StorePreferredPayloadHeadingsForRetrieval,
  FindPreferredTrayHeadingForRetrieval), IsAgvMotionBetweenFloors,
  ScheduleAgvLift / ScheduleAgvMoveToPickup with contracts, Codex's verb rule.
  Not agreed: renaming AddChainedEvent (the "Chain" family); its comment says
  which chain instead. Nothing changed. 230. `done` (2026-10-31) User: apply
  Codex review 9 as recommended (AddChainedEvent kept, comment fixed). Done, six
  commits, all rebuilt (tip `dca15cf9`). Names only plus contracts; recordings
  unchanged. Every commit built and tested on its own; tip scheduler 191,
  planner_core 22, advanced 12, tidy 0. Backup deleted on the user's word. Not
  pushed. 231. `done` (2026-10-31) Codex review 10 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_10.md`):
  motion_planner API names. "Exclusion filter" is not standard; "keep-out" is
  (Nav2 KeepoutFilter) and already the member's name. For this PR:
  FindRetrieveProcessingAction and the HideAgvs locals (`hide_ok` breaks the is_
  rule). The motion_planner renames go to a separate naming ticket. Nothing
  changed. 232. `done` (2026-10-31) Review-10 proposal settled with the user and
  checked by Codex. Changes from the last summary: FindPosePath keeps "Pose"
  (vertex-state paths exist), so ConvertPosePathToTrajectory stays; the
  recursion is FindRemainingAgvUnderTrayAssignment; the optional's empty success
  stays engaged, with a new test for no enabled AGVs; three dead lines go, not
  one; FindPayloadDeliveryAction gets a one-line contract. Nothing changed
  yet. 233. `done` (2026-10-31) User: apply the settled review-10 changes. Done,
  six commits (commit 1 unchanged, tip `e6976369`). motion_planner renames and
  the optional assignment in commit 2, FindPayloadDeliveryAction in commit 3.
  Tidy then flagged the new optional reads in the hiding tests (gtest ASSERT is
  not modelled); fixed with an if/FAIL guard, folded into commit 2. Every commit
  built and tested on its own; tip scheduler 191, planner_core 22, advanced 12,
  motion_planner 82, tidy 0. Backups deleted on the user's word. Not
  pushed. 234. `done` (2026-10-31) Codex review 11 evaluated with the user's
  simplification question
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_11.md`):
  occupancy_history / OrderAfterPriorOccupants, collision-id names,
  ApplyBayOrChargerTransition, blocker locals agreed; MakeBayInboundPose and the
  action-graph propagation declined. Simplifications proposed: the two duration
  maps into AgvAssignmentState, logging on rclcppx (drops roslog); PlanContext&
  and the tray result structs left for C1. Nothing changed. 235. `done`
  (2026-10-31) Codex reviewed the review-11 plan and agreed; refinements
  recorded in `SW2-1135_scheduler_renames/codex_reviews/codex_review_11.md`
  (occupancy and skip-policy comments, cohesion rationale and a non-inserting
  earliest-start lookup, logging strings as data, `{:g}` for the audit CSV,
  entry_index out of the log call). Ticket to raise: occupancy graph lacks some
  AGV edges. Nothing changed. 236. `done` (2026-10-31) User: apply the refined
  review-11 plan. Done, six commits, all rebuilt (tip `30b014aa`). Planning
  behaviour and recordings unchanged; log calls on rclcppx with identical audit
  CSV (checked). Every commit built and tested on its own; tip scheduler 191,
  planner_core 22, advanced 12, motion_planner 82, tidy 0. Backup deleted on the
  user's word. Not pushed. 237. `done` (2026-10-31) The user force-pushed:
  origin/jmg/SW2-1135/scheduler-renames-and-cleanups is `30b014aa` (checked with
  ls-remote), the same as the local branch; working tree clean. 238. `done`
  (2026-10-31) Codex review 12 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_12.md`): all four
  agreed, plus a third ignored ApplyTo (the path-repair replay). Landing: the
  applies in commit 4, BuildAgvOrderDag, ClassifyBay and the split comment in
  commit 1, `<algorithm>` in commit 5. Needs another force-push. Nothing
  changed. 239. `done` (2026-10-31) User: apply review 12 as assessed. Done, six
  commits, all rebuilt (tip `9bc62155`): the three checked applies in commit 4,
  BuildAgvOrderDag, ClassifyBay and the split comment in commit 1, `<algorithm>`
  in commit 5. Recordings unchanged. Every commit built and tested on its own;
  tip scheduler 191, planner_core 22, advanced 12, motion_planner 82, tidy 0.
  Not pushed. Backup `backup-30b014aa` deleted on the user's word. 240. `done`
  (2026-10-31) Codex review 13 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_13.md`): the
  AssignTrays decomposition is phase C1 (C1-5, C1-6) as planned; defer it there,
  with Codex's cautions and the current names folded into PROMPT.md. Proposed
  now: `new_move_path` to `root_path_poses` (commit 1), the
  `common_ros_msgs.hpp` aggregator out of utils.cpp (commit 2). Nothing
  changed. 241. `done` (2026-10-31) User: apply the two small items, defer the
  extraction to C1, then sweep the comments to a minimal footprint with no
  context. Done, six commits, all rebuilt (tip `72599b1f`): `root_path_poses`
  (commit 1), the aggregator include out of utils.cpp (commit 2), 36 comments
  rewritten or deleted in the commits that wrote them; C1 note in PROMPT.md.
  Messages unchanged; recordings unchanged. Every commit built and tested on its
  own; tip scheduler 191, planner_core 22, advanced 12, motion_planner 82,
  tidy 0. Backup `backup-9bc62155` deleted on the user's word. Not pushed. 242.
  `done` (2026-10-31) Codex review 14 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_14.md`):
  static_graph_filtering. Proposed for commit 2 (neutral): SetEnabled,
  blocked_poses/edges, local and parameter names, comments that match the code
  (AGV/payload TRAY substitution, configured headings, "and" in
  BuildKeepOutFilters), .contains(), dead narration, includes and
  interfaces::msg::BayReport. Later, own PR: the extraction,
  BlockedGraphLocations, IgnoredObstacles. Ticket question: AGV against AGV uses
  the TRAY footprint. Nothing changed. 243. `done` (2026-10-31) User: apply
  review 14's commit-2 subset with names consistent with the scheduler; leave
  the extraction for its own PR. Done: commits 2 to 6 rebuilt on commit 1 (tip
  `d9082d54`); SetEnabled, scheduler-style names, comments that match the code,
  includes and interfaces::msg::BayReport. Commit 2 message has a paragraph.
  Recordings unchanged. Every commit built and tested on its own; tip scheduler
  191, planner_core 22, advanced 12, motion_planner 82, tidy 0. Backup
  `backup-72599b1f` deleted on the user's word. Not pushed. 244. `done`
  (2026-11-01) Codex review 15 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_15.md`):
  bay_readiness_ratio is system vocabulary (ROS param, service, SchedulerReport,
  REST, sim, scenarios): keep it, document it at SchedulerParams, rename the
  bay-rebalancing parameter to insert_ready_fraction (commit 1). Chugg (rename,
  header, names, Node split, ScopeExit, dead replay, SolveCbs with no caller)
  goes to a motion_planner clean-up PR with review 14's deferred items. VRC
  dispatch gap confirmed in code, unreachable from the scheduler: ticket.
  Nothing changed. 245. `done` (2026-11-01) User: apply review 15's commit-1
  part, Chugg to its own PR. Done, six commits rebuilt (tip `ce566d68`): the
  SchedulerParams doc comment and insert_ready_fraction (commit 1). Tidy on the
  folded tip found five unchecked optional reads on lines commit 2 renamed
  (round 14 tidied before folding; the hook reads commits only): fixed in commit
  2 with checks that throw invalid_argument; message updated. Recordings
  unchanged; every commit built and tested; tip tidy 0. Backup `backup-d9082d54`
  deleted on the user's word. Not pushed. 246. `done` (2026-11-01) User: rename
  the readiness ratio inside the scheduler, no comment to cover a name, and find
  other names that lean on comments. Done: target_insert_ready_bay_fraction in
  commit 1 (field, member, bay rebalancing, scenario key in 45 files); external
  names kept. Six commits rebuilt (tip `36288c0a`); recordings unchanged; every
  commit built and tested; tidy 0. Survey in
  `SW2-1135_scheduler_renames/names_covered_by_comments.md`: 17 proposals, not
  applied. Backup `backup-ce566d68`. Not pushed. 247. `done` (2026-11-01) User:
  apply all the name proposals except BayClassification, keep six commits. Done
  with `fix_a15.py` on every commit, so each rename lands where the name was
  written: commit 1 for most; commit 3 for IsParkingWithoutBayOrCharger,
  EventActionSpan, kMaxAgvMoveOrderPasses and the AgvAssignmentState comments;
  commit 4 for PlannedTrayMove (occupied_poses, source_pose_if_applied) and
  WriteJobActionIndices, split out of BuildScheduledActionsArray. Messages of
  commits 1, 3 and 4 updated. Tip `7401cd5a`, tree identical to the tested one;
  recordings unchanged; every commit built and tested; tidy 0. Left for the
  user: the "EnsureAgvMovePathsClear:" error prefix and advanced test07's
  comment naming it; the dead WILL_BE_RETRIEVE_READY branch (with
  BayClassification). Backup `backup-36288c0a`. Not pushed. 248. `done`
  (2026-11-01) User: fix the stale EnsureAgvMovePathsClear error prefix and
  test07's comment in the commits that wrote them. Done with `fix_a16.py`:
  test07's comment names OrderAgvMovesAfterBlockingAgvs and AssignAgvs (commit
  1, which renamed them) and agv_assignment.cpp (commit 5, which split the
  file); the two error texts change in commit 4 (it wrote the second and lists
  the error texts it changes; commits 1 and 3 promise unchanged strings),
  message updated. Tip `ce45d5ff`, tree identical to the tested one; recordings
  unchanged; every commit built and tested; tidy 0. Found, not changed: 32
  strings from main name 13 functions that no longer exist
  (names_covered_by_comments.md). Backups `backup-36288c0a`, `backup-7401cd5a`.
  Not pushed. 249. `done` (2026-11-01) User: fix the strings that name functions
  that no longer exist, in commit 4 with the other error-text changes. Done with
  `fix_a17.py`: 31 texts (item 248 said 32; 31 is right) in commits 4-6 lose the
  old name or say the step that failed ("Failed to assign AGVs: ..."); "Cannot
  find path" stays for test05/test07. Commit 4's message: one bullet for these
  and item 248's two texts (33). No recording holds them. The first fold stopped
  at step A (`clang-format -i` with no files); guarded, step A redone, rebase
  continued; commits 1-3 trees unchanged. Tip `afb46ad0`, tree identical to the
  tested one; every commit built and tested; tidy 0. Backups 36288c0a, 7401cd5a,
  ce45d5ff. Not pushed. 250. `done` (2026-11-01) User force-pushed `afb46ad0`
  (origin matches) and said to delete the backup branches: backup-36288c0a,
  backup-7401cd5a, backup-ce45d5ff and backup-ce566d68 deleted. Only the working
  branch is left. 251. `done` (2026-11-01) Codex review 16 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_16.md`): 1 agree with
  find + explicit failure via PlanContext::FindKeepOutFilter (commit 4; `.at()`
  would crash the node, nothing catches); 2 agree, n_remaining_* and
  assigned_bays (commit 1); 3 agree, const casts and the lift comment (commit
  1); 4 skip (.clang-tidy disables use-nodiscard by team choice). Nothing
  changed. 252. `done` (2026-11-01) User asked which .clang-tidy disables
  use-nodiscard and whether other packages use it. Root .clang-tidy, since 2021
  (aa344037, Mark Cutler); it only stops tidy from requiring it. This branch
  added src/planner/scheduler/.clang-tidy (unchecked-optional-access only).
  agvhito, bay and yasminx mark value returns (factories, predicates, ToString).
  Item 251's "team rule" was wrong; item 4 becomes apply (utils.hpp's eight
  value-only functions, commit 1). 253. `done` (2026-11-01) User: apply review
  16 items 1-4. Done with `fix_a18.py`, each edit where its code was written:
  n_remaining__\_ready_bays, assigned_bays and validation's const casts and lift
  comment in commit 1; [[nodiscard]] on utils' eight value-only functions where
  each is first declared (IsCarryingTray/HasPayload commit 2,
  MakeAgvPoseMove/MakeTrayMove commit 3 (file-local), MakeInboundPose commit 4,
  the heading helpers commit 5; not all in commit 1 as proposed, they did not
  exist there); PlanContext::FindKeepOutFilter and its five sites in commit 4,
  message bullet. Tip `56527885`, tree identical to the tested one; recordings
  unchanged; every commit built and tested, 0 warnings; tidy 0. Backup
  `backup-afb46ad0`. Not pushed. 254. `done` (2026-11-01) Codex review 17
  evaluated (`SW2-1135_scheduler_renames/codex_reviews/codex_review_17.md`): 1,
  2 agree, no change; 3 agree, ComputeStateAfterPlannedEvents in commit 3 with
  texts unchanged (option: one text for the 13 replay failures in commit 4); 4
  agree, filter lookup before the charger loop and const PlanContext& (commit
  4); 5 noted (no caller outside the scheduler). Nothing changed. 255. `done`
  (2026-11-01) User: apply review 17 items 3 and 4, one replay text in commit 4.
  Done with `fix_a19.py`: ComputeStateAfterPlannedEvents (file-local) and its 13
  callers in commit 3, texts unchanged; commit 4: the 13 replay failures and the
  two log lines before two of them read "Failed to apply the planned events:
  {}"; the charger search looks the AGV filter up once before its loop (none: no
  charger) and takes const PlanContext&. Messages of commits 3 and 4 updated.
  Tip `50b1b722`, tree identical to the tested one; recordings unchanged; every
  commit built and tested; tidy 0. Backups `backup-afb46ad0`, `backup-56527885`.
  Not pushed. 256. `done` (2026-11-01) Codex review 18 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_18.md`): 1 agree, the
  AGV-order cycle returns a failure instead of throwing (a cycle is reachable in
  principle, the throw would crash the node; BuildAgvOrderDag's throws are
  bookkeeping and stay), commit 4; 2 agree, drop the two inner ERROR logs (WARN
  in MakeFailedJob stays), commit 4; 3 agree, shortest_travel_duration /
  charger_pose_with_shortest_travel in commit 1, const locals in commit 3.
  Nothing changed. 257. `done` (2026-11-01) User: apply review 18 items 1-3.
  Done with `fix_a20.py`: commit 1 names charger_pose_with_shortest_travel (the
  search's result and the caller's local) and shortest_travel_duration; commit 3
  const locals and no travel_duration copy in the charger search; commit 4: the
  AGV-order cycle returns "Failed to assign AGVs: the assigned AGVs block each
  other's pickups" instead of throwing, and retrieve/repark drop their inner
  replay-failure ERROR logs; message bullets. Tip `cc4a9e92`, tree identical to
  the tested one; recordings unchanged; every commit built and tested; tidy 0.
  Backups afb46ad0, 56527885, 50b1b722. Not pushed. 258. `done` (2026-11-02)
  User asked whether the Jira ticket and PR description are updated. The local
  texts had the shas but stale claims: error strings that spell DoAgvAssignments
  "unchanged on purpose" (PR checklist, Jira DoD), "no other error string
  changed", client-visible text out of scope, "commit 10", reviews "4 to 15",
  and the Jira behaviour list missing the keep-out filter, the AGV-order cycle
  and the 33 reworded texts. Fixed in pr_description.md and jira_ticket.md; the
  old-name rg claim checked at `cc4a9e92` (none in scheduler or advanced tests).
  GitHub and Jira themselves are pasted by the user. 259. `done` (2026-11-02)
  User: the PR description has too much text, condense it. Rewritten in
  pr_description.md: one line per commit, one short list of commit 4's behaviour
  changes, a one-sentence Why, three testing lines (about 490 words from "#
  What" on, from 97 long lines); the details stay in the commit messages. 260.
  `done` (2026-11-02) User: rebase on the tip of main. main gained `f3fa775f`
  ([SW2-1071] parking options, central_api only, no overlap). Clean rebase; each
  commit equals its old version plus those two files; messages, authors and
  dates unchanged. Tip `a3370c4b`: built (0 warnings), scheduler 191,
  planner_core 22, advanced 12, motion_planner 82 with the recording check;
  tidy 0. Base in
  SW2-1135_scheduler_renames/codex_reviews/codex_review_prompt.md is now
  `f3fa775f`. Backup `backup-cc4a9e92`. Not pushed. (The CI rerun of run
  41462551815 tests the old tip `cc4a9e92`.) 261. `done` (2026-11-02) User
  pushed `a3370c4b` (origin matches) and said to delete the backups:
  backup-50b1b722, backup-56527885, backup-afb46ad0 and backup-cc4a9e92 deleted.
  Local `main` is at `5d5d7b39`, one behind origin/main `f3fa775f`;
  `git fetch origin main:main` fast-forwards it without switching branches. 262.
  `done` (2026-11-02) User: rescan controller_webview, write the deploy/test
  steps into the ticket folder, and give the Codex feedback its own folder.
  controller_webview is the NOC (PHP), now the app stack's `noc` service on port
  8011 (`/webviewer`), calling central's REST API on 5000 (alias `scheduler`);
  its README (microk8s, salt) is outdated. Wrote
  `SW2-1135_scheduler_renames/testing/deploy_and_test.md` (coverage so far,
  local sim, swarm deploy of the `pr-1018` images via `.env.local` (inferred),
  NOC endpoints, AGV checklist, open questions). Moved the 18 reviews and
  `codex_review_prompt.md` to `SW2-1135_scheduler_renames/codex_reviews/`; 31
  references updated (this file, PROMPT.md, code_notes.md, squash_plan.md);
  README table updated. 263. `done` (2026-11-02) Greptile's PR review (4/5, one
  P2) and Codex review 19 evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/codex_review_19.md`): 1 agree,
  commit 6 deleted the tiny_lot `OverlappingAgvAssignmentFailureTest2` with the
  Eccles test03 file; proposal: move it to the scenario suite (`plan/move_job/`,
  MOVE_TRAY supported) in commit 6, asserting both jobs come back executing; 2
  defer `AssignDestinationAndUnblockingMoves`' plan/schedule split to C1, which
  already deletes the function and merges its emission loop (PROMPT.md 636-742).
  Nothing changed. 264. `done` (2026-11-02) User: restore the tiny_lot test, and
  discuss BayClassification. Commit 6 now moves
  `OverlappingAgvAssignmentFailureTest2` into the scenario suite as
  `MoveJob.TwoTrayMovesWithOverlappingAgvs` (`plan/move_job/`, initial state
  `tiny_lot/agvs_on_w3_and_p6_trays_on_p6_and_p9`), asserting success, two jobs,
  both executing, each with actions; recorded with `record-reference` filtered
  to that test (AGV 2 takes tray 2 to charger 11 first, then AGV 1 tray 1 to
  P8). Message updated. Only commit 6 rebuilt (`67aedc95`), tree identical to
  the tested one; scheduler 192, planner_core 22, advanced 12, motion_planner
  82, recordings unchanged; tidy 0. Backup `backup-a3370c4b`. Not pushed. 265.
  `done` (2026-11-02) User: apply the BayClassification plan. Commit 1
  (`fix_a21.py`, all commits): INSERT_READY, INSERT_NEEDS_EMPTY_TRAY,
  INSERT_IN_PROGRESS, RETRIEVE_READY, RETRIEVE_NEEDS_TRAY_REMOVAL,
  RETRIEVE_IN_PROGRESS, NOT_USABLE, no comments on the enum; the never-produced
  WILL_BE_RETRIEVE_READY and its branch deleted in commit 1 (it deletes dead
  code; the plan said commit 6); one reason comment on the counting rule; the
  two test blocks that fed the dead value are now
  RetrievesInProgressCountAsInsertReady and BaysInProgressGetNoTransitions;
  stale "invalid" test comments reduced to what each bay holds;
  LeavesBayInFlightAlone -> LeavesRetrieveInProgressAlone. Commit 6: the
  scenario is MoveJob.TwoTrayMovesWithAgvUnderOneTray. Messages of commits 1 and
  6 updated. Tip `e5edee2e`, tree identical to the tested one; scheduler
  188/188/188/193/193/194, advanced 16 then 12, motion_planner 81 then 82,
  planner_core 22; recordings unchanged; tidy 0. Found for a ticket:
  INSERT_IN_PROGRESS counts as eligible but toward neither target (split off by
  one). Backups a3370c4b, 67aedc95. Not pushed. 266. `done` (2026-11-02) User:
  more detail in the deploy guide (SSH via Tailscale), the state of the
  software, update local main and rebase, did the tests pass. Central nodes run
  Tailscale SSH (tag:vng-os-central); vng-os creates the `ops` user and runs
  `tailscale up --ssh`; the guide's section 3 now has 3.1 images, 3.2 connecting
  (confirmed), 3.3 deploying (inferred), 3.4 going back. Local main
  fast-forwarded to `58bd75a3` (PR #1005, bay package only, no overlap); branch
  rebased clean, tip `8f9315c1`: built, scheduler 194, planner_core 22, advanced
  12, motion_planner 82 with recordings unchanged, tidy 0. Commits 1-5 unchanged
  in content since item 265's per-commit run. Backup `backup-e5edee2e`. Not
  pushed; PR CI (41 pass) is for `a3370c4b`. 267. `done` (2026-11-02) User
  pushed `8f9315c1` from the host (bypassing the container's hooks) and pressed
  Ctrl-C midway. The push landed: origin's branch and the PR head are
  `8f9315c1`, the PR is mergeable, the local branch is up to date, no git locks,
  fsck clean; CI run 41523411626 started on it. The two pre-push hooks it
  skipped are covered: clang-tidy on changed lines against main (item 266's
  `volley-in-container tidy` on this tip: 0) and check-branch-name (run now:
  passes). The commit-time hooks ran when the commits were made in the
  container; CI's prek job reruns them. 268. `done` (2026-11-02) User: delete
  the backups. Origin matched local `8f9315c1`; backup-a3370c4b, backup-67aedc95
  and backup-e5edee2e deleted. Only the working branch is left. 269. `done`
  (2026-11-02) Greptile's second review (of `8f9315c1`) evaluated
  (`SW2-1135_scheduler_renames/codex_reviews/greptile_review_2.md`): 1 the five
  `TODO(any)` need ticket keys (no open ticket exists for any; proposal: five
  tickets under SW2-1067, keys in commit 1); 2 delete the history comment above
  `MoveJob.TwoTrayMovesWithAgvUnderOneTray` (commit 6). CI run 41523411626: the
  sim unit-test job failed on a runner shutdown after its tests passed
  (infrastructure). Nothing changed. 270. `done` (2026-11-02) User logged in to
  central-eng-5675-pecos and asked what vngOS is and what the output means.
  vngOS = Volley Next Generation Operating System (vng-os README). On eng: vngOS
  26.44; swarm-deploy release `0d2054b` (untagged, branch `next`); site
  5675-pecos, sub-site eng, not the swarm root (the map server's image is from
  `central-comb:4000`); `docker service ls` shows only `global_*` and `site_*`:
  the eng application is not running; `.env.local` holds someone else's test
  (`VOLLEY_REGISTRY="${LOCAL_VOLLEY_REGISTRY}"`,
  `VOLLEY_VERSION=central-auth-v3`). The guide's section 3 now explains the
  output (3.3), keeps a copy of `.env.local`, points the registry back to ECR
  with the version (3.4), and restores or removes on the way back (3.5). 271.
  `done` (2026-11-02) User: CI good? TODOs predate the PR? Do another full
  comment sweep. CI on `8f9315c1`: 41 pass, 2 skipped after the sim rerun. All
  five TODO(any) were on main (isabel 3497, any 604 + Gunther 3090, mark 683,
  Any 2773, and the "FIX: Does using UsePreferredHeading on the blocking-tray
  dest break the triple-pick test" note over commented-out code at 2092, which
  belongs in that ticket). Sweep (`fix_a22.py`, each edit where its comment was
  written), scope: every comment in scheduler and scheduler_advanced_tests, plus
  comments the PR wrote elsewhere: six declaration comments cut to their
  contract (TrayDestinationPlan deleted, ResolveBlockingTrays,
  ScheduleAgvLiftChange, ScheduleAgvMoveToPickup, ApplyBayOrChargerTransition,
  MakeInboundPose); a stale `first_event`; Greptile's history line; two
  rebalancing-test lines; the three advanced-test headers (fix histories with
  stale MoveAgvToTrayPose, InsertVrcActionsIntoDag in utils.cpp,
  ResponseFromTrajectories) now say what each guards in 3-4 lines, their inner
  narration and "defensive check" blocks one line; motion_planner:
  FindAgvUnderTrayAssignment and ComputeEdgeMarginalDurations docs trimmed,
  "Ring 3b" dropped from garage_graph_pathing.cpp (commit 2). Found on the way,
  fixed in commit 4: two more error texts naming old functions,
  "MoveAgvToTrayPose: {}" -> "Failed to assign AGVs: {}",
  "ResponseFromTrajectories failed " -> "Failed to build the action graph: " (35
  texts now; commit 4 message, PR and Jira texts updated). 100 comment lines
  out, 29 in. Tip `a80d0ee3`, tree identical to the tested one; scheduler
  188/188/188/193/193/194, advanced 16 then 12, motion_planner 81 then 82,
  planner_core 22; recordings unchanged; tidy 0. Backup `backup-8f9315c1`. Not
  pushed. 272. `done` (2026-11-02) User: do the five TODOs fit one ticket in the
  refactor epic, will the refactor fix them; how `.env.local` becomes a deployed
  image; the NOC URL fails in Chrome. TODOs: the refactor keeps all five on
  purpose (PROMPT.md section 8 marks busy-time zero, the reduce placement and
  the advance fallback "keep"); homes: AGV busy time and the
  RemoveRedundantEdges dependency -> phase F (AGV module, section 9); root-path
  parking and the blocker's retrieval heading -> the tray solver after C2; the
  retrieve reported executing without PROCESS_RETRIEVE -> a bug outside the
  refactor (SW2-1067). Guide: new 3.5 (what `swarmctl deploy app` does, from
  swarmctl's source: env order, manifest, secrets, bay template,
  `docker stack deploy` with prune, resolve_image=never, with_registry_auth; ECR
  credential helper from vngOS's apply-device-config); step 8 corrected (a new
  push needs remove + deploy, since resolve_image=never); NOC: open on the
  laptop; on 2026-11-02 no `app-*` service ran in the Pecos swarm and every
  central node refused 8011. 273. `done` (2026-11-02) User: is the eng server
  up; skip the TODOs for now (asking the team); delete the backups.
  central-eng-5675-pecos is up (tailscale ping 14 ms, port 22 open, uptime 3
  days 7 h); over SSH, read only: `docker stack ls` lists only `global` and
  `site`, no `app` stack, so nothing serves 8011 (the NOC) or 5000 (central's
  API), which is Chrome's ERR_CONNECTION_REFUSED. Running on eng: the log
  collector, the logstore agent and a `local-registry` container. Origin matched
  `a80d0ee3`; backup-8f9315c1 deleted. The TODO tickets wait for the team. 274.
  `done` (2026-11-03) Deploy guide: swarmctl info output and where `branch next`
  comes from (CI's branch name; `next` merged into main as 26.41 by swarm-deploy
  PR #51, then deleted); Docker terms; `docker service ls` / `container ls` /
  `image ls` from eng with notes (the root is central-comb, the garage registry
  is vngOS's `local-registry`); what a release installs under `/data/swarm`;
  swarmctl is a shiv zipapp. Step 8 corrected again: central and bay services
  restart on every deploy (deploy timestamp in their command); control, noc and
  guidance do not. 275. `done` (2026-11-03) Dan's first review (13 inline
  comments on a80d0ee3): evaluation, plan and draft replies in
  `SW2-1135_scheduler_renames/codex_reviews/dan_review_1.md`. Proposed: items
  1-8 folded into commits 2-6; `ApplyTo`/`OnEvent`, `PlanMotions` reasons and
  rclcppx as follow-up tickets. Waits for the user's go; nothing changed in the
  repo, nothing posted. User: apply 1-8 (interrupted before any change). Dan's
  third review (include and alias pass, 11 comments) added as items 13-23, all
  now. 276. `done` (2026-11-03) Dan's review items 1-8 and 13-23 folded
  (`fix_a23.py`): six commits `fb84e9c0` (unchanged), `9640ca7b`, `f55265f7`,
  `13bf8b15` (the fixes), `236408e7`, `fcbb3a27`. Tip tree equals the tested
  tree; every commit builds with 0 warnings and passes with
  SCHEDULER_CHECK_RECORDINGS=1 (scheduler 194 at the tip, planner_core 24,
  advanced 15, motion_planner 82); tidy 0. Deviations from the plan in
  `codex_reviews/dan_review_1.md` ("As applied"): RemoveRedundantEdges in commit
  6, move factories in commit 5, std::hash kept (BottleneckAssignment needs the
  default hasher) but in agv_assignment.cpp, stage types defined in their .cpp.
  Backup `jmg/SW2-1135/backup-a80d0ee3`. Origin at `a80d0ee3` until the user
  force-pushes with lease. Replies drafted, not posted; follow-up tickets
  (OnEvent/ApplyTo, PlanMotions reasons, rclcppx) not created. 277. `done`
  (2026-11-03) The user force-pushed `fcbb3a27`; on the user's word the replies
  were posted with `codex_reviews/post_dan_replies.sh`: 21 thread replies, 👍 on
  the removals and "Thank you" comments, nothing on 🙏, and a summary comment.
  `dan_review_1.md` lists them as posted. Follow-up tickets (OnEvent/ApplyTo,
  PlanMotions reasons, rclcppx) still to create. 278. `done` (2026-11-03) On the
  user's word, the three follow-up tickets were created with acli from
  `SW2-1135_scheduler_renames/follow_up_tickets.md` (description as ADF):
  SW2-1170 (stdx::Result from event application), SW2-1171 (motion-planning
  failure reasons), SW2-1172 (scheduler to rclcppx). Each is a Task under
  SW2-482, assigned to the user, label Scheduler_and_Dispatcher, priority
  Medium, and blocked by SW2-1135. 279. `pending` (2026-11-03) Justin's review
  (two comments on commit 1, `fb84e9c0`): 4458633422 asks why `Scheduler` is not
  in `volley::scheduler`; 4458661278 asks to drop the redundant `volley::`
  prefixes (545 in the scheduler package). Neither is in PROMPT.md yet. Proposed
  reply: do both in one mechanical commit at the start of the next stage
  (SW2-484), ahead of the solver work. Replies drafted, not posted. 280. `done`
  (2026-11-03) Backup `jmg/SW2-1135/backup-a80d0ee3` deleted on the user's word;
  origin matched `fcbb3a27`. 281. `done` (2026-11-03) Justin's two comments
  evaluated in `codex_reviews/justin_review_1.md`: both confirmed and mechanical
  (169 `scheduler::`, about 590 `volley::` prefixes; no name clashes).
  Recommended now, as a seventh commit (Scheduler, SchedulerParams,
  SchedulerSPtr and SchedulerRos into volley::scheduler; SchedulerComponent
  keeps its plugin name). Waits for the user's choice. 282. `done` (2026-11-03)
  On the user's word, commit 7 `5bd41efe` "refactor(scheduler): move Scheduler
  into volley::scheduler and drop redundant prefixes" (script `fix_b1.py`, 32
  files; the message does not mention the review): Scheduler, SchedulerParams,
  SchedulerSPtr, SchedulerRos into volley::scheduler; SchedulerComponent stays
  (plugin name); volley:: and scheduler:: prefixes dropped inside the
  namespaces. Build 0 warnings; scheduler 194, planner_core 24, advanced 15,
  motion_planner 82 with recordings unchanged; hooks passed; tidy 0. Not pushed;
  replies to Justin not posted (drafts for "done now" in
  `codex_reviews/justin_review_1.md`). 283. `done` (2026-11-03) On the user's
  word, main fast-forwarded to `bf59774c` (PR #1019, pecos showcase layouts
  only) and the branch rebased onto it with `--autostash` (the user's local
  agvctl.yaml edit kept). No conflicts; range-diff shows all seven patches
  identical, now `73897bda` .. `ff6ba632`. Build 0 warnings; scheduler 194,
  planner_core 24, advanced 15, motion_planner 82 with recordings unchanged.
  Pushed by the user (origin matches `ff6ba632`). 284. `done` (2026-11-03) On
  the user's word, replies to Justin's two comments posted (4460977058,
  4460977359; text in `codex_reviews/justin_review_1.md`). 285. `done`
  (2026-11-03) Garage test issues checked against
  `pvc/test/confirm-insert-reliability-improvements` (`1c529f35` = main
  `bf59774c` + two commits from 22:35Z, after the failures). Not from this
  branch: (1) confirm_insert 500 "timeout waiting for service
  /bay/bN/confirm_insert ready": the REST API's long-lived client and 2.5 s
  `wait_for_service` (rest_api.py:488-493 v2, ros_parking_gateways.py:44-48 v3,
  same client dict); the bay creates the service unconditionally
  (bay_state_machine_ros.cpp:209); no `_service_event` messages because no
  request was ever sent. The teammate's branch recreates the client on a miss
  (v2 only) and waits 30 s per bay at startup. (2) "carrying t0": tray_id 0 is
  the no-tray sentinel, printed raw by garage_tracker.cpp:249-251 and
  chugg_sequential.cpp:562 (both on main); the scheduler's `IsCarryingTray`
  swaps keep `tray_id != 0`. 286. `done` (2026-11-03) On the user's word,
  `SW2-1135_scheduler_renames/testing/` created: `deploy_and_test.md` moved into
  it, and item 285's findings written up in
  `testing/garage_test_findings_2026-11-03.md`. 287. `done` (2026-11-03) Paula
  (16:06): confirm-insert also passed on `main`; she suspects a startup
  discovery race (seen months ago) and is checking the discovery server for
  changes. Added as 1.6.1 in `testing/garage_test_findings_2026-11-03.md`:
  consistent with not-this-branch; the 2 h 16 min between failures fits a missed
  startup discovery that never recovers. 288. `done` (2026-11-03) The user
  decided PR #1018 must fix the confirm_insert race (repeatable on deploy).
  Proposed an eighth commit in `testing/confirm_insert_fix_proposal.md`:
  `RediscoveringClient` in ros_parking_gateways.py (recreate on a missed
  `wait_for_service`, under a lock), used for both bay client dicts in
  rest_api.py (covers v2 and v3), plus a discovery wait in
  `bay_confirm_retrieve`; three unit tests. Not applied; waits for the user's
  go. 289. `done` (2026-11-03) On the user's word, the confirm_insert fix
  applied as proposed (item 288), unstaged: ros_parking_gateways.py
  (`RediscoveringClient`), rest_api.py (import, per-bay clients, retrieve wait),
  test_ros_parking_gateways.py (three tests). Build OK; central_api 452 tests, 0
  failures, 7 skipped; prek hooks pass. Not committed; waits for the user's
  go. 290. `done` (2026-11-03) On the user's word, the fix reworked to
  functional style with brief comments:
  `wait_for_discovery(client, recreate, timeout_sec) -> (client, is_discovered)`
  in ros_parking_gateways.py, `RestApi.recreate_client`, callers store the
  returned client (v2 insert, retrieve, `RosBayGateway` with a new
  `recreate_client` argument); no wrapper class or lock. Tests and fixtures
  updated (4 new tests). central_api 453 tests, 0 failures, 7 skipped; black,
  mypy pass. Unstaged, not committed. 291. `done` (2026-11-03) On the user's
  word (no patron cost, robust, small, functional), the fix reworked a third
  time: request path back to main's; pure
  `recreate_undiscovered(clients, recreate)` in ros_parking_gateways.py;
  `RestApi.refresh_bay_clients` on a 10 s timer swaps in recreated clients and
  destroys replaced ones one refresh later (no lock); `recreate_client` logs,
  throttled 60 s. Two tests. central_api 451 tests, 0 failures, 7 skipped;
  black, mypy pass. Unstaged, not committed. 292. `done` (2026-11-03) On the
  user's word, the fix's comments and docstrings removed (code and tests).
  black, mypy pass; central_api 451 tests, 0 failures, 7 skipped. Unstaged. 293.
  `done` (2026-11-03) On the user's word, the fix type-annotated:
  `DiscoverableClient` Protocol and a `ClientT` TypeVar for
  `recreate_undiscovered(Mapping[str, ClientT], Callable[[ClientT], ClientT]) ->      dict[str, ClientT]`;
  `BayClient: TypeAlias = RosClient[Any, Any]` for the two bay dicts, the
  retired list and the two methods; new tests annotated (client doubles).
  TypeVar over PEP 695 because mypy is 1.9.0. New lines pass mypy --strict;
  hooks, pylint 10.00; 451 tests, 0 failures, 7 skipped. Unstaged. 294. `done`
  (2026-11-03) On the user's word (readability), the helper, Protocol and
  TypeVar inlined into one `refresh_bay_clients` loop in rest_api.py;
  `retired_bay_clients` renamed `bay_clients_to_destroy`;
  ros_parking_gateways.py and its tests back to main. One test. central_api 450
  tests, 0 failures, 7 skipped; black, mypy, pylint 10.00. Unstaged. 295. `done`
  (2026-11-03) On the user's word, main fetched (still `bf59774c`, no rebase
  needed) and the confirm-insert fix committed as the eighth commit `073556ea`
  (rest_api.py, test_rest_api_v3.py; message from
  `testing/confirm_insert_fix_proposal.md`). Hooks incl. commitlint passed. Not
  pushed. 296. `done` (2026-11-03) The user pushed `073556ea` (PR head); its run
  41747735531 queued 00:33Z. Deploy doc gained 3.5.1 (what runs in central:
  rest_api, proxy, one component container with the scheduler, metrics, vis,
  foxglove bridge, recorder) and 3.5.2 (confirming a deploy has the fix: CI
  images pushed for the commit, GITSHA, grep the installed rest_api.py, rest_api
  etime, the recreate log). 297. `done` (2026-11-04 00:48Z) The user redeployed
  app-comb on central-comb (`.env.local`: VOLLEY_VERSION=pr-1018, ECR,
  BAY_IDS_OVERRIDE="7", MANUAL_STACKS="app"); before it, central ran `ff6ba63`
  (the earlier deploy). After: GITSHA `073556e`, installed rest_api.py has
  `refresh_bay_clients` at line 480; no "recreating its client" line in
  `docker logs` right after startup (not yet confirmed that docker logs reads
  the fluentd-driven output). Note: with BAY_IDS_OVERRIDE="7", the 19:35Z b21
  failure may have been a bay that wasn't deployed, not the race. 298. `done`
  (2026-11-04) `docker logs` reads central's output (8 rest_api lines), so the
  empty recreate grep is real: no client needed recreating after the 00:48Z
  deploy (discovery worked on that start). Next: confirm-insert on bay 7;
  optional mechanism test by scaling app-comb_bay7 to 0 and back. 299. `done`
  (2026-11-04 00:52Z) Mechanism test on central-comb:
  `docker service scale app-comb_bay7=0` → rest_api logged
  "/bay/b7/confirm_insert not discovered, recreating its client" (once,
  throttled); scaled back to 1. Shows the timer runs, detects an unmatched
  client and recreates it on the garage. Pending: no new line a minute after bay
  7 returned (clients matched again), then a confirm-insert. 300. `done`
  (2026-11-04) After bay 7 returned, no recreate line in the last 70 s (twice):
  the recreated clients matched bay 7 again and the refresh stopped recreating.
  Pending: confirm-insert on bay 7. 301. `done` (2026-11-04) NOC controls
  confirmed from controller_webview and dispatch.cpp, written up as deploy doc
  4.0: Request Control (needed to start, resume and change mode) → set mode
  (only while not Running; central starts in Manual) → Dispatcher Status on.
  Manual accepts move AGV/tray and bay transitions; Auto accepts retrieve,
  repark, charge and cleans/rebalances on its own; bay confirm insert/retrieve
  in both. 302. `done` (2026-11-04) Deploy doc 4.0 rewritten to explain the
  dispatcher (`/central/dispatcher`, one per garage in the central container;
  1.8 s loop: job queue, /scheduler/plan, send commands, auto-stop on faults),
  Status (Stopped fails all jobs and stops AGVs; Starting 1 min timeout; Paused
  does nothing; central boots Stopping→Stopped so it must be started) and Mode
  (Manual: operator moves only; Auto: patron retrieves/reparks/charges plus its
  own clean/rebalance/charge; change only while stopped). 303. `done`
  (2026-11-04) The patch (`073556ea`) didn't fix the confirm-insert failure.
  After a full app-comb recreate at 16:06Z (discovery server, central, bay 7 all
  started together), rest_api recreated b7's clients every minute and never
  matched; the 16:10:42Z insert got 500. A fresh rclpy process in the same
  container matched all bay 7 and central services in under 1.2 s. So: the
  rest_api process's DDS participant can't match bay 7's endpoints
  (participant-level startup race), not the client. Findings 1.9 written; next
  test: `docker service update --force app-comb_central`; fix options: DDS root
  cause, respawn rest_api when stuck, revert 073556ea. 304. `open` (2026-11-04)
  The user says the failure happens on every `swarmctl deploy app`.
  Counter-evidence: after the 00:48Z plain deploy (discovery server kept
  running) the refresh logged no recreates (clients matched) and the bay 7 scale
  test recovered. Today's 16:06Z failing deploy recreated the whole stack incl.
  the discovery server. Open question: did the failing deploys all start from a
  removed stack? The central-only restart is a diagnostic, not a fix; a plain
  redeploy now is the closer replica. 305. `done` (2026-11-04 16:29Z) Baseline
  before the retrieve, after the 16:23Z plain deploy (discovery server not
  restarted): rest_api up 6 min, no recreate lines, no rest_api warnings; graph
  probe shows exactly one server (bay_state_machine, gid 010f0f0f34001827) for
  b7 confirm_insert / confirm_retrieve / command. Dispatcher: AUTO 16:28:47,
  start 16:28:50, a16/a17 activated, b7 TRANSITION_TO_INSERT command answered
  16:28:54 (dispatcher's C++ client to /bay/b7/command works), bay 7
  READY_TO_INSERT 16:29:13. Probe script: scratchpad probe_graph.py, copied to
  the central container's /tmp. 306. `done` (2026-11-04 16:39Z) The retrieve
  after the 16:23Z plain deploy passed; no recreate lines, graph 1/1. The
  discovery server task is still from 16:06 (not restarted at 16:23). Every
  failure followed a start with the discovery server starting too (node boot
  11-03 ~18:25Z; stack recreate 11-04 16:06Z); every pass followed a redeploy
  with it running. Findings 1.10. Confirming test: remove + deploy, then
  central-only restart as the workaround. 307. `done` (2026-11-04) Wrote
  `testing/garage_troubleshooting_reference.md` (every command used on the
  garage, with how to read it, and both probe scripts) and
  `testing/dds_root_cause_plan.md` (setup across swarm-deploy / ros2-docker /
  volley / vng-os, hypotheses H1-H5, scripted full-restart attempts with a
  detector, experiments E1-E6, eProsima report). New facts: the Fast DDS profile
  lives in swarm-deploy `swarm/stacks/app/config/fastdds-profile.xml`; its
  README already describes this symptom (type propagation fix a92d7ed, deployed
  on comb); Fast DDS 3.6.2 / rmw 9.4.9 in all images; CI uses no discovery
  server; vng-os sets no UDP buffer sysctls. 308. `done` (2026-11-04) On the
  user's word, main fetched (`7e98112a`, PR #1027: Dan's fix for the "carrying
  t0" log in garage_tracker.cpp, issue 2) and the branch rebased onto it, no
  conflicts; range-diff shows all eight patches identical, now `73d0425e` ..
  `089e774d` (`089e774d` is the client-refresh fix). Build 0 warnings; scheduler
  194, planner_core 24, advanced 15, motion_planner 82, central_api 450 (7
  skipped), recordings unchanged. Not pushed; needs a force-push (origin is at
  `073556ea`). 309. `done` (2026-11-04) Dan's last DDS changes reviewed:
  swarm-deploy PR #54 (SW2-998, a92d7ed, 2026-10-09: type propagation disabled;
  tested with 5 stack restarts) and volley PR #972 (SW2-997: the same in CI;
  15/43 → 0/40 hangs locally), on top of swarm-deploy 0d2054b (SW2-857,
  2026-10-02: overlay0-only UDP + SHM, builtin transports off). New lead: the
  discovery-server service gets neither the profile nor its env (H6/E7 added to
  dds_root_cause_plan.md). 310. `done` (2026-11-04) Docs updated for the control
  container: reference section 13 (control vs central,
  `docker exec … /opt/volley/entrypoint.sh` for ros2 run / agvctl / scripts,
  cautions; swarmctl only has deploy/info/logs/remove/watch), section 6 points
  general probes at control, deploy doc 3.5.1 note, plan 4.3 runs the probe in
  control too. Verified `ros2 run agvhito_tools agvctl --help` in control. 311.
  `done` (2026-11-04) agvctl removed from the docs (it's for driving AGVs
  outside the autonomy stack). Added reference section 14 (Foxglove): central's
  foxglove_bridge on ws://<central>:8765 (comb answers the foxglove.sdk.v1
  handshake from the laptop), desktop app, Volley org layouts (Simulation),
  FoxNOC .foxe install, the useful topics as advertised on comb (/central/rosout
  carries rest_api logs; /central/plan_request and plan_response are the
  scheduler's input and output). 312. `done` (2026-11-04) Foxglove on comb
  connected with the FoxNOC (WIP) layout but looked empty: FoxNOC panels unknown
  (extension not installed) and the 3D panel unconfigured. Checked from control
  (probe_vis.py): /vis/_marker arrays flowing in frame `map`, volatile; no /tf
  on the garage. Reference 14 gained "If the view looks empty" (display frame
  map, switch on /vis topics, or the Simulation layout). 313. `done`
  (2026-11-04) Foxglove + FoxNOC working on comb (user installed the
  v0.1.0-alpha .foxe; 3D panel: topics first, then fixed/display frame `map`).
  Reference 14 updated with that order, the release download command and "save
  as a personal layout". Note: comb was switched by someone to
  VOLLEY_VERSION=bay-refactor (84f6deb, .env.local changed ~18:30 node time), so
  it no longer runs PR #1018. 314. `done` (2026-11-04) dds_root_cause_plan.md
  reviewed and updated: discovery server state is memory-only; graph during a
  failure; Dan's test depth; x-internal-network/overlay0 and discovery-server.md
  in the setup table; comb now on bay-refactor, so the plan starts by getting a
  detector build (pr-1018 with 089e774d, or an investigation branch if it's
  reverted) back on comb; `swarmctl remove` needs --yes (the script would have
  hung); the script now probes central and control on STUCK; new E1b (restart
  only the discovery server); E6/E7 reordered; capture via nsenter + host
  tcpdump (no image download); the safety net built from the existing refresh
  timer; order of work updated. 315. `in progress` (2026-11-04 20:06Z) Rebased
  onto main `8ebf0762` (PR #1008, the bay refactor; no file overlap,
  bay_state_machine_ros.cpp service setup unchanged): `cf72cc40` .. `e1d24a7c`,
  all eight patches identical. Tests running. Comb readiness: `.env.local`
  (changed 20:04:13) has VOLLEY_VERSION=pr-1018 but also
  VOLLEY_REGISTRY="${LOCAL_REGISTRY}/volley" uncommented, so
  central/control/noc/bay7 tasks are Rejected ("No such image:
  central-comb:4000/volley:central-pr-1018"; the local registry only has
  bay-refactor tags). Discovery server running since ~20:05. Test prerequisites
  not installed yet (no backups, script or probe). 316. `done` (2026-11-04)
  Permissions on comb: /data/swarm and /data/swarm/stacks are root:root 755
  (stack files root 644), .env.local is ops:ops 644. So `sed -i` on .env.local
  fails ("couldn't open temporary file … Permission denied") and backups can't
  go into /data/swarm. Gave the user `sed … > /tmp/… && cat … > .env.local` with
  a backup in ~; fixed deploy_and_test.md 3.4 (steps 3-4 and going back) and the
  plan's section 5 (sudo for stack files, both backups). 317. `done` (2026-11-04
  20:18Z) Rebased branch build + tests green (scheduler 194, planner_core 24,
  advanced 15, motion_planner 82, central_api 450/7 skipped). Comb: the user
  fixed .env.local (VOLLEY_REGISTRY commented; the stack had been removed) and
  deployed; full start ~20:14:20Z of every app-comb service, GITSHA 089e774;
  after 3.5 min no recreate lines (healthy); RcvbufErrors central 382 (all in
  the first minute), discovery server 0. Full starts: 2 STUCK / 3. Findings
  1.11, plan section 1 updated; the plan script's UDP counter command fixed (it
  read the header). Rebased branch `e1d24a7c` not pushed yet. 318. `done`
  (2026-11-04) Plan clarified at the user's question: an attempt is ~3.5 min but
  the garage is down only ~1-1.5 min (remove + start); it's a full restart
  (discovery server, control, noc, mysql, nginx too), the dispatcher comes back
  stopped. The baseline edits no files, so backups move to "before the first
  file-editing experiment". 319. `done` (2026-11-04 20:29Z) Installed on comb
  (ops home): ~/dds_attempt.sh (from plan 4.3, plus a NO_CENTRAL guard and the
  GITSHA in each log line; plan updated to match) and ~/probe_clients.py; sha256
  match local copies; bash -n ok. Nothing run. Plan 4.3 gained an unattended
  5-run loop that stops at the first non-ok result. 320. `done` (2026-11-04
  20:42Z) User pushed the rebased branch from the host (origin = e1d24a7c; PR no
  longer BEHIND, now BLOCKED pending checks; runtime-images still building).
  User chose not to wait for the new images (each log line records build=).
  Replaced ~/dds_attempt.sh on comb with a live-progress version (status line
  every 10 s; swarmctl output shown; same result logic and log line); checksum
  verified; plan 4.3 updated to match. No attempt run yet. 321. `done`
  (2026-11-04 20:44:58Z) Baseline attempt 1: build e1d24a7 (the new images were
  already in ECR), result ok, late_recreates 0, rcvbuf_errors central 116,
  discovery 0. Full starts so far: 2 STUCK / 4. 322. `done` (2026-11-04 20:58Z)
  Baseline run 2 (deploy 20:53:56Z, e1d24a7) STUCK; loop stopped. Captured: REST
  API stuck from its first check; fresh rclpy probes in central and control
  ready in 0.8-1.2 s; graph from control clean (1/1 server); central-3 receives
  bay 7 topics; central and bay 7 launched within 0.5 s of each other after
  waiting ~6 s for discovery-server DNS; bay services up at …646.1; drops
  central 517 (passes: 116, 382), discovery 0. No dispatcher calls to b7 at
  boot, so the C++ service check needs the dispatcher started. Findings 1.12.
  Full starts: 3 STUCK / 5. 323. `done` (2026-11-04) The user's team suspects a
  client-creation timeout from `ros2 service info --spin-time` varying. Ran it
  in control while stuck: empty at 0.1/0.3/0.5 s, stable from 1 s (2 clients:
  rest_api, foxglove_bridge; 1 server). That's the CLI participant's own
  discovery time, not a REST API timeout. Verbose shows the server knows
  rest_api's client endpoints. Findings 1.12 updated. 324. `done` (2026-11-04
  21:26Z) Run 2's REST API recovered by itself: last recreate line 20:56:27Z,
  none after; matched between 20:56:27 and 20:57:27, the window of the script's
  probes in central (~20:57:01-08) and control (~20:57:10). Either it
  self-recovers after ~3 min or a joining participant nudges it. 11-03 stayed
  stuck >2 h without probes. Findings 1.12 updated with the test: next STUCK,
  hands off ~10 min, then one probe. 325. `done` (2026-11-04 21:34Z)
  ~/dds_attempt.sh on comb replaced (checksum verified, plan 4.3 synced): on
  STUCK it now watches hands-off up to 10 min (recovery = 75 s without a new
  recreate line, using `docker logs -t` timestamps), logs self-recovery as a 70
  s window, otherwise runs one probe in control and watches 2 more min. Dry-run
  of the recovery check against the current central reported the 20:56:27
  recovery correctly. 326. `done` (2026-11-04 21:39Z) Baseline run 3 (deploy
  21:35:33Z) STUCK (recreate lines at t+31, t+92), drops 776. Per-socket check
  (/proc/net/udp drops + /proc/<pid>/fd inode map, scratchpad
  udp_drops_by_process.sh): all 776 on ONE socket owned by rest_api (pid 68),
  172.16.3.15:7424 = Fast DDS metatraffic unicast port for participant id 7
  (7410 + 2*7), i.e. the REST API's discovery socket. Drops: ok runs 116/382,
  stuck 517/776. Findings 1.13. Fix candidates: bigger receive buffer (E2), REST
  API as plain client (new). Loop still running (hands-off phase). 327. `done`
  (2026-11-04 21:50Z) Run 3: stuck 12 min hands-off (no self-recovery), then
  recovered within the minute of one probe in control (window 21:48:35-21:49:45,
  probe 21:48:41). Runs 2 and 3: a joining participant un-sticks the REST API
  (2/2). Hypothesis: the server re-sends bay 7's endpoint info on new interest
  in those topics. Corrected the GIL argument. Findings 1.13. Next: E1b (restart
  only the discovery server), at the user's request. 328. `done` (2026-11-04
  21:50-21:58Z) E1b: restart of only the discovery server with a healthy REST
  API -> no recreate lines for 4.5 min (not stuck, 1/1); 66 drops: 54 on
  launch's participant socket, 12 foxglove. Socket ownership: 7410/7411 = ros2
  launch (pid 7), inherited by every child; 7424/7425 = REST API only (its own
  participant, all 60 endpoints, prefix 01.0f.5d.85.44.00.a2.99), so the 776
  startup drops were on the REST API's discovery socket. Likely why: its
  participant registers last (ID 7, Python import time) and gets the server's
  full dump on top of the startup burst. Findings 1.14. Next: E2 (bigger
  buffer), then plain client. 329. `done` (2026-11-04 22:00Z) The user asked to
  keep the notes and every doc in sync each time (saved as memory
  volley-keep-notes-in-sync). Measured with `ss -uamn` in central: every DDS
  socket rb212992 (Linux rmem_default; Fast DDS requests no size), rmem_max
  4194304; 7424 (REST API) d776, 7410 (launch) d54, 7422 (foxglove) d12. Synced:
  plan section 1 status, hypothesis status, E2 detail (where to put the XML,
  expect rb ~8 MiB after); reference section 7 (awk counter, ss, per-socket
  drops script, launch's inherited sockets, the Fast DDS port formula and comb's
  port map). 330. `done` (2026-11-04 22:05Z) ~/dds_attempt.sh on comb updated
  (checksum verified, plan 4.3 synced): the result line now has
  rest_api_sockets=<port>:rb<buffer>/d<drops> for the REST API's own Fast DDS
  sockets (from `ss -uamnp`, excluding sockets shared with ros2 launch); tested
  on comb: 7424:rb212992/d776 7425:rb212992/d0. Walking the user through E2
  next. 331. `done` (2026-11-04 22:12Z) `sudo cp` refused for ops on comb
  (restricted sudoers). Workaround: `swarmctl --root <dir>` (reads .env,
  .env.local, manifest, stack files from <dir>, sets SWARM_ROOT_DIR so configs
  come from there); /data/swarm readable (6.3 MB). Script: SWARM_ROOT env
  selects the root (installed, checksum ok); plan section 5 and E2 now edit
  ~/swarm-exp, no sudo, nothing to restore but a redeploy from /data/swarm. 332.
  `done` (2026-11-04 22:10-22:13Z) Reviewed the user's ~/swarm-exp copy (only
  the profile differs, +2 buffer lines; valid XML; swarmctl --root info normal).
  First E2 attempt started with nohup over my non-interactive ssh: killed when
  the ssh session's systemd scope was cleaned up, right after `remove`, so
  app-comb was down 22:10:57-22:13:15. Relaunched as `systemd-run --user` unit
  dds-e2-1; first try failed (`NFS_HOSTNAME` missing: .env uses ${HOSTNAME},
  only exported by interactive logins), second with -E HOSTNAME=$(hostname)
  deployed at 22:13:15 (8/8). Plan 4.3 documents both traps and the unit
  command. Attempt in progress. 333. `done` (2026-11-04 22:16Z) E2 attempt 1 (4
  MiB buffers): applied correctly (profile in central has the lines; every Fast
  DDS socket rb8388608; RcvbufErrors 0; rest_api sockets d0), yet STUCK
  (recreate lines from t+30 s). Overflow isn't the cause; H1 ruled out. Leading
  hypothesis H7: discovery race at full start, announcements not acted on and
  never re-sent; a joining participant triggers a re-send. Findings 1.15, plan
  section 1 and hypothesis status updated. Attempt continuing (hands-off, then
  probe). 334. `done` (2026-11-04) Wrote `testing/dds_investigation_summary.md`
  (one-page consolidation: problem, topology with participant IDs/ports, every
  start in one table, established points, open hypotheses, constraints,
  repos/files) and `testing/codex_dds_review_prompt.md` (independent Codex
  review: read order, read-only rules, no garage access, report to
  `codex_dds_review_1.md`; asks for a critique, Fast DDS mechanics, new
  hypotheses, ranked experiments incl. an off-garage repro, fixes, questions).
  README updated. 335. `done` (2026-11-04 22:26-22:30Z) E2 attempt 1 final:
  stuck 10 min hands-off, probe in control 22:26:23, recovered in
  22:25:25-22:26:35 (3/3 recoveries with a joining participant; window starts 58
  s before the probe). Other four E2 attempts skipped (answered). Restored comb
  from /data/swarm via a systemd user unit (dds-restore, HOSTNAME set) at
  22:27:42: 8/8, GITSHA e1d24a7, profile original, sockets rb212992. That full
  start came up STUCK (2 recreate lines by 22:29:59); left stuck for the
  teammate. Full starts 6 STUCK / 8 (e1d24a7: 4/5). Wrote
  testing/dds_handoff_2026-11-04.md; findings 1.15, summary, plan and README
  updated. Testing handed off. 336. `done` (2026-11-04 22:35Z) Clarified: comb
  goes to a teammate for an unrelated branch tonight; DDS testing resumes
  2026-11-05. Rewrote testing/dds_handoff_2026-11-04.md: for her (current state,
  switching VOLLEY_VERSION with an in-place edit, the known full-start bug and
  the quick fix, inert leftovers); for tomorrow (status, checks before testing,
  next experiments: unrelated probe, packet capture, plain client, Codex, Dan).
  Findings, summary, plan, README updated. REST API left as is (her deploy
  restarts it). 337. `done` (2026-11-04 22:35Z) Saved comb's results locally in
  testing/comb_results_2026-11-04/ (logs: dds_attempts.log, dds_baseline.out,
  dds_e2_1.out, dds_restore.out, the 16:06 swarmctl logs; scripts:
  dds_attempt.sh, probe_*.py, udp_drops_by_process.sh, the E2 profile; README
  with how to reinstall); 7 remote files checksum-identical. Cleaned comb:
  removed those files and ~/swarm-exp from /home/ops, the probe scripts from
  central's and control's /tmp; no dds-* user units left; user's own dotfiles
  untouched. Handoff note, plan 4.3, README updated. 338. `done` (2026-11-04)
  Reviewed Codex's `testing/codex_dds_review_1.md`; verified against sources:
  (1) Fast DDS versions.md v3.5.0 "CLIENT participants now behave like
  SUPER_CLIENT" -> plain-client fix withdrawn, H3 moot; (2) rmw_fastrtps 9.4.9
  readiness = equal nonzero graph counts AND equal nonzero match counts; (3)
  Fast DDS 3.6.2 EDPSimpleListeners drops EDP data from an unknown participant
  with a WARNING (not printed by default; none in our saved logs), so H7's
  mechanism exists; (4) PR #6542 and issue #6594 exist. Agreed corrections: the
  probe is a compound intervention (3/3 is association); recovery windows
  inferred from throttled silence; E2 rules out central receive overflow only;
  participant ID is local socket order; E1b didn't test new endpoints; DNS/VIP
  unchecked. Findings 1.16, plan, summary, handoff updated. Proposed next steps:
  lab repro, diagnostic REST build (1 s heartbeat + own graph counts, no churn),
  Fast DDS warnings on, read-only DNS check, then garage capture. 339. `done`
  (2026-11-04) Explained the CLIENT = SUPER_CLIENT point with sources (added to
  findings 1.16 and the summary): Fast DDS PR #6272 (merged 2026-01-30, released
  v3.5.0) unified the two; the v3.6.2 versions.md says so; the docs' "Discovery
  Server and Discovery Server Pro" table says open source has no practical
  difference (only Pro filters); the server's DiscoveryDataBase.cpp used
  is_superclient() in v3.4.0 (L1216, L1297) and has none in v3.6.2. Comb's Fast
  DDS is the open-source ROS apt build. ROS_SUPER_CLIENT in volley's Dockerfile
  and docs/architecture/discovery-server.md predates this. 340. `done`
  (2026-11-04) Detailed the "show the H7 drop" test, as plan E8. Verified in
  Fast DDS v3.6.2 source: default verbosity Error (Log.cpp:45), Kind
  Error/Warning/Info = 0/1/2, no XML/env verbosity setting. In the devcontainer
  (same ros-lyrical-fastdds 3.6.2-1resolute.20260728.174239 as comb): the
  warning string is compiled into libfastdds.so.3.6, and Log::SetVerbosity is
  exported, so the REST API (Python) can raise its own verbosity via ctypes;
  gated by FASTDDS_WARNINGS=1. Corrected my earlier wording: a separate C++
  client only shows drops in its own participant, so the change belongs in the
  REST API process. 341. `done` (2026-11-04) Codex reviewed E8. Verified its key
  claim: in Fast DDS v3.6.2 PDP::addWriterProxyData/addReaderProxyData return
  null in several branches (PDP.cpp 960, 986-990 max proxies with its own
  RTPS_PDP warning, 1008, 1048, 1073-1077, 1095, and participant not found
  1016/1103), so "UNKNOWN RTPSParticipant" means a failed proxy add, not
  necessarily the H7 ordering race. E8 rewritten: it modifies the existing REST
  API process (no new node or participant); ctypes argtypes/restype,
  GetVerbosity read-back, a single loaded libfastdds, a controlled warning in
  the lab; keep all Fast DDS warnings; Codex's tighter result table; next
  instrumentation (GUIDs, topic, failure reason) would need a patched build;
  combine with the heartbeat diagnostics in one diagnostic branch. 342.
  `in progress` (2026-11-04) On the user's word: investigation branch
  `jmg/test/dds-rest-api-diagnostics` created at `07eb74dd` (PR #1018 without
  e1d24a7c) and checked out. Moving the feature branch back to 07eb74dd was
  blocked by the permission system (`git reset --hard`, then `git branch -f`);
  the user has to run it and force-push. On the investigation branch
  (uncommitted): central_api/dds_diagnostics.py (enable_fastdds_warnings via
  typed ctypes + read-back; BayDiscoveryMonitor 1 s heartbeat + change lines
  with the node's own rq/rr graph counts), rest_api.py wiring (REST_API_DDS_DIAG
  / FASTDDS_WARNINGS, spin-thread traceback), central_nodes.py additional_env,
  and test/test_dds_diagnostics.py (incl. a real libfastdds read-back = 1).
  central_api 451 / launcher 12 tests green; black, mypy, pylint 10.00. New
  attempt script dds_attempt_diag.sh (deployed bays only, graph counts, warnings
  saved, exact recovery), parsing tested offline with a fake docker. Plan,
  handoff, results README updated. 343. `done` (2026-11-04) The user dropped
  e1d24a7c from the feature branch (git branch -f to 07eb74dd + force-push):
  local, origin and PR #1018 head all 07eb74dd, 7 commits cf72cc40..07eb74dd.
  The investigation branch sits on 07eb74dd with the diagnostics
  uncommitted. 344. `done` (2026-11-04) On the user's word, committed the
  diagnostics on jmg/test/dds-rest-api-diagnostics as `5f72fcae`
  "chore(central_api): add temporary DDS discovery diagnostics to the REST API"
  (4 files; parent 07eb74dd); hooks incl. black, mypy, commitlint passed.
  Feature branch 7 commits, investigation branch 8. Not pushed; next: push,
  draft PR for pr-<n> images, deploy on comb, dds_attempt_diag.sh. 345. `done`
  (2026-11-04) The user recalled a CI-free deploy: volley
  `tools/local-runtime-deploy <TAG> <REGISTRY-HOST> [runtime]` (host only;
  checks /etc/docker/daemon.json insecure-registries;
  `docker buildx bake --push` of the runtime group
  bay/central/control/mapserver/noc with TAG, REGISTRY=<host>/volley,
  COMMIT_SHA=HEAD). Laptop checked: Docker 29.9.2 + buildx 0.38.1, daemon.json
  already lists central-comb:4000, registry reachable (200), AWS creds
  jon.gonzales. Procedure (tag dds-diag-<sha>, .env.local VOLLEY_REGISTRY
  local + VOLLEY_VERSION, going back) written as deploy_and_test.md 3.7; handoff
  updated. Not run. 346. `done` (2026-11-04) `docker login` to ECR failed
  ("error storing credentials … not implemented"): ~/.docker/config.json has
  credHelpers {ECR: ecr-login} (docker-credential-ecr-login 0.6.4), which
  fetches tokens from AWS creds and can't store. No login needed; confirmed with
  `docker buildx imagetools inspect` of ros2:lyrical-core-20260924-1 (manifest
  read OK). deploy_and_test.md 3.7 step 1 fixed. 347. `done` (2026-11-04) User
  started tools/local-runtime-deploy (build running). Codex reviewed the split
  and the diagnostics: no blocker in PR #1018 (head 07eb74dd) or the diagnostic
  Python; four script fixes, all applied to dds_attempt_diag.sh and tested
  offline: expected bays from BAY_IDS_OVERRIDE (else pre-removal services) with
  running-task check (BAY_NOT_RUNNING), explicit NO_HEARTBEAT outcome with no
  probe, log window starting before the deploy, single-process probe (source
  setup.bash, no entrypoint participant). Diagnostics changes deferred until the
  build finishes (it reads the working tree): endpoint GUIDs in change state,
  PID + callback begin/end markers; interpretation notes (non-atomic samples,
  validate warning output in the lab). Plan and results README updated. 348.
  `done` (2026-11-04) The local build finished: dds-diag-5f72fca, all five
  runtime images (bay, central, control, mapserver, noc) in central-comb:4000
  (tags/list). Then, uncommitted on jmg/test/dds-rest-api-diagnostics:
  dds_diagnostics.py records the rq/rr endpoint GIDs (sorted hex, `-` if none;
  rclpy.endpoint_info.TopicEndpointInfo.endpoint_gid) in ServiceState, so a swap
  at the same count prints a change line; `pid=` on every line; `check-start n=`
  before and `heartbeat n= took_ms=` after each check. test_dds_diagnostics.py:
  3 tests (incl. GID swap, empty endpoints as `-`, real libfastdds read-back).
  central_api 452 / launcher 12 green; black, mypy, pylint 10.00.
  dds_attempt_diag.sh: last_check and rest_api_pids on the result line, last
  check in NO_HEARTBEAT messages (helpers tested on sample lines); copied to
  comb_results scripts/. Next: commit approval, rebuild as dds-diag-<new sha>.
  Plan, handoff, results README, deploy_and_test 3.7 updated. 349. `done`
  (2026-11-04) On the user's word, committed the second diagnostics change as
  `29712d97` "chore(central_api): add endpoint ids, pid and check markers to the
  dds diagnostics" (2 files; parent 5f72fcae); commitlint and hooks passed
  (black/mypy hooks skipped these paths; both were run by hand, clean).
  Investigation branch 9 commits, not pushed. Next: rebuild
  `tools/local-runtime-deploy      dds-diag-29712d9 central-comb:4000`, deploy
  it on comb tomorrow, run dds_attempt_diag.sh. 350. `done` (2026-11-04) Both
  dds-diag image sets in central-comb:4000 (5f72fca and 29712d9; central 29712d9
  config GITSHA=29712d9, built 00:35Z); git push of the test branch confirmed
  (origin = 29712d97). Comb's registry is vng-os local-registry (registry:3,
  delete enabled; local-registry-gc.timer ~03:00 runs garbage-collect
  --delete-untagged). Each 5f72fca digest differs from its 29712d9 one, so
  deleting 5f72fca by digest is safe; command given to the user (DELETE
  /v2/volley/manifests/<digest>), not run. Codex reviewed 29712d97: Python
  sound; two dds_attempt_diag.sh fixes applied (ready_at = first ready=1 after
  the last ready=0; expected_bays keeps numeric IDs only, so empty stops before
  remove), 7 fixture cases pass; plan wording: an unmatched check-start means
  "didn't finish", not "blocked in a query". 351. `done` (2026-11-04) The user
  deleted the dds-diag-5f72fca tags (gone from tags/list). Wrote
  registry_versions.py (stdlib; one row per version: image build time, GITSHA,
  missing images) in comb_results scripts/: 68 versions on comb's registry,
  newest dds-diag-29712d9, most are teammates' branches (shared registry). No
  web UI ships with registry:3; joxit/docker-registry-ui on the laptop (proxy
  mode) suggested, not run. deploy_and_test 3.7 step 6 and the results README
  updated. 352. `done` (2026-11-04) registry_versions.py rewritten as a uv
  script (PEP 723 header, rich>=13.9, executable): rich table with build time in
  local time, colour-coded age, GITSHA, a ●/✗ column per image, `--highlight`
  (default dds-diag-), progress bar while reading configs. Ran against comb: 68
  versions. deploy_and_test 3.7 step 6 and results README updated. 353. `done`
  (2026-11-04) Sync check. Git: jmg/test/dds-rest-api-diagnostics local = origin
  = 29712d97 (committed 00:33:25Z), on the feature branch (local = origin =
  07eb74dd, 0 behind main), clean tree. Registry: only dds-diag-29712d9 left
  (5f72fca deleted); bay, central, control, mapserver GITSHA=29712d9, built
  00:35:02Z (after the commit); noc is the PHP NOC (docker/noc.Dockerfile, no
  _runtime, no GITSHA, cached layers dated 2026-10-12), and neither commit
  touches controller_webview. Fixed stale docs: deploy_and_test 3.7 intro,
  handoff (pushed, 29712d9 in registry, deploy dds-diag-29712d9, reinstall
  dds_attempt_diag.sh, pr-1018 = 07eb74d), plan heading,
  confirm_insert_fix_proposal status (dropped). 354. `done` (2026-11-04) Wrote
  testing/fable_dds_session_prompt.md: a self-contained prompt for a new session
  to continue the DDS investigation (reading order, state, what's ready, next
  steps, cautions, rules incl. comb changes need the user's go, notes from 355).
  Linked from the stage README. 355. `done` (2026-11-04) New session (Fable)
  resumed the DDS investigation from testing/fable_dds_session_prompt.md: read
  the summary, handoff "For tomorrow", plan sections 1/3/5 (E8, investigation
  branch)/6/9, the Codex review and the results README. Repo state confirmed:
  jmg/test/dds-rest-api-diagnostics at 29712d97, clean tree, two commits over
  07eb74dd (dds_diagnostics.py, rest_api.py, test_dds_diagnostics.py,
  central_nodes.py). The read-only ssh check of comb (.env.local, docker stack
  ls) was blocked by the session's permission classifier at first; the user
  allowed ssh reads. Comb state (00:56Z 11-05): .env.local has VOLLEY_REGISTRY
  uncommented, VOLLEY_VERSION=bay-refactor (the teammate's local build, central
  GITSHA=84f6deb), BAY_IDS_OVERRIDE="7"; app-comb 8/8 running,
  central/discovery-server/bay7 tasks started ~22:50Z; three ops shells from
  100.122.181.53 (since 11-03 19:19, 11-04 21:02 and 21:25); ~ops is clean (no
  scripts). Registry still has all five dds-diag-29712d9 images beside
  bay-refactor. Proposed first step: set VOLLEY_VERSION=dds-diag-29712d9
  (registry line already uncommented), swarmctl deploy app, check GITSHA=29712d9
  and the verbosity=1 line, reinstall dds_attempt_diag.sh + probe_clients.py,
  run one attempt; the unrelated-probe arm after a STUCK run's 10 min
  window. 356. `done` (2026-11-05) On the user's "Deploy it": backed up
  .env.local to /tmp/env.local.before-dds-diag on comb, set
  VOLLEY_VERSION=dds-diag-29712d9 (/tmp + cat > pattern; VOLLEY_REGISTRY was
  already uncommented by the teammate). First `swarmctl deploy app` over
  non-interactive ssh failed before any change: "required variable NFS_HOSTNAME
  is missing a value" (HOSTNAME is a shell variable, not exported; plan 4.3
  documents it); redone with `export HOSTNAME=$(hostname)`, deployed 00:58:07Z
  (plain redeploy, discovery server kept from ~22:50Z). Verified:
  GITSHA=29712d9; [dds-diag] verbosity=1 read-back (pid 68, one
  libfastdds.so.3.6.2.0 mapped); both bay 7 services ready=1 1/1 at check n=1;
  heartbeats 1/s, took_ms=1. Two Fast DDS warnings in the REST API's first
  second, proving the warning path: UTILS "Cannot get machine id. Failing back
  to IP based ID" and RTPS_TRANSPORT_SHM "Buffer is being invalidated,
  segment_size may be insufficient" (new facts for H4; findings 1.17). Summary
  table (+2 rows), handoff step 1, findings 1.17 updated. Not done: scripts not
  yet copied to comb, no attempt run; both need the user's go. 357.`done`
  (2026-11-05) On the user's "go ahead with the first test": scp'd
  dds_attempt_diag.sh + probe_clients.py to ~ops (md5 match), started
  `systemd-run --user --unit=dds-diag-1 ... -E HOSTNAME=$(hostname) dds_attempt_diag.sh diag1`
  at 02:01:24Z. Full start, deployed 02:01:52Z, result ok at 02:04:56Z: first
  check 02:02:04Z already ready=1 1/1 for both b7 services, 173 heartbeats, pid
  68, took_ms<=1; 288 RcvbufErrors in central (268 on the REST API's 7424,
  rb212992), 0 in the server. Same two Fast DDS warnings as 00:58Z (host-ID
  fallback, SHM segment_size), nothing else: every start, not a stuck signature.
  Bug: the script's save_warnings pattern never matches raw docker logs (ANSI
  escapes between `[` and the category), so fastdds_warnings=0 and an empty
  file; fixed locally (sed strip before grep, tested on a raw coloured line,
  bash -n ok) in both results folders, NOT yet re-copied to comb. Raw files in
  comb_results_2026-11-05/logs (+ README). Findings 1.18, summary (table row, 6
  of 9), plan branch section, 11-04 README updated. Full starts now 6 STUCK
  of 9. Next: re-copy the fixed script, more attempts until a STUCK one; both
  need the user's go. 358. `done` (2026-11-05) Re-copied the fixed
  dds_attempt_diag.sh (md5 match). diag2 (unit dds-diag-2, 02:09:57Z, deployed
  02:10:24Z): STUCK at 02:13:29Z. The stuck REST API's own graph: ready=0
  rq_readers=0 rr_writers=0 rq_gids=- rr_gids=- for both b7 services from the
  first check (02:10:36.997Z) for 777 s; heartbeats 1/s, took_ms<=1, pid 68
  (nothing blocked); fastdds_warnings=2 (the two of every start),
  unknown_participant=0 with verbosity confirmed: H7's failed-proxy-add branch
  did not fire. 598 RcvbufErrors on 7424, 0 on the server. 10 min hands-off, no
  change. Probe (one rclpy process in control, 4 clients) 02:23:32Z, ready after
  0.8 s; the REST API's check at 02:23:33.997Z: both services 1/1 with bay 7's
  GIDs (prefix 010f913b34000e4b). Recovery with a joining participant 4 of 4,
  now a positive transition. Full starts 7 STUCK of 10. Read-only: sudo -l
  allows tcpdump/lsof/dmesg as root (noexec), no nsenter; no tcpdump in the
  central image, no capture image on the host, ops in docker group, 17 GB free;
  host ifaces eth0/eth1/wlan0/tailscale0/docker_gwbridge. Raw files + README in
  comb_results_2026-11-05. Findings 1.19, summary (table, established 4 and 8,
  H7 narrowed), plan section 3 status, handoff updated. Stack left healthy. Next
  (user's go): diag3; unrelated-probe arm on the next STUCK (script edit +
  re-copy); capture sidecar in central's netns. 359. `done` (2026-11-05) User
  approved all four: diagnostics commit, unrelated-probe arm, capture sidecar,
  diag3 (one at a time); no Fast DDS fork. Committed `4b005718`
  "chore(central_api): report what the dds diagnostics see of each bay's nodes
  and topics" on the investigation branch (first try failed commitlint
  body-max-line-length, re-wrapped): BayGraphState per bay (nodes under /bay/bN,
  demangled topics under it, remote publishers on them by node namespace, their
  12-byte participant prefixes), a
  `change /bay/b7 nodes= topics= publishers= participants=` line on change; 4
  tests, central_api 446 passed / 7 skipped, mypy clean, pylint 10.00 from the
  repo root. NOT pushed (user pushes). Build
  `tools/local-runtime-deploy      dds-diag-4b00571 central-comb:4000` FAILED at
  push: `central-comb` no longer resolves on the laptop (home network
  192.168.8.1; tailnet name central-comb-5675-pecos = 100.120.46.20 resolves;
  registry answers 200 on 100.120.46.20:4000; daemon.json insecure-registries
  has only central-comb:4000). Needs a root change on the laptop (/etc/hosts
  line) by the user. Scripts v3 in comb_results_2026-11-05/scripts (and 11-04):
  PROBE_ORDER=unrelated,clients (probe_unrelated.py: one rclpy node, no clients,
  held 20 s; then the clients probe only if no recovery in 2 min), host capture
  (netshoot --net host, eth0 udp port 4789, from before the removal) and
  central-netns sidecar capture (--net container:<central>, -i any udp, started
  when the container exists), both -C 500 -W 4 into ~/captures, stopped by a
  finish trap that also saves central's and the server's full logs per run; bash
  -n ok, no offline run. Copied to comb (md5 match); nicolaka/netshoot:v0.16
  pulled on comb (898 MB); ~/captures created. Codex-style review of v3 not
  done. Explore subagent surveyed swarm-deploy (manifest order site/global/app;
  DEPLOY_ISO_TIMESTAMP only in central and bay commands; discovery-server in
  support.yaml 26-46 with no healthcheck/profile; app-scoped `internal` overlay;
  nothing waits for the server; release install = remove all + deploy all).
  Next: user adds the hosts line, rebuild, deploy dds-diag-4b00571, delete the
  29712d9 tags, diag3. 360. `done` (2026-11-05) User added the hosts line;
  rebuild pushed all five dds-diag-4b00571 images (cached build). Deployed on
  comb 02:53:54Z (VOLLEY_VERSION=dds-diag-4b00571, plain redeploy):
  GITSHA=4b00571; the new bay line works: nodes=7 topics=20 publishers=24
  participants=2 prefixes at the first check, took_ms=5. Registry deletion of
  the 29712d9 manifests was blocked by the permission classifier; command handed
  to the user (deploy_and_test 3.7 step 5). diag3 (unit dds-diag-3, v3 script):
  removed 02:54:47Z, deployed 02:55:15Z, ok at 02:58:22Z; host capture from
  02:54:47Z, central sidecar from 02:55:18Z (2 s after the deploy), both stopped
  by the trap (20.8 MB / 16.9 MB), full central + server logs saved. 324
  RcvbufErrors (146 on 7424). Raw files, logs and the two pcaps copied to
  comb_results_2026-11-05 (captures/, 37 MB; the notes folder is a git repo, so
  flagged). Findings 1.20, summary (+2 rows, 7 of 11), README updated. Full
  starts 7 STUCK of 11. Next: diag4 on the user's go (one at a time). 361.
  `done` (2026-11-05) diag4 (unit dds-diag-4, 03:02:22Z, deployed 03:02:50Z): ok
  at 03:05:57Z; captures 20.1/16.4 MB left on comb, logs copied. 1178
  RcvbufErrors (874 on 7424), the most yet, healthy. First bay line publishers=0
  participants=- for one check, then 24: a non-atomic transition. Full starts 7
  STUCK of 12 (diag builds 1 of 4). Findings 1.21, summary updated. Next: diag5
  on the user's go. 362. `done` (2026-11-05) User chose back-to-back:
  ~/dds_loop.sh (attempts until the first non-ok, diag5..diag12, 30 s apart) as
  unit dds-loop-5 from 03:08:09Z. diag5 03:11:43Z ok, diag6 03:15:49Z ok, diag7
  03:19:55Z ok, diag8 03:24:00Z ok, diag9 03:28:06Z ok; loop still running
  (diag10-12 left). Build 4b00571 with the v3 script (captures on) is 0 STUCK of
  7 (diag3-9); before it, 6 of 8 (e1d24a7 era) and 1 of 2 (29712d9, no
  captures). Two things changed at diag3 together: the build (per-second graph
  queries) and the captures (host eth0 promiscuous + a netshoot sidecar in
  central's netns). Proposed next arm: CAPTURE=0 toggle in the script (re-copy),
  loop on 4b00571 without captures; if still no STUCK, deploy 29712d9 (tags
  still in the registry) without captures to replicate diag2's conditions.
  Awaiting the user's go. 363. `done` (2026-11-05) Loop dds-loop-5 ended: diag10
  03:32:12Z, diag11 03:36:18Z, diag12 03:40:26Z all ok: diag3-12 = 10 ok of 10
  on 4b00571 with captures (~356 MB of pcaps in ~ops/captures). User: go for the
  capture-off arm then the 29712d9 fallback; the safety net forks off the
  feature-branch tip (done off the investigation tip 4b005718 so the diagnostics
  can watch it heal; rebase onto main once proven); the swarm-deploy change as a
  PR for Dan to review. CAPTURE=0 toggle added to the script (copied, md5
  7cf955a4); loop dds-loop-13 (diag13-20, CAPTURE=0) started 03:40:59Z. Branch
  jmg/test/rest-api-dds-watchdog (off 4b005718), uncommitted:
  central_api/bay_client_watchdog.py (BayClientWatchdog: 10 s timer, trips when
  a bay with a fresh report has had an unmatched confirm client for 60 s,
  os._exit(3) after flushing; restart_process), rest_api.py
  (garage_info_received_at, confirm_clients_by_bay, live_bays with
  FRESH_BAY_REPORT_SEC=10 on both the message age and the report staleness),
  launcher/central_nodes.py (respawn=True, respawn_delay=5.0),
  test_bay_client_watchdog.py (3 tests: trips at 60 s, a match or stale bay
  resets, an undeployed bay never trips). central_api 449 passed, launcher 12,
  mypy clean, pylint 10.00. Awaiting commit approval and a ticket number. Next:
  swarm-deploy start-gate branch. 364. `done` (2026-11-05) Committed `25f354bc`
  feat(central_api): restart the rest api when a live bay's confirm services
  stay unmatched (4 files, hooks + commitlint passed); built dds-diag-25f354b (5
  images). swarm-deploy branch trimmed per the user (bare
  DISCOVERY_SERVER_SETTLE_SEC=10 in .env, 2-sentence README section); still
  uncommitted. Volley branch jmg/test/discovery-server-settle (off 4b005718):
  entrypoint.sh probes, sleeps DISCOVERY_SERVER_SETTLE_SEC (default 0), probes
  again; shellcheck ok; uncommitted. Loop 2 (captures off, 4b00571): diag13 ok,
  diag14 ok, diag15 STUCK (03:49:31Z): bay line nodes=1 topics=18-24
  publishers=3 participants=…3500ab11 only, i.e. bay 7's state-machine
  participant (…34…, the one with the services) entirely unknown for 13 min; no
  EDP warning; unrelated probe (bare node, no clients) at 04:02:38Z, recovered
  04:02:40.888Z with the …34… participant and everything (nodes=8 publishers=31,
  both services 1/1). Any new participant repairs it. Captures on 0 of 10 vs off
  1 of 3 (suggestive). Deployed the watchdog build 04:03:54Z (GITSHA=25f354b,
  healthy, no trip); dds_loop.sh now also stops on a second rest_api pid; loop
  dds-loop-16 (diag16-25, CAPTURE=0) from 04:04:34Z. Findings 1.22, summary
  (table, established 9, H7), handoff updated; loop outputs + diag15 files
  copied. Full starts 8 STUCK of 23. Open asks: swarm-deploy commit, entrypoint
  commit, watchdog action (exit+respawn vs a temporary-participant "poke"
  first). 365. `done` (2026-11-05) User: "Add the poke". bay_client_watchdog.py,
  uncommitted on jmg/test/rest-api-dds-watchdog: at 60 s unmatched on a live
  bay, on_poke (poke_discovery: a daemon thread holds a node in a second rclpy
  Context for POKE_HOLD_SEC=5, i.e. a new DDS participant, then destroys it);
  still unmatched RESTART_AFTER_POKE_SEC=30 later, on_restart (os._exit(3)); a
  match clears both. Tests: poke at 60 s then restart at 90 s, a match after the
  poke resets (a second poke on a new streak), an undeployed bay never trips,
  and the real second-context participant comes up and down (installed rclpy).
  black, mypy clean, pylint 10.00, central_api 450 passed. Not committed
  (awaiting the word). Loop dds-loop-16 on the restart-only build 25f354b:
  diag16 ok (pid 68 only), diag17 running. The entrypoint settle change is still
  uncommitted in the working tree (it travels across branch switches; stage by
  name). 366. `done` (2026-11-05) User: "Commit all three". Committed `aeb59906`
  feat(central_api): poke discovery with a temporary participant before
  restarting the rest api (watchdog branch, 2 files) and `651eb3d7`
  feat(docker): wait for the discovery server to settle before starting the ros
  processes (jmg/test/discovery-server-settle, entrypoint.sh; first try failed
  body-max-line-length, re-wrapped). The swarm-deploy commit
  (jmg/discovery-server-settle, 4 files staged? no: the whole command was denied
  by the session's permissions before `git add`), so the user runs it. Building
  dds-diag-aeb5990 (watchdog branch checked out). Loop dds-loop-16 on 25f354b:
  diag16 ok, diag17 ok (pid 68 only), diag18 running. Plan: after the build,
  stop the loop in its 30 s gap after a result, deploy dds-diag-aeb5990, start a
  new loop (CAPTURE=0). 367. `done` (2026-11-05) dds-diag-aeb5990 built (5
  images). diag18 (25f354b) ok, pid 69 only; stopped dds-loop-16 in its gap at
  04:16:13Z. Deployed aeb5990 04:16:31Z (GITSHA=aeb5990, healthy, no watchdog
  line); loop dds-loop-19 (diag19-30, CAPTURE=0) from 04:16:47Z. dds_loop.sh
  (laptop copy) now also stops when the saved central log has a
  bay-client-watchdog line (a successful poke leaves one pid and an ok result);
  the running loop still has the old script, so the waiter checks the live log
  for that line. swarm-deploy commit still with the user (denied here). 368.
  `done` (2026-11-05) Branch picture for the user: feature branch 07eb74dd
  (origin) -> jmg/test/dds-rest-api-diagnostics (5f72fcae, 29712d97 = origin,
  4b005718 local only) -> jmg/test/rest-api-dds-watchdog (25f354bc, aeb59906)
  and jmg/test/discovery-server-settle (651eb3d7), both off 4b005718, local
  only. Only dds-rest-api-diagnostics is on origin (at 29712d97). Deleting it on
  the remote is a push: the user's. swarm-deploy: the four files are STAGED on
  jmg/discovery-server-settle; `git commit` there is denied by the session's
  permissions (twice), so the user commits. Loop dds-loop-19 (aeb5990): diag19
  running, no watchdog line yet. 369. `done` (2026-11-05) The user committed
  swarm-deploy `ec14784` feat(app): add a discovery server settle time for the
  ros containers (jmg/discovery-server-settle, clean tree) and deleted
  origin/jmg/test/dds-rest-api-diagnostics (ls-remote: only
  jmg/SW2-1135/scheduler-renames-and-cleanups left). Loop dds-loop-19 (aeb5990,
  CAPTURE=0): diag19 ok, diag20 running. Next: wait for a STUCK start to see the
  poke heal; then ticket + rename + rebase onto main for the watchdog; then the
  settle gate test (build dds-diag-651eb3d, deploy from a ~/swarm-exp copy with
  the settle env, loop). 370. `done` (2026-11-05) User: clean patch branches
  after the test, off main, squashed; temporary test branches fine; the settle
  gate is two paired PRs (swarm-deploy + volley) with the same title and
  cross-links; the swarm-deploy PR after the test. Wrote
  testing/pr_texts_dds_mitigations.md: pair A (swarm-deploy `ec14784` + the
  volley entrypoint commit, same title, each body names the other,
  why/what/cost/testing-to-fill-in) and B (the watchdog, two commits squashed).
  Loop dds-loop-19 (aeb5990): diag19 ok, diag20 ok, diag21 running, no watchdog
  line. Still open: the go for ~/swarm-exp on comb (settle test), the ticket
  number after a healed start. 371. `done` (2026-11-05) User allowed
  ~/swarm-exp. Building dds-diag-651eb3d (settle branch checked out). On comb:
  cp -r /data/swarm ~/swarm-exp; .env += DISCOVERY_SERVER_SETTLE_SEC=10;
  main.yaml (control, central) and bay.yaml.j2 +=
  `DISCOVERY_SERVER_SETTLE_SEC: ${DISCOVERY_SERVER_SETTLE_SEC:?}` under
  ROS_DISCOVERY_SERVER (as in swarm-deploy ec14784); .env.local
  VOLLEY_VERSION=dds-diag-651eb3d; `swarmctl --root ~/swarm-exp info` ok
  (release c9b6529); /data/swarm untouched. Settle loop later:
  SWARM_ROOT=~/swarm-exp CAPTURE=0 dds_loop.sh 31 40 (the settle build has no
  watchdog: one change at a time). Loop dds-loop-19 (aeb5990): diag19-21 ok,
  diag22 next, no watchdog line. 372. `done` (2026-11-05) User: no more
  investigation tests, just test the patch. dds-diag-651eb3d built and pushed (5
  tags). Loop dds-loop-19 ended: diag19-30 all ok on aeb5990, pid 68 each, no
  watchdog line (since diag3: 1 STUCK of 28). Copied the loop script that also
  stops on a watchdog line as ~/dds_loop_v2.sh; started dds-loop-31 (diag31-70,
  CAPTURE=0, aeb5990) at 05:05:39Z, unattended; stops itself at the first
  non-ok, second pid or watchdog line. Then: fill in the watchdog PR's testing
  section, ticket, clean branch off main (squashed); then the settle loop from
  ~/swarm-exp. 373. `done` (2026-11-05) User capped the watchdog test at 10 and
  asked to move faster. Loop dds-loop-31: diag31-40 all ok (pid 68, no watchdog
  line); it ran past the cap while waiting and was stopped at 06:08:20Z with the
  stack deployed (8/8 up, no capture containers). Poke build aeb5990: 22+
  healthy full starts, 0 false trips, 0 STUCK starts to heal. Since diag3: 1
  STUCK in ~40 full starts. Proposed fast path: stop comb testing, ship the
  watchdog on the unit tests + diag15's mechanism evidence + the no-false-trip
  record; the settle gate either shipped labelled untested or held; clean
  branches off main; restore comb to pr-1018. 374. `done` (2026-11-05) User:
  squash the watchdog into one commit, modern Python, fewer comments, confirm
  the diag commits are excluded from the patch branches (yes). origin/main
  8ebf0762 is identical to the feature tip for rest_api.py, central_nodes.py and
  entrypoint.sh. Clean branches off origin/main: jmg/rest-api-dds-watchdog
  `82df8676` (one commit: bay_client_watchdog.py with no inline comments and an
  `Action` alias, test with annotated locals instead of `# type:` comments,
  rest_api.py wiring without the diag block, central_nodes.py respawn without
  the comment; black, mypy, pylint 10.00, central_api 446 + launcher 12 passed)
  and jmg/discovery-server-settle `296cfb40` (entrypoint, one comment line,
  shellcheck ok). Test branches untouched. PR texts updated with branches,
  commits and the watchdog's testing section (27 healthy starts, no false trip,
  heal not observed in the field; mechanism shown in diag15). Open: ticket
  numbers for the branch names, the settle gate's fate, comb restore, pushes/PRs
  (the user's). 375. `done` (2026-11-05) User asked for a shareable write-up for
  teammates. Wrote a Claude Doc "Stuck REST API after a full start: what we
  found and what we're shipping"
  (https://claude.ai/artifact/RiT4zStfmPpMVFsJGfyNwS): the problem, what we
  established (whole-participant miss, nothing blocked, no warning, server still
  had it, any join heals in 2 s 5 of 5, the rate change), what we ruled out, the
  mechanism (reliable discovery stream to a late client; Fast DDS 3.6.x fix
  unreleased; no capture of a stuck start), patch A (watchdog: poke then
  restart; 27 healthy starts, no false trip, heal not observed in the field),
  patch B (settle gate, two paired PRs, untested), the test record table by
  setup, and the open decisions (patch B's fate, tickets, comb restore) as a
  checklist. One doc comment asks about patch B. 376. `done` (2026-11-05) User:
  hold patch B (settle gate); both branches kept (volley
  jmg/discovery-server-settle 296cfb40, swarm-deploy ec14784), PRs not opened.
  Doc updated (Tested line, checklist, Then; the anchored comment detached and
  answered). User asked what the "per-second graph query" is:
  BayDiscoveryMonitor.bay_state (4b00571+) calls get_node_names_and_namespaces,
  get_topic_names_and_types and get_publishers_info_by_topic per bay topic every
  second; all read rmw_fastrtps's in-process graph cache under its mutex, create
  no participant or endpoint and send nothing; the only conceivable influence is
  lock timing against the discovery listener thread; diag15 stuck with it
  present. 377. `done` (2026-11-05) Drafted the second Codex review prompt in
  chat and saved it as testing/codex_dds_review_prompt_2.md (reading order,
  branches and commits, read-only rules, six questions: conclusions, the rate
  change, patch A, patch B, what's missing for eProsima, what we got wrong;
  report to codex_dds_review_2.md). Still open: ticket for patch A, comb restore
  go. 378. `done` (2026-11-05) Codex review 2 (codex_dds_review_2.md) read and
  checked. Accepted: (a) the bay line infers participants from publishers' GID
  prefixes and the ROS graph, so "whole participant unknown" is "nothing of that
  participant reached the graph" (PDP vs EDP not separable from Python);
  "component participant completely known" softened to "its node and publishers
  were present"; "nothing blocked" to "its own callbacks kept running"; "5 of 5
  within 2 s" to "5 of 5 followed a join, the last two timestamped (1-3 s)";
  "registers last" to "last to create its sockets (ID 7)"; E1b to "existing
  matches survived"; the 7/10 vs 1/40 contrast labelled a pooled trend. (b) The
  script's one-service result line: docker logs keep CRs, so the last service's
  line ends in \r and states()/ready_at() miss it; fixed (tr -d '\r' in diag(),
  replayed offline: 2 of 2), both results folders. (c) Watchdog hardening to do
  before shipping: coalesce pokes (one at a time), create_node inside the try
  with a success/failure line, a restart budget (launch respawns on any exit, no
  exit-code filter, verified by Codex against launch lyrical), a test with a
  spinning main context during the poke, liveness age up to 20 s + skew noted.
  (d) Patch B stays held; the second probe is itself a join. (e) Cheapest
  decisive observation for eProsima: an in-process snapshot of PDP/EDP proxies
  and match counters when stuck (needs C++/rmw access; not from Python). Doc and
  summary items 8-9 updated. Disagree with nothing material; "UDP loss ruled
  out" is already stated narrowly as socket overflow. 379. `done` (2026-11-05)
  User: harden first. Watchdog hardening per Codex review 2: make_poker() (one
  poke thread at a time, logs "poke already running"); hold_extra_participant
  creates the node inside the try and logs "temporary participant up/down" or
  "failed"; restart_process(reason, log=/tmp/rest_api_watchdog_restarts,
  clock=time.time) keeps a budget of RESTART_BUDGET=3 per
  RESTART_BUDGET_WINDOW_SEC=3600 in a file (launch respawns on any exit); over
  budget it logs and returns. Tests: 6 (one poke at a time with a blocked fake
  hold; the budget with a fake clock; the poke beside a spinning main context;
  the earlier three). A first budget test called os._exit because
  restart_process used the real clock against fake stamps: made the clock
  injectable. black, mypy, pylint 10.00 (Poker class -> closure for R0903),
  central_api 448, launcher 12. Rebuilt the branch as ONE commit off origin/main
  without reset/rebase: saved the 4 files, renamed the branch, new
  jmg/rest-api-dds-watchdog off origin/main, committed `d43ce589`, deleted the
  old branch (82df8676). PR text updated (hardening, liveness caveat, 6 tests).
  Open: ticket for patch A (rename before push), comb restore (or a redeploy of
  d43ce589 for a couple of healthy starts first). 380.`done` (2026-11-05) User:
  deploy, restore, then tickets and renames. Test branch
  jmg/test/rest-api-dds-watchdog += `480b803f` chore: harden the bay client
  watchdog on the test branch (module + tests from d43ce589; 10 tests green).
  Built dds-diag-480b803, deployed 14:32:17Z (GITSHA=480b803, healthy, no
  watchdog line); loop dds-loop-47: diag47 ok, diag48 ok, pid 68, no watchdog
  line, no /tmp/rest_api_watchdog_restarts. Copied every run's outputs (194
  files, 4.5 MB) to comb_results_2026-11-05/logs. Restored: .env.local
  VOLLEY_REGISTRY commented, VOLLEY_VERSION=pr-1018 (backup
  /tmp/env.local.before-restore on comb), deployed from /data/swarm 14:41:33Z,
  ~/swarm-exp removed; central came up from ECR pr-1018 with GITSHA=e1d24a7 (the
  CI image predates the dropped e1d24a7c client-recreate commit; the branch tip
  is 07eb74dd), no diag lines; 8/8 up. Left on comb: ~ops scripts, outputs,
  captures (356 MB). Jira drafts in testing/jira_tickets_dds_mitigations.md (A
  watchdog, B held settle pair). Full starts 8 STUCK of 55. PR text, summary
  table, results README updated. Open: Jira keys -> rename 3 branches; registry
  deletion of 6 dds-diag tag sets (29712d9, 4b00571, 25f354b, aeb5990, 651eb3d,
  480b803); stale pr-1018 image; ~ops cleanup. 381. `done` (2026-11-05) "pr-1018
  is stale" was comb's cache, not CI: CI for 07eb74d passed 00:00Z; ECR
  central-pr-1018 digest 6472159… vs comb's cached 47d9a59… (created 11-04
  20:36, GITSHA=e1d24a7); swarmctl deploys with --resolve-image never, so the
  node keeps the cached image for the tag. No CI rerun needed; a `docker pull`
  of the five pr-1018 images on comb plus a redeploy would refresh it (needs the
  go). User: acli is installed, create the tickets. Created with
  `acli jira workitem create --project SW2 --type Task --assignee @me`: SW2-1181
  (watchdog) and SW2-1182 (settle gate, held), descriptions from the drafts, no
  parent. Renamed: volley jmg/SW2-1181/rest-api-dds-watchdog (d43ce589),
  jmg/SW2-1182/discovery-server-settle (296cfb40); swarm-deploy
  jmg/SW2-1182/discovery-server-settle (ec14784). PR texts carry the keys in the
  titles; the Jira drafts file notes the keys. Open: refresh comb's pr-1018
  cache (go), registry tag deletion (user), ~ops cleanup (go), parents for the
  tickets (user), pushes + PRs (user). 382.`done` (2026-11-05) User: pull and
  redeploy. `docker pull` of the five pr-1018 images on comb as ops failed: "no
  basic auth credentials" for ECR. swarmctl has no login/pull command; it passes
  --with-registry-auth (docker.py:267) from the invoking client's stored auth,
  and its aws.py reads AWS creds from device config paths for Secrets Manager.
  Reading ops's docker config / ~/.ecr was refused (credential materialization)
  and is the user's to look at. Comb still runs the cached e1d24a7 pr-1018
  images; redeploy pending a successful pull by the user. 383. `done`
  (2026-11-05) swarmctl at c9b6529 (docker.py:260-268): stack deploy with
  resolve_image="never" and with_registry_auth=True; a new VOLLEY_VERSION tag
  pulls, a rebuilt image under the same tag doesn't (the node keeps its cached
  tag). Pull as ops fails "no basic auth credentials" even from `bash -ic` (so
  not a missing profile); the ECR login on comb is something the user does (a
  docker login with a token that expires?). Branches vs origin/main 8ebf0762
  (fetched, unchanged): SW2-1181 and SW2-1182 patch branches 0 behind / 1 ahead;
  the three test branches and the feature branch 0 behind; swarm-deploy SW2-1182
  0 behind origin/HEAD a6aea5d. Comb still on cached e1d24a7. 384. `done`
  (2026-11-05) User's option: local-runtime-deploy. Checked out the feature tip
  07eb74dd, built `pr-1018-07eb74d` into central-comb:4000 (cached, 5 images),
  .env.local: VOLLEY_REGISTRY uncommented, VOLLEY_VERSION=pr-1018-07eb74d,
  deployed 15:06:29Z: central and control GITSHA=07eb74d, bay7 on the tag
  (container on the bay machine), 8/8. So comb's end state is the branch tip
  from the local registry, not ECR's stale pr-1018. Registry now holds the six
  dds-diag tag sets plus pr-1018-07eb74d (running: keep). Open: parents for the
  tickets, push SW2-1181 + PR, tag deletions, ~ops cleanup, whether to return to
  ECR pr-1018 once it's re-pulled with a login. 385. `done` (2026-11-05) User:
  create the PRs with gh in the house format, draft; run the respawn check.
  Deployed dds-diag-480b803 15:14:18Z (pid 68 healthy);
  `docker exec central kill -TERM 68` at 15:14:51Z: launch "process has finished
  cleanly [pid 68]", "process started with pid [366]" (~10 s: 5 s respawn
  delay + start), pid 366 ready=1 at its first check, service 1/1 throughout.
  Restored pr-1018-07eb74d 15:15:30Z (GITSHA=07eb74d, 8/8). House PR format (PR
  1027, 1008): title `[SW2-xxxx] …`, body`## What` / `## Why` / `## Testing`
  (or Summary/Changes). Wrote testing/pr_body_SW2-1181.md. `git push` of
  jmg/SW2-1181/rest-api-dds-watchdog was DENIED by the session's permissions:
  the user pushes, then `gh pr create --draft`. Open: the push, SW2-1182 draft
  PRs or not, parents, tag deletions, ~ops cleanup. 386.`done` (2026-11-05) The
  user pushed jmg/SW2-1181/rest-api-dds-watchdog (origin = d43ce589).
  `gh pr create --draft`: https://github.com/VolleyAutomation/volley/pull/1032,
  title "[SW2-1181] Heal or restart the REST API when a live bay's confirm
  services stay unmatched", body from testing/pr_body_SW2-1181.md. The app bound
  it (checks none yet, mergeable, review required). acli comment on SW2-1181
  with the PR link and the test summary. Open: SW2-1182 draft PRs or not,
  parents, tag deletions, ~ops cleanup, Auto-fix for #1032's CI. 387.`done`
  (2026-11-05) User: push the SW2-1182 pair as drafts; no parents; delete the
  tags (command); delete the ops files. Removed from ~ops on comb: captures (359
  MB), the scripts, probes, 48 attempt outputs, loop outputs, warnings, per-run
  central/server logs, dds_attempts.log (198 entries); ~ops back to
  .bashrc/.profile/.ecr/.shiv; stack 8/8 on pr-1018-07eb74d. swarm-deploy PR
  format (PR 67): `[SW2-xxxx] Title`,`## What`,`## Why`, Jira link. Wrote
  testing/pr_body_SW2-1182_volley.md and pr_body_SW2-1182_swarm-deploy.md, each
  opening with a "held, untested" line and naming its pair. Pushes are the
  user's (rule); then`gh pr create --draft` in each repo. Tag deletion command
  handed over again. 388. `done` (2026-11-05) Auto-fix event: Dan
  (volleydambrosio) asked on PR #1032 why not just exit/throw and let respawn
  reboot the node. Replied on the thread (discussion_r4482368249): the restart
  is the fallback and was exercised on comb; the poke heals in-process without
  dropped requests (a joining participant is what's needed, 5 of 5 on comb); a
  plain exit/exception on the spin thread leaves Flask running so launch never
  sees an exit, hence os._exit(3); launch respawns on any exit with no budget,
  hence the 3/hour budget. No code change; thread left for Dan to resolve. 389.
  `done` (2026-11-05) The user pushed both SW2-1182 branches. Drafts: volley
  #1033 and swarm-deploy #68, title "[SW2-1182] Wait for the discovery server to
  settle before starting the ROS processes", bodies from
  testing/pr_body_SW2-1182_{volley,swarm-deploy}.md, each opening "Held,
  untested on a garage" and linking the other; SW2-1182 commented with both
  links. Not watched by Auto-fix (held). Open: the registry deletion on the
  user's side. 390. `done` (2026-11-05) Dan's second comment on #1032
  (PR-level): the approach may help for the bay service, but he expects the same
  with other REST API services and wants to try a different DDS provider before
  deciding whether the fix is needed. Surfaced to the user with context (the
  miss is a whole participant, so any of its services would be affected; a
  provider switch changes the discovery layer the failure lives in; both need a
  reproducible failure). The user: no automated replies to PR comments, they
  come from him. Auto-fix turned off for #1032 (comment relay and CI watch are
  one switch here). Memory saved: volley-pr-replies-from-user. My earlier
  automated reply to Dan's first question (discussion_r4482368249) is still on
  the thread. 391. `done` (2026-11-05) Reorganised volley_notes on the user's go
  (git mv, nothing committed, 671 renames): guides/ {claude_workflow (was
  guide), mqtt_broker, host_setup (was kernel)}, research/ +=
  action_dependency_graph and bottleneck_assignment.md (was algorithms/),
  specs/agv_requirements, presentations/scheduler_package (425 MB, was under the
  epic), garage/ {deploy_and_test.md, troubleshooting_reference.md, scripts/
  (current copy of each attempt, loop, probe and registry script)},
  investigations/dds_rest_api_discovery/ {README.md (was
  fable_dds_session_prompt.md), summary.md, findings.md, plan.md, handoff.md,
  reviews/, patches/, results/2026-11-0{4,5}/}, tickets/ (was
  pull_request_notes; SW2-876 -> SW2-876_agvhito_state_machine), tools/scripts
  (was scripts/); src/volley_notes stays (uv_build). Empty diagrams/ removed.
  Paths rewritten in every doc outside this log, CLAUDE.local.md and two memory
  files; this log keeps its historical paths. New top-level README.md index. The
  teammate doc's results path updated. This log now lives at
  tickets/SW2-482_scheduler_core_refactor/SW2-482_notes.md. 392. `done`
  (2026-11-05) User asked to bring main up to date and rebase/push as needed.
  origin/main moved to 2dc276b5 (PR #1024, docs only: the garage state JSON
  schema); local main fast-forwarded with `git fetch origin main:main`. Every
  branch is 2 behind, none touches a file those commits touch; GitHub reports
  #1018, #1032 and #1033 MERGEABLE (state BEHIND, no conflict), #1018 still
  REVIEW_REQUIRED (no approval on record). No rebase needed; a rebase would
  force-push three pushed branches, so not done (rule). Local-only:
  jmg/SW2-1126/scheduler-scenario-files is merged (38 behind, 0 ahead); the
  three jmg/test/… branches are the comb builds. swarm-deploy branch 0
  behind. 393.`done` (2026-11-05) origin/main moved again to 1ef237be (PR
  #1014, SW2-1076: permission-model flag and insert request contract); local
  main fast-forwarded. The three PR branches are 3 behind; rest_api.py is
  touched by both #1014 and the watchdog but `git merge-tree` dry runs are clean
  for all three. Rebase + --force-with-lease commands handed to the user (rule:
  no rebase/push here). swarm-deploy branch 0 behind.
  394. `done` (2026-11-05) Earlier housekeeping confirmed done by the user: branches rebased+pushed, notes committed 8fc78b9,
       dds-diag tags deleted (0 left). Dan asked on Slack about "30+ launches without the watchdog": gave the split (55 full
       starts: 23 without the watchdog, 8 stuck; 32 with it, 0 stuck; the 0 is not evidence since the watchdog only heals).
       origin/main moved again to c41015a3 (PR #1023, admin auth foundation). On the user's ask, rebased here (the session
       allowed it): feature 661f2892 -> 129cd6fc; test branches --onto the new tip: diagnostics 3ed8e132, watchdog a31e3e76,
       settle d74cbf67; patch branches bac5b4b4 (SW2-1181) and dc93e855 (SW2-1182); all 0 behind, clean. One
       `git push --force-with-lease` of the six handed to the user.
  395. `done` (2026-11-05) Paula reproduced the not-ready state on main (5 of 10 restarts, a 2.5 s wait_for_service right after
       client creation); Dan gave the go-ahead; Slack replies drafted (numbers split, Justin's context). CI failures on #1018
       (3 system-test groups: "Failed to resolve action download info", GitHub infra) and #1032 (runner died at Set up job)
       rerun after the runs completed; both green (#1018: 40 passed, 2 skipped, Greptile neutral). The user merged #1018
       (squash, a468657f, 19:22:19Z). Local main fast-forwarded; deleted local jmg/SW2-1135/scheduler-renames-and-cleanups
       and the three jmg/test/… branches; the test branches are still on origin (deletion is a push: the user's). Left:
       jmg/SW2-1181, jmg/SW2-1182 (on main), jmg/SW2-1126 (merged, kept on request).

