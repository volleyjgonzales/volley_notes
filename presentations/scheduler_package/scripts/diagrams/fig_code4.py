"""Code-walkthrough figures, part 4: motions -> actions, bays, coupling matrix, test map.

The coupling matrix and the test map are computed from sources/repomix-scheduler.xml, so they stay in
sync with the code snapshot that ships with this pack."""
from __future__ import annotations

import re
from pathlib import Path

from components import (EVENT_COLOR, chip, code_panel, connect, event_box, flow, frame, label_pill, note,
                        num_badge)
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T
import snapshot

DOC1 = "01-software-background.html"
DOC2 = "02-issue-and-proposal.html"
DOC3 = "03-verification-plan.html"
TRAY, AGV, BAYC = T.amber, T.green, T.violet


def scheduler_method_bodies() -> dict[str, str]:
    """Every top-level function in the snapshot's src/*.cpp (Scheduler methods and file-local helpers), by short
    name, comments blanked. See snapshot.py."""
    return snapshot.bodies()


# --------------------------------------------------------------------------------------
# 32 — from trajectories to ActionNode[]
# --------------------------------------------------------------------------------------

@figure("32_motions_to_actions", "From trajectories to ActionNode[]", DOC1)
def motions_to_actions():
    d = Doc("32_motions_to_actions", "From timed trajectories to the ActionNode schedule",
            "CHUGG returns per-entity trajectories; BuildActionGraph turns every non-wait motion into an "
            "ActionNode, builds an action DAG, and serialises it with integer parent indices.")
    W = 1060
    lane_x = 120
    px_s = (W - lane_x - 10) / 72.0
    lanes = [("AGV-1", AGV), ("Bay B21", BAYC)]
    motions = {
        0: [(0, 6, "13->15"), (6, 12, "15->17"), (12, 16, "lift"), (16, 24, "17->15 L"), (24, 31, "15->13 L"),
            (31, 38, "13->18 L"), (38, 45, "18->22 L"), (45, 51, "22->41 L"), (51, 58, "41->21 L"), (58, 62, "lower")],
        1: [(62, 71, "PROCESS_RETRIEVE")],
    }
    d.text(0, 0, "1 · ContinuousState trajectories from Chugg::SolveSequential()  (waits are not drawn)", size=12.5,
           weight=600, fill=T.fg)
    ly = 22
    lh = 44
    for i, (name, col) in enumerate(lanes):
        y = ly + i * (lh + 10)
        d.rect(0, y, W, lh, rx=8, fill=T.tint(col, 0.04, T.bg), stroke=T.border_soft, sw=1, layer="bg")
        d.text(12, y + lh / 2, name, size=12, family="mono", weight=700, fill=col)
        for t0, t1, lab in motions[i]:
            x0 = lane_x + t0 * px_s
            x1 = lane_x + t1 * px_s
            fill = T.tint(TRAY if lab.endswith("L") else col, 0.35, T.bg)
            stroke = TRAY if lab.endswith("L") else col
            d.rect(x0 + 1, y + 7, x1 - x0 - 2, lh - 14, rx=5, fill=fill, stroke=stroke, sw=1)
            d.text((x0 + x1) / 2, y + lh / 2, lab, size=10.5, family="mono", fill=T.fg, anchor="middle")
    ay = ly + 2 * (lh + 10)
    d.line(lane_x, ay, W - 10, ay, stroke=T.border, sw=1)
    for t in range(0, 73, 10):
        x = lane_x + t * px_s
        d.line(x, ay, x, ay + 5, stroke=T.border, sw=1)
        d.text(x, ay + 16, f"{t} s", size=10.5, family="mono", fill=T.muted, anchor="middle")
    d.text(lane_x, ay + 34, "\"L\" = AGV loaded: the motion's collision id is the tray/payload, so the action has lift = true",
           size=11, fill=T.muted)
    # conversion steps
    sy = ay + 66
    d.text(0, sy, "2 · Scheduler::BuildActionGraph(ctx, final_state)   (src/action_graph.cpp)", size=12.5, weight=600, fill=T.fg)
    steps = [("CollectAndCollapse...", "sort motions; drop waits;\ncollapse VRC floor rides"),
             ("BuildActionDag...", "ToActionNode per motion;\nentity chain + occupancy"),
             ("TransferEventDag...", "end of event -> start of\neach dependent event"),
             ("InsertVrcActions...", "VRC approach / move\ncommands where needed"),
             ("BuildScheduled...", "topological order ->\nparents; job indices")]
    sw_ = (W - 4 * 18) / 5
    prev = None
    for i, (t, sub) in enumerate(steps):
        x = i * (sw_ + 18)
        bb = BBox(x, sy + 16, x + sw_, sy + 92)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.card, stroke=T.sky, sw=1.2)
        num_badge(d, bb.x0, bb.y0 + 2, i + 1, T.sky, r=9)
        d.text(bb.x0 + 16, bb.y0 + 20, t, size=11.5, family="mono", weight=600, fill=T.sky)
        for j, ln in enumerate(sub.split("\n")):
            d.text(bb.x0 + 16, bb.y0 + 42 + j * 16, ln, size=11, fill=T.muted)
        if prev:
            connect(d, [(prev.x1, prev.cy), (bb.x0, bb.cy)], kind="flow", color=T.faint, size=7)
        prev = bb
    d.text(0, sy + 112, "RemoveRedundantEdges() runs after steps 2, 3 and 4 to drop implied edges; a cycle (\"The graph must be a DAG.\") or a failed ToActionNode fails the whole plan.", size=11,
           fill=T.muted)
    # table
    ty = sy + 146
    d.text(0, ty, "3 · PlanResponse.schedule.nodes  (ActionNode[] in topological order)", size=12.5, weight=600,
           fill=T.fg)
    cols = [("idx", 50), ("type", 170), ("entity", 70), ("command", 440), ("parents", 70), ("duration", 80)]
    rows = [("0", "TYPE_AGV_COMMAND", "AGV-1", "src {node_id: 13, heading: 90} -> dst {node_id: 15, heading: 90}", "[]", "6.0 s"),
            ("1", "TYPE_AGV_COMMAND", "AGV-1", "node_id 15 -> node_id 17 (heading 90, lift false)", "[0]", "6.0 s"),
            ("2", "TYPE_AGV_COMMAND", "AGV-1", "lift: src.lift false -> dst.lift true", "[1]", "4.0 s"),
            ("3 .. 8", "TYPE_AGV_COMMAND", "AGV-1", "node_id 17 -> 15 -> 13 -> 18 -> 22 -> 41 -> 21, lift true", "[n-1]",
             "..."),
            ("9", "TYPE_AGV_COMMAND", "AGV-1", "lower: lift true -> false", "[8]", "4.0 s"),
            ("10", "TYPE_BAY_COMMAND", "bay 21", "COMMAND_TYPE_PROCESS_RETRIEVE", "[9]", "9.0 s")]
    x = 0
    hy = ty + 18
    d.rect(0, hy, W, 26, rx=6, fill=T.muted_bg)
    for (c, w) in cols:
        d.text(x + 10, hy + 13, c, size=11, family="mono", weight=600, fill=T.fg2)
        x += w
    for r, row in enumerate(rows):
        y = hy + 30 + r * 26
        if r % 2 == 0:
            d.rect(0, y - 2, W, 26, rx=4, fill=T.tint(T.card, 0.6, T.bg), layer="bg")
        x = 0
        for (c, w), v in zip(cols, row):
            col = BAYC if "BAY" in v else (T.fg if c != "parents" else T.sky)
            d.text(x + 10, y + 11, v, size=11, family="mono", fill=col)
            x += w
    ny = hy + 30 + len(rows) * 26 + 10
    d.text(0, ny + 6, "ScheduledJobData for the retrieve job: node_indices = [0 .. 10], bay_id = 21, "
                      "bay_arrival_node_guid = guid of node 10", size=11.5, family="mono", fill=T.muted)
    frame(d, title="From timed trajectories to the ActionNode schedule",
          subtitle="Illustrative retrieve of the tray at P17 into B21 (nodes and times invented). The shape matches the "
                   "RetrieveJob.FromStall scenario: every node is an AGV command except the last, which is PROCESS_RETRIEVE, with "
                   "one lift and one lower.",
          badge_key="illustrative",
          legend=[("box", AGV, "unloaded AGV motion"), ("box", TRAY, "loaded AGV motion"),
                  ("box", BAYC, "bay command"), ("box", T.sky, "conversion step")])
    return d


# --------------------------------------------------------------------------------------
# 33 — bays: commanded transitions, classification, rebalancing
# --------------------------------------------------------------------------------------

@figure("33_bay_logic", "Bay states, classification and rebalancing", DOC1)
def bay_logic():
    d = Doc("33_bay_logic", "Bays: commanded transitions, classification and rebalancing",
            "Bay transitions the scheduler commands, ClassifyBay() rules from bay_rebalancing.cpp, and a worked example of "
            "ComputeBayRebalancingActions().")
    # ---- animation: commands, classification rules, then ComputeBayRebalancingActions() one loop at a time
    d.step("The three bay commands the scheduler issues: TRANSITION_TO_RETRIEVE (from READY_TO_INSERT or "
           "VEHICLE_INSERTED), TRANSITION_TO_INSERT (from READY_TO_RETRIEVE) and PROCESS_RETRIEVE. The other "
           "states are reached through bay or customer activity.")
    d.step("ClassifyBays() turns each bay's state, plus whether a tray and a payload sit in it, into a "
           "classification. A disabled bay, or a payload without a tray, is NOT_USABLE; a bay that is processing "
           "is INSERT_IN_PROGRESS or RETRIEVE_IN_PROGRESS.")
    d.step("Worked example: four bays in bay_prioritization order [1, 2, 3, 4]. Classified, bays 1 and 4 are "
           "RETRIEVE_READY (no tray) and bays 2 and 3 are INSERT_READY (empty tray, no car). None is NOT_USABLE.")
    d.step("CalculateDesiredBaySplit(): 4 eligible bays x target_insert_ready_bay_fraction 0.75, rounded up = 3 insert-ready bays wanted, "
           "capped by the 3 empty trays; the remaining 1 bay should be retrieve-ready.")
    d.step("Loop 1: a RETRIEVE_IN_PROGRESS bay counts as insert-ready (the finished retrieve leaves it ready to "
           "insert) and is never changed. None here, so the counts stay at 3 and 1. (An INSERT_IN_PROGRESS bay "
           "is not counted.)")
    d.step("Loop 2: walk bay_prioritization front to back and keep every bay that is already INSERT_READY until "
           "enough are found: bays 2 and 3 are kept, 1 insert-ready bay is still missing.")
    d.step("Loop 3: walk the list back to front and keep bays that are already RETRIEVE_READY: bay 4 is kept, so "
           "the retrieve-ready quota is met.")
    d.step("Loop 4: walk front to back again and pick bays to switch to insert. Bay 1 is RETRIEVE_READY and not "
           "kept, so it goes on the to-insert list; ExpandRebalanceGarageJob will run the READY_FOR_INSERT recipe "
           "(empty tray in, then TRANSITION_TO_INSERT).")
    d.step("Loop 5 (switch to retrieve, back to front) has nothing left to do, and loop 6 finds no bay left that "
           "NEEDS_EMPTY_TRAY / NEEDS_TRAY_REMOVAL (those would fall back to retrieve-ready). Result: to-insert [1], to-retrieve [], a single "
           "bay transition. Keeping correct bays (loops 2, 3) before changing any (loops 4, 5) keeps transitions few.")
    # --- state boxes
    S_ = {
        "RTI": (0, 80, "READY_TO_INSERT"),
        "VI": (0, 220, "VEHICLE_INSERTED"),
        "RTR": (330, 150, "READY_TO_RETRIEVE"),
        "PR": (330, 290, "PROCESSING_RETRIEVE"),
        "PI": (0, 350, "PROCESSING_INSERT"),
    }
    B = {}
    for k, (x, y, name) in S_.items():
        w = text_width(name, 12, "mono", 700) + 30
        bb = BBox(x, y, x + w, y + 42)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=21, fill=T.card, stroke=C_ if (C_ := T.teal) else T.teal, sw=1.4)
        d.text(bb.cx, bb.cy, name, size=12, family="mono", weight=700, fill=T.fg, anchor="middle")
        B[k] = bb
    d.text(0, 10, "what the scheduler commands (BayCommand.command_type)", size=12.5, weight=600, fill=T.fg)
    connect(d, [(B["RTI"].x1, B["RTI"].cy), (B["RTR"].x0 + 30, B["RTI"].cy), (B["RTR"].x0 + 30, B["RTR"].y0)],
            kind="flow", color=BAYC, size=8, sw=1.6, label="TRANSITION_TO_RETRIEVE",
            label_at=((B["RTI"].x1 + B["RTR"].x0 + 30) / 2 + 30, B["RTI"].cy))
    connect(d, [(B["VI"].x1, B["VI"].cy), (B["RTR"].x0 + 30, B["VI"].cy), (B["RTR"].x0 + 30, B["RTR"].y1)],
            kind="flow", color=BAYC, size=8, sw=1.6, label="TRANSITION_TO_RETRIEVE",
            label_at=((B["VI"].x1 + B["RTR"].x0 + 30) / 2 + 30, B["VI"].cy))
    connect(d, [(B["RTR"].cx + 40, B["RTR"].y0), (B["RTR"].cx + 40, B["RTI"].y0 - 20), (B["RTI"].cx, B["RTI"].y0 - 20),
                (B["RTI"].cx, B["RTI"].y0)], kind="flow", color=BAYC, size=8, sw=1.6,
            label="TRANSITION_TO_INSERT", label_at=((B["RTR"].cx + 40 + B["RTI"].cx) / 2 + 60, B["RTI"].y0 - 20))
    with d.only(7):     # loop 4 picks bay 1: its READY_FOR_INSERT recipe ends with this command
        lx_, ly_ = (B["RTR"].cx + 40 + B["RTI"].cx) / 2 + 60, B["RTI"].y0 - 20
        tw_ = text_width("TRANSITION_TO_INSERT", 11, "mono") + 30
        d.rect(lx_ - tw_ / 2, ly_ - 13, tw_, 26, rx=13, fill="none", stroke=T.amber, sw=1.8, layer="top")
    connect(d, [(B["RTR"].cx + 40, B["RTR"].y1), (B["PR"].cx + 40, B["PR"].y0)], kind="flow", color=BAYC, size=8,
            sw=1.6, label="PROCESS_RETRIEVE", label_at=(B["PR"].cx + 40, (B["RTR"].y1 + B["PR"].y0) / 2))
    for k_, ln_ in enumerate([
            "VEHICLE_INSERTED and PROCESSING_* come from bay / customer activity (BayReport.msg states 5, 6, 9).",
            "In the scheduler's own replay (BayTransition::ApplyTo), PROCESS_RETRIEVE goes straight from",
            "READY_TO_RETRIEVE to READY_TO_INSERT: the car leaves. Other bay states: BOOTING, DOOR_VALIDATION,",
            "TRANSITIONING_TO_INSERT / _RETRIEVE, ERROR. MOVE_LIFT_TO_FLOOR is sent by Dispatch for BLift bays."]):
        d.text(0, B["PI"].y1 + 24 + k_ * 16, ln_, size=11, fill=T.muted)
    # --- classification table
    tx = 610
    _tab = d.at(1)
    _tab.__enter__()
    d.text(tx, 10, "ClassifyBay(state, tray_in_bay, payload_in_bay)", size=12.5, weight=600, fill=T.fg)
    rows = [("any", "no", "yes", "NOT_USABLE"), ("READY_TO_INSERT", "yes", "no", "INSERT_READY"),
            ("READY_TO_INSERT", "other", "", "INSERT_NEEDS_EMPTY_TRAY"), ("READY_TO_RETRIEVE", "no", "no", "RETRIEVE_READY"),
            ("READY_TO_RETRIEVE", "other", "", "RETRIEVE_NEEDS_TRAY_REMOVAL"),
            ("PROCESSING_INSERT", "yes", "yes", "INSERT_IN_PROGRESS"),
            ("PROCESSING_RETRIEVE", "yes", "yes", "RETRIEVE_IN_PROGRESS"), ("anything else / disabled", "", "", "NOT_USABLE")]
    cw = [170, 44, 54, 0]
    y = 30
    d.rect(tx, y, 1120 - tx, 24, rx=5, fill=T.muted_bg)
    for c, w, xo in (("state", 170, 0), ("tray", 44, 170), ("payload", 54, 214)):
        d.text(tx + 8 + xo, y + 12, c, size=10.5, family="mono", weight=600, fill=T.fg2)
    d.text(tx + 8 + 274, y + 12, "classification", size=10.5, family="mono", weight=600, fill=T.fg2)
    for r, (st, tr, pl, cl) in enumerate(rows):
        yy = y + 30 + r * 24
        col = T.green if cl in ("INSERT_READY", "RETRIEVE_READY") else (T.red if cl == "NOT_USABLE" else T.amber)
        d.text(tx + 8, yy + 8, st, size=10.5, family="mono", fill=T.fg)
        d.text(tx + 178, yy + 8, tr, size=10.5, family="mono", fill=T.muted)
        d.text(tx + 222, yy + 8, pl, size=10.5, family="mono", fill=T.muted)
        d.text(tx + 282, yy + 8, cl, size=10.5, family="mono", fill=col)
        if r in (1, 3):     # the two rows the worked example's bays fall into
            with d.only(2):
                d.rect(tx - 4, yy - 4, 1120 - tx + 8, 24, rx=5, fill=T.tint(T.sky, 0.12, T.bg), stroke=T.sky,
                       sw=1.4, layer="bg")
    _tab.__exit__(None, None, None)
    # --- rebalancing example
    ey = 500
    with d.at(2):
        d.text(0, ey, "ComputeBayRebalancingActions(): worked example", size=12.5, weight=600, fill=T.fg)
        d.text(0, ey + 22, "bay_prioritization = [1, 2, 3, 4]  (front = preferred for insert, back = preferred for "
                          "retrieve)   fraction = 0.75   empty trays = 3", size=11.5, family="mono", fill=T.muted)
    with d.at(3):
        d.text(0, ey + 42, "eligible bays = 4  ->  insert-ready wanted = min(ceil(0.75 x 4), 3) = 3,  "
                          "retrieve-ready wanted = 1", size=11.5, family="mono", fill=T.fg2)
    # (name, classification, action, colour once decided, step that decides it)
    bays = [("bay 1", "RETRIEVE_READY", "loop 4: -> READY_FOR_INSERT job", T.amber, 7),
            ("bay 2", "INSERT_READY", "loop 2: keep (insert 1/3)", T.green, 5),
            ("bay 3", "INSERT_READY", "loop 2: keep (insert 2/3)", T.green, 5),
            ("bay 4", "RETRIEVE_READY", "loop 3: keep (retrieve 1/1)", T.green, 6)]
    bw = 245
    cy0 = ey + 92
    for i, (b, cl, act, col, k) in enumerate(bays):
        x = i * (bw + 16)
        bb = BBox(x, cy0, x + bw, cy0 + 80)
        with d.at(2, k - 1):
            d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=10, fill=T.card, stroke=T.border, sw=1.4)
        with d.at(k):
            d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=10, fill=T.card, stroke=col, sw=1.4)
            d.text(x + 14, bb.y0 + 64, act, size=11, fill=col)
        with d.only(k):
            d.rect(bb.x0 - 5, bb.y0 - 5, bb.w + 10, bb.h + 10, rx=13, fill="none", stroke=T.sky, sw=1.8,
                   dash="3 3")
        with d.at(2):
            d.text(x + 14, bb.y0 + 20, b, size=13, weight=600, fill=T.fg)
            d.text(x + 14, bb.y0 + 42, cl, size=11, family="mono", fill=T.teal)
    # scan direction of the loop running in this step
    x_l, x_r, sy = 6, 4 * (bw + 16) - 22, ey + 70
    for k, fwd, lab in ((5, True, "loop 2: bay_prioritization front -> back, keep INSERT_READY"),
                        (6, False, "loop 3: back -> front, keep RETRIEVE_READY"),
                        (7, True, "loop 4: front -> back, switch to insert"),
                        (8, False, "loop 5: back -> front, switch to retrieve (quota already met)")):
        with d.only(k):
            pts = [(x_l, sy), (x_r, sy)] if fwd else [(x_r, sy), (x_l, sy)]
            connect(d, pts, kind="flow", color=T.sky, size=8, sw=1.6, label=lab, label_at=((x_l + x_r) / 2, sy))
    # running counters, one line per step
    status = {2: "ClassifyBays(): 4 bays, none NOT_USABLE",
              3: "still wanted: insert-ready 3 · retrieve-ready 1",
              4: "loop 1: no bay RETRIEVE_IN_PROGRESS  ->  still wanted: insert-ready 3 · retrieve-ready 1",
              5: "loop 2: bays 2, 3 kept  ->  still wanted: insert-ready 1 · retrieve-ready 1",
              6: "loop 3: bay 4 kept  ->  still wanted: insert-ready 1 · retrieve-ready 0",
              7: "loop 4: bay 1 -> to-insert list  ->  still wanted: insert-ready 0 · retrieve-ready 0",
              8: "loops 5, 6: nothing to change  ->  result = (to insert: [1], to retrieve: [ ])"}
    for k, txt in status.items():
        with d.only(k):
            d.text(0, cy0 + 104, txt, size=11.5, family="mono", weight=600, fill=T.sky)
    with d.at(7):
        d.text(0, cy0 + 128, "Loops 2 and 3 keep bays that are already right before loops 4 / 5 change anything, so "
                             "the result needs as few bay transitions as possible.", size=11.5, fill=T.muted)
    frame(d, title="Bays: commanded transitions, classification and rebalancing",
          subtitle="The scheduler only commands three bay transitions. REBALANCE_GARAGE jobs classify every bay, work "
                   "out how many should be ready for insert, and plan READY_FOR_INSERT / READY_FOR_RETRIEVE recipes.",
          badge_key="as-built",
          legend=[("arrow", BAYC, "BayCommand issued by the scheduler"), ("box", T.green, "already in a wanted state"),
                  ("box", T.amber, "gets a transition job")])
    return d


# --------------------------------------------------------------------------------------
# 34 — coupling matrix for the two algorithms (doc 02)
# --------------------------------------------------------------------------------------

TRAY_FILE = "src/tray_assignment.cpp"
AGV_FILE = "src/agv_assignment.cpp"
COLS = [("layout_", "layout_", "member"), ("graph", "motion_graph_", "member"),
        ("table", "collision_table_", "member"), ("cost_", "cost_model_", "member"), ("log", "logger_", "member"),
        ("dag", "event_dag", "ctx"), ("init", "initial_state", "ctx"), ("first", "first_event_by_tray", "ctx"),
        ("filt", "FindKeepOutFilter|keep_out_filter_by_footprint", "ctx"),
        ("SSS", "SingleSourceSearch", "ext"), ("Static", "BuildStaticObstacleFilter", "ext"),
        ("Path", "FindPosePath", "ext"), ("BA", "BottleneckAssignment", "ext")]


def _stage_rows(path: str, entry: str) -> list[str]:
    """Functions defined in one stage file: the entry point, then the others in file order (the stage files list
    what the entry point calls in call order, after the file-local helpers)."""
    fns = [f.name.split("::")[-1] for f in sorted(snapshot.functions().values(), key=lambda f: f.line)
           if f.path == path]
    return [entry] + [f for f in fns if f != entry]


@figure("34_coupling_matrix", "What the two algorithms touch", DOC2)
def coupling_matrix():
    d = Doc("34_coupling_matrix", "What AssignTrays and AssignAgvs touch",
            "Matrix of Scheduler members, PlanContext fields and external functions used by each function in "
            "tray_assignment.cpp and agv_assignment.cpp, plus callers outside those files. Computed from the snapshot.")
    bodies = scheduler_method_bodies()
    tray_rows, agv_rows = _stage_rows(TRAY_FILE, "AssignTrays"), _stage_rows(AGV_FILE, "AssignAgvs")
    tree = set(tray_rows) | set(agv_rows)
    members = {f.name.split("::")[-1] for f in snapshot.functions().values() if f.name.startswith("Scheduler::")}
    names = list(bodies)

    def uses(name, token):
        return re.search(r"\b(?:" + token + r")\b", bodies.get(name, "")) is not None

    def outside_callers(name):
        return [other for other in names
                if other not in tree and other != name and re.search(r"\b" + name + r"\(", bodies[other])]

    name_w = 300
    cw = 50
    TW = 1240
    callers_w = TW - name_w - cw * len(COLS)
    rh = 26
    groups = [("Scheduler members", "member", T.sky), ("PlanContext", "ctx", T.green), ("other packages", "ext", T.violet)]
    x = name_w
    for gname, gkey, gcol in groups:
        n = sum(1 for c in COLS if c[2] == gkey)
        d.rect(x + 2, 0, n * cw - 4, 22, rx=6, fill=T.tint(gcol, 0.16, T.bg), stroke=T.tint(gcol, 0.6, T.bg), sw=1)
        d.text(x + n * cw / 2, 11, gname, size=11, weight=600, fill=gcol, anchor="middle")
        x += n * cw
    d.text(x + 10, 11, "also called from outside these files", size=11, weight=600, fill=T.amber)
    hy = 30
    for i, (short, _, kind) in enumerate(COLS):
        cx = name_w + i * cw + cw / 2
        d.text(cx, hy + 10, short, size=10.5, family="mono", weight=600, fill=T.fg2, anchor="middle")
    y = hy + 30

    def section(title, rows, col):
        nonlocal y
        d.text(0, y + 8, title, size=12, family="mono", weight=700, fill=col)
        y += 22
        for r, name in enumerate(rows):
            if r % 2 == 0:
                d.rect(0, y - 3, TW, rh, rx=4, fill=T.tint(T.card, 0.6, T.bg), layer="bg")
            entry = r == 0
            is_member = name in members
            label = name + "()" + ("" if is_member else "  (free)")
            d.text(0 if entry else 14, y + 10, label, size=11.5, family="mono",
                   weight=700 if entry else 400, fill=T.fg if entry else (T.fg2 if is_member else T.muted))
            for i, (short, tok, kind) in enumerate(COLS):
                cx = name_w + i * cw + cw / 2
                gcol = {"member": T.sky, "ctx": T.green, "ext": T.violet}[kind]
                if uses(name, tok):
                    d.circle(cx, y + 10, 6.5, fill=gcol)
                else:
                    d.circle(cx, y + 10, 2, fill=T.border_soft)
            oc = outside_callers(name)
            if oc:
                lines = wrap(", ".join(oc), callers_w - 16, 11, "mono")
                d.text(name_w + len(COLS) * cw + 10, y + 10, lines[0] + (" ..." if len(lines) > 1 else ""), size=11,
                       family="mono", fill=T.amber)
            y += rh
        y += 14

    section("tray assignment: src/tray_assignment.cpp", tray_rows, TRAY)
    section("AGV assignment: src/agv_assignment.cpp", agv_rows, AGV)
    d.text(0, y + 4, "Column key: graph = motion_graph_, table = collision_table_, cost_ = cost_model_, log = logger_, "
                     "dag = event_dag, init = initial_state, first = first_event_by_tray, filt = FindKeepOutFilter,",
           size=11, fill=T.muted)
    d.text(0, y + 20, "SSS = SingleSourceSearch, Static = BuildStaticObstacleFilter, Path = FindPosePath "
                      "(motion_planner), BA = BottleneckAssignment (task_planner). (free) = file-local function.",
           size=11, fill=T.muted)
    frame(d, title="What AssignTrays and AssignAgvs touch",
          subtitle="Each row is a function defined in one of the two stage files, entry point first. Filled dots mark "
                   "what its body names. The right column lists callers outside the two files: helpers that cannot "
                   "simply move into a solver.",
          badge_key="as-built",
          legend=[("dot", T.sky, "Scheduler member"), ("dot", T.green, "PlanContext field or helper"),
                  ("dot", T.violet, "function from another package")],
          footnote="Generated by scripts/diagrams/fig_code4.py from sources/repomix-scheduler.xml (main at a468657f; "
                   "comments blanked, text match on the function body). Indirect use through a callee is not counted "
                   "on the caller's row; state passed in as TrayAssignmentState / AgvAssignmentState is not a column.")
    return d


# --------------------------------------------------------------------------------------
# 35 — where each test enters the pipeline (doc 03)
# --------------------------------------------------------------------------------------

ENTRY = [
    ("Plan() + scenario file", ["Plan", "ExpectDeterministic"], T.sky),
    ("tray assignment", ["AssignTrays", "ResolveBlockingTrays"], TRAY),
    ("AGV assignment", ["AssignAgvs", "ComputeTravelDuration", "ComputeAgvPickupDuration",
                        "ComputeAgvAssignmentCost"], AGV),
    ("validation / motion / action graph", ["ValidateEventSequence", "PlanMotions", "BuildActionGraph"], T.violet),
    ("utils, context & YAML", ["ValidateBaseState", "ClassifyBay", "ClassifyBays", "ComputeBayRebalancingActions",
                               "CalculateDesiredBaySplit", "CountEmptyTrays", "SetBayReadinessRatioCallback",
                               "ChainAfterLastEntityEvent", "YAML::Load"], T.teal),
]
CALL_PAT = {"Plan": r"(?:scenarios::|[.>])Plan\(", "YAML::Load": r"\bYAML::Load\("}
FOLDER_COL = {"jobs": T.sky, "stages": T.pink, "utils": T.teal}
GAP_CANDIDATES = ["ExpandJob", "OrderAgvMovesAfterBlockingAgvs", "OrderAllTransitionsAroundAgvLifts",
                  "ValidateMoveDestinationAndPath", "InsertVrcActionsIntoDag"]


def _test_files() -> dict[str, str]:
    return {p: snapshot.blank_comments(src) for p, src in snapshot.source_files().items()
            if p.startswith("test/src/") and p.endswith("_tests.cpp")}


def _tests():
    """[(path, suite, name, [entry indices it calls])] for every TEST in the snapshot's test/src/*/*_tests.cpp."""
    out = []
    for path, src in sorted(_test_files().items()):
        heads = [(m.start(), m.group(1), m.group(2)) for m in re.finditer(r"^TEST\((\w+),\s*(\w+)\)", src, re.M)]
        for i, (p, suite, name) in enumerate(heads):
            body = src[p:heads[i + 1][0] if i + 1 < len(heads) else len(src)]
            idx = [k for k, (_, fns, _) in enumerate(ENTRY)
                   if any(re.search(CALL_PAT.get(fn, r"\b" + fn + r"\("), body) for fn in fns)]
            out.append((path, suite, name, idx))
    return out


def _camel_wrap(name, width, size):
    parts = re.findall(r"[A-Z0-9]+[a-z0-9]*|[a-z]+", name)
    lines, cur = [], ""
    for p in parts:
        if text_width(cur + p, size, "mono") > width and cur:
            lines.append(cur)
            cur = p
        else:
            cur += p
    lines.append(cur)
    return lines


@figure("35_test_entry_points", "Where each test enters the pipeline", DOC3)
def test_map():
    d = Doc("35_test_entry_points", "Where the scheduler's tests enter the pipeline",
            "Every TEST in the scheduler package placed under the earliest pipeline stage it calls directly, grouped "
            "by test file and coloured by folder. Computed from the test sources.")
    tests = _tests()
    W = 1120
    ncol = len(ENTRY)
    gap = 14
    cw = (W - (ncol - 1) * gap) / ncol
    cols: dict[int, dict[str, list]] = {i: {} for i in range(ncol)}
    for path, suite, name, idx in tests:
        i = min(idx) if idx else ncol - 1
        cols[i].setdefault(path, []).append((suite, name, len(idx) - 1 if idx else 0))
    top = 0
    bottoms = []
    for i, (title, fns, col) in enumerate(ENTRY):
        x = i * (cw + gap)
        n = sum(len(v) for v in cols[i].values())
        d.rect(x, top, cw, 44, rx=8, fill=T.tint(col, 0.15, T.bg), stroke=col, sw=1.3)
        d.text(x + 12, top + 17, title, size=12, weight=600, fill=col)
        d.text(x + 12, top + 34, f"{n} tests", size=11, fill=T.muted)
        if i < 3:
            connect(d, [(x + cw, top + 22), (x + cw + gap, top + 22)], kind="flow", color=T.faint, size=6)
        y = top + 58
        for path, rows in sorted(cols[i].items(), key=lambda kv: (Path(kv[0]).parent.name, kv[0])):
            folder = Path(path).parent.name
            fcol = FOLDER_COL.get(folder, T.fg2)
            suites = sorted({s for s, _, _ in rows})
            lines = []
            for suite, name, extra in rows:
                wl = _camel_wrap(name, cw - 40, 11)
                lines.append((wl, extra))
            h = 24 + sum(15 * len(wl) for wl, _ in lines) + 6
            d.rect(x, y, cw, h, rx=6, fill=T.card, stroke=T.border_soft, sw=1)
            d.rect(x + 1, y + 1, 4, h - 2, rx=2, fill=fcol)
            head = Path(path).stem + "  (" + ", ".join(suites) + ")"
            head = wrap(head, cw - 22, 10, "mono")[0]
            d.text(x + 12, y + 12, head, size=10, family="mono", weight=700, fill=fcol)
            yy = y + 30
            for wl, extra in lines:
                for j, ln in enumerate(wl):
                    d.text(x + 12 + (8 if j else 0), yy + j * 15, ln, size=11, family="mono", fill=T.fg2)
                if extra:
                    d.text(x + cw - 6, yy, "+" + str(extra), size=10, family="mono", fill=T.muted, anchor="end")
                yy += 15 * len(wl)
            y += h + 6
        bottoms.append(y)
    # gaps: stage functions no test calls directly
    tsrc = "\n".join(_test_files().values())
    untested = [f for f in GAP_CANDIDATES if not re.search(r"\b" + f + r"\(", tsrc)]
    files = len(_test_files())
    nx = 1 * (cw + gap)
    ny = max(bottoms[1:]) + 10
    note(d, nx, ny, 3 * cw + 2 * gap,
         ("No test calls " + ", ".join(untested) + " directly; they run only inside larger tests. " if untested else "")
         + "Each Plan() test loads test/scenarios/plan/<suite>/<Name>.yaml; each job file's Deterministic test plans "
           "every scenario of its suite twice and compares the responses. Stage tests load "
           "test/scenarios/task_planning/<stage>/. A recorded output is compared only with "
           "SCHEDULER_CHECK_RECORDINGS=1.", title="Gaps worth knowing", accent=T.amber)
    frame(d, title="Where the scheduler's tests enter the pipeline",
          subtitle=f"{len(tests)} TEST cases in {files} files (one gtest binary each), placed under the earliest stage "
                   "each calls. \"+n\" means it also calls n later stages. Job-level behaviour is tested end to end "
                   "through Plan() with one scenario file per test.",
          badge_key="as-built",
          legend=[("fill", FOLDER_COL["jobs"], "test/src/jobs/"),
                  ("fill", FOLDER_COL["stages"], "test/src/stages/"),
                  ("fill", FOLDER_COL["utils"], "test/src/utils/")],
          footnote="Generated from sources/repomix-scheduler.xml (main at a468657f) by scripts/diagrams/fig_code4.py.")
    return d
