# 06 · LLM packs: Phases 1–6

All repomix commands run on the **[HOST]** from `~/volley`. Do file 05 first: it decides the shape of Phase 1 and gives you `recon.md`. Prompts are in file 07. **For the step-by-step session workflow in claude.ai (what to upload, paste and save), follow file 09.**

Packs are written as **Markdown** (`--style markdown`, `.md`), which uploads cleanly to the claude.ai web interface.


## 6.0 One-time: a shared ignore list

**[HOST]** Create `~/volley-packs/repomix.config.json`, passed with `-c`, so packs stay lean without touching the repo:

```json
{
  "output": {
    "style": "markdown",
    "removeEmptyLines": true,
    "showLineNumbers": false
  },
  "ignore": {
    "useGitignore": true,
    "useDefaultPatterns": true,
    "customPatterns": [
      "**/*.3ds", "**/*.dae", "**/*.png", "**/*.ico", "**/*.svg",
      "**/*.typeface.json", "**/*.tex", "**/*.cls", "**/*.bib",
      "**/terraform/**", "**/.terraform.lock.hcl",
      "src/launcher/layouts/**", "src/scenario/scenarios/**",
      "docs/assets/**", "controller_webview/fonts/**",
      "controller_webview/js/**",
      "controller_webview/includes/SleekDB/**",
      "controller_webview/css/**",
      "uv.lock",
      "artifacts/**",
      "docs/deprecated/**",
      "build/**", "install/**", "log/**", "coverage/**",
      "tools/third_party/**"
    ]
  },
  "security": { "enableSecurityCheck": true }
}
```

Check the exact config schema against your installed version with `repomix --init` (it generates a template you can compare against). If a key differs, follow the template.

Add an alias to `~/.zshrc` (after oh-my-zsh is sourced), then `exec zsh`:
```zsh
# [HOST] ~/.zshrc
alias rmx='repomix -c ~/volley-packs/repomix.config.json'
```
**zsh gotcha:** always keep repomix and `rg` globs in quotes, as below. Unquoted `**` or `!` get expanded or interpreted by zsh before the tool sees them (you'd get `zsh: no matches found`).

**All Phase 1–6 repomix commands run on the [HOST] from `~/volley`.**

---

## 6.1 Phase 1: Orientation pack (docs-first or metadata-first)

Goal: vocabulary, components, how they connect, and the C++ ground rules. Which pack you build depends on the docs inventory in **05 §5.1**.

**`recon.md` is not part of the pack.** It lives in the Claude Project's knowledge (09 §9.3), so every session sees it automatically.

**1A: Docs-first** (docs are sufficient and fresh):
```zsh
# [HOST]
cd ~/volley
rmx --include ".claude/CLAUDE.md,README.md,docs/index.md,docs/glossary.md,docs/architecture/**/*.md,docs/guides/cpp-style.md,docs/guides/volley-cmake.md,docs/guides/contributing.md,src/**/README.md" \
    --style markdown --token-count-tree 500 \
    -o ~/volley-packs/01-orientation.md
```

**1B: Metadata-first** (docs thin or stale). This version learns the structure from build metadata instead of prose:
```zsh
# [HOST]
rmx --include ".claude/CLAUDE.md,README.md,docs/glossary.md,docs/guides/cpp-style.md,src/**/package.xml,src/**/CMakeLists.txt,src/infrastructure/volley_cmake/**,src/**/launch/**,.colcon/defaults.yaml,pyproject.toml" \
    --remove-empty-lines --token-count-tree 500 \
    -o ~/volley-packs/01-orientation.md
```
Add any `docs/architecture/*.md` that 05 §5.1 showed is fresher than its code.

**Volley's actual Phase 1: hybrid** (decided from the 05 §5.1 results on 2026-10-06). This is 1B plus the current architecture docs:
```zsh
# [HOST]
cd ~/volley
rmx --include ".claude/CLAUDE.md,README.md,docs/index.md,docs/glossary.md,docs/architecture/bay.md,docs/architecture/sim.md,docs/architecture/system-tests.md,docs/architecture/vrc.md,docs/architecture/agv.md,docs/architecture/vda5050.md,docs/guides/cpp-style.md,docs/guides/volley-cmake.md,src/**/package.xml,src/**/CMakeLists.txt,src/infrastructure/volley_cmake/**,src/**/launch/**,.colcon/defaults.yaml" \
    --remove-empty-lines --token-count-tree 1000 \
    -o ~/volley-packs/01-orientation.md
```
Expect roughly 40–50k tokens (≈15k of docs, the rest manifests, CMake and macros); check the printed total. Infra docs (`docker-build`, `apt-proxy`, `discovery-server`) are left out because file 03 already covers that ground.

Add one line to the P1 task: *"agv.md (Jun) and vda5050.md (Apr) predate recent agvhito changes (Sep); treat them as possibly stale and flag contradictions with the code."*

Left out on purpose:
- `docs/deprecated/` is stale by definition. Exception: `deprecated/central.md` and `deprecated/scheduler.md` are the only long-form prose on those subsystems, so attach them to the **Phase 4** deep dives as "historical; verify against code". `tech-debt.md` belongs in Phase 6.
- `docs/guides/getting-started.md`, `simulation*.md` and `tips-and-tricks/` cover workflow you've already captured in your notes (file 03).
- `docs/papers/` is useful later, for the scheduler deep dive.

**Prompt:** base prompt (07 §7.2) + task **P1** (07 §7.4).

Save the results as described in 09 §9.4 (steps 6–9). `volley-notes.md` is the start of every future session.

**Head start:** you already have dev-environment notes (devcontainer, poe, direnv, build outputs, troubleshooting). Put them at the top of `volley-notes.md` as a "Dev environment" section, then add the Phase 1 output below it. In later sessions, tell the LLM not to re-derive anything that section already covers.

An optional **tooling pack** fills in the remaining (verify) items in those notes cheaply. These are small text files:
```zsh
# [HOST]
rmx --include ".envrc,.colcon/**,prek.toml,pyproject.toml,.devcontainer/**,scripts/set-*,scripts/util_*.sh,docker/docker-bake.hcl,docker/Dockerfile" \
    -o ~/volley-packs/01b-tooling.md
```
**Prompt:** task **P1b** (07 §7.4).

> In claude.ai, `recon.md` and `volley-notes.md` sit in the Project knowledge and the base prompt is the Project instructions (09 §9.3), so every chat has them without re-uploading.

---

## 6.2 Phase 2: Interfaces (the contracts)

Goal: every message/service/action plus package manifests. This is small and high value.

```zsh
# [HOST]
rmx --include "src/interfaces/**,src/vda5050/vda5050_interfaces/**,src/**/package.xml" \
    -o ~/volley-packs/02-interfaces.md
```

**Prompt:** base prompt (07 §7.2) + task **P2** (07 §7.4).

---

## 6.3 Phase 3: Skeleton (compressed public API)

Goal: class and function shape of the whole C++/Python codebase without bodies.

Check size first:
```zsh
# [HOST]
rmx --include "src/**/include/**/*.hpp,src/**/include/**/*.h" --compress \
    --token-count-tree 3000 -o /tmp/scratch.xml
```

If it's reasonably sized, pack all headers at once:
```zsh
# [HOST]
rmx --include "src/**/include/**/*.hpp,src/**/include/**/*.h" \
    --compress --remove-comments --no-directory-structure \
    -o ~/volley-packs/03-skeleton-cpp.md
```

If it's too big, split by the graph layers in 05 §5.3:
```zsh
# [HOST]
rmx --include "src/infrastructure/volley_cmake/**,src/core/stdx/include/**,src/common/include/**,src/core/rclcppx/include/**,src/structures/include/**" \
    --compress --remove-comments -o ~/volley-packs/03a-foundation.md

rmx --include "src/common_ros/include/**,src/core/yasminx/include/**,src/communication/mqtt/**/include/**,src/data/**/include/**" \
    --compress --remove-comments -o ~/volley-packs/03b-ros-glue.md

rmx --include "src/planner/**/include/**" \
    --compress --remove-comments -o ~/volley-packs/03c-planning.md

rmx --include "src/central/include/**,src/agvhito*/include/**,src/bay/include/**,src/lift/include/**,src/vrc/include/**,src/vecs/include/**" \
    --compress --remove-comments -o ~/volley-packs/03d-nodes.md

rmx --include "src/sim/include/**,src/vis/include/**" \
    --compress --remove-comments -o ~/volley-packs/03e-sim-vis.md
```

Python skeleton (launcher, scenarios, system tests, central_api):
```zsh
# [HOST]
rmx --include "src/launcher/**/*.py,src/central_api/**/*.py,src/scenario/scenario/**/*.py,src/system_tests/system_tests/**/*.py,src/common_py/common_py/**/*.py,src/sim_metrics/sim_metrics/**/*.py" \
    --compress --remove-comments -o ~/volley-packs/03f-python.md
```

**Prompt:** base prompt (07 §7.2) + task **P3** (07 §7.4).

---

## 6.4 Phase 4: Subsystem deep dives (full source, one at a time)

Follow the **analysis order from 05 §5.3**: foundations → contracts → launcher/common_ros → planning chain bottom-up → central → equipment → integration. Jump ahead only when your first ticket needs it. Use the per-package sizes from 05 §5.2 to decide whether a package fits in one pack or needs `--compress`.

Template (implementation only, no tests):
```zsh
# [HOST]
PKG=src/planner/scheduler
rmx --include "$PKG/**" --ignore "$PKG/test/**" --remove-comments \
    -o ~/volley-packs/04-$(basename $PKG).xml
```
Tests are a second, separate pack. Tests are great executable documentation, so read them when you want to see *behavior* rather than structure:
```zsh
# [HOST]
rmx --include "$PKG/test/**" --compress -o ~/volley-packs/04-$(basename $PKG)-tests.xml
```

Concrete set:
```zsh
# [HOST]
# in analysis order (05 §5.3); trim the list to what you'll actually read this week
for PKG in src/launcher src/common_ros \
           src/planner/task_planner src/planner/planner_core src/planner/cost_functions \
           src/planner/motion_planner src/planner/scheduler \
           src/central src/agvhito src/vda5050/map_server src/bay src/lift src/vrc src/sim; do
  rmx --include "$PKG/**" --ignore "$PKG/test/**,$PKG/**/test/**" --remove-comments \
      -o ~/volley-packs/04-$(echo $PKG | tr / -).xml
done
ls -la ~/volley-packs   # check sizes; only open what you need
```

The launcher's `layouts/` are 199k tokens of site data, so the shared config ignores them. Ignore rules beat `--include` in repomix, so use **plain `repomix` without `-c`** for the one example layout you want, e.g. the small `25_spot_single_pick.yaml` (2.8k):
```zsh
# [HOST]
rmx --include "src/launcher/launch/**,src/launcher/launcher/**,src/launcher/params/**" \
    -o ~/volley-packs/04-launcher.md
repomix --style markdown --include "src/launcher/layouts/25_spot_single_pick.yaml,src/scenario/scenarios/events_insert_retrieve.yaml" \
    -o ~/volley-packs/04-launcher-examples.md
```

**Packages that need special handling** (sizes from 05 §5.2):

- **`central`** (~119k tokens of implementation). Split it in two:
  - `--include "src/central/include/**,src/central/src/dispatch*,src/central/src/execution*,src/central/src/schedule*"`
  - `--include "src/central/include/**,src/central/src/garage_tracker*,src/central/src/metrics*,src/central/src/mqtt*"`
- **`common_ros`** (~95k). Pack `--compress` first. Then do a full pack of just the files the skeleton points at, e.g. `discrete_garage_state.cpp` (17k) and `versioned_state_buffer.*`.
- **`scheduler`**. `scheduler.cpp` alone is 47k tokens. Read `scheduler.hpp` plus a `--compress` pack of `scheduler.cpp` first, then let Claude Code walk the function bodies you care about. For background, also attach `docs/deprecated/scheduler.md` and the formal problem statement. That file is a `.tex`, so it's ignored by the shared config; use plain repomix:
  `repomix --style markdown --include "docs/papers/scheduing-problem/volley_scheduling.tex" -o ~/volley-packs/04-scheduler-paper.md`
- **Tests** are ~45–50% of each big package. Read them in a separate pack, and only for packages you'll change.

**Prompt:** base prompt (07 §7.2) + task **P4** (07 §7.4).

**Alternative for this phase:** run Claude Code in the repo and ask it the same question. It will open only the files it needs and can follow references across packages.

---

## 6.5 Phase 5: Vertical slice (follow one feature end to end)

Goal: trace a **retrieval** (or whatever your first ticket touches) across packages. Use `rg` to pick the files, then pack exactly those.

```zsh
# [HOST]
# 1. Find candidate files (adjust terms after Phase 2 tells you real names)
rg -il "retriev" src controller_webview/action controller_webview/requests \
   -g '!**/test/**' > /tmp/slice.txt
rg -il "vda5050|order" src/agvhito src/vda5050 src/central -g '!**/test/**' >> /tmp/slice.txt
sort -u /tmp/slice.txt -o /tmp/slice.txt
wc -l /tmp/slice.txt            # prune by hand if > ~30 files

# 2. Pack exactly those
cat /tmp/slice.txt | repomix --stdin --remove-comments --output-show-line-numbers \
   -o ~/volley-packs/05-slice-retrieval.md
```
Line numbers let the LLM cite `file:line`, so you can jump there in your editor.

**Prompt:** base prompt (07 §7.2) + task **P5** (07 §7.4).

Repeat for: store/insert, EV charging stop, repark, system pause/stop.

---

## 6.6 Phase 6: History & context (why is it like this?)

```zsh
# [HOST]
PKG=src/planner/scheduler
rmx --include "$PKG/**" --compress --include-logs --include-logs-count 30 \
    -o ~/volley-packs/06-history-scheduler.md
```
Also useful before your first PR (packs your uncommitted changes plus context):
```zsh
# [HOST]
rmx --include "<files you touched>" --include-diffs -o ~/volley-packs/review.md
```

**Prompt:** base prompt (07 §7.2) + task **P6** (07 §7.4).

