# Pause: central-comb handed over for unrelated testing (2026-11-04, ~22:30Z), DDS testing resumes 2026-11-05

The garage goes to a teammate for a different, unrelated branch tonight. The DDS investigation resumes tomorrow.
Background: `summary.md`. Detail: `findings.md` (1.9-1.15),
`plan.md`, `../../garage/troubleshooting_reference.md`.

## For the teammate testing her branch on comb

- **Comb right now:** `app-comb` runs PR #1018's build (`VOLLEY_VERSION=pr-1018`, images from ECR), redeployed at
  22:27:42Z from the normal `/data/swarm`, original Fast DDS profile. The dispatcher is stopped.
- **Switching to her branch:** set `VOLLEY_VERSION=pr-<n>` (or her tag) in `/data/swarm/.env.local`, then
  `swarmctl deploy app`. **`sed -i` on that file fails** for `ops` ("couldn't open temporary file … Permission
  denied", the folder is root's); edit it with an editor that writes in place, or with
  `sed '…' /data/swarm/.env.local > /tmp/env.new && cat /tmp/env.new > /data/swarm/.env.local`.
  `VOLLEY_REGISTRY` is commented out (ECR). Uncomment it only for images pushed to the node's local registry.
- **A known, unrelated bug she may hit** (it's in the shared DDS setup, also seen on `main`): after a **full** start
  (stack removed and deployed, or a node boot), the REST API sometimes never finds the bays' `confirm_insert` service,
  so confirm-insert returns 500 ("timeout waiting for service /bay/bN/confirm_insert ready"). A plain
  `swarmctl deploy app` on a running stack has always been fine. **Quick fix:** start any fresh ROS process, for example
  ```bash
  docker exec "$(docker ps -qf name=_control.)" /opt/volley/entrypoint.sh ros2 node list --no-daemon --spin-time 5
  ```
  or restart central (`docker service update --force app-comb_central`). (On PR #1018's build, a stuck REST API also
  logs `recreating its client` once a minute. Other builds just fail the confirm-insert.)
- **Nothing from the DDS tests is left on comb:** the scripts, logs and `~/swarm-exp` were copied to
  `results/2026-11-04/` locally and deleted from `/home/ops` and the containers' `/tmp` (22:35Z).

## For tomorrow (resuming the DDS investigation)

**Where it stands (2026-11-04 22:30Z):**
- full starts STUCK 6 of 8 (build `e1d24a7`: 4 of 5)
- ruled out: socket overflow (E2: 4 MiB buffers, 0 drops, still stuck), a discovery server restart alone (E1b),
  recreating clients, waiting (12+ min)
- **a new participant joining un-sticks the REST API: 3 of 3**
- leading hypothesis H7: a discovery race at full start, with bay 7's endpoint announcements not acted on and never
  re-sent

**Before testing:**
1. ~~**Check what she left:**~~ **Done 2026-11-05 00:58Z** (findings 1.17): she had deployed `bay-refactor` from the local
   registry (`VOLLEY_REGISTRY` already uncommented); `VOLLEY_VERSION=dds-diag-29712d9` set, deployed, `GITSHA=29712d9` and
   the verbosity read-back confirmed. Over non-interactive ssh, `export HOSTNAME=$(hostname)` before `swarmctl deploy`.
   Original text: **Check what she left:** `cat /data/swarm/.env.local` (`VOLLEY_VERSION`, `VOLLEY_REGISTRY` commented,
   `BAY_IDS_OVERRIDE="7"`), and `docker stack ls`. For the diagnostic runs, uncomment `VOLLEY_REGISTRY` and set
   `VOLLEY_VERSION=dds-diag-29712d9` (in-place edit as above), deploy, and check `GITSHA` is `29712d9`. (PR #1018's own
   build, `pr-1018`, is `07eb74d` since the client-recreate commit was dropped.)
2. **Reinstall the scripts** (comb was cleaned up): from `results/2026-11-04/` on the laptop,
   `scp scripts/dds_attempt_diag.sh scripts/probe_clients.py ops@central-comb-5675-pecos:` and
   `chmod +x ~/dds_attempt_diag.sh`.
   For experiments that edit stack files, make a fresh `cp -r /data/swarm ~/swarm-exp`.
3. **Run attempts from your own interactive shell on comb,** or remotely as a systemd user unit with `HOSTNAME` set
   (plan 4.3); never `nohup` over a non-interactive ssh.

**The diagnostic build:** branch `jmg/test/dds-rest-api-diagnostics`, head `29712d97`, pushed (origin matches; no PR)
(plan, "The investigation branch").
- `dds-diag-29712d9` is in comb's registry (`central-comb:4000`): all five images, built from `29712d97` and pushed from
  the laptop with `tools/local-runtime-deploy` (`../../garage/deploy_and_test.md` 3.7). `GITSHA=29712d9` in bay, central, control and
  mapserver; `noc` (the PHP NOC) carries no `GITSHA`. The older `dds-diag-5f72fca` tags were deleted.
- Deploy with `VOLLEY_REGISTRY` uncommented and `VOLLEY_VERSION=dds-diag-<sha>`, then run `dds_attempt_diag.sh`
  (reinstall from `results/2026-11-04/scripts/`, with `probe_clients.py`).

**Done 2026-11-05 02:01-02:24Z:** diag1 ok, diag2 STUCK with `rq_readers=0 rr_writers=0`, no EDP warning, recovered 1 s
after the probe (findings 1.18-1.19). The scripts are installed in `~ops` (fixed warnings grep). Stack healthy afterwards.

**2026-11-05 04:05Z:** diag15 (captures off) STUCK: the REST API never learned bay 7's state-machine participant at all;
a bare node joining healed it in 2 s (findings 1.22). Watchdog build `25f354b` deployed, loop `dds-loop-16` running.
Branches: `jmg/test/rest-api-dds-watchdog` (`25f354bc`, unpushed), `jmg/test/discovery-server-settle` (entrypoint settle,
uncommitted), swarm-deploy `jmg/discovery-server-settle` (uncommitted). `.env.local`: `VOLLEY_VERSION=dds-diag-25f354b`.

**2026-11-05 05:06Z:** decision: no more investigation arms, test the patches. Watchdog (poke) build `aeb5990` under a long
unattended loop `dds-loop-31` (diag31-70, captures off; stops at the first watchdog line). diag3-30: 1 STUCK of 28. Settle
build `651eb3d` pushed; `~/swarm-exp` on comb carries the settle variable and that build; its loop runs after the watchdog
has healed a start. PR texts: `patches/pr_texts_dds_mitigations.md`. To restore comb afterwards: `.env.local` back to
`VOLLEY_VERSION=pr-1018` with `VOLLEY_REGISTRY` commented, deploy from `/data/swarm`.

**2026-11-05 15:07Z, end of the session's comb work:** comb runs the feature tip `07eb74d` from the local registry
(`VOLLEY_REGISTRY` uncommented, `VOLLEY_VERSION=pr-1018-07eb74d`), because ECR's `pr-1018` on the node is a cached `e1d24a7`
and swarmctl deploys with `resolve-image never`. Branches: volley `jmg/SW2-1181/rest-api-dds-watchdog` (`d43ce589`, one
commit, hardened), `jmg/SW2-1182/discovery-server-settle` (`296cfb40`, held), swarm-deploy `jmg/SW2-1182/discovery-server-settle`
(`ec14784`, held); the three `jmg/test/…` branches are the comb builds. Tickets SW2-1181, SW2-1182. Doc for teammates:
https://claude.ai/artifact/RiT4zStfmPpMVFsJGfyNwS. PR texts: `patches/pr_texts_dds_mitigations.md`.

**Next experiments, in order:**
1. **Unrelated-probe test:** when stuck, start a participant that creates no bay clients
   (`ros2 node list --no-daemon --spin-time 5` in `control`). Recovery would mean any new participant triggers it;
   no recovery would mean it takes interest in the same topics.
2. **Packet capture of a stuck start** (plan section 6). `ops` may not be allowed `sudo nsenter`/`tcpdump` either:
   check `sudo -l` first, or ask Dan.
3. ~~The REST API as a plain client~~: **withdrawn.** In Fast DDS ≥ 3.5.0 a CLIENT behaves like a SUPER_CLIENT
   (Codex review, verified). See the revised next steps in notes item 338.
4. **Codex review:** `reviews/codex_dds_review_prompt.md` (report to `reviews/codex_dds_review_1.md`).
5. **Bring Dan in** with the summary: the fix will likely be in swarm-deploy (start order, profile) or the Fast DDS
   version.
