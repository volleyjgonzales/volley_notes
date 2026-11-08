#!/usr/bin/env python3
"""Figures of the SW2-905 notes, drawn with the study pack's SVG kit.

    python3 scripts/build_figures.py          # writes figures/*.svg

Reuses scheduler_package/scripts/diagrams (svgkit, facility, components, theme) of the SW2-482 notes, so
the Pecos geometry comes from the same YAML and the figures look like the study pack's. The blocked-pose
sets of figure 03 come from figures/data/blocked_poses.json, computed from the cached collision table in
the devcontainer by scripts/blocked_poses.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TICKET = HERE.parent
DIAGRAMS = TICKET.parents[1] / "presentations" / "scheduler_package" / "scripts" / "diagrams"
sys.path.insert(0, str(DIAGRAMS))

from components import card, chip, connect, flow, frame, label_pill, note, num_badge  # noqa: E402
from facility import C_BAY, C_CHG, C_PARK, C_WP, Map, NODES, STALL_L, STALL_W  # noqa: E402
from svgkit import BBox, Doc  # noqa: E402
from theme import S, T  # noqa: E402

OUT = TICKET / "figures"
FULL_X, FULL_Y = (20.0, 46.6), (6.4, 25.6)
EAST_X = (26.0, 46.6)

# the reproduction state (scenario_proposal/busy_garage_car_in_bay_7_agv_on_charger_14.yaml)
EMPTY_TRAYS = {7: 5, 10: 19, 4: 2, 5: 6, 6: 20}          # tray id -> node
LOADED_TRAYS = {15: 3, 17: 17, 21: 23}                    # tray id -> node (car on it)
AGVS = {7: (5, 90), 10: (19, 90), 1: (14, -90)}           # agv id -> pose
DISABLED = (24,)

# footprint sizes in metres (common/constants.hpp, layout parking windows)
TRAY_L, TRAY_W = 14 * 12 * 0.0254, 7 * 12 * 0.0254        # 4.267 x 2.134
AGV_L, AGV_W = 157.5 * 0.0254, 73.5 * 0.0254             # 4.000 x 1.867
STD_L, STD_W = 5.182, 2.21
LEG = 3 * 0.0254

MAP_LEGEND = [("box", C_PARK, "parking stall"), ("box", C_BAY, "customer bay"), ("ring", C_CHG, "AGV charger"),
              ("dot", C_WP, "waypoint"), ("box", T.amber, "tray"), ("box", T.pink, "car on the tray"),
              ("box", T.green, "AGV")]


def stall_rect(m: Map, nid, *, inset=3):
    x, y = m.P(nid)
    w, h = STALL_L * m.s - inset, STALL_W * m.s - inset
    return x - w / 2, y - h / 2, w, h


def ring(d: Doc, m: Map, nid, color, *, dash="5 4", sw=2.2, grow=4):
    x, y, w, h = stall_rect(m, nid)
    d.rect(x - grow, y - grow, w + 2 * grow, h + 2 * grow, rx=8, fill="none", stroke=color, sw=sw, dash=dash,
           layer="top")


def disabled_mark(d: Doc, m: Map, nid, *, label=True):
    x, y, w, h = stall_rect(m, nid)
    d.rect(x, y, w, h, rx=4, fill=T.tint(T.faint, 0.25, T.bg_deep), stroke=T.faint, sw=1.2, dash="4 3",
           layer="under")
    cx, cy = m.P(nid)
    d.line(cx - 10, cy - 10, cx + 10, cy + 10, stroke=T.faint, sw=2, layer="main")
    d.line(cx - 10, cy + 10, cx + 10, cy - 10, stroke=T.faint, sw=2, layer="main")
    if label:
        chip(d, x + w - 4, y + h - 2, "disabled", T.faint, anchor="end", size=10, layer="labels")


def scene(m: Map, *, labels=True, agv1=True, agv1_label_side="right"):
    """The reproduction state on a map."""
    for tid, nid in EMPTY_TRAYS.items():
        m.tray(nid, f"T{tid}" if labels else "", chip_pos="bl")
    for tid, nid in LOADED_TRAYS.items():
        m.tray(nid, f"T{tid}" if labels else "", payload=True, chip_pos="bl")
    m.tray(7, "T27" if labels else "", payload=True, emphasis=True, chip_pos="bl")
    for nid in DISABLED:
        disabled_mark(m.d, m, nid, label=labels)
    m.agv(5, "AGV-7" if labels else "", heading=90, label_side="below")
    m.agv(19, "AGV-10" if labels else "", heading=90, label_side="below")
    if agv1:
        m.agv(14, "AGV-1" if labels else "", heading=-90, label_side=agv1_label_side)


def bay_state(d: Doc, m: Map, nid, text):
    x, y = m.P(nid)
    label_pill(d, x, y + (STALL_W + 0.9) * m.s / 2 + 12, text, color=C_BAY, size=10, bg=T.bg_deep, border=C_BAY)


# --------------------------------------------------------------------------------------
def fig_scenario():
    d = Doc("01_scenario", "The reproduction state on the Pecos layout",
            "Pecos combined with the SW2-905 reproduction state: a car on tray 27 in bay B7, every stall but P15 "
            "occupied, P24 disabled, and AGV 1 stopped on charger C14, 0.6 m from P15.")
    m = Map(d, 0, 0, 35, FULL_X, FULL_Y)
    m.base(labels=True, highlight=(15,), zones=False)
    scene(m, agv1_label_side="left")
    bay_state(d, m, 7, "B7 VEHICLE_INSERTED")
    bay_state(d, m, 21, "B21 READY_TO_RETRIEVE")
    # the free stall and the charger next to it
    ring(d, m, 15, T.green)
    x, y, w, h = stall_rect(m, 15)
    label_pill(d, x + w / 2 + 16, y + 13, "only stall without a tray", color=T.green, size=10.5,
               bg=T.bg_deep, border=T.green)
    cx, cy = m.P(14)
    px, py = m.P(15)
    xx = cx - 2.55 * m.s
    d.line(xx, cy, xx, py, stroke=T.red, sw=1.6, layer="top")
    d.line(xx - 5, cy, xx + 5, cy, stroke=T.red, sw=1.6, layer="top")
    d.line(xx - 5, py, xx + 5, py, stroke=T.red, sw=1.6, layer="top")
    label_pill(d, xx - 8, (cy + py) / 2, "0.61 m: AGV-1 overlaps P15", color=T.red, size=10.5,
               bg=T.bg_deep, border=T.red, anchor="end")
    frame(d, title="SW2-905 reproduction: a car to park, one free stall, and an AGV on the charger beside it",
          subtitle="Occupancy from scenario_proposal/busy_garage_car_in_bay_7_agv_on_charger_14.yaml on the real "
                   "Pecos geometry. The insert must take T27 out of B7 and park it; P15 is the only stall without "
                   "a tray, and AGV-1 on C14 physically overlaps it.",
          badge_key="yaml+scenario", legend=MAP_LEGEND + [("dashbox", T.green, "candidate stall"),
                                                           ("dashbox", T.faint, "disabled node")],
          legend_title="Map")
    return d


# --------------------------------------------------------------------------------------
def fig_context():
    d = Doc("02a_context", "Where the chargers are",
            "The Pecos layout with its three AGV chargers; each is a side pose 0.61 m from a stall or a waypoint. "
            "The dashed box marks the C14, P15, P19 area drawn to scale in the next figure.")
    m = Map(d, 0, 0, 30, FULL_X, FULL_Y)
    m.base(labels=True, zones=False)
    for cid, nid, txt in ((10, 9, "C10 is 0.61 m from W9"), (14, 15, "C14 is 0.61 m from P15"),
                          (16, 17, "C16 is 0.61 m from P17")):
        x, y = m.P(cid)
        d.circle(x, y, 0.75 * m.s, fill="none", stroke=T.red, sw=2, dash="4 3", layer="top")
        if cid == 10:
            label_pill(d, x + 0.9 * m.s, y - 18, txt, color=T.red, size=10.5, bg=T.bg_deep, border=T.red, anchor="start")
        elif cid == 14:
            label_pill(d, x - 3.2 * m.s, y + 2, txt, color=T.red, size=10.5, bg=T.bg_deep, border=T.red, anchor="end")
        else:
            label_pill(d, x + 1.0 * m.s, y + 22, txt, color=T.red, size=10.5, bg=T.bg_deep, border=T.red, anchor="start")
    # zoom box of figure 1b
    x0, y0, x1, y1 = m.X(34.0), m.Y(20.9), m.X(40.4), m.Y(15.2)
    d.rect(x0, y0, x1 - x0, y1 - y0, rx=6, fill="none", stroke=T.sky, sw=1.8, dash="7 5", layer="top")
    d.text(x0 + 8, y0 - 9, "area of the next figure", size=10.5, family="mono", fill=T.sky, halo=T.bg_deep,
           halo_w=3, layer="top")
    frame(d, title="The AGV chargers of Pecos sit beside a stall or a waypoint",
          subtitle="All three chargers are side poses in the parking columns, not separate bays: an AGV charging "
                   "on one of them stands 0.61 m from the centre of the neighbouring node.",
          badge_key="yaml",
          legend=[("box", C_PARK, "parking stall"), ("box", C_BAY, "customer bay"), ("ring", C_CHG, "AGV charger"),
                  ("dot", C_WP, "waypoint"), ("ring", T.red, "charger whose AGV overlaps the neighbour")])
    return d


def _footprint_panel(d: Doc, ox, stall, *, overlap: bool):
    m = Map(d, ox, 0, 60, (34.0, 40.4), (15.2, 20.9))
    m.floor(axes=True, tick=1)
    n14, ns = NODES[14], NODES[stall]

    def rect_m(cx, cy, L, W, **kw):
        d.rect(m.X(cx - L / 2), m.Y(cy + W / 2), L * m.s, W * m.s, **kw)

    m.clip()
    rect_m(ns.x, ns.y, 5.791, 2.21, rx=3, fill="none", stroke=T.tint(C_PARK, 0.45, T.bg_deep), sw=1.2, dash="3 3",
           layer="under")
    rect_m(ns.x, ns.y, TRAY_L, TRAY_W, rx=4, fill=T.tint(T.amber, 0.18, T.bg_deep), stroke=T.amber, sw=1.8, layer="main")
    rect_m(n14.x, n14.y, AGV_L, AGV_W, rx=6, fill=T.tint(T.green, 0.20, T.bg_deep), stroke=T.green, sw=2, layer="main")
    if overlap:
        ox0, ox1 = n14.x - AGV_L / 2, n14.x + AGV_L / 2
        oy0, oy1 = max(n14.y - AGV_W / 2, ns.y - TRAY_W / 2), min(n14.y + AGV_W / 2, ns.y + TRAY_W / 2)
        d.rect(m.X(ox0), m.Y(oy1), (ox1 - ox0) * m.s, (oy1 - oy0) * m.s, fill=T.tint(T.red, 0.45, T.bg_deep),
               stroke=T.red, sw=1.2, layer="over")
        label_pill(d, m.X((ox0 + ox1) / 2), m.Y((oy0 + oy1) / 2), f"overlap {oy1 - oy0:.2f} m deep", color=T.red,
                   size=10.5, bg=T.bg_deep, border=T.red)
    for nid, col in ((14, C_CHG), (stall, C_PARK)):
        x, y = m.P(nid)
        d.circle(x, y, 3.5, fill=col, stroke=T.bg_deep, sw=1, layer="top")
    m.unclip()
    x14, y14 = m.P(14)
    xs, ys = m.P(stall)
    d.text(xs + 8, ys - 8, ns.label, size=11, family="mono", weight=700, fill=C_PARK, halo=T.bg_deep, halo_w=3,
           layer="top")
    d.text(x14 + 8, y14 + 12, "C14", size=11, family="mono", weight=700, fill=C_CHG, halo=T.bg_deep, halo_w=3,
           layer="top")
    label_pill(d, m.X(ns.x), m.Y(ns.y + TRAY_W / 2) - 12, "TRAY 4.27 x 2.13 m", color=T.amber, size=10.5,
               bg=T.bg_deep, border=T.amber)
    label_pill(d, m.X(n14.x), m.Y(n14.y - AGV_W / 2) + 12, "AGV 4.00 x 1.87 m", color=T.green, size=10.5,
               bg=T.bg_deep, border=T.green)
    # centre-to-centre distance on the right
    xx = m.X(40.4) - 22
    d.line(xx, y14, xx, ys, stroke=T.fg2, sw=1.4, layer="top")
    for yy in (y14, ys):
        d.line(xx - 5, yy, xx + 5, yy, stroke=T.fg2, sw=1.4, layer="top")
    d.text(xx + 9, (y14 + ys) / 2, f"dy = {ns.y - n14.y:.3f} m", size=10.5, family="mono", fill=T.fg2,
           anchor="start", halo=T.bg_deep, halo_w=3, layer="top")
    b = m.box
    return b


def fig_overlap():
    d = Doc("02b_overlap", "C14 against P15 and against P19, to scale",
            "Left: the AGV on C14 and a tray on P15 overlap. Right: the same AGV and a tray on P19 do not. "
            "Same scale, same column of the layout.")
    b1 = _footprint_panel(d, 0, 15, overlap=True)
    b2 = _footprint_panel(d, b1.w + 150, 19, overlap=False)
    d.text(b1.x0, b1.y0 - 16, "C14 against P15: overlap", size=S.h, weight=600, fill=T.red, layer="labels")
    d.text(b2.x0, b2.y0 - 16, "C14 against P19: clear", size=S.h, weight=600, fill=T.green, layer="labels")
    d.text_lines(b1.x0, b1.y1 + 44, ["dy = 0.609 m is less than (w_TRAY + w_AGV) / 2 = 2.00 m,",
                                     "so the two rectangles share 1.39 m of the column."],
                 size=S.small, fill=T.fg2, lh=1.45)
    d.text_lines(b2.x0, b2.y1 + 44, ["dy = 2.895 m is more than 2.00 m: a gap of 0.90 m remains.",
                                     "The stall pitch of 2.286 m keeps neighbouring stalls apart too."],
                 size=S.small, fill=T.fg2, lh=1.45)
    frame(d, title="Why an AGV on C14 blocks P15 but not P19",
          subtitle="Both rectangles have their long side along the row, so they overlap when the centre-to-centre "
                   "distance along the column is less than half the sum of their widths. The collision table stores "
                   "the answer of this test for every pair of footprints and poses.",
          badge_key="yaml",
          legend=[("box", T.green, "AGV footprint"), ("box", T.amber, "TRAY footprint"),
                  ("fill", T.tint(T.red, 0.45, T.bg_deep), "overlap"), ("dashbox", C_PARK, "XL parking window")],
          footnote="Sizes from common/constants.hpp; node positions from the YAML. The payload footprint of a loaded "
                   "tray is larger than the tray's (5.18 x 2.21 m for STANDARD) and overlaps the AGV as well.")
    return d


def fig_substitutions():
    d = Doc("02c_substitutions", "The two footprint substitutions",
            "Left: an AGV under a parked tray is checked against the tray's legs, so it fits. Right: a loaded tray "
            "beside a parked AGV is checked with the tray footprint, not the payload's.")
    s_ = 58

    def rect(cx, cy, L, W, **kw):
        d.rect(cx - L * s_ / 2, cy - W * s_ / 2, L * s_, W * s_, **kw)

    # panel 1: AGV under a tray
    px, py = 190, 150
    d.rect(px - 180, py - 120, 360, 240, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
    rect(px, py, TRAY_L, TRAY_W, rx=4, fill="none", stroke=T.tint(T.amber, 0.45, T.bg_deep), sw=1.4, dash="5 4",
         layer="main")
    rect(px, py, AGV_L, AGV_W, rx=6, fill=T.tint(T.green, 0.20, T.bg_deep), stroke=T.green, sw=2, layer="main")
    for sx in (-1, 1):
        for sy in (-1, 1):
            rect(px + sx * (TRAY_L / 2 - LEG / 2) * s_, py + sy * (TRAY_W / 2 - LEG / 2) * s_, LEG, LEG,
                 fill=T.amber, layer="over")
    d.text(px, py - 4, "AGV", size=11, family="mono", weight=700, fill=T.green, anchor="middle", layer="top")
    d.text(px, py + 12, "under the deck", size=10, fill=T.green, anchor="middle", layer="top")
    label_pill(d, px, py - TRAY_W * s_ / 2 - 14, "TRAY outline (not used for an AGV)", color=T.amber, size=10,
               bg=T.bg_deep, border=T.amber)
    label_pill(d, px, py + TRAY_W * s_ / 2 + 14, "TRAY_LEGS: four 0.076 m squares", color=T.amber, size=10,
               bg=T.bg_deep, border=T.amber)
    d.text(px - 180, py - 136, "Moving AGV, parked tray: checked against TRAY_LEGS", size=S.h, weight=600,
           fill=T.fg, layer="labels")
    d.text_lines(px - 180, py + 140, ["The AGV body is lower than the tray deck, so only the legs can",
                                       "stop it. With the full TRAY rectangle no AGV could ever drive",
                                       "under a tray to lift it."], size=S.small, fill=T.fg2, lh=1.45)
    # panel 2: payload beside an AGV
    qx, qy = 700, 150
    d.rect(qx - 240, qy - 120, 480, 240, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
    ax, ay = qx - 20, qy + 52          # parked AGV
    tx, ty = qx + 10, qy - 40          # loaded tray beside it (shifted along the column)
    rect(tx, ty, STD_L, STD_W, rx=4, fill=T.tint(T.pink, 0.10, T.bg_deep), stroke=T.pink, sw=1.4, dash="6 4", layer="main")
    rect(tx, ty, TRAY_L, TRAY_W, rx=4, fill=T.tint(T.amber, 0.18, T.bg_deep), stroke=T.amber, sw=1.8, layer="main")
    rect(ax, ay, AGV_L, AGV_W, rx=6, fill=T.tint(T.green, 0.20, T.bg_deep), stroke=T.green, sw=2, layer="main")
    ox0, ox1 = max(ax - AGV_L * s_ / 2, tx - TRAY_L * s_ / 2), min(ax + AGV_L * s_ / 2, tx + TRAY_L * s_ / 2)
    oy0, oy1 = max(ay - AGV_W * s_ / 2, ty - TRAY_W * s_ / 2), min(ay + AGV_W * s_ / 2, ty + TRAY_W * s_ / 2)
    d.rect(ox0, oy0, ox1 - ox0, oy1 - oy0, fill=T.tint(T.red, 0.45, T.bg_deep), stroke=T.red, sw=1.2, layer="over")
    d.text(ax, ay + 4, "parked AGV", size=11, family="mono", weight=700, fill=T.green, anchor="middle", layer="top")
    label_pill(d, tx, ty - STD_W * s_ / 2 - 14, "PAYLOAD rectangle of the car", color=T.pink, size=10,
               bg=T.bg_deep, border=T.pink)
    d.text(tx, ty - 2, "TRAY (used)", size=11, family="mono", weight=700, fill=T.amber, anchor="middle", layer="top")
    d.text(qx - 240, qy - 136, "Moving PAYLOAD or AGV, parked AGV: checked as a TRAY", size=S.h, weight=600,
           fill=T.fg, layer="labels")
    d.text_lines(qx - 240, qy + 140, ["A car overhangs its tray but sits above an AGV's height, so the tray",
                                       "frame is what an AGV body can hit. The check uses the TRAY rectangle",
                                       "for a passing payload; the collision table has the payload entry too."],
                 size=S.small, fill=T.fg2, lh=1.45)
    frame(d, title="Flat footprints with two substitutions for height",
          subtitle="The collision table works in two dimensions. Two rules in BuildStaticObstacleFilter stand in "
                   "for the third: static_graph_filtering.cpp:65 and :83.",
          badge_key="schematic",
          legend=[("box", T.green, "AGV footprint"), ("box", T.amber, "TRAY footprint"),
                  ("dashbox", T.pink, "PAYLOAD footprint"), ("fill", T.tint(T.red, 0.45, T.bg_deep), "overlap")])
    return d


# --------------------------------------------------------------------------------------
FILTER_SPECS = {
    "keep_out": dict(
        name="03a_keep_out", heading="The keep-out filter: what is off limits for the whole plan",
        subtitle="Built once per plan request from the initial state, for each footprint class, and stored in "
                 "PlanContext::keep_out_filter_by_footprint. It names every enabled entity as ignored, so only "
                 "disabled nodes, disabled entities and whatever stands on a disabled node remain as obstacles.",
        ignored=["every enabled tray (T4 .. T27)", "every enabled AGV (AGV-1, AGV-7, AGV-10)",
                 "every enabled bay (B7, B21)"],
        counted=["disabled node P24", "no disabled entity in this state"],
        verdict=("P15 is not in the keep-out filter", T.green),
        used=["job expansion: a requested destination", "in a disabled area is refused",
              "validation: first check of a destination"],
        counted_ids=set(),
    ),
    "stall_search": dict(
        name="03b_stall_search", heading="The stall search's filter: everything movable is transparent",
        subtitle="BuildImmobileTrayFilter builds the static obstacle filter for the tray's own footprint with every "
                 "tray and every AGV in the ignore sets, so that a tray or an AGV standing in the way does not stop "
                 "the search for a stall. Acceptance of a stall then only asks whether a tray stands on it.",
        ignored=["every tray (T4 .. T27)", "every AGV (AGV-1, AGV-7, AGV-10)"],
        counted=["disabled node P24", "bays not ready to retrieve (none here:",
                 "B7 is transitioned to retrieve first)"],
        verdict=("P15 looks free: no tray stands on it", T.green),
        used=["FindDestinationForRootTray", "FindBlockingTrayResolution", "AssignEmptyTrayToMove"],
        counted_ids=set(),
    ),
    "validation": dict(
        name="03c_validation", heading="Validation's filter: only the mover and its carrier are ignored",
        subtitle="ValidateMoveDestinationAndPath builds the static obstacle filter for the tray move with "
                 "ignore_trays = {T27} and ignore_agvs = {AGV-7}. Every other tray and AGV in the working state "
                 "counts, and the destination must be an enabled pose of this filter.",
        ignored=["T27, the tray being moved", "AGV-7, the AGV carrying it"],
        counted=["every other tray and AGV", "disabled node P24", "bays not ready to retrieve (none)"],
        verdict=("P15 blocked: an AGV stands on C14", T.red),
        used=["ValidateEventSequence, for every", "tray move and AGV move of the plan"],
        counted_ids={"T4", "T5", "T6", "T7", "T10", "T15", "T17", "T21", "AGV-1", "AGV-10"},
    ),
}


def fig_filter(key):
    spec = FILTER_SPECS[key]
    data = json.loads((OUT / "data" / "blocked_poses.json").read_text())[key]
    d = Doc(spec["name"], spec["heading"], spec["subtitle"])
    scale = 26
    m = Map(d, 0, 0, scale, FULL_X, FULL_Y)
    m.base(labels=True, zones=False, axes=False)
    counted = spec["counted_ids"]

    def col_for(entity):
        return None if entity in counted else T.faint

    for tid, nid in EMPTY_TRAYS.items():
        m.tray(nid, f"T{tid}", color=col_for(f"T{tid}") or T.amber, chip_pos="bl")
    for tid, nid in LOADED_TRAYS.items():
        m.tray(nid, f"T{tid}", color=col_for(f"T{tid}") or T.amber, payload=True, chip_pos="bl")
    m.tray(7, "T27", color=col_for("T27") or T.amber, payload=True, emphasis=True, chip_pos="tr")
    disabled_mark(d, m, 24)
    for aid, (nid, heading) in AGVS.items():
        m.agv(nid, f"AGV-{aid}", heading=heading, color=col_for(f"AGV-{aid}") or T.green,
              label_side="below" if aid == 1 else "right")
    # blocked poses at heading 90
    by_node = {}
    for pose, causes in data.items():
        nid, heading = pose.split("@")
        if int(heading) == 90:
            by_node.setdefault(int(nid), set()).update(causes)
    blocked_lines = []
    for nid in sorted(by_node):
        n = NODES[nid]
        causes = by_node[nid]
        is_agv = any(c.startswith("AGV") for c in causes)
        col = T.red if is_agv else (T.faint if any(c.startswith("disabled") for c in causes) else T.amber)
        if n.type == "Parking":
            x, y, w, h = stall_rect(m, nid)
            d.rect(x, y, w, h, rx=3, fill="none", stroke=col, sw=2.4, layer="top")
            d.rect(x, y, w, h, rx=3, fill=T.tint(col, 0.22, T.bg_deep), layer="under")
        else:
            x, y = m.P(nid)
            d.circle(x, y, 0.8 * scale, fill="none", stroke=col, sw=2.4, dash="5 3", layer="top")
        pretty = ", ".join(sorted(c.replace("AGV", "AGV-") if c.startswith("AGV") else c for c in causes))
        blocked_lines.append(f"{n.label:>4}  by {pretty}")
    ring(d, m, 15, spec["verdict"][1], grow=5, sw=2.6)
    # side panel
    px = m.box.x1 + 34
    pw = 330
    y = m.box.y0
    n1 = note(d, px, y, pw, "PAYLOAD STANDARD, the footprint of the loaded tray T27 (id 5)",
              title="Moving footprint", accent=T.pink)
    n2 = note(d, px, n1.y1 + 12, pw, "\n".join(spec["ignored"]), title="Ignored (treated as not there)",
              accent=T.faint)
    n3 = note(d, px, n2.y1 + 12, pw, "\n".join(spec["counted"]), title="Counted as obstacles", accent=T.amber)
    body = "\n".join(blocked_lines) if blocked_lines else "none"
    n4 = note(d, px, n3.y1 + 12, pw, body, title="Poses at heading 90 this filter disables", accent=T.red)
    n5 = note(d, px, n4.y1 + 12, pw, "\n".join(spec["used"]), title="Where it is used", accent=T.sky)
    label_pill(d, px + pw / 2, n5.y1 + 24, spec["verdict"][0], color=spec["verdict"][1], size=11.5, bg=T.bg_deep,
               border=spec["verdict"][1])
    frame(d, title=spec["heading"], subtitle=spec["subtitle"], badge_key="yaml+scenario",
          legend=[("box", T.amber, "tray counted as an obstacle"), ("box", T.green, "AGV counted as an obstacle"),
                  ("box", T.faint, "entity present but ignored by this filter"),
                  ("box", T.red, "pose disabled because of an AGV"), ("box", T.amber, "pose disabled because of a tray"),
                  ("dashbox", T.faint, "disabled node"), ("dashbox", spec["verdict"][1], "candidate stall P15")],
          footnote="Pose entries computed from the cached collision table by scripts/blocked_poses.py; edge entries "
                   "are not drawn. Grey entities are in the ignore sets, so the filter does not see them.")
    return d


def fig_filter_keep_out():
    return fig_filter("keep_out")


def fig_filter_stall_search():
    return fig_filter("stall_search")


def fig_filter_validation():
    return fig_filter("validation")


# --------------------------------------------------------------------------------------
def fig_pipeline():
    d = Doc("04_pipeline", "The insert request through the pipeline",
            "Flow of the insert from the bay through the dispatcher and the scheduler stages to the validation "
            "failure and back to the dispatcher, which drops the job.")
    W, H, GX, GY = 236, 168, 128, 54
    xs = [i * (W + GX) for i in range(4)]
    bay = card(d, xs[0], 0, W, H, title="Bay", accent=C_BAY, sub="src/bay",
               lines=["confirm_insert", "doors close", "VEHICLE_VETTED", "reports VEHICLE_INSERTED"])
    dis = card(d, xs[1], 0, W, H, title="Dispatcher", accent=T.sky, sub="central, CreateJobsFromEvents",
               lines=["bay event ->", "InsertJob(B7, payload)", "+ RebalanceGarageJob (AUTO)", "PlanRequest"])
    s1 = card(d, xs[2], 0, W, H, title="Job expansion", accent=T.violet, num=1, sub="ExpandInsertJob",
              lines=["BayTransition B7 -> retrieve", "TrayMove T27 -> ?", "destination left blank"])
    s2 = card(d, xs[3], 0, W, H, title="Tray assignment", accent=T.amber, num=2, sub="ResolveBlockingTrays",
              lines=["open-space search from B7", "every AGV ignored", "P15 holds no tray", "chooses P15@90"])
    y2 = H + GY
    s3 = card(d, xs[3], y2, W, H, title="AGV assignment", accent=T.green, num=3, sub="ComputeAgvAssignmentCost",
              lines=["costs the pickup leg only", "AGV-7 chosen", "loaded leg not checked"])
    val = card(d, xs[2], y2, W, H, title="Validation", accent=T.red, num=4, sub="ValidateMoveDestinationAndPath",
               lines=["ignore_agvs = {AGV-7}", "P15 blocked by AGV-1", "\"Requested to move to", " 15 @ 90 but it's occupied.\""])
    rest = card(d, xs[1], y2, W, H, title="Motion planning, action graph", accent=T.faint, num=5,
                sub="not reached", lines=["CHUGG", "BuildActionGraph"], dashed=True)
    out = card(d, xs[0], y2, W, H, title="Outcome", accent=T.red, sub="PlanClientCallback",
               lines=["success = true, jobs STATE_ERROR", "retry x4, simpler requests", "INSERT alone -> OnError",
                      "bay stays VEHICLE_INSERTED"])
    flow(d, bay, dis, color=C_BAY, label="BayStateChanged")
    flow(d, dis, s1, color=T.sky, label="Plan()")
    flow(d, s1, s2, color=T.violet)
    flow(d, s2, s3, color=T.amber, side="v")
    flow(d, s3, val, color=T.green)
    connect(d, [(val.x0, val.cy), (rest.x1, rest.cy)], kind="flow", color=T.faint, size=8, sw=1.5, dash="5 4",
            label="only if valid")
    connect(d, [(rest.x0, rest.cy), (out.x1, out.cy)], kind="flow", color=T.faint, size=8, sw=1.5, dash="5 4")
    # the failure path back to the dispatcher
    yb = y2 + H + 34
    pts = [(val.cx, val.y1), (val.cx, yb), (out.cx, yb), (out.cx, out.y1)]
    d.path(f"M{pts[0][0]} {pts[0][1]} L{pts[1][0]} {pts[1][1]} L{pts[2][0]} {pts[2][1]} L{pts[3][0]} {pts[3][1]}",
           stroke=T.red, sw=2, layer="edges")
    d.arrowhead((out.cx, out.y1), (out.cx, yb), kind="filled", color=T.red, size=11)
    label_pill(d, (val.cx + out.cx) / 2, yb, "fail_all_jobs: every job of the request errored", color=T.red,
               size=11, bg=T.bg, border=T.red)
    frame(d, title="Where the insert fails and why nothing recovers",
          subtitle="The stall is chosen at stage 2 without regard to AGVs; validation, two stages later, is the "
                   "first check that counts the AGV on the charger. The response is a success with every job in "
                   "error, so the dispatcher retries, then drops the INSERT job. No event re-creates it.",
          badge_key="as-built",
          legend=[("arrow", T.fg2, "normal flow"), ("dasharrow", T.faint, "not reached in this case"),
                  ("arrow", T.red, "failure path")])
    return d


# --------------------------------------------------------------------------------------
def fig_options():
    d = Doc("05_options", "Option A and option B on the reproduction state",
            "Left: option A, the stall search treats AGV-1 as an illegal pose, skips P15 and stashes T27 on W31. "
            "Right: option B, AGV-1 moves to the free charger C10 first and T27 is parked on P15.")
    scale, gap = 20, 44
    pw = (FULL_X[1] - FULL_X[0]) * scale
    specs = [
        ("A", "Option A: skip the stall that overlaps an AGV", T.sky,
         ["AGV-1 stays on C14 and keeps charging.", "P15 is rejected as a destination; no other stall is",
          "free, so tier 2 stashes T27 on waypoint W31.", "Moves: AGV-7 approach, lift, carry, lower (as today).",
          "Open point: a later repark must move T27 off W31."]),
        ("B", "Option B: move the blocking AGV first", T.green,
         ["AGV-1 drives to the free charger C10 before the", "tray move; P15 becomes usable and T27 is parked.",
          "Moves: one AGV move added (about 20 m), charging", "interrupted and resumed on C10. AGV-1 on C10",
          "overlaps W9, so AGV-7 approaches B7 via W4 instead."]),
    ]
    for i, (key, title, col, lines) in enumerate(specs):
        ox = i * (pw + gap)
        m = Map(d, ox, 0, scale, FULL_X, FULL_Y)
        m.base(labels=True, zones=False, axes=False, highlight=(15,))
        scene(m, labels=False)
        chip(d, m.P(7)[0] - 10, m.P(7)[1] - 0.4 * scale, "T27", T.amber, size=10, anchor="middle")
        chip(d, m.P(14)[0] - 2.6 * scale, m.P(14)[1], "AGV-1", T.green, size=10, anchor="end")
        chip(d, m.P(5)[0], m.P(5)[1] + 1.1 * scale, "AGV-7", T.green, size=10, anchor="middle")
        if key == "A":
            x, y = m.P(15)
            d.line(x - 12, y - 12, x + 12, y + 12, stroke=T.red, sw=3, layer="top")
            d.line(x - 12, y + 12, x + 12, y - 12, stroke=T.red, sw=3, layer="top")
            sx, sy, sw_, sh = stall_rect(m, 15)
            label_pill(d, sx + sw_ / 2, sy + sh + 22, "illegal pose: overlaps AGV-1", color=T.red, size=10,
                       bg=T.bg_deep, border=T.red)
            m.route([5, 9, 8, 31, 7], T.green, sw=3, dash="6 5", num=1, num_at=0)
            m.route([7, 31], T.amber, sw=4, num=2, num_at=1, offset=(0, 14))
            x, y = m.P(31)
            label_pill(d, x - 10, y - 24, "T27 stashed on W31 (tier 2)", color=T.amber, size=10,
                       bg=T.bg_deep, border=T.amber, anchor="start")
        else:
            m.route([14, 15, 13, 8, 9, 10], T.green, sw=3, num=1, num_at=0, offset=(0, -8))
            x, y = m.P(10)
            label_pill(d, x + 0.36 * scale + 46, y + 26, "AGV-1 -> C10, free charger", color=T.green, size=10,
                       bg=T.bg_deep, border=T.green, anchor="start")
            m.route([5, 4, 8, 31, 7], T.green, sw=3, dash="6 5", num=2, num_at=0, offset=(0, 10))
            m.route([7, 31, 8, 13, 15], T.amber, sw=4, num=3, num_at=1, offset=(0, 14))
            x, y, w, h = stall_rect(m, 15)
            label_pill(d, x + w / 2, y + h + 22, "T27 parked on P15", color=T.amber, size=10, bg=T.bg_deep,
                       border=T.amber)
        b = m.box
        d.text(b.x0, b.y0 - 14, title, size=S.h, weight=600, fill=col, layer="labels")
        d.text_lines(b.x0, b.y1 + 18, lines, size=S.small, fill=T.fg2, lh=1.45)
    frame(d, title="Two ways out: avoid the stall, or clear it",
          subtitle="Both start from the detection that option A adds: the stall search must know which stalls a "
                   "parked AGV overlaps. Option A then looks elsewhere; option B spends one AGV move to use the "
                   "best stall. Routes are graph walks for illustration, not recorded plans.",
          badge_key="yaml+hyp",
          legend=[("route", T.green, "AGV move (dashed: approach to the tray)"), ("route", T.amber, "tray move"),
                  ("dashbox", C_PARK, "candidate stall")])
    return d


# --------------------------------------------------------------------------------------
def scene_pr(m: Map, *, labels=True):
    """The committed scenario (two AGVs): AGV-1 idle on C14, AGV-2 under the empty tray at P5."""
    for tid, nid in EMPTY_TRAYS.items():
        m.tray(nid, f"T{tid}" if labels else "", chip_pos="bl")
    for tid, nid in LOADED_TRAYS.items():
        m.tray(nid, f"T{tid}" if labels else "", payload=True, chip_pos="bl")
    m.tray(7, "T27" if labels else "", payload=True, emphasis=True, chip_pos="bl")
    for nid in DISABLED:
        disabled_mark(m.d, m, nid, label=labels)
    m.agv(5, "AGV-2" if labels else "", heading=90, label_side="below")
    m.agv(14, "AGV-1" if labels else "", heading=-90, label_side="left")


def fig_pr():
    d = Doc("06_pr_scenario_and_plan", "The blocked insert on main and with this PR",
            "Left: on main the stall search picks P15, the only stall without a tray, although AGV-1 on charger "
            "C14 overlaps it; validation rejects the plan and the insert is dropped. Right: with this PR AGV-1 "
            "drives to charger C16 while AGV-2 fetches the car, and the car is parked on P15.")
    scale, gap = 20, 44
    pw = (FULL_X[1] - FULL_X[0]) * scale
    specs = [
        ("main", "On main: the insert fails", T.red,
         ["The stall search ignores AGVs and picks P15, the only stall without a",
          "tray, 0.6 m from AGV-1 on C14. Validation rejects the destination as",
          "occupied, every job of the request fails, and the insert is dropped",
          "with the car shut in the bay."]),
        ("pr", "With this PR: the AGV moves and the car is parked", T.green,
         ["AGV-1 is sent to the nearest free charger that keeps the tray's route",
          "open, C16, while AGV-2 drives to the bay and lifts the tray; only the",
          "loaded leg to P15 waits for AGV-1 to arrive",
          "(recorded as InsertJob.StallBlockedByAgvOnCharger)."]),
    ]
    for i, (key, title, col, lines) in enumerate(specs):
        ox = i * (pw + gap)
        m = Map(d, ox, 0, scale, FULL_X, FULL_Y)
        m.base(labels=True, zones=False, axes=False, highlight=(15,))
        scene_pr(m, labels=False)
        chip(d, m.P(7)[0] - 10, m.P(7)[1] - 0.4 * scale, "T27", T.amber, size=10, anchor="middle")
        chip(d, m.P(14)[0] - 3.1 * scale, m.P(14)[1], "AGV-1", T.green, size=10, anchor="end")
        chip(d, m.P(5)[0], m.P(5)[1] + 1.1 * scale, "AGV-2", T.green, size=10, anchor="middle")
        if key == "main":
            m.route([5, 9, 8, 31, 7], T.green, sw=3, dash="6 5", num=1, num_at=0, offset=(0, -8))
            m.route([7, 31, 8, 13, 15], T.amber, sw=4, num=2, num_at=1, offset=(0, 12))
            x, y = m.P(15)
            d.line(x - 14, y - 14, x + 14, y + 14, stroke=T.red, sw=3.5, layer="top")
            d.line(x - 14, y + 14, x + 14, y - 14, stroke=T.red, sw=3.5, layer="top")
            sx, sy, sw_, sh = stall_rect(m, 15)
            label_pill(d, sx + sw_ / 2, sy + sh + 22, "rejected: P15 is 0.61 m from AGV-1", color=T.red,
                       size=10, bg=T.bg_deep, border=T.red)
        else:
            m.route([14, 15, 17, 16], T.green, sw=3, num=1, num_at=2, offset=(0, -8))
            x, y = m.P(16)
            label_pill(d, x + 0.36 * scale + 4, y + 24, "AGV-1 to C16", color=T.green, size=10,
                       bg=T.bg_deep, border=T.green, anchor="start")
            m.route([5, 9, 8, 31, 7], T.green, sw=3, dash="6 5", num=2, num_at=0, offset=(0, -8))
            m.route([7, 31, 8, 13, 15], T.amber, sw=4, num=3, num_at=1, offset=(0, 12))
            x, y, w, h = stall_rect(m, 15)
            label_pill(d, x + w / 2, y + h + 22, "T27 parked on P15", color=T.amber, size=10, bg=T.bg_deep,
                       border=T.amber)
        b = m.box
        d.text(b.x0, b.y0 - 14, title, size=S.h, weight=600, fill=col, layer="labels")
        d.text_lines(b.x0, b.y1 + 18, lines, size=S.small, fill=T.fg2, lh=1.45)
    frame(d, title="SW2-905: the only free stall is beside a charging AGV",
          subtitle="Pecos combined layout (5675_pecos_combined) with the scenario's occupancy: a car on tray 27 in "
                   "bay B7, every stall but P15 holding a tray, AGV-1 idle on C14, AGV-2 under the empty tray at "
                   "P5. The routes on the right are the recorded plan; moves 1 and 2 run at the same time.",
          legend=[("route", T.green, "AGV move (dashed: approach to the tray)"), ("route", T.amber, "tray move"),
                  ("dashbox", C_PARK, "candidate stall")])
    return d


FIGURES = [fig_scenario, fig_context, fig_overlap, fig_substitutions, fig_filter_keep_out,
           fig_filter_stall_search, fig_filter_validation, fig_pipeline, fig_options, fig_pr]


def main():
    OUT.mkdir(exist_ok=True)
    problems = 0
    for fn in FIGURES:
        doc = fn()
        svg = doc.render()
        (OUT / f"{doc.name}.svg").write_text(svg, encoding="utf-8")
        ov = doc.text_overlaps()
        problems += len(ov)
        c = doc.canvas
        flag = "" if not ov else f"   !! {len(ov)} text overlaps: {ov[:4]}"
        print(f"{doc.name:16s} {c.w:5.0f} x {c.h:5.0f}  {len(svg) / 1024:6.1f} KB{flag}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
