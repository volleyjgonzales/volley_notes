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
01-background.md:167:## The physical garage and its coordinate system
01-background.md:177:### Geometric versus logical position
01-background.md:182:# msg/GeometricPose.msg          # msg/GaragePose.msg
01-background.md:188:### Node, heading, pose, vertex: the words for places
01-background.md:219:### Asset types, and the other kinds of “type”
01-background.md:239:### How values are written in this guide
01-background.md:250:### Layout, GarageGraph and CollisionTable: three views of the same garage
01-background.md:283:## Vocabulary
01-background.md:311:### Acronyms and abbreviations
01-background.md:368:## The garage model in code: `Layout`, `PoseGraph`, `GarageGraph` and `CollisionTable`
01-background.md:378:### `Layout`: places in sorted vectors and ordered maps
01-background.md:403:### `PoseGraph`: from nodes to poses
01-background.md:435:### `GarageGraph` and its `Vertex`
01-background.md:467:#### Reading the `boost::adjacency_list` type
01-background.md:582:#### When `GetVertexFromPose` returns nothing
01-background.md:599:### `CollisionTable`: precomputed conflict sets
01-background.md:632:### Which structure answers which question
01-background.md:646:## ROS messages and services
01-background.md:652:### The `Plan` call at a glance
01-background.md:677:### `PlanRequest`: one moment in a running schedule
01-background.md:701:### `base_state`: the garage snapshot
01-background.md:737:### `SchedulerJob`: what to do, and what happened
01-background.md:763:### `Schedule` and `ActionNode`: commands in, commands out
01-background.md:786:### `PlanResponse` and `ScheduledJobData`: what comes back
01-background.md:813:### Places, ids and garage events
01-background.md:827:## `DiscreteGarageState`: the bridge between the garage and the planner
01-background.md:843:## Package anatomy: files and classes
01-background.md:880:## Objects, ownership and lifetimes
01-background.md:888:### Constructing the Scheduler
01-background.md:912:### Creating the per-call context
01-background.md:960:## One `Plan()` call, step by step
01-background.md:1022:## The base schedule: reserved assets and keep-out filters
01-background.md:1032:### What the loop marks
01-background.md:1049:### What closing a node does to the graph
01-background.md:1075:### Why reserve the assets that still have to move
01-background.md:1086:### One flag, two meanings
01-background.md:1094:### Where the flags are read
01-background.md:1111:### `disabledness_filters`: the keep-out map
01-background.md:1151:## Event types and polymorphism
01-background.md:1175:### The base class
01-background.md:1212:### The subclasses, and what `Apply` does
01-background.md:1247:### Inside `AgvMove::Apply`
01-background.md:1288:### What `OnEvent` is
01-background.md:1309:### Why the code is structured this way
01-background.md:1327:### A mental model: events are checked deltas, a state is a replay
01-background.md:1345:## Directed acyclic graphs, then `ScheduleEventDag`
01-background.md:1349:### Graph theory in one paragraph
01-background.md:1357:### What a topological ordering is, in plain words
01-background.md:1373:### The class: `DagBase<T>` and `ScheduleEventDag`
01-background.md:1418:### What is stored: vertices, edges and shared events
01-background.md:1436:### The operations
01-background.md:1506:### Copies share events: `event_dag_copy` as a work queue
01-background.md:1516:### How the DAG grows during `Plan()`
01-background.md:1530:### `Reduce()`: fewer edges, same order
01-background.md:1551:### Gotchas
01-background.md:1564:## `ScheduleContext`: the per-call workspace
01-background.md:1578:### The definition, annotated
01-background.md:1626:### The four groups
01-background.md:1638:### Job indices and bookkeeping maps
01-background.md:1642:### `scheduled_jobs` in detail
01-background.md:1674:### The three helper methods
01-background.md:1708:### `last_entity_event` in detail
01-background.md:1724:### `first_tray_event` in detail
01-background.md:1770:### Life cycle across one `Plan()` call
01-background.md:1790:### Gotchas
01-background.md:1800:## Packages, build system and dependencies
01-background.md:1812:### Source index
01-background.md:1830:## Debugging and testing
01-background.md:1847:## C++ concepts and idioms in context
01-background.md:1867:## Reading the C++ code: a call trace and a route through the source
01-background.md:1871:### How to read the call-trace figures
01-background.md:1891:### Where to start: a reading route
01-background.md:1926:### Following the calls yourself
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
02-layout-file.md:202:### `max_resource_size`
02-layout-file.md:206:### Bay-only fields: `prioritization_value`, `insert_floor`, `system_floors`
02-layout-file.md:214:## Edges
02-layout-file.md:231:## From the layout to the graph: vertices and edges
02-layout-file.md:239:### Vertices: one per node and heading
02-layout-file.md:245:### Translation edges: same heading, and both nodes must allow it
02-layout-file.md:255:### Slot names and the AGV's own directions
02-layout-file.md:268:### Rotation edges: on one node, to the nearest heading each way
02-layout-file.md:272:### Edge types and lengths
02-layout-file.md:282:### Reading a route on the graph
02-layout-file.md:290:## Parking windows and the buffer
02-layout-file.md:302:## Floors and VRCs
02-layout-file.md:314:## VRC support across the pipeline
02-layout-file.md:332:## What the parser checks, and what it accepts silently
02-layout-file.md:355:## Issues found while reading the parser and its users
02-layout-file.md:359:### An AGV already charging on C14 or C16 is not recognised
02-layout-file.md:363:### An edge to an unknown node creates a phantom node
02-layout-file.md:367:### An empty VRC node list is undefined behaviour
02-layout-file.md:371:### `GetGarageLayout` publishes vertex indices as edge ends
02-layout-file.md:375:### One behaviour depends on the layout's name
02-layout-file.md:379:### Fields that are stored but have no effect
02-layout-file.md:388:## Improvements
02-layout-file.md:392:### Inside the scheduler (fits the refactor)
02-layout-file.md:401:### In the format and parser (common_ros, interfaces, site configuration)
03-task-planning.md:1:# 03 — Task planning: building the event DAG
03-task-planning.md:7:## The whole journey of one job
03-task-planning.md:17:## The single-agent searches in `motion_planner`
03-task-planning.md:33:## Job expansion: from jobs to events
03-task-planning.md:49:### How to read the job figures
03-task-planning.md:58:### What a job is
03-task-planning.md:64:### The loop in `Plan()`
03-task-planning.md:68:#### What the code does, in order
03-task-planning.md:74:#### How `job_index` works
03-task-planning.md:117:#### Why it is built this way
03-task-planning.md:136:### The shape of every job method
03-task-planning.md:182:#### What a job method reads, changes and returns
03-task-planning.md:211:#### Assessment of the design
03-task-planning.md:237:### Every job sees the garage through `working_state`
03-task-planning.md:251:### Where the edges come from
03-task-planning.md:270:#### Rule A, rule B and rule C in the code
03-task-planning.md:288:### Job methods are built from a few shared pieces
03-task-planning.md:303:### `TYPE_REPARK_TRAY` and `TYPE_MOVE_TRAY` — `PlanReparkTrayJob`
03-task-planning.md:336:### `TYPE_MOVE_AGV` — `PlanAgvMoveJob`
03-task-planning.md:365:### `TYPE_TRANSITION_BAY_TO_INSERT` / `_TO_RETRIEVE` — `PlanBayTransitionJob`
03-task-planning.md:393:### `TYPE_CHARGE_PAYLOAD` — `PlanChargePayloadJob`
03-task-planning.md:419:### `TYPE_RETRIEVE` — `PlanRetrieveJob`
03-task-planning.md:452:### `TYPE_INSERT` — `PlanInsertJob`
03-task-planning.md:479:### `TYPE_READY_FOR_INSERT` — `PlanReadyForInsertJob`
03-task-planning.md:507:### `TYPE_READY_FOR_RETRIEVE` — `PlanReadyForRetrieveJob`
03-task-planning.md:533:### `TYPE_CHARGE_AGV` — `PlanAgvChargeJob`
03-task-planning.md:559:### `TYPE_CLEAN_GARAGE` — `PlanCleanGarageJob`
03-task-planning.md:584:### `TYPE_REBALANCE_GARAGE` — `PlanRebalanceGarageJob`
03-task-planning.md:609:### Gotchas
03-task-planning.md:643:### Cheat sheet and self-check
03-task-planning.md:667:## Tray assignment: `DoTrayAssignments`
03-task-planning.md:671:### The problem this stage solves
03-task-planning.md:720:### The blocking-tray loop
03-task-planning.md:864:### Filling a blank tray id: `AssignTrayIdForEmptyMove`
03-task-planning.md:900:### Filling a blank destination: `AssignDestForUntargetedMove`
03-task-planning.md:939:#### Inside `ResolveBlockingTrays`
03-task-planning.md:966:### Occupancy becomes dependencies: `freeing_moves`
03-task-planning.md:981:## AGV assignment: `DoAgvAssignments`
03-task-planning.md:1034:### Repairing paths after assignment
03-task-planning.md:1046:## `Reduce()` and `SanityCheckEvents`
03-task-planning.md:1061:## Bays, VECS and VRCs
03-task-planning.md:1065:### Bays and rebalancing
03-task-planning.md:1075:### VECS (EV charging)
03-task-planning.md:1079:### VRCs (lifts between floors)
04-motion-planning.md:1:# 04 — Motion planning: from the event DAG to timed motions
04-motion-planning.md:7:## Where motion planning sits: two DAGs around one planner
04-motion-planning.md:28:## How the motion planner is packaged and called
04-motion-planning.md:47:## CHUGG, the motion planner
04-motion-planning.md:87:### Inside SolveSequential: one event at a time
04-motion-planning.md:127:### SIPP, the single-AGV search
04-motion-planning.md:139:## Timing: parameters and the cost model
04-motion-planning.md:143:### What can be configured
04-motion-planning.md:183:### The cost model: how long a move takes
04-motion-planning.md:231:## `ContinuousState`: the timeline CHUGG reads and writes
04-motion-planning.md:281:### Why a `Trajectory` is a `std::set`, and the alternative
04-motion-planning.md:328:## The code: classes and the call sequence
04-motion-planning.md:332:### Where the classes live
04-motion-planning.md:347:### CHUGG and its collaborators
04-motion-planning.md:360:### The search classes: SIPP on a generic A\*
04-motion-planning.md:372:### One `PlanMotions` call, call by call
04-motion-planning.md:403:### What the structure means for a refactor
04-motion-planning.md:413:## The single-agent searches and static filters
04-motion-planning.md:441:### The class design: engine, environments and states
04-motion-planning.md:464:### Who calls which search
04-motion-planning.md:477:### `SingleSourceSearch`: the shared engine
04-motion-planning.md:495:### Static filters: `GetStaticFilter` and `GraphFilterProperties`
04-motion-planning.md:525:### The tray searches: `BlockingTraySearchEnvironment` and its two subclasses
04-motion-planning.md:550:### `GetPosePath` and `ConvertPosePathToTrajectory`
04-motion-planning.md:558:### `HideAgvs`: a tray for every AGV
04-motion-planning.md:570:## Solver inputs and outputs: CHUGG and the standard MAPF problem
04-motion-planning.md:574:### The standard MAPF problem, and CBS
04-motion-planning.md:602:### What CHUGG receives instead
04-motion-planning.md:619:### CHUGG's problem in the same notation
04-motion-planning.md:646:### Can CHUGG take a CBS-style input, and can CBS take CHUGG's?
04-motion-planning.md:654:### From CHUGG towards the standard solvers
04-motion-planning.md:668:### A solver-neutral description of the problem
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
05-action-graph.md:583:### The construction, step by step
05-action-graph.md:605:### VRC commands: lifts between floors
05-action-graph.md:615:### Our edges versus Type 1 and Type 2
05-action-graph.md:638:### What goes over the wire
05-action-graph.md:655:### Persistent planning: `base_schedule` and the split
05-action-graph.md:679:### What this means for the refactor
05-action-graph.md:689:## Check your understanding
05-action-graph.md:717:## References
05-action-graph.md:728:## Design notes
05-action-graph.md:732:### Events plus a DAG: two established models combined
05-action-graph.md:741:### Comparison with Open-RMF's `rmf_traffic`
05-action-graph.md:760:### A DAG and its topological order allow parallel commands
05-action-graph.md:777:### Where the complexity comes from
05-action-graph.md:792:## Known limitations and reading checkpoint
06-dispatch.md:1:# 06 — Dispatch: the scheduler's only client
06-dispatch.md:7:## The `central` package at a glance
06-dispatch.md:23:## Jobs in Dispatch
06-dispatch.md:33:## The plan loop and what goes into a `PlanRequest`
06-dispatch.md:64:## What Dispatch does with the response
06-dispatch.md:79:## Executing the schedule
06-dispatch.md:85:## What this means for the scheduler
06-dispatch.md:96:## To expand
07-issue-and-proposal.md:1:# 07 — Issue & proposal: the scheduler core refactor
07-issue-and-proposal.md:18:## Ticket and scope
07-issue-and-proposal.md:26:## The pipeline the refactor works on
07-issue-and-proposal.md:44:### Where the code will live
07-issue-and-proposal.md:63:### Necessary and avoidable complexity in task planning
07-issue-and-proposal.md:82:## Where the two algorithms sit today
07-issue-and-proposal.md:131:## What the two algorithms touch
07-issue-and-proposal.md:156:### Why the default solver needs graph and collision services
07-issue-and-proposal.md:176:## Current versus target responsibilities
07-issue-and-proposal.md:199:## Module layout: stage folders or stage packages
07-issue-and-proposal.md:207:### Stage names
07-issue-and-proposal.md:219:### Option 1: stage folders in `scheduler`
07-issue-and-proposal.md:227:### Option 2: one package per stage
07-issue-and-proposal.md:237:### Comparison
07-issue-and-proposal.md:254:### Recommendation: folders now, packages when proven
07-issue-and-proposal.md:270:## Target architecture
07-issue-and-proposal.md:278:### Classes and call sequence
07-issue-and-proposal.md:290:## Proposed layout and API for the assignment stages
07-issue-and-proposal.md:294:### Tray assignment
07-issue-and-proposal.md:298:#### The new pieces and how they fit together
07-issue-and-proposal.md:450:#### Source tree
07-issue-and-proposal.md:520:# PROPOSED — CMakeLists.txt (excerpt; the rest of the file is unchanged)
07-issue-and-proposal.md:521:# Shared core: no stage, no scheduler.hpp
07-issue-and-proposal.md:524:# Stage libraries: each links scheduler_core and lower packages, never ${PROJECT_NAME}
07-issue-and-proposal.md:542:# The orchestrator library links the stages
07-issue-and-proposal.md:571:#### Before and after: the tray call tree
07-issue-and-proposal.md:612:#### Errors: `stdx::Expected` instead of `BoolStringPair`
07-issue-and-proposal.md:638:#### Why return a result, and how it is applied
07-issue-and-proposal.md:697:#### Free-function signatures and the `Plan()` call site
07-issue-and-proposal.md:767:#### Names in the tray module, and why
07-issue-and-proposal.md:786:### AGV assignment
07-issue-and-proposal.md:790:#### The new pieces and how they fit together
07-issue-and-proposal.md:865:#### Source tree
07-issue-and-proposal.md:891:#### Before and after: the AGV call tree
07-issue-and-proposal.md:906:#### Errors
07-issue-and-proposal.md:920:#### Why edit in place first, and how a result can follow
07-issue-and-proposal.md:933:#### Free-function signatures and the `Plan()` call site
07-issue-and-proposal.md:979:#### Names in the AGV module, and why
07-issue-and-proposal.md:1000:## Naming and the ROS boundary
07-issue-and-proposal.md:1011:### What is renamed, and what is translated
07-issue-and-proposal.md:1032:### The translation header
07-issue-and-proposal.md:1079:### Internal types instead of messages
07-issue-and-proposal.md:1128:### Renames in `scheduler`
07-issue-and-proposal.md:1149:### The base-schedule reservation and the keep-out map
07-issue-and-proposal.md:1180:### Renames in `planner_core`
07-issue-and-proposal.md:1218:### What waits for `common_ros` and the interfaces
07-issue-and-proposal.md:1226:## Key invariants to maintain
07-issue-and-proposal.md:1248:## Staged plan
07-issue-and-proposal.md:1270:## Decisions to resolve in review
07-issue-and-proposal.md:1291:## Risks that must not be silently "fixed"
07-issue-and-proposal.md:1305:## Next actions
07-issue-and-proposal.md:1313:## Evaluating the event-graph strategy
07-issue-and-proposal.md:1317:### The problem the scheduler solves
07-issue-and-proposal.md:1338:### What the event DAG is
07-issue-and-proposal.md:1354:### Four kinds of edge
07-issue-and-proposal.md:1371:### Strengths and costs of the current strategy
07-issue-and-proposal.md:1383:### Related formulations
07-issue-and-proposal.md:1398:### Alternative architectures
07-issue-and-proposal.md:1413:### Recommendation
07-issue-and-proposal.md:1425:## Future work: swappable motion planners
07-issue-and-proposal.md:1433:### Why this is harder than the task-planning interfaces
07-issue-and-proposal.md:1442:### The interface
07-issue-and-proposal.md:1501:### Where the pieces live
07-issue-and-proposal.md:1514:### Solvers that support less than the full problem
07-issue-and-proposal.md:1522:### A staged plan for motion planning
07-issue-and-proposal.md:1537:### Decisions for the motion-planning work
07-issue-and-proposal.md:1547:## Future work: performance instrumentation and evaluation
07-issue-and-proposal.md:1551:### Instrumentation in layers
07-issue-and-proposal.md:1561:### A structured evaluation
07-issue-and-proposal.md:1569:## Proposed future work: the naming catalogue and small struct refactors
07-issue-and-proposal.md:1577:### How to read the catalogue
07-issue-and-proposal.md:1592:### Naming rules
07-issue-and-proposal.md:1596:#### Spell words out
07-issue-and-proposal.md:1602:#### One concept, one word
07-issue-and-proposal.md:1631:#### Endpoint pairs: one pair per kind
07-issue-and-proposal.md:1640:#### Units in the name when they are not obvious
07-issue-and-proposal.md:1644:#### Ids, indices and their types
07-issue-and-proposal.md:1653:#### Maps are named `<value>_by_<key>`
07-issue-and-proposal.md:1657:#### Booleans
07-issue-and-proposal.md:1661:#### State versus status
07-issue-and-proposal.md:1665:#### The same object has the same name at every layer
07-issue-and-proposal.md:1669:#### "Plan" means the `Plan()` call, and nothing else
07-issue-and-proposal.md:1673:### The headline renames
07-issue-and-proposal.md:1693:### The `scheduler` package
07-issue-and-proposal.md:1697:#### Scheduler members
07-issue-and-proposal.md:1711:#### ScheduleContext
07-issue-and-proposal.md:1729:#### Pipeline stages: folders and namespaces
07-issue-and-proposal.md:1762:#### Names seen in `motion_planner`
07-issue-and-proposal.md:1772:### planner_core: events and the DAG
07-issue-and-proposal.md:1788:### common_ros: the garage model
07-issue-and-proposal.md:1792:#### GarageGraph and Transition
07-issue-and-proposal.md:1811:#### PoseGraph and Layout
07-issue-and-proposal.md:1830:#### CollisionTable and footprints
07-issue-and-proposal.md:1845:#### DiscreteGarageState and asset ids
07-issue-and-proposal.md:1855:### ROS interfaces
07-issue-and-proposal.md:1859:#### Ids and integer widths
07-issue-and-proposal.md:1870:#### Garage model messages
07-issue-and-proposal.md:1888:#### State and event messages
07-issue-and-proposal.md:1903:#### Jobs, plans and schedules
07-issue-and-proposal.md:1920:#### Command messages
07-issue-and-proposal.md:1930:### Small struct refactors
07-issue-and-proposal.md:1934:#### Transition: one unit per field
07-issue-and-proposal.md:1955:#### Pose-change messages nest the pose
07-issue-and-proposal.md:1960:# today: AgvPoseChanged.msg (TrayPoseSetManually.msg is the same with tray_id)
07-issue-and-proposal.md:1967:# proposed
07-issue-and-proposal.md:1975:#### CollisionTable::Edge becomes a named struct
07-issue-and-proposal.md:1993:#### PoseGraph neighbour slots
07-issue-and-proposal.md:2008:#### AssetId with an enumerated type
07-issue-and-proposal.md:2013:# today: GarageEntityId.msg
07-issue-and-proposal.md:2017:# proposed: AssetId.msg
07-issue-and-proposal.md:2030:#### Disallowed headings live on the edge
07-issue-and-proposal.md:2035:# today: GarageLayout.msg
07-issue-and-proposal.md:2039:# proposed
07-issue-and-proposal.md:2045:### Keep as they are
07-issue-and-proposal.md:2056:### Decisions for review
07-issue-and-proposal.md:2067:### Rollout
08-verification.md:1:# 08 — Verification: regression parity and benchmarks
08-verification.md:5:## Two separate goals
08-verification.md:9:## What the existing tests cover
08-verification.md:26:### How a stage-level test is built
08-verification.md:57:### Tests most relevant to the two solvers
08-verification.md:76:### Gaps
08-verification.md:86:## Proposed benchmark dataset (requirements, not completed scenarios)
08-verification.md:105:## Compare meaning, not pointers or GUIDs
08-verification.md:149:## Benchmark method
08-verification.md:165:## Build and run commands
08-verification.md:177:## System-level checks in simulation
08-verification.md:181:## Test layers, and how baselines are computed and stored
08-verification.md:194:### Computing a baseline
08-verification.md:203:### Where fixtures and results are stored
08-verification.md:239:### Updating a golden file
08-verification.md:243:### Testing the algorithm without the simulator
08-verification.md:247:### Where the simulator fits
08-verification.md:253:## Acceptance checklist
08-verification.md:270:## Evidence limits
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
09-simulation.md:594:### Determinism, and what to compare
09-simulation.md:600:## Checking the refactor with the simulator
09-simulation.md:610:### Replay recorded plan calls
09-simulation.md:637:### Closed-loop runs
09-simulation.md:652:### When to run what
09-simulation.md:667:## Gaps and proposed improvements
09-simulation.md:687:## Open questions
09-simulation.md:702:## Evidence limits
INDEX.md:1:# Study pack index (file:line: heading). Read a section with Read offset=<line>.
