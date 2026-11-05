# Finding the DDS root cause of the stuck REST API

**Goal.** Find why, after some starts, the REST API's DDS participant can't match bay services that
exist, and fix it where it starts, so no process (Python or C++) can come up that way.
Background: `findings.md` sections 1.9 and 1.10. Commands:
`../../garage/troubleshooting_reference.md`.

## 1. What we know (2026-11-04)

**Status after the baseline so far (findings 1.11-1.14):**
- **Full starts:** 3 STUCK of 5 (build `e1d24a7`: 2 of 3).
- **The overflow:** in stuck runs, the REST API's **own discovery socket** (port 7424, its participant ID 7) overflows
  at startup: 517 and 776 `RcvbufErrors`, against 116 and 382 on healthy starts. Every DDS socket in central has the
  Linux default receive buffer, 212,992 bytes (`ss -uamn`: `rb212992`). Fast DDS requests no size; the container
  would allow up to 4 MiB.
- **Why the REST API:** its participant registers last in the container (Python import time) and gets the server's
  full graph on top of the startup burst.
- **Recovery:** waiting doesn't help (12 min); a new participant joining un-sticks it (2 of 2).
- **E1b:** a discovery server restart alone doesn't cause it (1 of 1).
- **E2 (4 MiB buffers), 22:13Z:** buffers in effect (`rb8388608`), **0 drops, still STUCK.** So the overflow
  isn't the cause (findings 1.15).
- **E2 final:** recovered right after the probe (3 of 3 recoveries with a joining participant). The restore's full
  start at 22:27:42 was STUCK too: 6 STUCK of 8 full starts.
- **Paused** 2026-11-04 22:30Z (comb lent for unrelated testing), resuming 2026-11-05 (`handoff.md`).
- **Next:** packet capture of a stuck start, the "unrelated probe" test,
  and the REST API as a plain client.

- **The symptom.** The REST API (`rest_api`, Python, in the `central` container) can't match bay 7's
  `confirm_insert` / `confirm_retrieve` service endpoints. Recreating its clients doesn't help. A new
  Python process in the same container matches them in under 1.2 s. So the REST API process's single
  DDS participant is stuck.
- **When.** Each failure followed a start in which the discovery server came up together with the
  participants: the node boot on 2026-11-03 (~18:25Z) and the full stack recreate on 2026-11-04 at 16:06Z.
  Each pass followed a plain redeploy with the discovery server already running (00:48Z and 16:23Z),
  including a retrieve and an insert. Two failures and two passes, so a pattern, not yet a proof.
- **It has happened before.** swarm-deploy's README ("Fast DDS profile") describes the same thing:
  when a whole stack starts at once, discovery traffic "floods UDP and overflows socket buffers"; "a
  dropped reply leaves its endpoint pair unmatched, and Fast DDS never retries it". In practice "a single
  service like `/bay/b7/command` that never matched". Dan's fix was to disable type propagation (swarm-deploy
  `a92d7ed`, 2026-10-09). Comb's release (`c9b6529`) includes it, and the container's profile has it, but
  the failure still happens. So that fix wasn't complete, or the trigger is something else. Dan tested his
  fix with 5 stack restarts (swarm-deploy PR #54) and 40 local CI runs (volley PR #972), so a failure that
  happens only some of the time could have slipped through.
- **The discovery server keeps its state in memory only.** No backup mode and no volume, so every
  restart begins with an empty database, rebuilt only as participants register. On a full start the
  server's database and every participant begin from zero at the same moment.
- **Not every full start fails.** On 2026-11-04 at 20:14Z a stack created from scratch matched fine, with 382
  UDP receive-buffer drops in central's container in its first minute and 0 in the discovery server
  (findings 1.11). So far 2 of 3 full starts were STUCK.
- **What the graph looks like during a failure.** A fresh process (in `central` or `control`) sees bay 7's
  services, with one server and matching endpoint counts (`probe_graph.py`), and matches them in about 1 s
  (`probe_clients.py`). Central's C++ processes receive bay 7's topics, and the Foxglove bridge (also in
  central) shows them.
- **Not known yet:**
  - whether C++ processes get stuck too (central's C++ nodes received bay 7's *topics* during the failure,
    but nobody tested a C++ *service* client)
  - whether it's UDP loss, the start order, the super-client mode, the transport mix, or a Fast DDS bug
- **CI can't catch it.** The system tests run without a discovery server
  (`.github/actions/system-tests-group/action.yml`: `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` and a
  profile that only disables type propagation).

## 2. How DDS is set up, and where each piece lives

```
                      swarm-deploy (stack files, profile)          ros2-docker (base images)
                      ─────────────────────────────────          ─────────────────────────
discovery-server ──── support.yaml: fast-discovery-server 42 ───── Dockerfile stage discovery-server
   (app stack,          -l discovery-server -p 11811                (Fast DDS 3.6.2)
   central node)
central container ─── main.yaml: ROS_DISCOVERY_SERVER,       ┐
   (super client)       FASTDDS_DEFAULT_PROFILES_FILE,       ├─ config/fastdds-profile.xml
                        configs: fastdds-profile             │   (SHM + UDP on overlay0 only,
bay<N> container ──── bay.yaml.j2: same env and config       ┘    type propagation disabled)
   (plain client)
                      volley (images): Dockerfile ROS_SUPER_CLIENT=true for central/control,
                      RMW_IMPLEMENTATION=rmw_fastrtps_cpp; entrypoint.sh runs discovery_probe
```

| Repo | File | What it decides |
|---|---|---|
| **swarm-deploy** | `swarm/stacks/app/support.yaml` | The `discovery-server` service: image `ros2:lyrical-discovery-server-20260911`, command, overlay network (`ifname: overlay0`), UDP port 11811 published in host mode. **It's in the `app` stack, so it restarts with every stack recreate.** |
| | `swarm/stacks/app/main.yaml` | `central` and `control`: `ROS_DISCOVERY_SERVER`, `FASTDDS_DEFAULT_PROFILES_FILE`, the `fastdds-profile` config |
| | `swarm/stacks/app/bay.yaml.j2` | The same for each `bay<N>` |
| | `swarm/stacks/app/config/fastdds-profile.xml` | The Fast DDS profile: transports and type propagation |
| | `swarm/.env` | `DISCOVERY_SERVER_HOST=discovery-server`, `DISCOVERY_SERVER_PORT=11811` |
| | `x-internal-network` in each stack file | Joins services to the `internal` overlay and names the interface `overlay0` (`com.docker.network.endpoint.ifname`), which the profile's allowlist refers to. Containers also get `eth0` on the host-local `docker_gwbridge`. On comb: central 172.16.3.5, discovery server 172.16.3.3 |
| | `README.md`, "Fast DDS profile" | Why the profile exists; history in `0d2054b` (overlay-only, 2026-10-02) and `a92d7ed` (type propagation, 2026-10-09) |
| **ros2-docker** (GitHub `VolleyAutomation/ros2-docker`, not cloned here) | `Dockerfile`, stage `discovery-server` | The server image: `CMD ["fast-discovery-server", "42", "-l", "0.0.0.0", "-p", "11811"]`, a health check (a listening socket only); history in `b8491a4c` ("discovery server entrypoint and health check based on DDS 3 changes") |
| | `Dockerfile`, stages `core`/`base` | The ROS snapshot date, which fixes the Fast DDS version (`ROS_SNAPSHOT_DATESTAMP=2026-08-19`: `fastdds 3.6.2`, `rmw-fastrtps 9.4.9`) |
| **volley** | `docker/Dockerfile` | `runtime-central` / `runtime-control`: `ROS_SUPER_CLIENT=true`; all runtime images: `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` |
| | `docker/docker-bake.hcl` | Which base images (`ros2:lyrical-core-20260924-1`, …) the runtime images use |
| | `docker/resources/entrypoint.sh` | Runs `discovery_probe` before `ros2 launch` |
| | `src/infrastructure/dds_discovery/src/discovery_probe.cpp` | Waits until the server's hostname resolves (Fast DDS "silently falls back to simple discovery" otherwise) and one throwaway participant gets an answer. It checks the server once per container, not per process. |
| | `src/launcher/launcher/central_nodes.py` | Starts `rest_api` first, then the component container |
| | `src/central_api/central_api/rest_api.py` | The REST API's clients; `refresh_bay_clients` (`073556ea`, `089e774d` after the rebase) logs when a bay client is unmatched |
| | `docs/architecture/discovery-server.md` | The repo's own description: which images are super clients and why (central for the Foxglove bridge, control for `ros2` CLI debugging) |
| **vng-os** (`~/repos/vng-os`) | | The device OS. It sets no UDP buffer sysctls (`net.core.rmem_*`). Inside the central container `rmem_max` is 4 MiB, `rmem_default` 208 KiB. |

## 3. Hypotheses

| # | Hypothesis | Fits | Doesn't fit yet |
|---|---|---|---|
| H1 | **UDP loss during a mass start** drops a discovery message that Fast DDS doesn't recover (the README's explanation, with a path type propagation didn't cover) | Only full starts fail; the README saw the same symptom | No drop counts measured during a failure |
| H2 | **Start order:** participants register while the discovery server itself is just starting (its in-memory database empty), and the server never relays some endpoints to them | Every failure had the server starting at the same moment | Plain redeploys also start central and the bay together, and they pass |
| H3 | **Super client:** the central container's participants receive the whole swarm's discovery data, a bigger burst at start, and Python's slower discovery thread loses some of it | Only `rest_api` (Python, first to start) is known stuck | Untested for C++; fresh Python participants are fine |
| H4 | **Transport mix:** SHM between processes in one container, UDP on `overlay0` to other hosts; a locator or transport choice goes wrong at start | The profile was changed recently (`0d2054b`) | No direct evidence |
| H5 | **A Fast DDS 3.6.2 bug** in client/server discovery after a server (re)start | The README's "never retries" | Need the release notes of newer 3.6.x / 3.7 |
| H6 | **The discovery server isn't covered by the profile.** In `support.yaml` the `discovery-server` service has no `FASTDDS_DEFAULT_PROFILES_FILE` and no `fastdds-profile` config, so it runs with Fast DDS's builtin transports (every interface, `docker_gwbridge` included) and default type propagation, unlike every other participant since `0d2054b` / `a92d7ed`. Type propagation hardly matters for the server (it has no user endpoints); its transports and advertised addresses might | The fixes of 2026-10-02 and 10-09 changed only the clients | Its log shows it listening on the overlay address (`172.16.3.3:11811`); not tested whether it advertises other addresses |

They aren't exclusive: H1 and H2 can both be true (the burst is biggest when the server and everyone
start together).

**Status (2026-11-04 22:00Z):**
- **H1, ruled out as the cause:** the REST API's socket overflowed in earlier stuck runs, but with 4 MiB buffers it got
  stuck with zero drops (E2).
- **New leading hypothesis, H7:** a discovery race, with bay 7's endpoint announcements reaching the REST API when it
  doesn't act on them and never re-sent. The mechanism exists in Fast DDS 3.6.2 (`EDPSimpleListeners.cpp`: endpoint data
  from an unknown participant is dropped, logged only as a warning, which isn't printed by default). Recoveries after a
  joining participant (3 of 3) are an association, not proof (findings 1.16).
- **H3, moot:** in Fast DDS ≥ 3.5.0 a CLIENT behaves like a SUPER_CLIENT (verified in `versions.md`), so super-client
  mode changes nothing. The plain-client fix is withdrawn (findings 1.16).
- **H2, a full start is needed:** a discovery server restart alone didn't cause it (E1b).
- **H4, H5 and H6:** untested.
- **diag2 (2026-11-05, findings 1.19):** in a stuck start with Fast DDS warnings confirmed on, the REST API's own graph
  cache never had bay 7's endpoints (`0/0` for 777 s) and **no `RTPS_EDP` warning appeared**, so H7's failed-proxy-add
  branch is out for that run. The data never reached EDP processing, or was dropped by a silent path. One rclpy process
  joining in `control` made both services appear in the REST API's graph within 1-2 s (4 of 4). Next: the unrelated-probe
  arm and a capture inside central's network namespace (sidecar; `ops` has `sudo tcpdump` but no `nsenter`, section 6).

## 4. The test setup

### 4.1 Where

On comb, at a time when nobody else is running orders or tests there. Each attempt takes about 3.5 min,
but the garage is only down for about 1-1.5 min of it:
- `remove` plus a 20 s pause, with **every** `app-comb` service stopped
- the services starting (30-60 s)
- the rest is the script waiting to judge, with the stack up

It's a full restart, not the usual central-and-bay one: the discovery server, control, noc, mysql and nginx
restart too, because that's the condition that fails. Each time, central comes back with the dispatcher
stopped, and any job in progress is failed. 5 attempts take about 18 min. Keep `BAY_IDS_OVERRIDE="7"`
(one bay is enough).

**Comb must run a build with the detector** (next section). As of 2026-11-04 ~18:30 node time, someone
switched comb to `VOLLEY_VERSION=bay-refactor` (`84f6deb`), which doesn't have it. Agree with that person,
set `VOLLEY_VERSION=pr-1018` in `/data/swarm/.env.local` (after the rebased branch is pushed and CI's
`runtime-images` job passed), check `GITSHA` after the first deploy (`../../garage/troubleshooting_reference.md`
section 3), and put their version back at the end.

### 4.2 The detector

The detector is the REST API refresh from `073556ea` (now `089e774d` on the rebased branch). It logs
`/bay/b7/confirm_… not discovered, recreating its client` every minute while the REST API is stuck,
without needing a vehicle in the bay. **If that commit is reverted from PR #1018, keep it on a separate
investigation branch** and deploy that branch's images (`VOLLEY_VERSION=pr-<n>` of a draft PR), or there's
no way to see the failure without a real confirm-insert. You can also watch the line live in Foxglove: a
Log panel on `/central/rosout` (reference section 14). **Stuck** = that line still appears from 90 s after the deploy on. **Healthy** =
no line, or one line in the first 60 s and then nothing.

For the C++ side, start the dispatcher (NOC, or FoxNOC's Garage Control panel: Auto, then Status on) and
look for `Received response from b7` after `Sending type 1 command to b7` in central's log. If it's missing in
a stuck run, C++ is affected too.

### 4.3 One attempt, scripted

Save as `~/dds_attempt.sh` on the node (`ops`). The latest copy, with the probe scripts and the day's logs, is in
`results/2026-11-04/` (comb was cleaned up on 2026-11-04 at 22:35Z). It recreates the stack, prints a
status line every 10 s (services up, REST API uptime, recreate lines so far, UDP drops in central), then
records the result and the UDP drop counters and appends one line to `~/dds_attempts.log`:
```bash
#!/usr/bin/env bash
# One full-restart attempt: recreate app-comb, watch it come up, record whether rest_api is stuck.
# On STUCK: watch hands-off for 10 min (does it recover by itself?), then start one fresh participant
# in control and watch 2 min more (does a joining participant make it recover?).
set -u
label="${1:-baseline}"
# SWARM_ROOT=<dir> deploys from a copy of /data/swarm (for experiments that edit stack files without root).
swarm_root="${SWARM_ROOT:-/data/swarm}"
swarmctl=(/data/swarm/bin/swarmctl --root "$swarm_root")
hands_off=600
after_probe=120
say() { echo "[$(date -u +%T)] $*"; }
log() { echo "$*" | tee -a ~/dds_attempts.log; }
udp_drops() { docker exec "$1" awk '/^Udp:/{n++; if (n==2) {print $6; exit}}' /proc/net/snmp 2>/dev/null; }
recreates() { docker logs --since "$start" "$1" 2>&1 | grep -c 'recreating its client'; }
# The REST API's own Fast DDS sockets (not the ones inherited from ros2 launch): port:rb<buffer>/d<drops>.
rest_api_sockets() {
  docker exec "$1" ss -uamnp 2>/dev/null | awk '
    /users:\(\("rest_api"/ && !/\),\(/ { n = split($4, a, ":"); port = a[n]; getline
      if (port !~ /^74[0-9][0-9]$/) next
      match($0, /rb[0-9]+/); rb = substr($0, RSTART, RLENGTH)
      match($0, /d[0-9]+\)/); d = substr($0, RSTART, RLENGTH - 1)
      printf "%s:%s/%s ", port, rb, d }'
}

last_line() { docker logs -t --since "$start" "$1" 2>&1 | grep 'recreating its client' | tail -n 1 | awk '{print $1}'; }

# Watches rest_api for $2 seconds. A stuck rest_api logs a recreate line at least every 70 s, so 75 s
# without a new line means it matched, sometime in the 70 s after its last line. Sets $recovered_at to
# that last line's time (Unix seconds), or leaves it empty if it's still stuck at the end.
watch_recovery() {
  local phase="$1" seconds="$2" begin now ts last
  begin=$(date +%s); recovered_at=""
  while true; do
    sleep 10
    now=$(date +%s)
    ts=$(last_line "$C")
    last=$(date -u -d "$ts" +%s 2>/dev/null || echo "$begin")
    printf '    %s t+%3ds  recreates %-3s last line %3ds ago\n' "$phase" "$((now - begin))" "$(recreates "$C")" "$((now - last))"
    if [ $((now - last)) -ge 75 ]; then recovered_at=$last; return; fi
    [ $((now - begin)) -ge "$seconds" ] && return
  done
}

say "attempt '$label' (root $swarm_root): removing app-comb"
"${swarmctl[@]}" remove --yes app 2>&1 | sed 's/^/    /'
say "removed; waiting 20 s"
sleep 20
say "deploying app-comb"
"${swarmctl[@]}" deploy app 2>&1 | sed 's/^/    /'
start=$(date -u +%FT%TZ)
deployed=$(date +%s)
say "deployed; watching for 180 s (stuck = recreate lines between 90 and 180 s)"

while true; do
  elapsed=$(( $(date +%s) - deployed ))
  [ "$elapsed" -ge 180 ] && break
  sleep 10
  elapsed=$(( $(date +%s) - deployed ))
  up=$(docker service ls --filter name=app-comb_ --format '{{.Replicas}}' | grep -c '^1/1')
  total=$(docker service ls --filter name=app-comb_ -q | wc -l)
  C=$(docker ps -qf name=_central.)
  if [ -n "$C" ]; then
    api=$(docker exec "$C" ps -eo etime,args 2>/dev/null | awk '/[r]est_api/{print $1; exit}')
    count=$(recreates "$C")
    drops=$(udp_drops "$C")
  else
    api="-"; count="-"; drops="-"
  fi
  printf '    t+%3ds  services %s/%s  rest_api up %-6s recreates %-3s udp drops central %s\n' \
    "$elapsed" "$up" "$total" "${api:--}" "$count" "${drops:--}"
done

C=$(docker ps -qf name=_central.)
D=$(docker ps -qf name=_discovery-server.)
if [ -z "$C" ]; then
  say "result: NO_CENTRAL"
  log "$start label=$label result=NO_CENTRAL (central not running after 180 s)"
  exit 1
fi
build=$(docker exec "$C" printenv GITSHA)
late=$(docker logs --since 90s "$C" 2>&1 | grep -c 'recreating its client')
drops_c=$(udp_drops "$C")
drops_d=$(udp_drops "$D")
sockets=$(rest_api_sockets "$C")
result=$([ "$late" -gt 0 ] && echo STUCK || echo ok)
say "result: $result"
log "$start label=$label build=$build result=$result late_recreates=$late rcvbuf_errors central=$drops_c discovery=${drops_d:-n/a} rest_api_sockets=${sockets% }"
[ "$result" = STUCK ] || exit 0

say "STUCK: hands off for up to $((hands_off / 60)) min. Run no ros2 commands, probes or Foxglove reconnects meanwhile."
watch_recovery "hands-off" "$hands_off"
if [ -n "$recovered_at" ]; then
  say "recovered by itself"
  log "  self-recovered: matched between $(date -u -d @"$recovered_at" +%T) and $(date -u -d @$((recovered_at + 70)) +%T) ($((recovered_at - deployed))-$((recovered_at + 70 - deployed)) s after the deploy); no probe run"
  exit 0
fi
log "  still stuck after $((hands_off / 60)) min hands-off"

K=$(docker ps -qf name=_control.)
docker exec -i "$K" sh -c 'cat > /tmp/probe_clients.py' < ~/probe_clients.py
probe_time=$(date +%s)
say "one fresh participant: probe in control"
log "  probe in control at $(date -u +%T):"
docker exec "$K" /opt/volley/entrypoint.sh python3 /tmp/probe_clients.py 2>&1 | grep -v discovery_probe | sed 's/^/    /' | tee -a ~/dds_attempts.log
watch_recovery "after-probe" "$after_probe"
if [ -n "$recovered_at" ]; then
  log "  recovered: matched between $(date -u -d @"$recovered_at" +%T) and $(date -u -d @$((recovered_at + 70)) +%T); the probe started at $(date -u -d @"$probe_time" +%T)"
else
  log "  still stuck $((after_probe / 60)) min after the probe"
fi
say "done: leave the stack as it is for the C++ check and the restart test if it's still stuck"
```
```bash
chmod +x ~/dds_attempt.sh
```
```bash
~/dds_attempt.sh baseline
```
**Starting attempts remotely (not from your own interactive shell):** two traps, both hit on 2026-11-04.
- **`nohup … &` over a non-interactive ssh doesn't survive the connection closing.** The session's systemd scope
  is cleaned up, processes included, which killed an attempt right after it removed the stack and left comb
  without its app stack for ~2 min. Start it as a systemd user unit instead, which lives outside the session (it
  needs your user's manager running, i.e. some login session of yours open, since lingering is off).
- **`HOSTNAME` must be in the environment.** `.env` sets `NFS_HOSTNAME="${HOSTNAME}"` and the stack files use
  `${HOSTNAME}` for the log collector. An interactive login exports it; a unit or plain `bash -c` doesn't, and the
  deploy fails with `required variable NFS_HOSTNAME is missing a value`.
```bash
systemd-run --user --unit=dds-e2-1 --collect -p WorkingDirectory=/home/ops -E SWARM_ROOT=/home/ops/swarm-exp -E HOSTNAME=$(hostname) /bin/bash -c "/home/ops/dds_attempt.sh E2 > /home/ops/dds_e2_1.out 2>&1"
```
```bash
systemctl --user is-active dds-e2-1
```
```bash
tail -f ~/dds_e2_1.out
```

To run the 5 baseline attempts unattended, stopping at the first one that isn't `ok` (so you can do the
checks below before anything restarts again), and surviving an ssh disconnect:
```bash
nohup bash -c 'for i in 1 2 3 4 5; do ~/dds_attempt.sh baseline || break; tail -n 1 ~/dds_attempts.log | grep -q "result=ok" || break; done' > ~/dds_baseline.out 2>&1 &
```
```bash
tail -f ~/dds_attempts.log
```
(A STUCK run appends its probe lines after the result line, so the last line isn't `result=ok` and the loop
stops.)
Each attempt takes about 3.5 min. The check looks at the window from 90 to 180 s after the deploy: a
healthy start logs at most one line, in its first minute, and a stuck one logs one at least every 70 s (one
tick plus the one-minute throttle). `remove` needs `--yes`: without it, it waits for a confirmation that
never comes, because the script sends its output to `/dev/null`. Put `probe_clients.py`
(`../../garage/troubleshooting_reference.md` section 12) in `~` on the node. On a STUCK result the script then
copies it into the new `central` and `control` containers and records whether fresh processes match.
`RcvbufErrors` is the 6th field of the second `Udp:` line, the values; the first is the header, and the `UdpLite:` lines come right after (datagrams dropped
because a socket buffer was full). The counters start at 0 with each new container, so they cover
exactly this start. If the discovery server image has no `sh` or `grep`, its column shows `n/a`.

**When an attempt is STUCK** (changed 2026-11-04 after run 2 recovered by itself, findings 1.12), the script
doesn't probe straight away, because a joining participant might be what un-sticks the REST API:
1. **Hands off, up to 10 min.** It prints a status line every 10 s. Run no `ros2` commands, probes or Foxglove
   reconnects meanwhile. If 75 s pass without a new recreate line, it logs `self-recovered: matched between
   <t> and <t+70 s>` and stops. The window is that wide because the REST API logs at most once a minute.
2. **Otherwise, one fresh participant:** `probe_clients.py` in `control`, then 2 min more watching. It logs
   `recovered: matched between … ; the probe started at …` or `still stuck 2 min after the probe`.
3. **If it's still stuck,** do the C++ check from 4.2, then the workaround:
```bash
docker service update --force app-comb_central
```
and confirm it recovers (no recreate lines after 90 s). That proves a process restart is the cure.

A STUCK attempt takes up to about 16 min (3 + 10 + 2 + the probe).

### 4.4 How many attempts

Two of two full starts failed so far. Run **5 baseline attempts** first, to measure the failure rate
without changes. If it's 5/5, one change that gives **5/5 ok** is a strong result. If the baseline is
flaky (say 2/5), each variant needs about 10 attempts before a difference means anything.

## 5. The experiments, one change at a time

**The baseline (section 4) changes no files**: it only removes and redeploys the stack with the current
settings, so it needs no backups. They're for the experiments below that edit files.

Restore each change before the next. **The stack files belong to `root`** (`/data/swarm/stacks/app/*.yaml`,
`config/fastdds-profile.xml`), and on comb `ops` may not use `sudo` for `cp` or editors (checked 2026-11-04: "ops is
not allowed to execute '/usr/bin/cp …' as root"). **So edit a copy instead:** everything under `/data/swarm` is
readable (6.3 MB), and `swarmctl --root <dir>` deploys from any folder. It reads `.env`, `.env.local`, the
manifest and the stack files from there, and sets `SWARM_ROOT_DIR` (where the configs, the profile included,
are read from) to it. `/data/swarm` stays untouched, so there's nothing to restore except redeploying from it.
```bash
cp -r /data/swarm ~/swarm-exp
```
Edit files under `~/swarm-exp/stacks/…` (no sudo needed), check with
`/data/swarm/bin/swarmctl --root ~/swarm-exp info`, and run attempts with
`SWARM_ROOT=~/swarm-exp ~/dds_attempt.sh <label>`. `~/swarm-exp/.env.local` is a copy, so make `.env.local` changes
for the experiment there. To go back: `swarmctl remove --yes app`, wait 20 s, `swarmctl deploy app` (from
`/data/swarm`; remove first, because a changed config can't replace one of the same name). `.env.local` belongs to `ops`, but its
folder doesn't, so edit it with the `/tmp` + `cat >` pattern from `../../garage/deploy_and_test.md` 3.4, not `sed -i`.
Back up both once:
```bash
sudo cp -a /data/swarm/stacks /data/swarm/stacks.before-dds-tests
```
```bash
cp /data/swarm/.env.local ~/env.local.before-dds-tests
```
A Mender release install replaces `/data/swarm`, so don't leave test edits there. Docker configs can't
change in place, but every attempt removes the stack, so an edited profile is picked up by the next
attempt.

### E1: Discovery server first (H2)
No file changes. Recreate the stack, let it come up, then restart only the participants once the
server has been up for a while:
```bash
swarmctl remove --yes app; sleep 20; swarmctl deploy app; sleep 60
docker service update --force app-comb_central &
docker service update --force app-comb_bay7 &
wait
```
Then check the detector after 60 s. **If this always passes while the baseline fails, the start order
is the trigger.** Fix candidates:
- move `discovery-server` out of the `app` stack into the long-lived `site` stack (swarm-deploy), so
  deploys and recreates never restart it
- make `discovery_probe` also wait until the server has been up a few seconds (it already waits for
  name resolution and one answer)
- handle node boots, when everything still starts together: a stack-level start order, or the self-heal
  below

### E1b: Restart only the discovery server (H2)
Everything else keeps running:
```bash
docker service update --force app-comb_discovery-server
```
Wait about a minute, then check the detector. This tests the other half of H2: whether the participants
recover when the server alone restarts (its database is empty and they must register again), with no
mass start of participants.
- **Gets stuck:** the server restart alone is enough. Moving the server out of the `app` stack is then
  the fix, and it's worth reporting to eProsima.
- **Stays healthy:** it takes the server and the participants starting together.

### E2: Bigger UDP buffers (H1)
The baseline showed it: the REST API's discovery socket overflows in stuck runs, with every DDS socket at the
208 KiB Linux default. In the copy's profile, `~/swarm-exp/stacks/app/config/fastdds-profile.xml` (see above), in the `udp_overlay`
transport descriptor, after `</interfaces>`:
```xml
        <sendBufferSize>4194304</sendBufferSize>
        <receiveBufferSize>4194304</receiveBufferSize>
```
4 MiB is the container's `rmem_max`. More needs `net.core.rmem_max` raised on the hosts, which is vng-os. After the
next attempt's deploy, check that it took effect: the attempt's `rest_api_sockets=` field (or
`docker exec "$C" ss -uamn`) should show `rb` of about 8 MiB (the kernel doubles the requested value for its own
bookkeeping) instead of `rb212992`.
**No STUCK in 5 attempts, and few or no drops on the REST API's socket, means the overflow is the mechanism**,
and a bigger buffer is the fix (to land in swarm-deploy's profile).

### E3: No super client in central (H3)
In `/data/swarm/stacks/app/main.yaml`, under `central:` → `environment:`, add:
```yaml
      ROS_SUPER_CLIENT: "false"
```
(stack environment overrides the image's `ENV`). Side effects for the test only: central's own
`ros2 node list` and the Foxglove bridge then see less of the graph, so the NOC's 3D view and FoxNOC may
show less. **If STUCK disappears**, the super-client burst matters. The fix then is a design question
(which central processes really need the whole graph; the REST API doesn't).

### E4: UDP only, no shared memory (H4)
In the profile, remove `<transport_id>shm</transport_id>` from `<userTransports>`. Processes in the same
container then talk over UDP too. **If STUCK disappears**, the SHM/UDP mix is involved, and that's for
eProsima.

### E5: Another Fast DDS version (H5)
This needs new images, so do it last, with Dan:
1. Check the Fast DDS release notes after 3.6.2 (and the ROS Lyrical sync notes) for fixes about
   discovery server, client/server PDP or EDP, or "endpoints not matched". The eProsima repo is
   `eProsima/Fast-DDS`. Search its issues for "discovery server" together with "EDP", "not matched" or
   "super client".
2. In ros2-docker, bump the ROS snapshot date to one with the newer `ros-lyrical-fastdds`, and build the
   `core` / `base` / `discovery-server` images.
3. In volley's `docker/docker-bake.hcl`, point `BASE_IMAGE` at the new base, build a PR, and in
   swarm-deploy (or `.env.local` for a test) use the new discovery server image tag.
4. Run the baseline attempts again.

### E6: C++ or Python only?
In every STUCK attempt, do the dispatcher check from 4.2. If the dispatcher (C++) can call bay 7 while
the REST API can't, the trigger is specific to the first-started or the Python participant, which narrows
H3 and points at timing inside the central container: `rest_api` is launched first.

### E7: Give the discovery server the same profile (H6)
In `/data/swarm/stacks/app/support.yaml`, under `discovery-server:`, add the same lines the other services have:
```yaml
    environment:
      FASTDDS_DEFAULT_PROFILES_FILE: /etc/fastdds/profile.xml
    configs:
      - source: fastdds-profile
        target: /etc/fastdds/profile.xml
```
(`support.yaml` itself defines the `fastdds-profile` config, lines 95-97, so the service can reference it
as is). Check first what the server advertises today: with a packet capture (section 6), look at the
locators in its DATA(p). **If it advertises a `docker_gwbridge` address, or STUCK disappears with the profile**,
the server was the gap left by the two October fixes.

### E8: Make Fast DDS show failed endpoint additions (instrumentation for H7)

Reviewed by Codex (2026-11-04); its corrections are folded in.

**What it changes:** the **existing REST API process**, not a new node. A few lines in `rest_api.py` `main()`
raise Fast DDS's log level for that process, before `rclpy.init()`. No participant is added to the graph, which matters
because a joining participant can un-stick the REST API.

**What the warning means, and what it doesn't.** When endpoint data (DATA(w)/DATA(r)) can't be added as a remote
proxy, the EDP listener logs `EPROSIMA_LOG_WARNING(RTPS_EDP, "Received message from UNKNOWN RTPSParticipant,
removing")` (`EDPSimpleListeners.cpp`, from ~85). Despite its wording, this fires whenever `PDP::addWriterProxyData` /
`addReaderProxyData` returns null (`PDP.cpp` 931-1103). That happens when the owning participant isn't known (the H7
race), but also in other failure branches, and when the proxy pool is full. That last case also logs `RTPS_PDP
"Maximum number of … proxies"`. So the warning shows **a failed proxy addition**, not necessarily "endpoint data
before participant data". And on its own it doesn't prove the rest of H7's chain (acknowledged, never re-sent,
permanently missing); a capture and the endpoint state are still needed for that.

**Why we've never seen it.** Fast DDS's runtime verbosity defaults to `Error` (`Log.cpp:45`), and 3.6.2 has no XML or
environment setting for it. Checked in the devcontainer (same package as comb): the warning text is compiled into
`libfastdds.so.3.6`, and `Log::SetVerbosity` is exported (`Kind`: Error 0, Warning 1, Info 2). The log level is per
process, so only the REST API itself can show its own failures. A separate process would be a stand-in at best.

**Diagnostic change** (in `rest_api.py` `main()`, right before `rclpy.init`; gated so normal runs are unchanged):
```python
if os.environ.get("FASTDDS_WARNINGS") == "1":
    import ctypes
    fastdds = ctypes.CDLL("libfastdds.so.3.6")
    set_verbosity = getattr(fastdds, "_ZN8eprosima7fastdds3dds3Log12SetVerbosityENS2_4KindE")
    set_verbosity.argtypes = [ctypes.c_int]
    set_verbosity.restype = None
    get_verbosity = getattr(fastdds, "_ZN8eprosima7fastdds3dds3Log12GetVerbosityEv")
    get_verbosity.restype = ctypes.c_int
    set_verbosity(1)  # Log::Kind::Warning
    print(f"Fast DDS log verbosity set to {get_verbosity()} (1 = Warning)", flush=True)
```
Before trusting it, check:
- the startup line reads back `1`
- the REST API process has loaded only one `libfastdds` (`grep libfastdds /proc/<pid>/maps`), so the call reached the
  library rmw uses
- (in the lab) a deliberately triggered Fast DDS warning shows up in the output, so silence later means something

The mangled symbol is acceptable for a pinned diagnostic image. Reusable tooling would want a small C wrapper.

Set `FASTDDS_WARNINGS=1` for the REST API: in `launcher/central_nodes.py`, `additional_env={"FASTDDS_WARNINGS": "1"}` on
its `Node`, or for the whole central service in the experiment copy's `main.yaml`. **Keep all Fast DDS warnings**, not
just one grep (`RTPS_EDP`, `RTPS_PDP`, transports):
```bash
docker logs "$C" 2>&1 | grep -E '\[RTPS_|Warning' > fastdds_warnings_<run>.txt
```
Build it into **one diagnostic branch** together with Codex's heartbeat diagnostics (1 s readiness per service,
positive transitions, the REST API's own graph counts), deployed as that branch's `pr-<n>` tag. In the lab, the same
lines go in the long-running test client, with no build.

**Reading the result** (needs stuck and healthy starts, with the read-back confirmed in each):

| Observation | What it supports |
|---|---|
| Warning only in stuck starts | A relationship between failed proxy additions and the symptom. It doesn't yet identify bay 7 or prove the ordering |
| Warning in healthy and stuck starts | Some failures are harmless or recover. Identify which endpoints they were |
| No warning during a stuck start, logging confirmed | Strong evidence against this rejection path in that run; not against every discovery race |
| The failure rate changes with logging on | Timing sensitivity. Fewer failures isn't a fix |

**If the warning appears,** the next instrumentation needs the remote endpoint's GUID, the topic, the local
participant's GUID and the actual failure reason. That means a patched Fast DDS or rmw build (or a lab build), since the
message itself names none of them.

### The investigation branch (2026-11-04)

`jmg/test/dds-rest-api-diagnostics` in volley, based on PR #1018 **without** the client-recreate commit (`e1d24a7c`, which
didn't fix anything and added discovery traffic). It adds, for the REST API only:
- **`central_api/dds_diagnostics.py`:**
  - `enable_fastdds_warnings()`: E8, with typed `ctypes` and the verbosity read-back. A unit test proved it against
    the installed `libfastdds.so.3.6` (read-back 1).
  - `BayDiscoveryMonitor`: a 1 s timer that leaves the clients alone and prints `[dds-diag]` lines: a `change` line
    whenever a bay service's readiness or the REST API's **own** graph counts (`rq_readers`, `rr_writers`) change, and
    a `heartbeat` with the not-ready services.
- **`rest_api.py`:** wired in behind `REST_API_DDS_DIAG=1` / `FASTDDS_WARNINGS=1`, plus a traceback if the spin thread dies.
- **`launcher/central_nodes.py`:** sets both variables for the REST API node.

Unit tests: `test/test_dds_diagnostics.py`; `central_api` 451 and `launcher` 12 tests green; black, mypy, pylint 10.00.

Its attempt script is `results/2026-11-04/scripts/dds_attempt_diag.sh`:
- **Judging:** STUCK means a **deployed** bay's confirm service is still not ready 180 s after the deploy. The REST API
  also holds clients for undeployed layout bays, which are never ready. `NO_HEARTBEAT` / `NO_DIAG` if the diagnostics
  aren't there.
- **What it records:** the stuck services' graph counts, the Fast DDS warnings (`~/dds_warnings_<label>_<start>.txt`),
  and exact recovery times from the `ready=1` change lines.

**Reading the graph counts while stuck** (rmw needs both parts for readiness):
- `rq_readers=0` / `rr_writers=0`: the REST API's participant never learned bay 7's endpoints (the H7 family).
- `1`/`1` but `ready=0`: the endpoints are known but not matched.

**Codex review of the branch and script (2026-11-04, applied to the script):**
- the expected bays come from `BAY_IDS_OVERRIDE` (else the bays deployed before the removal), and each must have its
  task running, else `BAY_NOT_RUNNING:<bays>` rather than a false STUCK or ok
- heartbeat loss gives an explicit `NO_HEARTBEAT`, and the attempt stops without probing
- the log window starts before the deploy, so the earliest startup lines (verbosity read-back, warnings) are included
- the probe is one rclpy process (`source /opt/volley/setup.bash && python3 …`), without the entrypoint's extra discovery
  participant

These were tested offline with a fake `docker`.

**Second diagnostics change (2026-11-04, commit `29712d97`, pushed; images `dds-diag-29712d9` in comb's registry):**
- endpoint GIDs in the change records (`rq_gids=…`, `rr_gids=…`, sorted hex, `-` if none): counts can stay 1/1 while
  the endpoints behind them change, and that now prints a `change` line
- `pid=` on every `[dds-diag]` line, so a REST API restart shows
- each check is bracketed: `check-start n=<n>` first, then `heartbeat n=<n> took_ms=<ms> not_ready=…`. A `check-start`
  with no heartbeat after it means the callback started and didn't finish (a graph query, `service_is_ready()` or a
  stdout write could be what blocked); neither line means it never ran
- `dds_attempt_diag.sh` logs `last_check="started n=…"|"finished n=…"` and `rest_api_pids=` on the result line, and the
  last check in the `NO_HEARTBEAT` messages (helpers tested offline on sample lines)
- `central_api` 452 and `launcher` 12 tests green (3 in `test_dds_diagnostics.py`, incl. a GID swap at the same count);
  black, mypy, pylint 10.00
- Codex review of `29712d97` (no issue in the Python), two script fixes applied and tested offline with fake logs and a
  fake `docker`:
  - recovery time: `ready_at` now takes each service's first `ready=1` after its last `ready=0`. GID changes also print
    `ready=1` lines, so "the latest `ready=1`" could be later than the recovery and make a probe look like it came first
  - no expected bays: empty lines are dropped and only numeric IDs become `b<n>`, so with no override and no bay services
    the list is empty and the script stops before `remove` (it used to yield `b` and carry on)

**First runs (2026-11-05, findings 1.17-1.18):** the plain redeploy at 00:58Z and the full start `diag1` at 02:01Z were
both ok, with the first check already `ready=1 1/1`. Two Fast DDS warnings appear in every start of the REST API (host-ID
fallback to IP, SHM `segment_size`), so they're not a stuck signature. The script's warnings grep missed them because Fast
DDS colours its lines; `save_warnings` now strips ANSI escapes first.

Still to keep in mind:
- when reading results, treat one `ready=0` with `1/1` sample as a possible transition (the three queries aren't
  atomic); only a persistent pattern means a failed match
- check once in the lab that a real Fast DDS warning reaches the captured output, not just the verbosity read-back

To get images, push the branch and open a **draft** PR (CI builds `pr-<n>`; only the branch-name check fails,
because `test/` branches aren't ticket-named, and image builds don't depend on it).

## 6. Capturing more detail when needed

Only if the experiments above don't separate the hypotheses:
- **Packet capture on the overlay** during an attempt. The central node has `tcpdump` and `nsenter`, so you
  can capture inside the central container's network namespace with no extra image (sudo asks for your
  password). Start it right after `swarmctl deploy app`, once the new central container exists:
  ```bash
  PID=$(docker inspect -f '{{.State.Pid}}' "$(docker ps -qf name=_central.)")
  ```
  ```bash
  sudo nsenter -t "$PID" -n tcpdump -i overlay0 -w /tmp/start.pcap udp
  ```
  This sees everything central's processes exchange with the discovery server and the bays over the overlay
  (not shared-memory traffic between central's own processes). Copy `/tmp/start.pcap` to your laptop and open
  it in Wireshark, which decodes RTPS. Look for:
  - the bay's DATA(r)/DATA(w) for `rq/bay/b7/confirm_insertRequest` / `rr/bay/b7/confirm_insertReply` being
    sent to the REST API's participant
  - the addresses in bay 7's and the server's DATA(p) (H4, H6)
  The traffic between nodes is VXLAN on the host's `eth0` (UDP 4789), which Wireshark can also decode.
- **Fast DDS warnings and errors** already go to stderr, so they're in `docker logs`. Grep for
  `RTPS_` and `PDP`/`EDP`. Info-level Fast DDS logs are compiled out of release packages.
- **rmw debug logs** for one process: add `--log-level rmw_fastrtps_cpp:=debug` to the `rest_api` node's
  ros args in `launcher/central_nodes.py` (needs a build).

## 7. Reporting to eProsima, if it's a Fast DDS bug

Open an issue on `eProsima/Fast-DDS` with:
- versions: Fast DDS 3.6.2, rmw_fastrtps 9.4.9, ROS Lyrical (snapshot 2026-08-19), Ubuntu resolute
- the topology: one discovery server (`fast-discovery-server`), super clients on the central host and plain
  clients on other hosts, over a Docker swarm overlay
- the profile (`fastdds-profile.xml`), and that type propagation is disabled
- the symptom: a client participant stays unmatched with one remote service's endpoints for hours,
  while new participants on the same host match within a second
- the trigger and the failure rate from section 4, and the experiment that changes it
- a minimal repro if possible: three containers (server, a Python process with a client, a C++ process
  with a service), started together with Docker Compose in a loop, using the same images and profile.
  Build it once the experiments show the trigger, so it can be kept small.

## 8. Meanwhile: the safety net (separate from the root cause)

Whatever the root cause, a fresh participant matches at once, so a process restart should cure a stuck
one. Confirm that in the first STUCK attempt (the workaround in 4.3). A small, separate PR can make the REST
API restart itself:
- The `refresh_bay_clients` timer already detects an unmatched bay client. Instead of recreating clients,
  it exits the process if central reports that bay alive (continuous garage info, which the REST API
  already subscribes to) and the client stays unmatched for 60 s.
- `respawn=True` on the `rest_api` node in `launcher/central_nodes.py` restarts it with a new participant.

Until then, after a node boot or a full stack recreate, run `docker service update --force app-comb_central`
once and check the log.

## 9. Order of work

1. Make sure nobody else is using comb for about 20 min (5 attempts), including whoever ran `bay-refactor` there.
2. Push the rebased branch, wait for `runtime-images`, set `VOLLEY_VERSION=pr-1018`, deploy, and check `GITSHA`.
3. Install `dds_attempt.sh` and `probe_clients.py` in `~` (no backups needed yet).
4. 5 baseline attempts, with the C++ check and the workaround on the first STUCK one.
   Before the first experiment that edits files, back up `/data/swarm/stacks` (and `.env.local` if it will
   change), as in section 5.
5. E1 and E1b (start order, server restart), then E2 (buffers, if drops were seen). These are the most
   likely.
6. E7 (server profile), E3, E4 if those don't separate things.
7. Write the results into `findings.md` and take them to Dan: the fix is in
   swarm-deploy (start order, profile) or ros2-docker (Fast DDS version). E5 and an eProsima report only if
   it comes to that.
8. Restore `/data/swarm/stacks` and `.env.local` from the backups and redeploy what was there before.
