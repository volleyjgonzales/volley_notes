# Watching `StallBlockedByAgvOnCharger` in simulation, with Foxglove

Written 2026-11-06 from `docs/architecture/sim.md`, `docs/guides/simulation.md`, `src/sim/src/scenario_runner.cpp`,
`src/sim/src/simulator.cpp`, `src/central/src/dispatch.cpp` and the notes repo's `garage/deploy_and_test.md`
(section 2) and `garage/troubleshooting_reference.md` (section 14). Run by the user in Foxglove on 2026-11-06.

## 1. The scenario file

`src/scenario/scenarios/5675_pecos_sandbox_combined_insert_blocked_by_agv_on_charger.yaml` (in the tests commit). It is the scheduler test's busy garage on the sandbox layout, which is
the combined layout without bay B21 and waypoint W41 (the other 26 nodes keep their ids):

- The site's two AGVs: AGV 1 idle on C14 at its inbound pose `14 @ -90`, AGV 2 under the empty tray at P5.
- An empty tray (27) waits in bay B7; cars (STANDARD, 5.182 m by 2.21 m) on P2, P3, P6, P17, P20, P23 and P24;
  P15 is the only stall without a tray.
- Events, by sim time: readiness ratio 0 (0 s); dispatcher mode MANUAL (0.5 s); start (1 s); a
  `transition_bay_to_insert` job for B7 (40 s); a `patron_arrival` for payload `…27` (45 s).

Why MANUAL. In AUTO the dispatcher's first act after creating its execution state is a clean-garage job
(`dispatch.cpp:962`), whose hiding search moves every AGV under a tray, AGV 1 included, before any patron can
arrive. In MANUAL nothing moves on its own; the bay is readied by the manual transition job
(`TransitionBayToInsertSrvCallback`, manual mode only) and the insert job is still created from the bay's
VEHICLE_INSERTED event (`CreateJobsFromEvents`, not mode-gated) and planned by the dispatcher's planner timer,
which runs in both modes (`dispatch_ros.cpp:142`, the "auto planner" services only pause it). The simulated
bay boots to READY_TO_RETRIEVE; with the tray already inside, the transition job only closes the doors. The
simulated bay confirms the insert itself (`simulator.auto_confirm_insert`, default true), so the patron drives
in, is vetted, the bay reports VEHICLE_INSERTED and the insert job is born.

What should happen: the plan of the recorded scenario. AGV 1 drives C14 → P15 → P17 → C16 while AGV 2 drives
P5 → W9 → W8 → W31 → B7 and lifts; the loaded leg B7 → W31 → W8 → W13 → P15 waits for AGV 1 to reach C16;
the car ends on P15. Before the fix the request fails validation ("Requested to move to 15@90 but it's
occupied") and the dispatcher drops the insert with the car in the closed bay.

## 2. Running it

The whole workspace must be built on the branch (the sim launches central, the bays and the simulator, not
only the planner), inside the devcontainer:

```bash
volley-in-container sh 'poe build'
```

Then, in a container shell (the sim is interactive, so not through the wrapper):

```bash
cd ~/volley && devc attach
source install/setup.zsh
ros2 launch launcher sim.launch.py scenario:=/home/jon-gonzales/volley/src/scenario/scenarios/5675_pecos_sandbox_combined_insert_blocked_by_agv_on_charger.yaml real_time_factor:=1 enable_dispatch_charging_mode:=false rviz:=false
```

- The absolute path is deliberate: a bare name is looked up in the installed `scenario` package, which only
  knows the file after a rebuild of that package (`sim_nodes.py:462`).
- `real_time_factor` 1 or 2 is watchable; 10 is the system tests' speed. `0` pauses.
- `rviz:=false` keeps the visualizer and the Foxglove bridge (both come with `vis`, on by default for manual
  runs) and skips the RViz window.
- `enable_dispatch_charging_mode:=false` keeps the dispatcher from queuing charge jobs on its own.
- Add `printdags:=true` to print the scheduler's DAGs to the terminal, and `record_artifacts:=true` to save
  an mcap under `artifacts/` that Foxglove can replay later.
- The launcher sets `ROS_DOMAIN_ID=75` unless one is set, so the sim does not mix with a real garage.

Stopping: Ctrl+C in that terminal (twice if it hangs); afterwards check for leftovers from a container shell:

```bash
ps aux | grep -E 'ros2|component_container|visualizer' | grep -v grep
```

## 3. Foxglove

1. The Foxglove desktop app on the laptop (`foxglove.dev/download`; the web app may refuse a plain `ws://`
   connection). Sign in to the Volley organization for the shared layouts.
2. Open connection → Foxglove WebSocket → `ws://localhost:8765`. The bridge is launched by the sim with the
   visualizer (`sim_nodes.py:265`) and the devcontainer shares the host's network, so `localhost` works.
3. Layout **Simulation** (its 3D panel reads `/vis/*`, published by the visualizer), or **FoxNOC** if the
   `.foxe` is installed (troubleshooting reference, section 14).
4. Worth adding as panels: a Raw Messages or State Transitions panel on `/central/discrete_garage_state`
   (bay 7's state: READY_TO_RETRIEVE → READY_TO_INSERT → PROCESSING_INSERT → VEHICLE_INSERTED, then AGV 1's
   pose leaving node 14), `/central/report` (the dispatcher's jobs and status), and a Log panel filtered on
   `scheduler` and `dispatcher` for the plan: with the fix there is no "Pre-motion planning sanity check
   failed" line; without it, that line and "Failed to plan Insert job" appear.

## 4. Timing to expect

The simulated bay boots only after its hardware-reset call, then validates its doors: every door closed
(`bay.door.close_time` 4 s), then the transition to the initial retrieve floor opens the system door
(`wait_to_open_time` 10 s plus `open_time` 4 s), so READY_TO_RETRIEVE comes roughly 20 s in. The manual
transition-to-insert job needs that state (`ExpandBayTransitionJob`: "not in Ready for Retrieve") and a
rejected manual job is dropped, not retried, which is why the event sits at 40 s. The patron at 45 s only
needs to be queued: the simulator offers a queued patron to the bays on every tick until one is
READY_TO_INSERT (`simulator.cpp:179`), so the patron drives in as soon as the transition's door travel is
done (about 14 s), is confirmed, and the insert plan follows within the dispatcher's next cycle (1.8 s).
The other timed scenarios put their patrons at 5 to 30 s; the later times here buy the manual transition
its margin. The plan itself is about 75 s of sim time at factor 1.

## 5. If it does not do what the recording does

- AGV 1 moves before the patron arrives: the dispatcher was not in MANUAL (the mode can only be set while
  STOPPED, which is why the event comes before `start_dispatch`), or dispatch charging was on.
- The patron never enters: B7 did not reach READY_TO_INSERT. Check the transition job's outcome in
  `/central/report` and the bay's state; the bay may still have been booting at 40 s (move the event later).
- The plan differs from the recording: the sim's collision table is the sandbox layout's, and the scheduler
  runs with `params_sim.yaml`; a different charger (C10) or route is still a correct eviction. A stash on
  W31 means no charger was reachable or every placement closed the route: compare with the four
  `StallBlockedBy*` recordings.
