import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({
    "svg.fonttype": "path", "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold", "figure.facecolor": "white",
    "axes.facecolor": "white", "savefig.facecolor": "white",
})
C = dict(s1="#1f6fb4", s2="#d9622b", pt="#2a9d4a", aux="#7a7a7a", hl="#c0392b", box="#555555", fill="#eef3fa")
def save(fig, path, preview):
    fig.savefig(path, format="svg", bbox_inches="tight")
    fig.savefig(preview, format="png", dpi=80, bbox_inches="tight")
    plt.close(fig)
def arrow(ax, p, q, color, lw=2, label=None, ms=14):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=ms))
    if label: ax.text(*label[0], label[1], color=color)
def clean(ax, lim=None):
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    if lim: ax.set_xlim(lim[0]); ax.set_ylim(lim[1])
