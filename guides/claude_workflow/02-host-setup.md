# 02 · Host setup (your laptop)

Everything here runs on the **[HOST]**, once. The dev container needs 2.1–2.7. The exploration tooling (files 05–06) needs 2.8–2.11.


## 2.1 Docker + buildx, without sudo
```bash
# [HOST]
docker --version && docker buildx version
sudo usermod -aG docker "$USER"     # then log out and back in
docker run --rm hello-world         # must work without sudo
```
Why: `initialize.sh` calls `docker` directly as you.

## 2.2 Tailscale (hard requirement)
```bash
# [HOST]
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                   # log in with your company account
tailscale status                    # should list peers
```
Why: `initialize.sh` exits with *"Tailscale is not running on host"* if `tailscale status` fails. The image build uses `--allow=network.host`, which most likely means it reaches internal infrastructure such as the apt proxy over the tailnet (`docs/architecture/apt-proxy.md`) **(verify)**. If you don't have tailnet access yet, that's your first ask.

## 2.3 AWS ECR login (hard requirement)

The Dockerfile starts `FROM ${BASE_TOOLCHAIN_IMAGE}`, which is a team-built ROS 2 Lyrical base image in a **private AWS ECR registry** (`628548651667.dkr.ecr.us-west-2.amazonaws.com/ros2:lyrical-base-toolchain-<date>`). The build runs on your host, so **your host's Docker** must be logged in. Without that, you get `401 Unauthorized` at `load metadata`.

```zsh
# [HOST] one-time: AWS CLI v2
cd /tmp && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip -q awscliv2.zip && sudo ./aws/install
aws configure sso                                 # start URL, region, account, role from the team
```
```zsh
# [HOST] ~/.zshrc. Use the profile name the team uses; "volley" is a placeholder.
alias ecr-login='aws sso login --profile volley && aws ecr get-login-password --region us-west-2 --profile volley | docker login --username AWS --password-stdin 628548651667.dkr.ecr.us-west-2.amazonaws.com'
```
```zsh
# [HOST] each morning (ECR tokens last 12 h), before opening the container
ecr-login
```
Run the login as yourself, **not** with `sudo`: Docker stores the credential in your `~/.docker/config.json`. If you'd rather not log in every day, use the Amazon ECR credential helper (`sudo apt install amazon-ecr-credential-helper`, plus `"credHelpers": {"628548651667.dkr.ecr.us-west-2.amazonaws.com": "ecr-login"}` in `~/.docker/config.json` and `export AWS_PROFILE=...` in `~/.zshrc`). Then only the SSO session needs renewing.

## 2.4 X11 access for GUIs
```bash
# [HOST]
sudo apt install x11-xserver-utils  # provides xhost
echo $DISPLAY                       # usually :0 or :1; must be non-empty
```
Why: `initialize.sh` runs `xhost +local:docker` so the container may draw on your screen. On Ubuntu's default Wayland session this goes through XWayland, which usually works. If GUIs fail, try logging into an "Ubuntu on Xorg" session.

## 2.5 SSH key on GitHub
```bash
# [HOST]
ssh -T git@github.com               # should greet you by username
```
Why: `~/.ssh` is mounted read-only into the container, and that's how git authenticates there.

## 2.6 Editor: VS Code or terminal

**Either** VS Code + Dev Containers extension (option A, 03 §3.3): install `ms-vscode-remote.remote-containers`. The container installs its own extension list (clangd, Python, CMake, Claude Code, …). **Or** the Dev Containers CLI for a terminal-only workflow (option B, 03 §3.4).

## 2.7 zsh: host vs container

**zsh note:** the container inherits `SHELL` from the host, and the image does ship zsh, but **without oh-my-zsh**. Your container home is the `volley-home` volume, **not** your host home, so your host `~/.zshrc` and `~/.oh-my-zsh` aren't visible inside. You'll create a container `~/.zshrc` in 03 §3.5. That step is required, not cosmetic.

## Shell conventions for the tools below

Everything in this section is **[HOST]**, in zsh. With oh-my-zsh, put any `eval`/`export`/`alias` lines **after** the `source $ZSH/oh-my-zsh.sh` line in `~/.zshrc`, so plugins don't override them. After editing, run `exec zsh` (cleaner than `source ~/.zshrc` with oh-my-zsh).

## 2.8 fnm — Fast Node Manager

**What it is:** A Node.js version manager written in Rust, like `nvm` but much faster and shell-agnostic. It lets you install and switch Node versions per project (it reads `.nvmrc` / `.node-version`). You need Node for repomix and for some Claude Code installs.

**Install:**
```zsh
# [HOST]
sudo apt install curl unzip           # installer needs these
curl -fsSL https://fnm.vercel.app/install | bash
```
The installer detects zsh and appends a block to `~/.zshrc`. Open `~/.zshrc`, make sure that block sits **below** `source $ZSH/oh-my-zsh.sh`, and make sure it contains this line (add `--use-on-cd` if missing):
```zsh
eval "$(fnm env --use-on-cd --shell zsh)"
```
Optional: add `fnm` to your oh-my-zsh `plugins=(...)` list for tab completion.

Then:
```zsh
# [HOST]
exec zsh
fnm install --lts          # install latest LTS Node
fnm default lts-latest     # make it the default
node -v && npm -v
```
`--use-on-cd` auto-switches the Node version when you `cd` into a directory with a `.node-version` file.

## 2.9 uv — Python package & project manager

**What it is:** Astral's Rust-based replacement for `pip`, `pip-tools`, `virtualenv`, `pipx` and `pyenv`. It is very fast and lockfile-based. **Volley already uses it** (`uv.lock`, `pyproject.toml`), so you'll need it for the Python side of the repo (lint, docs, tooling).

**Install:**
```zsh
# [HOST]
curl -LsSf https://astral.sh/uv/install.sh | sh
exec zsh
uv --version              # if "command not found": ensure ~/.local/bin is on PATH in ~/.zshrc
```
Tab completion, added to `~/.zshrc` after oh-my-zsh is sourced:
```zsh
eval "$(uv generate-shell-completion zsh)"
eval "$(uvx --generate-shell-completion zsh)"
```
Key commands:
```zsh
uv sync                      # create .venv from pyproject.toml + uv.lock (run in repo root)
uv run <cmd>                 # run inside the project venv without activating it
uvx <tool>                   # run a CLI tool in a throwaway env (like npx)
uv tool install <tool>       # install a CLI tool globally (like pipx)
uv python install 3.12       # manage Python versions
```
**Host vs container:**

- On the **[HOST]** you only need uv for standalone tools (`uvx`, `uv tool install`).
- In the **[CONTAINER]**, don't run `uv sync` yourself. The project pins `requires-python >=3.14,<3.15` (ROS Lyrical's Python), and its dependencies live in `[dependency-groups]` (`runtime`, `dev`, `docs`, ...) that the image already installs.
- Poe runs with `executor.type = "simple"`, so tasks use the container's environment directly, with no `.venv`.
- The only uv command you'll normally touch is **`poe lock`** (`uv lock`) after editing dependencies.

To browse the docs as a site, run this in the **[CONTAINER]**, where the pinned MkDocs plugins are installed. `--network=host` means the URL opens in your host browser:
```zsh
# [CONTAINER]
poe docs                     # mkdocs serve --livereload → http://127.0.0.1:8000
```

## 2.10 repomix — pack a repo into one LLM-friendly file

**What it is:** A Node CLI that concatenates selected files into a single XML/Markdown/plain/JSON document. The output includes a directory tree and per-file token counts, and the tool can compress code to signatures, strip comments, and run a secret scan (Secretlint) before output.

**Install (after fnm):**
```zsh
# [HOST]
npm install -g repomix
repomix --version
# or no-install: npx repomix@latest ...
```

Key flags used below:

| Flag | Purpose |
|---|---|
| `--include "a/**,b/**"` | Comma-separated globs to include |
| `-i, --ignore "..."` | Globs to exclude |
| `--compress` | Tree-sitter extraction of signatures/structure |
| `--remove-comments`, `--remove-empty-lines` | Further trimming |
| `--token-count-tree [N]` | Show token counts per file/dir (optionally only ≥N) |
| `--style markdown\|xml` | Output format (XML is easy for Claude to parse; Markdown is easy for you to read) |
| `-o <file>` | Output path |
| `--stdin` | Pack exactly the file list piped in |
| `--include-logs`, `--include-logs-count N`, `--include-diffs` | Add git history / uncommitted changes |
| `--no-directory-structure` | Skip the tree (saves tokens on repeat packs) |

**Keep packs out of the repo:**
```zsh
# [HOST]
mkdir -p ~/volley-packs
```

## 2.11 Other helpful tools (apt vs cargo)

Everything here is **[HOST]**. Most tools can be installed two ways:

- **`sudo apt install`** is quick and needs no extra toolchain, but you get Ubuntu's (sometimes older) version. A few tools aren't packaged at all (e.g. tokei), and Ubuntu **renames** two binaries: `fd` → `fdfind`, `bat` → `batcat`.
- **`cargo install`** builds the latest release from source with Rust, and the binaries keep their real names. It needs a one-time Rust + C toolchain setup (§2.11.1), and each install takes a minute or two to compile.

Pick one method per tool. If you install both, whichever directory comes first on `PATH` wins: `~/.cargo/bin` (cargo) or `/usr/bin` (apt). Check with `which -a <tool>`.

### 2.11.1 One-time: Rust toolchain (only needed for the cargo method)

```zsh
# [HOST]
sudo apt install build-essential       # C compiler + linker (`cc`); Rust needs it to link
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # accept the defaults
exec zsh
cc --version && cargo --version
```

- **rustup** is Rust's official installer. It installs into `~/.rustup` and `~/.cargo`, with no `sudo`, and puts `~/.cargo/bin` on your PATH. If a cargo-installed tool isn't found after `exec zsh`, add `source "$HOME/.cargo/env"` to `~/.zshrc`.
- **Why `build-essential`:** Rust compiles code itself but calls the system C linker (`cc`) for the final link. Without it, every crate's `build.rs` fails with `linker 'cc' not found`.
- Some crates (anything doing HTTPS/TLS) also need `sudo apt install pkg-config libssl-dev`.
- **Optional, faster:** `cargo install cargo-binstall`. After that, `cargo binstall <tool>` downloads a prebuilt binary when one exists instead of compiling.
- **Updating:** re-run `cargo install <crate>` to get the latest version (`rustup update` updates Rust itself). apt tools update with the rest of the system (`sudo apt upgrade`).

### 2.11.2 Tool reference

Each entry covers what the tool is, why it helps on Volley, a couple of example commands, and both install methods.

#### ripgrep (`rg`): search code fast
A recursive grep replacement written in Rust. It skips files listed in `.gitignore` and hidden/binary files by default, searches in parallel, and is typically much faster than `grep -r` on a repo this size. This is the main way you'll find "where is X used", and Phase 5 uses it to choose which files go into a pack.
```zsh
rg -n "retriev" src -g '!**/test/**'        # line numbers, skip tests
rg -l "vda5050" src | sort                    # just the file names
rg -t cpp "class .*Scheduler"                 # only C++ files
```
Install: `sudo apt install ripgrep` · `cargo install ripgrep`

#### fd: find files by name
A simpler, faster `find`. It uses regex or glob patterns, respects `.gitignore`, and has sane defaults (`fd foo` instead of `find . -iname '*foo*'`). Handy for "where are all the launch files / layouts / package.xml files".
```zsh
fd package.xml src                            # all 37 package manifests
fd -e launch.py src/launcher                  # launch files
fd -e hcl src tools                           # where do those 29 HCL files live?
```
Install: `sudo apt install fd-find` (binary is `fdfind`; alias below) · `cargo install fd-find` (binary `fd`)

#### bat: `cat` with syntax highlighting
Prints files with syntax highlighting, line numbers and git change markers, and pages long output automatically. It's nicer than `cat` for reading a file quickly in the terminal. `bat -r 40:80 file.cpp` shows just a line range.
Install: `sudo apt install bat` (binary `batcat`) · `cargo install --locked bat` (binary `bat`)

#### tokei: count lines of code (fast)
Counts files, code, comment and blank lines per language, very fast (Rust, parallel). It answers "how big is this, and in what languages?", which feeds your token budget. `-f` lists every file and `-t` filters languages.
```zsh
tokei src --sort code
tokei -f -t HCL src tools                     # which files are HCL?
```
Install: not in Ubuntu's apt repos · `cargo install tokei` (needs §2.11.1)

#### cloc: count lines of code (classic)
"Count Lines Of Code", a long-standing Perl script that does the same job as tokei. It's slower but packaged everywhere, and it has a few extra tricks:

- `--vcs=git` counts only git-tracked files, so build output and vendored junk outside git are ignored.
- `--by-file` gives per-file counts.
- `--diff` compares two trees or tarballs.
- `--csv` gives machine-readable output.

```zsh
cloc --vcs=git src
cloc src tools controller_webview --exclude-dir=third_party,js,SleekDB
cloc --by-file --include-lang=C++ src/planner/scheduler
```
Install: `sudo apt install cloc` · no cargo version (it's Perl; `npm install -g cloc` also works). Use **tokei or cloc**, not both.

#### jq / jaq: query and reshape JSON
`jq` is a command-line JSON processor. You use it to filter, select and reformat JSON, e.g. repomix `--style json` output, `gh` CLI output, schema files, or `colcon` and CI artifacts. `jaq` is a faster, jq-compatible reimplementation in Rust.
```zsh
jq '.' file.json                              # pretty-print
gh run list --json name,status | jq '.[] | select(.status!="completed")'
```
Install: `sudo apt install jq` · `cargo install jaq` (binary `jaq`)

#### yq: query YAML
jq for YAML. That's useful here because the codebase has about 42k lines of YAML (layouts, params, scenarios, colcon defaults). Watch out: there are two different tools called `yq`. **Ubuntu's apt `yq`** is a Python wrapper that converts YAML to JSON and pipes it through jq, so it uses jq syntax. **Mike Farah's `yq`** (Go) has its own similar syntax. Pick one and stick with it.
```zsh
yq '.' .colcon/defaults.yaml
yq '.build' .colcon/defaults.yaml
```
Install: `sudo apt install yq` (Python flavour) or `uv tool install yq` · no cargo version

#### Graphviz (`dot`, `tred`): render graphs
Turns `.dot` graph descriptions into SVG or PNG. `colcon graph --dot` emits the package dependency graph in this format. `tred` removes redundant transitive edges, so the picture shows only direct structure.
```zsh
tred pkg-graph.dot | dot -Tsvg -o pkg-graph.svg
```
Install: `sudo apt install graphviz` · no cargo version

#### direnv: per-directory environment
Loads and unloads environment variables when you `cd` into or out of a directory that has an `.envrc`. Volley uses it **inside the container** to source ROS and the workspace overlay. On the host it's optional; you'd only need it if you add host-side `.envrc` files of your own.
Install: `sudo apt install direnv`, then add `direnv` to oh-my-zsh `plugins=(...)` · no cargo version (written in Go)

#### gh: GitHub from the terminal
The official GitHub CLI. Use it to list and check out PRs, watch CI runs (`gh run watch`), read failing job logs, and open issues. With 18 workflow files in `.github/workflows`, `gh run view --log-failed` saves a lot of clicking.
```zsh
gh auth login
gh pr checkout 1234
gh run list --branch my-branch
gh run view --log-failed
```
Install: `sudo apt install gh` (Ubuntu's copy, may be older), or GitHub's own apt repo for the latest (setup lines at cli.github.com) · no cargo version

#### clangd: C++ language server
Gives editors jump-to-definition, find-references, hover types and clang-tidy diagnostics, using `compile_commands.json` from the build. In this codebase it's the replacement for Microsoft's IntelliSense, which the devcontainer disables.
Install: nothing. It's in the container and wired to the VS Code extension; it needs a build first (05 §5.5).

#### Claude Code: coding agent
An agent that reads, greps, runs and edits files on demand, so it only spends tokens on what it actually opens. The repo already has `.claude/CLAUDE.md` and settings for it.
Install: auto-installed as a VS Code extension in the container; CLI docs at https://docs.claude.com/en/docs/claude-code/overview

**If you used apt for fd/bat**, add these to `~/.zshrc` (after oh-my-zsh is sourced) so commands in this guide work as written:
```zsh
alias fd=fdfind
alias bat=batcat
```
Skip them if you used cargo. oh-my-zsh's `git` plugin is on by default and gives you short aliases (`gst`, `gco`, `glog`).

**Install everything in one go**, whichever method you choose:
```zsh
# [HOST] apt route
sudo apt install ripgrep fd-find bat cloc jq graphviz direnv

# [HOST] cargo route (after §2.11.1), plus the apt-only tools
cargo install ripgrep fd-find tokei
cargo install --locked bat
sudo apt install jq graphviz direnv
```

