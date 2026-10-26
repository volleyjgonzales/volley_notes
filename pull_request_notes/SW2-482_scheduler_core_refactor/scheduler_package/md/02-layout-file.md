# 02 — The layout file: the garage as YAML

*One YAML file per site describes everything about the garage that does not move: where the nodes are, which headings an AGV may have at each, which nodes connect, which payload sizes fit where, where the bays and chargers face, and, for multi-floor sites, the floors and VRCs. Every planner in the pipeline is built from it.*

The Background tab describes the C++ objects built from the file ([section 8.1](#bg-layout-places-in-sorted-vectors-and-ordered-maps)). This tab is about the file itself: every key, how the parser reads it, who uses it downstream, what the parser checks and what it silently accepts, and what could be improved. All examples use the Pecos file, `sources/5675_pecos_combined.yaml` (352 lines), and the parser in `common_ros/src/layout.cpp`. Facts that are read from the code but not observed in a run are marked as such.

## What the layout file is, and who reads it

The layout is a static description: it holds no AGVs, trays or bay states (those arrive in every request as `DiscreteGarageState`). The scheduler node reads the ROS parameter `layout` (a name such as `5675_pecos_combined`), resolves it to a file with `GetLayoutPathByName` (site configuration), and the `Scheduler` constructor builds four objects from it, once, for the life of the node:

``` cpp
// scheduler.cpp, Scheduler::Scheduler(layout_filepath, logger, params)
layout_(std::make_shared<Layout>(layout_filepath)),   // parse the YAML
pg_(layout_),                                          // PoseGraph: poses and neighbour slots
gg_(pg_),                                              // GarageGraph: typed, weighted transitions
table_(gg_, logger),                                   // CollisionTable: which places conflict
```

![Diagram: the Pecos YAML file and its lookup feed a Layout class box; arrows labelled with fields lead to PoseGraph, GarageGraph and CollisionTable; three coloured buses connect Layout, GarageGraph and CollisionTable to six reader cards (scheduler, CHUGG/SIPP, action graph, safety checker, tape layout, GetGarageLayout).](figures/105_layout_consumers.svg)

**Who reads the layout file.** The YAML is looked up by name (ROS parameter `layout`, then `GetLayoutPathByName`), parsed once into a `Layout`, and expanded into a `PoseGraph`, a `GarageGraph` and a `CollisionTable`; the collision table is cached on disk under the layout name and md5. Arrow labels name the fields that flow (headings and `rotation_allowed` become poses, edges become neighbour slots, windows become footprints). In each reader, L, GG and CT mark what it reads from the Layout, the GarageGraph and the CollisionTable.

Three consequences follow from this structure:

- **A layout change needs a restart.** The four objects are members built in the constructor; nothing reloads them.
- **The md5 is part of the cache key.** The collision table is cached on disk under the layout name and the file's md5, and `GetStaticFilter` refuses a graph and a table whose md5s differ. Any byte change, a comment included, forces a rebuild of the table.
- **Everything downstream sees the layout only through these objects.** Task planning asks `layout_` for bay prioritization, inbound headings and windows; the searches and CHUGG use `gg_` and `table_`; the action graph uses `layout_` again for VRCs. Which reader uses which field is in the per-field sections below.

## The file at a glance

`Layout::Layout(YAML::Node)` reads these top-level keys and ignores any other. Pecos uses five of the eight.

| Key                           | Required?                               | What it describes                                                                  | Pecos                                                 |
|-------------------------------|-----------------------------------------|------------------------------------------------------------------------------------|-------------------------------------------------------|
| `name`                        | yes                                     | The layout's name: part of the collision-table cache key and of log and file names | `5675_pecos_combined`                                 |
| `parking_window_buffer`       | yes (`length_m`, `width_m`)             | A margin added to the windows by `GetBufferedResourceWindow`                       | 0.1524 m × 0.0762 m (6 in × 3 in)                     |
| `parking_windows`             | in practice                             | The payload size classes: name, length, width, optional height                     | COMPACT, STANDARD, LARGE, XL                          |
| `rotation_circle_tape_radius` | no (default `kDefaultTapeCircleRadius`) | Radius of the tape circle painted at rotation nodes (tape layout tool)             | absent                                                |
| `floors`                      | no (default: one floor, id 0, z 0)      | Floor ids and heights, for multi-floor sites                                       | absent                                                |
| `nodes`                       | in practice                             | Every place: position, type, size limit, headings, rotation, facing; bay extras    | 28 nodes: 13 Waypoint, 10 Parking, 3 AgvCharge, 2 Bay |
| `edges`                       | in practice                             | Which nodes connect (undirected), with an optional disallowed orientation          | 37 edges                                              |
| `vrcs`                        | no                                      | Vertical conveyors: id, root node, one node per floor                              | absent                                                |

Step through the figure to see each part of the file next to what it creates on the floor plan.

![Animated figure: an abridged listing of 5675_pecos_combined.yaml with line numbers beside the Pecos floor plan; each step highlights YAML lines and the matching stall, node, bay, charger, edges or sandbox zones on the map.](figures/106_layout_yaml_to_map.svg)

**The Pecos YAML and the map it describes.** Step through the file: each step highlights some of its lines on the left and draws what they create on the floor plan on the right: the window and buffer that size every stall, a parking node, the rotation waypoint W8, bay B21, charger C14, the edges, and the section comments that mark the two sandboxes and the measurement datum. The card under the map shows the C++ values `Layout(YAML::Node)` stores.

One Pecos node, as written in the file:

``` yaml
  - id: 8                    # node id: referenced by edges, poses, events and messages
    x: 30.8823               # metres, site frame (ENU), float32
    y: 12.7753
    type: Waypoint           # Waypoint | Parking | Bay | BLift | AgvCharge | EvCharge | Lift
    max_resource_size: XL    # largest payload window allowed here (a parking_windows name, or TRAY)
    rotation_allowed: true   # may an AGV turn in place here?
    headings:                # degrees; each one also allows its reciprocal
      - 0
      - 90
    faces_reciprocal: false  # bays and chargers: which reciprocal is the inbound heading
```

## The AGV and garage coordinate systems

Three frames appear in the code: the garage frame, in which the layout is written; the AGV's own body frame; and a helper frame that the planner's geometry code uses internally. The heading ties them together. This section states each frame and the files it is read from, because several comments in the code use the word “+y” for different axes.

![Animated diagram of the Pecos map around W8 with a side panel and a table: the garage frame, headings measured counter-clockwise from north, AGV-1 at W8 heading 90 with body axes x forward (west) and y left (south), a locomote arrow west to W31 and a strafe arrow north to W13, the planner frame P with x out of the right side and the PoseGraph slot names, footprints built in P and rotated, a 45-degree rotation-sign example, and a table mapping source files to frames.](figures/115_agv_coordinate_frames.svg)

**AGV and garage coordinate systems.** Step through the garage frame G (x east, y north, z up; node positions in metres), the heading \theta (from garage local north, counter-clockwise, 90 = west), the AGV body frame B (x forward along the long side, y left), locomote versus strafe on two real Pecos edges at W8, the planner's helper frame P (B turned by −90°: x out of the right side, y forward) and the PoseGraph slot names that live in it, footprints built in P and rotated by the heading, and a rotation-sign inconsistency that only matters at headings that are not multiples of 90°. The table lists which source file fixes which frame. The AGV is drawn as a 2.2 m × 1.1 m schematic because `common/constants.hpp` (with `kAgvLength` and `kAgvWidth`) is not in the snapshots.

### The garage frame

Node coordinates `x`, `y` (and floor heights `z`) are metres in a right-handed garage frame with **x east, y north, z up**. The axes are stated in `agv_interfaces/msg/NodeAccuracy.msg` (“the garage frame, +x (east), +y (north), +z (up)”); the origin is a site choice, recorded for Pecos only as a comment on node 22 (`# Offset "origin" (take any future measurements from here)`). “North” is the garage's local north from the CAD drawing, not geographic north (`GaragePose.msg`).

### The heading

A heading \theta is an angle measured **from garage local north, counter-clockwise**: 0 points north (+y), 90 west (−x), −90 east (+x), 180 south. `GaragePose.heading` stores it as whole degrees in \[-179, 180\], and `GeometricPose.yaw` stores the same angle in radians:

``` text
interfaces/msg/GaragePose.msg:
  # Headings are defined relative to garage local north, a direction that is defined in the CAD file.
  # Headings are right-hand, and increase in the counter clockwise direction. Thus, heading 90 points west.
  int16 heading # in degrees, [-179:180]
```

This is *not* the usual mathematical angle, which is measured from +x. The code says so where it converts: `GarageGraph::LocomoteOrStrafe` (`garage_graph.cpp`) notes that the yaw is in the “Volley heading convention (heading 0 = +y, CCW positive) — NOT the math / atan2 convention (0 = +x)” and adds \pi/2 before comparing it with an `atan2` bearing. The direction a heading points to is therefore

\mathbf{f}(\theta) = \begin{pmatrix} -\sin\theta \\ \cos\theta \end{pmatrix} = \begin{pmatrix} \cos(\theta + \pi/2) \\ \sin(\theta + \pi/2) \end{pmatrix}, \qquad \mathbf{f}(90^\circ) = \begin{pmatrix} -1 \\ 0 \end{pmatrix}\\ \text{(west)}.

### The AGV body frame

The AGV's body frame B has **x along the AGV's long side, pointing in the heading direction** (forward, the driving direction), **y to the AGV's left**, and z up. This is the frame of the AGV's own messages (“in the AGV frame” in `NodeAccuracy.msg`). The snapshots do not write its axes down anywhere; the definition above is the team's, and it is consistent with every use in the planner listed below. In the garage frame its axes are

\hat{\mathbf{x}}\_B = \mathbf{f}(\theta) = \begin{pmatrix} -\sin\theta \\ \cos\theta \end{pmatrix}, \qquad \hat{\mathbf{y}}\_B = \begin{pmatrix} -\cos\theta \\ -\sin\theta \end{pmatrix}, \qquad \mathbf{p}\_G = \mathbf{p}\_{\text{node}} + R(\theta + \pi/2)\\ \mathbf{p}\_B,

where R(\alpha) is the counter-clockwise rotation by \alpha. What the planner does with it:

- **Locomote is along body x, strafe along body y.** `IsLocomoteOrStrafe` (`common_ros/src/agv_motion_type.cpp`) calls an edge a LOCOMOTE when its bearing \operatorname{atan2}(\Delta y, \Delta x) is within 10^{-3} rad of \theta + \pi/2 or its reciprocal, which is \pm\hat{\mathbf{x}}\_B, and a STRAFE when it is near \theta, which is \pm\hat{\mathbf{y}}\_B. At W8 with heading 90, the edge to W31 (west) is a locomote and the edge to W13 (north) is a strafe.
- **The long dimensions lie along body x.** The AGV's collision footprint has `kAgvLength` along body x, and a payload window's `length_m` (the car's length) also lies along body x, so a car rides lengthwise along the AGV. Pecos confirms the orientation: its parking nodes use headings ±90, so an AGV in a stall points west or east, and the XL stalls are 5.791 m long in x and 2.21 m wide in y.
- **Inbound headings use it too.** A bay's inbound heading is the heading in which the AGV's body x points out of the bay into the garage (bay 7: −90, east, towards W31; [section 4.5](#ly-faces-reciprocal-and-the-inbound-heading)).

### The planner's helper frame

The geometry code in `common_ros` does not build footprints in B. It builds them in a frame P that is B turned by −90°: **x_P points out of the AGV's right side** (body −y) and **y_P points forward** (body +x). In P the heading is an ordinary counter-clockwise rotation from the garage axes:

\mathbf{p}\_G = \mathbf{p}\_{\text{node}} + R(\theta)\\ \mathbf{p}\_P, \qquad \hat{\mathbf{x}}\_P = \begin{pmatrix} \cos\theta \\ \sin\theta \end{pmatrix} = -\hat{\mathbf{y}}\_B, \qquad \hat{\mathbf{y}}\_P = \hat{\mathbf{x}}\_B.

That is why the code reads as if the AGV drove along “+y”. The evidence, file by file:

| Source                                                                                                  | What it says                                                                                                                                                                                               | Frame                                                             |
|---------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `common_ros/src/tape_layout.cpp`, `AddExtensionNode`                                                    | “AGV heading is zero out the right side of the vehicle”; uses `BodyToInertial(1, 0, heading)`                                                                                                              | P: the unit x vector at angle \theta points out of the right side |
| `common_ros/src/collision_geometry.cpp`, `AgvEntity::BasePoly`, `RectangleFromSize`                     | `RectangleFromSize(kAgvLength, kAgvWidth)`, but the function's signature is `RectangleFromSize(double width, double length)` and it puts its *length* argument along x: the AGV's length ends up along y_P | P, then rotated by the heading in `PolyAtPose`                    |
| `common_ros/src/collision_geometry.cpp`, payload `BasePoly`                                             | `RectangleFromSize(window_.length_m, window_.width_m)`: the window length along y_P                                                                                                                        | P                                                                 |
| `common_ros/src/polygon_utils.cpp`, `CalcOverlappingSizedPoses`                                         | “Everything is a crab, so our parking window lengths are our pose widths”; passes `width_m` as `length_along_heading`                                                                                      | P: “along heading” means along x_P, the AGV's side                |
| `common_ros/include/common_ros/layout.hpp`, `GetInboundHeading`; `pose_graph.hpp`, `GetBayOutboundPose` | “an AGV with that heading has a +y axis facing the system interior door”; “the system interior door is in the +y direction in the bay's primary pose”; the outbound move is “always a LEFT action”         | P: “+y” is y_P, the AGV's forward axis                            |
| `common_ros/src/pose_graph.cpp`, neighbour classification                                               | Bearings are measured relative to \theta used as a math angle: FORWARD = +x_P, LEFT = +y_P, BACK = -x_P, RIGHT = -y_P                                                                                      | P: FORWARD and BACK are strafes, LEFT and RIGHT locomotes         |
| `common_ros/src/agv_motion_type.cpp`, `IsLocomoteOrStrafe`; `garage_graph.cpp`, `LocomoteOrStrafe`      | Locomote along \theta + \pi/2, strafe along \theta; “heading 0 = +y”                                                                                                                                       | G and B: locomote along \hat{\mathbf{x}}\_B                       |
| `interfaces/msg/GaragePose.msg`, `GeometricPose.msg`; `agv_interfaces/msg/NodeAccuracy.msg`             | Heading from local north, counter-clockwise, 90 = west; garage +x east, +y north, +z up; offsets “in the AGV frame”                                                                                        | G and the heading; B named but not defined                        |
| `sources/5675_pecos_combined.yaml`                                                                      | Parking headings 90, stalls 5.791 m along x                                                                                                                                                                | Consistent with B: long axis along the heading                    |

**Not in the snapshots:** the values of `kAgvLength` and `kAgvWidth` (`common/constants.hpp`), and the definitions of `Wrap`, `SignedAngleDist` and `BodyToInertial`. The slot names above assume `SignedAngleDist(a, b)` = b - a, which is what makes `GetBayOutboundPose`'s “always LEFT” true.

### One inconsistency: the rotation sign

Boost's `rotate_transformer` rotates clockwise for a positive angle (the comment in `polygon_utils.cpp` says so). `CreateRectangularPolygon` and `BayOdpEntity::PolyAtPose` therefore pass `-heading` (a net counter-clockwise rotation, as the heading convention requires), but `CollisionEntity::PolyAtPose`, which places every AGV, tray and payload footprint in the collision table, passes `+heading` (a net clockwise rotation). A centred rectangle turned by \theta or -\theta is the same shape when \theta is a multiple of 90°, so Pecos and every axis-aligned layout are unaffected; at any other heading (45°, say) the collision table's footprint would be mirrored about the node's north–south axis. This is read from the code, not observed; the fix is a one-character change in `common_ros`, worth making before any layout uses diagonal headings.

### How this pack draws the frames

Map figures draw an AGV as a rounded rectangle with its long side along body x, a chevron at the front, and the label next to it; heading 90 therefore appears as an AGV pointing left (west). Where a figure needs the helper frame (the PoseGraph slots, the footprint construction), it labels the axes x_P and y_P explicitly.

## Nodes

Every node becomes one `GarageNodeMsg` in `Layout::nodes_`, sorted by id. Its fields, in file order:

### Identity and position: `id`, `x`, `y`, `floor`

These four fields name a node and place it in the site. Edges, poses and collision footprints all refer to a node through its `id` and are measured from its `x` and `y`, so these fields are the ones to understand first.

- **`id`** (required, `uint32`) is the node's name everywhere: in edges, in `GaragePose.node_id`, in events and messages. A bay's id is also its bay id (read a second time as `uint16`), so bay ids and node ids share one number space. Ids need not be contiguous: Pecos has 1–11, 13–27, 31 and 41 (no 12). Code that needs a dense index uses the position in the sorted vector, never the id ([section 9.4](#ly-edgemsg-carries-indices) shows where that distinction leaks).
- **`x`, `y`** (required, metres, read as `float`) place the node in the site frame. They decide what an edge *is* (its bearing makes it a locomote or a strafe), how long it takes (its length feeds the trapezoid cost model), and every footprint polygon in the collision table. Pecos's measurement datum is recorded only in a comment on node 22: `# Offset "origin" (take any future measurements from here)`.
- **`floor`** (optional, default 0) matters only with `floors` and VRCs: nodes on different floors never collide unless both are VRC nodes, and a segment between floors is legal only between lift nodes ([section 6](#ly-floors-and-vrcs)).

### Node types

`type` (required) is a string mapped to a `GarageNodeMsg.TYPE_*` constant; an unknown string throws. The type decides which planners may use the node and for what.

| YAML        | Constant          | Pecos | What the type drives                                                                                                                                                             |
|-------------|-------------------|-------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Waypoint`  | `TYPE_WAYPOINT`   | 13    | Aisles. A tray may be stashed on one only when `allow_waypoint_stash` is set                                                                                                     |
| `Parking`   | `TYPE_PARKING`    | 10    | Park destinations, open-space search targets, the retrieval-heading cache (`InitRetrievalHeadings`)                                                                              |
| `Bay`       | `TYPE_BAY`        | 2     | Customer bays: bay prioritization, inbound heading, the bay's overdrive-plate footprint (`BAY_ODP`)                                                                              |
| `BLift`     | `TYPE_BLIFT`      | 0     | A bay that is also a VRC terminal (“A BLift is a Bay that is also a Lift (VRC) terminal”). Same bay setup as `Bay`, but the collision table builds `BAY_ODP` only for `TYPE_BAY` |
| `AgvCharge` | `TYPE_AGV_CHARGE` | 3     | AGV chargers: `PlanAgvChargeJob` picks one; SIPP keeps any other entity off them                                                                                                 |
| `EvCharge`  | `TYPE_EV_CHARGE`  | 0     | Car chargers: only EV-charge payloads park there; the required heading is hard-coded, not read from `faces_reciprocal`                                                           |
| `Lift`      | `TYPE_LIFT`       | 0     | VRC stops: allows segments between floors                                                                                                                                        |

### `headings`: from a node to its poses

`headings` lists, in degrees, the orientations an AGV may have at the node. The parser reads each as `uint16` and sorts them. `GetAllowedHeadings` then adds every reciprocal (a centred rectangle covers the same area either way, [section 8.2](#bg-posegraph-from-nodes-to-poses)), and each resulting heading is one pose: a node with `[90]` has poses −90 and 90; node 8 with `[0, 90]` has −90, 0, 90 and 180. Pecos has 26 × 2 + 2 × 4 = 60 poses.

The heading is the direction of the AGV's body +x axis, which runs along its long side and is its driving (locomote) axis; 90 means facing west. Moving along body x is a locomote, along body y a strafe ([section 3](#ly-agv-coordinate-system)).

![Animated figure: a map crop around waypoints W8 and W9 with an AGV at the poses of node 8, coloured arrows for the FORWARD, BACK, LEFT, RIGHT and rotation slots, and a table of the eight PoseNeighbor slots for poses (8,90), (8,−90), (8,0), (8,180) and (9,90), ending with Pecos totals.](figures/107_node_to_poses.svg)

**How one node becomes poses and neighbour slots.** Step through W8 (headings \[0°, 90°\], rotation allowed) and W9 (heading \[90°\]): `GetAllowedHeadings` adds each reciprocal, so W8 has four poses and W9 two; an AGV at each pose shows that the heading is where body +x, the long and driving axis, points (90° = west). The table fills the eight `PoseNeighbor` slots as `pose_graph.cpp` does, with the direction each slot means for the AGV. The slot names are not the AGV's own frame: `FORWARD` and `BACK` are strafes out of its right and left sides, `LEFT` and `RIGHT` locomotes forward and back. (W8, 0°) and (W8, 180°) exist only as stepping stones for rotation. Pecos has 60 poses and 164 filled slots; [section 6](#ly-vertices-and-edges) shows how they connect.

Why headings matter:

- **They decide which edges exist for an AGV.** A translation from one pose to the next keeps the heading, so an edge between two nodes exists for heading *h* only if both nodes allow *h*. Node 8's extra poses 0 and 180 have no translation neighbours at all, because none of its neighbours allows 0 or 180; they exist only so that a turn from 90 to −90 can be two 90° steps.
- **They decide the inbound heading of bays and chargers**: `headings[0]`, possibly reversed by `faces_reciprocal` ([section 3.5](#ly-faces-reciprocal-and-the-inbound-heading)).
- **They are what `HasGaragePose` checks** when a request names a pose, and what the controller snaps a measured yaw to (`GetClosestHeading`).

### `rotation_allowed`

Required boolean. When true, `PoseGraph` links each pose of the node to its nearest clockwise and counter-clockwise allowed headings (`ROT_RIGHT`, `ROT_LEFT`), the GarageGraph types those links `ROTATION`, the collision table uses a circle (radius half the window's diagonal) instead of a rectangle at that node, and the tape tool paints a rotation circle. Elsewhere an AGV can only keep its heading. In Pecos only waypoints 8 and 22 allow rotation, one per sandbox; every reversal of an AGV's heading must pass through one of them. With a single heading, both rotation slots point to the reciprocal: a 180° spin.

### `faces_reciprocal` and the inbound heading

Optional boolean, default false, meaningful only for bays and chargers. The *inbound heading* of such a node is `headings[0] + 180 · faces_reciprocal` (`GetInboundHeading`): for a bay, the heading a payload facing into the garage has on insert; for a charger, the heading an AGV must have to charge. In Pecos the bays 7 and 21 and the chargers 14 and 16 set it; charger 10 does not.

![Animated figure: map of bay B7 and chargers C10 and C14 with AGVs at their inbound poses, next to the YAML entries and highlighted C++ from layout.cpp, pose_graph.cpp and scheduler.cpp; a table of raw and wrapped inbound headings; the last step marks the failing −90 == 270 comparison in red.](figures/108_inbound_heading.svg)

**How faces_reciprocal sets the inbound heading.** Step through bay 7 and chargers 10 and 14, which all list heading 90: `faces_reciprocal: true` adds 180, which gives 270, and `GetInboundHeading` does not wrap it. Wrapped, it is −90: the AGV in bay 7 faces east, towards W31, its outbound pose is the LEFT neighbour (31, −90), and parking nodes cache the reciprocal, 90, as their retrieval heading. The last step shows one place where the unwrapped value is used: `PlanAgvChargeJob` compares a stored −90 with 270, so, reading the code, an AGV already charging on C14 or C16 is not recognised as charging (not observed in a run).

The field is easy to misread, for three reasons: its name describes a mechanism (“use the reciprocal”) rather than the result; its meaning differs by node type (the header comment and `GarageNode.msg` describe the bay case differently); and the helper that applies it returns an unwrapped angle (270 rather than −90), which every caller must remember to wrap. `GetBayInboundHeading` wraps; `PlanAgvChargeJob`'s “already charging?” test does not:

``` cpp
// scheduler.cpp, Scheduler::PlanAgvChargeJob: the early return for an AGV already on its charger
if(curr_node.type == GarageNodeMsg::TYPE_AGV_CHARGE &&
    agv.pose.heading == volley::GetInboundHeading(curr_node)) {   // -90 == 270 for C14 and C16
  return std::make_pair(true, "");
}
// ... later, the destination pose IS wrapped:
//   ConstructGaragePose(charge_node_id, static_cast<int16_t>(volley::Wrap(volley::GetInboundHeading(node))))
```

Reading the code, an AGV already charging on `C14` or `C16` is therefore not treated as charging, and the charger search plans a move to another free charger. This is a one-line fix inside the scheduler (wrap the value, or call `GetBayInboundHeading`'s charger equivalent); it has not been reproduced in a test.

### `max_resource_size`

Required string: the name of the largest payload window allowed at the node (one of the `parking_windows` names, or the automatic `TRAY`). The parser turns it into `max_resource_size_index`, the window's position in the area-sorted list ([section 5](#ly-parking-windows-and-the-buffer)), and an unknown name throws. Sizes 0 up to that index are allowed at the node: the static filters disable the node for larger payloads, SIPP refuses traversals with a larger footprint, and the retrieve job checks that the chosen bay fits the car. In Pecos every node is `XL` except the three chargers, which are `TRAY`: an AGV may stand there, a tray with a car may not.

### Bay-only fields: `prioritization_value`, `insert_floor`, `system_floors`

For `Bay` and `BLift` nodes the parser reads three more optional keys:

- **`prioritization_value`** (int, default 0). The parser sorts bays by it, highest first, into `bay_prioritization_`: the first bay is the one most preferred to be ready for insert, the last the one most preferred to be ready for retrieve. Ties are broken by the *higher bay id first* (a `std::priority_queue<std::pair<int, uint16_t>>`), which is deterministic but nowhere documented. Pecos sets no value, so the order is `[21, 7]`: B21 is preferred insert-ready, B7 is tried first for a retrieve and drives the retrieval-heading cache. The value is not copied into `GarageNode.bay_prioritization`, which stays 0. Consumers: `ComputeBayRebalancingActions`, `PlanRetrieveJob` and `InitRetrievalHeadings` ([section 20](#bg-bays-vecs-and-vrcs)).
- **`insert_floor`** (default: the node's floor). Stored, but no code in the snapshots reads it.
- **`system_floors`** (list, default: the node's floor). The scheduler's bay-opening code uses `system_floors[0]` as the retrieve floor (“Pick the first floor for now”).

## Edges

Each entry `{src, dst}` connects two nodes. The parser stores the pair as `(min, max)` in an undirected Boost graph, so the names `src` and `dst` carry no meaning; travel is allowed both ways. An optional `disallowed_edge_orientation` (degrees) removes that heading and its reciprocal from the edge.

The edge list says *which* nodes connect; the node coordinates and headings say *how*. For each pose, `PoseGraph` computes the bearing of every edge relative to the pose's heading and files the destination into one of four slots, within 0.1 rad (about 5.7°). An edge that fits no slot, for a heading both nodes share, throws when the graph is built.

![Map of node 8 and its neighbours 31, 9, 4 and 13 at real coordinates, with four narrow tolerance wedges around node 8. A table of bearings and slots, the classification code with highlighted lines, the eight slots of pose (8, 90), and hypothetical edits shown in red.](figures/110_edge_classification.svg)

**From layout edges to neighbour slots.** PoseGraph names each edge per pose: it takes the atan2 bearing of the edge, subtracts the pose's yaw and snaps the result to FORWARD (0°), LEFT (+90°), BACK (180°) or RIGHT (−90°) within 0.1 rad. For pose (W8, 90°) this gives W13 FORWARD, W31 LEFT, W4 BACK and W9 RIGHT. The pose faces −x (west), so for the AGV itself LEFT is forward and RIGHT back (locomotes), FORWARD is its right and BACK its left (strafes). Step through the four neighbours, then three hypothetical edits: a diagonal edge that makes the constructor throw, a disallowed_edge_orientation that removes a heading and its reciprocal from one edge, and a 0.1 m misalignment that PoseGraph accepts at 0.1 rad but GetMotionType rejects at 1e-3 rad.

What follows for whoever edits a layout:

- **Edges must be axis-aligned with the headings they serve.** Pecos's are exactly horizontal or vertical. A diagonal edge between nodes that share a heading stops the scheduler at start-up; a diagonal edge between nodes with no shared heading is silently useless.
- **The two tolerances disagree.** `PoseGraph` accepts 0.1 rad, but `GetMotionType`, which classifies a motion as locomote or strafe when commands are built, demands 1e-3 rad and throws otherwise. A short edge (the 0.6096 m charger spurs) with a few millimetres of coordinate error passes the first check and fails the second.
- **The slot names are misleading.** `FORWARD` and `BACK` are out of the AGV's right and left sides (body ∓y), which is a strafe; `LEFT` and `RIGHT` are along body ±x, the driving axis. The names belong to the planner's helper frame, whose x axis points out of the AGV's right side ([section 3.4](#ly-the-planners-helper-frame)); [section 6.3](#ly-graph-slot-frame) maps each slot to the AGV's own direction.
- **The sandboxes hang on one edge.** Pecos's two YAML sections are joined only by edge 8–13 (4.391 m); a `disallowed_edge_orientation` of 90 on it would split the garage for every AGV.

## From the layout to the graph: vertices and edges

The layout lists nodes and undirected edges; the planner searches a directed graph whose vertices are *poses*, a node together with a heading. Two classes build that graph when the scheduler starts. `PoseGraph` (`common_ros/src/pose_graph.cpp`) decides which poses exist and which pose can be reached from which; `GarageGraph` (`garage_graph.cpp`) turns that into a Boost graph with one vertex per pose and one typed, directed edge per connection. This section follows both constructors on W8 and its four neighbours, the part of Pecos where an AGV can turn, and answers two questions the earlier figures leave open: how a vertex connects to the vertices of the next node, and where turning fits in.

![Animated schematic of W8 with W31 to the west, W9 east, W13 north and W4 south. Each node holds small circles, one per allowed heading, labelled with the heading and the vertex number. Translation edges join circles of the same heading on neighbouring nodes in two layers (90° and −90°); W8's 0° and 180° circles have no translation edges; a ring of rotation edges at W8 joins all four of its circles. Edges are then coloured LOCOMOTE (east–west), STRAFE (north–south) and ROTATION, and a highlighted route goes from (W31, 90°) to W8, turns twice and returns to (W31, −90°). Beside it, the abridged PoseGraph and GarageGraph constructors and a table of the six out-edges of (W8, 90°).](figures/148_pose_graph_construction.svg)

**How vertices and edges are built from the layout.** Step through W8 (headings \[0°, 90°\], rotation allowed) and its neighbours W31, W9, W4 and W13 (heading \[90°\], no rotation), drawn as a schematic. Every allowed heading of a node is one vertex. A translation edge joins two vertices of the *same* heading on neighbouring nodes, so the 90° and −90° vertices form two separate layers, and W8's 0° and 180° vertices get no translation edge at all. Rotation edges stay on W8 and join each heading to the nearest one clockwise and counter-clockwise; they are the only link between the layers. GarageGraph types each edge from the geometry, and the last step shows the route that turns an AGV at W31 round: drive to W8, rotate twice, drive back.

### Vertices: one per node and heading

A vertex is a pose, the pair (node, heading), not a node. `PoseGraph` walks the nodes in id order and, for each, the headings returned by `GetAllowedHeadings`: every heading listed in the YAML plus its reciprocal, wrapped to \[-179^\circ, 180^\circ\] and sorted. Each one becomes a pose, appended to `poses_` and recorded in `pose_indices_`. A node therefore has as many vertices as it has distinct allowed headings: two for a node that lists one heading, four for W8 and W22, which list 0° and 90°. `GarageGraph` then adds one Boost vertex per pose, in the same order, to an `adjacency_list` with `vecS` storage, so the vertex number equals the pose index: (W8, 90°) is pose 16 and vertex `v16`, and (W22, 90°) is `v44`, the vertex in [Figure](#bg-fig-76_garage_graph_vertex).

All poses of a node share its position. They differ only in the AGV's orientation, which decides the directions it can drive and the area it covers. That is why the planner cannot work on nodes alone: at W8 facing west and at W8 facing north are different states with different next moves.

### Translation edges: same heading, and both nodes must allow it

For each pose (node n, heading h) and each layout neighbour m of n, the constructor builds the pose (m, h) with the **same heading** and looks it up. If m does not allow h, that pose does not exist and no edge is made; this is the rule through which headings decide connectivity. Two more checks can drop or redirect the edge: a `disallowed_edge_orientation` on the layout edge that equals h or its reciprocal removes it, and a pair of VRC nodes is filed under `VRC_UP` or `VRC_DOWN` by floor ([section](#ly-floors-and-vrcs)). Otherwise the destination goes into one of the four translation slots, chosen by the bearing of the edge ([section](#ly-edges)).

Three consequences, all visible in [Figure](#ly-fig-148_pose_graph_construction):

- **A translation never turns the AGV.** Every translation edge joins two vertices with the same heading, so the vertices of one heading form a layer of their own; around W8 there is a 90° layer and a −90° layer.
- **Each layout edge becomes up to four graph edges.** The neighbour loop runs from both ends, once for each heading both nodes allow: W8–W31 gives (W8, 90°) → (W31, 90°), (W31, 90°) → (W8, 90°) and the same pair at −90°. The four layout edges around W8 give 16 translation edges.
- **A pose whose heading no neighbour shares has no translation edge.** (W8, 0°) and (W8, 180°) look for (W31, 0°), (W9, 0°) and so on, and find none. They can only be reached by turning.

### Slot names and the AGV's own directions

The four translation slots are called `FORWARD`, `LEFT`, `BACK` and `RIGHT`, but they are not the AGV's forward, left, back and right. `pose_graph.cpp` computes the bearing of the edge with `atan2`, which measures from east, and subtracts the heading as if the heading were also measured from east. The heading is measured from north ([section](#ly-the-heading)), so the result is a quarter turn off, and the names belong to the planner's helper frame, whose x axis points out of the AGV's right side ([section](#ly-the-planners-helper-frame)). `GarageGraph::LocomoteOrStrafe` compares the same two angles and adds \pi/2 first, with a comment that explains the mismatch; the slot names were never changed. In the AGV's own frame, forward from (W8, 90°) is (W31, 90°), which the code stores as `LEFT`.

| Slot in the code | Relative bearing in the code | Direction for the AGV | Neighbour of (W8, 90°) | Edge type  |
|------------------|------------------------------|-----------------------|------------------------|------------|
| `LEFT`           | +90^\circ                    | forward               | (W31, 90°), west       | `LOCOMOTE` |
| `RIGHT`          | -90^\circ                    | back                  | (W9, 90°), east        | `LOCOMOTE` |
| `FORWARD`        | 0^\circ                      | right                 | (W13, 90°), north      | `STRAFE`   |
| `BACK`           | 180^\circ                    | left                  | (W4, 90°), south       | `STRAFE`   |

The mapping is the same at every heading, because it comes from a fixed quarter-turn offset: at (W8, −90°), where the AGV faces east, `LEFT` is W9 (its forward) and `RIGHT` is W31. The names do not affect planning, since edge types come from geometry; the one place that reads a slot by name is `GetBayOutboundPose`, which takes the `LEFT` neighbour of a bay pose, that is, the AGV's forward move out of the bay. `PoseGraph` belongs to `common_ros`, so renaming the slots is outside this refactor; it is listed with the format changes in [section](#ly-improvements-in-the-format).

### Rotation edges: on one node, to the nearest heading each way

If the node has `rotation_allowed`, each of its poses gets two more neighbours on the *same node*: `ROT_RIGHT`, the allowed heading reached by the smallest clockwise turn, and `ROT_LEFT`, the one reached by the smallest counter-clockwise turn. With W8's headings −90°, 0°, 90° and 180°, (W8, 90°) has `ROT_RIGHT` = (W8, 0°) and `ROT_LEFT` = (W8, 180°), and the four poses form a ring of 8 directed rotation edges. These are the only edges that change the heading, and so the only link between the 90° and −90° layers. A node without `rotation_allowed` has no rotation edges, and an AGV there keeps the heading it arrived with. If a rotating node lists a single heading, the nearest heading in both directions is the reciprocal, and both rotation slots hold the same 180° turn.

### Edge types and lengths

`GarageGraph` adds one directed edge for every filled slot (`AddEdge`) and gives it a `Transition` with a type and a length:

- **`ROTATION`** for the two rotation slots; the length is the angle turned, in radians (\pi/2 for each step at W8).
- **`VRC_TRANSITION`** for the two VRC slots; the length is the difference in floor height.
- **`LOCOMOTE` or `STRAFE`** for a translation, decided by `LocomoteOrStrafe` from the geometry: motion mostly along the AGV's facing axis is a locomote, mostly across it a strafe. The length is the distance between the nodes. Around W8 at ±90°, east–west edges are locomotes and north–south edges strafes; the slot name plays no part.

The cost functions turn these lengths into durations, and the searches in [section](#mp-single-agent-searches) run on this graph.

### Reading a route on the graph

Translations keep the heading and rotations stay on one node, so every change of orientation happens at a node that allows rotation. To turn an AGV at W31 from 90° to −90°, the shortest route is (W31, 90°) → (W8, 90°), a locomote driven backwards; (W8, 90°) → (W8, 0°) → (W8, −90°), two 90° turns; and (W8, −90°) → (W31, −90°), a locomote driven forwards. Turning through 180° instead costs the same. This is also why W8 lists 0°: without it, W8 would have only the poses ±90°, and both rotation slots would hold a single 180° spin. For whoever edits a layout, three rules follow:

- a node connects to a neighbour only in the headings both of them allow;
- an AGV cannot change heading at a node without `rotation_allowed`;
- every area where AGVs must turn round needs a reachable rotation node; in Pecos these are W8 and W22.

## Parking windows and the buffer

`parking_windows` defines the payload size classes, each with `name`, `length_m` (along the AGV's long, driving axis: body x), `width_m` and an optional `height_m` (0 means unconstrained; larger than the bay clearance `kBayHeight` throws). The parser adds a `TRAY` window of the nominal tray size, sorts all windows by area (TRAY must come out smallest), and requires each to fit inside the next; two windows of equal size throw. A window's position in this list is its *resource size index*, and the collision entity id of a payload footprint is `PAYLOAD (4) + index`.

![Nested rectangles of the five resource windows to scale, a table of their indices and entity ids, two flow lanes showing the buffer unused and the unbuffered windows feeding the collision table, a scaled view of four Pecos stalls with XL and buffered outlines and their clearances, and a Pecos map marking the three TRAY-only chargers.](figures/109_resource_windows.svg)

**Resource windows.** The parser adds a TRAY window (`kTrayLength` × `kTrayWidth`; its size is not in the snapshots, so it is drawn nominal) to the four Pecos windows. It sorts all five by area into indices 0 to 4 (TRAY, COMPACT, STANDARD, LARGE, XL), throws unless each fits inside the next, and gives each a collision entity id PAYLOAD (4) + index. A node's `max_resource_size` admits sizes 0 up to its own index: XL everywhere except chargers 10, 14 and 16, which are TRAY. The buffer (+0.1524 m length, +0.0762 m width) is applied only inside `CalcOverlappingSizedPoses`, whose result nothing in the snapshots reads; the collision table uses the unbuffered windows. That matters in Pecos: unbuffered, neighbouring stalls clear by 0.2 mm in x and 76 mm in y; buffered, they would overlap by 152.2 mm in x and 0.2 mm in y.

- **Indices are positional.** Adding a window between two existing ones renumbers every larger one, and with it the collision entity ids. Anything that stores an index (logs, caches, tests) breaks silently; names are the stable identifiers.
- **The buffer does not protect anything today.** The collision table is built from the unbuffered windows (`CollisionTable::BuildEntityTable` uses `GetResourceWindow`), and the only reader of the buffered footprints, `PoseGraph::GetOverlappingSizedPoses`, has no caller in the snapshots (it may be used outside them). Pecos's stall pitch equals the XL length to 0.2 mm, so with the buffer applied neighbouring XL stalls would overlap.
- **Only heights are optional.** Pecos sets none, so every window is height-unconstrained.

## Floors and VRCs

Three keys describe multi-floor sites. None is used in Pecos.

- **`floors`**: a list of `{id, z}`. Without it there is one floor, id 0 at z 0. The z values give a VRC ride its length (`|Δz|`), which the cost model turns into a ride time.
- **`floor`** on each node (default 0), and **`Lift`** / **`BLift`** node types for the VRC stops.
- **`vrcs`**: a list of `{id, root_node, nodes}`. The parser sorts each VRC's nodes by floor and adds a layout edge between adjacent floors. `PoseGraph` files those edges as `VRC_UP` / `VRC_DOWN` (by floor, not by bearing: the stops share x and y), the GarageGraph types them `VRC_TRANSITION` with length `|Δz|`, and the collision table makes the stops of one VRC collide across floors (the “shaft rule”). `root_node` is stored but not validated, and read only by `GetRootNodeForVrcNode`, which nothing in the snapshots calls.

![Animated two-floor layout with a VRC shaft: AGV-1 carries tray T7 from floor 0 to floor 1 across the VRC edge, then the AGV trajectory, the collapsed motions and the action DAG with the inserted VRC approach and move commands, and a list of gaps.](figures/114_vrc_ride.svg)

**An AGV changes floors today.** Step through it on a two-floor layout made up for this figure (Pecos has no VRC). The `floors`, Lift nodes and `vrcs` entry turn into one `VRC_TRANSITION` edge of length \|dz\|. Task planning sees only a TrayMove. SIPP drives AGV-1 across the VRC edge for 13.87 s of trapezoid travel, with no door time and no carriage. Only the collision table's shaft rule keeps AGV-2 out. The action graph then collapses the ride into one motion, and `InsertVrcActionsIntoDag` adds an approach command and replaces the ride with a VRC move command (door close + transit + door open = 19.87 s), chained per VRC. The last step lists the gaps. Timings use the cost_functions defaults.

## VRC support across the pipeline

VRC support is a working skeleton rather than a finished feature. The layout and graph layers model a VRC ride as an ordinary edge an AGV can take; motion planning plans the AGV across it like any other edge; and the VRC commands themselves are added only at the very end, when the action graph is built. Task planning has no VRC logic, and the carriage is never planned as an agent with its own position or timing. Nothing in the snapshots tests the scheduler's VRC path end to end, and Pecos has no VRC, so none of this code runs there.

![Matrix of VRC support by layer: layout and graphs partial, task planning no, motion planning partial, action graph partial, dispatch and safety partial; columns for what exists, what runs on a plan call, and gaps.](figures/112_vrc_support_status.svg)

**VRC support across the pipeline.** For each layer, what VRC code exists, what of it runs on a normal plan call, and what is missing or risky. The layout and graph layers (common_ros) parse floors, Lift/BLift nodes and `vrcs`, create `VRC_UP`/`VRC_DOWN` pose neighbours and `VRC_TRANSITION` edges, and let VRC nodes on different floors collide (the shaft rule). Task planning creates no `VrcTransition`. SIPP drives the AGV across the VRC edge, and `PlanNodeSequential` has no VRC branch. VRC commands appear only in the action graph (`CollectAndCollapseTrajectoryMotions`, `InsertVrcActionsIntoDag` in utils.cpp). The BLift conversion to `MOVE_LIFT_TO_FLOOR` happens in Dispatch, which is outside the snapshots. Pecos has no VRC, so none of this runs there.

| Layer                                              | Supported?                      | What runs on a plan call                                                                                                                                                                                                                                                                                          | What is missing                                                                                                                                                                                                                                               |
|----------------------------------------------------|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Layout and graphs (common_ros)                     | Largely yes                     | Parses `floors`, `vrcs`, Lift and BLift; `VRC_UP` / `VRC_DOWN` pose neighbours; `VRC_TRANSITION` edges of length `|Δz|`; the shaft rule in the collision table                                                                                                                                                    | No check that VRC stops are Lift or BLift nodes; an empty `nodes` list underflows; an unknown floor id yields z = 0 silently; BLift has no overdrive-plate (`BAY_ODP`) footprint; no VRC tests in the snapshots                                               |
| Task planning (scheduler stages 1–3, planner_core) | No (implicit only)              | Nothing VRC-specific. Search costs come from the GarageGraph, which contains the VRC edges, so a tray on another floor is reachable and costed like any move. Bays use `system_floors[0]` as the retrieve floor                                                                                                   | `VrcTransition` is defined in planner_core but never created; assignment is not floor-aware; no reservation of the carriage; the charge job's “trapped in a bay” check tests only `TYPE_BAY`, so a BLift is missed; `insert_floor` is unused                  |
| Motion planning (CHUGG, SIPP, cost model)          | Partial                         | SIPP drives the AGV across the `VRC_TRANSITION` edge; the cost is a trapezoid over `|Δz|` at `vrc_transit`; multi-floor rides count as one run; other AGVs are kept out by the shaft rule                                                                                                                         | `PlanEventSequential(VrcTransition)` is fully written but `PlanNodeSequential` never calls it; the ride time leaves out door times and the carriage's approach, so it is optimistic; the carriage is not an agent                                             |
| Action graph                                       | Partial (the main runtime path) | `CollectAndCollapseTrajectoryMotions` merges each run of floor-traversal motions into one; `InsertVrcActionsIntoDag` adds an approach command when the carriage is on the wrong floor, replaces the AGV's ride action with a VRC move command (door close + transit + door open), and chains the commands per VRC | A ride at the very end of a trajectory is dropped (no flush after the loop); the collapsed motion borrows the next motion's action id; per-VRC chaining skips an edge that would close a cycle; VRC commands in the base schedule are ignored; no direct test |
| Dispatch and safety (outside the scheduler)        | Partial, outside the snapshots  | `GarageSafetyChecker` blocks a VRC command while a BLift bay on that VRC is not idle; Dispatch converts a VRC command for a BLift into `BayCommand.COMMAND_TYPE_MOVE_LIFT_TO_FLOOR`                                                                                                                               | The scheduler never sends `MOVE_LIFT_TO_FLOOR` itself and nothing orders a VRC command after the bay state the safety checker requires                                                                                                                        |

**In short.** The task planner does not support VRCs: it neither creates VRC events nor reasons about floors, and works only because the graph it searches happens to contain the VRC edges. The motion planner supports them partially: it can route an AGV through a VRC, but plans the ride as plain travel, without the carriage, its doors or its other users. The VRC commands Dispatch needs are reconstructed afterwards by the action graph. A site with a VRC therefore depends on code paths that no snapshot test exercises; before such a site goes live, the minimum is an end-to-end test of a cross-floor retrieve, the trailing-ride fix in `CollectAndCollapseTrajectoryMotions`, and door times in the ride cost.

## What the parser checks, and what it accepts silently

The parser checks types and a few cross-references, but not references between nodes and edges.

![A four-node example layout shown three ways (YAML, the parser's view, and its internal maps), stepping through five silent faults and the existing checks, with the exact layout.cpp lines and a two-column summary of checked versus not-checked inputs.](figures/111_layout_validation.svg)

**What the layout parser checks.** `Layout::Layout` throws for an unknown node type, an unknown `max_resource_size`, windows that do not nest, `height_m` above `kBayHeight` and an unknown VRC node id; `PoseGraph` throws for a node without headings and an off-axis edge between nodes that share a heading. It does not check references within the file. Step through five faults on a four-node example that load without an error: an edge to an unknown id lands on index 0 (the lowest id), a duplicate id is last-wins and duplicates poses, a misspelt optional key is silently defaulted, a heading listed with its reciprocal duplicates poses, and an empty VRC node list underflows `size() - 1`.

| Input                                                                                              | Checked?        | What happens                                                                                                                                                                    |
|----------------------------------------------------------------------------------------------------|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Unknown node `type`, unknown `max_resource_size`                                                   | yes             | Throws at load                                                                                                                                                                  |
| Windows that do not nest, equal windows, a window smaller than TRAY, `height_m` above `kBayHeight` | yes             | Throws at load                                                                                                                                                                  |
| A node without headings; an off-axis edge between nodes that share a heading                       | yes (PoseGraph) | Throws when the scheduler is constructed                                                                                                                                        |
| A missing required scalar (`id`, `x`, `rotation_allowed`, ...)                                     | yes (yaml-cpp)  | Throws, but the message does not name the node                                                                                                                                  |
| An edge that names an unknown node id                                                              | no              | `node_id_to_index_[a]` is `std::map::operator[]`: it inserts the id with index 0, so the edge attaches to the lowest-id node and `HasNode` starts returning true for the bad id |
| Duplicate node ids, duplicate edges                                                                | no              | Last-wins index, duplicated poses; parallel edges and an “overwrote slot” warning                                                                                               |
| A heading listed with its reciprocal (`[0, 180]`)                                                  | no              | Duplicate poses and GarageGraph vertices                                                                                                                                        |
| Bay or charger with several headings, or a heading outside \[0, 179\]                              | no              | `headings[0]` silently defines the inbound heading; 270 wraps for poses but not in `GetInboundHeading`                                                                          |
| A misspelt optional key (`faces_reciprocol`, `prioritisation_value`, ...)                          | no              | Silently defaulted                                                                                                                                                              |
| A VRC with an empty `nodes` list; VRC stops that are not lift nodes; an unknown `root_node`        | no              | `vrc.nodes.size() - 1` underflows (undefined behaviour); the others fail later or never                                                                                         |
| Floor ids above 255                                                                                | no              | Read as `uint32`, stored in a `uint8` field: 256 becomes 0                                                                                                                      |
| A node on a floor that `floors` does not list                                                      | no              | `GetFloorZForFloorId` returns 0.0 rather than “unknown”, so ride lengths are silently wrong                                                                                     |

## Issues found while reading the parser and its users

Each item below is read from the code; none has been reproduced in a run.

### An AGV already charging on C14 or C16 is not recognised

`PlanAgvChargeJob` compares the AGV's stored heading (−90) with the unwrapped inbound heading (270) of chargers with `faces_reciprocal: true` ([section 3.5](#ly-faces-reciprocal-and-the-inbound-heading)). Fix: wrap the value, in the scheduler.

### An edge to an unknown node creates a phantom node

Edge parsing uses `node_id_to_index_[a]`. A typo in an edge id silently connects the other end to the lowest-id node and makes the typo look like a real node to `HasNode`. Fix: `.at()` and a clear error, in common_ros.

### An empty VRC node list is undefined behaviour

`for(std::size_t i = 0; i < vrc.nodes.size() - 1; i++)` underflows when `nodes` is empty. Fix: `i + 1 < vrc.nodes.size()` and a check that the list has at least two stops, in common_ros.

### `GetGarageLayout` publishes vertex indices as edge ends

`GetGarageLayout` fills `EdgeMsg.src` / `dst` with Boost vertex indices, which are positions in the id-sorted node vector, not node ids. `Edge.msg`'s comment (“node index”) matches, but the YAML and every other message use ids, and in Pecos they differ (edge 8–31 is published as `{7, 26}`). The message also omits floors and disallowed orientations. Whoever serves and reads this service is outside the snapshots; check the consumer before changing it.

### One behaviour depends on the layout's name

`Scheduler::UseEvChargeHeading` tests `strstr(name, "576_eccles")`. Site behaviour should be layout data (for example a per-node preferred heading), not a name match.

### Fields that are stored but have no effect

Some keys in the layout file are parsed and stored but have no effect in the snapshots, or have an effect that does not reach the published messages. They are listed here so that a reader editing a layout does not expect behaviour the code does not provide.

- `parking_window_buffer`: applied only to footprints that nothing in the snapshots reads ([section 5](#ly-parking-windows-and-the-buffer)).
- `insert_floor`, `vrcs[].root_node`: stored, never read in the snapshots.
- `faces_reciprocal` on parking and waypoint nodes: ignored, but Pecos writes `false` on every one.
- `prioritization_value`: used for ordering, but not copied into `GarageNode.bay_prioritization`, so anything reading the message sees 0.

## Improvements

The layout format and its parser live in `common_ros`, `interfaces` and the site configuration, which the refactor does not rename ([section 16.1](#nm-how-to-read-this-list)). The items below are therefore split by where they would land: the scheduler-side items fit the refactor; the rest are a separate proposal for the owners of those packages.

### Inside the scheduler (fits the refactor)

Each item below changes only scheduler code and leaves the layout file and its parser untouched, so it can be made within the refactor. The items follow from the issues in [section](#ly-issues-found) and the field descriptions in [section](#ly-nodes).

- Wrap every inbound heading the scheduler compares (the charger test above, and `ApplyTransitionToFreeingMoves` for VECS), or call one helper that returns a wrapped pose.
- Replace the `576_eccles` name test with a layout-driven rule once the field exists; until then, keep it in one named function with a comment.
- Give the bay order a name that says what it is (for example `BaysByInsertPreference()`) and document the tie rule where task planning reads it.
- Use window *names* in logs and messages, never indices.

### In the format and parser (common_ros, interfaces, site configuration)

The remaining proposals change the file format or its parser, which belong to `common_ros`, `interfaces` and the site configuration rather than to the scheduler. The table pairs each current convention with a proposed replacement and the reason for it; the schema and linter described after the table would catch most of the cases that [section](#ly-validation) shows the parser accepts silently.

| Today                                                                                        | Proposed                                                                                                                                                                         | Why                                                                                                        |
|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `headings: [90]` + `faces_reciprocal: true`                                                  | `inbound_heading: -90` on Bay, BLift, AgvCharge and EvCharge; `headings` unchanged elsewhere                                                                                     | States the result instead of the mechanism; one meaning; already wrapped                                   |
| `headings` (degrees, reciprocals implied)                                                    | `headings_deg`, documented “each heading also allows its reciprocal”; reject a heading listed with its reciprocal                                                                | Units in the key, as `length_m` already does; no duplicate poses                                           |
| `src` / `dst` on an undirected edge                                                          | `nodes: [8, 31]`                                                                                                                                                                 | The order has no meaning; the names suggest it does                                                        |
| `prioritization_value`                                                                       | `insert_preference` (higher = preferred ready for insert), ties documented                                                                                                       | Says which way the order points                                                                            |
| `parking_windows`, read into `resource_windows_`                                             | `size_classes` (or keep the key and rename the code)                                                                                                                             | One word for one concept across file, code and messages                                                    |
| Section comments (`# 5675_pecos_sandbox_eng`), datum in a comment                            | `zone:` per node; `datum:` at top level                                                                                                                                          | Comments carry meaning the parser drops, yet change the md5                                                |
| `rotation_allowed` required, `faces_reciprocal` optional                                     | All booleans optional with documented defaults                                                                                                                                   | Consistency                                                                                                |
| PoseGraph slots `FORWARD` / `LEFT` / ...                                                     | `STRAFE_POS` / `LOCOMOTE_POS` / ... (or document the body frame next to the enum)                                                                                                | The current names contradict the heading convention                                                        |
| `PoseNeighbor` slots `FORWARD`, `LEFT`, `BACK`, `RIGHT`, named in the planner's helper frame | Names in the AGV's own frame: today's `LEFT` becomes `FORWARD`, `RIGHT` becomes `BACK`, `FORWARD` becomes `RIGHT`, `BACK` becomes `LEFT`; `GetBayOutboundPose` updated with them | The names then describe the move the AGV makes; behaviour unchanged, because edge types come from geometry |

**A schema and a linter.** Most of the silent cases above are cheap to catch before a file ever reaches a robot:

- A JSON Schema for the file (types, ranges, enums for `type` and window names, no unknown keys), checked in CI for every site configuration.
- A `layout_lint` tool (common_ros) that loads the file and checks what a schema cannot: every edge end exists; no duplicate nodes, edges or floors; every node is on some edge; every shared-heading edge is within 1e-3 rad, not 0.1; bays and chargers have exactly one heading in range and an outbound pose; VRCs have at least two stops, all lift nodes, on distinct listed floors, with `root_node` among them; `insert_floor` and `system_floors` name listed floors.
- In the parser: `.at()` instead of `operator[]`, `add_vertex` for every node (a node whose index is above every edge end is otherwise outside the Boost graph), the VRC loop bound, and error messages that name the node.
