"""ScheduleEventDag figures for doc 01 ("Directed acyclic graphs, then ScheduleEventDag"): class family, storage and identity, the operations
on a small example, and the shallow copy used as a work queue in DoAgvAssignments.
Types from sources/repomix-planner-core.xml and the interfaces .msg files."""
from __future__ import annotations

from components import EVENT_COLOR, chip, connect, frame, label_pill, note, uml_class
from fig_concepts import EV, EDG
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S

DOC1 = "01-software-background.html"
ORDER = ["a", "b", "c", "d", "e", "f"]          # insertion order -> vertex index (illustrative)
VIDX = {k: i for i, k in enumerate(ORDER)}
POS = {"a": (0, 0), "b": (1, 0), "c": (2, 0), "d": (3, 0), "e": (0, 1), "f": (1, 1)}


# --------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------

def _node(d: Doc, x, y, k, *, state="normal", w=50, h=30, label=None):
    kind = EV[k][0] if k in EV else "TrayMove"
    col = EVENT_COLOR[kind]
    if state == "gone":
        d.rect(x, y, w, h, rx=7, fill="none", stroke=T.faint, sw=1.1, dash="4 3")
        d.text(x + w / 2, y + h / 2, label or k, size=12, family="mono", fill=T.faint, anchor="middle")
        return BBox(x, y, x + w, y + h)
    fill = T.card
    sw = 1.4
    if state == "hi":
        fill = T.tint(T.green, 0.22, T.bg)
        col2 = T.green
        sw = 2
    elif state == "new":
        fill = T.tint(T.sky, 0.18, T.bg)
        col2 = T.sky
        sw = 2
    else:
        col2 = col
    d.rect(x, y, w, h, rx=7, fill=fill, stroke=col2, sw=sw)
    d.text(x + w / 2, y + h / 2, label or k, size=12.5, family="mono", weight=700, fill=T.fg, anchor="middle")
    return BBox(x, y, x + w, y + h)


def _mini_dag(d: Doc, x0, y0, *, nodes=None, edges=None, states=None, edge_styles=None, gx=74, gy=58,
              extra_nodes=None):
    nodes = nodes if nodes is not None else ORDER
    edges = edges if edges is not None else EDG
    states = states or {}
    edge_styles = edge_styles or {}
    pos = dict(POS)
    if extra_nodes:
        pos.update(extra_nodes)
    boxes = {}
    for k in nodes:
        c, r = pos[k]
        boxes[k] = _node(d, x0 + c * gx, y0 + r * gy, k, state=states.get(k, "normal"))
    for u, v in edges:
        if u not in boxes or v not in boxes:
            continue
        a, b = boxes[u], boxes[v]
        st = edge_styles.get((u, v), "normal")
        col = {"normal": T.fg2, "new": T.sky, "gone": T.red, "bad": T.red}[st]
        dash = "4 3" if st in ("gone", "bad") else None
        if abs(a.cy - b.cy) < 1 and b.x0 - a.x1 < gx:          # neighbours on one row
            pts = [(a.x1, a.cy), (b.x0, b.cy)]
        elif abs(a.cy - b.cy) < 1:                             # skip edge on the same row: arc above
            lift = 14 + 6 * ((b.x0 - a.x1) // gx)
            pts = [(a.cx + 6, a.y0), (a.cx + 6, a.y0 - lift), (b.cx - 6, a.y0 - lift), (b.cx - 6, b.y0)]
        else:
            if b.cy > a.cy:
                pts = [(a.cx, a.y1), (a.cx, (a.y1 + b.y0) / 2), (b.cx, (a.y1 + b.y0) / 2), (b.cx, b.y0)]
            else:
                pts = [(a.cx, a.y0), (a.cx, (a.y0 + b.y1) / 2), (b.cx, (a.y0 + b.y1) / 2), (b.cx, b.y1)]
        connect(d, pts, kind="flow", color=col, size=7, sw=1.4 if st == "normal" else 1.8, dash=dash, radius=5)
    return boxes


def _panel(d: Doc, x, y, w, h, n, title, sub, col=T.sky):
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=T.border_soft, sw=1.2)
    d.circle(x + 20, y + 20, 11, fill=col)
    d.text(x + 20, y + 20.5, str(n), size=11.5, family="mono", weight=700, fill=T.bg, anchor="middle")
    d.text(x + 38, y + 20, title, size=12.5, family="mono", weight=600, fill=T.fg)
    d.text(x + 16, y + h - 34, sub[0], size=S.small, fill=T.fg2)
    if len(sub) > 1:
        d.text(x + 16, y + h - 16, sub[1], size=S.small, fill=T.muted)


# --------------------------------------------------------------------------------------
# 63 — class family
# --------------------------------------------------------------------------------------

@figure("63_event_dag_classes", "ScheduleEventDag and the DagBase family", DOC1)
def event_dag_classes():
    d = Doc("63_event_dag_classes", "ScheduleEventDag and the DagBase family",
            "ScheduleEventDag specialises the generic DagBase<T> for events. The scheduler uses three DagBase "
            "instantiations.")
    M = 11.5
    base = uml_class(d, 0, 0, "DagBase<T>", accent=T.violet,
                     stereo="class template · planner_core/event_dag.hpp", size=M,
                     attrs=["# dag_: adjacency_list<vecS, vecS, bidirectionalS,", "        shared_ptr<T>>",
                            "# ptr_to_vertex_: unordered_map<shared_ptr<T>, Vertex>",
                            "  Vertex = vertex_descriptor (size_t, 0..n-1)"],
                     methods=["+ Add(ptr): optional<Vertex>  // nullopt if present",
                              "+ AddDependency(parent, child): bool  // no cycle check",
                              "+ AddDependent(child, parent): bool",
                              "+ Has(ptr), HasVertex(v), HasDependency(p, c): bool",
                              "+ GetVertex(ptr), GetFromVertex(v): optional<...>",
                              "+ GetInEdges(v), GetOutEdges(v)  // throw if absent",
                              "+ GetSourceVertex(e), GetTargetVertex(e), GetVertices()",
                              "+ GetParents(x), GetChildren(x)",
                              "+ GetRootVertices(), GetLeafVertices()",
                              "+ WouldCreateCycle(parent, child): bool  // BFS",
                              "+ GetTopologicalOrdering()  virtual  // Boost DFS",
                              "+ Reduce(): BoolStringPair", "+ Remove(ptr), RemoveVertex(v)  // renumbers",
                              "+ Replace(old, new): bool", "+ NumVertices(), NumEdges()",
                              "+ PrintGraph(label, logger), DrawGraph(name)"])
    sub = uml_class(d, 0, base.y1 + 90, "ScheduleEventDag", accent=T.amber,
                    stereo="planner_core · DagBase<ScheduleEvent> + 8 methods", size=M,
                    attrs=["  VertexVec = std::vector<Vertex>"],
                    methods=["+ AddEvent(e): bool", "+ HasEvent(e): bool",
                             "+ GetEventFromVertex(v): optional<ScheduleEventSPtr>",
                             "+ GetVertexFromEvent(e): optional<Vertex>",
                             "+ GetRootEvents(): vector  // sorted by job index",
                             "+ GetLeafEvents(): vector  // vertex order",
                             "+ GetTopologicalOrdering()  override",
                             "    // Kahn, lowest job index first",
                             "+ Apply(DiscreteGarageState&) const: BoolStringPair"])
    # inheritance (hollow triangle at base)
    connect(d, [(sub.cx, sub.y0), (sub.cx, base.y1)], kind="inh", color=T.amber, label="T = ScheduleEvent",
            label_at=(sub.cx, (sub.y0 + base.y1) / 2))
    # instances column
    ix = max(base.x1, sub.x1) + 110
    inst = [
        ("ctx->events", "ScheduleEventDag", T.amber,
         ["the plan: built in job expansion,", "extended by tray and AGV assignment,", "read by CHUGG and the response"]),
        ("event_dag_copy", "ScheduleEventDag", T.amber,
         ["local in DoAgvAssignments: a shallow", "copy consumed root by root (Remove)", "as a work queue (see below)"]),
        ("agv_event_dag", "DagBase<uint16_t>", T.violet,
         ["local in DoAgvAssignments (GetEventDag):", "which matched AGV must go first", "within one matching round"]),
        ("final_actions_dag", "DagBase<ActionNodeMsg>", T.violet,
         ["local in ResponseFromTrajectories:", "one vertex per action node; becomes", "the response's parent indices"]),
    ]
    y = 0
    boxes = []
    for nm, ty, col, lines in inst:
        w = 330
        h = 30 + 18 * len(lines) + 12
        d.rect(ix, y, w, h, rx=8, fill=T.card, stroke=col, sw=1.4)
        d.rich(ix + 14, y + 17, [(nm, "mono", 700, T.fg), (" : " + ty, "mono", 400, col)], size=12)
        for i, ln in enumerate(lines):
            d.text(ix + 14, y + 40 + i * 18, ln, size=S.small, fill=T.fg2)
        boxes.append((BBox(ix, y, ix + w, y + h), col))
        y += h + 22
    # dependency lines from instances to their class
    for (b, col), tgt in zip(boxes, [sub, sub, base, base]):
        mx = ix - 50
        connect(d, [(b.x0, b.cy), (mx, b.cy), (mx, tgt.y0 + 30 if tgt is sub else tgt.y0 + 60),
                    (tgt.x1, tgt.y0 + 30 if tgt is sub else tgt.y0 + 60)], kind="dep", color=col)
    label_pill(d, ix - 50, (boxes[1][0].y1 + boxes[2][0].y0) / 2, "«instance of»", color=T.muted)
    note(d, ix, y + 6, 330,
         "DagBase<T> is header-only. ScheduleEventDag's Apply, GetRootEvents, GetLeafEvents and "
         "GetTopologicalOrdering are in src/event_dag.cpp; the other four are one-line wrappers in the header.",
         title="Where the code is", accent=T.violet)
    frame(d, title="ScheduleEventDag and the DagBase family",
          subtitle="One generic graph class, three element types. ScheduleEventDag adds the event-specific helpers "
                   "and replaces the topological sort with one that puts lower job indices first.",
          badge_key="as-built",
          legend=[("box", T.violet, "generic DagBase<T> / its other instances"), ("box", T.amber, "ScheduleEventDag"),
                  ("inh", T.amber, "specialises"), ("dep", T.fg2, "instance of")])
    return d


# --------------------------------------------------------------------------------------
# 64 — storage and the three names of an event
# --------------------------------------------------------------------------------------

@figure("64_event_dag_storage", "ScheduleEventDag storage and event identity", DOC1)
def event_dag_storage():
    d = Doc("64_event_dag_storage", "Inside ctx->events: vertices, edges and shared event objects",
            "The DAG stores a vertex per event holding a shared_ptr, and directed edges between vertex indices. "
            "Other structures point at the same event objects.")
    # ---- vertex table ----
    d.text(0, 0, "dag_: vertices", size=13, weight=600, fill=T.fg)
    d.text(0, 18, "index = insertion order (vecS)", size=S.small, fill=T.muted)
    rows_y = {}
    for i, k in enumerate(ORDER):
        y = 40 + i * 44
        d.rect(0, y, 190, 34, rx=6, fill=T.card, stroke=T.border_soft, sw=1)
        d.text(12, y + 17, f"v{i}", size=12.5, family="mono", weight=700, fill=T.amber)
        d.text(52, y + 17, "shared_ptr ->", size=11.5, family="mono", fill=T.fg2)
        d.circle(176, y + 17, 4, fill=T.fg2)
        rows_y[k] = y + 17
    # ---- event objects ----
    ex = 330
    d.text(ex, 0, "event objects (heap)", size=13, weight=600, fill=T.fg)
    d.text(ex, 18, "one object per event, shared by every holder", size=S.small, fill=T.muted)
    ev_y = {}
    for i, k in enumerate(ORDER):
        kind, text, job, _ = EV[k]
        col = EVENT_COLOR[kind]
        y = 40 + i * 44
        d.rect(ex, y, 260, 34, rx=7, fill=T.card, stroke=col, sw=1.4)
        d.text(ex + 12, y + 11, f"{kind} · job_index {job}", size=10, family="mono", weight=600, fill=col)
        d.text(ex + 12, y + 25, f"{k}: {text}", size=11.5, family="mono", fill=T.fg)
        ev_y[k] = y + 17
        connect(d, [(180, rows_y[k]), (ex, ev_y[k])], kind="flow", color=T.fg2, size=7, sw=1.2)
    # ---- edge list ----
    lx = ex + 260 + 70
    d.text(lx, 0, "dag_: edges (u -> v: u finishes first)", size=13, weight=600, fill=T.fg)
    d.text(lx, 18, "stored between vertex indices", size=S.small, fill=T.muted)
    for i, (u, v) in enumerate(EDG):
        y = 40 + i * 32
        d.rect(lx, y, 210, 26, rx=6, fill=T.card, stroke=T.border_soft, sw=1)
        d.text(lx + 12, y + 13, f"(v{VIDX[u]}, v{VIDX[v]})", size=12, family="mono", weight=600, fill=T.fg)
        d.text(lx + 100, y + 13, f"{u} -> {v}", size=11.5, family="mono", fill=T.muted)
    # ---- other holders ----
    hx = lx
    hy = 40 + len(EDG) * 32 + 30
    d.text(hx, hy, "other holders of the same objects", size=13, weight=600, fill=T.fg)
    holders = [("ctx->last_entity_event[Tray 19]", "f", T.green),
               ("ctx->first_tray_event[21]", "b", T.green),
               ("event_dag_copy  (DoAgvAssignments)", "a", T.amber)]
    for i, (nm, k, col) in enumerate(holders):
        y = hy + 22 + i * 36
        b = chip(d, hx, y + 8, nm, col, size=11)
        connect(d, [(b.x0, y + 8), (b.x0 - 22, y + 8), (b.x0 - 22, ev_y[k]), (ex + 260, ev_y[k])], kind="flow",
                color=col, size=7, sw=1.2, dash="5 4")
    # ---- ptr_to_vertex_ map ----
    py = 40 + 6 * 44 + 26
    d.text(0, py, "ptr_to_vertex_: the reverse map", size=13, weight=600, fill=T.fg)
    d.text(0, py + 18, "unordered_map<shared_ptr<ScheduleEvent>, Vertex>", size=S.small, family="mono", fill=T.muted)
    for i, k in enumerate(ORDER):
        x = (i % 3) * 100
        y = py + 34 + (i // 3) * 32
        d.rect(x, y, 92, 26, rx=6, fill=T.card, stroke=T.tint(T.sky, 0.6, T.bg), sw=1)
        d.text(x + 46, y + 13, f"&{k} -> v{i}", size=11.5, family="mono", fill=T.fg, anchor="middle")
    d.text(0, py + 112, "kept in sync by Add / Remove / Replace;", size=S.small, fill=T.fg2)
    d.text(0, py + 130, "Add(ptr) refuses a pointer already present", size=S.small, fill=T.fg2)
    top_bottom = max(py + 140, hy + 22 + 3 * 36)

    # ---- three names of one event ----
    y0 = top_bottom + 40
    d.text(0, y0, "One event, three names, and how to convert between them", size=13, weight=600, fill=T.fg)
    cards = [
        ("ScheduleEventSPtr", "identity: the object itself", ["keys of the bookkeeping maps", "AddDependency(a, b)",
                                                             "WouldCreateCycle(a, b)", "Remove(e) on a copy"], T.sky),
        ("Vertex (size_t)", "position in this DAG", ["GetTopologicalOrdering() result", "edge.m_source / m_target",
                                                        "CHUGG motion.GetActionId()", "changes if a vertex is removed"],
         T.amber),
        ("job_index (unsigned int)", "a field of the event", ["event->GetJobIndex()", "scheduled_jobs[k]",
                                                       "rule B: leaves of the same job", "shared by a whole job"],
         T.green),
    ]
    cw = 290
    gap = 200
    cbs = []
    for i, (t1, t2, lines, col) in enumerate(cards):
        x = i * (cw + gap)
        h = 46 + 19 * len(lines) + 10
        d.rect(x, y0 + 24, cw, h, rx=9, fill=T.card, stroke=col, sw=1.5)
        d.text(x + 14, y0 + 42, t1, size=13, family="mono", weight=700, fill=col)
        d.text(x + 14, y0 + 60, t2, size=S.small, fill=T.muted)
        for j, ln in enumerate(lines):
            d.text(x + 24, y0 + 84 + j * 19, ln, size=11.5, family="mono", fill=T.fg2)
            d.circle(x + 15, y0 + 84 + j * 19, 2.3, fill=col)
        cbs.append(BBox(x, y0 + 24, x + cw, y0 + 24 + h))
    a, b, c = cbs
    connect(d, [(a.x1, a.y0 + 34), (b.x0, b.y0 + 34)], kind="flow", color=T.fg2, size=7,
            label="GetVertexFromEvent(e)", label_at=((a.x1 + b.x0) / 2, a.y0 + 20))
    d.text((a.x1 + b.x0) / 2, a.y0 + 50, "hash lookup in ptr_to_vertex_", size=10.5, fill=T.muted, anchor="middle")
    connect(d, [(b.x0, b.y0 + 74), (a.x1, a.y0 + 74)], kind="flow", color=T.fg2, size=7,
            label="GetEventFromVertex(v)", label_at=((a.x1 + b.x0) / 2, a.y0 + 92))
    d.text((a.x1 + b.x0) / 2, a.y0 + 112, "index into dag_", size=10.5, fill=T.muted, anchor="middle")
    yb = a.y1 + 30
    connect(d, [(a.cx, a.y1), (a.cx, yb), (c.cx, yb), (c.cx, c.y1)], kind="flow", color=T.fg2, size=7,
            label="event->GetJobIndex()", label_at=((a.cx + c.cx) / 2, yb))
    d.text(b.x1 + 14, b.y0 + 54, "no index -> event lookup:", size=S.small, fill=T.muted)
    d.text(b.x1 + 14, b.y0 + 72, "many events share one job", size=S.small, fill=T.muted)
    frame(d, title="Inside ctx->events: vertices, edges and shared event objects",
          subtitle="The example is the DAG of the topological-ordering figure (job 0 = a retrieve, jobs 1 and 2 repark T19). "
                   "dag_ and ptr_to_vertex_ are DagBase's two members; the holders on the right are illustrative.",
          badge_key="as-built",
          legend=[("box", T.sky, "shared_ptr identity"), ("box", T.amber, "vertex index"),
                  ("box", T.green, "job index / bookkeeping maps"), ("dasharrow", T.green, "another pointer to the same object")],
          footnote="From planner_core/event_dag.hpp. PlanMotions maps each motion back to its event with "
                   "static_cast<ScheduleEventDag::Vertex>(motion.GetActionId()), which is why ctx->events must never "
                   "lose a vertex.")
    return d


# --------------------------------------------------------------------------------------
# 65 — operations on the example DAG
# --------------------------------------------------------------------------------------

@figure("65_event_dag_operations", "ScheduleEventDag operations", DOC1)
def event_dag_operations():
    d = Doc("65_event_dag_operations", "What each ScheduleEventDag operation does",
            "Eight panels apply one operation each to the example DAG of the topological-ordering figure and show the result.")
    PW, PH, GAP = 330, 250, 22
    dx, dy = 22, 72

    def at(i):
        return (i % 4) * (PW + GAP), (i // 4) * (PH + GAP)

    # 1 AddEvent
    x, y = at(0)
    _panel(d, x, y, PW, PH, 1, "AddEvent(g)", ["adds vertex v6, no edges yet", "rules A/B/C then add its edges"])
    _mini_dag(d, x + dx, y + dy, nodes=ORDER + ["g"], states={"g": "new"}, extra_nodes={"g": (3, 1)})
    # 2 AddDependency
    x, y = at(1)
    _panel(d, x, y, PW, PH, 2, "AddDependency(d, g)", ["edge d -> g: g waits for d", "false if d or g missing, or edge exists"])
    _mini_dag(d, x + dx, y + dy, nodes=ORDER + ["g"], edges=EDG + [("d", "g")], states={"g": "new"},
              edge_styles={("d", "g"): "new"}, extra_nodes={"g": (3, 1)})
    # 3 roots / leaves
    x, y = at(2)
    _panel(d, x, y, PW, PH, 3, "GetRootEvents()", ["roots = no in-edge, by job index: {a, e}", "GetLeafEvents() = no out-edge: {d, f}"],
           col=T.green)
    _mini_dag(d, x + dx, y + dy, states={"a": "hi", "e": "hi"})
    # 4 topological ordering
    x, y = at(3)
    _panel(d, x, y, PW, PH, 4, "GetTopologicalOrdering()", ["optional<VertexVec>: lowest job index first",
                                                           "empty optional if there is a cycle"], col=T.green)
    for i, k in enumerate(["a", "b", "c", "d", "e", "f"]):
        _node(d, x + 18 + i * 50, y + 82, k, w=42)
        d.text(x + 39 + i * 50, y + 128, f"v{VIDX[k]}", size=10.5, family="mono", fill=T.muted, anchor="middle")
    d.text(x + 18, y + 156, "returns vertex indices, not events;", size=S.small, fill=T.fg2)
    d.text(x + 18, y + 174, "map back with GetEventFromVertex(v)", size=S.small, fill=T.fg2)
    # 5 Apply
    x, y = at(4)
    _panel(d, x, y, PW, PH, 5, "Apply(working_state)", ["replays every event, in a topological order,",
                                                        "onto a COPY of initial_state; returns BoolStringPair"],
           col=T.violet)
    lines = ["working_state = ctx->initial_state;", "ctx->events.Apply(working_state);", "",
             "a  B21 -> TO_RETRIEVE", "b  T21 leaves B21 (dest ?)", "c  T17 -> B21", "d  B21 PROCESS_RETRIEVE",
             "e, f  T19 -> P24 -> P23"]
    for i, ln in enumerate(lines):
        d.text(x + 18, y + 54 + i * 17, ln, size=11, family="mono", fill=T.fg2 if i > 2 else T.fg)
    # 6 WouldCreateCycle
    x, y = at(5)
    _panel(d, x, y, PW, PH, 6, "WouldCreateCycle(d, a)", ["true: a already reaches d, so d -> a would",
                                                          "close a loop; callers then skip the edge"], col=T.red)
    _mini_dag(d, x + dx, y + dy, states={"a": "hi", "d": "hi"})
    bx0 = x + dx + 3 * 74 + 25
    connect(d, [(bx0, y + dy + 30), (bx0, y + dy + 46), (x + dx + 25, y + dy + 46), (x + dx + 25, y + dy + 30)],
            kind="flow", color=T.red, dash="4 3", size=7)
    label_pill(d, x + dx + 1.5 * 74 + 25, y + dy + 46, "d -> a ?", color=T.red)
    # 7 Reduce
    x, y = at(6)
    _panel(d, x, y, PW, PH, 7, "Reduce()", ["drops a -> c and a -> d: implied by a -> b -> c -> d",
                                            "HasDependency(a, c): true before, false after"], col=T.amber)
    _mini_dag(d, x + dx, y + dy, edge_styles={("a", "c"): "gone", ("a", "d"): "gone"})
    # 8 Remove on a copy
    x, y = at(7)
    _panel(d, x, y, PW, PH, 8, "copy.Remove(a)", ["on event_dag_copy only: roots become {b, e};",
                                                  "ctx->events keeps a (and its vertex index)"], col=T.amber)
    boxes = _mini_dag(d, x + dx, y + dy, nodes=["b", "c", "d", "e", "f"], edges=[e for e in EDG if "a" not in e],
                      states={"b": "hi", "e": "hi"})
    _node(d, x + dx, y + dy, "a", state="gone")
    frame(d, title="What each ScheduleEventDag operation does",
          subtitle="Each panel starts from the same six-event DAG (job 0: a retrieve; jobs 1 and 2: T19 reparked twice) "
                   "and applies one operation. Green: what the call returns. Blue: what it adds. Red dashes: what it "
                   "removes or refuses.",
          badge_key="illustrative",
          legend=[("box", T.green, "returned / selected"), ("box", T.sky, "added"), ("dasharrow", T.red, "removed / refused"),
                  ("dashbox", T.faint, "removed vertex")],
          footnote="Behaviour from planner_core/event_dag.hpp and src/event_dag.cpp. AddDependency returns false if an "
                   "endpoint is missing or the edge exists, and never checks for cycles.")
    return d


# --------------------------------------------------------------------------------------
# 66 — the shallow copy as a work queue in DoAgvAssignments
# --------------------------------------------------------------------------------------

@figure("66_event_dag_copy_queue", "event_dag_copy as a work queue", DOC1)
def event_dag_copy_queue():
    d = Doc("66_event_dag_copy_queue", "DoAgvAssignments consumes a shallow copy of the DAG",
            "Rounds of DoAgvAssignments: the copy loses its roots one by one while ctx->events gains AGV events; "
            "both point at the same event objects.")
    # step k: (nodes left in the copy, roots highlighted, title, code line)
    S_ = [
        (ORDER, {"a", "e"}, "start", "auto event_dag_copy(ctx->events);"),
        (["b", "c", "d", "e", "f"], {"b", "e"}, "round 1 · phase 1", "apply + Remove the non-tray root a"),
        (["c", "d", "f"], {"c", "f"}, "round 1 · phase 2", "match AGVs to tray roots b, e; Remove them"),
        (["d"], {"d"}, "round 2 · phase 2", "match AGVs to tray roots c, f; Remove them"),
        ([], set(), "round 3 · phase 1", "apply + Remove d; the copy is empty"),
    ]
    d.step("Start: the copy has the same six events (the same objects) as ctx->events. Its roots, a and e, are the "
           "events with no unprocessed prerequisite.")
    d.step("Phase 1 drains the non-tray roots: the bay transition a is applied to working_state and removed from the "
           "copy. Removing a makes b a root. ctx->events is unchanged.")
    d.step("Phase 2 matches AGVs to the TrayMove roots b and e (BottleneckAssignment), calls SetAgvId on them and "
           "removes them from the copy. Their approach, lift and lower events are added to ctx->events only.")
    d.step("Round 2: no non-tray roots, so phase 2 matches c and f. Their AGV events go into ctx->events; d becomes "
           "the only root.")
    d.step("Round 3: d is applied and removed. The copy is empty and the loop ends; path repair, Reduce() and "
           "AddDepsAfterAmiga then run on ctx->events.")
    GX = 96
    # ---- left: the copy
    W1 = 470
    d.rect(0, 0, W1, 262, rx=10, fill=T.card, stroke=T.amber, sw=1.3)
    d.text(14, 18, "event_dag_copy (the work queue)", size=12.5, weight=600, fill=T.amber)
    for k, (nodes, roots, title, code) in enumerate(S_):
        with d.only(k):
            d.text(14, 40, f"{title}: {code}", size=11, family="mono", fill=T.fg2)
            states = {n: "hi" for n in roots}
            if nodes:
                _mini_dag(d, 30, 96, nodes=nodes, edges=[e for e in EDG if e[0] in nodes and e[1] in nodes],
                          states=states, gx=GX)
            for n in ORDER:
                if n not in nodes:
                    c, r = POS[n]
                    _node(d, 30 + c * GX, 96 + r * 58, n, state="gone")
            d.text(14, 230, "roots: " + (", ".join(sorted(roots)) if roots else "none (empty)"), size=S.small,
                   fill=T.fg)
    # ---- right: ctx->events
    X2 = W1 + 40
    W2 = 640
    d.rect(X2, 0, W2, 262, rx=10, fill=T.tint(T.sky, 0.05, T.bg), stroke=T.sky, sw=1.3)
    d.text(X2 + 14, 18, "ctx->events: never shrinks, keeps every vertex index", size=12.5, weight=600, fill=T.sky)
    _mini_dag(d, X2 + 30, 76, gx=GX)
    agv = {"b": ("AGV-1", 2), "e": ("AGV-2", 2), "c": ("AGV-1", 3), "f": ("AGV-3", 3)}
    for n, (who, k) in agv.items():
        c, r = POS[n]
        with d.at(k):
            d.text(X2 + 30 + c * GX + 25, 76 + r * 58 + 40, who, size=10.5, family="mono", weight=600, fill=T.green,
                   anchor="middle")
    rows = [("b, e", "approach, lift, lower for b (AGV-1) and e (AGV-2), with edges", 2),
            ("c, f", "approach, lift, lower for c (AGV-1) and f (AGV-3), with edges", 3),
            ("then", "EnsureAgvMovePathsClear, Reduce(), AddDepsAfterAmiga", 4)]
    d.text(X2 + 14, 204, "added AGV events:", size=S.small, weight=600, fill=T.fg2)
    for i, (who, txt, k) in enumerate(rows):
        with d.at(k):
            d.text(X2 + 130, 204 + i * 20, f"{who}: {txt}", size=S.small, fill=T.fg)
    with d.at(0, 1):
        d.text(X2 + 130, 204, "none yet", size=S.small, fill=T.muted)
    d.text(0, 292, "Every SetAgvId(...) on a root of the copy is visible in ctx->events: both DAGs hold the same TrayMove "
           "objects. New AGV events are added only to ctx->events, so they never become roots of the copy.",
           size=S.small, fill=T.muted)
    frame(d, title="DoAgvAssignments consumes a shallow copy of the DAG",
          subtitle="The copy is a work queue (Kahn's algorithm in rounds): its roots are the events whose "
                   "prerequisites are all assigned. Phase 1 drains non-tray roots, phase 2 matches AGVs to the "
                   "TrayMove roots with BottleneckAssignment.",
          badge_key="illustrative",
          legend=[("box", T.green, "roots of the copy at this step"), ("dashbox", T.faint, "already removed from the copy"),
                  ("box", T.sky, "ctx->events")],
          footnote="AGV numbers are illustrative; the matching depends on costs. In the code, unmatched TrayMove roots "
                   "stay in the copy for the next round.")
    return d


# --------------------------------------------------------------------------------------
# 67 — TrayMove::Apply branch by branch
# --------------------------------------------------------------------------------------

def _box(d: Doc, x, y, w, lines, col, *, title=None, dashed=False, h=None):
    lh = 17
    hh = h or (16 + (22 if title else 0) + lh * len(lines))
    d.rect(x, y, w, hh, rx=9, fill=T.card, stroke=col, sw=1.5, dash="5 4" if dashed else None)
    yy = y + 18
    if title:
        d.text(x + 14, yy, title, size=12.5, family="mono", weight=700, fill=col)
        yy += 22
    for ln in lines:
        d.text(x + 14, yy, ln, size=11.5, fill=T.fg2)
        yy += lh
    return BBox(x, y, x + w, y + hh)


@figure("67_traymove_apply", "What TrayMove::Apply does", DOC1)
def traymove_apply():
    d = Doc("67_traymove_apply", "What TrayMove::Apply does to a DiscreteGarageState",
            "Flowchart of TrayMove::Apply: blank tray id, blank destination, occupied destination, no AGV, and "
            "AGV-carried cases.")
    QW, OW, GX = 300, 430, 110
    ox = QW + GX
    start = _box(d, 0, 0, QW, ["const: changes only `state`"], T.sky, title="TrayMove::Apply(state)")
    qs = [
        ("tray id set?", "no", ["return {true, \"\"}: nothing changes", "(the bay a READY_FOR_INSERT fills",
                                 "still looks empty to later jobs)"], T.amber, "no-op"),
        ("destination set?", "no", ["remove the tray's payload (if any),", "then the tray itself, from `state`",
                                     "(TODO in the code: park it at {node_id: 0, heading: 0})"], T.red, "tray disappears"),
        ("another tray on the destination node?", "yes", ["move that tray to the placeholder pose {node_id: 0, heading: 0},",
                                                           "then continue below"], T.sky, "occupant evicted"),
        ("AGV id set?", "no", ["TrayPoseChanged (TrayPoseSetManually): the tray jumps to", "dest (node and heading); no AGV moves"],
         T.green, "teleport"),
        ("AGV at tray pose (same axis), lifted,\nand carrying this tray?", "no",
         ["return {false, \"Tray move has assigned AGV", "but ...\"}: replay stops here"], T.red, "fail"),
    ]
    y = start.y1 + 40
    prev = start
    qboxes = []
    for i, (q, branch, out, col, tag) in enumerate(qs):
        lines = q.split("\n")
        qb = _box(d, 0, y, QW, lines, T.fg2, h=24 + 17 * len(lines))
        connect(d, [(prev.cx if prev is start else 60, prev.y1), (60, prev.y1 + 10) if prev is not start else
                    (prev.cx, prev.y1 + 10), (60, qb.y0)] if False else [(60, prev.y1), (60, qb.y0)],
                kind="flow", color=T.fg2, size=8)
        ob = _box(d, ox, y - 4, OW, out, col, title=tag)
        connect(d, [(qb.x1, qb.cy), (ob.x0, qb.cy)], kind="flow", color=col, size=8,
                label=branch, label_at=((qb.x1 + ob.x0) / 2, qb.cy - 12))
        other = "no" if branch == "yes" else "yes"
        label_pill(d, 92, qb.y1 + 14, other, color=T.fg2)
        if branch == "yes":
            # occupied-destination branch rejoins the main column
            connect(d, [(ob.cx, ob.y1), (ob.cx, ob.y1 + 16), (120, ob.y1 + 16), (120, qb.y1 + 30)], kind="flow",
                    color=T.sky, size=7, dash="5 4")
        qboxes.append(qb)
        prev = qb
        y = max(qb.y1, ob.y1) + 48
    end = _box(d, 0, y, QW + GX + OW, ["AgvPoseChanged: the AGV (and the tray it carries) moves to dest; the AGV's "
                                        "heading is Wrap(dest + 180) if it faces opposite to the tray"], T.green,
               title="carried by the AGV")
    connect(d, [(60, prev.y1), (60, end.y0)], kind="flow", color=T.fg2, size=8)
    frame(d, title="What TrayMove::Apply does to a DiscreteGarageState",
          subtitle="planner_core/src/schedule_events.cpp. Job methods replay half-specified TrayMoves through this "
                   "function, so the blank-field branches decide what later jobs see in working_state.",
          badge_key="as-built",
          legend=[("box", T.fg2, "question"), ("box", T.green, "tray moves"), ("box", T.amber, "nothing happens"),
                  ("box", T.sky, "side effect, then continue"), ("box", T.red, "tray removed / replay fails")])
    return d


# --------------------------------------------------------------------------------------
# 68 — the job-index priority topological sort
# --------------------------------------------------------------------------------------

@figure("68_topological_priority", "How ScheduleEventDag orders events", DOC1)
def topological_priority():
    d = Doc("68_topological_priority", "How ScheduleEventDag::GetTopologicalOrdering picks the next event",
            "Kahn's algorithm with a min-priority queue on job index, step by step on the example DAG, compared with "
            "the Boost DFS order DagBase would give.")
    d.text(0, 0, "Example DAG (job index: a, b, c, d = 0; e = 1; f = 2)", size=13, weight=600, fill=T.fg)
    steps = [("a:0  e:1", "a", "a"), ("b:0  e:1", "b", "a b"), ("c:0  e:1", "c", "a b c"),
             ("d:0  e:1", "d", "a b c d"), ("e:1", "e", "a b c d e"), ("f:2", "f", "a b c d e f")]
    # ---- animation: step 0 = the start, step i = the i-th pop from the heap
    d.step("Start: count each event's incoming edges. a and e have none, so both go on the min-heap, keyed by "
           "job index: a (job 0), e (job 1).")
    why = {"a": "a has the lowest job index (0) of the ready events. Popping it removes a -> b and a -> c; "
                "b now has no incoming edge and joins the heap.",
           "b": "b (job 0) beats e (job 1). Its edge b -> c goes, so c becomes ready.",
           "c": "c (job 0) beats e (job 1). Removing c -> d makes d ready.",
           "d": "d (job 0) is still ahead of e: job 0 finishes first wherever the edges allow.",
           "e": "Only e is ready. Popping it makes f ready.",
           "f": "f is last. Six events were popped, as many as the DAG has, so there is no cycle and the order is returned."}
    for i, (_, take, _) in enumerate(steps):
        d.step(f"Pop {take}. " + why[take])
    ready_at = [{"a", "e"}, {"b", "e"}, {"c", "e"}, {"d", "e"}, {"e"}, {"f"}, set()]
    for k in range(len(steps) + 1):
        done = set(steps[k - 1][2].split()) if k else set()
        cur = steps[k - 1][1] if k else None
        states = {}
        for n in "abcdef":
            if n == cur:
                states[n] = "hi"
            elif n in done:
                states[n] = "gone"
            elif n in ready_at[k]:
                states[n] = "new"
        with d.only(k):
            _mini_dag(d, 10, 40, states=states)
    d.text(0, 196, "green = popped now   blue = ready (on the heap)   dashed = already in the order", size=S.small,
           fill=T.muted)
    # steps table
    tx = 380
    d.text(tx, 0, "ScheduleEventDag: take the ready event with the lowest job index", size=13, weight=600, fill=T.fg)
    hx = [tx, tx + 50, tx + 210, tx + 270]
    for x, h in zip(hx, ["step", "ready  (event:job)", "take", "order so far"]):
        d.text(x, 30, h, size=10.5, family="mono", weight=600, fill=T.muted)
    yy = 52
    for i, (rdy, take, so) in enumerate(steps):
        if i % 2 == 0:
            d.rect(tx - 6, yy - 12, 520, 24, rx=5, fill=T.tint(T.card, 0.55, T.bg), layer="under")
        with d.only(i + 1):
            d.rect(tx - 6, yy - 12, 520, 24, rx=5, fill=T.tint(T.green, 0.16, T.bg), stroke=T.green, sw=1.2,
                   layer="under")
        with d.at(i + 1):
            d.text(hx[0], yy, str(i + 1), size=11.5, family="mono", fill=T.fg2)
            d.text(hx[1], yy, rdy, size=11.5, family="mono", fill=T.fg)
            d.text(hx[2], yy, take, size=11.5, family="mono", weight=700, fill=T.green)
            d.text(hx[3], yy, so, size=11.5, family="mono", fill=T.fg2)
        yy += 26
    # comparison
    cy = max(yy, 200) + 30
    d.text(0, cy, "Same DAG, two implementations", size=13, weight=600, fill=T.fg)
    rows = [("ScheduleEventDag::GetTopologicalOrdering()", "a b c d e f", T.green,
             "Kahn + min-heap on job index: job 0 first wherever the edges allow"),
            ("DagBase<T>::GetTopologicalOrdering()", "e f a b c d", T.violet,
             "Boost topological_sort (DFS from vertex 0 upward), reversed: valid, but ignores jobs")]
    for i, (nm, order, col, why) in enumerate(rows):
        y = cy + 26 + i * 56
        d.rect(0, y, 900, 46, rx=8, fill=T.card, stroke=col, sw=1.4)
        d.text(14, y + 15, nm, size=12, family="mono", weight=700, fill=col)
        d.text(14, y + 33, why, size=S.small, fill=T.fg2)
        d.text(886, y + 23, order, size=14, family="mono", weight=700, fill=T.fg, anchor="end")
    note(d, 0, cy + 26 + 2 * 56 + 14, 900,
         "Only the job index is compared, so among ready events of the same job the heap's internal order decides. "
         "That order is deterministic for a DAG built the same way, but it is not 'vertex order'. Reduce() calls the "
         "virtual GetTopologicalOrdering, so on a ScheduleEventDag it also uses the job-priority order.",
         title="Ties within one job", accent=T.sky)
    frame(d, title="How ScheduleEventDag::GetTopologicalOrdering picks the next event",
          subtitle="planner_core/src/event_dag.cpp overrides the Boost sort so that earlier jobs come first. "
                   "If some events never become ready (a cycle), the count falls short and the method returns nullopt.",
          badge_key="as-built",
          legend=[("box", T.green, "ScheduleEventDag order"), ("box", T.violet, "generic DagBase order")])
    return d
