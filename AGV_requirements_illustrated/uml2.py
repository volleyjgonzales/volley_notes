"""UML-style composition diagrams of VDA5050 messages, showing every field.

Field set follows VDA 5050 v2.0. errorHint is from a newer revision and is
flagged. commonMessage is HITO's own topic; its fields are placeholders.
Relevant fields are highlighted; all others are listed in grey so the reader
sees what the whole structure holds.
"""
import textwrap
from svgkit import SVG, C

HEADER = ["headerId · timestamp · version ·", "manufacturer · serialNumber"]

# class -> (stereotype, [(field, short type, long note or None)], [(role, multiplicity, class)])
SCHEMA = {
    "order": ("topic · fleet → AGV",
              [("orderId", "string", None), ("orderUpdateId", "uint32", None), ("zoneSetId", "string", None)],
              [("nodes", "1..*", "Node"), ("edges", "0..*", "Edge")]),
    "Node": (None, [("nodeId", "string", None), ("sequenceId", "uint32", None), ("nodeDescription", "string", None),
                    ("released", "bool", None)],
             [("nodePosition", "0..1", "NodePosition"), ("actions", "0..*", "Action")]),
    "NodePosition": (None, [("x", "m", None), ("y", "m", None), ("theta", "rad", "rad, −π … π"),
                            ("allowedDeviationXY", "m", None), ("allowedDeviationTheta", "rad", None),
                            ("mapId", "string", None), ("mapDescription", "string", None)], []),
    "Edge": (None, [("edgeId", "string", None), ("sequenceId", "uint32", None), ("edgeDescription", "string", None),
                    ("released", "bool", None), ("startNodeId", "string", None), ("endNodeId", "string", None),
                    ("maxSpeed", "m/s", None), ("maxHeight", "m", None), ("minHeight", "m", None),
                    ("orientation", "rad", None), ("orientationType", "enum", "GLOBAL | TANGENTIAL"),
                    ("direction", "string", None), ("rotationAllowed", "bool", None), ("maxRotationSpeed", "rad/s", None),
                    ("length", "m", None)],
             [("trajectory", "0..1", "Trajectory"), ("actions", "0..*", "Action")]),
    "Trajectory": (None, [("degree", "number", None), ("knotVector", "array", None), ("controlPoints", "array", None)], []),
    "Action": (None, [("actionType", "string", None), ("actionId", "string", None), ("actionDescription", "string", None),
                      ("blockingType", "enum", "NONE | SOFT | HARD")],
               [("actionParameters", "0..*", "ActionParameter")]),
    "ActionParameter": (None, [("key", "string", None), ("value", "any", None)], []),
    "instantActions": ("topic · fleet → AGV", [], [("actions", "1..*", "Action")]),
    "state": ("topic · AGV → fleet",
              [("orderId", "string", None), ("orderUpdateId", "uint32", None), ("zoneSetId", "string", None),
               ("lastNodeId", "string", None), ("lastNodeSequenceId", "uint32", None), ("driving", "bool", None),
               ("paused", "bool", None), ("newBaseRequest", "bool", None), ("distanceSinceLastNode", "m", None),
               ("operatingMode", "enum", "AUTOMATIC | SEMIAUTOMATIC | MANUAL | SERVICE | TEACHIN")],
              [("nodeStates", "0..*", "NodeState"), ("edgeStates", "0..*", "EdgeState"), ("agvPosition", "0..1", "AgvPosition"),
               ("velocity", "0..1", "Velocity"), ("loads", "0..*", "Load"), ("actionStates", "0..*", "ActionState"),
               ("batteryState", "1", "BatteryState"), ("errors", "0..*", "Error"), ("information", "0..*", "Info"),
               ("safetyState", "1", "SafetyState")]),
    "NodeState": (None, [("nodeId", "string", None), ("sequenceId", "uint32", None), ("nodeDescription", "string", None),
                         ("released", "bool", None)], [("nodePosition", "0..1", "NodePosition")]),
    "EdgeState": (None, [("edgeId", "string", None), ("sequenceId", "uint32", None), ("edgeDescription", "string", None),
                         ("released", "bool", None)], [("trajectory", "0..1", "Trajectory")]),
    "AgvPosition": (None, [("x", "m", None), ("y", "m", None), ("theta", "rad", None), ("mapId", "string", None),
                           ("mapDescription", "string", None), ("positionInitialized", "bool", None),
                           ("localizationScore", "0…1", None), ("deviationRange", "m", None)], []),
    "Velocity": (None, [("vx", "m/s", None), ("vy", "m/s", None), ("omega", "rad/s", None)], []),
    "Load": (None, [("loadId", "string", None), ("loadType", "string", None), ("loadPosition", "string", None),
                    ("weight", "kg", None)],
             [("boundingBoxReference", "0..1", "BoundingBoxReference"), ("loadDimensions", "0..1", "LoadDimensions")]),
    "ActionState": (None, [("actionId", "string", None), ("actionType", "string", None), ("actionDescription", "string", None),
                           ("actionStatus", "enum", "WAITING | INITIALIZING | RUNNING | PAUSED | FINISHED | FAILED"),
                           ("resultDescription", "string", None)], []),
    "BatteryState": (None, [("batteryCharge", "%", None), ("batteryVoltage", "V", None), ("batteryHealth", "%", None),
                            ("charging", "bool", None), ("reach", "m", None)], []),
    "Error": (None, [("errorType", "string", None), ("errorDescription", "string", None),
                     ("errorLevel", "enum", "WARNING | FATAL"), ("errorHint", "string", "string, newer spec revision")],
              [("errorReferences", "0..*", "ErrorReference")]),
    "ErrorReference": (None, [("referenceKey", "string", None), ("referenceValue", "string", None)], []),
    "Info": (None, [("infoType", "string", None), ("infoDescription", "string", None), ("infoLevel", "enum", "DEBUG | INFO")],
             [("infoReferences", "0..*", "InfoReference")]),
    "SafetyState": (None, [("eStop", "enum", "AUTOACK | MANUAL | REMOTE | NONE"), ("fieldViolation", "bool", None)], []),
    "visualization": ("topic · AGV → fleet", [], [("agvPosition", "0..1", "AgvPosition"), ("velocity", "0..1", "Velocity")]),
    "connection": ("topic · AGV → fleet", [("connectionState", "enum", "ONLINE | OFFLINE | CONNECTIONBROKEN")], []),
    "factsheet": ("topic · AGV → fleet", [],
                  [("typeSpecification", "1", "TypeSpecification"), ("physicalParameters", "1", "PhysicalParameters"),
                   ("protocolLimits", "1", "ProtocolLimits"), ("protocolFeatures", "1", "ProtocolFeatures"),
                   ("agvGeometry", "1", "AgvGeometry"), ("loadSpecification", "1", "LoadSpecification")]),
    "ProtocolFeatures": (None, [], [("optionalParameters", "0..*", "OptionalParameter"), ("agvActions", "0..*", "AgvAction")]),
    "AgvAction": (None, [("actionType", "string", None), ("actionDescription", "string", None),
                         ("actionScopes", "enum[]", "INSTANT | NODE | EDGE"), ("resultDescription", "string", None)],
                  [("actionParameters", "0..*", "AgvActionParameter")]),
    "commonMessage": ("HITO custom topic · AGV → fleet",
                      [("rfidSignalStrength", "number", "S value on HMI"), ("rfidReading", "string", "tag id"),
                       ("tapeSensor", "number|\"\"", "offset, empty when no reading"),
                       ("laserField", "int", "active field 0 … 63")], []),
}
for _n in ("TypeSpecification", "PhysicalParameters", "ProtocolLimits", "AgvGeometry", "LoadSpecification",
           "OptionalParameter", "BoundingBoxReference", "LoadDimensions", "InfoReference", "AgvActionParameter"):
    SCHEMA[_n] = (None, [], [])

BOXW, GAPX, GAPY = 200, 38, 16
HEAD, ROW, NOTE = 30, 17, 13


def wrap(t, n=34):
    return textwrap.wrap(t, n) if t else []


class Node:
    def __init__(self, cls, role=None, mult=None, root=False):
        self.cls, self.role, self.mult, self.root = cls, role, mult, root
        self.hl = {}            # field -> (rid, note)
        self.children = []
        self.rid = None
        self.cnote = None

    # rows: ("header"|"field"|"part", ...)
    def rows(self):
        stereo, attrs, kids = SCHEMA[self.cls]
        out = []
        if self.root:
            out.append(("header",))
        for name, short, long in attrs:
            if name in self.hl:
                rid, note = self.hl[name]
                out.append(("field", name, short, rid, note or long or short))
            else:
                out.append(("field", name, short, None, None))
        expanded = {c.role for c in self.children}
        for role, mult, cls in kids:
            if role not in expanded:
                out.append(("part", role, mult, cls))
        return out


def build(root, picks):
    tree = Node(root, root=True)
    for path, rid, note in picks:
        parts = path.split(".")
        cur = tree
        if len(parts) == 1:
            tree.rid, tree.cnote = rid, note
            continue
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
                    cur.rid, cur.cnote = rid, note
            else:
                assert any(a[0] == p for a in attrs), (cur.cls, p)
                if rid or p not in cur.hl:
                    cur.hl[p] = (rid, note)
    _sort(tree)
    return tree


def _sort(n):
    korder = [k[0] for k in SCHEMA[n.cls][2]]
    n.children.sort(key=lambda c: korder.index(c.role))
    for c in n.children:
        _sort(c)


def row_h(r):
    if r[0] == "header":
        return ROW + 2 * NOTE
    if r[0] == "field" and r[3]:
        return ROW + NOTE * len(wrap(r[4]))
    return ROW


def box_h(n):
    h = HEAD + 6 + sum(row_h(r) for r in n.rows())
    if n.cnote:
        h += NOTE * (len(wrap(n.cnote)) + 1)
    return max(h, HEAD + 16) + 4


def sub_h(n):
    own = box_h(n)
    if not n.children:
        return own
    return max(own, sum(sub_h(c) for c in n.children) + GAPY * (len(n.children) - 1))


def _pill(s, right, y, rid):
    w = 10 + len(rid) * 6.3
    s.rect(right - w, y, w, 15, fill=C["accent"], rx=7.5)
    s.text(right - w / 2, y + 11, rid, size=9.5, anchor="middle", color="#FFFFFF", weight=600, mono=True)


def draw(s, n, x, y):
    h = box_h(n)
    stereo = SCHEMA[n.cls][0]
    hl = n.rid is not None
    edge = C["accent"] if hl else C["fg"]
    root = n.root
    s.rect(x, y, BOXW, h, fill=C["card"], stroke=edge, sw=2 if hl else 1.4, rx=4)
    s.rect(x, y, BOXW, HEAD, fill=C["fg"] if root else C["bg"], rx=4)
    s.rect(x, y + HEAD - 4, BOXW, 4, fill=C["fg"] if root else C["bg"])
    s.line(x, y + HEAD, x + BOXW, y + HEAD, edge, 1)
    if root:
        s.text(x + 10, y + 12, f"«{stereo}»", size=9.5, color="#BFDBFE")
        s.text(x + 10, y + 25, n.cls, size=13, weight=700, color="#FFFFFF", mono=True)
    else:
        arr = "[ ]" if n.mult.endswith("*") else ""
        s.text(x + 10, y + 11, f"type {n.cls}", size=9, color=C["mutedfg"])
        s.text(x + 10, y + 25, n.role + arr, size=12.5, weight=700, color=C["fg"], mono=True)
    if hl:
        _pill(s, x + BOXW - 6, y + 8, n.rid)
    yy = y + HEAD + 4
    if n.cnote:
        for i, ln in enumerate(wrap(n.cnote)):
            s.text(x + 10, yy + 12 + i * NOTE, ln, size=10, color=C["accent"], italic=True)
        yy += NOTE * (len(wrap(n.cnote)) + 1)
    for r in n.rows():
        rh = row_h(r)
        if r[0] == "header":
            lab = "header (assumed same as VDA5050)" if n.cls == "commonMessage" else "header (common to all topics)"
            s.text(x + 10, yy + 12, lab, size=10, color=C["slate"], weight=600)
            for i, ln in enumerate(HEADER):
                s.text(x + 18, yy + 12 + NOTE * (i + 1), ln, size=9.5, color=C["slate"])
        elif r[0] == "field":
            _, name, short, rid, note = r
            if rid:
                s.rect(x + 3, yy + 1, BOXW - 6, rh - 2, fill=C["accent"], rx=3, opacity=0.14)
                s.text(x + 10, yy + 12.5, name, size=10.5, mono=True, weight=700, color=C["ink"])
                _pill(s, x + BOXW - 6, yy + 1.5, rid)
                for i, ln in enumerate(wrap(note)):
                    s.text(x + 18, yy + 12.5 + NOTE * (i + 1), ln, size=9.5, color=C["accent"])
            else:
                s.text(x + 10, yy + 12.5, name, size=10.5, mono=True, color=C["mutedfg"])
                s.text(x + BOXW - 8, yy + 12.5, short, size=9.5, anchor="end", color="#94A3B8")
        else:
            _, role, mult, cls = r
            arr = "[ ]" if mult.endswith("*") else ""
            s.raw(f'<path d="M {x+10} {yy+9} L {x+14} {yy+6} L {x+18} {yy+9} L {x+14} {yy+12} Z" fill="{C["slate"]}"/>')
            s.text(x + 23, yy + 12.5, role + arr, size=10.5, mono=True, color=C["slate"], italic=True)
            if 6.4 * len(role + arr) + 4.9 * len(cls) + 10 < BOXW - 31:
                s.text(x + BOXW - 8, yy + 12.5, cls, size=9, anchor="end", color="#94A3B8")
        yy += rh
    cy = y
    px = x + BOXW
    for c in n.children:
        ch = sub_h(c)
        cx = x + BOXW + GAPX
        ty, sy = cy + HEAD / 2, y + HEAD / 2
        mx = px + 14
        s.path(f"M {px+10} {sy} L {mx} {sy} L {mx} {ty} L {cx} {ty}", C["fg"], 1.3)
        s.raw(f'<path d="M {px} {sy} L {px+5} {sy-4} L {px+10} {sy} L {px+5} {sy+4} Z" fill="{C["fg"]}"/>')
        s.text(cx - 3, ty - 4, c.mult, size=9.5, anchor="end", color=C["fg"], mono=True)
        draw(s, c, cx, cy)
        cy += ch + GAPY


def figure(title, subtitle, roots, notes=None, width=960):
    trees = [build(r, p) for r, p in roots]
    top = 96
    total = sum(sub_h(t) for t in trees) + 26 * (len(trees) - 1)
    notes = notes or []
    h = top + total + 64 + len(notes) * 18 + 16
    s = SVG(width, int(h), title, subtitle)
    y = top
    for t in trees:
        draw(s, t, 28, y)
        y += sub_h(t) + 26
    ly = y + 4
    s.raw(f'<path d="M 28 {ly} L 33 {ly-4} L 38 {ly} L 33 {ly+4} Z" fill="{C["fg"]}"/>')
    s.line(38, ly, 66, ly, C["fg"], 1.3)
    s.text(74, ly + 4, "composition: right box is nested in left box", size=11, color=C["mutedfg"])
    _pill(s, 380, ly - 7, "x.y")
    s.text(388, ly + 4, "field a requirement depends on", size=11, color=C["mutedfg"])
    s.text(620, ly + 4, "grey = other fields of the same object", size=11, color=C["mutedfg"])
    ly2 = ly + 22
    s.raw(f'<path d="M 28 {ly2} L 32 {ly2-3} L 36 {ly2} L 32 {ly2+3} Z" fill="{C["slate"]}"/>')
    s.text(42, ly2 + 4, "nested object not expanded here", size=11, color=C["slate"], italic=True)
    s.text(260, ly2 + 4, "0..1 optional · 1 required · 0..* / 1..* array [ ]", size=11, color=C["mutedfg"], mono=True)
    for i, t in enumerate(notes):
        s.text(28, ly2 + 26 + i * 18, t, size=11.5, color=C["mutedfg"])
    return s
