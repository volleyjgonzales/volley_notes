"""fig_sim: the simulation stack and how it can check the refactor (127-130).

Doc 09-simulation.html. Facts from sources/repomix-sim.xml and sources/repomix-vis.xml:
* sim_world_node (SimulatorComponent -> Simulator): parses the scenario YAML (ParseScenarioFile), seeds the
  garage tracker through /central/add_agv, add_tray, add_payload (ProcessInitialConditions, retried each tick),
  starts the scenario clock when /central/report says STATUS_STOPPED and consistent, turns due events into
  /central/* (and /scheduler/set_bay_readiness_ratio) service calls, offers queued patrons to
  /bay/b<N>/sim_offer_inserting_payload, checks collisions on every 50 ms update, publishes /sim/report.
* bay_sim_node (BaySimComponent -> BaySim): one per bay; publishes load cells, IO-link, vehicle prox, radar,
  ODP observer; simulated doors; auto-confirms insert / retrieve.
* sim_clock_node (SimClockRos): publishes /clock, real_time_factor (runtime parameter), 5 ms publish period.
* vis (VisManager): RViz marker topics from the snapshot, the schedule, the dispatch and sim reports.
* central DispatchRos::CallPlanner publishes every PlanRequest and PlanResponse on topics "to be bagged".
AGV motion is simulated by agvhito's SimAgvComponent (one per scenario AGV, /agv/a<N>/sim; launcher/sim_nodes.py),
whose code is not in the snapshots; it starts at the scenario's garage_pose and reports through AgvReport.
"""
from __future__ import annotations

from components import connect, frame, label_pill
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import S, T

DOC = "09-simulation.html"
SIM, STACK, SCH, MACH, VIS = T.sky, T.violet, T.green, T.amber, T.teal


def _box(d, x, y, w, title, sub, col, rows=(), h=None, dashed=False):
    h = h or (44 + 18 * len(rows) + (8 if rows else 0))
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=col, sw=1.6, dash="6 4" if dashed else None)
    d.text(x + 12, y + 18, title, size=13, family="mono", weight=700, fill=col)
    d.text(x + 12, y + 35, sub, size=10.5, fill=T.muted)
    yy = y + 56
    for r in rows:
        d.text(x + 14, yy, r, size=11, family="mono", fill=T.fg2)
        yy += 18
    return BBox(x, y, x + w, y + h)


# --------------------------------------------------------------------------------------------------------------
@figure("127_sim_architecture", "The simulation stack", DOC)
def sim_architecture():
    d = Doc("127_sim_architecture", "The simulation stack",
            "Component diagram: the sim package replaces patrons, bay hardware and time; the real central, "
            "scheduler and bay state machines run unchanged.")
    # sim side (left)
    scen = _box(d, 0, 0, 300, "scenario.yaml", "layout, initial_conditions, events", SIM,
                ["layout: <name>", "initial_conditions: trays, agvs,", "  obstructions (or a file name)",
                 "events: [{time, type, ...}]"])
    simw = _box(d, 0, 170, 300, "sim_world", "Simulator, node /sim/sim_world", SIM,
                ["ScenarioRunner: events by time", "Patrons: insert queue", "CollisionDetector: 3D OBBs",
                 "SimClients: /central/* calls", "update every 50 ms (sim time)"])
    bays = _box(d, 0, 410, 300, "bay_sim  x N", "BaySim, node /bay/b<N>/bay_sim", SIM,
                ["load cells, IO-link, prox, radar,", "ODP observer, simulated doors", "auto confirm_insert / retrieve"])
    clock = _box(d, 0, 590, 300, "clock", "SimClockRos, node /sim/clock", SIM,
                 ["/clock every 5 ms (wall)", "real_time_factor (0 = pause)"])
    # real stack (middle)
    cen = _box(d, 420, 170, 330, "central", "dispatcher + garage_tracker (real)", STACK,
               ["/central/start, retrieve, add_tray, ...", "/central/garage_snapshot", "/central/report",
                "plan_request / plan_response topics"])
    sch = _box(d, 860, 170, 260, "scheduler", "real; the code being refactored", SCH,
               ["/scheduler/plan", "/scheduler/set_bay_readiness_ratio"])
    baysm = _box(d, 420, 410, 330, "bay state machine x N", "bay package (real)", MACH,
                 ["reads the simulated sensors", "/bay/b<N>/confirm_insert, report"])
    agv = _box(d, 860, 410, 260, "SimAgv  x N", "agvhito, node /agv/a<N>/sim", SIM,
               ["starts at the scenario's pose", "/agv/a<N>/commandlist", "AgvReport -> garage_tracker"],
               dashed=True)
    vis = _box(d, 860, 590, 260, "vis + RViz", "VisManager: marker topics", VIS,
               ["subscribes to garage_snapshot,", "schedule, report, /sim/report"])
    connect(d, [(scen.cx, scen.y1), (simw.cx, simw.y0)], kind="assoc", color=SIM, sw=1.6, label="ParseScenarioFile")
    connect(d, [(simw.x1, simw.cy - 30), (cen.x0, simw.cy - 30)], kind="assoc", color=SIM, sw=1.6,
            label="events")
    connect(d, [(cen.x0, simw.cy + 30), (simw.x1, simw.cy + 30)], kind="assoc", color=STACK, sw=1.4, dash="5 4",
            label="snapshot, report")
    connect(d, [(simw.cx, simw.y1), (bays.cx, bays.y0)], kind="assoc", color=SIM, sw=1.6,
            label="sim_offer_inserting_payload")
    connect(d, [(bays.x1, bays.cy - 12), (baysm.x0, bays.cy - 12)], kind="assoc", color=SIM, sw=1.6,
            label="sensors, doors")
    connect(d, [(baysm.x0, bays.cy + 22), (bays.x1, bays.cy + 22)], kind="assoc", color=MACH, sw=1.4,
            dash="5 4", label="report; confirm_*")
    connect(d, [(cen.x1, cen.cy - 14), (sch.x0, cen.cy - 14)], kind="assoc", color=SCH, sw=1.8, label="Plan")
    connect(d, [(baysm.cx, baysm.y0), (baysm.cx, cen.y1)], kind="assoc", color=MACH, sw=1.4, dash="5 4",
            label="bay events")
    connect(d, [(cen.x1 - 40, cen.y1), (cen.x1 - 40, agv.cy), (agv.x0, agv.cy)], kind="assoc", color=STACK, sw=1.6,
            label="commands")
    connect(d, [(agv.cx, agv.y0), (agv.cx, sch.y1 + 40), (cen.x1 - 10, sch.y1 + 40), (cen.x1 - 10, cen.y1)],
            kind="assoc", color=MACH, sw=1.4, dash="5 4", label="AgvReport")
    d.text(clock.x1 + 16, clock.cy - 8, "/clock  ->  every node with use_sim_time", size=11.5, family="mono",
           fill=SIM)
    d.text(clock.x1 + 16, clock.cy + 12, "all timers above run in simulated time", size=11, fill=T.muted)
    frame(d, title="The simulation stack",
          subtitle="The sim package stands in for patrons, bay hardware and time, and agvhito's SimAgv for the "
                   "AGVs. Dispatch, the garage tracker, the bay state machines and the scheduler are the real nodes, "
                   "so a scenario exercises the scheduler exactly as it runs on site.",
          badge_key="as-built",
          legend=[("box", SIM, "simulated"), ("box", STACK, "central (real)"), ("box", SCH, "scheduler (real)"),
                  ("box", MACH, "bay state machines (real)"), ("dashbox", SIM, "simulated; code not in the snapshots"),
                  ("arrow", T.fg2, "call or data"), ("dasharrow", T.fg2, "report or reply")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("128_sim_scenario_run", "One scenario run, step by step (animated)", DOC)
def sim_scenario_run():
    d = Doc("128_sim_scenario_run", "One scenario run",
            "UML sequence diagram, animated: seeding, the scenario clock, events becoming service calls, the plan "
            "call, patrons and the simulated bay, and the collision check.")
    parts = [("sim", "Simulator", SIM), ("cen", "central", STACK), ("sch", "scheduler", SCH),
             ("bay", "BaySim + bay SM", MACH), ("agv", "SimAgv x N", SIM)]
    sub = {"sim": "/sim/sim_world", "cen": "dispatcher, tracker", "sch": "/scheduler/plan",
           "bay": "bay_sim, bay", "agv": "agvhito, /agv/a<N>/sim"}
    xs, x = {}, 80
    for k, gap in (("sim", 0), ("cen", 300), ("sch", 250), ("bay", 230), ("agv", 210)):
        x += gap
        xs[k] = x
    col = {k: c for k, _, c in parts}
    head_h = 50
    for k, label, c in parts:
        w = max(text_width(label, 12.5, "mono", 600), text_width(sub[k], 10.5, "sans")) + 28
        d.rect(xs[k] - w / 2, 0, w, head_h, rx=8, fill=T.card, stroke=c, sw=1.5)
        d.text(xs[k], 18, label, size=12.5, family="mono", weight=600, fill=c, anchor="middle")
        d.text(xs[k], 36, sub[k], size=10.5, fill=T.muted, anchor="middle")
    y = head_h + 44
    steps = []

    def step(caption):
        k = d.step(caption)
        steps.append([k, None, None])
        return k

    def mark(yy):
        s_ = steps[-1]
        s_[1] = yy if s_[1] is None else min(s_[1], yy)
        s_[2] = yy if s_[2] is None else max(s_[2], yy)

    def msg(a, b, text, *, ret=False, dy=42, color=None):
        nonlocal y
        c = color or (T.muted if ret else col[a])
        with d.at(steps[-1][0]):
            x1, x2 = xs[a], xs[b]
            xa = x1 + (7 if x2 > x1 else -7)
            xb = x2 - (7 if x2 > x1 else -7)
            d.line(xa, y, xb, y, stroke=c, sw=1.5, dash="6 4" if ret else None, layer="edges")
            d.arrowhead((xb, y), (xa, y), kind="open" if ret else "filled", color=c, size=9)
            label_pill(d, min(xa, xb) + 16, y - 13, text, color=c if not ret else T.fg2, bg=T.bg, size=11.5,
                       anchor="start")
        mark(y - 26)
        mark(y + 6)
        y += dy

    def selfmsg(a, text, sub_text=None, dy=46, color=None):
        nonlocal y
        c = color or col[a]
        with d.at(steps[-1][0]):
            x0 = xs[a] + 7
            d.polyline([(x0, y - 4), (x0 + 30, y - 4), (x0 + 30, y + 18), (x0 + 4, y + 18)], stroke=c, sw=1.5,
                       radius=4)
            d.arrowhead((x0, y + 18), (x0 + 30, y + 18), kind="filled", color=c, size=8)
            d.text(x0 + 40, y + 2, text, size=11.5, family="mono", fill=c)
            if sub_text:
                d.text(x0 + 40, y + 19, sub_text, size=11, fill=T.muted)
        mark(y - 14)
        mark(y + (26 if sub_text else 20))
        y += dy + (8 if sub_text else 0)

    step("Seeding: on every 50 ms update, until it succeeds, the Simulator calls add_agv (id only), add_tray and "
         "add_payload on the garage tracker for every entry of initial_conditions. The SimAgv nodes already stand at "
         "the scenario's poses and report them. Until seeding succeeds the Simulator does nothing else.")
    msg("sim", "cen", "/central/add_agv, add_tray, add_payload")
    step("The scenario clock starts when /central/report says Dispatch is STOPPED and consistent. Event times are "
         "seconds after that moment, in simulated time.")
    msg("cen", "sim", "DispatchReport: STOPPED, consistent", ret=True)
    selfmsg("sim", "running_ = true; start_time_ = now")
    step("Events fall due: ScenarioRunner returns every event with time <= now - start_time_. Each becomes one "
         "service call; most are asynchronous, so the Simulator does not see whether the call succeeded.")
    selfmsg("sim", "GetNextEvents(t)", "t = 0: start_dispatch    t = 5: retrieve_request")
    msg("sim", "cen", "/central/start, /central/retrieve (async)")
    step("Dispatch queues the job, calls the scheduler (this is where the refactored code runs), publishes the "
         "request and response on the plan_request / plan_response topics, and sends commands.")
    msg("cen", "sch", "Plan(PlanRequest)")
    msg("sch", "cen", "PlanResponse", ret=True)
    msg("cen", "agv", "/agv/a<N>/commandlist", color=STACK)
    msg("agv", "cen", "AgvReport -> garage_snapshot", ret=True)
    step("Patrons: a patron_arrival event enters the insert queue. Each update offers the front of the queue to "
         "every bay; a BaySim accepts only when its bay is READY_TO_INSERT. It then fakes the vehicle driving on "
         "and, with auto_confirm_insert, confirms the insert, which makes Dispatch create an INSERT job.")
    selfmsg("sim", "patron_arrival -> Patrons insert queue")
    msg("sim", "bay", "/bay/b<N>/sim_offer_inserting_payload")
    msg("bay", "cen", "confirm_insert -> bay event -> INSERT job", ret=True)
    step("Every update: the Simulator rebuilds a 3D box for every AGV, tray, payload, bay overdrive plate, charger "
         "and obstruction from the latest snapshot, and tests every pair. A carried tray is exempt.")
    msg("cen", "sim", "/central/garage_snapshot", ret=True)
    selfmsg("sim", "RunCollisionCheck(): FindCollisions()", "O(n^2) pairs; AGV + tray within 0.15 m = carried")
    step("A collision ends the run: the Simulator logs FATAL with the pair (for example a3 collided with t17) and "
         "calls rclcpp::shutdown(). Otherwise it publishes /sim/report (running, remaining events, insert queue).")
    selfmsg("sim", "collision -> RCLCPP_FATAL + shutdown", color=T.red)
    selfmsg("sim", "else PublishReport(): /sim/report")
    end_y = y + 4
    for k, _, c in parts:
        d.line(xs[k], head_h, xs[k], end_y, stroke=T.border, sw=1.2, dash="4 5", layer="under")
    x_left, x_right = 0, xs["agv"] + 130
    for k, y0, y1 in steps:
        with d.only(k):
            d.rect(x_left, y0 - 8, x_right - x_left, y1 - y0 + 16, rx=8, fill=T.tint(T.sky, 0.07, T.bg),
                   stroke=T.tint(T.sky, 0.35, T.bg), sw=1, layer="under")
        with d.at(k):
            d.text(x_left - 26, y0 + 4, f"{k + 1}", size=13, family="mono", weight=700, fill=T.sky)
    frame(d, title="One scenario run",
          subtitle="From seeding the garage to the last event. Messages stay on screen; the highlighted band is the "
                   "current step. All times are simulated time from /clock.",
          badge_key="as-built",
          legend=[("arrow", T.fg2, "call or command"), ("dep", T.muted, "reply, report or event")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("129_sim_collision_volumes", "Collision volumes in the simulator", DOC)
def sim_collision_volumes():
    d = Doc("129_sim_collision_volumes", "Collision volumes in the simulator",
            "Side view of the 3D boxes the Simulator builds from the snapshot, and the separating-axis test.")
    # ---- panel A: side elevation (z up), schematic
    X0, G = 0, 250          # ground line y
    sc = 120                # px per metre (schematic)
    d.text(X0, -6, "A · side view: each body is a yaw-rotated box with a height band [z_lo, z_hi]", size=12.5,
           weight=600, fill=T.fg)
    d.line(X0, G, X0 + 760, G, stroke=T.border, sw=1.5)
    d.text(X0 + 764, G + 4, "floor z (per node floor)", size=10.5, fill=T.muted)

    def band(x, w, z0, z1, col, title=""):
        d.rect(x, G - z1 * sc, w, (z1 - z0) * sc, rx=4, fill=T.tint(col, 0.18, T.bg), stroke=col, sw=1.6)
        if title:
            d.text(x + 8, G - z1 * sc + 13, title, size=11.5, family="mono", weight=600, fill=col)

    # AGV under a lifted tray carrying a payload
    band(X0 + 20, 220, 0, 0.28, T.green, "AGV")
    d.rect(X0 + 20, G - 0.40 * sc, 220, 0.12 * sc, rx=3, fill="none", stroke=T.green, sw=1.4, dash="4 3")
    band(X0 + 10, 240, 0.34, 0.42, T.amber)
    band(X0 + 20, 220, 0.42, 1.82, T.pink, "payload")
    d.text(X0 + 256, G - 0.38 * sc + 4, "tray", size=11.5, family="mono", weight=600, fill=T.amber)
    # bay overdrive plate beside a tray in a bay
    bx = X0 + 320
    band(bx, 110, 0, 0.33, T.teal, "ODP")
    band(bx + 120, 130, 0.34, 0.42, T.amber)
    d.text(bx + 120, G - 0.42 * sc - 8, "tray in the bay", size=10.5, fill=T.amber)
    d.rect(bx, G + 10, 110, 10, rx=3, fill="none", stroke=T.teal, sw=1.4, dash="4 3")
    # charger
    band(X0 + 600, 60, 0, 0.9, T.violet, "chg")
    # band descriptions
    rows = [(T.green, "AGV: floor .. lowered + (raised - lowered) x max lift fraction;"),
            (T.green, "   dashed: lifted, it reaches into the tray band (carried-tray exemption)"),
            (T.amber, "tray: (kTrayHeight - kTrayThickness) .. kTrayHeight"),
            (T.pink, "payload: tray top .. + payload.height_m, on the tray's pose"),
            (T.teal, "bay overdrive plate: floor .. tray top - 6 mm; when the system"),
            (T.teal, "   doors are open it moves to -0.2 .. -0.1 m and never collides"),
            (T.violet, "charger, obstruction: static, registered once")]
    for i, (c, r) in enumerate(rows):
        d.text(X0, G + 44 + i * 19, r, size=11.5, fill=c if not r.startswith("   ") else T.muted)
    # ---- panel B: separating axis test (top view)
    Y0 = G + 200
    d.text(X0, Y0, "B · top view: two boxes are apart if one of the four face normals separates them", size=12.5,
           weight=600, fill=T.fg)
    import math

    def obb(cx, cy, hx, hy, yaw, col, label):
        c, s = math.cos(yaw), math.sin(yaw)
        pts = [(cx + c * a * hx - s * b * hy, cy - (s * a * hx + c * b * hy)) for a, b in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        d.polygon(pts, fill=T.tint(col, 0.18, T.bg), stroke=col, sw=1.8)
        d.text(cx, cy + 4, label, size=12, family="mono", weight=600, fill=col, anchor="middle")
        return pts

    pa = obb(X0 + 150, Y0 + 120, 90, 40, 0.0, T.green, "a1")
    pb = obb(X0 + 330, Y0 + 130, 70, 34, 0.6, T.amber, "t17")
    # projection on box a's x axis (horizontal)
    ax_y = Y0 + 230
    d.line(X0 + 20, ax_y, X0 + 500, ax_y, stroke=T.border, sw=1.2)
    d.text(X0 + 504, ax_y + 4, "a1's x axis", size=10.5, fill=T.muted)
    for pts, col in ((pa, T.green), (pb, T.amber)):
        lo, hi = min(p[0] for p in pts), max(p[0] for p in pts)
        d.line(lo, ax_y - (6 if col == T.green else -6), hi, ax_y - (6 if col == T.green else -6), stroke=col, sw=4)
    lo_b = min(p[0] for p in pb)
    hi_a = max(p[0] for p in pa)
    d.text((hi_a + lo_b) / 2, ax_y + 26, "gap on this axis -> no collision", size=11, fill=T.fg2, anchor="middle")
    # rules
    rx = X0 + 560
    rules = ["DoesIntersect(a, b): SAT on a's two normals", "and on b's two normals, and the z bands overlap",
             "(touching is not a collision)", "", "Exempt: an AGV and a tray whose centres are", "within 0.15 m in x and y (a carried tray)",
             "", "No safety margin is added to the boxes;", "VRCs are not among the checked bodies"]
    for i, r in enumerate(rules):
        d.text(rx, Y0 + 60 + i * 19, r, size=11.5, fill=T.fg2 if r and not r.startswith("Not") else T.muted)
    frame(d, title="Collision volumes in the simulator",
          subtitle="Rebuilt from the latest garage snapshot on every update; any overlapping pair ends the run. "
                   "Heights are drawn to show the bands, not measured: the constants (kTrayHeight, kAgvHeightRaised, "
                   "...) live in common, outside the snapshots.",
          badge_key="schematic",
          legend=[("box", T.green, "AGV"), ("box", T.amber, "tray"), ("box", T.pink, "payload"),
                  ("box", T.teal, "bay overdrive plate"), ("box", T.violet, "charger")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("130_sim_verification_loop", "Using the simulator to verify the refactor", DOC)
def sim_verification_loop():
    d = Doc("130_sim_verification_loop", "Using the simulator to verify the refactor",
            "Three checks: record realistic plan calls on the baseline, replay them offline through both "
            "schedulers, and rerun the scenarios closed loop on the candidate.")
    BASE, CAND, CHK = T.muted, T.sky, T.green
    # row 1: record
    s1 = _box(d, 0, 0, 230, "scenario set", "YAML, real-site layouts", T.fg2,
              ["retrieve with blockers,", "insert queue, clean, ..."])
    b1 = _box(d, 300, 0, 290, "sim run · baseline", "pinned commit, RTF fixed", BASE,
              ["real central + scheduler", "ros2 bag record:", "  plan_request, plan_response,", "  job lists, reports"])
    bag = _box(d, 660, 0, 250, "baseline bag", "per scenario", BASE,
               ["N plan calls (request, response)", "KPIs: jobs done / failed,", "durations, collisions = 0"])
    connect(d, [(s1.x1, s1.cy), (b1.x0, s1.cy)], kind="assoc", color=T.fg2, sw=1.6)
    connect(d, [(b1.x1, s1.cy), (bag.x0, s1.cy)], kind="assoc", color=BASE, sw=1.6)
    # row 2: replay
    y2 = 210
    rep = _box(d, 300, y2, 290, "offline replay test", "gtest, no ROS graph needed", CAND,
               ["for each recorded PlanRequest:", "  old Scheduler::Plan(request)", "  new Scheduler::Plan(request)",
                "  Canonicalize both, compare"])
    res = _box(d, 660, y2, 250, "parity result", "canonical comparison, Verification tab", CHK,
               ["p = passed / recorded calls", "gate: p = 1", "sanity: old replay == recorded"])
    connect(d, [(bag.cx, bag.y1), (bag.cx, y2 - 30), (rep.cx, y2 - 30), (rep.cx, rep.y0)], kind="assoc",
            color=BASE, sw=1.6, label="requests + responses")
    connect(d, [(rep.x1, rep.cy), (res.x0, rep.cy)], kind="assoc", color=CHK, sw=1.6)
    # row 3: closed loop
    y3 = 430
    c3 = _box(d, 300, y3, 290, "sim run · candidate", "same scenarios, same settings", CAND,
              ["refactored scheduler", "ros2 bag record (same topics)"])
    kpi = _box(d, 660, y3, 250, "KPI comparison", "against the baseline runs", CHK,
               ["no collision, no stuck run", "same jobs complete / fail", "durations within tolerance"])
    connect(d, [(s1.cx, s1.y1), (s1.cx, c3.cy), (c3.x0, c3.cy)], kind="assoc", color=T.fg2, sw=1.6)
    connect(d, [(c3.x1, c3.cy), (kpi.x0, c3.cy)], kind="assoc", color=CHK, sw=1.6)
    connect(d, [(bag.x1, bag.cy), (bag.x1 + 40, bag.cy), (bag.x1 + 40, kpi.cy), (kpi.x1, kpi.cy)], kind="assoc",
            color=BASE, sw=1.4, dash="5 4", label="baseline KPIs")
    for yy, t, s in ((s1.y0 + 4, "1 · record", "once per baseline"), (y2 + 4, "2 · replay", "every PR"),
                     (y3 + 4, "3 · closed loop", "before merging a stage")):
        d.text(-24, yy + 10, t, size=12.5, weight=600, fill=T.fg, anchor="end")
        d.text(-24, yy + 28, s, size=11, fill=T.muted, anchor="end")
    frame(d, title="Using the simulator to verify the refactor",
          subtitle="Replay checks the scheduler alone on realistic requests and is deterministic; the closed loop "
                   "checks that the whole stack still behaves, and is not. Dispatch already publishes every plan "
                   "request and response for bagging.",
          badge_key="proposed",
          legend=[("box", BASE, "baseline (pinned commit)"), ("box", CAND, "candidate (refactor branch)"),
                  ("box", CHK, "check")])
    return d
