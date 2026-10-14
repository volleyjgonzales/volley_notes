"""Chapter 03 execution figures: why dropping waits can save time, and what an executor tracks."""
from __future__ import annotations

from collections import defaultdict

from adg import execute
from adgdraw import Lanes
from components import connect, frame, label_pill, note
from fig_adg import gantt, robot_legend
from garage import Garage
from keys import action_rows, key_panel
from scene import draw_robot, sched_positions
from registry import figure
from svgkit import BBox, Doc, text_width
import example as ex
from theme import S, T

DOC = "chapters/03-scp-illustrated.md"
FAST = {"A1": 0.5, "A2": 0.5}


def _dur(a):
    return 1.0 if a.wait else FAST.get(a.R, 1.0)


@figure("16-waits-throughput", "Planned waits vs emergent waits when AGVs run early", DOC)
def waits_throughput():
    d = Doc("16-waits-throughput", "Planned waits vs emergent waits")
    w = execute(ex.ACTIONS, ex.T1_FULL | ex.T2_FULL, _dur)
    n = execute(ex.MOVES, ex.T1 | ex.T2_SCP, _dur)
    mw, mn = max(e for _, e in w.values()), max(e for _, e in n.values())
    assert mn < mw
    tmax = int(mw) + 1
    b1 = gantt(d, 0, 0, w, title=f"(a) Original ADG with wait actions: makespan {mw:g} s", tmax=tmax)
    b2w = w[ex.A["A3-2"]][0]
    label_pill(d, 70 + b2w * 78, b1.y1 + 6, f"A3-2 starts at {b2w:g} s: AGV-2 left W22 at {w[ex.A['A2-2']][1]:g} s, but AGV-3's "
               "1-s wait A3-1 must run out first", color=T.amber, size=11.5, family="sans", border=T.amber,
               anchor="start")
    b2 = gantt(d, 0, b1.y1 + 44, n, title=f"(b) Waits removed, SCP edges: makespan {mn:g} s", tmax=tmax)
    b2n = n[ex.A["A3-2"]][0]
    label_pill(d, 70 + b2n * 78, b2.y1 + 6, f"A3-2 starts at {b2n:g} s, the moment A2-2 completes",
               color=T.green, size=11.5, family="sans", border=T.green, anchor="start")
    for b, m in ((b1, mw), (b2, mn)):
        x = 70 + m * 78
        d.line(x, b.y0 + 20, x, b.y1 - 14, stroke=T.red if m == mw else T.green, sw=1.6, dash="5 4", layer="over")
    key_panel(d, 0, b2.y1 + 34, b2.x1, "How to read the bars", [
        ("A3-2 W18→W22", "one action as a bar: AGV-3's step 2, from W18 to W22; length = how long it took", T.green),
        ("A3-1 wait", "dashed bar: a planned wait action (1 s)", T.green),
        ("makespan", "the time at which the last AGV has finished (dashed vertical line)", T.red)])
    frame(d, title="Planned waits vs emergent waits when AGVs run early",
          subtitle="AGV-1 and AGV-2 are lightly loaded and need only 0.5 s per move; everything else takes 1 s, a wait "
                   "action also 1 s. With waits in the graph, AGV-3 and AGV-4 still sit out their full planned waits. Without "
                   "them, AGV-3 and AGV-4 wait exactly as long as the dependencies require, and the gain cascades down the "
                   "convoy.",
          badge_key="illustrative",
          legend=robot_legend([("dashbox", T.fg2, "wait action"), ("dash", T.red, "makespan")]),
          footnote="Same mechanism as the paper's section 4.2 experiment (there: 0.8 s for a move followed by "
                   "another move, 1 s otherwise). The gain only appears when AGVs are faster than planned; "
                   "when everyone is exactly on time both graphs give the same makespan.")
    return d


@figure("17-execution-snapshot", "What the executor knows at t = 3.5 s", DOC)
def snapshot():
    d = Doc("17-execution-snapshot", "Executor snapshot")
    E = ex.T1 | ex.T2_SCP
    sch = execute(ex.MOVES, E, lambda a: 1.0)
    tau = 3.5
    preds = defaultdict(set)
    for u, v in E:
        preds[v].add(u)
    state, missing = {}, {}
    for a in ex.MOVES:
        s, e = sch[a]
        if e <= tau:
            state[a] = "done"
        elif s <= tau:
            state[a] = "running"
        else:
            state[a] = "blocked"
            missing[a] = sorted(p.id for p in preds[a] if sch[p][1] > tau)
    L = Lanes(d, 0, 0, ex.ROBOTS, ex.COLOR, max(a.t for a in ex.ACTIONS))
    for a in ex.MOVES:
        st = state[a]
        if st == "done":
            L.action(a, style="dim", note="done")
        elif st == "running":
            L.action(a, style="focus", note="RUNNING")
        else:
            L.action(a, note=f"open {len(missing[a])}")
    for u, v in sorted(ex.T1):
        L.type1(u, v, color=T.faint if state[u] == "done" else None)

    def style(c, a):
        if state[c] == "done":
            return {"color": T.border, "pill": False}
        return {"color": T.fg2, "sw": 1.8}
    L.type2(ex.T2_SCP, style=style)
    # bookkeeping table
    x0 = L.x0 + L.W + 30
    d.text(x0, 6, "Dispatcher bookkeeping at 3.5 s", size=13.5, weight=600, fill=T.fg)
    rows = [(a, state[a]) for a in sorted(ex.MOVES, key=lambda a: sch[a])]
    for i, (a, st) in enumerate(rows):
        y = 38 + i * 25
        col = ex.COLOR[a.R]
        d.text(x0, y, a.id, size=12, family="mono", weight=700, fill=col)
        if st == "done":
            txt, c2 = "completed", T.faint
        elif st == "running":
            txt, c2 = "dispatched, running", T.teal
        else:
            txt, c2 = f"open preds {len(missing[a])}: " + ", ".join(missing[a]), T.fg2
        d.text(x0 + 40, y, txt, size=12, family="mono", fill=c2)
    note(d, x0, 38 + len(rows) * 25 + 6, 320,
         "When A2-2 reports 'done', the executor decrements the counter of each successor. A3-2 hits 0 and is sent "
         "to AGV-3. Nothing in this loop reads a clock.", title="Next event", accent=T.teal)
    # where everybody is
    yg = L.y1 + 24
    d.text(0, yg, "On the floor at 3.5 s: AGV-2 is leaving W22; AGV-3 waits at W18 for it, AGV-4 waits behind AGV-3",
           size=13.5, weight=600, fill=T.fg)
    G = Garage(d, 0, yg + 16, 26, xlim=(19.6, 46.6), ylim=(10.8, 25.6))
    G.base(labels=True, axes=False, context=False, highlight=("W22",), wp_below=True)
    for r, st in sched_positions(sch, tau).items():
        draw_robot(G, r, st["at"], st["heading"], label_side="right" if r != "A2" else "above")
    key_panel(d, 0, G.box.y1 + 24, max(G.box.x1, x0 + 340), "How to read this figure", action_rows(wait=False) + [
        ("done", "completed action (faded)", T.faint),
        ("RUNNING", "dispatched to its AGV and in progress", T.teal),
        ("open 1", "blocked: number of predecessors that have not completed yet", T.fg2)])
    frame(d, title="What the executor knows at t = 3.5 s",
          subtitle="Nominal run of the final ADG (every action 1 s). An action is dispatched when its count of "
                   "unfinished predecessors reaches 0; AGVs report completion; that is the whole protocol.",
          badge_key="illustrative",
          legend=[("box", T.faint, "completed"), ("box", T.teal, "running"), ("box", T.fg2, "blocked: waits on a predecessor"),
                  ("arrow", T.fg2, "edge still constraining something")],
          footnote="This nominal run needs 8 s although the plan had 5 steps: an ADG lets an AGV enter a place only "
                   "after the previous AGV's move out of it has completed, so the plan's 'following' moves become "
                   "sequential. How much that costs in practice depends on how long one move takes.")
    return d
