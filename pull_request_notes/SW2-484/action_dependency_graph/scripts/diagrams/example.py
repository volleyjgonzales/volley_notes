"""The single worked example used by every figure and every chapter.

Garage (schematic, Pecos naming style; see garage.py):

                       B7   customer bay (door faces south)
                       |
                       W8
                       |
    C10 -- W11 -- W12 -- W13 -- W14 -- P19
                       |
                       P23

Prefixes follow the reference pack: C = AGV charger, W = waypoint, B = customer bay,
P = parking stall. Robots are named so that they never clash with those prefixes:
L, M, N drive east in a convoy (Lead, Middle, the Next one behind), X crosses the junction W13.
An action is named robot + time step: M2 = AGV M's action at plan step 2.

The plan is the result of CBS on this instance (fig 2.1) and is collision-free under the classic
vertex / swap rules (asserted below).
"""
from adg import actions_from_paths, conflicts, type1, type2_exhaustive, type2_cp, type2_scp, drop_waits, candidate_index
from garage import NODES as GNODES, EDGES as GEDGES
from theme import T

VERTS = ["C10", "W11", "W12", "W13", "W14", "P19", "B7", "W8", "P23"]
EDGES = GEDGES
JUNCTION = "W13"

PATHS = {
    "L": ["W12", "W13", "W14", "P19"],          # lead: fetch the tray parked at P19
    "X": ["B7", "W8", "W13", "P23"],            # carries a customer's car on its tray from bay B7 to stall P23
    "M": ["W11", "W12", "W12", "W13", "W14"],   # middle: to waypoint W14 (waits for its next job)
    "N": ["C10", "W11", "W11", "W12", "W13", "W8"],   # leaves the charger, queues in front of bay B7
}
ROBOTS = ["L", "X", "M", "N"]           # lane order in the ADG figures
COLOR = {"L": T.sky, "X": T.violet, "M": T.green, "N": T.pink}
ROLE = {"L": "lead of the convoy", "X": "crosses the junction with a car",
        "M": "middle of the convoy", "N": "last of the convoy"}

ACTIONS = actions_from_paths(PATHS)
MOVES = drop_waits(ACTIONS)
T1_FULL = type1(ACTIONS)
T2_FULL = type2_exhaustive(ACTIONS)
T1 = type1(MOVES)
T2_CP = type2_cp(MOVES)
T2_SCP = type2_scp(MOVES)
INDEX = candidate_index(MOVES)

A = {a.id: a for a in ACTIONS}           # "M1" -> Action(M, 1, W12, W12)

assert not conflicts(PATHS)
assert set(VERTS) == {v for e in EDGES for v in e}
