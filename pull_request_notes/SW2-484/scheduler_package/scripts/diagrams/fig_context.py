"""ScheduleContext figures for doc 01: anatomy (fields, groups, related types) and lifecycle
(which Plan() stage creates, reads or writes each field)."""
from __future__ import annotations

from components import chip, connect, frame, label_pill, note, uml_class
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S

DOC1 = "01-software-background.html"

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
                    stereo="value type · DiscreteGarageState", size=M,
                    attrs=["agvs, trays, payloads,", "bays, vecs, vrcs,", "disabled nodes"])
    dag = uml_class(d, rx, dgs.y1 + 30, "ScheduleEventDag", accent=PLAN, stereo="planner_core · event DAG", size=M,
                    attrs=["vertices: shared_ptr<ScheduleEvent>", "edge u -> v: u finishes first"],
                    methods=["AddEvent, AddDependency", "GetTopologicalOrdering, Reduce"])
    sjd = uml_class(d, rx, dag.y1 + 30, "ScheduledJobDataMsg", accent=PLAN, stereo="ROS message", size=M,
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


# --------------------------------------------------------------------------------------
# 69 — scheduled_jobs through one Plan() call
# --------------------------------------------------------------------------------------

def _cells(d: Doc, x, y, items, *, w=40, h=26, gap=4):
    """Draw a vector as a row of cells. items: list of (text, color)."""
    if not items:
        d.text(x, y + h / 2, "[ ]", size=12, family="mono", fill=T.faint)
        return x + 24
    for txt, col in items:
        cw = max(w, text_width(txt, 11.5, "mono", 600) + 14)
        d.rect(x, y, cw, h, rx=5, fill=T.tint(col, 0.16, T.bg), stroke=T.tint(col, 0.7, T.bg), sw=1)
        d.text(x + cw / 2, y + h / 2, txt, size=11.5, family="mono", weight=600, fill=col, anchor="middle")
        x += cw + gap
    return x


@figure("69_scheduled_jobs", "scheduled_jobs through one Plan() call", DOC1)
def scheduled_jobs_flow():
    d = Doc("69_scheduled_jobs", "How scheduled_jobs is built, used and rebuilt",
            "Plan() routes each pending job either into plan_ctx->scheduled_jobs (planned) or straight into "
            "result.scheduled_jobs (failed); at the end the planned ones are labelled, rebuilt and appended to result.")
    OK, BAD, IDX = T.green, T.red, T.amber
    W = 1340
    # ---- the three objects involved ----
    objs = [
        ("request_data", "const PlanRequestMsg&  (Plan's parameter)", T.sky,
         ["pending_jobs: SchedulerJob[]   <- what to plan", "(also id, base_state, base_schedule, ...)"]),
        ("plan_ctx", "ScheduleContextSPtr = std::shared_ptr<ScheduleContext>", T.violet,
         ["scheduled_jobs: vector<ScheduledJobDataMsg>", "events: ScheduleEventDag   (every event has a job_index)"]),
        ("result", "PlanResponseMsg  (local in Plan(), returned at the end)", OK,
         ["scheduled_jobs: ScheduledJobData[]  <- sent to Dispatch", "(also success, message, id, schedule)"]),
    ]
    ow = (W - 2 * 30) / 3
    ob = []
    for i, (nm, ty, col, lines) in enumerate(objs):
        x = i * (ow + 30)
        d.rect(x, 0, ow, 96, rx=10, fill=T.card, stroke=col, sw=1.5)
        d.text(x + 14, 20, nm, size=14, family="mono", weight=700, fill=col)
        d.text(x + 14, 40, ty, size=11, family="mono", fill=T.fg2)
        for j, ln in enumerate(lines):
            d.text(x + 14, 62 + j * 18, ln, size=11, family="mono", fill=T.muted if ln.startswith("(") else T.fg)
        ob.append(BBox(x, 0, x + ow, 96))
    d.text(0, 122, "Created at the top of Plan():  PlanResponseMsg result;  ...  plan_ctx = "
                   "std::make_shared<ScheduleContext>(request_data.id, std::move(initial_state), now);",
           size=11, family="mono", fill=T.muted)
    # ---- the job loop ----
    y0 = 160
    d.text(0, y0, "The job loop:  for(const SchedulerJobMsg& job : request_data.pending_jobs) switch(job.type) { ... }",
           size=13, weight=600, fill=T.fg)
    cols = [(0, "request_data.pending_jobs[i]", "SchedulerJobMsg"),
            (225, "job_index passed", "= plan_ctx->scheduled_jobs.size()"),
            (470, "job method call (\"expansion\")", "Plan<Type>Job(plan_ctx, ..., job_index)"),
            (760, "then", "which list gets the job"),
            (985, "plan_ctx->scheduled_jobs", "after this step"),
            (1175, "result.scheduled_jobs", "after this step")]
    hy = y0 + 22
    d.rect(-8, hy - 4, W + 16, 42, rx=6, fill=T.muted_bg, layer="under")
    for x, h, sub in cols:
        d.text(x, hy + 9, h, size=11, family="mono", weight=600, fill=T.fg2)
        if sub:
            d.text(x, hy + 26, sub, size=10, family="mono", fill=T.muted)
    rows = [("A  RETRIEVE", "0", True, "PlanRetrieveJob: adds its events (bay", "transitions, tray moves), all job_index 0",
             "plan_ctx->PushBackScheduledJob(job)", [("A", OK)], []),
            ("B  INSERT", "1", False, "PlanInsertJob: adds 2 events (idx 1),", "then fails: returns {false, msg}",
             "result.scheduled_jobs.push_back(\n  FailJob(job, msg))", [("A", OK)], [("B", BAD)]),
            ("C  REPARK_TRAY", "1", True, "PlanReparkTrayJob: adds 1 event (idx 1);", "B's 2 leftovers now look like C's",
             "plan_ctx->PushBackScheduledJob(job)", [("A", OK), ("C", OK)], [("B", BAD)]),
            ("D  MOVE_AGV", "2", True, "PlanAgvMoveJob: adds 1 event (idx 2)", "returns success",
             "plan_ctx->PushBackScheduledJob(job)", [("A", OK), ("C", OK), ("D", OK)], [("B", BAD)])]
    y = hy + 50
    for i, (job, idx, ok, m1, m2, act, sj, res) in enumerate(rows):
        if i % 2 == 0:
            d.rect(-8, y - 6, W + 16, 56, rx=6, fill=T.tint(T.card, 0.6, T.bg), layer="under")
        d.text(0, y + 10, job, size=12, family="mono", weight=600, fill=T.fg)
        d.text(225, y + 10, idx, size=13, family="mono", weight=700, fill=IDX)
        chip(d, 470, y + 10, "success" if ok else "failure", OK if ok else BAD, size=10.5)
        d.text(550, y + 10, m1, size=10.5, fill=T.fg2)
        d.text(470, y + 32, m2, size=10.5, fill=T.fg2 if ok else BAD)
        for j, ln in enumerate(act.split("\n")):
            d.text(760, y + 10 + j * 16, ln, size=10.5, family="mono", fill=OK if ok else BAD)
        _cells(d, 985, y - 2, sj)
        _cells(d, 1175, y - 2, res)
        y += 56
    # ---- end of Plan() ----
    y2 = y + 30
    d.text(0, y2, "After the loop: tray and AGV assignment, motion planning, then the response is built", size=13,
           weight=600, fill=T.fg)
    steps = [
        ("BuildActionDagFromMotions", "for each motion: action.job_id = plan_ctx->scheduled_jobs[event->GetJobIndex()]"
         ".job.guid", [("A", OK), ("C", OK), ("D", OK)], ""),
        ("BuildScheduledActionsArray", "copy into unordered_map<guid, ...>, append each action's position to its job's "
         "node_indices, clear + refill the vector", [("C", OK), ("A", OK), ("D", OK)], "plan_ctx->scheduled_jobs"),
        ("final loop in Plan()", "for each entry of plan_ctx->scheduled_jobs: job.state = STATE_EXECUTING; "
         "RETRIEVE: bay_id, bay_arrival_node_guid; result.scheduled_jobs.push_back(entry)", None, ""),
        ("SchedulerRos (plan service)", "after Plan() returns: job_data.job.time_planned = now for every entry",
         None, ""),
    ]
    yy = y2 + 24
    for nm, what, cells, tag in steps:
        d.text(0, yy + 13, nm, size=11.5, family="mono", weight=600, fill=T.sky)
        d.text(230, yy + 13, what, size=10.5, fill=T.fg2)
        if cells:
            _cells(d, 1175, yy, cells)
        yy += 36
    d.rect(-8, yy + 2, W + 16, 40, rx=8, fill=T.tint(OK, 0.06, T.bg), stroke=T.tint(OK, 0.5, T.bg), sw=1)
    d.text(6, yy + 22, "result.scheduled_jobs  (what Dispatch receives)  =", size=12, family="mono", weight=600,
           fill=T.fg)
    _cells(d, 420, yy + 9, [("B  STATE_ERROR", BAD), ("C  EXECUTING", OK), ("A  EXECUTING", OK), ("D  EXECUTING", OK)])
    d.text(940, yy + 22, "failures first, then planned jobs in hash-map order", size=11, fill=T.muted)
    frame(d, title="How scheduled_jobs is built, used and rebuilt",
          subtitle="Each pending job goes to exactly one list during the loop: plan_ctx->scheduled_jobs if its job "
                   "method succeeds, result.scheduled_jobs (as a FailJob entry) if it fails. Planned jobs reach result "
                   "only at the very end.",
          badge_key="as-built",
          legend=[("box", OK, "planned job"), ("box", BAD, "failed job"), ("box", IDX, "job_index"),
                  ("box", T.violet, "plan_ctx (ScheduleContext)"), ("box", T.sky, "request_data")],
          footnote="Event counts and the rebuild order are illustrative. If a later stage (tray or AGV assignment, "
                   "CHUGG) fails, Plan() instead returns early and appends a FailJob entry for every pending job.")
    return d


# --------------------------------------------------------------------------------------
# 70 — last_entity_event during job expansion
# --------------------------------------------------------------------------------------

RULE_COL = {"A": T.green, "B": T.amber, "C": T.violet}


@figure("70_last_entity_event", "last_entity_event during job expansion", DOC1)
def last_entity_event_flow():
    from fig_eventdag import _node, POS
    d = Doc("70_last_entity_event", "last_entity_event while jobs are expanded",
            "Six events are added in order. For each, the table shows the map lookup (rule A), the leaf edges "
            "(rule B), the bay edge (rule C) and the map afterwards; the DAG on the right colours each edge by "
            "the rule that added it.")
    hx = [0, 36, 270, 430, 560, 670]
    for x, h in zip(hx, ["#", "event added (job)", "rule A: key -> edge", "rule B", "rule C",
                         "last_entity_event after"]):
        d.text(x, 0, h, size=11, family="mono", weight=600, fill=T.muted)
    rows = [
        ("a", "BayTransition B21 (0)", "Bay 21: none", "-", "-", ["Bay21:a"]),
        ("b", "TrayMove T21 -> ? (0)", "Tray 21: none", "a -> b", "-", ["Bay21:a", "Tray21:b"]),
        ("c", "TrayMove T17 -> B21 (0)", "Tray 17: none", "b -> c", "a -> c", ["Bay21:a", "Tray21:b", "Tray17:c"]),
        ("d", "BayTransition B21 (0)", "Bay 21: a -> d", "c -> d", "-", ["Bay21:d", "Tray21:b", "Tray17:c"]),
        ("e", "TrayMove T19 -> P24 (1)", "Tray 19: none", "-", "-", ["... ", "Tray19:e"]),
        ("f", "TrayMove T19 -> P23 (2)", "Tray 19: e -> f", "-", "-", ["... ", "Tray19:f"]),
    ]
    y = 22
    for i, (k, ev, ra, rb, rc, mp) in enumerate(rows):
        if i % 2 == 0:
            d.rect(-8, y - 6, 1030, 34, rx=6, fill=T.tint(T.card, 0.6, T.bg), layer="under")
        d.text(hx[0], y + 11, k, size=12.5, family="mono", weight=700, fill=T.fg)
        d.text(hx[1], y + 11, ev, size=11.5, family="mono", fill=T.fg2)
        d.text(hx[2], y + 11, ra, size=11.5, family="mono", fill=RULE_COL["A"] if "->" in ra else T.muted)
        d.text(hx[3], y + 11, rb, size=11.5, family="mono", fill=RULE_COL["B"] if "->" in rb else T.faint)
        d.text(hx[4], y + 11, rc, size=11.5, family="mono", fill=RULE_COL["C"] if "->" in rc else T.faint)
        x = hx[5]
        for m in mp:
            changed = m.endswith(":" + k)
            b = chip(d, x, y + 11, m, T.green if changed else T.fg2, size=10.5)
            x = b.x1 + 4
        y += 34
    # DAG with coloured edges
    gx0, gy0 = 0, y + 76
    d.text(0, gy0 - 52, "The resulting DAG, edges coloured by rule", size=13, weight=600, fill=T.fg)
    gxs, gys = 110, 70
    boxes = {}
    for k, (c, r) in POS.items():
        boxes[k] = _node(d, gx0 + c * gxs, gy0 + r * gys, k)
    edges = [("a", "b", "B"), ("b", "c", "B"), ("c", "d", "B"), ("a", "c", "C"), ("a", "d", "A"), ("e", "f", "A")]
    for u, v, r in edges:
        a, b = boxes[u], boxes[v]
        col = RULE_COL[r]
        if abs(a.cy - b.cy) < 1 and b.x0 - a.x1 < gxs:
            pts = [(a.x1, a.cy), (b.x0, b.cy)]
        else:
            lift = 16 if v == "c" else 30
            pts = [(a.cx + 8, a.y0), (a.cx + 8, a.y0 - lift), (b.cx - 8, a.y0 - lift), (b.cx - 8, b.y0)]
        connect(d, pts, kind="flow", color=col, size=7, sw=1.8, radius=5)
    note(d, 520, gy0 - 30, 500,
         "Rule A links events of the same entity across jobs (e -> f). Rule B only links events of one job. "
         "Rule C reads last_entity_event for a bay or VECS but never writes it. After job expansion nothing "
         "updates the map again, so later stages keep their own (last_tray_event, last_agv_event).",
         title="What the map is for", accent=T.green)
    frame(d, title="last_entity_event while jobs are expanded",
          subtitle="The map holds, for each AGV, tray, bay and VECS, the last event that touched it. "
                   "UpdateLastEntityEvent(key, e) adds last[key] -> e if there is an entry, then sets last[key] = e.",
          badge_key="illustrative",
          legend=[("arrow", RULE_COL["A"], "rule A (last_entity_event)"), ("arrow", RULE_COL["B"], "rule B (leaves of the job)"),
                  ("arrow", RULE_COL["C"], "rule C (into a bay / VECS)"), ("box", T.green, "map entry changed by this event")],
          footnote="Same six events as the topological-ordering figure. Keys are GarageEntityIdMsg values built with "
                   "AgvId / TrayId / BayId / VecsId; a TrayMove with no tray has no key and skips rule A.")
    return d


# --------------------------------------------------------------------------------------
# 71 — first_tray_event: filled by tray assignment, read by AGV assignment
# --------------------------------------------------------------------------------------

@figure("71_first_tray_event", "first_tray_event: why the first move", DOC1)
def first_tray_event_flow():
    d = Doc("71_first_tray_event", "first_tray_event: written by tray assignment, read by AGV assignment",
            "Left: tray assignment fills the map with the first move of each tray. Right: AGV assignment uses it "
            "so an AGV does not drive through a tray's starting node before the tray has left; using the last "
            "move would close a cycle.")
    # ---- left: filling ----
    d.text(0, 0, "1  Tray assignment fills it (DoTrayAssignments)", size=13, weight=600, fill=T.fg)
    hx = [0, 40, 270, 470]
    for x, h in zip(hx, ["#", "TrayMove processed", "last_tray_event", "first_tray_event"]):
        d.text(x, 26, h, size=11, family="mono", weight=600, fill=T.muted)
    rows = [("m1", "T15: P15 -> P19 (blocker)", "15: m1", ["15: m1"], True),
            ("m2", "T17: P17 -> B21", "17: m2", ["15: m1", "17: m2"], True),
            ("m3", "T15: P19 -> P24", "15: m3  (+ edge m1 -> m3)", ["15: m1", "17: m2"], False)]
    y = 46
    for i, (k, mv, lte, fte, new) in enumerate(rows):
        if i % 2 == 0:
            d.rect(-8, y - 6, 640, 32, rx=6, fill=T.tint(T.card, 0.6, T.bg), layer="under")
        d.text(hx[0], y + 10, k, size=12, family="mono", weight=700, fill=T.amber)
        d.text(hx[1], y + 10, mv, size=11.5, family="mono", fill=T.fg2)
        d.text(hx[2], y + 10, lte, size=11.5, family="mono", fill=T.fg2)
        x = hx[3]
        for j, m in enumerate(fte):
            changed = new and j == len(fte) - 1
            b = chip(d, x, y + 10, m, T.green if changed else T.fg2, size=10.5)
            x = b.x1 + 4
        y += 32
    code = ["if(last_tray_event.contains(tray))", "  AddDependency(last_tray_event[tray], move);",
            "else", "  ctx->first_tray_event[tray] = move;   // first time this tray moves",
            "last_tray_event[tray] = move;"]
    from components import code_panel
    cp = code_panel(d, 0, y + 10, 520, code, title="same pattern in the main loop and AssignDestForUntargetedMove",
                    size=11.5)
    # ---- right: using ----
    rx = 700
    d.text(rx, 0, "2  AGV assignment reads it (MoveAgvToTrayPose)", size=13, weight=600, fill=T.fg)
    d.text(rx, 24, "AGV-1's chain: moves T15 out, then fetches X via P15, later moves T15 again",
           size=S.small, fill=T.muted)
    nodes = [("m1", "AGV-1 carries T15 out (m1)", T.amber), ("ap", "AGV-1 approaches X via P15", T.green),
             ("cx", "AGV-1 carries X", T.amber), ("m3", "AGV-1 carries T15 again (m3)", T.amber)]
    bx = {}
    yy = 52
    for k, txt, col in nodes:
        d.rect(rx, yy, 300, 36, rx=8, fill=T.card, stroke=col, sw=1.4)
        d.text(rx + 14, yy + 18, txt, size=11.5, family="mono", fill=T.fg)
        bx[k] = BBox(rx, yy, rx + 300, yy + 36)
        yy += 64
    for a, b in (("m1", "ap"), ("ap", "cx"), ("cx", "m3")):
        connect(d, [(bx[a].cx, bx[a].y1), (bx[b].cx, bx[b].y0)], kind="flow", color=T.fg2, size=7)
    label_pill(d, bx["m1"].cx + 70, (bx["m1"].y1 + bx["ap"].y0) / 2, "AGV-1's own chain", color=T.muted)
    # good edge first -> approach
    connect(d, [(bx["m1"].x1, bx["m1"].cy), (bx["m1"].x1 + 40, bx["m1"].cy), (bx["m1"].x1 + 40, bx["ap"].cy),
                (bx["ap"].x1, bx["ap"].cy)], kind="flow", color=T.green, size=7, sw=1.8,
            label="first_tray_event[15] -> approach", label_at=(bx["m1"].x1 + 40, (bx["m1"].cy + bx["ap"].cy) / 2),
            label_anchor="start")
    # bad edge last -> approach
    connect(d, [(bx["m3"].x0, bx["m3"].cy), (bx["m3"].x0 - 40, bx["m3"].cy), (bx["m3"].x0 - 40, bx["ap"].cy),
                (bx["ap"].x0, bx["ap"].cy)], kind="flow", color=T.red, size=7, sw=1.8, dash="5 4",
            label="last move -> approach", label_at=(bx["m3"].x0 - 40, (bx["m3"].cy + bx["ap"].cy) / 2),
            label_anchor="end")
    d.text(rx, yy + 8, "green: what the code adds (T15 has left P15 before AGV-1 drives through it)",
           size=S.small, fill=T.green)
    d.text(rx, yy + 26, "red: with the LAST move, approach -> ... -> m3 -> approach is a cycle",
           size=S.small, fill=T.red)
    note(d, rx, yy + 46, 360,
         "For each node on the AGV's path to the tray it is fetching (except the destination), look up the tray "
         "that started there in ctx->initial_state, then add first_tray_event[tray] -> move_to_tray unless "
         "WouldCreateCycle(first, root_event) says it would loop. A tray that never moves has no entry, so no edge.",
         title="The rule in MoveAgvToTrayPose", accent=T.sky)
    frame(d, title="first_tray_event: written by tray assignment, read by AGV assignment",
          subtitle="The map answers one question: when has this tray left the node it started on? The first move "
                   "is the answer, and the only safe one: later moves of the same tray may come after the very AGV "
                   "move that has to wait.",
          badge_key="illustrative",
          legend=[("box", T.green, "map entry written by this move"), ("arrow", T.green, "edge the code adds"),
                  ("dasharrow", T.red, "edge it must not add (cycle)")],
          footnote="Tray ids, nodes and the AGV chain are illustrative. The rule and the reason are from "
                   "scheduler.cpp (MoveAgvToTrayPose) and the comment on first_tray_event in scheduler.hpp.")
    return d


# --------------------------------------------------------------------------------------
# 72 — CHUGG: inputs, what is known inside, outputs
# --------------------------------------------------------------------------------------

@figure("72_chugg_io", "CHUGG inputs and outputs", DOC1)
def chugg_io():
    d = Doc("72_chugg_io", "CHUGG: what goes in, what comes out",
            "PlanMotions builds seven inputs, constructs volley::Chugg and calls SolveSequential; the result is a "
            "ContinuousState of per-entity trajectories that ResponseFromTrajectories turns into ActionNodes.")
    ins = [("gg_", "GarageGraph: poses and moves"), ("table_", "CollisionTable: footprint conflicts"),
           ("ctx->events", "the reduced event DAG (what, in which order)"),
           ("initial_trajectories", "ContinuousState(initial_state, table_, layout, start_time)"),
           ("edge_durations", "GetEdgeDurations(gg_, cost_model_): trapezoid profile"),
           ("heuristics", "GetAllPairsMinCost(gg_, edge_durations, ...): A* heuristic"),
           ("cost_model_", "MotionCostModel: speeds, lift times, ...")]
    y = 0
    ib = []
    for nm, desc in ins:
        d.rect(0, y, 380, 40, rx=8, fill=T.card, stroke=T.sky, sw=1.2)
        d.text(14, y + 13, nm, size=12, family="mono", weight=700, fill=T.sky)
        d.text(14, y + 29, desc, size=10.5, fill=T.fg2)
        ib.append(BBox(0, y, 380, y + 40))
        y += 48
    # CHUGG box
    cx0, cy0, cw, ch = 470, 0, 480, max(y - 8, 360)
    d.rect(cx0, cy0, cw, ch, rx=12, fill=T.tint(T.amber, 0.06, T.bg), stroke=T.amber, sw=1.6)
    d.text(cx0 + 16, cy0 + 22, "volley::Chugg  (motion_planner/chugg.hpp)", size=13, family="mono", weight=700,
           fill=T.amber)
    d.text(cx0 + 16, cy0 + 42, "Constrained Huge Unknown Graph alGorithm", size=11, family="mono",
           fill=T.fg2)
    d.rect(cx0 + 16, cy0 + 60, cw - 32, ch - 120, rx=8, fill="none", stroke=T.amber, sw=1.1)
    d.text(cx0 + 28, cy0 + 78, "inside (chugg_common.cpp, chugg_sequential.cpp)", size=11, fill=T.muted)
    inside = ["InitializeEventOrder: one topological order", "  of the event DAG = the priority order",
              "for each event in that order:", "  wait for dependencies (GetDependency-",
              "    CompletionTime), then plan it:",
              "  AGV / tray: SIPP on this AGV's safe-",
              "    interval table, others frozen in place",
              "  bay / VECS: fixed duration (params; 60 s",
              "    hard-coded for PROCESS_RETRIEVE)",
              "  commit; carve into every other AGV's table",
              "pairwise collision check of all new motions"]
    for i, ln in enumerate(inside):
        d.text(cx0 + 28, cy0 + 102 + i * 18, ln, size=11, family="mono", fill=T.fg2)
    d.text(cx0 + 16, cy0 + ch - 44, "nullopt -> every job fails:", size=11, fill=T.red)
    d.text(cx0 + 16, cy0 + ch - 26, "\"CHUGG failed to find a solution, event dag may be infeasible\"", size=10.5,
           family="mono", fill=T.red)
    for b in ib:
        connect(d, [(b.x1, b.cy), (cx0 - 30, b.cy), (cx0 - 30, cy0 + ch / 2), (cx0, cy0 + ch / 2)], kind="flow",
                color=T.sky, size=7, sw=1.1)
    # outputs
    ox = cx0 + cw + 80
    d.rect(ox, cy0, 380, 230, rx=10, fill=T.card, stroke=T.green, sw=1.5)
    d.text(ox + 14, cy0 + 20, "ContinuousState", size=13, family="mono", weight=700, fill=T.green)
    d.text(ox + 14, cy0 + 38, "GetTrajectories(): entity -> list of Motion", size=11, family="mono", fill=T.fg2)
    mlines = ["Motion", "  GetEntityId()    which AGV / bay / VECS ...", "  GetInterval()    [start, end] time",
              "  GetCollisionId() footprint (AGV, AGV+tray, ...)", "  GetActionId()    = event vertex in ctx->events",
              "  GetSourcePose(), GetLocation()", "  GetDelta()       discrete change, if any", "  IsIdle()"]
    for i, ln in enumerate(mlines):
        d.text(ox + 14, cy0 + 66 + i * 19, ln, size=11, family="mono", fill=T.fg if i == 0 else T.fg2)
    connect(d, [(cx0 + cw, cy0 + 110), (ox, cy0 + 110)], kind="flow", color=T.green, size=8, label="optional",
            label_at=((cx0 + cw + ox) / 2, cy0 + 96))
    rb = BBox(ox, cy0 + 270, ox + 380, cy0 + 360)
    d.rect(rb.x0, rb.y0, rb.w, rb.h, rx=10, fill=T.card, stroke=T.violet, sw=1.4)
    d.text(ox + 14, rb.y0 + 20, "ResponseFromTrajectories", size=12.5, family="mono", weight=700, fill=T.violet)
    d.text(ox + 14, rb.y0 + 42, "one ActionNode per motion with a delta;", size=11, fill=T.fg2)
    d.text(ox + 14, rb.y0 + 60, "action id -> event -> job guid", size=11, fill=T.fg2)
    connect(d, [(ox + 190, cy0 + 230), (ox + 190, rb.y0)], kind="flow", color=T.violet, size=8)
    frame(d, title="CHUGG: what goes in, what comes out",
          subtitle="The scheduler decides WHAT happens and in which order (the event DAG). CHUGG decides WHEN and "
                   "WHERE along the graph, so that bodies never collide: it returns timed trajectories for every entity.",
          badge_key="as-built",
          legend=[("box", T.sky, "inputs built in PlanMotions"), ("box", T.amber, "volley::Chugg::SolveSequential"),
                  ("box", T.green, "output")],
          footnote="Inputs and the call are from Scheduler::PlanMotions; the inside of the amber box is from motion_planner "
                   "(chugg_common.cpp, chugg_sequential.cpp); the Motion accessors are from trajectory.hpp.")
    return d


# --------------------------------------------------------------------------------------
# 73 — ScheduledJobData: complete UML with who writes what
# --------------------------------------------------------------------------------------

@figure("73_scheduled_job_data_uml", "ScheduledJobData and the messages around it", DOC1)
def scheduled_job_data_uml():
    d = Doc("73_scheduled_job_data_uml", "ScheduledJobData: what one entry holds",
            "UML of the ROS messages around ScheduledJobData: PlanResponse holds the Schedule and the "
            "ScheduledJobData array; each entry holds a full SchedulerJob plus links into Schedule.nodes.")
    M = 11.5
    RESP, REQ, LINK = T.green, T.sky, T.amber
    resp = uml_class(d, 0, 0, "PlanResponse", accent=RESP, stereo="interfaces/msg", size=M,
                     attrs=["+ success: bool", "+ message: string", "+ id: Guid", "+ schedule: Schedule",
                            "+ scheduled_jobs: ScheduledJobData[]"])
    sjd = uml_class(d, 0, resp.y1 + 80, "ScheduledJobData", accent=RESP, stereo="interfaces/msg · one per job",
                    size=M,
                    attrs=["+ job: SchedulerJob",
                           "    // copied from the request; state etc. filled in",
                           "+ node_indices: uint32[]",
                           "    // positions in PlanResponse.schedule.nodes",
                           "    // written by BuildScheduledActionsArray",
                           "    // .msg: the job's final actions would suffice; all are listed",
                           "+ bay_id: uint16",
                           "    // RETRIEVE only: bay of the PROCESS_RETRIEVE action",
                           "+ bay_arrival_node_guid: Guid",
                           "    // RETRIEVE only: guid of that action"])
    job = uml_class(d, sjd.x1 + 120, 0, "SchedulerJob", accent=REQ, stereo="interfaces/msg · the request's job",
                    size=M,
                    attrs=["// what to do (from the request; never changed)",
                           "+ guid: Guid",
                           "+ type: uint8,  type_name: string   // TYPE_RETRIEVE, ...",
                           "+ agv_id, bay_id, tray_id: uint16",
                           "+ payload_id: Guid",
                           "+ destination: GaragePose",
                           "+ allow_reciprocal: bool",
                           "// status (filled in by the scheduler)",
                           "+ state: uint8,  state_name: string",
                           "    // in: STATE_UNPLANNED; out: STATE_EXECUTING or STATE_ERROR",
                           "+ note: string        // FailJob: the failure message",
                           "+ retain_job: bool    // FailJob: ask Dispatch to keep and retry",
                           "+ time_planned: Time  // SchedulerRos, after Plan()",
                           "// not written by the scheduler package",
                           "+ time_registered, time_completed: Time",
                           "+ seconds_to_bay_arrival: float32",
                           "+ needs_bay_in_retrieve: bool",
                           "// STATE_*: UNPLANNED 0, EXECUTING 1, SUCCESS 2, ERROR 3"])
    sch = uml_class(d, job.x0, job.y1 + 60, "Schedule", accent=RESP, stereo="interfaces/msg", size=M,
                    attrs=["+ header: std_msgs/Header", "+ nodes: ActionNode[]   // topological order"])
    an = uml_class(d, job.x0, sch.y1 + 50, "ActionNode", accent=RESP, stereo="interfaces/msg · abridged", size=M,
                   attrs=["+ guid: Guid", "+ job_id: Guid      // = SchedulerJob.guid of its job",
                          "+ type: uint8         // AGV / BAY / VECS / VRC command",
                          "+ parents: uint32[]   // indices into Schedule.nodes",
                          "+ bay_id: uint32,  bay_command: BayCommand", "+ agv_id, agv_command, ..."])
    # composition
    connect(d, [(resp.cx, resp.y1), (resp.cx, sjd.y0)], kind="comp", color=RESP, mult_end="0..*",
            label="scheduled_jobs", label_at=(resp.cx, (resp.y1 + sjd.y0) / 2))
    jy = sjd.y0 + 34
    connect(d, [(sjd.x1, jy), (job.x0, jy)],
            kind="comp", color=REQ, mult_end="1", label="job", label_at=((sjd.x1 + job.x0) / 2, jy - 12))
    connect(d, [(resp.x1 - 40, resp.y0), (resp.x1 - 40, -28), (job.x1 + 28, -28), (job.x1 + 28, sch.cy), (sch.x1, sch.cy)],
            kind="comp", color=RESP, mult_end="1", label="schedule", label_at=((resp.x1 + job.x1) / 2, -40))
    connect(d, [(sch.cx, sch.y1), (sch.cx, an.y0)], kind="comp", color=RESP, mult_end="0..*", label="nodes",
            label_at=(sch.cx + 10, (sch.y1 + an.y0) / 2 - 6), label_anchor="start")
    # links by value
    yl = sjd.y0 + 104
    connect(d, [(sjd.x1, yl), (sjd.x1 + 90, yl), (sjd.x1 + 90, an.y0 + 40), (an.x0, an.y0 + 40)], kind="dep",
            color=LINK, label="node_indices[i] = index into nodes", label_at=(sjd.x1 + 90, an.y0 + 10),
            label_anchor="end")
    yb = max(an.y1, sjd.y1) + 40
    bx = sjd.x0 + sjd.w * 0.4
    connect(d, [(bx, sjd.y1), (bx, yb), (an.cx, yb), (an.cx, an.y1)], kind="dep",
            color=LINK, label="bay_arrival_node_guid = guid of the PROCESS_RETRIEVE node",
            label_at=((bx + an.cx) / 2, yb + 16))
    note(d, 0, yb + 44, sjd.w,
         "Inside Plan(), entries are ScheduledJobDataMsg (the C++ alias). plan_ctx->scheduled_jobs holds the "
         "planned jobs; result.scheduled_jobs (PlanResponse) ends up with every pending job: failures from FailJob, "
         "then the planned entries.", title="Where entries live", accent=RESP)
    frame(d, title="ScheduledJobData: what one entry holds",
          subtitle="One ScheduledJobData per pending job in the response. It wraps the request's SchedulerJob (with "
                   "its status filled in) and points into the response's Schedule: which actions belong to this job, "
                   "and for a retrieve, which action is the car's arrival at the bay.",
          badge_key="as-built",
          legend=[("box", REQ, "request side (SchedulerJob)"), ("box", RESP, "response side"),
                  ("comp", T.fg2, "contains"), ("dep", LINK, "refers to (by index or guid)")],
          footnote="Fields and types from interfaces/msg (ScheduledJobData.msg, SchedulerJob.msg, PlanResponse.msg, Schedule.msg, ActionNode.msg); \"who writes\" comments from the scheduler code.")
    return d


# --------------------------------------------------------------------------------------
# 74 — ScheduledJobData on the Pecos map: what node_indices points at
# --------------------------------------------------------------------------------------

@figure("74_scheduled_job_data_map", "ScheduledJobData on a 2D example", DOC1)
def scheduled_job_data_map():
    from facility import Map
    d = Doc("74_scheduled_job_data_map", "ScheduledJobData on the Pecos map",
            "A RETRIEVE (car on T17 to bay B21) and a MOVE_AGV planned together. The map numbers each action by its "
            "index in Schedule.nodes; the ScheduledJobData cards show which indices belong to which job.")
    QA_X, QA_Y = (20.4, 46.4), (15.3, 25.2)
    s = 24
    m = Map(d, 0, 0, s, QA_X, QA_Y)
    m.base(labels=True, zones=False, axes=False)
    m.tray(17, "T17", payload=True, chip_pos="bl")
    m.agv(13, "AGV-1", heading=90, label_side="below")
    m.agv(26, "AGV-2", heading=90, label_side="above")
    JA, JB = T.amber, T.sky
    m.route([13, 15, 17], T.green, sw=3, offset=(0, -6))
    m.route([17, 15, 13, 18, 22, 41, 21], JA, sw=4, offset=(0, 6))
    m.route([26, 25], JB, sw=3)
    from components import num_badge
    marks = [(0, (34.0, 17.2), -16, T.green), (1, (40.1, 17.2), -16, T.green), (2, (43.0, 17.2), -22, JA),
             (4, (40.1, 17.2), 18, JA), (5, (34.0, 17.2), 18, JA), (6, (30.9, 18.35), 0, JA),
             (7, (30.9, 20.6), 0, JA), (8, (29.45, 21.7), -16, JA), (9, (25.5, 21.7), -16, JA),
             (10, (23.1, 21.7), 16, JA), (11, (23.1, 21.7), -24, T.violet), (3, (34.0, 24.0), -16, JB)]
    for n, xy, dy, col in marks:
        x, y = m.P(xy)
        if xy == (30.9, 18.35) or xy == (30.9, 20.6):
            x += 16
        if n == 10:
            x += 28
        num_badge(d, x, y + dy, n, col, r=10)
    mb = m.box
    # ---- Schedule.nodes strip ----
    sx = mb.x1 + 50
    d.text(sx, 0, "PlanResponse.schedule.nodes  (ActionNode[] in topological order)", size=12.5, weight=600,
           fill=T.fg)
    acts = [("AGV-1: W13 -> P15", JA), ("AGV-1: P15 -> P17", JA), ("AGV-1: lift", JA), ("AGV-2: W26 -> W25", JB),
            ("AGV-1: P17 -> P15, lifted", JA), ("AGV-1: P15 -> W13, lifted", JA), ("AGV-1: W13 -> W18, lifted", JA),
            ("AGV-1: W18 -> W22, lifted", JA), ("AGV-1: W22 -> W41, lifted", JA), ("AGV-1: W41 -> B21, lifted", JA),
            ("AGV-1: lower", JA), ("bay 21: PROCESS_RETRIEVE", T.violet)]
    cy = 22
    cells = {}
    for i, (lab, col) in enumerate(acts):
        y = cy + i * 26
        d.rect(sx, y, 34, 22, rx=4, fill=T.muted_bg)
        d.text(sx + 17, y + 11, str(i), size=11, family="mono", weight=700, fill=T.fg, anchor="middle")
        d.rect(sx + 40, y, 300, 22, rx=4, fill=T.tint(col, 0.14, T.bg), stroke=T.tint(col, 0.6, T.bg), sw=1)
        d.text(sx + 50, y + 11, lab, size=11, family="mono", fill=T.fg)
        d.text(sx + 332, y + 11, "job A" if col != JB else "job B", size=10, family="mono",
               fill=JB if col == JB else JA, anchor="end")
        cells[i] = BBox(sx, y, sx + 340, y + 22)
    # ---- ScheduledJobData cards ----
    kx = sx + 390
    cards = [
        ("ScheduledJobData  (job A)", JA,
         ["job.type = TYPE_RETRIEVE", "job.guid = a1f3...   (= ActionNode.job_id)", "job.state = STATE_EXECUTING",
          "node_indices = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11]", "bay_id = 21",
          "bay_arrival_node_guid = nodes[11].guid"]),
        ("ScheduledJobData  (job B)", JB,
         ["job.type = TYPE_MOVE_AGV", "job.guid = 7c02...", "job.state = STATE_EXECUTING", "node_indices = [3]",
          "bay_id = 0   (not a retrieve)", "bay_arrival_node_guid = (empty)"]),
        ("ScheduledJobData  (job C, failed)", T.red,
         ["job.type = TYPE_INSERT", "job.state = STATE_ERROR", "job.note = <failure message>",
          "job.retain_job = true / false", "node_indices = []   (no actions)"]),
    ]
    y = 22
    cb = []
    for title, col, lines in cards:
        h = 30 + 19 * len(lines) + 8
        d.rect(kx, y, 400, h, rx=9, fill=T.card, stroke=col, sw=1.5)
        d.text(kx + 14, y + 17, title, size=12.5, family="mono", weight=700, fill=col)
        for j, ln in enumerate(lines):
            d.text(kx + 14, y + 40 + j * 19, ln, size=11, family="mono", fill=T.fg2)
        cb.append(BBox(kx, y, kx + 400, y + h))
        y += h + 18
    # arrows from job A card to index 11 and job B card to index 3
    connect(d, [(cb[0].x0, cb[0].y0 + 135), (cells[11].x1 + 20, cb[0].y0 + 135), (cells[11].x1 + 20, cells[11].cy),
                (cells[11].x1, cells[11].cy)], kind="dep", color=T.violet)
    connect(d, [(cb[1].x0, cb[1].y0 + 97), (cells[3].x1 + 30, cb[1].y0 + 97), (cells[3].x1 + 30, cells[3].cy),
                (cells[3].x1, cells[3].cy)], kind="dep", color=JB)
    note(d, 0, mb.y1 + 24, mb.w,
         "node_indices are not contiguous: actions of different jobs interleave in the topological order "
         "(job B's move is index 3, in the middle of job A's actions). Dispatch uses node_indices to know which actions "
         "serve which job, and bay_arrival_node_guid to know when the car reaches the customer.",
         title="Reading node_indices", accent=T.amber)
    frame(d, title="ScheduledJobData on the Pecos map",
          subtitle="Two planned jobs and one failed job. AGV-1 fetches T17 (with its car) and carries it to bay B21; "
                   "AGV-2 moves out of the way. Badges on the map are positions in Schedule.nodes.",
          badge_key="yaml+hyp",
          legend=[("box", JA, "job A (RETRIEVE) actions"), ("box", JB, "job B (MOVE_AGV)"),
                  ("box", T.violet, "bay command"), ("route", T.green, "AGV-1 unloaded"), ("route", JA, "AGV-1 loaded")],
          footnote="Geometry from the Pecos YAML; occupancy, guids and the exact action order are illustrative. "
                   "The shape of job A's actions matches the RetrieveJob test.")
    return d
