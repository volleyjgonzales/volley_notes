"""Job-expansion figures: the Plan() loop, the building-block matrix and one 2D scenario per job type.

Every per-job figure has the same four parts so they can be compared side by side:
  map      the garage as working_state sees it when the job method starts (Pecos YAML geometry,
           hypothetical occupancy). Arrows are *intent* only: job expansion plans no paths.
  request  the SchedulerJob fields the method reads and the job_index it receives.
  events   the ScheduleEvents appended to ctx->events, in creation order, with every edge the
           method adds and the rule that added it (A = same entity, B = earlier leaf of the same
           job, C = tray into a bay/VECS waits for that resource's last event).
  steps    the method body as numbered steps, each with what happens in this example.
"""
from __future__ import annotations

import math
import re

from components import (EVENT_COLOR, chip, code_panel, connect, event_box, frame, label_pill, note, num_badge)
from facility import Map, NODES, STALL_L, STALL_W, C_BAY
from fig_code4 import _source_files, _strip_comments
from registry import figure
from svgkit import BBox, Doc, text_width, wrap, pts_to_path
from theme import S, T

DOC1 = "01-software-background.html"
TRAY, AGV, BAYC, VECS = T.amber, T.green, T.violet, T.pink
RULE_B = T.fg2
QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)
FULL_X, FULL_Y = (20.4, 46.4), (6.9, 25.2)
W = 1120
ENT_COL = {"tray": TRAY, "agv": AGV, "bay": BAYC, "vecs": VECS}


# --------------------------------------------------------------------------------------
# small drawing helpers
# --------------------------------------------------------------------------------------

def bay_pill(d: Doc, m: Map, nid: int, text: str, color=C_BAY, below=False):
    x, y = m.P(nid)
    off = (STALL_W + 0.9) * m.s / 2 + 12
    label_pill(d, x, y + off if below else y - off, text, color=color, bg=T.bg_deep, border=color, size=10.5)


def ghost(d: Doc, m: Map, nid, text: str, color=TRAY):
    x, y = m.P(nid)
    w, h = (STALL_L - 0.5) * m.s, (STALL_W - 0.32) * m.s
    d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill="none", stroke=color, sw=1.3, dash="5 4", layer="main")
    if text:
        d.text(x, y + 1, text, size=10.5, family="mono", fill=color, anchor="middle", halo=T.bg_deep, halo_w=3)


def vecs_mark(d: Doc, m: Map, nid: int, text: str):
    """Hypothetical VECS charger drawn on a parking stall (Pecos has no EV-charge node)."""
    x, y = m.P(nid)
    w, h = STALL_L * m.s - 3, STALL_W * m.s - 3
    d.rect(x - w / 2, y - h / 2, w, h, rx=4, fill="none", stroke=VECS, sw=2, dash="6 3", layer="under")
    d.text(x, y - h / 2 - 11, text, size=10.5, family="mono", weight=600, fill=VECS, anchor="middle",
           halo=T.bg_deep, halo_w=3, layer="labels")


def odp_area(d: Doc, m: Map, nid: int, text: str, color=T.red):
    """Illustrative BAY_ODP collision area: the bay plus the apron on its garage side."""
    x, y = m.P(nid)
    x0, x1 = x - STALL_L * m.s / 2 + 4, x + (STALL_L / 2 + 3.4) * m.s
    h = (STALL_W + 1.6) * m.s
    m.clip()
    d.rect(x0, y - h / 2, x1 - x0, h, rx=10, fill=T.tint(color, 0.06, T.bg_deep), stroke=color, sw=1.4,
           dash="3 3", layer="under")
    m.unclip()
    d.text(x1 - 6, y + h / 2 - 10, text, size=10.5, family="mono", fill=color, anchor="end", halo=T.bg_deep,
           halo_w=3)


def intent(d: Doc, m: Map, src, dst, num, color, *, bend=0.18, q_off=(0, -40), src_off=(0, 0), dst_off=(0, 0),
           num_t=0.5, dash="7 5"):
    """Curved 'intent' arrow (no path is planned at this stage). dst=None -> arrow to a '?' bubble."""
    k = m.s / 21
    q_off, src_off, dst_off = [(a * k, b * k) for a, b in (q_off, src_off, dst_off)]
    x0, y0 = m.P(src)
    x0, y0 = x0 + src_off[0], y0 + src_off[1]
    if dst is None:
        x1, y1 = x0 + q_off[0], y0 + q_off[1]
    else:
        x1, y1 = m.P(dst)
        x1, y1 = x1 + dst_off[0], y1 + dst_off[1]
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    cx, cy = (x0 + x1) / 2 + nx * bend * L, (y0 + y1) / 2 + ny * bend * L
    end_cut = 16 if dst is None else 6
    # shorten the end so the arrowhead tip sits at the target
    tx, ty = x1 - (x1 - cx) / math.hypot(x1 - cx, y1 - cy) * end_cut, y1 - (y1 - cy) / math.hypot(x1 - cx, y1 - cy) * end_cut
    hb = 12
    bx, by = tx - (tx - cx) / math.hypot(tx - cx, ty - cy) * hb * 0.8, ty - (ty - cy) / math.hypot(tx - cx, ty - cy) * hb * 0.8
    pd = f"M{x0:.1f} {y0:.1f} Q{cx:.1f} {cy:.1f} {bx:.1f} {by:.1f}"
    bb = BBox(min(x0, x1, cx), min(y0, y1, cy), max(x0, x1, cx), max(y0, y1, cy))
    d.path(pd, stroke=T.bg_deep, sw=7, layer="over", bbox=bb)
    d.path(pd, stroke=color, sw=3, dash=dash, layer="over", bbox=bb)
    d.arrowhead((tx, ty), (cx, cy), kind="filled", color=color, size=hb, layer="over")
    if dst is None:
        d.circle(x1, y1, 13, fill=T.bg_deep, stroke=color, sw=2, layer="top")
        d.text(x1, y1 + 0.5, "?", size=15, family="mono", weight=700, fill=color, anchor="middle", layer="top")
    t = num_t
    px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
    py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
    num_badge(d, px, py, num, color, r=11)


def agv_intent(d, m, src, dst, num, *, bend=0.15, src_off=(0, 0), dst_off=(0, 0), num_t=0.5):
    intent(d, m, src, dst, num, AGV, bend=bend, src_off=src_off, dst_off=dst_off, num_t=num_t, dash="3 4")


def state_tag(d: Doc, m: Map, nid, text, color):
    x, y = m.P(nid)
    label_pill(d, x, y, text, color=color, bg=T.bg_deep, border=color, size=10.5)


# --------------------------------------------------------------------------------------
# right column: request card + event column with rule-labelled edges
# --------------------------------------------------------------------------------------

def request_card(d: Doc, x, y, w, rows, *, title="Request"):
    pad = 14
    kw = max(text_width(k, 11, "mono") for k, _ in rows) + 14
    lines = []
    for k, v in rows:
        vl = wrap(v, w - 2 * pad - kw, 11.5, "mono")
        lines.append((k, vl))
    h = pad * 2 + 22 + sum(len(v) for _, v in lines) * 17
    d.rect(x, y, w, h, rx=10, fill=T.tint(T.sky, 0.06, T.bg), stroke=T.tint(T.sky, 0.5, T.bg), sw=1.2)
    d.text(x + pad, y + pad + 6, title, size=12.5, weight=600, fill=T.sky)
    yy = y + pad + 30
    for k, vl in lines:
        d.text(x + pad, yy, k, size=11, family="mono", fill=T.muted)
        for j, v in enumerate(vl):
            d.text(x + pad + kw, yy + j * 17, v, size=11.5, family="mono", fill=T.fg)
        yy += 17 * len(vl)
    return BBox(x, y, x + w, y + h)


RULE_STYLE = {"A": (None, 1.8), "B": ("5 4", 1.5), "C": ("2 4", 1.8)}


def event_column(d: Doc, x, y, events, edges, *, bw=290, gap=40, lane_x0=None):
    """events: list of (kind, text, job, style); numbered 1..n.
    edges: (i, j, rule, entity_or_color, label) with 1-based indices."""
    boxes = []
    yy = y
    for i, ev in enumerate(events):
        kind, text, job, style = ev[:4]
        sub = ev[4] if len(ev) > 4 else None
        k = f"{kind} · job {job}" if job is not None else kind
        b = event_box(d, x, yy, k, text, n=i + 1, w=bw, style=style, size=11.5, sub=sub)
        boxes.append(b)
        yy = b.y1 + gap
    lane_x0 = lane_x0 or x + bw + 34
    lanes_used = []
    adj_count = {}
    for (i, j, rule, ent, *lab) in edges:
        a, b = boxes[i - 1], boxes[j - 1]
        col = ENT_COL.get(ent, ent) if rule != "B" else RULE_B
        if rule == "C":
            col = ENT_COL.get(ent, ent)
        dash, sw = RULE_STYLE[rule]
        text = lab[0] if lab else (f"{rule} · {ent}" if rule == "A" and ent in ENT_COL else rule)
        if j == i + 1:
            k = adj_count.get(i, 0)
            adj_count[i] = k + 1
            xx = a.x0 + 46 + k * 92
            connect(d, [(xx, a.y1), (xx, b.y0)], kind="flow", color=col, size=8, sw=sw, dash=dash)
            label_pill(d, xx + 8, (a.y1 + b.y0) / 2, text, color=col, size=10, anchor="start", bg=T.bg)
        else:
            lane = 0
            while any(l == lane and not (j <= s0 or i >= s1) for (l, s0, s1) in lanes_used):
                lane += 1
            lanes_used.append((lane, i, j))
            lx = lane_x0 + lane * 44
            ya, yb = a.cy - 6, b.cy + 6
            connect(d, [(a.x1, ya), (lx, ya), (lx, yb), (b.x1, yb)], kind="flow", color=col, size=8, sw=sw,
                    dash=dash, radius=7)
            label_pill(d, lx, (ya + yb) / 2, text, color=col, size=10, bg=T.bg)
    return boxes


# --------------------------------------------------------------------------------------
# step table
# --------------------------------------------------------------------------------------

REPLAY = ("Make a scratch copy of the request's garage and apply every event already in the DAG, so the method "
          "sees the garage as earlier jobs will leave it.")
GENERAL = {
"40_job_move_agv": [
    REPLAY,
    "Refuse jobs that do not name an AGV. Choosing an AGV for the caller is not implemented (a TODO).",
    "Look the AGV up in the scratch garage; a missing or disabled AGV cannot be moved.",
    "If the AGV already stands at the destination pose, succeed without adding anything.",
    "Describe the move as current pose -> destination, then check the destination exists in the graph and is "
    "not disabled for an AGV in this state (empty or carrying a tray).",
    "Optional shortcut: if the caller allows the reverse heading and the headings are the same or opposite, keep "
    "the AGV where it is.",
    "An AGV without a tray gets one AgvMove, chained after the AGV's previous event (rule A).",
    "An AGV carrying a tray moves the tray with it: create a TrayMove with this AGV already assigned, convert the "
    "destination to the tray's heading and apply the parking-heading policy; chain after the tray's last event.",
    "Make the new event wait for any earlier events of the same job (rule B).",
],
"41_job_repark_tray": [
    "A repark needs at least a tray or a destination; with neither there is nothing to plan.",
    REPLAY,
    "Create the TrayMove object now (tagged with job_index) and fill it in step by step; it joins the DAG later.",
    "Look the tray up and reject unknown or disabled trays. Note: this reads the request snapshot, not the scratch "
    "garage.",
    "A tray on a VECS that is charging must stop charging first; any other non-ready VECS state blocks the job.",
    "Choose the parking heading: an empty tray keeps its heading if that fits; a loaded tray faces the node's "
    "retrieval heading so a later retrieve is fast.",
    "If the tray is already at the destination pose, succeed without a move.",
    "Reject destinations that are a VECS not ready to charge, not in the graph, disabled for this tray, or a "
    "disabled bay.",
    "Apply the heading policy again for every known tray (EV-charge exception, then retrieval heading), then "
    "store the destination.",
    "Add the TrayMove to the DAG and chain it after this tray's previous event (rule A).",
    "If the destination is a bay or VECS, also wait for that resource's last event (rule C).",
    "Make the move wait for earlier events of the same job (rule B).",
],
"42_job_retrieve": [
    REPLAY,
    "Find the car. A car that does not exist cannot be retrieved.",
    "The car's node must not be disabled for its size.",
    "A car on a charging VECS must stop charging first; a VECS in another busy state means 'try later' "
    "(retain_job).",
    "Choose a bay: walk the layout's bay list from the back, skip unusable bays, take the first one already in "
    "retrieve mode, else remember the first one in insert mode or with a car inserted.",
    "No usable bay: fail and ask Dispatch to keep the job for later.",
    "If the chosen bay is not in retrieve mode yet, add the transition that switches it (chained to the bay, "
    "rule A).",
    "If a tray already occupies the bay, plan it out of the bay; its destination is left for tray assignment.",
    "Plan the car's tray into the bay, turned so the car faces the right way.",
    "Add the hand-over: the bay processes the retrieve once the tray is in.",
    "Report success; retain_job is false.",
],
"43_job_insert": [
    REPLAY,
    "The bay must exist and be enabled.",
    "There must be a tray in the bay, and it must carry a car: that is what is being inserted.",
    "Only these two bay states are accepted; anything else needs a different transition first.",
    "Make the tray reachable from the garage side: add a retrieve-mode transition for the bay on its first "
    "system floor.",
    "Plan the loaded tray out of the bay; where it parks is decided by tray assignment.",
    "Ask Dispatch (asynchronously) for a separate job that puts an empty tray back into this bay.",
    "Report success.",
    "Context, not this method: if the insert fails, Plan() asks Dispatch to clean the garage.",
],
"44_job_ready_for_insert": [
    REPLAY,
    "Only a bay in retrieve mode can be prepared for the next insert.",
    "Work out the bay's inbound pose and whether a tray is already inside.",
    "Empty bay: plan 'any empty tray -> this bay'. The tray is left blank for now.",
    "Bay holds a car: send it to a VECS first if it asked for charging, then plan an empty tray in. A car that "
    "did not ask for charging is moved later as a blocking tray.",
    "Bay already holds an empty tray: nothing to move.",
    "Try to fill the blank early: replay the DAG again and pick the nearest empty tray for this job's "
    "'? -> bay' moves. If none is found, leave it for tray assignment.",
    "Switch the bay to insert mode after the tray is in.",
    "Report success.",
],
"45_job_ready_for_retrieve": [
    REPLAY,
    "Only a bay in insert or retrieve mode can be prepared for retrieval.",
    "A bay in insert mode is switched to retrieve mode first.",
    "Check whether a tray sits in the bay.",
    "A car in the bay that asked for charging goes to a VECS.",
    "Any other tray is moved out of the bay, destination left for tray assignment.",
    "Report success. No final transition: the bay stays in retrieve mode.",
],
"46_job_clean_garage": [
    REPLAY,
    "Only the first successful job of a request hides AGVs: ask HideAgvs (motion_planner) for one hiding pose "
    "per AGV.",
    "If no hiding assignment exists, the job fails.",
    "Add one AgvMove per AGV that is not already hidden, chained per AGV (and per bay when hiding in a bay).",
    "Find trays left standing on waypoints by an earlier tier-2 stash.",
    "Plan each of them back into parking; destination left for tray assignment. Failures are only logged.",
    "Report success.",
],
"47_job_rebalance_garage": [
    REPLAY,
    "Ask which bays should switch to insert mode and which to retrieve mode, given the readiness ratio "
    "('Bays, VECS and VRCs').",
    "Run the READY_FOR_INSERT recipe for each bay that should accept cars, under this job's index.",
    "Run the READY_FOR_RETRIEVE recipe for each bay that should hand cars out, under this job's index.",
    "Report success; failures of individual bays are only logged.",
],
"48_job_charge_agv": [
    REPLAY,
    "The AGV must exist and be enabled.",
    "An AGV already on a charger, facing the charger's inbound heading, needs nothing.",
    "An AGV in a bay that is in insert mode is trapped: switch the bay to retrieve mode first. Any bay state "
    "other than these two fails the job.",
    "Cost every charger with no AGV on it by travel time, using a path search that avoids current obstacles; keep "
    "the cheapest.",
    "No reachable free charger: fail with a warning about the battery.",
    "Drive the AGV to the chosen charger (reuses PlanAgvMoveJob).",
    "If the AGV was trapped, put the bay back into insert mode (reuses PlanBayTransitionJob).",
],
"49_job_bay_transition": [
    REPLAY,
    "The bay must exist and be enabled.",
    "The bay's ODP collision area must be clear of AGVs and trays in the scratch garage.",
    "Insert mode can only be entered from retrieve mode.",
    "Retrieve mode needs a floor (the bay's first system floor) and starts from insert mode or a car inserted.",
    "Any other command is rejected.",
    "Add the bay transition, chained after the bay's previous event (rule A) and earlier events of the job "
    "(rule B).",
],
"50_job_charge_payload": [
    REPLAY,
    "Find the car and the tray it is on.",
    "If the tray already sits on an EV charging node whose VECS is ready, no move is needed.",
    "Otherwise search for a reachable VECS spot, reusing the open-space search of ResolveBlockingTrays.",
    "The search must have found a node, and that node must have a VECS (an EV_CHARGE node).",
    "Plan the tray onto the VECS (reuses PlanReparkTrayJob).",
    "Start charging once the tray is there.",
],
}


TAG_COL = {"ok": T.green, "skip": T.faint, "fail": T.red, "event": T.sky, "edge": T.fg2, "call": T.teal,
           "note": T.amber}


def step_table(d: Doc, x, y, w, steps, *, title="The method, step by step"):
    """steps: (code, general, scenario, tag_text, tag_kind). Returns bottom y."""
    c0, c4 = 34, 132
    rest = w - c0 - c4
    c1, c2 = 0.36 * rest, 0.34 * rest
    c3 = rest - c1 - c2
    d.text(x, y, title, size=13.5, weight=600, fill=T.fg)
    hy = y + 24
    xs = [x + c0, x + c0 + c1 + 10, x + c0 + c1 + c2 + 16, x + c0 + c1 + c2 + c3 + 12]
    for cx, lab in zip(xs, ["code (Scheduler::...)", "what the step does, in general", "in this example",
                            "result"]):
        d.text(cx, hy, lab, size=10.5, family="mono", weight=600, fill=T.muted, letter_spacing=0.4)
    yy = hy + 14
    for r, (code, gen, scen, tag, kind) in enumerate(steps):
        cl = []
        for part in code.split("\n"):
            cl += wrap(part, c1 - 12, 10.5, "mono")
        gl = wrap(gen, c2 - 14, 11, "sans")
        sl = wrap(scen, c3 - 14, 11, "sans")
        tl = wrap(tag, c4 - 20, 10.5, "mono") if tag else []
        n = max(len(cl), len(gl), len(sl), len(tl), 1)
        h = 12 + n * 15.5
        if r % 2 == 0:
            d.rect(x, yy, w, h, rx=5, fill=T.tint(T.card, 0.55, T.bg), layer="bg")
        num_badge(d, x + 15, yy + 14, r + 1, T.tint(T.fg2, 0.85, T.bg), r=10)
        for j, ln in enumerate(cl):
            d.text(xs[0], yy + 14 + j * 15.5, ln, size=10.5, family="mono", fill=T.fg2)
        for j, ln in enumerate(gl):
            d.text(xs[1], yy + 14 + j * 15.5, ln, size=11, fill=T.fg2)
        for j, ln in enumerate(sl):
            d.text(xs[2], yy + 14 + j * 15.5, ln, size=11, fill=T.fg if kind != "skip" else T.muted)
        if tag:
            col = TAG_COL.get(kind, T.fg2)
            for j, ln in enumerate(tl):
                label_pill(d, xs[3], yy + 14 + j * 18, ln, color=col, size=10.5, anchor="start",
                           bg=T.tint(col, 0.12, T.bg), border=T.tint(col, 0.6, T.bg))
        yy += h + 2
    return yy


def notes_row(d: Doc, x, y, w, items, gap=18):
    n = len(items)
    cw = (w - gap * (n - 1)) / n
    bot = y
    for i, (title, text, acc) in enumerate(items):
        b = note(d, x + i * (cw + gap), y, cw, text, title=title, accent=acc)
        bot = max(bot, b.y1)
    return bot


REGIONS = {"qa": (QA_X, QA_Y), "full": (FULL_X, FULL_Y), "mid": (FULL_X, (9.2, 25.2))}


def job_figure(name, *, heading, subtitle, req, region, draw_map, map_caption, events, edges, steps,
               notes=(), outside=(), legend_extra=(), bw=320, badge="yaml+hyp", request_title="Request", scale=None,
               legend_override=None, events_title="Events appended to ctx->events",
               events_sub="numbered in creation order; arrows = edges this method adds"):
    d = Doc(name, heading, subtitle)
    xl, yl = REGIONS[region]
    s = W / (xl[1] - xl[0])
    m = Map(d, 0, 0, s, xl, yl)
    m.base(labels=True, zones=False, axes=False)
    draw_map(d, m)
    mb = m.box
    d.text(0, -16, map_caption, size=12.5, family="mono", weight=600, fill=T.fg2)
    y2 = mb.y1 + 44
    lw = 470
    rc = request_card(d, 0, y2, lw, req, title=request_title)
    yl_ = rc.y1
    for title, text in outside:
        b = note(d, 0, yl_ + 18, lw, text, title=title, accent=T.teal)
        yl_ = b.y1
    ex = lw + 50
    d.text(ex, y2 + 8, events_title, size=13, weight=600, fill=T.fg)
    d.text(ex, y2 + 27, events_sub, size=11, fill=T.muted)
    if events:
        boxes = event_column(d, ex, y2 + 50, events, edges, bw=bw)
        yr = boxes[-1].y1
    else:
        yr = y2 + 50
    y = max(yl_, yr) + 46
    gens = GENERAL.get(name, [""] * len(steps))
    assert len(gens) == len(steps), (name, len(gens), len(steps))
    steps = [(c, g, sc, t, k) for (c, sc, t, k), g in zip(steps, gens)]
    y = step_table(d, 0, y, W, steps)
    if notes:
        y = notes_row(d, 0, y + 22, W, notes)
    legend = [("box", TRAY, "TrayMove"), ("box", AGV, "AgvMove"), ("box", BAYC, "BayTransition"),
              ("box", VECS, "VecsTransition"), ("arrow", T.fg2, "rule A: same entity (colour = entity)"),
              ("dasharrow", RULE_B, "rule B: earlier leaf of the same job"),
              ("dasharrow", BAYC, "rule C: into a bay / VECS"), ("ring", T.fg2, "? = left for DoTrayAssignments")]
    if legend_override is not None:
        legend = legend_override
    frame(d, title=heading, subtitle=subtitle, badge_key=badge, legend=list(legend) + list(legend_extra))
    return d


# ======================================================================================
# 36 — the expansion loop in Plan()
# ======================================================================================

@figure("36_expansion_loop", "Job expansion: the loop in Plan()", DOC1)
def expansion_loop():
    d = Doc("36_expansion_loop", "Job expansion: the loop in Plan(), step by step",
            "Three pending jobs. Each row shows the code that runs for one loop iteration and the three containers "
            "after it. One job can create several events; all of them carry that job's index.")
    CX = {"code": 0, "jobs": 384, "ev": 602, "res": 960}
    CW = {"jobs": 198, "ev": 338, "res": 160}
    for t, k in (("loop iteration and the code that runs", "code"), ("plan_ctx->scheduled_jobs", "jobs"),
                 ("plan_ctx->events  (one box = one event)", "ev"), ("result.scheduled_jobs", "res")):
        d.text(CX[k], 0, t, size=11.5, family="mono", weight=600, fill=T.muted)

    def jobs_box(y, items, h):
        x = CX["jobs"]
        d.rect(x, y, CW["jobs"], h, rx=8, fill=T.bg_deep, stroke=T.tint(T.green, 0.5, T.bg), sw=1.1)
        if not items:
            d.text(x + 12, y + 18, "{ }  size() = 0", size=11, family="mono", fill=T.faint)
            return
        for k, (lab, new) in enumerate(items):
            yy = y + 18 + k * 22
            d.text(x + 12, yy, f"[{k}]", size=11, family="mono", weight=700, fill=T.green)
            d.text(x + 44, yy, lab, size=11, family="mono", fill=T.fg if new else T.fg2)
            if new:
                label_pill(d, x + CW["jobs"] - 10, yy, "new", color=T.green, size=9.5, anchor="end",
                           bg=T.tint(T.green, 0.15, T.bg))
        d.text(x + 12, y + h - 12, f"size() = {len(items)}", size=10.5, family="mono", fill=T.muted)

    EW, EH = 150, 34

    def events_box(y, groups, h):
        """groups: list of (title, [(kind, text, job)], new)."""
        x = CX["ev"]
        d.rect(x, y, CW["ev"], h, rx=8, fill=T.bg_deep, stroke=T.tint(T.amber, 0.5, T.bg), sw=1.1)
        if not groups:
            d.text(x + 12, y + 18, "empty DAG", size=11, family="mono", fill=T.faint)
            return
        gy = y + 8
        for title, evs, new in groups:
            rows = (len(evs) + 1) // 2
            gh = 20 + rows * (EH + 6)
            d.rect(x + 6, gy, CW["ev"] - 12, gh, rx=7, fill="none",
                   stroke=T.tint(T.fg2, 0.55 if new else 0.25, T.bg), sw=1, dash="4 3")
            d.text(x + 14, gy + 10, title, size=9.5, family="mono", fill=T.fg2 if new else T.faint)
            for k, (kind, text, job) in enumerate(evs):
                col = EVENT_COLOR[kind]
                ex, ey = x + 14 + (k % 2) * (EW + 8), gy + 18 + (k // 2) * (EH + 6)
                d.rect(ex, ey, EW, EH, rx=6, fill=T.card, stroke=col, sw=1.5 if new else 1,
                       opacity=None if new else 0.55)
                d.text(ex + 8, ey + 11, text, size=9.5, family="mono", fill=T.fg if new else T.muted)
                d.text(ex + 8, ey + 25, f"job_index = {job}", size=9.5, family="mono", weight=700, fill=col)
            gy += gh + 6

    def ev_height(groups):
        return 16 + sum(20 + ((len(e) + 1) // 2) * (EH + 6) + 6 for _, e, _ in groups)

    def result_box(y, items, h):
        x = CX["res"]
        d.rect(x, y, CW["res"], h, rx=8, fill=T.bg_deep, stroke=T.tint(T.red, 0.45, T.bg), sw=1.1)
        if not items:
            d.text(x + 12, y + 18, "{ }", size=11, family="mono", fill=T.faint)
        for k, (lab, col) in enumerate(items):
            d.text(x + 12, y + 18 + k * 22, lab, size=10.5, family="mono", fill=col)

    RET = [("BayTransition", "B21 TO_RETRIEVE", 0), ("TrayMove", "T21: B21 -> ?", 0),
           ("TrayMove", "T17: P17 -> B21", 0), ("BayTransition", "B21 PROCESS_RETRIEVE", 0)]
    G_RET = "PlanRetrieveJob(.., 0) made these 4"
    G_REP = "PlanReparkTrayJob(.., 1) made this 1"
    REP = [("TrayMove", "T19: P19 -> P24", 1)]
    rows = [
        ("before the loop", [
            ("plan_ctx built from request_data.base_state", T.fg2),
            ("pending_jobs = [RETRIEVE, INSERT, REPARK_TRAY]", T.fg2)],
         [], [], [], None),
        ("i = 0  ·  TYPE_RETRIEVE (car on T17)", [
            ("job_index = scheduled_jobs.size()  -> 0", T.teal),
            ("PlanRetrieveJob(plan_ctx, job.payload_id, 0)", T.sky),
            ("-> success. ONE job, FOUR events, each", T.green),
            ("   constructed with job_index 0", T.green),
            ("plan_ctx->PushBackScheduledJob(job)  -> [0]", T.sky)],
         [("RETRIEVE", True)], [(G_RET, RET, True)], [], T.green),
        ("i = 1  ·  TYPE_INSERT (bay B7)", [
            ("job_index = scheduled_jobs.size()  -> 1", T.teal),
            ("PlanInsertJob(plan_ctx, job.bay_id, 1)", T.sky),
            ("-> fails before adding any event:", T.red),
            ("   \"... the bay has no tray in discrete state.\"", T.red),
            ("result.scheduled_jobs.push_back(FailJob(job, msg))", T.sky),
            ("clean_garage_request_fn_()   // INSERT only", T.sky)],
         [("RETRIEVE", False)], [(G_RET, RET, False)], [("INSERT  STATE_ERROR", T.red)], T.red),
        ("i = 2  ·  TYPE_REPARK_TRAY (T19 -> P24)", [
            ("job_index = scheduled_jobs.size()  -> 1   (again)", T.teal),
            ("PlanReparkTrayJob(plan_ctx, job.tray_id, 1, ...)", T.sky),
            ("-> success. ONE job, ONE event, job_index 1", T.green),
            ("plan_ctx->PushBackScheduledJob(job)  -> [1]", T.sky)],
         [("RETRIEVE", False), ("REPARK_TRAY", True)], [(G_RET, RET, False), (G_REP, REP, True)],
         [("INSERT  STATE_ERROR", T.red)], T.green),
    ]
    y = 22
    for title, code, jobs, groups, res, col in rows:
        h = max(18 + len(code) * 19 + 26, ev_height(groups) + 16, 96)
        d.rect(-10, y, W + 20, h, rx=10, fill=T.tint(T.card, 0.45, T.bg), layer="bg")
        if col:
            d.rect(-10, y, 4, h, rx=2, fill=col, layer="bg")
        d.text(0, y + 16, title, size=12.5, family="mono", weight=700, fill=T.fg)
        for k, (ln, c) in enumerate(code):
            d.text(0, y + 38 + k * 19, ln, size=10.5, family="mono", fill=c)
        jobs_box(y + 8, jobs, h - 16)
        events_box(y + 8, groups, h - 16)
        result_box(y + 8, res, h - 16)
        y += h + 12

    # ---- one job -> many events -> many actions ----
    y += 14
    d.text(0, y, "One job, many events, many actions: how the index ties them together to the end", size=13,
           weight=600, fill=T.fg)
    y += 16
    h = 214
    d.rect(-10, y, W + 20, h, rx=10, fill=T.tint(T.sky, 0.05, T.bg), stroke=T.tint(T.sky, 0.35, T.bg), sw=1,
           layer="bg")
    stages = [
        ("job", ["scheduled_jobs[0]", "RETRIEVE", "guid = g_ret"], T.green, 0, 170),
        ("after job expansion", ["4 events", "job_index = 0"], T.amber, 200, 190),
        ("after tray + AGV assignment", ["the 4, plus any blocker", "TrayMoves and AgvMoves", "(approach, lift, lower)",
                                          "all job_index = 0"], T.amber, 420, 240),
        ("in the response", ["N ActionNodes,", "job_id = g_ret", "node_indices = [..]"], T.sky, 690, 200),
    ]
    by = y + 34
    prev = None
    for title, lines, col, x, w in stages:
        bh = 30 + 17 * len(lines)
        d.text(x + 10, by - 10, title, size=10.5, family="mono", weight=600, fill=T.muted)
        d.rect(x + 10, by, w, bh, rx=8, fill=T.card, stroke=col, sw=1.4)
        for k, ln in enumerate(lines):
            d.text(x + 22, by + 18 + k * 17, ln, size=10.5, family="mono", fill=T.fg)
        if prev:
            connect(d, [(prev, by + 24), (x + 10, by + 24)], kind="flow", color=T.faint, size=8, sw=1.4)
        prev = x + 10 + w
    d.text(910, by + 6, "lookup in ToActionNode():", size=10, family="mono", fill=T.faint)
    d.text(910, by + 22, "scheduled_jobs[", size=10, family="mono", fill=T.faint)
    d.text(910, by + 38, "  event->GetJobIndex()]", size=10, family="mono", fill=T.faint)
    d.text(910, by + 54, "  .job.guid", size=10, family="mono", fill=T.faint)
    lines = [("Later stages keep the tag: a blocker TrayMove is built as TrayMove(move->GetJobIndex()) and an AGV "
              "approach as AgvMove(root_event->GetJobIndex(), ...), so they belong to the job whose move needed them.",
              T.fg2),
             ("Final result.scheduled_jobs = [INSERT STATE_ERROR, RETRIEVE STATE_EXECUTING, REPARK_TRAY "
              "STATE_EXECUTING]: failures first, in loop order, then successes with their node_indices.", T.fg),
             ("Why size() and not i: the index must point into scheduled_jobs, which only holds successful jobs. "
              "With i, the REPARK's event would say 2, and scheduled_jobs[2] does not exist.", T.amber)]
    yy = by + 112
    for t, c in lines:
        for ln in wrap(t, W - 20, 11.5):
            d.text(10, yy, ln, size=11.5, fill=c)
            yy += 17
        yy += 4
    frame(d, title="Job expansion: the loop in Plan(), step by step",
          subtitle="job_index is the job's position in plan_ctx->scheduled_jobs (jobs that have succeeded so far), "
                   "not its position in the request (i). A job usually creates several events; every one of them is "
                   "constructed with the same job_index, and so are the events later stages add for that job.",
          badge_key="as-built",
          legend=[("box", TRAY, "TrayMove"), ("box", BAYC, "BayTransition"), ("dashbox", T.fg2, "events made by one job call"),
                  ("fill", T.green, "job succeeded"), ("fill", T.red, "job failed"),
                  ("fill", T.teal, "where job_index comes from")])
    return d


# ======================================================================================
# 37 — building blocks matrix (computed from scheduler.cpp)
# ======================================================================================

ENTRY_METHODS = ["PlanAgvMoveJob", "PlanRetrieveJob", "PlanReparkTrayJob", "PlanInsertJob", "PlanReadyForInsertJob",
                 "PlanReadyForRetrieveJob", "PlanCleanGarageJob", "PlanUnstashWaypointTraysJob",
                 "PlanRebalanceGarageJob", "PlanAgvChargeJob", "PlanBayTransitionJob", "PlanChargePayloadJob",
                 "PlanOpenBayDoor"]
JOB_TYPES = {"PlanAgvMoveJob": "MOVE_AGV", "PlanRetrieveJob": "RETRIEVE", "PlanReparkTrayJob": "REPARK_TRAY, MOVE_TRAY",
             "PlanInsertJob": "INSERT", "PlanReadyForInsertJob": "READY_FOR_INSERT",
             "PlanReadyForRetrieveJob": "READY_FOR_RETRIEVE", "PlanCleanGarageJob": "CLEAN_GARAGE",
             "PlanUnstashWaypointTraysJob": "(helper)", "PlanRebalanceGarageJob": "REBALANCE_GARAGE",
             "PlanAgvChargeJob": "CHARGE_AGV", "PlanBayTransitionJob": "TRANSITION_BAY_TO_*",
             "PlanChargePayloadJob": "CHARGE_PAYLOAD", "PlanOpenBayDoor": "(helper)"}
CALL_COLS = ["PlanReparkTrayJob", "PlanAgvMoveJob", "PlanBayTransitionJob", "PlanOpenBayDoor", "PlanChargePayloadJob",
             "PlanReadyForInsertJob", "PlanReadyForRetrieveJob", "PlanUnstashWaypointTraysJob", "ResolveBlockingTrays",
             "AssignTrayIdForEmptyMove", "UsePreferredHeading", "UseEvChargeHeading", "HideAgvs",
             "ComputeBayRebalancingActions"]
SHORT = {"PlanReparkTrayJob": "Repark", "PlanAgvMoveJob": "AgvMove", "PlanBayTransitionJob": "BayTrans",
         "PlanOpenBayDoor": "OpenDoor", "PlanChargePayloadJob": "ChgPay", "PlanReadyForInsertJob": "RdyIns",
         "PlanReadyForRetrieveJob": "RdyRet", "PlanUnstashWaypointTraysJob": "Unstash",
         "ResolveBlockingTrays": "Resolve", "AssignTrayIdForEmptyMove": "EmptyTray", "UsePreferredHeading": "PrefHdg",
         "UseEvChargeHeading": "EvHdg", "HideAgvs": "Hide", "ComputeBayRebalancingActions": "Rebal"}
MAKE_COLS = [("TrayMove", "TrayMove"), ("AgvMove", "AgvMove"), ("BayTransition", "BayTransition"),
             ("VecsTransition", "VecsTransition")]


def job_method_bodies():
    src = _strip_comments(_source_files()["src/scheduler.cpp"])
    out = {}
    for name in ENTRY_METHODS:
        m = re.search(r"Scheduler::" + name + r"\(", src)
        i = src.index("{", m.end())
        depth, j = 0, i
        while True:
            if src[j] == "{":
                depth += 1
            elif src[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out[name] = src[i:j + 1]
    return out


@figure("37_job_building_blocks", "Job methods and their building blocks", DOC1)
def building_blocks():
    d = Doc("37_job_building_blocks", "Job methods are built from a few shared pieces",
            "Matrix computed from scheduler.cpp: which job methods each Plan<Type>Job calls, which events it creates "
            "itself, and which edge rules it applies itself.")
    bodies = job_method_bodies()
    name_w, cw, rh = 290, 50, 30
    cols = [(c, "call") for c in CALL_COLS] + [(k, "make") for k, _ in MAKE_COLS] + [("A", "rule"), ("B", "rule")]
    # group header
    groups = [("calls", len(CALL_COLS), T.teal), ("creates directly", len(MAKE_COLS), T.amber),
              ("edge rules", 2, T.fg2)]
    x = name_w
    for g, n, col in groups:
        d.rect(x + 2, 0, n * cw - 4, 22, rx=6, fill=T.tint(col, 0.16, T.bg), stroke=T.tint(col, 0.6, T.bg), sw=1)
        d.text(x + n * cw / 2, 11, g, size=11, weight=600, fill=col, anchor="middle")
        x += n * cw
    for i, (c, kind) in enumerate(cols):
        cx = name_w + i * cw + cw / 2
        lab = SHORT.get(c, {"TrayMove": "Tray", "AgvMove": "Agv", "BayTransition": "Bay", "VecsTransition": "Vecs"}.get(c, c))
        d.text(cx, 40, lab, size=10.5, family="mono", weight=600, fill=T.fg2, anchor="middle")
    y = 62
    for r, name in enumerate(ENTRY_METHODS):
        b = bodies[name]
        if r % 2 == 0:
            d.rect(0, y - 4, name_w + len(cols) * cw, rh, rx=4, fill=T.tint(T.card, 0.6, T.bg), layer="bg")
        d.text(0, y + 7, name + "()", size=11.5, family="mono", weight=600, fill=T.fg)
        d.text(0, y + 21, JOB_TYPES[name], size=9.5, family="mono", fill=T.muted)
        for i, (c, kind) in enumerate(cols):
            cx = name_w + i * cw + cw / 2
            if kind == "call":
                hit = re.search(r"\b" + c + r"\(", b) is not None and c != name
                col = T.teal
            elif kind == "make":
                hit = re.search(r"make_shared<(volley::)?" + c + r">", b) is not None
                col = EVENT_COLOR[c]
            else:
                tok = "UpdateLastEntityEvent" if c == "A" else "UpdateLeafDependencies"
                hit = tok in b
                col = T.fg2
            if hit:
                d.circle(cx, y + 11, 7, fill=col)
            else:
                d.circle(cx, y + 11, 2, fill=T.border_soft)
        y += rh
    d.text(0, y + 14, "Column key: Repark = PlanReparkTrayJob, OpenDoor = PlanOpenBayDoor, ChgPay = PlanChargePayloadJob, "
                      "RdyIns / RdyRet = PlanReadyFor{Insert,Retrieve}Job, Resolve = ResolveBlockingTrays,",
           size=10.5, fill=T.muted)
    d.text(0, y + 30, "EmptyTray = AssignTrayIdForEmptyMove, PrefHdg / EvHdg = UsePreferredHeading / UseEvChargeHeading, "
                      "Hide = volley::HideAgvs, Rebal = ComputeBayRebalancingActions.", size=10.5, fill=T.muted)
    frame(d, title="Job methods are built from a few shared pieces",
          subtitle="Read a row to see what one job method does itself and what it delegates. PlanReparkTrayJob is the "
                   "workhorse: six other methods create their TrayMoves through it, so rule C and the heading policy "
                   "live in one place.",
          badge_key="as-built",
          legend=[("dot", T.teal, "calls"), ("dot", TRAY, "make_shared<TrayMove>"), ("dot", AGV, "AgvMove"),
                  ("dot", BAYC, "BayTransition"), ("dot", VECS, "VecsTransition"),
                  ("dot", T.fg2, "applies rule A / B itself")],
          footnote="Generated by scripts/diagrams/fig_jobs.py from sources/repomix-scheduler.xml (comments stripped, "
                   "text match on each method body). Calls made by a callee are not repeated on the caller's row.")
    return d


# ======================================================================================
# per-job scenario figures
# ======================================================================================

def bay_events(d: Doc, m: Map, nid: int, items, *, dy=0, dx=0):
    """Numbered BayTransition / VecsTransition markers stacked under a bay (or node)."""
    x, y = m.P(nid)
    y0 = y + (STALL_W + 0.9) * m.s / 2 + 16 + dy
    for k, (n, text, col) in enumerate(items):
        yy = y0 + k * 24
        num_badge(d, x - 50 + dx, yy, n, col, r=10)
        d.text(x - 36 + dx, yy, text, size=10.5, family="mono", fill=col, halo=T.bg_deep, halo_w=3)


@figure("42_job_retrieve", "TYPE_RETRIEVE: PlanRetrieveJob", DOC1)
def job_retrieve():
    def draw(d, m):
        m.tray(15, "T15", chip_pos="bl")
        m.tray(17, "T17", payload=True, emphasis=True, chip_pos="bl")
        m.tray(20, "T20", payload=True, chip_pos="bl")
        m.tray(21, "T21", chip_pos="tr")
        m.agv(11, "AGV A", heading=90, label_side="above")
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")
        bay_pill(d, m, 7, "B7 disabled", color=T.red)
        intent(d, m, 21, None, 2, TRAY, q_off=(118, -30), bend=0.1, num_t=0.78, src_off=(30, -8))
        intent(d, m, 17, 21, 3, TRAY, bend=-0.16, dst_off=(40, -6), src_off=(-20, 0), num_t=0.62)
        bay_events(d, m, 21, [(1, "TRANSITION_TO_RETRIEVE", BAYC), (4, "PROCESS_RETRIEVE", BAYC)], dx=10)

    return job_figure(
        "42_job_retrieve", heading="TYPE_RETRIEVE  ->  PlanRetrieveJob()",
        subtitle="Bring the car on tray T17 to a customer bay. The method picks the bay, opens it for retrieval, "
                 "plans the empty tray out and the car's tray in, then hands the car over.",
        req=[("job.type", "TYPE_RETRIEVE"), ("job.payload_id", "<GUID of the car on T17>"),
             ("job_index", "0 (first job, DAG empty)"),
             ("call", "PlanRetrieveJob(plan_ctx, job.payload_id, 0)"),
             ("returns", "tuple<bool, string, bool retain_job>")],
        region="mid", draw_map=draw, map_caption="working_state at the start of the job (= request)",
        events=[("BayTransition", "B21: TRANSITION_TO_RETRIEVE", 0, "solid"),
                ("TrayMove", "T21: B21 -> ?", 0, "solid", "via PlanReparkTrayJob, no destination"),
                ("TrayMove", "T17: P17 -> B21", 0, "solid", "via PlanReparkTrayJob, heading set"),
                ("BayTransition", "B21: PROCESS_RETRIEVE", 0, "solid")],
        edges=[(1, 2, "B", "bay"), (2, 3, "B", "bay"), (3, 4, "B", "bay"), (1, 3, "C", "bay", "C · B21"),
               (1, 4, "A", "bay", "A · B21")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);",
             "First job, so the DAG is empty and working_state equals the request.", "replay", "ok"),
            ("payload_opt = working_state.GetPayload(payload_id)", "The car is on tray T17 at P17.", "found", "ok"),
            ("disabledness_filters[payload].IsEnabled(tray node)", "P17 is not disabled.", "passes", "ok"),
            ("GetVecs(tray node): CHARGING -> add VecsTransition (stop);\nother non-ready state -> fail, retain_job",
             "P17 has no VECS.", "skipped", "skip"),
            ("for bay in reverse(layout_->GetBayPrioritization()):\n  skip disabled / window too small;\n"
             "  READY_TO_RETRIEVE -> take it, stop;\n  else remember first READY_TO_INSERT\n  or VEHICLE_INSERTED",
             "Assume the layout prioritises [B7, B21]. Walking from the back: B21 is READY_TO_INSERT, so it is "
             "remembered; B7 is disabled and skipped. No bay is READY_TO_RETRIEVE, so B21 is used.",
             "bay = B21", "ok"),
            ("no bay -> return {false, \"No Bay available\", true}", "A bay was found.", "skipped", "skip"),
            ("bay READY_TO_INSERT or VEHICLE_INSERTED ->\n  BayTransition(TRANSITION_TO_RETRIEVE); rule A",
             "B21 must switch to retrieve mode before trays can go in or out on the garage side.", "adds 1", "event"),
            ("GetTrayOnNode(bay) -> PlanReparkTrayJob(ctx, tray,\n  job_index, allow_recip = true)   // no dest",
             "Empty tray T21 occupies B21. It must leave first; where it goes is decided later.",
             "adds 2 · rule B", "event"),
            ("dest = {bay id, GetBayInboundHeading(bay)}, flipped\n  unless payload.reciprocal_to_tray;\n"
             "PlanReparkTrayJob(ctx, payload tray, job_index,\n  false, dest)",
             "T17 goes into B21, turned so the car faces the right way for the customer. Inside the call: rule B "
             "(after 2) and rule C (after B21's last event, 1).", "adds 3 · B, C", "event"),
            ("BayTransition(PROCESS_RETRIEVE);\nUpdateLastEntityEvent (A); UpdateLeafDependencies (B)",
             "The bay hands the car over once T17 is inside.", "adds 4 · A, B", "event"),
            ("return {true, \"\", false}", "Plan() pushes the job onto plan_ctx->scheduled_jobs.", "success", "ok"),
        ],
        notes=[("Why two tray moves?", "A bay holds one tray. The empty tray T21 has to leave before T17 can enter, "
                "so the method plans that move explicitly instead of leaving it to the blocking-tray search.", T.amber),
               ("retain_job", "Only RETRIEVE returns a third value. When no bay is available, or the payload sits "
                "on a VECS in an unexpected state, it is true: FailJob() copies it so Dispatch keeps the job and "
                "retries later.", T.sky),
               ("Not decided yet", "Where T21 parks, which trays block T17's path, which AGV does the work and the "
                "exact route are all chosen by the later stages (sections 15 to 18).", T.border)],
        bw=300)


def cost_tag(d, m, nid, text, color, *, dx=0, dy=-26):
    k = m.s / 21
    dx, dy = dx * k, dy * k
    x, y = m.P(nid)
    label_pill(d, x + dx, y + dy, text, color=color, bg=T.bg_deep, border=color, size=10)


# --------------------------------------------------------------------------------------
@figure("40_job_move_agv", "TYPE_MOVE_AGV: PlanAgvMoveJob", DOC1)
def job_move_agv():
    def draw(d, m):
        m.agv(26, "A (empty)", heading=90, label_side="above")
        m.tray(18, "", chip_pos="bl")
        m.agv(18, "B carries T9", heading=90, label_side="left", lifted=True)
        m.tray(15, "T15", chip_pos="bl")
        m.tray(20, "T20", payload=True, chip_pos="bl")
        agv_intent(d, m, 26, 13, 1, bend=0.25, num_t=0.45)
        intent(d, m, 18, 24, 2, TRAY, bend=-0.25, src_off=(30, -6), num_t=0.55)
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")

    return job_figure(
        "40_job_move_agv", heading="TYPE_MOVE_AGV  ->  PlanAgvMoveJob()",
        subtitle="Two MOVE_AGV jobs in one request. An empty AGV produces an AgvMove; an AGV that is carrying a tray "
                 "produces a TrayMove whose AGV is already fixed.",
        req=[("job 0", "TYPE_MOVE_AGV, agv_id = A, destination = {node_id: 13, heading: 90}"),
             ("job 1", "TYPE_MOVE_AGV, agv_id = B, destination = {node_id: 24, heading: 90}"),
             ("call", "PlanAgvMoveJob(plan_ctx, job.agv_id,\n  job.destination, false, job_index)"),
             ("returns", "BoolStringPair {success, message}")],
        region="qa", draw_map=draw, map_caption="request state (job 1 also sees A at W13 after replay)",
        events=[("AgvMove", "AGV A: {node_id: 26, heading: 90} -> {node_id: 13, heading: 90}", 0, "solid"),
                ("TrayMove", "T9: W18 -> P24, agv = B", 1, "solid", "AGV preset by SetAgvId(); heading may change")],
        edges=[],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);",
             "Job 0: empty DAG. Job 1: replays event 1, so A is already at W13.", "replay", "ok"),
            ("if(!agv_id) return {false, \"... not yet supported\"}",
             "Both jobs name an AGV. Moving 'any AGV' is a TODO.", "passes", "ok"),
            ("agv_opt = working_state.GetAgv(*agv_id);\nmissing or disabled -> fail", "A and B exist and are enabled.",
             "passes", "ok"),
            ("agv_opt->pose == dest -> return {true, \"\"}", "Neither AGV is at its destination.",
             "no early exit", "skip"),
            ("pose_change = {current node+heading -> dest};\ndest vertex must exist and be enabled for\n"
             "CollisionEntityIdFromAgvState(agv)",
             "The collision entity depends on whether the AGV carries a tray. W13 and P24 are enabled.", "passes", "ok"),
            ("if(allow_recip && IsAngleOrReciprocal(...))\n  next = current pose",
             "Plan() and PlanAgvChargeJob() both pass false, so this branch never runs (and would turn the move "
             "into a no-op if it did).", "never taken", "skip"),
            ("agv.tray_id == 0 -> AgvMove(job_index, pose_change);\nUpdateLastEntityEvent(AGV)  // rule A",
             "Job 0: A is empty. A has no earlier event, so rule A adds no edge.", "adds 1", "event"),
            ("else -> TrayMove: SetTrayId, SetAgvId(agv);\nflip dest if AGV and tray headings are reciprocal;\n"
             "UsePreferredHeading; SetDest; rule A (tray)",
             "Job 1: B carries T9. The destination is converted from AGV to tray heading, then the parking "
             "heading policy may change it.", "adds 2", "event"),
            ("UpdateLeafDependencies(new_event, job_index)", "Each job has only one event: no rule B edge.",
             "no edge", "skip"),
        ],
        notes=[("No edges here", "The two events belong to different jobs and touch different entities, so "
                "nothing orders them yet. Occupancy edges (who must leave a node first) are added by the later "
                "stages.", T.border),
               ("A TrayMove with an AGV", "This is the only job method that creates a TrayMove with the AGV "
                "already set: the tray is on that AGV, so no other AGV can carry it.", T.amber),
               ("Not checked here", "Whether the path is free, whether other AGVs are in the way and how long "
                "the move takes. Those come from motion planning.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("41_job_repark_tray", "TYPE_REPARK_TRAY / MOVE_TRAY: PlanReparkTrayJob", DOC1)
def job_repark():
    def draw(d, m):
        m.tray(19, "T19", payload=True, emphasis=True, chip_pos="bl")
        ghost(d, m, 24, "")
        d.text(m.P(24)[0] + 20, m.P(24)[1] - 4, "T19 after job 0", size=10.5, family="mono", fill=TRAY, anchor="middle",
               halo=T.bg_deep, halo_w=3)
        m.tray(15, "T15", chip_pos="bl")
        m.tray(17, "T17", payload=True, chip_pos="bl")
        intent(d, m, 19, 24, 1, TRAY, bend=-0.3, num_t=0.5)
        intent(d, m, 24, 23, 2, TRAY, bend=0.45, num_t=0.5)
        bay_pill(d, m, 21, "B21 READY_TO_RETRIEVE")

    return job_figure(
        "41_job_repark_tray", heading="TYPE_REPARK_TRAY / TYPE_MOVE_TRAY  ->  PlanReparkTrayJob()",
        subtitle="Move one tray to a parking node. Two jobs move the same tray, so rule A chains them. Six other "
                 "job methods create their tray moves through this method.",
        req=[("job 0", "TYPE_REPARK_TRAY, tray_id = 19, destination = P24,\n  allow_reciprocal = true"),
             ("job 1", "TYPE_MOVE_TRAY, tray_id = 19, destination = P23"),
             ("call", "PlanReparkTrayJob(plan_ctx, job.tray_id, job_index,\n  job.allow_reciprocal, job.destination)"),
             ("note", "from Plan() the destination is always present")],
        region="qa", draw_map=draw, map_caption="request state; dashed = where job 0 leaves T19",
        events=[("TrayMove", "T19: P19 -> P24@retrieval", 0, "solid", "heading = gg_.GetRetrievalHeading(P24)"),
                ("TrayMove", "T19: P24 -> P23", 1, "solid")],
        edges=[(1, 2, "A", "tray", "A · T19")],
        steps=[
            ("if(!tray_id && !dest) return {false, ...}", "Both are given.", "passes", "ok"),
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);",
             "Job 1 replays event 1, so working_state has T19 at P24.", "replay", "ok"),
            ("auto tray_move = make_shared<TrayMove>(job_index)", "Created now, added to the DAG at step 10.",
             "not in DAG yet", "skip"),
            ("tray_opt = ctx->initial_state.GetTray(*tray_id)\n// initial_state, not working_state\n"
             "missing or disabled -> fail",
             "Both jobs read T19 at P19, the request position, even though job 1's working_state has it at P24.",
             "passes", "note"),
            ("VECS at the tray's request node (working_state):\n  CHARGING -> add VecsTransition(stop), no rule A/B;\n"
             "  other non-ready state -> fail", "P19 has no VECS.", "skipped", "skip"),
            ("if dest is a plain parking node && allow_recip:\n  empty tray -> keep current heading if same or "
             "opposite;\n  loaded tray -> node's retrieval heading (flipped\n  if payload.reciprocal_to_tray)",
             "Job 0: P24 is parking and T19 carries a car, so the heading becomes P24's retrieval heading. "
             "Job 1 has allow_reciprocal = false.", "heading set", "ok"),
            ("tray_opt->pose == dest -> return {true, \"\"}",
             "Compares with the request position (step 4). Neither job is a no-op.", "no early exit", "skip"),
            ("dest VECS not READY_TO_CHARGE -> fail;\ndest vertex must exist and be enabled for the\n"
             "tray's collision entity; dest bay disabled -> fail", "P24 and P23 are plain, enabled parking.",
             "passes", "ok"),
            ("UsePreferredHeading(dst, payload, tray); SetDest",
             "T19 is loaded, so the retrieval heading of P24 (job 0) or P23 (job 1) is used if that node has a feasible "
             "one; Pecos is not 576_eccles, so the EV exception does nothing.",
             "dest set", "ok"),
            ("ctx->events.AddEvent(tray_move);\nUpdateLastEntityEvent(tray)  // rule A",
             "Job 0: T19 has no earlier event. Job 1: T19's last event is 1, so edge 1 -> 2.", "adds 1, 2 · A", "event"),
            ("dest is a bay  -> AddDependency(last bay event, move)\ndest is a VECS -> AddDependency(last VECS "
             "event, move)", "Neither destination is a bay or VECS.", "rule C skipped", "skip"),
            ("UpdateLeafDependencies(tray_move, job_index)", "Each job has one event: no rule B edge.", "no edge",
             "skip"),
        ],
        notes=[("When is the destination '?'", "Never from Plan(): job.destination is always passed. Internal callers "
                "(RETRIEVE, INSERT, READY_FOR_RETRIEVE, the unstash helper) call it without a destination, and "
                "DoTrayAssignments() chooses one later.", T.amber),
               ("initial_state, not working_state", "The tray lookup in step 4 uses the request snapshot. A later "
                "job moving the same tray is still planned correctly (rule A orders it), but the 'already there' "
                "check compares against the old position.", T.sky),
               ("allow_reciprocal", "For a loaded tray, step 9 sets the retrieval heading anyway, so the flag "
                "mostly matters for empty trays.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("43_job_insert", "TYPE_INSERT: PlanInsertJob", DOC1)
def job_insert():
    def draw(d, m):
        m.tray(21, "T21", payload=True, emphasis=True, chip_pos="tr")
        bay_pill(d, m, 21, "B21 VEHICLE_INSERTED")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(20, "T20", payload=True, chip_pos="bl")
        m.tray(23, "T23", chip_pos="bl")
        intent(d, m, 21, None, 2, TRAY, q_off=(118, 52), bend=-0.1, src_off=(30, 8))
        bay_events(d, m, 21, [(1, "TRANSITION_TO_RETRIEVE", BAYC)], dx=10)

    return job_figure(
        "43_job_insert", heading="TYPE_INSERT  ->  PlanInsertJob()",
        subtitle="A customer has driven onto tray T21 in bay B21. Make the bay accessible from the garage side and "
                 "move the loaded tray out. Where it parks is decided later.",
        req=[("job.type", "TYPE_INSERT"), ("job.bay_id", "21"), ("job_index", "0"),
             ("call", "PlanInsertJob(plan_ctx, job.bay_id, 0)"), ("returns", "BoolStringPair")],
        region="qa", draw_map=draw, map_caption="working_state at the start of the job",
        events=[("BayTransition", "B21: TRANSITION_TO_RETRIEVE", 0, "solid", "via PlanOpenBayDoor, floor = floors[0]"),
                ("TrayMove", "T21: B21 -> ?", 0, "solid", "via PlanReparkTrayJob, no destination")],
        edges=[(1, 2, "B", "bay")],
        outside=[("Not an event: a callback", "reset_bay_state_request_fn_(21, READY_TO_INSERT) asks Dispatch "
                  "(through SchedulerRos) for a separate job that refills B21 with an empty tray.")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("bay_opt = working_state.GetBay(bay_id);\nmissing or disabled -> fail", "B21 exists and is enabled.",
             "passes", "ok"),
            ("tray_opt = GetTrayOnNode(bay);\nno tray -> fail; tray without payload -> fail",
             "T21 is in the bay and carries the customer's car.", "passes", "ok"),
            ("state must be VEHICLE_INSERTED or READY_TO_RETRIEVE", "B21 is VEHICLE_INSERTED.", "passes", "ok"),
            ("PlanOpenBayDoor(ctx, bay, job_index):\n  floor = GetBaySystemFloors(bay)[0] (none -> fail);\n"
             "  BayTransition(TRANSITION_TO_RETRIEVE); rule A; rule B",
             "Added even when the bay is already READY_TO_RETRIEVE.", "adds 1", "event"),
            ("PlanReparkTrayJob(ctx, tray, job_index, allow_recip = true)\n// no destination",
             "T21 leaves the bay. Rule B orders it after 1.", "adds 2 · B", "event"),
            ("if(reset_bay_state_request_fn_)\n  reset_bay_state_request_fn_(bay_id, READY_TO_INSERT)",
             "Ask for a follow-up job instead of planning the refill here.", "callback", "call"),
            ("return {true, \"\"}", "", "success", "ok"),
            ("// in Plan(), only for INSERT:\nfailure -> clean_garage_request_fn_()",
             "If the insert had failed, Plan() would also ask Dispatch for a CLEAN_GARAGE job.", "not reached", "skip"),
        ],
        notes=[("Why a retrieve transition?", "The code reuses TRANSITION_TO_RETRIEVE (helper PlanOpenBayDoor) to "
                "make the tray in the bay reachable from the garage before an AGV lifts it.", T.violet),
               ("Why not refill the bay here?", "The comment in the code: if T21 was the last empty tray, a refill "
                "would fail and take the insert down with it. A separate job can fail on its own.", T.teal),
               ("Not decided yet", "Where T21 parks (DoTrayAssignments, with ResolveBlockingTrays), which AGV and "
                "which route.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("44_job_ready_for_insert", "TYPE_READY_FOR_INSERT: PlanReadyForInsertJob", DOC1)
def job_ready_for_insert():
    def draw(d, m):
        bay_pill(d, m, 21, "B21 READY_TO_RETRIEVE (empty)")
        m.tray(23, "T23", emphasis=True, chip_pos="bl")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(17, "T17", payload=True, chip_pos="bl")
        m.tray(20, "T20", payload=True, chip_pos="bl")
        intent(d, m, 23, 21, 1, TRAY, bend=0.3, dst_off=(40, 0), num_t=0.5)
        cost_tag(d, m, 23, "nearest empty tray", TRAY, dy=-32)
        bay_events(d, m, 21, [(2, "TRANSITION_TO_INSERT", BAYC)], dx=10)

    return job_figure(
        "44_job_ready_for_insert", heading="TYPE_READY_FOR_INSERT  ->  PlanReadyForInsertJob()",
        subtitle="Put an empty tray into bay B21 and switch the bay to insert mode, so the next customer can drive "
                 "in. The tray is chosen early, inside this method, when possible.",
        req=[("job.type", "TYPE_READY_FOR_INSERT"), ("job.bay_id", "21"), ("job_index", "0"),
             ("call", "PlanReadyForInsertJob(plan_ctx, job.bay_id, 0)"), ("returns", "BoolStringPair")],
        region="qa", draw_map=draw, map_caption="working_state at the start of the job",
        events=[("TrayMove", "T23: P23 -> B21", 0, "solid", "created as '? -> B21', tray filled in step 7"),
                ("BayTransition", "B21: TRANSITION_TO_INSERT", 0, "solid")],
        edges=[(1, 2, "B", "bay")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("bay must exist and be READY_TO_RETRIEVE", "B21 is READY_TO_RETRIEVE.", "passes", "ok"),
            ("bay_pose = {bay id, GetBayInboundHeading(bay)};\ntray_in_bay = GetTrayOnNode(bay)",
             "B21 is empty.", "no tray", "ok"),
            ("no tray in bay ->\n  PlanReparkTrayJob(ctx, nullopt, job_index, true,\n  bay_pose)   // tray unknown",
             "A TrayMove with a destination but no tray: '? -> B21'.", "adds 1", "event"),
            ("loaded tray in bay -> if payload.ev_charge_requested:\n  PlanChargePayloadJob(...); then the same "
             "\n  empty-tray move as step 4",
             "Not this case. A loaded tray that is not for charging stays put: DoTrayAssignments() later treats "
             "it as blocking the destination and moves it.", "skipped", "skip"),
            ("empty tray already in bay -> nothing to move", "Not this case.", "skipped", "skip"),
            ("fill pass: fill_state = replay again; walk the\ntopological order; for this job's TrayMoves\n"
             "with a dest but no tray:\n  AssignTrayIdForEmptyMove(*move, fill_state)",
             "Nearest empty tray by graph search: T23 (illustrative). Rule A is applied now for T23. If no tray "
             "is found, the move stays '? -> B21' for DoTrayAssignments().", "tray = T23", "ok"),
            ("BayTransition(TRANSITION_TO_INSERT);\nrule A (bay); rule B", "After the tray is in.",
             "adds 2 · B", "event"),
            ("return {true, \"\"}", "", "success", "ok"),
        ],
        notes=[("Two ways to get a tray", "Early, here, with AssignTrayIdForEmptyMove; or late, in "
                "DoTrayAssignments(), which sees trays freed by every other job too. Failing early is only a "
                "warning.", T.amber),
               ("A loaded tray in the bay", "If the car asked for EV charging, PlanChargePayloadJob() sends it to "
                "a VECS first. Otherwise nothing moves it explicitly; it is cleared as a blocking tray.", T.pink),
               ("Bug to know about", "PlanReparkTrayJob() is called with no tray here, and its 'already at "
                "destination' check reads tray_opt->pose without testing tray_opt. That is undefined behaviour.",
                T.red)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("45_job_ready_for_retrieve", "TYPE_READY_FOR_RETRIEVE: PlanReadyForRetrieveJob", DOC1)
def job_ready_for_retrieve():
    def draw(d, m):
        m.tray(21, "T21", emphasis=True, chip_pos="tr")
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(17, "T17", payload=True, chip_pos="bl")
        m.tray(24, "T24", payload=True, chip_pos="bl")
        intent(d, m, 21, None, 2, TRAY, q_off=(118, 52), bend=-0.1, src_off=(30, 8))
        bay_events(d, m, 21, [(1, "TRANSITION_TO_RETRIEVE", BAYC)], dx=10)

    return job_figure(
        "45_job_ready_for_retrieve", heading="TYPE_READY_FOR_RETRIEVE  ->  PlanReadyForRetrieveJob()",
        subtitle="Prepare bay B21 for a future retrieve: switch it to retrieve mode and clear the tray inside. Unlike "
                 "READY_FOR_INSERT, there is no final bay transition.",
        req=[("job.type", "TYPE_READY_FOR_RETRIEVE"), ("job.bay_id", "21"), ("job_index", "0"),
             ("call", "PlanReadyForRetrieveJob(plan_ctx, job.bay_id, 0)"), ("returns", "BoolStringPair")],
        region="qa", draw_map=draw, map_caption="working_state at the start of the job",
        events=[("BayTransition", "B21: TRANSITION_TO_RETRIEVE", 0, "solid", "via PlanOpenBayDoor"),
                ("TrayMove", "T21: B21 -> ?", 0, "solid", "via PlanReparkTrayJob, no destination")],
        edges=[(1, 2, "B", "bay")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("bay must exist; state READY_TO_INSERT or\nREADY_TO_RETRIEVE, else fail", "B21 is READY_TO_INSERT.",
             "passes", "ok"),
            ("READY_TO_INSERT -> PlanOpenBayDoor(ctx, bay, job_index)",
             "BayTransition TRANSITION_TO_RETRIEVE on the first system floor.", "adds 1", "event"),
            ("tray_in_bay = GetTrayOnNode(bay)", "Empty tray T21 is inside.", "found", "ok"),
            ("payload with ev_charge_requested ->\n  PlanChargePayloadJob(ctx, payload, job_index)",
             "T21 has no payload.", "skipped", "skip"),
            ("else -> PlanReparkTrayJob(ctx, tray, job_index, true)\n// no destination",
             "T21 leaves the bay; rule B orders it after 1.", "adds 2 · B", "event"),
            ("return {true, \"\"}", "The bay stays READY_TO_RETRIEVE.", "success", "ok"),
        ],
        notes=[("Same first half as INSERT", "Both call PlanOpenBayDoor() and then move the tray out with no "
                "destination. INSERT requires a loaded tray; this job accepts any tray, or none.", T.violet),
               ("EV payload in the bay", "Goes to a VECS through PlanChargePayloadJob() instead of an ordinary "
                "repark.", T.pink),
               ("Usually not requested directly", "REBALANCE_GARAGE calls this method for each bay it wants in "
                "retrieve mode.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("46_job_clean_garage", "TYPE_CLEAN_GARAGE: PlanCleanGarageJob", DOC1)
def job_clean_garage():
    def draw(d, m):
        m.tray(24, "T24", chip_pos="bl")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(20, "T20", payload=True, chip_pos="bl")
        m.tray(25, "T9 on W25", chip_pos="bl")
        m.agv(27, "A", heading=90, label_side="left")
        m.agv(13, "B", heading=90, label_side="left")
        agv_intent(d, m, 27, 24, 1, bend=-0.6, num_t=0.5)
        agv_intent(d, m, 13, 15, 2, bend=0.35, num_t=0.5)
        intent(d, m, 25, None, 3, TRAY, q_off=(-6, 64), src_off=(30, 6), bend=-0.3)
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")

    return job_figure(
        "46_job_clean_garage", heading="TYPE_CLEAN_GARAGE  ->  PlanCleanGarageJob()",
        subtitle="Tidy up when there is no other work: park idle AGVs out of the way under trays, and put trays "
                 "that an earlier plan left on waypoints back into parking.",
        req=[("job.type", "TYPE_CLEAN_GARAGE"), ("job_index", "0 (needed for hiding)"),
             ("call", "PlanCleanGarageJob(plan_ctx, 0)"), ("returns", "BoolStringPair")],
        region="qa", draw_map=draw, map_caption="working_state at the start of the job",
        events=[("AgvMove", "A: W27 -> P24 (under T24)", 0, "solid"),
                ("AgvMove", "B: W13 -> P15 (under T15)", 0, "solid"),
                ("TrayMove", "T9: W25 -> ?", 0, "solid", "via PlanUnstashWaypointTraysJob")],
        edges=[(2, 3, "B", "bay"), (1, 3, "B", "bay")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("if(job_index == 0):\n  [ok, hide] = volley::HideAgvs(working_state, table_)",
             "First job, so AGVs are hidden. HideAgvs (motion_planner) returns the first assignment it finds, one hiding pose per "
             "AGV (A -> P24, B -> P15 here, illustrative).", "hiding spots", "ok"),
            ("hiding failed -> return {false, ...}", "It succeeded.", "skipped", "skip"),
            ("for each (agv, dest) with agv.pose != dest:\n  AgvMove; rule A (AGV);\n"
             "  dest is a bay -> rule A for that bay too;\n  agv_move->Apply(working_state)",
             "No rule B: the hide moves do not wait for each other.", "adds 1, 2", "event"),
            ("PlanUnstashWaypointTraysJob(ctx, job_index):\n  replay; collect enabled trays on TYPE_WAYPOINT",
             "T9 was left on waypoint W25 by an earlier tier-2 stash.", "T9 found", "ok"),
            ("  for each: PlanReparkTrayJob(ctx, tray, job_index,\n  true)   // no destination; failures logged",
             "Rule B: both hide moves are leaves of this job, so 3 waits for 1 and 2.", "adds 3 · B", "event"),
            ("return {true, \"\"}   // unstash failure is only logged", "", "success", "ok"),
        ],
        notes=[("job_index == 0", "Means the first job that succeeded in this request, not the first in the list. "
                "If an earlier job failed, CLEAN_GARAGE can still get index 0.", T.amber),
               ("Why under trays?", "An AGV parked under a tray takes no extra space and is out of the aisles. "
                "If the hiding spot is a bay, the bay's next transition waits for the AGV (rule A on the bay).",
                T.green),
               ("Waypoint stash", "When ResolveBlockingTrays() finds no parking it may leave a blocker on a "
                "waypoint (tier 2, 'Tray assignment'). CLEAN_GARAGE is what puts it back.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("47_job_rebalance_garage", "TYPE_REBALANCE_GARAGE: PlanRebalanceGarageJob", DOC1)
def job_rebalance():
    def draw(d, m):
        bay_pill(d, m, 7, "B7 READY_TO_RETRIEVE (empty)")
        m.tray(21, "T21", chip_pos="tr")
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")
        m.tray(5, "T5", emphasis=True, chip_pos="bl")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(20, "T20", payload=True, chip_pos="bl")
        m.tray(6, "T6", payload=True, chip_pos="bl")
        intent(d, m, 5, 7, 1, TRAY, bend=-0.25, dst_off=(40, 0), num_t=0.62)
        intent(d, m, 21, None, 4, TRAY, q_off=(118, 48), bend=-0.1, src_off=(30, 8))
        bay_events(d, m, 7, [(2, "TRANSITION_TO_INSERT", BAYC)], dx=10)
        bay_events(d, m, 21, [(3, "TRANSITION_TO_RETRIEVE", BAYC)], dx=10)

    return job_figure(
        "47_job_rebalance_garage", heading="TYPE_REBALANCE_GARAGE  ->  PlanRebalanceGarageJob()",
        subtitle="Keep the right share of bays in insert mode. The method asks ComputeBayRebalancingActions() "
                 "which bays to switch, then runs the READY_FOR_INSERT and READY_FOR_RETRIEVE recipes with the "
                 "same job_index.",
        req=[("job.type", "TYPE_REBALANCE_GARAGE"), ("job_index", "0"),
             ("call", "PlanRebalanceGarageJob(plan_ctx, 0)"),
             ("input", "bay_readiness_ratio_ (set by service)"), ("returns", "BoolStringPair, always true")],
        region="mid", draw_map=draw, map_caption="working_state at the start of the job",
        events=[("TrayMove", "T5: P5 -> B7", 0, "solid", "READY_FOR_INSERT recipe for B7"),
                ("BayTransition", "B7: TRANSITION_TO_INSERT", 0, "solid"),
                ("BayTransition", "B21: TRANSITION_TO_RETRIEVE", 0, "solid", "READY_FOR_RETRIEVE recipe for B21"),
                ("TrayMove", "T21: B21 -> ?", 0, "solid")],
        edges=[(1, 2, "B", "bay"), (2, 3, "B", "bay", "B · across bays"), (3, 4, "B", "bay")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("[to_insert, to_retrieve] = ComputeBayRebalancingActions(\n  working_state,\n"
             "  layout_->GetBayPrioritization(), bay_readiness_ratio_)",
             "Illustrative result: B7 should become insert-ready, B21 retrieve-ready. 'Bays, VECS and VRCs' explains the "
             "classification and the ratio.", "[B7], [B21]", "ok"),
            ("for bay in to_insert:\n  PlanReadyForInsertJob(ctx, bay, job_index)\n  failure -> log and continue",
             "Empty tray T5 (nearest, illustrative) into B7, then B7 to insert mode.", "adds 1, 2", "event"),
            ("for bay in to_retrieve:\n  PlanReadyForRetrieveJob(ctx, bay, job_index)\n  failure -> log and continue",
             "B21 to retrieve mode, then T21 out. Rule B links 3 to 2 because both recipes share job_index 0.",
             "adds 3, 4 · B", "event"),
            ("return {true, \"\"}   // per-bay failures never fail the job", "", "success", "ok"),
        ],
        notes=[("Rule B serialises the bays", "Every sub-recipe uses the same job_index, so the first event of "
                "B21's recipe waits for the leaves of B7's. Bays are rebalanced one after another, not in "
                "parallel.", T.fg2),
               ("Almost never fails", "Per-bay failures are logged and skipped, and their partial events stay. The job "
                "fails only if the initial replay fails; it may succeed with no events at all.", T.amber),
               ("No AGV hiding", "Unlike CLEAN_GARAGE, rebalancing assumes more work is coming, so AGVs stay "
                "where they are.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("48_job_charge_agv", "TYPE_CHARGE_AGV: PlanAgvChargeJob", DOC1)
def job_charge_agv():
    def draw(d, m):
        m.agv(21, "A (trapped)", heading=90, label_side="right")
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")
        m.agv(16, "B", heading=90, label_side="left")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(5, "T5", payload=True, chip_pos="bl")
        agv_intent(d, m, 21, 14, 2, bend=-0.2, src_off=(40, 0), num_t=0.5)
        cost_tag(d, m, 14, "C14 free · 31 s · best", AGV, dy=26)
        cost_tag(d, m, 10, "C10 free · 48 s", T.fg2, dx=-80, dy=0)
        cost_tag(d, m, 16, "C16 has AGV B: skipped", T.red, dy=26)
        bay_events(d, m, 21, [(1, "TRANSITION_TO_RETRIEVE", BAYC), (3, "TRANSITION_TO_INSERT", BAYC)], dx=10)

    return job_figure(
        "48_job_charge_agv", heading="TYPE_CHARGE_AGV  ->  PlanAgvChargeJob()",
        subtitle="Send AGV A to the cheapest free charger. A is trapped in bay B21 (insert mode), so the bay is "
                 "switched to retrieve mode to let it out and switched back afterwards.",
        req=[("job.type", "TYPE_CHARGE_AGV"), ("job.agv_id", "A"), ("job_index", "0"),
             ("call", "PlanAgvChargeJob(plan_ctx, job.agv_id, 0)"), ("returns", "BoolStringPair")],
        region="mid", draw_map=draw, map_caption="working_state at the start (costs illustrative)",
        events=[("BayTransition", "B21: TRANSITION_TO_RETRIEVE", 0, "solid"),
                ("AgvMove", "A: B21 -> C14@inbound", 0, "solid", "via PlanAgvMoveJob"),
                ("BayTransition", "B21: TRANSITION_TO_INSERT", 0, "solid", "via PlanBayTransitionJob")],
        edges=[(1, 2, "B", "bay"), (2, 3, "B", "bay"), (1, 3, "A", "bay", "A · B21")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("AGV must exist and not be disabled", "A is enabled.", "passes", "ok"),
            ("already on a TYPE_AGV_CHARGE node at its inbound\nheading -> return {true, \"\"}", "A is in a bay.",
             "no early exit", "skip"),
            ("on a bay node:\n  READY_TO_INSERT -> BayTransition(TO_RETRIEVE),\n"
             "    Apply to working_state, rule A (bay);\n  READY_TO_RETRIEVE -> fine; other -> fail",
             "B21 is READY_TO_INSERT, so A is trapped until the bay switches.", "adds 1", "event"),
            ("for each TYPE_AGV_CHARGE node:\n  skip if an AGV is on it;\n  pose = {node, inbound heading};"
             " must be enabled;\n  cost = GetJustMovingCost(..., static filters)",
             "C16 is skipped (AGV B). C14 and C10 are costed; C14 is cheaper. 'Free' only means no AGV on the "
             "node, not that its surroundings are clear.", "best = C14", "ok"),
            ("no charger -> return {false, \"Caution: No available ...\"}", "C14 was found.", "skipped", "skip"),
            ("PlanAgvMoveJob(ctx, agv, best, false, job_index)",
             "Replays event 1 (bay now READY_TO_RETRIEVE), adds the move, rule A (A) and rule B (after 1).",
             "adds 2 · B", "event"),
            ("trapped -> PlanBayTransitionJob(ctx, bay,\n  TRANSITION_TO_INSERT, job_index)",
             "Puts B21 back into insert mode: rule A after 1 and rule B after 2.", "adds 3 · A, B", "event"),
        ],
        notes=[("Composite job", "Two of the three events come from other job methods. That is why the matrix "
                "of building blocks shows AgvMove and BayTrans calls on this row.", T.teal),
               ("Cost, not distance", "GetJustMovingCost() asks the motion cost model for the travel time, using "
                "static filters so a path must exist. AGV assignment uses the same helper.", T.green),
               ("Not checked", "Whether the charger area is free of trays or other conflicts (a TODO in the "
                "code).", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("49_job_bay_transition", "TYPE_TRANSITION_BAY_TO_*: PlanBayTransitionJob", DOC1)
def job_bay_transition():
    def draw(d, m):
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")
        m.tray(21, "T21", chip_pos="tr")
        bay_pill(d, m, 7, "B7 READY_TO_RETRIEVE")
        odp_area(d, m, 7, "BAY_ODP area (extent illustrative)")
        m.agv(31, "C", heading=90, label_side="above")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(5, "T5", payload=True, chip_pos="bl")
        bay_events(d, m, 21, [(1, "TRANSITION_TO_RETRIEVE", BAYC)], dx=10)
        x, y = m.P(7)
        d.text(x - 110, y + 96, "job 1 rejected: area occupied", size=10.5, family="mono", fill=T.red,
               halo=T.bg_deep, halo_w=3)

    return job_figure(
        "49_job_bay_transition", heading="TYPE_TRANSITION_BAY_TO_INSERT / _TO_RETRIEVE  ->  PlanBayTransitionJob()",
        subtitle="Command one bay to change mode. Job 0 succeeds; job 1 is rejected because an AGV stands in the "
                 "bay's ODP collision area, so it adds no event.",
        req=[("job 0", "TYPE_TRANSITION_BAY_TO_RETRIEVE, bay_id = 21"),
             ("job 1", "TYPE_TRANSITION_BAY_TO_INSERT, bay_id = 7"),
             ("call", "PlanBayTransitionJob(plan_ctx, job.bay_id,\n  COMMAND_TYPE_TRANSITION_TO_*, job_index)"),
             ("returns", "BoolStringPair")],
        region="mid", draw_map=draw, map_caption="working_state at the start of job 0",
        events=[("BayTransition", "B21: TRANSITION_TO_RETRIEVE", 0, "solid", "cmd.floor = GetBaySystemFloors(21)[0]")],
        edges=[],
        outside=[("Job 1: FailJob, no event", "\"Requested to transition b7 but the ODP's area is occupied.\" "
                  "Plan() appends FailJob(job, message) to result.scheduled_jobs; job 1's index is not used.")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);",
             "Job 1 replays event 1 first.", "replay", "ok"),
            ("bay must exist and not be disabled", "B21 and B7 are enabled.", "passes", "ok"),
            ("filters = GetStaticFilter(BAY_ODP, gg_, working_state,\n  table_, ...);\n"
             "!filters.IsEnabled(bay pose) -> fail",
             "Job 0: nothing near B21. Job 1: AGV C stands in B7's ODP area, so job 1 fails here.",
             "job 1 fails", "fail"),
            ("TO_INSERT: bay must be READY_TO_RETRIEVE", "Job 1 never gets here.", "not reached", "skip"),
            ("TO_RETRIEVE: floor = GetBaySystemFloors(bay)[0]\n  (none -> fail); bay must be READY_TO_INSERT\n"
             "  or VEHICLE_INSERTED", "Job 0: B21 is READY_TO_INSERT.", "passes", "ok"),
            ("other command type -> fail", "", "skipped", "skip"),
            ("BayTransition(cmd); UpdateLastEntityEvent(bay);\nUpdateLeafDependencies", "Job 0 only.",
             "adds 1", "event"),
        ],
        notes=[("Also used inside other jobs", "PlanAgvChargeJob() calls it to put a bay back into insert mode. "
                "Retrieve, insert and ready-for-retrieve create their bay transitions directly or through "
                "PlanOpenBayDoor(), which skips the ODP check.", T.violet),
               ("Floor", "Retrieve transitions made here or in PlanOpenBayDoor() carry the bay's first system "
                "floor. Insert transitions, and the retrieve transitions RETRIEVE and CHARGE_AGV build inline, "
                "send floor 0.", T.border),
               ("Static filter", "GetStaticFilter() marks graph vertices blocked by entities in working_state for "
                "the given collision entity, here BAY_ODP.", T.border)],
        bw=300)


# --------------------------------------------------------------------------------------
@figure("50_job_charge_payload", "TYPE_CHARGE_PAYLOAD: PlanChargePayloadJob", DOC1)
def job_charge_payload():
    def draw(d, m):
        vecs_mark(d, m, 23, "V23 READY_TO_CHARGE (invented VECS)")
        m.tray(20, "T20 (EV)", payload=True, emphasis=True, chip_pos="bl")
        m.tray(15, "T15", chip_pos="bl")
        m.tray(17, "T17", payload=True, chip_pos="bl")
        m.tray(24, "T24", chip_pos="bl")
        intent(d, m, 20, 23, 1, TRAY, bend=0.3, num_t=0.5, dst_off=(10, 6), src_off=(-10, -6))
        x, y = m.P(23)
        num_badge(d, x - 40, y + 6, 2, VECS, r=10)
        d.text(x - 26, y + 6, "-> CHARGING", size=10.5, family="mono", fill=VECS, halo=T.bg_deep, halo_w=3)
        bay_pill(d, m, 21, "B21 READY_TO_INSERT")

    return job_figure(
        "50_job_charge_payload", heading="TYPE_CHARGE_PAYLOAD  ->  PlanChargePayloadJob()",
        subtitle="Charge an electric car. If its tray is not already on a ready VECS, find one, plan the tray move, "
                 "then switch the VECS to CHARGING.",
        req=[("job.type", "TYPE_CHARGE_PAYLOAD"), ("job.payload_id", "<GUID of the car on T20>"),
             ("job_index", "0"), ("call", "PlanChargePayloadJob(plan_ctx, job.payload_id, 0)"),
             ("returns", "BoolStringPair")],
        region="qa", draw_map=draw,
        map_caption="working_state at the start (Pecos has no VECS; V23 is invented)",
        events=[("TrayMove", "T20: P20 -> V23", 0, "solid", "via PlanReparkTrayJob; heading from the search"),
                ("VecsTransition", "V23: READY_TO_CHARGE -> CHARGING", 0, "solid")],
        edges=[(1, 2, "B", "bay")],
        steps=[
            ("working_state = ctx->initial_state;\nctx->events.Apply(working_state);", "Empty DAG.", "replay", "ok"),
            ("payload must exist; tray = GetTray(payload.tray_id)", "The car is on T20 at P20.", "found", "ok"),
            ("tray on a TYPE_EV_CHARGE node whose VECS is\nREADY_TO_CHARGE -> use it, no tray move",
             "P20 is plain parking.", "no", "skip"),
            ("[dest, _] = ResolveBlockingTrays(tray, job_index,\n  working_state)   // unblocking moves discarded",
             "The open-space search only accepts a spot with a VECS for an EV-charge payload "
             "(OpenSpaceSearchEnvironment): V23 here.", "dest = V23", "ok"),
            ("no dest -> fail; dest has no VECS -> fail", "V23 is a VECS.", "passes", "ok"),
            ("UseEvChargeHeading(dest);\nPlanReparkTrayJob(ctx, tray, job_index, false, dest)",
             "UseEvChargeHeading only matters on 576_eccles. Adds the TrayMove with rule A (T20); rule C would wait "
             "for V23's last event (none yet).",
             "adds 1", "event"),
            ("VecsTransition(READY_TO_CHARGE -> CHARGING);\nrule A (VECS); rule B", "Starts after the tray arrives.",
             "adds 2 · B", "event"),
        ],
        notes=[("Also called by bay jobs", "READY_FOR_INSERT and READY_FOR_RETRIEVE call it when the car in the "
                "bay asked for EV charging, so the car goes to a VECS instead of ordinary parking.", T.pink),
               ("Discarded unblocking moves", "ResolveBlockingTrays() also returns the moves needed to reach the "
                "VECS. They are ignored here; DoTrayAssignments() finds blockers again later.", T.amber),
               ("Stop-charging events", "RETRIEVE and REPARK add the opposite transition (CHARGING -> "
                "READY_TO_CHARGE) without rule A, so it is not chained to this one by entity.", T.border)],
        bw=300)


# ======================================================================================
# 38 — reads / mutates / returns for one job method
# ======================================================================================

def _panel(d, x, y, w, title, items, col, *, sub=None, size=11):
    """items: list of (mono_text, sans_note or None)."""
    pad = 12
    rows = []
    for code, nt in items:
        cl = wrap(code, w - 2 * pad, size, "mono")
        nl = wrap(nt, w - 2 * pad - 10, 10.5, "sans") if nt else []
        rows.append((cl, nl))
    sl = wrap(sub, w - 2 * pad, 10.5, "sans") if sub else []
    h = pad + 24 + len(sl) * 15 + sum(len(c) * 16 + len(n) * 14 + 8 for c, n in rows) + pad - 4
    d.rect(x, y, w, h, rx=10, fill=T.tint(col, 0.07, T.bg), stroke=col, sw=1.5)
    d.text(x + pad, y + pad + 6, title, size=12.5, weight=600, fill=col)
    yy = y + pad + 26
    for ln in sl:
        d.text(x + pad, yy, ln, size=10.5, fill=T.muted)
        yy += 15
    for cl, nl in rows:
        for ln in cl:
            d.text(x + pad, yy, ln, size=size, family="mono", fill=T.fg)
            yy += 16
        for ln in nl:
            d.text(x + pad + 10, yy - 2, ln, size=10.5, fill=T.fg2)
            yy += 14
        yy += 8
    return BBox(x, y, x + w, y + h)


@figure("38_job_method_dataflow", "What a job method reads, changes and returns", DOC1)
def job_method_dataflow():
    d = Doc("38_job_method_dataflow", "What PlanRetrieveJob reads, changes and returns",
            "Read-only inputs, the context it changes in place, local scratch state, the return value, and the "
            "external side effects some job methods have.")
    MUT, RO, OUT, LOC, EXT = T.amber, T.sky, T.green, T.fg2, T.red
    _sig = [("std::tuple<bool, std::string, bool>", "// RETURNED: {success, message, retain_job}"),
            ("Scheduler::PlanRetrieveJob(ScheduleContextSPtr ctx,", "// the shared_ptr is copied; *ctx is shared and CHANGED"),
            ("                           const GuidMsg& payload_id,", "// read-only"),
            ("                           size_t job_index) const;", "// read-only copy; 'const' = members of *this read-only")]
    sig = code_panel(d, 0, 0, W, [a.ljust(58) + b for a, b in _sig
], title="include/scheduler/scheduler.hpp", size=11.5)
    y0 = sig.y1 + 34
    # ---- left: read-only ----
    lw = 330
    ro = _panel(d, 0, y0, lw, "Read-only inputs", [
        ("this->layout_", "bay prioritisation, inbound heading, resource windows"),
        ("this->gg_  (and table_ via filters)", "pose -> graph vertex"),
        ("payload_id, job_index", "the job's fields, by const& / by value"),
        ("ctx->initial_state", "copied, never changed"),
        ("ctx->disabledness_filters[id]", "read, but operator[] on a std::unordered_map inserts a default entry "
                                          "if id is missing"),
    ], RO)
    # ---- centre: the function and its local scratch ----
    cx, cw = lw + 50, 330
    d.rect(cx, y0, cw, 228, rx=12, fill=T.card, stroke=T.fg2, sw=1.6)
    d.text(cx + cw / 2, y0 + 22, "PlanRetrieveJob(...)", size=13.5, family="mono", weight=700, fill=T.fg,
           anchor="middle")
    d.text(cx + cw / 2, y0 + 42, "plus nested PlanReparkTrayJob calls", size=11, fill=T.muted, anchor="middle")
    d.rect(cx + 16, y0 + 62, cw - 32, 150, rx=8, fill=T.bg_deep, stroke=LOC, sw=1, dash="4 3")
    d.text(cx + 28, y0 + 80, "local scratch (gone at return)", size=11, weight=600, fill=LOC)
    for k, ln in enumerate(["working_state = ctx->initial_state;", "ctx->events.Apply(working_state);",
                            "payload_opt, tray, bay_opt, bay_pose,", "dest_pose, cmd ...",
                            "bay_opt->state = READY_TO_RETRIEVE;", "  // edits the local copy only"]):
        d.text(cx + 28, y0 + 102 + k * 17, ln, size=10.5, family="mono", fill=T.fg2 if k < 5 else T.faint)
    fb = BBox(cx, y0, cx + cw, y0 + 228)
    # ---- right: returned ----
    rx = cx + cw + 50
    rw = W - rx
    out = _panel(d, rx, y0, rw, "Returned", [
        ("{true, \"\", false}", "success; Plan() then appends the job to scheduled_jobs"),
        ("{false, msg, retain_job}", "failure; retain_job = true asks Dispatch to keep the job (no bay free, "
                                     "VECS busy)"),
    ], OUT, sub="the only output visible in the signature")
    connect(d, [(ro.x1, y0 + 60), (fb.x0, y0 + 60)], kind="flow", color=RO, size=9, sw=2)
    connect(d, [(fb.x1, y0 + 60), (out.x0, y0 + 60)], kind="flow", color=OUT, size=9, sw=2)
    # ---- bottom: mutated in place ----
    my = max(ro.y1, fb.y1, out.y1) + 56
    connect(d, [(fb.cx - 30, my), (fb.cx - 30, fb.y1)], kind="flow", color=MUT, size=9, sw=2)
    connect(d, [(fb.cx + 30, fb.y1), (fb.cx + 30, my)], kind="flow", color=MUT, size=9, sw=2)
    label_pill(d, fb.cx + 40, (fb.y1 + my) / 2, "read and written through ctx", color=MUT, size=10.5,
               anchor="start", bg=T.bg)
    mh = 236
    d.rect(0, my, W, mh, rx=12, fill=T.tint(MUT, 0.06, T.bg), stroke=MUT, sw=1.6)
    d.text(14, my + 20, "Changed in place through ctx: the real output, not visible in the return type", size=12.5,
           weight=600, fill=MUT)
    hx = [14, 250, 560]
    for x, h in zip(hx, ["member of *ctx", "before the call (first job)", "after the call"]):
        d.text(x, my + 46, h, size=10.5, family="mono", weight=600, fill=T.muted)
    rows = [("ctx->events", "{ }  (no events, no edges)",
             ["+4 events, all job_index 0:", "  e1 B21 TO_RETRIEVE   e2 T21 -> ?", "  e3 T17 -> B21        e4 B21 PROCESS_RETRIEVE",
              "+5 edges: e1->e2, e2->e3, e1->e3, e3->e4, e1->e4"]),
            ("ctx->last_entity_event", "{ }",
             ["{ B21 -> e4,  T21 -> e2,  T17 -> e3 }", "(used by rule A in later jobs)"]),
            ("ctx->disabledness_filters", "one entry per collision id", ["unchanged, unless operator[] inserted a key"])]
    yy = my + 68
    for name, before, after in rows:
        d.text(hx[0], yy, name, size=11.5, family="mono", weight=700, fill=T.fg)
        d.text(hx[1], yy, before, size=11, family="mono", fill=T.muted)
        for k, ln in enumerate(after):
            d.text(hx[2], yy + k * 17, ln, size=11, family="mono", fill=T.fg)
        yy += 17 * max(1, len(after)) + 10
    d.text(14, my + mh - 16, "Not touched by job methods: ctx->scheduled_jobs (Plan() appends after success), "
                             "ctx->first_tray_event (tray assignment), ctx->initial_state.", size=11, fill=T.fg2)
    # ---- external side effects + pure alternative ----
    ey = my + mh + 26
    ext = _panel(d, 0, ey, 420, "Side effects outside the plan (other job methods)", [
        ("PlanInsertJob -> reset_bay_state_request_fn_(bay, READY_TO_INSERT)",
         "an async ROS request to Dispatch (TransitionBayToInsert), sent during expansion, even if a later "
         "stage fails the plan"),
        ("Plan() on INSERT failure -> clean_garage_request_fn_()", "an async Trigger request to Dispatch"),
    ], EXT)
    pure = code_panel(d, 450, ey, W - 450, [
        "// sketch: same work, everything visible in the signature",
        "struct JobPlan { std::vector<ScheduleEventSPtr> events;",
        "                 std::vector<Edge> edges;          // rules A, B, C",
        "                 std::vector<FollowUp> requests; }; // instead of callbacks",
        "std::expected<JobPlan, JobFailure>",
        "PlanRetrieveJob(const PlanView& view,   // working_state, DAG, last events: const&",
        "                const RetrieveJob& job, size_t job_index) const;",
        "// Plan(): if(plan) Commit(*plan_ctx, *plan) else FailJob(...)",
    ], title="A pure alternative (not in the code)", size=10.5)
    frame(d, title="What PlanRetrieveJob reads, changes and returns",
          subtitle="The return type only says whether the job worked. The events, the edges and the entity "
                   "bookkeeping are written into the shared ScheduleContext as the method runs, including from "
                   "nested job-method calls. The same pattern holds for every Plan<Type>Job.",
          badge_key="as-built",
          legend=[("box", RO, "read-only input"), ("box", MUT, "changed in place (through ctx)"),
                  ("box", OUT, "returned"), ("dashbox", LOC, "local copy, discarded"),
                  ("box", EXT, "leaves the process")])
    return d
