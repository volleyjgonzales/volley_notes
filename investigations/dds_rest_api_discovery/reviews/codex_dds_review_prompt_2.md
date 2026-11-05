# Second independent review: the DDS investigation's conclusions and the two proposed patches

You are reviewing the second phase of an investigation into why one ROS 2 process on a test garage sometimes
never discovers a service that is plainly available. Your first review (`../reviews/codex_dds_review_1.md`) was folded into
the plan; since then the team ran about 40 instrumented full starts, narrowed the failure to a specific shape,
and wrote two patches. Your value is again an independent read: **don't assume anything is correct because it's
written down.** Check the conclusions against the raw results, judge whether the patches are the right ones,
and say what you would do differently.

## Where things are

- **Notes folder:**
  `/home/jon-gonzales/repos/volley_notes/investigations/dds_rest_api_discovery/`.
  Read in this order:
  1. `../summary.md`: the one-page picture, the table of every start, what's established (items 1-9),
     the hypotheses' status.
  2. `../findings.md`, sections 1.17-1.22: the instrumented runs, in particular 1.19 (diag2) and
     1.22 (diag15, the whole-participant miss and the no-clients probe).
  3. `../patches/pr_texts_dds_mitigations.md`: the two patches as their PR texts.
  4. `../results/2026-11-05/`: the raw outputs (`logs/dds_attempts.log` has one line per attempt; `logs/dds_central_diag15_*.log`
     is the full central log of the stuck start; `logs/central_diag_diag2_recovery.txt` the diag2 recovery) and the
     scripts that produced them (`scripts/dds_attempt_diag.sh`, `dds_loop.sh`, `probe_unrelated.py`).
  5. `../plan.md`, sections 3 (hypotheses), 5 (E8 and "The investigation branch") and 6.
  6. `../reviews/codex_dds_review_1.md`: your first review, for what was already said.

  The running log is `.../SW2-482_scheduler_core_refactor/SW2-482_notes.md`, items 355-376, with exact timestamps.
- **volley repo:** `/home/jon-gonzales/volley`. Branches to read with `git show`/`git diff`, don't check them out:
  - `jmg/rest-api-dds-watchdog` (`82df8676`, one commit off `main`): patch A, the watchdog.
  - `jmg/discovery-server-settle` (`296cfb40`, one commit off `main`): patch B's volley half, the entrypoint.
  - `jmg/test/dds-rest-api-diagnostics` (`4b005718`): the instrumentation the results came from
    (`src/central_api/central_api/dds_diagnostics.py`). Not for shipping.
- **swarm-deploy:** `/home/jon-gonzales/swarm-deploy`, branch `jmg/discovery-server-settle` (`ec14784`): patch B's
  stack half.
- **Fast DDS** 3.6.2, rmw_fastrtps 9.4.9, ROS Lyrical. Source not on this machine; use the eProsima repository,
  its issue tracker (`gh` works) and the docs. PR #6542 on the `3.6.x` branch is the upstream lead.

## Rules

- **Read-only.** Don't modify, stage, commit or push anything in any repository. Don't edit the existing notes.
- **Don't connect to the garage** (`ssh ops@central-comb-5675-pecos` or any node).
- **Label every claim** as in your first review: Verified (checked in the cited code, data or document), or
  Inferred with a confidence. Cite file and line, or the log line and timestamp.
- **Write your report to one new file:** `../reviews/codex_dds_review_2.md` in the notes folder.

## What we need from you

1. **The conclusions.** The summary's established items 8 and 9 say: in a stuck start the REST API's participant
   never learned one specific remote participant (bay 7's state machine), nothing in the process was blocked,
   Fast DDS logged no warning with the warning level confirmed on, and any new participant joining repaired it
   within 2 s (5 of 5, once with a node that had no clients). Check each against the raw lines. Is any of them
   over-stated? Is there a reading of diag15 other than "the discovery stream from the server to this one reader
   lost the announcement and nothing resynchronised it"?
2. **The rate change.** 7 STUCK of 10 full starts before 02:54Z on 11-05, then 1 of about 40. Two things changed
   together: build `4b00571` added a per-second graph query (reads of the rmw graph cache under its mutex, no
   participant, no traffic) and the packet captures came and went. Could the graph query plausibly suppress the
   race? What else could? What single experiment would separate them cheapest?
3. **Patch A, the watchdog** (`bay_client_watchdog.py`, the REST API wiring, `respawn=True` in the launcher).
   Review the logic, the thresholds (60 s, 5 s hold, 30 s), the liveness rule (garage info within 10 s and a bay
   report at most 10 s stale), the second rclpy context as the poke, the hard exit, and what `respawn=True` changes
   for other crashes. What can go wrong: a restart loop, a false trip during a bay restart, the poke's context
   interfering with the main one, in-flight requests. Is a poke from inside the stuck process the same as the
   probe's join from another container?
4. **Patch B, the settle gate** (the entrypoint change and the three swarm-deploy files). It is held, untested on
   comb. Is 10 s the right shape of gate at all, given that nothing in Swarm orders services? Would you ship it
   as a hypothesis, test it first, or replace it with something else (a server healthcheck the probe waits on,
   the server in its own stack, `endpoint_mode: dnsrr`)?
5. **What's missing before an eProsima report**, given we have no capture of a stuck start and the failure is now
   rare. Is there a cheaper decisive observation than a capture?
6. **Anything we got wrong**, in the write-up for teammates (same content as the summary) or in the tests
   themselves: the detector, the hands-off window, the probe order, the judgment at 180 s.

Keep it under 1500 words, findings first, in the order above.
