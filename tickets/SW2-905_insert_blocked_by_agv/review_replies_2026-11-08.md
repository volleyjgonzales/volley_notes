# PR #1036 review replies, drafted 2026-11-08

**Posted 2026-11-08 at Jon's explicit request** (as Jon's account): Greptile
https://github.com/VolleyAutomation/volley/pull/1036#discussion_r4508944733, Jesse logging
#discussion_r4508944859, Jesse VECS #discussion_r4508944933, Jesse test constants #discussion_r4508945065,
top-level comment #issuecomment-6730790952; PR body edited (overlap wording, Testing parentheses).
The VECS reply went up in the simpler form below, not the original paragraph.

Assessment: `SW2-905_notes.md`, section 12, entries of 2026-11-08. Checked against the pushed branch on
2026-11-08: tests `a90f42da`, fix `55a5877a`. 

## Greptile, "Eviction runs before earlier moves" (tray_assignment.cpp:464)

> Right. The insert's eviction moves were added to the DAG without chaining them after the AGV's earlier
> planned moves; roots are applied in job order, so with two MOVE_AGV jobs for the same AGV ahead of the
> insert the eviction ran between them and the second move failed its start-pose check. Fixed: eviction
> moves are chained after the AGV's last planned event, and an AGV with moves later in the plan is not
> evicted (it would start those from the stall it left). Two recorded scenarios cover it:
> `StallBlockedByAgvParkedThereByEarlierMoves` (AGV 1 brought to C14 by two MOVE_AGV jobs in the same
> request as the insert, then evicted after the second) and `StallBlockedByAgvWithLaterMove` (AGV 1 has a
> later move, so the car is stashed on W31 and the move keeps its destination).

## Jesse, log eviction failures before returning nullopt (tray_assignment.cpp:636)

> Agreed. The eviction search now returns why it gave up (no stall even one that overlaps a parked AGV, no
> eligible AGV to relocate, no reachable free charger, or no charger relocation that permits the tray plan),
> and the fallback logs one INFO line, "tray {} remains stashed on {}: {reason}", once per tray rather than
> per candidate, so a car on a waypoint next to an open stall is explained in central's log.

## Jesse, VECS charge path and blocking-tray reparks (tray_assignment.cpp:572)

> This is about VECS stalls (car charging) in charge jobs, not AGV chargers.
>
> Yes, intentional. SW2-905 is about inserts, so only the insert gets the AGV relocation. The charge job and
> blocking-tray reparks only get the new "don't park a tray overlapping a parked AGV" rule.
>
> For charging, that doesn't make things worse. If another VECS is free, the job uses it. If the blocked
> VECS is the only one, the job now fails during planning; on main it picked that VECS anyway and failed
> validation, the same bug as the insert.
>
> Relocating an AGV off a VECS is a bigger change: the charge job picks its VECS during job expansion,
> before tray assignment runs, so expansion would have to add the AGV move and keep the ready-to-charge and
> ordering checks. I'd like to do that as a separate ticket, with a test on a layout that has VECS (Pecos has
> none).

## Jesse, Pecos constants in the test helpers (insert_job_tests.cpp:143)

> Good point. The expectation structs now carry the chargers, the bay and the stash node, so the helpers
> have no Pecos constants left.

## Top-level comment after the force push

> Pushed the review fixes as the same two commits (tests `a90f42da`, fix `55a5877a`). Besides the threads
> above: the eviction helpers and the request flag are renamed (`ResolveRequest::is_parked_agv_overlap_allowed`,
> `PlanAgvEvictionsToChargers`, `AreTrayMovesReachable`), the failure messages name trays and AGVs in full,
> and `GetTopologicalOrdering` breaks ties among ready events by creation order. The SW2-1190 commit
> (explicit destinations of move tray jobs) moved to its own branch and gets its own PR after this one.

## PR body

Done: the sentence on the AGV move ("waits only for that AGV's earlier planned events…") is in the live
body. Applied 2026-11-08 as well (the flag was renamed because the rule is about overlap, not the same pose):
in item 2, replace "treats every parked AGV's pose as a place a tray may drive through but must not be
lowered on" with "lets a tray drive past a parked AGV but never lowers it where it would overlap one".
Also in Testing: a stray ")" after "watched in Foxglove", and the garage-test note opens "(" without
closing it. The local copy is `pr_description.md`.

## Checklist before posting
- Code is pushed (tests `a90f42da`, fix `55a5877a`).
- CI on #1036: the run on `55a5877a` lost its build runner (shutdown signal mid `colcon build`); failed jobs
  rerun on 2026-11-08, result pending (`gh pr checks 1036`).
- #1043 still shows `unit-tests` failing for task_planner and vecs from run 42310032195 (2026-11-06).

## Note for the Greptile reply, if asked why `event_dag.cpp` changed

> Recording the earlier-moves scenario showed validation replaying the carrier's approach before the insert's
> bay transition, which the extra jobs' pops had reordered in the heap; the bay's inbound pose is blocked
> until the transition, so the plan failed. Among ready events, those of one job now replay in creation
> order (expansion before assignment). No existing recording changes.

## Follow-up reply on Jesse's VECS thread (posted 2026-11-08, #discussion_r4508969671)

Ticket created 2026-11-08: SW2-1192, "Move a parked AGV off the only free VECS for a charge payload job"
(epic SW2-1067, Relates SW2-905). Reply to #discussion_r4508944933:

> Tracked as [SW2-1192](https://volleyautomation.atlassian.net/browse/SW2-1192): move a parked AGV off the only free VECS for a charge payload job, tested on Gramercy's VECS layout.
