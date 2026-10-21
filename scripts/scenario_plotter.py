#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["plotly>=6.1", "rich>=13", "pyyaml>=6"]
# ///
"""Render a sim scenario as a standalone, interactive HTML page.

The scenario's layout is drawn with layout_plotter.py (keep the two scripts side by side) and its
initial state on top: AGVs, trays and their payloads at their garage poses, plus nodes that the
events disable. A sidebar holds the scenario's notes (its header comments), the initial state and
the events timeline; hover a row to highlight the nodes it refers to, click it to jump there.

Scenario YAML as read here (see src/scenario/scenarios):
    layout: <layout name>
    initial_conditions:
      agvs:  [{id, garage_pose: {node_id, heading}}, ...]
      trays: [{id, garage_pose: {node_id, heading}, payload: {id, length_m, width_m}}, ...]
    events: [{type, time, ...}, ...]      any *node_id / agv_id / tray_id / payload_id field is linked

Examples:
    uv run scenario_plotter.py --list
    uv run scenario_plotter.py --list eccles
    uv run scenario_plotter.py 576_eccles_budget_sandbox_agv_in_the_way --show
"""

import argparse
import html
import math
import re
import webbrowser
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

import layout_plotter as lp
import plotly.graph_objects as go
import yaml
from rich.console import Console
from rich.console import Group
from rich.markup import escape
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

LAYOUT_PLOTTER_API: Final = 3  # layout_plotter.API_VERSION this script was written against
if getattr(lp, "API_VERSION", 0) < LAYOUT_PLOTTER_API:
    raise SystemExit(
        f"error: {lp.__file__} is older than this scenario_plotter.py needs "
        f"(API {getattr(lp, 'API_VERSION', 1)}, need {LAYOUT_PLOTTER_API}).\n"
        "Replace it with the layout_plotter.py that came with this script; keep both in the same folder."
    )

type Point = lp.Point
type Polygon = lp.Polygon
type Traces = tuple[go.Scatter, ...]

# =============================================================================================
# Plain data
# =============================================================================================


@dataclass(frozen=True, slots=True)
class Pose:
    node: int
    heading: float


@dataclass(frozen=True, slots=True)
class Payload:
    id: str
    length: float | None
    width: float | None

    @property
    def short(self) -> str:
        """First block of a GUID (B138BD8E-CEEF-... -> B138BD8E); short ids as they are."""
        return self.id.split("-")[0] if len(self.id) > 16 and "-" in self.id else self.id


@dataclass(frozen=True, slots=True)
class Agv:
    id: int
    pose: Pose | None
    note: str = ""

    @property
    def label(self) -> str:
        return f"a{self.id}"


@dataclass(frozen=True, slots=True)
class Tray:
    id: int
    pose: Pose | None
    payload: Payload | None
    note: str = ""

    @property
    def label(self) -> str:
        return f"t{self.id}"


@dataclass(frozen=True, slots=True)
class Refs:
    nodes: tuple[int, ...] = ()
    agvs: tuple[int, ...] = ()
    trays: tuple[int, ...] = ()
    payloads: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Event:
    index: int  # position in the file (ties in time keep file order)
    time: float | None
    type: str
    fields: Mapping[str, Any]  # everything except type and time
    refs: Refs


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    path: Path
    layout: str | None
    agvs: tuple[Agv, ...]
    trays: tuple[Tray, ...]
    events: tuple[Event, ...]
    notes: tuple[str, ...]  # top-level comment blocks

    @property
    def payloads(self) -> tuple[Payload, ...]:
        return tuple(t.payload for t in self.trays if t.payload)

    @property
    def is_event_only(self) -> bool:
        """An event sequence with no layout or initial state, meant to run on top of a scenario."""
        return self.layout is None and not self.agvs and not self.trays and bool(self.events)

    @property
    def end_time(self) -> float | None:
        times = [e.time for e in self.events if e.time is not None]
        return max(times) if times else None


@dataclass(frozen=True, slots=True)
class NodeToggle:
    node: int
    time: float | None
    disabled: bool


# =============================================================================================
# Parsing
# =============================================================================================

SETUP_PREFIXES: Final = ("set_", "start_", "stop_")  # configuration events, not garage actions
FLOW_PREFIXES: Final = ("wait_", "done_", "sleep")  # sequencing events (wait_for_..., done_events_wait...)
REF_KEYS: Final[Mapping[str, str]] = {
    "node_id": "nodes",
    "node_ids": "nodes",
    "node": "nodes",
    "agv_id": "agvs",
    "agv_ids": "agvs",
    "tray_id": "trays",
    "tray_ids": "trays",
    "payload_id": "payloads",
    "payload_ids": "payloads",
}


def as_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def as_pose(raw: Any) -> Pose | None:
    pose = lp.field(raw, "garage_pose", "pose") if isinstance(raw, Mapping) else None
    node = lp.field(pose, "node_id", "node") if isinstance(pose, Mapping) else None
    if node is None:
        return None
    return Pose(int(node), as_float(lp.field(pose, "heading")) or 0.0)


def as_payload(raw: Any) -> Payload | None:
    if not isinstance(raw, Mapping) or lp.field(raw, "id") is None:
        return None
    return Payload(
        str(raw["id"]),
        as_float(lp.field(raw, "length_m", "length")),
        as_float(lp.field(raw, "width_m", "width")),
    )


def walk_refs(value: Any, key: str = "") -> Iterator[tuple[str, Any]]:
    """(kind, id) for every linked field anywhere inside an event."""
    kind = next((k for suffix, k in REF_KEYS.items() if key == suffix or key.endswith("_" + suffix)), None)
    if isinstance(value, Mapping):
        for k, v in value.items():
            yield from walk_refs(v, str(k))
    elif isinstance(value, list):
        for v in value:
            yield from walk_refs(v, key)
    elif kind and value is not None:
        yield kind, value


def event_refs(raw: Mapping[str, Any]) -> Refs:
    found: defaultdict[str, list[Any]] = defaultdict(list)
    for kind, value in walk_refs(raw):
        found[kind].append(value)

    def ints(kind: str) -> tuple[int, ...]:
        out = []
        for v in found[kind]:
            try:
                out.append(int(v))
            except (TypeError, ValueError):
                continue
        return tuple(dict.fromkeys(out))

    return Refs(
        nodes=ints("nodes"),
        agvs=ints("agvs"),
        trays=ints("trays"),
        payloads=tuple(dict.fromkeys(str(v) for v in found["payloads"])),
    )


def to_event(index: int, raw: Any) -> Event:
    raw = raw if isinstance(raw, Mapping) else {"value": raw}
    fields = {str(k): v for k, v in raw.items() if k not in ("type", "time")}
    return Event(index, as_float(raw.get("time")), str(raw.get("type", "?")), fields, event_refs(raw))


COMMENT_RE: Final = re.compile(r"^#(?!!)\s?(.*)$")
SECTION_RE: Final = re.compile(r"^\s+(agvs|trays):\s*$")
ITEM_RE: Final = re.compile(r"^\s*-\s+id:\s*(\S+)")


def header_notes(text: str) -> tuple[str, ...]:
    """Top-level comment blocks (column-0 `#` lines), split at blank lines or YAML keys."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if (m := COMMENT_RE.match(line)) is not None:
            current.append(m.group(1).rstrip())
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return tuple(
        "\n".join(b).strip("\n") for b in blocks if any(s.strip() for s in b) and not looks_like_yaml(b)
    )


YAMLISH_RE: Final = re.compile(r"^\s*(-\s+)?([\w.-]+:(\s.*)?|-\s*\S+)\s*$")


def looks_like_yaml(lines: Sequence[str]) -> bool:
    """A commented-out block of YAML (`- enabled: true`), not a note."""
    content = [ln for ln in lines if ln.strip()]
    return bool(content) and all(YAMLISH_RE.match(ln) for ln in content) and any(":" in ln for ln in content)


def entity_notes(text: str) -> Mapping[tuple[str, str], str]:
    """Indented comments right above an AGV or tray, keyed by (agvs|trays, id)."""
    notes: dict[tuple[str, str], str] = {}
    section, pending = "", list[str]()
    for line in text.splitlines():
        if (m := SECTION_RE.match(line)) is not None:
            section, pending = m.group(1), []
        elif line.strip().startswith("#") and line.startswith((" ", "\t")):
            pending.append(line.strip().lstrip("#").strip())
        elif (m := ITEM_RE.match(line)) is not None and section:
            if pending:
                notes[(section, m.group(1))] = " ".join(pending)
            pending = []
        elif line.strip():
            pending = []
    return notes


def parse_scenario(path: Path) -> Scenario:
    text = path.read_text(encoding="utf-8")
    doc = lp.yaml_load(text)
    if not isinstance(doc, Mapping):
        raise ValueError(f"{lp.pretty(path)} is not a scenario (expected a YAML mapping)")
    init = lp.field(doc, "initial_conditions") or {}
    notes = entity_notes(text)
    agvs = tuple(
        Agv(int(a["id"]), as_pose(a), notes.get(("agvs", str(a["id"])), ""))
        for a in lp.field(init, "agvs") or ()
        if isinstance(a, Mapping) and "id" in a
    )
    trays = tuple(
        Tray(
            int(t["id"]),
            as_pose(t),
            as_payload(lp.field(t, "payload")),
            notes.get(("trays", str(t["id"])), ""),
        )
        for t in lp.field(init, "trays") or ()
        if isinstance(t, Mapping) and "id" in t
    )
    events = tuple(
        sorted(
            (to_event(i, e) for i, e in enumerate(lp.field(doc, "events") or ())),
            key=lambda e: (math.inf if e.time is None else e.time, e.index),
        )
    )
    layout = lp.field(doc, "layout")
    return Scenario(
        name=path.stem,
        path=path,
        layout=None if layout is None else str(layout),
        agvs=agvs,
        trays=trays,
        events=events,
        notes=header_notes(text),
    )


def node_toggles(s: Scenario) -> tuple[NodeToggle, ...]:
    """Node enable/disable events (set_node_disabledness and friends), in time order."""
    return tuple(
        NodeToggle(n, e.time, bool(e.fields.get("disable", e.fields.get("disabled", True))))
        for e in s.events
        if "disable" in e.type or "enable" in e.type
        for n in e.refs.nodes
    )


def is_setup(event_type: str) -> bool:
    return event_type.startswith(SETUP_PREFIXES)


def is_flow(event_type: str) -> bool:
    return event_type.startswith(FLOW_PREFIXES)


def is_action(event_type: str) -> bool:
    """Something happens in the garage: patron arrivals, retrievals, moves, reparks..."""
    return not (is_setup(event_type) or is_flow(event_type))


# =============================================================================================
# Drawing (world metres; shapes from the design docs' facility.py)
# =============================================================================================

AGV_L, AGV_W = 2.2, 1.1  # schematic AGV, as in the design docs
TRAY_INSET = (0.5, 0.32)  # tray = stall minus this (length, width)


def car(center: Point, length: float, width: float, heading: float) -> tuple[Polygon, Polygon, Polygon]:
    """Top-down car (body, windshield, rear window); the windshield is on the heading side."""
    u, _ = lp.frame(heading)
    body = lp.rounded(lp.box(center, length, width, heading), min(width * 0.4, 0.8))
    front = lp.rounded(lp.box(lp.add(center, u, 0.23 * length), 0.14 * length, 0.68 * width, heading), 0.12)
    rear = lp.rounded(lp.box(lp.add(center, u, -0.21 * length), 0.10 * length, 0.60 * width, heading), 0.1)
    return body, front, rear


def agv_shapes(
    center: Point, heading: float
) -> tuple[Polygon, Polygon, tuple[Polygon, ...], tuple[Point, ...]]:
    """(body, lift plate, wheels, front chevron) of a schematic AGV."""
    u, v = lp.frame(heading)
    hx, hy = AGV_L / 2, AGV_W / 2
    body = lp.rounded(lp.box(center, AGV_L, AGV_W, heading), 0.3)
    plate = lp.rounded(lp.box(center, 0.4 * AGV_L, 0.56 * AGV_W, heading), 0.08)
    wheels = tuple(
        lp.rounded(lp.box(lp.add(lp.add(center, u, along), v, side * hy), 0.2 * AGV_L, 0.12, heading), 0.04)
        for along in (-hx + 0.26 * AGV_L, hx - 0.26 * AGV_L)
        for side in (-1, 1)
    )
    tip = lp.add(center, u, hx - 0.06 * AGV_L)
    back = lp.add(center, u, hx - 0.2 * AGV_L)
    chevron = (lp.add(back, v, 0.26 * AGV_W), tip, lp.add(back, v, -0.26 * AGV_W))
    return body, plate, wheels, chevron


def legend_swatch(name: str, rank: int, *, symbol: str, fill: str, line: str, size: float = 13) -> go.Scatter:
    return go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker={"symbol": symbol, "size": size, "color": fill, "line": {"color": line, "width": 1.6}},
        name=name,
        legendgroup=name,
        legendrank=rank,
        showlegend=True,
    )


ENTITY_HOVER: Final = "%{customdata}<extra></extra>"


def hover(
    points: Sequence[Point], texts: Sequence[str], *, accent: str, group: str, p: lp.Palette
) -> go.Scatter:
    return go.Scatter(
        x=[q[0] for q in points],
        y=[q[1] for q in points],
        mode="markers",
        # Plotly scores a marker hover as max(d - r, 1 - 3/r): at the centre the smaller marker wins, so
        # these stay smaller than the layout's 18 px node targets and an AGV on a node shows the AGV.
        marker={"size": 16, "color": "rgba(0,0,0,0)"},
        customdata=list(texts),
        hovertemplate=ENTITY_HOVER,
        hoverlabel={"bordercolor": accent, "bgcolor": p.card},
        showlegend=False,
        legendgroup=group,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class Placed[T]:
    item: T
    node: lp.PlotNode
    heading: float


def place[T: (Agv, Tray)](
    items: Iterable[T], by_id: Mapping[int, lp.PlotNode], floor: int
) -> tuple[Placed[T], ...]:
    return tuple(
        Placed(item=i, node=by_id[i.pose.node], heading=i.pose.heading)
        for i in items
        if i.pose and i.pose.node in by_id and by_id[i.pose.node].floor == floor
    )


def tray_traces(trays: Sequence[Placed[Tray]], stall: lp.StallSize, p: lp.Palette, labels: bool) -> Traces:
    if not trays:
        return ()
    name, pname = "Tray", "Payload"
    tl, tw = stall.length - TRAY_INSET[0], stall.width - TRAY_INSET[1]
    bodies = [lp.rounded(lp.box(t.node.xy, tl, tw, t.heading), 0.15) for t in trays]
    rails = [
        (
            lp.add(lp.add(t.node.xy, u, -tl / 2 + 0.2), v, side * 0.28 * tw),
            lp.add(lp.add(t.node.xy, u, tl / 2 - 0.2), v, side * 0.28 * tw),
        )
        for t in trays
        for u, v in (lp.frame(t.heading),)
        for side in (-1, 1)
    ]
    loaded = [t for t in trays if t.item.payload]
    cars = [
        car(
            t.node.xy,
            min(t.item.payload.length or tl, tl) * 0.78 if t.item.payload else 0,
            min(t.item.payload.width or tw, tw) * 0.72 if t.item.payload else 0,
            t.heading,
        )
        for t in loaded
    ]
    out: Traces = (
        legend_swatch(name, 200, symbol="square", fill=lp.tint(p.tray, 0.3, p.floor), line=p.tray),
        lp.shapes(bodies, fill=lp.tint(p.tray, 0.20, p.floor), line=p.tray, width=1.6, group=name),
        lp.segments(rails, color=lp.tint(p.tray, 0.45, p.floor), width=1, group=name),
    )
    if cars:
        out += (
            legend_swatch(
                pname, 201, symbol="square", fill=lp.tint(p.payload, 0.35, p.floor), line=p.payload
            ),
            lp.shapes(
                [c[0] for c in cars],
                fill=lp.tint(p.payload, 0.28, p.floor),
                line=p.payload,
                width=1.3,
                group=pname,
            ),
            lp.shapes(
                [w for c in cars for w in c[1:]],
                fill=lp.tint(p.payload, 0.55, p.floor),
                line=None,
                group=pname,
            ),
        )
    if labels:
        corners = [lp.bottom_left(lp.box(t.node.xy, tl - 0.4, tw - 0.3, t.heading)) for t in trays]
        out += (
            lp.labels(
                corners,
                [t.item.label for t in trays],
                position="top right",
                color=p.tray,
                halo=lp.tint(p.tray, 0.20, p.floor),
                size=11,
                weight=700,
                group=name,
            ),
        )
    texts = [
        f"<b>{t.item.label}</b>  tray<br>at {t.node.label} @ {t.heading:g}°"
        + (
            f"<br>payload {html.escape(t.item.payload.id)}"
            + (
                f"<br>{t.item.payload.length:g} × {t.item.payload.width:g} m"
                if t.item.payload.length and t.item.payload.width
                else ""
            )
            if t.item.payload
            else "<br>no payload"
        )
        + (f"<br><i>{html.escape(t.item.note)}</i>" if t.item.note else "")
        for t in trays
    ]
    return (*out, hover([t.node.xy for t in trays], texts, accent=p.tray, group=name, p=p))


def agv_traces(agvs: Sequence[Placed[Agv]], p: lp.Palette) -> Traces:
    if not agvs:
        return ()
    name = "AGV"
    parts = [agv_shapes(a.node.xy, a.heading) for a in agvs]
    # The AGV label sits beside the body, on the side away from the stall's top-left label.
    label_at = [lp.add(a.node.xy, (0.0, -AGV_W / 2 - 0.25)) for a in agvs]
    texts = [
        f"<b>{a.item.label}</b>  AGV<br>at {a.node.label} @ {a.heading:g}°"
        + (f"<br><i>{html.escape(a.item.note)}</i>" if a.item.note else "")
        for a in agvs
    ]
    return (
        legend_swatch(name, 199, symbol="square", fill=lp.tint(p.agv, 0.3, p.floor), line=p.agv),
        lp.shapes([w for q in parts for w in q[2]], fill=p.fg2, line=None, group=name),
        lp.shapes([q[0] for q in parts], fill=lp.tint(p.agv, 0.22, p.floor), line=p.agv, width=2, group=name),
        lp.shapes(
            [q[1] for q in parts],
            fill=lp.tint(p.agv, 0.32, p.floor),
            line=lp.tint(p.agv, 0.7, p.floor),
            width=1,
            group=name,
        ),
        go.Scatter(
            x=[x for q in parts for x in (*(c[0] for c in q[3]), None)],
            y=[y for q in parts for y in (*(c[1] for c in q[3]), None)],
            mode="lines",
            line={"color": p.agv, "width": 2.4},
            **lp.grouped(name),
        ),
        go.Scatter(  # AGV labels stay visible at every zoom: there are few and they matter
            x=[q[0] for q in label_at],
            y=[q[1] for q in label_at],
            mode="text",
            text=[a.item.label for a in agvs],
            textposition="bottom center",
            textfont={
                "family": lp.FONT_MONO,
                "size": 11.5,
                "color": p.agv,
                "weight": 700,
                "shadow": f"0 0 3px {p.floor}, 0 0 2px {p.floor}",
            },
            **lp.grouped(name),
        ),
        hover([a.node.xy for a in agvs], texts, accent=p.agv, group=name, p=p),
    )


def disabled_traces(
    toggles: Sequence[NodeToggle], by_id: Mapping[int, lp.PlotNode], floor: int, p: lp.Palette
) -> Traces:
    """Nodes that some event disables, marked with a red cross; hover lists when."""
    history: defaultdict[int, list[NodeToggle]] = defaultdict(list)
    for t in toggles:
        if t.node in by_id and by_id[t.node].floor == floor:
            history[t.node].append(t)
    nodes = [by_id[n] for n, ts in history.items() if any(t.disabled for t in ts)]
    if not nodes:
        return ()
    name = "Disabled node"

    def when(t: NodeToggle) -> str:
        return f"{'disabled' if t.disabled else 'enabled'} at {'?' if t.time is None else f'{t.time:g} s'}"

    return (
        legend_swatch(name, 202, symbol="x-thin", fill=p.danger, line=p.danger, size=12),
        go.Scatter(
            x=[n.x for n in nodes],
            y=[n.y for n in nodes],
            mode="markers",
            marker={"symbol": "x-thin", "size": 16, "line": {"color": p.danger, "width": 3}},
            **lp.grouped(name),
        ),
        hover(
            [n.xy for n in nodes],
            [f"<b>{n.label}</b>  {n.kind}<br>" + "<br>".join(map(when, history[n.id])) for n in nodes],
            accent=p.danger,
            group=name,
            p=p,
        ),
    )


def highlight_trace(p: lp.Palette) -> go.Scatter:
    """Empty ring trace the sidebar fills with the nodes of the hovered row."""
    return go.Scatter(
        x=[],
        y=[],
        mode="markers",
        meta="highlight",
        # open symbols take their stroke from marker.color: set it, or plotly picks a colorway colour
        marker={"symbol": "circle-open", "size": 46, "color": p.fg, "line": {"color": p.fg, "width": 3}},
        hoverinfo="skip",
        showlegend=False,
    )


OBJECT_GROUPS: Final = ("AGV", "Tray", "Payload", "Disabled node")  # what the Show/Dim/Hide control fades


def scenario_traces(s: Scenario, scene: lp.Scene, floor: int, p: lp.Palette, *, labels: bool) -> Traces:
    by_id = {n.id: n for n in scene.nodes}
    return (
        *tray_traces(place(s.trays, by_id, floor), scene.stall, p, labels),
        *agv_traces(place(s.agvs, by_id, floor), p),
        *disabled_traces(node_toggles(s), by_id, floor, p),
        highlight_trace(p),
    )


# =============================================================================================
# Sidebar (HTML) and its script
# =============================================================================================


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


URL_RE: Final = re.compile(r"https?://[^\s<>\"']+")


def linkify(text: str) -> str:
    out, last = [], 0
    for m in URL_RE.finditer(text):
        out += [
            esc(text[last : m.start()]),
            f'<a href="{esc(m.group(0))}" target="_blank" rel="noopener">{esc(m.group(0))}</a>',
        ]
        last = m.end()
    return "".join([*out, esc(text[last:])])


def chip(text: str, kind: str, title: str = "") -> str:
    tip = f' title="{esc(title)}"' if title else ""
    return f'<span class="chip {kind}"{tip}>{esc(text)}</span>'


def fmt_time(t: float | None) -> str:
    return "—" if t is None else f"{t:g} s"


def fmt_value(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, Mapping):
        return "{" + ", ".join(f"{k}: {fmt_value(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(fmt_value(x) for x in v) + "]"
    return str(v)


def event_kind(e: Event) -> str:
    if not is_action(e.type):
        return "node" if e.refs.nodes else "setup"
    if e.refs.agvs and not e.refs.trays:
        return "agv"
    if e.refs.trays:
        return "tray"
    return "action"


@dataclass(frozen=True, slots=True)
class Locator:
    """Where things are, to turn an event's references into nodes on the map."""

    nodes: Mapping[int, lp.PlotNode]
    agv_node: Mapping[int, int]
    tray_node: Mapping[int, int]
    payload_tray: Mapping[str, int]

    def nodes_of(self, refs: Refs) -> tuple[int, ...]:
        ids = (
            *refs.nodes,
            *(self.agv_node[a] for a in refs.agvs if a in self.agv_node),
            *(self.tray_node[t] for t in refs.trays if t in self.tray_node),
            *(
                self.tray_node[self.payload_tray[q]]
                for q in refs.payloads
                if q in self.payload_tray and self.payload_tray[q] in self.tray_node
            ),
        )
        return tuple(dict.fromkeys(i for i in ids if i in self.nodes))


def locator(s: Scenario, scene: lp.Scene) -> Locator:
    return Locator(
        nodes={n.id: n for n in scene.nodes},
        agv_node={a.id: a.pose.node for a in s.agvs if a.pose},
        tray_node={t.id: t.pose.node for t in s.trays if t.pose},
        payload_tray={t.payload.id: t.id for t in s.trays if t.payload},
    )


def row_attrs(nodes: Sequence[int]) -> str:
    return f' data-nodes="{" ".join(map(str, nodes))}" tabindex="0"' if nodes else ""


def node_chip(n: lp.PlotNode | None, node_id: int) -> str:
    return chip(
        n.label if n else f"N{node_id}?", "node" if n else "missing", "" if n else "not in the layout"
    )


def ref_chips(e: Event, loc: Locator) -> str:
    return "".join(
        [
            *(node_chip(loc.nodes.get(n), n) for n in e.refs.nodes),
            *(chip(f"a{a}", "agv") for a in e.refs.agvs),
            *(chip(f"t{t}", "tray") for t in e.refs.trays),
            *(chip(Payload(q, None, None).short, "payload", q) for q in e.refs.payloads),
        ]
    )


def sidebar_html(s: Scenario, scene: lp.Scene, layout_path: Path, warnings: Sequence[str]) -> str:
    loc = locator(s, scene)
    by_id = loc.nodes
    multi = len(lp.floors_of(scene)) > 1

    def where(pose: Pose | None) -> str:
        if pose is None:
            return '<span class="missing">no pose</span>'
        n = by_id.get(pose.node)
        floor = f" · floor {n.floor}" if n and multi else ""
        return f"{node_chip(n, pose.node)} <span class='dim'>@ {pose.heading:g}°{floor}</span>"

    agv_events: defaultdict[int, list[Event]] = defaultdict(list)
    for e in s.events:
        for a in e.refs.agvs:
            agv_events[a].append(e)

    def agv_row(a: Agv) -> str:
        extra = "".join(
            f"<div class='sub'>{esc(e.type)} {esc(', '.join(f'{k}: {fmt_value(v)}' for k, v in e.fields.items() if k != 'agv_id'))} <span class='dim'>at {fmt_time(e.time)}</span></div>"
            for e in agv_events[a.id]
        )
        note = f"<div class='note'>{esc(a.note)}</div>" if a.note else ""
        nodes = (a.pose.node,) if a.pose and a.pose.node in by_id else ()
        return f"<div class='row'{row_attrs(nodes)}>{chip(a.label, 'agv')} {where(a.pose)}{note}{extra}</div>"

    def tray_row(t: Tray) -> str:
        p = t.payload
        payload = (
            f"<div class='sub'>{chip(p.short, 'payload', p.id)} <span class='mono dim'>{esc(p.id)}</span>"
            + (f" <span class='dim'>{p.length:g} × {p.width:g} m</span>" if p.length and p.width else "")
            + "</div>"
            if p
            else ""
        )
        note = f"<div class='note'>{esc(t.note)}</div>" if t.note else ""
        nodes = (t.pose.node,) if t.pose and t.pose.node in by_id else ()
        return (
            f"<div class='row'{row_attrs(nodes)}>{chip(t.label, 'tray')} {where(t.pose)}{note}{payload}</div>"
        )

    def event_row(e: Event) -> str:
        details = " · ".join(
            f"<span class='k'>{esc(k)}</span> {esc(fmt_value(v))}"
            for k, v in e.fields.items()
            if k not in REF_KEYS
        )
        return (
            f"<div class='row event {event_kind(e)}'{row_attrs(loc.nodes_of(e.refs))}>"
            f"<span class='t'>{fmt_time(e.time)}</span>"
            f"<span class='body'><span class='type'>{esc(e.type)}</span> {ref_chips(e, loc)}"
            f"{f'<span class=details>{details}</span>' if details else ''}</span></div>"
        )

    counts = [
        (len(s.agvs), "AGV", "agv"),
        (len(s.trays), "tray", "tray"),
        (len(s.payloads), "payload", "payload"),
        (len(s.events), "event", "plain"),
    ]
    summary = "".join(
        f"<span class='stat {k}'><b>{n}</b> {label}{'' if n == 1 else 's'}</span>" for n, label, k in counts
    )
    end = (
        f"<span class='stat plain'>ends <b>{fmt_time(s.end_time)}</b></span>"
        if s.end_time is not None
        else ""
    )
    notes = (
        "<details open><summary>Notes</summary>"
        + "".join(f"<pre>{linkify(n)}</pre>" for n in s.notes)
        + "</details>"
        if s.notes
        else ""
    )
    warn = (
        "<div class='warnings'>" + "".join(f"<div>⚠ {esc(w)}</div>" for w in warnings) + "</div>"
        if warnings
        else ""
    )
    agv_rows = "".join(map(agv_row, s.agvs)) or "<div class='empty'>no AGVs</div>"
    tray_rows = "".join(map(tray_row, s.trays)) or "<div class='empty'>no trays</div>"
    event_rows = "".join(map(event_row, s.events)) or "<div class='empty'>no events</div>"
    return f"""
<aside id="side" aria-label="Scenario">
  <header>
    <div class="kicker">scenario</div>
    <h1>{esc(s.name)}</h1>
    <div class="layout">layout <span class="mono">{esc(layout_path.stem)}</span></div>
    <div class="stats">{summary}{end}</div>
    <div class="controls">
      <div class="seg" role="radiogroup" aria-label="AGVs, trays and payloads" title="AGVs, trays and payloads (D)">
        <span class="seg-label">objects</span>
        <button type="button" role="radio" data-objects="show" aria-checked="true">Show</button>
        <button type="button" role="radio" data-objects="dim" aria-checked="false">Dim</button>
        <button type="button" role="radio" data-objects="hide" aria-checked="false">Hide</button>
      </div>
      <button type="button" id="clear-selection" hidden>Clear selection ✕</button>
    </div>
  </header>
  {warn}
  {notes}
  <details open><summary>AGVs <span class="count">{len(s.agvs)}</span></summary>{agv_rows}</details>
  <details open><summary>Trays <span class="count">{len(s.trays)}</span></summary>{tray_rows}</details>
  <details open><summary>Events <span class="count">{len(s.events)}</span></summary>
    <div class="timeline">{event_rows}</div>
  </details>
  <footer>hover a row to find it on the map · click to jump there · click it again, empty map or
  <kbd>Esc</kbd> to clear · <kbd>D</kbd> dims AGVs, trays and payloads · legend entries toggle each kind</footer>
</aside>
"""


SIDEBAR_CSS: Final = """
  #side {
    position: fixed; top: 0; right: 0; bottom: 0; width: var(--sidebar-w); overflow-y: auto;
    box-sizing: border-box; padding: 18px 18px 28px; background: var(--card);
    border-left: 1px solid var(--border-soft); color: var(--fg2);
    font: 13px/1.45 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
    scrollbar-width: thin;
  }
  #side .kicker { font: 600 10.5px 'JetBrains Mono', ui-monospace, monospace; letter-spacing: .08em;
    text-transform: uppercase; color: var(--faint); }
  #side h1 { margin: 2px 0 2px; font-size: 17px; font-weight: 600; color: var(--fg); overflow-wrap: anywhere; }
  #side .layout { color: var(--muted); font-size: 12px; }
  #side .mono, #side pre, #side .chip, #side .t, #side .type, #side .k {
    font-family: 'JetBrains Mono', ui-monospace, monospace; }
  #side .stats { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  #side .stat { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border-soft);
    color: var(--muted); }
  #side .stat b { color: var(--fg); font-weight: 600; }
  #side .stat.agv { border-color: var(--agv); } #side .stat.tray { border-color: var(--tray); }
  #side .stat.payload { border-color: var(--payload); }
  #side details { margin-top: 14px; border-top: 1px solid var(--border-soft); padding-top: 10px; }
  #side summary { cursor: pointer; font-weight: 600; color: var(--fg); list-style: none; display: flex;
    align-items: center; gap: 6px; }
  #side summary::before { content: "▸"; color: var(--faint); font-size: 11px; transition: transform .15s; }
  #side details[open] > summary::before { transform: rotate(90deg); }
  #side .count { font: 500 11px 'JetBrains Mono', monospace; color: var(--faint); }
  #side pre { margin: 8px 0 0; padding: 8px 10px; white-space: pre-wrap; overflow-wrap: anywhere;
    font-size: 11.5px; line-height: 1.5; color: var(--fg2); background: var(--floor);
    border: 1px solid var(--border-soft); border-radius: 8px; }
  #side a { color: var(--parking); }
  #side .row { margin: 6px 0 0; padding: 6px 8px; border-radius: 8px; border: 1px solid transparent; }
  #side .row[data-nodes] { cursor: pointer; }
  #side .row[data-nodes]:hover, #side .row.active { background: var(--floor); border-color: var(--border-soft); }
  #side .row.selected { border-color: var(--fg2); }
  #side .row:focus-visible { outline: 2px solid var(--parking); outline-offset: 1px; }
  #side .sub, #side .note { margin: 3px 0 0 2px; font-size: 12px; color: var(--muted); }
  #side .note { font-style: italic; }
  #side .dim { color: var(--faint); }
  #side .missing { color: var(--danger); }
  #side .chip { display: inline-block; font-size: 11px; font-weight: 600; padding: 0 6px; margin-right: 3px;
    border-radius: 5px; border: 1px solid var(--border-soft); color: var(--fg2); background: var(--floor); }
  #side .chip.agv { color: var(--agv); border-color: var(--agv); background: var(--agv-bg); }
  #side .chip.tray { color: var(--tray); border-color: var(--tray); background: var(--tray-bg); }
  #side .chip.payload { color: var(--payload); border-color: var(--payload); background: var(--payload-bg); }
  #side .chip.node { color: var(--fg2); }
  #side .chip.missing { color: var(--danger); border-color: var(--danger); background: var(--danger-bg); }
  #side .timeline { position: relative; margin-top: 4px; }
  #side .event { display: grid; grid-template-columns: 56px 1fr; gap: 8px; align-items: baseline;
    border-left: 3px solid var(--border-soft); border-radius: 0 8px 8px 0; }
  #side .event.node { border-left-color: var(--danger); }
  #side .event.agv { border-left-color: var(--agv); }
  #side .event.tray { border-left-color: var(--tray); }
  #side .event.action { border-left-color: var(--payload); }
  #side .t { font-size: 11.5px; color: var(--muted); text-align: right; }
  #side .type { font-size: 12px; font-weight: 600; color: var(--fg); margin-right: 4px; }
  #side .event.setup .type { font-weight: 500; color: var(--fg2); }
  #side .details { display: block; font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
  #side .k { color: var(--faint); font-size: 11px; }
  #side .empty { color: var(--faint); font-style: italic; margin-top: 6px; }
  #side .warnings { margin-top: 12px; padding: 8px 10px; border-radius: 8px; color: var(--danger);
    background: var(--danger-bg); border: 1px solid var(--danger); font-size: 12px; }
  #side footer { margin-top: 18px; font-size: 11.5px; color: var(--faint); }
  #side .controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; }
  #side .seg { display: inline-flex; align-items: center; gap: 2px; padding: 2px; border-radius: 8px;
    border: 1px solid var(--border-soft); background: var(--floor); }
  #side .seg-label { font: 600 10.5px 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: .06em;
    color: var(--faint); padding: 0 6px 0 6px; }
  #side .seg button, #side #clear-selection { all: unset; cursor: pointer; font-size: 12px; padding: 3px 9px;
    border-radius: 6px; color: var(--muted); }
  #side .seg button:hover, #side #clear-selection:hover { color: var(--fg); }
  #side .seg button[aria-checked="true"] { background: var(--card); color: var(--fg); font-weight: 600;
    box-shadow: 0 0 0 1px var(--border-soft); }
  #side .seg button:focus-visible, #side #clear-selection:focus-visible { outline: 2px solid var(--parking); }
  #side #clear-selection { border: 1px solid var(--border-soft); }
  #side #clear-selection[hidden] { display: none; }
  #side kbd { font: 11px 'JetBrains Mono', monospace; padding: 0 4px; border: 1px solid var(--border-soft);
    border-radius: 4px; }
  @media (max-width: 760px) {
    body.with-sidebar { --sidebar-w: 0px; }
    #side { top: auto; height: 42vh; width: 100%; border-left: 0; border-top: 1px solid var(--border-soft); }
    body.with-sidebar #plot { right: 0; bottom: 42vh; }
  }
"""

SIDEBAR_JS: Final = """
(() => {
  const page = window.layoutPage;
  const gd = page.gd;
  const nodes = PAGE.extra.nodes;  // id -> [x, y, floor]
  const OBJECTS = new Set(PAGE.extra.objectGroups);  // legend groups drawn by the scenario
  const side = document.getElementById("side");
  const clearBtn = document.getElementById("clear-selection");
  let selected = null;  // the clicked row: its ring stays until cleared
  let objects = "show";  // show | dim | hide

  const idsOf = (row) => (row && row.dataset.nodes ? row.dataset.nodes.split(" ").filter((i) => i in nodes) : []);
  const ringIndex = () => gd.data.findIndex((t) => t.meta === "highlight");

  function ring(ids) {
    const i = ringIndex();
    if (i < 0) return;
    const here = ids.filter((id) => String(nodes[id][2]) === page.state.floor);
    Plotly.restyle(gd, { x: [here.map((id) => nodes[id][0])], y: [here.map((id) => nodes[id][1])] }, [i]);
  }

  // ---- show / dim / hide the scenario's objects (AGVs, trays, payloads, disabled-node marks) --------
  // Legend swatches (data-less traces) are left alone so the legend keeps its colours.
  function applyObjects() {
    const idx = gd.data.flatMap((t, i) =>
      OBJECTS.has(t.legendgroup) && !(t.x && t.x.length === 1 && t.x[0] === null) ? [i] : []);
    if (!idx.length) return;
    Plotly.restyle(gd, { opacity: { show: 1, dim: 0.18, hide: 0 }[objects] }, idx);
    // Tooltip traces (invisible markers with a hovertemplate) are switched off when hidden: plotly
    // ignores hoverinfo "skip" once a hovertemplate is set. Groups hidden from the legend stay hidden.
    const tips = idx.filter((i) => gd.data[i].hovertemplate);
    const off = tips.filter((i) => gd.data[i].visible !== "legendonly" && gd.data[i].visible !== false);
    const back = tips.filter((i) => gd.data[i].visible === false);
    if (objects === "hide" && off.length) Plotly.restyle(gd, { visible: false }, off);
    if (objects !== "hide" && back.length) Plotly.restyle(gd, { visible: true }, back);
    for (const b of side.querySelectorAll("[data-objects]")) b.setAttribute("aria-checked", String(b.dataset.objects === objects));
  }
  function setObjects(mode) { objects = mode; applyObjects(); }
  side.querySelectorAll("[data-objects]").forEach((b) => b.addEventListener("click", () => setObjects(b.dataset.objects)));

  // ---- selection ---------------------------------------------------------------------------------
  function clearSelection() {
    side.querySelectorAll(".row.selected").forEach((r) => r.classList.remove("selected"));
    selected = null;
    clearBtn.hidden = true;
    ring([]);
  }

  function centre(ids) {
    const fl = gd._fullLayout, xa = fl.xaxis, ya = fl.yaxis;
    const xs = ids.map((id) => nodes[id][0]), ys = ids.map((id) => nodes[id][1]);
    const pad = 6;  // metres around the referenced nodes
    const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
    const span = (r) => Math.abs(r[1] - r[0]);
    // Keep the current zoom if everything fits; otherwise zoom out just enough (aspect stays 1:1).
    const perPx = Math.max(span(xa.range) / xa._length, (x1 - x0) / xa._length, (y1 - y0) / ya._length);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, hw = (perPx * xa._length) / 2, hh = (perPx * ya._length) / 2;
    return Plotly.relayout(gd, { "xaxis.range": [cx - hw, cx + hw], "yaxis.range": [cy - hh, cy + hh] });
  }

  async function jump(row) {
    if (row === selected) { clearSelection(); return; }  // clicking the selected row again deselects
    const ids = idsOf(row);
    if (!ids.length) return;
    side.querySelectorAll(".row.selected").forEach((r) => r.classList.remove("selected"));
    selected = row;
    row.classList.add("selected");
    clearBtn.hidden = false;
    const floorsHit = [...new Set(ids.map((id) => String(nodes[id][2])))];
    if (!floorsHit.includes(page.state.floor)) await page.show({ floor: floorsHit[0] });
    const here = ids.filter((id) => String(nodes[id][2]) === page.state.floor);
    ring(here);
    await centre(here);
  }

  side.addEventListener("mouseover", (e) => {
    const row = e.target.closest(".row[data-nodes]");
    if (!row) return;
    row.classList.add("active");
    ring(idsOf(row));
  });
  side.addEventListener("mouseout", (e) => {
    const row = e.target.closest(".row[data-nodes]");
    if (!row || row.contains(e.relatedTarget)) return;
    row.classList.remove("active");
    ring(idsOf(selected));
  });
  side.addEventListener("click", (e) => {
    if (e.target.closest("a, summary, button")) return;
    const row = e.target.closest(".row[data-nodes]");
    if (row) jump(row);
    else if (selected) clearSelection();  // empty sidebar space
  });
  side.addEventListener("keydown", (e) => {
    const row = e.target.closest(".row[data-nodes]");
    if (row && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); jump(row); }
  });
  clearBtn.addEventListener("click", clearSelection);

  // A click on the map that is not a drag (pan / zoom box) clears the selection. Plotly covers the
  // page with a drag layer while the button is down, so the release is caught on the document.
  let down = null;
  gd.addEventListener("pointerdown", (e) => {
    down = e.target.closest(".modebar, .legend") ? null : [e.clientX, e.clientY];
  }, true);
  document.addEventListener("pointerup", (e) => {
    if (down && selected && Math.hypot(e.clientX - down[0], e.clientY - down[1]) < 4) clearSelection();
    down = null;
  }, true);

  document.addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey || e.target.closest("input, textarea")) return;
    if (e.key === "Escape") clearSelection();
    if (e.key.toLowerCase() === "d") setObjects({ show: "dim", dim: "hide", hide: "show" }[objects]);
  });
  // Redraws (floor / theme switches) bring fresh traces: reapply the objects mode and the selection.
  document.addEventListener("layout:shown", () => { applyObjects(); ring(idsOf(selected)); });
  applyObjects();
})();
"""

# =============================================================================================
# Finding scenarios
# =============================================================================================

SCENARIOS_ENV: Final = lp.SCENARIOS_ENV
scenario_dirs = lp.scenario_dirs  # --scenarios-dir, $VOLLEY_SCENARIOS, installed, then the workspace


def find_scenarios(dirs: Iterable[Path]) -> tuple[lp.LayoutFile, ...]:
    return lp.find_layouts(dirs)  # same rules: every *.yaml, symlink-install duplicates removed


def infer_layout(name: str, layout_names: Iterable[str]) -> str | None:
    """The longest layout name that `name` starts with (`175_e82nd_events_drain` -> `175_e82nd`)."""
    hits = [n for n in layout_names if name.startswith(n + "_")]
    return max(hits, key=len) if hits else None


def known_layout_names(layout_extra: Sequence[Path]) -> frozenset[str]:
    files = lp.find_layouts(lp.layout_dirs(layout_extra))
    return frozenset({f.name for f in files} | {n for f in files if (n := lp.yaml_name(f.path))})


def resolve_scenario(name: str, dirs: Sequence[Path]) -> Path:
    if (path := Path(name).expanduser()).is_file():
        return path
    stem = Path(name).stem
    for f in find_scenarios(dirs):
        if f.name == stem:
            return f.path
    searched = "\n  ".join(map(lp.pretty, dirs)) or "(no scenario folders found)"
    raise FileNotFoundError(
        f"no scenario named {stem!r}; searched:\n  {searched}\n"
        f"use --list to see what is available, or --scenarios-dir / ${SCENARIOS_ENV} to add a folder"
    )


# =============================================================================================
# --list
# =============================================================================================


@dataclass(frozen=True, slots=True)
class Listed:
    file: lp.LayoutFile
    scenario: Scenario | None
    error: str | None = None


def read_listed(f: lp.LayoutFile) -> Listed:
    try:
        return Listed(f, parse_scenario(f.path))
    except (OSError, yaml.YAMLError, ValueError, KeyError, TypeError) as exc:
        return Listed(f, None, type(exc).__name__)


def actions(s: Scenario) -> str:
    """Garage actions by count; setup (set_/start_) and sequencing (wait_/done_) events are left out."""
    kinds = Counter(e.type for e in s.events if is_action(e.type))
    return ", ".join(f"{k}" + (f" ×{n}" if n > 1 else "") for k, n in kinds.most_common())


JIRA_RE: Final = re.compile(r"https?://[^\s/]*atlassian\.net/browse/([A-Z][A-Z0-9]+-\d+)\S*")


def compact_links(text: str) -> str:
    """Jira links become their key (SW2-77); other links their host and last path segment."""
    text = JIRA_RE.sub(r"\1", text)

    def shorten(m: re.Match[str]) -> str:
        url = m.group(0).rstrip(".,)")
        host = re.sub(r"^https?://(www\.)?", "", url).split("/", 1)[0]
        tail = url.rstrip("/").rsplit("/", 1)[-1]
        return host if tail == host or tail.startswith("http") else f"{host}/…/{tail}"

    return URL_RE.sub(shorten, text)


def first_note(s: Scenario, width: int = 48) -> str:
    """The first line of the scenario's header comments, links shortened, cut to `width`."""
    line = next((ln.strip() for n in s.notes for ln in n.splitlines() if ln.strip()), "")
    line = compact_links(line)
    return line if len(line) <= width else line[: width - 1] + "…"


ACTIONS_MIN: Final = 20  # actions keep this much room; "referenced in" gets what is left (12 to 34)


def scenario_table(*, with_git: bool, name_width: int, width: int) -> Table:
    table = Table(header_style="bold", box=None, padding=(0, 1), pad_edge=False)
    # Name, with the scenario's first note under it (wrapped to the column).
    table.add_column("scenario", min_width=name_width, max_width=name_width, overflow="fold")
    for col in ("agvs", "trays", "payloads", "events"):
        table.add_column(col, justify="right", no_wrap=True, min_width=len(col))
    if with_git:
        table.add_column("changed", style="dim", no_wrap=True, min_width=10)
    fixed = (
        name_width
        + sum(len(c) + 2 for c in ("agvs", "trays", "payloads", "events"))
        + (12 if with_git else 0)
    )
    refs_width = max(12, min(34, width - fixed - ACTIONS_MIN - 4))
    table.add_column(
        "referenced in",
        style="dim",
        no_wrap=True,
        overflow="ellipsis",
        min_width=refs_width,
        max_width=refs_width,
    )
    table.add_column(
        "actions", style="dim", no_wrap=True, overflow="ellipsis", min_width=ACTIONS_MIN
    )  # one per line
    return table


def action_lines(s: Scenario) -> str:
    """Garage actions, one per line, most frequent first."""
    kinds = Counter(e.type for e in s.events if is_action(e.type))
    return "\n".join(f"{k}" + (f" [dim]×{n}[/]" if n > 1 else "") for k, n in kinds.most_common())


def add_group(
    table: Table, title: str, items: Sequence[Listed], activity: Mapping[str, lp.Activity], *, note: str = ""
) -> int:
    with_git = any(c.header == "changed" for c in table.columns)
    width = table.columns[0].max_width or 50
    table.add_section()
    table.add_row(f"[bold cyan]{title}[/] [dim]· {len(items)}[/]{f'  {note}' if note else ''}")
    for item in sorted(items, key=lambda i: i.file.name.lower()):
        act = activity.get(item.file.name)
        mark = lp.STATUS_MARK[act.status] if act else " "
        changed, refs = lp.activity_cells(act)
        git_cells = (changed,) if with_git else ()
        title_line = Text.from_markup(f"{mark} {escape(item.file.name)}")
        if item.scenario is None:
            problem = Padding(Text(f"could not read: {item.error}", style="red"), (0, 0, 0, 2))
            table.add_row(Group(title_line, problem), *[""] * 4, *git_cells, refs, "")
            continue
        sc = item.scenario
        memo = first_note(sc, 2 * (width - 2))
        # The note wraps under the name, indented, instead of being cut off in a column of its own.
        name = (
            Group(title_line, Padding(Text(memo, style="dim italic"), (0, 0, 0, 2))) if memo else title_line
        )
        table.add_row(
            name,
            lp.count(len(sc.agvs)),
            lp.count(len(sc.trays)),
            lp.count(len(sc.payloads)),
            lp.count(len(sc.events)),
            *git_cells,
            refs,
            action_lines(sc),
        )
    return len(items)


def scenario_activity(files: Sequence[lp.LayoutFile], dirs: Sequence[Path]) -> Mapping[str, lp.Activity]:
    root = next((r for d in dirs if (r := lp.git_root(d))), None)
    if root is None:
        return {}
    history = lp.git_histories(root, [f.path for f in files])
    refs = lp.git_refs(root, [f.name for f in files], dirs)
    return {
        f.name: lp.Activity(history=history.get(f.path.resolve()), refs=refs.get(f.name, ())) for f in files
    }


def print_scenarios(
    console: Console, pattern: str, extra: Sequence[Path], layout_extra: Sequence[Path], *, show_all: bool
) -> int:
    dirs = scenario_dirs(extra)
    if not dirs:
        console.print(
            f"[yellow]no scenario folders found[/] - pass --scenarios-dir, set ${SCENARIOS_ENV}, "
            "or run from the workspace root"
        )
        return 1
    files = find_scenarios(dirs)
    with console.status(f"reading {len(files)} scenarios…"):
        listed = tuple(map(read_listed, files))
        layout_names = known_layout_names(layout_extra)
        activity = scenario_activity(files, dirs)

    match = pattern.lower()
    picked = [
        i
        for i in listed
        if not match
        or match in i.file.name.lower()
        or match in ((i.scenario and i.scenario.layout) or "").lower()
    ]
    unreadable = [i for i in picked if i.scenario is None]
    event_only = [i for i in picked if i.scenario and i.scenario.is_event_only]
    scenarios = [i for i in picked if i.scenario and not i.scenario.is_event_only]
    by_layout: defaultdict[str, list[Listed]] = defaultdict(list)
    for i in scenarios:
        by_layout[(i.scenario and i.scenario.layout) or "(no layout)"].append(i)
    renderable = sorted((k for k in by_layout if k in layout_names), key=str.lower)
    missing = sorted((k for k in by_layout if k not in layout_names), key=str.lower)
    if not (by_layout or event_only or unreadable):
        console.print(f"[yellow]no scenarios matching {pattern!r}[/]")
        return 1

    name_width = min(60, max((len(i.file.name) for i in picked), default=30) + 3)
    table = scenario_table(with_git=bool(activity), name_width=name_width, width=console.width)
    for layout in renderable:
        add_group(table, layout, by_layout[layout], activity)
    for layout in missing:  # last: these cannot be rendered from the layouts we found
        add_group(table, layout, by_layout[layout], activity, note="[red]layout not found[/]")
    if show_all and event_only:
        by_guess: defaultdict[str, list[Listed]] = defaultdict(list)
        for i in event_only:
            by_guess[infer_layout(i.file.name, layout_names) or "?"].append(i)
        for guess in sorted(by_guess, key=str.lower):
            title = "event-only" + (
                f" · for {guess} (from file name)" if guess != "?" else " · layout unknown"
            )
            add_group(table, title, by_guess[guess], activity)
    if unreadable:
        add_group(table, "unreadable", unreadable, activity)
    console.print(table)

    where = ", ".join(lp.pretty(d) for d in dirs)
    total = sum(1 for i in listed if not (i.scenario and i.scenario.is_event_only))
    shown = len(scenarios) + len(unreadable)
    counted = f"{shown} of {total} scenarios" if shown != total else f"{total} scenarios"
    lines = [f"[dim]{counted} in {where} · grouped by layout[/]"]
    if missing:
        n = sum(len(by_layout[k]) for k in missing)
        lines.append(f"[dim]{n} use a layout that is not in the layout folders and cannot be rendered[/]")
    if event_only and not show_all:
        lines.append(
            f"[dim]+ {len(event_only)} event-only files (no layout or initial state; they run on top of a "
            "scenario) · [/]--all[dim] to list them[/]"
        )
    if activity:
        shown_names = {i.file.name for i in (*scenarios, *unreadable, *(event_only if show_all else ()))}
        states = Counter(activity[n].status for n in shown_names if n in activity)
        tally = " · ".join(f"{states[k]} {k}" for k in ("active", "quiet", "unused") if states[k])
        lines.append(f"[dim]{tally}[/]\n{lp.STATUS_LEGEND}")
        lines.append(f"[dim]{lp.CHANGED_LEGEND}[/]")
    lines.append(f"[dim]render one with:[/] {lp.invocation()} [cyan]<scenario>[/]")
    console.print("\n" + "\n".join(lines))
    return 0


# =============================================================================================
# Render
# =============================================================================================


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderOptions:
    scenario: str
    output: Path | None
    show: bool
    labels: bool
    theme: lp.ThemeName
    stall: lp.StallSize | None
    plotlyjs: Literal[True, "cdn"]
    layouts_dirs: tuple[Path, ...]
    scenarios_dirs: tuple[Path, ...]
    layout: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ListOptions:
    pattern: str
    show_all: bool
    layouts_dirs: tuple[Path, ...]
    scenarios_dirs: tuple[Path, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Options:
    command: RenderOptions | ListOptions
    debug: bool


def missing_refs(s: Scenario, by_id: Mapping[int, lp.PlotNode]) -> tuple[str, ...]:
    """Things the scenario puts on nodes the layout does not have."""
    placed = (
        *((a.label, a.pose.node) for a in s.agvs if a.pose),
        *((t.label, t.pose.node) for t in s.trays if t.pose),
    )
    return (
        *(f"{label} is on node {n}, which is not in the layout" for label, n in placed if n not in by_id),
        *(
            f"{e.type} at {fmt_time(e.time)} refers to node {n}, which is not in the layout"
            for e in s.events
            for n in e.refs.nodes
            if n not in by_id
        ),
    )


def render(opts: RenderOptions, console: Console) -> int:
    path = resolve_scenario(opts.scenario, scenario_dirs(opts.scenarios_dirs))
    with console.status(f"loading [bold]{lp.pretty(path)}[/]…"):
        s = parse_scenario(path)
        inferred = (
            None if (opts.layout or s.layout) else infer_layout(s.name, known_layout_names(opts.layouts_dirs))
        )
        layout = opts.layout or s.layout or inferred
        if not layout:
            what = "is an event-only file with no `layout:`" if s.is_event_only else "has no `layout:`"
            raise ValueError(f"{lp.pretty(path)} {what}; pass --layout LAYOUT to draw it on one")
        layout_path = lp.resolve_layout(layout, lp.layout_dirs(opts.layouts_dirs))
        doc = lp.yaml_load(layout_path.read_text(encoding="utf-8"))
        scene = lp.build_scene(doc, opts.stall)
    if not scene.nodes:
        raise ValueError(f"layout {layout!r} has no nodes")
    by_id = {n.id: n for n in scene.nodes}
    warnings = missing_refs(s, by_id)

    with console.status("rendering…"):
        figures = {
            t: {
                f: lp.build_floor_figure(
                    scene, f, title=s.name, palette=lp.PALETTES[t], show_labels=opts.labels
                )
                for f in lp.floors_of(scene)
            }
            for t in (lp.ThemeName.DARK, lp.ThemeName.LIGHT)
        }
        for t, per_floor in figures.items():
            for f, fig in per_floor.items():
                fig.add_traces(list(scenario_traces(s, scene, f, lp.PALETTES[t], labels=opts.labels)))
                fig.update_layout(
                    title_text=f"{s.name}<br><span style='font-size:12.5px;color:{lp.PALETTES[t].muted}'>"
                    f"layout {layout_path.stem}  ·  {len(s.agvs)} AGVs  ·  {len(s.trays)} trays  ·  "
                    f"{len(s.payloads)} payloads  ·  {len(s.events)} events</span>"
                )
        page = lp.page_html(
            figures,
            lp.floor_tabs(scene),
            title=s.name,
            theme=opts.theme,
            plotlyjs=opts.plotlyjs,
            kind="scenario",
            sidebar=sidebar_html(s, scene, layout_path, warnings),
            extra_css=SIDEBAR_CSS,
            extra_js=SIDEBAR_JS,
            extra={
                "nodes": {str(n.id): [n.x, n.y, n.floor] for n in scene.nodes},
                "objectGroups": list(OBJECT_GROUPS),
            },
        )
        output = (opts.output or Path(f"{s.name}.html")).with_suffix(".html")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page, encoding="utf-8")

    console.print(f"[dim]scenario[/] {lp.pretty(path)}")
    how = " [yellow](from the file name)[/]" if inferred else " [dim](--layout)[/]" if opts.layout else ""
    console.print(f"[dim]layout[/]   {lp.pretty(layout_path)}{how}")
    console.print(summary(s))
    for w in warnings:
        console.print(f"[yellow]warning:[/] {w}")
    console.print(f"[green]✓[/] wrote [bold]{output}[/] ({output.stat().st_size / 1024:,.0f} KB)")
    if opts.show:
        webbrowser.open(output.resolve().as_uri())
    return 0


def summary(s: Scenario) -> Table:
    table = Table(box=None, padding=(0, 2), show_header=False)
    table.add_column(style="bold")
    table.add_column()
    table.add_row("agvs", ", ".join(a.label for a in s.agvs) or "·")
    table.add_row("trays", f"{len(s.trays)} ({len(s.payloads)} with a payload)")
    table.add_row(
        "events", f"{len(s.events)}" + (f", last at {fmt_time(s.end_time)}" if s.end_time is not None else "")
    )
    if act := actions(s):
        table.add_row("actions", act)
    if s.notes:
        table.add_row("notes", first_note(s, 70))
    return table


# =============================================================================================
# CLI
# =============================================================================================


def parse_args(argv: Sequence[str] | None = None) -> Options:
    parser = argparse.ArgumentParser(
        prog="scenario_plotter",
        description="Render a sim scenario (its layout, initial state and events) as an interactive HTML page.",
        epilog=(
            "examples:\n"
            "  uv run scenario_plotter.py --list\n"
            "  uv run scenario_plotter.py --list eccles\n"
            "  uv run scenario_plotter.py 576_eccles_budget_sandbox_agv_in_the_way --show\n"
            "  uv run scenario_plotter.py path/to/scenario.yaml -o /tmp/scenario.html"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "scenario", metavar="SCENARIO", nargs="?", help="scenario name or path to the YAML file"
    )
    parser.add_argument(
        "-l",
        "--list",
        metavar="PATTERN",
        nargs="?",
        const="",
        help="list scenarios, grouped by layout (optionally only those whose name or layout contains PATTERN)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="with --list: also list event-only files (no layout or initial state)",
    )
    parser.add_argument(
        "--layout",
        metavar="LAYOUT",
        help="draw on this layout instead of the scenario's own (needed for event-only files, unless their "
        "name starts with a layout name)",
    )
    parser.add_argument("-o", "--output", type=Path, help="output .html path (default: ./<SCENARIO>.html)")
    parser.add_argument("--show", action="store_true", help="open the result in a web browser")
    parser.add_argument("--no-labels", dest="labels", action="store_false", help="hide node and tray labels")
    parser.add_argument(
        "--theme",
        type=lp.ThemeName,
        choices=list(lp.ThemeName),
        default=lp.ThemeName.AUTO,
        help="theme the page opens in; auto follows the OS / your last toggle (default: auto)",
    )
    parser.add_argument(
        "--stall",
        nargs=2,
        type=float,
        metavar=("LENGTH", "WIDTH"),
        help="stall size in metres (default: from the layout)",
    )
    parser.add_argument(
        "--cdn", action="store_true", help="load plotly.js from a CDN (small file, needs internet)"
    )
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        action="append",
        default=[],
        metavar="DIR",
        help=f"extra folder to look for scenarios in (repeatable; also ${SCENARIOS_ENV})",
    )
    parser.add_argument(
        "--layouts-dir",
        type=Path,
        action="append",
        default=[],
        metavar="DIR",
        help=f"extra folder to look for layouts in (repeatable; also ${lp.LAYOUTS_ENV})",
    )
    parser.add_argument("--debug", action="store_true", help="show the full traceback on failure")
    args = parser.parse_args(argv)

    dirs = {"layouts_dirs": tuple(args.layouts_dir), "scenarios_dirs": tuple(args.scenarios_dir)}
    if args.list is not None:
        listing = ListOptions(pattern=args.list or args.scenario or "", show_all=args.all, **dirs)
        return Options(command=listing, debug=args.debug)
    if args.scenario is None:
        parser.error("SCENARIO is required (use --list to see what is available)")
    return Options(
        command=RenderOptions(
            scenario=args.scenario,
            output=args.output,
            show=args.show,
            labels=args.labels,
            theme=args.theme,
            stall=lp.StallSize(*args.stall) if args.stall else None,
            plotlyjs="cdn" if args.cdn else True,
            layout=args.layout,
            **dirs,
        ),
        debug=args.debug,
    )


def main(argv: Sequence[str] | None = None) -> int:
    opts = parse_args(argv)
    console = Console()
    try:
        match opts.command:
            case ListOptions() as o:
                return print_scenarios(
                    console, o.pattern, o.scenarios_dirs, o.layouts_dirs, show_all=o.show_all
                )
            case RenderOptions() as o:
                return render(o, console)
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