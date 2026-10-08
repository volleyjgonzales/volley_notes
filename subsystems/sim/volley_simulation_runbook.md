# Volley Simulation Setup and Runbook

[Overview and ROS concepts](volley_simulation_guide.md) · [Simulation package](volley_sim_package.md) · [Visualizer package](volley_vis_package.md) · [Launcher package](volley_launcher_package.md)

## Acronyms, abbreviations, and project names

This reference is local to this document so it remains readable on its own. Formal expansions are distinguished from product/project names whose full forms are not stated in the supplied source. Acronyms inside code, endpoint names, file paths and diagrams retain their exact spelling.

| Term | Full name or meaning | Role in this document |
| --- | --- | --- |
| 2D / 3D | Two-dimensional / three-dimensional. | Planar geometry versus a volume or mesh with height/depth. |
| DAG | Directed acyclic graph. | Dependency graph for scheduled work; `printdags` controls diagnostic output. |
| ROS | Robot Operating System; these guides use ROS 2. | Framework for nodes, messages, services, parameters and execution. |
| AGV | Automated guided vehicle. | Mobile robot that transports parking trays. |
| VRC | Vertical reciprocating conveyor (standard equipment term). | Here, a floor-to-floor carriage/lift with gates. The project source does not explicitly spell out its name; the conventional expansion is documented by [Wildeck](https://www.wildeck.com/vertical-conveyors-vrcs/). |
| CLI | Command-line interface. | Commands/options entered in a terminal. |
| UUID | Universally unique identifier. | Identifier type/notation used by generated interfaces and helper tools. |
| ID | Identifier. | Numeric resource identity or a named configuration identifier. |
| YAML | YAML Ain’t Markup Language (recursive acronym). | Scenario, layout and parameter configuration format. |
| JSON | JavaScript Object Notation. | Docker configuration file format. |
| CSV | Comma-separated values. | Metrics-table serialization format. |
| MCAP | File-format name; the cited specification supplies no letter-by-letter expansion. | Container for timestamped messages, used for ROS bag artifacts. [Format specification](https://mcap.dev/spec). |
| UTC | Coordinated Universal Time. | Timezone used for artifact directory timestamps. |
| URL | Uniform Resource Locator. | Web/resource address including a mesh base URL. |
| AWS | Amazon Web Services. | Cloud service provider for the documented container-image workflow. |
| ECR | Elastic Container Registry. | Amazon’s container-image registry used by the Docker pull workflow. |
| IAM | Identity and Access Management. | AWS account/permission management used by authentication setup. |
| STS | Security Token Service. | AWS service used by `aws sts get-caller-identity`. |
| ACL | Access control list. | Tailscale access policy/tag requirement in the setup guide. |
| SSH | Secure Shell. | Authenticated repository access using SSH keys. |
| APT | Advanced Package Tool. | Ubuntu package management via the `apt` command/proxy. |
| VS Code | Visual Studio Code. | Editor used to open the development container and preview Markdown. |
| RViz | ROS visualization application; a product/tool name rather than a supplied formal acronym. | Displays MarkerArray messages and meshes; does not simulate physical motion. |
| sim / vis / devc | Simulation / visualization / development-container wrapper names. | Package/tool shorthand, not additional engines or protocols. |

Environment variables are configuration names, rather than independent protocols:

| Name | Meaning |
| --- | --- |
| `ROS_DOMAIN_ID` | ROS discovery-domain identifier; same domain allows discovery, different domains separate graphs. |
| `ROS_DISTRO` | ROS distribution name used to select the installed underlay. |
| `ROS_HOME` | ROS runtime-data home directory; fallback is `~/.ros`. |
| `ARTIFACTS_DIR` | Artifact root directory override. |
| `INSTALLATION_ID` | Installation identifier; sim path explicitly uses 9998. |
| `LAYOUT` | Layout-name environment variable for production loading; sim chooses scenario layout. |

Uppercase state labels (`AUTO`, `STOPPED`, `OPEN`, `CLOSED`, and similar), enum constants, macro names and build flags are exact code identifiers, not unexplained acronyms. `RISK` is a review label; `TODO` means “to do.” Units use `m` for metres, `s` for seconds, `ms` for milliseconds, `ns` for nanoseconds, and `kg` for kilograms.

This preserves the supplied setup/simulation guides and adds source-backed visualization checks. The supplied launcher pack now confirms option parsing, topology and namespace settings; no commands were executed against a live ROS (Robot Operating System) system.

## 1. Setup and documented launch walkthrough

### 1.1 Quick start: an already configured and built workspace

Run ROS commands **inside the development container**, from the workspace root. The workspace must already be built and its ROS environment loaded.

#### Terminal 1: launch the simulated garage

```bash
INSTALLATION_ID=1 LAYOUT=5675_pecos_sandbox_eng \
  ros2 launch launcher sim.launch.py \
  scenario:=5675_pecos_sandbox_eng_empty_start_in_auto.yaml \
  enable_dispatch_charging_mode:=false
```

Leave this terminal running. The documented manual configuration starts visualization and RViz by default.

| Setting | Role |
| --- | --- |
| `INSTALLATION_ID=1` | Supplies installation context through an environment variable. |
| `LAYOUT=5675_pecos_sandbox_eng` | Selects the layout through an environment variable. |
| `scenario:=...yaml` | Supplies the scenario and its initial conditions as a ROS launch argument. |
| `enable_dispatch_charging_mode:=false` | Disables automatic dispatch charging behavior for this walkthrough. |

The leading environment assignments apply to this command; they do not permanently export those variables in your shell. The `name:=value` arguments are ROS launch arguments, distinct from shell environment variables.

#### Terminal 2: attach and inject events

On the **host**, open another terminal at the repository root and attach to the container:

```bash
devc attach
```

Then, **inside the container**, run:

```bash
ros2 run scenario exercise_sim_events \
  -l 5675_pecos_sandbox_eng \
  -e 5675_pecos_sandbox_eng_events_fill_from_empty
```

The launch scenario establishes the starting state. The exercise file supplies the subsequent workload. They are separate inputs, and both use the same layout in this example.

To request a metrics file explicitly:

```bash
ros2 run scenario exercise_sim_events \
  -l 5675_pecos_sandbox_eng \
  -e 5675_pecos_sandbox_eng_events_fill_from_empty \
  -o /tmp/sim_results/events_summary.csv
```

#### Terminal 3: inspect the running system

Attach another container terminal and run these commands individually:

```bash
ros2 node list
ros2 topic list
ros2 service list
ros2 topic echo /clock --once
ros2 topic echo /scheduler/report
ros2 topic echo /central/garage_snapshot
```

An advancing `/clock`, active control and simulation nodes, garage-state messages, and event-driven changes in scheduler reports are useful signs of a working simulation. A launch process remaining alive alone does not establish that jobs are completing.

Press `Ctrl+C` in the event-driver terminal and the launch terminal to stop both processes. Stop any topic-echo commands as well. The original onboarding guide also asks developers to share an RViz screenshot in the software Slack channel; that is an optional team onboarding step, separate from running the simulation.

### 1.2 First-time environment setup

#### Host and container responsibilities

| Environment | Responsibilities |
| --- | --- |
| Host | Docker, Tailscale, Git/SSH (Secure Shell) access, AWS (Amazon Web Services) image-pull authentication, `devc`, and the VS Code (Visual Studio Code) application. |
| Development container | ROS 2, compiler and libraries, workspace build, launch commands, event scripts, and ROS inspection. |

The supplied getting-started guide targets an Ubuntu Linux x86 host. Apple Silicon users should complete the repository's `docs/guides/mac-setup.md` first; those instructions were not included in the supplied material.

There is no need to install ROS packages on the host for the documented container workflow. The source checkout is bind-mounted into the container. The guide describes matching host/container user IDs (identifiers) and a persistent container home volume.

#### 2.1 Docker and Tailscale on the host

Install Docker Engine and configure your user to run Docker without `sudo`. Docker Desktop is not required by the supplied guide. Verify:

```bash
docker run hello-world
```

Install Tailscale on the host and join the Volley tailnet:

```bash
sudo tailscale up
tailscale status --peers=false
```

Ask a Volley Tailscale administrator to apply the machine's required ACL (access control list) tag. The development container uses an internal apt proxy reachable through that tailnet. The guide states that `.devcontainer/scripts/initialize.sh` refuses to start when Tailscale is down.

#### 2.2 Repository access and `devc`

Configure an SSH key authorized for the organization's GitHub repositories. Then install `devc`, the container-management wrapper:

```bash
git clone git@github.com:VolleyAutomation/devc.git ~/.devc
~/.devc/install.sh
```

Clone Volley if you do not already have a checkout:

```bash
cd ~
git clone git@github.com:VolleyAutomation/volley.git
cd volley
```

You can use another parent directory. An existing checkout does not need to be cloned again.

#### 2.3 Authenticate container image pulls

On the host, install AWS CLI (command-line interface) and the Amazon ECR (Elastic Container Registry) credential helper. Configure the AWS credentials prescribed by your organization; the supplied guide describes an IAM (Identity and Access Management) access key configured with:

```bash
aws --version
aws configure
aws sts get-caller-identity
sudo apt install amazon-ecr-credential-helper
```

The documented AWS region is `us-west-2`. Merge this entry into the existing top-level object in `~/.docker/config.json`, preserving its other settings:

```json
{
  "credHelpers": {
    "628548651667.dkr.ecr.us-west-2.amazonaws.com": "ecr-login"
  }
}
```

The supplied guide uses this image to check authentication:

```bash
docker pull 628548651667.dkr.ecr.us-west-2.amazonaws.com/ros2:lyrical-core-20260924
```

That tag is a documented example, not a guarantee of the image selected by another repository revision. Use the checkout's container configuration as the authority for its actual image.

#### 2.4 Open the development container

Install VS Code and its Dev Containers extension on the host. From the repository root:

```bash
code .
```

Choose **Reopen in Container**. Run subsequent builds and ROS commands in a terminal attached to that container. For additional terminals, use `devc attach` from the host repository root.

#### 2.5 Load the ROS environment

The repository uses `direnv` to source the ROS underlay and the built workspace overlay automatically when you enter the workspace. Enable the appropriate hook in your container shell configuration:

```bash
# In ~/.bashrc, for Bash:
eval "$(direnv hook bash)"
```

```zsh
# In ~/.zshrc, for Zsh:
eval "$(direnv hook zsh)"
```

Restart the shell or source its configuration, then enter the workspace. If automatic sourcing is unavailable, use the appropriate setup files for your container. For Bash, after a successful build:

```bash
source /opt/ros/"$ROS_DISTRO"/setup.bash
source install/setup.bash
```

This manual fallback assumes `ROS_DISTRO` is set to the installed distribution. Check it before sourcing rather than guessing a distribution name.

#### 2.6 Select a ROS domain

The getting-started guide recommends a unique domain per developer:

```bash
poe domain-id <id>
```

Replace `<id>` with your selected domain. The earlier architecture guide says the supplied simulation loader sets `ROS_DOMAIN_ID=75` **only when it is not already set**. Domain 75 separates the default simulation from other domains, but does not give every developer a unique simulation network.

Ensure all terminals used for this simulation share the same effective domain and ROS discovery configuration. A domain set inside the launch process does not automatically update a separately attached shell. Check terminal configuration when an event script cannot discover the simulation.

#### 2.7 Build the workspace

Inside the container, from the workspace root, use one of:

```bash
colcon build
```

```bash
poe build
```

The guide's resource examples are:

| Host memory | Documented build example |
| --- | --- |
| At least 64 GiB | Default maximum parallelism: `colcon build`. |
| 32 GiB | `colcon build --parallel-workers 3`. |
| 16 GiB | `colcon build --parallel-workers 1`; expect a long build. |

These are repository guidance, not measured guarantees for every machine. The task runner also accepts worker arguments, for example `poe build --parallel-workers 2`.

After building, refresh the workspace environment and verify installation:

```bash
ros2 pkg prefix launcher
ros2 pkg executables scenario
ros2 pkg executables sim
```

Components can be loaded into containers without a separate executable for every class. An absent component name in `ros2 pkg executables sim` does not, by itself, prove the simulation is missing.


## 2. Full-system launch options

| Argument | Documented default | Meaning |
| --- | --- | --- |
| `scenario` | `None` in manual sim entry; named tests may supply one | Scenario file containing initial conditions. Supply it explicitly for this workflow. |
| `real_time_factor` | `1.0` for manual runs; `10.0` for system tests | Ratio of simulated to wall time; `0` pauses simulated time. |
| `enable_dispatch_charging_mode` | `true` | Enable automatic dispatch charging behavior. |
| `garage_dirtiness_threshold_ratio` | YAML (YAML Ain’t Markup Language; configuration format) default retained; earlier guide says `0.1`, unverified | Threshold for queuing an idle AUTO-mode garage-cleaning job. |
| `record_artifacts` | `false` | Enable ROS MCAP (timestamped-message container file format) artifact recording. |
| `artifacts_output_dir` | Timestamped directory under `ARTIFACTS_DIR` | Artifact output location. |
| `artifact_basename` | `sim` | Artifact subdirectory and file base name. |
| `vis` | `true` for manual runs | Enable the 3D visualizer. |
| `rviz` | `true` | Enable RViz. |
| `use_remote_meshes` | `false` in supplied launcher | Explicitly overrides `vis` application default `true`; local assets required. |
| `remote_mesh_prefix` | `https://aws-mesh-proxy.tailfadbb4.ts.net/model/` in supplied `vis` code | Remote mesh base URL (Uniform Resource Locator); launcher only passes a supplied nonempty override. |
| `printdags` | `false` | Print scheduler DAGs (directed acyclic graphs) to standard output. |
| `auto_confirm_insert` | YAML default retained; value unverified | Let simulated patron insert confirmations happen automatically. |

These options are confirmed by `launcher/sim_nodes.py`. Unset auto-confirm and dirtiness threshold preserve YAML values; those files were excluded. Dispatch charging is only forced when its option is false. In particular, `auto_confirm_insert` maps to `simulator.auto_confirm_insert` in the bay component.

The sim parser uses `sys.argv` regexes rather than declared launch arguments. Therefore the following command may not list these options; use the [launcher option table](volley_launcher_package.md#public-simulation-launch-options) for the source-backed catalog:

```bash
ros2 launch launcher sim.launch.py --show-args
```

For a documented headless configuration, add `vis:=false rviz:=false` to the quick-start launch command. To accelerate the simulation, add `real_time_factor:=10.0`. To record it, add `record_artifacts:=true`, with an output directory if desired.


## 3. Exercise driver and metrics

The exercise script and metrics source are not in this pack. The following interfaces and defaults are retained from the earlier documentation.

### 3.1 Exercise-script interface

The correct package/executable form shown by the quick-start guide is:

```bash
ros2 run scenario exercise_sim_events \
  -l <layout> -e <events_yaml> [-o <output_csv_path>]
```

Replace placeholders and omit the square brackets when supplying `-o`. The architecture guide's `ros2 run exercise_sim_events ...` line omits the `scenario` package; this document uses the complete quick-start form.

| Option | Required | Meaning |
| --- | --- | --- |
| `-l`, `--layout` | Yes | Layout name. |
| `-e`, `--events` | Yes | Events YAML name. The supplied quick start uses a name without `.yaml`. |
| `-o`, `--output` | No | CSV (comma-separated values) output path. Pass it explicitly when metrics are needed. |

The script waits for the dispatcher to be running. It monitors `/central/discrete_garage_state` and `/central/report` for bay readiness and job progress.

| Script event | Fields described in the guide | Behavior |
| --- | --- | --- |
| `patron_arrival` | `payload_id`, `mass`, dimensions, `wait_for_job_completion` | Wait for a bay ready to insert; inject arrival and optionally wait for the job. |
| `retrieve_request` | Optional `payload_id`, `wait_for_job_completion` | Retrieve specified payload, or randomly select a stored payload when omitted. |
| `move_agv` | `agv_id`, `pose.node_id`, `pose.heading` | Move/teleport AGV (automated guided vehicle); track scheduler job completion. |
| `move_tray` | `tray_id`, `pose.node_id`, `pose.heading` | Move/teleport tray; track scheduler job completion. |
| `repark_tray` | `tray_id`, pose fields, `allow_reciprocal` | Reposition a parked tray. |
| `sleep` | `duration` | Wait in wall-clock time, not simulated time. |

For patron and retrieve events, `wait_for_job_completion` defaults to `true`. The script polls until the corresponding job reaches a terminal state. The script's event schema and the timed scenario schema should not be assumed interchangeable; use an existing exercise file as the template for new workloads.


### 3.2 CSV metrics

The documented writer is `SimMetricsWriter` in `src/sim_metrics/sim_metrics/csv_metrics_utils.py`. Job-bearing events produce rows; sleep events do not.

| Column | Meaning |
| --- | --- |
| `event_type` | Arrival, retrieval, move, or another recorded job-bearing event. |
| `payload_id` | Payload UUID (universally unique identifier) from the scheduler job, where applicable. |
| `request_time(s)` | Simulated timestamp when the scheduler registered the job. |
| `start_time(s)` | Simulated timestamp when the scheduler produced a plan. |
| `end_time(s)` | Simulated timestamp when the job reached a terminal state. |
| `destination_node_id` | Destination node associated with the job. |
| `result` | Documented values include `SUCCESS`, `ERROR`, `EXECUTING`, and `UNPLANNED`. |

`EXECUTING` and `UNPLANNED` are not proof of terminal completion; inspect the result before interpreting timestamps as a completed-job duration.

The documented `csv_metrics_utils.summarize_csv(path)` utility reports status counts and computes timing statistics from `SUCCESS` rows only:

$$
q=t_{\mathrm{start}}-t_{\mathrm{request}},\qquad
d=t_{\mathrm{end}}-t_{\mathrm{start}}.
$$

It reports minimum, mean, and maximum queue delay and execution duration per event type. Here $q,d\in\mathbb{R}_{\ge0}$ are queue delay and execution duration, and the timestamp scalars are in $\mathbb{R}_{\ge0}$ with units of simulated seconds. These are simulated-time measurements; divide by a constant positive $r$ only when you specifically need an idealized wall-time equivalent.

The architecture guide lists `/tmp/sim_results/events_summary.csv` as a default but also says writing occurs when `-o` is supplied. Because those statements leave the no-`-o` behavior unclear, use an explicit output path when collecting results. Copy wanted results out of temporary locations before cleaning or rebuilding environments.


## 4. Running-system troubleshooting

| Symptom | First checks |
| --- | --- |
| Container initialization fails with Tailscale error | Check host Tailscale connection and required ACL tag; reopen the container after resolving it. |
| Image pull is unauthorized | Check `aws sts get-caller-identity`, the ECR helper installation, and the registry entry in Docker configuration. |
| `ros2` is unavailable | Confirm the terminal is in the development container and the underlay is sourced. |
| `launcher` or `scenario` is not found | Confirm build success and workspace overlay sourcing; inspect `ros2 pkg prefix launcher`. |
| Scenario or layout cannot be found | Check the exact names against the checkout, installation, and launch arguments. |
| Event script waits indefinitely | Check dispatcher state, matching ROS domains, service discovery, and whether a bay is ready to insert. |
| ROS time does not advance | Check `/clock`, the clock component, and `real_time_factor`; `0` intentionally pauses the simulation. |
| Inserts remain unfinished | Check `auto_confirm_insert`; when disabled, an external confirmation is required. |
| RViz fails while other nodes run | Check container display setup and mesh access; use `vis:=false rviz:=false` to investigate without visualization. |
| Build exhausts memory | Reduce `--parallel-workers` using the documented memory guidance. |
| No metrics file appears | Pass `-o` explicitly and check the output directory and script errors. |

To inspect the event service without inventing its schema:

```bash
ros2 service list -t
ros2 service type /sim/enqueue_garage_event
```

Use `ros2 interface show <returned_type>` for its actual message definition. Exact node names, service request fields, installed executable names, and launch defaults should be verified from the running checkout rather than inferred from class names.



## 5. Visualizer troubleshooting

| Symptom | Check |
| --- | --- |
| RViz displays no objects | Confirm `/vis/trays` and other expected MarkerArray topics exist; compare actual namespace with configured RViz topics. |
| Frame-related RViz error | Factory marker frame and supplied RViz Fixed Frame should both be `map`. A different fixed frame needs an appropriate transform. |
| Meshes fail to load | Check `use_remote_meshes` and prefix; local mode needs installed `sim/3d` assets, remote mode needs resource access from RViz's environment. |
| Objects look frozen | Check `/clock` progression, `use_sim_time`, snapshot delivery and whether source state changes. |
| Removed AGV still appears | Source AGV cache is not reconciled on absence; a continually republished mesh is not proof of current garage membership. |
| Doors look out of sync | Visual overdrive and VRC (vertical reciprocating conveyor; the floor-to-floor lift) gate animations use hardcoded 4 s / 3 s durations; changing hardware parameters does not reconfigure them. |
| Displayed cars have unexpected size/color | Car mesh/color are process-salted choices; displayed mesh dimensions are not resized to each physical payload in this code. |

```bash
ros2 topic list -t
ros2 topic info /vis/trays --verbose
ros2 topic echo /vis/trays --once
ros2 topic echo /central/garage_snapshot --once
```

Inspect `header.frame_id`, marker pose, `mesh_resource`, namespace and ID in the marker data. Marker outputs are topics; `/central/add_tray` is a service, so inspect it with `ros2 service type`, not `ros2 topic echo`.

## Source and rendering notes

Setup commands derive from the supplied repository getting-started/simulation guides. Package-source analysis is in the three companion package guides; metrics/event-script source is still omitted. Markdown uses `$...$`, `$$...$$`, and Mermaid fenced blocks. Save these files together to preserve their relative navigation links.

### Launcher-specific setup checks

- Sim layout comes from scenario YAML; this launch path sets installation ID `9998` regardless of shell `LAYOUT`/`INSTALLATION_ID`. Preserve the documented command for other tooling, but do not infer its environment values control these sim parameters.
- The source starts RViz without an explicit display config. Select the installed vis configuration and Fixed Frame `map` if needed.
- `vis:=false` gates visualizer, bridge, and RViz. `rviz:=false` keeps visualizer/bridge available when vis is enabled.
- The clock is configured first in the main container, with no startup-readiness barrier. Check `/clock` and component/service discovery if startup stalls.
- Artifact output defaults to a UTC (Coordinated Universal Time) timestamp under `ARTIFACTS_DIR`, otherwise `${ROS_HOME:-~/.ros}/artifacts`. Recorder source subdirectories are flattened during installation, so its installed include is `launch/recorder.launch.xml`.
- Bagplay loops playback but does not request `--clock` or pass layout/use_sim_time to vis; see the [launcher guide](volley_launcher_package.md) before treating it as a complete simulation replay.
