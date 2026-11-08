# Codex review 2 of PR #1036 (tip `9c8637c4`), 2026-11-05

Same prompt as review 1 with the tip updated. Quoted as received; evaluation follows.

## The review

> Reviewed `9c8637c4`, the updated notes and the live PR description. The previously reproduced insert
> failure is fixed; no new reproduced blocking defect. The remaining concern is coverage of eviction
> combined with blocking-tray moves.
>
> 1. **Coverage gap / plausible limitation: reachability is checked before prerequisite tray moves**
>    (`tray_assignment.cpp:693`). `MoveAgvToFreeCharger` rejects placements unless the root destination is
>    reachable in the state before blocking trays move; the later check after the prerequisite moves is
>    never reached by rejected placements, and the prerequisites' own routes are not validated. Evaluate
>    each candidate relocation against the resulting tray plan, or add a scenario combining eviction with
>    a required blocking-tray repark. Plausible, not reproduced (the blocker probe stashed, as did its
>    control).
> 2. **Naming: `IsDestinationReachable` hides the entity and the carrier assumption** (`:703`). Rename to
>    `IsTrayDestinationReachable`; explain the under-tray exemption locally (the prospective carrier before
>    assignment); qualify "validation's own filter" in the notes.
> 3. **Small rule issues.** `DependsOn` → `IsDependentOn` with `[[nodiscard]]`; `loaded_departure` →
>    `loaded_departure_index_opt` with `.value()`; `agv_move` can be `const`; the stage test's `stash` /
>    `stall` need `_opt` names and `.value()`, and "not P15" does not prove a stash, so assert a waypoint;
>    the comment above `ExpectEviction` repeats the assertions. Accepts the rationale for
>    `overlaps_destination`.
> 4. **Documentation / commit hygiene.** The PR text still names `RegisterTransition`; the last commit is
>    described by the review it answers rather than its behaviour; it mixes scheduler fixes with the
>    viewer correction, against the one-topic convention. Fold corrections into their commits before merge.
>
> Closed from review 1: the route-failure probe now stashes instead of erroring; resolver calls add the
> AGV exclusions centrally; `ExpectEviction` checks ancestry and job; the hash clears the selection; the
> renames are clearer. Correction: the exclusion regression was introduced by `2008ca0a`, as the notes say,
> not by `4d7401c7`.
>
> Greptile pre-answers: stable sorting keeps the charge job's tie behaviour; the under-tray exemption is
> the prospective carrier; recursive eviction is not verified; two-AGV eviction is not established (each
> intermediate check still sees the remaining blocker); the C1 API and #1031 work stay deferred.
>
> Verdict: no reproduced blocker to leaving draft; add the combined blocking-tray coverage or document the
> limitation, and finish the naming and documentation corrections before merge. Verified: builds with 0
> warnings; 201 + 24 + 15 tests with recording comparison; tidy, Black, mypy; 69 scenarios rendered.

## Evaluation

| # | Verdict | What was done |
|---|---|---|
| 1 | **Accepted.** | The placement loop became a depth-first search over the blocking AGVs and their ranked chargers (`EvictBlockingAgvs`), and the feasibility check moved to the leaf, where every AGV has been placed: the tray plan is resolved there and `IsTrayPlanFeasible` walks its blocking-tray moves in sequence (each move's own route, then the move applied) before the root move. That also answers the two-AGV objection: the check no longer sees a remaining blocker. No scenario combines an eviction with a blocking-tray repark; the Pecos states in the set do not produce one without inventing a layout, so the limitation stays documented. |
| 2 | **Accepted.** | `IsTrayDestinationReachable`; one line beside the exemption; the notes say "validation's filter, with the AGV under the tray taken for its carrier". |
| 3 | **Accepted.** | All applied; the stage test asserts a waypoint through the layout. |
| 4 | **Accepted, overtaken.** | The user asked for a three-commit history (viewer, tests, solution), so the five commits were rebuilt from the final tree; the PR text was rewritten for them and names `RecordTransitionOccupancy`. The test commit records the final behaviour and is red on its own until the solution commit; it compiles on its own (checked). |

## Fixes applied (in the rebuilt commits)

- `EvictBlockingAgvs` (recursive), `IsTrayPlanFeasible`, `IsTrayDestinationReachable`; `MoveAgvToFreeCharger`
  and the two-stage check are gone.
- Tests: `IsDependentOn`, `loaded_departure_index_opt`, `stash_opt` / `stall_opt` with the waypoint assertion,
  no comment above `ExpectEviction`.
- Recordings unchanged by the search change: the route scenario still sends AGV 7 to C14.
