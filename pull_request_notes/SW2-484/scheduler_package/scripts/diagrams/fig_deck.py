"""Figures made for the stakeholder deck (deck/figures/), not for the study site.

One running scenario on the Pecos QA section, used from the domain slide to AGV assignment:
  job A  retrieve the vehicle on tray T17 (stall P17) at bay B21; bay B21 still holds the empty tray T21,
         and tray T15 (stall P15) stands on the route out of stall P17
  job B  clean the garage: tray T27 is stranded on waypoint W27 and goes to stall P24
  AGV-1 waits at waypoint W26, AGV-2 at stall P24; tray T20 (with a vehicle) stays at stall P20.

The figures carry no title block (the slide has the title) and no player script. Movers use explicit keyframe
times (data-mt) and step durations (data-md), so an AGV can drive to a tray, lift it and carry it in ONE step
while the tray waits until the AGV arrives; deck/src/deck.js plays them.

Run:  python3 scripts/diagrams/fig_deck.py   (writes deck/figures/*.svg, then the light-theme map)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from components import chip, num_badge, label_pill
from facility import Map, NODES, STALL_L, STALL_W, C_BAY
from svgkit import BBox, Doc, text_width, wrap, pts_to_path, fmt
from theme import S, T

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deck" / "figures"
QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)
AGV_C, TRAY_C = T.green, T.amber
HL = T.sky          # "new in this step" / current focus
DONE = T.faint


# --------------------------------------------------------------------------------------------------------------
# moving entities with explicit timing
# --------------------------------------------------------------------------------------------------------------
class Play:
    """AGVs and trays that move between steps. script(step, agv, ops): ops are ("drive", [node ids]), ("lift",),
    ("carry", [node ids]), ("lower",). Within a step every AGV runs its ops back to back at the same speed; a lifted
    tray rides along from the moment it is lifted."""

    def __init__(self, m: Map):
        self.m, self.d = m, m.d
        self.ents, self.order, self.scripts = {}, [], {}

    def agv(self, name, at, *, label_side="below"):
        self.ents[name] = dict(kind="agv", at=at, label_side=label_side)
        self.order.append(name)

    def tray(self, name, at, *, payload=False, chip_pos="bl", emphasis=False):
        self.ents[name] = dict(kind="tray", at=at, payload=payload, chip_pos=chip_pos, emphasis=emphasis)
        self.order.append(name)

    def script(self, step, agv, ops):
        self.scripts.setdefault(step, []).append((agv, ops))

    def draw(self):
        d, m = self.d, self.m
        n = len(d.steps)
        pos = {e: m.P(v["at"]) for e, v in self.ents.items()}
        start = dict(pos)
        frames = {e: [] for e in self.ents}
        times = {e: [] for e in self.ents}
        durs = []
        for k in range(n):
            tracks = {}      # entity -> [(x, y, dist)]
            longest = 0.0
            for agv, ops in self.scripts.get(k, []):
                dist, carrying = 0.0, None
                tr = [(*pos[agv], 0.0)]
                for op in ops:
                    if op[0] in ("drive", "carry"):
                        for nid in op[1]:
                            p = m.P(nid)
                            q = tr[-1]
                            seg = math.hypot(p[0] - q[0], p[1] - q[1])
                            if seg < 1e-6:
                                continue
                            dist += seg
                            tr.append((p[0], p[1], dist))
                            if carrying:
                                tracks[carrying].append((p[0], p[1], dist))
                    elif op[0] == "lift":
                        here = tr[-1][:2]
                        cand = [t for t, v in self.ents.items() if v["kind"] == "tray"
                                and math.hypot(pos[t][0] - here[0], pos[t][1] - here[1]) < 1.0 * m.s]
                        if cand:
                            carrying = cand[0]
                            tracks[carrying] = [(*pos[carrying], 0.0), (*pos[carrying], dist)]
                    elif op[0] == "lower":
                        if carrying:
                            pos[carrying] = tracks[carrying][-1][:2]
                        carrying = None
                tracks[agv] = tr
                pos[agv] = tr[-1][:2]
                longest = max(longest, dist)
            for t, tr in tracks.items():
                pos[t] = tr[-1][:2]
            durs.append(int(min(4200, 450 + longest * 2.6)) if longest else 0)
            for e in self.ents:
                tr = tracks.get(e)
                if not tr or longest == 0:
                    frames[e].append([(pos[e][0] - start[e][0], pos[e][1] - start[e][1])])
                    times[e].append([1])
                    continue
                pts = [(x - start[e][0], y - start[e][1]) for x, y, _ in tr]
                ts = [round(s / longest, 4) for _, _, s in tr]
                if ts[-1] < 1:
                    pts.append(pts[-1])
                    ts.append(1)
                frames[e].append(pts)
                times[e].append(ts)
        for kind in ("tray", "agv"):
            for e in self.order:
                v = self.ents[e]
                if v["kind"] != kind:
                    continue
                sub = Doc(d.name + "-mv", "")
                sub.uses_map = True
                sm = Map(sub, m.ox, m.oy, m.s, (m.xmin, m.xmax), (m.ymin, m.ymax))
                if kind == "agv":
                    sm.agv(v["at"], e, label_side=v["label_side"], color=AGV_C)
                else:
                    sm.tray(v["at"], e, payload=v["payload"], chip_pos=v["chip_pos"], emphasis=v["emphasis"],
                            color=TRAY_C)
                content = "".join("".join(sub.layers[L]) for L in Doc.LAYERS)
                for key, chars in sub.glyphs.items():
                    d.glyphs.setdefault(key, set()).update(chars)
                fr = [[(round(x, 2), round(y, 2)) for x, y in f] for f in frames[e]]
                for f in fr:
                    dx, dy = f[-1]
                    d.grow(BBox(sub.bounds.x0 + dx, sub.bounds.y0 + dy, sub.bounds.x1 + dx, sub.bounds.y1 + dy))
                d._movers.append(fr)
                mid = len(d._movers) - 1
                d.raw(f"<g data-mv='{json.dumps(fr, separators=(',', ':'))}' data-mvid=\"{mid}\" "
                      f"transform=\"translate(0 0)\" data-mt='{json.dumps(times[e], separators=(',', ':'))}' "
                      f"data-md='{json.dumps(durs)}'>{content}</g>", "top")


# --------------------------------------------------------------------------------------------------------------
# small drawing helpers
# --------------------------------------------------------------------------------------------------------------
def box(d: Doc, x, y, w, top, main, *, h=50, stroke=T.border, size=12.5):
    d.rect(x, y, w, h, rx=8, fill=T.card, stroke=stroke, sw=1.4)
    d.text(x + 10, y + 15, top, size=10.5, family="mono", fill=T.muted)
    s = size
    while text_width(main, s) > w - 18 and s > 10:
        s -= 0.5
    d.text(x + 10, y + 34, main, size=s, fill=T.fg)
    return BBox(x, y, x + w, y + h)


def ring(d: Doc, b: BBox, color=HL, pad=4, sw=2.2, dash=None):
    d.rect(b.x0 - pad, b.y0 - pad, b.w + 2 * pad, b.h + 2 * pad, rx=10, fill="none", stroke=color, sw=sw, dash=dash,
           layer="over")


def check(d: Doc, b: BBox):
    x, y = b.x1 - 4, b.y0 + 4
    d.circle(x, y, 9, fill=AGV_C, layer="top")
    d.path(f"M{x - 4} {y} L{x - 1} {y + 3.5} L{x + 4.5} {y - 3.5}", stroke=T.bg, sw=2, layer="top")


def arrow(d: Doc, pts, color=T.fg2, *, sw=1.6, dash=None, size=9, layer="edges"):
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    L = math.hypot(xb - xa, yb - ya) or 1
    end = (xb - (xb - xa) / L * size * 0.85, yb - (yb - ya) / L * size * 0.85)
    d.path(pts_to_path(pts[:-1] + [end], 8), stroke=color, sw=sw, dash=dash, layer=layer)
    d.arrowhead((xb, yb), (xa, ya), kind="filled", color=color, size=size, layer=layer)


def map_route(d: Doc, m: Map, ids, color, *, sw=3, dash="7 5", offset=(0, 0)):
    pts = [m.P(i) for i in ids]
    pts = [(x + offset[0], y + offset[1]) for x, y in pts]
    d.path(pts_to_path(pts[:-1] + [pts[-1]], 8), stroke=T.bg_deep, sw=sw + 4, layer="over", opacity=0.85)
    arrow(d, pts, color, sw=sw, dash=dash, size=12, layer="over")


def node_ring(d: Doc, m: Map, nid, color, *, w=None, h=None, sw=2.4, dash=None):
    x, y = m.P(nid)
    w = w or (STALL_L - 0.2) * m.s
    h = h or (STALL_W + 0.1) * m.s
    d.rect(x - w / 2, y - h / 2, w, h, rx=8, fill="none", stroke=color, sw=sw, dash=dash, layer="top")


def bay_pill(d: Doc, m: Map, text):
    x, y = m.P(21)
    label_pill(d, x, y - (STALL_W + 0.9) * m.s / 2 - 13, text, color=C_BAY, bg=T.bg_deep, border=C_BAY, size=11)


def base_map(d: Doc, s):
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    return m


def save(d: Doc):
    OUT.mkdir(parents=True, exist_ok=True)
    svg = d.render(pad=18, interactive=False)
    (OUT / f"{d.name}.svg").write_text(svg, encoding="utf-8")
    ov = d.text_overlaps()
    print(f"{d.name:28s} {d.canvas.w:5.0f} x {d.canvas.h:5.0f}  {len(svg) / 1024:6.1f} KB"
          + (f"   !! {len(ov)} text overlaps: {ov[:3]}" if ov else ""))


def scenario_entities(p: Play, *, agv2=True, job_b=True):
    p.tray("T15", 15, chip_pos="bl")
    p.tray("T17", 17, payload=True, emphasis=True, chip_pos="tr")
    p.tray("T20", 20, payload=True, chip_pos="bl")
    p.tray("T21", 21, chip_pos="tr")
    if job_b:
        p.tray("T27", 27, chip_pos="tr")
    p.agv("AGV-1", 26, label_side="below")
    if agv2:
        p.agv("AGV-2", 24, label_side="below")


# --------------------------------------------------------------------------------------------------------------
# d01  the scenario (static)
# --------------------------------------------------------------------------------------------------------------
def d01_scenario():
    d = Doc("d01_scenario", "The running example", "Pecos QA section with the scenario used throughout the deck.")
    m = base_map(d, 30)
    p = Play(m)
    scenario_entities(p)
    p.draw()
    callouts = [(1, (23.1, 24.0)), (2, (46.0, 18.4)), (3, (33.6, 17.1)), (4, (34.6, 24.6)), (5, (45.9, 24.6))]
    for nmb, xy in callouts:
        x, y = m.P(xy)
        num_badge(d, x, y, nmb, HL, r=12)
    # thin leader lines
    for (a, b) in (((23.1, 24.0), (23.1, 23.2)), ((46.0, 18.4), (45.3, 17.6)), ((33.6, 17.1), (34.4, 17.1)),
                   ((34.6, 24.6), (35.9, 24.2)), ((45.9, 24.6), (45.0, 24.3))):
        (x0, y0), (x1, y1) = m.P(a), m.P(b)
        d.line(x0, y0, x1, y1, stroke=HL, sw=1.5, layer="over")
    save(d)


# --------------------------------------------------------------------------------------------------------------
# d02  one job, its actions and their execution (simplified world: no other trays)
# --------------------------------------------------------------------------------------------------------------
def d02_actions():
    d = Doc("d02_actions", "From a job to an ordered graph of actions",
            "Simplified: one retrieve job, no other trays. The action graph is the output; the steps execute it.")
    S0 = d.step("Input: one job, retrieve the vehicle on tray T17 at bay B21. Output: the action graph below, two "
                "lanes, one per machine. The next steps execute it.")
    S1 = d.step("Bay B21 switches to retrieve mode. It has no predecessor, so it can start at once, in parallel "
                "with AGV-1's first drive.")
    S2 = d.step("AGV-1 drives from waypoint W26 to stall P17 and stops under tray T17.")
    S3 = d.step("AGV-1 lifts tray T17 with the vehicle on it.")
    S4 = d.step("AGV-1 carries tray T17 to bay B21. This action waits for two predecessors: the lift, and the bay "
                "switching to retrieve mode.")
    S5 = d.step("AGV-1 lowers tray T17 in bay B21.")
    S6 = d.step("Bay B21 hands the vehicle over to the customer, after the lower. Every action ran when its "
                "predecessors were complete; no clock was needed.")
    m = base_map(d, 26)
    p = Play(m)
    p.tray("T17", 17, payload=True, emphasis=True, chip_pos="tr")
    p.agv("AGV-1", 26, label_side="below")
    p.script(S2, "AGV-1", [("drive", [23, 19, 15, 17])])
    p.script(S4, "AGV-1", [("lift",), ("carry", [15, 13, 18, 22, 41, 21]), ("lower",)])
    p.draw()
    with d.at(S0, S0):
        bay_pill(d, m, "B21 ready to insert")
    with d.at(S1, S5):
        bay_pill(d, m, "B21 retrieve mode")
    with d.at(S6):
        bay_pill(d, m, "B21 vehicle handed over")
    with d.only(S1):
        map_route(d, m, [26, 23, 19, 15, 17], AGV_C, dash="7 5")
    with d.only(S3):
        map_route(d, m, [17, 15, 13, 18, 22, 41, 21], TRAY_C, dash="7 5", offset=(0, 7))
    # action graph
    mb = m.box
    y0 = mb.y1 + 46
    lane_x = 80
    W = mb.x1
    bw, gap = (W - lane_x - 3 * 18) / 4, 18
    lanes = {"AGV-1": (y0, AGV_C), "Bay B21": (y0 + 98, C_BAY)}
    for name, (ly, col) in lanes.items():
        d.text(0, ly + 25, name, size=12.5, family="mono", weight=600, fill=col)
        d.line(lane_x - 10, ly + 25, W, ly + 25, stroke=T.border_soft, sw=1, dash="3 5", layer="bg")
    d.text(0, y0 - 22, "Output: action graph", size=12.5, weight=600, fill=T.fg)
    d.text(text_width("Output: action graph", 12.5, "sans", 600) + 12, y0 - 22,
           "boxes = actions · arrows = must complete before", size=11.5, fill=T.muted)
    xs = [lane_x + i * (bw + gap) for i in range(4)]
    a_drive = box(d, xs[0], y0, bw, "AGV-1", "drive to stall P17")
    a_lift = box(d, xs[1], y0, bw, "AGV-1", "lift tray T17")
    a_carry = box(d, xs[2], y0, bw, "AGV-1", "carry to bay B21")
    a_lower = box(d, xs[3], y0, bw, "AGV-1", "lower tray T17")
    by = lanes["Bay B21"][0]
    b_mode = box(d, xs[0], by, bw, "bay B21", "retrieve mode")
    b_hand = box(d, xs[3], by, bw, "bay B21", "hand over vehicle")
    for a, b in ((a_drive, a_lift), (a_lift, a_carry), (a_carry, a_lower)):
        arrow(d, [(a.x1, a.cy), (b.x0, b.cy)])
    arrow(d, [(b_mode.x1, b_mode.cy), (a_carry.x0 - 26, b_mode.cy), (a_carry.x0 - 26, a_carry.y1 - 12),
              (a_carry.x0, a_carry.y1 - 12)], HL)
    arrow(d, [(a_lower.cx, a_lower.y1), (b_hand.cx, b_hand.y0)], HL)
    d.text(a_carry.x0 - 34, (b_mode.cy + a_carry.y1) / 2 + 4, "bay ready first", size=10.5, fill=HL, anchor="end")
    d.text(a_lower.cx + 8, (a_lower.y1 + b_hand.y0) / 2, "tray in place first", size=10.5, fill=HL)
    order = [(S1, [b_mode]), (S2, [a_drive]), (S3, [a_lift]), (S4, [a_carry]), (S5, [a_lower]), (S6, [b_hand])]
    for k, bs in order:
        with d.only(k):
            for b in bs:
                ring(d, b, T.fg, sw=2.4)
        with d.at(k + 1):
            for b in bs:
                check(d, b)
    save(d)


# --------------------------------------------------------------------------------------------------------------
# d03  two jobs -> event DAG -> execution
# --------------------------------------------------------------------------------------------------------------
def d03_event_dag():
    d = Doc("d03_event_dag", "Two jobs become one event DAG",
            "Job expansion, tray assignment and AGV assignment build the event DAG; the last steps execute it.")
    S0 = d.step("The scheduler receives two jobs. Job A: retrieve the vehicle on tray T17 at bay B21. Job B: clean "
                "the garage by moving tray T27 off waypoint W27.")
    S1 = d.step("Job expansion: each job becomes events with must-happen-before edges. Some details are still "
                "open: where tray T21 goes when it leaves the bay.")
    S2 = d.step("Tray assignment fills the open destination (tray T21 to stall P23) and adds an event for tray T15, "
                "which stands on the route of tray T17.")
    S3 = d.step("AGV assignment: AGV-1 takes job A's three tray moves, in order; AGV-2 takes job B. The event DAG "
                "is complete and goes to motion planning.")
    S4 = d.step("Execution: AGV-1 moves tray T15 to stall P19 while AGV-2 moves tray T27 to stall P24. The two "
                "jobs run in parallel.")
    S5 = d.step("Bay B21 is in retrieve mode; AGV-1 takes the empty tray T21 out of the bay to stall P23.")
    S6 = d.step("AGV-1 brings tray T17 into bay B21 and the bay hands the vehicle over. Both jobs are complete.")
    m = base_map(d, 26)
    p = Play(m)
    scenario_entities(p)
    p.script(S4, "AGV-1", [("drive", [23, 19, 15]), ("lift",), ("carry", [19]), ("lower",)])
    p.script(S4, "AGV-2", [("drive", [27]), ("lift",), ("carry", [24]), ("lower",)])
    p.script(S5, "AGV-1", [("drive", [18, 22, 41, 21]), ("lift",), ("carry", [41, 22, 23]), ("lower",)])
    p.script(S6, "AGV-1", [("drive", [22, 18, 13, 15, 17]), ("lift",), ("carry", [15, 13, 18, 22, 41, 21]),
                           ("lower",)])
    p.draw()
    with d.at(S0, S4):
        bay_pill(d, m, "B21 ready to insert")
    with d.at(S5, S5):
        bay_pill(d, m, "B21 retrieve mode")
    with d.at(S6):
        bay_pill(d, m, "B21 vehicle handed over")
    with d.only(S0):
        node_ring(d, m, 17, HL)
        node_ring(d, m, 21, HL, h=(STALL_W + 1.1) * m.s)
        node_ring(d, m, 27, HL, w=STALL_L * m.s, h=STALL_W * m.s)
        x, y = m.P(17)
        chip(d, x - 30, y + STALL_W * m.s / 2 + 14, "job A", HL, anchor="middle", size=11)
        x, y = m.P(27)
        chip(d, x - 40, y - STALL_W * m.s / 2 - 12, "job B", HL, anchor="middle", size=11)
    with d.at(S2, S3):
        map_route(d, m, [15, 19], TRAY_C, offset=(-12, 0))
        map_route(d, m, [21, 41, 22, 23], TRAY_C, offset=(0, -8))
    with d.at(S1, S3):
        map_route(d, m, [17, 15, 13, 18, 22, 41, 21], TRAY_C, offset=(0, 8))
        map_route(d, m, [27, 24], TRAY_C, offset=(12, 0))
    # ---- event DAG
    mb = m.box
    W = mb.x1
    y0 = mb.y1 + 50
    with d.at(S1):
        d.text(0, y0 - 24, "Event DAG", size=12.5, weight=600, fill=T.fg)
        d.text(text_width("Event DAG", 12.5, "sans", 600) + 12, y0 - 24,
               "boxes = events · arrows = must happen before", size=11.5, fill=T.muted)
    bw, gap = (W - 3 * 26) / 4, 26
    xs = [i * (bw + gap) for i in range(4)]
    y2 = y0 + 50 + 44
    with d.at(S1):
        e0 = box(d, xs[0], y0, bw, "job A", "bay B21 to retrieve mode")
    with d.only(S1):
        e1a = box(d, xs[1], y0, bw, "job A", "tray T21 out of bay, to ?")
    with d.at(S2):
        e1 = box(d, xs[1], y0, bw, "job A", "tray T21 to stall P23")
    with d.at(S1):
        e2 = box(d, xs[2], y0, bw, "job A", "tray T17 to bay B21")
        e3 = box(d, xs[3], y0, bw, "job A", "bay B21 hands over")
        eb = box(d, xs[0], y2, bw, "job B", "tray T27 to stall P24")
        for a, b in ((e0, e1), (e1, e2), (e2, e3)):
            arrow(d, [(a.x1, a.cy), (b.x0, b.cy)])
    with d.at(S2):
        e4 = box(d, xs[2], y2, bw, "job A · added", "tray T15 to stall P19")
        arrow(d, [(e4.cx, e4.y0), (e2.cx, e2.y1)], TRAY_C)
        d.text(e4.cx + 8, (e4.y0 + e2.y1) / 2, "clears the route", size=10.5, fill=TRAY_C)
    with d.only(S1):
        for b in (e0, e1a, e2, e3, eb):
            ring(d, b)
    with d.only(S2):
        for b in (e1, e4):
            ring(d, b)
    with d.at(S3):
        for b, a in ((e4, "AGV-1"), (e1, "AGV-1"), (e2, "AGV-1"), (eb, "AGV-2")):
            chip(d, b.x1 - 6, b.y0 + 15, a, AGV_C, anchor="end", size=10, layer="top")
        arrow(d, [(e4.x0, e4.cy), (e1.cx, e4.cy), (e1.cx, e1.y1)], AGV_C, dash="5 4")
        d.text(e1.cx + 8, (e4.cy + e1.y1) / 2 - 2, "AGV-1 order", size=10.5, fill=AGV_C)
    with d.only(S3):
        for b in (e4, e1, e2, eb):
            ring(d, b, AGV_C)
    for k, bs in ((S4, (e4, eb)), (S5, (e0, e1)), (S6, (e2, e3))):
        with d.only(k):
            for b in bs:
                ring(d, b, T.fg, sw=2.4)
        with d.at(k + 1):
            for b in bs:
                check(d, b)
    save(d)


# --------------------------------------------------------------------------------------------------------------
# d04  tray assignment
# --------------------------------------------------------------------------------------------------------------
def d04_trays():
    d = Doc("d04_trays", "Tray assignment", "Which trays move, where to, and in which order.")
    S0 = d.step("Tray T17 must reach bay B21, but it is enclosed: tray T15 occupies stall P15, tray T20 occupies "
                "stall P20, and charger C16 is a dead end. Bay B21 still holds the empty tray T21.")
    S1 = d.step("Tray assignment chooses a route for tray T17 (via stall P15) and finds what stands on it: tray "
                "T15, and tray T21 in the bay.")
    S2 = d.step("It picks a free stall for each: tray T15 to stall P19, tray T21 to stall P23, and orders both moves "
                "before tray T17's move.")
    m = base_map(d, 26)
    p = Play(m)
    scenario_entities(p, agv2=False, job_b=False)
    p.draw()
    with d.only(S0):
        for nid in (15, 20):
            node_ring(d, m, nid, T.red)
        node_ring(d, m, 21, T.red, h=(STALL_W + 1.1) * m.s)
        x, y = m.P(16)
        d.circle(x, y, 13, fill="none", stroke=T.red, sw=2.2, layer="top")
    with d.at(S1):
        map_route(d, m, [17, 15, 13, 18, 22, 41, 21], TRAY_C, offset=(0, 8))
    with d.only(S1):
        node_ring(d, m, 15, T.red)
        node_ring(d, m, 21, T.red, h=(STALL_W + 1.1) * m.s)
    with d.at(S2):
        map_route(d, m, [15, 19], HL, dash=None, offset=(-12, 0))
        map_route(d, m, [21, 41, 22, 23], HL, dash=None, offset=(0, -8))
    mb = m.box
    y0 = mb.y1 + 40
    bw = 200
    with d.at(S2):
        a = box(d, 0, y0, bw, "added", "tray T15 to stall P19", stroke=HL)
        b = box(d, 0, y0 + 64, bw, "filled", "tray T21 to stall P23", stroke=HL)
        c = box(d, 300, y0 + 32, bw, "job A", "tray T17 to bay B21")
        arrow(d, [(a.x1, a.cy), (260, a.cy), (260, c.cy - 8), (c.x0, c.cy - 8)], HL)
        arrow(d, [(b.x1, b.cy), (260, b.cy), (260, c.cy + 8), (c.x0, c.cy + 8)], HL)
        d.text(c.x1 + 16, c.cy, "both moves must finish first", size=11.5, fill=T.muted)
    save(d)


# --------------------------------------------------------------------------------------------------------------
# d05  AGV assignment
# --------------------------------------------------------------------------------------------------------------
def d05_agvs():
    d = Doc("d05_agvs", "AGV assignment", "Costs per AGV and tray move, then a bottleneck matching.")
    S0 = d.step("For each AGV and each tray move that can start now, a cost: the time to reach the tray and lift "
                "it (illustrative values).")
    S1 = d.step("Bottleneck matching keeps the largest chosen cost as small as possible: AGV-1 takes tray T15 "
                "(14 s), AGV-2 takes tray T27 (6 s). AGV-1 then continues with job A's next tray moves.")
    m = base_map(d, 26)
    p = Play(m)
    scenario_entities(p)
    p.draw()
    pairs = {("AGV-1", "T15"): ([26, 23, 19, 15], 14), ("AGV-1", "T27"): ([26, 27], 22),
             ("AGV-2", "T15"): ([24, 23, 19, 15], 31), ("AGV-2", "T27"): ([24, 27], 6)}
    off = {("AGV-1", "T15"): (-8, 0), ("AGV-2", "T15"): (8, 6), ("AGV-1", "T27"): (0, -8), ("AGV-2", "T27"): (8, 0)}
    win = {("AGV-1", "T15"), ("AGV-2", "T27")}
    for key, (route, cost) in pairs.items():
        with d.only(S0):
            map_route(d, m, route, T.muted, sw=2, dash="5 4", offset=off[key])
        if key in win:
            with d.at(S1):
                map_route(d, m, route, AGV_C, sw=3, dash=None, offset=off[key])
    # cost table
    mb = m.box
    y0 = mb.y1 + 34
    cw, rh = 150, 34
    x0 = 120
    d.text(0, y0 + rh / 2, "time to lift", size=11.5, fill=T.muted)
    for j, t in enumerate(("tray T15", "tray T27")):
        d.text(x0 + j * cw + cw / 2, y0 + rh / 2, t, size=12.5, weight=600, fill=T.fg, anchor="middle")
    for i, a in enumerate(("AGV-1", "AGV-2")):
        y = y0 + (i + 1) * rh
        d.text(0, y + rh / 2, a, size=12.5, family="mono", weight=600, fill=AGV_C)
        d.line(0, y, x0 + 2 * cw, y, stroke=T.border_soft, sw=1)
        for j, t in enumerate(("T15", "T27")):
            cost = pairs[(a, t)][1]
            cx = x0 + j * cw + cw / 2
            d.text(cx, y + rh / 2, f"{cost} s", size=13, family="mono", fill=T.fg2, anchor="middle")
            if (a, t) in win:
                with d.at(S1):
                    d.rect(cx - 34, y + 5, 68, rh - 10, rx=8, fill="none", stroke=AGV_C, sw=2, layer="over")
    with d.at(S1):
        d.text(x0 + 2 * cw + 24, y0 + rh * 1.6, "largest chosen cost: 14 s", size=12, fill=T.fg2)
        d.text(x0 + 2 * cw + 24, y0 + rh * 2.3, "(the other pairing would need 31 s)", size=11.5, fill=T.muted)
    save(d)


ALL = [d01_scenario, d02_actions, d03_event_dag, d04_trays, d05_agvs]

if __name__ == "__main__":
    for f in ALL:
        f()
