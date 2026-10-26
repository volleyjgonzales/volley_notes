"""Drawing helpers shared by the deck figures (boxes, arrows, frames, sequence diagrams, UML, robots, icons)."""
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle, Polygon

from figstyle import AMBER, BG, BORDER, CARD, FG, GREEN, MONO, MUTED, MUTED_BG, RED, SKY, VIOLET, plt

PINK = "#F472B6"
TEAL = "#2DD4BF"
FRAME_FILL = "#151d30"


def canvas(w, h, xlim=None, ylim=None, equal=True):
    """A blank axes in data units; by default 1 unit = 1 inch so text sizes are predictable."""
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*(xlim or (0, w)))
    ax.set_ylim(*(ylim or (0, h)))
    if equal:
        ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def node(ax, x, y, text, color=SKY, w=1.9, h=0.62, fs=11, fill=CARD, mono=True, sub=None, bold=True, lw=1.8,
         ls="-", sub_fs=8.5, tc=FG, z=3):
    """Rounded box centred on (x, y). Returns the patch so arrows can clip to it."""
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                       facecolor=fill, edgecolor=color, lw=lw, ls=ls, zorder=z)
    ax.add_patch(p)
    if sub:
        nl = sub.count("\n") + 1
        dy = 0.07 + 0.065 * nl
        ax.text(x, y + dy, text, ha="center", va="center", fontsize=fs, family=MONO if mono else None,
                color=tc, fontweight="bold" if bold else "normal", zorder=z + 1)
        ax.text(x, y + dy - 0.16 - 0.065 * nl, sub, ha="center", va="center", fontsize=sub_fs, color=MUTED,
                zorder=z + 1, linespacing=1.15)
    else:
        ax.text(x, y, text, ha="center", va="center", fontsize=fs, family=MONO if mono else None,
                color=tc, fontweight="bold" if bold else "normal", zorder=z + 1, linespacing=1.15)
    return p


def center(p):
    bb = p.get_bbox()
    return ((bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2)


def edge(ax, pa, pb, label=None, color=MUTED, rad=0.0, lw=1.5, ls="-", fs=8.5, lpos=0.5, loff=(0, 0.13),
         lcolor=None, a=None, b=None, style="-|>", mono=True, z=2):
    """Arrow between two patches (pa, pb) or points (a, b), optional label at lpos along the chord."""
    kw = dict(arrowstyle=style, mutation_scale=13, color=color, lw=lw, ls=ls,
              connectionstyle=f"arc3,rad={rad}", zorder=z, shrinkA=2, shrinkB=2)
    if pa is not None:
        kw["patchA"] = pa
    if pb is not None:
        kw["patchB"] = pb
    ca = a if a is not None else center(pa)
    cb = b if b is not None else center(pb)
    ax.add_patch(FancyArrowPatch(ca, cb, **kw))
    if label:
        mx, my = ca[0] + (cb[0] - ca[0]) * lpos, ca[1] + (cb[1] - ca[1]) * lpos
        dx, dy = cb[0] - ca[0], cb[1] - ca[1]
        k = rad * 0.5 * (1 if lpos == 0.5 else 2 * min(lpos, 1 - lpos))
        mx += dy * k
        my -= dx * k
        ax.text(mx + loff[0], my + loff[1], label, ha="center", va="center", fontsize=fs,
                family=MONO if mono else None, color=lcolor or color, zorder=z + 3,
                bbox=dict(boxstyle="round,pad=0.12", facecolor=BG, edgecolor="none", alpha=0.85))


def label(ax, x, y, text, color=MUTED, fs=10, ha="center", mono=False, bold=False, va="center", z=6, **kw):
    return ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color, family=MONO if mono else None,
                   fontweight="bold" if bold else "normal", zorder=z, linespacing=1.2, **kw)


def frame(ax, x0, y0, x1, y1, title=None, color=VIOLET, fs=10, fill=FRAME_FILL, ls="--", lw=1.3, tpos="left"):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.02,rounding_size=0.15",
                                facecolor=fill, edgecolor=color, lw=lw, ls=ls, zorder=1))
    if title:
        if tpos == "left":
            ax.text(x0 + 0.12, y1 - 0.12, title, ha="left", va="top", fontsize=fs, family=MONO, color=color,
                    fontweight="bold", zorder=5)
        else:
            ax.text((x0 + x1) / 2, y1 - 0.12, title, ha="center", va="top", fontsize=fs, family=MONO,
                    color=color, fontweight="bold", zorder=5)


def chip(ax, x, y, text, color, fs=8.5, ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fs, family=MONO, color=color, zorder=6,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, edgecolor=color, lw=1.0))


# ------------------------------------------------------------------ sequence diagrams
class Seq:
    """Minimal UML-style sequence diagram: lifelines at given x, messages drawn top-down."""

    def __init__(self, ax, actors, top, bottom, head_h=0.55, fs=9.5):
        self.ax, self.x, self.top, self.bottom = ax, {}, top, bottom
        for name, (x, color, w, sub) in actors.items():
            self.x[name] = x
            node(ax, x, top, name, color, w=w, h=head_h, fs=fs, sub=sub, sub_fs=7.8)
            ax.plot([x, x], [top - head_h / 2, bottom], color=BORDER, lw=1.0, ls=(0, (4, 3)), zorder=1)

    def msg(self, a, b, y, text, color=SKY, fs=8.3, ls="-", above=True, lpos=0.5, ha="center", tc=None):
        xa, xb = self.x[a], self.x[b]
        if a == b:   # self-call: small loop on the right
            self.ax.add_patch(FancyArrowPatch((xa, y), (xa, y - 0.22), connectionstyle="arc3,rad=-1.2",
                                              arrowstyle="-|>", mutation_scale=10, color=color, lw=1.3,
                                              zorder=3))
            self.ax.text(xa + 0.22, y - 0.11, text, ha="left", va="center", fontsize=fs, family=MONO,
                         color=tc or color, zorder=6)
            return
        self.ax.add_patch(FancyArrowPatch((xa, y), (xb, y), arrowstyle="-|>", mutation_scale=11, color=color,
                                          lw=1.4, ls=ls, zorder=3, shrinkA=0, shrinkB=0))
        xm = xa + (xb - xa) * lpos
        if ha == "left":
            xm = min(xa, xb) + 0.1
        self.ax.text(xm, y + (0.1 if above else -0.12), text, ha=ha, va="bottom" if above else "top",
                     fontsize=fs, family=MONO, color=tc or color, zorder=6,
                     bbox=dict(boxstyle="round,pad=0.08", facecolor=BG, edgecolor="none", alpha=0.85))

    def note(self, a, y, text, color=AMBER, fs=8, w=None, ha="left", dx=0.12):
        x = self.x[a] + (dx if ha == "left" else -dx)
        self.ax.text(x, y, text, ha=ha, va="center", fontsize=fs, color=color, zorder=6, linespacing=1.15,
                     bbox=dict(boxstyle="round,pad=0.25", facecolor=CARD, edgecolor=color, lw=0.9))

    def act(self, a, y0, y1, color=SKY, w=0.12):
        self.ax.add_patch(Rectangle((self.x[a] - w / 2, y1), w, y0 - y1, facecolor=MUTED_BG, edgecolor=color,
                                    lw=1.0, zorder=2))

    def band(self, y0, y1, text, color=VIOLET, x0=None, x1=None, fs=8):
        xs = list(self.x.values())
        x0 = min(xs) - 0.9 if x0 is None else x0
        x1 = max(xs) + 0.9 if x1 is None else x1
        self.ax.add_patch(FancyBboxPatch((x0, y1), x1 - x0, y0 - y1, boxstyle="round,pad=0.0,rounding_size=0.08",
                                         facecolor="none", edgecolor=color, lw=1.0, ls="--", zorder=1))
        self.ax.text(x0 + 0.08, y0 - 0.06, text, ha="left", va="top", fontsize=fs, family=MONO, color=color,
                     zorder=6, bbox=dict(boxstyle="round,pad=0.1", facecolor=BG, edgecolor="none"))


# ------------------------------------------------------------------ UML class diagrams
UML_FS = 7.6


def _cw(fs):            # JetBrains Mono advance = 0.6 em
    return 0.6 * fs / 72.0


def _lh(fs):
    return 1.42 * fs / 72.0


class UBox:
    """Bounding box of a drawn UML class; anchor helpers for relationship lines."""

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    def top(self, f=0.5):
        return (self.x0 + f * (self.x1 - self.x0), self.y1)

    def bot(self, f=0.5):
        return (self.x0 + f * (self.x1 - self.x0), self.y0)

    def left(self, f=0.5):
        return (self.x0, self.y0 + f * (self.y1 - self.y0))

    def right(self, f=0.5):
        return (self.x1, self.y0 + f * (self.y1 - self.y0))


def uml_class(ax, x0, ytop, name, attrs=(), methods=(), color=SKY, stereo=None, fs=UML_FS, w=None,
              italic=False, name_fs=None):
    """UML class box: [«stereotype»] name / attributes / operations, monospace throughout.
    Lines may be (text, colour) tuples. Returns a UBox."""
    name_fs = name_fs or fs + 1.2
    lines_a = [a if isinstance(a, tuple) else (a, FG) for a in attrs]
    lines_m = [m if isinstance(m, tuple) else (m, FG) for m in methods]
    longest = max([len(name) * (name_fs / fs)] + [len(t) for t, _ in lines_a + lines_m] + [len(stereo or "") + 4])
    w = w or longest * _cw(fs) + 0.22
    lh = _lh(fs)
    head_h = (lh * 1.25 if stereo else 0) + _lh(name_fs) + 0.1
    a_h = (len(lines_a) * lh + 0.1) if lines_a else 0.0
    m_h = (len(lines_m) * lh + 0.1) if lines_m else 0.0
    h = head_h + a_h + m_h
    y0 = ytop - h
    ax.add_patch(Rectangle((x0, y0), w, h, facecolor=CARD, edgecolor=color, lw=1.3, zorder=3))
    ax.add_patch(Rectangle((x0, ytop - head_h), w, head_h, facecolor=MUTED_BG, edgecolor=color, lw=1.3, zorder=3))
    y = ytop - 0.06
    if stereo:
        ax.text(x0 + w / 2, y, f"«{stereo}»", ha="center", va="top", fontsize=fs - 0.6, family=MONO, color=MUTED,
                zorder=5)
        y -= lh * 1.15
    ax.text(x0 + w / 2, y, name, ha="center", va="top", fontsize=name_fs, family=MONO, color=color,
            fontweight="bold", style="italic" if italic else "normal", zorder=5)
    y = ytop - head_h - 0.05
    for block in (lines_a, lines_m):
        if not block:
            continue
        for t, c in block:
            t = t.replace(" ", "\u00a0")
            ax.text(x0 + 0.09, y, t, ha="left", va="top", fontsize=fs, family=MONO, color=c, zorder=5)
            y -= lh
        y -= 0.1
        if block is lines_a and lines_m:
            ax.plot([x0, x0 + w], [y + 0.05, y + 0.05], color=color, lw=0.8, zorder=4)
    return UBox(x0, y0, x0 + w, ytop)


def _head(ax, tip, frm, kind, color, size=0.13):
    import numpy as _np
    tip, frm = _np.asarray(tip, float), _np.asarray(frm, float)
    d = tip - frm
    d = d / (_np.linalg.norm(d) + 1e-12)
    n = _np.array([-d[1], d[0]])
    if kind in ("inh", "real"):
        pts = [tip, tip - d * size * 1.3 + n * size * 0.75, tip - d * size * 1.3 - n * size * 0.75]
        ax.add_patch(Polygon(pts, closed=True, facecolor=BG, edgecolor=color, lw=1.2, zorder=6))
        return tip - d * size * 1.3
    if kind in ("comp", "agg"):
        pts = [tip, tip - d * size + n * size * 0.55, tip - d * size * 2, tip - d * size - n * size * 0.55]
        ax.add_patch(Polygon(pts, closed=True, facecolor=color if kind == "comp" else BG, edgecolor=color, lw=1.2,
                             zorder=6))
        return tip - d * size * 2
    if kind in ("assoc", "dep"):
        ax.plot([tip[0], tip[0] - d[0] * size * 1.2 + n[0] * size * 0.6], [tip[1], tip[1] - d[1] * size * 1.2 + n[1] * size * 0.6],
                color=color, lw=1.2, zorder=6)
        ax.plot([tip[0], tip[0] - d[0] * size * 1.2 - n[0] * size * 0.6], [tip[1], tip[1] - d[1] * size * 1.2 - n[1] * size * 0.6],
                color=color, lw=1.2, zorder=6)
        return tip
    return tip


def uml_rel(ax, pts, kind="assoc", color=MUTED, label=None, lpos=None, mult_a=None, mult_b=None, fs=7.2, lc=None):
    """Relationship polyline from pts[0] (source) to pts[-1] (target).
    kind: inh / real (hollow triangle at target), comp / agg (diamond at SOURCE = owner),
    assoc / dep (open arrow at target; dep and real are dashed)."""
    pts = [tuple(p) for p in pts]
    ls = "--" if kind in ("dep", "real") else "-"
    p = list(pts)
    if kind in ("inh", "real", "assoc", "dep"):
        p[-1] = tuple(_head(ax, pts[-1], pts[-2], kind, color))
    if kind in ("comp", "agg"):
        p[0] = tuple(_head(ax, pts[0], pts[1], kind, color))
    xs, ys = zip(*p)
    ax.plot(xs, ys, color=color, lw=1.15, ls=ls, zorder=2)
    if label:
        i = len(pts) // 2 - (1 if len(pts) % 2 == 0 else 0)
        a, b = pts[i], pts[min(i + 1, len(pts) - 1)]
        lx, ly = lpos or ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        ax.text(lx, ly, label, ha="center", va="center", fontsize=fs, family=MONO, color=lc or color, zorder=7,
                bbox=dict(boxstyle="round,pad=0.1", facecolor=BG, edgecolor="none"))
    for m, (pp, qq) in ((mult_a, (pts[0], pts[1])), (mult_b, (pts[-1], pts[-2]))):
        if m:
            import numpy as _np
            d = _np.asarray(qq, float) - _np.asarray(pp, float)
            d = d / (_np.linalg.norm(d) + 1e-12)
            n = _np.array([-d[1], d[0]])
            pos = _np.asarray(pp) + d * 0.3 + n * 0.12
            ax.text(pos[0], pos[1], m, ha="center", va="center", fontsize=fs, family=MONO, color=lc or color, zorder=7)


# ------------------------------------------------------------------ a top-down AGV icon
def agv(ax, x, y, theta, color=SKY, L=0.56, W=0.42, alpha=1.0, z=5, frame=False, label=None, lw=1.4,
        fill=None, wheel=True, scale=1.0):
    """Top view of a small differential-drive robot: rounded body, two drive wheels, casters,
    front bumper, lidar puck and a heading arrow. (x, y) is the centre, theta the heading."""
    import numpy as _np
    from matplotlib.transforms import Affine2D
    L, W = L * scale, W * scale
    tr = Affine2D().rotate(theta).translate(x, y) + ax.transData
    body = FancyBboxPatch((-L / 2, -W / 2), L, W, boxstyle=f"round,pad=0,rounding_size={0.12 * scale}",
                          facecolor=fill or CARD, edgecolor=color, lw=lw, alpha=alpha, zorder=z, transform=tr)
    ax.add_patch(body)
    if wheel:
        for s in (-1, 1):
            ax.add_patch(Rectangle((-0.09 * scale, s * W / 2 - 0.035 * scale),
                                   0.18 * scale, 0.07 * scale, facecolor=FG, edgecolor="none", alpha=0.85 * alpha,
                                   zorder=z + 1, transform=tr))
        for cx in (-L / 2 + 0.07 * scale,):
            for s in (-1, 1):
                ax.add_patch(Circle((cx, s * W / 4), 0.025 * scale, facecolor=MUTED, edgecolor="none",
                                    alpha=alpha, zorder=z + 1, transform=tr))
    ax.add_patch(Rectangle((L / 2 - 0.05 * scale, -W / 2 + 0.05 * scale), 0.05 * scale, W - 0.1 * scale,
                           facecolor=color, edgecolor="none", alpha=0.8 * alpha, zorder=z + 1, transform=tr))
    ax.add_patch(Circle((L / 4, 0), 0.055 * scale, facecolor=BG, edgecolor=color, lw=1.0, alpha=alpha,
                        zorder=z + 2, transform=tr))
    ax.add_patch(FancyArrowPatch((-0.1 * scale, 0), (L / 2 + 0.16 * scale, 0), arrowstyle="-|>",
                                 mutation_scale=9, color=color, lw=1.3, alpha=alpha, zorder=z + 3, transform=tr))
    if frame:
        for (dx, dy), c, t in (((0.38, 0), RED, "x_b"), ((0, 0.38), GREEN, "y_b")):
            ax.add_patch(FancyArrowPatch((0, 0), (dx * scale, dy * scale), arrowstyle="-|>", mutation_scale=8,
                                         color=c, lw=1.1, zorder=z + 4, transform=tr))
    if label:
        ax.text(x, y - W * 0.9 - 0.08, label, ha="center", va="top", fontsize=8, family=MONO, color=color,
                zorder=z + 4)


# ------------------------------------------------------------------ small pictograms (s = size in data units)
def icon_server(ax, x, y, s=0.5, color=GREEN, z=6):
    """A rack server: three stacked units with status LEDs. (x, y) is the centre."""
    w, h = 0.75 * s, s
    for i in range(3):
        y0 = y - h / 2 + i * h / 3
        ax.add_patch(FancyBboxPatch((x - w / 2, y0 + 0.02 * s), w, h / 3 - 0.04 * s,
                                    boxstyle=f"round,pad=0,rounding_size={0.04 * s}", facecolor=CARD,
                                    edgecolor=color, lw=1.2, zorder=z))
        ax.add_patch(Circle((x - w / 2 + 0.12 * s, y0 + h / 6), 0.035 * s, facecolor=color, edgecolor="none",
                            zorder=z + 1))
        ax.plot([x - 0.05 * s, x + w / 2 - 0.1 * s], [y0 + h / 6] * 2, color=MUTED, lw=0.9, zorder=z + 1)


def icon_laptop(ax, x, y, s=0.5, color=RED, z=6):
    """A laptop / operator screen."""
    w, h = 0.95 * s, 0.6 * s
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2 + 0.1 * s), w, h, boxstyle=f"round,pad=0,rounding_size={0.05 * s}",
                                facecolor=CARD, edgecolor=color, lw=1.3, zorder=z))
    for i, f in enumerate((0.7, 0.45, 0.55)):
        ax.plot([x - w / 2 + 0.12 * s, x - w / 2 + 0.12 * s + f * (w - 0.24 * s)],
                [y + 0.3 * s - i * 0.13 * s] * 2, color=color, lw=1.0, alpha=0.7, zorder=z + 1)
    ax.add_patch(Polygon([(x - w / 2 - 0.12 * s, y - h / 2 + 0.06 * s), (x + w / 2 + 0.12 * s, y - h / 2 + 0.06 * s),
                          (x + w / 2, y - h / 2 + 0.12 * s), (x - w / 2, y - h / 2 + 0.12 * s)],
                         closed=True, facecolor=color, edgecolor=color, lw=1.0, zorder=z))


def icon_door(ax, x, y, s=0.5, color=TEAL, z=6):
    """A door in its frame, slightly open, with a handle."""
    w, h = 0.6 * s, s
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor="none", edgecolor=color, lw=1.4, zorder=z))
    ax.add_patch(Polygon([(x - w / 2, y - h / 2), (x + w * 0.3, y - h / 2 + 0.08 * s), (x + w * 0.3, y + h / 2 - 0.08 * s),
                          (x - w / 2, y + h / 2)], closed=True, facecolor=CARD, edgecolor=color, lw=1.2, zorder=z + 1))
    ax.add_patch(Circle((x + w * 0.18, y), 0.04 * s, facecolor=color, edgecolor="none", zorder=z + 2))


def icon_lift(ax, x, y, s=0.5, color=TEAL, z=6):
    """A lift car with up / down arrows."""
    w, h = 0.7 * s, s
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=CARD, edgecolor=color, lw=1.4, zorder=z))
    ax.plot([x, x], [y - h / 2, y + h / 2], color=color, lw=0.9, zorder=z + 1)
    for sgn in (1, -1):
        cx = x + sgn * w * 0.25
        tip = y + sgn * 0.22 * s
        ax.add_patch(Polygon([(cx - 0.09 * s, y - sgn * 0.02 * s), (cx + 0.09 * s, y - sgn * 0.02 * s), (cx, tip)],
                             closed=True, facecolor=color, edgecolor="none", zorder=z + 2))


def icon_workcell(ax, x, y, s=0.5, color=TEAL, z=6):
    """A dispenser / ingestor: a cabinet with a tray and a box on it."""
    w, h = 0.8 * s, 0.8 * s
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor=CARD, edgecolor=color, lw=1.4, zorder=z))
    ax.plot([x - w / 2 - 0.1 * s, x + w / 2 + 0.1 * s], [y, y], color=color, lw=1.6, zorder=z + 1)
    ax.add_patch(Rectangle((x - 0.15 * s, y), 0.3 * s, 0.22 * s, facecolor=color, edgecolor="none", alpha=0.7,
                           zorder=z + 1))


def icon_cloud(ax, x, y, s=0.5, color=AMBER, z=6):
    """A cloud outline (vendor cloud / external service)."""
    for dx, dy, r in ((-0.28, -0.05, 0.22), (0.0, 0.08, 0.3), (0.3, -0.04, 0.22)):
        ax.add_patch(Circle((x + dx * s, y + dy * s), r * s, facecolor=CARD, edgecolor=color, lw=1.2, zorder=z))
    ax.add_patch(Rectangle((x - 0.3 * s, y - 0.27 * s), 0.6 * s, 0.2 * s, facecolor=CARD, edgecolor="none", zorder=z + 1))
    ax.plot([x - 0.48 * s, x + 0.5 * s], [y - 0.27 * s] * 2, color=color, lw=1.2, zorder=z + 1)
