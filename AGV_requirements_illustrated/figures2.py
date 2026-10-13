"""Second pass: realistic scale, zoom insets, VDA5050 structure diagrams.

Plan views: 1 m = 40 px (svgkit.PX). AGV assumed 1.8 m x 1.1 m, tape 50 mm.
"""
import math
import figures as F
from figures import status_chip_for, W
from svgkit import SVG, C, STATUS, PX, AGV_L, AGV_W
import uml3 as uml


def m(v):
    return v * PX


# ------------------------------------------------------------------ robot key
def fig_robot_key():
    s = SVG(W, 330, "How to read the robot in these figures",
            "Top-down view. The orange end is always the front. Plan views are drawn to scale: 1 m = 40 px")
    s.robot(220, 180, 0, scale=2.0)
    L, Wd = AGV_L * PX * 2, AGV_W * PX * 2
    # dimensions
    y = 180 + Wd / 2 + 26
    s.line(220 - L / 2, y, 220 + L / 2, y, C["mutedfg"], 1, arrow="mutedfg")
    s.line(220 + L / 2, y, 220 - L / 2, y, C["mutedfg"], 1, arrow="mutedfg")
    s.text(220, y + 18, "1.8 m (assumed)", size=12, anchor="middle", mono=True, color=C["mutedfg"])
    x = 220 - L / 2 - 22
    s.line(x, 180 - Wd / 2, x, 180 + Wd / 2, C["mutedfg"], 1, arrow="mutedfg")
    s.line(x, 180 + Wd / 2, x, 180 - Wd / 2, C["mutedfg"], 1, arrow="mutedfg")
    s.text(x - 8, 184, "1.1 m", size=12, anchor="end", mono=True, color=C["mutedfg"])
    s.arrow(220 + L / 2 + 10, 180, 220 + L / 2 + 70, 180, "accent", 2.2)
    s.text(220 + L / 2 + 14, 170, "heading", size=12.5, color=C["accent"], weight=600)
    s.text(40, 304, "Shown here at 2× scale. Orange bumper = front, chevron points forward, slots = rear.", size=12, color=C["mutedfg"])
    x = 560
    s.text(x, 104, "Same robot at plan-view scale", size=13, weight=600, color=C["fg"])
    s.robot(x + 40, 140, 0)
    s.scale_bar(x + 100, 140, 1)
    s.text(x, 194, "Symbols", size=13, weight=600, color=C["fg"])
    s.tape(x, 220, x + 70, 220)
    s.text(x + 86, 224, "magnetic tape, 50 mm wide", size=12.5)
    s.node(x + 35, 248)
    s.text(x + 86, 252, "node (order waypoint)", size=12.5)
    s.rfid(x + 35, 276)
    s.text(x + 86, 280, "RFID tag", size=12.5)
    s.circle(x + 35, 304, 9, stroke=C["accent"], sw=1.8)
    s.text(x + 86, 308, "magnifier: zoomed inset follows", size=12.5)
    return s


# ------------------------------------------------------------------ 3.1 realistic braking
def fig_3_1():
    s = SVG(W, 450, "Where to stop after an order is cancelled",
            "3.1 stop at the next node if braking allows   3.2 otherwise stop at the node after next   (example values)")
    x0, y0, w, h = 90, 110, 800, 220
    dmax, vmax, a = 14.0, 2.0, 0.25
    X = lambda d: x0 + d / dmax * w
    Y = lambda v: y0 + h - v / vmax * (h - 20)
    s.axes(x0, y0, w + 20, h, "distance along path (m)", "speed (m/s)")
    for d in range(0, 13, 2):
        s.text(X(d), y0 + h + 16, str(d), size=10.5, anchor="middle", mono=True, color=C["mutedfg"])
    for v in (0.5, 1.0, 1.5, 2.0):
        s.line(x0 - 4, Y(v), x0, Y(v), C["mutedfg"], 1)
        s.text(x0 - 8, Y(v) + 4, f"{v:g}", size=10.5, anchor="end", mono=True, color=C["mutedfg"])
    nodes = [(0, "N1"), (6, "N2 next"), (12, "N3")]
    for d, lab in nodes:
        s.line(X(d), y0 + h - 4, X(d), y0 + h + 4, C["ink"], 2)
        s.text(X(d), y0 + h + 36, lab, size=12, anchor="middle", mono=True, weight=600)
    dc = 2.5
    s.line(X(dc), y0, X(dc), y0 + h, C["accent"], 1.4, dash="4 4")
    s.text(X(dc) + 6, y0 + 14, "cancel received at 2.5 m", size=12, color=C["accent"], weight=600)

    def profile(v, stop, col, dash=None):
        brake = stop - v * v / (2 * a)
        pts = [(X(0), Y(v)), (X(brake), Y(v))]
        for i in range(1, 31):
            d = brake + (stop - brake) * i / 30
            pts.append((X(d), Y(math.sqrt(max(0, 2 * a * (stop - d))))))
        s.path("M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts), col, 2.6, dash=dash)
        return brake

    b1 = profile(0.8, 6, C["primary"])
    s.okx(X(6), y0 + h - 22, True, 9)
    s.text(X(6) - 12, Y(0.8) - 34, "3.1  0.8 m/s: needs 1.3 m to stop → stops at N2", size=12, anchor="end", color=C["primary"], weight=600)
    b2 = profile(2.0, 12, C["green"], dash="8 5")
    s.okx(X(12), y0 + h - 22, True, 9)
    s.text(X(12) + 10, Y(2.0) + 4, "", size=12)
    s.text(X(7.0), Y(2.0) - 10, "3.2  2.0 m/s: needs 8 m, only 3.5 m left → stops at N3", size=12, color=C["green"], weight=600)
    s.text(x0, 408 - 2, "Braking assumed at 0.25 m/s². Stopping distance = v² / 2a.", size=11.5, color=C["mutedfg"])
    status_chip_for(s, 90, 416, "3.1", "10 + 10 days, 'will try'")
    status_chip_for(s, 620, 416, "3.2")
    return s


# ------------------------------------------------------------------ 3.6 / 3.7 with zoom insets
def fig_3_6():
    s = SVG(W, 560, "Stopping and rotation precision at a node",
            "3.6 stop within 10 mm of the node centre, never past it   3.7 heading within ±1.5°, overshoot < 0.5°")
    # left: position
    s.text(40, 104, "Stopping at a node", size=13, weight=600, color=C["fg"])
    y = 160
    s.tape(40, y, 450, y)
    nx = 300
    s.node(nx, y, "N", label_dy=-30)
    s.robot(nx, y, 0)
    s.arrow(60, y - 18, 180, y - 18, "slate", 1.6)
    s.text(60, y - 26, "approach", size=12, color=C["mutedfg"])
    s.scale_bar(60, y + 42, 1)
    box = (40, 250, 410, 250)
    s.magnifier(nx, y, 10, box)
    bx, by, bw, bh = box
    k = 4.0  # px per mm
    cx, cy = bx + bw / 2, by + bh / 2 + 6
    s.text(bx + 12, by + 20, "zoom ×100  (4 px = 1 mm)", size=11.5, color=C["accent"], weight=600)
    s.rect(bx + 2, cy - 25 * k, bw - 4, 50 * k, fill=C["tape"], opacity=0.25)
    s.text(bx + 12, cy - 25 * k + 14, "tape, 50 mm wide", size=11, color=C["mutedfg"])
    s.raw(f'<rect x="{cx}" y="{by+30}" width="{bx+bw-2-cx}" height="{bh-34}" fill="url(#hatch-red)"/>')
    s.text(cx + 10, by + 44, "past centre: not allowed", size=11.5, color=C["red"], weight=600)
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="{10*k}" fill="{C["primary"]}" opacity="0.15" stroke="{C["primary"]}" stroke-width="1.6"/>')
    s.line(cx, cy, cx - 10 * k * 0.707, cy + 10 * k * 0.707, C["primary"], 1.4)
    s.text(cx - 34, cy + 44, "10 mm", size=11.5, anchor="end", color=C["primary"], weight=600, mono=True)
    s.line(cx, by + 28, cx, by + bh - 4, C["ink"], 1, dash="3 3")
    s.text(cx - 6, by + bh - 10, "node centre", size=11, anchor="end", color=C["mutedfg"])
    s.circle(cx - 6 * k, cy - 3 * k, 4, fill=C["green"])
    s.text(cx - 6 * k - 8, cy - 3 * k - 8, "valid: 6 mm short", size=11, anchor="end", color=C["green"], weight=600)
    s.scale_bar(bx + bw - 120, by + 20, 0.01, px_per_m=k * 1000)
    status_chip_for(s, 40, 520, "3.6")
    # right: heading
    s.text(500, 104, "Heading after an in-place turn", size=13, weight=600, color=C["fg"])
    rx, ry = 700, 190
    s.tape(rx - 60, ry, rx + 60, ry)
    s.tape(rx, ry - 60, rx, ry + 60)
    s.robot(rx, ry, -90)
    for a in (-1.5, 1.5):
        t = math.radians(-90 + a)
        s.line(rx, ry, rx + 90 * math.cos(t), ry + 90 * math.sin(t), C["primary"], 1, dash="3 2")
    s.text(rx + 10, ry - 88, "±1.5° drawn true size", size=11, color=C["primary"])
    bump = (rx, ry - AGV_L * PX / 2)
    box2 = (500, 250, 430, 250)
    s.magnifier(bump[0], bump[1], 9, box2)
    bx, by, bw, bh = box2
    s.text(bx + 12, by + 20, "sideways offset of the front bumper centre, 0.9 m ahead", size=11.5, color=C["accent"], weight=600)
    k = 3.0
    zy = by + bh / 2 + 10
    gx0, gx1 = bx + 60, bx + bw - 16
    for v, lab, col, dash in [(23.6, "+1.5° = +23.6 mm", C["primary"], "5 4"), (-23.6, "−1.5° = −23.6 mm", C["primary"], "5 4"),
                              (7.9, "overshoot limit 0.5° = 7.9 mm", C["accent"], "2 3")]:
        yy = zy - v * k
        s.line(gx0, yy, gx1, yy, col, 1.2, dash=dash)
        s.text(gx1, yy - 4, lab, size=10.5, anchor="end", color=col, mono=True)
    s.line(gx0, zy, gx1, zy, C["ink"], 1)
    s.text(gx0 - 6, zy + 4, "target", size=10.5, anchor="end", color=C["ink"])
    s.text(gx0 - 6, zy - 23.6 * k + 4, "+24", size=10, anchor="end", mono=True, color=C["mutedfg"])
    s.text(gx0 - 6, zy + 23.6 * k + 4, "−24", size=10, anchor="end", mono=True, color=C["mutedfg"])
    pts = []
    for i in range(0, 121):
        t = i / 120
        off = -26 * math.exp(-5 * t) * math.cos(9 * t) + 2.0 * (1 - math.exp(-5 * t))
        pts.append((gx0 + t * (gx1 - gx0), zy - max(-36, off) * k))
    s.path("M " + " L ".join(f"{a:.1f} {b:.1f}" for a, b in pts), C["fg"], 2)
    s.text(gx1, by + bh - 10, "time →", size=11, anchor="end", color=C["mutedfg"])
    status_chip_for(s, 500, 520, "3.7", "overshoot limit too tight", C["red"])
    return s


# ------------------------------------------------------------------ 7.6 realistic with zoom
def fig_7_6():
    s = SVG(W, 610, "Lateral tracking error must stay within 10 mm",
            "7.6 at every commanded speed up to max, and every payload")
    y = 140
    x0 = 60
    s.text(x0, 104, "Plan view, to scale: 20 m of tape", size=13, weight=600, color=C["fg"])
    s.tape(x0, y, x0 + m(20), y)
    rx = x0 + m(16)
    s.robot(rx, y, 0)
    s.scale_bar(x0, y + 44, 2)
    s.text(x0 + 290, 104, "At this scale 10 mm is 0.4 px, so the inset zooms in on the tape sensor.",
           size=11.5, color=C["mutedfg"])
    sx = rx + AGV_L * PX / 2 - 8
    box = (40, 220, 880, 312)
    s.magnifier(sx, y, 9, box)
    bx, by, bw, bh = box
    k = 4.0
    gx0, gx1 = bx + 100, bx + bw - 24
    zy = by + 30 + 30 * k
    s.text(bx + 12, by + 20, "lateral error at the tape sensor (mm)  vs  distance travelled (m)", size=11.5, color=C["accent"], weight=600)
    s.rect(gx0, zy - 10 * k, gx1 - gx0, 20 * k, fill=C["primary"], opacity=0.08)
    for v, lab, col, dash in [(10, "+10 mm limit", C["primary"], "5 4"), (-10, "−10 mm limit", C["primary"], "5 4"),
                              (25, "tape edge +25 mm", C["slate"], "2 3"), (-25, "tape edge −25 mm", C["slate"], "2 3")]:
        yy = zy - v * k
        s.line(gx0, yy, gx1, yy, col, 1.2, dash=dash)
        s.text(gx0 - 6, yy + 4, f"{v:+d}", size=10, anchor="end", color=col, mono=True)
    s.text(gx0 + 6, zy - 25 * k + 14, "beyond the tape edge the sensor loses the tape", size=10.5, color=C["slate"])
    s.line(gx0, zy, gx1, zy, C["ink"], 1)
    pts = []
    for i in range(0, 401):
        t = i / 400
        amp = 4 + 14 * t ** 2.2
        pts.append((gx0 + t * (gx1 - gx0), zy - amp * math.sin(t * 34) * k))
    s.path("M " + " L ".join(f"{a:.1f} {b:.1f}" for a, b in pts), C["fg"], 1.8)
    for d in range(0, 21, 4):
        xx = gx0 + d / 20 * (gx1 - gx0)
        s.text(xx, zy + 30 * k + 14, f"{d} m", size=10.5, anchor="middle", mono=True, color=C["mutedfg"])
    for d, v in [(2, "0.3 m/s"), (10, "1.0 m/s"), (18, "1.5 m/s")]:
        xx = gx0 + d / 20 * (gx1 - gx0)
        s.text(xx, zy + 30 * k + 32, v, size=10.5, anchor="middle", mono=True, color=C["primary"])
    s.text(gx0 - 30, zy + 30 * k + 32, "speed", size=10.5, anchor="end", color=C["primary"])
    s.text(gx0 - 30, zy + 30 * k + 14, "distance", size=10.5, anchor="end", color=C["mutedfg"])
    status_chip_for(s, 40, 548, "7.6", "HITO: can't be guaranteed with current vehicle", C["red"])
    s.text(40, 592, "Illustrative trace: the error grows with speed and load; the source gives no measured data.", size=11, color=C["mutedfg"], italic=True)
    return s


# ------------------------------------------------------------------ 7.7 physically consistent braking
def fig_7_7():
    s = SVG(W, 500, "Braking for a short final edge",
            "7.7 reach zero exactly at the final node   7.8 plan over consecutive same-primitive edges   7.9 start on an earlier edge")
    x0 = 80
    X = lambda d: x0 + m(d)
    v, a = 1.2, 0.25
    N = [0, 8.5, 16.0, 17.5]
    dstop = v * v / (2 * a)
    top, bot = 140, 280
    Y = lambda vv: bot - vv / v * (bot - top)
    s.axes(x0, 110, m(20) + 10, 170, "distance (m)", "speed (m/s)")
    s.text(x0 - 8, Y(1.2) + 4, "1.2", size=10.5, anchor="end", mono=True, color=C["mutedfg"])

    def prof(brake, col, dash=None):
        stop = brake + dstop
        pts = [(X(0), Y(v)), (X(brake), Y(v))]
        for i in range(1, 31):
            d = brake + dstop * i / 30
            pts.append((X(d), Y(math.sqrt(max(0, 2 * a * (stop - d))))))
        s.path("M " + " L ".join(f"{p:.1f} {q:.1f}" for p, q in pts), col, 2.6, dash=dash)
        return stop

    stop_bad = prof(N[2], C["red"], "7 5")
    s.text(X(stop_bad) + 6, bot - 40, f"stops {stop_bad - N[3]:.1f} m", size=12, color=C["red"], weight=600)
    s.text(X(stop_bad) + 6, bot - 25, "past N4", size=12, color=C["red"], weight=600)
    s.text(X(N[2]) + 4, top - 10, "today: brake from N3", size=12, color=C["red"])
    prof(N[3] - dstop, C["primary"])
    s.circle(X(N[3] - dstop), Y(v), 5, fill=C["primary"])
    s.text(X(N[3] - dstop) - 8, top - 10, f"required: brake at {N[3]-dstop:.1f} m, on edge 2", size=12, anchor="end", color=C["primary"], weight=600)
    s.okx(X(N[3]), bot - 14, True, 8)
    yt = 340
    s.tape(x0, yt, X(20), yt)
    for i, d in enumerate(N):
        s.node(X(d), yt, f"N{i+1}", label_dy=24)
    s.text((X(N[0]) + X(N[1])) / 2, yt - 30, "edge 1 · 8.5 m", size=12, anchor="middle", color=C["mutedfg"])
    s.text((X(N[1]) + X(N[2])) / 2, yt - 30, "edge 2 · 7.5 m", size=12, anchor="middle", color=C["mutedfg"])
    s.text(X(N[3]) + 8, yt - 30, "final edge 1.5 m", size=12, anchor="end", color=C["mutedfg"])
    s.robot(X(2), yt, 0)
    sd0, sd1 = X(N[3] - dstop), X(N[3])
    for xx in (sd0, sd1):
        s.line(xx, yt + 38, xx, yt + 54, C["accent"], 2)
    s.line(sd0, yt + 46, sd1, yt + 46, C["accent"], 2)
    s.text(sd1 + 8, yt + 50, f"stopping distance {dstop:.1f} m", size=12, color=C["accent"], weight=600)
    s.scale_bar(x0, yt + 50, 2)
    s.text(x0 + 140, yt + 54, "1.2 m/s, 0.25 m/s² (example values)", size=11.5, color=C["mutedfg"])
    status_chip_for(s, 40, 430, "7.7", "30 + 30 days")
    w = s.chip(40, 460, "duplicate", "7.8 and 7.9  Closed as duplicate")
    s.text(40 + w + 12, 475.5, "yet HITO notes it plans over one edge only today", size=12, color=C["teal"])
    return s


# ------------------------------------------------------------------ 8.1 realistic lidar fields
def fig_8_1():
    s = SVG(W, 520, "Lidar protective fields: all 64, chosen at runtime, override per edge",
            "8.1 use all 64 fields   8.2 pick by speed, motion primitive, payload size   8.4 remote override edge by edge")
    cx, cy = 140, 230
    front = cx + AGV_L * PX / 2
    fields = [("f3", 0.4, 1.3, "≤ 0.3 m/s"), ("f12", 1.0, 1.4, "≤ 0.8 m/s"), ("f41", 2.2, 1.5, "≤ 1.5 m/s")]
    for i, (lab, ahead, wid, sp) in reversed(list(enumerate(fields))):
        L, Wd = m(ahead), m(wid)
        r = min(12, L / 2)
        s.raw(f'<path d="M {front} {cy-Wd/2} L {front+L-r} {cy-Wd/2} Q {front+L} {cy-Wd/2} {front+L} {cy-Wd/2+r} '
              f'L {front+L} {cy+Wd/2-r} Q {front+L} {cy+Wd/2} {front+L-r} {cy+Wd/2} L {front} {cy+Wd/2} Z" '
              f'fill="{C["accent"]}" fill-opacity="{0.08 + 0.06*(2-i)}" stroke="{C["accent"]}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    s.robot(cx, cy, 0)
    for i, (lab, ahead, wid, sp) in enumerate(fields):
        tx = front + m(ahead)
        ty = cy - m(wid) / 2 - 14 - i * 30
        s.line(tx, cy - m(wid) / 2 + 2, tx, ty + 4, C["accent"], 1)
        s.text(tx, ty, f"{lab}  {ahead} m  {sp}", size=11, color=C["accent"], weight=600, mono=True, anchor="middle")
    s.scale_bar(cx - 40, cy + 70, 1)
    s.text(cx - 40, cy + 100, "to scale; field sizes are example values", size=11.5, color=C["mutedfg"])
    bx = 560
    for i, (lab, val) in enumerate([("wheel speed", "1.2 m/s"), ("motion primitive", "forward"), ("payload size offset", "+150 mm")]):
        yy = 112 + i * 56
        s.rect(bx, yy, 170, 42, fill=C["bg"], stroke=C["border"], rx=6)
        s.text(bx + 12, yy + 18, lab, size=12, color=C["mutedfg"])
        s.text(bx + 12, yy + 35, val, size=13, mono=True, weight=600)
        s.arrow(bx + 172, yy + 21, bx + 222, 196, "slate", 1.4)
    s.rect(bx + 224, 168, 130, 60, fill=C["primary"], rx=8)
    s.text(bx + 289, 194, "field selector", size=12.5, anchor="middle", color="#fff", weight=600)
    s.text(bx + 289, 214, "→ 0 … 63", size=12.5, anchor="middle", color="#fff", mono=True)
    s.text(bx, 300, "8.1 needs rewiring + software (20 + 20 days)", size=12, color=C["mutedfg"])
    s.text(bx, 318, "8.2 schema to be agreed (10 + 10 days)", size=12, color=C["mutedfg"])
    y = 420
    s.text(40, 382, "8.4 remote override of a protective stop, edge by edge", size=13, weight=600, color=C["fg"])
    xs = [60, 260, 460, 660, 900]
    for i in range(4):
        if i == 2:
            s.line(xs[i], y, xs[i + 1], y, C["accent"], 6, cap="butt")
        else:
            s.tape(xs[i], y, xs[i + 1], y)
    s.text((xs[2] + xs[3]) / 2, y + 36, "override active on this edge only", size=12, anchor="middle", color=C["accent"], weight=600)
    for x in xs:
        s.node(x, y)
    s.robot(560, y, 0)
    status_chip_for(s, 40, 478, "8.4", "10 + 10 days")
    w = status_chip_for(s, 300, 478, "8.1")
    status_chip_for(s, 300 + w + 12, 478, "8.2")
    return s


# ------------------------------------------------------------------ 8.3 / 8.5 to scale with zoom
def fig_8_3():
    s = SVG(W, 530, "Pallet coupling and payload weight",
            "8.3 confirm 'pins in cups' and report via VDA5050   8.5 estimate weight from hydraulic pressure")
    s.text(40, 104, "Side view, 1 m = 100 px (pins and cups too small to judge)", size=13, weight=600, color=C["fg"])
    k = 100
    x0, base = 70, 236
    # AGV body 1.8 x 0.3 m
    s.rect(x0, base - 0.3 * k, 1.8 * k, 0.3 * k, fill=C["card"], stroke=C["fg"], sw=2, rx=4)
    s.rect(x0 + 1.8 * k - 6, base - 0.3 * k + 2, 6, 0.3 * k - 4, fill=C["accent"], rx=2)
    for wx in (0.35, 1.45):
        s.circle(x0 + wx * k, base + 4, 6, fill=C["ink"])
    # pallet 2.0 x 0.06 m, 0.05 m above AGV
    py = base - 0.3 * k - 0.05 * k
    s.rect(x0 - 0.1 * k, py - 0.06 * k, 2.0 * k, 0.06 * k, fill=C["card"], stroke=C["fg"], sw=2)
    for cxm in (0.3, 1.5):
        px = x0 + cxm * k
        s.rect(px - 3, py, 6, 0.05 * k, fill=C["slate"])
    s.magnifier(x0 + 0.3 * k, py, 12, (40, 290, 410, 186))
    s.scale_bar(300, 150, 0.5, px_per_m=k)
    bx, by = 40, 290
    s.text(bx + 12, by + 18, "zoom ×10 (1 px = 1 mm): one pin under its cup", size=11.5, color=C["accent"], weight=600)
    z = 2.0

    def pin_cup(ox, off, ok):
        deck = by + 56
        cupw, pinw = 60, 40
        s.rect(ox - 80, deck, 160, 14, fill=C["muted"], stroke=C["fg"], sw=1.2)
        s.rect(ox - cupw / 2, deck, cupw, 14, fill=C["card"], stroke=C["fg"], sw=1.2)
        pinx = ox + off
        top = deck + (0 if ok else 14)
        s.rect(pinx - pinw / 2, top, pinw, 60 - (0 if ok else 14), fill=C["slate"], rx=2)
        s.okx(ox, deck + 84, ok, 9)
        s.text(ox, deck + 106, "pin in cup" if ok else f"{off} mm off: pin hits deck", size=11.5, anchor="middle",
               color=C["green"] if ok else C["red"], weight=600)

    pin_cup(bx + 105, 0, True)
    pin_cup(bx + 305, 35, False)
    s.text(bx + 12, by + 36, "cup Ø 60 mm, pin Ø 40 mm (assumed)", size=10.5, color=C["mutedfg"])
    status_chip_for(s, 40, 492, "8.3")
    s.line(480, 96, 480, 480, C["border"], 1.2)
    s.text(520, 104, "Payload weight from lift pressure", size=13, weight=600, color=C["fg"])
    s.rect(540, 150, 60, 120, fill=C["bg"], stroke=C["fg"], sw=2, rx=4)
    s.rect(548, 200, 44, 62, fill=C["secondary"], rx=2, opacity=0.6)
    s.text(570, 290, "lift cylinder", size=12, anchor="middle", color=C["mutedfg"])
    s.circle(670, 190, 30, fill=C["card"], stroke=C["fg"], sw=2)
    s.line(670, 190, 690, 172, C["accent"], 2.5)
    s.text(670, 240, "pressure sensor", size=12, anchor="middle", color=C["mutedfg"])
    s.arrow(602, 200, 638, 192, "ink", 1.6)
    s.arrow(702, 190, 750, 190, "ink", 1.6)
    s.rect(752, 160, 180, 60, fill=C["bg"], stroke=C["border"], rx=6)
    s.text(766, 184, "weight ≈ P · A / g", size=13, mono=True)
    s.text(766, 206, "→ state.loads[].weight", size=11.5, mono=True, color=C["fg"])
    s.note(520, 320, 410, ["Both blocked: current hardware has no sensor", "for either. Feasible solution still to be discussed."],
           color=C["slate"], size=12.5)
    status_chip_for(s, 520, 492, "8.5")
    return s


def gamepad(s, cx, cy, sc=1.0):
    """Generic console-style gamepad (two grips, offset thumbsticks, d-pad, four face buttons)."""
    def P(x, y):
        return f"{cx + x*sc:.1f} {cy + y*sc:.1f}"
    body = (f"M {P(-60,-34)} C {P(-30,-44)} {P(30,-44)} {P(60,-34)} "
            f"C {P(84,-28)} {P(100,10)} {P(104,40)} "
            f"C {P(108,66)} {P(92,80)} {P(76,72)} "
            f"C {P(62,64)} {P(52,42)} {P(36,34)} "
            f"C {P(16,28)} {P(-16,28)} {P(-36,34)} "
            f"C {P(-52,42)} {P(-62,64)} {P(-76,72)} "
            f"C {P(-92,80)} {P(-108,66)} {P(-104,40)} "
            f"C {P(-100,10)} {P(-84,-28)} {P(-60,-34)} Z")
    s.raw(f'<path d="{body}" fill="{C["card"]}" stroke="{C["fg"]}" stroke-width="2.2" stroke-linejoin="round"/>')
    # shoulder bumpers
    s.raw(f'<path d="M {P(-74,-30)} Q {P(-58,-44)} {P(-34,-41)}" stroke="{C["fg"]}" stroke-width="4" fill="none" stroke-linecap="round"/>')
    s.raw(f'<path d="M {P(74,-30)} Q {P(58,-44)} {P(34,-41)}" stroke="{C["fg"]}" stroke-width="4" fill="none" stroke-linecap="round"/>')
    # left stick (upper left), d-pad (lower left)
    for (x, y) in [(-56, -8), (28, 16)]:
        s.circle(cx + x*sc, cy + y*sc, 15*sc, fill=C["muted"], stroke=C["fg"], sw=1.6)
        s.circle(cx + x*sc, cy + y*sc, 9*sc, fill=C["fg"])
    dx, dy = cx - 28*sc, cy + 16*sc
    s.raw(f'<path d="M {dx-4*sc} {dy-13*sc} h {8*sc} v {9*sc} h {9*sc} v {8*sc} h {-9*sc} v {9*sc} h {-8*sc} v {-9*sc} '
          f'h {-9*sc} v {-8*sc} h {9*sc} Z" fill="{C["slate"]}"/>')
    # face buttons (diamond)
    for (x, y, col) in [(56, -20, C["accent"]), (56, 4, C["green"]), (44, -8, C["primary"]), (68, -8, C["red"])]:
        s.circle(cx + x*sc, cy + y*sc, 6.5*sc, fill=col)
    # centre buttons
    s.circle(cx, cy - 22*sc, 7*sc, fill=C["bg"], stroke=C["fg"], sw=1.4)
    for x in (-14, 14):
        s.rect(cx + x*sc - 4*sc, cy - 6*sc, 8*sc, 5*sc, fill=C["slate"], rx=2)


def fig_5_1():
    s = SVG(W, 666, "Where commonMessage lives, and the fields requested in it",
            "5.1 RFID signal strength   5.3 tape sensor no-reading   5.13 RFID reading   5.15 selected laser field")
    # topic strip
    s.text(28, 104, "1. Topic: a separate MQTT message, next to the standard VDA5050 topics", size=13, weight=600, color=C["fg"])
    parts = ["uagv", "v2", "HITO", "AGV001"]
    x = 28
    for i, p in enumerate(parts):
        w = 18 + len(p) * 8
        s.rect(x, 118, w, 28, fill=C["bg"], stroke=C["border"], rx=5)
        s.text(x + w / 2, 137, p, size=13, anchor="middle", mono=True, color=C["fg"])
        x += w
        s.text(x + 7, 137, "/", size=14, anchor="middle", mono=True, color=C["mutedfg"])
        x += 14
    sx = x
    topics = [("state", False), ("visualization", False), ("connection", False), ("factsheet", False),
              ("order", False), ("instantActions", False), ("commonMessage", True)]
    for i, (t, custom) in enumerate(topics):
        y = 118 + (0 if custom else 0)
    # stack topics as a column of choices
    tx = sx
    bx, by = tx, 118
    for i, (t, custom) in enumerate(topics):
        w = 18 + len(t) * 8
        if bx + w > 932:
            bx, by = tx, by + 34
        s.rect(bx, by, w, 28, fill="#FFF7ED" if custom else C["card"], stroke=C["accent"] if custom else C["border"], rx=5,
               sw=2 if custom else 1)
        s.text(bx + w / 2, by + 19, t, size=12.5, anchor="middle", mono=True,
               color=C["accent"] if custom else C["mutedfg"], weight=700 if custom else 400)
        bx += w + 8
    s.text(tx, 200, "grey: standard VDA5050 topics     orange: HITO's own topic (name assumed; to be confirmed in the 2.8 documentation)",
           size=11.5, color=C["mutedfg"])
    s.text(28, 200, "", size=11)
    # payload
    s.text(28, 240, "2. Payload: what the AGV screen shows, and the JSON HITO would publish", size=13, weight=600, color=C["fg"])
    s.rect(28, 256, 240, 196, fill=C["ink"], rx=10)
    s.text(46, 284, "AGV HMI screen", size=12, color="#94A3B8")
    s.lines(46, 318, ["S   78", "RFID 0x00A7", "Tape  --", "Field 12"], size=15, color="#E2E8F0", mono=True, lh=30)
    jx = 340
    s.rect(jx, 256, 592, 316, fill=C["bg"], stroke=C["border"], rx=8)
    s.text(jx + 16, 278, "topic …/AGV001/commonMessage   (field names are placeholders)", size=11.5, color=C["mutedfg"], italic=True)
    rows = [
        ("{", None, None),
        ('  "headerId": 1042,', None, "hdr"),
        ('  "timestamp": "2026-10-13T08:30:12Z",', None, "hdr"),
        ('  "version": "2.0.0",', None, "hdr"),
        ('  "manufacturer": "HITO",', None, "hdr"),
        ('  "serialNumber": "AGV001",', None, "hdr"),
        ('  "rfidSignalStrength": 78,', "5.1", None),
        ('  "rfidReading": "0x00A7",', "5.13", None),
        ('  "tapeSensor": "",', "5.3", None),
        ('  "laserField": 12', "5.15", None),
        ("}", None, None),
    ]
    from data import BY_ID
    ys = {}
    for i, (t, rid, kind) in enumerate(rows):
        y = 304 + i * 25
        col = C["slate"] if kind == "hdr" else C["fg"]
        s.text(jx + 18, y, t, size=13, mono=True, color=col, weight=600 if rid else 400)
        if rid:
            st = BY_ID[rid][1]
            s.chip(jx + 360, y - 16, st, f"{rid}  {STATUS[st][0]}")
            ys[rid] = y
    # bracket for header
    s.line(jx + 344, 329 - 12, jx + 344, 429 + 4, C["slate"], 1.4)
    s.text(jx + 352, 370, "header, assumed to match", size=10.5, color=C["slate"])
    s.text(jx + 352, 384, "the VDA5050 message header", size=10.5, color=C["slate"])
    for i, rid in enumerate(["5.1", "5.13", "5.3", "5.15"]):
        s.arrow(250, 314 + i * 30, jx - 6, ys[rid] - 5, "slate", 1.2, dash="4 4")
    s.note(28, 588, 904, ["5.3 Volley asks for an empty string or omitted value when the sensor reads nothing. HITO proposes instead that",
                          "a value stuck at 0 for 1 second means no reading. 0 is also a valid reading, so this needs a decision."],
           color=C["accent"], size=12)
    return s


def agv_side(s, x, ground, load):
    """Side view of the AGV, front to the right. load: 0 none, 1 empty pallet, 2 loaded pallet."""
    s.rect(x, ground - 20, 74, 15, fill=C["card"], stroke=C["fg"], sw=1.6, rx=3)
    s.rect(x + 70, ground - 19, 4, 13, fill=C["accent"], rx=1)
    for wx in (14, 60):
        s.circle(x + wx, ground - 4, 4, fill=C["ink"])
    s.line(x - 6, ground, x + 82, ground, C["tape"], 1.2)
    if load >= 1:
        py = ground - 26
        s.rect(x - 4, py, 82, 5, fill=C["card"], stroke=C["fg"], sw=1.4)
        for fx in (6, 36, 66):
            s.rect(x + fx - 4, py + 5, 8, 1.5, fill=C["fg"])
    if load == 2:
        by = ground - 26 - 24
        s.rect(x + 4, by, 66, 24, fill=C["accent"], stroke=C["accent"], sw=1.4, rx=2, opacity=0.35)
        s.rect(x + 4, by, 66, 24, fill="none", stroke=C["accent"], sw=1.4, rx=2)
        s.line(x + 4, by + 12, x + 70, by + 12, C["accent"], 1)
        s.line(x + 37, by, x + 37, by + 24, C["accent"], 1)


def fig_7_4():
    s = SVG(W, 560, "Tuning the tape-following controller: speed axis vs payload axis",
            "7.4 parameters vary with commanded speed   7.5 one set must hold across all payloads (closed as duplicate)")
    x0, y0, cw, ch = 300, 124, 100, 72
    speeds = ["0.2", "0.5", "1.0", "1.5", "2.0"]
    loads = ["unloaded", "empty pallet", "max payload"]
    shades = ["#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6"]
    s.text(x0 + 2.5 * cw, y0 - 30, "commanded speed (m/s)", size=12, anchor="middle", color=C["mutedfg"])
    for j, sp in enumerate(speeds):
        s.text(x0 + j * cw + cw / 2, y0 - 10, sp, size=12, anchor="middle", mono=True, color=C["mutedfg"])
    for i, ld in enumerate(loads):
        ry = y0 + i * ch
        s.raw(f'<g transform="translate(52 {ry + ch - 5}) scale(1.3)">')
        agv_side(s, 0, 0, i)
        s.raw("</g>")
        s.text(x0 - 16, ry + ch / 2 + 4, ld, size=12.5, anchor="end", weight=600)
        for j in range(5):
            s.rect(x0 + j * cw + 2, ry + 2, cw - 4, ch - 4, fill=shades[j], rx=4)
            s.text(x0 + j * cw + cw / 2, ry + ch / 2 + 5, f"K{j+1}", size=13, anchor="middle",
                   mono=True, weight=600, color=C["fg"] if j < 3 else "#fff")
    gx = x0 + 5 * cw
    s.arrow(x0, y0 + 3 * ch + 16, gx, y0 + 3 * ch + 16, "primary", 2.2)
    s.text(x0, y0 + 3 * ch + 38, "7.4  gains change smoothly with commanded speed", size=12.5, color=C["primary"], weight=600)
    s.line(gx + 18, y0, gx + 18, y0 + 3 * ch, C["teal"], 2.2)
    s.line(gx + 12, y0, gx + 24, y0, C["teal"], 2.2)
    s.line(gx + 12, y0 + 3 * ch, gx + 24, y0 + 3 * ch, C["teal"], 2.2)
    s.text(gx + 30, y0 + 98, "7.5  same", size=12.5, color=C["teal"], weight=600)
    s.text(gx + 30, y0 + 116, "column for", size=12.5, color=C["teal"], weight=600)
    s.text(gx + 30, y0 + 134, "every load", size=12.5, color=C["teal"], weight=600)
    s.text(40, y0 - 10, "load condition (side view)", size=12, color=C["mutedfg"])
    yb = y0 + 3 * ch + 76
    s.text(40, yb, "Ruled out", size=13, weight=600, color=C["red"])
    s.okx(54, yb + 30, False, 8)
    s.text(72, yb + 34, "one hard-coded set per motion primitive (violates 7.4)", size=12.5)
    s.okx(54, yb + 58, False, 8)
    s.text(72, yb + 62, "separate tables per payload weight (violates 7.5)", size=12.5)
    s.note(520, yb - 8, 412, ["8.5: the AGV can't measure payload weight today,", "so it couldn't pick a per-weight table anyway.",
                               "Ask HITO to test 7.4 at all three loads."], color=C["accent"], size=12.5)
    status_chip_for(s, 40, yb + 84, "7.4", "30 + 30 days")
    status_chip_for(s, 400, yb + 84, "7.5")
    return s


# ------------------------------------------------------------------ 8.6 at scale
def fig_8_6():
    s = SVG(W, 370, "Remote joystick to recover an AGV that left the tape",
            "8.6 remote movement over a new MQTT topic")
    y = 230
    s.tape(60, y, 620, y)
    s.node(160, y)
    s.node(520, y)
    s.robot(360, y - m(1.0), -15)
    s.okx(360, y - 100, False, 9)
    s.text(380, y - 96, "1 m off tape: auto mode halts", size=12.5, color=C["red"])
    s.path(f"M 392 {y-m(1.0)+6} Q 430 {y-12} 470 {y-1}", C["primary"], 2.2, dash="6 4", arrow="primary")
    s.robot(480, y, 0, ghost=True, color=C["primary"])
    s.text(480, y + 46, "back on tape", size=12.5, anchor="middle", color=C["primary"], weight=600)
    s.scale_bar(60, y + 50, 1)
    jx = 800
    gamepad(s, jx, 190, 1.05)
    s.text(jx, 290, "operator gamepad (not to scale)", size=12, anchor="middle", color=C["mutedfg"])
    s.arrow(jx - 116, 180, 420, y - 70, "slate", 1.6, dash="5 4")
    s.text(560, 192, "MQTT topic (new)", size=12, anchor="middle", color=C["mutedfg"], mono=True)
    status_chip_for(s, 60, 330, "8.6", "30 + 30 days")
    return s


# ------------------------------------------------------------------ VDA5050 topic map
def fig_topics():
    rows = [
        ("order", "fleet → AGV", "route: nodes, edges, actions", "1.1 1.2 3.3 3.4 3.6 3.7 6.1 8.4"),
        ("instantActions", "fleet → AGV", "commands that act now", "2.5 2.6 3.1 8.4"),
        ("state", "AGV → fleet", "full status, errors, loads", "1.3 1.4 2.5 2.6 5.4–5.12 8.3 8.5 8.6"),
        ("visualization", "AGV → fleet", "position + velocity, high rate", "4.1 5.10 5.14"),
        ("connection", "AGV → fleet", "online / offline; Last Will", "2.2 2.3 2.4"),
        ("factsheet", "AGV → fleet", "capabilities; retained", "2.1 6.2"),
        ("commonMessage", "AGV → fleet", "HITO custom, not VDA5050", "4.2 5.1 5.3 5.13 5.15"),
    ]
    s = SVG(W, 160 + len(rows) * 40 + 40, "Where VDA5050 data travels",
            "Each topic is its own MQTT message. Topic path: uagv / v2 / {manufacturer} / {serialNumber} / {topic}")
    y0 = 108
    s.text(40, y0, "topic", size=12, weight=600, color=C["mutedfg"])
    s.text(230, y0, "direction", size=12, weight=600, color=C["mutedfg"])
    s.text(400, y0, "carries", size=12, weight=600, color=C["mutedfg"])
    s.text(640, y0, "requirements", size=12, weight=600, color=C["mutedfg"])
    for i, (t, d, what, rids) in enumerate(rows):
        y = y0 + 16 + i * 40
        custom = t == "commonMessage"
        s.rect(28, y, 904, 34, fill=C["bg"] if not custom else "#FFF7ED", rx=6, stroke=C["accent"] if custom else None, sw=1)
        s.text(40, y + 22, t, size=13, weight=700, mono=True, color=C["fg"] if not custom else C["accent"])
        to_agv = d.startswith("fleet")
        ax0, ax1 = (230, 360) if to_agv else (360, 230)
        s.arrow(ax0, y + 17, ax1, y + 17, "primary" if to_agv else "green", 2)
        s.text(295, y + 12, d, size=10, anchor="middle", color=C["mutedfg"])
        s.text(400, y + 22, what, size=12)
        s.text(640, y + 22, rids, size=11.5, mono=True, color=C["fg"])
    yb = y0 + 16 + len(rows) * 40 + 20
    s.text(40, yb, "Example: uagv/v2/HITO/AGV001/state.   Field structure of each message follows in each section.",
           size=12, color=C["mutedfg"])
    return s


# ------------------------------------------------------------------ structure figures per group
def S(title, sub, roots, notes=None):
    return uml.figure(title, sub, roots, notes)


def fig_uml_1():
    return S("Where the group 1 fields live", "order → nodes[] → nodePosition.theta, and state.driving",
             [("order", [("order.nodes.nodeId", None, None), ("order.nodes.released", None, None),
                         ("order.nodes.nodePosition.theta", "1.1 1.2", "target heading")]),
              ("state", [("state.driving", "1.3 1.4", "true while wheels are commanded")])],
             ["theta is in radians in the order; the figures show degrees for readability (90° = π/2)."])


def fig_uml_2():
    return S("Where the group 2 fields live", "connectionState, the retained factsheet, and instant-action status",
             [("connection", [("connection.connectionState", "2.2–2.4", "Will payload = CONNECTIONBROKEN")]),
              ("factsheet", [("factsheet", "2.1", "whole message sent with MQTT retain = true")]),
              ("instantActions", [("instantActions.actions.actionType", "2.6", "e.g. stopPause"),
                                  ("instantActions.actions.actionId", None, None)]),
              ("state", [("state.actionStates.actionId", None, None),
                         ("state.actionStates.actionStatus", "2.5 2.6", "FINISHED only once applied")])],
             ["The retain flag is an MQTT transport setting, not a field inside the message.",
              "actionStates[].actionId matches the actionId the fleet sent, which is how a command is tracked to FINISHED."])


def fig_uml_3():
    return S("Where the group 3 fields live", "cancelOrder, the released horizon, and the allowed deviations per node",
             [("instantActions", [("instantActions.actions.actionType", "3.1 3.2", "cancelOrder")]),
              ("order", [("order.nodes.released", "3.3 3.4", "false = horizon"),
                         ("order.nodes.nodePosition.allowedDeviationXY", "3.6", "0.01 m = 10 mm"),
                         ("order.nodes.nodePosition.allowedDeviationTheta", "3.7", "0.026 rad = 1.5°"),
                         ("order.edges.released", "3.3 3.4", "false = horizon")])],
             ["VDA5050 already has fields for the 3.6 / 3.7 tolerances; the fleet can send them per node.",
              "There is no standard field for rotation overshoot (3.7, 0.5°)."])


def fig_uml_5():
    return S("Where the group 4 and 5 fields live", "errors, position and velocity in state and visualization, plus HITO's commonMessage",
             [("state", [("state.agvPosition.x", "5.10", None), ("state.agvPosition.y", "5.11", None),
                         ("state.agvPosition.theta", "5.12", "from the estimate, not first RFID"),
                         ("state.errors.errorType", "5.5", "agreed enum string"),
                         ("state.errors.errorLevel", None, None),
                         ("state.errors.errorDescription", "5.8", None),
                         ("state.errors.errorHint", "5.9", "newer spec revision"),
                         ("state.errors.errorReferences.referenceKey", None, None)]),
              ("visualization", [("visualization", "4.1", "rate from iconfig.yaml"),
                                 ("visualization.agvPosition.x", "5.10", None), ("visualization.agvPosition.theta", "5.10", None),
                                 ("visualization.velocity.vx", "5.14", "dx/dt"), ("visualization.velocity.vy", "5.14", "dy/dt"),
                                 ("visualization.velocity.omega", "5.14", "dθ/dt")]),
              ("commonMessage", [("commonMessage", "4.2", "rate from iconfig.yaml"),
                                 ("commonMessage.rfidSignalStrength", "5.1", None), ("commonMessage.rfidReading", "5.13", None),
                                 ("commonMessage.tapeSensor", "5.3", "empty when no reading"),
                                 ("commonMessage.laserField", "5.15", None)])],
             ["5.4 asks that every HMI error code appears as one entry in state.errors[].",
              "commonMessage is HITO's own message; its field names here are placeholders until 2.8 documents them."])


def fig_uml_6():
    return S("Where the group 6 fields live", "a rotation-direction action attached to a node, declared in the factsheet",
             [("order", [("order.nodes.nodeId", None, None),
                         ("order.nodes.actions.actionType", "6.1 6.2", "custom name, to be agreed"),
                         ("order.nodes.actions.blockingType", "6.1", "NONE"),
                         ("order.nodes.actions.actionParameters.key", "6.1", "e.g. \"direction\""),
                         ("order.nodes.actions.actionParameters.value", "6.1", "e.g. \"CW\"")]),
              ("factsheet", [("factsheet.protocolFeatures.agvActions.actionType", "6.2", "AGV lists the custom action"),
                             ("factsheet.protocolFeatures.agvActions.actionScopes", None, "NODE")])],
             ["Custom actions are allowed by VDA5050; the AGV advertises them in factsheet.protocolFeatures.agvActions[]."])


def fig_uml_8():
    return S("Where the group 8 fields live", "loads, safety state, operating mode, override actions and the active lidar field",
             [("state", [("state.operatingMode", "8.6", "MANUAL while joystick-driven"),
                         ("state.loads", "8.3", "no standard 'coupled' field: needs an extension"),
                         ("state.loads.weight", "8.5", "kg"),
                         ("state.safetyState.fieldViolation", "8.4", "true while the protective field is breached")]),
              ("instantActions", [("instantActions.actions.actionType", "8.4", "custom override action")]),
              ("order", [("order.edges.actions.actionType", "8.4", "override scoped to this edge")]),
              ("commonMessage", [("commonMessage.laserField", "8.2 5.15", "selected field index")])],
             ["Group 7 (tape tracking and braking) is internal control behaviour; it adds no message fields."])


ALL = []
_over = {
    "robot_key": fig_robot_key, "3_1_cancel_stop": fig_3_1, "3_6_precision": fig_3_6, "7_6_lateral_error": fig_7_6,
    "7_7_deceleration": fig_7_7, "5_1_common_message": fig_5_1, "7_4_gain_scheduling": fig_7_4, "8_1_lidar_fields": fig_8_1, "8_3_pallet_payload": fig_8_3, "8_6_joystick": fig_8_6,
}
for name, fn in F.ALL:
    ALL.append((name, _over.get(name, fn)))
ALL += [("vda_topics", fig_topics), ("uml_1", fig_uml_1), ("uml_2", fig_uml_2), ("uml_3", fig_uml_3),
        ("uml_5", fig_uml_5), ("uml_6", fig_uml_6), ("uml_8", fig_uml_8)]
