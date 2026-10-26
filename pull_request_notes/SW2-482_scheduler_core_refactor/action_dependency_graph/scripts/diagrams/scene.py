"""Place the example's AGVs (and the trays they carry) in the garage at a plan step or at a
continuous time of an executed schedule."""
from __future__ import annotations

from garage import NODES, heading_between, node_axis

HEADING = "w"   # every Pecos node allows heading 90 (= facing west); AGVs move sideways along the aisle
import example as ex

CARRIES = {"A2": "T23"}         # X carries tray T23 (with a customer's car) for its whole route
PARKED_TRAYS = [("P15", "T15", True), ("P17", "T17", False), ("P19", "T19", True), ("P20", "T20", True),
                ("P24", "T24", False), ("P2", "T2", True), ("P3", "T3", False), ("P5", "T5", True), ("P6", "T6", True)]


def _heading_at(path, t):
    for k in range(t, len(path) - 1):          # next real move
        if path[k + 1] != path[k]:
            return heading_between(path[k], path[k + 1])
    for k in range(min(t, len(path) - 1), 0, -1):   # last real move
        if path[k] != path[k - 1]:
            return heading_between(path[k - 1], path[k])
    return "e"


def plan_positions(t):
    """{robot: (vertex or (x, y), heading, moving_next, waiting_now)} at plan step t."""
    out = {}
    for r, p in ex.PATHS.items():
        k = min(t, len(p) - 1)
        v = p[k]
        nxt = p[k + 1] if k + 1 < len(p) else None
        waiting = nxt is not None and nxt == v
        out[r] = dict(at=v, heading=_heading_at(p, k), next=nxt if nxt and nxt != v else None, waiting=waiting,
                      done=k == len(p) - 1)
    return out


def sched_positions(sched, tau):
    """Positions at time tau of an executed schedule {action: (start, end)} (linear interpolation)."""
    out = {}
    for r in ex.ROBOTS:
        acts = sorted([a for a in sched if a.R == r], key=lambda a: a.t)
        pos, head, state = None, None, "idle"
        p = ex.PATHS[r]
        pos = NODES[p[0]].x, NODES[p[0]].y
        head = _heading_at(p, 0)
        for a in acts:
            s, e = sched[a]
            A, B = NODES[a.s], NODES[a.g]
            if tau >= e:
                pos = (B.x, B.y)
                if not a.wait:
                    head = heading_between(a.s, a.g)
                state = "idle"
            elif tau >= s:
                f = (tau - s) / (e - s)
                pos = (A.x + (B.x - A.x) * f, A.y + (B.y - A.y) * f)
                if not a.wait:
                    head = heading_between(a.s, a.g)
                state = "wait" if a.wait else "moving"
                break
            else:
                state = "blocked"
                break
        out[r] = dict(at=pos, heading=head, state=state)
    return out


def draw_trays(G, *, skip=(), dim_context=True, labels=True):
    for v, label, car in PARKED_TRAYS:
        if v in skip or not G.visible(NODES[v], -1.0):
            continue
        G.tray(v, label if labels else None, axis=node_axis(v), payload=car, dim=dim_context and not NODES[v].used)


def draw_robot(G, r, at, heading, *, label=True, label_side="below", ghost=False, size=1.0):
    col = ex.COLOR[r]
    if r in CARRIES and not ghost:
        G.tray(at, None, axis="x", payload=True)
    return G.agv(at, f"AGV-{r[1:]}" if label is True else (label or None), heading=HEADING, color=col,
                 label_side=label_side, lifted=r in CARRIES, ghost=ghost, size=size)
