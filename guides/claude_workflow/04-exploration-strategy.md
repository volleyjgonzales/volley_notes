# 04 · Exploration strategy

The goal is to understand the codebase in layers. Each layer costs a few thousand to a few tens of thousands of tokens, and you only spend more once a layer has told you where to look next. Files 05–07 put this into practice.

## 4.1 Where to run things

Every command block is tagged:

- **[HOST]** means your laptop's terminal: **zsh with oh-my-zsh**, outside Docker.
- **[CONTAINER]** means a terminal inside the dev container: any VS Code terminal once you're attached, or `devcontainer exec --workspace-folder ~/volley zsh` / `docker exec -it volley-user-develop zsh` from the host. The container shell is **zsh without oh-my-zsh**, with its own `~/.zshrc` that hooks direnv (see 03 §3.5).

**Which side am I on?** `--network=host` makes the container share your hostname, so the prompt looks identical. Check with `ls /.dockerenv && echo "in container"`.

The rule of thumb: **reading and packing code happens on the [HOST]; building and anything ROS happens in the [CONTAINER].** Repomix, fnm and uv-for-tooling don't need ROS, and installing them on the host means they survive container rebuilds.

Two facts from `devcontainer.json` that matter here:

1. **The repo path is identical in both places** (`~/volley` → `/home/jon-gonzales/volley`), so file paths in notes and LLM answers work either side.
2. **`~` is different in each place.** The container home is a Docker volume (`volley-home`), not your host home. So `~/volley-packs` inside the container is *not* the same folder as on the host. To move files between them, use the repo's bind-mounted **`artifacts/`** folder (`$ARTIFACTS_DIR` in the container). It's meant for exactly this; check that it's gitignored with `git check-ignore -v artifacts/foo`.

## 4.2 Strategy in one page

**Rule 1: Measure before you pack.** Every repomix run prints a token count. Use `--token-count-tree` (free, local) to see where the tokens live before you send anything to an LLM.

**Rule 2: Signatures before bodies.** `--compress` uses Tree-sitter to keep classes, functions and interfaces and drop most implementation. That is roughly what you'd skim as a human anyway. It handles both C++ and Python.

**Rule 3: One pack, one question.** Don't upload a pack and ask "explain this." Ask a specific question ("Draw the data flow from a retrieval request to an AGV order"). Specific prompts produce shorter, more useful answers.

**Rule 4: Carry notes forward, not code.** After each session, have the LLM update a running `volley-notes.md`. Start the next session with the notes plus a new pack. Don't re-upload old packs. The notes are your compressed memory.

**Rule 5: New chat per subsystem.** Long chats re-send their whole history every turn. A fresh chat with `notes + one pack` is much cheaper than turn 40 of a mega-chat.

**Rule 6: Use free local tools for structure.** `colcon graph` (container), `tokei`/`cloc`, `rg`, `git log` (host) and clangd (container, via VS Code) answer many questions at zero token cost.

**Rule 7: Consider Claude Code for the deep-dive phases.** The repo ships `.claude/CLAUDE.md` and `.claude/settings.json`, and the dev container auto-installs the Claude Code VS Code extension, so the team already uses it. Run it **in the [CONTAINER]** so it can also build and run tests; your login persists in the `volley-home` volume. An agent that reads files on demand is usually cheaper than pasting packs, because it reads only what it needs. Repomix packs are best for the "big picture in one shot" phases.

## 4.3 Rough token budget

| Phase | What | Expected size* | Tool |
|---|---|---|---|
| 0 (file 05) | Local recon: metrics, graph, fact sheet | 0 | tokei/cloc, colcon, repomix tree |
| 1 | Orientation pack (docs-first or metadata-first) + recon.md | small–medium | repomix → chat |
| 2 | Interfaces pack | small | repomix → chat |
| 3 | Compressed headers ("skeleton") | medium | repomix `--compress` |
| 4 | Per-subsystem deep dives | medium each | repomix or Claude Code |
| 5 | Vertical-slice trace | medium | `rg` + `repomix --stdin` |
| 6 | History / hotspots | small | `--include-logs`, git |

\*Fill in the real numbers from file 05 (recon). A useful rule of thumb: keep any single pack you upload well under half of your model's context window, so there's room for the conversation.

## 4.4 Session hygiene checklist

- [ ] Start every session with `volley-notes.md` plus **one** pack.
- [ ] Ask a specific question; ask for bounded output ("under 500 words", "table").
- [ ] End every session with: *"Update volley-notes.md with what we learned; keep it under N words total."* Then replace your local copy.
- [ ] When a chat gets long, start a new one with the updated notes.
- [ ] Re-run Phase 3 skeleton packs only when the code changes meaningfully (`git log --since`).
- [ ] Never paste `build/`, `install/`, `log/`, bag files or vendored JS.
- [ ] Let repomix's secret scan run (it's on by default). Also check that site configs/params contain no credentials before uploading anything, and follow your company's policy on sharing source with external AI tools.

