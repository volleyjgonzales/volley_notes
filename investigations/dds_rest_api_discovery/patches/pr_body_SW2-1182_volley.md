**Held, untested on a garage.** Paired with swarm-deploy PR https://github.com/VolleyAutomation/swarm-deploy/pull/68 (same title), which sets `DISCOVERY_SERVER_SETTLE_SEC` for the ROS containers; without it this change does nothing. Kept as a draft until the failure it targets reproduces and a before-and-after run can be measured (SW2-1182).

## What
`docker/resources/entrypoint.sh`: after `discovery_probe` succeeds, if `DISCOVERY_SERVER_SETTLE_SEC` is set and positive, sleep that long and run the probe again, so the container's ROS processes start only once the discovery server has been answering for at least that long. Unset or 0 keeps today's behaviour. Each probe is a throwaway participant, as today.

## Why
Every stuck start in the REST API discovery investigation (SW2-1181, #1032) was a full start of the app stack in which the discovery server came up in the same second as every participant on a freshly created overlay: 8 of 23 full starts on central-comb on 2026-11-03/04. A redeploy with the server already running never stuck (0 of 6). Swarm orders nothing between services. Letting the server settle before participants register is a hypothesis that removes that trigger.

## Testing
shellcheck clean. Not run on a garage: the images were built and a stack copy with the variable was staged on comb, but the failure had become too rare (1 in about 40 full starts) to measure a difference, and the test was stopped. Codex's review notes that the second probe is itself a joining participant, so a test must separate the delay from the extra join.

Jira: https://volleyautomation.atlassian.net/browse/SW2-1182
