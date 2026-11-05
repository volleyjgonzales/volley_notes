#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["plotly>=6.1", "rich>=13", "pyyaml>=6"]
# ///
"""Render a layout YAML file as a standalone, interactive HTML floor plan.

Runs anywhere: it reads the layout YAML itself (no ROS, no common_py), and `uv run` installs
its three dependencies from the block above on first use.

The drawing follows the facility map of the design docs (scripts/diagrams/facility.py):
everything is in metres on a floor with a 1 m / 5 m grid, parking nodes are drawn as stalls the
size of the largest parking window and turned to the node's heading, bays are rounded customer
bays with a door on the aisle side, waypoint aisles sit on corridor bands, and chargers and
lifts get small icons. Hover any node for its details; click a legend entry to hide a layer;
the half-circle button in the toolbar switches between the dark and light theme, and
floor tabs (or keys 1-9, [ and ]) switch floors on multi-floor layouts.

Layouts are found by name in src/config/site_config/layouts of the volley workspace
(--list shows where it looked; --layouts-dir or $VOLLEY_LAYOUTS add folders).

Examples:
    uv run layout_plotter.py --list
    uv run layout_plotter.py 5675_pecos_combined --show
    uv run layout_plotter.py ~/volley/src/config/site_config/layouts/5675_pecos_combined.yaml
    uv run layout_plotter.py 5675_pecos_combined --layouts-dir ~/code/volley/src/config/site_config/layouts
"""

import argparse
import html
import itertools
import json
import math
import os
import re
import subprocess
import sys
import webbrowser
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from dataclasses import field as dataclass_field
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal

import plotly.graph_objects as go
import yaml
from plotly.offline import get_plotlyjs, get_plotlyjs_version
from rich.console import Console
from rich.markup import escape
from rich.table import Table

# Bumped when scenario_plotter.py needs something new from this module; it checks this on import.
API_VERSION: Final = 3

type Point = tuple[float, float]
type Polygon = tuple[Point, ...]

# Layout YAML as read by this script (the keys facility.py reads):
#   parking_windows: [{name, length_m, width_m}, ...]
#   nodes: [{id, x, y, type: Waypoint|Parking|Bay|AgvCharge|..., headings: [deg], rotation_allowed,
#            floor (optional, default 0)}, ...]
#   edges: [{src, dst}, ...]           (node ids; edges between floors are not drawn)
type YamlDoc = Mapping[str, Any]


# =============================================================================================
# Theme (scripts/diagrams/theme.py + lightmode.py: ui-ux-pro-max "Developer Tool / IDE")
# =============================================================================================

FONT_MONO: Final = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
FONT_SANS: Final = "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
GOOGLE_FONTS_URL: Final = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap"
)


class ThemeName(StrEnum):
    AUTO = "auto"
    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True, slots=True, kw_only=True)
class Palette:
    """Colour roles. Categorical hues: parking sky, bay violet, charger yellow, lift teal, tray orange,
    AGV green, payload pink - checked for separation in both themes (EV chargers reuse the charger
    yellow with a payload-pink ring; Lift and BLift share teal and differ by label)."""

    scheme: Literal["dark", "light"]
    bg: str
    floor: str
    card: str
    grid_minor: str
    grid_major: str
    corridor: str
    fg: str
    fg2: str
    muted: str
    faint: str
    border: str
    border_soft: str
    edge: str
    parking: str
    bay: str
    charger: str
    ev: str
    lift: str
    blift: str
    agv: str
    tray: str
    payload: str
    danger: str
    axis_x: str  # map frame arrows, ROS colours: x red, y green
    axis_y: str


DARK: Final = Palette(
    scheme="dark",
    bg="#0F172A",
    floor="#0B1222",
    card="#1B2336",
    grid_minor="#1F2B3F",
    grid_major="#2C3B54",
    corridor="#18233A",
    fg="#F8FAFC",
    fg2="#CBD5E1",
    muted="#94A3B8",
    faint="#64748B",
    border="#475569",
    border_soft="#334155",
    edge="#55657F",
    parking="#38BDF8",
    bay="#A78BFA",
    charger="#FACC15",
    ev="#F472B6",
    lift="#5EEAD4",
    blift="#5EEAD4",
    agv="#22C55E",
    tray="#F97316",
    payload="#F472B6",
    danger="#EF4444",
    axis_x="#F87171",
    axis_y="#4ADE80",
)

LIGHT: Final = Palette(
    scheme="light",
    bg="#FFFFFF",
    floor="#F8FAFC",
    card="#FFFFFF",
    grid_minor="#E5EAF1",
    grid_major="#D2DBE6",
    corridor="#E8EDF4",
    fg="#0F172A",
    fg2="#334155",
    muted="#475569",
    faint="#64748B",
    border="#94A3B8",
    border_soft="#CBD5E1",
    edge="#94A3B8",
    parking="#0369A1",
    bay="#7C3AED",
    charger="#CA8A04",
    ev="#DB2777",
    lift="#0D9488",
    blift="#0D9488",
    agv="#15803D",
    tray="#C2410C",
    payload="#DB2777",
    danger="#B91C1C",
    axis_x="#DC2626",
    axis_y="#16A34A",
)

PALETTES: Final[Mapping[ThemeName, Palette]] = {ThemeName.DARK: DARK, ThemeName.LIGHT: LIGHT}


def tint(color: str, alpha: float, over: str) -> str:
    """Blend `color` over `over` at `alpha` -> opaque hex (no opacity stacking where shapes overlap)."""
    fg, bg = (tuple(int(c[i : i + 2], 16) for i in (1, 3, 5)) for c in (color, over))
    return "#" + "".join(f"{round(b + (f - b) * alpha):02X}" for f, b in zip(fg, bg, strict=True))


# =============================================================================================
# Plain data extracted from the layout
# =============================================================================================

UNKNOWN: Final = "Unknown"
DEFAULT_HEADING: Final = 90.0  # deg; 0 = world +y, counter-clockwise positive (GaragePose.msg)
DEFAULT_STALL: Final = (5.791, 2.21)  # m; Pecos XL parking window (length, width)

PREFIX: Final[Mapping[str, str]] = {
    "Waypoint": "W",
    "Parking": "P",
    "Bay": "B",
    "AgvCharge": "C",
    "EvCharge": "E",
    "Lift": "L",
    "BLift": "BL",
}


@dataclass(frozen=True, slots=True)
class PlotNode:
    id: int
    x: float
    y: float
    floor: int
    kind: str
    heading: float
    rotation_allowed: bool
    vrc: int | None = None  # id of the VRC (vertical lift) this node is a stop of

    @property
    def xy(self) -> Point:
        return (self.x, self.y)

    @property
    def label(self) -> str:
        return f"{PREFIX.get(self.kind, 'N')}{self.id}"


@dataclass(frozen=True, slots=True)
class StallSize:
    length: float  # along the heading (the AGV's long side)
    width: float


type Edge = tuple[PlotNode, PlotNode]


@dataclass(frozen=True, slots=True)
class Scene:
    nodes: tuple[PlotNode, ...]
    edges: tuple[Edge, ...]
    stall: StallSize
    notes: tuple[str, ...]  # assumptions made while reading the layout
    floor_z: Mapping[int, float] = dataclass_field(default_factory=dict)  # floors: [{id, z}]
    vrcs: Mapping[int, tuple[int, ...]] = dataclass_field(default_factory=dict)  # vrc id -> node ids


def field(obj: object, *names: str) -> Any:
    """First present attribute or mapping key among `names` (layout objects vary: msgs, dicts)."""
    for name in names:
        if isinstance(obj, Mapping) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def node_heading(node: YamlDoc) -> float | None:
    headings = field(node, "headings")
    if headings:
        return float(headings[0])
    heading = field(node, "heading")
    return None if heading is None else float(heading)


def layout_stall(doc: YamlDoc) -> StallSize | None:
    sizes = [
        (float(length), float(width))
        for w in field(doc, "parking_windows") or ()
        if (length := field(w, "length_m", "length")) is not None
        and (width := field(w, "width_m", "width")) is not None
    ]
    return StallSize(*max(sizes)) if sizes else None


def to_node(raw: YamlDoc, heading: float | None) -> PlotNode:
    return PlotNode(
        id=int(raw["id"]),
        x=float(raw["x"]),
        y=float(raw["y"]),
        floor=int(field(raw, "floor") or 0),
        kind=str(field(raw, "type") or UNKNOWN),
        heading=DEFAULT_HEADING if heading is None else heading,
        rotation_allowed=bool(field(raw, "rotation_allowed")),
    )


def build_scene(doc: YamlDoc, stall_override: StallSize | None) -> Scene:
    raw_nodes: Sequence[YamlDoc] = field(doc, "nodes") or ()
    headings = [node_heading(n) for n in raw_nodes]
    nodes = tuple(sorted(map(to_node, raw_nodes, headings), key=lambda n: n.id))
    by_id = {n.id: n for n in nodes}
    pairs = (
        (by_id.get(int(field(e, "src", "source"))), by_id.get(int(field(e, "dst", "target"))))
        for e in field(doc, "edges") or ()
    )
    edges = tuple((a, b) for a, b in pairs if a and b and a.floor == b.floor)

    vrcs = {
        int(field(v, "id")): tuple(int(i) for i in field(v, "nodes") or ())
        for v in field(doc, "vrcs") or ()
        if field(v, "id") is not None
    }
    stop_of = {node_id: vrc for vrc, ids in vrcs.items() for node_id in ids}
    nodes = tuple(replace(n, vrc=stop_of.get(n.id)) for n in nodes)
    edges = tuple((replace(a, vrc=stop_of.get(a.id)), replace(b, vrc=stop_of.get(b.id))) for a, b in edges)
    floor_z = {
        int(field(f, "id")): float(field(f, "z") or 0.0)
        for f in field(doc, "floors") or ()
        if field(f, "id") is not None
    }

    from_layout = layout_stall(doc)
    stall = stall_override or from_layout or StallSize(*DEFAULT_STALL)
    no_headings = bool(nodes) and all(h is None for h in headings)
    no_windows = stall_override is None and from_layout is None
    notes = (
        *(
            (f"no node headings found; stalls drawn at {DEFAULT_HEADING:g}° (long side along x)",)
            if no_headings
            else ()
        ),
        *(
            (f"no parking windows found; stalls drawn {stall.length:g} × {stall.width:g} m (use --stall)",)
            if no_windows
            else ()
        ),
    )
    return Scene(nodes=nodes, edges=edges, stall=stall, notes=notes, floor_z=floor_z, vrcs=vrcs)


def floors_of(scene: Scene) -> tuple[int, ...]:
    return tuple(sorted({n.floor for n in scene.nodes}))


def on_floor(scene: Scene, floor: int) -> Scene:
    return Scene(
        nodes=tuple(n for n in scene.nodes if n.floor == floor),
        edges=tuple(e for e in scene.edges if e[0].floor == floor),
        stall=scene.stall,
        notes=scene.notes,
        floor_z=scene.floor_z,
        vrcs=scene.vrcs,
    )


def neighbours(scene: Scene) -> Mapping[int, tuple[PlotNode, ...]]:
    adj: defaultdict[int, list[PlotNode]] = defaultdict(list)
    for a, b in scene.edges:
        adj[a.id].append(b)
        adj[b.id].append(a)
    return {k: tuple(v) for k, v in adj.items()}


# =============================================================================================
# Geometry (world metres, y up)
# =============================================================================================


def add(p: Point, q: Point, k: float = 1.0) -> Point:
    return (p[0] + q[0] * k, p[1] + q[1] * k)


def sub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def unit(v: Point) -> Point:
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


def dot(p: Point, q: Point) -> float:
    return p[0] * q[0] + p[1] * q[1]


def frame(heading_deg: float) -> tuple[Point, Point]:
    """(long axis, short axis) of a footprint facing `heading_deg` (0 = +y, CCW, 90 = -x)."""
    a = math.radians(heading_deg)
    u = (-math.sin(a), math.cos(a))
    return u, (-u[1], u[0])


def box(center: Point, length: float, width: float, heading_deg: float) -> Polygon:
    u, v = frame(heading_deg)
    return tuple(
        add(add(center, u, sl * length / 2), v, sw * width / 2)
        for sl, sw in ((1, 1), (-1, 1), (-1, -1), (1, -1))
    )


def rounded(poly: Polygon, radius: float, steps: int = 5) -> Polygon:
    """Round every corner of a convex polygon with a quadratic Bezier of `radius` metres."""

    def corner(i: int) -> Iterable[Point]:
        prev, p, nxt = poly[i - 1], poly[i], poly[(i + 1) % len(poly)]
        a = add(p, unit(sub(prev, p)), radius)
        b = add(p, unit(sub(nxt, p)), radius)
        for t in (s / steps for s in range(steps + 1)):
            yield (
                (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * p[0] + t**2 * b[0],
                (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * p[1] + t**2 * b[1],
            )

    return tuple(pt for i in range(len(poly)) for pt in corner(i))


def circle(center: Point, r: float, n: int = 32) -> Polygon:
    return tuple(
        (center[0] + r * math.cos(2 * math.pi * i / n), center[1] + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    )


def bolt(center: Point, r: float) -> Polygon:
    """Lightning bolt (icons.bolt), y flipped from SVG to world."""
    shape = ((0.12, 0.62), (-0.38, -0.1), (-0.02, -0.1), (-0.14, -0.62), (0.38, 0.12), (0.02, 0.12))
    return tuple((center[0] + dx * r, center[1] + dy * r) for dx, dy in shape)


def updown_arrow(center: Point, h: float) -> tuple[Polygon, ...]:
    """Vertical double arrow (icons.lift): shaft + two heads."""
    x, y = center
    s, hw = h * 0.06, h * 0.24
    shaft = ((x - s, y - h * 0.3), (x + s, y - h * 0.3), (x + s, y + h * 0.3), (x - s, y + h * 0.3))
    up = ((x - hw, y + h * 0.18), (x + hw, y + h * 0.18), (x, y + h * 0.48))
    down = ((x - hw, y - h * 0.18), (x + hw, y - h * 0.18), (x, y - h * 0.48))
    return (shaft, up, down)


def band(a: Point, b: Point, width: float) -> Polygon | None:
    """Rectangle of `width` along segment a-b with square caps (a corridor)."""
    d = unit(sub(b, a))
    if d == (0.0, 0.0):
        return None
    n = (-d[1], d[0])
    a2, b2 = add(a, d, -width / 2), add(b, d, width / 2)
    return (add(a2, n, width / 2), add(b2, n, width / 2), add(b2, n, -width / 2), add(a2, n, -width / 2))


def top_left(poly: Polygon) -> Point:
    """The vertex that is top-left on screen."""
    return max(poly, key=lambda p: (round(p[1], 3), -p[0]))


def bottom_left(poly: Polygon) -> Point:
    return min(poly, key=lambda p: (round(p[1], 3), p[0]))


def bounds(polys: Iterable[Polygon]) -> tuple[float, float, float, float]:
    pts = [p for poly in polys for p in poly]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


# =============================================================================================
# Trace primitives
# =============================================================================================


def flatten(
    polys: Iterable[Sequence[Point]], *, closed: bool
) -> tuple[list[float | None], list[float | None]]:
    """Polygons -> one x/y list with None gaps, so N shapes cost one trace."""
    xs: list[float | None] = []
    ys: list[float | None] = []
    for poly in polys:
        ring = (*poly, poly[0]) if closed else tuple(poly)
        xs.extend([*(p[0] for p in ring), None])
        ys.extend([*(p[1] for p in ring), None])
    return xs, ys


def grouped(group: str | None) -> dict[str, Any]:
    """Trace kwargs for a drawing trace: no legend entry, no hover, toggled with `group`."""
    return {"hoverinfo": "skip", "showlegend": False, "legendgroup": group}


def shapes(
    polys: Sequence[Polygon],
    *,
    fill: str | None,
    line: str | None,
    width: float = 1.2,
    dash: str | None = None,
    group: str | None = None,
) -> go.Scatter:
    xs, ys = flatten(polys, closed=True)
    return go.Scatter(
        x=xs,
        y=ys,
        mode="lines",
        fill="toself" if fill else None,
        fillcolor=fill,
        line={"color": line or "rgba(0,0,0,0)", "width": width if line else 0, "dash": dash},
        **grouped(group),
    )


def segments(
    segs: Sequence[tuple[Point, Point]], *, color: str, width: float, group: str | None = None
) -> go.Scatter:
    xs, ys = flatten(segs, closed=False)
    return go.Scatter(
        x=xs,
        y=ys,
        mode="lines",
        line={"color": color, "width": width},
        **grouped(group),
    )


def dots(
    points: Sequence[Point],
    *,
    size: float,
    color: str,
    outline: str | None = None,
    group: str | None = None,
) -> go.Scatter:
    return go.Scatter(
        x=[p[0] for p in points],
        y=[p[1] for p in points],
        mode="markers",
        marker={
            "symbol": "circle",
            "size": size,
            "color": color,
            "line": {"color": outline or color, "width": 1.5 if outline else 0},
        },
        **grouped(group),
    )


def labels(
    points: Sequence[Point],
    texts: Sequence[str],
    *,
    position: str,
    color: str,
    halo: str,
    group: str,
    size: float = 10.5,
    weight: int = 400,
    family: str = FONT_MONO,
) -> go.Scatter:
    return go.Scatter(
        x=[p[0] for p in points],
        y=[p[1] for p in points],
        mode="text",
        meta="label",  # the page hides these until zoomed in (see PAGE_SCRIPT)
        text=list(texts),
        textposition=position,
        textfont={
            "family": family,
            "size": size,
            "color": color,
            "weight": weight,
            "shadow": f"0 0 3px {halo}, 0 0 2px {halo}",
        },
        **grouped(group),
    )


HOVER: Final = (
    "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
    "x %{x:.3f} m · y %{y:.3f} m<br>"
    "heading %{customdata[2]}° · floor %{customdata[3]}<br>"
    "rotation %{customdata[4]}%{customdata[5]}<extra></extra>"
)


def hover_targets(nodes: Sequence[PlotNode], *, accent: str, group: str, p: Palette) -> go.Scatter:
    """Invisible markers over each node that carry the tooltip."""
    return go.Scatter(
        x=[n.x for n in nodes],
        y=[n.y for n in nodes],
        mode="markers",
        marker={"size": 18, "color": "rgba(0,0,0,0)"},
        customdata=[
            (
                n.label,
                n.kind,
                f"{n.heading:g}",
                n.floor,
                "allowed" if n.rotation_allowed else "no",
                "" if n.vrc is None else f"<br>VRC {n.vrc} stop",
            )
            for n in nodes
        ],
        hovertemplate=HOVER,
        hoverlabel={"bordercolor": accent, "bgcolor": p.card},
        showlegend=False,
        legendgroup=group,
    )


# =============================================================================================
# Layers: one pure function per kind of thing on the floor
# =============================================================================================


@dataclass(frozen=True, slots=True, kw_only=True)
class Ctx:
    p: Palette
    stall: StallSize
    adj: Mapping[int, tuple[PlotNode, ...]]
    labels: bool
    legend_here: frozenset[str]  # legend entries to show for this floor


type Traces = tuple[go.Scatter, ...]
type LayerFn = Callable[[Sequence[PlotNode], Ctx], Traces]

MAP_FRAME: Final = "Map frame"
LEGEND_ORDER: Final = (
    "Parking stall",
    "Customer bay",
    "Waypoint",
    "AGV charger",
    "EV charger",
    "Lift",
    "BLift",
    "Other node",
    "Rotation allowed",
    "Map frame",
)


def legend(
    name: str, ctx: Ctx, *, symbol: str, fill: str, line: str, size: float = 13, width: float = 1.5
) -> Traces:
    """A data-less trace that only draws the legend swatch."""
    if name not in ctx.legend_here:
        return ()
    return (
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker={"symbol": symbol, "size": size, "color": fill, "line": {"color": line, "width": width}},
            name=name,
            legendgroup=name,
            legendrank=LEGEND_ORDER.index(name),
            showlegend=True,
        ),
    )


LEGEND_NAME: Final[Mapping[str, str]] = {
    "Parking": "Parking stall",
    "Bay": "Customer bay",
    "Waypoint": "Waypoint",
    "AgvCharge": "AGV charger",
    "EvCharge": "EV charger",
    "Lift": "Lift",
    "BLift": "BLift",
}


def legend_names(scene: Scene) -> frozenset[str]:
    rotation = {"Rotation allowed"} if any(n.rotation_allowed for n in scene.nodes) else set()
    return frozenset({LEGEND_NAME.get(n.kind, "Other node") for n in scene.nodes} | rotation | {MAP_FRAME})


def corridors(scene: Scene, ctx: Ctx) -> Traces:
    """Bands under aisle edges (waypoint-waypoint and waypoint-bay)."""
    aisle = {"Waypoint", "Bay"}
    polys = tuple(
        poly
        for a, b in scene.edges
        if {a.kind, b.kind} <= aisle and not a.kind == b.kind == "Bay"
        if (poly := band(a.xy, b.xy, ctx.stall.width)) is not None
    )
    return (shapes(polys, fill=ctx.p.corridor, line=None),) if polys else ()


def edges_layer(scene: Scene, ctx: Ctx) -> Traces:
    segs = tuple((a.xy, b.xy) for a, b in scene.edges)
    return (segments(segs, color=ctx.p.edge, width=1.5),) if segs else ()


def parking_layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
    p, s, name = ctx.p, ctx.stall, "Parking stall"
    gap = 0.06  # hairline between neighbouring stalls
    stalls = tuple(rounded(box(n.xy, s.length - gap, s.width - gap, n.heading), 0.12) for n in nodes)
    fill, line = tint(p.parking, 0.10, p.floor), tint(p.parking, 0.55, p.floor)
    out: Traces = (
        *legend(name, ctx, symbol="square", fill=tint(p.parking, 0.25, p.floor), line=line),
        shapes(stalls, fill=fill, line=line, group=name),
        dots([n.xy for n in nodes], size=5, color=tint(p.parking, 0.8, p.floor), group=name),
    )
    if ctx.labels:
        corners = [top_left(box(n.xy, s.length - 0.36, s.width - 0.3, n.heading)) for n in nodes]
        out += (
            labels(
                corners,
                [n.label for n in nodes],
                position="bottom right",
                color=tint(p.parking, 0.9, p.floor),
                halo=p.floor,
                size=11,
                weight=600,
                group=name,
            ),
        )
    return (*out, hover_targets(nodes, accent=p.parking, group=name, p=p))


def door(
    bay: PlotNode, length: float, width: float, adj: Mapping[int, tuple[PlotNode, ...]]
) -> tuple[Point, Point]:
    """The short side of the bay that faces its aisle neighbour (the garage door)."""
    u, v = frame(bay.heading)
    toward = adj.get(bay.id, ())
    side = 1.0 if not toward or dot(sub(toward[0].xy, bay.xy), u) >= 0 else -1.0
    mid = add(bay.xy, u, side * length / 2)
    return add(mid, v, width / 2 - 0.3), add(mid, v, -(width / 2 - 0.3))


def bay_layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
    p, name = ctx.p, "Customer bay"
    length, width = ctx.stall.length, ctx.stall.width + 0.9
    bays = tuple(rounded(box(n.xy, length, width, n.heading), 0.3) for n in nodes)
    out: Traces = (
        *legend(name, ctx, symbol="square", fill=tint(p.bay, 0.25, p.floor), line=p.bay),
        shapes(bays, fill=tint(p.bay, 0.12, p.floor), line=p.bay, width=1.6, group=name),
        segments(tuple(door(n, length, width, ctx.adj) for n in nodes), color=p.bay, width=4.5, group=name),
        dots([n.xy for n in nodes], size=6.5, color=p.bay, group=name),
    )
    if ctx.labels:
        inner = [box(n.xy, length - 0.6, width - 0.5, n.heading) for n in nodes]
        out += (
            labels(
                [top_left(b) for b in inner],
                [n.label for n in nodes],
                position="bottom right",
                color=p.bay,
                halo=p.floor,
                size=12,
                weight=700,
                group=name,
            ),
            labels(
                [bottom_left(b) for b in inner],
                ["customer bay"] * len(nodes),
                position="top right",
                color=tint(p.bay, 0.75, p.floor),
                halo=p.floor,
                size=10.5,
                family=FONT_SANS,
                group=name,
            ),
        )
    return (*out, hover_targets(nodes, accent=p.bay, group=name, p=p))


def waypoint_layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
    p, name = ctx.p, "Waypoint"
    out: Traces = (
        *legend(name, ctx, symbol="circle", fill=p.fg2, line=p.floor, size=10),
        dots([n.xy for n in nodes], size=9, color=p.fg2, outline=p.floor, group=name),
    )
    if ctx.labels:
        out += (
            labels(
                [add(n.xy, (-0.42, 0.42)) for n in nodes],
                [n.label for n in nodes],
                position="top left",
                color=p.muted,
                halo=p.floor,
                group=name,
            ),
        )
    return (*out, hover_targets(nodes, accent=p.fg2, group=name, p=p))


def side_labels(nodes: Sequence[PlotNode], offset: float, color: str, ctx: Ctx, group: str) -> Traces:
    if not ctx.labels:
        return ()
    return (
        labels(
            [add(n.xy, (offset, 0)) for n in nodes],
            [n.label for n in nodes],
            position="middle right",
            color=color,
            halo=ctx.p.floor,
            size=11,
            weight=600,
            group=group,
        ),
    )


def charger_layer(name: str, ring: Callable[[Palette], str]) -> LayerFn:
    """Charger: tinted disc with a yellow lightning bolt (facility.Map.nodes, AgvCharge).

    Every charger's bolt is the charger yellow; the ring says what it charges (yellow for AGVs, the
    payload pink for EVs)."""

    def layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
        p, c, edge, r = ctx.p, ctx.p.charger, ring(ctx.p), 0.42
        return (
            *legend(name, ctx, symbol="circle", fill=tint(c, 0.35, p.floor), line=edge, size=14, width=2),
            shapes(
                [circle(n.xy, r) for n in nodes], fill=tint(c, 0.22, p.floor), line=edge, width=2, group=name
            ),
            shapes([bolt(n.xy, r) for n in nodes], fill=c, line=c, width=0.5, group=name),
            *side_labels(nodes, r + 0.1, edge, ctx, name),
            hover_targets(nodes, accent=edge, group=name, p=p),
        )

    return layer


def lift_layer(name: str, color: Callable[[Palette], str]) -> LayerFn:
    """Lift: rounded square with an up/down arrow (icons.lift)."""

    def layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
        p, c, s = ctx.p, color(ctx.p), 1.1
        return (
            *legend(name, ctx, symbol="square", fill=tint(c, 0.3, p.floor), line=c),
            shapes(
                [rounded(box(n.xy, s, s, 0), 0.14) for n in nodes],
                fill=tint(c, 0.16, p.floor),
                line=c,
                width=1.6,
                group=name,
            ),
            shapes([a for n in nodes for a in updown_arrow(n.xy, s * 0.8)], fill=c, line=None, group=name),
            *side_labels(nodes, s / 2 + 0.1, c, ctx, name),
            hover_targets(nodes, accent=c, group=name, p=p),
        )

    return layer


def other_layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
    p, name = ctx.p, "Other node"
    marker = {"symbol": "x-thin", "size": 10, "line": {"color": p.muted, "width": 1.6}}
    return (
        *legend(name, ctx, symbol="x-thin", fill=p.muted, line=p.muted, size=10),
        go.Scatter(
            x=[n.x for n in nodes], y=[n.y for n in nodes], mode="markers", marker=marker, **grouped(name)
        ),
        *side_labels(nodes, 0.25, p.muted, ctx, name),
        hover_targets(nodes, accent=p.muted, group=name, p=p),
    )


def rotation_layer(nodes: Sequence[PlotNode], ctx: Ctx) -> Traces:
    rings = [circle(n.xy, 0.62) for n in nodes if n.rotation_allowed]
    if not rings:
        return ()
    name = "Rotation allowed"
    return (
        *legend(name, ctx, symbol="circle-open", fill=ctx.p.muted, line=ctx.p.muted, size=14, width=1.2),
        shapes(rings, fill=None, line=ctx.p.muted, width=1, dash="dot", group=name),
    )


# Node kind -> layer. Stalls and bays sit under the edges; the rest above, in this order.
UNDER: Final[Mapping[str, LayerFn]] = {"Parking": parking_layer, "Bay": bay_layer}
OVER: Final[Mapping[str, LayerFn]] = {
    "Lift": lift_layer("Lift", lambda p: p.lift),
    "BLift": lift_layer("BLift", lambda p: p.blift),
    "AgvCharge": charger_layer("AGV charger", lambda p: p.charger),
    "EvCharge": charger_layer("EV charger", lambda p: p.payload),
    "Waypoint": waypoint_layer,
}


def floor_traces(scene: Scene, ctx: Ctx) -> Traces:
    by_kind: defaultdict[str, list[PlotNode]] = defaultdict(list)
    for n in scene.nodes:
        by_kind[n.kind if n.kind in {**UNDER, **OVER} else UNKNOWN].append(n)

    def draw(layers: Mapping[str, LayerFn]) -> Traces:
        return tuple(t for kind, fn in layers.items() if kind in by_kind for t in fn(by_kind[kind], ctx))

    return (
        *corridors(scene, ctx),
        *draw(UNDER),
        *edges_layer(scene, ctx),
        *rotation_layer(scene.nodes, ctx),
        *draw(OVER),
        *(other_layer(by_kind[UNKNOWN], ctx) if UNKNOWN in by_kind else ()),
    )


# =============================================================================================
# Figure
# =============================================================================================


def footprint(scene: Scene) -> tuple[float, float, float, float]:
    """World extent including stall and bay outlines, padded by a metre."""
    s = scene.stall
    polys = [
        box(n.xy, s.length, s.width + 0.9, n.heading) if n.kind in UNDER else circle(n.xy, 0.8, 8)
        for n in scene.nodes
    ]
    x0, x1, y0, y1 = bounds(polys)
    return x0 - 1, x1 + 1, y0 - 1, y1 + 1


def grid_steps(span: float) -> tuple[int, int]:
    """(minor, major) grid spacing in metres for a floor `span` metres across."""
    return (1, 5) if span <= 80 else (5, 25) if span <= 300 else (10, 50)


def axis(p: Palette, *, title: str, rng: tuple[float, float], steps: tuple[int, int]) -> dict[str, Any]:
    minor, major = steps
    return {
        "title": {"text": title, "font": {"family": FONT_MONO, "size": 11.5, "color": p.muted}},
        "range": list(rng),
        "tickfont": {"family": FONT_MONO, "size": 10.5, "color": p.muted},
        "dtick": major,
        "tick0": 0,
        "showgrid": True,
        "gridcolor": p.grid_major,
        "gridwidth": 1,
        "minor": {"dtick": minor, "showgrid": True, "gridcolor": p.grid_minor, "gridwidth": 0.6},
        "zeroline": False,
        "showline": True,
        "mirror": True,
        "linecolor": p.border_soft,
        "ticks": "outside",
        "ticklen": 5,
        "tickcolor": p.border,
        "constrain": "range",  # equal aspect by widening the visible range, so the plot fills the page
    }


def subtitle(scene: Scene) -> str:
    counts = Counter(n.kind for n in scene.nodes)
    parts = (
        f"{len(scene.nodes)} nodes",
        f"{len(scene.edges)} edges",
        *(
            f"{counts[k]} {k}"
            for k in ("Parking", "Bay", "AgvCharge", "EvCharge", "Lift", "BLift")
            if counts[k]
        ),
        f"stall {scene.stall.length:g} × {scene.stall.width:g} m",
    )
    return "  ·  ".join(parts)


FRAME_HOVER: Final = (
    "<b>map frame</b>  origin (0, 0)<br>"
    "x → right (red), y → up (green), metres<br>"
    "heading 0° = +y, counter-clockwise:<br>"
    "90° = −x · 180° = −y · −90° = +x<extra></extra>"
)


def arrow(tail: Point, direction: Point, length: float, width: float) -> Polygon:
    """A filled arrow (shaft + head) from `tail` along unit `direction`, in metres."""
    u = unit(direction)
    v = (-u[1], u[0])
    head_l, head_w = 0.28 * length, 2.6 * width
    neck = add(tail, u, length - head_l)
    tip = add(tail, u, length)
    hw = width / 2
    return (
        add(tail, v, hw),
        add(neck, v, hw),
        add(neck, v, head_w / 2),
        tip,
        add(neck, v, -head_w / 2),
        add(neck, v, -hw),
        add(tail, v, -hw),
    )


def frame_traces(scene: Scene, ctx: Ctx) -> Traces:
    """The map coordinate frame at (0, 0): x and y arrows sized to the layout. Drawn wherever the
    origin is; it does not move the default view to include it."""
    x0, x1, y0, y1 = footprint(scene) if scene.nodes else (0.0, 10.0, 0.0, 10.0)
    length = min(6.0, max(1.5, 0.07 * max(x1 - x0, y1 - y0)))
    width = length * 0.045
    p, name = ctx.p, MAP_FRAME
    halo = f"0 0 3px {p.floor}, 0 0 2px {p.floor}"
    tips = ((length + 0.18 * length, 0.0), (0.0, length + 0.18 * length))
    return (
        *legend(name, ctx, symbol="cross-thin", fill=p.axis_x, line=p.axis_x, size=12, width=2.5),
        shapes([arrow((0.0, 0.0), (1.0, 0.0), length, width)], fill=p.axis_x, line=None, group=name),
        shapes([arrow((0.0, 0.0), (0.0, 1.0), length, width)], fill=p.axis_y, line=None, group=name),
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers",
            marker={"symbol": "circle", "size": 8, "color": p.fg, "line": {"color": p.floor, "width": 2}},
            **grouped(name),
        ),
        go.Scatter(
            x=[t[0] for t in tips],
            y=[t[1] for t in tips],
            mode="text",
            text=["x", "y"],
            textposition="middle center",
            textfont={
                "family": FONT_MONO,
                "size": 13,
                "weight": 700,
                "color": [p.axis_x, p.axis_y],
                "shadow": halo,
            },
            **grouped(name),
        ),
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="text",
            text=["(0, 0)"],
            textposition="bottom left",
            textfont={"family": FONT_MONO, "size": 10.5, "color": p.muted, "shadow": halo},
            **grouped(name),
        ),
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers",
            marker={"size": 14, "color": "rgba(0,0,0,0)"},
            hovertemplate=FRAME_HOVER,
            hoverlabel={"bordercolor": p.fg2, "bgcolor": p.card},
            showlegend=False,
            legendgroup=name,
        ),
    )


def build_floor_figure(
    scene: Scene, floor: int, *, title: str, palette: Palette, show_labels: bool
) -> go.Figure:
    """One floor of `scene`, framed to the whole layout so every floor shares one scale and origin."""
    floor_scene = on_floor(scene, floor)
    x0, x1, y0, y1 = footprint(scene)
    steps = grid_steps(max(x1 - x0, y1 - y0))
    ctx = Ctx(
        p=palette,
        stall=scene.stall,
        adj=neighbours(scene),
        labels=show_labels,
        legend_here=legend_names(floor_scene),
    )
    # The frame is drawn last so stalls or bays at the origin do not cover it.
    fig = go.Figure([*floor_traces(floor_scene, ctx), *frame_traces(scene, ctx)])
    fig.update_xaxes(axis(palette, title="x [m]", rng=(x0, x1), steps=steps), uirevision="floorplan")
    fig.update_yaxes(
        axis(palette, title="y [m]", rng=(y0, y1), steps=steps),
        scaleanchor="x",
        scaleratio=1,
        uirevision="floorplan",  # zoom survives floor and theme switches
    )
    multi = len(floors_of(scene)) > 1

    fig.update_layout(
        title={
            "text": (
                f"{title}<br><span style='font-size:12.5px;color:{palette.muted}'>{subtitle(scene)}</span>"
            ),
            "font": {"family": FONT_SANS, "size": 21, "color": palette.fg, "weight": 600},
            "x": 0.012,
            "xanchor": "left",
            "y": 0.975,
        },
        font={"family": FONT_SANS, "color": palette.fg2},
        paper_bgcolor=palette.bg,
        plot_bgcolor=palette.floor,
        margin={"l": 64, "r": 24, "t": 122 if multi else 84, "b": 92},  # room for the floor tabs
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"family": FONT_SANS, "size": 12.5, "color": palette.fg2},
            "itemsizing": "constant",
            "groupclick": "togglegroup",
            "orientation": "h",
            "x": 0.5,
            "xanchor": "center",
            "yref": "container",
            "y": 0.012,
            "yanchor": "bottom",
        },
        hoverlabel={"font": {"family": FONT_MONO, "size": 12, "color": palette.fg}},
        hovermode="closest",
        hoverdistance=14,
        dragmode="pan",
        modebar={"bgcolor": "rgba(0,0,0,0)", "color": palette.faint, "activecolor": palette.fg},
    )
    return fig


# =============================================================================================
# HTML
# =============================================================================================


@dataclass(frozen=True, slots=True)
class FloorTab:
    floor: int
    label: str
    detail: str


def floor_tabs(scene: Scene) -> tuple[FloorTab, ...]:
    counts = Counter(n.floor for n in scene.nodes)
    parking = Counter(n.floor for n in scene.nodes if n.kind == "Parking")

    def detail(f: int) -> str:
        z = scene.floor_z.get(f)
        height = f"z {z:g} m · " if z is not None and len(scene.floor_z) > 1 else ""
        return f"{height}{counts[f]} nodes · {parking[f]} stalls"

    return tuple(FloorTab(f, f"Floor {f}", detail(f)) for f in floors_of(scene))


def theme_css(name: str, p: Palette) -> str:
    """CSS custom properties for the page chrome (background, floor tabs) in one theme."""
    return (
        f"--bg:{p.bg};--tab-bg:{p.card};--tab-border:{p.border_soft};--tab-fg:{p.muted};"
        f"--tab-hover:{p.fg2};--tab-on-bg:{tint(p.parking, 0.18, p.card)};--tab-on-fg:{p.fg};"
        f"--tab-on-border:{p.parking};--tab-detail:{p.faint};color-scheme:{name};"
        f"--fg:{p.fg};--fg2:{p.fg2};--muted:{p.muted};--faint:{p.faint};--card:{p.card};"
        f"--floor:{p.floor};--border:{p.border};--border-soft:{p.border_soft};"
        f"--parking:{p.parking};--bay:{p.bay};--charger:{p.charger};--agv:{p.agv};--tray:{p.tray};"
        f"--payload:{p.payload};--danger:{p.danger};"
        f"--agv-bg:{tint(p.agv, 0.16, p.card)};--tray-bg:{tint(p.tray, 0.16, p.card)};"
        f"--payload-bg:{tint(p.payload, 0.16, p.card)};--danger-bg:{tint(p.danger, 0.16, p.card)};"
        f"--parking-bg:{tint(p.parking, 0.16, p.card)};--charger-bg:{tint(p.charger, 0.16, p.card)};"
    )


def page_html(
    figures: Mapping[ThemeName, Mapping[int, go.Figure]],
    tabs: Sequence[FloorTab],
    *,
    title: str,
    theme: ThemeName,
    plotlyjs: Literal[True, "cdn"],
    kind: str = "layout",
    sidebar: str = "",
    extra_css: str = "",
    extra_js: str = "",
    extra: Mapping[str, Any] | None = None,
) -> str:
    """One self-contained page holding every floor in both themes.

    `sidebar` (HTML), `extra_css`, `extra_js` and `extra` (as PAGE.extra) let another page - the
    scenario viewer - build on the floor plan. Its script can use `window.layoutPage` and listen for
    the `layout:shown` event, fired after every redraw (floor or theme switch).

    Floor tabs and a modebar button switch what is drawn. The plot fills a fixed,
    overflow-hidden viewport, so redraws (home, zoom, resize) never toggle page scrollbars -
    which would resize the plot and redraw it again.
    """
    figs = {
        t.value: {str(f): json.loads(fig.to_json()) for f, fig in per_floor.items()}
        for t, per_floor in figures.items()
    }
    script = (
        f'<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js" charset="utf-8"></script>'
        if plotlyjs == "cdn"
        else f'<script type="text/javascript">{get_plotlyjs()}</script>'
    )
    data = {
        "labelPxPerM": LABEL_MIN_PX_PER_M,
        "figs": figs,
        "floors": [{"floor": t.floor, "label": t.label, "detail": t.detail} for t in tabs],
        "theme": theme.value,
        "filename": title,
        "extra": dict(extra or {}),
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return PAGE_TEMPLATE.format(
        title=html.escape(title),
        kind=html.escape(kind),
        body_class="with-sidebar" if sidebar else "",
        sidebar=sidebar,
        extra_css=extra_css,
        extra_js=extra_js,
        fonts=GOOGLE_FONTS_URL,
        dark=theme_css("dark", DARK),
        light=theme_css("light", LIGHT),
        plotly=script,
        payload=payload,
        app=PAGE_SCRIPT,
    )


# Labels appear once a metre is this many pixels wide: a 2.21 m stall is then ~20 px tall, enough
# for its 11 px label, and waypoint labels on a 2.4 m pitch stop overlapping.
LABEL_MIN_PX_PER_M: Final = 9.0

PAGE_TEMPLATE: Final = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {kind}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{fonts}">
<style>
  :root {{ {dark} }}
  html[data-theme="light"] {{ {light} }}
  html, body {{ margin: 0; height: 100%; overflow: hidden; background: var(--bg); }}
  #plot {{ position: fixed; inset: 0; }}
  body.with-sidebar {{ --sidebar-w: min(420px, 38vw); }}
  body.with-sidebar #plot {{ right: var(--sidebar-w); }}
  body.with-sidebar #floors {{ max-width: calc(100vw - var(--sidebar-w) - 32px); }}
  body.with-sidebar #hint {{ right: calc(var(--sidebar-w) + 20px); }}
  #floors {{
    position: fixed; top: 70px; left: 16px; z-index: 10;
    display: flex; gap: 4px; padding: 3px; max-width: calc(100vw - 32px); overflow-x: auto;
    background: var(--tab-bg); border: 1px solid var(--tab-border); border-radius: 10px;
    font-family: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
    scrollbar-width: none;
  }}
  #floors[hidden] {{ display: none; }}
  #floors button {{
    all: unset; cursor: pointer; white-space: nowrap;
    display: flex; align-items: baseline; gap: 8px;
    padding: 5px 12px; border-radius: 7px; border: 1px solid transparent;
    color: var(--tab-fg); font-size: 13px; font-weight: 500;
  }}
  #floors button:hover {{ color: var(--tab-hover); }}
  #floors button:focus-visible {{ outline: 2px solid var(--tab-on-border); outline-offset: 1px; }}
  #floors button[aria-selected="true"] {{
    background: var(--tab-on-bg); border-color: var(--tab-on-border); color: var(--tab-on-fg); font-weight: 600;
  }}
  #hint {{
    position: fixed; right: 20px; top: 40px; z-index: 10; pointer-events: none;
    font: 12px 'IBM Plex Sans', system-ui, sans-serif; color: var(--tab-detail);
  }}
  #hint kbd {{
    font: 11px 'JetBrains Mono', ui-monospace, monospace; padding: 1px 5px;
    border: 1px solid var(--tab-border); border-radius: 4px; background: var(--tab-bg);
  }}
  #hint[hidden] {{ display: none; }}
  #floors small {{
    color: var(--tab-detail); font-size: 11px; font-weight: 400;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
  }}
{extra_css}
</style>
{plotly}
</head>
<body class="{body_class}">
<nav id="floors" role="tablist" aria-label="Floor" hidden></nav>
<div id="plot"></div>
<div id="hint" hidden></div>
{sidebar}
<script>const PAGE = {payload};</script>
<script>{app}</script>
<script>{extra_js}</script>
</body>
</html>
"""

# Contrast icon (half-filled circle), 24x24, drawn without holes so it fills correctly.
PAGE_SCRIPT: Final = """
(() => {
  const KEY = "layout-plotter-theme";
  const gd = document.getElementById("plot");
  const nav = document.getElementById("floors");
  const floors = PAGE.floors.map((f) => String(f.floor));
  const stored = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
  const store = (t) => { try { localStorage.setItem(KEY, t); } catch { /* private mode */ } };
  const osTheme = () => matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  const valid = (t) => t === "dark" || t === "light";
  const hashFloor = () => {
    const m = location.hash.match(/floor=([^&]+)/);
    return m && floors.includes(decodeURIComponent(m[1])) ? decodeURIComponent(m[1]) : null;
  };

  const state = {
    theme: PAGE.theme !== "auto" ? PAGE.theme : (valid(stored()) ? stored() : osTheme()),
    floor: hashFloor() ?? floors[0],
  };
  let revision = 0;

  const config = {
    responsive: true,
    scrollZoom: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "sendChartToCloud"],
    showSendToCloud: false,
    showTips: false,
    toImageButtonOptions: { format: "png", filename: PAGE.filename, scale: 2 },
    modeBarButtonsToAdd: [{
      name: "theme",
      title: "Toggle light / dark",
      // contrast icon (half-filled circle), drawn without holes so it fills correctly
      icon: { width: 24, height: 24, path: "M12 2A10 10 0 0 0 12 22Z M12 2A10 10 0 0 1 12 22L12 20A8 8 0 0 0 12 4Z" },
      click: () => { store(state.theme === "dark" ? "light" : "dark"); show({ theme: state.theme === "dark" ? "light" : "dark" }); },
    }],
  };

  // Layers hidden from the legend, by legend group, so they stay hidden across switches.
  const hiddenGroups = () => new Set(
    (gd._fullData || []).filter((t) => t.visible === "legendonly" && t.legendgroup).map((t) => t.legendgroup),
  );

  // ---- labels: automatic by zoom level; L cycles auto -> always -> never --------------------------
  const hint = document.getElementById("hint");
  const LABEL_MODES = ["auto", "always", "never"];
  let labelMode = "auto";
  let labelsOn = false;
  const labelTraces = () => gd.data.flatMap((t, i) => (t.meta === "label" ? [i] : []));
  const pxPerMetre = () => {
    const xa = gd._fullLayout && gd._fullLayout.xaxis;
    return xa ? xa._length / Math.abs(xa.range[1] - xa.range[0]) : 0;
  };

  function updateLabels(force = false) {
    const traces = labelTraces();
    const want = labelMode === "always" || (labelMode === "auto" && pxPerMetre() >= PAGE.labelPxPerM);
    hint.hidden = !traces.length || (labelMode === "auto" && want);
    hint.innerHTML =
      labelMode === "auto" ? "Zoom in to see labels · <kbd>L</kbd> to always show"
      : labelMode === "always" ? "Labels always shown · <kbd>L</kbd> to hide"
      : "Labels hidden · <kbd>L</kbd> for automatic";
    if (!traces.length || (want === labelsOn && !force)) return;
    labelsOn = want;
    Plotly.restyle(gd, { mode: want ? "text" : "none" }, traces);
  }

  document.addEventListener("keydown", (e) => {
    if (e.key.toLowerCase() !== "l" || e.metaKey || e.ctrlKey || e.altKey || e.target.closest("input, textarea")) return;
    labelMode = LABEL_MODES[(LABEL_MODES.indexOf(labelMode) + 1) % LABEL_MODES.length];
    updateLabels();
  });

  function show(change) {
    Object.assign(state, change);
    document.documentElement.dataset.theme = state.theme;
    for (const b of nav.children) b.setAttribute("aria-selected", String(b.dataset.floor === state.floor));
    if (floors.length > 1) history.replaceState(null, "", `#floor=${encodeURIComponent(state.floor)}`);
    PAGE.filename && (config.toImageButtonOptions.filename = `${PAGE.filename}_floor_${state.floor}`);

    const hidden = hiddenGroups();
    const fig = PAGE.figs[state.theme][state.floor];
    const data = fig.data.map((t) => ({
      ...t,
      ...(hidden.has(t.legendgroup) ? { visible: "legendonly" } : {}),
      ...(t.meta === "label" ? { mode: labelsOn ? "text" : "none" } : {}),
    }));
    // A new layout revision resets trace state (we restore it above); the axes keep their own
    // uirevision, so zoom and pan carry over between floors and themes.
    return Plotly.react(gd, data, { ...fig.layout, uirevision: ++revision }, config).then(() => {
      updateLabels();
      document.dispatchEvent(new CustomEvent("layout:shown", { detail: { ...state } }));
    });
  }

  // For pages built on top of this one (scenario viewer).
  window.layoutPage = { gd, state, show: (change) => show(change), floors };

  if (floors.length > 1) {
    for (const f of PAGE.floors) {
      const b = document.createElement("button");
      b.type = "button";
      b.role = "tab";
      b.dataset.floor = String(f.floor);
      b.innerHTML = `<span></span><small></small>`;
      b.firstChild.textContent = f.label;
      b.lastChild.textContent = f.detail;
      b.addEventListener("click", () => show({ floor: String(f.floor) }));
      nav.append(b);
    }
    nav.hidden = false;
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("input, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
      const i = floors.indexOf(state.floor);
      const next =
        /^[1-9]$/.test(e.key) ? floors[Number(e.key) - 1]
        : e.key === "[" || e.key === "PageUp" ? floors[Math.max(0, i - 1)]
        : e.key === "]" || e.key === "PageDown" ? floors[Math.min(floors.length - 1, i + 1)]
        : undefined;
      if (next !== undefined && next !== state.floor) { e.preventDefault(); show({ floor: next }); }
    });
    addEventListener("hashchange", () => { const f = hashFloor(); if (f && f !== state.floor) show({ floor: f }); });
  }

  show({}).then(() => {
    gd.on("plotly_relayout", () => updateLabels());  // zoom, pan, home, resize
  });
})();
"""


# =============================================================================================
# Finding layouts
# =============================================================================================

LAYOUTS_SUBDIR: Final = Path("share") / "site_config" / "layouts"
SOURCE_LAYOUTS: Final = Path("src") / "config" / "site_config" / "layouts"
WORKSPACES: Final = (Path.home() / "volley", Path.home() / "repos" / "volley")
LAYOUTS_ENV: Final = "VOLLEY_LAYOUTS"


def layout_dirs(extra: Sequence[Path] = ()) -> tuple[Path, ...]:
    """Folders that hold layout YAML files, in search order.

    1. --layouts-dir arguments, then $VOLLEY_LAYOUTS (os.pathsep-separated)
    2. installed copies, <prefix>/share/site_config/layouts, for each AMENT_PREFIX_PATH prefix
       (inside the ROS container, after `source install/setup.zsh`)
    3. src/config/site_config/layouts under the current directory and under ~/volley and
       ~/repos/volley (the workspace checkout, on the host or in the container)
    """
    env = (Path(p) for p in os.environ.get(LAYOUTS_ENV, "").split(os.pathsep) if p)
    prefixes = (Path(p) for p in os.environ.get("AMENT_PREFIX_PATH", "").split(os.pathsep) if p)
    candidates = (
        *extra,
        *env,
        *(p / LAYOUTS_SUBDIR for p in prefixes),
        *(root / SOURCE_LAYOUTS for root in (Path.cwd(), *WORKSPACES)),
    )
    found = (c.expanduser() for c in candidates)
    return tuple(dict.fromkeys(c.resolve() for c in found if c.is_dir()))


@dataclass(frozen=True, slots=True)
class LayoutFile:
    name: str
    path: Path
    folder: Path


def find_layouts(dirs: Iterable[Path], pattern: str = "") -> tuple[LayoutFile, ...]:
    """Every *.yaml under `dirs`, one entry per real file (symlink-install duplicates removed)."""
    found = (
        LayoutFile(
            name=path.stem,
            path=path,
            folder=folder,
        )
        for folder in dirs
        for path in sorted(folder.rglob("*.y*ml"))
        if path.is_file() and pattern.lower() in path.stem.lower()
    )
    unique = {f.path.resolve(): f for f in reversed(tuple(found))}  # keep the first folder's copy
    return tuple(sorted(unique.values(), key=lambda f: f.name))


def pretty(path: Path) -> str:
    for base, label in ((Path.cwd(), "."), (Path.home(), "~")):
        if path.is_relative_to(base):
            return str(Path(label) / path.relative_to(base))
    return str(path)


def resolve_layout(name: str, dirs: Sequence[Path]) -> Path:
    """A YAML path as given, or the layout called `name` in the first folder that has it."""
    if (path := Path(name).expanduser()).is_file():
        return path
    stem = Path(name).stem
    files = find_layouts(dirs)
    for f in files:
        if f.name == stem:
            return f.path
    for f in files:  # the layout's own `name:` can differ from its file name
        if yaml_name(f.path) == stem:
            return f.path
    searched = "\n  ".join(map(pretty, dirs)) or "(no layout folders found)"
    raise FileNotFoundError(
        f"no layout named {stem!r}; searched:\n  {searched}\n"
        f"use --list to see what is available, or --layouts-dir / ${LAYOUTS_ENV} to add a folder"
    )


# ---------------------------------------------------------------------------------------------
# --list: what is in each layout, and which layouts describe the same site
# ---------------------------------------------------------------------------------------------

NAME_RE: Final = re.compile(r"^name:\s*['\"]?([^'\"#\n]+?)['\"]?\s*(?:#.*)?$", re.MULTILINE)
SECTION_RE: Final = re.compile(r"^\s*#+\s*([A-Za-z0-9][\w.-]*)\s*$", re.MULTILINE)
CHARGERS: Final = frozenset({"AgvCharge", "EvCharge"})
CONTAINED: Final = 0.9  # share of A's nodes found in B for "A is part of B"
OVERLAP_MIN_NODES: Final = 5  # shared positions needed to call two layouts one site...
OVERLAP_MIN_SHARE: Final = 0.5  # ...and at least this share of the smaller layout

type NodeKey = tuple[int, float, float, str]  # floor, x, y, type - ids get renumbered between files


@dataclass(frozen=True, slots=True)
class LayoutSummary:
    file: LayoutFile
    floors: int = 0
    nodes: int = 0
    kinds: Counter[str] = dataclass_field(default_factory=Counter)
    size: tuple[float, float] = (0.0, 0.0)  # extent of the node positions, metres
    keys: frozenset[NodeKey] = frozenset()
    sections: frozenset[str] = frozenset()  # `# <name>` comment lines
    vrcs: int = 0
    yaml_name: str | None = None  # the layout's own `name:`
    top_keys: tuple[str, ...] = ()
    error: str | None = None

    @property
    def is_layout(self) -> bool:
        return self.error is not None or "nodes" in self.top_keys

    @property
    def name(self) -> str:
        return self.file.name


def yaml_load(text: str) -> Any:
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)  # libyaml when available: ~10x faster
    return yaml.load(text, Loader=loader)  # noqa: S506 - a safe loader either way


def yaml_name(path: Path) -> str | None:
    """The top-level `name:` of a YAML file, without parsing the whole file."""
    try:
        m = NAME_RE.search(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    return m.group(1).strip() if m else None


def summarize(file: LayoutFile) -> LayoutSummary:
    try:
        text = file.path.read_text(encoding="utf-8")
        doc = yaml_load(text)
        if not isinstance(doc, Mapping):
            return LayoutSummary(file, error="not a YAML mapping")
        scene = build_scene(doc, None)
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as exc:
        return LayoutSummary(file, error=type(exc).__name__)
    xs, ys = [n.x for n in scene.nodes] or [0.0], [n.y for n in scene.nodes] or [0.0]
    return LayoutSummary(
        file,
        floors=len(floors_of(scene)),
        nodes=len(scene.nodes),
        kinds=Counter(n.kind for n in scene.nodes),
        size=(max(xs) - min(xs), max(ys) - min(ys)),
        keys=frozenset((n.floor, round(n.x, 2), round(n.y, 2), n.kind) for n in scene.nodes),
        sections=frozenset(SECTION_RE.findall(text)),
        vrcs=len(scene.vrcs),
        yaml_name=str(doc["name"]) if "name" in doc else None,
        top_keys=tuple(str(k) for k in doc),
    )


def linked(a: LayoutSummary, b: LayoutSummary) -> bool:
    """Same site: a section comment naming the other, or shared node positions."""
    if a.name in b.sections or b.name in a.sections:
        return True
    shared = len(a.keys & b.keys)
    return shared >= max(OVERLAP_MIN_NODES, OVERLAP_MIN_SHARE * min(len(a.keys), len(b.keys)))


def part_of(a: LayoutSummary, b: LayoutSummary) -> bool:
    """`a` is a piece of `b`: b is bigger and holds (nearly) all of a's nodes, or names it as a section."""
    if a.name in b.sections:
        return True
    return bool(a.keys) and len(b.keys) > len(a.keys) and len(a.keys & b.keys) >= CONTAINED * len(a.keys)


def site_groups(items: Sequence[LayoutSummary]) -> tuple[tuple[LayoutSummary, ...], ...]:
    """Connected components of `linked`, largest site first, then by name."""
    parent = list(range(len(items)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in itertools.combinations(range(len(items)), 2):
        if linked(items[i], items[j]):
            parent[root(i)] = root(j)
    groups: defaultdict[int, list[LayoutSummary]] = defaultdict(list)
    for i, item in enumerate(items):
        groups[root(i)].append(item)
    ordered = (tuple(sorted(g, key=lambda s: s.name)) for g in groups.values())
    return tuple(sorted(ordered, key=lambda g: (len(g) == 1, g[0].name)))


def common_prefix(names: Sequence[str]) -> str:
    prefix = os.path.commonprefix(list(names))
    return prefix.rstrip("_-.") if len(prefix) >= 3 else ""


def group_titles(groups: Sequence[Sequence[LayoutSummary]]) -> tuple[str, ...]:
    """Common name prefix per group; the biggest layout's name where two groups would share one."""
    prefixes = [common_prefix([s.name for s in g]) for g in groups]
    clash = Counter(prefixes)
    return tuple(
        p if p and clash[p] == 1 else max(g, key=lambda s: s.nodes).name
        for p, g in zip(prefixes, groups, strict=True)
    )


def relation(s: LayoutSummary, group: Sequence[LayoutSummary], prefix: str) -> str:
    def short(name: str) -> str:
        return name.removeprefix(prefix).lstrip("_-.") or name

    pieces = [o for o in group if o is not s and part_of(o, s)]
    parts = [o for o in pieces if not any(part_of(o, q) for q in pieces if q is not o)]
    wholes = [o for o in group if o is not s and part_of(s, o)]
    same = [o for o in group if o is not s and o.keys and o.keys == s.keys]
    notes = (
        *(["combines " + ", ".join(short(o.name) for o in parts)] if parts else []),
        *(["same nodes as " + ", ".join(short(o.name) for o in same)] if same else []),
        *(["part of " + short(min(wholes, key=lambda o: len(o.keys)).name)] if wholes and not same else []),
    )
    if notes:
        return " · ".join(notes)
    # In the group only through partial overlap: say with what, and how much.
    others = [o for o in group if o is not s and o.keys]
    best = max(others, key=lambda o: len(o.keys & s.keys), default=None)
    shared = len(best.keys & s.keys) if best else 0
    if best is None or not shared:
        return (
            "linked by section comment"
            if any(s.name in o.sections or o.name in s.sections for o in others)
            else ""
        )
    return f"shares {shared} of {len(s.keys)} node positions with {short(best.name)}"


def name_hint(s: LayoutSummary, titles: Sequence[str]) -> str:
    """Flag a lone layout whose name starts like a site group's (a hint only, not used to group)."""
    match = next((t for t in titles if t and s.name.startswith(t)), None)
    return f"[yellow]name matches {match}, but no shared nodes[/]" if match else ""


def count(n: int) -> str:
    return str(n) if n else "[dim]·[/]"


# ---------------------------------------------------------------------------------------------
# Activity: is a layout / scenario still in use? (git history + who references it)
# ---------------------------------------------------------------------------------------------

ACTIVE_DAYS: Final = 182  # "recent" = the last six months
BULK_FILES: Final = 30  # commits touching more YAML files than this are sweeps (lint, moves), not edits
REF_EXCLUDE: Final = ("repomix-*", "*.xml", "*.lock", "*.svg")  # snapshots that mention every name

SCENARIOS_SUBDIR: Final = Path("share") / "scenario" / "scenarios"
SOURCE_SCENARIOS: Final = Path("src") / "scenario" / "scenarios"
SCENARIOS_ENV: Final = "VOLLEY_SCENARIOS"


def scenario_dirs(extra: Sequence[Path] = ()) -> tuple[Path, ...]:
    """--scenarios-dir, $VOLLEY_SCENARIOS, installed share/scenario/scenarios, then the workspace."""
    env = (Path(p) for p in os.environ.get(SCENARIOS_ENV, "").split(os.pathsep) if p)
    prefixes = (Path(p) for p in os.environ.get("AMENT_PREFIX_PATH", "").split(os.pathsep) if p)
    candidates = (
        *extra,
        *env,
        *(p / SCENARIOS_SUBDIR for p in prefixes),
        *(root / SOURCE_SCENARIOS for root in (Path.cwd(), *WORKSPACES)),
    )
    found = (c.expanduser() for c in candidates)
    return tuple(dict.fromkeys(c.resolve() for c in found if c.is_dir()))


@dataclass(frozen=True, slots=True)
class Change:
    date: str  # YYYY-MM-DD
    author: str
    subject: str


@dataclass(frozen=True, slots=True)
class History:
    last: Change | None  # last real edit (bulk commits and pure renames skipped)
    recent: int  # real edits in the last ACTIVE_DAYS
    added: str | None = None  # date of the commit that added it (even a bulk one)


def git(root: Path, *args: str, timeout: float = 30) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=timeout, check=True
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def git_root(path: Path) -> Path | None:
    out = git(path if path.is_dir() else path.parent, "rev-parse", "--show-toplevel", timeout=5)
    return Path(out.strip()).resolve() if out else None


def git_histories(root: Path, files: Iterable[Path]) -> Mapping[Path, History]:
    """Real edit history of each file (absolute, resolved paths), following renames.

    One `git log` over every YAML file in the repo, walked newest to oldest: a rename moves the
    tracking to the old path, so a file keeps its history across moves (launcher -> site_config).
    """
    tracked: dict[str, Path] = {}
    for f in files:
        real = f.resolve()
        if real.is_relative_to(root):
            tracked[str(real.relative_to(root))] = real
    if not tracked:
        return {}
    out = git(
        root,
        "log",
        "-M",
        "--no-merges",
        "--name-status",
        "--format=%x1e%cs%x1f%an%x1f%s",
        "--",
        "*.yaml",
        "*.yml",
    )
    if out is None:
        return {}
    cutoff = (datetime.now() - timedelta(days=ACTIVE_DAYS)).date().isoformat()
    last: dict[Path, Change] = {}
    added: dict[Path, str] = {}
    recent: Counter[Path] = Counter()
    for record in out.split("\x1e")[1:]:
        head, *lines = record.strip("\n").split("\n")
        date, author, subject = [*head.split("\x1f"), "", "", ""][:3]
        entries = [ln.split("\t") for ln in lines if ln.strip()]
        bulk = len(entries) > BULK_FILES
        for status, *paths in entries:
            if status.startswith(("R", "C")) and len(paths) == 2:
                old, new = paths
                key = tracked.get(new)
                if key is None:
                    continue
                tracked[old] = key  # older commits know this file by its old path
                edited = status[1:] != "100"  # R100 = moved, not changed
            elif paths and paths[0] in tracked and status[:1] in ("M", "A"):
                key, edited = tracked[paths[0]], True
                if status[:1] == "A":
                    added[key] = date  # walking back in time: the oldest add wins
            else:
                continue
            if edited and not bulk:
                last.setdefault(key, Change(date, author, subject))
                recent[key] += date >= cutoff
    return {p: History(last.get(p), recent[p], added.get(p)) for p in set(tracked.values())}


def ref_kind(path: str) -> str:
    """What kind of file mentions a name: ci, test, batch, launch, config, docs or code."""
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    if (
        p.startswith((".github/", ".gitlab", ".circleci/", "ci/"))
        or "/ci/" in p
        or name.startswith("ci")
        or "-ci" in name
    ):
        return "ci"
    if "batch_config" in p:
        return "batch"
    if "/test" in p or name.startswith("test") or "tests/" in p or "system_test" in p:
        return "test"
    if "launch" in p:
        return "launch"
    if name.endswith((".md", ".rst", ".txt", ".html")) or p.startswith("docs/"):
        return "docs"
    if name.endswith((".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".env")):
        return "config"
    return "code"


def git_refs(root: Path, names: Iterable[str], skip: Iterable[Path]) -> Mapping[str, tuple[str, ...]]:
    """Repo files (outside `skip` folders) that mention each name as a whole word."""
    wanted = sorted({n for n in names if n})
    if not wanted:
        return {}
    excludes = [
        f":(exclude){d.resolve().relative_to(root)}" for d in skip if d.resolve().is_relative_to(root)
    ]
    excludes += [f":(exclude,glob)**/{g}" for g in REF_EXCLUDE]
    pattern_file = "\n".join(wanted)
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "grep", "-I", "-z", "-o", "-w", "-F", "-f", "-", "--", ".", *excludes],
            input=pattern_file,
            check=False,  # exit 1 means no matches
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout  # exit 1 = no matches, which is fine
    except (OSError, subprocess.SubprocessError):
        return {}
    found: defaultdict[str, set[str]] = defaultdict(set)
    for line in out.splitlines():
        path, _, match = line.partition("\0")
        if match:
            found[match].add(path)
    return {n: tuple(sorted(found[n])) for n in wanted if n in found}


STRONG_REFS: Final = frozenset({"ci", "test", "batch", "launch", "config"})


@dataclass(frozen=True, slots=True)
class Activity:
    history: History | None  # None outside a git repo
    refs: tuple[str, ...]  # files that mention it
    users: int = 0  # layouts: scenarios that use it
    active_users: int = 0  # layouts: ...of which are active themselves

    @property
    def kinds(self) -> tuple[str, ...]:
        order = ("ci", "test", "batch", "launch", "config", "code", "docs")
        found = {ref_kind(r) for r in self.refs}
        return tuple(k for k in order if k in found)

    @property
    def status(self) -> str:
        """active: edited in the last six months, or wired into ci/tests/batch/launch/config;
        quiet: referenced, but untouched; unused: nothing outside its folder points at it."""
        recent = bool(self.history and self.history.recent)
        if recent or STRONG_REFS & set(self.kinds) or self.active_users:
            return "active"
        if self.refs or self.users:
            return "quiet"
        return "unused"


STATUS_MARK: Final = {"active": "[green]●[/]", "quiet": "[yellow]○[/]", "unused": "[red]✕[/]"}
STATUS_LEGEND: Final = (
    "[green]●[/] active = edited in the last 6 months, or used by ci/test/batch/launch/config"
    " (layouts: or by an active scenario)\n[yellow]○[/] quiet = referenced, but untouched   "
    "[red]✕[/] unused = nothing outside its folder references it"
)


CHANGED_LEGEND: Final = (
    f"changed = last real edit (renames followed; commits touching >{BULK_FILES} YAML files skipped); "
    "[italic]italic[/] = date added, no real edit since"
)


def activity_cells(a: Activity | None, *, users_label: str = "") -> tuple[str, str]:
    """(changed, referenced in) table cells. A date in italics is when the file was added: it has had
    no real edit since (only sweeps and moves)."""
    if a is None:
        return ("", "")
    h = a.history
    changed = (
        h.last.date
        if h and h.last
        else f"[italic]{h.added}[/]"
        if h and h.added
        else "[dim]?[/]"
        if h
        else ""
    )
    noun = users_label if a.users != 1 else users_label.removesuffix("s")
    active = f" ({a.active_users} active)" if a.active_users and a.active_users != a.users else ""
    lines = [f"{a.users} {noun}{active}"] if a.users and users_label else []
    lines += [escape(short_path(r)) for r in a.refs[:MAX_REFS]]
    lines += [f"[dim]+{len(a.refs) - MAX_REFS} more[/]"] if len(a.refs) > MAX_REFS else []
    return (changed, "\n".join(lines) or "[dim]—[/]")


MAX_REFS: Final = 3  # files listed per row in "referenced in"; the rest are counted


def short_path(path: str, width: int = 32) -> str:
    """Repo path shortened from the middle: src/system_tests/test/test_x.py -> src/…/test/test_x.py."""
    if len(path) <= width:
        return path
    parts = path.split("/")
    for keep in range(len(parts) - 1, 0, -1):
        candidate = "/".join([parts[0], "…", *parts[-keep:]])
        if len(candidate) <= width:
            return candidate
    return parts[-1]  # just the file name; the cell cuts it if it is still too long


def scenario_layouts(dirs: Iterable[Path]) -> Mapping[Path, str]:
    """Scenario file -> the layout it names (`layout:` line), without parsing the files."""
    pattern = re.compile(r"^layout:\s*['\"]?([^'\"#\s]+)", re.MULTILINE)
    out: dict[Path, str] = {}
    for f in find_layouts(dirs):
        try:
            if m := pattern.search(f.path.read_text(encoding="utf-8")):
                out[f.path] = m.group(1)
        except OSError:
            continue
    return out


def layout_activity(
    summaries: Sequence[LayoutSummary], dirs: Sequence[Path], scenario_folders: Sequence[Path]
) -> Mapping[str, Activity]:
    root = next((r for d in dirs if (r := git_root(d))), None)
    scenarios = scenario_layouts(scenario_folders)
    names = {s.name for s in summaries} | {s.yaml_name for s in summaries if s.yaml_name}
    history = git_histories(root, [*(s.file.path for s in summaries), *scenarios]) if root else {}
    refs = git_refs(root, names | {p.stem for p in scenarios}, [*dirs, *scenario_folders]) if root else {}

    def scenario_active(path: Path) -> bool:
        return Activity(history=history.get(path.resolve()), refs=refs.get(path.stem, ())).status == "active"

    def of(s: LayoutSummary) -> Activity:
        aliases = {s.name, s.yaml_name} - {None}
        users = [p for p, layout in scenarios.items() if layout in aliases]
        return Activity(
            history=history.get(s.file.path.resolve()) if root else None,
            refs=tuple(sorted({r for a in aliases for r in refs.get(str(a), ())})),
            users=len(users),
            active_users=sum(map(scenario_active, users)) if root else 0,
        )

    return {s.name: of(s) for s in summaries}


def print_layouts(console: Console, pattern: str, extra: Sequence[Path]) -> int:
    dirs = layout_dirs(extra)
    if not dirs:
        console.print(
            "[yellow]no layout folders found[/] - pass --layouts-dir, set "
            f"${LAYOUTS_ENV}, or run from the workspace root"
        )
        return 1
    files = find_layouts(dirs)
    with console.status(f"reading {len(files)} layouts…"):
        everything = tuple(map(summarize, files))
        summaries = tuple(s for s in everything if s.is_layout)
        others = tuple(s for s in everything if not s.is_layout)
        activity = layout_activity(summaries, dirs, scenario_dirs())
    groups = [g for g in site_groups(summaries) if any(pattern.lower() in s.name.lower() for s in g)]
    if not groups:
        console.print(f"[yellow]no layouts matching {pattern!r}[/]")
        return 1

    table = Table(header_style="bold", box=None, padding=(0, 1), pad_edge=False)
    table.add_column("layout", no_wrap=True, min_width=max((len(s.name) for s in summaries), default=20) + 2)
    for col in ("floors", "nodes", "stalls", "bays", "chargers", "vrcs"):
        table.add_column(col, justify="right", no_wrap=True, min_width=len(col))
    table.add_column("size m", justify="right", style="dim", no_wrap=True, min_width=8)
    with_git = any(a.history is not None for a in activity.values())
    if with_git:
        table.add_column("changed", style="dim", no_wrap=True, min_width=10)
    table.add_column(
        "referenced in", style="dim", no_wrap=True, overflow="ellipsis", min_width=14, max_width=34
    )
    table.add_column("", style="dim italic", no_wrap=True, overflow="ellipsis", max_width=48)

    shown = 0
    singles = [g[0] for g in groups if len(g) == 1]
    multi = [g for g in site_groups(summaries) if len(g) > 1]
    title_of = {g[0].name: t for g, t in zip(multi, group_titles(multi), strict=True)}
    titles = list(title_of.values())
    for group in (g for g in groups if len(g) > 1):
        prefix = common_prefix([s.name for s in group])
        table.add_section()
        table.add_row(f"[bold cyan]{title_of[group[0].name]}[/] [dim]· {len(group)} layouts[/]")
        for s in group:
            table.add_row(
                *row(
                    s,
                    "",
                    pattern,
                    relation(s, group, prefix),
                    activity=activity.get(s.name),
                    with_git=with_git,
                )
            )
            shown += 1
    if singles:
        table.add_section()
        table.add_row("[bold cyan]other sites[/] [dim]· one layout each[/]")
        for s in singles:
            table.add_row(
                *row(s, "", pattern, name_hint(s, titles), activity=activity.get(s.name), with_git=with_git)
            )
            shown += 1
    console.print(table)

    for s in others:
        keys = ", ".join(s.top_keys) or "empty"
        console.print(f"\n[dim]not a layout (no nodes):[/] {s.file.path.name} [dim]({keys})[/]")
    where = ", ".join(pretty(d) for d in dirs)
    counted = f"{shown} of {len(summaries)} layouts" if shown != len(summaries) else f"{shown} layouts"
    states = Counter(a.status for a in activity.values())
    tally = " · ".join(f"{states[k]} {k}" for k in ("active", "quiet", "unused") if states[k])
    console.print(
        f"\n[dim]{counted} in {where} · grouped by section comments and shared node positions[/]\n"
        f"[dim]{tally}[/]\n{STATUS_LEGEND}\n"
        f"[dim]{CHANGED_LEGEND}[/]\n"
        f"[dim]render one with:[/] {invocation()} [cyan]<layout>[/]"
    )
    return 0


def invocation() -> str:
    """How this script was started, for copy-pasteable hints (`uv run` sets $UV)."""
    script = pretty(Path(sys.argv[0]).resolve()) if sys.argv and sys.argv[0] else "layout_plotter.py"
    return f"uv run {script}" if os.environ.get("UV") else script


def row(
    s: LayoutSummary, indent: str, pattern: str, note: str, *, activity: Activity | None, with_git: bool
) -> tuple[str, ...]:
    """One table row: status mark + name, counts, activity, note."""
    mark = STATUS_MARK[activity.status] if activity else " "
    label = f"[bold]{s.name}[/]" if pattern and pattern.lower() in s.name.lower() else s.name
    name = f"{indent}{mark} {label}"
    changed, used = activity_cells(activity, users_label="scenarios")
    act = (changed, used) if with_git else (used,)
    if s.error:
        return (name, *[""] * 7, *act, f"[red]could not read: {escape(s.error)}[/]")
    k = s.kinds
    return (
        name,
        count(s.floors),
        count(s.nodes),
        count(k["Parking"]),
        count(k["Bay"]),
        count(sum(k[c] for c in CHARGERS)),
        count(s.vrcs),
        f"{s.size[0]:.0f} × {s.size[1]:.0f}",
        *act,
        " · ".join(filter(None, (note, name_mismatch(s)))),
    )


def name_mismatch(s: LayoutSummary) -> str:
    return f"[yellow]name: {s.yaml_name}[/]" if s.yaml_name and s.yaml_name != s.name else ""


# =============================================================================================
# Console
# =============================================================================================


def summary_table(scene: Scene) -> Table:
    counts = Counter((n.floor, n.kind) for n in scene.nodes)
    floors = floors_of(scene)
    table = Table(title="nodes", title_justify="left", header_style="bold", box=None, padding=(0, 2))
    table.add_column("type")
    for f in floors:
        table.add_column(f"floor {f}", justify="right")
    for kind in sorted({k for _, k in counts}):
        table.add_row(kind, *(str(counts.get((f, kind), "·")) for f in floors))
    return table


# =============================================================================================
# CLI
# =============================================================================================


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderOptions:
    layout_name: str
    output: Path
    show: bool
    labels: bool
    theme: ThemeName
    stall: StallSize | None
    plotlyjs: Literal[True, "cdn"]
    layouts_dirs: tuple[Path, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ListOptions:
    pattern: str
    layouts_dirs: tuple[Path, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Options:
    command: RenderOptions | ListOptions
    debug: bool


def parse_args(argv: Sequence[str] | None = None) -> Options:
    parser = argparse.ArgumentParser(
        prog="layout_plotter",
        description="Render a layout as an interactive, standalone HTML floor plan.",
        epilog=(
            "examples:\n"
            "  uv run layout_plotter.py --list\n"
            "  uv run layout_plotter.py --list pecos\n"
            "  uv run layout_plotter.py 5675_pecos_combined --show\n"
            "  uv run layout_plotter.py 5675_pecos_combined -o /tmp/pecos.html --theme light\n"
            "  uv run layout_plotter.py path/to/layout.yaml"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "layout_name", metavar="LAYOUT", nargs="?", help="layout name or path to the YAML file"
    )
    parser.add_argument(
        "-l",
        "--list",
        metavar="PATTERN",
        nargs="?",
        const="",
        help="list the available layouts (optionally only names containing PATTERN) and exit",
    )
    parser.add_argument(
        "--layouts-dir",
        type=Path,
        action="append",
        default=[],
        metavar="DIR",
        help=f"extra folder to look for layouts in (repeatable; also ${LAYOUTS_ENV})",
    )
    parser.add_argument("-o", "--output", type=Path, help="output .html path (default: ./<LAYOUT>.html)")
    parser.add_argument("--show", action="store_true", help="open the result in a web browser")
    parser.add_argument("--no-labels", dest="labels", action="store_false", help="hide node labels")
    parser.add_argument(
        "--theme",
        type=ThemeName,
        choices=list(ThemeName),
        default=ThemeName.AUTO,
        help="theme the page opens in; auto follows the OS / your last toggle (default: auto)",
    )
    parser.add_argument(
        "--stall",
        nargs=2,
        type=float,
        metavar=("LENGTH", "WIDTH"),
        help="stall size in metres (default: the layout's largest parking window)",
    )
    parser.add_argument(
        "--cdn", action="store_true", help="load plotly.js from a CDN (small file, needs internet)"
    )
    parser.add_argument("--debug", action="store_true", help="show the full traceback on failure")
    args = parser.parse_args(argv)

    if args.list is not None:
        listing = ListOptions(
            pattern=args.list or args.layout_name or "", layouts_dirs=tuple(args.layouts_dir)
        )
        return Options(command=listing, debug=args.debug)
    if args.layout_name is None:
        parser.error("LAYOUT is required (use --list to see what is available)")

    output: Path = args.output or Path(Path(args.layout_name).name)
    render = RenderOptions(
        layout_name=args.layout_name,
        output=output.with_suffix(".html"),
        show=args.show,
        labels=args.labels,
        theme=args.theme,
        stall=StallSize(*args.stall) if args.stall else None,
        plotlyjs="cdn" if args.cdn else True,
        layouts_dirs=tuple(args.layouts_dir),
    )
    return Options(command=render, debug=args.debug)


def render(opts: RenderOptions, console: Console) -> int:
    path = resolve_layout(opts.layout_name, layout_dirs(opts.layouts_dirs))
    title = path.stem

    with console.status(f"loading [bold]{pretty(path)}[/]…"):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, Mapping):
            raise ValueError(f"{pretty(path)} is not a layout (expected a YAML mapping)")
        scene = build_scene(doc, opts.stall)
    if not scene.nodes:
        raise ValueError(f"layout {opts.layout_name!r} has no nodes")

    with console.status("rendering…"):
        figures = {
            t: {
                f: build_floor_figure(scene, f, title=title, palette=PALETTES[t], show_labels=opts.labels)
                for f in floors_of(scene)
            }
            for t in (ThemeName.DARK, ThemeName.LIGHT)
        }
        page = page_html(figures, floor_tabs(scene), title=title, theme=opts.theme, plotlyjs=opts.plotlyjs)
        opts.output.parent.mkdir(parents=True, exist_ok=True)
        opts.output.write_text(page, encoding="utf-8")

    matched_by_name = Path(opts.layout_name).stem != path.stem
    console.print(
        f"[dim]layout[/]  {pretty(path)}"
        + (f"  [dim](matched by name: {opts.layout_name})[/]" if matched_by_name else "")
    )
    console.print(summary_table(scene))
    for note in scene.notes:
        console.print(f"[yellow]note:[/] {note}")
    size_kb = opts.output.stat().st_size / 1024
    console.print(f"[green]✓[/] wrote [bold]{opts.output}[/] ({size_kb:,.0f} KB)")
    if opts.show:
        webbrowser.open(opts.output.resolve().as_uri())
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    opts = parse_args(argv)
    console = Console()
    try:
        match opts.command:
            case ListOptions(pattern=pattern, layouts_dirs=extra):
                return print_layouts(console, pattern, extra)
            case RenderOptions() as render_opts:
                return render(render_opts, console)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI boundary: report, don't crash
        err = Console(stderr=True)
        if opts.debug:
            err.print_exception()
        else:
            err.print(f"[bold red]error:[/] {exc}\n[dim]rerun with --debug for the traceback[/]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())