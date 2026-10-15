"""Doc 04 (naming): one concept, many names today. Every spelling is from the source snapshots
(sources/repomix-*.xml) or, for GarageServices, from doc 02's proposal."""
from __future__ import annotations

from components import frame
from registry import figure
from svgkit import Doc, text_width
from theme import T

DOC4 = "04-naming.html"

# (concept, accent, [(current spelling, where)], proposed)
CARDS = [
    ("The motion-graph object", T.green, [
        ("gg_", "Scheduler, CollisionTable, GarageOccupancyChecker"),
        ("graph", "GarageServices (doc 02)"),
        ("base_graph_", "the Boost object inside it"),
        ("GarageGraph", "the class"),
    ], "motion_graph (MotionGraph)"),
    ("The collision-table object", T.amber, [
        ("table_", "Scheduler"),
        ("collision_table_", "GarageOccupancyChecker"),
        ("collisions", "GarageServices (doc 02)"),
    ], "collision_table"),
    ("A footprint size class", T.sky, [
        ("ParkingWindow", "message"),
        ("resource_windows", "GarageLayout.msg, Layout"),
        ("resource_size_index", "SizedPose.msg, Layout"),
        ("max_resource_size(_index)", "GarageNode.msg"),
        ("buffer", "GarageLayout.msg (the margin)"),
    ], "size class, size_class_index"),
    ("Endpoints of a move or change", T.violet, [
        ("src / dst", "Edge.msg, AgvCommand.msg"),
        ("dest_", "TrayMove"),
        ("src_state_", "BayTransition"),
        ("_curr / _next", "AgvPoseChanged, *StateChanged"),
        ("current_ / next_discrete_state", "VrcStateChanged"),
        ("from_ / to_", "VrcTransition"),
    ], "source/target, start/goal, from/to"),
    ("\"Edge\" means four things", T.teal, [
        ("Edge.msg", "two layout node ids"),
        ("GarageGraph::Edge", "Boost edge descriptor"),
        ("CollisionTable::Edge", "array of two poses"),
        ("edge (prose)", "a DAG dependency"),
    ], "edge, Edge, Segment, dependency"),
    ("\"Transition\" means three things", T.pink, [
        ("Transition", "motion-graph edge property"),
        ("TransitionType::VRC_TRANSITION", "AGV rides a VRC"),
        ("Bay/Vecs/VrcTransition", "asset state-change events"),
        ("ScheduleEventType::VRC_TRANSITION", "the event kind"),
    ], "Transition, RIDE_VRC, *StateChange"),
    ("Floor id width", T.sky, [
        ("uint8", "GarageFloor.id, GarageNode.floor, BayCommand.floor"),
        ("uint16", "DiscreteVrcState.current_floor, VrcCommand"),
        ("uint32", "GarageTray.floor, GaragePayload.floor"),
    ], "uint8 floor_id"),
    ("AGV / bay / VECS / VRC id width", T.green, [
        ("uint16", "state, event and job messages"),
        ("uint32", "ActionNode.agv_id, bay_id, vecs_id, vrc_id"),
        ("uint32_t", "Vrc::id (layout.hpp)"),
    ], "uint16"),
    ("The AGV's lift is up", T.amber, [
        ("lift", "DiscreteAgvState.msg"),
        ("lift", "AgvGoal.msg"),
        ("raised", "AgvLiftChanged.msg"),
    ], "lift_raised"),
    ("A physical thing, and its shape", T.violet, [
        ("GarageEntityId, entity_type", "asset identity"),
        ("CollisionEntityId", "footprint shape for collisions"),
        ("resource", "SetResourceDisabledness.srv"),
        ("disabledness", "messages, ScheduleContext"),
    ], "AssetId, FootprintType, disabled"),
]


@figure("82_naming_today", "One concept, many names", DOC4)
def naming_today():
    d = Doc("82_naming_today", "One concept, many names",
            "Ten concepts that have several spellings today across ROS messages and C++, each with the "
            "proposed single name.")
    ncol = 2
    cw = 780
    gap = 26
    rh = 22
    tops = [0.0] * ncol
    for k, (concept, col, rows, proposed) in enumerate(CARDS):
        c = k % ncol
        x = c * (cw + gap)
        y = tops[c]
        h = 46 + rh * len(rows) + 46
        d.rect(x, y, cw, h, rx=10, fill=T.card, stroke=T.tint(col, 0.7, T.bg), sw=1.4)
        d.text(x + 16, y + 22, concept, size=14, weight=600, fill=T.fg)
        d.text(x + cw - 16, y + 22, f"{len(rows)} places today", size=11.5, fill=T.muted, anchor="end")
        yy = y + 50
        for cur, where in rows:
            d.text(x + 16, yy, cur, size=12, family="mono", weight=600, fill=col)
            d.text(x + 330, yy, where, size=12, fill=T.fg2)
            yy += rh
        # proposed
        py = yy + 14
        d.line(x + 16, py - 16, x + cw - 16, py - 16, stroke=T.border_soft)
        d.text(x + 16, py + 2, "proposed", size=11.5, weight=600, fill=T.muted)
        w = text_width(proposed, 12.5, "mono", 700)
        d.rect(x + 96, py - 11, w + 18, 24, rx=12, fill=T.tint(col, 0.18, T.bg), stroke=col, sw=1.2)
        d.text(x + 105, py + 1, proposed, size=12.5, family="mono", weight=700, fill=T.fg)
        tops[c] = y + h + gap
    frame(d, title="One concept, many names",
          subtitle="Each card is one concept: its spellings today (mono, with where they appear) and the single "
                   "name proposed in this document. Widths are field types in the messages.",
          badge_key="as-built",
          footnote="Spellings from sources/repomix-interfaces.xml, repomix-common-ros.xml, repomix-planner-core.xml "
                   "and repomix-scheduler.xml; GarageServices from doc 02's proposal.")
    return d
