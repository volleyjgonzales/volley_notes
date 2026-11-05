# Codex review 10 (2026-10-31) and its evaluation

Codex read the tip `dca15cf9`: names of motion_planner functions the scheduler calls, and
FindProcessRetrieveAction. Checked here; nothing changed (item 231).

User's question: is "exclusion filter" standard? No. The standard terms are "keep-out" (Nav2's costmap
KeepoutFilter, keep-out zones in AGV and warehouse robotics) and "filtered graph" (Boost.Graph's
`filtered_graph` with vertex and edge predicates; GraphFilterProperties is that). The scheduler already
says it: the result is stored in `keep_out_filter_by_footprint`. So a name, if any: `BuildKeepOutFilters`.

| # | Finding | Check | Verdict |
|---|---|---|---|
| 1 | GetDisabledEntitiesFilters: incomplete name; wrap as BuildPlanningExclusionFilters. | Confirmed: per footprint (collision id), a GraphFilterProperties that keeps disabled AGVs, trays and bays and anything on a disabled node, and ignores the rest. motion_planner API; 3 files outside the scheduler call it. | No scheduler wrapper: its one call site assigns to `keep_out_filter_by_footprint`, which already says what the result is. Rename it `BuildKeepOutFilters` in motion_planner, in a naming ticket (below). |
| 2 | GetEdgeDurations computes; ComputeEdgeTransitionDurations; locals. | Confirmed: evaluates the cost model on every edge. 7 files outside. | API rename in the ticket. Locals in PlanMotions: `edge_durations` is accurate; `heuristics` is the standard A* term (the comment above says so); keep both. |
| 3 | FindProcessRetrieveAction reads as Find + Process. | Fair: the command name starts with a verb. | Agree: `FindRetrieveProcessingAction`, local `retrieve_processing_action`. Commit 3. |
| 4 | GetStaticFilter, GetPosePath, GetAllPairsMinCost, HideAgvs, ConvertPosePathToTrajectory hide computation. | Confirmed; 3 to 6 files outside the scheduler each. HideAgvs returns `pair<bool, map>`; the scheduler unpacks it as `[hide_ok, hide_assignments]`, a bool without `is_`. | API renames in the ticket (BuildCollisionFilter, FindPosePath, ComputeAllPairsMinimumCosts, BuildTrajectoryFromPosePath; for HideAgvs, keep the code's own term "hiding": FindAgvHidingPoses, returning a named result instead of the pair). Now, in our code: `[is_hiding_found, hiding_pose_by_agv]`. Commit 1 (where the job expansion locals were named). |
| 5 | Keep real getters and SingleSourceSearch. | Agree. | No change. |

Ticket proposal (motion_planner naming pass, separate PR): BuildKeepOutFilters, BuildCollisionFilter,
ComputeEdgeTransitionDurations, ComputeAllPairsMinimumCosts, FindPosePath, BuildTrajectoryFromPosePath,
FindAgvHidingPoses with a named result. Touches motion_planner, its tests and 3-7 callers each.

## Agreed proposal after discussion and Codex's review of it (item 232)

The user: rename at the source where possible (packages under src/planner are in scope), no wrappers;
standard vocabulary. Settled names: BuildKeepOutFilters, BuildStaticObstacleFilter(s) (contract: the
state snapshot treated as stationary for this search), ComputeEdgeDurations,
ComputeEdgeMarginalDurations, ComputeAllPairsShortestPathCosts, FindPosePath (kept "Pose": the
blocking-tray search returns vertex-state paths, `critical_path` is vertex-keyed, so "pose path" is a
real distinction; ConvertPosePathToTrajectory stays as it is), FindAgvUnderTrayAssignment returning
`std::optional<map>` (internal recursion: FindRemainingAgvUnderTrayAssignment, file-local; the base
case returns an engaged empty map, not nullopt; new test for no enabled AGVs; callers test
engagement), contract comment without the fewest-moves claim. Scheduler: FindPayloadDeliveryAction
(contract: "the job's PROCESS_RETRIEVE bay action"; Codex confirmed the bay emits
EVENT_PAYLOAD_DELIVERED for it). Dead code: the commented-out edge-cost line in
agv_hiding_search.cpp, the commented-out initializer and member in the header; the cpp's TODO about
unit edge costs stays (the header's duplicate goes). Search order, candidate order and
success/failure semantics unchanged.
