"""Blocked poses of the SW2-905 reproduction state, from the cached Pecos collision table.
Mirrors BuildStaticObstacleFilter for the queried (moving) footprint 5 = PAYLOAD STANDARD (tray 27)."""
import json, sys
pp = json.load(open(sys.argv[1]))["pose_pose_map"]
TRAY, AGV, STD, XL = "2", "3", "5", "7"

def q(fixed, pose, queried):
    key = f"{pose[0]}@{pose[1]}"
    try:
        return {(int(p["node_id"]), int(p["heading"])) for p in pp[fixed][key][queried]}
    except KeyError:
        return set()

trays = {7: ((5, 90), TRAY), 10: ((19, 90), TRAY), 4: ((2, 90), TRAY), 5: ((6, 90), TRAY), 6: ((20, 90), TRAY),
         15: ((3, 90), STD), 17: ((17, 90), STD), 21: ((23, 90), STD), 27: ((7, 90), STD)}
agvs = {7: (5, 90), 10: (19, 90), 1: (14, -90)}
disabled = [24]

def filt(ignore_trays, ignore_agvs):
    out = {}   # pose -> list of causes
    def add(poses, cause):
        for p in poses:
            out.setdefault(p, []).append(cause)
    for tid, (pose, fp) in trays.items():
        if tid in ignore_trays: continue
        add(q(fp, pose, STD), f"T{tid}")
    for aid, pose in agvs.items():
        if aid in ignore_agvs: continue
        add(q(AGV, pose, TRAY), f"AGV{aid}")          # PAYLOAD vs AGV is checked as TRAY
    for node in disabled:
        for h in (90,):                                  # node 24 allows heading 90 only
            add(q(XL, (node, h), STD), f"disabled P{node}")
    return out

panels = {
    "keep_out":   filt(ignore_trays=set(trays), ignore_agvs=set(agvs)),
    "stall_search": filt(ignore_trays=set(trays), ignore_agvs=set(agvs)),
    "validation": filt(ignore_trays={27}, ignore_agvs={7}),
}
res = {k: {f"{n}@{h}": v for (n, h), v in sorted(d.items())} for k, d in panels.items()}
print(json.dumps(res, indent=1))
