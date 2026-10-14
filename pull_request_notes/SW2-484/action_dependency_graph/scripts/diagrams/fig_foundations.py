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
         ["A3-1 = ⟨W18, W18, 1, 3⟩  wait", "A3-2 = ⟨W18, W22, 2, 3⟩  move", "⟨start, goal, t, AGV⟩"]),
        ("ADG construction", T.teal, "this paper: drop waits + SCP",
         ["A3-0 " + AR + " A3-2  same AGV", "A2-2 " + AR + " A3-2  AGV-2 leaves", "W22 before AGV-3 enters"]),
        ("Executor", T.green, "start a step when allowed",
         ["start A3-2 when A3-0", "and A2-2 report 'done'", "no clock needed"]),
    ]
    w, h, gap = 250, 158, 28
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
        ("⟨s,g,t,R⟩", "an action: AGV number R goes from place s to place g during step t (s = g: a wait)",
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
@figure("03-facility", "The worked example: four routes through one junction", DOC)
def facility():
    d = Doc("03-facility", "Four routes through one junction")
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
@figure("04-conflicts", "Vertex conflict, swap conflict and following", DOC)
def conflicts_fig():
    d = Doc("04-conflicts", "MAPF conflict types")
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
@figure("05-filmstrip", "The plan, step by step", DOC)
def filmstrip():
    d = Doc("05-filmstrip", "The plan, step by step")
    T_MAX = max(len(p) for p in ex.PATHS.values())
    s = 22
    xl, yl = (19.9, 40.6), (11.4, 25.2)
    fw, fh = (xl[1] - xl[0]) * s, (yl[1] - yl[0]) * s
    gx, gy = 28, 76
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
          subtitle="The four routes of figure 1.3 with their timing: one frame per time step t. Dashed arrows show "
                   "the move each AGV makes before the next frame. Read across the junction W22 (ringed): "
                   "AGV-1 uses it at t = 1, AGV-2 at t = 2, AGV-3 at t = 3, AGV-4 at t = 4.",
          badge_key="illustrative",
          legend=[("box", T.sky, "AGV-1"), ("box", T.violet, "AGV-2 (with car)"), ("box", T.green, "AGV-3"),
                  ("box", T.pink, "AGV-4"), ("dasharrow", T.fg2, "move during the next step"),
                  ("box", T.amber, "tray"), ("ring", T.teal, "junction W22")])
    return d


# --------------------------------------------------------------------------------------
@figure("06-plan-table", "The plan as a table, and the visit order it implies", DOC)
def plan_table():
    d = Doc("06-plan-table", "The plan as a table")
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
          subtitle="The same plan as figure 1.5, written as the MAPF solution Π that the algorithms work with. "
                   "Row = one AGV's path; column = one time step. Collision-free: no column contains the same place "
                   "twice, and no two AGVs swap places between neighbouring columns.",
          badge_key="illustrative",
          legend=[("box", T.teal, "AGV is at junction W22"), ("dashbox", T.amber, "wait (same place as before)"),
                  ("arrow", T.fg2, "leaves before the next AGV enters")],
          footnote="π_R(t) reads 'the place of AGV R at time step t'; Π (capital pi) is the set of all "
                   "four paths.")
    return d
