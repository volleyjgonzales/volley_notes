# 07 · Prompt library

All prompts used with the packs. Each session uses: **base prompt** (§7.2, set once as the Claude Project instructions) + **one task prompt** (§7.4) + the attached pack(s), sent **in one message**. `stack-map.md` and `volley-notes.md` come from the Project knowledge. The session-by-session workflow is in file 09.

## 7.1 Why your prompt was adapted, and how

> **Math notation:** rule 6 of the base prompt asks for LaTeX: italic scalars, bold lower-case vectors, bold upper-case matrices, with dimensions stated (e.g. $\mathbf{v} \in \mathbb{R}^n$). claude.ai renders it in chat. For your saved `.md` notes, use a viewer with math support (VS Code's Markdown preview, Obsidian, or GitHub).
>
> **Update after the second real session:** Claude kept asking "which session?" because the chat had no repomix pack and the task wasn't in the message. Now every step builds a pack with the task embedded at the end, and the base prompt says to follow the pack's Instruction section. Diagrams are now part of every package document: UML classDiagram, data-flow flowchart, and stateDiagram-v2 for state machines.
>
> **Update after the first real session:** two changes. (1) The base prompt listed "confirmed facts", so Claude audited them when a chat had no pack attached. Facts now live in `stack-map.md` as background, and the base prompt tells Claude to just ask which session you're on if no pack or task is attached. (2) "Downloadable file" only works with file creation enabled, so every file request now falls back to one fenced Markdown block. `volley_guide.py` key `[w]` saves that block from your clipboard.

Your draft prompt is a good starting point: it sets a clear role and goal, asks concrete questions, and demands concision and file paths. Six adjustments make it fit this repo and the token budget:

1. **Questions 1 and 2 are mostly answered already.** colcon/CMake, the C++ standard and dependencies come out of `recon.md` (file 05). Ask the model to *confirm and interpret* those facts rather than *discover* them; that costs fewer tokens and gives more reliable answers.
2. **Make it ROS 2-specific.** Generic options (Bazel, Abseil, Qt) waste words. In ROS 2 the real threading model is **executors + callback groups + timers**, and the main ownership questions are **message `SharedPtr`/`UniquePtr`**, node lifetimes, and callbacks that capture `this`. Ask about those directly.
3. **A chat model only sees what you attach.** "Analyze the workspace" invites confident guesses. Require evidence tags (`[seen: path]` vs `[inferred]`) and an explicit "not in provided files" answer when something is missing.
4. **Split it into a reusable base plus a per-session task.** The role, rules and output format stay constant, so put them in a Claude Project's instructions once. Each session then only states the task.
5. **Make every session feed your notes.** Each session ends with two short prompts (09 §9.6): one saves the detail to a `subsystems/` file, the other merges a summary into `volley-notes.md`. That's how knowledge accumulates without re-sending packs.
6. **Add a "before I change X" prompt** (P-change). "Safely write code" needs a prompt for the moment you actually edit code.

## 7.2 Base prompt (Project version: paste into the Claude Project's instructions)

```text
You are a senior C++ systems and performance engineer with deep ROS 2 experience
(rclcpp executors and callback groups, QoS, composable components, intra-process
comms, colcon/ament CMake). I'm new to this codebase and I'm learning it bottom-up,
ONE PACKAGE PER CHAT, starting from the lowest layer of the package dependency graph.
My goal is to understand, navigate, and safely change it without breaking its
architectural patterns or introducing memory, lifetime, or concurrency bugs.

Project knowledge (background, not claims to audit):
- stack-map.md: build/runtime facts, layer table, components per package.
- volley-notes.md: my running summary and an index of my per-package documents.

How each chat works:
- I attach a repomix pack named like P07-common-part1of1.md. Its header names the
  package; its LAST SECTION ("Instruction") contains the full task. My message
  repeats that task. Follow it even if my message text is short.
- For packages split into several parts, I also attach my package document from
  the earlier parts; extend it instead of starting over.

Rules:
1. Base answers on the attached pack; use project knowledge for context. If
   something isn't in the pack, say "not in provided files" and name the file(s)
   that would answer it. Don't fill gaps with what a typical ROS project would do.
2. Tag claims: [seen: path] when directly observed, [inferred] when deduced.
3. Point to file paths for everything. Prefer tables and short bullets. No generic
   C++ advice unless it is tied to a specific file here.
4. Flag anything risky (object lifetime, callbacks capturing `this`/raw pointers,
   data races, blocking work inside callbacks, exceptions escaping callbacks,
   unbounded queues/allocations in hot paths) as "RISK:" with the path.
5. Diagrams: Mermaid in ```mermaid blocks. classDiagram for types (inheritance,
   composition *--, aggregation o--, edge labels for unique_ptr / shared_ptr /
   reference / raw pointer), flowchart for data flow (topics, services, actions,
   timers, external I/O, calls into lower layers), stateDiagram-v2 for state
   machines (states, transitions, triggers/guards). Only draw what the pack
   supports; label guessed edges [inferred].
6. Math: use LaTeX whenever an answer involves math (costs, kinematics, geometry,
   scheduling formulations, time intervals): inline $...$, display $$...$$. Notation:
   scalars italic ($t$, $v_{max}$), vectors bold lower case ($\mathbf{v}$), matrices
   bold upper case ($\mathbf{A}$), sets/spaces blackboard bold. State dimensions when
   a symbol is introduced, e.g. $\mathbf{p} \in \mathbb{R}^2$,
   $\mathbf{A} \in \mathbb{R}^{m \times n}$, $t \in \mathbb{R}_{\ge 0}$, and say what
   each symbol means and which code variable/file it corresponds to.
7. Files: if you can create files, deliver documents as downloadable .md files.
   If you can't, output the complete document in ONE fenced block using FOUR
   backticks (````markdown … ````) so inner ```mermaid blocks survive, and nothing
   else.
````markdown with four backticks if it
   contains code blocks) and
   nothing else, so I can copy it in one go.
````markdown with four backticks if it
   contains code blocks) and
   nothing else, so I can copy it in one go.
```

## 7.3 Claude Code variant (agentic, in the container)

Claude Code can read files itself, so it doesn't need packs. It does need guardrails to keep it cheap and read-only during learning:

```text
<base prompt from 7.2, minus the "Attached:" bullet>

Work read-only: do not edit files, do not run builds, tests, or anything that
modifies the workspace. Use rg/fd to locate code and open only the files you need;
list the files you read at the end. Start from .claude/CLAUDE.md and
artifacts/recon.md.

Task: <one task prompt from 7.4>
```

## 7.4 Task prompts

**Current workflow: one package per chat, bottom-up.** `volley_guide.py` generates one step per package (P01, P02, …; big packages get parts P05-1, P05-2, …). Each step **embeds the package task in the repomix pack itself**, via `--instruction-file-path`, so the pack is self-describing. You still paste the same task into the message, together with the attachment. The script fills in the package, its position, dependencies, dependents and parts. Template:

```text
PACKAGE TASK: `<pkg>` — package 7 of 37 (bottom-up), dependency depth 2.
Attached pack: P07-<pkg>-part1of1.md. This is part 1 of 1 of this package. Start the document; later parts will extend it.
Depends on (workspace): <deps>. Used by: <dependents>.
Lower-layer packages are already documented in volley-notes.md; reuse their terms.

Write the package document 07-<pkg>.md with these sections:
1. Summary: purpose in 2–3 sentences; what it provides to the packages that use it.
2. Files: table of every file in the pack: path, lines (approx.), role in one line.
3. Public API: key types, functions, macros, components, interfaces, with paths;
   how dependents are meant to use them.
4. Diagrams (Mermaid, rule 5):
   a. UML classDiagram of the main types with ownership on the edges.
   b. Data-flow flowchart: inputs/outputs (topics, services, actions, timers,
      parameters, MQTT/DB/hardware I/O) and calls into lower-layer packages.
   c. stateDiagram-v2 for each state machine (YASMIN or enum-driven); if there is
      none, write "no state machine".
5. Behavior: construction → steady state → shutdown; executors, callback groups,
   threads, timers; parameters and their defaults.
6. Ownership and safety: object lifetimes, callbacks capturing `this`, locks and
   atomics, error handling (std::optional vs exceptions vs asserts), RISK items.
7. Math: algorithms and formulas in LaTeX (rule 6), if any.
8. Tests: what they cover, what they reveal about intended behavior, gaps.
9. Idioms to reuse when writing code here, and open questions for the team.
Deliver it as described in rule 7 (downloadable 07-<pkg>.md, or one ````markdown block).
```

**Merge notes** (after the last package of each dependency depth, or more often):
```text
Now update volley-notes.md (in the project knowledge) with this package's results.
Merge into existing sections instead of appending; add one row to "Package index"
for packages/<NN-pkg>.md (package, one-line purpose, key types); add new glossary
terms and conventions; move answered items out of "Open questions"; keep
[seen]/[inferred] tags; keep the whole file under 3,000 words.
Return the COMPLETE updated file as described in rule 7.
```

The prompts below are from earlier iterations. P5 (slice) and P-change (ticket) are still used. The others are kept for reference only.

**P1: Orientation** (Phase 1; your four questions, adapted)
```text
Task (orientation), using recon.md and the pack. Max 700 words.
1. Build & entry points: confirm the build flow (colcon -> volley_cmake macros ->
   targets) and the key macros a package uses. List runtime executables, components
   and launch files by package; say which launch file starts the full system / sim.
2. Toolchain & dependencies: the C++ standard and compiler/warning/sanitizer flags
   actually configured; external dependencies grouped by role (ROS core, messaging/
   MQTT, math/geometry, telemetry, persistence, testing, other). Note anything unusual.
3. Layout: where core logic, unit tests, configuration (params, layouts, schemas) and
   generated code live; restate the layer order from colcon graph in one line each.
4. Memory & concurrency: from the grep counts and any code in the pack, the dominant
   ownership style (unique/shared/raw), how messages are passed, executor types and
   callback groups, and which files contain explicit threads/locks/atomics. Say
   plainly what cannot be concluded without reading those files.
Also: a glossary of domain terms (tray, bay, VRC, node, ...) as used here.
```

**P1b: Tooling pack**
```text
Using these files, confirm or correct every item marked (inferred) or (verify) in
the "Dev environment" section of my notes, and list what prek.toml enforces.
Return only the updated Dev environment section. Max 500 words.
```

**P2: Contracts** (Phase 2)
```text
Here are all ROS 2 interface definitions and package manifests. Group interfaces by
subsystem, describe each topic/service/action's purpose, and infer which package
publishes/serves vs subscribes/calls (mark [inferred]). Note message fields that
imply ownership or timing semantics (stamps, IDs, sequence numbers, large arrays).
Max 800 words; table format.
```

**P3: Skeleton** (Phase 3, one per layer pack)
```text
From these compressed headers: main classes per package with one-line
responsibilities; key abstractions (node base classes, state machines, planner
interfaces, plugin points); ownership visible in signatures (unique_ptr/shared_ptr/
references/raw pointers in members and parameters); anything that suggests threading
(mutex members, atomics, callback groups). Name the 10 files I should read in full
first. Max 600 words.
```

**P4: Deep dive** (Phase 4, one package)
```text
Deep dive on <pkg>: lifecycle (startup -> steady state -> shutdown), executor and
callback-group setup, which callbacks can run concurrently and what shared state
they touch, state machines and their states, ROS interfaces it owns, parameters,
error handling, ownership/lifetime of the main objects, and anything surprising or
fragile (RISK:). Max 600 words.
```

**P5: Vertical slice** (Phase 5)
```text
Trace <feature, e.g. vehicle retrieval> from operator request to AGV motion to bay
confirmation. Numbered sequence with path:line for each hop, the message/service/
action used, which executor/thread runs it, and where state is persisted. Flag any
hop you couldn't find. Max 600 words.
```

**P6: History** (Phase 6)
```text
Using the git log and compressed code: what changed in this package recently and
why, which areas are churning, and what tech debt is implied. Cross-check with
docs/deprecated/tech-debt.md if attached. Max 400 words.
```

**P-change: before you edit anything** (use with the files you'll touch plus their callers)
```text
I'm about to change <symbol/file> to <goal>. Using the attached files:
1. Who calls this, from which executor/callback group/thread? Can it run
   concurrently with anything that touches the same state?
2. Ownership and lifetime of every object involved (creator, holder, destruction;
   any callback capturing `this` or raw pointers).
3. Invariants and local patterns I must follow (error handling, logging, parameters,
   naming, clang-tidy rules, tests).
4. Tests that cover this today, and the tests I should add.
5. RISK: items in my planned change. Max 400 words.
```

## 7.5 End-of-session prompts

**Save detail:**
```text
Write everything we established in this chat as a standalone Markdown file named
<NN-name>.md: purpose, position in the stack, key files (paths), public API, classes and
responsibilities, idioms, executor/threading and ownership findings, ROS interfaces,
parameters, RISK items, and open questions. Keep [seen]/[inferred] tags. No length
limit, but no repetition.
Deliver it as a file: if you can create files, a downloadable <NN-name>.md; otherwise the
complete file in ONE fenced block (````markdown with four backticks if it
   contains code blocks) and nothing else.
```

**Merge notes:**
```text
Now update volley-notes.md (in the project knowledge) with this session's results.
Merge into existing sections instead of appending; add one row to "Subsystem index"
for subsystems/<NN-name>.md; move answered items out of "Open questions"; keep
[seen]/[inferred] tags; keep the whole file under 3,000 words.
Return the COMPLETE updated file: if you can create files, as a downloadable
volley-notes.md; otherwise in ONE fenced block (````markdown with four backticks if it
   contains code blocks) and nothing else.
```
