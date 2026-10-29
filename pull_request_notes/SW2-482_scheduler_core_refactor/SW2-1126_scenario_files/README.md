# SW2-1126: Record the scheduler planning tests as scenario files

The first sub-ticket of the Scheduler Core Refactor (epic SW2-482): the parity baseline, stage A of
`../PROMPT.md`. Branch `jmg/SW2-1126/scheduler-scenario-files`, two commits (`28f69008`, `6d4ae5b5`);
PR #1007, merged into main on 2026-10-29 as `61e7b0d7`.

| File | What it is |
|---|---|
| `code_notes.md` | The description of the commits as they stand, rewritten after every change: files, how a test run flows, the comparison, clang-tidy, questions and answers, the reviews, open points. Read this first. |
| `scenario_selection.md` | How the scenarios were chosen: every old test mapped to its scenario, the four new ones, the layout decisions, the gaps and the points to decide. For reviewing the selection. |
| `jira_ticket.md` | The ticket's title, how it was created under the epic, and its description. |
| `pr_description.md` | The PR title and body to paste into GitHub, in the repo's `# What` / `# Why` / `# Testing` form, with the traceability list. |
| `review_meeting_agenda.md` | The 30-minute walkthrough for the reviewers: timeboxed topics, what to have open, likely questions with short answers. |
| `pr_prep_plan.md` | The assessment of the branch against the team's implicit review guidelines, with what was applied. |

The running review log of the whole refactor stays in `../SW2-482_notes.md`; this sub-ticket's rounds are
its items 1 to 157. The conventions the review settled are distilled in `../review_rules.md`, section 7.
