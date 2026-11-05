"""Code-walkthrough figures, part 3: tray assignment, freeing moves, AGV matching, AGV expansion, path repair."""
from __future__ import annotations

from components import (EVENT_COLOR, chip, code_panel, connect, event_box, flow, frame, label_pill, note,
                        num_badge)
from facility import Map, NODES, STALL_L, STALL_W, C_BAY, Scene
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


def _hl(d: Doc, bb, col, pad=5):
    """Highlight ring drawn behind a box (use inside d.only)."""
    d.rect(bb.x0 - pad, bb.y0 - pad, bb.w + 2 * pad, bb.h + 2 * pad, rx=12, fill=T.tint(col, 0.14, T.bg),
           stroke=col, sw=2.2, layer="under")


def _hl_diamond(d: Doc, bb, col, pad=7):
    cx, cy, w, h = bb.cx, bb.cy, bb.w / 2 + pad * 1.6, bb.h / 2 + pad
    d.polygon([(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)], fill=T.tint(col, 0.14, T.bg), stroke=col,
              sw=2.2, layer="under")


def _hl_code(d: Doc, panel, first, last=None, *, size=11.5, col=T.sky):
    """Highlight code lines first..last of a code_panel with a title (geometry mirrors code_panel)."""
    last = first if last is None else last
    lh = size * 1.5
    y0 = panel.y0 + 14 + 24 + size / 2 + first * lh - lh / 2
    h = (last - first + 1) * lh
    d.rect(panel.x0 + 6, y0, panel.w - 12, h, rx=4, fill=T.tint(col, 0.16, "#0B1222"), stroke=T.tint(col, 0.6, T.bg),
           sw=1, layer="main")


def _hl_flow(d: Doc, pts, col=T.fg):
    connect(d, pts, kind="flow", color=col, size=9, sw=2.6)


# --------------------------------------------------------------------------------------
# 27 — DoTrayAssignments decision flow
# --------------------------------------------------------------------------------------

@figure("27_tray_assignment_flow", "DoTrayAssignments decision flow", DOC1)
def tray_flow():
    d = Doc("27_tray_assignment_flow", "Inside DoTrayAssignments()",
            "For every event in topological order: apply non-tray transitions, fill a missing tray id, fill a missing "
            "destination, or find the critical path and resolve blocking trays with two fallbacks.")
    # ---- steps: walk concrete events e0, e1, e2 (+ its blocker e4) through the loop
    S0 = d.step("Start of DoTrayAssignments(): working_state is a copy of the initial state and freeing_moves is "
                "empty. The loop visits the events in topological order: e0, e1, e2, ...")
    S1 = d.step("e0 is a BayTransition (TO_RETRIEVE on B21), not a TrayMove. ApplyTransitionToFreeingMoves() "
                "registers its pose in freeing_moves, applies it to working_state and the loop continues.")
    S2 = d.step("e1 moves T21 out of bay B21 but has no destination. AssignDestForUntargetedMove() runs "
                "ResolveBlockingTrays(T21): OpenSpaceSearch finds parking spot P23 in tier 1, then the loop continues.")
    S3 = d.step("e2 (T17: P17 -> B21) has a tray id and a destination. B21 is free in working_state because e1 already "
                "ran. BlockingTraySearch walks the critical path P17 -> P15 -> W13 -> ... -> B21 and finds T15 on P15.")
    S4 = d.step("Blocking loop, first pass: ResolveBlockingTrays(T15) with T17 immobile and the critical path banned "
                "finds P19 for T15.")
    S5 = d.step("The blocker move is emitted as a new event e4 (T15: P15 -> P19) with the edge e4 -> e2, plus edges "
                "from freeing_moves for every pose on e4's path.")
    S6 = d.step("Recompute the blocking trays on the remaining path: none are left, so the while loop ends.")
    S7 = d.step("Finish e2: dependencies from freeing_moves for the destination and source (e1 -> e2, e0 -> e2), "
                "Apply(e2) to working_state, record last_tray_event / first_tray_event for T17.")
    S8 = d.step("What if ResolveBlockingTrays had found no spot for T15? Fallback 1 advances T17 one step along its "
                "critical path and resolves again; fallback 2 retries without the critical-path ban, else it errors.")
    S9 = d.step("A later event e5 that asks for 'any empty tray' has no tray id. AssignTrayIdForEmptyMove() runs "
                "EmptyTraySearch from the destination (time + 30 s per blocker), then continues at 'has destination?'.")
    S10 = d.step("After the last event the loop ends. Every TrayMove now has a tray id and a destination; Reduce() is "
                 "deliberately not called here.")
    cx = 250
    y = 0
    loop = _box(d, cx - 230, y, 460, "for event : ctx->events.GetTopologicalOrdering()",
                ["working_state = ctx->initial_state;  freeing_moves = {}"], col=T.sky, title_col=T.sky)
    q1 = _diamond(d, cx, loop.y1 + 60, "TrayMove?", w=170)
    p_l_q1 = [(cx, loop.y1), (cx, q1.y0)]
    connect(d, p_l_q1, kind="flow", color=T.faint, size=7)
    nt = _box(d, cx + 160, q1.cy - 34, 330, "ApplyTransitionToFreeingMoves()",
              ["bay / VECS transition: register its pose,", "apply it, continue"], col=BAYC, title_col=BAYC)
    p_q1_nt = [(q1.x1, q1.cy), (nt.x0, q1.cy)]
    connect(d, p_q1_nt, kind="flow", color=T.faint, size=7, label="no",
            label_at=((q1.x1 + nt.x0) / 2, q1.cy - 12))
    q2 = _diamond(d, cx, q1.y1 + 70, "has tray id?", w=190)
    p_q1_q2 = [(cx, q1.y1), (cx, q2.y0)]
    connect(d, p_q1_q2, kind="flow", color=T.faint, size=7, label="yes",
            label_at=(cx + 18, (q1.y1 + q2.y0) / 2))
    a1 = _box(d, cx + 160, q2.cy - 34, 330, "AssignTrayIdForEmptyMove()",
              ["EmptyTraySearch from the destination: cheapest", "empty tray (time + 30 s per blocker)"], col=TRAY, title_col=TRAY)
    p_q2_a1 = [(q2.x1, q2.cy), (a1.x0, q2.cy)]
    connect(d, p_q2_a1, kind="flow", color=T.faint, size=7, label="no",
            label_at=((q2.x1 + a1.x0) / 2, q2.cy - 12))
    q3 = _diamond(d, cx, q2.y1 + 70, "has destination?", w=210)
    p_q2_q3 = [(cx, q2.y1), (cx, q3.y0)]
    connect(d, p_q2_q3, kind="flow", color=T.faint, size=7)
    p_a1_q3 = [(a1.cx, a1.y1), (a1.cx, a1.y1 + 14), (cx + 40, a1.y1 + 14), (cx + 40, q3.y0 + 6)]
    connect(d, p_a1_q3, kind="flow", color=T.faint, size=7)
    a2 = _box(d, cx + 160, q3.cy - 44, 330, "AssignDestForUntargetedMove()",
              ["ResolveBlockingTrays(tray): OpenSpaceSearch", "tier 1 parking, tier 2 waypoint stash;",
               "adds blocker moves; then continue"], col=TRAY, title_col=TRAY)
    p_q3_a2 = [(q3.x1, q3.cy), (a2.x0, q3.cy)]
    connect(d, p_q3_a2, kind="flow", color=T.faint, size=7, label="no",
            label_at=((q3.x1 + a2.x0) / 2, q3.cy - 12))
    s1 = _box(d, cx - 230, q3.y1 + 40, 460, "destination free?  then BlockingTraySearch",
              ["critical path = tray pose -> dest; collect trays on it", "error if the destination is occupied/disabled"])
    p_q3_s1 = [(cx, q3.y1), (cx, s1.y0)]
    connect(d, p_q3_s1, kind="flow", color=T.faint, size=7, label="yes",
            label_at=(cx + 18, (q3.y1 + s1.y0) / 2))
    # blocking loop frame
    ly = s1.y1 + 34
    lf = BBox(cx - 250, ly, cx + 250 + 410, ly + 330)
    d.rect(lf.x0, lf.y0, lf.w, lf.h, rx=12, fill=T.tint(TRAY, 0.03, T.bg), stroke=T.tint(TRAY, 0.5, T.bg), sw=1,
           dash="6 5", layer="bg")
    d.text(lf.x0 + 14, ly + 18, "while (blocking trays remain on the critical path)", size=12, family="mono",
           weight=600, fill=TRAY)
    r1 = _box(d, cx - 230, ly + 36, 460, "ResolveBlockingTrays(blocker, immobile={root},",
              ["  illegal = critical path + earlier dests of this blocker)", "may recurse when the blocker is itself blocked"],
              col=TRAY)
    ax = cx + 180
    p_s1_r1 = [(ax, s1.y1), (ax, r1.y0)]
    connect(d, p_s1_r1, kind="flow", color=T.faint, size=7)
    f1 = _box(d, cx + 300, ly + 36, 350, "fallback 1: advance the root tray",
              ["one step along its critical path,", "then resolve again"], col=T.red, title_col=T.red, dash="5 4")
    f2 = _box(d, cx + 300, f1.y1 + 18, 350, "fallback 2: park on the critical path",
              ["retry without the critical-path ban; else error", "\"Failed to find open space for blocking tray\""],
              col=T.red, title_col=T.red, dash="5 4")
    p_r1_f1 = [(r1.x1, r1.y0 + 24), (f1.x0, r1.y0 + 24)]
    connect(d, p_r1_f1, kind="flow", color=T.red, size=7, dash="4 3",
            label="no dest", label_at=((r1.x1 + f1.x0) / 2, r1.y0 + 10))
    p_f1_f2 = [(f1.cx, f1.y1), (f2.cx, f2.y0)]
    connect(d, p_f1_f2, kind="flow", color=T.red, size=7, dash="4 3")
    r2 = _box(d, cx - 230, r1.y1 + 26, 460, "emit blocker TrayMoves as events (chained)",
              ["edge: blocker move -> root move", "edges from freeing_moves for every path pose"], col=TRAY)
    p_r1_r2 = [(cx, r1.y1), (cx, r2.y0)]
    connect(d, p_r1_r2, kind="flow", color=T.faint, size=7)
    r3 = _box(d, cx - 230, r2.y1 + 26, 460, "recompute blocking trays on the remaining path", [], col=TRAY)
    p_r2_r3 = [(cx, r2.y1), (cx, r3.y0)]
    connect(d, p_r2_r3, kind="flow", color=T.faint, size=7)
    p_r3_r1 = [(r3.x0, r3.cy), (r3.x0 - 12, r3.cy), (r3.x0 - 12, r1.cy), (r1.x0, r1.cy)]
    connect(d, p_r3_r1, kind="flow", color=TRAY, size=7, radius=4)
    fin = _box(d, cx - 230, lf.y1 + 30, 460, "finish this TrayMove",
               ["freeing_moves deps for dest + source; Apply(event);", "record last_tray_event / first_tray_event"],
               col=T.green, title_col=T.green)
    p_r3_fin = [(cx, r3.y1), (cx, fin.y0)]
    connect(d, [(cx, lf.y1), (cx, fin.y0)], kind="flow", color=T.faint, size=7)
    with d.at(S10):
        nb = note(d, cx + 300, fin.y0 - 4, 350,
                  "Reduce() is deliberately not called at the end: a source comment says reducing here breaks the "
                  "following AGV assignment. Every TrayMove now has a tray id and a destination.",
                  title="After the loop", accent=T.amber)

    # ---- per-step highlights: boxes on the current branch and the arrows taken
    HL = T.fg
    plan = {
        S0: ([loop], [], []),
        S1: ([loop, nt], [q1], [p_l_q1, p_q1_nt]),
        S2: ([loop, a2], [q1, q2, q3], [p_l_q1, p_q1_q2, p_q2_q3, p_q3_a2]),
        S3: ([loop, s1], [q1, q2, q3], [p_l_q1, p_q1_q2, p_q2_q3, p_q3_s1]),
        S4: ([r1], [], [p_s1_r1]),
        S5: ([r2], [], [p_r1_r2]),
        S6: ([r3], [], [p_r2_r3]),
        S7: ([fin], [], [[(cx, r3.y1), (cx, fin.y0)]]),
        S8: ([r1, f1, f2], [], [p_r1_f1, p_f1_f2]),
        S9: ([loop, a1], [q1, q2, q3], [p_l_q1, p_q1_q2, p_q2_a1, p_a1_q3]),
        S10: ([loop, nb], [], []),
    }
    for k, (boxes, dias, paths) in plan.items():
        with d.only(k):
            for bb in boxes:
                _hl(d, bb, T.red if bb in (f1, f2) else HL)
            for bb in dias:
                _hl_diamond(d, bb, HL)
            for pts in paths:
                _hl_flow(d, pts, T.red if pts in (p_r1_f1, p_f1_f2) else HL)
    # ---- "current event" panel above the loop
    py = -104
    pw = lf.x1 - (cx - 230)
    d.rect(cx - 230, py, pw, 76, rx=10, fill=T.tint(T.sky, 0.05, T.bg), stroke=T.tint(T.sky, 0.5, T.bg), sw=1.2)
    d.text(cx - 216, py + 16, "current event", size=10.5, family="mono", weight=600, fill=T.muted)
    cur = {
        S0: ("before the first event", T.sky,
             "working_state = initial state, freeing_moves = {}; order: e0, e1, e2, ..."),
        S1: ("e0  BayTransition TO_RETRIEVE @ B21", BAYC,
             "not a TrayMove -> register B21 in freeing_moves, Apply(e0), continue"),
        S2: ("e1  TrayMove T21: B21 -> ?", TRAY,
             "tray id yes, destination no -> OpenSpaceSearch tier 1 picks P23; continue"),
        S3: ("e2  TrayMove T17: P17 -> B21", TRAY,
             "B21 free (T21 left in e1); critical path P17 -> P15 -> W13 -> W18 -> W22 -> W41 -> B21; blocker: T15"),
        S4: ("e2  blocker T15 on P15", TRAY,
             "ResolveBlockingTrays(T15, immobile = {T17}, illegal = critical path) -> P19"),
        S5: ("e2  emit e4: TrayMove T15: P15 -> P19", TRAY,
             "edge e4 -> e2; freeing_moves adds edges for e4's path poses"),
        S6: ("e2  recompute blockers", TRAY, "remaining path P15 -> ... -> B21 is clear -> leave the while loop"),
        S7: ("e2  finish", T.green, "edges e1 -> e2, e0 -> e2 (B21); Apply(e2); last_tray_event[T17] = e2"),
        S8: ("what if: no spot for T15?", T.red,
             "fallback 1: move T17 one step, resolve again; fallback 2: allow the critical path; else error"),
        S9: ("e5  TrayMove ?: -> dest (empty tray wanted)", TRAY,
             "no tray id -> EmptyTraySearch from dest, cheapest empty tray; then 'has destination?'"),
        S10: ("loop finished", T.green, "every TrayMove has a tray id and a destination; no Reduce() here"),
    }
    for k, (ev, col, what) in cur.items():
        with d.only(k):
            chip(d, cx - 216, py + 40, ev, col, size=11.5)
            d.text(cx - 216, py + 63, what, size=11, fill=T.fg2)
    frame(d, title="Inside DoTrayAssignments()",
          subtitle="One pass over the event DAG in topological order. Searches come from motion_planner "
                   "(EmptyTraySearch, OpenSpaceSearch, BlockingTraySearch) and all run through SingleSourceSearch.",
          badge_key="as-built",
          legend=[("box", TRAY, "tray work"), ("box", BAYC, "non-tray event"), ("dashbox", T.red, "fallback"),
                  ("arrow", T.faint, "control flow"), ("box", T.fg, "current step")])
    return d


# --------------------------------------------------------------------------------------
# 28 — freeing_moves: occupancy -> dependencies
# --------------------------------------------------------------------------------------

@figure("28_freeing_moves", "freeing_moves: occupancy becomes dependencies", DOC1)
def freeing_moves():
    d = Doc("28_freeing_moves", "freeing_moves: turning shared space into dependencies",
            "GarageOccupancyChecker remembers which events used each pose. A later move through a pose depends on "
            "every earlier event whose footprint collides there.")
    S0 = d.step("Start: freeing_moves (a GarageOccupancyChecker) is empty. T21 sits in bay B21, T15 on P15, T17 on "
                "P17, T20 on P20.")
    S1 = d.step("e0, the BayTransition TO_RETRIEVE, is processed: ApplyTransitionToFreeingMoves() records e0 as an "
                "occupant of the bay pose B21. The dashed arrow previews the next event, e1 (T21 -> P23).")
    S2 = d.step("e1 (TrayMove T21 -> P23) is processed: its source pose B21 gets e1 as a second occupant. T21 now "
                "stands on P23 in working_state.")
    S3 = d.step("Every pose on e1's path (P23, W22, W41, ...) is recorded too, so later moves that cross that path "
                "will wait for e1. The dashed arrow previews the blocker move e4 (T15 -> P19), emitted next.")
    S4 = d.step("While e2 (T17 -> B21) resolves its blockers, the blocker move e4 (T15 -> P19) is emitted and its "
                "source pose P15 is recorded with e4.")
    S5 = d.step("Now e2's path is checked pose by pose. GetBlockers(P15) returns e4, because T15's old footprint "
                "collides with T17's: edge e4 -> e2.")
    S6 = d.step("At the destination B21, GetBlockers returns e1, which took T21 out of the bay: edge e1 -> e2.")
    S7 = d.step("B21 also returns e0, the bay transition registered there: edge e0 -> e2. All three edges are "
                "AddDependency() calls on the event DAG.")
    S8 = d.step("Finally e2 is applied (T17 now stands in B21 in working_state) and adds itself as an occupant of "
                "every pose it uses, so later moves through P17, P15, ..., B21 will depend on e2.")
    s = 24
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    m.tray(20, "T20", payload=True, chip_pos="bl")
    # trays that move in working_state: they glide to their new spot in the step that applies the move
    # (dashed preview one step earlier) and leave a dashed ghost behind
    sc = Scene(m)
    sc.tray("T17", 17, payload=True, emphasis=True, chip_pos="tr")
    sc.tray("T21", 21, chip_pos="tr")
    sc.tray("T15", 15, chip_pos="tr")
    sc.drive(S2, "T21", [21, 41, 22, 23])
    sc.drive(S4, "T15", [15, 19])
    sc.drive(S8, "T17", [17, 15, 13, 18, 22, 41, 21], preview=False)   # e2's route arrow (from S5) is the preview
    sc.draw()
    for nid, lab, k, e in ((15, "T15 left (e4)", S4, None), (21, "T21 left (e1)", S2, S7), (17, "T17 left (e2)", S8, None)):
        x, y = m.P(nid)
        w, h = (STALL_L - 0.5) * s, (STALL_W - 0.32) * s
        with d.at(k, e):
            d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill="none", stroke=TRAY, sw=1.3, dash="5 4", layer="main")
            d.text(x + w / 2 - 8, y - h / 2 + 11, lab, size=10.5, family="mono", fill=TRAY, anchor="end",
                   halo=T.bg_deep, halo_w=3)
    with d.at(S5):
        m.route([17, 15, 13, 18, 22, 41, 21], TRAY, sw=3.5, offset=(0, 7), num=2, num_at=0)
    # poses with recorded occupants
    for nid, k in ((21, S1), (15, S4)):
        x, y = m.P(nid)
        with d.at(k):
            d.circle(x, y, 13, fill="none", stroke=T.sky, sw=2, layer="top")
    # pose being queried by GetBlockers
    for nid, k in ((15, S5), (21, S6), (21, S7)):
        x, y = m.P(nid)
        with d.only(k):
            d.circle(x, y, 20, fill=T.tint(T.fg, 0.08, T.bg_deep), stroke=T.fg, sw=2.2, layer="over")
    mb = m.box
    # table of the checker contents
    tx = mb.x1 + 36
    tw = 1060 - tx
    d.text(tx, 12, "freeing_moves contents, filled as events are processed", size=12.5, weight=600, fill=T.fg)
    rows = [("B21 (bay pose)", "e0  BayTransition TO_RETRIEVE", "ApplyTransitionToFreeingMoves", S1),
            ("B21 (bay pose)", "e1  TrayMove T21 -> P23", "source pose of a move", S2),
            ("P23, W22, W41 ...", "e1  (path poses)", "every pose on e1's path", S3),
            ("P15", "e4  TrayMove T15 -> P19", "source pose of a move", S4),
            ("P17, P15, W13 ... B21", "e2  TrayMove T17 -> B21", "added after e2's edges", S8)]
    y = 30
    RB = {}
    for pose, ev, why, k in rows:
        d.rect(tx, y, tw, 52, rx=8, fill="none", stroke=T.border_soft, sw=1, dash="3 4", layer="under")
        with d.at(k):
            d.rect(tx, y, tw, 52, rx=8, fill=T.card, stroke=T.border_soft, sw=1)
            d.text(tx + 12, y + 18, pose, size=11.5, family="mono", weight=600, fill=T.sky)
            d.text(tx + 12, y + 37, ev, size=11.5, family="mono", fill=T.fg)
            d.text(tx + tw - 10, y + 18, why, size=10.5, fill=T.muted, anchor="end")
        RB[k] = BBox(tx, y, tx + tw, y + 52)
        y += 60
    with d.only(S0):
        d.text(tx + tw / 2, 30 + 26, "(empty)", size=11.5, family="mono", fill=T.faint, anchor="middle")
    # rows that answer GetBlockers in the edge steps
    for k, rk in ((S1, S1), (S2, S2), (S3, S3), (S4, S4), (S5, S4), (S6, S2), (S7, S1), (S8, S8)):
        with d.only(k):
            _hl(d, RB[rk], T.fg, pad=4)
    d.text(tx, y + 12, "edges added for e2 (T17 -> B21)", size=12.5, weight=600, fill=T.fg)
    edges = [("e4 -> e2", "path pose P15 was occupied by T15", S5), ("e1 -> e2", "destination B21 held T21", S6),
             ("e0 -> e2", "bay transition registered on B21", S7)]
    y += 26
    for e, why, k in edges:
        with d.at(k):
            chip(d, tx, y + 10, e, TRAY, size=11.5)
            d.text(tx + 92, y + 10, why, size=11.5, fill=T.fg2)
        y += 30
    cp = code_panel(d, 0, max(mb.y1, y) + 30, 1060, [
        "// DoTrayAssignments(), for each pose on a move's path (simplified):",
        "GarageOccupancyChecker<std::shared_ptr<ScheduleEvent>> freeing_moves(table_, gg_);  // Scheduler members",
        "auto blockers_opt = freeing_moves.GetBlockers(pose, tray_collision_id);   // who used this space before?",
        "for(auto& blocker : *blockers_opt) ctx->events.AddDependency(blocker, move);  // must happen first",
        "freeing_moves.AddOccupant(pose, tray_collision_id, move, /*lifted=*/true);    // remember this move too",
    ], title="the occupancy-to-edge pattern", size=11.5)
    for k, (a, b) in {S0: (1, 1), S1: (4, 4), S2: (4, 4), S3: (4, 4), S4: (4, 4), S5: (2, 3), S6: (2, 3),
                      S7: (2, 3), S8: (4, 4)}.items():
        with d.only(k):
            _hl_code(d, cp, a, b)
    frame(d, title="freeing_moves: turning shared space into dependencies",
          subtitle="Collision checks use the CollisionTable, so a pose \"collides\" if the two footprints overlap, "
                   "not only when node ids match. The same idea is reused on actions in ResponseFromTrajectories(). "
                   "Redundant edges are pruned later by Reduce().",
          badge_key="yaml+hyp",
          legend=[("route", TRAY, "e2: T17 -> B21"), ("dashbox", TRAY, "vacated by an earlier event"),
                  ("ring", T.sky, "pose with recorded occupants"), ("ring", T.fg, "pose being queried")])
    return d


# --------------------------------------------------------------------------------------
# 29 — AGV matching (BottleneckAssignment)
# --------------------------------------------------------------------------------------

@figure("29_agv_matching", "Matching AGVs to tray moves", DOC1)
def agv_matching():
    d = Doc("29_agv_matching", "Matching AGVs to root tray moves",
            "DoAgvAssignments builds an AGV-by-TrayMove cost table for the current root events and runs "
            "BottleneckAssignment; infeasible pairs get no edge.")
    S0 = d.step("One outer iteration of DoAgvAssignments: the root TrayMoves are e4 (T15 -> P19) and e1 (T21 -> "
                "P23); the candidate AGVs are AGV-1, AGV-2 and AGV-3. The cost table is still empty.")
    S1 = d.step("GetAgvToTrayAssignmentCost(AGV-1, e4): AGV-1 drives from W26 to T15 on P15 and lifts it, about 41 s.")
    S2 = d.step("AGV-1 -> e1: AGV-1 drives to T21 in bay B21, about 48 s.")
    S3 = d.step("AGV-2 -> e4: AGV-2 at W18 is close to P15, about 19 s, the cheapest pair.")
    S4 = d.step("AGV-2 -> e1: AGV-2 drives to B21, about 36 s.")
    S5 = d.step("AGV-3 already carries T24, so the cost function returns nullopt for both moves and AGV-3 gets no edge.")
    S6 = d.step("BottleneckAssignment minimises the largest cost used. With only edges <= 19 s (AGV-2/e4) it can match "
                "one move, not two.")
    S7 = d.step("Raise the limit to 36 s: AGV-2/e4 and AGV-2/e1 both need AGV-2, so still only one move can be matched.")
    S8 = d.step("At 41 s, AGV-1/e4 joins and {AGV-1/e4, AGV-2/e1} matches both moves; the threshold is 41 s. The "
                "cheaper total {AGV-2/e4 19 s, AGV-1/e1 48 s} loses because its worst pair is 48 s.")
    S9 = d.step("The matching goes to GetEventDag(), which orders matched AGVs whose paths would collide; then each "
                "pair is expanded into AGV events (the green legs show the drives to the trays).")
    P1 = d.step("Playing the plan: AGV-1 drives from W26 to P15 and stops under T15, the tray of e4.")
    P2 = d.step("AGV-2 drives from W18 past W22 and W41 into bay B21 and stops under T21, the tray of e1. The two "
                "drives share no node, so GetEventDag() adds no order between them.")
    s = 22
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    # mobile entities: the matched AGVs drive to their trays in the playback steps
    sc = Scene(m)
    sc.tray("T15", 15, chip_pos="bl")
    sc.tray("T21", 21, chip_pos="tr")
    sc.tray("T17", 17, payload=True, chip_pos="bl")
    sc.tray("T24", 24, chip_pos="bl")
    sc.agv("AGV-1", 26, heading=90, label_side="above")
    sc.agv("AGV-2", 18, heading=90, label_side="right")
    sc.agv("AGV-3", 24, heading=90, label_side="right")
    sc.lift(S0, "AGV-3")                                   # AGV-3 carries T24 throughout
    # the green chosen legs (S8 on) are the previews of these drives
    sc.drive(P1, "AGV-1", [26, 23, 19, 15], preview=False)
    sc.drive(P2, "AGV-2", [18, 22, 41, 21], preview=False)
    sc.draw()
    # travel legs being costed (A, B -> tray pose); kept for the chosen pairs at the end
    legs = {S1: [26, 23, 19, 15], S2: [26, 25, 22, 41, 21], S3: [18, 13, 15], S4: [18, 22, 41, 21]}
    for k, ids in legs.items():
        last = None if k in (S1, S4) else k
        first = k
        with d.only(k):
            m.route(ids, T.fg, sw=3, dash="6 4", offset=(0, 0))
        if k in (S1, S4):
            with d.at(S8, S9 if k == S1 else P1):
                m.route(ids, AGV, sw=3, offset=(5 if k == S1 else 0, 0 if k == S1 else -5))
    mb = m.box
    # bipartite graph
    gx = mb.x1 + 60
    agvs = [("AGV-1", "idle at W26"), ("AGV-2", "idle at W18"), ("AGV-3", "carrying T24")]
    moves = [("e4", "T15 -> P19"), ("e1", "T21 -> P23")]
    ay = [26, 116, 206]
    my = [56, 166]
    AB, MB = [], []
    for (a, sub), y in zip(agvs, ay):
        bb = BBox(gx, y, gx + 130, y + 50)
        d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=25, fill=T.card, stroke=AGV if a != "AGV-3" else T.faint, sw=1.4)
        d.text(bb.x0 + 16, y + 20, a, size=12, family="mono", weight=700, fill=AGV if a != "AGV-3" else T.muted)
        d.text(bb.x0 + 16, y + 37, sub, size=10.5, fill=T.muted)
        AB.append(bb)
    mx = gx + 300
    for (e, t), y in zip(moves, my):
        MB.append(event_box(d, mx, y, "TrayMove " + e, t, size=11.5, w=150))
    costs = {(0, 0): ("41 s", True, S1), (0, 1): ("48 s", False, S2), (1, 0): ("19 s", False, S3),
             (1, 1): ("36 s", True, S4)}
    thresh = {S6: 19, S7: 36, S8: 41}
    for (i, j), (c, chosen, k) in costs.items():
        a, b = AB[i], MB[j]
        t = 0.30 if (i + j) % 2 == 0 else 0.70
        lx, ly = a.x1 + (b.x0 - a.x1) * t, a.cy + (b.cy - a.cy) * t
        # feasible edge, revealed when its cost is computed
        with d.at(k, S7 if chosen else None):
            d.line(a.x1, a.cy, b.x0, b.cy, stroke=T.faint, sw=1.2, dash="4 4", layer="edges")
            label_pill(d, lx, ly, c, color=T.muted, size=11)
        with d.only(k):
            d.line(a.x1, a.cy, b.x0, b.cy, stroke=T.fg, sw=2.2, layer="edges")
        # edges inside the current threshold
        cost = int(c.split()[0])
        for st, th in thresh.items():
            if cost <= th and not (chosen and st == S8):
                with d.only(st):
                    d.line(a.x1, a.cy, b.x0, b.cy, stroke=T.sky, sw=2.2, layer="edges")
        if chosen:
            with d.at(S8):
                d.line(a.x1, a.cy, b.x0, b.cy, stroke=AGV, sw=3, layer="edges")
                label_pill(d, lx, ly, c, color=AGV, size=11)
    for k, (i, j) in ((S1, (0, 0)), (S2, (0, 1)), (S3, (1, 0)), (S4, (1, 1)), (P1, (0, 0)), (P2, (1, 1))):
        with d.only(k):
            _hl(d, AB[i], T.fg, pad=4)
            _hl(d, MB[j], T.fg, pad=4)
    d.text(gx, -12, "edge_costs (illustrative seconds)", size=12, weight=600, fill=T.fg)
    gy = AB[-1].y1 + 22
    with d.only(S5):
        _hl(d, AB[2], T.red, pad=4)
    with d.at(S5):
        for i, ln in enumerate(["no edges from AGV-3: it carries a different tray,",
                                "so GetAgvToTrayAssignmentCost() returns nullopt"]):
            d.text(gx, gy + i * 16, ln, size=11, fill=T.muted)
    # matching status line
    sy = gy + 50
    status = {S6: ("threshold <= 19 s", T.sky, "usable: AGV-2/e4 -> max matching 1 of 2"),
              S7: ("threshold <= 36 s", T.sky, "usable: AGV-2/e4, AGV-2/e1 (both AGV-2) -> 1 of 2"),
              S8: ("threshold <= 41 s", AGV, "+ AGV-1/e4 -> {AGV-1/e4, AGV-2/e1}: 2 of 2"),
              S9: ("matching", AGV, "{AGV-1/e4, AGV-2/e1}, threshold 41 s -> GetEventDag()")}
    for k, (lab, col, txt) in status.items():
        with d.at(k, None if k == S9 else k):
            cb = chip(d, gx, sy, lab, col, size=11.5)
            d.text(cb.x1 + 10, sy, txt, size=11.5, family="mono", fill=T.fg2)
    with d.at(S8):
        nb = note(d, gx, sy + 26, 1080 - gx,
                  "Bottleneck matching minimises the worst single cost. {AGV-1/e4 41 s, AGV-2/e1 36 s} wins with a "
                  "worst case of 41 s, although {AGV-2/e4 19 s, AGV-1/e1 48 s} has the lower total. GetAgvOccupiedDuration() "
                  "still returns 0, so queued work is not yet modelled.", title="What gets optimised", accent=T.amber)
    cp = code_panel(d, 0, max(mb.y1, nb.y1) + 30, 1080, [
        "// DoAgvAssignments(), one outer iteration (simplified)",
        "// cost(agv, move) = max(occupied(agv) - occupied(move), 0) + travel(agv.pose -> tray.pose) + lift_up",
        "edge_costs[{agv_id, root_event}] = GetAgvToTrayAssignmentCost(agv_id, *tray_move, working_state, adjusted, filters);",
        "auto [matching, threshold] = volley::BottleneckAssignment(edge_costs, agvs_to_assign, root_events,",
        "                                                            Interval::Duration::max()).value();",
        "auto agv_event_dag = GetEventDag(matching, working_state);   // order matched AGVs that would collide",
    ], title="task_planner::BottleneckAssignment", size=11.5)
    for k in range(S1, S9 + 1):
        a, b = (1, 2) if k <= S5 else ((3, 4) if k <= S8 else (5, 5))
        with d.only(k):
            _hl_code(d, cp, a, b)
    frame(d, title="Matching AGVs to root tray moves",
          subtitle="Each outer loop first applies every non-tray root, then matches AGVs to the TrayMoves that have no "
                   "unassigned parents. AGVs trapped in a bay that is not READY_TO_RETRIEVE are skipped.",
          badge_key="yaml+hyp",
          legend=[("route", AGV, "matched pair"), ("dash", T.faint, "feasible, not chosen"),
                  ("route", T.sky, "within the threshold"), ("box", TRAY, "root TrayMove"),
                  ("box", AGV, "enabled AGV")])
    return d


# --------------------------------------------------------------------------------------
# 30 — what one AGV assignment adds to the DAG
# --------------------------------------------------------------------------------------

@figure("30_agv_event_expansion", "What one AGV assignment adds", DOC1)
def agv_expansion():
    d = Doc("30_agv_event_expansion", "What one AGV assignment adds to the DAG",
            "Assigning AGV-1 to TrayMove e4 adds AgvMove(to tray), lift, sets agv_id on the TrayMove, and adds lower, "
            "with four kinds of dependency edges.")
    S0 = d.step("Before: TrayMove e4 (T15: P15 -> P19) is a root of event_dag_copy with no AGV yet. "
                "BottleneckAssignment matched it to AGV-1.")
    S1 = d.step("MoveAgvToTrayPose() adds an AgvMove that drives AGV-1 from W26 to the tray pose P15 (it is skipped "
                "when the AGV is already there).")
    S2 = d.step("AppendAgvLiftEvent(raised) adds an AgvMove that lifts T15 onto AGV-1, after the drive.")
    S3 = d.step("SetAgvId(AGV-1) fills in the TrayMove itself: e4 now carries T15 to P19 on AGV-1, after the lift.")
    S4 = d.step("AppendAgvLiftEvent(lowered) adds the lower at P19, so AGV-1 is free again after e4.")
    S5 = d.step("Incoming edge 1: AGV-1's previous event (last_agv_event[AGV-1]) must finish before AGV-1 drives off: one chain "
                "of events per AGV.")
    S6 = d.step("Incoming edge 2: if a tray stands on AGV-1's navigation path, that tray's first move "
                "(ctx->first_tray_event) must clear it first.")
    S7 = d.step("Incoming edge 3: AddNodeArrivalDeps() makes AGV-1's arrival at P15 wait until the previous AGV on that "
                "node has left.")
    S8 = d.step("Incoming edge 4: if agv_event_dag says another matched AGV (parent AGV-2) must go first, "
                "its last_move_to_tray_event[AGV-2] precedes AGV-1's drive.")
    S9 = d.step("Finally the assignment's event_cost (travel + lift_up + carry + lift_down) is propagated to the "
                "children and added to agv_occupied_durations[AGV-1].")
    W = 1060
    d.text(0, 0, "before", size=12.5, family="mono", weight=700, fill=T.muted)
    pre = event_box(d, 0, 16, "TrayMove e4", "T15: P15 -> P19   agv = ?", size=11.5)
    d.text(pre.x1 + 30, pre.cy, "a root of event_dag_copy, matched to AGV-1 by BottleneckAssignment", size=11.5,
           fill=T.muted)
    with d.only(S0):
        _hl(d, pre, T.fg, pad=4)
    y = pre.y1 + 74
    d.text(0, y - 20, "after", size=12.5, family="mono", weight=700, fill=T.fg)
    bw = 210
    gx = 44
    chain = [("AgvMove", "AGV-1: W26 -> P15", "MoveAgvToTrayPose()"), ("AgvMove", "AGV-1 lift", "AppendAgvLiftEvent(raised)"),
             ("TrayMove e4", "T15 -> P19, agv = AGV-1", "SetAgvId(AGV-1)"),
             ("AgvMove", "AGV-1 lower", "AppendAgvLiftEvent(lowered)")]
    xs = [i * (bw + gx) for i in range(4)]
    B = []
    for i, ((k, t, sub), x) in enumerate(zip(chain, xs)):
        d.rect(x, y, bw, 64, rx=8, fill="none", stroke=T.border_soft, sw=1, dash="3 4", layer="under")
        with d.at(S1 + i):
            B.append(event_box(d, x, y, k, t, w=bw, sub=sub, size=11.5, style="new" if k == "AgvMove" else "solid"))
        with d.only(S1 + i):
            _hl(d, B[-1], T.fg, pad=8)
    for i, (a, b) in enumerate(zip(B, B[1:])):
        with d.at(S2 + i):
            connect(d, [(a.x1, a.cy), (b.x0, b.cy)], kind="flow", color=AGV, size=8, sw=1.6)
    # incoming edge kinds
    src_y = y + 170
    kinds = [
        ("AGV-1's previous event", "last_agv_event[AGV-1]", AGV, 0, "chain per AGV"),
        ("first move of a path tray", "ctx->first_tray_event[id]", TRAY, 0, "tray on AGV-1's nav path clears first"),
        ("prior occupant of P15", "AddNodeArrivalDeps()", T.sky, 0, "previous AGV must leave the node"),
        ("parent AGV in agv_event_dag", "last_move_to_tray_event[AGV-2]", T.violet, 0, "collision order among matches"),
    ]
    for i, (name, code, col, tgt, why) in enumerate(kinds):
        x = i * (bw + gx)
        bb = BBox(x, src_y, x + bw, src_y + 64)
        k = S5 + i
        with d.at(k):
            d.rect(bb.x0, bb.y0, bb.w, bb.h, rx=8, fill=T.bg, stroke=col, sw=1.3, dash="4 3")
            d.text(x + 12, src_y + 17, name, size=11.5, weight=600, fill=col)
            csz = 11 if text_width(code, 11, "mono") <= bw - 22 else 10
            d.text(x + 12, src_y + 36, code, size=csz, family="mono", fill=T.fg2)
            d.text(x + 12, src_y + 53, why, size=10.5, fill=T.muted)
            tx = B[0].x0 + 30 + i * 40
            connect(d, [(bb.cx, bb.y0), (bb.cx, src_y - 26 - i * 0), (tx, src_y - 26), (tx, B[0].y1)], kind="flow",
                    color=col, size=8, sw=1.5, radius=6)
        with d.only(k):
            _hl(d, bb, col, pad=5)
            connect(d, [(bb.cx, bb.y0), (bb.cx, src_y - 26), (tx, src_y - 26), (tx, B[0].y1)], kind="flow",
                    color=col, size=10, sw=3, radius=6)
    # cost strip
    cy = src_y + 120
    with d.at(S9):
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
        d.text(0, cy + 66, "GetJustMovingCost() and the cost model's lift times; agv_occupied_durations[AGV-1] += event_cost",
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
    S0 = d.step("RunAgvPathRepairPass() replays the DAG in topological order with exact AGV occupancy. At index k it "
                "reaches the AgvMove that sends AGV-1 from W25 to W8.")
    S1 = d.step("Check 1: is AGV-1's path feasible when only AGV-1 itself is ignored? No: the path down past W13 is blocked, "
                "so TryClearBlockedAgvMove() continues.")
    S2 = d.step("Check 2: ignoring every other AGV the path is clear, so the obstacle is an AGV, not a tray or a "
                "disabled node.")
    S3 = d.step("Check 3: try each other AGV X and ignore only {AGV-1, X}. With X = AGV-2 the path clears: AGV-2, "
                "parked on W13, is the blocker.")
    S4 = d.step("Check 4: FindAgvDepartureFromNode(AGV-2, W13) looks after index k for the event in which AGV-2 leaves "
                "W13: AGV-2's AgvMove W13 -> P15 (dashed arrow).")
    S5 = d.step("Check 5: AddDependency(departure, AGV-1's move), unless that would form a cycle. AGV-1 now waits until "
                "AGV-2 has left W13.")
    S6 = d.step("The pass returns true (one edge added) and EnsureAgvMovePathsClear starts a fresh replay. It stops "
                "when a full replay adds nothing, on an error, or after 256 passes.")
    P1 = d.step("Playing the repaired order: AGV-2 departs first, driving from W13 into stall P15 under T15. W13 is "
                "now free.")
    P2 = d.step("Only then AGV-1 drives its reposition W25 -> W22 -> W18 -> W13 -> W8, through the node AGV-2 has left.")
    s = 24
    m = Map(d, 0, 0, s, (26.0, 46.4), (11.4, 25.2))
    m.base(labels=True, zones=False, axes=False)
    sc = Scene(m)
    sc.tray("T15", 15, chip_pos="bl")
    sc.tray("T19", 19, chip_pos="bl")
    sc.tray("T23", 23, chip_pos="bl")
    sc.agv("AGV-1", 25, heading=90, label_side="above")
    sc.agv("AGV-2", 13, heading=90, label_side="left")
    sc.drive(P1, "AGV-2", [13, 15], color=T.teal)               # its departure: dashed preview from S4
    sc.drive(P2, "AGV-1", [25, 22, 18, 13, 8], preview=False)  # the intended-path arrow is the preview
    sc.draw()
    x13, y13 = m.P(13)
    with d.at(S4, S5):     # Scene previews only the step before the drive; show B's departure from Check 4 on
        sc._arrow([m.P(13), m.P(15)], T.teal, dash="7 5", sw=3, op=None)
    with d.at(S1, P1):
        m.route([25, 22, 18, 13, 8], AGV, sw=3, offset=(10, 0), dash="7 5")
    with d.only(S1):
        d.circle(x13, y13, 26, fill="none", stroke=T.fg, sw=2, dash="4 3", layer="top")
        label_pill(d, x13 + 30, y13 + 34, "blocked here", color=T.fg, bg=T.bg_deep, border=T.fg, anchor="start",
                   size=11)
    with d.only(S2):
        d.circle(x13, y13, 26, fill=T.tint(T.bg_deep, 0.6, T.bg), stroke=T.faint, sw=2, dash="4 3", layer="top")
        label_pill(d, x13 + 30, y13 + 34, "ignoring all other AGVs: clear", color=T.muted, bg=T.bg_deep,
                   border=T.faint, anchor="start", size=11)
    with d.at(S3, S6):
        d.circle(x13, y13, 26, fill="none", stroke=T.red, sw=2, layer="top")
        label_pill(d, x13 + 30, y13 + 34, "AGV-1 cannot pass while AGV-2 is here", color=T.red, bg=T.bg_deep, border=T.red,
                   anchor="start", size=11)
    mb = m.box
    rx = mb.x1 + 40
    rw = 1060 - rx
    d.text(rx, 8, "topological replay finds", size=12.5, weight=600, fill=T.fg)
    a = event_box(d, rx, 26, "AgvMove (idx k)", "AGV-1: W25 -> W8", w=rw)
    with d.only(S0):
        _hl(d, a, T.fg, pad=4)
    with d.only(P2):
        _hl(d, a, T.fg, pad=4)
    bpos = BBox(rx, a.y1 + 96, rx + rw, a.y1 + 146)
    d.rect(bpos.x0, bpos.y0, bpos.w, bpos.h, rx=8, fill="none", stroke=T.border_soft, sw=1, dash="3 4",
           layer="under")
    with d.at(S4):
        b = event_box(d, rx, a.y1 + 96, "AgvMove (later)", "AGV-2: W13 -> P15  (AGV-2 departs)", w=rw)
    with d.only(S4):
        _hl(d, b, T.fg, pad=4)
    with d.only(P1):
        _hl(d, b, T.fg, pad=4)
    with d.at(S5):
        connect(d, [(b.x0 + 40, b.y0), (b.x0 + 40, a.y1)], kind="flow", color=T.red, size=9, sw=2)
        label_pill(d, a.x0 + 48, (a.y1 + b.y0) / 2, "new edge: departure -> AGV-1's move", color=T.red, anchor="start",
                   size=11)
    steps = [
        "path feasible ignoring only AGV-1?  no -> continue",
        "feasible ignoring every other AGV?  yes -> an AGV is the problem",
        "for each other AGV X: feasible ignoring {AGV-1, X}?  -> X = AGV-2",
        "FindAgvDepartureFromNode(AGV-2, W13) after idx k",
        "AddDependency(departure, move) unless it would form a cycle",
    ]
    yy = b.y1 + 34
    d.text(rx, yy - 8, "TryClearBlockedAgvMove(), in order", size=12, weight=600, fill=T.fg)
    for i, st in enumerate(steps, start=1):
        lines = wrap(st, rw - 30, 11.5, "mono")
        hgt = 16 * len(lines)
        with d.only(S1 + i - 1):
            d.rect(rx - 4, yy + 2, rw + 4, hgt + 8, rx=6, fill=T.tint(T.sky, 0.14, T.bg), stroke=T.sky, sw=1.2,
                   layer="under")
        with d.at(S1 + i - 1):
            num_badge(d, rx + 10, yy + 14, i, T.sky, r=9)
            for j, ln in enumerate(lines):
                d.text(rx + 26, yy + 14 + j * 16, ln, size=11.5, family="mono", fill=T.fg2)
        yy += hgt + 12
    cp = code_panel(d, 0, max(mb.y1, yy) + 24, 1060, [
        "// Scheduler::EnsureAgvMovePathsClear(ctx): called at the end of DoAgvAssignments(), before Reduce()",
        "for(size_t iter = 0; iter < 256; ++iter) {             // each productive pass adds exactly one edge",
        "  auto added_edge = RunAgvPathRepairPass(ctx);          // stdx::Expected<bool>",
        "  if(!added_edge.has_value()) return error;             // DAG could not be sorted",
        "  if(!added_edge.value()) return {};                    // full replay needed no repair",
        "}                                                       // cap hit: SanityCheckEvents is the backstop",
    ], title="why a separate pass", size=11.5)
    with d.at(S0, S5):
        _hl_code(d, cp, 2)
    with d.only(S6):
        _hl_code(d, cp, 1, 5)
    frame(d, title="Repairing AGV paths after assignment",
          subtitle="DoAgvAssignments orders events by its own serial assignment loop, which can differ from the final "
                   "topological order. This pass replays the real order, where AGV occupancy is exact, and adds one "
                   "gating edge at a time. Trays and disabled nodes are not fixed here.",
          badge_key="yaml+hyp",
          legend=[("dasharrow", AGV, "AGV-1's intended path"), ("dasharrow", T.teal, "AGV-2's departure"),
                  ("ring", T.red, "blocking AGV"),
                  ("arrow", T.red, "gating edge added")])
    return d
