# PR text (paste into GitHub)

Same form as the other PRs (`# What`, `# Why`, `# Testing`, a `Refs:` line; one line per paragraph and per
bullet). Rewritten 2026-11-06 at about a third of the previous length, after a look at the body lengths of
the last twelve PRs (100 to 600 words); the earlier, denser text is kept in `pr_description_dense_2026-11-06.md`.
Draft PR #1036 (https://github.com/VolleyAutomation/volley/pull/1036). The figure is added once approved.


Title: `[SW2-905] Keep tray destinations clear of parked AGVs`

---

# What

The stall search of tray assignment ignored every AGV, so an insert could be sent to the one free stall while an idle AGV charged 0.6 m from it. Validation then rejected the plan, every job of the request failed, and the dispatcher dropped the insert with the car already shut in the bay.

<img width="2382" height="1540" alt="06_pr_scenario_and_plan_light" src="https://github.com/user-attachments/assets/35188eab-ebbf-4ebf-8bbc-281aeace7df9" />

Three commits:

1. **Test viewer.** Steps of a solution are selected by clicking a row or a graph node, with a scrubber and the arrow keys; the details are split into tabs, with a timeline that lays the schedule out in time, one row per agent. Tooling only; it helped review the recordings.
2. **Scenarios.** Seven insert scenarios on the busy Pecos garage with its two AGVs (AGV 1 in the way, AGV 2 the carrier), recorded with the behaviour the next commit implements, plus a control and a simulation scenario for `sim.launch.py`.
3. **Fix.** `ResolveBlockingTrays` treats every parked AGV's pose as a place a tray may drive through but must not be lowered on. When that leaves only a waypoint stash, the scheduler moves the AGV instead: it finds the stall the AGV blocks, sends the AGV to the nearest free charger whose placement keeps the tray's route open, and parks the tray on the stall. The AGV move is a root of the event DAG, so the carrier's approach to the bay runs in parallel and only the loaded leg waits. A disabled AGV, or one carrying a tray, is never moved; with no usable charger the stash stays.

Behaviour changes outside the bug: `TrayAssignment.FillsBlankDestination` (sunrise) now parks tray 1 on P2062 instead of P2066, where the garage's only AGV stands idle, since the carrier is not known at that stage. Every other recording is unchanged.

Not in this PR: the unassignable-AGV list of #1031. Once that PR lands, AGVs on the list must be excluded from eviction as they are from carrier choice and hiding, while staying obstacles for occupancy and collision checks; that is one condition in the eviction's candidate loop, carried by whichever PR merges second, so low-battery AGVs recovering on a charger will then stay put and the insert will stash. Also deferred: moving a loaded AGV as a tray move, a hiding pose as a second choice when no charger is free, and scenarios for two AGVs blocking one stall or an eviction combined with a blocking-tray repark (no layout in the set produces those states).

# Why

An AGV charging beside the only free stall took the garage down: the insert could not plan, the bay stayed closed with the patron's car inside, and recovery meant faulting the bay and restarting the dispatcher. The stall search and validation now agree about AGVs, and when the only free stall is the one an idle AGV blocks, the AGV moves.

# Testing

- [x] `scheduler` and `scheduler_advanced_tests` build with 0 warnings; `prek` passes; `clang-tidy` on the changed lines: 0 findings
- [x] `scheduler` 202 tests (194 on main), `planner_core` 24, `scheduler_advanced_tests` 15; `SCHEDULER_CHECK_RECORDINGS=1` shows only the recordings named above
- [x] Three independent Codex reviews and Greptile's loaded-AGV finding; all fixed in these commits
- [x] The simulation scenario (`5675_pecos_sandbox_combined_insert_blocked_by_agv_on_charger`) watched in Foxglove

Refs: SW2-905
