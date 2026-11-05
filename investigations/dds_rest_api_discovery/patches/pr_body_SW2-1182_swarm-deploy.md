**Held, untested on a garage.** Paired with volley PR https://github.com/VolleyAutomation/volley/pull/1033 (same title), which makes the entrypoint honour the variable; this half only passes the number, and nothing changes until volley images with the entrypoint change are deployed. Kept as a draft until the failure it targets reproduces and a before-and-after run can be measured (SW2-1182).

## What

`DISCOVERY_SERVER_SETTLE_SEC=10` in `swarm/.env`, passed to `central`, `control` and every bay, and a short README section under the Fast DDS profile. With the matching volley entrypoint, each ROS container waits until the discovery server has been answering for that long before starting its processes; `0` keeps today's behaviour.

## Why

Every stuck start in the REST API discovery investigation (volley SW2-1181, #1032) was a full start of the `app` stack in which the discovery server came up in the same second as every participant on a freshly created overlay: 8 of 23 full starts on central-comb on 2026-11-03/04. A redeploy with the server already running never stuck (0 of 6). Swarm orders nothing between services and every release install is a remove-all then deploy-all. Letting the server settle before participants register is a hypothesis that removes that trigger. Cost: every ROS container's start takes 10 s longer.

Jira: https://volleyautomation.atlassian.net/browse/SW2-1182
