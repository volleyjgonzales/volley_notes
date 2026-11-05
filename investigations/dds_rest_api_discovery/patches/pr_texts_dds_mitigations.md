# PR texts: the two DDS mitigations (drafts, 2026-11-05)

Status: tickets SW2-1181 (watchdog) and SW2-1182 (settle gate, held) created 2026-11-05 with acli. Watchdog draft PR:
https://github.com/VolleyAutomation/volley/pull/1032 (body: `../patches/pr_body_SW2-1181.md`). SW2-1182 drafts, held: volley #1033 (https://github.com/VolleyAutomation/volley/pull/1033) and swarm-deploy #68
(https://github.com/VolleyAutomation/swarm-deploy/pull/68); bodies in `../patches/pr_body_SW2-1182_volley.md` and `../patches/pr_body_SW2-1182_swarm-deploy.md`. The two settle-gate PRs are a pair: same title, each body links the other.

## Pair A: discovery server settle time

### swarm-deploy PR (branch `jmg/SW2-1182/discovery-server-settle`, commit `ec14784`)

**Title:** `[SW2-1182] feat(app): add a discovery server settle time for the ros containers`

**Body:**

Paired with volley PR #<n> (`feat(docker): wait for the discovery server to settle before starting the ros
processes`). This half only passes the number; nothing changes until the volley images with the entrypoint change are
deployed.

**Why.** On a full start of the `app` stack (`release install`, a node boot, or `remove` plus `deploy`) the discovery
server comes up in the same second as every participant, on a freshly created overlay. On the Pecos combined garage,
8 of 23 such starts left the REST API's DDS participant without bay 7's state-machine participant for good: `confirm_insert`
returned 500 (`timeout waiting for service /bay/b7/confirm_insert ready`) until something made a new participant join.
A redeploy with the server already running never did this (0 of 6). Investigation notes: `<link to the findings doc>`.

**What.** `DISCOVERY_SERVER_SETTLE_SEC=10` in `swarm/.env`, passed to `central`, `control` and every bay. The volley
entrypoint already probes the server before starting the ROS processes; with the variable set it waits that long after
the first answer and probes again, so participants register with a server that has been answering for at least that
long, as they do on a plain redeploy. `0` keeps today's behaviour.

**Cost.** Every ROS container's start takes `DISCOVERY_SERVER_SETTLE_SEC` longer.

**Testing.** <to fill in: N full starts on comb from a copy of the stack with the variable, 0 STUCK, against 1 in 3 without
it on the same day; or "untested" if it ships before>.

### volley PR (branch `jmg/SW2-1182/discovery-server-settle` off `main`, commit `296cfb40`; test build was `651eb3d7`)

**Title:** `[SW2-1182] feat(docker): wait for the discovery server to settle before starting the ros processes`

**Body:**

Paired with swarm-deploy PR #<n> (`feat(app): add a discovery server settle time for the ros containers`), which sets
`DISCOVERY_SERVER_SETTLE_SEC` for the ROS containers. Without it the variable is unset and this change does nothing.

**Why.** Same paragraph as the swarm-deploy PR.

**What.** `docker/resources/entrypoint.sh`: after `discovery_probe` succeeds, if `DISCOVERY_SERVER_SETTLE_SEC` is set and
positive, sleep that long and run the probe again. Nine lines, shellcheck clean. Each probe is a throwaway participant,
as today.

**Testing.** Same as the swarm-deploy PR.

## B: the REST API's bay client watchdog

### volley PR (branch `jmg/rest-api-dds-watchdog` off `main`, one commit `82df8676`; test build was `aeb59906`)

**Title:** `[SW2-1181] feat(central_api): heal or restart the rest api when a live bay's confirm services stay unmatched`

**Body:**

**Why.** See pair A's "why": a stuck REST API participant never recovers by itself (13 min and 2 h observed), while any
new participant joining makes the discovery server send again and the stuck one catches up within 2 s (5 of 5 on comb,
once with a node that had no clients at all). Independent of pair A: that lowers the chance of the stuck state, this
bounds how long it lasts.

**What.** `central_api/bay_client_watchdog.py`, a 10 s timer on the REST API node:
- a bay counts as alive when the latest `/central/continuous_garage_info` arrived within 10 s and its report is at most
  10 s stale, so layout bays that aren't deployed never trip it
- once a live bay's `confirm_insert` / `confirm_retrieve` clients have been unmatched for 60 s, it pokes discovery: a node
  in a second rclpy context (a new DDS participant), held 5 s on its own thread, then destroyed
- still unmatched 30 s later, it ends the process (`os._exit(3)`, so the whole process, not just the spin thread) and
  launch respawns `rest_api` (`respawn=True`, 5 s delay, in `launcher/central_nodes.py`); a fresh participant matches at
  once
- a match clears both timers
- one poke runs at a time, and the poke logs whether its participant came up and went down
- a restart budget of 3 per hour, kept in `/tmp/rest_api_watchdog_restarts` because launch respawns on any exit code;
  over budget it logs and keeps poking instead
It prints a line per poke, participant up/down, restart or refused restart, and nothing otherwise.

**Liveness caveat.** "Alive" is garage info received within 10 s whose bay report is at most 10 s stale, so a bay's effective
age can reach 20 s plus clock skew; a bay that restarts briefly may still count as alive. The 60 s streak absorbs that.

**Cost.** A restart drops in-flight requests; the poke drops nothing. `respawn=True` also restarts the REST API after
any other crash, with a 5 s delay.

**Testing.** 6 unit tests (fake clock: poke at 60 s then restart at 90 s, a match resets, an undeployed bay never trips, one
poke at a time, the restart budget; and against the installed rclpy, the poke's second context coming and going while
the main context spins); `central_api` 448 passed, `launcher` 12. On
comb (build `aeb5990`, 2026-11-05 04:16-06:08Z): 27 full starts, all healthy, no false trip. No start stuck in that window
(the failure had become rare: 1 in ~40 full starts since 02:54Z, against 7 in 10 before), so the heal itself was not
observed in the field. Its mechanism was: in diag15 (03:49Z) a stuck REST API was healed within 2 s by one node with no
clients joining, which is what the poke does. The hardened version (one poke at a time, restart budget) ran 2 more full
starts on comb (14:32-14:40Z, test build `480b803`): healthy, no watchdog line, no restart file, one PID.
