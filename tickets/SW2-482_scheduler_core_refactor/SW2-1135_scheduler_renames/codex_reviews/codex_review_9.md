# Codex review 9 (2026-10-31) and its evaluation

Codex read the tip `f756a7cc` (source only): vocabulary (entity, resource, the Add/Order/Apply/Schedule
verbs), the base-schedule helper, the retrieval-heading cache, the floor-change check. Checked here
against the code, PlanRequest.msg and the blocking-tray search; applied in item 230; tip `dca15cf9`.

| # | Finding | Check | Verdict | Commit |
|---|---|---|---|---|
| 1 | Keep "entity" for GarageEntityId objects; "resource" for what a plan may not use; no "asset". | "asset" appears nowhere in the scheduler; "entity" is used only with GarageEntityId. | Agree; nothing to change. | none |
| 2 | DisableBaseScheduleEntities hides why (committed) and scope; `committed_actions` local; short contract. | PlanRequest.msg: base_schedule is "the immutable portion of the current schedule"; the helper disables AGVs, their two endpoint nodes, bays and chargers in the planning state copy, not the whole path, not VRCs. | Agree: `ExcludeCommittedResources(state, committed_actions)` (Codex's `...FromPlanning` repeats what the returned planning state says), local `committed_actions = request_data.base_schedule.nodes`, contract: "AGVs and the nodes their committed commands start and end on, bays and chargers; not the paths between, not VRCs". | 3 |
| 3 | The cached heading is the payload's preferred orientation; FindRetrievalTrayHeading turns it into the tray's. | Confirmed: StorePreferredRetrievalHeadings stores one heading per reachable parking node; FindRetrievalTrayHeading and BlockingTraySearch both reverse it when the payload sits reciprocal to its tray. | Agree on the distinction. Names: `StorePreferredPayloadHeadingsForRetrieval` (keeps the verb you chose last round; adds what is stored) and `FindPreferredTrayHeadingForRetrieval`, contracts: "for parking nodes that allow the heading and reach the preferred retrieve bay" / "the tray heading that puts the payload at that node's preferred heading". | 1, 6 |
| 4 | IsFloorTraversalMotion means "changes floors". | Confirmed: an AGV pose change whose source and destination nodes are on different floors; no VRC check. | Agree: `IsAgvMotionBetweenFloors`; locals `first_interfloor_motion`, `combined_interfloor_motion`. | 1 (name), where the locals first appear |
| 5 | AddChainedEvent: identify the chain; AddEventWithEntityOrdering. | It adds the event and calls ChainAfterLastEntityEvent. "Chain" is this code's word for a per-entity event order: ChainAfterLastEntityEvent, ChainTrayEvent, ChainAgvEvent. | Keep the name (renaming one member breaks the family); say which chain in its comment: "Adds `event` and chains it after its entity's last event; a tray move without a tray yet has no entity and is only added." | 3 |
| 6 | AppendAgvLiftEvent and AppendAgvMoveToTrayEvent add events, dependencies and apply state: ScheduleAgvLift, ScheduleAgvMoveToPickup, with a contract. | Confirmed (AddEvent, ChainAgvEvent and further dependencies, ApplyTo, return a duration). | Agree, with Codex's verb rule (Make constructs, Find queries, Add changes graph membership, Order adds dependencies, Apply changes projected state, Schedule does several of these for one planned step). Contract on each: "adds the events and their dependencies, applies them to the working state, returns their duration". | 1 |

The verb rule matches the names already in the code (Make*, Find*, Add*, Order*, Apply*), so adopting
it costs only the two Schedule renames.

## As applied (item 230)

As recommended. Commit 1: IsAgvMotionBetweenFloors with `first_interfloor_motion` and
`combined_interfloor_motion`; StorePreferredPayloadHeadingsForRetrieval with its contract;
ScheduleAgvLift and ScheduleAgvMoveToPickup with contracts (commit 1 still had older `//` comments
above both declarations; the contracts replace them). Commit 3: ExcludeCommittedResources with
`committed_actions` and its contract; AddChainedEvent's comment names the chain. Commit 6:
FindPreferredTrayHeadingForRetrieval with its contract. Commit 3's and 6's messages use the new names.
