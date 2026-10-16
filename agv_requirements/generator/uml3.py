"""UML-style composition diagrams of VDA5050 messages (v3).

* Every field of each drawn object is listed, with data type and unit.
* Nested objects are listed as fields too; the ones on the path to a
  requirement are highlighted and their composition line starts at that row.
* Composition lines carry the JSON key and multiplicity.
* Each message shows who publishes it and who receives it.

Field set follows VDA 5050 v2.0. errorHint is from a newer revision and is
flagged. commonMessage is HITO's own topic; its fields are placeholders.
"""
import textwrap
from svgkit import SVG, C

HEADER = ["headerId uint32 · timestamp string (ISO 8601)", "version · manufacturer · serialNumber string"]

F64 = "float64"
# class -> (stereotype, [(field, type, unit or "", long note or None)], [(role, multiplicity, class)])
SCHEMA = {
    "order": ("topic", [("orderId", "string", "", None), ("orderUpdateId", "uint32", "", None), ("zoneSetId", "string", "", None)],
              [("nodes", "1..*", "Node"), ("edges", "0..*", "Edge")]),
    "Node": (None, [("nodeId", "string", "", None), ("sequenceId", "uint32", "", None), ("nodeDescription", "string", "", None),
                    ("released", "boolean", "", None)],
             [("nodePosition", "0..1", "NodePosition"), ("actions", "0..*", "Action")]),
    "NodePosition": (None, [("x", F64, "m", None), ("y", F64, "m", None), ("theta", F64, "rad", "−π … π"),
                            ("allowedDeviationXY", F64, "m", None), ("allowedDeviationTheta", F64, "rad", None),
                            ("mapId", "string", "", None), ("mapDescription", "string", "", None)], []),
    "Edge": (None, [("edgeId", "string", "", None), ("sequenceId", "uint32", "", None), ("edgeDescription", "string", "", None),
                    ("released", "boolean", "", None), ("startNodeId", "string", "", None), ("endNodeId", "string", "", None),
                    ("maxSpeed", F64, "m/s", None), ("maxHeight", F64, "m", None), ("minHeight", F64, "m", None),
                    ("orientation", F64, "rad", None), ("orientationType", "string enum", "", "GLOBAL | TANGENTIAL"),
                    ("direction", "string", "", None), ("rotationAllowed", "boolean", "", None),
                    ("maxRotationSpeed", F64, "rad/s", None), ("length", F64, "m", None)],
             [("trajectory", "0..1", "Trajectory"), ("actions", "0..*", "Action")]),
    "Trajectory": (None, [("degree", F64, "", None), ("knotVector", "float64[]", "", None)],
                   [("controlPoints", "1..*", "ControlPoint")]),
    "Action": (None, [("actionType", "string", "", None), ("actionId", "string", "", None), ("actionDescription", "string", "", None),
                      ("blockingType", "string enum", "", "NONE | SOFT | HARD")],
               [("actionParameters", "0..*", "ActionParameter")]),
    "ActionParameter": (None, [("key", "string", "", None), ("value", "any", "", None)], []),
    "instantActions": ("topic", [], [("actions", "1..*", "Action")]),
    "state": ("topic",
              [("orderId", "string", "", None), ("orderUpdateId", "uint32", "", None), ("zoneSetId", "string", "", None),
               ("lastNodeId", "string", "", None), ("lastNodeSequenceId", "uint32", "", None), ("driving", "boolean", "", None),
               ("paused", "boolean", "", None), ("newBaseRequest", "boolean", "", None),
               ("distanceSinceLastNode", F64, "m", None),
               ("operatingMode", "string enum", "", "AUTOMATIC | SEMIAUTOMATIC | MANUAL | SERVICE | TEACHIN")],
              [("nodeStates", "0..*", "NodeState"), ("edgeStates", "0..*", "EdgeState"), ("agvPosition", "0..1", "AgvPosition"),
               ("velocity", "0..1", "Velocity"), ("loads", "0..*", "Load"), ("actionStates", "0..*", "ActionState"),
               ("batteryState", "1", "BatteryState"), ("errors", "0..*", "Error"), ("information", "0..*", "Info"),
               ("safetyState", "1", "SafetyState")]),
    "NodeState": (None, [("nodeId", "string", "", None), ("sequenceId", "uint32", "", None), ("nodeDescription", "string", "", None),
                         ("released", "boolean", "", None)], [("nodePosition", "0..1", "NodePosition")]),
    "EdgeState": (None, [("edgeId", "string", "", None), ("sequenceId", "uint32", "", None), ("edgeDescription", "string", "", None),
                         ("released", "boolean", "", None)], [("trajectory", "0..1", "Trajectory")]),
    "AgvPosition": (None, [("x", F64, "m", None), ("y", F64, "m", None), ("theta", F64, "rad", None), ("mapId", "string", "", None),
                           ("mapDescription", "string", "", None), ("positionInitialized", "boolean", "", None),
                           ("localizationScore", F64, "0 … 1", None), ("deviationRange", F64, "m", None)], []),
    "Velocity": (None, [("vx", F64, "m/s", None), ("vy", F64, "m/s", None), ("omega", F64, "rad/s", None)], []),
    "Load": (None, [("loadId", "string", "", None), ("loadType", "string", "", None), ("loadPosition", "string", "", None),
                    ("weight", F64, "kg", None)],
             [("boundingBoxReference", "0..1", "BoundingBoxReference"), ("loadDimensions", "0..1", "LoadDimensions")]),
    "ActionState": (None, [("actionId", "string", "", None), ("actionType", "string", "", None),
                           ("actionDescription", "string", "", None),
                           ("actionStatus", "string enum", "", "WAITING | INITIALIZING | RUNNING | PAUSED | FINISHED | FAILED"),
                           ("resultDescription", "string", "", None)], []),
    "BatteryState": (None, [("batteryCharge", F64, "%", None), ("batteryVoltage", F64, "V", None), ("batteryHealth", "int8", "%", None),
                            ("charging", "boolean", "", None), ("reach", "uint32", "m", None)], []),
    "Error": (None, [("errorType", "string", "", None), ("errorDescription", "string", "", None),
                     ("errorLevel", "string enum", "", "WARNING | FATAL"), ("errorHint", "string", "", "newer spec revision")],
              [("errorReferences", "0..*", "ErrorReference")]),
    "ErrorReference": (None, [("referenceKey", "string", "", None), ("referenceValue", "string", "", None)], []),
    "Info": (None, [("infoType", "string", "", None), ("infoDescription", "string", "", None),
                    ("infoLevel", "string enum", "", "DEBUG | INFO")], [("infoReferences", "0..*", "InfoReference")]),
    "SafetyState": (None, [("eStop", "string enum", "", "AUTOACK | MANUAL | REMOTE | NONE"), ("fieldViolation", "boolean", "", None)], []),
    "visualization": ("topic", [], [("agvPosition", "0..1", "AgvPosition"), ("velocity", "0..1", "Velocity")]),
    "connection": ("topic", [("connectionState", "string enum", "", "ONLINE | OFFLINE | CONNECTIONBROKEN")], []),
    "factsheet": ("topic", [],
                  [("typeSpecification", "1", "TypeSpecification"), ("physicalParameters", "1", "PhysicalParameters"),
                   ("protocolLimits", "1", "ProtocolLimits"), ("protocolFeatures", "1", "ProtocolFeatures"),
                   ("agvGeometry", "1", "AgvGeometry"), ("loadSpecification", "1", "LoadSpecification")]),
    "ProtocolFeatures": (None, [], [("optionalParameters", "0..*", "OptionalParameter"), ("agvActions", "0..*", "AgvAction")]),
    "AgvAction": (None, [("actionType", "string", "", None), ("actionDescription", "string", "", None),
                         ("actionScopes", "string enum[]", "", "INSTANT | NODE | EDGE"), ("resultDescription", "string", "", None)],
                  [("actionParameters", "0..*", "AgvActionParameter")]),
    "commonMessage": ("HITO custom topic",
                      [("rfidSignalStrength", "number", "", "S value on HMI"), ("rfidReading", "string", "", "tag id"),
                       ("tapeSensor", "number | \"\"", "mm", "empty when no reading"),
                       ("laserField", "int", "", "active field 0 … 63")], []),
}
for _n in ("TypeSpecification", "PhysicalParameters", "ProtocolLimits", "AgvGeometry", "LoadSpecification", "ControlPoint",
           "OptionalParameter", "BoundingBoxReference", "LoadDimensions", "InfoReference", "AgvActionParameter"):
    SCHEMA[_n] = (None, [], [])

FLOW = {  # root -> (from, to)
    "order": ("fleet", "agv"), "instantActions": ("fleet", "agv"), "state": ("agv", "fleet"),
    "visualization": ("agv", "fleet"), "connection": ("agv", "fleet"), "factsheet": ("agv", "fleet"),
    "commonMessage": ("agv", "fleet"),
}

BOXW, GAPX, GAPY = 230, 104, 16
HEAD, ROW, NOTE = 30, 17, 13
FLOWH = 40
NAMEW, TYPEW = 6.3, 4.9          # approx px per char: 10.5 px mono, 9.5 px sans


def wrap(t, n=40):
    return textwrap.wrap(t, n) if t else []


def tstr(typ, unit):
    return f"{typ} · {unit}" if unit else typ


class Node:
    def __init__(self, cls, role=None, mult=None, root=False):
        self.cls, self.role, self.mult, self.root = cls, role, mult, root
        self.hl = {}
        self.children = []
        self.rid = None
        self.cnote = None
        self.x = self.y = 0

    def rids(self):
        out = []
        if self.rid:
            out += self.rid.split()
        for rid, _ in self.hl.values():
            if rid:
                out += rid.split()
        for c in self.children:
            out += c.rids()
        seen = []
        for r in out:
            if r not in seen:
                seen.append(r)
        return seen

    def rows(self):
        _, attrs, kids = SCHEMA[self.cls]
        out = []
        if self.root:
            out.append(("header",))
        for name, typ, unit, long in attrs:
            rid, note = self.hl.get(name, (None, None))
            out.append(("field", name, tstr(typ, unit), rid, note or long))
        exp = {c.role: c for c in self.children}
        for role, mult, cls in kids:
            out.append(("part", role, mult, cls, exp.get(role)))
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
            _, attrs, kids = SCHEMA[cur.cls]
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


def _fits(name, t):
    return NAMEW * len(name) + TYPEW * len(t) + 22 < BOXW - 12


def row_h(r):
    if r[0] == "header":
        return ROW + 2 * NOTE
    if r[0] == "field":
        _, name, t, rid, note = r
        if rid:
            return ROW + NOTE * (1 + len(wrap(note)))
        extra = 0 if _fits(name, t) else NOTE
        return ROW + extra
    return ROW


def box_h(n):
    h = HEAD + 6 + sum(row_h(r) for r in n.rows())
    if n.cnote:
        h += NOTE * (len(wrap(n.cnote)) + 1)
    return max(h, HEAD + 16) + 4


def row_offsets(n):
    """y offset (from box top) of the centre of each part row."""
    yy = HEAD + 4 + (NOTE * (len(wrap(n.cnote)) + 1) if n.cnote else 0)
    offs = {}
    for r in n.rows():
        h = row_h(r)
        if r[0] == "part":
            offs[r[1]] = yy + h / 2
        yy += h
    return offs


def layout(n, x, y):
    n.x, n.y = x, y
    bottom = y + box_h(n)
    offs = row_offsets(n)
    cy = y
    for c in n.children:
        want = y + offs[c.role] - HEAD / 2
        cy = max(cy, want)
        cb = layout(c, x + BOXW + GAPX, cy)
        cy = cb + GAPY
        bottom = max(bottom, cb)
    return bottom


def depth(n):
    return 1 + max((depth(c) for c in n.children), default=0)


def _pill(s, right, y, rid, color=None):
    w = 10 + len(rid) * 6.0
    s.rect(right - w, y, w, 15, fill=color or C["accent"], rx=7.5)
    s.text(right - w / 2, y + 11, rid, size=9.5, anchor="middle", color="#FFFFFF", weight=600, mono=True)


def server_icon(s, x, y):
    for i in range(3):
        s.rect(x, y + i * 8, 22, 7, fill=C["card"], stroke=C["fg"], sw=1.3, rx=1.5)
        s.circle(x + 17, y + i * 8 + 3.5, 1.4, fill=C["green"])
        s.line(x + 4, y + i * 8 + 3.5, x + 11, y + i * 8 + 3.5, C["fg"], 1.2)


def agv_icon(s, x, y):
    s.robot(x + 15, y + 11, 0, scale=0.42)


def flow_badge(s, root, x, y):
    src, dst = FLOW[root]
    lab = {"fleet": "fleet manager", "agv": "AGV"}
    s.rect(x, y, BOXW, FLOWH - 8, fill=C["bg"], stroke=C["border"], rx=6)
    cx = x + 8
    for i, who in enumerate((src, dst)):
        if who == "fleet":
            server_icon(s, cx, y + 4)
            w = 26
        else:
            agv_icon(s, cx - 2, y + 5)
            w = 30
        s.text(cx + w + 2, y + 21, lab[who], size=10.5, color=C["fg"], weight=600)
        cx += w + 6 + len(lab[who]) * 5.6
        if i == 0:
            s.arrow(cx + 2, y + 16, cx + 30, y + 16, "accent", 2)
            cx += 40
    s.text(x + BOXW - 8, y + 21, "publishes →" if False else "", size=9, anchor="end")


def draw(s, n):
    x, y = n.x, n.y
    h = box_h(n)
    stereo = SCHEMA[n.cls][0]
    hl = n.rid is not None
    edge = C["accent"] if hl else C["fg"]
    s.rect(x, y, BOXW, h, fill=C["card"], stroke=edge, sw=2 if hl else 1.4, rx=4)
    s.rect(x, y, BOXW, HEAD, fill=C["fg"] if n.root else C["bg"], rx=4)
    s.rect(x, y + HEAD - 4, BOXW, 4, fill=C["fg"] if n.root else C["bg"])
    s.line(x, y + HEAD, x + BOXW, y + HEAD, edge, 1)
    if n.root:
        s.text(x + 10, y + 12, f"«{stereo}»", size=9.5, color="#BFDBFE")
        s.text(x + 10, y + 25, n.cls, size=13, weight=700, color="#FFFFFF", mono=True)
    else:
        s.text(x + 10, y + 12, f"«object» type {n.cls}", size=9, color=C["mutedfg"])
        s.text(x + 10, y + 25, n.role + ("[ ]" if n.mult.endswith("*") else ""), size=12.5, weight=700, color=C["fg"], mono=True)
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
            lab = "header (assumed same as VDA5050)" if n.cls == "commonMessage" else "header (in every VDA5050 message)"
            s.text(x + 10, yy + 12, lab, size=10, color=C["slate"], weight=600)
            for i, ln in enumerate(HEADER):
                s.text(x + 18, yy + 12 + NOTE * (i + 1), ln, size=9, color=C["slate"])
        elif r[0] == "field":
            _, name, t, rid, note = r
            if rid:
                s.rect(x + 3, yy + 1, BOXW - 6, rh - 2, fill=C["accent"], rx=3, opacity=0.14)
                s.text(x + 10, yy + 12.5, name, size=10.5, mono=True, weight=700, color=C["ink"])
                _pill(s, x + BOXW - 6, yy + 1.5, rid)
                s.text(x + 18, yy + 12.5 + NOTE, t, size=9.5, color=C["fg"], weight=600)
                for i, ln in enumerate(wrap(note)):
                    s.text(x + 18, yy + 12.5 + NOTE * (i + 2), ln, size=9.5, color=C["accent"])
            else:
                s.text(x + 10, yy + 12.5, name, size=10.5, mono=True, color=C["mutedfg"])
                if _fits(name, t):
                    s.text(x + BOXW - 8, yy + 12.5, t, size=9.5, anchor="end", color="#94A3B8")
                else:
                    s.text(x + BOXW - 8, yy + 12.5 + NOTE, t, size=9.5, anchor="end", color="#94A3B8")
        else:
            _, role, mult, cls, child = r
            label = role + ("[ ]" if mult.endswith("*") else "")
            on = child is not None
            col = C["primary"] if on else C["slate"]
            if on:
                s.rect(x + 3, yy + 1, BOXW - 6, rh - 2, fill=C["primary"], rx=3, opacity=0.12)
            s.raw(f'<path d="M {x+10} {yy+8.5} L {x+14} {yy+5.5} L {x+18} {yy+8.5} L {x+14} {yy+11.5} Z" fill="{col}"/>')
            s.text(x + 23, yy + 12.5, label, size=10.5, mono=True, color=col, weight=700 if on else 400)
            if on:
                rids = child.rids()
                txt = " ".join(rids) if len(" ".join(rids)) <= 14 else f"{rids[0]} … {rids[-1]}"
                _pill(s, x + BOXW - 6, yy + 1.5, txt, C["primary"])
            elif NAMEW * len(label) + TYPEW * len(cls) + 30 < BOXW - 12:
                s.text(x + BOXW - 8, yy + 12.5, cls, size=9, anchor="end", color="#94A3B8")
        yy += rh
    offs = row_offsets(n)
    px = x + BOXW
    for c in n.children:
        sy = y + offs[c.role]
        ty = c.y + HEAD / 2
        cx = c.x
        mx = px + 14
        s.raw(f'<path d="M {px} {sy} L {px+6} {sy-4.5} L {px+12} {sy} L {px+6} {sy+4.5} Z" fill="{C["primary"]}"/>')
        s.path(f"M {px+12} {sy} L {mx} {sy} L {mx} {ty} L {cx} {ty}", C["primary"], 1.4)
        s.text(cx - 5, ty - 5, c.role, size=10, anchor="end", color=C["primary"], mono=True, weight=600)
        s.text(cx - 5, ty + 13, c.mult, size=9.5, anchor="end", color=C["mutedfg"], mono=True)
        draw(s, c)


def figure(title, subtitle, roots, notes=None):
    trees = [build(r, p) for r, p in roots]
    d = max(depth(t) for t in trees)
    width = max(960, int(56 + d * BOXW + (d - 1) * GAPX))
    y = 96
    for t in trees:
        b = layout(t, 28, y + FLOWH)
        t._badge_y = y
        y = b + 28
    notes = notes or []
    h = y + 64 + len(notes) * 18 + 10
    s = SVG(width, int(h), title, subtitle)
    for t in trees:
        flow_badge(s, t.cls, 28, t._badge_y)
        draw(s, t)
    ly = y + 2
    s.raw(f'<path d="M 28 {ly} L 34 {ly-4.5} L 40 {ly} L 34 {ly+4.5} Z" fill="{C["primary"]}"/>')
    s.line(40, ly, 70, ly, C["primary"], 1.4)
    s.text(76, ly + 4, "composition: JSON key and multiplicity on the line", size=11, color=C["mutedfg"])
    _pill(s, 410, ly - 7, "x.y")
    s.text(418, ly + 4, "field a requirement depends on", size=11, color=C["mutedfg"])
    _pill(s, 640, ly - 7, "x.y", C["primary"])
    s.text(648, ly + 4, "nested object on the path to it", size=11, color=C["mutedfg"])
    ly2 = ly + 22
    s.text(28, ly2 + 4, "grey rows: the object's other fields, with data type · unit", size=11, color=C["mutedfg"])
    s.text(400, ly2 + 4, "0..1 optional · 1 required · 0..* / 1..* array [ ]", size=11, color=C["mutedfg"], mono=True)
    for i, t in enumerate(notes):
        s.text(28, ly2 + 26 + i * 18, t, size=11.5, color=C["mutedfg"])
    return s
