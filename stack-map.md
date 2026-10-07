# Volley stack map (bottom → top)

Compact reference for every session. Source: `colcon graph`, `volley-recon.sh` (commit fdd205e6, 2026-10-06). [seen] unless marked.

## Build & runtime facts

- ROS 2 Lyrical, 37 colcon packages, ~93k lines C++ / ~25k Python.
- **C++20, enforced** by `volley_cmake/cmake/volley_package.cmake`; `-Wall -Wextra -Wpedantic`.
- colcon defaults: symlink-install, RelWithDebInfo **with asserts**, ninja, mold, sccache, compile_commands.
- **ASan** on gtests (`volley_add_gtest.cmake`).
- clang-tidy: bugprone, cppcoreguidelines, clang-analyzer, google, modernize, naming. Exceptions are documented in `.clang-tidy` (JIRA SW2-750).
- Package macros: `volley_package`, `volley_add_library`, `volley_add_component`, `volley_add_executable`, `volley_add_gtest`, `volley_ament_auto_package`.
- Runtime: **29 rclcpp composable components**, composed by `src/launcher/launch/*.launch.py` (+ `agvhito/launch/proxy`, `vrc/launch/single`). No lifecycle nodes.
- Concurrency:
  - Mostly `SingleThreadedExecutor` (9 vs 1 multi-threaded).
  - Callback groups are all MutuallyExclusive.
  - Timers use `create_timer`, so they follow ROS/sim time.
- Files that start their own threads (high care):
  - `bay/src/guidance_websocket_server.cpp`
  - `common/src/heartbeat_monitor.cpp`
  - `communication/mqtt/src/client_impl.cpp`
  - `core/yasminx/src/root_state_machine.cpp`
  - `vrc/src/manager.cpp`
  - `agvhito_tools/src/agvctl/*`
- Errors: `std::optional` returns dominate; exceptions are also used (149 throw).
- External deps: yaml-cpp, nlohmann-json, Eigen, Boost, Paho MQTT C++, MySQL Connector/C++, OpenTelemetry, YASMIN, GSL, fmt, backward_ros, rosbag2/MCAP, foxglove_bridge.

## Layers (from `colcon graph`; each package only depends on layers below it)

| Layer | Packages | Used by (direct) |
|---|---|---|
| 0 Build | `volley_cmake` | 29 packages |
| 1 Core utilities | `stdx`, `rclcppx`, `yasminx` (→ agvhito), `mqtt` (→ agvhito, agvhito_tools), `otel` (→ central), `dds_discovery` (leaf) | stdx 8, rclcppx 13 |
| 1 Shared libraries | `common` (15 dependents), `structures` (bay, lift, vecs, sim) | many |
| 2 Contracts | `vrc_interfaces` → `interfaces` (18 dependents), `agv_interfaces`, `bay_interfaces`, `vda5050_interfaces` → `map_server` | almost all nodes |
| 3–6 Python chain | `common_py` → `sim_metrics` → `scenario` → `launcher`; `central_api` → `launcher` | `launcher`: 12 (incl. C++ pkgs) |
| 7 ROS glue | `common_ros` (13 dependents; oddly depends on `launcher`) | all node packages |
| 8 Planning libs | `task_planner` (only `volley_cmake`), `planner_core`, `cost_functions` | motion_planner, scheduler |
| 9 Motion planning | `motion_planner` | scheduler |
| 10 Scheduling | `scheduler` (SchedulerComponent) | agvhito_tools, scheduler_advanced_tests |
| 8 Nodes | `central`, `agvhito`, `bay`, `lift`, `vrc`, `vecs`, `vis` | sim (central, bay, vis) |
| 11 Integration | `sim`, `system_tests`, `scheduler_advanced_tests`, `agvhito_tools` | — |

**`central` does not link the scheduler or any planner.** They interact over ROS interfaces at runtime.

## Components per package

| Package | Components |
|---|---|
| central | Dispatch, GarageTracker (MySQL), AgvMonitor, GarageMonitor, ConsistencyMonitor, SafetyHardwareMonitor, MetricsRecorder, MqttBridge |
| bay | StateMachine, BliftStateMachine, BayGuidance, VehicleEstimator, PlcControl, IoLinkDriver, LoadCellDriver, VrcLiftBridge |
| scheduler | SchedulerComponent |
| agvhito | ProxyComponent, sim::SimAgvComponent |
| lift | LiftComponent, VCRControlComponent |
| vrc | RosNode |
| vecs | Vecs, evse::VecsEvse, io::VecsIo, sim::VecsSim (EV charging) [inferred] |
| sim | Simulator, SimClock, BaySim |

Other executables: `agvctl`, `listener` (agvhito_tools), `garage_tracker_recovery`, `discovery_probe`, `visualizer_node`, `geometry_visualization_tool`. Python entry points: `rest_api` (central_api), `server` (map_server), `exercise_sim_events`, `layout_plotter`.
