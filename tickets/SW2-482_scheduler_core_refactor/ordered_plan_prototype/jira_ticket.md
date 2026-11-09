# Proposed Jira work item: prototype an ordered plan for the scheduler's event graph (child of epic SW2-482)

Not created yet. Drafted 2026-11-08 from `proposal.md` and Codex review 1. When created, rename
this folder `SW2-XXXX_ordered_plan_prototype/` and add the link here.

## Title

Prototype an ordered plan with explicit prerequisites for the scheduler's event graph

## How to create and fill the work item

1. Open epic SW2-482 and, under *Child work items*, click **+**. Work type: **Task** (a spike;
   use *Spike* if the board has it).
2. *Summary*: the title above.
3. *Description*: paste the Markdown under "Description" below; check the headings came through
   and turn the Definition of Done into a checklist.
4. *Assignee*: Jon M Gonzales. *Priority*: Medium. *Labels*: Scheduler_and_Dispatcher.
5. *Development*: branch `jmg/SW2-XXXX/ordered-plan-prototype` from `main`.
6. *Linked work items*: relates to SW2-905 and SW2-1190 (the bugs that motivated it); relates to
   SW2-484 (its solver input is already a plain list of steps).

## Description (paste into the Description field)

## Objective

Find out, with evidence, whether the scheduler's event DAG can be replaced by an **ordered plan**:
events with stable IDs, one stored replay order, explicit prerequisites with a reason, and
one checked way to edit the plan, with the execution graph derived at the end. The goal is fewer
ways to change the plan and one replay that every stage shares, not new classes. The outcome
is a go/no-go and a design, not a production change.

## Background

Today about ten functions add edges to a mutable graph, and every stage recomputes a
topological order to replay state. Stages flatten the graph differently: AGV assignment applies
non-tray roots first, validation uses a tie-break. Two bugs this week came from that: an eviction
added without its AGV chain edge (SW2-1190) and a bay-transition/approach replay mismatch
(PR #1036). `OrderTransitionAroundAgvLifts` reads direct parents after `RemoveRedundantEdges`, so
results depend on which edges are direct (TODO at `scheduler.cpp:201`).

## Scope

Prototype code lives in the scheduler's tests (or a tool target), not in the planning path.

1. **Redundant-edge investigation.** Confirm or rule out that the `scheduler.cpp:201` TODO comes
   from consumers reading direct edges (`OrderTransitionAroundAgvLifts`,
   `TransferEventDagDepsToActionDag`). Report each consumer that behaves differently with
   transitive edges present.
2. **Phase 1, shadow comparison.** For every scenario file, take the final event DAG and its
   replay order. Derive prerequisites by rule: ownership (same AGV, tray, bay, VECS), persistent
   occupancy (vacates an endpoint or a pose on the route, via the collision table), and the
   semantic rules (job sequence, bay after hiding arrival, move out of bay after its last
   transition). Compare **reachability** with today's graph and report missing and extra
   orderings separately, grouped by rule.
3. **Phase 1, downstream.** Run `ValidateEventSequence`, Chugg and the action-graph build on the
   derived graph. Compare success, carrier assignments, makespan and concurrency (actions that may
   run in parallel) with today's output.
4. **Phase 2, built while planning.** For one stage (tray assignment, which already inserts by
   position), build prerequisites as events are added instead of from the finished graph. Compare
   as in 2 and 3. This tests the hard part: deriving dependencies before the final graph exists.
5. **Write-up.** Go/no-go, the `OrderedPlan` / prerequisites / `ReplayPlan` / checked edits API,
   how AGV assignment computes its frontier and writes its order back, the migration order by
   stage, and replay cost measured (time per plan, inserts, geometry and path-search calls).

## Definition of Done

- The redundant-edge report names each consumer and whether it explains the TODO.
- Phase 1 runs over every scenario file, plus these, which must be present:
  `InsertJob.StallBlockedByAgvParkedThereByEarlierMoves`, `InsertJob.StallBlockedByAgvOnCharger`,
  `InsertJob.StallBlockedByAgvWithLaterMove`, the SW2-1190 explicit-destination eviction
  (its test on initial state `5675_pecos_combined/tray_at_p23_agvs_at_c14_and_w8`, once merged), `OrderLiftsAroundBayTransitions`, the bay-transition vs
  approach case from PR #1036, and a new scenario with an enabled AGV blocking a corridor
  mid-route (`OrderAgvMoveAfterBlockerDeparture`), recorded on main first.
- Each missing or extra ordering is explained or attributed to a rule.
- Phase 2 results for tray assignment are reported the same way.
- Replay cost is measured on the largest scenario layout (`5675_pecos_combined`).
- No change to planning output: `SCHEDULER_CHECK_RECORDINGS=1 poe test-pkg scheduler` passes with
  every recording identical.
- Write-up in the ticket's notes folder, reviewed with the team before any production ticket.

## Out of scope

- Replacing `ScheduleEventDag` in the planning path: follow-up tickets, one stage each, after the
  go decision.
- Joint carrier choice and relocation (an evicted AGV chosen as carrier makes a pointless trip).
- Re-resolving an AGV's later move after eviction instead of refusing to evict it.
- Changes to Chugg, the executor or the action-graph message format.

## Review

The write-up and the comparison output are the deliverables. The comparison code is reviewed
for correctness of the rules, not merged into the planning path.
