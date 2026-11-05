"""Shared style tokens and drawing helpers for the course figures."""
import heapq
import itertools
import math
import random
from pathlib import Path

import logging

import matplotlib

matplotlib.use("svg")
# The SVGs keep text as text (svg.fonttype none) and the browser renders it with the deck's
# web fonts, so a missing local IBM Plex / JetBrains Mono only affects layout estimates.
# Silence matplotlib's "findfont: Font family ... not found" warnings about that.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle
import networkx as nx

OUT = Path(__file__).parent

# ---- design tokens (ui-ux-pro-max "Dark Mode (OLED)" developer palette) ----
BG = "#0F172A"
CARD = "#1B2336"
MUTED_BG = "#272F42"
FG = "#F8FAFC"
MUTED = "#94A3B8"
BORDER = "#475569"
GREEN = "#22C55E"
SKY = "#38BDF8"
AMBER = "#F59E0B"
RED = "#EF4444"
VIOLET = "#A78BFA"

plt.rcParams.update({
    "svg.fonttype": "none",
    "font.family": ["IBM Plex Sans", "DejaVu Sans"],
    "font.size": 13,
    "text.color": FG,
    "axes.edgecolor": BORDER,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.facecolor": "none",
    "figure.facecolor": "none",
    "savefig.transparent": True,
    "svg.hashsalt": "deck",   # stable element ids -> clean git diffs
})
MONO = ["JetBrains Mono", "DejaVu Sans Mono"]


plt.rcParams["mathtext.fontset"] = "dejavusans"


def save(fig, name):
    # Figures with $math$ are saved with text as paths: browsers do not have the math fonts that
    # matplotlib's mathtext would reference, so live text would render sub/superscripts wrongly.
    has_math = any("$" in t.get_text() for t in fig.findobj(matplotlib.text.Text))
    with plt.rc_context({"svg.fonttype": "path"} if has_math else {}):
        fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.05,
                    metadata={"Date": None})   # no timestamp -> reproducible output
    plt.close(fig)


def box(ax, xy, w, h, text, color, fs=12, mono=True, fill=CARD, sub=None):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                facecolor=fill, edgecolor=color, lw=1.8))
    ax.text(x, y + (0.12 if sub else 0), text, ha="center", va="center", fontsize=fs,
            family=MONO if mono else None, color=FG, fontweight="bold")
    if sub:
        ax.text(x, y - 0.2, sub, ha="center", va="center", fontsize=9.5, color=MUTED)


def arrow(ax, p, q, color=MUTED, style="-|>", lw=1.5, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=14, color=color, lw=lw, ls=ls))
