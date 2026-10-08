# SW2-876: HITO pause policy and unpause readiness barrier

This is a proposed implementation walkthrough for [SW2-876](https://volleyautomation.atlassian.net/browse/SW2-876), grounded in the supplied `agvhito-repomix.md` and `P15-yasminx-part1of1.md`. It proposes C++ changes; it does not modify the repository or claim that firmware tests have passed. The ticket text and firmware timing observations are supplied by the ticket description, not independently retrieved from Jira.

The change should remove automatic idle/stopped/error pause or software-stop actions and route every remaining unpause through one verified, cancellation-aware **200 ms wall-clock barrier**. Boot and explicit pause/resume are the two normal lifecycle cases. The inspected source also pauses during telemetry recovery; that path must be addressed explicitly to meet this policy.

## Terminology

| Term | Meaning here |
| --- | --- |
| AGV | Automated guided vehicle; the physical HITO robot. |
| HITO | Vendor/project label in this source; its formal expansion is not supplied. |
| ROS 2 | Robot Operating System 2; provides service requests and callbacks. |
| MQTT | Broker-based publish/subscribe protocol, historically MQ Telemetry Transport; carries robot orders and instant actions. |
| VDA5050 | VDA = Verband der Automobilindustrie, the German Association of the Automotive Industry; 5050 is the robot communication specification number. |
| YASMIN | Yet Another State MachINe; the upstream control-state library. |
| yasminx | Volley's C++ extension layer over YASMIN. |
| SM / bb | State machine / blackboard; shared state-machine data. Exact source identifiers retain these abbreviations. |
| API | Application programming interface. |
| ID / GUID | Identifier / globally unique identifier; action IDs correlate commands with firmware status. |
| QoS | Quality of service; MQTT/ROS delivery policy. |
| E-stop | Emergency stop. A hardware E-stop and a requested software E-stop are distinct mechanisms. |
| UTC | Coordinated Universal Time; the supplied firmware log uses UTC+8. |
| ms / s | Milliseconds / seconds. |
| YAML | YAML Ain’t Markup Language; configuration format, not the definition of this state graph. |
| RAII | Resource acquisition is initialization; C++ scope-based resource lifetime management. |
| JSON | JavaScript Object Notation; the serialized protocol payload format. |
| GoogleTest / CMake / colcon | C++ testing framework / build-system tool / ROS workspace build tool. |

`startPause`, `stopPause`, `auto_run`, `FINISHED`, and `FAILED` are exact protocol or firmware identifiers. `stdx::Expected` is the repository's value-or-error result type, not necessarily `std::expected`.

## 1. Start with the command sequence, not the state diagram

Read these files first, in this order. Paths are relative to the repository root; the Repomix extraction is a snapshot and does not establish the current checkout's commit.

| Order | Repository file and symbols | Why start here? |
| --- | --- | --- |
| 1 | `src/agvhito/src/sm/context_utils.cpp`: both `VerifiedPublish` overloads, `VerifyState` | Establish precisely what “verified” means. Instant-action verification waits for each action ID to report `FINISHED`; order verification waits for the robot to echo the order ID. Neither establishes `auto_run` readiness. |
| 2 | `src/agvhito/src/sm/booting_state.cpp`: `BootingState::Execute` | Find the first boot unpause and the following map operations. |
| 3 | `src/agvhito/src/sm/execution_paused_state.cpp`: `OnEntry`, `Step`, `OnExit` | Find explicit pause and resume, and their relationship to state transitions. |
| 4 | `src/agvhito/src/sm/executing_order_state.cpp`: `OnEntry`, `VerifiedUnpause` | Find the redundant order-start unpause and subsequent map/order publication. |
| 5 | `src/agvhito/src/sm/idle_state.cpp`, `stopped_state.cpp`, `error_state.cpp`, `execution_recovery_state.cpp` | Inventory automatic pauses, software-stop activation, and software-stop release. Recovery is an additional case absent from the ticket's removal list. |
| 6 | `src/agvhito/src/agv.cpp`: `RequestPause`, `RequestResume`, `RequestSoftEStop`, `Step`; `src/agvhito/src/agv_ros.cpp`: `SetupServiceServers` | Separate state-machine policy from explicit stop services and terminal-failure behavior. |
| 7 | `src/core/yasminx/src/lifecycle_state.cpp`, `root_state_machine.cpp` | Understand cancellation, `OnExit`, the worker thread, and shutdown before adding a wait. |

Use the checkout to repeat the inventory before editing:

```bash
rg -n 'MakeStartPauseAction|MakeStopPauseAction|MakeSoftEStopAction|VerifiedUnpause' \
  src/agvhito/include src/agvhito/src
```

Also read `src/agvhito/include/agvhito/sm/state_strings.hpp` and `src/agvhito/src/sm/root.cpp`. The former defines C++ outcome-to-state transition maps; the latter registers concrete state objects with those maps. The architecture is compiled C++, not YAML. This proposal changes state behavior and helper functions while preserving the nine-state routing graph.

### 1.0 From executable `main()` to robot control: two host paths

**There is no hand-written AGV `main()` body in the supplied pack.** `agvhito` defines ROS components and asks a build helper to provide standalone executables. Production launches `proxy_node`; the supplied simulation launch instead starts the framework-owned `rclcpp_components/component_container`, which loads `SimAgvComponent`. `sim_agv_node` is also declared as a standalone executable, but that is not the executable selected by this simulation launch.

The exact standalone `main()` implementation, the `volley_add_component` macro implementation and the container's `main()` are outside the pack. Do not invent a source filename or executor selection for production. The diagram starts at these executable entry boundaries, then shows confirmed constructors, callbacks and the worker. Dotted edges cross process startup/plugin loading, timer dispatch or MQTT, so the whole diagram is a **call path**, not a single uninterrupted C++ stack trace.

```mermaid
flowchart TB
    P["Production: proxy_node main; bootstrap omitted"]
    S["Simulation: component_container main; framework source omitted"]
    PC["ProxyComponent constructor"]
    IM["InstanceManager constructor"]
    D["Discovery timer: AgvDiscoveryCallback"]
    TC["TryCreateAgv: registration and factsheet gates"]
    SC["SimAgvComponent constructor"]
    SA["SimAgv constructor: Agv base first"]
    A["Agv constructor: blackboard, MQTT, root"]
    R["AgvRos: timers and services"]
    W["Root Run: separate worker"]
    B["State execute: Booting or lifecycle hooks"]
    PUB["VerifiedPublish: assemble and send"]
    F["External HITO firmware; readiness mode not observed"]
    CY["ROS cycle: Agv Step and DrainSubscriptions"]
    BB["Blackboard state and action-status manager"]
    P -.-> PC
    PC --> IM
    IM -.-> D
    D --> TC
    TC --> A
    TC --> R
    S -.-> SC
    SC --> SA
    SA --> A
    SC --> R
    A --> W
    W --> B
    B --> PUB
    PUB -.-> F
    R -.-> CY
    F -.-> CY
    CY --> BB
    BB -.-> PUB
```

The firmware box describes the physical production path. In simulation, `SimAgv` and `SimMqttClient` replace that external robot/transport boundary; the shared adapter and state-machine code still execute. `AgvRos` contains per-robot mutually exclusive ROS callbacks, while the root worker runs independently.

#### Production entry selection and component registration

`src/launcher/launcher/central_nodes.py`, function `get_standalone_nodes(params)`, selects the executable only for non-simulation runs:

```python
def get_standalone_nodes(params):
    # ... other standalone nodes omitted ...
    if not params.get("is_simulation"):
        launch_description_entities.append(
            Node(
                package="agvhito",
                executable="proxy_node",
                name=PROXY_NAME,
                # ... parameters and remappings omitted ...
            )
        )
    return launch_description_entities
```

**File:** `src/agvhito/CMakeLists.txt`  
**Build scope:** proxy component/executable declaration, excerpt:

```cmake
volley_add_component(
  ${PROJECT_NAME}_proxy_component
  src/instance_manager.cpp
  src/proxy_component.cpp
  PLUGIN "volley::agvhito::ProxyComponent"
  EXECUTABLE proxy_node
  LINK_LIBRARIES
    ${PROJECT_NAME}_agv_ros_lib
    ${PROJECT_NAME}_comms_lib
    ${PROJECT_NAME}_topics_lib
)
```

`src/agvhito/src/proxy_component.cpp` ends with `RCLCPP_COMPONENTS_REGISTER_NODE(volley::agvhito::ProxyComponent)`. That registration exposes the component to the ROS loading machinery; it is not the robot's business-logic loop. The constructor creates the node and, after layout/connection configuration, its manager:

```cpp
// File: src/agvhito/src/proxy_component.cpp
ProxyComponent::ProxyComponent(const rclcpp::NodeOptions& options) {
  const auto node = std::make_shared<volley::Node>("hito_proxy", options);
  SetNode(node);
  // ... layout, firmware-version and connection parameter checks omitted ...
  instance_manager_ = std::make_unique<InstanceManager>(InstanceManager::Context {
      .node = node,
      // ... layout, connection options, speed and firmware specification omitted ...
  });
}
```

This shortened constructor preserves the relevant calls; it is not the complete aggregate initialization. `InstanceManager::InstanceManager(Context)` connects MQTT, initializes maps, subscribes to central registration state, and installs a two-second discovery timer. Discovery calls `TryCreateAgv`; it does not create a managed robot until central tracks it and its factsheet/firmware checks pass:

```cpp
// File: src/agvhito/src/instance_manager.cpp
InstanceManager::InstanceManager(Context context) : context_(std::move(context)) {
  // ... MQTT, maps, subscriptions and service client setup omitted ...
  agv_discovery_timer_ = context_.node->create_timer(
      2s, [this]() { AgvDiscoveryCallback(); });
  // ... health and factsheet timers omitted ...
}

void InstanceManager::AgvDiscoveryCallback() {
  // ... identify reported robots and populate pending_agvs_ omitted ...
  std::erase_if(pending_agvs_, [this](auto& entry) {
    return TryCreateAgv(entry.second);
  });
  // ... diagnostics omitted ...
}

bool InstanceManager::TryCreateAgv(PendingAgv& pending_agv) {
  const AgvId id = pending_agv.id;
  // ... central registration, factsheet and firmware gates omitted ...
  auto sub_node = context_.node->create_sub_node(std::format("agv/a{}", id));
  auto agv = std::make_unique<Agv>(id, Agv::Context {
      // ... clock, layout, publisher connection and map configuration omitted ...
  });
  agvs_.emplace(id, std::make_unique<AgvRos>(std::move(agv), std::move(sub_node)));
  return true;
}
```

#### Simulation entry selection

**File:** `src/launcher/launcher/sim_nodes.py`  
**Function:** `get_sim_launch_description_entities(...)`, relevant excerpts:

```python
def get_sim_launch_description_entities(
    params,
    initial_conditions,
    scenario_filepath,
    record_artifacts=True,
    artifacts_output_dir=None,
    artifact_basename=None,
    run_visualization=True,
    run_rviz=True,
    use_remote_meshes=False,
    remote_mesh_prefix=None,
    real_time_factor=1.0,
):
    # ... scenario loading and other component descriptions omitted ...
    for agv in agvs:
        agv_id = agv["id"]
        composable_nodes.append(
            ComposableNode(
                package="agvhito",
                plugin="volley::agvhito::sim::SimAgvComponent",
                # ... robot namespace and initial-state parameters omitted ...
            )
        )
    # ... other launch actions omitted ...
    sim_node = ComposableNodeContainer(
        name="sim_nodes",
        package="rclcpp_components",
        executable="component_container",
        arguments=["--executor-type", "multi-threaded"],
        # ... descriptions, namespace and output configuration omitted ...
    )
    launch_description_entities.append(sim_node)
    # ... remaining launch actions and return omitted ...
```

The launch description selects the process and plugin; its Python function is not a C++ `main()`. Plugin construction calls `SimAgvComponent::SimAgvComponent`, which builds maps/context/options, then constructs `SimAgv` and `SimAgvRos`. `SimAgv::SimAgv` first invokes the base `Agv` constructor, so the shared state-machine path begins there. It then initializes simulated robot state and its local protocol subscriptions.

#### After construction: two execution paths cooperate

The following adapter excerpt shows where ROS callbacks are installed. Production creates `AgvRos`; simulation uses `SimAgvRos`, derived from it.

```cpp
// File: src/agvhito/src/agv_ros.cpp
AgvRos::AgvRos(AgvUPtr agv, rclcpp::Node::SharedPtr node) :
    agv_(std::move(agv)),
    logger_(agv_->GetLogger()),
    node_(std::move(node)),
    callback_group_(node_->create_callback_group(
        rclcpp::CallbackGroupType::MutuallyExclusive)),
    is_terminal_(false) {
  SetupPublishers();
  SetupServiceServers();
  // ... initial version report omitted ...
}

void AgvRos::SetupPublishers() {
  timers_.cycle = node_->create_timer(
      kCyclePeriod, [this]() { CycleCallback(); }, callback_group_);
  // ... report publishers and other timers omitted ...
}

void AgvRos::CycleCallback() {
  const auto step = agv_->Step();
  // ... fault reporting and callback reset if Step fails omitted ...
}

// File: src/agvhito/src/agv.cpp
stdx::Result Agv::Step() {
  const auto pre_step = PreStep();
  if(!pre_step.has_value()) {
    return stdx::Unexpected(pre_step.error());
  }
  DrainSubscriptions();
  ReportMessageStaleness();
  // ... terminal/PostStep checks and failure handling omitted ...
  return step_result;
}
```

`kCyclePeriod` is 50 ms. `step_result` is declared in the omitted body; the excerpt is not a replacement implementation. The cycle drains feedback into shared trackers/managers. Independently, `RootStateMachine::Run` calls the graph on its worker, which invokes a concrete state's execution path and waits on those shared observations. **The ROS cycle does not directly call `BootingState::Execute` every 50 ms.**

To locate actual bootstrap bodies in a complete checkout, inspect `volley_add_component` and generated build sources rather than search for a nonexistent AGV handwritten main:

```bash
rg -n 'volley_add_component|int main\(' src build/agvhito
rg -n 'int main\(|executor|spin' build/agvhito
```

Run those in a built checkout; `build/agvhito` is not included in the pack and might not yet exist. The missing bootstrap implementation limits what this document can assert about production executor details, but not the confirmed business-logic path from the component constructor onward.

### 1.1 Read the existing execution as three separate acknowledgments

The following snippets are **existing source excerpts**, not the proposed replacements in sections 3–5. Every function excerpt identifies its file, qualified function name and actual signature. Some show only relevant statements inside that function; explicit omission comments mark missing code. Signatures and enclosing scopes are retained to make each excerpt easy to locate; omitted statements mean these are not replacement implementations. They are context, not standalone compilable examples.

| Boundary | Existing code observes | What that observation does not establish |
| --- | --- | --- |
| Host transport | The MQTT publish future returns `PublishResult::Ok`. | That firmware accepted/executed the action, or is ready for another operation. |
| Robot action report | The matching action ID reports `ActionStatus::FINISHED`. | That the firmware's delayed transition into `auto_run` is complete. |
| Reported state | A nonstale state satisfies `PausedIs(false)` and, at boot, no E-stop. | That maps/orders are accepted at this exact instant. |

**The central defect is an incorrect readiness condition.** The C++ does serialize calls, but serializing after an acknowledgment that arrives too early still permits the next command to race the firmware. Separately, automatic pause/software-stop commands keep otherwise inactive robots in firmware modes that the ticket says prevent low-power standby.

### 1.2 Startup creates shared data, transport, and a separate worker

The `Agv` constructor initializes the blackboard before subscribing and starting the state machine. `SetupStateMachine` constructs the registered graph and calls `Run`:

**File:** `src/agvhito/src/agv.cpp`  
**Function:** `Agv::Agv` (existing source excerpt)

```cpp
Agv::Agv(AgvId id, Context context) :
    id_(id),
    hito_serial_number_(std::to_string(id_)),
    context_(std::move(context)),
    instant_assembler_((nullptr != context_.instant_assembler)
                           ? context_.instant_assembler
                           : std::make_shared<InstantActionAssembler>(id_, context_.clock)),
    order_assembler_(std::make_unique<OrderAssembler>(
        OrderAssembler::Config {context_.layout, context_.floor_map_ids, context_.speed_limits})),
    blackboard_(std::make_shared<yasmin::Blackboard>()) {
  InitializeBlackboard();
  SetupMqtt();
  SetupStateMachine();
  // ... initial state-request publication omitted ...
}
```

**File:** `src/agvhito/src/agv.cpp`  
**Function:** `Agv::SetupStateMachine` (existing source excerpt)

```cpp
void Agv::SetupStateMachine() {
  state_machine_ = sm::MakeRootStateMachine(context_.clock, context_.logger);

  state_machine_->Run(blackboard_);
}
```

`InitializeBlackboard` installs the action-state manager, tracked robot state, action assembler, order queue and MQTT publisher. States read those shared objects by typed keys. `src/agvhito/src/sm/root.cpp` registers `BootingState` first and binds each concrete class to its transition map. `Run` starts the graph on its own worker:

**File:** `src/core/yasminx/src/root_state_machine.cpp`  
**Function:** `RootStateMachine::Run` (existing source excerpt)

```cpp
void RootStateMachine::Run(yasmin::Blackboard::SharedPtr blackboard) {
  // Return early if the thread is already running.
  if(thread_.joinable()) {
    return;
  }
  thread_ = std::jthread([this, blackboard = std::move(blackboard)]() {
    try {
      (*this)(blackboard);
    }
    catch(const yasmin::StateMachineCancelException&) {  // NOLINT(bugprone-empty-catch)
      // cancel_state_machine() aborts the execution loop by throwing, which is the expected clean shutdown.
    }
    catch(const std::exception& ex) {
      // In the event this exception was not caused by rclcpp signal handler, make sure to report the
      // exception
      if(!is_canceled() && rclcpp::ok()) {
        LOG_FATAL(context_.logger, "State machine '{}' aborted: {}", get_name(), ex.what());
        // Bypass StateMachine::cancel_state, which leaves is_canceled() false once the loop is dead.
        yasmin::State::cancel_state();  // NOLINT(bugprone-parent-virtual-call)
      }
    }
  });
}
```

Here `(*this)(blackboard)` invokes the upstream state-machine execution interface. The enclosing `std::jthread` belongs to the root; execution is asynchronous with respect to the constructor and ROS callbacks. The worker may wait for telemetry while the ROS cycle continues to drain incoming messages. This separation is why the proposed delay belongs on this worker: sleeping in a ROS callback could obstruct the very feedback needed for verification.

### 1.2a `State` versus `LifecycleState`: execution body versus polling lifecycle

The exact class spelling is **`LifecycleState`**, not `LifeCycleState`. There are three layers: upstream `yasmin::State`, Volley `yasminx::State`, and Volley `yasminx::LifecycleState`.

| Type | Source | What a concrete subclass implements | Who manages repeated work? |
| --- | --- | --- | --- |
| `yasmin::State` | Upstream YASMIN, implementation not supplied | Upstream execution contract. | Upstream routing/execution framework. |
| `yasminx::State` | `src/core/yasminx/include/yasminx/state.hpp` and `src/core/yasminx/src/state.cpp` | `Execute(blackboard, from_transition)` returning an outcome or structured error. | The concrete `Execute` body; the base does not add periodic polling. |
| `yasminx::LifecycleState` | `src/core/yasminx/include/yasminx/lifecycle_state.hpp` and `src/core/yasminx/src/lifecycle_state.cpp` | Required `Step`; optional `OnEntry` and `OnExit`. | A final `Execute` implementation owns entry, repeated steps, rate sleep and exit. |

`State` is not necessarily non-blocking or instantaneous. `BootingState` derives directly from it and performs its own telemetry waits and verified action/map calls inside one `Execute` invocation. The other eight AGV control states derive from `LifecycleState` because they repeatedly inspect state/requests until a condition yields a transition. This custom state lifecycle is unrelated to the managed ROS lifecycle-node API.

**File:** `src/core/yasminx/src/state.cpp`  
**Function/scope:** `State::execute`

```cpp
Outcome State::execute(yasmin::Blackboard::SharedPtr blackboard) {
  // Get the from transition that got us here (if it exists)
  Transition from_transition;
  if(const auto transition = bb::Get(*blackboard, bb::kTransition)) {
    from_transition = transition.value();
  }
  // Execute the state providing the transition details
  auto step = Execute(blackboard, from_transition);
  if(step.has_value()) {
    return std::move(step).value();
  }
  const yasminx::ErrorOutcome& error_outcome = step.error();
  const std::string state_name = GetName();
  LOG_ERROR(GetLogger(), "Caught error outcome in '{}': {}", state_name, error_outcome);
  // Put the error information on the shared blackboard
  bb::Set(*blackboard, bb::kStateError, {.state_name = state_name, .error = error_outcome.error});
  return error_outcome.outcome;
}
```

The lowercase `execute` is the framework entry point and is declared `final` in the header. It reads the previous transition and invokes the virtual capitalized `Execute`. Success returns the transition outcome; an error stores detailed diagnostic data on the blackboard and returns the error's routing outcome. A derived class overrides `Execute`, not `execute`.

**File:** `src/core/yasminx/src/lifecycle_state.cpp`  
**Function/scope:** `LifecycleState::Execute`

```cpp
stdx::Expected<Outcome, ErrorOutcome> LifecycleState::Execute(
    yasmin::Blackboard::SharedPtr blackboard, const Transition& from_transition) {
  step_rate_.reset();
  if(auto on_entry = OnEntry(blackboard, from_transition); !on_entry.has_value()) {
    return stdx::Unexpected(std::move(on_entry).error());
  }
  std::optional<Outcome> step_outcome;
  while(true) {
    if(is_canceled()) {
      step_outcome = kOutcomeCanceled;
      break;
    }
    auto step = Step(blackboard);
    if(!step.has_value()) {
      return stdx::Unexpected(std::move(step).error());
    }
    if(std::holds_alternative<Finished>(step.value())) {
      step_outcome = std::move(std::get<Finished>(step.value()).outcome);
      break;
    }
    step_rate_.sleep();
  }
  auto on_exit = OnExit(blackboard, std::move(step_outcome));
  // A canceled state must always transition on the canceled outcome, regardless of what OnExit returns
  if(is_canceled()) {
    if(!on_exit.has_value()) {
      LOG_WARN(GetLogger(), "Canceled state '{}' OnExit failed with {}, returning '{}'", GetName(),
          on_exit.error(), kOutcomeCanceled);
    }
    else if(on_exit.value() != kOutcomeCanceled) {
      LOG_WARN(GetLogger(), "Canceled state '{}' OnExit returned '{}', returning '{}'", GetName(),
          on_exit.value(), kOutcomeCanceled);
    }
    return kOutcomeCanceled;
  }
  if(!on_exit.has_value()) {
    return stdx::Unexpected(std::move(on_exit).error());
  }
  return std::move(on_exit).value();
}
```

Read this loop in order: reset rate → `OnEntry` → cancellation check → `Step` → either repeat after `step_rate_.sleep()` or extract `Finished.outcome` → `OnExit` → enforce canceled outcome if necessary. The AGV subclasses pass the 100 ms `kDefaultStepPeriod`; ROS feedback has its separate 50 ms cycle.

`StepResult` is a `std::variant<Continue, Finished>`; `Finished` carries `std::optional<Outcome>`. Defaults matter: `OnEntry` succeeds without work; default `OnExit` forwards a supplied outcome but returns a logic error if no outcome exists. Paused and recovery return `Finished{}` and therefore supply their final routing outcome in their own `OnExit`.

**`OnExit` is not guaranteed cleanup.** Entry or Step error returns before exit. Normal completion and loop cancellation call exit, and cancellation then overrides the returned outcome. This is why a canceled paused state needs to avoid unpause inside its exit hook; a later canceled result cannot retract an already sent command. Throwing exceptions is a separate worker failure path.

The proposed `UnpauseAndSettle` helper fits both kinds: Booting calls it inside `Execute`, while the paused lifecycle state calls it inside `OnExit`. Neither requires changing `yasminx` itself.

### 1.3 Boot unpauses and then immediately prepares map commands

After waiting for a fresh state message, `BootingState::Execute` sends this batch and checks observable state:

**File:** `src/agvhito/src/sm/booting_state.cpp`  
**Function:** `BootingState::Execute` (existing source excerpt)

```cpp
stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> BootingState::Execute(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& /*from_transition*/) {
  // ... preceding statements omitted ...
  LOG_INFO(GetLogger(),
      "Performing booting actions: clearing soft-estop, canceling previous order, setting pause");
  const auto boot_actions = VerifiedPublish(
      {
          MakeSoftEStopAction(false),
          MakeCancelOrderAction(),
          MakeExceptionClearAction(),
          MakeStopPauseAction(),
      },
      *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!boot_actions.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, boot_actions.error());
  }

  const auto ready = VerifyState(
      *blackboard, GetContext(), All({AnyEStopIs(false), PausedIs(false)}), [this] { return is_canceled(); });
  if(!ready.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, ready.error());
  }
  // ... remaining function body omitted ...
}
```

Read this in order: release software E-stop, request cancellation of the previous order, clear exceptions, and unpause. `MakeStopPauseAction()` means **deactivate pause**, despite the old log saying “setting pause.” `VerifiedPublish` waits for every action in this batch to report completion, then `VerifyState` checks no E-stop and not paused. There is no `auto_run` readiness check and no mandatory settling interval between those successes and map preparation.

The same function then builds a map-action vector containing `enableMap` and publishes it:

**File:** `src/agvhito/src/sm/booting_state.cpp`  
**Function:** `BootingState::Execute` (existing source excerpt)

```cpp
stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> BootingState::Execute(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& /*from_transition*/) {
  // ... preceding statements omitted ...
  LOG_INFO(GetLogger(), "Requesting to enable localization map '{}'", localization_map_id);
  map_actions.push_back(MakeEnableMapAction(localization_map_id, kHitoMapVersion));

// ... intervening source omitted ...

  const auto verify_map_actions =
      VerifiedPublish(map_actions, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!verify_map_actions.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, verify_map_actions.error());
  }
  // ... remaining function body omitted ...
}
```

The omitted code handles optional downloads, deletion of old maps and additional floor maps. The important boundary is **successful boot-action verification → successful state predicate → map publication**, all in one execution body. If firmware has reported unpause complete and `paused == false` before entering `auto_run`, both C++ checks can pass while `enableMap` is still forbidden. Waiting longer for a map failure afterward cannot prevent the too-early send.

### 1.4 The action factory creates a command; it does not send or wait

The factory's implementation makes the distinction visible:

**File:** `src/agvhito/include/agvhito/topics/instant_actions.hpp`  
**Function:** `MakeStopPauseAction` (existing source excerpt)

```cpp
inline vda5050_interfaces::v2::instant_actions::Action MakeStopPauseAction() {
  return MakeAction(kActionStopPause, vda5050_interfaces::v2::instant_actions::BlockingType::NONE);
}
```

`MakeAction` assigns a generated action ID and the supplied `BlockingType`. `MakeStopPauseAction` only returns a message value; publication happens later in `VerifiedPublish`. `BlockingType::NONE` does not insert a host-side barrier or provide a firmware readiness guarantee. The source explicitly uses NONE for instant actions so they can run concurrently with movement/running actions; a vector's element order should not be read as proof that every firmware side effect has settled before the next action.

`InstantActionAssembler::AssembleMessage` wraps that vector into an MQTT message for this robot. The payload is the serialized protocol envelope, with header ID, timestamp, robot serial number and action IDs:

**File:** `src/agvhito/src/instant_action_assembler.cpp`  
**Function:** `InstantActionAssembler::AssembleMessage` (existing source excerpt)

```cpp
stdx::Expected<mqtt::Message> InstantActionAssembler::AssembleMessage(std::vector<vinstant::Action> actions) {
  auto assembled_or = Assemble(std::move(actions));
  if(!assembled_or.has_value()) {
    return stdx::Unexpected(assembled_or.error());
  }

  return mqtt::Message {
      .topic = topic_,
      .payload = ToPayload(assembled_or.value()),
      .qos = mqtt::ToQoS(vinstant::kQos),
      .retained = false,
  };
}
```

This is a transport message, not a ROS service request. The production MQTT client sends it to firmware; simulation uses the same logical interface with local transport. Neither message assembly nor its `retained = false` setting changes unpause readiness.

### 1.5 `VerifiedPublish` first verifies transport, then reads robot action status

The instant-action overload saves the IDs before moving the vector into the assembler, so it can correlate each later firmware status to the command it sent. Its publication stage is:

**File:** `src/agvhito/src/sm/context_utils.cpp`  
**Function:** `VerifiedPublish` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::Error> VerifiedPublish(std::vector<vinstant::Action> actions,
    const yasmin::Blackboard& blackboard, const yasminx::StateContext& context,
    std::function<bool()> is_canceled) {
  // ... preceding statements omitted ...
  // Capture pending actions before the assembler consumes the vector
  std::vector<PendingAction> pending;
  pending.reserve(actions.size());
  for(const auto& action : actions) {
    pending.emplace_back(PendingAction {
        .id = action.action_id,
        .type = action.action_type,
    });
  }

// ... intervening source omitted ...

  // Publish the message and wait for a result ok result
  auto publish_future = mqtt_pub->Publish(std::move(message_or).value());
  if(publish_future.wait_for(kPublishTimeout) != std::future_status::ready) {
    return stdx::Unexpected(yasminx::Error {
        .type = kErrorMqttPublishTimeout,
        .message = std::format("Timed out after {} waiting for instant action publish", kPublishTimeout),
    });
  }
  if(const auto publish_result = publish_future.get(); publish_result != mqtt::PublishResult::Ok) {
    return stdx::Unexpected(yasminx::Error {
        .type = kErrorMqttPublishFailed,
        .message = std::format("Instant action publish failed: {}", mqtt::ToString(publish_result)),
    });
  }
  // ... remaining function body omitted ...
}
```

The first check is a future becoming ready within the existing 250 ms publication timeout; the second is the future's `PublishResult::Ok`. Failure here becomes a transport error. **Neither check is robot-action completion.** Only after transport success does the helper poll the action-state manager.

To see where that manager's observations come from, follow the return path. `Agv::Step` calls `DrainSubscriptions`; received protocol state messages update both the action-state manager and tracked state:

**File:** `src/agvhito/src/agv.cpp`  
**Function:** `Agv::DrainSubscriptions` (existing source excerpt)

```cpp
void Agv::DrainSubscriptions() {
  // ... common-message subscription omitted ...
  {
    auto state_msgs = Drain<vstate::State>(context_.logger, *mqtt_state_sub_, vstate::Validate);
    for(auto& state_msg : state_msgs) {
      yasminx::bb::Get(*blackboard_, bb::kKeyActionStateManager).value()->Upsert(state_msg.action_states);
      if(state_msg.agv_position.has_value()) {
        const auto& position = state_msg.agv_position.value();
        yasminx::bb::Get(*blackboard_, bb::kKeyPoseFilter)
            .value()
            ->Set(FromIso8601(state_msg.timestamp, context_.clock->get_clock_type()), position.x, position.y,
                position.theta);
      }
      yasminx::bb::Get(*blackboard_, bb::kKeyState).value()->Set(std::move(state_msg));
    }
  }
  // ... visualization subscription omitted ...
}
```

The manager records `action_id → action_status` under its mutex. Its query returns an optional status; absent means no status for that ID has been stored yet:

**File:** `src/agvhito/src/action_state_manager.cpp`  
**Function:** `ActionStateManager::GetActionStatus` (existing source excerpt)

```cpp
std::optional<vstate::ActionStatus> ActionStateManager::GetActionStatus(const std::string& action_id) const {
  std::lock_guard<std::mutex> lock(mutex_);
  if(!action_states_.contains(action_id)) {
    return {};
  }

  return action_states_.at(action_id);
}
```

That mutex makes the status lookup synchronized with insertion. It does not attach a readiness timestamp, wait for `auto_run`, or reinterpret firmware's meaning of `FINISHED`.

The decisive part of the verification loop is:

**File:** `src/agvhito/src/sm/context_utils.cpp`  
**Function:** `VerifiedPublish` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::Error> VerifiedPublish(std::vector<vinstant::Action> actions,
    const yasmin::Blackboard& blackboard, const yasminx::StateContext& context,
    std::function<bool()> is_canceled) {
  // ... preceding statements omitted ...
  const auto deadline = context.clock->now() + rclcpp::Duration(kVerifyTimeout);
  while(!is_canceled()) {
    const auto manager = yasminx::bb::Get(blackboard, bb::kKeyActionStateManager).value();
    for(auto it = pending.begin(); it != pending.end();) {
      const auto status_or = manager->GetActionStatus(it->id);
      if(!status_or.has_value()) {
        ++it;
        continue;
      }

      const auto& status = status_or.value();
      if(status == vstate::ActionStatus::FAILED) {
        return stdx::Unexpected(yasminx::Error {
            .type = kErrorActionStatusFailed,
            .message = std::format("Action {} ({}) reported FAILED", it->id, it->type),
        });
      }

      if(status == vstate::ActionStatus::FINISHED) {
        it = pending.erase(it);
      }
      else {
        ++it;
      }
    }

    if(pending.empty()) {
      return {};
    }
  // ... remaining function body omitted ...
  }
}
```

**The exact release point is `if(pending.empty()) { return {}; }`.** Every reported `FINISHED` removes one pending action; once the last is removed, the caller continues immediately. For firmware that reports `stopPause` complete too early, the host has correctly observed the action status but has incorrectly used it as readiness for the next kind of command.

The relevant constants in this same file are:

```cpp
constexpr auto kPollPeriod {100ms};
constexpr auto kPublishTimeout {250ms};
constexpr auto kVerifyTimeout {35s};
```

The existing `kPollPeriod` is 100 ms and `kVerifyTimeout` is 35 s. The poll sleep occurs only while something remains pending; it is after the success return. It therefore cannot enforce even a 100 ms delay **after** completion, much less the requested 200 ms. A completion already stored before the first lookup produces no poll sleep at all. Timeout limits failed waiting; it is not a minimum settling time.

### 1.6 `VerifyState` adds a predicate, not an independent readiness signal

The next boot check uses `VerifyState`, whose successful path is:

**File:** `src/agvhito/src/sm/context_utils.cpp`  
**Function:** `VerifyState` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::Error> VerifyState(const yasmin::Blackboard& blackboard,
    const yasminx::StateContext& context, StatePredicate predicate, std::function<bool()> is_canceled) {
  const auto start = context.clock->now();
  const auto deadline = start + rclcpp::Duration(kVerifyTimeout);
  while(!is_canceled()) {
    const auto state_or = yasminx::bb::Get(blackboard, bb::kKeyState).value()->GetIfNotStale();
    if(state_or.has_value() && predicate.holds(state_or.value())) {
      return {};
    }
  }
}
```

`GetIfNotStale` means the cached state meets the tracker’s age policy. It does not require a state message sampled after this particular unpause or after entry to `auto_run`. Once a cached fresh state satisfies the predicate, the function returns immediately.

For `PausedIs(false)`, the underlying helpers are:

**File:** `src/agvhito/include/agvhito/topics/state_predicates.hpp`  
**Function:** `PausedIs` (existing source excerpt)

```cpp
inline StatePredicate PausedIs(bool paused) {
  return {
      .description = paused ? "the AGV to report paused" : "the AGV to report un-paused",
      .holds = [paused](
                   const vda5050_interfaces::v2::state::State& state) { return IsPaused(state) == paused; },
  };
}
```

**File:** `src/agvhito/include/agvhito/topics/state.hpp`  
**Function:** `IsPaused` (existing source excerpt)

```cpp
inline bool IsPaused(const vda5050_interfaces::v2::state::State& state) {
  return state.paused.value_or(false);
}
```

The predicate checks a pause flag, not firmware run mode. Furthermore, an absent optional `paused` field is interpreted as false by `value_or(false)`. That existing convention is another reason not to equate “predicate passed” with positive evidence of readiness. The proposed delay complements this observation; it does not turn the flag into an authoritative signal.

### 1.7 Idle causes another unpause immediately before a new map/order

The current Idle entry deliberately pauses the robot and verifies that state:

**File:** `src/agvhito/src/sm/idle_state.cpp`  
**Function:** `IdleState::OnEntry` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> IdleState::OnEntry(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& /*transition*/) {
  // ... preceding statements omitted ...
  LOG_INFO(GetLogger(), "Requesting the AGV to pause");

  const auto pause =
      VerifiedPublish({MakeStartPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!pause.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, pause.error());
  }

  const auto state_paused =
      VerifyState(*blackboard, GetContext(), PausedIs(true), [this] { return is_canceled(); });
  if(!state_paused.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, state_paused.error());
  }

  LOG_INFO(GetLogger(), "AGV is currently paused");
  // ... remaining function body omitted ...
}
```

Later, Idle's `Step` sees a queued order and returns `order-requested`, routing to `ExecutingOrderState`. New-order entry reads a fresh state into the local `state` variable and performs this automatic unpause:

**File:** `src/agvhito/src/sm/executing_order_state.cpp`  
**Function:** `ExecutingOrderState::OnEntry` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> ExecutingOrderState::OnEntry(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& transition) {
  // ... preceding statements omitted ...
  if(IsPaused(state)) {
    LOG_INFO(GetLogger(), "Un-pausing and clearing past exceptions");

    if(const auto unpause = VerifiedUnpause(*blackboard); !unpause.has_value()) {
      return stdx::Unexpected(unpause.error());
    }
  }

  LOG_INFO(GetLogger(), "AGV is reporting un-paused");
  // ... remaining function body omitted ...
}
```

Its private helper publishes unpause plus exception-clear, then checks the same insufficient pause flag:

**File:** `src/agvhito/src/sm/executing_order_state.cpp`  
**Function:** `ExecutingOrderState::VerifiedUnpause` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> ExecutingOrderState::VerifiedUnpause(
    const yasmin::Blackboard& blackboard) {
  const auto clear_pause = VerifiedPublish({MakeStopPauseAction(), MakeExceptionClearAction()}, blackboard,
      GetContext(), [this] { return is_canceled(); });
  if(!clear_pause.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, clear_pause.error());
  }

  const auto unpaused_verified =
      VerifyState(blackboard, GetContext(), PausedIs(false), [this] { return is_canceled(); });
  if(!unpaused_verified.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, unpaused_verified.error());
  }

  return {};
}
```

After it returns, `OnEntry` may enable a different map and then publish the new order:

**File:** `src/agvhito/src/sm/executing_order_state.cpp`  
**Function:** `ExecutingOrderState::OnEntry` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> ExecutingOrderState::OnEntry(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& transition) {
  // ... preceding statements omitted ...
  // If new order map_id is not the enabled map id
  const std::string& order_map_id = new_order.map_id;
  const auto current_enabled_map_id = GetEnabledMapId(state);
  if(!current_enabled_map_id.has_value() || current_enabled_map_id.value() != order_map_id) {
    LOG_INFO(GetLogger(), "Enabling new order map '{}'", order_map_id);

    const auto enable_order_map = VerifiedPublish({MakeEnableMapAction(order_map_id, kHitoMapVersion)},
        *blackboard, GetContext(), [this] { return is_canceled(); });
    if(!enable_order_map.has_value()) {
      return yasminx::MakeUnexpected(kOutcomeErrored, enable_order_map.error());
    }
  }

// ... intervening source omitted ...

  const auto order_verified =
      VerifiedPublish(new_order, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!order_verified.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, order_verified.error());
  }
  // ... remaining function body omitted ...
}
```

**This is the second concrete race chain: automatic Idle pause → new-order unpause → predicate success → enableMap/order publication before `auto_run`.** If the map already matches, the new order itself is the first readiness-sensitive publication. Both cases need the firmware to accept new work.

Notice that `GetEnabledMapId(state)` uses the local snapshot obtained before `VerifiedUnpause`; the helper checks newer blackboard state without replacing that local variable. Refreshing this snapshot might improve map selection, but it does not solve the main problem: neither old nor new `paused == false` proves readiness.

The ticket's policy removes the automatic Idle pause and this order-start unpause. That avoids repeatedly entering the problematic firmware transition at each new order, while the remaining boot/resume unpauses receive the explicit guard.

### 1.8 Explicit resume follows a service, blackboard request and lifecycle exit

The ROS endpoints are registered to adapter methods rather than publishing robot commands directly:

**File:** `src/agvhito/src/agv_ros.cpp`  
**Function:** `AgvRos::SetupServiceServers` (existing source excerpt)

```cpp
void AgvRos::SetupServiceServers() {
  // ... preceding statements omitted ...
  srv_servers_.pause = create_trigger_service(kPauseServiceTopic, &Agv::RequestPause);
  srv_servers_.resume = create_trigger_service(kResumeServiceTopic, &Agv::RequestResume);
  // ... remaining function body omitted ...
}
```

The `create_trigger_service` callback invokes the member function and sets `response->success` from the returned result. `Agv::RequestResume` checks the current state/request slot and stores a Resume request:

**File:** `src/agvhito/src/agv.cpp`  
**Function:** `Agv::RequestResume` (existing source excerpt)

```cpp
stdx::Result Agv::RequestResume() {
  const auto current_state = state_machine_->get_current_state();
  // Order is already executing, can return early
  if(current_state == sm::kStateExecutingOrder) {
    return {};
  }

  if(current_state != sm::kStateExecutionPaused) {
    return stdx::Unexpected("Cannot resume outside of the '{}' state, current state is '{}'",
        sm::kStateExecutionPaused, current_state);
  }

  // There should not be a active request on the blackboard at this point
  // If there is one return unexpected
  if(const auto request = yasminx::bb::Get(*blackboard_, bb::kKeyRequest)) {
    return stdx::Unexpected(
        "Blackboard unexpectedly contains an active request w/ command '{}'", request.value());
  }

  yasminx::bb::Set(*blackboard_, bb::kKeyRequest, bb::Request::Resume);

  return {};
}
```

The service call can return before firmware sees an unpause. While in the paused state, the worker consumes the request and finishes the polling loop:

**File:** `src/agvhito/src/sm/execution_paused_state.cpp`  
**Function:** `ExecutionPausedState::Step` (existing source excerpt)

```cpp
stdx::Expected<yasminx::LifecycleState::StepResult, yasminx::ErrorOutcome> ExecutionPausedState::Step(
    yasmin::Blackboard::SharedPtr blackboard) {
  // ... preceding statements omitted ...
  if(bb::TakeRequest(*blackboard) == bb::Request::Resume) {
    LOG_INFO(GetLogger(), "Processed {} request", bb::Request::Resume);
    return yasminx::LifecycleState::Finished {};
  }
  // ... remaining function body omitted ...
}
```

`LifecycleState::Execute` detects `Finished`, then invokes the concrete `OnExit`. The current paused-state exit is:

**File:** `src/agvhito/src/sm/execution_paused_state.cpp`  
**Function:** `ExecutionPausedState::OnExit` (existing source excerpt)

```cpp
stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> ExecutionPausedState::OnExit(
    yasmin::Blackboard::SharedPtr blackboard, std::optional<yasminx::Outcome> /*step_outcome*/) {
  LOG_INFO(GetLogger(), "Un-pausing AGV to enable order execution");
  const auto unpause =
      VerifiedPublish({MakeStopPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!unpause.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, unpause.error());
  }

  return kOutcomeResumed;
}
```

It returns `resumed` as soon as action completion is verified, with no settle delay and no separate post-unpause state check. The transition table routes `resumed` back to `executing-order`.

Importantly, that re-entry **does not immediately send enableMap or republish the already accepted order**:

**File:** `src/agvhito/src/sm/executing_order_state.cpp`  
**Function:** `ExecutingOrderState::OnEntry` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> ExecutingOrderState::OnEntry(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& transition) {
  // ... preceding statements omitted ...
  const bool from_paused = (transition.from_state == kStateExecutionPaused);
  const bool from_recovery = (transition.from_state == kStateExecutionRecovery);
  if(from_paused || from_recovery) {
    return {};
  }
  // ... remaining function body omitted ...
}
```

An onboard order may physically resume as firmware becomes ready; the adapter resumes monitoring it. Later work still needs the barrier, but it would be inaccurate to portray every explicit Resume call as immediately issuing a map command. In this source snapshot, the unpause inside ExecutingOrderState belongs to the separate new-order entry path in section 1.7. This identifies the code path; the supplied log alone does not establish that firmware incidents used precisely this repository revision.

There is also an exit-lifecycle issue: the generic library calls `OnExit` on cancellation and overrides its result afterward. The current exit ignores `step_outcome`; `VerifiedPublish` does check `is_canceled`, but an explicit canceled-exit guard makes the intent clear and avoids relying solely on a helper's pre-send check. Section 4.2 proposes that guard and the shared delay.

### 1.9 Stopped/Error and recovery expose the separate policy problem

Stopped entry currently requests software E-stop before clearing queued orders:

**File:** `src/agvhito/src/sm/stopped_state.cpp`  
**Function:** `StoppedState::OnEntry` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> StoppedState::OnEntry(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& /*transition*/) {
  // ... preceding statements omitted ...
  LOG_INFO(GetLogger(), "Requesting soft-estop as we have entered the state");
  const auto estop = VerifiedPublish(
      {MakeSoftEStopAction(true)}, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!estop.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, estop.error());
  }
  // ... remaining function body omitted ...
}
```

Error entry also requests software E-stop and even tolerates failure of its verification:

**File:** `src/agvhito/src/sm/error_state.cpp`  
**Function:** `ErrorState::OnEntry` (existing source excerpt)

```cpp
stdx::Expected<void, yasminx::ErrorOutcome> ErrorState::OnEntry(
    yasmin::Blackboard::SharedPtr blackboard, const yasminx::Transition& transition) {
  // ... preceding statements omitted ...
  LOG_ERROR(GetLogger(), "Requesting Soft-EStop as the state machine has errored");

  const auto estop = VerifiedPublish(
      {MakeSoftEStopAction(true)}, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!estop.has_value()) {
    LOG_ERROR(GetLogger(),
        "Unable to verify AGV accepted Soft-EStop, continuing in error as this may be a connection issue");
  }
  // ... remaining function body omitted ...
}
```

These commands are not a race workaround; they deliberately select a firmware stop mode. Combined with Idle's pause, they explain why “no dispatched work” is not the same as “eligible for low-power standby.” The firmware standby restriction and battery attribution come from the ticket, not from a power model in this C++ code.

The source's additional recovery path sends pause on stale-data entry and unpause on recovery exit. Its unpause failure policy is especially important:

**File:** `src/agvhito/src/sm/execution_recovery_state.cpp`  
**Function:** `ExecutionRecoveryState::OnExit` (existing source excerpt)

```cpp
stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome> ExecutionRecoveryState::OnExit(
    yasmin::Blackboard::SharedPtr blackboard, std::optional<yasminx::Outcome> /*step_outcome*/) {
  // ... preceding statements omitted ...
  const auto unpause =
      VerifiedPublish({MakeStopPauseAction()}, *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!unpause.has_value()) {
    // During testing, the un-pause instant action was stuck in waiting, since we are un-pausing, we will
    // allow this to continue
    LOG_WARN(GetLogger(), "Continuing even with un-pause verification error, {}", unpause.error());
  }

  return kOutcomeRecovered;
}
```

It can return `recovered` after a failed verification, rather than requiring successful unpause. Updating only boot and `ExecutionPausedState` would leave this unguarded unpause in place. The strict two-case proposal removes recovery pause/unpause; keeping it requires an explicit policy exception plus the shared guard and a defined failure route.

### 1.10 Connect the code to the observed firmware failure

The ticket reports that firmware marks `stopPause` complete before entering `auto_run`. In the supplied trace, EnableMap failed at 05:44:34.331 and `auto_run` followed at 05:44:34.336: a roughly 5 ms too-early map operation. The trace does not itself show when the host observed `FINISHED`. The aggregate 8–18 ms mid-order and 45–105 ms boot timings measure the interval after StopPause as reported in the ticket; they should not be silently relabeled as measured host-observation latencies.

| Existing observation or policy | Its limitation or failure | Proposed response |
| --- | --- | --- |
| `PublishResult::Ok` completes the transport stage. | It proves transport success only. Existing code correctly goes on to action-status verification, but that still does not prove readiness. | Preserve transport/action verification and add the readiness guard. |
| `FINISHED` means all consequences of unpause have settled. | Firmware reports completion before it accepts maps/orders in `auto_run`. | After verified unpause, enforce the named 200 ms elapsed-time barrier. |
| `PausedIs(false)` supplies the missing readiness guarantee. | It checks a cached pause flag, with missing flag interpreted as false; it does not check run state. | Retain useful state checks while treating the delay as a temporary guard, not proof. |
| The 100 ms poll interval provides a settling delay. | Success returns before the sleep; status may already be available at the first poll. | Start a separate deadline after successful unpause verification. |
| Routine pause/software E-stop is harmless while idle. | The ticket says these modes prevent firmware standby. | Remove routine commands from idle/stopped/error and resolve recovery policy explicitly. |
| The service returns success when it accepts Resume. | The callback stores a request; the worker publishes later. The response does not confirm physical resumption. | Preserve and document asynchronous acceptance semantics. |

This is why the implementation should begin with `context_utils.cpp` and its callers: the problem crosses transport, action-status reporting, cached telemetry, state lifecycle and firmware mode. A state graph shows legal routing, but cannot reveal that the particular acknowledgment used to permit the next command arrives too early.

### 1.10a Where does “firmware reports stopPause FINISHED immediately” appear?

**The physical firmware handler is not in this pack.** The statement is an observation in the ticket/logs. The Volley host code does not cause or specify the physical firmware's early completion; it receives an action-status report and uses that report as a condition to proceed.

The code connection is: `MakeStopPauseAction` creates an ID-bearing command → `VerifiedPublish` sends it → physical firmware responds on its state topic → `Agv::DrainSubscriptions` stores `state_msg.action_states` in `ActionStateManager` → `VerifiedPublish` reads the matching ID → a `FINISHED` value removes it from `pending` → empty pending set returns success. Sections 1.4–1.6 show each host-side step.

The closest **local equivalent**, which helps identify the protocol behavior but is not vendor firmware, is the simulator handler:

**File:** `src/agvhito/src/sim/sim_agv.cpp`  
**Function/scope:** `SimAgv::HandleActionStopPause`

```cpp
ActionResult SimAgv::HandleActionStopPause() {
  if(state_.estop) {
    return {.status = vstate::ActionStatus::FAILED, .error = {}};
  }

  state_.paused = false;

  // If not estopped and pause is released HITO clears the current errors
  state_.errors.clear();

  return {.status = vstate::ActionStatus::FINISHED, .error = {}};
}
```

It changes `state_.paused`, clears errors and returns `FINISHED` in the same call, except that it fails while E-stopped. This `FINISHED` return is an action result, not yet a received host telemetry message. The simulator subsequently puts that result into its stored action states:

**File:** `src/agvhito/src/sim/sim_agv.cpp`  
**Function/scope:** `SimAgv::UpdateActionState`

```cpp
void SimAgv::UpdateActionState(const vinstant::Action& action, const ActionResult& result) {
  if(result.error.has_value()) {
    AddError(result.error.value());
  }
  state_.action_states[action.action_id] =
      MakeActionState(action.action_id, action.action_type, result.status);
}
```

`SimAgv::BuildState()` includes `ToActionStates(state_.action_states)` in the protocol state; `SimAgv::PublishState()` serializes that state and publishes it through the local MQTT transport. The adapter then consumes it through the same `DrainSubscriptions` path as production.

So there are three distinct source locations to keep straight: vendor firmware's handler is **unavailable**; `SimAgv::HandleActionStopPause` is the simulated producer of immediate completion; `VerifiedPublish` is the host consumer whose early success permits the race. Changing the host delay works around observed firmware behavior; it does not change when vendor firmware marks the action finished.

### 1.10b Where does this code detect `auto_run`?

**It does not detect that firmware mode in the inspected sources.** A search of the supplied AGV, launcher and `yasminx` source finds no `auto_run` predicate/guard and no map/order gate based on that mode. Boot checks `AnyEStopIs(false)` and `PausedIs(false)`. New-order unpause checks `PausedIs(false)`. Neither is a firmware readiness signal.

The only use of `operating_mode` found in this AGV snapshot is a simulator report assignment:

```cpp
// File: src/agvhito/src/sim/sim_agv.cpp
// Function: SimAgv::BuildState() -- selected report fields only.
vstate::State SimAgv::BuildState() {
  // ... timestamp, optional pause flag and safety state preparation omitted ...
  return vstate::State {
      // ... other protocol fields omitted ...
      .paused = paused,
      .operating_mode = vstate::OperatingMode::AUTOMATIC,
      // ... position, actions, battery and error fields omitted ...
  };
}
```

That value is emitted unconditionally by the simulator; it is **not** a check by the adapter and does not model a delayed transition into firmware `auto_run`. A protocol “automatic operating mode” and a vendor's internal `auto_run` readiness state cannot be equated without a documented firmware contract. Adding `operating_mode == AUTOMATIC` as a guessed readiness check would therefore not establish the needed guarantee.

The ticket's “accepts maps/orders only after auto_run” is a firmware-side acceptance rule inferred from its logs. The host learns that it sent too early only through failures, such as an action status of `FAILED`; it currently has no positive readiness observation. The proposed 200 ms guard substitutes elapsed time for this missing signal. It must not be described as detecting `auto_run`.

To replace the delay later, ask firmware for a concrete exposed field or event whose documented meaning is **maps/orders are now accepted**, identify its protocol topic/type, and correlate its freshness with the unpause just issued. Until that contract exists, do not invent a run-mode field or infer readiness from a name.

## 2. Define the intended policy before deleting code

| Situation | Current snapshot behavior | Proposed normal lifecycle behavior |
| --- | --- | --- |
| Boot | Batch releases software E-stop, cancels previous order, clears exceptions, and unpauses; checks state; sends maps. | Keep preparation, publish unpause separately, wait 200 ms after observing its completion, verify unpaused/no E-stop, then send maps. |
| Idle entry | Clears software E-stop if present, pauses, verifies paused, possibly cancels previous order. | No automatic stop release or pause. Preserve safety/state checks; cancel unexpected traversal and verify physical traversal completion. |
| Stopped entry | Activates software E-stop and clears queued orders. | Clear queued orders without activating software E-stop. “Stopped” becomes an adapter dispatch state, not a firmware stop mode. |
| Error entry | Attempts software E-stop, logs diagnostics, clears queued orders. | Keep diagnostics, queue clearing and recovery behavior; remove software E-stop activation. An Error state alone will no longer guarantee a robot stop. |
| New order entry | If paused, unpauses and clears exceptions before map/order publication. | Remove automatic unpause and its private helper. Reject unexpected pause/E-stop before publishing; require boot or explicit resume to establish the normal unpaused condition. |
| Explicit pause while executing | Publishes `startPause`; waits for Resume; publishes `stopPause` on exit. | Preserve pause/resume; resume uses the shared unpause barrier. |
| Stale-telemetry recovery | Pauses on entry; unpauses on exit, tolerating verification failure. | For the strict two-case policy, remove both actions; recovery waits for fresh data without commanding pause/resume. This changes behavior during telemetry loss and needs an explicit engineering decision. |
| Explicit severe stop request | `Agv::RequestSoftEStop()` publishes a software E-stop. | Preserve this requested emergency-stop interface. It is not an automatic idle/stopped/error policy. |
| Terminal state-machine or `PostStep` failure | `Agv::Step()` sends a best-effort software E-stop. | Preserve the existing terminal-failure response; document it as an exception to normal lifecycle policy. |

The ticket's “only two cases” cannot literally mean deleting every software-stop command: it also asks to release software E-stop at boot, and the public severe-stop interface is separate. Recommended interpretation: **two normal lifecycle pause/unpause contexts; no routine software-stop activation just because the adapter is idle, stopped, or errored**. If the team instead intends to remove the explicit stop interface or terminal-failure response, that is a separate contract change.

There is a second ambiguity: `RequestPause()` currently returns success without doing anything outside `executing-order`. Keep that behavior for this ticket and correct its misleading comment; making an idle pause request physically pause the robot would require a new idle pause policy, graph behavior, and resume contract.

## 3. Put the barrier in `agvhito`, not in generic `yasminx`

Add a helper named `UnpauseAndSettle` to the existing `sm/context_utils` module. Put `kUnpauseSettlePeriod` in `sm/timing.hpp`. Call the helper from exactly two places: boot and `ExecutionPausedState::OnExit`.

Why this location:

- The delay compensates for HITO firmware behavior, not a general state-machine lifecycle rule.
- `context_utils` already contains action publication, state predicates, cancellation callbacks and result handling.
- A single helper prevents one resume path from omitting the delay.
- Waiting here serializes subsequent commands on the existing state-machine worker without sleeping inside ROS service callbacks or adding threads.
- Leaving generic `VerifiedPublish` unchanged avoids inserting 200 ms delays after unrelated actions or order publications.

### 3.1 Define the time invariant

Let $t_f$ be the host's monotonic time immediately after `VerifiedPublish(stopPause)` returns successfully. Let $t_n$ be the time of the next normal state-machine map/action/order publication. The required lower bound is:

$$
t_n-t_f\ge\tau,\qquad \tau=0.200\ \mathrm{s}.
$$

Starting at the **observed completion**, rather than at publication, is conservative. Transport and verification time do not count toward the 200 ms barrier. A slow completion therefore does not accidentally consume the entire guard interval.

Use `std::chrono::steady_clock` for this new wait. It measures elapsed host time and avoids wall-clock adjustments or advancing ROS simulated time releasing a physical firmware guard early. This deliberately imposes 200 ms of real elapsed time even in accelerated simulation. Existing `VerifiedPublish` and `VerifyState` still use `context.clock`; this proposal does not fix their simulated-clock timeout behavior.

“Before sending anything else” should mean no subsequent **normal state-machine control publication** until the helper succeeds. It is not a global mutex over the MQTT client: ROS stop callbacks, initial state requests and manager traffic use other call paths. Do not delay emergency-stop requests behind this barrier. If the firmware needs all diagnostic traffic suppressed too, inventory those publishers and design a broader per-robot outbound gate as separate scope.

### 3.2 Proposed declarations

In `src/agvhito/include/agvhito/sm/timing.hpp`, retain existing constants and add:

```cpp
/// Temporary HITO readiness guard after stopPause reports FINISHED.
/// Remove when firmware provides an authoritative readiness signal (SW2-876).
inline constexpr std::chrono::milliseconds kUnpauseSettlePeriod {200};
```

In `src/agvhito/include/agvhito/sm/context_utils.hpp`, add within `volley::agvhito::sm`:

```cpp
/// Publish stopPause by itself, verify FINISHED, wait the wall-clock
/// readiness guard, then verify fresh unpaused/no-E-stop state.
/// Does not clear an E-stop or exceptions and does not resume on cancellation.
[[nodiscard]] stdx::Expected<void, yasminx::Error> UnpauseAndSettle(
    const yasmin::Blackboard& blackboard,
    const yasminx::StateContext& context,
    std::function<bool()> is_canceled);
```

### 3.3 Proposed helper implementation

This is concrete proposed C++ using the supplied interfaces; it has not been compiled against the full workspace. In `src/agvhito/src/sm/context_utils.cpp`, add `<algorithm>`, `<chrono>`, `<thread>`, `<rclcpp/utilities.hpp>`, and `"agvhito/topics/instant_actions.hpp"` as direct includes. Existing includes already provide the blackboard, result/error types, timing constants and predicates through the module header.

Add the private wait in the existing anonymous namespace:

```cpp
constexpr auto kUnpauseCancelPollPeriod {10ms};

stdx::Expected<void, yasminx::Error> WaitForUnpauseSettle(
    const std::function<bool()>& is_canceled) {
  using Clock = std::chrono::steady_clock;
  const auto deadline = Clock::now() + kUnpauseSettlePeriod;
  const auto poll_period =
      std::chrono::duration_cast<Clock::duration>(kUnpauseCancelPollPeriod);

  while(true) {
    // Check interruption before success, including after the final sleep.
    if(is_canceled()) {
      return stdx::Unexpected(yasminx::Error {
          .type = kErrorCanceled,
          .message = "Canceled during the HITO unpause settle period",
      });
    }

    const auto now = Clock::now();
    if(now >= deadline) {
      return {};
    }

    std::this_thread::sleep_for(std::min(deadline - now, poll_period));
  }
}
```

Add the public helper in `volley::agvhito::sm`, outside that anonymous namespace:

```cpp
stdx::Expected<void, yasminx::Error> UnpauseAndSettle(
    const yasmin::Blackboard& blackboard,
    const yasminx::StateContext& context,
    std::function<bool()> is_canceled) {
  const auto interrupted = [&is_canceled] {
    return is_canceled() || !rclcpp::ok();
  };

  // Do not put another command in the same batch as stopPause.
  const auto published = VerifiedPublish(
      {MakeStopPauseAction()}, blackboard, context, interrupted);
  if(!published.has_value()) {
    return stdx::Unexpected(published.error());
  }

  LOG_INFO(context.logger, "Waiting {} for HITO unpause to settle",
      kUnpauseSettlePeriod);

  const auto settled = WaitForUnpauseSettle(interrupted);
  if(!settled.has_value()) {
    return stdx::Unexpected(settled.error());
  }

  // This checks observable state after the guard; it is not auto_run proof.
  return VerifyState(blackboard, context,
      All({AnyEStopIs(false), PausedIs(false)}), interrupted);
}
```

The helper starts the deadline slightly after successful action verification, which strengthens the lower bound. The loop checks elapsed time again after each sleep; early wakeups cannot shorten the guard. Ten-millisecond slices provide a cancellation check approximately every 10 ms while sleeping, subject to host scheduling. They are not a guaranteed cancellation-latency bound for publication or verification: those existing operations have their own waits.

The callback is passed as `std::function<bool()>`, matching existing helpers. The `interrupted` lambda captures a reference to this function, but every use is synchronous and completes before `UnpauseAndSettle` returns. Call sites capture their state object's `this`; they execute on the state-machine worker while the root owns the state. No callback is retained by the new helper.

`rclcpp::ok()` follows the supplied root's global-context convention. If production uses a non-default ROS context, use its shutdown predicate instead; do not assume the global context represents every node. `std::jthread` ownership and joining remain in `yasminx`; its stop token is not the cancellation mechanism used by these helpers.

## 4. Change boot first, then explicit resume

### 4.1 `src/agvhito/src/sm/booting_state.cpp`

In `BootingState::Execute`, split the current four-action batch. Retain software-stop release, prior-order cancellation, and exception clearing. Remove `MakeStopPauseAction()` from that batch and call the new helper before reading maps or sending any map actions:

```cpp
// File: src/agvhito/src/sm/booting_state.cpp
// Function: BootingState::Execute(blackboard, from_transition) -- proposed body excerpt.
LOG_INFO(GetLogger(),
    "Boot preparation: release soft E-stop, cancel prior order, clear exceptions");

const auto boot_actions = VerifiedPublish(
    {MakeSoftEStopAction(false), MakeCancelOrderAction(),
        MakeExceptionClearAction()},
    *blackboard, GetContext(), [this] { return is_canceled(); });
if(!boot_actions.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, boot_actions.error());
}

const auto unpaused = UnpauseAndSettle(
    *blackboard, GetContext(), [this] { return is_canceled(); });
if(!unpaused.has_value()) {
  return yasminx::MakeUnexpected(kOutcomeErrored, unpaused.error());
}

// Existing fresh-state read, expected-map calculation and map actions follow.
```

The helper absorbs the existing boot `VerifyState(All({AnyEStopIs(false), PausedIs(false)}))`; remove that duplicate block. Correct the old log that says “setting pause” even though it sends `stopPause`. Log “unpause guard complete; preparing map actions” after helper success, without claiming actual firmware readiness.

The preliminary batch preserves existing behavior; its action types use non-blocking protocol semantics, so vector order alone is not proof of firmware execution order. If clearing exceptions while the software stop is still engaged can fail on real firmware, serialize software-stop release and its state verification before cancel/exception-clear. That is a separately testable boot ordering concern, not something the new unpause delay fixes.

### 4.2 `src/agvhito/src/sm/execution_paused_state.cpp`

Keep `OnEntry` publishing `MakeStartPauseAction()` and keep `Step` consuming Resume. Replace `OnExit` with the shared unpause helper, and guard cancellation **before** sending anything:

```cpp
stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome>
ExecutionPausedState::OnExit(
    yasmin::Blackboard::SharedPtr blackboard,
    std::optional<yasminx::Outcome> step_outcome) {
  if(is_canceled() ||
      (step_outcome.has_value() &&
          step_outcome.value() == yasminx::kOutcomeCanceled)) {
    return yasminx::kOutcomeCanceled;
  }

  const auto unpaused = UnpauseAndSettle(
      *blackboard, GetContext(), [this] { return is_canceled(); });
  if(!unpaused.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, unpaused.error());
  }

  return kOutcomeResumed;
}
```

Why the guard matters: `yasminx::LifecycleState::Execute` calls `OnExit` after cancellation as well as normal completion. It later forces the returned outcome to cancellation, but that does not undo a command already sent by `OnExit`. The exit must therefore avoid publishing unpause during shutdown. The helper independently checks interruption before publication and during the delay. A cancellation racing immediately after the pre-publication check cannot retract an already sent action; this proposal does not provide atomic command/cancellation arbitration.

Normal resume reaches `Finished{}` without a carried outcome, so this overridden `OnExit` must return `kOutcomeResumed` itself. Do not remove the override: default `LifecycleState::OnExit` treats an empty outcome as a logic error.

The existing paused path resumes an already accepted order. `ExecutingOrderState::OnEntry` returns early when entered from paused or recovery, so it does not republish that order. A firmware resume may start existing motion **during the guard**; the guard prevents later commands, not physical resumption of an accepted order.

```mermaid
sequenceDiagram
    participant Caller as ROS service caller
    participant Adapter as AGV adapter
    participant Worker as State-machine worker
    participant Robot as HITO firmware
    Caller->>Adapter: resume request
    Adapter->>Adapter: Store Resume in blackboard
    Adapter-->>Caller: Request accepted
    Worker->>Worker: Consume Resume and enter OnExit
    Worker->>Robot: stopPause alone
    Robot-->>Worker: FINISHED observed
    Note over Worker,Robot: Firmware may still be entering auto_run
    Worker->>Worker: Wait at least 200 ms of steady elapsed time
    Robot-->>Worker: State telemetry continues independently
    Worker->>Worker: Verify fresh unpaused and no E-stop
    alt Guard and state checks succeed
        Worker->>Worker: Return resumed and re-enter execution
        Note over Worker,Robot: Subsequent normal publications are now permitted
    else Verification fails
        Worker->>Worker: Return errored; do not send follow-on commands
    else State canceled
        Worker->>Worker: Exit without further commands
    end
```

## 5. Remove automatic commands, preserving useful checks

### 5.1 Idle: stop pausing and stop clearing software E-stop

In `src/agvhito/src/sm/idle_state.cpp`, `IdleState::OnEntry` currently does more than the ticket's referenced pause line. Remove both the pause/paused-verification block and the automatic `MakeSoftEStopAction(false)`/exception-clear block. Otherwise boot would not be the only lifecycle software-stop release.

Retain the fresh-state check and replace the hard-stop-only check with existing `CheckEStopClear(state)` so a software stop is not silently cleared. Add `kErrorUnexpectedPause {"unexpected-pause"}` to `src/agvhito/include/agvhito/sm/error.hpp` for diagnostics. Return `kOutcomeErrored` if the robot is unexpectedly paused; do not invent an automatic unpause.

For the retained “unexpected active traversal” cancellation block, add `VerifyState(TraversalComplete())` after `VerifiedPublish(cancelOrder)`. Previously the pause provided immediate stopping behavior; merely deleting it leaves a gap because cancel acknowledgment is not proof that deceleration has completed.

Representative replacement logic after obtaining fresh `state`:

```cpp
// File: src/agvhito/src/sm/idle_state.cpp
// Function: IdleState::OnEntry(blackboard, transition) -- proposed body excerpt.
if(const auto clear = CheckEStopClear(state); !clear.has_value()) {
  return stdx::Unexpected(clear.error());
}
if(IsPaused(state)) {
  return yasminx::MakeUnexpected(kOutcomeErrored, yasminx::Error {
      .type = kErrorUnexpectedPause,
      .message = "Unexpected paused AGV on idle entry; refusing automatic unpause",
  });
}

if(!IsTraversalComplete(state)) {
  const auto canceled = VerifiedPublish(
      {MakeCancelOrderAction()}, *blackboard, GetContext(),
      [this] { return is_canceled(); });
  if(!canceled.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, canceled.error());
  }
  const auto stopped = VerifyState(*blackboard, GetContext(),
      TraversalComplete(), [this] { return is_canceled(); });
  if(!stopped.has_value()) {
    return yasminx::MakeUnexpected(kOutcomeErrored, stopped.error());
  }
}
return {};
```

This specifically returns `errored`, rather than the hardware/software E-stop outcomes, for unexpected pause. Existing Idle transition maps already support all three relevant error outcomes. `VerifyState` has the existing 35 s timeout; a timeout enters Error without an additional software-stop command under the proposed policy. This remains a failure to establish physical stop, not a successful idle state.

### 5.2 Stopped: retain queue clearing

In `src/agvhito/src/sm/stopped_state.cpp`, remove the log, `VerifiedPublish(MakeSoftEStopAction(true))`, and its error return from `StoppedState::OnEntry`. Keep clearing `bb::kKeyOrderQueue` and keep the localization/Activate logic in `Step`.

Controlled stopping during execution still follows `executing-order → canceling-order → stopped`. `CancelingOrderState` publishes cancel and waits for `IsTraversalComplete`. Remove neither this path nor its physical completion check. By contrast, entering Stopped from Error does not prove a current onboard order was canceled; that risk is addressed below, not by renaming the state.

### 5.3 Error: retain diagnostics and recovery delay

In `src/agvhito/src/sm/error_state.cpp`, remove the software-stop publication and its “continuing in error” warning. Retain transition/error/state logging, pending-queue clearing, the entry timestamp, waiting for fresh state and hardware E-stop release, and the existing five-second recovery behavior.

Be explicit in code comments: entering Error is no longer an instruction to stop the robot. Clearing `OrderQueue` affects local pending orders. Removing `bb::kKeyActiveOrder` during recovery removes local tracking; it does not cancel the robot's accepted order. A stale-data or protocol failure can therefore have a different physical consequence after this change.

### 5.4 Executing order: remove both helper declaration and definition

In `src/agvhito/src/sm/executing_order_state.cpp`:

1. Delete the `if(IsPaused(state))` unpause block from `OnEntry`.
2. Delete the misleading unconditional “AGV is reporting un-paused” log.
3. Delete the `ExecutingOrderState::VerifiedUnpause` definition at the end of the file.
4. After obtaining fresh state and **before map/order publication**, add `CheckEStopClear(state)` and the same unexpected-pause error guard shown for Idle.
5. Preserve map selection, order publication, tracking, and early-return behavior for paused/recovery re-entry.

In `src/agvhito/include/agvhito/sm/executing_order_state.hpp`, delete the private `VerifiedUnpause` declaration. Leaving a declaration behind is misleading even if it does not cause a linker error once unused.

The old private helper also sent `MakeExceptionClearAction()`. Its removal intentionally removes that order-start exception-clearing behavior. Boot still clears exceptions; resume previously did not separately clear them. Verify on hardware that `stopPause` clears the expected pause-related exception, rather than assuming the simulator's behavior is firmware proof.

The new guards are on the new-order entry path. They do not redesign every race with external stops or every telemetry check during ongoing execution. Existing `Step` E-stop checks remain.

### 5.5 Recovery: the additional required policy change

In `src/agvhito/src/sm/execution_recovery_state.cpp`, remove `MakeStartPauseAction()` from `OnEntry` and `MakeStopPauseAction()` from `OnExit`. Keep recovery's freshness checks for state, filtered pose and common message. Keep `OnEntry` as a diagnostic-only method, or remove that override and declaration to inherit the no-op entry.

Keep the `OnExit` override because recovery also returns `Finished{}` without an outcome:

```cpp
stdx::Expected<yasminx::Outcome, yasminx::ErrorOutcome>
ExecutionRecoveryState::OnExit(
    yasmin::Blackboard::SharedPtr /*blackboard*/,
    std::optional<yasminx::Outcome> step_outcome) {
  if(is_canceled() ||
      (step_outcome.has_value() &&
          step_outcome.value() == yasminx::kOutcomeCanceled)) {
    return yasminx::kOutcomeCanceled;
  }
  return kOutcomeRecovered;
}
```

If the team elects to retain automatic recovery pause, state the exception to the ticket clearly and route its unpause through `UnpauseAndSettle`, propagating failures instead of logging and continuing. That alternative has **three** lifecycle contexts and does not satisfy the strict two-case policy. Leaving the current recovery unpause untouched would also violate the “after every unpause” guard requirement.

### 5.6 Public service comments and stop exceptions

In `src/agvhito/src/agv.cpp`, correct `RequestPause()`'s comment to say it queues a pause only while executing and otherwise returns a no-op success. Do not describe all other states as paused or E-stopped after this change. Leave `RequestResume()`'s state checks in place.

Keep `RequestSoftEStop()` and the terminal-failure software-stop path in `Agv::Step()`. They remain intentional exceptions, and an explicit stop can still prevent firmware standby. A robot that retains a manually requested software stop is therefore not guaranteed to enter standby under this ticket.

No ROS interface definition needs to change. The `pause`/`resume` services are relative-name `std_srvs::srv::Trigger` endpoints in `agv_ros.cpp`; the adapter stores a blackboard request and returns success. A successful response is **request acceptance or an existing no-op case**, not confirmation that pause/unpause and the 200 ms barrier have completed.

## 6. File change checklist

| Repository path | Proposed change |
| --- | --- |
| `src/agvhito/include/agvhito/sm/timing.hpp` | Add documented `kUnpauseSettlePeriod {200}` milliseconds. |
| `src/agvhito/include/agvhito/sm/context_utils.hpp` | Declare `UnpauseAndSettle` and its verified contract. |
| `src/agvhito/src/sm/context_utils.cpp` | Add monotonic, cancellation-aware wait and shared unpause helper. |
| `src/agvhito/src/sm/booting_state.cpp` | Split boot unpause from preparation batch; call helper before maps; fix logs and remove duplicate state verification. |
| `src/agvhito/src/sm/execution_paused_state.cpp` | Use helper on normal resume; guard cancellation before publication. |
| `src/agvhito/src/sm/idle_state.cpp` | Remove automatic pause/software-stop release; retain safety checks and cancel unexpected traversal with completion verification. |
| `src/agvhito/src/sm/stopped_state.cpp` | Remove automatic software-stop activation; retain queue clearing. |
| `src/agvhito/src/sm/error_state.cpp` | Remove automatic software-stop activation; retain diagnostics/recovery; explain changed physical semantics. |
| `src/agvhito/src/sm/executing_order_state.cpp` | Remove order-start unpause/helper; guard unexpected pause/E-stop before new publications. |
| `src/agvhito/include/agvhito/sm/executing_order_state.hpp` | Remove obsolete private helper declaration. |
| `src/agvhito/include/agvhito/sm/error.hpp` | Add diagnostic `kErrorUnexpectedPause`. |
| `src/agvhito/src/sm/execution_recovery_state.cpp` | For strict policy, remove pause/unpause; preserve freshness polling and recovered/canceled exit outcomes. |
| `src/agvhito/include/agvhito/sm/execution_recovery_state.hpp` | Change only if removing the now-empty `OnEntry` override. |
| `src/agvhito/src/agv.cpp` | Update misleading pause comment; preserve explicit severe-stop and terminal-failure behavior. |
| `src/agvhito/CMakeLists.txt` | Add a state-machine test target linked to `${PROJECT_NAME}_state_machine_lib`. |
| `src/agvhito/test/sm/test_unpause_and_settle.cpp` | Proposed new tests for action ordering, elapsed guard and failure/cancellation. |
| `src/agvhito/test/sm/test_pause_policy.cpp` | Proposed new tests for state-entry policy, resume, recovery and cancellation. |

`state_strings.hpp`, `root.cpp`, `yasminx`, launcher configuration and ROS service schemas should not need changes for this design. No YAML delay parameter is needed: the ticket requests a temporary fixed workaround constant. Adding runtime configurability would add validation and deployment variance without establishing real readiness.

## 7. Tests that demonstrate the behavioral change

The AGV Repomix omits test bodies. Existing build declarations establish test targets but not their contents. The supplied `yasminx` tests confirm lifecycle behavior, including cancellation overriding an exit outcome; they do not prove that a derived exit hook avoided sending an unpause action.

Add a focused test target inside `if(BUILD_TESTING)`:

```cmake
volley_add_gtest(
  ${PROJECT_NAME}_state_machine_tests
  DIRECTORY test/sm
  LINK_LIBRARIES
    ${PROJECT_NAME}_state_machine_lib
)
```

Check `volley_add_gtest`'s actual directory-globbing behavior in the checkout. If the existing `${PROJECT_NAME}_core_tests` recursively collects `test/sm`, exclude the new directory from that target or use explicitly listed sources. Do not guess the wrapper macro's exclusion API from this pack.

### 7.1 Build a recording transport fixture

Use the checkout's `mqtt::IPublisher` interface and existing test doubles if available. The blackboard fixture supplies a real action assembler, an action-state manager, and a fresh tracked state. A recording publisher captures outgoing action/order payloads, IDs, and host monotonic timestamps; its publish future returns the intended transport result. Feed completion statuses for the **actual generated action IDs**, rather than treating a successful future as robot acceptance.

The extracted pack does not include the `IPublisher` declaration or existing test doubles, so this proposal does not invent a concrete subclass signature. Inspect those before implementing the fixture. Drive fresh telemetry asynchronously while the worker is waiting; a fixture that only updates state on the blocked test thread can deadlock or time out for the wrong reason.

| Test | Stimulus | Required observation |
| --- | --- | --- |
| Boot barrier | Firmware double marks unpause `FINISHED` immediately but remains unavailable for 105 ms. | No map/control publication until at least 200 ms after that completion is observable. Unpause is not batched with any follow-on action. |
| Resume barrier | Resume an accepted order; mark unpause complete immediately. | `kOutcomeResumed` is not returned before the guard and state check succeed. Existing order is not republished on paused re-entry. |
| Slow completion | Delay action completion independently of transport success. | Guard starts after successful action verification, not at send time; elapsed delay is not counted twice incorrectly or consumed early. |
| Action failure | Transport fails, times out, or robot reports `FAILED`. | Return the corresponding error; do not publish maps/order or return resumed. |
| Cancellation before exit | Cancel a paused state/root. | No `stopPause` is published by `OnExit`. |
| Cancellation during guard | Cancel after unpause completion but before deadline. | Helper returns canceled error; no normal follow-on command. Already sent unpause cannot be withdrawn. |
| ROS shutdown | Shutdown while guarding. | New wait exits through interruption; no subsequent normal publications. |
| Observable state failure | Guard completes but fresh state remains paused/E-stopped or becomes stale. | State verification fails/times out and no normal follow-on command is allowed. |
| Idle/stopped/error policy | Enter each state with appropriate fixtures. | No automatic `startPause` or software-stop activation. Idle does not automatically release software stop. Existing queue/diagnostic behavior remains. |
| Idle unexpected traversal | Cancel reports `FINISHED` before deceleration finishes. | Idle entry does not succeed until `TraversalComplete` holds. |
| Unexpected pause at order start | Present a paused fresh state on new-order entry. | Diagnostic error; no automatic unpause, enable-map or order publication. |
| Explicit pause/resume | Request Pause while executing, then Resume. | One pause action; one guarded unpause; correct existing outcomes. |
| Telemetry recovery | Make execution state/pose/common data stale, then fresh. | Under strict policy, recovery publishes neither pause nor unpause and retains its freshness gates. |
| Existing severe stop | Use the severe-stop service and terminal-failure path. | Existing software-stop behavior remains available; controlled stop still waits for traversal completion. |

Measure the guard's **lower bound** with a steady clock; avoid brittle tests demanding completion at exactly 200 ms or under a narrow upper bound. Several real-time guard tests add only fractions of a second. If the test suite later needs deterministic virtual-time testing, extract an internal deadline/wait abstraction; do not add broad clock injection to every state solely for this small workaround.

### 7.2 Why normal simulation cannot reproduce the ticket alone

`src/agvhito/src/sim/sim_agv.cpp` immediately clears its pause flag and reports `FINISHED` in `HandleActionStopPause`. It has no delayed `auto_run` readiness gate. Its battery model likewise does not implement the firmware standby behavior described by SW2-815.

Prefer a test-specific firmware/transport double that reports early completion and rejects map/order requests before a configured readiness deadline. It should model the two separate events: **action finished** and **commands accepted**. Keep production simulation unchanged unless a separately requested simulator feature justifies adding standby/readiness modeling. A passing standard simulation is useful regression evidence, not proof that the physical firmware race or overnight battery loss is resolved.

### 7.3 Build and run in the actual workspace

After implementing against the checkout, use its normal build environment:

```bash
colcon build --packages-up-to agvhito --cmake-args -DBUILD_TESTING=ON
colcon test --packages-select agvhito
colcon test-result --verbose
```

These are proposed commands, not results from this documentation task. Run existing AGV tests as well as the new state-machine target, then exercise boot, pause/resume and controlled stop in simulation before hardware validation.

## 8. Risks and design issues to resolve before rollout

| Risk / issue | Why it matters | Proposed treatment |
| --- | --- | --- |
| **Error no longer commands a stop** | An accepted onboard order can outlive local queue clearing or removal of active-order tracking. Entering Stopped after five seconds does not prove the robot is stationary. | Enumerate which failure classes can occur during motion and establish the firmware/external stopping contract. If a cancel/controlled-stop action is required on selected errors, define it separately rather than claiming queue clearing stops the robot. |
| **Recovery no longer pauses on stale telemetry** | The robot may continue its accepted order while central lacks trustworthy feedback. | The strict policy needs explicit agreement about firmware communication-loss handling and allowed blind-motion behavior. Retaining recovery pause is an alternative only if documented as a third case with guarded unpause. |
| **A preexisting software stop remains engaged** | Removing Idle's auto-clear can prevent recovery/activation from restoring operation and can still prevent standby. | Document the supported release path. In this design it is boot; do not silently remove an operator's requested stop during Idle. Test restart/release behavior and identify whether a separate explicit release API is needed. |
| **Hardware E-stop cannot be released in software** | Boot's release command affects software stop, while the predicate requires no E-stop of any kind. | Preserve the hardware distinction and failure diagnostics. Do not treat a fixed delay as permission to override a physical stop. |
| **200 ms is not a readiness signal** | Firmware load/version could produce a longer gap than the observed maximum. | Correlate host action IDs with firmware logs during rollout. Keep a named, documented workaround; request an authoritative readiness field/event from firmware. |
| **Other publishers bypass the barrier** | The root worker serializes its own control sequence, not every ROS callback or manager request. | Audit outbound paths; keep emergency stops immediate. Define exactly which diagnostic traffic firmware tolerates rather than adding an indiscriminate MQTT lock. |
| **Explicit resume can begin motion before guard completion** | An already accepted order can resume when firmware enters `auto_run`. | Explain that the barrier protects follow-on command readiness; it is not a delayed physical-resume mechanism. |
| **Existing clock-based verification can still stall** | `VerifiedPublish`/`VerifyState` use `context.clock` deadlines/sleeps; the new steady wait does not change those. | Keep cancellation tests and record this separate limitation. Do not claim the complete helper has a 200 ms maximum duration. |
| **Blocking waits and shutdown** | Root destruction joins its worker. A monolithic sleep or non-cooperative verification can delay shutdown. | Use short cancellation-aware slices and existing canceled-result convention; test cancellation. No new worker or detached callback. |
| **Stop/cancellation races remain** | A check immediately before sending is not atomic with an asynchronous stop request. | Preserve normal concurrency behavior; test representative races and avoid claiming the helper is a global safety arbiter. |
| **Blackboard request slot is not a queue** | Pause/Resume occupy a shared request key; `TakeRequest` reads and removes it. | Keep existing API semantics and test repeated/conflicting requests. Do not promise ordered processing of arbitrary concurrent service requests. |
| **Terminal failure can repeatedly activate software stop** | `Agv::Step` may run again while the machine remains terminal. | Preserve failure behavior in this ticket; inspect repeated publications and battery effects as a separate fault-latching/backoff issue. |
| **Removing order-start exception clearing** | Firmware errors formerly cleared there may persist. | Test supported firmware behavior after explicit resume and boot. Do not retain a hidden unpause simply to clear errors. |
| **Standby is not established by adapter state** | The ticket attributes battery loss to firmware mode. Simulator fractions/adapter Stopped state are not firmware low-power evidence. | Observe actual standby entry and battery behavior on hardware; inspect whether ongoing diagnostic traffic also prevents standby. |

The first two risks are material behavior changes, not implementation details to hide in a helper. A proposal can be complete while clearly distinguishing the requested policy from the physical stopping guarantees that must be established with the team and firmware supplier.

## 9. Suggested implementation and rollout order

1. Inventory the current checkout and confirm the recovery/explicit-stop interpretation against the ticket. Capture current boot and resume command order with IDs.
2. Add the constant/helper and tests. Update boot and explicit resume first; this isolates the readiness barrier from pause-policy deletions.
3. Remove Idle/Stopped/Error/order-start automatic commands, plus the strict-policy recovery commands. Add unexpected-pause checks and Idle traversal completion verification. Update comments and clean unused includes/declarations.
4. Run focused and existing tests, then simulation regression. Re-run the pause/unpause inventory: `MakeStopPauseAction` should appear in the action factory and the shared helper, with only boot and explicit-resume callers; `MakeStartPauseAction` should remain in the factory and explicit-paused entry.
5. Validate on a controlled physical robot: boot with the relevant map scenarios, repeated pause/resume, queued/new-map orders, controlled stop, operator E-stop, and telemetry recovery under the agreed contract. Correlate command/action IDs and both clocks; the supplied firmware timestamp is UTC+8, so normalize it before comparing central timestamps.
6. Roll out narrowly, monitor map/action failures and actual low-power entry, then compare overnight battery behavior. If rollback is needed, record that restoring the previous policy also restores the known standby issue; avoid treating rollback as resolution of SW2-815.

Do not artificially force a dangerous telemetry outage or stop scenario on an operating parking system; use the team's controlled hardware validation procedure. This proposal does not request deployment or change an active robot.

## 10. Definition of done and questions for the team

The implementation is reviewable when the shared helper enforces the measured lower bound, both normal unpause callers use it, canceled exit cannot deliberately send unpause, and tests demonstrate the absence of routine pause/software-stop commands in the removed paths. The ticket is behaviorally validated only when hardware accepts the first post-unpause map/order operations and eligible idle robots reach standby.

Resolve these concrete questions in review:

- Does “only two cases” include removal of telemetry-recovery pause/unpause? The source currently has that extra case.
- Are explicit severe-stop requests and terminal-failure software stops intentional exceptions? This proposal preserves them.
- What ensures physical stopping when entering Error during an active onboard order, after removing automatic software E-stop?
- What is the allowed robot behavior while execution telemetry is stale? What firmware communication-loss behavior is actually configured?
- How should an operator-requested software stop be released without an automatic Idle release? Is a restart sufficient or is a separate release operation required?
- Does the preliminary boot batch need stronger ordering between software-stop release, cancel, and exception-clear on supported firmware?
- Is the 200 ms guard required only for normal control publications, or must diagnostic traffic also wait? Emergency stops should remain immediate.
- What firmware readiness signal will replace the workaround, and how will its correlation/freshness be established?

The eventual firmware fix should replace the elapsed-time barrier with an authoritative, fresh readiness check while keeping centralized unpause handling. It should not turn `FINISHED` or `paused == false` into readiness assumptions again.
