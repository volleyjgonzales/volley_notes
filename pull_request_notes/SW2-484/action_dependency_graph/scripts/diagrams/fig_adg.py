"""Chapter 02 figures: CBS, clock- vs dependency-driven execution, the type-2 rule, the full ADG."""
from __future__ import annotations

from adg import conflicts as _conflicts, execute as _execute
from adgdraw import Lanes, ARROW
from components import chip, connect, frame, label_pill, note, num_badge
from garage import Garage, NODES
from keys import action_rows, key_panel
from registry import figure
from scene import draw_robot, draw_trays, sched_positions
from svgkit import BBox, Doc, text_width, wrap
import example as ex
from theme import S, T

DOC = "chapters/02-cbs-to-adg.md"
J = ex.JUNCTION
A = ex.A


def robot_legend(extra=()):
    return [("box", ex.COLOR[r], f"AGV-{r[1:]}") for r in ex.ROBOTS] + list(extra)


def _lanes(d, x0, y0, **kw):
    return Lanes(d, x0, y0, ex.ROBOTS, ex.COLOR, max(a.t for a in ex.ACTIONS), **kw)


# --------------------------------------------------------------------------------------
# CBS
# --------------------------------------------------------------------------------------
ROOT_PATHS = {"A1": ["W18", "W22", "W25", "W26"], "A2": ["B21", "W41", "W22", "P23"],
              "A3": ["W13", "W18", "W22", "W25"], "A4": ["W8", "W13", "W18", "W22", "W41"]}


def _first_conflict(P):
    c = sorted(_conflicts(P), key=lambda x: x[4])
    return c[0] if c else None


def _soc(P):
    return sum(len(p) - 1 for p in P.values())


@figure("07-cbs", "Conflict-Based Search on the worked example", DOC)
def cbs():
    d = Doc("07-cbs", "Conflict-Based Search on the worked example")
    root = dict(ROOT_PATHS)
    Lc = dict(root, A2=["B21", "W41", "W41", "W22", "P23"])
    Rc = dict(root, A3=["W13", "W18", "W18", "W22", "W25"])
    LR = dict(Lc, A4=["W8", "W13", "W18", "W18", "W22", "W41"])
    RR = dict(Rc, A4=["W8", "W13", "W13", "W18", "W22", "W41"])
    assert RR == ex.PATHS
    assert _first_conflict(root)[:5] == ("vertex", "A2", "A3", J, 2)
    assert _first_conflict(Lc)[:5] == ("vertex", "A2", "A4", J, 3)
    assert _first_conflict(Rc)[:5] == ("vertex", "A3", "A4", "W18", 2)
    assert _first_conflict(LR) is None and _first_conflict(RR) is None

    def node(x, y, w, title, P, changed, cons, accent, *, verdict=None, vcol=T.red, dim=False):
        lines = [f"AGV-{r[1:]}: " + " ".join(P[r]) for r in ex.ROBOTS] if P else []
        h = 44 + len(lines) * 19 + (30 if verdict else 0) + (20 if cons else 0)
        op = 0.5 if dim else None
        d.rect(x, y, w, h, rx=10, fill=T.card, stroke=accent, sw=1.5 if not dim else 1.1, opacity=op,
               dash="5 4" if dim else None)
        d.text(x + 14, y + 20, title, size=13.5, weight=600, fill=T.fg if not dim else T.muted)
        if P:
            d.text(x + w - 14, y + 20, f"cost {_soc(P)}", size=11.5, family="mono", fill=T.muted, anchor="end")
        yy = y + 46
        if cons:
            d.text(x + 14, yy - 2, cons, size=11, family="mono", fill=T.amber)
            yy += 20
        for r, ln in zip(ex.ROBOTS, lines):
            hl = r in changed
            d.text(x + 14, yy, ln, size=11.5, family="mono", weight=600 if hl else 400,
                   fill=ex.COLOR[r] if hl else T.fg2)
            yy += 19
        if verdict:
            d.line(x + 12, yy - 4, x + w - 12, yy - 4, stroke=T.border_soft, sw=1)
            d.text(x + 14, yy + 12, verdict, size=11.5, family="mono", weight=600, fill=vcol)
        return BBox(x, y, x + w, y + h)

    w1, w2, gap2 = 318, 290, 20
    xs2 = [i * (w2 + gap2) for i in range(4)]
    tot = xs2[-1] + w2
    rb = node(tot / 2 - w1 / 2, 0, w1, "Root: everyone's shortest path", root, set(), None, T.sky,
              verdict=f"conflict: AGV-2 and AGV-3 both at {J}, t=2")
    y1 = rb.y1 + 70
    lb = node((xs2[0] + xs2[1] + w2) / 2 - w1 / 2, y1, w1, "Child L", Lc, {"A2"}, f"+ ⟨AGV-2, {J}, 2⟩",
              T.border, verdict=f"conflict: AGV-2 and AGV-4 both at {J}, t=3")
    rbx = node((xs2[2] + xs2[3] + w2) / 2 - w1 / 2, y1, w1, "Child R", Rc, {"A3"}, f"+ ⟨AGV-3, {J}, 2⟩",
               T.border, verdict="conflict: AGV-3 and AGV-4 both at W18, t=2")
    y2 = max(lb.y1, rbx.y1) + 70
    ll = node(xs2[0], y2, w2, "Child LL", None, set(), f"+ ⟨AGV-2, {J}, 3⟩", T.border,
              verdict="cost 15, still conflicts", vcol=T.muted, dim=True)
    lr = node(xs2[1], y2, w2, "Child LR", LR, {"A4"}, f"+ ⟨AGV-4, {J}, 3⟩", T.green,
              verdict="no conflict: a solution", vcol=T.green)
    rl = node(xs2[2], y2, w2, "Child RL", None, set(), "+ ⟨AGV-3, W18, 2⟩", T.border,
              verdict="cost 15, still conflicts", vcol=T.muted, dim=True)
    rr = node(xs2[3], y2, w2, "Child RR  ← used in this kit", RR, {"A4"}, "+ ⟨AGV-4, W18, 2⟩", T.teal,
              verdict="no conflict: a solution", vcol=T.teal)
    for parent, kids, labs in ((rb, (lb, rbx), (f"AGV-2 may not be at {J} at t=2", f"AGV-3 may not be at {J} at t=2")),
                               (lb, (ll, lr), ("AGV-2 waits again", "AGV-4 waits at W18")),
                               (rbx, (rl, rr), ("AGV-3 detours", "AGV-4 waits at W13"))):
        for kid, lab in zip(kids, labs):
            my = (parent.y1 + kid.y0) / 2
            connect(d, [(parent.cx, parent.y1), (parent.cx, my), (kid.cx, my), (kid.cx, kid.y0)], kind="flow",
                    color=T.fg2, size=8, sw=1.4)
            label_pill(d, kid.cx, my + 2, lab, color=T.amber, size=11, family="sans", bg=T.bg)
    rows = [
        ("AGV-1: W18 W22 ...", "AGV-1's path: its place at t = 0, 1, 2, ... (figure 1.5 draws the final one)", T.fg2),
        ("⟨AGV-3, W22, 2⟩", "a constraint: AGV-3 may not be at W22 at time step t = 2", T.amber),
        ("cost 15", "sum of costs: total number of steps of all four paths (lower is better)", T.fg2),
        ("conflict", "the earliest moment two AGVs are on the same place (or swap places)", T.red),
        ("bold line", "the AGV that was re-planned in this node because of the new constraint", T.fg),
    ]
    key_panel(d, 0, max(ll.y1, lr.y1, rl.y1, rr.y1) + 30, tot, "How to read a node", rows)
    frame(d, title="Conflict-Based Search on the worked example",
          subtitle="High level: a tree of constraint sets. Each node plans every AGV on its own (low level, e.g. "
                   "space-time A*), finds the earliest conflict and branches into two children, each forbidding "
                   "one of the two AGVs from that place at that time.",
          badge_key="illustrative",
          legend=[("box", T.teal, "solution used in the rest of the kit"), ("box", T.green, "equally cheap solution"),
                  ("dashbox", T.border, "branch not expanded here")],
          footnote="LR and RR both cost 15, the optimum for this instance; which one CBS returns depends on its "
                   "tie-breaking. Every path and conflict in this figure is checked by an assertion in "
                   "scripts/diagrams/fig_adg.py.")
    return d


# --------------------------------------------------------------------------------------
# Delay: clock-driven vs ADG-driven execution
# --------------------------------------------------------------------------------------

def gantt(d, x0, y0, sched, *, title, scale=78, tmax=10, lane_h=34, occ=None, occ_bad=(), marker=None):
    """sched: {action: (start, end)}. occ: list of (robot, start, end) at the junction."""
    d.text(x0, y0, title, size=13.5, weight=600, fill=T.fg)
    y = y0 + (42 if marker is not None else 26)
    lw = 70
    rows = ex.ROBOTS + (["J"] if occ is not None else [])
    for i, r in enumerate(rows):
        yy = y + i * (lane_h + 6)
        if r == "J":
            d.text(x0, yy + lane_h / 2, f"at {J}", size=12, weight=600, fill=T.teal)
        else:
            d.text(x0, yy + lane_h / 2, f"AGV-{r[1:]}", size=12, weight=600, fill=ex.COLOR[r])
        d.rect(x0 + lw, yy, tmax * scale, lane_h, rx=4, fill=T.tint(T.card, 0.4, T.bg), layer="bg")
    for t in range(tmax + 1):
        gx = x0 + lw + t * scale
        d.line(gx, y - 4, gx, y + len(rows) * (lane_h + 6) - 6, stroke=T.grid, sw=1, layer="bg")
        d.text(gx, y + len(rows) * (lane_h + 6) + 8, f"{t} s", size=11, family="mono", fill=T.muted, anchor="middle")
    for a, (s, e) in sched.items():
        i = ex.ROBOTS.index(a.R)
        yy = y + i * (lane_h + 6)
        col = ex.COLOR[a.R]
        bx = x0 + lw + s * scale
        bw = (e - s) * scale
        slow = (e - s) > 1.01
        d.rect(bx + 1, yy + 3, bw - 2, lane_h - 6, rx=5, fill=T.bg if a.wait else T.tint(col, 0.22, T.bg),
               stroke=col, sw=1.2 if not slow else 2, dash="4 3" if a.wait else None)
        lab = a.id if bw < 70 else (f"{a.id} wait" if a.wait else f"{a.id} {a.s}→{a.g}")
        d.text(bx + bw / 2, yy + lane_h / 2, lab, size=10.5, family="mono", weight=600, fill=T.fg, anchor="middle")
    if occ is not None:
        yy = y + len(ex.ROBOTS) * (lane_h + 6)
        for k, (r, s, e) in enumerate(occ):
            col = ex.COLOR[r]
            off = (k % 2) * (lane_h / 2 - 2)
            d.rect(x0 + lw + s * scale + 1, yy + 3 + off, (e - s) * scale - 2, lane_h / 2 - 4, rx=3,
                   fill=T.tint(col, 0.45, T.bg), stroke=col, sw=1)
        for (s, e) in occ_bad:
            d.rect(x0 + lw + s * scale, yy - 2, (e - s) * scale, lane_h + 4, rx=4, fill="none", stroke=T.red, sw=2.2)
    if marker is not None:
        mx = x0 + lw + marker * scale
        d.line(mx, y - 10, mx, y + len(rows) * (lane_h + 6) - 2, stroke=T.amber, sw=1.4, dash="3 3", layer="over")
        d.text(mx, y - 16, f"{marker:g} s", size=10.5, family="mono", weight=600, fill=T.amber, anchor="middle")
    return BBox(x0, y0, x0 + lw + tmax * scale, y + len(rows) * (lane_h + 6) + 16)


def j_occupancy(sched):
    """Interval in which each AGV is at the junction: from arriving there to having fully left."""
    occ = []
    for r in ex.ROBOTS:
        acts = sorted([a for a in sched if a.R == r], key=lambda a: a.t)
        tin = None
        for a in acts:
            if a.g == J and not a.wait:
                tin = sched[a][1]
            if a.s == J and not a.wait and tin is not None:
                occ.append((r, tin, sched[a][1]))
                tin = None
    return occ


def overlaps(occ):
    out = []
    for i in range(len(occ)):
        for j in range(i + 1, len(occ)):
            s, e = max(occ[i][1], occ[j][1]), min(occ[i][2], occ[j][2])
            if s < e - 1e-9:
                out.append((s, e, occ[i][0], occ[j][0]))
    return out


DELAY = {"A2-1": 2.5}


def _dur(a):
    return DELAY.get(a.id, 1.0)


def timed_schedule(actions):
    by = {}
    for a in sorted(actions, key=lambda a: (a.R, a.t)):
        st = max(float(a.t), by.get(a.R, 0.0))
        by[a.R] = st + _dur(a)
        yield a, (st, st + _dur(a))


def snapshot_scene(d, x0, y0, sched, tau, title, *, bad=False):
    d.text(x0, y0, title, size=12.5, weight=600, fill=T.fg)
    G = Garage(d, x0, y0 + 14, 19, xlim=(20.4, 40.6), ylim=(14.6, 25.2))
    G.base(labels=True, axes=False, context=False, highlight=(J,), wp_below=True)
    pos = sched_positions(sched, tau)
    for r, st in pos.items():
        if NODES and G.xmin - 1 <= st["at"][0] <= G.xmax + 1 and G.ymin - 1 <= st["at"][1] <= G.ymax + 1:
            draw_robot(G, r, st["at"], st["heading"], label=f"AGV-{r[1:]}", label_side="right" if r != "A2" else "left")
    if bad:
        x, y = G.P(J)
        d.circle(x, y, 40, fill="none", stroke=T.red, sw=2.4, dash="5 4", layer="top")
    return G.box


@figure("08-delay", "One late AGV: clock-driven vs dependency-driven execution", DOC)
def delay():
    d = Doc("08-delay", "Clock-driven vs dependency-driven execution")
    timed = dict(timed_schedule(ex.ACTIONS))
    adg = _execute(ex.ACTIONS, ex.T1_FULL | ex.T2_FULL, _dur)
    occ_t, occ_a = j_occupancy(timed), j_occupancy(adg)
    bad_t, bad_a = overlaps(occ_t), overlaps(occ_a)
    assert bad_t and not bad_a
    tau = 3.75
    tmax = int(max(e for _, e in adg.values())) + 1
    b1 = gantt(d, 0, 0, timed, title="(a) Clock-driven: start each action at its planned time t (if the AGV is free)",
               tmax=tmax, occ=occ_t, occ_bad=[(s, e) for s, e, _, _ in bad_t], marker=tau)
    s, e, r1, r2 = bad_t[0]
    label_pill(d, 70 + s * 78, b1.y1 + 8, f"collisions at {J}: " + ", then ".join(f"AGV-{a[1:]} with AGV-{b[1:]}" for _, _, a, b in bad_t),
               color=T.red, size=11.5, family="sans", border=T.red, anchor="start")
    sc1 = snapshot_scene(d, b1.x1 + 36, b1.y0 + 28, timed, tau, f"(a) at {tau:g} s: AGV-2 is in {J}; AGV-3 is still leaving, AGV-4 entering",
                         bad=True)
    b2 = gantt(d, 0, max(b1.y1, sc1.y1) + 46, adg,
               title="(b) ADG-driven: start an action when all its predecessors are done", tmax=tmax, occ=occ_a,
               marker=tau)
    b2x = adg[A["A3-2"]][0]
    label_pill(d, 70 + b2x * 78, b2.y1 + 8, f"A3-2 starts at {b2x:g} s: right after A2-2 (AGV-2 leaves {J}) completes",
               color=T.green, size=11.5, family="sans", border=T.green, anchor="start")
    snapshot_scene(d, b2.x1 + 36, b2.y0 + 28, adg, tau, f"(b) at {tau:g} s: AGV-2 still arriving; AGV-3 and AGV-4 hold back")
    rows = [
        ("A2-1 W41→W22", "one action as a bar: AGV-2's step 1, from W41 to W22; length = how long it took", T.violet),
        ("thick bar", "the disturbed action: A2-1 takes 2.5 s instead of 1 s", T.violet),
        ("A3-1 wait", "dashed bar: a planned wait", T.green),
        (f"at {J}", f"who is at the junction {J}: from arriving there until the move out has completed", T.teal),
        ("3.75 s", "the moment drawn in the garage view on the right", T.amber),
    ]
    key_panel(d, 0, b2.y1 + 40, b2.x1 + 36 + 14.2 * 21, "How to read the bars", rows)
    frame(d, title="One late AGV: clock-driven vs dependency-driven execution",
          subtitle=f"Same plan, same disturbance: A2-1 (AGV-2 drives W41 → {J}) takes 2.5 s instead of 1 s. Every "
                   "other action takes 1 s. In (a) AGV-3 and AGV-4 keep to the timetable and drive into the junction while "
                   "AGV-2 is still in it. In (b) nobody enters before the previous AGV has completely left.",
          badge_key="illustrative",
          legend=robot_legend([("line", T.red, f"two AGVs at {J}")]),
          footnote="Clock-driven: an action starts at max(planned t, end of the AGV's previous action). ADG-driven: "
                   "the original ADG of figure 2.4 (with waits); an action starts as soon as all incoming edges "
                   "come from completed actions. Timings are illustrative; computed by scripts/adg/adg.py.")
    return d


# --------------------------------------------------------------------------------------
@figure("09-type2-rule", "One type-2 dependency, step by step", DOC)
def type2_rule():
    d = Doc("09-type2-rule", "One type-2 dependency, step by step")
    a0, b0 = A["A1-0"], A["A3-0"]
    d.text(0, 0, "In the garage at t = 0", size=13, weight=600, fill=T.fg)
    G = Garage(d, 0, 18, 30, xlim=(25.6, 36.2), ylim=(15.6, 23.2))
    G.base(labels=True, axes=False, context=False, wp_below=True)
    for r, at, nxt in (("A1", "W18", "W22"), ("A3", "W13", "W18")):
        (xa, ya), (xb, yb) = G.P(at), G.P(nxt)
        connect(d, [(xa + 48, ya - 4), (xb + 48, yb + 14)], kind="flow", color=ex.COLOR[r], size=8, sw=2,
                dash="5 3")
        draw_robot(G, r, at, "w", label=f"AGV-{r[1:]}", label_side="right")
    gb = G.box
    d.text(0, gb.y1 + 22, "A1-0 = W18 → W22 and A3-0 = W13 → W18,", size=12, family="mono", fill=T.fg2)
    d.text(0, gb.y1 + 40, "both planned for the same step t = 0", size=12, family="mono", fill=T.fg2)
    # the rule table
    x = gb.x1 + 40
    rows = [
        ("candidate c = A1-0", "c.s = W18", "it LEAVES W18", ex.COLOR["A1"]),
        ("target    a = A3-0", "a.g = W18", "it ENTERS W18", ex.COLOR["A3"]),
        ("same place?", "c.s = a.g", "W18 = W18  ✓", T.teal),
        ("c no later?", "c.t ≤ a.t", "0 ≤ 0  ✓", T.teal),
        ("other AGV?", "c.R ≠ a.R", "AGV-1 ≠ AGV-3  ✓", T.teal),
    ]
    d.text(x, 0, "The rule (paper, Algorithm 1, line 5)", size=13, weight=600, fill=T.fg)
    for i, (k, f, v, c) in enumerate(rows):
        yy = 34 + i * 30
        d.rect(x, yy - 12, 470, 26, rx=6, fill=T.tint(c, 0.07, T.bg) if i >= 2 else T.card, layer="under")
        d.text(x + 12, yy + 1, k, size=12.5, family="mono", fill=T.fg2)
        d.text(x + 190, yy + 1, f, size=12.5, family="mono", fill=c)
        d.text(x + 320, yy + 1, v, size=12.5, family="mono", weight=600, fill=c)
    y = max(gb.y1 + 70, 200)
    d.text(0, y, "Result: one type-2 edge in the ADG", size=13, weight=600, fill=T.fg)
    Ln = Lanes(d, 0, y + 22, ["A1", "A3"], ex.COLOR, 1, col_w=200, label_w=96, lane_h=78, axis=False)
    Ln.action(a0)
    Ln.action(A["A1-1"], style="dim")
    Ln.action(b0)
    Ln.action(A["A3-1"], style="dim")
    Ln.type1(a0, A["A1-1"], color=T.tint(T.sky, 0.4, T.bg))
    Ln.type1(b0, A["A3-1"], color=T.tint(T.green, 0.4, T.bg))
    Ln.type2([(a0, b0)], style=lambda c, a: {"color": T.teal, "sw": 2.2})
    note(d, Ln.x0 + Ln.W + 30, y + 22, 400,
         "A1-0 → A3-0 reads: AGV-3 may start entering W18 only after AGV-1 has finished leaving W18. Both are planned "
         "for t = 0 (AGV-3 'follows' AGV-1), but if AGV-1 is late, AGV-3 now waits for it instead of driving into AGV-1's rear.",
         title="What the arrow means", accent=T.teal)
    rows = [
        ("c, a", "two actions: c is the candidate source of an edge, a the target", T.fg2),
        (".s .g .t .R", "start place, goal place, time step and AGV of an action, written <s, g, t, R>", T.fg2),
    ] + action_rows(wait=True, t1=True, t2=False)
    key_panel(d, 0, Ln.y1 + 26, Ln.W + 30 + 400, "Symbols in this figure", rows)
    frame(d, title="One type-2 dependency, step by step",
          subtitle="A type-2 edge always connects an AGV that LEAVES a place to a later AGV that ENTERS the same "
                   "place. The edge points from the leaver to the enterer: the enterer is the one that waits.",
          badge_key="illustrative",
          legend=[("arrow", T.teal, "type-2 dependency"), ("dasharrow", T.fg2, "move planned for this step")] +
          robot_legend()[0:1] + [robot_legend()[2]])
    return d


@figure("10-adg-full", "The full ADG of the worked example (Algorithm 1)", DOC)
def adg_full():
    d = Doc("10-adg-full", "The full ADG of the worked example")
    L = _lanes(d, 0, 0)
    for a in ex.ACTIONS:
        L.action(a)
    for u, v in sorted(ex.T1_FULL):
        L.type1(u, v)
    L.type2(ex.T2_FULL, style=lambda c, a: {"color": T.fg2})
    n1, n2 = len(ex.T1_FULL), len(ex.T2_FULL)
    key_panel(d, 0, L.y1 + 20, L.W, "How to read this graph", action_rows())
    frame(d, title="The full ADG of the worked example (original construction, Algorithm 1)",
          subtitle=f"{len(ex.ACTIONS)} actions ({sum(a.wait for a in ex.ACTIONS)} of them waits), "
                   f"{n1} type-1 edges along the lanes, {n2} type-2 edges between lanes. One lane per AGV, one "
                   "column per plan time step. Every edge is computed by scripts/adg/adg.py from the plan.",
          badge_key="illustrative",
          legend=robot_legend([("dashbox", T.fg2, "wait action")]),
          footnote="Columns are the plan's time steps, but execution ignores them: an action starts when every "
                   "arrow into it comes from a completed action.")
    return d
