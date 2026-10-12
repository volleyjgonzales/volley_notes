# Source-driven AGVHITO diagram generators

Keep `generate_agvhito_state_machine.py` and `generate_agvhito_action_map.py` in the same directory. The action generator imports the shared parser and renderer from the state-machine generator. Filenames have no numeric upload suffix.

## Install and run

Requires Python 3.10+ and Matplotlib. Graphviz is optional, but recommended for the connected state-machine layout.

```bash
sudo apt install python3-matplotlib graphviz
```

Both scripts default to `/home/jon-gonzales/volley/src/agvhito`. They read `src/sm/**/*.cpp` and `include/agvhito/sm/**/*.hpp` directly. No Repomix input is required, and neither script modifies the checkout.

```bash
python3 generate_agvhito_state_machine.py --out-dir diagrams/current
python3 generate_agvhito_action_map.py --out-dir diagrams/current
```

Diagrams are split by default (`--split`): the existing PNG/SVG names contain main control flow, while `-errors` and `-cancellation` companion files contain the other routes. Failure/cancellation images omit action details; the main action diagram retains all hooks and their actions. Full topology and action JSON inventories remain unchanged.

```bash
# Default: separate main, failure, and cancellation diagrams.
python3 generate_agvhito_action_map.py --out-dir diagrams/current

# Optional: all transitions in one image again.
python3 generate_agvhito_action_map.py --no-split --out-dir diagrams/combined
python3 generate_agvhito_state_machine.py --no-split --out-dir diagrams/combined
```

Framework `canceled` routes are separated from ordinary `canceled-order` routes, which remain in main control flow. Routes into ErrorState and `errored` routes go to the failure diagram, including errored-to-terminal. Other terminal routes go to the cancellation/terminal diagram. Empty auxiliary route groups are omitted. Each generated `*-views.json` records the partition and filenames.

The default renderer is `auto`: Graphviz when `dot` is installed, otherwise Matplotlib. Use `--renderer graphviz` to require a connected graph or `--renderer matplotlib` for the source-grouped routing view. The routing view repeats destination cards deliberately so every outcome has an independent, readable arrow. It preserves the full graph's routes, rather than using the old hard-routed node arrangement.

Matplotlib uses native vector paths for SVG text, with no `foreignObject`. Graphviz writes native SVG labels. Blue denotes ordinary State, teal denotes LifecycleState, rose denotes root terminal outcomes, and amber highlights the three pause/software E-stop factories. Lifecycle cards include OnEntry, Step, and OnExit even when a hook contains no factory calls. The Matplotlib renderer separates hooks with dashed lines; Graphviz uses table separators.

## Diagram provenance

Every main/failure/cancellation diagram has a subtitle showing:

- Git branch (or `detached HEAD` / `unavailable`)
- Short commit hash (12 characters, or `unavailable`)
- Generation date and time, including the local UTC offset and timezone
- Whether files under the two SM source directories have uncommitted changes (`SM modified` / `SM clean`)
- State/route count for the displayed view
- Short SHA-256 fingerprint of the parsed source, including uncommitted content

The complete Git commit hash, commit date, generation timestamp, source root, and source-change flag are saved under `metadata` in `agvhito-state-machine.json` and `agvhito-action-model.json`. Exported source without a Git repository still renders; it is labeled honestly instead of guessing the branch. Changes elsewhere in the checkout do not mark SM sources modified.

## Compare main and your feature branch

You can run the scripts before and after switching branches, using separate output directories. Alternatively, use separate worktrees to avoid switching your current checkout:

```bash
# From the Volley repository root, use your existing local main reference.
git worktree add --detach /tmp/volley-main-diagrams main

# Use absolute paths to wherever you saved these two scripts.
python3 /path/to/generate_agvhito_state_machine.py \
  --package-root /tmp/volley-main-diagrams/src/agvhito \
  --out-dir /tmp/agvhito-diagrams/main
python3 /path/to/generate_agvhito_action_map.py \
  --package-root /tmp/volley-main-diagrams/src/agvhito \
  --out-dir /tmp/agvhito-diagrams/main

# Your feature branch remains checked out in the default local Volley path.
python3 /path/to/generate_agvhito_state_machine.py \
  --out-dir /tmp/agvhito-diagrams/feature
python3 /path/to/generate_agvhito_action_map.py \
  --out-dir /tmp/agvhito-diagrams/feature

diff -u /tmp/agvhito-diagrams/main/agvhito-state-machine.json \
        /tmp/agvhito-diagrams/feature/agvhito-state-machine.json
diff -u /tmp/agvhito-diagrams/main/agvhito-action-inventory.json \
        /tmp/agvhito-diagrams/feature/agvhito-action-inventory.json
```

The JSON inventory uses package-relative source paths. Line numbers and the source fingerprint naturally change when code moves or changes. Generation timestamps and branch/commit metadata also differ between runs. For a routing-only comparison, compare `edges` from the state-machine JSON; source fingerprint changes alone do not imply a topology change.

Use `--renderer none` to generate DOT/JSON/Markdown without image rendering. Use `--dpi 160` to change PNG resolution.

## What is parsed

| Information | Source |
| --- | --- |
| State names and outcome strings | String-valued constexpr constants in SM files/headers |
| Registered states and associated C++ classes | `add_state(name, std::make_shared<Class>(...), transition_map)` in `root.cpp` |
| Ordinary vs lifecycle state | Class inheritance in the state header |
| Outcome routes | Brace-initialized `yasmin::Transitions` maps in `state_strings.hpp` |
| Terminal outcomes | The root's `yasmin::Outcomes {...}` declaration |
| Initial state | Explicit `set_initial_state(...)`, otherwise first registration |
| Hook actions | `Make*Action(...)` calls reachable from Execute or lifecycle hooks |
| Indirect hook actions | Calls through SM member/free helpers and detail-header helpers |
| Source anchors | Package-relative filename and line number |

There are no fixed nine-state, 36-route, or 23-action assertions. Added registrations, outcomes, and factory calls appear automatically when they retain these supported C++ forms.

## Action inventory interpretation

The inventory shows action **factory** calls, not all function calls. It follows local helpers such as `VerifiedUnpause`, `StopPauseAndSettle`, and `VerifyCancelOrder` without baking in their names. For example, a single `MakeStopPauseAction()` factory site in `StopPauseAndSettle()` is attributed separately to each originating hook that calls it. Every record contains the originating class/hook, expression, helper call path, highlight flag, and exact leaf source location.

Unique factory sites and hook paths have different counts. Factories inside conditional branches or loops are static possible sites; the parser does not determine whether or how often they execute. The image does not reuse the old hand-written guard/batch descriptions, which could become wrong after a branch change.

Order payloads already assembled elsewhere can contain actions without a factory call in the state hook. Those embedded actions, external publishers in `Agv`, functions outside the two SM directories, callback targets, and virtual dispatch are outside this scan.

## Outputs

- `agvhito-state-machine.png`, `.svg`, `.dot`, `.json`
- `agvhito-state-machine-errors.png`, `.svg`, `.dot`
- `agvhito-state-machine-cancellation.png`, `.svg`, `.dot`
- `agvhito-state-machine-actions.png`, `.svg`, `.dot`
- `agvhito-state-machine-actions-errors.png`, `.svg`, `.dot`
- `agvhito-state-machine-actions-cancellation.png`, `.svg`, `.dot`
- `agvhito-state-machine-views.json` and `agvhito-state-machine-actions-views.json`: view manifests
- `agvhito-action-inventory.json`: attributed factory call paths
- `agvhito-hook-inventory.json`: every hook, including empty sections
- `agvhito-action-model.json`: topology and parser warnings for the action diagram
- `agvhito-action-map.md`: inventory table and interpretation notes

PNG/SVG are omitted with `--renderer none`.

## Bounds and validation

This is a small lexical parser, not a C++ AST. It masks comments and ordinary/raw string literals, tracks balanced braces/parentheses, and resolves straightforward namespace/member helper calls. It expects the registration and transition forms above and out-of-line state method definitions. Preprocessor conditions are not evaluated; macro-generated definitions, function pointers, aliases, custom intermediate state bases, and arbitrary C++ expressions are not supported. Overloaded helpers are followed conservatively rather than resolved by argument type.

Missing inputs, unknown constants/destinations, duplicate outcomes/registrations, unsupported class bases, declared hooks without recognized definitions, and unaccounted factory calls in recognized state files cause a clear error. Recursive helper paths are cut with a warning. Unsupported indirect dispatch can remain outside the inventory; this is not a claim of compiler-level completeness.

Validation performed against the supplied original snapshot and available feature code, not a live remote branch:

- Original snapshot: 9 states, 36 routes, 23 unique factory sites, 11 highlighted paths.
- Available feature recovery/refactor code: 9 states, 37 routes; shared stop-pause and cancellation helpers are attributed to their callers.
- Both Matplotlib diagrams rendered successfully; SVG arrow counts match parsed routes.
- Sixteen parser/split-view/metadata regression tests passed. Graphviz was not available in the validation environment, so its rendering path was not executed there.

Run the bundled tests without ROS or Matplotlib rendering:

```bash
python3 -m unittest discover -s . -p test_generators.py -v
```
