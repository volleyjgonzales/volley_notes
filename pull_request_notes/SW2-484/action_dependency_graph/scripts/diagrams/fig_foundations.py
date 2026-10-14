"""Chapter 01 figures: the garage, the pipeline, routes, conflicts, the plan as a filmstrip and table."""
from __future__ import annotations

from components import chip, connect, frame, label_pill, note, num_badge
from garage import Garage, NODES, STALL_L, STALL_W, node_axis, heading_between
from keys import key_panel, names_rows
from registry import figure
from scene import draw_robot, draw_trays, plan_positions
from svgkit import BBox, Doc, text_width, wrap
import example as ex
from theme import S, T

DOC = "chapters/01-visual-foundations.md"
AR = "→"
J = ex.JUNCTION


def _callout(d, n, x, y, tx, ty, color=T.fg):
    """Numbered badge at (tx, ty) with a leader line to the point (x, y)."""
    d.line(tx, ty, x, y, stroke=T.tint(color, 0.7, T.bg), sw=1.2, layer="top")
    d.circle(x, y, 3, fill=color, layer="top")
    num_badge(d, tx, ty, n, color, r=12)


# --------------------------------------------------------------------------------------
@figure("01-garage", "The garage: what is in it, and the graph drawn on top", DOC)
def garage_scene():
    d = Doc("01-garage", "The garage and its graph")
    G = Garage(d, 0, 0, 34)
    G.base(axes=True, zones=True)
    draw_trays(G)
    pos = plan_positions(0)
    for r, st in pos.items():
        draw_robot(G, r, st["at"], st["heading"], label_side={"A1": "right", "A3": "right", "A4": "right",
                                                             "A2": "above"}[r])
    P = G.P
    items = [
        ("B21", (-1.6, 1.0), (-0.6, 2.0), "Customer bay B21", T.teal,
         "Where a customer drops off or collects a car. The thick edge on its east side is the door to the "
         "garage."),
        ("B21", (1.1, -0.3), (3.0, -2.6), "Car on tray T23, carried by AGV-2", T.violet,
         "The car is never driven inside. It sits on a tray; an AGV drives under the tray, lifts it and "
         "carries it. T23 belongs to stall P23."),
        ("W18", (-0.6, 0), (-3.4, 0.6), "AGV (here AGV-1)", T.sky,
         "A flat robot, about 2.2 m x 1.1 m. Chevron = its front: every Pecos node allows heading 90 (facing "
         "west), so AGVs drive sideways along the north-south aisle. Square plate = lift."),
        ("P19", (1.6, 0.3), (7.4, -1.2), "Tray T19 with a parked car in stall P19", T.amber,
         "Stalls touch along x: P19 can only be reached through W18 or P20."),
        ("P23", (1.8, 0), (2.4, 2.0), "Parking stall P23 (empty)", "#8FA3BF",
         "Storage place for one tray, 5.79 m x 2.21 m (the YAML's XL window). AGV-2 will bring the car here."),
        ("C14", (0, 0), (-1.3, -1.6), "AGV charger C14", "#FACC15",
         "Chargers sit 0.6 m from a stall node. None of our AGVs uses one."),
        ("W25", (0, 0), (-2.6, 0.9), "Waypoint W25", T.fg2,
         "A spot where an AGV can stop. Shaded bands are the drivable aisles."),
        (J, (0, 0), (-3.0, -0.9), "Junction W22", T.teal,
         "Where the aisle from bay B21 meets the north-south aisle. One of the two nodes where the YAML "
         "allows rotation."),
    ]
    for i, (v, (dx, dy), (ox, oy), title, col, _) in enumerate(items, 1):
        n = NODES[v]
        x, y = P((n.x + dx, n.y + dy))
        tx, ty = P((n.x + dx + ox, n.y + dy + oy))
        _callout(d, i, x, y, tx, ty, col)
    # glossary on the right
    b = G.box
    x0 = b.x1 + 28
    rows = [(str(i), f"{title}. {expl}", col) for i, (_, _, _, title, col, expl) in enumerate(items, 1)]
    k1 = key_panel(d, x0, b.y0, 400, "What you are looking at", rows)
    rows2 = [
        ("●  dot", "a vertex of the facility graph: a place an AGV can stand", T.fg2),
        ("—  line", "an edge: AGVs can drive directly between its two places", T.fg2),
        ("- -  dashed", "parts of the garage the worked example does not use", T.muted),
        ("names", "P parking stall, W waypoint, B bay, C charger, T tray. AGVs are numbered AGV-1 to AGV-4 "
                  "in the order in which they pass the junction W22.", T.fg2),
    ]
    key_panel(d, x0, k1.y1 + 16, 400, "The graph on top", rows2)
    frame(d, title="The garage: what is in it, and the graph drawn on top",
          subtitle="The Pecos garage, top-down, at the start of the worked example (t = 0). Everything the algorithms see is the graph of dots and lines; the rest is there so "
                   "you know what the dots stand for.",
          badge_key="yaml+hyp",
          footnote="Node positions, types and edges from sources/5675_pecos_combined.yaml (28 nodes, 37 edges), drawn "
                   "with the reference pack's assets. AGVs, trays and cars are hypothetical: the YAML has no "
                   "occupancy. Dashed outlines are the YAML's two sections. The 5 m bar gives the scale.")
    return d


# --------------------------------------------------------------------------------------
@figure("02-pipeline", "From a planning problem to robust execution", DOC)
def pipeline():
    d = Doc("02-pipeline", "From a planning problem to robust execution")
    cards = [
        ("Problem", T.fg2, "map, robots, goals",
         ["map: 9 places, 8 links", "AGV-3: W13 " + AR + " W25", "AGV-2: B21 " + AR + " P23 (car)"]),
        ("MAPF solver", T.sky, "e.g. CBS (chapter 02)",
         ["π_3 = W13 W18 W18 W22 W25", "= AGV-3's place at t = 0..4", "assumes everyone is on time"]),
        ("Actions", T.violet, "cut each path into steps",
         ["A3-1 (a wait):", "⟨s=W18, g=W18, t=1, R=AGV-3⟩", "A3-2 (a move):", "⟨s=W18, g=W22, t=2, R=AGV-3⟩"]),
        ("ADG construction", T.teal, "this paper: drop waits + SCP",
         ["A3-0 " + AR + " A3-2  same AGV", "A2-2 " + AR + " A3-2  AGV-2 leaves", "W22 before AGV-3 enters"]),
        ("Executor", T.green, "start a step when allowed",
         ["start A3-2 when A3-0", "and A2-2 report 'done'", "no clock needed"]),
    ]
    w, h, gap = 250, 178, 28
    boxes = []
    for i, (title, col, sub, lines) in enumerate(cards):
        x = i * (w + gap)
        hl = col == T.teal
        if hl:
            d.rect(x - 7, -7, w + 14, h + 14, rx=14, fill="none", stroke=T.teal, sw=1.2, dash="4 3")
        d.rect(x, 0, w, h, rx=10, fill=T.card, stroke=col, sw=1.6 if hl else 1.3)
        num_badge(d, x + 20, 22, i + 1, col)
        d.text(x + 38, 22, title, size=14.5, weight=600, fill=T.fg)
        d.text(x + 14, 48, sub, size=11.5, fill=T.muted)
        d.line(x + 14, 64, x + w - 14, 64, stroke=T.border_soft, sw=1)
        for k, ln in enumerate(lines):
            d.text(x + 14, 84 + k * 22, ln, size=11.5, family="mono", fill=T.fg2)
        boxes.append(BBox(x, 0, x + w, h))
    for a, b in zip(boxes, boxes[1:]):
        connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=T.fg2, size=9, sw=1.6)
    ex_b = boxes[-1]
    y = h + 52
    d.rect(ex_b.x0 + 20, y, w - 40, 40, rx=8, fill=T.tint(T.green, 0.08, T.bg), stroke=T.green, sw=1.2)
    d.text(ex_b.cx, y + 20, "AGV-1 \u2026 AGV-4", size=12.5, weight=600, fill=T.green, anchor="middle")
    connect(d, [(ex_b.cx - 30, ex_b.y1), (ex_b.cx - 30, y)], kind="flow", color=T.green, size=8,
            label="start", label_at=(ex_b.cx - 30, (ex_b.y1 + y) / 2))
    connect(d, [(ex_b.cx + 30, y), (ex_b.cx + 30, ex_b.y1)], kind="flow", color=T.green, size=8,
            label="done", label_at=(ex_b.cx + 30, (ex_b.y1 + y) / 2))
    by = h + 128
    for (i0, i1, lab, col) in ((0, 1, "PLANNING  ·  assumes a shared clock", T.sky),
                               (2, 3, "POST-PROCESSING  ·  plan → DAG", T.teal),
                               (4, 4, "EXECUTION", T.green)):
        x0, x1 = boxes[i0].x0, boxes[i1].x1
        d.path(f"M{x0} {by - 8} L{x0} {by} L{x1} {by} L{x1} {by - 8}", stroke=col, sw=1.3)
        d.text((x0 + x1) / 2, by + 18, lab, size=11, family="mono", weight=600, fill=col, anchor="middle",
               letter_spacing=0.5)
    note(d, boxes[2].x0, h + 40, 2 * w + gap - 10,
         "The paper changes only step 4. Steps 1-3 and 5 are background you need to read it.", accent=T.teal)
    # symbols used in this figure
    rows = [
        ("W13 B21 P23", "places in the garage of figure 1.1 (W waypoint, B bay, P parking stall)", T.fg2),
        ("AGV-1 \u2026 AGV-4", "the four AGVs, numbered in the order they pass the junction W22", T.fg2),
        ("π_3", "the path of AGV-3: the place AGV-3 is at, for each time step t = 0, 1, 2, ...", T.fg2),
        ("⟨s=…, g=…, t=…, R=…⟩", "an action, always written with its field names: s = start place, g = goal place, t = time step, R = which AGV. Example: <s=W18, g=W22, t=2, R=AGV-3> = AGV-3 drives from W18 to W22 during step 2. s = g means a wait",
         T.fg2),
        ("A3-2", "short name for an action: AGV-3's step 2", T.fg2),
        ("A2-2 " + AR + " A3-2", "a dependency: A3-2 may not start until A2-2 has completed", T.teal),
        ("DAG", "directed acyclic graph: arrows, no cycles. The ADG is one.", T.fg2),
    ]
    key_panel(d, 0, by + 44, boxes[-1].x1, "Symbols in this figure", rows)
    frame(d, title="From a planning problem to robust execution",
          subtitle="A MAPF (multi-agent path finding) solver produces timed paths. The ADG (action dependency "
                   "graph) turns them into 'who must finish before whom', so AGVs that run early or late still "
                   "never meet. The examples in each card come from the worked example.",
          badge_key="schematic",
          legend=[("box", T.teal, "contribution of Dunkel (2024)"), ("arrow", T.fg2, "data flow"),
                  ("arrow", T.green, "runtime messages")])
    return d


# --------------------------------------------------------------------------------------
@figure("03-three-graphs", "Three graphs, one example", DOC)
def three_graphs():
    from adgdraw import Lanes
    d = Doc("03-three-graphs", "Three graphs, one example")
    T_MAX = max(len(p) for p in ex.PATHS.values())

    def head(x, y, title, vtxt, etxt, col):
        d.text(x, y, title, size=14, weight=600, fill=col)
        d.rich(x, y + 24, [("vertex = ", "sans", 600, T.fg2), (vtxt, "sans", 400, T.fg2)], size=12)
        d.rich(x, y + 42, [("edge = ", "sans", 600, T.fg2), (etxt, "sans", 400, T.fg2)], size=12)
        return y + 66

    # (a) facility graph
    ya = head(0, 0, "(a) Facility graph", "a place", "you can drive between the two places", T.fg)
    sa = 52
    grid = {"B21": (0, 0), "W41": (1, 0), "W22": (2, 0), "P23": (3, 0), "W25": (2, -1), "W26": (3, -1),
            "W18": (2, 1), "W13": (2, 2), "W8": (2, 3)}
    gp = {v: (24 + gx * sa, ya + 24 + (gy + 1) * sa) for v, (gx, gy) in grid.items()}
    for u, v in ex.EDGES:
        d.line(*gp[u], *gp[v], stroke=T.border, sw=2)
    for v, (x, y) in gp.items():
        hl = v == J
        d.circle(x, y, 17, fill=T.card, stroke=T.teal if hl else T.fg2, sw=1.8 if hl else 1.2)
        d.text(x, y + 0.5, v, size=10, family="mono", weight=600, fill=T.teal if hl else T.fg, anchor="middle")
    d.text(0, ya + 24 + 5 * sa, "no time, no AGVs: just where", size=11.5, fill=T.muted)
    d.text(0, ya + 24 + 5 * sa + 16, "driving is possible", size=11.5, fill=T.muted)

    # (b) time-expanded graph = timed plan
    xb = 270
    yb = head(xb, 0, "(b) Timed plan = paths in the time-expanded graph", "a place at a time step, e.g. (W22, 2)",
              "stay put or drive to a neighbour during one step", T.fg)
    rows = ["W26", "W25", "P23", "W22", "W41", "B21", "W18", "W13", "W8"]
    rh, cw, lx = 32, 92, xb + 52
    Y = {v: yb + 30 + i * rh for i, v in enumerate(rows)}
    X = {t: lx + 20 + t * cw for t in range(T_MAX)}
    adj = {v: {v} for v in rows}
    for u, v in ex.EDGES:
        adj[u].add(v); adj[v].add(u)
    for t in range(T_MAX - 1):
        for u in rows:
            for v in adj[u]:
                d.line(X[t], Y[u], X[t + 1], Y[v], stroke="#243048", sw=1, layer="under")
    for t in range(T_MAX):
        d.text(X[t], yb + 10, f"t={t}", size=11, family="mono", fill=T.muted, anchor="middle")
        for v in rows:
            d.circle(X[t], Y[v], 3.2, fill=T.faint, layer="main")
    for v in rows:
        d.text(lx, Y[v], v, size=11, family="mono", fill=T.teal if v == J else T.fg2, anchor="end")
    offs = {"A1": -2, "A2": 2, "A3": -4, "A4": 4}
    for r in ex.ROBOTS:
        p = ex.PATHS[r]
        pts = [(X[t], Y[p[t]] + offs[r] * 0.6) for t in range(len(p))]
        d.polyline(pts, stroke=ex.COLOR[r], sw=2.6, radius=0, layer="edges")
        for (x, y) in pts:
            d.circle(x, y, 4.2, fill=ex.COLOR[r], layer="over")
    x22, y22 = X[2], Y[J]
    d.circle(x22, y22, 11, fill="none", stroke=T.teal, sw=1.6, dash="3 2", layer="top")
    xr = X[T_MAX - 1] + 24
    d.line(x22 + 11, y22 - 6, xr, Y["P23"] - 26, stroke=T.teal, sw=1, dash="3 3", layer="top")
    label_pill(d, xr, Y["P23"] - 26, "dot (W22, 2): AGV-2 is here", color=T.teal, size=10.5, family="sans",
               border=T.tint(T.teal, 0.6, T.bg), anchor="start")
    d.text(xb, Y[rows[-1]] + 30, "Grey: every possible move or wait. Coloured: the four paths the MAPF solver picked.",
           size=11.5, fill=T.muted)
    d.text(xb, Y[rows[-1]] + 46, "A horizontal segment is a wait. Collision-free = no two paths share a dot or "
           "cross on one edge.", size=11.5, fill=T.muted)

    # (c) ADG excerpt
    yc = Y[rows[-1]] + 90
    yc2 = head(0, yc, "(c) Action dependency graph", "an action = one step of one AGV, e.g. A2-1 (W41 \u2192 W22)",
               "the target may not start before the source has completed", T.fg)
    Ln = Lanes(d, 0, yc2 + 6, ["A1", "A2", "A3"], ex.COLOR, 3, col_w=176, label_w=92, lane_h=70, axis=True)
    acts = [ex.A[k] for k in ("A1-1", "A2-1", "A2-2", "A3-2", "A3-3")]
    for a in acts:
        Ln.action(a)
    Ln.type1(ex.A["A2-1"], ex.A["A2-2"])
    Ln.type1(ex.A["A3-2"], ex.A["A3-3"])
    Ln.type2([(ex.A["A1-1"], ex.A["A2-1"]), (ex.A["A2-2"], ex.A["A3-2"])], style=lambda c, a: {"color": T.fg2})
    note(d, Ln.x0 + Ln.W + 30, yc2 + 6, 330,
         "Same example, third view. There is no time axis any more (the columns are only for reading): an arrow "
         "just says 'first this, then that'. A1-1 \u2192 A2-1: AGV-2 may enter W22 only after AGV-1 has left it. "
         "Chapter 02 builds the whole graph.", title="Excerpt", accent=T.teal)
    frame(d, title="Three graphs, one example",
          subtitle="All three are graphs: dots joined by lines. What a dot and a line stand for is what differs. "
                   "(a) is the map, (b) is the map unrolled over time, with the plan as four paths through it, "
                   "(c) keeps only the order in which steps must happen.",
          badge_key="illustrative",
          legend=[("box", ex.COLOR[r], f"AGV-{r[1:]}") for r in ex.ROBOTS] +
                 [("ring", T.teal, "junction W22")])
    return d


# --------------------------------------------------------------------------------------
TEG_ROWS = ["W25", "W22", "W18", "W41"]           # row order chosen so that valid paths never cross visually
TEG_EDGES = [("W41", "W22"), ("W22", "W25"), ("W22", "W18")]
TEG_OK = {"A1": ["W18", "W22", "W25", "W25"], "A2": ["W41", "W41", "W22", "W18"]}
TEG_VERTEX = {"A1": ["W18", "W22", "W25", "W25"], "A2": ["W41", "W22", "W18", "W18"]}
TEG_SWAP = {"A1": ["W18", "W22", "W41", "W41"], "A2": ["W41", "W41", "W22", "W18"]}
TEG_SWAP_FIX = {"A1": ["W18", "W22", "W25", "W25", "W22", "W41"], "A2": ["W41", "W41", "W41", "W22", "W18", "W18"]}


def _teg_conflicts(P):
    a, b = P["A1"], P["A2"]
    n = max(len(a), len(b))
    at = lambda p, t: p[min(t, len(p) - 1)]
    vx = [(at(a, t), t) for t in range(n) if at(a, t) == at(b, t)]
    sw = [(at(a, t), at(a, t + 1), t) for t in range(n - 1)
          if at(a, t) != at(a, t + 1) and at(a, t) == at(b, t + 1) and at(b, t) == at(a, t + 1)]
    return vx, sw


assert _teg_conflicts(TEG_OK) == ([], [])
assert _teg_conflicts(TEG_VERTEX) == ([("W22", 1)], [])
assert _teg_conflicts(TEG_SWAP) == ([], [("W22", "W41", 1)])
assert _teg_conflicts(TEG_SWAP_FIX) == ([], [])
for _P in (TEG_OK, TEG_VERTEX, TEG_SWAP, TEG_SWAP_FIX):
    for _p in _P.values():
        for _u, _v in zip(_p, _p[1:]):
            assert _u == _v or (_u, _v) in TEG_EDGES or (_v, _u) in TEG_EDGES


def _teg(d, x, y, *, paths=None, edges="all", dots_label_col=None, out_from=None, vertex=None, swap=None,
         tmax=4, cw=78, rh=44):
    """Small time-expanded graph for the 4-place T junction. Returns (bbox, X, Y)."""
    lx = x + 36
    X = {t: lx + 22 + t * cw for t in range(tmax)}
    Y = {v: y + 26 + i * rh for i, v in enumerate(TEG_ROWS)}
    adj = {v: {v} for v in TEG_ROWS}
    for u, v in TEG_EDGES:
        adj[u].add(v); adj[v].add(u)
    for t in range(tmax):
        d.text(X[t], y + 4, f"t={t}", size=11, family="mono", fill=T.muted, anchor="middle")
    for v in TEG_ROWS:
        d.text(lx, Y[v], v, size=11, family="mono", fill=T.fg2, anchor="end")
    if edges != "none":
        col = "#2A3852" if edges == "all" else "#1F2A3F"
        for t in range(tmax - 1):
            for u in TEG_ROWS:
                for v in adj[u]:
                    d.line(X[t] + 4, Y[u], X[t + 1] - 4, Y[v], stroke=col, sw=1.1, layer="under")
    if out_from:
        v0, t0 = out_from
        for v in sorted(adj[v0], key=TEG_ROWS.index):
            connect(d, [(X[t0], Y[v0]), (X[t0 + 1], Y[v])], kind="flow", color=T.teal, size=7, sw=1.8)
    for t in range(tmax):
        for v in TEG_ROWS:
            d.circle(X[t], Y[v], 4, fill=T.faint, stroke=T.bg_deep, sw=1, layer="main")
    if dots_label_col is not None:
        t = dots_label_col
        for v in TEG_ROWS:
            label_pill(d, X[t] + 6, Y[v] + 14, f"({v}, {t})", color=T.fg2, size=9.5, family="mono",
                       border=T.border, anchor="start")
    offs = {"A1": -2.0, "A2": 2.0}
    for r, p in (paths or {}).items():
        pts = [(X[t], Y[p[t]] + offs[r]) for t in range(min(len(p), tmax))]
        d.polyline(pts, stroke=ex.COLOR[r], sw=2.8, radius=0, layer="edges")
        for (px, py) in pts:
            d.circle(px, py, 4.6, fill=ex.COLOR[r], stroke=T.bg_deep, sw=1, layer="over")
    if vertex:
        v, t = vertex
        d.circle(X[t], Y[v], 13, fill="none", stroke=T.red, sw=2.2, dash="4 3", layer="top")
    if swap:
        u, v, t = swap
        cx, cy = (X[t] + X[t + 1]) / 2, (Y[u] + Y[v]) / 2
        d.circle(cx, cy, 14, fill="none", stroke=T.red, sw=2.2, dash="4 3", layer="top")
    return BBox(x, y - 8, X[tmax - 1] + 10, Y[TEG_ROWS[-1]] + 10), X, Y


def _teg_floor(d, x, y, s, agvs, *, title=None, arrows=(), ring=None, cross=None, labels=None):
    """Garage crop around W22 with the four places of the mini example. agvs: [(robot, (x, y) or place, side)]."""
    if title:
        d.text(x, y, title, size=11.5, family="mono", weight=600, fill=T.muted)
        y += 12
    G = Garage(d, x, y, s, xlim=(25.2, 33.9), ylim=(18.2, 25.3))
    G.floor(grid=True)
    G.corridors()
    for u, v in TEG_EDGES:
        d.line(*G.P(u), *G.P(v), stroke="#55657F", sw=1.5, layer="edges")
    for v in TEG_ROWS:
        px, py = G.P(v)
        d.circle(px, py, 4.5, fill=T.teal if v == "W22" else T.fg2, stroke=T.bg_deep, sw=1.5, layer="over")
        dx, dy, anc = labels[v]
        lx, ly = px + dx, py + dy
        d.text(lx, ly, v, size=10.5, family="mono", fill=T.teal if v == "W22" else T.muted, anchor=anc,
               layer="labels")
    for r, at, side in agvs:
        if isinstance(side, tuple):      # explicit label position (dx, dy) from the AGV centre
            ax, ay = G.agv(at, None, heading="w", color=ex.COLOR[r], size=0.82)
            chip(d, ax + side[0], ay + side[1], f"AGV-{r[1:]}", ex.COLOR[r], anchor="start", size=10.5,
                 fill=T.tint(ex.COLOR[r], 0.25, T.bg_deep), layer="top")
        else:
            G.agv(at, f"AGV-{r[1:]}", heading="w", color=ex.COLOR[r], size=0.82, label_side=side)
    for r, a, b, off in arrows:
        (xa, ya), (xb, yb) = G.P(a), G.P(b)
        connect(d, [(xa + off[0], ya + off[1]), (xb + off[0], yb + off[1])], kind="flow", color=ex.COLOR[r],
                size=8, sw=2.2)
    if ring:
        px, py = G.P(ring)
        d.circle(px, py, 36, fill="none", stroke=T.red, sw=2.2, dash="5 4", layer="top")
    if cross:
        (xa, ya), (xb, yb) = G.P(cross[0]), G.P(cross[1])
        xm, ym = (xa + xb) / 2, (ya + yb) / 2
        d.path(f"M{xm - 10} {ym - 10} L{xm + 10} {ym + 10} M{xm + 10} {ym - 10} L{xm - 10} {ym + 10}",
               stroke=T.red, sw=2.6, layer="top")
    return G.box


@figure("04-time-expanded", "From timed paths to the time-expanded graph", DOC)
def time_expanded():
    d = Doc("04-time-expanded", "From timed paths to the time-expanded graph")
    C1, C2 = ex.COLOR["A1"], ex.COLOR["A2"]

    def step(x, y, n, title, col=T.fg):
        num_badge(d, x + 11, y, n, col)
        d.text(x + 30, y, title, size=14, weight=600, fill=T.fg)
        return y + 26

    def para(x, y, w, txt, size=12, fill=T.fg2):
        lines = wrap(txt, w, size, "sans")
        d.text_lines(x, y, lines, size=size, fill=fill, lh=1.45)
        return y + len(lines) * size * 1.45

    # ---- row 1: step 1, the timed paths --------------------------------------------------
    y1 = step(0, 0, 1, "Start from the timed paths: two AGVs at a T-junction")
    fb = _teg_floor(d, 0, y1 + 4, 30, [("A1", "W18", "left"), ("A2", "W41", "below")],
                    labels={"W22": (12, -14, "start"), "W41": (-34, 4, "end"), "W25": (-14, 2, "end"),
                            "W18": (34, 26, "start")},
                    arrows=[("A1", "W18", "W22", (52, 0)), ("A1", "W22", "W25", (52, 0)),
                            ("A2", "W41", "W22", (0, -40))])
    d.text(fb.x0, fb.y1 + 18, "the garage at t = 0, arrows: where each AGV is headed", size=11, fill=T.muted)
    # table
    tx, ty = fb.x1 + 40, y1 + 24
    cwt, rht, lw = 70, 38, 92
    for t in range(4):
        d.text(tx + lw + t * cwt + cwt / 2, ty, f"t = {t}", size=11.5, family="mono", fill=T.muted, anchor="middle")
    for i, r in enumerate(("A1", "A2")):
        yy = ty + 18 + i * (rht + 8)
        d.text(tx, yy + rht / 2, f"AGV-{r[1:]}", size=12.5, family="mono", weight=700, fill=ex.COLOR[r])
        for t, v in enumerate(TEG_OK[r]):
            xx = tx + lw + t * cwt
            wait = t > 0 and TEG_OK[r][t - 1] == v
            d.rect(xx + 3, yy, cwt - 6, rht, rx=7, fill=T.tint(ex.COLOR[r], 0.10, T.bg),
                   stroke=T.tint(ex.COLOR[r], 0.55, T.bg), sw=1.1, dash="4 3" if wait else None)
            d.text(xx + cwt / 2, yy + rht / 2, v, size=12, family="mono", weight=600, fill=T.fg, anchor="middle")
    yt = ty + 18 + 2 * (rht + 8) + 14
    yt = para(tx, yt, 4 * cwt + lw, "Each row is one AGV's timed path π: its place at t = 0, 1, 2, 3. "
              "A dashed cell repeats the place before it: a one-step wait.")
    yt = para(tx, yt + 8, 4 * cwt + lw, "AGV-1 drives north W18 → W22 → W25. AGV-2 waits at W41 for "
              "one step, crosses W22 behind AGV-1 and turns south into W18, which AGV-1 has left.")
    note(d, tx + 4 * cwt + lw + 30, y1 + 10, 330,
         "A table like this is easy to read but hard to reason about. The trick is to turn it into a graph in which "
         "'AGV-2 is at W22 at step 2' is a single dot, and a whole timed path is a line through dots. "
         "Steps 2 to 4 below do exactly that.", title="Why build a graph?", accent=T.teal)

    # ---- row 2: steps 2-4 ------------------------------------------------------------------
    y2 = max(fb.y1 + 30, yt) + 40
    pw, gap = 392, 22
    ph = 300
    heads = [
        (2, "Copy every place once per step",
         "One dot per (place, step): 4 places × 4 steps = 16 dots. Rows are places, columns are steps. "
         "The labels show the names of the t = 1 column."),
        (3, "Add an arrow for every possible step",
         "From each dot, one arrow to the next column: flat = wait in place, sloped = drive to a neighbour on "
         "the map. Teal: the 4 ways out of (W22, 1), since W22 has 3 neighbours plus waiting."),
        (4, "Draw each AGV's path through it",
         "A timed path becomes a line with one dot per column. These two lines never share a dot and never "
         "use one road in opposite directions at the same step, so the plan is collision-free."),
    ]
    for k, (n, title, txt) in enumerate(heads):
        x0 = k * (pw + gap)
        d.rect(x0, y2, pw, ph, rx=10, fill=T.tint(T.card, 0.5, T.bg), stroke=T.border, sw=1.1, layer="bg")
        yy = step(x0 + 14, y2 + 24, n, title, T.teal)
        kw = dict(dots_label_col=1, edges="none") if n == 2 else \
            dict(out_from=("W22", 1)) if n == 3 else dict(paths=TEG_OK, edges="faint")
        bb, X, Y = _teg(d, x0 + 30, yy + 10, **kw)
        para(x0 + 16, bb.y1 + 24, pw - 32, txt, size=11.5)
        if n == 3:
            for v, lab in (("W25", "move to W25"), ("W22", "wait at W22"), ("W18", "move to W18"),
                           ("W41", "move to W41")):
                label_pill(d, X[2] + 12, Y[v], lab, color=T.teal, size=10, family="sans",
                           border=T.tint(T.teal, 0.6, T.bg), anchor="start")
    for k in range(2):
        xa = k * (pw + gap) + pw
        connect(d, [(xa + 2, y2 + ph / 2), (xa + gap - 2, y2 + ph / 2)], kind="flow", color=T.teal, size=8, sw=1.6)

    # ---- row 3: the two problems -----------------------------------------------------------
    y3 = y2 + ph + 46
    qw = (3 * pw + 2 * gap - gap) / 2
    probs = [
        ("Problem 1: two paths share a dot = vertex conflict", TEG_VERTEX, dict(vertex=("W22", 1)),
         dict(agvs=[("A1", (NODES["W22"].x, NODES["W22"].y + 0.45), (44, -4)),
                    ("A2", (NODES["W22"].x, NODES["W22"].y - 0.45), (44, 4))], ring="W22",
              labels={"W22": (-30, 44, "end"), "W41": (-34, 4, "end"), "W25": (-14, 2, "end"),
                      "W18": (14, 4, "start")},
              title="the garage at t = 1"),
         "Suppose AGV-2 does not wait: π₂ = W41 W22 W18 W18. Both lines go through the dot (W22, 1): "
         "π₁(1) = π₂(1) = W22, two AGVs on one spot at the same step.",
         "Fix: AGV-2 waits one step at W41, which moves its line one column to the right (the plan of step 4)."),
        ("Problem 2: two paths cross on one edge = swap conflict", TEG_SWAP, dict(swap=("W22", "W41", 1)),
         dict(agvs=[("A1", "W22", "right"), ("A2", "W41", "left")], cross=("W41", "W22"),
              labels={"W22": (30, 34, "start"), "W41": (0, 52, "middle"), "W25": (-14, 2, "end"),
                      "W18": (14, 4, "start")},
              arrows=[("A1", "W22", "W41", (0, -30)), ("A2", "W41", "W22", (0, 30))],
              title="the garage at t = 1, about to move"),
         "Now AGV-1 heads west instead: π₁ = W18 W22 W41 W41. No dot is shared at any step, yet the "
         "lines form an X between t = 1 and t = 2: AGV-1 drives W22 → W41 while AGV-2 drives W41 → W22, "
         "head-on on the same road. In symbols: π₁(1) = π₂(2) and π₂(1) = π₁(2).",
         "Fix: one AGV must step aside. AGV-1 pulls into W25, lets AGV-2 pass, then continues: "
         "π₁ = W18 W22 W25 W25 W22 W41."),
    ]
    hmax = 0
    for k, (title, P, mark, floor, txt, fix) in enumerate(probs):
        x0 = k * (qw + gap)
        top = y3
        yy = top + 24
        d.text(x0 + 16, yy, title, size=14, weight=600, fill=T.fg)
        d.text(x0 + qw - 16, yy, "✗ forbidden", size=12, family="mono", weight=600, fill=T.red, anchor="end")
        bb, X, Y = _teg(d, x0 + 10, yy + 34, paths=P, edges="faint", **mark)
        fb2 = _teg_floor(d, bb.x1 + 26, yy + 26, 25, floor["agvs"], title=floor["title"],
                         ring=floor.get("ring"), cross=floor.get("cross"), arrows=floor.get("arrows", ()),
                         labels=floor["labels"])
        yb = max(bb.y1, fb2.y1) + 18
        yb = para(x0 + 16, yb, qw - 32, txt, size=12)
        yb = para(x0 + 16, yb + 8, qw - 32, fix, size=12, fill=T.green)
        hmax = max(hmax, yb - top + 14)
    for k in range(2):
        x0 = k * (qw + gap)
        d.rect(x0, y3, qw, hmax, rx=10, fill=T.tint(T.red, 0.04, T.bg), stroke=T.tint(T.red, 0.45, T.bg), sw=1.2,
               layer="bg")
    note(d, 0, y3 + hmax + 22, 3 * pw + 2 * gap,
         "Why the second check is needed: in the time-expanded graph the two swapping AGVs use two different arrows, "
         "(W22, 1) → (W41, 2) and (W41, 1) → (W22, 2), so 'no shared dot' and even 'no shared arrow' both "
         "pass. What they share is the road W22 – W41 of the garage, in opposite directions during one step. "
         "A MAPF solver therefore checks two things: dots (vertex conflicts) and crossing pairs of arrows on the same "
         "road (swap conflicts). Figure 1.6 shows both on the real aisle.", title="Two checks, not one", accent=T.amber)
    frame(d, title="From timed paths to the time-expanded graph",
          subtitle="A two-AGV example on four places around junction W22. Step 1 is the plan as a table; steps 2-4 "
                   "build the time-expanded graph and draw the plan as one path per AGV through it. The bottom row "
                   "shows the two ways two paths can collide.",
          badge_key="illustrative",
          legend=[("box", C1, "AGV-1 (path, dots it visits)"), ("box", C2, "AGV-2"),
                  ("dot", T.faint, "a (place, step) vertex"), ("line", T.teal, "possible step out of (W22, 1)"),
                  ("ring", T.red, "conflict")],
          footnote="Places are real Pecos nodes (W41, W22, W25, W18) but this two-AGV plan is a teaching example, "
                   "separate from the four-AGV worked example. AGVs face west (heading 90) and drive sideways.")
    return d


# --------------------------------------------------------------------------------------
@figure("05-facility", "The worked example: four routes through one junction", DOC)
def facility():
    d = Doc("05-facility", "Four routes through one junction")
    G = Garage(d, 0, 0, 34)
    G.base(axes=True, highlight=(J,), zones=True)
    draw_trays(G)
    offs = {"A1": -16, "A3": 16, "A4": 30, "A2": 16}
    for r in ex.ROBOTS:
        p = ex.PATHS[r]
        verts = [p[0]] + [v for u, v in zip(p, p[1:]) if v != u]
        G.route(verts, ex.COLOR[r], offset=offs[r], sw=3)
    for r, s in plan_positions(0).items():
        draw_robot(G, r, s["at"], s["heading"], label_side={"A1": "left", "A3": "left", "A4": "left",
                                                            "A2": "above"}[r])
    for r, v in (("A3", "W18"), ("A4", "W13")):
        x, y = G.P((25.2, NODES[v].y))
        label_pill(d, x, y, f"AGV-{r[1:]} waits here at t = 1 \u2192", color=ex.COLOR[r], size=10.5, family="sans",
                   border=T.tint(ex.COLOR[r], 0.6, T.bg))
    # abstract graph inset
    b = G.box
    x0, y0 = b.x1 + 30, b.y0
    d.text(x0, y0 + 6, "The same thing as a graph", size=13.5, weight=600, fill=T.fg)
    s = 48
    grid = {"B21": (0, 0), "W41": (1, 0), "W22": (2, 0), "P23": (3, 0), "W25": (2, -1), "W26": (3, -1),
            "W18": (2, 1), "W13": (2, 2), "W8": (2, 3)}
    gp = {v: (x0 + 22 + gx * s, y0 + 90 + gy * s) for v, (gx, gy) in grid.items()}
    for u, v in ex.EDGES:
        d.line(*gp[u], *gp[v], stroke=T.border, sw=2)
    for v, (x, y) in gp.items():
        hl = v == J
        d.circle(x, y, 15, fill=T.card, stroke=T.teal if hl else T.fg2, sw=1.8 if hl else 1.2)
        d.text(x, y + 0.5, v, size=9.5, family="mono", weight=600, fill=T.teal if hl else T.fg, anchor="middle")
    gy = max(y for _, y in gp.values()) + 34
    txt = ("The 9 vertices and 8 edges of the YAML graph that the example uses (of 28 and 37). This is all a "
           "MAPF solver and the ADG construction look at: places and which places connect.")
    for i, ln in enumerate(wrap(txt, 270, 12, "sans")):
        d.text(x0, gy + i * 17, ln, size=12, fill=T.fg2)
    rows = [(f"AGV-{r[1:]}", f"{' '.join(ex.PATHS[r])}  ({ex.ROLE[r]})", ex.COLOR[r]) for r in ex.ROBOTS]
    key_panel(d, x0, gy + 80, 300, "Routes (place at t = 0, 1, 2, ...)", rows)
    frame(d, title="The worked example: four routes through one junction",
          subtitle="AGV-1, AGV-3 and AGV-4 drive north up the aisle in a convoy (AGV-4 comes up from the sandbox_eng section and "
                   "turns west at the junction to queue in front of bay B21). AGV-2 carries a customer's car from bay "
                   "B21 east across the junction W22 into stall P23.",
          badge_key="yaml+hyp",
          legend=[("route", T.sky, "AGV-1"), ("route", T.violet, "AGV-2"), ("route", T.green, "AGV-3"), ("route", T.pink, "AGV-4"),
                  ("ring", T.teal, "junction W22: every route passes it")],
          footnote="AGVs are drawn at their start positions (t = 0); each arrowhead marks the goal. A repeated "
                   "place in a route is a one-step wait.")
    return d


# --------------------------------------------------------------------------------------
@figure("06-conflicts", "Vertex conflict, swap conflict and following", DOC)
def conflicts_fig():
    d = Doc("06-conflicts", "MAPF conflict types")
    panels = [
        ("Vertex conflict", T.red, "✗ forbidden", [("A1", "W22", "W18"), ("A3", "W13", "W18")],
         "Both AGVs are at W18 at t = 1."),
        ("Swap conflict", T.red, "✗ forbidden", [("A1", "W18", "W22"), ("A3", "W22", "W18")],
         "They exchange places along one edge: a head-on crash between W18 and W22."),
        ("Following", T.green, "✓ allowed in the plan", [("A1", "W18", "W22"), ("A3", "W13", "W18")],
         "AGV-3 enters W18 in the same step in which AGV-1 leaves it. Fine if both move in lock-step."),
    ]
    pw, gap = 330, 26
    for k, (title, col, verdict, moves, cap) in enumerate(panels):
        x0 = k * (pw + gap)
        d.rect(x0, 0, pw, 330, rx=10, fill=T.tint(col, 0.04, T.bg), stroke=T.tint(col, 0.45, T.bg), sw=1.2,
               layer="bg")
        d.text(x0 + 16, 24, title, size=14, weight=600, fill=T.fg)
        d.text(x0 + pw - 16, 24, verdict, size=12, family="mono", weight=600, fill=col, anchor="end")
        for ti in (0, 1):
            gx0 = x0 + 18 + ti * 172
            d.text(gx0 + 2, 52, f"t = {ti}", size=12, family="mono", weight=600, fill=T.muted)
            G = Garage(d, gx0, 64, 26, xlim=(28.6, 33.4), ylim=(15.9, 23.0))
            G.floor(grid=False)
            G.corridors()
            for u, v in (("W13", "W18"), ("W18", "W22")):
                d.line(*G.P(u), *G.P(v), stroke="#55657F", sw=1.5, layer="edges")
            for v in ("W13", "W18", "W22"):
                x, y = G.P(v)
                d.circle(x, y, 4.5, fill=T.fg2, stroke=T.bg_deep, sw=1.5, layer="over")
                d.text(x - 34, y + 4, v, size=10.5, family="mono", fill=T.muted, anchor="end", layer="labels")
            for i, (r, a, b) in enumerate(moves):
                v = a if ti == 0 else b
                same = ti == 1 and moves[0][2] == moves[1][2]
                xy = (NODES[v].x, NODES[v].y + (0.45 if (same and i == 0) else -0.45 if same else 0))
                G.agv(xy, None, heading="w", color=ex.COLOR[r], size=0.9)
                cx, cy = G.P(xy)
                d.text(cx + 40, cy + 4, f"AGV-{r[1:]}", size=11, family="mono", weight=700, fill=ex.COLOR[r], layer="top")
                if ti == 0:
                    (xa, ya), (xb, yb) = G.P(a), G.P(b)
                    sgn = 1 if yb > ya else -1
                    connect(d, [(xa + 86 + 8 * i, ya + 6 * sgn), (xb + 86 + 8 * i, yb - 12 * sgn)], kind="flow",
                            color=ex.COLOR[r], size=7, sw=1.8)
            if k == 0 and ti == 1:
                x, y = G.P("W18")
                d.circle(x, y, 32, fill="none", stroke=T.red, sw=2, dash="4 3", layer="top")
            if k == 1 and ti == 0:
                (xa, ya), (xb, yb) = G.P("W18"), G.P("W22")
                xm = xa + 90
                d.path(f"M{xm - 9} {ya - 14} L{xm + 9} {yb + 14}", stroke=T.red, sw=2.2, layer="top")
                d.path(f"M{xm + 9} {ya - 14} L{xm - 9} {yb + 14}", stroke=T.red, sw=2.2, layer="top")
        lines = wrap(cap, pw - 32, 12, "sans")
        d.text_lines(x0 + 16, 262, lines, size=12, fill=T.fg2, lh=1.45)
    note(d, 0, 352, 3 * pw + 2 * gap,
         "Following is what makes plain timed execution fragile: if AGV-1 is a little late, AGV-3 drives into W18 while "
         "AGV-1 is still there. The type-2 edges of an ADG exist exactly to order such hand-overs (AGV-1 must finish "
         "leaving before AGV-3 starts entering).", title="Why the third case matters later", accent=T.amber)
    frame(d, title="Vertex conflict, swap conflict and following",
          subtitle="Two AGVs on three waypoints of the Pecos north-south aisle, shown at two consecutive time steps. A valid MAPF plan "
                   "contains no vertex and no swap conflicts; following is normally permitted.",
          badge_key="illustrative",
          legend=[("box", T.sky, "AGV-1"), ("box", T.green, "AGV-3"), ("line", T.red, "conflict"),
                  ("dot", T.fg2, "waypoint")],
          footnote="Arrows next to the t = 0 frame: the move each AGV makes during the step to t = 1. AGVs face west "
                   "(Pecos heading 90) and drive sideways along the aisle.")
    return d


# --------------------------------------------------------------------------------------
@figure("07-filmstrip", "The plan, step by step", DOC)
def filmstrip():
    d = Doc("07-filmstrip", "The plan, step by step")
    T_MAX = max(len(p) for p in ex.PATHS.values())
    s = 29
    xl, yl = (20.0, 40.4), (11.6, 26.0)
    fw, fh = (xl[1] - xl[0]) * s, (yl[1] - yl[0]) * s
    gx, gy = 30, 80
    for t in range(T_MAX):
        col, row = t % 2, t // 2
        x0, y0 = col * (fw + gx), row * (fh + gy)
        d.text(x0, y0 + 2, f"t = {t}", size=14, family="mono", weight=700, fill=T.fg)
        G = Garage(d, x0, y0 + 18, s, xlim=xl, ylim=yl)
        G.base(labels=True, axes=False, context=True, highlight=(J,), wp_below=True)
        pos = plan_positions(t)
        skip = ("W26",) if t >= 3 else ()
        draw_trays(G, labels=False)
        occupants = [r for r, st in pos.items() if st["at"] == J]
        for r, st in pos.items():
            if st["next"]:
                (xa, ya), (xb, yb) = G.P(st["at"]), G.P(st["next"])
                connect(d, [(xa, ya), (xb, yb)], kind="flow", color=ex.COLOR[r], size=7, sw=1.8, dash="4 3")
        for r, st in pos.items():
            draw_robot(G, r, st["at"], st["heading"], label=f"AGV-{r[1:]}", label_side="above", size=1.0)
            if st["waiting"]:
                x, y = G.P(st["at"])
                chip(d, x + 22, y, "waits", ex.COLOR[r], anchor="start", size=9.5, layer="top")
        notes = []
        for r, st in pos.items():
            if st["waiting"]:
                notes.append(f"AGV-{r[1:]} waits at {st['at']}")
            elif st["next"]:
                notes.append(f"AGV-{r[1:]}: {st['at']} {AR} {st['next']}")
        cap = f"at {J}: {'AGV-' + occupants[0][1:] if occupants else 'nobody'}"
        d.text(x0 + fw, y0 + 2, cap, size=11.5, family="mono", fill=T.teal, anchor="end")
        txt = "next step: " + ("; ".join(notes) if notes else "everyone has arrived")
        for i, ln in enumerate(wrap(txt, fw, 11, "sans")):
            d.text(x0, y0 + 18 + fh + 16 + i * 15, ln, size=11, fill=T.fg2)
    frame(d, title="The plan, step by step",
          subtitle="The four routes of figure 1.5 with their timing: one frame per time step t. Dashed arrows show "
                   "the move each AGV makes before the next frame. Read across the junction W22 (ringed): "
                   "AGV-1 uses it at t = 1, AGV-2 at t = 2, AGV-3 at t = 3, AGV-4 at t = 4.",
          badge_key="illustrative",
          legend=[("box", T.sky, "AGV-1"), ("box", T.violet, "AGV-2 (with car)"), ("box", T.green, "AGV-3"),
                  ("box", T.pink, "AGV-4"), ("dasharrow", T.fg2, "move during the next step"),
                  ("box", T.amber, "tray"), ("ring", T.teal, "junction W22")])
    return d


# --------------------------------------------------------------------------------------
@figure("08-plan-table", "The plan as a table, and the visit order it implies", DOC)
def plan_table():
    d = Doc("08-plan-table", "The plan as a table")
    T_MAX = max(len(p) for p in ex.PATHS.values())
    cw, rh, lw = 98, 40, 110
    d.text(0, 0, "1 · The place π_R(t) of each AGV R at each time step t", size=13.5, weight=600, fill=T.fg)
    y0 = 26
    for t in range(T_MAX):
        d.text(lw + t * cw + cw / 2, y0 + 12, f"t = {t}", size=12, family="mono", fill=T.muted, anchor="middle")
    for i, r in enumerate(ex.ROBOTS):
        y = y0 + 30 + i * rh
        col = ex.COLOR[r]
        d.text(10, y + rh / 2, f"AGV-{r[1:]}", size=13, weight=600, fill=col)
        p = ex.PATHS[r]
        for t in range(T_MAX):
            x = lw + t * cw
            v = p[min(t, len(p) - 1)]
            done = t >= len(p)
            waiting = 0 < t < len(p) and p[t] == p[t - 1]
            hl = v == J and not done
            fill = T.tint(T.teal, 0.16, T.bg) if hl else (T.card if not done else T.bg)
            d.rect(x + 3, y + 3, cw - 6, rh - 6, rx=6, fill=fill,
                   stroke=(T.amber if waiting else (T.teal if hl else T.border_soft)),
                   sw=1.3 if (waiting or hl) else 1, dash="4 3" if waiting else None)
            d.text(x + cw / 2, y + rh / 2, v + (" goal" if done else ""), size=12 if not done else 10.5,
                   family="mono", weight=600 if hl else 400, fill=T.faint if done else (T.teal if hl else T.fg),
                   anchor="middle")
    ty = y0 + 30 + len(ex.ROBOTS) * rh + 18
    d.text(0, ty, "A dashed amber cell repeats the previous place: that step is a wait. Grey cells: the AGV has "
                  "arrived and stays at its goal.", size=11.5, fill=T.muted)
    y = ty + 44
    d.text(0, y, "2 · Read the table column-wise per place: who uses it, in which order", size=13.5,
           weight=600, fill=T.fg)
    rows = []
    for v in ("W13", "W18", J, "W41"):
        visits = []
        for r in ex.ROBOTS:
            p = ex.PATHS[r]
            ts = [t for t in range(len(p)) if p[t] == v]
            if ts:
                visits.append((ts[0], ts[-1], r, ts[-1] == len(p) - 1))
        visits.sort()
        if len(visits) > 1:
            rows.append((v, visits))
    for k, (v, visits) in enumerate(rows):
        yy = y + 40 + k * 52
        d.circle(22, yy, 18, fill=T.card, stroke=T.teal if v == J else T.fg2, sw=1.6)
        d.text(22, yy, v, size=11, family="mono", weight=600, fill=T.teal if v == J else T.fg, anchor="middle")
        x = 70
        prev = None
        for (t0, t1, r, stays) in visits:
            col = ex.COLOR[r]
            lab = f"AGV-{r[1:]}  t={t0}" + (f"..{t1}" if t1 > t0 else "") + ("  (stays)" if stays else "")
            w = text_width(lab, 12, "mono", 600) + 22
            if prev is not None:
                connect(d, [(prev, yy), (x - 4, yy)], kind="flow", color=T.fg2, size=8, sw=1.4)
            d.rect(x, yy - 14, w, 28, rx=14, fill=T.tint(col, 0.16, T.bg), stroke=col, sw=1.3)
            d.text(x + 11, yy, lab, size=12, family="mono", weight=600, fill=col)
            prev = x + w
            x += w + 54
    note(d, 660, y + 22, 330,
         "Each arrow here, 'the earlier AGV must have left before the next one enters', becomes a type-2 edge of "
         "the action dependency graph in chapter 02.", title="Where this is going", accent=T.teal)
    frame(d, title="The plan as a table, and the visit order it implies",
          subtitle="The same plan as figure 1.7, written as the MAPF solution Π that the algorithms work with. "
                   "Row = one AGV's path; column = one time step. Collision-free: no column contains the same place "
                   "twice, and no two AGVs swap places between neighbouring columns.",
          badge_key="illustrative",
          legend=[("box", T.teal, "AGV is at junction W22"), ("dashbox", T.amber, "wait (same place as before)"),
                  ("arrow", T.fg2, "leaves before the next AGV enters")],
          footnote="π_R(t) reads 'the place of AGV R at time step t'; Π (capital pi) is the set of all "
                   "four paths.")
    return d
