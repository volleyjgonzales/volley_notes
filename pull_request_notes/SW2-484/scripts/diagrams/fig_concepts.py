"""Concept figures: Layout vs GarageGraph, the CollisionTable, and topological ordering.

The internals of Layout, PoseGraph, GarageGraph and CollisionTable live in common_ros (not in the
snapshot). What these figures state as fact is limited to what the scheduler code shows: the
constructor chain, the methods it calls and what it passes. Graph construction details and the
table's storage are drawn as concepts and labelled as such.
"""
from __future__ import annotations

import math

from components import (EVENT_COLOR, chip, code_panel, connect, frame, label_pill, note, num_badge)
from facility import Map, NODES, EDGES, STALL_L, STALL_W, C_BAY
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC1 = "01-software-background.md"
W = 1120
TRAY, AGV, BAYC = T.amber, T.green, T.violet


def _heading_vec(h):
    """GaragePose heading in degrees, +CCW from north; 90 = west. Returns unit (dx, dy) in SVG space."""
    a = math.radians(h)
    return -math.sin(a), -math.cos(a)


def _arrow_glyph(d, x, y, h, color, r=9):
    dx, dy = _heading_vec(h)
    tip = (x + dx * r * 0.75, y + dy * r * 0.75)
    tail = (x - dx * r * 0.6, y - dy * r * 0.6)
    d.line(tail[0], tail[1], tip[0] - dx * 3, tip[1] - dy * 3, stroke=color, sw=2, layer="top")
    d.arrowhead(tip, tail, kind="filled", color=color, size=6, layer="top")


def _card(d, x, y, w, title, lines, accent, *, sub=None, mono=True, size=11.5):
    pad = 14
    body = []
    for ln in lines:
        fam = "mono" if mono else "sans"
        body += [ln] if text_width(ln, size, fam) <= w - 2 * pad else wrap(ln, w - 2 * pad, size, fam)
    sl = wrap(sub, w - 2 * pad, 11, "sans") if sub else []
    h = pad * 2 + 22 + len(sl) * 16 + (6 if sl else 0) + len(body) * (size * 1.5)
    d.rect(x, y, w, h, rx=10, fill=T.tint(accent, 0.06, T.bg), stroke=T.tint(accent, 0.6, T.bg), sw=1.3)
    d.text(x + pad, y + pad + 6, title, size=13, weight=600, fill=accent)
    yy = y + pad + 28
    for ln in sl:
        d.text(x + pad, yy, ln, size=11, fill=T.muted)
        yy += 16
    if sl:
        yy += 6
    for ln in body:
        d.text(x + pad, yy, ln, size=size, family="mono" if mono else "sans", fill=T.fg2)
        yy += size * 1.5
    return BBox(x, y, x + w, y + h)


# ======================================================================================
# 51 — Layout vs PoseGraph / GarageGraph
# ======================================================================================

CROP_X, CROP_Y = (25.6, 40.9), (17.6, 25.4)
SHOW = [41, 22, 25, 26, 18, 23, 19]


@figure("51_layout_vs_garage_graph", "Layout vs GarageGraph", DOC1)
def layout_vs_graph():
    d = Doc("51_layout_vs_garage_graph", "Layout vs GarageGraph",
            "Left: the Layout is the parsed YAML: places, types and facts, keyed by node id. Right: the "
            "GarageGraph is a search graph whose vertices are poses (node + heading) and whose edges are moves.")
    # ---- construction chain (as-built, from the Scheduler constructor) ----
    chain = [("layout file (YAML)", "5675_pecos_combined.yaml", T.fg2),
             ("Layout", "layout_  · LayoutSPtr", T.sky),
             ("PoseGraph", "pg_(layout_)", T.teal),
             ("GarageGraph", "gg_(pg_)", T.green),
             ("CollisionTable", "table_(gg_, logger)", T.amber)]
    bw, gap = 196, 35
    boxes = []
    for i, (t, s, col) in enumerate(chain):
        x = i * (bw + gap)
        d.rect(x, 0, bw, 54, rx=9, fill=T.card, stroke=col, sw=1.4)
        d.text(x + 12, 18, t, size=12.5, weight=600, fill=col)
        d.text(x + 12, 38, s, size=11, family="mono", fill=T.fg2)
        if i:
            connect(d, [(x - gap, 27), (x, 27)], kind="flow", color=T.faint, size=8)
        boxes.append(x)
    d.text(0, 74, "Scheduler::Scheduler(): each member is built from the previous one, once, at start-up. "
                  "InitRetrievalHeadings() then caches a retrieval heading per parking node in gg_.",
           size=11.5, fill=T.muted)

    # ---- left panel: Layout ----
    top = 112
    pw = 540
    s = pw / (CROP_X[1] - CROP_X[0])
    d.text(0, top, "Layout  (layout_)  — places and facts", size=14, weight=600, fill=T.sky)
    m = Map(d, 0, top + 20, s, CROP_X, CROP_Y)
    m.base(labels=True, zones=False, axes=False)
    x22, y22 = m.P(22)
    d.circle(x22, y22, 13, fill="none", stroke=T.sky, sw=2.2, layer="top")
    lb = m.box
    yaml_lines = ["- id: 22", "  x: 30.8823        # metres", "  y: 21.7383", "  type: Waypoint",
                  "  max_resource_size: XL", "  rotation_allowed: true", "  headings: [0, 90]",
                  "  faces_reciprocal: false", "edges:   # among others", "  - {src: 18, dst: 22}",
                  "  - {src: 41, dst: 22}", "  - {src: 22, dst: 25}"]
    yc = _card(d, 0, lb.y1 + 18, pw, "Node W22 as it appears in the YAML", yaml_lines, T.sky,
               sub="Undirected edges between node ids; positions in metres; per-node allowed headings.")
    api = ["layout_->GetNodeById(22)        -> std::optional<GarageNodeMsg>",
           "layout_->GetNodeIdsOfType(TYPE_AGV_CHARGE)",
           "layout_->GetBayInboundHeading(bay) -> heading",
           "layout_->GetBayPrioritization()   -> bay ids",
           "layout_->GetResourceWindow(i)     -> L x W x H",
           "layout_->GetBaySystemFloors(bay), GetName()"]
    ya = _card(d, 0, yc.y1 + 14, pw, "What the scheduler asks it", api, T.sky, size=10.5)

    # ---- right panel: GarageGraph (conceptual expansion) ----
    rx = pw + 40
    rw = W - rx
    d.text(rx, top, "GarageGraph  (gg_)  — poses and moves", size=14, weight=600, fill=T.green)
    gs = rw / (CROP_X[1] - CROP_X[0])
    gm = Map(d, rx, top + 20, gs, CROP_X, CROP_Y)
    gb = gm.box
    d.rect(gb.x0, gb.y0, gb.w, gb.h, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
    # vertex positions: one per (node, heading)
    vpos = {}
    for nid in SHOW:
        n = NODES[nid]
        x, y = gm.P(nid)
        hs = n.headings
        if len(hs) == 1:
            vpos[(nid, hs[0])] = (x, y)
        else:
            vpos[(nid, 90)] = (x, y)
            vpos[(nid, 0)] = (x - 44, y - 50)
    # translation edges between same-heading vertices of adjacent nodes
    for a, b in EDGES:
        if a in SHOW and b in SHOW:
            for h in (0, 90):
                if (a, h) in vpos and (b, h) in vpos:
                    (x0, y0), (x1, y1) = vpos[(a, h)], vpos[(b, h)]
                    d.line(x0, y0, x1, y1, stroke=T.tint(T.green, 0.55, T.bg_deep), sw=2, layer="edges")
        elif (a in SHOW) != (b in SHOW):
            pass
    # rotation edge at W22
    (xa, ya_), (xb, yb) = vpos[(22, 0)], vpos[(22, 90)]
    d.path(f"M{xa:.1f} {ya_:.1f} Q{xa - 4:.1f} {yb + 4:.1f} {xb:.1f} {yb:.1f}", stroke=T.pink, sw=2,
           dash="4 3", layer="edges")
    label_pill(d, xa - 20, ya_, "rotate", color=T.pink, size=10, bg=T.bg_deep, anchor="end")
    for (nid, h), (x, y) in vpos.items():
        col = T.green
        d.circle(x, y, 13, fill=T.card, stroke=col, sw=1.8, layer="over")
        _arrow_glyph(d, x, y, h, col)
        lab = f"({NODES[nid].label},{h})"
        dy = 24 if not (nid == 22 and h == 0) else -24
        if nid == 22 and h == 90:
            dy = 26
        d.text(x, y + dy, lab, size=10, family="mono", fill=T.fg2, anchor="middle", halo=T.bg_deep, halo_w=3)
    gapi = ["gg_.GetVertexFromPose({22, 0})  -> std::optional<Vertex>",
            "gg_.GetPoseFromVertex(v)        -> GaragePoseMsg",
            "gg_.GarageNodeFromVertex(v)     -> layout node",
            "gg_.GetOutEdges(v), gg_.EdgeFromPoses(a, b)",
            "gg_.GetRetrievalHeading(node)   (cached at start-up)",
            "GetPosePath(gg_, from, to, cost_model_), searches"]
    note_lines = ["Vertex = (node, heading). A pose whose heading the",
                  "node does not allow has no vertex: GetVertexFromPose",
                  "returns an empty optional."]
    gc = _card(d, rx, gb.y1 + 18, rw, "What the scheduler asks it", gapi, T.green, size=10.5)
    gn = note(d, rx, gc.y1 + 14, rw,
              "Drawn: one vertex per allowed heading, a move between same-heading poses of adjacent nodes, and a "
              "rotation at W22 (rotation_allowed). The exact rules (reciprocal headings, directed or "
              "disallowed edge orientations, costs) are built by PoseGraph in common_ros and are not in the "
              "snapshot.", title="Conceptual expansion", accent=T.violet)

    # ---- bottom: which structure answers which question ----
    y = max(ya.y1, gn.y1) + 34
    d.text(0, y, "Four structures, four questions", size=14, weight=600, fill=T.fg)
    rows = [("layout_", "Layout", "What is node 22? Where is it? Which bay is preferred? How big may a car be?",
             "static, from YAML", T.sky),
            ("gg_", "GarageGraph", "Is pose (22, 0) allowed? Which poses can I move to from here? Path from A to B?",
             "static, derived", T.green),
            ("table_", "CollisionTable", "Would footprint A at pose a overlap footprint B at pose b?",
             "static, precomputed", T.amber),
            ("working_state", "DiscreteGarageState", "Where is tray 17 now? Which bay is READY_TO_RETRIEVE?",
             "changes every plan", T.violet)]
    yy = y + 20
    for i, (v, t, q, kind, col) in enumerate(rows):
        h = 34
        if i % 2 == 0:
            d.rect(0, yy, W, h, rx=6, fill=T.tint(T.card, 0.55, T.bg), layer="bg")
        d.text(12, yy + h / 2, v, size=12, family="mono", weight=600, fill=col)
        d.text(150, yy + h / 2, t, size=12, fill=T.fg)
        d.text(330, yy + h / 2, q, size=11.5, fill=T.fg2)
        d.text(W - 12, yy + h / 2, kind, size=10.5, family="mono", fill=T.muted, anchor="end")
        yy += h + 2
    frame(d, title="Layout vs GarageGraph",
          subtitle="Both describe the same garage. The Layout answers questions about places (node ids, types, "
                   "positions, bays). The GarageGraph answers questions about motion: its vertices are poses "
                   "(node + heading) and its edges are the moves between them. Searches and paths always run on gg_.",
          badge_key="yaml+concept",
          legend=[("dot", T.sky, "layout node (YAML)"), ("ring", T.green, "graph vertex = pose (arrow = heading)"),
                  ("line", T.green, "move between poses"), ("dash", T.pink, "rotation at a node")])
    return d


# ======================================================================================
# 52 — CollisionTable
# ======================================================================================

TRAY_L, TRAY_W = STALL_L, STALL_W   # schematic tray footprint = XL window


def _foot(node, h, L=TRAY_L, Wd=TRAY_W):
    n = NODES[node]
    if h % 180 == 90:
        return (n.x - L / 2, n.y - Wd / 2, n.x + L / 2, n.y + Wd / 2)
    return (n.x - Wd / 2, n.y - L / 2, n.x + Wd / 2, n.y + L / 2)


def _overlap(a, b, eps=0.05):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def _draw_foot(d, m, f, color, *, dash=None, fill_a=0.14, sw=2):
    x0, y1 = m.P((f[0], f[1]))
    x1, y0 = m.P((f[2], f[3]))
    d.rect(x0, y0, x1 - x0, y1 - y0, rx=6, fill=T.tint(color, fill_a, T.bg_deep), stroke=color, sw=sw, dash=dash,
           layer="main")
    return BBox(x0, y0, x1, y1)


@figure("52_collision_table", "CollisionTable", DOC1)
def collision_table():
    d = Doc("52_collision_table", "CollisionTable: precomputed footprint conflicts",
            "Two example queries on the Pecos map and the idea of a table answered once per pair of footprints and "
            "poses.")
    # ---- left: the map with two queries ----
    cx, cy = (25.4, 37.0), (16.4, 26.0)
    pw = 520
    s = pw / (cx[1] - cx[0])
    d.text(0, -16, "Two queries for a tray carried through W22", size=13, weight=600, fill=T.fg)
    m = Map(d, 0, 0, s, cx, cy)
    m.base(labels=True, zones=False, axes=False)
    m.clip()
    fA = _foot(18, 90)
    _draw_foot(d, m, fA, TRAY, fill_a=0.28)
    fB = _foot(22, 90)
    _draw_foot(d, m, fB, T.green, dash="6 4", fill_a=0.08)
    fC = _foot(22, 0)
    bc = _draw_foot(d, m, fC, T.red, dash="3 3", fill_a=0.06)
    # overlap region A ∩ C
    ox0, oy0, ox1, oy1 = max(fA[0], fC[0]), max(fA[1], fC[1]), min(fA[2], fC[2]), min(fA[3], fC[3])
    X0, Y1 = m.P((ox0, oy0))
    X1, Y0 = m.P((ox1, oy1))
    d.rect(X0, Y0, X1 - X0, Y1 - Y0, fill=T.tint(T.red, 0.55, T.bg_deep), layer="main")
    m.unclip()
    xa, ya = m.P(18)
    chip(d, xa - 150, ya + 34, "parked tray: TRAY @ (W18, 90)", TRAY, size=10.5)
    xb, yb = m.P(22)
    chip(d, xb - 120, yb - 40, "candidate a: (W22, 90)", T.green, size=10.5)
    chip(d, xb + 40, yb - 120, "candidate b: (W22, 0)", T.red, size=10.5)
    mb = m.box
    q = code_panel(d, 0, mb.y1 + 20, pw, [
        "// collision ids: CollisionEntityId_t (here both are tray footprints)",
        "table_.Query(tray_id, tray_id, {18, 90}, {22, 90})  // false: no overlap",
        "table_.Query(tray_id, tray_id, {18, 90}, {22, 0})   // true: they overlap",
    ], title="bool CollisionTable::Query(id_a, id_b, pose_a, pose_b)", size=11)
    q2 = note(d, 0, q.y1 + 14, pw,
              "The same two nodes can conflict or not depending on the headings: a 5.8 m tray turned to heading 0 "
              "at W22 reaches down over W18. That is why the table is keyed by pose (node + heading), not by node.",
              title="Heading matters", accent=T.amber)

    # ---- right: the table idea ----
    rx = pw + 50
    rw = W - rx
    d.text(rx, -16, "Built once, then looked up", size=13, weight=600, fill=T.fg)
    poses = [(41, 90), (22, 90), (22, 0), (18, 90), (25, 90), (23, 90), (19, 90)]
    labs = [f"{NODES[n].label}@{h}" for n, h in poses]
    cell = 44
    lx = rx + 74
    ly = 52
    d.text(rx, 12, "TRAY at pose a  vs  TRAY at pose b", size=11, family="mono", fill=T.muted)
    for j, lab in enumerate(labs):
        d.text(lx + j * cell + cell / 2, ly - 12, lab, size=10, family="mono", fill=T.fg2, anchor="middle")
    for i, lab in enumerate(labs):
        d.text(lx - 8, ly + i * cell + cell / 2, lab, size=10, family="mono", fill=T.fg2, anchor="end")
        for j in range(len(poses)):
            hit = _overlap(_foot(*poses[i]), _foot(*poses[j]))
            col = T.red if hit else T.border_soft
            fill = T.tint(T.red, 0.45 if i != j else 0.25, T.bg) if hit else T.tint(T.card, 0.6, T.bg)
            d.rect(lx + j * cell + 2, ly + i * cell + 2, cell - 4, cell - 4, rx=5, fill=fill,
                   stroke=col if hit else None, sw=1)
            if (labs[i], labs[j]) in (("W18@90", "W22@0"), ("W22@0", "W18@90")):
                d.rect(lx + j * cell, ly + i * cell, cell, cell, rx=6, fill="none", stroke=T.fg, sw=2)
    tb = ly + len(poses) * cell
    d.text(rx, tb + 18, "red = the two footprints overlap (computed here from schematic rectangles)", size=10.5,
           fill=T.muted)
    ids = _card(d, rx, tb + 38, rw, "Which footprint? The collision id", [
        "CollisionEntityId::AGV / TRAY / BAY_ODP",
        "CollisionEntityIdFromAgvState(agv, state, layout)",
        "CollisionEntityIdFromTrayState(tray, state, layout)",
        "CollisionEntityIdFromPayloadState(payload, layout)",
    ], T.amber, sub="An entity's id depends on its state, so the right footprint is used: e.g. the response code "
                    "treats any AGV motion whose id is not plain AGV as a lifted AGV carrying a tray.", size=10.5)

    # ---- bottom: who asks ----
    y = max(q2.y1, ids.y1) + 34
    d.text(0, y, "Who uses it", size=14, weight=600, fill=T.fg)
    uses = [("GetStaticFilter(id, gg_, working_state, table_, ...)",
             "For one entity, mark the graph vertices where it would conflict with what is in working_state (the id "
             "sets passed in are left out). Returns GraphFilterProperties; callers test filters.IsEnabled(vertex).", T.green),
            ("GetDisabledEntitiesFilters(gg_, initial_state, table_)",
             "Once per Plan(), from another package: ctx->disabledness_filters, one GraphFilterProperties per collision id, "
             "reflecting what initial_state marks as disabled.",
             T.violet),
            ("table_.Query(...) in DoTrayAssignments",
             "Does another tray block the root tray's next pose on its critical path?", TRAY),
            ("table_.Query(...) in AgvMatchingEventDeps",
             "Would another AGV at its pose conflict with this AGV at the tray? Then order that AGV first.", AGV)]
    yy = y + 20
    for i, (c, t, col) in enumerate(uses):
        tl = wrap(t, W - 460, 11.5)
        h = 14 + 16 * len(tl)
        if i % 2 == 0:
            d.rect(0, yy, W, h, rx=6, fill=T.tint(T.card, 0.55, T.bg), layer="bg")
        d.text(12, yy + 15, c, size=11, family="mono", fill=col)
        for k, ln in enumerate(tl):
            d.text(440, yy + 15 + 16 * k, ln, size=11.5, fill=T.fg2)
        yy += h + 2
    frame(d, title="CollisionTable: precomputed footprint conflicts",
          subtitle="table_ is built once from gg_ at start-up. Query(id_a, id_b, pose_a, pose_b) answers one "
                   "question: would footprint id_a at pose_a overlap footprint id_b at pose_b? Everything that "
                   "decides 'blocked' or 'in the way' is built on it.",
          badge_key="yaml+concept",
          legend=[("box", TRAY, "parked tray footprint"), ("dashbox", T.green, "candidate pose: free"),
                  ("dashbox", T.red, "candidate pose: conflict"), ("fill", T.tint(T.red, 0.55, T.bg_deep), "overlap")],
          footnote="Footprints use the XL parking window (5.79 x 2.21 m) as a schematic tray size. How the real table "
                   "stores and computes conflicts (footprint shapes, margins, swept volumes) lives in common_ros and "
                   "is not in the snapshot; only the Query signature and the call sites are.")
    return d


# ======================================================================================
# 53 — Topological ordering
# ======================================================================================

EV = {  # id: (kind, text, job, (col, row))
    "a": ("BayTransition", "B21 TO_RETRIEVE", 0, (0, 0)),
    "b": ("TrayMove", "T21 -> ?", 0, (1, 0)),
    "c": ("TrayMove", "T17 -> B21", 0, (2, 0)),
    "d": ("BayTransition", "B21 PROCESS_RETRIEVE", 0, (3, 0)),
    "e": ("TrayMove", "T19 -> P24", 1, (0, 1)),
    "f": ("TrayMove", "T19 -> P23", 2, (1, 1)),
}
EDG = [("a", "b"), ("b", "c"), ("a", "c"), ("c", "d"), ("a", "d"), ("e", "f")]


def _evbox(d, x, y, k, w=210):
    kind, text, job, _ = EV[k]
    col = EVENT_COLOR[kind]
    d.rect(x, y, w, 48, rx=8, fill=T.card, stroke=col, sw=1.4)
    d.circle(x + 2, y + 2, 11, fill=col, layer="top")
    d.text(x + 2, y + 2.5, k, size=12, family="mono", weight=700, fill=T.bg, anchor="middle", layer="top")
    d.text(x + 18, y + 15, f"{kind} · job {job}", size=10.5, family="mono", weight=600, fill=col)
    d.text(x + 12, y + 34, text, size=11.5, family="mono", fill=T.fg)
    return BBox(x, y, x + w, y + 48)


def _order_row(d, x, y, order, title, ok, *, bad=None):
    col = T.green if ok else T.red
    d.text(x, y, title, size=12, weight=600, fill=col)
    cw = 62
    cx = {}
    for i, k in enumerate(order):
        kind = EV[k][0]
        c = EVENT_COLOR[kind]
        xx = x + i * cw
        d.rect(xx, y + 48, 44, 30, rx=6, fill=T.card, stroke=c, sw=1.4)
        d.text(xx + 22, y + 63, k, size=13, family="mono", weight=700, fill=c, anchor="middle")
        d.text(xx + 22, y + 92, str(i), size=10, family="mono", fill=T.muted, anchor="middle")
        cx[k] = xx + 22
    for u, v in EDG:
        x0, x1 = cx[u], cx[v]
        back = x1 < x0
        h = 10 + abs(x1 - x0) * 0.16
        colr = T.red if back else T.tint(T.fg2, 0.7, T.bg)
        yb = y + 46
        d.path(f"M{x0:.1f} {yb} C{x0:.1f} {yb - h:.1f} {x1:.1f} {yb - h:.1f} {x1:.1f} {yb}", stroke=colr,
               sw=2 if back else 1.3, layer="edges", bbox=BBox(min(x0, x1), yb - h, max(x0, x1), yb))
        d.arrowhead((x1, yb), (x1 + (2 if back else -2), yb - 6), kind="filled", color=colr, size=7)
    if bad:
        d.text(x + len(order) * cw + 6, y + 63, bad, size=11, fill=T.red)
    return y + 100


@figure("53_topological_ordering", "Topological ordering", DOC1)
def topological_ordering():
    d = Doc("53_topological_ordering", "Topological ordering",
            "A topological order lists every event so that each edge points forward. Many such orders usually "
            "exist; a cycle makes it impossible.")
    # ---- the DAG ----
    d.text(0, -16, "The event DAG (edges: u -> v means u must finish before v starts)", size=13, weight=600,
           fill=T.fg)
    bw, gx, gy = 210, 62, 92
    pos = {}
    for k, (_, _, _, (c, r)) in EV.items():
        pos[k] = _evbox(d, c * (bw + gx), 56 + r * gy, k, bw)
    def edge(u, v, via=None, lab=None):
        a, b = pos[u], pos[v]
        if via is None:
            pts = [(a.x1, a.cy), (b.x0, b.cy)]
        else:
            pts = [(a.cx + via[0], a.y0), (a.cx + via[0], via[1]), (b.cx + via[2], via[1]), (b.cx + via[2], b.y0)]
        connect(d, pts, kind="flow", color=T.fg2, size=8, sw=1.5, radius=8)
    edge("a", "b")
    edge("b", "c")
    edge("c", "d")
    edge("e", "f")
    edge("a", "c", via=(-30, 38, -40))
    edge("a", "d", via=(30, 22, 0))
    d.text(pos["e"].x0, pos["e"].y1 + 22, "Job 0 is the retrieve from section 13; jobs 1 and 2 repark T19 twice "
           "(rule A: e -> f). Nothing links job 0 to jobs 1 and 2.", size=11, fill=T.muted)
    dag_bottom = pos["e"].y1 + 34

    # ---- by hand: repeatedly take an event with no unfinished prerequisites ----
    y0 = dag_bottom + 40
    d.text(0, y0, "Computing one by hand: repeatedly take an event whose prerequisites are all done",
           size=13, weight=600, fill=T.fg)
    steps = [("{a, e}", "a", "a"), ("{b, e}", "b", "a b"), ("{c, e}", "c", "a b c"), ("{d, e}", "d", "a b c d"),
             ("{e}", "e", "a b c d e"), ("{f}", "f", "a b c d e f")]
    hx = [0, 60, 280, 400]
    for x, h in zip(hx, ["step", "ready (in-degree 0)", "take", "order so far"]):
        d.text(x, y0 + 26, h, size=10.5, family="mono", weight=600, fill=T.muted)
    yy = y0 + 44
    for i, (rdy, take, so_far) in enumerate(steps):
        if i % 2 == 0:
            d.rect(-6, yy - 12, 640, 24, rx=5, fill=T.tint(T.card, 0.55, T.bg), layer="bg")
        d.text(hx[0], yy, str(i + 1), size=11.5, family="mono", fill=T.fg2)
        d.text(hx[1], yy, rdy, size=11.5, family="mono", fill=T.fg)
        d.text(hx[2], yy, take, size=11.5, family="mono", weight=700, fill=T.green)
        d.text(hx[3], yy, so_far, size=11.5, family="mono", fill=T.fg2)
        yy += 26
    nt = note(d, 680, y0 + 14, W - 680,
              "When several events are ready (steps 1 to 4: a and e), any choice gives a valid order. "
              "ScheduleEventDag::GetTopologicalOrdering() takes the lowest job index, exactly as here; among "
              "events of the same job its heap decides (section 12.5).",
              title="Ties", accent=T.sky)
    # ---- valid / invalid orders ----
    y1 = max(yy, nt.y1) + 34
    d.text(0, y1, "Same DAG, three candidate orders (arcs are the edges; numbers are positions)", size=13,
           weight=600, fill=T.fg)
    ya = _order_row(d, 0, y1 + 26, list("abcdef"), "valid: every edge points right", True)
    yb = _order_row(d, 560, y1 + 26, list("eafbcd"), "also valid: jobs interleaved", True)
    yc = _order_row(d, 0, ya + 10, list("acbdef"), "not valid", False, bad="b -> c points left: c would start before b")
    # ---- cycle ----
    cy0 = y1 + 36 + 100
    cxx = 690
    d.text(cxx, ya + 10, "A cycle: no order exists", size=12, weight=600, fill=T.red)
    p = _evbox(d, cxx, ya + 50, "b", 170)
    q = _evbox(d, cxx + 250, ya + 50, "c", 170)
    connect(d, [(p.x1, p.cy - 8), (q.x0, q.cy - 8)], kind="flow", color=T.fg2, size=8)
    connect(d, [(q.x0, q.cy + 10), (p.x1, p.cy + 10)], kind="flow", color=T.red, size=8)
    label_pill(d, (p.x1 + q.x0) / 2, p.y1 + 16, "added by mistake", color=T.red, size=10)
    bottom = max(yc, q.y1 + 34)
    cp = code_panel(d, 0, bottom + 10, W, [
        "// planner_core, as called from the scheduler (see the table in section 12.5)",
        "std::optional<VertexVec> order = ctx->events.GetTopologicalOrdering();  // VertexVec = std::vector<Vertex>",
        "if(!order.has_value()) return {false, \"Failed to get total ordering\"};     // the DAG has a cycle",
        "for(Vertex v : order.value()) { auto event = ctx->events.GetEventFromVertex(v).value(); ... }",
        "if(!ctx->events.WouldCreateCycle(a, b)) ctx->events.AddDependency(a, b);  // guard before risky edges",
    ], title="In code", size=11)
    uses = note(d, 0, cp.y1 + 16, W,
                "Every pass that needs 'what happens first' walks this order: events.Apply() when a job method "
                "replays the DAG, DoTrayAssignments(), the AGV assignment loop, EnsureAgvMovePathsClear(), "
                "SanityCheckEvents(), and the response builder. Because any valid order may be returned, "
                "DoAgvAssignments adds node-arrival edges: its comment notes that CHUGG's topological sort can "
                "interleave per-AGV chains and try to put two AGVs on one node.",
                title="Where the scheduler uses it", accent=T.green)
    frame(d, title="Topological ordering",
          subtitle="The event DAG says what must come before what. A topological order turns that partial order "
                   "into one list in which every edge points forward. It is what 'replay the DAG' means: apply the "
                   "events in that list order.",
          badge_key="illustrative",
          legend=[("box", TRAY, "TrayMove"), ("box", BAYC, "BayTransition"), ("arrow", T.fg2, "dependency edge"),
                  ("arrow", T.red, "edge pointing backwards / closing a cycle")])
    return d


# ======================================================================================
# 54 — a DAG is a partial order: robots still move in parallel
# ======================================================================================

@figure("54_partial_order_parallel", "From DAG to sorted list to parallel execution", DOC1)
def partial_order_parallel():
    d = Doc("54_partial_order_parallel", "From one DAG to a sorted list to parallel execution",
            "The input is one action DAG. Topological sorting turns it into one list. The response keeps the list "
            "and each node's parents, and execution starts every node whose parents are done.")
    A, B, BAY = T.green, T.sky, BAYC
    # action ids, labels, lane
    acts = {"A1": ("A -> P17", 0), "A2": ("lift T17", 0), "A3": ("T17 -> B21", 0), "A4": ("lower", 0),
            "B1": ("B -> P19", 1), "B2": ("lift T19", 1), "B3": ("T19 -> P24", 1), "B4": ("lower", 1),
            "Y1": ("TO_RETRIEVE", 2), "Y2": ("PROCESS_RETR.", 2)}
    lane_col = [A, B, BAY]
    lane_name = ["AGV A", "AGV B", "bay B21"]
    edges = [("A1", "A2", "c"), ("A2", "A3", "c"), ("A3", "A4", "c"), ("B1", "B2", "c"), ("B2", "B3", "c"),
             ("B3", "B4", "c"), ("Y1", "Y2", "c"), ("Y1", "A3", "x"), ("A3", "B3", "o"), ("A4", "Y2", "x")]
    ecol = {"c": T.tint(T.fg2, 0.75, T.bg), "x": BAY, "o": T.red}

    # ---------------- 1. input DAG ----------------
    d.text(0, -16, "1 · Input: one action DAG (the lanes are just a drawing aid; red and violet edges connect them)",
           size=13, weight=600, fill=T.fg)
    bw, bh, gx, gy, x0 = 112, 40, 30, 70, 80
    col_of = {"A1": 0, "A2": 1, "A3": 2, "A4": 3, "B1": 0, "B2": 1, "B3": 2, "B4": 3, "Y1": 0, "Y2": 3}
    box = {}
    for k, (lab, lane) in acts.items():
        x, y = x0 + col_of[k] * (bw + gx), 10 + lane * gy
        c = lane_col[lane]
        d.rect(x, y, bw, bh, rx=7, fill=T.card, stroke=c, sw=1.4)
        d.text(x + 8, y + 12, k, size=9.5, family="mono", weight=700, fill=c)
        d.text(x + bw / 2 + 8, y + 26, lab, size=10.5, family="mono", fill=T.fg, anchor="middle")
        box[k] = BBox(x, y, x + bw, y + bh)
    for i, n in enumerate(lane_name):
        d.text(0, 10 + i * gy + bh / 2, n, size=11, family="mono", weight=600, fill=lane_col[i])
    for u, v, kind in edges:
        a, b = box[u], box[v]
        col = ecol[kind]
        if a.cy == b.cy and kind != "x" and not (u == "Y1" and v == "Y2"):
            connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=col, size=7, sw=1.4)
        elif u == "Y1" and v == "Y2":
            connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=col, size=7, sw=1.2, dash="2 3")
        elif u == "Y1":
            connect(d, [(a.x1, a.cy - 8), (b.cx - 24, a.cy - 8), (b.cx - 24, b.y1)], kind="flow", color=col,
                    size=7, sw=1.5, dash="4 3")
        elif u == "A4":
            connect(d, [(a.cx, a.y1), (a.cx, b.y0)], kind="flow", color=col, size=7, sw=1.5, dash="4 3")
        else:   # A3 -> B3 occupancy
            connect(d, [(a.cx + 24, a.y1), (a.cx + 24, b.y0)], kind="flow", color=col, size=7, sw=1.7)
            label_pill(d, a.cx + 30, (a.y1 + b.y0) / 2, "occupancy", color=col, size=9.5, anchor="start")
    rx = x0 + 4 * (bw + gx) + 10
    note(d, rx, -4, W - rx,
         "It is one graph: Y1 -> A3, A3 -> B3 and A4 -> Y2 link the three lanes. A graph with no links at all "
         "would simply be a DAG in which nothing waits for anything.", title="Not three graphs", accent=T.violet)
    y1 = 10 + 3 * gy + 30

    # ---------------- 2. sorted list + 3. parents ----------------
    order = ["Y1", "A1", "B1", "A2", "B2", "A3", "B3", "A4", "B4", "Y2"]
    pos = {k: i for i, k in enumerate(order)}
    d.text(0, y1, "2 · events.GetTopologicalOrdering(): one flat list, every edge points right", size=13,
           weight=600, fill=T.fg)
    d.text(0, y1 + 18, "That is all a topological sort returns: positions 0..9. No times, no 'parallel' marks.",
           size=11, fill=T.muted)
    cw, cx0 = 104, 18
    ly = y1 + 150
    cx = {}
    for k in order:
        i = pos[k]
        x = cx0 + i * cw
        c = lane_col[acts[k][1]]
        d.rect(x, ly, 88, 34, rx=6, fill=T.card, stroke=c, sw=1.5)
        d.text(x + 44, ly + 17, k, size=12.5, family="mono", weight=700, fill=c, anchor="middle")
        d.text(x + 44, ly + 48, f"[{i}]", size=10.5, family="mono", fill=T.muted, anchor="middle")
        cx[k] = x + 44
    for u, v, kind in edges:
        xa, xb = cx[u], cx[v]
        h = 10 + (xb - xa) * 0.11
        yb = ly - 2
        col = ecol[kind]
        d.path(f"M{xa:.1f} {yb} C{xa:.1f} {yb - h:.1f} {xb:.1f} {yb - h:.1f} {xb:.1f} {yb}", stroke=col,
               sw=1.4, layer="edges", bbox=BBox(xa, yb - h, xb, yb))
        d.arrowhead((xb, yb), (xb - 2, yb - 6), kind="filled", color=col, size=7)
    # parents row
    py = ly + 86
    d.text(0, py - 10, "3 · Written to the response: Schedule.nodes[i] with its parents (indices into the same list)",
           size=13, weight=600, fill=T.fg)
    parents = {k: sorted(pos[u] for u, v, _ in edges if v == k) for k in order}
    for k in order:
        x = cx0 + pos[k] * cw
        txt = "[" + ", ".join(map(str, parents[k])) + "]"
        d.rect(x, py + 8, 88, 30, rx=6, fill=T.bg_deep, stroke=T.border_soft, sw=1)
        d.text(x + 44, py + 23, "parents " + txt, size=9.5, family="mono",
               fill=T.fg if parents[k] else T.green, anchor="middle")
    d.text(0, py + 56, "Nodes with no parents (Y1, A1, B1) can start immediately. Every parent index is smaller than "
                       "the node's own index, because the list is topologically sorted. The list order and the parents "
                       "together are the 'sorted graph'.", size=11, fill=T.fg2)
    y3 = py + 94

    # ---------------- 4. execution ----------------
    d.text(0, y3, "4 · Execution: a node starts once all its parents are done (durations from motion planning, "
                  "values illustrative)", size=13, weight=600, fill=T.fg)
    ty = y3 + 34
    tx0, sc = x0, 12.4
    sched = {0: [("A1", 0, 14), ("A2", 14, 4), ("A3", 18, 22), ("A4", 40, 4)],
             1: [("B1", 0, 10), ("B2", 10, 4), ("wait", 14, 26), ("B3", 40, 12), ("B4", 52, 4)],
             2: [("Y1", 0, 15), ("Y2", 44, 20)]}
    T_END = 66
    for t in range(0, T_END + 1, 10):
        x = tx0 + t * sc
        d.line(x, ty - 6, x, ty + 3 * 42, stroke=T.grid, sw=1, layer="bg")
        d.text(x, ty + 3 * 42 + 10, f"{t} s", size=10, family="mono", fill=T.muted, anchor="middle")
    for r in range(3):
        y = ty + r * 42
        d.text(0, y + 14, lane_name[r], size=11, family="mono", weight=600, fill=lane_col[r])
        for lab, s0, du in sched[r]:
            x, w = tx0 + s0 * sc, du * sc
            if lab == "wait":
                d.rect(x, y, w, 28, rx=5, fill="none", stroke=T.faint, sw=1, dash="3 3")
                d.text(x + w / 2, y + 14, "B3 waits for parent A3 (occupancy)", size=10, fill=T.muted, anchor="middle")
                continue
            d.rect(x, y, w, 28, rx=5, fill=T.tint(lane_col[r], 0.25, T.bg), stroke=lane_col[r], sw=1.2)
            d.text(x + w / 2, y + 14, lab, size=10.5, family="mono", weight=700, fill=T.fg, anchor="middle")
    d.rect(tx0 - 4, ty - 8, 15 * sc + 8, 3 * 42 + 2, rx=6, fill="none", stroke=T.amber, sw=1.4, dash="5 4",
           layer="over")
    label_pill(d, tx0 + 15 * sc + 10, ty - 14, "t = 0: Y1, A1 and B1 have no parents, so all three start together",
               color=T.amber, size=10, bg=T.bg, anchor="start")
    frame(d, title="From one DAG to a sorted list to parallel execution",
          subtitle="Topological sorting does not create parallelism and does not remove it. It only lists the nodes "
                   "so that every edge points forward. Parallelism comes from the DAG itself: nodes with no path "
                   "between them may run at the same time, and the parents field carries that into the response.",
          badge_key="illustrative",
          legend=[("box", A, "AGV A actions"), ("box", B, "AGV B actions"), ("box", BAY, "bay actions"),
                  ("arrow", T.tint(T.fg2, 0.75, T.bg), "same-entity chain"), ("dasharrow", BAY, "bay dependency"),
                  ("arrow", T.red, "cross-AGV occupancy edge")],
          footnote="The scheduler builds Schedule.nodes this way in BuildScheduledActionsArray: it walks the action DAG "
                   "in topological order, gives each node its position, and fills parents from the node's in-edges "
                   "plus the previous action of the same AGV, bay or VRC. How Dispatch executes the schedule is "
                   "outside this package.")
    return d
