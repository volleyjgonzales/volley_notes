# SW2-905 reviewer walkthrough

PR [1036](https://github.com/VolleyAutomation/volley/pull/1036) fixes an insert that could leave a customer's car inside a closed bay because an idle robot blocked the only available parking stall. The scheduler now avoids parking over robots and, when necessary, plans a robot relocation before moving the car into the freed stall. If it cannot find a feasible relocation, it retains the existing waypoint-stash fallback.

This explanation follows the two-commit branch at `a3bbcb65`, based on main `afc637ba`, as pushed on 9 November 2026 after the second round of review fixes. The intended reader is a C++ reviewer who knows dependency graphs but has not worked on this scheduler.

## The garage objects and the failure

A customer leaves a car on a **tray** in a **bay**. An **AGV** is the mobile robot that drives beneath a tray, raises its lift, carries the tray and car, and lowers them at a destination. A **stall** is a parking location; a **waypoint** is a routing location that can sometimes temporarily hold a tray. An AGV charger charges the robot, whereas a VECS is equipment for charging a parked electric vehicle.

The garage layout is a graph. A **pose** includes a node and a heading; different node IDs do not guarantee that the objects at those nodes are physically separated. A collision table answers geometric questions using the footprint of each object, such as an AGV, a tray, or a tray carrying a particular size of car.

In the current reproduction, the car is on tray 27 in bay B7. P15 is the only free stall. AGV 1 is stopped at charger C14, whose pose is only 0.6 metres from P15; the two nodes are distinct, but parking the tray at P15 would overlap the AGV. AGV 2 waits beneath an empty tray at P5 and can carry the customer's tray.

Before this PR, destination selection ignored AGVs and accepted P15. Later validation counted the parked AGV and rejected that same destination as occupied. No executable insert schedule resulted. The documented operational consequence was that the dispatcher dropped the insert with the customer's car still inside the bay. This PR changes planning; it does not change the dispatcher's retry policy.

## How a request becomes executable actions

The scheduler does not plan detailed robot motion in one step. Its stages progressively add information:

| Stage | Responsibility | Relevant code |
|---|---|---|
| Job expansion | Turn an insert request into events, including a bay transition and a tray move whose destination is initially unknown. | `src/planner/scheduler/src/job_expansion.cpp` |
| Tray assignment | Choose trays and destinations, plan blocking-tray reparks, and add dependencies. This PR also introduces AGV relocation events here. | `src/planner/scheduler/src/tray_assignment.cpp` |
| AGV assignment | Choose the carrier and add its approach, lift and other required events; account for already planned AGV moves. | `src/planner/scheduler/src/agv_assignment.cpp` |
| Event validation | Replay the events against a working garage state and check destinations and paths. | `src/planner/scheduler/src/validation.cpp` |
| Motion planning | CHUGG turns the event graph into trajectories while accounting for spatial and temporal conflicts. | `Scheduler::PlanMotions`, then `src/planner/motion_planner/` |
| Action graph construction | Convert planned motion into executable actions with job IDs and parent dependencies. | `src/planner/scheduler/src/action_graph.cpp` |

The event graph is a directed acyclic graph, or DAG. An edge A → B means A must finish before B. A topological ordering is one legal order for inspecting or replaying that graph; it does not mean all events execute serially.

The stages use copies of the discrete garage state to reason about the effects of proposed events. Applying an event to such a copy is a planning operation, not a command sent to a physical robot.

## Why destination selection and validation disagreed

`ResolveBlockingTrays` uses `FindDestinationForRootTray` to search for a destination. The root tray is the tray whose destination the caller is trying to resolve. Other trays may need to move first, producing the plan's `required_moves`.

The search is cost-based through `SingleSourceSearch`; it is not plain breadth-first traversal. It first tries parking or suitable EV-charger nodes. If permitted and no such destination is found, it can fall back to a waypoint stash.

Three different mechanisms matter:

- The **path filter** determines which graph poses and edges the search can traverse. `BuildImmobileTrayFilter` ignores enabled AGVs and movable trays so the search can discover possibilities that require moving something else. Disabled entities and locations still impose restrictions.
- **Illegal parking poses** constrain destination acceptance. The search may travel through an excluded object's vicinity but must not finish where the destination footprint overlaps it.
- The **keep-out filter** represents restrictions such as disabled or reserved resources. It is distinct from the current occupancy filter used to reason about a particular move.

The old search's optimistic treatment of AGVs was not matched by a destination exclusion. Validation, by contrast, used `BuildStaticObstacleFilter` and ignored the moving carrier rather than every AGV. The disagreement concerned physical occupancy, not merely whether a tray already occupied the destination node.

## The first change makes the resolver avoid parked AGVs

`ResolveBlockingTrays` now copies the request and merges `CollectIllegalPosesOfParkedAgvs` into its illegal poses. This happens at the shared resolver entry point, so fixed-destination blocker searches and charge-payload callers receive the same policy as insert destination assignment.

The helper excludes the AGV already carrying the root tray. That AGV travels with the tray and is not a separate parked obstacle. Disabled AGVs are handled through the existing disabled-entity restrictions rather than offered for relocation.

`ResolveRequest::is_parked_agv_overlap_allowed` defaults to false. The eviction candidate search sets it to true to ask a counterfactual question: which stall could this tray take if destinations overlapping a parked AGV were allowed? Overlap is a collision-table query against the AGV's footprint, so an AGV on C14 blocks P15 without standing on it. The flag is not permission to execute an overlapping placement.

Tray assignment also now applies AGV events to its working state. Otherwise, a search after a planned AGV move would still see that robot at its old pose. Bay and VECS transitions retain their occupancy registration and state application; VRC transitions remain explicitly skipped in this stage. `RecordTransitionOccupancy` describes the registration operation, while `ApplyToWorkingState` centralizes application and its error message.

This alone prevents selecting P15 in the reproduction, but would leave the car stashed on W31. The relocation search is what recovers normal parking.

## The second change finds a feasible AGV relocation plan

`AssignDestinationAndUnblockingMoves` first obtains the ordinary tray plan. Only if that plan ends at a waypoint does it try `ResolveByEvictingAgvs`.

The relocation procedure is:

1. Rerun destination resolution with waypoint stashing disabled and destinations overlapping parked AGVs allowed. This identifies a candidate destination such as P15.
2. Query the collision table for AGVs whose current poses overlap that candidate. Disabled AGVs, AGVs carrying a tray, the root tray's existing carrier and AGVs with planned moves later in the request (`ResolveRequest::unevictable_agvs`) are never relocated: the last would start those moves from the stall they left.
3. Exclude chargers whose inbound AGV pose would also overlap the candidate destination. Checking the inbound pose matters because the robot's arrival heading affects its footprint.
4. Use `FindUnoccupiedChargersByTravelTime` to enumerate reachable, unoccupied charger poses in travel-time order. The normal charge-job helper remains a wrapper that takes the first result; stable sorting preserves encounter order for equal costs.
5. `PlanAgvEvictionsToChargers` explores placements recursively. Each attempted AGV move is applied to a separate state copy before placing the next AGV. Consequently, later searches see already occupied candidate chargers. A failed branch does not modify its caller's state.
6. Once all candidate AGVs are placed, rerun ordinary tray resolution with AGV parking exclusions restored. Reject a missing destination or another waypoint stash.
7. Call `AreTrayMovesReachable`: check each required blocking-tray move's route, apply it, and then check the root tray's route. Return the first feasible complete placement, or retain the original stash if none works.

`ResolveByEvictingAgvs` returns `stdx::Expected<AgvEvictionPlan>`. When it fails, the error names the reason (no stall even one that overlaps a parked AGV, no eligible AGV to relocate, no reachable free charger, no charger relocation that permits the tray plan, or relocation moves that cannot wait for the tray moves planned before them), and tray assignment logs one INFO line per tray: "tray {} remains stashed on {}: {reason}".

The feasibility check uses the static obstacle filtering used for validation. Because AGV assignment has not yet run, it treats an AGV standing beneath the tray as its prospective carrier. That assumption is documented in `IsTrayDestinationReachable`; later assignment, validation and motion planning still run.

The parking-exclusion query and validation are not literally identical geometric operations in every case. The former uses the moving tray or payload footprint; the existing static obstacle filter substitutes the TRAY footprint in certain checks against an AGV. Changing that substitution is outside this PR.

## Why checking only the freed stall was insufficient

An early version could move a blocking AGV to C10 and thereby close a route through adjacent waypoint W9. It had freed the destination stall but made that stall unreachable by the loaded tray. Its final destination search still ignored AGVs on paths, so only validation discovered the problem.

The current route regression scenario makes this visible: AGV 1 occupies the only free stall P5, AGV 2 is beneath the car in B7, P15 contains an empty tray, and W4 is disabled. The car's route to P5 must use W9. C10 is the nearest available charger, but placing AGV 1 there closes that route. The planner rejects that placement and uses C14 instead, then parks the car at P5.

Review also exposed why feasibility must be checked on the complete plan. Checking the root route before planned blocker moves could reject a placement that those moves would make usable; applying blocker moves without checking their routes could miss an infeasible prerequisite. The final implementation checks those moves in order at the completed-placement leaf.

## How relocation and insertion are ordered

For an accepted plan, tray assignment adds each relocation event to the DAG chained after that AGV's earlier planned events (`AddChainedEvent`), and makes it a predecessor of every generated tray move, including blocking-tray reparks and the root move. It also applies the relocation to its working state before applying the tray moves. Tray assignment counts each AGV's planned moves from job expansion and applies them in order, so an AGV brought to a charger by earlier jobs in the same request is relocated from where those jobs leave it.

The relocation also waits for the tray moves planned before it in the request. Charger selection runs on tray assignment's working state, in which those moves have already happened, so a charger may be reachable only because an earlier tray has left the route. Each relocation therefore depends on the last event of every tray moved earlier in the request (`CollectLastTrayEvents`, ordered by tray id so plans stay deterministic). If one of those dependencies would close a cycle through the insert's own tray move, the relocation is dropped and the stash is kept.

This ordering is deliberately conservative: the relocation waits for the whole earlier move, not only the departure, and for every earlier tray, not only those on its route. In `StallBlockedByAgvRouteClearedByEarlierTrayMove` it lengthens the plan from 149.9 s to 206.0 s; the plan without it was valid, because the motion planner made AGV 1 wait. Requests without earlier tray moves are unaffected: every pre-existing recording is unchanged.

AGV assignment records the moving AGV's busy time and chains subsequent work for that AGV. The relocation carries the insert's job index from its creation; action graph construction maps that index to the job GUID.

Once a relocation waits for earlier tray moves, the AGV it relocates may itself carry one of those trays, so it is no longer where tray assignment found it. Tray assignment records its relocation moves in `PlanContext::agv_evictions`; when AGV assignment applies one as a ready root event, it first sets the move's start to the AGV's current pose (`AgvMove::SetSourcePose`). Requested MOVE_AGV jobs keep their fixed start and its check.

`GetTopologicalOrdering` now breaks ties among ready events by job index, then by creation order. Before, events of one job that were ready together came out in heap order, so validation could replay the carrier's approach before the insert's bay transition, whose inbound pose stays blocked until the transition; the earlier-moves scenario exposed it. No existing recording changes.

The reproduction has two chains that may overlap:

```text
AGV 1 leaves C14 ── reaches C16 ───────────────────────┐
                                                    v
AGV 2 approaches B7 ── lifts tray ── loaded departure ── parks at P15
                            ^
                     bay transition
```

The carrier's approach need not wait for the relocation. Its loaded departure does wait for the relocation to finish. Waiting until the other AGV reaches its charger is deliberately coarser than waiting merely until it clears the stall; the high-level relocation is one event.

CHUGG must still resolve collisions between otherwise independent trajectories. An action table's row order therefore cannot prove either serial execution or safe concurrency. The regression test walks `ActionNode.parents` to establish that the loaded departure descends from the relocation's final action, and verifies that the relocation actions belong to the insert job.

## What the tests and viewer show

The eleven new insert recordings use the site's two AGVs, with AGV 1 blocking and AGV 2 carrying where both are present.

| Scenario | Property exercised |
|---|---|
| `FromBay7StallFree` | With C14 enabled and empty, park on P15 without eviction. |
| `StallBlockedByAgvOnCharger` | Relocate AGV 1 from C14 to C16, then park on P15; verify dependency ancestry and job association. |
| `StallBlockedByAgvEvictedAwayFromRoute` | Reject C10 because it closes W9; use C14 and park on P5. |
| `StallBlockedByAgvNoFreeCharger` | Other chargers are disabled; retain the W31 stash. This is no longer the earlier fixture with AGVs on every charger. |
| `StallBlockedByAgvChargersUnreachable` | Chargers exist but access is blocked; retain the stash. |
| `StallBlockedByDisabledAgvOnCharger` | Do not relocate a disabled AGV; retain the stash. |
| `StallBlockedByLoadedAgvOnCharger` | Do not relocate an AGV carrying a tray; retain the stash. |
| `StallBlockedByAgvParkedThereByEarlierMoves` | Two MOVE_AGV jobs in the same request bring AGV 1 to C14; relocate it after the second, then park on P15. |
| `StallBlockedByAgvWithLaterMove` | AGV 1 has a move later in the request; do not relocate it, stash on W31, and keep the move's destination. |
| `StallBlockedByAgvRouteClearedByEarlierTrayMove` | C16 disabled; an empty tray on W8 at heading 0 blocks every route from C14 to C10 until an earlier MOVE_TRAY takes it to W4. The relocation to C10 must depend on that tray's departure; the test fails without the ordering. |
| `EvictionAfterCarryingEarlierTray` | The same with the tray on W13: AGV 1 carries it to W4 first, then relocates to C10 from W4, not from C14. |

The new unrecorded stage test, `KeepsDestinationsOffParkedAgvs`, checks the resolver's default exclusion policy and its explicit candidate-search exception. The pre-existing `FillsBlankDestination` recording changes from P2066 to P2062: the only AGV occupies P2066, and tray assignment does not yet know it will become the carrier. That is an intentional conservative destination change.

Recording comparison is opt-in through `SCHEDULER_CHECK_RECORDINGS=1`; it compares normalized recorded input/output. Ordinary CI assertions, particularly dependency and job-state assertions, remain essential. Passing recordings do not establish arbitrary multi-AGV or recursive eviction correctness.

The engineering viewer that helped review these recordings moved to PR #1043 (SW2-1191).

A separate simulation scenario exercises the full stack: `src/scenario/scenarios/5675_pecos_sandbox_combined_insert_blocked_by_agv_on_charger.yaml`. It sets MANUAL dispatch, requests B7's transition at 40 seconds and queues a patron at 45 seconds. Those delays allow bay startup and door validation. The sandbox layout and simulation parameters can produce routes different from the unit-test recording; see [simulation instructions](/home/jon-gonzales/repos/volley_notes/tickets/SW2-905_insert_blocked_by_agv/simulation.md).

## Review boundaries and remaining work

The PR changes stall choice and can insert AGV relocation events; it does not redesign carrier assignment, CHUGG or dispatcher recovery. A single enabled AGV can still be sent to a charger and subsequently selected as the carrier, producing an unnecessary trip. Likewise, when the relocated AGV first carries an earlier tray away, the stall is already free but the relocation still runs. Relocation destinations are limited to chargers; hiding beneath an empty tray is deferred.

The current tests do not combine eviction with a blocking-tray repark or demonstrate two independent AGVs blocking one stall. The recursive placement code and sequential feasibility checks address those structures, but the recordings do not exercise them. The search also fixes the blocking-AGV iteration order and returns the first feasible charger combination; it is not a global optimization over all move orders and destinations. A narrower ordering, waiting only for trays whose poses lie on the relocation's route, would recover the time the conservative ordering costs; it is left for later.

When the unassignable-AGV policy from PR 1031 is integrated, those AGVs must remain obstacles but must not become eviction candidates. Relocating AGVs off the explicit destination of a move tray job is SW2-1190, on its own branch for a follow-up PR. The proposed C1 tray-module extraction also needs to represent AGV relocation outputs and incoming AGV state changes; a tray-only result type cannot preserve this behavior.

The history is `edbb1a3c` for scenarios and `a3bbcb65` for the scheduler solution. The scenario commit intentionally contains expectations that require the following solution commit. The review-driven corrections, including the 8 November renames and the 9 November ordering and start-pose fixes, are folded into the relevant commits rather than left as separate fixes.
