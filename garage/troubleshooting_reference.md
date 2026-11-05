# Garage troubleshooting reference

The commands used while deploying and debugging PR #1018 on central-comb (2026-11-03 and 04), with what
each one tells you. They work on any Pecos central node: swap the host, and `app-comb` for that node's
stack (`swarmctl info` shows it). Background for the confirm-insert investigation: 
`investigations/dds_rest_api_discovery/findings.md`. Deploy steps: `garage/deploy_and_test.md`.

Contents:

1. Getting onto the node
2. What is deployed
3. Deploying and checking the build
4. Logs
5. The REST API and confirm-insert
6. The ROS graph from inside a container
7. DDS configuration and network health
8. Exercising a failure on purpose
9. The NOC and the dispatcher
10. CI
11. Reading timestamps
12. The probe scripts
13. The control container: running your own ROS commands
14. Foxglove: streaming the garage's data to your laptop

---

## 1. Getting onto the node

```bash
ssh ops@central-comb-5675-pecos
```
The central nodes are on the tailnet (`central-eng-5675-pecos`, `central-qa-5675-pecos`,
`central-5675-pecos-bench`, `central-comb-5675-pecos`). See `deploy_and_test.md` 3.2.

**Running commands from your laptop without logging in.** A non-interactive ssh shell doesn't load
`~/.bashrc`, so `swarmctl` isn't on its PATH. Use its full path:
```bash
ssh ops@central-comb-5675-pecos '/data/swarm/bin/swarmctl info'
```
`docker` works as is. Save long output to a file on your side:
```bash
ssh ops@central-comb-5675-pecos '/data/swarm/bin/swarmctl logs -e logstore-agent -e noc' > comb_logs.txt
```

**What `swarmctl` can do:** `deploy`, `info`, `logs`, `remove` and `watch`, nothing else. There's no
command to run something inside a container. For that, use `docker exec` on the node where the
container runs (section 13).

---

## 2. What is deployed

```bash
swarmctl info
```
- **Release:** the swarm-deploy release installed on the node (tooling and stack files, from Mender).
  This is not the volley version.
- **Environment:** `site-sub-name` (e.g. `comb`), `swarm-root`, and `manual-stacks` (a manual stack only
  changes when someone runs `swarmctl deploy`).
- **Stacks:** what this node may deploy, and under which name (`app (app-comb)`).

```bash
docker stack ls
```
The stacks running in the whole swarm, with their service counts (`app-comb`, `global`, `site`).

```bash
docker service ls --format '{{.Name}}  {{.Image}}'
```
Every service and the image tag it runs. Add `| grep app-comb` for one stack.

```bash
docker service ps app-comb_central
```
The service's tasks (containers), including old ones: their state (`Running 15 minutes ago`,
`Shutdown …`), the node they're on and any error. **The age of each service's task shows what the last
deploy restarted.** After `swarmctl deploy app` on a running stack, only `central` and `bay<N>` are new,
because their command carries the deploy timestamp. If every service, the `discovery-server` included,
has one task with the same age, the stack was created from scratch (removed and deployed, or the node
rebooted).

```bash
for s in discovery-server central control bay7 noc; do docker service ps app-comb_$s --format "$s {{.CurrentState}} {{.Node}}" | head -3; done
```
The same for several services at once.

```bash
cat /data/swarm/.env.local
```
The node's overrides: `VOLLEY_VERSION` (which `pr-<n>` or release tag to run), `VOLLEY_REGISTRY` (ECR or a
local registry), `BAY_IDS_OVERRIDE` (which bays are deployed), `MANUAL_STACKS`. **A bay not in
`BAY_IDS_OVERRIDE` has no services, so its confirm-insert can't work.**

---

## 3. Deploying and checking the build

**Before deploying**, check that CI pushed images for your commit (from your laptop):
```bash
gh pr checks 1018 | grep runtime-images
```
```bash
gh run list --branch jmg/SW2-1135/scheduler-renames-and-cleanups --limit 3 --json headSha,status,conclusion --jq '.[] | "\(.headSha[0:8]) \(.status) \(.conclusion)"'
```
`runtime-images / build-push` must pass for the commit at the top. The whole run can still say `queued`
or `in_progress` while tests run, which doesn't matter for deploying.

**Deploy:**
```bash
swarmctl deploy app
```
It prints "Updating service" for every service, but only services whose spec changed restart: `central`
and the bays, because of `DEPLOY_ISO_TIMESTAMP`. The new containers pull the tag again, so they get the
latest build. `control`, `noc` and `bay<N>-guidance` keep their old containers (`deploy_and_test.md` 3.4,
step 8).
```bash
swarmctl watch
```
It returns at once when everything has already converged.

**Set the central container once** (the pattern matches `<stack>_central.<n>.<id>` on any node):
```bash
C=$(docker ps -qf name=_central.)
```

**Which commit is running** (the runtime images carry `GITSHA`, 7 characters):
```bash
docker exec "$C" printenv GITSHA
```
Compare with `git rev-parse --short=7 <branch>` on your laptop.

**Whether specific code is in the image:**
```bash
docker exec "$C" sh -c 'grep -n "def refresh_bay_clients" $(find /opt/volley -name rest_api.py -path "*central_api*")'
```

**How long each process has run** (also shows whether something restarted since the deploy):
```bash
docker exec "$C" ps -eo pid,etime,args
```
```bash
docker exec "$C" ps -eo etime,args | grep "[r]est_api"
```
The `[r]` keeps the grep itself out of the output.

**Which image digest a container runs** (if `GITSHA` looks wrong):
```bash
docker inspect --format '{{.Image}}' "$C"
```
```bash
docker image ls --digests | grep central-pr-1018
```

**What runs in central:** `rest_api`, `proxy_node`, one component container (`[central-3]`: dispatcher,
garage tracker, scheduler and the monitors), `metrics_recorder`, `visualizer_node`, `foxglove_bridge` and a
recorder (`deploy_and_test.md` 3.5.1). The number in a log prefix such as `[rest_api-1]` is the launch
order.

---

## 4. Logs

**The whole stack, once, to a file** (without `-f` it prints everything and exits):
```bash
swarmctl logs -e logstore-agent -e noc
```
`-e` leaves out a service by short name. `-s` picks one stack, `-f` follows, `-n <lines>` shows only the
end.

**Central only:**
```bash
docker logs "$C" 2>&1 | tail -100
```
```bash
docker logs --since 1m "$C" 2>&1 | grep 'recreating its client'
```
The stack logs to fluentd, but Docker keeps a local copy, so `docker logs` works. Check it returns
anything with `docker logs "$C" 2>&1 | grep -c rest_api`.

**A service on another node** (for example a bay, which runs on its bay computer). The swarm manager
fetches it:
```bash
docker service logs --since 10m app-comb_bay7 | tail -30
```
This merges the logs of **all** the service's tasks, old and new, and they share a slot name
(`app-comb_bay7.1`). **Keep the task IDs** (don't pass `--no-task-ids`), or an old container's shutdown
lines can look recent.

**Filters that were useful:**

| Looking for | grep |
|---|---|
| REST API recreating bay clients | `'recreating its client'` |
| REST API warnings and errors | `grep "rest_api-1" \| grep -E "ERROR\|WARN"` |
| Failed confirm-insert | `'timeout waiting for service'` |
| Dispatcher activity | `"central.dispatcher"` |
| Bay state changes | `'Transitioning from state'` |
| Patron app requests (nginx access log) | `'confirm-insert\|/api/v3/'` |
| Startup, per container | `'discovery_probe\|process started'` |

Strip colour codes when saving logs: `sed -E 's/\x1b\[[0-9;]*m//g'`.

**Shutdown noise that is harmless:** when a deploy replaces a container, `ros2 launch` sends SIGINT to its
processes. The rosbag recorder can then log `ERROR … Failure in topics discovery … rcl node's context is
invalid` and still end with `process has finished cleanly`.

---

## 5. The REST API and confirm-insert

| Symptom | Where | Meaning |
|---|---|---|
| `confirm-insert: timeout waiting for service /bay/bN/confirm_insert ready` (HTTP 500) | `[rest_api-1]` | The REST API's client never became available for that bay within 2.5 s |
| `/bay/bN/confirm_… not discovered, recreating its client` | `[rest_api-1]`, at most once a minute (`073556ea` only) | The 10 s refresh found a client with no matched service |
| The same line every minute while the bay is up | | The REST API process is stuck, not just one client (findings 1.9) |
| `"POST /api/v3/bay/b7/confirm-insert HTTP/1.1" 500` | `app-comb.nginx` | The patron app's request and its status |

Request paths: v2 `rest_api.py` `bay_confirm_insert`, v3 `RosBayGateway.confirm_insert`, the NOC
`api/bay/b<id>/confirm-insert` (v1). All use the same per-bay clients.

---

## 6. The ROS graph from inside a container

**Which container.** For general graph checks, use the `control` container (section 13): it runs nothing,
doesn't restart on every deploy, and doesn't touch the running garage. Use `central` only when the
question is about central's own processes. The 2026-11-04 test of whether a fresh process **in the same
container as the REST API** could match bay 7 had to run in `central`. In the commands below, swap `$C` for
`$K` (the control container) as needed.

Run `ros2` and Python through the image's entrypoint, which sources `/opt/volley/setup.bash` and waits for
the discovery server (expect three `discovery_probe` lines first):
```bash
docker exec "$C" /opt/volley/entrypoint.sh ros2 node list --no-daemon --spin-time 8
```
```bash
docker exec "$C" /opt/volley/entrypoint.sh ros2 service list --no-daemon --spin-time 8
```
**Use `--spin-time`.** With the discovery server, a new process needs a few seconds to learn the graph.
The default wait printed an empty list.

**Who serves a service, as a fresh process sees it** (script in section 12):
```bash
docker exec "$C" /opt/volley/entrypoint.sh python3 /tmp/probe_graph.py
```
It prints the readers of each service's request topic and the writers of its response topic. A healthy
service has one of each, from the same node (`/bay/b7/bay_state_machine`). **rmw_fastrtps reports a
service available only when those counts match**, so a ghost or duplicate server shows up here as a
mismatch.

**Whether a fresh process can match a service** (script in section 12):
```bash
docker exec "$C" /opt/volley/entrypoint.sh python3 /tmp/probe_clients.py
```
It creates clients and waits for them to become ready, without sending a request. On 2026-11-04 every
service was ready in 0.8–1.2 s while the long-running REST API stayed stuck. **That test is what
showed the problem is the REST API process, not the bay, the network or the discovery server.**

Copying a script into a container (it's gone when the container is replaced; `central` is replaced on every
deploy, `control` only when the stack is recreated or its image changes):
```bash
cat probe_graph.py | docker exec -i "$C" sh -c 'cat > /tmp/probe_graph.py'
```
From your laptop:
```bash
P=$(base64 -w0 probe_graph.py); ssh ops@central-comb-5675-pecos "echo $P | base64 -d | docker exec -i \$(docker ps -qf name=_central.) sh -c 'cat > /tmp/probe_graph.py'"
```

---

## 7. DDS configuration and network health

**DDS environment of a container:**
```bash
docker exec "$C" sh -c 'env | grep -E "^(ROS_|RMW_|FASTDDS|FASTRTPS)" | sort'
```
Central: `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_DISCOVERY_SERVER=discovery-server:11811`,
`ROS_SUPER_CLIENT=true`, `FASTDDS_DEFAULT_PROFILES_FILE=/etc/fastdds/profile.xml`.

**The Fast DDS profile** (from swarm-deploy `swarm/stacks/app/config/fastdds-profile.xml`, mounted as a
Docker config):
```bash
docker exec "$C" cat /etc/fastdds/profile.xml
```

**Fast DDS and rmw versions:**
```bash
docker exec "$C" sh -c 'dpkg -l | grep -E "fastdds|fastcdr|rmw-fastrtps" | awk "{print \$2, \$3}"'
```
On 2026-11-04: `fastdds 3.6.2`, `rmw-fastrtps-cpp 9.4.9`, the same in the discovery server image.

**The discovery server:**
```bash
D=$(docker ps -qf name=_discovery-server.)
```
```bash
docker inspect --format '{{.Config.Cmd}}' "$D"
```
```bash
docker service logs app-comb_discovery-server
```
It runs `fast-discovery-server 42 -l discovery-server -p 11811` and logs its GUID prefix and address at
start.

**The network, host and container.** vngOS has no `ip` command on the host. Use `ifconfig`, `networkctl list`
or `ls /sys/class/net`. Containers have `ip`:
```bash
ifconfig | grep -E "^[a-z]|inet "
```
```bash
docker exec "$C" ip -br a
```
```bash
docker network ls --format "{{.Name}}  {{.Driver}}  {{.Scope}}"
```
```bash
docker network inspect app-comb_internal --format "{{.Driver}} {{range .IPAM.Config}}{{.Subnet}}{{end}}"
```
On comb (2026-11-04):
- **Host:** `eth0` 10.0.1.173 (the garage LAN), `tailscale0` 100.120.46.20, `docker0` 172.17.0.1,
  `docker_gwbridge` 172.18.0.1, and one `veth…` per container interface.
- **Central container:** `overlay0` 172.16.3.5/24 (swarm overlay `app-comb_internal`, 172.16.3.0/24; the
  discovery server is 172.16.3.3) and `eth0` 172.18.0.13/16 (on `docker_gwbridge`, host-local).
- **The `@ifN` suffix** is the index of the interface's other end. `eth0@if566` pairs with the host's
  `vethef08a0f` (index 566 in `networkctl list`). `overlay0`'s peer is in the overlay network's own hidden
  namespace (`/run/docker/netns`, root only), so the host's interface list doesn't show it.

**UDP buffers and drops** (in the container's own network namespace, which is what matters for its
processes):
```bash
docker exec "$C" sh -c 'cat /proc/sys/net/core/rmem_max /proc/sys/net/core/rmem_default; grep -E "^Udp:" /proc/net/snmp'
```
In the `Udp:` lines, `RcvbufErrors` counts datagrams dropped because a socket's buffer was full: the
kind of loss swarm-deploy's README blames for unmatched endpoints at startup. The counters reset with the
container. Run the same `grep` on the host for the host's namespace. The value alone (the second `Udp:` line,
6th field):
```bash
docker exec "$C" awk '/^Udp:/{n++; if (n==2) {print $6; exit}}' /proc/net/snmp
```

**Drops and buffer size per socket:** `ss` (in the container) shows each UDP socket's receive buffer limit
(`rb`) and its drops (`d`):
```bash
docker exec "$C" ss -uamn
```
On 2026-11-04 every DDS socket in central had `rb212992` (208 KiB, the Linux `rmem_default`; Fast DDS requests
no size). The REST API's discovery socket had `d776`.

**Which process owns a socket:** `/proc/net/udp`'s last column is the per-socket drop count, and its inode
column can be matched to a process through `/proc/<pid>/fd`. This script lists the sockets with drops and their
owners (copy it in as in section 6, then `docker exec "$C" sh /tmp/udp_drops.sh`):
```sh
#!/bin/sh
# UDP sockets with drops in this network namespace, and the process that owns each one.
for p in /proc/[0-9]*; do
  name=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null | cut -c1-70)
  for fd in "$p"/fd/*; do
    l=$(readlink "$fd" 2>/dev/null) || continue
    case "$l" in socket:*) i=${l#socket:[}; echo "${i%]} ${p#/proc/} $name";; esac
  done
done > /tmp/sockmap
for f in /proc/net/udp /proc/net/udp6; do
  [ -r "$f" ] && awk 'NR>1 {print $10, $NF, $2, $14}' "$f"
done | while read -r inode drops local rest; do
  [ "$drops" -gt 0 ] 2>/dev/null || continue
  owner=$(grep "^$inode " /tmp/sockmap | head -n 1 | cut -d' ' -f2-)
  echo "$drops $local ${owner:-?}"
done | sort -rn
echo "total RcvbufErrors: $(awk '/^Udp:/{n++; if (n==2) {print $6; exit}}' /proc/net/snmp)"
```
Caveat: `ros2 launch` creates its own participant before starting the processes, and **every child inherits
copies of its sockets**. So a socket can have several holders, and the script reports the first one it finds.
To see all holders of one port, list every `/proc/<pid>/fd` pointing at that inode.

**Fast DDS ports (domain 0):** discovery (metatraffic) unicast **7410 + 2 × participant ID**, user data **7411 +
2 × ID**. IDs are given out per network namespace in creation order. On comb (2026-11-04): 7410/7411 `ros2 launch`
(ID 0), 7412-7423 central's other processes, **7424/7425 the REST API (ID 7, it registers last)**.

---

## 8. Exercising a failure on purpose

**Take a bay away and bring it back** (only with no vehicle or operation in the bay):
```bash
docker service scale app-comb_bay7=0
```
```bash
docker logs --since 1m "$C" 2>&1 | grep 'recreating its client'
```
```bash
docker service scale app-comb_bay7=1
```
```bash
docker logs --since 70s "$C" 2>&1 | grep 'recreating its client'
```
The second grep, run more than a minute after the bay is back, should print nothing (the throttle
allows one line a minute, so a 70 s window would catch a repeat).

**Restart only central** (the REST API gets a new participant; the discovery server and bays keep
running). This is also the workaround when the REST API is stuck:
```bash
docker service update --force app-comb_central
```
It stops the dispatcher, so start it again from the NOC.

**Recreate the whole stack** (everything starts at once, the discovery server included; on 2026-11-04 this
is when the REST API got stuck):
```bash
swarmctl remove app
```
```bash
swarmctl deploy app
```

---

## 9. The NOC and the dispatcher

NOC: `http://central-comb-5675-pecos:8011/webviewer/` (`deploy_and_test.md` 4 and 4.0).

1. **Request Control.** Needed to start, resume and change mode.
2. **Dispatcher Mode.** Only while Status is off. Manual accepts move AGV/tray and bay transitions;
   Auto accepts retrieve, repark and charge, and cleans and rebalances on its own.
3. **Dispatcher Status → on.** Central always boots stopped. A stopped dispatcher fails every job.

Dispatcher lines worth knowing:

| Line | Meaning |
|---|---|
| `Set dispatcher mode to AUTO` | Mode change accepted |
| `Starting! Start Service was requested.` | Status on |
| `Attempting to start the garage. Temporarily blocked because: …` | Starting, waiting for AGVs/bays |
| `Cannot start dispatch - …` | Start refused (stale, inconsistent or faulted) |
| `Sending type 1 command to b7` / `Received response from b7: …` | A C++ service call to the bay succeeded |
| `Cannot accept … job if dispatcher is not in MANUAL mode` | A job from the other mode was refused |

---

## 10. CI

```bash
gh pr checks 1018
```
```bash
gh run list --branch <branch> --limit 5 --json databaseId,headSha,status,conclusion,createdAt --jq '.[] | "\(.databaseId) \(.headSha[0:8]) \(.status) \(.conclusion) \(.createdAt)"'
```
**Jobs per attempt** (a run re-run with `--failed` has attempt 2):
```bash
gh api "repos/VolleyAutomation/volley/actions/runs/<run>/attempts/1/jobs?per_page=100" --jq '.jobs[] | select(.conclusion != "success" and .conclusion != "skipped") | "\(.id) \(.name) \(.conclusion)"'
```
**A job's log** (`gh run view --log-failed` printed nothing with gh 2.45):
```bash
gh api repos/VolleyAutomation/volley/actions/jobs/<job>/logs > job.log
```
```bash
grep -nE '##\[error\]|FAILED|Failed' job.log
```
**"The runner has received a shutdown signal … The operation was canceled"** means the CI machine went
away (infrastructure), not a test failure. Re-run just the failed jobs:
```bash
gh run rerun <run> --failed
```

---

## 11. Reading timestamps

ROS log stamps are Unix seconds (`[1793808642.313586177]`):
```bash
date -u -d @1793808642
```
Docker and nginx print UTC already. The NOC and patron apps may show local time.

---

## 12. The probe scripts

Both run in the central container through the entrypoint (section 6). They only create entities and wait.
They never send a request.

**`probe_graph.py`**: who serves each bay 7 service:
```python
import time
import rclpy

rclpy.init()
node = rclpy.create_node("probe_graph")
end = time.monotonic() + 6.0
while time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.2)
for service in ("/bay/b7/confirm_insert", "/bay/b7/confirm_retrieve", "/bay/b7/command"):
    request = "rq" + service + "Request"
    response = "rr" + service + "Reply"
    readers = node.get_subscriptions_info_by_topic(request, no_mangle=True)
    writers = node.get_publishers_info_by_topic(response, no_mangle=True)
    print(f"{service}: request readers={len(readers)} response writers={len(writers)}")
    for kind, infos in (("  rq reader", readers), ("  rr writer", writers)):
        for info in infos:
            gid = bytes(info.endpoint_gid[:12]).hex()
            print(f"{kind} {info.node_namespace}/{info.node_name} gid={gid}")
node.destroy_node()
rclpy.shutdown()
```

**`probe_clients.py`**: whether a fresh process can match each service:
```python
import time
import rclpy
from interfaces.srv import BayCommand, SetPayloadInfo
from std_srvs.srv import Trigger

rclpy.init()
node = rclpy.create_node("probe_clients")
targets = [
    (SetPayloadInfo, "/bay/b7/confirm_insert"),
    (Trigger, "/bay/b7/confirm_retrieve"),
    (BayCommand, "/bay/b7/command"),
    (Trigger, "/central/start"),
]
clients = [(name, node.create_client(srv, name)) for srv, name in targets]
deadline = time.monotonic() + 20.0
ready = {}
while time.monotonic() < deadline and len(ready) < len(clients):
    rclpy.spin_once(node, timeout_sec=0.2)
    for name, client in clients:
        if name not in ready and client.service_is_ready():
            ready[name] = round(20.0 - (deadline - time.monotonic()), 1)
for name, _ in clients:
    print(f"{name}: {'ready after ' + str(ready[name]) + ' s' if name in ready else 'NOT ready after 20 s'}")
node.destroy_node()
rclpy.shutdown()
```

---

## 13. The control container: running your own ROS commands

`control` (`app-comb_control`) is the stack's toolbox. Same build and same `/opt/volley` install as
`central`, the same DDS setup (super client, Fast DDS profile, `ROS_DISCOVERY_SERVER`), placed on the
central node, but it starts **no** ROS process: its command is `sleep infinity`. It's there so you can run
`ros2` commands and scripts against the live garage with the tools of the deployed version. For
watching data, Foxglove (section 14) is usually easier than the CLI.

| | `central` | `control` |
|---|---|---|
| Starts | `central.launch.py` (REST API, dispatcher, tracker, scheduler, …) | `sleep infinity` |
| Restarts on every `swarmctl deploy app` | Yes | No (only on a stack recreate or a new image) |
| Logs | fluentd | Docker's default driver (a "debug service" per the stack file) |
| Use for | Questions about central's own processes | Your own commands and probes |

**There is no `swarmctl` command for this. Use `docker exec` on the central node:**
```bash
K=$(docker ps -qf name=_control.)
```
An interactive shell with ROS set up:
```bash
docker exec -it "$K" /opt/volley/entrypoint.sh bash
```
**Always go through the entrypoint** (or `source /opt/volley/setup.bash` inside). `docker exec` doesn't run
the image's entrypoint by itself, so without it `ros2` isn't found or not set up. The entrypoint also runs
the discovery probe first, so a command starts only once the discovery server answers.

One command, without a shell:
```bash
docker exec "$K" /opt/volley/entrypoint.sh ros2 node list --no-daemon --spin-time 8
```
```bash
docker exec -it "$K" /opt/volley/entrypoint.sh ros2 topic echo /bay/b7/report --once
```
`ros2 run <package> <executable>` works the same way, for any executable in the image.
Use `-it` for anything interactive or long-running (Ctrl-C then stops it). Leave it out for one-shot output
you want to pipe or save.

**Things to know:**
- **Every command is a new DDS participant** (a fresh process), registering with the discovery server. That
  makes `control` a good comparison point: if something can't be reached from the REST API but can from
  `control`, the problem is in the REST API's process.
- **Super client:** the `ros2` graph commands see the whole graph, including the bays.
- **Commands with side effects act on the real garage:** `ros2 service call`, `ros2 topic pub`. Check
  the dispatcher is stopped (or that you mean it) before changing anything.
- **Files you copy in** stay until `control` is replaced (stack recreate or new image), so it's the place
  to keep the probe scripts during an investigation:
  ```bash
  cat probe_graph.py | docker exec -i "$K" sh -c 'cat > /tmp/probe_graph.py'
  ```
  ```bash
  docker exec "$K" /opt/volley/entrypoint.sh python3 /tmp/probe_graph.py
  ```

---

## 14. Foxglove: streaming the garage's data to your laptop

For **watching** data (topics, logs, the 3D garage view, the plan going to the scheduler), Foxglove is
easier than `ros2 topic echo` in a container: you see everything live on your laptop, with no ssh.

**How it works.** `central` runs `foxglove_bridge` (launched from `central.launch.py`), a WebSocket server on
port **8765**, published on the central node (swarm-deploy `main.yaml`). The bridge is a ROS process in
central's container. Central's container is a super client, so it sees the whole graph, bays and AGVs
included. The repo's `docs/architecture/discovery-server.md` gives that as the reason central is a super
client: "Runs the Foxglove bridge which requires topic introspection". The Foxglove app on your laptop
connects to that WebSocket over the tailnet and subscribes to what you open.

### Setup (once)

1. **Install the Foxglove desktop app** from `https://foxglove.dev/download` (Linux `.deb`, macOS:
   `brew install --cask foxglove-studio`, as in the repo's `docs/guides/mac-setup.md`). The desktop app is
   the safer choice for a garage: the web app at `app.foxglove.dev` is served over HTTPS, and browsers
   may block its plain `ws://` connection to the garage *(inferred: not tried)*.
2. **Sign in to the Volley Foxglove organization** to get the shared layouts (`mac-setup.md`: "select the
   shared **Simulation** layout").
3. **Optional: FoxNOC**, the Foxglove-based NOC replacement (`VolleyAutomation/foxnoc`). It isn't in
   the extension registry (licence limits), so install it by hand: get or build the `.foxe` file
   (`npm install`, `npm run package` in that repo), then in Foxglove: user icon → **Extensions** →
   **Install local extension** → the `.foxe` file, then choose the **FoxNOC** layout. Details are on the
   FoxNOC Confluence page linked from its README.

### Connecting to a garage

1. Check that the bridge answers (from your laptop, on the tailnet). `101 Switching Protocols` means it's
   up:
   ```bash
   curl -s -i -N -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H 'Sec-WebSocket-Protocol: foxglove.sdk.v1' http://central-comb-5675-pecos:8765/ | head -1
   ```
   Confirmed on 2026-11-04 for comb. The port exists only while that node's `app` stack runs. If the name
   doesn't resolve, use the full tailnet name (`central-comb-5675-pecos.tailfadbb4.ts.net`) or the
   address (`100.120.46.20`).
2. In Foxglove: **Open connection** → **Foxglove WebSocket** → `ws://central-comb-5675-pecos:8765`. Other
   garages: the same with their central node's name (`deploy_and_test.md` 3.2).
3. Choose a layout: **Simulation** (its 3D panel uses `/vis/*`, which the garage's `visualizer_node` publishes
   too) or **FoxNOC**.

### If the view looks empty

Seen on 2026-11-04 with the **FoxNOC (WIP)** layout on comb:
- **"Unknown panel type: foxnoc-extension.NOC - …"** (Service Call, Garage Status, Garage Control): the
  layout uses FoxNOC's panels, but the FoxNOC extension isn't installed in this app. Install the `.foxe`
  (Setup, step 3) and reload, or pick a layout that doesn't need it. A built `.foxe` is attached to the
  `v0.1.0-alpha` release (built from `main`), so no npm build is needed:
  ```bash
  gh release download v0.1.0-alpha --repo VolleyAutomation/foxnoc --pattern '*.foxe' --dir ~/Downloads/foxnoc-0.1.0
  ```
- **The 3D panel shows only a grid:** nothing is switched on for it. The data is there (checked from
  `control`: the visualizer publishes `/vis/agvs`, `/vis/bays`, `/vis/nodes`, `/vis/trays`,
  `/vis/environment`, … as marker arrays in frame **`map`**, volatile QoS). The garage publishes **no
  `/tf`**, so Foxglove can't work out a frame by itself. Click the 3D panel, then in its settings (the left
  sidebar's **Panel** tab, or the panel's gear). **Order matters** (confirmed on comb, 2026-11-04):
  the frame dropdowns stay empty, and you can't type in them, until Foxglove has received a message
  with that frame, so switch the topics on first:
  1. **Topics:** make `/vis/environment`, `/vis/nodes`, `/vis/edges`, `/vis/bays`, `/vis/trays`,
     `/vis/payloads`, `/vis/agvs` visible (and `/vis/layout_spaces`, `/vis/schedule_dag` if useful).
     **Transforms** then shows `(1)`.
  2. **Frame → Fixed frame** and **Display frame:** `map`.
  3. If nothing is in view, use **Fit to view** (the square icon on the panel's toolbar).

  Then **save the layout as a personal copy** (layout menu, top right → Save as), not over the shared
  organisation layout, so your teammates' layout doesn't change and yours reopens ready.

  Or load the shared **Simulation** layout, which already has a 3D panel set up this way
  (`docs/guides/mac-setup.md`).
- **Check what's arriving:** the left sidebar's **Topics** tab lists every topic the bridge offers, and
  **Problems** shows connection or schema errors.

### Topics worth knowing (as the bridge advertised them on comb)

| Topic | What it shows |
|---|---|
| `/central/rosout` | Log lines from central's processes, **including `rest_api`**: put a Log panel on it and filter for `recreating its client` or `timeout waiting for service` instead of grepping `docker logs` |
| `/bay/b7/rosout`, `/hito_proxy/rosout`, `/vis/rosout` | Logs of bay 7, the AGV proxy, the visualizer |
| `/central/plan_request`, `/central/plan_response` | What the dispatcher asks the **scheduler** and what it answers: the input and output of the code PR #1018 changes |
| `/central/pending_jobs`, `/central/active_jobs`, `/central/completed_jobs` | The dispatcher's job queue |
| `/central/report`, `/scheduler/report` | Dispatcher and scheduler reports (status, mode, jobs) |
| `/central/discrete_garage_state`, `/central/garage_snapshot`, `/central/discrete_events` | The garage tracker's state and the events applied to it |
| `/central/continuous_garage_info`, `/central/consistency_report`, `/central/garage_status` | Freshness, consistency and up/down status, the inputs to the dispatcher's start checks |
| `/bay/b7/report`, `/bay/b7/vehicle_pose`, `/bay/b7/PATRON/report`, `/bay/b7/SYSTEM/report` | Bay 7's state machine, vehicle position and doors |
| `/agv/a16/report`, `/agv/a16/faults`, `/central/a16/command_sequence` | One AGV's reports, faults and the commands sent to it |
| `/vis/agvs`, `/vis/bays`, `/vis/trays`, `/vis/payloads`, `/vis/schedule_dag`, … | The 3D garage view and the schedule graph |

### Things to know

- **It's the live garage.** Foxglove can also publish topics and call services, and FoxNOC sends operator
  commands. Treat those like the NOC.
- **Bandwidth.** Everything you open streams over the tailnet. Open what you need; the 3D view and the
  sensor topics (`radar`, `load_cells`) are the heavy ones.
- **What it can't show.** Foxglove shows topics and logs, not whether a particular DDS client has matched
  its server. For the REST API problem it shows the symptom (`/central/rosout`). The probes in
  sections 6 and 12 still answer *why*. One useful signal: if the bridge (a C++ process in central's
  container) shows bay 7's topics, central's container itself can see bay 7.
- **After a deploy,** `central` restarts and so does the bridge. Foxglove reconnects on its own after a short
  wait, or reopen the connection.
