"""Read the code snapshots in sources/repomix-*.xml: files, top-level function bodies and line numbers.

Line numbers are those of each file as it appears in the snapshot, which are the lines of the live file at the
snapshot's commit. Figures that cite `file:line` compute it here instead of hard-coding it.

    defs = functions("scheduler")             # {"Scheduler::Plan": Fn(...), "ChainTrayEvent": Fn(...), ...}
    loc("Scheduler::ExpandRetrieveJob")       # "job_expansion.cpp:167"
    calls("Scheduler::Plan", r"\\bExpandJob\\(")  # [line, ...] in scheduler.cpp, inside Plan()'s body
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOMIX = {"scheduler": "repomix-scheduler.xml", "planner_core": "repomix-planner-core.xml",
           "motion_planner": "repomix-motion-planner.xml"}


@lru_cache(maxsize=None)
def source_files(pkg: str = "scheduler") -> dict[str, str]:
    raw = (ROOT / "sources" / REPOMIX[pkg]).read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(r'<file path="([^"]+)">\n(.*?)</file>', raw, re.S)}


def blank_comments(src: str) -> str:
    """Comments and string literals replaced by spaces, newlines kept, so offsets and line numbers still match."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])\'', blank, src, flags=re.S)


@dataclass
class Fn:
    name: str        # "Scheduler::Plan" or "ChainTrayEvent"
    path: str        # "src/scheduler.cpp"
    line: int        # line of the name in the definition
    start: int       # offset of the body's "{"
    end: int         # offset after the body's "}"
    header: str      # text from the end of the previous declaration to the body, whitespace collapsed

    @property
    def file(self) -> str:
        return Path(self.path).name

    @property
    def loc(self) -> str:
        return f"{self.file}:{self.line}"

    @property
    def body(self) -> str:
        """Body with comments and string literals blanked."""
        return blank_comments(source_files_of(self))[self.start:self.end]

    @property
    def end_line(self) -> int:
        return source_files_of(self)[:self.end].count("\n") + 1


_PKG_OF: dict[str, str] = {}


def source_files_of(fn: Fn) -> str:
    return source_files(_PKG_OF[fn.path])[fn.path]


def _scan(path: str, src: str) -> list[Fn]:
    """Function definitions whose enclosing braces are all namespaces (incl. anonymous ones)."""
    clean = blank_comments(src)
    out: list[Fn] = []
    stack: list[bool] = []          # True = namespace brace
    last_stop = 0                   # end of the previous top-level declaration
    i, n = 0, len(clean)
    while i < n:
        c = clean[i]
        if c in ";}" and all(stack):
            if c == "}":
                stack.pop()
            last_stop = i + 1
        elif c == "{":
            if all(stack):
                header = clean[last_stop:i]
                is_ns = re.search(r"\bnamespace\b[\w:\s]*$", header) is not None
                if not is_ns:
                    m = re.search(r"([A-Za-z_~][\w:]*(?:<[^<>()]*>)?)\s*\(", header)
                    is_fn = m and not re.match(r"\s*(?:template\s*<[^>]*>\s*)?(?:struct|class|enum|union)\b",
                                                header) and "=" not in header[:m.start()]
                    # find the matching brace
                    k, depth = i, 0
                    while k < n:
                        if clean[k] == "{":
                            depth += 1
                        elif clean[k] == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    if is_fn:
                        name = re.sub(r"<[^<>()]*>$", "", m.group(1))
                        line = src[:last_stop + m.start(1)].count("\n") + 1
                        out.append(Fn(name, path, line, i, k + 1, " ".join(header.split())))
                    i = k + 1
                    last_stop = i
                    continue
                stack.append(True)
            else:
                stack.append(False)
        elif c == "}":
            stack.pop()
        i += 1
    return out


@lru_cache(maxsize=None)
def functions(pkg: str = "scheduler", prefix: str = "src/") -> dict[str, Fn]:
    """Top-level function definitions in every `<prefix>*.cpp` of the snapshot. Overloads keep the first."""
    out: dict[str, Fn] = {}
    for path, src in sorted(source_files(pkg).items()):
        if not (path.startswith(prefix) and path.endswith(".cpp")):
            continue
        _PKG_OF[path] = pkg
        for fn in _scan(path, src):
            out.setdefault(fn.name, fn)
    return out


def bodies(pkg: str = "scheduler", *, qualified: bool = False) -> dict[str, str]:
    """{name: body text} for every top-level function in src/*.cpp; `Scheduler::` dropped unless qualified."""
    out: dict[str, str] = {}
    for name, fn in functions(pkg).items():
        key = name if qualified else name.split("::")[-1]
        out[key] = out.get(key, "") + fn.body
    return out


def fn(name: str, pkg: str = "scheduler") -> Fn:
    defs = functions(pkg)
    if name in defs:
        return defs[name]
    hits = [f for k, f in defs.items() if k.split("::")[-1] == name]
    if len(hits) != 1:
        raise KeyError(f"{name}: {len(hits)} definitions in the {pkg} snapshot")
    return hits[0]


def loc(name: str, pkg: str = "scheduler") -> str:
    return fn(name, pkg).loc


def calls(caller: str, pattern: str, pkg: str = "scheduler") -> list[int]:
    """Line numbers (in the caller's file) where `pattern` matches inside the caller's body."""
    f = fn(caller, pkg)
    clean = blank_comments(source_files_of(f))
    return [clean[:f.start + m.start()].count("\n") + 1 for m in re.finditer(pattern, clean[f.start:f.end])]


def call(caller: str, pattern: str, pkg: str = "scheduler", *, nth: int | None = None, file: bool = True) -> str:
    """'job_expansion.cpp:203' (first match) or 'file.cpp:203, :240' (all matches when nth is None)."""
    lines = calls(caller, pattern, pkg)
    if not lines:
        raise KeyError(f"{pattern!r} not found in {caller}")
    f = fn(caller, pkg).file
    if nth is not None:
        return f"{f}:{lines[nth]}" if file else f":{lines[nth]}"
    s = ", ".join(f":{ln}" for ln in lines)
    return (f + s) if file else s


def line_of(path: str, pattern: str, pkg: str = "scheduler", nth: int = 0) -> int:
    """Line of the nth match of `pattern` in a whole file (e.g. a declaration in a header)."""
    src = source_files(pkg)[path]
    m = list(re.finditer(pattern, src, re.M))[nth]
    return src[:m.start()].count("\n") + 1
