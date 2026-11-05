# Stage 2 review (branch `jmg/SW2-1135/scheduler-renames-and-cleanups` at `ec2785b3`, 2026-10-30)

Written by the stage-A session after reading the ten commits, the headers at the tip, the stage-2 code
notes, and two subagent checks (one of the bug-fix commit `ec2785b3`, one of the neutrality of
`a5ea1fcf` and `8e976f18`). Read-only: nothing in the repo was changed.

State: 10 commits, 63 files, +3275 / -4966. Latest runs green: scheduler 19/19 binaries,
planner_core + motion_planner + scheduler_advanced_tests green, tree clean (recordings unchanged).
Not visible in the logs: whether one of the two back-to-back scheduler runs had
`SCHEDULER_CHECK_RECORDINGS=1`. Confirm before the PR; the bug-fix commit needs it (see 1.1).

## 1. The changes

### 1.1 `ec2785b3` fix(scheduler): fix bugs found during the refactor

All seven fixes are real and the code does what the message says. Corrections to the message and
gaps:

- The closing sentence "the existing scenarios do not reach these paths" is wrong for three fixes.
  `plan/retrieve_job/AdvancesRootTray.yaml` reaches the advance-move path (fix 2);
  `plan/bay_job/ReadyForInsert.yaml` reached the empty-optional read (fix 4, an empty bay reparks
  no tray); `repark_tray_job/UnplugsCharger*.yaml` and `*/WhileCharging.yaml` reach the chained
  stop-charging event (fix 6). Say instead: "The recorded outputs are unchanged
  (SCHEDULER_CHECK_RECORDINGS=1)", and make sure that run happened on this commit.
- Unmentioned behaviour change in fix 2: an unblocking move whose apply fails now fails the whole
  tray assignment; before, the result was ignored. Add that sentence to the message.
- Fix 5 (ExpandAgvMoveJob keeps the heading only) is on a path no caller reaches: both callers pass
  `is_reciprocal_allowed = false`. Either drop the parameter (dead code commit) or keep the fix and
  say the path is unreachable today.
- Only fix 1 has a test (RetrieveJob.FailedJobReportedOnce). Worth adding, as stage scenarios on
  tiny_lot: fix 2 (a blocker move that cannot apply fails AssignTrays), fix 3 (a destination usable
  only through its reciprocal heading), fix 4 (ReadyForInsert on an empty bay already covers it;
  name it in the message).
- Minor: "Tried to move a<id>" has no space because AGVs print as `a1`; fine, but the reviewer
  will ask. The message's "A missing space" fix is the TrayMove text, not this one.

### 1.2 `a5ea1fcf` and `8e976f18` (dead code, simplify, extract)

No confirmed behaviour change. Three spots are equivalent only because of a property of a
neighbouring function; a one-line comment at each, or a sentence in the PR, saves a reviewer the
derivation:

- `ChainAgvEvent` writes `last_agv_event[agv_id]` before `OrderArrivalAfterPriorOccupant` runs
  (old code wrote it after). Equivalent because that method skips the arriving AGV's own entry.
- `OrderAfterFreeingMoves` at the root-move site now skips `blocker == event`; the root event is
  not an occupant yet at that point, so nothing is dropped.
- `AddChainedEvent` chains on `GetGarageEntityId()`; at the charge-job bay transition it now runs
  before `ApplyTo`, which is const on the event.

Everything else checked (the 14 std::tie sites, Plan()'s failure lambda and messages, the four
parameter structs, the optional `->` rewrites, the hoisted filters, ClassifyBay's dead else, the
removed erase) is equivalent.

### 1.3 PR hygiene

- The branch spans scheduler, planner_core, motion_planner, agvhito_tools and
  scheduler_advanced_tests. The Jira description still holds the narrow version; re-paste Scope and
  Definition of Done from `jira_ticket.md`, and list the planner_core API trim and the message-alias
  removal there, since they are the parts other packages see.
- Keep the `fix(scheduler)` commit last and separate (it is); the PR body should say the refactor
  commits are behaviour-neutral and the fix commit is not.
- The package-level `.clang-tidy` suppression mirrors `src/agvhito/src/sm/.clang-tidy`; say so in
  the PR body, it is the one policy change.
- `volley::Scheduler` next to `volley::scheduler::PlanContext` is a transitional split; a line in
  the PR body that the class moves in stage C avoids the question.
- Not on this branch: deleting `scheduler_advanced_tests` after moving its three June regression
  tests into scenario files (see the stage-A session's assessment of 2026-10-29). A separate
  ticket.

## 2. Naming

The renames made are sound; "Expand", "Assign", "Order", "Compute", "Find", "Apply" are used
consistently. Proposals, in order of value:

1. **`*_by_*` in the assignment states.** PlanContext uses `last_event_by_asset`,
   `first_event_by_tray`, `keep_out_filter_by_footprint`; the new structs do not:
   `AgvAssignmentState::last_agv_event` -> `last_event_by_agv`, `last_move_to_tray_event` ->
   `last_move_to_tray_event_by_agv`, `current_node_occupant` -> `occupant_by_node`;
   `TrayAssignmentState::last_tray_event` -> `last_event_by_tray`.
2. **"asset" vs "entity".** The type is `GarageEntityId` and the rest of the code says entity
   (`CollisionEntityId`, `GarageEntityId`). `last_event_by_asset` -> `last_event_by_entity`,
   `AppendToAssetChain` -> `ChainAfterLastEntityEvent`. Then PlanContext, the file-local
   `ChainTrayEvent` / `ChainAgvEvent` and `AddChainedEvent` all share the verb "Chain".
3. **`AssignDestAndUnblockingMoves`** -> `AssignDestinationAndUnblockingMoves` (the only method name
   with the abbreviation; `FindDestinationForRootTray`, `FindUsableDestination` spell it out).
4. **`is_reciprocal_allowed`** -> `is_reciprocal_heading_allowed`: it is the heading that may flip,
   never the node. Message field `allow_recip` stays.
5. **`GateAgvMoveOnBlockerDeparture`** -> `OrderAgvMoveAfterBlockerDeparture`: it adds one
   dependency, like every other `Order*` method.
6. **`FindAgvsAtPickupPose(matching, ...)`** and `BuildAgvOrderDag(matching, ...)`: the parameter is
   the root event per AGV; `root_event_by_agv`.
7. **`ComputeTravelDuration(..., agv_id)`**: the parameter is a `GarageEntityId`; `agv_entity`.
8. **`AssignTrayIdForEmptyMove`** -> `PickEmptyTrayForMove` (it chooses the tray; the id is how).
9. **`PropagateEventCostToChildren(event_cost)`** -> `PropagateEarliestStartToChildren(duration)`;
   it updates `event_earliest_starts`, and the class now says "duration" for times and "cost" for
   the assignment objective.
10. **`TogglePrintDags`** -> `ToggleDagPrinting`, to match `is_dag_printing_enabled_`.
11. **`GetFirstSystemFloor`**: the comment "The error completes '...but it '" documents a
    caller/callee coupling on error text. Return a full sentence and drop the coupling.
12. Leave: `motion_graph_` of type `GarageGraph` (decided in the plan), `dest` as the local name
    (codebase-wide, `GetDest`/`SetDest` in planner_core), `Dag::Has/Add/Remove/Replace`.

## 3. Expand methods: readability

Lengths at the tip: AssignTrays 291, Plan 130, ExpandReparkTrayJob 112, AssignAgvs 110,
ExpandRetrieveJob 72, ExpandAgvMoveJob 61, the other Expand* 28-64. The tray and AGV solvers are
stage C; the Expand methods are stage 2 material.

ExpandAgvMoveJob (the pasted version):

- Bind a reference once the optional is checked: `const auto& agv = *agv_opt;` and then `agv.pose`,
  `agv.disabled`. The method mixes `agv_opt->`, `*agv_opt` and `agv_opt.value()`; agvhito's
  `const vstate::State& state = state_or.value();` is the model.
- Build `pose_change` after the destination checks and only in the unloaded branch; today it is
  built before validation and discarded on the loaded branch.
- The reciprocal-heading rule applies only to the unloaded move; the loaded branch uses
  `ApplyPreferredHeading`. Split after the checks: `if(IsCarryingTray(agv)) { ...TrayMove } else
  { ...AgvMove }` with the heading rule inside the else, so the asymmetry is visible.
- The three setters on a fresh TrayMove (`SetTrayId`, `SetAgvId`, `SetDest`) appear here and in
  ExpandReparkTrayJob; a `TrayMove(job_index, tray_id, dest)` constructor in planner_core (the API
  trim commit already touches the class) or a local `MakeTrayMove` helper.
- `IsReciprocal(agv.pose.heading, tray.pose.heading)`: see section 5.

ExpandReparkTrayJob:

- The `if(dest)` block (50 lines) resolves and validates the destination: extract
  `ResolveReparkDestination(working_state, tray_opt, dest, is_reciprocal_heading_allowed)` returning
  `stdx::Expected<GaragePose, JobFailure>`; the method then reads as validate tray, resolve
  destination, add event, order.
- The trailing bay / charger dependency block is one concept: `OrderAfterBayAndChargerEvents(ctx,
  working_state, tray_move)`.
- `applied.error()` is logged with ERRORS and returned; every other Expand* only returns. One or
  the other.

ExpandRetrieveJob: `working_state.GetTray(payload_opt->tray_id).value()` and
`GetVertexFromPose(tray.pose).value()` are the two unchecked values; a comment naming the
invariant (ValidateBaseState guarantees both) or an early failure, since this is the entry point
of a client request.

## 4. The agvhito state-machine style, and what fits stage 2

What `src/agvhito/src/sm` does that the scheduler does not yet:

- `stdx::Unexpected(fmt, args...)` (stdx/expected.hpp:36 takes a `std::format_string`) instead of
  string concatenation. scheduler.cpp has 4 `std::format` calls against 72 `" + std::to_string`
  joins (utils.cpp 7). Example: `return stdx::Unexpected("Tried to move a{} which doesn't exist!",
  agv_id);`.
- A typed error (`yasminx::Error{type, message}` with `kError*` constants) and a
  `std::formatter<Error>` (yasminx/format.hpp) so errors print with `{}`.
- `///` with `@p` / `@return` on every declaration; designated initialisers for error structs;
  `k`-constants for limits and repeated prefixes (`kMsgPrefix`); reference bound after the check.

Within stage 2 (text-preserving, no client-visible change):

1. **Format strings for every `stdx::Result` return and every `JobFailure` text.** For `JobFailure`
   add two file-local helpers in scheduler.cpp:
   `Fail(std::format_string<Args...>, Args&&...)` returning `stdx::Unexpected(JobFailure{...})` and
   `RetryableFail(...)`. 61 sites become one line each and the positional / designated mix goes
   away. Keep every string identical; the recordings and `FailedJobReportedOnce` check the texts.
2. **`std::formatter` for the message types in the texts** (`GaragePose`, `Guid`, the entity ids),
   delegating to the existing `to_string` overloads in common_ros `print_utils.hpp`, in the pattern
   of yasminx/format.hpp. That is a header-only addition to common_ros; without it every `{}` needs
   `std::to_string(...)` in the argument list, which still beats concatenation. Decide which; the
   common_ros addition is small and the PR already touches planner_core and agvhito_tools.
3. **Reference-after-check** at the sites that still read `x_opt->` four or more times (the
   Expand* methods, AssignTrays).
4. **`///` on the public declarations in scheduler.hpp** (it mixes `//` and `///`).
5. **Named constants** for the bay-command placeholder ids `1u` / `2u` in the retrieve and charge
   jobs, and the iteration cap in RepairAgvMovePaths.

Later, not stage 2: a typed error for JobFailure (`type` next to `message`, with constants), since
Dispatch reads the message today and a type is a contract change; `_or` suffixes for Expected
results (agvhito: `message_or`, `state_or`) only if the team wants the convention, it is churn
otherwise.

## 5. `IsReciprocal` and friends

Definitions: `volley::IsReciprocal(int, int)` and `IsAngleOrReciprocal(int, int)` in
common/math_utils; `IsAngleOrReciprocal(GaragePose, GaragePose)` and `ReciprocalGaragePose` in
common_ros/pose_utils; `ReciprocalAngle` in common/math_utils.

Reach outside tests:

| helper | scheduler | planner_core | motion_planner | common_ros |
|---|---|---|---|---|
| `IsReciprocal` | 1 | 0 | 2 | 0 |
| `IsAngleOrReciprocal` | 7 | 1 | 1 | 9 |
| `ReciprocalGaragePose` | 2 | 0 | 1 | 0 |
| `ReciprocalAngle` | 3 | 0 | 2 | 1 |

- `IsReciprocal` is planner-only (three call sites). A global rename to `AreOppositeHeadings` is
  cheap but touches common and motion_planner. Better and in-package: the scheduler's one use asks a
  domain question, "is the tray carried backwards on the AGV", and the payload already has
  `reciprocal_to_tray`. Add `IsTrayReversedOnAgv(const DiscreteAgvState&, const DiscreteTrayState&)`
  to scheduler utils next to `IsCarryingTray` / `HasPayload`, and leave common alone. The two chugg
  sites (`agv_recip`, `recip`) ask the same question and can adopt it when motion_planner is
  touched.
- `IsAngleOrReciprocal` is used across common_ros (garage state, safety checker, layout, pose
  graph); renaming it (`AreCollinearHeadings`) is a common_ros ticket. In the scheduler, do not
  alias it; name the decisions instead, as `KeepTrayHeadingIfEquivalent` already does: the seven
  sites are all "same axis, so no rotation", and three of them (lines ~1684, ~2056, ~2432 at the
  tip) are that same helper's logic inline.

## 6. Status (2026-10-30): implemented and folded into the commits

The user asked for the recommendations to be implemented and folded into the existing ten commits
(`--amend`, same sequence). Done by the stage-A session; history rewritten, the old tip is kept as
branch `jmg/SW2-1135/backup-ec2785b3`. New shas: `991502ec`, `a005b90d`, `891dc19f`, `828f4bfb`,
`98bbc0fe`, `b1a85516`, `04c5ca33`, `5fc0e120`, `bfc23e67`, `ebb9de58`. Details and checks in
`code_notes.md` ("Review fold-in") and `../SW2-482_notes.md` item 205.

- Section 2 (naming): every rename landed in the commit that introduced the old name:
  `ToggleDagPrinting` (#1); `last_event_by_entity`, `ChainAfterLastEntityEvent`, `entity` (#2);
  `AssignDestinationAndUnblockingMoves`, `OrderAgvMoveAfterBlockerDeparture`, `PickEmptyTrayForMove`,
  `PropagateEarliestStartToChildren`, `root_event_by_agv` (#4); `last_event_by_agv`,
  `last_move_to_tray_event_by_agv`, `occupant_by_node`, `last_event_by_tray` (#5);
  `is_reciprocal_heading_allowed` (#6); `event_duration` and `agv_entity` parameters (#9).
- Sections 3 and 4 (expand methods, agvhito style) landed in #9: `Fail` / `RetryableFail` with
  `std::format` (96 `JobFailure` / string-concatenation sites), `scheduler/format.hpp`
  (`std::formatter` for `GaragePose`, `Guid`, `GarageEntityId`), `MakeTrayMove`, `PickupHeading`,
  `OrderAfterBayAndChargerEvents`, `ApplyReparkHeadingPreference`, `CheckReparkDestination`, the
  placeholder-id and repair-pass constants, reference bindings after the optional checks, `///`
  comments on the class, and `ExpandAgvMoveJob` / `ExpandReparkTrayJob` restructured as proposed.
  Every error string is unchanged.
- Section 5: `IsTrayReversedOnAgv(agv, tray)` in scheduler utils (#9); common untouched.
- Section 1.1: the fix commit's message now states the reachability of each fix, the unmentioned
  behaviour change of fix 2, that fix 5's path is unreachable (both callers pass false), and that
  the recordings are unchanged. Fix 3 turned out unreachable as well: `GetAllowedHeadings`
  (common_ros/pose_utils.cpp) adds each heading and its reciprocal, so a destination usable only
  through its reciprocal heading cannot exist; the scenario written for it failed and was dropped,
  and the message says so. Section 1.2's three spots have comments at `ChainTrayEvent` /
  `ChainAgvEvent` and `AddChainedEvent`.
- Not done: scenarios for fixes 2 and 4 (fix 4 is covered by `ReadyForInsert.yaml`, named in the
  message); the Jira re-paste (user); the PR body (the other session's, `pr_description.md` has
  the renamed names).
