"""Code-walkthrough figures, part 3: tray assignment, freeing moves, AGV matching, AGV expansion, path repair."""
from __future__ import annotations

from components import (EVENT_COLOR, chip, code_panel, connect, event_box, flow, frame, label_pill, note,
                        num_badge)
from facility import Map, NODES, STALL_L, STALL_W, C_BAY
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC1 = "01-software-background.html"
TRAY, AGV, BAYC = T.amber, T.green, T.violet
QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)


def _box(d: Doc, x, y, w, title, lines=(), *, col=T.border, title_col=T.fg, mono_title=True, h=None, fill=T.card,
         dash=None, size=11.5):
    lh = 16
    hh = h or (26 + len(lines) * lh + 10)
    d.rect(x, y, w, hh, rx=8, fill=fill, stroke=col, sw=1.3, dash=dash)
    d.text(x + 12, y + 17, title, size=12, family="mono" if mono_title else "sans", weight=700 if mono_title else 600,
           fill=title_col)
    for i, ln in enumerate(lines):
        d.text(x + 12, y + 38 + i * lh, ln, size=size, fill=T.muted)
    return BBox(x, y, x + w, y + hh)


def _diamond(d: Doc, cx, cy, text, *, w=200, h=54, col=T.fg2):
    pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    d.polygon(pts, fill=T.tint(col, 0.1, T.bg), stroke=col, sw=1.3)
    d.text(cx, cy, text, size=11.5, family="mono", fill=T.fg, anchor="middle")
    return BBox(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


# --------------------------------------------------------------------------------------
# 27 — DoTrayAssignments decision flow
# --------------------------------------------------------------------------------------

@figure("27_tray_assignment_flow", "DoTrayAssignments decision flow", DOC1)
def tray_flow():
    d = Doc("27_tray_assignment_flow", "Inside DoTrayAssignments()",
            "For every event in topological order: apply non-tray transitions, fill a missing tray id, fill a missing "
            "destination, or find the critical path and resolve blocking trays with two fallbacks.")
    cx = 250
    y = 0
    loop = _box(d, cx - 230, y, 460, "for event : ctx->events.GetTopologicalOrdering()",
                ["working_state = ctx->initial_state;  freeing_moves = {}"], col=T.sky, title_col=T.sky)
    q1 = _diamond(d, cx, loop.y1 + 60, "TrayMove?", w=170)
    connect(d, [(cx, loop.y1), (cx, q1.y0)], kind="flow", color=T.faint, size=7)
    nt = _box(d, cx + 160, q1.cy - 34, 330, "ApplyTransitionToFreeingMoves()",
              ["bay / VECS transition: register its pose,", "apply it, continue"], col=BAYC, title_col=BAYC)
    connect(d, [(q1.x1, q1.cy), (nt.x0, q1.cy)], kind="flow", color=T.faint, size=7, label="no",
            label_at=((q1.x1 + nt.x0) / 2, q1.cy - 12))
    q2 = _diamond(d, cx, q1.y1 + 70, "has tray id?", w=190)
    connect(d, [(cx, q1.y1), (cx, q2.y0)], kind="flow", color=T.faint, size=7, label="yes",
            label_at=(cx + 18, (q1.y1 + q2.y0) / 2))
    a1 = _box(d, cx + 160, q2.cy - 34, 330, "AssignTrayIdForEmptyMove()",
              ["EmptyTraySearch from the destination: cheapest", "empty tray (time + 30 s per blocker)"], col=TRAY, title_col=TRAY)
    connect(d, [(q2.x1, q2.cy), (a1.x0, q2.cy)], kind="flow", color=T.faint, size=7, label="no",
            label_at=((q2.x1 + a1.x0) / 2, q2.cy - 12))
    q3 = _diamond(d, cx, q2.y1 + 70, "has destination?", w=210)
    connect(d, [(cx, q2.y1), (cx, q3.y0)], kind="flow", color=T.faint, size=7)
    connect(d, [(a1.cx, a1.y1), (a1.cx, a1.y1 + 14), (cx + 40, a1.y1 + 14), (cx + 40, q3.y0 + 6)], kind="flow",
            color=T.faint, size=7)
    a2 = _box(d, cx + 160, q3.cy - 44, 330, "AssignDestForUntargetedMove()",
              ["ResolveBlockingTrays(tray): OpenSpaceSearch", "tier 1 parking, tier 2 waypoint stash;",
               "adds blocker moves; then continue"], col=TRAY, title_col=TRAY)
    connect(d, [(q3.x1, q3.cy), (a2.x0, q3.cy)], kind="flow", color=T.faint, size=7, label="no",
            label_at=((q3.x1 + a2.x0) / 2, q3.cy - 12))
    s1 = _box(d, cx - 230, q3.y1 + 40, 460, "destination free?  then BlockingTraySearch",
              ["critical path = tray pose -> dest; collect trays on it", "error if the destination is occupied/disabled"])
    connect(d, [(cx, q3.y1), (cx, s1.y0)], kind="flow", color=T.faint, size=7, label="yes",
            label_at=(cx + 18, (q3.y1 + s1.y0) / 2))
    # blocking loop frame
    ly = s1.y1 + 34
    lf = BBox(cx - 250, ly, cx + 250 + 380, ly + 330)
    d.rect(lf.x0, lf.y0, lf.w, lf.h, rx=12, fill=T.tint(TRAY, 0.03, T.bg), stroke=T.tint(TRAY, 0.5, T.bg), sw=1,
           dash="6 5", layer="bg")
    d.text(lf.x0 + 14, ly + 18, "while (blocking trays remain on the critical path)", size=12, family="mono",
           weight=600, fill=TRAY)
    r1 = _box(d, cx - 230, ly + 36, 460, "ResolveBlockingTrays(blocker, immobile={root},",
              ["  illegal = critical path + earlier dests of this blocker)", "may recurse when the blocker is itself blocked"],
              col=TRAY)
    f1 = _box(d, cx + 260, ly + 36, 350, "fallback 1: advance the root tray",
              ["one step along its critical path,", "then resolve again"], col=T.red, title_col=T.red, dash="5 4")
    f2 = _box(d, cx + 260, f1.y1 + 18, 350, "fallback 2: park on the critical path",
              ["retry without the critical-path ban; else error", "\"Failed to find open space for blocking tray\""],
              col=T.red, title_col=T.red, dash="5 4")
    connect(d, [(r1.x1, r1.y0 + 24), (f1.x0, r1.y0 + 24)], kind="flow", color=T.red, size=7, dash="4 3",
            label="no dest", label_at=((r1.x1 + f1.x0) / 2, r1.y0 + 12))
    connect(d, [(f1.cx, f1.y1), (f2.cx, f2.y0)], kind="flow", color=T.red, size=7, dash="4 3")
    r2 = _box(d, cx - 230, r1.y1 + 26, 460, "emit blocker TrayMoves as events (chained)",
              ["edge: blocker move -> root move", "edges from freeing_moves for every path pose"], col=TRAY)
    connect(d, [(cx, r1.y1), (cx, r2.y0)], kind="flow", color=T.faint, size=7)
    r3 = _box(d, cx - 230, r2.y1 + 26, 460, "recompute blocking trays on the remaining path", [], col=TRAY)
    connect(d, [(cx, r2.y1), (cx, r3.y0)], kind="flow", color=T.faint, size=7)
    connect(d, [(r3.x0, r3.cy), (r3.x0 - 12, r3.cy), (r3.x0 - 12, r1.cy), (r1.x0, r1.cy)], kind="flow",
            color=TRAY, size=7, radius=4)
    fin = _box(d, cx - 230, lf.y1 + 30, 460, "finish this TrayMove",
               ["freeing_moves deps for dest + source; Apply(event);", "record last_tray_event / first_tray_event"],
               col=T.green, title_col=T.green)
    connect(d, [(cx, lf.y1), (cx, fin.y0)], kind="flow", color=T.faint, size=7)
    note(d, cx + 260, fin.y0 - 4, 350,
         "Reduce() is deliberately not called at the end: a source comment says reducing here breaks the following "
         "AGV assignment. Every TrayMove now has a tray id and a destination.", title="After the loop", accent=T.amber)
    frame(d, title="Inside DoTrayAssignments()",
          subtitle="One pass over the event DAG in topological order. Searches come from motion_planner "
                   "(EmptyTraySearch, OpenSpaceSearch, BlockingTraySearch) and all run through SingleSourceSearch.",
          badge_key="as-built",
          legend=[("box", TRAY, "tray work"), ("box", BAYC, "non-tray event"), ("dashbox", T.red, "fallback"),
                  ("arrow", T.faint, "control flow")])
    return d


# --------------------------------------------------------------------------------------
# 28 — freeing_moves: occupancy -> dependencies
# --------------------------------------------------------------------------------------

@figure("28_freeing_moves", "freeing_moves: occupancy becomes dependencies", DOC1)
def freeing_moves():
    d = Doc("28_freeing_moves", "freeing_moves: turning shared space into dependencies",
            "GarageOccupancyChecker remembers which events used each pose. A later move through a pose depends on "
            "every earlier event whose footprint collides there.")
    s = 24
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    m.tray(17, "T17", payload=True, emphasis=True, chip_pos="bl")
    m.tray(20, "T20", payload=True, chip_pos="bl")
    # ghosts for vacated spots
    for nid, lab in ((15, "T15 left (e4)"), (21, "T21 left (e1)")):
        x, y = m.P(nid)
        w, h = (STALL_L - 0.5) * s, (STALL_W - 0.32) * s
        d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill="none", stroke=TRAY, sw=1.3, dash="5 4", layer="main")
        d.text(x + w / 2 - 8, y - h / 2 + 11, lab, size=10.5, family="mono", fill=TRAY, anchor="end", halo=T.bg_deep,
               halo_w=3)
    m.route([17, 15, 13, 18, 22, 41, 21], TRAY, sw=3.5, offset=(0, 7), num=2, num_at=0)
    # highlight poses on the path that have occupants
    for nid, col in ((15, T.sky), (21, T.sky)):
        x, y = m.P(nid)
        d.circle(x, y, 13, fill="none", stroke=col, sw=2, layer="top")
    mb = m.box
    # table of the checker contents
    tx = mb.x1 + 36
    tw = 1060 - tx
    d.text(tx, 12, "freeing_moves contents when e2 is processed", size=12.5, weight=600, fill=T.fg)
    rows = [("B21 (bay pose)", "e0  BayTransition TO_RETRIEVE", "ApplyTransitionToFreeingMoves"),
            ("B21 (bay pose)", "e1  TrayMove T21 -> P23", "source pose of a move"),
            ("P15", "e4  TrayMove T15 -> P19", "source pose of a move"),
            ("P23, W22, W41 ...", "e1  (path poses)", "every pose on e1's path")]
    y = 30
    for pose, ev, why in rows:
        d.rect(tx, y, tw, 52, rx=8, fill=T.card, stroke=T.border_soft, sw=1)
        d.text(tx + 12, y + 18, pose, size=11.5, family="mono", weight=600, fill=T.sky)
        d.text(tx + 12, y + 37, ev, size=11.5, family="mono", fill=T.fg)
        d.text(tx + tw - 10, y + 18, why, size=10.5, fill=T.muted, anchor="end")
        y += 60
    d.text(tx, y + 12, "edges added for e2 (T17 -> B21)", size=12.5, weight=600, fill=T.fg)
    edges = [("e4 -> e2", "path pose P15 was occupied by T15"), ("e1 -> e2", "destination B21 held T21"),
             ("e0 -> e2", "bay transition registered on B21")]
    y += 26
    for e, why in edges:
        chip(d, tx, y + 10, e, TRAY, size=11.5)
        d.text(tx + 92, y + 10, why, size=11.5, fill=T.fg2)
        y += 30
    code_panel(d, 0, max(mb.y1, y) + 30, 1060, [
        "// DoTrayAssignments(), for each pose on a move's path (simplified):",
        "GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>> freeing_moves(table_, gg_);  // Scheduler members",
        "auto blockers_opt = freeing_moves.GetBlockers(pose, tray_collision_id);   // who used this space before?",
        "for(auto& blocker : *blockers_opt) ctx->events.AddDependency(blocker, move);  // must happen first",
        "freeing_moves.AddOccupant(pose, tray_collision_id, move, /*lifted=*/true);    // remember this move too",
    ], title="the occupancy-to-edge pattern", size=11.5)
    frame(d, title="freeing_moves: turning shared space into dependencies",
          subtitle="Collision checks use the CollisionTable, so a pose \"collides\" if the two footprints overlap, "
                   "not only when node ids match. The same idea is reused on actions in ResponseFromTrajectories(). "
                   "Redundant edges are pruned later by Reduce().",
          badge_key="yaml+hyp",
          legend=[("route", TRAY, "e2: T17 -> B21"), ("dashbox", TRAY, "vacated by an earlier event"),
                  ("ring", T.sky, "pose with recorded occupants")])
    return d


# --------------------------------------------------------------------------------------
# 29 — AGV matching (BottleneckAssignment)
# --------------------------------------------------------------------------------------

@figure("29_agv_matching", "Matching AGVs to tray moves", DOC1)
def agv_matching():
    d = Doc("29_agv_matching", "Matching AGVs to root tray moves",
            "DoAgvAssignments builds an AGV-by-TrayMove cost table for the current root events and runs "
            "BottleneckAssignment; infeasible pairs get no edge.")
    s = 22
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    m.tray(15, "T15", chip_pos="bl")
    m.tray(21, "T21", chip_pos="tr")
    m.tray(17, "T17", payload=True, chip_pos="bl")
    m.agv(26, "A", heading=90, label_side="above")
    m.agv(18, "B", heading=90, label_side="left")
    m.tray(24, "T24", chip_pos="bl")
    m.agv(24, "C", heading=90, label_side="right")
    mb = m.box
    # bipartite graph
    gx = mb.x1 + 60
    agvs = [("A", "idle at W26"), ("B", "idle at W18"), ("C", "carrying T24")]
    moves = [("e4", "T15 -> P19"), ("e1", "T21 -> P23")]
    ay = [26, 116, 206]
    my = [56, 166]
    AB, MB = [], []
    for (a, sub), y in zip(agvs, ay):
        bb = BBox(gx, y, gx + 130, y + 50)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=25, fill=T.card, stroke=AGV if a != "C" else T.faint, sw=1.4)
        d.text(bb.x0 + 16, y + 20, f"AGV {a}", size=12, family="mono", weight=700, fill=AGV if a != "C" else T.muted)
        d.text(bb.x0 + 16, y + 37, sub, size=10.5, fill=T.muted)
        AB.append(bb)
    mx = gx + 300
    for (e, t), y in zip(moves, my):
        MB.append(event_box(d, mx, y, "TrayMove " + e, t, size=11.5, w=150))
    costs = {(0, 0): ("41 s", True), (0, 1): ("48 s", False), (1, 0): ("19 s", False), (1, 1): ("36 s", True)}
    for (i, j), (c, chosen) in costs.items():
        a, b = AB[i], MB[j]
        col = AGV if chosen else T.faint
        d.line(a.x1, a.cy, b.x0, b.cy, stroke=col, sw=3 if chosen else 1.2, dash=None if chosen else "4 4",
               layer="edges")
        t = 0.30 if (i + j) % 2 == 0 else 0.70
        lx, ly = a.x1 + (b.x0 - a.x1) * t, a.cy + (b.cy - a.cy) * t
        label_pill(d, lx, ly, c, color=col if chosen else T.muted, size=11)
    d.text(gx, -12, "edge_costs (illustrative seconds)", size=12, weight=600, fill=T.fg)
    gy = AB[-1].y1 + 22
    for i, ln in enumerate(["no edges from C: it carries a different tray,",
                            "so GetAgvToTrayAssignmentCost() returns nullopt"]):
        d.text(gx, gy + i * 16, ln, size=11, fill=T.muted)
    nb = note(d, gx, gy + 40, 1080 - gx,
              "Bottleneck matching minimises the worst single cost. {A-e4 41 s, B-e1 36 s} wins with a worst "
              "case of 41 s, although {B-e4 19 s, A-e1 48 s} has the lower total. GetAgvOccupiedDuration() "
              "still returns 0, so queued work is not yet modelled.", title="What gets optimised", accent=T.amber)
    code_panel(d, 0, max(mb.y1, nb.y1) + 30, 1080, [
        "// DoAgvAssignments(), one outer iteration (simplified)",
        "// cost(agv, move) = max(occupied(agv) - occupied(move), 0) + travel(agv.pose -> tray.pose) + lift_up",
        "edge_costs[{agv_id, root_event}] = GetAgvToTrayAssignmentCost(agv_id, *tray_move, working_state, adjusted, filters);",
        "auto [matching, threshold] = volley::BottleneckAssignment(edge_costs, agvs_to_assign, root_events,",
        "                                                            Interval::Duration::max()).value();",
        "auto agv_event_dag = GetEventDag(matching, working_state);   // order matched AGVs that would collide",
    ], title="task_planner::BottleneckAssignment", size=11.5)
    frame(d, title="Matching AGVs to root tray moves",
          subtitle="Each outer loop first applies every non-tray root, then matches AGVs to the TrayMoves that have no "
                   "unassigned parents. AGVs trapped in a bay that is not READY_TO_RETRIEVE are skipped.",
          badge_key="yaml+hyp",
          legend=[("route", AGV, "matched pair"), ("dash", T.faint, "feasible, not chosen"), ("box", TRAY, "root TrayMove"),
                  ("box", AGV, "enabled AGV")])
    return d


# --------------------------------------------------------------------------------------
# 30 — what one AGV assignment adds to the DAG
# --------------------------------------------------------------------------------------

@figure("30_agv_event_expansion", "What one AGV assignment adds", DOC1)
def agv_expansion():
    d = Doc("30_agv_event_expansion", "What one AGV assignment adds to the DAG",
            "Assigning AGV B to TrayMove e4 adds AgvMove(to tray), lift, sets agv_id on the TrayMove, and adds lower, "
            "with four kinds of dependency edges.")
    W = 1060
    d.text(0, 0, "before", size=12.5, family="mono", weight=700, fill=T.muted)
    pre = event_box(d, 0, 16, "TrayMove e4", "T15: P15 -> P19   agv = ?", size=11.5)
    d.text(pre.x1 + 30, pre.cy, "a root of event_dag_copy, matched to AGV A by BottleneckAssignment", size=11.5,
           fill=T.muted)
    y = pre.y1 + 74
    d.text(0, y - 20, "after", size=12.5, family="mono", weight=700, fill=T.fg)
    bw = 210
    gx = 44
    chain = [("AgvMove", "A: W26 -> P15", "MoveAgvToTrayPose()"), ("AgvMove", "A: lift", "AppendAgvLiftEvent(raised)"),
             ("TrayMove e4", "T15 -> P19, agv = A", "SetAgvId(A)"), ("AgvMove", "A: lower", "AppendAgvLiftEvent(lowered)")]
    xs = [i * (bw + gx) for i in range(4)]
    B = []
    for (k, t, sub), x in zip(chain, xs):
        B.append(event_box(d, x, y, k, t, w=bw, sub=sub, size=11.5, style="new" if k == "AgvMove" else "solid"))
    for a, b in zip(B, B[1:]):
        connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=AGV, size=8, sw=1.6)
    # incoming edge kinds
    src_y = y + 170
    kinds = [
        ("A's previous event", "last_agv_event[A]", AGV, 0, "chain per AGV"),
        ("first move of a path tray", "ctx->first_tray_event[id]", TRAY, 0, "tray on A's nav path clears first"),
        ("prior occupant of P15", "AddNodeArrivalDeps()", T.sky, 0, "previous AGV must leave the node"),
        ("parent AGV in agv_event_dag", "last_move_to_tray_event[B]", T.violet, 0, "collision order among matches"),
    ]
    for i, (name, code, col, tgt, why) in enumerate(kinds):
        x = i * (bw + gx)
        bb = BBox(x, src_y, x + bw, src_y + 64)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.bg, stroke=col, sw=1.3, dash="4 3")
        d.text(x + 12, src_y + 17, name, size=11.5, weight=600, fill=col)
        d.text(x + 12, src_y + 36, code, size=11, family="mono", fill=T.fg2)
        d.text(x + 12, src_y + 53, why, size=10.5, fill=T.muted)
        tx = B[0].x0 + 30 + i * 40
        connect(d, [(bb.cx, bb.y0), (bb.cx, src_y - 26 - i * 0), (tx, src_y - 26), (tx, B[0].y1)], kind="flow",
                color=col, size=8, sw=1.5, radius=6)
    # cost strip
    cy = src_y + 120
    d.text(0, cy, "event_cost for this assignment", size=12.5, weight=600, fill=T.fg)
    parts = [("travel W26 -> P15", 0.34, AGV), ("lift_up", 0.10, T.violet), ("carry P15 -> P19", 0.42, TRAY),
             ("lift_down", 0.10, T.violet)]
    x = 0
    total = W - 260
    for lab, f, col in parts:
        w = total * f
        d.rect(x, cy + 14, w - 4, 30, rx=6, fill=T.tint(col, 0.35, T.bg), stroke=col, sw=1)
        d.text(x + 10, cy + 29, lab, size=11, family="mono", fill=T.fg)
        x += w
    d.text(x + 10, cy + 29, "-> PropagateEventCostToChildren()", size=11.5, family="mono", fill=T.muted)
    d.text(0, cy + 66, "GetJustMovingCost() and the cost model's lift times; agv_occupied_durations[A] += event_cost",
           size=11, fill=T.muted)
    frame(d, title="What one AGV assignment adds to the DAG",
          subtitle="Matching only picks pairs; the loop that follows turns each pair into real events and wires them "
                   "into the DAG so motion planning can replay them safely.",
          badge_key="as-built",
          legend=[("box", AGV, "new AgvMove"), ("box", TRAY, "existing TrayMove"), ("dashbox", T.fg2, "where incoming edges come from")])
    return d


# --------------------------------------------------------------------------------------
# 31 — EnsureAgvMovePathsClear
# --------------------------------------------------------------------------------------

@figure("31_agv_path_repair", "EnsureAgvMovePathsClear", DOC1)
def path_repair():
    d = Doc("31_agv_path_repair", "Repairing AGV paths after assignment",
            "EnsureAgvMovePathsClear replays the DAG in topological order; if an AGV reposition is blocked only by "
            "another AGV's body, it gates the move on that AGV's next departure.")
    s = 24
    m = Map(d, 0, 0, s, (26.0, 46.4), (11.4, 25.2))
    m.base(labels=True, zones=False, axes=False)
    m.tray(15, "T15", chip_pos="bl")
    m.tray(19, "T19", chip_pos="bl")
    m.tray(23, "T23", chip_pos="bl")
    m.agv(25, "A", heading=90, label_side="above")
    m.agv(13, "B (parked)", heading=90, label_side="left")
    m.route([25, 22, 18, 13, 8], AGV, sw=3, offset=(10, 0), dash="7 5")
    x13, y13 = m.P(13)
    d.circle(x13, y13, 26, fill="none", stroke=T.red, sw=2, layer="top")
    label_pill(d, x13 + 30, y13 + 34, "A cannot pass while B is here", color=T.red, bg=T.bg_deep, border=T.red,
               anchor="start", size=11)
    mb = m.box
    rx = mb.x1 + 40
    rw = 1060 - rx
    d.text(rx, 8, "topological replay finds", size=12.5, weight=600, fill=T.fg)
    a = event_box(d, rx, 26, "AgvMove (idx k)", "A: W25 -> W8", w=rw)
    b = event_box(d, rx, a.y1 + 96, "AgvMove (later)", "B: W13 -> P15  (B departs)", w=rw)
    connect(d, [(b.x0 + 40, b.y0), (a.x0 + 40, a.y1)], kind="flow", color=T.red, size=9, sw=2)
    label_pill(d, a.x0 + 48, (a.y1 + b.y0) / 2, "new edge: departure -> A's move", color=T.red, anchor="start",
               size=11)
    steps = [
        "path feasible ignoring only A?  no -> continue",
        "feasible ignoring every other AGV?  yes -> an AGV is the problem",
        "for each other AGV X: feasible ignoring {A, X}?  -> X = B",
        "FindAgvDepartureFromNode(B, W13) after idx k",
        "AddDependency(departure, move) unless it would form a cycle",
    ]
    yy = b.y1 + 34
    d.text(rx, yy - 8, "TryClearBlockedAgvMove(), in order", size=12, weight=600, fill=T.fg)
    for i, st in enumerate(steps, start=1):
        num_badge(d, rx + 10, yy + 14, i, T.sky, r=9)
        for j, ln in enumerate(wrap(st, rw - 30, 11.5, "mono")):
            d.text(rx + 26, yy + 14 + j * 16, ln, size=11.5, family="mono", fill=T.fg2)
        yy += 16 * len(wrap(st, rw - 30, 11.5, "mono")) + 12
    code_panel(d, 0, max(mb.y1, yy) + 24, 1060, [
        "// Scheduler::EnsureAgvMovePathsClear(ctx): called at the end of DoAgvAssignments(), before Reduce()",
        "for(size_t iter = 0; iter < 256; ++iter) {             // each productive pass adds exactly one edge",
        "  auto added_edge = RunAgvPathRepairPass(ctx);          // stdx::Expected<bool>",
        "  if(!added_edge.has_value()) return error;             // DAG could not be sorted",
        "  if(!added_edge.value()) return {};                    // full replay needed no repair",
        "}                                                       // cap hit: SanityCheckEvents is the backstop",
    ], title="why a separate pass", size=11.5)
    frame(d, title="Repairing AGV paths after assignment",
          subtitle="DoAgvAssignments orders events by its own serial assignment loop, which can differ from the final "
                   "topological order. This pass replays the real order, where AGV occupancy is exact, and adds one "
                   "gating edge at a time. Trays and disabled nodes are not fixed here.",
          badge_key="yaml+hyp",
          legend=[("dasharrow", AGV, "A's intended path"), ("ring", T.red, "blocking AGV"),
                  ("arrow", T.red, "gating edge added")])
    return d
