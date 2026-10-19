"""fig_messages: the Plan service messages, field by field (118-121).

Doc 01-background.html, section "ROS messages and services".

Facts drawn, each from the snapshots:
* PlanRequest.msg field comments: base_schedule is "the immutable portion of the current schedule" and the
  scheduler "is to assume that all of these actions will be completed"; planned_jobs "will be completed during
  execution of the base schedule"; active_jobs "have actions in the base schedule but will not be completed by
  the base schedule"; pending_jobs "need to be planned". ActionNode.outside_split: "outside the split in the
  schedule while waiting on the plan call response and will not be sent".
* Scheduler::Plan reads request_data.id, base_state (ValidateBaseState), base_schedule (reservation loop) and
  pending_jobs; planned_jobs, active_jobs and outside_split are never read in src/.
* DiscreteGarageState::Set (common_ros) rebuilds the state from existence events in the order: fault, AGVs
  (tray_id forced to 0), bays, VECS, VRCs, trays (tray.agv_id re-attaches), payloads (payload.tray_id sets the
  tray's payload), disabled nodes. The message's hash is not checked. ValidateBaseState then checks payload
  sizes against the layout's resource windows and that AGV and tray poses exist.
* ActionNodeFromMotion (scheduler.cpp) writes guid, job_id, duration, type, the id and command of the type;
  BuildScheduledActionsArray writes parents. status, outside_split and AgvCommand.id are left at defaults.
The scenario (AGV-2, T15, B21, j0, j1) is the one of figure 116; times are illustrative.
"""
from __future__ import annotations

from components import chip, code_panel, connect, frame, label_pill, uml_class
from facility import Map, Scene
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC = "01-background.html"
QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)
BUSY = T.violet
KEEP = T.red
NEW = T.sky
DONE = T.faint
JA, JB, JN = T.amber, T.teal, T.sky      # job colours: J-A (active), J-B (planned), new plan


# --------------------------------------------------------------------------------------
# 118 — PlanRequest on a time line
# --------------------------------------------------------------------------------------

@figure("118_plan_request_timeline", "A PlanRequest on the time line (animated)", DOC)
def plan_request_timeline():
    d = Doc("118_plan_request_timeline", "A PlanRequest on the time line",
            "Animated: what each PlanRequest field means relative to the schedule Dispatch is already running: "
            "base_state is the garage now, base_schedule the actions that keep running during the call, and the "
            "three job lists sort jobs by how much of them that schedule covers.")
    S0 = d.step("The schedule Dispatch is running when it calls Plan(). Each box is one ActionNode on the lane of "
                "the asset that executes it. Faded boxes are finished. The line marks now, when the request is built.")
    S1 = d.step("id is a fresh Guid that the response echoes. base_state is the garage at now, as a discrete "
                "snapshot: AGV-2 has lifted T15 at P15 (a0 is finished) and waits for a1.")
    S2 = d.step("The split. Actions before it keep being sent while the call is in flight: they form "
                "base_schedule (a1, a2, b1), which the scheduler must assume will complete. Actions after it are "
                "held back (outside_split = true) and are not sent.")
    S3 = d.step("planned_jobs: jobs that base_schedule finishes (J-B, the bay transition). active_jobs: jobs "
                "with actions in base_schedule that it does not finish (J-A: its lower, a3, is held back).")
    S4 = d.step("pending_jobs: jobs to plan now (j0 and j1). They have no actions yet. Plan() reads only id, "
                "base_state, base_schedule and pending_jobs; planned_jobs and active_jobs are not read.")
    S5 = d.step("Plan() reserves AGV-2 and B21 from now to the end of the new plan, plans j1 on AGV-1 and fails "
                "j0 (it needs AGV-2). The response holds only the new actions; joining them to the running schedule "
                "is Dispatch's job.")

    x0 = 150                      # lane label column
    tmin, tmax = -24.0, 44.0
    px = 13.5
    X = lambda t: x0 + (t - tmin) * px
    lanes = ["AGV-1", "AGV-2", "AGV-3", "B21 (bay)"]
    lh = 64
    y_top = 40
    Y = {ln: y_top + i * lh for i, ln in enumerate(lanes)}
    x_end = X(tmax)
    # lanes
    for ln in lanes:
        y = Y[ln]
        d.rect(x0, y, x_end - x0, lh - 10, rx=6, fill=T.tint(T.fg, 0.03, T.bg), stroke=T.border_soft, sw=1,
               layer="bg")
        d.text(x0 - 14, y + (lh - 10) / 2, ln, size=12.5, family="mono", weight=600,
               fill=BUSY if ln in ("AGV-2", "B21 (bay)") else T.fg2, anchor="end")
    # time axis
    ya = Y[lanes[-1]] + lh + 4
    d.line(x0, ya, x_end, ya, stroke=T.border, sw=1.2)
    for t in range(-20, 45, 10):
        d.line(X(t), ya, X(t), ya + 5, stroke=T.border, sw=1)
        d.text(X(t), ya + 17, f"{t:+d} s" if t else "0", size=S.tiny, family="mono", fill=T.muted, anchor="middle")
    d.text(x_end, ya + 34, "time relative to the request (illustrative)", size=S.small, fill=T.muted, anchor="end")

    def act(lane, t0, t1, name, label, col, *, k=None, faded=False, held=False):
        y = Y[lane] + 7
        h = lh - 24
        x, w = X(t0), X(t1) - X(t0) - 3
        ctx = d.at(k) if k is not None else _null()
        with ctx:
            d.rect(x, y, w, h, rx=6, fill=T.card if not faded else T.bg, stroke=col, sw=1.5,
                   dash="5 4" if held else None, opacity=0.5 if faded else None)
            d.text(x + 8, y + 13, name, size=10.5, family="mono", weight=700, fill=col, opacity=0.6 if faded else None)
            d.text(x + 8, y + 29, label, size=10.5, family="mono", fill=T.fg2 if not faded else T.muted,
                   opacity=0.6 if faded else None)
        return BBox(x, y, x + w, y + h)

    # finished actions
    act("AGV-1", -22, -12, "c0", "W25->W26", DONE, faded=True)
    act("AGV-2", -14, -4, "a0", "lift @P15", JA, faded=True)
    # running schedule
    A1 = act("AGV-2", 1, 11, "a1", "P15->P19", JA)
    A2 = act("AGV-2", 11, 21, "a2", "P19->P23", JA)
    B1 = act("B21 (bay)", 2, 24, "b1", "TRANSITION_TO_RETRIEVE", JB)
    A3 = act("AGV-2", 26, 32, "a3", "lower @P23", JA, held=True)
    # now line
    d.line(X(0), y_top - 18, X(0), ya, stroke=T.fg, sw=2, layer="over")
    label_pill(d, X(0), y_top - 22, "now", color=T.fg, size=11.5, bg=T.bg)
    # split
    xs = X(24.5)
    with d.at(S2):
        d.line(xs, y_top - 18, xs, ya, stroke=T.amber, sw=2, dash="7 5", layer="over")
        label_pill(d, xs, y_top - 22, "split", color=T.amber, size=11.5, bg=T.bg)
        d.rect(X(0) + 2, y_top - 4, xs - X(0) - 4, ya - y_top + 2, rx=8, fill=BUSY, opacity=0.06, layer="under")
        d.text((X(0) + xs) / 2, ya - 8, "base_schedule", size=11.5, family="mono", weight=700, fill=BUSY,
               anchor="middle", halo=T.bg, halo_w=3)
        d.text(xs + 8, ya - 8, "outside_split = true: held back", size=11, family="mono", fill=T.amber,
               halo=T.bg, halo_w=3)
    # base_state column
    with d.at(S1):
        d.rect(X(0) - 4, y_top - 6, 8, ya - y_top + 6, rx=3, fill=T.fg, opacity=0.25, layer="under")
    # S5: reservation hatch and new plan
    with d.at(S5):
        for ln in ("AGV-2", "B21 (bay)"):
            y = Y[ln]
            d.rect(X(0), y + 2, x_end - X(0) - 2, lh - 14, rx=5, fill=KEEP, opacity=0.08, layer="under")
            d.rect(X(0), y + 2, x_end - X(0) - 2, lh - 14, rx=5, fill="none", stroke=KEEP, sw=1.5, dash="4 4",
                   layer="under")
            d.text(x_end - 8, y + lh - 18, "reserved", size=10.5, fill=KEEP, anchor="end",
                   halo=T.bg, halo_w=3, layer="top")
    for (t0, t1, nm, lb) in ((1, 8, "n1", "W26->W27"), (8, 15, "n2", "W27->P24"), (15, 19, "n3", "lift"),
                             (19, 28, "n4", "P24->P20"), (28, 32, "n5", "lower")):
        act("AGV-1", t0, t1, nm, lb, JN, k=S5)

    # right-hand cards: the request fields
    cx = x_end + 40
    cw = 380
    y = 0

    def card(title, rows, col, k_show, k_hl=None, mono=True):
        nonlocal y
        h = 30 + 21 * len(rows) + 8
        bb = BBox(cx, y, cx + cw, y + h)
        d.rect(cx, y, cw, h, rx=9, fill=T.card, stroke=T.tint(col, 0.7, T.bg), sw=1.3)
        d.text(cx + 12, y + 16, title, size=12, family="mono", weight=700, fill=col)
        yy = y + 38
        for r in rows:
            with d.at(k_show):
                d.text(cx + 14, yy, r, size=11.5, family="mono" if mono else "sans", fill=T.fg2)
            yy += 21
        if k_hl is not None:
            with d.only(k_hl):
                d.rect(cx - 4, y - 4, cw + 8, h + 8, rx=12, fill="none", stroke=col, sw=2.2, layer="under")
        y += h + 10
        return bb

    card("id", ["Guid of this call; echoed in PlanResponse.id"], T.fg2, S1, S1)
    card("base_state : DiscreteGarageState", ["AGV-2 at P15@90, lift up, tray_id 15",
                                              "AGV-1 at W26, AGV-3 at W13: idle",
                                              "B21: READY_TO_INSERT",
                                              "trays T15, T17 (+ car), T24"], T.violet, S1, S1)
    card("base_schedule : Schedule", ["a1  AGV-2  P15@90 -> P19@90", "a2  AGV-2  P19@90 -> P23@90",
                                      "b1  B21  TRANSITION_TO_RETRIEVE"], BUSY, S2, S2)
    card("planned_jobs : SchedulerJob[]", ["J-B  TRANSITION_BAY_TO_RETRIEVE  B21"], JB, S3, S3)
    card("active_jobs : SchedulerJob[]", ["J-A  REPARK_TRAY  T15 -> P23"], JA, S3, S3)
    card("pending_jobs : SchedulerJob[]", ["j0  MOVE_AGV     AGV-2 -> C14", "j1  REPARK_TRAY  T24 -> P20"], JN,
         S4, S4)
    with d.at(S5):
        d.text(cx + 14, y + 8, "response: j1 -> n1..n5 (STATE_EXECUTING)", size=11.5, family="mono", fill=JN)
        d.text(cx + 14, y + 29, "response: j0 -> STATE_ERROR, \"disabled agv 2\"", size=11.5, family="mono",
               fill=KEEP)
    frame(d, title="A PlanRequest on the time line",
          subtitle="The request describes one moment in a schedule that keeps running. Lane colours: violet = "
                   "assets busy in base_schedule. Durations and the place of the split are illustrative; where "
                   "Dispatch draws the split is not in the snapshots.",
          badge_key="conceptual",
          legend=[("box", JA, "J-A: active job"), ("box", JB, "J-B: planned job"), ("box", JN, "j1: new plan"),
                  ("dashbox", T.amber, "held back (outside_split)"), ("dashbox", KEEP, "reserved lane")])
    return d


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# --------------------------------------------------------------------------------------
# 119 — base_state: records, links, and how Set() rebuilds them
# --------------------------------------------------------------------------------------

@figure("119_base_state_records", "base_state: records, links and how they are loaded (animated)", DOC)
def base_state_records():
    d = Doc("119_base_state_records", "base_state: records, links and how they are loaded",
            "Animated: the DiscreteGarageState message of the running example, record by record, in the order "
            "DiscreteGarageState::Set adds them, and the checks ValidateBaseState runs afterwards.")
    S0 = d.step("The garage at now, in the scenario of the time-line figure. The message lists every asset in "
                "flat arrays; links between records are ids, not pointers.")
    S1 = d.step("Set() starts empty and replays one existence event per record. AGVs come first, with tray_id "
                "forced to 0, because their trays do not exist yet.")
    S2 = d.step("Bays, then VECS and VRCs (none in this layout). A bay record is a state machine value and an "
                "operator flag; its position comes from the layout, since a bay's id is its node id.")
    S3 = d.step("Trays. A tray with agv_id != 0 is attached to that AGV (which must be lifted, on the same node "
                "and parallel), and the AGV's tray_id is set from it: tray.agv_id is the field that counts.")
    S4 = d.step("Payloads. payload.tray_id puts the car on its tray (which must be empty): tray.payload_id is "
                "filled from it. reciprocal_to_tray says the car faces the other way on the tray.")
    S5 = d.step("disabled_nodes become NodeDisablednessChanged events (none here). The message's hash is not "
                "compared. Any failed event rejects the whole request: PlanResponse.success = false.")
    S6 = d.step("ValidateBaseState then checks the state against the layout: every payload fits some resource "
                "window, and every AGV and tray pose exists. Only after that does the reservation loop run.")
    s = 22
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    sc = Scene(m)
    sc.tray("T15", 15, chip_pos="bl")
    sc.tray("T17", 17, payload=True, chip_pos="bl")
    sc.tray("T24", 24, chip_pos="tr")
    sc.agv("AGV-2", 15, heading=90, color=BUSY, label_side="right")
    sc.agv("AGV-1", 26, heading=90, label_side="above")
    sc.agv("AGV-3", 13, heading=90, label_side="below")
    sc.lift(S0, "AGV-2")
    sc.draw()
    mb = m.box
    # record boxes in columns
    gx = mb.x1 + 40
    colw = 300
    rec = {}

    def record(key, x, y, name, rows, col, k):
        with d.at(k):
            b = uml_class(d, x, y, name, accent=col, attrs=rows, w=colw, size=11.5, name_size=12.5, compact=True)
        rec[key] = b
        return b

    y = mb.y0
    a1 = record("a1", gx, y, "agvs[0]", ["id = 1", "pose = {26, 90}", "lift = false", "tray_id = 0"], T.green, S1)
    a2 = record("a2", gx, a1.y1 + 10, "agvs[1]", ["id = 2", "pose = {15, 90}", "lift = true",
                                                  "tray_id = 15  (zeroed, then re-set)", "disabled = false"], BUSY, S1)
    b21 = record("b21", gx, a2.y1 + 10, "bays[0]", ["id = 21", "state = READY_TO_INSERT", "disabled = false"],
                 T.teal, S2)
    tx = gx + colw + 36
    t15 = record("t15", tx, mb.y0, "trays[0]", ["id = 15", "pose = {15, 90}", "agv_id = 2",
                                                "payload_id = 0"], T.amber, S3)
    t17 = record("t17", tx, t15.y1 + 10, "trays[1]", ["id = 17", "pose = {17, 90}", "agv_id = 0",
                                                      "payload_id = G  (filled from payload)"], T.amber, S3)
    p = record("p", tx, t17.y1 + 10, "payloads[0]", ["payload.id = G", "payload.length_m = 4.9 ...",
                                                     "tray_id = 17", "reciprocal_to_tray = false"], T.pink, S4)
    dn = record("dn", gx, b21.y1 + 10, "disabled_nodes", ["[]   (operator-closed nodes)"], KEEP, S5)
    # links (row centres mirror uml_class geometry: header 32.5, pad 8, row 11.5 * 1.55)
    def row_y(b, i):
        return b.y0 + 32.5 + 8 + 11.5 * 1.55 * (i + 0.5)

    with d.at(S3):
        ya, yb = row_y(t15, 2), row_y(a2, 3)
        xm = (a2.x1 + t15.x0) / 2
        d.polyline([(t15.x0, ya), (xm, ya), (xm, yb), (a2.x1 + 8, yb)], stroke=T.amber, sw=1.8, radius=5)
        d.arrowhead((a2.x1, yb), (a2.x1 + 12, yb), kind="filled", color=T.amber, size=9)
    with d.at(S4):
        ya, yb = row_y(p, 2), row_y(t17, 3)
        xr = p.x1 + 18
        d.polyline([(p.x1, ya), (xr, ya), (xr, yb), (t17.x1 + 8, yb)], stroke=T.pink, sw=1.8, radius=5)
        d.arrowhead((t17.x1, yb), (t17.x1 + 12, yb), kind="filled", color=T.pink, size=9)
    # the map entity of each step
    for k, nids in ((S1, (26, 15, 13)), (S2, (21,)), (S3, (15, 17, 24)), (S4, (17,))):
        with d.only(k):
            for nid in nids:
                x_, y_ = m.P(nid)
                d.circle(x_, y_, 34 if nid != 21 else 46, fill="none", stroke=T.sky, sw=2.2, layer="top")
    # order strip
    oy = max(dn.y1, p.y1, mb.y1) + 28
    order = [("fault", None), ("agvs", S1), ("bays", S2), ("vexen, vrcs", S2), ("trays", S3), ("payloads", S4),
             ("disabled_nodes", S5), ("layout checks", S6)]
    d.text(0, oy, "DiscreteGarageState::Set(msg), then ValidateBaseState:", size=12, weight=600, fill=T.fg)
    ox = 0
    for i, (lbl, k) in enumerate(order):
        w = text_width(lbl, 11.5, "mono", 600) + 24
        bb = BBox(ox, oy + 16, ox + w, oy + 46)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=15, fill=T.card, stroke=T.border, sw=1.2)
        d.text(bb.cx, bb.cy, lbl, size=11.5, family="mono", weight=600, fill=T.fg2, anchor="middle")
        if k is not None:
            with d.only(k):
                d.rect(bb.x0 - 3, bb.y0 - 3, bb.w + 6, bb.h + 6, rx=18, fill="none", stroke=T.sky, sw=2.2)
        if i < len(order) - 1:
            d.arrowhead((ox + w + 16, bb.cy), (ox + w + 2, bb.cy), kind="filled", color=T.muted, size=8)
        ox += w + 20
    with d.only(S6):
        d.text(0, oy + 66, "payload fits a resource window (GetSmallestEnclosingResourceSizeIndex); AGV and tray "
                           "poses exist (HasGaragePose)", size=11.5, family="mono", fill=T.sky)
    frame(d, title="base_state: records, links and how they are loaded",
          subtitle="Ids link records: tray.agv_id and payload.tray_id are authoritative, agv.tray_id and "
                   "tray.payload_id are rebuilt from them. Values are illustrative.",
          badge_key="yaml+hyp",
          legend=[("box", T.green, "AGV record"), ("box", T.amber, "tray record"), ("box", T.pink, "payload record"),
                  ("box", T.teal, "bay record"), ("assoc", T.fg2, "id link used by Set()")])
    return d


# --------------------------------------------------------------------------------------
# 120 — SchedulerJob: who writes which field
# --------------------------------------------------------------------------------------

@figure("120_scheduler_job_round_trip", "SchedulerJob: who writes which field", DOC)
def scheduler_job_round_trip():
    d = Doc("120_scheduler_job_round_trip", "SchedulerJob: who writes which field",
            "A SchedulerJob travels from Dispatch to the scheduler in PlanRequest.pending_jobs and back inside "
            "PlanResponse.scheduled_jobs[i].job. Each field group is written by one side.")
    DIS, SCH = T.sky, T.green
    groups = [
        ("identity", DIS, ["type, type_name", "guid", "time_registered"], "Dispatch, when the job is created"),
        ("arguments", DIS, ["agv_id, bay_id, tray_id: uint16", "payload_id: Guid", "destination: GaragePose",
                            "allow_reciprocal: bool"], "Dispatch; only those of the job's type are read"),
        ("status in", DIS, ["state = STATE_UNPLANNED"], "Dispatch"),
        ("status out", SCH, ["state, state_name: EXECUTING | ERROR", "note: failure message",
                             "retain_job: retry next call"], "Plan(): FailJob or the final loop"),
        ("timestamps", SCH, ["time_planned"], "SchedulerRos, after Plan() returns"),
        ("never written", T.faint, ["time_completed", "seconds_to_bay_arrival", "needs_bay_in_retrieve"],
         "not set anywhere in scheduler src/"),
    ]
    x = 0
    y = 0
    w = 330
    boxes = []
    for i, (name, col, rows, who) in enumerate(groups):
        cx = (i % 3) * (w + 40)
        cy = (i // 3) * 190
        b = uml_class(d, cx, cy, name, accent=col, attrs=rows, w=w, size=11.5, name_size=12.5, compact=True,
                      stereo="field group")
        d.text(cx, b.y1 + 16, who, size=11, fill=T.muted)
        boxes.append(b)
    # state machine
    sy = 400
    d.text(0, sy, "SchedulerJob.state across one call", size=12.5, weight=600, fill=T.fg)
    st = {}
    for name, x_, col in (("STATE_UNPLANNED", 0, DIS), ("STATE_EXECUTING", 380, SCH), ("STATE_ERROR", 380, KEEP),
                          ("STATE_SUCCESS", 760, T.faint)):
        yy = sy + 30 if name != "STATE_ERROR" else sy + 110
        tw = text_width(name, 12, "mono", 700) + 30
        d.rect(x_, yy, tw, 40, rx=20, fill=T.card, stroke=col, sw=1.6)
        d.text(x_ + tw / 2, yy + 20, name, size=12, family="mono", weight=700, fill=col, anchor="middle")
        st[name] = BBox(x_, yy, x_ + tw, yy + 40)
    u, e, er, su = st["STATE_UNPLANNED"], st["STATE_EXECUTING"], st["STATE_ERROR"], st["STATE_SUCCESS"]
    connect(d, [(u.x1, u.cy), (e.x0, e.cy)], kind="assoc", color=SCH, sw=1.6, label="planned and motion plan found")
    connect(d, [(u.cx, u.y1), (u.cx, er.cy), (er.x0, er.cy)], kind="assoc", color=KEEP, sw=1.6,
            label="job or stage failed")
    connect(d, [(e.x1, e.cy), (su.x0, su.cy)], kind="assoc", color=T.faint, sw=1.4, dash="5 4",
            label="Dispatch, after execution")
    frame(d, title="SchedulerJob: who writes which field",
          subtitle="Blue groups are set by Dispatch and only read by the scheduler; green groups are written by "
                   "the scheduler into the copy it returns. The scheduler never sets STATE_SUCCESS.",
          badge_key="as-built",
          legend=[("box", DIS, "written by Dispatch"), ("box", SCH, "written by the scheduler"),
                  ("box", T.faint, "not written by the scheduler")])
    return d


# --------------------------------------------------------------------------------------
# 121 — ActionNode and AgvCommand
# --------------------------------------------------------------------------------------

@figure("121_action_node_anatomy", "ActionNode and AgvCommand, field by field", DOC)
def action_node_anatomy():
    d = Doc("121_action_node_anatomy", "ActionNode and AgvCommand, field by field",
            "Left: a Schedule is an array of ActionNodes in topological order; parents are indices of earlier "
            "nodes. Right: the four kinds of AgvCommand, told apart by comparing src and dst.")
    # schedule as array + DAG
    nodes = [("0", "B21", "TRANSITION_TO_RETRIEVE"), ("1", "AGV-1", "W22@90 -> W41@90 (T17)"),
             ("2", "AGV-1", "W41@90 -> B21@90 (T17)"), ("3", "AGV-1", "lower @B21"),
             ("4", "B21", "PROCESS_RETRIEVE"), ("5", "AGV-1", "B21@90 -> W41@90")]
    parents = {1: [], 2: [1], 3: [2], 4: [3, 0], 5: [3]}
    bw, bh = 300, 46
    ys = {}
    for i, (idx, who, what) in enumerate(nodes):
        y = i * (bh + 14)
        col = T.green if who.startswith("AGV") else T.violet
        d.rect(40, y, bw, bh, rx=8, fill=T.card, stroke=col, sw=1.5)
        d.text(52, y + 15, f"nodes[{idx}]  {'TYPE_AGV_COMMAND' if col == T.green else 'TYPE_BAY_COMMAND'}",
               size=10.5, family="mono", weight=600, fill=col)
        d.text(52, y + 33, f"{who}: {what}", size=11.5, family="mono", fill=T.fg)
        d.text(30, y + bh / 2, idx, size=12, family="mono", weight=700, fill=T.muted, anchor="end")
        ys[i] = y
    for c, ps in parents.items():
        for k, p in enumerate(ps):
            off = 18 + 22 * k + (c - p) * 4
            x = 40 + bw
            pts = [(x, ys[p] + bh / 2 + 6), (x + off, ys[p] + bh / 2 + 6), (x + off, ys[c] + bh / 2 - 6),
                   (x, ys[c] + bh / 2 - 6)]
            connect(d, pts, kind="assoc", color=T.sky, sw=1.4)
    d.text(40 + bw + 70, ys[4] + bh / 2 + 4, "parents = [3, 0]", size=11.5, family="mono", fill=T.sky)
    d.text(40, ys[5] + bh + 26, "parents are indices into Schedule.nodes; every parent index is smaller",
           size=11, fill=T.muted)
    d.text(40, ys[5] + bh + 44, "than the node's own index (topological order).", size=11, fill=T.muted)

    # AgvCommand kinds
    gx = 40 + bw + 220
    kinds = [("Translate", "node differs; heading, lift same", "move"),
             ("Rotate", "same node; heading differs", "rot"),
             ("Lift", "same pose; lift differs", "lift"),
             ("Center", "src == dst", "center")]
    cw, ch = 210, 150
    for i, (name, rule, kind) in enumerate(kinds):
        x = gx + (i % 2) * (cw + 20)
        y = (i // 2) * (ch + 20)
        d.rect(x, y, cw, ch, rx=10, fill=T.card, stroke=T.border, sw=1.2)
        d.text(x + 12, y + 18, name, size=12.5, weight=600, fill=T.green)
        d.text(x + 12, y + 36, rule, size=10.5, fill=T.muted)
        cxa, cya = x + 60, y + 95
        if kind == "move":
            _agv(d, cxa + 100, cya, 90, T.faint)
            _agv(d, cxa, cya, 90, T.green)
            d.arrowhead((cxa + 28, cya - 26), (cxa + 76, cya - 26), kind="filled", color=T.green, size=9)
            d.line(cxa + 34, cya - 26, cxa + 76, cya - 26, stroke=T.green, sw=1.8)
            d.text(cxa + 50, cya + 30, "heading 90: forward = -x", size=10.5, family="mono", fill=T.fg2,
                   anchor="middle")
        elif kind == "rot":
            _agv(d, cxa + 50, cya, 90, T.faint)
            _agv(d, cxa + 50, cya, 0, T.green)
        elif kind == "lift":
            _agv(d, cxa + 50, cya, 90, T.green, lifted=True)
            d.text(cxa + 50, cya + 36, "lift: false -> true", size=10.5, family="mono", fill=T.fg2, anchor="middle")
        else:
            _agv(d, cxa + 50, cya, 90, T.green)
            d.circle(cxa + 50, cya, 30, fill="none", stroke=T.green, sw=1.4, dash="3 3")
    code_panel(d, gx, 2 * (ch + 20) + 10, 2 * cw + 20, [
        "AgvCommand { id; src: AgvGoal; dst: AgvGoal }",
        "AgvGoal    { pose: GaragePose; lift: bool }",
        "// scheduler sets src/dst from the motion's delta;",
        "// id is left empty",
    ], title="interfaces/msg/AgvCommand.msg, AgvGoal.msg", size=11.5)
    frame(d, title="ActionNode and AgvCommand, field by field",
          subtitle="One ActionNode is one command to one machine. type says which of the four id/command pairs is "
                   "set; the others keep default values. The example is the end of a retrieve: the car on T17 "
                   "is lowered in bay B21, which then processes the retrieve.",
          badge_key="as-built",
          legend=[("box", T.green, "AGV command"), ("box", T.violet, "bay command"),
                  ("assoc", T.sky, "parents index")])
    return d


def _agv(d: Doc, cx, cy, heading, col, lifted=False):
    """Small top-down AGV: long side along the heading direction (body x)."""
    L, W = 52, 26
    if heading in (90, -90):
        w, h = L, W
    else:
        w, h = W, L
    d.rect(cx - w / 2, cy - h / 2, w, h, rx=5, fill=T.tint(col, 0.15, T.bg), stroke=col, sw=1.6)
    # nose marker toward heading: 90 = -x (west), 0 = +y (north, up on screen)
    if heading == 90:
        d.polygon([(cx - w / 2 + 3, cy), (cx - w / 2 + 11, cy - 6), (cx - w / 2 + 11, cy + 6)], fill=col)
    elif heading == 0:
        d.polygon([(cx, cy - h / 2 + 3), (cx - 6, cy - h / 2 + 11), (cx + 6, cy - h / 2 + 11)], fill=col)
    if lifted:
        d.rect(cx - w / 2 - 6, cy - h / 2 - 6, w + 12, h + 12, rx=7, fill="none", stroke=T.amber, sw=1.6)
