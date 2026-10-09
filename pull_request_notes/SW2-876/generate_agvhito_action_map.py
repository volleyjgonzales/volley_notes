#!/usr/bin/env python3
"""Render the action-annotated AGVHITO graph and its source call-site inventory.

Python 3.10+; dependency: matplotlib. No network access or document mutation.
Input: the supplied nine-state agvhito-repomix.md snapshot. This is a bounded
source audit, not a general C++ parser/call-graph engine. It recognizes state
hooks and VerifiedUnpause, checks all Make*Action call sites in each state file,
and rejects unaccounted sites instead of silently omitting them.
"""
from pathlib import Path
import argparse
import json
import math
import re
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon

CLASSES = {
    'booting': ('BootingState', 'booting_state'),
    'localizing': ('LocalizingState', 'localizing_state'),
    'stopped': ('StoppedState', 'stopped_state'),
    'idle': ('IdleState', 'idle_state'),
    'executing-order': ('ExecutingOrderState', 'executing_order_state'),
    'execution-paused': ('ExecutionPausedState', 'execution_paused_state'),
    'execution-recovery': ('ExecutionRecoveryState', 'execution_recovery_state'),
    'canceling-order': ('CancelingOrderState', 'canceling_order_state'),
    'error': ('ErrorState', 'error_state'),
}
MAPS = dict(zip(
    ['kBootingTransitions', 'kLocalizingTransitions', 'kStoppedTransitions',
     'kIdleTransitions', 'kExecutingOrderTransitions', 'kExecutionPausedTransitions',
     'kExecutionRecoveryTransitions', 'kCancelingOrderTransitions', 'kErrorTransitions'],
    CLASSES))
HIGHLIGHTS = {'MakeStartPauseAction', 'MakeStopPauseAction', 'MakeSoftEStopAction'}
BG, INK, MUTED, BORDER = '#F8FAFC', '#0F172A', '#475569', '#E2E8F0'
BLUE, TEAL, ROSE, AMBER = '#2563EB', '#0F766E', '#BE123C', '#92400E'


def packed_file(pack: str, path: str) -> str:
    match = re.search(r'^## File: ' + re.escape(path) +
                      r'\n```[^\n]*\n(.*?)\n```', pack, re.M | re.S)
    if not match:
        raise ValueError(f'Missing packed source: {path}')
    return match.group(1)


def without_comments(text: str) -> str:
    # Preserve string/character literals and offsets. The snapshot has no raw
    # string literal in these state implementations; do not claim a full lexer.
    token = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/', re.S)
    return token.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0])
                     if m[0].startswith(('//', '/*')) else m[0], text)


def matching(text: str, start: int, opening: str, closing: str) -> int:
    depth, quote, escaped = 0, None, False
    for i in range(start, len(text)):
        c = text[i]
        if quote:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == quote:
                quote = None
            continue
        if c in ('"', "'"):
            quote = c
        elif c == opening:
            depth += 1
        elif c == closing:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f'Unbalanced {opening}{closing} at offset {start}')


def calls(body: str) -> list[dict]:
    found = []
    for match in re.finditer(r'\b(Make[A-Za-z0-9_]*Action)\s*\(', body):
        start = body.index('(', match.start())
        end = matching(body, start, '(', ')')
        args = re.sub(r'\s+', ' ', body[start + 1:end]).strip()
        found.append({'factory': match[1], 'arguments': args,
                      'expression': match[1] + '(' + args + ')',
                      'highlight': match[1] in HIGHLIGHTS})
    return found


def audit(pack: str) -> tuple[list, list]:
    records = []
    for state, (cls, file) in CLASSES.items():
        path = f'src/sm/{file}.cpp'
        code = without_comments(packed_file(pack, path))
        count = 0
        for m in re.finditer(re.escape(cls) + r'::(Execute|OnEntry|Step|OnExit|VerifiedUnpause)\s*\(', code):
            param_start = code.index('(', m.start())
            param_end = matching(code, param_start, '(', ')')
            body_start = code.index('{', param_end)
            body_end = matching(code, body_start, '{', '}')
            for index, call in enumerate(calls(code[body_start:body_end + 1])):
                records.append(dict(call, state=state, cpp_class=cls,
                                    method=m[1], index=index, source=path,
                                    lifecycle_hook='OnEntry -> VerifiedUnpause' if m[1] == 'VerifiedUnpause' else m[1]))
                count += 1
        if count != len(calls(code)):
            raise ValueError(f'Unaccounted action factory call in {path}; extend the audit first.')
    decl = packed_file(pack, 'include/agvhito/sm/state_strings.hpp')
    values = dict(re.findall(r'inline constexpr auto (k\w+) \{"([^"]+)"\}', decl))
    values['yasminx::kOutcomeCanceled'] = 'canceled'
    edges = []
    for name, body in re.findall(r'inline const yasmin::Transitions (k\w+) \{(.*?)\n\};', decl, re.S):
        for outcome, dest in re.findall(r'\{([^,]+),\s*([^}]+)\}', body):
            edges.append((MAPS[name], values[outcome.strip()], values[dest.strip()]))
    if len(edges) != 36 or len(records) != 23 or sum(r['highlight'] for r in records) != 11:
        raise ValueError('Snapshot differs from the reviewed 36-edge / 23-call / 11-highlight inventory.')
    helper_source = packed_file(pack, 'src/sm/executing_order_state.cpp')
    if 'VerifiedUnpause(*blackboard)' not in helper_source:
        raise ValueError('Expected OnEntry -> VerifiedUnpause call must be re-reviewed.')
    return records, edges


def condition(record: dict) -> str:
    state, factory, args = record['state'], record['factory'], record['arguments']
    if state == 'booting':
        if factory in HIGHLIGHTS or factory in {'MakeCancelOrderAction', 'MakeExceptionClearAction'}:
            return 'Boot preparation batch; verified together'
        if factory == 'MakeDownloadMapAction':
            return 'If localization map is missing' if 'localization' in args else 'For each missing floor map'
        return 'Enable localization map' if factory == 'MakeEnableMapAction' else 'For each reported map outside the expected set'
    if state == 'idle':
        if factory in {'MakeSoftEStopAction', 'MakeExceptionClearAction'}:
            return 'Only when the entry snapshot reports software E-stop'
        return 'Always after entry checks' if factory == 'MakeStartPauseAction' else 'If entry snapshot reports incomplete traversal'
    if state == 'executing-order':
        return 'New-order path: only if robot is paused; verified batch' if record['method'] == 'VerifiedUnpause' else 'New-order path: only if enabled map differs / is absent'
    if state == 'execution-recovery':
        return 'Verification failure is logged and tolerated'
    if state == 'error':
        return 'Software-stop verification failure is logged and tolerated'
    if state == 'execution-paused':
        return 'Explicit pause entry' if record['method'] == 'OnEntry' else 'Exit after Resume; current hook ignores step_outcome'
    if state == 'canceling-order':
        return 'Entry always sends cancel, even without local active-order tracking'
    if state == 'localizing':
        return 'Enable the configured localization map on entry'
    return 'Activate software E-stop on entry; failure propagates'


def node_rows(state: str, records: list) -> list:
    owned = [r for r in records if r['state'] == state]
    rows = []
    if state == 'booting':
        rows.append(('hook', 'Execute', None))
        rows += [('call', r['expression'], r) for r in owned]
        rows.append(('note', 'Two verified batches; no settling guard in this snapshot.', None))
    else:
        rows.append(('hook', 'OnEntry', None))
        if state == 'executing-order':
            rows.append(('note', 'Resume / recovery re-entry skips new-order dispatch.', None))
            rows.append(('helper', 'if paused -> VerifiedUnpause', None))
            rows += [('call', r['expression'], r) for r in owned if r['method'] == 'VerifiedUnpause']
        rows += [('call', r['expression'], r) for r in owned if r['method'] == 'OnEntry']
        if state == 'executing-order':
            rows.append(('order', 'VerifiedPublish(new_order)', None))
            rows.append(('note', 'Publishes an already assembled order; not an action factory.', None))
        step_calls = [r for r in owned if r['method'] == 'Step']
        rows.append(('hook' if step_calls else 'note', 'Step' if step_calls else 'Step: no Make*Action call sites', None))
        rows += [('call', r['expression'], r) for r in step_calls]
        exit_calls = [r for r in owned if r['method'] == 'OnExit']
        rows.append(('hook' if exit_calls else 'note', 'OnExit' if exit_calls else 'OnExit: inherited; no factory calls in this class', None))
        rows += [('call', r['expression'], r) for r in exit_calls]
    return rows


def expression_lines(expression: str) -> list[str]:
    if len(expression) <= 55:
        return [expression]
    factory, args = expression.split('(', 1)
    return [factory + '('] + ['  ' + line for line in textwrap.wrap(args, width=56)]


def row_height(row: tuple) -> int:
    return len(expression_lines(row[1])) * 28 + 24 if row[0] == 'call' else 34


def generate(repo_path: Path, output_dir: Path, dpi: int = 130) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = repo_path.read_text(encoding='utf-8')
    records, expected = audit(pack)
    W, H = 3500, 5260
    plt.rcParams.update({'font.family': 'Nimbus Sans', 'svg.fonttype': 'path'})
    fig = plt.figure(figsize=(35, 52.6), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
    def txt(x, y, text, size=16, color=INK, weight='normal', ha='left', mono=False, **kwargs):
        return ax.text(x, y, text, fontsize=size, color=color, fontweight=weight,
                       ha=ha, va='center', fontfamily='Nimbus Mono PS' if mono else 'Nimbus Sans', zorder=8, **kwargs)
    def rect(x, y, w, h, fill='white', stroke=BORDER, radius=18, z=2, lw=1.5):
        p = FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={radius}',
                          facecolor=fill, edgecolor=stroke, lw=lw, zorder=z) if radius else Rectangle((x, y), w, h, facecolor=fill, edgecolor=stroke, lw=lw, zorder=z)
        ax.add_patch(p)
        return p
    def panel(x, y, w, h):
        rect(x, y + 5, w, h, '#E8EDF3', '#E8EDF3', 24, 0)
        rect(x, y, w, h, radius=24, z=1)
    def action_node(state, x, y):
        rows = node_rows(state, records)
        height = 110 + sum(row_height(r) for r in rows) + 20
        ordinary = state == 'booting'; color = BLUE if ordinary else TEAL
        rect(x, y, 680, height, stroke=color, radius=0 if ordinary else 18, z=4, lw=2)
        txt(x + 28, y + 32, state, 19, weight='bold', mono=True)
        txt(x + 28, y + 68, CLASSES[state][0], 16, MUTED)
        txt(x + 650, y + 69, 'State' if ordinary else 'LifecycleState', 11, color, ha='right')
        ax.plot([x + 25, x + 655], [y + 92, y + 92], color=BORDER, lw=1.5, zorder=5)
        cursor = y + 106
        for kind, text, record in rows:
            height_row = row_height((kind, text, record))
            if kind == 'call':
                lines = expression_lines(text)
                if record['highlight']:
                    rect(x + 18, cursor, 644, 28 * len(lines) + 4, '#FFFBEB', '#FDE68A', 7, 5, 1)
                for i, line in enumerate(lines):
                    txt(x + 30, cursor + 15 + i * 28, line, 12, AMBER if record['highlight'] else INK,
                        'bold' if record['highlight'] else 'normal', mono=True)
                note = condition(record)
                txt(x + 31, cursor + 28 * len(lines) + 17, note, 10, MUTED)
            else:
                txt(x + 29, cursor + 17, text, 12 if kind != 'hook' else 14,
                    TEAL if kind in ('hook', 'helper', 'order') else MUTED,
                    'bold' if kind == 'hook' else 'normal', mono=kind in ('helper', 'order'))
            cursor += height_row
        return (x, y, 680, height)
    drawn = []
    def edge(a, label, b, points, labelpos, color=BLUE, size=13):
        key = (a, label, b)
        if key not in expected or key in drawn:
            raise ValueError(f'Unexpected / repeated edge: {key}')
        drawn.append(key)
        line, = ax.plot(*zip(*points), color=color, lw=2.5, zorder=3, solid_capstyle='round', solid_joinstyle='round')
        line.set_gid('edge-' + '-'.join(key))
        px, py = points[-2]; x, y = points[-1]; dx, dy = x - px, y - py
        norm = math.hypot(dx, dy)
        if norm < 22:
            raise ValueError(f'Arrow segment too short: {key}')
        ux, uy = dx / norm, dy / norm
        head = Polygon([(x, y), (x - 19*ux + 8*uy, y - 19*uy - 8*ux),
                        (x - 19*ux - 8*uy, y - 19*uy + 8*ux)], facecolor=color, edgecolor=color, zorder=10)
        head.set_gid('arrowhead-' + '-'.join(key)); ax.add_patch(head)
        txt(*labelpos, label, size, color, ha='center', mono=True,
            bbox=dict(facecolor='white', edgecolor='none', pad=3))
    txt(70,60,'SW2-876  /  ACTION CALL-SITE AUDIT',13,BLUE,'bold')
    txt(70,120,'AGVHITO state machine + action calls',37,weight='bold')
    txt(70,174,'Execute / OnEntry / Step / OnExit, including the VerifiedUnpause helper path.',18,MUTED)
    rect(70,203,780,52,'#FFFBEB','#FDE68A',10)
    txt(92,229,'AMBER  MakeStartPauseAction / MakeStopPauseAction / MakeSoftEStopAction',13,AMBER,'bold')
    txt(3430,229,'23 call sites  /  11 highlighted  /  36 routes',15,MUTED,ha='right',mono=True)
    panel(50,290,3400,3330)
    txt(90,342,'01   State hooks and control flow',25,weight='bold')
    txt(90,387,'Current source behavior. Action-factory calls create commands; VerifiedPublish sends and verifies them.',15,MUTED)
    positions={'booting':(200,460),'localizing':(200,1360),'stopped':(200,1730),'idle':(200,2260),
               'executing-order':(1450,2260),'execution-paused':(2600,1360),
               'execution-recovery':(2600,2900),'canceling-order':(1450,3300),'error':(1450,460)}
    boxes = {s: action_node(s,*p) for s,p in positions.items()}
    def port(s,side,f=.5):
        x,y,w,h=boxes[s]
        return {'left':(x-3,y+h*f),'right':(x+w+3,y+h*f),
                'top':(x+w*f,y-3),'bottom':(x+w*f,y+h+3)}[side]
    def vertical(a,label,b):
        p,q=port(a,'bottom'),port(b,'top')
        edge(a,label,b,[p,q],(p[0],(p[1]+q[1])/2))
    vertical('booting','booted','localizing')
    vertical('localizing','localized','stopped')
    vertical('stopped','activate-requested','idle')
    p,q=port('stopped','left',.2),port('localizing','left',.2)
    edge('stopped','not-localized','localizing',[p,(110,p[1]),(110,q[1]),q],(115,(p[1]+q[1])/2),size=10)
    p,q=port('idle','left',.2),port('stopped','left',.75)
    edge('idle','controlled-stop-requested','stopped',[p,(105,p[1]),(105,q[1]),q],(260,(p[1]+q[1])/2),size=12)
    p,q=port('idle','right',.15),port('executing-order','left',.15)
    edge('idle','order-requested','executing-order',[p,(1340,p[1]),(1340,q[1]),q],(1165,p[1]),size=13)
    p,q=port('executing-order','left',.8),port('idle','right',.8)
    edge('executing-order','order-complete','idle',[p,(1360,p[1]),(1360,3120),(970,3120),(970,q[1]),q],(1165,3120))
    p,q=port('executing-order','top',.25),port('executing-order','top',.7)
    edge('executing-order','order-requested','executing-order',[p,(p[0],2110),(q[0],2110),q],(1770,2080))
    txt(1770,2138,'next queued order',11,MUTED,ha='center')
    p,q=port('executing-order','right',.12),port('execution-paused','left',.25)
    edge('executing-order','pause-requested','execution-paused',[p,(2390,p[1]),(2390,q[1]),q],(2390,1860))
    p,q=port('execution-paused','left',.75),port('executing-order','top',.88)
    edge('execution-paused','resumed','executing-order',[p,(2260,p[1]),(2260,2190),(q[0],2190),q],(2260,1940))
    p,q=port('executing-order','right',.78),port('execution-recovery','left',.2)
    edge('executing-order','order-data-stale','execution-recovery',[p,(2480,p[1]),(2480,q[1]),q],(2480,(p[1]+q[1])/2))
    p,q=port('execution-recovery','bottom'),port('executing-order','bottom',.88)
    edge('execution-recovery','recovered','executing-order',[p,(p[0],3510),(2290,3510),(2290,3020),(q[0],3020),q],(2650,3510))
    p,q=port('executing-order','bottom',.45),port('canceling-order','top',.45)
    edge('executing-order','controlled-stop-requested','canceling-order',[p,q],(p[0],(p[1]+q[1])/2))
    p,q=port('canceling-order','left',.5),port('stopped','right',.8)
    edge('canceling-order','canceled-order','stopped',[p,(1210,p[1]),(1210,q[1]),q],(1210,3270))
    p,q=port('error','left',.25),port('stopped','right',.2)
    edge('error','recovered','stopped',[p,(1170,p[1]),(1170,q[1]),q],(1170,1350))
    txt(2940,1930,'No state Step contains a Make*Action call site.',14,TEAL,'bold',ha='center')
    txt(2940,1970,'Step may still process orders, requests, or callbacks.',13,MUTED,ha='center')
    txt(2940,2010,'Factories inside VerifiedUnpause are attributed to OnEntry.',13,MUTED,ha='center')
    txt(90,3570,'Conditions and batch notes are source-audited. Vector order is not a firmware execution-order guarantee.',14,MUTED)
    for px,target,title,count,color in [(50,'error','Failure routes',12,ROSE),(1780,'terminal','Cancellation routes',9,MUTED)]:
        panel(px,3670,1670,1000)
        txt(px+40,3725,('02   ' if target=='error' else '03   ')+title,23,weight='bold')
        txt(px+1620,3725,str(count)+' OUTCOME ROUTES',12,MUTED,'bold','right')
        subset=[e for e in expected if e[2]==target]
        sources=[s for s in CLASSES if any(e[0]==s for e in subset)]
        tx=px+1390
        rect(tx,3780,240,810,'#FFF1F2' if target=='error' else '#F1F5F9',color,15,z=4,lw=2)
        txt(tx+120,3810,target,16,color,'bold','center',mono=True)
        txt(tx+120,3840,'ErrorState' if target=='error' else 'root outcome',12,MUTED,ha='center')
        y=3790
        for state in sources:
            labels=[o for a,o,b in subset if a==state]
            height=112 if len(labels)==3 else 62
            rect(px+40,y,590,height,stroke=BLUE if state=='booting' else TEAL,radius=0 if state=='booting' else 12,z=4)
            txt(px+65,y+height/2,state,13,weight='bold',mono=True)
            ports=[y+height/2] if len(labels)==1 else [y+22,y+56,y+90]
            for label,py in zip(labels,ports):
                edge(state,label,target,[(px+633,py),(tx-3,py)],(px+1000,py),color,size=12)
            y+=height+24
        txt(px+40,4630,'Repeated cards are the same states; all failure/cancellation outcomes remain included.',12,MUTED)
    panel(50,4720,3400,360)
    txt(90,4770,'04   Related publishers outside the registered state hooks',22,weight='bold')
    outside=[('Agv constructor','MakeStateRequestAction()','Initial telemetry request; fire-and-forget.'),
             ('Agv::RequestSoftEStop','MakeSoftEStopAction(true)','Explicit severe stop; ignored while Booting / Localizing.'),
             ('Agv::Step','MakeSoftEStopAction(true)','Terminal/PostStep failure; best-effort publication.'),
             ('InstanceManager::RequestFactsheet','MakeFactsheetRequestAction()','Discovery / factsheet request; not a state action.')]
    manager=packed_file(pack,'src/instance_manager.cpp')
    if 'MakeFactsheetRequestAction()' not in manager:
        raise ValueError('Missing expected discovery factsheet action.')
    for i,(caller,expr,note) in enumerate(outside):
        y=4820+i*55
        txt(95,y,caller,14,weight='bold',mono=True)
        if 'MakeSoftEStopAction' in expr:
            rect(960,y-20,560,40,'#FFFBEB','#FDE68A',8,z=5)
        txt(980,y,expr,14,AMBER if 'MakeSoftEStopAction' in expr else INK,mono=True)
        txt(1630,y,note,14,MUTED)
    txt(70,5140,'Instant-action factories: 23 state call sites / 11 highlighted. Step has 0 direct sites in the nine state classes.',14,weight='bold')
    txt(70,5180,'Order payloads may already contain actions (e.g. lift) assembled elsewhere; publishing an order does not call their factories here.',13,MUTED)
    txt(70,5218,'SW2-876 proposal is not applied. No action is implied by Continue{}, a graph edge, or the adapter state name alone.',13,MUTED)
    if set(drawn)!=set(expected) or len(drawn)!=36:
        raise ValueError('Rendered transitions do not exactly match the source map.')
    png,svg=output_dir/'agvhito-state-machine-actions.png',output_dir/'agvhito-state-machine-actions.svg'
    fig.savefig(png,dpi=dpi,facecolor=BG)
    fig.savefig(svg,facecolor=BG)
    plt.close(fig)
    if svg.read_text().count('id="arrowhead-')!=36:
        raise ValueError('Expected 36 explicit SVG arrowhead groups.')
    for record in records:
        record['condition']=condition(record)
    (output_dir/'agvhito-action-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
    rows=['# AGVHITO action map and diagram generators','',
          'This companion describes current source behavior, not the proposed SW2-876 changes.',
          '', '![State machine with hook-level action calls](agvhito-state-machine-actions.png)', '',
          'Amber highlights `MakeStartPauseAction`, `MakeStopPauseAction`, and `MakeSoftEStopAction`. '
          '`true` activates software E-stop; `false` releases it. '
          'All 36 mapped outcome routes are retained; all 23 state call sites are listed below.', '',
          '## Action call-site inventory', '',
          '| State | Hook / helper | Exact factory expression | Guard / timing context |',
          '| --- | --- | --- | --- |']
    for r in records:
        expr='**`'+r['expression']+'`**' if r['highlight'] else '`'+r['expression']+'`'
        rows.append(f"| `{r['state']}` | `{r['lifecycle_hook']}` | {expr} | {r['condition']} |")
    rows+=['', '## Interpretation', '',
           '- `Make*Action` constructs a protocol action; `VerifiedPublish` publishes and verifies it.',
           '- `ExecutingOrderState::OnEntry` reaches `MakeStopPauseAction` and exception-clear indirectly through its private `VerifiedUnpause` helper, before enabling a map / publishing a new order. Resume/recovery re-entry skips this new-order path.',
           '- None of the eight lifecycle Step implementations directly calls an instant-action factory. This does not mean Step has no side effects: it can mutate tracking, consume requests, and invoke callbacks.',
           '- `VerifiedPublish(new_order)` publishes an already assembled order. Embedded actions, such as `MakeLiftAction` in `OrderAssembler`, are assembled elsewhere and are not factory calls inside this state hook.',
           '- Recovery logs/tolerates pause/unpause verification failures; Error logs/tolerates its software-stop verification failure. Other listed verification failures propagate through the existing outcomes.',
           '- Related publishers outside the graph include the initial state request, explicit severe-stop service, terminal/PostStep E-stop, and InstanceManager factsheet discovery request.',
           '- Calls are grouped by hook, not by a promised firmware execution schedule. Multiple actions in a verified batch can have nonblocking protocol semantics.',
           '', '## Regenerate both diagrams', '',
           'Use Python 3.10+ with `matplotlib` installed. The scripts do not install packages or access the network. The ZIP includes the exact input snapshot as `agvhito-repomix.md`.', '',
           '```bash',
           'python3 generate_agvhito_state_machine.py --repo agvhito-repomix.md --out-dir diagrams',
           'python3 generate_agvhito_action_map.py --repo agvhito-repomix.md --out-dir diagrams',
           '```', '',
           '`generate_agvhito_state_machine.py` reproduces the previously delivered styled state diagram. '
           '`generate_agvhito_action_map.py` generates the extended image, SVG, JSON audit inventory, and this companion. '
           'Both accept `--dpi`, and export SVG text as paths to avoid font-installation differences in viewers. '
           'The preferred fonts are Nimbus Sans / Nimbus Mono PS; Matplotlib uses its available fallback if they are absent.', '',
           'The layout and guard annotations target this reviewed nine-state snapshot. The audit is a bounded lexical scan, not a C++ compiler, AST parser, or runtime command recorder. '
           'It validates 36 mapped routes, 23 action factory sites, and 11 highlighted sites and rejects unexpected changes. '
           'When a patch changes the graph, hook calls, helper structure, or guards, update the layout/annotations and review the source before changing these checks. '
           'Future action calls are not silently dropped.', '',
           '## Source anchors', '',
           '- `include/agvhito/sm/state_strings.hpp` and `src/sm/root.cpp`: names, routing and registration.',
           '- `src/sm/*_state.cpp`: all nine state bodies and the private unpause helper.',
           '- `include/agvhito/topics/instant_actions.hpp`: factory parameters and protocol action types.',
           '- `src/agv.cpp`, `src/instance_manager.cpp`: publishers outside the state hooks.',
           '- `src/order_assembler.cpp`: order payload assembly, including lift actions.', '']
    (output_dir/'agvhito-action-map.md').write_text('\n'.join(rows),encoding='utf-8')
    print('Validated 23 state factory call sites, 11 highlighted sites, and 36 rendered transitions.')
    print('Node heights:', {s:box[3] for s,box in boxes.items()})


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).with_name('agvhito-repomix.md'))
    parser.add_argument('--out-dir',type=Path,default=Path('diagrams'))
    parser.add_argument('--dpi',type=int,default=130)
    args=parser.parse_args()
    if not args.repo.is_file():
        parser.error(f'Repomix input does not exist: {args.repo}')
    if args.dpi<72:
        parser.error('--dpi must be at least 72')
    generate(args.repo,args.out_dir,args.dpi)


if __name__=='__main__':
    main()
