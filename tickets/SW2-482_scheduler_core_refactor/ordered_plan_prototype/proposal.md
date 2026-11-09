# Ordered plan: a simpler model for the scheduler's event graph (proposal, 2026-11-08)

Status: proposal, revised after Codex review 1 (`codex_reviews/assessment_1.md`). Nothing
implemented. Line numbers are from `jmg/SW2-905/insert-stall-blocked-by-agv` at `a38e7eb8`.

## Problem

The scheduler keeps its plan in `ScheduleEventDag` (`planner_core/event_dag.hpp`, a boost
`adjacency_list` of `shared_ptr<ScheduleEvent>`). Boost is not the problem. The problem is
that a graph everyone edits is the source of truth, while nearly all reasoning runs on a
flattened copy of it:

- **State is computed from an order nobody stores.** `ApplyEventsTo`, `ComputeStateBefore`,
  `AddNextMissingAgvMoveOrder`, `ValidateEventSequence` and Chugg each call
  `GetTopologicalOrdering()` and replay. The order among independent events is a tie-break
  (job index, then creation order since PR #1036), so "the state before event X" changes when an
  edge is added elsewhere.
- **Stages flatten differently.** `AssignAgvs` applies every non-tray root before costing tray
  roots (`ApplyNonTrayRootEvents`, `agv_assignment.cpp:189`); validation replays the topological
  order. The EV-charge session hit this: bay transition and carrier approach replayed in
  different orders, "Cannot find path from 5@90 to 7@90".
- **Edges come from about ten places, each with its own rule:** `ChainAfterLastEntityEvent`,
  `OrderAfterJobLeafEvents`, tray-assignment blockers (`OrderAfterPriorOccupants`),
  `OrderAfterTraysOnPath`, `OrderTransitionAroundAgvLifts`, `OrderAgvMoveAfterBlockerDeparture`
  (guarded by `WouldCreateCycle`), eviction edges, then `RemoveRedundantEdges`. There are three
  parallel per-entity chain mechanisms: `ChainTrayEvent`/`first_event_by_tray`,
  `ChainAgvEvent`/`last_event_by_agv`, `PlanContext::last_event_by_entity`.
- **Results depend on which edges are direct.** `OrderTransitionAroundAgvLifts` walks direct
  parents/children right after `RemoveRedundantEdges` (`agv_assignment.cpp:182-186, 660-685`);
  the TODO at `scheduler.cpp:201` says planning fails without the reduction.

Two bugs this week came straight from this: an eviction added with `AddEvent` instead of
`AddChainedEvent`, so the AGV's later move still started from its old pose (SW2-1190,
`282431de`; PR #1036), and the replay-order mismatch above.

## What needs a partial order

1. **AGV assignment** matches a frontier of ready tray moves together (`BottleneckAssignment`
   over `GetRootEvents()` of a copy it `Remove`s from, `agv_assignment.cpp:121-172`).
2. **Chugg**: `GetDependencyCompletionTime` (`chugg_common.cpp:185`) starts an event when its
   parents finish.
3. **The executor**: the action graph's `parents` (`action_graph.cpp:452-462`).

Everything else (job expansion, tray assignment, validation) linearises anyway.

## Proposed model

Vocabulary from Codex review 1. These are responsibilities, not six new classes.

| Concept | Responsibility |
|---|---|
| `OrderedPlan` | Events with stable IDs and one canonical replay order, **stored**, not recomputed |
| Prerequisites | Required orderings by event ID, each with a reason (`same AGV`, `job sequence`, `vacates destination`, `clears route`, `lift before transition`, ...) |
| `ReplayPlan` | State evolution along the stored order, with named checks (below) |
| Checked plan edits | `Insert`, `Replace`, `Reorder`: transactional; the only way to change the plan |
| Dependency derivation | Adds resource and occupancy prerequisites by rule, in one place |
| Execution graph | The final graph for Chugg and the action graph; same output format as today |

### Rules

- The stored order always satisfies every prerequisite. An edit that cannot satisfy them fails
  with both prerequisites and their reasons ("no position satisfies A and B"). This replaces
  `WouldCreateCycle`.
- Replay has three separate checks, named as such:
  - **apply**: `ApplyTo` computes the next discrete state (start pose, tray presence);
  - **planning preconditions**: destination clear by footprint (collision table), bay state
    allows it;
  - **motion feasibility**: a route exists given persistent occupancy (`ValidateEventSequence`'s
    job). Timing stays with Chugg.
- Inserting at index *i* replays the suffix, so a later event whose start is now stale fails at
  the edit, not at validation.
- Three conflict classes:
  - **ownership**: same AGV, tray, bay or VECS, a prerequisite;
  - **persistent occupancy**: an event that vacates a pose another event needs, at its endpoints
    *or along its route* (today's `OrderAfterTraysOnPath`, `OrderAgvMoveAfterBlockerDeparture`,
    eviction-before-tray-move), a prerequisite with reason;
  - **transient traffic**: two moves crossing in time, left to Chugg, as now. No edge, so motion
    is not serialised (the EV-charge session's example: an edge from the bay transition to the
    carrier approach would delay the approach by the 14 s bay command).
- Semantic orderings stay explicit prerequisites: job sequence, bay chained after a hiding move's
  arrival, a move out of a bay after the bay's last transition.
- AGV assignment computes its frontier from prerequisites (events whose prerequisites are all
  assigned), matches as today, and writes the resulting order back through one `Reorder` edit.
  Which AGV carries a tray stays open until then.
- Transitive edges never change meaning. Any consumer that reads direct parents must read
  reachability or an explicit prerequisite instead (fixes the `RemoveRedundantEdges` TODO at its
  cause).

## Not solved by this

- Evicting an AGV that is then chosen as carrier makes a pointless relocation trip; the evicted
  AGV is still a candidate (`available_agv_ids`, `agv_assignment.cpp:108-117`). Needs carrier
  choice and relocation considered together. A follow-up.
- An AGV with later moves is not evicted. That is a first-version policy; re-resolving the later
  move from its new start is possible later.

## Risks

- Deriving prerequisites while planning, not from today's finished graph, is unproven; the
  prototype's phase 2 tests it.
- Replay cost: O(n) per insert, O(n^2) per plan, plus geometry and path searches in
  preconditions. Measure.
- Recordings: target zero changes first. Any change is reviewed per scenario with the viewer, as
  in #1007 and #1018. No bulk re-recording.

## Prototype

See `jira_ticket.md`. Phase 1 shadows today's pipeline and compares; phase 2 builds
prerequisites while planning for one stage. Production code is unchanged until a go/no-go.

## Input

- Codex review 1: `codex_reviews/codex_review_1.md`, assessed in `codex_reviews/assessment_1.md`.
- SW2-905 / SW2-1190 session (2026-11-08): list model would have prevented the stale-start bug.
  Conflicts are spatial (charger 14 vs stall 15, about 0.6 m apart), so per-resource lanes alone
  reproduce the bug class. The occupancy history in `AssignTrays` is already a small derived-deps
  engine but does not record AGV moves.
- EV-charge session (PR #1036, 2026-11-08): two of three bugs this week were ordering bugs a
  stored order prevents. The third (AGV with later moves) needs an exclusion rule under any
  order. Warned against route-level edges.
- Background: `volley_notes/research/action_dependency_graph/` (CBS to the action dependency
  graph) and `volley_notes/presentations/scheduler_package/`.
