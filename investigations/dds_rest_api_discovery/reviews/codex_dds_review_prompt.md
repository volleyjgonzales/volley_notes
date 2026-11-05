# Independent review of a DDS discovery failure investigation

You are reviewing an investigation into why one ROS 2 process on a test garage sometimes never discovers a
service that is plainly available. Another engineer and an assistant have spent two days on it. Your value is an
independent read: **don't assume anything in the notes is correct because it's written down**. Check the reasoning
against the evidence, look for what was missed, and propose better explanations or experiments if you have them.

## Where things are

- **Notes folder** (all the investigation material):
  `/home/jon-gonzales/repos/volley_notes/investigations/dds_rest_api_discovery/`.
  Read in this order:
  1. `../summary.md`: one-page overview (the problem, topology, every start observed, what's
     established, open hypotheses, constraints, repos and files). Start here.
  2. `../findings.md`, issue 1, sections 1.1-1.15: the dated findings with the raw numbers. (Issue 2,
     "carrying t0", is unrelated and already fixed.)
  3. `../plan.md`: the hypotheses (H1-H7), the experiments (E1-E7), the attempt script (section 4.3).
  4. `../../../garage/troubleshooting_reference.md`: every command used, with how to read its output; the probe scripts
     (sections 7, 12).
  5. `../../../garage/deploy_and_test.md`: how the garage stack is deployed (section 3), what runs in central (3.5.1).
  6. `../patches/confirm_insert_fix_proposal.md`: the client-recreate patch that didn't fix it.

  The running log is `/home/jon-gonzales/repos/volley_notes/tickets/SW2-482_scheduler_core_refactor/SW2-482_notes.md`,
  items 285 onwards. Use it for exact timestamps and the order of events. The latest items may be newer than the
  summary.
- **volley repo:** `/home/jon-gonzales/volley`, branch `jmg/SW2-1135/scheduler-renames-and-cleanups` (`e1d24a7`).
  The REST API is `src/central_api/central_api/rest_api.py`. The DDS-related setup is listed in the summary's last
  table.
- **swarm-deploy** (stack files, Fast DDS profile, discovery server service): `/home/jon-gonzales/swarm-deploy`. The
  local checkout is older; read the current files with `git -C /home/jon-gonzales/swarm-deploy show
  origin/HEAD:<path>` (run `git fetch` first if needed). The garage runs release `c9b6529`.
- **ros2-docker** (base images, the discovery server image): GitHub only,
  `gh api repos/VolleyAutomation/ros2-docker/contents/Dockerfile --jq .content | base64 -d`.
- **Fast DDS** is 3.6.2 (rmw_fastrtps 9.4.9, ROS Lyrical). The source isn't on this machine. Use your knowledge, the
  eProsima Fast-DDS repository and its issue tracker on GitHub (`gh` works), and the Fast DDS documentation.

## Rules

- **Read-only.** Don't modify, stage, commit or push anything in any repository. Don't edit the existing notes.
- **Don't connect to the garage** (`ssh ops@central-comb-5675-pecos` or any other node). It's a shared test system,
  and every experiment there takes it down. Propose experiments; don't run them.
- **Write your report to one new file:** `../reviews/codex_dds_review_1.md` in the notes folder above.
- **Mark every claim** as *verified* (you checked it in code, docs or data; cite file and line, commit, or URL) or
  *inferred* (your reasoning). Say how confident you are in each proposal.

## What we need from you

1. **Critique of the reasoning.** Are any of the "established" points in the summary not actually supported by the
   data? Were any results misread? Pay particular attention to:
   - the claim that the REST API registers last (participant ID 7) and why
   - the conclusion that UDP socket overflow is *not* the cause (E2: 4 MiB buffers, 0 drops, still stuck), and
     whether drops could be happening somewhere that wasn't measured (the discovery server, bay 7's host, the
     sender side, shared memory)
   - the inference that a joining participant un-sticks the REST API (2 of 2), and the alternative that the
     recovery time is coincidental
   - the recovery-time windows, given the REST API logs at most once a minute while stuck
2. **Fast DDS mechanics.** With Fast DDS 3.x discovery-server (client / super-client) behaviour in mind, explain
   which mechanisms could leave one participant permanently unmatched with remote endpoints the server knows
   about, while new participants match at once. Cover:
   - PDP/EDP ordering
   - how the server relays EDP to clients and super clients, and whether it re-sends
   - lease and liveliness
   - client re-sync, and what a server or client restart triggers
   - type propagation being disabled
   - SHM vs UDP locator selection
   - the discovery server running without the profile

   Point to Fast DDS issues, pull requests or release notes after 3.6.2 that look related.
3. **Hypotheses we haven't considered.** Anything in the setup that could explain why it's always the REST API (the
   Python, late-registering super client), why only full starts trigger it, and why the rate is about 2 of 3. Include
   things outside DDS if relevant: Docker overlay or VXLAN, DNS resolution of `discovery-server` at startup (the
   server gets a new IP on every restart; clients resolve the name once), the entrypoint probe, `ros2 launch`'s own
   participant whose sockets are inherited by every child, rclpy specifics.
4. **Experiments, ranked by information gained per garage minute.** For each: what it distinguishes, the exact
   change (file, setting, command), how to read the result, and the cost (stack restarts, builds). Experiments
   that can be done off the garage (for example a Docker Compose reproduction on a laptop, with the same images
   and profile) are especially valuable: say how you'd build one.
5. **Fixes.**
   - **Short-term mitigations:** for example the REST API restarting itself when a bay is alive but unmatched, or
     running the REST API as a plain client.
   - **The real fix,** with its trade-offs, and which repo each belongs in (volley, swarm-deploy, ros2-docker,
     upstream Fast DDS).
6. **Questions** the team should answer, or data it should collect, before choosing a fix. Also what a good
   eProsima bug report would need, if it's a Fast DDS bug.

Be concrete and concise. A short list of well-supported points beats a long list of possibilities. If you think the
investigation is on the wrong track, say so plainly and explain why.
