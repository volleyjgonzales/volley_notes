# 02 — Scheduler Core Refactor: problem statement and proposal

This document explains *what* the refactor changes and *why*, using the code in `sources/repomix-scheduler.xml` as evidence. It assumes you have read sections 7–10, 13 and 16–17 of [01 — Software background](01-software-background.md). Code snippets follow the same conventions as doc 01: every snippet says which class it lives in, what `this` is, and the type of each variable that is not obvious. Snippets marked **proposed** do not exist in the repository.

| Name in snippets | Type | What it is |
|---|---|---|
| `this` inside `Scheduler::…` | `const volley::Scheduler*` | The one `Scheduler` object, owned by `SchedulerRos` through `SchedulerSPtr` (`std::shared_ptr<Scheduler>`) |
| `plan_ctx`, `ctx` | `ScheduleContextSPtr` = `std::shared_ptr<ScheduleContext>` | Per-`Plan()` scratch state: initial state, event DAG, job list, bookkeeping maps |
| `ctx->events` | `volley::ScheduleEventDag` | The event DAG being built (Boost graph of `std::shared_ptr<ScheduleEvent>`) |
| `ctx->initial_state` | `volley::DiscreteGarageState` | Snapshot of the garage at request time; never mutated after `Plan()` builds it |
| `working_state` | `volley::DiscreteGarageState` (local copy) | `initial_state` with already-planned events applied, used to answer "where is everything *now*?" |
| `gg_`, `table_`, `cost_model_`, `layout_`, `logger_` | `GarageGraph`, `CollisionTable`, `cost::MotionCostModel`, `LayoutSPtr`, `rclcpp::Logger` | `Scheduler` data members built once in the constructor |
| `stdx::Expected<T>`, `stdx::Result` | `tl::expected<T, std::string>`, `tl::expected<void, std::string>` (from the `stdx` package) | A value or an error message; `Result` is success or an error. Proposed replacement for `BoolStringPair` (section 6.4) |
| `svc` | `const common::GarageServices&` (**proposed**) | Bundle of const references to `gg_`, `table_`, `cost_model_`, `*layout_` plus the logger, passed to every pure helper (section 6.1) |

## Contents

<!-- toc -->
- [1. Ticket and scope](#1-ticket-and-scope)
- [2. Where the two algorithms sit today](#2-where-the-two-algorithms-sit-today)
- [3. What the two algorithms touch](#3-what-the-two-algorithms-touch)
- [4. Current versus target responsibilities](#4-current-versus-target-responsibilities)
- [5. Target architecture](#5-target-architecture)
- [6. Proposed layout and API for tray assignment](#6-proposed-layout-and-api-for-tray-assignment)
- [7. Key invariants to maintain](#7-key-invariants-to-maintain)
- [8. Staged plan](#8-staged-plan)
- [9. Decisions to resolve in review](#9-decisions-to-resolve-in-review)
- [10. Risks that must not be silently "fixed"](#10-risks-that-must-not-be-silently-fixed)
- [11. Next actions](#11-next-actions)
<!-- /toc -->

## 1. Ticket and scope

**Parent Jira initiative:** **Scheduler Core Refactor** (parent key not given in the supplied ticket text). **Specific tasks:** [SW2-484](https://volleyautomation.atlassian.net/browse/SW2-484) (tray solver interface, in progress), [SW2-769](https://volleyautomation.atlassian.net/browse/SW2-769) (scheduler package reorganization, marked done) and [SW2-487](https://volleyautomation.atlassian.net/browse/SW2-487) (tray benchmark set, To Do). The links follow the usual Jira URL pattern; the base domain and current status have not been verified. Related keys reported by the user: SW2-677, SW2-652, SW2-593, SW2-488, SW2-496, SW2-514, SW2-663, SW2-18, SW2-686, SW2-776 and SW2-905. **Do not assume all of them block the refactor.**

**Objective:** move tray-move planning and AGV assignment out of large `Scheduler` methods and behind generic, swappable interfaces. Default implementations must reproduce current behaviour, and each solver needs at least **10 real-customer-layout scenarios** with recorded baseline performance. **Out of scope:** changes to CHUGG/SIPP motion planning, a new optimal solver, and adding to active schedules.

**Definition of Done:** two generic interfaces; two behaviour-equivalent default implementations; 10+ site-based benchmark scenarios per solver with saved baselines; every `Scheduler` assignment call site routed through the interfaces; old code paths removed. Source: user-provided Jira text, October 2026. This describes the intended state, not the code today.

## 2. Where the two algorithms sit today

Both algorithms are `const` member functions of `Scheduler` that take the per-call context and edit it in place. They return `BoolStringPair` (`std::pair<bool, std::string>`: success flag plus a message). Section 6 proposes replacing both habits: `stdx::Expected` instead of `BoolStringPair`, and a returned result instead of editing `ctx`.

```cpp
// include/scheduler/scheduler.hpp — inside class volley::Scheduler (public section)
BoolStringPair DoTrayAssignments(ScheduleContextSPtr ctx) const;  // fills tray ids + destinations, adds blocker moves
BoolStringPair DoAgvAssignments(ScheduleContextSPtr ctx) const;   // picks AGVs, adds approach/lift/lower events
```

`const` here only means the methods do not change `Scheduler`'s own members. The real output is the mutation of `*ctx`, which the `shared_ptr` lets them reach. They are called from the middle of `Scheduler::Plan`:

```cpp
// src/scheduler.cpp — PlanResponseMsg Scheduler::Plan(const PlanRequestMsg& request_data, const rclcpp::Time& now) const
// this     : const Scheduler*  (the Scheduler that SchedulerRos owns)
// plan_ctx : ScheduleContextSPtr, created earlier in Plan() from the request's garage state
// result   : PlanResponseMsg being built; result.scheduled_jobs is std::vector<ScheduledJobDataMsg>
//   ...every pending job has already been expanded into events by a Plan<Type>Job method...

auto [success, message] = DoTrayAssignments(plan_ctx);   // same as this->DoTrayAssignments(plan_ctx)
if(!success) {
  result.success = true;                                 // the *call* succeeded...
  result.message = "Failed tray assignments: " + message;
  for(const auto& job : request_data.pending_jobs) {     // ...but every pending job is reported failed
    result.scheduled_jobs.push_back(FailJob(job, message));
  }
  return result;
}
std::tie(success, message) = DoAgvAssignments(plan_ctx); // same failure handling as above
// ...then plan_ctx->events.Reduce(), SanityCheckEvents(plan_ctx), PlanMotions(...)
```

Two consequences matter for the refactor:

- **Failure is all-or-nothing.** If either algorithm fails, every pending job fails with the same message, and `success` stays `true`. A new solver must keep that contract or `SchedulerRos` clients will see different responses.
- **Tests already call the algorithms directly.** `test/scheduler_tests.cpp` calls `scheduler.DoTrayAssignments(ctx)` 4 times, `scheduler.DoAgvAssignments(ctx)` 9 times and `scheduler.ResolveBlockingTrays(...)` once. They build a whole `Scheduler` from a layout file to do so:

```cpp
// test/scheduler_tests.cpp — TEST(Scheduler, ...) ; all objects are locals of the test body
Scheduler scheduler(layout_filepath, logger, params);  // loads the layout, builds gg_, table_, cost_model_
ScheduleContextSPtr ctx = std::make_shared<ScheduleContext>(request_id, state, rclcpp::Time());
auto tray_move = std::make_shared<TrayMove>(0u);       // job_index 0; no destination set
tray_move->SetTrayId(1);
ctx->events.AddEvent(tray_move);                       // hand-built one-event DAG
std::tie(success, msg) = scheduler.DoTrayAssignments(ctx);
```

That pattern is the baseline the refactor improves on: after the change, a test should be able to construct the solver with only the services it needs.

## 3. What the two algorithms touch

Figure 1 is generated from `scheduler.cpp`. Each row is one `Scheduler` method in the tray or AGV call tree. Each column is something its body uses. The right-hand column lists callers outside the two trees: those are the helpers you cannot simply move.

![What the two algorithms touch](figures/34_coupling_matrix.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#34_coupling_matrix) · [standalone SVG](figures/34_coupling_matrix.svg)</sub>

**Figure 1 — Coupling of the tray and AGV call trees.** Filled dots mark a token found in the method body (comment-stripped). A helper that receives the DAG as a parameter rather than through `ctx` shows no `events` dot even though it edits the DAG, so read the dots as "uses directly", not "is independent of".

What the matrix tells you:

1. **Both trees need the same three services.** `gg_` (graph search), `table_` (collision checks) and `cost_model_` (travel times) appear throughout. `layout_` is used mainly for node types and headings. All four are read-only after construction, which makes constructor injection by `const&` safe as long as the `Scheduler` outlives the solver.
2. **The tray tree touches three context fields:** it edits `ctx->events`, reads `ctx->initial_state`, and fills `ctx->first_tray_event` (the first move of each tray, keyed by tray id `uint16_t`). The AGV tree reads `first_tray_event` back inside `MoveAgvToTrayPose`. That map is the hand-off between the two solvers and must be part of both contracts.
3. **Five helpers are shared with job planning.** They must stay reachable from `Scheduler` (or move to a shared utility) after the algorithms leave:

| Helper (all `Scheduler` members) | Also called by | Why |
|---|---|---|
| `ResolveBlockingTrays` (public) | `PlanChargePayloadJob`, one test | Finds a VECS node plus unblocking moves when the requested node is not a ready VECS |
| `AssignTrayIdForEmptyMove` | `PlanReadyForInsertJob` | Picks an empty tray early, best-effort |
| `UsePreferredHeading` | `PlanAgvMoveJob`, `PlanReparkTrayJob` | Chooses the parking heading that makes later retrieval fastest |
| `UseEvChargeHeading` | `PlanChargePayloadJob` | Heading for a VECS node |
| `GetJustMovingCost` | `PlanAgvChargeJob`, tests | Travel-time estimate for an AGV between two poses |

4. **External algorithms are already separate.** `SingleSourceSearch`, `GetStaticFilter`, `GetPosePath` and `BottleneckAssignment` come from other packages. The default solvers keep calling them; nothing about them changes.
5. **Some "AGV assignment" work is graph repair, not matching.** `DoAgvAssignments` ends with `EnsureAgvMovePathsClear(ctx)` (up to 256 repair passes), then `ctx->events.Reduce()`, then `AddDepsAfterAmiga(...)`. `Plan` calls `Reduce()` a second time afterwards. Keep all of these in the same order inside the default AGV solver for the first pass; see risk 2 in section 10.

### Why the default solver needs graph and collision services

This is the start of today's tray algorithm. Note the two different garage states:

```cpp
// src/scheduler.cpp — Scheduler::DoTrayAssignments(ScheduleContextSPtr ctx) const
// this : const Scheduler* ; gg_ and table_ are Scheduler members
auto working_state = ctx->initial_state;               // DiscreteGarageState COPY; updated as moves are assigned
auto total_ordering_opt = ctx->events.GetTopologicalOrdering();  // std::optional<...>: empty if the DAG has a cycle
if(!total_ordering_opt.has_value()) {
  return std::make_pair(false, "Failed to get total ordering");
}

// Remembers which already-planned event vacates each node, so a later move INTO that
// node can depend on it. Needs the graph and collision table to know which nodes overlap.
volley::GarageOccupancyChecker<std::shared_ptr<volley::ScheduleEvent>> freeing_moves(table_, gg_);
```

`ctx->initial_state` stays untouched; `working_state` is the solver's private "garage after everything planned so far". Keeping that distinction is invariant 9 in practice (section 7).

## 4. Current versus target responsibilities

| Concern | Today (method in `Scheduler`) | After the refactor |
|---|---|---|
| Validate request, build `ScheduleContext` | `Plan` | Stays in `Scheduler` |
| Expand jobs into events | `Plan<Type>Job` (12 methods) | Stays in `Scheduler` |
| Choose tray and destination for each `TrayMove` | `DoTrayAssignments` → `AssignTrayIdForEmptyMove`, `AssignDestForUntargetedMove` | `tray_assignment::DefaultSolver` (the loop) + pure `ChooseEmptyTray`, `ChooseParkingSpot` (section 6.3) |
| Move blocking trays out of the way | `ResolveBlockingTrays` → `FindOpenSpaceForRootTray`, `TryFindBlockingTrayResolution` | Pure free function `tray_assignment::ResolveBlockingTrays(svc, request)`, public so job planning can call it too |
| Write the tray results into `ctx` | (done inside `DoTrayAssignments`) | `tray_assignment::ApplyTrayAssignment(ctx, result)`, called by `Plan()` right after `Solve`; the only writer (sections 6.1, 6.5) |
| Choose parking headings | `UsePreferredHeading`, `UseRetrievalHeading`, `UseEvChargeHeading` | Pure functions in `common/headings` |
| Match AGVs to tray moves | `DoAgvAssignments` + cost helpers + `BottleneckAssignment` | `agv_assignment::DefaultSolver` |
| Add approach, lift and lower events | `MoveAgvToTrayPose`, `AppendAgvLiftEvent`, `AddNodeArrivalDeps` | Default AGV solver |
| Repair AGV path conflicts, reduce, AMIGA deps | `EnsureAgvMovePathsClear`, `Reduce`, `AddDepsAfterAmiga` (end of `DoAgvAssignments`) | Default AGV solver, same order (move later only with evidence) |
| DAG primitives | `planner_core::ScheduleEventDag` | Unchanged |
| Sanity check, motion planning, response | `SanityCheckEvents`, `PlanMotions`, `ResponseFromTrajectories` | Unchanged |

**Decision needed:** where the solver *interfaces* live. Section 6.2 proposes starting inside the scheduler package: subfolders `common/`, `tray_assignment/` and `agv_assignment/` under `include/scheduler/`, `src/` and `test/`, still built by the one `CMakeLists.txt`. Moving a module to its own package later is a matter of moving those three subfolders. Options are `planner_core`, a small solver-interface package, or a new scheduler-core package. A default implementation needs `motion_planner` and `cost_functions`, so putting it in a low-level package can create dependency cycles. Check against `package.xml` and the exported CMake targets before choosing.

## 5. Target architecture

![Target design](figures/02_target_architecture.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#02_target_architecture) · [standalone SVG](figures/02_target_architecture.svg)</sub>

**Figure 2 — Proposed architecture.** Solver contracts separate policy from orchestration. Both default solvers get graph, collision, cost and layout services through one `const GarageServices&`. The tray solver only reads the event DAG and returns its edits, which `Scheduler` applies; the AGV solver edits the DAG in place for the first pass (section 6.7). This is a proposal, not existing code.

### Classes and call sequence

The two figures below are the proposal at a glance; section 6 then defines each type and function.

![Solver UML](figures/08_uml_solver.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#08_uml_solver) · [standalone SVG](figures/08_uml_solver.svg)</sub>

**Figure 3 — Proposed class structure.** `Scheduler` owns a `tray_assignment::Solver` and builds the read-only `Input` it passes in. `DefaultSolver` and a test double realize the interface (dashed line, hollow triangle) and return `stdx::Expected<Result>`; `Scheduler` applies the `Result` in one place. `DefaultSolver` delegates to pure free functions that job planning also calls. This is the **Strategy** pattern: `Scheduler` depends on the stable interface, not on the algorithm.

![Solver call sequence](figures/09_sequence_tray.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#09_sequence_tray) · [standalone SVG](figures/09_sequence_tray.svg)</sub>

**Figure 4 — Proposed tray solver interaction.** `Scheduler` calls `Solve`. The solver reads the topological event order once, then records (does not apply) tray fills, blocker moves, edges and `first_tray_event` in a `Result`, and returns `stdx::Expected<Result>`. `Scheduler` replays the result into `ctx->events` with `ApplyTrayAssignment`, which ends with the cycle check, and AGV assignment continues.

## 6. Proposed layout and API for tray assignment

This section first introduces the new types and shows how they work with `ScheduleContext` (6.1), then where the files go (6.2), then which of today's functions turn into what (6.3). After that come errors (6.4), the reasoning behind returning a result (6.5), the remaining signatures and the `Plan()` call site (6.6), and how much of this applies to AGV assignment (6.7). Everything here is **proposed**; names are suggestions for review.

### 6.1 The new pieces and how they fit together

Today `DoTrayAssignments(ctx)` does two jobs at once: it **decides** (which tray, which destination, which blockers move where) and it **writes** those decisions into `ctx` as it goes. The proposal separates the two:

- **Deciding** happens in `tray_assignment::DefaultSolver::Solve`. It receives read-only references to the parts of `ctx` it needs and returns its decisions as a value, a `Result`. It never writes `ctx`.
- **Writing** happens in one free function, `tray_assignment::ApplyTrayAssignment(ScheduleContext&, const Result&)`, which `Plan()` calls right after `Solve` succeeds.

So yes: `ctx` is still changed. It has to be, because AGV assignment and motion planning read the blocker moves, filled-in fields and `first_tray_event` from it. What changes is *where*: one function, called once, after all the decisions are made, instead of writes spread through a 560-line loop and its helpers.

![Tray assignment data flow, today vs proposed](figures/58_tray_dataflow.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#58_tray_dataflow) · [standalone SVG](figures/58_tray_dataflow.svg)</sub>

**Figure 5 — How tray assignment reads and writes `ScheduleContext`.** Top: today `DoTrayAssignments` gets a shared, mutable pointer to the context and writes into it throughout the loop, so a failure halfway leaves it half-edited. Bottom: (1) `Plan` passes `Solve` two `const` references; (2) `Solve` keeps its working data in a private `Pass`, calls pure functions to decide, and returns a `Result`; (3) `ApplyTrayAssignment` writes the `Result` into the context. If `Solve` fails, step 3 never runs and the context is unchanged.

The pieces, all in namespace `volley::tray_assignment` unless marked `common`:

| Piece | What it is | Declared in | Lives for | Reads | Writes |
|---|---|---|---|---|---|
| `common::GarageServices` | Struct of `const` references to the graph, collision table, cost model and layout, plus the logger | `include/scheduler/common/garage_services.hpp` | As long as the `Scheduler` (member `services_`) | — | nothing |
| `Input` | Struct of two `const` references into `plan_ctx` | `include/scheduler/tray_assignment/solver.hpp` | One `Solve` call (a temporary built in `Plan`) | `initial_state`, `events` | nothing |
| `Result` | Plain value: `fills`, ordered `edits`, `first_tray_event` | `solver.hpp` | From `Solve`'s return until `ApplyTrayAssignment` | — | — (it is data) |
| `TrayFill`, `AddEvent`, `AddDependency`, `DagEdit` | The element types inside `Result` | `solver.hpp` | Inside `Result` | — | — |
| `Solver` | Interface with one method, `Solve(const Input&) const` | `solver.hpp` | Owned by `Scheduler` (`tray_solver_`) | — | — |
| `DefaultSolver` | Today's algorithm behind the interface; holds only `const GarageServices&` | `default_solver.hpp`, `src/tray_assignment/default_solver.cpp` | Owned by `Scheduler` | `Input`, services | nothing outside itself |
| `DefaultSolver::Pass` | **Private nested class**: the loop's working data | declared in `default_solver.hpp`, defined in `src/tray_assignment/pass.hpp` | One `Solve` call (a local variable) | `Input`, services | only its own members |
| Pure functions | `ChooseEmptyTray`, `ResolveBlockingTrays`, `ChooseParkingSpot`, `FindCriticalPath`, the heading functions, ... | `empty_tray.hpp`, `blocking_trays.hpp`, `src/tray_assignment/critical_path.hpp`, `common/headings.hpp` | — | their arguments | nothing |
| `ApplyTrayAssignment` | Free function, the only one that takes a mutable `ScheduleContext&` | `apply.hpp`, `src/tray_assignment/apply.cpp` | — | `Result` | `ctx.events`, event fields, `ctx.first_tray_event` |

What happens in `Plan()`, step by step:

1. **Build the input.** `Input{plan_ctx->initial_state, plan_ctx->events}`: two `const` references, no copies.
2. **Solve.** `DefaultSolver::Solve` creates a `Pass` on its stack. The `Pass` copies `initial_state` into `working_state_` and starts with an empty occupancy record, per-tray chain and `result_`. For each event in topological order, `Solve` asks pure functions for decisions (which empty tray, which parking spot, the critical path, where each blocker goes) and tells the `Pass` to record them: `Fill` adds a `TrayFill`, `EmitMoveChain` appends `AddEvent` / `AddDependency` entries in today's order, and `CommitRootMove` records the root move's edges. Each recorded move is also applied to `working_state_`, so later decisions see the garage as it will be. At the end, `Solve` returns the `Pass`'s `Result`. On any error it returns `stdx::Unexpected(message)`; the `Pass` is destroyed, and nothing outside `Solve` was touched.
3. **Apply.** `ApplyTrayAssignment(*plan_ctx, result)` replays `edits` into `plan_ctx->events`, sets the filled fields on the existing `TrayMove`s, copies `first_tray_event`, and runs the same cycle check `DoTrayAssignments` ends with today.
4. **Continue.** AGV assignment runs on `plan_ctx` exactly as today.

The types, in one place:

```cpp
// PROPOSED — include/scheduler/common/garage_services.hpp
namespace volley::common {
struct GarageServices {                   // read-only services every search needs; built once by Scheduler
  const GarageGraph& graph;               // Scheduler::gg_
  const CollisionTable& collisions;       // Scheduler::table_
  const cost::MotionCostModel& costs;     // Scheduler::cost_model_
  const Layout& layout;                   // *Scheduler::layout_
  rclcpp::Logger logger;                  // copy of Scheduler::logger_
};
}  // namespace volley::common
```

```cpp
// PROPOSED — include/scheduler/tray_assignment/solver.hpp
namespace volley::tray_assignment {

struct Input {                                     // everything Solve may read; nothing it may write
  const DiscreteGarageState& initial_state;        // plan_ctx->initial_state
  const ScheduleEventDag& events;                  // plan_ctx->events, after job expansion
};

// A blank filled on an EXISTING TrayMove of the input DAG. ApplyTrayAssignment calls SetTrayId / SetDest.
struct TrayFill {
  ScheduleEventSPtr event;   // the TrayMove, as the input DAG holds it (same shared_ptr)
  uint16_t tray_id;          // unchanged if it was already set
  GaragePoseMsg dest;        // unchanged if it was already set; heading may be adjusted
};

// One structural edit, recorded in the order today's code makes it.
struct AddEvent      { ScheduleEventSPtr event; };                       // a NEW TrayMove (blocker, advance)
struct AddDependency { ScheduleEventSPtr from; ScheduleEventSPtr to; };  // from must finish before to
using DagEdit = std::variant<AddEvent, AddDependency>;

struct Result {
  std::vector<TrayFill> fills;                                       // one per TrayMove that had a blank
  std::vector<DagEdit> edits;                                        // replay front to back
  std::unordered_map<uint16_t, ScheduleEventSPtr> first_tray_event;  // hand-off to AGV assignment
};

class Solver {
 public:
  virtual ~Solver() = default;
  [[nodiscard]] virtual stdx::Expected<Result> Solve(const Input& input) const = 0;
};

}  // namespace volley::tray_assignment
```

```cpp
// PROPOSED — include/scheduler/tray_assignment/default_solver.hpp
namespace volley::tray_assignment {
class DefaultSolver final : public Solver {
 public:
  explicit DefaultSolver(const common::GarageServices& services);   // services must outlive the solver
  [[nodiscard]] stdx::Expected<Result> Solve(const Input& input) const override;
 private:
  class Pass;                                // defined in src/tray_assignment/pass.hpp; no one else can name it
  const common::GarageServices& services_;
};
}  // namespace volley::tray_assignment
```

```cpp
// PROPOSED — src/tray_assignment/pass.hpp (private header: not under include/, not installed)
class DefaultSolver::Pass {
 public:
  Pass(const common::GarageServices& svc, const DiscreteGarageState& initial_state);  // copies the state
  stdx::Result RecordTransition(const ScheduleEventSPtr& event);   // was ApplyTransitionToFreeingMoves
  void Fill(const ScheduleEventSPtr& event, uint16_t tray_id, const GaragePoseMsg& dest);  // → result_.fills
  void EmitMoveChain(std::span<const PlannedTrayMove> moves, const EmitOptions& options);  // → result_.edits
  stdx::Result CommitRootMove(const ScheduleEventSPtr& event, const TrayMove& resolved,
                              const CommitOptions& options);      // root move: edges, apply, chain
  const DiscreteGarageState& State() const { return working_state_; }  // what the pure functions read
  Result TakeResult() && { return std::move(result_); }
 private:
  const common::GarageServices& svc_;
  DiscreteGarageState working_state_;                                // initial_state + every move so far
  GarageOccupancyChecker<ScheduleEventSPtr> freeing_moves_;          // who used each pose → new edges
  std::unordered_map<uint16_t, ScheduleEventSPtr> last_tray_event_;  // per-tray chain
  Result result_;                                                    // what Solve returns
};
```

```cpp
// PROPOSED — src/tray_assignment/default_solver.cpp (shape only)
stdx::Expected<Result> DefaultSolver::Solve(const Input& input) const {
  auto order = input.events.GetTopologicalOrdering();              // the only read of the DAG's structure
  if(!order) return stdx::Unexpected("Failed to get total ordering");
  Pass pass(services_, input.initial_state);
  for(auto vertex : *order) {
    ScheduleEventSPtr event = input.events.GetEventFromVertex(vertex).value();
    if(event->GetType() != ScheduleEventType::TRAY_MOVE) {
      if(auto r = pass.RecordTransition(event); !r) return stdx::Unexpected(r.error());
      continue;
    }
    // Work on a resolved COPY of the TrayMove; *event itself is never modified (6.5).
    // Blank tray id   -> ChooseEmptyTray(services_, pass.State(), dest), then pass.Fill(...)
    // Blank dest      -> ChooseParkingSpot(...), pass.Fill(...), pass.EmitMoveChain(...), pass.CommitRootMove(...)
    // Both set        -> CheckDestinationUsable, FindCriticalPath, blocker loop with ResolveBlockingTrays,
    //                    TryAdvanceRoot and BlockersOnPath; pass.EmitMoveChain(...); pass.CommitRootMove(...)
  }
  return std::move(pass).TakeResult();
}
```

```cpp
// PROPOSED — include/scheduler/tray_assignment/apply.hpp
namespace volley::tray_assignment {
// The only function in the module that takes a mutable context. Implementation in 6.5.
[[nodiscard]] stdx::Result ApplyTrayAssignment(ScheduleContext& ctx, const Result& result);
}  // namespace volley::tray_assignment
```

`EmitOptions` and `CommitOptions` carry the small differences between today's two copies of the emission code (6.3) so that parity holds; they can disappear once those differences are settled.

### 6.2 Source tree

The package root stays `scheduler/` with **one** `CMakeLists.txt`. The new code goes into subfolders of the existing `include/scheduler/` and `src/` (and `test/`), one per module:

```text
scheduler/                                       # ROS package root (name unchanged)
├── CMakeLists.txt                               # the only CMakeLists.txt; lists the new .cpp files
├── package.xml                                  # already depends on stdx
├── include/
│   └── scheduler/
│       ├── scheduler.hpp                        # existing: Plan(), job expansion; owns services_, tray_solver_
│       ├── scheduler_ros.hpp                    # existing
│       ├── scheduler_msgs.hpp                   # existing
│       ├── utils.hpp                            # existing
│       ├── common/
│       │   ├── garage_services.hpp              # GarageServices
│       │   ├── headings.hpp                     # PreferredHeading, RetrievalHeading, EvChargeHeading
│       │   └── overloaded.hpp                   # Overloaded helper for std::visit
│       ├── tray_assignment/
│       │   ├── solver.hpp                       # Solver, Input, Result, TrayFill, DagEdit
│       │   ├── default_solver.hpp               # DefaultSolver (declares the private nested Pass)
│       │   ├── apply.hpp                        # ApplyTrayAssignment
│       │   ├── empty_tray.hpp                   # ChooseEmptyTray, TrayChoice
│       │   └── blocking_trays.hpp               # ResolveBlockingTrays, ChooseParkingSpot, PlannedTrayMove, ...
│       └── agv_assignment/
│           ├── solver.hpp
│           ├── default_solver.hpp
│           └── travel_cost.hpp                  # GetJustMovingCost (shared with PlanAgvChargeJob)
├── src/
│   ├── scheduler.cpp                            # existing; shrinks to Plan() + job expansion
│   ├── scheduler_component.cpp                  # existing
│   ├── scheduler_ros.cpp                        # existing
│   ├── utils.cpp                                # existing
│   ├── common/
│   │   └── headings.cpp
│   ├── tray_assignment/
│   │   ├── default_solver.cpp                   # Solve(): the per-event loop
│   │   ├── pass.hpp                             # PRIVATE header: DefaultSolver::Pass
│   │   ├── pass.cpp
│   │   ├── critical_path.hpp                    # PRIVATE header: CheckDestinationUsable, FindCriticalPath, ...
│   │   ├── critical_path.cpp
│   │   ├── empty_tray.cpp
│   │   ├── blocking_trays.cpp                   # + detail::FindOpenSpace, detail::TryResolveBlocker
│   │   └── apply.cpp
│   └── agv_assignment/
│       ├── default_solver.cpp
│       └── travel_cost.cpp
└── test/
    ├── scheduler_tests.cpp                      # existing (and the other existing test files)
    ├── tray_assignment/                         # empty_tray, blocking_trays, critical_path, default_solver, apply
    └── agv_assignment/
```

The single `CMakeLists.txt` only grows its source lists. Today it builds one shared library with `volley_add_library(${PROJECT_NAME} SHARED src/scheduler.cpp src/utils.cpp)` and four `volley_add_gtest` targets:

```cmake
# PROPOSED — CMakeLists.txt (excerpt; the rest of the file is unchanged)
volley_add_library(
  ${PROJECT_NAME}
  SHARED
  src/scheduler.cpp
  src/utils.cpp
  src/common/headings.cpp
  src/tray_assignment/default_solver.cpp
  src/tray_assignment/pass.cpp
  src/tray_assignment/critical_path.cpp
  src/tray_assignment/empty_tray.cpp
  src/tray_assignment/blocking_trays.cpp
  src/tray_assignment/apply.cpp
  src/agv_assignment/default_solver.cpp
  src/agv_assignment/travel_cost.cpp
)

if(BUILD_TESTING)
  volley_add_gtest(
    tray_assignment_tests
    test/tray_assignment/empty_tray_test.cpp
    test/tray_assignment/blocking_trays_test.cpp
    test/tray_assignment/critical_path_test.cpp
    test/tray_assignment/default_solver_test.cpp
    test/tray_assignment/apply_test.cpp
    LINK_LIBRARIES
      yaml-cpp
      ${PROJECT_NAME}
  )
endif()
```

How the boundaries hold with one library target:

- **Public vs private headers.** Headers under `include/scheduler/<module>/` are the module's API; code includes them as `#include "scheduler/tray_assignment/solver.hpp"`. Headers next to the `.cpp` files in `src/<module>/` are private. They are not under `include/`, so they are not installed and not on anyone's include path, and only files in the same folder include them (`#include "pass.hpp"`). Check that `volley_add_library` exports only `include/` (it is defined in `volley_cmake`, not in this snapshot).
- **`Pass` cannot be used from outside even by accident.** It is a private nested class of `DefaultSolver`, so code outside `DefaultSolver` cannot name it, whatever it includes.
- **Dependency direction is a rule, checked in CI.** With one target, CMake cannot stop `src/tray_assignment/*.cpp` from including `scheduler/scheduler.hpp`. The rules: `tray_assignment/` and `agv_assignment/` never include `scheduler.hpp`; `agv_assignment/` does not include `tray_assignment/` (the hand-off, `first_tray_event`, is a plain map in its `Input`); `common/` includes neither. A one-line grep in CI enforces this. If the team later wants the linker to enforce it, the same `CMakeLists.txt` can declare one library per module without moving any file.

Names: **`tray_assignment` rather than `tray_movement`**, because job expansion also plans tray movement (it creates the `TrayMove`s); this module only fills in what expansion left open (tray ids, destinations, blockers). It matches the stage name in doc 01 (`DoTrayAssignments`) and pairs with `agv_assignment`. Namespaces follow the folders: `volley::tray_assignment`, `volley::agv_assignment`, `volley::common`.

### 6.3 Before and after: the tray call tree

Not everything moves into the new class. The two figures below show the same call tree before and after; the question that sorts every function is **what does it write?**

![Tray call tree today](figures/59_tray_tree_before.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#59_tray_tree_before) · [standalone SVG](figures/59_tray_tree_before.svg)</sub>

**Figure 6 — Tray call tree today.** Every function is a `Scheduler` member, and the main loop's six blocks are written inline in `DoTrayAssignments`. The chips show what each one writes: red for something in `ScheduleContext` (the DAG, the hand-off map, or a field of an event in the DAG), amber for an argument passed by reference, green for nothing. Three functions already write nothing, but their signatures do not say so, and four functions are also called by job planning.

![Proposed tray_assignment module](figures/60_tray_tree_after.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#60_tray_tree_after) · [standalone SVG](figures/60_tray_tree_after.svg)</sub>

**Figure 7 — The same call tree after the refactor (UML).** `Pass` is drawn **inside** `DefaultSolver` because it is a private nested class: it exists only during one `Solve` call and holds the only state that changes while solving. Everything green is a pure function, grouped by the header that declares it; `// was ...` names the member or inline block it replaces. `ApplyTrayAssignment` (red) is the only function that takes a mutable `ScheduleContext`, and `Scheduler::Plan` calls it right after `Solve`. Job methods call the public pure functions directly with `services_`.

In short, today's functions fall into four groups:

| Group | Functions | Why there |
|---|---|---|
| **Solver class** | `DefaultSolver::Solve` (was `DoTrayAssignments`, minus everything below) | The interface method; runs the per-event loop |
| **Private, mutable, one per call** | `Pass::RecordTransition`, `Fill`, `EmitMoveChain`, `CommitRootMove` (were `ApplyTransitionToFreeingMoves`, the setters, the two copies of the emission block, the root-move tail) | They update the loop's working data, which only `Solve` can see |
| **Pure** | `ChooseEmptyTray`, `ResolveBlockingTrays`, `ChooseParkingSpot`, `detail::FindOpenSpace`, `detail::TryResolveBlocker`, `CheckDestinationUsable`, `FindCriticalPath`, `TryAdvanceRoot`, `BlockersOnPath`, `PreferredHeading`, `RetrievalHeading`, `EvChargeHeading` | They only compute an answer from their arguments |
| **Writes the context** | `ApplyTrayAssignment` (new) | Replaces every write that used to happen inside the loop |

**What “pure” means here.** The function's result depends only on its arguments, and it writes nothing reachable from them: no member state, no `ctx`, no event objects. Inputs come in by `const&` or by value, and the answer comes back as the return value. The read-only services (`GarageGraph`, `CollisionTable`, `MotionCostModel`, `Layout`) are passed as one `const GarageServices&` (`svc`), because they never change after the `Scheduler` constructor. Logging is the one allowed side effect: it does not change what any later call computes.

Why make them pure:

- **They can be tested alone.** `ChooseEmptyTray` needs a layout, a `DiscreteGarageState` and a destination, not a `Scheduler`, not a `ScheduleContext`, not a DAG. Today the only way to test it is through `DoTrayAssignments` or `PlanReadyForInsertJob`.
- **The “shared helper” problem in section 3 goes away.** Job methods call the same free functions with the `Scheduler`'s `services_`. No back-pointer from the solver to `Scheduler`, and no copy of the helpers on both sides.
- **The recursion is easier to trust.** `ResolveBlockingTrays` ↔ `TryResolveBlocker` already work on private copies of the state; as free functions with no members to touch, that guarantee is visible in the signature.
- **One copy of the emission code.** The two emission blocks differ in three small ways today, and parity means keeping all three:
  - the main loop registers each move's source pose with the generic `TRAY` collision id, while `AssignDestForUntargetedMove` uses the tray's own id → a parameter of `EmitMoveChain`;
  - only the main loop erases the tray from `blocking_tray_set` → stays in the caller;
  - only `AssignDestForUntargetedMove` checks the result of `Apply`. The main loop *cannot* yet: on the fallback-1 path the advance move was already applied before it reaches this block and is applied a second time here (the `TODO(Gunther)` at `:2933` says so). Checking would make that path fail → a parameter for now; fix the double apply as its own reviewed change.

  The root-move tails differ too: the main loop adds `freeing_moves` edges for the root move's destination and source and registers its source (`:3024`–`:3050`); `AssignDestForUntargetedMove` does neither (doc 01, section 16). `CommitRootMove` keeps both behaviours behind a flag until someone decides whether the second is a bug.

**What stays mutable, and why that is fine.** The loop needs a garage state that changes after every move, an occupancy record and a per-tray “last move” map. Those live in `Pass`, an object created inside `Solve` and destroyed when it returns. Nothing outside can see it. Seen from the caller, `Solve` is still a pure function: same `Input`, same `Result`. This is the usual pattern of “local mutation, pure interface”: rewriting the loop to thread an immutable state through every step would add copying and noise without making the code any safer.

### 6.4 Errors: `stdx::Expected` instead of `BoolStringPair`

`BoolStringPair` (`std::pair<bool, std::string>`) and `stdx::Expected` say the same thing (“it worked, or here is why not”), but `Expected` says it in the type: a caller cannot read a value without checking, and there is no meaningless message on success or meaningless value on failure. The project already has `volley::stdx` (`src/core/stdx/include/stdx/expected.hpp`), aliases over `tl::expected`, and **the scheduler package already uses it**: `package.xml` depends on `stdx`, `EnsureAgvMovePathsClear` returns `stdx::Result`, `RunAgvPathRepairPass` returns `stdx::Expected<bool>`, and `utils.cpp`'s `InsertVrcActionsIntoDag` returns `stdx::Result`. So this is finishing a migration that has started, not adding a dependency:

- `stdx::Expected<T, E = std::string>`: a `T` or an error `E`.
- `stdx::Result` = `stdx::Expected<void>`: success or an error string.
- `stdx::Unexpected(msg)` and `stdx::Unexpected(fmt, args...)` (with `std::format`) to build the error.

| Today | With `stdx` |
|---|---|
| `BoolStringPair F(...)` that only reports success | `stdx::Result F(...)` |
| `BoolStringPair F(TrayMove& move, ...)` that reports success **and** edits its input | `stdx::Expected<TrayChoice> F(...)`: the edit becomes the return value |
| `return std::make_pair(true, "");` | `return {};` |
| `return std::make_pair(false, "Failed to find empty tray to move to " + std::to_string(dest));` | `return stdx::Unexpected("Failed to find empty tray to move to {}", std::to_string(dest));` |
| `auto [ok, msg] = F(); if(!ok) return std::make_pair(false, msg);` | `if(auto r = F(); !r) return stdx::Unexpected(r.error());` |
| `std::pair<std::optional<GaragePoseMsg>, std::vector<std::pair<std::shared_ptr<TrayMove>, std::vector<GaragePoseMsg>>>>` | `stdx::Expected<BlockingResolution>` with named fields `dest` and `required_moves` (a `std::vector<PlannedTrayMove>`, each `{move, path}`) |
| test: `std::tie(success, msg) = scheduler.DoTrayAssignments(ctx); EXPECT_TRUE(success) << msg;` | `auto r = solver.Solve(input); ASSERT_TRUE(r) << r.error();` |

Three rules keep this consistent:

1. **`stdx::Expected` / `stdx::Result` at every function that can fail for a reason someone should read.** That is every public function in 6.3 and every `Pass` method.
2. **`std::optional` stays for “searched, found nothing”** inside a module, where the caller handles the empty case itself and has no message to pass on: `detail::FindOpenSpace`, `detail::TryResolveBlocker`, `TryAdvanceRoot`. Converting these to `Expected` would invent error strings nobody reads. `ResolveBlockingTrays` is the boundary: today its failures are only logged (`WARNS` / `ERRORS`); as `Expected`, the reason travels to the caller, which still treats it as “try the next fallback”.
3. **Keep `E = std::string` for the parity pass.** Error text reaches clients through `FailJob(job, message)` and may be matched by tests. A typed error (`struct Error { Code code; std::string message; }`, which `Expected<T, E>` already allows) is a good follow-up once the benchmarks exist.

Two practical notes. `std::format` has no formatter for `GaragePoseMsg`; either pass `std::to_string(pose)` as above (identical text to today) or add a `std::formatter<GaragePoseMsg>` in `common`. And `tl::expected` has `and_then` / `transform`, which keeps call sites flat (see the `Plan()` snippet in 6.6).

### 6.5 Why return a result, and how it is applied

Today `DoTrayAssignments(ctx)` edits three things it does not own: the DAG (`ctx->events`), the hand-off map (`ctx->first_tray_event`) and the `TrayMove` objects inside the DAG (`SetTrayId`, `SetDest`). The proposal: `Solve` takes a read-only `Input` and **returns a description of the edits**; `Plan()` writes them into the context with one call to `ApplyTrayAssignment`.

**Why this is practical for tray assignment.** The tray tree reads the DAG exactly once: `GetTopologicalOrdering()` at the start (plus `GetEventFromVertex` to walk it). After that it only *writes*: `AddEvent`, `AddDependency`, the two setters, and `first_tray_event`. Nothing in the loop reads back an edge it added. So the solver never needs to see its own edits in the DAG, and recording them instead of applying them changes nothing it computes. (The garage *state* the loop does read is `working_state`, which is private to the `Pass` anyway.)

**Why not return a whole new DAG.** `ScheduleEventDag` holds `std::shared_ptr<ScheduleEvent>`. Copying it copies pointers, so a “new DAG” would share event objects with the old one, and the setters would still edit the caller's events. A deep copy needs cloning and an old → new identity map for `first_tray_event` and every later stage. `planner_core` has no virtual `Clone()`: events are copy-constructible, but only through their concrete type, so cloning means a `dynamic_cast` (or a switch on `GetType()`) over the five subclasses. An **edit log** avoids both: it refers to existing events by the same `shared_ptr`, adds new events as new objects, and never touches the caller's.

The `Result` type and its parts are defined in 6.1. An **edit log** means: `fills` for blanks on existing events, `edits` for new events and edges in the order today's code creates them, and the hand-off map.

**Parity depends on the order.** The DAG's vertex indices follow `AddEvent` order (Boost `vecS`). `ScheduleEventDag::GetTopologicalOrdering()` takes the lowest job index first, but breaks ties within a job by heap order, which depends on vertex order and on the order edges were added; `Reduce()` and every replay use that ordering (doc 01, section 12.5). `edits` is therefore an ordered log, and `ApplyTrayAssignment` replays it front to back with the same `AddEvent` / `AddDependency` calls today's code makes, so the resulting DAG is the same graph built in the same order. `AddDependency` returns `false` only when an endpoint is missing or the edge already exists, and tray assignment only logs it, so replaying the same calls gives the same edge set.

**The one subtle part: the loop needs filled values before they are applied.** After `ChooseEmptyTray`, the main loop plans *that* tray's path, and later `Apply`s the move to `working_state`. Today it reads the id back from the mutated event. In the new design the `Pass` makes a resolved copy, `TrayMove resolved = *move; resolved.SetTrayId(choice.tray_id);`, applies the copy to its `working_state`, records a `TrayFill`, and never touches `*move`. Both assumptions hold in `planner_core` (`sources/repomix-planner-core.xml`): `ScheduleEvent`'s copy constructor is public and defaulted, so `TrayMove resolved = *move;` compiles (copy *assignment* is private, so `resolved = *move;` does not), and `Apply` is a `const` member, so it can only change the state it is given. One behaviour to keep in mind: `TrayMove::Apply` with a blank tray id does nothing, and with a blank destination it removes the tray from the state (doc 01, section 11). The resolved copy always has both fields set, so the `Pass` never hits those branches.

**Applying it.** One function owns every write to the context:

```cpp
// PROPOSED — src/tray_assignment/apply.cpp ; declared in include/scheduler/tray_assignment/apply.hpp
stdx::Result ApplyTrayAssignment(ScheduleContext& ctx, const Result& result) {
  for(const auto& edit : result.edits) {                       // structure first, in recorded order
    stdx::Result applied = std::visit(Overloaded{
        [&](const AddEvent& e) -> stdx::Result {
          if(!ctx.events.AddEvent(e.event)) return stdx::Unexpected("event added twice");  // AddEvent: false if present
          return {};
        },
        [&](const AddDependency& e) -> stdx::Result {
          if(!ctx.events.HasEvent(e.from) || !ctx.events.HasEvent(e.to)) {      // today: a silent no-op
            return stdx::Unexpected("edge to an event that is not in the DAG");
          }
          ctx.events.AddDependency(e.from, e.to);   // false now only means "edge already there", as today
          return {};
        }}, edit);
    if(!applied) return applied;
  }
  for(const auto& fill : result.fills) {                       // then the blanks
    auto* move = dynamic_cast<TrayMove*>(fill.event.get());
    if(move == nullptr) return stdx::Unexpected("TrayFill on a non-TrayMove event");
    move->SetTrayId(fill.tray_id);
    move->SetDest(fill.dest);
  }
  ctx.first_tray_event = result.first_tray_event;
  if(!ctx.events.GetTopologicalOrdering()) {                   // same check DoTrayAssignments ends with today
    return stdx::Unexpected("Failed to get new total ordering");
  }
  return {};
}
```

(`Overloaded` is the usual two-line helper for `std::visit`, in `include/scheduler/common/overloaded.hpp`.) The two checks are the only intended difference from today. `AddDependency` returns `false` both for a duplicate edge (harmless, and common) and for an endpoint that was never added (a lost edge, silently). Today's tray code always adds an event before linking it, so the check should never fire; if it does, it has found a bug that today would have shipped as a missing dependency. Applying fills after the edits gives the same DAG: `AddEvent` and `AddDependency` only touch `dag_` and the pointer-keyed `ptr_to_vertex_` map, and the only field the DAG ever reads is the job index (for ordering), which fills do not change. Today the setters run earlier only because that was the convenient place.

**What this buys:**

- **A failed solve leaves `ctx` untouched.** Today a failure halfway through has already added events and edges to `ctx->events`. `Plan` throws the whole response away in that case, so it does not matter yet, but it blocks any future “drop the failing job and retry the rest” (section 2: failure is all-or-nothing).
- **Tests can assert exactly what the solver decided:** “filled tray 23 into event 1, added one move T23 → P24, one edge to event 1”, without diffing whole DAGs.
- **The benchmark (SW2-487) can time `Solve` alone**, with no DAG mutation in the measurement, and compare `Result`s between solvers.
- **A `FakeSolver` is trivial:** it returns a canned `Result`.

**Limits to be honest about.** `const ScheduleEventDag&` stops structural edits, but `GetEventFromVertex` still hands out `std::shared_ptr<ScheduleEvent>` to non-const events, so the compiler does not stop a solver from calling a setter. The rule is enforced by review and by one test: snapshot every event's fields before `Solve`, compare after. Changing `planner_core` to hand out `shared_ptr<const ScheduleEvent>` would make it a compile error, but that is outside this refactor.

### 6.6 Free-function signatures and the `Plan()` call site

The types in 6.1 cover the solver itself. These are the public pure functions that both `DefaultSolver` and job planning call:

```cpp
// PROPOSED — include/scheduler/tray_assignment/empty_tray.hpp and blocking_trays.hpp
namespace volley::tray_assignment {

struct TrayChoice { uint16_t tray_id; GaragePoseMsg dest; };   // dest heading may follow the tray
[[nodiscard]] stdx::Expected<TrayChoice> ChooseEmptyTray(
    const common::GarageServices& svc, const DiscreteGarageState& state, const GaragePoseMsg& dest);

struct PlannedTrayMove { std::shared_ptr<TrayMove> move; std::vector<GaragePoseMsg> path; };  // path empty if recursive
struct BlockingResolution { GaragePoseMsg dest; std::vector<PlannedTrayMove> required_moves; };

struct ResolveRequest {                       // named fields replace today's 7 positional parameters
  uint16_t tray_id;
  size_t job_index;
  const DiscreteGarageState& base_state;
  std::set<uint16_t> immobile_trays = {};
  VertexCollisionIdMap illegal_poses = {};
  bool enforce_retrieval_heading = false;
  bool allow_waypoint_stash = true;
};
[[nodiscard]] stdx::Expected<BlockingResolution> ResolveBlockingTrays(
    const common::GarageServices& svc, const ResolveRequest& request);

struct ParkingPlan { GaragePoseMsg dest; std::vector<PlannedTrayMove> required_moves; };  // dest heading final
[[nodiscard]] stdx::Expected<ParkingPlan> ChooseParkingSpot(
    const common::GarageServices& svc, const DiscreteGarageState& state, uint16_t tray_id, size_t job_index);

}  // namespace volley::tray_assignment
```

`ResolveRequest` is worth its few lines: today's main-loop call is `ResolveBlockingTrays(blocking_tray_id, move->GetJobIndex(), working_state, std::set<uint16_t>{move->GetTrayId().value()}, WithPriorDests(blocking_tray_id, critical_path))`, and the `AssignDestForUntargetedMove` call passes `{}, {}` positionally. With designated initializers the call says what each value is:

```cpp
// PROPOSED — inside Pass / DefaultSolver
auto resolution = ResolveBlockingTrays(svc, {.tray_id = blocker,
                                             .job_index = root.GetJobIndex(),
                                             .base_state = pass.State(),
                                             .immobile_trays = {root_tray},
                                             .illegal_poses = WithPriorDests(blocker, critical.vertices)});
if(!resolution) { /* fallback 1, then fallback 2, as today */ }
```

And the call site in `Plan()`, with today's failure contract unchanged (section 2):

```cpp
// PROPOSED — src/scheduler.cpp, Scheduler::Plan
// this         : const Scheduler*
// services_    : common::GarageServices, new member declared after gg_, table_, cost_model_, layout_
// tray_solver_ : std::unique_ptr<tray_assignment::Solver>, new member declared after services_
auto assigned = tray_solver_->Solve({plan_ctx->initial_state, plan_ctx->events})
                    .and_then([&](const tray_assignment::Result& r) {
                      return tray_assignment::ApplyTrayAssignment(*plan_ctx, r);
                    });
if(!assigned) {
  result.success = true;                                    // unchanged: the call succeeded...
  result.message = "Failed tray assignments: " + assigned.error();
  for(const auto& job : request_data.pending_jobs) {        // ...and every pending job fails
    result.scheduled_jobs.push_back(FailJob(job, assigned.error()));
  }
  return result;
}
```

**Lifetime rule.** `GarageServices` and `DefaultSolver` hold references into the `Scheduler`. Declare `services_` after `gg_`, `table_`, `cost_model_` and `layout_`, and `tray_solver_` after `services_`, so they are destroyed first. A test that builds a solver directly must keep the graph, table, cost model and layout alive for the solver's lifetime.

### 6.7 AGV assignment: same layout and error type now, returned result later

The `agv_assignment` folder, `stdx::Expected` and pure helpers apply directly: the cost estimates (`GetJustMovingCost`, shared with `PlanAgvChargeJob`; `GetAgvToTrayAssignmentCost`; `GetAgvOccupiedDuration`), feasibility checks and matching inputs are queries over const services and a state, and `BottleneckAssignment` is already external.

Returning a result is harder there, for reasons visible in the code:

- The AGV tree **reads the DAG it is building.** It consumes `event_dag_copy` root by root (`event_dag_copy.Remove(root_event)`), and `EnsureAgvMovePathsClear` repeatedly inspects edges added earlier in the same stage (up to 256 repair passes), followed by `Reduce()`.
- It **reads back fields it set**: `SetAgvId` on a `TrayMove`, then `GetAgvId()` on candidate moves while building later dependencies.

An edit log could still work, if the solver keeps a private *structural* copy of the DAG (the default copy constructor copies `dag_` and `ptr_to_vertex_`, so the copy shares the events), applies every edit to that copy as it goes, and logs it, including a `Reduce` step. The log must name events by pointer, never by vertex: `Remove` on the work-queue copy renumbers its vertices. The field reads are the real obstacle: they would need either cloned events with an identity map (and `planner_core` has no `Clone()`, see 6.5), or a side table (`agv_of[event]`) replacing every `GetAgvId()` read, which touches parity-sensitive code. **Recommendation:** for stage F, use the same layout and `stdx` types, and give the AGV solver an `Input` plus an explicitly mutable `ScheduleEventDag&` (named as such in the signature). Convert it to a returned result after the benchmarks exist and can prove nothing changed.

```cpp
// PROPOSED — sketch only; include/scheduler/agv_assignment/solver.hpp
namespace volley::agv_assignment {
struct Input {
  const DiscreteGarageState& initial_state;                                 // plan_ctx->initial_state
  const std::unordered_map<uint16_t, ScheduleEventSPtr>& first_tray_event;  // from tray_assignment::Result
};
class Solver {
 public:
  virtual ~Solver() = default;
  // events is edited in place in the first pass (see 6.7); the name says so.
  [[nodiscard]] virtual stdx::Result SolveInPlace(const Input& input, ScheduleEventDag& events) const = 0;
};
}  // namespace volley::agv_assignment
```

## 7. Key invariants to maintain

1. Every `TrayMove` that will execute has a tray id and a destination after tray assignment.
2. The DAG stays acyclic; `GetTopologicalOrdering()` must succeed after each solver.
3. Each tray's moves form a chain in physical order, and `first_tray_event[tray_id]` is that tray's first move (not its last; using the last creates cycles when one AGV moves a tray twice).
4. Blocking-tray moves are created in recursive prerequisite order, and a tray already being moved is not chosen to move again in the same resolution.
5. AGV matches respect disabled AGVs, AGVs trapped in a bay that is not `STATE_READY_TO_RETRIEVE`, reachability, collisions, lift state and AGVs already busy.
6. Arrival ordering never puts two AGVs on one node: `AddNodeArrivalDeps` and `EnsureAgvMovePathsClear` keep doing their jobs.
7. `Scheduler::Plan` output is unchanged, apart from log text. The DAG side is deterministic for a given build order (job index first, then heap order); remaining variation comes from `unordered_map` iteration elsewhere, for example the order of `result.scheduled_jobs` (doc 01, section 13).
8. `Reduce()` and path-repair placement stay where they are during extraction.
9. `tray_assignment::Solver::Solve` changes nothing reachable from its `Input`; `ApplyTrayAssignment` is the only place tray assignment writes `ctx`. A test snapshots every event's fields before `Solve` and compares after.
10. `ApplyTrayAssignment` replays `Result::edits` in recorded order, so vertex indices, edge sets **and the order of each vertex's out-edges** match what `DoTrayAssignments` builds today. The last one matters: `ScheduleEventDag::GetTopologicalOrdering()` breaks ties inside a job by heap order, which follows push order, which follows out-edge order (doc 01, section 12.5).
11. Every event is in the DAG once. `AddEvent` refuses a pointer that is already present, so a solver must never record `AddEvent` for an event of the input DAG.

Invariant 4 in a picture (illustrative; real graphs and paths depend on the layout):

![Garage setup](figures/03_garage_xy.svg)

<sub>Pan / zoom: [interactive viewer](figures/viewer.html#03_garage_xy) · [standalone SVG](figures/03_garage_xy.svg)</sub>

**Figure 8 — Top-down garage setup.** AGV 1 faces +x and carries tray T1 toward the goal. Trays T2 and T3 sit on the route, so two prerequisite tray moves (T2 → S3, T3 → S4) must finish first; they are independent of each other. Coordinates are schematic, not a customer layout.

## 8. Staged plan

A move-only refactor is risky because the helpers in section 3 are shared with job planning. Moving them blindly either breaks those callers or recreates the coupling through a back-pointer to `Scheduler`.

| Stage | Change | Exit criterion |
|---|---|---|
| A — baseline | Pin the commit, build, run the 72 active tests; record output DAGs (`debug/printdags`) and `ScheduledJobDataMsg` lists for curated fixtures | Reproducible behaviour captured |
| B — dependency map | Confirm Figure 1 against the branch; decide where the five shared helpers live | Ownership design written down |
| C1 — pure helpers in place | Still inside `scheduler.cpp`: turn the heading helpers, `AssignTrayIdForEmptyMove` (→ `ChooseEmptyTray`), `ResolveBlockingTrays` and the inline main-loop blocks into free functions over `GarageServices` returning `stdx::Expected`; job planning calls them too. Merge the two emission blocks | All tests and DAG snapshots identical; new unit tests for each pure function |
| C2 — tray module | Create the `common/` and `tray_assignment/` subfolders under `include/scheduler/`, `src/` and `test/` (section 6.2) and add the files to `CMakeLists.txt`; move the pure functions; add `Solver`, `Input`, `Result`, `Pass`, `DefaultSolver`, `ApplyTrayAssignment` | A test constructs `DefaultSolver` without a `Scheduler`; invariant 9 test passes |
| D — tray migration | `Plan` calls `Solve` + `ApplyTrayAssignment`; keep `DoTrayAssignments` temporarily for side-by-side comparison of the two DAGs | All tests and DAG snapshots identical |
| E — tray cleanup | Delete `DoTrayAssignments` and the old members; port the 4 direct `DoTrayAssignments` tests and the `ResolveBlockingTrays` test to `tray_assignment/test` | No production call to the old methods |
| F — AGV module | `agv_assignment/` with the same layout and `stdx` types; pure cost helpers; `SolveInPlace(input, events)` (section 6.7); port the 9 direct tests | Same behaviour and coverage |
| G — benchmarks | ≥10 real-site scenarios per solver, timed in a pinned environment | Results stored with metadata, no regressions |
| H — final cleanup | Remove legacy code; run full system and advanced suites | Definition of Done demonstrable |

**Ticket mapping:** check SW2-769's package structure against the current branch. SW2-484 is the natural first implementation ticket, and C1 is a good first PR inside it: no new files outside `scheduler.cpp`, easy to review for parity. SW2-487 can start as soon as baseline capture is deterministic. No AGV-specific child tickets were supplied, so none are named here.

## 9. Decisions to resolve in review

| Decision | Initial recommendation | Evidence needed |
|---|---|---|
| Input/output style | Tray: read-only `Input`, returned `stdx::Expected<Result>` (edit log) applied by `Scheduler` (6.5). AGV: explicit `ScheduleEventDag&` for the first pass (6.7) | Confirmed in `planner_core`: `TrayMove` copy-constructible, `Apply` is `const`; replay order gives identical DAG snapshots |
| Error reporting | `stdx::Expected<T>` / `stdx::Result` with `std::string` errors; `std::optional` only for internal “found nothing” searches (6.4) | Tests that match error text; `std::to_string` vs a `std::formatter<GaragePoseMsg>` |
| Which functions stay members | Only the solver's `Solve` and the private `Pass`; everything else becomes a pure free function over `GarageServices` (6.3) | Each pure function's unit test passes without a `Scheduler` |
| Folder layout and names | Subfolders `common/`, `tray_assignment/`, `agv_assignment/` under `include/scheduler/`, `src/` and `test/`; one `CMakeLists.txt`; private headers in `src/<module>/`; namespaces to match (6.2) | `volley_add_library` exports only `include/`; CI include check for dependency direction |
| Virtual interface vs templates | Virtual `Solve`, owned by `Scheduler` through `std::unique_ptr` | Existing code style, whether plugins must swap solvers at runtime |
| Where interfaces live | Small, low-dependency header package | `colcon graph`, `package.xml`, exported CMake targets |
| Where default solvers live | Scheduler library sub-module first | Avoid new group-level dependency cycles |
| Benchmarks | Direct solver benchmark plus optional end-to-end `Plan` benchmark | Fixtures, harness, timing environment |
| What "same result" means | Same tray/AGV assignments, same edge set after `Reduce`, same final state and errors | Stable event identifiers. Tie-breaking is now known: identical `AddEvent`/`AddDependency` sequences give identical orders; otherwise compare orders per job index |
| `planner_core` changes | None for parity. Later candidates: `[[nodiscard]]` on `AddDependency` (or an error for missing endpoints), a virtual `Clone()` on `ScheduleEvent`, `shared_ptr<const ScheduleEvent>` accessors for read-only users | Agreement from the `planner_core` owners; every other planner package depends on it |

## 10. Risks that must not be silently "fixed"

These are behaviours a reviewer may want to change. Changing them during extraction breaks parity.

1. `GetAgvOccupiedDuration` always returns `Duration::zero()` (`// TODO(isabel) implement!`). The matching costs depend on that.
2. `Reduce()` runs inside `DoAgvAssignments` *and* again in `Plan`. The `TODO` above the second call says planning may fail without it; nobody has confirmed why.
3. `DoTrayAssignments` postpones DAG reduction until after AGV assignment (“Reduce here breaks the AgvAssignments for some reason”); moving it earlier is high risk. A likely reason, now that `Reduce()` is readable: AGV assignment has code that looks only at **direct** edges. `PropagateEventCostToChildren` passes a matched tray move's cost to its direct children only, and only tray moves propagate; if `Reduce()` replaces a direct edge “tray move A → tray move C” with the path “A → bay transition → C”, C never sees A's cost and the matching changes. `AddDepsAfterAmiga` also inspects only direct in- and out-edges (and already runs after the reduction at the end of `DoAgvAssignments`). Treat this as a hypothesis to test, not a fix.
4. `TrayMove::Apply` treats blank fields specially (`planner_core/src/schedule_events.cpp`): no tray id → no-op; no destination → the tray and its payload are **removed** from the state; a tray already on the destination is moved to `0@0`. Later jobs' `working_state` depends on this; a solver that replays half-specified moves must reproduce it exactly.
5. `ScheduleEventDag` uses pointer identity and Boost `vecS` vertex indices. Removing a vertex shifts every later index down by one (the comment in `RemoveVertexHelper` says so), and CHUGG maps motions back to events by vertex index, so never remove from `ctx->events` and never cache vertex descriptors across `Remove`.
6. `AddDependency` never checks for cycles and returns `false` silently when an endpoint is missing; `WouldCreateCycle` returns `false` ("safe") in the same case. A refactor that reorders `AddEvent` and `AddDependency` calls can drop edges without any error.
7. Test names such as `576_eccles_half` and `1355_fulton` suggest real sites, but `tiny_lot` and `triple_pick_lot` are synthetic. Record which layouts are real before counting them toward the 10-scenario goal.
8. SW2-905 (insert fails when an AGV collides with the chosen parking node) is in the parent ticket; that does not mean the refactor causes it.
9. In fallback 1 (“advance the root tray”), the path recorded for the advance move is `std::vector<GaragePoseMsg>{gg_.GetVertexFromPose(tray_opt->pose).value(), advance_move->GetDest().value()}` (`:2842`–`:2844`). Its first element is a graph *vertex* converted to a `GaragePoseMsg`, and `tray_opt` was already refreshed to the post-advance pose. The `freeing_moves` edges built from that path may therefore be wrong. Reproduce it with a test before touching it; when `TryAdvanceRoot` returns a `PlannedTrayMove`, keep the same path until then.

## 11. Next actions

1. In the ROS container, build and run `colcon test --packages-select planner_core scheduler scheduler_advanced_tests`, then `colcon test-result --verbose` to capture the baseline.
2. Confirm the branch matches this snapshot; keep edits in small reviewable commits.
3. Map symbol use from the repository root: `rg -n 'ResolveBlockingTrays|DoTrayAssignments|DoAgvAssignments|first_tray_event|BottleneckAssignment'`. Compare with Figure 1, and rebuild Figure 1 (`python3 scripts/diagrams/build.py 34`) after replacing `sources/repomix-scheduler.xml` with a newer snapshot.
