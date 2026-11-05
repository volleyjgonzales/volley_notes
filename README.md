# volley_notes

Working notes for the Volley workspace, outside the code repositories. Nothing here ships; the code lives in
`volley`, `swarm-deploy` and `ros2-docker`.

| Folder | What's in it |
|---|---|
| `guides/` | How-tos: `claude_workflow/` (the Claude Code workflow, recon scripts, prompt library), `mqtt_broker/` (the broker setup guide and its diagrams), `host_setup/` (laptop kernel fixes) |
| `subsystems/` | One note per volley package (`01-common` … `24-central`), the Boost Graph primer, the swarm-deploy reference under `deploy/`, figures under `figures/` |
| `research/` | Background reading: the MG-TAPF paper walkthrough, the action dependency graph tutorial, the bottleneck assignment explainer |
| `specs/` | `agv_requirements/`: the illustrated AGV requirements and the site generator |
| `presentations/` | `scheduler_package/`: the scheduler deck and its generated site (large) |
| `garage/` | Operating the test garages: `deploy_and_test.md` (deploying a build, the NOC, the dispatcher), `troubleshooting_reference.md` (every command used on a garage and how to read it), `scripts/` (attempt, loop, probe and registry scripts, one current copy each) |
| `investigations/` | Issues worked across tickets. `dds_rest_api_discovery/`: the REST API stuck after a full start (2026-11-03 to 05): `README.md` is the entry point with the reading order, then `summary.md`, `findings.md`, `plan.md`, `handoff.md`, `reviews/` (Codex), `patches/` (PR and ticket texts), `results/<date>/` (raw logs, scripts as run, reference captures) |
| `tickets/` | Per-ticket and per-PR notes: `SW2-482_scheduler_core_refactor/` (the epic: `SW2-482_notes.md` running log, `PROMPT.md`, `review_rules.md`, stage folders `SW2-1126_scenario_files/` and `SW2-1135_scheduler_renames/`), `SW2-876_agvhito_state_machine/`, `SW2-905_insert_blocked_by_agv/`, `rclcppx-component-review.md` |
| `tools/` | Standalone scripts: the AGV state machine, layout and scenario plotters |
| `src/volley_notes/` | The `volley-notes` package behind `pyproject.toml` (`uv run volley-notes`) |

Conventions: a ticket folder is `SW2-<n>_<slug>`; raw results go under the investigation or ticket that produced them,
dated; large generated output (captures, sites) stays out of git.
