"""Pecos facility drawing: loads the YAML layout and renders it top-down in metres.

All node positions and edges come from sources/5675_pecos_combined.yaml. Stall rectangles use
the layout's XL parking window (length along x, width along y), centred on each Parking node.
AGVs, trays and payloads are *drawn on request* only - the YAML has no occupancy.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from svgkit import BBox, Doc, text_width, pts_to_path
from components import chip, num_badge
from theme import T, S

ROOT = Path(__file__).resolve().parents[2]
YAML = ROOT / "sources" / "5675_pecos_combined.yaml"

WP_LABEL_BELOW = {9}   # W9 sits right under charger C10
PREFIX = {"Parking": "P", "Waypoint": "W", "Bay": "B", "AgvCharge": "C"}
C_PARK, C_BAY, C_CHG, C_WP = T.sky, T.teal, T.violet, T.fg2


@dataclass
class Node:
    id: int
    x: float
    y: float
    type: str
    headings: list
    rotation: bool
    reciprocal: bool
    section: str

    @property
    def label(self):
        return f"{PREFIX[self.type]}{self.id}"


def load():
    """Read nodes/edges/windows with PyYAML; YAML section comments (sandbox_eng / sandbox_qa) are
    recovered from the raw text because PyYAML drops comments."""
    import yaml
    raw = YAML.read_text()
    data = yaml.safe_load(raw)
    section, sec_of = "", {}
    for line in raw.splitlines():
        m = re.match(r"\s*#\s*5675_pecos_(\w+)", line)
        if m:
            section = m.group(1)
        m = re.match(r"\s*- id:\s*(\d+)", line)
        if m:
            sec_of[int(m.group(1))] = section
    nodes = {n["id"]: Node(n["id"], float(n["x"]), float(n["y"]), n["type"], list(n.get("headings", [])),
                           bool(n.get("rotation_allowed")), bool(n.get("faces_reciprocal")), sec_of[n["id"]])
             for n in data["nodes"]}
    edges = [(e["src"], e["dst"]) for e in data["edges"]]
    windows = {w["name"]: w for w in data["parking_windows"]}
    return nodes, edges, windows


NODES, EDGES, WINDOWS = load()
assert len(NODES) == 28 and len(EDGES) == 37, (len(NODES), len(EDGES))
STALL_L = WINDOWS["XL"]["length_m"]   # 5.791 m along x
STALL_W = WINDOWS["XL"]["width_m"]    # 2.21 m along y


class Map:
    def __init__(self, doc: Doc, ox: float, oy: float, scale: float, xlim, ylim):
        self.d = doc
        self.ox, self.oy, self.s = ox, oy, scale
        self.xmin, self.xmax = xlim
        self.ymin, self.ymax = ylim

    # world -> svg
    def X(self, x):
        return self.ox + (x - self.xmin) * self.s

    def Y(self, y):
        return self.oy + (self.ymax - y) * self.s

    def P(self, nid_or_xy):
        if isinstance(nid_or_xy, int):
            n = NODES[nid_or_xy]
            return self.X(n.x), self.Y(n.y)
        return self.X(nid_or_xy[0]), self.Y(nid_or_xy[1])

    def clip(self):
        self.d.clip_on(self.box, rx=10)

    def unclip(self):
        self.d.clip_off()

    @property
    def box(self):
        return BBox(self.X(self.xmin), self.Y(self.ymax), self.X(self.xmax), self.Y(self.ymin))

    def visible(self, n: Node, margin=0.0):
        return self.xmin - margin <= n.x <= self.xmax + margin and self.ymin - margin <= n.y <= self.ymax + margin

    # ----------------------------------------------------------------------------------
    def floor(self, *, axes=True, tick=None, grid=True):
        d, b = self.d, self.box
        tick = tick or (2 if self.s > 45 else 5)
        d.rect(b.x0, b.y0, b.w, b.h, rx=10, fill=T.bg_deep, stroke=T.border_soft, sw=1, layer="bg")
        self.clip()
        if grid:
            for gx in range(math.ceil(self.xmin), math.floor(self.xmax) + 1):
                major = gx % tick == 0
                d.line(self.X(gx), b.y0 + 1, self.X(gx), b.y1 - 1, stroke=T.grid if not major else "#253247",
                       sw=1 if major else 0.6, layer="bg", cap="butt")
            for gy in range(math.ceil(self.ymin), math.floor(self.ymax) + 1):
                major = gy % tick == 0
                d.line(b.x0 + 1, self.Y(gy), b.x1 - 1, self.Y(gy), stroke=T.grid if not major else "#253247",
                       sw=1 if major else 0.6, layer="bg", cap="butt")
        if axes:
            self.unclip()
            for gx in range(math.ceil(self.xmin), math.floor(self.xmax) + 1):
                if gx % tick == 0:
                    d.line(self.X(gx), b.y1, self.X(gx), b.y1 + 5, stroke=T.border, sw=1)
                    d.text(self.X(gx), b.y1 + 16, f"{gx}", size=S.tiny, family="mono", fill=T.muted, anchor="middle")
            for gy in range(math.ceil(self.ymin), math.floor(self.ymax) + 1):
                if gy % tick == 0:
                    d.line(b.x0 - 5, self.Y(gy), b.x0, self.Y(gy), stroke=T.border, sw=1)
                    d.text(b.x0 - 9, self.Y(gy), f"{gy}", size=S.tiny, family="mono", fill=T.muted, anchor="end")
            d.text(b.x1, b.y1 + 32, "x [m]", size=S.small, family="mono", fill=T.muted, anchor="end")
            d.text(b.x0 - 9, b.y0 - 12, "y [m]", size=S.small, family="mono", fill=T.muted, anchor="end")

    def zones(self):
        """Dashed outline per YAML section (sandbox_eng / sandbox_qa)."""
        d = self.d
        groups = {}
        for n in NODES.values():
            groups.setdefault(n.section, []).append(n)
        for sec, ns in groups.items():
            xs0 = [n.x - (STALL_L / 2 if n.type in ("Parking", "Bay") else 0.6) for n in ns]
            xs1 = [n.x + (STALL_L / 2 if n.type in ("Parking", "Bay") else 0.6) for n in ns]
            ys0 = [n.y - (STALL_W / 2 if n.type in ("Parking", "Bay") else 0.6) for n in ns]
            ys1 = [n.y + (STALL_W / 2 if n.type in ("Parking", "Bay") else 0.6) for n in ns]
            m = 0.45
            x0, x1 = max(min(xs0) - m, self.xmin + 0.15), min(max(xs1) + m, self.xmax - 0.15)
            y0, y1 = max(min(ys0) - m, self.ymin + 0.15), min(max(ys1) + m + 0.55, self.ymax - 0.15)
            if x1 <= x0 or y1 <= y0:
                continue
            d.rect(self.X(x0), self.Y(y1), (x1 - x0) * self.s, (y1 - y0) * self.s, rx=8, fill="none",
                   stroke="#2C3A52", sw=1.2, dash="6 5", layer="bg")
            d.text(self.X(x0) + 8, self.Y(y1) + 10, f"yaml: 5675_pecos_{sec}", size=10.5, family="mono",
                   fill=T.faint, layer="bg")

    def corridors(self):
        """Light bands under waypoint-to-waypoint edges (and bay connectors) = travel corridors."""
        d = self.d
        w = STALL_W * self.s
        for a, b in EDGES:
            A, B = NODES[a], NODES[b]
            if {A.type, B.type} <= {"Waypoint", "Bay"} and not (A.type == B.type == "Bay"):
                if not (self.visible(A, 3) or self.visible(B, 3)):
                    continue
                x0, y0 = self.P(a)
                x1, y1 = self.P(b)
                d.path(f"M{x0} {y0} L{x1} {y1}", stroke="#18233A", sw=w, cap="square", layer="bg",
                       bbox=BBox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def stalls(self, *, labels=True, dim=False, highlight=()):
        d = self.d
        for n in NODES.values():
            if n.type != "Parking" or not self.visible(n, 3):
                continue
            x, y = self.P(n.id)
            w, h = STALL_L * self.s - 3, STALL_W * self.s - 3
            hl = n.id in highlight
            d.rect(x - w / 2, y - h / 2, w, h, rx=4, fill=T.tint(C_PARK, 0.10 if not dim else 0.06, T.bg_deep),
                   stroke=T.tint(C_PARK, 0.55 if not dim else 0.32, T.bg_deep) if not hl else C_PARK,
                   sw=1.2 if not hl else 2, layer="under")
            if labels and self.box.pad(-4).intersects(BBox(x - w / 2 + 7, y - h / 2 + 4, x - w / 2 + 30, y - h / 2 + 16)):
                d.text(x - w / 2 + 7, y - h / 2 + 10, n.label, size=11 if self.s > 30 else 10, family="mono",
                       weight=600, fill=T.tint(C_PARK, 0.9 if not dim else 0.6, T.bg_deep), layer="labels",
                       halo=T.bg_deep, halo_w=3)

    def bays(self, *, labels=True):
        d = self.d
        for n in NODES.values():
            if n.type != "Bay" or not self.visible(n, 3):
                continue
            x, y = self.P(n.id)
            w, h = STALL_L * self.s - 3, (STALL_W + 0.9) * self.s
            d.rect(x - w / 2, y - h / 2, w, h, rx=8, fill=T.tint(C_BAY, 0.12, T.bg_deep), stroke=C_BAY, sw=1.6,
                   layer="under")
            # door on the garage side (east) - faces_reciprocal
            d.line(x + w / 2, y - h / 2 + 6, x + w / 2, y + h / 2 - 6, stroke=C_BAY, sw=4.5, cap="round",
                   layer="under")
            if labels:
                d.text(x - w / 2 + 9, y - h / 2 + 12, n.label, size=12, family="mono", weight=700, fill=C_BAY,
                       layer="under")
                d.text(x - w / 2 + 9, y + h / 2 - 11, "customer bay", size=10, fill=T.tint(C_BAY, 0.75, T.bg_deep),
                       layer="under")

    def edges(self, *, color="#55657F", sw=1.5):
        d = self.d
        for a, b in EDGES:
            A, B = NODES[a], NODES[b]
            if not (self.visible(A, 1) or self.visible(B, 1)):
                continue
            (x0, y0), (x1, y1) = self.P(a), self.P(b)
            d.line(x0, y0, x1, y1, stroke=color, sw=sw, layer="edges")

    def nodes(self, *, labels=True, label_types=("Waypoint", "AgvCharge"), only=None, dim=False):
        d = self.d
        for n in NODES.values():
            if not self.visible(n, 0.2):
                continue
            x, y = self.P(n.id)
            if n.type == "Waypoint":
                d.circle(x, y, 4.5, fill=C_WP if not dim else T.faint, stroke=T.bg_deep, sw=1.5, layer="over")
                if labels and n.type in label_types and (only is None or n.id in only):
                    dy = 12 if n.id in WP_LABEL_BELOW else -10
                    d.text(x - 7, y + dy, n.label, size=10.5, family="mono", fill=T.muted, anchor="end",
                           halo=T.bg_deep, halo_w=3.5, layer="labels")
            elif n.type == "Parking":
                d.circle(x, y, 2.6, fill=T.tint(C_PARK, 0.8, T.bg_deep), layer="over")
            elif n.type == "Bay":
                d.circle(x, y, 3.2, fill=C_BAY, layer="over")
            elif n.type == "AgvCharge":
                r = max(9, 0.36 * self.s)
                d.circle(x, y, r, fill=T.tint(C_CHG, 0.25, T.bg_deep), stroke=C_CHG, sw=1.6, layer="over")
                bolt = [(x + 0.12 * r, y - 0.62 * r), (x - 0.38 * r, y + 0.1 * r), (x - 0.02 * r, y + 0.1 * r),
                        (x - 0.14 * r, y + 0.62 * r), (x + 0.38 * r, y - 0.12 * r), (x + 0.02 * r, y - 0.12 * r)]
                d.polygon(bolt, fill=C_CHG, layer="over", join="round")
                if labels and n.type in label_types and (only is None or n.id in only):
                    d.text(x + r + 5, y + 2, n.label, size=11, family="mono", weight=600, fill=C_CHG,
                           halo=T.bg_deep, halo_w=3.5, layer="labels")

    def base(self, *, labels=True, dim=False, highlight=(), axes=True, zones=True):
        self.floor(axes=axes)
        self.clip()
        if zones:
            self.zones()
        self.corridors()
        self.stalls(labels=labels, dim=dim, highlight=highlight)
        self.bays(labels=labels)
        self.edges()
        self.nodes(labels=labels, dim=dim)
        self.unclip()

    # ----------------------------------------------------------------------------------
    # entities (hypothetical occupancy)
    # ----------------------------------------------------------------------------------
    def tray(self, nid, label, *, color=T.amber, payload=False, emphasis=False, chip_pos="bl"):
        d = self.d
        x, y = self.P(nid)
        w, h = (STALL_L - 0.5) * self.s, (STALL_W - 0.32) * self.s
        d.rect(x - w / 2, y - h / 2, w, h, rx=6, fill=T.tint(color, 0.20, T.bg_deep), stroke=color,
               sw=2.2 if emphasis else 1.6, layer="main")
        # tray rails
        for f in (-0.28, 0.28):
            d.line(x - w / 2 + 6, y + f * h, x + w / 2 - 6, y + f * h, stroke=T.tint(color, 0.45, T.bg_deep), sw=1,
                   layer="main")
        if payload:
            self.car(x, y, w * 0.78, h * 0.72)
        if label and chip_pos == "bl":
            chip(self.d, x - w / 2 + 4, y + h / 2 - 2, label, color, anchor="start", size=10.5,
                 fill=T.tint(color, 0.3, T.bg_deep), layer="labels")
        elif label:
            chip(self.d, x + w / 2 - 4, y - h / 2 + 2, label, color, anchor="end", size=10.5,
                 fill=T.tint(color, 0.3, T.bg_deep), layer="labels")

    def car(self, x, y, w, h, color=T.pink):
        """Top-down car silhouette facing west (heading 90)."""
        d = self.d
        d.rect(x - w / 2, y - h / 2, w, h, rx=h * 0.42, fill=T.tint(color, 0.28, T.bg_deep), stroke=color, sw=1.3,
               layer="main")
        # windshield (front = west / left) and rear window
        d.rect(x - w / 2 + w * 0.2, y - h / 2 + h * 0.16, w * 0.14, h * 0.68, rx=3, fill=T.tint(color, 0.55, T.bg_deep),
               layer="main")
        d.rect(x + w / 2 - w * 0.24, y - h / 2 + h * 0.2, w * 0.1, h * 0.6, rx=3, fill=T.tint(color, 0.45, T.bg_deep),
               layer="main")

    def agv(self, xy, label, *, heading=90, color=T.green, label_side="below", lifted=False):
        """Top-down AGV (~2.2 m x 1.1 m, schematic size). heading 90 = facing west per GaragePose convention."""
        d = self.d
        x, y = self.P(xy)
        L, Wd = 2.2 * self.s, 1.1 * self.s
        ang = {90: 180, 270: 0, 0: -90, 180: 90}.get(heading, 180)  # svg rotation: facing -x
        g = []
        hx, hy = L / 2, Wd / 2
        wheel = f'<rect x="{-hx + 0.16 * L}" y="{-hy - 3}" width="{0.2 * L}" height="5" rx="2" fill="#CBD5E1"/>' \
                f'<rect x="{hx - 0.36 * L}" y="{-hy - 3}" width="{0.2 * L}" height="5" rx="2" fill="#CBD5E1"/>' \
                f'<rect x="{-hx + 0.16 * L}" y="{hy - 2}" width="{0.2 * L}" height="5" rx="2" fill="#CBD5E1"/>' \
                f'<rect x="{hx - 0.36 * L}" y="{hy - 2}" width="{0.2 * L}" height="5" rx="2" fill="#CBD5E1"/>'
        body = f'<rect x="{-hx}" y="{-hy}" width="{L}" height="{Wd}" rx="{Wd * 0.28}" fill="{T.tint(color, 0.22, T.bg_deep)}" stroke="{color}" stroke-width="2"/>'
        plate = f'<rect x="{-hx + 0.3 * L}" y="{-hy + 0.22 * Wd}" width="{0.4 * L}" height="{0.56 * Wd}" rx="3" fill="{T.tint(color, 0.5 if lifted else 0.3, T.bg_deep)}" stroke="{T.tint(color, 0.7, T.bg_deep)}" stroke-width="1"/>'
        chev = f'<path d="M{hx - 0.2 * L} {-0.26 * Wd} L{hx - 0.06 * L} 0 L{hx - 0.2 * L} {0.26 * Wd}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
        d.raw(f'<g transform="translate({x:.2f} {y:.2f}) rotate({ang})">{wheel}{body}{plate}{chev}</g>', "top",
              BBox(x - L / 2 - 4, y - L / 2 - 4, x + L / 2 + 4, y + L / 2 + 4))
        if label:
            if label_side == "below":
                chip(d, x, y + Wd / 2 + 16, label, color, anchor="middle", size=10.5,
                     fill=T.tint(color, 0.25, T.bg_deep), layer="top")
            elif label_side == "above":
                chip(d, x, y - Wd / 2 - 16, label, color, anchor="middle", size=10.5,
                     fill=T.tint(color, 0.25, T.bg_deep), layer="top")
            elif label_side == "left":
                chip(d, x - L / 2 - 8, y, label, color, anchor="end", size=10.5,
                     fill=T.tint(color, 0.25, T.bg_deep), layer="top")
            else:
                chip(d, x + L / 2 + 8, y, label, color, anchor="start", size=10.5,
                     fill=T.tint(color, 0.25, T.bg_deep), layer="top")

    def route(self, ids, color, *, sw=4, dash=None, offset=(0, 0), num=None, num_at=0, head=True, layer="over"):
        """Route along node ids (graph walk). offset in px shifts the whole route (to separate overlaps)."""
        pts = [self.P(i) if isinstance(i, int) else self.P(i) for i in ids]
        pts = [(x + offset[0], y + offset[1]) for x, y in pts]
        d = self.d
        # shorten end for the arrowhead
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
        L = math.hypot(xb - xa, yb - ya)
        hl = 13
        end = (xb - (xb - xa) / L * hl * 0.8, yb - (yb - ya) / L * hl * 0.8) if head else pts[-1]
        body = pts[:-1] + [end]
        d.path(pts_to_path(body, 8), stroke=T.bg_deep, sw=sw + 4, dash=None, layer=layer, opacity=0.9)
        d.path(pts_to_path(body, 8), stroke=color, sw=sw, dash=dash, layer=layer)
        if head:
            d.arrowhead((xb, yb), (xa, ya), kind="filled", color=color, size=hl, layer=layer)
        if num is not None:
            nx, ny = pts[num_at]
            num_badge(d, nx, ny, num, color, r=11)
        return pts
