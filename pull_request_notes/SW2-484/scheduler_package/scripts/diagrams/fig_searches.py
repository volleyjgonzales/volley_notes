"""fig_searches: the single-agent searches and static filters of motion_planner (140-144).

Doc 04-motion-planning.html, section "The single-agent searches and static filters".

140  who calls which search: scheduler methods -> search functions -> environments -> SingleSourceSearch,
     with GetStaticFilter feeding every search (static).
141  SingleSourceSearch (path_search.hpp) on a small abstract graph: open set, closed set, predecessors and
     the environment callbacks, step by step, beside the abridged A* loop (animated).
142  GetStaticFilter (static_graph_filtering.cpp) for a TRAY footprint on the Pecos QA section: parked trays,
     AGVs, a bay that is not READY_TO_RETRIEVE, a disabled node; the keep-out areas are plain rectangles with
     no buffer, the real sets come from CollisionTable::Query (animated).
143  BlockingTraySearchEnvironment and OpenSpaceSearchEnvironment (blocking_tray_search.cpp): one expansion
     from tray T17 at P17, costs = edge length at an illustrative 1 m/s plus 30 s per tray newly crossed;
     the goal test decides where each environment stops (animated).
144  HideAgvs (agv_hiding_search.cpp): one search per AGV at 1 s per edge, destinations in expansion order,
     greedy with backtracking (animated).

Geometry is the Pecos YAML; occupancy is hypothetical. The searches are recomputed here with the same
rules (zero heuristic, closed set, first-found blocking set kept), so the orders shown follow from the code.
"""
from __future__ import annotations

import heapq
import math

from components import code_panel, frame, label_pill, num_badge
from facility import EDGES, NODES, STALL_L, STALL_W, Map, Scene
from fig_reserve import _hl_code, _overlap, _rect_at, AGV_L, AGV_W
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T

DOC = "04-motion-planning.html"
QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)
QA = {n for n in NODES if NODES[n].section == "sandbox_qa"}
ADJ: dict = {}
for _a, _b in EDGES:
    ADJ.setdefault(_a, []).append(_b)
    ADJ.setdefault(_b, []).append(_a)

OFF = T.red          # switched off by the filter
OPEN = T.sky         # in the open set / current
DONE = T.fg2         # closed
GOAL = T.green
CODE_W = 700


def _lab(n):
    return NODES[n].label


def _sweep(a, b, L=STALL_L, W=STALL_W):
    ra, rb = _rect_at(a, L, W), _rect_at(b, L, W)
    return (min(ra[0], rb[0]), min(ra[1], rb[1]), max(ra[2], rb[2]), max(ra[3], rb[3]))


def _qa_map(d, s=34.0):
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    return m


def _edge_line(d, m, a, b, color, *, sw=3.0, dash="4 4", layer="over"):
    (x0, y0), (x1, y1) = m.P(a), m.P(b)
    d.line(x0, y0, x1, y1, stroke=color, sw=sw, dash=dash, layer=layer)


def _xmark(d, m, nid, color=OFF):
    x, y = m.P(nid)
    d.line(x - 7, y - 7, x + 7, y + 7, stroke=color, sw=2.6, layer="top")
    d.line(x - 7, y + 7, x + 7, y - 7, stroke=color, sw=2.6, layer="top")


def _area(d, m, rect, color, *, k):
    x0, y0, x1, y1 = rect
    X0, X1 = m.X(x0), m.X(x1)
    Y0, Y1 = m.Y(y1), m.Y(y0)
    with k:
        d.rect(X0, Y0, X1 - X0, Y1 - Y0, rx=5, fill=color, opacity=0.12, layer="over")
        d.rect(X0, Y0, X1 - X0, Y1 - Y0, rx=5, fill="none", stroke=color, sw=1.8, dash="6 4", layer="over")


# ======================================================================================
# 140 — who calls which search
# ======================================================================================

@figure("140_search_toolbox", "The single-agent searches: callers, environments and filters", DOC)
def search_toolbox():
    d = Doc("140_search_toolbox", "The single-agent searches in motion_planner",
            "Static: which scheduler methods call which search function, which environment each search uses, and "
            "how GetStaticFilter feeds all of them. Every search runs on the same SingleSourceSearch engine.")
    col_x = [0, 330, 690, 1080]
    col_w = [290, 320, 320, 300]
    heads = ["Called from (scheduler)", "Search function", "Search environment (goal and cost)",
             "Engine and inputs"]
    for x, w, h in zip(col_x, col_w, heads):
        d.text(x, 0, h, size=12.5, family="mono", weight=600, fill=T.muted)

    def box(x, y, w, h, title, sub, *, col=T.border, title_col=T.fg, mono=True):
        d.rect(x, y, w, h, rx=9, fill=T.card, stroke=col, sw=1.4)
        d.text(x + 12, y + 20, title, size=13, family="mono" if mono else "sans", weight=600, fill=title_col)
        for i, ln in enumerate(sub):
            d.text(x + 12, y + 40 + i * 17, ln, size=11.5, fill=T.fg2)
        return BBox(x, y, x + w, y + h)

    rows = [  # (callers, function, environment)
        (["GetJustMovingCost", "IsMovePossible, MoveAgvToTrayPose", "TryClearBlockedAgvMove",
          "InitRetrievalHeadings"],
         ("GetPosePath", ["shortest pose path for one AGV", "then ConvertPosePathToTrajectory"]),
         ("GarageGraphEnvironment", ["goal: the target vertex", "step: trapezoid time of the edge"])),
        (["DoTrayAssignments", "(the blocking-tray loop)"],
         ("SingleSourceSearch", ["called directly"]),
         ("BlockingTraySearchEnvironment", ["goal: the target vertex", "step: time + 30 s per tray crossed"])),
        (["FindOpenSpaceForRootTray", "TryFindBlockingTrayResolution"],
         ("SingleSourceSearch", ["called directly"]),
         ("OpenSpaceSearchEnvironment", ["goal: first free parking or", "EV-charge node that fits"])),
        (["AssignTrayIdForEmptyMove"],
         ("SingleSourceSearch", ["called directly"]),
         ("EmptyTraySearchEnvironment", ["goal: first node holding", "a tray without a payload"])),
        (["PlanCleanGarageJob"],
         ("HideAgvs", ["one search per AGV,", "greedy with backtracking"]),
         ("AgvSearchEnvironment", ["no goal: explores everything", "step: 1 s per edge"])),
    ]
    y = 26
    env_boxes = []
    rh = 104
    for callers, (fn, fsub), (env, esub) in rows:
        b0 = box(col_x[0], y, col_w[0], rh - 16, callers[0], callers[1:], mono=True)
        b1 = box(col_x[1], y, col_w[1], rh - 16, fn, fsub, col=T.tint(T.sky, 0.6, T.bg))
        b2 = box(col_x[2], y, col_w[2], rh - 16, env, esub, col=T.tint(T.sky, 0.6, T.bg))
        for (a, b) in ((b0, b1), (b1, b2)):
            d.line(a.x1, a.y0 + a.h / 2, b.x0 - 6, b.y0 + b.h / 2, stroke=T.fg2, sw=1.5)
            d.arrowhead((b.x0 - 2, b.y0 + b.h / 2), (a.x1, a.y0 + a.h / 2), kind="filled", color=T.fg2, size=8)
        env_boxes.append(b2)
        y += rh
    # engine and filters
    ey = 26
    eng = box(col_x[3], ey, col_w[3], 190, "SingleSourceSearch", [
        "one A* function template (path_search.hpp)", "open set: Fibonacci heap, lowest f first",
        "closed set and predecessors in one map", "zero heuristic here, so it is Dijkstra",
        "stops when OnExpansion returns true", "at most 5,000,000 expansions"], col=T.sky, title_col=T.sky)
    flt = box(col_x[3], ey + 230, col_w[3], 190, "GetStaticFilter", [
        "per footprint type: which poses and", "edges are usable, given parked trays,",
        "AGVs, bays not ready to retrieve,", "disabled nodes and node size",
        "-> GraphFilterProperties", "(two boolean masks)"], col=OFF, title_col=OFF)
    bus = eng.x0 - 22                      # one bus from every environment into the engine
    for b in env_boxes:
        d.line(b.x1, b.y0 + b.h / 2, bus, b.y0 + b.h / 2, stroke=T.sky, sw=1.4)
    d.line(bus, env_boxes[0].y0 + env_boxes[0].h / 2, bus, env_boxes[-1].y0 + env_boxes[-1].h / 2, stroke=T.sky,
           sw=1.4)
    d.line(bus, eng.y0 + 60, eng.x0 - 6, eng.y0 + 60, stroke=T.sky, sw=1.4)
    d.arrowhead((eng.x0 - 2, eng.y0 + 60), (bus, eng.y0 + 60), kind="filled", color=T.sky, size=8)
    d.text(col_x[3], ey + 214, "each search runs on the engine", size=11, fill=T.sky)
    d.text(col_x[3], flt.y1 + 22, "each search reads one filter; edges only,", size=11, fill=OFF)
    d.text(col_x[3], flt.y1 + 39, "except GarageGraph and Agv environments,", size=11, fill=OFF)
    d.text(col_x[3], flt.y1 + 56, "which also test the target vertex", size=11, fill=OFF)
    frame(d, title="The single-agent searches in motion_planner",
          subtitle="Task planning calls these searches while it builds the event DAG. They see only static "
                   "obstacles through a filter and ignore everyone else's timing; only CHUGG, later, plans in time.",
          badge_key="as-built",
          legend=[("box", T.sky, "search function / environment / engine"), ("box", OFF, "static filter")])
    return d


# ======================================================================================
# 141 — SingleSourceSearch, step by step
# ======================================================================================

G_NODES = {"S": (0, 1), "B": (1, 2), "A": (1, 0), "C": (2, 2), "G": (2, 0), "D": (3, 0)}
G_EDGES = [("S", "A", 4), ("S", "B", 1), ("B", "A", 2), ("A", "G", 3), ("B", "C", 6), ("C", "G", 2),
           ("G", "D", 2)]


def _sss_trace():
    """Dijkstra exactly as SingleSourceSearch runs it with a zero heuristic and a target G."""
    adj = {}
    for a, b, w in G_EDGES:
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))
    for k in adj:
        adj[k].sort()
    g = {"S": 0}
    pred = {"S": ("S", 0)}
    closed = []
    open_ = {"S": 0}
    trace = []   # (kind, node, detail)
    trace.append(("init", "S", dict(open=dict(open_), closed=list(closed), pred=dict(pred))))
    while open_:
        u = min(open_, key=lambda n: (open_[n], -open_[n], n))
        if u == "G":
            trace.append(("goal", u, dict(open=dict(open_), closed=list(closed), pred=dict(pred))))
            return trace
        del open_[u]
        closed.append(u)
        events = []
        for v, w in adj[u]:
            if v in closed:
                events.append(("skip", v, None))
                continue
            t = g[u] + w
            if v not in open_:
                open_[v] = t
                g[v] = t
                pred[v] = (u, w)
                events.append(("discover", v, t))
            elif t < open_[v]:
                events.append(("update", v, (open_[v], t)))
                open_[v] = t
                g[v] = t
                pred[v] = (u, w)
            else:
                events.append(("worse", v, t))
        trace.append(("expand", u, dict(open=dict(open_), closed=list(closed), pred=dict(pred), events=events)))
    return trace


SSS = _sss_trace()
assert [t[1] for t in SSS if t[0] == "expand"] == ["S", "B", "A"] and SSS[-1][0] == "goal"


@figure("141_single_source_search", "SingleSourceSearch: the A* engine every search uses (animated)", DOC)
def single_source_search():
    d = Doc("141_single_source_search", "SingleSourceSearch, step by step",
            "Animated: the generic search on a six-node graph with a zero heuristic, as every scheduler search "
            "runs it. Each step pops the cheapest open node, asks the environment whether it is a goal, closes it "
            "and asks the environment for its neighbors.")
    steps = []
    for kind, u, info in SSS:
        if kind == "init":
            cap = ("Start: the source S goes into the open set with cost 0 (init_cost plus the heuristic, which is "
                   "0). The predecessor map records S as its own predecessor; that is how GetPath later knows "
                   "where to stop.")
        elif kind == "goal":
            cap = ("G is the cheapest open node. OnExpansion(G) returns true, the environment's goal test, so the "
                   "search returns at once: SearchSolution keeps the predecessor map and target = G. "
                   "GetPath(G) walks the predecessors back: G <- A <- B <- S, cost 6. C and D are never expanded.")
        else:
            parts = []
            for ev, v, det in info["events"]:
                if ev == "discover":
                    parts.append(f"{v} discovered at {det}")
                elif ev == "update":
                    parts.append(f"{v} improved from {det[0]} to {det[1]} (decrease key, new predecessor {u})")
                elif ev == "skip":
                    parts.append(f"{v} is closed, skipped")
                else:
                    parts.append(f"{v} not improved")
            cap = (f"Pop {u} (cost {SSS_g(u)}). OnExpansion({u}) is false, so {u} is closed. "
                   f"GetNeighbors({u}): " + "; ".join(parts) + ".")
        steps.append(d.step(cap))
    # ---- graph (left)
    gx0, gy0, sx, sy = 40, 100, 170, 120
    P = {n: (gx0 + c * sx, gy0 + r * sy) for n, (c, r) in G_NODES.items()}
    d.text(0, 20, "the graph: nodes are states, numbers are step costs", size=12.5, family="mono", weight=600,
           fill=T.fg2)
    for a, b, w in G_EDGES:
        (x0, y0), (x1, y1) = P[a], P[b]
        d.line(x0, y0, x1, y1, stroke=T.border, sw=1.6)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        label_pill(d, mx, my, str(w), color=T.fg2, size=11, bg=T.bg)
    expanded_at = {}
    for k, (kind, u, info) in enumerate(SSS):
        if kind == "expand":
            expanded_at[u] = k
    for n, (x, y) in P.items():
        d.circle(x, y, 22, fill=T.card, stroke=T.fg2, sw=1.6)
        d.text(x, y + 0.5, n, size=15, family="mono", weight=700, fill=T.fg, anchor="middle", layer="labels")
    # per-step overlays: open ring, closed fill, g labels, predecessor arrows
    for k, (kind, u, info) in enumerate(SSS):
        with d.only(k):
            for n, gv in info["open"].items():
                x, y = P[n]
                d.circle(x, y, 27, fill="none", stroke=OPEN, sw=2.2, dash="4 3", layer="over")
                label_pill(d, x, y - 40, f"g = {gv}", color=OPEN, size=11, bg=T.bg, border=OPEN)
            for n in info["closed"]:
                x, y = P[n]
                d.circle(x, y, 22, fill=T.tint(DONE, 0.25, T.bg), stroke=DONE, sw=2, layer="over")
            for n, (p, _w) in info["pred"].items():
                if p == n:
                    continue
                (x0, y0), (x1, y1) = P[n], P[p]
                L = math.hypot(x1 - x0, y1 - y0)
                ux, uy = (x1 - x0) / L, (y1 - y0) / L
                d.line(x0 + ux * 26, y0 + uy * 26, x1 - ux * 30, y1 - uy * 30, stroke=T.violet, sw=2.2,
                       layer="top")
                d.arrowhead((x1 - ux * 28, y1 - uy * 28), (x0, y0), kind="filled", color=T.violet, size=9,
                            layer="top")
            cur = u
            x, y = P[cur]
            d.circle(x, y, 31, fill="none", stroke=GOAL if kind == "goal" else T.amber, sw=3, layer="top")
            if kind == "goal":
                path = ["G", "A", "B", "S"]
                for a, b in zip(path, path[1:]):
                    (x0, y0), (x1, y1) = P[a], P[b]
                    d.line(x0, y0, x1, y1, stroke=GOAL, sw=5, opacity=0.45, layer="under")
    # ---- state tables under the graph
    ty = gy0 + 2 * sy + 70
    d.text(0, ty, "open set (lowest cost first)", size=12, family="mono", weight=600, fill=OPEN)
    d.text(330, ty, "closed", size=12, family="mono", weight=600, fill=DONE)
    d.text(520, ty, "callback this step", size=12, family="mono", weight=600, fill=T.amber)
    for k, (kind, u, info) in enumerate(SSS):
        with d.only(k):
            for i, (n, gv) in enumerate(sorted(info["open"].items(), key=lambda t: (t[1], t[0]))):
                d.text(4, ty + 24 + i * 20, f"{n}  g = {gv}", size=12, family="mono", fill=T.fg)
            d.text(334, ty + 24, ", ".join(info["closed"]) or "(none)", size=12, family="mono", fill=T.fg)
            cb = {"init": ["GetHeuristic(S) = 0"],
                  "goal": ["OnExpansion(G) -> true", "OnTermination()"],
                  "expand": [f"OnExpansion({u}) -> false", f"GetNeighbors({u})"]}[kind]
            if kind == "expand":
                for ev, v, _det in info["events"]:
                    if ev == "discover":
                        cb.append(f"OnDiscovery({v})")
                    elif ev == "update":
                        cb.append(f"OnUpdate({v})")
            for i, s in enumerate(cb):
                d.text(524, ty + 24 + i * 20, s, size=12, family="mono", fill=T.fg)
    # ---- code (right)
    cx = 720
    cp = code_panel(d, cx, 0, CODE_W, [
        "// path_search.hpp, SingleSourceSearch (abridged)",
        "PushOpenSet(source, init_cost, init_cost + env.GetHeuristic(source));",
        "predecessors[source] = {source, init_cost, /*closed=*/false};",
        "while(!open_set.empty() && ++n <= kMaxExpansions) {",
        "  SearchNode current = open_set.top();      // lowest f, then highest g",
        "  if(env.OnExpansion(current.state, current.g_val, meta))",
        "    return SearchSolution(source, predecessors, meta, current.state);",
        "  open_set.pop();  mark current closed in predecessors;",
        "  for(auto& [next, step] : env.GetNeighbors(current.state)) {",
        "    if(next is closed) continue;",
        "    Cost g = current.g_val + step;",
        "    if(next not in open set) {",
        "      push(next, g, g + env.GetHeuristic(next));",
        "      predecessors[next] = {current.state, step};  env.OnDiscovery(...);",
        "    } else if(g < g of next in open set) {",
        "      decrease key;  predecessors[next] = {current.state, step};",
        "      env.OnUpdate(...);",
        "    }",
        "  }",
        "}",
        "return SearchSolution(source, predecessors, meta);   // no target",
    ], title="the engine: one loop, callbacks into the environment", size=11.5)
    hl = {}
    for k, (kind, u, info) in enumerate(SSS):
        hl[k] = {"init": (1, 2), "goal": (5, 6), "expand": (4, 16)}[kind]
    for k, (a, b) in hl.items():
        with d.only(k):
            _hl_code(d, cp, a, b, size=11.5)
    # contract box under the code
    by = cp.y1 + 18
    d.rect(cx, by, CODE_W, 132, rx=9, fill=T.card, stroke=T.border, sw=1.2)
    d.text(cx + 12, by + 20, "SearchEnvironment<State, Cost>: what each search supplies", size=12, family="mono",
           weight=600, fill=T.fg)
    for i, (k_, v_) in enumerate([("OnExpansion(state, g, meta)", "true = stop here: the goal test"),
                                  ("GetNeighbors(state)", "next states and the cost of each step"),
                                  ("GetHeuristic(state)", "estimate to go; 0 in every scheduler search"),
                                  ("OnDiscovery / OnUpdate / OnTermination", "optional hooks, logging")]):
        d.text(cx + 14, by + 46 + i * 21, k_, size=11.5, family="mono", fill=T.sky)
        d.text(cx + 330, by + 46 + i * 21, v_, size=11.5, fill=T.fg2)
    frame(d, title="SingleSourceSearch: the engine behind every single-agent search",
          subtitle="A generic A* (Dijkstra when the heuristic is zero). The environment decides what a state is, what "
                   "its neighbors cost and when to stop; the engine only orders the work.",
          badge_key="as-built",
          legend=[("ring", OPEN, "open, with cost so far g"), ("fill", DONE, "closed"),
                  ("ring", T.amber, "node being expanded"), ("arrow", T.violet, "predecessor"),
                  ("ring", GOAL, "goal: OnExpansion returned true")])
    return d


def SSS_g(u):
    for kind, n, info in SSS:
        if kind != "init" and n == u:
            pass
    # cost of u when popped = its g in the step before
    g = {}
    for kind, n, info in SSS:
        for k_, v_ in info["open"].items():
            g.setdefault(k_, v_)
            g[k_] = min(g[k_], v_)
    g["S"] = 0
    return g[u]


# ======================================================================================
# 142 — GetStaticFilter
# ======================================================================================

F_TRAYS = {15: "K", 20: "T20"}        # parked, not ignored
F_IGNORED = {17: "T17"}               # the tray being moved: in ignore_trays
F_AGV = 26                            # AGV-1 on W26, not ignored
F_DISABLED = 24                       # P24 in disabled_nodes_
ODP = (23.1233 + STALL_L / 2 - 0.4, 21.7383 - STALL_W / 2, 23.1233 + STALL_L / 2 + 1.6, 21.7383 + STALL_W / 2)


def _off_by(vol_list, L=STALL_L, W=STALL_W):
    """Poses and edges a TRAY footprint cannot use because of the given volumes (plain rectangles)."""
    poses = {n for n in QA if any(_overlap(_rect_at(n, L, W), v) for v in vol_list)}
    edges = {(a, b) for a, b in EDGES if a in QA and b in QA and any(_overlap(_sweep(a, b), v) for v in vol_list)}
    return poses, edges


F_STEPS = [
    ("trays", [_rect_at(n, STALL_L, STALL_W) for n in F_TRAYS]),
    ("agvs", [_rect_at(F_AGV, AGV_L, AGV_W)]),
    ("bays", [ODP]),
    ("disabled", [_rect_at(F_DISABLED, STALL_L, STALL_W)]),
]
F_OFF = {k: _off_by(v) for k, v in F_STEPS}


@figure("142_static_filter", "GetStaticFilter: from garage state to graph masks (animated)", DOC)
def static_filter():
    d = Doc("142_static_filter", "GetStaticFilter, source by source",
            "Animated: the filter for a TRAY footprint, built from one garage state in the four passes of the "
            "code. Each pass asks the CollisionTable where a tray cannot be because of something else and switches "
            "those poses and edges off.")
    S0 = d.step("The garage state and the call: GetStaticFilter(TRAY, gg, dgs, ctable, ignore_trays = {T17}, "
                "ignore_agvs = {}, ignore_bays = {}). Tray T17 is the one being moved, so it is ignored. "
                "Trays K and T20 are parked, AGV-1 stands on W26, bay B21 is READY_TO_INSERT and node P24 is "
                "disabled.")
    S1 = d.step("Pass 1, parked trays. For each tray not in ignore_trays, Query(tray footprint, TRAY, tray pose) "
                "returns every pose and edge where a moving tray would overlap it. K and T20 switch off their own "
                "nodes and the edges into them. T17 is skipped: it is the tray being moved.")
    S2 = d.step("Pass 2, AGVs. AGV-1 is not ignored, so the area of an AGV at W26 is switched off for a tray. "
                "For a TRAY or payload footprint the code queries against TRAY, because an AGV meets a tray's "
                "legs before its payload.")
    S3 = d.step("Pass 3, bays. A bay that is not READY_TO_RETRIEVE has its overdrive plate out, so its BAY_ODP "
                "volume is switched off: B21 itself and the approach from W41. A bay that is ready to retrieve "
                "is skipped entirely.")
    S4 = d.step("Pass 4, disabled nodes. P24 is in disabled_nodes_ (or holds a disabled asset), so it is blocked at "
                "its largest window, PAYLOAD + max_resource_size_index, for every heading of the node, whatever is "
                "really there.")
    S5 = d.step("Result: GraphFilterProperties(gg, disabled_poses, disabled_edges) starts with every vertex and "
                "edge enabled and sets the listed ones to false. A fifth pass runs only for payload footprints: "
                "nodes whose largest window is too small are switched off too.")
    m = _qa_map(d)
    mb = m.box
    sc = Scene(m)
    sc.tray("K", 15, chip_pos="bl")
    sc.tray("T20", 20, payload=True, chip_pos="bl")
    sc.tray("T17 (moving)", 17, payload=True, chip_pos="bl", emphasis=True)
    sc.agv("AGV-1", F_AGV, heading=90, label_side="above")
    sc.draw()
    bx, by = m.P(21)
    label_pill(d, bx, by - 52, "B21 READY_TO_INSERT", color=T.teal, size=10.5, bg=T.bg_deep, border=T.teal)
    x24, y24 = m.P(24)
    label_pill(d, x24, y24 + 26, "P24 disabled", color=OFF, size=10.5, bg=T.bg_deep, border=OFF)
    passes = [("trays", S1), ("agvs", S2), ("bays", S3), ("disabled", S4)]
    for i, (key, k) in enumerate(passes):
        vols = dict(F_STEPS)[key]
        for v in vols:
            _area(d, m, v, OFF, k=d.only(k))
        poses, edges = F_OFF[key]
        with d.at(k, S5):
            for a, b in sorted(edges):
                _edge_line(d, m, a, b, OFF)
            for n in sorted(poses):
                _xmark(d, m, n)
    with d.only(S1):
        x, y = m.P(17)
        label_pill(d, x - 40, y - 34, "ignored: not an obstacle", color=T.amber, size=10.5, bg=T.bg_deep, border=T.amber)
    # mask strip under the map
    all_poses = set().union(*[F_OFF[k][0] for k in F_OFF])
    all_edges = set().union(*[F_OFF[k][1] for k in F_OFF])
    vy = mb.y1 + 30
    d.text(mb.x0, vy, "vertex_filter_ for the QA poses (all headings 90 here)", size=12, weight=600, fill=T.fg)
    verts = [21, 41, 22, 25, 26, 27, 18, 13, 23, 24, 19, 20, 15, 17]
    cw = (mb.w - (len(verts) - 1) * 4) / len(verts)
    for i, n in enumerate(verts):
        x0 = mb.x0 + i * (cw + 4)
        d.rect(x0, vy + 12, cw, 42, rx=6, fill=T.card, stroke=T.border, sw=1)
        d.text(x0 + cw / 2, vy + 26, _lab(n), size=10.5, family="mono", fill=T.fg2, anchor="middle")
        with d.at(S0, S4):
            d.text(x0 + cw / 2, vy + 44, "·", size=12, family="mono", fill=T.muted, anchor="middle")
        with d.at(S5):
            off = n in all_poses
            d.text(x0 + cw / 2, vy + 44, "false" if off else "true", size=10.5, family="mono", weight=700,
                   fill=OFF if off else GOAL, anchor="middle")
    with d.at(S5):
        d.text(mb.x0, vy + 80, f"{len(all_poses)} poses and {len(all_edges)} edges switched off in this section; "
                               "the graph itself is not edited.", size=11.5, fill=T.fg2)
    # code (right)
    cx = mb.x1 + 40
    cp = code_panel(d, cx, mb.y0, CODE_W + 60, [
        "// static_graph_filtering.cpp, GetStaticFilter (abridged)",
        "all_disabled_nodes = dgs.GetDisabledNodes();",
        "for(const auto& [id, tray] : dgs.GetTrays()) {           // 1. parked trays",
        "  if(tray.disabled) all_disabled_nodes.insert(tray.pose.node_id);",
        "  if(ignore_trays.count(id)) continue;",
        "  other = footprint of tray (TRAY_LEGS if collision_id is AGV);",
        "  off += ctable.Query(other, collision_id, tray.pose);",
        "}",
        "for(const auto& [id, agv] : dgs.GetAgvs()) {             // 2. AGVs",
        "  if(agv.disabled) all_disabled_nodes.insert(agv.pose.node_id);",
        "  if(ignore_agvs.count(id)) continue;",
        "  off += ctable.Query(AGV, collision_id >= AGV ? TRAY : collision_id, agv.pose);",
        "}",
        "for(const auto& [id, bay] : dgs.GetBays()) {             // 3. bays",
        "  if(bay.disabled) all_disabled_nodes.insert(id);",
        "  if(ignore_bays.count(id) || bay.state == READY_TO_RETRIEVE) continue;",
        "  off += ctable.Query(BAY_ODP, collision_id, {id, inbound heading});",
        "}",
        "for(auto node_id : all_disabled_nodes)                    // 4. disabled nodes",
        "  for(auto head : node.headings)",
        "    off += ctable.Query(PAYLOAD + max window (or TRAY), collision_id, {node_id, head});",
        "if(collision_id >= PAYLOAD)                               // 5. node too small",
        "  off += every pose whose max window < this size, with its in- and out-edges;",
        "return GraphFilterProperties(gg, disabled_poses, disabled_edges);  // all true, listed false",
    ], title="one call per footprint type", size=11)
    for k, (a, b) in {S0: (0, 0), S1: (2, 7), S2: (8, 12), S3: (13, 17), S4: (18, 20), S5: (21, 23)}.items():
        with d.only(k):
            _hl_code(d, cp, a, b, size=11)
    frame(d, title="GetStaticFilter: from garage state to graph masks",
          subtitle="Nothing is removed from the graph: the filter is two boolean masks over its vertices and edges. "
                   "Areas are plain rectangles with no buffer; the real sets come from CollisionTable::Query.",
          badge_key="yaml+hyp",
          legend=[("dashbox", OFF, "volume queried in this pass"), ("dash", OFF, "edge switched off"),
                  ("ring", OFF, "x = pose switched off")])
    return d


# ======================================================================================
# 143 — BlockingTraySearchEnvironment and OpenSpaceSearchEnvironment
# ======================================================================================

B_TRAYS = {15: "K", 20: "T20", 19: "T19", 24: "T24"}
B_SRC = 17   # tray T17 (R) at P17
B_TARGET = 21


def _blocking_trace():
    def crossed(a, b):
        s = _sweep(a, b)
        return {t for n, t in B_TRAYS.items() if _overlap(s, _rect_at(n, STALL_L, STALL_W))}
    g, bl, pred = {B_SRC: 0}, {B_SRC: frozenset()}, {B_SRC: B_SRC}
    closed, pq, c = [], [(0, 0, B_SRC)], 0
    while pq:
        gv, _, u = heapq.heappop(pq)
        if u in closed or gv > g[u]:
            continue
        closed.append(u)
        for v in ADJ[u]:
            if v not in QA or v in closed or NODES[v].type == "AgvCharge":
                continue
            L = math.dist((NODES[u].x, NODES[u].y), (NODES[v].x, NODES[v].y))
            new = crossed(u, v) - bl[u]
            t = gv + round(L) + 30 * len(new)
            if v not in g or t < g[v]:
                if v not in g:
                    bl[v] = bl[u] | new          # the code keeps the first-found set
                g[v], pred[v] = t, u
                c += 1
                heapq.heappush(pq, (t, c, v))
    return closed, g, bl, pred


B_CLOSED, B_G, B_BL, B_PRED = _blocking_trace()
assert B_CLOSED[:3] == [17, 20, 15] and B_G[21] == 54 and B_BL[21] == {"K"}
B_OPEN = next(n for n in B_CLOSED if NODES[n].type == "Parking" and n not in B_TRAYS and n != B_SRC)
B_STASH = next(n for n in B_CLOSED if NODES[n].type in ("Parking", "Waypoint") and n not in B_TRAYS
               and n != B_SRC)
assert B_OPEN == 23 and B_STASH == 13, (B_OPEN, B_STASH)


def _path(pred, n):
    out = [n]
    while pred[n] != n:
        n = pred[n]
        out.append(n)
    return out[::-1]


@figure("143_blocking_tray_search", "BlockingTraySearchEnvironment and OpenSpaceSearchEnvironment (animated)", DOC)
def blocking_tray_search():
    d = Doc("143_blocking_tray_search", "One expansion, three goal tests",
            "Animated: tray T17 at P17 searched outward with the blocking-tray cost. Nodes are closed in cost "
            "order; each carries the trays crossed on the way. The goal test of each environment decides where "
            "the same expansion stops.")
    order = B_CLOSED[: B_CLOSED.index(B_TARGET) + 1]
    S0 = d.step("The tray to move is T17 at P17. Trays K, T19, T20 and T24 are parked. The filter keeps static "
                "obstacles out; parked trays are not filtered here, they are paid for. Each step costs the edge's "
                "trapezoid time (here: length at 1 m/s, illustrative) plus 30 s for each tray the moving tray's "
                "footprint newly overlaps.")
    pop_step = {}
    for i, n in enumerate(order):
        bl = sorted(B_BL[n])
        extra = ""
        if n == 20:
            extra = " Entering P20 overlaps T20: +30 s."
        if n == 15:
            extra = " Entering P15 overlaps K: +30 s. Every route out of P17 crosses a tray."
        if n == B_OPEN:
            extra = (f" {_lab(n)} is the first free parking node closed: OpenSpaceSearchEnvironment would stop "
                     "here (its goal test).")
        if n == B_STASH:
            extra = (f" {_lab(n)} is a free waypoint: with allow_waypoint_stash the open-space search would "
                     "already stop here, at tier 2.")
        if n == B_TARGET:
            extra = (" B21 is the target vertex: BlockingTraySearchEnvironment stops. Path P17 -> P15 -> W13 -> "
                     "W18 -> W22 -> W41 -> B21, blocking_trays = {K}: the loop must move K first.")
        pop_step[n] = d.step(f"Close {_lab(n)} at {B_G[n]} s, trays crossed {{{', '.join(bl)}}}.{extra}")
    S_END = len(d.steps) - 1
    m = _qa_map(d)
    mb = m.box
    sc = Scene(m)
    sc.tray("T17 (moving)", B_SRC, payload=True, chip_pos="bl", emphasis=True)
    for n, t in B_TRAYS.items():
        sc.tray(t, n, payload=(t != "K"), chip_pos="bl")
    sc.draw()
    for n in order:
        k = pop_step[n]
        x, y = m.P(n)
        with d.at(k):
            col = GOAL if n in (B_OPEN, B_STASH, B_TARGET) else DONE
            label_pill(d, x + 14, y - 22, f"{B_G[n]} s", color=col, size=10.5, anchor="start", bg=T.bg_deep,
                       border=col)
        with d.only(k):
            d.circle(x, y, 18, fill="none", stroke=T.amber, sw=3, layer="top")
            p = B_PRED[n]
            if p != n:
                _edge_line(d, m, p, n, T.amber, sw=4, dash=None)
    with d.at(pop_step[B_OPEN]):
        x, y = m.P(B_OPEN)
        d.circle(x, y, 24, fill="none", stroke=GOAL, sw=2.2, dash="4 3", layer="top")
    with d.at(pop_step[B_STASH]):
        x, y = m.P(B_STASH)
        d.circle(x, y, 24, fill="none", stroke=GOAL, sw=2.2, dash="2 3", layer="top")
    with d.at(S_END):
        m.route(_path(B_PRED, B_TARGET), GOAL, sw=3.5, offset=(0, 10))
    # goal tests (right)
    cx = mb.x1 + 40
    cw = CODE_W
    d.text(cx, mb.y0 + 4, "the environments share GetNeighbors; each has its own OnExpansion", size=12.5,
           family="mono", weight=600, fill=T.fg2)
    tests = [
        ("BlockingTraySearchEnvironment", "OnExpansion: state.vert == target",
         ["the cheapest route to one target pose,", "and the trays on it (blocking_trays)"], pop_step[B_TARGET]),
        ("OpenSpaceSearchEnvironment", "OnExpansion: a free parking or EV-charge node",
         ["no tray on it, not an illegal pose, retrieval heading", "if asked, a VECS for an EV-charge car, height fits;",
          "a free waypoint too if allow_waypoint_stash"], pop_step[B_OPEN]),
        ("EmptyTraySearchEnvironment", "OnExpansion: a node holding a tray without a payload",
         ["searches from the destination outward; see", "AssignTrayIdForEmptyMove (Task planning tab)"], None),
    ]
    ty = mb.y0 + 24
    for title, test, lines, k in tests:
        h = 52 + 17 * len(lines)
        d.rect(cx, ty, cw, h, rx=9, fill=T.card, stroke=T.tint(T.sky, 0.6, T.bg), sw=1.3)
        d.text(cx + 12, ty + 19, title, size=12.5, family="mono", weight=600, fill=T.sky)
        d.text(cx + 12, ty + 38, test, size=11.5, family="mono", fill=T.fg)
        for i, ln in enumerate(lines):
            d.text(cx + 12, ty + 58 + i * 17, ln, size=11.5, fill=T.fg2)
        if k is not None:
            with d.at(k):
                stop = {pop_step[B_TARGET]: f"stops at {_lab(B_TARGET)}, {B_G[B_TARGET]} s",
                        pop_step[B_OPEN]: f"stops at {_lab(B_OPEN)}, {B_G[B_OPEN]} s "
                                          f"({_lab(B_STASH)}, {B_G[B_STASH]} s, with a waypoint stash)"}[k]
                label_pill(d, cx + cw - 12, ty + 19, stop, color=GOAL, size=10.5, anchor="end", bg=T.bg_deep,
                           border=GOAL)
        ty += h + 12
    cp = code_panel(d, cx, ty + 6, cw, [
        "// blocking_tray_search.cpp, BlockingTraySearchEnvironment::GetNeighbors (abridged)",
        "for(auto edge : graph_.GetOutEdges(state.vert)) {",
        "  if(filters_ && !filters_->IsEnabled(edge)) continue;   // edges only",
        "  neighbor = {target(edge), state.blocking_trays};",
        "  cost = cost_model_.Duration(transition);               // trapezoid time",
        "  for(const auto& [id, tray] : base_state_.GetTrays()) {",
        "    if(id == tray_id_) continue;                         // the moving tray",
        "    if(table_.Query(tray footprint, collision_id_, tray.pose, edge))",
        "      if(neighbor.blocking_trays.insert(id).second) cost += 30s;",
        "  }",
        "  if(!max_blocking_trays_ || neighbor.blocking_trays.size() <= *max_blocking_trays_)",
        "    neighbors.emplace_back(neighbor, cost);",
        "}",
    ], title="the shared step cost", size=11)
    for n in order:
        with d.only(pop_step[n]):
            _hl_code(d, cp, 3, 8, size=11)
    frame(d, title="One expansion, three goal tests",
          subtitle="The three tray searches differ only in where they start and in OnExpansion. Times are "
                   "illustrative (1 m/s, no acceleration); the +30 s per crossed tray is the code's constant.",
          badge_key="yaml+hyp",
          legend=[("ring", T.amber, "node closed this step, with its predecessor edge"),
                  ("dot", DONE, "closed, with its cost"), ("ring", GOAL, "where a goal test stops"),
                  ("route", GOAL, "path returned to the blocking-tray loop")])
    return d


# ======================================================================================
# 144 — HideAgvs
# ======================================================================================

H_TRAYS = {23: "T23", 15: "T15", 17: "T17"}
H_AGVS = {"AGV-1": 26, "AGV-2": 22}


def _hide_bfs(src, blocked):
    dist, order = {src: 0}, [src]
    q = [src]
    while q:
        u = q.pop(0)
        for v in sorted(ADJ[u]):
            if v in QA and v not in dist and v not in blocked and NODES[v].type != "Bay":
                dist[v] = dist[u] + 1
                order.append(v)
                q.append(v)
    dests = [n for n in order if n in H_TRAYS]
    return dist, order, dests


H1 = _hide_bfs(H_AGVS["AGV-1"], {H_AGVS["AGV-2"]})
H1_DEST = H1[2][0]
H2 = _hide_bfs(H_AGVS["AGV-2"], {H1_DEST})
H2_DEST = H2[2][0]
assert H1_DEST == 23 and H2_DEST == 15, (H1_DEST, H2_DEST)


@figure("144_hide_agvs", "HideAgvs: a hiding tray for every AGV (animated)", DOC)
def hide_agvs():
    d = Doc("144_hide_agvs", "HideAgvs, AGV by AGV",
            "Animated: two AGVs are sent under trays before a CLEAN_GARAGE job. Each AGV gets one search that "
            "explores everything at 1 s per edge; the tray poses it reaches become its candidate list, nearest "
            "first. The first AGV takes its nearest candidate, and the next AGV searches again in the changed "
            "garage.")
    S0 = d.step("Input: the garage state. AGV-1 stands on W26 and AGV-2 on W22; trays T15, T17 and T23 are "
                "parked. The goal: every enabled AGV under a tray, as a map from AGV id to pose.")
    S1 = d.step("AGV-1: GetStaticFilter(AGV, ..., ignore_agvs = {AGV-1}). For an AGV, parked trays count only "
                "with their legs, so an AGV can drive under them; AGV-2 at W22 is an obstacle.")
    S2 = d.step("SingleSourceSearch with AgvSearchEnvironment: every edge costs 1 s and OnExpansion never stops "
                "the search, so it closes every reachable pose. Each closed pose under a tray (same or reciprocal "
                "heading) is appended to the candidate list, so the list is in order of edge count.")
    S3 = d.step(f"AGV-1 takes its first candidate, {_lab(H1_DEST)}. The move is applied to a copy of the garage "
                "state (OnEvent(AgvPoseChanged)), and HideOneAgv recurses for the remaining AGVs.")
    S4 = d.step(f"AGV-2 searches again in the changed copy: AGV-1 now stands at {_lab(H1_DEST)}, so that pose is "
                f"blocked. The nearest remaining candidate is {_lab(H2_DEST)}.")
    S5 = d.step("Every AGV has a pose: the recursion returns {AGV-1: " + _lab(H1_DEST) + ", AGV-2: "
                + _lab(H2_DEST) + "}. Had AGV-2 found no candidate, the loop would have tried AGV-1's next "
                "candidate, then the AGVs in another order: the first full assignment found is returned, not the "
                "one with the fewest moves.")
    m = _qa_map(d)
    mb = m.box
    sc = Scene(m)
    for n, t in H_TRAYS.items():
        sc.tray(t, n, payload=(t != "T23"), chip_pos="bl")
    sc.agv("AGV-1", H_AGVS["AGV-1"], heading=90, label_side="above")
    sc.agv("AGV-2", H_AGVS["AGV-2"], heading=90, color=T.violet, label_side="below")
    sc.drive(S3, "AGV-1", _path_bfs(H_AGVS["AGV-1"], H1_DEST, {H_AGVS["AGV-2"]}))
    sc.drive(S5, "AGV-2", _path_bfs(H_AGVS["AGV-2"], H2_DEST, {H1_DEST}))
    sc.draw()
    with d.only(S1):
        x, y = m.P(H_AGVS["AGV-2"])
        d.circle(x, y, 20, fill="none", stroke=OFF, sw=2.4, layer="top")
        label_pill(d, x + 70, y - 30, "obstacle for AGV-1", color=OFF, size=10.5, bg=T.bg_deep, border=OFF)
    for k, (dist, order, dests), col in ((S2, H1, T.green), (S4, H2, T.violet)):
        with d.only(k):
            for n in order:
                x, y = m.P(n)
                label_pill(d, x + 12, y - 20, f"{dist[n]}", color=col, size=10, anchor="start", bg=T.bg_deep,
                           border=col)
            for i, n in enumerate(dests):
                x, y = m.P(n)
                num_badge(d, x - 22, y - 22, i + 1, col, r=10)
    with d.only(S4):
        x, y = m.P(H1_DEST)
        d.circle(x, y, 20, fill="none", stroke=OFF, sw=2.4, layer="top")
    # candidate lists under the map
    ly = mb.y1 + 30
    d.text(mb.x0, ly, "candidate lists (GetSortedDestinations), in the order the search closed them", size=12,
           weight=600, fill=T.fg)
    with d.at(S2):
        d.text(mb.x0, ly + 24, "AGV-1:  " + ",  ".join(f"{_lab(n)} ({H1[0][n]} s)" for n in H1[2]), size=12,
               family="mono", fill=T.green)
    with d.at(S4):
        d.text(mb.x0, ly + 46, "AGV-2:  " + ",  ".join(f"{_lab(n)} ({H2[0][n]} s)" for n in H2[2]), size=12,
               family="mono", fill=T.violet)
    # code (right)
    cx = mb.x1 + 40
    cp = code_panel(d, cx, mb.y0, CODE_W, [
        "// agv_hiding_search.cpp, HideOneAgv (abridged)",
        "if(agvs_to_assign.empty()) return {true, {}};",
        "for(uint16_t agv_id : agvs_to_assign) {           // unordered_set order",
        "  auto filter = GetStaticFilter(AGV, gg, state, table, {}, {agv_id}, {});",
        "  AgvSearchEnvironment env(state, gg, filter);       // 1 s per edge, never stops",
        "  SingleSourceSearch(agv_pose, 0, env);",
        "  for(const auto& dest : env.GetSortedDestinations()) {",
        "    auto working_state = state;  apply AGV move to dest;",
        "    auto next = agvs_to_assign;  next.erase(agv_id);",
        "    auto [ok, rest] = HideOneAgv(working_state, table, next);   // recurse",
        "    if(ok) { rest[agv_id] = dest;  return {true, rest}; }",
        "  }",
        "}",
        "return {false, {}};                                  // no assignment",
    ], title="HideAgvs calls this with every enabled AGV", size=11)
    for k, (a, b) in {S1: (3, 3), S2: (4, 6), S3: (7, 9), S4: (3, 9), S5: (10, 10)}.items():
        with d.only(k):
            _hl_code(d, cp, a, b, size=11)
    frame(d, title="HideAgvs: a hiding tray for every AGV",
          subtitle="Used by PlanCleanGarageJob for job index 0. Distances count edges, not time (a TODO in the "
                   "code); the order among equally near poses depends on the heap. Positions are hypothetical.",
          badge_key="yaml+hyp",
          legend=[("dot", T.green, "AGV-1: edges from its start"), ("dot", T.violet, "AGV-2: edges from its start"),
                  ("ring", OFF, "blocked for this search")])
    return d


def _path_bfs(src, dst, blocked):
    prev, q = {src: src}, [src]
    while q:
        u = q.pop(0)
        for v in sorted(ADJ[u]):
            if v in QA and v not in prev and v not in blocked and NODES[v].type != "Bay":
                prev[v] = u
                q.append(v)
    out = [dst]
    while out[-1] != src:
        out.append(prev[out[-1]])
    return out[::-1]
