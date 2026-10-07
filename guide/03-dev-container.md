# 03 · The dev container

How the container is built and started, and how to work inside it. It assumes the host setup in file 02 is done.


> Based on `.devcontainer/devcontainer.json`, `initialize.sh` and `post-create.sh`. `post-attach.sh`, `utils.sh`, `docker-bake.hcl` and the Dockerfile weren't reviewed yet. Items that depend on them are marked **(verify)**.

Each command block below starts with a tag that says where to run it:

- **[HOST]** means your laptop's zsh terminal, outside Docker.
- **[CONTAINER]** means a terminal inside the dev container (any VS Code terminal once you're attached).

## 3.1 The mental model

The dev image isn't pulled ready-made. Every time you open the container, **your laptop builds it locally** on top of a team base image from the company's private AWS ECR registry (so your host Docker must be logged in to ECR; see 02 §2.3). It builds with `docker buildx bake ... user-develop` and tags it `volley:user-develop-local`. The image is built with **your UID/GID** baked in, so files you create inside the container are owned by you on the host.

The lifecycle when you click *Reopen in Container* in VS Code, or run `devcontainer up` in a terminal (it's identical either way):

```
[HOST]       initializeCommand  → .devcontainer/scripts/initialize.sh   (every open)
[DOCKER]     create container from volley:user-develop-local
[CONTAINER]  postCreateCommand  → .devcontainer/scripts/post-create.sh  (first time the container is created)
[CONTAINER]  postAttachCommand  → .devcontainer/scripts/post-attach.sh  (every attach)
```

Because `initialize.sh` deletes any existing `volley-user-develop` container each time, **the container is disposable**. Only three things persist:

| What | Where it lives | Survives container rebuild? |
|---|---|---|
| The repo (`~/volley`) | Bind mount; **same path** inside and outside | Yes (it's your host folder) |
| Your container home dir (`~`) | Docker volume `volley-home` | Yes, but it is **not** your host home |
| Git hooks (`.git/hooks`) | Docker volume `volley-git-hooks`, container-only, so hooks **don't run for commits made on the host** | Yes |
| `apt install`s, edits to `/opt`, etc. | Container filesystem | **No**. Ask to add them to the Dockerfile. |

What the `runArgs` mean:

| Flag | Why it's there |
|---|---|
| `--network=host` | The container shares your laptop's network stack. ROS 2/DDS discovery, MQTT and Tailscale all "just work", but your nodes are visible to anyone on the same LAN with the same `ROS_DOMAIN_ID` (see §3.8). |
| `--ipc=host` | DDS shared-memory transport between processes uses the host's IPC namespace and `/dev/shm`. |
| `--shm-size=4G` | Probably has **no effect** combined with `--ipc=host`, since the host's `/dev/shm` is used. |
| `--privileged` | Access to host devices (USB/serial to PLCs and hardware, `/dev/dri`). Convenient for robotics; treat the container as having root on your machine. |
| `--tmpfs=/tmp:exec` | Fast, clean `/tmp` on every start. |
| X11 socket + `DISPLAY` | GUI apps (RViz, rqt) render on your host screen. |
| `/var/run/dbus` | Exposes the host's system D-Bus, which some GUI and system tools expect. |
| `~/.ssh` (read-only) | Your SSH keys work for `git push/pull` inside the container. |

Notable env vars set for you: `COLCON_DEFAULTS_FILE` (so a bare `colcon build` uses the repo's flags), `SCCACHE_CONF` (compiler cache), `ARTIFACTS_DIR` (`~/volley/artifacts`, a handy bind-mounted drop zone), `SHELL` (copied from the host, so it will be your zsh path, see §3.5), and `VOLLEY_WS` (the workspace path).

**Where am I?** With `--network=host`, the container shares your laptop's hostname, so the prompt looks identical on both sides. Check with `ls /.dockerenv && echo "in container"`.

The ROS distro is **ROS 2 Lyrical** on **Python 3.14** (from the `/opt/ros/lyrical/...` paths in the VS Code settings). There is **no `--gpus` flag**, so the NVIDIA dGPU is not passed through. RViz will use the iGPU via `--privileged`/`/dev/dri` or software rendering. That's fine on day 1; ignore my earlier NVIDIA Container Toolkit note until someone says you need it.

## 3.2 Docker primer: the commands in `initialize.sh`, explained

### `docker build` vs `docker buildx` vs `docker buildx bake`

- **BuildKit** is Docker's modern build engine. It runs independent Dockerfile stages in parallel, caches better, supports cache mounts (`RUN --mount=type=cache`), and passes secrets and SSH keys into builds without baking them into layers.
- **`docker buildx`** is the Docker CLI plugin that exposes all of BuildKit's features. On current Docker Engine (23.0+), **plain `docker build` is already an alias for `docker buildx build`**, so for a single image the two do the same thing. buildx adds the features `build` doesn't have:
  - multi-platform images (`--platform linux/amd64,linux/arm64`);
  - pluggable *builders* (`docker buildx ls`, `docker buildx create`), e.g. a builder running in a container or on a remote machine;
  - exporting and importing cache to and from a registry or GitHub Actions (that's how CI stays fast);
  - **`bake`**.
- **`docker buildx bake`** is to `docker build` what `make` is to `gcc`. Instead of a long command line, you describe **targets** in a file (`docker/docker-bake.hcl`). Each target has its Dockerfile, stage, build args, tags, cache settings, and so on. Targets can inherit from each other and be grouped, and you build one by name. One file then serves every image (dev, runtime, NOC, CI variants) in one place, with shared settings.

### The build line, piece by piece

```bash
export COMMIT_SHA REGISTRY TAG USER_GID USER_UID
docker buildx bake --allow=network.host -f docker/docker-bake.hcl user-develop
```

| Part | Meaning |
|---|---|
| `export ...` | HCL `variable "TAG" {}` blocks in a bake file are filled **from environment variables with the same name**. Exporting them is how the script passes your UID/GID (so the image user matches you), the git SHA (labels/version info), and the image name and tag in. `REGISTRY`/`TAG` come from `utils.sh`; the result is `volley:user-develop-local` **(verify in utils.sh)**. |
| `-f docker/docker-bake.hcl` | Which bake file to read. CI uses `docker-bake.ci.hcl` on top of it. |
| `user-develop` | The **target** to build: the developer image, as opposed to runtime/NOC/CI targets. |
| `--allow=network.host` | An **entitlement**, i.e. explicit permission for a privileged build feature. The target almost certainly sets `network = "host"`, so `RUN` steps use your host's network, including Tailscale. That's how the build reaches internal hosts such as the apt proxy. Recent buildx versions refuse privileged features unless you grant them like this. If you get `unknown flag: --allow`, your buildx is too old: `sudo apt install --only-upgrade docker-buildx-plugin`. |

Useful exploration commands, all **[HOST]**:
```bash
docker buildx version                                        # plugin installed? version?
docker buildx ls                                             # available builders
docker buildx bake -f docker/docker-bake.hcl --print user-develop   # resolved target as JSON: Dockerfile, stage, args, tags. Builds nothing.
docker buildx bake -f docker/docker-bake.hcl --list=targets  # every target in the file (newer buildx)
docker buildx du                                             # build-cache disk usage
```
`--print` is the best way to understand the image without reading HCL first.

### The other Docker commands in the script

| Command | What it does |
|---|---|
| `docker volume inspect volley-home` | Succeeds only if the named volume exists, so it's used as an "already initialized?" check. |
| `docker volume create volley-home` | Creates a **named volume**: Docker-managed storage (under `/var/lib/docker/volumes`) that outlives any container. |
| `docker run --rm --volume volley-home:/home/$USER <image> sudo chown UID:GID /home/$USER` | Starts a throwaway container (`--rm` deletes it on exit) with the volume mounted, fixes ownership, and exits. This is the standard trick for running one command against a volume. |
| `docker run --rm ... cat <hashfile> \| sha256sum --check` | Same trick, reading a file from the volume to see whether `devcontainer.json` changed. |
| `docker ps -aq -f name="^/volley-user-develop$"` | Lists IDs (`-q`) of **all** containers, including stopped ones (`-a`), whose name matches the regex. Docker stores names with a leading `/`, hence `^/…$`. |
| `docker rm -f volley-user-develop` | Force-removes the container, stopping it first if needed. |
| `xhost +local:docker` | Not Docker: tells your X server to accept connections from local non-network clients, which is how container GUIs reach your screen. |

### Image vs container vs volume (vocabulary)

- **Image** (`volley:user-develop-local`): read-only filesystem plus metadata. Listed with `docker images`.
- **Container** (`volley-user-develop`): a running (or stopped) instance of an image with a thin writable layer. Listed with `docker ps -a`. Throwaway here.
- **Volume** (`volley-home`, `volley-git-hooks`): persistent storage mounted into containers. Listed with `docker volume ls`.
- **Bind mount** (`~/volley`, `~/.ssh`): a host directory mapped straight into the container.

## 3.3 Option A: first launch with VS Code

```bash
# [HOST]
cd ~/volley
code .
```
In VS Code, open the Command Palette (`Ctrl+Shift+P`) → **Dev Containers: Reopen in Container**. Click "show log" in the bottom-right toast to watch progress.

What `initialize.sh` is doing (on the host), in order:

1. **Tailscale check.** It fails fast if you're not on the tailnet.
2. **`build_image`.** Runs `docker buildx bake -f docker/docker-bake.hcl user-develop` with your UID/GID and the current commit SHA. The first run takes a while (ROS + deps); afterwards it's mostly cached, but it re-runs on **every** open, so Dockerfile changes you pull get picked up automatically.
3. **`initialize_home_volume`.** Creates the `volley-home` volume once and `chown`s it to you. This works around a VS Code bug where a fresh volume is root-owned.
4. **`sync_devcontainer_config`.** If `devcontainer.json` changed since last time (it compares a sha256 stored in the volume), it wipes `~/.vscode-server` so the extensions and settings are reinstalled cleanly.
5. **`remove_existing_container`.** Deletes the old `volley-user-develop` container so a fresh one is created.
6. **`allow_x11_access`.** Runs `xhost +local:docker`.

Then, on first creation, `post-create.sh` runs inside the container (the same happens with the CLI in §3.4):

1. **`fix_volume_permissions`.** `chown`s the git-hooks volume to you.
2. **`hash_devcontainer_config`.** Stores the sha256 that step 4 above compares against.
3. **`prek_hook_install`.** Installs pre-commit, **commit-msg** (commitlint) and **pre-push** hooks. Expect commits to be linted and pushes to run checks.
4. **`sync_rosdep` / `sync_colcon_mixins`.** Copies the rosdep cache and colcon mixins baked into the image (under `/root`) into your home, so nothing is re-downloaded on start.
5. **`sync_direnv`.** Writes a direnv config that **auto-trusts** the workspace, so `.envrc` loads by itself whenever you `cd ~/volley`.
6. **`maybe_install_rviz_config`.** Seeds `~/.rviz2/default.rviz` from `src/vis/config/default.rviz.in`.
7. **`maybe_set_domain_id`.** If your local envrc (probably `.envrc.local`, **verify** in `scripts/util_path.sh`) sets neither `ROS_DOMAIN_ID` nor `ROS_DISCOVERY_SERVER`, it writes `ROS_DOMAIN_ID=101`.

## 3.4 Option B: terminal only (no VS Code)

**You don't have to use VS Code.** `devcontainer.json` is an open spec, and the **Dev Containers CLI** runs the same lifecycle (`initializeCommand` → create → `postCreateCommand` → `postAttachCommand`), resolving the same `${localWorkspaceFolder}`-style variables. You get the same container as VS Code users, which keeps you in sync with the team.

**One-time install [HOST]** (needs Node; see 02 §2.8):
```zsh
npm install -g @devcontainers/cli
devcontainer --version
```

**Start the environment [HOST]:**
```zsh
cd ~/volley
devcontainer up --workspace-folder .
```
This runs `initialize.sh` on the host (Tailscale check, `buildx bake`, volume setup, removal of any old container, `xhost`). It then creates the container with the `runArgs`/mounts/env from `devcontainer.json`, and runs `post-create.sh` and `post-attach.sh` inside it. When it finishes, it prints JSON with `"outcome": "success"`.

**Get a shell [HOST]** (repeat in as many terminals or tmux panes as you like):
```zsh
devcontainer exec --workspace-folder ~/volley zsh     # or bash, if the image has no zsh
```
or, equivalently, with plain Docker:
```zsh
docker exec -it -w ~/volley volley-user-develop zsh
```
`devcontainer exec` is slightly nicer: it uses `remoteUser` and the container environment exactly as the spec defines them.

⚠️ **Run `up` once per session, then use `exec`.** Because `initialize.sh` deletes the existing container each time, running `devcontainer up` again **kills every open container shell and running process** (sims, builds). Use it only when you actually want a fresh container.

**Handy aliases for `~/.zshrc` [HOST]:**
```zsh
alias vup='devcontainer up --workspace-folder ~/volley'
alias vsh='devcontainer exec --workspace-folder ~/volley zsh'
alias vstop='docker stop volley-user-develop'
```

**A typical terminal-only morning:**
```zsh
# [HOST]
sudo tailscale up            # only if not connected
ecr-login                    # ECR token, see 02 §2.3
vup                          # build/refresh image + fresh container (~seconds when cached)
vsh                          # shell #1: build
# [CONTAINER]
poe build-pkg central        # = colcon build --packages-up-to central
```
```zsh
# [HOST], new terminal/pane
vsh                          # shell #2: run sim / ros2 CLI / rviz2
```

**Editing code without VS Code.** The repo is a bind mount, so you can edit files with any editor **on the host** and build in the container. The catch is C++ language features: clangd needs the container's toolchain, ROS headers and `compile_commands.json`, whose paths only exist inside the container. Your options:

- Run your editor **inside** the container (e.g. install Neovim there; your config persists in the `volley-home` volume).
- Edit on the host and accept weaker C++ navigation; use `rg` for search.
- Any IDE with Dev Containers support (JetBrains Gateway, Neovim plugins) reads the same `devcontainer.json`.

Claude Code also runs fine as a CLI inside the container instead of the VS Code extension.

**What you lose without VS Code:** the auto-installed extensions and settings (clangd wiring, formatters on save, the yamllint/gersemi helpers). The `prek` git hooks still run on commit and push either way, so formatting and lint are still enforced.

**Fallback: raw Docker with no CLI.** Not recommended, because you'd have to keep it in sync with `devcontainer.json` by hand. It shows what the CLI does for you:
```zsh
# [HOST]
cd ~/volley
.devcontainer/scripts/initialize.sh                 # build image, volumes, cleanup, xhost
WS=$PWD
docker run -d --name volley-user-develop \
  --ipc=host --network=host --privileged --shm-size=4G --tmpfs=/tmp:exec,mode=777 \
  -e ARTIFACTS_DIR=$WS/artifacts -e COLCON_DEFAULTS_FILE=$WS/.colcon/defaults.yaml \
  -e DISPLAY=$DISPLAY -e NO_MKDOCS_2_WARNING=true -e SCCACHE_CONF=$WS/.sccache.toml \
  -e SHELL=$SHELL -e VOLLEY_WS=$WS \
  --mount type=bind,source=$HOME/.ssh,target=$HOME/.ssh,readonly \
  --mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix \
  --mount type=bind,source=/var/run/dbus,target=/var/run/dbus \
  --mount type=volume,source=volley-git-hooks,target=$WS/.git/hooks \
  --mount type=volume,source=volley-home,target=$HOME \
  --mount type=bind,source=$WS,target=$WS \
  -w $WS \
  volley:user-develop-local sleep infinity          # keep-alive, like the CLI does
docker exec -it -u $USER -w $WS volley-user-develop .devcontainer/scripts/post-create.sh   # first time only
docker exec -it -u $USER -w $WS volley-user-develop .devcontainer/scripts/post-attach.sh
docker exec -it -u $USER -w $WS volley-user-develop zsh
```
Each `docker run` flag maps one-to-one to `runArgs`, `containerEnv` and `mounts` in `devcontainer.json`. That's a good way to read that file.

## 3.5 First-time container shell setup (zsh + direnv). Do this before building.

**What's going on:** the image ships zsh but **no oh-my-zsh**, and your container home (`volley-home` volume) starts **empty**, with no `~/.zshrc`. With no `~/.zshrc`, direnv isn't hooked into the shell. ROS then never gets sourced, and the first build fails with `Could not find a package configuration file provided by "ament_cmake_auto"` (see §3.15).

Create `~/.zshrc` **in the container**. It lives in the volume, so you only do this once:
```zsh
# [CONTAINER]  ~/.zshrc
# poe shell completions
fpath=(~/.zfunc $fpath)
mkdir -p ~/.zfunc
poe _zsh_completion >~/.zfunc/_poe 2>/dev/null

# Enable zsh's completion system (must come after fpath is set)
autoload -Uz compinit && compinit

# direnv: auto-load .envrc (ROS sourcing, local settings)
eval "$(direnv hook zsh)"
```
Then:
```zsh
# [CONTAINER]
rm -f ~/.zcompdump*     # drop stale completion cache
exec zsh
cd ~/volley
direnv allow            # post-create already whitelists the workspace, so this may be a no-op
echo $ROS_DISTRO        # must print: lyrical
```

What each part does:

- `fpath` is zsh's search path for functions. Adding `~/.zfunc` lets zsh find the generated `_poe` completion file.
- `compinit` turns on zsh's completion system, and it must run **after** `fpath` is set.
- `2>/dev/null` hides errors. That means that if `poe` isn't on `PATH`, completions fail silently. Check with `which poe` and `ls -la ~/.zfunc/_poe`.

**Want oh-my-zsh in the container too?** Install it inside the container; it persists in the volume. Put the `fpath=(...)` lines **before** `source $ZSH/oh-my-zsh.sh` (oh-my-zsh runs `compinit` itself, so drop your own `compinit` line). Put the direnv hook **after** it.

### How direnv works here

direnv sets and unsets environment variables based on the current directory. Its hook runs before every prompt. It finds the nearest `.envrc`, runs it in a **bash** subprocess, and applies the resulting environment changes to your shell. When you leave the directory, the changes are reverted.

- **`.envrc`** (committed) sources the ROS 2 underlay `/opt/ros/lyrical`, so CMake finds ROS packages through `CMAKE_PREFIX_PATH`. **Once `install/` exists**, it also sources the workspace overlay, so `ros2 run` finds Volley's packages. You don't need to `source install/setup.zsh` by hand.
- **`.envrc.local`** (machine-specific, not committed) holds things like `ROS_DOMAIN_ID` and `ROS_DISCOVERY_SERVER`. `post-create.sh` seeds it, and the poe tasks in §3.8 edit it.

Gotchas:

- `.envrc` is always bash, whatever your shell.
- **Only environment variables carry over.** Shell functions, aliases and completions don't, so `ros2` tab completion isn't set up by direnv. To get it, add this to `~/.zshrc` **(verify the path)**:
  `[[ -f /opt/ros/lyrical/share/ros2cli/environment/ros2-argcomplete.zsh ]] && source /opt/ros/lyrical/share/ros2cli/environment/ros2-argcomplete.zsh`
- A new or changed `.envrc` needs `direnv allow`.
- **After the first successful build, run `direnv reload`** (or `cd` out and back in) so the overlay gets picked up.

## 3.6 Sanity checks

```zsh
# [CONTAINER]
ls /.dockerenv && echo "in container"   # host and container share a hostname (--network=host), so the prompt looks the same
whoami && id                     # same user/UID as on the host
pwd                              # /home/jon-gonzales/volley, the same path as on the host
echo $ROS_DISTRO                 # lyrical
direnv status | head -5          # .envrc found and allowed
env | grep -E 'ROS_|COLCON_|SCCACHE'
which poe prek                   # both on PATH
poe                              # lists every project task
```

## 3.7 Poe the Poet: the project's command menu

**What it is:** a task runner. It gives the project named commands that you run as `poe <task>`, like `npm run` scripts or Makefile targets. All tasks are defined in `pyproject.toml` under `[tool.poe]`.

- `poe` on its own lists every task with its help text.
- `poe <task> --help` shows a task's arguments.

`executor.type = "simple"` means poe does **not** create or sync a uv `.venv`. Tasks run directly in the container's environment, the ROS Python 3.14 plus whatever the image installed. **Prefer `poe` over raw commands**, since it encodes the team's flags. The raw commands are shown below so you know what's happening underneath.

| Task | Runs | Use it for |
|---|---|---|
| `poe build` | `colcon build` | Build the whole workspace. Extra args are forwarded to colcon. |
| `poe build-pkg <pkg>` | `colcon build --packages-up-to <pkg>` | One package plus everything it depends on (day-to-day). |
| `poe test` | `colcon test` then `colcon test-result --verbose` | All tests, with a readable summary. |
| `poe test-pkg <pkg>` | same, `--packages-up-to <pkg>` | Test one package plus its deps. |
| `poe coverage` | build with `--mixin coverage-gcc`, test, gcovr | HTML report at `coverage/index.html`. The next normal build recompiles everything. |
| `poe check` | `prek run --show-diff-on-failure --all-files` | Every formatter and linter on every file. **Run before pushing.** |
| `poe clean` / `poe clean-yes` | `colcon clean workspace` | Delete `build/`, `install/`, `log/` (with or without a prompt). |
| `poe clean-pkg <pkg>` | `colcon clean packages --packages-select <pkg>` | Clean just that package. |
| `poe docs` | `mkdocs serve --livereload` | Docs at http://127.0.0.1:8000, which opens in your **host** browser thanks to `--network=host`. |
| `poe lock` | `uv lock` | Regenerate `uv.lock` after editing dependencies. Installs nothing. |
| `poe sccache-stats` / `sccache-zero` / `sccache-clear` | sccache cmds / `rm -r ~/.cache/sccache` | Inspect, reset counters, or wipe the compiler cache. |
| `poe domain-id <id>` | `scripts/set-domain-id` | Set your `ROS_DOMAIN_ID` (§3.8). |
| `poe discovery-server <IP:PORT>` | `scripts/set-discovery-server` | Use a Fast DDS discovery server instead of multicast discovery. |

**`--packages-up-to` vs `--packages-select`:**

- `--packages-up-to <pkg>` builds the package **and its dependencies**, so everything it relies on is current. That's why building uses it.
- `--packages-select <pkg>` touches **only** that package. That's why cleaning uses it: it avoids needless rebuilds of dependencies.

**Reading the TOML.** These two forms produce identical data:
- a task under its own header, `[tool.poe.tasks.build-pkg]`;
- an inline table, `build-pkg = { ... }`, under `[tool.poe.tasks]`.

Simple tasks use inline tables; tasks with `args` or several steps get their own header. Every `key = value` line belongs to the most recent header above it, so **inline tasks must come before the first `[tool.poe.tasks.<name>]` header**.

Inside a task:
- `${pkg}` is replaced by the argument named `pkg`.
- `positional = true` lets you write `poe build-pkg my_pkg` instead of `--pkg my_pkg`.
- `required = true` makes poe error out if the argument is missing.
- `cmd` tasks run without a shell, so no pipes or `&&`; `shell` tasks run through one.
- Tasks that declare `args` generally don't forward extra flags.

## 3.8 Pick your own ROS_DOMAIN_ID (do this on day 1)

Because of `--network=host`, everyone whose container defaulted to `101` on the same office network sees everyone else's nodes and topics. That makes sims interfere with each other in confusing ways.

```zsh
# [CONTAINER]
poe domain-id <your-number>          # or: poe discovery-server <IP:PORT>
direnv reload
echo $ROS_DOMAIN_ID
cat .envrc.local                     # the scripts most likely write here (verify)
```
A task can't change the environment of the shell that called it. That's why these scripts write to `.envrc.local` and direnv applies the change. Ask whether the team keeps a domain-ID allocation list, and when to use the discovery server instead (`docs/architecture/discovery-server.md`). If `ROS_DISCOVERY_SERVER` is set, `post-create.sh` skips its domain-ID default.

## 3.9 Build

```zsh
# [CONTAINER]
cat .colcon/defaults.yaml            # what a bare colcon build actually does
poe build                            # full workspace: 37 packages, volley_cmake first. Slow the first time.
direnv reload                        # pick up the new install/ overlay
poe build-pkg central                # day-to-day: just what you need
poe sccache-stats                    # confirm the compiler cache is hitting
```
`COLCON_DEFAULTS_FILE` and `SCCACHE_CONF` are already set, so you never pass those flags by hand. The cache lives in `~/.cache/sccache`, inside the home volume, so it survives container rebuilds.

**Where the build output goes.** All of it is gitignored and visible from the host.

| Path | Contents |
|---|---|
| `build/<pkg>/` | Intermediate files: CMake cache, objects, generated code, test results, and `compile_commands.json` (what clangd uses) |
| `install/` | Finished products plus the overlay setup scripts that `.envrc` sources |
| `log/latest_build/<pkg>/` | Full build output per package. **Look here when a build fails.** |
| `coverage/` | `poe coverage` HTML report |
| `artifacts/` | `$ARTIFACTS_DIR`. What writes here isn't known yet: `grep -rn ARTIFACTS_DIR scripts tools src .github` |

`poe clean` deletes `build/`, `install/` and `log/`.

**Package dependency graph.** This shows the 37 workspace packages from their `package.xml` files. External ROS and system deps aren't drawn, and it's different from `rqt_graph`, which shows live nodes and topics.
```zsh
# [CONTAINER]
colcon graph                                                          # text view
colcon graph --dot | tred | dot -Tsvg -o artifacts/package-graph.svg  # tred drops redundant transitive edges
colcon graph --dot --packages-up-to central | dot -Tsvg -o artifacts/central-graph.svg
colcon graph --dot --dot-cluster | dot -Tsvg -o artifacts/package-graph-clustered.svg   # grouped by folder
```
This needs Graphviz (`which dot`). An `apt install graphviz` in the container is lost on rebuild. Alternatives: render on the host (`colcon graph --dot > artifacts/pkg.dot` in the container, then `dot -Tsvg` on the host), or ask for Graphviz to be added to the image. A possible poe task, which must go in the **inline** section of `[tool.poe.tasks]`:
```toml
graph = { help = "Render package dependency graph to artifacts/package-graph.svg", shell = "colcon graph --dot | tred | dot -Tsvg -o artifacts/package-graph.svg" }
```

## 3.10 Test, coverage, lint

```zsh
# [CONTAINER]
poe test-pkg <pkg>                   # one package plus its deps
poe test                             # everything (slow)
poe coverage                         # then open coverage/index.html on the host
poe check                            # all prek hooks on all files, before pushing
```
System and scenario tests are heavier; see `docs/architecture/system-tests.md`.

**Commit from inside the container.** The `volley-git-hooks` volume is mounted over `.git/hooks`. The prek hooks (pre-commit, commit-msg/commitlint, pre-push) exist **only in the container**, so commits made from a host terminal or a host git GUI skip them silently. CI will then catch what the hooks would have.

## 3.11 Docs

```zsh
# [CONTAINER]
poe docs                             # open http://127.0.0.1:8000 in your host browser
```

## 3.12 GUI check

```zsh
# [CONTAINER]
rviz2                                # should open a window on your desktop
```
If it fails with "cannot open display", run `xhost +local:docker` on the **[HOST]**, and confirm `echo $DISPLAY` matches in both places.

## 3.13 Run the simulation

Follow `docs/guides/simulation.md`. The entry point is a launch file in `src/launcher/launch` with a layout from `src/launcher/layouts`. Set your domain ID (§3.8) first.

## 3.14 Day-to-day and reset

| Task | Where | Command |
|---|---|---|
| Morning start | HOST | `sudo tailscale up` (if needed), `ecr-login` (see 02 §2.3), then Reopen in Container or `devcontainer up` |
| Rebuild after Docker changes | — | Automatic: `initialize.sh` rebuilds on every open |
| Shell without VS Code | HOST | `devcontainer exec --workspace-folder ~/volley zsh` or `docker exec -it volley-user-develop zsh` |
| Terminal-only workflow | HOST | See §3.4: `devcontainer up` once, then `devcontainer exec ... zsh` per shell |
| Am I in the container? | either | `ls /.dockerenv` |
| Wipe container home (fresh start) | HOST, container stopped | `docker rm -f volley-user-develop && docker volume rm volley-home`. This loses `~/.zshrc`, the sccache cache, and any Claude Code login. |
| Wipe git-hooks volume | HOST | `docker volume rm volley-git-hooks` (post-create reinstalls the hooks) |
| Disk cleanup | HOST | `docker system df`, then `docker builder prune` (keeps volumes) |

## 3.15 Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Build fails: `401 Unauthorized` from `628548651667.dkr.ecr.us-west-2.amazonaws.com` | Host Docker isn't logged in to ECR, or the 12 h token expired. **[HOST]** `ecr-login` (02 §2.3) |
| "Tailscale is not running on host" | **[HOST]** `sudo tailscale up` |
| `permission denied ... docker.sock` | Not in the `docker` group yet; log out and back in |
| `Could not find a package configuration file provided by "ament_cmake_auto"`, then `ninja: error: loading 'build.ninja'` | ROS isn't sourced because direnv isn't hooked into your shell. The ninja error is just fallout from the failed CMake configure. Fix: §3.5, check `echo $ROS_DISTRO` prints `lyrical`, then `poe clean-yes && poe build`. Quick workaround: `source /opt/ros/lyrical/setup.zsh`. If `ls /opt/ros/lyrical/share/ament_cmake_auto` is missing, the image is broken; rebuild the container. |
| `ros2 run` can't find Volley packages | Overlay not loaded yet: `direnv reload` after the first build |
| No `poe` tab completion | `which poe`; `ls -la ~/.zfunc/_poe`; `rm -f ~/.zcompdump* && exec zsh` |
| Extensions missing or stale | Reopen the container; if `devcontainer.json` changed, `.vscode-server` is wiped and extensions reinstall |
| Files owned by root in the repo | Something ran with `sudo` inside; `sudo chown -R $(id -u):$(id -g) <path>` |
| Seeing nodes you didn't start | Domain-ID collision; see §3.8 |
| `git push` hangs or auth fails | **[HOST]** `ssh -T git@github.com`; keys must exist in host `~/.ssh` |
| Commit rejected | commitlint/prek hook. Use `type(scope): message` and read the hook output. |
| Hooks didn't run at all | You committed from the host; commit from the container (§3.10) |

