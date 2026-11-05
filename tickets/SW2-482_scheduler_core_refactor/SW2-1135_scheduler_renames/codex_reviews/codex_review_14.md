# Codex review 14 (2026-10-31) and its evaluation

Codex read the tip `72599b1f` and reviewed `motion_planner`'s `static_graph_filtering.{hpp,cpp}`
(GraphFilterProperties, BuildStaticObstacleFilter(s), BuildKeepOutFilters). Checked here; nothing
changed (item 242).
Applied in item 243: the commit-2 subset, with the scheduler's names; tip `d9082d54`. The extraction,
`BlockedGraphLocations` and `IgnoredObstacles` wait for their own PR.

Context: commit 2 already renamed these functions (`GetStaticFilter`, `GetAllStaticFilters`,
`GetDisabledEntitiesFilters`). Callers: scheduler (7), motion_planner (`chugg_common.cpp`,
`agv_hiding_search.cpp`), tests (`static_graph_filtering_tests` 10 cases, `blocking_tray_search_tests`,
`agv_hiding_search_tests`, scheduler `sanity_check_tests`). `CollisionEntityId`: BAY_ODP 0, TRAY_LEGS 1,
TRAY 2, AGV 3, PAYLOAD 4 and up.

| # | Finding | Check | Verdict | Where |
|---|---|---|---|---|
| 1 | `AddProperty` overwrites a bool: `SetEnabled`; `vfilter`/`efilter`. | Confirmed; two callers (`chugg_common.cpp:95,98`). | Agree: `SetEnabled(vertex, is_enabled)` / `(edge, is_enabled)`, `vertex_filter`/`edge_filter`. | commit 2 |
| 2 | `disabled_poses`/`disabled_edges` also hold occupied and oversize locations; a `BlockedGraphLocations` struct. | Confirmed: obstacles, disabled-node volumes and oversize poses all land there. | Rename to `blocked_poses`/`blocked_edges` (locals and the constructor's parameters): agree, commit 2. The struct: with the extraction (#3). | 2 / later |
| 3 | Extract `CollectDisabledNodeIds`, `CollectObstacleExclusions`, `CollectDisabledNodeExclusions`, `CollectOversizeExclusions`. | Boundaries real; the invariant holds (a disabled object's node is collected before the ignore check, lines 57-63, 78-84, 102-108). | Agree in substance, not in this PR: restructuring the filter every motion search depends on is a motion_planner change of its own. | separate PR |
| 4 | Names: `gg`, `dgs`, `ctable`; `collision_id` vs `other_collision_id`; `adjust_collision_id`; `bay_head`; `max_win_idx`; `disabled_entity_collision_id`; `collision_id_filters`; collision id by value. | Confirmed. Same kind as the renames already in commit 2. | Agree: `graph`, `state`, `collision_table`, `moving_collision_id`, `obstacle_collision_id`, `effective_moving_collision_id`, `bay_inbound_heading`, `max_resource_size_index`, `disabled_node_collision_id`, `filter_by_collision_id` (matches `keep_out_filter_by_footprint`); also `head` to `heading`, `e_opt`/`v_opt`, `curr_tray_*`. By value: callers unchanged. | commit 2 |
| 5 | `collision_id >= AGV` substitutes TRAY for AGV too, the comment names payloads only; "all possible orientations" iterates the node's configured headings. | Confirmed: AGV is 3, so a moving AGV is checked against an AGV obstacle with the TRAY footprint (conservative; maybe deliberate, an AGV may carry a tray); `garage_node.headings` are the configured ones. | Agree: comments say what the code does, conditions unchanged. Question for a ticket: is AGV-against-AGV meant to use TRAY? | commit 2 + ticket |
| 6 | `BuildStaticObstacleFilters` builds AGV, TRAY, then one per tray footprint in the state; a local `add_filter_if_missing`; `try_emplace` evaluates its argument. | Confirmed. | Contract in the header comment now (commit 2); the helper with the extraction. | 2 / later |
| 7 | Three same-typed ignore sets: an `IgnoredObstacles` struct; `.contains()`; the BuildKeepOutFilters comment says "or" where the code requires both. | Confirmed: "ignore all entities that are not disabled or are not on disabled nodes" vs `!on_disabled_node && !disabled`. | Comment fix and `.contains()`: commit 2. The struct changes about 25 call sites in two packages and touches C1's signatures (BuildImmobileTrayFilter): later, with the extraction. | 2 / later |
| 8 | `// ffs`, the commented-out WARNS block, "Ignore any moving …", loop announcements; header includes; `BayReportMsg`; angle brackets. | Confirmed. The header also lacks `<set>` (used in the .cpp) and the .cpp `<stdexcept>`, `<string>`. | Agree: commit 2 (its "message headers per file" theme covers `interfaces::msg::BayReport`). Keep the tray-leg and disabled-node volume rationale. | commit 2 |
| - | Keep exceptions; `Expected` would be a separate API change. | Agree. | - | - |

## Proposal

- Now, in commit 2 (behaviour-neutral, two files plus `chugg_common.cpp`): #1, #2 renames, #4, #5 and
  #6 comments, #7 comment and `.contains()`, #8. Recordings and the ten filter tests must not change.
- Later, own ticket and PR in motion_planner: #3 extraction with `BlockedGraphLocations`,
  `add_filter_if_missing`, `IgnoredObstacles`. Do it after C1 settles `GarageServices` and the
  tray-assignment signatures, or fold `IgnoredObstacles` into C1's signatures.
- Ticket question: AGV against AGV checked with the TRAY footprint.
