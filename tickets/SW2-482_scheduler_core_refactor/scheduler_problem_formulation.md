# The scheduler as a multi-agent planning problem: a solver-agnostic formulation (draft for review)

Status: draft, 2026-11-08. Nothing implemented. Code references are to
`jmg/SW2-905/insert-stall-blocked-by-agv` at `a38e7eb8`. Literature citations are from memory and
not yet checked against the papers; verify them before quoting.

## 1. Purpose

Describe what the scheduler solves in the vocabulary of the multi-agent path finding (MAPF)
literature, as a fixed **problem instance** that any solver can read. Goals:

- separate *what is asked* (the instance) from *how it is solved* (the solver) and *how it is run*
  (the execution graph);
- make solvers swappable behind one interface, today's pipeline being the first;
- turn the recorded scenario files into a benchmark that any solver can be run against.

This is complementary to `ordered_plan_prototype/`: that proposal simplifies the inside of
today's solver; this one defines the boundary around it. Recommended order: boundary first.

## 2. Why the event DAG is not the right interface

`ScheduleEventDag` (`planner_core/event_dag.hpp`) carries three different things at once:

| Role | Examples in the DAG today | Where it belongs |
|---|---|---|
| **Problem constraints** | job order (`OrderAfterJobLeafEvents`), "bay ready before the tray enters", "stop charging before the tray leaves the VECS" | the instance, as precedence constraints |
| **Solver decisions** | which empty tray, which stall, which AGV, freeing moves, AGV evictions, lift ordering | inside the solver |
| **Execution dependencies** | "this action may start once those finish" | the solution's execution graph (the action graph, an ADG) |

The literature keeps these apart. A MAPF paper's input is a graph, agents, goals and constraints.
Its output is a timed plan per agent. A temporal plan graph or action dependency graph (TPG/ADG;
Hönig et al. 2016, 2019) is built *from* the output for robust execution. Volley already builds
that last graph (`action_graph.cpp`; background in `volley_notes/research/action_dependency_graph/`).
Only the first two roles need untangling.

## 3. Related problem settings

| Setting | Adds over plain MAPF | Maps to |
|---|---|---|
| MAPF (Stern et al., SoCS 2019, definitions and benchmarks) | agents, start, goal, conflicts | AGV routing (Chugg) |
| TAPF / CBS-TA (Ma & Koenig, AAMAS 2016; Hönig et al., AAMAS 2018) | the solver assigns goals to agents | choosing the AGV, the stall |
| MAPD (Ma et al., AAMAS 2017) | tasks are pickup then delivery; agents carry objects | tray moves |
| MAPF with precedence-constrained goal sequences, MAPF-PC (Zhang, Chen, Li, Williams, Koenig, AAMAS 2022) | goal sequences per agent, "goal A before goal B" across agents; CBS-PC, PBS-PC | job ordering, devices before moves |
| Multi-agent task assignment with precedence (e.g. Brown et al., ICRA 2020, assembly planning) | task allocation plus routing under precedence | the whole pipeline, coarse |
| MAPF for large agents (Li et al., AAAI 2019); SIPP and its variants | footprints instead of cells; continuous time | the collision table, Chugg |
| Puzzle-based storage (Gue & Kim, 2007); rearrangement and navigation among movable obstacles | objects block other objects and must be moved first | freeing moves, AGV eviction |
| Lifelong MAPD | tasks arrive over time; committed plans stay fixed | the base schedule, replanning |

Closest single fit: **MAPD with goal sets and precedence constraints (MAPD-PC)**, preceded by
a **rearrangement** step that the standard settings do not have.

## 4. The instance

Informal definition, then a data sketch. Names are placeholders.

### 4.1 Elements

- **Map.** The motion graph (poses: node plus heading; edges with durations) and a **conflict
  relation**: two (entity footprint, pose) pairs conflict if they overlap (today's collision
  table). The relation also covers swept volumes along edges.
- **Agents.** AGVs: start pose, enabled or not, loaded or not, battery. Traversable poses depend on
  load state (today's keep-out filters per footprint).
- **Objects.** Trays (pose, payload or empty), payloads (on a tray, EV or not, preferred heading).
  Objects move only when an agent carries them.
- **Devices.** Bays, VECS chargers and VRCs: fixed position, a state machine, a duration per
  transition. A device's state can gate poses: a bay's inbound pose is passable only in some
  states (`static_graph_filtering.cpp:98`).
- **Goals.** One of:
  - `AgentAt(agv, poses)`: the AGV ends at one of the poses;
  - `ObjectAt(tray | payload | "any empty tray", poses)`: the object ends at one of the poses;
    needs a carrier;
  - `DeviceIn(device, state)`: the device reaches the state (a transition).

  A **pose set** expresses choice: "any free stall", "either heading" (`allow_reciprocal`),
  "any bay that can retrieve". The solver picks one.
- **Tasks.** One per job: an ordered sequence of goals, plus a job index and a priority. The
  sequence's order is within-task precedence.
- **Precedence constraints.** `finish(A) <= start(B)` between goals, within and across tasks, each
  with a reason. Job order is one source of these, device prerequisites another.
- **Reservations.** Resources the base schedule has committed: AGVs, nodes, bays and VECS
  unavailable (today's `ExcludeCommittedResources`, `scheduler.cpp:31`). In lifelong terms,
  these are fixed prefixes of other agents' plans.
- **Objective.** To decide in review. Candidates: makespan, sum of task completion times, retrieve
  latency (time to bay arrival, already reported as `seconds_to_bay_arrival`), with the number of
  extra moves as a tie-break.

### 4.2 Data sketch

```cpp
namespace volley::planning {

using PoseSet = std::vector<GaragePose>;          // one pose = a fixed goal; several = a choice

struct AgentAt  { uint16_t agv_id; PoseSet poses; };
struct ObjectAt { ObjectRef object; PoseSet poses; };   // tray id, payload id, or "any empty tray"
struct DeviceIn { DeviceRef device; uint8_t state; };   // bay, VECS or VRC state
using Goal = std::variant<AgentAt, ObjectAt, DeviceIn>;

struct GoalId { size_t task; size_t index; };
struct Task { Guid job; size_t job_index; std::vector<Goal> goals; };   // goals in order
struct Precedence { GoalId before; GoalId after; Reason reason; };

struct Instance {
  const World& world;                       // map, conflict relation, durations (services, not data)
  DiscreteGarageState initial_state;        // agents, objects, devices
  std::vector<Task> tasks;
  std::vector<Precedence> precedences;      // across tasks; within-task order is implicit
  Reservations reservations;                // from the base schedule
  Objective objective;
};

struct Solution {
  std::vector<AgentPlan> agent_plans;       // timed actions per AGV: move, lift, lower, wait
  std::vector<DevicePlan> device_plans;     // timed transitions per device
  std::vector<GoalBinding> bindings;        // which pose of each set, which tray for "any empty"
  std::vector<Task> added_tasks;            // tasks the solver created (freeing, eviction)
};

class Solver {
 public:
  virtual ~Solver() = default;
  [[nodiscard]] virtual stdx::Expected<Solution> Solve(const Instance& instance) const = 0;
};

}  // namespace volley::planning
```

The action graph for the executor is built from `Solution` by one function, solver-independent,
the way an ADG is built from a MAPF solution.

## 5. Today's jobs as tasks

From `SchedulerJob.msg` and `job_expansion.cpp`. This is what expansion would produce instead of
events. Rows marked *(check)* were read quickly and need confirming.

| Job | Goal sequence | Choices (pose sets) |
|---|---|---|
| `MOVE_AGV` | `AgentAt(agv, dest)` | reciprocal heading if allowed |
| `MOVE_TRAY` | `ObjectAt(tray, dest)` | dest if unset; heading |
| `INSERT` (bay) | `DeviceIn(bay, READY_TO_RETRIEVE)` if needed, then `ObjectAt(tray in bay, stalls)` | which stall; a separate request resets the bay to insert |
| `RETRIEVE` (payload) | `DeviceIn(vecs, stop)` if on a charger; `DeviceIn(bay, READY_TO_RETRIEVE)` if needed; clear the bay (`ObjectAt(tray in bay, stalls)`); `ObjectAt(payload's tray, bay inbound)`; `DeviceIn(bay, PROCESS_RETRIEVE)` | **which bay** (today chosen during expansion, `FindBayForRetrieve`); heading by `reciprocal_to_tray` |
| `REPARK_TRAY` | `ObjectAt(tray, stalls)` | stall, heading |
| `READY_FOR_INSERT` (bay) | charge or clear the tray in the bay; `ObjectAt(any empty tray, bay)`; `DeviceIn(bay, TRANSITION_TO_INSERT)` *(check)* | which empty tray |
| `READY_FOR_RETRIEVE` (bay) | `DeviceIn(bay, READY_TO_RETRIEVE)`; charge or clear the tray in the bay *(check)* | |
| `TRANSITION_BAY_TO_INSERT` / `_TO_RETRIEVE` | `DeviceIn(bay, state)` | |
| `CHARGE_AGV` | `AgentAt(agv, chargers)`; `DeviceIn(vecs, start)` *(check)* | which charger |
| `CHARGE_PAYLOAD` | `ObjectAt(payload's tray, EV stalls)`; `DeviceIn(vecs, start)` *(check)* | which charging stall |
| `CLEAN_GARAGE` | for each AGV, `AgentAt(agv, hiding spots)`; trays out of bays to stalls | which hiding spot |
| `REBALANCE_GARAGE` | `READY_FOR_INSERT` / `READY_FOR_RETRIEVE` tasks per bay | as those |

Notable: today expansion **already decides** some choices (bay for a retrieve, a heading) against a
working state that includes earlier jobs' events. In the formulation those are pose sets and
belong to the solver. Solver #1 can keep deciding them in the same place and order.

## 6. Where Volley departs from the standard settings

1. **Tasks created by blockage.** A tray behind other trays, or a stall overlapped by an AGV on a
   charger, needs moves that no job asked for. Standard MAPD has a fixed task set. Model: the
   solver may return `added_tasks`; or a separate **rearrangement layer** turns the instance
   into one where every goal is reachable once its precedences hold (§7).
2. **Objects only move when carried, and carrying changes the agent.** A loaded AGV has a
   different footprint and traversable set. Standard MAPD treats carrying as free. Model: agent
   state `loaded` selects the footprint in the conflict relation.
3. **Devices with state machines.** Modelled as goals on immobile resources with durations, plus
   pose gating (a device state makes poses passable or not). MAPF-PC covers the precedence part,
   not the gating; the gating is part of the world model.
4. **Persistent vs transient occupancy.** A parked AGV or a stationary tray blocks a pose until it
   moves; that is a precedence ("after X leaves"). Two AGVs crossing is a timing conflict, left to
   the router. Mixing the two serialises motion (the bay-transition vs carrier-approach example,
   14 s).
5. **Footprints.** Large, heterogeneous footprints and a precomputed conflict table, not grid
   cells. Covered by large-agent MAPF and SIPP-style planners such as Chugg.
6. **Replanning on top of a committed schedule.** Reservations, as in lifelong MAPD.

## 7. Layered solving

```
Request ──► Instance (§4)                          solver-independent
              │
              ├─► Rearrangement: add freeing and eviction tasks, bind blocked goals
              │     ──► Instance' where the task set is final       (Volley-specific)
              │
              ├─► Assignment and routing (swappable)                 (textbook-shaped)
              │     today's pipeline | CBS-TA | PBS-PC | greedy + LNS | ...
              │
              └─► Solution ──► execution graph (ADG) ──► dispatcher  (exists today)
```

- **Solver #1 is today's scheduler**, wrapped. Expansion builds events from the instance's
  tasks; tray assignment, AGV assignment and Chugg run as now; an adapter turns the result into a
  `Solution`. The event DAG becomes an internal detail of solver #1. Recordings stay identical.
- **The rearrangement split is a real trade-off.** Separating "which extra moves" from "who does
  them, when" loses optimality where they interact (an AGV evicted from a charger and then chosen
  as carrier makes a pointless trip). Today's pipeline already makes this split. A later solver
  could merge the two layers.
- **What becomes swappable in practice** is mainly the second layer: assignment and routing,
  given a final task set. CBS-TA or PBS-PC run end to end on raw Volley instances would fail,
  because they neither create tasks nor model blocking objects.

## 8. How this connects to existing work

- **SW2-484's tray-assignment solver** (`PROMPT.md`, `solver.hpp` sketch): its
  `Input{initial_state, steps}` with `MoveRequest` (optional tray, optional destination) and
  `StateChange` is a narrow version of this instance: `ObjectAt` goals with pose sets, and
  `DeviceIn` goals. Its `Result{fills, new_moves, edges}` is bindings, added tasks and precedences.
  The formulation generalises it to the whole scheduler; SW2-484 can adopt the vocabulary without
  waiting for the rest.
- **The ordered-plan proposal** (`ordered_plan_prototype/`) simplifies solver #1's inside and is
  independent of this boundary.
- **Scenario files** (SW2-1126) already hold an initial state, a request and the expected output.
  With an instance format they become a benchmark for any solver: success, makespan, extra
  moves, planning time.
- **The action graph** stays the execution format; the dispatcher does not change.

## 9. Migration, each step behaviour-preserving

1. Define `Instance`, `Task`, `Goal`, `Precedence`, `Solution` as plain data, with YAML in the
   scenario files' style.
2. Build `Instance` from a planning request (one function; today's job validation moves here).
3. Wrap today's pipeline as `LegacySolver`: tasks to events, run, events to `Solution`. Build the
   action graph from `Solution`. All recordings identical.
4. Move expansion's choices (bay for a retrieve, headings) behind pose sets, still decided by
   solver #1 in the same order. Recordings identical.
5. Split out the rearrangement layer from tray assignment as its own stage with the instance in
   and out.
6. Add a second solver for layer 2 (a greedy MAPD-PC baseline first, then e.g. PBS-PC) and
   compare on the scenario benchmark.

## 10. Open questions for review

1. **Objective.** Makespan, sum of completion times, retrieve latency, or a weighted mix? The
   current pipeline optimises none explicitly (bottleneck assignment per frontier, greedy
   elsewhere).
2. **Is the rearrangement layer part of the instance or of the solver?** Proposed: of the solver,
   with a standard layer that solvers may reuse.
3. **Granularity of goals.** Do lifts and lowers, VRC rides and bay sub-steps appear as goals, or
   only in agent plans? Proposed: only in plans.
4. **Device pose gating.** Part of the world model (a function of device state), or explicit
   precedences generated per instance? Proposed: world model.
5. **Failure semantics.** Today a job can fail alone (expansion rolls it back) or fail the whole
   plan. Should `Solution` report per-task failure, with retryable or not, as `ScheduledJob` does?
6. **Time model.** Discrete steps, or continuous with durations as Chugg uses? Proposed:
   continuous; discretised solvers convert.
7. **Where pose-set choices are made in solver #1.** Expansion (as now) or tray assignment? Affects
   step 4.

## 11. References (verify before citing)

- R. Stern et al., "Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks", SoCS 2019.
- H. Ma, S. Koenig, "Optimal Target Assignment and Path Finding for Teams of Agents", AAMAS 2016.
- H. Ma, J. Li, T. K. S. Kumar, S. Koenig, "Lifelong Multi-Agent Path Finding for Online Pickup and
  Delivery Tasks", AAMAS 2017.
- W. Hönig et al., "Conflict-Based Search with Optimal Task Assignment", AAMAS 2018.
- W. Hönig et al., "Multi-Agent Path Finding with Kinematic Constraints", ICAPS 2016 (temporal
  plan graph).
- W. Hönig et al., "Persistent and Robust Execution of MAPF Schedules in Warehouses", RA-L 2019
  (action dependency graph).
- H. Zhang, J. Chen, J. Li, B. Williams, S. Koenig, "Multi-Agent Path Finding for
  Precedence-Constrained Goal Sequences", AAMAS 2022.
- J. Li et al., "Multi-Agent Path Finding for Large Agents", AAAI 2019.
- K. Brown et al., "Optimal Sequential Task Assignment and Path Finding for Multi-Agent Robotic
  Assembly Planning", ICRA 2020.
- K. R. Gue, B. S. Kim, "Puzzle-Based Storage Systems", Naval Research Logistics, 2007.
- M. Phillips, M. Likhachev, "SIPP: Safe Interval Path Planning for Dynamic Environments", ICRA
  2011.
