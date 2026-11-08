# Study pack index (file:line: heading). Read a section with Read offset=<line>.
01-background.md:1:# 01 — Background: the scheduler and its data
01-background.md:11:## How to use this study pack
01-background.md:28:### How to read the code snippets
01-background.md:49:## What the scheduler does: the big picture
01-background.md:55:### The pipeline in one picture
01-background.md:71:### A request is not a plan
01-background.md:75:### Four representations of one plan
01-background.md:88:### How to think about the scheduler
01-background.md:106:### Where the code is
01-background.md:122:### A map of the study pack by stage
01-background.md:134:## Where the scheduler runs: the node and its interfaces
01-background.md:171:## The physical garage and its coordinate system
01-background.md:181:### Geometric versus logical position
01-background.md:186:# msg/GeometricPose.msg          # msg/GaragePose.msg
01-background.md:192:### Node, heading, pose, vertex: the words for places
01-background.md:223:### Asset types, and the other kinds of “type”
01-background.md:243:### How values are written in this guide
01-background.md:254:### Layout, GarageGraph and CollisionTable: three views of the same garage
01-background.md:288:## Vocabulary
01-background.md:316:### Acronyms and abbreviations
01-background.md:373:## The garage model in code: `Layout`, `PoseGraph`, `GarageGraph` and `CollisionTable`
01-background.md:383:### `Layout`: places in sorted vectors and ordered maps
01-background.md:408:### `PoseGraph`: from nodes to poses
01-background.md:440:### `GarageGraph` and its `Vertex`
01-background.md:472:#### Reading the `boost::adjacency_list` type
01-background.md:587:#### When `GetVertexFromPose` returns nothing
01-background.md:604:### `CollisionTable`: precomputed conflict sets
01-background.md:637:### Which structure answers which question
01-background.md:651:## ROS messages and services
01-background.md:657:### The `Plan` call at a glance
01-background.md:682:### `PlanRequest`: one moment in a running schedule
01-background.md:706:### `base_state`: the garage snapshot
01-background.md:742:### `SchedulerJob`: what to do, and what happened
01-background.md:768:### `Schedule` and `ActionNode`: commands in, commands out
01-background.md:791:### `PlanResponse` and `ScheduledJobData`: what comes back
01-background.md:818:### Places, ids and garage events
01-background.md:832:## `DiscreteGarageState`: the bridge between the garage and the planner
01-background.md:848:## Package anatomy: files and classes
01-background.md:896:## Objects, ownership and lifetimes
01-background.md:904:### Constructing the Scheduler
01-background.md:929:### Creating the per-call context
01-background.md:971:## One `Plan()` call, step by step
01-background.md:1043:## The base schedule: reserved assets and keep-out filters
01-background.md:1053:### What the loop marks
01-background.md:1070:### What closing a node does to the graph
01-background.md:1096:### Why reserve the assets that still have to move
01-background.md:1107:### One flag, two meanings
01-background.md:1115:### Where the flags are read
01-background.md:1132:### `keep_out_filter_by_footprint`: the keep-out map
01-background.md:1179:## Event types and polymorphism
01-background.md:1207:### The base class
01-background.md:1244:### The subclasses, and what `ApplyTo` does
01-background.md:1279:### Inside `AgvMove::ApplyTo`
01-background.md:1320:### What `OnEvent` is
01-background.md:1341:### Why the code is structured this way
01-background.md:1359:### A mental model: events are checked deltas, a state is a replay
01-background.md:1377:## Directed acyclic graphs, then `ScheduleEventDag`
01-background.md:1381:### Graph theory in one paragraph
01-background.md:1389:### What a topological ordering is, in plain words
01-background.md:1405:### The class: `Dag<T>` and `ScheduleEventDag`
01-background.md:1449:### What is stored: vertices, edges and shared events
01-background.md:1467:### The operations
01-background.md:1545:### Copies share events: `pending_events` as a work queue
01-background.md:1555:### How the DAG grows during `Plan()`
01-background.md:1569:### `RemoveRedundantEdges()`: fewer edges, same order
01-background.md:1590:### Gotchas
01-background.md:1603:## `PlanContext`: the per-call workspace
01-background.md:1617:### The definition, annotated
01-background.md:1667:### The four groups
01-background.md:1679:### Job indices and bookkeeping maps
01-background.md:1683:### `scheduled_jobs` in detail
01-background.md:1715:### The helper methods
01-background.md:1766:### `last_event_by_entity` in detail
01-background.md:1782:### `first_event_by_tray` in detail
01-background.md:1834:### Life cycle across one `Plan()` call
01-background.md:1854:### Gotchas
01-background.md:1864:## Packages, build system and dependencies
01-background.md:1877:### Source index
01-background.md:1900:## Debugging and testing
01-background.md:1920:## C++ concepts and idioms in context
01-background.md:1943:## Reading the C++ code: a call trace and a route through the source
01-background.md:1947:### How to read the call-trace figures
01-background.md:1967:### Where to start: a reading route
01-background.md:1996:### Following the calls yourself
02-layout-file.md:1:# 02 — The layout file: the garage as YAML
02-layout-file.md:7:## What the layout file is, and who reads it
02-layout-file.md:29:## The file at a glance
02-layout-file.md:65:## The AGV and garage coordinate systems
02-layout-file.md:73:### The garage frame
02-layout-file.md:77:### The heading
02-layout-file.md:92:### The AGV body frame
02-layout-file.md:104:### The planner's helper frame
02-layout-file.md:126:### One inconsistency: the rotation sign
02-layout-file.md:130:### How this pack draws the frames
02-layout-file.md:134:## Nodes
02-layout-file.md:138:### Identity and position: `id`, `x`, `y`, `floor`
02-layout-file.md:146:### Node types
02-layout-file.md:160:### `headings`: from a node to its poses
02-layout-file.md:176:### `rotation_allowed`
02-layout-file.md:180:### `faces_reciprocal` and the inbound heading
02-layout-file.md:205:### `max_resource_size`
02-layout-file.md:209:### Bay-only fields: `prioritization_value`, `insert_floor`, `system_floors`
02-layout-file.md:217:## Edges
02-layout-file.md:234:## From the layout to the graph: vertices and edges
02-layout-file.md:242:### Vertices: one per node and heading
02-layout-file.md:248:### Translation edges: same heading, and both nodes must allow it
02-layout-file.md:258:### Slot names and the AGV's own directions
02-layout-file.md:271:### Rotation edges: on one node, to the nearest heading each way
02-layout-file.md:275:### Edge types and lengths
02-layout-file.md:285:### Reading a route on the graph
02-layout-file.md:293:## Parking windows and the buffer
02-layout-file.md:305:## Floors and VRCs
02-layout-file.md:317:## VRC support across the pipeline
02-layout-file.md:335:## What the parser checks, and what it accepts silently
02-layout-file.md:358:## Issues found while reading the parser and its users
02-layout-file.md:362:### An AGV already charging on C14 or C16 was not recognised (fixed)
02-layout-file.md:366:### An edge to an unknown node creates a phantom node
02-layout-file.md:370:### An empty VRC node list is undefined behaviour
02-layout-file.md:374:### `GetGarageLayout` publishes vertex indices as edge ends
02-layout-file.md:378:### One behaviour depended on the layout's name (removed)
02-layout-file.md:382:### Fields that are stored but have no effect
02-layout-file.md:391:## Improvements
02-layout-file.md:395:### Inside the scheduler (fits the refactor)
02-layout-file.md:404:### In the format and parser (common_ros, interfaces, site configuration)
03-task-planning.md:1:# 03 — Task planning: building the event DAG
03-task-planning.md:7:## The whole journey of one job
03-task-planning.md:17:## The single-agent searches in `motion_planner`
03-task-planning.md:33:## Job expansion: from jobs to events
03-task-planning.md:49:### How to read the job figures
03-task-planning.md:58:### What a job is
03-task-planning.md:64:### The loop in `Plan()`
03-task-planning.md:68:#### What the code does, in order
03-task-planning.md:93:#### How `job_index` works
03-task-planning.md:138:#### Why it is built this way
03-task-planning.md:157:### The shape of every job method
03-task-planning.md:212:#### What a job method reads, changes and returns
03-task-planning.md:241:#### Assessment of the design
03-task-planning.md:267:### Every job sees the garage through `working_state`
03-task-planning.md:281:### Where the edges come from
03-task-planning.md:302:#### The three edge helpers in the code
03-task-planning.md:320:### Job methods are built from a few shared pieces
03-task-planning.md:335:### `TYPE_REPARK_TRAY` and `TYPE_MOVE_TRAY` — `ExpandReparkTrayJob`
03-task-planning.md:371:### `TYPE_MOVE_AGV` — `ExpandAgvMoveJob`
03-task-planning.md:400:### `TYPE_TRANSITION_BAY_TO_INSERT` / `_TO_RETRIEVE` — `ExpandBayTransitionJob`
03-task-planning.md:430:### `TYPE_CHARGE_PAYLOAD` — `ExpandChargePayloadJob`
03-task-planning.md:458:### `TYPE_RETRIEVE` — `ExpandRetrieveJob`
03-task-planning.md:492:### `TYPE_INSERT` — `ExpandInsertJob`
03-task-planning.md:521:### `TYPE_READY_FOR_INSERT` — `ExpandReadyForInsertJob`
03-task-planning.md:551:### `TYPE_READY_FOR_RETRIEVE` — `ExpandReadyForRetrieveJob`
03-task-planning.md:579:### `TYPE_CHARGE_AGV` — `ExpandAgvChargeJob`
03-task-planning.md:607:### `TYPE_CLEAN_GARAGE` — `ExpandCleanGarageJob`
03-task-planning.md:633:### `TYPE_REBALANCE_GARAGE` — `ExpandRebalanceGarageJob`
03-task-planning.md:660:### Gotchas
03-task-planning.md:694:### Cheat sheet and self-check
03-task-planning.md:718:## Tray assignment: `AssignTrays`
03-task-planning.md:722:### The problem this stage solves
03-task-planning.md:771:### The blocking-tray loop
03-task-planning.md:930:### Filling a blank tray id: `AssignEmptyTrayToMove`
03-task-planning.md:966:### Filling a blank destination: `AssignDestinationAndUnblockingMoves`
03-task-planning.md:1003:#### Inside `ResolveBlockingTrays`
03-task-planning.md:1030:### Occupancy becomes dependencies: `occupancy_history`
03-task-planning.md:1045:## AGV assignment: `AssignAgvs`
03-task-planning.md:1108:### Repairing paths after assignment
03-task-planning.md:1120:## `RemoveRedundantEdges()` and `ValidateEventSequence`
03-task-planning.md:1135:## Bays, VECS and VRCs
03-task-planning.md:1139:### Bays and rebalancing
03-task-planning.md:1161:### VECS (EV charging)
03-task-planning.md:1165:### VRCs (lifts between floors)
04-motion-planning.md:1:# 04 — Motion planning: from the event DAG to timed motions
04-motion-planning.md:7:## Where motion planning sits: two DAGs around one planner
04-motion-planning.md:28:## How the motion planner is packaged and called
04-motion-planning.md:47:## CHUGG, the motion planner
04-motion-planning.md:89:### Inside SolveSequential: one event at a time
04-motion-planning.md:129:### SIPP, the single-AGV search
04-motion-planning.md:141:## Timing: parameters and the cost model
04-motion-planning.md:145:### What can be configured
04-motion-planning.md:185:### The cost model: how long a move takes
04-motion-planning.md:233:## `ContinuousState`: the timeline CHUGG reads and writes
04-motion-planning.md:284:### Why a `Trajectory` is a `std::set`, and the alternative
04-motion-planning.md:331:## The code: classes and the call sequence
04-motion-planning.md:335:### Where the classes live
04-motion-planning.md:350:### CHUGG and its collaborators
04-motion-planning.md:363:### The search classes: SIPP on a generic A\*
04-motion-planning.md:375:### One `PlanMotions` call, call by call
04-motion-planning.md:406:### What the structure means for a refactor
04-motion-planning.md:416:## The single-agent searches and static filters
04-motion-planning.md:444:### The class design: engine, environments and states
04-motion-planning.md:467:### Who calls which search
04-motion-planning.md:480:### `SingleSourceSearch`: the shared engine
04-motion-planning.md:498:### Static filters: `BuildStaticObstacleFilter` and `GraphFilterProperties`
04-motion-planning.md:528:### The tray searches: `BlockingTraySearchEnvironment` and its two subclasses
04-motion-planning.md:553:### `FindPosePath` and `ConvertPosePathToTrajectory`
04-motion-planning.md:561:### `FindAgvUnderTrayAssignment`: a tray for every AGV
04-motion-planning.md:573:## Solver inputs and outputs: CHUGG and the standard MAPF problem
04-motion-planning.md:577:### The standard MAPF problem, and CBS
04-motion-planning.md:605:### What CHUGG receives instead
04-motion-planning.md:622:### CHUGG's problem in the same notation
04-motion-planning.md:649:### Can CHUGG take a CBS-style input, and can CBS take CHUGG's?
04-motion-planning.md:657:### From CHUGG towards the standard solvers
04-motion-planning.md:671:### A solver-neutral description of the problem
05-action-graph.md:1:# 05 — Action graph: from timed motions to the schedule
05-action-graph.md:9:## Why a timed plan is not enough
05-action-graph.md:27:## Graphs and orders, from scratch
05-action-graph.md:31:### Directed graphs and paths
05-action-graph.md:39:### DAGs are partial orders
05-action-graph.md:50:### Topological orders
05-action-graph.md:58:### Topological orders and parallelism
05-action-graph.md:88:### Transitive reduction
05-action-graph.md:101:## From a timed plan to an ADG
05-action-graph.md:105:### Plans and actions
05-action-graph.md:126:### Type 1 edges: each robot's own order
05-action-graph.md:134:### Type 2 edges: handing a location over
05-action-graph.md:157:### From a space-time table to an ADG: the algorithm
05-action-graph.md:391:### Cycles mean "only with perfect timing"
05-action-graph.md:395:## Executing an ADG
05-action-graph.md:399:### Statuses and the dispatch rule
05-action-graph.md:419:### Why it is safe
05-action-graph.md:432:### Why it finishes
05-action-graph.md:440:### Timing: earliest start, critical path and slack
05-action-graph.md:465:### Where the parallelism comes from
05-action-graph.md:504:## Beyond the basic ADG
05-action-graph.md:514:## The action DAG in the scheduler
05-action-graph.md:518:### Two DAGs, two jobs
05-action-graph.md:531:### How the action DAG is built
05-action-graph.md:602:### The construction, step by step
05-action-graph.md:624:### VRC commands: lifts between floors
05-action-graph.md:634:### Our edges versus Type 1 and Type 2
05-action-graph.md:657:### What goes over the wire
05-action-graph.md:674:### Persistent planning: `base_schedule` and the split
05-action-graph.md:703:### What this means for the refactor
05-action-graph.md:713:## Check your understanding
05-action-graph.md:741:## References
05-action-graph.md:752:## Design notes
05-action-graph.md:756:### Events plus a DAG: two established models combined
05-action-graph.md:765:### Comparison with Open-RMF's `rmf_traffic`
05-action-graph.md:784:### A DAG and its topological order allow parallel commands
05-action-graph.md:801:### Where the complexity comes from
05-action-graph.md:816:## Known limitations and reading checkpoint
06-dispatch.md:1:# 06 — Dispatch: the scheduler's only client
06-dispatch.md:7:## The `central` package at a glance
06-dispatch.md:23:## Jobs in Dispatch
06-dispatch.md:33:## The plan loop and what goes into a `PlanRequest`
06-dispatch.md:64:## What Dispatch does with the response
06-dispatch.md:79:## Executing the schedule
06-dispatch.md:85:## What this means for the scheduler
06-dispatch.md:96:## To expand
07-issue-and-proposal.md:1:# 07 — Issue & proposal: the scheduler core refactor
07-issue-and-proposal.md:19:## Ticket and scope
07-issue-and-proposal.md:27:## The pipeline the refactor works on
07-issue-and-proposal.md:45:### Where the code will live
07-issue-and-proposal.md:64:### Necessary and avoidable complexity in task planning
07-issue-and-proposal.md:83:## Where the two algorithms sit today
07-issue-and-proposal.md:146:## What the two algorithms touch
07-issue-and-proposal.md:172:### Why the default solver needs graph and collision services
07-issue-and-proposal.md:199:## Current versus target responsibilities
07-issue-and-proposal.md:222:## Module layout: stage folders or stage packages
07-issue-and-proposal.md:230:### Stage names
07-issue-and-proposal.md:242:### Option 1: stage folders in `scheduler`
07-issue-and-proposal.md:250:### Option 2: one package per stage
07-issue-and-proposal.md:260:### Comparison
07-issue-and-proposal.md:277:### Recommendation: folders now, packages when proven
07-issue-and-proposal.md:293:## Target architecture
07-issue-and-proposal.md:301:### Classes and call sequence
07-issue-and-proposal.md:313:## Proposed layout and API for the assignment stages
07-issue-and-proposal.md:317:### Tray assignment
07-issue-and-proposal.md:321:#### The new pieces and how they fit together
07-issue-and-proposal.md:473:#### Source tree
07-issue-and-proposal.md:548:# PROPOSED — CMakeLists.txt (excerpt; the rest of the file is unchanged)
07-issue-and-proposal.md:549:# Shared core: no stage, no scheduler.hpp
07-issue-and-proposal.md:552:# Stage libraries: each links scheduler_core and lower packages, never ${PROJECT_NAME}
07-issue-and-proposal.md:570:# The orchestrator library links the stages
07-issue-and-proposal.md:600:#### Before and after: the tray call tree
07-issue-and-proposal.md:640:#### Errors: `stdx::Expected` instead of `BoolStringPair` (done in PR \#1018)
07-issue-and-proposal.md:669:#### Why return a result, and how it is applied
07-issue-and-proposal.md:728:#### Free-function signatures and the `Plan()` call site
07-issue-and-proposal.md:811:#### Names in the tray module, and why
07-issue-and-proposal.md:830:### AGV assignment
07-issue-and-proposal.md:834:#### The new pieces and how they fit together
07-issue-and-proposal.md:911:#### Source tree
07-issue-and-proposal.md:938:#### Before and after: the AGV call tree
07-issue-and-proposal.md:953:#### Errors
07-issue-and-proposal.md:968:#### Why edit in place first, and how a result can follow
07-issue-and-proposal.md:981:#### Free-function signatures and the `Plan()` call site
07-issue-and-proposal.md:1024:#### Names in the AGV module, and why
07-issue-and-proposal.md:1045:## Naming and the ROS boundary
07-issue-and-proposal.md:1056:### What is renamed, and what is translated
07-issue-and-proposal.md:1077:### The translation header
07-issue-and-proposal.md:1124:### Internal types instead of messages
07-issue-and-proposal.md:1173:### Renames in `scheduler`
07-issue-and-proposal.md:1202:### The base-schedule reservation and the keep-out map
07-issue-and-proposal.md:1233:### Renames in `planner_core`
07-issue-and-proposal.md:1271:### What waits for `common_ros` and the interfaces
07-issue-and-proposal.md:1279:## Key invariants to maintain
07-issue-and-proposal.md:1301:## Staged plan
07-issue-and-proposal.md:1325:## Decisions to resolve in review
07-issue-and-proposal.md:1346:## Risks that must not be silently "fixed"
07-issue-and-proposal.md:1363:## Next actions
07-issue-and-proposal.md:1371:## Evaluating the event-graph strategy
07-issue-and-proposal.md:1375:### The problem the scheduler solves
07-issue-and-proposal.md:1396:### What the event DAG is
07-issue-and-proposal.md:1412:### Four kinds of edge
07-issue-and-proposal.md:1429:### Strengths and costs of the current strategy
07-issue-and-proposal.md:1441:### Related formulations
07-issue-and-proposal.md:1456:### Alternative architectures
07-issue-and-proposal.md:1471:### Recommendation
07-issue-and-proposal.md:1483:## Future work: swappable motion planners
07-issue-and-proposal.md:1491:### Why this is harder than the task-planning interfaces
07-issue-and-proposal.md:1500:### The interface
07-issue-and-proposal.md:1559:### Where the pieces live
07-issue-and-proposal.md:1572:### Solvers that support less than the full problem
07-issue-and-proposal.md:1580:### A staged plan for motion planning
07-issue-and-proposal.md:1595:### Decisions for the motion-planning work
07-issue-and-proposal.md:1605:## Future work: performance instrumentation and evaluation
07-issue-and-proposal.md:1609:### Instrumentation in layers
07-issue-and-proposal.md:1619:### A structured evaluation
07-issue-and-proposal.md:1627:## Proposed future work: the naming catalogue and small struct refactors
07-issue-and-proposal.md:1635:### How to read the catalogue
07-issue-and-proposal.md:1650:### Naming rules
07-issue-and-proposal.md:1654:#### Spell words out
07-issue-and-proposal.md:1660:#### One concept, one word
07-issue-and-proposal.md:1689:#### Endpoint pairs: one pair per kind
07-issue-and-proposal.md:1698:#### Units in the name when they are not obvious
07-issue-and-proposal.md:1702:#### Ids, indices and their types
07-issue-and-proposal.md:1711:#### Maps are named `<value>_by_<key>`
07-issue-and-proposal.md:1715:#### Booleans
07-issue-and-proposal.md:1719:#### State versus status
07-issue-and-proposal.md:1723:#### The same object has the same name at every layer
07-issue-and-proposal.md:1727:#### "Plan" means the `Plan()` call, and nothing else
07-issue-and-proposal.md:1731:### The headline renames
07-issue-and-proposal.md:1751:### The `scheduler` package
07-issue-and-proposal.md:1755:#### Scheduler members
07-issue-and-proposal.md:1770:#### PlanContext (was ScheduleContext)
07-issue-and-proposal.md:1788:#### Pipeline stages: folders and namespaces
07-issue-and-proposal.md:1824:#### Names seen in `motion_planner`
07-issue-and-proposal.md:1834:### planner_core: events and the DAG
07-issue-and-proposal.md:1850:### common_ros: the garage model
07-issue-and-proposal.md:1854:#### GarageGraph and Transition
07-issue-and-proposal.md:1873:#### PoseGraph and Layout
07-issue-and-proposal.md:1892:#### CollisionTable and footprints
07-issue-and-proposal.md:1907:#### DiscreteGarageState and asset ids
07-issue-and-proposal.md:1917:### ROS interfaces
07-issue-and-proposal.md:1921:#### Ids and integer widths
07-issue-and-proposal.md:1932:#### Garage model messages
07-issue-and-proposal.md:1950:#### State and event messages
07-issue-and-proposal.md:1965:#### Jobs, plans and schedules
07-issue-and-proposal.md:1982:#### Command messages
07-issue-and-proposal.md:1992:### Small struct refactors
07-issue-and-proposal.md:1996:#### Transition: one unit per field
07-issue-and-proposal.md:2017:#### Pose-change messages nest the pose
07-issue-and-proposal.md:2022:# today: AgvPoseChanged.msg (TrayPoseSetManually.msg is the same with tray_id)
07-issue-and-proposal.md:2029:# proposed
07-issue-and-proposal.md:2037:#### CollisionTable::Edge becomes a named struct
07-issue-and-proposal.md:2055:#### PoseGraph neighbour slots
07-issue-and-proposal.md:2070:#### AssetId with an enumerated type
07-issue-and-proposal.md:2075:# today: GarageEntityId.msg
07-issue-and-proposal.md:2079:# proposed: AssetId.msg
07-issue-and-proposal.md:2092:#### Disallowed headings live on the edge
07-issue-and-proposal.md:2097:# today: GarageLayout.msg
07-issue-and-proposal.md:2101:# proposed
07-issue-and-proposal.md:2107:### Keep as they are
07-issue-and-proposal.md:2118:### Decisions for review
07-issue-and-proposal.md:2129:### Rollout
08-verification.md:1:# 08 — Verification: regression parity and benchmarks
08-verification.md:5:## Two separate goals
08-verification.md:9:## What the existing tests cover
08-verification.md:35:### How a stage-level test is built
08-verification.md:69:### Tests most relevant to the two solvers
08-verification.md:90:### Where the old tests went
08-verification.md:115:### Gaps
08-verification.md:127:## Proposed benchmark dataset (requirements, not completed scenarios)
08-verification.md:146:## Compare meaning, not pointers or GUIDs
08-verification.md:180:## Benchmark method
08-verification.md:196:## Build and run commands
08-verification.md:210:## System-level checks in simulation
08-verification.md:214:## Test layers, and how baselines are computed and stored
08-verification.md:227:### Computing a baseline
08-verification.md:237:### Where fixtures and results are stored
08-verification.md:288:### Updating a recording
08-verification.md:292:### Testing the algorithm without the simulator
08-verification.md:296:### Where the simulator fits
08-verification.md:302:## Acceptance checklist
08-verification.md:319:## Evidence limits
09-simulation.md:1:# 09 — Simulation: running the real stack against a simulated garage
09-simulation.md:5:## Simulation in brief
09-simulation.md:35:## From the layout to a running simulation
09-simulation.md:60:### Where the layouts are
09-simulation.md:81:### The Pecos test facility as three layouts
09-simulation.md:91:### Two kinds of site: a bay at grade, and a bay on a car lift
09-simulation.md:101:## What runs during a simulation
09-simulation.md:122:### What is real and what is simulated
09-simulation.md:132:### How the processes are arranged
09-simulation.md:141:### Simulated time
09-simulation.md:150:## One scenario run
09-simulation.md:158:### Seeding the garage, and the scenario clock
09-simulation.md:164:### Timed actions become service calls
09-simulation.md:187:### Patrons and the simulated bay
09-simulation.md:198:### Collision checking
09-simulation.md:210:### What the Simulator reports, and how to watch a run
09-simulation.md:218:## Scenario files and events files
09-simulation.md:225:### The scenario file
09-simulation.md:246:### Events files and the exerciser
09-simulation.md:274:### The per-site scenario family
09-simulation.md:300:### Batch configurations
09-simulation.md:306:### A scenario for the running example
09-simulation.md:311:# PROPOSED: 5675_pecos_sandbox_qa_retrieve_with_blocker.yaml (start file)
09-simulation.md:334:# PROPOSED: 5675_pecos_sandbox_qa_events_retrieve_then_park.yaml (events file)
09-simulation.md:348:## Running a simulation
09-simulation.md:356:### Launching
09-simulation.md:388:### Parameters, from defaults to the scenario
09-simulation.md:404:### Recording a run, and looking at it again
09-simulation.md:414:### A wrong layout or events file in step 4
09-simulation.md:439:## Recipes: parking, retrieving and steering a running simulation
09-simulation.md:447:### Insert a car automatically, from the scenario
09-simulation.md:452:# my_qa_one_insert.yaml: a copy of 5675_pecos_sandbox_qa_empty_start_in_auto.yaml, plus the last action
09-simulation.md:485:### Insert a car by hand, while the simulation runs
09-simulation.md:508:### Confirm the insert yourself
09-simulation.md:519:### Retrieve a car
09-simulation.md:527:### Other operator actions by hand
09-simulation.md:546:### Pause, speed up, slow down, watch
09-simulation.md:557:## Testing with scenarios
09-simulation.md:561:### What a run can tell you
09-simulation.md:575:### A scenario catalogue for the refactor
09-simulation.md:596:### Determinism, and what to compare
09-simulation.md:602:## Checking the refactor with the simulator
09-simulation.md:612:### Replay recorded plan calls
09-simulation.md:640:### Closed-loop runs
09-simulation.md:655:### When to run what
09-simulation.md:670:## Gaps and proposed improvements
09-simulation.md:690:## Open questions
09-simulation.md:705:## Evidence limits
INDEX.md:1:# Study pack index (file:line: heading). Read a section with Read offset=<line>.
