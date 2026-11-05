# PR preparation plan against the implicit review guidelines (2026-10-26)

Assessment of commit 1 (632701c6) against the team's implicit guidelines and Greptile's habits, as
summarised by the other agent's report. Checked against the code, not assumed. Status: all of A1 to A5 and B6 to B9
applied on 2026-10-26 (review log items 115 and 116).

## A. Recommended before opening the PR (likely to be raised)

1. **package.xml: drop `<test_depend>ament_index_cpp</test_depend>`.** It was there for the
   `layout_test` branch of the state loader, which is gone; no file in the package uses it now.
   Guideline 1.6 (every unused dep removed), dambrosio, 14 comments in 3 PRs.
2. **Shorten the test names of seven words or more** (dambrosio: "I try to keep these under 4-5
   words"; Claude-style long names were called out). Seven qualify, all but one in `test/utils/`
   (no scenario files to rename):
   - `RejectsAnAgvOnANodeTheLayoutDoesNotHave` (11) -> `RejectsAgvOnUnknownNode`
   - `TransitionsBothBaysToInsertForARatioOfOne` (10) -> `RatioOneInsertsBothBays`
   - `RejectsAPayloadThatDoesNotFitItsStall` (9) -> `RejectsOversizedPayload`
   - `SplitsTheBaysByReadinessRatioAndEmptyTrays` (9) -> `SplitsBaysByRatio`
   - `ClassifiesABayByStateTrayAndPayload` (8) -> `ClassifiesBay`
   - `CountsTraysWithoutPayloadOnEnabledNodes` (7) -> `CountsEmptyEnabledTrays`
   - `TransitionsOnlyWhatTheDesiredSplitRequires` (7) -> `TransitionsOnlyAsNeeded`
   Ten more have six words (`DoesNotMoveAgvsUnderTrays`, `BaseScheduleReservesAgvAndNodes`,
   `FailsWhenDisabledAgvBlocksPath`, `ChainsThreeMovesAcrossTwoAgvs`,
   `FailsWhenBayTransitionTrapsAgv`, `UsesAgvFreedByBayTransition`,
   `ResolvesManyBlockersThenAssignsAgvs`, `ClassifiesTheBaysOfAState`, `LeavesABayInFlightAlone`,
   `AgvCurrentPoseToTrayMove`); renaming a plan or stage test renames its scenario file and its
   `test:` key. Suggest leaving those, except the two padded with articles
   (`ClassifiesTheBaysOfAState` -> `ClassifiesBays`, `LeavesABayInFlightAlone` ->
   `LeavesBayInFlightAlone`).
3. **Split the viewer into its own commit in the same PR.** The guideline is one coherent change
   per commit, and the team regroups commits on request (jabel, PR991). The viewer is 15 files and
   2,910 lines (`tools/`, `pyproject.toml`, `uv.lock`) with no dependency from the tests on it, so
   it is a clean second commit, `feat(scheduler): add a viewer page for the test scenarios`.
   The tests, scenario files, CMake and `.clang-tidy` stay in the `test(scheduler)` commit; the
   commit message loses its last paragraph. One PR, two commits.
4. **PR description with the traceability list** (jlessner: every behaviour change and changed
   constant called out). Beyond the objective and scope: `AgvChargeJob.TwoAgvsDistinctChargers`
   now plans two jobs (the old test gave both the same GUID); the scenarios moved from
   576_eccles, 1355_fulton and the synthetic lots to the three sites, and what that changed
   (the retrieval-heading rule no longer exercised, the insert on 5675 lowered on the waypoint);
   the four new tests; the loaders compiled once (and the clang-tidy time that fixed);
   the `.clang-tidy` exception and why; the GUID numbering of requests and jobs; the dropped
   `ament_index_cpp` dependency; why the viewer is in this PR (the review aid for the recorded
   diffs, kept together with the files it reads). Use the Jira draft's observation list.
5. **Say what `test/scenarios/` is, in the README's first line and in the PR description.**
   Greptile checks YAML under a "scenarios" name against its "Scenario authoring" and "Simulation
   and scenarios" knowledge-base docs (all P1: event types the exerciser supports, capacity,
   drains, `*_events_*` companions). These files are gtest inputs and recordings, not simulation
   workloads; one sentence pre-empts the findings and is the one-line reply if they come anyway.

## B. Worth doing, reviewer taste

6. **Reuse `volley::to_string(const GuidMsg&)`** (`common_ros/print_utils.hpp`) in `GuidScalar`
   for the 8-4-4-4-12 form instead of the hand-rolled hex loop: build a `GuidMsg` from the bytes
   and call it. Guideline 1.2 (reuse shared helpers), the second most frequent theme.
7. **A shared `now` for the tests.** Fifteen tests pass `rclcpp::Time()` (default-constructed,
   `RCL_SYSTEM_TIME`) as the planning time. The scheduler never compares it with a ROS stamp, so
   nothing breaks, but guideline 1.8 (dambrosio's "Blocker" in PR987 was exactly this
   constructor) makes a question likely. One `inline const rclcpp::Time kNow {0, 0, RCL_ROS_TIME}`
   in a test header, used everywhere, removes the question and the fifteen repetitions.
8. **Viewer module size.** `scenarios.py` (875 lines) and `scene.py` (830) are the "god file"
   shape mzhong flags in Python (11 comments). A pure move would split `scenarios.py` into the
   loader/adapter and the table builders, and `scene.py` into the scene and the path drawing.
   No behaviour change; do it only if the viewer commit is expected to get a close Python review.
9. **`docs/deprecated/tech-debt.md` and `scheduler.md`** list "scheduler_jobs_tests.cpp:2244 fix
   assignment costs test"; that test passes and is recorded now, so the entries are stale. They
   live under `deprecated/`; a one-line removal is optional (guideline 1.3, stale docs).

## C. Checked and fine, with the reply ready if asked

- `.value()`/`.has_value()` scrub: no `->` or `*` on an optional remains in the tests (the
  remaining `->` are on a `unique_ptr`, on `ctx` and on event pointers); `std::get_if` returns a
  pointer and is checked.
- `[[nodiscard]]` on every value-returning function of the support headers.
- Includes: every `<...>` in the support sources is used; no aggregator headers.
- No `main()` in tests, no sleeps, timers or tick counts; `rclcpp::init` not needed (no ROS
  time or executors).
- Comments: no restating comments, no history, `///` throughout the headers.
- Stage tests build their DAG by hand rather than through `Plan` (guideline: drive production
  wiring). Reply: the stage tests isolate one stage on a DAG the test controls; the 45 plan
  scenarios drive the production wiring end to end, and commit 2's solver interface will let a
  stage be recorded inside `Plan`.
- `std::cout << "Recorded ..."` in the recorder: intentional feedback of a recording run, not
  debug logging.
- The viewer has no tests: engineering-only tool (the team's accepted answer, mzhong PR945).
  `argparse` with defaults from the package, no `sys.path` edits, f-strings, no hard-coded values.
- Scenario `description` fields are several sentences each: they are data the viewer shows, not
  comments; keep.
- Examples run the viewer with `uv run python ...`, not `ros2 run`: it is a dev-group tool
  (plotly, rich), not a ROS executable.

## Suggested order

A1, A2, A3 and A4 together in one round (rename, package.xml, split, message and description),
A5 in the same round; B6 and B7 are small and fit in the same round; B8 and B9 on request.
