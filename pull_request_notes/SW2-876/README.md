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

## Diff the generated action maps

`compare_agvhito_action_maps.py` is standalone: it does not need either generator beside it. It reads the full JSON model and action inventory in two output folders, even when the images in those folders were generated in split mode.

```bash
python3 compare_agvhito_action_maps.py main feat --out-dir diff
```

Default output is a **connected Graphviz graph**, with each state drawn once and transitions connecting those state nodes, matching the connected layout of the original generators. Unchanged actions are gray, removed actions have red strikethrough, and new actions have a green `+`. Failure/cancellation routes remain separate from main control flow. Lifecycle hooks remain separated by table rules.

Install the native Graphviz executable once on Ubuntu:

```bash
sudo apt install graphviz
```

When running inside your uv project, use:

```bash
uv run python pull_request_notes/SW2-876/compare_agvhito_action_maps.py \
  /home/jon-gonzales/Desktop/main \
  /home/jon-gonzales/Desktop/feat \
  --out-dir /home/jon-gonzales/Desktop/diff
```

Graphviz assigns positions automatically; adding/deleting states can move nodes, so the layout is connected but does not lock exact old pixel coordinates. Retained routes influence placement; added/deleted routes are drawn without forcing new ranks. Removed routes are dashed red, added routes are green, and retained routes are muted gray. `--renderer routing` explicitly selects the previous Matplotlib view with repeated destination cards. Retained actions whose helper path changed show the old red path and the new green path; moving a call into a helper does not count as removing and re-adding the action. Factory argument changes and moves between hooks do count as deletion/addition. Duplicate factory occurrences are preserved.

```bash
# Focus on changed states/actions/routes; omit unchanged rows.
python3 compare_agvhito_action_maps.py main feat --out-dir diff-changes --changes-only

# Put every route into one diagram.
python3 compare_agvhito_action_maps.py main feat --out-dir diff-all --no-split

# DOT/JSON/Markdown only: no rendering dependencies required.
python3 compare_agvhito_action_maps.py main feat --out-dir diff-data --no-render
```

Inputs required in each folder:

- `agvhito-action-inventory.json`
- `agvhito-action-model.json`, or `agvhito-state-machine.json`

Older original snapshot-only outputs may lack the model JSON; regenerate them with the source-driven generators first. The older inventory's `lifecycle_hook`/`method` schema is also recognized when a model is available.

Outputs:

- `agvhito-action-diff.png` / `.svg` / `.dot`: connected action and main control-flow differences
- `agvhito-action-diff-errors.png` / `.svg` / `.dot`: connected failure-route differences
- `agvhito-action-diff-cancellation.png` / `.svg` / `.dot`: connected cancellation/terminal differences
- `agvhito-action-diff.json`: full comparison, raw old/new records, source anchors, counts, and provenance
- `agvhito-action-diff.md`: counts and tables of changed actions/transitions

Line-number shifts, whitespace outside argument literals, generation timestamps, and Git metadata do not create action changes. State class/kind/constant/map changes and initial/terminal outcome changes are reported. Ordered alignment shows insertions at their feature position and moved actions as deletion/addition pairs; source order does not establish firmware execution order.

This compares **action factory inventories and declared routes**, not complete C++ behavior. Changed guard conditions, verification logic, batching, wait durations, and callbacks cannot be inferred from these JSON files. Helpers retain their logical identity when moved between files; raw old/new source locations remain in JSON. In particular, changing the settling interval does not show up as a factory addition/deletion.

The comparison uses ordered alignment for each hook. It preserves both input sequences: ignore red deletions to read feature order; ignore green additions to read main order. Diagram labels show the action expression without position annotations; sequence positions remain available in JSON. An action moved within a hook appears red at its old position and green at its new position. Duplicate expressions are retained as separate occurrences; among equally long alignments, identical helper paths are preferred.

The action generator numbers each hook's static action sequence. Helpers expand at their call sites, and factories in arguments appear before factories inside the called helper. Initializer-list expressions retain source order. This is not a runtime trace: branch alternatives are displayed in lexical order, loops are not unrolled, and C++ does not guarantee the lexical evaluation order of sibling ordinary function arguments. It does not infer MQTT publication or firmware execution order.

Replace **all three scripts** together. The comparator can correct insertion/reorder display using existing inventories; regenerate both branch inventories to benefit from the argument-before-helper correction. Generate main outputs with the main checkout selected and feature outputs with the feature checkout selected:

```bash
uv run python pull_request_notes/SW2-876/generate_agvhito_action_map.py --out-dir /home/jon-gonzales/Desktop/main
# After selecting the feature checkout:
uv run python pull_request_notes/SW2-876/generate_agvhito_action_map.py --out-dir /home/jon-gonzales/Desktop/feat
uv run python pull_request_notes/SW2-876/compare_agvhito_action_maps.py /home/jon-gonzales/Desktop/main /home/jon-gonzales/Desktop/feat --out-dir /home/jon-gonzales/Desktop/diff
```

Forty-one regression checks pass; one native Graphviz rendering check is skipped because `dot` is unavailable here. Ordered-projection checks cover insertions, deletions, duplicates and reorders; source fixtures cover initializer lists and helper argument/body ordering. Connected DOT checks verify unique nodes, preserved routes, escaped labels and red-struck/green-added actions. Native rendering still needs execution on a machine with Graphviz installed. The script checks the resulting SVG for every expected transition.

## Bounds and validation

This is a small lexical parser, not a C++ AST. It masks comments and ordinary/raw string literals, tracks balanced braces/parentheses, and resolves straightforward namespace/member helper calls. It expects the registration and transition forms above and out-of-line state method definitions. Preprocessor conditions are not evaluated; macro-generated definitions, function pointers, aliases, custom intermediate state bases, and arbitrary C++ expressions are not supported. Overloaded helpers are followed conservatively rather than resolved by argument type.

Missing inputs, unknown constants/destinations, duplicate outcomes/registrations, unsupported class bases, declared hooks without recognized definitions, and unaccounted factory calls in recognized state files cause a clear error. Recursive helper paths are cut with a warning. Unsupported indirect dispatch can remain outside the inventory; this is not a claim of compiler-level completeness.

Validation performed against the supplied original snapshot and available feature code, not a live remote branch:

- Original snapshot: 9 states, 36 routes, 23 unique factory sites, 11 highlighted paths.
- Available feature recovery/refactor code: 9 states, 37 routes; shared stop-pause and cancellation helpers are attributed to their callers.
- Both Matplotlib diagrams rendered successfully; SVG arrow counts match parsed routes.
- Eighteen parser/split-view/metadata/sequence regression tests passed. Graphviz was not available in the validation environment, so its rendering path was not executed there.

Run the bundled tests without ROS or Matplotlib rendering:

```bash
python3 -m unittest discover -s . -p 'test_*.py' -v
```

## Confirm the comparator copy

The uploaded inventories confirm that `LocalizingState::OnEntry` adds
`MakeStopPauseAction()` through `StopPauseAndSettle` **before**
`MakeEnableMapAction(localization_map_id, kHitoMapVersion)`. The comparator
must display +stopPause before the unchanged map action, without main/feat
position annotations. A regression test covers this insertion through the
connected DOT renderer.

Verify the copy in your repository before rerunning it:

```bash
uv run python pull_request_notes/SW2-876/compare_agvhito_action_maps.py --version
```

Expected: `AGVHITO action comparator: ordered-alignment-v1 (plain labels)`.
If `--version` is unrecognized, that path still contains an older script.
