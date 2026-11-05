"""fig_reserve: base-schedule reservation and the Apply call chain (116, 117).

Doc 01-background.html.

116 follows Scheduler::Plan (scheduler.cpp): the base_schedule loop (SetAgvDisabled, SetNodeDisabled on
src and dst, SetBayDisabled, SetVecsDisabled), GetDisabledEntitiesFilters (static_graph_filtering.cpp), the
`agv.disabled` check in PlanAgvMoveJob, the `disabledness_filters[...]` check in PlanReparkTrayJob and the skip of
disabled AGVs in DoAgvAssignments / Chugg::GetMovableAgvs. Occupancy is hypothetical; geometry is the Pecos
YAML. The keep-out overlay is drawn from the rule "a vertex or edge touching a reserved node's volume is
off" and is illustrative: the real sets come from CollisionTable::Query.

117 follows ScheduleEventDag::Apply (event_dag.cpp), AgvMove::Apply (schedule_events.cpp) and
DiscreteGarageState::OnEvent(const AgvPoseChangedMsg&) (common_ros discrete_garage_state.cpp).
"""
from __future__ import annotations

from components import chip, code_panel, frame, label_pill
from facility import EDGES, NODES, STALL_L, STALL_W, Map, Scene
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import S, T

DOC = "01-background.html"
QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)
FREE = T.green
BUSY = T.violet       # entities owned by the running base schedule
KEEP = T.red          # keep-out (reserved) areas
NEW = T.sky

RESERVED_NODES = [15, 19, 23, 21]
BLOCKED_EDGES = [(a, b) for a, b in EDGES if a in RESERVED_NODES or b in RESERVED_NODES]
assert (15, 19) in BLOCKED_EDGES and (19, 23) in BLOCKED_EDGES and (21, 41) in BLOCKED_EDGES
assert (24, 27) not in BLOCKED_EDGES and (20, 24) not in BLOCKED_EDGES and (26, 27) not in BLOCKED_EDGES


def _hl_code(d: Doc, panel, first, last=None, *, size=11.5, col=T.sky):
    last = first if last is None else last
    lh = size * 1.5
    y0 = panel.y0 + 14 + 24 + size / 2 + first * lh - lh / 2
    h = (last - first + 1) * lh
    d.rect(panel.x0 + 6, y0, panel.w - 12, h, rx=4, fill=T.tint(col, 0.16, "#0B1222"),
           stroke=T.tint(col, 0.6, T.bg), sw=1, layer="main")


def _card(d: Doc, x, y, w, title, rows, *, accent, k, rh=22):
    """Titled card whose rows are (text, color, step) and appear at their step."""
    h = 34 + rh * len(rows) + 6
    with d.at(k):
        d.rect(x, y, w, h, rx=9, fill=T.card, stroke=T.tint(accent, 0.7, T.bg), sw=1.3)
        d.text(x + 12, y + 17, title, size=12, weight=600, fill=accent)
    yy = y + 40
    for text, col, kk in rows:
        with d.at(kk):
            d.text(x + 14, yy, text, size=11.5, family="mono", fill=col)
        yy += rh
    return BBox(x, y, x + w, y + h)


@figure("116_base_schedule_reservation", "Reserving what the running schedule uses (animated)", DOC)
def base_schedule_reservation():
    d = Doc("116_base_schedule_reservation", "Reserving what the running schedule uses",
            "Animated: Plan() marks every AGV, node, bay and VECS used by base_schedule as disabled, builds the "
            "keep-out filters once, and every later stage avoids those assets; both schedules then run side by side.")
    S0 = d.step("base_state, the snapshot Dispatch sends: AGV-2 is lifted under T15 at P15, AGV-1 is idle at W26, "
                "AGV-3 is idle at W13, empty tray T24 is at P24 and loaded tray T17 at P17.")
    S1 = d.step("base_schedule: every action of Dispatch's schedule that is not completed yet. a1 moves AGV-2 "
                "P15 -> P19, a2 moves it P19 -> P23 (carrying T15), a3 lowers T15 at P23, b1 sends B21 "
                "TRANSITION_TO_RETRIEVE. The scheduler must assume all of them complete.")
    S2 = d.step("The loop in Plan() reserves what they use: AGV-2 is disabled; P15, P19 and P23 (every source and "
                "destination) and B21 go into disabled_nodes_; bay B21 is disabled. The snapshot is not advanced: "
                "in initial_state AGV-2 is still at P15.")
    S3 = d.step("GetDisabledEntitiesFilters builds the keep-out map once. Per footprint, a vertex or edge is off if "
                "it collides with a reserved entity, an entity standing on a reserved node, or a reserved node's "
                "largest window at any heading. Free AGVs and trays are ignored here: they may move.")
    S4 = d.step("Pending job j0, MOVE_AGV AGV-2 -> C14: PlanAgvMoveJob reads agvs_[2].disabled and fails the job with "
                "\"Tried to move a disabled agv 2\". The message cannot tell a busy AGV from one taken out of service.")
    S5 = d.step("Pending job j1, REPARK_TRAY T24 -> P20: P20 is on in disabledness_filters[TRAY], so a TrayMove "
                "T24 -> P20 is added to the event DAG.")
    S6 = d.step("DoAgvAssignments offers only AGV-1 and AGV-3; AGV-2 is skipped. AGV-1 gets the move. CHUGG's "
                "GetMovableAgvs skips AGV-2 too: it stays a static obstacle at P15 and the reserved nodes stay "
                "blocked for the whole new plan.")
    P1 = d.step("Execution. Dispatch keeps running a1 and a2 (AGV-2 carries T15 to P23) while the new plan starts: "
                "AGV-1 drives W26 -> W27 -> P24 and lifts T24. The two schedules share no AGV, bay or reserved node, "
                "so no edge joins them.")
    P2 = d.step("AGV-1 carries T24 to P20 and lowers it. AGV-2 was unavailable to the new plan from start to end, "
                "even though its last base action ended early.")
    s = 24
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    mb = m.box
    # reserved volumes (largest window at the node), from S2 on
    for nid in RESERVED_NODES:
        x, y = m.P(nid)
        w = STALL_L * s + 4
        h = (STALL_W + (0.9 if NODES[nid].type == "Bay" else 0)) * s + 4
        with d.at(S2):
            d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill="none", stroke=KEEP, sw=2, dash="6 4", layer="over")
        with d.at(S3, S6):
            d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill=KEEP, opacity=0.14, layer="over")
    # blocked edges and vertices of the AGV keep-out filter
    with d.at(S3, S6):
        for a, b in BLOCKED_EDGES:
            (x0, y0), (x1, y1) = m.P(a), m.P(b)
            d.line(x0, y0, x1, y1, stroke=KEEP, sw=2.4, dash="3 4", layer="over")
        for nid in RESERVED_NODES:
            x, y = m.P(nid)
            d.line(x - 6, y - 6, x + 6, y + 6, stroke=KEEP, sw=2.4, layer="top")
            d.line(x - 6, y + 6, x + 6, y - 6, stroke=KEEP, sw=2.4, layer="top")
    # base schedule routes (dashed, owned by Dispatch)
    with d.at(S1, S6):
        m.route([15, 19], BUSY, sw=3, dash="7 5", offset=(-9, 0), num=1, num_at=0)
        m.route([19, 23], BUSY, sw=3, dash="7 5", offset=(9, 0), num=2, num_at=0)
        bx, by = m.P(21)
        chip(d, bx + 26, by + 32, "b1 TRANSITION_TO_RETRIEVE", BUSY, size=10.5)
    # job markers
    cx, cy = m.P(14)
    with d.only(S4):
        ax, ay = m.P(15)
        d.circle(ax, ay, 30, fill="none", stroke=KEEP, sw=2.4, layer="top")
        d.text(cx + 12, cy + 21, "j0 refused", anchor="middle", size=11, family="mono", weight=700, fill=KEEP, halo=T.bg_deep,
               halo_w=3, layer="top")
    with d.at(S5, S6):
        m.route([24, 20], NEW, sw=3, dash="6 4", offset=(8, 0))
        px, py = m.P(20)
        d.circle(px, py, 13, fill="none", stroke=NEW, sw=2.2, layer="top")
    # mobile entities
    sc = Scene(m)
    sc.tray("T15", 15, chip_pos="bl")
    sc.tray("T17", 17, payload=True, chip_pos="bl")
    sc.tray("T24", 24, chip_pos="tr")
    sc.agv("AGV-2", 15, heading=90, color=BUSY, label_side="right")
    sc.agv("AGV-1", 26, heading=90, label_side="above")
    sc.agv("AGV-3", 13, heading=90, label_side="below")
    sc.lift(S0, "AGV-2")
    sc.drive(P1, "AGV-2", [15, 19, 23], preview=False, color=BUSY)
    sc.drive(P1, "AGV-1", [26, 27, 24])
    sc.lift(P1, "AGV-1")
    sc.drive(P2, "AGV-1", [24, 20])
    sc.lower(P2, "AGV-1")
    sc.draw()

    # right-hand cards
    tx = mb.x1 + 34
    tw = 470
    y = mb.y0
    c1 = _card(d, tx, y, tw, "base_schedule (every incomplete action)", [
        ("a1  AGV_COMMAND  AGV-2  P15@90 -> P19@90", BUSY, S1),
        ("a2  AGV_COMMAND  AGV-2  P19@90 -> P23@90", BUSY, S1),
        ("a3  AGV_COMMAND  AGV-2  lower @P23", BUSY, S1),
        ("b1  BAY_COMMAND  B21  TRANSITION_TO_RETRIEVE", BUSY, S1)], accent=BUSY, k=S0)
    y = c1.y1 + 12
    c2 = _card(d, tx, y, tw, "initial_state after the loop", [
        ("agvs_[2].disabled = true", KEEP, S2),
        ("bays_[21].disabled = true", KEEP, S2),
        ("disabled_nodes_ = {15, 19, 23, 21}", KEEP, S2),
        ("agvs_[2].pose = P15@90  (not advanced)", T.fg2, S2)], accent=KEEP, k=S0)
    y = c2.y1 + 12
    c3 = _card(d, tx, y, tw, "disabledness_filters  (one GraphFilterProperties per footprint)", [
        ("[AGV]   P15 P19 P23 B21 and their edges off", KEEP, S3),
        ("[TRAY], [PAYLOAD+k]: same rule, own footprint", KEEP, S3)], accent=KEEP, k=S0)
    y = c3.y1 + 12
    c4 = _card(d, tx, y, tw, "pending_jobs", [
        ("j0  MOVE_AGV AGV-2 -> C14      failed: disabled agv", KEEP, S4),
        ("j1  REPARK_TRAY T24 -> P20     TrayMove added", NEW, S5),
        ("AGV candidates: AGV-1, AGV-3   (AGV-2 skipped)", FREE, S6)], accent=NEW, k=S0)
    for k, (bb, col) in {S1: (c1, BUSY), S2: (c2, KEEP), S3: (c3, KEEP), S4: (c4, KEEP), S5: (c4, NEW),
                         S6: (c4, FREE)}.items():
        with d.only(k):
            d.rect(bb.x0 - 4, bb.y0 - 4, bb.w + 8, bb.h + 8, rx=12, fill="none", stroke=col, sw=2.2, layer="under")
    cp_y = max(mb.y1, c4.y1) + 26
    cp = code_panel(d, 0, cp_y, tx + tw, [
        "// Scheduler::Plan(), right after ValidateBaseState (abridged)",
        "for(const auto& node : request_data.base_schedule.nodes) {",
        "  if(node.type == ActionNodeMsg::TYPE_AGV_COMMAND) {",
        "    initial_state.SetAgvDisabled(node.agv_id);                          // AGV-2",
        "    initial_state.SetNodeDisabled(node.agv_command.src.pose.node_id);   // P15, P19",
        "    initial_state.SetNodeDisabled(node.agv_command.dst.pose.node_id);   // P19, P23",
        "  } else if(node.type == ActionNodeMsg::TYPE_BAY_COMMAND) {",
        "    initial_state.SetBayDisabled(node.bay_id);                          // B21, also a disabled node",
        "  } else if(node.type == ActionNodeMsg::TYPE_VECS_COMMAND) { initial_state.SetVecsDisabled(node.vecs_id); }",
        "}",
        "plan_ctx->disabledness_filters = volley::GetDisabledEntitiesFilters(gg_, plan_ctx->initial_state, table_);",
        "if(agv_opt.value().disabled) return {false, \"Tried to move a disabled agv \" + ...};      // PlanAgvMoveJob",
        "if(!ctx->disabledness_filters[collision_id].IsEnabled(dest_vert)) return {false, ...};  // repark check",
        "for(const auto& [agv_id, agv_state] : working_state.GetAgvs()) { if(agv_state.disabled) continue; ... }",
    ], title="the reservation and three of its readers", size=11.5)
    for k, (a, b) in {S1: (1, 1), S2: (2, 9), S3: (10, 10), S4: (11, 11), S5: (12, 12), S6: (13, 13)}.items():
        with d.only(k):
            _hl_code(d, cp, a, b)
    frame(d, title="Reserving what the running schedule uses",
          subtitle="\"Disabled\" here means \"owned by the running schedule\": the new plan routes around those "
                   "assets for its whole duration. The keep-out overlay shows the rule, not CollisionTable output.",
          badge_key="yaml+hyp",
          legend=[("box", BUSY, "busy: in base_schedule"), ("dash", BUSY, "base action (Dispatch)"),
                  ("dashbox", KEEP, "reserved node volume"), ("dash", KEEP, "keep-out edge (AGV)"),
                  ("dasharrow", NEW, "new TrayMove"), ("box", FREE, "free AGV")])
    return d


# --------------------------------------------------------------------------------------
# 117 — the Apply call chain
# --------------------------------------------------------------------------------------

@figure("117_apply_call_chain", "Replaying one AgvMove: from the DAG to OnEvent (animated)", DOC)
def apply_call_chain():
    d = Doc("117_apply_call_chain", "Replaying one AgvMove, call by call",
            "UML sequence diagram, animated: ScheduleEventDag::Apply walks the topological order; each event's "
            "virtual Apply picks the subclass, std::visit picks the variant alternative, and overload resolution "
            "picks the DiscreteGarageState::OnEvent that checks and changes the state.")
    CAL, DAG, EV, VIS, DGS = T.muted, T.sky, T.green, T.amber, T.violet
    parts = [("cal", "Plan<Type>Job / any stage", CAL), ("dag", "ctx->events : ScheduleEventDag", DAG),
             ("ev", "*event : AgvMove", EV), ("vis", "std::visit + lambda", VIS),
             ("dgs", "working_state : DiscreteGarageState", DGS)]
    sub = {"cal": "scheduler", "dag": "planner_core", "ev": "planner_core", "vis": "<variant>, compiler-generated",
           "dgs": "common_ros"}
    q = {"ev": "which event class?  run time: virtual", "vis": "which change?  run time: variant index",
         "dgs": "which rule?  compile time: overload"}
    gaps = {"dag": 270, "ev": 290, "vis": 290, "dgs": 330}
    xs, x = {}, 110
    for k, _, _ in parts:
        x += gaps.get(k, 0)
        xs[k] = x
    col = {k: c for k, _, c in parts}
    head_h = 50
    qy = 0
    for k, label, c in parts:
        w = max(text_width(label, 12.5, "mono", 600), text_width(sub[k], 10.5, "sans")) + 28
        d.rect(xs[k] - w / 2, qy + 30, w, head_h, rx=8, fill=T.card, stroke=c, sw=1.5)
        d.text(xs[k], qy + 48, label, size=12.5, family="mono", weight=600, fill=c, anchor="middle")
        d.text(xs[k], qy + 66, sub[k], size=10.5, fill=T.muted, anchor="middle")
        if k in q:
            d.text(xs[k], qy + 12, q[k], size=11, weight=600, fill=c, anchor="middle")
    top = qy + 30 + head_h
    y = top + 44
    steps: list = []
    frags: list = []
    cur = {"k": 0}

    def step(caption):
        k = d.step(caption)
        cur["k"] = k
        steps.append([k, None, None])
        return k

    def mark(yy):
        s_ = steps[-1]
        s_[1] = yy if s_[1] is None else min(s_[1], yy)
        s_[2] = yy if s_[2] is None else max(s_[2], yy)

    def msg(a, b, text, *, ret=False, dy=42, c=None):
        nonlocal y
        c = c or (T.muted if ret else col[b])
        with d.at(cur["k"]):
            x1, x2 = xs[a], xs[b]
            off = 7
            xa = x1 + (off if x2 > x1 else -off)
            xb = x2 - (off if x2 > x1 else -off)
            d.line(xa, y, xb, y, stroke=c, sw=1.5, dash="6 4" if ret else None, layer="edges")
            d.arrowhead((xb, y), (xa, y), kind="open" if ret else "filled", color=c, size=9)
            label_pill(d, min(xa, xb) + 16, y - 13, text, color=c if not ret else T.fg2, bg=T.bg, size=11.5,
                       anchor="start")
        mark(y - 26)
        mark(y + 6)
        y += dy

    def selfmsg(a, text, *, dy=46, c=None, sub_text=None):
        nonlocal y
        c = c or col[a]
        with d.at(cur["k"]):
            x0 = xs[a] + 7
            h = 22
            d.polyline([(x0, y - 4), (x0 + 30, y - 4), (x0 + 30, y + h - 4), (x0 + 4, y + h - 4)], stroke=c, sw=1.5,
                       radius=4)
            d.arrowhead((x0, y + h - 4), (x0 + 30, y + h - 4), kind="filled", color=c, size=8)
            d.text(x0 + 40, y + 2, text, size=11.5, family="mono", fill=c)
            if sub_text:
                d.text(x0 + 40, y + 19, sub_text, size=11, fill=T.muted)
        mark(y - 14)
        mark(y + (26 if sub_text else 20))
        y += dy + (8 if sub_text else 0)

    step("A caller needs \"the garage after everything planned so far\": it copies ctx->initial_state into "
         "working_state and asks the event DAG to replay itself onto that copy.")
    a0 = y
    selfmsg("cal", "working_state = ctx->initial_state;", sub_text="a value copy; the context is not touched")
    msg("cal", "dag", "Apply(working_state)")
    step("ScheduleEventDag::Apply computes a topological order and visits every event in it. Order matters: an "
         "AgvMove only succeeds if earlier events left the AGV where this one expects it.")
    selfmsg("dag", "GetTopologicalOrdering()", sub_text="std::nullopt if the graph has a cycle -> {false, ...}")
    loop_y0 = y - 24
    y += 18
    step("For one vertex the DAG holds a std::shared_ptr<ScheduleEvent>. Calling the pure-virtual Apply runs "
         "AgvMove::Apply through the vtable: the first choice, made at run time from the object's class.")
    msg("dag", "ev", "event->Apply(state)    // virtual")
    step("AgvMove stores discrete_change_, a std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg>. std::visit reads "
         "which alternative it holds (index 1 here) and calls the lambda with that alternative: the second choice.")
    msg("ev", "vis", "std::visit(lambda, discrete_change_)")
    selfmsg("vis", "index() == 1  ->  arg : const AgvPoseChangedMsg&", sub_text="the lambda was compiled once per "
            "alternative; visit jumps to the right copy")
    step("The lambda body is one call, state.OnEvent(arg). The compiler already picked the overload for each "
         "copy of the lambda: OnEvent(const AgvPoseChangedMsg&) here, OnEvent(const AgvLiftChangedMsg&) in the "
         "other. This third choice costs nothing at run time.")
    msg("vis", "dgs", "state.OnEvent(arg)    // overload resolution")
    step("OnEvent checks the event against the state before changing it: the AGV exists, it is at node_id_curr@"
         "heading_curr, the move is not in place, and no other AGV is on node_id_next. It checks no geometry or "
         "edges.")
    selfmsg("dgs", "HasAgv(agv_id); pose == curr; next != curr", sub_text="else FailedEvent(\"a1 should be at ...\")")
    selfmsg("dgs", "carried tray -> moves to next (keeps reciprocal heading)")
    selfmsg("dgs", "no other AGV on node_id_next", sub_text="checked after the tray was moved: a failure here leaves "
            "the tray moved")
    step("All checks pass: the AGV's pose becomes node_id_next@heading_next and OnEvent returns SucceededEvent(), "
         "{true, \"\"}. The pair travels back unchanged through the lambda, visit and Apply.")
    selfmsg("dgs", "agv.pose = next;  return {true, \"\"}")
    msg("dgs", "vis", "BoolStringPair", ret=True)
    msg("vis", "ev", "BoolStringPair", ret=True)
    msg("ev", "dag", "BoolStringPair", ret=True)
    loop_y1 = y - 14
    frags.append((loop_y0, loop_y1, xs["dag"] - 70, xs["dgs"] + 430, "loop", "[for each event in topological order]",
                  1))
    step("The first failure stops the replay: ScheduleEventDag::Apply returns {false, \"Event <event>: <reason>\"} "
         "and working_state keeps every change made before it. Callers must treat that copy as spoiled.")
    y += 10
    msg("dag", "cal", "{true, \"\"}  or  {false, \"Event ...: a1 should be at ...\"}", ret=True)
    a1 = y - 30
    end_y = y + 6

    for k, _, c in parts:
        d.line(xs[k], top, xs[k], end_y, stroke=T.border, sw=1.2, dash="4 5", layer="under")
    d.rect(xs["cal"] - 6, a0 - 8, 12, a1 - a0 + 16, rx=2, fill=T.tint(CAL, 0.35, T.bg), stroke=CAL, sw=1,
           layer="under")
    x_left, x_right = 0, xs["dgs"] + 450
    for k, y0, y1 in steps:
        with d.only(k):
            d.rect(x_left, y0 - 8, x_right - x_left, y1 - y0 + 16, rx=8, fill=T.tint(T.sky, 0.07, T.bg),
                   stroke=T.tint(T.sky, 0.35, T.bg), sw=1, layer="under")
        with d.at(k):
            d.text(x_left - 26, y0 + 4, f"{k + 1}", size=13, family="mono", weight=700, fill=T.sky)
    for (y0, y1, fx0, fx1, tag, guard, k) in frags:
        with d.at(k):
            d.rect(fx0, y0, fx1 - fx0, y1 - y0, rx=6, fill="none", stroke=T.faint, sw=1.2, layer="under")
            tw = text_width(tag, 11.5, "mono", 700) + 16
            d.path(f"M{fx0} {y0 + 6} Q{fx0} {y0} {fx0 + 6} {y0} L{fx0 + tw + 8} {y0} L{fx0 + tw + 8} {y0 + 12} "
                   f"L{fx0 + tw} {y0 + 20} L{fx0} {y0 + 20} Z", fill=T.muted_bg, stroke=T.faint, sw=1, layer="under")
            d.text(fx0 + 8, y0 + 10, tag, size=11.5, family="mono", weight=700, fill=T.fg2)
            d.text(fx0 + tw + 16, y0 + 10, guard, size=11.5, family="mono", fill=T.muted)
    cp = code_panel(d, 0, end_y + 26, x_right, [
        "BoolStringPair AgvMove::Apply(volley::DiscreteGarageState& state) const {   // const: the event never changes",
        "  return std::visit(",
        "      [this, &state](auto&& arg) -> BoolStringPair { return state.OnEvent(arg); },  // generic lambda",
        "      discrete_change_);   // std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg>",
        "}",
    ], title="planner_core/src/schedule_events.cpp", size=11.5)
    for k, (a, b) in {2: (0, 0), 3: (1, 3), 4: (2, 2)}.items():
        with d.only(k):
            _hl_code(d, cp, a, b, col=T.amber)
    frame(d, title="Replaying one AgvMove: three choices on the way to OnEvent",
          subtitle="Each layer answers one question. The event DAG supplies the order, the event supplies the "
                   "change, and DiscreteGarageState owns the rule. Messages stay on screen; the highlighted band "
                   "is the current step.",
          badge_key="as-built",
          legend=[("arrow", T.fg2, "call"), ("dep", T.muted, "return BoolStringPair")])
    return d


# --------------------------------------------------------------------------------------
# 122 — what closing a node does, data structure by data structure
# --------------------------------------------------------------------------------------
# Geometry rule (illustrative, axis-aligned rectangles, no buffer): a reserved node blocks the XL window
# (STALL_L x STALL_W, long side along x at heading 90) centred on it. An AGV pose (2.2 m x 1.1 m, long side
# along x) is off if its rectangle overlaps that window; an edge is off if the box swept between its two end
# footprints overlaps it. The real sets come from CollisionTable::Query(PAYLOAD + index(XL), AGV, {node, h}).
AGV_L, AGV_W = 2.2, 1.1
ZOOM_X, ZOOM_Y = (27.6, 46.4), (17.9, 25.4)


def _rect_at(nid, L, W):
    n = NODES[nid]
    return (n.x - L / 2, n.y - W / 2, n.x + L / 2, n.y + W / 2)


def _overlap(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def _keep_out(reserved):
    vols = [_rect_at(r, STALL_L, STALL_W) for r in reserved]
    poses = {nid for nid in NODES if any(_overlap(_rect_at(nid, AGV_L, AGV_W), v) for v in vols)}
    edges = set()
    for a, b in EDGES:
        ra, rb = _rect_at(a, AGV_L, AGV_W), _rect_at(b, AGV_L, AGV_W)
        sweep = (min(ra[0], rb[0]), min(ra[1], rb[1]), max(ra[2], rb[2]), max(ra[3], rb[3]))
        if any(_overlap(sweep, v) for v in vols):
            edges.add((a, b))
    return poses, edges


PATH_RES = [26, 27, 24]
P_POSES, P_EDGES = _keep_out(PATH_RES)
GAP_RES = [25, 27]
G_POSES, G_EDGES = _keep_out(GAP_RES)
assert {26, 27, 24} <= P_POSES and (26, 27) in P_EDGES and (24, 27) in P_EDGES
assert 26 not in G_POSES and (25, 26) in G_EDGES and (26, 27) in G_EDGES and (23, 26) not in G_EDGES


@figure("122_closing_a_node", "What closing a node does, data structure by data structure (animated)", DOC)
def closing_a_node():
    d = Doc("122_closing_a_node", "What closing a node does",
            "Animated: two one-edge AGV commands in base_schedule, followed from the reservation loop through "
            "DiscreteGarageState, GetStaticFilter and CollisionTable::Query to the boolean masks of "
            "GraphFilterProperties that every search reads. The last step shows the gap left by a command that "
            "spans several nodes.")
    S0 = d.step("base_schedule holds two commands for AGV-1, each one graph edge: c1 W26@90 -> W27@90 and c2 "
                "W27@90 -> P24@90. Scheduler-built schedules always look like this: one CHUGG motion per edge, one "
                "ActionNode per motion.")
    S1 = d.step("The reservation loop: SetAgvDisabled(1) sets agvs_[1].disabled; SetNodeDisabled adds the source "
                "and destination of each command to disabled_nodes_ (a std::set<uint32_t>). W27 is the end of c1 "
                "and the start of c2, so the whole route is covered: {24, 26, 27}.")
    S2 = d.step("GetStaticFilter(AGV, ...) copies disabled_nodes_ into all_disabled_nodes and adds the node of every "
                "disabled entity (AGV-1 stands on W26). For each node it takes the largest window the node allows "
                "(max_resource_size_index; XL here) as a footprint, PAYLOAD + index(XL).")
    S3 = d.step("For each heading of the node it asks the CollisionTable: Query(PAYLOAD + index(XL), AGV, {27, 90}) "
                "returns every pose and edge where an AGV would overlap that window. Both go into disabled_poses "
                "and disabled_edges.")
    S4 = d.step("All three nodes together: the route, both edges of it and every edge touching its stops are off, "
                "plus any pose whose footprint reaches into a window. The graph itself is not edited: Layout, "
                "PoseGraph, GarageGraph and CollisionTable stay as they are.")
    S5 = d.step("GraphFilterProperties(gg_, disabled_poses, disabled_edges) builds two boolean masks over the "
                "graph, all true, then false for each listed pose and edge. disabledness_filters keeps one per "
                "footprint (AGV, TRAY, each payload window); CHUGG builds the same masks as constraints_.")
    S6 = d.step("The gap, a different request: AGV-1 stands on W25 and its one command c W25@90 -> W27@90 passes "
                "through W26. Only W25 and W27 are reserved. "
                "Their windows block the edges W25-W26 and W26-W27, but the pose W26 and the edge P23-W26 stay on, "
                "so a new plan could park an AGV on W26, in the running AGV's way.")
    s = 34
    m = Map(d, 0, 0, s, ZOOM_X, ZOOM_Y)
    m.base(labels=True, zones=False, axes=False)
    mb = m.box

    def vol(nid, k):
        x, y = m.P(nid)
        w, h = STALL_L * s, STALL_W * s
        with k:
            d.rect(x - w / 2, y - h / 2, w, h, rx=5, fill=KEEP, opacity=0.13, layer="over")
            d.rect(x - w / 2, y - h / 2, w, h, rx=5, fill="none", stroke=KEEP, sw=1.8, dash="6 4", layer="over")

    def xmark(nid, col=KEEP):
        x, y = m.P(nid)
        d.line(x - 7, y - 7, x + 7, y + 7, stroke=col, sw=2.6, layer="top")
        d.line(x - 7, y + 7, x + 7, y - 7, stroke=col, sw=2.6, layer="top")

    def edge_off(a, b):
        (x0, y0), (x1, y1) = m.P(a), m.P(b)
        d.line(x0, y0, x1, y1, stroke=KEEP, sw=3, dash="4 4", layer="over")

    # base-schedule commands (S0..S5)
    with d.at(S0, S5):
        m.route([26, 27], BUSY, sw=3.5, dash="7 5", offset=(0, -10), num=1, num_at=0)
        m.route([27, 24], BUSY, sw=3.5, dash="7 5", offset=(10, 0), num=2, num_at=0)
    # S1 rings on reserved nodes
    for nid in PATH_RES:
        x, y = m.P(nid)
        with d.at(S1, S5):
            d.circle(x, y, 15, fill="none", stroke=KEEP, sw=2.4, layer="top")
    # S2 + S3: W27 alone
    vol(27, d.only(S2))
    vol(27, d.only(S3))
    p27, e27 = _keep_out([27])
    with d.only(S3):
        for a, b in sorted(e27):
            edge_off(a, b)
        for nid in sorted(p27):
            xmark(nid)
    # S4, S5: all three
    for nid in PATH_RES:
        vol(nid, d.at(S4, S5))
    with d.at(S4, S5):
        for a, b in sorted(P_EDGES):
            edge_off(a, b)
        for nid in sorted(P_POSES):
            xmark(nid)
    # S6: gap case
    for nid in GAP_RES:
        vol(nid, d.only(S6))
    with d.only(S6):
        m.route([25, 26, 27], BUSY, sw=3.5, dash="7 5", offset=(0, -10))
        for a, b in sorted(G_EDGES):
            edge_off(a, b)
        for nid in sorted(G_POSES):
            xmark(nid)
        x, y = m.P(26)
        d.circle(x, y, 17, fill="none", stroke=T.amber, sw=2.6, layer="top")
        m.route([23, 26], T.amber, sw=3, offset=(10, 0))
        label_pill(d, x + 6, y + 30, "W26 still on", color=T.amber, bg=T.bg_deep, border=T.amber, size=11)
    sc = Scene(m)
    sc.agv("AGV-1", 26, heading=90, color=BUSY, label_side="above")
    sc.jump(S6, "AGV-1", 25)
    sc.draw()

    # right: the data structures, top to bottom
    tx = mb.x1 + 34
    tw = 520
    y = mb.y0
    cards = {}

    def card(key, title, sub, rows, col):
        """rows: (text, first_step, last_step); rows sharing a slot are alternatives in time."""
        nonlocal y
        slots = sorted({r[3] for r in rows})
        h = 50 + 20 * len(slots) + 6
        d.rect(tx, y, tw, h, rx=9, fill=T.card, stroke=T.tint(col, 0.7, T.bg), sw=1.3)
        d.text(tx + 12, y + 16, title, size=12, family="mono", weight=700, fill=col)
        d.text(tx + 12, y + 33, sub, size=10.5, fill=T.muted)
        for text, k0, k1, slot in rows:
            with d.at(k0, k1):
                d.text(tx + 14, y + 54 + 20 * slot, text, size=11, family="mono",
                       fill=T.amber if k0 == S6 else T.fg2)
        cards[key] = BBox(tx, y, tx + tw, y + h)
        y += h + 9

    card("bs", "PlanRequest.base_schedule : Schedule", "input, read once by the loop",
         [("nodes[0]  c1  AGV-1  src {26, 90}  dst {27, 90}", S0, S5, 0),
          ("nodes[1]  c2  AGV-1  src {27, 90}  dst {24, 90}", S0, S5, 1),
          ("nodes[0]  c   AGV-1  src {25, 90}  dst {27, 90}  (via W26)", S6, S6, 0)], BUSY)
    card("dgs", "initial_state : DiscreteGarageState", "common_ros; changed by the loop",
         [("agvs_[1].disabled = true", S1, S6, 0),
          ("disabled_nodes_ = {24, 26, 27}   // std::set<uint32_t>", S1, S5, 1),
          ("disabled_nodes_ = {25, 27}       // W26 is not added", S6, S6, 1)], KEEP)
    card("loc", "GetStaticFilter locals", "motion_planner; built per call, per footprint",
         [("all_disabled_nodes = {24, 26, 27}   // + nodes of disabled assets", S2, S5, 0),
          ("all_disabled_nodes = {25, 27}       // AGV-1 stands on W25", S6, S6, 0),
          ("footprint of a node = PAYLOAD + index(XL)", S2, S6, 1),
          ("disabled_poses : unordered_set<GaragePose>", S2, S6, 2),
          ("disabled_edges : unordered_set<array<GaragePose, 2>>", S2, S6, 3)], KEEP)
    card("gfp", "GraphFilterProperties", "one per footprint; what every search reads",
         [("vertex_filter_ : VertexVectorPropertyMap<bool>", S5, S6, 0),
          ("edge_filter_   : EdgeVectorPropertyMap<bool>", S5, S6, 1),
          ("IsEnabled(v) / IsEnabled(e): unchecked index", S5, S6, 2)], KEEP)
    card("ctx", "ctx->disabledness_filters", "unordered_map<CollisionEntityId_t, GraphFilterProperties>",
         [("[AGV], [TRAY], [PAYLOAD + k] for each car size present", S5, S6, 0),
          ("CHUGG: constraints_ = GetAllStaticFilters(...) (same masks)", S5, S6, 1)], KEEP)
    hl = {S0: ["bs"], S1: ["dgs"], S2: ["loc"], S3: ["loc"], S4: ["loc"], S5: ["gfp", "ctx"], S6: ["dgs", "loc"]}
    for k, keys in hl.items():
        with d.only(k):
            for key in keys:
                bb = cards[key]
                d.rect(bb.x0 - 4, bb.y0 - 4, bb.w + 8, bb.h + 8, rx=12, fill="none", stroke=T.sky, sw=2.2,
                       layer="under")
    # vertex mask strip
    vy = mb.y1 + 26     # the mask strip sits under the map; the code goes in a third column
    verts = [25, 26, 27, 22, 23, 24, 19, 20]
    d.text(0, vy, "vertex_filter_[AGV] for the poses on this map (all headings are 90 here)", size=12, weight=600,
           fill=T.fg)
    cw = (mb.x1 - mb.x0 - 7 * 6) / 8      # eight cells across the width of the map
    for i, nid in enumerate(verts):
        x0 = mb.x0 + i * (cw + 6)
        lbl = NODES[nid].label + "@90"
        d.rect(x0, vy + 14, cw, 46, rx=7, fill=T.card, stroke=T.border, sw=1)
        d.text(x0 + cw / 2, vy + 28, lbl, size=11, family="mono", fill=T.fg2, anchor="middle")
        with d.before(S5) if hasattr(d, "before") else _Upto(d, S4):
            d.text(x0 + cw / 2, vy + 47, "true", size=11.5, family="mono", weight=700, fill=FREE, anchor="middle")
        on5 = nid not in P_POSES
        on6 = nid not in G_POSES
        with d.only(S5):
            d.text(x0 + cw / 2, vy + 47, "true" if on5 else "false", size=11.5, family="mono", weight=700,
                   fill=FREE if on5 else KEEP, anchor="middle")
        with d.only(S6):
            d.text(x0 + cw / 2, vy + 47, "true" if on6 else "false", size=11.5, family="mono", weight=700,
                   fill=(T.amber if nid == 26 else FREE) if on6 else KEEP, anchor="middle")
    cp = code_panel(d, tx + tw + 34, mb.y0, 820, [
        "// motion_planner/src/static_graph_filtering.cpp, GetStaticFilter (abridged)",
        "std::set<uint32_t> all_disabled_nodes(disabled_nodes.begin(), disabled_nodes.end());",
        "for(const auto& [agv_id, agv] : dgs.GetAgvs()) if(agv.disabled) all_disabled_nodes.insert(agv.pose.node_id);",
        "for(const auto& node_id : all_disabled_nodes) {",
        "  auto node = gg.GetLayout()->GetNodeById(node_id).value();          // throws if the id is unknown",
        "  auto footprint = node.max_resource_size_index > 0 ? PAYLOAD + node.max_resource_size_index : TRAY;",
        "  for(auto head : node.headings) {",
        "    auto [poses, edges] = ctable.Query(footprint, collision_id, ConstructGaragePose(node_id, head));",
        "    disabled_poses.insert(poses.begin(), poses.end());  disabled_edges.insert(edges.begin(), edges.end());",
        "  }",
        "}",
        "return {gg, disabled_poses, disabled_edges};   // GraphFilterProperties: masks all true, listed ones false",
    ], title="from closed nodes to masks", size=11)
    for k, (a, b) in {S2: (1, 5), S3: (6, 8), S4: (3, 10), S5: (11, 11), S6: (1, 2)}.items():
        with d.only(k):
            _hl_code(d, cp, a, b, size=11)
    frame(d, title="What closing a node does",
          subtitle="Nothing is removed from the graph. Closing a node adds its id to a set; every filter built "
                   "from the state then switches off the poses and edges that touch the node's largest window. "
                   "Overlaps are drawn with plain rectangles and no buffer; the real sets come from the "
                   "CollisionTable.",
          badge_key="yaml+hyp",
          legend=[("dash", BUSY, "base_schedule command"), ("ring", KEEP, "node in disabled_nodes_"),
                  ("dashbox", KEEP, "largest window of a closed node"), ("dash", KEEP, "edge switched off"),
                  ("ring", T.amber, "left on: the gap")])
    return d


class _Upto:
    """Visible from step 0 to step k (inclusive)."""

    def __init__(self, d, k):
        self.ctx = d.at(0, k)

    def __enter__(self):
        return self.ctx.__enter__()

    def __exit__(self, *a):
        return self.ctx.__exit__(*a)
