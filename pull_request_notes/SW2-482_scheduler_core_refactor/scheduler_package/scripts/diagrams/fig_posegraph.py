"""fig_posegraph: how poses, vertices and edges are built from the layout (148).

Doc 02-layout-file.html, section "From the layout to the graph: vertices and edges".

148  W8 and its four layout neighbours W31, W9, W4, W13 (Pecos), drawn as a schematic plus: one vertex
     per (node, heading), translation edges that keep the heading, rotation edges only at W8, edge types,
     and one route that needs a rotation (animated). Code: pose_graph.cpp constructor and
     garage_graph.cpp constructor / AddEdge, abridged.

Headings, rotation flags and edges are the Pecos YAML; vertex numbers are pose indices recomputed with
fig_layout.POSES (node-id order, ascending heading), which is the Boost vertex order (vecS, add_vertex in
pose order). Volley heading convention: 0 = north, counter-clockwise, 90 faces west.
"""
from __future__ import annotations

import math

from components import code_panel, frame, label_pill, num_badge
from fig_layout import POSES, allowed, slots
from fig_reserve import _hl_code
from registry import figure
from svgkit import BBox, Doc
from theme import T

DOC = "02-layout-file.html"
VX = T.teal              # vertex (pose)
FOC = T.sky              # the pose in focus
LOC, STR, ROT = T.green, T.amber, T.pink
NEU = T.fg2              # translation edge before it is typed

SP = 330                 # schematic spacing between nodes
MG = 165                 # margin around the outer nodes
CX, CY = SP + MG, SP + MG - 10   # W8
R8, RN_ = 130, 100       # drawn radius of W8 and of a neighbour
NODE_XY = {8: (CX, CY), 31: (CX - SP, CY), 9: (CX + SP, CY), 13: (CX, CY - SP), 4: (CX, CY + SP)}
NB = [31, 9, 13, 4]
D = 60                   # diagonal offset of the +-90 vertices
RN = 86                  # offset of the 0 / 180 vertices
VR = 16                  # vertex radius

# heading -> offset of its vertex from the node centre (svg y down)
OFF = {90: (-D, -D), -90: (D, D), 0: (0, -RN), 180: (0, RN)}
VID = {p: i for i, p in enumerate(POSES)}
ROUTE = [(31, 90), (8, 90), (8, 0), (8, -90), (31, -90)]
assert VID[(8, 90)] == 16 and VID[(22, 90)] == 44

# what each slot means for the AGV, and the motion type GarageGraph gives it
AGV_DIR = {"FORWARD": "right", "BACK": "left", "LEFT": "forward", "RIGHT": "back"}
KIND = {"FORWARD": "STRAFE", "BACK": "STRAFE", "LEFT": "LOCOMOTE", "RIGHT": "LOCOMOTE"}


def deg(h):
    return f"{h}°".replace("-", "−")


def vxy(nid, h):
    x, y = NODE_XY[nid]
    ox, oy = OFF[h]
    return x + ox, y + oy


def facing(h):
    """Unit vector (svg) of the AGV's facing at heading h: 0 north, counter-clockwise."""
    a = math.radians(h)
    return -math.sin(a), -math.cos(a)


def vertex(d: Doc, nid, h, *, col=VX, strong=False):
    x, y = vxy(nid, h)
    d.circle(x, y, VR, fill=T.tint(col, 0.30 if strong else 0.16, T.bg_deep), stroke=col, sw=2.4 if strong else 1.6,
             layer="top")
    fx, fy = facing(h)
    tip = (x + fx * (VR + 9), y + fy * (VR + 9))
    d.arrowhead(tip, (x, y), kind="filled", color=col, size=8, layer="top")
    d.text(x, y + 0.5, f"{h}".replace("-", "−"), size=9.5, family="mono", weight=700, fill=col if strong else T.fg,
           anchor="middle", layer="top")


def seg(d: Doc, a, b, col, *, sw=2.2, both=True, dash=None, layer="edges", cut=VR + 3, op=None):
    (x0, y0), (x1, y1) = a, b
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    p0 = (x0 + ux * cut, y0 + uy * cut)
    p1 = (x1 - ux * cut, y1 - uy * cut)
    d.line(p0[0] + (ux * 7 if both else 0), p0[1] + (uy * 7 if both else 0), p1[0] - ux * 7, p1[1] - uy * 7,
           stroke=col, sw=sw, dash=dash, layer=layer, opacity=op)
    d.arrowhead(p1, p0, kind="filled", color=col, size=10, layer=layer)
    if both:
        d.arrowhead(p0, p1, kind="filled", color=col, size=10, layer=layer)


def rot_curve(d: Doc, h0, h1, col, *, sw=2.6, both=True, layer="over", bulge=16):
    """Edge on W8 from the vertex of heading h0 to that of h1, running round the node centre the short way
    (counter-clockwise if h1 is the next heading counter-clockwise), bulging outwards."""
    (x0, y0), (x1, y1) = vxy(8, h0), vxy(8, h1)
    a0 = math.atan2(-(y0 - CY), x0 - CX)
    a1 = math.atan2(-(y1 - CY), x1 - CX)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    r0, r1 = math.hypot(x0 - CX, y0 - CY), math.hypot(x1 - CX, y1 - CY)
    n = 40
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a0 + da * t
        r = r0 + (r1 - r0) * t + bulge * math.sin(math.pi * t)
        pts.append((CX + r * math.cos(a), CY - r * math.sin(a)))
    keep = [p for p in pts if math.hypot(p[0] - x0, p[1] - y0) > VR + 4 and math.hypot(p[0] - x1, p[1] - y1) > VR + 4]
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in keep)
    d.path(path, stroke=T.bg_deep, sw=sw + 3.5, layer=layer)
    d.path(path, stroke=col, sw=sw, layer=layer)
    d.arrowhead(keep[-1], keep[-3], kind="filled", color=col, size=10, layer=layer)
    if both:
        d.arrowhead(keep[0], keep[2], kind="filled", color=col, size=10, layer=layer)
    return keep[len(keep) // 2]


@figure("148_pose_graph_construction", "How vertices and edges are built from the layout (animated)", DOC)
def pose_graph_construction():
    d = Doc("148_pose_graph_construction", "How vertices and edges are built from the layout",
            "Animated schematic of W8 and its four Pecos neighbours: one vertex per node and heading, translation "
            "edges that keep the heading and need both nodes to allow it, rotation edges only at W8 because only W8 "
            "has rotation_allowed, the motion type of each edge, and a route that needs two rotations; beside the "
            "abridged constructors of PoseGraph and GarageGraph.")

    caps = [
        "The layout part. W8 and its four neighbours (schematic, not to scale) with the four YAML edges between "
        "them. The edges are undirected and know nothing about headings. W8 lists headings [0°, 90°] and "
        "rotation_allowed: true; W31, W9, W4 and W13 list [90°] and may not rotate. Their other edges are not drawn.",
        "Vertices. GetAllowedHeadings adds the reciprocal of every listed heading, and PoseGraph makes one pose per "
        "(node, heading), in node-id order. W8 gets four poses, each neighbour two. GarageGraph adds one vertex per "
        "pose in the same order, so the vertex number is the pose index: (W8, 90°) is v16. The tick on each circle "
        "is where the AGV faces.",
        "Translation rule, shown for (W8, 90°). For each layout neighbour, PoseGraph builds the pose with the same "
        "heading, (Wn, 90°), and keeps the edge only if that pose exists. All four neighbours allow 90°, so v16 gets "
        "four translation edges. A translation never changes the heading: the AGV moves without turning.",
        "Which slot each edge is stored in. The slot comes from the edge's bearing minus the heading taken as a math "
        "angle, which is a quarter turn off the AGV's own frame. The AGV at (W8, 90°) faces west: W31 is its forward "
        "(slot LEFT), W9 its back (RIGHT), W13 its right (FORWARD) and W4 its left (BACK).",
        "The same rule for every pose. The 90° vertices form one layer and the −90° vertices another; each layout "
        "edge gives one directed edge each way in each layer: 4 layout edges × 2 headings × 2 directions = 16 "
        "translation edges in this sketch. Nothing connects the two layers yet.",
        "(W8, 0°) and (W8, 180°). The rule looks for (W31, 0°), (W9, 0°), (W13, 0°), (W4, 0°) and the 180° "
        "equivalents, and finds none: no neighbour allows 0° or 180°. These two vertices get no translation edge; "
        "they exist only as steps for turning.",
        "Rotation edges, only at nodes with rotation_allowed. Each pose of W8 links to the nearest other heading of "
        "W8 clockwise (ROT_RIGHT) and counter-clockwise (ROT_LEFT): from 90°, ROT_RIGHT is 0° and ROT_LEFT is 180°. "
        "Four poses × 2 = 8 directed ROTATION edges, a ring that joins the two layers. The neighbours have none.",
        "Edge types, set by GarageGraph::AddEdge. Rotation slots become ROTATION (length: the yaw difference). A "
        "translation is typed by geometry: along the AGV's facing axis (east–west here) it is LOCOMOTE, sideways "
        "(north–south) STRAFE. The slot name plays no part; (W8, 90°) to (W13, 90°) is a STRAFE.",
        "A route that needs rotation: turn an AGV at W31 from 90° to −90°. W31 cannot rotate, so the shortest route "
        "drives to W8 (LOCOMOTE, backwards), turns twice (90° to 0° to −90°) and drives back (LOCOMOTE, now "
        "forwards): v57, v16, v15, v14, v56. Through 180° instead costs the same.",
    ]
    ks = [d.step(c) for c in caps]
    K_LAY, K_VX, K_RULE, K_SLOT, K_ALL, K_STEP, K_ROT, K_TYPE, K_ROUTE = ks

    d.text(0, 0, "W8 and its four neighbours (schematic)", size=13.5, weight=600, fill=T.fg)
    box = BBox(CX - SP - MG, CY - SP - MG, CX + SP + MG, CY + SP + MG)
    d.rect(box.x0, box.y0 + 30, box.w, box.h - 30, rx=12, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
    # compass
    nx, ny = box.x1 - 40, box.y0 + 74
    d.line(nx, ny + 18, nx, ny - 12, stroke=T.muted, sw=1.6)
    d.arrowhead((nx, ny - 18), (nx, ny + 18), kind="filled", color=T.muted, size=8)
    d.text(nx, ny - 30, "N", size=11, weight=600, fill=T.muted, anchor="middle")

    # ---- layout: nodes and undirected edges ----
    for nid in NB:
        x, y = NODE_XY[nid]
        with d.at(K_LAY, K_LAY):
            d.line(CX, CY, x, y, stroke=T.border, sw=6, layer="under")
        with d.at(K_VX):
            d.line(CX, CY, x, y, stroke=T.border_soft, sw=4, layer="under", dash="2 6")
    for nid, (x, y) in NODE_XY.items():
        d.circle(x, y, R8 if nid == 8 else RN_, fill=T.tint(T.fg2, 0.05, T.bg_deep), stroke=T.border, sw=1.2,
                 dash=None if nid == 8 else "4 4", layer="under")
        with d.at(K_LAY, K_LAY):
            d.circle(x, y, 7, fill=T.fg2, layer="main")
        lx, ly, anc_ = (x, y + RN_ + 20, "middle") if nid != 8 else (x - R8 * 0.71 - 4, y - R8 * 0.71 - 4, "end")
        d.text(lx, ly, f"W{nid}", size=13, family="mono", weight=700, fill=T.fg, anchor=anc_, halo=T.bg_deep,
               halo_w=4)
    yaml_tag = {8: "headings [0°, 90°] · rotation_allowed: true", 31: "[90°] · no rotation",
                9: "[90°] · no rotation", 13: "[90°] · no rotation", 4: "[90°] · no rotation"}
    tag_pos = {8: (CX + 24, CY - R8 - 20, "start"), 31: (CX - SP, CY + RN_ + 46, "middle"),
               9: (CX + SP, CY + RN_ + 46, "middle"),
               13: (CX + RN_ + 12, CY - SP, "start"), 4: (CX + RN_ + 12, CY + SP, "start")}
    with d.only(K_LAY):
        for nid, (x, y, anc) in tag_pos.items():
            label_pill(d, x, y, yaml_tag[nid], color=T.fg2, bg=T.bg_deep, border=T.border, size=10.5, anchor=anc,
                       layer="top")

    # ---- vertices ----
    for nid in NODE_XY:
        for h in allowed(nid):
            if (nid, h) == (8, 90):
                with d.only(K_VX):
                    vertex(d, nid, h)
                with d.at(K_RULE, K_SLOT):
                    vertex(d, nid, h, col=FOC, strong=True)
                with d.at(K_ALL, K_TYPE):
                    vertex(d, nid, h)
            else:
                with d.at(K_VX, K_TYPE if (nid, h) in ROUTE else None):
                    vertex(d, nid, h)
    # vertex numbers
    vlab = {}
    for nid in NODE_XY:
        for h in allowed(nid):
            x, y = vxy(nid, h)
            if nid == 8:
                pos = {90: (x - 22, y - 22, "end"), -90: (x + 22, y + 26, "start"), 0: (x + 22, y - 8, "start"),
                       180: (x - 22, y + 10, "end")}[h]
            else:
                pos = (x - 22, y - 20, "end") if h == 90 else (x + 22, y + 22, "start")
            vlab[(nid, h)] = pos
    with d.at(K_VX):
        for (nid, h), (x, y, anc) in vlab.items():
            d.text(x, y, f"v{VID[(nid, h)]}", size=10.5, family="mono", weight=600, fill=T.muted, anchor=anc,
                   halo=T.bg_deep, halo_w=3, layer="top")

    # ---- translation edges ----
    def tcol(nid):
        return LOC if nid in (31, 9) else STR

    for nid in NB:
        for h in (90, -90):
            a, b = vxy(8, h), vxy(nid, h)
            focus = h == 90
            if focus:
                with d.at(K_RULE, K_SLOT):
                    seg(d, a, b, FOC, sw=2.8, both=False)
            with d.at(K_ALL, K_STEP):
                seg(d, a, b, NEU, sw=2.0)
            with d.at(K_ROT, K_ROT):
                seg(d, a, b, NEU, sw=1.6, op=0.45)
            with d.at(K_TYPE, K_TYPE):
                seg(d, a, b, tcol(nid), sw=2.4)
            with d.at(K_ROUTE):
                seg(d, a, b, tcol(nid), sw=1.6, op=0.35)
    # slot labels for (W8, 90)
    slot_of = {v[0]: k for k, v in slots((8, 90)).items() if not k.startswith("ROT")}
    lab_xy = {31: (CX - SP / 2 - 44, CY - D - 22), 9: (CX + SP / 2 - 12, CY - D - 22),
              13: (CX - D - 12, CY - SP / 2 - 18), 4: (CX - D - 12, CY + SP / 2 + 26)}
    with d.only(K_SLOT):
        for nid, (x, y) in lab_xy.items():
            sl = slot_of[nid]
            anc = "middle" if nid in (31, 9) else "end"
            label_pill(d, x, y, f"{sl} slot = AGV {AGV_DIR[sl]}", color=tcol(nid), bg=T.bg_deep, border=tcol(nid),
                       size=10.5, anchor=anc, layer="top")
        # the AGV's own frame at (W8, 90)
        x, y = vxy(8, 90)
        label_pill(d, CX + 92, CY - 140, "AGV at (W8, 90°) faces west", color=FOC, bg=T.bg_deep, border=FOC,
                   size=10.5, anchor="start", layer="top")
    with d.at(K_RULE, K_RULE):
        label_pill(d, CX + 92, CY - 140, "same heading: (Wn, 90°)", color=FOC, bg=T.bg_deep, border=FOC, size=10.5,
                   anchor="start", layer="top")
    # counts / layers
    with d.only(K_ALL):
        label_pill(d, CX - SP - 60, CY - D - 22, "90° layer", color=T.fg2, bg=T.bg_deep, border=T.border,
                   size=10.5, anchor="start", layer="top")
        label_pill(d, CX + SP + 60, CY + D + 24, "−90° layer", color=T.fg2, bg=T.bg_deep, border=T.border,
                   size=10.5, anchor="end", layer="top")
    # stepping stones: failed look-ups
    with d.only(K_STEP):
        for h in (0, 180):
            a = vxy(8, h)
            for nid in NB:
                x, y = NODE_XY[nid]
                tx, ty = x + (a[0] - CX), y + (a[1] - CY)
                d.circle(tx, ty, VR - 2, fill="none", stroke=T.red, sw=1.4, dash="3 3", layer="top")
                d.line(tx - 5, ty - 5, tx + 5, ty + 5, stroke=T.red, sw=1.6, layer="top")
                d.line(tx + 5, ty - 5, tx - 5, ty + 5, stroke=T.red, sw=1.6, layer="top")
        label_pill(d, CX + 92, CY - 140, "(Wn, 0°), (Wn, 180°): no such pose", color=T.red, bg=T.bg_deep,
                   border=T.red, size=10.5, anchor="start", layer="top")
        for h in (0, 180):
            x, y = vxy(8, h)
            d.circle(x, y, VR + 5, fill="none", stroke=T.red, sw=1.6, layer="top")

    # ---- rotation ring ----
    ring = [(90, 180), (180, -90), (-90, 0), (0, 90)]   # counter-clockwise order of headings
    with d.at(K_ROT, K_TYPE):
        for h0, h1 in ring:
            rot_curve(d, h0, h1, ROT)
    with d.at(K_ROUTE):
        for h0, h1 in ring:
            rot_curve(d, h0, h1, ROT, sw=1.6)
    with d.only(K_ROT):
        label_pill(d, CX + 92, CY - 140, "ROT_RIGHT: clockwise · ROT_LEFT: counter-clockwise", color=ROT,
                   bg=T.bg_deep, border=ROT, size=10.5, anchor="start", layer="top")
    # ---- types legend inside the sketch ----
    with d.only(K_TYPE):
        label_pill(d, CX + 92, CY - 140, "LOCOMOTE east–west · STRAFE north–south", color=T.fg2, bg=T.bg_deep,
                   border=T.border, size=10.5, anchor="start", layer="top")

    # ---- route ----
    route = ROUTE
    with d.at(K_ROUTE):
        seg(d, vxy(31, 90), vxy(8, 90), FOC, sw=3.4, both=False, layer="top")
        # 90 -> 0 and 0 -> -90 are clockwise: draw them as arcs from the target side
        m2 = rot_curve(d, 90, 0, FOC, sw=3.4, both=False, layer="top")
        m3 = rot_curve(d, 0, -90, FOC, sw=3.4, both=False, layer="top")
        seg(d, vxy(8, -90), vxy(31, -90), FOC, sw=3.4, both=False, layer="top")
        for p in route:
            vertex(d, p[0], p[1], col=FOC, strong=True)

        def out(pt, r=22):
            vx_, vy_ = pt[0] - CX, pt[1] - CY
            L = math.hypot(vx_, vy_)
            return pt[0] + vx_ / L * r, pt[1] + vy_ / L * r
        for i, (bx, by) in enumerate([(CX - SP / 2, CY - D - 20), out(m2), out(m3), (CX - SP / 2, CY + D + 20)]):
            num_badge(d, bx, by, i + 1, FOC)

    # ================= right column: code and the out-edges of v16 =================
    rx = box.x1 + 50
    d.text(rx, 0, "How the two constructors build them (abridged)", size=13.5, weight=600, fill=T.fg)
    code = [
        "// pose_graph.cpp, PoseGraph::PoseGraph(layout)",
        "for(const auto& node : layout_->GetNodes())",
        "  for(int16_t heading : GetAllowedHeadings(node)) {  // YAML + reciprocals",
        "    Pose pose = ConstructGaragePose(node.id, heading);",
        "    pose_indices_.emplace(pose, poses_.size());",
        "    poses_.emplace_back(pose);",
        "  }",
        "for(each pose) {                                    // 8 slots, all -1",
        "  for(const Node& node_dest : layout_->GetNeighboringNodes(node.id)) {",
        "    Pose pose_dest = ConstructGaragePose(node_dest.id, pose.heading);",
        "    if(pose_indices_.find(pose_dest) == pose_indices_.end())",
        "      continue;                     // heading not valid at node_dest",
        "    // (VRC pairs and disallowed_edge_orientation elided)",
        "    double bearing = std::atan2(node_dest.y - node.y, node_dest.x - node.x);",
        "    double relative_bearing = SignedAngleDist(heading_rad, bearing);",
        "    // 0 FORWARD, +pi/2 LEFT, pi BACK, -pi/2 RIGHT (within 0.1 rad)",
        "  }",
        "  if(node.rotation_allowed)",
        "    for(int16_t heading_dest : GetAllowedHeadings(node))  // same node",
        "      // nearest clockwise -> ROT_RIGHT, counter-clockwise -> ROT_LEFT",
        "}",
        "// garage_graph.cpp, GarageGraph::GarageGraph(pose_graph)",
        "for(const auto& pose : pose_graph.GetPoses())",
        "  pose_to_vertex_[pose] = boost::add_vertex(pose, base_graph_);  // vN = pose N",
        "for(const auto& pose : pose_graph.GetPoses())",
        "  for(auto pose_neighbor : kPoseNeighbors)        // every filled slot",
        "    AddEdge(pose, dest_pose, pose_neighbor);       // one directed edge",
        "// AddEdge: ROT_* -> ROTATION, VRC_* -> VRC_TRANSITION,",
        "//          otherwise LocomoteOrStrafe(src, dst): geometry, not the slot",
    ]
    CS = 11
    cp = code_panel(d, rx, 22, 640, code, size=CS, title="pose_graph.cpp (constructor) · garage_graph.cpp (constructor, AddEdge)")
    hl = {K_LAY: [(1, 1)], K_VX: [(1, 5), (21, 23)], K_RULE: [(8, 11)], K_SLOT: [(13, 15)], K_ALL: [(7, 16)],
          K_STEP: [(9, 11)], K_ROT: [(17, 19)], K_TYPE: [(24, 28)], K_ROUTE: []}
    cols = {K_LAY: T.fg2, K_VX: VX, K_RULE: FOC, K_SLOT: FOC, K_ALL: NEU, K_STEP: T.red, K_ROT: ROT,
            K_TYPE: LOC, K_ROUTE: FOC}
    for k, spans in hl.items():
        with d.only(k):
            for a, b in spans:
                _hl_code(d, cp, a, b, size=CS, col=cols[k])

    # out-edges of v16
    ty = cp.y1 + 40
    d.text(rx, ty, "Out-edges of v16 = (W8, 90°): one per filled slot", size=13.5, weight=600, fill=T.fg)
    hdr = [("slot (code)", 0), ("to", 120), ("AGV direction", 270), ("edge type", 430)]
    rh = 26
    y0 = ty + 16
    d.rect(rx, y0, 640, rh, rx=4, fill=T.tint(VX, 0.14, T.bg))
    for h_, o in hdr:
        d.text(rx + 10 + o, y0 + rh / 2, h_, size=10.5, family="mono", weight=600, fill=T.muted)
    s16 = slots((8, 90))
    rows = [("LEFT", "forward (west)", "LOCOMOTE", LOC), ("RIGHT", "back (east)", "LOCOMOTE", LOC),
            ("FORWARD", "right (north)", "STRAFE", STR), ("BACK", "left (south)", "STRAFE", STR),
            ("ROT_RIGHT", "turn clockwise", "ROTATION", ROT), ("ROT_LEFT", "turn counter-cw", "ROTATION", ROT)]
    for i, (sl, dirn, kind, col) in enumerate(rows):
        yy = y0 + rh * (i + 1)
        d.rect(rx, yy, 640, rh, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        dst = s16[sl]
        rot = sl.startswith("ROT")
        k_row = K_ROT if rot else K_RULE
        with d.at(k_row):
            d.text(rx + 10 + 120, yy + rh / 2, f"(W{dst[0]}, {deg(dst[1])})  v{VID[dst]}", size=11, family="mono",
                   fill=T.fg)
        with d.at(K_ROT if rot else K_SLOT):
            d.text(rx + 10, yy + rh / 2, sl, size=11, family="mono", weight=600, fill=T.fg)
            d.text(rx + 10 + 270, yy + rh / 2, dirn, size=11, family="mono", fill=T.fg2)
        with d.at(K_TYPE):
            d.text(rx + 10 + 430, yy + rh / 2, kind, size=11, family="mono", weight=700, fill=col)
    for i in (6, 7):
        yy = y0 + rh * (i + 1)
        d.rect(rx, yy, 640, rh, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        with d.at(K_VX):
            d.text(rx + 10, yy + rh / 2, ("VRC_UP", "VRC_DOWN")[i - 6], size=11, family="mono", fill=T.faint)
            d.text(rx + 10 + 120, yy + rh / 2, "-1 (no VRC: no edge)", size=11, family="mono", fill=T.faint)
    tb = BBox(rx, y0, rx + 640, y0 + rh * 9)
    d.rect(rx, y0, 640, rh * 9, rx=4, fill="none", stroke=T.tint(VX, 0.5, T.bg), sw=1)

    # counts
    cy0 = tb.y1 + 34
    d.text(rx, cy0, "Counts in this sketch", size=13.5, weight=600, fill=T.fg)
    counts = [("vertices", "W8: 4, each neighbour: 2", "12", K_VX),
              ("translation edges", "4 layout edges × 2 headings × 2 ways", "16", K_ALL),
              ("rotation edges", "4 poses of W8 × 2 (ROT_LEFT, ROT_RIGHT)", "8", K_ROT)]
    for i, (a, b, v, k) in enumerate(counts):
        yy = cy0 + 18 + i * 24
        d.rect(rx, yy, 640, 24, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        d.text(rx + 10, yy + 12, a, size=11, fill=T.fg2)
        with d.at(k):
            d.text(rx + 190, yy + 12, b, size=10.5, family="mono", fill=T.muted)
            d.text(rx + 630, yy + 12, v, size=11.5, family="mono", weight=700, fill=T.fg, anchor="end")

    frame(d, title="How vertices and edges are built from the layout",
          subtitle="One vertex per node and heading; translation edges keep the heading and need both nodes to allow "
                   "it; rotation edges stay on one node and exist only where rotation_allowed is true. Step through "
                   "W8 and its four Pecos neighbours.",
          badge_key="yaml",
          legend=[("dot", VX, "vertex = pose (node, heading); tick = facing"), ("arrow", LOC, "LOCOMOTE"),
                  ("arrow", STR, "STRAFE"), ("arrow", ROT, "ROTATION"), ("arrow", FOC, "edge or route in focus")],
          footnote="Schematic: distances are not to scale (W8–W31 is 2.86 m, W8–W9 6.30 m, W8–W4 2.29 m, W8–W13 "
                   "4.39 m). Headings, rotation flags and edges from the Pecos YAML; vertex numbers are pose "
                   "indices, which equal Boost vertex indices because GarageGraph adds the vertices in pose order "
                   "to a vecS adjacency_list. A double-headed line or arc stands for two directed edges, one each "
                   "way. Heading convention: 0° north, counter-clockwise, 90° faces west.")
    return d
