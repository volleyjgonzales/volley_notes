# SW2-876 — Implementation plan for pause and software E-stop policy

Status: implementation plan only; no C++ patch has been applied or built. This plan is based on `agvhito-repomix.md` and the expanded action plan agreed in this conversation. It supersedes the policy choices in the earlier problem/solution document where they differ, especially Error entry and exit. Paths below are relative to the `agvhito` package; prepend `src/agvhito/` in the full checkout.

## 1. Target behavior and scope

Idle and Stopped must avoid the routine pause/software E-stop actions that interfere with firmware auto charging. Starting a new order and recovering telemetry must not implicitly pause or unpause. Boot and an explicit execution Resume share a verified unpause operation followed by a minimum 200 ms settling period. Error continues to request software E-stop on entry and releases it on successful recovery exit.

| State / hook | Delete | Add or retain | Resulting behavior |
| --- | --- | --- | --- |
| `StoppedState::OnEntry` | `MakeSoftEStopAction(true)` publication, verification, related log/error handling | Retain order-queue clearing | Stopped is an adapter dispatch state; entry does not command firmware E-stop. |
| `IdleState::OnEntry` | `MakeSoftEStopAction(false)`, `MakeStartPauseAction()`, pause verification, associated blocks/logs | Retain freshness and hardware-stop checks, unexpected-order cancellation; add completion verification after cancellation | Idle does not release a stop or engage pause. |
| `ExecutingOrderState::OnEntry` | Conditional call to `VerifiedUnpause`, and that helper's implementation/declaration | Retain map/order workflow; replace implicit unpause with a fail-fast precondition for a new order | Only boot or explicit Resume owns unpause. |
| `ExecutionRecoveryState::OnEntry` | `MakeStartPauseAction()` and tolerated verification failure | Retain hook for a truthful recovery log | Recovery waits for telemetry without commanding a firmware pause. |
| `ExecutionRecoveryState::OnExit` | `MakeStopPauseAction()` and tolerated verification failure | Retain recovered outcome; handle cancellation explicitly | Freshness recovery does not unpause. |
| `ErrorState::OnEntry` | Nothing from the existing E-stop policy | **Retain `MakeSoftEStopAction(true)`**, tolerated entry verification failure, diagnostics and queue clearing | Error still attempts to stop the robot. This differs from the older proposal. |
| `ErrorState::OnExit` | No existing override to delete | Add verified `MakeSoftEStopAction(false)` on successful recovery only | Return recovered only after successful release verification. Canceled exit sends no release. |
| `BootingState::Execute` | `MakeStopPauseAction()` from the preparation batch; duplicate final-state verification block | Add `UnpauseAndSettle` between preparation and all map actions | Verify the three preparation actions, unpause separately, settle, then prepare maps. |
| `ExecutionPausedState::OnExit` | Direct unpause publication | Add `UnpauseAndSettle` on explicit Resume only | Resume returns to execution after the guard and final state verification. |
| `ExecutionPausedState::OnEntry` | Nothing | Retain `MakeStartPauseAction()` | Explicit execution pause remains supported. |

Supporting changes below—Idle traversal verification, new-order preconditions, explicit exit outcomes, and Error release-failure routing—make the requested deletions concrete. They do not add another automatic pause/unpause path. Keep the explicit severe-stop service, terminal-failure software stop, simulator action handlers, and action factories. Keep existing exception-clear actions at boot. Remove the exception-clear actions that existed solely inside the deleted Idle release batch and order-start unpause helper; do not introduce a new unconditional exception-clear policy.

## 2. File-by-file change list

| Package-relative file | Operation | Exact change |
| --- | --- | --- |
| `include/agvhito/sm/timing.hpp` | Add | `kUnpauseSettlePeriod` of 200 ms. |
| `include/agvhito/sm/context_utils.hpp` | Add | Declaration and contract for `UnpauseAndSettle`. |
| `src/sm/context_utils.cpp` | Add | Shared helper and private cancellation-aware steady-clock wait. Existing generic publication/verification behavior stays intact. |
| `include/agvhito/sm/detail/unpause_settle.hpp` | Add | Internal steady-clock wait used directly by production helper and focused wait tests. Complete implementation appears in section 9. |
| `src/sm/booting_state.cpp` | Modify/delete | Split preparation/unpause; use helper; delete duplicate ready check and misleading logs. |
| `src/sm/execution_paused_state.cpp` | Modify | Explicit Resume completion outcome; guarded exit; replace direct unpause with helper. |
| `src/sm/stopped_state.cpp` | Delete/modify | Delete E-stop block and unused includes; retain queue clearing and `Step`. |
| `src/sm/idle_state.cpp` | Delete/modify | Delete soft-stop release and pause blocks; add physical traversal verification after unexpected-order cancellation. |
| `include/agvhito/sm/executing_order_state.hpp` | Delete | Private `VerifiedUnpause` declaration. |
| `src/sm/executing_order_state.cpp` | Delete/modify | Delete helper definition/call; add new-order preconditions and truthful logs. |
| `src/sm/execution_recovery_state.cpp` | Delete/modify | Delete entry/exit actions; preserve freshness checks; explicitly identify normal recovered completion. |
| `include/agvhito/sm/execution_recovery_state.hpp` | Modify | Describe telemetry-only recovery. Retain current hooks. |
| `include/agvhito/sm/error_state.hpp` | Add/modify | Add `OnExit` override and required direct includes; correct class comment. |
| `src/sm/error_state.cpp` | Add | Guarded, verified recovery release in `OnExit`; retain entry behavior. |
| `include/agvhito/sm/state_strings.hpp` | Modify | Add Error `kOutcomeErrored` → terminal routing for failure of the new exit operation. |
| `include/agvhito/sm/error.hpp` | Add | Named `kErrorUnexpectedPause` for refused new-order dispatch; reuse existing errors for publication, state and E-stop failures. |
| `CMakeLists.txt` | Add | State-machine GoogleTest target linked to state-machine/core/comms/topics libraries. Confirm source-glob behavior to avoid duplicate registration. |
| `test/sm/*` | Add | Fixture, helper regressions, changed-state tests and lifecycle/routing integration tests detailed below. |
| `test/topics/test_state_predicates.cpp` | Extend | Verify `TraversalComplete()` independently of cancel action `FINISHED`. |

Use the existing context-utils module for the public helper and the small internal header above for the shared wait/test seam. No new production thread, ROS service, blackboard key, or generic `yasminx` modification is planned. There are no existing `test/sm` tests in the supplied snapshot; do not claim that named state tests already exist.

## 3. Shared `UnpauseAndSettle` implementation

### 3.1 Interface and clock contract

Add inside `volley::agvhito::sm`:

```cpp
// include/agvhito/sm/timing.hpp
/// Minimum steady-clock settling period after stopPause is verified FINISHED.
/// Temporary HITO firmware readiness workaround for SW2-876; this delay does not detect auto_run.
inline constexpr std::chrono::milliseconds kUnpauseSettlePeriod {200};

// include/agvhito/sm/context_utils.hpp
/// Publish stopPause as a single-action batch and verify that it reaches FINISHED.
/// Wait at least kUnpauseSettlePeriod using a steady clock after successful action verification,
/// then verify non-stale AGV state reports no E-stop and no pause.
/// @p blackboard supplies the publisher, action assembler, action statuses, and tracked AGV state.
/// @p context supplies the logger and clock used by existing publication/state verification.
/// @p is_canceled is polled while waiting; cancellation or ROS shutdown aborts the operation.
/// Does not release software E-stop, clear exceptions, or detect firmware auto_run readiness.
/// @return Empty on success, or the publication/action/state verification error; a canceled
/// error when interrupted. Callers must not issue follow-on control commands on failure.
[[nodiscard]] stdx::Expected<void, yasminx::Error> UnpauseAndSettle(
    const yasmin::Blackboard& blackboard,
    const yasminx::StateContext& context,
    std::function<bool()> is_canceled);
```

Document the period as a temporary HITO firmware workaround for SW2-876. Use `stdx::Expected`, matching the repo, rather than migrating to `std::expected` as part of this patch.

Define `t_verified` as the steady-clock time immediately after successful `VerifiedPublish(stopPause)`. Subsequent normal state-machine control publication must occur at least 200 ms after `t_verified`. Transport time and waiting for `FINISHED` do not count toward the guard. The 50 ms ROS cycle and 100 ms helper polling period do not establish this lower bound.

### 3.2 Algorithm in `context_utils.cpp`

1. Compose an interruption predicate from the supplied cancellation callback and ROS shutdown. Match the current root's global `rclcpp::ok()` convention; confirm the real checkout's ROS context if it differs.
2. Call `VerifiedPublish({MakeStopPauseAction()}, blackboard, context, interrupted)`. This **one-action batch** prevents an enable-map or unrelated action from sharing the unpause message. Use actual generated action IDs and preserve existing failure types.
3. On success, record a `std::chrono::steady_clock` deadline of now + 200 ms. On any publication/action failure or cancellation, return the original error without entering the guard.
4. Wait in short slices, approximately 10 ms. Before every success check and after every wakeup, check interruption. Recalculate remaining time; sleep for `min(remaining, poll_period)`. A canceled wait returns `kErrorCanceled`. Check the deadline again after early wakeups; avoid a single uninterruptible sleep.
5. After the deadline, call existing `VerifyState` with `All({AnyEStopIs(false), PausedIs(false)})` and the same interruption predicate. Return its success/error. This reads non-stale telemetry but does not require a message newer than the unpause; do not claim event correlation beyond the existing API.
6. Only the caller's success branch proceeds to maps, orders, or a resumed outcome. Log guard start/completion without saying that `auto_run` was detected.

Add direct includes for `<algorithm>`, `<chrono>`, `<thread>`, `<rclcpp/utilities.hpp>`, and `agvhito/topics/instant_actions.hpp` where needed. Keep callbacks synchronous and uncached. A local private deadline-wait function may be extracted into `sm/detail` for focused deterministic tests; it must not widen the public state-machine API or alter production timing.

The helper does not release software E-stop or clear exceptions. That work belongs to the relevant caller policy. It is not a mutex over all publishers: severe-stop requests remain able to publish immediately, and manager diagnostics have separate paths. Existing generic verification uses `context.clock`; this patch gives the new **settling interval** a steady clock, without claiming to fix all simulated-clock timeout behavior.

## 4. State changes in implementation order

### 4.1 Booting

In `BootingState::Execute`, retain the initial non-stale state wait, its cancellation path, and existing map inventory/verification.

Replace the current four-action preparation batch with:

```cpp
// Unpause must be separate from preparation so its completion starts the firmware settling guard.
const auto prepared = VerifiedPublish(
    {MakeSoftEStopAction(false), MakeCancelOrderAction(), MakeExceptionClearAction()},
    *blackboard, GetContext(), [this] { return is_canceled(); });
if(!prepared.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, prepared.error());
}

// Do not publish map actions until verified unpause and the full settling guard have succeeded.
const auto unpaused = UnpauseAndSettle(
    *blackboard, GetContext(), [this] { return is_canceled(); });
if(!unpaused.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, unpaused.error());
}
```

Delete the old `VerifyState(All({AnyEStopIs(false), PausedIs(false)}))` block: the helper owns it after the guard. Keep the subsequent fresh-state read used to calculate map work. Every download, enable and delete-map publication remains after successful helper completion. Change “setting pause” and “ready” logs to reflect preparation, verified unpause and guard completion.

Retaining a three-action preparation batch retains current batch semantics; vector order does not establish firmware execution order. This plan does not add serial preparation commands beyond separating unpause.

### 4.2 Explicit execution pause and Resume

Keep `ExecutionPausedState::OnEntry` and its verified `MakeStartPauseAction()`.

Change the Resume branch of `Step` from `Finished {}` to:

```cpp
// Carry explicit Resume authorization into OnExit; other exit paths must not unpause the AGV.
return yasminx::LifecycleState::Finished {.outcome = kOutcomeResumed};
```

Use the currently ignored `step_outcome` parameter in `OnExit`. In order:

1. If canceled, the outcome is `yasminx::kOutcomeCanceled`, or ROS is shutting down, return canceled without any unpause publication.
2. Require `step_outcome == kOutcomeResumed`; an absent/unexpected completion is an error, not authorization to resume. Reuse `kErrorWrongRequest` for an invalid completion diagnostic and route `kOutcomeErrored` to Error.
3. Call `UnpauseAndSettle`. On failure, use the existing error-result convention with `kOutcomeErrored`. The root's cancellation handling must still produce canceled on cancellation; verify this in the actual dependency.
4. Return `kOutcomeResumed` only on helper success.

`ExecutingOrderState::OnEntry` already returns early when re-entered from paused; preserve that behavior. Resume must not republish the active order, pop the pending queue, or enable a map again. Physical motion may resume before the guard completes; the delay protects follow-on host commands, not delayed physical resumption.

### 4.3 Stopped

Delete the leading log, `VerifiedPublish({MakeSoftEStopAction(true)})`, and failure return from `StoppedState::OnEntry`. Retain queue clearing and return success. Queue clearing will now execute even though no action verification occurs first.

Remove `context_utils.hpp` and `topics/instant_actions.hpp` from this `.cpp` if unused after the deletion; retain includes required by `Step` and the blackboard. Keep stale-state waiting, localization loss → Localizing, and Activate → Idle unchanged. Stopped entry does not prove physical stopping; controlled-stop cancellation already has its separate traversal-completion path.

### 4.4 Idle

Delete the **entire** `if(IsSoftEStopped(state))` release block, including its `MakeExceptionClearAction()` companion and verification/error/logging. Delete pause publication, its error handling, `VerifyState(PausedIs(true))`, and “currently paused” logging. Do not leave a predicate waiting for an action no longer sent.

Retain the non-stale state requirement and hardware E-stop check. Keep `IdleState::Step` E-stop checks, controlled-stop routing and queued-order routing. An existing software E-stop therefore remains visible to the existing Step logic; Idle will not clear it. Error recovery exit is now the ordinary recovery-release path, in addition to boot.

Keep unexpected traversal cancellation in entry. Since Idle no longer first pauses the robot, add `VerifyState(..., TraversalComplete(), ...)` after successful `VerifiedPublish(cancelOrder)` inside that branch. `FINISHED` for cancel does not prove deceleration/traversal has finished. Return `kOutcomeErrored` on verification failure. Log successful cancellation/completion only afterward. The old entry snapshot may decide whether cancellation is required; the completion check must read live tracked state through `VerifyState`.

This supporting completion check was also in the earlier proposal. It preserves the intent that idle dispatch does not race an unexpectedly active onboard order, without reintroducing a pause. Keep existing stale-state and hardware-stop errors; do not replace them with unconditional success to accommodate the action deletions.

### 4.5 Starting an order

Delete these together:

- The `if(IsPaused(state))` block in `ExecutingOrderState::OnEntry` that logs unpause/exception clearing and calls `VerifiedUnpause`.
- The private `VerifiedUnpause` declaration in `executing_order_state.hpp`.
- Its definition in `executing_order_state.cpp`, including the `{MakeStopPauseAction(), MakeExceptionClearAction()}` batch, `PausedIs(false)` verification, and failure handling.
- The unconditional “reporting un-paused” log unless made conditional on an actual check.

For a **new** order, after the existing queue/non-stale state checks and before map enabling, action-manager clearing or order publication:

1. Call `CheckEStopClear(state)` and propagate its existing hardware/software-stop outcome/error.
2. If `IsPaused(state)`, return `yasminx::MakeUnexpected(kOutcomeErrored, Error{.type = kErrorUnexpectedPause, ...})` explaining that new-order entry does not unpause. Add this error constant in `sm/error.hpp`.
3. Otherwise continue the existing enabled-map comparison, order publication/echo verification, active-order installation and queue pop.

The paused/recovery early return remains before this new-order workflow. Recovery does not authorize new publication and does not replace the existing `Step` checks. Tests must distinguish new-order entry from both re-entry paths. Preserve the execution self-transition for the next queued order.

Do not retain `MakeExceptionClearAction()` as a hidden replacement for the deleted helper. If firmware needs another exception-clear path, identify that separately; boot still clears exceptions, and firmware `stopPause` behavior is not a reason to unpause inside order entry.

### 4.6 Telemetry recovery

Keep `ExecutionRecoveryState::OnEntry` as a successful, log-only hook saying it is waiting for state, filtered pose and common data. Delete its pause publication, warning-on-verification-failure block, and comments that imply a pause is being attempted.

Keep all three freshness gates and the `Continue {}` behavior in `Step`. Change normal completion to `Finished {.outcome = kOutcomeRecovered}` so exit can distinguish completion from cancellation.

Keep `OnExit` as a publication-free hook. Return canceled for cancellation/shutdown, forward `kOutcomeRecovered` on normal completion, and report an errored diagnostic for missing/unexpected completion. Delete unpause publication, tolerated failure logic and obsolete firmware comment. Keep its header declaration; remove unused context-utils/instant-actions includes from the `.cpp`. Update the class comment to describe telemetry-only recovery.

Do not add `UnpauseAndSettle` here. Loss of host telemetry no longer commands a pause; the onboard order may continue during recovery. Preserve active-order tracking and the existing re-entry path without republishing the order.

### 4.7 Error recovery release

**Keep `ErrorState::OnEntry` unchanged in policy:** it still requests `MakeSoftEStopAction(true)`, tolerates verification failure on entry, logs diagnostics, clears the queue and records `entry_stamp_`. Keep the existing Step requirement for non-stale state, hardware E-stop cleared, and the five-second recovery delay. Step already finishes with `kOutcomeRecovered` and clears requests, active order and queue before exiting.

Add an `OnExit` declaration matching the other lifecycle states:

```cpp
/// Release software E-stop only after normal error recovery, then verify observable stop clearance.
/// @p blackboard supplies the tracked AGV state and instant-action publication dependencies.
/// @p step_outcome must identify recovered completion; canceled exit or shutdown sends no release.
/// @return The recovered outcome after successful release/state verification, the canceled outcome
/// when interrupted before release, or an errored result on invalid completion or release failure.
[[nodiscard]] stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> OnExit(
    yasmin::Blackboard::SharedPtr blackboard,
    std::optional<yasminx::Outcome> step_outcome) override;
```

Add direct `<optional>`, outcome/transition headers as needed in `error_state.hpp`. Correct its current comment: recovery waits for hardware E-stop clearance, then the new exit releases software E-stop; it does not wait for software E-stop to already be clear.

Implement exit in this order:

1. Check cancellation, canceled outcome and ROS shutdown **before release**. Return canceled and send nothing in those paths.
2. Require `step_outcome == kOutcomeRecovered`. Missing/unexpected completion returns an error without release.
3. Re-check fresh state and hardware E-stop immediately before sending. The Step observation may have changed. Stale state or newly engaged hardware E-stop returns an error without release.
4. Call `VerifiedPublish({MakeSoftEStopAction(false)}, ...)` with a cancellation/shutdown predicate. Send the release even when cached telemetry reports no software E-stop: entry may have sent activation without successfully observing it.
5. After action success, use `VerifyState(..., AnyEStopIs(false), ...)` before reporting recovered. This is a proposed supporting check that confirms observable stop clearance. It is not firmware readiness or traversal-completion proof.
6. Return `kOutcomeRecovered` only on success. On transport/action/state-verification failure, propagate the original error with `kOutcomeErrored` using the routing below. Do not log-and-continue to Stopped after an unverified release.

There is no `stopPause` in this hook and no new 200 ms barrier for software E-stop release: the requested guard addresses `stopPause` specifically. Do not claim that release of software E-stop cannot resume a retained onboard order. Local active-order/queue clearing does not cancel such an order; validate this recovery behavior on the controlled robot test setup.

#### Error exit failure routing

The supplied `kErrorTransitions` contains only recovered → Stopped and canceled → terminal. A new exit error cannot blindly return `kOutcomeErrored` without declaring a route.

Proposed implementation: add `{kOutcomeErrored, kOutcomeTerminal}` to `kErrorTransitions`. `OutcomesOf(kErrorTransitions)` then declares the extra outcome automatically. This fails the root rather than entering Stopped after unsuccessful release or recursively re-entering Error and activating/releasing in a loop. Preserve and test the existing root/`Agv::Step` terminal-failure software-stop response. An error-to-terminal route is an additional **failure** route; successful recovery topology stays the same.

This changes the graph from 36 to **37 declared transitions**. Update any diagram-generation audit expecting 36 when rendering the patched snapshot. The current action-map diagram is a baseline, not a picture of this future implementation.

## 5. Cancellation and lifecycle integration

The AGVHITO snapshot imports `yasminx`; its implementation is not included. Historical excerpts in the background document show exit invoked on normal completion and cancellation, but bypassed on entry/Step error. Verify those facts in the actual checkout before implementing tests or relying on exit behavior. In particular, confirm forwarding of explicit `Finished.outcome`, storage/propagation of `ErrorOutcome`, and canceled-outcome precedence.

Do not rely on a lifecycle wrapper overriding the final canceled outcome after `OnExit`: it cannot retract a command already published. Explicit pre-send guards plus the existing `VerifiedPublish` pre-send cancellation check are required for both resume and Error release. Cancellation can race a publication already in progress; tests should prove that cancellation observed before entry to publication sends nothing, without claiming atomic exclusion against all asynchronous requests.

The plan adds no unconditional release in destructors or generic cleanup. Error entry/Step failure and root shutdown must not trigger Error recovery release. No new callbacks outlive their state. Always join test workers during fixture teardown, including failing assertions.

## 6. Tests: add, extend, replace, delete

### 6.1 New fixture and target

Add `test/sm/state_test_fixture.hpp` (and a `.cpp` only if useful) with the real typed blackboard, tracked state, `ActionStateManager`, `InstantActionAssembler`, order queue and context. Use `SimMqttClient` for successful transport scenarios; reuse patterns from `test/comms/test_sim_mqtt.cpp`, `test/test_instant_action_assembler.cpp`, and `test/test_tracked_message.cpp`.

Subscribe before starting a worker. Decode real outbound instant-action/order messages and correlate actual action IDs. A test responder supplies `FINISHED`/`FAILED` and fresh telemetry. Use a recording publisher double for transport failure/timeout cases the successful simulated transport cannot inject. Record publication order and steady-clock timestamps in a synchronized event ledger.

Initialize every telemetry field required by safety/map/order predicates, including `safety_state.e_stop`; do not rely on unspecified defaults. `PausedIs(false)` currently treats an absent flag as false—retain and document that existing behavior rather than silently changing protocol semantics.

Use condition variables/promises or bounded receiver waits for synchronization. Negative action assertions should inspect the complete event ledger after hook/worker completion, not infer success from an arbitrary 50 ms timeout. Keep telemetry fresh throughout intentional real-time waits. Test cancellation with an explicit guard-entry seam so it occurs during settling rather than after it.

Add an `agvhito_state_machine_tests` target under `BUILD_TESTING`, following existing `volley_add_gtest` conventions and linking `${PROJECT_NAME}_state_machine_lib`, core, comms and topics libraries as required. Check the actual `volley_cmake` directory-glob behavior: if the existing core target recursively includes `test/sm`, exclude those sources there to avoid duplicate/unlinked registrations. Do not invent an exclusion option without checking the installed macro.

### 6.2 Required test cases

| New test file | Cases / setup | Required assertions |
| --- | --- | --- |
| `test/sm/test_unpause_and_settle.cpp` | Immediate `FINISHED`, fresh unpaused/no-E-stop state | Exactly one `stopPause` action in its batch; helper does not succeed until full 200 ms after guard start. |
| Same | Early firmware completion with a test-specific command acceptance deadline | A follow-on control message is not sent before the full guard; firmware double distinguishes action completion from command acceptance. |
| Same | Delay `FINISHED` by 300 ms | Another full 200 ms guard follows observation; send-time delay does not consume it. |
| Same | Canceled before publication; canceled during guard; shutdown during guard | Correct canceled error; pre-canceled case sends nothing; interrupted worker sends no follow-on control. |
| Same | Transport failure/timeout, `FAILED`, action verification timeout | Original error is returned; no downstream control. The concrete timeout test exercises the existing real 35 s timeout; the steady guard is not advanced or bypassed. |
| Same | Still paused, any E-stop, or stale state after guard | Helper cannot succeed until the existing final predicate/freshness requirements hold; timeout/cancellation prevents follow-on publication. |
| `test/sm/test_booting_state.cpp` | Maps present/missing, initial state stale then fresh | Preparation contains only soft-release/cancel/exception-clear; unpause is separate; all map actions occur after guard; existing map choices/outcome preserved. |
| Same | Preparation failure, unpause failure, cancellation during guard | No map publication and no `booted` success. Check cancellation routing through the real lifecycle/root as applicable. |
| `test/sm/test_execution_paused_state.cpp` | Entry, wait, explicit Resume | Entry emits one start-pause; no unpause while waiting; explicit Resume emits one guarded stop-pause and returns resumed only on success. |
| Same | Canceled exit, absent/unexpected exit outcome, failed helper | No unpause on unauthorized exit; failure does not return resumed; lifecycle cancellation wins. |
| Same / lifecycle integration | Resume into executing with an existing active order | No duplicate order, map enable, active-order replacement or queue pop. |
| `test/sm/test_stopped_state.cpp` | Queue populated at entry, repeated ticks, Activate/localization loss | Queue cleared; no instant actions from entry; existing stale/localization/Activate outcomes retained. |
| `test/sm/test_idle_state.cpp` | Fresh stationary state with/without software stop | Entry publishes no pause, soft-stop release or exception-clear; existing hardware-stop rejection and Step software-stop detection retained. |
| Same | Unexpected traversal; cancel is `FINISHED` while still driving | Entry does not finish until `TraversalComplete()` holds; no pause introduced; verification failure yields error. |
| Same | Stale entry, controlled stop, queued order | Existing validation/outcomes preserved; dispatch does not require `paused == true`. |
| `test/sm/test_executing_order_state.cpp` | New order, already unpaused; map same/different | No pause/unpause/exception-clear; existing map/order publication, acceptance, active-order set and queue-pop behavior. |
| Same | New order while paused or hardware/software stopped | Correct error/outcome; no map/order publication, action-manager clearing or queue pop before preconditions pass. |
| Same | Entry from paused/recovery, or next queued order self-transition | Re-entry preserves accepted active order without republication; next-order self-transition executes new-order workflow without implicit unpause. |
| `test/sm/test_execution_recovery_state.cpp` | Each freshness input stale individually, then all fresh | No instant actions in any hook; `Continue` until all three gates; recovered exit retains active order. |
| Same | Canceled or invalid exit completion | Canceled/errored routing respectively; no publication. |
| `test/sm/test_error_state.cpp` | Error entry, including failed entry activation verification | Still emits soft-stop true; diagnostics/queue clearing retained; tolerated entry failure does not eliminate recovery behavior. |
| Same | Fresh state, hardware stop clear, 5 s elapsed, normal exit | Exactly one soft-stop false on exit; recovered only after `FINISHED` and clear-state verification; Stopped entry does not reactivate it. |
| Same | Stale state/hardware E-stop before recovery, and changes between Step and exit | No premature release; fresh/hardware recheck enforced. Software E-stop present must not prevent Step reaching the release hook. |
| Same | Canceled/shutdown/invalid exit; release transport/action/state failure | No release on unauthorized exit; failure never returns recovered; retained activation may remain in effect. |
| `test/sm/test_state_machine_policy.cpp` | Real root/lifecycle normal recovery and Error exit failure | Successful Error → Stopped → Idle does not reengage a stop/pause; release failure uses errored → terminal; terminal fault response remains available. |
| Same | Idle → executing → explicit pause → Resume; telemetry recovery round trip | Only explicit pause sends start-pause; Resume guard completes before re-entry; telemetry recovery neither pauses nor republishes an order. |

For the timing tests, assert a **lower bound**, not exact duration or a narrow upper bound. Timestamp just before exposing `FINISHED` for an integration assertion; add a focused private-wait test recording guard entry/exit to prove the full 200 ms independently of transport polling. Test a backward/forward ROS clock change at the wait seam: it must not shorten the new steady-clock interval. Do not freeze `context.clock` in a test that still depends on existing clock-based action/state verification.

Prove test sensitivity by temporarily omitting the wait: the focused interval test must fail. The early-completion firmware-double test must detect the missing guard under a synchronized execution setup. Restore the implementation before final checks.

### 6.3 Extend existing tests

Extend `test/topics/test_state_predicates.cpp` with a `TraversalCompleteTest.CancelFinishedWhileDrivingIsIncomplete` case. Report a cancel action as `FINISHED`, keep `driving=true` and an outstanding edge/node, and assert incomplete. Independently clear outstanding traversal and driving, asserting the predicate remains false until all required fields are clear. Existing `test/topics/test_state.cpp` already has traversal-helper tests; extend these only if a missing case is identified, rather than duplicating all field checks.

Retain existing factory/assembler, core, simulator and predicate coverage. The meanings of `startPause`, `stopPause`, and software E-stop actions are unchanged. Existing simulator motion and battery-model tests remain useful, but do not model firmware auto charging inhibition or the delayed `auto_run` acceptance window.

### 6.4 Tests to modify or delete in the real checkout

The snapshot has no state-specific tests to delete. If the real branch already contains tests from the previous proposal or other patches, make these replacements explicitly:

| Old expectation | Required replacement |
| --- | --- |
| Stopped publishes/verifies soft-stop true | Assert no entry publication and queue clearing. Delete the obsolete Stopped action-failure branch test; transport failures remain covered where commands still exist. |
| Idle clears soft-stop/exception, pauses, and waits for paused state | Assert those commands absent; retain stale/hardware/queue/controlled-stop checks. Delete obsolete release/pause failure tests; add unexpected-traversal completion test. |
| Order entry unpauses and clears exceptions | Replace with refused paused dispatch and no publication; delete unit tests specific to removed `VerifiedUnpause`. |
| Recovery pauses/unpauses, tolerating action failures | Replace with no-publication and all-three-freshness tests. Delete tests of removed tolerated action-failure branches. |
| Error entry sends no software stop, as in older proposed policy | Replace with retained activation test and new guarded recovery release tests. |
| Error recovery immediately reaches Stopped without exit work | Require verified soft-stop release and clear telemetry; add release-failure terminal routing test. |
| Paused `Step` yields `Finished {}` | Expect explicit `kOutcomeResumed`; direct exit tests must supply that outcome. |
| Recovery `Step` yields `Finished {}` | Expect explicit `kOutcomeRecovered`. |
| Boot includes unpause in a four-action batch, or polling alone supplies the delay | Replace with three-action preparation, singleton unpause, full measured guard and map-order assertions. |

Delete only tests of code that is removed. Move coverage of queue handling, freshness, request processing, error reporting and cancellation into replacement cases instead of dropping it.

## 7. Final action inventory and documentation updates

### 7.1 Required source comments

Comments are part of the implementation, not optional follow-up work. Put declaration contracts in
headers using the existing `///` style, `@p` for parameter names, and `@return` for success/error
semantics. Keep rationale beside the relevant implementation branch using `//`. Document observable
behavior and timing precisely; do not describe an elapsed-time workaround as a detected firmware mode.
The file-path comments in this plan identify snippet destinations and need not be copied into source.

Use the complete declaration comments in sections 3.1 and 4.7. Add the following private-helper comment
if the steady wait is factored into a function named `WaitForUnpauseSettle`:

```cpp
/// Wait at least kUnpauseSettlePeriod using steady-clock time, checking interruption between sleeps.
/// @p is_canceled includes cancellation and shutdown checks supplied by the caller.
/// @return Empty when the full interval has elapsed, or a canceled error when interrupted.
```

Place these comments on the corresponding new helper implementation steps:

```cpp
// Keep stopPause alone: another control action in this batch could run before unpause settles.

// Start the guard after FINISHED is observed; transport and action execution time do not count.

// Check interruption before reporting success, including after the final sleep.

// Check observable stop/pause state after the guard; this is not an auto_run readiness signal.
```

Replace affected class documentation with these concrete descriptions. Keep the class declarations
and existing method contracts; these are replacement comment blocks, not new classes:

```cpp
// include/agvhito/sm/stopped_state.hpp
/// State that prevents adapter order dispatch until activation is requested.
/// Clears queued orders on entry without commanding software E-stop or pause.
/// The adapter state alone does not establish that physical traversal has stopped.

// include/agvhito/sm/idle_state.hpp
/// State that waits for a pending order or controlled-stop request without commanding pause.
/// Cancels unexpected traversal on entry and verifies completion before allowing dispatch.
/// Does not release software E-stop; existing stop checks retain their error routing.

// include/agvhito/sm/executing_order_state.hpp
/// State that publishes new orders and tracks accepted order execution.
/// New-order dispatch requires non-stale state with no E-stop or pause; this state does not unpause.
/// Re-entry from explicit pause or telemetry recovery retains the previously accepted active order.

// include/agvhito/sm/execution_paused_state.hpp
/// State that explicitly pauses order execution and waits for a Resume request.
/// Normal Resume exit verifies unpause and waits the firmware settling guard before returning resumed.
/// Canceled exit does not deliberately publish unpause.

// include/agvhito/sm/execution_recovery_state.hpp
/// State that waits for fresh state, filtered pose, and common telemetry during order execution.
/// Does not command pause or unpause, and retains the accepted active order during recovery.

// include/agvhito/sm/error_state.hpp
/// State that attempts software E-stop on entry and records diagnostics while awaiting recovery.
/// Normal recovery requires fresh state, hardware E-stop clearance, and the recovery delay.
/// Recovery exit releases software E-stop and verifies observable stop clearance before returning.
/// Canceled exit does not release the stop; release failure routes to the terminal outcome.
```

Add short implementation comments where the policy would otherwise be easy to reverse accidentally:

| Location | Exact comment text to add or use as the replacement |
| --- | --- |
| `StoppedState::OnEntry`, before queue clearing | `// Stopped suppresses adapter dispatch without engaging a firmware stop mode.` |
| `IdleState::OnEntry`, before unexpected traversal cancellation | `// Cancel unexpected traversal without pausing; cancel FINISHED alone does not prove motion stopped.` |
| `IdleState::OnEntry`, before new completion verification | `// Read live tracked state until traversal is complete before permitting order dispatch.` |
| `ExecutingOrderState::OnEntry`, before new-order preconditions | `// Boot and explicit Resume own unpause; refuse paused or E-stopped new-order dispatch here.` |
| `ExecutionRecoveryState::OnEntry` | `// Telemetry recovery does not command pause; the accepted onboard order may continue.` |
| `ExecutionRecoveryState::Step`, before recovered completion | `// Carry normal completion into OnExit without publishing or replacing the active order.` |
| Paused and Error exit, before cancellation guards | `// Exit also runs on cancellation; never release pause or stop merely because the hook was called.` |
| `ErrorState::OnExit`, before fresh-state/hardware check | `// Recheck before release because the state observed by Step may have changed.` |
| `ErrorState::OnExit`, before release verification | `// Do not report recovery after an unverified software-stop release.` |
| `kErrorTransitions`, before new errored-to-terminal entry | `// Failed recovery release must not enter Stopped or repeat Error activation/release in a loop.` |

Remove comments tied to deleted branches: Idle soft-stop clearing/pause verification, Stopped stop
activation, order-start unpause/exception clearing, and Recovery's tolerated pause/unpause failures.
Keep unrelated comments about queue ownership, map selection, freshness and cancellation accurate.
Do not replace deleted actions with comments claiming that those actions still occur.

In the new regression tests, explain fixture behavior and the condition under test using `//`:

```cpp
// Model the ticket: FINISHED is observable before firmware accepts follow-on control commands.

// Record before exposing FINISHED so host polling cannot make the measured lower bound shorter.

// Cancel at the guard-entry synchronization point; this must interrupt settling, not a later stage.

// Inspect the completed publication ledger; a short receive timeout is not proof of action absence.

// cancelOrder FINISHED is independent of driving and outstanding node/edge traversal.
```

Review comments alongside the tests: both must describe the same batch boundaries, clock origin,
exit authorization, state predicates and failure routing. No test is needed solely to assert prose
formatting; source review verifies that the required comments accompany the implementation.

### 7.2 Action inventory and diagram updates

Expected production state-machine policy after the patch:

| Factory / helper | Allowed state-machine locations |
| --- | --- |
| `MakeStartPauseAction()` | `ExecutionPausedState::OnEntry` only. |
| `MakeStopPauseAction()` | Inside `UnpauseAndSettle` only; helper called from Boot Execute and explicit paused Resume exit. |
| `MakeSoftEStopAction(true)` | Error entry retained; no Stopped entry call. Existing non-state service/terminal-fault calls retained. |
| `MakeSoftEStopAction(false)` | Boot preparation and Error recovery exit; no Idle call. |
| `MakeExceptionClearAction()` | Boot preparation; no Idle release batch or new-order unpause helper. |

Update state/header comments and ticket documentation that says Idle is paused, Stopped activates software E-stop, order entry unpauses, or telemetry recovery pauses. Mark the old problem/solution policy as superseded by this plan, especially its removal of Error entry activation and boot-only release discussion. Preserve the existing diagrams as labeled baseline snapshots until regenerated against the implemented source.

When updating `generate_agvhito_action_map.py`, review its hard-coded snapshot expectations and annotated conditions rather than merely decreasing the call count. The new shared helper must be attributed to Boot and paused exit, and the added Error exit release must be shown. Update `generate_agvhito_state_machine.py` for the additional Error failure edge (37 total). Do not label the guard or removal policy as current behavior before the code patch exists.

## 8. Implementation sequence and acceptance

1. Inspect the current branch and dependency lifecycle source; confirm this snapshot's hooks and transition maps. Register the fixture/test target and establish command/outcome recording.
2. Implement the named guard/helper and timing tests. Change Boot and explicit Resume together; verify no map/order path bypasses the guard in those flows.
3. Delete Stopped/Idle/order-start/recovery actions and their dead branches/declarations. Add Idle traversal completion and new-order preconditions; run the changed-state tests.
4. Add Error release hook, header/comment changes and errored → terminal route. Add real lifecycle tests for normal recovery, cancellation and release failure.
5. Clean includes, run format/static checks required by the checkout, build and run all AGVHITO targets. Re-run the action inventory against the patched sources.
6. Exercise simulation boot/maps, queued orders, explicit pause/Resume, controlled stop, Error recovery and telemetry recovery. Use the test firmware double for early-completion acceptance behavior; normal simulation alone does not reproduce it.
7. Validate on the team's controlled hardware setup: auto charging remains eligible in Idle/Stopped; Error release followed by Stopped does not reactivate stop; first post-unpause map/order is accepted; telemetry recovery behaves as intended without automatic pause. Record host action IDs, steady elapsed time, firmware mode/charging observations and version. Adapter state alone is not proof of charging or firmware readiness.

Proposed workspace commands, to run after implementation:

```bash
colcon build --packages-up-to agvhito --cmake-args -DBUILD_TESTING=ON
colcon test --packages-select agvhito
colcon test-result --verbose
rg -n 'Make(StartPause|StopPause|SoftEStop|ExceptionClear)Action|UnpauseAndSettle|VerifiedUnpause' \
  src/agvhito/include src/agvhito/src
```

Acceptance requires all requested factory removals, no dead verification branches, no private `VerifiedUnpause`, retained explicit pause/Error activation, guarded unpause at exactly the two intended caller sites, and successful Error recovery release with declared failure routing. New tests must prove both action absence and preserved queue/freshness/outcome behavior. The original early-`FINISHED` regression and full 200 ms lower bound remain mandatory.

The main behavior to review during hardware validation is that software-stop release in Error recovery can affect an onboard order even though local active-order tracking was removed, while telemetry recovery no longer requests a pause. Those are direct consequences of the requested policy. This plan does not silently add a cancellation or readiness protocol to resolve them.





## 9. Complete proposed code changes

The following patch supplies the actual additions, replacements, and deletions for the reviewed
AGVHITO snapshot. It includes comments, direct includes, declaration changes, transition routing,
the shared helper, test support, tests, and CMake registration. Unchanged code appears as diff context;
it is not an instruction to reconstruct omitted new behavior. Apply from the package root.

These are **proposed source changes**, not a compiled implementation. ROS, MQTT, VDA5050, yasminx,
and volley_cmake dependencies are not shipped in the Repomix export. Verify them in the full checkout
using the build/test commands in section 8. No placeholder functions or test-harness pseudocode are
used in this patch. The real lifecycle integration still needs execution against that dependency.

This revision fixes the test access errors reported during the first build: lifecycle integration uses the public callable state interface, and variant visitors inspect Step results without naming protected alternatives. All six affected test/support files are corrected; production code is unchanged by this follow-up.

The concrete helper uses a small `sm/detail/unpause_settle.hpp` header so focused tests can call the
same production wait directly. Include `<algorithm>`, `<chrono>`, and `<thread>` there, rather than
adding unused includes to `context_utils.cpp`. This resolves the optional test seam described earlier.
Cancellation returned by the helper maps directly to the canceled outcome in Boot and Resume exit.

Tests use hook-level calls plus the public callable state interface for lifecycle integration.
LifecycleState's private `Execute` and protected variant alternatives are not accessed by tests.
Firmware action-status and state responses are supplied by a real simulated
MQTT subscription. Existing hardware rollout checks are procedures, not additional source changes.
Baseline Python diagrams are separate historical artifacts; regenerate them from the final checkout
after implementation rather than modifying their baseline snapshot inputs in this code patch.

### include/agvhito/sm/context_utils.hpp

```diff
--- a/include/agvhito/sm/context_utils.hpp
+++ b/include/agvhito/sm/context_utils.hpp
@@ -41,6 +41,19 @@
 stdx::Expected<void, yasminx::Error> VerifyState(const yasmin::Blackboard& blackboard,
     const yasminx::StateContext& context, StatePredicate predicate, std::function<bool()> is_canceled);
 
+/// Publish stopPause alone and verify that it reaches FINISHED.
+/// Wait at least kUnpauseSettlePeriod using a steady clock after successful action verification,
+/// then verify non-stale AGV state reports no E-stop and no pause.
+/// @p blackboard supplies the publisher, assembler, action statuses, and tracked AGV state.
+/// @p context supplies the logger and clock for existing publication/state verification.
+/// @p is_canceled is polled while waiting; cancellation or ROS shutdown aborts the operation.
+/// Does not release software E-stop, clear exceptions, or detect firmware auto_run readiness.
+/// @return Empty on success, the publication/action/state verification error on failure,
+/// or a canceled error when interrupted. Callers must not publish follow-on control on failure.
+[[nodiscard]] stdx::Expected<void, yasminx::Error> UnpauseAndSettle(
+    const yasmin::Blackboard& blackboard, const yasminx::StateContext& context,
+    std::function<bool()> is_canceled);
+
 }  // namespace sm
 
 }  // namespace volley::agvhito
```

### include/agvhito/sm/error_state.hpp

```diff
--- a/include/agvhito/sm/error_state.hpp
+++ b/include/agvhito/sm/error_state.hpp
@@ -1,16 +1,21 @@
 #pragma once
 
+#include <optional>
 #include <rclcpp/time.hpp>
 #include <stdx/expected.hpp>
 #include <yasmin/types.hpp>
 #include <yasminx/error.hpp>
 #include <yasminx/lifecycle_state.hpp>
+#include <yasminx/outcome.hpp>
+#include <yasminx/transition.hpp>
 #include <yasminx/state_context.hpp>
 
 namespace volley::agvhito::sm {
 
-/// State that handles errors generated internally from the state machine. Attempts auto recovery if the AGV
-/// is not in a soft or hard e-stop state.
+/// State that attempts software E-stop on entry and records diagnostics while awaiting recovery.
+/// Normal recovery requires fresh state, hardware E-stop clearance, and the recovery delay.
+/// Recovery exit releases software E-stop and verifies observable stop clearance before returning.
+/// Canceled exit does not release the stop; release failure routes to the terminal outcome.
 class ErrorState : public yasminx::LifecycleState {
 public:
   explicit ErrorState(yasminx::StateContext context);
@@ -21,6 +26,15 @@
   [[nodiscard]] stdx::Expected<StepResult, yasminx::ErrorOutcome> Step(
       yasmin::Blackboard::SharedPtr blackboard) override;
 
+  /// Release software E-stop after normal recovery and verify observable stop clearance.
+  /// @p blackboard supplies tracked state and instant-action publication dependencies.
+  /// @p step_outcome must identify recovered completion; canceled exit sends no release.
+  /// @return Recovered after successful release/state verification, canceled when interrupted,
+  /// or an errored result on invalid completion or release failure.
+  [[nodiscard]] stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> OnExit(
+      yasmin::Blackboard::SharedPtr blackboard,
+      std::optional<yasminx::Outcome> step_outcome) override;
+
 private:
   rclcpp::Time entry_stamp_;
 };
```

### include/agvhito/sm/error.hpp

```diff
--- a/include/agvhito/sm/error.hpp
+++ b/include/agvhito/sm/error.hpp
@@ -27,6 +27,8 @@
 inline constexpr auto kErrorSoftEstop {"soft-estop"};
 inline constexpr auto kErrorStateStale {"state-stale"};
 inline constexpr auto kErrorVerifyTimeout {"verify-timeout"};
+/// New-order dispatch encountered an unexpected paused firmware state.
+inline constexpr auto kErrorUnexpectedPause {"unexpected-pause"};
 inline constexpr auto kErrorWrongRequest {"wrong-request"};
 
 inline auto MakeHwEstopError() {
```

### include/agvhito/sm/executing_order_state.hpp

```diff
--- a/include/agvhito/sm/executing_order_state.hpp
+++ b/include/agvhito/sm/executing_order_state.hpp
@@ -11,7 +11,9 @@
 
 namespace volley::agvhito::sm {
 
-/// State that performs order execution including execution status and completion criteria checking.
+/// State that publishes new orders and tracks accepted order execution.
+/// New-order dispatch requires non-stale state with no E-stop or pause; this state does not unpause.
+/// Re-entry from explicit pause or telemetry recovery retains the accepted active order.
 class ExecutingOrderState : public yasminx::LifecycleState {
 public:
   explicit ExecutingOrderState(yasminx::StateContext context);
@@ -23,7 +25,6 @@
       yasmin::Blackboard::SharedPtr blackboard) override;
 
 private:
-  stdx::Expected<void, yasminx::ErrorOutcome> VerifiedUnpause(const yasmin::Blackboard& blackboard);
 
   /// Timestamp of the state message that reported the active order completed. Used to ensure we get a more
   /// recent common message to calculate node accuracy.
```

### include/agvhito/sm/execution_paused_state.hpp

```diff
--- a/include/agvhito/sm/execution_paused_state.hpp
+++ b/include/agvhito/sm/execution_paused_state.hpp
@@ -11,8 +11,9 @@
 
 namespace volley::agvhito::sm {
 
-/// State that holds the AGV in a paused state during order execution, and waits for a resume request to
-/// transition.
+/// State that explicitly pauses order execution and waits for a Resume request.
+/// Normal Resume exit verifies unpause and waits the firmware settling guard before returning resumed.
+/// Canceled exit does not deliberately publish unpause.
 class ExecutionPausedState : public yasminx::LifecycleState {
 public:
   explicit ExecutionPausedState(yasminx::StateContext context);
```

### include/agvhito/sm/execution_recovery_state.hpp

```diff
--- a/include/agvhito/sm/execution_recovery_state.hpp
+++ b/include/agvhito/sm/execution_recovery_state.hpp
@@ -11,7 +11,8 @@
 
 namespace volley::agvhito::sm {
 
-/// State that attempts recovery during execution of an order.
+/// State that waits for fresh state, filtered pose, and common telemetry during order execution.
+/// Does not command pause or unpause, and retains the accepted active order during recovery.
 class ExecutionRecoveryState : public yasminx::LifecycleState {
 public:
   explicit ExecutionRecoveryState(yasminx::StateContext context);
```

### include/agvhito/sm/idle_state.hpp

```diff
--- a/include/agvhito/sm/idle_state.hpp
+++ b/include/agvhito/sm/idle_state.hpp
@@ -8,7 +8,9 @@
 
 namespace volley::agvhito::sm {
 
-/// State that holds the AGV in a paused state, and waits for a assembled order request to transition.
+/// State that waits for a pending order or controlled-stop request without commanding pause.
+/// Cancels unexpected traversal on entry and verifies completion before allowing dispatch.
+/// Does not release software E-stop; existing stop checks retain their error routing.
 class IdleState : public yasminx::LifecycleState {
 public:
   explicit IdleState(yasminx::StateContext context);
```

### include/agvhito/sm/state_strings.hpp

```diff
--- a/include/agvhito/sm/state_strings.hpp
+++ b/include/agvhito/sm/state_strings.hpp
@@ -56,6 +56,8 @@
 };
 
 inline const yasmin::Transitions kErrorTransitions {
+    // Failed recovery release must not enter Stopped or loop through Error again.
+    {kOutcomeErrored, kOutcomeTerminal},
     {kOutcomeRecovered, kStateStopped},
     {yasminx::kOutcomeCanceled, kOutcomeTerminal},
 };
```

### include/agvhito/sm/stopped_state.hpp

```diff
--- a/include/agvhito/sm/stopped_state.hpp
+++ b/include/agvhito/sm/stopped_state.hpp
@@ -8,7 +8,9 @@
 
 namespace volley::agvhito::sm {
 
-/// State that holds the AGV in a soft e-stop state, and waits for an activation request to transition.
+/// State that prevents adapter order dispatch until activation is requested.
+/// Clears queued orders on entry without commanding software E-stop or pause.
+/// The adapter state alone does not establish that physical traversal has stopped.
 class StoppedState : public yasminx::LifecycleState {
 public:
   explicit StoppedState(yasminx::StateContext context);
```

### include/agvhito/sm/timing.hpp

```diff
--- a/include/agvhito/sm/timing.hpp
+++ b/include/agvhito/sm/timing.hpp
@@ -10,4 +10,8 @@
 /// Default period for throttled logging.
 inline constexpr std::chrono::seconds kDefaultLogThrottlePeriod {5};
 
+/// Minimum steady-clock settling period after stopPause is verified FINISHED.
+/// Temporary HITO firmware workaround for SW2-876; this delay does not detect auto_run.
+inline constexpr std::chrono::milliseconds kUnpauseSettlePeriod {200};
+
 }  // namespace volley::agvhito::sm
```

### src/sm/booting_state.cpp

```diff
--- a/src/sm/booting_state.cpp
+++ b/src/sm/booting_state.cpp
@@ -69,27 +69,25 @@
         });
   }
 
-  LOG_INFO(GetLogger(),
-      "Performing booting actions: clearing soft-estop, canceling previous order, setting pause");
+  LOG_INFO(GetLogger(), "Boot preparation: release soft E-stop, cancel order, clear exceptions");
+  // Unpause separately so its completion starts the firmware settling guard.
   const auto boot_actions = VerifiedPublish(
-      {
-          MakeSoftEStopAction(false),
-          MakeCancelOrderAction(),
-          MakeExceptionClearAction(),
-          MakeStopPauseAction(),
-      },
+      {MakeSoftEStopAction(false), MakeCancelOrderAction(), MakeExceptionClearAction()},
       *blackboard, GetContext(), [this] { return is_canceled(); });
   if(!boot_actions.has_value()) {
     return yasminx::MakeUnexpected(kOutcomeErrored, boot_actions.error());
   }
 
-  const auto ready = VerifyState(
-      *blackboard, GetContext(), All({AnyEStopIs(false), PausedIs(false)}), [this] { return is_canceled(); });
-  if(!ready.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, ready.error());
+  // All map publication remains after verified unpause and the full settling guard.
+  const auto unpaused = UnpauseAndSettle(
+      *blackboard, GetContext(), [this] { return is_canceled(); });
+  if(!unpaused.has_value()) {
+    if(unpaused.error().type == kErrorCanceled) {
+      return yasminx::kOutcomeCanceled;
+    }
+    return yasminx::MakeUnexpected(kOutcomeErrored, unpaused.error());
   }
-
-  LOG_INFO(GetLogger(), "AGV is ready to receive bootup map actions");
+  LOG_INFO(GetLogger(), "Unpause guard complete; preparing boot map actions");
 
   state_or = yasminx::bb::Get(*blackboard, bb::kKeyState).value()->GetIfNotStale();
   if(!state_or.has_value()) {
```

### src/sm/context_utils.cpp

```diff
--- a/src/sm/context_utils.cpp
+++ b/src/sm/context_utils.cpp
@@ -4,6 +4,7 @@
 #include <mqtt/results.hpp>
 #include <mqtt/topic_utils.hpp>
 #include <rclcpp/duration.hpp>
+#include <rclcpp/utilities.hpp>
 #include <rclcppx/logging.hpp>
 #include <string>
 #include <utility>
@@ -14,9 +15,11 @@
 
 #include "agvhito/order_assembler.hpp"
 #include "agvhito/sm/blackboard.hpp"
+#include "agvhito/sm/detail/unpause_settle.hpp"
 #include "agvhito/sm/error.hpp"
 #include "agvhito/sm/timing.hpp"
 #include "agvhito/topics/core.hpp"
+#include "agvhito/topics/instant_actions.hpp"
 
 namespace volley::agvhito::sm {
 
@@ -218,4 +221,28 @@
   });
 }
 
+stdx::Expected<void, yasminx::Error> UnpauseAndSettle(
+    const yasmin::Blackboard& blackboard, const yasminx::StateContext& context,
+    std::function<bool()> is_canceled) {
+  const auto interrupted = [&is_canceled] { return is_canceled() || !rclcpp::ok(); };
+
+  // Keep stopPause alone: another batched control action could run before unpause settles.
+  const auto published = VerifiedPublish(
+      {MakeStopPauseAction()}, blackboard, context, interrupted);
+  if(!published.has_value()) {
+    return stdx::Unexpected(published.error());
+  }
+
+  // Start after FINISHED is observed; transport and action execution time do not count.
+  LOG_INFO(context.logger, "Waiting {} for HITO unpause to settle", kUnpauseSettlePeriod);
+  const auto settled = detail::WaitForUnpauseSettle(interrupted);
+  if(!settled.has_value()) {
+    return stdx::Unexpected(settled.error());
+  }
+
+  // Check observable state after the guard; this is not an auto_run readiness signal.
+  return VerifyState(blackboard, context,
+      All({AnyEStopIs(false), PausedIs(false)}), interrupted);
+}
+
 }  // namespace volley::agvhito::sm
```

### src/sm/error_state.cpp

```diff
--- a/src/sm/error_state.cpp
+++ b/src/sm/error_state.cpp
@@ -2,6 +2,7 @@
 
 #include <nlohmann/json.hpp>
 #include <rclcpp/duration.hpp>
+#include <rclcpp/utilities.hpp>
 #include <rclcppx/logging.hpp>
 #include <stdx/expected.hpp>
 #include <utility>
@@ -15,6 +16,7 @@
 
 #include "agvhito/sm/blackboard.hpp"
 #include "agvhito/sm/context_utils.hpp"
+#include "agvhito/sm/error.hpp"
 #include "agvhito/sm/state_strings.hpp"
 #include "agvhito/sm/timing.hpp"
 #include "agvhito/topics/instant_actions.hpp"
@@ -99,4 +101,52 @@
   return yasminx::LifecycleState::Continue {};
 }
 
+stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> ErrorState::OnExit(
+    yasmin::Blackboard::SharedPtr blackboard, std::optional<yasminx::Outcome> step_outcome) {
+  // Exit also runs on cancellation; being called does not authorize release.
+  const auto interrupted = [this] { return is_canceled() || !rclcpp::ok(); };
+  if(interrupted() || step_outcome == yasminx::kOutcomeCanceled) {
+    return yasminx::kOutcomeCanceled;
+  }
+  if(step_outcome != kOutcomeRecovered) {
+    return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
+        .type = kErrorWrongRequest,
+        .message = "Error exit requires normal recovered completion",
+    });
+  }
+
+  // Recheck before release: Step's state observation may have changed.
+  const auto state = yasminx::bb::Get(*blackboard, bb::kKeyState).value()->GetIfNotStale();
+  if(!state.has_value()) {
+    return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
+        .type = kErrorStateStale,
+        .message = "State became stale before software E-stop recovery release",
+    });
+  }
+  if(IsHardEStopped(state.value())) {
+    return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
+        .type = kErrorHwEstop,
+        .message = "Hardware E-stop engaged before software E-stop recovery release",
+    });
+  }
+
+  // Do not report recovery after an unverified software-stop release.
+  const auto released = VerifiedPublish(
+      {MakeSoftEStopAction(false)}, *blackboard, GetContext(), interrupted);
+  if(!released.has_value()) {
+    if(released.error().type == kErrorCanceled) {
+      return yasminx::kOutcomeCanceled;
+    }
+    return yasminx::MakeUnexpected(kOutcomeErrored, released.error());
+  }
+  const auto clear = VerifyState(*blackboard, GetContext(), AnyEStopIs(false), interrupted);
+  if(!clear.has_value()) {
+    if(clear.error().type == kErrorCanceled) {
+      return yasminx::kOutcomeCanceled;
+    }
+    return yasminx::MakeUnexpected(kOutcomeErrored, clear.error());
+  }
+  return kOutcomeRecovered;
+}
+
 }  // namespace volley::agvhito::sm
```

### src/sm/executing_order_state.cpp

```diff
--- a/src/sm/executing_order_state.cpp
+++ b/src/sm/executing_order_state.cpp
@@ -105,15 +105,16 @@
   }
   const vstate::State& state = state_or.value();
 
+  // Boot and explicit Resume own unpause; refuse paused or E-stopped new-order dispatch.
+  if(const auto clear = CheckEStopClear(state); !clear.has_value()) {
+    return stdx::Unexpected(clear.error());
+  }
   if(IsPaused(state)) {
-    LOG_INFO(GetLogger(), "Un-pausing and clearing past exceptions");
-
-    if(const auto unpause = VerifiedUnpause(*blackboard); !unpause.has_value()) {
-      return stdx::Unexpected(unpause.error());
-    }
-  }
-
-  LOG_INFO(GetLogger(), "AGV is reporting un-paused");
+    return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
+        .type = kErrorUnexpectedPause,
+        .message = "New-order entry does not unpause the AGV; boot or explicit Resume must do so",
+    });
+  }
 
   const auto new_order_or = yasminx::bb::Get(*blackboard, bb::kKeyOrderQueue).value()->Front();
   if(!new_order_or.has_value()) {
@@ -286,21 +287,5 @@
   return yasminx::LifecycleState::Continue {};
 }
 
-stdx::Expected<void, yasminx::ErrorOutcome> ExecutingOrderState::VerifiedUnpause(
-    const yasmin::Blackboard& blackboard) {
-  const auto clear_pause = VerifiedPublish({MakeStopPauseAction(), MakeExceptionClearAction()}, blackboard,
-      GetContext(), [this] { return is_canceled(); });
-  if(!clear_pause.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, clear_pause.error());
-  }
-
-  const auto unpaused_verified =
-      VerifyState(blackboard, GetContext(), PausedIs(false), [this] { return is_canceled(); });
-  if(!unpaused_verified.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, unpaused_verified.error());
-  }
-
-  return {};
-}
 
 }  // namespace volley::agvhito::sm
```

### src/sm/execution_paused_state.cpp

```diff
--- a/src/sm/execution_paused_state.cpp
+++ b/src/sm/execution_paused_state.cpp
@@ -1,5 +1,6 @@
 #include "agvhito/sm/execution_paused_state.hpp"
 
+#include <rclcpp/utilities.hpp>
 #include <rclcppx/logging.hpp>
 #include <stdx/expected.hpp>
 #include <utility>
@@ -11,6 +12,7 @@
 
 #include "agvhito/sm/blackboard.hpp"
 #include "agvhito/sm/context_utils.hpp"
+#include "agvhito/sm/error.hpp"
 #include "agvhito/sm/state_strings.hpp"
 #include "agvhito/sm/timing.hpp"
 #include "agvhito/topics/instant_actions.hpp"
@@ -41,21 +43,34 @@
 
   if(bb::TakeRequest(*blackboard) == bb::Request::Resume) {
     LOG_INFO(GetLogger(), "Processed {} request", bb::Request::Resume);
-    return yasminx::LifecycleState::Finished {};
+    // Carry explicit Resume authorization into OnExit.
+    return yasminx::LifecycleState::Finished {.outcome = kOutcomeResumed};
   }
 
   return yasminx::LifecycleState::Continue {};
 }
 
 stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> ExecutionPausedState::OnExit(
-    yasmin::Blackboard::SharedPtr blackboard, std::optional<yasminx::Outcome> /*step_outcome*/) {
-  LOG_INFO(GetLogger(), "Un-pausing AGV to enable order execution");
-  const auto unpause =
-      VerifiedPublish({MakeStopPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
-  if(!unpause.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, unpause.error());
+    yasmin::Blackboard::SharedPtr blackboard, std::optional<yasminx::Outcome> step_outcome) {
+  // Exit also runs on cancellation; being called does not authorize release.
+  if(is_canceled() || !rclcpp::ok() || step_outcome == yasminx::kOutcomeCanceled) {
+    return yasminx::kOutcomeCanceled;
   }
-
+  if(step_outcome != kOutcomeResumed) {
+    return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
+        .type = kErrorWrongRequest,
+        .message = "Paused exit requires explicit Resume completion",
+    });
+  }
+  LOG_INFO(GetLogger(), "Verifying unpause and waiting for the firmware settling guard");
+  const auto unpaused = UnpauseAndSettle(
+      *blackboard, GetContext(), [this] { return is_canceled(); });
+  if(!unpaused.has_value()) {
+    if(unpaused.error().type == kErrorCanceled) {
+      return yasminx::kOutcomeCanceled;
+    }
+    return yasminx::MakeUnexpected(kOutcomeErrored, unpaused.error());
+  }
   return kOutcomeResumed;
 }
 
```

### src/sm/execution_recovery_state.cpp

```diff
--- a/src/sm/execution_recovery_state.cpp
+++ b/src/sm/execution_recovery_state.cpp
@@ -1,5 +1,6 @@
 #include "agvhito/sm/execution_recovery_state.hpp"
 
+#include <rclcpp/utilities.hpp>
 #include <rclcppx/logging.hpp>
 #include <stdx/expected.hpp>
 #include <utility>
@@ -11,10 +12,9 @@
 #include <yasminx/transition.hpp>
 
 #include "agvhito/sm/blackboard.hpp"
-#include "agvhito/sm/context_utils.hpp"
+#include "agvhito/sm/error.hpp"
 #include "agvhito/sm/state_strings.hpp"
 #include "agvhito/sm/timing.hpp"
-#include "agvhito/topics/instant_actions.hpp"
 #include "agvhito/tracked_message.hpp"
 
 namespace volley::agvhito::sm {
@@ -25,16 +25,9 @@
 }
 
 stdx::Expected<void, yasminx::ErrorOutcome> ExecutionRecoveryState::OnEntry(
-    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& /*transition*/) {
-  LOG_WARN(GetLogger(), "Pausing AGV while waiting for stale order data to recover");
-
-  const auto pause =
-      VerifiedPublish({MakeStartPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
-  if(!pause.has_value()) {
-    // If we entered this state we had connectivity issues, instead of erroring we need to continue
-    LOG_WARN(GetLogger(), "Continuing even with pause error, {}", pause.error());
-  }
-
+    yasmin::Blackboard::SharedPtr /*blackboard*/, const yasminx::Transition& /*transition*/) {
+  // Telemetry recovery does not pause; the accepted onboard order may continue.
+  LOG_WARN(GetLogger(), "Waiting for fresh order data without commanding pause");
   return {};
 }
 
@@ -50,7 +43,8 @@
 
   if(state_fresh && filtered_pose_fresh && common_msg_fresh) {
     LOG_INFO(GetLogger(), "Order data (state, filtered pose, and common message) is fresh, exiting recovery");
-    return yasminx::LifecycleState::Finished {};
+    // Carry normal completion into OnExit without publishing or replacing the order.
+    return yasminx::LifecycleState::Finished {.outcome = kOutcomeRecovered};
   }
 
   LOG_WARN_THROTTLE(GetLogger(), GetClock(), kDefaultLogThrottlePeriod,
@@ -60,17 +54,17 @@
 }
 
 stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> ExecutionRecoveryState::OnExit(
-    yasmin::Blackboard::SharedPtr blackboard, std::optional<yasminx::Outcome> /*step_outcome*/) {
-  LOG_INFO(GetLogger(), "Attempting to un-pause the AGV so order execution can continue");
-
-  const auto unpause =
-      VerifiedPublish({MakeStopPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
-  if(!unpause.has_value()) {
-    // During testing, the un-pause instant action was stuck in waiting, since we are un-pausing, we will
-    // allow this to continue
-    LOG_WARN(GetLogger(), "Continuing even with un-pause verification error, {}", unpause.error());
+    yasmin::Blackboard::SharedPtr /*blackboard*/, std::optional<yasminx::Outcome> step_outcome) {
+  if(is_canceled() || !rclcpp::ok() || step_outcome == yasminx::kOutcomeCanceled) {
+    return yasminx::kOutcomeCanceled;
   }
-
+  if(step_outcome != kOutcomeRecovered) {
+    return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
+        .type = kErrorWrongRequest,
+        .message = "Telemetry recovery exit requires recovered completion",
+    });
+  }
+  LOG_INFO(GetLogger(), "Telemetry recovered; continuing the accepted order without unpause");
   return kOutcomeRecovered;
 }
 
```

### src/sm/idle_state.cpp

```diff
--- a/src/sm/idle_state.cpp
+++ b/src/sm/idle_state.cpp
@@ -40,41 +40,20 @@
     return MakeHwEstopError();
   }
 
-  if(IsSoftEStopped(state)) {
-    LOG_INFO(GetLogger(), "Clearing active AGV Soft-EStop");
-
-    const auto clear = VerifiedPublish({MakeSoftEStopAction(false), MakeExceptionClearAction()}, *blackboard,
-        GetContext(), [this] { return is_canceled(); });
-    if(!clear.has_value()) {
-      return yasminx::MakeUnexpected(kOutcomeErrored, clear.error());
-    }
-  }
-
-  LOG_INFO(GetLogger(), "Requesting the AGV to pause");
-
-  const auto pause =
-      VerifiedPublish({MakeStartPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
-  if(!pause.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, pause.error());
-  }
-
-  const auto state_paused =
-      VerifyState(*blackboard, GetContext(), PausedIs(true), [this] { return is_canceled(); });
-  if(!state_paused.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, state_paused.error());
-  }
-
-  LOG_INFO(GetLogger(), "AGV is currently paused");
-
-  // Check if the AGV is still traversing or driving
-  // This corresponds to the AGV having a active order that we need to cancel before we can execute.
+  // Cancel unexpected traversal without pausing; FINISHED alone does not prove motion stopped.
   if(!IsTraversalComplete(state)) {
     const auto cancel_order = VerifiedPublish(
         {MakeCancelOrderAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
     if(!cancel_order.has_value()) {
       return yasminx::MakeUnexpected(kOutcomeErrored, cancel_order.error());
     }
-    LOG_INFO(GetLogger(), "Canceled previously active order '{}'", state.order_id);
+    // Read live state until traversal completes before permitting dispatch.
+    const auto completed = VerifyState(
+        *blackboard, GetContext(), TraversalComplete(), [this] { return is_canceled(); });
+    if(!completed.has_value()) {
+      return yasminx::MakeUnexpected(kOutcomeErrored, completed.error());
+    }
+    LOG_INFO(GetLogger(), "Canceled previous order '{}' and verified traversal complete", state.order_id);
   }
 
   return {};
```

### src/sm/stopped_state.cpp

```diff
--- a/src/sm/stopped_state.cpp
+++ b/src/sm/stopped_state.cpp
@@ -10,10 +10,8 @@
 #include <yasminx/lifecycle_state.hpp>
 
 #include "agvhito/sm/blackboard.hpp"
-#include "agvhito/sm/context_utils.hpp"
 #include "agvhito/sm/state_strings.hpp"
 #include "agvhito/sm/timing.hpp"
-#include "agvhito/topics/instant_actions.hpp"
 #include "agvhito/topics/state.hpp"
 
 namespace volley::agvhito::sm {
@@ -26,16 +24,9 @@
 
 stdx::Expected<void, yasminx::ErrorOutcome> StoppedState::OnEntry(
     yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& /*transition*/) {
-  LOG_INFO(GetLogger(), "Requesting soft-estop as we have entered the state");
-  const auto estop = VerifiedPublish(
-      {MakeSoftEStopAction(true)}, *blackboard, GetContext(), [this] { return is_canceled(); });
-  if(!estop.has_value()) {
-    return yasminx::MakeUnexpected(kOutcomeErrored, estop.error());
-  }
-
+  // Stopped suppresses adapter dispatch without engaging a firmware stop mode.
   LOG_INFO(GetLogger(), "Clearing any queued orders");
   yasminx::bb::Get(*blackboard, bb::kKeyOrderQueue).value()->Clear();
-
   return {};
 }
 
```

### test/topics/test_state_predicates.cpp

```diff
--- a/test/topics/test_state_predicates.cpp
+++ b/test/topics/test_state_predicates.cpp
@@ -104,3 +104,25 @@
   EXPECT_NE(joined.find(paused.description), std::string::npos);
   EXPECT_NE(joined.find(cleared.description), std::string::npos);
 }
+
+TEST(TraversalCompleteTest, CancelFinishedWhileDrivingIsIncomplete) {
+  vstate::State state {};
+  state.driving = true;
+  state.edge_states.emplace_back();
+  vstate::ActionState cancel {};
+  cancel.action_id = "cancel-1";
+  cancel.action_type = "cancelOrder";
+  cancel.action_status = vstate::ActionStatus::FINISHED;
+  state.action_states.push_back(cancel);
+
+  // cancelOrder FINISHED is independent of driving and outstanding traversal.
+  const auto complete = volley::agvhito::TraversalComplete();
+  EXPECT_FALSE(complete.holds(state));
+  state.driving = false;
+  EXPECT_FALSE(complete.holds(state));
+  state.edge_states.clear();
+  state.driving = true;
+  EXPECT_FALSE(complete.holds(state));
+  state.driving = false;
+  EXPECT_TRUE(complete.holds(state));
+}
```

### CMakeLists.txt

```diff
--- a/CMakeLists.txt
+++ b/CMakeLists.txt
@@ -159,14 +159,35 @@
       yaml-cpp
   )
 
+  # Keep the new state-machine tests out of the core test source set.
+  volley_glob_sources(core_test_sources DIRECTORY test EXCLUDE "^test/sm/")
   volley_add_gtest(
     ${PROJECT_NAME}_core_tests
-    DIRECTORY test
+    ${core_test_sources}
     LINK_LIBRARIES
       ${PROJECT_NAME}_core_lib
       ${PROJECT_NAME}_comms_lib
       ${PROJECT_NAME}_topics_lib
   )
+  volley_add_gtest(
+    ${PROJECT_NAME}_state_machine_tests
+    test/sm/test_booting_state.cpp
+    test/sm/test_error_state.cpp
+    test/sm/test_executing_order_state.cpp
+    test/sm/test_execution_paused_state.cpp
+    test/sm/test_execution_recovery_state.cpp
+    test/sm/test_idle_state.cpp
+    test/sm/test_state_machine_policy.cpp
+    test/sm/test_stopped_state.cpp
+    test/sm/test_unpause_and_settle.cpp
+    LINK_LIBRARIES
+      ${PROJECT_NAME}_state_machine_lib
+      ${PROJECT_NAME}_core_lib
+      ${PROJECT_NAME}_comms_lib
+      ${PROJECT_NAME}_topics_lib
+      nlohmann_json::nlohmann_json
+  )
+
   install(FILES test/test_layout.yaml DESTINATION share/${PROJECT_NAME}/test)
 
   volley_add_gtest(
```

### include/agvhito/sm/detail/unpause_settle.hpp

```diff
--- /dev/null
+++ b/include/agvhito/sm/detail/unpause_settle.hpp
@@ -0,0 +1,41 @@
+#pragma once
+
+#include <algorithm>
+#include <chrono>
+#include <functional>
+#include <stdx/expected.hpp>
+#include <thread>
+#include <yasminx/error.hpp>
+
+#include "agvhito/sm/error.hpp"
+#include "agvhito/sm/timing.hpp"
+
+namespace volley::agvhito::sm::detail {
+
+/// Wait at least kUnpauseSettlePeriod using steady time, checking interruption between sleeps.
+/// @p is_canceled includes cancellation and shutdown checks supplied by the caller.
+/// @return Empty when the full interval has elapsed, or a canceled error when interrupted.
+[[nodiscard]] inline stdx::Expected<void, yasminx::Error> WaitForUnpauseSettle(
+    const std::function<bool()>& is_canceled) {
+  using Clock = std::chrono::steady_clock;
+  constexpr auto kCancelPollPeriod = std::chrono::milliseconds {10};
+  const auto deadline = Clock::now() + kUnpauseSettlePeriod;
+  const auto poll_period = std::chrono::duration_cast<Clock::duration>(kCancelPollPeriod);
+
+  while(true) {
+    // Check interruption before success, including after the final sleep.
+    if(is_canceled()) {
+      return stdx::Unexpected(yasminx::Error {
+          .type = kErrorCanceled,
+          .message = "Canceled during the HITO unpause settling period",
+      });
+    }
+    const auto now = Clock::now();
+    if(now >= deadline) {
+      return {};
+    }
+    std::this_thread::sleep_for(std::min(deadline - now, poll_period));
+  }
+}
+
+}  // namespace volley::agvhito::sm::detail
```

### test/sm/test_executing_order_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_executing_order_state.cpp
@@ -0,0 +1,84 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/executing_order_state.hpp"
+#include "agvhito/sm/error.hpp"
+
+namespace volley::agvhito::test {
+using ExecutingTest = StateTest;
+
+TEST_F(ExecutingTest, NewOrderDoesNotUnpauseOrClearExceptions) {
+  ASSERT_TRUE(queue->Push(Order()));
+  sm::ExecutingOrderState executing(context);
+  ASSERT_TRUE(executing.OnEntry(blackboard, From(sm::kStateIdle)).has_value());
+  EXPECT_TRUE(ActionTypes().empty());
+  ASSERT_EQ(publisher->Publications().size(), 1u);
+  EXPECT_TRUE(publisher->Publications().front().payload.contains("orderId"));
+  EXPECT_TRUE(queue->Empty());
+  ASSERT_TRUE(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).has_value());
+  EXPECT_EQ(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).value()->GetOrderId(), "order-1");
+}
+
+TEST_F(ExecutingTest, DifferentMapRetainsMapThenOrderSequence) {
+  ASSERT_TRUE(queue->Push(Order("order-2", "next-floor")));
+  sm::ExecutingOrderState executing(context);
+  ASSERT_TRUE(executing.OnEntry(blackboard, From(sm::kStateIdle)).has_value());
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"enableMap"}));
+  const auto messages = publisher->Publications();
+  ASSERT_EQ(messages.size(), 2u);
+  EXPECT_TRUE(messages.front().payload.contains("actions"));
+  EXPECT_TRUE(messages.back().payload.contains("orderId"));
+}
+
+TEST_F(ExecutingTest, UnexpectedPauseRefusesPublicationAndKeepsQueueAndManager) {
+  state.paused = true;
+  Refresh();
+  ASSERT_TRUE(queue->Push(Order()));
+  vs::ActionState previous {};
+  previous.action_id = "previous";
+  previous.action_status = vs::ActionStatus::FINISHED;
+  manager->Upsert(previous);
+  sm::ExecutingOrderState executing(context);
+  const auto result = executing.OnEntry(blackboard, From(sm::kStateIdle));
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorUnexpectedPause);
+  EXPECT_FALSE(queue->Empty());
+  EXPECT_TRUE(manager->GetActionStatus("previous").has_value());
+  EXPECT_FALSE(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).has_value());
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ExecutingTest, SoftwareStopRefusesNewOrder) {
+  state.safety_state.e_stop = vs::EStop::REMOTE;
+  Refresh();
+  ASSERT_TRUE(queue->Push(Order()));
+  sm::ExecutingOrderState executing(context);
+  const auto result = executing.OnEntry(blackboard, From(sm::kStateIdle));
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().outcome, sm::kOutcomeSoftEstopTriggered);
+  EXPECT_TRUE(publisher->Publications().empty());
+  EXPECT_FALSE(queue->Empty());
+}
+
+TEST_F(ExecutingTest, ReentryRetainsActiveOrderWithoutPublication) {
+  const auto active = std::make_shared<ActiveOrder>(Order());
+  yasminx::bb::Set(*blackboard, bb::kKeyActiveOrder, active);
+  for(const auto from : {sm::kStateExecutionPaused, sm::kStateExecutionRecovery}) {
+    sm::ExecutingOrderState executing(context);
+    ASSERT_TRUE(executing.OnEntry(blackboard, From(from)).has_value());
+    EXPECT_EQ(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).value(), active);
+  }
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ExecutingTest, NextQueuedOrderSelfTransitionDoesNotUnpause) {
+  ASSERT_TRUE(queue->Push(Order("first")));
+  sm::ExecutingOrderState executing(context);
+  ASSERT_TRUE(executing.OnEntry(blackboard, From(sm::kStateIdle)).has_value());
+  ASSERT_TRUE(queue->Push(Order("second")));
+  ASSERT_TRUE(executing.OnEntry(blackboard, From(sm::kStateExecutingOrder)).has_value());
+  EXPECT_TRUE(ActionTypes().empty());
+  EXPECT_EQ(publisher->Publications().size(), 2u);
+  EXPECT_EQ(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).value()->GetOrderId(), "second");
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_unpause_and_settle.cpp

```diff
--- /dev/null
+++ b/test/sm/test_unpause_and_settle.cpp
@@ -0,0 +1,192 @@
+#include "state_test_fixture.hpp"
+
+#include <atomic>
+#include <condition_variable>
+
+#include "agvhito/sm/context_utils.hpp"
+#include "agvhito/sm/detail/unpause_settle.hpp"
+#include "agvhito/sm/error.hpp"
+#include "agvhito/sm/timing.hpp"
+#include "../time_utils.hpp"
+
+namespace volley::agvhito::test {
+using namespace sm;
+using UnpauseTest = StateTest;
+
+TEST(UnpauseWaitTest, FullSteadyClockInterval) {
+  const auto before = SteadyClock::now();
+  const auto result = sm::detail::WaitForUnpauseSettle([] { return false; });
+  const auto after = SteadyClock::now();
+  ASSERT_TRUE(result.has_value());
+  EXPECT_GE(after - before, kUnpauseSettlePeriod);
+}
+
+TEST(UnpauseWaitTest, CancellationDuringGuard) {
+  std::atomic<bool> canceled {false};
+  std::promise<void> entered;
+  bool signaled = false;
+  // The callback is invoked from within the production wait, after the deadline is created.
+  auto worker = std::async(std::launch::async, [&] {
+    return sm::detail::WaitForUnpauseSettle([&] {
+      if(!signaled) {
+        signaled = true;
+        entered.set_value();
+      }
+      return canceled.load();
+    });
+  });
+  entered.get_future().wait();
+  canceled.store(true);
+  const auto result = worker.get();
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorCanceled);
+}
+
+TEST_F(UnpauseTest, EarlyFinishedBlocksFollowOnControl) {
+  enforce_readiness = true;
+  // Model FINISHED preceding readiness; the follow-on command is timestamped at publication.
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  ASSERT_TRUE(result.has_value());
+  const auto next = VerifiedPublish(
+      {MakeEnableMapAction("floor", kHitoMapVersion)}, *blackboard, context, [] { return false; });
+  ASSERT_TRUE(next.has_value());
+  const auto messages = publisher->Publications();
+  ASSERT_EQ(messages.size(), 2u);
+  ASSERT_EQ(messages.front().payload.at("actions").size(), 1u);
+  EXPECT_EQ(messages.front().payload.at("actions").front().at("actionType"), "stopPause");
+  const auto observed = FinishedAt();
+  EXPECT_GE(messages.back().stamp - observed, kUnpauseSettlePeriod);
+  // A firmware acceptance window of 105 ms must also be cleared by the stronger 200 ms guard.
+  EXPECT_GE(messages.back().stamp, observed + 105ms);
+}
+
+TEST_F(UnpauseTest, SlowFinishedDoesNotConsumeGuard) {
+  stop_delay = 300ms;
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  const auto returned = SteadyClock::now();
+  ASSERT_TRUE(result.has_value());
+  EXPECT_GE(returned - FinishedAt(), kUnpauseSettlePeriod);
+  EXPECT_GE(returned - publisher->Publications().front().stamp, 500ms);
+}
+
+TEST(UnpauseWaitTest, RosClockJumpDoesNotShortenSteadyInterval) {
+  const auto ros_clock = MakeClock(rclcpp::Time(1, 0, kForceRosTime));
+  ASSERT_TRUE(ros_clock.has_value());
+  bool jumped = false;
+  bool time_update_succeeded = false;
+  const auto before = SteadyClock::now();
+  const auto result = sm::detail::WaitForUnpauseSettle([&] {
+    if(!jumped) {
+      jumped = true;
+      // A large ROS-time jump has no effect on the production wait's steady deadline.
+      time_update_succeeded = SetNow(ros_clock.value(), rclcpp::Time(1000, 0, kForceRosTime)).has_value();
+    }
+    return false;
+  });
+  const auto after = SteadyClock::now();
+  ASSERT_TRUE(time_update_succeeded);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_GE(after - before, sm::kUnpauseSettlePeriod);
+}
+
+TEST_F(UnpauseTest, ShutdownDuringGuardReturnsCanceled) {
+  std::promise<void> entered;
+  bool signaled = false;
+  auto worker = std::async(std::launch::async, [&] {
+    return sm::detail::WaitForUnpauseSettle([&] {
+      if(!signaled) {
+        signaled = true;
+        entered.set_value();
+      }
+      return !rclcpp::ok();
+    });
+  });
+  entered.get_future().wait();
+  rclcpp::shutdown();
+  const auto result = worker.get();
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, sm::kErrorCanceled);
+}
+
+TEST_F(UnpauseTest, FinalStateCheckBlocksSuccessWhileStale) {
+  apply_state_changes = false;
+  auto empty = std::make_shared<TrackedMessage<vs::State>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+  yasminx::bb::Set(*blackboard, bb::kKeyState, empty);
+  const auto started = SteadyClock::now();
+  const auto result = UnpauseAndSettle(*blackboard, context, [&] {
+    return SteadyClock::now() - started >= 500ms;
+  });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, sm::kErrorCanceled);
+}
+
+TEST_F(UnpauseTest, CanceledBeforePublishSendsNothing) {
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return true; });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(UnpauseTest, FailedActionPreservesError) {
+  fail_action = "stopPause";
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorActionStatusFailed);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"stopPause"}));
+}
+
+TEST_F(UnpauseTest, TransportFailurePreservesError) {
+  publisher->mode = RecordingPublisher::Mode::Error;
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorMqttPublishFailed);
+}
+
+TEST_F(UnpauseTest, TransportTimeoutPreservesError) {
+  publisher->mode = RecordingPublisher::Mode::Timeout;
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorMqttPublishTimeout);
+}
+
+TEST_F(UnpauseTest, ActionVerificationTimeoutPreservesError) {
+  // Intentionally exercises the existing real 35 s verification timeout, without a new clock seam.
+  hold_action = "stopPause";
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorVerifyTimeout);
+}
+
+TEST_F(UnpauseTest, FinalStateCheckBlocksSuccessWhilePaused) {
+  apply_state_changes = false;
+  state.paused = true;
+  Refresh();
+  const auto started = SteadyClock::now();
+  const auto result = UnpauseAndSettle(*blackboard, context, [&] {
+    return SteadyClock::now() - started >= 500ms;
+  });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorCanceled);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"stopPause"}));
+}
+
+TEST_F(UnpauseTest, FinalStateCheckBlocksSuccessWhileEStopped) {
+  state.safety_state.e_stop = vs::EStop::REMOTE;
+  Refresh();
+  const auto started = SteadyClock::now();
+  const auto result = UnpauseAndSettle(*blackboard, context, [&] {
+    return SteadyClock::now() - started >= 500ms;
+  });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorCanceled);
+}
+
+TEST_F(UnpauseTest, ShutdownBeforePublishSendsNothing) {
+  rclcpp::shutdown();
+  const auto result = UnpauseAndSettle(*blackboard, context, [] { return false; });
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().type, kErrorCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_error_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_error_state.cpp
@@ -0,0 +1,165 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/error_state.hpp"
+#include "agvhito/sm/stopped_state.hpp"
+#include "agvhito/sm/idle_state.hpp"
+#include "agvhito/sm/error.hpp"
+
+namespace volley::agvhito::test {
+using ErrorTest = StateTest;
+
+TEST_F(ErrorTest, EntryStillActivatesSoftwareStopAndClearsQueue) {
+  ASSERT_TRUE(queue->Push(Order()));
+  sm::ErrorState error(context);
+  ASSERT_TRUE(error.OnEntry(blackboard, {}).has_value());
+  EXPECT_TRUE(queue->Empty());
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"eStop"}));
+  const auto message = publisher->Publications().front();
+  EXPECT_EQ(message.payload.at("actions").front().at("actionParameters").front().at("value"), "true");
+}
+
+TEST_F(ErrorTest, EntryActivationVerificationFailureRemainsTolerated) {
+  fail_action = "eStop";
+  ASSERT_TRUE(queue->Push(Order()));
+  sm::ErrorState error(context);
+  EXPECT_TRUE(error.OnEntry(blackboard, {}).has_value());
+  EXPECT_TRUE(queue->Empty());
+}
+
+TEST_F(ErrorTest, RecoveredExitReleasesAndStoppedIdleDoNotReactivate) {
+  state.safety_state.e_stop = vs::EStop::REMOTE;
+  Refresh();
+  sm::ErrorState error(context);
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), sm::kOutcomeRecovered);
+  const auto message = publisher->Publications().front();
+  EXPECT_EQ(message.payload.at("actions").front().at("actionParameters").front().at("value"), "false");
+  sm::StoppedState stopped(context);
+  ASSERT_TRUE(stopped.OnEntry(blackboard, {}).has_value());
+  sm::IdleState idle(context);
+  ASSERT_TRUE(idle.OnEntry(blackboard, {}).has_value());
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"eStop"}));
+}
+
+TEST_F(ErrorTest, CanceledAndInvalidExitSendNoRelease) {
+  sm::ErrorState error(context);
+  const auto canceled = error.OnExit(blackboard, yasminx::kOutcomeCanceled);
+  ASSERT_TRUE(canceled.has_value());
+  EXPECT_EQ(canceled.value(), yasminx::kOutcomeCanceled);
+  const auto invalid = error.OnExit(blackboard, std::nullopt);
+  ASSERT_FALSE(invalid.has_value());
+  EXPECT_EQ(invalid.error().error.type, sm::kErrorWrongRequest);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ErrorTest, HardwareStopBeforeReleaseSendsNothing) {
+  state.safety_state.e_stop = vs::EStop::MANUAL;
+  Refresh();
+  sm::ErrorState error(context);
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorHwEstop);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ErrorTest, StaleStateBeforeReleaseSendsNothing) {
+  auto empty = std::make_shared<TrackedMessage<vs::State>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+  yasminx::bb::Set(*blackboard, bb::kKeyState, empty);
+  sm::ErrorState error(context);
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorStateStale);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ErrorTest, ReleaseFailureRoutesToTerminalInsteadOfRecovered) {
+  fail_action = "eStop";
+  sm::ErrorState error(context);
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorActionStatusFailed);
+  EXPECT_EQ(result.error().outcome, sm::kOutcomeErrored);
+  EXPECT_EQ(sm::kErrorTransitions.at(result.error().outcome), sm::kOutcomeTerminal);
+}
+
+TEST_F(ErrorTest, TransportFailureDoesNotRecover) {
+  publisher->mode = RecordingPublisher::Mode::Error;
+  sm::ErrorState error(context);
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorMqttPublishFailed);
+  EXPECT_EQ(sm::kErrorTransitions.at(result.error().outcome), sm::kOutcomeTerminal);
+}
+
+TEST_F(ErrorTest, HardwareStopAndRecoveryDelayStillGateStep) {
+  sm::ErrorState error(context);
+  ASSERT_TRUE(error.OnEntry(blackboard, {}).has_value());
+  const auto immediate = error.Step(blackboard);
+  ASSERT_TRUE(immediate.has_value());
+  EXPECT_TRUE(IsContinuing(immediate.value()));
+  state.safety_state.e_stop = vs::EStop::MANUAL;
+  Refresh();
+  std::this_thread::sleep_for(5100ms);
+  const auto hard_stopped = error.Step(blackboard);
+  ASSERT_TRUE(hard_stopped.has_value());
+  EXPECT_TRUE(IsContinuing(hard_stopped.value()));
+  state.safety_state.e_stop = vs::EStop::REMOTE;
+  Refresh();
+  const auto ready = error.Step(blackboard);
+  ASSERT_TRUE(ready.has_value());
+  const auto done = FinishedOutcome(ready.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeRecovered);
+  // Software stop is still engaged here: Step must reach the release hook despite it.
+}
+
+TEST_F(ErrorTest, LifecycleNormalRecoveryActivatesThenReleases) {
+  sm::ErrorState error(context);
+  const auto outcome = RunLifecycle(error, blackboard, {});
+  EXPECT_EQ(outcome, sm::kOutcomeRecovered);
+  const auto messages = publisher->Publications();
+  ASSERT_EQ(messages.size(), 2u);
+  EXPECT_EQ(messages[0].payload.at("actions").front().at("actionParameters").front().at("value"), "true");
+  EXPECT_EQ(messages[1].payload.at("actions").front().at("actionParameters").front().at("value"), "false");
+}
+
+TEST_F(ErrorTest, CanceledFlagOverridesRecoveredAuthorization) {
+  sm::ErrorState error(context);
+  error.cancel_state();
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ErrorTest, ShutdownExitDoesNotReleaseStop) {
+  sm::ErrorState error(context);
+  rclcpp::shutdown();
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(ErrorTest, FinishedReleaseWithStopStillReportedCannotRecover) {
+  state.safety_state.e_stop = vs::EStop::REMOTE;
+  Refresh();
+  apply_state_changes = false;
+  sm::ErrorState error(context);
+  // Stop the long verification deterministically after the release publication has occurred.
+  publisher->respond = [this, &error](const auto& payload) {
+    Respond(payload);
+    workers.emplace_back([&error] {
+      std::this_thread::sleep_for(300ms);
+      error.cancel_state();
+    });
+  };
+  const auto result = error.OnExit(blackboard, sm::kOutcomeRecovered);
+  workers.clear();  // Join before the local state object leaves scope.
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_EQ(publisher->Publications().size(), 1u);
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_booting_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_booting_state.cpp
@@ -0,0 +1,74 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/booting_state.hpp"
+#include "agvhito/sm/error.hpp"
+#include "agvhito/sm/timing.hpp"
+
+namespace volley::agvhito::test {
+using BootTest = StateTest;
+
+TEST_F(BootTest, UnpauseSeparateFromPreparationAndMapsAfterGuard) {
+  sm::BootingState boot(context);
+  const auto result = boot.Execute(blackboard, {});
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), sm::kOutcomeBooted);
+  const auto messages = publisher->Publications();
+  ASSERT_EQ(messages.size(), 3u);
+  EXPECT_EQ(messages[0].payload.at("actions").size(), 3u);
+  ASSERT_EQ(messages[1].payload.at("actions").size(), 1u);
+  EXPECT_EQ(messages[1].payload.at("actions").front().at("actionType"), "stopPause");
+  EXPECT_GE(messages[2].stamp - FinishedAt(), sm::kUnpauseSettlePeriod);
+  const auto types = ActionTypes();
+  ASSERT_GE(types.size(), 5u);
+  EXPECT_EQ(types[0], "eStop");
+  EXPECT_EQ(types[1], "cancelOrder");
+  EXPECT_EQ(types[2], "exceptionClear");
+  EXPECT_EQ(types[3], "stopPause");
+}
+
+TEST_F(BootTest, PreparationFailurePreventsUnpauseAndMaps) {
+  fail_action = "cancelOrder";
+  sm::BootingState boot(context);
+  const auto result = boot.Execute(blackboard, {});
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorActionStatusFailed);
+  ASSERT_EQ(publisher->Publications().size(), 1u);
+  EXPECT_EQ(ActionTypes().size(), 3u);
+}
+
+TEST_F(BootTest, FailedUnpausePreventsMaps) {
+  fail_action = "stopPause";
+  sm::BootingState boot(context);
+  const auto result = boot.Execute(blackboard, {});
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().outcome, sm::kOutcomeErrored);
+  EXPECT_EQ(publisher->Publications().size(), 2u);
+}
+
+TEST_F(BootTest, CancellationAfterUnpausePreventsMaps) {
+  sm::BootingState boot(context);
+  publisher->respond = [this, &boot](const auto& payload) {
+    Respond(payload);
+    if(payload.contains("actions") && payload.at("actions").size() == 1u &&
+        payload.at("actions").front().at("actionType") == "stopPause") {
+      boot.cancel_state();
+    }
+  };
+  const auto result = boot.Execute(blackboard, {});
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_EQ(publisher->Publications().size(), 2u);
+}
+
+TEST_F(BootTest, ExistingLocalizationMapDoesNotDownloadItAgain) {
+  SetEnabledMap("localization");
+  Refresh();
+  sm::BootingState boot(context);
+  ASSERT_TRUE(boot.Execute(blackboard, {}).has_value());
+  const auto messages = publisher->Publications();
+  ASSERT_EQ(messages.size(), 3u);
+  ASSERT_EQ(messages.back().payload.at("actions").size(), 1u);
+  EXPECT_EQ(messages.back().payload.at("actions").front().at("actionType"), "enableMap");
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/state_test_fixture.hpp

```diff
--- /dev/null
+++ b/test/sm/state_test_fixture.hpp
@@ -0,0 +1,361 @@
+#pragma once
+
+#include <gtest/gtest.h>
+
+#include <chrono>
+#include <algorithm>
+#include <functional>
+#include <future>
+#include <memory>
+#include <mutex>
+#include <nlohmann/json.hpp>
+#include <optional>
+#include <rclcpp/clock.hpp>
+#include <rclcpp/logger.hpp>
+#include <rclcpp/utilities.hpp>
+#include <stdexcept>
+#include <string>
+#include <thread>
+#include <utility>
+#include <variant>
+#include <vector>
+#include <yasmin/blackboard.hpp>
+#include <yasminx/blackboard_constants.hpp>
+#include <yasminx/blackboard_utils.hpp>
+#include <yasminx/lifecycle_state.hpp>
+#include <yasminx/state_context.hpp>
+#include <yasminx/transition.hpp>
+
+#include "agvhito/active_order.hpp"
+#include "agvhito/comms/sim_mqtt_client.hpp"
+#include "agvhito/pose_filter.hpp"
+#include "agvhito/sm/blackboard.hpp"
+#include "agvhito/sm/state_strings.hpp"
+#include "agvhito/topics/core.hpp"
+#include "agvhito/topics/instant_actions.hpp"
+#include "agvhito/topics/state.hpp"
+
+namespace volley::agvhito::test {
+
+namespace vi = vda5050_interfaces::v2::instant_actions;
+namespace vs = vda5050_interfaces::v2::state;
+namespace vo = vda5050_interfaces::v2::order;
+namespace hc = vda5050_interfaces::hitov2::common_message;
+using SteadyClock = std::chrono::steady_clock;
+using namespace std::chrono_literals;
+
+/// Inspect a Step result without naming LifecycleState's protected variant alternatives.
+/// @return True for Continue, false for a Finished alternative carrying an outcome member.
+template <typename StepResultT>
+bool IsContinuing(const StepResultT& result) {
+  return std::visit([](const auto& value) {
+    return !requires { value.outcome; };
+  }, result);
+}
+
+/// Inspect completion without naming LifecycleState's protected Finished type.
+/// @return The optional finished outcome, or nullopt for Continue.
+template <typename StepResultT>
+std::optional<yasminx::Outcome> FinishedOutcome(const StepResultT& result) {
+  return std::visit([](const auto& value) -> std::optional<yasminx::Outcome> {
+    if constexpr(requires { value.outcome; }) {
+      return value.outcome;
+    }
+    return std::nullopt;
+  }, result);
+}
+
+/// Execute through the public callable state interface, preserving framework outcome handling.
+/// @p transition is installed as the entry transition read by yasminx::State's wrapper.
+/// @return The routed outcome, including errors/cancellation handled by the framework wrapper.
+template <typename StateT>
+yasminx::Outcome RunLifecycle(StateT& state, const yasmin::Blackboard::SharedPtr& blackboard,
+    const yasminx::Transition& transition) {
+  yasminx::bb::Set(*blackboard, yasminx::bb::kTransition, transition);
+  return state(blackboard);
+}
+
+struct Publication {
+  SteadyClock::time_point stamp;
+  std::string topic;
+  nlohmann::json payload;
+};
+
+/// Records real messages, with optional deterministic transport error/timeout injection.
+class RecordingPublisher final : public mqtt::IPublisher {
+public:
+  enum class Mode { Normal, Error, Timeout };
+
+  explicit RecordingPublisher(mqtt::IPublisherUPtr delegate) : delegate_(std::move(delegate)) {}
+
+  std::future<mqtt::PublishResult> Publish(mqtt::Message message) override {
+    const auto stamp = SteadyClock::now();
+    const auto payload = nlohmann::json::parse(message.payload.begin(), message.payload.end());
+    if(accept && !accept(stamp, payload)) {
+      std::promise<mqtt::PublishResult> promise;
+      promise.set_value(mqtt::PublishResult::Error);
+      return promise.get_future();
+    }
+    {
+      const std::lock_guard lock(mutex_);
+      publications_.push_back({stamp, message.topic, payload});
+    }
+    if(mode == Mode::Timeout) {
+      // Retain the promise so the future stays pending rather than becoming broken.
+      pending_.push_back(std::make_shared<std::promise<mqtt::PublishResult>>());
+      return pending_.back()->get_future();
+    }
+    if(mode == Mode::Error) {
+      std::promise<mqtt::PublishResult> promise;
+      promise.set_value(mqtt::PublishResult::Error);
+      return promise.get_future();
+    }
+    auto result = delegate_->Publish(std::move(message));
+    if(respond) {
+      respond(payload);
+    }
+    return result;
+  }
+
+  mqtt::PublishResult PublishWait(mqtt::Message message) override {
+    return Publish(std::move(message)).get();
+  }
+
+  std::vector<Publication> Publications() const {
+    const std::lock_guard lock(mutex_);
+    return publications_;
+  }
+
+  Mode mode {Mode::Normal};
+  std::function<bool(SteadyClock::time_point, const nlohmann::json&)> accept;
+  std::function<void(const nlohmann::json&)> respond;
+
+private:
+  mqtt::IPublisherUPtr delegate_;
+  mutable std::mutex mutex_;
+  std::vector<Publication> publications_;
+  std::vector<std::shared_ptr<std::promise<mqtt::PublishResult>>> pending_;
+};
+
+/// Supplies actual assembler/manager/tracker dependencies and synchronous firmware responses.
+/// Delayed responses use owned jthreads joined before any blackboard objects are destroyed.
+class StateTest : public testing::Test {
+protected:
+  void SetUp() override {
+    if(!rclcpp::ok()) {
+      int argc = 0;
+      rclcpp::init(argc, nullptr);
+      owns_ros_ = true;
+    }
+    clock = std::make_shared<rclcpp::Clock>(RCL_SYSTEM_TIME);
+    context = {.clock = clock, .logger = rclcpp::get_logger("sw2_876_test")};
+    blackboard = std::make_shared<yasmin::Blackboard>();
+    manager = std::make_shared<ActionStateManager>();
+    queue = std::make_shared<OrderQueue>();
+    pose = std::make_shared<PoseFilter>(clock);
+    tracked = std::make_shared<TrackedMessage<vs::State>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+    common = std::make_shared<TrackedMessage<hc::CommonMessage>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+    publisher = std::make_shared<RecordingPublisher>(client.CreatePublisher());
+    // Subscribe before any operation; the responder consumes actual encoded messages.
+    instant_sub = client.CreateSubscription(vi::GetTopic(kHitoManufacturer, "+"), {});
+    order_sub = client.CreateSubscription(vo::GetTopic(kHitoManufacturer, "+"), {});
+    publisher->respond = [this](const auto& payload) { Respond(payload); };
+    publisher->accept = [this](const auto stamp, const auto& payload) {
+      if(!enforce_readiness) {
+        return true;
+      }
+      const std::lock_guard lock(stamp_mutex);
+      if(!stop_finished_at.has_value()) {
+        return true;
+      }
+      // The test firmware rejects subsequent control inside its modeled readiness window.
+      const bool is_order = payload.contains("orderId");
+      const bool is_map = payload.contains("actions") && std::any_of(
+          payload.at("actions").begin(), payload.at("actions").end(), [](const auto& action) {
+            const auto type = action.at("actionType").template get<std::string>();
+            return type == "enableMap" || type == "downloadMap" || type == "deleteMap";
+          });
+      return !(is_order || is_map) || stamp >= stop_finished_at.value() + 105ms;
+    };
+
+    yasminx::bb::Set(*blackboard, bb::kKeyActionStateManager, manager);
+    yasminx::bb::Set(*blackboard, bb::kKeyOrderQueue, queue);
+    yasminx::bb::Set(*blackboard, bb::kKeyPoseFilter, pose);
+    yasminx::bb::Set(*blackboard, bb::kKeyState, tracked);
+    yasminx::bb::Set(*blackboard, bb::kKeyCommonMessage, common);
+    yasminx::bb::Set(*blackboard, bb::kKeyInstantAssembler,
+        std::make_shared<InstantActionAssembler>(AgvId {1}, clock));
+    yasminx::bb::Set(*blackboard, bb::kKeyMqttPublisher, mqtt::IPublisherSPtr {publisher});
+    yasminx::bb::Set(*blackboard, bb::kKeyLocalizationMapId, std::string {"localization"});
+    yasminx::bb::Set(*blackboard, bb::kKeyFloorMapIds, FloorMapIds {});
+    state.safety_state.e_stop = vs::EStop::NONE;
+    state.paused = false;
+    state.driving = false;
+    state.last_node_id = "1";
+    state.agv_position = vs::AgvPosition {};
+    state.agv_position->position_initialized = true;
+    state.agv_position->x = 1.0;
+    state.agv_position->y = 1.0;
+    SetEnabledMap("floor");
+    Refresh();
+    RefreshCommon();
+    ASSERT_TRUE(pose->Set(clock->now(), 0, 0, 0));
+  }
+
+  void TearDown() override {
+    workers.clear();  // jthread destruction joins, including after a fatal assertion.
+    if(owns_ros_) {
+      rclcpp::shutdown();
+    }
+  }
+
+  void Refresh() {
+    state.timestamp = ToIso8601(clock->now());
+    tracked->Set(state);
+  }
+
+  void RefreshCommon() {
+    hc::CommonMessage message {};
+    message.timestamp = ToIso8601(clock->now());
+    common->Set(message);
+  }
+
+  void SetEnabledMap(const std::string& id) {
+    vs::Map map {};
+    map.map_id = id;
+    map.map_version = kHitoMapVersion;
+    map.map_status = vs::MapStatus::ENABLED;
+    state.maps = std::vector<vs::Map> {map};
+  }
+
+  AssembledOrder Order(const std::string& id = "order-1", const std::string& map = "floor") {
+    AssembledOrder order {};
+    order.map_id = map;
+    order.order.order_id = id;
+    order.order.serial_number = "test-1";
+    order.order.manufacturer = kHitoManufacturer;
+    order.order.version = kHitoProtocolVersion;
+    // An empty command collection is sufficient for entry/publication tests; no motion is processed.
+    return order;
+  }
+
+  yasminx::Transition From(const std::string& name) {
+    yasminx::Transition transition {};
+    transition.from_state = name;
+    return transition;
+  }
+
+  void Respond(const nlohmann::json& payload) {
+    if(payload.contains("actions")) {
+      const auto received = instant_sub->TryReceive();
+      if(!received.has_value()) {
+        throw std::runtime_error("SimMqttClient did not route the instant-action message");
+      }
+      const auto decoded = nlohmann::json::parse(received->payload.begin(), received->payload.end()).get<vi::InstantActions>();
+      for(const auto& action : decoded.actions) {
+        if(action.action_type == "stopPause" && stop_delay > 0ms) {
+          workers.emplace_back([this, action] {
+            std::this_thread::sleep_for(stop_delay);
+            Complete(action);
+          });
+        }
+        else {
+          Complete(action);
+        }
+      }
+    }
+    else if(payload.contains("orderId")) {
+      const auto received = order_sub->TryReceive();
+      if(!received.has_value()) {
+        throw std::runtime_error("SimMqttClient did not route the order message");
+      }
+      state.order_id = payload.at("orderId").get<std::string>();
+      Refresh();
+    }
+  }
+
+  void Complete(const vi::Action& action) {
+    const bool failed = action.action_type == fail_action;
+    if(!failed && apply_state_changes) {
+      if(action.action_type == "stopPause") {
+        state.paused = false;
+      }
+      if(action.action_type == "startPause") {
+        state.paused = true;
+      }
+      if(action.action_type == "eStop") {
+        const auto enabled = nlohmann::json(action).at("actionParameters").at(0).at("value").get<std::string>();
+        state.safety_state.e_stop = enabled == "true" ? vs::EStop::REMOTE : vs::EStop::NONE;
+      }
+      if(action.action_type == "cancelOrder" && complete_cancel_motion) {
+        state.driving = false;
+        state.node_states.clear();
+        state.edge_states.clear();
+      }
+      if(action.action_type == "enableMap") {
+        const auto id = nlohmann::json(action).at("actionParameters").at(0).at("value").get<std::string>();
+        SetEnabledMap(id);
+      }
+      Refresh();
+    }
+    if(action.action_type == "stopPause") {
+      // Record before exposing FINISHED so polling cannot shorten the measured lower bound.
+      const std::lock_guard lock(stamp_mutex);
+      stop_finished_at = SteadyClock::now();
+    }
+    if(action.action_type != hold_action) {
+      vs::ActionState status {};
+      status.action_id = action.action_id;
+      status.action_type = action.action_type;
+      status.action_status = failed ? vs::ActionStatus::FAILED : vs::ActionStatus::FINISHED;
+      manager->Upsert(status);
+    }
+  }
+
+  std::vector<std::string> ActionTypes() {
+    std::vector<std::string> types;
+    for(const auto& message : publisher->Publications()) {
+      if(message.payload.contains("actions")) {
+        for(const auto& action : message.payload.at("actions")) {
+          types.push_back(action.at("actionType").get<std::string>());
+        }
+      }
+    }
+    return types;
+  }
+
+  SteadyClock::time_point FinishedAt() {
+    const std::lock_guard lock(stamp_mutex);
+    return stop_finished_at.value();
+  }
+
+  // State writes are serialized by each test: at most one delayed responder is active.
+  // The tracked state and action manager provide synchronized reads to the operation worker.
+  comms::SimMqttClient client;
+  rclcpp::Clock::SharedPtr clock;
+  yasminx::StateContext context {.clock = {}, .logger = rclcpp::get_logger("sw2_876_test")};
+  yasmin::Blackboard::SharedPtr blackboard;
+  ActionStateManagerSPtr manager;
+  OrderQueueSPtr queue;
+  PoseFilterSPtr pose;
+  TrackedMessageSPtr<vs::State> tracked;
+  TrackedMessageSPtr<hc::CommonMessage> common;
+  std::shared_ptr<RecordingPublisher> publisher;
+  mqtt::ISubscriptionSPtr instant_sub;
+  mqtt::ISubscriptionSPtr order_sub;
+  vs::State state {};
+  bool apply_state_changes {true};
+  bool enforce_readiness {false};
+  bool complete_cancel_motion {true};
+  std::string fail_action;
+  std::string hold_action;
+  std::chrono::milliseconds stop_delay {0};
+  std::vector<std::jthread> workers;
+  std::mutex stamp_mutex;
+  std::optional<SteadyClock::time_point> stop_finished_at;
+
+private:
+  bool owns_ros_ {false};
+};
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_stopped_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_stopped_state.cpp
@@ -0,0 +1,38 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/stopped_state.hpp"
+
+namespace volley::agvhito::test {
+using StoppedTest = StateTest;
+
+TEST_F(StoppedTest, EntryClearsQueueWithoutActions) {
+  ASSERT_TRUE(queue->Push(Order()));
+  sm::StoppedState stopped(context);
+  ASSERT_TRUE(stopped.OnEntry(blackboard, {}).has_value());
+  EXPECT_TRUE(queue->Empty());
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(StoppedTest, ActivatePreservesOutcomeWithoutActions) {
+  sm::StoppedState stopped(context);
+  yasminx::bb::Set(*blackboard, bb::kKeyRequest, bb::Request::Activate);
+  const auto result = stopped.Step(blackboard);
+  ASSERT_TRUE(result.has_value());
+  const auto done = FinishedOutcome(result.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeActivateRequested);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(StoppedTest, LostLocalizationPreservesOutcome) {
+  state.agv_position.reset();
+  Refresh();
+  sm::StoppedState stopped(context);
+  const auto result = stopped.Step(blackboard);
+  ASSERT_TRUE(result.has_value());
+  const auto done = FinishedOutcome(result.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeNotLocalized);
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_state_machine_policy.cpp

```diff
--- /dev/null
+++ b/test/sm/test_state_machine_policy.cpp
@@ -0,0 +1,65 @@
+#include "state_test_fixture.hpp"
+
+#include <yasminx/root_state_machine.hpp>
+#include <yasminx/state.hpp>
+
+#include "agvhito/sm/error_state.hpp"
+#include "agvhito/sm/stopped_state.hpp"
+#include "agvhito/sm/idle_state.hpp"
+
+namespace volley::agvhito::test {
+
+namespace {
+constexpr auto kVisitedStopped = "visited-stopped";
+
+/// Finite integration probe: exercise real Stopped entry, then terminate the test graph.
+class StoppedProbe final : public yasminx::State {
+public:
+  explicit StoppedProbe(yasminx::StateContext context) :
+      yasminx::State(yasmin::Outcomes {kVisitedStopped}, context), stopped_(context) {}
+
+  stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> Execute(
+      yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& transition) override {
+    const auto entry = stopped_.OnEntry(blackboard, transition);
+    if(!entry.has_value()) {
+      return stdx::Unexpected(entry.error());
+    }
+    return kVisitedStopped;
+  }
+
+private:
+  sm::StoppedState stopped_;
+};
+}  // namespace
+
+using PolicyTest = StateTest;
+
+TEST_F(PolicyTest, RootSuccessfulErrorExitReachesStoppedWithoutReactivation) {
+  yasminx::RootStateMachine root("policy-test",
+      yasmin::Outcomes {sm::kOutcomeTerminal, kVisitedStopped}, context);
+  root.add_state(sm::kStateError, std::make_shared<sm::ErrorState>(context), sm::kErrorTransitions);
+  root.add_state(sm::kStateStopped, std::make_shared<StoppedProbe>(context),
+      yasmin::Transitions {{kVisitedStopped, kVisitedStopped}});
+  const auto outcome = root(blackboard);
+  EXPECT_EQ(outcome, kVisitedStopped);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"eStop", "eStop"}));
+  sm::IdleState idle(context);
+  ASSERT_TRUE(idle.OnEntry(blackboard, {}).has_value());
+  EXPECT_EQ(publisher->Publications().size(), 2u);
+}
+
+TEST_F(PolicyTest, RootReleaseFailureTerminatesWithoutEnteringStopped) {
+  // Activation may fail and be tolerated; failed release must terminate the graph.
+  fail_action = "eStop";
+  yasminx::RootStateMachine root("policy-test",
+      yasmin::Outcomes {sm::kOutcomeTerminal, kVisitedStopped}, context);
+  root.add_state(sm::kStateError, std::make_shared<sm::ErrorState>(context), sm::kErrorTransitions);
+  root.add_state(sm::kStateStopped, std::make_shared<StoppedProbe>(context),
+      yasmin::Transitions {{kVisitedStopped, kVisitedStopped}});
+  const auto outcome = root(blackboard);
+  EXPECT_EQ(outcome, sm::kOutcomeTerminal);
+  EXPECT_TRUE(root.is_completed());
+  // is_completed() is the condition the unchanged Agv::Step terminal-stop path consumes.
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_execution_paused_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_execution_paused_state.cpp
@@ -0,0 +1,89 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/execution_paused_state.hpp"
+#include "agvhito/sm/executing_order_state.hpp"
+#include "agvhito/sm/error.hpp"
+#include "agvhito/sm/timing.hpp"
+
+namespace volley::agvhito::test {
+using PausedTest = StateTest;
+
+TEST_F(PausedTest, PauseWaitsWithoutUnpauseUntilExplicitResume) {
+  sm::ExecutionPausedState paused(context);
+  ASSERT_TRUE(paused.OnEntry(blackboard, {}).has_value());
+  const auto waiting = paused.Step(blackboard);
+  ASSERT_TRUE(waiting.has_value());
+  EXPECT_TRUE(IsContinuing(waiting.value()));
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"startPause"}));
+  yasminx::bb::Set(*blackboard, bb::kKeyRequest, bb::Request::Resume);
+  const auto resumed = paused.Step(blackboard);
+  ASSERT_TRUE(resumed.has_value());
+  const auto done = FinishedOutcome(resumed.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeResumed);
+  const auto result = paused.OnExit(blackboard, done);
+  const auto returned = SteadyClock::now();
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), sm::kOutcomeResumed);
+  EXPECT_GE(returned - FinishedAt(), sm::kUnpauseSettlePeriod);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"startPause", "stopPause"}));
+}
+
+TEST_F(PausedTest, CanceledExitDoesNotUnpause) {
+  sm::ExecutionPausedState paused(context);
+  const auto result = paused.OnExit(blackboard, yasminx::kOutcomeCanceled);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(PausedTest, MissingResumeAuthorizationDoesNotUnpause) {
+  sm::ExecutionPausedState paused(context);
+  const auto result = paused.OnExit(blackboard, std::nullopt);
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorWrongRequest);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(PausedTest, FailedUnpauseDoesNotReturnResumed) {
+  fail_action = "stopPause";
+  sm::ExecutionPausedState paused(context);
+  const auto result = paused.OnExit(blackboard, sm::kOutcomeResumed);
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().outcome, sm::kOutcomeErrored);
+  EXPECT_EQ(result.error().error.type, sm::kErrorActionStatusFailed);
+}
+
+TEST_F(PausedTest, LifecycleResumeAndExecutingReentryDoNotRepublishOrder) {
+  const auto active = std::make_shared<ActiveOrder>(Order());
+  yasminx::bb::Set(*blackboard, bb::kKeyActiveOrder, active);
+  yasminx::bb::Set(*blackboard, bb::kKeyRequest, bb::Request::Resume);
+  sm::ExecutionPausedState paused(context);
+  const auto outcome = RunLifecycle(paused, blackboard, From(sm::kStateExecutingOrder));
+  EXPECT_EQ(outcome, sm::kOutcomeResumed);
+  sm::ExecutingOrderState executing(context);
+  ASSERT_TRUE(executing.OnEntry(blackboard, From(sm::kStateExecutionPaused)).has_value());
+  EXPECT_EQ(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).value(), active);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"startPause", "stopPause"}));
+  EXPECT_EQ(publisher->Publications().size(), 2u);
+}
+
+TEST_F(PausedTest, CanceledFlagOverridesResumeAuthorization) {
+  sm::ExecutionPausedState paused(context);
+  paused.cancel_state();
+  const auto result = paused.OnExit(blackboard, sm::kOutcomeResumed);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(PausedTest, ShutdownExitDoesNotUnpause) {
+  sm::ExecutionPausedState paused(context);
+  rclcpp::shutdown();
+  const auto result = paused.OnExit(blackboard, sm::kOutcomeResumed);
+  ASSERT_TRUE(result.has_value());
+  EXPECT_EQ(result.value(), yasminx::kOutcomeCanceled);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_execution_recovery_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_execution_recovery_state.cpp
@@ -0,0 +1,63 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/execution_recovery_state.hpp"
+#include "agvhito/sm/executing_order_state.hpp"
+#include "agvhito/sm/error.hpp"
+
+namespace volley::agvhito::test {
+using RecoveryTest = StateTest;
+
+TEST_F(RecoveryTest, HooksDoNotPublishAndKeepActiveOrder) {
+  const auto active = std::make_shared<ActiveOrder>(Order());
+  yasminx::bb::Set(*blackboard, bb::kKeyActiveOrder, active);
+  sm::ExecutionRecoveryState recovery(context);
+  const auto outcome = RunLifecycle(recovery, blackboard, From(sm::kStateExecutingOrder));
+  EXPECT_EQ(outcome, sm::kOutcomeRecovered);
+  sm::ExecutingOrderState executing(context);
+  ASSERT_TRUE(executing.OnEntry(blackboard, From(sm::kStateExecutionRecovery)).has_value());
+  EXPECT_EQ(yasminx::bb::Get(*blackboard, bb::kKeyActiveOrder).value(), active);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(RecoveryTest, EachFreshnessGateMustHold) {
+  sm::ExecutionRecoveryState recovery(context);
+  const auto expect_continue = [&] {
+    const auto step = recovery.Step(blackboard);
+    ASSERT_TRUE(step.has_value());
+    EXPECT_TRUE(IsContinuing(step.value()));
+  };
+  const auto good_state = tracked;
+  auto empty_state = std::make_shared<TrackedMessage<vs::State>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+  yasminx::bb::Set(*blackboard, bb::kKeyState, empty_state);
+  expect_continue();
+  yasminx::bb::Set(*blackboard, bb::kKeyState, good_state);
+
+  const auto good_common = common;
+  auto empty_common = std::make_shared<TrackedMessage<hc::CommonMessage>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+  yasminx::bb::Set(*blackboard, bb::kKeyCommonMessage, empty_common);
+  expect_continue();
+  yasminx::bb::Set(*blackboard, bb::kKeyCommonMessage, good_common);
+
+  pose->Reset();
+  expect_continue();
+  ASSERT_TRUE(pose->Set(clock->now(), 0, 0, 0));
+  const auto fresh = recovery.Step(blackboard);
+  ASSERT_TRUE(fresh.has_value());
+  const auto done = FinishedOutcome(fresh.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeRecovered);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(RecoveryTest, CanceledAndInvalidExitRemainPublicationFree) {
+  sm::ExecutionRecoveryState recovery(context);
+  const auto canceled = recovery.OnExit(blackboard, yasminx::kOutcomeCanceled);
+  ASSERT_TRUE(canceled.has_value());
+  EXPECT_EQ(canceled.value(), yasminx::kOutcomeCanceled);
+  const auto invalid = recovery.OnExit(blackboard, std::nullopt);
+  ASSERT_FALSE(invalid.has_value());
+  EXPECT_EQ(invalid.error().outcome, sm::kOutcomeErrored);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+}  // namespace volley::agvhito::test
```

### test/sm/test_idle_state.cpp

```diff
--- /dev/null
+++ b/test/sm/test_idle_state.cpp
@@ -0,0 +1,102 @@
+#include "state_test_fixture.hpp"
+
+#include "agvhito/sm/idle_state.hpp"
+#include "agvhito/sm/error.hpp"
+
+namespace volley::agvhito::test {
+using IdleTest = StateTest;
+
+TEST_F(IdleTest, StationaryEntryDoesNotInterfereWithCharging) {
+  sm::IdleState idle(context);
+  ASSERT_TRUE(idle.OnEntry(blackboard, {}).has_value());
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(IdleTest, EntryDoesNotReleaseExistingSoftwareStop) {
+  state.safety_state.e_stop = vs::EStop::REMOTE;
+  Refresh();
+  sm::IdleState idle(context);
+  ASSERT_TRUE(idle.OnEntry(blackboard, {}).has_value());
+  EXPECT_TRUE(publisher->Publications().empty());
+  const auto step = idle.Step(blackboard);
+  ASSERT_FALSE(step.has_value());
+  EXPECT_EQ(step.error().outcome, sm::kOutcomeSoftEstopTriggered);
+}
+
+TEST_F(IdleTest, HardwareStopStillRejectsEntry) {
+  state.safety_state.e_stop = vs::EStop::MANUAL;
+  Refresh();
+  sm::IdleState idle(context);
+  const auto result = idle.OnEntry(blackboard, {});
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().outcome, sm::kOutcomeHwEstopTriggered);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(IdleTest, CancelFinishedIsNotTraversalCompletion) {
+  state.driving = true;
+  state.edge_states.emplace_back();
+  complete_cancel_motion = false;
+  Refresh();
+  // Inject FINISHED synchronously, but delay actual motion/traversal completion.
+  publisher->respond = [this](const auto& payload) {
+    Respond(payload);
+    workers.emplace_back([this] {
+      std::this_thread::sleep_for(300ms);
+      state.driving = false;
+      state.edge_states.clear();
+      Refresh();
+    });
+  };
+  sm::IdleState idle(context);
+  const auto before = SteadyClock::now();
+  const auto result = idle.OnEntry(blackboard, {});
+  const auto after = SteadyClock::now();
+  ASSERT_TRUE(result.has_value());
+  EXPECT_GE(after - before, 300ms);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"cancelOrder"}));
+}
+
+TEST_F(IdleTest, QueuedOrderDoesNotRequirePausedState) {
+  ASSERT_TRUE(queue->Push(Order()));
+  sm::IdleState idle(context);
+  const auto step = idle.Step(blackboard);
+  ASSERT_TRUE(step.has_value());
+  const auto done = FinishedOutcome(step.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeOrderRequested);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+TEST_F(IdleTest, ControlledStopOutcomePreserved) {
+  yasminx::bb::Set(*blackboard, bb::kKeyRequest, bb::Request::ControlledStop);
+  sm::IdleState idle(context);
+  const auto step = idle.Step(blackboard);
+  ASSERT_TRUE(step.has_value());
+  const auto done = FinishedOutcome(step.value());
+  ASSERT_TRUE(done.has_value());
+  EXPECT_EQ(done, sm::kOutcomeControlledStopRequested);
+}
+
+TEST_F(IdleTest, CancelFailureCannotCompleteEntry) {
+  state.driving = true;
+  Refresh();
+  fail_action = "cancelOrder";
+  sm::IdleState idle(context);
+  const auto result = idle.OnEntry(blackboard, {});
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorActionStatusFailed);
+  EXPECT_EQ(ActionTypes(), (std::vector<std::string> {"cancelOrder"}));
+}
+
+TEST_F(IdleTest, StaleEntryStillRejectsActivation) {
+  auto empty = std::make_shared<TrackedMessage<vs::State>>(clock, rclcpp::Duration(30s), rclcpp::Duration(60s));
+  yasminx::bb::Set(*blackboard, bb::kKeyState, empty);
+  sm::IdleState idle(context);
+  const auto result = idle.OnEntry(blackboard, {});
+  ASSERT_FALSE(result.has_value());
+  EXPECT_EQ(result.error().error.type, sm::kErrorStateStale);
+  EXPECT_TRUE(publisher->Publications().empty());
+}
+
+}  // namespace volley::agvhito::test
```

