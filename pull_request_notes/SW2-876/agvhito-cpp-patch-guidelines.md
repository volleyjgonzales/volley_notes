# AGVHITO C++ patch guidelines

Practical reference for implementing patches in this repository, with emphasis on the AGV state machine.

**Basis:** the attached `agvhito-repomix(1).md`. Paths below are relative to the AGVHITO package; prepend `src/agvhito/` in the full workspace. **Observed** means a pattern appears in the snapshot. **Recommended** means guidance for new patches, rather than a verified company-wide requirement. Follow the checkout's `AGENTS.md`, formatter, lint configuration, and build settings when available; those policies and the external `stdx`/`yasminx` implementations are not established by this export. The SW2-876 readiness helper remains a proposal, not existing repository behavior.

## 1. Quick reference

| Feature / idiom | Default for a patch | Source examples |
| --- | --- | --- |
| `const auto` | Immutable local values and checked result wrappers; use mutable `auto` when changing or moving the value. | `src/sm/executing_order_state.cpp` |
| `const auto&` | Borrow an existing object when its owner outlives the reference; avoid unnecessary payload copies. | `src/sm/booting_state.cpp` |
| Explicit types | Use when units, ownership, protocol meaning, or conversions need to be visible. | `include/agvhito/sm/timing.hpp`, `src/pose_filter.cpp` |
| Structured bindings | `const auto& [key, value]` for read-only map traversal. | `src/sm/booting_state.cpp` |
| Nested namespaces | Match `volley::agvhito`, `::sm`, `::comms`, or `::sim`; do not invent another namespace for a small helper. | `include/agvhito/sm/context_utils.hpp` |
| Anonymous namespace | File-private constants and implementation helpers in `.cpp` files. | `src/sm/context_utils.cpp` |
| Designated initializers | Name aggregate fields, in declaration order, for context, errors, and protocol values. | `src/sm/root.cpp` |
| `stdx::Expected` | Preserve existing result/error types; check before extracting. | `include/agvhito/sm/context_utils.hpp` |
| `std::optional` | Represent legitimate absence; absence is not automatically failure. | `include/agvhito/comms/i_map_client.hpp` |
| Guard clauses | Return early for stale data, cancellation, and failed operations. | `src/sm/executing_order_state.cpp` |
| `explicit`, `override`, `[[nodiscard]]` | Match existing state declarations and make interface intent visible. | `include/agvhito/sm/localizing_state.hpp` |
| Typed blackboard keys | Use `yasminx::bb::Get/Set/Remove` and declared `bb::kKey...` constants. | `include/agvhito/sm/blackboard.hpp` |
| Outcomes and transition maps | Keep routing constants, supported outcomes, and state registration consistent. | `include/agvhito/sm/state_strings.hpp`, `src/sm/root.cpp` |
| RAII locks and ownership | Use standard scoped locks and smart pointers; respect the framework's ownership. | `src/pose_filter.cpp`, `src/sm/root.cpp` |
| Verification helpers | Separate transport success, robot action completion, telemetry predicates, and physical readiness. | `src/sm/context_utils.cpp` |
| Typed time durations | Use named chrono durations; choose the clock to match the required behavior. | `include/agvhito/sm/timing.hpp` |
| Focused tests | Exercise changed behavior and failure/cancellation paths using existing fixtures. | `test/comms/test_sim_mqtt.cpp`, `test/topics/test_state_predicates.cpp` |

## 2. Local declarations: `auto`, constness, and references

### 2.1 Prefer immutable locals when mutation is unnecessary

**Observed:** state code commonly uses `const auto` for operation results and snapshots:

```cpp
const auto state_or =
    yasminx::bb::Get(*blackboard, bb::kKeyState).value()->GetIfNotStale();
if(!state_or.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
      .type = kErrorStateStale,
      .message = "State message is stale, preventing order execution",
  });
}
const vstate::State& state = state_or.value();
```

Here `state_or` owns the returned optional snapshot. `state` borrows its contained value and is valid while `state_or` remains alive and unchanged. Explicit `vstate::State&` communicates the protocol type; `const auto& state = state_or.value();` is also reasonable in a small, obvious scope.

| Declaration | Meaning | Use when |
| --- | --- | --- |
| `auto value = expression;` | Usually owns a value; ordinary deduction drops top-level references and constness. | Mutating a local copy or consuming it through a move. |
| `const auto value = expression;` | Owns an immutable local value. | The value/result is only inspected. |
| `auto& value = expression;` | Borrows a mutable lvalue. | Mutation of the original object is intentional. |
| `const auto& value = expression;` | Borrows read-only; can bind to a temporary under applicable lifetime-extension rules. | Avoiding copies with a clear lifetime. |
| `auto&& value = expression;` | Deduces a reference according to value category. | Generic code that needs it; do not use by habit in ordinary state logic. |

**Recommended:** choose ownership first, then constness. `auto` is not automatically a performance improvement; it can copy a large object returned by reference.

### 2.2 Constness of a smart pointer does not make its pointee const

```cpp
const auto queue = yasminx::bb::Get(*blackboard, bb::kKeyOrderQueue).value();
queue->Clear();
```

This is legal: the local smart pointer cannot be reassigned, but the pointed-to queue remains mutable. Use a pointer/reference to a const pointee when the API needs to prevent pointee mutation. Do not infer thread safety from `const auto` or from `shared_ptr` ownership.

### 2.3 Avoid references into temporary result wrappers

```cpp
// Avoid: GetIfNotStale() returns a temporary optional owner.
const auto& state = tracker->GetIfNotStale().value();

// Prefer: keep the owner alive, then validate and borrow.
const auto state_or = tracker->GetIfNotStale();
if(!state_or.has_value()) {
  // Return the appropriate outcome/error for this state.
}
```

The second snippet is a pattern fragment: its absent-value branch must exit before extraction. Binding a reference through `.value()` does not extend the lifetime of the temporary wrapper. Also inspect getters' signatures: a reference to shared mutable storage has different concurrency semantics from an owned snapshot.

### 2.4 Use mutable results when extracting by move

**Observed:** `MapClient::GetMaps` checks `auto map_or`, then extracts with `std::move(map_or).value().value()`.

`std::move` is a cast that permits move-aware overload selection; it does not itself move anything. Moving from a `const` object often selects copying or fails for move-only types. A result that will be consumed should generally be `auto`, not `const auto`.

Do not add `std::move` to every return. Return a local owner normally, as `MakeRootStateMachine` does with `return state_machine;`; return-value optimization or implicit move handles suitable cases. After an actual move, do not assume the source retains its previous content.

## 3. Namespaces, names, headers, and constants

**Observed:** package code uses nested namespace declarations and closing comments:

```cpp
namespace volley::agvhito::sm {

namespace vstate = vda5050_interfaces::v2::state;

namespace {
constexpr auto kPollPeriod {100ms};
}  // namespace

}  // namespace volley::agvhito::sm
```

The duration literal requires `std::chrono_literals` to be in scope. Match the surrounding file's placement. File-level aliases such as `vstate`, `vinstant`, and `vorder` make protocol-heavy code readable.

**Recommended:** keep broad `using namespace` directives out of public headers. Existing `.cpp` files use chrono directives; follow their local style without importing an entire unrelated namespace. Put private helpers in an anonymous namespace in a `.cpp`; expose only helpers that callers need.

Observed naming patterns:

- Types: `BootingState`, `StatePredicate`, `ActionStateManager`.
- Methods/functions: `OnEntry`, `VerifiedPublish`, `GetIfNotStale`.
- Locals: `state_or`, `order_map_id`, `is_canceled`.
- Members: `entry_stamp_`, `order_complete_stamp_`.
- Constants: `kDefaultStepPeriod`, `kOutcomeResumed`, `kErrorStateStale`.

The `_or` suffix appears for both expected results and optional values. Determine semantics from the declared return type, rather than the name alone.

**Observed:** headers use `#pragma once`; `.cpp` files generally include their own header first, then external headers, then package headers. Include what new code directly needs, rather than relying on incidental transitive includes. Preserve intentional `IWYU pragma: keep`, formatting controls, and narrow lint suppressions; do not copy suppressions into unrelated code.

Use `inline constexpr` for shared header constants whose type supports it. The transition maps are `inline const yasmin::Transitions`, not `constexpr`; do not assume every runtime container supports constant evaluation. Keep units in the type or name:

```cpp
inline constexpr std::chrono::milliseconds kDefaultStepPeriod {100};
inline constexpr std::chrono::seconds kDefaultLogThrottlePeriod {5};
```

**Recommended:** use strong/explicit types at boundaries when deduction could conceal a unit, signedness, narrowing conversion, or ownership contract. Braced initialization helps catch many narrowing conversions, but does not make every conversion safe.

## 4. Structured bindings and ranges

**Observed:** boot code reads floor-map entries as:

```cpp
for(const auto& [_, floor_map_id] : floor_map_ids) {
  expected_map_ids.insert(floor_map_id);
}
```

`const auto&` avoids copying the entry and prevents mutation through these bindings. `auto [key, value]` copies an entry; changing the copied value does not update the container. `auto& [key, value]` borrows it for mutation, subject to the container's type rules: a map's key is normally const.

`_` is an ordinary variable name here, not a special discard operator. Use a meaningful name if the value will be used, and follow local lint requirements for unused bindings. Do not keep these references after erasing entries or invalidating the underlying container.

**Observed:** `OutcomesOf` uses `std::views::keys` and constructs an owned outcome container:

```cpp
inline yasmin::Outcomes OutcomesOf(const yasmin::Transitions& transitions) {
  const auto keys = std::views::keys(transitions);
  return {keys.begin(), keys.end()};
}
```

The view refers to `transitions`; the returned outcomes own their elements. Prefer existing `std::ranges::any_of`, `all_of`, and `find_if` patterns for straightforward checks. Do not return a view into a local container or build a complex pipeline that obscures the state-machine decision.

## 5. Aggregates and designated initializers

**Observed:** contexts, errors, lifecycle results, and protocol messages often use named aggregate members:

```cpp
yasminx::StateContext {
    .clock = std::move(clock),
    .logger = std::move(logger),
}

yasminx::Error {
    .type = kErrorStateStale,
    .message = "State is stale",
}

yasminx::LifecycleState::Finished {.outcome = kOutcomeOrderDataStale}
```

**Recommended:** use this style when the type is an aggregate and field names clarify meaning. C++ designated initializers must follow member declaration order. They are not arbitrary-order named constructor arguments; do not use them on a nonaggregate type or mix designated and positional clauses in the same aggregate initializer.

Omitted fields use their default member initializer when provided, or the applicable aggregate-initialization rules otherwise. Inspect the declaration before relying on a default. External protocol structs can contain scalar fields without safe default member initialization; existing predicate tests explicitly set `state.safety_state.e_stop` for meaningful checks. Value initialization (`State state {};`) is useful, but still set the fields that express the test's intended state.

When adding an aggregate member, inspect existing aggregate call sites and defaults. A field addition can change behavior even when old code still compiles.

## 6. Results: `stdx::Expected`, `std::expected`, and optional values

### 6.1 Use the repository abstraction in repository APIs

**Observed:** this package uses `stdx::Expected`, `stdx::Unexpected`, and `stdx::Result`, rather than spelling its APIs with `std::expected`.

| Shape in this package | Meaning |
| --- | --- |
| `stdx::Expected<T, yasminx::Error>` | Helper returns a value or a structured diagnostic error. |
| `stdx::Expected<void, yasminx::Error>` | Helper succeeds without a payload, or returns a diagnostic error. |
| `stdx::Expected<void, yasminx::ErrorOutcome>` | State entry succeeds, or returns failure with routing information. |
| `stdx::Expected<StepResult, yasminx::ErrorOutcome>` | State step continues/finishes, or returns a routed failure. |
| `stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome>` | State execution/exit returns an outcome or routed failure. |
| `stdx::Expected<T>` / `stdx::Result` | Uses repository defaults/aliases; inspect `stdx/expected.hpp` before depending on their exact definitions. |
| `std::optional<T>` | A value may legitimately be absent. |

`std::expected<T, E>` is the standard C++23 value-or-error facility. It is conceptually related, but the attached export does not establish whether `stdx::Expected` is an alias, wrapper, or separate implementation. Do not replace it opportunistically or assume support for `and_then`, `transform`, or every standard overload.

In particular, the repository has calls such as `stdx::Unexpected("... {}", argument)`. That formatting convenience is not the ordinary `std::unexpected` construction API. Preserve the existing abstraction unless a patch explicitly addresses its migration.

### 6.2 Check the active alternative before extraction

**Observed helper pattern:**

```cpp
const auto published = VerifiedPublish(
    {MakeCancelOrderAction()}, *blackboard, GetContext(),
    [this] { return is_canceled(); });
if(!published.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, published.error());
}
return {};
```

`.value()` requires a value; `.error()` requires an error. The exact invalid-access behavior of the repository wrapper is external to this pack; never rely on it for ordinary control flow.

For an expected-with-void success, `return {};` expresses successful completion in the observed code. It does not universally mean success: in an optional-returning function `{}` can mean absence; in an expected-with-value it may construct a default value. Make the return type and intent clear.

### 6.3 Preserve the distinction between diagnostics and graph routing

```cpp
// In a helper returning Expected<void, yasminx::Error>:
return stdx::Unexpected(yasminx::Error {
    .type = kErrorVerifyTimeout,
    .message = "Timed out waiting for traversal completion",
});

// At the state boundary, choose an outcome for that helper failure:
return yasminx::MakeUnexpected(kOutcomeErrored, result.error());

// If result already contains ErrorOutcome, preserve its routing:
return stdx::Unexpected(result.error());
```

These are separate pattern fragments with their corresponding return types. `yasminx::Error` carries diagnostics; `ErrorOutcome` adds outcome/routing semantics. Do not wrap an already routed failure as though it were only a diagnostic, or flatten a specific hardware/software-stop outcome to `errored` without intent. `CheckEStopClear` demonstrates routed errors.

### 6.4 Optional absence and operation failure are different

**Observed:** `IMapClient::GetMap` returns `stdx::Expected<std::optional<Map>>`:

1. Outer error: request/decoding failed.
2. Outer success, empty optional: map is absent.
3. Outer success, present optional: map exists.

Handle both layers explicitly. Likewise, a tracked state's empty optional means fresh data is unavailable; a missing active order has different meaning and a different diagnostic. `PausedIs(false)` interprets an unset pause flag as false in the current code; do not equate that default with positive firmware-readiness evidence.

## 7. State-machine interface and routing conventions

### 7.1 Choose the existing state model that fits the task

**Observed:** `BootingState` derives from `yasminx::State` and supplies `Execute`. Most other states derive from `yasminx::LifecycleState` and implement entry and polling hooks.

| Hook | Observed purpose | Return shape |
| --- | --- | --- |
| `Execute` | Entire execution body, such as boot initialization. | Expected outcome / error outcome. |
| `OnEntry` | Initialization, validation, or a one-time entry command. | Expected void / error outcome. |
| `Step` | Inspect fresh telemetry or requests and decide whether to continue. | Expected `StepResult` / error outcome. |
| `OnExit` | Exit work and/or final outcome selection when overridden. | Expected outcome / error outcome. |

A typical declaration uses `explicit` on the constructor, `override` on hooks, and `[[nodiscard]]` on their results. Preserve framework signatures exactly; a similarly named method with the wrong signature is not an override.

Constructors derive their supported outcomes from the transition map:

```cpp
ExecutionPausedState::ExecutionPausedState(yasminx::StateContext context) :
    yasminx::LifecycleState(
        OutcomesOf(kExecutionPausedTransitions),
        std::move(context), kDefaultStepPeriod) {
}
```

### 7.2 Keep the step result separate from the final outcome

**Observed:**

```cpp
return yasminx::LifecycleState::Continue {};
return yasminx::LifecycleState::Finished {.outcome = kOutcomeOrderComplete};
```

`Continue` asks the lifecycle to keep polling; `Finished` ends that polling phase. In paused/recovery states, `Step` returns `Finished {}` and their `OnExit` supplies `kOutcomeResumed` / `kOutcomeRecovered`. Preserve that pairing. Removing an exit override requires checking what happens to a finish without an explicit outcome.

The external `yasminx` implementation is not included here. Check it before relying on the precise order of hooks during cancellation, entry failure, step failure, or exit failure. For a new hook with physical side effects, cancellation behavior must be explicit and covered by a test; do not assume a later canceled outcome undoes an earlier command.

### 7.3 Keep graph declarations and behavior consistent

Adding a routed outcome requires checking:

1. Its name/constant in `include/agvhito/sm/state_strings.hpp`.
2. The source state's transition map, including cancellation.
3. `OutcomesOf(...)` used in the state constructor.
4. Destination state registration in `src/sm/root.cpp`.
5. Tests for both the returned outcome and resulting behavior.

The graph is compiled C++ in this package. A new diagnostic type can be independent of graph routing: several failures can intentionally share `kOutcomeErrored` while preserving distinct `kError...` types.

Do not confuse `kOutcomeCanceledOrder` (robot-order cancellation completed, routing to Stopped) with `yasminx::kOutcomeCanceled` (framework/state execution canceled, routing to the terminal outcome in these maps).

### 7.4 Preserve re-entry behavior and order ownership

**Observed:** `ExecutingOrderState::OnEntry` returns early when re-entered from paused or recovery because the robot already has the order. Re-entering after a queued-order self-transition is different: it dispatches a new order.

**Recommended:** before changing entry code, enumerate initial entry, self-transition, resume, and recovery. A validation or publication placed before the existing early return may alter all of them. Avoid republishing an accepted order as a side effect of resume, and preserve the sequence of verified publication, active-order installation, and pending-queue removal.

Reset per-execution members in the appropriate entry path, as existing code does with `order_complete_stamp_.reset()`. State objects can be reused; constructor initialization alone may not cover re-entry.

## 8. Blackboard access and telemetry

**Observed:** keys couple the name and value type:

```cpp
inline constexpr yasminx::bb::Key<ActionStateManagerSPtr>
    kKeyActionStateManager {"action-state-manager"};
```

Use declared keys and the typed utilities. Avoid scattering raw key strings or bypassing their type contract. `Agv::InitializeBlackboard` installs required dependencies before `SetupStateMachine` runs the graph.

There are two separate checks in this common expression:

```cpp
const auto state_or =
    yasminx::bb::Get(*blackboard, bb::kKeyState).value()->GetIfNotStale();
```

The first `.value()` assumes the tracker dependency exists. `GetIfNotStale()` can legitimately return no usable telemetry. The export does not include the implementation of typed `bb::Get`; inspect it for exact return/error behavior when modifying initialization.

**Recommended:** unchecked extraction is appropriate only for a documented initialization invariant. Optional keys such as active order or registered callbacks must be checked. New tests must initialize every invariant required by the hook they invoke.

Read a snapshot once for a coherent decision. Re-read after waits or operations when the next decision requires newer data. Do not hold an old snapshot and call it “current” merely because the tracker has since received messages. Even a fresh message does not automatically correlate with the just-issued action: match IDs and, where required, timestamps.

`bb::TakeRequest` reads and removes the shared request key, including requests the caller cannot act on. This is a consumable slot, not a queue. Fetch it once per decision; do not call it repeatedly to test different cases. Its read/remove sequence alone does not prove atomic request consumption under concurrent writers; inspect synchronization before promising stronger semantics.

## 9. Cancellation, callbacks, clocks, and concurrency

### 9.1 Make waits cooperative

**Observed:** helper calls receive `[this] { return is_canceled(); }`, and polling loops inspect cancellation. Boot returns the framework canceled outcome directly; helper waits report `kErrorCanceled`, which callers adapt.

**Recommended:** check cancellation before a new physical command, while waiting, and before allowing follow-on work. Define how that error maps at the state boundary. A check followed by a publish is not atomic with an asynchronous stop request; a command already sent cannot be withdrawn by returning canceled.

For `OnExit` code that can resume/unpause, inspect both `is_canceled()` and the lifecycle's exit reason as applicable. Cancellation should not deliberately initiate new motion. Check the external lifecycle contract and preserve its outcome handling.

### 9.2 Choose clock semantics deliberately

| Requirement | Clock choice to consider |
| --- | --- |
| ROS timestamp comparisons, telemetry age, simulation-driven waits | The existing context/ROS clock and compatible clock types. |
| A physical firmware settling interval that must take real elapsed time | `std::chrono::steady_clock`, explicitly chosen for that requirement. |
| Human-facing logs / timestamp formatting | Existing timestamp utilities and clock conventions. |

The existing `VerifiedPublish` / `VerifyState` deadlines and sleeps use `context.clock`. Boot chooses `rclcppx::GetSteadyOrSimClock`. Do not describe all existing waits as steady wall-clock waits. A paused simulation clock can affect progress; jumping timestamps can affect freshness checks.

Use a deadline, check it after waking, and define interruption behavior. For a new real-time guard, short cancellation-aware waits can improve responsiveness; they do not guarantee a precise cancellation latency under OS scheduling. Verify elapsed-time lower bounds without requiring exact completion times.

### 9.3 Callback capture is a lifetime contract

`[this]` borrows the state object; it does not keep it alive. Existing verification helpers use their cancellation callable synchronously. Do not store that callable or launch detached work from it without designing ownership and shutdown. Reference captures are appropriate only when the referenced object outlives every invocation.

**Recommended:** keep blocking state work on the established execution path. ROS callbacks process subscriptions and requests; a wait that prevents those callbacks from running can starve its own completion condition. Inspect the worker/executor arrangement in the full workspace before adding blocking work or another thread.

### 9.4 RAII does not replace a concurrency design

**Observed:** `PoseFilter` and `ActionStateManager` use scoped locks; `TrackedMessage` declares a mutex and thread-safety annotations. `std::lock_guard lock(mutex_)` uses class template argument deduction; an explicitly typed lock guard also appears in the repo.

Keep locks scoped and avoid sleeping, invoking arbitrary callbacks, or publishing while holding a data mutex unless the design explicitly requires it. `shared_ptr` manages lifetime; it does not synchronize the object. `const` methods can lock a `mutable` mutex and can still need synchronization.

## 10. Command verification and physical semantics

**Observed:** `VerifiedPublish` has different verification contracts for instant actions and orders:

| Observation | What it establishes | What it does not establish |
| --- | --- | --- |
| Publish future returns `PublishResult::Ok` | Transport reported success. | Robot execution or readiness. |
| Matching action ID is `FINISHED` | Robot reports that action complete. | Every delayed firmware consequence has settled. |
| Order ID is echoed | Reported order acceptance condition holds. | Traversal complete or robot stationary. |
| Fresh state satisfies a predicate | The sampled fields meet that predicate. | An undocumented firmware mode or stronger physical guarantee. |
| `IsTraversalComplete(state)` | No remaining node/edge states and not driving, per this snapshot. | Every unrelated stop/readiness condition. |

Reuse `VerifiedPublish`, `VerifyState`, action factories, and named predicates instead of duplicating their protocol plumbing. Keep error propagation and cancellation connected. An action factory creates the action; it does not send or verify it.

Vector order in an instant-action batch is not proof of serial firmware execution. When one action requires another to complete or settle, publish/verify the prerequisite and then the dependent operation under a documented contract.

The SW2-876 proposal adds a HITO-specific unpause guard to `sm/context_utils`; it does not change every `VerifiedPublish` call. Future vendor workarounds should likewise live near vendor behavior, rather than becoming an unexplained delay in a generic state-machine framework.

Removing a physical pause/stop command is a behavioral change even if the adapter's destination state remains named Idle, Stopped, or Error. Local queue clearing or dropping `kKeyActiveOrder` does not cancel an order already accepted by the robot. Review physical effects as well as return values.

## 11. Additional idioms worth following

**Observed ownership patterns:** `unique_ptr` for root ownership, `shared_ptr` for framework-owned states and shared blackboard dependencies, and `weak_ptr` for simulated publisher links. Use `make_unique` / `make_shared` and existing aliases where appropriate. Pass owned configuration/context by value and move into a member when following the established constructor style; borrow read-only inputs through `const&` when ownership is unnecessary.

**Observed concepts:** `TrackedMessage` constrains its template through `VdaMessage`, using `requires` and `std::convertible_to`. This expresses the minimal timestamp operation it needs. Use concepts for real generic interface requirements; a concrete state patch does not need a template merely to look modern.

**Observed variants:** simulation motion code uses `std::visit` for its motion alternatives. Keep variant handling type-aware and cover every relevant alternative. Do not replace distinct protocol or lifecycle states with loosely related flags unless it simplifies an actual invariant.

**Observed boundary handling:** map-client decoding catches exceptions and converts them to expected errors; simulation also throws for certain invalid motion combinations. The package is not universally exception-free. Prefer returned results for expected operational failures in state/helpers; preserve boundary exception handling rather than catching everything in each state and silently continuing.

**Observed logging:** use `LOG_INFO`, `LOG_WARN`, and their throttled variants with the supplied logger/clock. Log IDs, the failed predicate, and meaningful timing when diagnosing protocol behavior. Polling logs should be throttled. Report “request accepted” separately from “action completed”; avoid claiming readiness from transport success alone.

## 12. Language features and build compatibility

| Feature seen or discussed | Standard introduction | Patch implication |
| --- | --- | --- |
| `auto`, lambdas, move semantics, smart pointers | C++11 | Existing baseline idioms. |
| Nested namespace syntax, structured bindings, `std::optional`, `std::variant`, CTAD, `if` initializer, `[[nodiscard]]` | C++17 | Extensively compatible with the snapshot's style. |
| Designated initializers, concepts, ranges | C++20 | Already appear in this export. |
| `std::expected` | C++23 | Do not infer availability from `stdx::Expected`. |

These are feature introduction dates, not proof of the workspace's configured language standard. `CMakeLists.txt` delegates setup to `volley_cmake`; that implementation and the external standard-library compatibility policy are not included. Inspect actual compile flags and dependency headers before adopting an additional feature.

## 13. Tests and patch review checklist

Start with the nearest existing fixture:

| Change | Existing reference |
| --- | --- |
| State predicates | `test/topics/test_state_predicates.cpp` |
| Action ID/status tracking | `test/test_action_state_manager.cpp` |
| Action assembly and generated message fields | `test/test_instant_action_assembler.cpp` |
| In-process MQTT transport | `test/comms/test_sim_mqtt.cpp` |
| Telemetry age and simulated time | `test/test_tracked_message.cpp`, `test/time_utils.hpp` |
| Order progress and queue behavior | `test/test_active_order.cpp`, `test/test_order_queue.cpp` |

**Recommended:** test the externally meaningful change. For a state patch this may include the returned outcome, command presence/absence, order re-entry behavior, stale-data handling, cancellation, and a physical-completion predicate. A test that only reconstructs the implementation's expression provides little regression protection.

Use `ASSERT_TRUE(result.has_value())` before dereferencing in GoogleTest; `EXPECT_TRUE` permits execution to continue after failure. Feed status for the actual generated action ID. Drive telemetry concurrently when the worker waits for it. Ensure failure paths cancel/join work and bound receiver waits. For timing guards, assert a monotonic lower bound and avoid narrow scheduling-dependent upper bounds.

The existing CMake test targets use `volley_add_gtest`; its globbing implementation is outside this export. When adding a new test directory or target, inspect the macro and avoid compiling/registering the same tests twice. Link the library that owns the behavior being tested, not an unrelated library selected solely because its target already exists.

Before submitting a patch:

- Confirm the needed types, APIs, and compiler features in the checkout.
- Match nearby names, namespace placement, includes, and formatting.
- Check every optional/expected extraction and the lifetime of every borrowed value.
- Preserve error diagnostics and intentional outcome routing.
- Keep transition maps, supported outcomes, and state registration aligned.
- Check initial entry, self-transition, resume, recovery, and per-entry resets.
- Make command ordering, telemetry freshness/correlation, and cancellation explicit.
- Distinguish adapter state changes from physical robot actions.
- Add or extend the relevant regression test and run the affected suite.
- Update comments when behavior changes; report validation that actually ran.

## 14. Patterns to review carefully before copying

| Existing or tempting pattern | Review concern |
| --- | --- |
| Unchecked blackboard `.value()` | Depends on initialization invariants; optional runtime data needs checks. |
| `const auto` everywhere | Can introduce copies and block move extraction; choose ownership deliberately. |
| Reference to `.value()` of a temporary wrapper | Can dangle after the full expression. |
| `Finished {}` without an explicit outcome | Depends on exit/default behavior; verify the lifecycle contract. |
| Exit hook that unpauses | Must handle cancellation and object lifetime. |
| Recovery logs verification failure and continues | Existing policy exception, not a general error-handling recommendation. |
| `FINISHED` or `paused == false` means ready | Stronger claim than these observations establish. |
| `TakeRequest` treated as a request queue | Consumption/discard and concurrency semantics differ. |
| Deleting pause/stop but retaining the state name | May change physical guarantees without changing graph routing. |
| Copying a new modern standard-library API | Requires compiler/library support and compatibility with repository wrappers. |

Use this reference to keep patches consistent with the package while reviewing the assumptions behind each copied pattern.
