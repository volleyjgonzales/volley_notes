# Jira ticket drafts for epic SW2-482 (drafted 2026-11-09)

The next eight work items of the epic, combined to keep the number of PRs down: one PR per ticket.
Three expand tickets that exist (SW2-1170, SW2-1171, SW2-1172), one rewrites SW2-484, three are
new (SW2-1203, SW2-1204, SW2-1205), and SW2-1190 is unchanged. Code references are to `main` at
`1c5b0473`. Applied to Jira on 2026-11-09.

Each one is a **Task** under epic SW2-482, label `Scheduler_and_Dispatcher`, priority Medium,
assignee Jon M Gonzales. The *Links* line of each ticket lists its "is blocked by" links. In acli
the `--in` ticket gets the link's verb: `jira workitem link create --in <blocker> --out <this
ticket> --type Blocks --yes` reads "`<blocker>` blocks `<this ticket>`".

| # | Ticket | Summary | Blocked by |
|---|---|---|---|
| 1 | SW2-1190 | Evict parked AGVs from a move tray job's explicit destination | SW2-905 |
| 2 | SW2-1171 | Report why motion planning failed, and clean up the motion planner | - |
| 3 | SW2-1170 | Return stdx::Result from event application, and rename planner_core's types | SW2-905 |
| 4 | SW2-1172 | Move the scheduler to rclcppx and keep ROS types at its boundary | - |
| 5 | SW2-1203 | Extract tray assignment's decisions into a tray_assignment module | SW2-1190, SW2-1192 |
| 6 | SW2-484 | Put tray assignment behind a solver interface | SW2-1203 |
| 7 | SW2-1204 | Split the scheduler into one library per planning stage | SW2-484 |
| 8 | SW2-1205 | Move AGV assignment into an agv_assignment module | SW2-1204 |

Order: SW2-905 merges on 2026-11-10, then SW2-1171 is next and SW2-1190 waits. 2, 3 and 4 touch
`motion_planner`, `planner_core` and the scheduler's ROS layer, not `tray_assignment.cpp`, so they
do not conflict with SW2-1190 or SW2-1192 whenever those run. 5 to 8 follow in order, after
SW2-1190 and SW2-1192.

---

## 1. SW2-1190: Evict parked AGVs from a move tray job's explicit destination

No change: in progress, its description is current. Links: is blocked by SW2-905 (exists).

---

## 2. SW2-1171: Report why motion planning failed, and clean up the motion planner

New summary (was "Report why motion planning failed"). Links: none.

### Description

#### Objective

When motion planning fails, `Plan()` reports "CHUGG failed to find a solution, event dag may be
infeasible" for every job. The real reason (a colliding solution, an AGV move with no trajectory, a
tray move that could not be planned) is only logged inside `motion_planner`. Carry it to the plan
response, so operators and tests see why.

The same files carry the motion-planner clean-up deferred from the reviews of PR #1018. It goes in
the same PR, one commit per theme, so `motion_planner` is reviewed once.

#### Scope

Failure reasons:

- `Chugg::SolveSequential` returns `stdx::Expected<ContinuousState>`. The per-node and per-event
  planning (`PlanNodeSequential`, `PlanEventSequential`) return `stdx::Result` with the texts they
  log today.
- `Scheduler::PlanMotions` returns `stdx::Expected<ContinuousState>` (today `std::optional`), and
  `Plan()` reports the reason in place of the generic text.
- An unhandled event fails: `PlanNodeSequential` dispatches AGV, tray, bay and VECS events but not
  VRC transitions, though a VRC overload exists, and an event it does not dispatch plans as a
  success. Dispatch VRC transitions, and make any other unhandled event a failure. The scheduler
  cannot produce the case today; add a test in `chugg_tests.cpp`.
- The four `SolveSequential` calls in `chugg_tests.cpp` follow.

CHUGG clean-up, no behaviour change:

- Name the class and its files for what they do: plan trajectories for the event DAG (name settled in
  review, for example `EventTrajectoryPlanner`).
- The header describes sequential planning, the only mode used. Remove the commented-out methods
  and banners. Remove `SolveCbs` and `chugg_cbs.cpp`: nothing calls them, tests included.
- Clearer names for `geometry_`, `init_traj_`, `EntityCurrentTime`, `GetStaticConstraintsCopy`,
  `GetUpdatedContinuousState`, `InitializeEventOrder`, `GetBaysMovingAfter` and
  `GetVexenMovingAfter`, matching the scheduler's (`collision_table_`, `initial_state`).
  `GetEventEntity` returns the AGV for a tray move: name or document it.
- `Node` holds shared planning state and search state: rename its fields so the two read apart
  (splitting it is out of scope).
- `stdx::ScopeExit` instead of restoring by hand after `SetEventSafeIntervals` and `AuditScope`.
- `GetVexenMovingAfter` replays every event into a state it never reads: remove the replay.

`static_graph_filtering` clean-up, no behaviour change:

- Extract `CollectDisabledNodeIds`, `CollectObstacleExclusions`, `CollectDisabledNodeExclusions`
  and `CollectOversizeExclusions` from the filter builders, keeping the order in which a disabled
  object's node is collected before the ignore check.
- A `BlockedGraphLocations` struct for the blocked poses and edges, an `IgnoredObstacles` struct for
  the three ignore sets, and a local `add_filter_if_missing` helper.
- A moving AGV is checked against an AGV obstacle with the TRAY footprint. Document it as
  intended, or fix it with its own test and recording diff.

#### Definition of Done

- A failed plan's message names the event or collision that failed.
- The changed failure messages in the recorded scenarios are reviewed as a diff, not re-recorded
  blindly. Successful plans are unchanged (`SCHEDULER_CHECK_RECORDINGS=1`).
- `motion_planner` (including `chugg_tests` and `static_graph_filtering_tests`), `scheduler` and
  `scheduler_advanced_tests` tests pass. Tidy is clean on the changed lines.

#### Out of scope

- Changing CHUGG's search, or splitting `Node`.
- Moving `PlanMotions` into its own library (the stage-split ticket).

---

## 3. SW2-1170: Return stdx::Result from event application, and rename planner_core's types

New summary (was "Return stdx::Result from event application (ApplyTo, ApplyBayCommand,
DiscreteGarageState)"). Links: is blocked by SW2-905 (its PR adds a stand-in this ticket removes).

### Description

#### Objective

`ScheduleEvent::ApplyTo` and `ApplyBayCommand` are the last `BoolStringPair` returns in the planner.
They call `DiscreteGarageState::OnEvent`, which central, bay and vecs also use. Give
`DiscreteGarageState` a `stdx::Result` method next to `OnEvent`, so the planner can use it without
migrating every caller at once. In the same pass over `planner_core`'s API, give its types the
names the scheduler now uses.

#### Scope

- `common_ros`: add `stdx::Result ApplyEvent(...)` to `DiscreteGarageState` for each `OnEvent`
  overload, with the same failure texts. `OnEvent` becomes a thin wrapper around it. `SucceededEvent`
  is never called with a message, so no caller loses a success text.
- `planner_core`: `ApplyTo` and `ApplyBayCommand` return `stdx::Result` and call `ApplyEvent`;
  `ScheduleEventDag::ApplyEventsTo` drops its conversion.
- `scheduler`: remove the `ApplyToWorkingState` stand-in in `tray_assignment.cpp` (added by
  SW2-905's PR #1036). Callers in `scheduler` and `motion_planner` follow.
- Rename `planner_core`'s types and methods, with `[[deprecated]]` aliases for the old names:
  `ScheduleEventDag` → `EventDag`, `SetDest` → `SetDestination`, and the other abbreviations found
  in a survey of `planner_core`'s headers (the PR lists them). Callers in this repository use the
  new names.

#### Definition of Done

- No `BoolStringPair` left in `planner_core`'s headers.
- No caller in the repository uses a deprecated name (the build shows no deprecation warning).
- The failure texts are unchanged. The scheduler's recorded scenarios are identical
  (`SCHEDULER_CHECK_RECORDINGS=1`).
- `common_ros`, `planner_core`, `scheduler`, `motion_planner` and `central` tests pass.

#### Out of scope

- Migrating central, bay and vecs off `OnEvent`, and deprecating it: a later ticket.
- Removing `common/types.hpp` from planner_core, which also needs a home for `EnumNameString` in stdx.
- Removing the deprecated aliases: a later clean-up, once no open branch uses the old names.

---

## 4. SW2-1172: Move the scheduler to rclcppx and keep ROS types at its boundary

New summary (was "Move the scheduler's node, component and parameters to rclcppx"). Links: none.

### Description

#### Objective

The scheduler logs and creates its services through `rclcppx`, but its node, component and
parameter reads still come from `common_ros` (`common_ros/node.hpp`, `common_ros/component.hpp`,
`node->Param<T>`). Move them to `rclcppx` (`node.hpp`, `component.hpp`, `parameter.hpp`), so the
package uses one ROS layer.

Inside the planner, the per-plan context (`PlanContext`) still holds ROS types: an `rclcpp::Time`
constructor, `interfaces::msg::ScheduledJobData` jobs, and events keyed by
`interfaces::msg::GarageEntityId`. Convert at the boundary instead, so planning code works on the
scheduler's own types.

#### Scope

rclcppx:

- `scheduler_component.cpp`: the component and its 23 parameter reads.
- `scheduler_ros.hpp` and `scheduler_ros.cpp`: the node handle and the `printdags` parameter.
- Any other `common_ros` ROS wrapper the scheduler uses.

Domain types at the boundary, each one mechanical commit:

- `AssetId` / `AssetType` for garage entities, with conversions in one place
  (`ros/convert.hpp`: `ToAssetId`, `ToMsg`). `PlanContext::last_event_by_entity` is keyed by
  `AssetId`.
- A `ScheduledJob` type in place of `interfaces::msg::ScheduledJobData` inside the context; the
  response converts it back.
- `PlanContext` is constructed from a timepoint, not an `rclcpp::Time`.
- `ExcludeCommittedResources` is renamed for what it does (reserves the base schedule's assets,
  for example `ReserveBaseScheduleAssets`).

#### Definition of Done

- The scheduler includes no `common_ros` node, component or parameter header.
- `plan_context.hpp` includes no `interfaces/msg` or `rclcpp` header.
- Parameter names, defaults and the handling of a missing parameter are unchanged. The recorded
  scenarios are identical (`SCHEDULER_CHECK_RECORDINGS=1`).
- Checked in simulation: the node starts, reads its parameters, and answers the `plan` and
  `set_bay_readiness_ratio` services. CI's simulated system tests pass.

#### Out of scope

- Domain types that live in `common_ros` (`DiscreteGarageState`, `GarageGraph`, `Layout`).
- Other packages' use of the `common_ros` wrappers.
- ROS types inside the planning stages beyond `PlanContext` (each stage's module ticket).

---

## 5. SW2-1203: Extract tray assignment's decisions into a tray_assignment module

Links: is blocked by SW2-1190 and SW2-1192 (both change `tray_assignment.cpp`); blocks SW2-484.

### Description

#### Objective

Tray assignment is a set of `Scheduler` member functions in `tray_assignment.cpp` that decide and
write to the event DAG in the same place, and two copies of the code that emits tray moves. Turn its
decisions into free functions in a module with its own library and test target, so each can be
tested without a `Scheduler` and a solver can be built on them (SW2-484). No behaviour change.

#### Scope

- A `GarageServices` bundle (motion graph, collision table, cost model, layout, logger), owned by
  `Scheduler` and passed to the module's functions.
- A `scheduler_tray_assignment` library and its own gtest, which links the library without the
  scheduler's.
- As free functions that return their result instead of editing a move: the tray heading helpers
  (EV charging, retrieval, preferred heading) and the empty-tray choice (today
  `AssignEmptyTrayToMove`).
- `ResolveBlockingTrays`, with its two searches (`FindDestinationForRootTray`,
  `FindBlockingTrayResolution`), as a free function that returns plain planned moves, not events.
- The main loop's decisions as pure functions: whether a destination is usable, the root tray's
  path, the trays blocking a path (by footprint, not only node), and the parking-spot choice (from
  `AssignDestinationAndUnblockingMoves`).
- One function that emits a chain of tray moves and one that commits the root move, in place of the
  two copies. The differences between the copies stay, behind explicit options.
- The AGV-eviction search added by SW2-905 and SW2-1190 moves into the module the same way.
- Unit tests for each public function, on the recorded initial states.

#### Definition of Done

- The recorded scenarios are identical (`SCHEDULER_CHECK_RECORDINGS=1`), checked on every commit.
- The module test covers every public function and links without the scheduler library.
- `scheduler`, `scheduler_advanced_tests` and `planner_core` tests pass. Tidy is clean on added and
  moved code.

#### Out of scope

- The solver interface and removing the remaining members (SW2-484).
- Any behaviour change, including the known quirks: they are listed in the PR and fixed in SW2-484.

---

## 6. SW2-484: Put tray assignment behind a solver interface

New description (the current one is a sentence; this keeps its goal). Move the ticket back to To
Do and assign it: it has no PR yet. Links: is blocked by SW2-1203.

### Description

#### Objective

One of the goals of this epic is one algorithm for planning tray moves across job types. Put tray
assignment behind an abstract solver with plain-data input and output, with today's algorithm as
the first implementation, so other solvers can be tried against the same tests and benchmarks
(SW2-487).

#### Scope

- The interface, in plain data:
  - input: the initial garage state and the ordered steps of the plan, each a tray move request
    (tray and destination, either may be blank) or a state change (a bay or VECS transition);
  - result: the blanks filled, the new moves the solver adds (freeing and eviction moves), and the
    ordering edges, all by id;
  - a `Solver` class with one `Solve` method.
- `DefaultSolver`: today's loop over the module's functions (from SW2-1203), recording its moves and edges
  instead of writing the event DAG, in the same order. Occupancy is keyed by step and move id.
- An adapter that builds the input from the event DAG and applies the result back.
- `Scheduler::AssignTrays` runs the injected solver (`DefaultSolver` by default, a constructor
  parameter for tests). The legacy members are deleted.
- Then two behaviour fixes, each its own commit with its recording diff reviewed:
  - when several events occupy one pose, the order of their ordering edges depends on pointer
    hashes and can differ between runs: make it deterministic by id;
  - a tray move without a destination never registers its source and destination as occupied, so
    later moves are not ordered after it: register them.

#### Definition of Done

- `Plan()` keeps its failure contract and the `"Failed tray assignments: "` prefix. A fake solver
  injected in a test shows its error reported and every pending job failed.
- `DefaultSolver` is tested on hand-built inputs, without a `Scheduler` or a DAG: a clear move, a
  blank destination, a blank tray, a blocker on the path, a bay transition before a move into the
  bay, and two runs on the same input giving equal results.
- The recorded scenarios are identical except for the two fixes' reviewed diffs.
- `scheduler`, `scheduler_advanced_tests` and `planner_core` tests pass. Tidy is clean.

#### Out of scope

- A second solver, and the benchmarks (SW2-487).
- A solver interface for the whole scheduler: the problem-formulation draft in the epic's notes
  proposes one. This ticket uses its vocabulary where it fits.

---

## 7. SW2-1204: Split the scheduler into one library per planning stage

Links: is blocked by SW2-484.

### Description

#### Objective

After tray assignment, the other planning stages are still one library, so any stage can include
any other. Give each stage its own folder and library target, and check the boundaries in CI, so the
pipeline's structure is enforced, not just intended. No behaviour change.

#### Scope

- A folder and library target each for job expansion, validation, motion planning and the action
  graph, next to tray assignment's.
- Motion planning: `PlanMotions` becomes a free function.
- Action graph: the builders in the anonymous namespace and `InsertVrcActionsIntoDag` move into
  the library, with narrower inputs than the whole plan context.
- Each stage's tests move to its folder.
- An include-boundary check in CI: a stage includes another only through its declared dependency.

#### Definition of Done

- The recorded scenarios are identical (`SCHEDULER_CHECK_RECORDINGS=1`).
- The boundary check runs in CI and fails on a disallowed include.
- `scheduler` and `scheduler_advanced_tests` tests pass. Tidy is clean on moved code.

#### Out of scope

- AGV assignment (its own ticket).
- Changes inside a stage beyond what the move needs.

---

## 8. SW2-1205: Move AGV assignment into an agv_assignment module

Links: is blocked by SW2-1204.

### Description

#### Objective

AGV assignment is about twenty `Scheduler` member functions in `agv_assignment.cpp`, and it throws
on some failures instead of returning them. Give it the same module layout as tray assignment:
free functions over `GarageServices`, pure cost functions, its own library and tests. No behaviour
change, apart from failures being returned.

#### Scope

- `agv_assignment` folder, library and test target, in the layout of `tray_assignment`.
- The cost functions as pure functions: `ComputeAgvAssignmentCost`, `ComputeTravelDuration`,
  `ComputeAgvPickupDuration`, `ComputeAgvLiftDuration`, `ComputeAgvMoveDuration` and the edge
  costs.
- An entry point that still writes the event DAG (`SolveInPlace(input, event_dag)`), so the stage
  moves without a new interface.
- `stdx::Result` / `stdx::Expected` in place of the four `throw std::runtime_error` in
  `agv_assignment.cpp` (adding to or reading the AGV order DAG). `Plan()` reports them as job
  failures.
- The tests of `agv_assignment_tests.cpp` and `assignment_cost_tests.cpp` move to the module. New
  direct tests for path repair and for ordering AGV moves after blocking AGVs
  (`OrderAgvMovesAfterBlockingAgvs`).

#### Definition of Done

- The recorded scenarios are identical (`SCHEDULER_CHECK_RECORDINGS=1`).
- No `throw` left in AGV assignment. A test shows each former throw reported as a failure.
- The module test links without the scheduler library.
- `scheduler` and `scheduler_advanced_tests` tests pass. Tidy is clean.

#### Out of scope

- A solver interface for AGV assignment.
- Changing how AGVs are chosen or ordered.
