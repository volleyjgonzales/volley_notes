from pathlib import Path
import textwrap
import math
import yaml
import sys
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from matplotlib.lines import Line2D

ROOT = Path('/mnt/data/scheduler_core_refactor')
FIG = ROOT/'figures'
SRC = ROOT/'sources'/'5675_pecos_combined.yaml'

sys.path.insert(0, str(ROOT/'scripts'))
from figstyle import plt, BG, CARD, FG, MUTED, BORDER, SKY, GREEN, AMBER, RED, VIOLET, MONO
from draw import canvas, uml_class, uml_rel, label, agv


def save(fig, name):
    fig.savefig(FIG/name, facecolor=BG, bbox_inches='tight', pad_inches=0.08, metadata={'Date':None})
    plt.close(fig)


def legend_box(ax, x, y, w, h, title, entries):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.03,rounding_size=0.12',
                                facecolor='#121b2d', edgecolor=BORDER, lw=1.2, zorder=20))
    ax.text(x+0.12, y+h-0.12, title, ha='left', va='top', fontsize=8.8, color=FG,
            family=MONO, fontweight='bold', zorder=21)
    yy = y+h-0.38
    for kind, color, text in entries:
        if kind == 'box':
            ax.add_patch(Rectangle((x+0.12, yy-0.12), 0.22, 0.15, facecolor=CARD, edgecolor=color, lw=1.4, zorder=21))
        elif kind == 'line':
            ax.plot([x+0.10, x+0.34], [yy-0.04, yy-0.04], color=color, lw=2.0, zorder=21)
        elif kind == 'arrow':
            ax.annotate('', xy=(x+0.34, yy-0.04), xytext=(x+0.10, yy-0.04),
                        arrowprops=dict(arrowstyle='-|>', color=color, lw=1.8), zorder=21)
        elif kind == 'diamond':
            pts = [(x+0.09, yy-0.04), (x+0.15, yy+0.02), (x+0.21, yy-0.04), (x+0.15, yy-0.10)]
            ax.add_patch(plt.Polygon(pts, closed=True, facecolor=color, edgecolor=color, lw=1.2, zorder=21))
            ax.plot([x+0.21, x+0.34], [yy-0.04, yy-0.04], color=color, lw=1.6, zorder=21)
        elif kind == 'triangle':
            pts = [(x+0.34, yy-0.04), (x+0.23, yy+0.03), (x+0.23, yy-0.11)]
            ax.add_patch(plt.Polygon(pts, closed=True, facecolor=BG, edgecolor=color, lw=1.2, zorder=21))
            ax.plot([x+0.10, x+0.23], [yy-0.04, yy-0.04], color=color, lw=1.6, zorder=21)
        ax.text(x+0.42, yy-0.04, text, ha='left', va='center', fontsize=7.9, color=MUTED,
                family=MONO, zorder=21)
        yy -= 0.28


def wrap_lines(lines, width=42):
    out = []
    for line in lines:
        if len(line) <= width:
            out.append(line)
        else:
            out.extend(textwrap.wrap(line, width=width, break_long_words=False, break_on_hyphens=False))
    return out


def fig_event_hierarchy():
    fig, ax = canvas(14.5, 8.6, equal=False)
    # base class top center
    base = uml_class(ax, 4.95, 8.10, 'ScheduleEvent',
                     attrs=['# type_: ScheduleEventType', '- job_idx_: size_t'],
                     methods=['+ Apply(state) const = 0', '+ GetGarageEntityId() const = 0', '+ GetType() const'],
                     color=SKY, stereo='abstract base class', w=4.6, fs=8.0, name_fs=9.6)
    # children row 1
    tray = uml_class(ax, 0.35, 5.50, 'TrayMove',
                     attrs=['- tray_id_: optional<uint16_t>', '- dest_: optional<GaragePoseMsg>', '- agv_id_: optional<uint16_t>'],
                     methods=['+ Assigned() const', '+ SetTrayId(id)', '+ SetDest(dest)', '+ SetAgvId(id)'],
                     color=GREEN, w=4.1, fs=7.4, name_fs=9.0)
    agv = uml_class(ax, 5.10, 5.50, 'AgvMove',
                    attrs=['- discrete_change_: variant<AgvLiftChangedMsg, AgvPoseChangedMsg>'],
                    methods=['+ GetAgvId() const', '+ GetSrc() const', '+ GetDest() const', '+ Apply(state) const'],
                    color=GREEN, w=4.3, fs=7.2, name_fs=9.0)
    bay = uml_class(ax, 10.15, 5.50, 'BayTransition',
                    attrs=['- bay_state_change_: DiscreteBayStateChangedMsg', '- command_: BayCommandMsg'],
                    methods=['+ GetBayId() const', '+ GetCommand() const', '+ Apply(state) const'],
                    color=VIOLET, w=4.1, fs=7.1, name_fs=9.0)
    vecs = uml_class(ax, 2.70, 2.45, 'VecsTransition',
                     attrs=['- state_change_: DiscreteVecsStateChangedMsg'],
                     methods=['+ GetVecsId() const', '+ Apply(state) const'],
                     color=VIOLET, w=4.1, fs=7.1, name_fs=9.0)
    vrc = uml_class(ax, 7.90, 2.45, 'VrcTransition',
                    attrs=['- state_change_: DiscreteVrcStateChangedMsg', '- from_vrc_node_id_: uint32_t', '- to_vrc_node_id_: uint32_t'],
                    methods=['+ GetRequestedFloor() const', '+ Apply(state) const'],
                    color=VIOLET, w=4.2, fs=7.0, name_fs=9.0)
    # inheritance relationships
    uml_rel(ax, [tray.top(0.5), (tray.cx, 6.20), (base.cx-3.20, 6.20), base.bot(0.14)], kind='inh', color=SKY)
    uml_rel(ax, [agv.top(0.5), (agv.cx, 6.20), base.bot(0.50)], kind='inh', color=SKY)
    uml_rel(ax, [bay.top(0.5), (bay.cx, 6.20), (base.cx+3.20, 6.20), base.bot(0.86)], kind='inh', color=SKY)
    uml_rel(ax, [vecs.top(0.5), (vecs.cx, 3.30), (base.cx-1.20, 3.30), (base.cx-1.20, 6.20), base.bot(0.34)], kind='inh', color=SKY)
    uml_rel(ax, [vrc.top(0.5), (vrc.cx, 3.30), (base.cx+1.20, 3.30), (base.cx+1.20, 6.20), base.bot(0.66)], kind='inh', color=SKY)
    # classification chips
    for x, y, txt, col in [
        (2.35, 0.82, 'assignment-oriented events', GREEN),
        (10.75, 0.82, 'resource-state transitions', VIOLET),
    ]:
        ax.text(x, y, txt, ha='center', va='center', fontsize=8.4, color=col, family=MONO,
                bbox=dict(boxstyle='round,pad=0.22', facecolor=BG, edgecolor=col, lw=1.0), zorder=15)
    legend_box(ax, 10.8, 0.95, 3.35, 1.95, 'legend', [
        ('triangle', SKY, 'public inheritance (is-a)'),
        ('box', SKY, 'abstract base class'),
        ('box', GREEN, 'movement / assignment event'),
        ('box', VIOLET, 'other resource transition')
    ])
    ax.text(7.25, 8.52, 'Existing event hierarchy', ha='center', va='bottom', fontsize=13.2,
            color=FG, family=MONO, fontweight='bold')
    ax.text(7.25, 8.24,
            'Every concrete subclass overrides Apply(...) so the event can mutate a DiscreteGarageState during replay.',
            ha='center', va='top', fontsize=8.6, color=MUTED)
    save(fig, '12_uml_event_hierarchy.svg')


def fig_ros_messages():
    fig, ax = canvas(17.0, 10.2, equal=False)
    # service frame
    ax.add_patch(FancyBboxPatch((0.25, 0.25), 16.5, 9.55, boxstyle='round,pad=0.03,rounding_size=0.18',
                                facecolor='none', edgecolor=BORDER, lw=1.2, linestyle='--', zorder=1))
    ax.text(0.42, 9.62, 'srv/Plan.srv', ha='left', va='top', fontsize=10.2, color=FG, family=MONO, fontweight='bold')
    ax.text(0.42, 9.34, 'The ROS service is composed of a request message and a response message.', ha='left', va='top',
            fontsize=8.2, color=MUTED)

    req = uml_class(ax, 0.50, 8.75, 'PlanRequest',
                    attrs=wrap_lines([
                        '+ id: Guid', '+ base_state: DiscreteGarageState', '+ base_schedule: Schedule',
                        '+ planned_jobs: SchedulerJob[]', '+ active_jobs: SchedulerJob[]', '+ pending_jobs: SchedulerJob[]'
                    ], 34), color=SKY, stereo='ROS message', w=4.25, fs=7.1, name_fs=9.4)
    state = uml_class(ax, 0.40, 5.55, 'DiscreteGarageState',
                      attrs=wrap_lines([
                          '+ header: std_msgs/Header', '+ is_faulted: bool', '+ agvs: DiscreteAgvState[]',
                          '+ bays: DiscreteBayState[]', '+ vexen: DiscreteVecsState[]', '+ trays: DiscreteTrayState[]',
                          '+ payloads: DiscretePayloadState[]', '+ vrcs: DiscreteVrcState[]',
                          '+ disabled_nodes: uint32[]', '+ hash: uint64'
                      ], 36), color=VIOLET, stereo='ROS message', w=4.45, fs=6.9, name_fs=9.0)
    agv_state = uml_class(ax, 0.35, 2.42, 'DiscreteAgvState',
                          attrs=wrap_lines([
                              '+ id: uint16', '+ state: uint8', '+ pose: GaragePose', '+ lift: bool',
                              '+ tray_id: uint16', '+ disabled: bool'
                          ], 32), color=VIOLET, stereo='ROS message', w=3.6, fs=6.8, name_fs=8.6)
    tray_state = uml_class(ax, 4.25, 2.42, 'DiscreteTrayState',
                           attrs=wrap_lines([
                               '+ id: uint16', '+ pose: GaragePose', '+ agv_id: uint16',
                               '+ payload_id: Guid', '+ disabled: bool'
                           ], 32), color=VIOLET, stereo='ROS message', w=3.55, fs=6.8, name_fs=8.6)
    pose = uml_class(ax, 3.00, 0.95, 'GaragePose',
                     attrs=['+ node_id: uint32', '+ heading: int16'],
                     color='#6EE7B7', stereo='ROS message', w=2.7, fs=6.8, name_fs=8.6)
    job = uml_class(ax, 5.45, 8.75, 'SchedulerJob',
                    attrs=wrap_lines([
                        '+ type, type_name', '+ state, state_name', '+ guid: Guid', '+ note: string',
                        '+ agv_id / bay_id / tray_id', '+ payload_id: Guid', '+ destination: GaragePose',
                        '+ allow_reciprocal: bool', '+ seconds_to_bay_arrival: float32',
                        '+ retain_job / needs_bay_in_retrieve: bool'
                    ], 34), color=SKY, stereo='ROS message', w=4.55, fs=6.8, name_fs=9.0)

    resp = uml_class(ax, 10.00, 8.75, 'PlanResponse',
                     attrs=wrap_lines([
                         '+ success: bool', '+ message: string', '+ id: Guid',
                         '+ schedule: Schedule', '+ scheduled_jobs: ScheduledJobData[]'
                     ], 32), color=GREEN, stereo='ROS message', w=3.75, fs=7.0, name_fs=9.4)
    sched = uml_class(ax, 10.10, 5.90, 'Schedule',
                      attrs=['+ header: std_msgs/Header', '+ nodes: ActionNode[]'],
                      color=GREEN, stereo='ROS message', w=3.10, fs=7.0, name_fs=8.8)
    action = uml_class(ax, 8.25, 2.62, 'ActionNode',
                       attrs=wrap_lines([
                           '+ guid: Guid', '+ job_id: Guid', '+ type: uint8', '+ parents: uint32[]',
                           '+ duration: float32', '+ status: uint8', '+ outside_split: bool',
                           '+ agv_id: uint32, agv_command: AgvCommand', '+ bay_id: uint32, bay_command: BayCommand',
                           '+ vecs_id: uint32, vecs_command: VecsCommand', '+ vrc_id: uint32, vrc_command: VrcCommand'
                       ], 44), color=GREEN, stereo='ROS message', w=5.2, fs=6.7, name_fs=9.0)
    agv_cmd = uml_class(ax, 13.90, 2.82, 'AgvCommand',
                        attrs=['+ id: string', '+ src: AgvGoal', '+ dst: AgvGoal'],
                        color=AMBER, stereo='ROS message', w=2.9, fs=6.9, name_fs=8.8)
    agv_goal = uml_class(ax, 13.70, 0.95, 'AgvGoal',
                         attrs=['+ pose: GaragePose', '+ lift: bool'],
                         color=AMBER, stereo='ROS message', w=2.6, fs=6.8, name_fs=8.6)
    bay_cmd = uml_class(ax, 13.25, 5.90, 'BayCommand',
                        attrs=['+ command_type: uint8', '+ command_id: string', '+ floor: uint8'],
                        color=AMBER, stereo='ROS message', w=3.05, fs=6.8, name_fs=8.8)
    vecs_cmd = uml_class(ax, 14.95, 5.90, 'VecsCommand',
                         attrs=['+ header', '+ command_id: string', '+ command_type: uint8'],
                         color=AMBER, stereo='ROS message', w=3.00, fs=6.7, name_fs=8.8)
    vrc_cmd = uml_class(ax, 12.95, 4.15, 'VrcCommand',
                        attrs=['+ header', '+ command_id: string', '+ command_type: uint8', '+ requested_floor: uint16'],
                        color=AMBER, stereo='ROS message', w=3.6, fs=6.7, name_fs=8.8)
    sjd = uml_class(ax, 10.25, 0.95, 'ScheduledJobData',
                    attrs=wrap_lines([
                        '+ job: SchedulerJob', '+ node_indices: uint32[]', '+ bay_id: uint16', '+ bay_arrival_node_guid: Guid'
                    ], 30), color=GREEN, stereo='ROS message', w=3.5, fs=6.8, name_fs=8.8)

    # composition relationships
    for owner, child, lbl, lpos in [
        (req, state, 'base_state', (2.00, 6.62)),
        (req, sched, 'base_schedule', (6.30, 7.10)),
        (req, job, 'planned_jobs / active_jobs / pending_jobs', (5.10, 8.00)),
        (state, agv_state, 'agvs[]', (0.98, 3.97)),
        (state, tray_state, 'trays[]', (4.00, 4.08)),
        (agv_state, pose, 'pose', (1.70, 1.70)),
        (tray_state, pose, 'pose', (4.05, 1.62)),
        (job, pose, 'destination', (4.95, 3.55)),
        (resp, sched, 'schedule', (10.70, 6.96)),
        (resp, sjd, 'scheduled_jobs[]', (10.75, 2.05)),
        (sched, action, 'nodes[]', (9.75, 4.40)),
        (action, agv_cmd, 'agv_command', (13.00, 3.32)),
        (action, bay_cmd, 'bay_command', (12.55, 5.25)),
        (action, vecs_cmd, 'vecs_command', (14.15, 4.80)),
        (action, vrc_cmd, 'vrc_command', (12.30, 3.05)),
        (agv_cmd, agv_goal, 'src / dst', (14.65, 1.95)),
        (agv_goal, pose, 'pose', (8.35, 0.62)),
        (sjd, job, 'job', (8.10, 4.88)),
    ]:
        # simple orthogonal polylines manually selected for compactness
        if owner is req and child is state:
            pts = [req.bot(0.35), (2.0, 6.9), state.top(0.45)]
        elif owner is req and child is sched:
            pts = [req.right(0.55), (7.3, 7.75), sched.left(0.8)]
        elif owner is req and child is job:
            pts = [req.right(0.23), job.left(0.23)]
        elif owner is state and child is agv_state:
            pts = [state.bot(0.26), agv_state.top(0.42)]
        elif owner is state and child is tray_state:
            pts = [state.bot(0.82), tray_state.top(0.46)]
        elif owner is agv_state and child is pose:
            pts = [agv_state.bot(0.60), pose.top(0.25)]
        elif owner is tray_state and child is pose:
            pts = [tray_state.bot(0.25), pose.top(0.82)]
        elif owner is job and child is pose:
            pts = [job.bot(0.78), (7.0, 4.65), (7.0, 1.55), pose.top(0.98)]
        elif owner is resp and child is sched:
            pts = [resp.bot(0.42), sched.top(0.5)]
        elif owner is resp and child is sjd:
            pts = [resp.bot(0.72), sjd.top(0.65)]
        elif owner is sched and child is action:
            pts = [sched.bot(0.50), action.top(0.42)]
        elif owner is action and child is agv_cmd:
            pts = [action.right(0.34), agv_cmd.left(0.44)]
        elif owner is action and child is bay_cmd:
            pts = [action.right(0.84), bay_cmd.left(0.52)]
        elif owner is action and child is vecs_cmd:
            pts = [action.right(0.94), vecs_cmd.left(0.55)]
        elif owner is action and child is vrc_cmd:
            pts = [action.right(0.12), vrc_cmd.left(0.52)]
        elif owner is agv_cmd and child is agv_goal:
            pts = [agv_cmd.bot(0.52), agv_goal.top(0.50)]
        elif owner is agv_goal and child is pose:
            pts = [agv_goal.left(0.50), (12.1, 0.55), pose.right(0.50)]
        elif owner is sjd and child is job:
            pts = [sjd.left(0.62), (8.75, 1.80), (8.75, 8.25), job.right(0.85)]
        uml_rel(ax, pts, kind='comp', color=AMBER, label=lbl, lpos=lpos, fs=6.7)

    # legends
    legend_box(ax, 14.05, 7.15, 2.35, 1.95, 'legend', [
        ('diamond', AMBER, 'composition / contains field'),
        ('box', SKY, 'request-side message'),
        ('box', GREEN, 'response / schedule message'),
        ('box', VIOLET, 'garage-state snapshot'),
        ('box', AMBER, 'command / nested utility message')
    ])
    ax.text(8.5, 9.88, 'As-built ROS service and message composition', ha='center', va='bottom', fontsize=13.2,
            color=FG, family=MONO, fontweight='bold')
    ax.text(8.5, 9.60,
            'Each box is a generated ROS message or service type. Diamonds mark ownership: the source message contains the target as a field or array.',
            ha='center', va='top', fontsize=8.6, color=MUTED)
    save(fig, '13_uml_ros_messages.svg')


def fig_pecos_scene(name, agv_nodes, tray_nodes, path_defs, xlim, ylim, note):
    d = yaml.safe_load(SRC.read_text())
    N = {v['id']: v for v in d['nodes']}
    E = [(e['src'], e['dst']) for e in d['edges']]
    fig, ax = plt.subplots(figsize=(12.5, 8.4))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect('equal'); ax.set_axisbelow(True)
    ax.grid(color='#26334b', linewidth=.45, alpha=.35)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_xlabel('x [m]', color=MUTED, family=MONO); ax.set_ylabel('y [m]', color=MUTED, family=MONO)

    # background drive aisles approximated from rows in YAML
    y_rows = sorted({round(n['y'], 2) for n in N.values() if n['type'] in ('Parking', 'Waypoint', 'AgvCharge')})
    for y in y_rows:
        ax.add_patch(Rectangle((xlim[0]+0.2, y-0.52), xlim[1]-xlim[0]-0.4, 1.04, facecolor='#183149', edgecolor='none', alpha=.18, zorder=0))

    # edges
    for a, b in E:
        p, q = N[a], N[b]
        if not (xlim[0]-1 <= p['x'] <= xlim[1]+1 and ylim[0]-1 <= p['y'] <= ylim[1]+1):
            continue
        if not (xlim[0]-1 <= q['x'] <= xlim[1]+1 and ylim[0]-1 <= q['y'] <= ylim[1]+1):
            continue
        ax.plot([p['x'], q['x']], [p['y'], q['y']], color='#64748b', lw=2.0, zorder=1)

    # nodes
    for i, n in N.items():
        x, y, typ = n['x'], n['y'], n['type']
        if not (xlim[0]-0.8 <= x <= xlim[1]+0.8 and ylim[0]-0.8 <= y <= ylim[1]+0.8):
            continue
        c = {'Parking':SKY, 'Bay':GREEN, 'Waypoint':MUTED, 'AgvCharge':VIOLET}.get(typ, AMBER)
        if typ == 'Parking':
            ax.add_patch(Rectangle((x-1.90, y-0.88), 3.8, 1.76, facecolor='#17283b', edgecolor=c, lw=1.2, alpha=.95, zorder=2))
            ax.text(x, y+1.10, f'P{i}', ha='center', va='bottom', fontsize=8.0, color=c, family=MONO,
                    fontweight='bold', zorder=12, bbox=dict(fc=BG, ec='none', pad=.25))
        elif typ == 'Bay':
            ax.add_patch(FancyBboxPatch((x-1.9, y-1.02), 3.8, 2.04, boxstyle='round,pad=.03,rounding_size=.18',
                                        facecolor='#14372a', edgecolor=c, lw=1.8, zorder=2))
            ax.plot([x+1.92, x+1.92], [y-0.75, y+0.75], color=AMBER, lw=3.6, zorder=3)
            ax.text(x, y+1.24, f'B{i}', ha='center', va='bottom', fontsize=8.2, color=c, family=MONO,
                    fontweight='bold', zorder=12, bbox=dict(fc=BG, ec='none', pad=.25))
        elif typ == 'AgvCharge':
            ax.add_patch(Circle((x, y), .55, facecolor='#2a2145', edgecolor=c, lw=1.7, zorder=3))
            ax.text(x+0.95, y+0.45, f'C{i}', ha='left', va='bottom', fontsize=7.8, color=c, family=MONO,
                    fontweight='bold', zorder=12, bbox=dict(fc=BG, ec='none', pad=.25))
        else:
            ax.add_patch(Circle((x, y), .13, facecolor=c, edgecolor=c, zorder=3))
            ax.text(x-0.35, y+0.38, f'W{i}', ha='right', va='bottom', fontsize=7.1, color=MUTED, family=MONO,
                    zorder=12, bbox=dict(fc=BG, ec='none', pad=.20))

    # paths
    for ids, color, caption in path_defs:
        pts = [N[i] for i in ids]
        for p, q in zip(pts, pts[1:]):
            ax.annotate('', xy=(q['x'], q['y']), xytext=(p['x'], p['y']),
                        arrowprops=dict(arrowstyle='-|>', color=color, lw=3.2, mutation_scale=16, shrinkA=12, shrinkB=12),
                        zorder=7)
        mid = pts[len(pts)//2]
        ax.text(mid['x']+0.2, mid['y']+0.8, caption, color=color, fontsize=8.2, family=MONO,
                bbox=dict(boxstyle='round,pad=.2', fc=BG, ec=color, lw=0.9), zorder=13)

    # trays and agvs
    for nid, txt in tray_nodes:
        x, y = N[nid]['x'], N[nid]['y']
        ax.add_patch(FancyBboxPatch((x-1.05, y-0.40), 2.1, 0.80, boxstyle='round,pad=.02,rounding_size=.10',
                                    fc='#4a341f', ec=AMBER, lw=2.0, zorder=8))
        ax.text(x, y, txt, ha='center', va='center', fontsize=8.5, color='#fff2d5', family=MONO, fontweight='bold', zorder=9)
    for nid, txt, heading in agv_nodes:
        x, y = N[nid]['x'], N[nid]['y']
        agv(ax, x, y, heading, color=GREEN, L=.8, W=.62, scale=1.55, label=None)
        ax.text(x, y-1.00, txt, ha='center', va='top', fontsize=8.0, color=FG, family=MONO,
                zorder=12, bbox=dict(fc=BG, ec='none', pad=.35))

    # legends
    legend_entries = [
        ('box', SKY, 'parking node / stall outline'),
        ('box', GREEN, 'bay resource'),
        ('box', VIOLET, 'AGV charging node'),
        ('line', '#64748b', 'garage-graph edge'),
        ('arrow', GREEN, 'primary AGV / tray path'),
        ('arrow', AMBER, 'blocking-tray path')
    ]
    legend_box(ax, xlim[1]-5.7, ylim[0]+0.35, 5.35, 2.12, 'legend', legend_entries)

    ax.set_title(name, loc='left', color=FG, fontsize=15.5, family=MONO, fontweight='bold', pad=12)
    ax.text(0.0, -0.12, note, transform=ax.transAxes, ha='left', va='top', fontsize=9.0, color=MUTED)
    fig.subplots_adjust(left=.08, right=.98, top=.90, bottom=.16)
    save(fig, f'15_{name.lower().replace(" ", "_")}.svg')


def update_markdown():
    p = ROOT/'01-software-background.md'
    s = p.read_text()

    # richer message/services section
    start = s.index('## 4. ROS messages and services')
    end = s.index('## 5. C++ classes: orientation and source map')
    replacement = '''## 4. ROS messages and services

The `interfaces` package defines the wire contracts under `msg/` and `srv/`. `rosidl_generate_interfaces` turns those text definitions into generated C++ structs, introspection support, and serialization code. This is **data exchange**, not C++ inheritance. In other words, when one ROS message appears inside another, the relationship is **composition**: one struct contains another struct or an array of such structs as a field.

For a new engineer, the most useful way to read these interfaces is from **outside in**:

1. Start with `srv/Plan.srv`, because it is the service boundary for the Scheduler.
2. Open `PlanRequest.msg` and `PlanResponse.msg` to see the request/response payloads.
3. Then expand the nested messages that matter most: `DiscreteGarageState`, `Schedule`, `ActionNode`, and `SchedulerJob`.
4. Only after that should you drill into utility types such as `GaragePose`, `AgvGoal`, or the resource-specific command messages.

| Interface | What it contains | Why it matters to the Scheduler |
|---|---|---|
| `srv/Plan.srv` | A `PlanRequest` and a `PlanResponse`. | This is the ROS service contract that `SchedulerRos` exposes. When another node “calls the Scheduler”, this is the exact boundary crossing. |
| `msg/PlanRequest.msg` | A planning ID, the current `DiscreteGarageState`, the immutable `base_schedule`, and three job arrays: `planned_jobs`, `active_jobs`, and `pending_jobs`. | This message tells the Scheduler both **what the world looks like now** and **what work still needs to be planned**. |
| `msg/PlanResponse.msg` | A success flag, human-readable message, plan-call ID, an output `Schedule`, and `ScheduledJobData[]`. | This is how the Scheduler returns both the executable schedule and job-level bookkeeping information back to the caller. |
| `msg/SchedulerJob.msg` | A high-level job request, including job type, state, IDs for AGV/bay/tray/payload, and an optional destination. | This message expresses user or dispatcher intent. It is still much more abstract than the final action schedule. |
| `msg/DiscreteGarageState.msg` | Arrays of AGVs, bays, VECS, trays, payloads, VRCs, plus disabled nodes and a hash. | This is the Scheduler’s snapshot of the garage at the beginning of a plan call. The in-process C++ `DiscreteGarageState` class is built around this same conceptual information. |
| `msg/GarageLayout.msg` | Layout name, nodes, floors, edges, disallowed orientations, and resource windows. | This message defines the static topology over which AGVs, trays, and payloads move. |
| `msg/GarageNode.msg` | Node geometry, node type, floor, allowed headings, rotation permission, and bay-specific metadata. | This tells the rest of the software what a particular node ID actually means in physical and operational terms. |
| `msg/GaragePose.msg` | A node ID and a discrete heading. | This is the canonical discrete pose type used throughout scheduling, assignment, and action generation. |
| `msg/Schedule.msg` | A topologically ordered array of `ActionNode`s. | This is the output execution DAG that downstream execution software consumes. |
| `msg/ActionNode.msg` | An action type, dependency indices, timing/status fields, and type-specific command payloads. | This is the final bridge from in-memory planning logic to executable ROS-level commands. |

![ROS message relationships](figures/13_uml_ros_messages.svg)

*Figure 3 — As-built ROS service and message composition derived from the `.msg` and `.srv` definitions. A **filled diamond** means “contains as a field or array element.” Blue boxes sit on the **request / intent** side, violet boxes describe the **garage-state snapshot**, green boxes describe the **response / schedule** side, and amber boxes are **nested command or utility messages**. The dashed outer frame marks the `Plan.srv` boundary.*

A few important reading notes help prevent confusion:

- `PlanRequest` and `PlanResponse` are ROS message **types**, not C++ service handler classes.
- `Schedule.nodes` is a topologically ordered array of `ActionNode` messages, so dependencies in the serialized schedule are represented by **integer parent indices**, not pointers.
- `ActionNode` is intentionally wide: it contains several command fields, but only the field corresponding to the node’s `type` is semantically active.
- `SchedulerJob.destination` and `DiscreteAgvState.pose` both use `GaragePose`, which keeps the discrete graph interpretation consistent across request, state, and output data.

`ActionNode.parents` therefore contains **indices** into the output schedule, not `shared_ptr` references to `ScheduleEvent` objects. The transition from in-process event objects to serialized action indices happens near the end of planning.

'''
    s = s[:start] + replacement + s[end:]

    start = s.index('## 5. C++ classes: orientation and source map')
    end = s.index('## 6. Objects and ownership: the Scheduler and ScheduleContext')
    replacement = '''## 5. C++ classes: orientation and source map

Once the ROS interfaces are clear, the next question is: **which C++ objects hold, transform, and emit those data?** The table below is deliberately more descriptive than a quick reference sheet, because these classes are the vocabulary of the rest of the guide.

Read the rows in three passes:

1. First, identify the *orchestrator* types such as `Scheduler` and `ScheduleContext`.
2. Next, identify the *domain-model* types such as `ScheduleEvent`, `TrayMove`, `AgvMove`, and `DiscreteGarageState`.
3. Finally, identify the *infrastructure* types such as `ScheduleEventDag`, `GarageGraph`, `GarageOccupancyChecker`, and the collision / cost helpers.

| Class / type | What it does | Declared in | Key members / methods |
|---|---|---|---|
| `Scheduler` | The main planner object. It validates requests, expands jobs into abstract events, performs tray and AGV assignment, checks the resulting plan, and invokes motion planning. In other words, this is the *orchestrator* of the entire pipeline. | `src/planner/scheduler/include/scheduler/scheduler.hpp` | `Plan`, `DoTrayAssignments`, `DoAgvAssignments`, `PlanMotions` |
| `SchedulerParams` | A bundle of constructor-time configuration and planning parameters. It lets the planner be configured without encoding every setting as a separate constructor argument. | Same `scheduler.hpp` | `motion_cost`, `bay_readiness_ratio`, `cost_audit` |
| `ScheduleContext` | The mutable working set for a single plan call. It carries the initial garage state, the evolving event DAG, scheduled-job metadata, and several helper maps used to preserve dependency relationships. | Same `scheduler.hpp` | `initial_state`, `events`, `scheduled_jobs`, `first_tray_event` |
| `ScheduleEvent` | The abstract base class for in-memory schedule events. Each concrete subclass represents a state-changing operation that can be replayed against a `DiscreteGarageState`. | `src/planner/planner_core/include/planner_core/schedule_events.hpp` | `Apply`, `GetGarageEntityId`, `GetJobIndex`, `GetType` |
| `TrayMove` | A partially or fully assigned tray-relocation event. Before assignment, it may be missing the tray ID, destination, or AGV ID; after assignment, it becomes much more concrete. | Same `schedule_events.hpp` | `GetTrayId`, `SetTrayId`, `GetDest`, `SetDest`, `SetAgvId` |
| `AgvMove` | A concrete AGV movement or lift-change event. Unlike `TrayMove`, this represents *robot* motion rather than abstract tray intent. | Same `schedule_events.hpp` | `GetDiscreteChange`, `GetAgvId`, `Apply` |
| `BayTransition` | A state transition or command affecting a bay. It captures the bay-side operations required for insert/retrieve workflows. | Same `schedule_events.hpp` | `GetSourceState`, `GetCommand`, `Apply` |
| `VecsTransition` | A state transition for EV charging equipment. This is the scheduler-facing representation of charging-resource state changes. | Same `schedule_events.hpp` | `GetStateChange`, `Apply` |
| `VrcTransition` | A transition involving a VRC, including floor movement and gate-related state changes. It matters in multi-floor garages even though the Pecos YAML used in the figures has no VRC node. | Same `schedule_events.hpp` | `GetFromVrcNodeId`, `GetToVrcNodeId`, `Apply` |
| `DagBase<T>` | A reusable directed-graph template implemented with Boost Graph. It provides graph storage and generic algorithms such as adding edges and obtaining a topological order. | `src/planner/planner_core/include/planner_core/event_dag.hpp` | `Add`, `AddDependency`, `Reduce`, `GetTopologicalOrdering` |
| `ScheduleEventDag` | The Scheduler-specific DAG specialization whose vertices are `ScheduleEvent` objects. This is where abstract event dependencies are stored before action generation. | Same `event_dag.hpp` | `AddEvent`, `GetTopologicalOrdering`, `Apply` |
| `DiscreteGarageState` | The in-memory state model that answers questions like “where is tray 19?” or “is AGV 4 disabled?” It is replayed and mutated repeatedly during planning. | `src/common_ros/include/common_ros/discrete_garage_state.hpp` (included; implementation not supplied) | `GetAgv`, `GetTray`, `OnEvent` |
| `GarageGraph` / `PoseGraph` | Graph structures used to map between node/heading poses and search vertices. These help the Scheduler and motion planner reason about movement feasibility. | `src/common_ros/include/common_ros/garage_graph.hpp` and `pose_graph.hpp` (included; bodies not supplied) | `GetVertexFromPose`, `GetPoseFromVertex` |
| `GarageOccupancyChecker<T>` | An occupancy/dependency helper that remembers who currently blocks a pose and which event would free it. This helper is especially relevant when tray moves and AGV arrivals must wait on one another. | `src/common_ros/include/common_ros/garage_occupancy_checker.hpp` (included; body not supplied) | `GetBlockers`, `AddOccupant` |
| `CollisionTable` | A geometry / compatibility helper used by the Scheduler to reject incompatible co-occupancy and movement combinations. The exact class definition was not included in the uploaded snapshots, but its role is visible through its use sites. | Exact class declaration not established by snapshots | `Query` (used by Scheduler) |
| `MotionCostModel` | A cost / duration model for estimating travel- and action-related costs. It supplies the timing assumptions that later influence assignment and scheduling. | `cost_functions/motion_cost_model.hpp` (included; body not supplied) | `Params` |

![Current class relationships](figures/11_uml_existing_core.svg)

*Figure 4 — Existing core-class relationships. `Scheduler` orchestrates planning, `ScheduleContext` packages one plan attempt’s mutable working data, `ScheduleEventDag` stores abstract event dependencies, and `DiscreteGarageState` models the world that those events mutate. The diagram is intentionally compact, so it shows the dominant ownership / usage relationships rather than every helper member.*

If you are looking for the shortest possible mental model, use this one: **`Scheduler` is the conductor, `ScheduleContext` is the score currently being annotated, `ScheduleEventDag` is the dependency structure of abstract work, and `DiscreteGarageState` is the simulated world on which the work is replayed.**

'''
    s = s[:start] + replacement + s[end:]

    start = s.index('## 7. Event types and polymorphism')
    end = s.index('## 8. Directed acyclic graphs, then ScheduleEventDag')
    replacement = '''## 7. Event types and polymorphism

At this point we can finally explain `ScheduleEventDag` cleanly, because we now know what a **schedule event** is. A `ScheduleEvent` is an in-memory C++ object representing an abstract operation that can be replayed against a `DiscreteGarageState`. The base class is intentionally small: it provides a virtual destructor, a virtual `Apply(...)`, and query functions such as `GetGarageEntityId()`.

The key design idea is **runtime polymorphism**. The DAG stores `std::shared_ptr<ScheduleEvent>`, but at runtime those pointers may actually point to `TrayMove`, `AgvMove`, `BayTransition`, `VecsTransition`, or `VrcTransition` objects. When the Scheduler replays the DAG, the correct subclass implementation of `Apply(...)` runs through virtual dispatch.

![Existing event inheritance](figures/12_uml_event_hierarchy.svg)

*Figure 5 — Existing C++ inheritance hierarchy, not proposed solver architecture. A **hollow triangle** means public inheritance and points toward the base class. Blue marks the abstract base type, green marks movement / assignment events, and violet marks other resource-transition events. The arrow therefore reads as “`TrayMove` **is a** `ScheduleEvent`,” not “`ScheduleEvent` contains a `TrayMove`.”*

This figure often causes two kinds of confusion:

1. The inheritance arrow does **not** mean execution order. It only expresses the C++ type relationship.
2. The subclasses are **siblings**, not phases. For example, a `TrayMove` does not “turn into” an `AgvMove`; rather, both appear as separate event objects in the overall event DAG.

```cpp
// Abridged from planner_core/schedule_events.hpp.
class ScheduleEvent {
 public:
  virtual ~ScheduleEvent() = default;
  virtual BoolStringPair Apply(DiscreteGarageState& state) const = 0;
  virtual std::optional<GarageEntityIdMsg> GetGarageEntityId() const = 0;
};

class TrayMove : public ScheduleEvent {
 public:
  bool Assigned() const { return tray_id_ && dest_; }
  std::optional<uint16_t> GetTrayId() const { return tray_id_; }
  void SetTrayId(uint16_t id) { tray_id_ = id; }
  std::optional<GaragePoseMsg> GetDest() const { return dest_; }
  void SetDest(GaragePoseMsg dest) { dest_ = dest; }
  std::optional<uint16_t> GetAgvId() const { return agv_id_; }
  void SetAgvId(uint16_t id) { agv_id_ = id; }
};
```

A `TrayMove` is therefore **not an AGV command**. Before assignment, it may mean “find an empty tray for this bay” or “find somewhere to repark this specified tray.” `AgvMove` differs: it owns a `std::variant<AgvLiftChangedMsg, AgvPoseChangedMsg>` and uses `std::visit` to apply one concrete discrete change. `BayTransition`, `VecsTransition`, and `VrcTransition` encapsulate other resource changes. The common base class lets all of them coexist inside the same `ScheduleEventDag`.

'''
    s = s[:start] + replacement + s[end:]

    # Expand section 8 first paragraph a bit
    s = s.replace('**Now the implementation.** `DagBase<T>` is a C++ template implemented on a Boost `adjacency_list`; its vertices hold `std::shared_ptr<T>`. The specialized subclass `ScheduleEventDag : DagBase<ScheduleEvent>` stores abstract events and computes a topological ordering prioritizing earlier job indices among currently eligible events.',
                  '**Now the implementation.** `DagBase<T>` is a C++ template implemented on a Boost `adjacency_list`; its vertices hold `std::shared_ptr<T>`. The specialized subclass `ScheduleEventDag : DagBase<ScheduleEvent>` stores abstract event objects and dependency edges between them. In practical terms, this means the Scheduler can ask questions such as “which work has no unsatisfied prerequisites yet?” or “if I add this dependency, would I create a cycle?” The custom topological ordering also biases earlier job indices among currently eligible events, so job grouping influences the replay order when multiple events are otherwise ready.')

    # section 11 captions maybe not necessary. Enhance table 3 slightly? We'll leave.
    p.write_text(s)


def make_zip():
    zip_path = Path('/mnt/data/scheduler-core-refactor-study-v5.zip')
    import zipfile
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in ROOT.rglob('*'):
            if path.is_file():
                z.write(path, path.relative_to(ROOT.parent))
    return zip_path


if __name__ == '__main__':
    fig_event_hierarchy()
    fig_ros_messages()
    fig_pecos_scene(
        'AGV approach and pickup',
        agv_nodes=[(10, 'AGV A', math.pi/2)],
        tray_nodes=[(3, 'tray T3')],
        path_defs=[([10, 9, 11, 6, 3], GREEN, 'approach + pickup route')],
        xlim=(34.0, 45.5), ylim=(7.0, 14.8),
        note='Real Pecos node coordinates and edges are shown. The AGV starting at charger C10 and the tray placed at parking node P3 are illustrative scenario choices, not YAML occupancy facts.'
    )
    fig_pecos_scene(
        'Blocking tray move',
        agv_nodes=[(14, 'AGV A', math.pi/2)],
        tray_nodes=[(15, 'root tray'), (19, 'blocking tray')],
        path_defs=[([19, 23, 22, 18], AMBER, 'blocking tray clears aisle'), ([15, 19, 23], GREEN, 'root tray then advances')],
        xlim=(29.0, 44.8), ylim=(15.6, 25.4),
        note='The parking-lot scene is grounded in the Pecos layout geometry. The two tray placements and both routes are explanatory examples showing prerequisite relocation; they are not claimed to be the exact output of a validated scheduler run.'
    )
    update_markdown()
    zp = make_zip()
    print(zp)
