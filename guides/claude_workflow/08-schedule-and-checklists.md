# 08 · Schedule, checklists, open questions

## 8.1 Suggested 5-day schedule

| Day | Plan |
|---|---|
| 1 | Host setup (02), container up (03), SETUP-1…4 in `volley_guide.py` |
| 2 | Depth 0–1 packages: build system, core utilities, `common`, `structures`, interfaces (~10 small packages, ~20 min each) |
| 3 | `common_ros`, planning libraries, `motion_planner` |
| 4 | `scheduler`, `central` (parts), `agvhito` |
| 5 | `bay`, `lift`, `vrc`, `vecs`, `vis`, `sim`, then the deferred Python packages |
| 6 | SLICE (retrieval), then TICKET |

`volley_guide.py list` shows the exact order and how many parts each package has.



## 8.2 Day-1 checklist

- [ ] **[HOST]** Docker without sudo, buildx present
- [ ] **[HOST]** `sudo tailscale up`; `tailscale status` OK
- [ ] **[HOST]** AWS SSO + ECR login work (`docker manifest inspect` on the base image)
- [ ] **[HOST]** `xhost` installed; `ssh -T git@github.com` OK
- [ ] Container up via VS Code *Reopen in Container* **or** `devcontainer up` (03 §3.3 / §3.4)
- [ ] **[CONTAINER]** `~/.zshrc` with the direnv hook; `echo $ROS_DISTRO` → `lyrical` (03 §3.5)
- [ ] **[CONTAINER]** Sanity checks in 03 §3.6 pass; `poe` lists tasks
- [ ] **[CONTAINER]** Unique `ROS_DOMAIN_ID` via `poe domain-id` (03 §3.8)
- [ ] **[CONTAINER]** `poe build`, `direnv reload`, `poe test-pkg <pkg>` pass
- [ ] **[CONTAINER]** `rviz2` opens on your screen; `poe docs` opens in the host browser
- [ ] Read `.claude/CLAUDE.md` + glossary yourself
- [ ] **[HOST]** `volley-recon.sh` → `artifacts/recon.md`; Phase 1A/1B decided (05 §5.8)
- [ ] Sim launches; `ros2 node list` captured and compared to 01 §1.3

## 8.3 Open questions and files still to read

**Files that would resolve the remaining (verify) items:**
- `.devcontainer/scripts/post-attach.sh` and `utils.sh`: what runs on every attach, and where the `DEVCONTAINER_*` names come from.
- `.envrc` / `.envrc.local`: exact sourcing logic.
- `scripts/set-domain-id`, `scripts/set-discovery-server`: confirm they write `.envrc.local`.
- `prek.toml`: what `poe check` enforces.
- `docker/` (`docker-bake.hcl`, `Dockerfile`): stages, base image, what the image installs.
- `src/`: the 37 packages and how they relate (06 Phases 2–4).

**Questions for the team:**
1. `.claude/CLAUDE.md` is only 119 words and the glossary 88. Is there a fuller onboarding or architecture doc somewhere (wiki, Notion) that isn't in the repo?
2. Are `docs/deprecated/central.md` and `scheduler.md` still roughly accurate, or actively misleading?
3. `architecture/agv.md` and `vda5050.md` predate recent `agvhito` changes. Are they still current?
4. Is there a `ROS_DOMAIN_ID` allocation list, or should I use the discovery server?
5. ECR auth: daily `docker login`, or the ECR credential helper? Which AWS profile name?
6. Could Graphviz (and anything else people keep `apt install`ing) be added to the dev image?
7. What writes to `artifacts/`?
8. Do I ever need the NVIDIA GPU in the container (sim, perception)?
9. Confirm: `vecs` looks like **EV charging** (`vecs_evse_control.cpp`), and "hito" looks like the AGV model or vendor (`hito_agv.dae`).
10. Is `controller_webview` (PHP) still the production NOC or being replaced?
11. What is the canonical "hello world" sim command and layout?
12. What is a good first ticket?

