# Codex review 3 (2026-10-30) and its evaluation

Codex read the tip `5c764d8c` (before its findings were applied; source only). Seven findings on the heading policy and the action
graph, all confirmed here by reading.

| # | Finding | Check | Verdict |
|---|---|---|---|
| 1 | In ExpandAgvMoveJob `dest` is the requested AGV pose and then, for a carried tray, becomes the tray's pose (reversed when the tray sits reversed). The reversal is needed: TrayMove::ApplyTo (schedule_events.cpp 222-228) converts the tray destination back to the AGV heading with the tray/AGV offset. Name the two poses apart. | Confirmed. | Agree, behaviour-neutral: `const auto tray_dest = IsTrayReversedOnAgv(agv, tray) ? ReversePoseHeading(dest) : dest;` and use it for the preference and the move. Lands in commit 9, where the branch got its shape. |
| 2 | Heading precedence is unclear: ExpandReparkTrayJob applies ApplyReparkHeadingPreference only when `is_reciprocal_heading_allowed`, validates the destination (CheckReparkDestination), then calls ApplyPreferredHeading regardless of the flag, which can override a requested heading for a loaded tray after validation; ExpandAgvMoveJob applies the preference to a carried tray regardless of its flag. | Confirmed control flow. Pre-existing; the fix commit did not change it. ApplyRetrievalHeading checks the node's allowed headings but not the keep-out filter of the pose it chooses, so a heading changed after validation is checked less than the requested one. | A contract decision, not a refactor: is a requested heading authoritative, and when does the retrieval preference apply? Changing the order changes plans wherever the preference fires. Proposal: a ticket that defines the precedence (requested heading, AGV/tray conversion, optional parking preference), resolves the destination once before validating it, and re-records what moves. A cheap experiment first: move ApplyPreferredHeading before CheckReparkDestination and run the recording comparison; if nothing changes, that part can land now. |
| 3a | ApplyPreferredHeading now only delegates to ApplyRetrievalHeading (tray_assignment.cpp 38-41). | Confirmed; commit 13 made it a pure delegate. | Agree: delete the wrapper, its three callers call ApplyRetrievalHeading. Amend into commit 13 (the tip). |
| 3b | ExpandAgvMoveJob's `is_reciprocal_heading_allowed` is false at both callers (scheduler.cpp 218, job_expansion.cpp 615); the unloaded reciprocal branch is unused. | Confirmed; no test calls the method; the job message's `allow_reciprocal` reaches only ExpandReparkTrayJob. | Agree: delete the parameter and the branch. Commit 10's fix of that branch then has nothing to fix; its bullet goes. Done as a commit of its own rather than folded into commit 5: the branch has three different shapes across commits 5, 9 and 10, so a pattern fold-in is not worth the risk. |
| 4 | ToActionNode returns nullptr for five outcomes (no delta, deserialisation failure, event type mismatch, unsupported charger state, unknown delta type) and the caller reports one generic failure; the lift branch uses throwing `std::get` for the location. | Confirmed (action_graph.cpp 52-146). | Agree: return `stdx::Expected<interfaces::msg::ActionNode>` with one message per outcome, `std::get_if` for the lift pose, `const ScheduleEvent&` for the event, and let the caller make the shared pointer. The generic failure text is replaced by the specific one; no recorded scenario reaches a failure. One commit with item 6. |
| 5 | ToActionNode dispatches on serialised type strings and also downcasts the event for bay commands. | Confirmed. | Keep the five-way dispatch, as Codex also concludes; the typed-variant rewrite would add a parallel hierarchy for one function. Covered by item 4's per-branch validation. |
| 6 | CollectAndCollapseTrajectoryMotions, BuildActionDagFromMotions and TransferEventDagDepsToActionDag return `std::optional<std::string>` where a value means failure; the caller adapts to `stdx::Expected`. | Confirmed (149, 188, 235; BuildActionGraph wraps each). | Agree: `stdx::Result` for the three, the caller propagates. Same commit as item 4. |
| 7 | MotionScheduleOrder orders by start time, action id, then hash; two distinct motions with equal start, action id and colliding hashes compare equivalent and `std::set` drops one (action_graph.cpp 39-49). | Confirmed as written; no collision reproduced. | Latent defect: replace the hash with a structural tie-breaker (end time, collision id, location) so equal keys mean equal motions, or collect into a vector with a stable sort and no silent dedupe. Which of the two depends on whether duplicates are expected across trajectories; the recording comparison decides. Fix-commit material. |

Also: the rollback in Plan() copies the DAG and the maps but shares the event objects, which is
sound because expansion never mutates an existing event (tray assignment does, later, on its own
copies of the context's state). Worth one line at the restore so it stays that way.

## Proposed work

1. Amend commit 13: delete ApplyPreferredHeading (3a).
2. Fold into commit 9: `tray_dest` in ExpandAgvMoveJob (1); into commit 10: the comparator (7),
   recording-guarded, and the one-line rollback note.
3. Commit 14: delete ExpandAgvMoveJob's reciprocal parameter and branch (3b), message 10 loses its
   bullet.
4. Commit 15: action graph error handling, `stdx::Expected` from ToActionNode and `stdx::Result`
   from its three siblings (4, 5, 6).
5. Item 2: the precedence experiment now (recordings decide), the contract as a ticket.
