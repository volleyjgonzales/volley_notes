# Volley recon fact sheet

Generated 2026-10-06 at commit `fdd205e6` on branch `main`.

## Size by language (src tools controller_webview)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Language              Files        Lines         Code     Comments       Blanks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 JavaScript              386       151005        86806        13703        50496
 C++                     389       101617        77674         9495        14448
 YAML                    200        44541        42538         1134          869
 Python                  166        30212        24598         1396         4218
 C++ Header              306        25357        15707         4939         4711
 TeX                       1         3777         2855            0          922
 CSS                       3         2520         2207           97          216
 CMake                    41         2656         2067          208          381
 PHP                      30         2328         1498          434          396
 HCL                      29          979          851            7          121
 XML                      38         1047          847           14          186
 JSON                      9          724          722            0            2
 Autoconf                  1          357          357            0            0
 Shell                     5          436          294           58           84
 TypeScript               12          402          294           35           73
 Jinja2                    3           94           79            0           15
 BASH                      3          104           66           19           19
 Templ                     3           61           61            0            0
 Forge Config              7           28           28            0            0
 Markdown                 10          498            0          398          100
 Plain Text                3           58            0           47           11
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Total                  1645       368812       259560        31984        77268
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Size per package (C++ + Python code lines)

```
src/central                                   17428
src/common_ros                                15011
src/agvhito                                   10299
src/bay                                       10050
src/planner/scheduler                          9463
src/sim                                        8299
src/planner/motion_planner                     7787
src/system_tests                               4236
src/common                                     4045
src/common_py                                  3205
src/central_api                                3032
src/sim_metrics                                2941
src/vis                                        2214
src/planner/planner_core                       2006
src/planner/scheduler_advanced_tests           1872
src/vecs                                       1744
src/agvhito_tools                              1638
src/vrc                                        1591
src/launcher                                   1584
src/lift                                       1141
src/structures                                  843
src/vda5050/vda5050_interfaces                  807
src/communication/mqtt                          797
src/core/yasminx                                731
src/planner/task_planner                        687
src/planner/cost_functions                      659
src/scenario                                    621
src/core/rclcppx                                404
src/data/otel                                   324
src/vda5050/map_server                          276
src/infrastructure/dds_discovery                140
src/core/stdx                                    63
src/interfaces/bay_interfaces                    20
src/interfaces/vrc_interfaces                     0
src/interfaces/interfaces                         0
src/interfaces/agv_interfaces                     0
src/infrastructure/volley_cmake                   0
```

## Documentation inventory (words)

```
docs/architecture              10920 words (9 files)
docs/guides                     4771 words (8 files)
docs/tips-and-tricks            1314 words (3 files)
docs/deprecated                19764 words (9 files)
docs/papers                        0 words (0 files)
.claude/CLAUDE.md                119 words
README.md                         22 words
docs/index.md                     60 words
docs/glossary.md                  88 words
```

## Doc freshness (last commit date)

```
2026-09-28  docs/architecture/system-tests.md
2026-09-28  docs/architecture/sim.md
2026-09-28  docs/architecture/docker-build.md
2026-09-24  docs/guides/getting-started.md
2026-09-23  docs/deprecated/data_and_plotting.md
2026-09-23  docs/architecture/bay.md
2026-09-18  docs/deprecated/tech-debt.md
2026-09-18  docs/deprecated/scheduler.md
2026-09-18  docs/deprecated/overview.md
2026-09-16  docs/tips-and-tricks/ros.md
2026-09-16  docs/index.md
2026-09-16  docs/guides/simulation.md
2026-09-16  docs/guides/cpp-style.md
2026-09-11  docs/guides/volley-cmake.md
2026-09-10  docs/guides/mac-setup.md
2026-09-03  docs/tips-and-tricks/colcon.md
2026-08-28  docs/architecture/vrc.md
2026-08-27  docs/guides/release-workflow.md
2026-08-20  docs/architecture/discovery-server.md
2026-07-02  docs/deprecated/ros-nodes.md
2026-07-02  docs/deprecated/network-topology.md
2026-07-02  docs/deprecated/deployment.md
2026-07-02  docs/deprecated/central.md
2026-07-02  docs/deprecated/aws.md
2026-06-30  docs/coverage.md
2026-06-10  docs/architecture/apt-proxy.md
2026-06-04  docs/architecture/agv.md
2026-05-29  docs/guides/contributing.md
2026-05-04  docs/guides/simulation-in-cloud.md
2026-04-27  docs/architecture/vda5050.md
2026-04-15  docs/glossary.md
2026-04-13  README.md
2026-04-13  docs/tips-and-tricks/garage-cmds.md
2026-04-08  .claude/CLAUDE.md
2026-03-23  src/vecs/README.md
2026-03-23  src/sim/python/agv_simulation/README.md
2026-03-23  src/central_api/README.md
2026-03-23  src/central_api/proxy/README.md
2026-03-23  src/central_api/central_api_demo/README.md
2025-05-01  src/data/mqtt/terraform/README.md
--- code, for comparison ---
2026-10-05  src/system_tests
2026-10-05  src/launcher
2026-10-05  src/interfaces/interfaces
2026-10-05  src/common
2026-10-05  src/bay
2026-10-01  src/sim
2026-10-01  src/planner/scheduler
2026-10-01  src/planner/motion_planner
2026-10-01  src/interfaces/bay_interfaces
2026-10-01  src/infrastructure/volley_cmake
2026-10-01  src/core/rclcppx
2026-10-01  src/common_ros
2026-09-29  src/vrc
2026-09-29  src/vecs
2026-09-29  src/lift
2026-09-29  src/central_api
2026-09-29  src/central
2026-09-29  src/agvhito
2026-09-28  src/sim_metrics
2026-09-25  src/scenario
2026-09-24  src/interfaces/vrc_interfaces
2026-09-24  src/interfaces/agv_interfaces
2026-09-18  src/planner/task_planner
2026-09-18  src/planner/scheduler_advanced_tests
2026-09-18  src/planner/planner_core
2026-09-18  src/planner/cost_functions
2026-09-18  src/agvhito_tools
2026-09-16  src/vda5050/vda5050_interfaces
2026-09-16  src/infrastructure/dds_discovery
2026-09-16  src/data/otel
2026-09-16  src/core/yasminx
2026-09-16  src/common_py
2026-09-15  src/vis
2026-09-11  src/structures
2026-09-11  src/core/stdx
2026-09-11  src/communication/mqtt
2026-09-03  src/vda5050/map_server
```

## Package mentions in docs (0 = undocumented)

```
agvhito_tools                    0
dds_discovery                    0
map_server                       0
otel                             0
rclcppx                          0
stdx                             0
agv_interfaces                   1
cost_functions                   1
scheduler_advanced_tests         1
vda5050_interfaces               1
vrc_interfaces                   1
yasminx                          1
bay_interfaces                   2
mqtt                             2
planner_core                     2
sim_metrics                      2
task_planner                     2
common_py                        3
motion_planner                   3
vis                              3
volley_cmake                     3
vrc                              3
central_api                      4
structures                       4
system_tests                     4
agvhito                          5
common_ros                       5
launcher                         6
scenario                         6
vecs                             6
interfaces                       7
common                           8
sim                             11
scheduler                       12
bay                             15
lift                            15
central                         16
```

## C++ standard, warnings, sanitizers

```
src/vda5050/vda5050_interfaces/CMakeLists.txt:89:target_compile_features(${PROJECT_NAME}_cpp INTERFACE cxx_std_20)
src/infrastructure/volley_cmake/cmake/volley_package.cmake:1:set(CXX_STANDARD 20)
src/infrastructure/volley_cmake/cmake/volley_package.cmake:8:  if(CMAKE_CXX_STANDARD AND NOT CMAKE_CXX_STANDARD STREQUAL "${CXX_STANDARD}")
src/infrastructure/volley_cmake/cmake/volley_package.cmake:9:    message(WARNING "CMAKE_CXX_STANDARD ${CMAKE_CXX_STANDARD} overridden to ${CXX_STANDARD}")
src/infrastructure/volley_cmake/cmake/volley_package.cmake:12:  set(CMAKE_CXX_STANDARD ${CXX_STANDARD})
src/infrastructure/volley_cmake/cmake/volley_package.cmake:13:  set(CMAKE_CXX_STANDARD_REQUIRED ON)
src/infrastructure/volley_cmake/cmake/volley_add_gtest.cmake:87:    target_compile_options(${target} PRIVATE -fsanitize=address)
src/infrastructure/volley_cmake/cmake/volley_add_gtest.cmake:88:    target_link_options(${target} PRIVATE -fsanitize=address)
src/infrastructure/volley_cmake/cmake/volley_package.cmake:24:        -Wall                 # constructs commonly associated with defects
src/infrastructure/volley_cmake/cmake/volley_package.cmake:25:        -Wextra               # the same, for cases that are situational or harder to avoid
src/infrastructure/volley_cmake/cmake/volley_package.cmake:32:        -Wpedantic            # reliance on non-standard language extensions
```

## .colcon/defaults.yaml

```
---
# https://colcon.readthedocs.io/en/released/user/configuration.html#defaults-yaml

# event-handlers
#   - console_cohesion: groups each package's output together
#     Needed for ninja to properly report build failures
#     See:  https://github.com/colcon/colcon-cmake/issues/67)
#   - summary: show pass/fail/skip/abort summary at the end

build:
  symlink-install: true
  mixin:
    - build-testing-on
    - compile-commands
    - mold
    - ninja
    - rel-with-deb-info-assert
    - sccache
  event-handlers:
    - console_cohesion+
    - summary+

test:
  event-handlers:
    - console_cohesion+
    - summary+
```

## clang-tidy checks (head)

```
Checks: |
  -*,
  bugprone-*,
  cppcoreguidelines-*,
  clang-analyzer-*,
  google-*,
  modernize-*,
  readability-identifier-naming,
  -clang-analyzer-cplusplus.Move,
  -cppcoreguidelines-pro-bounds-array-to-pointer-decay,
  -cppcoreguidelines-pro-type-vararg,
  -cppcoreguidelines-avoid-magic-numbers,
  -modernize-pass-by-value,
  -modernize-use-trailing-return-type,
  -modernize-use-nodiscard,
  -bugprone-infinite-loop,
  -bugprone-easily-swappable-parameters,
  -modernize-deprecated-headers,
  -cppcoreguidelines-non-private-member-variables-in-classes,
  -cppcoreguidelines-avoid-c-arrays,
  -modernize-avoid-c-arrays,
  -cppcoreguidelines-special-member-functions,
  -hicpp-special-member-functions,
  -cppcoreguidelines-pro-bounds-pointer-arithmetic,
  -google-build-using-namespace,
  -modernize-use-designated-initializers,
  -modernize-replace-auto-ptr,
  -modernize-deprecated-ios-base-aliases,
  -google-readability-namespace-comments,

# For any disabled checks above, these are the recorded or inferred justifications.

# For current violation counts, file impacts and recommendations to keep or remove individual exceptions,
# see the JIRA ticket SW2-750, .ClangTidyChecks-findings.md attachment.

# -clang-analyzer-cplusplus.Move
#   We have an unavoidable issue in subscription->provide_intra_process_message(std::move(message)) deep within ROS.
#   Seems not to affect performance.
#
# -cppcoreguidelines-pro-bounds-array-to-pointer-decay
```

## Most-used CMake commands/macros

```
    129 volley_add_gtest
     47 find_package
     36 volley_add_library
     30 project
     30 cmake_minimum_required
     29 volley_package
     29 volley_ament_auto_package
     29 volley_add_component
     23 if
     23 endif
     12 target_include_directories
     12 set
     10 install
      9 file
      7 volley_add_executable
      6 ament_export_dependencies
      4 volley_glob_sources
      4 rosidl_generate_interfaces
      3 target_compile_options
      2 target_link_libraries
      2 list
      2 foreach
      2 endforeach
      2 ament_auto_depend_on_packages
      2 add_launch_test
```

## External dependencies (package.xml, excluding workspace packages)

```
     23 ament_cmake_gtest
     20 rclcpp
      9 yaml-cpp
      9 std_srvs
      9 rclpy
      8 rclcpp_components
      8 libboost-dev
      8 ament_index_cpp
      8 ament_cmake
      7 std_msgs
      7 nlohmann-json-dev
      7 eigen
      6 ament_cmake_pytest
      5 backward_ros
      4 rosidl_default_runtime
      4 rclcpp_action
      4 python3-pytest
      4 geometry_msgs
      3 yasmin
      3 rcpputils
      2 uuid
      2 libmysqlcppconn-dev
      2 libmsgsl-dev
      2 launch_testing_ament_cmake
      2 launch_ros
      2 ament_index_python
      1 visualization_msgs
      1 rosidl_typesupport_introspection_cpp
      1 rosidl_runtime_py
      1 rosgraph_msgs
      1 rosbag2_transport
      1 rosbag2_storage_mcap
      1 rosbag2_py
      1 rmw
      1 rcl_logging_noop
      1 nlohmann_json_schema_validator_vendor
      1 launch
      1 foxglove_bridge
      1 fmt
      1 fastdds
      1 example_interfaces
```

## find_package()

```
     29 volley_cmake
      6 Boost
      5 nlohmann_json
      2 PahoMqttCpp
      2 ament_cmake_auto
      1 opentelemetry
      1 nlohmann_json_schema_validator
      1 launch_testing_ament_cmake
      1 eigen3_cmake_module
      1 Eigen3
      1 cli
      1 ament_cmake_gtest
```

## Entry points

C++ main():
```
src/agvhito_tools/src/agvctl/app.cpp
src/agvhito_tools/src/listener/app.cpp
src/bay/test/bay_guidance_tests.cpp
src/bay/test/garage_door_sim_tests.cpp
src/bay/test/vehicle_estimator_ros_tests.cpp
src/bay/test/vehicle_estimator_tests.cpp
src/central/src/garage_tracker_recovery.cpp
src/central/test/agv_monitor_tests.cpp
src/central/test/charge_agvs_tests.cpp
src/central/test/consistency_monitor_ros_tests.cpp
src/central/test/consistency_monitor_tests.cpp
src/central/test/dispatch_jobs_tests.cpp
src/central/test/dispatch_tests.cpp
src/central/test/execution_garage_state_tests.cpp
src/central/test/execution_state_tests.cpp
src/central/test/garage_monitor_tests.cpp
src/central/test/garage_tracker_mysql_io_tests.cpp
src/central/test/garage_tracker_ros_tests.cpp
src/central/test/garage_tracker_tests.cpp
src/central/test/mqtt_bridge_tests.cpp
src/central/test/schedule_tests.cpp
src/common_ros/src/geometry_visualization_tool.cpp
src/common_ros/test/discrete_garage_state_tests.cpp
src/common_ros/test/layout_tests.cpp
src/common_ros/test/node_tests.cpp
src/common_ros/test/pose_graph_tests.cpp
src/common_ros/test/ros_utils_tests.cpp
src/common/test/geometry_utils_tests.cpp
src/common/test/math_utils_tests.cpp
src/core/rclcppx/test/test_interface_factories.cpp
src/data/otel/examples/metrics_usage_example.cpp
src/infrastructure/dds_discovery/src/discovery_probe.cpp
src/sim/test/bay_sim_tests.cpp
src/vecs/test/vecs_evse_control_tests.cpp
src/vecs/test/vecs_io_control_tests.cpp
src/vecs/test/vecs_tests.cpp
src/vis/src/visualizer_node.cpp
src/vrc/test/drivers/test_mock_hw_driver.cpp
```
Components:
```
src/sim/src/simulator_component.cpp:31:RCLCPP_COMPONENTS_REGISTER_NODE(volley::sim::SimulatorComponent)
src/sim/src/sim_clock_component.cpp:84:RCLCPP_COMPONENTS_REGISTER_NODE(volley::sim::SimClockComponent)
src/sim/src/bay_sim_component.cpp:108:RCLCPP_COMPONENTS_REGISTER_NODE(volley::sim::BaySimComponent)
src/lift/src/vcr_component.cpp:144:RCLCPP_COMPONENTS_REGISTER_NODE(lift::VCRControlComponent)
src/lift/src/lift_component.cpp:48:RCLCPP_COMPONENTS_REGISTER_NODE(lift::LiftComponent)
src/bay/src/vehicle_estimator_component.cpp:44:RCLCPP_COMPONENTS_REGISTER_NODE(bay::VehicleEstimatorComponent)
src/bay/src/blift_state_machine_component.cpp:50:RCLCPP_COMPONENTS_REGISTER_NODE(bay::BliftStateMachineComponent)
src/bay/src/bay_guidance_component.cpp:24:RCLCPP_COMPONENTS_REGISTER_NODE(bay::BayGuidanceComponent)
src/bay/src/bay_state_machine_component.cpp:35:RCLCPP_COMPONENTS_REGISTER_NODE(bay::StateMachineComponent)
src/bay/src/plc_control_component.cpp:64:RCLCPP_COMPONENTS_REGISTER_NODE(bay::PlcControlComponent)
src/bay/src/load_cell_driver_component.cpp:40:RCLCPP_COMPONENTS_REGISTER_NODE(bay::LoadCellDriverComponent)
src/bay/src/io_link_driver_component.cpp:35:RCLCPP_COMPONENTS_REGISTER_NODE(bay::IoLinkDriverComponent)
src/bay/src/vrc_lift_bridge_component.cpp:155:RCLCPP_COMPONENTS_REGISTER_NODE(bay::VrcLiftBridgeComponent)
src/vecs/src/vecs_component.cpp:37:RCLCPP_COMPONENTS_REGISTER_NODE(vecs::VecsComponent)
src/vecs/src/vecs_evse_component.cpp:42:RCLCPP_COMPONENTS_REGISTER_NODE(vecs::evse::VecsEvseComponent)
src/vecs/src/vecs_sim_component.cpp:35:RCLCPP_COMPONENTS_REGISTER_NODE(vecs::sim::VecsSimComponent)
src/vecs/src/vecs_io_component.cpp:42:RCLCPP_COMPONENTS_REGISTER_NODE(vecs::io::VecsIoComponent)
src/agvhito/src/sim/sim_agv_component.cpp:108:RCLCPP_COMPONENTS_REGISTER_NODE(volley::agvhito::sim::SimAgvComponent)
src/central/src/consistency_monitor_component.cpp:24:RCLCPP_COMPONENTS_REGISTER_NODE(central::ConsistencyMonitorComponent)
src/central/src/mqtt_bridge_component.cpp:24:RCLCPP_COMPONENTS_REGISTER_NODE(central::MqttBridgeComponent)
src/central/src/dispatch_component.cpp:64:RCLCPP_COMPONENTS_REGISTER_NODE(central::DispatchComponent)
src/central/src/agv_monitor_component.cpp:37:RCLCPP_COMPONENTS_REGISTER_NODE(central::AgvMonitorComponent)
src/central/src/safety_hardware_monitor_component.cpp:29:RCLCPP_COMPONENTS_REGISTER_NODE(central::SafetyHardwareMonitorComponent)
src/central/src/metrics_recorder_component.cpp:22:RCLCPP_COMPONENTS_REGISTER_NODE(central::MetricsRecorderComponent)
src/central/src/garage_monitor_component.cpp:37:RCLCPP_COMPONENTS_REGISTER_NODE(central::GarageMonitorComponent)
src/central/src/garage_tracker_component.cpp:82:RCLCPP_COMPONENTS_REGISTER_NODE(central::GarageTrackerComponent)
src/agvhito/src/proxy_component.cpp:75:RCLCPP_COMPONENTS_REGISTER_NODE(volley::agvhito::ProxyComponent)
src/planner/scheduler/src/scheduler_component.cpp:71:RCLCPP_COMPONENTS_REGISTER_NODE(volley::SchedulerComponent)
src/vrc/src/ros_node.cpp:277:RCLCPP_COMPONENTS_REGISTER_NODE(volley::vrc::RosNode)
```
Python console_scripts:
```
src/vda5050/map_server/setup.py:25:        "console_scripts": [
src/vda5050/map_server/setup.py-26-            "server = map_server.server:main",
src/vda5050/map_server/setup.py-27-        ]
src/vda5050/map_server/setup.py-28-    },
src/vda5050/map_server/setup.py-29-)
--
src/launcher/setup.py:45:        "console_scripts": [
src/launcher/setup.py-46-            "layout_plotter = launcher.layout_plotter:main",
src/launcher/setup.py-47-        ],
src/launcher/setup.py-48-    },
src/launcher/setup.py-49-)
--
src/central_api/setup.py:25:        "console_scripts": [
src/central_api/setup.py-26-            "rest_api = central_api.rest_api:main",
src/central_api/setup.py-27-        ]
src/central_api/setup.py-28-    },
src/central_api/setup.py-29-)
--
src/scenario/setup.py:34:        "console_scripts": [
src/scenario/setup.py-35-            "exercise_sim_events = scenario.exercise_sim_events:main",
src/scenario/setup.py-36-        ],
src/scenario/setup.py-37-    },
src/scenario/setup.py-38-)
```
Launch files:
```
src/agvhito/launch/proxy.launch.py
src/launcher/launch/bagplay.launch.py
src/launcher/launch/bay.launch.py
src/launcher/launch/central.launch.py
src/launcher/launch/lift.launch.py
src/launcher/launch/sim.launch.py
src/launcher/launch/support/recorder.launch.xml
src/launcher/launch/vecs.launch.py
src/vrc/launch/single.launch.py
```
Lifecycle nodes:
```
```

## Memory management (occurrences in src, C++)

```
std::make_unique            297
std::unique_ptr             161
std::make_shared            847
std::shared_ptr             367
std::weak_ptr                13
shared_from_this              9
\bnew\s+[A-Za-z_]           210
\bdelete\s                    6
std::pmr                      0
Allocator                    10
std::span                     0
std::string_view            146
```

## Concurrency (occurrences in src, C++)

```
MultiThreadedExecutor           1
SingleThreadedExecutor          9
EventsExecutor                  0
StaticSingleThreaded            0
create_callback_group          15
MutuallyExclusive              16
Reentrant                       0
use_intra_process_comms         4
std::thread                     9
std::jthread                   11
std::async                      0
std::mutex                     50
std::shared_mutex               2
std::scoped_lock                0
std::lock_guard                40
std::unique_lock               21
std::atomic                    47
condition_variable             13
create_wall_timer               1
create_timer                   51
```
Files with explicit multithreading:
```
src/agvhito_tools/src/agvctl/agv_ctl.cpp
src/agvhito_tools/src/agvctl/agv_ctl.hpp
src/agvhito_tools/src/agvctl/app.cpp
src/agvhito_tools/src/listener/app.cpp
src/bay/include/bay/guidance_websocket_server.hpp
src/bay/src/guidance_websocket_server.cpp
src/bay/test/bay_guidance_tests.cpp
src/bay/test/guidance_websocket_server_tests.cpp
src/common/include/common/heartbeat_monitor.hpp
src/common_ros/test/ros_utils_tests.cpp
src/common/src/heartbeat_monitor.cpp
src/communication/mqtt/src/client_impl.cpp
src/communication/mqtt/src/client_impl.hpp
src/core/yasminx/include/yasminx/root_state_machine.hpp
src/core/yasminx/src/root_state_machine.cpp
src/sim/test/bay_sim_tests.cpp
src/vrc/include/vrc/manager.hpp
src/vrc/src/manager.cpp
```

## Error handling and tests

```
\bthrow\b                   149
catch\s*\(                   98
std::expected                 0
tl::expected                  2
std::optional               552
RCLCPP_(ERROR|FATAL)         35
assert\(                     39
gtest cases                1215
pytest functions            180
```

## Git hotspots (last 6 months, by package dir)

```
    270 system_tests/tests
    252 scenario/scenarios
    165 agvhito/src
    161 agvhito/include
    149 agv/agv
    133 interfaces/interfaces
    102 scheduler/motion_planner
     91 scheduler/core
     87 central/src
     84 sim/3d
     73 agvhito/test
     69 launcher/layouts
     66 bay/src
     56 sim/src
     53 launcher/params
     52 planner/motion_planner
     50 agvhito/tools
     49 sim_metrics/sim_metrics
     47 common_ros/src
     45 central/include
     44 vis/src
     43 scenario/sets
     43 core/yasminx
     39 scheduler/cost_functions
     39 agvhito_tools/src
```

## Top contributors (last 6 months)

```
   193	Dan Ambrosio
   158	volleypvancamp
    69	Justin Abel
    45	Paul
    11	Jon Lessner
     6	Matthew Zhong
     4	volleybpeterson
     3	Paul Miller
     2	Brandon Peterson
     2	paula van camp
     1	Camille Mahoney
     1	volleyjlessner
```
