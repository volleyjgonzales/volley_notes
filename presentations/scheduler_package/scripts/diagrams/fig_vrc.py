"""VRC and deployment figures.

112 VRC support status across the pipeline (static matrix, doc 02-layout-file).
113 How the motion planner is packaged and called (static, doc 04-motion-planning).
114 What happens today when an AGV changes floors (animated, illustrative two-floor layout,
    doc 02-layout-file).

Facts checked against sources/*.xml:
  common_ros  layout.cpp (floors, floor, Lift/BLift, vrcs + add_edge between adjacent floors),
              pose_graph.cpp (VRC_UP/VRC_DOWN by floor, DEO skipped, same heading),
              garage_graph.cpp (AddEdge: VRC_TRANSITION, length |dz|, throws without z),
              collision_geometry.cpp (different floors collide only if both nodes are VRC nodes),
              garage_safety_checker.cpp (BLift idle gate on TYPE_VRC_COMMAND).
  motion_planner  chugg_sequential.cpp (PlanNodeSequential: AgvMove/TrayMove/Bay/Vecs branches only;
              PlanEventSequential(VrcTransition) door close + transit + door open), continuous_state.cpp
              (stationary VRC motion, TRAY_LEGS placeholder), CMakeLists (SHARED DIRECTORY src).
  cost_functions  vrc_transit {0.254 m/s, 0.2 m/s^2}, vrc_door_open/close 3 s defaults, Trapezoid.
  scheduler   scheduler.cpp (CollectAndCollapseTrajectoryMotions, PlanMotions, ResponseFromTrajectories),
              utils.cpp (InsertVrcActionsIntoDag at file line 366, VrcFloorTransitDuration),
              scheduler_component.cpp / scheduler_ros.cpp / CMakeLists / package.xml.
"""
from __future__ import annotations

import math

from components import chip, code_panel, connect, frame, label_pill, note, num_badge
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC_LAYOUT = "02-layout-file.html"
DOC_MP = "04-motion-planning.html"

VRC = T.teal          # VRC / carriage (as in 80_asset_types)
AGV = T.green
TRAY = T.amber
STATUS = {"yes": ("YES", T.green), "partial": ("PARTIAL", T.amber), "no": ("NO", T.red),
          "na": ("N/A", T.faint)}

# illustrative ride numbers (cost_functions defaults; production reads them from ROS params)
DZ = 3.2
V_VRC, A_VRC = 0.254, 0.2
DOOR = 3.0


def _trap(d, v, a):
    if d < v * v / a:
        return 2 * math.sqrt(d / a)
    return d / v + v / a


RIDE = _trap(DZ, V_VRC, A_VRC)             # 13.87 s
CMD = DOOR + RIDE + DOOR                   # 19.87 s


def _status_pill(d: Doc, cx, cy, key, *, sub=None):
    label, col = STATUS[key]
    w = text_width(label, 11, "mono", 700) + 0.8 * (len(label) - 1) + 26
    d.rect(cx - w / 2, cy - 12, w, 24, rx=12, fill=T.tint(col, 0.18, T.bg), stroke=col, sw=1.3)
    d.circle(cx - w / 2 + 11, cy, 3.5, fill=col)
    d.text(cx + 5, cy, label, size=11, family="mono", weight=700, fill=col, anchor="middle", letter_spacing=0.8)
    if sub:
        for i, ln in enumerate(wrap(sub, 120, 10.5)):
            d.text(cx, cy + 26 + i * 14, ln, size=10.5, fill=T.muted, anchor="middle")


def _bullets(d: Doc, x, y, w, items, *, size=11.5, color=T.fg2, lh=1.42, gap=5, mark="•", mark_col=None):
    """Bulleted, wrapped text block; returns bottom y."""
    yy = y
    for it in items:
        lines = wrap(it, w - 14, size)
        d.text(x, yy, mark, size=size, fill=mark_col or T.faint, baseline="top")
        for i, ln in enumerate(lines):
            d.text(x + 13, yy + i * size * lh, ln, size=size, fill=color, baseline="top")
        yy += len(lines) * size * lh + gap
    return yy


def _bullets_h(items, w, *, size=11.5, lh=1.42, gap=5):
    return sum(len(wrap(it, w - 14, size)) * size * lh + gap for it in items)


# ======================================================================================
# 112 — VRC support status matrix
# ======================================================================================
@figure("112_vrc_support_status", "VRC support across the pipeline: what exists, what runs, what is missing",
        DOC_LAYOUT)
def vrc_support_status():
    d = Doc("112_vrc_support_status", "VRC support across the pipeline",
            "Matrix: for each layer (layout and graphs, task planning, motion planning, action graph, dispatch "
            "and safety) what VRC code exists, what of it runs on a normal plan call, what is missing or risky, "
            "and a yes / partial / no status. Pecos has no VRC.")
    rows = [
        dict(name="Layout and graphs", pkg="common_ros · interfaces", status="partial",
             sub="parsed and wired into every graph",
             exists=["Layout parses floors {id, z}, a floor per node, Lift (TYPE_LIFT = 3), BLift (TYPE_BLIFT = 7, "
                     "a bay that is also a VRC terminal) and vrcs {id, root_node, nodes}; it sorts the VRC nodes by "
                     "floor and adds a layout edge between adjacent floors.",
                     "PoseGraph puts a VRC pair in the VRC_UP / VRC_DOWN slots by floor, not by bearing; same "
                     "heading on both ends, disallowed-orientation check skipped.",
                     "GarageGraph::AddEdge: TransitionType VRC_TRANSITION, length = |dz| between the floors "
                     "(throws if a z is missing), then a re-tag and audit pass.",
                     "CollisionTable: nodes on different floors never collide unless both are VRC nodes (the "
                     "shaft rule)."],
             runs=["All of it: Layout, PoseGraph, GarageGraph and CollisionTable are built once in the Scheduler "
                   "constructor and used by every search of every plan call."],
             missing=["VRC nodes are not checked to be Lift or BLift; an empty nodes list underflows "
                      "(nodes.size() - 1).",
                      "GetFloorZForFloorId returns 0.0 for an unknown floor, so a missing floor silently gives a "
                      "wrong ride time.",
                      "BLift gets no BAY_ODP collision entries (built for TYPE_BAY only).",
                      "No VRC tests in common_ros."]),
        dict(name="Task planning", pkg="scheduler stages 1-3 · planner_core", status="no",
             sub="floors handled only implicitly",
             exists=["planner_core VrcTransition (ScheduleEventType VRC_TRANSITION = 5): Apply runs "
                     "IDLE -> MOVING -> IDLE and teleports the AGV (and its trays) to the other VRC node.",
                     "ApplyCommand(TYPE_VRC_COMMAND) is a no-op (\"handled via VrcTransition events\")."],
             runs=["No VrcTransition is ever created: job expansion, tray and AGV assignment and SanityCheckEvents "
                   "contain no VRC code.",
                   "A tray or AGV on another floor is reachable and costed like any move, because the searches run "
                   "on gg_, which contains the VRC edges.",
                   "The only floor rule: bay retrieve takes system_floors[0] (\"Pick the first floor for now\")."],
             missing=["Tray, parking and AGV choice ignore floors and the carriage.",
                      "No job type targets a floor; insert_floor is never read.",
                      "The Charge job's trapped-in-bay check tests TYPE_BAY only, so a BLift is missed."]),
        dict(name="Motion planning", pkg="motion_planner · cost_functions", status="partial",
             sub="the AGV rides; the carriage is not planned",
             exists=["Chugg::PlanEventSequential(VrcTransition): wait for dependencies, then one VRC motion of "
                     "door close + transit + door open.",
                     "ContinuousState gives every VRC a stationary motion (TRAY_LEGS as a placeholder footprint)."],
             runs=["SIPP plans the AGV over VRC_TRANSITION edges like any edge: cost TrapezoidDuration(|dz|, "
                   "vrc_transit), no wheel-turn penalty; same-VRC, same-direction rides coalesce into one run.",
                   "The shaft rule keeps a second AGV off the VRC nodes of other floors.",
                   "PlanNodeSequential branches on AgvMove, TrayMove, BayTransition and VecsTransition only: the "
                   "VRC overload is never called."],
             missing=["Ride time leaves out the doors (3 s + 3 s by default) and the empty carriage's trip to the "
                      "AGV's floor: planned times are optimistic.",
                      "The carriage is not an agent and is never reserved.",
                      "A VrcTransition, if one appeared, would still be Applied: a teleport with no motion."]),
        dict(name="Action graph", pkg="scheduler.cpp · utils.cpp", status="partial",
             sub="where VRC commands are made",
             exists=["CollectAndCollapseTrajectoryMotions (scheduler.cpp) and InsertVrcActionsIntoDag "
                     "(utils.cpp:366), called from ResponseFromTrajectories."],
             runs=["Each run of floor-traversal motions becomes one motion (first source pose to the next motion's "
                   "source pose).",
                   "After the second Reduce, AGV actions are walked in topological order with a simulated floor per "
                   "VRC: an approach TYPE_VRC_COMMAND is added if the carriage is on the wrong floor, and each "
                   "cross-floor AGV action is Replaced by a VRC move command (door close + transit + door open), "
                   "chained per VRC."],
             missing=["A ride at the end of a trajectory is dropped (no flush after the loop).",
                      "The collapsed motion borrows the next motion's action id.",
                      "Chain edges that would close a cycle are skipped; VRC commands in base_schedule are ignored "
                      "when seeding the floor.",
                      "No direct tests."]),
        dict(name="Dispatch and safety", pkg="garage_safety_checker · interfaces · Dispatch",
             status="partial", sub="Dispatch is not in the snapshots",
             exists=["GarageSafetyChecker::IsSafe blocks a VRC command while any BLift bay on that VRC is not "
                     "READY_TO_RETRIEVE or VEHICLE_INSERTED.",
                     "BayCommand COMMAND_TYPE_MOVE_LIFT_TO_FLOOR = 4, \"used by the dispatcher in place of "
                     "TYPE_VRC_COMMAND when a VRC is owned by a BLift bay\"; VrcCommand, VrcStateChanged, "
                     "vrc_interfaces/VrcMove.action."],
             runs=["Nothing during a plan call: the scheduler never uses the safety checker and never sends "
                   "MOVE_LIFT_TO_FLOOR. Executing (and converting) VRC commands is Dispatch's job, outside the "
                   "snapshots."],
             missing=["The BLift conversion and the idle-bay gate cannot be checked here.",
                      "Nothing in the plan orders a VRC command after the bay state the checker requires "
                      "(inference).",
                      "The checker gives VRC commands no location, so VRC occupancy is not checked."]),
    ]
    cols = [("Layer", 200), ("What exists", 330), ("What runs on a normal plan call", 330),
            ("Missing or risky", 330), ("Status", 140)]
    xs = [0]
    for _, w in cols:
        xs.append(xs[-1] + w)
    W = xs[-1]
    pad = 14
    head_h = 34
    d.rect(0, 0, W, head_h, rx=8, fill=T.card_hi)
    for i, (label, w) in enumerate(cols):
        mid = label == "Status"
        d.text(xs[i] + (w / 2 if mid else pad), head_h / 2, label.upper(), size=10.5, family="mono", weight=600,
               fill=T.muted, letter_spacing=0.8, anchor="middle" if mid else "start")
    y = head_h + 8
    col_keys = ["exists", "runs", "missing"]
    col_colors = [T.fg2, T.fg2, T.fg2]
    marks = [(T.sky, "•"), (T.green, "•"), (T.red, "•")]
    for r_i, r in enumerate(rows):
        hs = [_bullets_h(r[k], cols[i + 1][1] - 2 * pad) for i, k in enumerate(col_keys)]
        h = max(max(hs) + 2 * pad - 5, 110)
        d.rect(0, y, W, h, rx=8, fill=T.card if r_i % 2 == 0 else T.tint(T.card, 0.55, T.bg),
               stroke=T.border_soft, sw=1)
        for i in range(1, len(cols)):
            d.line(xs[i], y + 8, xs[i], y + h - 8, stroke=T.border_soft, sw=1, layer="under")
        d.text(pad, y + pad + 6, r["name"], size=14, weight=600, fill=T.fg)
        for i, ln in enumerate(wrap(r["pkg"], cols[0][1] - 2 * pad, 10.5, "mono")):
            d.text(pad, y + pad + 28 + i * 15, ln, size=10.5, family="mono", fill=T.muted)
        for i, k in enumerate(col_keys):
            mc, mk = marks[i]
            _bullets(d, xs[i + 1] + pad, y + pad, cols[i + 1][1] - 2 * pad, r[k], color=col_colors[i],
                     mark_col=mc, mark=mk)
        _status_pill(d, xs[4] + cols[4][1] / 2, y + 30, r["status"], sub=r["sub"])
        y += h + 8
    # Pecos strip
    d.rect(0, y + 4, W, 40, rx=8, fill=T.tint(T.violet, 0.08, T.bg), stroke=T.tint(T.violet, 0.5, T.bg), sw=1)
    d.rich(pad, y + 24, [("Pecos: ", "sans", 600, T.violet),
                         ("5675_pecos_combined.yaml has no floors, vrcs, floor, Lift or BLift (13 Waypoint, 10 "
                          "Parking, 3 AgvCharge, 2 Bay), so none of the VRC code above runs for that site.",
                          "sans", 400, T.fg2)], size=12)
    _status_pill(d, xs[4] + cols[4][1] / 2, y + 24, "na")
    frame(d, title="VRC support across the pipeline",
          subtitle="The graph layer and motion planning treat a VRC ride as one more edge the AGV drives; the VRC "
                   "commands appear only when the action graph is built. Task planning has no VRC logic and the "
                   "carriage is never planned as an agent. Nothing in the snapshots tests the path end to end.",
          badge_key="as-built",
          legend=[("dot", T.sky, "code that exists"), ("dot", T.green, "runs on every plan call"),
                  ("dot", T.red, "gap or risk"), ("fill", T.green, "yes"), ("fill", T.amber, "partial"),
                  ("fill", T.red, "no")],
          footnote="From layout.cpp, pose_graph.cpp, garage_graph.cpp, collision_geometry.cpp and "
                   "garage_safety_checker.cpp (common_ros); schedule_events.cpp (planner_core); chugg_sequential.cpp "
                   "and continuous_state.cpp (motion_planner); motion_cost_model.hpp defaults (cost_functions); "
                   "scheduler.cpp and utils.cpp (scheduler); BayCommand.msg (interfaces). Dispatch is not in the "
                   "snapshots: its row lists only what the messages and the safety checker say.")
    return d


# ======================================================================================
# 114 — what happens today when an AGV changes floors (animated, illustrative)
# ======================================================================================
_F1, _F0 = 0, 300            # panel tops: floor 1 above, floor 0 below
_PW, _PH = 540, 210
_XP, _XW, _XL = 70, 250, 430
_CY, _SY = 95, 170           # corridor and spur y inside a panel


def _n(floor, kind):
    top = _F1 if floor == 1 else _F0
    return {"P": (_XP, top + _CY), "W": (_XW, top + _CY), "L": (_XL, top + _CY), "S": (_XW, top + _SY)}[kind]


def _agv_glyph(d: Doc, x, y, col, *, tray=False):
    if tray:
        d.rect(x - 31, y - 20, 62, 40, rx=3, fill=T.tint(TRAY, 0.16, T.bg_deep), stroke=TRAY, sw=1.6, layer="top")
        for dx in (-31, 27):
            for dy in (-20, 16):
                d.rect(x + dx, y + dy, 4, 4, fill=TRAY, layer="top")
    for dx in (-17, 7):
        d.rect(x + dx, y - 16, 10, 4, rx=1.5, fill=T.fg2, layer="top")
        d.rect(x + dx, y + 12, 10, 4, rx=1.5, fill=T.fg2, layer="top")
    d.rect(x - 24, y - 13, 48, 26, rx=7, fill=T.tint(col, 0.30, T.bg_deep), stroke=col, sw=2, layer="top")
    # heading 90 = facing -x: chevron on the left end
    d.path(f"M{x - 10} {y - 7} L{x - 18} {y} L{x - 10} {y + 7}", stroke=col, sw=2.4, layer="top")


def _mbox(d: Doc, x, y, w, kind, text, col, *, sub=None, style="solid", h=None):
    h = h or (60 if sub else 46)
    faded = style == "faded"
    d.rect(x, y, w, h, rx=7, fill=T.bg if faded else T.card, stroke=T.tint(col, 0.45, T.bg) if faded else col,
           sw=1.3, dash="5 4" if style == "dashed" else None)
    d.text(x + 9, y + 13, kind, size=10, family="mono", weight=600, fill=T.faint if faded else col)
    d.text(x + 9, y + 31, text, size=11, family="mono", fill=T.muted if faded else T.fg)
    if sub:
        d.text(x + 9, y + 48, sub, size=10, fill=T.muted)
    return BBox(x, y, x + w, y + h)


def _panel_head(d: Doc, x, y, n, title, col=T.sky):
    num_badge(d, x + 11, y + 11, n, col)
    d.text(x + 30, y + 11, title, size=15, weight=600, fill=T.fg)


@figure("114_vrc_ride", "What happens today when an AGV changes floors (animated)", DOC_LAYOUT)
def vrc_ride():
    d = Doc("114_vrc_ride", "An AGV changes floors: what the pipeline does today",
            "Animated, illustrative two-floor layout with one VRC. Step 0 shows the layout entries and the graph "
            "edges they create; step 1 the task planning (a plain TrayMove); step 2 SIPP driving AGV-1 across the "
            "VRC edge; steps 3 and 4 how the action graph collapses the ride and replaces it with VRC commands; "
            "step 5 the gaps.")
    d.uses_map = False
    caps = [
        "Layout. floors gives each floor a z; the two Lift nodes L3 (floor 0) and L13 (floor 1) share x and y; vrcs "
        "{id 1, root_node 3, nodes [3, 13]} makes them one VRC. Layout adds the 3-13 edge, PoseGraph files it under "
        "VRC_UP / VRC_DOWN by floor, and GarageGraph types it VRC_TRANSITION with length |3.2 - 0.0| = 3.2 m. The "
        "base state has the carriage at floor 1.",
        "Task planning. Moving T7 from P1 (floor 0) to P11 (floor 1) is an ordinary TrayMove carried by AGV-1, with "
        "its lift events. Stages 1-3 never look at floors or the carriage, and no VrcTransition event is created.",
        "Motion planning. SIPP drives AGV-1 P1 -> W2 -> L3 -> L13 -> W12 -> P11 and takes the VRC edge like any "
        "edge: 13.87 s of trapezoid travel over 3.2 m, no door time, no carriage. The plan does not know the "
        "carriage is on floor 1. The shaft rule keeps AGV-2 off L13 during the ride.",
        "Action graph, part 1. CollectAndCollapseTrajectoryMotions merges each run of floor-traversal motions into "
        "one motion (here a run of one): from the first source pose L3@90 to the next motion's source pose L13@90, "
        "with that next motion's action id. Each motion then becomes an AGV command.",
        "Action graph, part 2. InsertVrcActionsIntoDag simulates the carriage floor: it adds an approach VRC "
        "command to floor 0 before W2 -> L3, replaces the ride L3 -> L13 with a VRC move command to floor 1 "
        "(3 + 13.87 + 3 = 19.87 s each) and chains the VRC's users: approach, W2 -> L3, move, L13 -> W12.",
        "The gaps: the written VrcTransition planner is never called, SIPP's ride time is optimistic, the carriage "
        "is not an agent, a ride at the end of a trajectory is dropped, and task planning is not floor-aware.",
    ]
    for c in caps:
        d.step(c)
    N = len(caps)

    # ---------------- map: two floor plans stacked, VRC shaft between ----------------
    for floor, top, z in ((1, _F1, "3.2"), (0, _F0, "0.0")):
        d.rect(0, top, _PW, _PH, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1.2, layer="bg")
        d.text(14, top + 20, f"floor {floor}", size=13.5, weight=600, fill=T.fg)
        d.text(14 + text_width(f"floor {floor}", 13.5, "sans", 600) + 10, top + 20, f"id: {floor}   z: {z} m",
               size=11, family="mono", fill=T.muted)
    # shaft
    sx0, sx1 = _XL - 31, _XL + 31
    sy0, sy1 = _F1 + _CY - 30, _F0 + _CY + 30
    d.rect(sx0, sy0, sx1 - sx0, sy1 - sy0, rx=8, fill=T.tint(VRC, 0.07, T.bg), stroke=T.tint(VRC, 0.6, T.bg), sw=1.3,
           dash="6 4", layer="under")
    d.text(_XL, sy1 + 16, "VRC r1 shaft", size=10.5, family="mono", fill=VRC, anchor="middle")
    # edges
    ecol = "#55657F"
    for f in (0, 1):
        for a, b in (("P", "W"), ("W", "L"), ("W", "S")):
            (x1, y1), (x2, y2) = _n(f, a), _n(f, b)
            d.line(x1, y1, x2, y2, stroke=ecol, sw=2, layer="edges")
    (lx, ly1), (_, ly0) = _n(1, "L"), _n(0, "L")
    d.line(lx, ly1, lx, ly0, stroke=VRC, sw=2.4, layer="edges")
    # gap labels (left of the shaft)
    gx = sx0 - 12
    d.text(gx, 232, "GarageGraph edge: VRC_TRANSITION, length |3.2 - 0.0| = 3.2 m", size=10.5, family="mono",
           fill=VRC, anchor="end")
    d.text(gx, 252, "PoseGraph: L3@90 -VRC_UP-> L13@90,  L13@90 -VRC_DOWN-> L3@90", size=10.5, family="mono",
           fill=T.fg2, anchor="end")
    d.text(gx, 272, "(same for heading -90; slot chosen by floor, not bearing)", size=10.5, fill=T.muted,
           anchor="end")
    # nodes
    names = {(0, "P"): "P1", (0, "W"): "W2", (0, "L"): "L3", (0, "S"): "P4",
             (1, "P"): "P11", (1, "W"): "W12", (1, "L"): "L13", (1, "S"): "P14"}
    for (f, k), nm in names.items():
        x, y = _n(f, k)
        if k in ("P", "S"):
            d.rect(x - 9, y - 9, 18, 18, rx=3, fill=T.bg_deep, stroke=T.fg2, sw=1.6)
        elif k == "W":
            d.circle(x, y, 6.5, fill=T.sky)
        else:
            d.rect(x - 8, y - 8, 16, 16, rx=2, fill=VRC)
        if k == "L":
            d.text(sx1 + 10, y - 8, nm, size=12, family="mono", weight=700, fill=VRC)
            d.text(sx1 + 10, y + 9, "type: Lift", size=10, family="mono", fill=T.muted)
        elif k == "S":
            d.text(x - 32, y + 1, nm, size=11.5, family="mono", weight=600, fill=T.fg2, anchor="end")
        else:
            d.text(x, y + 26, nm, size=11.5, family="mono", weight=600, fill=T.fg2, anchor="middle")

    # route trail (from step 2)
    route = [_n(0, "P"), _n(0, "W"), _n(0, "L"), _n(1, "L"), _n(1, "W"), _n(1, "P")]
    with d.at(2):
        d.polyline([(x, y - 0) for x, y in route], stroke=T.tint(AGV, 0.7, T.bg), sw=3, dash="7 5", radius=8,
                   layer="edges")
    # carriage (mover): rests at floor 1, moves in step 4 (approach to floor 0, ride back to floor 1)
    cx, cy = _n(1, "L")
    dz = _n(0, "L")[1] - cy

    def carriage(sub):
        sub.rect(cx - 27, cy - 23, 54, 46, rx=6, fill=T.tint(VRC, 0.16, T.bg_deep), stroke=VRC, sw=2)
        sub.text(cx, cy + 15, "carriage", size=8.5, family="mono", fill=VRC, anchor="middle")
    frames = [[(0, 0)] for _ in range(N)]
    frames[4] = [(0, 0), (0, dz), (0, 0)]
    d.mover(frames, carriage, layer="over")
    # AGV-1 carrying T7 (mover)
    ax, ay = _n(0, "P")
    path = [(x - ax, y - ay) for x, y in route]

    def agv1(sub):
        _agv_glyph(sub, ax, ay, AGV, tray=True)
        chip(sub, ax, ay - 36, "AGV-1 + T7", AGV, anchor="middle", size=10.5, fill=T.tint(AGV, 0.25, T.bg_deep),
             layer="top")
    fr = [[(0, 0)], [(0, 0)], path] + [[path[-1]] for _ in range(N - 3)]
    d.mover(fr, agv1, layer="top")
    # AGV-2 parked on P14
    bx, by = _n(1, "S")
    _agv_glyph(d, bx, by, T.sky)
    chip(d, bx + 34, by, "AGV-2", T.sky, size=10.5, fill=T.tint(T.sky, 0.25, T.bg_deep), layer="top")
    # step-2 warnings on the map
    with d.only(2):
        x, y = _n(0, "L")
        d.circle(x, y, 36, stroke=T.red, sw=1.6, dash="4 3", layer="over")
        label_pill(d, 395, _F0 + _SY + 8, "no carriage here; the plan does not check", color=T.red,
                   border=T.tint(T.red, 0.6, T.bg), size=10.5, family="sans", bg=T.bg_deep)
        label_pill(d, 140, _F1 + _SY + 20, "shaft rule: L13 blocked for AGV-2", color=T.red,
                   border=T.tint(T.red, 0.6, T.bg), size=10.5, family="sans", bg=T.bg_deep)

    # ---------------- right panel, one per step ----------------
    RX, RW = 590, 700
    # step 0: layout
    with d.only(0):
        _panel_head(d, RX, 0, 0, "Layout: three YAML sections make the VRC", VRC)
        code_panel(d, RX, 34, 300, [
            "floors:",
            "  - {id: 0, z: 0.0}",
            "  - {id: 1, z: 3.2}",
            "nodes:",
            "  - {id: 3, type: Lift,",
            "     floor: 0, x: 14.0, y: 4.0,",
            "     headings: [90], ...}",
            "  - {id: 13, type: Lift,",
            "     floor: 1, x: 14.0, y: 4.0,",
            "     headings: [90], ...}",
            "  # P1, W2, P4 floor 0;",
            "  # P11, W12, P14 floor 1",
            "edges:  # 3-13 comes from vrcs",
            "  - {src: 2, dst: 3}  # ...",
            "vrcs:",
            "  - id: 1",
            "    root_node: 3",
            "    nodes: [3, 13]",
        ], title="layout YAML (illustrative)", size=11)
        _bullets(d, RX + 320, 40, RW - 320, [
            "Layout::Layout reads floors {id, z} and a floor per node (default 0). type: Lift becomes TYPE_LIFT (3); "
            "a BLift (TYPE_BLIFT, 7) is a bay that is also a VRC terminal.",
            "vrcs: nodes are sorted by floor and each adjacent pair gets a layout edge, so 3-13 is not listed under "
            "edges. root_node is read but has no consumer in the snapshots.",
            "PoseGraph: the two Lift nodes share x and y, so the neighbour slot is chosen by floor: VRC_UP (6) "
            "towards floor 1, VRC_DOWN (7) back. Both nodes need the heading; the disallowed-orientation check is "
            "skipped.",
            "GarageGraph::AddEdge: Transition {length: |dz| = 3.2 m, type: VRC_TRANSITION}; it throws if a floor "
            "has no z.",
            "CollisionTable: nodes on different floors never collide unless both are VRC nodes, so L3, L13 and the "
            "edge between them act as one shaft.",
            "The PlanRequest base state reports VRC r1 (DiscreteVrcState) at current_floor 1.",
        ], size=11.5)
    # step 1: task planning
    with d.only(1):
        _panel_head(d, RX, 0, 1, "Task planning: just a TrayMove", T.amber)
        y = 40
        _mbox(d, RX, y, 330, "AgvMove (stage 3)", "AGV-1 lift raise at P1", AGV)
        _mbox(d, RX, y + 58, 330, "TrayMove", "T7: P1 -> P11, carried by AGV-1", TRAY)
        _mbox(d, RX, y + 116, 330, "AgvMove (stage 3)", "AGV-1 lift lower at P11", AGV)
        for k in range(2):
            connect(d, [(RX + 165, y + 46 + k * 58), (RX + 165, y + 58 + k * 58)], kind="flow", color=T.faint,
                    size=7, sw=1.3)
        g = _mbox(d, RX, y + 196, 330, "VrcTransition (planner_core)", "r1: floor 0 -> floor 1", T.red,
                  sub="defined, never created by the scheduler", style="dashed")
        _bullets(d, RX + 350, 40, RW - 350, [
            "Stages 1-3 (job expansion, tray assignment, AGV assignment) see a tray on P1 and a destination P11. "
            "No code in them reads a floor, a VRC or the carriage.",
            "Costs come from single-agent searches on gg_, which contains the VRC edges: P11 is reachable and costed "
            "like any parking spot, with the ride counted as 13.87 s.",
            "planner_core's VrcTransition would run IDLE -> MOVING -> IDLE and teleport the AGV and its trays to the "
            "other VRC node, but nothing creates one.",
            "The carriage state in DiscreteGarageState is never advanced during planning.",
        ], size=11.5)
    # step 2: motion planning
    with d.only(2):
        _panel_head(d, RX, 0, 2, "Motion planning: SIPP takes the VRC edge", AGV)
        rows = [("P1@90 -> W2@90", "LOCOMOTE", "6.0 m", ""), ("W2@90 -> L3@90", "LOCOMOTE", "6.0 m", ""),
                ("L3@90 -> L13@90", "VRC_TRANSITION", "3.2 m", f"{RIDE:.2f} s"),
                ("L13@90 -> W12@90", "LOCOMOTE", "6.0 m", ""), ("W12@90 -> P11@90", "LOCOMOTE", "6.0 m", "")]
        y = 38
        d.rect(RX, y, RW, 24, rx=5, fill=T.card_hi)
        for x, lab in ((RX + 10, "EDGE OF AGV-1'S PATH"), (RX + 220, "TRANSITION TYPE"), (RX + 400, "LENGTH"),
                       (RX + 490, "SIPP EDGE COST")):
            d.text(x, y + 12, lab, size=10, family="mono", weight=600, fill=T.muted, letter_spacing=0.5)
        for i, (e, t, L, c) in enumerate(rows):
            yy = y + 24 + i * 24
            hl = t == "VRC_TRANSITION"
            d.rect(RX, yy, RW, 24, rx=4, fill=T.tint(VRC, 0.12, T.bg) if hl else (T.card if i % 2 else T.bg))
            d.text(RX + 10, yy + 12, e, size=11, family="mono", fill=T.fg)
            d.text(RX + 220, yy + 12, t, size=11, family="mono", fill=VRC if hl else T.fg2)
            d.text(RX + 400, yy + 12, L, size=11, family="mono", fill=T.fg2)
            d.text(RX + 490, yy + 12, c or "trapezoid (locomote)", size=11, family="mono",
                   fill=VRC if hl else T.faint)
        y += 24 + len(rows) * 24 + 14
        code_panel(d, RX, y, RW, [
            "TrapezoidDuration(|dz| = 3.2 m, vrc_transit.speed 0.254 m/s, accel 0.2 m/s²)",
            f"  = 3.2 / 0.254 + 0.254 / 0.2 = 12.60 + 1.27 = {RIDE:.2f} s   // d > v²/a = 0.32 m: trapezoid",
            "// no door close / open, no carriage approach, no wheel-turn penalty, no load slow-down",
        ], size=11)
        _bullets(d, RX, y + 98, RW, [
            "Doors (vrc_door_close 3 s, vrc_door_open 3 s by default) and the empty carriage's trip from floor 1 to "
            "floor 0 are not in the cost. Same-VRC, same-direction rides coalesce into one run.",
            "The carriage is not a SIPP agent and nothing reserves it; ContinuousState holds only a stationary VRC "
            "motion with a TRAY_LEGS placeholder footprint.",
            "The collision table's shaft rule (both nodes are VRC nodes) is what keeps AGV-2 off L13 while AGV-1 is "
            "on L3 or on the ride edge.",
            "Chugg::PlanEventSequential(VrcTransition), which would add door close + transit + door open, has no "
            "branch in PlanNodeSequential.",
        ], size=11.5)
    # step 3: collapse
    with d.only(3):
        _panel_head(d, RX, 0, 3, "Action graph: collapse the floor traversal", VRC)
        code_panel(d, RX, 34, RW, [
            "// CollectAndCollapseTrajectoryMotions (scheduler.cpp), per entity trajectory",
            "for motion in traj:",
            "  if IsFloorTraversalMotion(motion):        // AgvPoseChanged, node floors differ",
            "    first = first or motion;  continue",
            "  elif first:                               // the run ended at this motion",
            "    insert Motion(motion.entity, [first.begin, motion.begin),",
            "                  motion.collision_id, motion.action_id,",
            "                  {first.source_pose, motion.source_pose});  first = none",
            "  if waiting or idle: continue              // waits are dropped",
            "  insert motion",
            "// no flush after the loop: a trajectory that ends in a run loses its ride",
        ], size=11)
        _bullets(d, RX, 274, RW, [
            "Here the run is one motion, because the ride spans two floors; a ride over several floors arrives as "
            "several motions and leaves as one.",
            "The merged motion borrows the collision id and action id of the next motion (L13@90 -> W12@90), which "
            "may belong to a different event.",
            "BuildActionDagFromMotions then turns every motion into an AGV command; the DAG is reduced twice before "
            "VRC commands are added.",
        ], size=11.5)
    # step 4: InsertVrcActionsIntoDag
    with d.only(4):
        _panel_head(d, RX, 0, 4, "Action graph: InsertVrcActionsIntoDag (utils.cpp:366)", VRC)
        items = [
            "Walk the AGV commands in topological order. The simulated floor of r1 starts at the base state's "
            "current_floor (1), or at the required floor if the base state has no r1.",
            "W2@90 -> L3@90 ends on a VRC node and needs the carriage at floor 0, but it is at 1: add an approach "
            f"TYPE_VRC_COMMAND {{vrc_id 1, COMMAND_TYPE_MOVE, requested_floor 0}}, duration 3 + {RIDE:.2f} + 3 = "
            f"{CMD:.2f} s, as a parent of W2 -> L3.",
            "L3@90 -> L13@90 crosses floors (both ends must be on the same VRC, else the call fails): Replace it "
            f"with a VRC move command {{requested_floor 1}}, {CMD:.2f} s. AGV-1 gets no command for the ride; it "
            "rides as cargo.",
            "Serialise users of r1 through last_vrc_action: approach -> W2 -> L3 -> move -> L13 -> W12 (the exit "
            "command). An edge that would close a cycle is skipped.",
            "Dispatch runs the commands. For a VRC owned by a BLift it sends BayCommand MOVE_LIFT_TO_FLOOR "
            "instead, and GarageSafetyChecker blocks the command unless the BLift bay is idle (Dispatch is not in "
            "the snapshots).",
        ]
        y = 40
        for i, it in enumerate(items):
            num_badge(d, RX + 10, y + 8, i + 1, VRC, r=10)
            lines = wrap(it, RW - 34, 11.5)
            for j, ln in enumerate(lines):
                d.text(RX + 30, y + j * 16.5, ln, size=11.5, fill=T.fg2, baseline="top")
            y += len(lines) * 16.5 + 14
        note(d, RX, y + 4, RW,
             f"SIPP planned the ride as {RIDE:.2f} s. The move command Dispatch will run takes {CMD:.2f} s, and "
             f"the {CMD:.2f} s approach must finish before AGV-1 may enter L3 (it can overlap AGV-1's earlier "
             "commands). None of this is in the planned times.",
             title="Planned time vs commanded time", accent=T.amber)
    # step 5: gaps
    with d.at(5):
        _panel_head(d, RX, 0, 5, "What is missing", T.red)
        gaps = [
            ("Unused VRC planner.", "Chugg::PlanEventSequential(VrcTransition) is written (wait, door close, "
             "transit, door open) but PlanNodeSequential has no branch for it and the scheduler never creates the "
             "event."),
            ("Optimistic ride time.", f"SIPP charges {RIDE:.2f} s for the ride; the VRC move command is {CMD:.2f} s "
             f"and here a {CMD:.2f} s approach must finish before AGV-1 enters L3. Planned times and the makespan "
             "are too short."),
            ("The carriage is not an agent.", "No SIPP agent, no reservation; its floor enters only when the action "
             "graph is built. Two AGVs are kept apart only by the collision table's shaft rule."),
            ("Trailing ride dropped.", "If a trajectory ends with a floor traversal, CollectAndCollapse never "
             "flushes the run: no AGV command, so no VRC move command either."),
            ("Task planning is not floor-aware.", "Tray, parking and AGV choice ignore floors and where the "
             "carriage is; no VrcTransition is planned."),
        ]
        y = 40
        for i, (h, t) in enumerate(gaps):
            num_badge(d, RX + 10, y + 9, i + 1, T.red, r=10)
            d.text(RX + 30, y + 1, h, size=12.5, weight=600, fill=T.fg, baseline="top")
            lines = wrap(t, RW - 34, 11.5)
            for j, ln in enumerate(lines):
                d.text(RX + 30, y + 20 + j * 16, ln, size=11.5, fill=T.fg2, baseline="top")
            y += 20 + len(lines) * 16 + 14

    # ---------------- bottom strip: trajectory -> motions -> action DAG ----------------
    BY = 560
    LW = 210
    BW, BG = 138, 18
    bx0 = LW + 10

    def bxs(i):
        return bx0 + i * (BW + BG)
    labels_a = [("AgvLiftChanged", "lift ↑ at P1"), ("AgvPoseChanged", "P1@90 -> W2@90"),
                ("AgvPoseChanged", "W2@90 -> L3@90"), ("floor traversal", "L3@90 -> L13@90"),
                ("AgvPoseChanged", "L13@90 -> W12@90"), ("AgvPoseChanged", "W12@90 -> P11@90"),
                ("AgvLiftChanged", "lift ↓ at P11")]
    rows_y = [BY, BY + 86, BY + 172]
    row_titles = [("Trajectory of AGV-1", "Motions from SIPP (waits not shown)", 2),
                  ("all_motions", "after CollectAndCollapseTrajectoryMotions", 3),
                  ("Action DAG", "after InsertVrcActionsIntoDag", 4)]
    for (t, s, k), yy in zip(row_titles, rows_y):
        with d.at(k):
            d.text(0, yy + 14, t, size=13, weight=600, fill=T.fg)
            for j, ln in enumerate(wrap(s, LW - 10, 11)):
                d.text(0, yy + 33 + j * 15, ln, size=11, fill=T.muted)
    with d.at(2):
        for i, (k, t) in enumerate(labels_a):
            _mbox(d, bxs(i), rows_y[0], BW, k, t, VRC if i == 3 else AGV)
    with d.at(3):
        for i, (k, t) in enumerate(labels_a):
            if i == 3:
                b = _mbox(d, bxs(i), rows_y[1], BW, "collapsed motion", "L3@90 -> L13@90", VRC,
                          sub="action id of next")
            else:
                _mbox(d, bxs(i), rows_y[1], BW, k, t, AGV, style="faded")
        connect(d, [(bxs(3) + BW / 2, rows_y[0] + 46), (bxs(3) + BW / 2, rows_y[1])], kind="flow", color=VRC,
                size=7, sw=1.4)
    with d.at(4):
        cmd_y = rows_y[2]
        boxes = []
        for i, (k, t) in enumerate(labels_a):
            if i == 3:
                boxes.append(_mbox(d, bxs(i), cmd_y, BW, "VRC cmd r1: move", "requested_floor 1", VRC,
                                   sub=f"{CMD:.2f} s (replaced)", h=60))
            else:
                txt = t.replace("@90", "")
                boxes.append(_mbox(d, bxs(i), cmd_y, BW, "AGV command", txt, AGV, h=60))
        for i in range(len(boxes) - 1):
            a, b = boxes[i], boxes[i + 1]
            connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=T.faint, size=7, sw=1.3)
        ap = _mbox(d, bxs(1), cmd_y + 82, BW + 40, "VRC cmd r1: approach", "requested_floor 0", VRC,
                   sub=f"{CMD:.2f} s (inserted)")
        connect(d, [(ap.x1, ap.cy), (boxes[2].cx, ap.cy), (boxes[2].cx, boxes[2].y1)], kind="flow", color=VRC,
                size=7, sw=1.5)
        # per-VRC chain: W2->L3 -> move -> L13->W12 (shown as a teal arc above)
        ch = [boxes[2], boxes[3], boxes[4]]
        for a, b in zip(ch, ch[1:]):
            yb = a.y0 - 9
            d.polyline([(a.cx, a.y0), (a.cx, yb), (b.cx, yb), (b.cx, b.y0 - 1)], stroke=VRC, sw=1.4, dash="5 4",
                       radius=5)
            d.arrowhead((b.cx, b.y0), (b.cx, yb), kind="filled", color=VRC, size=7)
        d.text(boxes[5].x0, cmd_y + 100, "teal dashed: last_vrc_action chain of r1", size=11, fill=VRC)
        d.text(boxes[5].x0, cmd_y + 118, "grey: AGV-1's own order", size=11, fill=T.muted)

    frame(d, title="An AGV changes floors: what the pipeline does today",
          subtitle="Step through it: the layout entries that make a VRC, task planning (a plain TrayMove), SIPP "
                   "driving AGV-1 across the VRC edge, the two action-graph passes that turn the ride into VRC "
                   "commands, and the gaps. A two-floor layout made up for this figure; Pecos has no VRC.",
          badge_key="illustrative",
          legend=[("box", VRC, "VRC: node, edge, carriage, command"), ("box", AGV, "AGV-1 motion or command"),
                  ("box", TRAY, "tray T7"), ("dot", T.sky, "Waypoint"), ("box", T.fg2, "Parking"),
                  ("dashbox", T.red, "exists, never created"),
                  ("dash", T.tint(AGV, 0.7, T.bg), "AGV-1's planned path")],
          footnote="Ride numbers use the cost_functions defaults (vrc_transit 0.254 m/s, 0.2 m/s²; doors 3 s each); "
                   "the scheduler node reads the real values from ROS parameters (vrc.performance_limits.transit.*, "
                   "vrc.door.*). LOCOMOTE costs are not computed here. Sources: layout.cpp, pose_graph.cpp, "
                   "garage_graph.cpp, collision_geometry.cpp, chugg_sequential.cpp, scheduler.cpp "
                   "(CollectAndCollapseTrajectoryMotions), utils.cpp (InsertVrcActionsIntoDag).")
    return d


# ======================================================================================
# 113 — how the motion planner is packaged and called
# ======================================================================================
def _layer_box(d: Doc, x, y, w, h, name, tag, col, *, sub=None):
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=col, sw=1.5)
    d.text(x + 14, y + 18, name, size=13.5, family="mono", weight=700, fill=col)
    if sub:
        d.text(x + 14 + text_width(name, 13.5, "mono", 700) + 12, y + 18, sub, size=11, fill=T.muted)
    if tag:
        d.text(x + w - 14, y + 18, tag, size=10.5, family="mono", fill=T.faint, anchor="end")
    return BBox(x, y, x + w, y + h)


def _small(d: Doc, x, y, w, h, title, lines, col, *, title_mono=True, dashed=False, size=11):
    d.rect(x, y, w, h, rx=7, fill=T.tint(col, 0.08, T.bg), stroke=T.tint(col, 0.7, T.bg), sw=1.2,
           dash="5 4" if dashed else None)
    d.text(x + 10, y + 15, title, size=11.5, family="mono" if title_mono else "sans", weight=600, fill=col)
    for i, ln in enumerate(lines):
        d.text(x + 10, y + 34 + i * size * 1.5, ln, size=size, family="mono", fill=T.fg2)
    return BBox(x, y, x + w, y + h)


@figure("113_motion_planner_deployment", "How the motion planner is packaged and called", DOC_MP)
def motion_planner_deployment():
    d = Doc("113_motion_planner_deployment", "How the motion planner is packaged and called",
            "One OS process, scheduler_node, holds the ROS component, SchedulerRos with the plan service, the "
            "Scheduler library and the motion_planner shared library. A plan request runs synchronously on one "
            "thread from the service callback through task planning and CHUGG and back. Below: the package "
            "dependencies and what would change if the motion planner became a separate node.")
    SCH, MP, EXT, ROS = T.sky, T.amber, T.faint, T.violet
    PX0, PX1 = 300, 1330
    IX0, IX1 = PX0 + 22, PX1 - 22
    IW = IX1 - IX0
    # ---------- process frame ----------
    d.text(PX0 + 20, 22, "OS process: scheduler_node", size=15, weight=600, fill=T.fg)
    d.text(PX0 + 20 + text_width("OS process: scheduler_node", 15, "sans", 600) + 14, 22,
           "volley_add_component(scheduler_component ... PLUGIN \"volley::SchedulerComponent\" "
           "EXECUTABLE scheduler_node)", size=10.5, family="mono", fill=T.muted)
    # SchedulerComponent
    y0 = 50
    comp = _layer_box(d, IX0, y0, IW, 62, "SchedulerComponent", "scheduler_component.cpp · rclcpp component", ROS,
                      sub="RCLCPP_COMPONENTS_REGISTER_NODE(volley::SchedulerComponent)")
    d.text(IX0 + 14, y0 + 44, "reads ROS parameters (layout, scheduler.*, agv / vrc / bay / vecs limits), finds the "
           "layout file, builds SchedulerRos; a missing parameter exits the process", size=11, fill=T.fg2)
    # SchedulerRos
    y1 = comp.y1 + 34
    ros = _layer_box(d, IX0, y1, IW, 156, "SchedulerRos", "scheduler_ros.cpp · owns every ROS object", ROS)
    cw = (IW - 4 * 14) / 3
    c1 = _small(d, IX0 + 14, y1 + 32, cw, 110, "services (default callback group)",
                ["plan            interfaces/srv/Plan", "set_bay_readiness_ratio", "debug/printdags (Trigger)"], ROS,
                title_mono=False)
    _small(d, c1.x1 + 14, y1 + 32, cw, 110, "publishers (pub_cb_group_)",
           ["version_info    every 5 s", "report          every 5 s", "own MutuallyExclusive group:",
            "a long Plan() cannot block them"], T.green, title_mono=False)
    _small(d, c1.x1 + cw + 28, y1 + 32, cw, 110, "clients into /central",
           ["/central/clean_garage", "/central/rebalance_garage", "/central/transition_bay_to_insert",
            "/central/transition_bay_to_retrieve"], T.amber, title_mono=False)
    # Scheduler
    y2 = ros.y1 + 44
    sch = _layer_box(d, IX0, y2, IW, 176, "Scheduler", "libscheduler.so · volley_add_library(scheduler SHARED "
                     "src/scheduler.cpp src/utils.cpp)", SCH, sub="no ROS transport: only rclcpp::Logger, rclcpp::Time")
    _small(d, IX0 + 14, y2 + 32, 250, 130, "built once, in the constructor",
           ["layout_     Layout (YAML)", "pg_         PoseGraph", "gg_         GarageGraph", "table_      CollisionTable",
            "cost_model_ MotionCostModel"], SCH, title_mono=False)
    chips = [("ValidateBaseState", T.fg2), ("stages 1-3", T.amber), ("SanityCheckEvents", T.fg2),
             ("PlanMotions", SCH), ("ResponseFromTrajectories", T.fg2)]
    CX0 = IX0 + 282
    d.text(CX0, y2 + 47, "Plan(request_data, now): one call, one thread, start to finish", size=11.5,
           weight=600, fill=SCH)
    cx = CX0
    cy = y2 + 96
    cb = {}
    for i, (t, c) in enumerate(chips):
        w = text_width(t, 10.5, "mono", 600) + 16
        b = chip(d, cx, cy, t, c, size=10.5)
        cb[t] = b
        if i < len(chips) - 1:
            connect(d, [(b.x1 + 2, cy), (b.x1 + 20, cy)], kind="flow", color=T.faint, size=6, sw=1.2)
        cx = b.x1 + 22
    tpb = cb["stages 1-3"]
    d.text(tpb.cx, tpb.y0 - 10, "task planning", size=10.5, fill=T.amber, anchor="middle")
    d.text(cb["PlanMotions"].cx, tpb.y0 - 10, "motion planning", size=10.5, fill=SCH, anchor="middle")
    d.text(cb["ResponseFromTrajectories"].cx, tpb.y0 - 10, "action DAG", size=10.5, fill=T.fg2, anchor="middle")
    # motion_planner
    y3 = sch.y1 + 92
    mp = _layer_box(d, IX0, y3, IW, 206, "libmotion_planner.so", "volley_add_library(motion_planner SHARED "
                    "DIRECTORY src)", MP)
    d.text(IX0 + 14, y3 + 190, "a plain C++ shared library: no node, no component, no ROS interfaces; rclcpp only "
           "for logging (rclcpp::Logger, RCLCPP_ERROR); data types are interfaces message structs and common_ros "
           "classes", size=11, fill=T.fg2)
    sw_ = (IW - 3 * 14) / 2
    srch = _small(d, IX0 + 14, y3 + 34, sw_, 130, "single-agent searches (called many times by task planning)",
                  ["SingleSourceSearch, GetPosePath     path_search, garage_graph_pathing",
                   "GetStaticFilter, GetDisabledEntitiesFilters   static_graph_filtering",
                   "HideAgvs                             agv_hiding_search",
                   "BlockingTraySearchEnvironment        blocking_tray_search"], MP, title_mono=False, size=10.5)
    chg = _small(d, srch.x1 + 14, y3 + 34, sw_, 130, "CHUGG (called once per plan by PlanMotions)",
                 ["GetEdgeDurations, GetAllPairsMinCost  per call",
                  "ContinuousState init(initial_state, table_, layout, t0)",
                  "Chugg(gg_, table_, events, init, ...)  fresh per call",
                  "SolveSequential(audit) -> optional<ContinuousState>",
                  "  SippAgv, SippEnvironment, SafeIntervalTable, ..."], MP, title_mono=False, size=10.5)
    # process frame (drawn last so it encloses everything)
    d.rect(PX0, 0, PX1 - PX0, mp.y1 + 22, rx=14, fill=T.tint(SCH, 0.035, T.bg), stroke=T.sky, sw=1.4, layer="bg")

    # ---------- call path ----------
    # Dispatch column
    DX1 = 170
    dsp = BBox(0, y1 - 10, DX1, y1 + 170)
    d.rect(dsp.x0, dsp.y0, dsp.w, dsp.h, rx=12, fill=T.bg, stroke=T.border, sw=1.4, dash="6 5")
    d.text(16, dsp.y0 + 24, "Dispatch", size=15, weight=600, fill=T.fg)
    d.text(16, dsp.y0 + 44, "(in the central node)", size=11.5, fill=T.muted)
    for i, ln in enumerate(wrap("Owns the job queue, calls plan with the current garage state and executes the "
                                "action DAG it gets back.", DX1 - 30, 11)):
        d.text(16, dsp.y0 + 70 + i * 15, ln, size=11, fill=T.muted)
    plan_y = c1.y0 + 42
    connect(d, [(DX1, plan_y - 8), (c1.x0 - 2, plan_y - 8)], kind="flow", color=SCH, size=8, sw=1.6)
    label_pill(d, (DX1 + c1.x0) / 2, plan_y - 22, "PlanRequest", color=SCH, size=10.5)
    connect(d, [(c1.x0, plan_y + 12), (DX1 + 2, plan_y + 12)], kind="flow", color=T.green, size=8, sw=1.6,
            dash="5 4")
    label_pill(d, (DX1 + c1.x0) / 2, plan_y + 26, "PlanResponse", color=T.green, size=10.5)
    num_badge(d, DX1 + 16, plan_y - 22, 1, SCH, r=10)
    num_badge(d, DX1 + 16, plan_y + 26, 7, T.green, r=10)
    cl_y = c1.y1 - 6
    connect(d, [(IX0, cl_y), (DX1 + 2, cl_y)], kind="flow", color=T.amber, size=7, sw=1.3, dash="5 4")
    d.text(DX1 + 10, cl_y + 14, "async job requests", size=10, fill=T.amber)
    # 2: SchedulerRos -> Scheduler::Plan
    px = c1.cx
    connect(d, [(px, c1.y1), (px, sch.y0)], kind="flow", color=SCH, size=8, sw=1.6)
    label_pill(d, px + 12, (c1.y1 + sch.y0) / 2, "scheduler_->Plan(request->request_data, node_->now())  "
               "synchronous, same thread", color=SCH, size=10.5, anchor="start")
    num_badge(d, px - 18, (c1.y1 + sch.y0) / 2, 2, SCH, r=10)
    # 3: task planning -> searches
    tp = cb["stages 1-3"]
    x3 = srch.x0 + 330
    connect(d, [(tp.cx, tp.y1), (tp.cx, sch.y1 + 33), (x3, sch.y1 + 33), (x3, mp.y0 + 34)], kind="flow",
            color=T.amber, size=8, sw=1.5)
    num_badge(d, x3 - 18, sch.y1 + 33, 3, T.amber, r=10)
    label_pill(d, x3 + 8, sch.y1 + 54, "many direct calls", color=T.amber, size=10.5, anchor="start")
    # 4/5: PlanMotions -> CHUGG and back
    pm = cb["PlanMotions"]
    xa, xb = chg.x0 + 40, chg.x0 + 100
    connect(d, [(pm.cx - 14, pm.y1), (pm.cx - 14, sch.y1 + 22), (xa, sch.y1 + 22), (xa, chg.y0)],
            kind="flow", color=SCH, size=8, sw=1.5)
    connect(d, [(xb, chg.y0), (xb, sch.y1 + 44), (pm.cx + 14, sch.y1 + 44), (pm.cx + 14, pm.y1 + 1)],
            kind="flow", color=T.green, size=8, sw=1.5, dash="5 4")
    num_badge(d, xa - 16, sch.y1 + 76, 4, SCH, r=10)
    label_pill(d, xa - 32, sch.y1 + 76, "SolveSequential", color=SCH, size=10.5, anchor="end")
    num_badge(d, xb + 16, sch.y1 + 76, 5, T.green, r=10)
    label_pill(d, xb + 32, sch.y1 + 76, "optional<ContinuousState>", color=T.green, size=10.5, anchor="start")
    # 6: response
    rf = cb["ResponseFromTrajectories"]
    num_badge(d, rf.x1 + 16, rf.cy, 6, T.fg2, r=10)

    # ---------- bottom: package dependencies + library vs node ----------
    by = mp.y1 + 70
    d.text(0, by, "Package dependencies (package.xml)", size=14, weight=600, fill=T.fg)
    pk = {}

    def pkg(key, x, y, label, col, sub=None, dashed=False, w=150):
        d.rect(x, y, w, 40 if not sub else 52, rx=8, fill=T.card, stroke=col, sw=1.4, dash="5 4" if dashed else None)
        d.text(x + 10, y + 16, label, size=12, family="mono", weight=700, fill=col)
        if sub:
            d.text(x + 10, y + 36, sub, size=10, fill=T.muted)
        pk[key] = BBox(x, y, x + w, y + (40 if not sub else 52))
    gy = by + 26
    pkg("sch", 0, gy + 74, "scheduler", SCH, "node + libscheduler", w=150)
    pkg("mp", 220, gy + 74, "motion_planner", MP, "libmotion_planner", w=160)
    deps = ["common_ros", "cost_functions", "planner_core", "interfaces"]
    for i, k in enumerate(deps):
        pkg(k, 460, gy + i * 50, k, T.fg2, w=150)
    connect(d, [(pk["sch"].x1, pk["sch"].cy), (pk["mp"].x0, pk["mp"].cy)], kind="dep", color=MP, size=8)
    for k in deps:
        b = pk[k]
        connect(d, [(pk["mp"].x1, pk["mp"].cy), (pk["mp"].x1 + 40, pk["mp"].cy), (pk["mp"].x1 + 40, b.cy),
                    (b.x0, b.cy)], kind="dep", color=T.fg2, size=8, radius=6)
    d.text(0, gy + 220, "motion_planner also: common, eigen, rclcpp, rclcppx (declared; no snapshot source", size=11,
           fill=T.muted)
    d.text(0, gy + 236, "includes it). scheduler depends on all four directly as well, plus task_planner (not in",
           size=11, fill=T.muted)
    d.text(0, gy + 252, "the snapshots), vrc_interfaces, rclcpp_components, rclcppx, std_srvs, stdx.", size=11,
           fill=T.muted)
    # library vs node table
    TX = 720
    TW = PX1 - TX
    d.text(TX, by, "Library today vs a separate motion-planner node", size=14, weight=600, fill=T.fg)
    rows = [
        ("Call", "a C++ call on the plan-service thread; gg_, table_, the event DAG and edge costs passed by const "
                 "reference", "a service or action call per plan, with a timeout"),
        ("Data", "nothing is copied or serialised", "ScheduleEventDag and ContinuousState are C++ classes, not "
                 "messages: new .msg types or a serialiser; the node keeps its own Layout, GarageGraph and "
                 "CollisionTable"),
        ("Latency", "the search itself", "plus serialise, transport and deserialise per call; task planning's "
                    "many single-agent searches would have to stay in the scheduler (inference)"),
        ("Failure", "a crash or hang in CHUGG takes the scheduler node with it", "restartable and replaceable on its "
                    "own; the scheduler must handle timeouts and a missing planner"),
        ("Versions", "one build: scheduler and motion_planner always match", "two deployables: message schema, cost "
                     "parameters and layout (md5) must be checked to match"),
    ]
    c0, c1w = 80, (TW - 80) / 2
    ty = by + 18
    d.rect(TX, ty, TW, 26, rx=6, fill=T.card_hi)
    d.text(TX + 10, ty + 13, "", size=10)
    d.text(TX + c0 + 10, ty + 13, "TODAY: SHARED LIBRARY", size=10, family="mono", weight=600, fill=MP,
           letter_spacing=0.5)
    d.text(TX + c0 + c1w + 10, ty + 13, "IF IT BECAME ITS OWN NODE", size=10, family="mono", weight=600,
           fill=T.violet, letter_spacing=0.5)
    ty += 30
    for i, (k, a, b) in enumerate(rows):
        la = wrap(a, c1w - 20, 11)
        lb = wrap(b, c1w - 20, 11)
        h = max(len(la), len(lb)) * 15.5 + 14
        d.rect(TX, ty, TW, h, rx=5, fill=T.card if i % 2 == 0 else T.tint(T.card, 0.5, T.bg))
        d.text(TX + 10, ty + 8, k, size=11.5, weight=600, fill=T.fg, baseline="top")
        for j, ln in enumerate(la):
            d.text(TX + c0 + 10, ty + 8 + j * 15.5, ln, size=11, fill=T.fg2, baseline="top")
        for j, ln in enumerate(lb):
            d.text(TX + c0 + c1w + 10, ty + 8 + j * 15.5, ln, size=11, fill=T.fg2, baseline="top")
        ty += h + 3

    frame(d, title="How the motion planner is packaged and called",
          subtitle="The motion planner is a shared library linked into the scheduler node, not a node of its own. A "
                   "plan request runs on one thread, synchronously, from the plan service callback through task "
                   "planning (which calls the single-agent searches) and CHUGG (built fresh for each call) and back "
                   "to the service response.",
          badge_key="as-built",
          legend=[("arrow", SCH, "call (synchronous)"), ("dasharrow", T.green, "return"),
                  ("dasharrow", T.amber, "async request to Dispatch"), ("dep", T.fg2, "package depends on"),
                  ("box", ROS, "ROS layer"), ("box", SCH, "scheduler library"), ("box", MP, "motion_planner")],
          footnote="From scheduler_component.cpp, scheduler_ros.cpp, scheduler.cpp (Scheduler::Scheduler, Plan, "
                   "PlanMotions), the scheduler and motion_planner CMakeLists.txt and package.xml. Dispatch is not in "
                   "the snapshots; its role is inferred from comments and client names. The right-hand column of the "
                   "table is a design assessment, not existing code.")
    return d
