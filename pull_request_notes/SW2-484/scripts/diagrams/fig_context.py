"""ScheduleContext figures for doc 01: anatomy (fields, groups, related types) and lifecycle
(which Plan() stage creates, reads or writes each field)."""
from __future__ import annotations

from components import chip, connect, frame, label_pill, note, uml_class
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S

DOC1 = "01-software-background.md"

ID, INP, PLAN, BOOK = T.fg2, T.violet, T.amber, T.green

GROUPS = [
    ("identity", ID, "who and when", [
        ("request_id", "GuidMsg", "stored; not read in scheduler.cpp"),
        ("request_id_str", "std::string", "names the debug DAG dumps"),
        ("start_time", "Interval::Timepoint", "t = 0 for PlanMotions"),
    ]),
    ("fixed inputs", INP, "set at the start of Plan(), then only read", [
        ("initial_state", "DiscreteGarageState", "the garage at request time; base of every replay"),
        ("disabledness_filters", "CollistionFilterMap", "unusable vertices, per footprint type"),
    ]),
    ("the plan being built", PLAN, "grows stage by stage", [
        ("events", "ScheduleEventDag", "every stage adds events and edges"),
        ("scheduled_jobs", "vector<ScheduledJobDataMsg>", "entry k = the job with job_index k"),
    ]),
    ("bookkeeping", BOOK, "links between events, consumed later", [
        ("last_entity_event", "GarageEntityEventMap", "rules A and C; job expansion only"),
        ("first_tray_event", "unordered_map<uint16_t, ScheduleEventSPtr>", "tray assignment -> AGV assignment"),
    ]),
]

METHODS = [
    ("ScheduleContext(reqid, initial_state, now)", "sets the identity fields and initial_state"),
    ("PushBackScheduledJob(job)", "appends a ScheduledJobDataMsg for a job that planned"),
    ("UpdateLastEntityEvent(entity, event)", "rule A: edge last[entity] -> event, then last[entity] = event"),
    ("UpdateLeafDependencies(event, job_index)", "rule B: edge from every leaf of the same job"),
]


@figure("61_schedule_context_anatomy", "ScheduleContext anatomy", DOC1)
def schedule_context_anatomy():
    d = Doc("61_schedule_context_anatomy", "ScheduleContext: fields, groups and related types",
            "One object per Plan() call. Nine public fields in four groups, three helper methods, and the types "
            "its fields hold.")
    # ---- left: who holds the pointer ----
    lw = 290
    d.rect(0, 0, lw, 330, rx=10, fill=T.card, stroke=T.sky, sw=1.5)
    d.text(16, 20, "Plan()", size=14, family="mono", weight=700, fill=T.sky)
    d.text(16, 42, "plan_ctx : ScheduleContextSPtr", size=11.5, family="mono", fill=T.fg)
    d.text(16, 60, "= std::make_shared<ScheduleContext>(...)", size=10.5, family="mono", fill=T.muted)
    d.text(16, 92, "the same pointer is passed to:", size=S.small, fill=T.muted)
    for i, nm in enumerate(["Plan<Type>Job(ctx, ...)  x12", "DoTrayAssignments(ctx)", "DoAgvAssignments(ctx)",
                            "SanityCheckEvents(ctx)", "PlanMotions(ctx)", "ResponseFromTrajectories(ctx, ...)"]):
        d.text(28, 116 + i * 24, nm, size=11.5, family="mono", fill=T.fg2)
        d.circle(19, 116 + i * 24, 2.5, fill=T.sky)
    d.text(16, 270, "freed when Plan() returns", size=S.small, fill=T.muted)
    d.text(16, 290, "(last shared_ptr goes away)", size=S.small, fill=T.muted)
    left = BBox(0, 0, lw, 330)

    # ---- centre: the class ----
    x0 = lw + 70
    W = 560
    y = 0
    head = 44
    rows = []
    yy = head + 6
    for gname, gcol, gsub, fields in GROUPS:
        rows.append(("group", yy, gname, gcol, gsub))
        yy += 30
        for f in fields:
            rows.append(("field", yy, f, gcol))
            yy += 40
        yy += 6
    mstart = yy + 8
    yy = mstart + 30
    for m in METHODS:
        rows.append(("method", yy, m))
        yy += 40
    H = yy + 6
    d.rect(x0, y, W, H, rx=8, fill=T.card, stroke=T.sky, sw=1.6)
    d.path(f"M{x0} {head} L{x0} 8 Q{x0} 0 {x0 + 8} 0 L{x0 + W - 8} 0 Q{x0 + W} 0 {x0 + W} 8 L{x0 + W} {head} Z",
           fill=T.tint(T.sky, 0.16))
    d.text(x0 + W / 2, 13, "«class · include/scheduler/scheduler.hpp · all members public»", size=S.tiny,
           fill=T.muted, anchor="middle")
    d.text(x0 + W / 2, 31, "ScheduleContext", size=S.h, family="mono", weight=700, fill=T.sky, anchor="middle")
    field_y = {}
    for r in rows:
        if r[0] == "group":
            _, gy, gname, gcol, gsub = r
            d.rect(x0 + 1, gy, W - 2, 26, fill=T.tint(gcol, 0.12, T.card))
            d.text(x0 + 14, gy + 13, gname, size=12, weight=600, fill=gcol)
            d.text(x0 + 24 + text_width(gname, 12, "sans", 600), gy + 13, gsub, size=S.small, fill=T.muted)
        elif r[0] == "field":
            _, fy, (nm, ty, what), gcol = r
            d.rich(x0 + 14, fy + 10, [("+ ", "mono", 600, gcol), (nm, "mono", 600, T.fg), (": " + ty, "mono", 400, T.muted)],
                   size=12)
            d.text(x0 + 30, fy + 28, what, size=S.small, fill=T.fg2)
            field_y[nm] = fy + 10
        else:
            _, my, (sig, what) = r
            d.rich(x0 + 14, my + 10, [("+ ", "mono", 600, T.sky), (sig, "mono", 400, T.fg)], size=12)
            d.text(x0 + 30, my + 28, what, size=S.small, fill=T.fg2)
    d.line(x0, mstart, x0 + W, mstart, stroke=T.tint(T.sky, 0.45), sw=1)
    d.text(x0 + 14, mstart + 15, "methods", size=12, weight=600, fill=T.sky)
    ctx = BBox(x0, 0, x0 + W, H)
    connect(d, [(left.x1, 42), (ctx.x0, 42)], kind="assoc", color=T.sky, label="points to", label_at=((left.x1 + ctx.x0) / 2, 28))

    # ---- right: related types ----
    rx = ctx.x1 + 90
    M = 11.5
    dgs = uml_class(d, rx, field_y["initial_state"] - 40, "DiscreteGarageState", accent=INP,
                    stereo="value type · section 5", size=M,
                    attrs=["agvs, trays, payloads,", "bays, vecs, vrcs,", "disabled nodes"])
    dag = uml_class(d, rx, dgs.y1 + 30, "ScheduleEventDag", accent=PLAN, stereo="planner_core · section 12", size=M,
                    attrs=["vertices: shared_ptr<ScheduleEvent>", "edge u -> v: u finishes first"],
                    methods=["AddEvent, AddDependency", "GetTopologicalOrdering, Reduce"])
    sjd = uml_class(d, rx, dag.y1 + 30, "ScheduledJobDataMsg", accent=PLAN, stereo="ROS message · section 7", size=M,
                    attrs=["job: SchedulerJob", "node_indices: action positions", "bay_id, bay_arrival_node_guid"])
    ev = uml_class(d, rx, sjd.y1 + 30, "ScheduleEventSPtr", accent=BOOK, stereo="shared_ptr<ScheduleEvent>", size=M,
                   attrs=["the SAME object as in events", "(map value = pointer, not copy)"])
    for nm, box, off in (("initial_state", dgs, 45), ("events", dag, 40), ("scheduled_jobs", sjd, 64)):
        fy = field_y[nm]
        mx = ctx.x1 + off
        connect(d, [(ctx.x1, fy), (mx, fy), (mx, box.cy), (box.x0, box.cy)], kind="comp", color=T.fg2)
    for nm in ("last_entity_event", "first_tray_event"):
        fy = field_y[nm]
        mx = ctx.x1 + 18
        connect(d, [(ctx.x1, fy), (mx, fy), (mx, ev.cy), (ev.x0, ev.cy)], kind="assoc", color=BOOK)
    # job-index note
    note(d, 0, left.y1 + 30, lw,
         "Every event stores a job_index. scheduled_jobs[k] is the job whose events have GetJobIndex() == k; "
         "the response uses it to label each ActionNode with its job's guid.", title="How events find their job")
    note(d, 0, left.y1 + 190, lw,
         "Only Plan() and the methods it calls ever see the context. Nothing outlives the call except the "
         "PlanResponse built from it.", title="Scope")
    frame(d, title="ScheduleContext: fields, groups and related types",
          subtitle="Everything a single Plan() call knows and builds lives in this one object. Plan() creates it, "
                   "every later stage receives the same shared_ptr, and it is freed when Plan() returns.",
          badge_key="as-built",
          legend=[("box", ID, "identity"), ("box", INP, "fixed inputs"), ("box", PLAN, "the plan being built"),
                  ("box", BOOK, "bookkeeping maps"), ("comp", T.fg2, "holds by value"),
                  ("assoc", BOOK, "holds a pointer to")],
          footnote="CollistionFilterMap (sic) = unordered_map<CollisionEntityId_t, GraphFilterProperties>. "
                   "GarageEntityEventMap = unordered_map<GarageEntityIdMsg, ScheduleEventSPtr>.")
    return d


# --------------------------------------------------------------------------------------
# 62 — lifecycle matrix
# --------------------------------------------------------------------------------------

STAGES = [("construct", "make_shared"), ("filters", "GetDisabled-\nEntitiesFilters"),
          ("job\nexpansion", "Plan<Type>Job"), ("tray\nassignment", "DoTray-\nAssignments"),
          ("AGV\nassignment", "DoAgv-\nAssignments"), ("reduce +\nsanity", "Reduce,\nSanityCheckEvents"),
          ("motion\nplanning", "PlanMotions"), ("build\nresponse", "ResponseFrom-\nTrajectories"),
          ("fill\nresult", "end of Plan()")]

# codes: C created with a value, E created empty, R read, W write, RW both, D debug-only read, X rebuilt
LIFE = [
    ("request_id", ID, ["C", "", "", "", "", "", "", "", ""]),
    ("request_id_str", ID, ["C", "", "", "D", "D", "", "", "D", ""]),
    ("start_time", ID, ["C", "", "", "", "", "", "R", "", ""]),
    ("initial_state", INP, ["C", "R", "R", "R", "R", "R", "R", "R", ""]),
    ("disabledness_filters", INP, ["E", "W", "R", "", "", "R", "", "", ""]),
    ("events", PLAN, ["E", "", "RW", "RW", "RW", "RW", "R", "R", ""]),
    ("scheduled_jobs", PLAN, ["E", "", "W", "", "", "", "", "X", "R"]),
    ("last_entity_event", BOOK, ["E", "", "RW", "", "", "", "", "", ""]),
    ("first_tray_event", BOOK, ["E", "", "", "W", "R", "", "", "", ""]),
]

CODE = {"C": ("created", T.violet), "E": ("created empty", T.faint), "R": ("read", T.sky), "W": ("written", T.red),
        "RW": ("read + written", T.amber), "D": ("debug dumps only", T.muted), "X": ("rebuilt", T.pink)}


@figure("62_schedule_context_lifecycle", "ScheduleContext lifecycle", DOC1)
def schedule_context_lifecycle():
    d = Doc("62_schedule_context_lifecycle", "Which Plan() stage touches which ScheduleContext field",
            "Matrix: rows are the nine fields, columns are the Plan() stages in order; each cell says whether "
            "the stage creates, reads, writes or rebuilds that field.")
    name_w = 200
    cw = 104
    hy = 0
    for j, (st, fn) in enumerate(STAGES):
        cx = name_w + j * cw + cw / 2
        for k, ln in enumerate(st.split("\n")):
            d.text(cx, hy + 10 + k * 16, ln, size=12, weight=600, fill=T.fg, anchor="middle")
        for k, ln in enumerate(fn.split("\n")):
            d.text(cx, hy + 50 + k * 14, ln, size=10, family="mono", fill=T.muted, anchor="middle")
        d.text(cx, hy + 88, str(j + 1), size=10.5, family="mono", weight=600, fill=T.faint, anchor="middle")
    # arrow of time
    d.line(name_w + 10, hy + 102, name_w + len(STAGES) * cw - 10, hy + 102, stroke=T.border, sw=1.2)
    d.arrowhead((name_w + len(STAGES) * cw - 4, hy + 102), (name_w + 10, hy + 102), kind="filled", color=T.border,
                size=8)
    y0 = hy + 120
    rh = 40
    for i, (nm, col, cells) in enumerate(LIFE):
        y = y0 + i * rh
        if i % 2 == 0:
            d.rect(0, y, name_w + len(STAGES) * cw, rh, rx=4, fill=T.tint(T.card, 0.7, T.bg), layer="under")
        d.rect(0, y + 8, 4, rh - 16, rx=2, fill=col)
        d.text(14, y + rh / 2, nm, size=12, family="mono", weight=600, fill=T.fg)
        for j, c in enumerate(cells):
            if not c:
                continue
            cx = name_w + j * cw + cw / 2
            lab, ccol = CODE[c]
            chip(d, cx, y + rh / 2, c, ccol, size=11, anchor="middle")
    yb = y0 + len(LIFE) * rh
    for j in range(len(STAGES) + 1):
        x = name_w + j * cw
        d.line(x, y0 - 4, x, yb, stroke=T.border_soft, sw=0.8, layer="under")
    # callouts
    tot = name_w + len(STAGES) * cw
    nw = (tot - 2 * 20) / 3
    note(d, 0, yb + 28, nw,
         "last_entity_event is only maintained while jobs are expanded. Tray and AGV assignment add events "
         "without updating it, so after stage 3 it is stale.", title="Stale after job expansion")
    note(d, nw + 20, yb + 28, nw,
         "first_tray_event is empty until tray assignment fills it, and only AGV assignment reads it: it is "
         "the hand-off between those two stages.", title="A hand-off map")
    note(d, 2 * (nw + 20), yb + 28, nw,
         "BuildScheduledActionsArray fills node_indices and rebuilds scheduled_jobs from an unordered_map, so "
         "after stage 8 entry k no longer matches job_index k.", title="Reordered at the end")
    frame(d, title="Which Plan() stage touches which ScheduleContext field",
          subtitle="Stages left to right in the order Plan() runs them. Read along a row to see a field's life; read "
                   "down a column to see what a stage depends on and what it changes.",
          badge_key="as-built",
          legend=[("box", CODE[k][1], f"{k}  {CODE[k][0]}") for k in ("C", "E", "R", "W", "RW", "X", "D")],
          footnote="From scheduler.cpp: accesses through ctx-> / plan_ctx-> and the three helper methods, grouped by "
                   "the stage whose function contains them. Stage 6 reads disabledness_filters through "
                   "IsMovePossible, called by SanityCheckEvents.")
    return d
