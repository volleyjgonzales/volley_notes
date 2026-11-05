# 00 · Volley onboarding guide: index

A sequenced guide for getting productive in the `volley` codebase: robotic parking, ROS 2 Lyrical, colcon, ~93k lines of C++ and ~25k of Python. Read the files in order. Each file's sections are numbered with the file's prefix, so **"03 §3.5"** means file 03, section 3.5.

| # | File | What it covers | When |
|---|---|---|---|
| 00 | `00-index.md` | This index, conventions | First |
| 01 | `01-system-overview.md` | What the system is, tech stack, config files, Python deps, package map, reading order | Day 1, morning (read) |
| 02 | `02-host-setup.md` | Everything on your laptop: Docker, Tailscale, AWS ECR, X11, SSH, editor choice, fnm, uv, repomix, Rust, CLI tools | Day 1, once |
| 03 | `03-dev-container.md` | How the dev container works and how to drive it: Docker primer, VS Code or CLI launch, zsh/direnv, poe, build/test, troubleshooting | Day 1, then reference |
| 04 | `04-exploration-strategy.md` | Where to run things, token-saving rules, budget, session hygiene | Before any LLM use |
| 05 | `05-recon.md` | Zero-token reconnaissance: docs inventory, sizes, dependency graph, C++ fact sheet, `recon.md` | Day 1, afternoon |
| 06 | `06-llm-packs.md` | repomix config and Phases 1–6: what to pack, in which order | Days 2–5 |
| 07 | `07-prompt-library.md` | Base prompt + task prompts for each phase, plus the "before I change X" prompt | Used with 06 |
| 08 | `08-schedule-and-checklists.md` | 5-day schedule, day-1 checklist, open questions, files still to read | Track progress |
| 09 | `09-claude-web-runbook.md` | **How to run each session in claude.ai**: Project setup, which file to update, what to upload/paste/save, session table S0–S15 | Days 2–5, every session |
| — | `codemap.md` (generated) | Detailed file layout of every package (files, line counts, types, components, launch contents, tests), made by `volley_guide.py codemap` | optional local reference |
| — | `stack-map.md` | Bottom-up layer table, build/runtime facts, components: goes into the Claude Project knowledge | SETUP-3/4 |
| — | `volley-recon.sh` | Optional local sizing fact sheet (05 §5.7); not uploaded | As needed |
| — | `volley_guide.py` | **Interactive step-by-step guide** through setup and sessions S0–S15: commands (it can run them), files to upload with token sizes, prompts copied to the clipboard, where to save results. Run: `uv run ~/repos/volley_notes/guide/volley_guide.py` | Every session |

## Conventions

- **[HOST]** means your laptop's zsh (oh-my-zsh). **[CONTAINER]** means a shell inside the dev container (zsh, no oh-my-zsh). Check where you are with `ls /.dockerenv`.
- **(verify)** marks an inference not yet confirmed by reading the relevant file. 08 lists the files that would resolve them.
- The repo is at `~/volley`, the same path on host and in the container. Packs go in `~/volley-packs/` and your notes in the `~/repos/volley_notes/` git repo (09 §9.2).

## The path in one line

Host setup (02) → container up and building (03) → `volley_guide.py` SETUP-1…4 → **one chat per package, bottom-up** (P01 … Pnn, each with a self-describing repomix pack and a package document with UML / data-flow / state diagrams) → SLICE → TICKET.
