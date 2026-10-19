"""fig_formulation: the event DAG as a partial-order plan, and the kinds of edge in it (125).

Doc 07-issue-and-proposal.html. Illustrative example built from the Pecos retrieve of the Task planning tab:
a RETRIEVE of the car on T17 into bay B21 (which holds empty tray T21), a blocker T15, and a second job that
reparks T24. Edge kinds are an analysis category of this study pack, not a code concept; the code rules that
create edges of each kind are named in the table of the section.
"""
from __future__ import annotations

from components import EVENT_COLOR, connect, event_box, frame, label_pill
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import S, T

DOC = "07-issue-and-proposal.html"
CAUSAL, PATH, RES, CONS = T.green, T.sky, T.amber, T.red


@figure("125_event_dag_edge_kinds", "Four kinds of edge in the event DAG (animated)", DOC)
def edge_kinds():
    d = Doc("125_event_dag_edge_kinds", "Four kinds of edge in the event DAG",
            "Animated: one small event DAG with every edge classified by why it exists: required by the domain, "
            "required only by a path chosen early, a resource order whose direction was chosen greedily, or "
            "conservative. Today every kind reaches CHUGG as a hard precedence constraint.")
    S0 = d.step("Two jobs. Job A retrieves the car on T17 into bay B21, which still holds empty tray T21; tray "
                "assignment also moves T15, which stands on T17's chosen route. Job B, a clean, moves two trays off "
                "waypoints. Seven events after AGV assignment (AGV-1 serves job A's moves, AGV-2 the blocker and "
                "job B's first move, AGV-3 its second); AGV approach and lift events are left out.")
    S1 = d.step("Causal edges (green): an effect of one event is a precondition of the next. Until B21 is in "
                "retrieve mode its door area blocks the aisle, the bay node must be empty before T17 enters, and "
                "the car must be in the bay before the hand-over. Every valid plan contains these orders.")
    S2 = d.step("Path-dependent edge (blue): T15 must leave P15 only because T17's route was fixed through P15 "
                "before motion planning. With another route, or with T15 leaving in time, the edge is not needed. "
                "These come from occupancy checks (freeing_moves) and path repairs.")
    S3 = d.step("Resource-order edge (amber): AGV-2 does the blocker move and job B's first move, so one must come "
                "first, but either order is valid. The direction was fixed by request order and assignment: in "
                "scheduling terms, a disjunctive constraint whose choice was made greedily.")
    S4 = d.step("Conservative edge (red): rule B makes each new event of a job wait for all of the job's current "
                "leaves, so job B's two moves are chained although they use different AGVs, trays and places.")
    S5 = d.step("What the motion planner receives today: all seven edges as hard precedence. A solver that knew "
                "the kinds could keep green, choose amber, let paths decide blue and drop red, and so find plans "
                "with more parallelism.")
    ev = {
        "e5": ("TrayMove", "T41  W41 -> P20", 1, 0),
        "e6": ("TrayMove", "T27  W27 -> P24", 2, 0),
        "e0": ("BayTransition", "B21 -> TO_RETRIEVE", 0, 1),
        "e4": ("TrayMove", "T15  P15 -> P19", 1, 1),
        "e1": ("TrayMove", "T21  B21 -> P23", 0, 2),
        "e2": ("TrayMove", "T17  P17 -> B21", 1, 2),
        "e3": ("BayTransition", "B21  PROCESS_RETRIEVE", 2, 2),
    }
    W, H = 250, 64
    gx, gy = 380, 120
    B = {}
    for k, (kind, text, c, r) in ev.items():
        x, y = 20 + c * gx, 40 + r * gy * 1.2
        sub = {"e0": "job A", "e1": "job A, AGV-1", "e2": "job A, AGV-1", "e3": "job A",
               "e4": "job A (blocker), AGV-2", "e5": "job B, AGV-2", "e6": "job B, AGV-3"}[k]
        B[k] = event_box(d, x, y, f"{kind} {k}", text, w=W, sub=sub)
    edges = [
        ("e0", "e1", CAUSAL, S1, "door area clear"),
        ("e0", "e2", CAUSAL, S1, "bay in retrieve mode"),
        ("e1", "e2", CAUSAL, S1, "bay node empty"),
        ("e2", "e3", CAUSAL, S1, "car in bay"),
        ("e4", "e2", PATH, S2, "route through P15"),
        ("e4", "e5", RES, S3, "AGV-2 order"),
        ("e5", "e6", CONS, S4, "rule B only"),
    ]
    for a, b, col, k, lbl in edges:
        A, Bb = B[a], B[b]
        if abs(A.cy - Bb.cy) < 2:
            pts = [(A.x1, A.cy), (Bb.x0, Bb.cy)]
        elif abs(A.cx - Bb.cx) < 2:
            pts = [(A.cx, A.y1), (Bb.cx, Bb.y0)] if A.cy < Bb.cy else [(A.cx, A.y0), (Bb.cx, Bb.y1)]
        else:
            xm = (A.x1 + Bb.x0) / 2
            pts = [(A.x1, A.cy), (xm, A.cy), (xm, Bb.cy), (Bb.x0, Bb.cy)]
        with d.at(k):
            connect(d, pts, kind="flow", color=col, sw=2.4)
            if len(pts) == 4:
                label_pill(d, pts[1][0] + 8, (pts[1][1] + pts[2][1]) / 2, lbl, color=col, size=10.5, bg=T.bg,
                           anchor="start")
            elif pts[0][1] == pts[-1][1]:
                label_pill(d, (pts[0][0] + pts[-1][0]) / 2, pts[0][1] + 18, lbl, color=col, size=10.5, bg=T.bg)
            else:
                label_pill(d, pts[0][0] + 8, (pts[0][1] + pts[-1][1]) / 2, lbl, color=col, size=10.5, bg=T.bg,
                           anchor="start")
    with d.only(S5):
        for bb in B.values():
            d.rect(bb.x0 - 5, bb.y0 - 5, bb.w + 10, bb.h + 10, rx=11, fill="none", stroke=T.fg2, sw=1.4,
                   dash="3 3", layer="under")
    # right: where each kind belongs
    tx = 20 + 2 * gx + W + 50
    rows = [("causal", CAUSAL, "required in every valid plan", "hard precedence", S1),
            ("path-dependent", PATH, "required only for a route chosen early", "leave to the path planner", S2),
            ("resource order", RES, "some order needed, direction free", "disjunction: solver chooses", S3),
            ("conservative", CONS, "not required", "drop", S4)]
    y = 40
    d.text(tx, y - 14, "edge kind -> where it belongs", size=12.5, weight=600, fill=T.fg)
    for name, col, why, where, k in rows:
        d.rect(tx, y, 380, 74, rx=9, fill=T.card, stroke=T.tint(col, 0.7, T.bg), sw=1.3)
        d.line(tx + 14, y + 20, tx + 44, y + 20, stroke=col, sw=2.6)
        d.arrowhead((tx + 52, y + 20), (tx + 30, y + 20), kind="filled", color=col, size=9)
        d.text(tx + 62, y + 20, name, size=12.5, family="mono", weight=700, fill=col)
        d.text(tx + 14, y + 42, why, size=11.5, fill=T.fg2)
        d.text(tx + 14, y + 60, "-> " + where, size=11.5, family="mono", fill=T.muted)
        with d.only(k):
            d.rect(tx - 4, y - 4, 388, 82, rx=12, fill="none", stroke=col, sw=2.2, layer="under")
        y += 86
    with d.only(S5):
        d.text(tx, y + 14, "today: all four -> hard precedence in CHUGG", size=12, family="mono", weight=700,
               fill=T.red)
    frame(d, title="Four kinds of edge in the event DAG",
          subtitle="The event DAG is a partial-order plan. Its edges record different things, but the pipeline "
                   "fixes all of them before timing and geometry are known. Example and classification are "
                   "illustrative.",
          badge_key="analysis",
          legend=[("arrow", CAUSAL, "causal"), ("arrow", PATH, "path-dependent"), ("arrow", RES, "resource order"),
                  ("arrow", CONS, "conservative")])
    return d
