# 05 · Local reconnaissance (zero LLM tokens)

> **Role, revised after the first session:** recon is a planning tool for **you** (pack sizes, the ignore list, which docs are stale, high-care files). It is **not** uploaded to Claude. What Claude needs from it has been distilled into `stack-map.md` (layer table, build/runtime facts, components), which goes into Project knowledge. Learning happens bottom-up through the stack (09 §9.5).

Run everything here **before** any repomix pack (file 06). It costs no tokens, takes about 30–60 minutes, and produces two things:

1. Facts you'd otherwise pay an LLM to rediscover: build system, C++ standard, dependencies, entry points, memory and threading patterns.
2. The evidence you need to decide **what kind of Phase 1 to run** (§5.1). Is the documentation good enough to learn from, or do you have to learn from code metadata?

At the end, §5.7 bundles all of it into one small `artifacts/recon.md` "fact sheet" that you attach to your first LLM session together with the base prompt from file 07.

All commands run from `~/volley`. Most are **[HOST]** (git, rg, tokei); a few need the **[CONTAINER]** (colcon, compilers).

## 5.1 Docs inventory: is there enough documentation to learn from?

The answer to "does a docs-first Phase 1 make sense?" isn't known yet. Your tokei run only covered `src tools controller_webview`, where it found just 10 Markdown files (~400 lines). Most of the documentation lives in `docs/`, `.claude/` and the root README, so measure there:

```zsh
# [HOST]
cd ~/volley
tokei docs .claude README.md controller_webview/README.md src -t Markdown   # lines of prose by location
find . -name '*.md' -not -path './.git/*' -not -path './build/*' -not -path './install/*' -not -path './log/*' \
  -print0 | xargs -0 wc -w | sort -n | tail -40                               # biggest docs by word count
```

**Where the docs are, by section** (deprecated vs current matters):
```zsh
# [HOST]
for d in docs/architecture docs/guides docs/tips-and-tricks docs/deprecated docs/papers; do
  files=($d/**/*.md(N))
  printf "%-26s %6s words  (%d files)\n" "$d" "$( (( $#files )) && cat $files | wc -w || echo 0)" $#files
done
wc -w .claude/CLAUDE.md README.md docs/index.md docs/glossary.md
yq '.nav' mkdocs.yml 2>/dev/null || rg -n -A60 '^nav:' mkdocs.yml   # what the docs site actually exposes
```
`**/*.md(N)` is zsh: `**` recurses, and `(N)` means "no error if nothing matches".

> **Why the first version hung:** `docs/papers` contains no `.md` files, so the glob expanded to nothing and the command became a bare `cat`. With no file arguments, `cat` reads **stdin**, so it sat waiting for keyboard input. The fixed loop only calls `cat` when the file list is non-empty. Watch for this trap with any command that falls back to stdin: `cat`, `wc`, `xargs cat` (use `xargs -r`), and `git shortlog` (pass `HEAD`).

**Are they fresh?** Compare the last commit date of each doc with the code it describes:
```zsh
# [HOST]
for f in .claude/CLAUDE.md README.md docs/**/*.md(N) src/**/README.md(N); do
  printf "%s  %s\n" "$(git log -1 --format=%cs -- "$f")" "$f"
done | sort -r | head -50

for d in src/planner/scheduler src/central src/agvhito src/bay src/sim; do
  printf "%s  %s (code)\n" "$(git log -1 --format=%cs -- "$d")" "$d"
done
```

**Coverage: which packages are mentioned in the docs at all?**
```zsh
# [HOST]
for p in $(rg --no-filename -o '<name>([^<]+)</name>' -r '$1' -g package.xml src | sort -u); do
  printf "%-28s %3s docs\n" "$p" "$(rg -l -w "$p" docs .claude README.md 2>/dev/null | wc -l)"
done | sort -k2 -n
```
Packages with `0 docs` are code-only knowledge, so plan to learn them from Phase 3/4 packs.

**Decision rule for Phase 1.** Words × ~1.3 ≈ tokens.

| What you find | Phase 1 becomes |
|---|---|
| Current (non-deprecated) docs total more than ~10k words, `docs/architecture/*` changed within the last few months, and most core packages are mentioned | **1A. Docs-first pack** (06 §6.1): architecture + glossary + CLAUDE.md + selected guides |
| Docs thin, stale, or mostly in `deprecated/` | **1B. Metadata-first pack** (06 §6.1): `recon.md` + all `package.xml` + key `CMakeLists.txt` + launch files + the few current docs |
| Somewhere in between (the likely case) | Do **1B**, and add `.claude/CLAUDE.md`, `glossary.md` and the architecture docs that are fresher than their code |

Whatever the outcome, read `.claude/CLAUDE.md` yourself; it costs nothing. It turned out to be only **119 words**, so it's a pointer, not the dense summary I'd expected.

### Results from the first run (2026-10-06)

| Measure | Finding |
|---|---|
| Total | 42 Markdown files, ~40k words (≈52k tokens), and **half of it is `deprecated/`** (19.8k words) |
| Current docs | `architecture/` 10.9k words, `guides/` 4.8k, `tips-and-tricks/` 1.3k: **~17k words ≈ 22k tokens** |
| Entry docs | `CLAUDE.md` 119 words, `glossary.md` 88, `index.md` 60. All tiny, and last touched in April. |
| Fresh (Sept 2026, code also Sept/Oct) | `architecture/` sim, system-tests, docker-build, bay; `guides/` getting-started, simulation, cpp-style, volley-cmake |
| Possibly stale (doc older than its code) | `architecture/agv.md` (Jun) and `vda5050.md` (Apr) vs `src/agvhito` (Sep 29); `vrc.md` (Aug) |
| Biggest single docs | `deprecated/tech-debt.md` 6.6k words, `deprecated/central.md` 3k, `architecture/bay.md` 3k, `deprecated/aws.md` 2.9k |
| Undocumented packages | `stdx`, `rclcppx`, `otel`, `dds_discovery`, `map_server`, `agvhito_tools` (0 mentions) |
| Thinly documented | the planning chain: `cost_functions` 1, `planner_core` 2, `task_planner` 2, `motion_planner` 3 |
| Well documented | `central` 16, `bay` 15, `lift` 15, `scheduler` 12, `sim` 11. Much of the `central`/`scheduler` prose is in `deprecated/` though. |

**Decision: the in-between case → hybrid Phase 1** (06 §6.1). The bay, sim and system-tests docs are current and worth sending. The core libraries and the planning chain have to be learned from code. `deprecated/central.md` and `deprecated/scheduler.md` are the only long-form prose on those two subsystems, so save them for the Phase 4 deep dives, labeled "historical; verify against code". Keep them out of Phase 1.


## 5.2 Where do the lines and tokens live?
```zsh
# [HOST]
cd ~/volley
tokei src tools controller_webview --sort code      # or: cloc --vcs=git src tools controller_webview
repomix --token-count-tree 2000 -o /tmp/scratch.xml   # only show files/dirs ≥2000 tokens
```

**Measured (first run, `src tools controller_webview`):** 1,645 files, ~260k lines of code.

| Language | Code lines | What it probably is | Pack it? |
|---|---|---|---|
| JavaScript | 86.8k | Mostly **vendored libraries** in `controller_webview/js/` (jQuery, three.js, Chart, moment) | **No.** Already excluded in 06 §6.0. |
| C++ + headers | 77.7k + 15.7k ≈ **93k** | The core system | Compressed first, then package by package |
| YAML | 42.5k | Layouts, params, scenarios, configs: data, not logic | One representative sample only |
| Python | 24.6k | launcher, scenario, system_tests, central_api, sim_metrics, tools | Compressed, then by package |
| CMake | 2.1k (41 files) | Per-package builds on top of `volley_cmake` | Small; include with each package |
| PHP | 1.5k | NOC actions/requests | Small; good feature inventory |
| HCL (29), TeX (1), TypeScript (12), Templ, Forge Config | small | Unexpected outside `docker/`. Find them: `tokei -f -t HCL,TeX,TypeScript src tools` | Investigate, probably skip |
| "Autoconf" (1) | 357 | Almost certainly `src/vis/config/default.rviz.in`; tokei maps `.in` files to Autoconf | Skip |

**What this means for the token budget:** code costs very roughly 8–12 tokens per line. So the real logic (~118k lines of C++ and Python) is on the order of **1M+ tokens**, which you can never send in one go. That's why the plan goes docs → interfaces → compressed skeleton → one package at a time. `repomix --token-count-tree` gives you the real numbers; trust it over this estimate.

**Size per package** (C++ and Python only), to plan Phase 4 pack sizes:
```zsh
# [HOST]
for d in $(find src -name package.xml -printf '%h\n' | sort); do
  printf "%-40s %8s\n" "$d" "$(tokei "$d" -t 'C++,C++ Header,Python' -C | awk '$1=="Total"{print $4}')"
done | sort -k2 -nr
```
The apt-only equivalent uses cloc (the code column is the 5th CSV field of the last line):
```zsh
for d in $(find src -name package.xml -printf '%h\n' | sort); do
  printf "%-40s %8s\n" "$d" "$(cloc --quiet --csv --include-lang='C++,C/C++ Header,Python' "$d" | tail -1 | cut -d, -f5)"
done | sort -k2 -nr
```

Look out for big non-code files: vendored JS in `controller_webview/js/`, 3D assets, `SleekDB`, `uv.lock`, schemas, and the YAML layouts. They should be excluded from every pack (see 06 §6.0).

### Results from the first `--token-count-tree` run (2026-10-06)

The unfiltered repo is **~23M tokens**, and almost none of that is code you need to read:

| Where | Tokens | What it is | Action |
|---|---|---|---|
| `src/sim/3d/*.dae` | **16.3M** (71%) | Collada 3D meshes: cars, tray (3.9M alone), AGV, bay | Ignore (`**/*.dae`) |
| `controller_webview/js/**` | 4.76M | three.js, draco, ammo.js, jQuery… vendored; the NOC's own JS is just `js/noc/` (27k) | Ignore, except `js/noc/` if you work on the NOC |
| `docs/papers/…/IEEEtran.cls` + `.bib` | 96k | LaTeX class and bibliography | Ignore. Keep `volley_scheduling.tex` (5k): it's the formal scheduling problem, useful for the scheduler deep dive. |
| `src/sim/python/agv_simulation/documentation/main.tex` | 61k | AGV dynamics write-up (that's tokei's "TeX" file) | Skip unless you work on AGV dynamics |
| `src/launcher/layouts/*.yaml` | 199k | Site layouts (`kmart_nashville` 50k, `peachy_phase1` 41k) | Pack one small layout as an example |
| `src/scenario/scenarios/*.yaml` | 91k | Scenario data | Pack one as an example |
| `**/terraform/**` | ~12k | Terraform for the `central_api` demo/proxy and `data/mqtt`: these are the 29 "HCL" files | Ignore |
| `controller_webview/fonts`, `docs/assets/favicon.svg` | 68k | Fonts/assets | Ignore |

All of these are now in the shared ignore list (06 §6.0).

**Real code by package (tokens, from the tree; implementation = `include/` + `src/`):**

| Package | Impl | Tests | Note |
|---|---|---|---|
| `central` | ~119k | ~118k | Split for deep dives: dispatch/execution vs garage_tracker |
| `common_ros` | ~95k | ~103k | `discrete_garage_state.cpp` 17k |
| `agvhito` | ~90k | ~43k | sim/ and sm/ subfolders |
| `bay` | ~74k | ~66k | `bay_state_machine.hpp` 10k |
| `scheduler` | ~63k | ~58k | **`scheduler.cpp` is 47k tokens in one file** |
| `motion_planner` | ~60k | ~52k | SIPP / "chugg" planners |
| `common` | ~40k | ~19k | |
| `vis` | ~29k | — | |
| `central_api` | ~26k | — | Almost all in `rest_api.py` |
| `vecs` | ~23k | ~4k | EV charging (EVSE) control |
| `sim` (C++) / sim python | ~26k / ~54k | ~12k / ~24k | Python excludes the 61k `main.tex` |
| `interfaces` / `vda5050_interfaces` | 15k / 29k | | vda5050 includes 18k of JSON schemas |
| `planner_core` | ~14k | ~12k | `event_dag.hpp` |
| `vrc`, `lift`, `mqtt`, `structures`, `rclcppx`, `yasminx`, `volley_cmake`, `otel`, `task_planner`, `cost_functions` | 4–12k each | | Small, so pack these whole |
| `launcher` (minus layouts) | ~17k | ~2k | |

**Takeaways:**

- C++ implementation totals roughly **0.75M tokens**, plus about the same again in tests. **Tests are ~45–50% of every big package**, so the Phase 4 template excludes them by default.
- Every package except `central` and `common_ros` fits in one implementation pack of ≤90k tokens. Split those two.
- `scheduler.cpp` (47k) is best read with **Claude Code**, or compressed first (06 §6.4).
- The small foundation packages together are well under 60k tokens, so a single uncompressed pack is fine.

## 5.3 Package dependency graph
There are **37 colcon packages**; `volley_cmake` builds first. `colcon` lives in the container. Graphviz isn't in the image, and an `apt install` there is lost on rebuild, so export `.dot` files into `artifacts/` and render them on the host:
```zsh
# [CONTAINER]
cd ~/volley
colcon list --names-only | sort > "$ARTIFACTS_DIR/packages.txt"
colcon graph                                                    # text view: who depends on whom
colcon graph --dot > "$ARTIFACTS_DIR/pkg-graph.dot"
colcon graph --dot --dot-cluster > "$ARTIFACTS_DIR/pkg-graph-clustered.dot"     # grouped by folder
colcon graph --dot --packages-up-to central > "$ARTIFACTS_DIR/central-graph.dot"
```
```zsh
# [HOST]   (sudo apt install graphviz)
cd ~/volley/artifacts
tred pkg-graph.dot | dot -Tsvg -o ~/volley-packs/pkg-graph.svg      # tred drops redundant transitive edges
dot -Tsvg pkg-graph-clustered.dot -o ~/volley-packs/pkg-graph-clustered.svg
dot -Tsvg central-graph.dot -o ~/volley-packs/central-graph.svg
xdg-open ~/volley-packs/pkg-graph.svg
```
The graph covers only workspace packages, built from each `package.xml`; external ROS and system deps aren't drawn. It's a build-time view, unlike `rqt_graph`, which shows live nodes and topics.
### Reading `colcon graph` text output

Each row is one package, listed in **build (topological) order**: everything a package depends on appears above it. The columns to the right use that same order. On a package's row, `+` marks the package itself, and characters to its right show which **later** packages depend on it:

- `*` means a direct dependency.
- `.` means an indirect one, through something else.
- Blank means no dependency.

So a row with many `*`s is a widely used foundation, and a row with nothing after `+` is a **leaf**: nothing in the workspace depends on it.

### What Volley's graph says (decoded)

| Layer | Packages (build order) | Notes |
|---|---|---|
| 0. Build system | `volley_cmake` | Used directly by 29 of 36 packages. Read `docs/guides/volley-cmake.md`. |
| 1. Foundations | `common` (15 direct dependents), `rclcppx` (13), `stdx` (8), `structures` (4: bay, lift, vecs, sim) | Read these first: nearly everything is written in their vocabulary. |
| 1. Leaf libraries | `mqtt` (agvhito, agvhito_tools), `otel` (central only), `agv_interfaces` (agvhito, central), `task_planner` (scheduler only) | `task_planner` has **no** Volley deps besides `volley_cmake`, so it's a pure algorithm library and an easy, self-contained read. |
| 2. Contracts | `vrc_interfaces` → **`interfaces`** (18 dependents), `bay_interfaces`, `vda5050_interfaces` | `interfaces` is the main message contract. |
| 2. Small runtime pieces | `yasminx` (agvhito only), `dds_discovery` (leaf), `vrc` (leaf) | `vrc` is a standalone node with no dependents. |
| 3–6. Python orchestration chain | `common_py` → `sim_metrics` → `scenario` → **`launcher`**, plus `central_api` → `launcher`, and `map_server` (vda5050) → `agvhito` | `launcher` has 12 dependents, including C++ packages, probably for launch files and params used by tests **(verify)**. |
| 7. ROS glue | **`common_ros`** (13 dependents) | It depends on `launcher`, so it's built after the Python chain. |
| 8. Nodes / subsystems | `central`, `bay`, `lift`, `vecs`, `vis`, `agvhito`, plus planning libs `planner_core` and `cost_functions` | `lift` and `vecs` are leaves. |
| 9–10. Planning chain | `planner_core` + `cost_functions` → `motion_planner` → **`scheduler`** (pulls in `task_planner` too) | The deepest C++ stack in the repo. |
| 11. Top-level / integration | `sim` (depends on `central`, `bay`, `vis`, `system_tests`), `scheduler_advanced_tests`, `agvhito_tools` (depends on `agvhito` + `scheduler`) | `sim` composes the real nodes. |

**Two surprises worth noting in your notes:**

1. **`central` does not depend on `scheduler` or any planner package.** The planning stack and `central` probably talk over ROS interfaces at runtime rather than linking each other. You can study them independently; confirm in Phase 2/5.
2. **`common_ros` depends on `launcher`**, a C++ library on a Python package. That's unusual. Find out why (probably test or launch resources) by checking `src/common_ros/package.xml`.

**Analysis order derived from the graph.** This replaces the earlier guess.

1. **Foundations:** `volley_cmake` → `stdx`, `common`, `rclcppx` → `structures`. Compressed skeleton first; these are tiny relative to their reach.
2. **Contracts:** `vrc_interfaces`, `interfaces`, `bay_interfaces`, `agv_interfaces`, `vda5050_interfaces` (Phase 2).
3. **Entry point:** `launcher` (+ `common_py`), which tells you which nodes run together. Then `common_ros`.
4. **Planning chain, bottom-up:** `task_planner` → `planner_core` → `cost_functions` → `motion_planner` → `scheduler` → `scheduler_advanced_tests` (the tests show intended behavior).
5. **Orchestration:** `central` (+ `otel`, `central_api`).
6. **Equipment:** `agvhito` (+ `mqtt`, `yasminx`, `map_server`, `vda5050_interfaces`) → `bay` → `lift` → `vrc`.
7. **Integration:** `sim`, `vis`, `scenario`/`sim_metrics`, `system_tests`, `agvhito_tools`.
8. **Leftovers, as needed:** `vecs`, `dds_discovery`.

Each step only depends on what you've already read. When a pack references a type from an earlier layer, your notes will already explain it.

This is the single best architecture diagram you'll get for free. Leaf packages are foundations (stdx, structures); top packages are integration points (central, launcher).

## 5.4 Code fact sheet: answer the core C++ questions locally

These commands answer most of the "senior C++ engineer" questions (file 07) **without an LLM**. You then give the LLM the facts and ask it to *interpret* them, which is much cheaper than asking it to *discover* them.

### Build system and C++ standard
Known so far: ROS 2 / colcon, driving CMake + ninja, with in-house macros in `volley_cmake`. Pin down the details:
```zsh
# [HOST]
ls src/infrastructure/volley_cmake/**/*(.N)                             # what the macro package contains
rg -n 'CMAKE_CXX_STANDARD|cxx_std_[0-9]+|CXX_STANDARD' -g 'CMakeLists.txt' -g '*.cmake' src
rg -n -- '-W(all|extra|error|pedantic|conversion|shadow)|-fsanitize|-O[0-3s]' -g 'CMakeLists.txt' -g '*.cmake' src/infrastructure .colcon
cat .colcon/defaults.yaml; ls .colcon/mixin; cat .colcon/mixin/*.mixin   # build types, sanitizer/coverage mixins?
head -60 .clang-tidy                                                     # which checks are enforced = the team's safety rules
```
```zsh
# [CONTAINER]
g++ --version | head -1; clang++ --version 2>/dev/null | head -1; cmake --version | head -1; ninja --version
```

### How packages declare targets (the macro vocabulary)
```zsh
# [HOST]
rg --no-filename -o '^\s*([a-z_]+)\(' -r '$1' -g CMakeLists.txt src | sort | uniq -c | sort -rn | head -30
```
Anything frequent that isn't standard CMake (e.g. `volley_*` or `ament_auto_*`) is a macro to look up in `volley_cmake` or `docs/guides/volley-cmake.md`.

### Third-party dependencies
```zsh
# [HOST]
# workspace package names (to tell internal from external deps)
rg --no-filename -o '<name>([^<]+)</name>' -r '$1' -g package.xml src | sort -u > /tmp/ws-pkgs.txt
# every dependency declared in package.xml, with counts; external ones are the third-party set
rg --no-filename -o '<(?:build_|exec_|test_|build_export_)?depend>([^<]+)</' -r '$1' -g package.xml src \
  | sort | uniq -c | sort -rn | grep -v -w -F -f /tmp/ws-pkgs.txt | head -50
# CMake-level dependencies
rg --no-filename -o 'find_package\(\s*([A-Za-z0-9_]+)' -r '$1' -g CMakeLists.txt -g '*.cmake' src | sort | uniq -c | sort -rn
ls tools/third_party
```

### Entry points: what actually runs
```zsh
# [HOST]
rg -l 'int\s+main\s*\(' -t cpp src | sort                          # C++ executables
rg -n 'RCLCPP_COMPONENTS_REGISTER_NODE' -t cpp src                 # composable nodes
rg -n -A8 'console_scripts' -g setup.py src                        # Python executables
find src -name '*.launch.py' -o -name '*.launch.xml' -o -name '*.launch.yaml' | sort   # launch files
rg -l 'rclcpp_lifecycle|LifecycleNode' -t cpp src                  # managed (lifecycle) nodes?
```

### Memory management patterns
```zsh
# [HOST]
for pat in 'std::make_unique' 'std::unique_ptr' 'std::make_shared' 'std::shared_ptr' 'std::weak_ptr' \
           'shared_from_this' '\bnew\s+[A-Za-z_]' '\bdelete\s' 'std::pmr' 'Allocator' 'std::span' 'std::string_view'; do
  printf "%-22s %6s\n" "$pat" "$(rg -o -t cpp "$pat" src | wc -l)"
done
```
How to read this: a high `make_unique`/`unique_ptr` count with near-zero raw `new`/`delete` means modern RAII ownership. Lots of `shared_ptr` is normal in ROS 2, because node handles and message `SharedPtr`s use it. Any `weak_ptr`/`shared_from_this` points to callback-lifetime handling worth studying.

### Concurrency model
```zsh
# [HOST]
for pat in 'MultiThreadedExecutor' 'SingleThreadedExecutor' 'EventsExecutor' 'StaticSingleThreaded' \
           'create_callback_group' 'MutuallyExclusive' 'Reentrant' 'use_intra_process_comms' \
           'std::thread' 'std::jthread' 'std::async' 'std::mutex' 'std::shared_mutex' 'std::scoped_lock' \
           'std::lock_guard' 'std::unique_lock' 'std::atomic' 'condition_variable' 'create_wall_timer' 'create_timer'; do
  printf "%-26s %6s\n" "$pat" "$(rg -o -t cpp "$pat" src | wc -l)"
done
rg -l 'MultiThreadedExecutor|std::thread|std::jthread' -t cpp src     # where concurrency actually lives
```
How to read this: in ROS 2, **executors and callback groups are the threading model**. Single-threaded executors plus mutually exclusive groups mean callbacks never run concurrently. A multi-threaded executor, reentrant groups, or raw `std::thread` means shared state needs locks. The files from the last command are where data races could live, so read them carefully before you change anything there.

### Error handling and testing
```zsh
# [HOST]
for pat in '\bthrow\b' 'catch\s*\(' 'std::expected' 'tl::expected' 'std::optional' 'RCLCPP_(ERROR|FATAL)' 'assert\('; do
  printf "%-22s %6s\n" "$pat" "$(rg -o -t cpp "$pat" src | wc -l)"
done
rg -c -t cpp '\bTEST(_F|_P)?\s*\(' src | awk -F: '{s+=$2} END{print s" gtest cases"}'
rg -l 'gmock|GMock' -t cpp src | wc -l
rg -l '^def test_|^\s+def test_' -t py src | wc -l
ls src/*/test src/*/*/test 2>/dev/null | head
```

## 5.5 Make C++ navigable
```zsh
# [CONTAINER]
echo $ROS_DISTRO                                    # must be "lyrical" (direnv hooked; see 03 §3.5)
grep -n -i compile_commands .colcon/defaults.yaml   # probably already enabled
poe build                                           # colcon build with the repo defaults
direnv reload                                       # load the new install/ overlay
# only if the grep found nothing:
poe build --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```
Each package writes `build/<pkg>/compile_commands.json`, and the repo's `.clangd` tells clangd where to find them **(verify)**. Note that C++ IntelliSense is deliberately disabled in favor of clangd. Once the build has run, clangd gives you jump-to-definition and find-references across packages, which is often faster than asking an LLM.

## 5.6 History hotspots
```zsh
# [HOST]   (works in the container too; same repo)
cd ~/volley
git log --since="6 months ago" --name-only --pretty=format: -- src | \
  awk -F/ 'NF>2{print $2"/"$3}' | sort | uniq -c | sort -rn | head -25
git shortlog -sn --since="6 months ago" HEAD -- src/planner     # who to ask about the planner
```
Frequently changed packages are where you'll likely work first.

## 5.7 Bundle everything into `recon.md`

[`volley-recon.sh`](volley-recon.sh) runs the **[HOST]** commands from §5.1–§5.6 and writes a single Markdown fact sheet. Keep the script and its output in your notes repo (09 §9.2):

```zsh
# [HOST]
cd ~/volley && zsh ~/repos/volley_notes/guide/volley-recon.sh > ~/repos/volley_notes/recon.md
wc -w ~/repos/volley_notes/recon.md        # a few thousand words: cheap to keep in Project knowledge
```
Optional container-only facts: write them to `artifacts/` (the container can't see your host home), then append on the host:
```zsh
# [CONTAINER]
{ echo "## Toolchain (container)"; echo '```'; g++ --version | head -1; cmake --version | head -1;
  echo "ROS_DISTRO=$ROS_DISTRO"; echo '```'; echo "## colcon graph"; echo '```'; colcon graph; echo '```'; } > "$ARTIFACTS_DIR/recon-container.md"
```
```zsh
# [HOST]
cat ~/volley/artifacts/recon-container.md >> ~/repos/volley_notes/recon.md
```

`recon.md` goes into the Claude Project knowledge (09 §9.3). Re-run the script after big merges and replace it there.

## 5.8 Checkpoint: before you move on to file 06

You should now know:

- [x] whether Phase 1 is **1A (docs-first)** or **1B (metadata-first)** (§5.1): **hybrid**, decided 2026-10-06;
- [ ] the C++ standard, compilers, warnings, and the clang-tidy rules (§5.4);
- [ ] the third-party dependency list (§5.4);
- [ ] every executable, component and launch file (§5.4);
- [ ] roughly how ownership and threading are done, and **which files hold the concurrency** (§5.4);
- [ ] per-package sizes (§5.2) and the analysis order (§5.3);
- [ ] who owns what, and what's churning (§5.6).

## 5.9 What the first recon showed (commit `fdd205e6`, 2026-10-06)

**Build and toolchain** [seen]:

- C++20 is **enforced** by `volley_cmake/cmake/volley_package.cmake`; a package-level `CMAKE_CXX_STANDARD` is overridden with a warning.
- Warnings are `-Wall -Wextra -Wpedantic`.
- `volley_add_gtest` builds tests with **AddressSanitizer** (`-fsanitize=address`), possibly conditionally; check lines 80–90 of that file.
- `.colcon/defaults.yaml`: `symlink-install`, mixins `build-testing-on`, `compile-commands` (so clangd works out of the box), `mold` (fast linker), `ninja`, `rel-with-deb-info-assert` (optimized with asserts on), `sccache`.
- Macro vocabulary:
  - `volley_add_gtest` (129 uses), `volley_add_library` (36), `volley_package` / `volley_ament_auto_package` / `volley_add_component` (29 each), `volley_add_executable` (7);
  - so: **29 packages, each built as components**.
- clang-tidy enables `bugprone-*`, `cppcoreguidelines-*`, `clang-analyzer-*`, `google-*`, `modernize-*` and naming checks, with a documented list of exceptions (JIRA SW2-750).

**External dependencies** (beyond core ROS):

| Area | Packages |
|---|---|
| Parsing / config | yaml-cpp, nlohmann-json (+ JSON schema validator) |
| Math / geometry | Eigen, Boost |
| Messaging | Paho MQTT C++ (VDA 5050), Fast DDS |
| Persistence | MySQL Connector/C++ (`garage_tracker_mysql_io`) |
| Telemetry | OpenTelemetry |
| State machines | YASMIN (`yasminx` wraps it) |
| Safety / utilities | Microsoft GSL, fmt, backward_ros (stack traces), CLI parser (`cli`) |
| Tooling | rosbag2 (MCAP), foxglove_bridge |

**Runtime architecture: components, not executables.** 29 `RCLCPP_COMPONENTS_REGISTER_NODE` registrations, composed by launch files in `src/launcher/launch/` (`central`, `bay`, `lift`, `vecs`, `sim`, `bagplay`), plus `agvhito/launch/proxy.launch.py` and `vrc/launch/single.launch.py`. Almost every `main()` is a test. The real executables are `agvctl` and `listener` (agvhito_tools), `garage_tracker_recovery`, `discovery_probe`, `visualizer_node` and `geometry_visualization_tool`. There are **no lifecycle nodes**.

| Package | Components |
|---|---|
| central | Dispatch, GarageTracker, AgvMonitor, GarageMonitor, ConsistencyMonitor, SafetyHardwareMonitor, MetricsRecorder, MqttBridge |
| bay | StateMachine, BliftStateMachine, BayGuidance, VehicleEstimator, PlcControl, IoLinkDriver, LoadCellDriver, VrcLiftBridge |
| scheduler | SchedulerComponent: a **separate node from central** (confirms 05 §5.3) |
| agvhito | ProxyComponent, sim::SimAgvComponent |
| lift | LiftComponent, VCRControlComponent |
| vrc | RosNode |
| vecs | Vecs, evse::VecsEvse, io::VecsIo, sim::VecsSim (EV charging, real + sim) |
| sim | Simulator, SimClock, BaySim |

**Concurrency** [seen counts; interpretation inferred]:

- **Mostly single-threaded:** 9 `SingleThreadedExecutor` vs 1 `MultiThreadedExecutor`. 15 callback groups, all `MutuallyExclusive`, **0 `Reentrant`**. `use_intra_process_comms` appears in 4 places.
- ROS callbacks therefore **mostly don't run concurrently with each other**. The real thread-safety concerns are concentrated in the files that spawn their own threads: `bay/guidance_websocket_server`, `common/heartbeat_monitor`, `mqtt/client_impl`, `yasminx/root_state_machine`, `vrc/manager` and `agvhito_tools/agvctl`. These files hold most of the 50 `std::mutex`, 47 `std::atomic` and 13 `condition_variable` uses. **Treat them as high-care files.**
- Timers: `create_timer` 51 vs `create_wall_timer` 1. Timers follow the ROS clock, so they also run on **sim time** (`SimClockComponent`). Keep using `create_timer` in new code.

**Memory** [seen counts]:

- `make_shared` 847 / `shared_ptr` 367 (normal for ROS messages and nodes); `make_unique` 297 / `unique_ptr` 161; `weak_ptr` 13; `shared_from_this` 9; `string_view` 146; no `std::pmr` or `std::span`.
- The **210 raw `new`** count over-counts, because the regex also matches comments like "create new order". Check the real ones: `rg -n '\bnew\s+[A-Z][A-Za-z_:<>]*\s*[({]' -t cpp src -g '!**/test/**'`.

**Errors and tests:**

- Error style is **`std::optional` returns** (552), with exceptions also in use (149 `throw`, 98 `catch`); `tl::expected` appears only twice. Find out which convention applies where. A `throw` that escapes a ROS callback kills the component container (RISK).
- Tests: **1,215 gtest cases and 180 pytest functions.**

**Activity:**

- Hotspots: `system_tests`, `scenario/scenarios`, `agvhito`, `interfaces`, `motion_planner`.
- Paths like `scheduler/motion_planner`, `scheduler/core` and `agv/agv` show **directories were moved within the last 6 months** (the planner used to live under `src/scheduler`). Use `git log --follow` when tracing history.
- Most active contributors: Dan Ambrosio, Paula Van Camp, Justin Abel, Paul. They're the people to ask.

**Docs:** README is 22 words, CLAUDE.md 119, glossary 88 (see §5.1 results).

