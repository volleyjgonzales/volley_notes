"""Code-walkthrough figures, part 2: working-state replay, dependency rules, retrieve walkthrough."""
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


def _bay_state(d: Doc, m: Map, nid: int, text: str, color=C_BAY):
    x, y = m.P(nid)
    label_pill(d, x, y - (STALL_W + 0.9) * m.s / 2 - 12, text, color=color, bg=T.bg_deep, border=color, size=10.5)


def _ghost(d: Doc, m: Map, nid: int, text: str, color=TRAY):
    x, y = m.P(nid)
    w, h = (STALL_L - 0.5) * m.s, (STALL_W - 0.32) * m.s
    d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill="none", stroke=color, sw=1.3, dash="5 4", layer="main")
    d.text(x, y + 1, text, size=10.5, family="mono", fill=color, anchor="middle", halo=T.bg_deep, halo_w=3)


# --------------------------------------------------------------------------------------
# 23 — working_state = initial_state + replay(events)
# --------------------------------------------------------------------------------------

@figure("23_working_state_replay", "working_state: replaying the DAG", DOC1)
def working_state():
    d = Doc("23_working_state_replay", "How each job sees the garage: working_state",
            "Every Plan<Type>Job copies ctx->initial_state and replays all events planned so far, so a later job "
            "sees the garage as earlier jobs will leave it.")
    W = 1040
    cp = code_panel(d, 0, 0, W, [
        "// Inside Scheduler::PlanRetrieveJob(ScheduleContextSPtr ctx, const GuidMsg& payload_id, size_t job_index) const",
        "// `this` is the Scheduler (const); ctx is the per-call ScheduleContext created in Plan().",
        "volley::DiscreteGarageState working_state = ctx->initial_state;  // (1) copy the request's snapshot",
        "auto [success, message] = ctx->events.Apply(working_state);      // (2) replay every event planned so far",
        "auto payload_opt = working_state.GetPayload(payload_id);         // (3) read the garage as it WILL be",
    ], title="the pattern at the top of every Plan<Type>Job", size=11.5)
    s = 21
    mw = (QA_X[1] - QA_X[0]) * s
    mh = (QA_Y[1] - QA_Y[0]) * s
    y1 = cp.y1 + 70
    # row A: initial state
    mA = Map(d, 0, y1, s, QA_X, QA_Y)
    mA.base(labels=True, zones=False, axes=False)
    mA.tray(15, "T15", chip_pos="bl")
    mA.tray(17, "T17", payload=True, emphasis=True, chip_pos="bl")
    mA.tray(20, "T20", payload=True, chip_pos="bl")
    _bay_state(d, mA, 21, "B21 READY_TO_RETRIEVE")
    d.text(0, y1 - 18, "ctx->initial_state", size=13, family="mono", weight=700, fill=T.fg)
    d.text(170, y1 - 18, "copied from PlanRequest.base_state; never modified", size=11.5, fill=T.muted)
    # row B: working state after replay
    y2 = y1 + mh + 92
    mB = Map(d, 0, y2, s, QA_X, QA_Y)
    mB.base(labels=True, zones=False, axes=False)
    _ghost(d, mB, 15, "T15 was here")
    mB.tray(23, "T15", chip_pos="bl", emphasis=True)
    mB.tray(17, "T17", payload=True, emphasis=True, chip_pos="bl")
    mB.tray(20, "T20", payload=True, chip_pos="bl")
    _bay_state(d, mB, 21, "B21 READY_TO_RETRIEVE")
    d.text(0, y2 - 18, "working_state", size=13, family="mono", weight=700, fill=T.fg)
    d.text(130, y2 - 18, "= initial_state + Apply(e0) — what PlanRetrieveJob reads", size=11.5, fill=T.muted)
    # arrow between rows
    ax = mw / 2
    connect(d, [(ax, y1 + mh + 6), (ax, y2 - 34)], kind="flow", color=T.sky, size=10, sw=2)
    label_pill(d, ax + 12, (y1 + mh + y2 - 30) / 2, "ctx->events.Apply(working_state)", color=T.sky, anchor="start",
               size=11.5)
    # right column: the event DAG as seen at that moment
    rx = mw + 60
    rw = W - rx
    d.text(rx, y1 - 18, "ctx->events while planning job 1", size=13, family="mono", weight=700, fill=T.fg)
    d.rect(rx, y1, rw, y2 + mh - y1, rx=12, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
    e0 = event_box(d, rx + 22, y1 + 40, "TrayMove · job 0", "T15: P15 -> P23", n=0, w=rw - 44)
    d.text(rx + 22, y1 + 30, "already planned by job 0 (REPARK_TRAY)", size=11, fill=T.muted)
    d.text(rx + 22, e0.y1 + 22, "replayed by Apply() into working_state", size=11, fill=T.sky)
    yy = e0.y1 + 70
    d.text(rx + 22, yy - 10, "added now by job 1 (RETRIEVE payload on T17)", size=11, fill=T.muted)
    e1 = event_box(d, rx + 22, yy, "TrayMove · job 1", "T17: P17 -> B21", n=1, w=rw - 44, style="new")
    e2 = event_box(d, rx + 22, e1.y1 + 26, "BayTransition · job 1", "B21: PROCESS_RETRIEVE", n=2, w=rw - 44,
                   style="new")
    flow(d, e1, e2, side="v")
    note(d, rx + 22, e2.y1 + 30, rw - 44,
         "Apply() moves entities discretely: the tray simply appears at its destination. Paths, AGVs and timing "
         "do not exist yet; they are added by the later stages.", title="Discrete, not physical")
    frame(d, title="How each job sees the garage: working_state",
          subtitle="Every Plan<Type>Job starts the same way: copy ctx->initial_state, then replay the whole event DAG "
                   "built so far. Job 1 therefore plans against the garage that job 0 will leave behind, not the "
                   "garage in the request.",
          badge_key="yaml+hyp",
          legend=[("box", TRAY, "TrayMove"), ("box", BAYC, "BayTransition"), ("dashbox", TRAY, "position before replay"),
                  ("box", T.pink, "payload"), ("ring", T.muted, "new event")])
    return d


# --------------------------------------------------------------------------------------
# 25 — how edges are added during job expansion
# --------------------------------------------------------------------------------------

@figure("25_dependency_rules", "How job expansion adds DAG edges", DOC1)
def dependency_rules():
    d = Doc("25_dependency_rules", "Where the edges come from during job expansion",
            "UpdateLastEntityEvent chains events that touch the same entity; UpdateLeafDependencies orders events "
            "within one job; tray moves into a bay depend on that bay's last event.")
    W = 1040
    hw = (W - 24) / 2
    c1 = code_panel(d, 0, 0, hw, [
        "// ScheduleContext::UpdateLastEntityEvent",
        "void UpdateLastEntityEvent(const GarageEntityIdMsg& id,",
        "                           ScheduleEventSPtr new_event) {",
        "  if(last_entity_event.find(id) != last_entity_event.end())",
        "    events.AddDependency(last_entity_event.at(id), new_event);",
        "  // id = one AGV, tray, bay or VECS",
        "  last_entity_event[id] = new_event;",
        "}",
    ], title="rule A · per-entity chain", size=11.5)
    c2 = code_panel(d, hw + 24, 0, hw, [
        "// ScheduleContext::UpdateLeafDependencies",
        "void UpdateLeafDependencies(const ScheduleEventSPtr& child,",
        "                            size_t job_index) {",
        "  for(const auto& leaf : events.GetLeafEvents()) {",
        "    if(leaf == child) continue;",
        "    if(leaf->GetJobIndex() == job_index)   // same job only",
        "      events.AddDependency(leaf, child);   // leaf = no out-edges",
        "  }",
        "}",
    ], title="rule B · in-job ordering", size=11.5)
    # DAG
    y0 = max(c1.y1, c2.y1) + 140
    bw, gx = 210, 52
    xs = [i * (bw + gx) for i in range(4)]
    ev = [
        ("BayTransition", "B21: TO_RETRIEVE"),
        ("TrayMove", "T21 (in bay) -> ?"),
        ("TrayMove", "T17 -> B21"),
        ("BayTransition", "B21: PROCESS_RETRIEVE"),
    ]
    B = [event_box(d, xs[i], y0, k + " · job 0", t, n=i, w=bw) for i, (k, t) in enumerate(ev)]
    e4 = event_box(d, xs[1], y0 + 170, "TrayMove · job 1", "T21 -> P24", n=4, w=bw)
    d.text(xs[0] - 4, y0 - 100, "job 0  TYPE_RETRIEVE  (payload on T17, bay B21 was READY_TO_INSERT with empty tray T21)",
           size=11.5, fill=T.muted)
    d.text(xs[0] - 4, e4.y0 - 14, "job 1  TYPE_REPARK_TRAY T21 -> P24", size=11.5, fill=T.muted)
    LEAF, ENT, BAYR = T.fg2, T.violet, T.violet
    # rule B (leaf) edges: e0->e1, e1->e2, e2->e3
    for a, b in ((0, 1), (1, 2), (2, 3)):
        connect(d, [(B[a].x1, B[a].cy + 8), (B[b].x0, B[b].cy + 8)], kind="flow", color=LEAF, size=8, dash="5 4")
    # rule C: tray move into a bay depends on the bay's last event: e0 -> e2
    yA = y0 - 30
    connect(d, [(B[0].x0 + 150, B[0].y0), (B[0].x0 + 150, yA), (B[2].x0 + 60, yA), (B[2].x0 + 60, B[2].y0)],
            kind="flow", color=BAYR, size=8, dash="2 4", sw=1.6)
    label_pill(d, (B[0].x0 + 150 + B[2].x0 + 60) / 2, yA, "rule C · dest is a bay", color=BAYR, size=10.5)
    # rule A: entity chain B21: e0 -> e3
    yB = y0 - 66
    connect(d, [(B[0].x0 + 90, B[0].y0), (B[0].x0 + 90, yB), (B[3].x0 + 100, yB), (B[3].x0 + 100, B[3].y0)],
            kind="flow", color=ENT, size=8, sw=1.6)
    label_pill(d, (B[0].x0 + 90 + B[3].x0 + 100) / 2 + 120, yB, "rule A · entity B21", color=ENT, size=10.5)
    # rule A: entity chain T21: e1 -> e4 (crosses jobs)
    connect(d, [(B[1].x0 + 50, B[1].y1), (B[1].x0 + 50, e4.y0)], kind="flow", color=TRAY, size=8, sw=1.6)
    label_pill(d, B[1].x0 + 56, (B[1].y1 + e4.y0) / 2, "rule A · entity T21", color=TRAY, size=10.5, anchor="start")
    note(d, xs[2], e4.y0 - 6, xs[3] + bw - xs[2],
         "Rule B never links different jobs. Jobs only become ordered through shared entities (rule A) and, "
         "later, through the occupancy edges added by tray and AGV assignment.", title="Jobs stay independent")
    frame(d, title="Where the edges come from during job expansion",
          subtitle="Each Plan<Type>Job adds an event, then calls one or both ScheduleContext helpers. Rule C lives in "
                   "PlanReparkTrayJob. The letters A, B, C are this guide's names, not the code's. The result is a "
                   "partial order, not a sequence.",
          badge_key="as-built",
          legend=[("arrow", ENT, "rule A: same entity (bay)"), ("arrow", TRAY, "rule A: same entity (tray)"),
                  ("dasharrow", LEAF, "rule B: leaf of the same job"), ("dasharrow", BAYR, "rule C: into a bay")])
    return d


# --------------------------------------------------------------------------------------
# 26 — one RETRIEVE job through all three stages (flagship walkthrough)
# --------------------------------------------------------------------------------------

def _chain(d, x, y, items, *, bw=None, gap=26, h=50):
    boxes = []
    for kind, txt, n, st in items:
        b = event_box(d, x, y, kind, txt, n=n, style=st, w=bw, h=h, size=11.5)
        if boxes:
            connect(d, [(boxes[-1].x1, boxes[-1].cy), (b.x0, b.cy)], kind="flow", color=T.fg2, size=8)
        boxes.append(b)
        x = b.x1 + gap
    return boxes


@figure("26_retrieve_walkthrough", "One RETRIEVE job through every stage", DOC1)
def retrieve_walkthrough():
    d = Doc("26_retrieve_walkthrough", "One RETRIEVE job, stage by stage",
            "Pecos example: retrieving the payload on T17 to bay B21. The map numbers match the events, and the "
            "three bands show the event DAG after expansion, tray assignment and AGV assignment.")
    W = 1060
    s = 24
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    m.tray(15, "T15", chip_pos="bl")
    m.tray(17, "T17", payload=True, emphasis=True, chip_pos="bl")
    m.tray(20, "T20", payload=True, chip_pos="bl")
    m.tray(21, "T21", chip_pos="tr")
    m.agv(26, "AGV A", heading=90, label_side="above")
    _bay_state(d, m, 21, "B21 READY_TO_INSERT")
    # routes (illustrative graph walks)
    m.route([21, 41, 22, 23], TRAY, sw=3, offset=(0, -7), num=1, num_at=0, dash="7 5")
    m.route([15, 19], TRAY, sw=3, offset=(-14, 0), num=4, num_at=0, dash="7 5")
    m.route([17, 15, 13, 18, 22, 41, 21], TRAY, sw=3.5, offset=(0, 7), num=2, num_at=0)
    mb = m.box
    # scenario panel
    px = mb.x1 + 30
    pw = W - px
    d.text(px, 10, "Request", size=13, weight=600, fill=T.fg)
    facts = [("job 0", "TYPE_RETRIEVE, payload on T17"), ("bay", "B21 is READY_TO_INSERT, empty T21 inside"),
             ("trays", "T15 empty at P15, T20 loaded at P20"), ("AGV", "A idle at W26")]
    yy = 34
    for k, v in facts:
        d.text(px, yy, k, size=11.5, family="mono", fill=T.muted)
        for j, ln in enumerate(wrap(v, pw - 62, 12)):
            d.text(px + 56, yy + j * 17, ln, size=12, fill=T.fg2)
        yy += 17 * len(wrap(v, pw - 62, 12)) + 8
    note(d, px, yy + 6, pw,
         "Destinations P23 and P19 and the AGV order are one plausible outcome of the searches, chosen to "
         "illustrate the mechanics. The real choices come from OpenSpaceSearch and BottleneckAssignment.",
         title="Illustrative choices")
    # bands
    y = mb.y1 + 60
    bands = []

    def band(title, sub, height, col):
        nonlocal y
        d.rect(0, y, W, height, rx=12, fill=T.tint(col, 0.04, T.bg), stroke=T.tint(col, 0.4, T.bg), sw=1,
               layer="bg")
        d.text(16, y + 20, title, size=12.5, family="mono", weight=700, fill=col)
        d.text(16 + text_width(title, 12.5, "mono", 700) + 14, y + 20, sub, size=11.5, fill=T.muted)
        top = y + 40
        y += height + 18
        return top

    # band 1: after job expansion
    t1 = band("1 · after PlanRetrieveJob()", "T21 has no destination yet; transitive edges omitted (see the edge-rules figure)", 112,
              T.fg2)
    b1 = _chain(d, 16, t1 + 6, [("BayTransition", "B21: TO_RETRIEVE", 0, "solid"),
                                 ("TrayMove", "T21 -> ?", 1, "solid"), ("TrayMove", "T17 -> B21", 2, "solid"),
                                 ("BayTransition", "B21: PROCESS_RETRIEVE", 3, "solid")], gap=40)
    # band 2: after tray assignment
    t2 = band("2 · after DoTrayAssignments()", "T21 gets a destination; blocker T15 on T17's critical path is moved first",
              120, TRAY)
    b2 = _chain(d, 16, t2 + 10, [("BayTransition", "B21: TO_RETRIEVE", 0, "faded"),
                                  ("TrayMove", "T21 -> P23", 1, "new"), ("TrayMove", "T17 -> B21", 2, "faded"),
                                  ("BayTransition", "B21: PROCESS_RETRIEVE", 3, "faded")], gap=40)
    e4 = event_box(d, b2[3].x1 + 40, t2 + 10, "TrayMove · blocker", "T15 -> P19", n=4, style="new", size=11.5)
    connect(d, [(e4.cx, e4.y1), (e4.cx, e4.y1 + 14), (b2[2].cx + 30, e4.y1 + 14), (b2[2].cx + 30, b2[2].y1)],
            kind="flow", color=TRAY, size=8, sw=1.6)
    # band 3: after AGV assignment
    t3 = band("3 · after DoAgvAssignments()", "AGV A gets move -> lift -> carry -> lower around every TrayMove (one valid order)",
              268, AGV)
    bw3 = 138
    rows = [
        [("AgvMove", "A -> P15", None, "new"), ("AgvMove", "lift", None, "new"), ("TrayMove", "T15 -> P19", 4, "solid"),
         ("AgvMove", "lower", None, "new")],
        [("AgvMove", "A -> B21", None, "new"), ("AgvMove", "lift", None, "new"), ("TrayMove", "T21 -> P23", 1, "solid"),
         ("AgvMove", "lower", None, "new")],
        [("AgvMove", "A -> P17", None, "new"), ("AgvMove", "lift", None, "new"), ("TrayMove", "T17 -> B21", 2, "solid"),
         ("AgvMove", "lower", None, "new")],
    ]
    left = 210
    rb = []
    for i, r in enumerate(rows):
        rb.append(_chain(d, left, t3 + 6 + i * 74, r, bw=bw3, gap=22))
    e0b = event_box(d, 16, t3 + 80, "BayTransition", "B21: TO_RETRIEVE", n=0, w=170, size=11.5)
    e3b = event_box(d, rb[2][-1].x1 + 30, t3 + 6 + 2 * 74, "BayTransition", "PROCESS_RETRIEVE", n=3, size=11.5)
    connect(d, [(rb[2][-1].x1, rb[2][-1].cy), (e3b.x0, e3b.cy)], kind="flow", color=BAYC, size=8, sw=1.5, dash="2 4")
    # chain edges between rows (same AGV)
    for a, b in ((rb[0][-1], rb[1][0]), (rb[1][-1], rb[2][0])):
        connect(d, [(a.cx, a.y1), (a.cx, a.y1 + 11), (b.cx, a.y1 + 11), (b.cx, b.y0)], kind="flow", color=AGV,
                size=8, sw=1.5)
    # bay transition must precede lifting T21 inside the bay (AddDepsAfterAmiga)
    connect(d, [(e0b.x1, e0b.cy), (rb[1][1].x0 - 8, e0b.cy), (rb[1][1].x0 - 8, rb[1][1].cy - 30),
                (rb[1][1].cx, rb[1][1].cy - 30), (rb[1][1].cx, rb[1][1].y0)], kind="flow", color=BAYC, size=8,
            sw=1.5, dash="2 4")
    frame(d, title="One RETRIEVE job, stage by stage",
          subtitle="The map shows the intended tray moves (numbers = event ids). Below, the same event DAG grows in "
                   "three passes: job expansion creates intent, tray assignment makes it concrete and unblocks the "
                   "path, AGV assignment adds who does it.",
          badge_key="yaml+hyp",
          legend=[("box", TRAY, "TrayMove"), ("box", AGV, "AgvMove"), ("box", BAYC, "BayTransition"),
                  ("ring", T.muted, "added in this pass"), ("dasharrow", BAYC, "AddDepsAfterAmiga edge")])
    return d
