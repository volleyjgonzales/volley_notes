# Names that lean on a comment (survey, 2026-11-01, item 246)

The user: "I don't want to rely on comments" to explain a name. Surveyed every comment on a declaration
in the scheduler's headers and the file-local ones in its sources, at tip `ce566d68` plus the
`target_insert_ready_bay_fraction` rename. A comment that states a reason, a unit of work order or an
edge-case contract stays; a comment that says what a name should have said is listed.

## Names to change (applied in item 247, except `BayClassification`)

| Where | Name | Comment that covers it | Proposal |
|---|---|---|---|
| `bay_rebalancing.hpp` | `ClassifyBay(uint8_t state, ...)` | "`state` is the bay's planned state once the schedule is done" | `planned_bay_state` |
| `bay_rebalancing.hpp` | `BayClassification` values | a trailing comment on each value; `NOT_USABLE` says "in an error state" but is also returned for disabled bays, non-processing states and a payload without a tray | see below |
| `scheduler.hpp` | `PlannedTrayMove::path` | "`path` is empty when recursion produced the move"; holds the search path, the advance's two poses or the root path's poses | `occupied_poses` (each pose is ordered after its prior occupants and registered as occupied by the move) |
| `scheduler.hpp` | `PlannedTrayMove::applied_from` | "the tray's pose before the move when the move is already applied" | `source_pose_if_applied` |
| `scheduler.hpp` | `BlockingTrayResolution::path` | "empty when `prereq_moves` exist" | follows `PlannedTrayMove` |
| `scheduler.hpp` | `AgvAssignmentState::last_occupant_by_node` | "Lets an arrival depend on the prior occupant's last event" (it holds an AGV id) | `last_agv_by_node` |
| `scheduler.hpp` | `agv_occupied_durations` | "How long each AGV is busy with the events assigned to it so far" | `busy_duration_by_agv` (the code's `_by_` convention) |
| `scheduler.hpp` | `event_earliest_starts` | "The earliest start of each event, from the assigned events it waits for" | `earliest_start_by_event` |
| `scheduler.hpp` | `RepairAgvMovePaths` | "AssignAgvs does not know the final topological order; this adds the gating edges it missed" | `OrderAgvMovesAfterBlockingAgvs` (it adds ordering edges; paths are unchanged) |
| `scheduler.hpp` | `RunAgvPathRepairPass` -> `Expected<bool>` | "True if it added an edge" | `AddNextMissingAgvMoveOrder`, returning `is_edge_added` by name |
| `scheduler.hpp` | `MakeBayInboundPose` | "The bay's node with its configured inbound heading." | name is enough: delete the comment |
| `scheduler.hpp` | `IsPlainParkingSpot` | "A parking node with no EV charger and no bay on it." | `IsParkingWithoutBayOrCharger` |
| `scheduler.hpp` | `ScheduleAgvLift(..., is_raising)` | "Adds the AGV's lift (`is_raising`) or lower" | `ScheduleAgvLiftChange` |
| `action_graph.cpp` | `BuildScheduledActionsArray` | "Also writes node_indices into ctx->scheduled_jobs" | a separate `WriteJobActionIndices` step (applied in commit 4, which wrote the function's current shape) |
| `action_graph.cpp` | `ComputeVrcFloorTransitDuration` -> `float` | "Seconds for ..." | `ComputeVrcFloorTransitSeconds` (or return a `Duration`) |
| `action_graph.cpp` | `ActionSpan` | "The first and last action nodes made from one event's motions." | `EventActionSpan` |
| `scheduler_ros.hpp` | `pub_cb_group_` | "For the publication timers, so the long-running Plan service ... cannot block them." | `publication_timer_callback_group_` (the reason stays) |

`BayClassification`, one option (the bay's state and what it holds):
`READY_TO_INSERT_WITH_EMPTY_TRAY`, `WILL_BE_READY_TO_INSERT`, `READY_TO_RETRIEVE_AND_EMPTY`,
`WILL_BE_READY_TO_RETRIEVE` (never produced, see below), `READY_TO_INSERT_BUT_BLOCKED`,
`READY_TO_RETRIEVE_BUT_HOLDS_TRAY`, `WILL_BE_READY_TO_RETRIEVE_BUT_HOLDS_TRAY`, `UNUSABLE`. Needs a
discussion of its own (the user, item 247).

Also renamed with these in item 247: `agv_occupied_duration` (ComputeAgvAssignmentCost) to
`agv_busy_duration`, `kMaxAgvPathRepairPasses` to `kMaxAgvMoveOrderPasses`, the locals `added_edge` to
`is_edge_added`, `path_repair` to `ordered`, `unblock_path`/`new_move_path` to `occupied_poses`.
Item 248: `AddNextMissingAgvMoveOrder`'s two error texts no longer start "EnsureAgvMovePathsClear:" (commit
4); test07's header comment names `OrderAgvMovesAfterBlockingAgvs` and `AssignAgvs` (commit 1) and
`agv_assignment.cpp` (commit 5).

Item 249 (commit 4): the 31 strings from main that named 13 functions that no longer exist lose the
old name or say the step that failed; "Cannot find path" stays (two advanced tests look for it). They were: `DoAgvAssignments` 7, `PlanInsertJob` 6, `PlanReadyForInsertJob` 4, `PlanCleanGarageJob` 3,
`PlanUnstashWaypointTraysJob` 2, `AddDepsAfterAmiga` 2, and one each of `TrayAssignments`, `SchedulerNode`,
`PlanRebalanceGarageJob`, `PlanOpenBayDoor`, `IsMovePossible`, `GetJustMovingCost`, `DoTrayAssignments`.

## Found on the way

- `BayClassification::WILL_BE_RETRIEVE_READY` is never produced: `ClassifyBay` maps PROCESSING_INSERT to
  `WILL_BE_RETRIEVE_READY_BUT_INVALID`. `ComputeBayRebalancingActions` still checks for it
  (`bay_rebalancing.cpp:92`): a dead branch.

## Kept (reason, contract or domain term)

`AddChainedEvent` (kept by the user's decision, round 9); `occupancy_history`; `ResolveDestinationHeading`,
`FindPreferredTrayHeadingForRetrieval`, `ResolveCarriedTrayDestination`, `ApplyBayOrChargerTransition`,
`ScheduleAgvMoveToPickup`, `OrderArrivalAfterPriorOccupant`, `IsPayloadWithinBaySizeLimits`,
`ValidateBaseState`, `MakeInboundPose`, `ResolveBlockingTrays`, `TrayDestinationPlan` (edge-case
contracts); `IsBayOdpAreaClear` (ODP is the domain's term, as `CollisionEntityId::BAY_ODP`);
`target_insert_ready_bay_fraction_` ("Atomic: several callback groups..."), `is_dag_printing_enabled_`
(a dependency), `kMaxAgvPathRepairPasses`, `kBay*PlaceholderId`, `IsLiftedMotion`,
`FindPayloadDeliveryAction` (reasons).

## BayClassification (applied in item 265, commit 1)

After Codex's review and the user's question ("does READY_TO_INSERT_WITHOUT_EMPTY_TRAY mean insert with
payload?"): the values say what the bay is ready for, still needs, or is doing, in the scheduler's own
insert/retrieve words, without comments: `INSERT_READY`, `INSERT_NEEDS_EMPTY_TRAY` (was
`INSERT_READY_BUT_INVALID`), `INSERT_IN_PROGRESS` (was `WILL_BE_RETRIEVE_READY_BUT_INVALID`),
`RETRIEVE_READY`, `RETRIEVE_NEEDS_TRAY_REMOVAL` (was `RETRIEVE_READY_BUT_INVALID`), `RETRIEVE_IN_PROGRESS`
(was `WILL_BE_INSERT_READY`), `NOT_USABLE`. `WILL_BE_RETRIEVE_READY` (never produced) is deleted with its
branch; one reason comment stays at the rule that counts a retrieve in progress as insert-ready.

Found, for a ticket: `INSERT_IN_PROGRESS` counts as an eligible bay in the split but toward neither target,
so the split can be off by one (one bay mid-insert and one empty retrieve-ready bay at ratio 0.5 turns
the empty bay insert-ready). Fixing it changes planning output.
