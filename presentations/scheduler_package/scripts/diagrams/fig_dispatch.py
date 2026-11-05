"""fig_dispatch: the central package and the plan call seen from Dispatch (123, 124).

Doc 06-dispatch.html. Facts from sources/repomix-central.xml:
* dispatch_ros.cpp: publishers/subscriptions/services/clients (Plan client "/scheduler/plan", per-entity
  /command, /commandlist, VRC action), planner timer kPlannerPeriod = 850 ms, plan request/response published
  for bagging.
* garage_tracker: source of truth; publishes ContinousGarageInfo, DiscreteEvents, DiscreteGarageState.
* consistency_monitor: compares gitsha / layout md5 of every entity, including the scheduler's version info.
* Dispatch::ShouldCallPlanner, GetPlannerServiceRequest, PlanClientCallback, CreateExecutionStatePtr,
  ExecutionState::SendReadyCommands (30 s command horizon), UpdateInternal, CompleteJobs.
"""
from __future__ import annotations

from components import connect, frame, label_pill, uml_class
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import S, T

DOC = "06-dispatch.html"
DIS, SCH, TRK, ENT, MON, OPS = T.sky, T.green, T.violet, T.amber, T.teal, T.fg2


def _box(d, x, y, w, title, sub, col, rows=(), h=None):
    h = h or (44 + 18 * len(rows) + (8 if rows else 0))
    d.rect(x, y, w, h, rx=10, fill=T.card, stroke=col, sw=1.6)
    d.text(x + 12, y + 18, title, size=13, family="mono", weight=700, fill=col)
    d.text(x + 12, y + 35, sub, size=10.5, fill=T.muted)
    yy = y + 56
    for r in rows:
        d.text(x + 14, yy, r, size=11, family="mono", fill=T.fg2)
        yy += 18
    return BBox(x, y, x + w, y + h)


@figure("123_central_components", "The central package around the scheduler", DOC)
def central_components():
    d = Doc("123_central_components", "The central package around the scheduler",
            "Component diagram: the dispatcher sits between the job sources, the garage tracker, the scheduler "
            "and the machines; the other central nodes monitor or report.")
    ops = _box(d, 360, 0, 380, "job sources", "operators, UI, patrons; Dispatch's own idle jobs", OPS,
               ["retrieve, insert*, move_agv, move_tray, repark_tray,", "charge_payload, transition_bay_to_*,",
                "clean_garage, rebalance_garage   (*from bay events)"])
    dis = _box(d, 360, 190, 380, "dispatcher", "Dispatch + DispatchRos: job queue, plan calls, execution", DIS,
               ["jobs_pending_ / jobs_active_ / jobs_completed_", "ExecutionState: schedule, latest, future",
                "planner timer 850 ms, command horizon 30 s"])
    sch = _box(d, 860, 190, 300, "scheduler", "SchedulerRos + Scheduler (this study pack)", SCH,
               ["service /scheduler/plan", "Plan(PlanRequest) -> PlanResponse", "stateless between calls"])
    trk = _box(d, 0, 190, 280, "garage_tracker", "source of truth for the garage", TRK,
               ["DiscreteGarageState, DiscreteEvents,", "ContinousGarageInfo", "set_*_disabledness services"])
    ent = _box(d, 360, 420, 380, "AGVs, bays, VECS, VRCs", "the machines (separate nodes)", ENT,
               ["AGV: /activate, /command, /commandlist, /stop", "bay, VECS: /command;  VRC: action goal",
                "each publishes reports"])
    mon = _box(d, 860, 420, 300, "monitors", "other central nodes", MON,
               ["consistency_monitor: versions + layout md5", "agv_monitor: disables low-battery AGVs",
                "garage_monitor, metrics_recorder,", "mqtt_bridge, safety_hardware_monitor"])
    connect(d, [(ops.cx, ops.y1), (dis.cx, dis.y0)], kind="assoc", color=OPS, sw=1.6, label="job services")
    connect(d, [(dis.x1, dis.cy - 16), (sch.x0, sch.cy - 16)], kind="assoc", color=SCH, sw=1.8,
            label="PlanRequest")
    connect(d, [(sch.x0, sch.cy + 18), (dis.x1, dis.cy + 18)], kind="assoc", color=SCH, sw=1.8, dash="6 4",
            label="PlanResponse")
    connect(d, [(trk.x1, trk.cy), (dis.x0, dis.cy)], kind="assoc", color=TRK, sw=1.6, label="state + events")
    connect(d, [(dis.cx, dis.y1), (ent.cx, ent.y0)], kind="assoc", color=ENT, sw=1.6, label="commands")
    connect(d, [(ent.x0, ent.cy), (trk.cx, ent.cy), (trk.cx, trk.y1)], kind="assoc", color=ENT, sw=1.4,
            dash="5 4", label="reports")
    connect(d, [(mon.cx, mon.y0), (mon.cx, dis.y1 + 40), (dis.x1 - 30, dis.y1 + 40), (dis.x1 - 30, dis.y1)],
            kind="assoc", color=MON, sw=1.4, dash="5 4", label="ConsistencyReport")
    frame(d, title="The central package around the scheduler",
          subtitle="The scheduler talks to one node only: the dispatcher calls /scheduler/plan and nothing else "
                   "calls it. Everything the scheduler knows about the garage arrives in that request.",
          badge_key="as-built",
          legend=[("arrow", T.fg2, "request, command or data flow"), ("dasharrow", T.fg2, "reply or report")])
    return d


@figure("124_plan_call_sequence", "One plan call seen from Dispatch (animated)", DOC)
def plan_call_sequence():
    d = Doc("124_plan_call_sequence", "One plan call seen from Dispatch",
            "UML sequence diagram, animated: the planner timer, the request, the scheduler, the checks on the "
            "response, the new execution state, command sending and job completion.")
    parts = [("tmr", "planner_timer_", T.muted), ("dis", ":Dispatch", DIS), ("sch", ":Scheduler", SCH),
             ("ex", "exec_state_ : ExecutionState", T.violet), ("ent", "machines", ENT)]
    sub = {"tmr": "DispatchRos, 850 ms", "dis": "central", "sch": "via /scheduler/plan",
           "ex": "schedule, latest, future", "ent": "AGVs, bays, VECS, VRCs"}
    xs, x = {}, 90
    for k, gap in (("tmr", 0), ("dis", 260), ("sch", 330), ("ex", 300), ("ent", 290)):
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

    def msg(a, b, text, *, ret=False, dy=42):
        nonlocal y
        c = T.muted if ret else col[b]
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

    def selfmsg(a, text, sub_text=None, dy=46):
        nonlocal y
        c = col[a]
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

    step("Every 850 ms the planner timer asks ShouldCallPlanner: Dispatch is RUNNING, no call is in flight, no "
         "job is active (overlapping planning is off), at least one enabled AGV is free, and some pending job is "
         "worth planning.")
    msg("tmr", "dis", "ShouldCallPlanner()")
    step("GetPlannerServiceRequest builds the request: base_state = GetLatest(); base_schedule = every incomplete "
         "node and active_jobs = jobs_active_ (both empty today); pending_jobs = queued jobs, capped by the request "
         "strategy. The jobs sent are remembered as in flight.")
    selfmsg("dis", "GetPlannerServiceRequest(now)", "plan_call_data_ = {id, base_schedule}; jobs_in_flight_")
    step("CallPlanner publishes the request on a topic for bagging and sends it asynchronously. The scheduler "
         "runs Plan() synchronously in its service callback and answers.")
    msg("dis", "sch", "async Plan(request)")
    selfmsg("sch", "Scheduler::Plan(request, now)", "reserve, expand, assign, CHUGG, action DAG")
    msg("sch", "dis", "PlanResponse", ret=True)
    step("PlanClientCallback checks, in order: an execution state exists, the id matches the call in flight, "
         "success is true, the execution state has not diverged, every base_schedule node is in the response "
         "unchanged, and not every job failed (if more than one was sent).")
    selfmsg("dis", "PlanClientCallback: id, success, diverged, base nodes, all-failed",
            "any failure -> RejectPlanResponse (and a simpler strategy if all jobs failed)")
    step("A new execution state is built from the response nodes alone: completed nodes are skipped, parents "
         "renumbered, AGV src/dst lift and pose fields rewritten from the future state, and every node applied "
         "to the future state.")
    msg("dis", "ex", "CreateExecutionStatePtr(latest, old schedule, response nodes)")
    step("Per returned job: EXECUTING moves it from pending to active with its node guids to complete; ERROR "
         "drops it, or keeps a RETRIEVE (retain_job, or requeued up to 10 times).")
    selfmsg("dis", "jobs: pending -> active | completed(ERROR) | requeued")
    step("Ready commands go out: an action is sent when its parents are done, it starts within the 30 s command "
         "horizon and the safety checker accepts it. AGV moves are chained into one command list.")
    msg("dis", "ex", "SendReadyCommands()")
    msg("ex", "ent", "/commandlist, /command, VRC goal")
    step("Machines report; the garage tracker turns reports into discrete events. Each event completes the "
         "matching leading action and advances the latest state. A job whose actions are all complete moves "
         "to completed (SUCCESS); when no job is active, the next plan call can happen.")
    msg("ent", "ex", "events (via garage_tracker)", ret=True)
    selfmsg("ex", "UpdateInternal -> CompleteAction", "a failure marks the state diverged; Dispatch stops")
    msg("ex", "dis", "schedule status", ret=True, dy=36)
    selfmsg("dis", "CompleteJobs(now): active -> completed")
    end_y = y + 4
    for k, _, c in parts:
        d.line(xs[k], head_h, xs[k], end_y, stroke=T.border, sw=1.2, dash="4 5", layer="under")
    x_left, x_right = 0, xs["ent"] + 160
    for k, y0, y1 in steps:
        with d.only(k):
            d.rect(x_left, y0 - 8, x_right - x_left, y1 - y0 + 16, rx=8, fill=T.tint(T.sky, 0.07, T.bg),
                   stroke=T.tint(T.sky, 0.35, T.bg), sw=1, layer="under")
        with d.at(k):
            d.text(x_left - 26, y0 + 4, f"{k + 1}", size=13, family="mono", weight=700, fill=T.sky)
    frame(d, title="One plan call seen from Dispatch",
          subtitle="From the timer that decides to plan to the jobs that complete. Messages stay on screen; the "
                   "highlighted band is the current step.",
          badge_key="as-built",
          legend=[("arrow", T.fg2, "call or command"), ("dep", T.muted, "reply or event")])
    return d
