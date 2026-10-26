# 09 — Simulation: running the real stack against a simulated garage

*A simulation runs the garage software on a computer with no garage attached: the hardware, the patrons and the clock are replaced by programs that pretend to be them. This tab explains what that means, starting from nothing; which sites the layouts describe; what runs during a simulation; how to write a scenario, start a simulation, park and retrieve cars in it, and record it; and how to use it to show that the refactor changed nothing.*

## Simulation in brief

On site, the garage software is a set of programs that talk to each other and to hardware: AGVs, bays with sensors and doors, EV chargers, car lifts, and people using the app. In a simulation, **the same programs run unchanged**, and each piece of hardware, each person and the clock is replaced by a small program written for the purpose, a **stand-in**. The production programs cannot tell the difference: they send the same commands and receive the same kind of reports.

![On site and in simulation](figures/127_sim_architecture.svg)

**On site and in simulation.** Each row is one thing outside the software (left), the production program that talks to it (middle, unchanged), and the stand-in that replaces it in simulation (right, blue). The scheduler (green) talks only to Dispatch, so a simulation exercises it exactly as the site does.

That is what makes a simulation useful for this refactor: the scheduler receives realistic requests, many of them, from a garage whose state evolves over hours of simulated operation, and the result of each plan is carried out and checked for collisions. Nothing needs a real garage, and a simulation can run faster than real time.

The words used in the rest of this tab:

| Term               | Meaning here                                                                                                                     | Example                                                  |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| ROS 2 node         | A named unit of running software. Nodes exchange messages; the garage software is a few dozen of them                            | `/central/dispatcher`, `/scheduler/scheduler`            |
| topic              | A named stream of messages: one node publishes, any number listen                                                                | `/clock`, `/central/report`                              |
| service            | A named request and reply between two nodes                                                                                      | `/scheduler/plan`, `/sim/enqueue_garage_event`           |
| parameter          | A named setting a node reads, mostly at start                                                                                    | `real_time_factor`, `bay_readiness_ratio`                |
| process            | A program the operating system runs. A *component container* is one process that hosts several nodes                             | `sim/central_sim_nodes` hosts Dispatch and the scheduler |
| launch file        | A Python script that reads configuration and starts processes                                                                    | `sim.launch.py`                                          |
| configuration file | A text file on disk. It does nothing by itself; a launch file or a node reads it                                                 | layout, scenario, events and parameter files             |
| layout file        | The map of one garage: nodes, edges, bays, chargers (Layout file tab)                                                            | `5675_pecos_sandbox_qa`                                  |
| scenario file      | The starting state of one simulation: which layout, where the AGVs and trays are, which cars are parked, and a few timed actions | `5675_pecos_sandbox_qa_full_start_in_auto.yaml`          |
| events file        | A list of actions (park a car, retrieve a car, move an AGV) fed into a running simulation one after the other                    | `5675_pecos_sandbox_qa_events_drain_from_full.yaml`      |
| stand-in           | A program that exists only in simulation and replaces hardware, people or time                                                   | `/agv/a1/sim` plays AGV-1                                |
| simulated time     | The time every node sees, published by the simulated clock; it can run faster than real time or pause                            | `/clock`                                                 |
| patron             | A customer who parks (insert) or collects (retrieve) a car                                                                       |                                                          |

What a simulation can show: whether plans can be carried out without collisions, whether jobs succeed, how long they take, and how the system behaves over many jobs. What it cannot show: whether the hardware behaves like its stand-in. The stand-ins use the same timing parameters as the planner ([section 3.1](#sm-what-is-real-and-what-is-simulated)), so a simulation checks the plans, not the timing model.

## From the layout to a running simulation

A simulation starts from configuration files and ends as a set of running nodes. [Figure 2](#sm-fig-131_sim_layout_to_site) follows one example, the Pecos QA sandbox, from the files to the processes.

![From files to running processes](figures/131_sim_layout_to_site.svg)

**From files to running processes.** 1: three kinds of configuration file. 2: the launch file reads them once. 3: the nodes that then run, grouped by why they exist. Two simulated AGVs because the scenario lists two; one set of bay nodes because the layout has one bay; no charger or lift nodes because the layout has none; and a fixed set in every simulation.

- **The scenario file** (`scenario/scenarios/<name>.yaml`) names the layout, places AGVs and trays on its node ids, says which trays hold cars, may override parameters, and lists timed set-up actions such as "start Dispatch at 1 s".
- **The layout file** is the map of the Layout file tab ([section 2](#ly-the-file-at-a-glance)). The launch file reads it to decide which hardware exists, and every node receives its name as the `layout` parameter.
- **The parameter files** (`launcher/params/`) hold settings: defaults for every site (`params.yaml`), changes for simulation (`params_sim.yaml`) and the site's own hardware settings (`installations/params_<layout>.yaml`, optional in simulation). [Section 6.2](#sm-parameters) lists the order.

The rule for which nodes run:

| In the files                                           | Nodes started                                                                                                                                                 |
|--------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Each AGV in the scenario's `initial_conditions.agvs`   | `/agv/a<id>/sim`: a simulated AGV that starts at the pose given in the scenario                                                                               |
| Each `Bay` node in the layout                          | The real bay nodes `/bay/b<id>/bay_state_machine`, `vehicle_estimator`, `bay_guidance`, and the stand-in `/bay/b<id>/bay_sim` for the bay's sensors and doors |
| Each `BLift` node (a bay that is also a car-lift stop) | The same, with the BLift state machine instead of the standard one, plus `vrc_lift_bridge`; the launch fails if the BLift belongs to no `vrcs` entry          |
| Each `EvCharge` node                                   | `/vecs/v<id>/vecs_node` (real) and `vecs_sim_node` (stand-in charger)                                                                                         |
| Each `vrcs` entry (a car lift)                         | `/vrc/r<id>/manager`, the lift's stand-in: floors and heights from the layout, speed and doors from the parameters, starting floor from the scenario          |
| Always                                                 | The simulated clock and the Simulator, the central nodes with the scheduler, the REST API, and (by default) the visualizer                                    |

Because the launch file takes the layout name from the scenario, every node runs on the same layout, by construction.

### Where the layouts are

Layout names start with a street address. The parameter files and the scenarios name the following layouts. The locations below are inferred from the names; four addresses are confirmed by public sources, the others are guesses that the team can correct.

![Where the layouts are](figures/132_sim_sites.svg)

**Where the layouts are.** Grouped by the place the name points to, west to east. Green: the address is named in a public source. Amber: the street and city are inferred. Grey, dashed: a guess.

| Layout(s)                                                                                                            | Likely place                                                | Evidence                                                                                                                                                                                                                    | In the repository                                                                                                                                                                                                          |
|----------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `1355_fulton`                                                                                                        | 1355 Fulton St, San Francisco, CA                           | Named as Volley's operating garage ([CoStar](https://costar.com/article/2009773374/how-robot-valets-are-set-to-park-cars-in-new-york-luxury-towers))                                                                        | Installation parameters with IO-link addresses and a 5 kN load-cell scale; a scheduler test plans on it (Verification tab); a comment in `events_insert_retrieve.yaml` mentions the "Fulton garage"                        |
| `5675_pecos_bench`, `5675_pecos_sandbox_eng`, `_qa`, `_combined`                                                     | 5675 N Pecos St, Denver, CO                                 | Volley's headquarters and robotics test facility ([ColoradoBiz](https://coloradobiz.com/volley-automation-headquarters-denver-robotics-facility/))                                                                          | The layout of this pack ([section 2.2](#sm-the-pecos-test-facility)); the standardized test batches run on the sandboxes                                                                                                   |
| `38_gramercy`                                                                                                        | 38 Gramercy Park East, New York, NY                         | Condominium project with a Volley system ([Mann Report](https://www.mannpublications.com/mannreport/2026/07/08/volley-automation-deploying-robotic-parking-systems-at-two-marquee-new-york-city-residential-developments/)) | A BLift at node 26 and VRC 1: patrons insert on floor 1, the car goes down to floor 0 (comment in `params_38_gramercy.yaml`)                                                                                               |
| `550_w21st`                                                                                                          | 550 West 21st St, New York, NY                              | Second Manhattan project (same source)                                                                                                                                                                                      | Three batch configurations (14, 15 and 16 cars, one retrieve each) and `single_triple_pick_retrieve.yaml`; no installation parameter file                                                                                  |
| `576_eccles` and six variants (`_half`, `_mini`, `_no_bay`, `_under_vcr`, `_budget_sandbox`, `_budget_sandbox_mini`) | 576 Eccles Ave, South San Francisco, CA (inferred)          | Eccles Avenue is in South San Francisco, Volley's former headquarters city; the many variants suggest a test site                                                                                                           | `exercise_576_eccles.yaml` (2 AGVs, 27 trays, node ids up to 60); `try_odp_agv_collide_bay_outbound_node.yaml` on `_mini`; the scheduler tests the name in `UseEvChargeHeading` ([section 10.5](#ly-name-based-behaviour)) |
| `415_east_grand_ave`                                                                                                 | 415 East Grand Ave, South San Francisco, CA (inferred)      | East Grand Avenue is also in South San Francisco                                                                                                                                                                            | `params.yaml` keeps the default bay sensor box at 4.5 × 2.0 m with the comment "Old east grand ave sizes", which suggests an earlier site                                                                                  |
| `360_w_broadway`                                                                                                     | 360 West Broadway: SoHo, Manhattan, or South Boston (guess) | None found; both cities have a West Broadway, and Volley names projects in New York and Boston                                                                                                                              | Only `bay.floor_spec: 360_w_broadway_blift`: a BLift site                                                                                                                                                                  |
| `vrc_sandbox`                                                                                                        | Probably a car-lift test bed (guess)                        | No address in the name                                                                                                                                                                                                      | Installation parameters like the sandboxes'                                                                                                                                                                                |
| `275_sunrise_b`                                                                                                      | Not identified                                              | No match found for the address                                                                                                                                                                                              | Seven scenario files (the largest in the package), no installation parameter file                                                                                                                                          |
| `tiny_lot`, `multisize`                                                                                              | Synthetic                                                   |                                                                                                                                                                                                                             | Test layouts: the scheduler's unit tests use `tiny_lot`; `multisize` tests parking-window sizes                                                                                                                            |

### The Pecos test facility as three layouts

The Pecos YAML used throughout this pack (`5675_pecos_combined.yaml`) has two sections, marked by comments: `5675_pecos_sandbox_eng` (bay B7, stalls P2, P3, P5, P6, charger C10) and `5675_pecos_sandbox_qa` (bay B21, six stalls from P15 to P24, chargers C14 and C16). They are joined by the single edge W8–W13 ([section 5](#ly-edges)). The scenarios use three layouts: each sandbox alone and both together, with the same node ids. The names suggest an engineering area and a QA area on the same test floor.

![The Pecos test facility as three layouts](figures/133_sim_pecos_setups.svg)

**The Pecos test facility as three layouts.** Geometry from the Pecos YAML; AGVs, trays and cars read from the three `full_start_in_auto` scenario files. In the QA sandbox both AGVs start lowered under trays T15 and T17. The other start files change only the cars, the AGV positions and the dispatch mode.

The installation parameters of the three sandboxes differ in the hardware only: the IO-link master addresses are swapped between `sandbox_eng` (master 1 at .60, master 2 at .62) and the other two, `sandbox_eng` has a 5 kN load-cell scale (0.001), and all three set the bay's sensor box to 5.791 m × 2.2098 m (the XL parking window's length). `5675_pecos_bench` has an empty parameter file and no scenario in the snapshot.

### Two kinds of site: a bay at grade, and a bay on a car lift

Pecos is a single floor: the customer bay is one node of the parking floor. The New York sites are different. At 38 Gramercy the bay is a **BLift**: its tray carriage is also a stop of a car lift (VRC), so the patron leaves the car at the street-level motor court and the lift lowers the tray to the parking floor. 360 W Broadway has a BLift floor specification too. The launch file handles both kinds by node type.

![Two kinds of site](figures/134_sim_site_archetypes.svg)

**Two kinds of site.** Schematic side views. A BLift site adds the BLift bay machine, the bridge to its lift and the lift's stand-in. How far the planner supports car lifts is the subject of the Layout file tab ([section 8](#ly-vrc-support-status)).

For the refactor this matters in one way: a BLift scenario is the only kind that drives the lift code paths of the scheduler end to end. Their layouts are not in the snapshots, so no BLift scenario could be read.

## What runs during a simulation

A simulation runs the production software of the garage unchanged and replaces only the patrons, the operator, the hardware and time with stand-in nodes. Knowing which nodes are stand-ins shows which parts of a simulated run reflect the scheduler. The figure shows the processes for the Pecos QA sandbox; the table that follows lists each stand-in and what it plays.

![Processes, and the nodes inside them](figures/135_sim_launch_topology.svg)

**Processes, and the nodes inside them.** Each large box is one operating-system process; each row inside is one ROS node with its role. The example is the Pecos QA sandbox (bay B21, AGV-1 and AGV-2). The scheduler is one node of the central container, as on site.

The stand-ins, and what each one plays:

| Stand-in node                          | Package   | Plays                                                                                                                                                                                                                          | Settings it reads                                                                                          |
|----------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `/sim/sim_world` (the Simulator)       | `sim`     | The patrons and the operator: it seeds the garage with the scenario's AGVs, trays and cars, fires the scenario's timed actions, holds the queue of patrons waiting to park, and checks every update that no two bodies overlap | `simulator.scenario`: the scenario path, set by the launch file                                            |
| `/bay/b<id>/bay_sim`, one per bay      | `sim`     | The bay's sensors (load cells, break beams, vehicle proximity, radar) and doors, and the patron's confirmation of an insert or retrieve                                                                                        | `bay_id`, door open and close times, `bay.floor_spec`, `simulator.auto_confirm_insert` (default true)      |
| `/agv/a<id>/sim`, one per scenario AGV | `agvhito` | The AGV: it executes the command lists Dispatch sends and reports its pose, lift and state. On site the same package's `proxy_node` talks to the real AGVs instead                                                             | `agv_id`, `initial_node_id`, `initial_heading`, `initial_lifted` (from the scenario), the `agv` parameters |
| `/vecs/v<id>/vecs_sim_node`            | `vecs`    | An EV charger                                                                                                                                                                                                                  | `vecs_id`                                                                                                  |
| `/vrc/r<id>/manager`                   | `vrc`     | A car lift: floors, travel, gates                                                                                                                                                                                              | floors from the layout, speed and door times, starting floor                                               |
| `/sim/clock`                           | `sim`     | Time: publishes simulated time on `/clock`                                                                                                                                                                                     | `real_time_factor` (default 1.0), `clock_publish_period_ms` (5)                                            |

Two more nodes exist only in simulation but play nothing: the visualizer (`/vis/visualizer`, with the Foxglove bridge and RViz), which draws the garage from the published state, and the recorder (`/sim/recorder`), when recording is on.

### What is real and what is simulated

For the refactor, the boundary between production code and stand-ins determines what a simulated run can reveal. The list below separates the two and notes the timing values they share, which limit what a simulation can show about the cost model.

- **Real (production software, unchanged):** the dispatcher, the garage tracker and the monitors (`central`), the scheduler, the bay state machines, vehicle estimators and guidance (`bay`), the VECS manager, and the REST API. The dispatcher calls `/scheduler/plan` and carries out the response as on site (Dispatch tab, [section 3](#ds-what-goes-into-a-planrequest)).
- **Simulated:** patrons, the bay, charger and lift hardware, the AGVs, time, and the operator actions written in the scenario or an events file.
- **Shared timing:** `params.yaml` gives the AGV lift durations (6 s up, 6 s down) once, as the "shared source of truth between the scheduler's cost model and the AGV sim"; drive speeds and accelerations are in the same file. If the simulated AGV uses them as the cost model does, simulated job durations match the planner's estimates by construction, so a simulation cannot reveal a wrong cost model, only a wrong plan.

Because the scheduler is untouched by the simulation, any difference in a simulated run between the old and the refactored scheduler comes from the scheduler, or from timing ([section 8.3](#sm-determinism-and-what-to-compare)).

### How the processes are arranged

The nodes listed above run in a small number of operating-system processes. The grouping affects resource use, shutdown and network isolation, not how the nodes communicate; the points below cover the containers, the separate clock process, shutdown on failure and the ROS domain.

- **Component containers** group nodes into one process to save resources; it changes nothing about how they communicate. There are three kinds: `sim/sim_nodes` (the simulated AGVs and the Simulator), one `sim/b<id>_nodes` per bay, and `sim/central_sim_nodes` (the central nodes and the scheduler). Each runs a multi-threaded executor.
- **The clock runs in its own process**, on wall time, "to minimize lost-wakeup stalls"; every other node has `use_sim_time` true and follows it.
- If the clock process or the `sim_nodes` container exits unexpectedly (for example after a collision, [section 4.4](#sm-collision-checking)), the launch shuts everything down.
- `ROS_DOMAIN_ID` defaults to 75, so a simulation does not see other ROS systems on the network unless they use the same domain.

### Simulated time

`/sim/clock` keeps a simulated time and, every 5 ms of wall time, advances it by 5 ms × `real_time_factor` and publishes it on `/clock`. Every other node follows it, so all timers in the stack, including the dispatcher's 850 ms planner timer and the Simulator's 50 ms update, run in simulated time.

- `real_time_factor:=4` on the launch command runs four times faster; 0 pauses everything. It can be changed while running ([section 7.6](#sm-pause-speed-up-slow-down)).
- The scheduler's planning takes wall time. At high factors a plan call takes proportionally more simulated time, so job durations measured in simulated time grow with the factor. Fix the factor when comparing runs.
- At factors above 10, each `/clock` message advances time by more than the Simulator's 50 ms update period. Check that the timers still fire as often as expected before trusting results at such factors.
- The event runner of [section 5.2](#sm-events-files-and-the-exerciser) runs on wall time: its `sleep` action and its 1 s polling do not scale with the factor.

## One scenario run

[Figure 7](#sm-fig-128_sim_scenario_run) follows a run from start to end. Everything the Simulator does happens in its update, every 50 ms of simulated time.

![One scenario run](figures/128_sim_scenario_run.svg)

**One scenario run.** Seeding the garage, the start of the scenario clock, timed actions turned into service calls, the plan call, a patron's insert through the simulated bay, and the collision check that runs on every update.

### Seeding the garage, and the scenario clock

The first updates tell the garage tracker what is in the garage. The Simulator waits until `/central/add_agv`, `add_tray` and `add_payload` are available, then calls them for every AGV, tray and car of the scenario; a failed call stops the Simulator. `add_agv` receives only the id: the AGV's pose comes from its simulated AGV node, which the launch file started at the scenario's pose.

The **scenario clock** starts at the first update in which `/central/report` says Dispatch is stopped and consistent. The times in the scenario's `events` are seconds after that moment, not after the launch, so the same scenario lines up the same way whatever the start-up takes. Because Dispatch is stopped at that moment, a scenario normally starts with `set_dispatch_mode` and `start_dispatch` actions.

### Timed actions become service calls

The Simulator keeps the scenario's actions ("events") sorted by time. On each update it takes every action that is due and sends one service call for it. The same actions can be added while the simulation runs, through the service `/sim/enqueue_garage_event` ([section 7](#sm-recipes)).

| Action `type`                                            | Fields in the scenario file                                                                                                 | What happens                                                                                                                     |
|----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `start_dispatch`, `stop_dispatch`, `pause_dispatch`      | none                                                                                                                        | `/central/start`, `stop`, `pause`                                                                                                |
| `set_dispatch_mode`                                      | `mode`: 1 automatic, 2 manual (as the files use them)                                                                       | `/central/set_mode`                                                                                                              |
| `patron_arrival`                                         | `payload_id`; optional `length_m` (4.5), `width_m` (2.0), `height_m` (1.4), `mass` (1800 kg), `ev_charge_requested` (false) | A patron joins the Simulator's queue and waits for a bay ready to insert ([section 4.3](#sm-patrons-and-the-simulated-bay))      |
| `retrieve_request`                                       | `payload_id`                                                                                                                | `/central/retrieve`: a patron asks for this car                                                                                  |
| `charge_payload`                                         | `payload_id`                                                                                                                | `/central/charge_payload`                                                                                                        |
| `repark_tray`                                            | `tray_id`, `pose`, optional `allow_reciprocal`                                                                              | `/central/repark_tray`                                                                                                           |
| `move_agv`, `move_tray`                                  | `agv_id` or `tray_id`, `pose`                                                                                               | `/central/move_agv`, `move_tray`                                                                                                 |
| `remove_agv`                                             | `agv_id`                                                                                                                    | `/central/remove_agv`; the AGV's collision body is removed too                                                                   |
| `set_node_disabledness`, `set_tray_disabledness`         | `node_id` or `tray_id`, `disable`                                                                                           | `/central/set_node_disabledness`, `set_tray_disabledness`                                                                        |
| `transition_bay_to_insert`, `transition_bay_to_retrieve` | `bay_id`                                                                                                                    | `/central/transition_bay_to_insert`, `_retrieve`                                                                                 |
| `set_bay_readiness_ratio`                                | `bay_readiness_ratio`                                                                                                       | `/scheduler/set_bay_readiness_ratio`: the only action that talks to the scheduler directly; a change also queues a rebalance job |
| `set_auto_planner`                                       | `enabled`                                                                                                                   | Turns the dispatcher's 850 ms planner timer on or off                                                                            |
| `call_planner`                                           | none                                                                                                                        | `/central/trigger_plan_call`: one plan call now, accepted only while the timer is off                                            |
| `set_agv_battery_fraction`                               | `agv_id`, `battery_fraction`                                                                                                | Nothing: logged as not implemented                                                                                               |

Every action in a scenario file needs a `time`. A pose is `{node_id, heading}`. Most calls are asynchronous: the Simulator does not learn whether Dispatch accepted them. For testing the scheduler, `set_auto_planner: false` followed by `call_planner` actions makes plan calls happen at chosen moments instead of every 850 ms.

### Patrons and the simulated bay

A `patron_arrival` puts a car at the back of the Simulator's insert queue. Every update, the Simulator offers the car at the front to each bay (`/bay/b<id>/sim_offer_inserting_payload`). A bay's stand-in accepts only when its bay reports `READY_TO_INSERT` (an empty tray in the bay, doors ready) and no insert is in progress; the first bay that accepts takes the patron. If no bay is ready, the patron waits, however long that takes ([section 7.1](#sm-insert-a-car-automatically) says how bays become ready).

The bay's stand-in then plays the patron and the hardware, every 50 ms:

- **Load cells** show the tray's mass, plus the car's mass in proportion to the axles on the tray while the patron drives on (the tire sensor is briefly "broken" to model the wheels crossing it).
- **Vehicle proximity** sees the car; the **radar** is always clear; the doors open and close with the configured times.
- **Insert:** with `auto_confirm_insert` (the default), the stand-in confirms the insert with the car's dimensions when the bay's machine reaches `VEHICLE_INSERTED`. Otherwise the bay waits for a confirmation from outside, as from the app on site ([section 7.3](#sm-confirm-the-insert-yourself)). The bay then reports the car, and Dispatch creates the INSERT job that the scheduler plans.
- **Retrieve:** when the retrieve sequence runs and the doors are closed, the stand-in confirms the retrieve once; when the patron door opens, the car is assumed to leave at once.

### Collision checking

Every update, the Simulator builds a 3D box for every AGV, tray, car and bay from the latest `/central/garage_snapshot`; chargers and the scenario's obstructions are registered once. It tests every pair: two boxes collide when no face of either separates them (the separating-axis test) and their height bands overlap.

![Collision volumes in the simulator](figures/129_sim_collision_volumes.svg)

**Collision volumes.** The height bands of each body (A) and the separating-axis test in plan view (B). Schematic: the dimensions are constants in `common`, outside the snapshots.

An AGV and a tray whose centres are within 0.15 m in x and in y count as "carried" and are not reported; this also covers the QA sandbox's start, where both AGVs stand lowered under trays. Any other overlap ends the run: the Simulator logs a fatal error with the pair, for example `Collision: a3 collided with t17!` (a = AGV, t = tray, p = car keyed by its tray, b = bay, c = charger, o = obstruction), and stops, which stops the launch.

This check is independent of the planner's own collision model (Motion planning tab). It sees the poses the machines actually report, so it catches a plan that is unsafe when carried out, not only when planned. It sees them every 50 ms of simulated time, so a brief overlap between two updates can be missed.

### What the Simulator reports, and how to watch a run

While a scenario runs, its progress can be followed through a Simulator topic, the visualizer and the central topics of Dispatch. The list below names these sources, which are the ones to watch when checking whether a run proceeds as expected.

- `/sim/report`: whether the scenario clock is running, how many timed actions remain, and the cars waiting to be inserted.
- RViz and Foxglove (both started by default) show the visualizer's pictures: AGVs, their commands, trays, cars, bays, lifts, the layout, the insert and retrieve queues, and the current schedule.
- The central topics: `/central/report` (Dispatch's status, mode, consistency), the pending, active and completed job lists, and the plan request and response topics ([section 6.3](#sm-recording-a-run)).

## Scenario files and events files

The `scenario` package keeps two kinds of YAML file in one folder, `scenarios/`, and installs them all to `share/scenario/scenarios`:

- A **scenario file** has a `layout` key. It is what the launch command takes; the Simulator fires its `events` at their times.
- An **events file** has only `events`. A separate program, `exercise_sim_events`, feeds it into a running simulation one action at a time.

### The scenario file

The file is read twice: by the launch file in Python, which needs the layout, the AGVs and the parameter overrides, and by the Simulator in C++, which needs the trays, cars, obstructions and actions. A required field that is missing stops the start.

| Key                  | Content                                                                                             | Read by                                    |
|----------------------|-----------------------------------------------------------------------------------------------------|--------------------------------------------|
| `layout`             | Layout name                                                                                         | launch file, Simulator                     |
| `initial_conditions` | Either inline, or the name of a file holding them. Lists `agvs`, `trays`, `obstructions` and `vrcs` | launch file (AGVs, lifts), Simulator (all) |
| `params`             | Optional parameter overrides, `{section: {key: value}}`, applied over every parameter file          | launch file                                |
| `events`             | A list of `{time, type, ...}` ([section 4.2](#sm-events-become-service-calls))                      | Simulator                                  |

| Entry             | Fields (defaults)                                                                                                                                                                    |
|-------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `agvs[]`          | `id`; `garage_pose {node_id, heading}` (required: the simulated AGV starts there); `lift_fraction` (0; only exactly 1 starts the AGV lifted); `battery_fraction` (1; read, not used) |
| `trays[]`         | `id`; `garage_pose` ({0, 0}); `agv_id` (0) and `reciprocal_to_agv` (false) for a tray on an AGV; `disabled` (false); optional `payload` (the car on it)                              |
| `trays[].payload` | `id` (a GUID string); `length_m` (4.5), `width_m` (2.0), `height_m` (1.4), `mass` (1800 kg); `reciprocal_to_tray` (false)                                                            |
| `obstructions[]`  | `id`, `x_loc`, `y_loc`, `yaw` \[rad\], `x_len`, `y_len` \[m\]; `z_loc` (0), `z_len`. Collision bodies only: the planner does not know about them                                     |
| `vrcs[]`          | `id`, `initial_floor`: the lift's starting floor (−1 if absent)                                                                                                                      |

Conventions in the existing files: tray ids equal the node id of their starting stall (T15 on P15); car lengths are the parking-window lengths (5.182 m STANDARD, 5.791 m XL, 4.877 m, 4.4 m COMPACT); car GUIDs follow a pattern such as `00030017-0000-0000-0000-000000001717`. A readme in the package (`readme_payload_guid_bytes_to_vehicle_model_color.md`, not in the snapshot) explains how the GUID's bytes select the car model and colour the visualizer draws.

### Events files and the exerciser

`exercise_sim_events` (the "exerciser") is a separate program, started in a second terminal while a simulation runs:

``` bash
ros2 run scenario exercise_sim_events -l <layout> -e <events file> [-o <csv>]
```

It waits until Dispatch is running, then runs the file's actions in order, each after the previous one is handled, and sends each one to `/sim/enqueue_garage_event` with time 0, so the Simulator fires it on its next update.

![Two ways to feed events](figures/136_sim_two_runners.svg)

**Two ways to feed actions.** A: the scenario file's actions, fired by the Simulator at fixed times. B: an events file, fed one action at a time; an action with `wait_for_job_completion` holds the next one until its job ends.

| Action `type`           | Fields                                                                          | Counts as handled when                                                            | Job it follows      |
|-------------------------|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|---------------------|
| `retrieve_request`      | `payload_id` (optional: a random car in the garage, never the same one twice)   | the service answers                                                               | RETRIEVE            |
| `patron_arrival`        | `payload_id` (optional: random GUID), `length_m`, `width_m`, `height_m`, `mass` | a bay was ready to insert when the request was sent and has since left that state | INSERT              |
| `repark_tray`           | `tray_id`, `pose`, `allow_reciprocal` (required)                                | the service answers                                                               | REPARK_TRAY         |
| `move_agv`, `move_tray` | `agv_id` or `tray_id`, `pose`                                                   | the service answers                                                               | MOVE_AGV, MOVE_TRAY |
| `sleep`                 | `duration` \[s, wall time\]                                                     | the time has passed                                                               | none                |

- **Optional on every action:** `wait_for_job_completion: true` makes the action count as handled only when its job has ended (SUCCESS or ERROR).
- **Which job belongs to an action:** before each action, the exerciser notes the jobs of that type already in Dispatch's report; the first new job of that type is taken as the action's job.
- **End:** after the last action, when every followed job has ended, the exerciser writes one CSV row per action (default `/tmp/sim_results/events_summary.csv`), stops the other ROS processes, and exits with status 0, or 1 if any job ended in ERROR or something failed.

This is the closest thing to a pass or fail the stack has: an events file gives an exit status and a metrics file per run.

### The per-site scenario family

Each site with standardized tests gets the same set of files: start files and events files that pair up. The Pecos sandboxes follow this pattern, and so does `275_sunrise_b`.

![The per-site scenario family](figures/137_sim_scenario_families.svg)

**The per-site scenario family.** Filling an empty garage and draining a full one use the same car GUIDs, so one undoes the other. The move-each-node files and the standardized batch do not run as they are ([section 10](#sm-gaps-and-improvements)).

Two settings in the start files are chosen on purpose. `bay_readiness_ratio` is 1.0 when the garage starts empty, so that every bay is made ready for a patron, and 0.0 when it starts full, so that the scheduler does not spend AGV time preparing bays for inserts that will not come. The auto planner is switched on at 5 s, after Dispatch has started in automatic mode at 1 s.

Besides the families, the package has scenarios named after one behaviour. They are the closest existing material to the catalogue of [section 8.2](#sm-a-scenario-catalogue-for-the-refactor):

| Scenario                                         | Layout                   | What it sets up                                                                                        | Runs as is?                                                                                 |
|--------------------------------------------------|--------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `tiny_lot_retrieve`                              | `tiny_lot`               | One AGV, one car on T2; retrieve at 5 s                                                                | yes                                                                                         |
| `tiny_lot_move_tray`                             | `tiny_lot`               | Repark T2 on its own node with heading 180 at 3 s (a turn in place)                                    | yes                                                                                         |
| `tiny_lot_idle`                                  | `tiny_lot`               | Dispatch in automatic mode with nothing to do; tray T9 starts on the AGV's node                        | yes                                                                                         |
| `multisize_inserts_and_retrieves`                | `multisize`              | Patrons with cars of 5.4, 5.0 and 4.4 m, a retrieve at 180 s, another patron                           | yes                                                                                         |
| `clean_garage_unstashes_waypoint_tray`           | `5675_pecos_sandbox_eng` | T1 on waypoint W1, T2 in bay B7                                                                        | no actions: Dispatch never starts unless someone starts it                                  |
| `repark_tray`, `payload_starts_in_bay`           | `5675_pecos_sandbox_eng` | A car on a stall, or in bay B7                                                                         | same; meant to be driven by hand                                                            |
| `charge_then_repark`                             | `5675_pecos_sandbox_eng` | AGV-2 in bay B7, its battery set to 9 % at 150 s to free the bay, a repark at 190 s                    | runs, but the battery actions are not implemented, so the case it describes does not happen |
| `single_triple_pick_retrieve`                    | `550_w21st`              | 15 cars, two AGVs; no actions (the batch configurations add one retrieve each)                         | with a batch runner                                                                         |
| `exercise_576_eccles`                            | `576_eccles`             | 27 trays (26 with cars of 2000 kg and 1.75 m), node 26 disabled at 1 s, auto planner at 10 s           | yes                                                                                         |
| `try_odp_agv_collide_bay_outbound_node`          | `576_eccles_mini`        | Two AGVs under two trays on a bay's outbound node: a collision case for the bay's overdrive plate      | needs `start_dispatch`                                                                      |
| `events_insert_retrieve`, `tiny_lot_events_fill` | (events files)           | A long insert and retrieve sequence that "should fill up" the Fulton garage; two patrons on `tiny_lot` | no: older action types ([section 10](#sm-gaps-and-improvements))                            |

### Batch configurations

`batch_configs/*.yaml` group runs: a `batch_name` to group results, a `layout` and `layout_version`, one start `scenario`, and a list of `events` files. The three `550_w21st` batches start a full garage (14, 15 or 16 cars) and retrieve each car in turn, one events file per stall; the two standardized tests run `fill_and_drain` three times on the engineering and the QA sandbox, with `batch_name: release-26.XX` to be replaced by the release under test.

The program that reads these files is not in the snapshots, and the package does not install `batch_configs/`. The launch code is ready for it: `get_sim_launch_description` takes a scenario, an artifacts directory and base name, parameter overrides and a real time factor as Python arguments.

### A scenario for the running example

The running example of the deck, written as a start file and an events file on the QA sandbox: a retrieve whose route is blocked by tray T15, with the empty tray T21 still in bay B21, followed by a patron who wants to park. The files are a proposal, not files from the repository; they follow the conventions of the existing files.

``` yaml
# PROPOSED: 5675_pecos_sandbox_qa_retrieve_with_blocker.yaml (start file)
layout: 5675_pecos_sandbox_qa
initial_conditions:
  agvs:
    - {id: 1, garage_pose: {node_id: 26, heading: 90}}                 # AGV-1 on waypoint W26
    - {id: 2, garage_pose: {node_id: 24, heading: 90}}                 # AGV-2 lowered on stall P24
  trays:
    - {id: 15, garage_pose: {node_id: 15, heading: 90}}                # empty, on the route
    - id: 17
      garage_pose: {node_id: 17, heading: 90}
      payload: {id: 00030017-0000-0000-0000-000000001717, length_m: 5.182, width_m: 2.21}
    - id: 20
      garage_pose: {node_id: 20, heading: 90}
      payload: {id: 00050020-0000-0000-0000-000000002020, length_m: 5.182, width_m: 2.21}
    - {id: 21, garage_pose: {node_id: 21, heading: 90}}                # empty, in bay B21
params:
  scheduler: {cost_audit: true}                                       # per-segment cost lines in the log
events:
  - {type: set_dispatch_mode, time: 0.5, mode: 1}
  - {type: set_bay_readiness_ratio, time: 0.5, bay_readiness_ratio: 0.0}
  - {type: start_dispatch, time: 1.0}
  - {type: set_auto_planner, time: 5.0, enabled: true}

# PROPOSED: 5675_pecos_sandbox_qa_events_retrieve_then_park.yaml (events file)
events:
  - type: retrieve_request
    payload_id: 00030017-0000-0000-0000-000000001717
    wait_for_job_completion: true
  - type: patron_arrival
    payload_id: 00000000-0000-0000-0000-000000000099
    length_m: 4.877
    width_m: 2.21
    wait_for_job_completion: true
```

Whether the patron can park depends on a bay becoming ready to insert. With `bay_readiness_ratio` 0.0, Dispatch does not prepare one by itself; whether the empty tray that the retrieve leaves in B21 is enough is for a run to show. If the patron keeps waiting, raise the ratio ([section 7.2](#sm-insert-a-car-by-hand)). If Dispatch starts in automatic mode it may also queue a clean and a rebalance job of its own (Dispatch tab, [section 2](#ds-jobs-in-dispatch)), so the first plan call can already contain more than the retrieve.

## Running a simulation

This section covers the practical side: preparing the files, launching the stack, feeding it work and evaluating the result. The figure shows the whole workflow in seven steps across two terminals; the subsections that follow cover the launch command, parameters, recording, and the risk of pairing a simulation with the wrong layout or events file.

![Running a simulation, end to end](figures/138_sim_workflow.svg)

**Running a simulation, end to end.** Prepare the files (1, 2), run (3 to 5), evaluate (6, 7). Terminal 1 holds the launch; terminal 2 is for feeding work and for the commands of [section 7](#sm-recipes). Nothing checks that step 4 matches the simulation started in step 3 ([section 6.4](#sm-mismatch-protection)).

### Launching

A simulation is started with one `ros2 launch` command that names a scenario file; an optional earlier command draws the layout map with its node ids. The example below starts a Pecos QA sandbox scenario at four times real time with recording on, and the table after it lists every argument the launch file reads, with its default.

``` bash
source install/setup.bash                                                   # in every terminal
ros2 run launcher layout_plotter 5675_pecos_sandbox_qa -o /tmp/qa.png       # optional: the map, with node ids
ros2 launch launcher sim.launch.py \
  scenario:=5675_pecos_sandbox_qa_full_start_in_auto.yaml \
  real_time_factor:=4 record_artifacts:=true rviz:=false
```

The launch keeps running until Ctrl+C, a collision, or the exerciser stops it. Its arguments:

| Argument                             | Default                                                                                                                                          | Effect                                                                                                                                                                                       |
|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scenario:=`                         | (required)                                                                                                                                       | A path to a scenario file, or a file name in `share/scenario/scenarios`. The name is joined to that folder unchanged, so it includes `.yaml`. A path needs no rebuild after editing the file |
| `real_time_factor:=`                 | `1.0`                                                                                                                                            | Simulated seconds per wall second ([section 3.3](#sm-simulated-time))                                                                                                                        |
| `vis:=`                              | `true`                                                                                                                                           | Start the visualizer and the Foxglove bridge                                                                                                                                                 |
| `rviz:=`                             | `true`                                                                                                                                           | Start RViz; only has an effect when `vis` is true                                                                                                                                            |
| `record_artifacts:=`                 | `false`                                                                                                                                          | Record every topic to an mcap file ([section 6.3](#sm-recording-a-run))                                                                                                                      |
| `artifacts_output_dir:=`             | `$ARTIFACTS_DIR/<UTC timestamp>`; if `ARTIFACTS_DIR` is unset, `$ROS_HOME/artifacts/<UTC timestamp>`, that is `~/.ros/artifacts/<UTC timestamp>` | Folder for the recording; the timestamp looks like `20261020T120000Z`                                                                                                                        |
| `artifact_basename:=`                | `sim`                                                                                                                                            | Subfolder and file prefix of the recording                                                                                                                                                   |
| `auto_confirm_insert:=`              | `true` (from `params.yaml`)                                                                                                                      | Whether the bay's stand-in confirms inserts itself ([section 7.3](#sm-confirm-the-insert-yourself))                                                                                          |
| `garage_dirtiness_threshold_ratio:=` | `0.10` (from `params.yaml`)                                                                                                                      | How untidy an idle garage may get before Dispatch queues a clean-garage job                                                                                                                  |
| `enable_dispatch_charging_mode:=`    | `true`                                                                                                                                           | Only `false` has an effect: it sets the parameter to false. Otherwise the node keeps its own default, which is not in the snapshots                                                          |
| `printdags:=`                        | `false`                                                                                                                                          | Sets the `printdags` parameter of every node                                                                                                                                                 |
| `use_remote_meshes:=`                | `false`                                                                                                                                          | Where the visualizer loads its 3D models from: `false` uses the local `package://sim/3d/`; `true` uses `remote_mesh_prefix`                                                                  |
| `remote_mesh_prefix:=`               | `https://aws-mesh-proxy.tailfadbb4.ts.net/model/` (the visualizer's built-in value)                                                              | Base URL of the 3D models; used only with `use_remote_meshes:=true`                                                                                                                          |

These are not declared launch arguments: the launch file reads them from the command line with regular expressions. `ros2 launch ... --show-args` does not list them, and a misspelled one is ignored without a warning.

### Parameters, from defaults to the scenario

Every node gets one merged set of parameters. Later layers win:

| Layer | File or source             | Notes                                                                                                                                                                                                                   |
|-------|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1     | `params/params.yaml`       | Defaults: AGV speeds, accelerations and lift times; bay doors and hardware addresses; `scheduler.bay_readiness_ratio` 0.5, `scheduler.cost_audit` false; `simulator.auto_confirm_insert` true; charger and lift timings |
| 2     | `params/params_sim.yaml`   | No MySQL database for the garage tracker; the bay guidance web socket off (port 0)                                                                                                                                      |
| 3     | `params_<layout>.yaml`     | The site's installation file ([section 2.1](#sm-where-the-layouts-are)), if it exists. Without one, the bay's sensor box stays 4.5 m × 2.0 m                                                                            |
| 4     | `params_s<DEVICE_ID>.yaml` | Optional; `DEVICE_ID` defaults to 0                                                                                                                                                                                     |
| 5     | common values              | `layout`, `installation_id` 9998, `use_sim_time` true, in every section                                                                                                                                                 |
| 6     | the scenario's `params:`   | Per-scenario overrides                                                                                                                                                                                                  |
| 7     | launch arguments           | `is_simulation` true, and the arguments above                                                                                                                                                                           |

Layer 6 is the clean way to vary a scheduler setting in a test, for example `params: {scheduler: {bay_readiness_ratio: 0.0}}`, without editing a shared file.

### Recording a run, and looking at it again

`record_artifacts:=true` adds a recorder (`/sim/recorder`, on simulated time) that writes every topic into one mcap file set, compressed and not split, in `<artifacts_output_dir>/<artifact_basename>`. Topics that appear later are recorded as well.

The recording therefore holds what a replay of the scheduler needs: Dispatch publishes every request it sends to `/scheduler/plan` and every response it receives on two topics, explicitly "to be bagged", next to the job lists, the reports, the scheduler's report (with the current `bay_readiness_ratio`) and `/clock`. To look at a recording again, with the visualizer and Foxglove:

``` bash
ros2 launch launcher bagplay.launch.py bagfile:=~/.ros/artifacts/20261020T120000Z/sim   # plays it in a loop
```

### A wrong layout or events file in step 4

Step 4 names a layout and an events file a second time, independently of the scenario launched in step 3. No component checks that the three agree. The exerciser reads its `-l` argument only to print it, and the Simulator accepts any action whose type it knows. The table lists what happens today for each kind of mismatch.

| Mistake in step 4                                                                                                | What happens                                                                                                                                                                                             | Detected          |
|------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|
| `-l` names a different layout                                                                                    | Nothing changes. The simulation keeps the layout of the scenario launched in step 3; only the exerciser's log line is wrong.                                                                             | No                |
| The events file name is misspelled                                                                               | Loading fails before the first action; the exerciser exits with status 1. The simulation keeps running, because the exerciser's shutdown step is skipped.                                                | Yes, at once      |
| An action type is unknown                                                                                        | The exerciser stops with "Unknown event type" when it reaches that action, with status 1; the simulation keeps running.                                                                                  | Yes, when reached |
| The events file was written for another layout: a `retrieve_request` names car GUIDs that are not in this garage | The Simulator accepts the request (its answer only confirms the action type), Dispatch refuses the retrieve, and no job appears. The exerciser waits for that job without a time limit.                  | No: the run hangs |
| As above, with `move_tray`, `move_agv` or `repark_tray`                                                          | Tray, AGV or node ids that do not exist here: refused, and the run hangs in the same way. Ids that happen to exist here as well: a different but valid move is executed, and the run ends with status 0. | No                |
| `patron_arrival` actions                                                                                         | Not tied to a layout: the car is offered to whichever bay is ready to insert. Only the car dimensions may not suit the site.                                                                             | Not needed        |

The exerciser does record a refused request (the flag `_sim_event_failed` in `event_base.py`), but no code reads the flag. It also attributes to an action the first new job of the matching type, so a job that Dispatch creates on its own, such as a clean-garage tray move, can be mistaken for the job of a refused action.

Proposed protections, from the cheapest:

1.  **Compare `-l` with the running simulation.** Every node carries the `layout` parameter (parameter layer 5); the exerciser reads it from `/sim/sim_world` and stops with status 1 on a mismatch. Alternatively, drop `-l` and take the layout from the simulation.
2.  **Declare the layout in each events file.** A top-level `layout:` line, as scenario files and batch configurations already have; the exerciser refuses a file whose layout differs from the running one.
3.  **Check identifiers before the first action.** Car GUIDs against the cars in `DiscreteGarageState`, which the exerciser already receives; tray, AGV and node ids against the layout.
4.  **Treat refusals and silence as failures.** Act on `_sim_event_failed`, and give each action a time limit for its job to appear and to finish.
5.  **Test the files in CI.** For every events file: a declared layout, identifiers that exist in that layout and in the start scenario it is paired with in a batch configuration.

Until these exist, the practical safeguards are to keep events files named after their layout (as the per-site families are), to check the start of the exerciser's output for "Waiting for event … to be handled" lines that never clear, and, where the batch runner is available, to start runs from a batch configuration ([section 5.4](#sm-batch-configurations)), which names the layout, the start scenario and the events files together.

## Recipes: parking, retrieving and steering a running simulation

The commands below assume a launched simulation in terminal 1 and are typed in terminal 2, after `source install/setup.bash` and with the same `ROS_DOMAIN_ID` (75 unless set). Bay and node ids are those of the Pecos QA sandbox.

![How a car gets parked in simulation](figures/139_sim_insert_paths.svg)

**How a car gets parked in simulation.** Three ways to make a patron arrive (A, B, C), one queue, the wait for a bay ready to insert, the simulated drive-on, the confirmation (automatic or by hand), and the production software parking the car.

### Insert a car automatically, from the scenario

A patron can park only when a bay is **ready to insert**: an empty tray stands in the bay and its doors are ready. In automatic mode Dispatch prepares bays by itself when `bay_readiness_ratio` is above 0 and an empty tray is free; in manual mode nobody prepares a bay unless asked. So the start file must give the garage at least one empty tray, run Dispatch in automatic mode, and set a readiness ratio above 0. The QA sandbox's `empty_start_in_auto` file does all three; copy it and add one action:

``` yaml
# my_qa_one_insert.yaml: a copy of 5675_pecos_sandbox_qa_empty_start_in_auto.yaml, plus the last action
layout: 5675_pecos_sandbox_qa
initial_conditions:
  agvs:
    - {id: 1, garage_pose: {node_id: 15, heading: 90}}
    - {id: 2, garage_pose: {node_id: 17, heading: 90}}
  trays:                                         # six empty trays
    - {id: 15, garage_pose: {node_id: 15, heading: 90}}
    - {id: 17, garage_pose: {node_id: 17, heading: 90}}
    - {id: 19, garage_pose: {node_id: 19, heading: 90}}
    - {id: 20, garage_pose: {node_id: 20, heading: 90}}
    - {id: 23, garage_pose: {node_id: 23, heading: 90}}
    - {id: 24, garage_pose: {node_id: 24, heading: 90}}
events:
  - {type: set_dispatch_mode, time: 0.5, mode: 1}                    # automatic
  - {type: set_bay_readiness_ratio, time: 0.5, bay_readiness_ratio: 1.0}
  - {type: start_dispatch, time: 1.0}
  - {type: set_auto_planner, time: 5.0, enabled: true}
  - type: patron_arrival                                             # the car to park
    time: 60.0
    payload_id: 00000000-0000-0000-0000-000000000099
    length_m: 5.182
    width_m: 2.21
```

``` bash
ros2 launch launcher sim.launch.py scenario:=$PWD/my_qa_one_insert.yaml real_time_factor:=4
```

What happens: an AGV brings an empty tray into B21 and the bay becomes ready; at 60 s of scenario time the patron arrives, the bay's stand-in plays the drive-on and confirms, Dispatch creates an INSERT job, the scheduler plans it and an AGV parks the car. `ros2 topic echo /sim/report` shows the car in the waiting list until a bay takes it. A time before the bay is ready does no harm: the patron waits in the queue.

The same with an events file, which also gives an exit status: write the `patron_arrival` (without `time`, with `wait_for_job_completion: true`) into an events file and run `ros2 run scenario exercise_sim_events -l 5675_pecos_sandbox_qa -e <file>`. The exerciser itself waits for a ready bay before it sends the patron.

### Insert a car by hand, while the simulation runs

The quickest way is the script in the `sim` package's `scripts/` folder:

``` bash
scripts/trigger_patron_arrival.bash      # a patron with a random id: 1500 kg, 5.0 m x 2.0 m x 3.0 m
```

It prints a "Generated UUID" and a "UUID byte array". Only the byte array is the car's id; the printed UUID is generated separately and is not used ([section 10](#sm-gaps-and-improvements)). To choose the id and the size, call the service yourself:

``` bash
ros2 service call /sim/enqueue_garage_event interfaces/srv/SimEvent "{type: patron_arrival, time: 0.0,
  payload: {id: {bytes: [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,153]},
            mass: 1500.0, length_m: 5.182, width_m: 2.21, height_m: 1.5}}"
```

- `time` is in seconds of scenario time: 0, or any time already past, fires on the next update; a later time schedules the action.
- `id` is the 16 bytes of the car's GUID. The bytes above are meant as `00000000-0000-0000-0000-000000000099` (0x99 = 153), assuming the bytes are in the order of the written GUID; the conversion is in `common`, outside the snapshots.
- Through the service there are no defaults: a size left out is 0. Give mass, length, width and height.
- The reply says `success: true` when the action was queued; an unknown `type` gives `success: false` with the reason.

If no bay becomes ready, give the garage one: in automatic mode, raise the ratio with `"{type: set_bay_readiness_ratio, time: 0.0, float_value: 1.0}"`; in manual mode, with an empty tray already in the bay, ask for the transition with `"{type: transition_bay_to_insert, time: 0.0, resource_id: 21}"`.

### Confirm the insert yourself

On site, a patron who has left the car confirms the insert in the app. The simulation does this automatically unless launched with `auto_confirm_insert:=false`; the bay then waits after the drive-on until someone confirms through the REST API, as the app would:

``` bash
curl -X POST http://localhost:5000/api/bay/b21/confirm-insert -H "Content-Type: application/json" \
  -d '{"payload_id":"<uuid>","payload_id_claim":"<uuid>","patron_name":"","patron_identity":"","payload_type":"auto"}'
```

`scripts/confirm_insert.bash` sends this request with a new random UUID, for bay B39 of the Eccles layout; change the bay number for another layout (B21 or B7 on Pecos). Use this to test what happens when a patron is slow to confirm, or to drive the bay by hand.

### Retrieve a car

A retrieve needs the car's GUID: one from the scenario's `initial_conditions`, or one given at its `patron_arrival`. No ready bay is needed: the retrieve job prepares one. The bay's stand-in always confirms the retrieve itself, and the car leaves as soon as the patron door opens.

- **From the scenario file:** `- {type: retrieve_request, time: 120.0, payload_id: 00030017-0000-0000-0000-000000001717}`.
- **From an events file:** a `retrieve_request` without `payload_id` picks a random car still in the garage.
- **By hand:** `ros2 service call /sim/enqueue_garage_event interfaces/srv/SimEvent "{type: retrieve_request, time: 0.0, payload: {id: {bytes: [...]}}}"`.

### Other operator actions by hand

Every action of [section 4.2](#sm-events-become-service-calls) can be sent through `/sim/enqueue_garage_event`. The service has one set of generic fields, so each action uses some of them:

| Action `type`                                                       | Service fields used                                              | Example                                                                                               |
|---------------------------------------------------------------------|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `start_dispatch`, `stop_dispatch`, `pause_dispatch`, `call_planner` | none                                                             | `{type: stop_dispatch, time: 0.0}`                                                                    |
| `set_dispatch_mode`                                                 | `uint_value` = mode                                              | `{type: set_dispatch_mode, time: 0.0, uint_value: 2}`                                                 |
| `set_auto_planner`                                                  | `bool_value` = enabled                                           | `{type: set_auto_planner, time: 0.0, bool_value: false}`                                              |
| `set_bay_readiness_ratio`                                           | `float_value`                                                    | `{type: set_bay_readiness_ratio, time: 0.0, float_value: 0.5}`                                        |
| `move_agv`, `move_tray`                                             | `resource_id` = AGV or tray id, `pose`                           | `{type: move_agv, time: 0.0, resource_id: 1, pose: {node_id: 26, heading: 90}}`                       |
| `repark_tray`                                                       | `resource_id` = tray id, `pose`, `bool_value` = allow_reciprocal | `{type: repark_tray, time: 0.0, resource_id: 20, pose: {node_id: 23, heading: 90}, bool_value: true}` |
| `remove_agv`                                                        | `resource_id` = AGV id                                           | `{type: remove_agv, time: 0.0, resource_id: 2}`                                                       |
| `set_node_disabledness`, `set_tray_disabledness`                    | `resource_id` = node or tray id, `bool_value` = disable          | `{type: set_node_disabledness, time: 0.0, resource_id: 22, bool_value: true}`                         |
| `transition_bay_to_insert`, `transition_bay_to_retrieve`            | `resource_id` = bay id                                           | `{type: transition_bay_to_insert, time: 0.0, resource_id: 21}`                                        |
| `charge_payload`, `retrieve_request`, `patron_arrival`              | `payload`                                                        | see the sections above                                                                                |

The type is matched without regard to case. Wrap the whole request in double quotes after `interfaces/srv/SimEvent`, as in the examples above.

### Pause, speed up, slow down, watch

The speed of a running simulation is set by the `real_time_factor` parameter of `/sim/clock` ([section 3.3](#sm-simulated-time)), which can be changed without restarting the launch. The commands below pause and resume the simulation, change its speed, and show the Simulator and Dispatch reports while it runs.

``` bash
ros2 param set /sim/clock real_time_factor 0     # pause everything
ros2 param set /sim/clock real_time_factor 1     # real time again; 4 = four times faster
ros2 topic echo /sim/report                      # scenario clock running? actions left? cars waiting?
ros2 topic echo /central/report                  # Dispatch: status, mode, consistent or not
```

## Testing with scenarios

A scenario run exercises the scheduler on realistic, changing garage states, but the Simulator by itself fails only on a collision. This section sets out which signals a run provides, a catalogue of scenarios covering the cases the refactor must preserve, and why two runs of the same scenario cannot be compared request by request.

### What a run can tell you

The Simulator itself only fails on a collision; the exerciser adds an exit status for the jobs it followed. The other signals are in the topics, and a test has to read them:

| Signal                      | Where                                                                                                         | Meaning for the scheduler                                                                                                     |
|-----------------------------|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Collision                   | fatal log line; the launch stops                                                                              | The plan, as carried out, put two bodies in the same place: a motion-planning or action-graph defect, or an execution problem |
| Exerciser exit status       | 0, or 1 if a followed job ended in ERROR                                                                      | A job of the workload failed                                                                                                  |
| Job outcome                 | completed job list: SUCCESS or ERROR, with notes; the exerciser's CSV                                         | An ERROR from planning means the scheduler failed the job (its message is the scheduler's error text)                         |
| Rejected plan               | Dispatch log (`RejectPlanResponse`), no new schedule                                                          | The response broke Dispatch's checks: base schedule changed, id mismatch, every job failed                                    |
| Stuck run                   | the exerciser does not finish; or no actions remain but pending or active jobs do not decrease for a set time | A plan that cannot complete, a job planned again and again, or a deadlock                                                     |
| Divergence or inconsistency | `/central/report`                                                                                             | What the machines did no longer matches the plan; Dispatch stops                                                              |
| Durations                   | the exerciser's CSV; the job lists                                                                            | Plan quality as the patron sees it: how long a retrieve takes                                                                 |

### A scenario catalogue for the refactor

The benchmark matrix of the Verification tab ([section 3](#vr-proposed-benchmark-dataset-requirements-not-completed-scenarios)) lists what each solver must be exercised on. The same cases as simulation runs, on real-site layouts, make each row run through the whole stack. The last column says which existing files already cover the case:

| Case                      | Key actions                                                                 | Exercises                                                                 | Expected                                   | Existing files                                                                                            |
|---------------------------|-----------------------------------------------------------------------------|---------------------------------------------------------------------------|--------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Retrieve, free route      | `retrieve_request`                                                          | Tray: empty-tray choice for the bay. AGV: one nearby AGV                  | Job SUCCESS, one plan call                 | `tiny_lot_retrieve`                                                                                       |
| Retrieve behind a blocker | retrieve of a car enclosed by trays                                         | Tray: blocker resolution, free-stall choice, freeing-move edges           | SUCCESS; blocker moved before the root     | none ([section 5.5](#sm-a-scenario-for-the-running-example))                                              |
| Drain a full garage       | one `retrieve_request` per car, each waiting for completion                 | Tray: recursive resolution, deep cars; AGV: every stall reached           | All SUCCESS                                | `*_full_start_in_auto` + `*_events_drain_from_full` (three Pecos layouts); the `550_w21st` batches        |
| Back-to-back requests     | several requests without waiting                                            | Tray and AGV across jobs in one call; bottleneck matching over many roots | All SUCCESS; no AGV double-booked          | none for retrieves; the first two patrons of `5675_pecos_sandbox_combined_events_fill_from_empty` overlap |
| Fill an empty garage      | one `patron_arrival` per stall                                              | INSERT jobs, parking-spot choice, bay readiness                           | Queue drains; all cars parked              | `*_empty_start_in_auto` + `*_events_fill_from_empty`                                                      |
| Mixed sizes               | patrons with cars of several lengths                                        | Parking-window fit                                                        | Each car on a stall of its size            | `multisize_inserts_and_retrieves`                                                                         |
| Clean garage              | trays on waypoints at the start, Dispatch in automatic mode                 | Tray: stash and unstash moves; AGV: several moves of one tray             | Waypoints cleared                          | `clean_garage_unstashes_waypoint_tray` (needs set-up actions)                                             |
| Disabled node             | `set_node_disabledness`                                                     | Reservation and keep-out filters, route repair                            | SUCCESS on another route, or a clear ERROR | `exercise_576_eccles` (disabled from the start)                                                           |
| AGV lost                  | `remove_agv` mid-run                                                        | AGV assignment with fewer candidates                                      | Jobs complete with the remaining AGVs      | none                                                                                                      |
| Readiness change          | `set_bay_readiness_ratio`                                                   | Rebalance job: bay transitions and tray moves                             | Bays end in the requested ratio            | the start files set it once                                                                               |
| Planner on demand         | `set_auto_planner: false`, then `call_planner` after each burst of requests | Large plan calls with many pending jobs                                   | Repeatable call contents for replay        | none                                                                                                      |
| Car-lift ride             | an insert or retrieve on a BLift site                                       | Lift edges, BLift bay, lift commands in the action graph                  | SUCCESS                                    | none in the snapshot (the New York layouts are not included)                                              |

### Determinism, and what to compare

Two runs of the same scenario do not produce the same plan calls. Timers in different nodes fire in different orders, service calls are asynchronous, the real time factor stretches planning time differently, the exerciser polls on wall time, and AGVs finish actions at slightly different simulated times. A job that arrives 50 ms later may land in the next plan call. Comparing two runs request by request therefore shows differences even when the scheduler is unchanged.

So the comparison is split. The **scheduler** is compared on identical inputs: the plan calls recorded in one run, replayed offline ([section 9.1](#sm-replay-recorded-plan-calls)). The **system** is compared statistically: outcomes and durations over repeated runs ([section 9.2](#sm-closed-loop-runs)).

## Checking the refactor with the simulator

The simulator supports two checks of the refactor: replaying recorded plan calls through the old and the new scheduler, and running complete scenarios on the candidate. The figure shows how the two fit together, from a one-time recording on the baseline to the checks on each pull request and before each stage is merged.

![Using the simulator to verify the refactor](figures/130_sim_verification_loop.svg)

**Using the simulator to verify the refactor.** Record realistic plan calls once on the baseline; replay them through the old and the new scheduler on every pull request; run the scenarios on the candidate before a stage is merged.

The existing families give a ready-made baseline set: for each Pecos layout, fill from empty and drain from full, run with `record_artifacts:=true` and the exerciser, at a fixed `real_time_factor`. Together with the `550_w21st` batches and `exercise_576_eccles`, that covers three sites, both directions of traffic and garages up to 27 trays.

### Replay recorded plan calls

The scheduler is a function of the request, the time and its parameters (Background tab). A recording from a baseline run holds the requests and the responses; a test can feed each recorded request to the old and the new `Scheduler::Plan` and compare the two results with the canonical comparison of the Verification tab ([section 4](#vr-compare-meaning-not-pointers-or-guids)). This adds to the hand-built fixtures in three ways: the requests are real (states left by earlier jobs, several pending jobs, disabled nodes); there are many of them; and they cover what Dispatch actually sends, including `base_state` fields the fixtures never set.

``` cpp
// PROPOSED — test/replay_plan_calls_tests.cpp (sketch; reads a recording made with record_artifacts:=true)
// layout / params : those of the recorded run (same layout file, bay_readiness_ratio from the scheduler report)
volley::Scheduler old_scheduler(layout_path, logger, params);      // baseline commit, built from a pinned copy
volley::Scheduler new_scheduler(layout_path, logger, params);      // refactor branch: Plan() through the solvers
for(const auto& [stamp, request, recorded] : ReadPlanCalls(bag_path)) {   // pairs matched by request id
  const PlanResponseMsg old_response = old_scheduler.Plan(request, stamp);
  const PlanResponseMsg new_response = new_scheduler.Plan(request, stamp);
  EXPECT_EQ(Canonical(old_response), Canonical(recorded)) << "replay is not faithful";   // sanity check
  EXPECT_EQ(Canonical(new_response), Canonical(old_response)) << "behaviour changed";
}
```

Notes for the test:

- **The old scheduler must run in the same test,** or its canonical outputs must be stored. The simplest route is to compare `new` against `recorded` (the old responses are in the recording already), keeping the old-replay check for the baseline commit only.
- **Time:** `Plan` takes `now`; use the recording's receive stamp of the request in simulated time, the same for both schedulers.
- **Parameters:** `set_bay_readiness_ratio` changes the scheduler between calls, and a scenario's `params:` block may change others. Record the scheduler report, keep the scenario file with the recording, and set the ratio before each replayed call.
- **Canonical form:** compare the action graphs by content and reduced edge sets, and the scheduled jobs by job, never by GUID or index (Verification tab, [section 4](#vr-compare-meaning-not-pointers-or-guids)).
- **Gate:** the pass ratio p over all recorded calls must be 1, exactly as for the fixtures.

Replay is repeatable and needs no running simulation, so it can run in CI on every pull request. The recordings become part of the benchmark set: their requests can be timed with the method of the Verification tab ([section 5](#vr-benchmark-method)).

### Closed-loop runs

Replay checks the scheduler on the baseline's requests only. If the refactor changed a decision, later requests in a live run would differ, and replay alone would not show the consequence. Full simulation runs on the candidate (closed loop: each plan's outcome shapes the next request) check that the system still behaves. For scenario s and run r\in\\1,\ldots,R\\, where R\in\mathbb N is the number of runs, record:

- whether any collision occurred (must be never);
- the exerciser's exit status and the outcome of every job, SUCCESS or ERROR with its error class (must match the baseline runs);
- the makespan M\_{s,r}\in\mathbb R\_{\ge0} \[s\]: simulated time from the scenario start until no job is pending or active;
- for each retrieve, the time from request to hand-over \[s\], and its median W\_{s,r} over the run (the exerciser's CSV has one row per action).

Let \widetilde M_s and \widetilde M_s^{(0)} be the medians of the makespan over the runs of the candidate and of the baseline. The relative change \Delta_s\in\mathbb R is:

\Delta_s=\frac{\widetilde M_s-\widetilde M_s^{(0)}}{\widetilde M_s^{(0)}}.

For a refactor that should not change behaviour, the expected value of \Delta_s is 0; accept it when \|\Delta_s\| stays within the spread of the baseline's own runs, measured beforehand with the same real time factor. The same rule applies to W. A change outside that spread, with the replay passing, points at timing rather than decisions: investigate before merging.

### When to run what

Replay needs no running simulation and can run on every pull request, whereas closed-loop runs need full simulations and are reserved for fewer points. The table assigns the simulation work to each stage of the staged plan, from recording the baseline in stage A to a final closed-loop pass in stages H and I.

| Staged plan stage                           | Simulation work                                                                                                                                               |
|---------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A (baseline)                                | Run the Pecos families, the `550_w21st` batches and `exercise_576_eccles` on the pinned commit; keep the recordings, CSVs and baseline KPIs with the code SHA |
| B2, C0, C1 (renames, folders, pure helpers) | Replay on every pull request                                                                                                                                  |
| C2, D, E (tray module, migration, cleanup)  | Replay on every pull request; closed-loop runs before merging D and E                                                                                         |
| F (AGV module)                              | Same as D and E                                                                                                                                               |
| G (benchmarks)                              | Add the recorded requests to the benchmark set; time them                                                                                                     |
| H, I (cleanup, `planner_core` names)        | Replay and one closed-loop pass of the whole set                                                                                                              |

The stages are those of the Issue & proposal tab ([section 13](#pr-staged-plan)).

## Gaps and proposed improvements

Found while reading the packages. None blocks the refactor; the first four matter most for using the simulator as a test.

- **The Simulator has no pass or fail.** A run ends on a collision or when it is stopped; only the exerciser gives an exit status, and only for the jobs it followed. Proposed: an optional `expect` block in the scenario (jobs that must succeed, a time limit, allowed errors) checked by the Simulator, which then exits with a status code.
- **Some events files use action types the exerciser does not know.** All `*_events_move_each_node` files, `tiny_lot_events_fill` and `events_insert_retrieve` use `wait_for_any_non_busy_agv`, `wait_until_previous_completed`, `wait_for_next_bay_ready_to_insert` or `done_events_wait_jobs_end_simulation`, and fields `sleep` and `time` it ignores. The exerciser stops with "Unknown event type" and status 1. Proposed: convert them (most map to `wait_for_job_completion` and `sleep`), or delete them, and add a test that loads every events file.
- **The standardized batches refer to a missing file.** `pecos_sandbox_eng.yaml` and `pecos_sandbox_qa.yaml` list `*_events_fill_and_drain` three times; no such file is among the scenario files. Proposed: add the file (fill then drain), and a test that every name in a batch configuration resolves.
- **Actions due in the same update run in reverse order.** The Simulator takes the due actions from the back of the list, so the newest runs first. The start files hit this: `set_dispatch_mode` and `set_bay_readiness_ratio` both at 0.5 s fall in the same update. Actions with equal times have no defined order at all. Proposed: process in time order, then in file order.
- **Nothing ties the exerciser to the running simulation.** Its layout argument is not checked, events files do not declare a layout, and an action refused by Dispatch leaves the exerciser waiting without a time limit. Proposed: the five protections of [section 6.4](#sm-mismatch-protection).
- **The patron script prints the wrong id.** `trigger_patron_arrival.bash` prints a UUID from `uuidgen` but sends 16 unrelated random bytes, so the printed UUID cannot be used to retrieve the car. It also uses a height of 3.0 m, above the bay's height-check lidars (1.97 m in `params.yaml`). Proposed: send the printed UUID's bytes, and a realistic height.
- **Service results are not checked by the Simulator.** Most actions are sent without waiting for the answer, so a refused retrieve leaves no trace in the Simulator; the exerciser records a refusal but does not act on it ([section 6.4](#sm-mismatch-protection)). Proposed: count failed answers in `/sim/report`.
- **Battery state is not simulated from the scenario.** `battery_fraction` in `agvs[]` is read but not passed on, and `set_agv_battery_fraction` is logged as not implemented. `charge_then_repark.yaml` depends on both, so it does not test what its comments describe.
- **The exerciser stops every ROS process on the machine.** At the end it sends SIGINT to every process whose command line contains `ros-args`, not only to the simulation it ran against. Proposed: stop only the launch it belongs to.
- **Launch arguments are parsed by hand.** A misspelled argument (`realtime_factor:=4`) is ignored without a warning, and `--show-args` lists nothing. Proposed: declare them as launch arguments.
- **One scenario file, two readers.** The launch file (Python) and the Simulator (C++) each read part of the file; a field one adds can be ignored by the other, as `agvs[].garage_pose` is by the Simulator. Proposed: one schema, checked by a test against every file in `scenarios/`.
- In the Simulator's YAML reader, the `set_auto_planner` case has no `break` and falls into the cases without fields. Harmless today; add the `break`.
- **A collision leaves only a log line** and stops the process (`TODO(SW2-306)`). Proposed: publish the colliding pair, the time and the last snapshot first; with `record_artifacts` the recording then shows the moment.
- **Collision bodies are not published.** The code to build them as messages exists and the visualizer defines a `collision_bodies` topic name, but nothing publishes it. Publishing it would show the boxes in RViz and Foxglove.
- **Start files without set-up actions.** `clean_garage_unstashes_waypoint_tray`, `repark_tray`, `payload_starts_in_bay` and `try_odp_agv_collide_bay_outbound_node` have `events: []`, so Dispatch never starts unless someone starts it. If they are meant for automatic runs, add the four set-up actions of the families.

## Open questions

Answering these needs code or knowledge that is not in the snapshots:

- **Site locations:** are the inferred places of [section 2.1](#sm-where-the-layouts-are) right, and where are `360_w_broadway` and `275_sunrise_b`?
- **The Pecos file name:** this pack's layout file is `5675_pecos_combined.yaml`; the scenarios use `5675_pecos_sandbox_combined`. Are they the same file, renamed?
- **Batch runner:** which program reads `batch_configs/`, and where are its results stored?
- **Older events files:** does another tool (for example `system_tests`, a dependency of `sim`) still read the action types the exerciser rejects?
- **Manual confirmation:** when an insert is confirmed through the REST API with its own `payload_id`, which id does the parked car get: the patron's or the confirmation's?
- **Bay readiness after a retrieve:** with `bay_readiness_ratio` 0.0, does the empty tray a retrieve leaves in the bay make the bay ready to insert?
- **Sensor box on layouts without installation parameters:** `550_w21st`, `275_sunrise_b`, `tiny_lot` and `multisize` run with the default 4.5 m × 2.0 m box. Does the vehicle estimator reject a longer simulated car, and does it matter for those scenarios?
- **The simulated AGV:** does it use the speeds, lift and wheel-turn times of `params.yaml` as the cost model does, and does it model battery drain?
- **GUID bytes:** the order in which a GUID string maps to its 16 bytes (`ParseGuid` in `common`), needed to type ids by hand.
- **Topic names:** the exact names of the plan request and response topics, needed by the replay test.

## Evidence limits

This tab is based on `sources/repomix-sim.xml` (the `sim` package without its tests, scenario files and 3D models), `sources/repomix-vis.xml`, `sources/repomix-launcher.xml` (launch files, `launcher/*.py`, all parameter files), `sources/repomix-scenario.xml` (the `scenario` package filtered to the Pecos files, the named behaviour scenarios, the event runner and the batch configurations; the `275_sunrise_b` files, the other per-site files and the GUID readme were left out), and `sources/5675_pecos_combined.yaml`, with the `central`, `scheduler` and `interfaces` snapshots for the services and messages. The `agvhito`, `bay`, `vecs`, `vrc`, `central_api`, `sim_metrics`, `common` and `system_tests` packages, and the layout files other than Pecos, are not included; statements about them come from call sites and scripts. The site locations are inferences from the layout names, checked against the public sources linked in [section 2.1](#sm-where-the-layouts-are). The recipes are built from the code and scripts and were not run. The scenario and events files of [section 5.5](#sm-a-scenario-for-the-running-example) and of the recipes, the replay test, the KPI rule and the improvements are proposals.
