# Codex review 12 (2026-10-31) and its evaluation

Codex read the pushed tip `30b014aa`. Four findings; checked here; applied in item 239; tip `9bc62155`.

| # | Finding | Check | Verdict | Commit |
|---|---|---|---|---|
| 1 | Two `ApplyTo` results are discarded in job expansion: the clean-garage AGV move and the charge job's bay transition. | Confirmed; both states are used afterwards (the next AGV's move, `trapping_bay_opt`). A third: RunAgvPathRepairPass replays every event with `event->ApplyTo(working_state);` and ignores the result. | Agree, all three: the two expansions return `Fail(...)` (the expansion rollback restores the context); the repair pass returns its `stdx::Unexpected`. Planning behaviour changes only when an apply fails, which no recording reaches. | 4 |
| 2 | BuildAgvOrderDag keeps `optional<Vertex>` per AGV and checks them during dependency building. | Confirmed; `Add` only fails for a node already in the DAG, and every node is new. | Agree: check `Add` once and keep `vertex_by_agv` (plain vertices); the dependency loop keeps its AddDependency check. | 1 |
| 3 | ClassifyBay nests `else` after returns; `is_occupied_indefinitely` contradicts the prediction that follows. | Confirmed. | Agree: the payload-without-tray guard, then a `switch(state)` with one case per processing state (each: tray and payload, or NOT_USABLE), the two ready states and `default`; the boolean disappears. ClassifyBays' two bools become `const`. | 1 |
| 4 | The bay-split comment says "one bay stays insert-ready", which the calculation does not guarantee; `<algorithm>` is missing in bay_rebalancing.cpp. | Confirmed: a zero ratio, no eligible bays or no empty trays give zero. | Agree: "Round fractional targets up to favour insert readiness; empty-tray availability caps the result." (commit 1); `#include <algorithm>` in bay_rebalancing.cpp (commit 5, where the file is made). | 1, 5 |

The branch is pushed at `30b014aa`; folding these in rewrites all six commits again and needs another
force-push with lease.
