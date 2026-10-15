#!/usr/bin/env python3
"""Insert or refresh a table of contents between <!-- toc --> and <!-- /toc --> in the study docs.

    python3 scripts/add_toc.py            # all three documents

Anchors follow GitHub's slug rules (lower case, punctuation removed, spaces -> '-', duplicates get -1, -2 ...).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = {"01-software-background.md": 3, "02-issue-and-proposal.md": 2, "03-verification-plan.md": 2}


def slug(text, seen):
    s = text.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    s = s.replace(" ", "-")
    base, n = s, seen.get(s, 0)
    seen[base] = n + 1
    return base if n == 0 else f"{base}-{n}"


def headings(md):
    out, fence = [], False
    for line in md.split("\n"):
        if line.startswith("```"):
            fence = not fence
            continue
        m = None if fence else re.match(r"^(#{2,6}) (.+)$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def build(md, max_level):
    seen = {}
    lines = []
    for level, text in headings(md):
        anchor = slug(text, seen)     # every heading takes a slug, listed or not, so duplicates stay correct
        if level > max_level or text == "Contents":
            continue
        indent = "  " * (level - 2)
        lines.append(f"{indent}- [{text}](#{anchor})")
    return "\n".join(lines)


for name, max_level in DOCS.items():
    p = ROOT / name
    md = p.read_text(encoding="utf-8")
    md = re.sub(r"\n## Contents\n\n<!-- toc -->.*?<!-- /toc -->\n", "\n", md, flags=re.S)
    toc = build(md, max_level)
    block = f"\n## Contents\n\n<!-- toc -->\n{toc}\n<!-- /toc -->\n"
    first = re.search(r"^## ", md, flags=re.M)
    md = md[:first.start()].rstrip("\n") + "\n" + block + "\n" + md[first.start():]
    p.write_text(md, encoding="utf-8")
    print(name, toc.count("\n") + 1, "entries")
