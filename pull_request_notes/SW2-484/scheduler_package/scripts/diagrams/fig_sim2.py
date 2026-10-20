"""fig_sim2: sites, setups and the simulation workflow (131-138).

Doc 09-simulation.html. Facts from sources/repomix-launcher.xml (launch/sim.launch.py, launcher/sim_nodes.py,
utils.py, bay_nodes.py, central_nodes.py, vecs_nodes.py, vrc_nodes.py, params/*), sources/repomix-scenario.xml
(scenario/exercise_sim_events.py, scenario/events/*.py, scenarios/*.yaml, batch_configs/*.yaml) and
sources/5675_pecos_combined.yaml. Site locations are inferred from the layout names (street addresses); the
evidence is listed in the document (section "Where the layouts are").
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from components import card, chip, connect, frame, label_pill
from facility import Map, NODES, STALL_L, STALL_W
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
from theme import S, T

DOC = "09-simulation.html"
ROOT = Path(__file__).resolve().parents[2]
SIM, STACK, SCH, MACH, VIS = T.sky, T.violet, T.green, T.amber, T.teal


# --------------------------------------------------------------------------------------------------------------
# scenario files, read from the repomix snapshot (so the figures cannot drift from the files)
# --------------------------------------------------------------------------------------------------------------
def _scenarios() -> dict:
    raw = (ROOT / "sources" / "repomix-scenario.xml").read_text()
    out = {}
    for m in re.finditer(r'<file path="(scenarios|batch_configs)/([^"]+)\.yaml">\n(.*?)\n</file>', raw, re.S):
        out[m.group(2)] = yaml.safe_load(m.group(3))
    return out


SCEN = _scenarios()


def _box(d, x, y, w, title, sub, col, rows=(), h=None, dashed=False, title_size=13, row_size=11, mono_rows=True):
    h = h or (44 + 18 * len(rows) + (8 if rows else 0))
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=col, sw=1.6, dash="6 4" if dashed else None)
    d.text(x + 12, y + 18, title, size=title_size, family="mono", weight=700, fill=col)
    if sub:
        d.text(x + 12, y + 35, sub, size=10.5, fill=T.muted)
    yy = y + 56 if sub else y + 40
    for r in rows:
        d.text(x + 14, yy, r, size=row_size, family="mono" if mono_rows else "sans", fill=T.fg2)
        yy += 18
    return BBox(x, y, x + w, y + h)


# --------------------------------------------------------------------------------------------------------------
@figure("131_sim_layout_to_site", "From a layout to a simulated site", DOC)
def sim_layout_to_site():
    d = Doc("131_sim_layout_to_site", "From a layout to a simulated site",
            "The layout file is the centre of a simulated site: the launcher derives the bay, VECS and VRC "
            "nodes from it, the scenario places AGVs and trays on its node ids, and the installation parameter "
            "file of the same name tunes the site's hardware.")
    FILE = T.fg2
    # centre: the layout file
    lay = _box(d, 400, 0, 360, "layout: <name>.yaml", "the map (Layout file tab)", SIM,
               ["nodes: id, x, y, floor, type, headings", "  Bay / BLift nodes", "  EvCharge nodes",
                "  Parking, Waypoint, AgvCharge, Lift", "edges, parking_windows, buffer", "floors, vrcs"],
               title_size=14, h=186)
    # left: scenario
    scn = _box(d, 0, 0, 300, "scenario: <file>.yaml", "scenario package (or a path)", FILE,
               ["layout: <name>", "initial_conditions:", "  agvs: id, garage_pose", "  trays: id, garage_pose, payload",
                "  obstructions, vrcs", "params: {node: {...}}", "events: [{time, type, ...}]"], h=186)
    # right: installation params
    par = _box(d, 860, 0, 300, "params_<name>.yaml", "launcher/params/installations", FILE,
               ["bay: io_link masters and ports", "bay: estimator sensor box [m]", "bay: floor_spec (BLift sites)",
                "bay: load_cells scale", "scheduler: bay_readiness_ratio", "optional in sim; required on site"],
               h=186)
    connect(d, [(scn.x1, 60), (lay.x0, 60)], kind="assoc", color=FILE, sw=1.6)
    d.text((scn.x1 + lay.x0) / 2, 50, "names it", size=10.5, fill=T.muted, anchor="middle")
    connect(d, [(par.x0, 60), (lay.x1, 60)], kind="dep", color=FILE, sw=1.4)
    d.text((par.x0 + lay.x1) / 2, 50, "same name", size=10.5, fill=T.muted, anchor="middle")
    # derived runtime nodes (bottom row)
    y = 270
    W, gap = 272, 24
    xs = [i * (W + gap) for i in range(4)]
    der = [
        ("per scenario AGV  a<id>", "container sim/sim_nodes", SIM,
         ["/agv/a<id>/sim  (agvhito", "  SimAgvComponent)", "initial_node_id, initial_heading",
          "initial_lifted = lift_fraction == 1"]),
        ("per Bay node  b<id>", "container sim/b<id>_nodes", MACH,
         ["/bay/b<id>/bay_state_machine", "  (BLift: BliftStateMachine", "   + vrc_lift_bridge)",
          "/bay/b<id>/vehicle_estimator", "/bay/b<id>/bay_guidance", "/bay/b<id>/bay_sim   (sim)"]),
        ("per EvCharge node  v<id>", "standalone processes", MACH,
         ["/vecs/v<id>/vecs_node", "/vecs/v<id>/vecs_sim_node (sim)"]),
        ("per vrcs entry  r<id>", "standalone process (sim driver)", MACH,
         ["/vrc/r<id>/manager", "floors and z from the layout,", "speed and doors from params,",
          "initial_floor from the scenario"]),
    ]
    boxes = [_box(d, x, y, W, t, s_, c, rows, h=176, title_size=12.5, row_size=10.5)
             for x, (t, s_, c, rows) in zip(xs, der)]
    connect(d, [(boxes[0].cx, scn.y1), (boxes[0].cx, boxes[0].y0)], kind="assoc", color=SIM, sw=1.5)
    d.text(boxes[0].cx + 8, (scn.y1 + boxes[0].y0) / 2 + 4, "initial_conditions.agvs", size=10.5, family="mono",
           fill=SIM)
    for b in boxes[1:3]:
        connect(d, [(b.cx, lay.y1), (b.cx, b.y0)], kind="assoc", color=MACH, sw=1.5)
    b = boxes[3]
    connect(d, [(lay.x1 - 14, lay.y1), (lay.x1 - 14, lay.y1 + 40), (b.cx, lay.y1 + 40), (b.cx, b.y0)],
            kind="assoc", color=MACH, sw=1.5)
    d.text(boxes[1].cx + 8, (lay.y1 + y) / 2 + 4, "one set per node of that type", size=10.5, fill=MACH)
    # once per run
    y2 = y + 176 + 30
    once = _box(d, 0, y2, 4 * W + 3 * gap, "once per run, whatever the layout", None, STACK,
                ["sim/clock (/clock)   ·   sim/sim_world (Simulator: scenario path)   ·   central container: "
                 "dispatcher, garage_tracker, monitors, scheduler",
                 "rest_api   ·   vis/visualizer, foxglove_bridge, rviz2 (vis:=, rviz:=)   ·   recorder "
                 "(record_artifacts:=true)",
                 "every node: the merged parameter dict, with layout = <name>, installation_id = 9998, "
                 "use_sim_time = true"], h=104, row_size=11)
    frame(d, title="From a layout to a simulated site",
          subtitle="A simulation runs one layout. The launcher starts one set of bay nodes per Bay or BLift node, "
                   "one VECS per EvCharge node and one VRC driver per vrcs entry; the scenario puts AGVs and "
                   "trays on the layout's node ids; params_<layout>.yaml, if it exists, carries the site's hardware "
                   "settings.",
          badge_key="as-built",
          legend=[("box", SIM, "layout, simulated AGVs"), ("box", FILE, "input files"),
                  ("box", MACH, "machines derived from the layout"), ("box", STACK, "fixed part of the stack"),
                  ("arrow", T.fg2, "derives or names"), ("dasharrow", T.fg2, "found by name")])
    return d


# --------------------------------------------------------------------------------------------------------------
SITES = {
    "Bay Area, California": [
        ("1355 Fulton St, San Francisco", ["1355_fulton"], "operating customer garage", "public"),
        ("576 Eccles Ave, South San Francisco", ["576_eccles", "_half", "_mini", "_no_bay", "_under_vcr",
                                                 "_budget_sandbox", "_budget_sandbox_mini"],
         "former test site (7 variants)", "inferred"),
        ("415 East Grand Ave, South San Francisco", ["415_east_grand_ave"], "earlier site; default bay box",
         "inferred"),
    ],
    "Denver, Colorado": [
        ("5675 N Pecos St, Denver", ["5675_pecos_bench", "5675_pecos_sandbox_eng", "5675_pecos_sandbox_qa",
                                     "5675_pecos_sandbox_combined"], "headquarters test facility", "public"),
        ("vrc_sandbox (no street in the name)", ["vrc_sandbox"], "VRC test bed", "guess"),
    ],
    "New York": [
        ("38 Gramercy Park East, Manhattan", ["38_gramercy"], "condominium; BLift + VRC", "public"),
        ("550 W 21st St, Manhattan", ["550_w21st"], "condominium; batch tests", "public"),
        ("360 W Broadway: Manhattan (SoHo)?", ["360_w_broadway"], "BLift floor spec", "guess"),
    ],
}
UNPLACED = [("275_sunrise_b", "7 scenario files, no params file"), ("tiny_lot", "synthetic test layout"),
            ("multisize", "synthetic: parking-window sizes")]
EVID = {"public": (T.green, "named in a public source"), "inferred": (T.amber, "street + city inferred"),
        "guess": (T.muted, "guess")}


@figure("132_sim_sites", "Where the layouts are", DOC)
def sim_sites():
    d = Doc("132_sim_sites", "Where the layouts are",
            "Every layout in the launcher's installation parameters and in the scenarios, grouped by the place "
            "its name points to, west to east, with how sure the location is.")
    W, gap = 340, 30
    x = 0
    col_bottom = 0
    for region, sites in SITES.items():
        d.text(x, 0, region, size=15, weight=600, fill=T.fg)
        d.line(x, 12, x + W, 12, stroke=T.border_soft, sw=1)
        y = 30
        for addr, layouts, kind, ev in sites:
            col, evtxt = EVID[ev]
            lines = []
            line = ""
            for i, l in enumerate(layouts):
                piece = (l if i == 0 or not l.startswith("_") else l) + ("  " if i < len(layouts) - 1 else "")
                if text_width(line + piece, 11, "mono") > W - 30:
                    lines.append(line.rstrip())
                    line = ""
                line += piece
            lines.append(line.rstrip())
            h = 64 + 17 * len(lines)
            d.rect(x, y, W, h, rx=10, fill=T.card, stroke=col, sw=1.6 if ev != "guess" else 1.2,
                   dash=None if ev != "guess" else "6 4")
            d.circle(x + 16, y + 19, 5, fill=col)
            d.text(x + 28, y + 19, addr, size=13, weight=600, fill=T.fg)
            d.text(x + 28, y + 38, kind, size=11, fill=T.muted)
            for i, ln in enumerate(lines):
                d.text(x + 28, y + 58 + 17 * i, ln, size=11, family="mono", fill=T.fg2)
            y += h + 14
        col_bottom = max(col_bottom, y)
        x += W + gap
    # unplaced row
    y = col_bottom + 18
    d.text(0, y, "Not placed", size=15, weight=600, fill=T.fg)
    d.line(0, y + 12, 3 * W + 2 * gap, y + 12, stroke=T.border_soft, sw=1)
    xx = 0
    for name, note in UNPLACED:
        w = 3 * W / 3 + (2 * gap) / 3 - 0
        d.rect(xx, y + 28, w - 10, 50, rx=10, fill=T.card, stroke=T.border, sw=1.2)
        d.text(xx + 16, y + 48, name, size=12, family="mono", weight=600, fill=T.fg2)
        d.text(xx + 16, y + 66, note, size=11, fill=T.muted)
        xx += w + 10 - 10 + 0
    frame(d, title="Where the layouts are",
          subtitle="Layout names start with a street address. Four are confirmed by public sources (Volley's "
                   "Denver headquarters, its two Manhattan projects and the operating San Francisco garage); "
                   "the others are inferred from the street name and the company's history, and may be wrong.",
          badge_key="inferred",
          legend=[("dot", T.green, EVID["public"][1]), ("dot", T.amber, EVID["inferred"][1]),
                  ("dot", T.muted, EVID["guess"][1])],
          footnote="Layout names from launcher/params/installations and the scenario files; a leading _ abbreviates "
                   "the first name in the card. Sources are listed in the document.")
    return d


# --------------------------------------------------------------------------------------------------------------
ENG_Y, QA_Y, ALL_Y = (6.7, 14.6), (15.2, 25.3), (6.7, 25.3)
X_RANGE = (20.0, 46.4)


def _occupancy(m: Map, scen: dict, *, agv_side=None):
    ic = scen["initial_conditions"]
    agv_at = {a["garage_pose"]["node_id"] for a in ic.get("agvs", [])}
    for t in ic.get("trays", []):
        nid = t["garage_pose"]["node_id"]
        m.tray(nid, f"T{t['id']}", payload="payload" in t, chip_pos="tr" if nid in agv_at else "bl")
    for a in ic.get("agvs", []):
        nid = a["garage_pose"]["node_id"]
        side = (agv_side or {}).get(a["id"], "below")
        m.agv(nid, f"AGV-{a['id']}", heading=a["garage_pose"]["heading"], label_side=side)


@figure("133_sim_pecos_setups", "The Pecos test facility as three layouts", DOC)
def sim_pecos_setups():
    d = Doc("133_sim_pecos_setups", "The Pecos test facility as three layouts",
            "Plan view of the Pecos layout. The sandbox_eng and sandbox_qa sections are separate layouts; "
            "sandbox_combined is both. Each panel shows the occupancy of that layout's full_start_in_auto "
            "scenario file.")
    s = 21
    W = (X_RANGE[1] - X_RANGE[0]) * s
    panels = [
        ("5675_pecos_sandbox_eng", "5675_pecos_sandbox_eng_full_start_in_auto", 0, 40, ENG_Y,
         "bay B7, stalls P2 P3 P5 P6, charger C10"),
        ("5675_pecos_sandbox_qa", "5675_pecos_sandbox_qa_full_start_in_auto", 0, None, QA_Y,
         "bay B21, stalls P15-P24, chargers C14 C16"),
        ("5675_pecos_sandbox_combined", "5675_pecos_sandbox_combined_full_start_in_auto", W + 70, 40, ALL_Y,
         "both sections, joined by edge W8-W13"),
    ]
    y_left = 40
    for lay, scen, x, y, yr, note in panels:
        if y is None:
            y = y_left
        m = Map(d, x, y, s, X_RANGE, yr)
        m.base(labels=True, zones=(lay.endswith("combined")), axes=False)
        _occupancy(m, SCEN[scen])
        d.text(x, y - 26, f"layout {lay}", size=13, family="mono", weight=700, fill=T.fg)
        d.text(x, y - 9, note, size=11, fill=T.muted)
        h = (yr[1] - yr[0]) * s
        if x == 0:
            y_left = y + h + 86
        ic = SCEN[scen]["initial_conditions"]
        d.text(x, y + h + 18, f"{scen}.yaml: {len(ic['agvs'])} AGV, {len(ic['trays'])} trays with vehicles",
               size=11, family="mono", fill=T.fg2)
    # what the other start files change
    xr = W + 70
    yb = 40 + (ALL_Y[1] - ALL_Y[0]) * s + 44
    rows = [("empty_*", "the same trays without payloads (and, for combined, AGVs at W9 and P17)"),
            ("*_no_op", "same occupancy, events: [] - Dispatch is never started"),
            ("single_agv_start_in_manual", "AGV-1 alone at W13, no trays, Dispatch in manual mode (qa, combined)")]
    for i, (k, v) in enumerate(rows):
        d.text(xr, yb + i * 20, k, size=11, family="mono", weight=600, fill=SIM)
        d.text(xr + 196, yb + i * 20, v, size=11, fill=T.fg2)
    frame(d, title="The Pecos test facility as three layouts",
          subtitle="The Denver test floor is described once (5675_pecos_combined.yaml, two YAML sections) and "
                   "simulated as three layouts: each sandbox alone, or both together. Node ids are shared, so a "
                   "scenario for one sandbox uses the same P, W and B numbers as the combined layout.",
          badge_key="yaml+scenario",
          legend=[("box", T.sky, "stall (Parking)"), ("box", T.teal, "customer bay"), ("box", T.amber, "tray"),
                  ("box", T.pink, "vehicle on a tray"), ("box", T.green, "AGV (heading 90 = facing -x)")],
          footnote="An AGV and a tray on the same stall: the AGV is lowered under the tray (initial_lifted is "
                   "false unless lift_fraction is 1).")
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("134_sim_site_archetypes", "Two kinds of site: a bay at grade, and a bay on a VRC", DOC)
def sim_site_archetypes():
    d = Doc("134_sim_site_archetypes", "Two kinds of site",
            "Side elevations, schematic. Left: a single-floor garage whose customer bay is a node of the "
            "parking floor (Pecos). Right: a BLift site, where the bay carriage is also a VRC that takes the "
            "tray between the street-level motor court and the parking floor (38 Gramercy).")
    G = 260

    def floor_slab(x0, x1, y, label):
        d.rect(x0, y, x1 - x0, 10, fill=T.muted_bg, stroke=T.border, sw=1)
        d.text(x1 + 8, y + 9, label, size=11, family="mono", fill=T.muted)

    def car(x, y, w=86, h=26, col=T.pink):
        d.rect(x, y - h, w, h, rx=10, fill=T.tint(col, 0.25, T.bg), stroke=col, sw=1.4)
        d.circle(x + 18, y, 7, fill=T.bg, stroke=col, sw=1.4)
        d.circle(x + w - 18, y, 7, fill=T.bg, stroke=col, sw=1.4)

    def tray(x, y, w=110):
        d.rect(x, y - 7, w, 7, rx=2, fill=T.tint(T.amber, 0.35, T.bg), stroke=T.amber, sw=1.3)

    def agv(x, y, w=74):
        d.rect(x, y - 14, w, 14, rx=4, fill=T.tint(T.green, 0.3, T.bg), stroke=T.green, sw=1.4)

    # ---- A: bay at grade
    d.text(0, 0, "A · bay at grade (Pecos; one floor in the layout)", size=13.5, weight=600, fill=T.fg)
    floor_slab(0, 520, G, "floor 0")
    # bay
    d.rect(10, G - 120, 170, 120, fill=T.tint(T.teal, 0.08, T.bg), stroke=T.teal, sw=1.4, dash="6 4")
    d.text(18, G - 104, "bay B21", size=12, family="mono", weight=700, fill=T.teal)
    d.text(18, G - 88, "patron and garage doors", size=10.5, fill=T.muted)
    tray(25, G - 2)
    car(37, G - 9)
    # parking
    for i, xx in enumerate((250, 390)):
        tray(xx, G - 18)
        agv(xx + 18, G - 2) if i == 0 else None
        car(xx + 12, G - 25)
    d.text(250, G - 82, "stalls P19, P23: trays on stands; an AGV drives", size=10.5, fill=T.muted)
    d.text(250, G - 68, "under a tray, lifts it and carries it", size=10.5, fill=T.muted)
    d.line(182, G - 30, 240, G - 30, stroke=T.green, sw=1.6, dash="5 4")
    d.arrowhead((240, G - 30), (182, G - 30), kind="filled", color=T.green, size=9)
    rowsA = ["launcher: bay::StateMachineComponent per Bay node",
             "the patron drives on and off at the bay's own level", "no floors, no vrcs entries"]
    for i, r in enumerate(rowsA):
        d.text(0, G + 40 + i * 19, r, size=11.5, family="mono" if i == 0 else "sans", fill=T.fg2)
    # ---- B: BLift
    X = 640
    d.text(X, 0, "B · BLift: the bay is a VRC stop (38 Gramercy, 360 W Broadway)", size=13.5, weight=600,
           fill=T.fg)
    top, bot = G - 150, G
    floor_slab(X + 120, X + 520, top, "floor 1: motor court")
    floor_slab(X + 120, X + 520, bot, "floor 0: parking")
    # shaft
    d.rect(X, top - 70, 110, bot - top + 80, fill=T.tint(T.violet, 0.06, T.bg), stroke=T.violet, sw=1.4,
           dash="6 4")
    d.text(X + 8, top - 54, "VRC r1 shaft", size=11, family="mono", weight=600, fill=T.violet)
    # carriage at floor 1 (bay) with car, ghost at floor 0
    d.rect(X + 6, top - 4, 98, 6, fill=T.violet)
    tray(X + 6, top - 4, 98)
    car(X + 12, top - 11, w=80)
    d.text(X + 124, top - 44, "BLift node 26: the bay is the VRC carriage", size=11, family="mono", weight=700, fill=T.teal)
    d.text(X + 124, top - 28, "the patron drives onto the tray at floor 1", size=10.5, fill=T.muted)
    d.rect(X + 6, bot - 4, 98, 6, fill=T.tint(T.violet, 0.45, T.bg))
    d.line(X + 55, top + 10, X + 55, bot - 14, stroke=T.violet, sw=1.8, dash="5 4")
    d.arrowhead((X + 55, bot - 14), (X + 55, top + 10), kind="filled", color=T.violet, size=10)
    d.text(X + 122, (top + bot) / 2 + 4, "the carriage lowers the tray", size=10.5, fill=T.violet)
    # parking on floor 0
    for xx in (X + 210, X + 360):
        tray(xx, bot - 18)
        car(xx + 12, bot - 25)
    agv(X + 140, bot - 2)
    d.line(X + 118, bot - 30, X + 200, bot - 30, stroke=T.green, sw=1.6, dash="5 4")
    d.arrowhead((X + 200, bot - 30), (X + 118, bot - 30), kind="filled", color=T.green, size=9)
    rowsB = ["launcher: bay::BliftStateMachineComponent",
             "  + bay::VrcLiftBridgeComponent (/vrc/r<id>/report -> /lift/l<bay>/report)",
             "  + /vrc/r<id>/manager (vrc sim driver: floors, z, speed, doors)",
             "params: bay.floor_spec = 38_gramercy_blift"]
    for i, r in enumerate(rowsB):
        d.text(X, G + 40 + i * 19, r, size=11.5, family="mono", fill=T.fg2)
    frame(d, title="Two kinds of site: a bay at grade, and a bay on a VRC",
          subtitle="The launcher chooses the bay state machine from the node type. A Bay node gets the standard "
                   "machine; a BLift node gets the BLift machine, a bridge to its VRC, and the VRC's simulated "
                   "driver. The planner's VRC support is described in the Layout file tab.",
          badge_key="schematic",
          legend=[("box", T.teal, "bay"), ("box", T.violet, "VRC"), ("box", T.amber, "tray"),
                  ("box", T.pink, "vehicle"), ("box", T.green, "AGV")],
          footnote="38 Gramercy: per the comment in params_38_gramercy.yaml, the BLift is node 26 and VRC 1 takes "
                   "the vehicle from floor 1 to floor 0. The layouts of the New York sites are not in the "
                   "snapshots, so the floor plan is not drawn.")
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("135_sim_launch_topology", "What sim.launch.py starts", DOC)
def sim_launch_topology():
    d = Doc("135_sim_launch_topology", "What sim.launch.py starts",
            "Deployment view of one simulation: processes and component containers, their namespaces and "
            "nodes, which part is simulated, and which exits stop the whole launch.")
    PROC = T.border

    def container(x, y, w, title, sub, nodes, *, h=None, accent=T.fg2, dashed=False, exit_stops=False):
        h = h or (52 + 20 * len(nodes) + 10)
        d.rect(x, y, w, h, rx=12, fill=T.bg_deep, stroke=accent, sw=1.4, dash="6 4" if dashed else None)
        d.text(x + 14, y + 20, title, size=12.5, family="mono", weight=700, fill=T.fg)
        d.text(x + 14, y + 37, sub, size=10.5, fill=T.muted)
        if exit_stops:
            chip(d, x + w - 10, y + 10, "exit = shutdown", T.red, anchor="end", size=10,
                 fill=T.tint(T.red, 0.18, T.bg_deep), layer="labels")
        yy = y + 52
        for name, col in nodes:
            d.rect(x + 12, yy, w - 24, 17, rx=4, fill=T.tint(col, 0.12, T.bg_deep), stroke=T.tint(col, 0.55,
                                                                                                  T.bg_deep), sw=1)
            d.text(x + 20, yy + 9, name, size=10.5, family="mono", fill=col)
            yy += 20
        return BBox(x, y, x + w, y + h)

    W = 330
    c1 = container(0, 0, W, "sim/clock", "process · wall time · publishes /clock",
                   [("sim_clock_node (SimClockRos)", SIM)], exit_stops=True)
    c2 = container(0, c1.y1 + 20, W, "sim/sim_nodes", "container · multi-threaded executor",
                   [("/agv/a1/sim  SimAgvComponent (agvhito)", SIM), ("/agv/a2/sim  ...one per scenario AGV", SIM),
                    ("/sim/sim_world  SimulatorComponent", SIM)], exit_stops=True)
    c3 = container(W + 30, 0, W, "sim/b<id>_nodes  (one per bay)", "container · multi-threaded executor",
                   [("/bay/b<id>/bay_state_machine", MACH), ("/bay/b<id>/vehicle_estimator", MACH),
                    ("/bay/b<id>/bay_guidance", MACH), ("/bay/b<id>/vrc_lift_bridge  (BLift)", MACH),
                    ("/bay/b<id>/bay_sim  BaySimComponent", SIM)])
    c4 = container(2 * W + 60, 0, W, "sim/central_sim_nodes", "container · multi-threaded executor",
                   [("/central/dispatcher", STACK), ("/central/garage_tracker", STACK),
                    ("/central/consistency_monitor", STACK), ("/central/agv_monitor", STACK),
                    ("/central/safety_hardware_monitor", STACK), ("/central/garage_monitor", STACK),
                    ("/scheduler/scheduler  SchedulerComponent", SCH)])
    c5 = container(W + 30, c3.y1 + 20, W, "per EvCharge node  /  per VRC", "standalone processes",
                   [("/vecs/v<id>/vecs_node", MACH), ("/vecs/v<id>/vecs_sim_node", SIM),
                    ("/vrc/r<id>/manager  (vrc sim driver)", SIM)])
    c6 = container(2 * W + 60, c4.y1 + 20, W, "standalone and optional", "processes",
                   [("rest_api (central_api)", STACK), ("/vis/visualizer  vis:=true (default)", VIS),
                    ("foxglove_bridge  with vis", VIS), ("rviz2  rviz:=true (default)", VIS),
                    ("/sim/recorder  record_artifacts:=true", T.fg2)], dashed=False)
    # parameters panel
    y = max(c2.y1, c5.y1, c6.y1) + 30
    d.rect(0, y, 3 * W + 60, 64, rx=10, fill=T.card, stroke=T.border_soft, sw=1)
    d.text(14, y + 22, "Every node gets the same merged parameter dict; the launcher adds is_simulation = true, "
                       "installation_id = 9998, use_sim_time = true (false only for sim/clock).",
           size=11.5, fill=T.fg2)
    d.text(14, y + 44, "Not started in simulation: the agvhito proxy_node that talks to the real AGVs, and the bay "
                       "and VECS hardware drivers.", size=11.5, fill=T.fg2)
    frame(d, title="What sim.launch.py starts",
          subtitle="Three component containers and a handful of processes, all in ROS domain 75 unless "
                   "ROS_DOMAIN_ID is set. The scheduler runs inside the central container, as on site. If the "
                   "clock process or the sim_nodes container exits unexpectedly, the launch shuts down.",
          badge_key="as-built",
          legend=[("box", SIM, "simulated (sim, agvhito, vecs, vrc sim parts)"), ("box", STACK, "central (real)"),
                  ("box", SCH, "scheduler (real)"), ("box", MACH, "bay and VECS nodes (real)"),
                  ("box", VIS, "visualisation")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("136_sim_two_runners", "Two ways to feed events: timed and sequential", DOC)
def sim_two_runners():
    d = Doc("136_sim_two_runners", "Two ways to feed events",
            "Timeline comparison: the Simulator fires a scenario file's events at their times; exercise_sim_events "
            "sends an events file one event at a time, each after the previous one is handled.")
    X0, PX = 210, 16.0       # x of t = 0, px per second (lane A)
    # lane A
    yA = 30
    d.text(0, yA, "A · scenario file", size=13.5, weight=600, fill=SIM)
    d.text(0, yA + 18, "events: in the scenario", size=11, fill=T.muted)
    d.text(0, yA + 34, "run by sim/sim_world (C++)", size=11, fill=T.muted)
    axis_y = yA + 80
    d.line(X0, axis_y, X0 + 52 * PX, axis_y, stroke=T.border, sw=1.4)
    for t in range(0, 51, 5):
        d.line(X0 + t * PX, axis_y, X0 + t * PX, axis_y + 6, stroke=T.border, sw=1)
        d.text(X0 + t * PX, axis_y + 19, f"{t}", size=10.5, family="mono", fill=T.muted, anchor="middle")
    d.text(X0 + 52 * PX + 8, axis_y + 4, "scenario time [s]", size=10.5, fill=T.muted)
    evA = [(0.5, "set_dispatch_mode 1 (auto)"), (0.5, "set_bay_readiness_ratio 1.0"), (1.0, "start_dispatch"),
           (5.0, "set_auto_planner on"), (40.0, "retrieve_request  (an example)")]
    rows = {0: 3, 1: 2, 2: 1, 3: 0, 4: 0}
    for i, (t, name) in enumerate(evA):
        x = X0 + t * PX
        yy = axis_y - 16 - rows[i] * 17
        d.line(x, axis_y - 5, x, yy + 5, stroke=T.tint(SIM, 0.6, T.bg), sw=1)
        d.text(x + 5, yy, f"{t:g} s  {name}", size=10.5, family="mono", fill=T.fg2)
    for t in sorted({t for t, _ in evA}):
        d.circle(X0 + t * PX, axis_y, 5, fill=SIM)
    d.text(0, yA + 50, "(<site>_empty_start_in_auto)", size=10.5, family="mono", fill=T.muted)
    d.text(X0, axis_y + 44, "Fires every event whose time has passed, on the 50 ms update; does not wait for "
                            "anything; clock starts when Dispatch is STOPPED and consistent.", size=11.5, fill=T.fg2)
    # lane B
    yB = axis_y + 100
    d.text(0, yB, "B · events file", size=13.5, weight=600, fill=SCH)
    d.text(0, yB + 18, "no layout, no initial state", size=11, fill=T.muted)
    d.text(0, yB + 34, "run by exercise_sim_events", size=11, fill=T.muted)
    d.text(0, yB + 50, "(Python, own process)", size=11, fill=T.muted)
    by = yB + 6
    blocks = [("wait", "wait\nfor Dispatch RUNNING", 160, T.border),
              ("1", "retrieve_request\nwait_for_job_completion", 210, SCH),
              ("2", "retrieve_request\nwait_for_job_completion", 210, SCH),
              ("3", "patron_arrival\nwaits for a READY bay", 200, SCH),
              ("end", "jobs done -> CSV,\nSIGINT the stack", 150, T.border)]
    x = X0
    for k, text, w, col in blocks:
        h = 54
        d.rect(x, by, w - 10, h, rx=8, fill=T.tint(col, 0.12, T.bg), stroke=col, sw=1.4)
        lines = text.split("\n")
        d.text(x + 10, by + 20, lines[0], size=11, family="mono", weight=600, fill=col if col != T.border else T.fg2)
        if len(lines) > 1:
            d.text(x + 10, by + 38, lines[1], size=10.5, fill=T.muted)
        if k not in ("wait", "end"):
            chip(d, x + w - 14, by - 4, f"event {k}", col, anchor="end", size=10, fill=T.tint(col, 0.2, T.bg),
                 layer="labels")
        x += w
    d.text(X0, by + 80, "Starts the next event only when the previous one is handled: the service answered and, "
                        "with wait_for_job_completion, its job is SUCCESS or ERROR.", size=11.5, fill=T.fg2)
    d.text(X0, by + 98, "Each event goes to /sim/enqueue_garage_event with time 0, so sim_world fires it on its "
                        "next update.", size=11.5, fill=T.fg2)
    frame(d, title="Two ways to feed events: timed and sequential",
          subtitle="A scenario file's events are fired by the Simulator at fixed times. An events file is fed one "
                   "event at a time by exercise_sim_events, which waits for each job and writes per-event metrics. "
                   "Batch configurations pair one scenario with one or more events files.",
          badge_key="as-built",
          legend=[("dot", SIM, "timed event (scenario file)"), ("box", SCH, "sequential event (events file)")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("137_sim_scenario_families", "The per-site scenario family", DOC)
def sim_scenario_families():
    d = Doc("137_sim_scenario_families", "The per-site scenario family",
            "The start files and events files every site gets, and how they pair: an empty garage is filled, a "
            "full garage is drained, a single manual AGV visits every node.")
    # start files (left), events files (right), resulting state
    def start(x, y, name, rows, col=SIM):
        return _box(d, x, y, 300, name, None, col, rows, h=40 + 18 * len(rows))

    def events(x, y, name, rows, col=SCH, dashed=False):
        return _box(d, x, y, 300, name, None, col, rows, h=40 + 18 * len(rows), dashed=dashed)

    s1 = start(0, 0, "<site>_empty_start_in_auto", ["trays without vehicles", "mode 1 (auto) at 0.5 s",
                                                   "bay_readiness_ratio 1.0", "auto planner on at 5 s"])
    e1 = events(400, 0, "<site>_events_fill_from_empty", ["patron_arrival x stalls", "wait_for_job_completion"])
    s2 = start(0, 150, "<site>_full_start_in_auto", ["trays with vehicles", "mode 1 (auto) at 0.5 s",
                                                    "bay_readiness_ratio 0.0", "auto planner on at 5 s"])
    e2 = events(400, 150, "<site>_events_drain_from_full", ["retrieve_request x vehicles",
                                                           "wait_for_job_completion"])
    s3 = start(0, 300, "<site>_single_agv_start_in_manual", ["AGV-1 only, no trays", "mode 2 (manual) at 0.5 s",
                                                            "no auto planner"])
    e3 = events(400, 300, "<site>_events_move_each_node", ["wait_for_any_non_busy_agv,", "move_agv to each node,",
                                                          "done_events_wait_jobs_end_..."], col=T.red, dashed=True)
    s4 = start(0, 432, "<site>_empty_no_op  /  _full_no_op", ["events: []", "Dispatch stays STOPPED"], col=T.fg2)
    for a, b, lab in ((s1, e1, "+"), (s2, e2, "+"), (s3, e3, "+")):
        connect(d, [(a.x1, a.cy), (b.x0, a.cy)], kind="line", color=T.border, sw=1.4)
        d.circle((a.x1 + b.x0) / 2, a.cy, 11, fill=T.bg, stroke=T.border, sw=1.2)
        d.text((a.x1 + b.x0) / 2, a.cy + 1, lab, size=14, weight=600, fill=T.fg2, anchor="middle")
    # results
    rx = 780
    r1 = _box(d, rx, e1.y0, 260, "garage full", "every stall holds a vehicle", T.fg2, h=60)
    r2 = _box(d, rx, e2.y0, 260, "garage empty", "every vehicle retrieved", T.fg2, h=60)
    r3 = _box(d, rx, e3.y0, 260, "not runnable today", "exerciser: Unknown event type", T.red, h=60)
    r4 = _box(d, rx, s4.y0, 260, "for inspection", "RViz / Foxglove; drive by hand", T.fg2, h=60)
    for a, b in ((e1, r1), (e2, r2)):
        connect(d, [(a.x1, a.y0 + 30), (b.x0, a.y0 + 30)], kind="assoc", color=SCH, sw=1.5)
    connect(d, [(e3.x1, e3.y0 + 30), (r3.x0, e3.y0 + 30)], kind="assoc", color=T.red, sw=1.4, dash="5 4")
    connect(d, [(s4.x1, s4.y0 + 30), (r4.x0, s4.y0 + 30)], kind="assoc", color=T.fg2, sw=1.4)
    # fill <-> drain loop
    connect(d, [(r1.cx, r1.y1), (r1.cx, r2.y0)], kind="assoc", color=T.muted, sw=1.2, dash="4 4",
            label="same vehicles: drain undoes fill", label_at=(r1.cx, (r1.y1 + r2.y0) / 2))
    # batch note
    yb = r4.y1 + 30
    d.rect(0, yb, 1040, 58, rx=10, fill=T.card, stroke=T.red, sw=1.2, dash="6 4")
    d.text(14, yb + 22, "batch_configs/standardized_tests/pecos_sandbox_qa.yaml: scenario <site>_empty_start_in_auto, "
                        "events 3 x <site>_events_fill_and_drain", size=11.5, family="mono", fill=T.fg2)
    d.text(14, yb + 42, "No *_events_fill_and_drain file is among the scenario files: the standardized test refers "
                        "to a file that is not there.", size=11.5, fill=T.red)
    frame(d, title="The per-site scenario family",
          subtitle="Each site gets the same set of files. Start files carry the layout, the initial state and "
                   "timed set-up events; events files carry the workload and are fed by exercise_sim_events. "
                   "Pecos sandbox_eng, sandbox_qa and sandbox_combined (and 275_sunrise_b) follow this pattern.",
          badge_key="as-built",
          legend=[("box", SIM, "start file (scenario: layout + initial state)"), ("box", SCH, "events file"),
                  ("dashbox", T.red, "broken or missing")])
    return d


# --------------------------------------------------------------------------------------------------------------
@figure("138_sim_workflow", "Running a simulation, end to end", DOC)
def sim_workflow():
    d = Doc("138_sim_workflow", "Running a simulation, end to end",
            "Seven steps from choosing a layout to comparing results, with the command or file for each.")
    PREP, RUN, EVAL = T.sky, T.violet, T.green
    steps = [
        ("Choose the layout", "Layout file tab", PREP,
         ["ros2 run launcher layout_plotter \\", "  <layout> -o map.png --show", "node ids for poses and events"]),
        ("Write or pick a scenario", "scenario/scenarios/*.yaml", PREP,
         ["layout, initial_conditions,", "set-up events, params overrides"]),
        ("Launch", "launcher/launch/sim.launch.py", RUN,
         ["ros2 launch launcher sim.launch.py \\", "  scenario:=<name|path>", "  real_time_factor:=4 vis:=false"]),
        ("Drive it", "second terminal", RUN,
         ["ros2 run scenario exercise_sim_events \\", "  -l <layout> -e <events file>",
          "or: ros2 service call /sim/enqueue_garage_event"]),
        ("Watch", "while it runs", RUN,
         ["RViz, Foxglove (vis:=true)", "ros2 topic echo /sim/report", "ros2 param set /sim/clock real_time_factor 0"]),
        ("Collect", "artifacts", EVAL,
         ["record_artifacts:=true -> mcap of all", "  topics in ~/.ros/artifacts/<UTC>/sim",
          "exerciser CSV: /tmp/sim_results/", "  events_summary.csv"]),
        ("Compare", "Checking the refactor, below", EVAL,
         ["replay recorded plan calls", "KPIs against baseline runs", "bagplay.launch.py bagfile:=<dir>"]),
    ]
    W, H, gx = 330, 138, 26
    for i, (t, sub, col, rows) in enumerate(steps):
        r, c = divmod(i, 3) if i < 6 else (2, 1)
        if i == 6:
            r, c = 2, 0
        x, y = c * (W + gx), r * (H + 46)
        d.rect(x, y, W, H, rx=10, fill=T.card, stroke=col, sw=1.5)
        d.circle(x + 20, y + 20, 12, fill=col)
        d.text(x + 20, y + 21, str(i + 1), size=12, family="mono", weight=700, fill=T.bg, anchor="middle")
        d.text(x + 40, y + 21, t, size=13.5, weight=600, fill=T.fg)
        d.text(x + 40, y + 39, sub, size=10.5, fill=T.muted)
        for k, row in enumerate(rows):
            d.text(x + 16, y + 64 + 18 * k, row, size=10.5, family="mono", fill=T.fg2)
        # arrow to next
        if i < 6:
            nr, nc = divmod(i + 1, 3) if i + 1 < 6 else (2, 0)
            nx, ny = nc * (W + gx), nr * (H + 46)
            if nr == r:
                connect(d, [(x + W, y + H / 2), (nx, ny + H / 2)], kind="flow", color=T.border, sw=1.5, size=8)
            else:
                connect(d, [(x + W / 2, y + H), (x + W / 2, y + H + 22), (nx + W / 2, y + H + 22), (nx + W / 2, ny)],
                        kind="flow", color=T.border, sw=1.5, size=8)
    # side note in the free cell
    x, y = 1 * (W + gx) + 20, 2 * (H + 46)
    notes = ["A batch config (batch_configs/*.yaml) names a layout,",
             "one start scenario and a list of events files:",
             "steps 3 and 4 repeated, results grouped by batch_name.",
             "The runner that reads it is not in the snapshots."]
    for k, n in enumerate(notes):
        d.text(x + 340 - 340 + 0, y + 20 + 18 * k, n, size=11, fill=T.muted)
    frame(d, title="Running a simulation, end to end",
          subtitle="The launch file starts the stack on a scenario; a second process feeds the workload; artifacts "
                   "and metrics come out of both. The same steps serve manual exploration and the refactor checks.",
          badge_key="as-built",
          legend=[("box", PREP, "prepare"), ("box", RUN, "run"), ("box", EVAL, "evaluate")])
    return d
