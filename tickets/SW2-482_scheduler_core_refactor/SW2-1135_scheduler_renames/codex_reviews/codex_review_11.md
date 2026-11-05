# Codex review 11 (2026-10-31) and its evaluation, with the user's simplification question

Codex read the tip `e6976369`: occupancy vocabulary, collision-id names, the bay/charger transition
helper, the action-graph occupancy skip, blocker-resolution locals. The user also asked which structs
or functions can be simplified (fewer inputs, less common_ros). Checked here; nothing changed (item 234).

## Codex's findings

| # | Finding | Check | Verdict |
|---|---|---|---|
| 1 | MakeBayInboundPose duplicates MakeInboundPose's construction; centralise, keep the bay check. | Same pose for a bay; the bay helper's lookup (GetBayInboundHeading) is the bay-type check. The shared part is one ConstructGaragePose call. | No change: routing through MakeInboundPose adds a node lookup to save one line. |
| 2 | `freeing_moves` holds occupancy history, not freeing moves. | Confirmed: tray moves and bay/charger transitions registered per collision footprint, queried for events to order after. | Agree: `occupancy_history` (TrayAssignmentState member, action-graph local; Codex's event_/action_ prefixes repeat the type), `OrderAfterFreeingMoves` to `OrderAfterPriorOccupants` (the checker's own words, and OrderArrivalAfterPriorOccupant already exists). The debug DAG labels "after_freeing_moves" follow; the TRAY-footprint comment stays. |
| 3 | `tray_entity`, `tray_entity_id`, `root_collision_entity` hold collision ids. | Confirmed. In AssignTrays `tray_entity_id` and `tray_collision_id` are the same constant in one loop. | Agree: one `tray_collision_id` per function (declared once), `root_tray_collision_id`. |
| 4 | ApplyTransitionAndRegisterOccupant takes every non-tray event, handles two. | Confirmed: AGV moves and VRC transitions return without effect. | Agree: `ApplyBayOrChargerTransition`, contract "applies a bay or charger transition to the working state and records it in the occupancy history; other events are ignored". No extracted query. |
| 5 | Make the action-graph occupancy skip explicit; propagate for supported locations. | The locations outside the occupancy graph include AGV edges at pecos charger 14 (item 222), not only bay and VECS motions, so a type test cannot separate expected from unexpected. | Decline: it would need a list of known-missing edges. The skip and its comment state the rule. |
| 6 | Blocker-resolution locals describe representation. | `critical_path` is a vertex-to-footprint map fed to ResolveRequest::illegal_poses, not an ordered path. | Agree in the code's vocabulary: `root_path_illegal_poses`; `blocking_tray_prior_dests` to `prior_dests_by_blocking_tray`; lambda parameters `for_tray` to `blocking_tray_id`, `base` to `illegal_poses` (the lambda name `with_prior_dests` reads well and stays). Comments that say "critical path" follow. |

## The user's question: what else can be simpler

- Fewer inputs: `agv_occupied_durations` and `event_earliest_starts` are AssignAgvs locals passed to
  ApplyNonTrayRootEvents, ComputeAgvAssignmentEdgeCosts and PropagateEarliestStartToChildren. As
  members of AgvAssignmentState they leave three signatures (ComputeAgvAssignmentEdgeCosts from five
  to three). Recommended, commit 3.
- Less common_ros: the scheduler logs with common_ros' stream macros 39 times and rclcppx's format
  macros twice; agvhito, vrc and bay use rclcppx. One style (rclcppx LOG_*) drops
  `common_ros/roslog.hpp` from six scheduler files. Log lines may print numbers slightly differently
  (std::format); logs are not recorded. Recommended, commit 3 (its std::format theme).
- The other common_ros includes are the domain types (DiscreteGarageState, Layout, GarageGraph,
  CollisionTable, GarageOccupancyChecker) or are used; nothing else to drop.
- PlanContextSPtr by value in 34 methods: PlanContext& would say "modifies the plan" without shared
  ownership, but it touches nearly every function in every commit; a change of its own (C1 reshapes
  these signatures anyway).
- The tray-resolution result structs (OpenSpaceSearchResult, BlockingTrayResolution,
  TrayDestinationPlan) are the code the tray solver (SW2-484) replaces; leave them.
- Parameter counts: no method above five.

## Codex's review of this plan, and the refined plan (item 235)

Codex agreed, including both declines. Refinements adopted:
- Occupancy comment: occupants are the events (actions in the graph) whose spatial effect orders what
  comes later, not the objects present now.
- Action-graph skip: the comment says it is a policy (locations outside the occupancy graph add no
  ordering), not a proof that they cannot conflict; the model limitation goes to a ticket. No
  hard-coded edges.
- AgvAssignmentState owns `agv_occupied_durations` and `event_earliest_starts` because they live and
  change with the assignment stage (cohesion, not the parameter count). ComputeAgvAssignmentEdgeCosts
  reads `event_earliest_starts` without inserting (zero when absent; every other read is operator[]
  with the same zero and nothing iterates the map), so it takes `const AgvAssignmentState&`; the
  propagate and apply helpers keep the mutations.
- Logging on rclcppx: existing message strings are passed as data (`LOG_WARN(logger, "{}", message)`),
  never as the format string. The cost-audit CSV keeps its number format: `{:g}` matches the stream
  default (six significant digits); its `entry_index++` moves out of the log call.
- The promise is "planning behaviour and scenario recordings unchanged; log output may change in
  number formatting outside the audit CSV".
