#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13"]
# ///
"""
volley_guide.py: step-by-step guide through the Volley onboarding sessions (guide file 09).

For every step it shows:
  - which terminal commands to run (and can run them for you, after confirmation)
  - which files to upload to claude.ai, with size and approximate token count
  - which prompt to paste (copies it to the clipboard)
  - where to save the results, then a checklist
Progress is stored in <notes>/.volley_guide_state.json.

Run (no install needed; uv reads the dependency header above):
    uv run ~/repos/volley_notes/guide/volley_guide.py            # interactive
    uv run volley_guide.py list | show S3 | done | jump S5 | copy S1 1

Paths (override with env vars):
    VOLLEY_WS     repo                  default ~/volley
    VOLLEY_NOTES  notes git repo        default ~/repos/volley_notes
    VOLLEY_PACKS  repomix outputs       default ~/volley-packs
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from rich import box
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()

# --------------------------------------------------------------------------- paths
HOME = Path.home()
WS = Path(os.environ.get("VOLLEY_WS", HOME / "volley")).expanduser()
NOTES = Path(os.environ.get("VOLLEY_NOTES", HOME / "repos" / "volley_notes")).expanduser()
PACKS = Path(os.environ.get("VOLLEY_PACKS", HOME / "volley-packs")).expanduser()
SUBS = NOTES / "subsystems"
CONFIG = PACKS / "repomix.config.json"
STATE_FILE = NOTES / ".volley_guide_state.json"
STACK_MAP = NOTES / "stack-map.md"
CODEMAP = NOTES / "codemap.md"
RMX = f"repomix -c {CONFIG}"


def recon_script() -> Path:
    for p in (NOTES / "guide" / "volley-recon.sh", NOTES / "volley-recon.sh"):
        if p.exists():
            return p
    return NOTES / "guide" / "volley-recon.sh"


# --------------------------------------------------------------------------- prompts (07 / 09)
BASE_PROMPT = r"""You are a senior C++ systems and performance engineer with deep ROS 2 experience
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
   else."""


def package_prompt(pkg: str, order: int, total: int, depth: int, part: int, nparts: int,
                   pack_name: str, doc_name: str, deps: list[str], dependents: list[str],
                   tests_compressed: bool, extra_docs: list[str]) -> str:
    part_line = (f"This is part {part} of {nparts} of this package. "
                 + ("Start the document; later parts will extend it."
                    if part == 1 else f"Also attached: {doc_name} from the earlier part(s). Extend and correct it; "
                                      "return the COMPLETE updated document."))
    docs_line = (f"\nAlso attached: {', '.join(extra_docs)} (repo docs; may be stale, verify against code)."
                 if extra_docs and part == 1 else "")
    tests_line = " Tests in this pack are compressed (signatures only)." if tests_compressed else ""
    return f"""PACKAGE TASK: `{pkg}` — package {order} of {total} (bottom-up), dependency depth {depth}.
Attached pack: {pack_name}. {part_line}{tests_line}{docs_line}
Depends on (workspace): {', '.join(deps) or 'nothing'}. Used by: {', '.join(dependents) or 'nothing (leaf)'}.
Lower-layer packages are already documented in volley-notes.md; reuse their terms.

Write the package document {doc_name} with these sections:
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
Deliver it as described in rule 7 (downloadable {doc_name}, or one ````markdown block)."""


PCHANGE = """I'm about to change <symbol/file> to <goal>. Using the attached files:
1. Who calls this, from which component, executor/callback group/thread? Can it run
   concurrently with anything that touches the same state?
2. Ownership and lifetime of every object involved (creator, holder, destruction;
   any callback capturing `this` or raw pointers).
3. Invariants and local patterns I must follow (error handling, logging, parameters,
   naming, clang-tidy rules, tests).
4. Tests that cover this today, and the tests I should add.
5. RISK: items in my planned change. Max 400 words."""

P5 = """Trace a vehicle retrieval from operator request to AGV motion to bay
confirmation. Numbered sequence with path:line for each hop, the message/service/
action used, which component and executor/thread runs it, and where state is
persisted. Include a Mermaid sequenceDiagram of the whole flow. Flag any hop you
couldn't find. Max 600 words plus the diagram."""


def merge_notes(doc_name: str) -> str:
    return f"""Now update volley-notes.md (in the project knowledge) with this package's results.
Merge into existing sections instead of appending; add one row to "Package index"
for packages/{doc_name} (package, one-line purpose, key types); add new glossary
terms and conventions; move answered items out of "Open questions"; keep
[seen]/[inferred] tags; keep the whole file under 3,000 words.
Return the COMPLETE updated file as described in rule 7."""


SEED_NOTES = """# Volley notes

## Dev environment
(paste your existing devcontainer / poe / direnv notes here)

## Glossary

## Architecture summary
(components, how they talk, layer order)

## Conventions & safety rules
(C++20, clang-tidy, ownership, executors/callback groups, error handling, tests)

## Package index
| File | Package | Purpose | Key types |
|---|---|---|

## Open questions
"""

REPOMIX_CONFIG = {
    "output": {"style": "markdown", "removeEmptyLines": True, "showLineNumbers": False},
    "ignore": {
        "useGitignore": True,
        "useDefaultPatterns": True,
        "customPatterns": [
            "**/*.3ds", "**/*.dae", "**/*.png", "**/*.ico", "**/*.svg",
            "**/*.typeface.json", "**/*.tex", "**/*.cls", "**/*.bib",
            "**/terraform/**", "**/.terraform.lock.hcl",
            "src/launcher/layouts/**", "src/scenario/scenarios/**",
            "docs/assets/**", "controller_webview/fonts/**",
            "controller_webview/js/**", "controller_webview/includes/SleekDB/**",
            "controller_webview/css/**", "uv.lock", "artifacts/**", "docs/deprecated/**",
            "build/**", "install/**", "log/**", "coverage/**", "tools/third_party/**",
        ],
    },
    "security": {"enableSecurityCheck": True},
}


# --------------------------------------------------------------------------- code map generator
LAYERS = [
    ("0 · build", ["volley_cmake"]),
    ("1 · core utilities", ["stdx", "rclcppx", "yasminx", "mqtt", "otel", "dds_discovery"]),
    ("1 · shared libraries", ["common", "structures"]),
    ("2 · contracts", ["vrc_interfaces", "interfaces", "agv_interfaces", "bay_interfaces",
                       "vda5050_interfaces", "map_server"]),
    ("7 · ROS glue", ["common_ros"]),
    ("8 · planning libraries", ["task_planner", "planner_core", "cost_functions"]),
    ("9 · motion planning", ["motion_planner"]),
    ("10 · scheduling", ["scheduler"]),
    ("8 · nodes", ["central", "agvhito", "bay", "lift", "vrc", "vecs", "vis"]),
    ("11 · integration", ["sim", "system_tests", "scheduler_advanced_tests", "agvhito_tools"]),
    ("3–6 · Python chain / top", ["common_py", "sim_metrics", "scenario", "central_api", "launcher"]),
]
LAYER_OF = {p: name for name, pkgs in LAYERS for p in pkgs}
ORDER = {p: i for i, (_, pkgs) in enumerate(LAYERS) for p in pkgs}

SKIP_DIRS = {"build", "install", "log", ".git", "__pycache__", "node_modules", "terraform", ".terraform", "3d"}
SKIP_EXT = {".dae", ".3ds", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".stl", ".tex", ".cls", ".bib",
            ".pyc", ".so", ".a", ".bin", ".woff", ".ttf"}
DATA_DIRS = {"layouts", "scenarios", "schemas", "batch_configs", "sets", "params", "config", "documentation"}
SRC_EXT = {".hpp", ".h", ".hh", ".cpp", ".cc", ".cxx", ".py", ".msg", ".srv", ".action"}
VENDORED = ("controller_webview/js/threejs", "controller_webview/js/jquery", "controller_webview/js/chart",
            "controller_webview/js/moment", "controller_webview/js/async", "controller_webview/includes/SleekDB",
            "controller_webview/fonts", "controller_webview/css", "tools/third_party")


def _read(p: Path) -> str:
    try:
        if p.stat().st_size > 2_000_000:
            return ""
        return p.read_text(errors="replace")
    except OSError:
        return ""


def _lines(p: Path) -> int:
    t = _read(p)
    return t.count("\n") + (1 if t and not t.endswith("\n") else 0)


def _cpp_brief(text: str) -> str:
    head = "\n".join(text.splitlines()[:60])
    m = re.search(r"@brief\s+(.+)", head)
    if m:
        return m.group(1).strip()[:110]
    for line in head.splitlines():
        s = line.strip()
        if s.startswith(("///", "//!")) and len(s) > 6:
            return s.lstrip("/!").strip()[:110]
    return ""


def _cpp_decls(text: str) -> list[str]:
    t = re.sub(r"//[^\n]*", "", text)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"template\s*<[^<>]*(?:<[^<>]*>[^<>]*)*>", "", t)
    names = []
    for m in re.finditer(r"(?<!enum )\b(class|struct)\s+(?:\[\[[^\]]*\]\]\s*)?([A-Za-z_]\w*)\b[^;{()]*\{", t):
        names.append(f"{m.group(1)} {m.group(2)}")
    for m in re.finditer(r"\benum\s+(?:class|struct)?\s*([A-Za-z_]\w*)\s*(?::\s*[\w:]+)?\s*\{", t):
        names.append(f"enum {m.group(1)}")
    for m in re.finditer(r"\busing\s+([A-Za-z_]\w*)\s*=", t):
        if len(names) < 14:
            names.append(f"using {m.group(1)}")
    seen = list(dict.fromkeys(names))
    return seen[:14] + (["…"] if len(seen) > 14 else [])


def _py_info(text: str) -> tuple[str, list[str]]:
    import ast
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return "", []
    doc = (ast.get_docstring(tree) or "").strip().splitlines()
    names = [f"class {n.name}" if isinstance(n, ast.ClassDef) else f"def {n.name}"
             for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
             and not n.name.startswith("_")]
    return (doc[0][:110] if doc else ""), names[:10] + (["…"] if len(names) > 10 else [])


def _iface_fields(text: str) -> str:
    parts, fields = [], []
    for line in text.splitlines():
        s = line.split("#")[0].strip()
        if s == "---":
            parts.append(fields)
            fields = []
        elif s:
            toks = s.split()
            if len(toks) >= 2:
                fields.append(toks[1].split("=")[0])
    parts.append(fields)
    return " | ".join(", ".join(f[:10]) + (", …" if len(f) > 10 else "") for f in parts)


def _pkg_xml(p: Path) -> dict:
    t = _read(p)
    get = lambda tag: (re.search(fr"<{tag}>(.*?)</{tag}>", t, re.S) or [None, ""])[1].strip()
    deps = sorted(set(re.findall(r"<(?:build_|exec_|test_|build_export_)?depend>([^<]+)</", t)))
    return {"name": get("name"), "desc": " ".join(get("description").split())[:220],
            "build_type": get("build_type") or "?", "deps": deps}


def _describe_file(f: Path) -> str:
    ext = "".join(f.suffixes[-2:]) if f.name.endswith(".launch.py") else f.suffix
    text = _read(f)
    bits = []
    if ext in (".hpp", ".h", ".hh"):
        brief, decls = _cpp_brief(text), _cpp_decls(text)
        if decls:
            bits.append(", ".join(decls))
        if brief:
            bits.append(f'"{brief}"')
    elif ext in (".cpp", ".cc", ".cxx"):
        comps = re.findall(r"RCLCPP_COMPONENTS_REGISTER_NODE\(\s*([^)]+?)\s*\)", text)
        if comps:
            bits.append("component " + ", ".join(comps))
        if re.search(r"\bint\s+main\s*\(", text):
            bits.append("main()")
        brief = _cpp_brief(text)
        if brief:
            bits.append(f'"{brief}"')
    elif ext == ".launch.py" or (ext == ".py" and "launch" in f.parts):
        plugins = re.findall(r"plugin\s*=\s*['\"]([^'\"]+)", text)
        execs = re.findall(r"executable\s*=\s*['\"]([^'\"]+)", text)
        includes = re.findall(r"['\"]([\w.]+\.launch\.(?:py|xml))['\"]", text)
        if plugins:
            bits.append("loads " + ", ".join(dict.fromkeys(plugins)))
        if execs:
            bits.append("runs " + ", ".join(dict.fromkeys(execs)))
        if includes:
            bits.append("includes " + ", ".join(dict.fromkeys(includes)))
        if ext == ".py" and not (plugins or execs):
            doc, names = _py_info(text)
            bits += [", ".join(names)] if names else []
    elif ext == ".py":
        doc, names = _py_info(text)
        if names:
            bits.append(", ".join(names))
        if doc:
            bits.append(f'"{doc}"')
    elif ext in (".msg", ".srv", ".action"):
        fields = _iface_fields(text)
        if fields:
            bits.append(fields)
    return " — " + " · ".join(bits) if bits else ""


def _test_summary(test_dir: Path) -> str:
    files = [f for f in test_dir.rglob("*") if f.is_file() and f.suffix in (".cpp", ".py", ".hpp")]
    cases = sum(len(re.findall(r"\bTEST(?:_F|_P)?\s*\(", _read(f))) + len(re.findall(r"^\s*def test_", _read(f), re.M))
                for f in files)
    names = sorted({f.stem for f in files})
    shown = ", ".join(names[:25]) + (", …" if len(names) > 25 else "")
    return f"{len(files)} files, {cases} test cases: {shown}"


def _walk_pkg(root: Path, out: list[str]) -> None:
    def rec(d: Path, depth: int) -> None:
        entries = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name))
        for e in entries:
            if e.name.startswith(".") or e.name in SKIP_DIRS:
                continue
            rel_indent = "  " * depth
            if e.is_dir():
                if e.name in ("test", "tests"):
                    out.append(f"{rel_indent}- `{e.name}/` — {_test_summary(e)}")
                    continue
                if e.name in DATA_DIRS:
                    files = [f for f in e.rglob("*") if f.is_file() and f.suffix not in SKIP_EXT]
                    names = ", ".join(sorted(f.stem for f in files)[:30]) + (", …" if len(files) > 30 else "")
                    out.append(f"{rel_indent}- `{e.name}/` — data, {len(files)} files: {names}")
                    continue
                out.append(f"{rel_indent}- `{e.name}/`")
                rec(e, depth + 1)
            elif e.suffix not in SKIP_EXT:
                n = _lines(e) if e.suffix in SRC_EXT | {".txt", ".xml", ".yaml", ".yml", ".cmake", ".md", ".json", ".py"} else 0
                desc = _describe_file(e) if (e.suffix in SRC_EXT or e.name.endswith(".launch.py")) else ""
                size = f" ({n})" if n else ""
                out.append(f"{rel_indent}- `{e.name}`{size}{desc}")
    rec(root, 0)


def generate_codemap(ws: Path = WS) -> str:
    src = ws / "src"
    pkgs = []
    for px in sorted(src.rglob("package.xml")):
        if any(part in SKIP_DIRS for part in px.parts):
            continue
        info = _pkg_xml(px)
        info["dir"] = px.parent
        pkgs.append(info)
    ws_names = {p["name"] for p in pkgs}
    pkgs.sort(key=lambda p: (ORDER.get(p["name"], 99), p["name"]))

    out = ["# Volley code map", "",
           f"Generated {__import__('datetime').date.today()} from `{ws}` "
           f"(commit `{subprocess.run(['git', '-C', str(ws), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()}`).",
           "Every package in `src/`, bottom-up by stack layer: description, dependencies, files with line counts, "
           "declared types, components, launch contents and tests. Meshes, vendored JS, layouts/scenarios data and "
           "Terraform are summarized, not listed.", "",
           "Legend: `file (lines) — declared types · \"doc brief\"`; components = `RCLCPP_COMPONENTS_REGISTER_NODE`.", ""]

    # ---- repository top level
    out += ["## Repository top level", ""]
    for e in sorted(ws.iterdir(), key=lambda x: (x.is_file(), x.name)):
        if e.name in (".git", "build", "install", "log"):
            continue
        if e.is_dir():
            files = [f for f in e.rglob("*") if f.is_file() and not any(s in f.parts for s in SKIP_DIRS)]
            out.append(f"- `{e.name}/` — {len(files)} files")
            if e.name in ("controller_webview", "tools", "docs", "docker", "scripts", ".github", ".devcontainer"):
                for sub in sorted(x for x in e.iterdir() if not x.name.startswith(".") or e.name == ".github"):
                    relp = str(sub.relative_to(ws))
                    if sub.is_dir():
                        n = sum(1 for f in sub.rglob("*") if f.is_file())
                        if relp.startswith(VENDORED):
                            tag = " (vendored)"
                        elif any(v.startswith(relp + "/") for v in VENDORED):
                            tag = " (mostly vendored; own code listed below)"
                        else:
                            tag = ""
                        line = f"  - `{sub.name}/` — {n} files{tag}"
                        if sub.name in ("action", "requests", "noc", "demo", "scripts", "workflows", "architecture",
                                        "guides", "deprecated", "tips-and-tricks"):
                            stems = sorted(x.stem for x in sub.iterdir() if x.is_file())
                            line += ": " + ", ".join(stems[:40])
                        out.append(line)
                        if sub.name == "js":
                            for js in sorted(sub.iterdir()):
                                if js.is_dir() and not str(js.relative_to(ws)).startswith(VENDORED):
                                    out.append(f"    - `{js.name}/`: " + ", ".join(sorted(x.name for x in js.iterdir())))
                    elif sub.suffix not in SKIP_EXT:
                        desc = _describe_file(sub) if sub.suffix == ".py" else ""
                        out.append(f"  - `{sub.name}`{desc}")
        else:
            out.append(f"- `{e.name}`")
    out.append("")

    # ---- packages
    out += ["## Packages (bottom-up)", ""]
    current_layer = None
    for p in pkgs:
        layer = LAYER_OF.get(p["name"], "other")
        if layer != current_layer:
            out += [f"### Layer {layer}", ""]
            current_layer = layer
        code_lines = sum(_lines(f) for f in p["dir"].rglob("*")
                         if f.suffix in (".hpp", ".h", ".cpp", ".cc", ".py") and not any(s in f.parts for s in SKIP_DIRS))
        internal = [d for d in p["deps"] if d in ws_names]
        external = [d for d in p["deps"] if d not in ws_names]
        out.append(f"#### `{p['name']}` · `{p['dir'].relative_to(ws)}` · {p['build_type']} · {code_lines:,} lines")
        if p["desc"]:
            out.append(f"> {p['desc']}")
        out.append(f"- **depends on (workspace):** {', '.join(internal) or '—'}")
        out.append(f"- **depends on (external):** {', '.join(external) or '—'}")
        dependents = [q["name"] for q in pkgs if p["name"] in q["deps"]]
        out.append(f"- **used by:** {', '.join(dependents) or '— (leaf)'}")
        out.append("- **files:**")
        body: list[str] = []
        _walk_pkg(p["dir"], body)
        out += ["  " + b for b in body]
        out.append("")
    return "\n".join(out) + "\n"


def act_codemap() -> None:
    if not (WS / "src").exists():
        console.print(f"[red]{WS / 'src'} not found (set VOLLEY_WS)[/]")
        return
    with console.status("scanning src/ …"):
        text = generate_codemap()
    CODEMAP.parent.mkdir(parents=True, exist_ok=True)
    CODEMAP.write_text(text)
    console.print(f"[green]wrote[/] {CODEMAP}: {len(text.split()):,} words, ~{len(text) // 4:,} tokens")


# --------------------------------------------------------------------------- python actions
def act_write_config() -> None:
    PACKS.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists() and not Confirm.ask(f"{CONFIG} exists. Overwrite?", default=False):
        return
    CONFIG.write_text(json.dumps(REPOMIX_CONFIG, indent=2) + "\n")
    console.print(f"[green]wrote[/] {CONFIG}")


def act_copy_stack_map() -> None:
    src = next((p for p in (Path(__file__).resolve().parent / "stack-map.md", NOTES / "guide" / "stack-map.md")
                if p.exists()), None)
    if src is None:
        console.print("[red]stack-map.md not found next to this script or in guide/. Download it with the guide files.[/]")
        return
    if STACK_MAP.exists() and not Confirm.ask(f"{STACK_MAP} exists. Overwrite?", default=False):
        return
    STACK_MAP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, STACK_MAP)
    console.print(f"[green]copied[/] {src} → {STACK_MAP}")


def act_seed_notes() -> None:
    f = NOTES / "volley-notes.md"
    if f.exists():
        console.print(f"[yellow]{f} already exists, left untouched[/]")
        return
    NOTES.mkdir(parents=True, exist_ok=True)
    f.write_text(SEED_NOTES)
    console.print(f"[green]wrote[/] {f}. Paste your dev-environment notes into its first section.")


# --------------------------------------------------------------------------- step model
@dataclass
class Cmd:
    label: str
    cmd: str = ""                      # shell command (run with zsh/bash)
    cwd: Path | None = None
    where: str = "HOST"                # HOST | CONTAINER | CLAUDE
    runnable: bool = True
    action: Callable[[], None] | None = None   # python action instead of shell
    produces: list[Path] = field(default_factory=list)  # files this creates (auto-detected for shell cmds)


@dataclass
class Step:
    id: str
    title: str
    goal: str
    commands: list[Cmd] = field(default_factory=list)
    uploads: list[Path] = field(default_factory=list)       # attach to the chat
    knowledge: list[Path] = field(default_factory=list)     # put in Project knowledge
    prompts: list[tuple[str, str]] = field(default_factory=list)
    save: list[tuple[str, Path]] = field(default_factory=list)
    checks: list[Path] = field(default_factory=list)        # files that should exist when done
    notes: list[str] = field(default_factory=list)
    session: bool = False                                   # show the standard session loop
    subsystem: str = ""                                     # subsystems/<name>
    upload_why: str = ""                                    # why these uploads (or none)


SESSION_UPLOAD_WHY = (
    "Attach these to THIS chat only (paperclip), not to Project knowledge: they're package-specific and "
    "would otherwise be re-sent with every future chat. stack-map.md, volley-notes.md and the base prompt "
    "come from the Project automatically. Send the attachments and prompt 1 in ONE message."
)
LOCAL_ONLY_WHY = "Nothing to upload in this step. It only prepares files on your machine; uploads start in SETUP-4."

PKG_DOCS = NOTES / "packages"
WORK = PACKS / "work"                      # file lists + instruction files for repomix
PART_BUDGET = int(os.environ.get("VOLLEY_PART_BUDGET", 60_000))                      # est. tokens per pack (chars / 4)
DEFER_TO_END = ["common_py", "sim_metrics", "scenario", "central_api", "launcher"]  # orchestration: read after the nodes
NO_PACK_DIRS = {"layouts", "scenarios", "schemas", "sets", "batch_configs", "documentation", "3d", "terraform"}
EXTRA_DOCS = {
    "volley_cmake": ["docs/guides/volley-cmake.md", "docs/guides/cpp-style.md"],
    "dds_discovery": ["docs/architecture/discovery-server.md"],
    "vda5050_interfaces": ["docs/architecture/vda5050.md"],
    "vrc": ["docs/architecture/vrc.md"],
    "agvhito": ["docs/architecture/agv.md"],
    "bay": ["docs/architecture/bay.md"],
    "scheduler": ["docs/deprecated/scheduler.md"],
    "central": ["docs/deprecated/central.md"],
    "sim": ["docs/architecture/sim.md"],
    "system_tests": ["docs/architecture/system-tests.md"],
}


@dataclass
class Pkg:
    name: str
    dir: Path
    deps: list[str]
    dependents: list[str] = field(default_factory=list)
    depth: int = 0


def discover_packages() -> list[Pkg]:
    """Workspace packages from package.xml, ordered bottom-up by dependency depth."""
    src = WS / "src"
    if not src.exists():
        return []
    found: dict[str, Pkg] = {}
    for px in sorted(src.rglob("package.xml")):
        if any(part in SKIP_DIRS for part in px.parts):
            continue
        info = _pkg_xml(px)
        if info["name"]:
            found[info["name"]] = Pkg(info["name"], px.parent, info["deps"])
    for p in found.values():
        p.deps = [d for d in p.deps if d in found and d != p.name]
    for p in found.values():
        p.dependents = sorted(q.name for q in found.values() if p.name in q.deps)

    def depth(name: str, stack: tuple = ()) -> int:
        if name in stack:
            return 0
        p = found[name]
        return 0 if not p.deps else 1 + max(depth(d, stack + (name,)) for d in p.deps)

    for p in found.values():
        p.depth = depth(p.name)
    normal = [p for p in found.values() if p.name not in DEFER_TO_END]
    deferred = [found[n] for n in DEFER_TO_END if n in found]
    normal.sort(key=lambda p: (p.depth, -len(p.dependents), p.name))
    return normal + deferred


def _est(paths: list[Path]) -> int:
    return sum(p.stat().st_size for p in paths if p.exists()) // 4


def package_files(pkg: Pkg) -> tuple[list[Path], list[Path]]:
    impl, tests = [], []
    for f in sorted(pkg.dir.rglob("*")):
        if not f.is_file() or f.suffix in SKIP_EXT or f.name.startswith("."):
            continue
        rel_parts = f.relative_to(pkg.dir).parts
        if any(part in SKIP_DIRS or part in NO_PACK_DIRS for part in rel_parts[:-1]):
            continue
        if f.stat().st_size > 300_000:
            continue
        (tests if any(part in ("test", "tests") for part in rel_parts[:-1]) else impl).append(f)

    def rank(f: Path) -> tuple:
        rel = f.relative_to(pkg.dir)
        top = rel.parts[0] if len(rel.parts) > 1 else ""
        order = {"": 0, "include": 1, "src": 2, "msg": 1, "srv": 1, "action": 1}.get(top, 3)
        if f.name in ("package.xml", "CMakeLists.txt", "setup.py", "setup.cfg"):
            order = -1
        return (order, str(rel))
    impl.sort(key=rank)
    return impl, tests


def plan_parts(pkg: Pkg) -> list[tuple[list[Path], bool]]:
    """Split a package into packs of ≤ PART_BUDGET est. tokens. Returns [(files, compress_tests_only_part)]."""
    impl, tests = package_files(pkg)
    parts: list[list[Path]] = []
    cur, size = [], 0
    for f in impl:
        s = _est([f])
        # split when full, but don't leave a tiny part behind (allow up to 1.6× when the part is still small)
        if cur and size + s > PART_BUDGET and (size >= 0.4 * PART_BUDGET or size + s > 1.6 * PART_BUDGET):
            parts.append(cur)
            cur, size = [], 0
        cur.append(f)
        size += s
    t = _est(tests)
    result: list[tuple[list[Path], bool]] = []
    if tests and size + t <= PART_BUDGET:
        cur += tests
        tests = []
    if cur:
        parts.append(cur)
    result = [(p, False) for p in parts]
    if tests:
        result.append((tests, t > PART_BUDGET))     # separate tests part; compressed if still too big
    return result or [([], False)]


def make_prep(listfile: Path, instr: Path, files: list[Path], prompt: str) -> Callable[[], None]:
    def prep() -> None:
        WORK.mkdir(parents=True, exist_ok=True)
        listfile.write_text("\n".join(str(f.relative_to(WS)) for f in files) + "\n")
        instr.write_text(prompt + "\n")
        console.print(f"[green]wrote[/] {listfile.name} ({len(files)} files, ~{_est(files):,} tok est.) and {instr.name}")
    return prep


def package_steps() -> list[Step]:
    pkgs = discover_packages()
    total = len(pkgs)
    steps: list[Step] = []
    for idx, pkg in enumerate(pkgs, 1):
        doc = f"{idx:02d}-{pkg.name}.md"
        parts = plan_parts(pkg)
        n = len(parts)
        last_in_depth = idx == total or pkgs[idx].depth != pkg.depth or pkg.name in DEFER_TO_END
        for pi, (files, compress) in enumerate(parts, 1):
            sid = f"P{idx:02d}" + (f"-{pi}" if n > 1 else "")
            pack_name = f"P{idx:02d}-{pkg.name}-part{pi}of{n}.md"
            listfile, instr = WORK / f"{pack_name}.files.txt", WORK / f"{pack_name}.instructions.md"
            extra = [d for d in EXTRA_DOCS.get(pkg.name, []) if (WS / d).exists()]
            prompt = package_prompt(pkg.name, idx, total, pkg.depth, pi, n, pack_name, doc, pkg.deps,
                                    pkg.dependents, compress, [Path(d).name for d in extra])
            header = f"Volley package pack: {pkg.name}, part {pi} of {n}. The task is in the Instruction section at the end."
            uploads = [PACKS / pack_name] + ([WS / d for d in extra] if pi == 1 else []) + \
                      ([PKG_DOCS / doc] if pi > 1 else [])
            est = _est(files)
            title = f"{pkg.name}" + (f" · part {pi}/{n}" if n > 1 else "") + f" · depth {pkg.depth}"
            goal = (f"Package {idx}/{total}: `{pkg.dir.relative_to(WS)}`. Depends on: {', '.join(pkg.deps) or 'nothing'}. "
                    f"Used by: {', '.join(pkg.dependents) or 'nothing (leaf)'}. This pack: {len(files)} files, "
                    f"~{est:,} tokens (est.)" + (", tests compressed." if compress else "."))
            notes = []
            if pkg.name in DEFER_TO_END:
                notes.append("Python orchestration package: deferred to the end because it composes the nodes "
                             "you've already documented (common_ros depends on launcher only for launch/test resources).")
            if pi < n:
                notes.append(f"After saving the doc, continue with part {pi + 1}; attach the doc you just saved.")
            notes.append("Prompt 2 (merge notes) is "
                         + ("RECOMMENDED now: last package at this depth." if last_in_depth and pi == n
                            else "optional here; do it at least once per depth level."))
            steps.append(Step(
                sid, title, goal,
                commands=[
                    Cmd("Prepare file list + task instructions", action=make_prep(listfile, instr, files, prompt),
                        produces=[listfile, instr]),
                    Cmd("Build the repomix pack (task embedded at the end)",
                        f'{RMX} --stdin {"--compress " if compress else ""}--header-text "{header}" '
                        f'--instruction-file-path {instr} -o {PACKS / pack_name} < {listfile}', cwd=WS),
                    Cmd("Commit your notes after saving", f'git add -A && git commit -m "package {pkg.name} part {pi}/{n}"',
                        cwd=NOTES),
                ],
                uploads=uploads,
                prompts=[("Package task (paste with the attachments)", prompt),
                         ("Merge notes into volley-notes.md", merge_notes(doc))],
                save=[("Package doc", PKG_DOCS / doc), ("volley-notes.md (overwrite)", NOTES / "volley-notes.md")],
                checks=[PACKS / pack_name, PKG_DOCS / doc],
                notes=notes, session=True, subsystem=doc, upload_why=SESSION_UPLOAD_WHY,
            ))
    return steps


def build_steps() -> list[Step]:
    s: list[Step] = []
    s.append(Step(
        "SETUP-1", "Notes repo and folders",
        "Create the git repo for your knowledge (notes) and the folder for packs. The guide files "
        "(00–09, stack-map.md, volley-recon.sh, this script) go in guide/.",
        commands=[
            Cmd("Create folders", f"mkdir -p {NOTES}/guide {PKG_DOCS} {SUBS} {PACKS}"),
            Cmd("Init the notes git repo", f"git -C {NOTES} rev-parse 2>/dev/null || git -C {NOTES} init"),
            Cmd("Write the volley-notes.md seed (skeleton)", action=act_seed_notes, produces=[NOTES / "volley-notes.md"]),
            Cmd("Move the guide files into guide/ (adjust the source path)",
                f"mv ~/Downloads/0*-*.md ~/Downloads/stack-map.md ~/Downloads/volley-recon.sh "
                f"~/Downloads/volley_guide.py {NOTES}/guide/", runnable=False),
        ],
        checks=[NOTES / "volley-notes.md", PKG_DOCS],
        upload_why=LOCAL_ONLY_WHY,
        notes=["Paste your existing dev-environment notes into the first section of volley-notes.md.",
               "If your volley-notes.md has a 'Subsystem index' section, rename it to 'Package index'."],
    ))
    s.append(Step(
        "SETUP-2", "repomix config",
        "Write the shared ignore list (meshes, vendored JS, layouts, LaTeX, Terraform…). Package packs are built "
        "from explicit file lists, but the config still sets Markdown output and the security check.",
        commands=[
            Cmd("Check repomix is installed (needs --stdin, --header-text, --instruction-file-path)", "repomix --version"),
            Cmd("Write ~/volley-packs/repomix.config.json", action=act_write_config, produces=[CONFIG]),
        ],
        checks=[CONFIG],
        upload_why=LOCAL_ONLY_WHY,
    ))
    s.append(Step(
        "SETUP-3", "Stack map (+ optional code map)",
        "stack-map.md goes into Project knowledge. codemap.md is an optional local reference: a generated "
        "file layout of every package you can browse while reading.",
        commands=[
            Cmd("Copy stack-map.md into the notes repo", action=act_copy_stack_map, produces=[STACK_MAP]),
            Cmd("Optional: generate codemap.md (for you, not uploaded)", action=act_codemap, produces=[CODEMAP]),
        ],
        checks=[STACK_MAP],
        upload_why=LOCAL_ONLY_WHY,
    ))
    s.append(Step(
        "SETUP-4", "Create / update the Claude Project (claude.ai)",
        "A Project holds the base prompt (instructions) and two small living files (knowledge), so every "
        "chat gets them automatically.",
        commands=[
            Cmd("claude.ai → Projects → \"Volley onboarding\" (create or open)", where="CLAUDE", runnable=False),
            Cmd("Project instructions → REPLACE with the base prompt (copy with [c])", where="CLAUDE", runnable=False),
            Cmd("Project knowledge → stack-map.md + volley-notes.md only (remove recon.md / codemap.md if present)",
                where="CLAUDE", runnable=False),
            Cmd("Settings → enable 'Code execution and file creation' (lets Claude hand you .md files)",
                where="CLAUDE", runnable=False),
        ],
        knowledge=[STACK_MAP, NOTES / "volley-notes.md"],
        prompts=[("Base prompt (Project instructions)", BASE_PROMPT)],
        upload_why=(
            "No repomix pack is uploaded here, and that's intentional: Project knowledge is sent with EVERY chat, "
            "so it only holds what every session needs (stack-map.md ≈ 900 words, volley-notes.md ≤ 3k words). "
            "Every following step (P01, P02, …) builds a repomix pack for ONE package and you attach it to that "
            "package's chat."),
        notes=["The next steps are generated from the repo: one per package (bigger packages get several parts)."],
    ))
    pkg_steps = package_steps()
    if not pkg_steps:
        s.append(Step("P??", "Package steps unavailable",
                      f"No packages found under {WS / 'src'}. Set VOLLEY_WS to your repo and restart."))
    s += pkg_steps
    s.append(Step(
        "SLICE", "Slice · vehicle retrieval (after all packages)",
        "Follow one feature end to end across the packages you've documented.",
        commands=[
            Cmd("1. Collect candidate files", f"( rg -il 'retriev' src controller_webview/action controller_webview/requests "
                f"-g '!**/test/**'; rg -il 'vda5050|order' src/agvhito src/vda5050 src/central -g '!**/test/**' ) "
                f"| sort -u > {WORK / 'slice-files.txt'} && wc -l {WORK / 'slice-files.txt'}", cwd=WS),
            Cmd("2. Prune the list by hand if it's over ~30 files", f"${{EDITOR:-nano}} {WORK / 'slice-files.txt'}",
                runnable=False),
            Cmd("3. Pack exactly those files", f'{RMX} --stdin --output-show-line-numbers '
                f'-o {PACKS / "SLICE-retrieval.md"} < {WORK / "slice-files.txt"}', cwd=WS),
        ],
        uploads=[PACKS / "SLICE-retrieval.md"],
        prompts=[("Slice task", P5)],
        save=[("Slice doc", SUBS / "20-slice-retrieval.md")],
        checks=[PACKS / "SLICE-retrieval.md", SUBS / "20-slice-retrieval.md"],
        session=True, subsystem="20-slice-retrieval.md", upload_why=SESSION_UPLOAD_WHY,
        notes=["Also attach the package docs for central, agvhito and bay."],
    ))
    s.append(Step(
        "TICKET", "Your first ticket",
        "Before editing: callers, threads, lifetimes, invariants and tests of what you'll touch.",
        commands=[
            Cmd("1. List the files you'll touch plus their callers", f"rg -l '<Symbol>' src > {WORK / 'ticket-files.txt'}",
                cwd=WS, runnable=False),
            Cmd("2. Pack them", f'{RMX} --stdin --output-show-line-numbers -o {PACKS / "TICKET.md"} '
                f'< {WORK / "ticket-files.txt"}', cwd=WS, runnable=False),
        ],
        uploads=[PACKS / "TICKET.md"],
        prompts=[("P-change (fill in <symbol> and <goal>)", PCHANGE)],
        save=[("Ticket notes", SUBS / "30-ticket.md")],
        session=True, subsystem="30-ticket.md", upload_why=SESSION_UPLOAD_WHY,
        notes=["Attach the package docs of the packages involved."],
    ))
    return s


STEPS = build_steps()
SESSION_LOOP = [
    ("terminal", "[r] runs the commands: prepare the file list + instructions, then build the pack. "
                 "Check the token count repomix prints."),
    ("claude.ai", "Open the Volley Project → start a NEW chat."),
    ("chat", "Attach EVERY file under 'Attach to the chat' AND paste prompt 1 in the SAME message. Send."),
    ("chat", "Ask follow-ups if needed (2–3 max)."),
    ("chat", "Claude returns the package doc: download it to the 'Package doc' path, or copy the ````markdown "
             "block and press [w] → 1."),
    ("chat", "Prompt 2 (merge notes) when the step's note says so; save it with [w] → 2."),
    ("Project", "If volley-notes.md changed: replace it in Project knowledge."),
    ("terminal", "Commit (last command; [r] offers it)."),
    ("you", "Read the doc; spot-check 2–3 claims and one diagram against the code."),
]


# --------------------------------------------------------------------------- state
def load_state() -> dict:
    """Progress lives in STATE_FILE: the current step id and the ids marked done.
    It's written after every key press, so quitting (or Ctrl-C) and restarting resumes
    at the same step. The id (not the position) is stored, so the guide can gain steps later."""
    try:
        st = json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        st = {"current_id": STEPS[0].id, "done": []}
    i = find(st.get("current_id", "")) if st.get("current_id") else None
    if i is None and "current" in st and "current_id" not in st:   # old format stored an index
        i = min(int(st["current"]), len(STEPS) - 1)
    if i is None:                                   # step id no longer exists (guide changed): first step not done
        done = set(st.get("done", []))
        i = next((k for k, x in enumerate(STEPS) if x.id not in done), 0)
    st["current"] = i
    st.setdefault("done", [])
    return st


def save_state(st: dict) -> None:
    data = {"current_id": STEPS[st["current"]].id, "done": st["done"]}
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(data, indent=2))
    except OSError as e:
        console.print(f"[red]could not save state: {e}[/]")


def find(step_id: str) -> int | None:
    for i, st in enumerate(STEPS):
        if st.id.lower() == step_id.lower():
            return i
    return None


# --------------------------------------------------------------------------- helpers
def fsize(p: Path) -> str:
    if not p.exists():
        return "[red]missing[/]"
    if p.is_dir():
        return "[green]dir[/]"
    b = p.stat().st_size
    return f"[green]{b / 1024:,.0f} KB[/] · ~{b // 4:,} tok"


def where_badge(w: str) -> Text:
    colors = {"HOST": "black on cyan", "CONTAINER": "black on magenta", "CLAUDE": "black on yellow"}
    return Text(f" {w} ", style=colors.get(w, "reverse"))


def copy_to_clipboard(text: str) -> bool:
    for tool in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-b", "-i"], ["pbcopy"]):
        if shutil.which(tool[0]):
            try:
                subprocess.run(tool, input=text.encode(), check=True, timeout=5)
                return True
            except (subprocess.SubprocessError, OSError):
                continue
    return False


def paste_from_clipboard() -> str | None:
    for tool in (["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "-b", "-o"], ["pbpaste"]):
        if shutil.which(tool[0]):
            try:
                return subprocess.run(tool, capture_output=True, check=True, timeout=5).stdout.decode()
            except (subprocess.SubprocessError, OSError):
                continue
    return None


def strip_fences(text: str) -> str:
    """Remove one outer ```markdown … ``` fence (what Claude returns when it can't create files)."""
    lines = text.strip().splitlines()
    last = lines[-1].strip() if lines else ""
    if len(lines) >= 2 and lines[0].startswith("```") and len(last) >= 3 and set(last) == {"`"}:
        lines = lines[1:-1]
    return "\n".join(lines).rstrip() + "\n"


def do_write(step: Step) -> None:
    if not step.save:
        console.print("[yellow]this step has nothing to save[/]")
        return
    k = pick(len(step.save), "target (1 = detail file, 2 = volley-notes.md)")
    if k is None:
        return
    name, target = step.save[k]
    text = paste_from_clipboard()
    if text is None:
        console.print("[red]no clipboard tool (sudo apt install wl-clipboard). Save the file by hand.[/]")
        return
    text = strip_fences(text)
    words = len(text.split())
    if words < 30:
        console.print(f"[red]clipboard has only {words} words. Copy Claude's whole answer (code-block copy button) first.[/]")
        return
    console.print(Panel(Text("\n".join(text.splitlines()[:12]) + "\n…"), title=f"clipboard preview · {words:,} words"))
    if target.exists() and not Confirm.ask(f"overwrite {target}?", default=k == 1):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    console.print(f"[green]wrote[/] {target} ({words:,} words)")


def shell() -> str:
    return shutil.which("zsh") or shutil.which("bash") or "/bin/sh"


def run_cmd(c: Cmd) -> None:
    if c.action:
        c.action()
        return
    cwd = c.cwd or Path.cwd()
    if not cwd.exists():
        console.print(f"[red]cwd {cwd} does not exist[/]")
        return
    console.print(Rule(f"[bold]$ {c.label}"))
    console.print(Syntax(c.cmd, "bash", word_wrap=True))
    try:
        r = subprocess.run([shell(), "-c", c.cmd], cwd=cwd)
        style = "green" if r.returncode == 0 else "red"
        console.print(f"[{style}]exit code {r.returncode}[/]")
    except KeyboardInterrupt:
        console.print("[yellow]interrupted[/]")


# --------------------------------------------------------------------------- rendering
def render(idx: int, st_state: dict) -> None:
    step = STEPS[idx]
    done = step.id in st_state["done"]
    console.clear()
    title = Text.assemble((f"{step.id}", "bold cyan"), "  ·  ", (step.title, "bold"),
                          ("   ✔ done" if done else "", "green"))
    console.print(Panel(Text(step.goal), title=title, subtitle=f"step {idx + 1}/{len(STEPS)} · {len(st_state['done'])} done · progress: {STATE_FILE.name}",
                        border_style="green" if done else "cyan", box=box.ROUNDED))

    if step.commands:
        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", expand=True)
        t.add_column("#", width=3)
        t.add_column("where", width=11)
        t.add_column("what")
        for i, c in enumerate(step.commands, 1):
            body: list = [Text(c.label, style="bold")]
            if c.action:
                body.append(Text("(python action: run with [r])", style="dim"))
            elif c.cmd:
                body.append(Syntax(c.cmd, "bash", word_wrap=True, background_color="default"))
            if c.cwd:
                body.append(Text(f"cwd: {c.cwd}", style="dim"))
            if not c.runnable and not c.action:
                body.append(Text("(manual)", style="yellow"))
            t.add_row(str(i), where_badge(c.where), Group(*body))
        console.print(Panel(t, title="1 · Commands / actions", border_style="blue"))

    if step.knowledge:
        t = Table(box=box.MINIMAL, expand=True)
        t.add_column("Upload to Project knowledge")
        t.add_column("size", justify="right")
        for p in step.knowledge:
            t.add_row(str(p), fsize(p))
        console.print(Panel(t, title="2 · Claude Project knowledge (shared by every chat)", border_style="yellow"))

    if step.uploads:
        t = Table(box=box.MINIMAL, expand=True)
        t.add_column("Attach to the chat (📎)")
        t.add_column("size", justify="right")
        for p in step.uploads:
            t.add_row(str(p), fsize(p))
        total = sum(p.stat().st_size for p in step.uploads if p.exists() and p.is_file()) // 4
        t.add_row("[dim]total (approx.)[/]", f"~{total:,} tok")
        console.print(Panel(t, title="2 · Attach to a NEW chat in the Volley Project", border_style="yellow"))

    if step.upload_why:
        console.print(Panel(Text(step.upload_why), title="Why these uploads?" if (step.uploads or step.knowledge)
                            else "Uploads", border_style="dim yellow"))

    if step.prompts:
        t = Table(box=box.MINIMAL, expand=True)
        t.add_column("#", width=3)
        t.add_column("Prompt")
        t.add_column("first line", style="dim")
        for i, (name, text) in enumerate(step.prompts, 1):
            t.add_row(str(i), name, text.splitlines()[0][:70] + "…")
        console.print(Panel(t, title="3 · Prompts to paste (\\[c] copy, \\[v] view)", border_style="magenta"))

    if step.save:
        t = Table(box=box.MINIMAL, expand=True)
        t.add_column("Save")
        t.add_column("path")
        t.add_column("status", justify="right")
        for name, p in step.save:
            t.add_row(name, str(p), fsize(p))
        console.print(Panel(t, title="4 · Save results", border_style="green"))

    if step.session:
        t = Table(box=box.SIMPLE, show_header=False, expand=True)
        t.add_column(width=3)
        t.add_column(width=10, style="cyan")
        t.add_column()
        for i, (w, txt) in enumerate(SESSION_LOOP, 1):
            t.add_row(str(i), w, txt)
        console.print(Panel(t, title="5 · Session loop", border_style="white"))

    if step.notes:
        console.print(Panel(Markdown("\n".join(f"- {n}" for n in step.notes)), title="Notes", border_style="dim"))

    console.print(Text("[r] run  [c] copy prompt  [v] view prompt  [w] write clipboard → save file  [o] open folder  "
                       "[s] status  [d] done → next  [n]/[p] next/prev  [l] list  [j] jump  [q] quit", style="bold dim"))


def render_list(st_state: dict) -> None:
    t = Table(title="Volley onboarding steps", box=box.ROUNDED)
    t.add_column("", width=2)
    t.add_column("id")
    t.add_column("title")
    t.add_column("outputs present", justify="right")
    for i, s in enumerate(STEPS):
        mark = "✔" if s.id in st_state["done"] else ("▶" if i == st_state["current"] else "")
        present = sum(p.exists() for p in s.checks)
        t.add_row(mark, s.id, s.title, f"{present}/{len(s.checks)}" if s.checks else "—")
    console.print(t)


def fix_hint(step: Step, p: Path) -> str:
    """Explain how to create a missing file, based on what the guide knows produces it."""
    # 1. a command or action in this step produces it
    for i, c in enumerate(step.commands, 1):
        cmd = c.cmd or ""
        if (p in c.produces or f"-o {p}" in cmd or f"> {p}" in cmd
                or (cmd.startswith("mkdir") and str(p) in cmd.split())):
            how = "press [r] and run it" if (c.runnable or c.action) else "run it by hand (manual step)"
            return f"Created by command #{i} ({c.label}): {how}."
    # 2. this session's detail file
    if step.session and step.subsystem and p.name == step.subsystem and p.parent in (SUBS, PKG_DOCS):
        return ("Send the pack + prompt 1 in the claude.ai chat; download the document Claude returns to "
                f"{p}, or copy its ````markdown block and press [w] → 1.")
    # 3. the summary notes file
    if p == NOTES / "volley-notes.md":
        return "Created in SETUP-1 (python action #3). Jump there with [j] SETUP-1 and press [r]."
    # 4. a detail file from an earlier session
    if p.parent == SUBS:
        for other in STEPS:
            if other.subsystem == p.name:
                return f"Produced by session {other.id} ({other.title}). Complete it first ([j] {other.id}), or skip this attachment."
    # 5. a pack from another step
    for other in STEPS:
        for i, c in enumerate(other.commands, 1):
            if c.cmd and str(p) in c.cmd:
                return f"Created by {other.id} command #{i} ({c.label}). Run it there ([j] {other.id}, then [r])."
    # 6. files from the repo itself
    if WS in p.parents:
        return f"Expected in the volley repo but not found. Check the path, or `git -C {WS} pull`."
    if p == CODEMAP:
        return "Created in SETUP-3 (python action #2) or S1: press [r], or run `volley_guide.py codemap`."
    if p == STACK_MAP:
        return "Created in SETUP-3 (python action #1): [j] SETUP-3, then [r]."
    if p == NOTES / "recon.md":
        return "Optional, created in SETUP-3 command #2."
    return "Create it, or mark the step done anyway if you don't need it."


def missing_table(step: Step, paths: list[Path], title: str) -> Table:
    t = Table(title=title, box=box.SIMPLE, expand=True, title_justify="left")
    t.add_column("missing file", style="red", overflow="fold")
    t.add_column("how to fix", overflow="fold")
    for p in paths:
        t.add_row(Text(str(p)), Text(fix_hint(step, p)))
    return t


def render_status(step: Step) -> None:
    paths = list(dict.fromkeys(step.checks + step.uploads + step.knowledge + [p for _, p in step.save]))
    t = Table(title=f"{step.id}: expected files", box=box.SIMPLE, expand=True)
    t.add_column("file", overflow="fold")
    t.add_column("status", justify="right")
    t.add_column("how to fix", overflow="fold")
    for p in paths:
        t.add_row(Text(str(p)), fsize(p), Text("" if p.exists() else fix_hint(step, p)))
    console.print(t)


# --------------------------------------------------------------------------- interaction
def pick(n: int, what: str) -> int | None:
    if n == 0:
        console.print(f"[yellow]no {what} for this step[/]")
        return None
    if n == 1:
        return 0
    v = Prompt.ask(f"which {what}", choices=[str(i) for i in range(1, n + 1)], default="1")
    return int(v) - 1


def do_copy(step: Step, k: int | None = None) -> None:
    k = pick(len(step.prompts), "prompt") if k is None else k
    if k is None:
        return
    name, text = step.prompts[k]
    if copy_to_clipboard(text):
        console.print(f"[green]copied to clipboard:[/] {name}")
    else:
        console.print("[yellow]no clipboard tool found (sudo apt install wl-clipboard). Select and copy:[/]")
        console.print(Rule(name))
        print(text)          # plain print: no box characters in your selection
        console.print(Rule())


def interactive() -> None:
    st = load_state()
    if STATE_FILE.exists():
        console.print(f"[dim]Resuming at[/] [bold cyan]{STEPS[st['current']].id}[/] "
                      f"[dim]({len(st['done'])} done; progress file: {STATE_FILE})[/]")
        Prompt.ask("[dim]enter to continue[/]", default="")
    while True:
        idx = st["current"]
        step = STEPS[idx]
        render(idx, st)
        key = Prompt.ask("next action", default="d" if step.id not in st["done"] else "n").strip().lower()
        if key == "q":
            save_state(st)
            return
        if key == "r":
            runnable = [c for c in step.commands if c.runnable or c.action]
            if not runnable:
                console.print("[yellow]nothing runnable here; follow the manual steps[/]")
            for c in runnable:
                if Confirm.ask(f"run: [bold]{c.label}[/]?", default=True):
                    run_cmd(c)
            Prompt.ask("[dim]enter to continue[/]", default="")
        elif key == "c":
            do_copy(step)
            Prompt.ask("[dim]enter to continue[/]", default="")
        elif key == "w":
            do_write(step)
            Prompt.ask("[dim]enter to continue[/]", default="")
        elif key == "v":
            k = pick(len(step.prompts), "prompt")
            if k is not None:
                console.print(Rule(step.prompts[k][0]))
                print(step.prompts[k][1])
                console.print(Rule())
                Prompt.ask("[dim]enter to continue[/]", default="")
        elif key == "o":
            target = PACKS if step.uploads else NOTES
            opener = shutil.which("xdg-open") or shutil.which("open")
            if opener:
                subprocess.Popen([opener, str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            console.print(f"opened {target}")
        elif key == "s":
            render_status(step)
            Prompt.ask("[dim]enter to continue[/]", default="")
        elif key == "d":
            missing = [p for p in step.checks if not p.exists()]
            if missing:
                console.print(missing_table(step, missing, f"[yellow]{step.id} isn't finished: {len(missing)} expected file(s) missing[/]"))
                if not Confirm.ask("Mark done anyway?", default=False):
                    continue
            if step.id not in st["done"]:
                st["done"].append(step.id)
            st["current"] = min(idx + 1, len(STEPS) - 1)
            save_state(st)
        elif key == "n":
            st["current"] = min(idx + 1, len(STEPS) - 1)
        elif key == "p":
            st["current"] = max(idx - 1, 0)
        elif key == "l":
            render_list(st)
            Prompt.ask("[dim]enter to continue[/]", default="")
        elif key == "j":
            j = find(Prompt.ask("step id (e.g. S5)"))
            if j is None:
                console.print("[red]unknown id[/]")
            else:
                st["current"] = j
        save_state(st)


def main(argv: list[str]) -> None:
    if not argv:
        try:
            interactive()
        except KeyboardInterrupt:
            console.print()
        return
    st = load_state()
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        render_list(st)
    elif cmd in ("show", "next"):
        i = find(rest[0]) if rest else st["current"]
        if i is None:
            sys.exit(f"unknown step {rest[0]}")
        render(i, st)
    elif cmd == "done":
        step = STEPS[st["current"]]
        if step.id not in st["done"]:
            st["done"].append(step.id)
        st["current"] = min(st["current"] + 1, len(STEPS) - 1)
        save_state(st)
        console.print(f"[green]✔ {step.id}[/] → now at {STEPS[st['current']].id}")
    elif cmd == "jump" and rest:
        i = find(rest[0])
        if i is None:
            sys.exit(f"unknown step {rest[0]}")
        st["current"] = i
        save_state(st)
        render(i, st)
    elif cmd == "copy" and rest:
        i = find(rest[0])
        if i is None:
            sys.exit(f"unknown step {rest[0]}")
        k = int(rest[1]) - 1 if len(rest) > 1 else 0
        do_copy(STEPS[i], k)
    elif cmd == "codemap":
        if rest and rest[0] == "--stdout":
            print(generate_codemap())
        else:
            act_codemap()
    elif cmd == "reset":
        if Confirm.ask("reset progress?", default=False):
            save_state({"current": 0, "done": []})
    else:
        console.print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
