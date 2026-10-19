"""Code-walkthrough figures, part 2: working-state replay, dependency rules, retrieve walkthrough."""
from __future__ import annotations

from components import (EVENT_COLOR, chip, code_panel, connect, event_box, flow, frame, label_pill, note,
                        num_badge)
from facility import Map, NODES, Scene, STALL_L, STALL_W, C_BAY
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
    S0 = d.step("Job 0 (REPARK_TRAY) has already been planned: it added event 0, which moves T15 from P15 to P23. "
                "The request's snapshot ctx->initial_state still shows T15 at P15. Now PlanRetrieveJob starts "
                "job 1.")
    S1 = d.step("(1) PlanRetrieveJob copies ctx->initial_state into a local working_state. At this point the copy "
                "is identical: T15 is still at P15. The dashed arrow previews what replaying event 0 will do.")
    S2 = d.step("(2) ctx->events.Apply(working_state) replays every event planned so far. Event 0 moves T15 "
                "discretely to P23, so working_state now shows the garage as job 0 will leave it.")
    S3 = d.step("(3) The job reads the payload on T17 from working_state, not from the request. Any choice it "
                "makes (free spots, blockers) already accounts for T15 sitting at P23.")
    S4 = d.step("Job 1 adds its own events: first a TrayMove that brings T17 from P17 to bay B21.")
    S5 = d.step("Then a BayTransition B21 -> PROCESS_RETRIEVE, ordered after the tray move. The next job will "
                "replay all three events. Apply() is discrete: no paths, AGVs or timing yet.")
    size = 11.5
    cp = code_panel(d, 0, 0, W, [
        "// Inside Scheduler::PlanRetrieveJob(ScheduleContextSPtr ctx, const GuidMsg& payload_id, size_t job_index) const",
        "// `this` is the Scheduler (const); ctx is the per-call ScheduleContext created in Plan().",
        "volley::DiscreteGarageState working_state = ctx->initial_state;  // (1) copy the request's snapshot",
        "auto [success, message] = ctx->events.Apply(working_state);      // (2) replay every event planned so far",
        "auto payload_opt = working_state.GetPayload(payload_id);         // (3) read the garage as it WILL be",
    ], title="the pattern at the top of every Plan<Type>Job", size=size)
    # current code line highlight
    for k, li in ((S1, 2), (S2, 3), (S3, 4)):
        ly = cp.y0 + 14 + 24 + size / 2 + li * size * 1.5
        with d.only(k):
            d.rect(cp.x0 + 6, ly - 10, W - 12, 20, rx=5, fill=T.tint(T.sky, 0.18, "#0B1222"), stroke=T.sky,
                   sw=1, layer="edges")
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
    # row B: working state (appears at the copy, changes at the replay)
    y2 = y1 + mh + 92
    with d.at(S1):
        mB = Map(d, 0, y2, s, QA_X, QA_Y)
        mB.base(labels=True, zones=False, axes=False)
        mB.tray(17, "T17", payload=True, emphasis=True, chip_pos="bl")
        mB.tray(20, "T20", payload=True, chip_pos="bl")
        _bay_state(d, mB, 21, "B21 READY_TO_RETRIEVE")
        d.text(0, y2 - 18, "working_state", size=13, family="mono", weight=700, fill=T.fg)
    # T15 in working_state: a copy at P15, then Apply(e0) puts it at P23 (straight along P15 -> P19 -> P23;
    # the dashed arrow in step 1 previews the replay, the tray moves when step 2 replays event 0)
    sc = Scene(mB)
    sc.tray("T15", 15, chip_pos="bl", emphasis=True)
    sc.drive(S2, "T15", [15, 19, 23], color=TRAY)
    with d.at(S1):
        sc.draw()
    with d.only(S1):
        d.text(130, y2 - 18, "= copy of ctx->initial_state (identical for now)", size=11.5, fill=T.muted)
    with d.at(S2):
        _ghost(d, mB, 15, "T15 was here")
        d.text(130, y2 - 18, "= initial_state + Apply(e0) — what PlanRetrieveJob reads", size=11.5, fill=T.muted)
    with d.only(S3):
        x17, yy17 = mB.P(17)
        w17, h17 = (STALL_L - 0.5) * s + 12, (STALL_W - 0.32) * s + 12
        d.rect(x17 - w17 / 2, yy17 - h17 / 2, w17, h17, rx=9, fill="none", stroke=T.sky, sw=2, dash="4 3",
               layer="over")
    # arrow between rows
    ax = mw / 2
    with d.at(S1):
        connect(d, [(ax, y1 + mh + 6), (ax, y2 - 34)], kind="flow", color=T.sky, size=10, sw=2)
    with d.only(S1):
        label_pill(d, ax + 12, (y1 + mh + y2 - 30) / 2, "working_state = ctx->initial_state", color=T.sky,
                   anchor="start", size=11.5)
    with d.at(S2):
        label_pill(d, ax + 12, (y1 + mh + y2 - 30) / 2, "ctx->events.Apply(working_state)", color=T.sky,
                   anchor="start", size=11.5)
    # right column: the event DAG as seen at that moment
    rx = mw + 60
    rw = W - rx
    d.text(rx, y1 - 18, "ctx->events while planning job 1", size=13, family="mono", weight=700, fill=T.fg)
    d.rect(rx, y1, rw, y2 + mh - y1, rx=12, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
    e0 = event_box(d, rx + 22, y1 + 40, "TrayMove · job 0", "T15: P15 -> P23", n=0, w=rw - 44)
    d.text(rx + 22, y1 + 30, "already planned by job 0 (REPARK_TRAY)", size=11, fill=T.muted)
    with d.only(S2):
        d.rect(e0.x0 - 4, e0.y0 - 4, e0.w + 8, e0.h + 8, rx=11, fill="none", stroke=T.sky, sw=1.6, layer="over")
    with d.at(S2):
        d.text(rx + 22, e0.y1 + 22, "replayed by Apply() into working_state", size=11, fill=T.sky)
    yy = e0.y1 + 70
    with d.at(S4):
        d.text(rx + 22, yy - 10, "added now by job 1 (RETRIEVE payload on T17)", size=11, fill=T.muted)
        e1 = event_box(d, rx + 22, yy, "TrayMove · job 1", "T17: P17 -> B21", n=1, w=rw - 44, style="new")
    with d.at(S5):
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
    S0 = d.step("Start: job 0 retrieves the payload on T17 into bay B21, which still holds the empty tray T21. "
                "The DAG is empty and last_entity_event has no entries.")
    S1 = d.step("Event 0, BayTransition B21 -> TO_RETRIEVE. Rule A finds no earlier B21 event and rule B finds no "
                "earlier leaf of job 0, so no edge is added. last_entity_event[B21] = 0.")
    S2 = d.step("Event 1 moves T21 out of the bay (destination still open). Rule B: event 0 is a leaf of job 0, so "
                "0 -> 1. last_entity_event[T21] = 1.")
    S3 = d.step("Event 2 moves T17 into B21. Rule B: the only job-0 leaf is now event 1, so 1 -> 2. Rule C: the "
                "destination is a bay, so the move waits for the bay's last event: 0 -> 2.")
    S4 = d.step("Event 3, BayTransition B21 -> PROCESS_RETRIEVE. Rule A chains it to B21's last event (0 -> 3); "
                "rule B adds 2 -> 3. last_entity_event[B21] = 3.")
    S5 = d.step("Job 1 reparks T21 to P24 (event 4). Rule B finds no leaf of job 1, so it adds nothing; rule A "
                "links it to T21's last event: 1 -> 4. That shared tray is the only link between the two jobs.")
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
    LEAF, ENT, BAYR = T.fg2, T.violet, T.violet
    # which rule panel adds an edge at each step
    for k, panels in ((S2, [(c2, LEAF)]), (S3, [(c2, LEAF)]), (S4, [(c1, ENT), (c2, LEAF)]), (S5, [(c1, TRAY)])):
        with d.only(k):
            for p, col in panels:
                d.rect(p.x0 - 3, p.y0 - 3, p.w + 6, p.h + 6, rx=12, fill="none", stroke=col, sw=1.8, layer="over")
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
    B = []
    for i, (k, t) in enumerate(ev):
        with d.at(S1 + i):
            B.append(event_box(d, xs[i], y0, k + " · job 0", t, n=i, w=bw))
    with d.at(S5):
        e4 = event_box(d, xs[1], y0 + 170, "TrayMove · job 1", "T21 -> P24", n=4, w=bw)
    # "current event" ring
    for k, bb in zip((S1, S2, S3, S4, S5), B + [e4]):
        with d.only(k):
            d.rect(bb.x0 - 5, bb.y0 - 5, bb.w + 10, bb.h + 10, rx=12, fill="none", stroke=T.sky, sw=1.6,
                   dash="3 3", layer="over")
    d.text(xs[0] - 4, y0 - 100, "job 0  TYPE_RETRIEVE  (payload on T17, bay B21 was READY_TO_INSERT with empty tray T21)",
           size=11.5, fill=T.muted)
    with d.at(S5):
        d.text(xs[0] - 4, e4.y0 - 14, "job 1  TYPE_REPARK_TRAY T21 -> P24", size=11.5, fill=T.muted)
    # rule B (leaf) edges: e0->e1, e1->e2, e2->e3
    for a, b in ((0, 1), (1, 2), (2, 3)):
        with d.at(S1 + b):
            connect(d, [(B[a].x1, B[a].cy + 8), (B[b].x0, B[b].cy + 8)], kind="flow", color=LEAF, size=8, dash="5 4")
    # rule C: tray move into a bay depends on the bay's last event: e0 -> e2
    yA = y0 - 30
    with d.at(S3):
        connect(d, [(B[0].x0 + 150, B[0].y0), (B[0].x0 + 150, yA), (B[2].x0 + 60, yA), (B[2].x0 + 60, B[2].y0)],
                kind="flow", color=BAYR, size=8, dash="2 4", sw=1.6)
        label_pill(d, (B[0].x0 + 150 + B[2].x0 + 60) / 2, yA, "rule C · dest is a bay", color=BAYR, size=10.5)
    # rule A: entity chain B21: e0 -> e3
    yB = y0 - 66
    with d.at(S4):
        connect(d, [(B[0].x0 + 90, B[0].y0), (B[0].x0 + 90, yB), (B[3].x0 + 100, yB), (B[3].x0 + 100, B[3].y0)],
                kind="flow", color=ENT, size=8, sw=1.6)
        label_pill(d, (B[0].x0 + 90 + B[3].x0 + 100) / 2 + 120, yB, "rule A · entity B21", color=ENT, size=10.5)
    # rule A: entity chain T21: e1 -> e4 (crosses jobs)
    with d.at(S5):
        connect(d, [(B[1].x0 + 50, B[1].y1), (B[1].x0 + 50, e4.y0)], kind="flow", color=TRAY, size=8, sw=1.6)
        label_pill(d, B[1].x0 + 56, (B[1].y1 + e4.y0) / 2, "rule A · entity T21", color=TRAY, size=10.5,
                   anchor="start")
        nb = note(d, xs[2], e4.y0 - 6, xs[3] + bw - xs[2],
             "Rule B never links different jobs. Jobs only become ordered through shared entities (rule A) and, "
             "later, through the occupancy edges added by tray and AGV assignment.", title="Jobs stay independent")
    # bookkeeping state per step
    sy = max(nb.y1, e4.y1) + 26
    state = {S0: ("{ }", "{ }"), S1: ("{ B21: 0 }", "{ 0 }"), S2: ("{ B21: 0, T21: 1 }", "{ 1 }"),
             S3: ("{ B21: 0, T21: 1, T17: 2 }", "{ 2 }"), S4: ("{ B21: 3, T21: 1, T17: 2 }", "{ 3 }"),
             S5: ("{ B21: 3, T21: 4, T17: 2 }", "{ 3, 4 }")}
    d.text(0, sy, "last_entity_event", size=11.5, family="mono", weight=600, fill=T.muted)
    d.text(xs[2], sy, "leaf events", size=11.5, family="mono", weight=600, fill=T.muted)
    for k, (le, lv) in state.items():
        with d.only(k) if k != S5 else d.at(S5):
            d.text(150, sy, le, size=12, family="mono", fill=T.fg)
            d.text(xs[2] + 100, sy, lv, size=12, family="mono", fill=T.fg)
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
    S0 = d.step("The request: one TYPE_RETRIEVE job for the payload on T17. Bay B21 is READY_TO_INSERT and still "
                "holds the empty tray T21; AGV-1 is idle at W26. No events exist yet.")
    S1 = d.step("Job expansion (PlanRetrieveJob) writes the intent as four events: switch B21 to TO_RETRIEVE, move "
                "T21 out of the bay (destination unknown), bring T17 into B21, then PROCESS_RETRIEVE.")
    S2 = d.step("Tray assignment gives T21 a destination: P23. Event 1 becomes concrete; the other job events are "
                "unchanged.")
    S3 = d.step("Tray assignment also finds blocker T15 on T17's critical path and inserts event 4 (T15 -> P19). "
                "T17's move into the bay now waits for it.")
    S4 = d.step("AGV assignment wraps every TrayMove in move -> lift -> carry -> lower. In this order AGV-1 first "
                "drives to P15 and moves the blocker T15 to P19. The dashed arrow previews its first drive.")
    S5 = d.step("Next AGV-1 drives to B21 and moves T21 to P23. An AddDepsAfterAmiga edge makes lifting T21 wait for "
                "the bay's TO_RETRIEVE transition (event 0).")
    S6 = d.step("Finally AGV-1 fetches T17 at P17 and carries it into B21; after the lower, AddDepsAfterAmiga lets "
                "PROCESS_RETRIEVE (event 3) start. The DAG is now ready for Reduce() and the sanity check.")
    P1 = d.step("Playing the plan: AGV-1 drives from W26 to P15 and stops under the blocker T15 (first row of band 3).")
    P2 = d.step("AGV-1 lifts T15, carries it to the free stall P19 and lowers it (event 4). P15 is now free.")
    P3 = d.step("Meanwhile B21 has switched to READY_TO_RETRIEVE (event 0). AGV-1 drives P19 -> W18 -> W22 -> W41 "
                "into the bay, under the empty tray T21.")
    P4 = d.step("AGV-1 lifts T21 (this lift waited for event 0), carries it to P23 and lowers it (event 1).")
    P5 = d.step("AGV-1 drives from P23 to P17, through the stall P15 that T15 has left, and stops under T17.")
    P6 = d.step("AGV-1 lifts T17 with the car, carries it into B21 and lowers it (event 2). PROCESS_RETRIEVE "
                "(event 3) hands the car to the customer. Every tray and the AGV are where the plan leaves them.")
    W = 1060
    s = 24
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    sc = Scene(m)
    sc.tray("T15", 15, chip_pos="bl")
    sc.tray("T17", 17, payload=True, emphasis=True, chip_pos="tr")
    sc.tray("T20", 20, payload=True, chip_pos="bl")
    sc.tray("T21", 21, chip_pos="tr")
    sc.agv("AGV-1", 26, heading=90, label_side="right")
    sc.drive(P1, "AGV-1", [26, 23, 19, 15])
    sc.lift(P2, "AGV-1")
    sc.drive(P2, "AGV-1", [15, 19], color=TRAY)
    sc.lower(P3, "AGV-1")
    sc.drive(P3, "AGV-1", [19, 18, 22, 41, 21])
    sc.lift(P4, "AGV-1")
    sc.drive(P4, "AGV-1", [21, 41, 22, 23], color=TRAY)
    sc.lower(P5, "AGV-1")
    sc.drive(P5, "AGV-1", [23, 22, 18, 13, 15, 17])
    sc.lift(P6, "AGV-1")
    sc.drive(P6, "AGV-1", [17, 15, 13, 18, 22, 41, 21], color=TRAY)
    sc.draw()
    with d.at(S0, P2):
        _bay_state(d, m, 21, "B21 READY_TO_INSERT")
    with d.at(P3, P5):
        _bay_state(d, m, 21, "B21 READY_TO_RETRIEVE")
    with d.at(P6):
        _bay_state(d, m, 21, "B21 PROCESS_RETRIEVE")
    # planned tray moves (illustrative graph walks), drawn when the pass that fixes them runs; the playback
    # steps replace them with the moving AGV
    with d.at(S2, S6):
        m.route([21, 41, 22, 23], TRAY, sw=3, offset=(0, -7), num=1, num_at=0, dash="7 5")
    with d.at(S3, S6):
        m.route([15, 19], TRAY, sw=3, offset=(-14, 0), num=4, num_at=0, dash="7 5")
    with d.at(S1, S6):
        m.route([17, 15, 13, 18, 22, 41, 21], TRAY, sw=3.5, offset=(0, 7), num=2, num_at=0)
    mb = m.box
    # scenario panel
    px = mb.x1 + 30
    pw = W - px
    d.text(px, 10, "Request", size=13, weight=600, fill=T.fg)
    facts = [("job 0", "TYPE_RETRIEVE, payload on T17"), ("bay", "B21 is READY_TO_INSERT, empty T21 inside"),
             ("trays", "T15 empty at P15, T20 loaded at P20"), ("AGV", "AGV-1 idle at W26")]
    yy = 34
    for k, v in facts:
        d.text(px, yy, k, size=11.5, family="mono", fill=T.muted)
        for j, ln in enumerate(wrap(v, pw - 62, 12)):
            d.text(px + 56, yy + j * 17, ln, size=12, fill=T.fg2)
        yy += 17 * len(wrap(v, pw - 62, 12)) + 8
    with d.only(S0):
        d.rect(px - 10, -6, pw + 16, yy - 4, rx=10, fill="none", stroke=T.sky, sw=1.6, layer="over")
    note(d, px, yy + 6, pw,
         "Destinations P23 and P19 and the AGV order are one plausible outcome of the searches, chosen to "
         "illustrate the mechanics. The real choices come from OpenSpaceSearch and BottleneckAssignment.",
         title="Illustrative choices")
    # bands
    y = mb.y1 + 60

    def band(title, sub, height, col, first, last):
        nonlocal y
        with d.at(first):
            d.rect(0, y, W, height, rx=12, fill=T.tint(col, 0.04, T.bg), stroke=T.tint(col, 0.4, T.bg), sw=1,
                   layer="bg")
            d.text(16, y + 20, title, size=12.5, family="mono", weight=700, fill=col)
            d.text(16 + text_width(title, 12.5, "mono", 700) + 14, y + 20, sub, size=11.5, fill=T.muted)
        with d.at(first, last):
            d.rect(-3, y - 3, W + 6, height + 6, rx=14, fill="none", stroke=T.sky, sw=1.6, layer="over")
        top = y + 40
        y += height + 18
        return top

    # band 1: after job expansion
    t1 = band("1 · after PlanRetrieveJob()", "T21 has no destination yet; transitive edges omitted (see the edge-rules figure)", 112,
              T.fg2, S1, S1)
    with d.at(S1):
        _chain(d, 16, t1 + 6, [("BayTransition", "B21: TO_RETRIEVE", 0, "solid"),
                               ("TrayMove", "T21 -> ?", 1, "solid"), ("TrayMove", "T17 -> B21", 2, "solid"),
                               ("BayTransition", "B21: PROCESS_RETRIEVE", 3, "solid")], gap=40)
    # band 2: after tray assignment
    t2 = band("2 · after DoTrayAssignments()", "T21 gets a destination; blocker T15 on T17's critical path is moved first",
              120, TRAY, S2, S3)
    with d.at(S2):
        b2 = _chain(d, 16, t2 + 10, [("BayTransition", "B21: TO_RETRIEVE", 0, "faded"),
                                      ("TrayMove", "T21 -> P23", 1, "new"), ("TrayMove", "T17 -> B21", 2, "faded"),
                                      ("BayTransition", "B21: PROCESS_RETRIEVE", 3, "faded")], gap=40)
    with d.at(S3):
        e4 = event_box(d, b2[3].x1 + 40, t2 + 10, "TrayMove · blocker", "T15 -> P19", n=4, style="new", size=11.5)
        connect(d, [(e4.cx, e4.y1), (e4.cx, e4.y1 + 14), (b2[2].cx + 30, e4.y1 + 14), (b2[2].cx + 30, b2[2].y1)],
                kind="flow", color=TRAY, size=8, sw=1.6)
    # band 3: after AGV assignment
    t3 = band("3 · after DoAgvAssignments()", "AGV-1 gets move -> lift -> carry -> lower around every TrayMove (one valid order)",
              268, AGV, S4, S6)
    bw3 = 138
    rows = [
        [("AgvMove", "AGV-1 -> P15", None, "new"), ("AgvMove", "AGV-1 lift", None, "new"),
         ("TrayMove", "T15 -> P19", 4, "solid"), ("AgvMove", "AGV-1 lower", None, "new")],
        [("AgvMove", "AGV-1 -> B21", None, "new"), ("AgvMove", "AGV-1 lift", None, "new"),
         ("TrayMove", "T21 -> P23", 1, "solid"), ("AgvMove", "AGV-1 lower", None, "new")],
        [("AgvMove", "AGV-1 -> P17", None, "new"), ("AgvMove", "AGV-1 lift", None, "new"),
         ("TrayMove", "T17 -> B21", 2, "solid"), ("AgvMove", "AGV-1 lower", None, "new")],
    ]
    left = 210
    rb = []
    for i, r in enumerate(rows):
        with d.at(S4 + i):
            rb.append(_chain(d, left, t3 + 6 + i * 74, r, bw=bw3, gap=22))
    for k, i, j0, j1 in ((P1, 0, 0, 0), (P2, 0, 1, 3), (P3, 1, 0, 0), (P4, 1, 1, 3), (P5, 2, 0, 0), (P6, 2, 1, 3)):
        with d.only(k):
            bx0, bx1 = rb[i][j0].x0 - 6, rb[i][j1].x1 + 6
            d.rect(bx0, rb[i][j0].y0 - 6, bx1 - bx0, rb[i][j0].h + 12, rx=10, fill="none", stroke=T.sky, sw=2,
                   layer="over")
    with d.at(S4):
        e0b = event_box(d, 16, t3 + 80, "BayTransition", "B21: TO_RETRIEVE", n=0, w=170, size=11.5)
    with d.at(S6):
        e3b = event_box(d, rb[2][-1].x1 + 30, t3 + 6 + 2 * 74, "BayTransition", "PROCESS_RETRIEVE", n=3, size=11.5)
        connect(d, [(rb[2][-1].x1, rb[2][-1].cy), (e3b.x0, e3b.cy)], kind="flow", color=BAYC, size=8, sw=1.5,
                dash="2 4")
    # chain edges between rows (same AGV)
    for k, (a, b) in ((S5, (rb[0][-1], rb[1][0])), (S6, (rb[1][-1], rb[2][0]))):
        with d.at(k):
            connect(d, [(a.cx, a.y1), (a.cx, a.y1 + 11), (b.cx, a.y1 + 11), (b.cx, b.y0)], kind="flow", color=AGV,
                    size=8, sw=1.5)
    # bay transition must precede lifting T21 inside the bay (AddDepsAfterAmiga)
    with d.at(S5):
        connect(d, [(e0b.x1, e0b.cy), (rb[1][1].x0 - 8, e0b.cy), (rb[1][1].x0 - 8, rb[1][1].cy - 30),
                    (rb[1][1].cx, rb[1][1].cy - 30), (rb[1][1].cx, rb[1][1].y0)], kind="flow", color=BAYC, size=8,
                sw=1.5, dash="2 4")
    frame(d, title="One RETRIEVE job, stage by stage",
          subtitle="The map shows the intended tray moves (numbers = event ids). Below, the same event DAG grows in "
                   "three passes: job expansion creates intent, tray assignment makes it concrete and unblocks the "
                   "path, AGV assignment adds who does it. The last six steps play the plan on the map.",
          badge_key="yaml+hyp",
          legend=[("box", TRAY, "TrayMove"), ("box", AGV, "AgvMove"), ("box", BAYC, "BayTransition"),
                  ("ring", T.muted, "added in this pass"), ("dasharrow", BAYC, "AddDepsAfterAmiga edge")])
    return d
