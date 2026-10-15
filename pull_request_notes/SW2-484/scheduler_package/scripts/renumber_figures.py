#!/usr/bin/env python3
"""Renumber figure captions in the study docs after sections or figures move.

    python3 scripts/renumber_figures.py            # all three documents

A caption is a paragraph that starts with ``*Figure N —`` (doc 01) or ``**Figure N —`` (docs 02, 03).
Captions are numbered 1, 2, 3 ... in reading order. ``N`` may be the literal letter ``N`` for a new figure.
Every prose reference ``Figure K`` / ``Figures K and L`` is rewritten from the caption's old number to its new one.
Run ``scripts/add_toc.py`` afterwards if headings changed.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ["01-software-background.md", "02-issue-and-proposal.md", "03-verification-plan.md"]
CAPTION = re.compile(r"^(\*{1,2})Figure (\d+|N) —")
REF = re.compile(r"\b(Figures?) ((?:\d+)(?:(?:, | and | or |–)\d+)*)")


def renumber(text):
    lines = text.split("\n")
    old_to_new, n = {}, 0
    for i, line in enumerate(lines):
        m = CAPTION.match(line)
        if m:
            n += 1
            if m.group(2) != "N":
                old_to_new[int(m.group(2))] = n
            lines[i] = CAPTION.sub(lambda mm: f"{mm.group(1)}Figure \u0000{n}\u0000 —", line, count=1)
    out, fence = [], False
    for line in lines:
        if line.startswith("```"):
            fence = not fence
        if not fence:
            line = REF.sub(lambda m: m.group(1) + " " + re.sub(
                r"\d+", lambda d: "\u0000%d\u0000" % old_to_new.get(int(d.group(0)), int(d.group(0))), m.group(2)), line)
        out.append(line)
    return "\n".join(out).replace("\u0000", ""), n


if __name__ == "__main__":
    for name in DOCS:
        path = ROOT / name
        text, count = renumber(path.read_text())
        path.write_text(text)
        print(f"{name}: {count} figures")
