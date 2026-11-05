# SW2-1135: Rename the scheduler's members, expansion methods and plan context (and small clean-ups)

The second sub-ticket of the Scheduler Core Refactor (epic SW2-482): stage 2, phase B2 of
`../PROMPT.md` (commits 2 and 3). Work item: https://volleyautomation.atlassian.net/browse/SW2-1135.

Scope widened on 2026-10-29: after the two rename commits, small code-quality clean-ups, one per
commit, behaviour unchanged (see `jira_ticket.md`). Branch: `jmg/SW2-1135/scheduler-renames-and-cleanups`, created
from `main` at `61e7b0d7`. PR title:
`[SW2-1135] Rename, clean up and split the scheduler before the tray solver`.

| File | What it is |
|---|---|
| `jira_ticket.md` | The ticket's title, how to create it under the epic, and its description. Create the ticket from it first. |
| `pr_description.md` | The PR title and body to paste into GitHub, in the repo's `# What` / `# Why` / `# Testing` form. Drafted; the testing lines are filled at the end of the stage. |
| `code_notes.md` | The description of the commits as they stand, rewritten after every change. Empty until commit 2 starts. |
| (moved) | `garage/deploy_and_test.md`: testing in simulation, deploying to a garage, the NOC and the dispatcher. `investigations/dds_rest_api_discovery/findings.md`: the confirm-insert failure and "carrying t0", investigation to date. `garage_troubleshooting_reference.md`: every command used on the garage, with how to read the output. `dds_root_cause_plan.md`: how to find the DDS root cause (repos, config files, hypotheses, experiments). `confirm_insert_fix_proposal.md`: the client-refresh patch (`073556ea`), which didn't fix it. `dds_investigation_summary.md`: one-page summary of the DDS investigation (runs, topology, what's established, open hypotheses, constraints). `codex_dds_review_prompt.md`: the prompt for an independent Codex review of it (report goes to `codex_dds_review_1.md`). `dds_handoff_2026-11-04.md`: the pause of 2026-11-04 (comb lent for unrelated testing): a note for the teammate, and how to resume tomorrow. `fable_dds_session_prompt.md`: the prompt to start a new session that continues the DDS investigation. `comb_results_2026-11-04/`: raw logs and the scripts from comb (checksum-verified before comb was cleaned up). |
| `codex_reviews/` | The Codex reviews (`codex_review_1.md` to `_18.md`), each with its evaluation, and `codex_review_prompt.md`, the prompt they ran with. |

The running review log of the whole refactor stays in `../SW2-482_notes.md`; this stage's items start
after 158. The conventions to follow are `../review_rules.md`, section 7 in particular.
