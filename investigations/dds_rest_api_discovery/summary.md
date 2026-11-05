# DDS investigation: consolidated summary (2026-11-04)

One-page view of the stuck-REST-API investigation for a reviewer. The dated
detail is in `findings.md` (issue 1, sections 1.1-1.15),
the plan and experiments in `plan.md`, the commands in
`../../garage/troubleshooting_reference.md`, and how the garage is deployed in
`../../garage/deploy_and_test.md`. The running log of everything done is
`/home/jon-gonzales/repos/volley_notes/tickets/SW2-482_scheduler_core_refactor/SW2-482_notes.md`
(items 285-356).

## The problem

On the Pecos "combined" garage (`central-comb-5675-pecos`), the patron REST
API's `confirm-insert` sometimes fails with HTTP 500,
`confirm-insert: timeout waiting for service /bay/b7/confirm_insert ready`. The
REST API (`src/central_api/central_api/rest_api.py`, Python/rclpy) holds one
client per bay for `/bay/b<N>/confirm_insert` and `confirm_retrieve`. Before
calling, it waits 2.5 s for the service. When it fails, the client never becomes
available, although bay 7 offers the service.

## Topology

| Where | What | DDS role |
| --- | --- | --- |
| `central-comb` host (10.0.1.173 LAN, tailnet 100.120.46.20) | Docker swarm manager; `app-comb` stack: `central`, `control`, `noc`, `discovery-server`, `mysql`, `nginx` | |
| `discovery-server` container | `fast-discovery-server 42 -l discovery-server -p 11811` (image `ros2:lyrical-discovery-server-20260911`, from ros2-docker). **Doesn't load the Fast DDS profile.** State in memory only (no backup mode, no volume) | Discovery server |
| `central` container | `ros2 launch launcher central.launch.py`: `rest_api` (Python), `proxy_node`, one component container (dispatcher, garage tracker, **scheduler**, monitors), `metrics_recorder`, `visualizer_node`, `foxglove_bridge`, rosbag recorder | Super clients (`ROS_SUPER_CLIENT=true` from the image) |
| `control` container | `sleep infinity`; toolbox for `ros2` CLI and probes | Super client |
| `bay7-eng` host (a different machine) | `bay7` container: bay state machine and drivers, one component container | Plain client |

- **Network:** all on the swarm overlay `app-comb_internal` (172.16.3.0/24),
  interface named `overlay0`. Containers also have `eth0` on the host-local
  `docker_gwbridge`. Bay 7 ↔ central traffic crosses the LAN as VXLAN.
- **DDS setup:** `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, Fast DDS 3.6.2,
  rmw_fastrtps 9.4.9, ROS Lyrical (snapshot 2026-08-19), domain 0,
  `ROS_DISCOVERY_SERVER=discovery-server:11811`. Every ROS container loads the
  Fast DDS profile from swarm-deploy
  `swarm/stacks/app/config/fastdds-profile.xml`: builtin transports off; SHM
  plus UDPv4 limited to `overlay0`; `fastdds.type_propagation` disabled. Each
  container's entrypoint first runs `discovery_probe`
  (`src/infrastructure/dds_discovery/src/discovery_probe.cpp`): it waits until
  `discovery-server` resolves and a throwaway participant gets an answer.
- **Participants in central** (ports: discovery 7410 + 2·ID, data 7411 + 2·ID):
  ID 0 is `ros2 launch` itself (7410/7411, inherited as file descriptors by
  every child process). IDs 1-6 are the other processes. **ID 7 is the REST API
  (7424/7425): it registers last**, though its process starts first, presumably
  because of Python import time. All 60 of the REST API's endpoints are in that
  one participant.

## Every start observed

| When (UTC) | Kind of start | Build | Result | UDP drops in central (`RcvbufErrors`) | Notes |
| --- | --- | --- | --- | --- | --- |
| 11-03 ~18:25 | node boot (everything) | PR #1018 as of 11-03 (exact commit not recorded) | STUCK | — | failures at 19:35 (b21, bay possibly not deployed) and 21:51 (b7); stuck > 2 h |
| 11-04 00:48 | plain redeploy (central + bay only) | `073556e` | ok | — | |
| 11-04 16:06 | full stack recreate | `073556e` | STUCK | — | stuck from the first check; fresh process in the same container matched in < 1.2 s |
| 11-04 16:23 | plain redeploy | `073556e` | ok | — | a retrieve and an insert also passed |
| 11-04 20:14 | full stack recreate | `089e774` | ok | 382 | |
| baseline 1, 20:44:58 | full (`dds_attempt.sh`) | `e1d24a7` | ok | 116 | |
| baseline 2, 20:53:56 | full | `e1d24a7` | STUCK | 517 (not measured per socket) | recovered between 20:56:27 and 20:57:27, the minute the script's probes ran in central and control |
| baseline 3, 21:35:33 | full | `e1d24a7` | STUCK | 776, **all on the REST API's discovery socket 7424** | stuck 12 min hands-off; recovered between 21:48:35 and 21:49:45, the probe started 21:48:41 |
| E1b, 21:50:41 | discovery server restart only | `e1d24a7` | ok (not stuck for 4.5 min) | +66 (54 on launch's socket, 12 Foxglove) | |
| E2 attempt 1, 22:13:15 | full, profile with 4 MiB send/receive buffers | `e1d24a7` | **STUCK** | **0** (every Fast DDS socket `rb8388608`) | stuck 10 min hands-off; recovered between 22:25:25 and 22:26:35, the probe started 22:26:23 |
| restore, 22:27:42 | full, back to `/data/swarm` (original profile) | `e1d24a7` | **STUCK** | — | stuck at 22:30, when comb went to a teammate for unrelated testing; resumes 2026-11-05 |
| 11-04 ~22:50 | full (teammate, `bay-refactor`) | `84f6deb` | not measured | — | her unrelated testing; no diagnostics in that build |
| 11-05 00:58:07 | plain redeploy, **diagnostic build** | `29712d9` | ok | — | both bay 7 services ready at the first diag check; verbosity read-back 1; two Fast DDS warnings in the first second (host-ID fallback, SHM segment_size), findings 1.17 |
| diag1, 02:01:52 | full (`dds_attempt_diag.sh`, systemd user unit) | `29712d9` | ok | 288 (268 on the REST API's 7424) | ready at the first check, 11 s after the deploy; same two warnings, nothing else; the script's warnings file was empty because of ANSI colour codes (fixed locally, not yet re-copied), findings 1.18 |
| diag2, 02:10:24 | full (`dds_attempt_diag.sh`, fixed script) | `29712d9` | **STUCK** | 598 (all on 7424) | **the REST API's own graph: `rq_readers=0 rr_writers=0` for 777 s**, heartbeat fine, no EDP warning; probe (one rclpy process in control) 02:23:32, **recovered 02:23:33** with bay 7's GIDs, findings 1.19 |
| 11-05 02:53:54 | plain redeploy, build `4b00571` (bay graph line) | `4b00571` | ok | — | `nodes=7 topics=20 publishers=24`, 2 bay participants, 5 ms check; findings 1.20 |
| diag3, 02:55:15 | full (v3 script: captures, unrelated probe first) | `4b00571` | ok | 324 (146 on 7424) | everything full at the first check; captures and full logs saved; findings 1.20 |
| diag4, 03:02:50 | full (v3 script) | `4b00571` | ok | 1178 (874 on 7424) | most drops of any start, still healthy; one transitional `publishers=0` bay sample; findings 1.21 |
| diag5-12, 03:08-03:40 | 8 full starts back to back (v3 script, captures on) | `4b00571` | all ok | — | 10 ok of 10 on this build with captures (diag3-12); the setup suppresses the failure, or chance |
| diag13-14, 03:41-03:49 | back to back, **captures off** | `4b00571` | ok, ok | — | |
| **diag15, 03:49:31** | full, captures off | `4b00571` | **STUCK** | 600 (all on 7424) | **bay 7's state-machine participant entirely unknown** to the REST API (`nodes=1 publishers=3`, one prefix) for 13 min; **a bare rclpy node with no clients healed it in 2 s**; findings 1.22 |
| 11-05 04:03:54 | plain redeploy, **watchdog build** | `25f354b` | ok | — | no trip on a healthy start |
| diag16-18, 04:04-04:16 | back to back, captures off, watchdog (restart only) | `25f354b` | 3 ok | — | no false trip |
| diag19-45, 04:16-06:08 | back to back, captures off, watchdog with the poke | `aeb5990` | 27 ok | — | no false trip; no STUCK start to heal |
| diag47-48, 14:32-14:40 | two full starts, hardened watchdog | `480b803` | 2 ok | — | no watchdog line, no restart file |
| restore, 14:41:33 | plain redeploy back to `pr-1018` from ECR | `e1d24a7` | ok | — | the PR #1018 CI image predates the dropped client-recreate commit; `.env.local` registry line commented, `~/swarm-exp` removed |

"Plain redeploy" restarts only `central` and the bays (their command carries a
deploy timestamp); the discovery server keeps running. "Full" removes and
redeploys the whole `app` stack, so the discovery server starts together with
everything.

## What's established

1. **Only the REST API process is stuck.** During a stuck state:
   - a fresh rclpy process in the same container, or in `control`, matches every
     bay 7 service in 0.8-1.2 s (`probe_clients.py`)
   - the graph (`probe_graph.py` from `control`) shows exactly one server for
     each bay 7 service, with one request reader and one reply writer, from
     `/bay/b7/bay_state_machine`
   - `ros2 service info --verbose` shows the server knows the REST API's client
     endpoints
   - central's C++ processes receive bay 7's topics
2. **Recreating the REST API's clients doesn't help** (commit `e1d24a7`, a 10 s
   refresh that destroys and recreates unmatched clients). The participant is
   the problem, not the client objects.
3. **Waiting doesn't help:** 12 min hands-off (baseline 3), > 2 h on 11-03.
4. **A new participant joining un-sticks it (4 of 4).** Every probe created
   clients for the same bay 7 services. E2's window started 58 s before its
   probe, so that one is the least certain. diag2 (11-05) has a positive
   transition: both services went from `0/0` to `1/1` in the REST API's check
   1-2 s after the probe started, after 10 min of nothing.
5. **While stuck, the REST API's ROS graph has none of bay 7's service
   endpoints** (diag2: its own graph cache `rq_readers=0 rr_writers=0` from the
   first check to the recovery), its own callbacks keep running, and **Fast DDS
   logs no EDP warning** (verbosity confirmed on): the "UNKNOWN RTPSParticipant"
   rejection path didn't fire.
6. **Nothing of one remote participant reaches the graph** (diag15): the stuck
   REST API's graph holds the node and publishers of bay 7's component-container
   participant and nothing of the state machine's participant, which serves
   `confirm_insert`: no node, no publisher, no endpoint. Whether the participant
   announcement itself or only what follows it was lost can't be seen from
   Python (Codex review 2). **A bare node with no clients joining was followed
   by recovery in 1-3 s** (diag15), so same-topic interest isn't needed; 5 of 5
   recoveries followed a join, the last two with exact timestamps, the earlier
   three with windows.
7. **A discovery server restart alone doesn't cause it (1 of 1).** It takes a
   full start.
8. **UDP socket overflow isn't the cause.** It happened on the REST API's
   discovery socket in stuck runs, but E2 (4 MiB buffers, 0 drops) still got
   stuck.
9. **CI can't reproduce it:** the system tests run without a discovery server,
   with localhost-only discovery.

## Hypotheses still open

- **H7, now (diag15, 11-05):** the REST API's participant never receives one
  specific remote participant's discovery data (DATA(p) and all that follows)
  from the server, and nothing re-sends it until another participant registers,
  which makes the server's discovery writer send again and the REST API catch
  up. A silently desynchronised reliable discovery stream to one late client
  (the REST API registers last in central). Fast DDS PR #6542 (merged on `3.6.x`
  after 3.6.2, unreleased) describes a mechanism of that shape. The capture that
  would prove it seems to suppress the failure.
- **H7, narrowed by diag2 (11-05):** the failed-proxy-add branch (the
  UNKNOWN-participant warning) did not fire in a stuck start with logging on;
  what's left is that bay 7's endpoint data never reaches the REST API's EDP
  processing, or is discarded silently (reliability / sequence state, cf. Fast
  DDS PR #6542). A capture inside central's network namespace is the way to
  tell. Original statement: a discovery race at full start. The REST API is sent
  bay 7's endpoint data (DATA(r)/DATA(w) for `rq/bay/b7/confirm_insertRequest`,
  `rr/bay/b7/confirm_insertReply`, …) in a state where it doesn't act on it, for
  example before the owning participant's DATA(p) is known, or during the REST
  API's own late registration. Nothing re-sends it until new interest in those
  topics (a joining participant) makes the server relay it again.
- **H2 variant:** it depends on the discovery server and the participants
  starting within the same seconds (all containers' probes wait about 6 s for
  `discovery-server` to resolve, then start within 0.5 s of each other).
- **H3: moot.** Since Fast DDS 3.5.0 a CLIENT behaves like a SUPER_CLIENT, so
  this changes nothing (Codex review, verified). Sources:
  <https://github.com/eProsima/Fast-DDS/pull/6272>, the v3.6.2 `versions.md`,
  and the Fast DDS docs' "Discovery Server and Discovery Server Pro" table
  (findings 1.16).
- **H4:** the transport mix (SHM within a container, UDP across); untested.
- **H5:** a Fast DDS 3.6.2 bug; untested (newer 3.6.x / 3.7 not tried).
- **H6:** the discovery server runs without the profile (all interfaces, builtin
  transports); untested.

## Constraints for any proposal

- **Comb is a shared test garage.** Each full-restart attempt takes the app
  stack down for about 1-1.5 min; a STUCK attempt runs up to about 16 min.
- **`ops` (the login on the central nodes) has restricted sudo:** no `cp` or
  editors as root. Stack files in `/data/swarm` are root's. Experiments run from
  a copy with `swarmctl --root ~/swarm-exp` (see the plan).
- **Starting attempts remotely:** use a `systemd-run --user` unit with
  `HOSTNAME` set. `nohup` over a non-interactive ssh gets killed with the
  session. Details in plan section 4.3.
- **A probe, `ros2` command or Foxglove reconnect** creates a participant and
  may un-stick the REST API. Keep hands off while measuring.
- **Changing Fast DDS or the discovery server image** means a ros2-docker image
  bump (Dan) and a volley PR. Changing the profile or stack files means a
  swarm-deploy release. Changing the REST API's launch or code means a volley PR
  (the current branch is PR #1018, a scheduler refactor; a DDS fix should be its
  own PR).

## Repositories and key files

| Repo | Where | Files |
| --- | --- | --- |
| volley | `/home/jon-gonzales/volley` (branch `jmg/SW2-1135/scheduler-renames-and-cleanups`, `e1d24a7`) | `src/central_api/central_api/rest_api.py` (clients at ~374-381, `refresh_bay_clients` ~480, `main` ~3400), `src/central_api/central_api/ros_parking_gateways.py`, `src/launcher/launcher/central_nodes.py`, `src/launcher/launch/central.launch.py`, `docker/Dockerfile` (`ROS_SUPER_CLIENT` at 570/578), `docker/resources/entrypoint.sh`, `src/infrastructure/dds_discovery/src/discovery_probe.cpp`, `docs/architecture/discovery-server.md`, `.github/actions/system-tests-group/action.yml` |
| swarm-deploy | `/home/jon-gonzales/swarm-deploy` (local checkout older; use `git show origin/HEAD:<path>`; comb runs release `c9b6529`) | `swarm/stacks/app/support.yaml` (discovery server), `main.yaml`, `bay.yaml.j2`, `config/fastdds-profile.xml`, `swarm/.env`, `README.md` ("Fast DDS profile"), `swarmctl/src/swarmctl/` |
| ros2-docker | GitHub `VolleyAutomation/ros2-docker` only (`gh api repos/VolleyAutomation/ros2-docker/contents/...`) | `Dockerfile` stage `discovery-server` |

The probe and measurement scripts are reproduced in
`../../garage/troubleshooting_reference.md` (sections 7 and 12) and
`plan.md` (4.3).
