# Codex review 7 (2026-10-30) and its evaluation

Codex read the tip `280339f9` (source only): naming and ownership. Checked here against the code and
the history; applied in item 226; tip `7166af0e`. "Born in" is the commit that introduced the current name.

## Names

| Current | Codex | Check | Verdict | Born in |
|---|---|---|---|---|
| GetBayInboundPose(bay_id), GetInboundPose(node) | MakePoseAtBayWithInboundHeading, MakePoseAtNodeWithInboundHeading | Both build node id + configured inbound heading; "Get" suggests a stored value. "Inbound heading" is the layout's own term (GetInboundHeading, GetBayInboundHeading). | Agree on the verb; propose `MakeBayInboundPose` / `MakeInboundPose` with one contract line ("the node with its configured inbound heading"), shorter and in the layout's vocabulary. Codex's longer names are the alternative. Locals: the two `bay_pose` locals (job_expansion 199, 400) named for their use. | 3, 4 |
| PickEmptyTrayForMove | AssignEmptyTrayToMove | Confirmed: sets the tray id and may turn the destination heading. | Agree. | 1 |
| FindAgvsAtPickupPose | FindAssignedAgvsBlockingPickup | Confirmed: footprint collision via the collision table, only AGVs in the assignment map. | Agree. | 1 |
| SanityCheckEvents | ValidateEventSequence | Confirmed: replays events in order and checks bay ODP clearance and AGV moves. Used by `sanity_check_tests.cpp` and advanced tests 05, 07. | Agree; test suite and file names stay (scenario files are keyed by test name). | main (kept in 1) |
| CheckMovePossible | ValidateMoveDestinationAndPath | Confirmed: destination vertex, keep-out filter, occupancy, one filtered path. Its error text still says "Scheduler::IsMovePossible()" (unchanged on purpose). | Agree. | 1 |
| CreateActionGuid | GenerateNextActionGuid | Confirmed: static counter. Only action_graph.cpp (and utils' VRC insertion) use it. | Agree; and it becomes local to action_graph.cpp (see placement). | main |
| GetVersionInfo, GetSchedulerReport | BuildVersionInfo, BuildSchedulerReport | They allocate a new message per publish. Central has its own `GetVersionInfo`. | Low value; recommend leaving them (publish-time snapshots, same name as central's). | main |
| StopChargingBeforeTrayMove | ScheduleChargingStopBeforeTrayMove | Confirmed: adds an event. | Agree on the meaning; propose `AddChargingStopBeforeTrayMove` to match the file's own vocabulary (AddChainedEvent, AddBayTransitionToRetrieve, AppendAgvLiftEvent: Add/Append = put into the plan). | 3 |
| FindUsableDestination | ResolveDestinationHeading + contract | Confirmed: the reverse heading is tried only when the requested pose has no vertex (unreachable today, commit 4's message says so), not when it is blocked. | Agree. | 4 |
| FindRetrievalTrayHeading doc "retrieves fastest" | FindPreferredTrayHeadingForRetrieval | Confirmed: InitRetrievalHeadings picks the reverse of the first-choice retrieve bay's inbound heading where reachable; no travel-time comparison. | Fix the comment ("preferred", no optimality claim). Keep the name: "retrieval heading" is the garage graph's own term (Get/SetRetrievalHeading). Also InitRetrievalHeadings' comment says bays are considered "in ascending order" while FindBayForRetrieve walks the list in reverse; reword. | 6 |
| ExpandRetrieveJob, AssignAgvs, ResolveCarriedTrayDestination, PropagateEarliestStartToChildren, OrderArrivalAfterPriorOccupant | keep | | Agree. | |

Already as Codex wants: MakeBayCommand is file-local in job_expansion.cpp; AppendAgvLiftEvent already
lives in agv_assignment.cpp.

## Placement (utils.cpp, 482 lines)

Users per function (src, tests, tools, advanced tests):

- action_graph.cpp only: CreateActionGuid, IsFloorTraversalMotion, ComputeVrcFloorTransitDuration,
  InsertVrcActionsIntoDag (~150 lines). Move into action_graph.cpp's anonymous namespace.
- job_expansion.cpp only: HasPayload, IsTrayReversedOnAgv, MakeVecsStateChange. Move there, local.
- job_expansion.cpp + bay_rebalancing_tests: ClassifyBay(s), CalculateDesiredBaySplit,
  ComputeBayRebalancingActions (~200 lines). Own pair `bay_rebalancing.hpp/.cpp` (the test already
  has that name).
- scheduler.cpp + base_state_validation_tests: ValidateBaseState. Stays shared (utils or its own header).
- Shared by two or more stages: IsCarryingTray, Make(Bay)InboundPose, ReverseHeading,
  ReversePoseHeading, IsSameOrOppositeHeading, KeepTrayHeadingIfEquivalent, MakeAgvPoseMove,
  MakeTrayMove. These stay in utils (or split into heading and event-builder headers; with ~10
  functions left, one header is enough).

## Order inside stage files

agv_assignment.cpp: AssignAgvs at line 493 of 836, its parts after it, lower-level helpers before.
tray_assignment.cpp: AssignTrays is last. Agree with entry point first, then its parts in call order,
then lower-level support, matching scheduler.hpp's declaration order. Pure moves.

## Where it would land

- Renames: in the commit that introduced each name (table). Token renames apply cleanly in every tree.
- Comment fixes: commits 1 and 6.
- Placement and order: commit 5 (where the stage files and the shared utils were made; "no function
  body changes" still holds), or defer to stage C1, whose solver extraction may move these again.
  Recommendation: do the renames, comments and the single-user moves now; do the stage-file order
  now too (it helps reviewers of this PR); leave a heading/builder header split for C1.

## As applied (item 226)

All as recommended, Build* renames and the heading/builder header split left out. Renames landed in
the commit that introduced each name (1: AssignEmptyTrayToMove, FindAssignedAgvsBlockingPickup,
ValidateEventSequence, ValidateMoveDestinationAndPath, GenerateNextActionGuid; 3: MakeBayInboundPose,
AddChargingStopBeforeTrayMove, `bay_inbound_pose`/`payload_tray_dest`/`empty_tray_dest`; 4:
MakeInboundPose, ResolveDestinationHeading with its contract). Commit 5: VRC insertion and
GenerateNextActionGuid local to action_graph.cpp; IsTrayReversedOnAgv and MakeVecsStateChange local to
job_expansion.cpp; HasPayload stays shared (ClassifyBays uses it); bay_rebalancing.hpp/.cpp; members of
agv_assignment.cpp and tray_assignment.cpp ordered breadth first from AssignAgvs / AssignTrays in call
order (file-local helpers stay on top). Commit 6: FindRetrievalTrayHeading's comment. A body-by-body
comparison (renames applied, whitespace normalised) finds only the three intended edits: the two
renamed-local functions and InitRetrievalHeadings' comment; 103 function definitions before and after.
