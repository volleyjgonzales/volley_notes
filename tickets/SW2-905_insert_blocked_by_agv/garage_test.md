# Testing PR #1036 (SW2-905) on the Pecos comb garage, with the NOC

Written 2026-11-06 from `simulation.md` (the sim run of the same case), `garage/deploy_and_test.md` (sections
3.4, 3.6, 3.7, 4.0) and `tray_assignment.cpp`. Not yet run.

## 0. Facts checked before writing

- PR head `2f87b51a` = local branch tip. CI run 42272482949 ran on that commit and `runtime-images / build-push`
  passed, so ECR holds `volley:*-pr-1036` for exactly this code.
- Tailnet: `central-comb-5675-pecos` is the only Pecos central online (eng, bench and QA show `-`).
- comb runs the combined layout, the layout of the scheduler test (`busy_garage_car_in_bay_7_agv_on_charger_14`);
  the sim scenario used the sandbox layout. Node ids are the same.
- Stall search: disabled nodes are excluded (`path_filter.IsEnabled`), but a disabled node is also an
  obstacle in the keep-out filter for every footprint, so disabling a stall can close routes beside it (the
  disabled C10 closes W9). Fill stalls with trays rather than disabling them, near the route at least.

## 1. The case to reproduce

| Thing | State |
|---|---|
| AGV 1 ("the one in the way") | Enabled, idle, no tray, on charger C14 at `14@-90` |
| AGV 2 (the carrier) | Enabled, idle, anywhere off the route (the recording: under the empty tray on P5) |
| Bay B7 | Empty tray (27 in the recording) inside, bay ready for an insert |
| Stalls | Every stall except P15 holds a tray (car or empty). P15 is the only free stall |
| Chargers | C16 enabled and free (the recorded eviction target); C10 enabled too if you can |
| Dispatcher | **Manual**: in Auto, starting queues a clean-garage job that hides AGV 1 under a tray first |

Expected plan (the recording, and the sim): AGV 1 drives C14 → P15 → P17 → C16 while AGV 2 drives to W31 → B7
and lifts; the loaded leg B7 → W31 → W8 → W13 → P15 waits for AGV 1 to reach C16; the tray ends on P15.
On `main` the same request fails validation ("Requested to move to 15@90 but it's occupied") and the insert
is dropped with the car shut in the bay. Don't reproduce that on the garage: recovery is faulting the bay and
restarting the dispatcher.

## 2. Deploy pr-1036 on comb (you, on the node)

```bash
ssh ops@central-comb-5675-pecos
```
Record what's there, and save `.env.local` (comb may still point at the laptop-pushed `dds-diag-*` build):
```bash
swarmctl info; docker service ls --format '{{.Name}}  {{.Image}}'; cat /data/swarm/.env.local
```
```bash
cp /data/swarm/.env.local ~/env.local.before-pr-1036
```
Point it at ECR and the PR tag (no `sed -i` in `/data/swarm`):
```bash
sed -e 's/^VOLLEY_REGISTRY=/#VOLLEY_REGISTRY=/' -e 's/^VOLLEY_VERSION=.*/VOLLEY_VERSION=pr-1036/' /data/swarm/.env.local > /tmp/env.local.new && cat /tmp/env.local.new > /data/swarm/.env.local
```
```bash
swarmctl deploy app
```
Check the build: should print `2f87b51`.
```bash
docker exec "$(docker ps -qf name=_central.)" printenv GITSHA
```

## 3. NOC setup

Open `http://central-comb-5675-pecos:8011/webviewer/` on the laptop (or `http://100.120.46.20:8011/webviewer/`
if Chrome's secure DNS skips MagicDNS).

1. **Request Control** until the top bar says "Control: You".
2. Status is Stopped after the deploy. **Mode → Manual.**
3. While Stopped, check that AGVs 1 and 2, C14, C16, P15, B7 and the route nodes (W31, W8, W13, P17) are
   enabled.
4. **Status → on**, wait for Running.

## 4. Arrange the garage (Manual moves, one at a time)

Right-click → Move, poses like `14@-90`. Use AGV 2 for the tray moves.

1. Trays: move trays until every stall except P15 holds one, and an empty tray is in B7. If there are not
   enough trays, disable only stalls far from P15/P17/C14/C16/W13/W31 (Stopped only), never one beside the
   route.
2. AGV 2: leave it idle, without a tray, off the route (P5 under a tray is what the recording used).
3. AGV 1 last: **Move AGV 1 → `14@-90`** (it reaches C14 through P15, which is still free). Leave it there.
   Low battery doesn't matter yet (the unassignable list of #1031 is not on this branch).
4. **Never move a tray onto P15 by hand** (NOC tray → Move to `15@90`). A move with an explicit destination
   skips the stall search and the eviction, so validation rejects it while a16 is on C14 ("Requested to move to
   15@90 but it's occupied", the comb run of 2026-11-06), and a tray on P15 would leave the insert no stall.

Screenshot the NOC's 3D view here: it's the "before" picture.

## 5. The insert

1. Ready B7: the manual **transition bay to insert** job (bay right-click). It needs B7 READY_TO_RETRIEVE
   with the tray inside; a rejected manual job is dropped, so check the bay state first.
2. Drive a car in (or the usual test vehicle), then **Confirm insert payload** on B7. The bay reports
   VEHICLE_INSERTED and the dispatcher creates the InsertJob in Manual too; its planner timer plans it.
3. Keep a hand near **Pause/Stop** (anyone can stop, no control needed) and the physical E-stop.

## 6. What passes

- [ ] AGV 1 leaves C14 for C16 (through P15, P17) without a manual command
- [ ] AGV 2 approaches B7 at the same time and lifts; it carries the tray out only after AGV 1 is on C16
- [ ] The tray with the car is lowered on P15; the insert job completes; B7 is released
- [ ] AGV 1 ends charging on C16
- [ ] No validation error in central's log:
  ```bash
  docker service logs app-comb_central --since 15m 2>&1 | grep -i -E 'occupied|validat|fail'
  ```
- [ ] Nothing comes close to colliding (watch C14 → P15 → P17 and the loaded leg's turn into P15)

Optional, only if time allows: the control (AGV 1 not on C14, P15 free: plain insert to P15) and AGV 1
disabled on C14 (expect the tray stashed on a waypoint, AGV 1 untouched).

## 7. Going back (don't skip)

```bash
cat ~/env.local.before-pr-1036 > /data/swarm/.env.local
```
```bash
swarmctl deploy app
```
(or `swarmctl remove app` if the app wasn't running when you arrived). Re-enable anything you disabled first.

## 8. comb's state, read 2026-11-06 (over SSH, from the control container)

Read with `ros2 topic echo <topic> <type> --once` in `app-comb_control` (the type must be given, or the
echo gives up before discovery finishes; `ros2 topic list -t` lists them).

- Deploy: already `VOLLEY_VERSION=pr-1036`, ECR registry, `BAY_IDS_OVERRIDE="7"`; central's `GITSHA` is
  `2f87b51`. Central restarted about 1 h before. Step 2 is done; the saved `.env.local` copy is up to you.
- Dispatcher: STOPPED (4), MANUAL (2), consistent, no jobs pending or active, not faulted.
- AGVs: **a16** (not "AGV 1") stopped on C14 at `14@-90`, no tray, 79 %, not charging. **a17** stopped in
  bay B7 at `7@-90`, lift down, no tray, 91 %.
- Bay B7: READY_TO_RETRIEVE, door report SYSTEM_OPEN. Empty tray 9 in it at `7@90`.
- Trays (9): P2, P3, P5, P6, P17, P19, P20, P23 and B7. Stalls of the layout: 2, 3, 5, 6, 15, 17, 19, 20, 23,
  24. Disabled nodes: 24, 25, 26, 27. So **P15 is the only enabled free stall** and C10 and C16 are free and
  enabled: the case of section 1, with no tray moves needed.
- One difference from the recording: the carrier (a17) stands in B7 under the tray, not at P5, so the plan
  should have no approach leg: a16's eviction to C16, then a17 lifts and carries the tray to P15. Whether a
  car may be driven onto the tray with an AGV underneath is a question for Dan or Justin; otherwise move a17
  out first (Manual, for example to `5@90` under tray 5, the recording's pose).

### Commands behind each claim (run from the laptop)

Deploy, overrides and build:
```bash
ssh ops@central-comb-5675-pecos 'docker service ls --format "{{.Name}}  {{.Image}}" | grep app-comb; cat /data/swarm/.env.local'
```
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_central.)" printenv GITSHA'
```
```bash
ssh ops@central-comb-5675-pecos 'docker service ps app-comb_central --format "{{.CurrentState}}" | head -1'
```
Topic types (needed by the echoes):
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 topic list -t --no-daemon --spin-time 8' | grep -E 'central/(report|discrete_garage_state)|agv/a1[67]/report|bay/b7/report'
```
Dispatcher status and mode (`status: 4` = STOPPED, `mode: 2` = MANUAL, from `interfaces/msg/DispatchReport.msg`):
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 topic echo /central/report interfaces/msg/DispatchReport --once --no-daemon --spin-time 5'
```
AGVs, trays and disabled nodes (`garage_pose_and_lift`, `is_charging`, `battery_fraction` per AGV):
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 topic echo /agv/a16/report interfaces/msg/AgvReport --once --no-daemon --spin-time 5' | head -30
```
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 topic echo /central/discrete_garage_state interfaces/msg/DiscreteGarageState --once --no-daemon --spin-time 5 --full-length' > comb_dgs.yaml
```
```bash
grep -A3 -E '^- id:|^  pose:' comb_dgs.yaml | grep -E 'id:|node_id|heading' | head -60; grep -A6 '^disabled_nodes' comb_dgs.yaml
```
Bay 7:
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 topic echo /bay/b7/report interfaces/msg/BayReport --once --no-daemon --spin-time 5' | grep -E 'state_string'
```
The layout's stalls (on the laptop; node type `Parking`):
```bash
python3 -c "import yaml;n=yaml.safe_load(open('$HOME/volley/src/config/site_config/layouts/5675_pecos_combined.yaml'))['nodes'];print(sorted(x['id'] for x in n if x['type']=='Parking'))"
```

## 9. Correction to section 5: readying the bay is not a NOC button

The NOC's bay menu has only **Confirm insert payload** and **Confirm retrieve payload**
(`controller_webview/js/noc/noc3DMenus.js:397`; `action/` has no transition script). The manual transition is
the dispatcher's ROS service `/central/transition_bay_to_insert` (`interfaces/srv/TransitionBayToInsert`,
`dispatch_ros.cpp:230`), accepted only in Manual (`CanAcceptManualJob`). The scheduler then refuses it unless
B7 is READY_TO_RETRIEVE and its ODP area is clear (`ExpandBayTransitionJob`, `job_expansion.cpp:672`;
`IsBayOdpAreaClear`, `scheduler.cpp:348`), so with a17 in the bay it may fail with "the ODP's area is
occupied" (a safe failure; move a17 out and send it again). From the laptop:
```bash
ssh ops@central-comb-5675-pecos 'docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 service call /central/transition_bay_to_insert interfaces/srv/TransitionBayToInsert "{bay_id: 7}"'
```
