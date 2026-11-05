# central-comb results, 2026-11-04

Raw results and scripts from the DDS testing on `central-comb-5675-pecos`, copied from `/home/ops` at the end of the
day (checksums verified against comb before it was cleaned up). Interpretation: `../../findings.md`
(1.11-1.15) and `../../summary.md`.

## logs/

| File | What |
|---|---|
| `dds_attempts.log` | One result line per attempt (label, build, result, late recreate lines, UDP drops, the REST API's socket buffers and drops), plus the hands-off, probe and recovery lines of STUCK runs. Baseline 1-3, then E2 attempt 1 |
| `dds_baseline.out` | Live output of the baseline loop (status every 10 s): attempts 2 and 3 |
| `dds_e2_1.out` | Live output of E2 attempt 1 (4 MiB buffers), including the hands-off phase and the probe |
| `dds_restore.out` | The final redeploy from `/data/swarm` (22:27:42Z) |
| `swarmctl_logs_2026-11-04_1606-stuck.txt` | `swarmctl logs -e logstore-agent -e noc` captured during the 16:06Z stuck start (the first failure with the patch deployed) |

## scripts/

| File | What | Where it runs |
|---|---|---|
| `dds_attempt.sh` | One full-restart attempt: remove and redeploy `app-comb`, status every 10 s, STUCK detection, 10 min hands-off, one probe. `SWARM_ROOT=<dir>` deploys from a copy of `/data/swarm` | On comb, as `ops`, in `~` (from your interactive shell, or a `systemd-run --user` unit with `HOSTNAME` set, plan 4.3) |
| `probe_clients.py` | Fresh rclpy process: are bay 7's services and `/central/start` ready, and how fast | In `control` or `central`, via `/opt/volley/entrypoint.sh python3` |
| `probe_graph.py` | Who serves bay 7's services (request readers, reply writers, GIDs) | Same |
| `probe_rest_api_endpoints.py` | The REST API's endpoints grouped by participant GID prefix | Same |
| `probe_vis.py` | Whether the `/vis/*` marker topics carry data, and their frame and QoS | Same |
| `udp_drops_by_process.sh` | UDP sockets with drops, and the owning process (`/proc/net/udp` + `/proc/<pid>/fd`) | In a container: `docker exec -i "$C" sh < udp_drops_by_process.sh` |
| `dds_attempt_diag.sh` | The attempt script for the **diagnostic build** (branch `jmg/test/dds-rest-api-diagnostics`): judges the REST API from its `[dds-diag]` heartbeat (only deployed bays), records the stuck services' own graph counts, saves Fast DDS warnings per run (`~/dds_warnings_<label>_<start>.txt`), logs exact recovery times, the REST API's PIDs and where its last check got to (`started`/`finished`). Classifies `BAY_NOT_RUNNING` / `NO_HEARTBEAT` / `NO_DIAG` separately; the probe is a single rclpy process. Written and reviewed 2026-11-04 (Codex); first run on comb 2026-11-05 (diag1, ok). 2026-11-05: `save_warnings` strips ANSI escapes before matching (the coloured Fast DDS lines never matched before; findings 1.18). The `last_check` and PID fields need the second diagnostics change | On comb, as `ops`, like `dds_attempt.sh` |
| `registry_versions.py` | A node registry's volley versions as a `rich` table, newest first: build time, age, `GITSHA`, a column per image | On the laptop: `uv run scripts/registry_versions.py central-comb:4000` |
| `fastdds-profile.E2-4MiB-buffers.xml` | The E2 variant of swarm-deploy's `fastdds-profile.xml` (adds 4 MiB `sendBufferSize` / `receiveBufferSize` to `udp_overlay`) | Copy into `~/swarm-exp/stacks/app/config/` |

**To reinstall on comb** (from this folder, on your laptop):
```bash
scp scripts/dds_attempt.sh scripts/probe_clients.py ops@central-comb-5675-pecos:
```
```bash
ssh ops@central-comb-5675-pecos 'chmod +x ~/dds_attempt.sh'
```
