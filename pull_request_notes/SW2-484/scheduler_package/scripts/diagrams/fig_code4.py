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

DOC1 = "01-software-background.html"
DOC2 = "02-issue-and-proposal.html"
DOC3 = "03-verification-plan.html"
TRAY, AGV, BAYC = T.amber, T.green, T.violet
ROOT = Path(__file__).resolve().parents[2]
REPOMIX = ROOT / "sources" / "repomix-scheduler.xml"


def _source_files() -> dict[str, str]:
    raw = REPOMIX.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(r'<file path="([^"]+)">\n(.*?)</file>', raw, re.S)}


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def scheduler_method_bodies() -> dict[str, str]:
    """Top-level `Scheduler::Name(...) {...}` definitions in scheduler.cpp, comments removed."""
    src = _strip_comments(_source_files()["src/scheduler.cpp"])
    out: dict[str, str] = {}
    depth = 0
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 1 and src.startswith("Scheduler::", i):
            # only at namespace level (depth 1 inside `namespace volley {`)
            m = re.match(r"Scheduler::(\w+)\(", src[i:])
            if m:
                # find the opening brace of the body
                j = src.index("{", i)
                semi = src.find(";", i, j)
                if semi == -1:
                    k, d = j, 0
                    while True:
                        if src[k] == "{":
                            d += 1
                        elif src[k] == "}":
                            d -= 1
                            if d == 0:
                                break
                        k += 1
                    out[m.group(1)] = out.get(m.group(1), "") + src[j:k + 1]
                    i = k + 1
                    continue
        i += 1
    return out


# --------------------------------------------------------------------------------------
# 32 — from trajectories to ActionNode[]
# --------------------------------------------------------------------------------------

@figure("32_motions_to_actions", "From trajectories to ActionNode[]", DOC1)
def motions_to_actions():
    d = Doc("32_motions_to_actions", "From timed trajectories to the ActionNode schedule",
            "CHUGG returns per-entity trajectories; ResponseFromTrajectories turns every non-wait motion into an "
            "ActionNode, builds an action DAG, and serialises it with integer parent indices.")
    W = 1060
    lane_x = 120
    px_s = (W - lane_x - 10) / 72.0
    lanes = [("AGV A", AGV), ("Bay B21", BAYC)]
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
    d.text(0, sy, "2 · ResponseFromTrajectories(ctx, final_state)", size=12.5, weight=600, fill=T.fg)
    steps = [("CollectAndCollapse...", "sort motions; drop waits;\ncollapse VRC floor rides"),
             ("BuildActionDag...", "ToActionNode per motion;\nentity chain + occupancy"),
             ("TransferEventDag...", "end of event -> start of\neach dependent event"),
             ("InsertVrcActions...", "VRC approach / move\ncommands where needed"),
             ("BuildScheduled...", "topological order ->\nindices + parents")]
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
    d.text(0, sy + 112, "Reduce() runs between the steps to drop the \"overkill\" occupancy edges.", size=11,
           fill=T.muted)
    # table
    ty = sy + 146
    d.text(0, ty, "3 · PlanResponse.schedule.nodes  (ActionNode[] in topological order)", size=12.5, weight=600,
           fill=T.fg)
    cols = [("idx", 50), ("type", 170), ("entity", 70), ("command", 440), ("parents", 70), ("duration", 80)]
    rows = [("0", "TYPE_AGV_COMMAND", "agv 1", "src {node_id: 13, heading: 90} -> dst {node_id: 15, heading: 90}", "[]", "6.0 s"),
            ("1", "TYPE_AGV_COMMAND", "agv 1", "node_id 15 -> node_id 17 (heading 90, lift false)", "[0]", "6.0 s"),
            ("2", "TYPE_AGV_COMMAND", "agv 1", "lift: src.lift false -> dst.lift true", "[1]", "4.0 s"),
            ("3 .. 8", "TYPE_AGV_COMMAND", "agv 1", "node_id 17 -> 15 -> 13 -> 18 -> 22 -> 41 -> 21, lift true", "[n-1]",
             "..."),
            ("9", "TYPE_AGV_COMMAND", "agv 1", "lower: lift true -> false", "[8]", "4.0 s"),
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
          subtitle="Illustrative retrieve of the tray at P17 into B21 (times invented). The shape matches the "
                   "RetrieveJob test: every node is an AGV command except the last, which is PROCESS_RETRIEVE, with "
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
            "Bay transitions the scheduler commands, ClassifyBay() rules from utils.cpp, and a worked example of "
            "ComputeBayRebalancingActions().")
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
    connect(d, [(B["RTR"].cx + 40, B["RTR"].y1), (B["PR"].cx + 40, B["PR"].y0)], kind="flow", color=BAYC, size=8,
            sw=1.6, label="PROCESS_RETRIEVE", label_at=(B["PR"].cx + 40, (B["RTR"].y1 + B["PR"].y0) / 2))
    for k_, ln_ in enumerate([
            "VEHICLE_INSERTED and PROCESSING_* come from bay / customer activity (BayReport.msg states 5, 6, 9).",
            "In the scheduler's own replay (BayTransition::Apply), PROCESS_RETRIEVE goes straight from",
            "READY_TO_RETRIEVE to READY_TO_INSERT: the car leaves. Other bay states: BOOTING, DOOR_VALIDATION,",
            "TRANSITIONING_TO_INSERT / _RETRIEVE, ERROR. MOVE_LIFT_TO_FLOOR is sent by Dispatch for BLift bays."]):
        d.text(0, B["PI"].y1 + 24 + k_ * 16, ln_, size=11, fill=T.muted)
    # --- classification table
    tx = 610
    d.text(tx, 10, "ClassifyBay(state, tray_in_bay, payload_in_bay)", size=12.5, weight=600, fill=T.fg)
    rows = [("any", "no", "yes", "NOT_USABLE"), ("READY_TO_INSERT", "yes", "no", "INSERT_READY"),
            ("READY_TO_INSERT", "other", "", "INSERT_READY_BUT_INVALID"), ("READY_TO_RETRIEVE", "no", "no", "RETRIEVE_READY"),
            ("READY_TO_RETRIEVE", "other", "", "RETRIEVE_READY_BUT_INVALID"),
            ("PROCESSING_INSERT", "yes", "yes", "WILL_BE_RETRIEVE_READY_BUT_INVALID"),
            ("PROCESSING_RETRIEVE", "yes", "yes", "WILL_BE_INSERT_READY"), ("anything else / disabled", "", "", "NOT_USABLE")]
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
        d.text(tx + 282, yy + 8, cl.replace("_BUT_INVALID", "_BUT_INV."), size=10.5, family="mono", fill=col)
    # --- rebalancing example
    ey = 500
    d.text(0, ey, "ComputeBayRebalancingActions(): worked example", size=12.5, weight=600, fill=T.fg)
    d.text(0, ey + 22, "bay_prioritization = [1, 2, 3, 4]  (front = preferred for insert, back = preferred for retrieve)   "
                      "ratio = 0.75   empty trays = 3", size=11.5, family="mono", fill=T.muted)
    d.text(0, ey + 42, "eligible bays = 4  ->  insert-ready wanted = min(ceil(0.75 x 4), 3) = 3,  retrieve-ready wanted = 1",
           size=11.5, family="mono", fill=T.fg2)
    bays = [("bay 1", "RETRIEVE_READY", "step 4: -> READY_FOR_INSERT job", T.amber),
            ("bay 2", "INSERT_READY", "step 2: keep (insert 1/3)", T.green),
            ("bay 3", "INSERT_READY", "step 2: keep (insert 2/3)", T.green),
            ("bay 4", "RETRIEVE_READY", "step 3: keep (retrieve 1/1)", T.green)]
    bw = 245
    for i, (b, cl, act, col) in enumerate(bays):
        x = i * (bw + 16)
        bb = BBox(x, ey + 62, x + bw, ey + 142)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=10, fill=T.card, stroke=col, sw=1.4)
        d.text(x + 14, bb.y0 + 20, b, size=13, weight=600, fill=T.fg)
        d.text(x + 14, bb.y0 + 42, cl, size=11, family="mono", fill=T.teal)
        d.text(x + 14, bb.y0 + 64, act, size=11, fill=col)
    d.text(0, ey + 166, "Steps 2 and 3 keep bays that are already right before step 4 / 5 change anything, so the "
                       "result needs as few bay transitions as possible.", size=11.5, fill=T.muted)
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

TRAY_ROWS = ["DoTrayAssignments", "ApplyTransitionToFreeingMoves", "AssignTrayIdForEmptyMove",
             "AssignDestForUntargetedMove", "ResolveBlockingTrays", "FindOpenSpaceForRootTray",
             "TryFindBlockingTrayResolution", "UsePreferredHeading", "UseEvChargeHeading", "UseRetrievalHeading"]
AGV_ROWS = ["DoAgvAssignments", "GetAgvToTrayAssignmentCost", "GetAgvCurrentPoseToTrayMoveCost", "GetJustMovingCost",
            "GetAgvOccupiedDuration", "GetEventDag", "AgvMatchingEventDeps", "MoveAgvToTrayPose", "AddNodeArrivalDeps",
            "AppendAgvLiftEvent", "PropagateEventCostToChildren", "EnsureAgvMovePathsClear", "RunAgvPathRepairPass",
            "TryClearBlockedAgvMove", "FindAgvDepartureFromNode", "AddDepsAfterAmiga"]
COLS = [("layout_", "layout_", "member"), ("gg_", "gg_", "member"), ("table_", "table_", "member"),
        ("cost_", "cost_model_", "member"), ("log", "logger_", "member"),
        ("events", "ctx->events", "ctx"), ("init", "ctx->initial_state", "ctx"),
        ("first", "ctx->first_tray_event", "ctx"), ("filt", "disabledness_filters", "ctx"),
        ("SSS", "SingleSourceSearch", "ext"), ("Static", "GetStaticFilter", "ext"), ("Path", "GetPosePath", "ext"),
        ("BA", "BottleneckAssignment", "ext")]


@figure("34_coupling_matrix", "What the two algorithms touch", DOC2)
def coupling_matrix():
    d = Doc("34_coupling_matrix", "What DoTrayAssignments and DoAgvAssignments touch",
            "Matrix of Scheduler members, ScheduleContext fields and external functions used by each method in the "
            "tray and AGV call trees, plus callers outside those trees. Computed from scheduler.cpp.")
    bodies = scheduler_method_bodies()
    tree = set(TRAY_ROWS) | set(AGV_ROWS)
    names = list(bodies)

    def uses(name, token):
        b = bodies.get(name, "")
        return token in b

    def outside_callers(name):
        out = []
        for other in names:
            if other in tree or other == name:
                continue
            if re.search(r"\b" + name + r"\(", bodies[other]):
                out.append(other)
        return out

    name_w = 290
    cw = 50
    TW = 1220
    callers_w = TW - name_w - cw * len(COLS)
    rh = 26
    # header
    groups = [("Scheduler members", "member", T.sky), ("ScheduleContext", "ctx", T.green), ("other packages", "ext", T.violet)]
    x = name_w
    for gname, gkey, gcol in groups:
        n = sum(1 for c in COLS if c[2] == gkey)
        d.rect(x + 2, 0, n * cw - 4, 22, rx=6, fill=T.tint(gcol, 0.16, T.bg), stroke=T.tint(gcol, 0.6, T.bg), sw=1)
        d.text(x + n * cw / 2, 11, gname, size=11, weight=600, fill=gcol, anchor="middle")
        x += n * cw
    d.text(x + 10, 11, "also called from outside these trees", size=11, weight=600, fill=T.amber)
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
            indent = 0 if name in ("DoTrayAssignments", "DoAgvAssignments") else 14
            d.text(indent, y + 10, name + "()", size=11.5, family="mono",
                   weight=700 if indent == 0 else 400, fill=T.fg if indent == 0 else T.fg2)
            for i, (short, tok, kind) in enumerate(COLS):
                cx = name_w + i * cw + cw / 2
                gcol = {"member": T.sky, "ctx": T.green, "ext": T.violet}[kind]
                if uses(name, tok):
                    d.circle(cx, y + 10, 6.5, fill=gcol)
                else:
                    d.circle(cx, y + 10, 2, fill=T.border_soft)
            oc = outside_callers(name)
            if oc:
                txt = ", ".join(oc)
                lines = wrap(txt, callers_w - 16, 11, "mono")
                d.text(name_w + len(COLS) * cw + 10, y + 10, lines[0] + (" ..." if len(lines) > 1 else ""), size=11,
                       family="mono", fill=T.amber)
            y += rh
        y += 14

    section("tray assignment tree", TRAY_ROWS, TRAY)
    section("AGV assignment tree", AGV_ROWS, AGV)
    d.text(0, y + 4, "Column key: cost_ = cost_model_, log = logger_, init = ctx->initial_state, first = "
                     "ctx->first_tray_event, filt = ctx->disabledness_filters,", size=11, fill=T.muted)
    d.text(0, y + 20, "SSS = SingleSourceSearch (motion_planner), Static = GetStaticFilter, Path = GetPosePath, "
                      "BA = task_planner::BottleneckAssignment.", size=11, fill=T.muted)
    frame(d, title="What DoTrayAssignments and DoAgvAssignments touch",
          subtitle="Each row is a Scheduler method in one of the two call trees. Filled dots mark what its body uses. "
                   "The right column lists callers outside the trees: helpers that cannot simply move into a solver.",
          badge_key="as-built",
          legend=[("dot", T.sky, "Scheduler member"), ("dot", T.green, "ScheduleContext field"),
                  ("dot", T.violet, "function from another package")],
          footnote="Generated by scripts/diagrams/fig_code4.py from sources/repomix-scheduler.xml (comments stripped, "
                   "text match on the method body). Indirect use through a callee is not counted on the caller's row.")
    return d


# --------------------------------------------------------------------------------------
# 35 — where each test enters the pipeline (doc 03)
# --------------------------------------------------------------------------------------

ENTRY = [
    ("Plan()", ["Plan"], T.sky),
    ("tray assignment", ["DoTrayAssignments", "ResolveBlockingTrays"], TRAY),
    ("AGV assignment", ["DoAgvAssignments", "GetJustMovingCost", "GetAgvCurrentPoseToTrayMoveCost",
                        "GetAgvOccupiedDuration", "GetAgvToTrayAssignmentCost"], AGV),
    ("sanity / motion / response", ["SanityCheckEvents", "ResponseFromTrajectories", "PlanMotions"], T.violet),
    ("utils & context", ["ValidateBaseState", "ClassifyBay", "ClassifyBays", "ComputeBayRebalancingActions",
                         "CalculateDesiredBaySplit", "CountEmptyTrays", "SetBayReadinessRatioCallback",
                         "UpdateLastEntityEvent"], T.teal),
]
FILE_COL = {"scheduler_tests": T.fg, "scheduler_jobs_tests": T.sky, "scheduler_insert_orientation_tests": T.pink,
            "utils_tests": T.teal}


def _tests():
    files = _source_files()
    out = []
    for path, src in files.items():
        if not path.startswith("test/") or not path.endswith(".cpp"):
            continue
        src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        heads = [(m.start(), m.group(2)) for m in re.finditer(r"^TEST\((\w+),\s*(\w+)\)", src, re.M)]
        for i, (p, name) in enumerate(heads):
            body = src[p:heads[i + 1][0] if i + 1 < len(heads) else len(src)]
            calls = []
            for _, fns, _ in ENTRY:
                for fn in fns:
                    pat = r"[.>]Plan\(" if fn == "Plan" else r"\b" + fn + r"\("
                    if re.search(pat, body):
                        calls.append(fn)
            out.append((Path(path).stem, name, calls))
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
    d = Doc("35_test_entry_points", "Where the existing tests enter the scheduler",
            "Every TEST in the scheduler package placed under the earliest pipeline stage it calls directly, coloured "
            "by test file. Computed from the test sources.")
    tests = _tests()
    W = 1080
    ncol = len(ENTRY)
    cw = (W - (ncol - 1) * 14) / ncol
    cols = {i: [] for i in range(ncol)}
    for f, name, calls in tests:
        for i, (_, fns, _) in enumerate(ENTRY):
            if any(c in fns for c in calls):
                # deepest entry wins for tests that call several stages (e.g. tray + AGV + motions)
                pass
        idx = [i for i, (_, fns, _) in enumerate(ENTRY) if any(c in fns for c in calls)]
        cols[min(idx) if idx else 0].append((f, name, calls))
    top = 0
    for i, (title, fns, col) in enumerate(ENTRY):
        x = i * (cw + 14)
        d.rect(x, top, cw, 44, rx=8, fill=T.tint(col, 0.15, T.bg), stroke=col, sw=1.3)
        d.text(x + 12, top + 17, title, size=12.5, weight=600, fill=col)
        d.text(x + 12, top + 34, f"{len(cols[i])} tests", size=11, fill=T.muted)
        if i < ncol - 1 and i < 3:
            connect(d, [(x + cw, top + 22), (x + cw + 14, top + 22)], kind="flow", color=T.faint, size=6)
        y = top + 58
        for f, name, calls in sorted(cols[i], key=lambda t: (t[0], t[1])):
            lines = _camel_wrap(name, cw - 26, 11)
            h = 8 + 15 * len(lines)
            fcol = FILE_COL.get(f, T.fg2)
            d.rect(x, y, cw, h, rx=6, fill=T.card, stroke=T.border_soft, sw=1)
            d.rect(x + 1, y + 1, 4, h - 2, rx=2, fill=fcol)
            for j, ln in enumerate(lines):
                d.text(x + 12, y + 11 + j * 15, ln, size=11, family="mono", fill=T.fg2)
            extra = [c for c in calls if c not in fns]
            if extra:
                d.text(x + cw - 6, y + 11, "+" + str(len(extra)), size=10, family="mono", fill=T.muted, anchor="end")
            y += h + 5
    ymax = max(top + 58 + sum(8 + 15 * len(_camel_wrap(n, cw - 26, 11)) + 5 for _, n, _ in cols[i])
               for i in range(ncol))
    nx = 3 * (cw + 14)
    col3_bottom = top + 58 + sum(8 + 15 * len(_camel_wrap(n, cw - 26, 11)) + 5 for _, n, _ in cols[3])
    note(d, nx, col3_bottom + 16, cw,
         "No test calls EnsureAgvMovePathsClear, AddDepsAfterAmiga or InsertVrcActionsIntoDag directly; they run only "
         "inside larger tests. DoubleRetrieveDodgeAgv is commented out.", title="Gaps worth knowing", accent=T.amber)
    frame(d, title="Where the existing tests enter the scheduler",
          subtitle="Each card is one TEST, placed under the earliest stage it calls. \"+n\" means it also calls n "
                   "later stages. Most job-level behaviour is only tested end to end through Plan().",
          badge_key="as-built",
          legend=[("fill", FILE_COL["scheduler_tests"], "scheduler_tests.cpp"),
                  ("fill", FILE_COL["scheduler_jobs_tests"], "scheduler_jobs_tests.cpp"),
                  ("fill", FILE_COL["scheduler_insert_orientation_tests"], "scheduler_insert_orientation_tests.cpp"),
                  ("fill", FILE_COL["utils_tests"], "utils_tests.cpp")],
          footnote="Generated from sources/repomix-scheduler.xml by scripts/diagrams/fig_code4.py.")
    return d
