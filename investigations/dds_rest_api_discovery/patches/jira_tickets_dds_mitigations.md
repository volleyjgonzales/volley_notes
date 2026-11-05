# Jira work items for the two DDS mitigations (created 2026-11-05 with acli: SW2-1181, SW2-1182)

Two tickets, both Tasks. The parent is your call: they're a garage reliability issue, not part of epic SW2-482. Once
created, the branches get renamed to `jmg/<key>/…` and the PR titles get the key.

## Ticket A, SW2-1181: the REST API heals or restarts itself when a bay's confirm services stay unmatched

**Summary:** REST API: heal or restart when a live bay's confirm services stay unmatched after a full start

**Description:**

After a full start of the app stack (node boot, release install, or remove plus deploy) the patron REST API's DDS
participant sometimes never discovers bay 7's `confirm_insert` / `confirm_retrieve` services, and every confirm-insert
returns 500 (`timeout waiting for service /bay/b7/confirm_insert ready`) for hours. Seen on central-comb 8 times in 23
full starts on 2026-11-03/04; never after a plain redeploy. Only the REST API's process is affected; a fresh participant
sees the bay within a second, and a new participant joining made the stuck one catch up within seconds, 5 of 5 times.
Investigation write-up: <link to the doc / notes>.

**Scope**
- A watchdog on the REST API node (`central_api/bay_client_watchdog.py`): once a bay that central reports alive has
  had an unmatched confirm client for 60 s, hold a temporary participant (a node in a second rclpy context) for 5 s;
  still unmatched 30 s later, end the process; launch respawns `rest_api` (`respawn=True`, 5 s delay).
- One poke at a time; the poke logs whether its participant came up; a budget of 3 restarts per hour, kept in a file.
- Unit tests, including the poke's second context beside a spinning main context.

**Definition of Done**
- [ ] PR merged on `main`; `central_api` and `launcher` suites green; mypy, pylint, black clean
- [ ] On a garage: healthy full starts show no watchdog line and one REST API PID
- [ ] On a garage: one stuck start heals after the poke, or restarts within 90 s, with the log lines showing which
- [ ] The restart budget's file and the respawn behaviour are described in the PR

**Out of scope**
- The root cause in Fast DDS 3.6.2's discovery-server client stream (no public release carries the candidate fix yet)
- The start-order mitigation (ticket B)

## Ticket B, SW2-1182: discovery server settle time before the ROS processes start (held)

**Summary:** Wait for the discovery server to settle before starting the ROS processes on a full stack start

**Description:**

Every stuck start above was a full start in which the discovery server came up in the same second as every participant
on a freshly created overlay; 0 of 6 plain redeploys with the server already running stuck. Swarm orders nothing.
Hypothesis: letting the server answer for 10 s before a container's participants register removes the trigger.

**Scope**
- swarm-deploy: `DISCOVERY_SERVER_SETTLE_SEC=10`, passed to central, control and the bays (branch
  `jmg/discovery-server-settle`, commit `ec14784`).
- volley: the entrypoint probes the server, waits that long, probes again; 0 keeps today's behaviour
  (branch `jmg/discovery-server-settle`, commit `296cfb40`).
- Two paired PRs with the same title.

**Status:** held on 2026-11-05. Untested on comb: the failure became too rare (1 in ~40 starts) to measure a
before-and-after. Reopen when the failure reproduces; test with the extra probe's own join separated from the delay.

**Definition of Done**
- [ ] A measured difference on a garage: N full starts with the gate against N without, same day, same build
- [ ] Both PRs merged, or the branches dropped with the result recorded

**Out of scope**
- A server healthcheck gate, a separate server stack, `endpoint_mode: dnsrr` (alternatives noted in Codex review 2)
