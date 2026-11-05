# Dan's first review of PR #1018 (2026-11-03, commit a80d0ee3) and the plan

Read with `gh api repos/VolleyAutomation/volley/pulls/1018/reviews` (two reviews, 5755650662 and
5756021003) and `gh api "repos/VolleyAutomation/volley/pulls/1018/comments?per_page=100"` (13 inline
comments by `volleydambrosio`). Each claim was checked against the branch; Codex's plan (pasted by the
user) was compared item by item.

Dan's summary: the convention he suggests is `stdx::Expected<void, JobFailure>` for job expansion,
`stdx::Result` / `stdx::Expected<T>` for anything that fails with a reason, `std::optional` where "not
found" is normal. He offers a follow-up PR for these. That matches `PROMPT.md` section 6.5 and phase H.

## Plan

Fold each change into the commit that wrote the code, keeping six commits (review rules, section 7).
GitHub's force-push "compare" link shows Dan only what changed.

| # | Thread | Check | Plan | Commit |
|---|---|---|---|---|
| 1 | Advanced tests 05-07: why kept, rename? (4457348192) | 01-04 ran on the decommissioned `576_eccles` (one moved to `MoveJob.TwoTrayMovesWithAgvUnderOneTray` on `tiny_lot`). 05-07 run on layouts in service (`550_w21st`, `175_e82nd`) and guard three planning fixes. All three use suite `SchedulerJobs` and `…Test` names. | Now. Rename files, targets and suites to what each guards, house style (suite named after the file, short test names): `cross_floor_pathing_tests` / `CrossFloorPathing.RetrieveBehindThreeTrays`, `vrc_insertion_cycle_tests` / `VrcInsertionCycle.CrossFloorRetrieve`, `chokepoint_pathing_tests` / `ChokepointPathing.CleanGarage`. Assertions unchanged. | 6 |
| 2 | Move internal methods under `private:` (4457650634) | Confirmed: no caller outside `Scheduler` in `test/`, `scheduler_advanced_tests`, `central`, `agvhito_tools`. `StorePreferredPayloadHeadingsForRetrieval` is called from the constructor and `SchedulerRos` (a friend). | Now. Move the listed methods, grouped by pipeline stage like the `src/` split. Header only. | 5 |
| 3 | `AgvAssignmentEdgeKey` into `volley::scheduler` (4457650642) | Only `agv_assignment.cpp` uses it. A `std::hash` specialisation for an alias of `std::pair` is a specialisation for `std::pair` itself. | Now. Move it, with a named hasher passed to the map instead of `std::hash` (Codex's point). | 5 |
| 4 | Stage types out of `scheduler.hpp` (4457650653) | `AgvAssignmentState`, `TrayAssignmentState`, `ResolveRequest`, `CandidateMove` (and `PlannedTrayMove`, `TrayDestinationPlan`) are used only by `agv_assignment.cpp`, `tray_assignment.cpp`, `validation.cpp`, `scheduler.cpp`. `scheduler.hpp` needs only declarations for the private method signatures. | Now. Private headers `src/agv_assignment.hpp` and `src/tray_assignment.hpp` next to the stage files; forward declarations in `scheduler.hpp`. C1 later moves the tray ones into `blocking_trays.hpp`, F the AGV ones into its module. | 5 |
| 5 | `MakeAgvPoseMove` / `MakeTrayMove` out of `utils.hpp` (4457650661) | Confirmed: the only reason for `schedule_events.hpp` in `utils.hpp`. Used by `job_expansion.cpp`, `agv_assignment.cpp`, `tray_assignment.cpp`. | Now. Private header and source `src/move_events.{hpp,cpp}`. | 3 |
| 6 | `FindKeepOutFilter` returns a pointer (4457650624) | Confirmed: four of five callers build the same "No keep-out filter for footprint {}" error; the fifth (`job_expansion.cpp:862`, the charger search) treats absence as no candidate. | Now. `stdx::Expected<std::reference_wrapper<const GraphFilterProperties>>`, message built once; the charger search maps the error to `nullopt`. Same texts, so the recordings stay. | 4 |
| 7 | `RemoveRedundantEdges` ignores a cycle (4457650611) | Confirmed, and this PR changed it: `Reduce()` on main returned `{false, "The graph must be a DAG."}`. No production caller read it, though; only a test did. `AddDependency` does not refuse cycles. | Now. `[[nodiscard]] stdx::Result` with the old text, a test for a cyclic graph left unchanged. The five callers (`scheduler.cpp`, `agv_assignment.cpp`, three in `action_graph.cpp`) propagate it. A cyclic plan then fails at the reduction instead of at the later ordering; any recording that changes is reviewed, not re-recorded blindly. | 2 |
| 8 | `GetNode` throws (4457650597) | This PR changed it: main's `GetFromVertex` returned `optional`, but every caller called `.value()` at once, so it threw there too. Callers pass vertices from `GetVertices()`, an ordering or an edge. | Now, keep throwing: a bad vertex is a broken invariant, and `optional` would only add `.value()` at each site. One-line contract comment (Dan offered this option) and an invalid-vertex test. | 2 |
| 9 | `ApplyTo` / `ApplyBayCommand` return `BoolStringPair` (4457650562) | Confirmed. `OnEvent` has many overloads and callers in `central` and `common_ros` (Dan counts 25 outside `common_ros`). His question: `SucceededEvent` is never called with a message, so no caller can read a success text. | Defer to its own PR, as Dan offered: it adds API to `common_ros`, which central, bay and vecs share. Phase H in `PROMPT.md`. | ticket |
| 10 | `PlanMotions` loses the reason (4457650583) | Confirmed. The reasons are only logged inside `motion_planner` (`Chugg::SolveSequential`, `PlanNodeSequential`, `PlanEventSequential` return `optional` / `bool`), so returning `Expected` from `PlanMotions` alone would carry the same generic text. | Defer: a `motion_planner` change, `Expected` through the sequential solver plus its four tests, and it changes the failure texts reported for infeasible plans. Phase C0 already moves `PlanMotions` into `motion_planning/`. | ticket |
| 11 | rclcppx for parameters and ROS interfaces (4457602136, and his message) | The scheduler already uses `rclcppx` for logging and services (`CreateService`); the node and component wrappers and `Param` still come from `common_ros`. `rclcppx` has `node.hpp`, `component.hpp`, `parameter.hpp`. | Defer to a follow-up PR with startup, parameter and service checks. Section 9 of `PROMPT.md` ("rest of B2, the ROS boundary") is where it fits. | ticket |
| 12 | "But I do love removals", "Thank you", 🙏 | — | No change; a short reply or a reaction. | — |


### Dan's third review: includes and aliases (5756330572, 17:00, 11 comments)

He checked every removal with `clang++ -fsyntax-only` over the 81 planner and agvctl translation units.
Summary: no package can drop `common` or `common_ros` yet; the scheduler headers can be free of
`common/`; planner_core could drop `common` once `ApplyTo` leaves `BoolStringPair` (item 9, deferred) and
`EnumNameString` has a home in stdx. The build checks each removal again here, so nothing relies on a
transitive include. All are in code this PR rewrote, so all go in now.

| # | Thread | Plan | Commit |
|---|---|---|---|
| 13 | `scheduler.hpp` includes (4457901158) | Drop `<chrono>`, `<common/constants.hpp>`, `<common/types.hpp>`, `<motion_planner/garage_graph_pathing.hpp>`, `"scheduler/utils.hpp"`; `<rclcpp/rclcpp.hpp>` becomes `<rclcpp/logger.hpp>` and `<rclcpp/time.hpp>`; `GetVersionInfo`'s body moves to `scheduler.cpp`, taking `<common/system_utils.hpp>` with it. `agv_assignment.cpp`, `job_expansion.cpp`, `scheduler.cpp`, `tray_assignment.cpp` include `utils.hpp` themselves. Together with item 4 (stage types). | 5 |
| 14 | `utils.hpp`: `<common/types.hpp>`, `<interfaces/msg/guid.hpp>` (4457901167) | Drop both (item 5 already takes `schedule_events.hpp` out). | 5 |
| 15 | `utils.cpp`: four `interfaces/msg` includes (4457901176) | Drop them. | 5 |
| 16 | `scheduler.cpp`: `<ranges>` → `<algorithm>`, `format.hpp` unused (4457901182) | As suggested. | 5 |
| 17 | `action_graph.cpp`: `format.hpp` unused (4457901191) | Drop it. | 5 |
| 18 | `agv_assignment.cpp`: `format.hpp` unused (4457901199) | Drop it. | 5 |
| 19 | `event_dag.hpp`: `<common/types.hpp>` unused (4457901216) | Drop it; item 7 returns `stdx::Result`, already included. | 2 |
| 20 | `chugg_common.cpp`: `<queue>` unused (4457901225) | Drop it. | 2 |
| 21 | `agv_hiding_search.hpp`: `pose_utils`, `<chrono>`, `<common/types.hpp>`; `common/types.hpp` in `garage_graph_pathing.hpp`, `static_graph_filtering.hpp` (4457901238) | Drop them. | 2 |
| 22 | `schedule_events.hpp` / `event_dag.hpp` use the `*Msg` aliases (about 40) (4457901252) | `interfaces::msg::X` with its `#include`, as the scheduler does; same types, so no caller changes; drop `<common_ros/pose_utils.hpp>`, `<ostream>` and `planner_core_msgs.hpp` from these two. Deleting `planner_core_msgs.hpp` stays for later, as Dan says. | 2 |
| 23 | `FindAgvUnderTrayAssignment`, `FindPosePath` take `GaragePoseMsg` (4457901264) | `interfaces::msg::GaragePose` in the signatures this PR rewrote. | 2 |

Differences from Codex's plan:
- Codex would do 9 and 10 now (adapter around `OnEvent`, `Expected` through sequential planning). Both
  reach outside the scheduler, change shared or operator-facing behaviour, and Dan offered follow-ups.
  This PR is already large and in review.
- Same as Codex for 1-8, except 8: Codex's "document and test" is the same as here; its CHUGG
  restructuring note does not apply once 10 is deferred.
- Codex's three batches become per-commit folds (house style), in the order 2, 3, 4, 5, 6 so each
  rebuild sees its earlier commits. With the third review, commit 2 takes items 7, 8, 19-23, commit 3
  item 5, commit 4 item 6, commit 5 items 2-4 and 13-18, commit 6 item 1.

Checks after the fold (review rules section 7): clang-format, the build with 0 warnings, scheduler,
planner_core, motion_planner and scheduler_advanced_tests tests, with and without
`SCHEDULER_CHECK_RECORDINGS=1`, `prek run --files`, then `volley-in-container tidy` on the tip. Every commit
builds (`check_commits` script).

Follow-up tickets to propose to the user (creating them is the user's call): items 9, 10, 11.

## As applied (2026-11-03)

Folded with `fix_a23.py` (scratchpad); the commits differ from the plan above where the code made it
simpler:
- Item 7 (`RemoveRedundantEdges`) went into commit 6, not 2: the callers' code differs at every
  stage before the split, and commit 6 already makes the action-graph helpers propagate failures.
- Item 5 (move factories) went into commit 5, the file split, not 3.
- Item 3: a named hasher does not compile, because task_planner's `BottleneckAssignment` takes
  `std::unordered_map<std::pair<L, R>, V>` with the default hasher. The `std::hash` specialisation
  moved to `agv_assignment.cpp` instead.
- Item 4: no private headers. Each stage type is defined in the one `.cpp` that uses it.
  `ResolveRequest`, `PlannedTrayMove` and `TrayDestinationPlan` stay in `scheduler.hpp`, because
  `ResolveBlockingTrays` is public and tested.
- Item 2 also took four AGV-ordering methods Dan did not list but nothing outside calls.
- Test 06 checks for "must be a DAG" instead of "Failed to get final ordering". A cycle now fails at
  the reduction just before that check.

## Replies (as posted, from `post_dan_replies.sh`)

Each reply goes into the thread of the inline comment it names; reactions where no text is needed.

Review 1:
- **4457348192 (advanced tests):** 01-04 ran on 576_eccles, which is decommissioned (the one tiny_lot test
  became `MoveJob.TwoTrayMovesWithAgvUnderOneTray`). 05-07 run on layouts still in service and each guards
  a planning fix, so I kept them and renamed them: `cross_floor_pathing_tests`, `vrc_insertion_cycle_tests`
  and `chokepoint_pathing_tests`.
- **4457350408 (removals):** 👍 reaction.
- **4457556096 ("Thank you."):** 👍 reaction.
- **4457558467 (🙏):** nothing.
- **4457602136 (rclcppx):** Yes, I'd like to do that as a separate PR (the node and component wrappers and
  `Param` together). I'll make a ticket.

Review 2:
- **4457650562 (`ApplyTo`):** Agreed. On your question: `SucceededEvent` is never called with a message, so
  no caller relies on a success text. Since this adds API to common_ros, I'll do it in a follow-up PR as you
  suggested and make a ticket.
- **4457650583 (`PlanMotions`):** Agreed. The reasons are only logged inside motion_planner today
  (`SolveSequential` returns `optional`), so this needs a motion_planner change as well. I'll do it in a
  follow-up and make a ticket.
- **4457650597 (`GetNode`):** Throwing is deliberate: callers only pass vertices from the graph itself. Added
  the one-line note and a test for an unknown vertex.
- **4457650611 (`RemoveRedundantEdges`):** Good catch. It returns `stdx::Result` with "The graph must be a
  DAG." again, and the callers propagate it. Added a test.
- **4457650624 (`FindKeepOutFilter`):** Done. The charger search returns `nullopt` on the error.
- **4457650634 (private methods):** Done. I also made four AGV-ordering methods private, since nothing outside
  `Scheduler` calls them either.
- **4457650642 (`AgvAssignmentEdgeKey`):** Moved into `volley::scheduler`. The `std::hash` specialisation
  stays, because task_planner's `BottleneckAssignment` uses the default hasher, but it now lives in
  `agv_assignment.cpp`.
- **4457650653 (stage types):** Done: `AgvAssignmentState`, `TrayAssignmentState` and `CandidateMove` are now
  each defined in the one .cpp that uses them. `ResolveRequest` stays for now, since `ResolveBlockingTrays`
  is public and tested; it moves with the tray module.
- **4457650661 (`utils.hpp`):** Done: they moved to `move_events.hpp`.

Review 3:
- **4457901158 (`scheduler.hpp` includes):** Done, including moving `GetVersionInfo` into scheduler.cpp.
- **4457901252 (planner_core aliases):** Done. I left `planner_core_msgs.hpp` itself for a later cleanup.
- **4457901167, 4457901176, 4457901182, 4457901191, 4457901199, 4457901216, 4457901225, 4457901238,
  4457901264:** Done.

Conversation: Thanks for the reviews, Dan! The changes are pushed. The `ApplyTo`/`OnEvent` migration, the
`PlanMotions` failure reasons and the rclcppx move will be follow-up tickets.
