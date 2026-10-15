"""Schematic figures: 03 sequential tray moves (schematic garage), 14 VRC multi-floor transfer."""
from __future__ import annotations

from components import chip, connect, frame, label_pill, note, num_badge
from facility import Map
from registry import figure
from svgkit import BBox, Doc, text_width, wrap, pts_to_path
from theme import T, S


@figure("03_garage_xy", "Schematic garage: sequential tray moves", "02-issue-and-proposal.md")
def garage_xy():
    d = Doc("03_garage_xy", "Schematic garage: clearing a route with sequential tray moves",
            "AGV 1 faces +x carrying tray T1 toward the goal; trays T2 and T3 sit on the route and are reparked "
            "into side stalls first.")
    L, Wm = 5.8, 2.4               # schematic cell size in metres
    m = Map(d, 0, 0, 27, (-0.4, 6 * L + 0.4), (-2.3, 2 * Wm + 1.2))
    m.floor(axes=False)
    m.clip()
    lane_y, stall_y = 0.0, Wm + 0.25
    # lane cells N1..N6 and side stalls S3, S4
    cells = {}
    for i in range(6):
        cx = L / 2 + i * L
        cells[f"N{i + 1}"] = (cx, lane_y)
    cells["S3"] = (L / 2 + 2 * L, stall_y)
    cells["S4"] = (L / 2 + 3 * L, stall_y)
    cells["S5"] = (L / 2 + 4 * L, stall_y)
    # lane band
    x0, y0 = m.P((0, lane_y + Wm / 2))
    x1, y1 = m.P((6 * L, lane_y - Wm / 2))
    d.rect(x0, y0, x1 - x0, y1 - y0, fill="#18233A", layer="bg")
    for k, (cx, cy) in cells.items():
        x, y = m.P((cx, cy))
        w, h = (L - 0.12) * m.s, (Wm - 0.2) * m.s
        is_goal = k == "N6"
        d.rect(x - w / 2, y - h / 2, w, h, rx=5, fill=T.tint(T.sky, 0.08, T.bg_deep) if k.startswith("S") else "none",
               stroke=T.green if is_goal else T.tint(T.sky, 0.5, T.bg_deep), sw=2 if is_goal else 1.1,
               dash="6 4" if is_goal else (None if k.startswith("S") else "3 4"), layer="under")
        d.text(x - w / 2 + 7, y - h / 2 + 11, k, size=11, family="mono", weight=600,
               fill=T.green if is_goal else T.tint(T.sky, 0.9, T.bg_deep), halo=T.bg_deep, halo_w=3)
        d.circle(x, y, 2.6, fill=T.tint(T.sky, 0.8, T.bg_deep), layer="over")
    gx, gy = m.P(cells["N6"])
    d.text(gx, gy + 2, "GOAL", size=13, family="mono", weight=700, fill=T.green, anchor="middle", letter_spacing=1)
    # graph edges (schematic)
    for a, b in [("N1", "N2"), ("N2", "N3"), ("N3", "N4"), ("N4", "N5"), ("N5", "N6"), ("N3", "S3"), ("N4", "S4"),
                 ("N5", "S5"), ("S3", "S4"), ("S4", "S5")]:
        (ax, ay), (bx, by) = m.P(cells[a]), m.P(cells[b])
        d.line(ax, ay, bx, by, stroke="#55657F", sw=1.3, layer="edges")
    m.tray(cells["N3"], "T2", chip_pos="tr")
    m.tray(cells["N4"], "T3", chip_pos="tr")
    m.tray(cells["N1"], "T1", payload=True, emphasis=True, chip_pos="tr")
    m.agv(cells["N1"], "", heading=270)
    m.unclip()
    # moves
    m.route([cells["N3"], cells["S3"]], T.amber, sw=4, offset=(-30, 0), num=1, num_at=0)
    m.route([cells["N4"], cells["S4"]], T.amber, sw=4, offset=(-30, 0), num=2, num_at=0)
    m.route([cells["N1"], cells["N6"]], T.green, sw=4.5, offset=(0, 34), num=3, num_at=0)
    b = m.box
    n1x, n1y = m.P(cells["N1"])
    label_pill(d, n1x, n1y - Wm * m.s / 2 - 22, "AGV 1 carrying T1, facing +x", color=T.green, bg=T.bg_deep,
               border=T.green, size=11)
    # axis glyph (top-right, empty area above the goal)
    ox, oy = b.x1 - 120, b.y0 + 70
    d.line(ox, oy, ox + 46, oy, stroke=T.red, sw=2, layer="top")
    d.arrowhead((ox + 52, oy), (ox, oy), kind="filled", color=T.red, size=8, layer="top")
    d.text(ox + 58, oy, "+x", size=11, family="mono", fill=T.red, layer="top")
    d.line(ox, oy, ox, oy - 40, stroke=T.green, sw=2, layer="top")
    d.arrowhead((ox, oy - 46), (ox, oy), kind="filled", color=T.green, size=8, layer="top")
    d.text(ox, oy - 58, "+y", size=11, family="mono", fill=T.green, anchor="middle", layer="top")
    # dependency fan-in
    sy = b.y1 + 54
    cw = 210
    c1 = BBox(b.x0, sy, b.x0 + cw, sy + 50)
    c2 = BBox(b.x0, sy + 64, b.x0 + cw, sy + 114)
    c3 = BBox(b.x0 + cw + 90, sy + 32, b.x0 + 2 * cw + 90, sy + 82)
    for bb, n, col, kind, txt in ((c1, 1, T.amber, "TrayMove", "T2: N3 -> S3"), (c2, 2, T.amber, "TrayMove", "T3: N4 -> S4"),
                                  (c3, 3, T.green, "TrayMove", "T1: N1 -> GOAL")):
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.card, stroke=col, sw=1.4)
        num_badge(d, bb.x0, bb.y0, n, col, r=10)
        d.text(bb.x0 + 16, bb.y0 + 16, kind, size=11, family="mono", weight=600, fill=col)
        d.text(bb.x0 + 16, bb.y0 + 35, txt, size=12, family="mono", fill=T.fg)
    for bb in (c1, c2):
        mx = (bb.x1 + c3.x0) / 2
        connect(d, [(bb.x1, bb.cy), (mx, bb.cy), (mx, c3.cy), (c3.x0, c3.cy)], kind="flow", color=T.muted, size=8)
    d.text(b.x0, sy - 22, "dependencies: 1 and 2 are independent, both must precede 3", size=12, family="mono",
           fill=T.muted)
    note(d, c3.x1 + 30, sy, b.x1 - c3.x1 - 30,
         "Node IDs, distances and the side-stall choice are didactic. A real layout decides which stalls are "
         "reachable and whether a blocker can stay put.", title="Schematic only")
    frame(d, title="Schematic garage: clearing a route with sequential tray moves",
          subtitle="AGV 1 faces +x and must bring tray T1 to the goal. Trays T2 and T3 lie on the route, so two "
                   "prerequisite tray moves into side stalls are scheduled first.",
          badge_key="schematic",
          legend=[("route", T.amber, "prerequisite tray move"), ("route", T.green, "root tray move"),
                  ("box", T.amber, "tray"), ("box", T.pink, "payload"), ("box", T.sky, "stall / node cell"),
                  ("dashbox", T.green, "goal")])
    return d


@figure("14_vrc_floors", "VRC multi-floor transfer", "01-software-background.md")
def vrc():
    d = Doc("14_vrc_floors", "VRC: one layout, several floors",
            "Side elevation: a VRC platform carries an AGV and its tray from a node on floor F1 to a node on "
            "floor F2; VrcTransition simulates idle -> moving -> idle and moves entities at the source node.")
    W = 940
    fh = 190            # floor-to-floor height (px)
    slab = 14
    shaft_x0, shaft_x1 = 560, 770
    floors = {"F2": 40, "F1": 40 + fh + slab + 30}
    COL = {"F1": T.sky, "F2": T.violet}
    VR = T.amber

    def car_side(cx, base_y, w=150, col=T.pink):
        h = 34
        x0 = cx - w / 2
        pts = (f"M{x0} {base_y - 10} L{x0 + 6} {base_y - 22} L{x0 + w * 0.25} {base_y - 26} "
               f"L{x0 + w * 0.38} {base_y - h - 10} L{x0 + w * 0.7} {base_y - h - 10} L{x0 + w * 0.84} {base_y - 26} "
               f"L{x0 + w - 4} {base_y - 22} L{x0 + w} {base_y - 10} Z")
        d.path(pts, fill=T.tint(col, 0.25, T.bg), stroke=col, sw=1.5, bbox=BBox(x0, base_y - h - 10, x0 + w, base_y))
        for f in (0.22, 0.78):
            d.circle(x0 + w * f, base_y - 8, 9, fill=T.bg, stroke=col, sw=1.5)

    def tray_agv(cx, floor_y, *, agv=True, col=T.amber, ghost=False):
        tw = 190
        ty = floor_y - (26 if agv else 6)
        op = 0.45 if ghost else None
        d.rect(cx - tw / 2, ty - 6, tw, 6, rx=2, fill=T.tint(col, 0.6, T.bg), stroke=col, sw=1.2, opacity=op)
        if agv:
            d.rect(cx - 50, floor_y - 20, 100, 16, rx=4, fill=T.tint(T.green, 0.3, T.bg), stroke=T.green, sw=1.4,
                   opacity=op)
            for f in (-34, 34):
                d.circle(cx + f, floor_y - 4, 4, fill=T.fg2, opacity=op)
        if not ghost:
            car_side(cx, ty - 6)

    for fl, top in floors.items():
        y_floor = top + fh
        c = COL[fl]
        # floor band background
        d.rect(0, top, shaft_x0 - 10, fh, rx=10, fill=T.tint(c, 0.05, T.bg), stroke=T.tint(c, 0.4, T.bg), sw=1,
               layer="bg")
        d.text(16, top + 22, f"floor {fl}", size=14, weight=600, fill=c)
        d.rect(0, y_floor, shaft_x0 - 10, slab, rx=3, fill="#334155", layer="under")
        # parking stalls with trays (side view)
        for i, cx in enumerate((105, 305)):
            occupied = (fl == "F1" and i == 0) or (fl == "F2" and i == 1)
            d.line(cx - 100, y_floor - 1, cx + 100, y_floor - 1, stroke=T.tint(T.sky, 0.6, T.bg), sw=3)
            if occupied:
                tray_agv(cx, y_floor, agv=False)
            d.text(cx, y_floor + slab + 14, f"P{'1' if fl == 'F1' else '2'}{i + 1}", size=11, family="mono",
                   fill=T.muted, anchor="middle")
        # VRC gate node on each floor
        gxn = 470
        d.circle(gxn, y_floor - 2, 5, fill=T.fg2, layer="over")
        d.text(gxn, y_floor + slab + 14, "VRC node", size=11, family="mono", fill=T.fg2, anchor="middle")
        # gate at shaft opening
        d.rect(shaft_x0 - 10, top + 40, 8, fh - 40, rx=2, fill=T.tint(VR, 0.5, T.bg), stroke=VR, sw=1)
        d.text(shaft_x0 - 18, top + 30, "gate", size=10.5, family="mono", fill=VR, anchor="end")
    # shaft
    s_top = floors["F2"] - 10
    s_bot = floors["F1"] + fh + slab + 10
    d.rect(shaft_x0, s_top, shaft_x1 - shaft_x0, s_bot - s_top, rx=8, fill=T.tint(VR, 0.05, T.bg), stroke=VR, sw=1.6)
    for x in (shaft_x0 + 14, shaft_x1 - 14):
        d.line(x, s_top + 6, x, s_bot - 6, stroke=T.tint(VR, 0.5, T.bg), sw=2, dash="2 6")
    d.text((shaft_x0 + shaft_x1) / 2, s_top - 14, "VRC shaft", size=13, family="mono", weight=700, fill=VR,
           anchor="middle")
    # platform at F1 (current) with AGV + tray, ghost at F2 (target)
    pcx = (shaft_x0 + shaft_x1) / 2
    for fl, ghost in (("F1", False), ("F2", True)):
        y_floor = floors[fl] + fh
        d.rect(shaft_x0 + 8, y_floor, shaft_x1 - shaft_x0 - 16, slab, rx=3,
               fill=T.tint(VR, 0.55 if not ghost else 0.2, T.bg), stroke=VR, sw=1.2, dash="5 4" if ghost else None)
        tray_agv(pcx, y_floor, ghost=ghost)
    # lift arrow
    ay0 = floors["F1"] + fh - 120
    ay1 = floors["F2"] + fh + 30
    d.line(shaft_x1 - 40, ay0, shaft_x1 - 40, ay1 + 14, stroke=VR, sw=3)
    d.arrowhead((shaft_x1 - 40, ay1), (shaft_x1 - 40, ay0), kind="filled", color=VR, size=14)
    label_pill(d, shaft_x1 + 14, (ay0 + ay1) / 2, "VrcCommand.requested_floor = F2", color=VR, bg=T.bg,
               border=VR, anchor="start", size=11.5)
    # from / to labels
    label_pill(d, shaft_x1 + 14, floors["F1"] + fh - 10, "from_vrc_node_id (F1)", color=T.sky, bg=T.bg,
               border=T.sky, anchor="start", size=11.5)
    label_pill(d, shaft_x1 + 14, floors["F2"] + fh - 10, "to_vrc_node_id (F2)", color=T.violet, bg=T.bg,
               border=T.violet, anchor="start", size=11.5)
    # state strip
    sy = floors["F1"] + fh + slab + 74
    d.text(0, sy - 24, "VrcTransition::Apply  (discrete-state simulation)", size=12.5, family="mono", fill=T.muted)
    steps = [("VRC state", "IDLE at F1", VR), ("VRC state", "MOVING", VR), ("VRC state", "IDLE at F2", VR),
             ("AGVs + trays", "source node -> F2 node", T.green)]
    x = 0
    boxes = []
    for kind, txt, col in steps:
        w = max(text_width(txt, 12.5, "mono"), text_width(kind, 11, "mono", 600)) + 30
        d.rect(x, sy, w, 56, rx=8, fill=T.card, stroke=col, sw=1.4)
        d.text(x + 14, sy + 18, kind, size=11, family="mono", weight=600, fill=col)
        d.text(x + 14, sy + 38, txt, size=12.5, family="mono", fill=T.fg)
        boxes.append(BBox(x, sy, x + w, sy + 56))
        x += w + 34
    for a, b in zip(boxes, boxes[1:]):
        connect(d, [(a.x1 + 3, a.cy), (b.x0 - 2, a.cy)], kind="flow", color=T.muted, size=8, sw=1.6)
    frame(d, title="VRC: one layout, several floors",
          subtitle="Side elevation (not a plan view). A vertical reciprocating conveyor carries an AGV and its tray "
                   "between floor-specific nodes. This is general code-supported behaviour; the Pecos YAML has no "
                   "VRC, so it is not placed on the Pecos map.",
          badge_key="conceptual",
          legend=[("box", VR, "VRC shaft / platform"), ("box", T.green, "AGV"), ("box", T.amber, "tray"),
                  ("box", T.pink, "payload"), ("dashbox", VR, "target position")])
    return d
