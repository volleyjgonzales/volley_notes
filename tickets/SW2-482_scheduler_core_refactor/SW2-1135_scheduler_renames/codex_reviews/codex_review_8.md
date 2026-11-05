# Codex review 8 (2026-10-30) and its evaluation

Codex read the tip `7166af0e` (source only): extraction candidates in Plan(), PlanMotions() and
AssignAgvs(), and the retrieval-heading setup. Checked here by reading; applied in item 228; tip `f756a7cc`.
Every block is older than this branch (main or commit 1), so all of it is behaviour-neutral clean-up.

| # | Finding | Check | Verdict | Commit |
|---|---|---|---|---|
| 1 | InitRetrievalHeadings: abbreviated verb, unclear object; rename to CachePreferredRetrievalHeadingsForParkingNodes; optionally a free function computing a node-to-heading map; clearer locals. | Confirmed: it picks the reverse of the first-choice retrieve bay's inbound heading and stores it in the motion graph for each parking node that allows it and can reach the bay. | Agree on a full verb and the object. Propose `StorePreferredRetrievalHeadings` (it writes into the motion graph; "parking nodes" is in its comment). Locals as Codex proposes (`preferred_retrieve_bay_id`, `bay_inbound_heading_opt`, `preferred_retrieval_heading`, `parking_pose`, `allowed_node_headings`) plus `bay_pose` to `preferred_bay_pose`. Skip the free-function split: it runs once in the constructor and would need the logger or an error channel for one LOG_ERROR. FindRetrievalTrayHeading's comment follows the rename. | 1 |
| 2 | Base-schedule exclusions as a state transformation; `scheduled_action` for the loop variable; a switch. | Confirmed: AGV commands disable the AGV and both nodes, bay and VECS commands their entity; VRC commands are ignored (pre-existing; see below). | Agree: file-local `DisableBaseScheduleEntities(DiscreteGarageState state, std::span<const ActionNode> scheduled_actions)` returning the state (name follows the SetXDisabled calls and the entity vocabulary; Codex's ExcludeBaseScheduleResources is the alternative); switch with the other types left alone; the comment goes. | 3 |
| 3 | Retrieve-action lookup out of response assembly. | Confirmed. | Agree: file-local `FindProcessRetrieveAction(actions, job_id)` returning `const ActionNode*` (named after COMMAND_TYPE_PROCESS_RETRIEVE); local `process_retrieve_action`; the missing-action branch and its TODO stay at the caller. | 3 |
| 4 | Cost-audit CSV out of PlanMotions. | Confirmed: CSV header, per-entry lines, running total, drift warning. | Agree: file-local `LogMotionCostAudit(cost::CostVector& audit, const rclcpp::Logger& logger)`; `i` to `entry_index`, `running_seconds` to `cumulative_seconds`. | 3 |
| 5 | AssignAgvs setup: merge the two enabled-AGV loops; renames. | Confirmed: the second loop records `last_occupant_by_node` for the same enabled AGVs; merging moves it before the "no available AGVs" return, which then discards the state anyway. | Agree: one loop; `event_dag_copy` to `pending_events` (the name ApplyNonTrayRootEvents already uses), `agvs_to_assign` to `available_agv_ids`, `ordering_opt` to `agv_assignment_order_opt`, `event_cost` to `assignment_duration_or` (house rule: `_or` for an Expected). Renames limited to AssignAgvs (`ordering_opt` exists in other functions). | 3 |
| 6 | `HasTrayMoveEvents(ctx->event_dag)` for the opening none_of. | Confirmed. | Agree, file-local in agv_assignment.cpp. | 3 |

Observation, not proposed here: base-schedule VRC commands are not excluded, so a plan may use a car
lift that committed actions are using. Pre-existing; a ticket if it matters.

Proposed landing: #1 in commit 1 (where names were set), #2 to #6 in commit 3 (where long functions
handed named blocks to helpers). All commits rebuilt; recordings must stay identical.

## As applied (item 228)

As recommended, with the user's choice of names. #1 in commit 1 (token rename, locals renamed in code
only, so the LOG_ERROR text is unchanged); #2-#6 in commit 3: DisableBaseScheduleEntities,
FindProcessRetrieveAction and LogMotionCostAudit go into the file-local namespace of the file that
defines Plan() (scheduler.cpp; a new anonymous namespace after the split), HasTrayMoveEvents into
agv_assignment's. Log texts unchanged; recordings unchanged. Commit 3's message names the new functions.
