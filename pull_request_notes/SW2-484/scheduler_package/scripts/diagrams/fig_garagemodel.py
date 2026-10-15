"""The static garage model (doc 01, "The garage model in code"): Layout, PoseGraph, GarageGraph and
CollisionTable as data structures, from sources/repomix-common-ros.xml.

Pose indices / vertex numbers are computed from the Pecos YAML with the PoseGraph rules
(nodes in id order, headings sorted, each YAML heading h plus h + 180). Headings are written 0-359;
volley::Wrap's exact range lives in the `common` package, which is not in the snapshots.
"""
from __future__ import annotations

import math

import yaml

from components import code_panel, connect, frame, label_pill, note, uml_class
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


def allowed(nid):
    return sorted({(h + d) % 360 for h in _NODES[nid]["headings"] for d in (0, 180)})


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
    yb = max(gg.y1, ct.y1) + 30
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
                  ("box", CT, "space"), ("assoc", T.fg2, "holds"), ("dep", T.fg2, "built from")],
          footnote="From sources/repomix-common-ros.xml: layout.hpp, pose_graph.hpp, garage_graph.hpp, "
                   "collision_geometry.hpp. Private members abridged; types as declared.")
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
        "    boost::vecS,             // each vertex's out-edges: a std::vector",
        "    boost::vecS,             // the vertices: a std::vector  -> Vertex is an index",
        "    boost::bidirectionalS,   // also keep in-edges (GetInEdges)",
        "    GaragePoseMsg,           // bundled vertex property: the pose",
        "    boost::property<boost::edge_index_t, std::size_t, Transition>>;  // edge: index + Transition",
        "",
        "class GarageGraph {",
        "  using Vertex = BoostPoseGraph::vertex_descriptor;  // std::size_t, 0 .. NumVertices()-1",
        "  using Edge   = BoostPoseGraph::edge_descriptor;    // {m_source, m_target, property pointer}",
        "  BoostPoseGraph base_graph_;",
        "  std::unordered_map<GaragePoseMsg, Vertex> pose_to_vertex_;  // hash of (node_id, heading)",
        "};",
        "struct Transition { double length;  TransitionType type; };  // LOCOMOTE, STRAFE, ROTATION, VRC_TRANSITION",
    ], title="The definition", size=11.5)
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
        offs = ({0: (0, -36), 90: (-36, 0), 180: (0, 36), 270: (36, 0)} if len(hs) == 4
                else {90: (-24, -24), 270: (24, -24)})
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
            d.text(lx, ly, str(VERT[(nid, h)]), size=10.5, family="mono", weight=700,
                   fill=T.fg if nid == 22 else T.fg2, anchor="middle", halo=T.bg_deep, halo_w=3, layer="top")
    mb = m.box
    d.text(mb.x0, mb.y1 + 18, "Pecos, around W22: one ring per vertex (arrow = heading), number = Vertex.",
           size=11, fill=T.muted)
    d.text(mb.x0, mb.y1 + 34, f"Whole layout: {len(_NODES)} nodes -> {len(POSES)} vertices, {N_EDGES} directed edges "
                              f"({N_ROT} rotations).", size=11, fill=T.muted)

    # ---- bottom: the three storage structures ----
    top = max(code.y1, mb.y1 + 40) + 40
    hrows = [("{18, 90}", "34"), ("{18, 270}", "35"), ("{22, 0}", "42"), ("{22, 90}", "43"), ("{22, 180}", "44"),
             ("{22, 270}", "45"), ("{23, 90}", "46"), None, ("{41, 90}", "58")]
    t1 = _table(d, 0, top, 300, "pose_to_vertex_", "unordered_map<GaragePoseMsg, Vertex>",
                hrows, [("key: {node_id, heading}", 10), ("Vertex", 220)], GG, hl=(3,))
    v43 = out_edges((22, 90))
    vrows = []
    for v in (34, 42, 43, 44, 45, 46):
        p = POSES[v]
        outs = out_edges(p)
        ins = [q for q in POSES if any(t == p for t, _ in out_edges(q))]
        vrows.append((str(v), f"{{{p[0]}, {p[1]}}}", ", ".join(str(VERT[t]) for t, _ in outs),
                      ", ".join(str(VERT[q]) for q in ins)))
    vrows.insert(1, None)
    t2 = _table(d, t1.x1 + 40, top, 540, "base_graph_ vertices", "std::vector: index = Vertex; stored per vertex",
                vrows, [("Vertex", 10), ("bundle (pose)", 80), ("out_edges -> targets", 200), ("in_edges <- sources", 380)],
                GG, hl=(3,))
    erows = []
    for tgt, _ in v43:
        kind, length = transition((22, 90), tgt)
        erows.append((f"43 -> {VERT[tgt]}", f"{{{tgt[0]}, {tgt[1]}}}", kind, length))
    t3 = _table(d, t2.x1 + 40, top, 470, "edges out of vertex 43", "Edge = (source, target) + Transition{type, length}",
                erows, [("edge", 10), ("target pose", 110), ("Transition.type", 230), ("length", 370)], T.violet)
    # lookup arrows
    connect(d, [(t1.x1, t1.y0 + 34 + 22 + 3 * 22 + 11), (t2.x0, t2.y0 + 34 + 22 + 3 * 22 + 11)], kind="flow",
            color=GG, size=8)
    connect(d, [(t2.x1, t2.y0 + 34 + 22 + 3 * 22 + 11), (t3.x0, t3.y0 + 34 + 22 + 11)], kind="flow", color=T.violet,
            size=8)
    yb = max(t1.y1, t2.y1, t3.y1) + 28
    steps = [
        ("gg_.GetVertexFromPose({22, 90})", "hash lookup in pose_to_vertex_ -> 43; an unknown node or heading -> nullopt"),
        ("gg_.GetPoseFromVertex(43)", "index into base_graph_'s vertex vector -> {22, 90}; 43 >= NumVertices() -> nullopt"),
        ("gg_.GetOutEdges(43)", "iterator pair over that vertex's out-edge vector (throws std::invalid_argument if invalid)"),
        ("gg_.GarageNodeFromVertex(43)", "pose.node_id -> layout_->GetNodeById(22): a std::map lookup and a copy of the node"),
    ]
    w = t3.x1
    d.text(0, yb, "Reading the structure", size=13, weight=600, fill=T.fg)
    for i, (call, what) in enumerate(steps):
        y = yb + 22 + i * 24
        d.text(0, y, call, size=11.5, family="mono", fill=GG)
        d.text(330, y, what, size=11.5, fill=T.fg2)
    frame(d, title="What a GarageGraph Vertex is",
          subtitle="Vertex is BoostPoseGraph::vertex_descriptor: with vecS storage, a plain std::size_t index into "
                   "the graph's vertex vector. The pose lives in that vector entry; pose_to_vertex_ is the reverse "
                   "map. Vertex 43 is the pose {22, 90}; W22 lists headings 0 and 90, so it owns four vertices (42-45).",
          badge_key="yaml",
          legend=[("ring", GG, "vertex (arrow = heading)"), ("box", GG, "GarageGraph storage"),
                  ("box", T.violet, "edge records")],
          footnote="Vertex numbers and edges recomputed from the Pecos YAML with the PoseGraph rules "
                   "(nodes by id, headings ascending, h and h+180). Out-edge order inside Boost is insertion order, "
                   "which follows the neighbour slots; the lists here are sorted. Headings shown 0-359 "
                   "(volley::Wrap is in `common`, not in the snapshots).")
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
    ents = [("0", "BAY_ODP", "bay door area (only at bay poses)"), ("1", "TRAY_LEGS", "tray on the floor"),
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
    d.text(0, top, "One lookup: Query(TRAY, AGV, {18, 90}, {22, 90})", size=13, weight=600, fill=T.fg)
    levels = [("ppmap_", "ResMap<Pose, Pose>", "4 maps: pick by location kinds"),
              ("[2]", "fixed id = TRAY", "unordered_map<Pose, ...>"),
              ("[{18, 90}]", "fixed pose", "unordered_map<size_t, ...>"),
              ("[3]", "queried id = AGV", "unordered_set<Pose>"),
              ("contains {22, 90}?", "queried pose", "true = conflict")]
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
