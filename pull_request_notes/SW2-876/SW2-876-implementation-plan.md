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

No new source file is needed for the production helper: use the existing context-utils module. No new thread, ROS service, blackboard key, or generic `yasminx` modification is planned. There are no existing `test/sm` tests in the supplied snapshot; do not claim that named state tests already exist.

## 3. Shared `UnpauseAndSettle` implementation

### 3.1 Interface and clock contract

Add inside `volley::agvhito::sm`:

```cpp
// include/agvhito/sm/timing.hpp
inline constexpr std::chrono::milliseconds kUnpauseSettlePeriod {200};

// include/agvhito/sm/context_utils.hpp
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
const auto prepared = VerifiedPublish(
    {MakeSoftEStopAction(false), MakeCancelOrderAction(), MakeExceptionClearAction()},
    *blackboard, GetContext(), [this] { return is_canceled(); });
if(!prepared.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, prepared.error());
}

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
| Same | Transport failure/timeout, `FAILED`, action verification timeout | Original error is returned; no downstream control. Use controlled context time for existing 35 s timeouts without advancing the new steady guard. |
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
