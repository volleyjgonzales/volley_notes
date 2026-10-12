#!/usr/bin/env python3
"""Parse state hooks and local helpers to render the AGVHITO action map.

Keep generate_agvhito_state_machine.py beside this script. Both use the live
checkout by default. Static call paths are shown, including helper calls;
conditions, execution frequency, and firmware order are not inferred.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from generate_agvhito_state_machine import (
    HIGHLIGHTS, HOOKS, arguments, calls, parse_package, render_views, serializable,
    subtitle_lines,
)


def audit(model: dict) -> tuple[list[dict], dict]:
    definitions = model['functions']
    records, sections = [], {}
    by_class = {s['cpp_class']: s for s in model['states']}

    def resolve(name, owner):
        # Member lookup precedes free-function lookup. Qualified names must match
        # a namespace suffix; do not accidentally follow unrelated same-name calls.
        candidates = []
        if '::' not in name and '::' in owner['name']:
            cls = owner['name'].rsplit('::', 1)[0]
            candidates = [f for f in definitions if f['name'] == cls + '::' + name]
        if not candidates:
            candidates = [f for f in definitions if f['key'] == name or f['key'].endswith('::' + name)]
            if '::' not in name:
                namespace = owner['namespace']
                while True:
                    scoped = [f for f in candidates if f['namespace'] == namespace and '::' not in f['name']]
                    if scoped or not namespace:
                        candidates = scoped
                        break
                    namespace = namespace.rpartition('::')[0]
        # Distinct overloads are conservatively traversed; argument types are not inferred.
        return candidates

    def walk(fn, state, hook, chain, stack):
        if fn['id'] in stack:
            warning = f'Recursive helper path cut: {" -> ".join(chain)}'
            if warning not in model['warnings']:
                model['warnings'].append(warning)
            return
        stack = stack | {fn['id']}
        for name, args, offset in calls(fn['body']):
            line = fn['body_line'] + fn['body'].count('\n', 0, offset)
            short = name.split('::')[-1]
            if re.fullmatch(r'Make\w*Action', short):
                args = re.sub(r'\s+', ' ', args).strip()
                record = {'state': state['name'], 'cpp_class': state['cpp_class'],
                          'hook': hook, 'factory': short, 'arguments': args,
                          'expression': short + '(' + args + ')',
                          'highlight': short in HIGHLIGHTS,
                          'source': fn['source'], 'line': line,
                          'call_path': chain,
                          'via': ' -> '.join(chain) + f' [{fn["source"]}:{line}]'}
                records.append(record)
                sections[state['name']][hook].append(record)
                continue
            for helper in resolve(name, fn):
                walk(helper, state, hook,
                     chain + [helper['name'] + f'@{fn["source"]}:{line}'], stack)

    for state in model['states']:
        hooks = HOOKS if state['kind'] == 'lifecycle' else ('Execute',)
        sections[state['name']] = {hook: [] for hook in hooks}
        for hook in hooks:
            roots = [f for f in definitions if f['name'] == state['cpp_class'] + '::' + hook]
            if len(roots) > 1:
                raise ValueError(f'Multiple definitions of {state["cpp_class"]}::{hook}')
            if roots:
                walk(roots[0], state, hook, [roots[0]['name']], set())
            else:
                # Inherited lifecycle hooks are allowed, but a declared method
                # without a recognized definition must not silently disappear.
                header = model['files'][state['header']]
                from generate_agvhito_state_machine import mask_cpp
                if re.search(r'\b' + hook + r'\s*\(', mask_cpp(header)):
                    raise ValueError(f'Declared hook was not parsed: {state["cpp_class"]}::{hook}')
                if state['kind'] == 'state':
                    raise ValueError(f'Execute definition missing for {state["cpp_class"]}')

    accounted = {(r['source'], r['line'], r['factory']) for r in records}
    unmatched = []
    state_files = {s['header'] for s in model['states']}
    state_files.update(fn['source'] for fn in definitions
                       if fn['name'].split('::')[0] in by_class)
    for source in sorted(state_files):
        text = model['files'][source]
        for name, args, offset in calls(text):
            short = name.split('::')[-1]
            line = text.count('\n', 0, offset) + 1
            if re.fullmatch(r'Make\w*Action', short) and (source, line, short) not in accounted:
                unmatched.append(f'{name} [{source}:{line}]')
    if unmatched:
        raise ValueError('State factory calls not reachable from parsed hooks: ' + ', '.join(unmatched))
    return records, sections


def generate(package_root: Path, output_dir: Path, dpi=130, renderer='auto', split=True):
    model = parse_package(package_root)
    records, sections = audit(model)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'agvhito-action-inventory.json').write_text(json.dumps(records, indent=2) + '\n')
    (output_dir / 'agvhito-action-model.json').write_text(json.dumps(serializable(model), indent=2) + '\n')
    # Also list every lifecycle section, including hooks with no action factories.
    (output_dir / 'agvhito-hook-inventory.json').write_text(json.dumps(sections, indent=2) + '\n')
    used, views = render_views(model, output_dir, 'agvhito-state-machine-actions',
                              dpi, renderer, sections, split)
    rows = ['# AGVHITO state-machine action map', '',
            f'Parsed {len(model["states"])} states and {len(model["edges"])} routes from the checkout.', '',
            *subtitle_lines(model), '',
            *([f'![{kind} diagram]({view["stem"]}.png)' for kind, view in views.items()] if used != 'none' else []), '',
            'Amber highlights `MakeStartPauseAction`, `MakeStopPauseAction`, and `MakeSoftEStopAction`.',
            'Calls through local helpers are attributed to the originating hook. Empty sections include inherited hooks.', '',
            '| State | C++ class | Hook | Factory expression | Call path / source |',
            '| --- | --- | --- | --- | --- |']
    for state in model['states']:
        for hook, owned in sections[state['name']].items():
            if not owned:
                rows.append(f'| `{state["name"]}` | `{state["cpp_class"]}` | `{hook}` | — | — |')
            for r in owned:
                expr = r['expression'].replace('|', '&#124;').replace('`', '&#96;')
                via = r['via'].replace('|', '&#124;').replace('`', '&#96;')
                if r['highlight']:
                    expr = '**`' + expr + '`**'
                else:
                    expr = '`' + expr + '`'
                rows.append(f'| `{state["name"]}` | `{state["cpp_class"]}` | `{hook}` | {expr} | `{via}` |')
    rows += ['', '## Interpretation', '',
             '- This is a bounded lexical source scan, not a compiler or runtime trace.',
             '- Conditions and early returns are not evaluated. Calls are possible static paths, not promises that each action executes.',
             '- A factory inside a shared helper appears under each hook that can call that helper; this is distinct from the number of unique factory sites.',
             '- Overloads are followed conservatively because argument types are not resolved.',
             '- Only helpers defined under `src/sm` and `include/agvhito/sm` are traced. Actions assembled elsewhere or emitted by callbacks are outside this inventory.',
             '- `VerifiedPublish(new_order)` publishes an assembled order, whose embedded actions are outside this factory inventory.',
             '- `Continue` is an internal lifecycle step result, not a graph self-transition.',
             '- Split views separate failure and cancellation routes by default; `--no-split` combines them.',
             '- JSON inventories retain the full graph in either mode. Auxiliary diagrams omit action details to keep routing legible.',
             f'- Renderer: `{used}`. DOT source is also included; use Graphviz for a connected graph layout.', '']
    if model['warnings']:
        rows += ['## Parser warnings', ''] + ['- ' + w for w in model['warnings']] + ['']
    (output_dir / 'agvhito-action-map.md').write_text('\n'.join(rows), encoding='utf-8')
    unique = {(r['source'], r['line'], r['factory']) for r in records}
    print(f'{len(unique)} unique factory sites; {len(records)} hook paths; '
          f'{sum(r["highlight"] for r in records)} highlighted paths; '
          f'{len(model["edges"])} routes; renderer={used}; output={output_dir.resolve()}')
    return model, records, sections


def main():
    parser, args = arguments(__doc__)
    try:
        generate(args.package_root, args.out_dir, args.dpi, args.renderer, args.split)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
