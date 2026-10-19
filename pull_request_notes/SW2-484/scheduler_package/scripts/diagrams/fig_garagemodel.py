"""The static garage model (doc 01, "The garage model in code"): Layout, PoseGraph, GarageGraph and
CollisionTable as data structures, from sources/repomix-common-ros.xml.

Pose indices / vertex numbers are computed from the Pecos YAML with the PoseGraph rules
(nodes in id order, headings sorted, each YAML heading h plus Wrap(h + 180)). Headings are int16 in
[-179, 180] (interfaces/msg/GaragePose.msg), so the reciprocal of 90 is -90.
"""
from __future__ import annotations

import math

import yaml

from components import class_size, code_panel, connect, frame, label_pill, note, uml_class
from facility import Map
from fig_concepts import _arrow_glyph
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S
from pathlib import Path

DOC1 = "01-software-background.html"
LAY, PG, GG, CT = T.sky, T.teal, T.green, T.amber

# --------------------------------------------------------------------------------------
# Pecos pose graph, recomputed with the PoseGraph rules (pose_graph.cpp)
# --------------------------------------------------------------------------------------
_Y = yaml.safe_load((Path(__file__).resolve().parents[2] / "sources" / "5675_pecos_combined.yaml").read_text())
_NODES = {n["id"]: n for n in _Y["nodes"]}
_ADJ = {i: set() for i in _NODES}
for _e in _Y["edges"]:
    _ADJ[_e["src"]].add(_e["dst"])
    _ADJ[_e["dst"]].add(_e["src"])


def wrap(a):
    """volley::Wrap as GaragePose.msg defines the range: degrees in [-179, 180]."""
    return (a + 179) % 360 - 179


def allowed(nid):
    return sorted({wrap(h + d) for h in _NODES[nid]["headings"] for d in (0, 180)})


POSES = [(i, h) for i in sorted(_NODES) for h in allowed(i)]
VERT = {p: k for k, p in enumerate(POSES)}


def out_edges(p):
    nid, h = p
    out = [((j, h), "T") for j in sorted(_ADJ[nid]) if (j, h) in VERT]
    if _NODES[nid]["rotation_allowed"]:
        others = [g for g in allowed(nid) if g != h]
        cw = min(others, key=lambda g: (h - g) % 360)
        ccw = min(others, key=lambda g: (g - h) % 360)
        out += [((nid, cw), "R"), ((nid, ccw), "R")]
    return out


def transition(src, dst):
    """TransitionType and length as GarageGraph::AddEdge / LocomoteOrStrafe compute them."""
    a, b = _NODES[src[0]], _NODES[dst[0]]
    if src[0] == dst[0]:
        d = abs(((dst[1] - src[1]) + 180) % 360 - 180)
        return "ROTATION", f"{math.radians(d):.3f} rad"
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    yaw = math.radians(src[1]) + math.pi / 2          # Volley heading (0 = +y) -> math frame
    rel = math.atan2(dy, dx) - yaw
    dist = math.hypot(dx, dy)
    kind = "LOCOMOTE" if abs(math.cos(rel)) > abs(math.sin(rel)) else "STRAFE"
    return kind, f"{dist:.3f} m"


N_EDGES = sum(len(out_edges(p)) for p in POSES)
N_ROT = sum(1 for p in POSES for _, k in out_edges(p) if k == "R")
LBL = {nid: ("B" if n["type"] == "Bay" else "C" if n["type"] == "AgvCharge" else "P" if n["type"] == "Parking"
             else "W") + str(nid) for nid, n in _NODES.items()}


def _table(d, x, y, w, title, sub, rows, cols, accent, *, size=11.5, rh=22, hl=()):
    """Small data table: rows of cells; cols = [(header, x_offset)]."""
    d.text(x, y, title, size=13, weight=600, family="mono", fill=accent)
    d.text(x, y + 18, sub, size=11, fill=T.muted)
    y0 = y + 34
    d.rect(x, y0, w, rh, rx=4, fill=T.tint(accent, 0.14, T.bg))
    for hdr, ox in cols:
        d.text(x + ox, y0 + rh / 2, hdr, size=10.5, family="mono", weight=600, fill=T.muted)
    yy = y0 + rh
    for i, row in enumerate(rows):
        if row is None:
            d.text(x + w / 2, yy + rh / 2, "...", size=11, family="mono", fill=T.faint, anchor="middle")
            yy += rh
            continue
        fill = T.tint(accent, 0.10, T.bg) if i in hl else (T.tint(T.card, 0.6, T.bg) if i % 2 else T.card)
        d.rect(x, yy, w, rh, fill=fill, stroke=T.tint(accent, 0.55, T.bg) if i in hl else None, sw=1)
        for (txt, (hdr, ox)) in zip(row, cols):
            d.text(x + ox, yy + rh / 2, txt, size=size, family="mono", fill=T.fg if i in hl else T.fg2)
        yy += rh
    d.rect(x, y0, w, yy - y0, rx=4, fill="none", stroke=T.tint(accent, 0.5, T.bg), sw=1)
    return BBox(x, y, x + w, yy)


# ======================================================================================
# 75 — the four classes and what they store
# ======================================================================================

@figure("75_garage_model_classes", "The static garage model: four classes", DOC1)
def garage_model_classes():
    d = Doc("75_garage_model_classes", "The static garage model: Layout, PoseGraph, GarageGraph, CollisionTable",
            "UML of the four common_ros classes the Scheduler builds once, with the containers each one stores "
            "and the queries the scheduler makes of them.")
    M = 11
    lay = uml_class(d, 0, 0, "Layout", accent=LAY, stereo="common_ros/layout.hpp · places", size=M, attrs=[
        "- nodes_: std::vector<GarageNodeMsg>          // sorted by id",
        "- node_id_to_index_: std::map<uint32_t, uint32_t>",
        "- node_ids_by_type_: std::map<type, std::vector<uint32_t>>",
        "- graph_: adjacency_list<listS, vecS, undirectedS>",
        "      // vertex = index into nodes_, not the node id",
        "- disallowed_edge_orientations_: std::map<pair<u32,u32>, int16_t>",
        "- resource_windows_: std::vector<ParkingWindowMsg>  // by area",
        "- floors_, bay_prioritization_, bay_*_floors_, vrcs_",
        "- name_, md5sum_: std::string"], methods=[
        "+ GetNodeById(id): optional<GarageNodeMsg>    // a copy",
        "+ GetNodes(): const vector<GarageNodeMsg>&",
        "+ GetNodeIdsOfType(type): const vector<uint32_t>&",
        "+ GetNeighboringNodes(id): vector<GarageNodeMsg>",
        "+ HasEdge(a, b), GetDisallowedEdgeOrientation(a, b)",
        "+ GetGeometricPoseAtPose(pose): optional<GeometricPose>",
        "+ GetResourceWindow(i), GetBayInboundHeading(bay)"])
    pg = uml_class(d, lay.x1 + 150, 0, "PoseGraph", accent=PG, stereo="common_ros/pose_graph.hpp · poses", size=M,
                   attrs=[
                       "- layout_: LayoutSPtr",
                       "- poses_: std::vector<GaragePoseMsg>   // by node id, then heading",
                       "- pose_indices_: std::map<GaragePoseMsg, int, GaragePoseComparator>",
                       "- pose_neighbors_: std::vector<int>    // 8 slots per pose, -1 = none",
                       "- overlapping_sized_poses_: vector<vector<vector<SizedPoseMsg>>>"], methods=[
                       "+ PoseGraph(LayoutSPtr)                 // expands nodes into poses",
                       "+ GetPoses(): const vector<GaragePoseMsg>&",
                       "+ GetPoseIndex(pose): int               // kInvalidIndex = -1",
                       "+ GetNeighborPose(pose, PoseNeighbor): optional<GaragePoseMsg>",
                       "+ GetOverlappingSizedPoses(index, size)",
                       "+ GetBayOutboundPose(bay)"])
    gy = max(lay.y1, pg.y1) + 70
    gg = uml_class(d, 0, gy, "GarageGraph", accent=GG, stereo="common_ros/garage_graph.hpp · motion", size=M, attrs=[
        "- layout_: LayoutSPtr",
        "- base_graph_: BoostPoseGraph",
        "      // adjacency_list<vecS, vecS, bidirectionalS, GaragePoseMsg, {edge_index, Transition}>",
        "- pose_to_vertex_: std::unordered_map<GaragePoseMsg, Vertex>",
        "- edge_index_to_vertices_: std::vector<std::pair<Vertex, Vertex>>",
        "- node_retrieval_heading_: std::unordered_map<uint32_t, int16_t>"], methods=[
        "+ GetVertexFromPose(pose): optional<Vertex>   // exact hash lookup",
        "+ GetPoseFromVertex(v): optional<GaragePoseMsg>",
        "+ GarageNodeFromVertex(v): optional<GarageNodeMsg>",
        "+ GetOutEdges(v), GetInEdges(v)                // throw if v is invalid",
        "+ EdgeFromPoses(a, b), GetTransition(e): optional<...>",
        "+ GetVerticesAtGarageNode(node), GetBaseGraph()",
        "+ MakeVertexVectorPropertyMap<T>(), MakeEdgeVectorPropertyMap<T>()",
        "+ SetRetrievalHeading(node, h), GetRetrievalHeading(node)"])
    ct = uml_class(d, gg.x1 + 150, gy, "CollisionTable", accent=CT, stereo="common_ros/collision_geometry.hpp · space",
                   size=M, attrs=[
                       "- gg_: const GarageGraph&",
                       "- ppmap_: ResMap<Pose, Pose>    // pose vs pose",
                       "- pemap_: ResMap<Pose, Edge>    // pose vs edge",
                       "- epmap_: ResMap<Edge, Pose>",
                       "- eemap_: ResMap<Edge, Edge>",
                       "- cache_file_path_: ~/.cache/volley/<layout>_collision_table_<md5>.json"], methods=[
                       "+ CollisionTable(gg, logger)     // load cache, else build + save",
                       "+ Query(fixed_id, queried_id, loc): tuple<PoseSet, EdgeSet>",
                       "+ Query(fixed_id, queried_id, loc, queried_loc): bool"])
    # relations
    connect(d, [(pg.x0, pg.y0 + 70), (lay.x1, pg.y0 + 70)], kind="assoc", color=PG, label="layout_ (shared_ptr)",
            label_at=((pg.x0 + lay.x1) / 2, pg.y0 + 56))
    connect(d, [(gg.cx - 90, gg.y0), (gg.cx - 90, lay.y1)], kind="assoc", color=GG, label="layout_",
            label_at=(gg.cx - 96, (gg.y0 + lay.y1) / 2), label_anchor="end")
    connect(d, [(gg.cx + 60, gg.y0), (gg.cx + 60, gy - 34), (pg.cx, gy - 34), (pg.cx, pg.y1)], kind="dep",
            color=GG, label="built from (constructor only)", label_at=((gg.cx + pg.cx) / 2 + 40, gy - 46))
    connect(d, [(ct.x0, ct.y0 + 70), (gg.x1, ct.y0 + 70)], kind="assoc", color=CT, label="gg_ (reference)",
            label_at=((ct.x0 + gg.x1) / 2, ct.y0 + 56))
    # ---- the value types the four classes are made of ----
    VT = T.violet
    vy = max(gg.y1, ct.y1) + 64
    d.text(0, vy - 24, "The value types inside them", size=14, weight=600, fill=T.fg)
    d.text(260, vy - 24, "ROS messages (interfaces/msg, alias ...Msg) and plain C++ types; 'in:' names the members that hold them",
           size=11, fill=T.muted)
    vts = [
        ("GaragePoseMsg", "msg · a pose: in poses_, pose_to_vertex_, table keys", T.green, [
            "+ node_id: uint32", "+ heading: int16   // degrees [-179, 180]; 0 = +y, CCW+, 90 = west"]),
        ("GarageNodeMsg", "msg · a place: in Layout::nodes_", LAY, [
            "TYPE_UNKNOWN 0, PARKING 1, WAYPOINT 2, LIFT 3,", "BAY 4, AGV_CHARGE 5, EV_CHARGE 6, BLIFT 7",
            "+ id: uint32", "+ x, y: float32       // metres, east-north-up", "+ floor: uint8", "+ type: uint8",
            "+ max_resource_size: string", "+ max_resource_size_index: uint8",
            "+ bay_prioritization: int16   // bays", "+ rotation_allowed: bool",
            "+ headings: int16[]   // 0..179, ascending", "+ faces_reciprocal: bool",
            "+ insert_floor: uint8, system_floors: uint8[]   // bays"]),
        ("GeometricPoseMsg", "msg · metres + radians: GetGeometricPoseAtPose", T.sky, [
            "+ x, y: float32   // metres", "+ yaw: float32     // radians, same zero and sense as heading"]),
        ("SizedPoseMsg", "msg · pose + footprint size: overlapping_sized_poses_", PG, [
            "+ resource_size_index: uint8   // into resource_windows_", "+ pose: GaragePose"]),
        ("ParkingWindowMsg", "msg · a size class: Layout::resource_windows_", LAY, [
            "+ name: string   // COMPACT, ..., XL, TRAY", "+ length_m: float32   // along the heading",
            "+ width_m: float32    // across it", "+ height_m: float32"]),
        ("GarageFloorMsg", "msg · Layout::floors_", LAY, ["+ id: uint8", "+ z: float32   // metres, arbitrary origin"]),
        ("Vrc", "struct (layout.hpp) · Layout::vrcs_", LAY, [
            "+ id, root_node_id: uint32", "+ nodes: vector<GarageNodeMsg>   // by floor"]),
        ("Transition", "struct (garage_graph.hpp) · every gg_ edge", GG, [
            "+ length: double   // m, rad, or floor height", "+ type: TransitionType",
            "  LOCOMOTE | STRAFE | ROTATION | VRC_TRANSITION"]),
        ("PoseNeighbor", "enum (pose_graph.hpp) · slot in pose_neighbors_", PG, [
            "FORWARD, RIGHT, BACK, LEFT,", "ROT_RIGHT, ROT_LEFT, VRC_UP, VRC_DOWN"]),
        ("GarageGraph::Vertex / Edge", "aliases · Boost descriptors", GG, [
            "Vertex = std::size_t   // index of a pose", "Edge = {m_source, m_target, property*}"]),
        ("CollisionTable::Pose / Edge", "aliases · table keys", CT, [
            "Pose = GaragePoseMsg", "Edge = std::array<Pose, 2>   // a move",
            "PoseOrEdge = std::variant<Pose, Edge>"]),
        ("CollisionEntityId", "enum (collision_geometry.hpp) · table ids", CT, [
            "BAY_ODP = 0, TRAY_LEGS, TRAY, AGV,", "PAYLOAD (+ window index)"]),
    ]
    total_w = ct.x1
    gap = 22
    ncol = 3
    colw = (total_w - gap * (ncol - 1)) / ncol
    tops = [vy] * ncol
    for name, st, col, attrs in vts:
        c = min(range(ncol), key=lambda k: tops[k])
        b = uml_class(d, c * (colw + gap), tops[c], name, accent=col, stereo=st, attrs=attrs, size=10.5,
                      name_size=13, compact=True, w=colw)
        tops[c] = b.y1 + gap
    yb = max(tops) + 10
    note(d, 0, yb, ct.x1, "Scheduler::Scheduler builds them in this order and never changes them afterwards: "
         "layout_(make_shared<Layout>(file)), pg_(layout_), gg_(pg_), table_(gg_, logger). The only later write is "
         "gg_.SetRetrievalHeading(...) from InitRetrievalHeadings(), still inside the constructor. GarageGraph keeps "
         "no pointer to the PoseGraph: it copies poses and neighbours into its own Boost graph.",
         title="One chain, built once", accent=GG)
    frame(d, title="The static garage model: four classes and what they store",
          subtitle="Layout stores places (YAML nodes and edges); PoseGraph expands every node into poses and finds "
                   "each pose's neighbours; GarageGraph copies that into a Boost graph for searches; CollisionTable "
                   "precomputes which footprints conflict at which poses and edges. Members abridged.",
          badge_key="as-built",
          legend=[("box", LAY, "places"), ("box", PG, "poses"), ("box", GG, "motion graph"),
                  ("box", CT, "space"), ("box", T.sky, "geometry"), ("assoc", T.fg2, "holds"), ("dep", T.fg2, "built from")],
          footnote="From sources/repomix-common-ros.xml: layout.hpp, pose_graph.hpp, garage_graph.hpp, "
                   "collision_geometry.hpp; messages from interfaces/msg (sources/repomix-interfaces.xml). "
                   "Private members abridged.")
    return d


# ======================================================================================
# 76 — what a Vertex is
# ======================================================================================

@figure("76_garage_graph_vertex", "What a GarageGraph Vertex is", DOC1)
def garage_graph_vertex():
    d = Doc("76_garage_graph_vertex", "What a GarageGraph Vertex is",
            "A Vertex is an index into the Boost adjacency list's vertex vector. Each entry stores the pose "
            "(node + heading) and the vertex's out- and in-edge lists; a hash map translates poses to indices.")
    code = code_panel(d, 0, 0, 760, [
        "// common_ros/garage_graph.hpp",
        "using BoostPoseGraph = boost::adjacency_list<",
        "    boost::vecS,            // 1 OutEdgeList: each vertex's out-edges in a std::vector",
        "    boost::vecS,            // 2 VertexList: vertices in a std::vector -> Vertex = index",
        "    boost::bidirectionalS,  // 3 Directed: also keep in-edges (GetInEdges)",
        "    GaragePoseMsg,          // 4 VertexProperties: data stored WITH each vertex",
        "    boost::property<boost::edge_index_t, std::size_t, Transition>>;",
        "                            // 5 EdgeProperties: edge index, then the Transition bundle",
        "",
        "class GarageGraph {",
        "  using Vertex = BoostPoseGraph::vertex_descriptor;  // std::size_t, 0 .. NumVertices()-1",
        "  using Edge   = BoostPoseGraph::edge_descriptor;    // {m_source, m_target, property pointer}",
        "  BoostPoseGraph base_graph_;",
        "  std::unordered_map<GaragePoseMsg, Vertex> pose_to_vertex_;  // hash of (node_id, heading)",
        "};",
        "struct Transition { double length;  TransitionType type; };  // LOCOMOTE, STRAFE, ROTATION, VRC_TRANSITION",
    ], title="The definition (parameters 6 and 7 are Boost's defaults: no_property, listS)", size=11.5)
    # ---- right: mini map of W22's neighbourhood with vertex numbers ----
    xlim, ylim = (26.6, 39.2), (18.3, 25.2)
    s = 44
    mx = code.x1 + 40
    m = Map(d, mx, 0, s, xlim, ylim)
    m.base(labels=True, zones=False, axes=False)
    show = [18, 19, 22, 23, 25, 26, 41]
    for nid in show:
        x, y = m.P(nid)
        hs = allowed(nid)
        offs = ({0: (0, -36), 90: (-36, 0), 180: (0, 36), -90: (36, 0)} if len(hs) == 4
                else {90: (-24, -24), -90: (24, -24)})
        for h in hs:
            ox, oy = offs[h]
            px, py = x + ox, y + oy
            col = GG if nid == 22 else T.tint(GG, 0.7, T.bg)
            d.circle(px, py, 11, fill=T.card, stroke=col, sw=1.6, layer="over")
            _arrow_glyph(d, px, py, h, col, r=8)
            if len(hs) == 4:
                lx, ly = x + ox * 1.62, y + oy * 1.62
            else:
                lx, ly = px, py - 19
            d.text(lx, ly, f"v{VERT[(nid, h)]}", size=10.5, family="mono", weight=700,
                   fill=T.fg if nid == 22 else T.fg2, anchor="middle", halo=T.bg_deep, halo_w=3, layer="top")
    mb = m.box
    d.text(mb.x0, mb.y1 + 18, "Pecos, around W22: one ring per vertex (arrow = heading); v44 = GarageGraph::Vertex 44.",
           size=11, fill=T.muted)
    d.text(mb.x0, mb.y1 + 34, f"Whole layout: {len(_NODES)} nodes -> {len(POSES)} vertices, {N_EDGES} directed edges "
                              f"({N_ROT} rotations).", size=11, fill=T.muted)

    # ---- bottom: the three storage structures ----
    top = max(code.y1, mb.y1 + 40) + 40
    hrows = [(f"{{node_id: {n}, heading: {h}}}", str(VERT[(n, h)])) for n, h in ((18, -90), (18, 90), (22, -90), (22, 0), (22, 90),
                                                                 (22, 180), (23, 90))] + [None, ("{node_id: 41, heading: 90}", str(VERT[(41, 90)]))]
    t1 = _table(d, 0, top, 300, "pose_to_vertex_", "unordered_map<GaragePoseMsg, Vertex>",
                hrows, [("key: {node_id, heading}", 10), ("Vertex", 220)], GG, hl=(4,))
    v43 = out_edges((22, 90))
    vrows = []
    for v in (35, 42, 43, 44, 45, 47):
        p = POSES[v]
        outs = out_edges(p)
        ins = [q for q in POSES if any(t == p for t, _ in out_edges(q))]
        vrows.append((str(v), f"{{node_id: {p[0]}, heading: {p[1]}}}", ", ".join(str(VERT[t]) for t, _ in outs),
                      ", ".join(str(VERT[q]) for q in ins)))
    vrows.insert(1, None)
    t2 = _table(d, t1.x1 + 40, top, 680, "base_graph_ vertices", "std::vector: index = Vertex; stored per vertex",
                vrows, [("Vertex", 10), ("bundle: GaragePoseMsg", 70), ("out_edges -> target Vertex", 290),
                        ("in_edges <- source Vertex", 480)],
                GG, hl=(4,))
    erows = []
    for tgt, _ in v43:
        kind, length = transition((22, 90), tgt)
        erows.append((f"{VERT[(22, 90)]} -> {VERT[tgt]}", f"{{node_id: {tgt[0]}, heading: {tgt[1]}}}", kind, length))
    t3 = _table(d, t2.x1 + 40, top, 560, f"edges out of Vertex {VERT[(22, 90)]}", "Edge = (source Vertex, target Vertex) + Transition{type, length}",
                erows, [("edge", 10), ("target pose", 90), ("Transition.type", 310), ("length", 450)], T.violet)
    # lookup arrows
    connect(d, [(t1.x1, t1.y0 + 34 + 22 + 4 * 22 + 11), (t2.x0, t2.y0 + 34 + 22 + 4 * 22 + 11)], kind="flow",
            color=GG, size=8)
    connect(d, [(t2.x1, t2.y0 + 34 + 22 + 4 * 22 + 11), (t3.x0, t3.y0 + 34 + 22 + 11)], kind="flow", color=T.violet,
            size=8)
    yb = max(t1.y1, t2.y1, t3.y1) + 28
    steps = [
        ("gg_.GetVertexFromPose({node_id: 22, heading: 90})", "hash lookup in pose_to_vertex_ -> 44; {node_id: 22, heading: 270} or an unknown node -> nullopt"),
        ("gg_.GetPoseFromVertex(44)", "index into base_graph_'s vertex vector -> {node_id: 22, heading: 90}; v >= NumVertices() -> nullopt"),
        ("gg_.GetOutEdges(44)", "iterator pair over that vertex's out-edge vector (throws std::invalid_argument if invalid)"),
        ("gg_.GarageNodeFromVertex(44)", "pose.node_id -> layout_->GetNodeById(22): a std::map lookup and a copy of the node"),
    ]
    w = t3.x1
    d.text(0, yb, "Reading the structure", size=13, weight=600, fill=T.fg)
    for i, (call, what) in enumerate(steps):
        y = yb + 22 + i * 24
        d.text(0, y, call, size=11.5, family="mono", fill=GG)
        d.text(470, y, what, size=11.5, fill=T.fg2)
    frame(d, title="What a GarageGraph Vertex is",
          subtitle="Vertex is BoostPoseGraph::vertex_descriptor: with vecS storage, a plain std::size_t index into "
                   "the graph's vertex vector. The pose lives in that vector entry; pose_to_vertex_ is the reverse "
                   "map. Vertex 44 is the pose {node_id: 22, heading: 90}; W22 lists headings 0 and 90, so it owns four vertices (42-45).",
          badge_key="yaml",
          legend=[("ring", GG, "vertex (arrow = heading)"), ("box", GG, "GarageGraph storage"),
                  ("box", T.violet, "edge records")],
          footnote="Vertex numbers and edges recomputed from the Pecos YAML with the PoseGraph rules "
                   "(nodes by id, headings ascending, h and h+180). Out-edge order inside Boost is insertion order, "
                   "which follows the neighbour slots; the lists here are sorted. Headings are int16 in [-179, 180] "
                   "(GaragePose.msg), so the reciprocal of 90 is -90 and it sorts first.")
    return d


# ======================================================================================
# 81 — reading BoostPoseGraph: the seven template parameters and what Boost stores
# ======================================================================================

def _wrap_words(s, width, size, family="sans", weight=400):
    out, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if cur and text_width(t, size, family, weight) > width:
            out.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


@figure("81_boost_pose_graph", "Inside BoostPoseGraph", DOC1)
def boost_pose_graph():
    d = Doc("81_boost_pose_graph", "Inside BoostPoseGraph",
            "The seven template parameters of boost::adjacency_list as BoostPoseGraph fills them, and what Boost "
            "stores for Vertex 44: a vector entry holding the pose and two edge lists that point into one "
            "graph-wide edge list, where each edge's index and Transition are stored once.")
    W = 1580
    EV, VX, DR, GR = T.violet, GG, T.sky, T.faint
    # ---------------- 1. the seven parameters ----------------
    d.text(0, 0, "1  The type: boost::adjacency_list has seven template parameters", size=15, weight=600, fill=T.fg)
    d.text(0, 22, "Boost's parameter names (top) and what BoostPoseGraph passes (mono). The last two are not passed, "
                  "so they take Boost's defaults.", size=12, fill=T.muted)
    params = [
        ("OutEdgeList", ["boost::vecS"], EV, False,
         "container for each vertex's out-edge list: a std::vector"),
        ("VertexList", ["boost::vecS"], VX, False,
         "container for the vertices: a std::vector, so a vertex is named by its index (std::size_t)"),
        ("Directed", ["boost::bidirectionalS"], DR, False,
         "edges are one-way; each vertex also keeps an in-edge list (GetInEdges)"),
        ("VertexProperties", ["GaragePoseMsg"], VX, False,
         "data stored WITH each vertex (the bundle), read as base_graph_[v]. Not the vertex itself"),
        ("EdgeProperties", ["property<edge_index_t,", "  std::size_t, Transition>"], EV, False,
         "data stored with each edge: an edge index, then the Transition bundle, read as base_graph_[e]"),
        ("GraphProperties", ["no_property"], GR, True,
         "default: nothing is stored for the graph as a whole"),
        ("EdgeList", ["listS"], EV, True,
         "default: every edge sits once in a graph-wide std::list; vertex edge lists point into it"),
    ]
    gap = 12
    cw = (W - gap * 6) / 7
    ch = 150
    y0 = 44
    for k, (name, arg, col, dflt, what) in enumerate(params):
        x = k * (cw + gap)
        d.rect(x, y0, cw, ch, rx=10, fill=T.card, stroke=col, sw=1.5, dash="6 4" if dflt else None)
        num_badge_x = x + 20
        d.circle(num_badge_x, y0 + 20, 11, fill=col)
        d.text(num_badge_x, y0 + 20.5, str(k + 1), size=12, family="mono", weight=700, fill=T.bg, anchor="middle")
        d.text(x + 38, y0 + 20, name, size=13, weight=600, fill=T.fg)
        yy = y0 + 46
        for ln in arg:
            d.text(x + 14, yy, ln, size=11.5, family="mono", weight=600, fill=col)
            yy += 17
        yy += 6
        for ln in _wrap_words(what, cw - 28, 11.5):
            d.text(x + 14, yy, ln, size=11.5, fill=T.fg2)
            yy += 16
        if dflt:
            d.text(x + 14, y0 + ch - 14, "(default)", size=11, family="mono", fill=T.faint)
    # ---------------- 2. what is stored ----------------
    y1 = y0 + ch + 56
    d.text(0, y1, "2  What base_graph_ stores for Vertex 44 = {node_id: 22, heading: 90}", size=15, weight=600, fill=T.fg)
    d.text(0, y1 + 22, "Boost internals, simplified (names from boost/graph/detail/adjacency_list.hpp; members are private to "
                       "Boost: the code only uses the public calls in part 3).", size=12, fill=T.muted)
    # the vertex number
    vy = y1 + 82
    chip_bb = label_pill(d, 0, vy, "Vertex v = 44", color=VX, size=13, weight=700)
    d.text(0, vy + 26, "std::size_t", size=11.5, family="mono", fill=T.muted)
    d.text(0, vy + 42, "just a number", size=11.5, fill=T.muted)
    # the vertex vector
    vx0 = 200
    cellw = 92
    d.text(vx0, vy - 34, "m_vertices : std::vector<stored_vertex>", size=12, family="mono", weight=600, fill=VX)
    cells = ["...", "[42]", "[43]", "[44]", "[45]", "..."]
    for i, c in enumerate(cells):
        cx = vx0 + i * cellw
        hl = c == "[44]"
        d.rect(cx, vy - 18, cellw, 36, fill=T.tint(VX, 0.18, T.bg) if hl else T.card,
               stroke=VX if hl else T.border_soft, sw=1.6 if hl else 1)
        d.text(cx + cellw / 2, vy, c, size=12, family="mono", weight=700 if hl else 400,
               fill=T.fg if hl else T.muted, anchor="middle")
    connect(d, [(chip_bb.x1 + 6, vy), (vx0 - 2, vy)], kind="flow", color=VX, size=8)
    c44 = vx0 + 3 * cellw
    # the stored_vertex record
    sx, sy, sw_ = vx0, vy + 60, 640
    outs = out_edges((22, 90))
    ins = [q for q in POSES if any(t == (22, 90) for t, _ in out_edges(q))]
    rows = [
        ("m_property", "GaragePoseMsg", "{node_id: 22, heading: 90}"),
        ("m_out_edges", "std::vector<stored_edge_iter>", "  ".join(f"->{VERT[t]}" for t, _ in outs)),
        ("m_in_edges", "std::vector<stored_edge_iter>", "  ".join(f"<-{VERT[q]}" for q in ins)),
    ]
    rh = 46
    d.rect(sx, sy, sw_, 30 + rh * len(rows), rx=8, fill=T.card, stroke=VX, sw=1.5)
    d.rect(sx, sy, sw_, 28, rx=8, fill=T.tint(VX, 0.16, T.bg))
    d.text(sx + 12, sy + 14, "stored_vertex  (m_vertices[44])", size=12.5, family="mono", weight=600, fill=T.fg)
    for i, (mem, typ, val) in enumerate(rows):
        ry = sy + 30 + i * rh
        if i:
            d.line(sx, ry, sx + sw_, ry, stroke=T.border_soft)
        d.text(sx + 12, ry + 15, mem, size=12, family="mono", weight=600, fill=VX if i == 0 else EV)
        d.text(sx + 130, ry + 15, typ, size=11.5, family="mono", fill=T.muted)
        d.text(sx + 12, ry + 33, val, size=12, family="mono", fill=T.fg)
    connect(d, [(c44 + cellw / 2, vy + 18), (c44 + cellw / 2, sy)], kind="flow", color=VX, size=8)
    out_row_y = sy + 30 + rh + 33
    in_row_y = sy + 30 + 2 * rh + 33
    # position of the "->59" token inside the out-edge row
    toks = [f"->{VERT[t]}" for t, _ in outs]
    k59 = [t for t, _ in outs].index((41, 90))
    pre = "  ".join(toks[:k59]) + ("  " if k59 else "")
    t59x = sx + 12 + text_width(pre, 12, "mono") + text_width(toks[k59], 12, "mono") / 2
    d.rect(t59x - text_width(toks[k59], 12, "mono") / 2 - 4, out_row_y - 10, text_width(toks[k59], 12, "mono") + 8, 20,
           rx=4, fill="none", stroke=EV, sw=1.4)
    # the global edge list
    ex = sx + sw_ + 90
    ew = W - ex
    d.text(ex, vy - 34, "m_edges : std::list<list_edge>   (EdgeList = listS)", size=12, family="mono", weight=600, fill=EV)
    kind, length = transition((22, 90), (41, 90))
    ny = vy - 18
    d.rect(ex, ny, ew, 34, rx=6, fill=T.card, stroke=T.border_soft, dash="4 4")
    d.text(ex + ew / 2, ny + 17, "... one node per directed edge (E nodes) ...", size=11.5, fill=T.muted, anchor="middle")
    ly = ny + 50
    lines = [
        ("list_edge", T.fg, 600),
        ("  m_source   : 44", T.fg2, 400),
        (f"  m_target   : {VERT[(41, 90)]}            // {{node_id: 41, heading: 90}}", T.fg2, 400),
        ("  m_property : property<edge_index_t, size_t, Transition>", T.fg2, 400),
        ("    m_value  : i                 // edge index = num_edges() when AddEdge ran", T.fg2, 400),
        (f"    m_base   : Transition {{type: {kind}, length: {length.split()[0]}}}   // metres", T.fg2, 400),
    ]
    lh = 19
    lhgt = 16 + lh * len(lines)
    d.rect(ex, ly, ew, lhgt, rx=8, fill=T.tint(EV, 0.10, T.bg), stroke=EV, sw=1.5)
    for i, (s, col, wgt) in enumerate(lines):
        if "//" in s:
            j = s.index("//")
            d.rich(ex + 12, ly + 18 + i * lh, [(s[:j], "mono", wgt, col), (s[j:], "mono", 400, T.faint)], size=11.5)
        else:
            d.text(ex + 12, ly + 18 + i * lh, s, size=11.5, family="mono", weight=wgt, fill=col)
    # arrows: out-edge entry of 44 and in-edge entry of 59 both point at the same list node
    connect(d, [(t59x, out_row_y + 10), (t59x, out_row_y + 13), (ex - 40, out_row_y + 13), (ex - 40, ly + 30),
                (ex, ly + 30)], kind="flow", color=EV, size=8)
    in59 = ly + lhgt + 56
    d.text(ex, in59, f"m_vertices[{VERT[(41, 90)]}].m_in_edges  =  [ ...  <-44  ... ]", size=12, family="mono",
           fill=T.fg2)
    in_pre = f"m_vertices[{VERT[(41, 90)]}].m_in_edges  =  [ ...  "
    t44x = ex + text_width(in_pre, 12, "mono") + text_width("<-44", 12, "mono") / 2
    d.rect(t44x - text_width("<-44", 12, "mono") / 2 - 4, in59 - 10, text_width("<-44", 12, "mono") + 8, 20, rx=4,
           fill="none", stroke=EV, sw=1.4)
    connect(d, [(t44x, in59 - 10), (t44x, ly + lhgt)], kind="flow", color=EV, size=8)
    d.text(t44x + 12, in59 - 26, "the same list node: each edge is stored once", size=11.5, fill=EV)
    d.text(sx, sy + 30 + rh * len(rows) + 20, "stored_edge_iter = {m_target, iterator into m_edges}: the edge's data "
           "is not copied into the vertex", size=11.5, fill=T.muted)
    # ---------------- 3. reading it ----------------
    y3 = max(sy + 30 + rh * len(rows) + 20, in59) + 60
    d.text(0, y3, "3  Reading it through the public API", size=15, weight=600, fill=T.fg)
    code = code_panel(d, 0, y3 + 20, 880, [
        "// a vertex is a number; the pose is its bundle",
        "GaragePoseMsg& p = base_graph_[44];              // {node_id: 22, heading: 90}",
        "auto [it, end] = boost::out_edges(44, base_graph_);   // walks m_out_edges",
        "",
        "// an edge is a descriptor, not a number:",
        "// Edge e = {m_source: 44, m_target: 59, m_eproperty: pointer to the list node's property}",
        "Edge e = boost::edge(44, 59, base_graph_).first;  // scans 44's out-edges",
        f"Transition& t = base_graph_[e];                   // {{type: {kind}, length: {length.split()[0]}}}",
        "std::size_t i = edge_index_[e];                   // = boost::get(boost::edge_index, base_graph_)[e]",
    ], title="garage_graph.cpp style", size=12)
    note(d, code.x1 + 30, y3 + 20, W - code.x1 - 30,
         "Parameter 4 is named VertexProperties: data Boost keeps next to each vertex. The vertex itself is "
         "always vertex_descriptor, which Boost derives from parameter 2: with vecS it is the vector index. "
         "That index is what every Boost algorithm takes, and it makes per-vertex arrays plain vectors "
         "(dist[v], MakeVertexVectorPropertyMap<T>). Finding a vertex from a pose needs a hash, so GarageGraph "
         "adds pose_to_vertex_. DagBase<T> uses the same shape with std::shared_ptr<T> as its bundle.",
         title="Why Vertex is not a GaragePoseMsg", accent=VX, size=12)
    frame(d, title="Inside BoostPoseGraph: template parameters and storage",
          subtitle="using BoostPoseGraph = boost::adjacency_list<vecS, vecS, bidirectionalS, GaragePoseMsg, "
                   "boost::property<boost::edge_index_t, std::size_t, Transition>>. Vertex 44 is an index; the pose "
                   "is stored in that vector entry; each edge's index and Transition are stored once in the edge list.",
          badge_key="as-built",
          legend=[("box", VX, "vertex storage"), ("box", EV, "edge storage"), ("box", DR, "direction"),
                  ("dashbox", GR, "default (not passed)"), ("arrow", T.fg2, "points to")],
          footnote="Template parameters and Boost member names: boost/graph/adjacency_list.hpp and "
                   "boost/graph/detail/adjacency_list.hpp (BGL), simplified. BoostPoseGraph, AddEdge and edge_index_ "
                   "from sources/repomix-common-ros.xml (garage_graph.hpp/.cpp). Vertex numbers and the Transition "
                   "recomputed from the Pecos YAML; the edge index i is the insertion order and is not computed here.")
    return d


# ======================================================================================
# 77 — CollisionTable storage
# ======================================================================================

@figure("77_collision_table_storage", "CollisionTable storage", DOC1)
def collision_table_storage():
    d = Doc("77_collision_table_storage", "CollisionTable storage",
            "Four nested hash maps keyed fixed entity id -> fixed location -> queried entity id -> set of "
            "conflicting locations, built once from the GarageGraph and cached on disk.")
    code = code_panel(d, 0, 0, 700, [
        "// common_ros/collision_geometry.hpp (abridged)",
        "using Pose = GaragePoseMsg;",
        "using Edge = std::array<Pose, 2>;",
        "using PoseOrEdge = std::variant<Pose, Edge>;",
        "template <typename FixedState, typename QueriedState>",
        "using ResMap = std::unordered_map<size_t,                // fixed entity id",
        "    std::unordered_map<FixedState,                       // where it is",
        "        std::unordered_map<size_t,                       // queried entity id",
        "            std::unordered_set<QueriedState>>>>;         // where that one may NOT be",
        "ResMap<Pose, Pose> ppmap_;  ResMap<Pose, Edge> pemap_;",
        "ResMap<Edge, Pose> epmap_;  ResMap<Edge, Edge> eemap_;",
    ], title="The definition", size=11.5)
    # entity ids
    ents = [("0", "BAY_ODP", "overdrive-plate area (bay poses only)"), ("1", "TRAY_LEGS", "tray on the floor"),
            ("2", "TRAY", "tray"), ("3", "AGV", "AGV"), ("4, 5, ...", "PAYLOAD", "one per parking window (+ index)")]
    ex = code.x1 + 40
    d.text(ex, 8, "Entity ids (CollisionEntityId; table index)", size=13, weight=600, fill=CT)
    for i, (n, name, what) in enumerate(ents):
        y = 36 + i * 26
        d.rect(ex, y - 11, 430, 22, rx=4, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        d.text(ex + 10, y, n, size=11.5, family="mono", fill=T.fg)
        d.text(ex + 90, y, name, size=11.5, family="mono", fill=CT)
        d.text(ex + 200, y, what, size=11.5, fill=T.fg2)
    # nested lookup chain
    top = code.y1 + 50
    d.text(0, top, "One lookup: Query(TRAY, AGV, {node_id: 18, heading: 90}, {node_id: 22, heading: 90})", size=13, weight=600, fill=T.fg)
    levels = [("ppmap_", "ResMap<Pose, Pose>", "4 maps: pick by location kinds"),
              ("[2]", "fixed id = TRAY", "unordered_map<Pose, ...>"),
              ("[{node_id: 18, heading: 90}]", "fixed pose", "unordered_map<size_t, ...>"),
              ("[3]", "queried id = AGV", "unordered_set<Pose>"),
              ("contains {node_id: 22, heading: 90}?", "queried pose", "true = conflict")]
    x = 0
    bw, gap = 222, 30
    for i, (k, a, b) in enumerate(levels):
        bx = x + i * (bw + gap)
        col = CT if i < 4 else T.red
        d.rect(bx, top + 20, bw, 70, rx=8, fill=T.tint(col, 0.08, T.bg), stroke=T.tint(col, 0.6, T.bg), sw=1.3)
        d.text(bx + 12, top + 42, k, size=12.5, family="mono", weight=700, fill=col)
        d.text(bx + 12, top + 62, a, size=11, fill=T.fg2)
        d.text(bx + 12, top + 79, b, size=10.5, family="mono", fill=T.muted)
        if i:
            connect(d, [(bx - gap, top + 55), (bx, top + 55)], kind="flow", color=T.faint, size=8)
    by = top + 120
    build = code_panel(d, 0, by, 700, [
        "// CollisionTable::BuildTable(gg): every pair, once per layout",
        "for v in gg.GetVertices():                         // fixed pose",
        "  for fixed in entity ids:                         // BAY_ODP only at bay nodes",
        "    for queried in entity ids (from 1):",
        "      for w in gg.GetVertices():                   // queried pose, same floor (or VRC)",
        "        if circles overlap && polygons intersect:",
        "          ppmap_[fixed][pose(v)][queried].insert(pose(w))",
        "          ppmap_[queried][pose(w)][fixed].insert(pose(v))   // and the reverse",
        "      for e in gg.GetEdges(): ... pemap_ / epmap_  // edge = convex hull of both ends",
        "    ... eemap_ for edge vs edge",
    ], title="How it is filled", size=11.5)
    nb = note(d, build.x1 + 40, by, 520,
              "The constructor first tries LoadTable() from ~/.cache/volley/<layout name>_collision_table_<md5>.json; "
              "only when that fails does it run BuildTable() (vertices x vertices x entity pairs) and SaveTable(). "
              "The key is the layout's name and md5, so editing the YAML forces a rebuild, but a change to the "
              "footprint code alone does not: delete the cache file after changing collision geometry. "
              "Keys are poses and edges, not Vertex numbers, and a pose and its reciprocal are stored separately "
              "(a TODO in BuildTable).", title="Built once, cached on disk", accent=CT)
    frame(d, title="CollisionTable: precomputed conflict sets",
          subtitle="Nothing is computed geometrically during planning. Query looks up, for a fixed entity type at a "
                   "fixed pose or edge, the set of poses (or edges) where an entity of the queried type would "
                   "overlap it. The bool overloads test one location; the others return the whole set.",
          badge_key="as-built",
          legend=[("box", CT, "map level"), ("box", T.red, "answer")],
          footnote="From collision_geometry.hpp/.cpp. The lookup example shows the path through the maps; whether "
                   "that particular pair conflicts depends on the footprint sizes in `common`, not in the snapshots.")
    return d


# ======================================================================================
# 78 — heading convention
# ======================================================================================

def _rect_at(d, cx, cy, h, L, Wd, color, *, fill_alpha=0.12, label=None):
    """Footprint rectangle centred at (cx, cy), long side along heading h (0 = up, CCW+)."""
    a = math.radians(h)
    fx, fy = -math.sin(a), -math.cos(a)        # forward in SVG space
    sx, sy = -fy, fx                            # sideways
    pts = []
    for u, v in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        pts.append((cx + fx * L / 2 * u + sx * Wd / 2 * v, cy + fy * L / 2 * u + sy * Wd / 2 * v))
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    d.path(path, fill=T.tint(color, fill_alpha, T.bg), stroke=color, sw=1.6)
    tip = (cx + fx * L * 0.42, cy + fy * L * 0.42)
    d.line(cx, cy, tip[0] - fx * 6, tip[1] - fy * 6, stroke=color, sw=2.4, layer="top")
    d.arrowhead(tip, (cx, cy), kind="filled", color=color, size=9, layer="top")
    if label:
        d.text(cx, cy + 2, label, size=11, family="mono", weight=700, fill=T.fg, anchor="middle", halo=T.bg, halo_w=3,
               layer="top")


@figure("78_heading_convention", "Headings: what the number means", DOC1)
def heading_convention():
    d = Doc("78_heading_convention", "Headings: what the number means",
            "GaragePose.heading is an integer in degrees, 0 along +y, counter-clockwise positive, so 90 points to -x. "
            "A YAML node lists headings in 0..179; each also allows its reciprocal, which covers the same footprint.")
    # ---- compass ----
    cx, cy, R = 190, 210, 130
    d.circle(cx, cy, R, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    d.line(cx - R - 26, cy, cx + R + 26, cy, stroke=T.faint, sw=1)
    d.line(cx, cy + R + 26, cx, cy - R - 26, stroke=T.faint, sw=1)
    d.arrowhead((cx + R + 30, cy), (cx, cy), kind="filled", color=T.faint, size=8)
    d.arrowhead((cx, cy - R - 30), (cx, cy), kind="filled", color=T.faint, size=8)
    d.text(cx + R + 36, cy, "+x", size=12, family="mono", fill=T.muted)
    d.text(cx + 8, cy - R - 34, "+y", size=12, family="mono", fill=T.muted)
    for h, lab in ((0, "0"), (90, "90"), (180, "180"), (-90, "-90")):
        a = math.radians(h)
        fx, fy = -math.sin(a), -math.cos(a)
        tip = (cx + fx * (R - 14), cy + fy * (R - 14))
        d.line(cx, cy, tip[0] - fx * 8, tip[1] - fy * 8, stroke=T.green, sw=2.4)
        d.arrowhead(tip, (cx, cy), kind="filled", color=T.green, size=10)
        lx, ly = cx + fx * (R + 0) + (-18 if h == 90 else 22 if h == -90 else 14), cy + fy * (R - 2) + (16 if h == 180 else -6 if h == 0 else 14)
        d.text(lx, ly, lab, size=13, family="mono", weight=700, fill=T.fg, anchor="middle", halo=T.bg, halo_w=3)
    d.path(f"M{cx + 46:.1f} {cy - 38:.1f} A 60 60 0 0 0 {cx - 38:.1f} {cy - 46:.1f}", stroke=T.pink, sw=1.8)
    d.arrowhead((cx - 40, cy - 45), (cx - 20, cy - 58), kind="filled", color=T.pink, size=8)
    d.text(cx + 50, cy - 64, "CCW +", size=11, family="mono", fill=T.pink)
    d.text(cx, cy + R + 52, "GaragePoseMsg.heading: int16, degrees in [-179, 180]", size=12, family="mono", fill=T.fg2, anchor="middle")
    d.text(cx, cy + R + 70, "270 is never stored: Wrap(270) = -90.  yaw = heading x pi / 180", size=11, family="mono",
           fill=T.muted, anchor="middle")

    # ---- reciprocal: same footprint ----
    px = 470
    d.text(px, 40, "h and its reciprocal: same footprint, opposite facing", size=14, weight=600, fill=T.fg)
    for i, (h, col) in enumerate(((90, T.amber), (-90, T.amber))):
        bx = px + 40 + i * 230
        d.rect(bx - 90, 70, 180, 150, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
        d.circle(bx, 145, 3, fill=T.fg2)
        _rect_at(d, bx, 145, h, 124, 52, col)
        d.text(bx, 240, f"{{node_id: 22, heading: {h}}}", size=12, family="mono", fill=T.fg2, anchor="middle")
        d.text(bx, 258, "faces -x" if h == 90 else "faces +x", size=11, fill=T.muted, anchor="middle")
    d.text(px, 290, "The long side lies along the heading. A centred rectangle covers the same floor at h and h + 180,",
           size=11.5, fill=T.fg2)
    d.text(px, 308, "so every allowed heading comes with its reciprocal; only the facing differs (which way a car",
           size=11.5, fill=T.fg2)
    d.text(px, 326, "on the tray points, and where the AGV's front is).", size=11.5, fill=T.fg2)

    # ---- from YAML headings to poses ----
    ty = 370
    d.text(px, ty, "From the YAML to poses (GetAllowedHeadings)", size=14, weight=600, fill=T.fg)
    rows = [("W22", "headings: [0, 90]", "-90, 0, 90, 180", "4 poses, rotation_allowed: true"),
            ("P23", "headings: [90]", "-90, 90", "2 poses, no rotation"),
            ("B21", "headings: [90]", "-90, 90", "2 poses; inbound heading -90 (faces_reciprocal: true)")]
    for i, (n, yml, poses, note_) in enumerate(rows):
        y = ty + 30 + i * 30
        d.rect(px, y - 13, 760, 26, rx=4, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        d.text(px + 10, y, n, size=12, family="mono", weight=700, fill=LAY)
        d.text(px + 70, y, yml, size=12, family="mono", fill=T.fg2)
        d.text(px + 250, y, "->", size=12, family="mono", fill=T.faint)
        d.text(px + 285, y, poses, size=12, family="mono", fill=T.green)
        d.text(px + 450, y, note_, size=11.5, fill=T.muted)
    frame(d, title="Headings: what the number means",
          subtitle="A heading is the direction a pose faces, in whole degrees: 0 along +y, counter-clockwise positive, "
                   "so 90 faces -x (west) and -90 faces +x. It is an int16 in [-179, 180] in GaragePoseMsg; "
                   "GeometricPoseMsg carries the same angle as yaw in radians.",
          badge_key="as-built",
          legend=[("box", T.green, "heading arrow"), ("box", T.amber, "tray footprint"), ("box", LAY, "YAML node")],
          footnote="Convention from GaragePose.msg's comment and LocomoteOrStrafe in garage_graph.cpp; yaw from "
                   "Layout::GetGeometricPoseAtPose; range [-179, 180] from GaragePose.msg. YAML and GarageNode.headings use 0..179.")
    return d


# ======================================================================================
# 79 — node, pose, vertex: one place, four names
# ======================================================================================

@figure("79_node_pose_vertex", "Node, pose, vertex", DOC1)
def node_pose_vertex():
    d = Doc("79_node_pose_vertex", "Node, pose, vertex: one place, several names",
            "W22 as a Layout node, as four poses, as four GarageGraph vertices, and as the keys other structures use.")
    cols = [("node", "a place", "GarageNodeMsg  (Layout::nodes_)", LAY),
            ("pose", "a place + a heading", "GaragePoseMsg  {node_id, heading}", PG),
            ("vertex", "a pose's index in gg_", "GarageGraph::Vertex  (std::size_t)", GG)]
    cw, gap = 400, 70
    top = 0
    for i, (word, what, typ, col) in enumerate(cols):
        x = i * (cw + gap)
        d.rect(x, top, cw, 70, rx=10, fill=T.tint(col, 0.10, T.bg), stroke=col, sw=1.5)
        d.text(x + 16, top + 24, word, size=18, weight=600, fill=col)
        d.text(x + 16 + text_width(word, 18, "sans", 600) + 10, top + 24, f"= {what}", size=13, fill=T.fg2)
        d.text(x + 16, top + 50, typ, size=11.5, family="mono", fill=T.fg2)
        if i:
            connect(d, [(x - gap, top + 35), (x, top + 35)], kind="flow", color=T.faint, size=9)
    d.text(cw + gap / 2, top + 88, "x allowed headings", size=10.5, family="mono", fill=T.muted, anchor="middle")
    d.text(2 * cw + 1.5 * gap, top + 88, "pose_to_vertex_", size=10.5, family="mono", fill=T.muted, anchor="middle")
    # pictures
    py = top + 120
    # node
    x0 = 0
    d.rect(x0, py, cw, 230, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    ncx, ncy = x0 + cw / 2, py + 70
    d.circle(ncx, ncy, 9, fill=LAY)
    d.text(ncx, ncy + 26, "W22", size=13, family="mono", weight=700, fill=LAY, anchor="middle")
    for ln_i, ln in enumerate(["GarageNodeMsg {id: 22,", "  x: 30.88, y: 21.74,   // metres",
                                "  type: TYPE_WAYPOINT, headings: [0, 90],", "  rotation_allowed: true, ...}"]):
        d.text(x0 + 24, py + 150 + ln_i * 18, ln, size=11, family="mono", fill=T.fg2)
    # poses
    x1 = cw + gap
    d.rect(x1, py, cw, 230, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    pcx, pcy = x1 + cw / 2, py + 100
    d.circle(pcx, pcy, 4, fill=T.faint)
    pcx = x1 + 80
    d.circle(pcx, pcy, 4, fill=T.faint)
    for k, h in enumerate((-90, 0, 90, 180)):
        a = math.radians(h)
        fx, fy = -math.sin(a), -math.cos(a)
        qx, qy = pcx + fx * 44, pcy + fy * 44
        d.circle(qx, qy, 13, fill=T.card, stroke=PG, sw=1.6)
        _arrow_glyph(d, qx, qy, h, PG, r=9)
        d.text(qx + fx * 26, qy + fy * 22, str(h), size=9.5, family="mono", fill=T.muted, anchor="middle")
        d.text(x1 + 160, py + 50 + k * 34, f"{{node_id: 22, heading: {h}}}", size=11, family="mono", fill=T.fg2)
    d.text(pcx, py + 214, "same place, four headings", size=11, fill=T.muted, anchor="middle")
    # vertices
    x2 = 2 * (cw + gap)
    d.rect(x2, py, cw, 230, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1)
    for k, h in enumerate((-90, 0, 90, 180)):
        yy = py + 30 + k * 40
        d.rect(x2 + 40, yy, 60, 30, rx=4, fill=T.tint(GG, 0.16, T.bg), stroke=GG, sw=1.2)
        d.text(x2 + 70, yy + 15, str(VERT[(22, h)]), size=14, family="mono", weight=700, fill=T.fg, anchor="middle")
        if k == 0:
            d.text(x2 + 40, yy - 12, "Vertex   base_graph_[Vertex]", size=10.5, family="mono", fill=T.muted)
        d.text(x2 + 116, yy + 15, f"= {{node_id: 22, heading: {h}}}", size=11, family="mono", fill=T.fg2)
    d.text(x2 + cw / 2, py + 214, "four numbers; nothing else stored here", size=11, fill=T.muted, anchor="middle")
    # other names for the same place
    oy = py + 270
    d.text(0, oy, "The same place under other names", size=14, weight=600, fill=T.fg)
    others = [("GeometricPoseMsg", "{x: 30.88, y: 21.74, yaw: 1.571}   // yaw of heading 90", "metres and radians, for geometry and motion", T.sky),
              ("SizedPoseMsg", "{resource_size_index: 4, pose: {node_id: 22, heading: 90}}", "a pose plus a footprint size", PG),
              ("CollisionTable location", "Pose {node_id: 22, heading: 90}  or  Edge {pose, pose} (a move)", "a pose, or a move between two", CT),
              ("layout graph_ vertex", "20  (W22's position in Layout::nodes_)", "not the node id and not a gg_ vertex", LAY),
              ("pose index", "PoseGraph::GetPoseIndex({node_id: 22, heading: 90}) = 44", "equals the gg_ Vertex by construction", PG)]
    for i, (name, ex, what, col) in enumerate(others):
        y = oy + 30 + i * 28
        d.rect(0, y - 13, x2 + cw, 26, rx=4, fill=T.card if i % 2 else T.tint(T.card, 0.6, T.bg))
        d.text(12, y, name, size=12, family="mono", weight=600, fill=col)
        d.text(250, y, ex, size=12, family="mono", fill=T.fg2)
        d.text(820, y, what, size=11.5, fill=T.muted)
    frame(d, title="Node, pose, vertex: one place, several names",
          subtitle="A node is a place in the layout. A pose is that place plus a heading. A vertex is the number gg_ "
                   "gives one pose. W22 is one node, four poses and four vertices; the arrows are the only conversions "
                   "the code performs (GetAllowedHeadings, then GetVertexFromPose).",
          badge_key="yaml",
          legend=[("box", LAY, "Layout"), ("box", PG, "pose"), ("box", GG, "GarageGraph"), ("box", CT, "CollisionTable")],
          footnote="Values from the Pecos YAML; vertex numbers recomputed with the PoseGraph rules. Size index 4 = XL: "
                   "windows sorted by area are TRAY, COMPACT, STANDARD, LARGE, XL.")
    return d


# ======================================================================================
# 80 — asset types
# ======================================================================================

def _icon(d, kind, x, y, col):
    """Small pictogram centred at (x, y)."""
    if kind == "agv":
        d.rect(x - 26, y - 14, 52, 28, rx=6, fill=T.tint(col, 0.2, T.bg), stroke=col, sw=1.6)
        for dx in (-18, 10):
            d.rect(x + dx, y - 18, 8, 4, rx=1, fill=col)
            d.rect(x + dx, y + 14, 8, 4, rx=1, fill=col)
        d.line(x - 8, y, x + 12, y, stroke=col, sw=2)
        d.arrowhead((x + 16, y), (x, y), kind="filled", color=col, size=7)
    elif kind == "tray":
        d.rect(x - 30, y - 13, 60, 26, rx=3, fill=T.tint(col, 0.15, T.bg), stroke=col, sw=1.6)
        for dx in (-30, 26):
            for dy in (-13, 9):
                d.rect(x + dx, y + dy, 4, 4, fill=col)
    elif kind == "payload":
        d.rect(x - 28, y - 11, 56, 22, rx=9, fill=T.tint(col, 0.2, T.bg), stroke=col, sw=1.6)
        d.rect(x - 12, y - 7, 18, 14, rx=3, fill="none", stroke=col, sw=1.2)
    elif kind == "bay":
        d.path(f"M{x - 26} {y - 16} L{x + 26} {y - 16} L{x + 26} {y + 16} L{x - 26} {y + 16}", stroke=col, sw=2)
        d.line(x - 26, y - 16, x - 26, y - 6, stroke=col, sw=2)
        d.line(x - 26, y + 6, x - 26, y + 16, stroke=col, sw=2)
        d.text(x + 4, y + 1, "door", size=9, fill=col, anchor="middle")
    elif kind == "vecs":
        d.circle(x, y, 15, fill=T.tint(col, 0.15, T.bg), stroke=col, sw=1.6)
        d.path(f"M{x + 2} {y - 10} L{x - 5} {y + 1} L{x + 1} {y + 1} L{x - 2} {y + 10} L{x + 6} {y - 2} L{x} {y - 2} Z",
               fill=col)
    elif kind == "vrc":
        d.rect(x - 18, y - 18, 36, 36, rx=4, fill=T.tint(col, 0.15, T.bg), stroke=col, sw=1.6)
        d.line(x, y - 10, x, y + 10, stroke=col, sw=1.6)
        d.arrowhead((x, y - 13), (x, y), kind="filled", color=col, size=6)
        d.arrowhead((x, y + 13), (x, y), kind="filled", color=col, size=6)


@figure("80_asset_types", "Asset types", DOC1)
def asset_types():
    d = Doc("80_asset_types", "Asset types: what the scheduler plans for",
            "The six kinds of physical asset in the garage: how each is identified, which message holds its state, "
            "where it sits, which event changes it in the plan, which command executes it, and its footprint id.")
    assets = [
        ("agv", "AGV", T.green, "moves; carries one tray", [
            ("id", "uint16 · GarageEntityId {entity_type: 'a', id}"),
            ("state", "DiscreteAgvState {id, state, pose, lift, tray_id, disabled}"),
            ("sits on", "any pose; charges on TYPE_AGV_CHARGE (5)"),
            ("plan event", "AgvMove (pose or lift change)"),
            ("command", "ActionNode TYPE_AGV_COMMAND · AgvCommand {src, dst: AgvGoal}"),
            ("footprint", "CollisionEntityId AGV (3); loaded = its tray's id")]),
        ("tray", "tray", T.amber, "carried by an AGV; holds 0 or 1 payload", [
            ("id", "uint16 · GarageEntityId {entity_type: 't', id}"),
            ("state", "DiscreteTrayState {id, pose, agv_id, payload_id, disabled}"),
            ("sits on", "parking, bay or EV-charge nodes (any pose)"),
            ("plan event", "TrayMove (tray id, destination, AGV)"),
            ("command", "none of its own: AGV commands move it"),
            ("footprint", "TRAY (2) on an AGV, TRAY_LEGS (1) on the floor")]),
        ("payload", "payload (car)", T.pink, "rides on a tray", [
            ("id", "Guid (16 bytes) · no GarageEntityId"),
            ("state", "DiscretePayloadState {payload, tray_id, reciprocal_to_tray, charging}"),
            ("sits on", "a tray; Payload has mass and length/width/height_m"),
            ("plan event", "none: moves with its tray; PROCESS_RETRIEVE removes it"),
            ("command", "none"),
            ("footprint", "PAYLOAD + smallest parking window that fits")]),
        ("bay", "bay", T.violet, "where customers insert and retrieve cars", [
            ("id", "uint16 = its node_id · GarageEntityId {entity_type: 'b', id}"),
            ("state", "DiscreteBayState {id, state (BayReport STATE_*), disabled}"),
            ("sits on", "is a node: TYPE_BAY (4) or TYPE_BLIFT (7)"),
            ("plan event", "BayTransition (BayCommand from a given bay state)"),
            ("command", "ActionNode TYPE_BAY_COMMAND · BayCommand {command_type, floor}"),
            ("footprint", "BAY_ODP (0), at bay poses only")]),
        ("vecs", "VECS (EV charger)", T.sky, "charges a payload's battery", [
            ("id", "uint16 = its node_id · GarageEntityId {entity_type: 'v', id}"),
            ("state", "DiscreteVecsState {id, state (VecsReport), disabled}"),
            ("sits on", "is a node: TYPE_EV_CHARGE (6)"),
            ("plan event", "VecsTransition (state_curr -> state_next)"),
            ("command", "ActionNode TYPE_VECS_COMMAND · VecsCommand START/STOP_CHARGING"),
            ("footprint", "none")]),
        ("vrc", "VRC (vehicle lift)", T.teal, "moves an AGV between floors", [
            ("id", "uint16 · GarageEntityId {entity_type: 'r', id}"),
            ("state", "DiscreteVrcState {id, state, gates, current_floor, requested_floor}"),
            ("sits on", "a stack of TYPE_LIFT (3) nodes, one per floor"),
            ("plan event", "VrcTransition exists; the scheduler never creates one"),
            ("command", "ActionNode TYPE_VRC_COMMAND · VrcCommand {requested_floor}"),
            ("footprint", "none of its own")]),
    ]
    cw, ch, gx, gy = 560, 236, 26, 24
    for i, (kind, name, col, what, rows) in enumerate(assets):
        x = (i % 2) * (cw + gx)
        y = (i // 2) * (ch + gy)
        d.rect(x, y, cw, ch, rx=10, fill=T.card, stroke=T.tint(col, 0.7, T.bg), sw=1.5)
        _icon(d, kind, x + 46, y + 40, col)
        d.text(x + 92, y + 32, name, size=16, weight=600, fill=col)
        d.text(x + 92, y + 52, what, size=11.5, fill=T.muted)
        for k, (lab, val) in enumerate(rows):
            yy = y + 86 + k * 24
            d.text(x + 18, yy, lab, size=10.5, family="mono", weight=600, fill=T.faint)
            d.text(x + 104, yy, val, size=11, family="mono", fill=T.fg2)
    yb = 3 * (ch + gy) + 6
    note(d, 0, yb, 2 * cw + gx,
         "All six live in DiscreteGarageState (agvs, trays, payloads, bays, vexen, vrcs). Fixed assets (bay, VECS, "
         "VRC) are also layout nodes; mobile ones (AGV, tray, payload) are not: they have a pose. GarageEntityId "
         "{entity_type, id} is how last_entity_event and ActionNode bookkeeping name an asset; 's' (system) also exists.",
         title="Where they meet", accent=T.fg2)
    frame(d, title="Asset types: what the scheduler plans for",
          subtitle="Six kinds of physical asset. Three move (AGV, tray, payload) and three are fixed in the layout "
                   "(bay, VECS, VRC). Each row says which type in the code stands for that asset.",
          badge_key="as-built",
          legend=[("box", T.green, "AGV"), ("box", T.amber, "tray"), ("box", T.pink, "payload"),
                  ("box", T.violet, "bay"), ("box", T.sky, "VECS"), ("box", T.teal, "VRC")],
          footnote="From interfaces/msg (Discrete*State, GarageEntityId, ActionNode, *Command, GarageNode), "
                   "common_ros (AgvId/TrayId/BayId/VecsId/VrcId, CollisionEntityId) and planner_core (event classes).")
    return d
