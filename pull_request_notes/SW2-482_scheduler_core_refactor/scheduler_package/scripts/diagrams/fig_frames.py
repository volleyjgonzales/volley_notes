"""fig_frames: AGV and garage coordinate systems (115).

Doc 02-layout-file.html. Conventions, each checked against the snapshots:

* Garage frame G: +x east, +y north, +z up (agv_interfaces/msg/NodeAccuracy.msg). Node x, y in metres.
* Heading theta: GaragePose.heading (int16 degrees in [-179, 180]) / GeometricPose.yaw (radians), measured
  from garage local north, counter-clockwise positive, "heading 90 points west" (GaragePose.msg,
  GeometricPose.msg).
* Body frame B ("the AGV frame" of NodeAccuracy.msg; its axes are the team's definition, not in the
  snapshots): x along the long side in the heading (locomote) direction, y to the left, z up.
  forward f(theta) = (-sin theta, cos theta), left = (-cos theta, -sin theta), p_G = p_node + R(theta + pi/2) p_B.
* Helper frame P = B rotated by -90 deg (x_P out of the right side, y_P forward), p_G = p_node + R(theta) p_P:
  the frame of tape_layout.cpp, pose_graph.cpp slot names, collision_geometry and polygon_utils.
* Rotation sign: boost rotate_transformer turns clockwise for positive angles (polygon_utils.cpp comment);
  CreateRectangularPolygon and BayOdpEntity::PolyAtPose pass -heading, CollisionEntity::PolyAtPose passes
  +heading. Same rectangle at multiples of 90 deg, mirrored otherwise (read from the code).

kAgvLength / kAgvWidth (common/constants.hpp) are not in the snapshots: the AGV is the house schematic
2.2 m x 1.1 m used by facility.Map.agv.
"""
from __future__ import annotations

import math

from components import chip, code_panel, frame, label_pill, note
from facility import NODES, STALL_L, STALL_W, WINDOWS, Map
from fig_layout import C_LOC, C_STR, hvec, head_arrow
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

DOC = "02-layout-file.html"
NAME = "115_agv_coordinate_frames"
C_G = T.fg2          # garage frame
C_B = T.green        # body frame B
C_P = T.sky          # planner helper frame P
C_PAY = T.pink       # payload window
C_BAD = T.red
AGV_L, AGV_W = 2.2, 1.1      # schematic (kAgvLength / kAgvWidth are not in the snapshots)
XL = WINDOWS["XL"]

# --------------------------------------------------------------------------------------
# checks of the facts the figure draws (recomputed from the YAML)
# --------------------------------------------------------------------------------------


def fwd(h):
    a = math.radians(h)
    return -math.sin(a), math.cos(a)


def left(h):
    a = math.radians(h)
    return -math.cos(a), -math.sin(a)


def near_or_recip(a, b, tol=1e-3):
    d = abs((a - b + math.pi) % (2 * math.pi) - math.pi)
    return d < tol or abs(d - math.pi) < tol


def is_locomote_or_strafe(src, dst, heading_deg):
    """agv_motion_type.cpp IsLocomoteOrStrafe."""
    a, b = NODES[src], NODES[dst]
    eh = math.atan2(b.y - a.y, b.x - a.x)
    th = math.radians(heading_deg)
    loc = near_or_recip(eh, th + math.pi / 2)
    stf = near_or_recip(eh, th)
    if loc + stf != 1:
        return None
    return "LOCOMOTE" if loc else "STRAFE"


assert is_locomote_or_strafe(8, 31, 90) == "LOCOMOTE"
assert is_locomote_or_strafe(8, 9, 90) == "LOCOMOTE"
assert is_locomote_or_strafe(8, 13, 90) == "STRAFE"
assert is_locomote_or_strafe(8, 4, 90) == "STRAFE"
assert fwd(90) == (-1.0, fwd(90)[1]) and abs(fwd(90)[1]) < 1e-12
assert NODES[5].headings == [90] and abs(STALL_L - 5.791) < 1e-9 and abs(STALL_W - 2.21) < 1e-9


def svgp(cx, cy, s, gx, gy):
    """Garage-aligned panel coordinates (metres, y north) -> svg."""
    return cx + gx * s, cy - gy * s


def rect_P(cx, cy, s, wx, ly, phi_deg):
    """Corners of a rectangle built in P (wx along x_P, ly along y_P), rotated counter-clockwise by phi."""
    a = math.radians(phi_deg)
    c, sn = math.cos(a), math.sin(a)
    out = []
    for px, py in ((-wx / 2, -ly / 2), (wx / 2, -ly / 2), (wx / 2, ly / 2), (-wx / 2, ly / 2)):
        gx, gy = c * px - sn * py, sn * px + c * py
        out.append(svgp(cx, cy, s, gx, gy))
    return out


def agv_glyph(d, cx, cy, h, s, color, *, layer="main", lifted=False):
    """Top-down AGV (schematic AGV_L x AGV_W metres) at any heading; long side and chevron along body +x."""
    L, Wd = AGV_L * s, AGV_W * s
    ang = -90 - h
    hx, hy = L / 2, Wd / 2
    wl, wh = 0.2 * L, max(4.0, 0.09 * Wd)
    wheels = "".join(
        f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{wl:.2f}" height="{wh:.2f}" rx="2" fill="#CBD5E1"/>'
        for x0 in (-hx + 0.16 * L, hx - 0.36 * L) for y0 in (-hy - wh * 0.6, hy - wh * 0.4))
    body = (f'<rect x="{-hx:.2f}" y="{-hy:.2f}" width="{L:.2f}" height="{Wd:.2f}" rx="{Wd * 0.28:.2f}" '
            f'fill="{T.tint(color, 0.22, T.bg_deep)}" stroke="{color}" stroke-width="2"/>')
    plate = (f'<rect x="{-hx + 0.3 * L:.2f}" y="{-hy + 0.22 * Wd:.2f}" width="{0.4 * L:.2f}" height="{0.56 * Wd:.2f}" '
             f'rx="3" fill="{T.tint(color, 0.5 if lifted else 0.3, T.bg_deep)}" '
             f'stroke="{T.tint(color, 0.7, T.bg_deep)}" stroke-width="1"/>')
    chev = (f'<path d="M{hx - 0.2 * L:.2f} {-0.26 * Wd:.2f} L{hx - 0.06 * L:.2f} 0 L{hx - 0.2 * L:.2f} {0.26 * Wd:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
    r = math.hypot(L, Wd) / 2 + 4
    d.raw(f'<g transform="translate({cx:.2f} {cy:.2f}) rotate({ang:.2f})">{wheels}{body}{plate}{chev}</g>', layer,
          BBox(cx - r, cy - r, cx + r, cy + r))


def axis(d, x, y, ux, uy, L, color, label, *, sw=2.4, dash=None, lab_off=(0, 0), size=12, anchor="middle",
         layer="top", weight=700, family="mono", halo=T.bg):
    """Axis arrow from (x, y) along svg unit vector (ux, uy)."""
    tip = (x + ux * L, y + uy * L)
    d.line(x, y, tip[0] - ux * 8, tip[1] - uy * 8, stroke=color, sw=sw, dash=dash, layer=layer)
    d.arrowhead(tip, (x, y), kind="filled", color=color, size=10, layer=layer)
    if label:
        d.text(tip[0] + ux * 14 + lab_off[0], tip[1] + uy * 14 + lab_off[1], label, size=size, family=family,
               weight=weight, fill=color, anchor=anchor, halo=halo, halo_w=3)
    return tip


def z_up(d, x, y, color, r=7, layer="top"):
    """z axis pointing out of the page."""
    d.circle(x, y, r, fill=T.bg, stroke=color, sw=1.6, layer=layer)
    d.circle(x, y, 2.2, fill=color, layer=layer)


def arrow(d, a, b, color, *, sw=3, size=12, layer="over", dash=None, halo=T.bg_deep):
    ux, uy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    d.line(a[0], a[1], b[0] - ux * 8, b[1] - uy * 8, stroke=halo, sw=sw + 3.5, layer=layer)
    d.line(a[0], a[1], b[0] - ux * 8, b[1] - uy * 8, stroke=color, sw=sw, layer=layer, dash=dash)
    d.arrowhead(b, a, kind="filled", color=color, size=size, layer=layer)


def text_block(d, x, y, w, paras, *, size=11.5, lh=1.45, gap=6, fill=T.fg2):
    """Wrapped paragraphs; a paragraph is a str or (str, color, weight, family)."""
    yy = y
    for p in paras:
        if isinstance(p, str):
            p = (p, fill, 400, "sans")
        s, col, wt, fam = p
        for ln in wrap(s, w, size, fam, wt):
            d.text(x, yy, ln, size=size, family=fam, weight=wt, fill=col, baseline="top")
            yy += size * lh
        yy += gap
    return yy


def panel_box(d, x, y, w, h, title, color=T.border_soft):
    d.rect(x, y, w, h, rx=10, fill=T.bg_deep, stroke=color, sw=1)
    if title:
        d.text(x + 12, y + 16, title, size=11, family="mono", weight=600, fill=T.muted)
    return BBox(x, y, x + w, y + h)


def code(d, x, y, lines, *, title=None, size=10.5, w=None, hl=(), hl_col=C_LOC):
    tw = max(text_width(ln, size, "mono") for ln in lines) + 28
    if title:
        tw = max(tw, text_width(title, 11, "mono", 600) + 28)
    w = w or tw
    bb = code_panel(d, x, y, w, lines, title=title, size=size)
    lh = size * 1.5
    top = y + 14 + (24 if title else 0) + size / 2
    for i in hl:
        yy = top + i * lh
        d.rect(x + 6, yy - lh / 2, w - 12, lh, rx=3, fill=T.tint(hl_col, 0.22, "#0B1222"), layer="main")
    return bb


# ======================================================================================
# 115 — AGV and garage coordinate systems
# ======================================================================================

@figure(NAME, "AGV and garage coordinate systems (animated)", DOC)
def agv_coordinate_frames():
    d = Doc(NAME, "AGV and garage coordinate systems",
            "Animated: the garage frame G (x east, y north), the heading measured from north counter-clockwise, the "
            "AGV body frame B (x forward along the long side, y left), locomote and strafe on two Pecos edges at "
            "W8, the planner's helper frame P (x out of the right side, y forward) and its neighbour-slot names, "
            "footprints built in P, a rotation-sign inconsistency at a hypothetical 45 degree heading, and a table "
            "of which source file uses which frame.")

    caps = [
        "The garage frame G: +x east, +y north, +z up (NodeAccuracy.msg). Every node position in the layout YAML is "
        "an (x, y) in metres in G: W8 is at (30.8823, 12.7753); the XL parking window of stall P5 is 5.791 m along "
        "x and 2.21 m along y. North is 'garage local north', a direction defined in the CAD file (GaragePose.msg).",
        "The heading theta. GaragePose.heading is an int16 in degrees, [-179, 180]; GeometricPose.yaw is the same "
        "angle in radians. It is measured from garage local north (+y), counter-clockwise positive: 0 faces north, "
        "90 west, -90 east, 180 south. W8 lists headings [0, 90], so with the reciprocals its four poses face "
        "all four directions.",
        "The body frame B of AGV-1 at (8, 90): +x_B points along the long side in the heading direction (the "
        "locomote direction), +y_B to the left, +z_B up. In G the forward unit vector is f(theta) = (-sin theta, "
        "cos theta) and the left one (-cos theta, -sin theta); at theta = 90: west and south. B is the 'AGV frame' "
        "of NodeAccuracy.msg; its axes are the team's definition, the snapshots do not spell them out.",
        "Locomote = translation along body x, strafe = along body y. IsLocomoteOrStrafe (agv_motion_type.cpp) "
        "compares the edge bearing atan2(dy, dx) with heading + pi/2 (the math angle of +x_B) and with heading "
        "(the math angle of -y_B), each within 1e-3 rad or its reciprocal. W8 -> W31: bearing pi = 90 deg + pi/2, "
        "a LOCOMOTE of 2.857 m west. W8 -> W13: bearing pi/2 = heading, a STRAFE of 4.391 m north.",
        "The helper frame P that the planner's geometry code uses: B turned by -90 deg, so x_P points out of the "
        "AGV's right side (= -y_B) and y_P forward (= +x_B); p_G = p_node + R(theta) p_P, i.e. the heading used "
        "directly as a math angle. PoseGraph names its slots in P: FORWARD = +x_P = W13 (strafe right), BACK = W4 "
        "(strafe left), LEFT = +y_P = W31 (forward locomote), RIGHT = W9 (backward locomote).",
        "Footprints are built in P and then rotated by the heading. RectangleFromSize(width, length) puts its "
        "length argument along x, so AgvEntity's RectangleFromSize(kAgvLength, kAgvWidth) lays kAgvLength along "
        "y_P = +x_B, and a payload window's length_m also lies along y_P. Pecos check: at heading 90 the AGV's long "
        "axis and the XL window's 5.791 m lie along world x, the long side of stall P5.",
        "A sign inconsistency, read from the code and not observed. boost's rotate_transformer turns clockwise "
        "for positive angles. CreateRectangularPolygon and BayOdpEntity pass -heading (net counter-clockwise, "
        "correct); CollisionEntity::PolyAtPose passes +heading (net clockwise). At a hypothetical heading 45 the "
        "collision-table footprint of an AGV or payload would point north-east instead of north-west. At multiples "
        "of 90 deg, all Pecos uses, the centred rectangles coincide.",
        "The complete picture: one AGV, three frames. G for positions and headings, B for what the AGV does "
        "(locomote along x_B, strafe along y_B, NodeAccuracy offsets), P inside the planner's geometry and slot "
        "names. The table lists every source file that fixes one of them.",
    ]
    ks = [d.step(c) for c in caps]
    K0, K1, K2, K3, K4, K5, K6, K7 = ks

    # ------------------------------------------------------------------ map ------------
    s = 56
    m = Map(d, 0, 40, s, (26.6, 40.3), (9.35, 18.4))
    d.text(0, 0, "Around W8 (Pecos, metres in the garage frame G)", size=13.5, weight=600, fill=T.fg)
    m.floor(tick=2)
    m.clip()
    m.corridors()
    m.stalls(labels=True, dim=True, highlight=())
    m.edges()
    m.nodes(labels=True)
    m.unclip()
    x8, y8 = m.P(8)
    x31, y31 = m.P(31)
    x13, y13 = m.P(13)
    x9, y9 = m.P(9)
    x4, y4 = m.P(4)
    x5, y5 = m.P(5)
    box = m.box

    # garage frame triad (always)
    gx0, gy0 = box.x0 + 40, box.y1 - 30
    axis(d, gx0, gy0, 1, 0, 78, C_G, "", sw=2.2, halo=T.bg_deep)
    axis(d, gx0, gy0, 0, -1, 78, C_G, "", sw=2.2, halo=T.bg_deep)
    z_up(d, gx0, gy0, C_G)
    d.text(gx0 + 86, gy0, "+x east", size=11.5, family="mono", weight=700, fill=C_G, halo=T.bg_deep, halo_w=3)
    d.text(gx0 + 10, gy0 - 82, "+y north", size=11.5, family="mono", weight=700, fill=C_G, halo=T.bg_deep, halo_w=3)
    d.text(gx0 + 14, gy0 - 18, "+z up (out of page)", size=10.5, family="mono", fill=T.muted, halo=T.bg_deep,
           halo_w=3)
    d.text(gx0 - 14, gy0 - 40, "G", size=16, weight=600, fill=C_G, anchor="end", halo=T.bg_deep, halo_w=3)

    # step 0: node and stall in G
    with d.only(K0):
        d.circle(x8, y8, 14, fill="none", stroke=C_G, sw=2, layer="top")
        label_pill(d, x8 + 20, y8 - 26, "W8 = (30.8823, 12.7753) m", color=T.fg, bg=T.bg_deep, border=C_G,
                   anchor="start")
        sx0, sx1 = m.X(NODES[5].x - STALL_L / 2), m.X(NODES[5].x + STALL_L / 2)
        sy0, sy1 = m.Y(NODES[5].y + STALL_W / 2), m.Y(NODES[5].y - STALL_W / 2)
        d.rect(sx0 + 1.5, sy0 + 1.5, sx1 - sx0 - 3, sy1 - sy0 - 3, rx=4, fill="none", stroke=T.sky, sw=2.2,
               layer="top")
        yy = sy0 - 10
        d.line(sx0 + 2, yy, sx1 - 2, yy, stroke=T.sky, sw=1.4, layer="top")
        d.line(sx0 + 2, yy - 5, sx0 + 2, yy + 5, stroke=T.sky, sw=1.4, layer="top")
        d.line(sx1 - 2, yy - 5, sx1 - 2, yy + 5, stroke=T.sky, sw=1.4, layer="top")
        label_pill(d, (sx0 + sx1) / 2, yy - 16, "XL length_m 5.791 along x", color=T.sky, bg=T.bg_deep,
                   border=T.sky)
        label_pill(d, sx0 + 8, (sy0 + sy1) / 2 + 22, "width_m 2.21 along y", color=T.sky, bg=T.bg_deep,
                   border=T.sky, anchor="start")

    # step 1: W8's four poses
    with d.only(K1):
        for h, lab, off in ((0, "0", (12, 0)), (90, "90", (0, -14)), (-90, "-90", (0, -14)), (180, "180", (12, 0))):
            tip = head_arrow(d, x8, y8, h, T.green, L=62, start=8)
            fx, fy = hvec(h)
            d.text(tip[0] + fx * 4 + off[0], tip[1] + fy * 4 + off[1], lab, size=12, family="mono", weight=700,
                   fill=T.green, anchor="start" if off[0] else "middle", halo=T.bg_deep, halo_w=3)
        label_pill(d, x8 + 20, y8 + 40, "W8 headings [0, 90] + reciprocals = 4 poses", color=T.green,
                   bg=T.bg_deep, border=T.green, anchor="start")

    # AGV-1 at (8, 90) from step 2 on
    with d.at(K2):
        m.agv(8, "AGV-1", heading=90, label_side="above")
    with d.only(K2):
        fx, fy = hvec(90)
        axis(d, x8, y8, fx, fy, 104, C_B, "+x_B", lab_off=(4, -16), halo=T.bg_deep)
        lx, ly = hvec(180)     # left of a west-facing AGV = south
        axis(d, x8, y8, lx, ly, 84, C_B, "+y_B", lab_off=(26, -4), halo=T.bg_deep)
        z_up(d, x8, y8, C_B)
        label_pill(d, x8 + 70, y8 - 56, "f(90) = (-1, 0): west", color=C_B, bg=T.bg_deep, border=C_B,
                   anchor="start")

    # step 3+: locomote and strafe
    cut = AGV_L * s / 2 + 8
    with d.at(K3):
        arrow(d, (x8 - cut, y8), (x31 + 10, y31), C_LOC)
        arrow(d, (x8, y8 - AGV_W * s / 2 - 10), (x13, y13 + 10), C_STR)
        label_pill(d, (x31 + x8 - cut) / 2 - 10, y8 - 46, "LOCOMOTE  +x_B  2.857 m", color=C_LOC, bg=T.bg_deep,
                   border=C_LOC)
        label_pill(d, x8, (y8 + y13) / 2 - 22, "STRAFE  -y_B  4.391 m", color=C_STR, bg=T.bg_deep, border=C_STR)
    with d.at(K4):
        arrow(d, (x8 + cut, y8), (x9 - 10, y9), C_LOC, dash="7 5")
        arrow(d, (x8, y8 + AGV_W * s / 2 + 34), (x4, y4 - 10), C_STR, dash="7 5")
        label_pill(d, (x31 + x8 - cut) / 2 - 10, y8 + 26, "LEFT (3) = +y_P", color=C_P, bg=T.bg_deep, border=C_P)
        label_pill(d, x8, (y8 + y13) / 2 + 4, "FORWARD (0) = +x_P", color=C_P, bg=T.bg_deep, border=C_P)
        label_pill(d, (x8 + cut + x9) / 2 - 30, y8 - 22, "RIGHT (1) = -y_P", color=C_P,
                   bg=T.bg_deep, border=C_P)
        label_pill(d, x8 + 12, (y8 + y4) / 2 + 30, "BACK (2) = -x_P", color=C_P, bg=T.bg_deep,
                   border=C_P, anchor="start")
    with d.only(K4):
        fx, fy = hvec(0)     # x_P = right side of a west-facing AGV = north
        axis(d, x8 + 40, y8, fx, fy, 62, C_P, "", sw=2.2, dash="5 3", halo=T.bg_deep)
        d.text(x8 + 48, y8 - 62, "x_P", size=12, family="mono", weight=700, fill=C_P, halo=T.bg_deep, halo_w=3)

    # step 5+: AGV-2 and the XL payload window on P5
    with d.at(K5):
        m.agv(5, "AGV-2", heading=90, label_side="below", color=T.green)
        px0, px1 = m.X(NODES[5].x - XL["length_m"] / 2), m.X(NODES[5].x + XL["length_m"] / 2)
        py0, py1 = m.Y(NODES[5].y + XL["width_m"] / 2), m.Y(NODES[5].y - XL["width_m"] / 2)
        d.rect(px0 + 4, py0 + 4, px1 - px0 - 8, py1 - py0 - 8, rx=6, fill="none", stroke=C_PAY, sw=2, dash="6 4",
               layer="top")
        label_pill(d, x5 - 40, py0 - 16, "XL window 5.791 m along x = along +x_B", color=C_PAY, bg=T.bg_deep,
                   border=C_PAY)

    # ------------------------------------------------------------------ right panel ----
    RX = box.x1 + 48
    PW = 570
    PT = 40

    # step 0 --------------------------------------------------------------------------
    with d.only(K0):
        d.text(RX, 0, "1 · The garage frame G", size=13.5, weight=600, fill=T.fg)
        b1 = code(d, RX, PT, [
            "# agv_interfaces/msg/NodeAccuracy.msg",
            "# Heading of the node in the garage frame,",
            "#   +x (east), +y (north), +z (up).",
            "int16 node_heading_deg",
            "# interfaces/msg/GaragePose.msg",
            "# Headings are defined relative to garage local north,",
            "#   a direction that is defined in the CAD file.",
        ], title="the frame, as the messages state it", w=PW, hl=(1, 2, 5, 6), hl_col=C_G)
        b2 = code(d, RX, b1.y1 + 14, [
            "parking_windows:",
            "  - name: XL",
            "    length_m: 5.791      # along x at heading 90 / -90",
            "    width_m: 2.21",
            "nodes:",
            "  - id: 8",
            "    x: 30.8823           # metres, east",
            "    y: 12.7753           # metres, north",
            "    type: Waypoint",
            "    rotation_allowed: true",
            "    headings: [0, 90]",
            "  - id: 5               # P5, type Parking, headings [90]",
        ], title="sources/5675_pecos_combined.yaml (condensed; # comments added)", w=PW, hl=(5, 6, 7), hl_col=C_G)
        text_block(d, RX, b2.y1 + 16, PW, [
            "G is a right-handed frame fixed to the garage: x east, y north, z up, so seen from above z points out "
            "of the page. Its origin is the CAD origin and lies off this crop; the tick labels are metres in G.",
        ])

    # step 1 --------------------------------------------------------------------------
    with d.only(K1):
        d.text(RX, 0, "2 · The heading theta: from north, counter-clockwise", size=13.5, weight=600, fill=T.fg)
        cx, cy, R = RX + 170, PT + 200, 112
        d.circle(cx, cy, R, fill=T.bg_deep, stroke=T.border_soft, sw=1)
        d.line(cx - R - 60, cy, cx + R + 60, cy, stroke=T.faint, sw=1)
        d.line(cx, cy + R + 50, cx, cy - R - 50, stroke=T.faint, sw=1)
        for h in (0, 90, -90, 180):
            fx, fy = hvec(h)
            d.line(cx + fx * 10, cy + fy * 10, cx + fx * (R - 52), cy + fy * (R - 52), stroke=T.green, sw=2.4)
            d.arrowhead((cx + fx * (R - 44), cy + fy * (R - 44)), (cx, cy), kind="filled", color=T.green, size=10)
            ax, ay = cx + fx * (R + 6), cy + fy * (R + 6)
            agv_glyph(d, ax, ay, h, 26, T.green, layer="top")
        lab = {0: ("0: north (+y)", cx + 40, cy - R - 26, "start"),
               90: ("90: west (-x)", cx - R - 4, cy + 36, "middle"),
               -90: ("-90: east (+x)", cx + R + 4, cy + 36, "middle"),
               180: ("180: south (-y)", cx + 40, cy + R + 26, "start")}
        for h, (t, lx, ly, an) in lab.items():
            d.text(lx, ly, t, size=11.5, family="mono", weight=700, fill=T.fg, anchor=an, halo=T.bg, halo_w=3)
        # CCW arc from 0 to 90
        pts = []
        for i in range(25):
            fx, fy = hvec(90 * i / 24)
            pts.append((cx + fx * 40, cy + fy * 40))
        d.path("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts[:-2]), stroke=T.pink, sw=2)
        d.arrowhead(pts[-1], pts[-4], kind="filled", color=T.pink, size=8)
        d.text(cx - 36, cy - 52, "+theta", size=11, family="mono", weight=700, fill=T.pink, anchor="end")
        text_block(d, RX + 360, PT + 40, PW - 360, [
            ("GaragePose.heading", T.fg, 600, "mono"),
            "int16, degrees, [-179, 180]. 270 is stored as -90.",
            ("GeometricPose.yaw", T.fg, 600, "mono"),
            "the same angle in radians: yaw = heading x pi / 180.",
            ("Zero and sign", T.fg, 600, "sans"),
            "0 = garage local north (+y); counter-clockwise positive; 'heading 90 points west' (both .msg files).",
            ("Facing", T.fg, 600, "sans"),
            "the arrow is the AGV's front: its long side and driving direction (figure 78).",
        ], size=11)

    # step 2 --------------------------------------------------------------------------
    with d.only(K2):
        d.text(RX, 0, "3 · The body frame B (the 'AGV frame')", size=13.5, weight=600, fill=T.fg)
        bx = panel_box(d, RX, PT, PW, 250, "AGV-1 at heading 90, seen from above")
        cx, cy, sc = RX + 300, PT + 130, 70
        agv_glyph(d, cx, cy, 90, sc, C_B)
        fx, fy = hvec(90)
        axis(d, cx, cy, fx, fy, 170, C_B, "+x_B forward", lab_off=(10, -18))
        lx, ly = hvec(180)
        axis(d, cx, cy, lx, ly, 92, C_B, "+y_B left", lab_off=(48, -8))
        z_up(d, cx, cy, C_B)
        d.text(cx + 14, cy + 66, "+z_B up: out of the page (dot)", size=11, family="mono", fill=C_B, halo=T.bg_deep,
               halo_w=3)
        # long side dimension
        y_dim = cy - AGV_W * sc / 2 - 14
        d.line(cx - AGV_L * sc / 2, y_dim, cx + AGV_L * sc / 2, y_dim, stroke=T.muted, sw=1.2)
        for xx in (cx - AGV_L * sc / 2, cx + AGV_L * sc / 2):
            d.line(xx, y_dim - 5, xx, y_dim + 5, stroke=T.muted, sw=1.2)
        d.text(cx + 40, y_dim - 12, "long side along x_B (schematic 2.2 m)", size=10.5, fill=T.muted,
               anchor="middle")
        d.text(cx + AGV_L * sc / 2 + 12, cy, "rear", size=10.5, fill=T.muted)
        cb = code(d, RX, bx.y1 + 14, [
            "forward  f(theta) = (-sin theta,  cos theta)   // +x_B in G",
            "left     l(theta) = (-cos theta, -sin theta)   // +y_B in G",
            "p_G = p_node + R(theta + pi/2) * p_B",
            "theta = 90:  f = (-1, 0) west,  l = (0, -1) south",
            "# NodeAccuracy.msg: x_offset_m, y_offset_m 'in the AGV frame'",
            "#   yaw_offset_rad 'in the AGV frame (CCW positive)'",
        ], title="body -> garage", w=PW, hl=(0, 1, 2), hl_col=C_B)
        text_block(d, RX, cb.y1 + 14, PW, [
            "x_B runs along the long side and points where the heading points, so 'facing' and 'driving forward' "
            "are the same direction. heading + pi/2 is +x_B written as a math angle (0 = +x, CCW).",
            ("Not in the snapshots: NodeAccuracy.msg names 'the AGV frame' without defining its axes; B is the "
             "team's definition.", T.muted, 400, "sans"),
        ])

    # step 3 --------------------------------------------------------------------------
    with d.only(K3):
        d.text(RX, 0, "4 · Locomote along x_B, strafe along y_B", size=13.5, weight=600, fill=T.fg)
        c1 = code(d, RX, PT, [
            "// src/agv_motion_type.cpp  IsLocomoteOrStrafe(src, dst, heading)",
            "const double edge_heading = atan2(dst.y - src.y, dst.x - src.x);",
            "const bool locomote =",
            "    IsNearToAngleOrReciprocal(edge_heading, heading + M_PI_2, 1e-3);",
            "const bool strafe =",
            "    IsNearToAngleOrReciprocal(edge_heading, heading, 1e-3);",
            "if(locomote + strafe != 1) return {};      // neither, or both",
        ], w=PW, hl=(3, 5), hl_col=C_LOC)
        rows = [("edge", "dx, dy [m]", "atan2", "test (heading = pi/2)", "result"),
                ("W8 -> W31", "-2.857, 0", "pi", "= heading + pi/2", "LOCOMOTE"),
                ("W8 -> W13", "0, +4.391", "pi/2", "= heading", "STRAFE"),
                ("W8 -> W9", "+6.303, 0", "0", "recip. of heading + pi/2", "LOCOMOTE"),
                ("W8 -> W4", "0, -2.286", "-pi/2", "recip. of heading", "STRAFE")]
        ty = c1.y1 + 16
        cols = [0, 96, 196, 256, 466]
        for i, r in enumerate(rows):
            yy = ty + i * 24
            d.rect(RX, yy, PW, 24, rx=3, fill=T.tint(C_LOC, 0.12, T.bg) if i == 0 else
                   (T.card if i % 2 else T.tint(T.card, 0.6, T.bg)))
            for j, (v, ox) in enumerate(zip(r, cols)):
                col = T.muted if i == 0 else (C_LOC if v == "LOCOMOTE" else C_STR if v == "STRAFE" else T.fg2)
                d.text(RX + 10 + ox, yy + 12, v, size=10.5 if i == 0 else 11, family="mono",
                       weight=600 if (i == 0 or j == 4) else 400, fill=col)
        c2 = code(d, RX, ty + 5 * 24 + 16, [
            "// src/garage_graph.cpp  GarageGraph::LocomoteOrStrafe",
            "// src.yaw ... leaves it in *Volley* heading convention (heading 0",
            "// = +y, CCW positive) - NOT the math / atan2 convention (0 = +x).",
            "auto math_yaw = M_PI_2 + src.yaw;",
            "auto relative_heading = AngleDist(math_yaw, angle_of_motion);",
            "// LOCOMOTE if dist * |cos| > dist * |sin|, else STRAFE",
        ], w=PW, hl=(3,), hl_col=C_LOC)
        text_block(d, RX, c2.y1 + 14, PW, [
            "Both tests turn the heading into the math angle of +x_B before comparing it with atan2. The "
            "comment records that an earlier version compared them directly and swapped every LOCOMOTE and STRAFE.",
        ])

    # step 4 --------------------------------------------------------------------------
    with d.only(K4):
        d.text(RX, 0, "5 · The planner's helper frame P = B turned by -90 deg", size=13.5, weight=600, fill=T.fg)
        bx = panel_box(d, RX, PT, PW, 300, "AGV at heading 90 with the P axes and the PoseGraph slot names")
        cx, cy, sc = RX + 270, PT + 160, 56
        agv_glyph(d, cx, cy, 90, sc, C_B)
        tipx = axis(d, cx, cy, 0, -1, 86, C_P, "", dash="5 3")
        tipy = axis(d, cx, cy, -1, 0, 128, C_P, "", dash="5 3")
        z_up(d, cx, cy, C_P)
        d.text(tipx[0] + 12, tipx[1] + 6, "x_P = -y_B (out of the right side)", size=11, family="mono", weight=700,
               fill=C_P)
        d.text(RX + 14, cy - 20, "y_P = +x_B (forward)", size=11, family="mono", weight=700, fill=C_P)
        d.line(cx + 70, cy, cx + 128, cy, stroke=C_P, sw=1.4, dash="2 4")
        d.line(cx, cy + 34, cx, cy + 96, stroke=C_P, sw=1.4, dash="2 4")

        def slot(x, y, name, ax_, kind, anchor="start"):
            col = C_STR if "strafe" in kind else C_LOC
            d.rich(x, y, [(name + "  ", "mono", 700, C_P), (ax_, "mono", 400, T.fg2)], size=11, anchor=anchor)
            d.text(x if anchor == "start" else (x - text_width(name + "  " + ax_, 11, "mono") / 2 if anchor == "middle"
                   else x), y + 16, kind, size=11, weight=600, fill=col, anchor="start" if anchor != "end" else "end")
        slot(cx + 16, PT + 44, "FORWARD (0)", "+x_P", "strafe right  (W13 at (8, 90))")
        slot(RX + 14, cy + 22, "LEFT (3)", "+y_P", "locomote forward  (W31)")
        slot(cx + 16, PT + 262, "BACK (2)", "-x_P", "strafe left  (W4)")
        slot(cx + 136, cy - 8, "RIGHT (1)", "-y_P", "locomote backward  (W9)")
        c1 = code(d, RX, bx.y1 + 14, [
            "p_G = p_node + R(theta) * p_P      // heading used directly as a math angle",
            "// src/pose_graph.cpp: relative_bearing =",
            "//   SignedAngleDist(heading_rad, atan2(dy, dx))",
            "//   0 -> FORWARD, +pi/2 -> LEFT, pi -> BACK, -pi/2 -> RIGHT",
            "// src/tape_layout.cpp AddExtensionNode:",
            "//   'AGV heading is zero out the right side of the vehicle'",
            "auto [ux, uy] = BodyToInertial(1, 0, kDeg2Rad * heading);   // +x_P",
            "// layout.hpp GetInboundHeading: '+y axis facing the ... door'",
            "// pose_graph.hpp GetBayOutboundPose: '+y direction', always LEFT",
        ], w=PW, hl=(0, 6), hl_col=C_P)
        text_block(d, RX, c1.y1 + 14, PW, [
            "So in this code 'FORWARD' is not the AGV's front: it is +x_P, a strafe out of the right side. The '+y' "
            "of the layout.hpp and pose_graph.hpp comments is y_P, which is +x_B.",
            ("SignedAngleDist and BodyToInertial are not in the snapshots; the slot mapping assumes "
             "SignedAngleDist(a, b) = b - a, which the 'always LEFT' bay comment and figure 110 agree with.",
             T.muted, 400, "sans"),
        ], size=11)

    # step 5 --------------------------------------------------------------------------
    with d.only(K5):
        d.text(RX, 0, "6 · Footprints are built in P, then rotated by theta", size=13.5, weight=600, fill=T.fg)
        bx = panel_box(d, RX, PT, PW, 290, "")
        sc = 30
        # (a) in P, heading 0
        ax0, ay0 = RX + 130, PT + 156
        d.text(RX + 12, PT + 16, "built in P (theta = 0)", size=11, family="mono", weight=600, fill=T.muted)
        pay = rect_P(ax0, ay0, sc, XL["width_m"], XL["length_m"], 0)
        d.polygon(pay, fill=T.tint(C_PAY, 0.10, T.bg_deep), stroke=C_PAY, sw=1.8)
        d.polygon(rect_P(ax0, ay0, sc, AGV_W, AGV_L, 0), fill=T.tint(C_B, 0.2, T.bg_deep), stroke=C_B, sw=1.8)
        axis(d, ax0, ay0, 1, 0, 62, C_P, "x_P", lab_off=(6, 0), size=11)
        axis(d, ax0, ay0, 0, -1, 104, C_P, "y_P", lab_off=(16, 10), size=11)
        d.text(ax0 - 44, ay0 - 70, "length_m", size=10.5, family="mono", fill=C_PAY, anchor="end")
        d.text(ax0 - 44, ay0 - 56, "5.791 on y_P", size=10.5, family="mono", fill=C_PAY, anchor="end")
        d.text(ax0, ay0 + 104, "width_m 2.21 on x_P", size=10.5, family="mono", fill=C_PAY, anchor="middle")
        d.text(ax0 - 44, ay0 + 30, "kAgvLength", size=10.5, family="mono", fill=C_B, anchor="end")
        d.text(ax0 - 44, ay0 + 44, "on y_P", size=10.5, family="mono", fill=C_B, anchor="end")
        # arrow between
        arrow(d, (RX + 246, ay0), (RX + 296, ay0), T.fg2, sw=2, size=10, layer="main", halo=T.bg_deep)
        d.text(RX + 271, ay0 - 18, "R(90)", size=11, family="mono", weight=700, fill=T.fg2, anchor="middle")
        d.text(RX + 271, ay0 + 20, "CCW", size=10.5, family="mono", fill=T.muted, anchor="middle")
        # (b) rotated into G at theta = 90
        bx0, by0 = RX + 440, PT + 156
        d.text(RX + 330, PT + 16, "in G at theta = 90", size=11, family="mono", weight=600, fill=T.muted)
        d.polygon(rect_P(bx0, by0, sc, XL["width_m"], XL["length_m"], 90), fill=T.tint(C_PAY, 0.10, T.bg_deep),
                  stroke=C_PAY, sw=1.8)
        agv_glyph(d, bx0, by0, 90, sc, C_B)
        axis(d, bx0, by0, 0, -1, 62, C_P, "x_P", lab_off=(0, 0), size=11)
        axis(d, bx0, by0, -1, 0, 100, C_P, "y_P", lab_off=(6, -14), size=11)
        d.text(bx0, by0 + 56, "5.791 m along world x", size=10.5, family="mono", fill=C_PAY, anchor="middle")
        d.text(bx0, by0 + 72, "= stall P5's long side", size=10.5, family="mono", fill=C_PAY, anchor="middle")
        c1 = code(d, RX, bx.y1 + 14, [
            "// src/collision_geometry.cpp",
            "Polygon RectangleFromSize(double width, double length)",
            "  // corners (+-length/2, +-width/2): 'length' lies along x",
            "AgvEntity::BasePoly   = RectangleFromSize(kAgvLength, kAgvWidth);",
            "PayloadEntity::BasePoly = RectangleFromSize(window.length_m, window.width_m);",
            "  // -> kAgvLength and length_m lie along y_P = +x_B",
            "// src/polygon_utils.cpp CalcOverlappingSizedPoses:",
            "// NOTE: Everything is a crab, so our parking window lengths are our pose widths.",
            "CreateRectangularPolygon(x, y, heading, window.width_m, window.length_m);",
            "  // length_along_heading = width_m: 'heading' here means x_P",
        ], w=PW, size=10, hl=(3, 4, 7), hl_col=C_P)
        text_block(d, RX, c1.y1 + 12, PW, [
            ("kAgvLength, kAgvWidth and kTray* live in common/constants.hpp, which is not in the snapshots: the AGV "
             "is drawn as the 2.2 x 1.1 m schematic.", T.muted, 400, "sans"),
        ], size=11)

    # step 6 --------------------------------------------------------------------------
    with d.only(K6):
        d.text(RX, 0, "7 · Rotation sign: one call site turns the other way", size=13.5, weight=600, fill=T.fg)
        bx = panel_box(d, RX, PT, PW, 290, "")
        sc = 26
        for i, (title, sub, phi, col, ok) in enumerate((
                ("counter-clockwise (intended)", "rotate(-heading):|CreateRectangularPolygon, BayOdpEntity", 45,
                 C_B, True),
                ("clockwise", "Rotate(+heading):|CollisionEntity::PolyAtPose", -45, C_BAD, False))):
            cx, cy = RX + 140 + i * 290, PT + 148
            d.text(cx, PT + 18, title, size=12, weight=600, fill=col, anchor="middle")
            # compass guide
            d.line(cx - 110, cy, cx + 110, cy, stroke=T.border_soft, sw=1)
            d.line(cx, cy - 94, cx, cy + 100, stroke=T.border_soft, sw=1)
            d.text(cx + 6, cy - 86, "N", size=10.5, family="mono", fill=T.faint)
            # the other result, dashed, for comparison
            other = rect_P(cx, cy, sc, XL["width_m"], XL["length_m"], -phi)
            d.path("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in other) + " Z", stroke=T.muted, sw=1.3,
                   dash="4 3", layer="over")
            d.polygon(rect_P(cx, cy, sc, XL["width_m"], XL["length_m"], phi), fill=T.tint(col, 0.08, T.bg_deep),
                      stroke=col, sw=1.6)
            d.polygon(rect_P(cx, cy, sc, AGV_W, AGV_L, phi), fill=T.tint(col, 0.22, T.bg_deep), stroke=col, sw=2)
            a = math.radians(phi)
            ux, uy = -math.sin(a), -math.cos(a)     # svg direction of the rotated y_P
            axis(d, cx, cy, ux, uy, 96, col, "long axis " + ("NW" if ok else "NE"), lab_off=(-14 * (1 if ok else -1), -6),
                 size=11)
            for j, ln in enumerate(sub.split("|")):
                d.text(cx, PT + 258 + j * 15, ln, size=10, family="mono", fill=T.fg2, anchor="middle")
        d.text(RX + PW / 2, PT + 38, "hypothetical heading 45 deg (Pecos has none); dashed: the other result",
               size=10.5, fill=T.muted, anchor="middle")
        c1 = code(d, RX, bx.y1 + 14, [
            "// src/polygon_utils.cpp CreateRectangularPolygon",
            "// Note that boost rotates clockwise, and our headings are counter-clockwise.",
            "rotate_transformer<degree, double, 2, 2> rotate(-heading_deg);",
            "// src/collision_geometry.cpp BayOdpEntity::PolyAtPose",
            "return poly.Rotate(-1 * heading_opt.value()).Translate(node.x, node.y);",
            "// include/common_ros/collision_geometry.hpp CollisionEntity::PolyAtPose",
            "return poly.Rotate(pose.heading).Translate(node.x, node.y);   // AGV, tray, payload",
        ], w=PW, size=10, hl=(6,), hl_col=C_BAD)
        note(d, RX, c1.y1 + 14, PW,
             "Read from the code, not observed. A centred rectangle is unchanged by a half turn, so turning by "
             "+90 or -90 gives the same footprint: at 0, 90, -90 and 180 the clockwise call is harmless, and Pecos "
             "uses only those. At any other heading the collision-table footprints of the AGV, tray and payload "
             "would be the mirror image (about the y axis) of the ones polygon_utils builds for overlapping sized "
             "poses. A fix: Rotate(-pose.heading) in CollisionEntity::PolyAtPose.",
             title="Issue: CollisionEntity::PolyAtPose turns clockwise", accent=C_BAD, size=11)

    # step 7 --------------------------------------------------------------------------
    with d.only(K7):
        d.text(RX, 0, "8 · One AGV, three frames", size=13.5, weight=600, fill=T.fg)
        bx = panel_box(d, RX, PT, PW, 330, "AGV at node n, heading theta = 90")
        cx, cy, sc = RX + 300, PT + 170, 60
        agv_glyph(d, cx, cy, 90, sc, C_B)
        # G triad in the corner
        gx, gy = RX + 40, PT + 300
        axis(d, gx, gy, 1, 0, 60, C_G, "x_G east", lab_off=(30, 0), size=11)
        axis(d, gx, gy, 0, -1, 60, C_G, "y_G north", lab_off=(34, 0), size=11)
        z_up(d, gx, gy, C_G)
        fx, fy = hvec(90)
        axis(d, cx, cy, fx, fy, 160, C_B, "+x_B = y_P", lab_off=(0, 18), size=11.5)
        lx, ly = hvec(180)
        axis(d, cx, cy, lx, ly, 110, C_B, "+y_B (left)", lab_off=(44, 0), size=11.5)
        axis(d, cx + 8, cy - 8, 0, -1, 120, C_P, "x_P = -y_B (right)", lab_off=(70, 8), dash="5 3", size=11.5)
        z_up(d, cx, cy, C_B)
        d.text(cx + 100, cy + 50, "locomote: along x_B", size=11, family="mono", fill=C_LOC)
        d.text(cx + 100, cy + 68, "strafe: along y_B", size=11, family="mono", fill=C_STR)
        c1 = code(d, RX, bx.y1 + 14, [
            "theta: from +y_G, counter-clockwise          (GaragePose / GeometricPose)",
            "B -> G:  p_G = p_node + R(theta + pi/2) * p_B  (AGV frame, NodeAccuracy)",
            "P -> G:  p_G = p_node + R(theta) * p_P         (planner geometry, slots)",
            "B <-> P: x_P = -y_B,  y_P = +x_B",
            "forward f(theta) = (-sin theta, cos theta) = +x_B = +y_P",
        ], w=PW, size=10.5, hl=(1, 2), hl_col=C_P)

    # ------------------------------------------------------------------ table ----------
    rows = [
        ("agv_interfaces/msg/NodeAccuracy.msg", "garage frame '+x (east), +y (north), +z (up)'; x/y/yaw offsets 'in the "
         "AGV frame' (CCW positive)", "G, B", (K0, K2)),
        ("interfaces/msg/GaragePose.msg, GeometricPose.msg", "heading int16 degrees [-179, 180] / yaw rad; from garage "
         "local north, CCW; 'heading 90 points west'", "G (theta)", (K1,)),
        ("sources/5675_pecos_combined.yaml", "node x, y in metres; headings 0..179 (+ reciprocal); parking_windows "
         "length_m / width_m", "G", (K0, K5)),
        ("src/agv_motion_type.cpp  IsLocomoteOrStrafe", "LOCOMOTE if atan2 bearing = heading + pi/2 (or recip.), "
         "STRAFE if = heading; 1e-3 rad", "B", (K3,)),
        ("src/garage_graph.cpp  GarageGraph::LocomoteOrStrafe", "math_yaw = pi/2 + yaw; LOCOMOTE if |cos| > |sin| of "
         "the relative angle", "B", (K3,)),
        ("src/pose_graph.cpp, pose_graph.hpp", "FORWARD / LEFT / BACK / RIGHT by SignedAngleDist(heading_rad, "
         "bearing); bay outbound 'always LEFT', '+y direction'", "P", (K4,)),
        ("src/tape_layout.cpp  AddExtensionNode", "'AGV heading is zero out the right side of the vehicle'; "
         "BodyToInertial(1, 0, heading)", "P", (K4,)),
        ("include/common_ros/layout.hpp  GetInboundHeading", "'+y axis facing the system interior door' (y_P = +x_B)",
         "P", (K4,)),
        ("collision_geometry.hpp / .cpp", "RectangleFromSize(width, length): length on x; AGV, tray, payload "
         "BasePoly; PolyAtPose Rotate(+heading)", "P, net CW", (K5, K6)),
        ("src/polygon_utils.cpp", "CreateRectangularPolygon rotate(-heading_deg); CalcOverlappingSizedPoses: "
         "length_along_heading = width_m", "P, CCW", (K5, K6)),
        ("common/constants.hpp  (not in the snapshots)", "kAgvLength, kAgvWidth, kTray*: sizes only; drawn here as "
         "a 2.2 x 1.1 m schematic", "-", (K5,)),
    ]
    tx0 = 0
    tw = RX + PW
    ty0 = max(box.y1 + 60, 640)
    d.text(tx0, ty0, "Which source file fixes which frame", size=13.5, weight=600, fill=T.fg)
    rh = 24
    y0 = ty0 + 18
    cols = [("source", 10), ("what it defines", 400), ("frame", tw - 100)]
    d.rect(tx0, y0, tw, rh, rx=4, fill=T.tint(C_P, 0.14, T.bg))
    for hdr, ox in cols:
        d.text(tx0 + ox, y0 + rh / 2, hdr, size=10.5, family="mono", weight=600, fill=T.muted)
    for i, (src, what, fr, kk) in enumerate(rows):
        yy = y0 + rh * (i + 1)
        d.rect(tx0, yy, tw, rh, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        for k in kk:
            with d.only(k):
                d.rect(tx0 + 1, yy + 1, tw - 2, rh - 2, rx=3, fill=T.tint(C_P, 0.10, T.bg),
                       stroke=T.tint(C_P, 0.7, T.bg), sw=1.2, layer="main")
        fc = {"G": C_G, "B": C_B, "P": C_P}.get(fr[0], T.muted)
        if "CW" in fr and "CCW" not in fr:
            fc = C_BAD
        d.text(tx0 + 10, yy + rh / 2, src, size=10.5, family="mono", fill=T.fg)
        d.text(tx0 + 400, yy + rh / 2, what, size=11, fill=T.fg2)
        d.text(tx0 + tw - 100, yy + rh / 2, fr, size=11, family="mono", weight=700, fill=fc)
    d.rect(tx0, y0, tw, rh * (len(rows) + 1), rx=4, fill="none", stroke=T.tint(C_P, 0.5, T.bg), sw=1)

    frame(d, title="AGV and garage coordinate systems",
          subtitle="Step through the garage frame G, the heading, the AGV body frame B, locomote versus strafe on "
                   "real Pecos edges, the planner's helper frame P and its slot names, footprints built in P, and one "
                   "rotation-sign inconsistency. One heading theta, three frames: B and P differ by a quarter turn.",
          badge_key="as-built",
          legend=[("arrow", C_G, "garage frame G"), ("arrow", C_B, "body frame B (x forward, y left)"),
                  ("dasharrow", C_P, "helper frame P (x right, y forward)"), ("arrow", C_LOC, "LOCOMOTE (along x_B)"),
                  ("arrow", C_STR, "STRAFE (along y_B)"), ("dashbox", C_PAY, "payload window XL"),
                  ("box", T.green, "AGV (schematic 2.2 x 1.1 m)")],
          footnote="Map geometry from sources/5675_pecos_combined.yaml; code from sources/repomix-common-ros.xml and "
                   "repomix-interfaces.xml. The axes of B are the team's definition (the snapshots only say 'AGV "
                   "frame'). volley::SignedAngleDist, BodyToInertial and IsNearToAngleOrReciprocal (math_utils) and "
                   "common/constants.hpp are not in the snapshots. Step 7 is read from the code, not observed.")
    return d
