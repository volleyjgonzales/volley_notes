#!/usr/bin/env python3
"""Regenerate every figure of the study pack.

    python3 scripts/diagrams/build.py            # all figures + viewer
    python3 scripts/diagrams/build.py 13 15_     # only figures whose file name starts with these

Requires: fontTools and brotli  (pip install fonttools brotli)
Outputs:  figures/*.svg  and  figures/viewer.html
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from registry import FIGURES  # noqa: E402
import fig_flow, fig_uml, fig_facility, fig_misc, fig_code, fig_code2, fig_code3, fig_code4, fig_jobs, fig_concepts, fig_trace, fig_trayassign, fig_proposal, fig_context  # noqa: E402,F401
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
        print(f"{fig.name:40s} {c.w:5.0f} x {c.h:5.0f}  {len(svg) / 1024:6.1f} KB{flag}")
    if not argv:
        viewer.build(OUT, FIGURES)
        print("figures/viewer.html written")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
