"""fig_sim3: the simulation explained for a reader new to it (127, 131, 135, 139).

Colour roles in the Simulation tab (kept to three, plus red for problems):
  blue  (T.sky)   - a simulated stand-in: runs only in simulation and replaces hardware, people or time;
  green (T.green) - the scheduler, the code being refactored;
  grey  (neutral) - everything else: production software that runs unchanged, and files on disk.
Shapes carry the other distinctions: a file icon is a configuration file on disk, a window icon is a running
operating-system process, a dot-in-circle is a ROS node.

Facts from sources/repomix-launcher.xml (launcher/sim_nodes.py, bay_nodes.py, central_nodes.py, vrc_nodes.py,
vecs_nodes.py), sources/repomix-sim.xml (Simulator, BaySim, SimClockRos, scripts/), sources/repomix-scenario.xml
and sources/5675_pecos_combined.yaml (the QA sandbox: bay B21, stalls P15..P24, AGV chargers C14, C16, no EvCharge,
no VRC).
"""
from __future__ import annotations

from components import chip, connect, frame, label_pill
from icons import icon
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC = "09-simulation.html"
SIM, SCH, PROD = T.sky, T.green, T.fg2
FILE = T.muted


def region(d, x, y, w, h, title, sub=None, kind=None):
    d.rect(x, y, w, h, rx=14, fill=T.tint(T.fg2, 0.035, T.bg), stroke=T.border_soft, sw=1.2, layer="bg")
    tx = x + 18
    if kind:
        icon(d, kind, x + 28, y + 24, 22, T.fg2)
        tx = x + 50
    d.text(tx, y + 20, title, size=14, weight=600, fill=T.fg)
    if sub:
        d.text(tx, y + 38, sub, size=11, fill=T.muted)


def nodebox(d, x, y, w, name, role, col, *, h=None, mono=True, kind="node", role_lines=None):
    lines = role_lines or wrap(role, w - 44, 11, "sans") if role else []
    h = h or (30 + 16 * len(lines) + 8)
    d.rect(x, y, w, h, rx=8, fill=T.tint(col, 0.08, T.bg) if col != PROD else T.card, stroke=col, sw=1.5)
    icon(d, kind, x + 16, y + 16, 14 if kind == "node" else 18, col)
    d.text(x + 32, y + 17, name, size=12, family="mono" if mono else "sans", weight=600,
           fill=col if col != PROD else T.fg)
    for i, ln in enumerate(lines):
        d.text(x + 32, y + 35 + 16 * i, ln, size=11, fill=T.muted)
    return BBox(x, y, x + w, y + h)


# --------------------------------------------------------------------------------------------------------------
@figure("127_sim_architecture", "On site and in simulation", DOC)
def sim_architecture():
    d = Doc("127_sim_architecture", "On site and in simulation",
            "Three columns. Left: what the software talks to on site. Middle: the production software, which is "
            "the same in both cases. Right: the stand-in that replaces each real thing in a simulation.")
    XL, WL = 0, 250          # on site
    XM, WM = 330, 420        # production software
    XR, WR = 830, 330        # stand-ins
    top = 0
    region(d, XL, top, WL, 640, "On site", "the real world", "person")
    region(d, XM, top, WM, 640, "Production software", "the same code on site and in simulation", "gear")
    region(d, XR, top, WR, 640, "In simulation", "stand-ins that exist only in simulation", "process")
    d.rect(XR, top, WR, 640, rx=14, fill="none", stroke=SIM, sw=1.4, dash="7 5", layer="bg")

    # scheduler at the top of the middle column
    y0 = 64
    sch = nodebox(d, XM + 20, y0, WM - 40, "/scheduler/scheduler",
                  "plans: turns jobs into an action graph for the AGVs, bays and VRCs. Talks only to Dispatch, "
                  "never to hardware", SCH)
    for xx, ww in ((XL, WL), (XR, WR)):
        d.text(xx + ww / 2, sch.cy - 2, "nothing: the scheduler talks", size=11, fill=T.faint, anchor="middle")
        d.text(xx + ww / 2, sch.cy + 15, "to no hardware", size=11, fill=T.faint, anchor="middle")
    rows = [
        # (left icon, left title, left sub, middle name, middle role, right name, right role, right icon)
        ("person", "patrons, operators", "park and collect cars; app",
         "/central/dispatcher, garage_tracker", "Dispatch: jobs, plan calls, commands; the garage state",
         "/sim/sim_world", "plays the patrons and the operator from the scenario; checks for collisions"),
        ("agv", "AGVs", "via agvhito proxy_node", None, None,
         "/agv/a<N>/sim", "one virtual AGV per AGV in the scenario; executes commands, reports its pose"),
        ("bay", "bay hardware", "sensors, doors, load cells",
         "/bay/b<N>/bay_state_machine, ...", "runs the bay: insert and retrieve sequences",
         "/bay/b<N>/bay_sim", "fakes the bay's sensors and doors; confirms the insert for the patron"),
        ("bolt", "EV chargers", "VECS hardware",
         "/vecs/v<N>/vecs_node", "runs one EV charger",
         "/vecs/v<N>/vecs_sim_node", "fakes the charger"),
        ("lift", "VRC (car lift)", "BLift sites only",
         "/bay/b<N>/vrc_lift_bridge", "connects a BLift bay to its VRC",
         "/vrc/r<N>/manager", "fakes the VRC: floors, travel, doors"),
        ("clock", "wall clock", "real time",
         "every node", "reads the time for its timers",
         "/sim/clock", "publishes simulated time on /clock; can run faster, slower, or pause"),
    ]
    y = sch.y1 + 26
    cen = None
    for i, (ik, lt, ls, mn, mr, rn, rr) in enumerate(rows):
        rh = 76
        cy = y + rh / 2 - 8
        # left
        icon(d, ik, XL + 32, cy, 24, T.muted)
        d.text(XL + 56, cy - 4, lt, size=12.5, weight=600, fill=T.fg2)
        d.text(XL + 56, cy + 13, ls, size=10.5, fill=T.muted)
        # middle
        if mn is not None:
            if i == 0:
                mb = nodebox(d, XM + 20, y, WM - 40, mn, mr, PROD, h=rh * 2 - 12)
                cen = mb
            else:
                mb = nodebox(d, XM + 20, y, WM - 40, mn, mr, PROD, h=rh - 12)
        # right
        rb = nodebox(d, XR + 16, y, WR - 32, rn, rr, SIM, h=rh - 12)
        # connectors: left (dashed grey, on site) and right (blue, in simulation)
        tgt_y = cy
        d.line(XL + WL - 14, tgt_y, XM + 20, tgt_y, stroke=T.border, sw=1.3, dash="5 4", layer="edges")
        d.arrowhead((XM + 20, tgt_y), (XL + WL - 14, tgt_y), kind="open", color=T.border, size=8)
        d.line(XR + 16, tgt_y, XM + WM - 20, tgt_y, stroke=SIM, sw=1.6, layer="edges")
        d.arrowhead((XM + WM - 20, tgt_y), (XR + 16, tgt_y), kind="open", color=SIM, size=8)
        y += rh
    # scheduler <-> dispatcher
    connect(d, [(sch.cx, sch.y1), (sch.cx, cen.y0)], kind="assoc", color=SCH, sw=1.8)
    d.text(sch.cx + 8, (sch.y1 + cen.y0) / 2 + 4, "/scheduler/plan", size=10.5, family="mono", fill=SCH)
    # bottom notes
    yb = 640 + 26
    d.text(XL, yb, "Only in simulation, besides the stand-ins: the Simulator's collision check, which watches "
                   "every AGV, tray and car and stops the run if two overlap,", size=11.5, fill=T.fg2)
    d.text(XL, yb + 19, "and the visualizer (/vis/visualizer) for RViz and Foxglove. Both read the production "
                        "software's published state; neither changes it.", size=11.5, fill=T.fg2)
    frame(d, title="On site and in simulation",
          subtitle="A simulation keeps every piece of production software and replaces only what is outside it: "
                   "people, hardware and the clock. Each row shows one real thing, the software that talks to it, "
                   "and the stand-in that takes its place. The scheduler never talks to hardware, so it cannot tell "
                   "the difference.",
          badge_key="as-built",
          legend=[("box", SIM, "simulated stand-in (sim only)"), ("box", PROD, "production software (unchanged)"),
                  ("box", SCH, "the scheduler (being refactored)"), ("icon:node", PROD, "ROS node"),
                  ("dasharrow", T.border, "on site: talks to"), ("arrow", SIM, "in simulation: talks to")],
          footnote="<N> is an id: AGV-1 runs as /agv/a1/sim, bay B21's nodes are /bay/b21/... . On site the AGVs "
                   "are reached through agvhito's proxy_node, which the simulation does not start.")
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("131_sim_layout_to_site", "From files to running processes", DOC)
def sim_layout_to_site():
    d = Doc("131_sim_layout_to_site", "From files to running processes",
            "Worked example on the Pecos QA sandbox. Top: the configuration files on disk. Middle: the launch "
            "file reads them once. Bottom: the ROS nodes that then run, grouped by the reason they exist.")
    W = 1180
    # ---- band 1: files
    region(d, 0, 0, W, 214, "1 · Configuration files", "text files on disk; read once when the simulation starts",
           "file")
    files = [
        ("scenario file", "5675_pecos_sandbox_qa_full_start_in_auto.yaml", "package scenario",
         ["layout: 5675_pecos_sandbox_qa", "2 AGVs: AGV-1 on P15, AGV-2 on P17", "6 trays with cars on P15..P24",
          "set-up events: start Dispatch at 1 s"]),
        ("layout file", "5675_pecos_sandbox_qa", "the map (Layout file tab)",
         ["1 bay: B21", "6 stalls, waypoints, 2 AGV chargers", "no EV charger (EvCharge) node", "no VRC (vrcs)"]),
        ("parameter files", "params.yaml, params_sim.yaml,", "params_5675_pecos_sandbox_qa.yaml",
         ["defaults: speeds, door times, ...", "simulation: no database", "this site: bay sensor box 5.791 m",
          "(package launcher)"]),
    ]
    fw, gap = 360, 30
    for i, (kind, name, sub, rows) in enumerate(files):
        x = 20 + i * (fw + gap)
        d.rect(x, 54, fw, 146, rx=10, fill=T.card, stroke=T.border, sw=1.3)
        icon(d, "file", x + 22, 76, 24, FILE)
        d.text(x + 42, 72, kind, size=13, weight=600, fill=T.fg)
        d.text(x + 42, 88, name, size=10.5, family="mono", fill=T.fg2)
        d.text(x + 42, 102, sub, size=10.5, family="mono" if i == 2 else "sans", fill=T.muted)
        for k, r in enumerate(rows):
            d.text(x + 16, 124 + 18 * k, "· " + r, size=11, fill=T.fg2)
    # ---- band 2: launch
    ly = 244
    d.rect(W / 2 - 300, ly, 600, 64, rx=10, fill=T.card, stroke=T.border, sw=1.3)
    icon(d, "launch", W / 2 - 272, ly + 32, 26, T.fg2)
    d.text(W / 2 - 250, ly + 26, "2 · ros2 launch launcher sim.launch.py scenario:=<scenario file>", size=12,
           family="mono", weight=600, fill=T.fg)
    d.text(W / 2 - 250, ly + 46, "reads the three kinds of file, merges the parameters, decides which nodes to start, "
                                 "starts them", size=11, fill=T.muted)
    connect(d, [(W / 2, 214), (W / 2, ly)], kind="flow", color=T.border, sw=1.6, size=8)
    connect(d, [(W / 2, ly + 64), (W / 2, ly + 100)], kind="flow", color=T.border, sw=1.6, size=8)
    # ---- band 3: processes
    by = ly + 100
    region(d, 0, by, W, 452, "3 · Running ROS nodes", "programs that run until the simulation stops; they talk over "
                                                      "topics and services", "process")
    cw, cg = 270, 22
    cols = [
        ("from the scenario's agvs list", "one simulated AGV per entry", [
            ("/agv/a1/sim", "AGV-1: starts on P15, heading 90, lowered", SIM),
            ("/agv/a2/sim", "AGV-2: starts on P17, heading 90, lowered", SIM)]),
        ("from the layout's Bay nodes", "one set per bay; here only B21", [
            ("/bay/b21/bay_state_machine", "runs the bay's insert and retrieve sequences", PROD),
            ("/bay/b21/vehicle_estimator", "measures the car from the sensors", PROD),
            ("/bay/b21/bay_guidance", "guides the driver in the bay", PROD),
            ("/bay/b21/bay_sim", "fakes B21's sensors and doors", SIM)]),
        ("from EvCharge nodes, vrcs entries", "none: this layout has neither", []),
        ("always, whatever the files say", "the fixed part of the stack", [
            ("/sim/clock", "simulated time", SIM),
            ("/sim/sim_world", "patrons, scenario events, collision check", SIM),
            ("/central/dispatcher, ...", "Dispatch, garage tracker, monitors", PROD),
            ("/scheduler/scheduler", "the planner", SCH),
            ("/vis/visualizer", "pictures for RViz and Foxglove", PROD)]),
    ]
    for i, (why, sub, nodes) in enumerate(cols):
        x = 20 + i * (cw + cg)
        d.text(x, by + 74, why, size=12, weight=600, fill=T.fg)
        d.text(x, by + 91, sub, size=11, fill=T.muted)
        yy = by + 108
        if not nodes:
            d.rect(x, yy, cw, 60, rx=8, fill="none", stroke=T.border_soft, sw=1.2, dash="5 4")
            d.text(x + cw / 2, yy + 34, "no node started", size=11.5, fill=T.faint, anchor="middle")
        for name, role, col in nodes:
            b = nodebox(d, x, yy, cw, name, role, col)
            yy = b.y1 + 8
    frame(d, title="From files to running processes",
          subtitle="Configuration files describe the site and the starting state; they do nothing by themselves. "
                   "The launch file reads them and starts the running programs (ROS nodes). Which nodes exist "
                   "follows from the files: one simulated AGV per AGV in the scenario, one set of bay nodes per bay "
                   "in the layout, and a fixed set that every simulation has.",
          badge_key="as-built",
          legend=[("icon:file", FILE, "configuration file (on disk)"), ("icon:node", PROD, "running ROS node"),
                  ("box", SIM, "simulated stand-in"), ("box", PROD, "production software"),
                  ("box", SCH, "the scheduler")],
          footnote="The QA sandbox's chargers C14 and C16 are AGV chargers (AgvCharge), which need no node of their "
                   "own; only EV chargers (EvCharge) get a VECS node.")
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("135_sim_launch_topology", "Processes, and the nodes inside them", DOC)
def sim_launch_topology():
    d = Doc("135_sim_launch_topology", "Processes, and the nodes inside them",
            "Each large box is one operating-system process. A component container is a process that hosts several "
            "ROS nodes; each row inside it is one node, with its role. Example: the Pecos QA sandbox.")

    def proc(x, y, w, title, sub, nodes, *, stops=False):
        h = 64 + sum(30 + 16 * len(wrap(r, w - 68, 11, "sans")) + 8 for _, r, _ in nodes) + 8 * (len(nodes) - 1) + 14
        d.rect(x, y, w, h, rx=12, fill=T.bg_deep, stroke=T.border, sw=1.4)
        icon(d, "process", x + 22, y + 22, 22, T.fg2)
        d.text(x + 42, y + 20, title, size=12.5, family="mono", weight=600, fill=T.fg)
        d.text(x + 42, y + 37, sub, size=10.5, fill=T.muted)
        if stops:
            icon(d, "warn", x + w - 20, y + 20, 18, T.red)
        yy = y + 54
        for name, role, col in nodes:
            b = nodebox(d, x + 12, yy, w - 24, name, role, col)
            yy = b.y1 + 8
        return BBox(x, y, x + w, y + h)

    W, G = 370, 24
    a = proc(0, 0, W, "sim/clock", "process · runs on wall time", [
        ("/sim/clock", "publishes simulated time on /clock for every other node", SIM)], stops=True)
    b = proc(0, a.y1 + G, W, "sim/sim_nodes", "component container: one process, 3 nodes", [
        ("/agv/a1/sim", "simulated AGV-1 (agvhito SimAgvComponent)", SIM),
        ("/agv/a2/sim", "simulated AGV-2", SIM),
        ("/sim/sim_world", "the Simulator: patrons, scenario events, collision check", SIM)], stops=True)
    c = proc(W + G, 0, W, "sim/b21_nodes", "component container: one per bay", [
        ("/bay/b21/bay_state_machine", "the bay's insert and retrieve sequences", PROD),
        ("/bay/b21/vehicle_estimator", "estimates the car's size and position", PROD),
        ("/bay/b21/bay_guidance", "driver guidance display", PROD),
        ("/bay/b21/bay_sim", "simulated sensors and doors of B21", SIM)])
    e = proc(W + G, c.y1 + G, W, "standalone processes", "one process each", [
        ("rest_api", "the HTTP API the app uses (port 5000)", PROD),
        ("/vis/visualizer, foxglove_bridge, rviz2", "pictures of the garage (vis:=true)", PROD),
        ("/sim/recorder", "records every topic (record_artifacts:=true)", PROD)])
    f = proc(2 * (W + G), 0, W, "sim/central_sim_nodes", "component container: the central software", [
        ("/central/dispatcher", "jobs, plan calls, commands to AGVs and bays", PROD),
        ("/central/garage_tracker", "the garage state: AGVs, trays, cars", PROD),
        ("/central/consistency_monitor", "stops Dispatch if state and plan disagree", PROD),
        ("/central/agv_monitor, ...", "health checks (3 monitors)", PROD),
        ("/scheduler/scheduler", "the planner; answers /scheduler/plan", SCH)])
    yb = max(b.y1, e.y1, f.y1) + 24
    d.rect(0, yb, 3 * W + 2 * G, 70, rx=10, fill=T.card, stroke=T.border_soft, sw=1)
    d.text(16, yb + 24, "Not started in simulation: agvhito's proxy_node (the link to real AGVs) and the hardware "
                        "drivers of bays and chargers.", size=11.5, fill=T.fg2)
    d.text(16, yb + 46, "A layout with EV chargers or a VRC adds one process per charger (vecs_node + vecs_sim_node) "
                        "and per VRC (/vrc/r<N>/manager).", size=11.5, fill=T.fg2)
    frame(d, title="Processes, and the nodes inside them",
          subtitle="What the process list shows while the QA sandbox runs: three component containers and a few single "
                   "processes. Grouping nodes into one process changes nothing about how they talk; it only saves "
                   "resources. Nodes communicate over topics and services, which this view leaves out.",
          badge_key="as-built",
          legend=[("icon:process", T.fg2, "operating-system process"), ("icon:node", PROD, "ROS node"),
                  ("box", SIM, "simulated stand-in"), ("box", PROD, "production software"),
                  ("box", SCH, "the scheduler"), ("icon:warn", T.red, "if this process exits, the launch stops")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("139_sim_insert_paths", "How a car gets parked in simulation", DOC)
def sim_insert_paths():
    d = Doc("139_sim_insert_paths", "How a car gets parked in simulation",
            "Flow chart: three ways to make a patron arrive, the wait for a ready bay, the simulated drive-on, the "
            "insert confirmation (automatic or by hand), and the production software parking the car.")
    # entry points (left)
    ent = [
        ("file", "A · in the scenario file", ["- {type: patron_arrival, time: 30,", "   payload_id: <GUID>}",
                                              "fires 30 s after the scenario clock starts"]),
        ("terminal", "B · from an events file", ["ros2 run scenario exercise_sim_events \\",
                                                 "  -l <layout> -e <events file>",
                                                 "waits itself until a bay is ready"]),
        ("terminal", "C · by hand, at any moment", ["scripts/trigger_patron_arrival.bash",
                                                    "or ros2 service call /sim/enqueue_garage_event",
                                                    "  (type: patron_arrival)"]),
    ]
    ew, eh = 330, 96
    for i, (ik, t, rows) in enumerate(ent):
        y = i * (eh + 16)
        d.rect(0, y, ew, eh, rx=10, fill=T.card, stroke=T.border, sw=1.3)
        icon(d, ik, 22, y + 22, 22, T.fg2)
        d.text(44, y + 26, t, size=12.5, weight=600, fill=T.fg)
        for k, r in enumerate(rows):
            mono = not r.startswith(("fires", "waits"))
            d.text(16, y + 48 + 17 * k, r, size=10.5, family="mono" if mono else "sans",
                   fill=T.fg2 if mono else T.muted)
    # queue
    qx, qy = 400, 110
    q = nodebox(d, qx, qy, 250, "/sim/sim_world", "puts the patron in the insert queue", SIM, h=70)
    for i in range(3):
        y = i * (eh + 16) + eh / 2
        connect(d, [(ew, y), (ew + 30, y), (ew + 30, q.cy), (qx, q.cy)], kind="flow", color=T.border, sw=1.4,
                size=8)
    # decision diamond
    dx, dy = 790, q.cy
    dw, dh = 110, 62
    d.polygon([(dx, dy - dh), (dx + dw, dy), (dx, dy + dh), (dx - dw, dy)], fill=T.card, stroke=T.border, sw=1.4)
    d.text(dx, dy - 8, "a bay in state", size=11.5, fill=T.fg, anchor="middle")
    d.text(dx, dy + 10, "READY_TO_INSERT?", size=11, family="mono", fill=T.fg, anchor="middle")
    connect(d, [(q.x1, q.cy), (dx - dw, dy)], kind="flow", color=T.border, sw=1.4, size=8)
    # no branch (up)
    nb = BBox(dx - 200, -6, dx + 200, 60)
    d.rect(nb.x0, nb.y0, nb.w, nb.h, rx=8, fill=T.card, stroke=T.border_soft, sw=1.2)
    d.text(nb.x0 + 12, nb.y0 + 20, "no: the patron waits in the queue (checked every 50 ms)", size=11, fill=T.fg2)
    d.text(nb.x0 + 12, nb.y0 + 38, "a bay becomes ready when Dispatch prepares it: automatic mode with", size=10.5,
           fill=T.muted)
    d.text(nb.x0 + 12, nb.y0 + 53, "bay_readiness_ratio > 0 and a free empty tray", size=10.5, fill=T.muted)
    connect(d, [(dx, dy - dh), (dx, nb.y1)], kind="flow", color=T.border, sw=1.4, size=8)
    d.text(dx + 8, (dy - dh + nb.y1) / 2 + 4, "no", size=11, weight=600, fill=T.muted)
    # yes branch: down the right
    steps = [
        ("/bay/b<N>/bay_sim", "takes the patron: plays the car driving onto the tray (load cells, sensors)", SIM),
        ("confirm the insert", "automatic by default; with auto_confirm_insert:=false, by hand: "
                               "POST /api/bay/b<N>/confirm-insert (scripts/confirm_insert.bash)", SIM),
        ("/bay/b<N>/bay_state_machine", "reports the inserted car; Dispatch creates an INSERT job", PROD),
        ("/scheduler/scheduler", "plans the park: which stall, which AGV, which route", SCH),
        ("/agv/a<N>/sim", "carries the tray with the car from the bay to the stall", SIM),
    ]
    sx, sw_ = dx - 160, 330
    yy = dy + dh + 34
    connect(d, [(dx, dy + dh), (dx, yy)], kind="flow", color=T.border, sw=1.4, size=8)
    d.text(dx + 8, dy + dh + 20, "yes", size=11, weight=600, fill=T.muted)
    prev = None
    for name, role, col in steps:
        b = nodebox(d, sx, yy, sw_, name, role, col, mono=not name.startswith("confirm"),
                    kind="node" if not name.startswith("confirm") else "person")
        if prev:
            connect(d, [(b.cx, prev.y1), (b.cx, b.y0)], kind="flow", color=T.border, sw=1.4, size=8)
        prev = b
        yy = b.y1 + 22
    # retrieve note
    ry = 3 * (eh + 16) + 70
    lines = ["retrieve_request (A, B or C, with the car's GUID)",
             "-> Dispatch creates a RETRIEVE job; the scheduler plans it",
             "-> a simulated AGV brings the tray to a bay",
             "-> bay_sim confirms; the car leaves when the patron door opens.",
             "No ready bay is needed: the retrieve job prepares one.",
             "The GUID must be a car in the garage (initial_conditions or",
             "an earlier patron_arrival)."]
    d.rect(0, ry, 560, 50 + 18 * len(lines), rx=10, fill=T.card, stroke=T.border_soft, sw=1.2)
    d.text(16, ry + 24, "A retrieve takes the reverse path", size=12.5, weight=600, fill=T.fg)
    for k, r in enumerate(lines):
        d.text(16, ry + 48 + 18 * k, r, size=11, fill=T.fg2)
    # manual-mode note
    d.text(0, 3 * (eh + 16) + 16, "Manual mode (set_dispatch_mode 2): nothing prepares a bay by itself; ask for one "
                                  "with a transition_bay_to_insert event", size=11, fill=T.muted)
    d.text(0, 3 * (eh + 16) + 33, "(the bay must already hold an empty tray).", size=11, fill=T.muted)
    frame(d, title="How a car gets parked in simulation",
          subtitle="Whichever way the patron is created, it joins the same queue and waits for a bay that is ready "
                   "to insert. From there the simulated bay plays the driver, and the production software parks the "
                   "car exactly as on site.",
          badge_key="as-built",
          legend=[("box", SIM, "simulated stand-in"), ("box", PROD, "production software"),
                  ("box", SCH, "the scheduler"), ("icon:file", FILE, "written in a file"),
                  ("icon:terminal", T.fg2, "typed in a terminal")])
    return d
