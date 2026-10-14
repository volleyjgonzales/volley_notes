"""Reference implementation of the ADG constructions in Dunkel (2024), used to compute every
edge drawn in the figures. Nothing in the figures is hand-placed: if this file says an edge
exists, the figure draws it; if not, it does not.

    python3 scripts/adg/test_adg.py   # worked example + randomised check against Algorithm 1

Conventions (paper, Definition 1):
    an action is <s, g, t, R>: start vertex, goal vertex, time step, robot.
    action at time t moves robot R from pi_R(t) to pi_R(t+1). A wait has s == g.
    edge a -> b means "b may start only after a has completed".
"""
from __future__ import annotations

import bisect
import itertools
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Action:
    R: str      # robot
    t: int      # time step
    s: str      # start vertex
    g: str      # goal vertex

    @property
    def wait(self) -> bool:
        return self.s == self.g

    @property
    def id(self) -> str:
        return f"{self.R}{self.t}"

    def __str__(self):
        return f"{self.id}:{self.s}->{self.g}"


# --------------------------------------------------------------------------------------
# Plans
# --------------------------------------------------------------------------------------

def actions_from_paths(paths: dict[str, list[str]]) -> list[Action]:
    """paths[R] = [pi_R(0), pi_R(1), ...]; one action per step until the goal is reached."""
    out = []
    for R, p in paths.items():
        for t in range(len(p) - 1):
            out.append(Action(R, t, p[t], p[t + 1]))
    return out


def at(path, t):
    return path[min(t, len(path) - 1)]   # robots stay on their goal after finishing


def conflicts(paths: dict[str, list[str]]):
    """Classic MAPF conflicts: vertex (same vertex, same t) and swap (exchange along one edge)."""
    T = max(len(p) for p in paths.values())
    out = []
    for i, j in itertools.combinations(paths, 2):
        for t in range(T):
            if at(paths[i], t) == at(paths[j], t):
                out.append(("vertex", i, j, at(paths[i], t), t))
            if t + 1 < T and at(paths[i], t) == at(paths[j], t + 1) and at(paths[j], t) == at(paths[i], t + 1) \
                    and at(paths[i], t) != at(paths[i], t + 1):
                out.append(("swap", i, j, (at(paths[i], t), at(paths[i], t + 1)), t))
    return out


# --------------------------------------------------------------------------------------
# Edges
# --------------------------------------------------------------------------------------

def type1(actions):
    """Consecutive actions of the same robot (Definition 3; after wait removal: consecutive
    *remaining* actions)."""
    by = defaultdict(list)
    for a in actions:
        by[a.R].append(a)
    E = set()
    for R, lst in by.items():
        lst.sort(key=lambda a: a.t)
        E |= {(lst[k], lst[k + 1]) for k in range(len(lst) - 1)}
    return E


def type2_exhaustive(actions):
    """Algorithm 1: compare every pair. c -> a if c.s == a.g, c.t <= a.t, different robots."""
    return {(c, a) for a in actions for c in actions
            if c.R != a.R and c.s == a.g and c.t <= a.t}


def candidate_index(actions):
    """S[v] = actions that START at v, sorted by time (Algorithm 3, lines 1-5)."""
    S = defaultdict(list)
    for a in actions:
        S[a.s].append(a)
    for v in S:
        S[v].sort(key=lambda a: a.t)
    return S


def type2_cp(actions):
    """Algorithm 2: only look at S[a.g]."""
    S = candidate_index(actions)
    return {(c, a) for a in actions for c in S.get(a.g, []) if c.R != a.R and c.t <= a.t}


def latest_candidate(C, a):
    """Latest c in sorted list C with c.t <= a.t and c.R != a.R (walks back past a's own robot).
    Returns (c or None, k0, k): k0 = bisect position - 1, k = chosen index."""
    times = [c.t for c in C]
    k0 = bisect.bisect_right(times, a.t) - 1
    k = k0
    while k >= 0 and C[k].R == a.R:
        k -= 1
    return (C[k] if k >= 0 else None), k0, k


def type2_scp(actions):
    """Algorithm 3 (SCP): at most one type-2 edge per action, from its latest eligible candidate."""
    S = candidate_index(actions)
    E = set()
    for a in actions:
        c, _, _ = latest_candidate(S.get(a.g, []), a)
        if c is not None:
            E.add((c, a))
    return E


def type2_scp_as_printed(actions):
    """Algorithm 3 with lines 9-11 read literally: if C[k] belongs to a's own robot, add no edge.
    Safe, because C[k] reaches a through that robot's type-1 chain (see chapter 03, section 4.5).
    type2_scp() instead walks back to the latest different-robot candidate, as Theorem 3's wording
    suggests; it can only add edges that are already implied."""
    S = candidate_index(actions)
    E = set()
    for a in actions:
        C = S.get(a.g, [])
        k = bisect.bisect_right([c.t for c in C], a.t) - 1
        if k < 0 or C[k].R == a.R:
            continue
        E.add((C[k], a))
    return E


def drop_waits(actions):
    return [a for a in actions if not a.wait]


# --------------------------------------------------------------------------------------
# Graph checks
# --------------------------------------------------------------------------------------

def closure(nodes, edges):
    succ = defaultdict(set)
    for u, v in edges:
        succ[u].add(v)
    reach = {}
    for n in nodes:
        seen, stack = set(), [n]
        while stack:
            x = stack.pop()
            for y in succ[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        reach[n] = seen
    return reach


def is_acyclic(nodes, edges):
    r = closure(nodes, edges)
    return all(n not in r[n] for n in nodes)


def redundant_edges(nodes, edges):
    """Edges u->v such that v is still reachable from u without that edge."""
    out = set()
    for e in edges:
        rest = edges - {e}
        if e[1] in closure(nodes, rest)[e[0]]:
            out.add(e)
    return out


# --------------------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------------------

def execute(actions, edges, duration):
    """Event-driven ADG execution: an action starts the moment all its predecessors are done.
    duration(a) -> seconds. Returns {action: (start, end)}."""
    preds = defaultdict(set)
    for u, v in edges:
        preds[v].add(u)
    done = {}
    pending = set(actions)
    while pending:
        ready = [a for a in pending if preds[a] <= done.keys()]
        assert ready, "cycle"
        for a in sorted(ready, key=lambda a: (max([done[p][1] for p in preds[a]] or [0]), a.t)):
            st = max([done[p][1] for p in preds[a]] or [0.0])
            done[a] = (st, st + duration(a))
            pending.discard(a)
    return done


def occupancy_violations(sched, actions):
    """Simple safety audit for an executed schedule: a robot occupies s until its move ends and
    g from its move's start (it is entering). Two robots inside the same vertex interval -> violation."""
    iv = defaultdict(list)
    by = defaultdict(list)
    for a in actions:
        by[a.R].append(a)
    for R, lst in by.items():
        lst.sort(key=lambda a: a.t)
        moves = [a for a in lst if not a.wait]
        t_in = 0.0
        for a in moves:
            st, en = sched[a]
            iv[a.s].append((t_in, en, R))      # in s from arrival until move ends
            t_in = st                          # starts entering g at move start
        if moves:
            iv[moves[-1].g].append((t_in, float("inf"), R))
    bad = []
    for v, lst in iv.items():
        for (a0, a1, r1), (b0, b1, r2) in itertools.combinations(lst, 2):
            if r1 != r2 and a0 < b1 - 1e-9 and b0 < a1 - 1e-9:
                bad.append((v, r1, r2, max(a0, b0), min(a1, b1)))
    return bad
