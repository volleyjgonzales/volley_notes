"""Tray-assignment helpers drawn the same way as the job figures: AssignTrayIdForEmptyMove and
AssignDestForUntargetedMove (with ResolveBlockingTrays)."""
from __future__ import annotations

import fig_jobs as J
from components import label_pill, num_badge
from facility import STALL_L, STALL_W
from fig_jobs import (GENERAL, TRAY, BAYC, _EV_STEP, _intent, bay_pill, ghost, job_figure)
from registry import figure
from theme import T

DOC1 = "01-software-background.html"

LEGEND = [("box", TRAY, "TrayMove"), ("dashbox", TRAY, "event before the call (blank shown as ?)"),
          ("arrow", TRAY, "edge added by the call"), ("ring", T.fg2, "? = blank field")]


def ring(d, m, nid, color, *, w=None, h=None, dx=0, dy=0):
    """Transient highlight ring around a node / stall."""
    x, y = m.P(nid)
    w = w or STALL_L * m.s - 2
    h = h or STALL_W * m.s - 2
    d.rect(x + dx - w / 2, y + dy - h / 2, w, h, rx=8, fill="none", stroke=color, sw=2.4, dash="4 3", layer="top")


def xmark(d, m, nid, color=T.red, *, dx=0, dy=0):
    x, y = m.P(nid)
    x, y = x + dx, y + dy
    d.circle(x, y, 9, fill=T.bg_deep, stroke=color, sw=1.6, layer="top")
    d.line(x - 4, y - 4, x + 4, y + 4, stroke=color, sw=2, layer="top")
    d.line(x - 4, y + 4, x + 4, y - 4, stroke=color, sw=2, layer="top")


def wave(d, m, nid, n, *, dx=0, dy=-18, color=T.sky):
    x, y = m.P(nid)
    d.circle(x + dx, y + dy, 9, fill=T.bg_deep, stroke=color, sw=1.4, layer="top")
    d.text(x + dx, y + dy + 0.5, str(n), size=10, family="mono", weight=700, fill=color, anchor="middle",
           layer="top")


# --------------------------------------------------------------------------------------
@figure("55_assign_tray_id_empty", "AssignTrayIdForEmptyMove", DOC1)
def assign_tray_id():
    GENERAL["55_assign_tray_id_empty"] = [
        "An empty-tray move must at least say where the tray should go. Without a destination there is nothing "
        "to search from.",
        "The search starts at the destination and grows outward, because the question is 'which empty tray is "
        "closest to where it is needed?'.",
        "Build the graph filter for a tray footprint with every tray and AGV left out, so occupied nodes do not "
        "stop the search; only disabled or static obstacles do.",
        "Run the search. The environment's goal is a node that holds a tray with no payload. Each edge costs its "
        "trapezoid time plus 30 s for every tray it crosses, so a near tray behind blockers can lose to a farther one.",
        "If no empty tray is reachable, the whole tray assignment fails with this message.",
        "Take the tray on the node the search reached and write its id into the existing event. The event "
        "object is edited in place; nothing is added to the DAG.",
        "Avoid a pointless rotation: if the tray already sits on the same axis as the destination heading, keep "
        "the tray's heading (except on the 576_eccles EV-charging nodes).",
        "Return. DoTrayAssignments then treats the event like any other complete move and runs the blocking-tray "
        "loop for it.",
    ]

    def draw(d, m, sc):
        # steps: 0 start, 1 dest check, 2 start vertex, 3 filter, 4 search, 5 fail check (skipped),
        # 6 tray id written, 7 heading check, 8 return; then the playback steps
        PE = J._PLAN_END
        _EV_STEP[2] = 6                       # the "after" box appears when the tray id is written
        bay_pill(d, m, 21, "B21 READY_TO_RETRIEVE (empty)")
        sc.tray("T23 (empty)", 23, emphasis=True, chip_pos="bl")
        sc.tray("T15 (empty)", 15, chip_pos="bl")
        sc.tray("T17", 17, payload=True, chip_pos="bl")
        sc.tray("T19", 19, payload=True, chip_pos="bl")
        sc.tray("T20", 20, payload=True, chip_pos="bl")
        sc.tray("T24", 24, payload=True, chip_pos="bl")
        sc.agv("AGV-1", 27, heading=90, label_side="above")   # invented: the helper assigns no AGV
        bx, by = m.P(21)
        with d.at(0, 5):                      # the blank: which tray?
            d.circle(bx + 40, by + 34, 12, fill=T.bg_deep, stroke=TRAY, sw=2, layer="top")
            d.text(bx + 40, by + 34.5, "?", size=14, family="mono", weight=700, fill=TRAY, anchor="middle",
                   layer="top")
            label_pill(d, bx + 58, by + 34, "tray_id ? -> B21", color=TRAY, size=10, anchor="start", bg=T.bg_deep,
                       border=TRAY)
        with d.only(1):                       # dest is set
            ring(d, m, 21, T.green, w=STALL_L * m.s - 20, h=STALL_W * m.s - 14)
            label_pill(d, bx + 58, by - 30, "dest {node_id: 21, heading: -90}", color=T.green, size=10,
                       anchor="start", bg=T.bg_deep, border=T.green)
        with d.at(2, PE):                     # start vertex
            wave(d, m, 21, 0, dx=40)
        with d.only(2):
            label_pill(d, bx + 58, by - 30, "start = B21 (dest pose)", color=T.sky, size=10, anchor="start",
                       bg=T.bg_deep, border=T.sky)
        with d.only(3):                       # filter: trays and AGVs are not obstacles
            for nid in (23, 15, 17, 19, 20, 24):
                ring(d, m, nid, T.sky)
            x, y = m.P(19)
            label_pill(d, x, y, "trays + AGVs left out: not obstacles", color=T.sky, size=10, bg=T.bg_deep,
                       border=T.sky)
        with d.at(4, PE):                     # search: order the nodes are reached
            wave(d, m, 41, 1)
            wave(d, m, 22, 2, dx=18)
            wave(d, m, 25, 3, dx=18)
            wave(d, m, 18, 3, dx=18)
            wave(d, m, 23, 3, dx=-40, dy=-26, color=T.green)
            x, y = m.P(23)
            label_pill(d, x + 20, y - 66, "goal: tray without payload", color=T.green, size=10, anchor="middle",
                       bg=T.bg_deep, border=T.green)
        with d.only(4):                       # candidates considered
            ring(d, m, 23, T.green)
            x, y = m.P(15)
            label_pill(d, x, y - 14, "also empty, farther: not reached", color=T.muted, size=10, bg=T.bg_deep,
                       border=T.faint)
        with d.at(6, PE):                     # tray id written: T23 -> B21
            _intent(d, m, 23, 21, 1, TRAY, bend=0.3, dst_off=(40, 0), num_t=0.55)
        with d.only(6):
            ring(d, m, 23, TRAY)
        with d.only(7):                       # heading check
            ring(d, m, 23, T.fg2)
            x, y = m.P(23)
            label_pill(d, x, y + 16, "T23 faces 90 = dest axis: keep", color=T.fg2, size=10, bg=T.bg_deep,
                       border=T.fg2)
        with d.at(8, PE):                     # next: blocking-tray loop on T23's path
            m.route([23, 22, 41, 21], T.sky, sw=2, dash="2 4", offset=(0, 12), head=True)
            x, y = m.P(41)
            label_pill(d, x - 20, y + 30, "next: blocking-tray loop on this path", color=T.sky, size=10,
                       bg=T.bg_deep, border=T.sky)

    return job_figure(
        "55_assign_tray_id_empty", heading="AssignTrayIdForEmptyMove: which empty tray?",
        subtitle="A READY_FOR_INSERT job asked for 'an empty tray into bay B21' without saying which. This helper "
                 "searches outward from the bay for the nearest tray without a payload and writes its id into the "
                 "event.",
        req=[("call", "AssignTrayIdForEmptyMove(*move, working_state)"),
             ("move", "volley::TrayMove&: tray_id ?, dest {node_id: 21, heading: -90}"),
             ("", "  created by PlanReadyForInsertJob (job 0)"),
             ("working_state", "const DiscreteGarageState&: the garage after all earlier events"),
             ("called from", "DoTrayAssignments :2575, PlanReadyForInsertJob fill pass"),
             ("returns", "BoolStringPair")],
        request_title="Input", region="qa", draw_map=draw,
        map_caption="search from B21 outward; numbers = order the nodes are reached (illustrative)",
        events=[("TrayMove", "tray_id ? -> {node_id: 21, heading: -90}", 0, "optional", "before: tray id blank"),
                ("TrayMove", "tray_id 23: P23 -> {node_id: 21, heading: -90}", 0, "solid", "after: the same event object, tray id set")],
        edges=[],
        events_title="The event, before and after", events_sub="no events or edges are added by this helper",
        steps=[
            ("if(!move.GetDest())\n  return {false, \"Can't resolve a tray move with no tray id or dest\"}",
             "dest = {node_id: 21, heading: -90}, the bay's inbound pose (heading 90, faces_reciprocal: true).", "passes", "ok"),
            ("source.vert = gg_.GetVertexFromPose(move.GetDest().value())", "Start vertex = the one for {node_id: 21, heading: -90}.",
             "start = B21", "ok"),
            ("trays = all tray ids; agvs = all AGV ids;\nfilters = GetStaticFilter(TRAY, gg_, working_state, "
             "table_,\n  trays, agvs, {})", "All six trays and every AGV are left out of the filter.", "filter",
             "ok"),
            ("EmptyTraySearchEnvironment env(gg_, table_, working_state,\n  cost_model_, filters);\n"
             "solution = SingleSourceSearch(source, Duration(0), env)",
             "Reached in order: W41, W22, then W25, W18 and P23. P23 holds T23, which carries no car.",
             "found P23", "ok"),
            ("if(!solution.GetTarget()) return {false, \"Failed to find empty tray ...\"}", "A tray was found.",
             "skipped", "skip"),
            ("tray_to_use = working_state.GetTrayOnNode(\n  GetPoseFromVertex(target.vert)\n    ->node_id).value();\n"
             "move.SetTrayId(tray_to_use.id)", "The event now reads T23: P23 -> B21.", "tray = 23", "event"),
            ("if IsAngleOrReciprocal(tray.heading, dest.heading)\n  && tray.heading != dest.heading:\n"
             "  dest.heading = tray.heading; UseEvChargeHeading(dest);\n  move.SetDest(dest)",
             "T23 faces 90, the destination asks for 90: nothing to change.", "no change", "skip"),
            ("return {true, \"\"}", "Next: the blocking-tray loop for T23's path to B21 (P23 -> W22 -> W41 -> B21).",
             "success", "ok"),
        ],
        notes=[("Why the destination is the start", "The job knows where a tray is needed but not which tray is "
                "best. Searching from the destination finds the closest candidate, so the AGV carries an empty tray "
                "as short a way as possible.", T.sky),
               ("Not reserved", "Nothing marks T23 as taken. Later moves see it in B21 because DoTrayAssignments "
                "applies each move to working_state before the next event. A TODO in the code suggests choosing a "
                "tray that is a future blocker anyway.", T.amber),
               ("Same helper, two callers", "PlanReadyForInsertJob calls it early (best effort, PlanReadyForInsertJob); "
                "DoTrayAssignments calls it for every move still blank, with the full picture of all jobs.",
                T.border)],
        legend_override=LEGEND, bw=330)


# --------------------------------------------------------------------------------------
@figure("56_assign_dest_untargeted", "AssignDestForUntargetedMove", DOC1)
def assign_dest():
    GENERAL["56_assign_dest_untargeted"] = [
        "A move without a destination must at least name its tray, and that tray must exist in the current "
        "garage.",
        "A tray with a car must end at a heading that allows a fast retrieve later; an empty tray may park any "
        "way.",
        "Ask ResolveBlockingTrays for a parking spot. Steps 4 to 7 happen inside it, on a private copy of the "
        "garage.",
        "Search outward from the tray for the cheapest free parking node. The search may path through other "
        "trays; it returns the spot and the trays in the way. The nodes on that path (except the spot itself) "
        "become off-limits for blockers.",
        "Find a new spot for the first blocker that can be resolved. If that spot is blocked too, recurse into "
        "ResolveBlockingTrays with the root tray marked immobile. If no parking is reachable, try a waypoint "
        "stash (tier 2).",
        "Record the blocker's move and apply it to the private copy, so the next search sees the new layout.",
        "Search again for the root tray. Repeat until a spot with nothing in the way is found, or fail (after "
        "the tier-2 waypoint stash).",
        "Choose the heading (parking node: empty tray keeps its axis, loaded tray uses the preferred heading) and "
        "write the destination into the existing event.",
        "Turn the recorded blocker moves into real events: apply each, add it to the DAG, chain them in order, "
        "chain per tray, and add edges from earlier moves that free or use the same space (freeing_moves).",
        "Apply the root move and make it wait for the last blocker move; update the per-tray chain and "
        "first_tray_event.",
        "Return. DoTrayAssignments skips its main blocking-tray loop for this event (continue), because its "
        "blockers were handled here.",
    ]

    def draw(d, m, sc):
        # steps: 0 start, 1 tray check, 2 payload, 3 call RBT, 4 1st search, 5 blocker resolution,
        # 6 record + apply to private copy, 7 search again, 8 dest set, 9 blocker events, 10 root move, 11 return;
        # then the playback steps
        PE = J._PLAN_END
        _EV_STEP.clear()
        _EV_STEP.update({2: 9, 3: 10})        # event 2 at row 9; the 'after' event and its edge at row 10
        sc.tray("T21 (empty)", 21, emphasis=True, chip_pos="tr")
        with d.at(0, PE):
            bay_pill(d, m, 21, "B21: tray must leave")
        sc.tray("T23 (empty)", 23, chip_pos="bl")
        sc.tray("T9 stash", 25, chip_pos="bl")
        sc.tray("T19", 19, payload=True, chip_pos="bl")
        sc.tray("T15", 15, chip_pos="bl")
        sc.tray("T17", 17, payload=True, chip_pos="bl")
        sc.tray("T20", 20, payload=True, chip_pos="bl")
        sc.agv("AGV-1", 26, heading=90, label_side="below")   # invented: the helper assigns no AGV
        bx, by = m.P(21)
        with d.at(0, 7):                      # the blank destination
            _intent(d, m, 21, None, 1, TRAY, src_off=(40, 10), q_off=(70, 60), num_t=0.5)
        with d.only(1):
            ring(d, m, 21, T.green, w=STALL_L * m.s - 20, h=STALL_W * m.s - 14)
        with d.only(2):
            label_pill(d, bx - 30, by + 40, "T21 empty: any heading", color=T.green, size=10, anchor="start",
                       bg=T.bg_deep, border=T.green)
        b = m.box
        with d.at(3, 7):                      # ResolveBlockingTrays works on a private copy
            d.rect(b.x0 + 4, b.y0 + 4, b.w - 8, b.h - 8, rx=9, fill="none", stroke=T.teal, sw=2, dash="8 5",
                   layer="top")
            label_pill(d, b.x1 - 14, b.y1 - 18, "inside ResolveBlockingTrays: private copy of the garage",
                       color=T.teal, size=10, anchor="end", bg=T.bg_deep, border=T.teal)
        with d.at(4, PE):                     # tier-1 search: P24, T23 in the way
            m.route([21, 41, 22, 23, 24], T.red, sw=2.5, dash="3 4", offset=(0, -10), num=1, num_at=1)
            x, y = m.P(24)
            label_pill(d, x, y - 30, "1st search: P24, T23 in the way", color=T.red, size=10, bg=T.bg_deep,
                       border=T.red)
        with d.only(4):
            ring(d, m, 23, T.red)
            ring(d, m, 25, T.amber, w=STALL_L * m.s - 30)
        with d.at(5, 6):                      # off-limits for the blocker
            for nid, dx in ((41, 0), (22, 0), (23, -60)):
                xmark(d, m, nid, dx=dx, dy=18)
            x, y = m.P(22)
            label_pill(d, x - 12, y + 40, "off-limits for T23", color=T.red, size=10, anchor="end", bg=T.bg_deep,
                       border=T.red)
        with d.at(5, PE):                     # blocker pushed one stall deeper
            _intent(d, m, 23, 24, 2, TRAY, bend=0.35, num_t=0.5, src_off=(20, 8), dst_off=(-20, 8))
        with d.at(6, 8):                      # applied to the private copy only
            ghost(d, m, 24, "")
            gx, gy = m.P(24)
            d.text(gx + 22, gy + 26, "T23 (private copy)", size=10.5, family="mono", fill=TRAY, anchor="middle", halo=T.bg_deep,
                   halo_w=3)
        with d.at(9, PE):                     # applied to working_state as event 2
            ghost(d, m, 24, "")
            gx, gy = m.P(24)
            d.text(gx + 22, gy + 26, "T23 after event 2", size=10.5, family="mono", fill=TRAY, anchor="middle", halo=T.bg_deep,
                   halo_w=3)
        with d.only(7):                       # second search: P23, nothing in the way
            m.route([21, 41, 22, 23], T.green, sw=2.5, dash="3 4", offset=(0, 10))
            ring(d, m, 23, T.green)
            x, y = m.P(23)
            label_pill(d, x, y - 30, "2nd search: P23 free", color=T.green, size=10, bg=T.bg_deep,
                       border=T.green)
        with d.at(8, PE):                     # destination written
            _intent(d, m, 21, 23, 3, T.green, bend=-0.22, src_off=(40, 10), dst_off=(-30, 12), num_t=0.6,
                    dash=None)
        with d.only(8):
            x, y = m.P(23)
            label_pill(d, x - 85, y - 30, "dest {node_id: 23, heading: 90}", color=T.green, size=10, anchor="start",
                       bg=T.bg_deep,
                       border=T.green)
        with d.only(11):
            label_pill(d, bx - 30, by + 40, "main blocking-tray loop skipped", color=T.fg2, size=10, anchor="start",
                       bg=T.bg_deep, border=T.fg2)

    return job_figure(
        "56_assign_dest_untargeted", heading="AssignDestForUntargetedMove: where should this tray go?",
        subtitle="A RETRIEVE job planned 'empty tray T21 out of bay B21' without saying where. This helper asks "
                 "ResolveBlockingTrays for a parking spot, which may first move other trays out of the way, then "
                 "turns those extra moves into events.",
        req=[("call", "AssignDestForUntargetedMove(move, ctx, event, working_state,"),
             ("", "  freeing_moves, last_tray_event)"),
             ("move", "volley::TrayMove*: tray 21, dest ?  (created by PlanRetrieveJob)"),
             ("event", "const std::shared_ptr<ScheduleEvent>&: the same event, as a DAG vertex"),
             ("ctx", "ScheduleContextSPtr: events and first_tray_event are CHANGED"),
             ("working_state", "DiscreteGarageState&: CHANGED, moves are applied"),
             ("freeing_moves", "GarageOccupancyChecker<...>&: CHANGED"),
             ("last_tray_event", "unordered_map<uint16_t, ScheduleEventSPtr>&: CHANGED"),
             ("returns", "BoolStringPair")],
        request_title="Input", region="qa", draw_map=draw,
        map_caption="1 = first search result, 2 = blocker pushed deeper, 3 = final destination (illustrative)",
        events=[("TrayMove", "T21: B21 -> ?", 0, "optional", "before: destination blank"),
                ("TrayMove", "T23: P23 -> P24", 0, "solid", "NEW: blocker move, job_index 0"),
                ("TrayMove", "tray_id 21: B21 -> {node_id: 23, heading: 90}", 0, "solid", "after: same event as 1, dest set")],
        edges=[(2, 3, "A", "tray", "AddDependency(last_move, event)")],
        events_title="The DAG, before and after",
        events_sub="one new event and one new edge (plus any freeing_moves edges)",
        steps=[
            ("if(!move->GetTrayId()) fail;\ntray_opt = working_state.GetTray(*move->GetTrayId())",
             "T21 is in B21.", "passes", "ok"),
            ("enforce_retrieval_heading = working_state.GetPayload(\n  tray_opt->payload_id).has_value()",
             "T21 is empty.", "false", "ok"),
            ("auto [dest, required_moves] = ResolveBlockingTrays(\n  tray_id, job_index, working_state, {}, {},\n"
             "  enforce_retrieval_heading)", "allow_waypoint_stash keeps its default, true.", "call", "call"),
            ("FindOpenSpaceForRootTray(tray, entity, ws, immobile,\n  agvs, illegal, enforce, false)   // tier 1",
             "Every free spot near B21 is boxed in. Suppose the search returns P24 via P23, with T23 in the way "
             "(T9 sits on the W25 route).", "P24, 1 blocker", "ok"),
            ("TryFindBlockingTrayResolution(T23, root = T21, ...)",
             "W41, W22 and P23 are now off-limits for T23, but the target P24 is allowed: T23 can move one step "
             "deeper.", "T23 -> P24", "ok"),
            ("new_move = TrayMove(job_index); SetTrayId(23); SetDest(P24);\nnew_move->Apply(private copy);\n"
             "required_moves.push_back({new_move, path})", "P23 is free in the private copy.", "recorded", "ok"),
            ("loop: FindOpenSpaceForRootTray(...) again\n  no blocking trays -> dest = that pose",
             "The best spot is now P23, with nothing in the way.", "dest = P23", "ok"),
            ("parking + empty tray: keep tray heading if same axis;\nUseEvChargeHeading(dest); move->SetDest(dest)",
             "T21 faces 90 and so does P23.", "dest set", "event"),
            ("for each required move: Apply(working_state); AddEvent;\n  AddDependency(last_move, m);\n"
             "  last_tray_event / first_tray_event;\n  freeing_moves edges for every pose on its path",
             "Adds event 2, T23: P23 -> P24. first_tray_event[23] = event 2.", "adds 1 event", "event"),
            ("move->Apply(working_state);\nAddDependency(last_move, event);\nlast_tray_event[21] = event; "
             "first_tray_event[21] = event", "Edge event 2 -> event 3: T23 must be gone before T21 arrives.",
             "adds 1 edge", "event"),
            ("return {true, \"\"};   // DoTrayAssignments: continue", "The main blocking-tray loop is skipped "
             "for this event.", "success", "ok"),
        ],
        notes=[("Why 'push deeper'", "The code comment: resolve blockers 'in the order of fewest extra blocking "
                "moves ... This densifies nicely instead of reparking blocking trays halfway across the garage'. "
                "Here the blocker moves one stall and the root tray takes its place.", T.green),
               ("Two copies of the garage", "Steps 4 to 7 work on ResolveBlockingTrays' own copy. Step 9 applies "
                "the same moves again to the caller's working_state, which later events will see.", T.sky),
               ("Waypoint stash", "If no parking spot is reachable at all, tier 2 may return a waypoint (T9 on W25 "
                "is such a leftover). A later CLEAN_GARAGE job puts stashed trays back (PlanCleanGarageJob).",
                T.amber)],
        legend_override=LEGEND, bw=330)
