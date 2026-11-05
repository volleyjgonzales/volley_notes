# Codex review 18 (2026-11-01) and its evaluation

Codex read the tip `50b1b722` (source only). Checked here (item 256). Applied in item 257: items 1-3.

| # | Finding | Check | Verdict |
|---|---|---|---|
| 1 | `AssignAgvs` throws when the AGV order DAG has no topological order; it returns `stdx::Result` otherwise. | Confirmed (`agv_assignment.cpp:140`). `Dag::AddDependency` does not reject cycles, so AGVs blocking each other's pickups (A against B's tray, B against A's) give a cycle; nothing in `Plan()` catches, so the node would crash. Not reproduced. `BuildAgvOrderDag`'s two throws are bookkeeping: one vertex per AGV, and `FindAssignedAgvsBlockingPickup` lists each AGV once, so neither a missing vertex nor a duplicate edge can happen. | Agree: `stdx::Unexpected("Failed to assign AGVs: the assigned AGVs block each other's pickups")`; the two `BuildAgvOrderDag` throws stay. Commit 4, a fix with a bullet. |
| 2 | Retrieve and repark log the replay failure at ERROR, then `MakeFailedJob` logs it at WARN; the other 11 expansions only return it. | Confirmed (`job_expansion.cpp:173`, `:258`). Removing them drops two ERROR lines for a failure that means a bug; the WARN still carries the full text, and the response too. | Agree: remove both, in commit 4, where item 255 gave them the shared text. |
| 3 | Charger search names and constness: `best_cost`, `best_charger`, non-const locals, the `travel_duration` copy. | Confirmed. `best_charger`/`best_cost` come from main, inline in `ExpandAgvChargeJob` until commit 3 extracts the function. | Agree: `shortest_travel_duration`, `charger_pose_with_shortest_travel` (mirrors the function's name), in commit 1; `const` locals and no `travel_duration` copy in commit 3, where the function took its shape. |
| - | No further helper around the `Expected` checks. | | Agree. |
