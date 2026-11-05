## What
A watchdog on the REST API node (`central_api/bay_client_watchdog.py`) that heals, and failing that restarts, the process when a bay that central reports alive has had an unmatched `confirm_insert` / `confirm_retrieve` client for 60 s:
- a bay counts as alive when the latest `/central/continuous_garage_info` arrived within 10 s and its report is at most 10 s stale, so layout bays that aren't deployed never trip it
- at 60 s unmatched it pokes discovery: a node in a second rclpy context (a new DDS participant), held 5 s on its own thread, one poke at a time, logging whether the participant came up
- still unmatched 30 s after the poke, it ends the whole process (`os._exit(3)`) and launch respawns `rest_api` (`respawn=True`, 5 s delay, in `launcher/central_nodes.py`)
- a budget of 3 restarts per hour, kept in `/tmp/rest_api_watchdog_restarts` because launch respawns on any exit; over budget it logs and keeps poking
- a match clears both timers; it prints one line per poke, participant up/down, restart or refused restart, and nothing otherwise

`respawn=True` also restarts the REST API after any other crash, with a 5 s delay. A restart drops in-flight requests; the poke drops nothing.

## Why
After a full start of the app stack (node boot, release install, or remove plus deploy) the REST API's DDS participant sometimes never discovers bay 7's confirm services, and every confirm-insert returns 500 (`timeout waiting for service /bay/b7/confirm_insert ready`) for hours: 8 of 23 full starts on central-comb on 2026-11-03/04, never after a plain redeploy. Only the REST API's process is affected; a fresh participant sees the bay within a second, and a new participant joining made the stuck one catch up within 2 s, 5 of 5 times, once with a node that had no clients at all. The root cause sits in Fast DDS 3.6.2's discovery-server client stream (no release carries the candidate upstream fix yet); this bounds the outage to about a minute whatever the cause. SW2-1181.

## Testing
- 6 unit tests on a fake clock (poke at 60 s then restart at 90 s, a match resets, an undeployed bay never trips, one poke at a time, the restart budget) and against the installed rclpy (the poke's second context coming and going while the main context spins); `central_api` 448 passed, `launcher` 12; mypy, pylint, black clean.
- On central-comb, as a test build on top of the investigation's diagnostics: 29 full starts with the watchdog, all healthy, no false trip, one REST API PID each.
- Restart path on comb: `kill -TERM` of the REST API process inside central; launch logged `process has finished cleanly` and `process started with pid [366]` about 10 s later; the new process matched bay 7 at its first check; the service stayed 1/1.
- Not observed: a heal of a real stuck start. None occurred in the 29 starts after the watchdog was deployed (the failure became rare that night: 1 in about 40 full starts). The poke's mechanism was observed on a stuck start the same night (a node with no clients joining healed it in 2 s). The watchdog's own log lines will show a heal or a restart in production.
