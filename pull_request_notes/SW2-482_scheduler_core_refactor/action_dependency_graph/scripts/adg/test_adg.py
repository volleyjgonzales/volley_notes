#!/usr/bin/env python3
"""Checks for adg.py.

1. The worked example (chapters 01-03): prints its actions and edge counts and checks the numbers
   quoted in the text.
2. A randomised test: many small valid MAPF plans (prioritized planning on random grids). For each,
   the ADG after wait removal + SCP must keep every ordering of the exhaustive ADG (Algorithm 1
   with waits). Both SCP variants are tested: as printed (skip when the latest candidate is the
   target's own robot) and walk-back.

    python3 scripts/adg/test_adg.py            # a few seconds
    python3 scripts/adg/test_adg.py 300        # fewer random trials
"""
from __future__ import annotations

import random
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adg import (actions_from_paths, at, closure, conflicts, drop_waits, is_acyclic, redundant_edges,  # noqa: E402
                 type1, type2_cp, type2_exhaustive, type2_scp, type2_scp_as_printed)

EXAMPLE = {   # same plan as scripts/diagrams/example.py
    "A1": ["W18", "W22", "W25", "W26"],
    "A2": ["B21", "W41", "W22", "P23"],
    "A3": ["W13", "W18", "W18", "W22", "W25"],
    "A4": ["W8", "W13", "W13", "W18", "W22", "W41"],
}


def preserves(acts, full_edges, moves, edges):
    rf = closure(acts, full_edges)
    rr = closure(moves, edges)
    ms = set(moves)
    return all((rf[u] & ms) <= rr[u] for u in moves)


def worked_example():
    assert not conflicts(EXAMPLE)
    acts = actions_from_paths(EXAMPLE)
    full = type1(acts) | type2_exhaustive(acts)
    m = drop_waits(acts)
    cp, scp = type2_cp(m), type2_scp(m)
    print(f"worked example: {len(acts)} actions ({len(acts) - len(m)} waits)")
    print(f"  type-2 edges: Algorithm 1 = {len(type2_exhaustive(acts))}, after wait removal = {len(cp)}, "
          f"SCP = {len(scp)}")
    print("  SCP edges:", ", ".join(f"{c.id}->{a.id}" for c, a in sorted(scp, key=lambda e: (e[1].t, e[1].R))))
    print("  skipped by SCP:", ", ".join(f"{c.id}->{a.id}" for c, a in sorted(cp - scp, key=lambda e: e[1].id)))
    red = redundant_edges(set(m), type1(m) | scp)
    print("  still redundant after SCP:", ", ".join(f"{c.id}->{a.id}" for c, a in red))
    assert (len(type2_exhaustive(acts)), len(cp), len(scp)) == (15, 12, 8)
    assert type2_cp(m) == type2_exhaustive(m)
    assert is_acyclic(acts, full)
    assert preserves(acts, full, m, type1(m) | scp)


def _grid(w, h, holes):
    G = {}
    for x in range(w):
        for y in range(h):
            if (x, y) in holes:
                continue
            G[(x, y)] = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                         if 0 <= x + dx < w and 0 <= y + dy < h and (x + dx, y + dy) not in holes]
    return G


def _plan(G, s, g, reserved, H):
    def occ(v, t):
        return any(at(p, t) == v for p in reserved)

    def swap(u, v, t):
        return any(at(p, t) == v and at(p, t + 1) == u for p in reserved)
    q = deque([(s, 0, [s])])
    seen = {(s, 0)}
    while q:
        v, t, p = q.popleft()
        if v == g and all(not occ(g, tt) for tt in range(t, H + 5)):
            return p
        if t >= H:
            continue
        nb = G[v] + [v]
        random.shuffle(nb)
        for w in nb:
            if occ(w, t + 1) or swap(v, w, t) or (w, t + 1) in seen:
                continue
            seen.add((w, t + 1))
            q.append((w, t + 1, p + [w]))
    return None


def randomised(trials=3000, seed=1):
    random.seed(seed)
    n = ok_printed = ok_walk = reduced = differ = 0
    for _ in range(trials):
        w, h = random.randint(3, 5), random.randint(2, 4)
        holes = {(random.randrange(w), random.randrange(h)) for _ in range(random.randint(0, 2))}
        G = _grid(w, h, holes)
        V = list(G)
        k = random.randint(2, min(6, len(V) // 2))
        random.shuffle(V)
        starts, goals = V[:k], V[k:2 * k]
        paths = {}
        for i, (s, g) in enumerate(zip(starts, goals)):
            p = _plan(G, s, g, list(paths.values()) + [[starts[j]] for j in range(i + 1, k)], 14)
            if p is None:
                break
            paths[i] = p
        if len(paths) < k or conflicts(paths):
            continue
        acts = actions_from_paths(paths)
        full = type1(acts) | type2_exhaustive(acts)
        if not is_acyclic(acts, full):
            continue
        n += 1
        m = drop_waits(acts)
        assert type2_cp(acts) == type2_exhaustive(acts)
        printed, walk = type2_scp_as_printed(m), type2_scp(m)
        ok_printed += preserves(acts, full, m, type1(m) | printed)
        ok_walk += preserves(acts, full, m, type1(m) | walk)
        differ += printed != walk
        reduced += not redundant_edges(set(m), type1(m) | walk)
    print(f"random plans tested: {n}")
    print(f"  SCP, skip variant (literal pseudocode) keeps every ordering: {ok_printed}/{n}")
    print(f"  SCP with walk-back keeps every ordering: {ok_walk}/{n}  (variants differ on {differ} plans)")
    print(f"  SCP graph has no redundant edge at all: {reduced}/{n}  ({100 * (n - reduced) / n:.0f}% keep one or more)")
    assert ok_printed == n and ok_walk == n


if __name__ == "__main__":
    worked_example()
    randomised(int(sys.argv[1]) if len(sys.argv) > 1 else 3000)
