# PR text (paste into GitHub)

Same form as PRs #1007 and #1018 (`# What`, `# Why`, `# Testing`, a `Refs:` line; one line per paragraph
and per bullet, since GitHub renders a newline as a line break). Rewritten 2026-11-05 for the three
commits the user asked for (viewer, tests, solution), after Codex reviews 1 and 2; draft PR #1036
(https://github.com/VolleyAutomation/volley/pull/1036).

Title: `[SW2-905] Keep tray destinations clear of parked AGVs`

---

# What

Three commits: the test viewer, the scenarios that record the expected behaviour, and the solution.

1. **Test viewer** (`feat(scheduler)`). A step is selected by clicking its table row or DAG node, by a scrubber or by the arrow keys, and stays selected; the details under the figure are split into test, input, output and graph tabs; a failed plan gets a banner with its message; the URL hash names the scenario and the step and selects the initial state when it names none; an AGV that moves is drawn in the shade of its own path, as are its ghost and the selected step's stretch; a timeline tab lays the schedule out in time, one row per agent and one column per second, with captions on how to read it and the schedule. It rode along because I am its only user and it helped review the recordings. `poe scheduler-test-viewer` as before.
2. **Scenarios** (`test(scheduler)`). Six insert scenarios on the busy Pecos garage with the site's two AGVs (AGV 1 the one in the way, AGV 2 the carrier), where the only free stall is beside a charger (P15 next to C14 in five of them, P5 next to C10 in the route one). `StallBlockedByAgvOnCharger` puts AGV 1 on charger C14, 0.6 m from P15: before the fix the plan failed the pre-motion sanity check (`Requested to move to 15@90 but it's occupied`), the response succeeded with the job in error, and the dispatcher dropped the insert with the car shut in the bay; the recording now shows AGV 1 sent to another charger and the car parked on P15, and the test checks the dependency edges from the eviction to the loaded move and the job of the eviction's actions, not the order of the array. `StallBlockedByAgvEvictedAwayFromRoute`: the nearest charger would close the tray's only route, so the next one is taken. `StallBlockedByAgvNoFreeCharger` (the other chargers disabled), `StallBlockedByAgvChargersUnreachable` (the way to them disabled) and `StallBlockedByDisabledAgvOnCharger`: the stash on W31 as the last resort. A simulation scenario, `5675_pecos_sandbox_combined_insert_blocked_by_agv_on_charger.yaml`, sets up the same garage for `ros2 launch launcher sim.launch.py` (dispatcher in MANUAL so its start-up clean-garage job does not move AGV 1; a manual transition readies B7; a patron arrives at 45 s). `FromBay7StallFree` is the control with C14 enabled and empty: the car parks on P15. The older busy-garage states disable C14, which is why their inserts stash the car on W31; the `ExpectInsert` comment blamed the retrieval-heading rule, which caches no heading on this layout, and is corrected. This commit is red on its own: the first four scenarios need the next commit.
3. **Solution** (`fix(scheduler)`). The stall search of tray assignment ignored every AGV. `ResolveBlockingTrays` now adds every enabled AGV's pose, except the one under the root tray, to the search's illegal poses for every caller: a tray may still drive through an AGV's pose, since the AGV can move, but is not lowered where it would overlap one. When that leaves only a waypoint stash, `ResolveByEvictingAgvs` reruns the search without the AGV poses to find the stall it would have taken, asks the collision table which idle AGVs overlap it, and sends each to a free charger: chargers ranked by travel time, those whose occupant would overlap the stall skipped, and a placement kept only if the plan it leads to is feasible under validation's own filter, each blocking-tray move and then the root move. The AGV moves join the DAG before every tray move of the plan; they are roots, so AGV assignment schedules them like a charge job's move and the carrier's approach to the bay runs in parallel, only the loaded leg waits. A disabled AGV is never moved; with no feasible placement the stash stays. Tray assignment's working state now applies AGV moves as well as bay and VECS transitions, so the search sees the AGV poses validation replays; `AssignTrays` dispatches on the event type (which also shows that VRC transitions are skipped), `RecordTransitionOccupancy` only records occupancy, and the apply-to-working-state blocks share one `ApplyToWorkingState` helper, a stand-in until SW2-1170 makes `ApplyTo` return `stdx::Result`.

### Behaviour changes

- A stall whose footprint overlaps an idle AGV is no longer chosen for a tray. When that leaves no stall, the AGV is sent to a free charger that keeps the tray's route open and the tray takes the stall: in the reproduction AGV 1 goes from C14 to C16 and the car parks on P15. With no free charger, none reachable, or a disabled AGV, the car is stashed on W31 as the scheduler already does when C14 is disabled.
- `TrayAssignment.FillsBlankDestination` (275_sunrise_b, tray 1 next to the garage's only AGV, which stands idle on P2066) now sends the tray to P2062 instead of P2066. The old choice worked only because that AGV became the carrier; the carrier is not known at this stage, so an AGV's own stall is skipped even when the AGV would have carried the tray. The cost is a farther stall in a one-AGV garage. The same assumption is made the other way in the eviction's route check: the AGV standing under the tray counts as its carrier.
- Every other recording is unchanged.

### Not in this PR

- Honouring PR #1031's unassignable-AGV list (SW2-1164, not merged yet) in the eviction: a very-low-battery AGV must not be pulled off its charger. One line once that PR lands.
- A hiding pose under an empty tray as the eviction's second choice when no charger is free; the case where the blocking AGV is the only enabled one, which is evicted and then carries the tray, one needless move.
- Scenarios for two AGVs blocking one stall and for an eviction combined with a blocking-tray repark: no layout in the scenario set produces either state (an AGV on P15 and one on C14 would overlap each other). The eviction searches over every blocking AGV and checks the whole plan, but those paths have no recording.
- Re-queueing a failed insert in the dispatcher: PR #1031 does it while a low-battery AGV charges.

# Why

An AGV charging beside the only free stall took the whole garage down: the insert could not plan, the bay stayed closed with the patron's car inside, and recovery meant faulting the bay and restarting the dispatcher. The stall search and validation disagreed about AGVs; now they agree, and when the only free stall is the one an idle AGV blocks, the AGV moves.

# Testing

- [x] `scheduler` and `scheduler_advanced_tests` build with 0 warnings; `prek` passes; `clang-tidy` on the changed lines: 0 findings
- [x] `scheduler` 201 tests (194 on main, seven new), `planner_core` 24, `scheduler_advanced_tests` 15
- [x] `SCHEDULER_CHECK_RECORDINGS=1`: every recording identical except `FillsBlankDestination` (re-recorded); the six insert scenarios are new recordings, and `TrayAssignment.KeepsDestinationsOffParkedAgvs` is a new unrecorded stage test
- [x] `poe scheduler-test-viewer` renders; the step selection, scrubber, keys, tabs and hash checked in a browser
- [x] Two independent Codex reviews; their findings (a route an eviction could close, exclusions missing from two resolver callers, an ordering test that checked array order) are fixed in these commits

Refs: SW2-905
