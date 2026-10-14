"""Chapter 03 figures: wait removal, candidate index + binary search, why the latest candidate is
enough, and the final sparse ADG."""
from __future__ import annotations

import bisect

from adg import (Action, actions_from_paths, closure, conflicts, drop_waits, latest_candidate, redundant_edges,
                 type1, type2_cp, type2_exhaustive, type2_scp, type2_scp_as_printed)
from adgdraw import Lanes, ARROW
from components import chip, connect, frame, label_pill, note, num_badge
from keys import action_rows, key_panel
from registry import figure
from svgkit import BBox, Doc, text_width, wrap
import example as ex
from theme import S, T

DOC = "chapters/03-scp-illustrated.md"
A = ex.A
FOCUS = T.teal


def _panel_title(d, x, y, s, sub=None):
    d.text(x, y, s, size=13.5, weight=600, fill=T.fg)
    if sub:
        for i, ln in enumerate(wrap(sub, 560, 12, "sans")):
            d.text(x, y + 22 + i * 17, ln, size=12, fill=T.muted)
        return y + 22 + len(wrap(sub, 560, 12, "sans")) * 17 + 8
    return y + 26


# --------------------------------------------------------------------------------------
@figure("12-wait-removal", "Why every edge touching a wait is redundant", DOC)
def wait_removal():
    d = Doc("12-wait-removal", "Why every edge touching a wait is redundant")
    E = ex.T2_FULL
    # Theorem 2: edge INTO a wait  (L0 -> M1)
    assert (A["A1-0"], A["A3-1"]) in E and (A["A1-0"], A["A3-0"]) in E
    # Theorem 1: edge OUT of a wait (M1 -> N2)
    assert (A["A3-1"], A["A4-2"]) in E and (A["A3-2"], A["A4-2"]) in E

    def panel(x0, y0, robots, acts, red, path_edges, title, sub, tmax):
        yy = _panel_title(d, x0, y0, title, sub)
        L = Lanes(d, x0, yy, robots, ex.COLOR, tmax, col_w=170, label_w=92, lane_h=82, axis=True)
        for a in acts:
            L.action(a, style="focus" if a.wait else "normal")
        for a in acts:
            for b in acts:
                if (a, b) in ex.T1_FULL:
                    on = (a, b) in path_edges
                    L.type1(a, b, color=FOCUS if on else None, sw=2.4 if on else 1.6)
        t2 = [e for e in E if e[0] in acts and e[1] in acts]

        def st(c, a):
            if (c, a) in red:
                return {"color": T.red, "dash": "6 4", "sw": 1.8}
            if (c, a) in path_edges:
                return {"color": FOCUS, "sw": 2.4}
            return {"color": T.faint}
        L.type2(t2, style=st)
        return BBox(x0, y0, x0 + L.W, L.y1)

    b1 = panel(0, 0, ["A1", "A3"], [A["A1-0"], A["A1-1"], A["A3-0"], A["A3-1"], A["A3-2"]],
               {(A["A1-0"], A["A3-1"])}, {(A["A1-0"], A["A3-0"]), (A["A3-0"], A["A3-1"])},
               "(a) Edge INTO a wait  ·  Theorem 2",
               "AGV-3 waits at W18 (A3-1). A1-0 left W18, so the rule adds A1-0 → A3-1. But AGV-3 had to ENTER W18 first (A3-0), "
               "and the same rule already gave A1-0 → A3-0. Path A1-0 → A3-0 → A3-1 makes the red edge redundant.",
               2)
    b2 = panel(b1.x1 + 40, 0, ["A3", "A4"], [A["A3-1"], A["A3-2"], A["A4-1"], A["A4-2"]],
               {(A["A3-1"], A["A4-2"])}, {(A["A3-1"], A["A3-2"]), (A["A3-2"], A["A4-2"])},
               "(b) Edge OUT of a wait  ·  Theorem 1",
               "AGV-4 enters W18 later (A4-2), so the rule adds A3-1 → A4-2 (AGV-3's wait 'leaves' W18). But AGV-3's next move "
               "A3-2 really leaves W18, and gives A3-2 → A4-2. Path A3-1 → A3-2 → A4-2 makes the red edge "
               "redundant.", 2)
    # bottom: contraction of the lanes
    y = max(b1.y1, b2.y1) + 40
    yy = _panel_title(d, 0, y, "(c) So the waits can go: contract each lane",
                      "With every type-2 edge on A3-1 and A4-1 redundant, delete the two wait vertices and join the "
                      "neighbours with a type-1 edge. Here A3-0 → A3-2 and A4-0 → A4-2.")
    L = Lanes(d, 0, yy, ["A3", "A4"], ex.COLOR, 2, col_w=170, label_w=92, lane_h=82, axis=False)
    for a in (A["A3-0"], A["A3-2"], A["A4-0"], A["A4-2"]):
        L.action(a)
    L.action(A["A3-1"], style="ghost")
    L.action(A["A4-1"], style="ghost")
    L.type1(A["A3-0"], A["A3-2"], color=FOCUS, sw=2.2)
    L.type1(A["A4-0"], A["A4-2"], color=FOCUS, sw=2.2)
    note(d, L.x0 + L.W + 40, yy, 470,
         "Only the GRAPH loses the wait. AGV-3 still stands at W18: if AGV-2 is slow, AGV-3 simply does not get the "
         "'go' for A3-2 yet. The wait now emerges from the dependencies instead of being a 1-step timer, so AGV-3 can "
         "go the moment A2-2 is done.", title="What does not change", accent=T.amber)
    key_panel(d, 0, max(L.y1, yy + 120) + 24, b2.x1, "How to read this figure", action_rows() + [
        ("red dashed", "a type-2 edge that touches a wait and is implied by another path", T.red),
        ("teal path", "the path of other edges that already gives the same order", FOCUS)])
    frame(d, title="Why every edge touching a wait is redundant",
          subtitle="Wait actions (start = goal) appear in the original ADG of figure 2.4 with three type-2 edges: "
                   "A1-0 → A3-1, A3-1 → A4-2 and A3-0 → A4-1. For each one, the paper shows that a path through "
                   "a neighbouring move already enforces the same order.",
          badge_key="illustrative",
          legend=[("dasharrow", T.red, "edge on a wait (redundant)"), ("arrow", FOCUS, "path that replaces it"),
                  ("arrow", T.faint, "other edges"), ("dashbox", T.fg2, "wait action")],
          footnote="A3-0 → A4-1 (AGV-3 leaves W13, AGV-4 waits at W13) is the third case; it is replaced by A3-0 → A4-0 "
                   "→ A4-1, exactly as in panel (a). All edges computed by scripts/adg/adg.py.")
    return d


# --------------------------------------------------------------------------------------
@figure("13-candidate-index", "Candidate partitioning and the binary search", DOC)
def candidate_index():
    d = Doc("13-candidate-index", "Candidate partitioning and the binary search")
    S_ = ex.INDEX
    # ---- left: the whole index
    _panel_title(d, 0, 0, "1 · Build S: for every place v, the moves that START at v, sorted by t")
    order = ["W8", "W13", "W18", "W22", "W25", "B21", "W41"]
    y = 40
    rows = {}
    for v in order:
        lst = S_.get(v, [])
        if not lst:
            continue
        hl = v == ex.JUNCTION
        d.text(0, y + 15, f"S[{v}]", size=12.5, family="mono", weight=600, fill=FOCUS if hl else T.fg2)
        x = 70
        for i, c in enumerate(lst):
            lab = f"{c.id}  t={c.t}"
            w = text_width(lab, 11.5, "mono", 600) + 20
            col = ex.COLOR[c.R]
            d.rect(x, y + 2, w, 26, rx=13, fill=T.tint(col, 0.16, T.bg), stroke=col, sw=1.2)
            d.text(x + 10, y + 15, lab, size=11.5, family="mono", weight=600, fill=col)
            x += w + 8
        if hl:
            d.rect(-8, y - 4, x + 4, 38, rx=8, fill="none", stroke=FOCUS, sw=1.2, dash="4 3")
        rows[v] = y
        y += 42
    d.text(0, y + 6, f"One pass over the {len(ex.MOVES)} moves fills S; each list is sorted once.", size=11.5,
           fill=T.muted)
    left_h = y + 20

    # ---- right: the query for N3
    a = A["A4-3"]
    C = S_[a.g]
    x0 = 540
    _panel_title(d, x0, 0, f"2 · Query for one target: a = {a.id} ({a.s} {ARROW} {a.g}, t = {a.t}, AGV-{a.R[1:]})")
    steps = [
        f"a enters {a.g}, so only moves that LEAVE {a.g} can be its type-2 source:",
        f"look up S[{a.g}] instead of scanning all moves.",
    ]
    for i, s in enumerate(steps):
        d.text(x0, 34 + i * 18, s, size=12, fill=T.fg2)
    cw, ch = 122, 54
    ly = 112
    for i, c in enumerate(C):
        cx = x0 + i * (cw + 10)
        col = ex.COLOR[c.R]
        elig = c.t <= a.t and c.R != a.R
        d.rect(cx, ly, cw, ch, rx=8, fill=T.card if c.t <= a.t else T.bg, stroke=col, sw=1.4,
               opacity=None if c.t <= a.t else 0.45)
        d.text(cx + 10, ly + 16, f"[{i}] {c.id}", size=11.5, family="mono", weight=700, fill=col)
        d.text(cx + 10, ly + 37, f"t = {c.t}  {c.s}{ARROW}{c.g}", size=11, family="mono", fill=T.fg2)
    times = [c.t for c in C]
    k0 = bisect.bisect_right(times, a.t)
    c_sel, kk0, k = latest_candidate(C, a)
    assert kk0 == k and c_sel.id == "A3-3"
    # bracket for t <= a.t
    bx1 = x0 + k0 * (cw + 10) - 10
    d.path(f"M{x0} {ly + ch + 10} L{x0} {ly + ch + 18} L{bx1} {ly + ch + 18} L{bx1} {ly + ch + 10}",
           stroke=T.fg2, sw=1.2)
    d.text((x0 + bx1) / 2, ly + ch + 34, f"t ≤ {a.t}: eligible by time", size=11.5, fill=T.fg2, anchor="middle")
    # bisect pointer
    px = x0 + k0 * (cw + 10) - 5
    d.line(px, ly - 22, px, ly + ch + 4, stroke=T.amber, sw=1.6, dash="4 3")
    d.text(px, ly - 32, f"bisect_right(times, {a.t}) = {k0}", size=11.5, family="mono", weight=600, fill=T.amber,
           anchor="middle")
    lines = [
        ("times = [" + ", ".join(str(t) for t in times) + f"],  a.t = {a.t}", T.fg2),
        (f"k = {k0} - 1 = {k}  →  C[{k}] = {c_sel.id}, AGV-{c_sel.R[1:]} ≠ AGV-{a.R[1:]}  ✓", T.fg2),
        (f"CP  adds every eligible one:  " + ", ".join(f"{c.id}{ARROW}{a.id}" for c in C if c.t <= a.t and c.R != a.R),
         T.muted),
        (f"SCP adds only the latest:     {c_sel.id}{ARROW}{a.id}", FOCUS),
    ]
    for i, (s, col) in enumerate(lines):
        d.text(x0, ly + ch + 66 + i * 22, s, size=12, family="mono", weight=600 if col == FOCUS else 400, fill=col)
    # complexity strip
    yb = max(left_h, ly + ch + 66 + 4 * 22) + 34
    stats = [
        ("Algorithm 1", f"{len(ex.MOVES)} × {len(ex.MOVES)} = {len(ex.MOVES) ** 2} pair checks", "O(n²)", T.red),
        ("CP (Alg. 2)", f"{sum(len(S_.get(m.g, [])) for m in ex.MOVES)} candidate checks", "O(n²) worst case",
         T.amber),
        ("SCP (Alg. 3)", f"{len(ex.MOVES)} binary searches", "O(n log n)", FOCUS),
    ]
    for i, (n, s, o, col) in enumerate(stats):
        x = i * 340
        d.rect(x, yb, 320, 64, rx=10, fill=T.card, stroke=col, sw=1.3)
        d.text(x + 14, yb + 20, n, size=13, weight=600, fill=col)
        d.text(x + 306, yb + 20, o, size=12, family="mono", weight=600, fill=col, anchor="end")
        d.text(x + 14, yb + 44, s, size=12, family="mono", fill=T.fg2)
    key_panel(d, 0, yb + 84, 1000, "Symbols in this figure", [
        ("S[v]", "the index: list of all moves that START at place v, sorted by time step t", T.fg2),
        ("A1-1  t=1", "one entry: AGV-1's step 1, planned for t = 1 (colour = AGV)", T.sky),
        ("a", "the target action we are finding a type-2 source for; a.g is the place it enters", T.fg2),
        ("bisect_right", "binary search: the position just after the last entry with t <= a.t", T.amber),
        ("C[k]", "entry number k of the list C = S[a.g] (counting from 0)", T.fg2),
        ("n", "number of actions; O(n log n) means the work grows only a little faster than n", T.fg2)])
    frame(d, title="Candidate partitioning and the binary search",
          subtitle="The type-2 rule c.s = a.g means a target only ever needs the moves that leave its own goal "
                   "place. Group the moves by start place once (CP); sort each group by time and binary-search "
                   "it (SCP).",
          badge_key="illustrative",
          legend=[("box", ex.COLOR[r], f"AGV-{r[1:]}") for r in ex.ROBOTS] + [("dash", T.amber, "insertion point of a.t")],
          footnote=f"Counts are for the {len(ex.MOVES)} moves of the worked example after wait removal. At this size "
                   "the difference is cosmetic; the paper's benchmarks go up to 900 agents, where it is not.")
    return d


# --------------------------------------------------------------------------------------
@figure("14-why-latest", "Why the latest candidate is enough (Theorem 3)", DOC)
def why_latest():
    d = Doc("14-why-latest", "Why the latest candidate is enough")
    # chain at vertex C: L1 -> X1 -> X2 -> M2 -> M3 -> N3
    chain = [A["A1-1"], A["A2-1"], A["A2-2"], A["A3-2"], A["A3-3"], A["A4-3"]]
    T1 = ex.T1
    SCP = ex.T2_SCP
    for u, v in zip(chain, chain[1:]):
        assert (u, v) in T1 or (u, v) in SCP, (u, v)
    yy = _panel_title(d, 0, 0, "(a) The hand-over chain at the junction W22",
                      "Read left to right: AGV-1 leaves W22 (A1-1); AGV-2 enters W22 (A2-1) and leaves (A2-2); AGV-3 enters (A3-2) and "
                      "leaves (A3-3); AGV-4 enters (A4-3). Every link is an edge SCP keeps.")
    L = Lanes(d, 0, yy, ex.ROBOTS, ex.COLOR, 3, col_w=176, label_w=92, lane_h=74, axis=True)
    for a in chain:
        L.action(a, style="focus" if a.id == "A4-3" else "normal")
    for u, v in zip(chain, chain[1:]):
        if (u, v) in T1:
            L.type1(u, v, color=FOCUS, sw=2.4)
    keep = [(u, v) for u, v in zip(chain, chain[1:]) if (u, v) in SCP]
    pruned = [(c, a) for (c, a) in ex.T2_CP - ex.T2_SCP if c in chain and a in chain]
    assert {(A["A1-1"], A["A4-3"]), (A["A2-2"], A["A4-3"]), (A["A1-1"], A["A3-2"])} <= set(pruned)

    def st(c, a):
        if (c, a) in pruned:
            return {"color": T.red, "dash": "6 4", "sw": 1.6, "pill": False}
        return {"color": FOCUS, "sw": 2.4}
    L.type2(keep + pruned, style=st)
    note(d, L.x0 + L.W + 30, yy, 340,
         "S[W22] = [A1-1, A2-2, A3-3, A4-4]. Between two consecutive leavers of W22, someone must have entered it (here "
         "A2-1, then A3-2). That entering move got an edge from the previous leaver, and its own AGV's type-1 chain "
         "leads to the next leaver. So A1-1 reaches A2-2 and A2-2 reaches A3-3, and one edge A3-3 → A4-3 is enough.",
         title="The argument in words", accent=FOCUS)
    # (b) own robot case
    y2 = L.y1 + 40
    yy2 = _panel_title(d, 0, y2, "(b) Corner case: the latest candidate is the target's own AGV",
                       "A separate tiny plan on four places u, v, w, x: AGV-5 leaves v at t = 1; AGV-6 enters v (A6-1), leaves to w "
                       "(A6-2) and comes back (A6-3). For A6-3, S[v] = [A5-1, A6-2]: the search lands on A6-2, AGV-6 itself.")
    paths = {"A5": ["v", "v", "x"], "A6": ["u", "u", "v", "w", "v"]}
    assert not conflicts(paths)
    acts = drop_waits(actions_from_paths(paths))
    ids = {a.id: a for a in acts}
    t1 = type1(acts)
    printed, walk = type2_scp_as_printed(acts), type2_scp(acts)
    extra = walk - printed
    assert extra == {(ids["A5-1"], ids["A6-3"])}
    assert (ids["A5-1"], ids["A6-3"]) in redundant_edges(set(acts), t1 | walk)
    cols = {"A5": T.amber, "A6": T.teal}
    L2 = Lanes(d, 0, yy2, ["A5", "A6"], cols, 3, col_w=176, label_w=92, lane_h=74, axis=True,
               lane_labels={"A5": "AGV-5", "A6": "AGV-6"})
    for a in acts:
        L2.action(a, style="focus" if a.id == "A6-3" else "normal")
    for u, v in sorted(t1):
        L2.type1(u, v, sw=2.2)

    def st2(c, a):
        if (c, a) in extra:
            return {"color": T.red, "dash": "6 4", "sw": 1.6, "pill": False}
        return {"color": T.fg2, "sw": 2}
    L2.type2(printed | extra, style=st2)
    note(d, L2.x0 + L2.W + 30, yy2, 340,
         "Read literally, Algorithm 3 adds no edge for A6-3 when C[k] is AGV-6's own move, and that is safe: A5-1 → A6-1 "
         "→ A6-2 → A6-3 already orders A5-1 before A6-3. Walking back to A5-1 instead (as Theorem 3's wording suggests, "
         "red) only adds a redundant edge. A 1835-plan random test in scripts/adg/ confirms both variants keep "
         "every ordering.",
         title="Skipping is safe", accent=T.amber)
    key_panel(d, 0, L2.y1 + 24, L.W + 30 + 340, "Symbols in this figure", [
        ("A1-1 → A2-1", "a type-2 edge: A2-1 may start only after A1-1 has completed (pill: the place handed over)", T.fg2),
        ("A2-1 → A2-2", "a type-1 edge: the same AGV does its steps in order", FOCUS),
        ("dashed box", "the target action whose incoming edges we examine", FOCUS),
        ("u v w x", "panel (b) only: four places of a separate, made-up mini garage", T.fg2),
        ("AGV-5, AGV-6", "panel (b) only: two AGVs of that mini garage", T.fg2)])
    frame(d, title="Why the latest candidate is enough (Theorem 3)",
          subtitle="Every move that leaves a place is ordered after every earlier move that left it, through the "
                   "AGVs that entered in between. So a target only needs an edge from the most recent leaver; "
                   "edges from older leavers (red, added by CP) are implied.",
          badge_key="illustrative",
          legend=[("arrow", FOCUS, "edge kept by SCP"), ("dasharrow", T.red, "implied by a path: not needed"),
                  ("box", FOCUS, "target action")])
    return d


# --------------------------------------------------------------------------------------
@figure("15-adg-scp", "The ADG after both improvements", DOC)
def adg_scp():
    d = Doc("15-adg-scp", "The ADG after both improvements")
    L = Lanes(d, 0, 0, ex.ROBOTS, ex.COLOR, max(a.t for a in ex.ACTIONS))
    for a in ex.ACTIONS:
        L.action(a, style="ghost" if a.wait else "normal")
    for u, v in sorted(ex.T1):
        L.type1(u, v)
    pruned = ex.T2_CP - ex.T2_SCP
    still = redundant_edges(set(ex.MOVES), ex.T1 | ex.T2_SCP)
    assert still == {(A["A2-1"], A["A4-4"])}

    def st(c, a):
        if (c, a) in pruned:
            return {"color": T.tint(T.red, 0.75, T.bg), "dash": "5 4", "sw": 1.3, "pill": False}
        if (c, a) in still:
            return {"color": T.amber, "sw": 1.8}
        return {"color": T.fg2, "sw": 1.8}
    L.type2(ex.T2_SCP | pruned, style=st)
    n_full, n_cp, n_scp = len(ex.T2_FULL), len(ex.T2_CP), len(ex.T2_SCP)
    key_panel(d, 0, L.y1 + 20, L.W, "How to read this graph", action_rows(wait=False) + [
        ("faint box", "a wait action that has been removed; its AGV still stands still there", T.faint)])
    frame(d, title="The ADG after both improvements: no waits, at most one type-2 edge per action",
          subtitle=f"Type-2 edges: {n_full} in the original ADG (figure 2.4)  →  {n_cp} after dropping the "
                   f"two waits (CP finds exactly these)  →  {n_scp} with SCP. Red dashed: the {len(pruned)} "
                   f"edges SCP skips; each is implied by a path of solid edges.",
          badge_key="illustrative",
          legend=[("arrow", T.fg2, "type-2 kept by SCP"), ("dasharrow", T.red, "skipped by SCP (implied)"),
                  ("arrow", T.amber, "kept, yet still implied"), ("dashbox", T.faint, "removed wait")],
          footnote="SCP is not a full transitive reduction: A2-1 → A4-4 (amber) is still implied by "
                   "A2-1 → A2-2 → A3-2 → A3-3 → A4-3 → A4-4, because it is the only (hence latest) "
                   "candidate in S[W41]. In a 1835-plan random test, 15% of SCP graphs kept at least one such edge. "
                   "Harmless for correctness; it only means 'at most one type-2 edge per action', not 'minimal'.")
    return d
