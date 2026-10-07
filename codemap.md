# Volley code map

Generated 2026-10-06 from `/home/jon-gonzales/volley` (commit `fdd205e6`).
Every package in `src/`, bottom-up by stack layer: description, dependencies, files with line counts, declared types, components, launch contents and tests. Meshes, vendored JS, layouts/scenarios data and Terraform are summarized, not listed.

Legend: `file (lines) — declared types · "doc brief"`; components = `RCLCPP_COMPONENTS_REGISTER_NODE`.

## Repository top level

- `.claude/` — 2 files
- `.colcon/` — 5 files
- `.devcontainer/` — 6 files
  - `devcontainer.json`
  - `resources/` — 1 files
  - `scripts/` — 4 files: initialize, post-attach, post-create, utils
- `.github/` — 26 files
  - `.sccache.toml`
  - `actions/` — 4 files
  - `scripts/` — 3 files: ci-failure-report, ci-failure-summary, docker-bake-retag
  - `workflows/` — 18 files: .call-build, .call-builder-image, .call-coverage, .call-docker-tags, .call-docs, .call-ecr-auth, .call-post-static-analysis, .call-pre-static-analysis, .call-runtime-images, .call-site-scenario-tests, .call-system-tests, .call-unit-test-matrix, .call-unit-tests, ci, nightly-tests, release-tag, release-trigger, weekly-test-report
- `.vscode/` — 2 files
- `artifacts/` — 2 files
- `controller_webview/` — 460 files
  - `3d/` — 2 files
  - `README.md`
  - `action/` — 17 files: actionRetrieve, bayConfirmInsert, bayConfirmRetrieve, moveAgvToNode, moveTrayToNode, overridePayloadOnTray, overrideTrayPose, pauseSystem, reparkTray, setBayReadinessRatio, startSystem, stopEvCharging, stopSystem, toggleAgv, toggleMode, toggleNode, toggleTray
  - `css/` — 9 files (vendored)
  - `fonts/` — 2 files (vendored)
  - `images/` — 6 files
  - `includes/` — 14 files (mostly vendored; own code listed below)
  - `index.php`
  - `js/` — 404 files (mostly vendored; own code listed below)
    - `noc/`: noc3DMenus.js, noc3DRendering.js, nocControlHandler.js, nocTransactionDisplay.js
  - `requests/` — 5 files: controlManagement, locationsObjects, rosoutMessages, schedulerState, versionInfo
- `docker/` — 6 files
  - `Dockerfile`
  - `docker-bake.ci.hcl`
  - `docker-bake.hcl`
  - `noc.Dockerfile`
  - `resources/` — 2 files
- `docs/` — 39 files
  - `architecture/` — 9 files: agv, apt-proxy, bay, discovery-server, docker-build, sim, system-tests, vda5050, vrc
  - `assets/` — 3 files
  - `coverage.md`
  - `deprecated/` — 9 files: aws, central, data_and_plotting, deployment, network-topology, overview, ros-nodes, scheduler, tech-debt
  - `glossary.md`
  - `guides/` — 8 files: contributing, cpp-style, getting-started, mac-setup, release-workflow, simulation, simulation-in-cloud, volley-cmake
  - `hooks/` — 1 files
  - `index.md`
  - `papers/` — 3 files
  - `tips-and-tricks/` — 3 files: colcon, garage-cmds, ros
- `scripts/` — 8 files
  - `check_branch_name.sh`
  - `set-discovery-server`
  - `set-domain-id`
  - `util_constants.sh`
  - `util_core.sh`
  - `util_export.sh`
  - `util_log.sh`
  - `util_path.sh`
- `src/` — 1329 files
- `tools/` — 19 files
  - `BayPLCscript.py` — class BayDoorController, def bayStatus
  - `__init__.py`
  - `build_central_api_for_coverage.sh`
  - `build_coverage.sh`
  - `charge_ev_by_tray_id.py` — def callback
  - `clang-tidy-diff-hook`
  - `demo/` — 6 files: demo_agvsetup, demo_cmds, demo_prep, demo_run, localhost5000, readme_how_to_script_the_demo
  - `extract_plancalls_from_bagfile.py`
  - `layout_to_node_schedule.py` — def create_node_schedule · "Convert from garage layout yaml, to node schedule csv file."
  - `layout_to_scenario.py` — def charger_nodes_to_agvs, def single_agv_first_node, def single_payload, def parking_nodes_to_trays_payloads, def create_trays_in_bays, def clear_parking_space, def start_in_manual_events, def start_in_auto_events, def move_agv_to_each_node_events, def insert_single, … · "Input a layout yaml file.  Output generated scenario yaml file(s)."
  - `local-runtime-deploy`
  - `node_schedule_to_layout.py` — class LayoutBuilderException, def get_parking_window_id, def create_node, def process_filename, def create_layout · "CLI Tool used to translate node schedule csv files exported from Revit."
  - `replay_fast.sh`
  - `run_pylint.sh`
- `.clang-format`
- `.clang-tidy`
- `.clangd`
- `.commitlintrc.yaml`
- `.dockerignore`
- `.editorconfig`
- `.env.python`
- `.envrc`
- `.envrc.local`
- `.gcovr.cfg`
- `.gersemirc`
- `.gitattributes`
- `.gitignore`
- `.markdownlint-cli2.yaml`
- `.octocov.yaml`
- `.pylintrc`
- `.sccache.toml`
- `.shellcheckrc`
- `.taplo.toml`
- `.yamllint`
- `README.md`
- `mkdocs.yml`
- `prek.toml`
- `pyproject.toml`
- `uv.lock`

## Packages (bottom-up)

### Layer 0 · build

#### `volley_cmake` · `src/infrastructure/volley_cmake` · ament_cmake · 0 lines
> Shared Volley CMake configuration for ROS packages
- **depends on (workspace):** —
- **depends on (external):** —
- **used by:** — (leaf)
- **files:**
  - `cmake/`
    - `volley_add_component.cmake` (91)
    - `volley_add_executable.cmake` (63)
    - `volley_add_gtest.cmake` (90)
    - `volley_add_library.cmake` (70)
    - `volley_ament_auto_package.cmake` (6)
    - `volley_arguments.cmake` (60)
    - `volley_glob_sources.cmake` (61)
    - `volley_package.cmake` (89)
    - `volley_verify_headers.cmake` (58)
  - `CMakeLists.txt` (9)
  - `package.xml` (19)
  - `volley_cmake-extras.cmake` (9)

### Layer 1 · core utilities

#### `dds_discovery` · `src/infrastructure/dds_discovery` · ament_cmake · 198 lines
> DDS discovery related tools and applications.
- **depends on (workspace):** rclcppx
- **depends on (external):** fastdds, rclcpp
- **used by:** — (leaf)
- **files:**
  - `src/`
    - `discovery_probe.cpp` (198) — main() · "Environment variable holding the discovery server locators."
  - `CMakeLists.txt` (9)
  - `package.xml` (19)

#### `mqtt` · `src/communication/mqtt` · ament_cmake · 1,178 lines
> MQTT client wrapper around PahoMqttCpp
- **depends on (workspace):** —
- **depends on (external):** ament_cmake_gtest, rcpputils
- **used by:** agvhito, agvhito_tools
- **files:**
  - `include/`
    - `mqtt/`
      - `client.hpp` (77) — struct LifecycleCallbacks, class Client, using ConnectHandler, using ReconnectHandler, using DisconnectHandler, using ErrorHandler, using ClientSPtr, using ClientUPtr · "Lifecycle callback function triggered on the first successful broker connection."
      - `connection_options.hpp` (19) — struct ConnectionOptions · "MQTT client connection options."
      - `i_client.hpp` (42) — class IClient, using IClientSPtr, using IClientUPtr · "Interface for a MQTT client."
      - `i_publisher.hpp` (26) — class IPublisher, using IPublisherSPtr, using IPublisherUPtr · "Interface for a MQTT publisher."
      - `i_subscription.hpp` (37) — class ISubscription, using ISubscriptionSPtr · "Interface for a MQTT subscription."
      - `message.hpp` (25) — struct Message, enum QoS, using MessageSPtrConst
      - `results.hpp` (50) — enum ConnectResult, enum PublishResult
      - `subscription_options.hpp` (15) — struct SubscriptionOptions · "Options for a subscription handle."
      - `topic_utils.hpp` (25) — "@return The nth slash-separated segment of @p topic, or an empty string if @p index is out of range."
  - `src/`
    - `client.cpp` (35)
    - `client_impl.cpp` (346)
    - `client_impl.hpp` (112) — class ClientImpl, struct PendingPublish, struct SubscriptionEntry
    - `publisher.cpp` (23)
    - `publisher.hpp` (30) — class Publisher · "Concrete MQTT publisher."
    - `subscription.cpp` (74)
    - `subscription.hpp` (81) — class Subscription, using SubscriptionSPtr · "Concrete MQTT subscription."
    - `topic_utils.cpp` (69)
  - `test/` — 1 files, 3 test cases: test_topic_utils
  - `CMakeLists.txt` (15)
  - `package.xml` (24)

#### `otel` · `src/data/otel` · ament_cmake · 480 lines
> OpenTelemetry C++ and ROS SDK
- **depends on (workspace):** —
- **depends on (external):** rclcpp
- **used by:** central
- **files:**
  - `examples/`
    - `metrics_usage_example.cpp` (46) — main()
  - `include/`
    - `otel/`
      - `instruments/`
        - `counter.hpp` (36) — class Counter · "No-op until minted by MetricsClient::MakeCounter, then wraps an OTel counter."
        - `histogram.hpp` (36) — class Histogram · "No-op until minted by MetricsClient::MakeHistogram, then wraps an OTel histogram."
      - `attributes.hpp` (19) — using Attrs, using AttrsView · "Attribute set attached to a measurement."
      - `instrument_concepts.hpp` (20) — "Values OTel accepts for counters, non-negative (uint64 or double)."
      - `metrics_client.hpp` (123) — struct HistogramBoundaries, struct MetricsOptions, class MetricsClient · "Explicit bucket boundaries and measurement unit for a histogram instrument."
      - `metrics_client_ros.hpp` (15) — "Builds a metrics client, reading the endpoint from the node's @p endpoint_param"
  - `src/`
    - `metrics_client.cpp` (106)
    - `metrics_client_ros.cpp` (20)
    - `registered_gauge.hpp` (59) — class RegisteredGaugeBase, class RegisteredGauge · "Type-erased base so MetricsClient can own registered gauges of mixed value type."
  - `CMakeLists.txt` (27)
  - `package.xml` (17)

#### `rclcppx` · `src/core/rclcppx` · ament_cmake · 543 lines
> Volley rclcpp extensions
- **depends on (workspace):** —
- **depends on (external):** ament_cmake_gtest, example_interfaces, rclcpp, rclcpp_action
- **used by:** dds_discovery, yasminx, bay_interfaces, common_ros, motion_planner, scheduler, agvhito, bay, central, lift, vecs, vrc, sim
- **files:**
  - `include/`
    - `rclcppx/`
      - `interface_factories.hpp` (105) — "Pointer-like handle to a node, e.g. `rclcpp::Node::SharedPtr` or `rclcpp::Node*`."
      - `introspection.hpp` (48) — "Name of the node parameter that selects the introspection mode."
      - `logging.hpp` (133)
      - `qos.hpp` (80) — class BestEffortQoS, class LatchedQoS, class ReliableQoS · "@return @p profile with its history depth replaced by @p depth."
      - `topic.hpp` (19) — struct Topic, using Message · "Topic name, message type, and the QoS shared by its publishers and subscribers."
  - `test/` — 2 files, 13 test cases: test_interface_factories, test_qos
  - `CMakeLists.txt` (14)
  - `package.xml` (22)

#### `stdx` · `src/core/stdx` · ament_cmake · 100 lines
> Volley standard library extensions
- **depends on (workspace):** —
- **depends on (external):** ament_cmake_gtest, rcpputils
- **used by:** yasminx, vda5050_interfaces, common_ros, scheduler, agvhito, bay, vrc, agvhito_tools
- **files:**
  - `include/`
    - `stdx/`
      - `expected.hpp` (48) — using Expected, using Result · "Convenience aliases for tl::expected with string errors."
  - `test/` — 1 files, 6 test cases: test_expected
  - `CMakeLists.txt` (13)
  - `package.xml` (20)

#### `yasminx` · `src/core/yasminx` · ament_cmake · 1,032 lines
> Volley specific extension of the YASMIN Finite State Machine (FSM) library.
- **depends on (workspace):** rclcppx, stdx
- **depends on (external):** ament_cmake_gtest, rclcpp, yasmin
- **used by:** agvhito
- **files:**
  - `include/`
    - `yasminx/`
      - `blackboard_constants.hpp` (23) — struct Key, using value_type · "Strongly-typed blackboard key that pairs a name with the value type stored under it."
      - `blackboard_utils.hpp` (50) — "@return The value stored under @p key in @p blackboard, or nullopt if @p key is not present."
      - `error.hpp` (37) — struct Error, struct ErrorOutcome, struct StateError · "Error type used on internal state logical error."
      - `format.hpp` (37) — struct std
      - `lifecycle_state.hpp` (67) — class LifecycleState, struct Continue, struct Finished, using StepResult · "A @ref State with an OnEntry/Step/OnExit lifecycle looped at a fixed step period."
      - `outcome.hpp` (16) — using Outcome · "Alias for outcome type explicitness."
      - `root_state_machine.hpp` (71) — class RootStateMachine, struct SigintGuard, struct sigaction, enum SigintHandling, using RootStateMachineUPtr · "Controls how SIGINT is handled around state machine construction."
      - `state.hpp` (55) — class State · "Base state class that contains context."
      - `state_context.hpp` (14) — struct StateContext · "Required context needed by base @ref State."
      - `transition.hpp` (17) — struct Transition · "Information related to a state transition."
  - `src/`
    - `lifecycle_state.cpp` (90)
    - `root_state_machine.cpp` (105)
    - `state.cpp` (40)
  - `test/` — 6 files, 16 test cases: test_blackboard_utils, test_lifecycle_state, test_root_state_machine, test_ros_env, test_state, test_utils
  - `CMakeLists.txt` (22)
  - `package.xml` (23)

### Layer 1 · shared libraries

#### `common` · `src/common` · ament_cmake · 5,600 lines
> Common code and common utilities
- **depends on (workspace):** —
- **depends on (external):** ament_cmake, ament_cmake_gtest, eigen, rclcpp, rmw
- **used by:** common_ros, cost_functions, planner_core, motion_planner, scheduler, agvhito, bay, central, lift, vecs, vis, vrc, agvhito_tools, sim, central_api
- **files:**
  - `include/`
    - `common/`
      - `agv_can_ids.hpp` (28) — enum CanIds
      - `command_status.hpp` (18) — enum CommandStatus
      - `constants.hpp` (80)
      - `devices_agv.hpp` (63) — enum Side, enum SatelliteId, enum MotorId, enum LiftId, enum ClutchId, enum LineSensorId, enum RfidSensorId
      - `devices_bay.hpp` (97) — struct DoorHash, enum LoadCellId, enum IoLinkDevices, enum Door, enum OdpDoor, enum OdpSensor
      - `enum.hpp` (545) — struct CharCaseInsensitiveEqualTo, struct CharEqualTo, class StaticString, struct IsScopedEnum, struct IsUnscopedEnum, struct UnderlyingType, using values_t
      - `geometry_utils.hpp` (103) — struct Segment
      - `heartbeat_monitor.hpp` (60) — class HeartbeatMonitor
      - `math_utils.hpp` (293) — struct vec2f, struct Angle
      - `md5.hpp` (27) — "Get the MD5 sum of the given @ref str contents."
      - `modbus.hpp` (125) — class Modbus, enum ExceptionCode, enum FunctionCode, using LogFn
      - `modbus_mock.hpp` (56) — class ModbusMock
      - `modbus_tcp.hpp` (33) — class ModbusTCP, struct timeval
      - `motion_sim.hpp` (132) — struct Motion1D, class MotionSim, using vec2, using vec3, using mat3
      - `system_utils.hpp` (28)
      - `topic.hpp` (58) — struct Topic
      - `topics_agv.hpp` (30) — enum TopicAgv
      - `topics_bay.hpp` (32) — enum TopicBay
      - `topics_central.hpp` (54) — enum TopicCentral
      - `topics_common.hpp` (11)
      - `topics_sim.hpp` (21) — enum TopicSim
      - `topics_vecs.hpp` (21) — enum TopicVecs
      - `topics_visualizer.hpp` (48) — enum TopicVisualizer
      - `types.hpp` (7) — using BoolStringPair
      - `utils.hpp` (50)
  - `src/`
    - `devices_agv.cpp` (25)
    - `geometry_utils.cpp` (307)
    - `heartbeat_monitor.cpp` (58)
    - `math_utils.cpp` (88)
    - `md5.cpp` (282)
    - `modbus.cpp` (176)
    - `modbus_mock.cpp` (258)
    - `modbus_tcp.cpp` (168)
    - `motion_sim.cpp` (142)
    - `system_utils.cpp` (58)
    - `topic.cpp` (66)
    - `topics_agv.cpp` (44)
    - `topics_bay.cpp` (32)
    - `topics_central.cpp` (71)
    - `topics_common.cpp` (21)
    - `topics_sim.cpp` (35)
    - `topics_vecs.cpp` (34)
    - `topics_visualizer.cpp` (62)
  - `test/` — 11 files, 70 test cases: devices_agv_tests, enum_tests, geometry_utils_tests, heartbeat_monitor_tests, math_utils_tests, md5_tests, system_utils_tests, topic_tests, topics_bay_tests, topics_central_tests, utils_tests
  - `CMakeLists.txt` (51)
  - `package.xml` (22)

#### `structures` · `src/structures` · ament_cmake · 1,206 lines
> Common data structures and simple algorithms
- **depends on (workspace):** —
- **depends on (external):** ament_cmake_gtest, rclcpp
- **used by:** bay, lift, vecs, sim
- **files:**
  - `include/`
    - `structures/`
      - `circular_buffer.hpp` (43) — class CircularBuffer
      - `debouncer.hpp` (75) — class Debouncer
      - `lowpass_filter.hpp` (18) — class LowPassFilter
      - `multichannel_read.hpp` (25) — class MultichannelRead
      - `online_mean_variance.hpp` (78) — class OnlineMeanVariance
      - `state_machine.hpp` (195) — class StateTransition, class StateTransitionSingle, class StateTransitionAny, class StateMachine
      - `unique_queue.hpp` (83) — class UniqueQueue
  - `src/`
    - `lowpass_filter.cpp` (23)
    - `multichannel_read.cpp` (27)
  - `test/` — 7 files, 18 test cases: circular_buffer_tests, debouncer_tests, lowpass_filter_tests, multichannel_read_tests, online_mean_variance_tests, state_machine_tests, unique_queue_tests
  - `CMakeLists.txt` (29)
  - `package.xml` (19)

### Layer 2 · contracts

#### `agv_interfaces` · `src/interfaces/agv_interfaces` · ament_cmake · 0 lines
> Automated Guided Vehicle (AGV) interface definitions
- **depends on (workspace):** —
- **depends on (external):** rosidl_default_runtime, std_msgs
- **used by:** agvhito, central
- **files:**
  - `msg/`
    - `NodeAccuracy.msg` (28) — node_id, node_heading_deg, x_offset_m, x_offset_valid, y_offset_m, y_offset_valid, yaw_offset_rad, yaw_offset_valid, message
    - `NodeAccuracyStamped.msg` (5) — header, accuracy
  - `CMakeLists.txt` (25)
  - `package.xml` (24)

#### `bay_interfaces` · `src/interfaces/bay_interfaces` · ament_cmake · 27 lines
> Volley Bay Messages
- **depends on (workspace):** rclcppx
- **depends on (external):** rosidl_default_runtime, std_msgs
- **used by:** bay, vis, sim, system_tests
- **files:**
  - `include/`
    - `bay_interfaces/`
      - `topics.hpp` (27)
  - `msg/`
    - `IoLinkSensors.msg` (36) — BREAK_BEAM_INVALID, BREAK_BEAM_OPEN, BREAK_BEAM_BROKEN, header, sonar_patron_right, sonar_patron_left, sonar_system_right, sonar_system_left, tire_patron, tire_system, …
    - `LoadCells.msg` (5) — header, mass
    - `VehicleProxSensor.msg` (5) — header, activation_detection, presence_detection
  - `srv/`
    - `PatronLightControl.srv` (12) — LIGHTS_OFF, LIGHT_GREEN, LIGHT_RED, LIGHT_RED_FLASHING, light_state, flashing_period_ms | success, message
  - `CMakeLists.txt` (28)
  - `package.xml` (23)

#### `interfaces` · `src/interfaces/interfaces` · ament_cmake · 0 lines
> ROS messages, services, etc.
- **depends on (workspace):** vrc_interfaces
- **depends on (external):** geometry_msgs, rosidl_default_runtime, std_msgs
- **used by:** common_ros, cost_functions, planner_core, motion_planner, scheduler, agvhito, bay, central, lift, vecs, vis, agvhito_tools, sim, system_tests, central_api, common_py, scenario, sim_metrics
- **files:**
  - `msg/`
    - `Accel.msg` (5) — x, y, yaw
    - `ActionNode.msg` (39) — TYPE_AGV_COMMAND, TYPE_BAY_COMMAND, TYPE_VECS_COMMAND, TYPE_VRC_COMMAND, STATUS_NOT_RECEIVED, STATUS_RECEIVED, STATUS_COMPLETED, guid, job_id, type, …
    - `AgvBatteryFraction.msg` (2) — agv_id, battery_fraction
    - `AgvCommand.msg` (18) — id, src, dst
    - `AgvCommandReport.msg` (4) — command_type, command_type_string, command
    - `AgvCommandReportList.msg` (4) — header, completed_command, command_queue
    - `AgvCommandSequence.msg` (5) — header, agv_id, command_sequence
    - `AgvCommandStamped.msg` (3) — header, command
    - `AgvCommandStatus.msg` (5) — status, command_type, description
    - `AgvDisablednessChanged.msg` (2) — agv_id, disable
    - `AgvExistenceChanged.msg` (8) — agv_id, added, state, lift, node_id, heading, tray_id, disabled
    - `AgvFault.msg` (11) — TYPE_NONE, TYPE_UNSPECIFIED, TYPE_CAN_INTERFACE_NODE_GUARDING, TYPE_MOTOR_GENERAL, TYPE_LOCALIZATION, TYPE_AGV_STATE_MQTT_MESSAGE_NOT_RECEIVED, TYPE_AGV_ORDER_MQTT_MESSAGE_NOT_ACKNOWLEDGED, header, type, message
    - `AgvGoal.msg` (4) — pose, lift
    - `AgvLiftChanged.msg` (2) — agv_id, raised
    - `AgvPoseChanged.msg` (5) — agv_id, node_id_curr, heading_curr, node_id_next, heading_next
    - `AgvReport.msg` (40) — STATE_BOOTING, STATE_HARDWARE_VALIDATION, STATE_NOT_LOCALIZED, STATE_CENTERING, STATE_STOPPED, STATE_ACTIVE, STATE_JOYSTICK, STATE_ERROR, LIFT_STATE_UNKNOWN, LIFT_STATE_DOWN, …
    - `AgvSimState.msg` (4) — agv_id, state
    - `AgvSnapshot.msg` (3) — header, agvs
    - `AgvState.msg` (43) — header, INTERSECTION_NOT_CENTERED, INTERSECTION_MOVE_CENTERED, INTERSECTION_TRAY_CENTERED, intersection_status, is_stopped, geometric_pose, velocity_body, accel_body, lift_fractions, …
    - `AgvStateChanged.msg` (3) — agv_id, state_curr, state_next
    - `BayCommand.msg` (12) — COMMAND_TYPE_UNKNOWN, COMMAND_TYPE_TRANSITION_TO_INSERT, COMMAND_TYPE_PROCESS_RETRIEVE, COMMAND_TYPE_TRANSITION_TO_RETRIEVE, COMMAND_TYPE_MOVE_LIFT_TO_FLOOR, command_type, command_id, floor
    - `BayDisablednessChanged.msg` (2) — bay_id, disable
    - `BayExistenceChanged.msg` (4) — bay_id, added, state, disabled
    - `BayReport.msg` (45) — STATE_BOOTING, STATE_DOOR_VALIDATION, STATE_READY_TO_RETRIEVE, STATE_READY_TO_INSERT, STATE_TRANSITIONING_TO_INSERT, STATE_PROCESSING_RETRIEVE, STATE_PROCESSING_INSERT, STATE_TRANSITIONING_TO_RETRIEVE, STATE_ERROR, STATE_VEHICLE_INSERTED, …
    - `BayState.msg` (11) — id, system_doors_closed, patron_door_state, system_door_state, overdrive_left_state, overdrive_right_state, patron_light_state
    - `BayStateChanged.msg` (3) — bay_id, state_curr, state_next
    - `CollisionBody.msg` (19) — id, type, yaw, center, scale, TYPE_UNKNOWN, TYPE_AGV, TYPE_TRAY, TYPE_BAY, TYPE_PAYLOAD, …
    - `ConsistencyReport.msg` (2) — header, consistent
    - `ContinuousGarageAgvInfo.msg` (2) — report, staleness
    - `ContinuousGarageBayInfo.msg` (2) — report, staleness
    - `ContinuousGarageInfo.msg` (6) — header, agvs, bays, vexen, vrcs
    - `ContinuousGarageVecsInfo.msg` (2) — report, staleness
    - `DisabledResourceInfo.msg` (2) — resource_id, disabled_at
    - `DisallowedEdgeOrientation.msg` (6) — src, dst, heading
    - `DiscreteAgvState.msg` (6) — id, state, pose, lift, tray_id, disabled
    - `DiscreteBayState.msg` (3) — id, state, disabled
    - `DiscreteGarageEvent.msg` (5) — type, buffer
    - `DiscreteGarageEventStamped.msg` (18) — header, event, sequence_number, hash_prev, hash_next
    - `DiscreteGarageState.msg` (14) — header, is_faulted, agvs, bays, vexen, trays, payloads, vrcs, disabled_nodes, hash
    - `DiscretePayloadState.msg` (4) — payload, tray_id, reciprocal_to_tray, charging
    - `DiscreteTrayState.msg` (5) — id, pose, agv_id, payload_id, disabled
    - `DiscreteVecsState.msg` (3) — id, state, disabled
    - `DiscreteVrcState.msg` (16) — id, state, gates, current_floor, requested_floor
    - `DispatchHeartbeat.msg` (2) — header, installation_id
    - `DispatchReport.msg` (19) — STATUS_UNKNOWN, STATUS_STARTING, STATUS_RUNNING, STATUS_STOPPING, STATUS_STOPPED, STATUS_PAUSED, MODE_UNKNOWN, MODE_AUTO, MODE_MANUAL, header, …
    - `DoorReport.msg` (12) — DOOR_STATE_CLOSED, DOOR_STATE_OPEN, DOOR_STATE_MOVING, DOOR_STATE_ERROR, header, bay_id, door_name, door_state, door_state_string, action, …
    - `DoorsReport.msg` (23) — DOORS_UNKNOWN, DOORS_CLOSED, DOORS_SYSTEM_OPEN, DOORS_PATRON_OPEN, DOORS_SYSTEM_CLOSED, DOORS_PATRON_CLOSED, DOORS_ERROR, header, state, state_string, …
    - `Edge.msg` (4) — src, dst
    - `FaultStateChanged.msg` (1) — faulted
    - `GarageEntityId.msg` (7) — entity_type, id
    - `GarageEvent.msg` (112) — EVENT_UNKNOWN, EVENT_PATRON_ENQUEUE, EVENT_BAY_ENQUEUE, EVENT_CUSTOMER_CONFIRMED_BAY_INSERT, EVENT_RETRIEVE, EVENT_PAYLOAD_DELIVERED, EVENT_CUSTOMER_CONFIRMED_BAY_RETRIEVE, EVENT_PAYLOAD_REMOVED_FROM_BAY, EVENT_AGV_COMMAND_OVERWRITTEN, EVENT_AGV_STOP_ACCEPTED, …
    - `GarageEventStamped.msg` (3) — header, event
    - `GarageFloor.msg` (11) — id, z
    - `GarageLayout.msg` (20) — header, name, nodes, floors, edges, disallowed_edge_orientations, buffer, resource_windows
    - `GarageNode.msg` (52) — TYPE_UNKNOWN, TYPE_PARKING, TYPE_WAYPOINT, TYPE_LIFT, TYPE_BAY, TYPE_AGV_CHARGE, TYPE_EV_CHARGE, TYPE_BLIFT, id, x, …
    - `GaragePayload.msg` (4) — payload, pose, geometric_pose, floor
    - `GaragePose.msg` (7) — node_id, heading
    - `GaragePoseStamped.msg` (3) — header, garage_pose
    - `GarageSnapshot.msg` (11) — header, agvs, trays, payloads, bays, vrcs, bodies
    - `GarageStatusReport.msg` (12) — header, garage_up, in_auto_mode, uptime_seconds, downtime_seconds, agv_ids, active_agv_count, agv_statuses, bay_ids, active_bay_count, …
    - `GarageTray.msg` (6) — id, floor, pose, geometric_pose, payload_id, reciprocal_to_payload
    - `GeometricPose.msg` (7) — x, y, yaw
    - `Guid.msg` (4) — bytes
    - `LiftReport.msg` (14) — STATE_ERROR, STATE_RESET, STATE_AT_FLOOR, STATE_MOVE_REQUEST, STATE_MOVING, STATE_OPENING, STATE_OPEN, state, state_string, floor
    - `NodeDisablednessChanged.msg` (2) — node_id, disable
    - `OdpObserver.msg` (24) — header, bay_id, door_name, com_status, open_requested, safe_open_requested, open, close_requested, safe_close_requested, close, …
    - `ParkingWindow.msg` (7) — name, length_m, width_m, height_m
    - `Payload.msg` (6) — id, mass, length_m, width_m, height_m, ev_charge_requested
    - `PayloadExistenceChanged.msg` (10) — added, payload_id, mass, length_m, width_m, height_m, ev_charge_requested, tray_id, reciprocal_to_tray, charging
    - `PlanRequest.msg` (11) — id, base_state, base_schedule, planned_jobs, active_jobs, pending_jobs
    - `PlanResponse.msg` (7) — success, message, id, schedule, scheduled_jobs
    - `Schedule.msg` (5) — header, nodes
    - `ScheduledJobData.msg` (12) — job, node_indices, bay_id, bay_arrival_node_guid
    - `SchedulerJob.msg` (46) — TYPE_UNKNOWN, TYPE_MOVE_AGV, TYPE_MOVE_TRAY, TYPE_READY_FOR_INSERT, TYPE_READY_FOR_RETRIEVE, TYPE_RETRIEVE, TYPE_CHARGE_AGV, TYPE_TRANSITION_BAY_TO_INSERT, TYPE_TRANSITION_BAY_TO_RETRIEVE, TYPE_CLEAN_GARAGE, …
    - `SchedulerJobList.msg` (3) — header, jobs
    - `SchedulerReport.msg` (2) — header, bay_readiness_ratio
    - `SimReport.msg` (4) — header, running, num_remaining_events, payloads
    - `SizedPose.msg` (2) — resource_size_index, pose
    - `TrayDisablednessChanged.msg` (2) — tray_id, disable
    - `TrayExistenceChanged.msg` (9) — tray_id, added, node_id, heading, agv_id, disabled
    - `TrayPoseSetManually.msg` (5) — tray_id, node_id_curr, heading_curr, node_id_next, heading_next
    - `Twist.msg` (5) — x, y, yaw
    - `VecsCommand.msg` (9) — header, COMMAND_TYPE_UNKNOWN, COMMAND_TYPE_START_CHARGING, COMMAND_TYPE_STOP_CHARGING, command_id, command_type
    - `VecsDisablednessChanged.msg` (2) — vecs_id, disable
    - `VecsEvseReport.msg` (10) — header, vecs_id, state, state_string, is_plugged_in, vecs_set_max_current, current_limit, active_power, energy_delivered
    - `VecsExistenceChanged.msg` (4) — vecs_id, added, state, disabled
    - `VecsIoLedCommand.msg` (9) — header, COMMAND_TYPE_LEDS_ALL_ON, COMMAND_TYPE_LEDS_ALL_OFF, COMMAND_TYPE_LEDS_STOP_ON, command_id, command_type
    - `VecsIoReport.msg` (10) — header, vecs_id, is_faulted, clear_button_pressed, stop_button_pressed, clear_led_on, stop_led_on, alert_led_on
    - `VecsReport.msg` (23) — BOOTING, HARDWARE_VALIDATION, READY_TO_CHARGE, ATTACHING_ADAPTER, CHARGING, DETACHING_ADAPTER, ERROR, COMMAND_STATUS_UNKNOWN, COMMAND_STATUS_IN_PROGRESS, COMMAND_STATUS_COMPLETED, …
    - `VecsStateChanged.msg` (3) — vecs_id, state_curr, state_next
    - `VehicleBayPose.msg` (51) — ERROR_FLAG_NONE, ERROR_FLAG_OVERWEIGHT, ERROR_FLAG_TOO_LONG, ERROR_FLAG_TOO_WIDE, ERROR_FLAG_WHEELBASE_TOO_LONG, ERROR_FLAG_LIDAR_PATRON_TRIPPED, ERROR_FLAG_LIDAR_SYSTEM_TRIPPED, ERROR_FLAG_LIDAR_RIGHT_TRIPPED, ERROR_FLAG_LIDAR_LEFT_TRIPPED, ERROR_FLAG_TIRE_PATRON_TRIPPED, …
    - `VersionInfo.msg` (19) — header, name, release, gitsha, layout_md5sum
    - `VrcCommand.msg` (9) — header, COMMAND_TYPE_UNKNOWN, COMMAND_TYPE_MOVE, command_id, command_type, requested_floor
    - `VrcExistenceChanged.msg` (2) — discrete_state, added
    - `VrcStateChanged.msg` (2) — current_discrete_state, next_discrete_state
  - `srv/`
    - `AddAgv.srv` (9) — id, garage_pose, pose, lift_fraction, battery_fraction | success, message
    - `AddPayload.srv` (8) — payload, tray_id, reciprocal_to_tray, pose | success, message
    - `AddTray.srv` (9) — id, agv_id, reciprocal_to_agv, garage_pose, disabled | success, message
    - `AgvCommand.srv` (6) — command | command_status, message
    - `AgvCommandList.srv` (6) — commands | command_status, message
    - `AgvStop.srv` (25) — id, STOP_INVALID, STOP_AT_NEXT_POSE, STOP_NOW, STOP_HARD_FAULT, severity, reason, fault | command_status, success, message
    - `BayCommand.srv` (6) — command | success, message
    - `ChargePayload.srv` (8) — payload_id | success, message, job_id
    - `GetGarageLayout.srv` (7) —  | success, status_code, layout
    - `GetJobState.srv` (7) — guid | success, message, job
    - `LocalizeAgv.srv` (8) — garage_pose | success, message
    - `MoveAgv.srv` (10) — agv_id, pose | success, message, job_id
    - `MoveTray.srv` (10) — tray_id, pose | success, message, job_id
    - `PlacePayloadInBay.srv` (8) — payload, bay_id | success, message
    - `Plan.srv` (7) — request_data | response_data
    - `RegisterRetrievalCode.srv` (10) — payload_id | success, retrieval_code, message
    - `RemoveAgv.srv` (5) — id | success, message
    - `RemovePayload.srv` (5) — payload_id | success, message
    - `RemoveTray.srv` (5) — id | success, message
    - `ReparkTray.srv` (12) — tray_id, pose, allow_reciprocal | success, message, job_id
    - `Retrieve.srv` (9) — payload_id | success, message, job_id
    - `SetFloat32.srv` (7) — value | success, message
    - `SetPayload.srv` (5) — payload | success, message
    - `SetPayloadInfo.srv` (16) — payload_id, ev_charge_requested, length_m, width_m, height_m, mass | success, message
    - `SetResourceDisabledness.srv` (11) — resource_id, disable | success, message
    - `SetString.srv` (7) — value | success, message
    - `SetUInt16.srv` (7) — value | success, message
    - `SetUInt32.srv` (7) — value | success, message
    - `SetUInt8.srv` (7) — value | success, message
    - `SimEvent.srv` (15) — type, time, resource_id, pose, float_value, uint_value, bool_value, payload | success, message
    - `TransitionBayToInsert.srv` (13) — bay_id | success, message, job_id
    - `TransitionBayToRetrieve.srv` (13) — bay_id | success, message, job_id
    - `VecsCommand.srv` (6) — command | success, message
    - `VecsIoLedCommand.srv` (6) — command | success, message
  - `CMakeLists.txt` (27)
  - `package.xml` (24)

#### `map_server` · `src/vda5050/map_server` · ament_python · 389 lines
> VDA5050 compliant map server package
- **depends on (workspace):** vda5050_interfaces
- **depends on (external):** ament_cmake_pytest, python3-pytest, rclpy
- **used by:** agvhito
- **files:**
  - `map_server/`
    - `__init__.py`
    - `flask_app.py` (103) — class MapRequest, def create_app · "Flask app exposing HTTP endpoints for storing and retrieving maps."
    - `map_store.py` (46) — class MapStore · "Thread-safe FIFO-bounded cache of maps keyed by mapId."
    - `server.py` (50) — class Settings, def main · "Main flask based map server application."
  - `resource/`
    - `map_server`
  - `test/` — 2 files, 14 test cases: test_map_store, test_server
  - `package.xml` (21)
  - `setup.cfg`
  - `setup.py` (29)

#### `vda5050_interfaces` · `src/vda5050/vda5050_interfaces` · ament_cmake · 1,009 lines
> VDA5050 compliant interface definitions including generated pydantic models and C++ headers
- **depends on (workspace):** stdx
- **depends on (external):** ament_cmake_gtest, ament_cmake_pytest, nlohmann-json-dev, nlohmann_json_schema_validator_vendor
- **used by:** map_server, agvhito, agvhito_tools
- **files:**
  - `cmake/`
    - `Codegen.cmake` (90)
  - `include/`
    - `vda5050_interfaces/`
      - `schema.hpp` (105) — struct Collector · "Build a validator from a JSON Schema string."
  - `schemas/` — data, 8 files: commonMessage, connection, factsheet, instantActions, map, order, state, visualization
  - `scripts/`
    - `gen_cpp.py` (287) — def pascal, def snake_case, def enum_symbol, def name_from_field, class CppGen, def main · "Emit a C++ header from a VDA5050 JSON Schema file."
    - `gen_mqtt.py` (48) — def main · "Emit the shared topic constants header and Python module."
    - `gen_python.py` (80) — def main · "Emit a pydantic v2 module from a VDA5050 JSON Schema file."
  - `templates/`
    - `mqtt.hpp.j2`
    - `mqtt.py.j2`
    - `struct.hpp.j2`
  - `test/` — 2 files, 27 test cases: test_cpp_gen, test_py_gen
  - `CMakeLists.txt` (107)
  - `package.xml` (27)

#### `vrc_interfaces` · `src/interfaces/vrc_interfaces` · ament_cmake · 0 lines
> Vertical Reciprocating Conveyor (VRC) interface definitions
- **depends on (workspace):** —
- **depends on (external):** rosidl_default_runtime, std_msgs
- **used by:** interfaces, planner_core, scheduler, bay, central, vis, vrc
- **files:**
  - `action/`
    - `VrcMove.action` (17) — requested_floor | current_floor, message | current_floor, carriage_height_m
  - `msg/`
    - `GateReport.msg` (5) — floor, state
    - `GateState.msg` (9) — STATE_CLOSED, STATE_OPEN, STATE_CLOSING, STATE_OPENING, STATE_UNKNOWN, value
    - `VrcReport.msg` (22) — header, id, state, state_description, gates, current_floor, requested_floor, carriage_height_m
    - `VrcState.msg` (13) — STATE_INITIALIZING, STATE_IDLE, STATE_MOVING, STATE_CLOSING, STATE_OPENING, STATE_DISABLED, STATE_ERROR, STATE_UNKNOWN, value
  - `CMakeLists.txt` (25)
  - `package.xml` (24)

### Layer 7 · ROS glue

#### `common_ros` · `src/common_ros` · ament_cmake · 19,777 lines
> Common code and utilities that depend on ros or ros messages
- **depends on (workspace):** common, interfaces, launcher, rclcppx, stdx
- **depends on (external):** ament_cmake, ament_cmake_gtest, ament_index_cpp, eigen, libboost-dev, nlohmann-json-dev, rclcpp, rosidl_typesupport_introspection_cpp, std_msgs, std_srvs, yaml-cpp
- **used by:** cost_functions, planner_core, motion_planner, scheduler, agvhito, bay, central, lift, vecs, vis, agvhito_tools, scheduler_advanced_tests, sim
- **files:**
  - `include/`
    - `common_ros/`
      - `agv_motion_type.hpp` (41) — enum AgvMotionType, using GarageNodeMsg, using AgvCommandMsg, using AgvGoalMsg
      - `collision_geometry.hpp` (512) — struct std, struct Circle, class ComparableGeometry, class CollisionEntity, class TrayLegsEntity, class TrayEntity, class AgvEntity, class BayOdpEntity, class PayloadEntity, class CollisionTable, enum CollisionEntityId, using Point2d, using Polygon, using MultiPolygon
      - `common_ros_msgs.hpp` (108) — using ActionNodeMsg, using AgvCommandMsg, using AgvGoalMsg, using AgvReportMsg, using BayCommandMsg, using BayReportMsg, using DiscreteAgvStateMsg, using DiscreteBayStateMsg, using DiscretePayloadStateMsg, using DiscreteTrayStateMsg, using DiscreteVecsStateMsg, using DiscreteVrcStateMsg, using DiscreteGarageEventMsg, using DiscreteGarageStateMsg
      - `component.hpp` (23) — class Component
      - `discrete_garage_event_io.hpp` (70)
      - `discrete_garage_state.hpp` (190) — class DiscreteGarageState
      - `discrete_garage_state_utils.hpp` (45)
      - `garage_graph.hpp` (238) — struct std, struct Transition, class GarageGraph, enum TransitionType, using BoostPoseGraph, using Vertex, using Edge, using VertexVectorPropertyMap, using EdgeVectorPropertyMap, using GarageGraphSPtr
      - `garage_occupancy_checker.hpp` (235) — class GarageOccupancyChecker, struct OccupantBlockage, using OccupantSet, using OccupantBlockageMap · "A class that tracks which garage entities occupy which locations in the garage graph and provides"
      - `garage_safety_checker.hpp` (125) — class GarageSafetyChecker, class BlockingEntityEqual, class BlockingEntityHash, using BlockingEntity
      - `geometry_visualization.hpp` (54)
      - `layout.hpp` (255) — struct Vrc, class Layout, using graph, using LayoutSPtrConst, using LayoutSPtr
      - `manual_timer.hpp` (30) — class ManualTimer
      - `node.hpp` (109) — class Node, using SharedPtr, using NodeSPtr
      - `polygon_utils.hpp` (48) — using Point2d, using Polygon
      - `pose_graph.hpp` (128) — class PoseGraph, enum PoseNeighbor, using PoseGraphSPtr, using PoseGraphCSPtr
      - `pose_utils.hpp` (79) — struct GaragePoseComparator
      - `print_graph.hpp` (19) — "Render a dot graph as an ASCII DAG and print it to the log."
      - `print_utils.hpp` (59)
      - `repeated_data_checker.hpp` (34) — class RepeatedDataChecker
      - `ros_utils.hpp` (293) — struct std, struct GuidComparator, struct EdgeComparator, struct GarageEntityIdComparator, struct GarageEntityIdHasher, struct DiscreteGarageEventHasher, using ServiceResponseFuture
      - `roslog.hpp` (15)
      - `tape_layout.hpp` (32)
      - `versioned_state_buffer.hpp` (266) — enum DecodeStatus
  - `src/`
    - `agv_motion_type.cpp` (123)
    - `collision_geometry.cpp` (844) — "Returns whether the provided garage node belongs to a VRC"
    - `discrete_garage_state.cpp` (1835)
    - `discrete_garage_state_utils.cpp` (79)
    - `garage_graph.cpp` (338)
    - `garage_safety_checker.cpp` (591)
    - `geometry_visualization.cpp` (94)
    - `geometry_visualization_tool.cpp` (91) — main()
    - `layout.cpp` (813)
    - `manual_timer.cpp` (17)
    - `node.cpp` (25)
    - `polygon_utils.cpp` (137)
    - `pose_graph.cpp` (230)
    - `pose_utils.cpp` (122)
    - `print_graph.cpp` (84)
    - `print_utils.cpp` (433)
    - `ros_utils.cpp` (218)
    - `tape_layout.cpp` (285)
    - `versioned_state_buffer.cpp` (417)
  - `test/` — 19 files, 214 test cases: collision_geometry_tests, collision_geometry_tests_draw, collision_geometry_tests_eccles, discrete_garage_state_tests, discrete_garage_state_utils_tests, garage_graph_tests, garage_occupancy_checker_tests, garage_safety_checker_tests, layout_tests, manual_timer_tests, node_tests, polygon_utils_tests, pose_graph_tests, pose_utils_tests, print_utils_tests, repeated_data_checker_tests, ros_utils_tests, tape_layout_tests, versioned_state_buffer_tests
  - `CMakeLists.txt` (190)
  - `package.xml` (36)

### Layer 8 · planning libraries

#### `cost_functions` · `src/planner/cost_functions` · ament_cmake · 984 lines
> Single source of truth for all cost and duration estimates used in motion planning and simulation
- **depends on (workspace):** common, common_ros, interfaces
- **depends on (external):** ament_cmake_gtest, ament_index_cpp, eigen
- **used by:** motion_planner, scheduler
- **files:**
  - `include/`
    - `cost_functions/`
      - `cost_functions.hpp` (55) — struct CostEntry, struct CostVector, using SecondsF
      - `motion_cost_model.hpp` (100) — struct VelocityLimits, struct EventDurations, struct MotionCostParams, class MotionCostModel
      - `motion_run.hpp` (32) — struct MotionRun
  - `src/`
    - `cost_functions.cpp` (103)
    - `motion_cost_model.cpp` (80)
    - `motion_run.cpp` (131)
  - `test/` — 2 files, 28 test cases: cost_functions_tests, motion_run_tests
  - `CMakeLists.txt` (38)
  - `package.xml` (23)

#### `planner_core` · `src/planner/planner_core` · ament_cmake · 2,833 lines
> Shared domain model for the planner group: the schedule event hierarchy and the event DAG that every other package in src/planner plans over. Depends on no other package in the group.
- **depends on (workspace):** common, common_ros, interfaces, vrc_interfaces
- **depends on (external):** ament_cmake_gtest, libboost-dev, rclcpp
- **used by:** motion_planner, scheduler
- **files:**
  - `include/`
    - `planner_core/`
      - `event_dag.hpp` (590) — class DagBase, struct VertexLabelWriter, class ScheduleEventDag, using DagT, using Vertex, using Edge, using Iterator, using VertexVec
      - `planner_core_msgs.hpp` (46) — using ActionNodeMsg, using AgvCommandMsg, using AgvGoalMsg, using BayCommandMsg, using BayReportMsg, using GarageEntityIdMsg, using GarageNodeMsg, using GaragePoseMsg, using DiscreteAgvStateMsg, using DiscreteBayStateMsg, using DiscreteTrayStateMsg, using DiscreteGarageEventMsg, using DiscretePayloadStateMsg, using DiscreteGarageStateMsg
      - `schedule_events.hpp` (265) — class ScheduleEvent, class AgvMove, class TrayMove, class BayTransition, class VecsTransition, class VrcTransition, enum ScheduleEventType, using ScheduleEventSPtr
  - `src/`
    - `event_dag.cpp` (94)
    - `schedule_events.cpp` (459)
  - `test/` — 2 files, 21 test cases: event_dag_tests, schedule_events_tests
  - `CMakeLists.txt` (31)
  - `package.xml` (28)

#### `task_planner` · `src/planner/task_planner` · ament_cmake · 1,007 lines
> Libraries used for task planning
- **depends on (workspace):** —
- **depends on (external):** ament_cmake_gtest, libboost-dev
- **used by:** scheduler
- **files:**
  - `include/`
    - `task_planner/`
      - `assignment.hpp` (483)
  - `test/` — 1 files, 11 test cases: assignment_tests
  - `CMakeLists.txt` (13)
  - `package.xml` (18)

### Layer 9 · motion planning

#### `motion_planner` · `src/planner/motion_planner` · ament_cmake · 10,955 lines
> Libraries used for motion planning
- **depends on (workspace):** common, common_ros, cost_functions, interfaces, launcher, planner_core, rclcppx
- **depends on (external):** ament_cmake_gtest, ament_index_cpp, eigen, libboost-dev, rclcpp, yaml-cpp
- **used by:** scheduler, scheduler_advanced_tests
- **files:**
  - `include/`
    - `motion_planner/`
      - `agv_hiding_search.hpp` (57) — class AgvSearchEnvironment
      - `blocking_tray_search.hpp` (160) — struct BlockingTrayState, class BlockingTraySearchEnvironment, class OpenSpaceSearchEnvironment, class EmptyTraySearchEnvironment, struct std
      - `chugg.hpp` (262) — class Chugg, struct Node, struct NodeFlowtimeComparitor, struct NodeMakespanComparitor, using CollisionTable, using DiscreteGarageState, using GarageGraph, using EdgeCosts, using CollisionId, using ScheduleEventDag, using GraphConstraints, using ScheduleEvent, using EventType
      - `coalesce_trajectory.hpp` (26)
      - `continuous_state.hpp` (52) — class ContinuousState, using TrajectoryMap
      - `garage_graph_pathing.hpp` (107) — class GarageGraphEnvironment
      - `interval.hpp` (100) — class Interval, class IntervalSet, struct IntervalSorter, using Timepoint, using Duration
      - `motion_planner_msgs.hpp` (18) — using GaragePoseMsg, using AgvPoseChangedMsg, using AgvLiftChangedMsg, using BayStateChangedMsg, using VecsStateChangedMsg, using VrcStateChangedMsg
      - `path_search.hpp` (277) — struct SearchMetaData, class SearchEnvironment, class SearchSolution, struct SearchNode, using OpenSet, using OpenSetHandle
      - `safe_interval_path_planning.hpp` (247) — class SippState, class SippGoal, struct hash, class SippEnvironment, using Vertex, using Edge, using Neighbors, using GarageGraph, using EdgeDurations, using Transition, using TransitionType
      - `safe_interval_table.hpp` (213) — class SafeIntervalTable, struct TableEntryKeyHasher, using TableEntryKey, using IntervalTableMap
      - `sipp_agv.hpp` (134) — class SippAgv, using CollisionEntityId_t, using GarageGraph, using CollisionTable, using ScheduleEvent, using GraphConstraints, using SippSolution
      - `static_graph_filtering.hpp` (62) — class GraphFilterProperties
      - `trajectory.hpp` (196) — class Motion, class Trajectory, struct PoseHasher, struct EdgeHasher, struct MotionHasher, using Pose, using Edge, using CollisionEntityId_t, using Iterator, using ConstIterator
  - `src/`
    - `agv_hiding_search.cpp` (106)
    - `blocking_tray_search.cpp` (202)
    - `chugg_cbs.cpp` (128)
    - `chugg_common.cpp` (525)
    - `chugg_sequential.cpp` (690)
    - `coalesce_trajectory.cpp` (192)
    - `continuous_state.cpp` (292)
    - `garage_graph_pathing.cpp` (218)
    - `interval.cpp` (248)
    - `path_search.cpp` (13)
    - `safe_interval_path_planning.cpp` (601)
    - `safe_interval_table.cpp` (91)
    - `sipp_agv.cpp` (312)
    - `static_graph_filtering.cpp` (239)
    - `trajectory.cpp` (205)
  - `test/` — 14 files, 63 test cases: agv_hiding_search_tests, blocking_tray_search_tests, chugg_tests, coalesce_trajectory_tests, continuous_state_tests, garage_graph_pathing_tests, interval_tests, path_search_tests, safe_interval_planning_tests, safe_interval_table_tests, sipp_agv_tests, static_graph_filtering_tests, test_motion_cost_params, trajectory_tests
  - `CMakeLists.txt` (135)
  - `package.xml` (31)

### Layer 10 · scheduling

#### `scheduler` · `src/planner/scheduler` · ament_cmake · 12,113 lines
> The scheduler node and its utilities responsible for building a DAG of scheduled events from pending jobs
- **depends on (workspace):** common, common_ros, cost_functions, interfaces, launcher, motion_planner, planner_core, rclcppx, stdx, task_planner, vrc_interfaces
- **depends on (external):** ament_cmake_gtest, ament_index_cpp, backward_ros, libboost-dev, rclcpp, rclcpp_components, std_srvs, yaml-cpp
- **used by:** agvhito_tools, scheduler_advanced_tests
- **files:**
  - `include/`
    - `scheduler/`
      - `scheduler.hpp` (456) — struct std, struct SchedulerParams, class ScheduleContext, class Scheduler, struct OpenSpaceSearchResult, struct BlockingTrayResolution, using AgvAssignmentEdgeKey, using CollistionFilterMap, using GarageEntityEventMap, using ScheduleContextSPtr, using SchedulerSPtr
      - `scheduler_msgs.hpp` (58) — using ActionNodeMsg, using AgvGoalMsg, using BayCommandMsg, using BayReportMsg, using DiscreteAgvStateMsg, using DiscreteBayStateMsg, using DiscreteTrayStateMsg, using DiscreteGarageEventMsg, using DiscretePayloadStateMsg, using DiscreteGarageStateMsg, using GarageEntityIdMsg, using GarageNodeMsg, using GaragePoseMsg, using GuidMsg
      - `scheduler_ros.hpp` (40) — class SchedulerRos
      - `utils.hpp` (97) — enum BayClassification
  - `src/`
    - `scheduler.cpp` (4200)
    - `scheduler_component.cpp` (71) — component volley::SchedulerComponent
    - `scheduler_ros.cpp` (125)
    - `utils.cpp` (520)
  - `test/` — 4 files, 73 test cases: scheduler_insert_orientation_tests, scheduler_jobs_tests, scheduler_tests, utils_tests
  - `CMakeLists.txt` (62)
  - `package.xml` (41)

### Layer 8 · nodes

#### `agvhito` · `src/agvhito` · ament_cmake · 14,050 lines
> VDA5050-compliant proxy that relays Volley schedules to Hito AGVs
- **depends on (workspace):** agv_interfaces, common, common_ros, interfaces, launcher, map_server, mqtt, rclcppx, stdx, vda5050_interfaces, yasminx
- **depends on (external):** ament_cmake_gtest, ament_index_cpp, backward_ros, eigen, geometry_msgs, launch, launch_ros, launch_testing_ament_cmake, libboost-dev, nlohmann-json-dev, rclcpp, rclcpp_components, rcpputils, std_srvs, uuid, yaml-cpp, yasmin
- **used by:** agvhito_tools
- **files:**
  - `include/`
    - `agvhito/`
      - `comms/`
        - `i_map_client.hpp` (45) — class IMapClient, using MapLookup, using MapIds, using IMapClientSPtr, using IMapClientUPtr · "Alias for a lookup collection of maps indexed by map identifier."
        - `map_client.hpp` (46) — class MapClient, using MapClientSPtr, using MapClientUPtr · "Concrete HTTP map client class for interfacing with the map server service."
        - `map_client_connection_options.hpp` (14) — struct MapClientConnectionOptions · "Options used for connecting to the HTTP map server."
        - `sim_map_client.hpp` (55) — class SimMapClient, using SimMapClientSPtr, using SimMapClientUPtr · "Concrete HTTP map client class for simulated interaction with a map server service."
        - `sim_mqtt_client.hpp` (49) — class SimMqttClient, using SimMqttClientSPtr, using SimMqttClientUPtr · "Intra-process MQTT client used for simulation."
        - `sim_mqtt_publisher.hpp` (31) — class SimMqttPublisher · "Intra-process MQTT publisher used for simulation."
        - `sim_mqtt_subscription.hpp` (60) — class SimMqttSubscription · "Intra-process MQTT subscription used for simulation."
      - `sim/`
        - `action_utils.hpp` (62) — struct ActionResult · "@return JSON value of the first parameter in @p action_params matching @p key, or empty if none"
        - `agv_motion.hpp` (90) — class AgvMotion · "Kinematic simulator for a single AGV."
        - `battery_charge_model.hpp` (40) — class BatteryChargeModel, struct Options · "Tracks the simulated AGV battery charge fraction directly, with no voltage round-trip. The"
        - `kinematic_limits.hpp` (31) — struct KinematicLimits · "Deceleration applied during an emergency stop and pause events."
        - `motion_types.hpp` (131) — struct Waypoint, struct KinematicState, struct Velocity, struct LocomotionMotion, struct StrafeMotion, struct RotateMotion, struct ChangeDriveModeMotion, struct LiftMotion, struct OrderMotion, enum DriveMode, using MotionPrimitive · "Drive mode of the AGV."
        - `order_parsing_utils.hpp` (20) — "Convert a VDA5050 order into an ordered deque of scheduled motions, using released nodes"
        - `sim_agv.hpp` (220) — class SimAgv, struct InitialState, struct Options, struct State, struct OrderState, using ActionStateLookup, using StateMapLookup, using SimAgvUPtr · "Simulated AGV that emulates VDA5050 HITO behavior for testing and development."
        - `sim_agv_ros.hpp` (62) — class SimAgvRos, struct Subscribers, struct Publishers, struct Timers, using SimAgvRosUPtr · "ROS interface layer for a simulated AGV which adds simulation specific subscribers and timers on top of"
        - `topic_conversions.hpp` (118) — "@return the maps lookup @p maps flattened into a state message vector."
      - `sm/`
        - `blackboard.hpp` (100) — struct std, enum Request · "Tracked VDA5050 CommonMessage published from AGV."
        - `booting_state.hpp` (18) — class BootingState · "Initial root state machine state responsible for ensuring the AGV is actively reporting state. Performs"
        - `canceling_order_state.hpp` (25) — class CancelingOrderState · "State that cancels an active order, which will stop the AGV at the next order node."
        - `context_utils.hpp` (46) — "Assemble and publish a batch of instant @p actions"
        - `error.hpp` (72) — "@return Empty when @p state reports no e-stop, or the outcome and error to fault with when it does."
        - `error_state.hpp` (28) — class ErrorState · "State that handles errors generated internally from the state machine. Attempts auto recovery if the AGV"
        - `executing_order_state.hpp` (33) — class ExecutingOrderState · "State that performs order execution including execution status and completion criteria checking."
        - `execution_paused_state.hpp` (30) — class ExecutionPausedState · "State that holds the AGV in a paused state during order execution, and waits for a resume request to"
        - `execution_recovery_state.hpp` (29) — class ExecutionRecoveryState · "State that attempts recovery during execution of an order."
        - `idle_state.hpp` (23) — class IdleState · "State that holds the AGV in a paused state, and waits for a assembled order request to transition."
        - `localizing_state.hpp` (24) — class LocalizingState · "State that requests the AGV to enable the localization map, and verifies the AGV is reporting position is"
        - `root.hpp` (12) — "@return A @ref yasminx::RootStateMachine with all AGV states added, built with @p clock and @p logger."
        - `state_strings.hpp` (118) — "Shared outcome for state error outcome."
        - `stopped_state.hpp` (23) — class StoppedState · "State that holds the AGV in a soft e-stop state, and waits for an activation request to transition."
        - `timing.hpp` (13) — "Default step period for `LifecycleState` subclasses that poll the blackboard."
      - `topics/`
        - `action_types.hpp` (22)
        - `common_msg.hpp` (67) — "HITO `commonMessage` metadata keys for the four guide sensor deviations."
        - `core.hpp` (98) — "VDA5050 manufacturer field used for HITO AGVs."
        - `factsheet.hpp` (30) — "Key of the version entry the AGV reports its firmware version under."
        - `instant_actions.hpp` (131) — "Make an `instantAction` `Action` with a random GUID actionId."
        - `map.hpp` (62) — using FloorMaps, using FloorMapIds · "Alias for a collection of HITO maps, indexed by floor number."
        - `order.hpp` (161) — struct std, enum EdgeOrientation · "order-edge `orientation` values for the four supported motion primitives."
        - `state.hpp` (235) — struct std, enum LiftState · "@return The map @p map_id names in @p state, or `std::nullopt` if the AGV does not report it."
        - `state_predicates.hpp` (140) — struct StatePredicate · "A check on the AGV's reported state, with a description used for messaging."
      - `action_state_manager.hpp` (46) — class ActionStateManager, using ActionStateManagerSPtr · "Thread-safe store that maintains Action IDs to their latest VDA5050 ActionStatus."
      - `active_order.hpp` (92) — class ActiveOrder, struct Progress, struct CommandStatusReport, enum Phase, using ActiveOrderSPtr · "Processes and tracks progress of a actively executing VDA5050 order."
      - `agv.hpp` (148) — class Agv, struct RequestResult, struct Context, using AgvUPtr · "Drives a single HITO AGV over VDA5050 MQTT through an internal state machine."
      - `agv_ros.hpp` (134) — class AgvRos, struct Publishers, struct ServiceServers, struct Timers, using AgvRosUPtr · "AGV ROS interface layer for translating ROS specific communication types to the underlying AGV object."
      - `aliases.hpp` (10) — using AgvId · "Convenient AGV identifier alias that decouples underlying POD type."
      - `callback_aliases.hpp` (11) — using NodeAccuracyCallback · "Function callback alias for handling a node accuracy update.."
      - `conversions.hpp` (90) — enum AgvGoalType · "@return Parsed integer-based node identifier, or an error if @p node_id is not a valid integer."
      - `firmware_version.hpp` (20) — struct FirmwareVersionSpec · "Version specification that matches any firmware version."
      - `instance_manager.hpp` (138) — class InstanceManager, struct Context, struct PendingAgv, using InstanceManagerUPtr · "Discovers AGVs from VDA5050 state messages and owns an AGV instance per identifier."
      - `instant_action_assembler.hpp` (52) — class InstantActionAssembler, using InstantActionAssemblerSPtr · "Builds VDA5050 InstantActions messages for a single AGV."
      - `layout_utils.hpp` (36) — using GarageNode · "@return true if @p node is a type whose traversal is restricted (lift, bay, charge, or blift)."
      - `magnetic_guide_sensor.hpp` (87) — struct MgsDeviations, struct MgsOffsets · "Exclusive bound on the deviation a magnetic guide sensor can report."
      - `msg_conversions.hpp` (179) — using AgvReport · "@return AgvReport state enum corresponding to the yasmin state name @p state_name ."
      - `order_assembler.hpp` (79) — struct AssembledOrder, class OrderAssembler, struct Config, using OrderAssemblerSPtr · "Details for an assembled VDA5050 Order."
      - `order_queue.hpp` (54) — class OrderQueue, using OrderQueueSPtr · "Thread-safe FIFO queue of AssembledOrders that rejects duplicates by computing an order key from command"
      - `param_utils.hpp` (56) — "@return SpeedLimits built from the node's agv.performance_limits.* params, falling back to the"
      - `pose_filter.hpp` (78) — struct Pose2D, struct PoseFilterConfig, class PoseFilter, using PoseFilterSPtr · "Timestamped 2D pose in the global map frame."
      - `print_utils.hpp` (18) — "@return A multi-line status of the current state computed from @p state and @p pose ."
      - `speed_limits.hpp` (40) — struct SpeedLimits, struct std · "AGV speed limit configuration for linear (locomote/strafe) and rotation, each with its own"
      - `tracked_message.hpp` (98) — class TrackedMessage, struct Snapshot, enum MessageStaleness, using TrackedMessageSPtr · "Stores each message in order, keeping the most recent by timestamp."
  - `launch/`
    - `proxy.launch.py` (77) — runs proxy_node
  - `src/`
    - `comms/`
      - `map_client.cpp` (125)
      - `sim_mqtt_client.cpp` (29)
      - `sim_mqtt_client_impl.cpp` (69)
      - `sim_mqtt_client_impl.hpp` (47) — class SimMqttClientImpl
      - `sim_mqtt_publisher.cpp` (29)
      - `sim_mqtt_subscription.cpp` (74)
    - `sim/`
      - `agv_motion.cpp` (323)
      - `battery_charge_model.cpp` (39)
      - `order_parsing_utils.cpp` (307) — "@return true if @p node declares a lift up or lift down action."
      - `sim_agv.cpp` (681)
      - `sim_agv_component.cpp` (108) — component volley::agvhito::sim::SimAgvComponent
      - `sim_agv_ros.cpp` (85)
    - `sm/`
      - `booting_state.cpp` (153)
      - `canceling_order_state.cpp` (71)
      - `context_utils.cpp` (221)
      - `error_state.cpp` (102)
      - `executing_order_state.cpp` (306)
      - `execution_paused_state.cpp` (62)
      - `execution_recovery_state.cpp` (77)
      - `idle_state.cpp` (113)
      - `localizing_state.cpp` (64)
      - `root.cpp` (67)
      - `stopped_state.cpp` (68)
    - `topics/`
      - `map.cpp` (141) — "HITO laser-group extendInfo key."
      - `order.cpp` (150)
    - `action_state_manager.cpp` (59)
    - `active_order.cpp` (204)
    - `agv.cpp` (555)
    - `agv_ros.cpp` (328)
    - `instance_manager.cpp` (385) — "VDA5050 topics are "vda5050/v2/{manufacturer}/{serialNumber}/{subtopic}", serialNumber is at index 3."
    - `instant_action_assembler.cpp` (59)
    - `layout_utils.cpp` (28)
    - `order_assembler.cpp` (385)
    - `order_queue.cpp` (94) — "@return The duplicate-detection key for @p commands. Used to prevent queuing an order built from the exact"
    - `pose_filter.cpp` (99)
    - `print_utils.cpp` (115) — "@return The orientation for a Translate @p command , nullopt if orientation could not be determined."
    - `proxy_component.cpp` (75) — component volley::agvhito::ProxyComponent
    - `tracked_message.cpp` (127)
  - `test/` — 28 files, 230 test cases: test_action_state_manager, test_active_order, test_agv_motion, test_battery_charge_model, test_common_msg, test_conversions, test_core, test_factsheet, test_firmware_version, test_instant_action_assembler, test_layout_utils, test_magnetic_guide_sensor, test_map, test_map_client, test_map_client.test, test_msg_conversions, test_order, test_order_assembler, test_order_parsing_utils, test_order_queue, test_pose_filter, test_sim_map_client, test_sim_mqtt, test_state, test_state_predicates, …
  - `CMakeLists.txt` (186)
  - `package.xml` (50)

#### `bay` · `src/bay` · ament_cmake · 14,063 lines
> Bay code
- **depends on (workspace):** bay_interfaces, common, common_ros, interfaces, launcher, rclcppx, stdx, structures, vrc_interfaces
- **depends on (external):** ament_cmake, ament_cmake_gtest, ament_index_cpp, eigen, launch_testing_ament_cmake, libboost-dev, libmsgsl-dev, nlohmann-json-dev, rclcpp, rclcpp_action, rclcpp_components, rclpy, std_srvs, yaml-cpp
- **used by:** sim
- **files:**
  - `include/`
    - `bay/`
      - `sim/`
        - `garage_door_sim.hpp` (163) — struct BayDoorTimes, class GarageDoorSimCore, class GarageDoorSimRt, class GarageDoorSimFast, class GarageDoorSimFastInterface, using SecondsF
        - `perfect_doors.hpp` (28) — class PerfectDoorsInterface
      - `axis_filter.hpp` (58) — class AxisFilter · "Kalman filter for the [position, velocity] state of a single axis, measured by position"
      - `axle_counter.hpp` (130) — class AxleCounter
      - `bay_floor_spec.hpp` (65) — struct FloorSpec
      - `bay_guidance.hpp` (65) — class BayGuidance, enum GuidanceState · "The guidance websocket's actual bound port. Useful in tests that request port 0 for"
      - `bay_insert_state_machine.hpp` (142) — class InsertStateMachine, enum State, enum Event
      - `bay_msgs.hpp` (49) — using BayReportMsg, using BayCommandMsg, using DoorReportMsg, using DoorsReportMsg, using DispatchReportMsg, using GuidMsg, using GarageEventMsg, using LiftReportMsg, using OdpObserverMsg, using VehicleBayPoseMsg, using Payloadmsg, using VersionInfoMsg, using VehicleProxSensorMsg, using IoLinkSensorsMsg
      - `bay_retrieve_state_machine.hpp` (110) — class RetrieveStateMachine, enum State, enum Event
      - `bay_state_machine.hpp` (900) — class BayStateMachine, enum State, enum Event, enum Command
      - `bay_state_machine_ros.hpp` (95) — class BayStateMachineRos, using Trigger
      - `bay_timings.hpp` (16)
      - `bay_transition_state_machine.hpp` (205) — class BayTransitionStateMachine, enum State, enum Event
      - `break_beam_sensor.hpp` (42) — class BreakBeamSensor, class BreakBeamSensors
      - `doors_interface.hpp` (27) — class Interface
      - `doors_interface_base.hpp` (105) — class InterfaceBase, enum State, enum Action, using DoorId, using Doors
      - `garage_door_control.hpp` (50) — class GarageDoorControl
      - `garage_door_ros.hpp` (43) — class GarageDoorRos
      - `guidance_payload.hpp` (84) — struct GuidanceLidars, struct GuidancePose, struct GuidanceVelocity, struct GuidanceDimensions, struct GuidanceVehicle, struct GuidancePayload · "Vehicle physical characteristics (VehicleBayPose.msg's height/width/length/wheelbase)."
      - `guidance_websocket_server.hpp` (70) — class GuidanceWebSocketServer · "Broadcasts guidance JSON (see bay/schemas/bay_guidance.schema) to any connected"
      - `io_link_driver.hpp` (54) — class IoLinkDriver
      - `io_link_master.hpp` (64) — struct IoLinkMasterConfig, class IoLinkMaster
      - `lift_interface.hpp` (35) — class LiftInterface
      - `lift_interface_ros.hpp` (56) — class LiftInterfaceRos
      - `load_cell_driver.hpp` (66) — class LoadCellDriver
      - `odp_door_control.hpp` (81) — class OdpDoorControl
      - `open_close_state_machine.hpp` (145) — class OpenCloseStateMachine, enum DoorState, enum Action
      - `plc_control.hpp` (51) — class PlcControl
      - `plc_modbus_addresses.hpp` (162) — struct DoorAddresses, struct OdpSensorAddresses, enum DoorType
      - `vehicle_estimator.hpp` (84) — class VehicleEstimator, struct Config · "Estimates the pose of patron vehicles as they enter the bay. Discrete sensor inputs are"
      - `vehicle_estimator_ros.hpp` (40) — class VehicleEstimatorRos
      - `vehicle_proximity_sensor.hpp` (33) — class VehicleProximitySensor
  - `schemas/` — data, 1 files: bay_guidance
  - `src/`
    - `sim/`
      - `garage_door_sim.cpp` (166)
      - `perfect_doors.cpp` (65)
    - `axis_filter.cpp` (58)
    - `axle_counter.cpp` (145)
    - `bay_floor_spec.cpp` (101)
    - `bay_guidance.cpp` (313) — "Websocket params"
    - `bay_guidance_component.cpp` (24) — component bay::BayGuidanceComponent
    - `bay_insert_state_machine.cpp` (167)
    - `bay_retrieve_state_machine.cpp` (90)
    - `bay_state_machine_component.cpp` (35) — component bay::StateMachineComponent
    - `bay_state_machine_ros.cpp` (308)
    - `blift_state_machine_component.cpp` (50) — component bay::BliftStateMachineComponent
    - `break_beam_sensor.cpp` (62)
    - `doors_interface.cpp` (72)
    - `doors_interface_base.cpp` (209)
    - `garage_door_control.cpp` (80)
    - `garage_door_ros.cpp` (60)
    - `guidance_websocket_server.cpp` (176)
    - `io_link_driver.cpp` (247)
    - `io_link_driver_component.cpp` (35) — component bay::IoLinkDriverComponent
    - `io_link_master.cpp` (290)
    - `load_cell_driver.cpp` (312)
    - `load_cell_driver_component.cpp` (40) — component bay::LoadCellDriverComponent
    - `odp_door_control.cpp` (172)
    - `open_close_state_machine.cpp` (169)
    - `plc_control.cpp` (125)
    - `plc_control_component.cpp` (64) — component bay::PlcControlComponent
    - `plc_modbus_addresses.cpp` (65)
    - `vehicle_estimator.cpp` (241)
    - `vehicle_estimator_component.cpp` (44) — component bay::VehicleEstimatorComponent
    - `vehicle_estimator_ros.cpp` (67)
    - `vehicle_proximity_sensor.cpp` (36)
    - `vrc_lift_bridge_component.cpp` (155) — component bay::VrcLiftBridgeComponent
  - `test/` — 16 files, 132 test cases: axis_filter_tests, axle_counter_tests, bay_floor_spec_tests, bay_guidance_tests, bay_insert_state_machine_tests, bay_reset.test, bay_retrieve_state_machine_tests, bay_state_machine_tests, bay_transition_state_machine_tests, break_beam_sensor_tests, doors_interface_tests, garage_door_sim_tests, guidance_websocket_server_tests, open_close_state_machine_tests, vehicle_estimator_ros_tests, vehicle_estimator_tests
  - `CMakeLists.txt` (245)
  - `package.xml` (42)

#### `central` · `src/central` · ament_cmake · 23,863 lines
> Central cluster ROS nodes
- **depends on (workspace):** agv_interfaces, common, common_ros, interfaces, launcher, otel, rclcppx, vrc_interfaces
- **depends on (external):** ament_cmake, ament_cmake_gtest, ament_index_cpp, libboost-dev, libmysqlcppconn-dev, nlohmann-json-dev, rclcpp, rclcpp_action, rclcpp_components, std_srvs, yaml-cpp
- **used by:** sim
- **files:**
  - `include/`
    - `central/`
      - `agv_monitor.hpp` (36) — class AgvMonitor
      - `agv_monitor_ros.hpp` (25) — class AgvMonitorRos
      - `central_msgs.hpp` (191) — using ActionNodeMsg, using AgvStateMsg, using AgvCommandMsg, using AgvCommandSequenceMsg, using AgvCommandStatusMsg, using AgvSimStateMsg, using AgvSnapshotMsg, using AgvReportMsg, using BayCommandMsg, using BayReportMsg, using BayStateMsg, using ConsistencyReportMsg, using ConsistencyReportMsgUPtr, using ContinuousGarageAgvInfoMsg
      - `central_timing.hpp` (57)
      - `charge_agvs.hpp` (21)
      - `command_send.hpp` (76) — class CommandSend, class CommandSendFunctions, using CommandSendSPtr
      - `consistency_monitor.hpp` (56) — class ConsistencyMonitor
      - `consistency_monitor_ros.hpp` (38) — class ConsistencyMonitorRos
      - `dispatch.hpp` (352) — struct DispatchParams, struct LastPlanCallData, class Dispatch, enum Status, enum Mode, enum PlanRequestStrategy
      - `dispatch_jobs.hpp` (416) — class Job, class ChargeAgvJob, class CleanGarageJob, class RebalanceGarageJob, class MoveAgvJob, class MoveTrayJob, class ReparkTrayJob, class ReadyForInsertJob, class ReadyForRetrieveJob, class TransitionBayToInsertJob, class TransitionBayToRetrieveJob, class RetrieveJob, class InsertJob, class ChargePayloadJob, …
      - `dispatch_ros.hpp` (138) — struct AgvClients, struct BayClients, struct VecsClients, struct VrcClients, class DispatchRos
      - `execution_garage_state.hpp` (54) — class ExecutionGarageState
      - `execution_state.hpp` (142) — class ExecutionState, using ExecutionStateSPtr, using ExecutionStateStringPair
      - `execution_state_util.hpp` (57) — "Check whether the event's source node matches the command's source node."
      - `garage_monitor.hpp` (40) — class GarageMonitor
      - `garage_monitor_ros.hpp` (30) — class GarageMonitorRos
      - `garage_tracker.hpp` (196) — class GarageTracker
      - `garage_tracker_mysql_io.hpp` (137) — struct GarageDatabaseParameters
      - `garage_tracker_recovery_args.hpp` (37) — struct Options, enum Command
      - `garage_tracker_ros.hpp` (72) — class GarageTrackerRos
      - `metrics_recorder.hpp` (143) — class MetricsRecorder, struct BayStateEntry, struct DispatchStateEntry, struct DispatchStatusMode, using BayReportMsg, using AgvReportMsg, using NodeAccuracyMsg, using ContinuousGarageInfoMsg, using DiscreteGarageStateMsg, using DispatchReportMsg, using SchedulerJobListMsg, using SchedulerJobMsg
      - `mqtt_bridge.hpp` (45) — class MqttBridge
      - `mqtt_bridge_constants.hpp` (25)
      - `mqtt_bridge_ros.hpp` (25) — class MqttBridgeRos
      - `safety_hardware_monitor_ros.hpp` (22) — class SafetyHardwareMonitorRos
      - `schedule.hpp` (153) — class MotionBatch, class Schedule, enum MotionBatchState, using MotionBatchSPtr, using NodeBatchMap
      - `schedule_execution.hpp` (29) — class ScheduleExecution
      - `send_ready_agv_adaptor.hpp` (30) — class SendReadyAgvAdaptor
  - `src/`
    - `agv_monitor.cpp` (52)
    - `agv_monitor_component.cpp` (37) — component central::AgvMonitorComponent
    - `agv_monitor_ros.cpp` (36)
    - `charge_agvs.cpp` (100)
    - `command_send.cpp` (57)
    - `consistency_monitor.cpp` (150)
    - `consistency_monitor_component.cpp` (24) — component central::ConsistencyMonitorComponent
    - `consistency_monitor_ros.cpp` (61)
    - `dispatch.cpp` (2090)
    - `dispatch_component.cpp` (64) — component central::DispatchComponent
    - `dispatch_jobs.cpp` (246)
    - `dispatch_ros.cpp` (540)
    - `execution_garage_state.cpp` (314)
    - `execution_state.cpp` (1174)
    - `execution_state_util.cpp` (150)
    - `garage_monitor.cpp` (167)
    - `garage_monitor_component.cpp` (37) — component central::GarageMonitorComponent
    - `garage_monitor_ros.cpp` (40)
    - `garage_tracker.cpp` (1245)
    - `garage_tracker_component.cpp` (82) — component central::GarageTrackerComponent
    - `garage_tracker_mysql_io.cpp` (530)
    - `garage_tracker_recovery.cpp` (324) — main()
    - `garage_tracker_recovery_args.cpp` (229)
    - `garage_tracker_ros.cpp` (244)
    - `metrics_recorder.cpp` (335)
    - `metrics_recorder_component.cpp` (22) — component central::MetricsRecorderComponent
    - `mqtt_bridge.cpp` (265)
    - `mqtt_bridge_component.cpp` (24) — component central::MqttBridgeComponent
    - `mqtt_bridge_ros.cpp` (80)
    - `safety_hardware_monitor_component.cpp` (29) — component central::SafetyHardwareMonitorComponent
    - `safety_hardware_monitor_ros.cpp` (26)
    - `schedule.cpp` (475)
    - `schedule_execution.cpp` (32)
    - `send_ready_agv_adaptor.cpp` (147)
  - `test/` — 15 files, 202 test cases: agv_monitor_tests, charge_agvs_tests, consistency_monitor_ros_tests, consistency_monitor_tests, dispatch_jobs_tests, dispatch_tests, execution_garage_state_tests, execution_state_tests, garage_monitor_tests, garage_tracker_mysql_io_tests, garage_tracker_recovery_args_tests, garage_tracker_ros_tests, garage_tracker_tests, mqtt_bridge_tests, schedule_tests
  - `CMakeLists.txt` (222)
  - `package.xml` (39)

#### `lift` · `src/lift` · ament_cmake · 1,462 lines
> Lift state machine and control
- **depends on (workspace):** common, common_ros, interfaces, rclcppx, structures
- **depends on (external):** ament_cmake, ament_cmake_gtest, rclcpp, rclcpp_components, std_srvs
- **used by:** — (leaf)
- **files:**
  - `include/`
    - `lift/`
      - `autoquip_control.hpp` (89) — class AutoquipControl, enum MoveState
      - `autoquip_ros.hpp` (34) — class AutoquipRos
      - `lift_control.hpp` (61) — class LiftControl, struct Status
      - `lift_msgs.hpp` (11) — using LiftReportMsg, using SetUInt8Srv, using TriggerSrv
      - `lift_ros.hpp` (68) — class LiftRos
      - `lift_state_machine.hpp` (93) — class LiftStateMachine, enum State, enum Event, enum Command
  - `src/`
    - `autoquip_control.cpp` (384)
    - `lift_component.cpp` (48) — component lift::LiftComponent
    - `lift_control.cpp` (25)
    - `lift_state_machine.cpp` (155)
    - `vcr_component.cpp` (144) — component lift::VCRControlComponent
  - `test/` — 3 files, 1 test cases: autoquip_control_tests, lift_control_tests, lift_state_machine_tests
  - `CMakeLists.txt` (61)
  - `package.xml` (27)

#### `vecs` · `src/vecs` · ament_cmake · 2,479 lines
> Code related to the electric vehicle charging robot
- **depends on (workspace):** common, common_ros, interfaces, launcher, rclcppx, structures
- **depends on (external):** ament_cmake, ament_cmake_gtest, libmsgsl-dev, rclcpp, rclcpp_components, rclpy, std_srvs
- **used by:** — (leaf)
- **files:**
  - `include/`
    - `vecs/`
      - `evse_modbus_addresses.hpp` (29)
      - `io_modbus_addresses.hpp` (29)
      - `vecs.hpp` (150) — struct CommandSendFunctions, class Vecs, enum State, enum Event, enum Command, enum CommandStatus
      - `vecs_evse_control.hpp` (168) — struct ChargingState, class VecsEvseControl, enum Phase, enum State
      - `vecs_evse_ros.hpp` (64) — class VecsEvseRos · "ROS Types //////////"
      - `vecs_io_control.hpp` (112) — class VecsIoControl, enum Button, enum Led
      - `vecs_io_ros.hpp` (63) — class VecsIoRos · "ROS Types //////////"
      - `vecs_ros.hpp` (98) — class VecsRos
      - `vecs_sim.hpp` (103) — class VecsSim, class VecsHardwareSimRos
  - `src/`
    - `vecs.cpp` (185)
    - `vecs_component.cpp` (37) — component vecs::VecsComponent
    - `vecs_evse_component.cpp` (42) — component vecs::evse::VecsEvseComponent
    - `vecs_evse_control.cpp` (242)
    - `vecs_evse_ros.cpp` (112)
    - `vecs_io_component.cpp` (42) — component vecs::io::VecsIoComponent
    - `vecs_io_control.cpp` (151)
    - `vecs_io_ros.cpp` (109)
    - `vecs_ros.cpp` (206)
    - `vecs_sim.cpp` (193)
    - `vecs_sim_component.cpp` (35) — component vecs::sim::VecsSimComponent
  - `test/` — 3 files, 6 test cases: vecs_evse_control_tests, vecs_io_control_tests, vecs_tests
  - `CMakeLists.txt` (84)
  - `README.md` (39)
  - `package.xml` (30)

#### `vis` · `src/vis` · ament_cmake · 2,829 lines
> Visualization nodes and utilities
- **depends on (workspace):** bay_interfaces, common, common_ros, interfaces, launcher, vrc_interfaces
- **depends on (external):** ament_cmake, ament_cmake_gtest, backward_ros, eigen, geometry_msgs, rclcpp, std_msgs, visualization_msgs
- **used by:** sim
- **files:**
  - `config/` — data, 1 files: default.rviz
  - `include/`
    - `vis/`
      - `visualizer/`
        - `agv_visualizer.hpp` (42) — class AgvVisualizer
        - `bay_visualizer.hpp` (44) — class BayVisualizer, struct OdpAnimState
        - `i_visualizer.hpp` (34) — struct VisMessage, class IVisualizer, using VisualizerUPtr
        - `layout_visualizer.hpp` (43) — class LayoutVisualizer
        - `queue_visualizer.hpp` (60) — class QueueVisualizer
        - `schedule_visualizer.hpp` (27) — class ScheduleVisualizer
        - `tray_visualizer.hpp` (43) — class TrayVisualizer
        - `vrc_visualizer.hpp` (39) — class VrcVisualizer
      - `math.hpp` (26)
      - `models.hpp` (48) — struct CarModel, enum BayPiece
      - `topics.hpp` (27)
      - `utils.hpp` (50) — struct VisAgvCommandConfig
      - `vis_context.hpp` (31) — class VisContext, using VisContextSPtr
      - `vis_manager.hpp` (72) — class VisManager, using MarkerArrayPub, using MarkerArrayPubSPtr
  - `src/`
    - `visualizer/`
      - `agv_visualizer.cpp` (119)
      - `bay_visualizer.cpp` (277)
      - `layout_visualizer.cpp` (317)
      - `queue_visualizer.cpp` (271)
      - `schedule_visualizer.cpp` (54)
      - `tray_visualizer.cpp` (129)
      - `vrc_visualizer.cpp` (208)
    - `math.cpp` (75)
    - `models.cpp` (293)
    - `utils.cpp` (212)
    - `vis_manager.cpp` (148)
    - `visualizer_node.cpp` (20) — main()
  - `test/` — 1 files, 5 test cases: math_test
  - `CMakeLists.txt` (26)
  - `package.xml` (32)

#### `vrc` · `src/vrc` · ament_cmake · 2,256 lines
> Vertical Reciprocating Conveyor (VRC) module
- **depends on (workspace):** common, rclcppx, stdx, vrc_interfaces
- **depends on (external):** ament_cmake_gtest, backward_ros, rclcpp, rclcpp_action, rclcpp_components, yasmin
- **used by:** — (leaf)
- **files:**
  - `include/`
    - `vrc/`
      - `drivers/`
        - `i_hw_driver.hpp` (122) — struct HardwareStatus, class ProtectedHardwareStatus, class IHwDriver, using IHwDriverSPtr · "Snapshot of the current driver hardware state."
        - `mock_hw_driver.hpp` (50) — struct MockHWDriverConfig, class MockHWDriver · "Tunable kinematics for the simulated VRC."
      - `sm/`
        - `blackboard.hpp` (25) — struct Request, enum Command, using TypeRequest, using TypeHWDriver · "Blackboard specific key strings and type aliases"
        - `closing_state.hpp` (13) — class ClosingState
        - `error_state.hpp` (13) — class ErrorState
        - `idle_state.hpp` (19) — class IdleState · "Signal used to wake this state's execution loop"
        - `initializing_state.hpp` (13) — class InitializingState
        - `moving_state.hpp` (13) — class MovingState
        - `opening_state.hpp` (13) — class OpeningState
        - `state_strings.hpp` (26)
      - `core_types.hpp` (49) — struct FloorConfig, struct VrcStatus, enum GateState, using FloorNumber, using FloorConfigMap, using GateStateMap, using WakeSignal, using WakeSignalSPtr · "Configuration parameters for a single floor."
      - `manager.hpp` (54) — class Manager, using LogFunction · "Manages the VRC state machine and coordinates hardware operations."
      - `msg_conversions.hpp` (88) — using GateStateMsg, using VrcStateMsg, using VrcReport, using GateReportMsg · "Convert an internal @ref GateState enumeration to the corresponding GateState ROS message."
  - `launch/`
    - `single.launch.py` (50) — runs vrc
  - `src/`
    - `drivers/`
      - `mock_hw_driver.cpp` (149)
    - `sm/`
      - `closing_state.cpp` (65)
      - `error_state.cpp` (14)
      - `idle_state.cpp` (65)
      - `initializing_state.cpp` (26)
      - `moving_state.cpp` (41)
      - `opening_state.cpp` (73)
    - `manager.cpp` (180)
    - `ros_node.cpp` (277) — component volley::vrc::RosNode · "Forward a yasmin-sourced log message through the provided @c rclcpp logger while"
    - `ros_node.hpp` (79) — class RosNode, struct Params, using VrcMoveAction, using VrcMoveHandle, using VrcReportMsg · "ROS2 node for a single Vertical Reciprocating Conveyor (VRC)."
  - `test/` — 9 files, 40 test cases: stub_hw_driver, test_closing_state, test_error_state, test_idle_state, test_initializing_state, test_manager, test_mock_hw_driver, test_moving_state, test_opening_state
  - `CMakeLists.txt` (89)
  - `package.xml` (29)

### Layer 11 · integration

#### `agvhito_tools` · `src/agvhito_tools` · ament_cmake · 2,165 lines
> Command-line tools for testing HITO AGVs
- **depends on (workspace):** agvhito, common, common_ros, interfaces, launcher, mqtt, scheduler, stdx, vda5050_interfaces
- **depends on (external):** ament_cmake_gtest, fmt, rclcpp, uuid, yaml-cpp
- **used by:** — (leaf)
- **files:**
  - `config/` — data, 1 files: agvctl
  - `include/`
    - `agvhito_tools/`
      - `print.hpp` (63) — "Prints a formatted error message to stderr."
  - `src/`
    - `agvctl/`
      - `agv_ctl.cpp` (702)
      - `agv_ctl.hpp` (192) — class AgvCtl, struct PublishedAction, struct PublishedOrder · "CLI that controls a single HITO AGV directly over VDA5050 MQTT topics."
      - `agv_ctl_config.cpp` (103) — "@return The @p key child of @p node."
      - `agv_ctl_config.hpp` (63) — struct AgvCtlConfig, struct convert · "Required agvctl configuration."
      - `app.cpp` (119) — main()
      - `interrupt.cpp` (29)
      - `interrupt.hpp` (11) — "Installs the `SIGINT` handler backing @ref IsInterrupted."
      - `move_planner.cpp` (83)
      - `move_planner.hpp` (28) — class MovePlanner · "Plans a single AGV move against a discrete garage state holding only that AGV."
      - `parse_utils.cpp` (44)
      - `parse_utils.hpp` (18) — "@return All of @p text parsed as an integer, or `std::nullopt` on trailing or non-numeric characters."
      - `verb_console.hpp` (47) — class VerbConsole · "Prints one CLI verb's output to its session stream, prefixed with the time and the verb it belongs to."
    - `listener/`
      - `app.cpp` (104) — main()
      - `listener.cpp` (159)
      - `listener.hpp` (53) — struct ListenerOptions, class Listener · "Prints message information for VDA5050 MQTT topics published by a single HITO AGV."
      - `topic_rate_stats.cpp` (69)
      - `topic_rate_stats.hpp` (42) — class TopicRateStats, using Clock, using Seconds · "Tracks arrival rate statistics."
  - `test/` — 2 files, 14 test cases: test_agv_ctl_config, test_parse_utils
  - `CMakeLists.txt` (51)
  - `package.xml` (32)

#### `scheduler_advanced_tests` · `src/planner/scheduler_advanced_tests` · ament_cmake · 2,399 lines
> Advanced scenario testing just for scheduler.
- **depends on (workspace):** common_ros, launcher, motion_planner, scheduler
- **depends on (external):** ament_cmake_gtest, rclcpp, yaml-cpp
- **used by:** — (leaf)
- **files:**
  - `test/` — 7 files, 17 test cases: scheduler_advanced_scenario_test01, scheduler_advanced_scenario_test02, scheduler_advanced_scenario_test03, scheduler_advanced_scenario_test04, scheduler_advanced_scenario_test05, scheduler_advanced_scenario_test06, scheduler_advanced_scenario_test07
  - `CMakeLists.txt` (67)
  - `package.xml` (24)

#### `sim` · `src/sim` · ament_cmake · 9,822 lines
> Simulation nodes and utilities
- **depends on (workspace):** bay, bay_interfaces, central, common, common_ros, interfaces, launcher, rclcppx, structures, system_tests, vis
- **depends on (external):** ament_cmake, ament_cmake_gtest, ament_index_cpp, backward_ros, geometry_msgs, libmysqlcppconn-dev, rclcpp, rclcpp_components, rosgraph_msgs, std_srvs, yaml-cpp
- **used by:** — (leaf)
- **files:**
  - `include/`
    - `sim/`
      - `bay_sim.hpp` (118) — class BaySim, using BayDoors · "Main tick function used to update the simulated bay. `tray_opt` is the tray, if any, that is currently"
      - `collision_detector.hpp` (85) — struct BodyIdentifier, struct BodyData, class CollisionDetector, enum BodyType
      - `collision_utils.hpp` (35) — using BoxVertices
      - `oriented_bounding_box.hpp` (32) — struct OrientedBoundingBox, struct OrientedBoundingBox3D
      - `patrons.hpp` (46) — struct PayloadComparator, class Patrons
      - `scenario_runner.hpp` (117) — struct InitialConditions, struct Event, class ScenarioRunner, enum Type
      - `sim_clients.hpp` (66) — class SimClients · "Container for ROS clients used by the simulator to request jobs/actions from the rest of the stack"
      - `sim_msgs.hpp` (151) — using AgvBatteryFractionMsg, using AgvStateMsg, using AgvStopSrv, using AgvReportMsg, using AgvCommandMsg, using AgvSimStateMsg, using AgvCommandReportListMsg, using AgvCommandReportMsg, using AgvFaultMsg, using AgvGoalMsg, using AgvSnapshotMsg, using BayReportMsg, using BayCommandMsg, using BayStateMsg
      - `simulator.hpp` (98) — class Simulator · "A class that manages the simulation based on a provided scenario file. This class also manages"
      - `tray.hpp` (29) — struct Tray
  - `python/`
    - `agv_simulation/`
      - `agv_model/`
        - `__init__.py`
        - `agv_dynamics.py` (704) — class AgvDynamics · "documentation for the dynamics of a mecanum wheel robot used in this code"
        - `agv_kinematics.py` (640) — class AgvKinematics · "documentation for the kinematics of a mecanum wheel robot used in this code"
        - `eight_wheeled_robot_graphics.py` (426) — class EightWheeledRobotGraphics · "This module outlines the graphics for a four wheeled mecanum robot"
        - `four_wheeled_robot_graphics.py` (393) — class FourWheeledRobotGraphics · "This module outlines the graphics for a four wheeled mecanum robot"
        - `mecanum_wheel.py` (135) — class MecanumWheel, def calc_wheel_jacobian, def calc_actuated_wheel_jacobian, def calc_nonactuated_wheel_jacobian · "Documentation for the kinematic and dynamic properties of a mecanum wheel"
      - `documentation/` — data, 0 files: 
      - `scripts/`
        - `dynamic_simulation_eight_wheels.py` (329) — def update_lines · "Dynamic Simulation of an eight wheeled AGV"
        - `dynamics_simulation.py` (227) — def update_lines · "Nonlinear dynamic simulation of a 4 wheeled AGV"
        - `kinematics_eight_wheel_simulation.py` (290) — def update_lines · "Kinematic simulation of an eight wheeled AGV"
        - `kinematics_simulation.py` (208) — def update_lines · "Kinematic simulation of a four wheeled AGV"
        - `simulation_parameters.py` (36) — "These parameters are used for simulation of the AGV. The parameter values"
      - `tests/` — 9 files, 61 test cases: coupled_and_passive_wheel_dynamics_test, coupled_and_passive_wheel_kinematics_test, inclined_dynamics_tests, mecanum_wheel_tests, simplified_dynamics_tests, simplified_kinematics_tests, slip_and_slide_kinematics_tests, slip_friction_dynamics_tests, testing_parameters
      - `README.md` (8)
      - `setup.py` (10)
  - `scripts/`
    - `confirm_insert.bash`
    - `trigger_patron_arrival.bash`
  - `src/`
    - `bay_sim.cpp` (355)
    - `bay_sim_component.cpp` (108) — component volley::sim::BaySimComponent
    - `collision_detector.cpp` (159)
    - `collision_utils.cpp` (69)
    - `oriented_bounding_box.cpp` (114)
    - `patrons.cpp` (37)
    - `scenario_runner.cpp` (225)
    - `sim_clients.cpp` (239)
    - `sim_clock_component.cpp` (84) — component volley::sim::SimClockComponent · "A class used to publish time for the entire system when running simulation"
    - `simulator.cpp` (348)
    - `simulator_component.cpp` (31) — component volley::sim::SimulatorComponent · "Thin component wrapper that loads the scenario and creates a Simulator that runs the simulation"
    - `tray.cpp` (13)
  - `test/` — 4 files, 20 test cases: bay_sim_tests, obb_collision_tests, patrons_tests, scenario_runner_tests
  - `CMakeLists.txt` (68)
  - `package.xml` (41)

#### `system_tests` · `src/system_tests` · ament_python · 5,756 lines
> Contains system tests and supporting code
- **depends on (workspace):** bay_interfaces, common_py, interfaces, launcher, scenario
- **depends on (external):** ament_cmake_pytest, rclpy
- **used by:** sim
- **files:**
  - `resource/`
    - `system_tests`
  - `system_tests/`
    - `__init__.py`
    - `trial_node.py` (667) — def to_seconds, def header_stamp_is_zero, class TrialNode
    - `utils.py` (104) — def angle_dist, def is_near_angle_or_reciprocal, def is_near_geometric_pose, def is_near_geometric_pose_or_reciprocal, def load_layout_for_scenario, def run_system_test
  - `test/` — 1 files, 4 test cases: test_utils
  - `tests/` — 45 files, 45 test cases: run_scenario, system_agv_cannot_move_disabled_tray, system_agv_cannot_move_to_disabled_bay, system_agv_cannot_move_to_disabled_node, system_agv_deactivates, system_bay_error_stops_garage, system_bays_correct_state_to_start_and_stop, system_blift_single_insert, system_blift_single_retrieve, system_charge_then_insert, system_charge_then_repark, system_charge_then_retrieve, system_clean_garage_unstashes_waypoint, system_deviate_from_plan_with_agv, system_disabled_agvs_are_not_used, system_double_tray_move, system_drain_garage, system_ev_charge_insert_and_retrieve, system_fill_garage, system_get_job_state, system_insert_car_onto_last_tray, system_low_agv_voltage_causes_disable, system_manual_planner_calls, system_move_agv, system_move_agv_min_node_spacing, …
  - `package.xml` (21)
  - `setup.cfg`
  - `setup.py` (33)

### Layer 3–6 · Python chain / top

#### `central_api` · `src/central_api` · ament_python · 3,654 lines
> Contains the interface between ROS nodes in the central cluster and the NOC, app
- **depends on (workspace):** common, interfaces
- **depends on (external):** ament_cmake_pytest, python3-pytest, rclpy, std_msgs, std_srvs
- **used by:** launcher
- **files:**
  - `central_api/`
    - `garage_info/`
      - `0003.json` (19)
      - `9999.json` (19)
    - `__init__.py`
    - `rest_api.py` (3472) — class BaseModel, class KioskAdmin, class Patrons, class PayloadType, class TransactionType, class Payloads, class PayloadClaims, class RetrievalCodes, class Transactions, def create_tables, …
    - `rosout_recorder.py` (48) — class RosoutRecorder
  - `central_api_demo/`
    - `README.md` (78)
    - `Taskfile.yaml` (97)
    - `__init__.py`
    - `rest_api_mock.py` (105) — def is_valid_uuid, def health, def confirm_insert, def get_job_state, def retrieve_payload, def confirm_retrieve
  - `proxy/`
    - `README.md` (1)
    - `Taskfile.yaml` (91)
  - `resource/`
    - `central_api`
  - `README.md` (9)
  - `package.xml` (24)
  - `setup.cfg`
  - `setup.py` (29)

#### `common_py` · `src/common_py` · ament_python · 3,898 lines
> Common python packages
- **depends on (workspace):** interfaces
- **depends on (external):** ament_cmake_pytest, python3-pytest, rclpy
- **used by:** system_tests, launcher, scenario, sim_metrics
- **files:**
  - `common_py/`
    - `processing/`
      - `__init__.py`
      - `grid_generation.py` (252) — def make_element_with_text, def wrap_heading_to_grid_bounds, def generate_grid_for_layout, def generate_grid_config_for_layout, def write_xml_element_to_utf8, def write_xml_element_to_string
      - `pose_geometry.py` (186) — def get_canonical_reversible_heading, def create_rectangle, def create_rotation_polygon, def create_edge_polygon, def calc_pose_overlaps, def get_pose_polygons, def calc_overlapping_sized_poses
    - `__init__.py`
    - `batch_config.py` (38) — class BatchConfig
    - `general_utils.py` (218) — def wrap_deg, def merge_params_dict, def log_garage_event, def make_guid, def random_guid, def parse_guid, def guid_to_string, def is_empty_guid, def are_guids_equal, def ros_msg_from_dict, …
    - `git_utils.py` (53) — def get_base_repo_dir, def get_volley_gitsha
    - `layout.py` (531) — def get_headings_for_node, def get_inbound_heading, def get_outbound_heading, def get_tray_parking_window, def get_resource_windows, def resource_windows_are_valid, def get_agv_size, class Layout, def get_layouts_directory, def get_layout_filepath, …
    - `layout_generation.py` (202) — def make_edge, def get_closest_directional_node, def generate_stacked_corridors
    - `pose_graph.py` (281) — def angle_dist, class Pose, def calc_move_duration, class PoseGraph
    - `scenario.py` (241) — def get_num_initial_payloads, def get_num_events_of_type, def load_scenario, def get_scenario_filepath, def load_scenario_by_name, def load_initial_conditions, def get_discrete_garage_state_from_scenario, def get_scenario_base_from_discrete_garage_state
    - `scenario_generation.py` (506) — def get_blift_vrc_initial_conditions, def create_ith_payload_id, def get_auto_startup_events, def get_gamma_from_mean_and_variance, def generate_default_tray_initial_conditions, def create_payload_for_node, def spawn_payloads_on_trays, def spawn_agvs_under_trays, def generate_drain_scenario, def generate_fill_scenario, …
    - `shell_utils.py` (51) — def run_shell_command, def run_shell_command_with_success, def get_md5sum
  - `resource/`
    - `common_py`
  - `test/` — 6 files, 28 test cases: test_general_utils, test_layout, test_pose_geometry, test_pose_graph, test_scenario, test_shell_utils
  - `package.xml` (19)
  - `setup.cfg`
  - `setup.py` (24)

#### `launcher` · `src/launcher` · ament_python · 1,984 lines
> Launch files and associated material
- **depends on (workspace):** central_api, common_py, scenario
- **depends on (external):** ament_cmake_pytest, ament_index_python, foxglove_bridge, rcl_logging_noop, rclpy, rosbag2_storage_mcap, rosbag2_transport
- **used by:** common_ros, motion_planner, scheduler, agvhito, bay, central, vecs, vis, agvhito_tools, scheduler_advanced_tests, sim, system_tests
- **files:**
  - `launch/`
    - `support/`
      - `recorder.launch.xml` (67)
    - `bagplay.launch.py` (60) — runs visualizer_node
    - `bay.launch.py` (77) — runs component_container · includes recorder.launch.xml
    - `central.launch.py` (126) — runs component_container, metrics_recorder, visualizer_node · includes recorder.launch.xml
    - `lift.launch.py` (36) — runs component_container
    - `sim.launch.py` (12)
    - `vecs.launch.py` (39) — runs component_container
  - `launcher/`
    - `__init__.py`
    - `bay_nodes.py` (146) — def get_core_composable_nodes, def get_driver_composable_nodes
    - `central_nodes.py` (133) — def get_standalone_nodes, def get_composable_nodes
    - `layout_plotter.py` (199) — def plot_grid, def plot_nodes, def render_layout, def main · "Input a layout yaml file. Output generated layout visual."
    - `lift_nodes.py` (15) — def get_composable_nodes
    - `paths.py` (19) — def get_artifacts_dir, def get_ros_home_dir
    - `sim_nodes.py` (497) — def write_grid_to_file, def load_params_and_initial_conditions, def get_sim_clock_node, def get_sim_launch_description_entities, def get_sim_launch_description
    - `utils.py` (103) — def string_to_bool, def load_param_file, def load_params
    - `vecs_nodes.py` (90) — def get_vecs_sim_nodes, def make_core_nodes, def get_composable_hardware_driver_nodes, def make_composable_driver_nodes
    - `vrc_nodes.py` (53) — def get_vrc_sim_nodes
  - `layouts/` — data, 39 files: 1355_fulton, 175_e82nd, 25_spot_double_pick, 25_spot_single_pick, 25_spot_triple_pick, 275_sunrise_b, 360_w_broadway, 38_gramercy, 415_east_grand_ave, 550_w21st, 5675_pecos_bench, 5675_pecos_combined, 5675_pecos_sandbox_combined, 5675_pecos_sandbox_eng, 5675_pecos_sandbox_qa, 576_eccles, 576_eccles_budget_sandbox, 576_eccles_budget_sandbox_mini, 576_eccles_half, 576_eccles_hito_sandbox, 576_eccles_mini, 576_eccles_no_bay, 576_eccles_under_vcr, 5_southeast_martin_luther_king_blvd, CambridgesideV8, HQ_ev_test, cambridgewithlift, corridors_3_10, initial_conditions, kmart_nashville_layout, …
  - `params/` — data, 29 files: 360_w_broadway_blift_floor_spec, 38_gramercy_blift_floor_spec, params, params_1355_fulton, params_360_w_broadway, params_38_gramercy, params_415_east_grand_ave, params_5675_pecos_bench, params_5675_pecos_sandbox_combined, params_5675_pecos_sandbox_eng, params_5675_pecos_sandbox_qa, params_576_eccles, params_576_eccles_budget_sandbox, params_576_eccles_budget_sandbox_mini, params_576_eccles_half, params_576_eccles_mini, params_576_eccles_no_bay, params_576_eccles_under_vcr, params_agv, params_b21, params_b7, params_bay, params_central, params_l8, params_lift, params_sim, params_vecs, params_vrc_sandbox, vcr_blift_floor_spec
  - `resource/`
    - `launcher`
  - `scripts/`
    - `generate_layout.py` (54) — def generate_corridor_layout · "Helpful utility for generating layouts"
    - `layout_yaml_to_xml.py` (32) — def layout_yaml_to_xml
  - `test/` — 3 files, 13 test cases: test_launcher_utils, test_load_all_layout_yamls, test_paths
  - `package.xml` (25)
  - `setup.cfg`
  - `setup.py` (49)

#### `scenario` · `src/scenario` · ament_python · 803 lines
> Methods and nodes related to scenarios
- **depends on (workspace):** common_py, interfaces, sim_metrics
- **depends on (external):** python3-pytest, rclpy
- **used by:** system_tests, launcher
- **files:**
  - `batch_configs/` — data, 5 files: 550_14_car_pick_each, 550_15_car_pick_each, 550_16_car_pick_each, pecos_sandbox_eng, pecos_sandbox_qa
  - `resource/`
    - `scenario`
  - `scenario/`
    - `events/`
      - `__init__.py` (18)
      - `event_base.py` (247) — class EventContext, class EventBase, class SchedulerJobTracker
      - `move_agv_event.py` (27) — class MoveAgvEvent
      - `move_tray_event.py` (27) — class MoveTrayEvent
      - `patron_arrival_event.py` (97) — class PatronArrivalEvent
      - `repark_tray_event.py` (29) — class ReparkTrayEvent
      - `retrieve_request_event.py` (52) — class RetrieveRequestEvent
      - `sleep_event.py` (20) — class SleepEvent
    - `__init__.py`
    - `exercise_sim_events.py` (248) — class EventFactory, class ExerciseSimEventsNode, def end_simulation, def main · "Tool for exercising sim events"
  - `scenarios/` — data, 105 files: 175_e82nd_empty_start_in_auto, 175_e82nd_events_drain_from_full, 175_e82nd_events_fill_from_empty, 175_e82nd_events_move_each_node, 175_e82nd_full_start_in_auto, 175_e82nd_single_agv_start_in_manual, 275_sunrise_b_empty_start_in_auto, 275_sunrise_b_events_drain_from_full, 275_sunrise_b_events_fill_from_empty, 275_sunrise_b_events_move_each_node, 275_sunrise_b_full_start_in_auto, 275_sunrise_b_single_agv_start_in_manual, 360_w_broadway_empty_start_in_auto, 360_w_broadway_events_drain_from_full, 360_w_broadway_events_fill_from_empty, 360_w_broadway_full_start_in_auto, 38_gramercy_empty_no_op, 38_gramercy_empty_start_in_auto, 38_gramercy_events_drain_from_full, 38_gramercy_events_fill_from_empty, 38_gramercy_events_move_each_node, 38_gramercy_full_no_op, 38_gramercy_full_start_in_auto, 38_gramercy_single_agv_start_in_manual, 550_w21st_empty_start_in_auto, 550_w21st_events_drain_from_full, 550_w21st_events_fill_from_empty, 550_w21st_events_move_each_node, 550_w21st_full_start_in_auto, 550_w21st_single_agv_start_in_manual, …
  - `package.xml` (20)
  - `readme_payload_guid_bytes_to_vehicle_model_color.md` (195)
  - `setup.cfg`
  - `setup.py` (38)

#### `sim_metrics` · `src/sim_metrics` · ament_python · 3,608 lines
> Generate Batches of sim tests and extract metrics
- **depends on (workspace):** common_py, interfaces
- **depends on (external):** ament_index_python, rclpy, rosbag2_py, rosidl_runtime_py
- **used by:** scenario
- **files:**
  - `resource/`
    - `sim_metrics`
  - `scripts/`
    - `run_batch_job.sh`
  - `sim_metrics/`
    - `__init__.py`
    - `aggregate_batch_metrics.py` (889) — def m_to_mi, def sec_to_min, def sec_to_hr, def sec_to_time_string, def rad_to_revs, def safe_division, def get_scenario_name_from_main_log, def drop_zero_piechart_entries, def get_insert_times_in_minutes, def get_retrieve_times_in_minutes, …
    - `aws_batch_cli.py` (350) — def create_job_definition, def prompt, def sanitize, def submit_batch_impl, def cli, def list_jobs, def cancel_jobs, def list_job_defs, def submit_batch_job, def download_and_extract_results
    - `aws_common.py` (61) — def get_s3_file, def upload_config, def create_batch_client
    - `csv_metrics_utils.py` (277) — class JobStatus, class SimEventMetrics, class SimMetricsWriter, def read_events_from_csv, class BatchMetrics, def seconds_to_hhmmss, def summarize_csv
    - `download_cloudwatch_log_stream.py` (150) — def parse_args, def ms_to_utc, def iso_to_ms, def fetch_all_events, def main · "Download a CloudWatch log stream, with optional time filtering."
    - `extract_bag_metrics.py` (1134) — def angle_dist, def ros_stamp_to_seconds, def bag_timestamp_to_elapsed_seconds, def safe_division, def get_agv_ids, def get_bay_ids, def find_first_tray_at_node, def identify_payload_id_on_node_at_time, def get_first_discrete_garate_state_with_payload_id_on_tray, def calc_basic_gauge_statistics, …
    - `plot_pose_durations.py` (86) — def plot_polygon, def plot_pose_durations_heatmap
    - `read_bag.py` (122) — class BagReader
    - `scenario_stats.py` (500) — def iter_csv_keys, def percentile, def format_seconds, def format_hms, def format_mmss, def summarize, def plot_histogram, def histogram_path, def load_node_positions, def load_payload_node_map, … · "Compute average and worst-case retrieve_request metrics across all CSVs"
  - `package.xml` (20)
  - `setup.cfg`
  - `setup.py` (39)

