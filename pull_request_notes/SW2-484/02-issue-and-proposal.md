# 02 — SW2 Scheduler Core Refactor: problem statement and proposal

## 1. Ticket and scope

**Parent Jira initiative:** **Scheduler Core Refactor** (parent key not provided in the supplied ticket text). **Specific tasks:** [SW2-484](https://volleyautomation.atlassian.net/browse/SW2-484) (tray solver interface, in progress), [SW2-769](https://volleyautomation.atlassian.net/browse/SW2-769) (scheduler package reorganization, marked done), and [SW2-487](https://volleyautomation.atlassian.net/browse/SW2-487) (tray benchmark set, To Do). These links follow conventional Jira URL patterns; the base-domain resolution and current issue status have not been independently verified. Related issue keys reported by the user include SW2-677, SW2-652, SW2-593, SW2-488, SW2-496, SW2-514, SW2-663, SW2-18, SW2-686, SW2-776, and SW2-905; **do not infer that all are refactor blockers**.

**Objective:** move tray-move planning and AGV assignment from large `Scheduler` methods into generic, swappable interfaces, with default implementations reproducing current behavior and at least **10 real-customer-layout scenarios per solver** with recorded baseline performance. **Out of scope:** modifications to CHUGG/SIPP motion planning, implementing a new optimal solver, and adding to active schedules.

**Definition of Done:** two generic interfaces; two behavior-equivalent default implementations; 10+ site-based benchmark scenarios each and saved baselines; all Scheduler assignment call sites routed through the interfaces; old code paths removed. Source: user-provided Jira issue text, October 2026. This is the intended state, not current implementation.

## 2. Current technical problem

`Scheduler` currently owns both `DoTrayAssignments(ScheduleContextSPtr)` and `DoAgvAssignments(ScheduleContextSPtr)` and many of their helper methods. The algorithms directly access internal `GarageGraph`, `CollisionTable`, `MotionCostModel`, `Layout`, and logging state. They also mutate the shared `ScheduleContext` graph and event objects. This makes algorithm replacement expensive: a new implementation must effectively integrate with a large orchestration class, and benchmark harnesses tend to instantiate full `Scheduler` instead of a narrow independent solver.

Source anchors: `scheduler.hpp` declarations (`DoTrayAssignments`, `DoAgvAssignments`, helper sections, `ScheduleContext`); `scheduler.cpp` function definitions and `Scheduler::Plan` integration. The uploaded snapshot includes a pre-refactor code path, but may not reflect later commits.

**Conceptual target:**

![Target design](figures/02_target_architecture.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#02_target_architecture) · [standalone SVG](figures/02_target_architecture.svg)</sub>

**Figure 2 — Proposed architecture.** Solver contracts separate policy from orchestration; concrete default solvers may still depend on graph, collision, and cost services, injected by `const` reference at construction. Both solvers mutate the `planner_core` event DAG through their request. This is a proposed design, not an implementation already present.

## 3. Current versus target responsibilities

| Concern | Existing owner | Proposed owner |
|---|---|---|
| Validate incoming garage and job request | `Scheduler::Plan` | Stay in `Scheduler` |
| Expand jobs into initial events | `Plan*Job` methods | Stay in Scheduler/job-planning layer initially |
| Choose tray and destination | `DoTrayAssignments` | `DefaultTrayMoveSolver` |
| Find blocking trays and schedule relocation | `DoTrayAssignments` / `ResolveBlockingTrays` | Default tray solver or injected blocking-search collaborator |
| Select AGV and inject lift/reposition events | `DoAgvAssignments` | `DefaultAgvAssignmentSolver` |
| Store generic event DAG primitives | `planner_core` | Remain in `planner_core` |
| DAG reduction/sanity checking and trajectory planning | `Scheduler::Plan`, other methods | Stay put in initial refactor |

**Decision needed:** whether the new `TrayMoveSolver` *contract* is placed in `planner_core`, a distinct small solver-interface package, or a new scheduler-core package. `planner_core` currently declares it depends on **no other planner group package**, so moving a default implementation with `motion_planner` dependencies into it is not automatically a good idea. Package placement must be checked against actual CMake dependency export behavior.

## 4. Proposed interface (design sketch, not compile-ready)

A low-risk first step is a mutation-based contract that narrows access without immediately inventing a separate planning domain model:

```cpp
namespace volley {
struct TraySolveRequest {
  const DiscreteGarageState& initial_state;
  ScheduleEventDag& events;
  std::unordered_map<uint16_t, ScheduleEventSPtr>& first_tray_event;
};

class TrayMoveSolver {
 public:
  virtual ~TrayMoveSolver() = default;
  virtual BoolStringPair Solve(TraySolveRequest request) const = 0;
};
}  // namespace volley
```

Here `TraySolveRequest` is just a conceptual name: test and refine exact namespace, ownership/lifetime rules, and logging/environment dependencies. Passing references signals which fields a solver is allowed to mutate; the request structure should not blindly expose the entire `ScheduleContext`. The default concrete implementation could receive `const GarageGraph&`, `const CollisionTable&`, a motion-cost collaborator, and a logging collaborator at construction. **Lifetime requirements** must be explicit because the solver would retain references to Scheduler-owned objects.

For AGV assignment, use an analogous contract that receives the same DAG, an initial state, the `first_tray_event` mapping, and the required filters/time parameters. Avoid designing it entirely until the full AGV helper call graph has been separated into assignment policy, cost estimation, event expansion, and path/arrival repair responsibilities.

A second approach is an immutable request and returned `SolveResult` containing the resulting DAG and metadata. That is a cleaner abstract contract but currently harder because `ScheduleEventDag` contains shared event pointers and a shallow copy aliases event objects; copying the DAG alone does **not** isolate mutations such as `TrayMove::SetDest` or `SetAgvId`. A correct transactional result may require deep cloning and stable event identity. **Recommendation:** preserve mutation semantics in the first parity pass; evaluate immutable results afterward.

## 5. Key invariants to maintain

1. Every output `TrayMove` selected for actual execution has a resolved tray ID and destination.
2. The DAG stays acyclic; every prerequisite path remains valid after expansion.
3. The per-tray event chain preserves physical move order and the first clearing event remains available for downstream AGV planning.
4. Generated blocking-tray moves are performed in recursive prerequisite order; no inadvertent oscillation through repeated prior destinations.
5. AGV matches respect disabled state, bay trapping, reachability, collision constraints, lift state, and already occupied AGVs.
6. AGV arrival ordering prevents two AGVs from occupying an incompatible node state at the same execution point.
7. No change to public `Scheduler::Plan` observable results, barring controlled nondeterminism/diagnostics.
8. DAG reduction and path-repair placement remain behavior-equivalent; do not move them opportunistically during initial extraction.

The sequential tray move example in the SVG is illustrative; the concrete graph and valid path depend on each layout:

![Garage setup](figures/03_garage_xy.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#03_garage_xy) · [standalone SVG](figures/03_garage_xy.svg)</sub>

**Figure 3 — Top-down garage setup.** AGV 1 faces the positive $x$ direction and carries tray T1 toward the goal. Trays T2 and T3 lie along the illustrative route, so two prerequisite tray moves (T2 → S3, T3 → S4) must complete first; they are independent of each other. Coordinates are schematic; node IDs and distances are not an actual customer layout.

## 6. Why the first change should be small

A move-only refactor is risky because method bodies invoke member helpers such as `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove`, `ResolveBlockingTrays`, `UseEvChargeHeading`, and various cost/occupancy utilities. Some of these are used by ordinary job planning. Blindly relocating them will either break existing clients or recreate `Scheduler` coupling through a back-pointer.

**Recommended staged engineering plan:**

| Stage | Change | Exit criterion |
|---|---|---|
| A — baseline | Pin commit SHA, build and run existing scheduler tests, record output DAGs for curated fixtures | Reproducible existing behavior captured |
| B — dependency map | Record direct member fields/helpers used by both algorithms; identify external helper consumers | Compile-time/ownership design documented |
| C — tray interface | Introduce interface, default implementation, narrow injectable environment | Unit tests can construct solver directly |
| D — tray migration | Make `Scheduler::Plan` call the solver; temporarily retain parity adapter while comparing | Existing tests and graph snapshots equivalent |
| E — tray cleanup | Move only needed helpers and remove old public path after tests are adapted | No production calls to old method |
| F — AGV interface | Repeat for AGV assignment, including cost estimators and path constraints | Same behavior and integration coverage |
| G — benchmarks | >=10 real-site scenarios for each solver, baseline timing under pinned environment | Results stored with metadata and no regressions |
| H — final cleanup | Remove legacy implementations, run full system/advanced suites | All Definition of Done items demonstrable |

**Ticket mapping:** SW2-769 package structure should be checked against the actual branch; SW2-484 is the logical first active implementation; SW2-487 should start in parallel as soon as baseline capture can be made deterministic. Distinct AGV tickets were not identified in user-provided child items; avoid inventing their keys.

## 7. Important decisions to resolve during review

| Decision | Initial recommendation | Required evidence |
|---|---|---|
| API: input/output | Mutable restricted context for parity | DAG shared-pointer aliasing, failure mutation behavior |
| Virtual interface vs templates | Virtual `Solve` with `std::unique_ptr` ownership by Scheduler | Existing style, ABI boundary, plugin replacement needs |
| Where interface lives | Shared low-dependency header | `colcon graph` / `package.xml` and CMake transitive deps |
| Where concrete algorithms live | Solver implementation package or Scheduler library submodule | Motion/search dependencies, avoiding group-level dependency cycles |
| Benchmarks | Direct solver benchmark, optional end-to-end Plan benchmark | Exact fixtures and performance harness |
| What equals “same results” | Compare semantic assignments, event order constraints, final state, errors | Stable event identifiers and tie-breakers |

## 8. Risks and issues that must not be silently 'fixed'

- The AGV occupied-time function currently returns zero and is marked TODO; modifying this during refactor changes behavior.
- `DoTrayAssignments` intentionally postpones DAG reduction; moving reduction forward is high risk.
- `TrayMove::Apply` has permissive behavior when tray or destination is absent, including state mutation on untargeted moves. Tightening it during extraction would not be a pure refactor.
- `ScheduleEventDag` uses pointer identity and Boost vertex indexes. `Remove` can shift indexes, so do not assume vertex descriptors persist across removals.
- Existence of test labels such as `576_eccles_half`, `tiny_lot`, and `triple_pick_lot` does not by itself prove that a benchmark uses a real customer layout. Evidence must be recorded.
- The parent ticket includes SW2-905 (insert failing when AGV collides with selected parking node), but severity and prioritization do not prove it is caused by this refactor.

## 9. Next implementation actions

Run `colcon test --packages-select planner_core scheduler scheduler_advanced_tests` after the relevant packages have been built in the ROS container, then `colcon test-result --verbose` to capture a baseline. Verify branch/package state before editing; isolate edits behind reviewable commits. Generate a focused symbol use map with `rg -n 'ResolveBlockingTrays|DoTrayAssignments|DoAgvAssignments|first_tray_event|BottleneckAssignment' src/planner`, and inspect helper implementations before moving them.

## 10. Proposed UML and method sequence

![Solver UML](figures/08_uml_solver.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#08_uml_solver) · [standalone SVG](figures/08_uml_solver.svg)</sub>

**Figure 8 — Proposed UML class structure.** `Scheduler` holds a `TrayMoveSolver` and creates the `TraySolveRequest` it passes in; `DefaultTrayMoveSolver` and a test double realize the interface. The reference-based ownership shown is one possible first-pass design.

The design uses the **Strategy** pattern: `Scheduler` calls a stable solver interface without embedding the concrete algorithm. The relationship from `DefaultTrayMoveSolver` to `TrayMoveSolver` is interface realization (dashed line with hollow triangle). A test fake can implement the same interface.

![Solver call sequence](figures/09_sequence_tray.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#09_sequence_tray) · [standalone SVG](figures/09_sequence_tray.svg)</sub>

**Figure 9 — Proposed tray solver interaction.** The Scheduler delegates to the solver, which reads the topological event order, fills tray IDs and destinations, inserts blocker moves and dependencies into the event DAG when a route is blocked, records `first_tray_event`, and returns a success flag with a diagnostic. AGV assignment then continues in the Scheduler.

### C++ contract and calling code (proposed)

```cpp
struct TraySolveRequest {
  const DiscreteGarageState& initial_state;
  ScheduleEventDag& events;
  std::unordered_map<uint16_t, ScheduleEventSPtr>& first_tray_event;
};

class TrayMoveSolver {
 public:
  virtual ~TrayMoveSolver() = default;
  virtual BoolStringPair Solve(TraySolveRequest request) const = 0;
};

// Illustrative Scheduler integration after dependency injection:
TraySolveRequest request{ctx->initial_state, ctx->events,
                         ctx->first_tray_event};
auto [success, diagnostic] = tray_solver_->Solve(request);
```

These names and signatures are *proposals*, not existing repository declarations. The `const` reference to `initial_state` prevents changing the initial state through this argument, whereas the DAG and first-tray-event map are intentionally mutable. Alternative implementations can reuse the same contract, but an algorithm that needs different environment services will require constructor injection or a revised request representation.

### Representative current algorithm fragment (from `DoTrayAssignments`)

```cpp
auto working_state = ctx->initial_state;
auto total_ordering_opt = ctx->events.GetTopologicalOrdering();
if(!total_ordering_opt.has_value()) {
  return std::make_pair(false, "Failed to get total ordering");
}

volley::GarageOccupancyChecker<
    std::shared_ptr<volley::ScheduleEvent>> freeing_moves(table_, gg_);
```

This fragment demonstrates why a default implementation needs graph and collision dependencies and why the algorithm's mutable working state should not be confused with the immutable initial state.
