# Prompt: continue the DDS investigation (stuck REST API after a full start)

This folder is the investigation; this file was the session prompt that resumed it on 2026-11-05 and doubles as its
reading order. Paths below are relative to this folder unless they start with `../../`.

You're picking up a debugging investigation that's been running for two days. Work with me (Jon) on the garage node
`central-comb-5675-pecos`. The goal is the **root cause**, not another workaround: why, after a full start of the app
stack, the REST API in `central` sometimes never sees bay 7's `confirm_insert` / `confirm_retrieve` services, so
confirm-insert returns 500 `timeout waiting for service /bay/b7/confirm_insert ready`.

## Read first, in this order

All in `/home/jon-gonzales/repos/volley_notes/investigations/dds_rest_api_discovery/`:

1. `summary.md`: the one-page picture (topology, every start observed, what's established, open
   hypotheses, constraints, repos and key files).
2. `handoff.md`, section "For tomorrow": the exact state and how to resume.
3. `plan.md`: sections 1, 3 (hypotheses H1-H7), 5 (experiments, especially E8 and "The investigation
   branch"), 6 and 9. Skip the long script in 4.3; it's the old one.
4. `reviews/codex_dds_review_1.md`: an independent review; its corrections are already folded into the plan.
5. `results/2026-11-04/README.md`: the raw logs and every script, and where each runs.

Use these as references when needed, not end to end:
- `../../garage/troubleshooting_reference.md`: every command used on the garage, and how to read its output
- `../../garage/deploy_and_test.md`: section 3 on deploying, 3.7 on the local image build and registry
- `findings.md`: 1.9-1.16, the first findings

The running log is `../../SW2-482_notes.md`, section "Review log". The last item is 354, so continue at 355.

## Where it stands (2026-11-04 evening)

- **The symptom:** after a full start (stack removed and deployed, or a node boot), STUCK in 6 of 8 attempts. A plain
  `swarmctl deploy app` on a running stack has always been fine. Only the REST API's process is stuck: fresh
  participants see bay 7 within about 1.2 s, and the graph is clean. Waiting 12+ minutes doesn't help. A new
  participant joining was followed by recovery 3 of 3 times. That's an association: the probe did several things at
  once.
- **Ruled out:**
  - socket overflow: E2, 4 MiB buffers, 0 drops, still stuck
  - a discovery-server restart alone: E1b
  - recreating the REST API's clients: the dropped commit `e1d24a7c`
  - the "plain client" idea: since Fast DDS 3.5.0, CLIENT behaves like SUPER_CLIENT
- **Leading hypothesis (H7):** a discovery race at full start. Bay 7's endpoint announcements reach the REST API's
  participant but fail to be added as proxies, and they're never repaired. The "Received message from UNKNOWN
  RTPSParticipant, removing" path in `EDPSimpleListeners` fires whenever a proxy add fails. Fast DDS hides it
  because its default log level is Error.
- **Stack:** ROS 2 Lyrical, rmw_fastrtps 9.4.9, Fast DDS 3.6.2, rclpy, a `fast-discovery-server`, Docker swarm overlay
  (`overlay0`). The bays run on a different machine.

## What's ready to use

- **Investigation branch** `jmg/test/dds-rest-api-diagnostics` in `/home/jon-gonzales/volley`, head `29712d97`, pushed,
  no PR. It's two commits on PR #1018's feature branch (`jmg/SW2-1135/scheduler-renames-and-cleanups`, `07eb74dd`):
  - `src/central_api/central_api/dds_diagnostics.py`: Fast DDS warnings switched on through `Log::SetVerbosity` via
    ctypes, with a read-back.
  - `BayDiscoveryMonitor`, which prints `[dds-diag]` lines every second:
    - `change`: readiness, the REST API's own request-reader and reply-writer counts and GIDs
    - `check-start` and `heartbeat ... took_ms= not_ready=`, plus `pid=` on every line
  - Wired into `rest_api.py`, behind `REST_API_DDS_DIAG=1` / `FASTDDS_WARNINGS=1`, which `launcher/central_nodes.py` sets.
- **Images:** `dds-diag-29712d9` is in comb's local registry `central-comb:4000`, with all five images. They were built
  from the laptop with `tools/local-runtime-deploy`, not CI. **Not deployed yet.**
- **Attempt script:** `results/2026-11-04/scripts/dds_attempt_diag.sh`, run with `probe_clients.py`:
  - one full restart, judged from the heartbeat
  - results: STUCK / ok / BAY_NOT_RUNNING / NO_HEARTBEAT / NO_DIAG
  - Fast DDS warnings saved for each run
  - on STUCK: 10 minutes hands-off, then a single-process probe
  - It hasn't been run on comb yet. It was reviewed twice by Codex and tested offline with fake logs and a fake
    `docker`.
- **`registry_versions.py`** (`uv run`): a table of what's in a node's registry.

## Suggested next steps (propose, then wait for my go on anything that touches comb)

1. **Check comb's state with me.** A teammate tested an unrelated branch on it overnight. Read-only:
   `cat /data/swarm/.env.local` and `docker stack ls`.
2. **Deploy the diagnostic build.**
   - In `/data/swarm/.env.local`, uncomment `VOLLEY_REGISTRY` and set `VOLLEY_VERSION=dds-diag-29712d9`, then
     `swarmctl deploy app`.
   - Check `GITSHA` is `29712d9`, and that `[dds-diag] ... fastdds verbosity=1` appears in central's logs.
3. **Reinstall the scripts and run attempts.** I run them from my interactive shell on comb, or you start them as a
   `systemd-run --user` unit with `-E HOSTNAME=$(hostname)`.
4. **Read the results:**
   - `rq_readers=0` / `rr_writers=0` while stuck: the REST API never learned bay 7's endpoints.
   - `1`/`1` but `ready=0`: the endpoints are known but not matched locally.
   - Fast DDS warnings near the start: a "Maximum number of … proxies" warning, or the UNKNOWN-participant line, which
     tells you which branch of the proxy add failed.
   - GID changes, PID changes, or a `check-start` with no heartbeat after it.
5. **Then, depending on what that shows:**
   - the unrelated-probe test: a participant with no bay clients
   - a packet capture of a stuck start (plan section 6; check `sudo -l` first)
   - a lab reproduction with Docker Compose
   - E4 (UDP only), E5 (another Fast DDS version), E7 (the discovery server with the same profile)
   - finally, a write-up for Dan. The fix will likely be in swarm-deploy (start order or profile) or the Fast DDS
     version.

## Cautions when reading results

- The three graph queries in one sample aren't atomic. One `ready=0` with `1/1` can be a transition; only a pattern
  that persists means a failed match.
- A `check-start` with no heartbeat after it means the check didn't finish. It doesn't prove which call blocked.
- Keep "associated with" separate from "caused". Change one thing per experiment (plan section 5).
- Bay services in the layout that aren't deployed are never ready. Judge only the deployed bays (`BAY_IDS_OVERRIDE="7"`).

## Rules for this work

- `CLAUDE.local.md` in the repo applies: use `volley-in-container` for builds and tests; commit only with my explicit
  approval; never push, rebase, reset or force; stage by name.
- Don't change the feature branch. New diagnostics go on the investigation branch as new commits, after my approval.
  Then rebuild with `tools/local-runtime-deploy dds-diag-<sha> central-comb:4000` (`../../garage/deploy_and_test.md` 3.7), and
  delete your old tags in the shared registry (3.7 step 5; it's shared, so delete only your own `dds-diag-*` tags).
- **Comb is a shared garage.** Anything that changes it needs my go first: deploys, `.env.local` edits, restarts,
  probes, copying files to it. Read-only inspection over ssh (`ops@central-comb-5675-pecos`) is fine.
- **comb quirks:**
  - `ops` has restricted sudo
  - `/data/swarm` is root's, so `sed -i` fails: write to `/tmp` and `cat >` back into the file
  - `nohup` over a non-interactive ssh gets killed: use `systemd-run --user` with `HOSTNAME` set
  - during a hands-off window, run no ros2 commands, probes or Foxglove reconnects
- **When testing is done,** restore `.env.local`: comment `VOLLEY_REGISTRY` out again and set `VOLLEY_VERSION=pr-1018`
  (or whatever I say), then deploy.
- **Notes:**
  - Keep the notes log and every affected doc in sync each turn: summary, plan, findings, reference, handoff, results
    README.
  - Save raw results under a new `comb_results_<date>/`.
  - The notes folder lives outside the repo: never copy it in or commit it.
- No temp files in the workspace; use your scratchpad, or `/tmp` in the container.
- Style: brief replies, soft tone. In code: minimal comments, typed modern Python 3, functional style where it reads
  better, readability over abstraction, `is_` booleans.
