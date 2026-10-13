"""UML-style composition diagrams of the VDA5050 message structures.

Field set follows VDA 5050 v2.0 (abbreviated). errorHint is from a newer
revision and is flagged as such. commonMessage is HITO's own topic, not part
of VDA5050; its field names are illustrative.
"""
from svgkit import SVG, C, SANS, MONO

# class name -> (stereotype or None, [ (attr, type/enum note) ], [ (role, multiplicity, child class) ])
SCHEMA = {
    "order": ("topic · fleet → AGV", [("orderId", "string"), ("orderUpdateId", "uint32"), ("zoneSetId", "string")],
              [("nodes", "1..*", "Node"), ("edges", "0..*", "Edge")]),
    "Node": (None, [("nodeId", "string"), ("sequenceId", "uint32"), ("nodeDescription", "string"), ("released", "bool")],
             [("nodePosition", "0..1", "NodePosition"), ("actions", "0..*", "Action")]),
    "NodePosition": (None, [("x", "float64, m"), ("y", "float64, m"), ("theta", "float64, rad, −π…π"),
                            ("allowedDeviationXY", "float64, m"), ("allowedDeviationTheta", "float64, rad"), ("mapId", "string")], []),
    "Edge": (None, [("edgeId", "string"), ("sequenceId", "uint32"), ("released", "bool"), ("startNodeId", "string"),
                    ("endNodeId", "string"), ("maxSpeed", "float64, m/s"), ("orientation", "float64, rad"), ("rotationAllowed", "bool")],
             [("trajectory", "0..1", "Trajectory"), ("actions", "0..*", "Action")]),
    "Trajectory": (None, [("degree", ""), ("knotVector", ""), ("controlPoints", "")], []),
    "Action": (None, [("actionType", "string"), ("actionId", "string"), ("actionDescription", "string"),
                      ("blockingType", "NONE | SOFT | HARD")],
               [("actionParameters", "0..*", "ActionParameter")]),
    "ActionParameter": (None, [("key", "string"), ("value", "any")], []),
    "instantActions": ("topic · fleet → AGV", [], [("actions", "1..*", "Action")]),
    "state": ("topic · AGV → fleet", [("orderId", "string"), ("orderUpdateId", "uint32"), ("lastNodeId", "string"),
                                       ("lastNodeSequenceId", "uint32"), ("driving", "bool"), ("paused", "bool"),
                                       ("newBaseRequest", "bool"), ("distanceSinceLastNode", "float64, m"),
                                       ("operatingMode", "AUTOMATIC | SEMIAUTOMATIC | MANUAL | SERVICE | TEACHIN")],
              [("nodeStates", "0..*", "NodeState"), ("edgeStates", "0..*", "EdgeState"), ("agvPosition", "0..1", "AgvPosition"),
               ("velocity", "0..1", "Velocity"), ("loads", "0..*", "Load"), ("actionStates", "0..*", "ActionState"),
               ("batteryState", "1", "BatteryState"), ("errors", "0..*", "Error"), ("information", "0..*", "Info"),
               ("safetyState", "1", "SafetyState")]),
    "NodeState": (None, [("nodeId", ""), ("sequenceId", ""), ("released", "bool")], []),
    "EdgeState": (None, [("edgeId", ""), ("sequenceId", ""), ("released", "bool")], []),
    "AgvPosition": (None, [("x", "float64, m"), ("y", "float64, m"), ("theta", "float64, rad"), ("mapId", "string"),
                           ("positionInitialized", "bool"), ("localizationScore", "0.0 … 1.0"), ("deviationRange", "m")], []),
    "Velocity": (None, [("vx", "m/s"), ("vy", "m/s"), ("omega", "rad/s")], []),
    "Load": (None, [("loadId", ""), ("loadType", ""), ("loadPosition", ""), ("weight", "float64, kg")], []),
    "ActionState": (None, [("actionId", "string"), ("actionType", "string"), ("actionStatus", "WAITING … RUNNING | FINISHED | FAILED"),
                           ("resultDescription", "string")], []),
    "BatteryState": (None, [("batteryCharge", "%"), ("charging", "bool")], []),
    "Error": (None, [("errorType", "string"), ("errorLevel", "WARNING | FATAL"), ("errorDescription", "string"),
                     ("errorHint", "string — newer spec revision")],
              [("errorReferences", "0..*", "ErrorReference")]),
    "ErrorReference": (None, [("referenceKey", "string"), ("referenceValue", "string")], []),
    "Info": (None, [("infoType", ""), ("infoDescription", ""), ("infoLevel", "")], []),
    "SafetyState": (None, [("eStop", "AUTOACK | MANUAL | REMOTE | NONE"), ("fieldViolation", "bool")], []),
    "visualization": ("topic · AGV → fleet", [], [("agvPosition", "0..1", "AgvPosition"), ("velocity", "0..1", "Velocity")]),
    "connection": ("topic · AGV → fleet", [("connectionState", "ONLINE | OFFLINE | CONNECTIONBROKEN")], []),
    "factsheet": ("topic · AGV → fleet", [],
                  [("typeSpecification", "1", "TypeSpecification"), ("physicalParameters", "1", "PhysicalParameters"),
                   ("protocolLimits", "1", "ProtocolLimits"), ("protocolFeatures", "1", "ProtocolFeatures"),
                   ("agvGeometry", "1", "AgvGeometry"), ("loadSpecification", "1", "LoadSpecification")]),
    "ProtocolFeatures": (None, [], [("optionalParameters", "0..*", "OptionalParameter"), ("agvActions", "0..*", "AgvAction")]),
    "AgvAction": (None, [("actionType", "string"), ("actionDescription", "string"), ("actionScopes", "INSTANT | NODE | EDGE")], []),
    "commonMessage": ("HITO custom topic · AGV → fleet", [("rfidSignalStrength", "S value on HMI"), ("rfidReading", "tag id"),
                                                          ("tapeSensor", "offset, or empty"), ("laserField", "active field 0…63")], []),
}
for n in ("TypeSpecification", "PhysicalParameters", "ProtocolLimits", "AgvGeometry", "LoadSpecification", "OptionalParameter"):
    SCHEMA[n] = (None, [], [])

BOXW, GAPX, GAPY = 200, 38, 16
HEAD, ROW, NOTE = 30, 19, 14


import textwrap


def wrap(t, n=34):
    return textwrap.wrap(t, n) if t else []


class Node:
    def __init__(self, cls, role=None, mult=None):
        self.cls, self.role, self.mult = cls, role, mult
        self.attrs = []          # [(name, note, rid or None)]
        self.children = []
        self.hidden_attrs = 0
        self.hidden_parts = 0
        self.rid = None          # whole-class highlight
        self.cnote = None


def build(root, picks):
    """picks: list of (path, rid, note). path = 'state.errors.errorType'."""
    tree = Node(root)
    for path, rid, note in picks:
        parts = path.split(".")
        assert parts[0] == root, path
        cur = tree
        for i, p in enumerate(parts[1:]):
            stereo, attrs, kids = SCHEMA[cur.cls]
            kid = next((k for k in kids if k[0] == p), None)
            if kid:
                nxt = next((c for c in cur.children if c.role == p), None)
                if not nxt:
                    nxt = Node(kid[2], p, kid[1])
                    cur.children.append(nxt)
                cur = nxt
                if i == len(parts) - 2:
                    cur.rid = rid
                    cur.cnote = note
            else:
                a = next((a for a in attrs if a[0] == p), None)
                assert a, (cur.cls, p)
                if not any(x[0] == p for x in cur.attrs):
                    cur.attrs.append((p, note or a[1], rid))
        if len(parts) == 1:
            tree.rid, tree.cnote = rid, note
    _finish(tree)
    return tree


def _finish(n):
    stereo, attrs, kids = SCHEMA[n.cls]
    order = [a[0] for a in attrs]
    n.attrs.sort(key=lambda a: order.index(a[0]))
    n.hidden_attrs = len(attrs) - len(n.attrs)
    n.hidden_parts = len(kids) - len(n.children)
    korder = [k[0] for k in kids]
    n.children.sort(key=lambda c: korder.index(c.role))
    for c in n.children:
        _finish(c)


def box_h(n):
    h = HEAD + 6
    for name, note, rid in n.attrs:
        h += ROW + (NOTE * len(wrap(note)) if rid else 0)
    if n.hidden_attrs or n.hidden_parts:
        h += ROW
    if n.cnote:
        h += NOTE * (len(wrap(n.cnote)) + 1)
    return max(h, HEAD + 14)


def sub_h(n):
    own = box_h(n)
    if not n.children:
        return own
    kids = sum(sub_h(c) for c in n.children) + GAPY * (len(n.children) - 1)
    return max(own, kids)


def draw(s, n, x, y, root=False):
    h = box_h(n)
    stereo = SCHEMA[n.cls][0]
    hl = n.rid is not None
    edge = C["accent"] if hl else C["fg"]
    s.rect(x, y, BOXW, h, fill=C["card"], stroke=edge, sw=2 if hl else 1.4, rx=4)
    s.rect(x, y, BOXW, HEAD, fill=C["fg"] if root else C["bg"], rx=4)
    s.rect(x, y + HEAD - 4, BOXW, 4, fill=C["fg"] if root else C["bg"])
    s.line(x, y + HEAD, x + BOXW, y + HEAD, edge, 1)
    tcol = "#FFFFFF" if root else C["fg"]
    if stereo:
        s.text(x + 10, y + 12, f"«{stereo}»", size=9.5, color="#BFDBFE" if root else C["mutedfg"])
        s.text(x + 10, y + 25, n.cls, size=13, weight=700, color=tcol, mono=True)
    else:
        # part notation: role name (as it appears in JSON) over its type
        arr = "[ ]" if n.mult.endswith("*") else ""
        s.text(x + 10, y + 11, f"type {n.cls}", size=9, color=C["mutedfg"])
        s.text(x + 10, y + 25, n.role + arr, size=12.5, weight=700, color=tcol, mono=True)
    if hl:
        _pill(s, x + BOXW - 6, y + 8 if not stereo else y + 9, n.rid, root)
    yy = y + HEAD + 4
    if n.cnote:
        for i, ln in enumerate(wrap(n.cnote)):
            s.text(x + 10, yy + 12 + i * NOTE, ln, size=10, color=C["accent"], italic=True)
        yy += NOTE * (len(wrap(n.cnote)) + 1)
    for name, note, rid in n.attrs:
        rh = ROW + (NOTE * len(wrap(note)) if rid else 0)
        if rid:
            s.rect(x + 3, yy + 1, BOXW - 6, rh - 2, fill=C["accent"], rx=3, opacity=0.12)
        s.text(x + 10, yy + 14, name, size=11, mono=True, weight=600 if rid else 400,
               color=C["ink"] if rid else C["mutedfg"])
        if rid:
            _pill(s, x + BOXW - 6, yy + 3, rid)
            for i, ln in enumerate(wrap(note)):
                s.text(x + 18, yy + 14 + NOTE * (i + 1) - 1, ln, size=9.5, color=C["accent"])
        yy += rh
    if n.hidden_attrs or n.hidden_parts:
        bits = []
        if n.hidden_attrs:
            bits.append(f"+{n.hidden_attrs} fields")
        if n.hidden_parts:
            bits.append(f"+{n.hidden_parts} parts")
        s.text(x + 10, yy + 14, "  ".join(bits), size=10, color=C["slate"], italic=True)
    # children
    cy = y
    px = x + BOXW
    for c in n.children:
        ch = sub_h(c)
        cx = x + BOXW + GAPX
        ty = cy + HEAD / 2
        sy = y + HEAD / 2
        mx = px + 14
        s.path(f"M {px+10} {sy} L {mx} {sy} L {mx} {ty} L {cx} {ty}", C["fg"], 1.3)
        # filled diamond on the whole (composition)
        s.raw(f'<path d="M {px} {sy} L {px+5} {sy-4} L {px+10} {sy} L {px+5} {sy+4} Z" fill="{C["fg"]}"/>')
        s.text(cx - 3, ty - 4, c.mult, size=9.5, anchor="end", color=C["fg"], mono=True)
        draw(s, c, cx, cy)
        cy += ch + GAPY
    return h


def _pill(s, right, y, rid, on_dark=False):
    w = 10 + len(rid) * 6.3
    s.rect(right - w, y, w, 15, fill=C["accent"], rx=7.5)
    s.text(right - w / 2, y + 11, rid, size=9.5, anchor="middle", color="#FFFFFF", weight=600, mono=True)


def depth(n):
    return 1 + max((depth(c) for c in n.children), default=0)


def figure(title, subtitle, roots, notes=None, width=960):
    """roots: list of (rootname, picks). Stacked vertically."""
    trees = [build(r, p) for r, p in roots]
    top = 96
    total = sum(sub_h(t) for t in trees) + 26 * (len(trees) - 1)
    legend_h = 44
    h = top + total + legend_h + (len(notes) * 18 + 10 if notes else 0) + 20
    s = SVG(width, int(h), title, subtitle)
    y = top
    for t in trees:
        draw(s, t, 28, y, root=True)
        y += sub_h(t) + 26
    # legend
    ly = y + 4
    s.raw(f'<path d="M 28 {ly} L 33 {ly-4} L 38 {ly} L 33 {ly+4} Z" fill="{C["fg"]}"/>')
    s.line(38, ly, 70, ly, C["fg"], 1.3)
    s.text(78, ly + 4, "composition: the part is nested inside its parent", size=11, color=C["mutedfg"])
    s.text(390, ly + 4, "0..1 optional · 1 one · 0..* / 1..* list [ ]", size=11, color=C["mutedfg"], mono=True)
    _pill(s, 760, ly - 7, "x.y")
    s.text(768, ly + 4, "field named by requirement", size=11, color=C["mutedfg"])
    if notes:
        for i, t in enumerate(notes):
            s.text(28, ly + 30 + i * 18, t, size=11.5, color=C["mutedfg"])
    return s
