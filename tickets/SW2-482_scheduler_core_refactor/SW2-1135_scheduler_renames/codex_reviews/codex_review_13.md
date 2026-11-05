# Codex review 13 (2026-10-31) and its evaluation

Codex read the tip `9bc62155` and proposed decomposing `AssignTrays` into free functions in the
anonymous namespace of `tray_assignment.cpp`. The user asked whether it can be applied without
deviating from the goal of putting tray (and later AGV) assignment behind solver interfaces. Checked
here against the code and `PROMPT.md` (phase C1, sections 6.1 to 6.3); nothing changed (item 240).
Applied in item 241: the two small items, the C1 note in PROMPT.md, and a comment sweep the user asked
for; tip `72599b1f`.

## Finding: the decomposition is phase C1, already planned

| Codex's function | Code at the tip | Plan (PROMPT.md) |
|---|---|---|
| `FindRootTrayPath` | search and failure text, lines 88-101 | C1-5 `FindCriticalPath` (`critical_path.hpp`) |
| `BuildRootPathExclusions` | the loop of 127-135 (with the blocker list) | inside `FindCriticalPath` (vertices plus trays) |
| `FindTraysBlockingRemainingPath` | the re-scan of 275-293 | C1-5 `BlockersOnPath` |
| `IsTrayPoseBlocked` | the advance check of 171-183 | C1-5: `BlockersOnPath` on a one-vertex span |
| `RecordUnblockingMoves` | the emission loop of 231-268 | C1-6 `EmitMoveChain` (`EmitOptions`), alone in its commit |
| fallback block stays together | 153-212 | C1-5: "Fallback 1 stays inline" |
| don't merge the two emission loops yet | 231-268 and 437-466 | C1-6 merges them alone, behind options |

Codex's three cautions hold and match the plan: first-discovery order (vector plus set, both scans);
`applied_from` (the advance move is applied during the fallback, the loop must not apply it again);
the source-pose registration differs (generic `TRAY` id at line 264, the tray's own footprint at 462:
the plan's `EmitOptions::source_footprint`).

Where Codex differs from the plan, and why the plan wins for the solver goal:
- Placement. Anonymous namespace: not unit-testable, and C2's module test must link without
  `Scheduler`. The plan puts each function in `task_planning/tray_assignment/` with a test per function.
- Dependencies. Codex: pass the actual dependencies. Plan: `const GarageServices&` (C1-1). Either is
  free of `Scheduler&`; done now, C1 would change every signature again.
- Effectful emission. `RecordUnblockingMoves(PlanContext&, TrayAssignmentState&)` matches C1-6
  (DAG writes, file-local); in C2 it becomes a `Pass` method recording `NewMove`/`Edge`. Compatible.

Verdict: defer the extraction to C1 as planned. Doing it in SW2-1135 moves the same code twice
(anonymous namespace now, module later, with new parameters), adds logic restructuring to a PR
promised as renames, clean-ups and the split, and rewrites six pushed commits again.

## Small items that fit SW2-1135 now

| # | Item | Check | Verdict | Commit |
|---|---|---|---|---|
| 1 | `new_move_path` (main loop, line 224) is not a path. | Confirmed: built from the keys of `root_path_illegal_poses`, an `unordered_map`, so hash order; the blocker's last move is ordered after their prior occupants and registered as occupying them. | Agree: `root_path_poses`, with a one-line comment. The field `PlannedTrayMove::path` holds four different things (the search path, the advance's two poses, the root path's poses, empty from recursion); its contract goes to C1, where the struct moves to `blocking_trays.hpp`. | 1 |
| 2 | `utils.cpp` includes the aggregator `common_ros/common_ros_msgs.hpp`. | Confirmed: the scheduler's only remaining use; it pulls in 40 message headers. | Agree: replace with the headers it needs (commit 2's theme). Build check needed. | 2 |
| 3 | `Expected` versus `optional`; no `AllHaveValues` for mutations. | Matches PROMPT 6.5 and the code. | Nothing to do. | - |

## For the C1 plan (PROMPT.md, to refresh before C1 starts)

- Names: the code now says "root path" (`root_path_illegal_poses`, round 11), so `FindCriticalPath` /
  `CriticalPath` become `FindRootTrayPath` / `RootTrayPath`; `freeing_moves` is `occupancy_history`.
- C1-6: `check_apply` is moot (commit 4 made the main loop check its apply); the double apply (B2) is
  handled by `applied_from`, which `EmitMoveChain` must keep.
- Line numbers refer to the old `scheduler.cpp`; the code is in `tray_assignment.cpp` now.
- `IsTrayPoseBlocked` as `BlockersOnPath(...).empty()` on one vertex scans every tray instead of
  stopping at the first; same result.
- AGV assignment: nothing in this proposal touches it.
