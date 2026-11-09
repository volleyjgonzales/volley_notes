# Naming proposal for PR #1036 (SW2-905), for an independent review

You are reviewing a proposal to rename code on a draft pull request in a ROS 2 (C++20) workspace.
Another reviewer wrote the proposal, so don't trust it. For each item, say whether the new name or
text is accurate to what the code does, and whether it reads clearly to someone who knows the
garage domain but not this code. Where you disagree, propose an alternative.

## Where things are

- Repository: `/home/jon-gonzales/volley`. Branch: `jmg/SW2-905/insert-stall-blocked-by-agv`, tip
  `a38e7eb8`, two commits on `main`. Review the range `main...HEAD`.
- Files in scope: `src/planner/scheduler/src/tray_assignment.cpp`,
  `src/planner/scheduler/include/scheduler/scheduler.hpp`,
  `src/planner/planner_core/src/event_dag.cpp`,
  `src/planner/scheduler/test/src/stages/tray_assignment_tests.cpp`.
- Read-only. Don't edit, stage, commit or push anything.
- Garage vocabulary: a **stall** is a parking spot. An AGV can sit on a stall. A tray sits on a
  stall, on an AGV, or on an AGV that is on a stall. An AGV carries a tray by driving under it.
  A **waypoint** is a node in a driving lane. Leaving a tray there ("stashing") is a last resort.
  **Evicting** an AGV means sending it to a free charger so a tray can use the stall it was on.

## 1. Failure messages: `t{}` and `a{}` become `tray {}` and `AGV {}`

The branch adds seven messages that name trays as `t{}` and AGVs as `a{}`. Readers must already
know the shorthand. Keep the four older `t{}` messages that are also on `main` (lines 171, 276,
485, 630) as they are; they're out of scope for this PR.

`even over the AGVs` in the first message refers to the internal flag (item 3). The search behind
it asks: where could this tray park if the parked AGVs were moved away? The new text says that,
in the same terms as the messages after it ("once the AGVs are moved").

| Line | Now | Proposed |
|---|---|---|
| 480 | `"t{} stays stashed on {}: {}"` | `"tray {} stays stashed on {}: {}"` |
| 664 | `"no stall for t{} even over the AGVs"` | `"no stall for tray {}, even with the parked AGVs moved away"` |
| 707 | `"no destination for t{} once the AGVs are moved"` | `"no destination for tray {} once the AGVs are moved"` |
| 710 | `"only a waypoint for t{} once the AGVs are moved"` | `"only a waypoint for tray {} once the AGVs are moved"` |
| 713 | `"the route of t{} to {} is not feasible"` | `"the route of tray {} to {} is not feasible"` |
| 721 | `"no free charger reachable for a{}"` | `"no free charger reachable for AGV {}"` |
| 738 | `"no charger placement for a{} keeps a feasible plan: {}"` | `"no charger placement for AGV {} keeps a feasible plan: {}"` |

No recorded scenario under `src/planner/scheduler/test/scenarios/` contains any of these strings,
so the recordings don't change.

Questions for you:
- Is "even with the parked AGVs moved away" accurate? Check what
  `ResolveByEvictingAgvs` excludes (disabled AGVs, loaded AGVs, the carrier, AGVs with moves later
  in the plan) against what the candidate search at line 662 actually ignores
  (`CollectIllegalPosesOfParkedAgvs` skips disabled AGVs and the carrier only).
- Does mixing the old `t{}` messages and the new `tray {}` ones in one file make things worse?

## 2. The topological-ordering comparator in `event_dag.cpp`

Now:

```cpp
// Min-heap on job index, then on creation order: of the vertices ready at each step, the earliest job's
// comes first, and within a job the one added first, so expansion's events replay before assignment's.
const auto later_first = [this](Vertex left, Vertex right) {
  const auto left_job = GetEvent(left)->GetJobIndex();
  const auto right_job = GetEvent(right)->GetJobIndex();
  return std::tie(left_job, left) > std::tie(right_job, right);
};
std::priority_queue<Vertex, std::vector<Vertex>, decltype(later_first)> ready_vertices(later_first);
```

Proposed:

```cpp
// Min-heap on job index, then on creation order: of the vertices ready at each step, the earliest job's
// comes first, and within a job the one added first, so expansion's events replay before assignment's.
const auto is_later_event = [this](Vertex lhs, Vertex rhs) {
  const auto lhs_job = GetEvent(lhs)->GetJobIndex();
  const auto rhs_job = GetEvent(rhs)->GetJobIndex();
  return std::tie(lhs_job, lhs) > std::tie(rhs_job, rhs);
};
std::priority_queue<Vertex, std::vector<Vertex>, decltype(is_later_event)> ready_vertices(is_later_event);
```

Why:
- `left` and `right` read as directions, which in this codebase suggests AGV motion. They're only
  the comparator's two arguments: two event vertices of the DAG.
- `later_first` sounds like "later events come out first", which is the opposite of what happens.
  `is_later_event(lhs, rhs)` says what it returns: true when `lhs` comes after `rhs`.
  `std::priority_queue` pops its greatest element first, so this yields the earliest event.
- The comment stays as the branch has it. No new comment is added.

Question for you: is `is_later_event` clear in a `priority_queue` comparator, or would another name
read better?

## 3. `ResolveRequest::is_parking_over_agvs_allowed` becomes `is_parked_agv_pose_allowed`

What the flag does: when it's `false` (the default), `ResolveBlockingTrays`
(`tray_assignment.cpp:599`) adds the poses of parked AGVs (excluding disabled AGVs and the tray's
own carrier) to `illegal_poses`, so the destination search never picks a stall an AGV is on.
`ResolveByEvictingAgvs` (line 661) sets it to `true` to find a stall that only parked AGVs are
blocking, then moves those AGVs to chargers. A tray never ends up parked over an AGV.

Why rename: an AGV under a tray is the normal way trays are carried, so "parking over AGVs" reads
as that. The new name says what the flag allows: the destination may be a parked AGV's pose. It
follows the `is_*_allowed` pattern of its neighbour `is_waypoint_stash_allowed`. Like its
neighbours, it gets no doc comment.

Occurrences: `scheduler.hpp:71`, `tray_assignment.cpp:600` and `:661`,
`tray_assignment_tests.cpp:110`.

Question for you: does `is_parked_agv_pose_allowed` say clearly that it's about the *destination*
search? An alternative is `is_parked_agv_destination_allowed`.

## Not yet decided (comment if you have a view)

- `IsTrayPlanFeasible` (`tray_assignment.cpp:742`) only checks that each tray move has a path
  through obstacles that don't move (no collisions, no timing). Candidate: `AreTrayMovesReachable`,
  and "is not feasible" at line 713 would become "is not reachable".
- `ResolveByEvictingAgvs` and `FindAgvEvictionPlan` are hard to tell apart. The first picks the
  stall and works out which AGVs block it. The second recursively moves those AGVs to chargers.
  Candidate for the second: `PlanAgvEvictionsToChargers`.

## What to return

For each numbered item: agree or disagree, with a reason that cites file and line. For each text
change, give the exact string you'd use. List anything else in the range `main...HEAD` that has the
same naming problem (shorthand ids, direction words used for non-directions, flags named for the
wrong thing).

---

## Decisions after Codex's reply (2026-11-08)

Checked against `a38e7eb8`. Illegal poses block a destination by footprint overlap
(`blocking_tray_search.cpp:138`, collision-table query), and only for final destinations: paths
may still pass through them. So "pose" names are wrong; "overlap" is right.

| Item | Decision |
|---|---|
| 480 | `"tray {} remains stashed on {}: {}"` (Codex) |
| 664 | `"no stall for tray {}, even one that overlaps a parked AGV"` (Jon rejected Codex's wording) |
| 691 | `"no eligible AGV found to relocate from destination {}"` (Codex) |
| 707 | `"no destination found for tray {} after relocating the blocking AGVs"` (Codex) |
| 710 | `"only a waypoint destination found for tray {} after relocating the blocking AGVs"` (Codex) |
| 713 | `"tray {} cannot complete its planned moves to {} after relocating the blocking AGVs"` (Codex) |
| 721 | `"no eligible free charger is reachable for AGV {}"` (Codex) |
| 738 | `"no charger relocation for AGV {} permits the tray plan: {}"` (Codex) |
| Comparator | `is_later_event(left, right)` (Codex; Jon agreed once the lambda was renamed) |
| Comparator comment | `// Prefer the lowest job index, then the earliest-added event, among ready events.` (Codex) |
| Flag | `is_parked_agv_overlap_allowed`, with `/// The destination may overlap a parked AGV; the caller moves it first.` |
| `IsTrayPlanFeasible` | `AreTrayMovesReachable` (both agree) |
| `FindAgvEvictionPlan` | `PlanAgvEvictionsToChargers` (both agree) |
| `unevictable_agvs` | Keep, against Codex: same pattern as `immobile_trays` in the same struct and PR #1031's `unassignable_agvs` |
