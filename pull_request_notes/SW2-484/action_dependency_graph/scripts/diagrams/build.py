#!/usr/bin/env python3
"""Regenerate every figure of the learning kit.

    python3 scripts/diagrams/build.py            # all figures + figures/viewer.html
    python3 scripts/diagrams/build.py 05 07      # only figures whose file name starts with these

Requires: fontTools and brotli  (pip install fonttools brotli)
Every ADG edge drawn is computed by scripts/adg/adg.py from the example plan in example.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "adg"))

from registry import FIGURES  # noqa: E402
import fig_foundations, fig_adg, fig_scp, fig_exec  # noqa: E402,F401
import viewer  # noqa: E402

ROOT = HERE.parent.parent
OUT = ROOT / "figures"


def main(argv):
    OUT.mkdir(exist_ok=True)
    selected = [f for f in FIGURES if not argv or any(f.name.startswith(a) for a in argv)]
    problems = 0
    for fig in selected:
        doc = fig.fn()
        svg = doc.render()
        (OUT / f"{fig.name}.svg").write_text(svg, encoding="utf-8")
        ov = doc.text_overlaps()
        flag = "" if not ov else f"   !! {len(ov)} text overlaps: {ov[:4]}"
        problems += len(ov)
        c = doc.canvas
        print(f"{fig.name:34s} {c.w:5.0f} x {c.h:5.0f}  {len(svg) / 1024:6.1f} KB{flag}")
    if not argv:
        viewer.build(OUT, FIGURES)
        print("figures/viewer.html written")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
