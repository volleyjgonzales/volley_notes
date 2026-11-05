# Codex review 1 (2026-10-30) and its evaluation

Codex read the branch at `270fcb24` (the tip before its findings were applied) with
`codex_review_prompt.md`. It did a source-level
readability review only: no build, no tests, no recording comparison, no tidy, and it says so. The
behaviour-neutrality audit (prompt objectives 1, 2, 5, 7, 8) is therefore still outstanding.

| # | Codex finding | Check | Verdict |
|---|---|---|---|
| 1 | `AssignTrays` keeps two kinds of pending move in `required_moves` (already applied advance moves, and moves still to apply), and a second map `applied_move_sources` tells the emission loop which is which (tray_assignment.cpp 566-568, 617-630, 661-664). Introduced by the fix commit. Proposal: one record per planned move with an optional already-applied source pose. | Confirmed by reading: advance moves are applied when chosen (617-630) and recorded in the map; the emission loop at 663 skips `ApplyTo` for them and uses the recorded source. | Agree. Do it now, in the fix commit: replace the `TrayMovesWithPaths` pair with a `PlannedTrayMove {move, path, std::optional<GaragePose> applied_from}` (the struct PROMPT C1-4 plans anyway), drop the map. Small: the two loops over `required_moves` and `ResolveBlockingTrays`' return. |
| 2 | `occupant_by_node` (AgvAssignmentState) reads as current occupancy but is never cleared on departure; `OrderArrivalAfterPriorOccupant` uses it as "the AGV last placed at this node" (agv_assignment.cpp 108-119, 522). Proposal: `last_occupant_by_node`. | Confirmed: written at 522 (initial poses) and 119 (arrivals), no erase. The doc line already says "lets an arrival depend on the prior occupant's last event". | Agree. Rename in commit 5, where the field was named (`current_node_occupant` on main, `occupant_by_node` on the branch). |
| 3 | `AssignTrays` is still about 275 lines of path search, blocker selection, fallback advance, emission, dependencies and rescanning; extract one coherent operation (resolving a blocker with its fallbacks) later, not arbitrary chunks. | Agree, and already planned: PROMPT C1-5 (`CheckDestinationUsable`, `FindCriticalPath`, `BlockersOnPath`, `ChooseParkingSpot`) and C1-6 (`EmitMoveChain`, `CommitRootMove`). | Defer to the solver PR as planned. |

Also from Codex: keep the comments on blocked intermediate path nodes, draining non-tray roots
first, and the source bay's transition (all three survive the sweeps: tray_assignment.cpp 136 and
719, agv_assignment.cpp 527); give naming nits less weight than state-tracking issues. Greptile
pre-answers: "AssignTrays too complex" is a fair follow-up; "occupancy map is stale" is not a
defect (it keeps prior occupants for ordering); "advance move applied twice" would be wrong (the
loop skips entries in `applied_move_sources`). Its verdict: approve as an incremental refactor,
with the rename as a cheap improvement.

Evaluation: a useful second read of the hardest code, accurate on all three points, nothing
missed by the earlier review that it found and vice versa, except that it names the
two-container state as the first thing to fix, which the earlier review let stand. What it did
not do is the audit the prompt asked for; a second run limited to objectives 1 and 2, with the
recording comparison and tidy, is the gap.
