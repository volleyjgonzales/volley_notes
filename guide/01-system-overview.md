# 01 · System overview

> Started from the directory tree and updated as files were read. **(verify)** marks inferences not yet confirmed.

## 1.1 What this system probably is

The file names describe the business pretty clearly: `bayConfirmInsert.php`, `reparkTray.php`, `overridePayloadOnTray.php`, `stopEvCharging.php`, `carJS3.3ds`, `stoplight.3ds`. This looks like an **automated robotic parking garage** with these pieces:

- A driver leaves a car in a **bay**.
- The car sits on a **tray**. The tray's payload is the vehicle (see `readme_payload_guid_bytes_to_vehicle_model_color.md`).
- **AGVs** (automated guided vehicles) move trays between **nodes** on a layout graph.
- **Lifts / VRCs** (VRC most likely means Vertical Reciprocating Conveyor, a freight lift) move trays between levels **(verify)**.
- A **central** scheduler/planner decides which AGV moves which tray and when. It also handles retrieval requests and EV charging.
- A web **NOC** (network operations center) UI shows system state and lets operators intervene (pause, override a pose, toggle nodes, and so on).

Read `docs/glossary.md` first. It will confirm or correct this vocabulary in about 10 minutes.

---

## 1.2 Tech stack at a glance

| Area | Evidence in tree | What it tells you |
|---|---|---|
| ROS 2 **Lyrical** + colcon, Python 3.14 | `package.xml`, `.colcon/`, `/opt/ros/lyrical` | Standard ROS 2 workspace: **37 colcon packages** in `src/` (`volley_cmake` builds first). colcon drives CMake + ninja, with sccache. |
| Task runner | `[tool.poe]` in `pyproject.toml` | **Poe the Poet**: `poe build`, `poe test`, `poe check`, ... The front door for daily commands (see 03 §3.7). |
| Environment | `.envrc`, `.envrc.local` | **direnv** sources ROS and the workspace overlay automatically (see 03 §3.5). |
| C++ **20** | `volley_package.cmake` enforces C++20; `-Wall -Wextra -Wpedantic`; clang-tidy (bugprone, cppcoreguidelines, clang-analyzer, google, modernize); `docs/guides/cpp-style.md` | Most of the core logic. RelWithDebInfo + asserts, mold linker, ASan in gtests (05 §5.9). Read the style guide early. |
| Custom CMake layer | `src/infrastructure/volley_cmake`, `docs/guides/volley-cmake.md`, `.gersemirc` | Every package uses in-house macros: `volley_package`, `volley_add_library`, `volley_add_component`, `volley_add_gtest`, `volley_ament_auto_package`. |
| Runtime model | 29 `RCLCPP_COMPONENTS_REGISTER_NODE`; launch files in `src/launcher/launch/` | Nodes are **composable components** loaded by launch files; no lifecycle nodes. Mostly single-threaded executors with mutually exclusive callback groups (05 §5.9). |
| Python | `uv.lock`, `pyproject.toml` (`requires-python >=3.14,<3.15`), `.pylintrc`, `setup.py` packages | Launch files, scenarios, system tests, tooling, sim metrics. Dependencies managed by **uv** in dependency groups (§1.2.2). |
| DDS discovery | `src/infrastructure/dds_discovery`, `scripts/set-discovery-server`, `scripts/set-domain-id` | Fast DDS Discovery Server and ROS domain isolation. This matters on a shared network. |
| State machines | `src/core/yasminx` | Extensions on YASMIN, a ROS 2 state-machine library. Expect FSMs in bay, AGV, and lift logic. |
| Fleet protocol | `src/vda5050/` | VDA 5050 is the standard AGV-to-fleet-manager interface (orders, states, map). |
| MQTT | `src/communication/mqtt`, `src/data/mqtt` | VDA 5050 runs over MQTT. Data/telemetry may also go out this way. |
| Observability | `src/data/otel` | OpenTelemetry instrumentation. |
| Web NOC | `controller_webview/` (PHP, jQuery, three.js, SleekDB) | Legacy-style operator UI with a 3D garage view. `docker/noc.Dockerfile` builds it. |
| Python API | `src/central_api` (+ `proxy`, `central_api_demo`) | External or programmatic API into central. |
| Docs | `mkdocs.yml`, `docs/` | MkDocs Material; `poe docs` serves a browsable site. |
| Quality tooling | `prek.toml` (Rust pre-commit), `.commitlintrc.yaml`, `.markdownlint-cli2.yaml`, `.yamllint`, `.taplo.toml`, `.shellcheckrc`, `.gcovr.cfg`, `.octocov.yaml` | Heavy lint and coverage gating. Expect conventional commits and branch-name rules (`scripts/check_branch_name.sh`). |
| Build cache | `.sccache.toml` | sccache for compiler caching, locally and in CI. |

### 1.2.1 Root config files

| File | Purpose |
|---|---|
| `pyproject.toml` | Python project metadata, uv dependency groups, black/mypy config, poe tasks |
| `uv.lock` | Pinned Python dependency versions |
| `prek.toml` | prek hooks (formatters and linters), run by `poe check` and on commit/push |
| `.colcon/defaults.yaml` | Default colcon flags (used via `COLCON_DEFAULTS_FILE`) |
| `.envrc` / `.envrc.local` | direnv environment: ROS sourcing / machine-specific settings |
| `.env.python` | Env file for the VS Code Python extension |
| `.sccache.toml` | Compiler cache config |
| `.gcovr.cfg` | Coverage report config |
| `.clang-format`, `.clang-tidy`, `.clangd` | C++ formatting, linting, language server |
| `.pylintrc` | Python linting |
| `.gersemirc` | CMake formatting |
| `.taplo.toml` | TOML formatting |
| `.yamllint`, `.markdownlint-cli2.yaml`, `.shellcheckrc` | YAML, Markdown, shell linting |
| `.editorconfig` | Basic editor settings |
| `.commitlintrc.yaml` | Commit message rules |
| `.octocov.yaml` | Coverage reporting in CI |
| `mkdocs.yml` | Documentation site config |

Formatting conventions: format-on-save is on in VS Code, with rulers at **110 columns for C++** and **88 for Python** (black).

### 1.2.2 Python dependency groups (`pyproject.toml`)

`dependencies` is empty; everything lives in `[dependency-groups]`, organized by purpose:

- **`runtime`**: what the running system uses. That's the Flask stack, numpy/scipy/pandas, shapely, boto3, database drivers, twilio, sendgrid and more, plus the `map-server` and `vda5050-interfaces` groups.
- **`dev`**: `runtime` + `docs` + `vda5050-interfaces-dev`, plus tooling (black, mypy, pylint, prek, gcovr, gersemi, yamllint, shellcheck, shfmt, colcon-clean, empy).
- **`docs`**: MkDocs packages.
- **`map-server`**: Flask, pydantic-settings, waitress.
- **`vda5050-interfaces`**: pydantic. Its dev group adds datamodel-code-generator and jinja2, probably to generate the VDA 5050 message models.

After editing dependencies, run `poe lock` (that's `uv lock`), which regenerates `uv.lock` without installing anything.

---

## 1.3 Package map (`src/`)

Grouped by layer, from bottom to top. The layering is now **verified with `colcon graph`**: 37 packages, `volley_cmake` first. 05 §5.3 has the full decoded graph and the analysis order derived from it.

**Size (tokei, `src tools controller_webview`):** ~93k lines of C++ (including headers) and ~25k of Python are the real logic. The 87k lines of JavaScript are mostly vendored libraries in the NOC, and the 42k lines of YAML are layouts, params and scenarios (data).

**Token reality check (repomix, 05 §5.2):**
- The repo is ~23M tokens unfiltered, and 71% of that is 3D meshes (`src/sim/3d/*.dae`).
- The NOC's own JavaScript is only `controller_webview/js/noc/` (~27k tokens); the rest is vendored three.js/draco/jQuery.
- The 29 "HCL" files are Terraform for the `central_api` demo/proxy and `data/mqtt`.
- The largest real-code packages are `central`, `common_ros`, `agvhito`, `bay`, `scheduler` and `motion_planner`, at ~60–120k tokens of implementation each, plus about as much again in tests.

**Documentation coverage (05 §5.1):** current prose is strongest for `bay`, `sim` and system tests. The core libraries (`stdx`, `rclcppx`, `otel`) and the planning chain have little or no documentation, so learn them from code.

**Foundation**
- `core/stdx` — C++ std-library extensions and utilities.
- `core/rclcppx` — rclcpp helpers (node wrappers, QoS, params, timers); 13 direct dependents.
- `core/yasminx` — state-machine helpers. Only `agvhito` uses it directly.
- `common`, `common_ros`, `common_py` — shared code. `common` is the most-used library (15 direct dependents) and `common_ros` the ROS-coupled layer (13). Note that `common_ros` depends on the Python `launcher` package, which is unusual; check `src/common_ros/package.xml`. `common_py` is the base of the Python chain.
- `structures` — domain data structures (layout graph, trays, nodes?), used by `bay`, `lift`, `vecs`, `sim`.
- `vecs` — most likely **EV charging control** (`vecs_evse_control.cpp`, `vecs_sim.cpp`; EVSE = electric vehicle supply equipment) **(verify)**. It's a leaf node package: it depends on `structures`, `common_ros` and `launcher`, and nothing depends on it. See its `README.md`.
- `infrastructure/volley_cmake` (used by 29 packages), `infrastructure/dds_discovery` (a leaf).

**Interfaces** (`interfaces/`)
- `agv_interfaces`, `bay_interfaces`, `vrc_interfaces`, `interfaces` — `.msg/.srv/.action` definitions. `interfaces` (which builds on `vrc_interfaces`) is the main contract, with 18 dependents. Skim these early.
- `vda5050/vda5050_interfaces`, `vda5050/map_server`.

**Planning / brains** (`planner/`)
- `planner_core` — shared planning types.
- `task_planner` — what needs doing (store/retrieve/repark/charge). It has no Volley deps except `volley_cmake` and only `scheduler` uses it, so it's a self-contained algorithm library.
- `motion_planner` — paths on the node graph for AGVs. The CI action `collision-table-cache` suggests precomputed AGV collision tables.
- `cost_functions` — pluggable costs for the planners.
- `scheduler` + `scheduler_advanced_tests` — assigns tasks and resources over time. It runs as its own `SchedulerComponent`. This is the deepest C++ stack: `planner_core` + `cost_functions` → `motion_planner` → `scheduler`. `docs/papers/scheduing-problem` likely gives the formal problem statement. This is probably the hardest and most interesting part of the codebase.
- `central` — the orchestrating components: **Dispatch, GarageTracker (MySQL persistence), AgvMonitor, GarageMonitor, ConsistencyMonitor, SafetyHardwareMonitor, MetricsRecorder, MqttBridge**. **Correction:** it does **not** depend on `scheduler` or any planner package. It uses `agv_interfaces`, `otel`, `interfaces` and `common_ros`. Central and planning most likely interact over ROS interfaces at runtime, so you can study them separately.

**Equipment / edge**
- `agvhito`, `agvhito_tools` — AGV-side driver/bridge. "Hito" appears to be the AGV model or vendor (the sim mesh is `hito_agv.dae`) **(verify)**. It has `launch/` and `config/`.
- `bay` — bay controller. `schemas/` suggests JSON/YAML config validation. `tools/BayPLCscript.py` implies PLC integration.
- `lift`, `vrc` — vertical transport. Both are **leaf** nodes; `vrc` doesn't even use `common_ros`.

**Sim / test / ops**
- `sim` — C++ simulator plus Python and 3D assets. It's a top-level package that depends on `central`, `bay`, `vis` and `system_tests`, so it composes the real nodes. See `docs/architecture/sim.md`.
- `sim_metrics` — KPI extraction from sim runs.
- `scenario` — scripted scenarios and batch configs.
- `system_tests` — end-to-end tests (`docs/architecture/system-tests.md`).
- `launcher` — the main entry point: `launch/`, `layouts/` (garage layouts), `params/`. Built from the Python chain `common_py` → `sim_metrics` → `scenario` → `launcher`; 12 packages depend on it.
- `vis` — visualization (RViz markers?).

**Outside `src/`**
- `tools/` — layout ↔ scenario/node-schedule converters, bag-file plan extraction, demo scripting, coverage builds, `local-runtime-deploy`.
- `controller_webview/` — the NOC. `action/*.php` are operator commands and `requests/*.php` are state polling. These map closely to the operator-facing capabilities of central, so they make a good feature inventory.

---

## 1.4 Suggested reading order (day 1–3)

1. `README.md`, then `.claude/CLAUDE.md`. The latter is written for an AI agent but usually holds the most compact and current summary of the build/test conventions.
2. `docs/index.md`, `docs/glossary.md`, `docs/guides/getting-started.md`.
3. `docs/architecture/*.md` in this order: `agv`, `bay`, `vrc`, `vda5050`, `discovery-server`, `sim`, `system-tests`, `docker-build`.
4. Skip `docs/deprecated/` for the mental model, but `deprecated/scheduler.md` and `tech-debt.md` are good "why is it like this" context.
5. `src/interfaces/**` — read every message definition once.
6. `src/launcher/launch` + one file in `layouts/` — this shows which nodes actually run together.
7. One vertical slice end to end. A good choice is a **retrieval**: NOC `actionRetrieve.php` → central / central_api → task_planner → scheduler → motion_planner → VDA 5050 order → agvhito → bay confirm (`bayConfirmRetrieve.php`).
8. `docs/guides/contributing.md`, `cpp-style.md`, `release-workflow.md` before your first PR.

**Tip:** generate a ROS graph from a running sim (`ros2 node list`, `ros2 topic list -t`, `rqt_graph`). It is the fastest way to check this map against reality.

