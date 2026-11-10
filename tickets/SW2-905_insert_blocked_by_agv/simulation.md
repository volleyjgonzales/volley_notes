# Watching `StallBlockedByAgvOnCharger` in simulation, with Foxglove

Written 2026-11-06 from `docs/architecture/sim.md`, `docs/guides/simulation.md`, `src/sim/src/scenario_runner.cpp`,
`src/sim/src/simulator.cpp`, `src/central/src/dispatch.cpp` and the notes repo's `garage/deploy_and_test.md`
(section 2) and `garage/troubleshooting_reference.md` (section 14). Run by the user in Foxglove on 2026-11-06.
Updated 2026-11-08 with what that run taught (sections 2, 3, 6 and 7), from `src/vis/src/vis_manager.cpp`,
`src/sim/src/sim_clock_ros.cpp` and `src/sim/src/simulator.cpp`.

## 1. The scenario file

`src/scenario/scenarios/5675_pecos_combined_insert_blocked_by_agv_on_charger.yaml` (in the tests commit). It is the scheduler test's busy garage on
the `5675_pecos_combined` layout. Until 2026-11-09 it was `5675_pecos_sandbox_combined_…` on the sandbox
layout, which #1048 (SW2-598) deleted; the combined layout is a superset (it adds bay B21 and waypoint W41,
the other 26 nodes keep their ids), so the sim also starts a second bay. The old path now fails at launch
with `FileNotFoundError` and `InvalidFrontendLaunchFileError`.

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
ros2 launch launcher sim.launch.py scenario:=/home/jon-gonzales/volley/src/scenario/scenarios/5675_pecos_combined_insert_blocked_by_agv_on_charger.yaml real_time_factor:=1 enable_dispatch_charging_mode:=false rviz:=false
```

- The absolute path is deliberate: a bare name is looked up in the installed `scenario` package, which only
  knows the file after a rebuild of that package (`sim_nodes.py:462`).
- `real_time_factor` 1 or 2 is watchable; 10 is the system tests' speed. `0` pauses, but do not launch
  paused to get Foxglove ready first: section 3 explains why the 3D panel then stays empty. The factor can
  be changed while running (`ros2 param set /sim/clock real_time_factor 1.0`, or a Parameters panel in
  Foxglove), so pausing mid-run to look at a frame works.
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

On 2026-11-06 Ctrl+C in the VS Code terminal never reached the launch (no "user interrupted with ctrl-c"
line; `ros2 launch` and its five children were still alive). VS Code takes Ctrl+C as copy when text is
selected, and the key goes elsewhere when the terminal lacks focus. Sending the same signal from a host
terminal works whatever the terminal does:

```bash
devc exec pkill -INT -f "ros2 launch launcher sim.launch.py"
devc exec pgrep -af "component_container|foxglove_bridge|visualizer_node"
```

A second SIGINT makes launch stop at once if something hangs.

## 3. Foxglove

1. The Foxglove desktop app on the laptop (`foxglove.dev/download`; the web app may refuse a plain `ws://`
   connection). Sign in to the Volley organization for the shared layouts.
2. Open connection → Foxglove WebSocket → `ws://localhost:8765`. The bridge is launched by the sim with the
   visualizer (`sim_nodes.py:265`) and the devcontainer shares the host's network, so `localhost` works.
3. Layout **Simulation** (its 3D panel reads `/vis/*`, published by the visualizer), or **FoxNOC** if the
   `.foxe` is installed (troubleshooting reference, section 14). **Pecos Integration** works too (the topic
   names are the same); leave its Call Service panel (`{"value": 18}`) alone, it would change the sim's
   state.
4. Worth adding as panels: a Raw Messages or State Transitions panel on `/central/discrete_garage_state`
   (bay 7's state: READY_TO_RETRIEVE → READY_TO_INSERT → PROCESSING_INSERT → VEHICLE_INSERTED, then AGV 1's
   pose leaving node 14), `/central/report` (the dispatcher's jobs and status), and a Log panel filtered on
   `scheduler` and `dispatcher` for the plan: with the fix there is no "Pre-motion planning sanity check
   failed" line; without it, that line and "Failed to plan Insert job" appear.

Order: Foxglove first, then the launch. Foxglove keeps retrying `ws://localhost:8765` until the bridge is
up, so open the connection, then launch at factor 1; the first event worth watching is the transition.

Why launching at `real_time_factor:=0` leaves the 3D panel empty (seen 2026-11-06): every sim node runs with
`use_sim_time` (`sim_nodes.py:76`), the visualizer renders on a 50 ms timer on that clock
(`vis_manager.cpp:92`) and creates each `/vis/*` publisher only on its first render. With the clock frozen
the timer never fires, so the bridge never advertises a `/vis/*` topic (the `/vis/payloads` panel shows red,
the Dispatcher Mode panel "Unknown"). The scene appeared within a second of setting the factor to 1. If
the 3D panel stays empty after that, re-enable the `/vis/*` layers in its Topics section.

How the models get to Foxglove: markers are `MESH_RESOURCE` with a URL in `mesh_resource`, not the geometry.
The sim defaults to `use_remote_meshes:=false`, so the URLs are `package://sim/3d/*.dae`; Foxglove asks the
bridge for them over the same WebSocket (its `assets` capability) and caches each one. A live central uses
the Tailscale mesh proxy instead, because the runtime image drops `share/sim/`. No Tailscale is needed for
the sim.

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
- The plan differs from the recording: the sim's collision table is the combined layout's, and the scheduler
  runs with `params_sim.yaml`; a different charger (C10) or route is still a correct eviction. A stash on
  W31 means no charger was reachable or every placement closed the route: compare with the four
  `StallBlockedBy*` recordings.

## 6. Knowing when it is done

The sim never ends on its own. After the last event it keeps ticking with the garage idle until stopped;
nothing disappears and nothing is printed. The only time it exits by itself is a collision: `[FATAL] …
Collision: X collided with Y!`, then `rclcpp::shutdown()` (`simulator.cpp:326`), and the markers vanish
within their 1 s lifetime. Markers disappearing therefore means failure.

- `/sim/report` carries `num_remaining_events` and `running` (`simulator.cpp:331`); `running` turns true
  when dispatch settles and logs "Simulator running; scenario clock started." (`simulator.cpp:108`), and
  event times count from there. Zero remaining events means every event fired, not that the jobs finished.
- Done for this scenario: AGV 1 has left C14 for another charger (C16 in the recording), AGV 2 has parked
  car `…27` on P15, and `/central/active_jobs` and `/central/pending_jobs` are empty. A Raw Messages panel on
  `/sim/report` next to `/central/active_jobs` shows both at once.
- Without the fix: the insert job disappears from the jobs while the car stays in B7, after the planning
  failure lines in section 3.

## 7. The 2026-11-06 run

Run with the scenario as it stood before the timing change (transition at 20 s, patron at 90 s; section 4
explains why that transition was too early), launched paused, then set to factor 1.

- The scene, the cars (7 payloads, 21 `/vis/payloads` markers: body, wheels and windows each) and the
  dispatcher's MANUAL mode (mode 2, `DispatchReport.msg:10`) all came up as expected.
- Later the dispatcher sent B7 a type 1 command ("Empty Tray Delivered") every 1.8 s and the bay rejected
  each one: `ERROR: Empty Tray Delivered notification is not currently valid because A tray is not
  present`. AGV 1 logged "Chillin' while waiting for a pending order...". The run was stuck, not done.
  Not investigated. Likely candidates: the early transition was rejected and dropped, leaving B7 out of
  step with the dispatcher; or the simulated bay does not see tray 27 that the initial conditions put in
  B7, while the dispatcher does. Worth checking on the next run with the 40 s / 45 s scenario, before
  stopping: B7's state in `/central/discrete_garage_state` and the bay's tray presence in
  `/bay/b7/report`.
- `volley-in-container sh 'ros2 …'` saw neither `/sim/clock` nor `/clock`, even with `ROS_DOMAIN_ID=75`,
  while `pgrep` in the same container listed the sim's processes. Use an attached shell (`devc attach`) for
  `ros2 param` and `ros2 topic` on a running sim.
