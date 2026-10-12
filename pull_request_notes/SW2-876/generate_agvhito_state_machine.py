#!/usr/bin/env python3
"""Parse the AGVHITO checkout and render its registered state machine.

Python 3.10+ and matplotlib. Graphviz's optional `dot` executable provides a
connected graph layout; without it, a complete source-grouped routing diagram
is rendered. No fixed state names, transition counts, or route coordinates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_PACKAGE = Path('/home/jon-gonzales/volley/src/agvhito')
BG, INK, MUTED = '#F8FAFC', '#0F172A', '#475569'
BLUE, TEAL, ROSE, AMBER = '#2563EB', '#0F766E', '#BE123C', '#92400E'
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

    transitions = {}
    declaration = files['include/agvhito/sm/state_strings.hpp']
    code = mask_cpp(declaration)
    for m in re.finditer(r'\b(?:yasmin::)?Transitions\s+(k\w+)\s*(?:=\s*)?\{', code):
        start = code.index('{', m.start())
        end = closing(code, start)
        entries = []
        for entry in split_args(declaration[start + 1:end]):
            entry = mask_cpp(entry, strings=False).strip()
            if not entry:
                continue
            if not entry.startswith('{') or not entry.endswith('}'):
                raise ValueError(f'Unsupported transition entry in {m[1]}: {entry}')
            pair = split_args(entry[1:-1])
            if len(pair) != 2:
                raise ValueError(f'Expected outcome/destination pair in {m[1]}')
            entries.append({'outcome_constant': pair[0], 'destination_constant': pair[1],
                            'outcome': value(pair[0]), 'destination': value(pair[1])})
        if len({e['outcome'] for e in entries}) != len(entries):
            raise ValueError(f'Duplicate outcome in {m[1]}')
        transitions[m[1]] = entries

    root_text = files['src/sm/root.cpp']
    root_code = mask_cpp(root_text)
    states = []
    registrations = list(re.finditer(r'\badd_state\s*\(', root_code))
    for m in registrations:
        opening = root_code.index('(', m.start())
        end = closing(root_code, opening, '(', ')')
        args = split_args(root_text[opening + 1:end])
        if len(args) != 3:
            raise ValueError(f'Unsupported add_state registration: {root_text[m.start():end+1]}')
        cls = re.search(r'std::make_shared\s*<\s*([\w:]+)\s*>', args[1])
        if not cls or args[2] not in transitions:
            raise ValueError(f'Unsupported class/transition map in add_state({args[0]})')
        class_name = cls[1].split('::')[-1]
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
    import html
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
                    rows.append(f'<TR><TD ALIGN="LEFT"><FONT FACE="DejaVu Sans Mono" COLOR="{color_call}">{esc(record["expression"])}</FONT></TD></TR>')
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
    import textwrap
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
                    source_height += 22 * len(textwrap.wrap(r['expression'], 56)) + 18 * len(textwrap.wrap(r['via'], 68)) + 12
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
                    for line in textwrap.wrap(r['expression'], 56):
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


def arguments(description, default_dpi=130):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--package-root', type=Path, default=DEFAULT_PACKAGE,
                        help='AGVHITO package root; defaults to the local Volley checkout')
    parser.add_argument('--out-dir', type=Path, default=Path('diagrams'))
    parser.add_argument('--dpi', type=int, default=default_dpi)
    parser.add_argument('--renderer', choices=('auto', 'graphviz', 'matplotlib', 'none'), default='auto')
    parser.add_argument('--split', action=argparse.BooleanOptionalAction, default=True,
                        help='Separate failure and cancellation routes (default); --no-split shows all routes together')
    args = parser.parse_args()
    if args.dpi < 72:
        parser.error('--dpi must be at least 72')
    return parser, args


def generate(package_root: Path, output_dir: Path, dpi=130, renderer='auto', split=True):
    model = parse_package(package_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'agvhito-state-machine.json').write_text(json.dumps(serializable(model), indent=2) + '\n')
    used, views = render_views(model, output_dir, 'agvhito-state-machine', dpi, renderer, split=split)
    print(f'{len(model["states"])} states, {len(model["edges"])} routes; '
          f'views={ {k: v["route_count"] for k, v in views.items()} }; '
          f'renderer={used}; output={output_dir.resolve()}')
    return model


def main():
    parser, args = arguments(__doc__)
    try:
        generate(args.package_root, args.out_dir, args.dpi, args.renderer, args.split)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
