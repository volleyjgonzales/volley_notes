"""Pecos facility figures (real YAML geometry) and the DiscreteGarageState bridge."""
from __future__ import annotations

from contextlib import nullcontext

from components import chip, connect, frame, label_pill, note, num_badge, uml_class
from facility import Map, NODES, EDGES, Scene, STALL_L, STALL_W, C_BAY, C_CHG, C_PARK, C_WP
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

FULL_X = (20.0, 46.6)
FULL_Y = (6.4, 25.6)

MAP_LEGEND = [("box", C_PARK, "parking node · XL stall 5.79 × 2.21 m"), ("box", C_BAY, "bay (customer handoff)"),
              ("ring", C_CHG, "AGV charger"), ("dot", C_WP, "waypoint"), ("line", "#55657F", "graph edge"),
              ("fill", "#18233A", "waypoint corridor"), ("dashbox", "#3B4A63", "YAML section")]


def _event_strip(d: Doc, x0, y0, items, *, width=None, title=None, reveal=None, active=None):
    """Horizontal chain of event cards: items = [(num, color, kind, text)].
    reveal: optional list of step indexes, one per card; card i (and the arrow into it) appears at reveal[i]
    and gets a highlight ring at exactly that step.
    active: optional list (one per card) of steps or (first, last) ranges at which the card is outlined
    instead (the playback step that executes it)."""
    gap = 30
    pad = 12
    ws = [max(text_width(t, 12, "mono"), text_width(k, 11, "mono", 600)) + 2 * pad for _, _, k, t in items]
    if width:
        extra = (width - sum(ws) - gap * (len(ws) - 1)) / len(ws)
        ws = [w + max(0, extra) for w in ws]
    x = x0
    if title:
        with d.at(reveal[0]) if reveal else nullcontext():
            d.text(x0, y0 - 24, title, size=12, family="mono", fill=T.muted)
    boxes = []
    for i, ((n, col, kind, txt), w) in enumerate(zip(items, ws)):
        with d.at(reveal[i]) if reveal else nullcontext():
            d.rect(x, y0, w, 58, rx=8, fill=T.card, stroke=col, sw=1.4)
            if n is not None:
                num_badge(d, x, y0, n, col, r=10)
            d.text(x + pad + (6 if n is not None else 0), y0 + 18, kind, size=11, family="mono", weight=600, fill=col)
            d.text(x + pad, y0 + 40, txt, size=12, family="mono", fill=T.fg)
        if reveal or active:
            hl = (active[i] if active else reveal[i])
            with (d.at(*hl) if isinstance(hl, tuple) else d.only(hl)):
                d.rect(x - 5, y0 - 5, w + 10, 68, rx=11, fill="none", stroke=col, sw=2.2, layer="bg")
        boxes.append(BBox(x, y0, x + w, y0 + 58))
        x += w + gap
    for i, (a, b) in enumerate(zip(boxes, boxes[1:])):
        with d.at(reveal[i + 1]) if reveal else nullcontext():
            connect(d, [(a.x1 + 3, a.cy), (b.x0 - 2, a.cy)], kind="flow", color=T.muted, size=8, sw=1.6)
    return boxes


def _ring(d: Doc, m: Map, nid, color, r=24, label=None, dx=0, dy=0):
    """Dashed ring around a node (an occupied exit, a pick-up point ...), optional small label below it."""
    x, y = m.P(nid)
    d.circle(x, y, r, fill="none", stroke=color, sw=1.8, dash="5 4", layer="over")
    if label:
        d.text(x + dx, y + r + 10 + dy, label, size=10.5, family="mono", weight=600, fill=color, anchor="middle",
               halo=T.bg_deep, halo_w=3, layer="top")


@figure("15_facility_topology", "Pecos facility graph", "01-software-background.html")
def facility_topology():
    d = Doc("15_facility_topology", "Pecos facility topology",
            "Top-down plan of the 5675 Pecos layout: 28 nodes and 37 undirected edges at their YAML coordinates.")
    m = Map(d, 0, 0, 35, FULL_X, FULL_Y)
    m.base(labels=True)
    # orientation hint: heading 90 = west
    hx, hy = m.X(21.0), m.Y(8.0)
    d.rect(hx - 12, hy - 18, 70 + text_width("heading 90", 10.5, "mono") + 14, 36, rx=8, fill=T.bg,
           stroke=T.border_soft, sw=1, layer="labels")
    d.line(hx + 52, hy, hx + 8, hy, stroke=T.fg2, sw=2, layer="labels")
    d.arrowhead((hx + 2, hy), (hx + 52, hy), kind="filled", color=T.fg2, size=8, layer="labels")
    d.text(hx + 58, hy, "heading 90", size=10.5, family="mono", fill=T.fg2, layer="top")
    d.text(hx - 4, hy + 30, "GaragePose heading 90 points west (-x)", size=10.5, fill=T.muted, layer="top")
    frame(d, title="Pecos facility topology",
          subtitle="28 nodes and 37 undirected edges at their 5675_pecos_combined.yaml coordinates. Edges are "
                   "allowed node connections, not aisle widths or collision envelopes. No VRC in this layout.",
          badge_key="yaml", legend=MAP_LEGEND, legend_title="Map")
    return d


@figure("15_facility_scenario", "Pecos overview with hypothetical occupancy", "01-software-background.html")
def facility_scenario():
    d = Doc("15_facility_scenario", "Pecos overview with a hypothetical scene",
            "Pecos layout with an illustrative AGV-1 at charger C10 and trays at P3, P15, P17 and P20. Root tray R "
            "at P17 must reach bay B21, but K at P15, T20 at P20 and the dead-end charger C16 block every exit; "
            "a last step previews what has to happen: K moves aside first.")
    s0 = d.step("The real Pecos geometry from the YAML: two sections, parking stalls P, customer bays B7 and B21, "
                "AGV chargers C, waypoints W and the graph edges between them. Nothing is occupied yet.")
    s1 = d.step("A job asks for the car on tray R, so R is the root tray: it sits at P17 and must reach bay B21 "
                "(dashed: the requested move, not a planned route).")
    s2 = d.step("R cannot leave. P17 connects only to P15, P20 and charger C16: K (empty) is at P15, T20 (with a "
                "car) is at P20, and C16 is a dead end. K and T20 are blocking trays, so one of them must move first.")
    s3 = d.step("The rest of the scene: AGV-1 waits at charger C10, and tray T15 with a payload sits at P3. "
                "The approach and blocking-tray figures reuse this scene.")
    s4 = d.step("What has to happen (preview): AGV-1 leaves C10 via W9 and W8 and waits at W13, next to the "
                "blockers. Before R can leave, K must be moved out of the way, for example to the free stall P19 "
                "(dashed amber); the blocking-tray figure plays that plan move by move.")
    m = Map(d, 0, 0, 35, FULL_X, FULL_Y)
    m.base(labels=True, dim=True)
    # mobile things: one Scene per reveal group, each visible from the step that introduces it
    sc_r = Scene(m)
    sc_r.tray("R · root", 17, payload=True, emphasis=True)
    sc_k = Scene(m)
    sc_k.tray("K · blocker", 15)
    sc_k.tray("T20", 20, payload=True)
    sc_a = Scene(m)
    sc_a.tray("T15", 3, payload=True)
    sc_a.agv("AGV-1", 10, heading=90, label_side="above")
    sc_a.drive(s4, "AGV-1", [10, 9, 8, 13], preview=False)
    with d.at(s1):
        sc_r.draw()
        m.route([17, 15, 13, 18, 22, 41, 21], T.violet, sw=2.4, dash="7 6", offset=(0, -14))
        x, y = m.P(41)
        label_pill(d, (x + m.P(22)[0]) / 2, y - 34, "job: R  P17 -> B21", color=T.violet, bg=T.bg_deep, border=T.violet, size=11)
    with d.at(s2):
        sc_k.draw()
    with d.at(s2, s3):
        _ring(d, m, 15, T.red, r=20)
        _ring(d, m, 20, T.red, r=20)
    with d.at(s2):
        _ring(d, m, 16, T.red, r=20)
        x, y = m.P(16)
        label_pill(d, x, y + 34, "dead end", color=T.red, bg=T.bg_deep, border=T.red, size=10.5, layer="top")
    with d.at(s3):
        sc_a.draw()
    with d.at(s4):
        m.route([15, 19], T.amber, sw=3, dash="7 5", offset=(-16, 0), layer="top")
        x19, y19 = m.P(19)
        label_pill(d, x19 - 2, y19 + 32, "K moves first", color=T.amber, bg=T.bg_deep, border=T.amber, size=10.5,
                   anchor="start")
    frame(d, title="Pecos overview with a hypothetical scene",
          subtitle="Node positions and edges are real; AGV-1, the trays and payloads are teaching stand-ins, not "
                   "occupancy supplied by the YAML. The same scene is reused by the approach and blocking-tray figures.",
          badge_key="yaml+hyp",
          legend=[("box", T.amber, "tray (hypothetical)"), ("box", T.pink, "payload / vehicle"),
                  ("box", T.green, "AGV (hypothetical)"), ("dasharrow", T.violet, "requested move (job)"),
                  ("dasharrow", T.amber, "blocker must move first"),
                  ("ring", T.red, "occupied exit / dead end")] + MAP_LEGEND[:4], legend_title="Scene")
    return d


@figure("15_agv_approach_and_pickup", "AGV approach example", "01-software-background.html")
def agv_approach():
    d = Doc("15_agv_approach_and_pickup", "AGV approach, lift, carry and lower",
            "AGV-1 leaves charger C10 and drives 10 -> 9 -> 11 -> 6 -> 3 under the empty stall P6 to reach tray T15 "
            "at P3, lifts it, carries it to an example destination P2 and lowers it.")
    path = [10, 9, 11, 6, 3]
    caps = [
        "Start: hypothetical AGV-1 is unloaded at charger C10; tray T15 with a payload is parked at P3. "
        "The dashed arrow is the first edge it will drive.",
        "AGV-1 drives C10 -> W9, onto the waypoint corridor. Only graph edges can be used.",
        "AGV-1 drives W9 -> W11 along the corridor.",
        "AGV-1 drives W11 -> P6. The stall is empty and an unloaded AGV is low enough to pass under parked trays "
        "anyway.",
        "AGV-1 drives P6 -> P3 and stops under T15. The whole unloaded drive C10 -> P3 is one AgvMove (pose) "
        "event; the next event is the lift.",
        "Lift: AGV-1 raises T15 (with its car) off the floor. Lifting is its own event, separate from driving. "
        "The amber arrow is the carry that follows.",
        "Carry: the TrayMove takes T15 from P3 to its destination, here the free stall P2 as an example; T15 "
        "rides on AGV-1.",
        "Lower: AGV-1 sets T15 down at P2 and is free again. Move, lift, carry, lower is the pattern AGV "
        "assignment wraps around every TrayMove.",
    ]
    st = [d.step(c) for c in caps]
    m = Map(d, 0, 0, 58, (33.6, 46.6), (6.6, 15.2))
    m.base(labels=True, zones=False)
    sc = Scene(m)
    sc.tray("T15", 3, payload=True, emphasis=True, chip_pos="tr")
    sc.agv("AGV-1", 10, heading=90, label_side="left")
    # one edge per step; Scene draws the dashed preview of each edge in the step before
    for k in (1, 2, 3, 4):
        sc.drive(k, "AGV-1", path[k - 1:k + 1], trail=False)
    sc.lift(5, "AGV-1")
    sc.drive(6, "AGV-1", [3, 2], preview=False, trail=False)
    sc.lower(7, "AGV-1")
    sc.draw()
    # start marker after the AGV left C10
    x10, y10 = m.P(10)
    with d.at(1):
        d.rect(x10 - 1.1 * m.s, y10 - 0.55 * m.s, 2.2 * m.s, 1.1 * m.s, rx=0.3 * m.s, fill="none",
               stroke=T.green, sw=1.4, dash="5 4", layer="main")
        chip(d, x10, y10 - 0.55 * m.s - 16, "start @ C10", T.green, anchor="middle", size=10.5,
             fill=T.tint(T.green, 0.25, T.bg_deep), layer="top")
    # unloaded route driven so far: partial per step, full from step 4
    for k in (1, 2, 3):
        with d.only(k):
            m.route(path[:k + 1], T.green, sw=4.5)
    with d.at(4):
        m.route(path, T.green, sw=4.5)
    x3, y3 = m.P(3)
    x2, y2 = m.P(2)
    with d.only(4):
        d.circle(x3, y3, 30, fill="none", stroke=T.green, sw=1.6, dash="5 4", layer="over")
        label_pill(d, x3 - 40, y3 + 76, "next event: AGV-1 lift at P3", color=T.green, bg=T.bg_deep,
                   border=T.green, size=11.5)
    with d.at(5):
        label_pill(d, x3 + 10, y3 + 76, "AGV-1 lift @ P3", color=T.green, bg=T.bg_deep, border=T.green,
                   size=11.5)
    # carry route (loaded), offset below the stall row: previewed at the lift, kept afterwards
    with d.at(5):
        m.route([3, (NODES[2].x + 1.3, NODES[2].y)], T.amber, sw=4.5, offset=(0, 30), layer="top")
    with d.at(7):
        label_pill(d, x2 + 10, y2 + 76, "AGV-1 lower @ P2", color=T.green, bg=T.bg_deep, border=T.green,
                   size=11.5)
    b = m.box
    _event_strip(d, b.x0, b.y1 + 72, [
        (None, T.green, "AgvMove · pose", "AGV-1: C10 -> P3 unloaded"),
        (None, T.green, "AgvMove · lift", "AGV-1 lift T15 at P3"),
        (None, T.amber, "TrayMove", "T15: P3 -> P2 on AGV-1"),
        (None, T.green, "AgvMove · lift", "AGV-1 lower T15 at P2"),
    ], width=b.w, title="the same intent as abstract events (simplified)", reveal=[4, 5, 6, 7])
    frame(d, title="AGV approach, lift, carry and lower",
          subtitle="Hypothetical AGV-1 starts at charger C10 and reaches tray T15 at P3 via the connected nodes "
                   "10 -> 9 -> 11 -> 6 -> 3, then lifts it, carries it to an example destination P2 and lowers it. "
                   "Driving, lifting, carrying and lowering are separate events; the route is a graph walk, "
                   "not a recorded run.",
          badge_key="yaml+hyp",
          legend=[("dasharrow", T.green, "next edge (preview)"), ("route", T.green, "unloaded AGV route"),
                  ("route", T.amber, "loaded carry"), ("box", T.amber, "tray (hypothetical)"),
                  ("box", T.pink, "payload"), MAP_LEGEND[0], MAP_LEGEND[2], MAP_LEGEND[3]], legend_title="Scene")
    return d


@figure("15_blocking_tray_move", "Blocking tray example", "01-software-background.html")
def blocking():
    d = Doc("15_blocking_tray_move", "A blocking tray must move first",
            "Root tray R at P17 must reach bay B21. Its exits via P15 and P20 are occupied, so AGV-1 first "
            "relocates blocker K from P15 to P19, then fetches R and carries it to B21; each move is previewed "
            "as a numbered arrow and played in the next step.")
    caps = [
        "Start: root tray R at P17 must reach bay B21. P17 connects only to P15, P20 and charger C16; K holds "
        "P15, T20 holds P20 and C16 is a dead end, so R is boxed in. AGV-1 waits at W13.",
        "① AgvMove AGV-1 (dashed arrow): the first move of the plan is an unloaded drive W13 -> P15, under the "
        "blocker K.",
        "AGV-1 drives W13 -> P15 and lifts K. Next, ② TrayMove K: carry K to the free stall P19, off R's way out.",
        "AGV-1 carries K from P15 to P19 (②); P15 is now free. Next, ③ AgvMove AGV-1: lower K and drive back "
        "unloaded P19 -> P15 -> P17. ③ must wait for ②, because P15 was occupied until then.",
        "AGV-1 lowers K at P19, drives P19 -> P15 -> P17 and lifts R. Next, ④ TrayMove R: carry R out via P15, "
        "W13, W18, W22 and W41 into bay B21.",
        "AGV-1 carries R along ④ into bay B21. The BayTransition at B21 depends on ④.",
        "AGV-1 lowers R in B21 and the bay switches to retrieve, handing the car to the customer. The whole plan "
        "at once: the four numbered moves in the order the planner must respect, from the starting positions "
        "(dashed) to where the plan leaves every tray.",
    ]
    st = [d.step(c) for c in caps]
    S0, S1, S2, S3, S4, S5, S6 = st
    m = Map(d, 0, 0, 37, (20.0, 46.6), (14.9, 25.3))
    m.base(labels=True, zones=False)
    sc = Scene(m)
    sc.tray("T20", 20, payload=True)
    sc.tray("R · root", 17, payload=True, emphasis=True)
    sc.tray("K · blocker", 15)
    sc.agv("AGV-1", 13, heading=90, label_side="right")
    # the plan, played: each drive glides in the step after its numbered arrow appears
    sc.drive(S2, "AGV-1", [13, 15], preview=False, trail=False)
    sc.lift(S2, "AGV-1")
    sc.drive(S3, "AGV-1", [15, 19], preview=False, trail=False)
    sc.lower(S4, "AGV-1")
    sc.drive(S4, "AGV-1", [19, 15, 17], preview=False, trail=False)
    sc.lift(S4, "AGV-1")
    sc.drive(S5, "AGV-1", [17, 15, 13, 18, 22, 41, 21], preview=False, trail=False)
    sc.lower(S6, "AGV-1")
    sc.draw()
    # ghost of K's destination until K arrives there
    x19, y19 = m.P(19)
    w, h = (STALL_L - 0.5) * m.s, (STALL_W - 0.32) * m.s
    with d.at(S0, S2):
        d.rect(x19 - w / 2, y19 - h / 2, w, h, rx=6, fill="none", stroke=T.amber, sw=1.4, dash="5 4",
               layer="main")
        d.text(x19 - w / 2 + 10, y19 + h / 2 - 12, "K target", size=11, family="mono", fill=T.amber,
               halo=T.bg_deep, halo_w=3)
    # poster: dashed ghosts of the starting positions
    with d.at(S6):
        for nid, lab in ((15, "K start"), (17, "R start")):
            x, y = m.P(nid)
            d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill="none", stroke=T.amber, sw=1.4, dash="5 4",
                   layer="main")
            d.text(x + w / 2 - 10, y - h / 2 + 14, lab, size=11, family="mono", fill=T.amber, anchor="end",
                   halo=T.bg_deep, halo_w=3)
    # blocked exits of P17 at the start
    with d.only(S0):
        for nid in (15, 20, 16):
            _ring(d, m, nid, T.red, r=20)
        label_pill(d, m.X(20.6), m.Y(16.0), "every exit of P17 is blocked", color=T.red, bg=T.bg_deep,
                   border=T.red, size=11, anchor="start")
    # numbered routes: previewed one step before AGV-1 plays them, then kept (cumulative)
    with d.at(S1):
        m.route([13, 15], T.green, sw=2.6, dash="7 6", offset=(0, -17), num=1, num_at=0, layer="top")
    with d.at(S2):
        m.route([15, 19], T.amber, sw=4.5, offset=(-16, 0), num=2, num_at=0, layer="top")
    with d.at(S3):
        m.route([19, 15, 17], T.green, sw=2.6, dash="7 6", offset=(16, -5), num=3, num_at=1, layer="top")
    with d.at(S4):
        m.route([17, 15, 13, 18, 22, 41, 21], T.green, sw=4.5, offset=(0, 14), num=4, num_at=0, layer="top")
    with d.at(S6):
        x21, y21 = m.P(21)
        d.rect(m.X(20.3), m.Y(23.6), m.X(25.95) - m.X(20.3), m.Y(19.9) - m.Y(23.6), rx=10, fill="none",
               stroke=T.violet, sw=2.2, dash="6 4", layer="over")
        label_pill(d, x21, m.Y(19.4), "B21: retrieve", color=T.violet, bg=T.bg_deep, border=T.violet, size=11)
    b = m.box
    _event_strip(d, b.x0, b.y1 + 72, [
        (1, T.green, "AgvMove AGV-1", "W13 -> P15, lift K"),
        (2, T.amber, "TrayMove K", "P15 -> P19"),
        (3, T.green, "AgvMove AGV-1", "P19 -> P17, lift R"),
        (4, T.green, "TrayMove R", "P17 -> B21"),
        (None, T.violet, "BayTransition", "B21: retrieve"),
    ], width=b.w, title="dependency chain the planner must respect (simplified)", reveal=[S1, S2, S3, S4, S5],
        active=[S2, S3, S4, S5, S6])
    frame(d, title="A blocking tray must move first",
          subtitle="Root tray R (P17) must reach bay B21. Both of its exits are occupied (K at P15, T20 at P20), "
                   "so AGV-1 first reparks K at P19, returns unloaded, lifts R and carries it out via P15 and W13. "
                   "Occupancy and routes are illustrative, not a validated scheduler result.",
          badge_key="yaml+hyp",
          legend=[("dasharrow", T.green, "unloaded AGV"), ("route", T.amber, "carry blocker K"),
                  ("route", T.green, "carry root tray R"), ("box", T.amber, "tray"), ("box", T.pink, "payload"),
                  ("ring", T.red, "blocked exit"), ("dashbox", T.amber, "tray start / target")]
          + MAP_LEGEND[:4], legend_title="Scene")
    return d


@figure("16_discrete_garage_state_bridge", "DiscreteGarageState bridge", "01-software-background.html")
def bridge():
    d = Doc("16_discrete_garage_state_bridge", "DiscreteGarageState: from garage to records",
            "Left: Pecos map with AGV-4 at C10, tray 15 with a payload at P3, and bay 7. Right: the matching "
            "records inside one DiscreteGarageState snapshot.")
    m = Map(d, 0, 0, 25, (20.4, 46.4), (6.6, 25.4))
    m.base(labels=False, axes=True, zones=False)
    m.tray(3, "", payload=True, emphasis=True)
    m.agv(10, "", heading=90)
    b = m.box
    # node labels for the highlighted entities
    COL = {1: T.green, 2: T.amber, 3: T.pink, 4: C_BAY}
    x, y = m.P(10)
    num_badge(d, x + 40, y - 20, 1, COL[1])
    label_pill(d, x + 56, y - 20, "AGV-4 @ C10", color=COL[1], bg=T.bg_deep, anchor="start", size=11)
    x, y = m.P(3)
    num_badge(d, x - 50, y - 30, 2, COL[2])
    num_badge(d, x - 22, y - 30, 3, COL[3])
    label_pill(d, x - 6, y - 30, "tray 15 + payload @ P3", color=COL[2], bg=T.bg_deep, anchor="start", size=11)
    x, y = m.P(7)
    num_badge(d, x + 6, y - 40, 4, COL[4])
    label_pill(d, x + 22, y - 40, "bay 7 · READY_TO_RETRIEVE", color=COL[4], bg=T.bg_deep, anchor="start", size=11)
    d.text(b.x0 + 10, b.y0 + 14, "Pecos layout (YAML)", size=11.5, family="mono", weight=600, fill=T.muted)

    # right: state records
    rx = b.x1 + 64
    VIO = T.violet
    top = uml_class(d, rx, b.y0, "DiscreteGarageState", accent=VIO, stereo="one snapshot per plan", size=12,
                    attrs=["+ header: std_msgs/Header", "+ is_faulted: bool",
                           "+ agvs: DiscreteAgvState[]", "+ bays: DiscreteBayState[]", "+ vexen: DiscreteVecsState[]",
                           "+ trays: DiscreteTrayState[]", "+ payloads: DiscretePayloadState[]",
                           "+ vrcs: DiscreteVrcState[]", "+ disabled_nodes: uint32[]", "+ hash: uint64"], compact=True)
    recs = [
        (1, "agvs[0] : DiscreteAgvState", ["+ id = 4", "+ pose = GaragePose {node_id: 10, heading: 90}",
                                           "+ lift = false", "+ tray_id = 0"]),
        (2, "trays[0] : DiscreteTrayState", ["+ id = 15", "+ pose = GaragePose {node_id: 3, heading: 90}",
                                             "+ agv_id = 0", "+ payload_id = <payload GUID>"]),
        (3, "payloads[0] : DiscretePayloadState", ["+ tray_id = 15", "+ reciprocal_to_tray = false"]),
        (4, "bays[0] : DiscreteBayState", ["+ id = 7", "+ state = READY_TO_RETRIEVE"]),
    ]
    from components import class_size
    rw = max(max(class_size(n, attrs=a, size=12, compact=True)[0] for _, n, a in recs), top.w)
    # re-draw top at common width for alignment
    y = top.y1 + 44
    boxes = []
    trunk_x = rx + 18
    for n, name, attrs in recs:
        bx = uml_class(d, rx + 44, y, name, accent=COL[n], size=12, attrs=attrs, compact=True, w=rw - 44)
        num_badge(d, bx.x0, bx.y0, n, COL[n])
        boxes.append(bx)
        y = bx.y1 + 18
    # composition: trunk from the snapshot down the left side
    d.arrowhead((trunk_x, top.y1), (trunk_x, top.y1 + 30), kind="diamond", color=VIO, size=10)
    d.line(trunk_x, top.y1 + 15, trunk_x, boxes[-1].y0 + 24, stroke=VIO, sw=1.4, layer="edges")
    for bx in boxes:
        d.line(trunk_x, bx.y0 + 24, bx.x0 - 12, bx.y0 + 24, stroke=VIO, sw=1.4, layer="edges")
    d.text(trunk_x + 8, top.y1 + 26, "contains", size=S.tiny, family="mono", fill=T.muted, anchor="start")
    # left column under the map: reading guide + shared pose note
    gy = b.y1 + 56
    d.text(b.x0, gy, "How to read it", size=13, weight=600, fill=T.fg)
    steps = ["Start from a resource on the map (AGV, tray, payload, bay).",
             "Follow its number to the record on the right.",
             "AGV and tray records both point back to a graph node through GaragePose.",
             "All records live in one DiscreteGarageState snapshot."]
    yy = gy + 24
    for i, st in enumerate(steps, start=1):
        num_badge(d, b.x0 + 10, yy + 9, i, T.muted, r=9)
        for j, ln in enumerate(wrap(st, b.w - 34, 12.5, "sans")):
            d.text(b.x0 + 28, yy + 9 + j * 18, ln, size=12.5, fill=T.fg2)
        yy += 18 * len(wrap(st, b.w - 34, 12.5, "sans")) + 10
    note(d, b.x0, yy + 10, b.w,
         "GaragePose{node_id, heading} is a graph node plus a discrete heading in degrees (90 = west), "
         "not an x/y position in metres. The map coordinates come from the layout, not from the state.",
         title="Shared pose type")
    frame(d, title="DiscreteGarageState: from garage to records",
          subtitle="Each numbered resource on the map becomes one record inside the single DiscreteGarageState "
                   "snapshot the planner replays events against. Values are illustrative.",
          badge_key="yaml+hyp",
          legend=[("comp", VIO, "contains (array element)"), ("box", T.green, "AGV record"),
                  ("box", T.amber, "tray record"), ("box", T.pink, "payload record"), ("box", C_BAY, "bay record")],
          legend_title="Legend")
    return d
