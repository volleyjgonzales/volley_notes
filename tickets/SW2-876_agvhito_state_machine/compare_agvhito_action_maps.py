#!/usr/bin/env python3
"""Compare two generator output folders: main -> feature.

Python 3.10+; connected rendering requires Graphviz's dot executable. Reads JSON, not PNG pixels or
checkout code. Ignores source-line shifts, preserves duplicate factory counts,
and distinguishes retained actions with changed helper paths from +/- actions.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
import html
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import xml.etree.ElementTree as ET

BG, INK, MUTED = '#F8FAFC', '#0F172A', '#64748B'
RED, GREEN, AMBER = '#BE123C', '#15803D', '#92400E'
COLORS = {'removed': RED, 'added': GREEN, 'unchanged': MUTED, 'modified': AMBER}
MARKS = {'removed': '− ', 'added': '+ ', 'unchanged': '  ', 'modified': '↔ '}
HOOK_ORDER = ('Execute', 'OnEntry', 'Step', 'OnExit')


def cpp_tokens(text: str) -> tuple[str, ...]:
    pattern = (r'R"(?P<delim>[^ ()\\\t\r\n]{0,16})\(.*?\)(?P=delim)"'
               r'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
               r'|\w+|::|->|==|!=|<=|>=|&&|\|\||\+\+|--|<<|>>|\.\.\.|\S')
    return tuple(m[0] for m in re.finditer(pattern, text, re.S))


def normalize_record(record: dict) -> dict:
    r = dict(record)
    state = r.get('state')
    cls = r.get('cpp_class', '')
    hook = r.get('hook') or r.get('lifecycle_hook', '').split(' -> ')[0] or r.get('method')
    if not state or not hook or not r.get('factory'):
        raise ValueError('Action record lacks state, hook, or factory')
    args = r.get('arguments', '')
    path = r.get('call_path')
    if path is None:
        # Compatibility with the original supplied action inventory schema.
        path = [cls + '::' + hook]
        if r.get('method') and r['method'] != hook:
            path.append(cls + '::' + r['method'])
    r.update(hook=hook, arguments=args,
             expression=r.get('expression') or f'{r["factory"]}({args})',
             normalized_path=[p.split('@', 1)[0] for p in path])
    return r


def load_folder(folder: Path) -> dict:
    model_path = next((folder / name for name in
                       ('agvhito-action-model.json', 'agvhito-state-machine.json')
                       if (folder / name).is_file()), None)
    inventory_path = folder / 'agvhito-action-inventory.json'
    if model_path is None or not inventory_path.is_file():
        raise ValueError(f'{folder}: need agvhito-action-inventory.json and '
                         'agvhito-action-model.json (or agvhito-state-machine.json). '
                         'Regenerate with the source-driven scripts if these are missing.')
    model = json.loads(model_path.read_text(encoding='utf-8'))
    raw_records = json.loads(inventory_path.read_text(encoding='utf-8'))
    if not isinstance(model, dict) or not isinstance(raw_records, list):
        raise ValueError(f'{folder}: unexpected JSON schema')
    names = [s['name'] for s in model['states']]
    if len(names) != len(set(names)):
        raise ValueError(f'{folder}: duplicate states')
    records = [normalize_record(r) for r in raw_records]
    for record in records:
        if record['state'] not in names:
            raise ValueError(f'{folder}: action refers to unregistered state {record["state"]}')
    for edge in model['edges']:
        if edge['source'] not in names or edge['destination'] not in set(names) | set(model['terminal_outcomes']):
            raise ValueError(f'{folder}: invalid transition endpoint')
    return {'folder': str(folder.resolve()), 'model': model, 'records': records}


def action_key(record):
    return record['factory'], cpp_tokens(record['arguments'])


def compare_actions(old: list[dict], new: list[dict]) -> list[dict]:
    """Align in order; maximize retained expressions, then identical helper paths.

    Projecting old/new records from the rows reconstructs each input exactly.
    A moved action is removed at its old position and added at its new position.
    """
    m, n = len(old), len(new)
    scores = [[(0, 0) for _ in range(n + 1)] for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            best = max(scores[i + 1][j], scores[i][j + 1])
            if action_key(old[i]) == action_key(new[j]):
                tail = scores[i + 1][j + 1]
                match = (tail[0] + 1, tail[1] +
                         int(old[i]['normalized_path'] == new[j]['normalized_path']))
                best = max(best, match)
            scores[i][j] = best
    rows = []
    i = j = 0
    def append(status, oi=None, nj=None):
        rows.append({'status': status,
                     'old': old[oi] if oi is not None else None,
                     'new': new[nj] if nj is not None else None,
                     'old_sequence': oi + 1 if oi is not None else None,
                     'new_sequence': nj + 1 if nj is not None else None})
    while i < m or j < n:
        if i < m and j < n and action_key(old[i]) == action_key(new[j]):
            tail = scores[i + 1][j + 1]
            same_path = old[i]['normalized_path'] == new[j]['normalized_path']
            if (tail[0] + 1, tail[1] + int(same_path)) == scores[i][j]:
                append('unchanged' if same_path else 'modified', i, j)
                i += 1
                j += 1
                continue
        if i < m and (j == n or scores[i + 1][j] == scores[i][j]):
            append('removed', oi=i)
            i += 1
        else:
            append('added', nj=j)
            j += 1
    assert [r['old'] for r in rows if r['old'] is not None] == old
    assert [r['new'] for r in rows if r['new'] is not None] == new
    return rows


def route_key(edge):
    return edge['source'], edge['outcome'], edge['destination']


def build_diff(main: dict, feat: dict) -> dict:
    old_model, new_model = main['model'], feat['model']
    old_states = {s['name']: s for s in old_model['states']}
    new_states = {s['name']: s for s in new_model['states']}
    ordered = list(old_states) + [s for s in new_states if s not in old_states]
    states = []
    for name in ordered:
        old, new = old_states.get(name), new_states.get(name)
        status = 'added' if old is None else 'removed' if new is None else 'unchanged'
        fields = ['cpp_class', 'kind', 'constant', 'transition_map']
        changed = [f for f in fields if old and new and old.get(f) != new.get(f)]
        if changed:
            status = 'modified'
        hooks = list(dict.fromkeys(h for s in (old, new) if s for h in
                                  (('OnEntry', 'Step', 'OnExit') if s['kind'] == 'lifecycle' else ('Execute',))))
        hooks += [r['hook'] for r in main['records'] + feat['records']
                  if r['state'] == name and r['hook'] not in hooks]
        hooks = sorted(set(hooks), key=lambda h: (HOOK_ORDER.index(h) if h in HOOK_ORDER else 99, h))
        sections = {}
        order_changes = []
        for hook in hooks:
            before = [r for r in main['records'] if r['state'] == name and r['hook'] == hook]
            after = [r for r in feat['records'] if r['state'] == name and r['hook'] == hook]
            sections[hook] = compare_actions(before, after)
            old_keys, new_keys = list(map(action_key, before)), list(map(action_key, after))
            if Counter(old_keys) == Counter(new_keys) and old_keys != new_keys:
                order_changes.append(hook)
        states.append({'name': name, 'status': status, 'old': old, 'new': new,
                       'changed_fields': changed, 'sections': sections,
                       'factory_order_changed': order_changes})
    old_routes = {route_key(e): e for e in old_model['edges']}
    new_routes = {route_key(e): e for e in new_model['edges']}
    if len(old_routes) != len(old_model['edges']) or len(new_routes) != len(new_model['edges']):
        raise ValueError('Duplicate source/outcome/destination routes are unsupported')
    routes = [{'status': 'unchanged' if key in new_routes else 'removed',
               'old': edge, 'new': new_routes.get(key)} for key, edge in old_routes.items()]
    routes += [{'status': 'added', 'old': None, 'new': edge}
               for key, edge in new_routes.items() if key not in old_routes]
    action_rows = [r for s in states for rows in s['sections'].values() for r in rows]
    return {'generated_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'main': {'folder': main['folder'], 'metadata': old_model.get('metadata', {}),
                     'source_sha256': old_model.get('source_sha256'), 'initial_state': old_model.get('initial_state'),
                     'terminal_outcomes': old_model['terminal_outcomes']},
            'feat': {'folder': feat['folder'], 'metadata': new_model.get('metadata', {}),
                     'source_sha256': new_model.get('source_sha256'), 'initial_state': new_model.get('initial_state'),
                     'terminal_outcomes': new_model['terminal_outcomes']},
            'states': states, 'routes': routes,
            'summary': {'states': dict(Counter(s['status'] for s in states)),
                        'actions': dict(Counter(r['status'] for r in action_rows)),
                        'routes': dict(Counter(r['status'] for r in routes))}}


def split_routes(diff: dict, split: bool) -> dict[str, list]:
    if not split:
        return {'main': diff['routes']}
    errors = {s['name'] for s in diff['states'] if any(
        version and version.get('cpp_class') == 'ErrorState' for version in (s['old'], s['new']))}
    terminals = set(diff['main']['terminal_outcomes']) | set(diff['feat']['terminal_outcomes'])
    groups = {'main': [], 'errors': [], 'cancellation': []}
    for row in diff['routes']:
        edge = row['new'] or row['old']
        kind = ('cancellation' if edge['outcome'] == 'canceled' else
                'errors' if edge['destination'] in errors or edge['outcome'] == 'errored' else
                'cancellation' if edge['destination'] in terminals else 'main')
        groups[kind].append(row)
    return groups


def state_lines(state: dict, show_actions: bool, changes_only: bool):
    lines = []
    old, new = state['old'], state['new']
    current = new or old
    if state['status'] == 'modified':
        if any(f in state['changed_fields'] for f in ('cpp_class', 'kind')):
            for version, status in [(old, 'removed'), (new, 'added')]:
                lines.append((status, f'{version["cpp_class"]} · {version["kind"]}', 'class'))
        else:
            lines.append(('unchanged', f'{current["cpp_class"]} · {current["kind"]}', 'class'))
        for field in state['changed_fields']:
            if field not in {'cpp_class', 'kind'}:
                lines += [('removed', f'{field}: {old.get(field)}', 'note'),
                          ('added', f'{field}: {new.get(field)}', 'note')]
    else:
        lines.append((state['status'], f'{current["cpp_class"]} · {current["kind"]}', 'class'))
    if not show_actions:
        return lines
    for hook, rows in state['sections'].items():
        lines.append(('unchanged', hook, 'hook'))
        for row in rows:
            status = row['status']
            if changes_only and status == 'unchanged':
                continue
            record = row['new'] or row['old']
            # A retained action stays neutral; its changed helper path is shown separately.
            lines.append(('unchanged' if status == 'modified' else status, record['expression'], 'action'))
            if status == 'modified':
                lines.append(('removed', 'via ' + ' → '.join(row['old']['normalized_path']), 'note'))
                lines.append(('added', 'via ' + ' → '.join(row['new']['normalized_path']), 'note'))
            elif len(record['normalized_path']) > 1:
                lines.append((status, 'via ' + ' → '.join(record['normalized_path']), 'note'))
        if hook in state['factory_order_changed']:
            lines.append(('modified', 'Factory source order changed; see JSON for both sequences.', 'note'))
    return lines


def provenance(label, version):
    m = version['metadata']
    dirty = ' · SM modified' if m.get('sm_dirty') else ''
    stamp = ' · source generated ' + m['generated_at'] if m.get('generated_at') else ''
    fingerprint = ' · SHA ' + version['source_sha256'][:12] if version.get('source_sha256') else ''
    return f'{label}: {m.get("branch") or "branch unavailable"} @ {m.get("commit_short") or "commit unavailable"}{dirty}{stamp}{fingerprint}'


def render_routing(diff: dict, routes: list, output: Path, stem: str, kind: str, dpi: int,
           changes_only: bool, main_label: str, feat_label: str):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Polygon
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'path'})
    if changes_only:
        routes = [r for r in routes if r['status'] != 'unchanged']
    blocks = []
    for state in diff['states']:
        owned = [r for r in routes if (r['new'] or r['old'])['source'] == state['name']]
        changed_actions = any(r['status'] != 'unchanged' for rows in state['sections'].values() for r in rows)
        changed_state = state['status'] != 'unchanged' or bool(state['factory_order_changed'])
        if kind != 'main' and not owned:
            continue
        if changes_only and not (owned or kind == 'main' and (changed_actions or changed_state)):
            continue
        logical = state_lines(state, kind == 'main', changes_only)
        wrapped = []
        for status, text, role in logical:
            width = 62 if role in {'action', 'class'} else 78
            for index, line in enumerate(textwrap.wrap(text, width, break_long_words=False) or ['']):
                wrapped.append((status, line, role, index == 0))
        height = max(85 + sum(42 if r[2] == 'hook' else 23 for r in wrapped), 90 * len(owned) + 20)
        blocks.append((state, owned, wrapped, height))
    header = [provenance(main_label, diff['main']), provenance(feat_label, diff['feat']),
              f'Generated: {diff["generated_at"]} · red − removed · green + added · gray unchanged · ↔ changed path/order',
              'Static factory/call-path and declared-route comparison. Line shifts are ignored; runtime guards and batching are not inferred.']
    initial_old, initial_new = diff['main']['initial_state'], diff['feat']['initial_state']
    if initial_old != initial_new:
        header.append(f'Initial state changed: − {initial_old} → + {initial_new}')
    if set(diff['main']['terminal_outcomes']) != set(diff['feat']['terminal_outcomes']):
        header.append('Root terminal outcomes changed; see JSON for both sets.')
    header = [line for text in header for line in textwrap.wrap(text, 150, break_long_words=False)]
    top = 115 + 24 * len(header)
    width, height = 2100, max(top + sum(b[3] + 40 for b in blocks) + 80, top + 200)
    fig = plt.figure(figsize=(width / 100, height / 100), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, width); ax.set_ylim(height, 0); ax.axis('off')
    def text(x, y, content, size=11, color=INK, bold=False):
        ax.text(x, y, content, fontsize=size, color=color, weight='bold' if bold else 'normal', va='top', zorder=5)
    def box(x, y, w, h, color, fill='white'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=12',
                                   facecolor=fill, edgecolor=color, linewidth=1.5, zorder=2))
    title = {'main': 'actions and control flow', 'errors': 'failure routes', 'cancellation': 'cancellation and terminal routes'}[kind]
    text(50, 30, f'AGVHITO diff · {main_label} → {feat_label} · {title}', 23, INK, True)
    for index, line in enumerate(header):
        text(50, 80 + 24 * index, line, 10, MUTED)
    lookup = {s['name']: s for s in diff['states']}
    y, arrow_count = top, 0
    for state, owned, rows, h in blocks:
        color = COLORS[state['status']] if state['status'] != 'unchanged' else '#CBD5E1'
        fill = '#FFF1F2' if state['status'] == 'removed' else '#F0FDF4' if state['status'] == 'added' else 'white'
        box(50, y, 900, h, color, fill)
        text(75, y + 16, MARKS[state['status']] + state['name'], 17,
             COLORS[state['status']] if state['status'] != 'unchanged' else INK, True)
        cursor = y + 55
        for status, line, role, first in rows:
            if role == 'hook':
                ax.plot([70, 930], [cursor + 3, cursor + 3], color='#CBD5E1', linestyle='--', linewidth=1)
                text(75, cursor + 12, line, 12, INK, True)
                cursor += 42
            else:
                prefix = MARKS[status] if first else '  '
                if status in {'added', 'removed'}:
                    ax.add_patch(FancyBboxPatch((68, cursor - 2), 863, 22,
                        boxstyle='round,pad=0,rounding_size=3', edgecolor='none',
                        facecolor='#F0FDF4' if status == 'added' else '#FFF1F2', zorder=3))
                text(75, cursor, prefix + line, 11 if role != 'note' else 9, COLORS[status], role == 'action' and status in {'added', 'removed'})
                cursor += 23
        for index, route in enumerate(owned):
            edge = route['new'] or route['old']
            status = route['status']; color = COLORS[status]
            ey = y + 20 + index * 90
            box(1570, ey, 480, 65, color,
                '#F0FDF4' if status == 'added' else '#FFF1F2' if status == 'removed' else 'white')
            target = lookup.get(edge['destination'])
            target_version = (target['old'] if status == 'removed' else target['new'] or target['old']) if target else None
            text(1585, ey + 8, MARKS[status] + edge['destination'], 12, color, status != 'unchanged')
            text(1585, ey + 35, target_version['cpp_class'] if target_version else 'Root terminal outcome', 9, MUTED)
            cy = ey + 32
            line, = ax.plot([955, 1567], [cy, cy], color=color, linewidth=1.8 if status != 'unchanged' else 1.2,
                            linestyle='--' if status == 'removed' else '-', zorder=1)
            line.set_gid(f'edge-{arrow_count}')
            head = Polygon([(1567, cy), (1551, cy - 7), (1551, cy + 7)], facecolor=color, edgecolor=color, zorder=5)
            head.set_gid(f'arrowhead-{arrow_count}'); ax.add_patch(head)
            ax.text(1260, cy - 8, MARKS[status] + edge['outcome'], fontsize=10, color=color, ha='center', va='bottom',
                    bbox={'facecolor': BG, 'edgecolor': 'none', 'pad': 3}, zorder=5)
            arrow_count += 1
        y += h + 40
    if not blocks:
        text(50, top + 35, 'No changes in this view.' if changes_only else 'No routes in this view.', 17, MUTED)
    text(50, height - 45, 'Full comparison and source anchors: agvhito-action-diff.json / agvhito-action-diff.md', 10, MUTED)
    for ext in ('png', 'svg'):
        fig.savefig(output / f'{stem}.{ext}', dpi=dpi, facecolor=BG)
    plt.close(fig)
    if (output / f'{stem}.svg').read_text().count('id="arrowhead-') != arrow_count:
        raise ValueError('Diff SVG arrow count mismatch')
    return arrow_count


def connected_dot(diff: dict, routes: list, kind: str, changes_only: bool,
                  main_label='main', feat_label='feat') -> str:
    """One node per state; differences are annotations, not repeated route cards."""
    q = lambda text: json.dumps(str(text))
    esc = lambda text: html.escape(str(text), quote=True)
    if changes_only:
        routes = [r for r in routes if r['status'] != 'unchanged']
    endpoints = {(r['new'] or r['old'])[key] for r in routes for key in ('source', 'destination')}
    states = []
    for state in diff['states']:
        changed_actions = any(r['status'] != 'unchanged' for rows in state['sections'].values() for r in rows)
        changed_state = state['status'] != 'unchanged' or bool(state['factory_order_changed'])
        if kind != 'main' and state['name'] not in endpoints:
            continue
        if changes_only and not (state['name'] in endpoints or kind == 'main' and (changed_actions or changed_state)):
            continue
        states.append(state)
    titles = {'main': 'actions and control flow', 'errors': 'failure routes',
              'cancellation': 'cancellation and terminal routes'}
    title = f'AGVHITO diff · {main_label} → {feat_label} · {titles[kind]}'
    subtitles = [provenance(main_label, diff['main']), provenance(feat_label, diff['feat']),
                 f'Generated: {diff["generated_at"]}',
                 'Red strikethrough: removed · green +: added · gray: unchanged',
                 'Each state appears once; helper-path changes are shown below retained actions.']
    if diff['main']['initial_state'] != diff['feat']['initial_state']:
        subtitles.append(f'Initial state: − {diff["main"]["initial_state"]} → + {diff["feat"]["initial_state"]}')
    heading = f'<TR><TD><FONT POINT-SIZE="24"><B>{esc(title)}</B></FONT></TD></TR>'
    for text in subtitles:
        for line in textwrap.wrap(text, 140, break_long_words=False):
            heading += f'<TR><TD><FONT POINT-SIZE="10" COLOR="{MUTED}">{esc(line)}</FONT></TD></TR>'
    lines = ['digraph agvhito_diff {',
             'graph [rankdir=TB, bgcolor="#F8FAFC", pad="0.5", nodesep="0.7", ranksep="1.0", outputorder=edgesfirst];',
             'node [shape=plain, fontname="DejaVu Sans"];',
             'edge [fontname="DejaVu Sans", fontsize=11, arrowsize=0.9];',
             'graph [labelloc=t, label=<<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="4">' + heading + '</TABLE>>];']
    for state in states:
        version = state['new'] or state['old']
        status = state['status']
        border = COLORS[status] if status != 'unchanged' else '#0F766E' if version['kind'] == 'lifecycle' else '#2563EB'
        fill = '#FFF1F2' if status == 'removed' else '#F0FDF4' if status == 'added' else 'white'
        heading_text = esc(MARKS[status] + state['name'])
        if status == 'removed':
            heading_text = '<S>' + heading_text + '</S>'
        rows = [f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="17" COLOR="{border}"><B>{heading_text}</B></FONT></TD></TR>']
        for row_status, text, role in state_lines(state, kind == 'main', changes_only):
            if role == 'hook':
                rows.append(f'<HR/><TR><TD ALIGN="LEFT"><FONT COLOR="{INK}" POINT-SIZE="12"><B>{esc(text)}</B></FONT></TD></TR>')
                continue
            color = COLORS[row_status]
            text_lines = textwrap.wrap(text, 65 if role != 'note' else 85, break_long_words=False) or ['']
            content = '<BR ALIGN="LEFT"/>'.join(esc((MARKS[row_status] if i == 0 else '  ') + line)
                                                for i, line in enumerate(text_lines))
            if row_status == 'removed':
                content = '<S>' + content + '</S>'
            if role == 'action' and row_status == 'added':
                content = '<B>' + content + '</B>'
            bgcolor = ' BGCOLOR="#FFF1F2"' if row_status == 'removed' else ' BGCOLOR="#F0FDF4"' if row_status == 'added' else ''
            size = 10 if role == 'note' else 12
            face = 'DejaVu Sans Mono' if role == 'action' else 'DejaVu Sans'
            rows.append(f'<TR><TD ALIGN="LEFT"{bgcolor}><FONT FACE="{face}" POINT-SIZE="{size}" COLOR="{color}">{content}</FONT></TD></TR>')
        initial_old = state['name'] == diff['main']['initial_state']
        initial_new = state['name'] == diff['feat']['initial_state']
        if initial_old or initial_new:
            initial_status = 'unchanged' if initial_old and initial_new else 'added' if initial_new else 'removed'
            rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9" COLOR="{COLORS[initial_status]}">{esc(MARKS[initial_status] + "INITIAL STATE")}</FONT></TD></TR>')
        label = f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7" COLOR="{border}" BGCOLOR="{fill}">' + ''.join(rows) + '</TABLE>'
        lines.append(f'{q(state["name"])} [id={q("state-" + state["name"])}, label=<{label}>];')
    names = {s['name'] for s in states}
    old_terminals = set(diff['main']['terminal_outcomes'])
    new_terminals = set(diff['feat']['terminal_outcomes'])
    # A symbol may change from terminal outcome to registered state (or vice versa).
    # Draw it once; explicit state/terminal changes remain in the JSON comparison.
    for terminal in sorted((old_terminals | new_terminals) & endpoints - names):
        status = 'unchanged' if terminal in old_terminals & new_terminals else 'added' if terminal in new_terminals else 'removed'
        label = esc(MARKS[status] + terminal)
        if status == 'removed':
            label = '<S>' + label + '</S>'
        lines.append(f'{q(terminal)} [shape=doublecircle, color={q(COLORS[status])}, label=<{label}>];')
    for index, route in enumerate(routes):
        edge = route['new'] or route['old']
        status = route['status']
        label = esc(MARKS[status] + edge['outcome'])
        if status == 'removed':
            label = '<S>' + label + '</S>'
        style = 'dashed' if status == 'removed' else 'solid'
        # Changed routes remain visible without dominating the established layout.
        constraint = 'true' if status == 'unchanged' else 'false'
        lines.append(f'{q(edge["source"])} -> {q(edge["destination"])} '
                     f'[id="edge-{index}", label=<{label}>, color={q(COLORS[status])}, '
                     f'fontcolor={q(COLORS[status])}, style={style}, constraint={constraint}, '
                     f'penwidth={1.2 if status == "unchanged" else 2.0}];')
    if not states and not routes:
        lines.append('no_changes [label="No changes in this view.", fontcolor="#64748B"];')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def render_connected(dot_path: Path, dpi: int):
    if not shutil.which('dot'):
        raise ValueError('Connected rendering requires Graphviz. Install it with '
                         '`sudo apt install graphviz`, then rerun. '
                         'The DOT/JSON files are available; --no-render skips images.')
    for extension in ('svg', 'png'):
        # cairo PNG rendering supports HTML strikethrough consistently.
        target = 'png:cairo' if extension == 'png' else 'svg'
        result = subprocess.run(['dot', f'-T{target}', f'-Gdpi={dpi}', str(dot_path),
                                 '-o', str(dot_path.with_suffix('.' + extension))],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError('Graphviz rendering failed: ' + result.stderr.strip())
        if extension == 'svg':
            expected = set(re.findall(r'\[id="(edge-\d+)"', dot_path.read_text()))
            svg = ET.parse(dot_path.with_suffix('.svg'))
            actual = {element.get('id') for element in svg.iter()
                      if element.get('id', '').startswith('edge-')}
            if actual != expected:
                raise ValueError('Connected SVG does not contain every expected transition')


def write_markdown(diff, output, stems):
    rows = ['# AGVHITO action-map diff: main → feature', '',
            provenance('Main', diff['main']), provenance('Feature', diff['feat']),
            f'Generated: {diff["generated_at"]}', '',
            'Red strikethrough means removed; green `+` means added; gray content is unchanged. '
            'A retained factory with a changed helper path has separate old/new path annotations.', '',
            '## Counts', '', '| Item | Added | Removed | Retained | Changed path / state |',
            '| --- | ---: | ---: | ---: | ---: |']
    for category in ('states', 'actions', 'routes'):
        c = diff['summary'][category]
        rows.append(f'| {category} | {c.get("added",0)} | {c.get("removed",0)} | {c.get("unchanged",0)} | {c.get("modified",0)} |')
    if diff['main']['initial_state'] != diff['feat']['initial_state']:
        rows += ['', f'Initial state: − `{diff["main"]["initial_state"]}`; + `{diff["feat"]["initial_state"]}`.']
    removed_terminals = set(diff['main']['terminal_outcomes']) - set(diff['feat']['terminal_outcomes'])
    added_terminals = set(diff['feat']['terminal_outcomes']) - set(diff['main']['terminal_outcomes'])
    if removed_terminals or added_terminals:
        rows += ['', 'Root terminal outcomes: ' + '; '.join(
            ['− `' + t + '`' for t in sorted(removed_terminals)] +
            ['+ `' + t + '`' for t in sorted(added_terminals)]) + '.']
    rows += ['', '## Diagrams', '']
    rows += [f'![{kind}]({stem}.png)' for kind, stem in stems.items()]
    rows += ['', '## Action changes', '', '| State | Hook | Change | Expression | Helper path |',
             '| --- | --- | --- | --- | --- |']
    def safe(text):
        return str(text).replace('|', '&#124;').replace('`', '&#96;')
    for state in diff['states']:
        for hook, records in state['sections'].items():
            for row in records:
                if row['status'] == 'unchanged':
                    continue
                record = row['new'] or row['old']
                paths = ' → '.join(record['normalized_path'])
                if row['status'] == 'modified':
                    paths = '− ' + ' → '.join(row['old']['normalized_path']) + '; + ' + paths
                rows.append(f'| `{safe(state["name"])}` | `{safe(hook)}` | {row["status"]} | `{safe(record["expression"])}` | {safe(paths)} |')
        if state['factory_order_changed']:
            rows.append(f'| `{safe(state["name"])}` | {", ".join(state["factory_order_changed"])} | source order changed | See JSON | Runtime execution order is not inferred |')
    rows += ['', '## Transition changes', '', '| Change | Source | Outcome | Destination |',
             '| --- | --- | --- | --- |']
    for row in diff['routes']:
        if row['status'] != 'unchanged':
            e = row['new'] or row['old']
            rows.append(f'| {row["status"]} | `{safe(e["source"])}` | `{safe(e["outcome"])}` | `{safe(e["destination"])}` |')
    rows += ['', '## Limits', '',
             '- Compares static inventories and declared routes, not source code or runtime behavior.',
             '- Source line changes, timestamps, and branch/commit metadata do not count as action changes.',
             '- Factory argument changes appear as a deletion and addition; hook moves do too.',
             '- Ordered alignment preserves both hook sequences, preferring identical helpers among equally long alignments. Reordered actions appear removed at their old position and added at their new position.',
             '- Call paths ignore source-line anchors. Moving the same helper to another file does not change its logical path; raw locations remain in JSON.',
             '- Guards, batching, settling duration, and non-factory function changes cannot be reconstructed from these inventories.',
             '- Reading only retained and added rows reproduces feat order; retained and removed rows reproduce main order. Sequence positions remain in JSON for inspection.',
             '- Each lifecycle hook stays visible in the main view, even when it has no factories.', '']
    (output / 'agvhito-action-diff.md').write_text('\n'.join(rows), encoding='utf-8')


def generate(main_folder: Path, feat_folder: Path, output: Path, dpi=130,
             split=True, changes_only=False, no_render=False,
             main_label='main', feat_label='feat', renderer='graphviz'):
    diff = build_diff(load_folder(main_folder), load_folder(feat_folder))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'agvhito-action-diff.json').write_text(json.dumps(diff, indent=2) + '\n')
    stems = {}
    for kind, routes in split_routes(diff, split).items():
        if kind != 'main' and not routes:
            continue
        stem = 'agvhito-action-diff' + ('' if kind == 'main' else '-' + kind)
        dot_path = output / (stem + '.dot')
        dot_path.write_text(connected_dot(diff, routes, kind, changes_only, main_label, feat_label), encoding='utf-8')
        if not no_render:
            if renderer == 'graphviz':
                render_connected(dot_path, dpi)
            else:
                render_routing(diff, routes, output, stem, kind, dpi, changes_only, main_label, feat_label)
            stems[kind] = stem
    write_markdown(diff, output, stems)
    print(json.dumps(diff['summary'], indent=2))
    print(f'Output: {output.resolve()}')
    return diff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version',
                        version='AGVHITO action comparator: ordered-alignment-v1 (plain labels)')
    parser.add_argument('main_folder', type=Path)
    parser.add_argument('feat_folder', type=Path)
    parser.add_argument('--out-dir', type=Path, default=Path('diagrams/diff'))
    parser.add_argument('--dpi', type=int, default=130)
    parser.add_argument('--split', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--changes-only', action='store_true', help='Hide unchanged action/route rows and unaffected states')
    parser.add_argument('--no-render', action='store_true', help='DOT/JSON/Markdown only; no rendering dependencies needed')
    parser.add_argument('--renderer', choices=('graphviz', 'routing'), default='graphviz',
                        help='Connected graph by default; routing selects the previous Matplotlib view')
    parser.add_argument('--main-label', default='main')
    parser.add_argument('--feat-label', default='feat')
    args = parser.parse_args()
    if args.dpi < 72:
        parser.error('--dpi must be at least 72')
    try:
        generate(args.main_folder, args.feat_folder, args.out_dir, args.dpi,
                 args.split, args.changes_only, args.no_render, args.main_label, args.feat_label, args.renderer)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
