# central-comb results, 2026-11-05

Raw results from the DDS testing on `central-comb-5675-pecos` with the **diagnostic build** `dds-diag-29712d9`
(branch `jmg/test/dds-rest-api-diagnostics`). Interpretation: `../../findings.md` (1.17-1.18) and
`../../summary.md`. Scripts and how to install them: `../2026-11-04/README.md`.

## logs/

| File | What |
|---|---|
| `dds_attempts.log` | One result line per attempt (`~/dds_attempts.log` on comb, fresh file: comb was cleaned up on 11-04) |
| `dds_diag_1.out` | Live output of attempt `diag1` (unit `dds-diag-1`, 02:01:24Z): full start, result ok |
| `dds_warnings_diag1_2026-11-05T02:01:52Z.txt` | The script's warnings file for diag1: **empty because of the ANSI-escape bug** (findings 1.18); the real warnings are in the next file |
| `dds_diag_2.out` | Live output of attempt `diag2` (unit `dds-diag-2`, 02:09:57Z): full start, **STUCK**, 10 min hands-off, probe, recovered |
| `dds_warnings_diag2_2026-11-05T02:10:24Z.txt` | diag2's Fast DDS warnings (fixed script): the two of every start, nothing else |
| `central_diag_diag2_recovery.txt` | The REST API's `change` lines of diag2 (0/0 from the first check, 1/1 at 02:23:33.997Z with bay 7's GIDs), heartbeats after the recovery, capture-tool checks |
| `central_diag_diag1_head.txt` | The first 60 `[dds-diag]` and Fast DDS warning lines of central after the diag1 deploy, colour codes stripped |

| `dds_diag_3.out`, `dds_warnings_diag3_*.txt`, `dds_central_diag3_*.log`, `dds_discovery_diag3_*.log` | diag3 (build `4b00571`, v3 script, 02:54:47Z): full start, ok; central's and the discovery server's full logs |

| `dds_diag_<n>.out`, `dds_loop_<n>.out`, `dds_warnings_diag<n>_*.txt`, `dds_central_diag<n>_*.log`, `dds_discovery_diag<n>_*.log` | Every attempt diag1-48 (diag46 was interrupted by the loop stop with the stack deployed): live output, loop output, Fast DDS warnings, central's and the server's full logs. `dds_attempts.log` has one result line per attempt |

## captures/

`diag3_central.pcap0` (central's network namespace, `-i any udp`, from 2 s after the deploy) and `diag3_host.pcap0` (the
host's `eth0`, VXLAN UDP 4789, from before the removal): the **healthy reference** capture, 37 MB in all. Wireshark decodes
RTPS, and VXLAN on the host file. Large binaries: keep out of git if this folder is committed.

## scripts/

| File | What |
|---|---|
| `dds_loop.sh`, `dds_loop_v2.sh` | Back-to-back attempts until the first non-ok result; v2 also stops on a second REST API PID or a watchdog line in the saved central log |
| `dds_attempt_diag.sh` | v3 (2026-11-05 03:00Z, on comb; `CAPTURE=0` toggle and the carriage-return fix added later): `save_warnings` strips ANSI escapes; on STUCK the probes run in `PROBE_ORDER` (default `unrelated,clients`), each followed by a 2 min watch, stopping at the first recovery; a host capture (`eth0`, VXLAN UDP 4789, from before the removal) and a capture inside central's network namespace (sidecar `--net container:<central>`, `-i any udp`, from the moment the container exists), both `nicolaka/netshoot:v0.16` tcpdump capped at 4 x 500 MB in `~/captures`; a finish trap stops them and saves central's and the discovery server's full logs (`~/dds_central_<label>_<start>.log`, `~/dds_discovery_…`) |
| `probe_unrelated.py` | One rclpy node with **no clients**, held 20 s, prints the node count and bay 7's nodes as seen by that fresh participant |
| `probe_clients.py` | Unchanged: one rclpy node with the four bay 7 / central clients |

**Starting an attempt remotely** (on comb, as `ops`; `HOSTNAME` must be exported for `swarmctl`):
```bash
systemd-run --user --unit=dds-diag-<n> --collect -p WorkingDirectory=/home/ops -E HOSTNAME=$(hostname) /bin/bash -c "/home/ops/dds_attempt_diag.sh diag<n> > /home/ops/dds_diag_<n>.out 2>&1"
```
