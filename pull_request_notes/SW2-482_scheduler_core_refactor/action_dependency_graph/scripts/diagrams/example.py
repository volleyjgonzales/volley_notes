"""The single worked example used by every figure and every chapter.

It lives in the real Pecos garage (sources/5675_pecos_combined.yaml), in the sandbox_qa section:

                 W25 -- W26                 (top waypoint row)
                  |
    B21 -- W41 -- W22 -- P23                (W22 = the junction, rotation allowed)
                  |
                 W18
                  |
                 W13
                  |
                  W8                         (comes up from the sandbox_eng section)

Prefixes follow the YAML node types: P = parking stall, W = waypoint, B = customer bay,
C = AGV charger. AGVs are numbered AGV-1 ... AGV-4 in the order in which they pass the junction W22:
AGV-1, AGV-3, AGV-4 drive north up the aisle in a convoy, AGV-2 carries a
customer's car from bay B21 across the junction into stall P23.
An action is named robot + time step: A3-2 = AGV-3's action at plan step 2.

The plan is the result of CBS on this instance (fig 2.1) and is collision-free under the classic
vertex / swap rules (asserted below). AGV and tray occupancy is hypothetical; the YAML has none.
"""
from adg import actions_from_paths, conflicts, type1, type2_exhaustive, type2_cp, type2_scp, drop_waits, candidate_index
import garage
from theme import T

JUNCTION = "W22"
PATHS = {
    "A1": ["W18", "W22", "W25", "W26"],          # lead: up the aisle to the top row
    "A2": ["B21", "W41", "W22", "P23"],          # carries a customer's car from bay B21 into stall P23
    "A3": ["W13", "W18", "W18", "W22", "W25"],   # middle: up to W25
    "A4": ["W8", "W13", "W13", "W18", "W22", "W41"],   # last: turns west at the junction, queues in front of bay B21
}
VERTS = sorted({v for p in PATHS.values() for v in p})
EDGES = sorted({tuple(sorted((u, v))) for p in PATHS.values() for u, v in zip(p, p[1:]) if u != v})
garage.USED.update(VERTS)
garage.EX_EDGES.update(frozenset(e) for e in EDGES)
for u, v in EDGES:
    assert (u, v) in garage.ALL_EDGES or (v, u) in garage.ALL_EDGES, (u, v)
ROBOTS = ["A1", "A2", "A3", "A4"]           # lane order in the ADG figures
COLOR = {"A1": T.sky, "A2": T.violet, "A3": T.green, "A4": T.pink}
ROLE = {"A1": "lead of the convoy", "A2": "carries a car across the junction",
        "A3": "middle of the convoy", "A4": "last of the convoy"}

ACTIONS = actions_from_paths(PATHS)
MOVES = drop_waits(ACTIONS)
T1_FULL = type1(ACTIONS)
T2_FULL = type2_exhaustive(ACTIONS)
T1 = type1(MOVES)
T2_CP = type2_cp(MOVES)
T2_SCP = type2_scp(MOVES)
INDEX = candidate_index(MOVES)

A = {a.id: a for a in ACTIONS}           # "M1" -> Action(M, 1, W18, W18)

assert not conflicts(PATHS)
assert len(VERTS) == 9 and len(EDGES) == 8
