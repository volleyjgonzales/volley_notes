"""fig_layout2: figures for the Layout file tab (02-layout-file.html).

109 resource windows (static): the size classes, their indices, the unused buffer, Pecos stall spacing,
    which node allows which size, height_m.
110 edge classification (animated): how PoseGraph turns layout edges into neighbour slots, pose (8, 90).
111 layout validation (animated): what Layout::Layout checks and what it silently accepts.

Sources: sources/5675_pecos_combined.yaml and sources/repomix-common-ros.xml (src/layout.cpp,
src/pose_graph.cpp, src/pose_utils.cpp, src/polygon_utils.cpp, src/agv_motion_type.cpp,
include/common_ros/collision_geometry.hpp). Line numbers are lines of each file inside the snapshot.
"""
from __future__ import annotations

import math

from components import code_panel, connect, frame, label_pill, chip, num_badge
from facility import Map, NODES, WINDOWS
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

DOC = "02-layout-file.html"
CODE_BG = "#0B1222"

BUF_L = 0.1524     # parking_window_buffer.length_m (Pecos YAML)
BUF_W = 0.0762     # parking_window_buffer.width_m
WIN = [("COMPACT", 4.2672, 2.21), ("STANDARD", 5.182, 2.21), ("LARGE", 5.486, 2.21), ("XL", 5.791, 2.21)]
for _n, _l, _w in WIN:      # keep the numbers honest against the YAML
    assert abs(WINDOWS[_n]["length_m"] - _l) < 1e-9 and abs(WINDOWS[_n]["width_m"] - _w) < 1e-9, _n
WCOL = {"TRAY": T.amber, "COMPACT": T.teal, "STANDARD": T.sky, "LARGE": T.violet, "XL": T.green}
# TRAY is drawn at a NOMINAL size: kTrayLength / kTrayWidth / kTrayHeight are not in the snapshots.
TRAY_NOMINAL = (3.75, 1.85)


def _title(d, x, y, n, s, *, color=T.fg):
    d.text(x, y, f"{n}  {s}", size=13.5, weight=600, fill=color)


def _hl(d, panel: BBox, idx, color, *, size=11, title=True, k=None, k_last=None):
    """Highlight code_panel lines `idx` (0-based) during step k (or k..k_last)."""
    lh = size * 1.5
    top = panel.y0 + 14 + (24 if title else 0) + size / 2
    ctx = d.at(k, k_last) if k is not None else None
    if ctx:
        ctx.__enter__()
    for i in idx:
        yy = top + i * lh
        d.rect(panel.x0 + 6, yy - lh / 2, panel.w - 12, lh, rx=3, fill=T.tint(color, 0.22, CODE_BG), layer="main")
    if ctx:
        ctx.__exit__(None, None, None)


def _box(d, x, y, w, h, title, lines, color, *, size=11.5, mono_title=True, dashed=False):
    d.rect(x, y, w, h, rx=8, fill=T.tint(color, 0.08, T.bg), stroke=T.tint(color, 0.7, T.bg), sw=1.4,
           dash="6 4" if dashed else None)
    d.text(x + 12, y + 17, title, size=12, family="mono" if mono_title else "sans", weight=600, fill=color)
    for i, ln in enumerate(lines):
        d.text(x + 12, y + 38 + i * 17, ln, size=size, fill=T.fg2)
    return BBox(x, y, x + w, y + h)


# ======================================================================================
# 109 - resource windows
# ======================================================================================

@figure("109_resource_windows", "Resource windows: the size classes", DOC)
def resource_windows():
    d = Doc("109_resource_windows", "Resource windows: the size classes a node can hold",
            "The four Pecos parking windows plus the TRAY window the parser adds, drawn to scale and nested; their "
            "area-sorted indices 0 to 4 and collision entity ids 4 to 8; the buffer that is added but never used; "
            "Pecos stall spacing against the XL and buffered windows; which nodes allow which size; height_m.")
    K = 112.0
    # ---------------- 1: nested windows to scale ----------------
    _title(d, 0, 0, "1", "The five windows, to scale, centred on the node")
    PW, PH = 880, 476
    d.rect(0, 22, PW, PH, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    cx, cy = 400, 24 + 64 + 2.2862 * K / 2
    order = [("XL", 5.791, 2.21), ("LARGE", 5.486, 2.21), ("STANDARD", 5.182, 2.21), ("COMPACT", 4.2672, 2.21)]
    for name, L, W in order:
        col = WCOL[name]
        d.rect(cx - L * K / 2, cy - W * K / 2, L * K, W * K, fill=T.tint(col, 0.13, T.bg_deep), layer="under")
    for name, L, W in order:
        col = WCOL[name]
        d.rect(cx - L * K / 2, cy - W * K / 2, L * K, W * K, fill="none", stroke=col, sw=1.6)
    tl, tw = TRAY_NOMINAL
    d.rect(cx - tl * K / 2, cy - tw * K / 2, tl * K, tw * K, rx=4, fill=T.tint(WCOL["TRAY"], 0.10, T.bg_deep),
           stroke=WCOL["TRAY"], sw=1.6, dash="5 4")
    d.text(cx, cy - 36, "TRAY  (kTrayLength x kTrayWidth)", size=11.5, family="mono", weight=600,
           fill=WCOL["TRAY"], anchor="middle")
    d.text(cx, cy - 18, "drawn at a nominal size:", size=11, fill=T.muted, anchor="middle")
    d.text(cx, cy - 3, "the constants are not in the snapshots", size=11, fill=T.muted, anchor="middle")
    d.circle(cx, cy + 22, 4, fill=T.fg)
    d.text(cx, cy + 40, "node (x, y)", size=11, family="mono", fill=T.fg2, anchor="middle")
    # buffered XL
    bl, bw = 5.791 + BUF_L, 2.21 + BUF_W
    d.rect(cx - bl * K / 2, cy - bw * K / 2, bl * K, bw * K, fill="none", stroke=T.fg2, sw=1.3, dash="7 5",
           layer="over")
    # band names inside the gaps between the end edges (left side), small
    # length dimension rows
    rows = [("buffered XL  5.9434 m  (5.791 + 0.1524)", bl, T.fg2, "6 4"), ("XL  5.791 m", 5.791, WCOL["XL"], None),
            ("LARGE  5.486 m", 5.486, WCOL["LARGE"], None), ("STANDARD  5.182 m", 5.182, WCOL["STANDARD"], None),
            ("COMPACT  4.2672 m", 4.2672, WCOL["COMPACT"], None),
            ("TRAY  kTrayLength (nominal here)", tl, WCOL["TRAY"], "4 3")]
    ry = cy + bw * K / 2 + 22
    for i, (lab, L, col, dash) in enumerate(rows):
        y = ry + i * 19
        x0, x1 = cx - L * K / 2, cx + L * K / 2
        d.line(x0, y, x1, y, stroke=col, sw=1.3, dash=dash, cap="butt")
        d.line(x0, y - 5, x0, y + 5, stroke=col, sw=1.3)
        d.line(x1, y - 5, x1, y + 5, stroke=col, sw=1.3)
        d.text(cx, y, lab, size=11, family="mono", fill=col, anchor="middle", halo=T.bg_deep, halo_w=5)
    # width dimensions (right)
    for x, W, lab, col, dash in ((cx + bl * K / 2 + 26, 2.21, "2.21 m", WCOL["XL"], None),
                                 (cx + bl * K / 2 + 26 + 92, bw, "2.2862 m", T.fg2, "6 4")):
        y0, y1 = cy - W * K / 2, cy + W * K / 2
        d.line(x, y0, x, y1, stroke=col, sw=1.3, dash=dash, cap="butt")
        d.line(x - 5, y0, x + 5, y0, stroke=col, sw=1.3)
        d.line(x - 5, y1, x + 5, y1, stroke=col, sw=1.3)
        d.text(x + 8, cy - 8, lab, size=11, family="mono", fill=col)
    d.text(cx + bl * K / 2 + 34, cy + 10, "all four", size=10.5, fill=T.muted)
    d.text(cx + bl * K / 2 + 126, cy + 10, "buffered", size=10.5, fill=T.muted)
    # axes
    d.text(22, 44, "length_m runs along body +y, the facing / locomote axis (world x at heading 90 or -90);",
           size=11, fill=T.muted)
    d.text(22, 60, "width_m along body x. The four YAML windows share width 2.21 m, so only the ends differ.",
           size=11, fill=T.muted)

    # ---------------- 2: parser result table ----------------
    tx = PW + 40
    _title(d, tx, 0, "2", "What the parser makes of them (layout.cpp L97-151)")
    cols = [("idx", 0), ("name", 38), ("length x width [m]", 128), ("area [m2]", 300), ("nesting check vs next", 380),
            ("entity id", 590)]
    TW = 720
    hy = 40
    for lab, off in cols:
        d.text(tx + off + 8, hy, lab, size=10.5, family="mono", weight=600, fill=T.muted)
    d.line(tx, hy + 12, tx + TW, hy + 12, stroke=T.border_soft, sw=1)
    trow = [(0, "TRAY", "kTray* (values unknown)", "-", "<= COMPACT (must hold)", "4 = PAYLOAD + 0"),
            (1, "COMPACT", "4.2672 x 2.21", "9.4305", "4.2672 <= 5.182, 2.21 <= 2.21", "5"),
            (2, "STANDARD", "5.182 x 2.21", "11.4522", "5.182 <= 5.486, 2.21 <= 2.21", "6"),
            (3, "LARGE", "5.486 x 2.21", "12.1241", "5.486 <= 5.791, 2.21 <= 2.21", "7"),
            (4, "XL", "5.791 x 2.21", "12.7981", "(last)", "8 = PAYLOAD + 4")]
    for i, row in enumerate(trow):
        y = hy + 34 + i * 27
        col = WCOL[row[1]]
        d.rect(tx, y - 12, TW, 24, rx=4, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        d.rect(tx + 4, y - 8, 4, 16, rx=2, fill=col)
        for j, (lab, off) in enumerate(cols):
            fam = "mono"
            fill = col if j in (0, 1) else (T.fg2 if j != 4 else T.muted)
            d.text(tx + off + 14, y, str(row[j]), size=11.5 if j != 4 else 11, family=fam,
                   weight=700 if j == 1 else 400, fill=fill)
    yy = hy + 34 + 5 * 27 + 4
    for i, ln in enumerate([
            "1. TRAY {kTrayLength, kTrayWidth, kTrayHeight} is appended to the YAML windows.",
            "2. std::sort by length_m x width_m (not stable); TRAY must come out at index 0.",
            "3. Each window must be <= the next in length AND width; equal widths are fine, equal sizes throw.",
            "4. resource_name_to_index_: name -> index (emplace: a duplicate name keeps the first).",
            "5. CollisionTable: one PayloadEntity per window, id = PAYLOAD (4) + index."]):
        d.text(tx + 4, yy + i * 18, ln, size=11.5, fill=T.fg2)
    cp = code_panel(d, tx, yy + 5 * 18 + 6, TW, [
        "if(resource_windows_.at(0).name != \"TRAY\") {",
        "  throw std::runtime_error(\"A parking window smaller than the default tray size was found!\");",
        "}",
        "for(size_t i = 0; i + 1 < resource_windows_.size(); i++) {",
        "  ...  if(a.length_m > b.length_m || a.width_m > b.width_m) {",
        "    throw std::runtime_error(\"Parking windows do not nest within one another!\");",
        "  }  else if(a.length_m == b.length_m && a.width_m == b.width_m) {",
        "    throw std::runtime_error(\"Parking windows of equal size found!\");"],
        title="layout.cpp L132-145 (indentation trimmed, L138-139 elided)", size=11)

    # ---------------- 3: the buffer ----------------
    by = max(22 + PH, cp.y1) + 46
    _title(d, 0, by, "3", "The buffer: added to every window on request, and requested only by unused code")
    bw_, gap = 360, 60
    lane = [
        ("parking_window_buffer", ["YAML: length_m 0.1524 (6 in),", "width_m 0.0762 (3 in); no height"], T.fg2),
        ("Layout::GetBufferedResourceWindow(i)", ["length + 0.1524, width + 0.0762;", "height_m dropped (left 0)"],
         T.fg2),
        ("CalcOverlappingSizedPoses", ["called once in the PoseGraph constructor;", "result kept in overlapping_sized_poses_"],
         T.fg2),
        ("PoseGraph::GetOverlappingSizedPoses", ["the only reader of that result:", "no caller in any snapshot"], T.red),
    ]
    lane2 = [
        ("parking_windows + TRAY", ["the five unbuffered windows,", "sorted and indexed as in 2"], T.green),
        ("Layout::GetResourceWindow(i)", ["returns the window as written", "(no buffer)"], T.green),
        ("CollisionTable::BuildEntityTable", ["PayloadEntity(i, window):", "id = PAYLOAD (4) + i"], T.green),
        ("conflict sets (CollisionTable)", ["what SIPP, CHUGG and the scheduler", "query: unbuffered footprints"], T.green),
    ]
    for li, items in enumerate((lane, lane2)):
        y = by + 26 + li * 96
        prev = None
        for i, (t, lines, col) in enumerate(items):
            x = i * (bw_ + gap)
            b = _box(d, x, y, bw_, 74, t, lines, col)
            if prev:
                connect(d, [(prev.x1, prev.cy), (b.x0, b.cy)], kind="flow", color=T.tint(col, 0.8, T.bg), size=8)
            prev = b
        if li == 0:
            d.line(prev.x1 - 30, y + 10, prev.x1 - 12, y + 28, stroke=T.red, sw=2.4)
            d.line(prev.x1 - 12, y + 10, prev.x1 - 30, y + 28, stroke=T.red, sw=2.4)
    b3y = by + 26 + 2 * 96 - 6
    d.text(0, b3y, "So in these packages the buffer changes nothing that is checked. GarageLayoutMsg.buffer also carries "
                   "a copy for whoever reads that message (no reader in the snapshots).", size=11.5, fill=T.muted)

    # ---------------- 4: Pecos stall spacing ----------------
    sy = b3y + 44
    _title(d, 0, sy, "4", "Pecos stalls P2, P3, P5, P6 against the XL window and the buffered window")
    S4 = 66.0
    m = Map(d, 40, sy + 30, S4, (33.9, 46.3), (6.9, 11.8))
    m.floor(axes=True)
    m.clip()
    for a_, b_ in ((2, 3), (5, 6), (2, 5), (3, 6)):
        (x0, y0), (x1, y1) = m.P(a_), m.P(b_)
        d.line(x0, y0, x1, y1, stroke="#55657F", sw=1.4, layer="edges")
    for nid in (2, 3, 5, 6):
        n = NODES[nid]
        x, y = m.P(nid)
        L, W = 5.791 * S4, 2.21 * S4
        d.rect(x - L / 2, y - W / 2, L, W, fill=T.tint(WCOL["XL"], 0.12, T.bg_deep), stroke=WCOL["XL"], sw=1.3,
               layer="under")
        Lb, Wb = bl * S4, bw * S4
        d.rect(x - Lb / 2, y - Wb / 2, Lb, Wb, fill="none", stroke=T.fg2, sw=1.1, dash="6 4", layer="main")
        d.circle(x, y, 3.2, fill=T.sky, layer="over")
        d.text(x + 8, y - 9, f"P{nid}", size=11, family="mono", weight=600, fill=T.sky, halo=T.bg_deep, halo_w=3)
    # overlap of the buffered windows in x (between columns)
    xm = (NODES[2].x + NODES[3].x) / 2
    ov = (bl - (NODES[3].x - NODES[2].x)) / 2
    for nid_y in (8.2033, 10.4893):
        d.rect(m.X(xm - ov), m.Y(nid_y + bw / 2), 2 * ov * S4, bw * S4, fill=T.tint(T.red, 0.45, T.bg_deep),
               layer="main")
    m.unclip()
    mb = m.box
    # callouts
    gx = m.X(xm)
    d.line(gx, m.Y(8.2033) + 2.21 * S4 / 2 + 2, gx, mb.y1 + 40, stroke=T.red, sw=1, dash="3 3", layer="over")
    d.text(gx, mb.y1 + 52, "x: buffered windows overlap by 152.2 mm", size=11, family="mono", fill=T.red,
           anchor="middle")
    d.text(gx, mb.y1 + 68, "XL windows clear by 0.2 mm", size=11, family="mono", fill=WCOL["XL"], anchor="middle")
    gy = m.Y((NODES[2].y + NODES[5].y) / 2)
    d.line(m.X(NODES[3].x) + 5.791 * S4 / 2 - 30, gy, mb.x1 + 12, gy, stroke=T.fg2, sw=1, dash="3 3", layer="over")
    d.text(mb.x1 + 18, gy - 8, "y: XL clear by 76 mm", size=11, family="mono", fill=WCOL["XL"])
    d.text(mb.x1 + 18, gy + 8, "buffered overlap 0.2 mm", size=11, family="mono", fill=T.fg2)
    # table
    ty = mb.y1 + 96
    hdr = [("", 0), ("node spacing", 150), ("XL window", 270), ("clearance", 370), ("buffered", 480),
           ("clearance", 580)]
    for lab, off in hdr:
        d.text(40 + off, ty, lab, size=10.5, family="mono", weight=600, fill=T.muted)
    d.line(40, ty + 11, 40 + 700, ty + 11, stroke=T.border_soft, sw=1)
    srows = [("y (rows, P2-P5)", "2.2860 m", "2.2100 m", "+76.0 mm", "2.2862 m", "-0.2 mm"),
             ("x (columns, P2-P3)", "5.7912 m", "5.7910 m", "+0.2 mm", "5.9434 m", "-152.2 mm")]
    for i, r in enumerate(srows):
        y = ty + 30 + i * 22
        for j, (lab, off) in enumerate(hdr):
            col = T.fg2
            if j == 3:
                col = WCOL["XL"]
            if j == 5:
                col = T.red
            d.text(40 + off, y, r[j], size=11.5, family="mono" if j else "sans", fill=col)
    d.text(40, ty + 30 + 2 * 22 + 6, "Negative clearance = overlap. Unbuffered (what the collision table uses), "
           "neighbouring stalls just clear;", size=11.5, fill=T.muted)
    d.text(40, ty + 30 + 2 * 22 + 24, "buffered, every neighbouring pair would overlap, by 152 mm along x.",
           size=11.5, fill=T.muted)
    left_bottom = ty + 30 + 2 * 22 + 30

    # ---------------- 5: max_resource_size per node ----------------
    rx0 = 960
    _title(d, rx0, sy, "5", "max_resource_size per node (Pecos)")
    m2 = Map(d, rx0, sy + 30, 19.6, (20.0, 46.5), (6.6, 25.6))
    m2.base(labels=True, axes=False, zones=False)
    for nid in (10, 14, 16):
        x, y = m2.P(nid)
        chip(d, x - 14, y, "TRAY (0)", WCOL["TRAY"], size=10, anchor="end",
             fill=T.tint(WCOL["TRAY"], 0.3, T.bg_deep), layer="top") if nid == 10 else \
            chip(d, x - 8, y + 21, "TRAY (0)", WCOL["TRAY"], size=10, fill=T.tint(WCOL["TRAY"], 0.3, T.bg_deep),
                 layer="top")
    b2 = m2.box
    label_pill(d, b2.x0 + 8, b2.y1 - 16, "every other node (25 of 28): XL (4)", color=WCOL["XL"], size=10.5,
               bg=T.tint(WCOL["XL"], 0.18, T.bg_deep), border=T.tint(WCOL["XL"], 0.6, T.bg_deep), anchor="start")
    # allowed-size matrix
    my_ = b2.y1 + 30
    d.text(rx0, my_, "Sizes allowed at a node: index 0 .. max_resource_size_index", size=12.5, weight=600, fill=T.fg)
    names = ["TRAY", "COMPACT", "STANDARD", "LARGE", "XL"]
    cw_ = 82
    mx0 = rx0 + 170
    for j, nm in enumerate(names):
        d.text(mx0 + j * cw_ + cw_ / 2, my_ + 24, nm, size=10.5, family="mono", weight=600, fill=WCOL[nm],
               anchor="middle")
        d.text(mx0 + j * cw_ + cw_ / 2, my_ + 39, f"{j}  (id {4 + j})", size=10, family="mono", fill=T.muted,
               anchor="middle")
    for i, (lab, top) in enumerate((("25 XL nodes", 4), ("C10, C14, C16", 0))):
        y = my_ + 52 + i * 30
        d.text(rx0, y + 12, lab, size=11.5, fill=T.fg2)
        d.text(rx0 + 104, y + 12, f"index {top}", size=10.5, family="mono", fill=T.muted)
        for j in range(5):
            ok = j <= top
            d.rect(mx0 + j * cw_ + 3, y, cw_ - 6, 24, rx=4, fill=T.tint(T.green if ok else T.red, 0.2 if ok else 0.08, T.bg),
                   stroke=T.tint(T.green if ok else T.red, 0.6 if ok else 0.3, T.bg), sw=1)
            d.text(mx0 + j * cw_ + cw_ / 2, y + 12, "allowed" if ok else "no", size=10.5, family="mono",
                   fill=T.green if ok else T.tint(T.red, 0.8, T.bg), anchor="middle")
    uy = my_ + 52 + 2 * 30 + 16
    uses = [("SIPP GetTraversableEdges", "skips a target pose if collision id > PAYLOAD + index;"),
            ("", "on an AgvCharge node it also refuses every entity but the AGV"),
            ("GetStaticFilter", "disables poses (and their edges) whose index < the payload's window"),
            ("CalcOverlappingSizedPoses", "builds footprints for sizes 0..index only (buffered, see 3)"),
            ("PlanRetrieveJob", "bay fit: payload length, width (and height) vs the bay's window"),
            ("OpenSpaceSearch::OnExpansion", "payload height vs height_m of the node's window")]
    for i, (a_, b_) in enumerate(uses):
        y = uy + i * 18
        d.text(rx0, y, a_, size=11, family="mono", fill=T.sky)
        d.text(rx0 + 214, y, b_, size=11, fill=T.fg2)

    # ---------------- 6: height_m ----------------
    hy6 = max(left_bottom, uy + 6 * 18) + 30
    _title(d, 0, hy6, "6", "height_m: optional, and unset in Pecos")
    hl6 = [
        "Absent: height_m stays 0, which every reader treats as \"unconstrained\" "
        "(GetSmallestEnclosingResourceSizeIndex, PlanRetrieveJob, OpenSpaceSearchEnvironment::OnExpansion).",
        "Present: it must be <= kBayHeight, or the parser throws \"Parking window '<name>' has height_m=<h> which "
        "exceeds the physical bay clearance kBayHeight=<k>\" (layout.cpp L102-108). kBayHeight's value is not in the "
        "snapshots.",
        "TRAY gets kTrayHeight. The buffer drops height (GetBufferedResourceWindowHelper sets only length and width). "
        "Pecos sets no height_m, so its four windows are height-unconstrained."]
    yy = hy6 + 24
    for p in hl6:
        for ln in wrap(p, 1580, 11.5):
            d.text(0, yy, ln, size=11.5, fill=T.fg2)
            yy += 17
        yy += 4

    frame(d, title="Resource windows: the size classes a node can hold",
          subtitle="parking_windows defines discrete payload sizes. The parser adds TRAY, sorts all five by area, "
                   "insists that each fits inside the next, and numbers them 0 to 4; a node's max_resource_size "
                   "admits sizes 0 up to its own. The buffer is added only in code that nothing calls.",
          badge_key="yaml",
          legend=[("box", WCOL["TRAY"], "TRAY (nominal)"), ("box", WCOL["COMPACT"], "COMPACT"),
                  ("box", WCOL["STANDARD"], "STANDARD"), ("box", WCOL["LARGE"], "LARGE"), ("box", WCOL["XL"], "XL"),
                  ("dashbox", T.fg2, "XL + buffer"), ("fill", T.tint(T.red, 0.45, T.bg_deep), "buffered overlap")],
          footnote="Windows, buffer, node coordinates and max_resource_size from 5675_pecos_combined.yaml; parsing, "
                   "sorting and checks from layout.cpp L86-151; buffer from layout.cpp GetBufferedResourceWindowHelper; "
                   "consumers from polygon_utils.cpp, pose_graph.cpp, collision_geometry.hpp/.cpp, the motion planner "
                   "(SIPP, static filtering, open-space search) and the scheduler (PlanRetrieveJob). 'No caller' is "
                   "from a search of all six snapshots; other packages may call it. Clearances are computed from the "
                   "YAML numbers (float32 storage changes them by micrometres).")
    return d


# ======================================================================================
# 110 - edge classification in PoseGraph
# ======================================================================================

SLOT_COL = {"FORWARD": T.sky, "RIGHT": T.amber, "BACK": T.violet, "LEFT": T.green}
SLOT_IDX = {"FORWARD": 0, "RIGHT": 1, "BACK": 2, "LEFT": 3}
SLOT_REL = {"FORWARD": 0.0, "LEFT": 90.0, "BACK": 180.0, "RIGHT": -90.0}
TOL = 0.1          # kAngleToleranceRad (pose_graph.cpp L19)
TOL_MT = 1e-3      # IsLocomoteOrStrafe tolerance (agv_motion_type.cpp L20-21)


def _wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def _classify(src, dst_xy, heading_deg):
    """PoseGraph rule (pose_graph.cpp L103-138). relative = bearing - yaw (SignedAngleDist(a, b) = b - a,
    inferred from GetBayOutboundPose's 'always LEFT' contract)."""
    n = NODES[src]
    dx, dy = dst_xy[0] - n.x, dst_xy[1] - n.y
    bearing = math.degrees(math.atan2(dy, dx))
    rel = _wrap180(bearing - heading_deg)
    slot = None
    for name, c in SLOT_REL.items():
        if abs(_wrap180(rel - c)) < math.degrees(TOL):
            slot = name
    return dx, dy, bearing, rel, slot


@figure("110_edge_classification", "Edge classification: layout edges become neighbour slots (animated)", DOC)
def edge_classification():
    d = Doc("110_edge_classification", "From layout edges to neighbour slots",
            "Animated: PoseGraph classifies each edge of node 8 for pose (8, 90) by the bearing of the edge relative "
            "to the yaw: 31 LEFT, 9 RIGHT, 4 BACK, 13 FORWARD, each within 0.1 rad. Then three hypothetical edits: "
            "a diagonal edge that throws, a disallowed_edge_orientation that removes heading 90 and -90 from edge "
            "8-13, and a 0.1 m misalignment that PoseGraph accepts but GetMotionType rejects.")
    H = 90
    S_ = 56.0
    m = Map(d, 0, 30, S_, (26.8, 38.6), (9.5, 18.1))
    d.text(0, 0, "Node 8 and its graph neighbours (real coordinates)", size=13.5, weight=600, fill=T.fg)
    m.base(labels=True, zones=False, axes=True)
    cx, cy = m.P(8)

    def pt(ang_deg, r):
        a = math.radians(ang_deg)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    # ---- steps ----
    k0 = d.step("Pose (8, 90): W8 at heading 90. PoseGraph measures each edge against yaw = 90 x pi/180 = pi/2 "
                "rad in the atan2 frame (0 = +x, counter-clockwise), which points to +y. The four wedges are the "
                "translation slots: FORWARD at relative bearing 0, LEFT at +pi/2, BACK at pi, RIGHT at -pi/2, each "
                "+-0.1 rad (5.7 deg) wide. The pose faces -x, so LEFT is the facing direction: LEFT and RIGHT are "
                "locomotes, FORWARD and BACK strafes. All eight slots start at -1 (kInvalidIndex).")
    k1 = d.step("Neighbour 31 (28.0253, 12.7753) also allows heading 90, so pose (31, 90) exists. dx = -2.857, "
                "dy = 0: bearing atan2(0, -2.857) = 180 deg; relative to the yaw: +90 deg, inside the LEFT wedge. "
                "Slot LEFT (3) = (31, 90): a locomote toward the approach of bay 7.")
    k2 = d.step("Neighbour 9 (37.1856, 12.7753): dx = +6.3033, dy = 0, bearing 0 deg, relative -90 deg: RIGHT (1) "
                "= (9, 90), the other locomote direction.")
    k3 = d.step("Neighbour 4 (30.8823, 10.4893): dx = 0, dy = -2.286, bearing -90 deg, relative -180 deg, the same "
                "angle as +180: BACK (2) = (4, 90), a strafe.")
    k4 = d.step("Neighbour 13 (30.8823, 17.1663): dy = +4.391, bearing +90 deg, relative 0: FORWARD (0) = (13, 90), "
                "a strafe. Node 8 has rotation_allowed, so ROT_RIGHT (4) = (8, 0) and ROT_LEFT (5) = (8, 180), the "
                "nearest headings clockwise and counter-clockwise; no VRC, so slots 6 and 7 stay -1. Pose (8, -90) "
                "gets the mirror image: FORWARD 4, RIGHT 31, BACK 13, LEFT 9.")
    k5 = d.step("Hypothetical edge 8-5 (not in the YAML). Both nodes allow heading 90, so the edge is classified: "
                "bearing atan2(-2.286, 6.3033) = -19.9 deg, relative -109.9 deg, 19.9 deg (0.35 rad) from RIGHT and "
                "outside every wedge. The PoseGraph constructor throws. Poses are built in node-id order, so pose "
                "(5, -90) gets there first and the message reads \"Edge 5 <-> 8 with invalid translation "
                "connection!\". Had the nodes shared no heading, the edge would be skipped without a word.")
    k6 = d.step("Hypothetical disallowed_edge_orientation: 90 on edge 8-13. IsAngleOrReciprocal(90, heading) is true "
                "for 90 and -90, so (8, 90) loses FORWARD, (8, -90) loses BACK, and 13's poses lose 8. Node 13 has "
                "only those two headings, so the edge is gone from the PoseGraph while Layout::HasEdge(8, 13) stays "
                "true. 8-13 is the only edge between the two YAML sandboxes, so the pose graph would split in two.")
    k7 = d.step("Hypothetical: node 31 moved 0.1 m north (y = 12.8753). Bearing 178.0 deg, relative +88.0 deg: still "
                "inside the 5.7 deg LEFT wedge, so PoseGraph builds the edge. GetMotionType checks the same edge "
                "with IsLocomoteOrStrafe at 1e-3 rad: 2.0 deg (0.035 rad) is neither a locomote nor a strafe, and "
                "it throws \"Edge traversal is not perpendicular to where we are.\" on the first command that uses it.")
    k8 = d.step("The complete picture: the four Pecos edges of node 8 fill slots 0 to 3 of (8, 90), rotation fills "
                "4 and 5. Three rules to remember when editing edges: an off-axis edge throws only when the two "
                "nodes share a heading; a disallowed orientation removes a heading and its reciprocal from one "
                "edge; and PoseGraph's 0.1 rad tolerance is 100 times looser than the 1e-3 rad of GetMotionType.")

    # ---- wedges ----
    r0, r1 = 26, 104
    tol = math.degrees(TOL)
    for name, rel in SLOT_REL.items():
        c = H + rel
        col = SLOT_COL[name]
        a0, a1 = c - tol, c + tol
        p0, p1, p2, p3 = pt(a0, r0), pt(a0, r1), pt(a1, r1), pt(a1, r0)
        path = (f"M{p0[0]:.2f} {p0[1]:.2f} L{p1[0]:.2f} {p1[1]:.2f} A{r1} {r1} 0 0 0 {p2[0]:.2f} {p2[1]:.2f} "
                f"L{p3[0]:.2f} {p3[1]:.2f} A{r0} {r0} 0 0 1 {p0[0]:.2f} {p0[1]:.2f} Z")
        d.path(path, fill=T.tint(col, 0.32, T.bg_deep), stroke=col, sw=1, layer="over", opacity=0.9,
               bbox=BBox(min(p0[0], p1[0], p2[0], p3[0]), min(p0[1], p1[1], p2[1], p3[1]),
                         max(p0[0], p1[0], p2[0], p3[0]), max(p0[1], p1[1], p2[1], p3[1])))
    lab = {"FORWARD": (cx + 12, cy - 96, "start", "rel 0"), "BACK": (cx + 12, cy + 70, "start", "rel pi"),
           "LEFT": (cx - 72, cy + 18, "middle", "rel +pi/2"), "RIGHT": (cx + 72, cy + 18, "middle", "rel -pi/2")}
    for name, (x, y, anc, rl) in lab.items():
        d.text(x, y, f"{name} {SLOT_IDX[name]}", size=10.5, family="mono", weight=700, fill=SLOT_COL[name],
               anchor=anc, halo=T.bg_deep, halo_w=4)
        d.text(x, y + 14, rl, size=10, family="mono", fill=T.muted, anchor=anc, halo=T.bg_deep)
    # yaw arc from +x to +y
    ra = 64
    q0, q1 = pt(8, ra), pt(82, ra)
    d.path(f"M{q0[0]:.2f} {q0[1]:.2f} A{ra} {ra} 0 0 0 {q1[0]:.2f} {q1[1]:.2f}", stroke=T.pink, sw=1.6,
           layer="top", bbox=BBox(q1[0], q1[1], q0[0], q0[1]))
    d.arrowhead(pt(86, ra), pt(78, ra), kind="filled", color=T.pink, size=7)
    d.line(cx, cy, cx + 74, cy, stroke=T.pink, sw=1, dash="3 3", layer="top")
    d.text(pt(40, ra + 10)[0], pt(40, ra + 10)[1] - 2, "yaw pi/2", size=10.5, family="mono", fill=T.pink,
           halo=T.bg_deep, halo_w=4)
    # facing arrow (house convention, figure 78)
    d.line(cx - 6, cy, cx - 40, cy, stroke=T.fg, sw=2.6, layer="top")
    d.arrowhead((cx - 48, cy), (cx, cy), kind="filled", color=T.fg, size=9)
    d.text(cx - 58, cy - 12, "faces", size=10, fill=T.fg, anchor="middle", halo=T.bg_deep, halo_w=4)
    d.circle(cx, cy, 6, fill=T.fg2, stroke=T.bg_deep, sw=2, layer="top")

    # ---- classified edges ----
    nb = [(31, "LEFT", k1, (0, 20), "middle"), (9, "RIGHT", k2, (-14, -14), "end"),
          (4, "BACK", k3, (14, 0), "start"), (13, "FORWARD", k4, (14, 0), "start")]
    for nid, slot, k, (ox, oy), anc in nb:
        col = SLOT_COL[slot]
        x, y = m.P(nid)
        with d.at(k):
            d.line(cx, cy, x, y, stroke=col, sw=3.2, layer="edges")
            chip(d, x + ox, y + oy, f"({nid}, 90)", col, size=10,
                 anchor=anc, fill=T.tint(col, 0.28, T.bg_deep), layer="top")
        with d.only(k):
            d.circle(x, y, 13, fill="none", stroke=col, sw=2, layer="top")
    # hypothetical diagonal 8-5
    x5, y5 = m.P(5)
    with d.only(k5):
        d.line(cx, cy, x5, y5, stroke=T.red, sw=2.6, dash="7 5", layer="top")
        _, _, b85, rel85, _ = _classify(8, (NODES[5].x, NODES[5].y), H)
        q0, q1 = pt(0, 150), pt(b85, 150)
        d.path(f"M{q0[0]:.2f} {q0[1]:.2f} A150 150 0 0 1 {q1[0]:.2f} {q1[1]:.2f}", stroke=T.red, sw=1.4,
               layer="top", bbox=BBox(q1[0], q0[1], q0[0], q1[1]))
        d.text(pt(-10, 158)[0] + 4, pt(-10, 158)[1], f"{abs(b85):.1f} deg off RIGHT", size=10.5, family="mono",
               fill=T.red, halo=T.bg_deep, halo_w=4)
        chip(d, x5 + 10, y5 + 20, "hyp. edge 8-5: throws", T.red, size=10, anchor="end",
             fill=T.tint(T.red, 0.25, T.bg_deep), layer="top")
    # DEO on 8-13
    x13, y13 = m.P(13)
    with d.only(k6):
        d.line(cx, cy, x13, y13, stroke=T.red, sw=3.4, layer="top")
        mx_, my_ = cx, (cy + y13) / 2 - 20
        d.line(mx_ - 9, my_ - 9, mx_ + 9, my_ + 9, stroke=T.red, sw=2.6, layer="top")
        d.line(mx_ + 9, my_ - 9, mx_ - 9, my_ + 9, stroke=T.red, sw=2.6, layer="top")
        label_pill(d, mx_ + 16, my_, "disallowed_edge_orientation: 90 (hyp.)", color=T.red, size=10.5,
                   bg=T.tint(T.red, 0.15, T.bg_deep), border=T.tint(T.red, 0.6, T.bg_deep), anchor="start")
    # misaligned 31
    x31, y31 = m.P((NODES[31].x, NODES[31].y + 0.1))
    with d.only(k7):
        d.line(cx, cy, x31, y31, stroke=T.red, sw=2.2, dash="5 4", layer="top")
        d.circle(x31, y31, 6, fill=T.bg_deep, stroke=T.red, sw=1.8, dash="3 2", layer="top")
        chip(d, x31 - 30, y31 - 46, "31 moved +0.1 m (hyp.)", T.red, size=10, anchor="start",
             fill=T.tint(T.red, 0.25, T.bg_deep), layer="top")

    # ---- slots of (8, 90) ----
    mb = m.box
    sy0 = mb.y1 + 58
    d.text(0, sy0, "pose_neighbors_ for pose (8, 90): 8 slots per pose", size=13, weight=600, fill=T.fg)
    slots = [("FORWARD", 0, "(13, 90)", k4), ("RIGHT", 1, "(9, 90)", k2), ("BACK", 2, "(4, 90)", k3),
             ("LEFT", 3, "(31, 90)", k1), ("ROT_RIGHT", 4, "(8, 0)", k4), ("ROT_LEFT", 5, "(8, 180)", k4),
             ("VRC_UP", 6, None, None), ("VRC_DOWN", 7, None, None)]
    cw_ = mb.w / 4
    for i, (name, idx, val, k) in enumerate(slots):
        x = (i % 4) * cw_
        y = sy0 + 18 + (i // 4) * 50
        col = SLOT_COL.get(name, T.teal if name.startswith("ROT") else T.faint)
        d.rect(x + 2, y, cw_ - 6, 42, rx=6, fill=T.tint(col, 0.08, T.bg), stroke=T.tint(col, 0.5, T.bg), sw=1)
        d.text(x + 12, y + 13, f"{idx}  {name}", size=10.5, family="mono", weight=600, fill=col)
        if val is None:
            d.text(x + 12, y + 31, "-1", size=11.5, family="mono", fill=T.faint)
            continue
        with d.at(0, k - 1):
            d.text(x + 12, y + 31, "-1", size=11.5, family="mono", fill=T.faint)
        if name == "FORWARD":
            with d.at(k, k5):
                d.text(x + 12, y + 31, val, size=11.5, family="mono", weight=600, fill=T.fg)
            with d.only(k6):
                d.text(x + 12, y + 31, "-1  (DEO)", size=11.5, family="mono", fill=T.red)
            with d.at(k7):
                d.text(x + 12, y + 31, val, size=11.5, family="mono", weight=600, fill=T.fg)
        else:
            with d.at(k):
                d.text(x + 12, y + 31, val, size=11.5, family="mono", weight=600, fill=T.fg)
    with d.at(k4):
        d.text(0, sy0 + 18 + 2 * 50 + 10, "pose (8, -90): FORWARD (4, -90), RIGHT (31, -90), BACK (13, -90), "
               "LEFT (9, -90)", size=11, family="mono", fill=T.fg2)
        d.text(0, sy0 + 18 + 2 * 50 + 28, "poses (8, 0), (8, 180): no neighbour allows heading 0 or 180, so only "
               "rotation slots", size=11, family="mono", fill=T.fg2)

    # ---- table ----
    tx = mb.x1 + 50
    d.text(tx, 0, "atan2 bearing, relative bearing, slot", size=13.5, weight=600, fill=T.fg)
    cols = [("to", 0), ("dx, dy [m]", 52), ("bearing", 210), ("relative", 300), ("slot", 390), ("motion type", 510)]
    TW = 760
    for lab_, off in cols:
        d.text(tx + off + 8, 30, lab_, size=10.5, family="mono", weight=600, fill=T.muted)
    d.line(tx, 42, tx + TW, 42, stroke=T.border_soft, sw=1)

    def row(i, k_first, k_last, nid, xy, mt, *, hyp=False, slot_txt=None, label=None):
        dx, dy, bear, rel, slot = _classify(8, xy, H)
        y = 62 + i * 28
        col = SLOT_COL.get(slot, T.red) if not hyp else T.red
        with d.at(k_first, k_last):
            d.rect(tx, y - 12, TW, 24, rx=4, fill=T.tint(col, 0.10, T.bg))
            vals = [label or str(nid), f"{dx:+.4f}, {dy:+.4f}", f"{bear:+.1f} deg",
                    ("+-180.0 deg" if abs(abs(rel) - 180) < 1e-6 else f"{rel:+.1f} deg"),
                    slot_txt or f"{slot} ({SLOT_IDX[slot]})", mt]
            for j, (lab_, off) in enumerate(cols):
                d.text(tx + off + 8, y, vals[j], size=11.5, family="mono", weight=700 if j in (0, 4) else 400,
                       fill=col if j in (0, 4) else T.fg2)
    row(0, k1, None, 31, (NODES[31].x, NODES[31].y), "LOCOMOTE")
    row(1, k2, None, 9, (NODES[9].x, NODES[9].y), "LOCOMOTE")
    row(2, k3, None, 4, (NODES[4].x, NODES[4].y), "STRAFE")
    row(3, k4, None, 13, (NODES[13].x, NODES[13].y), "STRAFE")
    row(4, k5, k5, 5, (NODES[5].x, NODES[5].y), "-", hyp=True, slot_txt="none: throw", label="5 hyp")
    row(4, k6, k6, 13, (NODES[13].x, NODES[13].y), "-", hyp=True, slot_txt="skipped (DEO)", label="13 hyp")
    row(4, k7, k7, 31, (NODES[31].x, NODES[31].y + 0.1), "throws (1e-3)", hyp=True, slot_txt="LEFT (3)",
        label="31 hyp")
    d.text(tx, 62 + 5 * 28 - 4, "relative = SignedAngleDist(yaw, bearing) = bearing - yaw, wrapped; yaw = 90 deg. "
           "Slot if within 0.1 rad (5.73 deg) of 0, +90, 180 or -90.", size=11, fill=T.muted)
    d.text(tx, 62 + 5 * 28 + 13, "Motion type from IsLocomoteOrStrafe: along yaw + pi/2 (or its reciprocal) = "
           "LOCOMOTE, along yaw = STRAFE.", size=11, fill=T.muted)

    # ---- code ----
    cy0 = 62 + 5 * 28 + 34
    code = ["constexpr double kAngleToleranceRad = 0.1;  // ~5.7 deg",
            "// Skip edges with disallowed orientations.",
            "auto deo = layout_->GetDisallowedEdgeOrientation(pose.node_id, node_dest.id);",
            "if(deo.has_value() && volley::IsAngleOrReciprocal(deo.value(), pose.heading)) {",
            "  continue;",
            "}",
            "double bearing_from_source_rad = std::atan2(node_dest.y - node.y, node_dest.x - node.x);",
            "double relative_bearing = volley::SignedAngleDist(heading_rad, bearing_from_source_rad);",
            "if(volley::AngleDist(relative_bearing, 0.0) < kAngleToleranceRad) {          // FORWARD",
            "} else if(volley::AngleDist(relative_bearing, M_PI_2) < kAngleToleranceRad) {  // LEFT",
            "} else if(volley::AngleDist(relative_bearing, M_PI) < kAngleToleranceRad) {    // BACK",
            "} else if(volley::AngleDist(relative_bearing, -M_PI_2) < kAngleToleranceRad) { // RIGHT",
            "} else {",
            "  throw std::runtime_error(\"Edge \" + std::to_string(node.id) + \" <-> \" +",
            "      std::to_string(node_dest.id) + \" with invalid translation connection!\");",
            "}"]
    cp = code_panel(d, tx, cy0, TW, code, size=11,
                    title="pose_graph.cpp L19, L97-138 (per pose, per neighbour; slot assignments and logging elided)")
    _hl(d, cp, [6, 7], T.pink, k=k1, k_last=k4)
    _hl(d, cp, [9], SLOT_COL["LEFT"], k=k1, k_last=k1)
    _hl(d, cp, [11], SLOT_COL["RIGHT"], k=k2, k_last=k2)
    _hl(d, cp, [10], SLOT_COL["BACK"], k=k3, k_last=k3)
    _hl(d, cp, [8], SLOT_COL["FORWARD"], k=k4, k_last=k4)
    _hl(d, cp, [6, 7, 12, 13, 14], T.red, k=k5, k_last=k5)
    _hl(d, cp, [2, 3, 4], T.red, k=k6, k_last=k6)
    _hl(d, cp, [0, 9], T.red, k=k7, k_last=k7)

    # ---- step 7: tolerance mismatch ----
    ty7 = cp.y1 + 30
    with d.only(k7):
        d.text(tx, ty7, "Same edge, two tolerances", size=13, weight=600, fill=T.red)
        cp2 = code_panel(d, tx, ty7 + 14, TW, [
            "const double edge_heading = atan2(dst_node.y - src_node.y, dst_node.x - src_node.x);",
            "const bool locomote = volley::IsNearToAngleOrReciprocal(edge_heading, heading + M_PI_2, 1e-3);",
            "const bool strafe = volley::IsNearToAngleOrReciprocal(edge_heading, heading, 1e-3);",
            "// GetMotionType, L84, when neither (or both) is true:",
            "throw std::invalid_argument {\"GetMotionType() Edge traversal is not perpendicular to where we are.\"};"],
            title="agv_motion_type.cpp L19-21, L84 (IsLocomoteOrStrafe / GetMotionType)", size=11)
        yy = cp2.y1 + 24
        hdr = [("edge", 0), ("length", 120), ("PoseGraph accepts an offset up to", 230),
               ("GetMotionType up to", 520)]
        for lab_, off in hdr:
            d.text(tx + off, yy, lab_, size=10.5, family="mono", weight=600, fill=T.muted)
        for i, (e, L) in enumerate((("8-31", 2.857), ("8-9", 6.3033), ("9-10 (charger)", 0.6096))):
            y = yy + 22 + i * 20
            d.text(tx, y, e, size=11.5, family="mono", fill=T.fg2)
            d.text(tx + 120, y, f"{L:.4f} m", size=11.5, family="mono", fill=T.fg2)
            d.text(tx + 230, y, f"{L * math.tan(TOL) * 1000:.1f} mm  (L x tan 0.1)", size=11.5, family="mono",
                   fill=T.green)
            d.text(tx + 520, y, f"{L * math.tan(TOL_MT) * 1000:.2f} mm", size=11.5, family="mono", fill=T.red)
    # ---- final: summary ----
    with d.at(k8):
        d.text(tx, ty7, "Three rules for edge authors", size=13, weight=600, fill=T.fg)
        cards = [
            ("1  Off-axis edges", T.red,
             ["Nodes that share a heading: the PoseGraph constructor throws",
              "\"Edge a <-> b with invalid translation connection!\".",
              "No shared heading: the edge yields no pose edge, silently."]),
            ("2  disallowed_edge_orientation", T.amber,
             ["Removes heading h AND h + 180 on that one edge (both directions).",
              "The layout edge stays: HasEdge, GetNeighboringNodes, tape.",
              "Not range-checked and not checked against the node headings."]),
            ("3  Tolerance: 0.1 rad vs 1e-3 rad", T.violet,
             ["PoseGraph accepts 5.7 deg; IsLocomoteOrStrafe 0.057 deg.",
              "On 8-31 a 2.86 mm offset already fails GetMotionType;",
              "PoseGraph would accept 287 mm. Keep edges exactly axis-aligned."])]
        for i, (t, col, lines) in enumerate(cards):
            y = ty7 + 16 + i * 90
            d.rect(tx, y, TW, 82, rx=8, fill=T.tint(col, 0.07, T.bg), stroke=T.tint(col, 0.6, T.bg), sw=1.3)
            d.text(tx + 14, y + 17, t, size=12.5, weight=600, fill=col)
            for j, ln in enumerate(lines):
                d.text(tx + 14, y + 36 + j * 16, ln, size=11.5, fill=T.fg2)

    frame(d, title="From layout edges to neighbour slots",
          subtitle="The YAML edges are undirected and carry no direction names. PoseGraph gives them names per pose: "
                   "it takes the atan2 bearing of each edge, subtracts the pose's yaw and snaps the result to one of "
                   "four slots, within 0.1 rad. Step through the four neighbours of pose (8, 90), then three "
                   "hypothetical edits that throw, remove an edge, or pass here and fail later.",
          badge_key="yaml",
          legend=[("box", SLOT_COL["FORWARD"], "FORWARD 0 (strafe)"), ("box", SLOT_COL["RIGHT"], "RIGHT 1 (locomote)"),
                  ("box", SLOT_COL["BACK"], "BACK 2 (strafe)"), ("box", SLOT_COL["LEFT"], "LEFT 3 (locomote)"),
                  ("line", T.pink, "yaw reference"), ("dash", T.red, "hypothetical edit")],
          footnote="Coordinates and edges from 5675_pecos_combined.yaml; the edge 8-5, the orientation on 8-13 and the "
                   "moved node 31 are hypothetical. Rules from pose_graph.cpp L58-165 and agv_motion_type.cpp. The "
                   "sign convention SignedAngleDist(a, b) = b - a is inferred (volley::SignedAngleDist is not in the "
                   "snapshots); it is the one under which GetBayOutboundPose's documented 'always LEFT' holds for bays "
                   "7 and 21. The enum order is FORWARD 0, RIGHT 1, BACK 2, LEFT 3 (pose_graph.hpp); the code tests "
                   "FORWARD, LEFT, BACK, RIGHT, which cannot matter because the wedges do not overlap.")
    return d


# ======================================================================================
# 111 - layout validation
# ======================================================================================

def _yaml_panel(d, x, y, w, lines, *, title="YAML (illustrative)", size=11.5):
    """YAML block. lines: str, or (text, comment, comment_color) with the comment drawn after '  # '."""
    pad, lh = 14, size * 1.5
    h = pad * 2 + 24 + len(lines) * lh - (lh - size)
    d.rect(x, y, w, h, rx=10, fill=CODE_BG, stroke=T.border_soft, sw=1)
    d.text(x + pad, y + pad + 6, title, size=11, family="mono", weight=600, fill=T.muted)
    yy = y + pad + 24 + size / 2
    for ln in lines:
        if isinstance(ln, tuple):
            t, c, col = ln
            runs = [(t, "mono", 400, T.fg)]
            if c:
                runs.append(("  # " + c, "mono", 600, col))
            d.rich(x + pad, yy, runs, size=size)
        else:
            d.text(x + pad, yy, ln, size=size, family="mono", fill=T.fg if not ln.lstrip().startswith("#") else T.faint)
        yy += lh
    return BBox(x, y, x + w, y + h)


@figure("111_layout_validation", "Layout validation: what the parser checks and what it accepts (animated)", DOC)
def layout_validation():
    d = Doc("111_layout_validation", "What the layout parser checks, and what it silently accepts",
            "Animated: a four-node illustrative layout parsed by Layout::Layout, then five faults that load without "
            "an error (an edge to an unknown id, a duplicate node id, a misspelt optional key, a heading listed with "
            "its reciprocal, an empty VRC node list), the checks that do throw, and a summary of checked versus "
            "not checked.")
    OK, BAD, WARN = T.green, T.red, T.amber
    k0 = d.step("A valid four-node layout. The parser stores the nodes in nodes_, sorts them by id, and numbers "
                "them: node_id_to_index_ maps id 2, 4, 6, 8 to index 0, 1, 2, 3. graph_ is a Boost graph over "
                "those indices; each YAML edge becomes add_edge(node_id_to_index_[a], node_id_to_index_[b]).")
    k1 = d.step("(a) An edge to an id that does not exist: {src: 6, dst: 99}. node_id_to_index_ is a std::map and "
                "operator[] inserts the missing key with value 0, so 99 -> 0 and the edge joins node 6 to index 0, "
                "the lowest id (Bay 2). HasNode(99) is now true and GetNodeById(99) returns node 2's data. PoseGraph "
                "then puts both 4 and 2 into the LEFT slot of (6, 90) and only logs \"silent loss of an edge\".")
    k2 = d.step("(b) A second node with id 4. Both copies stay in nodes_ (indices 1 and 2, in an unspecified order: "
                "std::sort is not stable). The index loop is last-wins, so id 4 maps to 2 and the copy at index 1 is "
                "unreachable by id but still produces poses: (4, -90) and (4, 90) exist twice, and node 4 is listed "
                "under both Waypoint and Parking in node_ids_by_type_.")
    k3 = d.step("(c) A typo in an optional key: faces_reciprocol: true. The parser only looks up the keys it knows, "
                "so faces_reciprocal stays false and nothing is reported. Bay 2's inbound heading becomes 90 instead "
                "of Wrap(270) = -90, and GetBayOutboundPose(2) finds no LEFT neighbour of (2, 90): nullopt instead of "
                "(4, -90). Every optional key behaves this way.")
    k4 = d.step("(d) A heading listed with its reciprocal: headings: [0, 180] on node 6. GetAllowedHeadings adds "
                "h and Wrap(h + 180) for each entry, so node 6 gets 0, 0, 180, 180: four poses, two of them "
                "duplicates (pose_indices_ keeps the first). And because 4 and 8 allow only 90 and -90, the edges "
                "4-6 and 6-8 produce no pose edges at all, also without a message.")
    k5 = d.step("(e) A VRC with an empty node list. The loop bound vrc.nodes.size() - 1 is unsigned: 0 - 1 wraps to "
                "SIZE_MAX, the loop runs and reads vrc.nodes[0] and vrc.nodes[1] of an empty vector, which is "
                "undefined behaviour (in practice a crash, or garbage ids that operator[] inserts as in (a)). "
                "root_node is never checked against the node list.")
    k6 = d.step("What IS checked: an unknown node type, an unknown max_resource_size, windows that are smaller than "
                "TRAY, do not nest or are equal, height_m above kBayHeight, an unknown VRC node id, and (in "
                "PoseGraph) a node without headings and an off-axis shared-heading edge. A missing required key "
                "throws from yaml-cpp, without naming the node.")
    k7 = d.step("Summary. Required keys and enumerated values are checked; references between parts of the file "
                "(edge ids, duplicate ids, VRC lists), optional key names and heading sets are not. The five faulty "
                "lines are in layout.cpp, pose_utils.cpp and pose_graph.cpp; a lint pass or .at() instead of "
                "operator[] would catch (a), (b) and (e) at load.")

    # ---------------- panel A: YAML ----------------
    AX, AW = 0, 430
    d.text(AX, 0, "The input", size=13.5, weight=600, fill=T.fg)
    base_nodes = ["nodes:   # max_resource_size / rotation_allowed omitted",
                  "  - {id: 2, x: 0.0, y: 0.0, type: Bay,",
                  "     headings: [90], faces_reciprocal: true}",
                  "  - {id: 4, x: 4.0, y: 0.0, type: Waypoint, headings: [90]}",
                  "  - {id: 6, x: 8.0, y: 0.0, type: Waypoint, headings: [90]}",
                  "  - {id: 8, x: 8.0, y: 2.3, type: Parking, headings: [90]}"]
    base_edges = ["edges:", "  - {src: 2, dst: 4}", "  - {src: 4, dst: 6}", "  - {src: 6, dst: 8}"]
    yamls = {
        k0: base_nodes + base_edges,
        k1: base_nodes + base_edges + [("  - {src: 6, dst: 99}", "(a) no node 99", BAD)],
        k2: base_nodes + [("  - {id: 4, x: 4.0, y: 2.3, type: Parking, headings: [90]}", None, BAD),
                          ("", "(b) second id 4", BAD)] + base_edges,
        k3: ["nodes:", "  - {id: 2, x: 0.0, y: 0.0, type: Bay,",
             ("     headings: [90], faces_reciprocol: true}", None, BAD), ("", "(c) typo: ...reciprocol", BAD)]
            + base_nodes[3:] + base_edges,
        k4: base_nodes[:4] + [("  - {id: 6, x: 8.0, y: 0.0, type: Waypoint,", None, BAD),
                              ("     headings: [0, 180]}", "(d) 180 = reciprocal of 0", BAD)]
            + base_nodes[5:] + base_edges,
        k5: base_nodes + base_edges + ["vrcs:", "  - id: 1", "    root_node: 4",
                                       ("    nodes: []", "(e) empty list", BAD)],
        k6: ["# each of these makes Layout::Layout throw:",
             ("  type: Elevator", "unknown node type", OK),
             ("  max_resource_size: XXL", "unknown window name", OK),
             ("  - {name: COMPACT, length_m: 4.0, width_m: 2.3}", None, OK),
             ("  - {name: STANDARD, length_m: 5.2, width_m: 2.2}", "do not nest", OK),
             ("  - {name: XL, length_m: 5.791, width_m: 2.21, height_m: 9}", None, OK),
             ("", "above kBayHeight (if kBayHeight < 9)", OK),
             ("  nodes: [4, 77]", "VRC: no node 77", OK),
             ("  headings: []", "PoseGraph: no headings", OK),
             ("  - {id: 5, x: 1.0}", "required key missing (yaml-cpp)", OK)],
        k7: ["# all five faults load without an error:",
             ("  - {src: 6, dst: 99}", "(a) unknown id", BAD),
             ("  - {id: 4, ...}  (a second time)", "(b) duplicate id", BAD),
             ("  faces_reciprocol: true", "(c) misspelt key", BAD),
             ("  headings: [0, 180]", "(d) reciprocal pair", BAD),
             ("  nodes: []", "(e) empty VRC", BAD)],
    }
    yb = {}
    for k, lines in yamls.items():
        with d.only(k):
            yb[k] = _yaml_panel(d, AX, 20, AW, lines, size=11)

    # ---------------- panel B: drawing ----------------
    BX, BW, BY, BH = AW + 30, 400, 20, 330
    d.text(BX, 0, "As the parser sees it", size=13.5, weight=600, fill=T.fg)
    d.rect(BX, BY, BW, BH, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    G = 40.0

    def P(x, y):
        return BX + 40 + x * G, BY + 210 - y * G

    base_xy = {2: (0, 0), 4: (4, 0), 6: (8, 0), 8: (8, 2.3)}
    types = {2: "Bay", 4: "Waypoint", 6: "Waypoint", 8: "Parking"}
    tcol = {"Bay": T.teal, "Waypoint": T.fg2, "Parking": T.sky}

    def node(nid, xy, idx, *, col=None, dashed=False, idx_col=T.muted, tlabel=True):
        x, y = P(*xy)
        c = col or tcol[types.get(nid, "Waypoint")]
        d.circle(x, y, 13, fill=T.tint(c, 0.2, T.bg_deep), stroke=c, sw=1.6, dash="3 2" if dashed else None,
                 layer="over")
        d.text(x, y + 0.5, str(nid), size=12, family="mono", weight=700, fill=T.fg, anchor="middle", layer="top")
        if nid == 8 and xy == base_xy[8]:
            d.text(x - 18, y + 4, idx, size=10.5, family="mono", fill=idx_col, anchor="end", layer="top")
        else:
            d.text(x, y + 26, idx, size=10.5, family="mono", fill=idx_col, anchor="middle", layer="top")

    def edge(a, b, *, col="#55657F", dash=None, sw=2):
        (x0, y0), (x1, y1) = P(*base_xy[a]), P(*base_xy[b])
        d.line(x0, y0, x1, y1, stroke=col, sw=sw, dash=dash, layer="edges")

    for nid, xy in base_xy.items():
        x, y = P(*xy)
        d.text(x - 14, y - 20, types[nid], size=10, fill=tcol[types[nid]], anchor="start" if nid == 2 else "middle",
               halo=T.bg_deep, halo_w=3) if nid != 8 else d.text(x + 18, y - 4, types[nid], size=10,
                                                                    fill=tcol[types[nid]], halo=T.bg_deep)
    d.text(BX + 14, BY + BH - 14, "node id in the circle, [index in nodes_] below", size=10.5, fill=T.faint)
    # default nodes (all steps except where overridden)
    with d.at(k0, k1):
        for nid, i in ((2, 0), (4, 1), (6, 2), (8, 3)):
            node(nid, base_xy[nid], f"[{i}]")
    with d.at(k3, k7):
        for nid, i in ((2, 0), (4, 1), (6, 2), (8, 3)):
            if nid == 6:
                continue
            node(nid, base_xy[nid], f"[{i}]")
    with d.only(k2):
        node(2, base_xy[2], "[0]")
        node(4, base_xy[4], "[1] or [2]", idx_col=BAD)
        node(4, (4, 2.3), "[2] or [1]", col=T.sky, dashed=True, idx_col=BAD)
        node(6, base_xy[6], "[3]")
        node(8, base_xy[8], "[4]")
        x, y = P(4, 2.3)
        d.text(x, y - 22, "Parking (second id 4)", size=10, fill=BAD, anchor="middle", halo=T.bg_deep)
    with d.at(k3, k3):
        node(6, base_xy[6], "[2]")
    with d.at(k5, k7):
        node(6, base_xy[6], "[2]")
    with d.only(k4):
        node(6, base_xy[6], "[2]", col=BAD)
    # edges
    with d.at(k0, k1):
        edge(2, 4), edge(4, 6), edge(6, 8)
    with d.only(k2):
        edge(2, 4, col=BAD), edge(4, 6, col=BAD), edge(6, 8)
        x, y = P(4, 0)
        d.text(x, y + 48, "edges use index 2 (last wins);", size=10.5, fill=BAD, anchor="middle")
        d.text(x, y + 62, "the other copy has no edges", size=10.5, fill=BAD, anchor="middle")
    with d.at(k3, k3):
        edge(2, 4), edge(4, 6), edge(6, 8)
    with d.at(k5, k7):
        edge(2, 4), edge(4, 6), edge(6, 8)
    with d.only(k4):
        edge(2, 4)
        edge(4, 6, col=T.faint, dash="4 4", sw=1.4)
        edge(6, 8, col=T.faint, dash="4 4", sw=1.4)
        x, y = P(6, 0)
        d.text(x, y + 48, "4-6, 6-8: no shared heading,", size=10.5, fill=BAD, anchor="middle")
        d.text(x, y + 62, "so no pose edges (silent)", size=10.5, fill=BAD, anchor="middle")
        x6, y6 = P(8, 0)
        d.text(x6 + 20, y6 - 52, "poses 0, 0, 180, 180", size=10.5, family="mono", fill=BAD, anchor="end",
               halo=T.bg_deep)
    # (a) phantom edge
    with d.only(k1):
        (x0, y0), (x1, y1) = P(8, 0), P(0, 0)
        d.path(f"M{x0:.1f} {y0 + 12:.1f} Q{(x0 + x1) / 2:.1f} {y0 + 120:.1f} {x1:.1f} {y1 + 12:.1f}", stroke=BAD,
               sw=2.2, dash="6 4", layer="edges", bbox=BBox(x1, y0, x0, y0 + 66))
        d.text((x0 + x1) / 2, y0 + 76, "edge 6-99 = add_edge(2, 0): joins 6 to Bay 2", size=10.5, fill=BAD,
               anchor="middle", halo=T.bg_deep)
        chip(d, P(0, 2.3)[0] - 20, P(0, 2.3)[1] - 4, "99 -> index 0", BAD, size=10.5, anchor="start",
             fill=T.tint(BAD, 0.2, T.bg_deep), layer="top")
    # (c) facing arrows at the bay
    with d.only(k3):
        x, y = P(0, 0)
        d.line(x + 16, y - 36, x + 52, y - 36, stroke=OK, sw=2, dash="4 3", layer="top")
        d.arrowhead((x + 60, y - 36), (x + 16, y - 36), kind="filled", color=OK, size=8)
        d.text(x + 66, y - 36, "intended: -90 (faces +x)", size=10.5, family="mono", fill=OK, halo=T.bg_deep)
        d.line(x - 2, y - 56, x - 2 - 0.1, y - 56, stroke=BAD, sw=0.1)
        d.line(x + 52, y - 58, x + 16, y - 58, stroke=BAD, sw=2, layer="top")
        d.arrowhead((x + 8, y - 58), (x + 52, y - 58), kind="filled", color=BAD, size=8)
        d.text(x + 66, y - 58, "parsed: 90 (faces -x)", size=10.5, family="mono", fill=BAD, halo=T.bg_deep)
    # (e) VRC
    with d.only(k5):
        x, y = P(4, 2.3)
        d.rect(x - 84, y - 22, 168, 44, rx=6, fill=T.tint(BAD, 0.08, T.bg_deep), stroke=BAD, sw=1.4, dash="5 4")
        d.text(x, y - 6, "VRC 1: nodes []", size=10.5, family="mono", fill=BAD, anchor="middle")
        d.text(x, y + 10, "i < 0 - 1 = SIZE_MAX", size=10.5, family="mono", fill=BAD, anchor="middle")
    with d.only(k6):
        x, y = P(4, 2.3)
        d.text(x, y - 10, "load stops with", size=11, fill=OK, anchor="middle")
        d.text(x, y + 6, "an exception: good", size=11, fill=OK, anchor="middle")
    with d.only(k7):
        for t, (xx, yy), anc in (("(a) 6-99 becomes 6-2", (4, -1.9), "middle"), ("(b) two nodes 4", (4, 1.1), "middle"),
                                 ("(c) door faces -x", (-0.5, 1.1), "start"), ("(d) 6: 0, 0, 180, 180", (8.4, -1.1), "end"),
                                 ("(e) VRC 1: nodes []", (1.6, 3.4), "middle")):
            x, y = P(xx, yy)
            chip(d, x, y, t, BAD, size=10, anchor=anc, fill=T.tint(BAD, 0.2, T.bg_deep), layer="top")

    # ---------------- panel C: parser state ----------------
    CX, CW = BX + BW + 30, 480
    d.text(CX, 0, "Parser state afterwards", size=13.5, weight=600, fill=T.fg)
    d.rect(CX, 20, CW, BH, rx=10, fill=T.tint(T.card, 0.5, T.bg), stroke=T.border_soft, sw=1)

    def state(k, sections, last=None):
        with d.at(k, last if last is not None else k):
            y = 44
            for head, lines in sections:
                d.text(CX + 14, y, head, size=11, family="mono", weight=600, fill=T.muted)
                y += 18
                for ln in lines:
                    t, col = (ln, T.fg2) if isinstance(ln, str) else ln
                    d.text(CX + 22, y, t, size=11.5, family="mono", fill=col)
                    y += 17
                y += 7

    state(k0, [("nodes_ (sorted by id)", ["[0] 2 Bay   [1] 4 Waypoint   [2] 6 Waypoint", "[3] 8 Parking"]),
               ("node_id_to_index_  (std::map<uint32_t, uint32_t>)", ["{2: 0, 4: 1, 6: 2, 8: 3}"]),
               ("graph_ edges (index pairs)", ["(0, 1)  (1, 2)  (2, 3)"]),
               ("PoseGraph", ["8 poses: (id, -90) and (id, 90) per node"])])
    state(k1, [("node_id_to_index_", [("{2: 0, 4: 1, 6: 2, 8: 3, 99: 0}   <- inserted", BAD)]),
               ("graph_ edges", [("(0, 1)  (1, 2)  (2, 3)  (2, 0)   <- 6-2", BAD)]),
               ("lookups", [("HasNode(99) == true", BAD), ("GetNodeById(99) -> nodes_[0]: {id: 2, type: Bay}", BAD)]),
               ("PoseGraph, pose (6, 90)", ["4 and 2 both at bearing 180: LEFT twice,",
                                            ("WARN \"... silent loss of an edge.\"", WARN)])])
    state(k2, [("nodes_ (sorted, not stable)", ["[0] 2  [1] 4  [2] 4  [3] 6  [4] 8"]),
               ("node_id_to_index_ (last wins)", [("{2: 0, 4: 2, 6: 3, 8: 4}   <- [1] unreachable", BAD)]),
               ("graph_ edges", ["(0, 2)  (2, 3)  (3, 4)"]),
               ("node_ids_by_type_", [("Waypoint: [4, 6]   Parking: [4, 8]", BAD)]),
               ("PoseGraph", [("10 poses: (4, -90), (4, 90) twice; both read", BAD),
                              ("GetNodeById(4) = nodes_[2]", BAD)])])
    state(k3, [("node 2 as parsed", [("faces_reciprocal: false   (default)", BAD), "faces_reciprocol: never read"]),
               ("consequences", [("inbound heading 90 + 0 = 90 (meant -90)", BAD),
                                 ("GetBayOutboundPose(2) = nullopt", BAD), "  (meant (4, -90): 4 is LEFT of (2, -90))"]),
               ("defaulted the same way when misspelt", ["floor, faces_reciprocal, prioritization_value,",
                                                         "insert_floor, system_floors, height_m,",
                                                         "disallowed_edge_orientation, floors, vrcs,",
                                                         "rotation_circle_tape_radius"])])
    state(k4, [("node 6 as parsed", ["headings: [0, 180]  (sorted, as uint16)"]),
               ("GetAllowedHeadings(6)", ["Wrap(0)=0, Wrap(180)=180, Wrap(180)=180, Wrap(360)=0",
                                          ("sorted: [0, 0, 180, 180]", BAD)]),
               ("PoseGraph", [("poses_: (6, 0) (6, 0) (6, 180) (6, 180)", BAD),
                              "pose_indices_.emplace keeps the first of each",
                              ("GarageGraph vertices duplicated too", BAD)]),
               ("translations", [("(4, 0), (8, 0) do not exist: edges skipped", BAD)])])
    state(k5, [("vrcs_[1] as parsed", ["root_node_id: 4   (never validated)", "nodes: []   (no unknown id: no throw)"]),
               ("adjacent-floor loop", [("vrc.nodes.size() - 1 = 0 - 1", BAD),
                                        ("= 18446744073709551615 (size_t)", BAD),
                                        ("reads nodes[0], nodes[1] of an empty vector:", BAD),
                                        ("undefined behaviour", BAD)]),
               ("fine", ["a one-node VRC: 1 - 1 = 0 iterations"])])
    state(k6, [("exceptions (message)", [("\"Invalid node_type found in the layout file!\"", OK),
                                        ("\"Node 12 has unknown resource size XXL\"", OK),
                                        ("\"Parking windows do not nest within one another!\"", OK),
                                        ("\"Parking window 'XL' has height_m=9 which exceeds", OK),
                                        ("   the physical bay clearance kBayHeight=...\"", OK),
                                        ("\"Unknown node ID specified for VRC with id=1\"", OK),
                                        ("\"Node 12does not have any headings!\"  (sic)", OK),
                                        ("yaml-cpp InvalidNode / BadConversion (no node id)", OK)])])
    state(k7, [("loads without an error", [("(a) unknown edge id -> index 0", BAD), ("(b) duplicate id -> last wins", BAD),
                                           ("(c) misspelt optional key -> default", BAD),
                                           ("(d) h and h + 180 -> duplicate poses", BAD)]),
               ("undefined behaviour", [("(e) empty VRC node list", BAD)]),
               ("fails at load", [("unknown type / size, bad windows, unknown VRC id,", OK),
                                  ("no headings, off-axis edge, missing required key", OK)])])

    # ---------------- row 2: code ----------------
    RY = 20 + BH + 50
    d.text(0, RY - 22, "The code (exact lines)", size=13.5, weight=600, fill=T.fg)
    WCODE = BX + BW
    edges_code = ["  // Sort the nodes by node_id",
                  "  std::sort(nodes_.begin(), nodes_.end(), [](const GarageNodeMsg& a, const GarageNodeMsg& b) {",
                  "    return a.id < b.id;  // increasing order",
                  "  });",
                  "",
                  "  // Construct our indices",
                  "  for(size_t i = 0; i < nodes_.size(); i++) {",
                  "    node_id_to_index_[nodes_.at(i).id] = i;",
                  "  }",
                  "",
                  "  // Extract the edges",
                  "  for(const auto& yaml_edge : layout_yaml[\"edges\"]) {",
                  "    auto src = yaml_edge[\"src\"].as<int>();",
                  "    auto dst = yaml_edge[\"dst\"].as<int>();",
                  "    auto a = std::min(src, dst);",
                  "    auto b = std::max(src, dst);",
                  "    boost::add_edge(node_id_to_index_[a], node_id_to_index_[b], graph_);"]
    with d.at(k0, k2):
        cpe = code_panel(d, 0, RY, WCODE, edges_code, title="layout.cpp L284-300", size=11)
    _hl(d, cpe, [1, 2, 6, 7, 16], T.sky, k=k0, k_last=k0)
    _hl(d, cpe, [16], BAD, k=k1, k_last=k1)
    _hl(d, cpe, [1, 2, 6, 7], BAD, k=k2, k_last=k2)
    with d.only(k1):
        code_panel(d, 0, cpe.y1 + 12, WCODE, [
            "bool Layout::HasNode(uint32_t node_id) const {",
            "  return node_id_to_index_.find(node_id) != node_id_to_index_.end();",
            "}"], title="layout.cpp L351-353 (true for 99 once operator[] has inserted it)", size=11)
    with d.only(k3):
        cpc = code_panel(d, 0, RY, WCODE, [
            "    if(yaml_node[\"faces_reciprocal\"]) {",
            "      node.faces_reciprocal = yaml_node[\"faces_reciprocal\"].as<bool>();",
            "    }",
            "// ... and the consumer (layout.cpp L34-36):",
            "int GetInboundHeading(const GarageNodeMsg& node) {",
            "  return node.headings.at(0) + node.faces_reciprocal * 180;",
            "}"], title="layout.cpp L277-279: an absent key keeps the default; unknown keys are never visited",
            size=11)
    _hl(d, cpc, [0, 1, 2], BAD, k=k3, k_last=k3)
    with d.only(k4):
        cpd = code_panel(d, 0, RY, WCODE, [
            "// layout.cpp L270-275",
            "    for(const auto& yaml_heading : yaml_node[\"headings\"]) {",
            "      node.headings.emplace_back(yaml_heading.as<uint16_t>());",
            "    }",
            "    std::sort(node.headings.begin(), node.headings.end());",
            "// pose_utils.cpp L111-114 (GetAllowedHeadings)",
            "  for(uint16_t heading : node.headings) {",
            "    headings.emplace_back(volley::Wrap(heading));",
            "    headings.emplace_back(volley::Wrap(heading + 180));",
            "  }",
            "// pose_graph.cpp L36-39",
            "    for(int16_t heading : headings) {",
            "      Pose pose = ConstructGaragePose(node.id, heading);",
            "      pose_indices_.emplace(pose, poses_.size());",
            "      poses_.emplace_back(pose);"],
            title="No duplicate check anywhere between the YAML list and the poses", size=11)
    _hl(d, cpd, [7, 8, 13, 14], BAD, k=k4, k_last=k4)
    with d.only(k5):
        cpv = code_panel(d, 0, RY, WCODE, [
            "      vrc.root_node_id = vrc_yaml[\"root_node\"].as<uint32_t>();",
            "      for(const uint32_t node_id : vrc_yaml[\"nodes\"].as<std::vector<uint32_t>>()) {",
            "        const auto node = GetNodeById(node_id);",
            "        if(!node.has_value()) {",
            "          throw std::runtime_error(\"Unknown node ID specified for VRC with id=\" + std::to_string(vrc.id));",
            "        }",
            "        vrc.nodes.push_back(std::move(node.value()));",
            "      }",
            "      ...",
            "      // Add edges between adjacent floors of the VRC",
            "      for(std::size_t i = 0; i < vrc.nodes.size() - 1; i++) {",
            "        const auto a = std::min(vrc.nodes[i].id, vrc.nodes[i + 1].id);",
            "        const auto b = std::max(vrc.nodes[i].id, vrc.nodes[i + 1].id);",
            "        boost::add_edge(node_id_to_index_[a], node_id_to_index_[b], graph_);",
            "      }"], title="layout.cpp L321-339 (L329-333, the sort by floor, elided)", size=11)
    _hl(d, cpv, [10, 11, 12], BAD, k=k5, k_last=k5)
    _hl(d, cpv, [0], WARN, k=k5, k_last=k5)
    with d.only(k6):
        cpk = code_panel(d, 0, RY, WCODE, [
            "// layout.cpp L247-249",
            "      ERRORF(rclcpp::get_logger(\"\"), \"UNKNOWN  node type: %s\", node_type.c_str());",
            "      throw std::runtime_error(\"Invalid node_type found in the layout file!\");",
            "// layout.cpp L261-263",
            "      if(it == resource_name_to_index_.end()) {",
            "        throw std::runtime_error(",
            "            \"Node \" + std::to_string(node.id) + \" has unknown resource size \" + node.max_resource_size);",
            "// layout.cpp L132-145: TRAY smallest, nesting, equal sizes; L104-107: height_m > kBayHeight",
            "// layout.cpp L324-325",
            "        if(!node.has_value()) {",
            "          throw std::runtime_error(\"Unknown node ID specified for VRC with id=\" + std::to_string(vrc.id));",
            "// pose_graph.cpp L32-34",
            "    if(headings.size() == 0) {",
            "      // All nodes must support at least one heading",
            "      throw std::runtime_error(\"Node \" + std::to_string(node.id) + \"does not have any headings!\");"],
            title="The checks that exist", size=11)
    _hl(d, cpk, [2, 6, 10, 14], OK, k=k6, k_last=k6)
    with d.only(k7):
        cps = code_panel(d, 0, RY, WCODE, [
            "// (a) layout.cpp L300: operator[] inserts unknown ids with index 0",
            "    boost::add_edge(node_id_to_index_[a], node_id_to_index_[b], graph_);",
            "// (b) layout.cpp L291: last wins for a duplicate id",
            "    node_id_to_index_[nodes_.at(i).id] = i;",
            "// (c) layout.cpp L277: only known keys are looked up",
            "    if(yaml_node[\"faces_reciprocal\"]) {",
            "// (d) pose_utils.cpp L112-113: a reciprocal pair yields duplicates",
            "    headings.emplace_back(volley::Wrap(heading));",
            "    headings.emplace_back(volley::Wrap(heading + 180));",
            "// (e) layout.cpp L335: unsigned underflow for an empty list",
            "      for(std::size_t i = 0; i < vrc.nodes.size() - 1; i++) {"],
            title="The five lines behind (a) to (e)", size=11)
    _hl(d, cps, [1, 3, 5, 7, 8, 10], BAD, k=k7, k_last=k7)

    # verdict cards (right of the code)
    VX, VW = CX, CW
    verdicts = {k0: (OK, "Parsed", ["4 nodes, 3 edges, 8 poses."]),
                k1: (BAD, "Accepted silently", ["A phantom edge into the bay;", "PoseGraph logs one warning."]),
                k2: (BAD, "Accepted silently", ["Duplicate poses and type lists;", "which copy wins is unspecified."]),
                k3: (BAD, "Accepted silently", ["Bay door pose faces the wrong way;", "no outbound pose."]),
                k4: (BAD, "Accepted silently", ["Duplicate poses and an isolated", "node 6 in the pose graph."]),
                k5: (BAD, "Undefined behaviour", ["Out-of-bounds reads during load", "(inferred: usually a crash)."]),
                k6: (OK, "Load fails, with a message", ["Most messages name the node or", "window; yaml-cpp's do not."]),
                k7: (T.sky, "Fix at the source", ["node_id_to_index_.at(a), duplicate and", "unknown-key checks, i + 1 < size()."])}
    for k, (col, t, lines) in verdicts.items():
        with d.only(k):
            d.rect(VX, RY, VW, 92, rx=10, fill=T.tint(col, 0.10, T.bg), stroke=col, sw=1.5)
            d.text(VX + 16, RY + 22, t, size=15, weight=600, fill=col)
            for i, ln in enumerate(lines):
                d.text(VX + 16, RY + 48 + i * 18, ln, size=12, fill=T.fg2)

    # ---------------- row 3: summary ----------------
    SY = RY + 92 + 30
    SX0 = VX
    d.text(SX0, SY, "Checked vs not checked", size=13.5, weight=600, fill=T.fg)
    checked = ["unknown node type", "unknown max_resource_size", "window smaller than TRAY",
               "windows that do not nest, or equal sizes", "height_m > kBayHeight", "unknown VRC node id",
               "node without headings (PoseGraph)", "off-axis edge (PoseGraph)",
               "missing key or bad scalar (yaml-cpp)"]
    unchecked = [("(a) edge to an unknown node id", k1), ("(b) duplicate node id", k2),
                 ("(c) misspelt optional key", k3), ("(d) heading with its reciprocal", k4),
                 ("(e) empty VRC node list", k5), ("duplicate edges, self-edges", k7),
                 ("VRC root_node, VRC node types", k7), ("duplicate window names (first wins)", k7),
                 ("floor > 255 (truncated to uint8)", k7), ("headings >= 180, bay with 2 headings", k7)]
    colw = VW / 2
    d.text(SX0, SY + 24, "throws at load", size=11, family="mono", weight=600, fill=OK)
    d.text(SX0 + colw, SY + 24, "accepted silently", size=11, family="mono", weight=600, fill=BAD)
    with d.at(k6):
        for i, t in enumerate(checked):
            d.text(SX0, SY + 46 + i * 18, t, size=11.5, fill=T.fg2)
    for i, (t, k) in enumerate(unchecked):
        with d.at(k):
            d.text(SX0 + colw, SY + 46 + i * 18, t, size=11.5, fill=T.fg2 if k != k7 else T.muted)
    d.rect(SX0 - 10, SY - 16, VW + 14, 46 + 10 * 18 + 20, rx=10, fill="none", stroke=T.border_soft, sw=1,
           layer="under")

    frame(d, title="What the layout parser checks, and what it silently accepts",
          subtitle="Layout::Layout reads the keys it knows and throws when a required one is missing or an enumerated "
                   "value is unknown. It does not check references between parts of the file. Step through five "
                   "faults on a four-node example that load without an error, then the checks that do exist.",
          badge_key="illustrative",
          legend=[("box", OK, "checked: throws"), ("box", BAD, "not checked"), ("box", WARN, "warning or unvalidated"),
                  ("box", T.teal, "Bay"), ("box", T.sky, "Parking"), ("box", T.fg2, "Waypoint")],
          footnote="The four-node layout is illustrative; parser behaviour and the quoted lines are from layout.cpp, "
                   "pose_utils.cpp and pose_graph.cpp in the common_ros snapshot (line numbers are lines of each file). "
                   "Node 12 and the values in the step-7 messages are examples. The consequence of (e) beyond 'undefined "
                   "behaviour' is inferred, as is the yaml-cpp behaviour for a missing key.")
    return d
