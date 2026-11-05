#!/usr/bin/env python3
"""Render the AGVHITO state machine, with each state's actions, from source.

By default this renders the current checkout (including uncommitted edits).
Pass --base to compare against another branch or commit instead; refs are read
straight from Git, so nothing is checked out or stashed.

Python 3.10+ and matplotlib; Graphviz's `dot` gives a connected layout (falls
back to a matplotlib routing view). Static call paths are shown, including
helper calls; conditions, execution frequency, and firmware order are not
inferred. This is a bounded lexical source scan, not a compiler.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import html
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import xml.etree.ElementTree as ET


# ============================================================================
# Source parsing and single-branch rendering
# ============================================================================

DEFAULT_PACKAGE = Path('/home/jon-gonzales/volley/src/agvhito')
BG, INK, MUTED = '#F8FAFC', '#0F172A', '#475569'
BLUE, TEAL, ROSE, AMBER = '#2563EB', '#0F766E', '#BE123C', '#92400E'
# Diff colors
DIFF_MUTED, RED, GREEN = '#64748B', '#BE123C', '#15803D'
HIGHLIGHTS = {'MakeStartPauseAction', 'MakeStopPauseAction', 'MakeSoftEStopAction'}
HOOKS = ('OnEntry', 'Step', 'OnExit')


def source_metadata(package: Path) -> dict:
    """Record checkout provenance; exported source without Git remains supported."""
    generated = datetime.now().astimezone()
    metadata = {'generated_at': generated.isoformat(timespec='seconds'),
                'generated_timezone': generated.tzname(), 'source_root': str(package),
                'branch': None, 'commit': None, 'commit_short': None,
                'commit_date': None, 'sm_dirty': None}
    def git(*args):
        try:
            result = subprocess.run(['git', '-C', str(package), *args],
                                    capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None
    commit = git('rev-parse', '--verify', 'HEAD')
    if commit:
        branch = git('symbolic-ref', '--quiet', '--short', 'HEAD')
        status = git('status', '--porcelain', '--untracked-files=normal', '--',
                     'src/sm', 'include/agvhito/sm')
        metadata.update(branch=branch or 'detached HEAD', commit=commit,
                        commit_short=git('rev-parse', '--short=12', 'HEAD') or commit[:12],
                        commit_date=git('show', '-s', '--format=%cI', 'HEAD'),
                        sm_dirty=bool(status) if status is not None else None)
    return metadata


def subtitle_lines(model: dict) -> list[str]:
    metadata = model.get('metadata', {})
    dirty = metadata.get('sm_dirty')
    status = 'SM modified' if dirty is True else 'SM clean' if dirty is False else 'Git unavailable'
    return [f'Branch: {metadata.get("branch") or "unavailable"} · '
            f'Commit: {metadata.get("commit_short") or "unavailable"} · {status}',
            f'Generated: {metadata.get("generated_at", "unavailable")} '
            f'({metadata.get("generated_timezone") or "local time"}) · '
            f'{len(model["states"])} states · {len(model["edges"])} routes · '
            f'Source SHA: {model["source_sha256"][:12]}']


def mask_cpp(text: str, strings: bool = True) -> str:
    """Mask comments/literals while preserving offsets and line numbers."""
    pattern = re.compile(
        r'R"(?P<delim>[^ ()\\\t\r\n]{0,16})\(.*?\)(?P=delim)"'
        r'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', re.S)
    def replace(match):
        token = match[0]
        if not strings and not token.startswith(('//', '/*')):
            return token
        return ''.join('\n' if c == '\n' else ' ' for c in token)
    return pattern.sub(replace, text)


def closing(code: str, start: int, left: str = '{', right: str = '}') -> int:
    if code[start] != left:
        raise ValueError(f'Expected {left!r} at offset {start}')
    depth = 0
    for i in range(start, len(code)):
        if code[i] == left:
            depth += 1
        elif code[i] == right:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f'Unbalanced {left}{right} at offset {start}')


def split_args(text: str) -> list[str]:
    masked = mask_cpp(text)
    depth, start, parts = 0, 0, []
    for i, char in enumerate(masked):
        if char in '({[':
            depth += 1
        elif char in ')}]':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return parts


def calls(text: str):
    code = mask_cpp(text)
    for match in re.finditer(r'\b((?:[A-Za-z_]\w*::)*[A-Za-z_]\w*)\s*\(', code):
        start = code.index('(', match.start())
        end = closing(code, start, '(', ')')
        yield match[1], text[start + 1:end], match.start()


def ordered_calls(text: str):
    """Expand argument calls before callee bodies, retaining source offsets.

    Sibling expressions retain lexical order; this does not resolve C++'s
    unspecified argument evaluation order or evaluate control-flow guards.
    """
    code = mask_cpp(text)
    pattern = re.compile(r'\b((?:[A-Za-z_]\w*::)*[A-Za-z_]\w*)\s*\(')
    def visit(lo, hi):
        cursor = lo
        while (match := pattern.search(code, cursor, hi)) is not None:
            opening = code.index('(', match.start())
            end = closing(code, opening, '(', ')')
            yield from visit(opening + 1, end)
            yield match[1], text[opening + 1:end], match.start()
            cursor = end + 1
    yield from visit(0, len(code))


def functions(files: dict[str, str]) -> list[dict]:
    """Recognize ordinary free/member definitions, excluding declarations/calls."""
    found = []
    controls = {'if', 'for', 'while', 'switch', 'catch', 'sizeof', 'requires'}
    for path, text in sorted(files.items()):
        code = mask_cpp(text)
        namespaces = []
        for ns in re.finditer(r'\bnamespace\s+([\w:]+)\s*\{', code):
            opening = code.index('{', ns.start())
            namespaces.append((opening, closing(code, opening), ns[1]))
        consumed = -1
        for match in re.finditer(r'\b((?:[A-Za-z_]\w*::)*[A-Za-z_]\w*)\s*\(', code):
            if match.start() < consumed or match[1] in controls:
                continue
            start = code.index('(', match.start())
            end = closing(code, start, '(', ')')
            tail = re.match(r'\s*(?:(?:const|override|final)\s*)*\{', code[end + 1:])
            if not tail:
                continue
            opening = end + 1 + tail[0].rfind('{')
            finish = closing(code, opening)
            namespace = '::'.join(n for a, b, n in namespaces if a < match.start() < b)
            name = match[1]
            key = namespace + '::' + name if namespace else name
            found.append({'name': name, 'key': key, 'namespace': namespace,
                          'source': path, 'line': text.count('\n', 0, match.start()) + 1,
                          'body': text[opening + 1:finish],
                          'body_line': text.count('\n', 0, opening + 1) + 1,
                          'id': f'{path}:{opening}'})
            consumed = finish + 1
    return found


def parse_package(package: Path) -> dict:
    package = package.resolve()
    src, inc = package / 'src/sm', package / 'include/agvhito/sm'
    if not (src / 'root.cpp').is_file() or not (inc / 'state_strings.hpp').is_file():
        raise ValueError(f'Expected src/sm/root.cpp and include/agvhito/sm/state_strings.hpp under {package}')
    paths = sorted([*src.rglob('*.cpp'), *inc.rglob('*.hpp')])
    files = {str(p.relative_to(package)): p.read_text(encoding='utf-8') for p in paths}
    values = {'yasminx::kOutcomeCanceled': 'canceled'}
    for text in files.values():
        clean = mask_cpp(text, strings=False)
        for m in re.finditer(r'\bconstexpr\s+(?:auto|[\w:]+(?:\s*\*)?)\s+(k\w+)\s*(?:=\s*)?\{?\s*"([^"\n]+)"', clean):
            if m[1] in values and values[m[1]] != m[2]:
                # Local kName constants need not be globally unique.
                if m[1] != 'kName':
                    raise ValueError(f'Ambiguous constant {m[1]}')
            values[m[1]] = m[2]
    def value(symbol):
        symbol = symbol.strip()
        if symbol.startswith('"') and symbol.endswith('"'):
            return symbol[1:-1]
        if symbol in values:
            return values[symbol]
        if symbol.startswith(('sm::', 'volley::agvhito::sm::')) and symbol.split('::')[-1] in values:
            return values[symbol.split('::')[-1]]
        raise ValueError(f'Unresolved state/outcome constant: {symbol}')

    def transition_entries(body: str, label: str) -> list[dict]:
        entries = []
        for entry in split_args(body):
            entry = mask_cpp(entry, strings=False).strip()
            if not entry:
                continue
            if not entry.startswith('{') or not entry.endswith('}'):
                raise ValueError(f'Unsupported transition entry in {label}: {entry}')
            pair = split_args(entry[1:-1])
            if len(pair) != 2:
                raise ValueError(f'Expected outcome/destination pair in {label}')
            entries.append({'outcome_constant': pair[0], 'destination_constant': pair[1],
                            'outcome': value(pair[0]), 'destination': value(pair[1])})
        if len({e['outcome'] for e in entries}) != len(entries):
            raise ValueError(f'Duplicate outcome in {label}')
        return entries

    # Transition maps may be declared in any state-machine header or source file.
    transitions, declared_in = {}, {}
    map_type = r'(?:[\w:]*\bTransitions|std::(?:unordered_)?map\s*<[^;{}]*>)'
    for path, text in files.items():
        code = mask_cpp(text)
        for m in re.finditer(r'\b' + map_type + r'\s+(k\w+)\s*(?:=\s*)?\{', code):
            start = code.index('{', m.end() - 1)
            entries = transition_entries(text[start + 1:closing(code, start)], m[1])
            if m[1] in transitions and transitions[m[1]] != entries:
                raise ValueError(f'Transition map {m[1]} is declared differently in '
                                 f'{declared_in[m[1]]} and {path}')
            transitions[m[1]], declared_in[m[1]] = entries, path

    root_text = files['src/sm/root.cpp']
    root_code = mask_cpp(root_text)
    states = []
    registrations = list(re.finditer(r'\badd_state\s*\(', root_code))
    for m in registrations:
        opening = root_code.index('(', m.start())
        end = closing(root_code, opening, '(', ')')
        call = root_text[m.start():end + 1]
        args = [mask_cpp(a, strings=False).strip() for a in split_args(root_text[opening + 1:end])]
        if len(args) != 3:
            raise ValueError(f'Expected add_state(name, state, transitions) in src/sm/root.cpp, got: {call}')
        cls = re.search(r'\b(?:std::)?(?:make_shared|make_unique|shared_ptr|unique_ptr)\s*<\s*([\w:]+)\s*>'
                        r'|\bnew\s+([\w:]+)', args[1])
        if not cls:
            raise ValueError(f'Cannot find the state class for {args[0]} in src/sm/root.cpp '
                             f'(expected std::make_shared<SomeState>(...)): {args[1]}')
        transition_arg = args[2]
        if transition_arg.startswith('{'):
            # Transitions written inline at the registration.
            transition_map = f'<inline {args[0]}>'
            transitions[transition_map] = transition_entries(transition_arg[1:-1], transition_map)
        else:
            transition_map = re.sub(r'^(?:[\w]+::)+', '', transition_arg)
            if transition_map not in transitions:
                known = ', '.join(sorted(transitions)) or 'none'
                raise ValueError(f'Transition map {transition_arg!r} for {args[0]} was not found in any '
                                 f'src/sm or include/agvhito/sm file. Known maps: {known}')
        args[2] = transition_map
        class_name = (cls[1] or cls[2]).split('::')[-1]
        declarations = []
        for p, text in files.items():
            if p.endswith('.hpp'):
                match = re.search(r'\bclass\s+' + re.escape(class_name) + r'\s*(?:final\s*)?:\s*([^\{]+)\{', mask_cpp(text))
                if match:
                    declarations.append((p, match[1]))
        if len(declarations) != 1:
            raise ValueError(f'Expected one class declaration for {class_name}')
        header, bases = declarations[0]
        if re.search(r'\bLifecycleState\b', bases):
            kind = 'lifecycle'
        elif re.search(r'\bState\b', bases):
            kind = 'state'
        else:
            raise ValueError(f'Unsupported state base for {class_name}: {bases}')
        states.append({'name': value(args[0]), 'constant': args[0], 'cpp_class': class_name,
                       'kind': kind, 'header': header, 'transition_map': args[2]})
    if not states or len({s['name'] for s in states}) != len(states):
        raise ValueError('No states found, or duplicate state registrations')

    terminal_match = re.search(r'\byasmin::Outcomes\s*\{', root_code)
    if not terminal_match:
        raise ValueError('Cannot resolve root terminal outcomes')
    start = root_code.index('{', terminal_match.start())
    end = closing(root_code, start)
    terminals = [value(s) for s in split_args(root_text[start + 1:end]) if s]
    edges = [dict(e, source=s['name'], transition_map=s['transition_map'])
             for s in states for e in transitions[s['transition_map']]]
    destinations = {s['name'] for s in states} | set(terminals)
    for edge in edges:
        if edge['destination'] not in destinations:
            raise ValueError(f'Unregistered transition destination: {edge["destination"]}')
    initial = states[0]['name']
    explicit = re.search(r'\bset_initial_state\s*\(([^)]+)\)', root_code)
    if explicit:
        initial = value(root_text[explicit.start(1):explicit.end(1)])
    if initial not in {s['name'] for s in states}:
        raise ValueError('Initial state is not registered')
    fingerprint = hashlib.sha256(''.join(p + '\0' + t for p, t in files.items()).encode()).hexdigest()
    return {'states': states, 'edges': edges, 'terminal_outcomes': terminals,
            'initial_state': initial, 'source_sha256': fingerprint,
            'metadata': source_metadata(package),
            'files': files, 'functions': functions(files), 'warnings': []}


def serializable(model: dict) -> dict:
    return {k: v for k, v in model.items() if k not in {'files', 'functions'}}


def graph_dot(model: dict, sections: dict | None = None) -> str:
    def esc(s):
        return html.escape(str(s), quote=True)
    def quote(s):
        return json.dumps(str(s))
    lines = ['digraph agvhito {', 'graph [rankdir=TB, bgcolor="#F8FAFC", pad="0.4", nodesep="0.5", ranksep="0.9"];',
             'node [fontname="DejaVu Sans", shape=plain];',
             'edge [fontname="DejaVu Sans", fontsize=10, arrowsize=0.9, penwidth=1.5];']
    title = model.get('diagram_title', 'AGVHITO state machine')
    heading = f'<TR><TD><FONT POINT-SIZE="22"><B>{esc(title)}</B></FONT></TD></TR>'
    heading += ''.join(f'<TR><TD><FONT POINT-SIZE="10" COLOR="{MUTED}">{esc(line)}</FONT></TD></TR>'
                       for line in subtitle_lines(model))
    lines.append('graph [label=<<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="4">' + heading +
                 f'</TABLE>>, labelloc=t, fontname="DejaVu Sans", fontcolor="{INK}"];')
    for state in model['states']:
        color = TEAL if state['kind'] == 'lifecycle' else BLUE
        rows = [f'<TR><TD><FONT COLOR="{color}"><B>{esc(state["name"])}</B></FONT></TD></TR>',
                f'<TR><TD>{esc(state["cpp_class"])} · {esc(state["kind"])}</TD></TR>']
        if state['name'] == model['initial_state']:
            rows.append('<TR><TD><FONT POINT-SIZE="9">INITIAL STATE</FONT></TD></TR>')
        if sections is not None:
            for hook, records in sections[state['name']].items():
                rows.append(f'<HR/><TR><TD ALIGN="LEFT"><FONT COLOR="{TEAL}"><B>{hook}</B></FONT></TD></TR>')
                if not records:
                    rows.append('<TR><TD> </TD></TR>')
                for record in records:
                    color_call = AMBER if record['highlight'] else INK
                    rows.append(f'<TR><TD ALIGN="LEFT"><FONT FACE="DejaVu Sans Mono" COLOR="{color_call}">{esc(str(record.get("sequence", "")) + ". " + record["expression"])}</FONT></TD></TR>')
                    rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9">{esc(record["via"])}</FONT></TD></TR>')
        label = '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="8" COLOR="' + color + '" BGCOLOR="white">' + ''.join(rows) + '</TABLE>'
        lines.append(f'{quote(state["name"])} [label=<{label}>];')
    for terminal in model['terminal_outcomes']:
        lines.append(f'{quote(terminal)} [shape=doublecircle, color="{ROSE}", fontcolor="{ROSE}", label={quote(terminal)}];')
    for edge in model['edges']:
        color = ROSE if edge['destination'] in model['terminal_outcomes'] or edge['outcome'] == 'errored' else BLUE
        lines.append(f'{quote(edge["source"])} -> {quote(edge["destination"])} [label={quote(edge["outcome"])}, color="{color}", fontcolor="{color}"];')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def render_routing(model: dict, output: Path, stem: str, dpi: int, sections=None):
    """Fallback: repeat destination cards so every route remains legible."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Polygon
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'path'})
    visible_states = model['states']
    if model.get('diagram_kind') in {'errors', 'cancellation'}:
        visible_states = [s for s in visible_states
                          if any(e['source'] == s['name'] for e in model['edges'])]
    heights = {}
    for s in visible_states:
        source_height = 90
        if sections is not None:
            for hook, records in sections[s['name']].items():
                source_height += 45
                for r in records:
                    source_height += 22 * len(textwrap.wrap(str(r.get('sequence', '')) + '. ' + r['expression'], 56)) + 18 * len(textwrap.wrap(r['via'], 68)) + 12
        routes = sum(e['source'] == s['name'] for e in model['edges'])
        heights[s['name']] = max(source_height + 20, routes * 82 + 20)
    header_lines = [wrapped for line in subtitle_lines(model)
                    for wrapped in textwrap.wrap(line, 140, break_long_words=False)]
    header_bottom = 145 + 24 * len(header_lines)
    width, height = 1900, header_bottom + sum(heights.values()) + 55 * len(heights) + 50
    fig = plt.figure(figsize=(width / 100, height / 100), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, width); ax.set_ylim(height, 0); ax.axis('off')
    def text(x, y, label, size=12, color=INK, weight='normal'):
        ax.text(x, y, label, fontsize=size, color=color, weight=weight, va='top', zorder=4)
    def box(x, y, w, h, color, kind='lifecycle'):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
            boxstyle=f'round,pad=0,rounding_size={14 if kind == "lifecycle" else 0}',
            facecolor='white', edgecolor=color, linewidth=1.6, zorder=2))
    text(50, 35, model.get('diagram_title', 'AGVHITO · ' + ('state actions' if sections is not None else 'state machine')), 26, weight='bold')
    for index, line in enumerate(header_lines):
        text(50, 85 + 24 * index, line, 11, MUTED)
    text(50, header_bottom - 35, 'Routing view: repeated destination cards represent the same state. Blue = State; teal = LifecycleState; rose = terminal.', 11, MUTED)
    by_name = {s['name']: s for s in model['states']}
    y = header_bottom
    count = 0
    for s in visible_states:
        h = heights[s['name']]
        color = TEAL if s['kind'] == 'lifecycle' else BLUE
        box(50, y, 760, h, color, s['kind'])
        text(75, y + 18, s['name'], 18, color, 'bold')
        text(75, y + 48, f'{s["cpp_class"]} · {s["kind"]}' + (' · INITIAL' if s['name'] == model['initial_state'] else ''), 12, MUTED)
        cursor = y + 88
        if sections is not None:
            for hook, records in sections[s['name']].items():
                ax.plot([70, 790], [cursor, cursor], color='#CBD5E1', linestyle='--', linewidth=1)
                text(75, cursor + 8, hook, 13, TEAL, 'bold')
                cursor += 45
                for r in records:
                    for line in textwrap.wrap(str(r.get('sequence', '')) + '. ' + r['expression'], 56):
                        text(75, cursor, line, 12, AMBER if r['highlight'] else INK, 'bold' if r['highlight'] else 'normal')
                        cursor += 22
                    for line in textwrap.wrap(r['via'], 68):
                        text(75, cursor, line, 9, MUTED)
                        cursor += 18
                    cursor += 12
        for index, edge in enumerate(e for e in model['edges'] if e['source'] == s['name']):
            ey = y + 18 + index * 82
            target = by_name.get(edge['destination'])
            target_color = (TEAL if target['kind'] == 'lifecycle' else BLUE) if target else ROSE
            box(1380, ey, 470, 65, target_color, target['kind'] if target else 'terminal')
            text(1398, ey + 8, edge['destination'], 13, target_color, 'bold')
            text(1398, ey + 33, target['cpp_class'] if target else 'Root terminal outcome', 10, MUTED)
            cy = ey + 32
            line, = ax.plot([815, 1377], [cy, cy], color=target_color, linewidth=1.6, zorder=1)
            line.set_gid(f'edge-{count}')
            head = Polygon([(1377, cy), (1361, cy - 7), (1361, cy + 7)], facecolor=target_color, edgecolor=target_color, zorder=5)
            head.set_gid(f'arrowhead-{count}'); ax.add_patch(head)
            ax.text(1090, cy - 8, edge['outcome'], fontsize=10, ha='center', va='bottom', color=target_color, bbox={'facecolor': BG, 'edgecolor': 'none', 'pad': 3})
            count += 1
        y += h + 55
    text(50, height - 35, 'Declared transitions and static call sites; no runtime ordering or branch reachability is inferred.', 10, MUTED)
    for extension in ('png', 'svg'):
        fig.savefig(output / f'{stem}.{extension}', dpi=dpi, facecolor=BG)
    plt.close(fig)
    if (output / f'{stem}.svg').read_text().count('id="arrowhead-') != len(model['edges']):
        raise ValueError('Rendered arrow count does not match parsed transition count')


def render(model, output, stem, dpi, renderer, sections=None):
    output.mkdir(parents=True, exist_ok=True)
    dot_path = output / f'{stem}.dot'
    dot_path.write_text(graph_dot(model, sections), encoding='utf-8')
    if renderer == 'none':
        return 'none'
    if renderer == 'graphviz' or renderer == 'auto' and shutil.which('dot'):
        if not shutil.which('dot'):
            raise ValueError('Graphviz is unavailable. Install graphviz or use --renderer matplotlib.')
        for extension in ('svg', 'png'):
            subprocess.run(['dot', f'-T{extension}', f'-Gdpi={dpi}', str(dot_path), '-o', str(output / f'{stem}.{extension}')], check=True)
        return 'graphviz'
    render_routing(model, output, stem, dpi, sections)
    return 'matplotlib'


def diagram_views(model: dict, split: bool = True) -> dict[str, dict]:
    """Partition declared routes without removing any from the source model."""
    if not split:
        return {'main': dict(model, diagram_kind='main',
                             diagram_title='AGVHITO · all transitions')}
    error_states = {s['name'] for s in model['states'] if s['cpp_class'] == 'ErrorState'}
    grouped = {'main': [], 'errors': [], 'cancellation': []}
    for edge in model['edges']:
        if edge['outcome'] == 'canceled':
            kind = 'cancellation'
        elif edge['destination'] in error_states or edge['outcome'] == 'errored':
            kind = 'errors'
        elif edge['destination'] in model['terminal_outcomes']:
            kind = 'cancellation'
        else:
            kind = 'main'
        grouped[kind].append(edge)
    titles = {'main': 'AGVHITO · control flow', 'errors': 'AGVHITO · failure routes',
              'cancellation': 'AGVHITO · cancellation and terminal routes'}
    views = {}
    for kind, edges in grouped.items():
        names = {e['source'] for e in edges} | {e['destination'] for e in edges}
        states = model['states'] if kind == 'main' else [s for s in model['states'] if s['name'] in names]
        views[kind] = dict(model, states=states, edges=edges,
                           terminal_outcomes=[t for t in model['terminal_outcomes'] if t in names],
                           diagram_kind=kind, diagram_title=titles[kind])
    if sum(len(v['edges']) for v in views.values()) != len(model['edges']):
        raise ValueError('Split views do not account for all transitions')
    return views


def render_views(model, output, stem, dpi, renderer, sections=None, split=True):
    views = diagram_views(model, split)
    manifest = {}
    used = 'none'
    for kind, view in views.items():
        if kind != 'main' and not view['edges']:
            continue
        name = stem if kind == 'main' else stem + '-' + kind
        used = render(view, output, name, dpi, renderer,
                      sections if kind == 'main' else None)
        manifest[kind] = {'stem': name, 'route_count': len(view['edges']),
                          'edges': view['edges']}
    (output / f'{stem}-views.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return used, manifest


def arguments(description, default_dpi=130, extend=None, epilog=None):
    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package-root', type=Path, default=DEFAULT_PACKAGE,
                        help='AGVHITO package root; defaults to the local Volley checkout')
    parser.add_argument('--out-dir', type=Path, default=Path('diagrams'))
    parser.add_argument('--dpi', type=int, default=default_dpi)
    parser.add_argument('--renderer', choices=('auto', 'graphviz', 'matplotlib', 'none'), default='auto')
    parser.add_argument('--split', action=argparse.BooleanOptionalAction, default=True,
                        help='Separate failure and cancellation routes (default); --no-split shows all routes together')
    if extend is not None:
        extend(parser)
    args = parser.parse_args()
    if args.dpi < 72:
        parser.error('--dpi must be at least 72')
    return parser, args


# ============================================================================
# Branch comparison
# ============================================================================

COLORS = {'removed': RED, 'added': GREEN, 'unchanged': DIFF_MUTED, 'modified': AMBER}
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
        # Code fingerprints (absent in inventories from older generator versions).
        old_hooks = old_model.get('hook_digests', {}).get(name, {})
        new_hooks = new_model.get('hook_digests', {}).get(name, {})
        code_changes = {}
        if old and new:
            for hook in hooks:
                a, b = old_hooks.get(hook), new_hooks.get(hook)
                if a is None or b is None or a['sha'] == b['sha']:
                    continue
                code_changes[hook] = {
                    'defined': [a['sha'] is not None, b['sha'] is not None],
                    'added_calls': sorted(set(b['calls']) - set(a['calls'])),
                    'removed_calls': sorted(set(a['calls']) - set(b['calls'])),
                    'old_functions': a['functions'], 'new_functions': b['functions']}
        old_outside = old_model.get('state_digests', {}).get(name, {}).get('outside_hooks_sha')
        new_outside = new_model.get('state_digests', {}).get(name, {}).get('outside_hooks_sha')
        outside_changed = bool(old and new and old_outside and new_outside and old_outside != new_outside)
        if status == 'unchanged' and (code_changes or outside_changed):
            status = 'modified'
        states.append({'name': name, 'status': status, 'old': old, 'new': new,
                       'changed_fields': changed, 'sections': sections,
                       'factory_order_changed': order_changes,
                       'code_changes': code_changes, 'outside_hooks_changed': outside_changed})
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
            'summary': {'hooks_with_code_changes': sum(len(s['code_changes']) for s in states),
                        'states': dict(Counter(s['status'] for s in states)),
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
    if state.get('outside_hooks_changed'):
        lines.append(('modified', 'Code outside the hooks changed (constants, members, constructor or includes)', 'note'))
    if not show_actions:
        hooks = ', '.join(state.get('code_changes', {}))
        if hooks:
            lines.append(('modified', 'Code changed in ' + hooks, 'note'))
        return lines
    for hook, rows in state['sections'].items():
        lines.append(('unchanged', hook, 'hook'))
        change = state.get('code_changes', {}).get(hook)
        if change:
            before, after = change['defined']
            summary = ('hook newly overridden' if after and not before else
                       'override removed; inherited hook runs' if before and not after else
                       'code changed (comments/whitespace ignored)')
            lines.append(('modified', summary, 'note'))
            if change['added_calls']:
                lines.append(('added', 'now calls ' + ', '.join(change['added_calls']), 'note'))
            if change['removed_calls']:
                lines.append(('removed', 'no longer calls ' + ', '.join(change['removed_calls']), 'note'))
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


def render_diff_routing(diff: dict, routes: list, output: Path, stem: str, kind: str, dpi: int,
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
        text(50, 80 + 24 * index, line, 10, DIFF_MUTED)
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
            text(1585, ey + 35, target_version['cpp_class'] if target_version else 'Root terminal outcome', 9, DIFF_MUTED)
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
        text(50, top + 35, 'No changes in this view.' if changes_only else 'No routes in this view.', 17, DIFF_MUTED)
    text(50, height - 45, 'Full comparison and source anchors: agvhito-action-diff.json / agvhito-action-diff.md', 10, DIFF_MUTED)
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
            heading += f'<TR><TD><FONT POINT-SIZE="10" COLOR="{DIFF_MUTED}">{esc(line)}</FONT></TD></TR>'
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
    rows = ['# AGVHITO action-map diff: base → feature', '',
            provenance('Base', diff['main']), provenance('Feature', diff['feat']),
            f'Generated: {diff["generated_at"]}', '',
            'Red strikethrough means removed; green `+` means added; gray content is unchanged. '
            'A retained factory with a changed helper path has separate old/new path annotations.', '',
            '## Counts', '', '| Item | Added | Removed | Retained | Changed path / state |',
            '| --- | ---: | ---: | ---: | ---: |']
    for category in ('states', 'actions', 'routes'):
        c = diff['summary'][category]
        rows.append(f'| {category} | {c.get("added",0)} | {c.get("removed",0)} | {c.get("unchanged",0)} | {c.get("modified",0)} |')
    rows.append(f'| hooks with code changes | | | | {diff["summary"].get("hooks_with_code_changes", 0)} |')
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
    rows += ['', '## Code changes', '',
             'Hooks whose code differs (including traced helpers), even when no factory call or route changed. '
             'Comments and whitespace are ignored; log text and constants are not.', '',
             '| State | Where | Change | Calls added | Calls removed |', '| --- | --- | --- | --- | --- |']
    for state in diff['states']:
        if state.get('outside_hooks_changed'):
            rows.append(f'| `{safe(state["name"])}` | outside hooks | constants, members, constructor or includes | | |')
        for hook, change in state.get('code_changes', {}).items():
            before, after = change['defined']
            kind = 'newly overridden' if after and not before else 'override removed' if before and not after else 'code changed'
            rows.append(f'| `{safe(state["name"])}` | `{safe(hook)}` | {kind} | '
                        f'{safe(", ".join(change["added_calls"])) or "—"} | {safe(", ".join(change["removed_calls"])) or "—"} |')
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
             '- Non-factory code changes are flagged per hook with the set of calls added or removed; guard logic, timing, and constant values are not interpreted. Read the source diff for the details.',
             '- Reading only retained and added rows reproduces feat order; retained and removed rows reproduce main order. Sequence positions remain in JSON for inspection.',
             '- Each lifecycle hook stays visible in the main view, even when it has no factories.', '']
    (output / 'agvhito-action-diff.md').write_text('\n'.join(rows), encoding='utf-8')


def generate_diff(main_folder: Path, feat_folder: Path, output: Path, dpi=130,
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
                render_diff_routing(diff, routes, output, stem, kind, dpi, changes_only, main_label, feat_label)
            stems[kind] = stem
    write_markdown(diff, output, stems)
    print(json.dumps(diff['summary'], indent=2))
    print(f'Output: {output.resolve()}')
    return diff


# ============================================================================
# Action audit, git refs, and command line
# ============================================================================

EPILOG = """examples:
  # diagram for whatever is checked out now
  %(prog)s

  # what does the feature branch change relative to main?
  %(prog)s --base main --feature origin/dpa/SW2-805/prep-for-recovery

  # compare your uncommitted working tree against main, hiding unchanged rows
  %(prog)s --base main --changes-only
"""

NOT_CALLS = {'if', 'for', 'while', 'switch', 'catch', 'return', 'sizeof', 'alignof', 'decltype',
             'static_cast', 'dynamic_cast', 'const_cast', 'reinterpret_cast', 'noexcept',
             'requires', 'throw', 'co_return', 'co_await', 'co_yield', 'new', 'delete'}


def code_digest(chunks) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update('\0'.join(cpp_tokens(mask_cpp(chunk, strings=False))).encode())
        digest.update(b'\1')
    return digest.hexdigest()


def called_names(body: str) -> set[str]:
    """Non-factory calls, for a readable summary of what a changed hook does differently."""
    names = set()
    for name, _, _ in calls(body):
        short = name.split('::')[-1]
        if (short in NOT_CALLS or re.fullmatch(r'[A-Z][A-Z0-9_]*', short)
                or re.fullmatch(r'Make\w*Action', short)):
            continue
        names.add(name)
    return names


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

    def walk(fn, state, hook, chain, stack, seen):
        if fn['id'] in stack:
            warning = f'Recursive helper path cut: {" -> ".join(chain)}'
            if warning not in model['warnings']:
                model['warnings'].append(warning)
            return
        stack = stack | {fn['id']}
        seen.setdefault(fn['id'], fn)
        for name, args, offset in ordered_calls(fn['body']):
            line = fn['body_line'] + fn['body'].count('\n', 0, offset)
            short = name.split('::')[-1]
            if re.fullmatch(r'Make\w*Action', short):
                args = re.sub(r'\s+', ' ', args).strip()
                record = {'state': state['name'], 'cpp_class': state['cpp_class'],
                          'hook': hook, 'sequence': len(sections[state['name']][hook]) + 1, 'factory': short, 'arguments': args,
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
                     chain + [helper['name'] + f'@{fn["source"]}:{line}'], stack, seen)

    hook_digests, hook_roots = {}, []
    for state in model['states']:
        hooks = HOOKS if state['kind'] == 'lifecycle' else ('Execute',)
        sections[state['name']] = {hook: [] for hook in hooks}
        hook_digests[state['name']] = {}
        for hook in hooks:
            roots = [f for f in definitions if f['name'] == state['cpp_class'] + '::' + hook]
            if len(roots) > 1:
                raise ValueError(f'Multiple definitions of {state["cpp_class"]}::{hook}')
            seen = {}
            if roots:
                walk(roots[0], state, hook, [roots[0]['name']], set(), seen)
                hook_roots.append(roots[0])
            hook_digests[state['name']][hook] = {
                'sha': code_digest(f['body'] for f in seen.values()) if seen else None,
                'functions': [f['name'] for f in seen.values()],
                'calls': sorted(set().union(*(called_names(f['body']) for f in seen.values()))),
            }
            if not roots:
                # Inherited lifecycle hooks are allowed, but a declared method
                # without a recognized definition must not silently disappear.
                header = model['files'][state['header']]
                if re.search(r'\b' + hook + r'\s*\(', mask_cpp(header)):
                    raise ValueError(f'Declared hook was not parsed: {state["cpp_class"]}::{hook}')
                if state['kind'] == 'state':
                    raise ValueError(f'Execute definition missing for {state["cpp_class"]}')

    # Code in a state's own files outside its hook bodies (constants, members,
    # constructor, includes). Hook bodies are blanked so they are counted once.
    state_digests = {}
    blank = {}
    for root in hook_roots:
        opening = int(root['id'].rsplit(':', 1)[1])
        blank.setdefault(root['source'], []).append((opening + 1, opening + 1 + len(root['body'])))
    for state in model['states']:
        owned = sorted({state['header']} | {f['source'] for f in definitions
                                             if f['name'].split('::')[0] == state['cpp_class']})
        chunks = []
        for source in owned:
            text = model['files'][source]
            for lo, hi in sorted(blank.get(source, []), reverse=True):
                text = text[:lo] + text[hi:]
            chunks.append(source + '\0' + text)
        state_digests[state['name']] = {'outside_hooks_sha': code_digest(chunks), 'files': owned}
    model['hook_digests'], model['state_digests'] = hook_digests, state_digests

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


def generate(package_root: Path, output_dir: Path, dpi=130, renderer='auto', split=True,
             metadata: dict | None = None):
    model = parse_package(package_root)
    if metadata:
        model['metadata'].update(metadata)
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
                expr = (str(r['sequence']) + '. ' + r['expression']).replace('|', '&#124;').replace('`', '&#96;')
                via = r['via'].replace('|', '&#124;').replace('`', '&#96;')
                if r['highlight']:
                    expr = '**`' + expr + '`**'
                else:
                    expr = '`' + expr + '`'
                rows.append(f'| `{state["name"]}` | `{state["cpp_class"]}` | `{hook}` | {expr} | `{via}` |')
    rows += ['', '## Interpretation', '',
             '- Sequence numbers preserve source order within each hook, expanding helpers at their call site and argument calls before the callee body.',
             '- Sibling argument expressions retain lexical order; C++ may evaluate them in a different order. Branches, loops, and callback timing are not inferred.',
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


def git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f'git {" ".join(args)} failed: {error}') from error
    if result.returncode != 0:
        raise ValueError(f'git {" ".join(args)} failed: {result.stderr.strip() or "no output"}')
    return result.stdout.strip()


def export_ref(package_root: Path, ref: str, destination: Path) -> tuple[Path, dict]:
    """Extract only the state-machine sources of @p ref; the checkout is untouched."""
    package = package_root.resolve()
    top = Path(git(package, 'rev-parse', '--show-toplevel')).resolve()
    prefix = package.relative_to(top)
    try:
        commit = git(top, 'rev-parse', '--verify', '--quiet', ref + '^{commit}')
    except ValueError:
        raise ValueError(f'Unknown git ref {ref!r}. For a remote branch, run `git fetch` first '
                         f'or use its full name (e.g. origin/{ref}).') from None
    paths = [(prefix / sub).as_posix() for sub in ('src/sm', 'include/agvhito/sm')]
    archive = subprocess.run(['git', '-C', str(top), 'archive', '--format=tar', commit, '--', *paths],
                             capture_output=True)
    if archive.returncode != 0:
        raise ValueError(f'{ref}: cannot read {", ".join(paths)}: '
                         + archive.stderr.decode(errors='replace').strip())
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(destination, filter='data')
        else:
            tar.extractall(destination)
    metadata = {'branch': ref, 'commit': commit,
                'commit_short': git(top, 'rev-parse', '--short=12', commit),
                'commit_date': git(top, 'show', '-s', '--format=%cI', commit),
                'sm_dirty': False, 'source_root': f'{top} @ {ref}'}
    return destination / prefix, metadata


def compare_refs(package_root: Path, base: str, feature: str | None, output_dir: Path, dpi=130,
                 renderer='auto', split=True, changes_only=False):
    """Generate base and feature maps, then the diff, under output_dir/{base,feature,diff}."""
    with tempfile.TemporaryDirectory(prefix='agvhito-diff-') as temp:
        base_root, base_meta = export_ref(package_root, base, Path(temp) / 'base')
        generate(base_root, output_dir / 'base', dpi, renderer, split, base_meta)
        if feature:
            feat_root, feat_meta = export_ref(package_root, feature, Path(temp) / 'feature')
        else:
            feat_root, feat_meta = package_root, None
        model, _, _ = generate(feat_root, output_dir / 'feature', dpi, renderer, split, feat_meta)
    feat_label = feature or model['metadata'].get('branch') or 'working tree'
    if not feature and model['metadata'].get('sm_dirty'):
        feat_label += ' (uncommitted)'
    if renderer == 'auto':
        renderer = 'graphviz' if shutil.which('dot') else 'matplotlib'
    return generate_diff(output_dir / 'base', output_dir / 'feature', output_dir / 'diff', dpi,
                            split, changes_only, renderer == 'none', base, feat_label,
                            'routing' if renderer == 'matplotlib' else 'graphviz')


def diff_arguments(parser):
    group = parser.add_argument_group('branch comparison')
    group.add_argument('--base', metavar='REF',
                       help='Original branch/commit (e.g. main). Enables diff mode; writes '
                            'OUT_DIR/base, OUT_DIR/feature and OUT_DIR/diff')
    group.add_argument('--feature', metavar='REF',
                       help='Feature branch/commit to compare; defaults to the current checkout, '
                            'including uncommitted changes')
    group.add_argument('--changes-only', action='store_true',
                       help='In the diff, hide unchanged action/route rows and unaffected states')


def main():
    parser, args = arguments(__doc__, extend=diff_arguments, epilog=EPILOG)
    if args.base is None and (args.feature or args.changes_only):
        parser.error('--feature and --changes-only need --base')
    try:
        if args.base is None:
            generate(args.package_root, args.out_dir, args.dpi, args.renderer, args.split)
        else:
            compare_refs(args.package_root, args.base, args.feature, args.out_dir, args.dpi,
                         args.renderer, args.split, args.changes_only)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
