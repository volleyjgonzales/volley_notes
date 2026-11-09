# Assessment of Codex review 1 (2026-11-08)

Each point checked against `jmg/SW2-905/insert-stall-blocked-by-agv` at `a38e7eb8`. Verdict: accept
all five points. Point 3 changes the design the most. Point 5 corrects a claim I relayed from the
SW2-905 session. The proposal (`../proposal.md`) is revised accordingly.

| # | Codex's point | Verdict | Evidence / consequence |
|---|---|---|---|
| 1 | Replay must separate apply, planning preconditions and motion feasibility | Accept | `ScheduleEvent::ApplyTo` checks only discrete-state consistency (e.g. the start-pose check that failed with "a16 should be at 14@-90 but is at 16@-90"). Collision-free destinations live in `GarageOccupancyChecker` and the collision table; reachability in `ValidateEventSequence` (`validation.cpp`); timing in Chugg. The proposal names the three checks and says which edit runs which. "Evicting an AGV with later moves is impossible" is reworded as a policy of the first version: the later move could be re-resolved from its new start. |
| 2 | Start/end overlap is not enough: persistent occupancy along a route needs a prerequisite | Accept; my "routes go to Chugg" was too sharp | Two rules today do exactly this: `OrderAfterTraysOnPath` (`agv_assignment.cpp:715`) orders a pickup after the first move of each initial-state tray on the AGV's path, and `OrderAgvMoveAfterBlockerDeparture` (`agv_assignment.cpp:742`) gates an AGV move on the departure of an AGV whose absence alone clears the path. The proposal now has three conflict classes: ownership, persistent occupancy (endpoints *and* routes: "this move is only possible after that one vacates X"), and transient traffic (Chugg). |
| 3 | "Reorder independent entries" needs independence defined before the final graph exists | Accept; main design change | AGV assignment's batch is a frontier (`GetRootEvents` on a copy that `Remove`s applied events, `agv_assignment.cpp:121-172`), which a list alone cannot produce. Design now keeps **explicit prerequisites with stable IDs and a reason** throughout planning; the list is a canonical replay order consistent with them. Honest framing: this is still a DAG, but a disciplined one: one owner, one checked edit API, a stored order instead of a recomputed one, and every edge labelled with why it exists. |
| 4 | Forward-only edges remove cycles, not contradictions; investigate the `RemoveRedundantEdges` TODO | Accept, and a likely cause found | `OrderTransitionAroundAgvLifts` (`agv_assignment.cpp:646-690`) walks **direct** `GetParents`/`GetChildren` of each bay/VECS transition, and `AssignAgvs` calls it right after `RemoveRedundantEdges` (`agv_assignment.cpp:182-186`). So which lift edges get added depends on which edges are direct, not on reachability. `TransferEventDagDepsToActionDag` also iterates direct out-edges (`action_graph.cpp:440`). Probable explanation of the TODO at `scheduler.cpp:201`; to confirm in the prototype's first step. Contradictions are reported as "no position satisfies prerequisites A (reason) and B (reason)". |
| 5 | Eviction before assignment does not stop the evicted AGV from being the carrier | Accept; my relayed claim was wrong | `AssignAgvs` builds `available_agv_ids` from every non-disabled AGV in `ctx->initial_state` (`agv_assignment.cpp:108-117`), so the evicted AGV stays a candidate. The real cost is the pointless relocation trip when it is then chosen. Fixing that needs carrier choice and relocation considered together (or the relocation revisited after assignment); out of scope for the prototype, listed as a follow-up. |

## Also accepted

- Compare **reachability**, not raw edge sets; report missing and extra orderings separately and
  per rule.
- Matching a graph derived from today's flattened graph is evidence of compatibility only: the
  order already encodes today's decisions. A second phase must build prerequisites while
  planning.
- Behaviour-preserving target first; no bulk re-recording. Any recording change is reviewed per
  scenario.
- Measure replay cost: suffix replay is O(n) per insert and O(n^2) over a plan; geometry and path
  searches inside preconditions are the real cost.
- The responsibility table (`OrderedPlan`, prerequisites, `ReplayPlan`, checked edits,
  dependency derivation, execution graph) is adopted as vocabulary, not as six classes.

## Not covered by the review

- No scenario file is named for an enabled AGV blocking a corridor mid-route
  (`OrderAgvMoveAfterBlockerDeparture`). `FailsWhenDisabledAgvBlocksPath` is the disabled case,
  which that rule skips. The prototype needs one, recorded first on main.
- The EV-charge session fixed the replay tie-break to creation order in PR #1036
  (`event_dag.cpp:56-61`), so a stable canonical order already exists for the prototype to store.
