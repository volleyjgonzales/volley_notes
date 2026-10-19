"""fig_actiondag: building the action DAG, motion by motion (126).

Doc 05-action-graph.html. Follows Scheduler::ResponseFromTrajectories (scheduler.cpp):
CollectAndCollapseTrajectoryMotions (waits dropped, std::set<Motion, MotionScheduleOrder>: start time, then
action id = event vertex, then hash), BuildActionDagFromMotions (ToActionNode, event_start_end,
last_entity_action chain, GarageOccupancyChecker<shared_ptr<ActionNodeMsg>> freeing_moves: GetBlockers then
AddOccupant; lifted = collision id != AGV), Reduce, TransferEventDagDepsToActionDag (last action of e ->
first action of e' for each event edge), Reduce, InsertVrcActionsIntoDag (no VRC in Pecos), Reduce,
GetTopologicalOrdering, BuildScheduledActionsArray (parents as indices, extra same-entity chain edge,
node_indices per job). Times and the occupied-location lists are illustrative; the real sets come from
CollisionTable::Query.
"""
from __future__ import annotations

from components import code_panel, frame, label_pill
from facility import Map, Scene
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import S, T

DOC = "05-action-graph.html"
A1C, A2C, BAYC = T.green, T.violet, T.teal
CHAIN, OCC, EVT, GONE = T.green, T.sky, T.amber, T.faint


def _hl_code(d, panel, first, last=None, *, size=11, col=T.sky):
    last = first if last is None else last
    lh = size * 1.5
    y0 = panel.y0 + 14 + 24 + size / 2 + first * lh - lh / 2
    d.rect(panel.x0 + 6, y0, panel.w - 12, (last - first + 1) * lh, rx=4, fill=T.tint(col, 0.16, "#0B1222"),
           stroke=T.tint(col, 0.6, T.bg), sw=1, layer="main")


@figure("126_action_dag_construction", "Building the action DAG, motion by motion (animated)", DOC)
def action_dag_construction():
    d = Doc("126_action_dag_construction", "Building the action DAG, motion by motion",
            "Animated: ResponseFromTrajectories on a small retrieve. Motions are taken in start-time order; each "
            "becomes an ActionNode, is chained to its entity's previous action, depends on every earlier occupant "
            "of the space it needs, and then occupies that space. Event edges and two Reduce() passes finish the "
            "DAG, which is written out as Schedule.nodes.")
    S0 = d.step("Input: CHUGG's trajectories and the event DAG. AGV-2 must leave W22 (event f1). AGV-1 stands "
                "under T23 at P23; it lifts (e1), carries the car to bay B21 (e2, three edges), lowers (e3), and "
                "the bay hands the car over (e4). AGV-1 waits 3-5 s for AGV-2.")
    S1 = d.step("CollectAndCollapseTrajectoryMotions merges every entity's trajectory into one std::set ordered by "
                "MotionScheduleOrder: start time, then the event vertex, then a hash. Waits and idle motions are "
                "dropped (AGV-1's wait disappears); runs of floor-traversal motions would be merged into one.")
    S2 = d.step("Motion 1, AGV-2 W22 -> W18 (event f1). ToActionNode makes a0 (TYPE_AGV_COMMAND, fresh guid, "
                "job_id = job B). AGV-2 has no previous action. GetBlockers finds nothing. AddOccupant records a0 "
                "on every location an entity would collide with: W22, the edge and W18.")
    S3 = d.step("Motion 2, AGV-1 lifts at P23 (event e1). a1 is the first action of AGV-1. lifted is true unless the "
                "motion's collision id is the bare AGV. No earlier occupant conflicts with P23; a1 becomes its "
                "occupant.")
    S4 = d.step("Motion 3, AGV-1 carries T23 P23 -> W22 (event e2). Chain: a1 -> a2 (last_entity_action[AGV-1]). "
                "GetBlockers on the edge P23-W22 returns {a0, a1}: a0 still 'owns' W22, because occupancy is "
                "never cleared. New edge a0 -> a2 (blue): the hand-over of W22 from AGV-2 to AGV-1.")
    S5 = d.step("Motion 4, W22 -> W41 (event e2). Chain a2 -> a3. Blockers {a0, a2}: the edge a0 -> a3 is added "
                "although a0 -> a2 -> a3 already implies it ('overkill but pruned later by Reduce()').")
    S6 = d.step("Motion 5, W41 -> B21 (event e2). Chain a3 -> a4; blockers {a3}. event_start_end[e2] is now "
                "(a2, a4): first and last action of the event.")
    S7 = d.step("Motion 6, AGV-1 lowers T23 in B21 (event e3): a5, chained after a4, blocked by {a4}.")
    S8 = d.step("Motion 7, B21 PROCESS_RETRIEVE (event e4): a6, the bay's first action. No geometric edge "
                "orders it after the car's arrival (the code marks bay transitions with a TODO).")
    S9 = d.step("Reduce() keeps only the edges not implied by others: a0 -> a3 goes (a0 -> a2 -> a3 remains).")
    S10 = d.step("TransferEventDagDepsToActionDag: for each event edge e -> e', last action of e -> first action "
                 "of e'. e3 -> e4 adds a5 -> a6 (amber): the order that only job logic knows. The others (f1 -> e2 "
                 "as a0 -> a2, e1 -> e2, e2 -> e3) exist already. Reduce() again; no VRC in this layout.")
    S11 = d.step("BuildScheduledActionsArray: one topological order becomes Schedule.nodes. Each in-edge becomes a "
                 "parent index; the entity's previous action is re-added if Reduce() removed it; each job "
                 "collects its node_indices. This array is the response.")
    s = 26
    m = Map(d, 0, 0, s, (20.4, 41.6), (18.1, 23.3))
    m.base(labels=True, zones=False, axes=False)
    mb = m.box
    sc = Scene(m)
    sc.tray("T23", 23, payload=True, chip_pos="tr")
    sc.agv("AGV-2", 22, heading=90, color=A2C, label_side="right")
    sc.agv("AGV-1", 23, heading=90, color=A1C, label_side="above")
    sc.drive(S2, "AGV-2", [22, 18], preview=False, color=A2C)
    sc.lift(S3, "AGV-1")
    sc.drive(S4, "AGV-1", [23, 22], preview=False, color=A1C)
    sc.drive(S5, "AGV-1", [22, 41], preview=False, color=A1C)
    sc.drive(S6, "AGV-1", [41, 21], preview=False, color=A1C)
    sc.lower(S7, "AGV-1")
    sc.draw()
    # location being added (sky) and blockers' locations (amber), per step
    cur = {S2: [22, 18], S3: [23], S4: [23, 22], S5: [22, 41], S6: [41, 21], S7: [21], S8: [21]}
    blk = {S4: [22], S5: [22], S6: [41], S7: [21]}
    for k, nids in cur.items():
        with d.only(k):
            for nid in nids:
                x, y = m.P(nid)
                d.circle(x, y, 13, fill="none", stroke=T.sky, sw=2.4, layer="top")
            if len(nids) == 2:
                (x0, y0), (x1, y1) = m.P(nids[0]), m.P(nids[1])
                d.line(x0, y0, x1, y1, stroke=T.sky, sw=5, opacity=0.5, layer="over")
    for k, nids in blk.items():
        with d.only(k):
            for nid in nids:
                x, y = m.P(nid)
                d.circle(x, y, 20, fill="none", stroke=T.amber, sw=2.2, dash="4 3", layer="top")

    # ---- all_motions list (under the map)
    ly = mb.y1 + 26
    d.text(0, ly, "all_motions : std::set<Motion, MotionScheduleOrder>", size=12, family="mono", weight=700,
           fill=T.fg)
    motions = [("[0, 4)", "AGV-2", "W22 -> W18", "f1", "a0", S2),
               ("[1, 3)", "AGV-1", "lift @P23", "e1", "a1", S3),
               ("[3, 5)", "AGV-1", "wait @P23", "e2", None, None),
               ("[5, 10)", "AGV-1", "P23 -> W22", "e2", "a2", S4),
               ("[10, 13)", "AGV-1", "W22 -> W41", "e2", "a3", S5),
               ("[13, 17)", "AGV-1", "W41 -> B21", "e2", "a4", S6),
               ("[17, 19)", "AGV-1", "lower @B21", "e3", "a5", S7),
               ("[19, 45)", "B21", "PROCESS_RETRIEVE", "e4", "a6", S8)]
    rowh = 21
    for i, (iv, ent, what, ev, act, k) in enumerate(motions):
        y = ly + 20 + i * rowh
        col = {"AGV-1": A1C, "AGV-2": A2C, "B21": BAYC}[ent]
        d.text(8, y, f"{iv:<9} {ent:<6} {what:<17} {ev}", size=11, family="mono", fill=T.fg2)
        if act is None:
            with d.at(S1):
                d.line(4, y, 330, y, stroke=T.red, sw=1.6)
                d.text(338, y, "dropped (wait)", size=10.5, fill=T.red)
        else:
            with d.at(k):
                d.text(338, y, "-> " + act, size=11, family="mono", weight=700, fill=col)
            with d.only(k):
                d.rect(2, y - 10, 400, 20, rx=4, fill=T.tint(T.sky, 0.16, T.bg), stroke=T.sky, sw=1,
                       layer="under")
    list_bottom = ly + 20 + len(motions) * rowh

    # ---- right: maps and the occupancy table
    rx = mb.x1 + 36
    rw = 470
    y = 0

    def panel(title, sub, rows, h_rows):
        nonlocal y
        h = 46 + 19 * h_rows + 6
        d.rect(rx, y, rw, h, rx=9, fill=T.card, stroke=T.border, sw=1.2)
        d.text(rx + 12, y + 16, title, size=12, family="mono", weight=700, fill=T.fg)
        d.text(rx + 12, y + 33, sub, size=10.5, fill=T.muted)
        for text, slot, k0, k1, col in rows:
            with d.at(k0, k1):
                d.text(rx + 14, y + 54 + 19 * slot, text, size=11, family="mono", fill=col)
        bb = BBox(rx, y, rx + rw, y + h)
        y += h + 10
        return bb

    p_last = panel("last_entity_action", "unordered_map<GarageEntityId, shared_ptr<ActionNodeMsg>>", [
        ("AGV-2 -> a0", 0, S2, S11, A2C),
        ("AGV-1 -> a1", 1, S3, S3, A1C), ("AGV-1 -> a2", 1, S4, S4, A1C), ("AGV-1 -> a3", 1, S5, S5, A1C),
        ("AGV-1 -> a4", 1, S6, S6, A1C), ("AGV-1 -> a5", 1, S7, S11, A1C),
        ("B21   -> a6", 2, S8, S11, BAYC)], 3)
    p_ev = panel("event_start_end", "unordered_map<event vertex, pair<first action, last action>>", [
        ("f1 -> (a0, a0)", 0, S2, S11, A2C), ("e1 -> (a1, a1)", 1, S3, S11, A1C),
        ("e2 -> (a2, a2)", 2, S4, S4, A1C), ("e2 -> (a2, a3)", 2, S5, S5, A1C), ("e2 -> (a2, a4)", 2, S6, S11, A1C),
        ("e3 -> (a5, a5)", 3, S7, S11, A1C), ("e4 -> (a6, a6)", 4, S8, S11, BAYC)], 5)
    p_occ = panel("freeing_moves.occupancy_state_ (excerpt)",
                  "location (pose or edge) -> occupant -> blocked collision ids; never cleared", [
        ("W22@90          -> a0", 0, S2, S3, T.fg2), ("W22@90          -> a0, a2", 0, S4, S4, T.fg2),
        ("W22@90          -> a0, a2, a3", 0, S5, S11, T.fg2),
        ("W22-W18, W18@90 -> a0", 1, S2, S11, T.fg2),
        ("P23@90          -> a1", 2, S3, S3, T.fg2), ("P23@90          -> a1, a2", 2, S4, S11, T.fg2),
        ("W41@90          -> a3", 3, S5, S5, T.fg2), ("W41@90          -> a3, a4", 3, S6, S11, T.fg2),
        ("B21@90          -> a4", 4, S6, S6, T.fg2), ("B21@90          -> a4, a5", 4, S7, S11, T.fg2)], 5)
    with d.only(S4):
        d.text(rx + rw - 12, p_occ.y1 - 12, "GetBlockers(P23-W22) = {a0, a1}", size=11, family="mono",
               fill=T.amber, anchor="end")
    with d.only(S5):
        d.text(rx + rw - 12, p_occ.y1 - 12, "GetBlockers(W22-W41) = {a0, a2}", size=11, family="mono",
               fill=T.amber, anchor="end")

    # ---- the action DAG
    gy0 = max(y, list_bottom) + 34
    d.text(0, gy0 - 14, "final_actions_dag : DagBase<ActionNodeMsg>", size=12, family="mono", weight=700,
           fill=T.fg)
    pos = {"a0": (40, gy0 + 22), "a1": (40, gy0 + 96), "a2": (170, gy0 + 59), "a3": (300, gy0 + 59),
           "a4": (430, gy0 + 59), "a5": (560, gy0 + 59), "a6": (690, gy0 + 59)}
    kfirst = {"a0": S2, "a1": S3, "a2": S4, "a3": S5, "a4": S6, "a5": S7, "a6": S8}
    colr = {"a0": A2C, "a6": BAYC}
    for n, (x, yy) in pos.items():
        with d.at(kfirst[n]):
            c = colr.get(n, A1C)
            d.circle(x, yy, 19, fill=T.tint(c, 0.18, T.bg), stroke=c, sw=2)
            d.text(x, yy, n, size=12, family="mono", weight=700, fill=c, anchor="middle")

    def edge(a, b, col, k0, k1=-1, dash=None, bend=0.0):
        (x0, y0), (x1, y1) = pos[a], pos[b]
        import math
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        sx, sy = x0 + ux * 21, y0 + uy * 21
        ex, ey = x1 - ux * 23, y1 - uy * 23
        ctx = d.at(k0, k1) if k1 >= 0 else d.at(k0)
        with ctx:
            if bend:
                mx, my = (sx + ex) / 2 - uy * bend, (sy + ey) / 2 + ux * bend
                d.path(f"M{sx} {sy} Q{mx} {my} {ex} {ey}", stroke=col, sw=2, dash=dash, layer="edges")
                d.arrowhead((ex, ey), (mx, my), kind="filled", color=col, size=9)
            else:
                d.line(sx, sy, ex, ey, stroke=col, sw=2, dash=dash, layer="edges")
                d.arrowhead((ex, ey), (sx, sy), kind="filled", color=col, size=9)

    edge("a1", "a2", CHAIN, S4)
    edge("a2", "a3", CHAIN, S5)
    edge("a3", "a4", CHAIN, S6)
    edge("a4", "a5", CHAIN, S7)
    edge("a0", "a2", OCC, S4)
    edge("a0", "a3", OCC, S5, S8, bend=-40)
    edge("a0", "a3", GONE, S9, S9, dash="4 4", bend=-40)
    edge("a5", "a6", EVT, S10)
    with d.only(S9):
        label_pill(d, 235, gy0 + 0, "removed by Reduce()", color=GONE, size=10.5, bg=T.bg)
    with d.at(S10):
        label_pill(d, 625, gy0 + 32, "event e3 -> e4", color=EVT, size=10.5, bg=T.bg)

    # ---- Schedule.nodes (S11)
    ay = gy0 + 140
    d.text(0, ay, "PlanResponse.schedule.nodes  (one topological order)", size=12, family="mono", weight=700,
           fill=T.fg)
    out = [("0", "a0", "AGV-2  W22->W18", "[]", "B"), ("1", "a1", "AGV-1  lift @P23", "[]", "A"),
           ("2", "a2", "AGV-1  P23->W22", "[0, 1]", "A"), ("3", "a3", "AGV-1  W22->W41", "[2]", "A"),
           ("4", "a4", "AGV-1  W41->B21", "[3]", "A"), ("5", "a5", "AGV-1  lower B21", "[4]", "A"),
           ("6", "a6", "B21  hand-over", "[5]", "A")]
    cw = 112
    for i, (idx, a, what, par, job) in enumerate(out):
        x = i * (cw + 6)
        with d.at(S11):
            d.rect(x, ay + 14, cw, 74, rx=7, fill=T.card, stroke=T.sky, sw=1.3)
            d.text(x + 8, ay + 30, f"[{idx}] {a}", size=11, family="mono", weight=700, fill=T.sky)
            d.text(x + 8, ay + 48, what[:16], size=10, family="mono", fill=T.fg2)
            d.text(x + 8, ay + 64, "parents " + par, size=10, family="mono", fill=T.fg2)
            d.text(x + 8, ay + 79, "job " + job, size=10, family="mono", fill=T.muted)
    with d.at(S11):
        d.text(0, ay + 108, "scheduled_jobs: job A node_indices = [1, 2, 3, 4, 5, 6], bay_arrival_node_guid = guid "
                            "of [6];  job B node_indices = [0]", size=11, family="mono", fill=T.fg2)
    # ---- code panel
    cp = code_panel(d, 0, ay + 130, rx + rw, [
        "for(const auto& motion : all_motions) {                       // start time, event vertex, hash",
        "  auto action_node = ToActionNode(motion, job_guid, event);    // fresh guid, job_id, command",
        "  event_start_end[event] = {first or unchanged, action_node};",
        "  final_actions_dag.AddDependency(last_entity_action[entity], action_node);   // same entity",
        "  for(auto& blocker : *freeing_moves.GetBlockers(motion.GetLocation(), collision_id, lifted))",
        "    final_actions_dag.AddDependency(blocker, action_node);      // every earlier occupant",
        "  freeing_moves.AddOccupant(motion.GetLocation(), collision_id, action_node, lifted);",
        "}",
        "final_actions_dag.Reduce();  TransferEventDagDepsToActionDag(...);  Reduce();  InsertVrcActionsIntoDag(...);",
        "return BuildScheduledActionsArray(ctx, final_actions_dag, *final_actions_dag.GetTopologicalOrdering());",
    ], title="Scheduler::ResponseFromTrajectories -> BuildActionDagFromMotions (abridged)", size=11)
    hl = {S1: (0, 0), S2: (1, 6), S3: (1, 6), S4: (3, 5), S5: (4, 5), S6: (2, 3), S7: (3, 6), S8: (1, 6),
          S9: (8, 8), S10: (8, 8), S11: (9, 9)}
    for k, (a, b) in hl.items():
        with d.only(k):
            _hl_code(d, cp, a, b)
    frame(d, title="Building the action DAG, motion by motion",
          subtitle="Blue rings: the location the current motion needs. Dashed amber rings: locations where an "
                   "earlier occupant blocks it. Times and occupied-location lists are illustrative; the real sets "
                   "come from the CollisionTable.",
          badge_key="yaml+hyp",
          legend=[("arrow", CHAIN, "same entity (last_entity_action)"), ("arrow", OCC, "occupancy (freeing_moves)"),
                  ("arrow", EVT, "event DAG edge"), ("dasharrow", GONE, "removed by Reduce()")])
    return d
