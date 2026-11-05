# 09 · Running the sessions in Claude (web interface)

> **Shortcut:** `uv run ~/repos/volley_notes/guide/volley_guide.py` walks you through everything in this file interactively. It shows each step's commands (and runs them on request), the files to upload with their token sizes, and copies each prompt to your clipboard (install `wl-clipboard` first). It also tracks your progress. `volley_guide.py list` shows where you are.

This is the operational part: exactly which file to make, what to upload, what to paste, and where to save the answer, session by session. Files 06 (packs) and 07 (prompts) are the reference; this file is the checklist you follow.

## 9.1 Web interface or Claude Code?

**The web interface (claude.ai) is enough for the whole plan.** Use a **Claude Project** so that the base prompt and your notes ride along automatically. All packs in file 06 fit comfortably in a chat, including `scheduler.cpp` (47k tokens) and the biggest package packs (≤ ~120k).

| Use the web interface (default) | Reach for Claude Code (optional) |
|---|---|
| Phases 1–3: orientation, contracts, skeletons | Following a call chain across many packages without pre-selecting files |
| Phase 4 deep dives from a pack | Confirming behavior by **running** tests or `ros2` commands |
| Phase 5 slices (you pick files with `rg`) | Your first real edit: P-change review on live code, then making the change |
| Writing and merging notes | |

The workflow below is web-only. If you do use Claude Code later, use the read-only variant in 07 §7.3 and save its answers into the same notes files.

## 9.2 What lives where (and which file gets updated)

There are two kinds of files. Keep them separate:

- **The guide (00–09)** is the *method*. You don't update it during sessions. When you want it changed, ask for that in this conversation.
- **Your notes** are the *knowledge*. Sessions only ever produce or update these.

```text
~/repos/volley_notes/              ← git repo for your knowledge (commit after every session)
├── guide/                         ← these 00–09 files + volley-recon.sh (method; read-only in sessions)
├── stack-map.md                   ← layer table + build/runtime facts (Project knowledge)
├── codemap.md                     ← generated detailed file layout of every package (attach in S1, then as needed)
├── recon.md                       ← sizes, docs freshness, pattern counts, hotspots (attach in S1)
├── volley-notes.md                ← THE living summary. Updated at the end of every session. ≤3,000 words.
├── packages/                      ← one document per package (01-volley_cmake.md, …), the main output
└── subsystems/                    ← slice / ticket notes
    ├── 00-orientation.md
    ├── 01-contracts.md
    ├── 02-foundations.md
    └── …

~/volley-packs/                    ← repomix outputs (regenerable, never commit)
```

The rules:

- **`volley-notes.md` is the only file every session updates.** It's short: the glossary, architecture summary, layer map, conventions, open questions, and a one-line index of the `subsystems/` files.
- **Each session also creates one new `subsystems/NN-*.md`** holding the full detail from that session's answer. These stay *out* of the Project knowledge so they don't add tokens to every chat. You attach one only when a later session needs it.
- **`stack-map.md` and `volley-notes.md` go into the Project knowledge**, and nothing else does. `codemap.md` and `recon.md` are attached to the S1 chat (and again whenever useful), not kept in knowledge, because together they're ~20–35k tokens.

One-time setup on the **[HOST]**:
```zsh
mkdir -p ~/repos/volley_notes/{guide,subsystems} ~/volley-packs
mv ~/repos/volley_notes/volley-recon.sh ~/repos/volley_notes/guide/   # plus the 00–09 .md files
cd ~/repos/volley_notes && git init -q 2>/dev/null; true
cp ~/repos/volley_notes/guide/stack-map.md ~/repos/volley_notes/stack-map.md
```

## 9.3 One-time: create the Claude Project

1. In claude.ai, go to **Projects → Create project** and name it "Volley onboarding".
2. **Project instructions:** paste the base prompt from 07 §7.2 (Project version).
3. **Project knowledge:** upload `stack-map.md` and `volley-notes.md`. (If you uploaded `recon.md` earlier, remove it.) Also enable **Settings → Code execution and file creation**, so Claude can hand you `.md` files. Seed `volley-notes.md` with the skeleton below, then paste your existing dev-environment notes into its first section.
4. Nothing else goes into knowledge. Packs are attached to individual chats.

Seed for `volley-notes.md`:
```markdown
# Volley notes

## Dev environment
(paste your existing devcontainer / poe / direnv notes here)

## Glossary

## Architecture summary
(components, how they talk, layer order)

## Conventions & safety rules
(C++20, clang-tidy, ownership, executors/callback groups, error handling, tests)

## Subsystem index
| File | Covers | Session date |
|---|---|---|

## Open questions
```

## 9.4 The loop for every session

| Step | Where | What you do |
|---|---|---|
| 1 | [HOST] terminal | Build the pack for this session (the command is in the §9.5 table). Note the token total repomix prints. |
| 2 | claude.ai | Open the Project and start a **new chat**. Never continue an old one. |
| 3–4 | chat | **Attach** the pack(s) plus any `subsystems/` file the table lists, **and paste the task prompt in the same message**. Then send. A message with no pack or task just gets the question "which session?". |
| 5 | chat | Ask **at most 2–3 follow-ups**. Each turn re-sends the whole chat, so long chats get expensive. |
| 6 | chat | Paste the **save-detail prompt** (§9.6). If Claude returns a file, download it to `~/repos/volley_notes/subsystems/NN-name.md`. If it returns a fenced Markdown block, click the block's copy button and press `[w]` in `volley_guide.py`. |
| 7 | chat | Paste the **merge-notes prompt** (§9.6). Download the full new `volley-notes.md` and overwrite your local copy. |
| 8 | claude.ai Project | In Project knowledge, **delete the old `volley-notes.md` and upload the new one**. |
| 9 | [HOST] | `cd ~/repos/volley_notes && git add -A && git commit -m "session NN: <topic>"`. `git diff` shows what you learned. |

Read the subsystem file yourself before the next session. The LLM's job is to point; yours is to verify against the code.

## 9.5 The sessions: one package per chat, bottom-up

`volley_guide.py` reads every `package.xml` in `src/` and orders the packages **bottom-up by dependency depth**: packages with no workspace dependencies first, then the ones that only use those, and so on. Within a depth, more widely used packages come first. The Python orchestration packages (`common_py`, `sim_metrics`, `scenario`, `central_api`, `launcher`) are deferred to the end, because they compose the nodes you'll already have documented.

Each package becomes a step `Pnn`. Packages above ~60k tokens are split into parts (`Pnn-1`, `Pnn-2`, …). Tests go into the last part, compressed if they're too large.

For every step the script:
1. writes the exact file list (sources, headers, CMake, package.xml, launch/config; never meshes or site data) and the task text to `~/volley-packs/work/`;
2. builds `~/volley-packs/Pnn-<pkg>-partXofY.md` with `repomix --stdin --header-text … --instruction-file-path …`, so the pack's header names the package and its last section, **Instruction**, holds the task;
3. lists what to attach: the pack, plus any relevant repo doc on part 1 (e.g. `architecture/bay.md` for `bay`), plus your package doc from earlier parts on parts ≥ 2;
4. shows the task prompt to paste ([c] copies it);
5. saves the result to `~/repos/volley_notes/packages/nn-<pkg>.md`. If Claude returns a code block instead of a file, [w] saves it from the clipboard.

Every package document has the same sections: summary, files table, public API, **Mermaid diagrams** (UML classDiagram with ownership on the edges, data-flow flowchart, stateDiagram-v2 for state machines), behavior, ownership and safety, math in LaTeX, tests, idioms, and open questions.

**When packages change (regenerating docs):**
```zsh
cd ~/repos/volley_notes/guide
uv run volley_guide.py stale                               # which packs are missing or older than their code
uv run volley_guide.py export --changed                    # → /tmp/volley_repomix_commands.sh (refresh task embedded)
bash /tmp/volley_repomix_commands.sh                       # rebuild just those packs
uv run volley_guide.py export --out /tmp/all.sh            # or: every package's command (new-doc task embedded)
uv run volley_guide.py export --only central,bay --refresh # specific packages, refresh task embedded
```
For each rebuilt pack: start a new chat, attach the pack **plus your current `packages/nn-<pkg>.md`**, and paste the Refresh prompt (`volley_guide.py copy Pnn 2`). Claude returns the complete updated document, with a "Changes since last version" list at the top. Save it with `[w]` and commit, so `git diff` shows what changed.

After the packages: **SLICE** (vehicle retrieval end to end, with a sequence diagram) and **TICKET** (P-change before your first edit).

## 9.6 Prompts specific to the web workflow

**Project instructions:** use 07 §7.2 (Project version).

**Save-detail prompt** (step 6): see 07 §7.5. It asks for a downloadable file and falls back to one fenced Markdown block.

**Merge-notes prompt** (step 7): see 07 §7.5. It returns the complete `volley-notes.md` the same way.

**When a later session contradicts earlier notes**, add this to the task prompt:
*"If anything here contradicts volley-notes.md or the attached subsystem file, list the contradictions first, with paths."*

## 9.7 Keeping usage low in the web interface

- **One pack per chat, new chat per session, at most 2–3 follow-ups.** A long chat re-sends every earlier turn and attachment.
- **Keep Project knowledge small:** just `stack-map.md` (~900 words) and `volley-notes.md` (≤3k words). Big knowledge bases cost tokens in every chat.
- **Ask for downloadable files** rather than having long answers repeated in the chat.
- **Compressed first, full source second.** Only send full bodies for the files a skeleton answer told you to read.
- **Update `stack-map.md`** (and replace it in the Project) only if the package graph changes.
