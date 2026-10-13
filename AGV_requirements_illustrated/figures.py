"""All figure builders. Each returns an SVG object."""
import math
from svgkit import SVG, C, STATUS
from data import R, BY_ID

W = 960


def status_chip_for(s, x, y, rid, note=None, note_color=None):
    st = BY_ID[rid][1]
    w = s.chip(x, y, st, f"{rid}  {STATUS[st][0]}")
    if note:
        s.text(x + w + 12, y + 15.5, note, size=12, color=note_color or C["mutedfg"])
    return w


def rotation_sequence(s, x, y, headings, labels, gap=120, color=None, scale=0.85, arrow_label=None):
    """Draw the same robot at successive headings, left to right, joined by arrows."""
    for i, (h, lab) in enumerate(zip(headings, labels)):
        cx = x + i * gap
        s.tape(cx - 44, y, cx + 44, y, w=6)
        s.tape(cx, y - 44, cx, y + 44, w=6)
        s.node(cx, y, None, r=4)
        last = i == len(headings) - 1
        s.robot(cx, y, h, scale=scale, color=(color if last and color else None))
        s.text(cx, y + 66, lab, size=12.5, anchor="middle", mono=True, weight=600,
               color=(color if last and color else C["ink"]))
        if i:
            s.arrow(cx - gap + 50, y - 58, cx - 50, y - 58, "slate", 1.6)
    if arrow_label:
        s.text(x + (len(headings) - 1) * gap / 2, y - 72, arrow_label, size=12, anchor="middle", color=C["mutedfg"])


# ------------------------------------------------------------------ overview
def fig_overview():
    s = SVG(W, 480, "All 52 requirements at a glance",
            "Each tile is one requirement, coloured and lettered by HITO's response")
    cols, cw, ch, gx, gy = 13, 64, 46, 6, 6
    x0, y0 = 28, 86
    for i, r in enumerate(R):
        rid, st = r[0], r[1]
        _, col, letter = STATUS[st]
        x = x0 + (i % cols) * (cw + gx)
        y = y0 + (i // cols) * (ch + gy)
        s.rect(x, y, cw, ch, fill=col, rx=6, opacity=0.14)
        s.rect(x, y, cw, ch, stroke=col, rx=6, sw=1.4)
        s.text(x + 9, y + 20, rid, size=14, weight=600, color=C["ink"], mono=True)
        s.text(x + cw - 9, y + 38, letter, size=12, weight=700, color=col, anchor="end", mono=True)
    # counts bar
    counts = {}
    for r in R:
        counts[r[1]] = counts.get(r[1], 0) + 1
    order = ["works", "implement", "conditional", "duplicate", "process", "blocked", "rejected"]
    by = 324
    s.text(28, by - 10, "Distribution", size=13, weight=600, color=C["fg"])
    bx, bw = 28, 904
    for k in order:
        n = counts.get(k, 0)
        w = bw * n / 52
        s.rect(bx, by, w - 2, 26, fill=STATUS[k][1], rx=3)
        s.text(bx + w / 2 - 1, by + 18, str(n), size=13, color="#FFFFFF", weight=700, anchor="middle")
        bx += w
    # legend
    lx, ly = 28, 370
    for i, k in enumerate(order):
        w = s.chip(lx, ly, k, f"{STATUS[k][0]}  ({counts.get(k,0)})")
        lx += w + 12
        if lx > 700 and i < len(order) - 1:
            lx, ly = 28, ly + 34
    s.text(28, 458, "Numbering gaps in the source: 5.2 and 7.2 do not exist.", size=12, color=C["mutedfg"], italic=True)
    return s


def fig_estimates():
    rows = [r for r in R if r[4]]
    h = 120 + len(rows) * 24 + 40
    s = SVG(W, h, "Effort estimates by requirement",
            "Business days quoted by HITO. Development (solid) followed by testing (light); '/' items omitted")
    x0, y0, scale = 150, 96, 9.0
    for d in range(0, 61, 10):
        x = x0 + d * scale
        s.line(x, y0 - 6, x, y0 + len(rows) * 24, C["muted"], 1)
        s.text(x, y0 - 12, str(d), size=11, anchor="middle", color=C["mutedfg"], mono=True)
    for i, r in enumerate(rows):
        rid, st, _, _, dev, test = r
        y = y0 + i * 24
        col = STATUS[st][1]
        s.text(x0 - 64, y + 15, rid, size=12.5, anchor="end", mono=True, weight=600)
        s.circle(x0 - 48, y + 10, 6, fill=col)
        s.text(x0 - 48, y + 13.5, STATUS[st][2], size=8.5, anchor="middle", color="#fff", weight=700, mono=True)
        s.rect(x0, y + 3, dev * scale, 15, fill=col, rx=2)
        t = test or 0
        if t:
            s.rect(x0 + dev * scale + 1, y + 3, t * scale, 15, fill=col, rx=2, opacity=0.3)
        lbl = f"{dev} + {test}" if test else f"{dev} + /"
        s.text(x0 + (dev + t) * scale + 8, y + 15, lbl, size=11.5, color=C["mutedfg"], mono=True)
    tot_d = sum(r[4] for r in rows)
    tot_t = sum(r[5] or 0 for r in rows)
    yb = y0 + len(rows) * 24 + 26
    s.text(28, yb, f"Sum if done one after another: {tot_d} days development + {tot_t} days testing. "
                   f"Parallelism is not stated in the source.", size=12.5, color=C["mutedfg"])
    return s


def fig_robot_key():
    s = SVG(W, 300, "How to read the robot in these figures",
            "Top-down view. The vehicle is rectangular; the orange end is always the front")
    s.robot(220, 175, 0, scale=1.9)
    s.arrow(300, 175, 380, 175, "accent", 2.2)
    s.text(386, 179, "heading", size=13, color=C["accent"], weight=600)
    # callouts
    s.line(282, 150, 330, 110, C["mutedfg"], 1)
    s.text(334, 108, "orange bumper = front", size=12.5)
    s.line(225, 175, 240, 250, C["mutedfg"], 1)
    s.text(244, 262, "chevron points forward", size=12.5)
    s.line(160, 160, 120, 110, C["mutedfg"], 1)
    s.text(60, 104, "rear slots", size=12.5)
    s.line(200, 216, 160, 262, C["mutedfg"], 1)
    s.text(60, 274, "drive wheels", size=12.5)
    # other symbols
    x = 560
    s.text(x, 104, "Other symbols", size=13, weight=600, color=C["fg"])
    s.tape(x, 136, x + 70, 136)
    s.text(x + 86, 140, "magnetic tape", size=12.5)
    s.node(x + 35, 172)
    s.text(x + 86, 176, "node (order waypoint)", size=12.5)
    s.rfid(x + 35, 206)
    s.text(x + 86, 210, "RFID tag", size=12.5)
    s.robot(x + 35, 246, 0, scale=0.6, ghost=True)
    s.text(x + 86, 250, "dashed = target or later pose", size=12.5)
    s.tag(x + 20, 268, "1.1")
    s.text(x + 86, 283, "requirement id", size=12.5)
    return s


# ------------------------------------------------------------------ group 1
def fig_1_1():
    s = SVG(W, 400, "Rotate in place on a single-node order",
            "1.1  Order = [current node] with a different theta → rotate in place")
    s.text(40, 104, "Today: needs two nodes", size=14, weight=600, color=C["mutedfg"])
    s.tape(60, 220, 420, 220)
    s.node(140, 220, "N1", label_dy=48)
    s.node(340, 220, "N2", label_dy=-16)
    s.robot(140, 220, 0)
    s.arrow(200, 176, 300, 176, "slate", 1.6, dash="5 4")
    s.text(250, 166, "extra node needed", size=12, anchor="middle", color=C["mutedfg"])
    s.text(60, 310, "An order with a single node is not acted on;", size=12.5, color=C["mutedfg"])
    s.text(60, 328, "current logic expects at least two.", size=12.5, color=C["mutedfg"])
    s.line(480, 96, 480, 370, C["border"], 1.2)
    s.text(520, 104, "Required", size=14, weight=600, color=C["fg"])
    rotation_sequence(s, 600, 210, [0, -90], ["θ = 0°", "θ = 90°"], gap=220, color=C["primary"],
                      arrow_label="rotate in place on N1")
    s.text(520, 316, "order.nodes = [N1]   AGV already on N1", size=12.5, mono=True)
    s.text(520, 336, "N1.theta ≠ AGV theta", size=12.5, mono=True)
    status_chip_for(s, 520, 352, "1.1", "10 + 10 days")
    return s


def fig_1_2():
    s = SVG(W, 330, "Rotate to the final node's theta",
            "1.2  On arrival at the last node, turn to that node's theta")
    y = 200
    s.tape(40, y, 560, y)
    xs = [80, 230, 380, 530]
    for i, x in enumerate(xs):
        s.node(x, y, f"N{i+1}", label_dy=-36 if i == 3 else -14)
    s.robot(320, y, 0, ghost=True)
    s.arrow(370, y - 40, 470, y - 40, "slate", 1.6)
    s.text(420, y - 50, "arrives", size=12, anchor="middle", color=C["mutedfg"])
    s.robot(530, y, 0, scale=0.85)
    s.text(530, y + 66, "θ = 0°", size=12.5, anchor="middle", mono=True, weight=600)
    # after-pose inset
    s.arrow(600, y, 700, y, "primary", 2)
    s.text(650, y - 12, "then rotates", size=12, anchor="middle", color=C["primary"])
    cx = 790
    s.tape(cx - 44, y, cx + 44, y, w=6)
    s.tape(cx, y - 44, cx, y + 44, w=6)
    s.node(cx, y, None, r=4)
    s.robot(cx, y, 90, scale=0.85, color=C["primary"])
    s.text(cx, y + 66, "final θ = −90°", size=12.5, anchor="middle", mono=True, weight=600, color=C["primary"])
    s.text(cx, y - 66, "N4", size=12, anchor="middle", mono=True, weight=600, color=C["fg"])
    s.text(40, 300, "If the final node's theta differs from the AGV's theta, the AGV turns to it before finishing the order.",
           size=12.5, color=C["mutedfg"])
    status_chip_for(s, 700, 82, "1.2")
    return s


def fig_1_3():
    s = SVG(W, 430, "Driving flag follows commanded wheel speed",
            "1.3  driving = true whenever commanded wheel speed ≠ 0 (edges and rotations)   1.4  driving = false when it is 0")
    x0, y0, w = 110, 100, 780
    # phases
    phases = [(0, 0.12, "idle"), (0.12, 0.45, "edge move"), (0.45, 0.55, "stop"), (0.55, 0.78, "rotate in place"), (0.78, 1.0, "idle")]
    for a, b, lab in phases:
        s.rect(x0 + a * w, y0, (b - a) * w, 270, fill=C["muted"] if lab in ("edge move", "rotate in place") else "none", opacity=0.6)
        s.text(x0 + (a + b) / 2 * w, y0 + 16, lab, size=12, anchor="middle", color=C["mutedfg"])
    # wheel speed trace
    s.text(28, y0 + 70, "wheel", size=12.5, color=C["mutedfg"])
    s.text(28, y0 + 86, "speed", size=12.5, color=C["mutedfg"])
    base = y0 + 130
    pts = [(0, 0), (0.12, 0), (0.17, 1), (0.40, 1), (0.45, 0), (0.55, 0), (0.58, 0.6), (0.75, 0.6), (0.78, 0), (1, 0)]
    d = " ".join(("M" if i == 0 else "L") + f" {x0 + px*w:.1f} {base - py*90:.1f}" for i, (px, py) in enumerate(pts))
    s.line(x0, base, x0 + w, base, C["border"], 1)
    s.path(d, C["fg"], 2.4)
    # driving flag
    s.text(28, y0 + 205, "driving", size=12.5, color=C["mutedfg"])
    s.text(28, y0 + 221, "flag", size=12.5, color=C["mutedfg"])
    fb = y0 + 240
    fl = [(0, 0), (0.12, 0), (0.12, 1), (0.45, 1), (0.45, 0), (0.55, 0), (0.55, 1), (0.78, 1), (0.78, 0), (1, 0)]
    d = " ".join(("M" if i == 0 else "L") + f" {x0 + px*w:.1f} {fb - py*50:.1f}" for i, (px, py) in enumerate(fl))
    s.line(x0, fb, x0 + w, fb, C["border"], 1)
    s.path(d, C["primary"], 2.6)
    s.text(x0 + 0.285 * w, fb - 58, "true", size=12, anchor="middle", color=C["primary"], weight=600, mono=True)
    s.text(x0 + 0.665 * w, fb - 58, "true  (rotation counts)", size=12, anchor="middle", color=C["primary"], weight=600, mono=True)
    s.text(x0 + 0.5 * w, fb + 18, "false", size=12, anchor="middle", color=C["primary"], weight=600, mono=True)
    w = status_chip_for(s, 110, 390, "1.3")
    status_chip_for(s, 110 + w + 12, 390, "1.4", "4 + 2 days each")
    return s


# ------------------------------------------------------------------ group 2
def fig_2_mqtt():
    s = SVG(W, 560, "MQTT session: retained factsheet and Last Will",
            "2.1 retained factsheet   2.2 Last Will on connect   2.3 / 2.4 broker publishes CONNECTIONBROKEN on crash")
    lanes = [("AGV firmware", 120), ("VDA5050 agent", 340), ("MQTT broker", 580), ("Fleet manager (Volley)", 820)]
    top, bot = 100, 530
    for name, x in lanes:
        s.rect(x - 90, top, 180, 34, fill=C["bg"], stroke=C["border"], rx=6)
        s.text(x, top + 22, name, size=13, anchor="middle", weight=600, color=C["fg"])
        s.line(x, top + 34, x, bot, C["border"], 1.5, dash="4 5")

    def msg(y, a, b, text, color="ink", dash=None, rid=None, mono=False):
        xa, xb = lanes[a][1], lanes[b][1]
        s.arrow(xa + (6 if xb > xa else -6), y, xb - (6 if xb > xa else -6), y, color, 1.8, dash)
        s.text((xa + xb) / 2, y - 8, text, size=12, anchor="middle", color=C[color], mono=mono)
        if rid:
            s.tag(min(xa, xb) + 4 if False else (xa + xb) / 2 - 18, y + 6, rid)

    msg(170, 1, 2, "CONNECT  will = {connectionState: CONNECTIONBROKEN}", "primary", rid="2.2", mono=False)
    msg(230, 1, 2, "PUBLISH factsheet  retain = true", "primary", rid="2.1")
    msg(262, 2, 3, "factsheet (kept for late subscribers)", "slate")
    msg(320, 1, 2, "PUBLISH connection  ONLINE", "ink")
    msg(352, 2, 3, "ONLINE", "slate")
    # crash
    for i, (lab, rid) in enumerate([("firmware crash", "2.3"), ("agent crash", "2.4")]):
        x = lanes[i][1]
        y = 400
        s.path(f"M {x-10} {y-10} L {x+10} {y+10} M {x+10} {y-10} L {x-10} {y+10}", C["red"], 3)
        s.text(x, y + 28, lab, size=12, anchor="middle", color=C["red"], weight=600)
        s.tag(x - 18, y + 36, rid)
    s.text(470, 430, "TCP session drops,", size=12, anchor="middle", color=C["mutedfg"])
    s.text(470, 446, "keep-alive expires", size=12, anchor="middle", color=C["mutedfg"])
    s.arrow(lanes[2][1] + 6, 470, lanes[3][1] - 6, 470, "red", 2)
    s.text(700, 462, "broker publishes the stored Will:", size=12, anchor="middle", color=C["red"])
    s.text(700, 494, "CONNECTIONBROKEN", size=12.5, anchor="middle", color=C["red"], weight=600, mono=True)
    s.note(30, 474, 320, ["HITO: 2.3 / 2.4 are broker behaviour.", "They only work if 2.2 registers the Will."], color=C["accent"], size=12)
    return s


def fig_2_actions():
    s = SVG(W, 430, "When may an instant action report FINISHED?",
            "2.5 only after firmware has applied it   2.6 stopPause only after returning to auto-run")
    x0, w = 160, 740

    def row(y, title, events, finish_at, wrong_at, rid):
        s.text(28, y + 4, title, size=13, weight=600, color=C["fg"])
        s.tag(28, y + 14, rid)
        s.line(x0, y, x0 + w, y, C["mutedfg"], 1.5, arrow="mutedfg")
        for t, lab in events:
            x = x0 + t * w
            s.line(x, y - 7, x, y + 7, C["mutedfg"], 1.5)
            s.text(x, y + 26, lab, size=12, anchor="middle", color=C["mutedfg"])
        xw = x0 + wrong_at * w
        s.okx(xw, y - 30, ok=False, r=9)
        s.text(xw + 14, y - 26, "FINISHED here: not allowed", size=12, color=C["red"])
        xf = x0 + finish_at * w
        s.okx(xf, y - 30, ok=True, r=9)
        s.text(xf + 14, y - 26, "FINISHED", size=12, color=C["green"], weight=600, mono=True)

    row(170, "Any instant action", [(0.05, "agent receives"), (0.32, "passed to firmware"), (0.62, "firmware applied")], 0.62, 0.05, "2.5")
    status_chip_for(s, 760, 92, "2.5")
    row(330, "stopPause", [(0.05, "received"), (0.25, "paused"), (0.5, "resume requested"), (0.78, "back in auto-run")], 0.78, 0.5, "2.6")
    status_chip_for(s, 640, 252, "2.6", "4 + 2 days")
    return s


def fig_governance():
    s = SVG(W, 380, "Interface change control and documentation",
            "2.7 deviation list   2.8 custom message docs   2.9, 5.6, 5.7, 6.2 joint approval")
    # flow
    boxes = [(40, "Proposed change", C["mutedfg"]), (250, "Volley review", C["fg"]), (250, "HITO review", C["fg"]),
             (470, "Both approve", C["green"]), (680, "Release", C["primary"])]
    y = 130
    s.rect(40, y, 170, 50, fill=C["bg"], stroke=C["border"], rx=8)
    s.text(125, y + 30, "Proposed change", size=13, anchor="middle", weight=600)
    s.rect(260, y - 34, 170, 46, fill=C["card"], stroke=C["fg"], rx=8)
    s.text(345, y - 6, "Volley review", size=13, anchor="middle", weight=600, color=C["fg"])
    s.rect(260, y + 38, 170, 46, fill=C["card"], stroke=C["fg"], rx=8)
    s.text(345, y + 66, "HITO review", size=13, anchor="middle", weight=600, color=C["fg"])
    s.rect(490, y, 170, 50, fill=C["card"], stroke=C["green"], rx=8, sw=2)
    s.text(575, y + 30, "Both approve", size=13, anchor="middle", weight=600, color=C["green"])
    s.rect(720, y, 200, 50, fill=C["primary"], rx=8)
    s.text(820, y + 30, "Release", size=13, anchor="middle", weight=600, color="#fff")
    s.arrow(210, y + 20, 258, y - 10, "ink")
    s.arrow(210, y + 30, 258, y + 60, "ink")
    s.arrow(430, y - 10, 488, y + 18, "ink")
    s.arrow(430, y + 60, 488, y + 34, "ink")
    s.arrow(660, y + 25, 718, y + 25, "ink")
    # applies-to
    s.text(40, 250, "Applies to", size=13, weight=600, color=C["fg"])
    items = [("2.9", "any VDA5050 / custom message change"), ("5.6", "errorType strings before release"),
             ("5.7", "errorType strings frozen unless both agree"), ("6.2", "action type for rotation direction")]
    for i, (rid, t) in enumerate(items):
        yy = 266 + i * 26
        s.tag(40, yy, rid)
        s.text(90, yy + 15, t, size=12.5)
    s.text(500, 250, "Documents HITO provides", size=13, weight=600, color=C["fg"])
    s.tag(500, 266, "2.7")
    s.text(550, 281, "list of all deviations from VDA5050", size=12.5)
    s.text(550, 299, "10 days. HITO: future upkeep out of scope", size=12, color=C["accent"])
    s.tag(500, 316, "2.8")
    s.text(550, 331, "commonMessage: names, types, values, examples", size=12.5)
    s.text(550, 349, "4 days. Partly provided already", size=12, color=C["mutedfg"])
    return s


# ------------------------------------------------------------------ group 3
def fig_3_cancel():
    s = SVG(W, 430, "Where to stop after an order is cancelled",
            "3.1 stop at the next node if braking allows   3.2 otherwise stop at the node after next")
    x0, y0, w, h = 90, 110, 800, 220
    nodes = [(0.0, "N1 (passed)"), (0.45, "N2 next"), (0.9, "N3")]
    s.axes(x0, y0, w + 30, h, "distance along path", "speed")
    vb = y0 + 30
    xc = x0 + 0.18 * w
    s.line(xc, y0, xc, y0 + h, C["accent"], 1.4, dash="4 4")
    s.text(xc + 6, y0 + h - 12, "cancel received", size=12, color=C["accent"], weight=600)
    for t, lab in nodes:
        x = x0 + t * w
        s.line(x, y0 + h - 4, x, y0 + h + 4, C["ink"], 2)
        s.text(x, y0 + h + 36, lab, size=12, anchor="middle", mono=True, weight=600)
    # case A: enough distance -> stop at N2
    xa = x0 + 0.45 * w
    pa = f"M {x0} {vb} L {xc} {vb} Q {(xc+xa)/2} {vb} {xa} {y0+h}"
    s.path(pa, C["primary"], 2.6)
    s.okx(xa, y0 + h - 24, True, 9)
    s.text(xa + 22, y0 + h - 50, "3.1  can brake in time", size=12.5, color=C["primary"], weight=600)
    s.text(xa + 22, y0 + h - 34, "→ stop at N2", size=12.5, color=C["primary"])
    # case B: high speed -> cannot stop at N2 -> N3
    vb2 = y0 + 4
    xb = x0 + 0.9 * w
    pb = f"M {x0} {vb2} L {xc} {vb2} Q {xc + 0.5*(xb-xc)} {vb2} {xb} {y0+h}"
    s.path(pb, C["green"], 2.6, dash="8 5")
    s.okx(xb, y0 + h - 24, True, 9)
    s.text(xb - 230, vb2 + 50, "3.2  too fast to stop at N2", size=12.5, color=C["green"], weight=600)
    s.text(xb - 230, vb2 + 66, "→ pass N2, stop at N3", size=12.5, color=C["green"])
    status_chip_for(s, 90, 392, "3.1", "10 + 10 days, 'will try'")
    status_chip_for(s, 600, 392, "3.2")
    return s


def fig_3_release():
    s = SVG(W, 400, "Release horizon: stop at the last released node, unless more is released",
            "3.3 stop when the next edge is not released   3.4 pass through if it is released before arrival")

    def track(y, released_upto, robot_x, title, rid, stop):
        s.text(28, y - 42, title, size=13, weight=600, color=C["fg"])
        s.tag(28, y - 34 + 4, rid)
        xs = [140, 290, 440, 590, 740, 890]
        for i in range(len(xs) - 1):
            rel = i + 1 < released_upto
            if rel:
                s.tape(xs[i], y, xs[i + 1], y)
            else:
                s.line(xs[i], y, xs[i + 1], y, C["tape"], 3, dash="6 6")
        for i, x in enumerate(xs):
            rel = i < released_upto
            s.node(x, y, f"N{i+1}", color=C["fg"] if rel else C["tape"], filled=rel)
        s.robot(robot_x, y, 0, scale=0.8)
        last = xs[released_upto - 1]
        if stop:
            s.rect(last - 3, y - 34, 6, 68, fill=C["red"], rx=2)
            s.text(last, y + 46, "stop here", size=12, anchor="middle", color=C["red"], weight=600)
        else:
            n4 = xs[3]
            s.arrow(n4 - 50, y + 36, n4 + 90, y + 36, "green", 2.2)
            s.text(n4 + 20, y + 58, "passes N4 without stopping", size=12, anchor="middle", color=C["green"], weight=600)

    track(150, 4, 360, "Horizon not extended in time", "3.3", True)
    track(310, 6, 360, "Horizon extended before reaching N4", "3.4", False)
    s.text(28, 380, "Solid edges are released (base); dashed edges are horizon, not yet released.", size=12, color=C["mutedfg"])
    status_chip_for(s, 720, 92, "3.3")
    status_chip_for(s, 720, 252, "3.4")
    return s


def fig_3_5():
    s = SVG(W, 340, "Off-tape timer runs only while wheels are commanded to move",
            "3.5 Time-based off-magnetic-tape detection is armed only when commanded wheel speed ≠ 0")
    x0, w = 150, 740
    s.text(28, 132, "wheel speed", size=12.5, color=C["mutedfg"])
    pts = [(0, 0), (0.1, 0), (0.15, 1), (0.42, 1), (0.47, 0), (0.7, 0), (0.75, 1), (1, 1)]
    base = 150
    d = " ".join(("M" if i == 0 else "L") + f" {x0+px*w:.1f} {base-py*44:.1f}" for i, (px, py) in enumerate(pts))
    s.line(x0, base, x0 + w, base, C["border"], 1)
    s.path(d, C["fg"], 2.4)
    s.text(28, 196, "detection armed", size=12.5, color=C["mutedfg"])
    for a, b in [(0.1, 0.47), (0.7, 1)]:
        s.rect(x0 + a * w, 182, (b - a) * w, 22, fill=C["primary"], rx=4, opacity=0.85)
        s.text(x0 + (a + b) / 2 * w, 198, "armed", size=12, anchor="middle", color="#fff", weight=600)
    s.rect(x0 + 0.47 * w, 182, 0.23 * w, 22, fill=C["muted"], rx=4)
    s.text(x0 + 0.585 * w, 198, "off", size=12, anchor="middle", color=C["mutedfg"])
    s.text(28, 252, "tape reading", size=12.5, color=C["mutedfg"])
    s.rect(x0 + 0.52 * w, 238, 0.12 * w, 22, fill="url(#hatch-red)", stroke=C["red"], rx=4, sw=1)
    s.text(x0 + 0.58 * w, 280, "tape lost while standing still → no fault", size=12, anchor="middle", color=C["green"], weight=600)
    s.rect(x0, 238, 0.52 * w, 22, fill=C["muted"], rx=4)
    s.rect(x0 + 0.64 * w, 238, 0.36 * w, 22, fill=C["muted"], rx=4)
    status_chip_for(s, 28, 296, "3.5")
    return s


def fig_3_precision():
    s = SVG(W, 440, "Stopping and rotation precision at a node",
            "3.6 stop within 10 mm radius, never past the centre   3.7 rotation within ±1.5°, overshoot < 0.5°")
    # left: position
    cx, cy = 250, 250
    s.text(40, 104, "Position (exaggerated scale)", size=13, weight=600, color=C["fg"])
    s.tape(40, cy, 450, cy)
    s.rect(cx, cy - 110, 200, 220, fill="url(#hatch-red)")
    s.text(cx + 100, cy - 90, "past centre: not allowed", size=12, anchor="middle", color=C["red"], weight=600)
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="90" fill="{C["primary"]}" opacity="0.10" stroke="{C["primary"]}" stroke-width="1.5"/>')
    s.line(cx, cy, cx - 64, cy - 64, C["primary"], 1.5)
    s.text(cx - 96, cy - 72, "r = 10 mm", size=12.5, color=C["primary"], weight=600, mono=True)
    s.line(cx, cy - 115, cx, cy + 115, C["ink"], 1.2, dash="3 3")
    s.text(cx, cy + 132, "node centre", size=12, anchor="middle", color=C["mutedfg"])
    s.arrow(60, cy - 30, 200, cy - 30, "ink", 1.6)
    s.text(60, cy - 40, "approach", size=12, color=C["mutedfg"])
    s.circle(cx - 30, cy + 8, 6, fill=C["green"])
    s.text(cx - 40, cy + 40, "valid stop", size=12, anchor="end", color=C["green"], weight=600)
    status_chip_for(s, 40, 402, "3.6")
    # right: rotation (angles drawn x20)
    rx, ry, r = 720, 330, 170
    s.text(520, 104, "Heading after in-place rotation", size=13, weight=600, color=C["fg"])
    a1, a2 = -90 - 30, -90 + 30
    p1 = (rx + r * math.cos(math.radians(a1)), ry + r * math.sin(math.radians(a1)))
    p2 = (rx + r * math.cos(math.radians(a2)), ry + r * math.sin(math.radians(a2)))
    s.raw(f'<path d="M {rx} {ry} L {p1[0]:.1f} {p1[1]:.1f} A {r} {r} 0 0 1 {p2[0]:.1f} {p2[1]:.1f} Z" '
          f'fill="{C["primary"]}" opacity="0.10" stroke="{C["primary"]}" stroke-width="1" stroke-dasharray="4 3"/>')
    s.line(rx, ry, rx, ry - r - 4, C["fg"], 2)
    s.text(rx, ry - r - 12, "target θ", size=12.5, anchor="middle", color=C["fg"], weight=600)
    s.text(p2[0] + 8, p2[1] + 4, "±1.5°", size=13, color=C["primary"], weight=600, mono=True)
    s.arc(rx, ry, 130, 0, -88, "slate", 2, dash="5 4", arrow=False)
    s.arc(rx, ry, 130, -88, -100, "accent", 3)
    s.text(rx - 148, ry - 150, "overshoot < 0.5°", size=12.5, color=C["accent"], weight=600, mono=True)
    s.line(rx - 40, ry - 145, rx - 22, ry - 132, C["accent"], 1.2)
    s.text(rx + 130, ry + 20, "start", size=12, anchor="middle", color=C["mutedfg"])
    s.robot(rx, ry, -90, scale=0.8)
    s.text(520, 380, "angles drawn 20× larger than real", size=11.5, color=C["mutedfg"], italic=True)
    status_chip_for(s, 520, 402, "3.7", "overshoot limit too tight", C["red"])
    return s


# ------------------------------------------------------------------ group 4
def fig_4():
    s = SVG(W, 330, "Publishing rates read from iconfig.yaml",
            "4.1 visualization rate   4.2 commonMessage rate. Parameters don't exist yet; use case to be discussed")
    # config file card
    s.rect(28, 96, 270, 150, fill=C["bg"], stroke=C["border"], rx=8)
    s.text(44, 122, "iconfig.yaml", size=13, weight=600, color=C["fg"], mono=True)
    s.lines(44, 152, ["publish:", "  visualization_hz: 10", "  common_message_hz: 2"], size=12.5, mono=True, lh=22)
    s.text(44, 232, "keys are illustrative", size=11.5, color=C["mutedfg"], italic=True)
    x0, w = 400, 520
    for i, (name, n, rid) in enumerate([("visualization", 11, "4.1"), ("commonMessage", 3, "4.2")]):
        y = 140 + i * 80
        s.text(x0, y - 18, name, size=13, weight=600, mono=True)
        s.tag(x0 + 150, y - 32, rid)
        s.line(x0, y + 10, x0 + w, y + 10, C["mutedfg"], 1.3, arrow="mutedfg")
        for k in range(n):
            x = x0 + 10 + k * (w - 30) / max(n - 1, 1)
            s.line(x, y - 4, x, y + 10, C["primary"], 2.4)
        s.arrow(300, 170 + i * 40, x0 - 10, y + 2, "slate", 1.4, dash="4 4")
    s.text(x0 + w, 290, "time (1 s shown)", size=12, anchor="end", color=C["mutedfg"])
    w = status_chip_for(s, 28, 280, "4.1")
    status_chip_for(s, 28 + w + 12, 280, "4.2", "6 + 4 days each")
    return s


# ------------------------------------------------------------------ group 5
def fig_5_common():
    s = SVG(W, 470, "Fields requested in commonMessage",
            "5.1 RFID signal strength   5.3 tape sensor no-reading   5.13 RFID reading   5.15 selected laser field")
    # HMI screen
    s.rect(28, 96, 250, 200, fill=C["ink"], rx=10)
    s.text(48, 126, "AGV HMI screen", size=12, color="#94A3B8")
    s.lines(48, 160, ["S   78", "RFID 0x00A7", "Tape  --", "Field 12"], size=15, color="#E2E8F0", mono=True, lh=30)
    # JSON card
    jx = 360
    s.rect(jx, 96, 572, 270, fill=C["bg"], stroke=C["border"], rx=8)
    s.text(jx + 18, 122, "commonMessage (field names illustrative)", size=12, color=C["mutedfg"], italic=True)
    rows = [
        ("{", None, None),
        ('  "rfidSignalStrength": 78,', "5.1", 140),
        ('  "rfidReading": "0x00A7",', "5.13", 140),
        ('  "tapeSensor": "",', "5.3", 140),
        ('  "laserField": 12', "5.15", 140),
        ("}", None, None),
    ]
    for i, (t, rid, _) in enumerate(rows):
        y = 156 + i * 34
        s.text(jx + 22, y, t, size=14, mono=True, color=C["fg"])
        if rid:
            st = BY_ID[rid][1]
            s.chip(jx + 330, y - 16, st, f"{rid}  {STATUS[st][0]}")
    # arrows from HMI to json
    for i, yy in enumerate([155, 185, 215, 245]):
        ty = [190, 224, 258, 292][i]
        s.arrow(250, yy, jx - 6, ty - 6, "slate", 1.2, dash="4 4")
    s.note(28, 384, 904, ["5.3 Volley asks for an empty string or omitted value when the sensor reads nothing.",
                          "HITO proposes instead: a value stuck at 0 for 1 second means no reading. 0 is also a valid reading, so this needs a decision."],
           color=C["accent"], size=12.5)
    return s


def fig_5_errors():
    s = SVG(W, 470, "Error reporting in the state message",
            "5.4 every HMI code   5.5 defined errorType enum   5.6 / 5.7 jointly frozen   5.8 errorDescription   5.9 errorHint")
    s.rect(28, 100, 230, 170, fill=C["ink"], rx=10)
    s.text(46, 128, "HMI error list", size=12, color="#94A3B8")
    for i, (c, t) in enumerate([("E021", "tape lost"), ("E104", "lidar stop"), ("E330", "low battery")]):
        s.text(46, 162 + i * 32, c, size=14, color="#FCA5A5", mono=True, weight=600)
        s.text(104, 162 + i * 32, t, size=13, color="#E2E8F0")
    s.arrow(262, 185, 330, 185, "ink", 2)
    s.tag(270, 196, "5.4")
    jx = 340
    s.rect(jx, 96, 592, 250, fill=C["bg"], stroke=C["border"], rx=8)
    rows = [
        ('state.errors[0] = {', None),
        ('  "errorType": "tapeLost",', "5.5"),
        ('  "errorLevel": "FATAL",', None),
        ('  "errorDescription": "No tape under sensor",', "5.8"),
        ('  "errorHint": "Use joystick to re-align"', "5.9"),
        ('}', None),
    ]
    for i, (t, rid) in enumerate(rows):
        y = 130 + i * 34
        s.text(jx + 18, y, t, size=13.5, mono=True, color=C["fg"])
        if rid:
            st = BY_ID[rid][1]
            s.chip(jx + 430, y - 16, st, rid)
    # enum lock
    s.rect(28, 364, 440, 92, fill=C["card"], stroke=C["fg"], rx=8)
    s.text(46, 390, "errorType enum, locked", size=13, weight=600, color=C["fg"])
    s.text(46, 414, "tapeLost | lidarStop | batteryLow | ...", size=12.5, mono=True)
    s.text(46, 438, "changes need Volley + HITO approval (5.6, 5.7)", size=12.5, color=C["mutedfg"])
    s.note(492, 364, 440, ["5.9: HITO doesn't know errorHint. It appears in", "newer VDA5050 versions; confirm the spec baseline."],
           color=C["slate"], size=12.5)
    return s


def fig_5_pose():
    s = SVG(W, 470, "Pose and velocity come from the state estimate",
            "5.10 x, y, θ in state + visualization at TBD Hz   5.11 all axes update   5.12 θ not frozen   5.14 velocity")
    # left: wrong
    def panel(x0, title, good):
        s.text(x0, 104, title, size=13, weight=600, color=C["green"] if good else C["red"])
        s.okx(x0 + (232 if good else 236), 100, good, 9)
        y = 260
        n = 10
        pts = [(x0 + 20 + i * 34, y - 110 * (i / n) ** 1.7) for i in range(n + 1)]
        d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        s.path(d, C["tape"], 8)
        for k in (0, 4, 8):
            s.rfid(*pts[k])
        col = C["primary"] if good else C["red"]
        if not good:
            s.line(pts[0][0], y, pts[-1][0], y, C["red"], 1.2, dash="4 4")
            s.text(pts[-1][0], y + 18, "reported", size=11.5, anchor="end", color=C["red"], italic=True)
        for i in range(0, n, 2):
            px, py = pts[i]
            nx, ny = pts[i + 1]
            th = math.atan2(ny - py, nx - px)
            if not good:
                px, py, th = x0 + 20 + (i / n) * math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]), y, math.atan2(pts[1][1]-pts[0][1], pts[1][0]-pts[0][0])
            s.circle(px, py, 4.5, fill=col)
            s.line(px, py, px + 22 * math.cos(th), py + 22 * math.sin(th), col, 2)
        lx, ly = pts[-1]
        th = math.degrees(math.atan2(ly - pts[-2][1], lx - pts[-2][0]))
        s.robot(lx, ly, th, scale=0.6)
        return y

    panel(40, "Not acceptable: y and θ frozen", False)
    s.text(40, 310, "x grows with edge distance; y and θ stay frozen", size=12.5, color=C["mutedfg"])
    s.text(40, 328, "at the values from the first RFID tag.", size=12.5, color=C["mutedfg"])
    s.line(480, 96, 480, 340, C["border"], 1.2)
    panel(520, "Required: x, y, θ all estimated", True)
    s.text(520, 310, "Samples follow the curved edge with matching", size=12.5, color=C["mutedfg"])
    s.text(520, 328, "heading, straight from the state estimate.", size=12.5, color=C["mutedfg"])
    # bottom message line
    s.rect(28, 356, 904, 96, fill=C["bg"], rx=8)
    s.text(46, 384, 'agvPosition: { x, y, theta }    in state and visualization, at TBD Hz', size=13, mono=True, color=C["fg"])
    s.text(46, 412, 'velocity:    { vx = dx/dt, vy = dy/dt, omega = dθ/dt }', size=13, mono=True, color=C["fg"])
    s.text(46, 438, "5.10, 5.11, 5.12, 5.14: HITO says all already work. Only the report rate is still TBD.", size=12.5, color=C["green"])
    return s


# ------------------------------------------------------------------ group 6
def fig_6():
    s = SVG(W, 480, "Rotation direction chosen by a node action",
            "6.1  an action with blockingType NONE on the node sets clockwise or counter-clockwise   6.2  action type jointly agreed")
    rows = [("clockwise", [0, 90, 180], ["0°", "via −90°", "180°"]),
            ("counter-clockwise", [0, -90, 180], ["0°", "via +90°", "180°"])]
    for i, (lab, hs, ls) in enumerate(rows):
        y = 196 + i * 180
        s.text(28, y - 80, f"action: {lab}", size=13, weight=600, color=C["primary"])
        rotation_sequence(s, 90, y, hs, ls, gap=180, color=C["primary"], scale=0.72)
        # direction glyph
        gx = 520
        if lab == "clockwise":
            s.arc(gx, y, 26, -160, 120, "primary", 2.4)
        else:
            s.arc(gx, y, 26, -20, -300, "primary", 2.4)
        s.text(gx, y + 50, "CW" if lab == "clockwise" else "CCW", size=12, anchor="middle", mono=True, weight=600, color=C["primary"])
    s.rect(620, 96, 312, 210, fill=C["bg"], stroke=C["border"], rx=8)
    s.lines(638, 126, ["node.actions = [{", "  actionType: \"rotateDir\",", "  blockingType: \"NONE\",",
                       "  actionParameters: [", "    {key: \"direction\",", "     value: \"CW\"}]", "}]"],
            size=12, mono=True, color=C["fg"], lh=22)
    s.text(638, 290, "names illustrative; to be agreed (6.2)", size=11.5, color=C["mutedfg"], italic=True)
    w = status_chip_for(s, 620, 320, "6.1", "no estimate")
    status_chip_for(s, 620, 352, "6.2")
    return s


# ------------------------------------------------------------------ group 7
def fig_7_tracking():
    s = SVG(W, 420, "Tape tracking direction under three load conditions",
            "7.1 longitudinal tracking up to max speed   7.3 lateral (strafe) tracking up to max speed")
    loads = ["unloaded", "empty pallet", "max payload"]
    s.text(40, 108, "Longitudinal (forward / reverse along tape)", size=13, weight=600, color=C["green"])
    s.text(500, 108, "Lateral (sideslip / strafe along tape)", size=13, weight=600, color=C["red"])
    for i, lab in enumerate(loads):
        y = 170 + i * 80
        # longitudinal
        s.tape(40, y, 420, y)
        s.robot(200, y, 0, scale=0.75)
        if i >= 1:
            s.rect(178, y - 14, 44, 28, fill="none", stroke=C["accent"], sw=1.5, rx=2, dash="3 2")
        if i == 2:
            s.rect(182, y - 10, 36, 20, fill=C["accent"], rx=2, opacity=0.35)
        s.arrow(250, y, 330, y, "green", 2.2)
        s.text(40, y - 22, lab, size=12, color=C["mutedfg"])
        s.okx(400, y - 22, True, 8)
        # lateral: robot body perpendicular to tape, moving along tape
        s.tape(500, y, 900, y)
        s.robot(660, y, 90, scale=0.75)
        if i >= 1:
            s.rect(646, y - 22, 28, 44, fill="none", stroke=C["accent"], sw=1.5, rx=2, dash="3 2")
        if i == 2:
            s.rect(650, y - 18, 20, 36, fill=C["accent"], rx=2, opacity=0.35)
        s.arrow(700, y, 790, y, "red", 2.2, dash="6 4")
        s.text(500, y - 22, lab, size=12, color=C["mutedfg"])
        s.okx(880, y - 22, False, 8)
    s.text(500, 400, "HITO: current vehicle can't strafe stably at high speed", size=12, color=C["red"])
    status_chip_for(s, 40, 386, "7.1")
    status_chip_for(s, 680, 92 - 26, "7.3")
    return s


def fig_7_gains():
    s = SVG(W, 500, "Tracking-controller parameters: speed axis vs payload axis",
            "7.4 parameters vary with commanded speed   7.5 one set must hold across all payloads (closed as duplicate)")
    x0, y0, cw, ch = 180, 120, 110, 56
    speeds = ["0.2", "0.5", "1.0", "1.5", "2.0"]
    loads = ["unloaded", "empty pallet", "max payload"]
    shades = ["#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6"]
    for j, sp in enumerate(speeds):
        s.text(x0 + j * cw + cw / 2, y0 - 12, f"{sp} m/s", size=12, anchor="middle", mono=True, color=C["mutedfg"])
    for i, ld in enumerate(loads):
        s.text(x0 - 14, y0 + i * ch + ch / 2 + 4, ld, size=12.5, anchor="end")
        for j in range(5):
            s.rect(x0 + j * cw + 2, y0 + i * ch + 2, cw - 4, ch - 4, fill=shades[j], rx=4)
            s.text(x0 + j * cw + cw / 2, y0 + i * ch + ch / 2 + 5, f"K{j+1}", size=13, anchor="middle",
                   mono=True, weight=600, color=C["fg"] if j < 3 else "#fff")
    gx = x0 + 5 * cw
    s.arrow(x0, y0 + 3 * ch + 16, gx, y0 + 3 * ch + 16, "primary", 2.2)
    s.text(x0, y0 + 3 * ch + 38, "7.4  gains change smoothly with commanded speed", size=12.5, color=C["primary"], weight=600)
    s.line(gx + 22, y0, gx + 22, y0 + 3 * ch, C["teal"], 2.2)
    s.line(gx + 16, y0, gx + 28, y0, C["teal"], 2.2)
    s.line(gx + 16, y0 + 3 * ch, gx + 28, y0 + 3 * ch, C["teal"], 2.2)
    s.text(gx + 36, y0 + 70, "7.5  same column", size=12.5, color=C["teal"], weight=600)
    s.text(gx + 36, y0 + 88, "for every payload", size=12.5, color=C["teal"], weight=600)
    # not allowed
    s.text(40, 380, "Ruled out", size=13, weight=600, color=C["red"])
    s.okx(54, 410, False, 8)
    s.text(72, 414, "one hard-coded set per motion primitive (violates 7.4)", size=12.5)
    s.okx(54, 438, False, 8)
    s.text(72, 442, "separate tables per payload weight (violates 7.5)", size=12.5)
    s.note(520, 372, 412, ["8.5: the AGV can't measure payload weight today,", "so it couldn't pick a per-weight table anyway.",
                            "Ask HITO to test 7.4 at all three loads."], color=C["accent"], size=12.5)
    w = status_chip_for(s, 40, 462, "7.4", "30 + 30 days")
    status_chip_for(s, 400, 462, "7.5")
    return s


def fig_7_6():
    s = SVG(W, 330, "Lateral tracking error must stay within 10 mm",
            "7.6 all commanded speeds up to max, all payloads")
    y, x0, x1 = 190, 60, 900
    s.rect(x0, y - 50, x1 - x0, 100, fill=C["primary"], opacity=0.08)
    s.line(x0, y - 50, x1, y - 50, C["primary"], 1.2, dash="5 4")
    s.line(x0, y + 50, x1, y + 50, C["primary"], 1.2, dash="5 4")
    s.text(x0 + 4, y - 58, "+10 mm", size=12, mono=True, color=C["primary"])
    s.text(x0 + 4, y + 70, "−10 mm", size=12, mono=True, color=C["primary"])
    s.tape(x0, y, x1, y, w=6)
    pts = []
    for i in range(0, 241):
        t = i / 240
        amp = 20 + 60 * t ** 2
        pts.append((x0 + t * (x1 - x0), y + amp * math.sin(t * 22)))
    d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    s.path(d, C["fg"], 2)
    s.text(x0 + 60, 112, "low speed: inside band", size=12.5, color=C["green"], weight=600)
    s.text(x1 - 260, 112, "high speed, heavy load: exceeds", size=12.5, color=C["red"], weight=600)
    tdeg = math.degrees(math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0]))
    s.robot(pts[-1][0] - 4, pts[-1][1], tdeg, scale=0.55)
    s.text(x1, 278, "commanded speed →", size=12, anchor="end", color=C["mutedfg"])
    status_chip_for(s, 60, 290, "7.6", "HITO: can't be guaranteed with current vehicle", C["red"])
    return s


def fig_7_decel():
    s = SVG(W, 490, "Braking for a short final edge",
            "7.7 reach zero exactly at the final node   7.8 plan over consecutive same-primitive edges   7.9 start on an earlier edge")
    x0, w = 80, 820
    yt = 330
    nodes = [0, 0.42, 0.78, 0.92]
    s.tape(x0, yt, x0 + w, yt)
    for i, t in enumerate(nodes):
        s.node(x0 + t * w, yt, f"N{i+1}", label_dy=26)
    s.text(x0 + 0.21 * w, yt - 14, "edge 1", size=12, anchor="middle", color=C["mutedfg"])
    s.text(x0 + 0.60 * w, yt - 14, "edge 2", size=12, anchor="middle", color=C["mutedfg"])
    s.text(x0 + 0.85 * w, yt - 14, "short final edge", size=12, anchor="middle", color=C["mutedfg"])
    s.robot(x0 + 0.08 * w, yt, 0, scale=0.7)
    # stopping distance bracket
    sd0, sd1 = x0 + 0.62 * w, x0 + 0.92 * w
    s.line(sd0, yt + 56, sd1, yt + 56, C["accent"], 2)
    s.line(sd0, yt + 48, sd0, yt + 64, C["accent"], 2)
    s.line(sd1, yt + 48, sd1, yt + 64, C["accent"], 2)
    s.text((sd0 + sd1) / 2, yt + 82, "stopping distance at current speed", size=12, anchor="middle", color=C["accent"])
    # speed profiles
    s.axes(x0, 110, w + 10, 170, "distance", "speed")
    top, bot = 140, 280
    xf = x0 + 0.92 * w
    xs3 = x0 + 0.78 * w
    # wrong: decel starts at N3
    s.path(f"M {x0} {top} L {xs3} {top} Q {xs3 + 0.15*w} {top} {x0 + 0.99*w} {bot}", C["red"], 2.4, dash="7 5")
    s.text(x0 + 0.99 * w, bot - 30, "overshoots", size=12, anchor="end", color=C["red"], weight=600)
    s.text(xs3 - 6, top - 10, "today: brake from start of final edge", size=12, anchor="end", color=C["red"])
    # right: start at sd0
    s.path(f"M {x0} {top} L {sd0} {top} Q {(sd0+xf)/2 + 30} {top} {xf} {bot}", C["primary"], 2.8)
    s.circle(sd0, top, 5, fill=C["primary"])
    s.text(sd0 - 6, top + 26, "required: brake starts on edge 2", size=12, anchor="end", color=C["primary"], weight=600)
    s.okx(xf, bot - 16, True, 8)
    status_chip_for(s, 40, 420, "7.7", "30 + 30 days")
    w = s.chip(40, 448, "duplicate", "7.8 and 7.9  Closed as duplicate")
    s.text(40 + w + 12, 463.5, "yet HITO notes it plans over one edge only today", size=12, color=C["teal"])
    return s


# ------------------------------------------------------------------ group 8
def fig_8_lidar():
    s = SVG(W, 520, "Lidar protective fields: all 64, chosen at runtime, override per edge",
            "8.1 use all 64 fields   8.2 pick by speed, motion primitive, payload size   8.4 remote override edge by edge")
    cx, cy = 230, 250
    for k, (L, Wd, op) in enumerate([(240, 150, 0.06), (180, 120, 0.1), (120, 96, 0.16)]):
        s.raw(f'<path d="M {cx+30} {cy-Wd/2} L {cx+30+L*0.7} {cy-Wd/2} Q {cx+30+L} {cy} {cx+30+L*0.7} {cy+Wd/2} L {cx+30} {cy+Wd/2} Z" '
              f'fill="{C["accent"]}" opacity="{op+0.04}" stroke="{C["accent"]}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    s.robot(cx, cy, 0, scale=1.1)
    for lab, L in (("f3", 120), ("f12", 180), ("f41", 240)):
        s.text(cx + 30 + L - 6, cy + 4, lab, size=11.5, color=C["accent"], mono=True, anchor="end", weight=600)
    s.text(cx - 40, cy + 98, "nested fields grow with speed (f = field index)", size=12, color=C["mutedfg"])
    # selector
    bx = 560
    for i, (lab, val) in enumerate([("wheel speed", "1.2 m/s"), ("motion primitive", "forward"), ("payload size offset", "+150 mm")]):
        y = 112 + i * 56
        s.rect(bx, y, 170, 42, fill=C["bg"], stroke=C["border"], rx=6)
        s.text(bx + 12, y + 18, lab, size=12, color=C["mutedfg"])
        s.text(bx + 12, y + 35, val, size=13, mono=True, weight=600)
        s.arrow(bx + 172, y + 21, bx + 222, 196, "slate", 1.4)
    s.rect(bx + 224, 168, 130, 60, fill=C["primary"], rx=8)
    s.text(bx + 289, 194, "field selector", size=12.5, anchor="middle", color="#fff", weight=600)
    s.text(bx + 289, 214, "→ 0 … 63", size=12.5, anchor="middle", color="#fff", mono=True)
    s.tag(bx + 224, 236, "8.2")
    s.tag(bx + 280, 236, "8.1")
    s.text(bx, 300, "8.1 needs rewiring + software (20 + 20 days)", size=12, color=C["mutedfg"])
    s.text(bx, 318, "8.2 schema to be agreed (10 + 10 days)", size=12, color=C["mutedfg"])
    # override per edge
    y = 410
    s.text(40, 372, "8.4 remote override of a protective stop, edge by edge", size=13, weight=600, color=C["fg"])
    xs = [60, 260, 460, 660, 900]
    for i in range(4):
        if i == 2:
            s.line(xs[i], y, xs[i + 1], y, C["accent"], 10, cap="butt")
            s.text((xs[i] + xs[i + 1]) / 2, y + 30, "override active on this edge only", size=12, anchor="middle", color=C["accent"], weight=600)
        else:
            s.tape(xs[i], y, xs[i + 1], y)
    for x in xs:
        s.node(x, y)
    s.robot(560, y, 0, scale=0.6)
    status_chip_for(s, 40, 478, "8.4", "10 + 10 days")
    w = status_chip_for(s, 300, 478, "8.1")
    status_chip_for(s, 300 + w + 12, 478, "8.2")
    return s


def fig_8_pallet():
    s = SVG(W, 420, "Pallet coupling and payload weight",
            "8.3 confirm 'pins in cups' and report via VDA5050   8.5 estimate weight from hydraulic pressure")
    # left: side view pins in cups
    s.text(40, 108, "Side view: lift pins and pallet cups", size=13, weight=600, color=C["fg"])

    def side(x, ok):
        # pallet
        s.rect(x, 150, 180, 20, fill=C["card"], stroke=C["fg"], sw=2, rx=2)
        cups = [x + 40, x + 140]
        for c in cups:
            s.rect(c - 12, 170, 24, 14, fill=C["muted"], stroke=C["fg"], sw=1.5)
        # agv body
        off = 0 if ok else 26
        s.rect(x + 10 + off, 210, 160, 34, fill=C["card"], stroke=C["fg"], sw=2, rx=4)
        s.rect(x + 160 + off, 212, 8, 30, fill=C["accent"], rx=2)
        for c in cups:
            px = c + off
            s.rect(px - 6, 182 if ok else 171, 12, 28 if ok else 39, fill=C["slate"], rx=2)
        s.circle(x + 50 + off, 252, 8, fill=C["ink"])
        s.circle(x + 130 + off, 252, 8, fill=C["ink"])
        s.okx(x + 90, 290, ok, 10)
        s.text(x + 90, 318, "coupled" if ok else "pin missed cup", size=12.5, anchor="middle",
               color=C["green"] if ok else C["red"], weight=600)

    side(40, True)
    side(250, False)
    s.text(40, 352, 'report e.g. state.loads[0].coupled = true', size=12.5, mono=True, color=C["fg"])
    status_chip_for(s, 40, 374, "8.3")
    s.line(480, 96, 480, 400, C["border"], 1.2)
    # right: hydraulic
    s.text(520, 108, "Payload weight from lift pressure", size=13, weight=600, color=C["fg"])
    s.rect(540, 150, 60, 120, fill=C["bg"], stroke=C["fg"], sw=2, rx=4)
    s.rect(548, 200, 44, 62, fill=C["secondary"], rx=2, opacity=0.6)
    s.text(570, 290, "lift cylinder", size=12, anchor="middle", color=C["mutedfg"])
    s.circle(670, 190, 30, fill=C["card"], stroke=C["fg"], sw=2)
    s.line(670, 190, 690, 172, C["accent"], 2.5)
    s.text(670, 240, "P sensor", size=12, anchor="middle", color=C["mutedfg"])
    s.arrow(602, 200, 638, 192, "ink", 1.6)
    s.arrow(702, 190, 750, 190, "ink", 1.6)
    s.rect(752, 160, 170, 60, fill=C["bg"], stroke=C["border"], rx=6)
    s.text(766, 184, "weight ≈ k · P · A", size=13, mono=True)
    s.text(766, 206, "→ state.loads.weight", size=12, mono=True, color=C["fg"])
    status_chip_for(s, 520, 374, "8.5")
    s.note(520, 300, 410, ["Both blocked: current hardware has no sensor", "for it. Feasible solution still to be discussed."],
           color=C["slate"], size=12.5)
    return s


def fig_8_6():
    s = SVG(W, 360, "Remote joystick to recover an AGV that left the tape",
            "8.6 remote movement over a new MQTT topic")
    y = 230
    s.tape(60, y, 620, y)
    s.node(160, y)
    s.node(520, y)
    s.robot(360, y - 70, -25)
    s.okx(360, y - 128, False, 9)
    s.text(380, y - 124, "off tape: auto mode halts", size=12.5, color=C["red"])
    s.path(f"M 380 {y-50} Q 430 {y-10} 470 {y-2}", C["primary"], 2.4, dash="6 4", arrow="primary")
    s.robot(470, y, 0, ghost=True, color=C["primary"], scale=0.8)
    s.text(470, y + 50, "back on tape", size=12.5, anchor="middle", color=C["primary"], weight=600)
    # joystick
    jx = 780
    s.rect(jx - 80, 110, 160, 180, fill=C["bg"], stroke=C["border"], rx=12)
    s.circle(jx, 190, 44, fill=C["card"], stroke=C["fg"], sw=2)
    s.circle(jx + 10, 180, 16, fill=C["fg"])
    s.text(jx, 270, "operator joystick", size=12, anchor="middle", color=C["mutedfg"])
    s.arrow(jx - 82, 200, 520, y - 60, "slate", 1.6, dash="5 4")
    s.text(610, 150, "MQTT topic (new)", size=12, anchor="middle", color=C["mutedfg"], mono=True)
    status_chip_for(s, 60, 320, "8.6", "30 + 30 days")
    return s


ALL = [
    ("overview", fig_overview), ("estimates", fig_estimates), ("robot_key", fig_robot_key),
    ("1_1_single_node_rotation", fig_1_1), ("1_2_final_node_theta", fig_1_2), ("1_3_driving_flag", fig_1_3),
    ("2_1_mqtt_session", fig_2_mqtt), ("2_5_instant_actions", fig_2_actions), ("2_7_change_control", fig_governance),
    ("3_1_cancel_stop", fig_3_cancel), ("3_3_release_horizon", fig_3_release), ("3_5_off_tape", fig_3_5),
    ("3_6_precision", fig_3_precision), ("4_publish_rates", fig_4),
    ("5_1_common_message", fig_5_common), ("5_4_errors", fig_5_errors), ("5_10_pose", fig_5_pose),
    ("6_rotation_direction", fig_6), ("7_1_tracking_direction", fig_7_tracking), ("7_4_gain_scheduling", fig_7_gains),
    ("7_6_lateral_error", fig_7_6), ("7_7_deceleration", fig_7_decel),
    ("8_1_lidar_fields", fig_8_lidar), ("8_3_pallet_payload", fig_8_pallet), ("8_6_joystick", fig_8_6),
]
