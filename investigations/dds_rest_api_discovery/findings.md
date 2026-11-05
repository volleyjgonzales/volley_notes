# Garage test findings, 2026-11-03

Two problems seen while testing PR #1018 (branch `jmg/SW2-1135/scheduler-renames-and-cleanups`) on the
garage. A teammate's branch, `pvc/test/confirm-insert-reliability-improvements`, ran confirm-insert
successfully on the same hardware. Both were investigated from the code, starting from diffs against
that branch and against `main`.

**Summary**

| # | Problem | Caused by this branch? | Root cause | Fix |
|---|---|---|---|---|
| 1 | `confirm_insert` service "never ready", insert returns 500 | No (also passed on `main`, 16:06) | Most likely a startup discovery race (Paula). The REST API's long-lived bay clients wait only 2.5 s for discovery and never retry with a fresh client, so one missed discovery at startup lasts until the REST API restarts. | Recreate the client on a miss in both the v2 and v3 paths; the teammate's branch does it for v2 only. |
| 2 | AGVs logged as "carrying t0" | No | `tray_id` 0 is the "no tray" value, and two log lines print it raw | None needed. Optionally print "no tray" for 0. |

## How the branches compare

| Ref | Commit | What it is |
|---|---|---|
| `main` | `bf59774c` | Base of both branches |
| This branch | `ff6ba632` | `main` + the seven refactor commits |
| Teammate's branch | `1c529f35` | `main` + two commits (below) |

The teammate's two commits:

| Commit | Time (UTC) | Files | Change |
|---|---|---|---|
| `cf0eb3e9` "chore: bay state machine logging" | 22:35:30 | `bay/bay_state_machine.hpp`, `bay/bay_state_machine_ros.cpp` | Logging only: why `ConfirmInsert` is rejected, and "Created service confirm_insert" at startup |
| `1c529f35` "chore: confirm insert/retrieve client warmup helper" | 22:36:14 | `central_api/rest_api.py` | Waits for every bay's confirm clients at startup, and recreates a client when discovery misses (details in 1.4) |

Both commits are dated after the two failures (19:35Z and 21:51Z), and the branch was force-updated on
GitHub today (`b9ed8777` → `1c529f35`). So the run that worked used the REST API change above.

This branch changes nothing in `bay`, `central`, `central_api`, `common_ros`, `docker` or `launcher`.
Outside `src/planner` it touches only agvctl (`agvhito_tools/src/agvctl/move_planner.{hpp,cpp}`, the
`scheduler::Scheduler` member). Every file involved in either problem is identical to `main`.

---

## 1. `confirm_insert` never becomes ready

### 1.1 What was observed

```
[rest_api-1] [ERROR] [1793742677.403047304] [rest_api.rest_api]: confirm-insert: timeout waiting for service /bay/b7/confirm_insert ready
```

- 19:35:59Z `POST /api/v2/bay/b21/confirm-insert` → 500
- 21:51:17Z `POST /api/v3/bay/b7/confirm-insert` → 500
- Bay 7 logged `GUIDING_VEHICLE -> VEHICLE_INSERTED` (VEHICLE_COMPLIANT) at 21:49:49Z, then nothing more.
- Across the day's 14 rosbags, `/bay/*/confirm_insert/_service_event` has no messages. The `command`,
  `open`, `reset_hardware` and `patron_light_control` service events are present.

### 1.2 Where the error comes from

The REST API creates one client per bay at startup and keeps it for the life of the process
(`src/central_api/central_api/rest_api.py:372-379`):

```python
for bay_name in bay_names:
    self.bay_confirm_insert_clients[bay_name] = self.create_client(
        SetPayloadInfo, f"/bay/{bay_name}/confirm_insert"
    )
```

Both API versions use that same client dict and the same 2.5 s discovery timeout
(`ROS_SERVICE_DISCOVERY_TIMEOUT_SEC = 2.5`, `rest_api.py:88`):

| API | Route | Path to the wait | Wait |
|---|---|---|---|
| v2 | `rest_api.py:2879` | `REST_API.bay_confirm_insert` (`rest_api.py:2954`) | `rest_api.py:488-493`: `client.wait_for_service(timeout_sec=2.5)`, else `ConfirmInsertError` |
| v3 | `rest_api_v3.py:137` | `ParkingController.insert_for_patron` → `RosBayGateway.confirm_insert` | `ros_parking_gateways.py:44-48`: same wait, else `NotIssued` |

The gateway gets the dict itself (`rest_api.py:385`, `RosBayGateway(self.bay_confirm_insert_clients, ...)`),
so both versions share the same client objects. Both errors produce the same text: `ConfirmInsertError`
adds the `confirm-insert:` prefix (`rest_api.py:258`), and the gateway writes it out
(`ros_parking_gateways.py:46`). **The v2 vs v3 difference is unrelated.**

Neither path ever retries with a new client. If this client's view of the graph doesn't show the bay's
service within 2.5 s, every call fails the same way until the REST API restarts.

### 1.3 The bay side advertises the service

`src/bay/src/bay_state_machine_ros.cpp:204-212`, in `RegisterServices()`:

```cpp
command_srv_ = volley::rclcppx::CreateService<BayCommandSrv>(node_, "command", ...);

confirm_insert_srv_ = volley::rclcppx::CreateService<SetPayloadInfoSrv>(node_, "confirm_insert", ...);
```

`confirm_insert` is created unconditionally, in the same function and on the same node as `command`,
whose events do appear in the bags. Nothing in the bay state machine creates or destroys it per state.
So "never advertised" is unlikely, and "advertised under a different name" is ruled out: both are
relative names on the same `/bay/<name>` node, and `command` shows up as `/bay/<name>/command`.

### 1.4 Why the service-event topic is empty

`rclcppx::CreateService` turns on introspection
(`core/rclcppx/include/rclcppx/interface_factories.hpp:117-122`, from the `introspection_mode` parameter).
The server then publishes on `<service>/_service_event` **only when a request arrives or a response
goes out**. The REST API's clients are plain `create_client` calls with no introspection, so they
publish nothing either.

The REST API stopped at `wait_for_service` and never sent a request. So the bay had nothing to publish,
and the empty topic is what you'd see **whether or not the service was advertised**. It shows that no
call reached the bay, which matches bay 7's log stopping at `VEHICLE_INSERTED`. It doesn't show that
the service was missing.

### 1.5 What the teammate's branch changes, and why it worked there

`1c529f35` changes `rest_api.py` in two ways:

1. **Startup warm-up.** Right after creating each bay's clients, it calls
   `wait_for_service(timeout_sec=30.0)` on both and logs "discovered at startup" or "not discoverable
   within 30s".
2. **Recreate on a miss.** `_get_ready_client(client, recreate_fn)` waits 2.5 s. On a miss it creates a
   fresh client, which makes Fast-DDS ask the discovery server again, and waits another 2.5 s. The new
   client replaces the old one in the dict. This is wired into the v2 `bay_confirm_insert` and into
   `bay_confirm_retrieve`.

Points to note about that change:

- **v3 isn't covered by the retry.** `RosBayGateway.confirm_insert` still does one 2.5 s wait. It only
  benefits from the startup warm-up, or from a v2 call having already swapped the client in the shared
  dict. Today's 21:51Z failure was a v3 call.
- **The warm-up blocks startup.** It runs synchronously in `__init__`: up to 30 s × 2 services × each
  bay, if bays aren't reachable. A background `_warm_up_bay_clients` thread is defined but left
  commented out.
- **It's diagnostic code.** The extra `log_warning` lines ("Creating bay insert client…") and
  `cf0eb3e9`'s bay logging are for testing, not for merging as they are.

### 1.6 Likely root cause (not proven from code)

The REST API's long-lived clients lose sight of the bays' services, and nothing makes them look again.
The comment on the teammate's helper names the usual trigger: a node or discovery-server restart.
`swarm-deploy` restarts central and the bay services on every deploy (`DEPLOY_ISO_TIMESTAMP`, see
`../../garage/deploy_and_test.md` 3.4), so the order those containers come up in after a deploy is a plausible cause.
The code alone can't confirm it.

### 1.6.1 Update, 16:07: passed on `main`, likely a startup race

Paula: confirm-insert **passed on `main` too**. She thinks it's a startup race condition, the same one
seen a few months ago, and is checking whether anything in the discovery server has changed.

What this adds:

- **It confirms this branch isn't the cause.** `main` has the same REST API and bay code as this
  branch, without the teammate's fix, and it worked. So the problem comes and goes, depending on
  startup order, not on code.
- **A startup race fits the code.** If discovery of the bay's service is missed when the REST API and
  the bays (re)start together on a deploy, nothing in `main`'s REST API ever looks again (1.2).
- **The failure lasted, which also fits.** The two failures were 2 h 16 min apart (19:35Z and 21:51Z), on
  different bays (b21, b7). If the REST API wasn't restarted in between, the same clients stayed blind
  for over two hours. That's a missed discovery at startup that never recovers, not slow discovery.
  Check the rest_api container's start time to confirm.
- **For the fix, the retry matters more than the warm-up.** The 30 s startup wait only helps if the
  bays register within those 30 s. Recreating the client on a miss (1.5) recovers whenever the
  service eventually shows up, at the cost of one extra 2.5 s wait on the first call. That's why v3
  should get the retry too (1.8).

### 1.7 The one check that settles it

Grep the **teammate's** rest_api log from the run that worked:

```bash
grep -E 'recreating client and retrying|still not found after recreating|discovered at startup|not discoverable within' <rest_api log>
```

- If it shows "recreating client and retrying" and then a successful call, the stale long-lived client
  is the root cause, and recreating the client fixes it.
- If every bay was "discovered at startup" and no recreate happened, the 30 s startup wait was enough.
  The cause is then discovery that's slow right after a (re)start, not a client that goes stale later.

If it fails again on this branch, run this on the garage while it's failing, inside the central
container (a new participant, so it sees current discovery):

```bash
ros2 service list --no-daemon | grep confirm_insert
```

- Listed: the bay is advertised, and the REST API's existing client is stale.
- Not listed: the bay never registered with the discovery server. Look at the bay container and the
  discovery server, not the REST API.

### 1.8 Smallest fix

Use the same recreate-on-miss in the v3 gateway, so both paths behave the same:
`RosBayGateway.confirm_insert` (`ros_parking_gateways.py:44-48`). With the teammate's
`_get_ready_client` (or a small equivalent passed in), it would recreate the client and wait once more
before raising `NotIssued`, and store the new client back in the shared dict. The startup warm-up is
better as the background thread already drafted, so it doesn't hold up the API's startup.

This belongs to the teammate's branch or its own PR, not to PR #1018.

### 1.9 Update, 2026-11-04: the client-recreate patch didn't fix it

On central-comb, with `073556e` (the patch) deployed, the app stack was recreated at about 16:06:39Z:
the discovery server, central, control, noc and bay 7 all started at once (`docker service ps` shows a
single task each, all started together). The confirm-insert from the patron app at 16:10:42Z still
returned 500 (`timeout waiting for service /bay/b7/confirm_insert ready`). Logs: `swarmctl logs -e
logstore-agent -e noc`.

What the logs and checks on the node show:

| Check | Result |
|---|---|
| REST API refresh | Recreated b7's `confirm_insert` / `confirm_retrieve` clients **every minute** from 16:06:58Z on; never matched |
| Bay 7 advertises the services | Yes: a fresh `ros2 service list` in the central container lists `/bay/b7/confirm_insert`, `confirm_retrieve`, `command`; the bay's recorder subscribed to `/bay/b7/confirm_insert/_service_event` |
| Bay 7 ↔ central over DDS | Works for topics: the garage tracker gets bay 7's reports, the Foxglove bridge sees every `/bay/b7/*` topic |
| REST API in the graph | `/rest_api/rest_api` is listed by `ros2 node list` |
| **Fresh Python process in the same container** | `rclpy` clients for `/bay/b7/confirm_insert`, `/bay/b7/confirm_retrieve`, `/bay/b7/command`, `/central/start` all **ready in 0.8-1.2 s** |

**Conclusion.** The problem isn't the client object, bay 7, the network or the discovery server. It's
the REST API **process's DDS participant**. In rclpy, every client in a process uses its one
participant. rmw_fastrtps reports a client ready only when its request and response endpoints have
**matched** the server's, and this participant never matches bay 7's service endpoints, even for brand-new
clients. A new process (new participant) in the same container matches at once. That's why recreating
clients changed nothing.

**When it happens.** Last night's plain redeploy (00:48Z) restarted only central and bay 7 against a
discovery server that was already running, and everything matched. Today the whole stack, the
discovery server included, started at once, and the REST API's participant came up unable to match
bay 7. That fits a participant-level startup race. The Fast DDS profile in the runtime images
(`/etc/fastdds/profile.xml`, from the `ros2:lyrical-*` base image, not this repo) already mentions this
kind of failure: it disables type propagation because it "can flood UDP and leave endpoints unmatched,
this causes participant boot issues". Not yet known: whether only the Python REST API is affected or
C++ clients too (central's C++ nodes receive bay 7's **topics**, but the dispatcher's service client to
`/bay/b7/command` hasn't been exercised since startup).

**Decisive test.** Restart only `central` while the discovery server and bay 7 keep running:
```bash
docker service update --force app-comb_central
```
If the REST API then matches (no more recreate lines and a working confirm-insert), the cause is a
participant starting together with the discovery server and/or bay, and the patch is the wrong fix.

**Fix options**, to decide after that test:
1. **Root cause, in DDS setup** (Dan / ros2-docker owner): discovery server and participant start order,
   the base image's Fast DDS profile, the probe in `docker/resources/entrypoint.sh`. This fixes every
   process at once.
2. **Self-heal in the REST API**: if central reports bay N alive but the REST API's client for it
   stays unmatched for some time, exit, and have launch respawn the process (`respawn=True` in
   `launcher/central_nodes.py`). A new process gets a new participant. Restarting the process is the
   proven cure; recreating clients isn't.
3. **Revert `073556ea`**, since recreating clients doesn't help with this failure.

### 1.10 Update, 2026-11-04 16:23-16:39Z: a plain redeploy and a retrieve pass

| Deploy | Discovery server restarted? | REST API ↔ bay 7 |
|---|---|---|
| 2026-11-03 ~18:25Z, node boot (uptime 6 h at 00:30Z) | Yes (everything started) | Failed at 19:35Z and 21:51Z, hours later |
| 2026-11-04 00:48Z, plain `swarmctl deploy app` | No | Matched |
| 2026-11-04 16:06Z, whole stack recreated | Yes (one task per service, all started together) | Failed from the first refresh (16:06:58Z) |
| 2026-11-04 16:23Z, plain `swarmctl deploy app` | No (discovery server task still from ~16:06) | Matched; dispatcher started in AUTO at 16:28:50Z; retrieve and insert passed; no recreate lines; graph shows one bay 7 server |

Every failure so far followed a start in which the discovery server came up together with the
participants. Every pass followed a redeploy with the discovery server already running. The retrieve
isn't the trigger: this run did one and passed.

**Confirming test:** recreate the whole stack (`swarmctl remove app`, then `swarmctl deploy app`),
and within about 30 s check `docker logs "$C" 2>&1 | grep "recreating its client"`. If it's stuck, then
`docker service update --force app-comb_central` (the discovery server keeps running) should recover
it: a workaround, and a confirmation of the cause.

### 1.11 Update, 2026-11-04 20:14Z: a full start that passed

The `app-comb` stack had been removed. After fixing `.env.local` (a `VOLLEY_REGISTRY` override pointing at the
node's local registry, which has no `pr-1018` images), `swarmctl deploy app` created it from scratch at about
20:14:20Z: the discovery server, central, control, bay 7 and noc all started within the same minute. Build
`089e774`.
- After 3 min 24 s: **no** `recreating its client` lines. The REST API matched bay 7.
- `RcvbufErrors` (UDP datagrams dropped because a socket buffer was full): **382 in the central container**,
  all in its first minute (the same count at 1 min and 3.5 min), and **0 in the discovery server**.

So full starts don't always fail: **2 STUCK out of 3** so far. And UDP drops at startup happen even when
everything matches, so drops alone aren't enough. The baseline runs in `plan.md` section 4
should measure the rate and whether STUCK runs have more drops.

### 1.12 Update, 2026-11-04 20:53Z: baseline run 2 STUCK, caught live

Baseline runs with `~/dds_attempt.sh` (full stack recreate each time), build `e1d24a7`:

| Run | Deploy (UTC) | Result | UDP drops central / discovery server |
|---|---|---|---|
| 1 | 20:44:58 | ok | 116 / 0 |
| 2 | 20:53:56 | **STUCK** | 517 / 0 |

Run 2, captured before any restart:
- **The REST API was stuck from its first check.** Its first `recreating its client` line came ~20 s after it
  started (t+30 s after the deploy), then one a minute.
- **Fresh processes match:** `probe_clients.py` in `central` and in `control` got `/bay/b7/confirm_insert`,
  `confirm_retrieve`, `command` and `/central/start` ready in 0.8-1.2 s.
- **The graph is clean:** `probe_graph.py` from `control` shows exactly one server for each bay 7 service
  (one request reader, one response writer, from `/bay/b7/bay_state_machine`). No ghost or duplicate endpoints.
- **Central's C++ process gets bay 7's topics:** the garage tracker subscribed at …647.5 and received bay 7's
  state changes.
- **Simultaneous start:** in both central and bay 7, the entrypoint probe waited ~6 s for the name
  `discovery-server` to resolve (its container was starting too), then both launched within 0.5 s of each other
  (…644.3 bay, …644.8 central). Bay 7 created its services at …646.1, while the REST API was still starting.
- **Drops:** 517 in central (the most so far; the two passing full starts had 116 and 382), all within the first
  20 s; 0 in the discovery server.

Full starts so far: 3 STUCK / 5 (2 of 2 on build `e1d24a7`'s series so far: 1 ok, 1 STUCK).

**The `--spin-time` effect (checked while still stuck, from `control`):** `ros2 service info --no-daemon
--spin-time <t> /bay/b7/confirm_retrieve` prints nothing at 0.1, 0.3 and 0.5 s, and from 1 s on always
`Clients count: 2, Services count: 1`. That's the CLI's own new participant needing about 1 s to learn the
graph from the discovery server, the same as `probe_clients.py`'s 0.8 s. It isn't a client-creation timeout in
the REST API, whose clients waited hours on 11-03 and were recreated every 10 s here without ever matching.
`--verbose` (spin 5 s) for `/bay/b7/confirm_insert` lists the clients `rest_api` (2 endpoints) and
`foxglove_bridge`, and the server `/bay/b7/bay_state_machine`. **So the discovery server knows the REST API's
client endpoints.** What's missing is the REST API's own participant matching bay 7's server endpoints.

**Run 2 recovered on its own** (checked 21:26Z). The REST API's last `recreating its client` line was at
20:56:27Z (1793825787), and none came after. With the one-minute throttle, a still-stuck REST API would have
logged again by 20:57:27, so it matched bay 7 between **20:56:27 and 20:57:27**, about 3 min after it started.
That window contains the script's fresh-process probes: in `central` at ~20:57:01-08 and in `control` at
~20:57:10, right after the 20:57:00 result. Two explanations:
1. it recovers by itself after a few minutes, and the probes coincided
2. a new participant joining nudged it: the discovery server relays a new participant's announcement to every
   super client, the REST API included, which may make its participant reprocess discovery and match

Earlier cases don't decide it: on 11-03 the REST API stayed stuck for over 2 h with nobody probing; on 11-04 at
16:06 it was still stuck 9 min later, then my probes ran and the stack was redeployed at 16:23 before anyone
checked again. **Test on the next STUCK run:** no probes or `ros2` commands for ~10 min, watching the recreate
lines. Then one probe, and see whether recovery follows within a minute.

### 1.13 Update, 2026-11-04 21:35Z: baseline run 3 STUCK, and where the UDP drops happen

Run 3 (deploy 21:35:33Z, build `e1d24a7`): the REST API failed its first check at t+31 s and was still
failing at t+92 s. Central's container dropped **776** UDP datagrams, all within the first 20 s.

| Run | Result | `RcvbufErrors` in central |
|---|---|---|
| 20:14 full start | ok | 382 |
| Baseline 1 | ok | 116 |
| Baseline 2 | STUCK | 517 |
| Baseline 3 | STUCK | 776 |

**Per socket, while run 3 was stuck** (21:39Z, `/proc/net/udp` `drops` column, socket inodes matched to
processes via `/proc/<pid>/fd`; script `udp_drops_by_process.sh`): **all 776 drops were on a single socket
owned by the REST API** (`python3 …/rest_api`, pid 68), local address `0F0310AC:1D00` = 172.16.3.15:7424. No other
process in the container dropped anything. Fast DDS's ports for domain 0: discovery (metatraffic) unicast
7410 + 2 × participant id, user data 7411 + 2 × id. 7424 = 7410 + 2 × 7, so **this is the REST API participant's
discovery socket**.

So during the startup burst the REST API didn't drain its discovery socket fast enough. It's a super client
receiving the whole garage's discovery data, it's Python, and it's busy initialising (database, Twilio,
SendGrid, Flask). The buffer filled, and the kernel discarded discovery messages, presumably including bay 7's
endpoint announcements. That fits H1 and H3 together.

**Still open:**
- why Fast DDS never recovers the lost messages (discovery is meant to be reliable)
- whether the drops on healthy starts are also on the REST API's socket (the per-socket counters reset with the
  container, so record them per run from now on)

**Fix candidates:**
- **(a)** a bigger socket receive buffer in the Fast DDS profile (E2; the container allows up to 4 MiB, the default
  is about 208 KiB)
- **(b)** run the REST API as a plain client (`ROS_SUPER_CLIENT=false` for just that node in
  `launcher/central_nodes.py`). It doesn't need the whole graph, so far less discovery traffic would reach it.

**Run 3 outcome, and a correction.**
- **No self-recovery:** the REST API stayed stuck for 12 min hands-off (last recreate line 21:48:35; 13 lines).
- **It recovered right after one fresh participant:** the probe in `control` started at 21:48:41, and the REST API
  matched between 21:48:35 and 21:49:45 (no recreate line since).

With run 2 (recovered in the minute its probes ran), that's **2 of 2: a joining participant un-sticks the REST
API; waiting alone didn't**. The probe creates clients for the same bay 7 services. A plausible mechanism: on
seeing new endpoints for those topics, the discovery server re-sends bay 7's matching endpoint announcements to
the interested participants, the REST API included, delivering what its overflowed socket lost. To test: a probe
that only creates a client for an unrelated service.

**Correction to "Python is slow to drain":** Fast DDS reads its sockets in its own C++ receive threads, which
don't need Python's GIL, so the REST API's main-thread startup work shouldn't slow them. Why only the REST API's
discovery socket overflows (central's other six processes are super clients too) is still open: launch order
(`rest_api` starts first), or a per-participant difference such as socket buffer size.

### 1.14 Update, 2026-11-04 21:50Z: discovery server restart alone (E1b), and whose sockets drop

**E1b.** With the REST API healthy (after run 3's recovery), `docker service update --force
app-comb_discovery-server` at 21:50:41 (back at 21:50:56, new address 172.16.3.20). For 4.5 min after it: **no
recreate lines**, so the REST API stayed matched. Re-registration caused 66 more drops: 54 on the `ros2 launch`
participant's socket (below) and 12 on the Foxglove bridge's (port 7422). None were on the REST API's own socket.
**A discovery server restart alone doesn't get the REST API stuck (1 of 1).** It takes the full start.

**Which participant is whose** (inode holders from `/proc/<pid>/fd`):
- ports 7410/7411 (participant 0) belong to **`ros2 launch` (pid 7)**. Launch creates its participant before
  starting the processes, and every child inherits copies of those sockets.
- ports 7424/7425 (participant 7) are held **only by the REST API (pid 68)**: its own participant. All 60 of its ROS
  endpoints, the bay 7 clients included, are in that one participant (GID prefix `01.0f.5d.85.44.00.a2.99`).

**So all 776 startup drops in run 3 were on the REST API's own discovery socket**, and the per-process breakdown
is right.

**Why the REST API in particular (likely):** its participant got ID 7, the last in the container, although its
process starts first. Python takes a couple of seconds to import `rclpy`, so the REST API registers with the
discovery server after the other processes. The server then sends it everything already registered, while the
rest of the startup traffic (bay 7 and central's processes announcing themselves) is still arriving. That
combined burst overflows its socket. The C++ processes register earlier and receive the graph more gradually.

**Fix candidates, in order:**
1. **Bigger socket receive buffer** (E2, Fast DDS profile, no build). This targets the overflow itself.
2. **The REST API as a plain client** (`ROS_SUPER_CLIENT=false` for just that node), so the server sends it only what
   it needs. It needs a volley build; E3 tests the idea for all of central without one.
3. **A joining participant fixes a stuck REST API** (2 of 2), as a stopgap only, until the cause is fixed.

### 1.15 Update, 2026-11-04 22:13Z: E2 (4 MiB buffers): no drops, still STUCK

E2 attempt 1, from `~/swarm-exp` (the profile plus `sendBufferSize` / `receiveBufferSize` 4194304 in `udp_overlay`),
deployed 22:13:15Z, build `e1d24a7`. Checked at 22:16:14 inside central:
- **The change is in effect:** `/etc/fastdds/profile.xml` has the two lines, and every Fast DDS socket (7410-7425,
  the REST API's 7424/7425 included) has `rb8388608` (4 MiB requested, doubled by the kernel).
- **No drops:** `RcvbufErrors` 0, the REST API's sockets `d0`.
- **Still STUCK:** recreate lines from t+30 s (3 by t+153 s).

**So the socket overflow is not the cause.** It accompanied the earlier stuck runs, but here the REST API got
stuck with no drops anywhere in central. H1, in the form "the REST API's full socket drops the announcements",
is ruled out.

**Leading hypothesis now:** a Fast DDS discovery race during a full start. The REST API receives (or is sent) bay
7's endpoint announcements in a state where it doesn't act on them, for example endpoint data arriving before the
owning participant's announcement and being discarded, and nothing re-sends them. A new participant creating
endpoints on the same topics makes the server re-send the relevant announcements, which would explain recovery
after a probe (2 of 2). This points at Fast DDS or the discovery server's relaying, not at buffers.

**E2 attempt 1, final:** still stuck after 10 min hands-off (12 recreate lines); one probe in `control` at
22:26:23; recovered between 22:25:25 and 22:26:35. That's **3 of 3** recoveries in the window containing a joining
participant. The window starts 58 s before the probe, so self-recovery just before can't be fully excluded this
time, but three in a row after 10+ stuck minutes makes coincidence unlikely. The other four E2 attempts weren't run:
one stuck run with 0 drops already answered E2.

**Restore and handoff, 22:27:42Z:** `app-comb` redeployed from `/data/swarm` (original profile, `e1d24a7`; sockets
back to `rb212992`). That full start also came up **STUCK** (2 recreate lines by 22:29:59, REST API up 2:07). Comb then went to a teammate for an
unrelated branch; testing resumes 2026-11-05 (`handoff.md`). Full starts so far: 6 STUCK of 8 (on `e1d24a7`:
4 of 5). Next: packet
capture of a stuck start (plan section 6), the "unrelated probe" test, and the plain-client option, which changes
what the server sends the REST API.

### 1.16 Update, 2026-11-04 evening: Codex review (`reviews/codex_dds_review_1.md`), checked

Codex reviewed the investigation independently. Its main points, each checked against the source:
- **Super client is moot (verified).** Fast DDS `versions.md` at v3.6.2, under v3.5.0: "Discovery Server CLIENT
  participants now behave like SUPER_CLIENT participants." So every participant, bays included, receives the
  whole graph. **The "REST API as a plain client" fix is withdrawn**, and H3's super-client framing doesn't apply.
  Sources:
  - release note: https://github.com/eProsima/Fast-DDS/blob/v3.6.2/versions.md (v3.5.0 section, line 8)
  - the change: https://github.com/eProsima/Fast-DDS/pull/6272 ("now both CLIENT and SUPER_CLIENT act as a
    SUPER_CLIENT", merged 2026-01-30)
  - the docs' comparison table: https://fast-dds.docs.eprosima.com/en/latest/fastdds/discovery/discovery_server.html
    ("Discovery Server and Discovery Server Pro": open source, "None in practice, as every client already receives
    everything the server knows"; only Pro filters for a plain CLIENT)
  - the code: the server's `DiscoveryDataBase.cpp` checked `is_superclient()` when relaying in v3.4.0
    (https://github.com/eProsima/Fast-DDS/blob/v3.4.0/src/cpp/rtps/builtin/discovery/database/DiscoveryDataBase.cpp#L1216,
    #L1297) and has no super-client reference at all in v3.6.2
    (https://github.com/eProsima/Fast-DDS/blob/v3.6.2/src/cpp/rtps/builtin/discovery/database/DiscoveryDataBase.cpp)

  Comb's images use `ros-lyrical-fastdds 3.6.2` from the ROS apt snapshot, the open-source build, not Pro.
  Consequences: `ROS_SUPER_CLIENT` is redundant on Lyrical (volley `docker/Dockerfile:570,578` and
  `docs/architecture/discovery-server.md`, which still explains it as giving central a fuller view, predate Fast DDS
  3.5). The bays, set up as plain clients, receive the whole graph too. Every participant gets the same discovery
  data, so what singles out the REST API must be something else: when it joins, or how it processes what it gets.
- **Readiness has two parts (verified, rmw_fastrtps 9.4.9 `rmw_service_server_is_available.cpp`):** nonzero, equal
  graph-cache counts (request readers vs reply writers) **and** nonzero, equal local match counts. Our detector can't
  tell which one fails.
- **The H7 mechanism exists (verified, Fast DDS v3.6.2 `EDPSimpleListeners.cpp` ~114-133):** endpoint data from a
  participant not yet known is dropped with `EPROSIMA_LOG_WARNING(RTPS_EDP, "Received message from UNKNOWN
  RTPSParticipant, removing")` and removed from the history. Fast DDS prints only errors by default, so this warning
  would never have appeared in our logs; no saved log contains any `RTPS_` warning.
- **Fair corrections to our reasoning (agreed):**
  - The probe was a compound intervention: the entrypoint's raw discovery-probe participant, then an rclpy node with
    four clients. Recovery "3 of 3" is a temporal association, not proof of cause, and not evidence for same-topic
    interest specifically.
  - Recovery windows are inferred from the absence of a throttled log line (+60 s throttle +10 s tick). They need a
    positive transition logged instead.
  - E2 rules out central's receive-buffer overflow as *necessary*, not all packet loss (the server, bay host, VXLAN
    and sender side weren't measured).
  - Participant ID 7 reflects local socket-creation order, not server registration order. "Registers last" is
    plausible but unproven. The delay isn't attributable to rclpy imports alone: the database and auth setup run
    before `rclpy.init()`.
  - E1b showed existing matches survive a server restart, not that new endpoints are discovered afterwards.
  - The DNS question: the probe resolves `discovery-server` once; each process resolves it again; the server's task
    address changes on restart, while clients may reach a service VIP. Check what each process actually uses.
- **Upstream leads (verified to exist):** PR #6542 (volatile reader desync after an initial GAP, merged
  2026-09-23); issue #6594 (permanent one-direction match loss after an unanswered TypeLookup; open). The latter
  resembles our symptom, but type propagation is off here. There's no public Fast DDS 3.6.3; 3.7 is Pro.

### 1.17 Update, 2026-11-05 00:58Z: the diagnostic build deployed (plain redeploy, ok)

Comb had been running the teammate's `bay-refactor` build (central `GITSHA=84f6deb`, full start at about 22:50Z on 11-04).
`.env.local` already had `VOLLEY_REGISTRY` uncommented; `VOLLEY_VERSION` was set to `dds-diag-29712d9` and `swarmctl deploy
app` run at 00:58:07Z (a plain redeploy: the discovery server task from 22:50Z kept running). A first `swarmctl deploy`
over a non-interactive ssh failed before changing anything with `required variable NFS_HOSTNAME is missing a value`;
`export HOSTNAME=$(hostname)` fixes it (plan 4.3).

- `GITSHA=29712d9` in central; bay7, control and central tasks on the `dds-diag-29712d9` images.
- **The diagnostics work in place.** `[dds-diag] ... pid=68 fastdds verbosity=1 (1 = Warning)` at 00:58:21Z; the REST
  API process maps exactly one `libfastdds` (`/opt/ros/lyrical/lib/libfastdds.so.3.6.2.0`), so the `SetVerbosity` call
  reached the library rmw uses. Then `check-start n=1` / `heartbeat n=1 took_ms=1 not_ready=-` one second later, and
  one pair per second since (n=33 at 00:58:54Z, same PID).
- **Both bay 7 services were ready at the first check** (`ready=1 rq_readers=1 rr_writers=1`, request-reader GIDs
  `010f5950340041ea...2504` / `...2804`, reply-writer GIDs `...2603` / `...2903`, all one participant prefix), consistent with
  every plain redeploy so far.
- **Fast DDS warnings do reach the log** (the check E8 asked for), two of them in the first second of the participant,
  both from the REST API process and before its first check:
  - `[UTILS Warning] Cannot get machine id. Failing back to IP based ID -> Function Host` (00:58:21.309Z)
  - `[RTPS_TRANSPORT_SHM Warning] Buffer is being invalidated, segment_size may be insufficient -> Function
    invalidate_if_not_processing` (00:58:21.936Z)

  Neither is the `RTPS_EDP` UNKNOWN-participant line. The first is the host-ID fallback Codex's upstream table mentions
  (Fast DDS issue #6524: with an IP-based host ID, SHM locators can be chosen across hosts; here the bays are on another
  machine). The second says an SHM segment buffer was invalidated because the segment was too small, in a healthy start.
  Both are new facts for H4 (transport mix), not yet evidence of anything: they need the same lines from a stuck start
  to compare, and the warnings file of each attempt records them. The warnings' colour codes are ANSI escapes; strip
  them with `sed 's/\x1b\[[0-9;]*m//g'` when grepping.
- No attempt has run yet on this build; the scripts aren't installed on comb (`~ops` is clean).

### 1.18 Update, 2026-11-05 02:01Z: first full start on the diagnostic build (diag1): ok

`dds_attempt_diag.sh diag1` as a `systemd-run --user` unit (`dds-diag-1`, `HOSTNAME` exported); scripts installed
with matching checksums. Removed 02:01:24Z, deployed 02:01:52Z, result at 02:04:56Z. Raw files in
`results/2026-11-05/logs/`.

- **Result `ok`:** the REST API's first check at 02:02:04Z (11 s after the deploy, 1 s after the verbosity read-back)
  already had both bay 7 services `ready=1 rq_readers=1 rr_writers=1`; 173 heartbeats by the judgment, `took_ms=0-1`,
  one PID (68), no not-ready service. So in a healthy full start the match completes while the REST API is still
  starting, before the monitor's first query. Full starts: 6 STUCK of 9.
- **Drops without a stuck state:** 288 `RcvbufErrors` in central in the first 20 s, 268 of them on the REST API's own
  discovery socket 7424 (buffers at the default `rb212992`, this stack runs the original profile), 0 in the discovery
  server. Consistent with E2's conclusion: the overflow happens in healthy starts too.
- **The same two Fast DDS warnings** as in the plain redeploy (findings 1.17), again in the REST API's first second
  (02:02:03.254 host-ID fallback, 02:02:03.859 SHM `segment_size`), and nothing else. So they're part of every start of
  this process, not a stuck-start signature. No `RTPS_EDP` line.
- **Script bug found:** `dds_attempts.log` says `fastdds_warnings=0` and the warnings file is empty, though two
  warnings were in the log. Fast DDS colours its lines, and the ANSI escapes sit between `[` and `UTILS`, so the
  pattern `\[[A-Z0-9_]+ (Warning|Error)\]` never matched raw `docker logs`. Fixed in `save_warnings` (strip
  `\x1b\[[0-9;]*m` first; tested offline on a raw coloured line) in `results/2026-11-04/scripts/` and
  `results/2026-11-05/scripts/`. **The copy on comb is still the old one** until re-copied. The `warnings_on=1`
  and `unknown_participant` fields are unaffected (the first greps `[dds-diag]`, the second the file).
- `swarmctl` over a non-interactive ssh needs `export HOSTNAME=$(hostname)` (1.17); the unit sets it with `-E`.

### 1.19 Update, 2026-11-05 02:10Z: diag2, the first STUCK start seen from inside the stuck process

`dds_attempt_diag.sh diag2` (unit `dds-diag-2`, fixed warnings grep re-copied, checksum matched). Removed 02:09:57Z,
deployed 02:10:24Z, STUCK at 02:13:29Z, 10 min hands-off, probe 02:23:32Z, recovered 02:23:33Z. Raw files in
`results/2026-11-05/logs/` (`dds_diag_2.out`, `central_diag_diag2_recovery.txt`, the warnings file).

- **While stuck, the REST API's own graph cache had no bay 7 endpoints:** from its first check (02:10:36.997Z, 12 s
  after the deploy) both services read `ready=0 rq_readers=0 rr_writers=0 rq_gids=- rr_gids=-`, and that state line never
  changed for 777 s. Not "known but unmatched": **never learned.** The heartbeat ran every second throughout (n=1 to
  about 778, `took_ms` 0-1, one PID 68), so the executor and the timer were fine; nothing blocked.
- **No Fast DDS warning beyond the two of every start** (`fastdds_warnings=2`, `unknown_participant=0`, verbosity read
  back 1). With logging confirmed on in the stuck process, the `EDPSimpleListeners` "UNKNOWN RTPSParticipant"
  rejection path **did not fire** in this run, and no "Maximum number of … proxies" either. That's the E8 table's
  "strong evidence against this rejection path in that run". H7 as a failed-proxy-add race is out for diag2; what
  remains of H7 is the weaker form: the endpoint data for bay 7 never got as far as the REST API's EDP processing, or was
  discarded by a path that doesn't warn (reliability / sequence state, for example).
- **Recovery, now with a positive transition:** the single-process probe in `control` (four clients, no entrypoint
  participant) started 02:23:32Z; its clients were ready after 0.8 s; the REST API's check at 02:23:33.997Z showed
  both services `ready=1 rq_readers=1 rr_writers=1` with bay 7's endpoint GIDs (prefix `010f913b34000e4b`, request
  readers `…2504`/`…2804`, reply writers `…2603`/`…2903`). Both services arrived in the same 1 s check. **4 of 4**
  recoveries with a joining participant, this one within 1-2 s of the join and after 10 min of nothing. Still an
  association, but a tight one; the probe still carries same-topic clients, so the unrelated-probe arm is next.
- 598 `RcvbufErrors`, all on the REST API's 7424 (default buffer), 0 on the server; diag1 (ok) had 268. Still not a
  discriminator on its own (E2).
- Capture options checked (read-only): `ops` may run `/usr/bin/tcpdump` as root without a password (`sudo -l`), but not
  `nsenter`; no `tcpdump` in the central image; no capture image on the host; `ops` is in the `docker` group. So a
  capture inside central's network namespace needs a sidecar (`docker run --rm --net container:<central> <image with
  tcpdump>`), which adds no DDS participant; the host can see only the VXLAN side (`eth0`, UDP 4789: bay 7 ↔ central
  host), not the central ↔ discovery-server traffic, which stays inside the overlay namespace on this host.
- Full starts: 7 STUCK of 10 (diag build: 1 of 2).

### 1.20 Update, 2026-11-05 02:54Z: build `4b00571` deployed (bay graph line), v3 script, diag3 ok

- **Commit `4b005718`** on the investigation branch adds a `change /bay/b7 nodes= topics= publishers= participants=` line:
  what the REST API's own graph holds of bay 7 beyond the two service endpoints (nodes under `/bay/b7`, topics under it,
  remote publishers on them, and the publishers' 12-byte participant prefixes). Built on the laptop as `dds-diag-4b00571`
  (the push first failed because `central-comb` stopped resolving off the garage LAN; a hosts line fixed it), deployed at
  02:53:54Z as a plain redeploy, `GITSHA=4b00571`. The `29712d9` tags are still in the registry (deletion pending).
- **Healthy reference values:** `nodes=7 topics=20 publishers=24 participants=<2 prefixes>` within 12 s of the deploy,
  growing to `8/24/31` as bay 7 finishes starting; the check takes 2-5 ms. Bay 7 is two participants (the state machine
  and its component container).
- **diag3 (v3 script, unit `dds-diag-3`):** removed 02:54:47Z, deployed 02:55:15Z, **ok** at 02:58:22Z: both services and
  the bay line full at the first check (02:55:27.6Z). 324 `RcvbufErrors` in central, 146 on 7424. The same two warnings.
- **The v3 machinery works:** host capture (`eth0`, VXLAN) from before the removal; the central sidecar capture started
  2 s after the deploy (before the REST API's participant existed, 11 s later); both stopped by the finish trap; ~20 MB
  (central) and ~17 MB (host) for 3.5 min, so a STUCK run of 17 min is ~100 MB each, well under the 4 x 500 MB cap.
  Full logs of central and the server saved per run. The server's log is three lines (GUID prefix `01.0f.60.29.01.00.1e.2d`,
  `UDPv4:[172.16.3.13]:11811`). Raw files and the two pcaps in `results/2026-11-05/` (`captures/` holds 37 MB of
  pcaps as the healthy reference; decide whether they belong in the notes repo).
- Full starts: 7 STUCK of 11 (diag builds: 1 of 3).

### 1.21 Update, 2026-11-05 03:02Z: diag4 ok

Unit `dds-diag-4`: removed 03:02:22Z, deployed 03:02:50Z, **ok** at 03:05:57Z; captures 20.1 MB / 16.4 MB (left on comb), full
logs saved. 1178 `RcvbufErrors` in central, 874 on the REST API's 7424: the most drops of any start, healthy. The first bay
line read `nodes=7 topics=20 publishers=0 participants=-` and the next second `publishers=24` with both prefixes: the
graph queries aren't atomic, so one odd bay sample is a transition, like the service line. Full starts: 7 STUCK of 12
(diag builds: 1 of 4).

### 1.22 Update, 2026-11-05 03:08-04:03Z: loops; diag15 STUCK shows a whole missing participant; a bare node heals it

- **Loop 1, captures on, build `4b00571`:** diag5-12 all ok (with diag3-4: 10 of 10). **Loop 2, captures off (`CAPTURE=0`),
  same build:** diag13 ok, diag14 ok, **diag15 STUCK** (03:49:31Z deploy, judged 03:52:36Z). Captures on 0 of 10, captures off
  1 of 3: suggestive that the captures (the sidecar in central's namespace, or promiscuous `eth0`) shift the timing, not
  established. Full starts: 8 STUCK of 23.
- **What the stuck REST API knew of bay 7 (the new bay line):** `nodes=1 topics=18→24 publishers=3
  participants=010f2cbd3500ab11…` from its first check (03:49:43Z) for 13 min, against `nodes=7-8 topics=20-24
  publishers=24-31` and **two** participant prefixes on every healthy start. Bay 7 is two participants: `…34…` is the
  state machine's (it owns the confirm services and most publishers), `…35…` the component container's. **The stuck
  process knew the `…35…` participant completely and the `…34…` participant not at all:** no node name, no publisher, no
  service endpoint. So the miss is a whole remote participant (its DATA(p) and everything that follows), not a lost
  endpoint announcement. Consistent with no `RTPS_EDP` warning: endpoint data for an unknown participant would have
  logged one, so that data never arrived either. The topic count still grew (18→24): topics are known through central's
  own endpoints and the other bay participant.
- **The unrelated probe heals it (1 of 1):** after 10 min hands-off unchanged, one rclpy node **with no clients** in
  `control` (04:02:38Z) was followed within 2 s by the REST API's check showing the `…34…` participant with everything:
  `nodes=8 publishers=31`, both services `1/1`, `ready=1` (04:02:40.888Z). The clients probe never ran. **Any new
  participant repairs it; same-topic interest isn't needed** (5 of 5 recoveries with a joining participant; this one
  with no bay interest at all).
- **Reading:** the server has the `…34…` participant (fresh participants see it at once) and the REST API's participant
  never received it, until a new participant's registration made the server's discovery writer send again, after which
  the REST API caught up on everything it had missed. The shape is a reliable discovery stream between the server and
  one late client participant that silently lost samples and had nothing to resynchronise it. Fast DDS PR #6542 ("initial
  GAP can desynchronize a volatile late reader", merged 2026-09-23 on `3.6.x`, not in any release) describes a mechanism
  of this shape; the REST API is central's last participant to register. Not proven: a capture of a stuck start would
  show whether the server sent the DATA(p) and what the REST API acknowledged, and the captures seem to suppress the
  failure.
- 600 `RcvbufErrors`, all on 7424, 0 on the server; the socket list now shows `7427` as the REST API's user port (ID 8,
  the capture sidecar's absence shifts nothing; participant IDs vary per start).
- **Watchdog build deployed** at 04:03:54Z (`dds-diag-25f354b`, branch `jmg/test/rest-api-dds-watchdog`, commit
  `25f354bc`): healthy start, no trip. Loop `dds-loop-16` (diag16-25, captures off) started 04:04:34Z; the loop also stops
  on a second REST API PID in the result line, since a watchdog restart makes the start look ok by 180 s.

---

## 2. AGVs reported as "carrying t0"

### 2.1 What was observed

```
[central-3] [INFO] [1793741647.440576245] [central.garage_tracker]: GarageTracker::AgvReportCallback  a17 pose changed: node 10@90 -> node 8@90 (carrying t0)
```

This appeared on the first pose report after the AGV localized, before any order ran. The proxy's
pose line in the same second says `lifted=down`, and a16 showed the same thing. The scheduler then
logged `Setting safe intervals for event a17, t0`.

### 2.2 `t0` means "no tray"

Tray id 0 is the sentinel for "not carrying", used across the garage state:

- `common_ros/src/discrete_garage_state.cpp`: every carried-tray check is `tray_id != 0` or
  `tray_id == 0` (lines 972, 1046, 1101, 1140, 1480, 1501, 1635).
- `common_ros/src/print_utils.cpp:256`: the state printer writes `" No tray"` when `tray_id == 0`.
- `common_ros/test/discrete_garage_state_tests.cpp:746, 790`: `EXPECT_EQ(0, ...tray_id); // not carrying`.
- Central sets `event.tray_id = 0` for an AGV whose tray is unknown (`central/src/garage_tracker.cpp:219`).

No real tray can have id 0, so `t0` is never "a tray defaulting to 0 that is treated as real".

### 2.3 Where the two log lines come from

**Central** (`src/central/src/garage_tracker.cpp:249-259`):

```cpp
INFOS(logger_, "GarageTracker::AgvReportCallback  a"
                   << report->agv_id << " pose changed: node " << event.node_id_curr << "@"
                   << event.heading_curr << " -> node " << event.node_id_next << "@"
                   << event.heading_next << " (carrying t" << agv.tray_id << ")");
ApplyAndPublishEventOrFault(event);
if(agv.tray_id != 0) {
  ... "t" << agv.tray_id << " carried by agv " ...
}
```

It prints `agv.tray_id` whatever its value. The very next check treats 0 as not carrying, and the
"carried by agv" line didn't appear, which confirms that. The line dates from `ec40043f` (2026-08-13,
"update tray and agvs to new vrc nodes after riding a vrc") and is on `main`.

**Motion planner** (`src/planner/motion_planner/src/chugg_sequential.cpp:562-563`):

```cpp
INFOS(logger_, "Setting safe intervals for event " << std::to_string(volley::AgvId(event_agv)) << ", "
                                                   << std::to_string(volley::TrayId(event_tray)));
```

`event_tray` is 0 for an AGV-only move, and it's printed raw. The line has been on `main` since `52f1317c`
(2026-04-30), and this branch doesn't change it.

### 2.4 The scheduler renames don't change the meaning

This branch replaced each `agv.tray_id != 0` in the scheduler with `IsCarryingTray(agv)`, defined as
(`src/planner/scheduler/src/utils.cpp:46-47`):

```cpp
bool IsCarryingTray(const interfaces::msg::DiscreteAgvState& agv) {
  return agv.tray_id != 0;
}
```

The one removed `if(agv_opt->tray_id == 0)` (AGV move expansion) became the `if(IsCarryingTray(agv))`
branch in `job_expansion.cpp:123-149`. A loaded AGV gets a `TrayMove`, and an unloaded one still gets an
`AgvMove` (`MakeAgvPoseMove`). The recorded scenarios, which compare every planned event, are
unchanged across all seven commits. Central's tracker, where the log line comes from, is unchanged
anyway.

### 2.5 Fix

None needed: the AGVs are correctly tracked as unloaded. To make the logs clearer, print "no tray"
when the id is 0, as `print_utils.cpp:256` already does, in `garage_tracker.cpp:252` and
`chugg_sequential.cpp:563`.

The one check, if wanted: in the same plan, a17's first event should be an `AgvMove` with no tray. In
the snapshot, its `DiscreteAgvState.tray_id` should be 0 and `lift` false.
