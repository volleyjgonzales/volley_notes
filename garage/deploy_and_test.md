# Deploying and testing PR #1018 (SW2-1135)

Written 2026-11-02; local tip `8f9315c1` (on main `58bd75a3`). Sources: `~/volley` (CI workflows,
`docs/guides/simulation*.md`, `docker/docker-bake.hcl`, `controller_webview/`), `~/swarm-deploy` (`README.md`,
`swarm/.env`, `swarm/stacks/app/main.yaml`), `~/repos/vng-os` (the device OS) and this machine's Tailscale.
Steps marked *(inferred)* follow from how those pieces fit together; no repo documents a PR-deploy
procedure, so confirm them with Dan or Justin first.

## 1. Covered already

| Level | What ran | Result |
|---|---|---|
| Unit and scenario tests (local) | `scheduler` 194, `planner_core` 22, `scheduler_advanced_tests` 12, `motion_planner` 82, with `SCHEDULER_CHECK_RECORDINGS=1` | Pass on every commit; every recording identical |
| CI system tests (simulation) | All 13 groups: AGV moves, bay errors, blift insert/retrieve, charging, disabled components, dispatch control, misc, patron inserts, tray moves, triple-pick retrieves, VRC, vehicle sizes ([run 41479282871](https://github.com/VolleyAutomation/volley/actions/runs/41479282871)) | Pass on `a3370c4b` |

The CI system tests launch the whole stack (central, scheduler, simulated AGVs, bays, VRC) without any display.
Nightly site scenarios (fill and drain on the real site layouts) test `main`'s `sim-latest` image only, so
they do not cover the PR until it merges.

## 2. Simulation on the branch (local)

Build the whole workspace on the branch first: these tests launch central, the simulator and the bays, not
only the planner packages.

**Pass or fail, from any folder** (output arrives when it finishes, in `~/.cache/volley-in-container/logs/`):

```bash
volley-in-container sh 'launch_test src/system_tests/tests/system_fill_garage.py layout:=5675_pecos_sandbox_eng n_agvs:=1 real_time_factor:=10'
```

Then `system_drain_garage.py` the same way, and the `5675_pecos_sandbox_qa` layout. These are the nightly
job's runs, on your build.

**Watching it, with RViz:**

```bash
cd ~/volley && devc attach
```

The attached shell is zsh, so use the zsh setup file (`setup.bash` fails there: it finds its own folder
through a bash-only variable):

```bash
source install/setup.zsh
```

```bash
launch_test src/system_tests/tests/system_fill_garage.py layout:=5675_pecos_sandbox_eng n_agvs:=1 real_time_factor:=2 vis:=true
```

- `vis:=true` turns on the visualizer, Foxglove bridge and RViz (`src/launcher/launcher/sim_nodes.py`); the
  test's pass condition is the same either way. CI never passes it.
- `real_time_factor` 1 or 2 is watchable; 10 matches the nightly job.
- What the test checks: a generated scenario with one patron arrival per empty parking spot; it passes when
  every car is on a tray, every tray is on a parking or EV-charge node, and every bay is ready to insert or
  retrieve (time limit 6 h).

**Stopping it:** Ctrl+C in the terminal running `launch_test` (twice if it hangs); closing RViz alone leaves
the simulation running. After a run started through `volley-in-container`, check for leftovers from a
container shell:

```bash
ps aux | grep -E 'launch_test|ros2|rviz2|component_container' | grep -v grep
```

```bash
pkill -INT -f launch_test
```

Leftover nodes on the same ROS network confuse the next run; `export ROS_DOMAIN_ID=<0-101>` before
`launch_test` isolates a run, as the CI action does.

**Optional, main versus branch in the cloud:** `src/sim_metrics/sim_metrics/aws_batch_cli.py` runs batches of
full-garage simulations on AWS Batch and extracts metrics (AGV occupancy, job times). The same batch config
(`src/scenario/batch_configs/`) on `main` (`submit-batch-job -b <config>`) and on this branch
(`build-and-submit-batch-job -b <config>`) gives a behaviour comparison under load. Steps:
`docs/guides/simulation-in-cloud.md`.

## 3. Deploying to a garage

How a garage runs volley (`~/swarm-deploy/README.md`): one Docker swarm per garage; the central node deploys
the stacks, the bay computers join as workers. The `app` stack holds `central` (the scheduler is in it),
`control`, `noc` and one `bay<id>` service per bay. Every volley image is
`${VOLLEY_REGISTRY}:<component>-${VOLLEY_VERSION}`; the release sets `VOLLEY_VERSION` in `swarm/.env`
(26.41.1 on 2026-11-02). `swarmctl` is the tool run on the central node.

Docker terms, smallest to largest:

| Term | What it is | Volley example | See it with |
|---|---|---|---|
| Image | A read-only, versioned snapshot of a filesystem and start command, stored in a registry and pulled to a machine. Nothing runs. | `…/volley:central-pr-1018` | `docker image ls` |
| Container | A running (or stopped) process started from an image, on one machine. | the scheduler process on the eng computer | `docker ps` |
| Service | A swarm's standing order: "keep N containers of this image running, with these settings, on nodes matching these constraints". Swarm replaces a container that dies. | `app-eng_central`, `app-eng_bay3` | `docker service ls` |
| Task | One slot of a service: the swarm's record of one container it scheduled, with its state and node. | `app-eng_central.1` | `docker service ps <service>` |
| Stack | A named group of services deployed together from compose files; service names get the stack's name as a prefix. | `app-eng`, `global`, `site` | `docker stack ls` |

So the chain is: a stack holds services, each service keeps one task per replica, each task runs one
container, and each container is started from an image.

### 3.1 Before you go: images for the commit you want

PR CI pushes every runtime image tagged `pr-1018` (`volley:central-pr-1018`, `bay-pr-1018`,
`noc-pr-1018`, …, `docker/docker-bake.hcl`). The tag follows the PR's latest build that passed the
`runtime-images` job, so push first, then check that job passed for the pushed commit:

```bash
gh pr checks 1018
```

`git rev-parse --short origin/jmg/SW2-1135/scheduler-renames-and-cleanups` shows which commit that is.

### 3.2 Connecting to the central node (confirmed)

The central nodes are on your tailnet (`volleyautomation.com`) and run **Tailscale SSH**: `tailscale status`
lists them online, tagged `tag:vng-os-central`, with SSH host keys from Tailscale. The vng-os image creates
the login user **`ops`** (groups `docker` and `systemd-journal`, `vng-os-core-image.bb`) and joins the
tailnet with `tailscale up --ssh` (`tailscale-autoconnect`). Your shell history has
`ssh ops@central-comb-5675-pecos` from before.

| Garage | Tailnet name | Address |
|---|---|---|
| Pecos eng | `central-eng-5675-pecos` | 100.117.201.60 |
| Pecos bench | `central-5675-pecos-bench` | 100.116.92.11 |
| Pecos QA | `central-qa-5675-pecos` | 100.108.122.9 |
| Pecos combined | `central-comb-5675-pecos` | 100.120.46.20 |

1. Check the node is online from your laptop:
   ```bash
   tailscale status | grep central
   ```
2. Log in. Tailscale SSH authenticates you by your tailnet login, so there is no password or SSH key to
   set up; the tailnet's access rules decide whether `ops` is allowed:
   ```bash
   ssh ops@central-eng-5675-pecos
   ```
   `tailscale ssh ops@central-eng-5675-pecos` does the same. If the rules require a fresh check, the
   command prints a login link to open in the browser first. The full MagicDNS name,
   `central-eng-5675-pecos.tailfadbb4.ts.net`, works too.
3. On the node, `swarmctl` is on the `PATH` (vng-os's `.bashrc` adds `/data/swarm/bin`), and `ops` may run
   `docker` without `sudo`.

What is on the node: neither the volley repo nor a git checkout of swarm-deploy. A release is a Mender
artifact that `tools/swarm-artifact` builds in swarm-deploy's CI, and vngOS's swarm-deploy update module
unpacks it into `/data/swarm` (the previous release is kept in `/data/.swarm-last` for rollback):

| Path under `/data/swarm` | From |
|---|---|
| `.env`, `stacks/manifest.yaml`, `stacks/{app,global,site}/…` | swarm-deploy's `swarm/` folder, the git-tracked files only |
| `bin/swarmctl` | the `swarmctl` command, built from `swarmctl/` |
| `metadata.json` | the build's branch, commit and version (what `swarmctl info` prints under Release) |
| `.env.local` | the node's own overrides; not in the artifact, carried over by every release install |

`swarmctl` is Python, not compiled: a [shiv](https://shiv.readthedocs.io) zipapp (`poe build` in
`swarmctl/pyproject.toml`), one zip file holding swarmctl's code and its dependencies (click, rich,
python-on-whales, jinja2, requests-aws4auth, …), with a `#!/usr/bin/env python3` line at the top so it runs like any
executable. On first run shiv unpacks the dependencies into `~/.shiv/` and reuses them afterwards. It
needs Python 3.14 on the node; vngOS's image installs `python3`, and its Yocto release ships 3.14. `head -c 100 /data/swarm/bin/swarmctl` shows the
shebang, and `python3 -m zipfile -l /data/swarm/bin/swarmctl | head` lists what is inside.

The volley code reaches the node only as Docker images (`volley:central-…`, `…:noc-…`), pulled when a
stack is deployed.

### 3.3 What the eng node showed on 2026-11-02

vngOS is the **Volley Next Generation Operating System** (`~/repos/vng-os`): the Yocto-built Linux on every
central and bay computer, with Mender for over-the-air updates and Tailscale for networking.

- **Login banner:** the vngOS release (`Version: 26.44`), uptime, RAM, the two filesystems (`/` is the
  read-only-style OS root, 18.6 GiB; `/data` is the 1.8 TiB data partition that holds `/data/swarm`,
  logs and artifacts), and two services: Docker and Mender Connect (Mender's remote-access agent).
- **`swarmctl info`:**
  ```text
  ops@central-eng:~$ swarmctl info
  Release
    branch        next
    commit        0d2054b3b33336bc98478d8385b772a1c8b5509d
    commit_short  0d2054b
    dirty         False
    version       0d2054b

  Environment
    site-name      5675-pecos
    site-sub-name  eng
    fq-site-name   5675-pecos-eng
    swarm-root     no
    manual-stacks  -

  Stacks
    app  (app-eng)

  Labels
    Engine
      device=central-x86-64
      fq_site_name=5675-pecos-eng
  ```
  - *Release*: the swarm-deploy tree installed under `/data/swarm`, read from the Mender artifact's
    metadata. `branch` is the branch CI built the artifact from (`.call-mender-artifact.yml` passes
    `github.head_ref || github.ref_name` to `tools/swarm-artifact --branch`), not a branch that exists
    today. `next` was swarm-deploy's integration branch until PR #51 merged it into `main` on 2026-10-06
    (`fbb5977`, tagged `26.41`) and it was deleted. So this node runs a push build of `next` at `0d2054b`
    ("ensure only the overlay network is used for dds participants", 2026-10-02). That build is untagged,
    so `version` is the short sha, not a calendar version. Its changes are in `26.41` and later.
  - *Environment*: site `5675-pecos`, sub-site `eng`, so this node owns the stack `app-eng`; `swarm-root:
    no`: the Pecos garage is one swarm, and another central node is its root (the map server's image comes
    from `central-comb:4000`, so probably `central-comb-5675-pecos`). A non-root node may still deploy its
    own `app`.
  - *Stacks*: what this node may deploy (`app`, as `app-eng`), not what is running.
  - *Labels*: the engine labels swarm uses to place services (`device`, `fq_site_name`).
- In the listings below, `<ecr>` is `628548651667.dkr.ecr.us-west-2.amazonaws.com`, and `…` marks
  text, rows or columns cut to fit (the empty PORTS column, COMMAND and CREATED).
- **`docker service ls`** lists every service in the swarm, whichever node runs it:
  ```text
  ops@central-eng:~$ docker service ls
  ID             NAME                    MODE         REPLICAS   IMAGE
  bjrbxeq36q10   global_log-collector    global       3/3        fluentd:v1.19.3-1.0
  5hh9f1uab8xj   global_logstore-agent   global       3/3        <ecr>/logstore:agent-1.0.0-rc1
  2puh4d32podl   site_map-server         replicated   1/1        central-comb:4000/volley:mapserver-bay21-enable
  w52b7nphaola   site_mosquitto          replicated   1/1        eclipse-mosquitto:2.0.22
  r32nnf3o3yjx   site_otel-collector     replicated   1/1        otel/opentelemetry-collector-contrib:0.156.0
  5v8sqf7yp721   site_prometheus         replicated   1/1        prom/prometheus:v3.13.1
  ops@central-eng:~$ docker service ls --format '{{.Name}}  {{.Image}}' | grep app-eng
  ops@central-eng:~$
  ```
  - *Names* are `<stack>_<service>`: two stacks, `global` and `site`. **No `app-eng_*` service, so the eng
    application is not running** (the `grep` prints nothing).
  - *MODE* `global` runs one task on every node that matches the constraints (here every central node:
    `engine.labels.device == central-x86-64`), so `3/3` means three central nodes in the Pecos swarm.
    `replicated` runs a fixed count, here one; `1/1` is running/wanted.
  - `global` collects logs (`log-collector` is fluentd on port 24224, which the app's services log to;
    `logstore-agent` uploads `/data/logs` and `/data/artifacts` to the team's log store). `site` is the garage-wide services the
    root deploys: the map server, the MQTT broker (mosquitto) and telemetry (OpenTelemetry, Prometheus).
  - The map server runs a test build, `mapserver-bay21-enable`, from the garage registry, not a release
    image from ECR.
  - *PORTS* is empty because the services publish in `mode: host` (on the node itself), which this column
    does not show; `docker container ls` does.
- **`docker container ls`** shows only the containers on this node:
  ```text
  ops@central-eng:~$ docker container ls
  CONTAINER ID   IMAGE                            STATUS      PORTS                         NAMES
  ec3c220a7ee3   <ecr>/logstore:agent-1.0.0-rc1   Up 4 days                                 global_logstore-agent.0qwfqr….xvsece…
  f45a9fa917ec   fluentd:v1.19.3-1.0              Up 4 days   0.0.0.0:24224->24224/tcp, …   global_log-collector.0qwfqr….meecpy…
  a495b688c29a   registry:3                       Up 4 days   0.0.0.0:4000->5000/tcp, …     local-registry
  ```
  - Two are this node's tasks of the `global` services, named `<service>.<node id>.<task id>`. None of
    the `site` services run here, which fits `swarm-root: no`: they run on the root.
  - `local-registry` is not a swarm service. vngOS starts it on every central node as a systemd unit
    (`local-registry.service` in `vng-os`: `docker run registry:3`, port 4000, storage in
    `/data/rootfs/var/lib/local-registry`, garbage collection daily at 03:00). Only the root's is used:
    vngOS's `apply-device-config` sets `LOCAL_REGISTRY` to the root's hostname with `:4000` on every node,
    `central-comb:4000` here, which confirms `central-comb` is the root. dockerd trusts it over plain
    HTTP (`--insecure-registry`).
  - After a deploy, `app-eng_central`, `app-eng_control` and `app-eng_noc` containers appear here; the
    `bay<id>` containers run on the bay computers.
- **`docker image ls`** is the images cached on this node (abridged; `U` = in use by a container):
  ```text
  ops@central-eng:~$ docker image ls
  IMAGE                                              ID             DISK USAGE   CONTENT SIZE   EXTRA
  <ecr>/logstore:agent-1.0.0-rc1                     c600b6b377f6   382MB        98.5MB         U
  <ecr>/volley:central-26.20-latest                  ba2bfeb89169   2.28GB       459MB
  <ecr>/volley:central-26.33                         b737cc17c0fd   2.32GB       472MB
  <ecr>/volley:central-latest                        6a9db7096aa4   2.32GB       472MB
  <ecr>/volley:noc-26.33                             4beb32b6bdd6   689MB        172MB
  …
  central-comb:4000/volley:central-SW2-568           d8d6721ec0b0   2.32GB       472MB
  central-comb:4000/volley:central-central-auth-v3   3227d6e30e43   2.46GB       506MB
  central-comb:4000/volley:control-central-auth-v3   b361ff63ea2d   2.46GB       506MB
  central-comb:4000/volley:noc-central-auth-v3       b3b7c235b83c   688MB        172MB
  …
  fluentd:v1.19.3-1.0@sha256:89876975…               898769755998   284MB        81.6MB         U
  registry@sha256:8a7c1aae…                          8a7c1aae9db5   84.5MB       20.5MB         U
  ```
  - Release images from ECR (`26.20-latest`, `26.33`, `latest`), none for the current release `26.41.1`:
    no image of it is cached on eng.
  - Test builds others pushed to the garage registry, each a `central-`, `control-` and `noc-` set:
    `SW2-568`, `SW2-640`, `agv-id`, `capi-debug`, `central-auth-v3` (the one `.env.local` points at),
    `insert-bay-debug`, `rot-n-firmware`. Pushing a set to `central-comb:4000` and pointing
    `.env.local` at it is how the team tests branch builds; using the PR's ECR tag does the same without
    a push.
  - Images stay cached after their containers stop. No `pr-1018` image is here yet, so the first deploy
    downloads about 1.1 GB compressed (CONTENT SIZE: `central` and `control` ~0.5 GB each, `noc` 0.17 GB),
    about 5 GB on disk.
- **`/home/ops` is empty.** Nothing to keep there: the release, overrides and generated files are under
  `/data/swarm`, logs and artifacts under `/data`.
- **`/data/swarm/.env.local`** is set up for someone else's test: `VOLLEY_REGISTRY="${LOCAL_VOLLEY_REGISTRY}"`
  (images from the garage's own registry instead of AWS ECR) and `VOLLEY_VERSION=central-auth-v3`. Changing it
  undoes their setup; ask first. The PR's images are in ECR, so the registry line has to go back to ECR too:
  setting only `VOLLEY_VERSION=pr-1018` would look for `…/volley:central-pr-1018` in the local registry.

### 3.4 Running the PR build *(inferred)*

1. Pick the garage (eng or bench first), check with whoever set up `.env.local`, and tell the others.
2. Note the current state, so you can compare and go back:
   ```bash
   swarmctl info
   ```
   ```bash
   docker stack ls
   ```
   ```bash
   docker service ls --format '{{.Name}}  {{.Image}}'
   ```
   `swarmctl info` is the release and site (3.3). `docker stack ls` lists the stacks deployed in the whole
   swarm, one line each with its name and number of services; on eng on 2026-11-02 it listed only
   `global` and `site`, so no `app-eng` (the application was not running). `docker service ls` lists every
   service with the image it runs; the `--format` keeps only those two columns.
3. Read the device-local overrides and keep a copy to restore. **Permissions (checked on comb,
   2026-11-04):** `/data/swarm` belongs to `root`, so `ops` can't create files there, but `.env.local`
   belongs to `ops` and can be written. Keep the copy in your home folder:
   ```bash
   cat /data/swarm/.env.local
   ```
   ```bash
   cp /data/swarm/.env.local ~/env.local.before-pr-1018
   ```
4. Point the node at ECR and the PR's tag: comment out a `VOLLEY_REGISTRY` override, and replace the
   `VOLLEY_VERSION` line; other lines stay:
   ```bash
   sed -e 's/^VOLLEY_REGISTRY=/#VOLLEY_REGISTRY=/' -e 's/^VOLLEY_VERSION=.*/VOLLEY_VERSION=pr-1018/' /data/swarm/.env.local > /tmp/env.local.new && cat /tmp/env.local.new > /data/swarm/.env.local
   ```
   `sed` writes the edited copy to `/tmp`, then `cat … >` overwrites `.env.local`'s contents, which only
   needs write permission on the file. **Don't use `sed -i` here:** it creates a temporary file next to
   the original, in `/data/swarm`, and fails with "couldn't open temporary file … Permission denied".
   Each `-e` is one substitution, `s/<pattern>/<replacement>/`, tried on every line; `^` anchors the
   pattern at the start of the line:
   - `s/^VOLLEY_REGISTRY=/#VOLLEY_REGISTRY=/` puts `#` in front of a line that starts with `VOLLEY_REGISTRY=`,
     turning it into a comment, so the release's ECR registry from `/data/swarm/.env` applies again.
   - `s/^VOLLEY_VERSION=.*/VOLLEY_VERSION=pr-1018/` replaces a whole `VOLLEY_VERSION=` line (`.*` is the rest
     of the line) with `VOLLEY_VERSION=pr-1018`.

   On eng the two lines change from
   ```text
   VOLLEY_REGISTRY="${LOCAL_VOLLEY_REGISTRY}"
   VOLLEY_VERSION=central-auth-v3
   ```
   to
   ```text
   #VOLLEY_REGISTRY="${LOCAL_VOLLEY_REGISTRY}"
   VOLLEY_VERSION=pr-1018
   ```
   A line that does not start exactly that way (`export VOLLEY_VERSION=…`, a leading space) is left alone,
   and a missing `VOLLEY_VERSION` line is not added, so check the result:
   ```bash
   grep -E '^(VOLLEY_REGISTRY|VOLLEY_VERSION)=' /data/swarm/.env.local
   ```
   It should print only `VOLLEY_VERSION=pr-1018`. If it prints nothing, add the line:
   ```bash
   echo 'VOLLEY_VERSION=pr-1018' >> /data/swarm/.env.local
   ```
5. Deploy this node's application stack:
   ```bash
   swarmctl deploy app
   ```
   Nothing needs stopping first. `docker stack deploy` brings a running stack to the new files in place:
   swarm replaces the containers of each service whose settings changed (by default it stops the old
   container, then starts the new one), removes services no longer in the files (`prune=True`), and leaves
   the rest running. It touches only `app-eng`, not `global` or `site`. On eng the stack was not running,
   so the deploy simply creates it.
6. Check that its services run the PR's images from ECR, then watch them come up:
   ```bash
   docker service ls --format '{{.Name}}  {{.Image}}' | grep app-eng
   ```
   ```bash
   swarmctl watch
   ```
   Expect `app-eng_central  628548651667.dkr.ecr.us-west-2.amazonaws.com/volley:central-pr-1018` and the
   same tag on `control`, `noc` and the bays.
7. Follow the logs while testing (`swarmctl logs --help` shows how to pick one service, such as central):
   ```bash
   swarmctl logs
   ```
8. After a newer push, a plain deploy refreshes only some services. `swarmctl` deploys with
   `resolve_image="never"`, so a spec says `…:central-pr-1018`, not the image's digest, and a new push
   changes nothing in it. But every deploy stamps a new `DEPLOY_ISO_TIMESTAMP` into the command of
   `central` and each `bay<id>` (`artifacts_output_dir:=/artifacts/${DEPLOY_ISO_TIMESTAMP}`), so those
   two restart on every deploy, and a new container pulls its tag again (Docker's default in swarm).
   `control`, `noc` and the bay guidance services keep their old containers. To refresh all of them,
   recreate the stack *(inferred: check the running image afterwards)*:
   ```bash
   swarmctl remove app
   ```
   ```bash
   swarmctl deploy app
   ```
   For PR #1018 a plain deploy is enough: the scheduler and the REST API (`rest_api`, started by
   `launcher/central_nodes.py`) both run in `central`, which always restarts. To check which commit a
   service runs, read the `GITSHA` that the runtime images carry (on the node running it):
   ```bash
   docker exec "$(docker ps -qf name=_central.)" printenv GITSHA
   ```
   It is 7 characters and should match `git rev-parse --short=7 origin/jmg/SW2-1135/scheduler-renames-and-cleanups`.

### 3.5 What `swarmctl deploy app` does with that line

Read from `~/swarm-deploy/swarmctl/src/swarmctl` (`commands/deploy.py`, `env.py`, `docker.py`,
`selection.py`) and vngOS's `apply-device-config`.

1. **The environment.** `load_environment` reads three files in order, each overriding the one before,
   with `${…}` interpolated: `/data/config/device.env` (written by vngOS from the device configuration
   Mender delivers: `SITE_NAME`, `SITE_SUB_NAME`, `AWS_REGISTRY`, `LOCAL_REGISTRY`, …), then
   `/data/swarm/.env` (the release: `VOLLEY_REGISTRY="${AWS_REGISTRY}/volley"`, `VOLLEY_VERSION=26.41.1`,
   ports), then `/data/swarm/.env.local`. With the `VOLLEY_REGISTRY` override commented out, the release's
   ECR value stands; `VOLLEY_VERSION=pr-1018` wins over the release's version. The values become process
   environment variables, along with `FQ_SITE_NAME` (`5675-pecos-eng`) and `SWARM_ROOT_DIR`.
2. **Which stack.** `deployable_stacks` reads `stacks/manifest.yaml` and keeps what this node may deploy:
   `app`, deployed under the name `app-eng` because `SITE_SUB_NAME=eng`.
3. **Prerequisites.** Missing bind-mount directories are created, and missing docker secrets are fetched
   from AWS Secrets Manager with the device's credentials (`/data/config/aws/`).
4. **The bays.** `app/bay.yaml.j2` is rendered for this site's bays: the swarm nodes labelled with this
   `fq_site_name` (or `BAY_IDS_OVERRIDE`), one `bay<id>` and `bay<id>-guidance` service each.
5. **The deploy.** `docker stack deploy` runs with every `app/*.yaml` plus the rendered bay file
   (`prune=True`: services no longer in the files are removed; `with_registry_auth=True`: this node's
   registry login is sent along to the nodes that pull). Docker interpolates each `image:` line from the
   environment: `${VOLLEY_REGISTRY}:central-${VOLLEY_VERSION}` becomes
   `628548651667.dkr.ecr.us-west-2.amazonaws.com/volley:central-pr-1018`.
6. **The swarm.** The manager compares each service with what runs. A changed image tag counts as an
   update; unchanged services are left alone. `central` and the `bay<id>` services always count as
   changed, because their command carries the deploy's timestamp. It schedules each service's task by its placement
   constraints: `central`, `control`, `noc` on the node with this `fq_site_name`; `bay<id>` on the bay
   computer with that `bay_id`.
7. **The pull.** The docker daemon on each chosen node pulls the image from ECR, logging in through the
   ECR credential helper that vngOS configured (`credHelpers` in Docker's config, account and region
   from the device configuration), then starts the container. Ports such as the NOC's 8011 are published
   on that node (`mode: host`).

`swarmctl watch` and `docker service ps app-eng_central` show the tasks moving from pending to running;
an image that cannot be pulled shows there as a rejected task with the reason.


### 3.5.1 What runs in the `central` service

How to trace it, from the swarm file to the nodes:

1. `swarm/stacks/app/main.yaml` (swarm-deploy): `central` runs image `${VOLLEY_REGISTRY}:central-${VOLLEY_VERSION}`
   with `command: [artifacts_output_dir:=/artifacts/${DEPLOY_ISO_TIMESTAMP}]`, and publishes ports 5000
   (REST API) and 8765 (Foxglove bridge).
2. `docker/Dockerfile`, stage `runtime-central`: `ENTRYPOINT ["/opt/volley/entrypoint.sh", "ros2", "launch",
   "launcher", "central.launch.py"]`. Swarm's `command` is appended to it, so it becomes the launch
   argument `artifacts_output_dir:=…`. The stage also sets `ROS_SUPER_CLIENT=true`.
3. `src/launcher/launch/central.launch.py` and `src/launcher/launcher/central_nodes.py` list the
   processes, in launch order (the number in a log prefix such as `[rest_api-1]` is that order):

| # | Process (log prefix) | What it is |
|---|---|---|
| 1 | `rest_api` | `central_api`'s REST API (Flask, port 5000): patron apps, kiosk, confirm-insert/retrieve |
| 2 | `proxy_node` | `agvhito` AGV proxy (not in simulation) |
| 3 | `central` | One multi-threaded component container (`/central/central_nodes`) holding the components `agv_monitor`, `safety_hardware_monitor`, `consistency_monitor`, `dispatcher`, `garage_tracker`, `garage_monitor` and **`scheduler`** (`volley::SchedulerComponent`) |
| 4 | `metrics_recorder` | `central`'s metrics (OTel endpoint) |
| 5 | `visualizer_node` | `vis`, for Foxglove (FoxNOC) |
| 6+ | `foxglove_bridge` | The Foxglove bridge (port 8765) |
| | recorder | rosbag recorder for everything except `/bay/`, into `artifacts_output_dir` |

So the 2026-11-03 logs `[rest_api-1]` and `[central-3] … [central.garage_tracker]` both come from this
service. PR #1018 changes the `scheduler` component and `rest_api`, both in it.

To see it live on the central node:
```bash
docker exec "$(docker ps -qf name=_central.)" ps -eo pid,etime,args
```

**`control` next to it.** The `control` service (`app-comb_control`) has the same build and DDS setup
(super client, profile, discovery server) on the same node, but starts no ROS process (`sleep infinity`).
It's the toolbox for running your own `ros2` commands and scripts against the garage.
`swarmctl` has no command for that. Use `docker exec` through the image's entrypoint:
```bash
docker exec -it "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh bash
```
Details and cautions: `garage_troubleshooting_reference.md` section 13.
This lists the container's processes with their uptime. `etime` also shows when `rest_api` last
(re)started, which is the check section 1.6.1 of the findings needs.

### 3.5.2 Confirming the deploy has the rest_api fix (`073556ea`)

The commands below find the central container with `name=_central.`, which matches
`<stack>_central.<n>.<id>` whatever the stack is called: `app-eng` on eng, `app-<sub-site>` elsewhere
(`swarmctl info` shows it). They must run on the node where `central` runs. If
`docker ps --format '{{.Names}}' | grep _central` prints nothing, `central` isn't running on this node:
either the app stack isn't deployed, or it runs elsewhere (`docker service ps <stack>_central` shows the
node).

1. **Before deploying**, check that CI pushed images for that commit: the `runtime-images / build-push`
   job of the run for `073556ea` must pass. If you deploy earlier, `central` pulls the previous
   `pr-1018` images.
   ```bash
   gh pr checks 1018 | grep runtime-images
   ```
   ```bash
   gh run list --branch jmg/SW2-1135/scheduler-renames-and-cleanups --limit 3 --json headSha,status,conclusion --jq '.[] | "\(.headSha[0:8]) \(.status) \(.conclusion)"'
   ```
2. **After `swarmctl deploy app`**, on the central node, check which commit the image was built from
   (it should print `073556e`):
   ```bash
   docker exec "$(docker ps -qf name=_central.)" printenv GITSHA
   ```
3. **Check the code itself**: the installed `rest_api.py` should have the refresh method:
   ```bash
   docker exec "$(docker ps -qf name=_central.)" sh -c 'grep -n "def refresh_bay_clients" $(find /opt/volley -name rest_api.py -path "*central_api*")'
   ```
4. **Check the container is new**: `rest_api`'s `etime` should match the time since the deploy:
   ```bash
   docker exec "$(docker ps -qf name=_central.)" ps -eo etime,args | grep rest_api
   ```
5. **In use** (only if the race happens): within about 10 s of startup, the log shows
   `/bay/bN/confirm_… not discovered, recreating its client`:
   ```bash
   docker logs "$(docker ps -qf name=_central.)" 2>&1 | grep 'recreating its client'
   ```
   The stack logs to fluentd. `docker logs` still reads the local copy Docker keeps of the output
   (dual logging, Docker 20.10 and later) *(inferred: if it says the driver doesn't support reading, use
   `swarmctl logs`)*.

If step 2 shows an older commit, wait for CI and deploy again. `central` restarts on every deploy, so a
plain `swarmctl deploy app` pulls the new image (3.4, step 8).

### 3.7 Deploying a local build, without CI (`tools/local-runtime-deploy`)

For a branch that has no PR or CI images yet (for example the DDS investigation branch), build the runtime images on
the laptop and push them straight to the central node's own registry. Used 2026-11-04: `dds-diag-5f72fca`, then
`dds-diag-29712d9` (commit `29712d97`, the investigation branch's head), all five images pushed to `central-comb:4000`;
the `5f72fca` tags were deleted afterwards (step 5). Not yet deployed.

**What the script does** (`volley/tools/local-runtime-deploy <TAG> <REGISTRY-HOST> [TARGET=runtime]`):
- refuses to run inside the devcontainer, so run it on the laptop host
- checks that `/etc/docker/daemon.json` lists the registry as an insecure registry
- runs `docker buildx bake --push -f docker/docker-bake.hcl runtime` with `TAG`, `REGISTRY=<host>/volley` and
  `COMMIT_SHA=$(git rev-parse HEAD)` (so `GITSHA` in the images is the checked-out commit)
- the `runtime` group builds `bay`, `central`, `control`, `mapserver` and `noc`, every volley image the `app` stack
  needs, tagged `<host>/volley:<image>-<TAG>`

**Prerequisites on this laptop (all checked):**
- Docker 29.9.2 with buildx 0.38.1
- `/etc/docker/daemon.json`: `"insecure-registries": ["central-comb:4000"]`
- comb's registry answers at `http://central-comb:4000/v2/` (200)
- AWS credentials (`jon.gonzales`) for the ECR base image `ros2:lyrical-core-20260924-1` and the build cache

**Steps:**
1. On the laptop host, check out the commit to deploy with a clean working tree (`git status` empty). **No `docker login`
   for ECR:** this laptop's `~/.docker/config.json` hands the ECR registry to the `ecr-login` credential helper
   (`docker-credential-ecr-login` 0.6.4), which gets a token from the AWS credentials on every pull. `docker login`
   fails with `error storing credentials … not implemented`, because that helper can't store passwords. To check
   ECR access without pulling:
   ```bash
   docker buildx imagetools inspect 628548651667.dkr.ecr.us-west-2.amazonaws.com/ros2:lyrical-core-20260924-1
   ```
2. Build and push, with a tag that names the commit, so it can't clash with other local tags (the registry already has
   `bay-refactor`):
   ```bash
   tools/local-runtime-deploy dds-diag-$(git rev-parse --short=7 HEAD) central-comb:4000
   ```
   It's a full build of the workspace inside Docker (no sccache unless `USE_SCCACHE_S3=true` and the AWS variables
   are exported), so expect it to take a while the first time. Check the push:
   ```bash
   curl -s http://central-comb:4000/v2/volley/tags/list
   ```
3. On comb, point `.env.local` at the local registry and the new tag (in-place edit; `sed -i` fails there):
   ```bash
   sed -e 's/^#VOLLEY_REGISTRY=/VOLLEY_REGISTRY=/' -e 's/^VOLLEY_VERSION=.*/VOLLEY_VERSION=dds-diag-<sha>/' /data/swarm/.env.local > /tmp/env.local.new && cat /tmp/env.local.new > /data/swarm/.env.local
   ```
   Then `swarmctl deploy app`, and check `docker exec "$(docker ps -qf name=_central.)" printenv GITSHA` (the 7-character
   commit).
4. **Going back:** comment `VOLLEY_REGISTRY` out again and set `VOLLEY_VERSION=pr-1018` (or the release), then deploy.
   If `VOLLEY_REGISTRY` stays active with a tag that's only in ECR, every task fails with `No such image` (2026-11-04,
   findings 1.11).
5. **Deleting old local tags:** comb's registry is vng-os's `local-registry` (`registry:3`, deletes enabled). Delete each
   image's manifest by digest, which removes the tag; `local-registry-gc.timer` (about 03:00 daily) frees the space.
   Deleting a digest removes every tag on it, so first check it isn't shared with a tag you keep (`dds-diag-5f72fca`
   vs `dds-diag-29712d9`: all five differ). Never delete the tag comb is running.
   ```bash
   R=http://central-comb:4000/v2/volley; A='application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'; for i in bay central control mapserver noc; do d=$(curl -sI -H "Accept: $A" "$R/manifests/$i-dds-diag-<old-sha>" | tr -d '\r' | sed -n 's/^Docker-Content-Digest: //Ip'); [ -n "$d" ] && curl -s -o /dev/null -w "$i-dds-diag-<old-sha>: %{http_code}\n" -X DELETE "$R/manifests/$d"; done
   ```
   Each prints `202`. Don't run `registry garbage-collect` by hand while someone may be pushing.
6. **Seeing what's in the registry:** `uv run garage/scripts/registry_versions.py central-comb:4000`
   (a uv script; uv fetches `rich` on first run) prints a colour table, one row per version, newest first: build
   time (local), age, `GITSHA`, and a column per image (● present, ✗ missing). `dds-diag-*` rows are highlighted;
   `--highlight <prefix>` (repeatable) picks others.
   The registry is shared: most of its ~68 versions are teammates' branches, so delete only your own tags.

Pushing only adds tags to comb's registry; it doesn't change what's running until someone deploys.

### 3.6 Going back (do not skip)

`.env.local` survives release installs, so a forgotten override keeps the garage on the PR build after
the next release. Put the saved file back and redeploy; if the application was not running before (as on
eng on 2026-11-02), remove it instead of redeploying, so the garage is as you found it:

```bash
cat ~/env.local.before-pr-1018 > /data/swarm/.env.local
```

```bash
swarmctl deploy app
```

or, when it was not running before:

```bash
swarmctl remove app
```

```bash
docker service ls --format '{{.Name}}  {{.Image}}'
```

## 4. Sending jobs: the NOC (`controller_webview`)

NOC stands for **Network Operations Center**: the operators' interface, with full control of the garage
and a 3D view, and no login (it relies on the network being private). `~/volley/controller_webview` is the
NOC, a PHP web app. Its README (2021: microk8s, salt-configs, a hard-coded
central IP) is out of date. Today the NOC runs as the `noc` service of the `app` stack: image
`noc-${VOLLEY_VERSION}`, port 80 published as **8011**, files under `/webviewer` (`docker/noc.Dockerfile`).

- **Open it in the browser on your laptop** (on the tailnet), not on the central node:
  `http://central-eng-5675-pecos:8011/webviewer/`. The port is published on the central node itself, so
  it exists only while that node's `app` stack runs: on 2026-11-02 no `app-*` service ran anywhere in the
  Pecos swarm, and every central node refused port 8011 (`curl` from the laptop, exit 7), though
  `central-eng-5675-pecos` resolves (100.117.201.60). Deploy the `app` stack first (section 3.4).
- **If the name does not resolve in Chrome:** Chrome's "Use secure DNS" can bypass Tailscale's MagicDNS;
  use the full name `http://central-eng-5675-pecos.tailfadbb4.ts.net:8011/webviewer/` or the address
  `http://100.117.201.60:8011/webviewer/`. To check from a terminal first:
  ```bash
  curl -I http://central-eng-5675-pecos:8011/webviewer/
  ```
- **What a button does:** a POST to central's REST API on port **5000**. `central` carries the network alias
  `scheduler` because the PHP hard-codes `http://scheduler:5000/` (swarm-deploy's comment: "the apiUrl is
  hardcoded 24 places"). The endpoints behind the actions:

| Action | Endpoint |
|---|---|
| Retrieve | `api/dispatch/retrieve` (`payload_id`, `payload_id_claim`) |
| Repark tray | `api/dispatch/repark-tray` |
| Move AGV / tray to node | `api/dispatch/move-agv`, `api/dispatch/move-tray` |
| Bay confirm insert / retrieve | `api/bay/b<id>/confirm-insert`, `api/bay/b<id>/confirm-retrieve` |
| Start / stop / pause, mode | `api/dispatch/start`, `stop`, `pause`, `set-mode` |
| Stop EV charging | `api/dispatch/stop-ev-charging` |
| Bay readiness ratio | `api/scheduler/set-bay-readiness-ratio` |
| Enable/disable AGV, tray, node | `api/garage/agv/set-disabledness`, `tray/…`, `node/…` |
| Overrides | `api/garage/set-tray-pose`, `api/garage/tray/set-payload` |

The same calls work from a terminal on the tailnet *(inferred from the published port)*, for example:

```bash
curl -X POST http://central-eng-5675-pecos:5000/api/dispatch/retrieve -H 'Content-Type: application/json' -d '{"payload_id": "<guid>", "payload_id_claim": "<guid>"}'
```

### 4.0 The dispatcher, and taking control of it from the NOC (confirmed in the code)

Sources: `src/central/include/central/dispatch.hpp`, `src/central/src/dispatch.cpp`, `dispatch_ros.cpp`,
`central_timing.hpp`, and the NOC's `controller_webview/js/noc/` (`nocControlHandler.js`, `noc3DRendering.js`,
`noc3DMenus.js`).

#### What the dispatcher is

- **A ROS 2 node.** It's the component `central::DispatchComponent`, loaded as `/central/dispatcher`
  in the `central` component container (the `[central-3]` process, 3.5.1), next to the garage tracker and
  the scheduler. There is **one per garage**: each site's `app` stack runs one `central`.
- **What it does.** It's the garage's job runner, in its own header's words, "responsible for dispatching
  commands to our garage entities". Every 1.8 s (`kDispatchJobsPeriod`) it:
  1. keeps the **job queue**: retrieve, repark, move AGV/tray, insert, clean, rebalance, charge. Jobs arrive
     from the REST API, the NOC and bay events.
  2. asks the **scheduler** for a plan for the pending jobs (the `/scheduler/plan` service, the code this
     PR changes).
  3. **sends the plan's commands** to the AGVs, bays, VRCs and VECS as their turn comes, and marks
     jobs complete.
  4. **watches safety**: it stops on its own if the garage state is faulted or diverges, if its garage
     information goes stale, or if an active AGV or an enabled bay stops reporting.

  The scheduler only plans. Nothing moves unless the dispatcher is running and sends the commands.

#### Dispatcher Status: is it allowed to move anything?

Status is the dispatcher's on/off switch. Turning it on and off in the NOC calls `api/dispatch/start` / `stop`.

| Status | What happens |
|---|---|
| **Stopped** (and Stopping) | It sends no work. It actively stops every active AGV and moves bays and VECS to a stopped state; Stopping becomes Stopped once they all are. **Every pending and active job is failed**, and it accepts no new jobs. |
| **Starting** | After start: it activates the AGVs, lowers lifts and brings the bays to a ready state. If that takes over 1 min (`kTimeoutStarting`), it goes back to Stopping. |
| **Running** | It plans and dispatches as above. In Auto, starting also queues a clean-garage and a rebalance job. |
| **Paused** | It does nothing: it sends no new commands and keeps its jobs. Resuming goes straight back to Running, without Starting. |

**Do you need to toggle it? Yes.** Central comes up Stopping, then Stopped (`status_` starts at `STOPPING`),
so after every deploy or restart nothing moves until someone starts the dispatcher. Starting is refused
unless the garage is consistent, its reports are fresh and its state isn't faulted. The NOC alert or
central's log ("Cannot start dispatch - …") says which check failed.

It can also **switch itself off** (see "watches safety" above). If the toggle flips to Stopped on its
own, central's log has the reason. Because stopping fails every job, a retrieve or insert in progress
then has to be resent.

#### Dispatcher Mode: who decides what work happens?

Mode decides which jobs the dispatcher accepts and whether it makes work on its own. Each job type
belongs to one mode, and the dispatcher refuses the other mode's jobs (`CanAcceptAutoJob` /
`CanAcceptManualJob`).

| | **Manual**: operator / test mode | **Auto**: production mode |
|---|---|---|
| Jobs it accepts | Move one AGV, move one tray, put a bay into insert / retrieve | Retrieve a vehicle, repark a tray, charge a payload |
| Work it creates by itself | None: it only does what you send | Cleans the garage (hides AGVs under trays) and rebalances bays when started, after inserts and when idle; charges AGVs when idle (if enabled) |
| NOC right-click actions (not Stopped) | AGV → Move; tray → Move (asks for a pose such as `1003@-90`) | Payload → Retrieve; tray → Repark |
| Patron apps and kiosk | Retrieves are refused | Work normally |

- **The point:** in Manual, an operator can move one thing at a time, for setup, recovery or a test,
  without the dispatcher making its own moves. Auto is how the garage runs for patrons. It takes
  their requests and keeps itself tidy.
- **Both modes:** a bay's **Confirm insert payload** / **Confirm retrieve payload** work, and an
  inserted vehicle gets an insert job in either mode (only Auto follows it with a rebalance). The
  insert job only runs if the dispatcher is **Running**, because a Stopped dispatcher fails pending jobs.
- **Mode changes only while Stopped or Stopping** (`SetModeSrvCallback`; the NOC says "Stop the
  dispatcher to change into manual mode"), because the two modes' jobs don't mix. Central starts in
  **Manual** (`mode_` default).
- **Stopped only:** tray position and payload overrides, and enabling or disabling AGVs, trays and nodes.

#### In the NOC: Request Control → Mode → Status

`http://central-comb-5675-pecos:8011/webviewer/` on comb.

1. **Request Control** (top bar, "Control: ---"). Only one NOC user controls a garage at a time
   (`requests/controlManagement.php`). If someone else has it, they're asked to yield. "Control: You"
   means you have it. You need it to **start**, **resume** and **change mode**. Stopping and pausing
   don't need it, so anyone can stop the garage.
2. **Dispatcher Mode** → Manual or Auto, while Status is off.
3. **Dispatcher Status** → on. Watch it go through Starting to Running.
4. **Pause** is optional. It pauses while Running, and clicking it again resumes.

The Status and Mode toggles are disabled unless your NOC login has the `schedulerStatus` /
`schedulerMode` permissions.

**For PR #1018:** use **Manual** for single AGV/tray moves, which exercise the scheduler one job at a
time. Use **Auto** for retrieves, reparks and the insert + rebalance flow, which exercise job expansion
and tray and AGV assignment together. To switch: Status off, change Mode, Status on.

### 4.1 Other ways to send jobs: patron apps and FoxNOC

The NOC sends jobs as an operator. Patrons insert and retrieve through two Flutter apps that call
central's REST API (`src/central_api`, port 5000) directly, not the NOC:

| Client | Repo | Who uses it | Calls |
|---|---|---|---|
| Mobile app (iOS, Android) | `VolleyAutomation/volley-universal-mobile-app` | Patrons, on their phone | `/api/v2/*`: their payloads, confirm insert, confirm retrieve. Login by code over Twilio or SendGrid |
| Kiosk app (iPad in the bay) | `VolleyAutomation/volley-universal-kiosk-app` | Patrons at the bay; an admin sets the garage and bay id | `/api/v2/*`. Sends a retrieval code at insert |
| Bay guidance display | `VolleyAutomation/bay-guidance-app` | Patrons driving in | Display only: a WebSocket from the bay computer (`src/bay/src/bay_guidance.cpp`); ends an insert with "use the kiosk or mobile app" |
| FoxNOC | `VolleyAutomation/foxnoc` | Operators | A Foxglove extension meant to replace the NOC; installed by hand as a `.foxe` file (setup: `garage_troubleshooting_reference.md` section 14) |

- **Server side:** both patron apps talk to `src/central_api/central_api/rest_api.py` (`api/v2`) in this
  repo. A newer `rest_api_v3.py` (`api/v3`, "patron authenticated": tokens checked against signing keys)
  is in progress. That is likely what eng's `central-auth-v3` test build carries (inferred from the name).
- **Pointing an app at a garage:** each app reads its API address and keys from env files kept in
  LastPass (Shared-Software-Engineering > App Dev: `Mobile app - env files`, `Kiosk app - env files`;
  development, staging and production). Building one needs FVM and Flutter 3.44.9, plus Xcode or
  Android Studio. `volley-mock-central-api` is an old mocked backend for app work without a garage.
- **In simulation:** the sim confirms inserts itself. Launch with `auto_confirm_insert:=false` so an
  app or the REST API has to confirm them (`docs/architecture/sim.md`).
- **For this PR:** the apps change nothing in the scheduler's input. They reach the scheduler through
  the same central API and dispatcher as the NOC *(inferred from rest_api.py)*. The NOC (or `curl` on central's API) is enough to test the scheduler; the apps
  matter only for testing the patron flow end to end. Ask Justin or Dan which env file points at the
  Pecos garage before trying one.

## 5. What to test on the AGVs

The PR plans identically to `main` except for commit 4's fixes and the Eccles removal (Eccles is not a
Pecos layout), so test what commit 4 changed plus the most rewritten area:

- [ ] Insert, and retrieve, including a retrieve that has to move blocking trays (tray assignment)
- [ ] Repark after an earlier move in the same plan (commit 4: starts from the tray's planned pose)
- [ ] Charge job, including an AGV already on its charger (commit 4: it was sent to another charger)
- [ ] Several jobs in one request: all complete, reported in request order
- [ ] A job that should fail (for example a disabled bay): reported once, the other jobs still run

Expect quieter scheduler logs: the PR removed the step-by-step INFO and DEBUG narration; ERRORs and
outcome WARNs remain.

## 6. Open questions for Dan or Justin

1. Is the `.env.local` override how PR builds go onto a garage, or is there another route (a Mender
   artifact built from a branch)?
2. Which garage is free, and who needs to know before AGVs move?
3. Is the NOC the usual way to send test jobs on site, and at that URL?
