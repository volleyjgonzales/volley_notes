"""Doc 02 proposal figures: where each function of the tray-assignment call tree goes."""
from __future__ import annotations

from components import chip, connect, frame, label_pill
from registry import figure
from svgkit import BBox, Doc, text_width
from theme import T, S

DOC2 = "02-issue-and-proposal.md"
W = 1120
ROW = 24


def _item(d: Doc, x, y, new: str, old: str | None, *, col=T.fg, size=12.5):
    runs = [(new, "mono", 600, col)]
    if old:
        runs.append(("   // " + old, "mono", 400, T.faint))
    d.rich(x, y, runs, size=size)


def _band(d: Doc, y, h, color, title, sub):
    d.rect(0, y, W, h, rx=12, fill=T.tint(color, 0.06, T.bg), stroke=T.tint(color, 0.7, T.bg), sw=1.4,
           layer="under")
    c = chip(d, 18, y + 22, title, color, size=12)
    d.text(c.x1 + 12, y + 22, sub, size=S.small + 0.5, fill=T.muted)
    return y + 46


def _file_card(d: Doc, x, y, w, name, items, color):
    n = sum(2 if old else 1 for _, old in items)
    h = 40 + n * 20 + 8
    d.rect(x, y, w, h, rx=9, fill=T.card, stroke=T.tint(color, 0.55, T.bg), sw=1.2)
    d.text(x + 14, y + 18, name, size=11.5, family="mono", weight=600, fill=color)
    yy = y + 42
    for new, old in items:
        d.text(x + 14, yy, new, size=12, family="mono", weight=600, fill=T.fg)
        yy += 20
        if old:
            d.text(x + 30, yy - 2, "// " + old, size=11.5, family="mono", fill=T.faint)
            yy += 20
    return BBox(x, y, x + w, y + h)


@figure("57_tray_tree_placement", "Where the tray call tree goes", DOC2)
def tray_tree_placement():
    d = Doc("57_tray_tree_placement", "Where each function of the tray call tree goes",
            "Four layers: Scheduler keeps orchestration and the single write to ctx; DefaultSolver runs the loop; "
            "a private Pass holds the only mutable state; everything else becomes a pure free function.")
    SCH, CLS, PASS, PURE = T.sky, T.amber, T.violet, T.green

    # band 1: Scheduler
    y = _band(d, 0, 132, SCH, "stays in Scheduler", "scheduler.cpp; owns gg_, table_, cost_model_, layout_ and services_")
    _item(d, 24, y + 4, "Plan()", "Solve(), then ApplyTrayAssignment()")
    _item(d, 24, y + 4 + ROW, "ApplyTrayAssignment(ctx&, result) -> stdx::Result", "new: replays Result, cycle check")
    _item(d, 24, y + 4 + 2 * ROW, "Plan<Type>Job() (12 job methods)", "call the shared pure helpers below")
    b1 = BBox(0, 0, W, 132)

    # band 2: DefaultSolver
    y2 = b1.y1 + 46
    y = _band(d, y2, 84, CLS, "tray_assignment::DefaultSolver", "class; holds const GarageServices&; no other state")
    _item(d, 24, y + 4, "Solve(const Input&) const -> stdx::Expected<Result>",
          "was DoTrayAssignments(ctx); only the loop remains")
    b2 = BBox(0, y2, W, y2 + 84)

    # band 3: Pass
    y3 = b2.y1 + 46
    y = _band(d, y3, 156, PASS, "Pass (private)",
              "created inside Solve, destroyed on return: working_state, freeing_moves, last_tray_event, result_")
    _item(d, 24, y + 4, "RecordTransition(event) -> stdx::Result", "was ApplyTransitionToFreeingMoves")
    _item(d, 24, y + 4 + ROW, "EmitMoveChain(moves, root)",
          "was duplicated in DoTrayAssignments and AssignDest...")
    _item(d, 24, y + 4 + 2 * ROW, "CommitRootMove(event, resolved) -> stdx::Result",
          "was the tail of both")
    _item(d, 24, y + 4 + 3 * ROW, "Fill(event, tray_id, dest)", "was move->SetTrayId / SetDest on the input")
    b3 = BBox(0, y3, W, y3 + 156)

    # band 4: pure functions, four file cards in a 2 x 2 grid
    y4 = b3.y1 + 46
    top = y4 + 46
    cw = (W - 24 * 2 - 20) / 2
    c1 = _file_card(d, 24, top, cw, "tray_assignment/empty_tray.cpp  (public)", [
        ("ChooseEmptyTray(svc, state, dest)", "was AssignTrayIdForEmptyMove"),
        ("TrayChoice{tray_id, dest}  (the returned value)", None)], PURE)
    c2 = _file_card(d, 24 + cw + 20, top, cw, "common/headings.cpp  (public, shared)", [
        ("PreferredHeading(svc, dest, payload)", "was UsePreferredHeading"),
        ("RetrievalHeading(svc, dest, payload)", "was UseRetrievalHeading"),
        ("EvChargeHeading(layout, node_id)", "was UseEvChargeHeading")], PURE)
    top2 = max(c1.y1, c2.y1) + 18
    c3 = _file_card(d, 24, top2, cw, "tray_assignment/blocking_trays.cpp  (public)", [
        ("ResolveBlockingTrays(svc, request)", "was a member, same name"),
        ("ChooseParkingSpot(svc, state, tray, job)", "was 1st half of AssignDestForUntargetedMove"),
        ("detail::FindOpenSpace(svc, query)", "was FindOpenSpaceForRootTray"),
        ("detail::TryResolveBlocker(svc, ...)", "was TryFindBlockingTrayResolution")], PURE)
    c4 = _file_card(d, 24 + cw + 20, top2, cw, "tray_assignment/critical_path.cpp  (private)", [
        ("CheckDestinationUsable(svc, state, dest)", "was inline in the main loop"),
        ("FindCriticalPath(svc, state, tray, dest)", "was inline in the main loop"),
        ("TryAdvanceRoot(svc, state, path, at)", "was fallback 1, inline"),
        ("BlockersOnPath(svc, state, tray, path)", "was the re-scan, inline")], PURE)
    h4 = max(c3.y1, c4.y1) + 18 - y4
    _band(d, y4, h4, PURE, "pure free functions",
          "namespace tray_assignment; output depends only on the arguments; inputs passed by const& or value")
    b4 = BBox(0, y4, W, y4 + h4)

    # calls between layers (left margin)
    for a, b, lab in ((b1, b2, "Solve(input)"), (b2, b3, "owns one Pass per call"), (b3, b4, "calls")):
        connect(d, [(80, a.y1), (80, b.y0)], kind="flow", color=T.fg2, label=lab, label_at=(80, (a.y1 + b.y0) / 2),
                label_anchor="start")
    # shared helpers: Scheduler job methods -> pure functions (right margin)
    xr = W - 60
    connect(d, [(xr, b1.y1), (xr, b4.y0)], kind="flow", color=SCH, dash="6 4",
            label="job methods call these directly", label_at=(xr, (b2.y1 + b3.y0) / 2), label_anchor="end")
    frame(d, title="Where each function of the tray call tree goes",
          subtitle="Today every function here is a Scheduler member (grey comments). After the refactor, mutation is "
                   "confined to the top layer (writes ctx) and to Pass (private to one Solve call).",
          badge_key="proposed",
          legend=[("box", SCH, "Scheduler: orchestration, writes ctx"), ("box", CLS, "solver class"),
                  ("box", PASS, "pass-local mutable state"), ("box", PURE, "pure free function"),
                  ("arrow", T.fg2, "calls")],
          footnote="Grey // comments name the scheduler.cpp function or code block each one replaces. 'svc' is a "
                   "const GarageServices& (graph, collision table, cost model, layout, logger).")
    return d
