# PR text (paste into GitHub)

Same form as the other PRs (`# What`, `# Why`, `# Testing`, a `Refs:` line; one line per paragraph and per
bullet). Rewritten 2026-11-06 at about a third of the previous length; the earlier, denser text is kept in
`pr_description_dense_2026-11-06.md`. PR #1036 (https://github.com/VolleyAutomation/volley/pull/1036).

Synced 2026-11-08 from the live PR body (Jon's edits after the viewer moved to #1043). The overlap wording and Testing
parentheses were applied to the live body the same day.


Title: `[SW2-905] Keep tray destinations clear of parked AGVs`

---

# What

The stall search of tray assignment ignored every AGV, so an insert could be sent to the one free stall while an idle AGV charged 0.6 m from it. Validation then rejected the plan, every job of the request failed, and the dispatcher dropped the insert with the car already shut in the bay.

<img width="2382" height="1540" alt="06_pr_scenario_and_plan_light" src="https://github.com/user-attachments/assets/35188eab-ebbf-4ebf-8bbc-281aeace7df9" />

Two commits:

1. **Scenarios.** Nine insert scenarios on the busy Pecos garage with its two AGVs (AGV 1 in the way, AGV 2 the carrier), recorded with the behaviour the next commit implements, plus a control and a simulation scenario for `sim.launch.py`.
2. **Fix.** `ResolveBlockingTrays` lets a tray drive past a parked AGV but never lowers it where it would overlap one. When that leaves only a waypoint stash, the scheduler moves the AGV instead: it finds the stall the AGV blocks, sends the AGV to the nearest free charger whose placement keeps the tray's route open, and parks the tray on the stall. The AGV move waits only for that AGV's earlier planned events and precedes the dependent tray moves, so the carrier's approach to the bay may overlap it and only the loaded leg waits. When the eviction is not possible the stash stays and one INFO line in central's log says why. A disabled AGV, or one carrying a tray, is never moved; with no usable charger the stash stays.

The test viewer changes that helped review the recordings are now in #1043.

Behaviour changes outside the bug: `TrayAssignment.FillsBlankDestination` (sunrise) now parks tray 1 on P2062 instead of P2066, where the garage's only AGV stands idle, since the carrier is not known at that stage. Every other recording is unchanged.

Not in this PR: the unassignable-AGV list of #1031 (AGVs with very low battery that dispatch has sent to charge). With #1031, the scheduler never picks those AGVs to carry a tray and never parks them under trays during Clean. Once both PRs are on main, it must also never move them off a stall to make room, while still treating them as obstacles in occupancy and collision checks. That takes one extra condition in the loop that picks which parked AGVs to move (`ResolveByEvictingAgvs`), added by whichever PR merges second. A low-battery AGV charging next to the free stall will then stay put, and the insert will park its tray on a waypoint instead, as it did before this PR.

Also deferred:
- Moving an AGV that is carrying a tray off the stall. It would have to be planned as a tray move, not an AGV move, so for now such an AGV is never moved.
- When no charger is free, parking the blocking AGV under a tray (a hiding spot) before falling back to the waypoint.
- Scenarios with two AGVs blocking one stall, or with an AGV moved off a stall while a tray in the way is also reparked. No layout in the scenario set produces those states.

# Why

An AGV charging beside the only free stall took the garage down: the insert could not plan, the bay stayed closed with the patron's car inside, and recovery meant faulting the bay and restarting the dispatcher. The stall search and validation now agree about AGVs, and when the only free stall is the one an idle AGV blocks, the AGV moves.

# Testing

- [x] `scheduler` and `scheduler_advanced_tests` build with 0 warnings; `prek` passes; `clang-tidy` on the changed lines: 0 findings
- [x] `scheduler` 204 tests (194 on main), `planner_core` 24, `scheduler_advanced_tests` 15; `SCHEDULER_CHECK_RECORDINGS=1` shows only the recordings named above
- [x] Three independent Codex reviews and Greptile's loaded-AGV finding; all fixed in these commits
- [x] The simulation scenario (`5675_pecos_sandbox_combined_insert_blocked_by_agv_on_charger`) watched in Foxglove
- [x] Tested in garage. (Need to discuss optimal policy, the evicted agv goes to a charger, but then may be immediately assigned a job to move a tray into the bay)

Refs: SW2-905

[SW2-905]: https://volleyautomation.atlassian.net/browse/SW2-905?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ






