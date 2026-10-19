"""Pecos facility figures (real YAML geometry) and the DiscreteGarageState bridge."""
from __future__ import annotations

from contextlib import nullcontext

from components import chip, connect, frame, label_pill, note, num_badge, uml_class
from facility import Map, NODES, EDGES, STALL_L, STALL_W, C_BAY, C_CHG, C_PARK, C_WP
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

FULL_X = (20.0, 46.6)
FULL_Y = (6.4, 25.6)

MAP_LEGEND = [("box", C_PARK, "parking node · XL stall 5.79 × 2.21 m"), ("box", C_BAY, "bay (customer handoff)"),
              ("ring", C_CHG, "AGV charger"), ("dot", C_WP, "waypoint"), ("line", "#55657F", "graph edge"),
              ("fill", "#18233A", "waypoint corridor"), ("dashbox", "#3B4A63", "YAML section")]


def _event_strip(d: Doc, x0, y0, items, *, width=None, title=None, reveal=None):
    """Horizontal chain of event cards: items = [(num, color, kind, text)].
    reveal: optional list of step indexes, one per card; card i (and the arrow into it) appears at reveal[i]
    and gets a highlight ring at exactly that step."""
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
        if reveal:
            with d.only(reveal[i]):
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
            "Pecos layout with an illustrative AGV at charger C10 and trays at P3, P15, P17 and P20. Root tray R "
            "at P17 must reach bay B21, but K at P15, T20 at P20 and the dead-end charger C16 block every exit.")
    s0 = d.step("The real Pecos geometry from the YAML: two sections, parking stalls P, customer bays B7 and B21, "
                "AGV chargers C, waypoints W and the graph edges between them. Nothing is occupied yet.")
    s1 = d.step("A job asks for the car on tray R, so R is the root tray: it sits at P17 and must reach bay B21 "
                "(dashed: the requested move, not a planned route).")
    s2 = d.step("R cannot leave. P17 connects only to P15, P20 and charger C16: K (empty) is at P15, T20 (with a "
                "car) is at P20, and C16 is a dead end. K and T20 are blocking trays, so one of them must move first.")
    s3 = d.step("The rest of the scene: AGV A waits near charger C10, and tray T15 with a payload sits at P3. "
                "The approach and blocking-tray figures reuse this scene.")
    m = Map(d, 0, 0, 35, FULL_X, FULL_Y)
    m.base(labels=True, dim=True)
    with d.at(s1):
        m.tray(17, "R · root", payload=True, emphasis=True)
        m.route([17, 15, 13, 18, 22, 41, 21], T.violet, sw=2.4, dash="7 6", offset=(0, -14))
        x, y = m.P(41)
        label_pill(d, (x + m.P(22)[0]) / 2, y - 34, "job: R  P17 -> B21", color=T.violet, bg=T.bg_deep, border=T.violet, size=11)
    with d.at(s2):
        m.tray(15, "K · blocker", color=T.amber)
        m.tray(20, "T20", payload=True)
        _ring(d, m, 15, T.red, r=20)
        _ring(d, m, 20, T.red, r=20)
        _ring(d, m, 16, T.red, r=20)
        x, y = m.P(16)
        label_pill(d, x, y + 34, "dead end", color=T.red, bg=T.bg_deep, border=T.red, size=10.5, layer="top")
    with d.at(s3):
        m.tray(3, "T15", payload=True)
        m.agv(10, "AGV A", heading=90, label_side="above")
    frame(d, title="Pecos overview with a hypothetical scene",
          subtitle="Node positions and edges are real; the AGV, trays and payloads are teaching stand-ins, not "
                   "occupancy supplied by the YAML. The same scene is reused by the approach and blocking-tray figures.",
          badge_key="yaml+hyp",
          legend=[("box", T.amber, "tray (hypothetical)"), ("box", T.pink, "payload / vehicle"),
                  ("box", T.green, "AGV (hypothetical)"), ("dasharrow", T.violet, "requested move (job)"),
                  ("ring", T.red, "occupied exit / dead end")] + MAP_LEGEND[:4], legend_title="Scene")
    return d


@figure("15_agv_approach_and_pickup", "AGV approach example", "01-software-background.html")
def agv_approach():
    d = Doc("15_agv_approach_and_pickup", "AGV approach, lift, carry and lower",
            "AGV A leaves charger C10 and drives 10 -> 9 -> 11 -> 6 -> 3 under the empty stall P6 to reach tray T15 "
            "at P3, lifts it, carries it to an example destination P2 and lowers it.")
    path = [10, 9, 11, 6, 3]
    caps = [
        "Start: hypothetical AGV A is unloaded at charger C10; tray T15 with a payload is parked at P3.",
        "Drive C10 -> W9, onto the waypoint corridor. Only graph edges can be used.",
        "Drive W9 -> W11 along the corridor.",
        "Drive W11 -> P6. The stall is empty and an unloaded AGV is low enough to pass under parked trays anyway.",
        "Drive P6 -> P3 and stop under T15. The whole unloaded drive C10 -> P3 is one AgvMove (pose) event; "
        "the next event is the lift.",
        "Lift: the AGV raises T15 (with its car) off the floor. Lifting is its own event, separate from driving.",
        "Carry: the TrayMove takes T15 from P3 to its destination, here the free stall P2 as an example.",
        "Lower: the AGV sets T15 down at P2 and is free again. Move, lift, carry, lower is the pattern AGV "
        "assignment wraps around every TrayMove.",
    ]
    st = [d.step(c) for c in caps]
    m = Map(d, 0, 0, 58, (33.6, 46.6), (6.6, 15.2))
    m.base(labels=True, zones=False)
    # T15 positions
    with d.at(0, 5):
        m.tray(3, "T15", payload=True, emphasis=True, chip_pos="tr")
    with d.at(6):
        m.tray(2, "T15", payload=True, emphasis=True, chip_pos="tr")
    # AGV positions: one per step
    agv_at = {0: (10, False, "AGV A @ C10", "above"), 1: (9, False, "AGV A", "above"),
              2: (11, False, "AGV A", "above"), 3: (6, False, "AGV A", "above"),
              4: (3, False, "AGV A", "above"), 5: (3, True, "AGV A · lifted", "above"),
              6: (2, True, "AGV A · lifted", "above"), 7: (2, False, "AGV A", "above")}
    for k, (nid, lifted, lab, side) in agv_at.items():
        with d.only(k):
            m.agv(nid, lab, heading=90, label_side=side, lifted=lifted)
    # start marker after the AGV left C10
    x10, y10 = m.P(10)
    with d.at(1):
        d.rect(x10 - 1.1 * m.s, y10 - 0.55 * m.s, 2.2 * m.s, 1.1 * m.s, rx=0.3 * m.s, fill="none",
               stroke=T.green, sw=1.4, dash="5 4", layer="main")
        chip(d, x10, y10 - 0.55 * m.s - 16, "start @ C10", T.green, anchor="middle", size=10.5,
             fill=T.tint(T.green, 0.25, T.bg_deep), layer="top")
    # unloaded route: partial per step, full from step 4
    for k in (1, 2, 3):
        with d.only(k):
            m.route(path[:k + 1], T.green, sw=4.5)
    with d.at(4):
        m.route(path, T.green, sw=4.5)
    x3, y3 = m.P(3)
    x2, y2 = m.P(2)
    with d.only(4):
        d.circle(x3, y3, 30, fill="none", stroke=T.green, sw=1.6, dash="5 4", layer="over")
        label_pill(d, x3 - 40, y3 + 48, "next event: lift at P3", color=T.green, bg=T.bg_deep, border=T.green,
                   size=11.5)
    with d.at(5):
        label_pill(d, x3 + 10, y3 + 48, "lift @ P3", color=T.green, bg=T.bg_deep, border=T.green, size=11.5)
    # carry route (loaded), offset below the stall row
    with d.at(6):
        m.route([3, (NODES[2].x + 1.3, NODES[2].y)], T.amber, sw=4.5, offset=(0, 30))
    with d.at(7):
        label_pill(d, x2 + 10, y2 + 48, "lower @ P2", color=T.green, bg=T.bg_deep, border=T.green, size=11.5)
    b = m.box
    _event_strip(d, b.x0, b.y1 + 72, [
        (None, T.green, "AgvMove · pose", "C10 -> P3 unloaded"),
        (None, T.green, "AgvMove · lift", "at P3: lift T15"),
        (None, T.amber, "TrayMove", "T15: P3 -> P2"),
        (None, T.green, "AgvMove · lift", "at P2: lower T15"),
    ], width=b.w, title="the same intent as abstract events (simplified)", reveal=[4, 5, 6, 7])
    frame(d, title="AGV approach, lift, carry and lower",
          subtitle="Hypothetical AGV A starts at charger C10 and reaches tray T15 at P3 via the connected nodes "
                   "10 -> 9 -> 11 -> 6 -> 3, then lifts it, carries it to an example destination P2 and lowers it. "
                   "Driving, lifting, carrying and lowering are separate events; the route is a graph walk, "
                   "not a recorded run.",
          badge_key="yaml+hyp",
          legend=[("route", T.green, "unloaded AGV route"), ("route", T.amber, "loaded carry"),
                  ("box", T.amber, "tray (hypothetical)"),
                  ("box", T.pink, "payload"), MAP_LEGEND[0], MAP_LEGEND[2], MAP_LEGEND[3]], legend_title="Scene")
    return d


@figure("15_blocking_tray_move", "Blocking tray example", "01-software-background.html")
def blocking():
    d = Doc("15_blocking_tray_move", "A blocking tray must move first",
            "Root tray R at P17 must reach bay B21. Its exits via P15 and P20 are occupied, so AGV A first "
            "relocates blocker K from P15 to P19, then fetches R and carries it to B21.")
    caps = [
        "Start: root tray R at P17 must reach bay B21. P17 connects only to P15, P20 and charger C16; K holds "
        "P15, T20 holds P20 and C16 is a dead end, so R is boxed in. AGV A waits at W13.",
        "① AgvMove A: drive unloaded W13 -> P15 and lift the blocker K.",
        "② TrayMove K: carry K from P15 to the free stall P19, off R's way out. P15 is now free.",
        "③ AgvMove A: lower K at P19, drive back unloaded P19 -> P15 -> P17 and lift R. This must wait for ②, "
        "because P15 was occupied until then.",
        "④ TrayMove R: carry R out via P15, W13, W18, W22 and W41 into bay B21.",
        "BayTransition B21: R is lowered in the bay and the bay can switch to retrieve, handing the car to the "
        "customer. It depends on ④.",
        "The whole plan at once: starting positions, K's new home P19, and the four moves in the order the "
        "planner must respect.",
    ]
    st = [d.step(c) for c in caps]
    last = len(st) - 1
    m = Map(d, 0, 0, 37, (20.0, 46.6), (14.9, 25.3))
    m.base(labels=True, zones=False)
    m.tray(20, "T20", payload=True)
    # R: P17 (steps 0-3 and poster), B21 (4-5)
    for rng in ((0, 3), (last, None)):
        with d.at(*rng):
            m.tray(17, "R · root", payload=True, emphasis=True)
    with d.at(4, 5):
        m.tray(21, "R · root", payload=True, emphasis=True)
    # K: P15 (0-1 and poster), P19 (2-5)
    for rng in ((0, 1), (last, None)):
        with d.at(*rng):
            m.tray(15, "K · blocker", color=T.amber)
    with d.at(2, 5):
        m.tray(19, "K · blocker", color=T.amber)
    # ghost of K's destination
    x19, y19 = m.P(19)
    w, h = (STALL_L - 0.5) * m.s, (STALL_W - 0.32) * m.s
    for rng in ((0, 1), (last, None)):
        with d.at(*rng):
            d.rect(x19 - w / 2, y19 - h / 2, w, h, rx=6, fill="none", stroke=T.amber, sw=1.4, dash="5 4",
                   layer="main")
            d.text(x19 - w / 2 + 10, y19 + h / 2 - 12, "K after step 2", size=11, family="mono", fill=T.amber,
                   halo=T.bg_deep, halo_w=3)
    # blocked exits of P17 at the start
    with d.only(0):
        for nid in (15, 20, 16):
            _ring(d, m, nid, T.red, r=20)
        label_pill(d, m.X(20.6), m.Y(16.0), "every exit of P17 is blocked", color=T.red, bg=T.bg_deep,
                   border=T.red, size=11, anchor="start")
    # AGV A per step
    agv_at = {0: (13, False, "AGV A", "left"), 1: (15, True, "AGV A · lifted", "above"),
              2: (19, True, "AGV A · lifted", "above"), 3: (17, True, "AGV A · lifted", "above"),
              4: (21, True, "AGV A · lifted", "above"), 5: (21, False, "AGV A", "above"),
              last: (13, False, "AGV A", "left")}
    for k, (nid, lifted, lab, side) in agv_at.items():
        with d.only(k):
            m.agv(nid, lab, heading=90, label_side=side, lifted=lifted)
    # routes (offsets keep overlapping walks readable), cumulative
    with d.at(1):
        m.route([13, 15], T.green, sw=2.6, dash="7 6", offset=(0, -17), num=1, num_at=0)
    with d.at(2):
        m.route([15, 19], T.amber, sw=4.5, offset=(-16, 0), num=2, num_at=0)
    with d.at(3):
        m.route([19, 15, 17], T.green, sw=2.6, dash="7 6", offset=(16, -5), num=3, num_at=0)
    with d.at(4):
        m.route([17, 15, 13, 18, 22, 41, 21], T.green, sw=4.5, offset=(0, 10), num=4, num_at=0)
    with d.only(5):
        x21, y21 = m.P(21)
        d.rect(m.X(20.3), m.Y(23.6), m.X(25.95) - m.X(20.3), m.Y(19.9) - m.Y(23.6), rx=10, fill="none",
               stroke=T.violet, sw=2.2, dash="6 4", layer="over")
        label_pill(d, x21, m.Y(19.4), "B21: retrieve", color=T.violet, bg=T.bg_deep, border=T.violet, size=11)
    b = m.box
    _event_strip(d, b.x0, b.y1 + 72, [
        (1, T.green, "AgvMove A", "W13 -> P15, lift"),
        (2, T.amber, "TrayMove K", "P15 -> P19"),
        (3, T.green, "AgvMove A", "P19 -> P17, lift"),
        (4, T.green, "TrayMove R", "P17 -> B21"),
        (None, T.violet, "BayTransition", "B21: retrieve"),
    ], width=b.w, title="dependency chain the planner must respect (simplified)", reveal=[1, 2, 3, 4, 5])
    frame(d, title="A blocking tray must move first",
          subtitle="Root tray R (P17) must reach bay B21. Both of its exits are occupied (K at P15, T20 at P20), "
                   "so AGV A first reparks K at P19, returns unloaded, lifts R and carries it out via P15 and W13. "
                   "Occupancy and routes are illustrative, not a validated scheduler result.",
          badge_key="yaml+hyp",
          legend=[("dasharrow", T.green, "unloaded AGV"), ("route", T.amber, "carry blocker K"),
                  ("route", T.green, "carry root tray R"), ("box", T.amber, "tray"), ("box", T.pink, "payload"),
                  ("ring", T.red, "blocked exit")]
          + MAP_LEGEND[:4], legend_title="Scene")
    return d


@figure("16_discrete_garage_state_bridge", "DiscreteGarageState bridge", "01-software-background.html")
def bridge():
    d = Doc("16_discrete_garage_state_bridge", "DiscreteGarageState: from garage to records",
            "Left: Pecos map with AGV 4 at C10, tray 15 with a payload at P3, and bay 7. Right: the matching "
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
    label_pill(d, x + 56, y - 20, "AGV 4 @ C10", color=COL[1], bg=T.bg_deep, anchor="start", size=11)
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
