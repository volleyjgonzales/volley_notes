# Codex review 6 (2026-10-30) and its evaluation

Codex read the tip `276bd6a4` (source only). Seven findings, plus two of the user's rules: booleans
start with `is_`, and no `.second.second`. Checked here by reading (item 223); applied in item 224, tip `280339f9`.

| # | Finding | Check | Verdict and proposed commit |
|---|---|---|---|
| 1 | MotionScheduleOrder builds a full owning key per comparison: hash, a copy of the type string and `buffer.to_vector()` for both motions, even when the start times decide. | Confirmed. The payload copy is new in this branch (commit 4); the hash per comparison is older. | Agree: compare start, action id, hash, then the cheap fields (type as `string_view`), and the payload bytes last with `std::ranges::lexicographical_compare` on the buffers (no copy). Same lexicographic order, so the recordings must stay identical. Commit 4. |
| 2 | BuildScheduledActionsArray copies every job into a map, appends parents to the DAG's stored nodes, clears the job vector and refills it in map order. | Confirmed, with one observable effect Codex only hinted at: `response.scheduled_jobs` comes out in `unordered_map<Guid>` order, not request order (pre-existing on main). Central matches jobs by GUID (`dispatch.cpp`), so nothing relies on the order. | Agree: a GUID-to-index map and `node_indices` written in place (request order); build each output node as a local copy and add parents there, so the DAG is not modified. Re-records the response's job order in the multi-job scenarios (7 files) and nothing else; the diff must show only that. Commit 4, listed as a behaviour change. |
| 3 | `contains` + `operator[]` for the event span; use `try_emplace`. | Confirmed. The user's point: `.second` / `.first` on a pair say nothing. | Agree, in a form without pair members or an `inserted` bool: `struct ActionSpan { first_action; last_action; }`, map renamed `action_span_by_event`, and `auto& span = action_span_by_event[id]; if(!span.first_action) span.first_action = node; span.last_action = node;` (the ChainAfterLastEntityEvent idiom). TransferEventDagDepsToActionDag reads `span.first_action` / `span.last_action`. Neutral. Commit 3 (where EventActionSpans was named). |
| 4a | "ToActionNode replaces the placeholder command ids" (job_expansion.cpp 38) is false. | Confirmed: ToActionNode copies the bay command; central's `schedule.cpp:106` sets every command id to its node's GUID. The comment is this branch's (commit 3). | Correct it to say central does it. Commit 3. |
| 4b | "If this happens, consider adding a transition" (357) is speculation. | Pre-existing on main. | Delete. Commit 1 (comment sweep). |
| 4c | "never regresses on this path" (509). | Pre-existing. | "Best effort: log repark failures and continue." Commit 1. |
| 4d | "Snapshot first ... stable iteration set" (524) is wrong: ExpandReparkTrayJob mutates `ctx`, not the local `working_state`. | Confirmed. | Drop the collection pass and the comment; loop over `working_state.GetTrays()` directly (same order, same calls). Neutral. Commit 1. |
| 5 | StopChargingBeforeTrayMove's error is a sentence fragment its callers complete. | Confirmed; GetFirstSystemFloor has the same pattern ("The error completes ...but it "). Both were made in this branch to keep client-visible texts byte-identical. | Agree for both, as a deliberate message change: each helper returns a standalone sentence, callers prefix context with ": ". Changes two client-visible failure texts per helper; re-records `plan/retrieve_job/FromUnavailableCharger.yaml` and `plan/repark_tray_job/FromUnavailableCharger.yaml` (message only). Commit 4. |
| 6 | utils.hpp leans on transitive includes; scheduler.hpp includes it with angle brackets. | Confirmed: `<memory>`, `<vector>`, `<unordered_map>`, `<utility>`, `<cstdint>`, the VecsStateChanged message and `planner_core/schedule_events.hpp` (AgvMove, TrayMove) are used but not included. The angle-bracket include is on main. roslog: no deprecation marker; leave it. | Agree. Commit 5 (where utils.hpp gets its shared helpers). |
| 7 | Do not turn KeepTrayHeadingIfEquivalent into a value-returning helper for its own sake. | Agree. | No change. |
| user | Booleans start with `is_`. | Scan of `src/` and `include/`: no bool local or member without `is_` (functions use `Is*`/`Has*`). Codex's `inserted` would have broken it; item 3's form has no bool. | Kept in every new line. |
| user | No `.second.second`. | Covered by item 3. Related, same rule: pairs still in the package: ResolveBlockingTrays returns `pair<optional<GaragePose>, PlannedTrayMoves>`; CalculateDesiredBaySplit `pair<int,int>`; the two ComputeBayRebalancingActions `pair<vector, vector>` (`.second.push_back`); `ordered_matching` vector of pairs; AgvAssignmentEdgeKey (a map key). | Offer: named structs for the first three (and `ordered_matching`); keep AgvAssignmentEdgeKey a pair or make it a struct with a hasher. Neutral. Commit 1. |

Also seen, not proposed for this PR: BuildScheduledActionsArray gives every VECS command the default
entity id, so all VECS commands are chained one after another across chargers (pre-existing, safe
but over-serialised). A ticket.

Mechanics if applied: commits 1 to 6 are all rebuilt (item 4b-d and the pairs touch commit 1), each
intermediate commit built and tested on its own.

## As applied (item 224)

- Landed as proposed except where noted. Pairs went into commit 6, not commit 1: in commit 1 the
  callers still assign ResolveBlockingTrays' pair with `std::tie` (rewritten in later commits), so a
  struct there would have meant rewriting code that is replaced anyway.
- The new struct is `TrayDestinationPlan`, not `BlockingTrayResolution`: Scheduler already has a
  nested `BlockingTrayResolution` (FindBlockingTrayResolution).
- `ordered_matching` is gone: the loop walks the AGV order directly; the BottleneckAssignment pair is
  unpacked once as `[root_event_by_agv, bottleneck_threshold]` (the second is the threshold that
  produced the matching).
- Job order: the recordings stable-sort `scheduled_jobs` (test `plan.cpp`), so none changed; the
  order check in ReparkTrayJob.ReturnsTrayAfterEarlierRepark fails on the old builder (1002 before
  1001) and passes now.
- Messages: retrieve/repark "...that is on a VECS: v23 is in state 1, neither charging nor ready to
  charge"; bay transitions "...to READY_TO_RETRIEVE: b<id> has no system floor" / "has an empty
  list of system floors". Only the two FromUnavailableCharger recordings changed, message only.
- The entity scan for the action array uses `contains` + `at` and the span uses `operator[]`, so
  no `.second` or `inserted` bool appears; the comparator uses Interval's GetBegin/GetEnd instead
  of GetTimes().first/.second.
