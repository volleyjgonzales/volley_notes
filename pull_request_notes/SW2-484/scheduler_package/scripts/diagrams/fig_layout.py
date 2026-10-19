"""fig_layout: figures for the Layout file tab (doc 02-layout-file.html).

105  who reads the layout file (static)
106  the Pecos YAML side by side with the map it describes (animated)
107  one node becomes poses and neighbour slots (animated)
108  faces_reciprocal and the inbound heading of bays and chargers (animated)

Every number is read from sources/5675_pecos_combined.yaml or recomputed with the rules in
sources/repomix-common-ros.xml (layout.cpp, pose_utils.cpp, pose_graph.cpp, garage_graph.cpp).
Line numbers "file.cpp L123" are lines inside the file as it appears in the repomix snapshot.

Heading convention (GaragePose.msg, fig 78): degrees, 0 along world +y, counter-clockwise positive,
so 90 faces west. "Faces" means the AGV's body +y axis, which is its locomote (driving) axis;
body +x is the strafe axis. GeometricPose.yaw = heading in radians.
"""
from __future__ import annotations

import hashlib
import math

from components import chip, code_panel, connect, frame, label_pill, note, num_badge, uml_class
from facility import (C_BAY, C_CHG, C_PARK, C_WP, EDGES, NODES, STALL_L, STALL_W, WINDOWS, YAML, Map)
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import T, S

DOC = "02-layout-file.html"
LAY, PG, GG, CT = T.sky, T.teal, T.green, T.amber   # same colours as figs 75-81
FULL_X, FULL_Y = (20.0, 46.6), (6.4, 25.6)

YAML_TEXT = YAML.read_text()
YAML_LINES = YAML_TEXT.splitlines()
YAML_MD5 = hashlib.md5(YAML.read_bytes()).hexdigest()
BUF_L = 0.1524
BUF_W = 0.0762


def wrap_deg(a):
    """volley::Wrap as GaragePose.msg defines the range: degrees in [-179, 180]."""
    return (a + 179) % 360 - 179


def allowed(nid):
    """GetAllowedHeadings: every YAML heading h gives Wrap(h) and Wrap(h + 180), sorted."""
    return sorted({wrap_deg(h + dd) for h in NODES[nid].headings for dd in (0, 180)})


ADJ = {i: set() for i in NODES}
for _a, _b in EDGES:
    ADJ[_a].add(_b)
    ADJ[_b].add(_a)
POSES = [(i, h) for i in sorted(NODES) for h in allowed(i)]


def _sad(a, b):
    """SignedAngleDist(a, b) taken as b - a wrapped to [-pi, pi) (inferred, see report section 2)."""
    return (b - a + math.pi) % (2 * math.pi) - math.pi


def slots(pose):
    """PoseGraph neighbour slots of one pose, exactly as pose_graph.cpp L58-165 assigns them."""
    nid, h = pose
    out = {}
    n = NODES[nid]
    for j in sorted(ADJ[nid]):
        if (j, h) not in POSES:
            continue
        m = NODES[j]
        rel = _sad(math.radians(h), math.atan2(m.y - n.y, m.x - n.x))
        for name, ang in (("FORWARD", 0.0), ("LEFT", math.pi / 2), ("BACK", math.pi), ("RIGHT", -math.pi / 2)):
            if abs(_sad(ang, rel)) < 0.1:
                out[name] = (j, h)
                break
        else:
            raise ValueError(f"invalid translation {pose} -> {j}")
    if n.rotation:
        others = [g for g in allowed(nid) if g != h]
        out["ROT_RIGHT"] = (nid, min(others, key=lambda g: (h - g) % 360))   # clockwise
        out["ROT_LEFT"] = (nid, min(others, key=lambda g: (g - h) % 360))    # counter-clockwise
    return out


N_POSES = len(POSES)
N_FILLED = sum(len(slots(p)) for p in POSES)
N_ROT = sum(1 for p in POSES for k in slots(p) if k.startswith("ROT"))
assert N_POSES == 60 and N_FILLED == 164 and N_ROT == 16, (N_POSES, N_FILLED, N_ROT)
assert slots((8, 90)) == {"FORWARD": (13, 90), "BACK": (4, 90), "LEFT": (31, 90), "RIGHT": (9, 90),
                          "ROT_RIGHT": (8, 0), "ROT_LEFT": (8, 180)}
assert slots((7, -90)) == {"LEFT": (31, -90)}


def hvec(h):
    """Unit vector in SVG space of the facing (body +y) of heading h."""
    a = math.radians(h)
    return -math.sin(a), -math.cos(a)


def head_arrow(d, x, y, h, color, *, L=34, sw=2.6, size=10, layer="top", start=0.0, opacity=None):
    """Arrow from (x, y) in the facing direction of heading h."""
    fx, fy = hvec(h)
    x0, y0 = x + fx * start, y + fy * start
    tip = (x + fx * L, y + fy * L)
    d.line(x0, y0, tip[0] - fx * size * 0.6, tip[1] - fy * size * 0.6, stroke=color, sw=sw, layer=layer,
           opacity=opacity)
    d.arrowhead(tip, (x0, y0), kind="filled", color=color, size=size, layer=layer)
    return tip


def lbl(nid):
    n = NODES[nid]
    return {"Parking": "P", "Waypoint": "W", "Bay": "B", "AgvCharge": "C"}[n.type] + str(nid)


# --------------------------------------------------------------------------------------
# YAML panel: line-number gutter, light syntax colouring, rows addressable by YAML line number
# --------------------------------------------------------------------------------------
class YamlPanel:
    def __init__(self, d: Doc, x, y, w, items, *, size=11.0, lh=1.42, title=None):
        """items: YAML line numbers (int), or ("...", text) elision rows."""
        self.d, self.x, self.y, self.w = d, x, y, w
        self.size, self.lhp = size, size * lh
        pad = 12
        th = 26 if title else 0
        self.top = y + pad + th
        self.rows = {}
        h = pad * 2 + th + len(items) * self.lhp
        self.bb = BBox(x, y, x + w, y + h)
        d.rect(x, y, w, h, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
        if title:
            d.text(x + pad, y + pad + 6, title, size=11, family="mono", weight=600, fill=T.muted)
        gx = x + 44
        d.line(gx, self.top - 4, gx, y + h - pad + 4, stroke=T.border_soft, sw=1, layer="under")
        for i, it in enumerate(items):
            cy = self.top + i * self.lhp + self.lhp / 2
            if isinstance(it, int):
                self.rows[it] = cy
                d.text(gx - 8, cy, str(it), size=size - 1.5, family="mono", fill=T.faint, anchor="end")
                self._line(gx + 10, cy, YAML_LINES[it - 1])
            else:
                d.text(gx + 10, cy, it[1], size=size - 0.5, family="mono", style="italic", fill=T.faint)

    def _line(self, x, y, s):
        runs = []
        body, cmt = s, ""
        if "#" in s:
            i = s.index("#")
            body, cmt = s[:i], s[i:]
        if ":" in body and not body.strip().startswith("#"):
            i = body.index(":")
            key, val = body[:i + 1], body[i + 1:]
            k0 = len(key) - len(key.lstrip())
            dash = ""
            kk = key.lstrip()
            if kk.startswith("- "):
                dash, kk = "- ", kk[2:]
            runs += [(" " * k0, "mono", 400, T.fg), (dash, "mono", 400, T.muted), (kk, "mono", 400, T.tint(LAY, 0.9, T.bg_deep)),
                     (val, "mono", 400, T.fg)]
        else:
            runs.append((body, "mono", 400, T.fg))
        runs = [r for r in runs if r[0]]
        if runs:
            self.d.rich(x, y, runs, size=self.size)
        if cmt:
            w = text_width(body, self.size, "mono")
            self.d.text(x + w, y, cmt, size=self.size, family="mono", style="italic", fill=T.green)

    def band(self, lines, color, k0, k1=None):
        """Highlight the rows of these YAML line numbers during steps k0..k1."""
        with self.d.at(k0, k0 if k1 is None else k1):
            for ln in lines:
                cy = self.rows[ln]
                self.d.rect(self.x + 48, cy - self.lhp / 2, self.w - 54, self.lhp, rx=3,
                            fill=T.tint(color, 0.24, T.bg_deep), layer="main")
                self.d.rect(self.x + 46, cy - self.lhp / 2, 3, self.lhp, fill=color, layer="main")


def lines_box(d, x, y, lines, color, *, size=10.5, w=None, pad=8, family="mono", title=None, anchor="start",
              fill=None, layer="labels"):
    """Rounded label box holding several lines. (x, y) = top-left (anchor 'start') or top-centre."""
    lh = size * 1.45
    tw = max(text_width(s, size, family) for s in lines)
    if title:
        tw = max(tw, text_width(title, size, "sans", 600))
    w = w or tw + 2 * pad
    if anchor == "middle":
        x -= w / 2
    h = 2 * pad + len(lines) * lh - (lh - size) + (lh + 2 if title else 0)
    d.rect(x, y, w, h, rx=6, fill=fill or T.tint(color, 0.08, T.bg), stroke=T.tint(color, 0.55, T.bg), sw=1, layer=layer)
    yy = y + pad + size / 2 + 1
    if title:
        d.text(x + pad, yy, title, size=size, weight=600, fill=color, layer="top")
        yy += lh + 2
    for s in lines:
        d.text(x + pad, yy, s, size=size, family=family, fill=T.fg2, layer="top")
        yy += lh
    return BBox(x, y, x + w, y + h)


# ======================================================================================
# 105 — who reads the layout file
# ======================================================================================

@figure("105_layout_consumers", "Who reads the layout file", DOC)
def layout_consumers():
    d = Doc("105_layout_consumers", "Who reads the layout file",
            "The Pecos YAML is found by name, parsed once into a Layout, turned into a PoseGraph, a GarageGraph "
            "and a CollisionTable, and then read by the scheduler, the motion planner, the action graph, the safety "
            "checker, the tape tool and the GetGarageLayout message. Arrow labels name the fields that flow.")
    # ---------------- column B: the Layout object (top left) ----------------
    bx = 0
    d.text(bx, 0, "3  Parsed once: volley::Layout (layout.hpp)", size=13.5, weight=600, fill=T.fg)
    members = [("- name_: std::string", "name"),
               ("- md5sum_: std::string", "(md5 of the file)"),
               ("- parking_window_buffer_: ParkingWindowMsg", "parking_window_buffer"),
               ("- resource_windows_: vector<ParkingWindowMsg>", "parking_windows + TRAY"),
               ("- nodes_: vector<GarageNodeMsg>", "nodes, sorted by id"),
               ("- node_ids_by_type_: map<type, vector<id>>", "nodes[].type"),
               ("- graph_: boost::adjacency_list", "edges (+ VRC pairs)"),
               ("- disallowed_edge_orientations_: map", "edges[].disallowed_..."),
               ("- bay_prioritization_: vector<uint16_t>", "prioritization_value"),
               ("- floors_: vector<GarageFloorMsg>", "floors"),
               ("- vrcs_: unordered_map<uint32_t, Vrc>", "vrcs"),
               ("- tape_circle_radius_: double", "rotation_circle_tape_r..")]
    pecos = ["5675_pecos_combined", YAML_MD5[:8] + "...", "0.1524 x 0.0762", "TRAY .. XL (5)",
             "28 nodes", "4 types", "37 edges", "none", "[21, 7]", "default {0, z 0}", "none", "default"]
    methods = ["+ GetNodeById(id), GetNodeIdsOfType(type)", "+ GetResourceWindow(i), GetBufferedResourceWindow(i)",
               "+ GetBayInboundHeading(bay_id): Wrap(...)", "+ GetBayPrioritization(), GetVrcForNodeId(id)",
               "+ GetGarageLayout(): GarageLayoutMsg", "free: GetInboundHeading(node), not wrapped"]
    attrs = [""] + [m for m, _ in members]
    bw = 690
    L = uml_class(d, bx, 22, "Layout", accent=LAY, attrs=attrs, methods=methods, w=bw, size=11.5)
    lhm = 11.5 * 1.55
    head_h = S.h + 20
    row0 = 22 + head_h + 8
    kx, vx = bx + 345, bx + 545
    d.text(bx + 12, row0 + lhm / 2, "member", size=10, family="mono", fill=T.faint)
    d.text(kx, row0 + lhm / 2, "from YAML key", size=10, family="mono", fill=T.faint)
    d.text(vx, row0 + lhm / 2, "Pecos", size=10, family="mono", fill=T.faint)
    for i, ((_, key), val) in enumerate(zip(members, pecos), 1):
        cy = row0 + i * lhm + lhm / 2
        d.text(kx, cy, key, size=10, family="mono", fill=T.muted)
        d.text(vx, cy, val, size=10, family="mono", fill=T.green if val not in ("none", "default") else T.faint)

    # ---------------- under it: the file and how it is found ----------------
    ay = L.y1 + 70
    ax, aw = 0, 318
    d.text(ax, ay, "1  The file", size=13.5, weight=600, fill=T.fg)
    fb = lines_box(d, ax, ay + 18, ["sources/5675_pecos_combined.yaml",
                                    "name: 5675_pecos_combined",
                                    f"md5 {YAML_MD5[:16]}",
                                    f"    {YAML_MD5[16:]}",
                                    "352 lines: buffer, 4 parking_windows,",
                                    "28 nodes, 37 edges; no floors, vrcs",
                                    "or tape radius -> parser defaults"], LAY, size=10.5, w=aw, title="YAML file")
    connect(d, [(ax + aw / 2, fb.y0), (ax + aw / 2, L.y1)], kind="flow", color=LAY, size=9, sw=1.8)
    label_pill(d, ax + aw / 2 + 30, (fb.y0 + L.y1) / 2 - 8, "parse", color=LAY, size=10.5)
    lx = ax + aw + 54
    lw = bw - aw - 54
    d.text(lx, ay, "2  How it is found", size=13.5, weight=600, fill=T.fg)
    steps_ = [("ROS parameter (SchedulerComponent)", ["node->Param<std::string>(\"layout\")"]),
              ("volley::GetLayoutPathByName(name)", ["-> site_config::GetLayoutPathByName", "   (installed site configuration)"]),
              ("Layout(path)", ["YAML::LoadFile(path); md5sum_ = GetMD5Sum(path)"])]
    yy = ay + 18
    lb = None
    for i, (t, ls) in enumerate(steps_):
        b = lines_box(d, lx, yy, ls, LAY, size=10.5, w=lw, title=t, fill=T.card)
        if lb is not None:
            connect(d, [(lx + lw / 2, lb.y1), (lx + lw / 2, b.y0)], kind="flow", color=T.faint, size=8)
        lb = b
        yy = b.y1 + 18
    connect(d, [(lx + lw - 20, lb.y0), (lx + lw - 20, L.y1)], kind="flow", color=T.faint, size=8)
    note(d, ax, max(yy, fb.y1 + 18), bw, "GetLayoutByName(name) does both steps and returns a shared_ptr<const Layout>. "
                                         "Tests and the collision tools call GetLayoutPathByName with a constant name. "
                                         "The second constructor, Layout(YAML::Node), leaves md5sum_ empty.", size=11)

    # ---------------- column C: derived structures ----------------
    cx = bx + bw + 380
    d.text(cx, 0, "4  Built from it at start-up", size=13.5, weight=600, fill=T.fg)
    pgb = uml_class(d, cx, 22, "PoseGraph", accent=PG, compact=True, size=11.5, w=430,
                    attrs=["- poses_: vector<GaragePoseMsg>        // 60",
                           "- pose_indices_: map<GaragePose, int>",
                           "- pose_neighbors_: vector<int>  // 8 slots x 60",
                           "    FORWARD RIGHT BACK LEFT ROT_RIGHT ROT_LEFT",
                           "    VRC_UP VRC_DOWN; 164 of 480 filled",
                           "- overlapping_sized_poses_  // no caller reads it"])
    ggb = uml_class(d, cx, pgb.y1 + 84, "GarageGraph", accent=GG, compact=True, size=11.5, w=430,
                    attrs=["- base_graph_: vertex = one pose (60)",
                           "    edge = Transition {type, length} (164)",
                           "    LOCOMOTE / STRAFE: metres",
                           "    ROTATION: radians;  VRC_TRANSITION: |dz|",
                           "- pose_to_vertex_: map<GaragePose, Vertex>",
                           "- node_retrieval_heading_  // set by scheduler"])
    ctb = uml_class(d, cx, ggb.y1 + 84, "CollisionTable", accent=CT, compact=True, size=11.5, w=430,
                    attrs=["- entity table (footprints):",
                           "    AGV, TRAY, BAY_ODP, TRAY_LEGS,",
                           "    PAYLOAD + window index (5 sizes)",
                           "- ppmap_: [entity][pose][entity] -> poses",
                           "    pose x pose and pose x edge conflicts",
                           "- layout_id_ = hash(name_)",
                           "- cache_file_path_:",
                           "    ~/.cache/volley/<name>_collision_table_<md5>.json"])
    # vertical PG -> GG -> CT
    connect(d, [(cx + 215, pgb.y1), (cx + 215, ggb.y0)], kind="flow", color=PG, size=9, sw=1.8)
    lines_box(d, cx + 228, pgb.y1 + 18, ["poses -> vertices", "filled slots -> edges"], PG, size=10.5)
    connect(d, [(cx + 215, ggb.y1), (cx + 215, ctb.y0)], kind="flow", color=GG, size=9, sw=1.8)
    lines_box(d, cx + 228, ggb.y1 + 18, ["every vertex and edge, per", "footprint pair: polygon test"], GG, size=10.5)
    d.text(cx, ctb.y1 + 20, "Built once per layout; LoadTable() reads the cache file when it exists,",
           size=11, fill=T.muted)
    d.text(cx, ctb.y1 + 36, "BuildTable() + SaveTable() otherwise. Any edit to the file, a comment",
           size=11, fill=T.muted)
    d.text(cx, ctb.y1 + 52, "included, changes md5 and so forces a rebuild.", size=11, fill=T.muted)

    # Layout -> each derived structure, with the fields that flow
    gx0, gx1 = L.x1, cx
    flows = [(pgb, PG, ["headings -> poses: h and Wrap(h + 180)",
                        "rotation_allowed -> ROT_LEFT / ROT_RIGHT",
                        "graph_ + x, y -> FORWARD BACK LEFT RIGHT",
                        "  (bearing relative to the heading)",
                        "disallowed_edge_orientations_ -> skip",
                        "vrcs_ -> VRC_UP / VRC_DOWN",
                        "max_resource_size + buffered windows",
                        "  -> sized-pose overlaps"]),
             (ggb, GG, ["x, y + heading -> LOCOMOTE / STRAFE",
                        "  and length in metres",
                        "floors_ z -> VRC_TRANSITION length",
                        "vrcs_ -> re-mark VRC edges, audit"]),
             (ctb, CT, ["resource_windows_ (unbuffered)",
                        "  -> one PAYLOAD footprint per window",
                        "node type Bay -> BAY_ODP only at bays",
                        "floor, vrcs_ -> cross-floor filter",
                        "name_ + md5sum_ -> cache file name"])]
    for box, col, labels in flows:
        y = box.y0 + 30
        ys = min(y, L.y1 - 30)
        if ys == y:
            connect(d, [(gx0, y), (gx1, y)], kind="flow", color=col, size=9, sw=1.8)
        else:
            connect(d, [(gx0, ys), (gx1 - 30, ys), (gx1 - 30, y), (gx1, y)], kind="flow", color=col, size=9,
                    sw=1.8)
        lines_box(d, gx0 + 22, ys + 12, labels, col, size=10.5, fill=T.bg)

    # ---------------- column D: consumers, fed by three buses ----------------
    busL, busG, busC = cx + 430 + 40, cx + 430 + 70, cx + 430 + 100
    dx0 = cx + 430 + 150
    dw = 600
    d.text(dx0, 0, "5  Readers", size=13.5, weight=600, fill=T.fg)
    TAG = {"L": ("Layout", LAY), "G": ("GarageGraph", GG), "C": ("CollisionTable", CT)}
    cards = [
        ("Scheduler: task planning", "scheduler.cpp", [
            ("L", "bay_prioritization_: PlanRetrieveJob walks it in reverse (B7"),
            ("", "  first), ComputeBayRebalancingActions, InitRetrievalHeadings"),
            ("L", "headings[0] + faces_reciprocal: bay and charger inbound heading"),
            ("L", "node type AgvCharge: charger search in PlanAgvChargeJob"),
            ("L", "max_resource_size: bay fit (window length, width, height)"),
            ("G", "node_retrieval_heading_: written by InitRetrievalHeadings,"),
            ("", "  read by UseRetrievalHeading for park destinations"),
            ("C", "GetStaticFilter, open-space and blocking-tray searches"),
            ("L", "md5sum_ -> VersionInfo.layout_md5sum; name_ -> 576_eccles hack")]),
        ("CHUGG / SIPP: motion planning", "motion_planner, cost_functions", [
            ("C", "pose and edge conflicts -> safe intervals per pose"),
            ("G", "Transition type + length -> edge duration (cost model speed)"),
            ("L", "max_resource_size_index, AgvCharge type -> GetTraversableEdges"),
            ("L", "md5sum_: GetStaticFilter throws if graph and table differ"),
            ("L", "floors_ z, vrcs_ -> VRC travel time, run coalescing")]),
        ("Action graph: InsertVrcActionsIntoDag", "scheduler utils.cpp", [
            ("L", "vrcs_ + node floor -> VRC commands around AGV moves that"),
            ("", "  enter or leave a VRC (none in Pecos)")]),
        ("GarageSafetyChecker", "common_ros", [
            ("C", "blockers of a pose or edge before an action is applied"),
            ("L", "bay inbound heading -> ODP pose; vrcs_ -> BLift gating")]),
        ("Tape layout: ComputeTapeSegments", "tape_layout.cpp (callers: tests only here)", [
            ("L", "x, y and graph_ -> tape lines; headings -> extension length"),
            ("L", "rotation_allowed + tape_circle_radius_ -> tape circles")]),
        ("GetGarageLayout() -> GarageLayoutMsg", "layout.cpp (server and clients not in sources)", [
            ("L", "name_, nodes_, buffer, resource_windows_"),
            ("L", "graph_ edges as vertex INDICES, not node ids (8-31 -> {7, 26})"),
            ("", "  not sent: floors_, vrcs_, DEOs, bay prioritization")]),
    ]
    yy = 22
    taps = {"L": [], "G": [], "C": []}
    lh = 11 * 1.55
    for title, where, rows in cards:
        h = 16 + 22 + 10 + len(rows) * lh + 10
        d.rect(dx0, yy, dw, h, rx=10, fill=T.card, stroke=T.border, sw=1.3)
        d.text(dx0 + 14, yy + 18, title, size=13, weight=600, fill=T.fg)
        d.text(dx0 + dw - 14, yy + 18, where, size=10.5, family="mono", fill=T.faint, anchor="end")
        ry = yy + 44
        seen = set()
        for tag, s in rows:
            cy = ry + lh / 2
            if tag:
                name, col = TAG[tag]
                chip(d, dx0 + 12, cy, {"L": "L", "G": "GG", "C": "CT"}[tag], col, size=9.5)
                if tag not in seen:
                    taps[tag].append(cy)
                    seen.add(tag)
            d.text(dx0 + 52, cy, s, size=11, family="mono", fill=T.fg2)
            ry += lh
        yy += h + 16
    dy1 = yy - 16
    # buses
    top_y = -18
    connect(d, [(L.x0 + 300, L.y0), (L.x0 + 300, top_y), (busL, top_y), (busL, max(taps["L"]))], kind="line",
            color=LAY, sw=2, radius=10)
    connect(d, [(ggb.x1, ggb.y0 + 30), (busG, ggb.y0 + 30), (busG, max(taps["G"] + [ggb.y0 + 30]))],
            kind="line", color=GG, sw=2, radius=10)
    connect(d, [(ctb.x1, ctb.y0 + 30), (busC, ctb.y0 + 30), (busC, max(taps["C"]))], kind="line", color=CT, sw=2,
            radius=10)
    d.circle(L.x0 + 300, L.y0, 4, fill=LAY, layer="over")
    d.circle(ggb.x1, ggb.y0 + 30, 4, fill=GG, layer="over")
    d.circle(ctb.x1, ctb.y0 + 30, 4, fill=CT, layer="over")
    label_pill(d, (cx + busL) / 2 - 40, top_y, "Layout (shared_ptr), also via gg.GetLayout()", color=LAY, size=10.5)
    for tag, bus in (("L", busL), ("G", busG), ("C", busC)):
        col = TAG[tag][1]
        for ty in taps[tag]:
            d.circle(bus, ty, 3.5, fill=col, layer="over")
            connect(d, [(bus, ty), (dx0, ty)], kind="flow", color=col, size=7, sw=1.4)
    d.text(cx, max(ctb.y1 + 80, 0), "PoseGraph has no reader of its own: the scheduler keeps pg_ only to build gg_,",
           size=11, fill=T.muted)
    d.text(cx, ctb.y1 + 96, "and every reader reaches the Layout through gg_.GetLayout() or layout_.", size=11,
           fill=T.muted)

    frame(d, title="Who reads the layout file",
          subtitle="The layout YAML is looked up by name, parsed once into a Layout, and expanded into three derived "
                   "structures. Arrow labels name the fields that flow; in each reader, L, GG and CT mark what it reads "
                   "from the Layout, the GarageGraph and the CollisionTable.",
          badge_key="as-built",
          legend=[("box", LAY, "Layout and its fields"), ("box", PG, "PoseGraph"), ("box", GG, "GarageGraph"),
                  ("box", CT, "CollisionTable"), ("arrow", T.faint, "built from / read by")],
          footnote="Sources: layout.hpp, layout.cpp (Layout(YAML::Node) L82-344, GetGarageLayout), pose_graph.cpp, "
                   "garage_graph.cpp, collision_geometry.cpp (CollisionTable ctor, BuildEntityTable, GetCacheFilePath), "
                   "scheduler_component.cpp, scheduler.cpp, static_graph_filtering.cpp, safe_interval_path_planning.cpp, "
                   "garage_safety_checker.cpp, tape_layout.cpp. md5 is computed here from the snapshot copy of the file; "
                   "GetMD5Sum itself is not in the snapshots. Pecos counts: 60 poses, 164 directed GarageGraph edges "
                   "(148 translations, 16 rotations).")
    return d


# ======================================================================================
# shared map pieces for 106-108
# ======================================================================================

def faint_nodes(m: Map):
    for n in NODES.values():
        if m.visible(n, 0.2):
            x, y = m.P(n.id)
            m.d.circle(x, y, 3, fill=T.border, layer="over")


def bay_box(m: Map, nid, *, label=True, bright=False):
    d = m.d
    x, y = m.P(nid)
    w, h = STALL_L * m.s - 3, (STALL_W + 0.9) * m.s
    d.rect(x - w / 2, y - h / 2, w, h, rx=8, fill=T.tint(C_BAY, 0.12 if not bright else 0.2, T.bg_deep),
           stroke=C_BAY, sw=1.6 if not bright else 2.4, layer="under")
    d.line(x + w / 2, y - h / 2 + 6, x + w / 2, y + h / 2 - 6, stroke=C_BAY, sw=4.5, cap="round", layer="under")
    d.circle(x, y, 3.2, fill=C_BAY, layer="over")
    if label:
        d.text(x - w / 2 + 9, y - h / 2 + 12, lbl(nid), size=12, family="mono", weight=700, fill=C_BAY)
    return BBox(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def charger(m: Map, nid, *, label=True, bright=False):
    d = m.d
    x, y = m.P(nid)
    r = max(9, 0.36 * m.s)
    d.circle(x, y, r, fill=T.tint(C_CHG, 0.25 if not bright else 0.45, T.bg_deep), stroke=C_CHG,
             sw=1.6 if not bright else 2.6, layer="over")
    bolt = [(x + 0.12 * r, y - 0.62 * r), (x - 0.38 * r, y + 0.1 * r), (x - 0.02 * r, y + 0.1 * r),
            (x - 0.14 * r, y + 0.62 * r), (x + 0.38 * r, y - 0.12 * r), (x + 0.02 * r, y - 0.12 * r)]
    d.polygon(bolt, fill=C_CHG, layer="over", join="round")
    if label:
        d.text(x + r + 5, y + 2, lbl(nid), size=11, family="mono", weight=600, fill=C_CHG, halo=T.bg_deep,
               halo_w=3.5)
    return r


def stall(m: Map, nid, *, color=C_PARK, sw=2.2, buffered=False, dash=None, fill=True):
    d = m.d
    x, y = m.P(nid)
    Lm, Wm = (STALL_L + BUF_L, STALL_W + BUF_W) if buffered else (STALL_L, STALL_W)
    w, h = Lm * m.s, Wm * m.s
    d.rect(x - w / 2, y - h / 2, w, h, rx=3 if not buffered else 2,
           fill=T.tint(color, 0.14, T.bg_deep) if fill else "none", stroke=color, sw=sw, dash=dash, layer="main")
    return BBox(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def pose_fan(m: Map, nid, headings, color, *, L=30, labels=True, lab_off=12, size=10.5):
    x, y = m.P(nid)
    for h in headings:
        tip = head_arrow(m.d, x, y, h, color, L=L, start=5)
        if labels:
            fx, fy = hvec(h)
            m.d.text(tip[0] + fx * lab_off + (0 if abs(fx) < 0.5 else 0), tip[1] + fy * lab_off, str(h), size=size,
                     family="mono", weight=700, fill=color, anchor="middle", halo=T.bg_deep, halo_w=3)


def dim_line(d, p0, p1, text, color, *, off=(0, 0), text_off=(0, -10), size=10.5, anchor="middle"):
    (x0, y0), (x1, y1) = p0, p1
    x0, y0, x1, y1 = x0 + off[0], y0 + off[1], x1 + off[0], y1 + off[1]
    d.line(x0, y0, x1, y1, stroke=color, sw=1.3, layer="top")
    d.arrowhead((x0, y0), (x1, y1), kind="filled", color=color, size=7, layer="top")
    d.arrowhead((x1, y1), (x0, y0), kind="filled", color=color, size=7, layer="top")
    d.text((x0 + x1) / 2 + text_off[0], (y0 + y1) / 2 + text_off[1], text, size=size, family="mono", fill=color,
           anchor=anchor, halo=T.bg_deep, halo_w=3.5, layer="top")


def step_card(d, x, y, w, k, title, lines, color, *, h=None, size=11):
    """Per-step text card (shown only during step k)."""
    with d.only(k):
        lh = size * 1.5
        hh = h or (40 + len(lines) * lh)
        d.rect(x, y, w, hh, rx=10, fill=T.card, stroke=T.tint(color, 0.7, T.bg), sw=1.3)
        d.text(x + 14, y + 18, title, size=12.5, weight=600, fill=color)
        for i, s in enumerate(lines):
            d.text(x + 14, y + 40 + i * lh, s, size=size, family="mono", fill=T.fg2)


# ======================================================================================
# 106 — the YAML and the map it describes
# ======================================================================================

@figure("106_layout_yaml_to_map", "The Pecos YAML and the map it describes (animated)", DOC)
def layout_yaml_to_map():
    d = Doc("106_layout_yaml_to_map", "The Pecos YAML, line by line, and the map it describes",
            "Animated: the layout file on the left with the lines of each step highlighted, the Pecos floor on the "
            "right with the elements those lines create: windows and buffer, a parking node, a rotation waypoint, a "
            "bay, a charger, the edges and the section comments.")
    E = ("...",)
    items = [1, 2, 3, 4, 5, 6, 7, 8, ("...", "  # STANDARD 5.182, LARGE 5.486   (lines 9-14)"), 15, 16, 17, 19, 20,
             ("...", "  # nodes 1-7 and 31   (lines 21-92)"), *range(93, 103),
             ("...", "  # nodes 9, 10, 11   (lines 103-129)"), 131, ("...", "  # node 13   (lines 132-140)"),
             *range(141, 150), ("...", "  # nodes 15-18   (lines 150-185)"), *range(186, 195),
             ("...", "  # node 20   (lines 195-203)"), *range(204, 213), ("...", "  # node 41   (lines 213-221)"), 222,
             ("...", "  # rest of 22, nodes 23-27   (lines 223-276)"), 278, *range(279, 283),
             ("...", "  # 12 more   (lines 283-306)"), *range(307, 313), ("...", "  # (lines 313-326)"),
             327, 328, 329, 330, ("...", "  # 9 more; 37 edges in all   (lines 331-352)")]
    yp = YamlPanel(d, 0, 22, 545, items, size=10.5, lh=1.4, title="sources/5675_pecos_combined.yaml (abridged)")
    d.text(0, 0, "The file", size=13.5, weight=600, fill=T.fg)
    mx = yp.bb.x1 + 70
    s = 44
    d.text(mx - 40, 0, "What it describes: facility.Map of the same file (x, y in metres)", size=13.5, weight=600,
           fill=T.fg)
    m = Map(d, mx, 40, s, FULL_X, FULL_Y)

    caps = [
        "Top level. The parser reads name, parking_window_buffer, parking_windows, nodes and edges here; "
        "floors, vrcs and rotation_circle_tape_radius are absent, so Pecos gets one floor {id 0, z 0} and the "
        "default tape radius. Unknown keys would be ignored silently. Grey dots: the 28 nodes, not yet explained.",
        "parking_windows and the buffer set the stall size. XL is 5.791 m along the facing (body +y, world x at "
        "heading 90) by 2.21 m. The parser appends TRAY and sorts by area: TRAY 0, COMPACT 1, STANDARD 2, LARGE 3, "
        "XL 4. The buffer (+0.1524, +0.0762) is added only for the PoseGraph's sized-pose overlaps; with it, P19's "
        "footprint reaches 0.15 m into P20's.",
        "One Parking node: id 19 at (37.1856, 19.4523), XL, headings [90]. GetAllowedHeadings adds the reciprocal, "
        "so P19 has two poses: 90 (facing west) and -90 (facing east), each with the same XL rectangle. The other "
        "nine Parking nodes are the same shape.",
        "A rotation waypoint: node 8, headings [0, 90], rotation_allowed true. Four poses (-90, 0, 90, 180) and, "
        "because it may rotate, ROT_LEFT / ROT_RIGHT neighbours and a circular footprint of radius "
        "hypot(5.9434, 2.2862) / 2 = 3.18 m instead of a rectangle. W22 is the only other node like it.",
        "A Bay: node 21, headings [90], faces_reciprocal true. Inbound heading = Wrap(90 + 180) = -90: an AGV in "
        "the bay faces east, through the door on the garage side towards W41. No prioritization_value, so it "
        "counts as 0 and the bay order is [21, 7] (ties go to the higher id).",
        "An AgvCharge node: id 14, 0.6096 m south of P15, max_resource_size TRAY (index 0, so no payload may "
        "stand there), faces_reciprocal true. Its charging pose is (14, -90): facing east. C16 is the same; C10 "
        "has faces_reciprocal false, so it charges at 90.",
        "The edges list: 37 undirected edges (src/dst order is discarded). They draw the graph: three columns of "
        "waypoints and stalls, the bay spurs W31 and W41, and the 0.61 m charger spurs.",
        "The comments. # 5675_pecos_sandbox_eng and # 5675_pecos_sandbox_qa split the nodes into two sandboxes, "
        "joined only by edge 8-13 (4.391 m); # Offset \"origin\" on node 22 marks the measurement datum. The parser "
        "throws comments away, but they change the md5 and so force a collision-table rebuild.",
        "Everything: 28 nodes (13 waypoints, 10 parking, 3 chargers, 2 bays), 37 edges, 4 windows plus TRAY, two "
        "sandboxes. This is the map every other Pecos figure draws.",
    ]
    ks = [d.step(c) for c in caps]

    # -------- YAML highlights --------
    yp.band([1, 2, 5, 19, 278], LAY, 0)
    yp.band([2, 3, 4, 5, 6, 7, 8, 15, 16, 17], C_PARK, 1)
    yp.band(list(range(186, 195)), C_PARK, 2)
    yp.band(list(range(93, 103)), T.fg2, 3)
    yp.band(list(range(204, 213)), C_BAY, 4)
    yp.band(list(range(141, 150)), C_CHG, 5)
    yp.band([278, 279, 280, 281, 282, 307, 308, 309, 310, 311, 312, 327, 328, 329, 330], T.fg2, 6)
    yp.band([20, 131, 222], T.green, 7)

    # -------- map --------
    m.floor()
    m.clip()
    with d.at(7):
        m.zones()
    with d.at(6):
        m.corridors()
    with d.at(2, 7):
        m.stalls(labels=False, dim=True)
    with d.at(8):
        m.stalls(labels=True)
    with d.at(6, 7):
        m.bays(labels=False)
    with d.at(8):
        m.bays(labels=True)
    with d.at(6):
        m.edges()
    with d.at(0, 5):
        faint_nodes(m)
    with d.at(6, 7):
        m.nodes(labels=False)
    with d.at(8):
        m.nodes(labels=True)
    m.unclip()

    # step 1: windows -> stall size, on P19
    with d.only(1):
        b = stall(m, 19, color=C_PARK, sw=2)
        bb = stall(m, 19, color=T.amber, sw=1.4, buffered=True, dash="5 3", fill=False)
        for nb in (20, 15, 23):
            stall(m, nb, color=T.border, sw=1, fill=False, dash="3 3")
        dim_line(d, (b.x0, b.y0), (b.x1, b.y0), "XL length_m 5.791", C_PARK, off=(0, -16), text_off=(0, -12))
        dim_line(d, (b.x1, b.y0), (b.x1, b.y1), "width_m 2.21", C_PARK, off=(16, 0), text_off=(8, 0),
                 anchor="start")
        d.text(bb.x0, bb.y1 + 18, "buffered: 5.9434 x 2.2862 (dashed)", size=10.5, family="mono", fill=T.amber,
               halo=T.bg_deep, halo_w=3)
        d.text(bb.x0, bb.y1 + 34, "neighbour stalls 5.7912 m (x) and 2.286 m (y) apart", size=10.5,
               family="mono", fill=T.muted, halo=T.bg_deep, halo_w=3)
        x, y = m.P(19)
        d.circle(x, y, 3.5, fill=C_PARK, layer="over")
    # step 2: P19
    with d.only(2):
        stall(m, 19, color=C_PARK, sw=2.4)
        x, y = m.P(19)
        d.circle(x, y, 4.5, fill=C_PARK, layer="over")
        pose_fan(m, 19, [90, -90], PG, L=52)
        label_pill(d, x, y - STALL_W * s / 2 - 14, "P19 (37.1856, 19.4523)", color=C_PARK, bg=T.bg_deep,
                   border=C_PARK)
    # step 3: W8
    with d.only(3):
        x, y = m.P(8)
        r = math.hypot(STALL_L + BUF_L, STALL_W + BUF_W) / 2 * s
        d.circle(x, y, r, fill=T.tint(T.fg2, 0.05, T.bg_deep), stroke=T.fg2, sw=1.4, dash="6 4", layer="main")
        d.circle(x, y, 6, fill=T.fg, layer="over")
        pose_fan(m, 8, [-90, 0, 90, 180], PG, L=50)
        label_pill(d, x + 6, y + r + 14, "W8: circular footprint r = 3.18 m", color=T.fg2, bg=T.bg_deep,
                   border=T.fg2)
        d.path(f"M{x + 26:.1f} {y - 26:.1f} A 37 37 0 0 0 {x - 26:.1f} {y - 26:.1f}", stroke=T.pink, sw=1.8,
               layer="top")
        d.arrowhead((x - 26, y - 26), (x - 12, y - 35), kind="filled", color=T.pink, size=8)
        d.text(x + 34, y - 36, "ROT", size=10, family="mono", weight=700, fill=T.pink, halo=T.bg_deep, halo_w=3)
    # step 4: B21
    with d.at(4, 5):
        bay_box(m, 21, bright=True)
    with d.only(4):
        x, y = m.P(21)
        head_arrow(d, x, y, -90, PG, L=60, start=5)
        d.text(x + 8, y + 18, "inbound -90", size=11, family="mono", weight=700, fill=PG, halo=T.bg_deep, halo_w=3)
        bx_ = x + STALL_L * s / 2
        label_pill(d, bx_ - 6, y + (STALL_W + 0.9) * s / 2 + 16, "door on the garage side", color=C_BAY,
                   bg=T.bg_deep, anchor="end")
        x41, y41 = m.P(41)
        d.circle(x41, y41, 4.5, fill=C_WP, layer="over")
        d.text(x41, y41 - 12, "W41", size=10.5, family="mono", fill=T.muted, anchor="middle", halo=T.bg_deep,
               halo_w=3)
    # step 5: C14
    with d.only(5):
        x, y = m.P(14)
        r = charger(m, 14, label=False, bright=True)
        head_arrow(d, x, y, -90, PG, L=50, start=r + 2)
        d.text(x + 56, y, "(14, -90)", size=11, family="mono", weight=700, fill=PG, halo=T.bg_deep, halo_w=3)
        stall(m, 15, color=C_PARK, sw=1.2, fill=False)
        px, py = m.P(15)
        d.circle(px, py, 3.5, fill=C_PARK, layer="over")
        dim_line(d, (px - 30, py), (px - 30, y), "0.6096 m", C_CHG, text_off=(-6, 0), anchor="end")
        label_pill(d, x, y + r + 16, "C14: max_resource_size TRAY", color=C_CHG, bg=T.bg_deep, border=C_CHG)
    # step 6: edges
    with d.only(6):
        label_pill(d, m.X(33.9), m.Y(15.0), "37 undirected edges", color=T.fg2, bg=T.bg_deep, border=T.fg2)
    # step 7: sandboxes, datum, the joining edge
    with d.at(7, 8):
        x, y = m.P(22)
        d.circle(x, y, 11, fill="none", stroke=T.green, sw=1.8, layer="top")
        d.line(x - 17, y, x + 17, y, stroke=T.green, sw=1.4, layer="top")
        d.line(x, y - 17, x, y + 17, stroke=T.green, sw=1.4, layer="top")
    with d.only(7):
        x, y = m.P(22)
        label_pill(d, x + 20, y - 26, "# Offset \"origin\" (node 22)", color=T.green, bg=T.bg_deep, border=T.green,
                   anchor="start")
        (x8, y8), (x13, y13) = m.P(8), m.P(13)
        d.line(x8, y8, x13, y13, stroke=T.amber, sw=4, layer="over")
        label_pill(d, x8 + 14, m.Y(14.4), "edge 8-13: 4.391 m joins the sandboxes", color=T.amber,
                   bg=T.bg_deep, border=T.amber, anchor="start")

    # -------- "what the parser builds" card under the map --------
    cy0 = m.box.y1 + 48
    cw = m.box.w
    d.text(mx, cy0 - 14, "What Layout(YAML::Node) builds from the highlighted lines", size=13.5, weight=600,
           fill=T.fg)
    cards = [
        ("Keys read (layout.cpp L82-344)", ["name_ = \"5675_pecos_combined\"",
                                            "floors_ = [{id 0, z 0}]     // no floors key",
                                            "vrcs_ = {}   tape_circle_radius_ = kDefaultTapeCircleRadius",
                                            "nodes_ 28, sorted by id; graph_ from 37 edges"], LAY),
        ("Windows", ["parking_window_buffer_ = {\"buffer\", 0.1524, 0.0762}",
                     "resource_windows_ (by area): 0 TRAY (kTray*), 1 COMPACT 4.2672,",
                     "  2 STANDARD 5.182, 3 LARGE 5.486, 4 XL 5.791   (all 2.21 wide)",
                     "XL buffered 5.9434 x 2.2862: PoseGraph overlaps only, not CollisionTable"], C_PARK),
        ("nodes_[17]  (node 19)", ["GarageNodeMsg {id 19, x 37.1856, y 19.4523, type TYPE_PARKING,",
                                   "  max_resource_size \"XL\", max_resource_size_index 4,",
                                   "  rotation_allowed false, headings [90], faces_reciprocal false}",
                                   "poses (19, -90), (19, 90)"], C_PARK),
        ("nodes_[7]  (node 8)", ["GarageNodeMsg {id 8, x 30.8823, y 12.7753, type TYPE_WAYPOINT,",
                                 "  max_resource_size_index 4, rotation_allowed true, headings [0, 90]}",
                                 "poses (8, -90), (8, 0), (8, 90), (8, 180)",
                                 "ROT_LEFT / ROT_RIGHT slots; footprint: circle, not rectangle"], T.fg2),
        ("nodes_[19]  (node 21)", ["GarageNodeMsg {id 21, type TYPE_BAY, headings [90],",
                                   "  faces_reciprocal true, insert_floor 0, system_floors [0]}",
                                   "bay_prioritization_ = [21, 7]   (both 0; higher id first)",
                                   "GetBayInboundHeading(21) = Wrap(90 + 180) = -90"], C_BAY),
        ("nodes_[12]  (node 14)", ["GarageNodeMsg {id 14, x 37.1856, y 16.5567, type TYPE_AGV_CHARGE,",
                                   "  max_resource_size \"TRAY\", index 0, headings [90],",
                                   "  faces_reciprocal true}",
                                   "GetInboundHeading = 270 (not wrapped); charge pose (14, -90)"], C_CHG),
        ("graph_", ["for each edge: a = min(src, dst), b = max(src, dst)",
                    "  boost::add_edge(node_id_to_index_[a], node_id_to_index_[b])",
                    "no disallowed_edge_orientation in Pecos",
                    "PoseGraph turns them into 148 translation pose edges"], T.fg2),
        ("Comments", ["dropped by YAML::LoadFile: no field holds the sandbox",
                      "names or the datum; facility.py re-reads them from the text",
                      "md5sum_ covers every byte, comments included",
                      "  -> new cache file ~/.cache/volley/..._<md5>.json"], T.green),
        ("Totals", ["28 nodes: 13 Waypoint, 10 Parking, 3 AgvCharge, 2 Bay",
                    "37 edges, 5 resource windows, 60 poses, 164 pose edges",
                    "2 rotation nodes (8, 22), 2 bays (7, 21), 3 chargers (10, 14, 16)",
                    "2 sandboxes joined by edge 8-13"], LAY)]
    for k, (t, ls, col) in enumerate(cards):
        step_card(d, mx, cy0, cw, k, t, ls, col, h=40 + 4 * 16.5 + 4)

    frame(d, title="The Pecos YAML and the map it describes",
          subtitle="Step through the file: each step highlights some lines on the left and draws what they create on "
                   "the right, with the C++ values the parser stores underneath. Positions, sizes and headings are "
                   "the file's own numbers.",
          badge_key="yaml",
          legend=[("box", C_PARK, "parking stall (XL window)"), ("dashbox", T.amber, "buffered window"),
                  ("box", C_BAY, "bay"), ("ring", C_CHG, "AGV charger"), ("dot", C_WP, "waypoint"),
                  ("arrow", PG, "pose heading (facing, body +y)"), ("dashbox", T.fg2, "rotation footprint")],
          footnote="Parser behaviour from layout.cpp (Layout(YAML::Node), L82-344), pose_utils.cpp (GetAllowedHeadings), "
                   "polygon_utils.cpp (CalcOverlappingSizedPoses) and collision_geometry.cpp (BuildEntityTable uses "
                   "the unbuffered window). Line numbers in the panel are the file's own.")
    return d


# ======================================================================================
# 107 — one node becomes poses and neighbour slots
# ======================================================================================
C_LOC, C_STR, C_ROT = T.green, T.amber, T.pink
SLOT_ORDER = ["FORWARD", "RIGHT", "BACK", "LEFT", "ROT_RIGHT", "ROT_LEFT", "VRC_UP", "VRC_DOWN"]
SLOT_KIND = {"FORWARD": ("STRAFE", "body +x"), "BACK": ("STRAFE", "body -x"), "LEFT": ("LOCOMOTE", "body +y"),
             "RIGHT": ("LOCOMOTE", "body -y"), "ROT_RIGHT": ("ROTATION", "clockwise"),
             "ROT_LEFT": ("ROTATION", "counter-cw"), "VRC_UP": ("VRC_TRANSITION", "floor up"),
             "VRC_DOWN": ("VRC_TRANSITION", "floor down")}
KIND_COL = {"STRAFE": C_STR, "LOCOMOTE": C_LOC, "ROTATION": C_ROT, "VRC_TRANSITION": T.violet}


def slot_arrow(m: Map, src, dst, name, *, frac=0.62, cut0=16, cut1=10, edge_xy=None, lab_dx=0, lab_dy=0):
    """Arrow from node src to node dst (or to an svg point edge_xy) labelled with the slot name and motion."""
    d = m.d
    kind = SLOT_KIND[name][0]
    col = KIND_COL[kind]
    x0, y0 = m.P(src)
    x1, y1 = edge_xy if edge_xy else m.P(dst)
    L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    a = (x0 + ux * cut0, y0 + uy * cut0)
    b = (x1 - ux * cut1, y1 - uy * cut1)
    d.line(a[0], a[1], b[0] - ux * 8, b[1] - uy * 8, stroke=T.bg_deep, sw=6.5, layer="over")
    d.line(a[0], a[1], b[0] - ux * 8, b[1] - uy * 8, stroke=col, sw=3, layer="over")
    d.arrowhead(b, a, kind="filled", color=col, size=12, layer="over")
    px, py = x0 + (x1 - x0) * frac + lab_dx, y0 + (y1 - y0) * frac + lab_dy
    label_pill(d, px, py, f"{name} · {kind}", color=col, bg=T.bg_deep, border=col, size=10.5, layer="top")


def rot_arc(d, cx, cy, r, h0, h1, col, label, *, lab_r=None, lab_anchor="middle"):
    """Arc around (cx, cy) from facing h0 to facing h1 (shortest way), arrowhead at h1."""
    dh = ((h1 - h0 + 180) % 360) - 180
    n = 24
    pts = []
    for i in range(n + 1):
        hx, hy = hvec(h0 + dh * i / n)
        pts.append((cx + hx * r, cy + hy * r))
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts[:-2])
    d.path(path, stroke=T.bg_deep, sw=6, layer="over")
    d.path(path, stroke=col, sw=2.6, layer="over")
    d.arrowhead(pts[-1], pts[-4], kind="filled", color=col, size=11, layer="over")
    hx, hy = hvec(h0 + dh / 2)
    lr = lab_r or r + 18
    label_pill(d, cx + hx * lr, cy + hy * lr, label, color=col, bg=T.bg_deep, border=col, size=10.5, layer="top",
               anchor=lab_anchor)


def body_axes(d, x, y, h, *, L=58, label=True, col_y=C_LOC, col_x=C_STR):
    """Body +y (facing, locomote) and body +x (strafe) of an AGV at heading h."""
    fy = hvec(h)                # body +y in svg space
    fx = hvec(h - 90)           # body +x = facing rotated clockwise by 90 deg
    for (ux, uy), col, txt in ((fy, col_y, "+y"), (fx, col_x, "+x")):
        tip = (x + ux * L, y + uy * L)
        d.line(x, y, tip[0] - ux * 7, tip[1] - uy * 7, stroke=col, sw=2.2, layer="top", dash="5 3")
        d.arrowhead(tip, (x, y), kind="filled", color=col, size=9, layer="top")
        if label:
            d.text(tip[0] + ux * 14, tip[1] + uy * 14, txt, size=11, family="mono", weight=700, fill=col,
                   anchor="middle", halo=T.bg_deep, halo_w=3)


@figure("107_node_to_poses", "How one node becomes poses and neighbour slots (animated)", DOC)
def node_to_poses():
    d = Doc("107_node_to_poses", "How one node becomes poses and neighbour slots",
            "Animated: node 8 (headings [0, 90], rotation allowed) and node 9 (heading [90]) from the Pecos YAML, "
            "their poses after GetAllowedHeadings, an AGV at each pose, and the eight PoseNeighbor slots that "
            "pose_graph.cpp fills for them.")
    s = 70
    m = Map(d, 0, 40, s, (26.6, 40.6), (9.3, 18.3))
    d.text(0, 0, "Around W8 and W9 (Pecos, metres)", size=13.5, weight=600, fill=T.fg)
    m.floor(tick=2)
    m.clip()
    m.corridors()
    m.stalls(labels=True, dim=True)
    m.bays(labels=True)
    m.edges()
    m.nodes(labels=True)
    m.unclip()
    edge_r = (m.box.x1 - 2, m.P(9)[1])     # W11 is off the crop to the east

    caps = [
        "Two YAML entries. Node 8 at (30.8823, 12.7753) lists headings [0, 90] and rotation_allowed true; node 9, "
        "6.30 m to the east, lists [90] and may not rotate. Both are XL waypoints.",
        "GetAllowedHeadings (pose_utils.cpp) emits Wrap(h) and Wrap(h + 180) for every listed heading and sorts: "
        "node 8 gets four poses, -90, 0, 90, 180; node 9 gets two, -90 and 90. These are poses_[14..17] and "
        "poses_[18..19] of the 60 Pecos poses.",
        "What a heading means for the AGV. At (8, 90) the body +y axis, the AGV's driving (locomote) axis, points "
        "west: heading 90 = facing west. Body +x points north; moving along it is a strafe. GeometricPose.yaw is "
        "the same angle in radians.",
        "The eight slots of (8, 90). For each layout neighbour with the same heading, pose_graph.cpp measures the "
        "bearing relative to the heading: 0 is FORWARD (W13, north), 180 BACK (W4), +90 LEFT (W31, west), -90 RIGHT "
        "(W9). Rotation: the nearest clockwise heading is ROT_RIGHT (8, 0), the nearest counter-clockwise is "
        "ROT_LEFT (8, 180). No VRC, so VRC_UP and VRC_DOWN stay empty (-1).",
        "The same node at heading -90: the AGV faces east, so every name flips. FORWARD is now W4, BACK W13, LEFT "
        "W9 and RIGHT W31; ROT_LEFT is (8, 0) and ROT_RIGHT (8, 180). The neighbours are the same nodes, reached "
        "through different slots.",
        "(8, 0) and (8, 180) are stepping stones. No neighbour of node 8 has heading 0 or 180, so these poses get "
        "rotation slots only. They turn a 90 to -90 flip into two 90-degree steps; without heading 0 in the YAML, "
        "ROT_LEFT and ROT_RIGHT would both be one 180-degree spin.",
        "The names describe body x, not driving. FORWARD and BACK are travel along body +x and -x: GarageGraph "
        "types them STRAFE. LEFT and RIGHT are along body +y and -y: LOCOMOTE, the AGV's normal driving. Node 9 "
        "shows it: (9, 90) FORWARD is the 0.61 m strafe north onto charger C10, LEFT is the drive west to W8; it "
        "has no rotation slots.",
        "Summary for Pecos: 26 nodes with one heading give 2 poses each, nodes 8 and 22 give 4: 60 poses and 480 "
        "slots, of which 164 are filled (148 translations, 16 rotations, no VRC). GarageGraph turns each filled "
        "slot into one directed edge.",
    ]
    ks = [d.step(c) for c in caps]
    x8, y8 = m.P(8)
    x9, y9 = m.P(9)
    with d.only(0):
        for nid in (8, 9):
            x, y = m.P(nid)
            d.circle(x, y, 14, fill="none", stroke=LAY, sw=2.2, layer="top")
    with d.only(1):
        pose_fan(m, 8, [-90, 0, 90, 180], PG, L=48)
        pose_fan(m, 9, [-90, 90], PG, L=48)
    # AGVs
    with d.at(2, 3):
        m.agv(8, "AGV-1", heading=90, label_side="below")
    with d.only(2):
        body_axes(d, x8, y8, 90, L=92)
        label_pill(d, m.box.x0 + 12, y8 + 74, "body +y = locomote (driving) axis: west at heading 90",
                   color=C_LOC, bg=T.bg_deep, border=C_LOC, anchor="start")
        label_pill(d, x8 + 18, y8 - 112, "body +x = strafe axis: north at heading 90", color=C_STR, bg=T.bg_deep,
                   border=C_STR, anchor="start")
    with d.only(3):
        slot_arrow(m, 8, 13, "FORWARD", frac=0.55, cut0=40)
        slot_arrow(m, 8, 4, "BACK", frac=0.74, cut0=40)
        slot_arrow(m, 8, 31, "LEFT", frac=0.86, cut0=80, lab_dy=24)
        slot_arrow(m, 8, 9, "RIGHT", frac=0.5, cut0=80)
        rot_arc(d, x8, y8, 94, 90, 0, C_ROT, "ROT_RIGHT -> (8, 0)", lab_r=120, lab_anchor="end")
        rot_arc(d, x8, y8, 94, 90, 180, C_ROT, "ROT_LEFT -> (8, 180)", lab_r=124, lab_anchor="end")
    with d.only(4):
        m.agv(8, "AGV-1", heading=-90, label_side="below")
        slot_arrow(m, 8, 4, "FORWARD", frac=0.74, cut0=40)
        slot_arrow(m, 8, 13, "BACK", frac=0.55, cut0=40)
        slot_arrow(m, 8, 9, "LEFT", frac=0.5, cut0=80)
        slot_arrow(m, 8, 31, "RIGHT", frac=0.86, cut0=80, lab_dy=24)
        rot_arc(d, x8, y8, 94, -90, 0, C_ROT, "ROT_LEFT -> (8, 0)", lab_r=120, lab_anchor="start")
        rot_arc(d, x8, y8, 94, -90, -180, C_ROT, "ROT_RIGHT -> (8, 180)", lab_r=124, lab_anchor="start")
    with d.only(5):
        m.agv(8, "AGV-1", heading=0, label_side="right")
        rot_arc(d, x8, y8, 94, 0, 90, C_ROT, "ROT_LEFT -> (8, 90)", lab_r=124, lab_anchor="end")
        rot_arc(d, x8, y8, 94, 0, -90, C_ROT, "ROT_RIGHT -> (8, -90)", lab_r=124, lab_anchor="start")
        label_pill(d, x8, y8 + 128, "(8, 0): no FORWARD / BACK / LEFT / RIGHT", color=T.fg2, bg=T.bg_deep,
                   border=T.border)
    with d.only(6):
        d.circle(x9, y9, 13, fill="none", stroke=LAY, sw=2, layer="top")
        pose_fan(m, 9, [-90, 90], PG, L=40, labels=False)
        slot_arrow(m, 9, 10, "FORWARD", frac=1.0, cut0=14, cut1=22, lab_dx=-96, lab_dy=-34)
        slot_arrow(m, 9, 5, "BACK", frac=0.6, cut0=16)
        slot_arrow(m, 9, 8, "LEFT", frac=0.5, cut0=46, lab_dy=-22)
        slot_arrow(m, 9, 11, "RIGHT", frac=0.55, cut0=46, edge_xy=edge_r, cut1=2, lab_dy=22)
        label_pill(d, x9, y9 - 150, "(9, 90): heading [90] only, rotation_allowed false: no ROT slots",
                   color=T.fg2, bg=T.bg_deep, border=T.border)
        d.text(edge_r[0] - 8, edge_r[1] + 22, "to W11", size=10.5, family="mono", fill=T.muted, anchor="end",
               halo=T.bg_deep, halo_w=3)
    with d.at(7):
        m.agv(8, "AGV-1", heading=90, label_side="below")
        slot_arrow(m, 8, 13, "FORWARD", frac=0.55, cut0=40)
        slot_arrow(m, 8, 4, "BACK", frac=0.74, cut0=40)
        slot_arrow(m, 8, 31, "LEFT", frac=0.86, cut0=80, lab_dy=24)
        slot_arrow(m, 8, 9, "RIGHT", frac=0.5, cut0=80)
        rot_arc(d, x8, y8, 94, 90, 0, C_ROT, "ROT_RIGHT -> (8, 0)", lab_r=120, lab_anchor="end")
        rot_arc(d, x8, y8, 94, 90, 180, C_ROT, "ROT_LEFT -> (8, 180)", lab_r=124, lab_anchor="end")

    # ---------------- body axes at the four poses of node 8 ----------------
    by = m.box.y1 + 64
    with d.at(2):
        d.text(0, by, "Body axes at the four poses of node 8 (same convention as figure 78)", size=13.5,
               weight=600, fill=T.fg)
        mm = Map(d, 0, by + 20, 48, (0.0, m.box.w / 48), (0.0, 4.4))
        for i, (h, txt) in enumerate(((-90, "faces east"), (0, "faces north"), (90, "faces west"),
                                      (180, "faces south"))):
            cxm = (i + 0.5) * m.box.w / 48 / 4
            mm.agv((cxm, 2.4), None, heading=h)
            px, py = mm.P((cxm, 2.4))
            body_axes(d, px, py, h, L=58)
            d.text(px, by + 20 + 4.4 * 48 - 14, f"(8, {h})", size=12, family="mono", weight=700, fill=PG,
                   anchor="middle")
            d.text(px, by + 20 + 4.4 * 48 + 4, txt, size=11, fill=T.muted, anchor="middle")

    # ---------------- right column ----------------
    rx = m.box.x1 + 60
    d.text(rx, 0, "From YAML to poses", size=13.5, weight=600, fill=T.fg)
    y8p = YamlPanel(d, rx, 22, 300, list(range(93, 103)), size=10.5, title="node 8 (lines 93-102)")
    y9p = YamlPanel(d, rx + 320, 22, 300, list(range(103, 112)), size=10.5, title="node 9 (lines 103-111)")
    y8p.band([93, 98, 99, 100, 101], LAY, 0, 1)
    y9p.band([103, 109, 110], LAY, 0, 1)
    gy = max(y8p.bb.y1, y9p.bb.y1) + 18
    with d.at(1):
        lines_box(d, rx, gy, ["node 8: 0 -> 0, 180;  90 -> 90, Wrap(270) = -90",
                              "        sorted: -90, 0, 90, 180   poses_[14..17]",
                              "node 9: 90 -> 90, Wrap(270) = -90",
                              "        sorted: -90, 90           poses_[18..19]"], PG, size=11, w=620,
                  title="GetAllowedHeadings(node)", fill=T.card)
    # slot table
    ty = gy + 132
    d.text(rx, ty, "PoseNeighbor slots (pose_graph.hpp), -1 = empty", size=13.5, weight=600, fill=T.fg)
    cols = [("slot", 0), ("(8, 90)", 112), ("(8, -90)", 202), ("(8, 0)", 292), ("(8, 180)", 372),
            ("(9, 90)", 462), ("motion", 546)]
    tw = 680
    rh = 25
    y0 = ty + 18
    d.rect(rx, y0, tw, rh, rx=4, fill=T.tint(PG, 0.14, T.bg))
    for hdr, ox in cols:
        d.text(rx + 10 + ox, y0 + rh / 2, hdr, size=10.5, family="mono", weight=600, fill=T.muted)
    poses_cols = [((8, 90), 3), ((8, -90), 4), ((8, 0), 5), ((8, 180), 5), ((9, 90), 6)]
    for i, sl in enumerate(SLOT_ORDER):
        yy = y0 + rh * (i + 1)
        d.rect(rx, yy, tw, rh, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        d.text(rx + 10, yy + rh / 2, f"{i} {sl}", size=11, family="mono", weight=600, fill=T.fg)
        for j, (p, k) in enumerate(poses_cols):
            v = slots(p).get(sl)
            with d.at(k):
                d.text(rx + 10 + cols[j + 1][1], yy + rh / 2, f"({v[0]}, {v[1]})" if v else "-1", size=11,
                       family="mono", fill=(KIND_COL[SLOT_KIND[sl][0]] if v else T.faint))
        kind, axis = SLOT_KIND[sl]
        with d.at(6):
            d.text(rx + 10 + 546, yy + rh / 2, kind if kind != "VRC_TRANSITION" else "VRC", size=11,
                   family="mono", weight=600, fill=KIND_COL[kind])
            d.text(rx + tw - 8, yy + rh / 2, axis, size=10, family="mono", fill=T.muted, anchor="end")
    tb = BBox(rx, y0, rx + tw, y0 + rh * 9)
    d.rect(rx, y0, tw, rh * 9, rx=4, fill="none", stroke=T.tint(PG, 0.5, T.bg), sw=1)
    for k, col in ((3, 1), (4, 2), (5, 3), (6, 5)):
        with d.only(k):
            x0c = rx + cols[col][1] + 2
            x1c = rx + (cols[col + 1][1] if k != 5 else cols[5][1]) + 2
            d.rect(x0c, y0, x1c - x0c, rh * 9, rx=4, fill="none", stroke=T.sky, sw=1.8, layer="top")
    with d.only(6):
        for i in (0, 2):
            d.rect(rx + 1, y0 + rh * (i + 1) + 1, tw - 2, rh - 2, rx=3, fill="none", stroke=C_STR, sw=1.6,
                   layer="top")
        for i in (1, 3):
            d.rect(rx + 1, y0 + rh * (i + 1) + 1, tw - 2, rh - 2, rx=3, fill="none", stroke=C_LOC, sw=1.6,
                   layer="top")
    with d.at(6):
        note(d, rx, tb.y1 + 14, tw, "Naming issue: FORWARD and BACK are strafes (body x), LEFT and RIGHT are "
                                    "locomotes (body y, the driving axis). The names follow the heading angle used as "
                                    "body +x in the bearing test, not the way the AGV drives.",
             size=11, accent=C_STR)
    # summary
    sy = tb.y1 + 96
    with d.at(7):
        d.text(rx, sy, "Pecos totals (recomputed with the PoseGraph rules)", size=13.5, weight=600, fill=T.fg)
        rows = [("nodes with headings [90]", "26", "x 2 poses", "52"),
                ("nodes with headings [0, 90] (8, 22)", "2", "x 4 poses", "8"),
                ("poses_", "", "", "60"),
                ("slots (8 per pose)", "", "", "480"),
                ("filled: translations", "37 edges x 2 headings x 2 ways", "", "148"),
                ("filled: rotations", "8 poses x ROT_LEFT, ROT_RIGHT", "", "16"),
                ("filled: VRC_UP / VRC_DOWN", "no vrcs", "", "0"),
                ("GarageGraph edges = filled slots", "", "", "164")]
        for i, (a, b, c, v) in enumerate(rows):
            yy = sy + 18 + i * 22
            d.rect(rx, yy, tw, 22, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
            d.text(rx + 10, yy + 11, a, size=11, fill=T.fg2)
            d.text(rx + 300, yy + 11, b + ("  " + c if c else ""), size=10.5, family="mono", fill=T.muted)
            d.text(rx + tw - 10, yy + 11, v, size=11.5, family="mono", weight=700,
                   fill=T.green if v in ("60", "164") else T.fg, anchor="end")

    frame(d, title="How one node becomes poses and neighbour slots",
          subtitle="Step through node 8 and node 9 of the Pecos YAML: their listed headings, the poses they become, "
                   "what a heading means for the AGV's body, and the eight PoseNeighbor slots pose_graph.cpp fills.",
          badge_key="yaml",
          legend=[("arrow", PG, "pose heading (facing)"), ("arrow", C_LOC, "LOCOMOTE slot (body +-y)"),
                  ("arrow", C_STR, "STRAFE slot (body +-x)"), ("arrow", C_ROT, "rotation slot"),
                  ("box", T.green, "AGV (schematic 2.2 x 1.1 m)")],
          footnote="Slots recomputed from the YAML with pose_graph.cpp L58-165 (bearing tolerance 0.1 rad) and checked "
                   "against the report's table; the sign of SignedAngleDist is not in the snapshots and is inferred "
                   "from GetBayOutboundPose's documented 'always LEFT' contract. Motion types from "
                   "GarageGraph::LocomoteOrStrafe. Heading convention as in figure 78.")
    return d


# ======================================================================================
# 108 — faces_reciprocal and the inbound heading
# ======================================================================================

@figure("108_inbound_heading", "faces_reciprocal and the inbound heading (animated)", DOC)
def inbound_heading():
    d = Doc("108_inbound_heading", "How faces_reciprocal sets the inbound heading of a bay and a charger",
            "Animated: bay 7 and chargers 10 and 14 of the Pecos YAML; GetInboundHeading adds 180 when "
            "faces_reciprocal is true and does not wrap; the bay pose, its outbound pose, the retrieval heading "
            "cached on parking nodes, the charging poses, and the unwrapped comparison in PlanAgvChargeJob.")
    BAD, OK = T.red, T.green
    s = 50
    m = Map(d, 0, 40, s, (20.1, 39.9), (9.4, 18.4))
    d.text(0, 0, "The eng sandbox and the qa chargers (Pecos, metres)", size=13.5, weight=600, fill=T.fg)
    m.floor(tick=2)
    m.clip()
    m.corridors()
    m.stalls(labels=True, dim=True)
    m.bays(labels=True)
    m.edges()
    m.nodes(labels=True)
    m.unclip()

    caps = [
        "Three YAML entries that all list headings [90]. Bay 7 and charger 14 add faces_reciprocal: true; charger "
        "10 has faces_reciprocal: false. The heading list alone says only which axis the node allows (90 and its "
        "reciprocal -90); faces_reciprocal picks the direction that counts.",
        "GetInboundHeading (layout.cpp L34) returns headings[0] + faces_reciprocal x 180: 90 + 180 = 270 for bay 7. "
        "It does not wrap. GetBayInboundHeading wraps it: Wrap(270) = -90, the only form a GaragePose can hold "
        "(int16 in [-179, 180]).",
        "The bay pose (7, -90). Heading -90 faces east: AGV-1's body +y, its driving axis, points out of the bay "
        "through the garage-side door towards W31. With faces_reciprocal false it would face west, towards the "
        "patron side (layout.hpp: true = the listed heading has +y towards the patron door).",
        "GetBayOutboundPose (pose_graph.cpp L215) builds the same primary pose and returns its LEFT neighbour: "
        "(31, -90), 4.902 m east, a LOCOMOTE along body +y. The header promises it is always LEFT; nothing in the "
        "snapshots calls it.",
        "The retrieval heading. bay_prioritization_ is [21, 7] (both values 0, ties to the higher id), so "
        "InitRetrievalHeadings takes back() = bay 7, its inbound heading -90 and the reciprocal 90. It caches 90 on "
        "every Parking node that allows 90 and can reach (7, 90): all ten, P5 and P15 among them.",
        "Chargers. C10: faces_reciprocal false, 90 + 0 = 90, AGV-1 charges facing west. C14 (and C16): true, "
        "90 + 180 = 270, stored as pose (14, -90), AGV-2 charges facing east. Both are reached by a 0.61 m strafe: "
        "(9, 90) FORWARD -> (10, 90) and (15, -90) FORWARD -> (14, -90).",
        "The unwrapped comparison. PlanAgvChargeJob (scheduler.cpp L1505) asks whether the AGV is already charging "
        "with agv.pose.heading == GetInboundHeading(curr_node). For AGV-1 on C10 that is 90 == 90. For AGV-2 on C14 "
        "it is -90 == 270: false, so AGV-2 is not recognised as charging. Read from the code, not observed: the "
        "search that follows skips occupied chargers, C14 included, so it plans a move to another free charger or "
        "reports none available. The destination pose at L1548 does wrap.",
    ]
    ks = [d.step(c) for c in caps]
    x7, y7 = m.P(7)
    x31, y31 = m.P(31)
    x10, y10 = m.P(10)
    x14, y14 = m.P(14)
    with d.only(0):
        for nid in (7, 10, 14):
            x, y = m.P(nid)
            d.circle(x, y, 16, fill="none", stroke=LAY, sw=2.2, layer="top")
    with d.only(1):
        head_arrow(d, x7, y7, 90, T.faint, L=56, start=6)
        head_arrow(d, x7, y7, -90, PG, L=56, start=6)
        d.text(x7 - 62, y7 - 14, "90", size=11, family="mono", weight=700, fill=T.muted, anchor="end",
               halo=T.bg_deep, halo_w=3)
        d.text(x7 + 62, y7 - 14, "270 -> Wrap -> -90", size=11, family="mono", weight=700, fill=PG,
               halo=T.bg_deep, halo_w=3)
    with d.at(2, 4):
        m.agv(7, "AGV-1", heading=-90, label_side="above")
    with d.only(2):
        body_axes(d, x7, y7, -90, L=80)
        label_pill(d, x7 + 90, y7 + 40, "+y: garage-side door, towards W31", color=C_LOC, bg=T.bg_deep,
                   border=C_LOC, anchor="start")
        label_pill(d, m.box.x0 + 10, m.box.y0 + 22, "patron side (west)", color=T.muted, bg=T.bg_deep,
                   border=T.border, anchor="start")
    with d.at(3):
        slot_arrow(m, 7, 31, "LEFT", frac=0.5, cut0=80 if True else 0, cut1=10, lab_dy=-22)
        label_pill(d, x31, y31 + 28, "outbound (31, -90)", color=PG, bg=T.bg_deep, border=PG)
    with d.at(5):
        head_arrow(d, x7, y7, -90, PG, L=56, start=6)
        d.text(x7 - 8, y7 + 26, "(7, -90)", size=11, family="mono", weight=700, fill=PG, anchor="middle",
               halo=T.bg_deep, halo_w=3)
    with d.at(4):
        for nid, dy in ((5, 22), (15, -30)):
            x, y = m.P(nid)
            head_arrow(d, x, y, 90, T.amber, L=48, start=4)
            label_pill(d, x - 60, y + dy, "retrieval heading 90", color=T.amber, bg=T.bg_deep, border=T.amber,
                       anchor="middle")
    with d.only(4):
        label_pill(d, (x7 + x31) / 2 + 30, m.Y(16.2), "bay 7 = bay_prioritization_.back()", color=C_BAY,
                   bg=T.bg_deep, border=C_BAY)
    with d.at(5):
        m.agv(10, "AGV-1", heading=90, label_side="right")
        m.agv(14, "AGV-2", heading=-90, label_side="right")
    with d.only(5):
        label_pill(d, x10 - 74, y10 - 40, "(10, 90): faces west", color=PG, bg=T.bg_deep, border=PG, anchor="end")
        label_pill(d, x14, y14 + 46, "(14, -90): faces east", color=PG, bg=T.bg_deep, border=PG)
    with d.at(6):
        label_pill(d, x10 - 74, y10 - 40, "90 == 90: charging", color=OK, bg=T.bg_deep, border=OK, anchor="end")
        label_pill(d, x14, y14 + 56, "-90 == 270: false", color=BAD, bg=T.bg_deep, border=BAD)
        d.circle(x14, y14, 44, fill="none", stroke=BAD, sw=2, dash="5 4", layer="top")

    # ---------------- value table under the map ----------------
    ty = m.box.y1 + 52
    d.text(0, ty, "GetInboundHeading for every bay and charger in Pecos", size=13.5, weight=600, fill=T.fg)
    cols = [("node", 0), ("headings[0]", 90), ("faces_reciprocal", 210), ("GetInboundHeading", 370),
            ("wrapped", 540), ("pose that is used", 640)]
    tw = m.box.w
    rh = 25
    y0 = ty + 18
    d.rect(0, y0, tw, rh, rx=4, fill=T.tint(PG, 0.14, T.bg))
    for hdr, ox in cols:
        d.text(10 + ox, y0 + rh / 2, hdr, size=10.5, family="mono", weight=600, fill=T.muted)
    rows = [("B7", 7, 1, "bay pose (7, -90); outbound (31, -90)"),
            ("B21", 21, 1, "bay pose (21, -90); outbound (41, -90)"),
            ("C10", 10, 5, "charge pose (10, 90)"),
            ("C14", 14, 5, "charge pose (14, -90)"),
            ("C16", 16, 5, "charge pose (16, -90)")]
    for i, (name, nid, k, use) in enumerate(rows):
        n = NODES[nid]
        raw = n.headings[0] + (180 if n.reciprocal else 0)
        yy = y0 + rh * (i + 1)
        d.rect(0, yy, tw, rh, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        with d.at(k):
            vals = [name, str(n.headings[0]), "true" if n.reciprocal else "false", str(raw), str(wrap_deg(raw)), use]
            for j, (v, (hdr, ox)) in enumerate(zip(vals, cols)):
                col = T.fg2
                if j == 0:
                    col = C_BAY if name[0] == "B" else C_CHG
                if j == 3 and raw != wrap_deg(raw):
                    col = T.amber
                d.text(10 + ox, yy + rh / 2, v, size=11, family="mono", weight=700 if j == 0 else 400, fill=col)
    d.rect(0, y0, tw, rh * 6, rx=4, fill="none", stroke=T.tint(PG, 0.5, T.bg), sw=1)
    with d.at(6):
        for i in (3, 4):
            yy = y0 + rh * (i + 1)
            d.rect(10 + 368, yy + 2, 80, rh - 4, rx=3, fill="none", stroke=BAD, sw=1.6, layer="top")
    d.text(0, y0 + rh * 6 + 18, "Amber: the raw value is outside [-179, 180]; any caller that compares it with a "
                                "stored heading without Wrap gets a mismatch.", size=11, fill=T.muted)

    # ---------------- right column: YAML and code ----------------
    rx = m.box.x1 + 56
    d.text(rx, 0, "The YAML and the code that reads it", size=13.5, weight=600, fill=T.fg)
    pw = 226
    panels = [(list(range(75, 84)), "node 7 (Bay)", (78, 81, 82, 83)),
              (list(range(112, 121)), "node 10 (AgvCharge)", (115, 118, 119, 120)),
              (list(range(141, 150)), "node 14 (AgvCharge)", (144, 147, 148, 149))]
    pb = None
    for i, (lines, title, hl_) in enumerate(panels):
        yp = YamlPanel(d, rx + i * (pw + 10), 22, pw, lines, size=10, title=title)
        yp.band(list(hl_), LAY, 0)
        if i == 0:
            yp.band([81, 82, 83], LAY, 1, 4)
        else:
            yp.band([118, 119, 120] if i == 1 else [147, 148, 149], C_CHG, 5, 6)
        pb = yp.bb
    code = ["// layout.cpp L34-36",
            "int GetInboundHeading(const GarageNodeMsg& node) {",
            "  return node.headings.at(0) + node.faces_reciprocal * 180;",
            "}                                              // not wrapped",
            "// layout.cpp L680-690   GetBayInboundHeading(bay_id)",
            "  if(type is not TYPE_BAY or TYPE_BLIFT) return {};",
            "  return volley::Wrap(GetInboundHeading(node));",
            "// pose_graph.cpp L215-228   GetBayOutboundPose(bay_id)",
            "  int16_t bay_heading = bay_node.headings.front();",
            "  if(bay_node.faces_reciprocal) bay_heading = Wrap(bay_heading + 180);",
            "  return GetNeighborPose({bay_id, bay_heading}, PoseNeighbor::LEFT);",
            "// scheduler.cpp L342-384   InitRetrievalHeadings()",
            "  retrieve_bay_id = bay_prioritization.back();           // 7",
            "  retrieval_heading = ReciprocalAngle(GetBayInboundHeading(7));",
            "  for each Parking node allowing 90 with a path to (7, 90):",
            "    gg_.SetRetrievalHeading(node.id, retrieval_heading);  // 90",
            "// scheduler.cpp L1503-1506   PlanAgvChargeJob: already charging?",
            "  if(curr_node.type == GarageNodeMsg::TYPE_AGV_CHARGE &&",
            "     agv.pose.heading == volley::GetInboundHeading(curr_node))",
            "    return {true, \"\"};                     // -90 == 270 is false",
            "// scheduler.cpp L1547-1548   pose of each free charger",
            "  ConstructGaragePose(id, Wrap(GetInboundHeading(node)));  // wrapped"]
    cw = 3 * pw + 20
    cy0 = pb.y1 + 18
    size = 10.5
    pan = code_panel(d, rx, cy0, cw, code, size=size)
    lh = size * 1.5
    top = cy0 + 14 + size / 2

    def hl(lines, col, k0, k1=None):
        with d.at(k0, k0 if k1 is None else k1):
            for i in lines:
                yy = top + i * lh
                d.rect(rx + 6, yy - lh / 2, cw - 12, lh, rx=3, fill=T.tint(col, 0.22, "#0B1222"), layer="main")
    hl([1, 2, 3, 5, 6], PG, 1)
    hl([6], PG, 2)
    hl([8, 9, 10], PG, 3)
    hl([12, 13, 14, 15], T.amber, 4)
    hl([2, 21], C_CHG, 5)
    hl([18, 19], BAD, 6)
    hl([21], OK, 6)
    with d.at(6):
        note(d, rx, pan.y1 + 16, cw,
             "Consequence, read from the code and not observed: an AGV already charging on C14 or C16 is treated "
             "as not charging; the charger loop then skips every occupied charger (GetAgvOnNode), its own included, "
             "and plans a move to the cheapest other free charger, or fails with 'No available charge nodes'. "
             "Charger 10 is unaffected. A scheduler-only fix: compare with Wrap(GetInboundHeading(curr_node)).",
             size=11, accent=BAD, title="Issue: PlanAgvChargeJob compares an unwrapped heading")

    frame(d, title="How faces_reciprocal sets the inbound heading of a bay and a charger",
          subtitle="Step through bay 7 and chargers 10 and 14: the listed heading, the 180-degree flip that "
                   "faces_reciprocal adds, where the AGV's driving axis then points, the poses derived from it, and "
                   "one place where the unwrapped value is compared with a stored heading.",
          badge_key="yaml",
          legend=[("arrow", PG, "inbound heading (facing, body +y)"), ("arrow", T.amber, "cached retrieval heading"),
                  ("arrow", C_LOC, "LOCOMOTE slot"), ("box", T.green, "AGV (schematic 2.2 x 1.1 m)"),
                  ("dashbox", BAD, "comparison that fails")],
          footnote="Code from layout.cpp, pose_graph.cpp and scheduler.cpp (line numbers inside each file of the "
                   "snapshot). volley::Wrap is not in the snapshots; Wrap(270) = -90 follows the [-179, 180] range of "
                   "GaragePose.msg and the explicit Wrap the scheduler applies at L1548. Scheduler::"
                   "ApplyTransitionToFreeingMoves (VECS) also uses the unwrapped value; Pecos has no VECS node.")
    return d
