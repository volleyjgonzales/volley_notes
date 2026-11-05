# Assessment: clean-ups in cost_functions and motion_planner that make the scheduler more readable

Written 2026-10-30 on `jmg/SW2-1135/scheduler-renames-and-cleanups` at `1a76c027`, from a subagent
survey of the two packages spot-checked here. Read-only; nothing changed. Also answers the
Fail / FailRetryable question.

## 0. Fail and FailRetryable

One function with one differing field. 59 sites use `Fail`, two (ExpandRetrieveJob) use
`FailRetryable`. A single `Fail(is_retryable, fmt, args...)` puts a flag on 59 calls to serve two.
Recommendation: keep `Fail` alone, delete `FailRetryable` and its doc, and spell the two retryable
sites out with `stdx::Unexpected(JobFailure {.message = std::format(...), .is_retryable = true})`,
where the flag is visible at the point that matters. Lands in commit 9 (introduced there) or as a
one-line change on the tip.

## 1. What the scheduler uses, and what hurts

The scheduler touches a small surface of the two packages: `Interval::Duration` (51 mentions),
`Motion`, `GraphFilterProperties`, `ContinuousState`, the three blocking-tray search environments
with `SingleSourceSearch`, `GetPosePath`, `ConvertPosePathToTrajectory`, `GetStaticFilter`,
`HideAgvs`, `Chugg` with `GetEdgeDurations` + `GetAllPairsMinCost`, and `cost::MotionCostModel`
with `CostVector`. Ranked by how much a scheduler reader gains:

| # | where | item | blast radius |
|---|---|---|---|
| 1 | motion_planner | The blocking-tray searches expose the A* plumbing. The scheduler repeats a six-line ritual four times (tray_assignment.cpp 114-122, 159-169, 313-322, 517-523): build a `BlockingTrayState`, set `.vert` from the pose, construct an environment with 8-11 positional arguments, call `SingleSourceSearch(state, Duration(0), env)`, read `GetTarget().value().vert` back into a pose. Proposal: three pose-based free functions in `blocking_tray_search.hpp`, `FindOpenSpaceForTray`, `FindNearestEmptyTray`, `FindPathThroughBlockingTrays`, returning result structs (vertices in order plus the blocking tray ids the scheduler today rebuilds at 530-560); the environment classes stay as the implementation. | motion_planner 3 files (16 constructor sites in its test), scheduler 2 |
| 2 | motion_planner | `OpenSpaceSearchEnvironment` takes 11 positional parameters, five optional, two trailing bools; the scheduler passes `std::nullopt` to reach the bools. Proposal: an options struct with designated initialisers and `is_*` flag names; folds into item 1. The constructor also logs and continues on a missing tray or payload instead of failing. | motion_planner 3, scheduler 1 |
| 3 | motion_planner | `GetStaticFilter(collision_id, gg, dgs, ctable, ignore_trays, ignore_agvs, ignore_bays)`: "static" reads as the C++ keyword, the function builds a keep-out mask, the abbreviations and three same-typed sets invite swaps; four of six scheduler calls pass two empty sets, and `BuildImmobileTrayFilter` exists only to invert the ignore semantics. Proposal: `BuildKeepOutFilter(collision_id, graph, state, collision_table, IgnoredEntities{...})`, the scheduler's own vocabulary (`keep_out_filter_by_footprint`). Already pure. | motion_planner 6 (about 15 calls), scheduler 5 |
| 4 | motion_planner | `ConvertPosePathToTrajectory` needs an entity id, an unnamed collision id, an action id, a start time and an audit pointer to yield a duration; `ComputeTravelDuration` fakes a trajectory to measure a path. Proposal: `ComputePathDuration(graph, cost_model, source, target, filters, is_agv_loaded)` next to `GetPosePath`, summing `cost_model.Duration` over the coalesced runs; `ComputeTravelDuration` becomes one line. | motion_planner 3, scheduler 1 |
| 5 | motion_planner | `GetPosePath` returns an empty vector both for "no path" and for "pose not in the graph", and runs an A* per call under a "Get" name. Proposal: `FindPosePath` returning `std::optional`, with an unknown pose reported apart. | motion_planner 3, scheduler 3 files / 5 calls |
| 6 | motion_planner | `HideAgvs` returns `std::pair<bool, map>`. Proposal: `FindAgvHidingPoses` returning `std::optional<map>`. Pure. | motion_planner 3, scheduler 1 |
| 7 | motion_planner | `BlockingTrayState::vert` and `GraphFilterProperties::AddProperty(edge, bool)` (it sets the enabled flag). Proposal: `vertex`, `SetEnabled`. Item 1 removes the scheduler's reads of `vert`. | motion_planner 3, scheduler 1 / 0 |
| 8 | motion_planner | `PlanMotions` seeds Chugg by hand: `GetEdgeDurations`, `GetAllPairsMinCost(graph, durations, Duration(0), Duration::max())`, an eight-argument constructor; five motion_planner tests repeat the same lines, and the admissibility caveat lives in a scheduler comment. Proposal: `BuildSippHeuristics(graph, cost_model)` returning Chugg's `HeuristicMap`, with the caveat on it; `Compute*` names for the two pure functions. | motion_planner 7 / 5, scheduler 1 |
| 9 | both | Two duration types: `Interval::Duration` (nanoseconds) and `cost::SecondsF` (float seconds); the scheduler converts by hand in three places and motion_planner in seven, with a private `ToIntervalDuration` in garage_graph_pathing.cpp that would serve all. Proposal: publish the two conversions in `interval.hpp`. | motion_planner 7, scheduler 3 |
| 10 | cost_functions | `MotionCostModel` only ever produces time, but its `Duration` overloads return `SecondsF` while `MotionCostParams::events` are raw floats; the scheduler casts lift times and adds VRC door and transit floats in utils.cpp. Proposal: typed accessors on the model, `LiftDuration(is_raising)`, `VrcFloorTransitDuration(src_z, dst_z)` (moving `ComputeVrcFloorTransitDuration` from scheduler utils), `BayDoorDuration`; keep the class name (22 files, also `vrc`). | cost_functions 3, motion_planner 15 (name only), scheduler 3 |
| 11 | cost_functions | `CostVector` / `CostEntry` have public trailing-underscore fields (`entries_`, `duration_`, `explanation_`) and lower-case methods (`push`, `eval`, `value`); the scheduler's audit printing reads them. Proposal: `CostAudit` with `Add`, `Entries()`, `Total()`, plain field names. | cost_functions 4, motion_planner 4, scheduler 1 |
| 12 | motion_planner | Search "cost" is a score: travel time plus a 30 s penalty per newly blocking tray (`blocking_tray_search.cpp` 38-58, magic `30s`), and the AGV-hiding search counts hops as `Interval::Duration`. The scheduler never reads it but a reader assumes travel time. Proposal: a named `kBlockingTrayPenalty` and a class comment, or a distinct score type. | motion_planner 2, scheduler 0 |
| 13 | motion_planner | Small names: `Motion::GetDelta()` (the discrete state change, string-typed; the scheduler dispatches on `type == "AgvPoseChanged"` and deserialises) → `GetStateChange()` plus typed accessors; `ContinuousState::GetTrajectories()` vs `GetTrajectoryMap()` (same data, const vs mutable); `BayIsReadyToRetrieve` → `IsBayReadyToRetrieve`; `SearchSolution::GetTarget()` → `GetGoal()`; `Chugg` parameter `geometry` for a collision table. | motion_planner internal mostly, scheduler 2-4 |

Names that mislead without being used by the scheduler: `AgvSearchEnvironment` (the hiding
search) beside `GarageGraphEnvironment` (the pose-path search); `GetEdgeMarginalDurations`, a
rejected heuristic input the scheduler comment has to explain; `Chugg::SolveCbs` beside
`SolveSequential` (only the latter is used); `Interval::Before` compares begins only, and the
scheduler's `MotionScheduleOrder` reimplements that order; `kMaxExpansions = 5000000` truncates a
search silently, which the scheduler reports as "failed to find path".

## 2. Pure-function candidates

Already free and pure, only misnamed: `GetStaticFilter`, `GetPosePath`, `HideAgvs`,
`GetEdgeDurations`, `GetAllPairsMinCost`. Scheduler members that become one-liners or move out once
items 1, 4 and 10 land: `ComputeTravelDuration`, `ComputeAgvLiftDuration`,
`ComputeVrcFloorTransitDuration` (utils.cpp), `BuildImmobileTrayFilter`, and the search blocks of
`FindDestinationForRootTray`, `FindBlockingTrayResolution`, `PickEmptyTrayForMove` and
`AssignTrays`. `MotionCostModel`'s duration overloads read only the model's parameters and their
argument, so the typed accessors of item 10 are free functions of the model in all but syntax.

## 3. Where to do it

- **Not in this PR, except item 0.** Every item above changes a header another package owns and
  its tests (16 constructor sites in the blocking-tray test alone); this PR already spans five
  packages and twelve commits. A scheduler-local adapter for the search ritual would be thrown
  away when the upstream functions land, so it is not worth a commit either.
- **A stage of its own before C1**, since C1 defines `GarageServices` around exactly these APIs
  (`PROMPT.md` 6.2): one ticket, "motion_planner and cost_functions APIs the scheduler calls",
  with one commit per item in the order above, each behaviour-neutral and guarded by the recorded
  scenarios plus the two packages' own tests. Items 1 to 8 are the readability win; 9 to 13 are
  cheap mechanical follow-ups in the same ticket.
- **Keep the class name `MotionCostModel`**: it reaches `vrc`; the accessors are additive.
