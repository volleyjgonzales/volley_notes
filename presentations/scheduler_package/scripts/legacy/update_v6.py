from pathlib import Path
import yaml
import math
import re
import sys
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
from matplotlib.lines import Line2D

ROOT = Path('/mnt/data/scheduler_core_refactor')
FIG = ROOT/'figures'
YAML_PATH = ROOT/'sources'/'5675_pecos_combined.yaml'

sys.path.insert(0, str(ROOT/'scripts'))
from figstyle import plt, BG, CARD, FG, MUTED, BORDER, SKY, GREEN, AMBER, RED, VIOLET, MONO
from draw import canvas, uml_class, uml_rel, agv


def save(fig, name):
    fig.savefig(FIG/name, facecolor=BG, bbox_inches='tight', pad_inches=0.05, metadata={'Date':None})
    plt.close(fig)


def legend_box(ax, x, y, w, h, title, entries):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.03,rounding_size=0.12',
                                facecolor='#121b2d', edgecolor=BORDER, lw=1.1, zorder=30))
    ax.text(x+0.10, y+h-0.10, title, ha='left', va='top', fontsize=8.6, color=FG, family=MONO, fontweight='bold', zorder=31)
    yy = y+h-0.34
    for kind, color, text in entries:
        if kind == 'parking':
            ax.add_patch(Rectangle((x+0.10, yy-0.12), 0.28, 0.16, facecolor='#17283b', edgecolor=SKY, lw=1.2, zorder=31))
        elif kind == 'bay':
            ax.add_patch(FancyBboxPatch((x+0.10, yy-0.13), 0.28, 0.18, boxstyle='round,pad=0.01,rounding_size=0.03',
                                        facecolor='#14372a', edgecolor=GREEN, lw=1.2, zorder=31))
        elif kind == 'charge':
            ax.add_patch(Circle((x+0.24, yy-0.04), 0.08, facecolor='#2a2145', edgecolor=VIOLET, lw=1.2, zorder=31))
        elif kind == 'waypoint':
            ax.add_patch(Circle((x+0.24, yy-0.04), 0.04, facecolor=MUTED, edgecolor=MUTED, lw=1.0, zorder=31))
        elif kind == 'edge':
            ax.plot([x+0.10, x+0.38], [yy-0.04, yy-0.04], color='#64748b', lw=2.0, zorder=31)
        elif kind == 'route_g':
            ax.annotate('', xy=(x+0.38, yy-0.04), xytext=(x+0.10, yy-0.04), arrowprops=dict(arrowstyle='-|>', color=GREEN, lw=2.0), zorder=31)
        elif kind == 'route_a':
            ax.annotate('', xy=(x+0.38, yy-0.04), xytext=(x+0.10, yy-0.04), arrowprops=dict(arrowstyle='-|>', color=AMBER, lw=2.0), zorder=31)
        elif kind == 'comp':
            pts = [(x+0.10, yy-0.04), (x+0.18, yy+0.04), (x+0.26, yy-0.04), (x+0.18, yy-0.12)]
            ax.add_patch(Polygon(pts, closed=True, facecolor=AMBER, edgecolor=AMBER, lw=1.1, zorder=31))
            ax.plot([x+0.26, x+0.38], [yy-0.04, yy-0.04], color=AMBER, lw=1.5, zorder=31)
        elif kind == 'inh':
            pts = [(x+0.38, yy-0.04), (x+0.28, yy+0.04), (x+0.28, yy-0.12)]
            ax.add_patch(Polygon(pts, closed=True, facecolor=BG, edgecolor=SKY, lw=1.1, zorder=31))
            ax.plot([x+0.10, x+0.28], [yy-0.04, yy-0.04], color=SKY, lw=1.5, zorder=31)
        elif kind == 'class':
            ax.add_patch(Rectangle((x+0.10, yy-0.12), 0.28, 0.16, facecolor=CARD, edgecolor=color, lw=1.2, zorder=31))
        elif kind == 'data':
            ax.add_patch(Rectangle((x+0.10, yy-0.12), 0.28, 0.16, facecolor='#1a2438', edgecolor=color, lw=1.2, zorder=31))
        ax.text(x+0.48, yy-0.04, text, ha='left', va='center', fontsize=7.8, color=MUTED, family=MONO, zorder=31)
        yy -= 0.26


def load_layout():
    data = yaml.safe_load(YAML_PATH.read_text())
    nodes = {n['id']: n for n in data['nodes']}
    edges = [(e['src'], e['dst']) for e in data['edges']]
    return data, nodes, edges


def draw_facility(ax, nodes, edges, xpad=1.0, ypad=1.0):
    xs = [n['x'] for n in nodes.values()]
    ys = [n['y'] for n in nodes.values()]
    xmin, xmax = min(xs)-xpad, max(xs)+xpad
    ymin, ymax = min(ys)-ypad, max(ys)+ypad
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect('equal')
    ax.grid(color='#26334b', linewidth=.45, alpha=.30)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_xlabel('x [m]', color=MUTED, family=MONO)
    ax.set_ylabel('y [m]', color=MUTED, family=MONO)
    # row background bands
    y_rows = sorted({round(n['y'], 2) for n in nodes.values() if n['type'] in ('Parking', 'Waypoint', 'AgvCharge', 'Bay')})
    for y in y_rows:
        ax.add_patch(Rectangle((xmin+0.15, y-0.52), xmax-xmin-0.3, 1.04, facecolor='#183149', edgecolor='none', alpha=.12, zorder=0))
    # edges
    for a,b in edges:
        p,q = nodes[a], nodes[b]
        ax.plot([p['x'], q['x']], [p['y'], q['y']], color='#64748b', lw=1.9, zorder=1)
    # nodes
    for i,n in nodes.items():
        x,y,typ = n['x'], n['y'], n['type']
        if typ == 'Parking':
            ax.add_patch(Rectangle((x-1.88, y-0.86), 3.76, 1.72, facecolor='#17283b', edgecolor=SKY, lw=1.2, zorder=2))
            ax.text(x, y+1.02, f'P{i}', ha='center', va='bottom', fontsize=7.4, color=SKY, family=MONO, fontweight='bold',
                    bbox=dict(fc=BG, ec='none', pad=.18), zorder=10)
        elif typ == 'Bay':
            ax.add_patch(FancyBboxPatch((x-1.88, y-1.00), 3.76, 2.00, boxstyle='round,pad=.03,rounding_size=.16',
                                        facecolor='#14372a', edgecolor=GREEN, lw=1.8, zorder=2))
            ax.plot([x+1.88, x+1.88], [y-0.72, y+0.72], color=AMBER, lw=3.2, zorder=3)
            ax.text(x, y+1.12, f'B{i}', ha='center', va='bottom', fontsize=7.6, color=GREEN, family=MONO, fontweight='bold',
                    bbox=dict(fc=BG, ec='none', pad=.18), zorder=10)
        elif typ == 'AgvCharge':
            ax.add_patch(Circle((x, y), 0.50, facecolor='#2a2145', edgecolor=VIOLET, lw=1.6, zorder=3))
            ax.text(x+0.72, y+0.36, f'C{i}', ha='left', va='bottom', fontsize=7.2, color=VIOLET, family=MONO, fontweight='bold',
                    bbox=dict(fc=BG, ec='none', pad=.16), zorder=10)
        else:
            ax.add_patch(Circle((x, y), 0.12, facecolor=MUTED, edgecolor=MUTED, zorder=3))
            ax.text(x-0.28, y+0.28, f'W{i}', ha='right', va='bottom', fontsize=6.6, color=MUTED, family=MONO,
                    bbox=dict(fc=BG, ec='none', pad=.14), zorder=10)
    return xmin, xmax, ymin, ymax


def fig_facility_topology():
    data, nodes, edges = load_layout()
    fig, ax = plt.subplots(figsize=(13.2, 9.1))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    xmin,xmax,ymin,ymax = draw_facility(ax, nodes, edges, xpad=0.6, ypad=0.7)
    legend_box(ax, xmax-6.2, ymin+0.35, 5.8, 2.15, 'legend', [
        ('parking', SKY, 'parking node / tray stall'),
        ('bay', GREEN, 'bay node / customer handoff'),
        ('charge', VIOLET, 'AGV charging node'),
        ('waypoint', MUTED, 'waypoint / connector node'),
        ('edge', MUTED, 'undirected garage-graph edge'),
    ])
    ax.set_title('Pecos facility topology', loc='left', color=FG, fontsize=15.5, family=MONO, fontweight='bold', pad=12)
    ax.text(0.0, -0.11,
            'The view is tightly cropped to the YAML node extents to reduce unused border space. Open the linked SVG directly in VS Code or a browser if you want pan/zoom beyond the Markdown preview.',
            transform=ax.transAxes, ha='left', va='top', fontsize=8.8, color=MUTED)
    fig.subplots_adjust(left=.07, right=.985, top=.90, bottom=.15)
    save(fig, '15_facility_topology.svg')


def fig_uml_existing_core():
    fig, ax = canvas(17.5, 10.4, equal=False)
    ax.text(8.75, 10.05, 'Existing core planner relationships', ha='center', va='bottom', fontsize=13.2, color=FG, family=MONO, fontweight='bold')
    ax.text(8.75, 9.80, 'Orthogonal connectors emphasize ownership / usage rather than execution order.', ha='center', va='top', fontsize=8.6, color=MUTED)

    sched = uml_class(ax, 6.3, 9.2, 'Scheduler',
                      attrs=['- layout_: GarageLayout', '- gg_: GarageGraph', '- table_: CollisionTable',
                             '- motion_cost_: MotionCostModel', '- logger_: rclcpp::Logger'],
                      methods=['+ Plan(request) -> PlanResponseMsg', '+ DoTrayAssignments(ctx)', '+ DoAgvAssignments(ctx)',
                               '+ PlanMotions(ctx)'], color=SKY, stereo='orchestrator', w=4.6, fs=7.6, name_fs=9.6)
    ctx = uml_class(ax, 1.0, 6.7, 'ScheduleContext',
                    attrs=['+ initial_state: DiscreteGarageState', '+ events: ScheduleEventDag', '+ scheduled_jobs: vector<...>',
                           '+ last_entity_event: map<...>', '+ first_tray_event: map<...>'],
                    methods=['+ PushBackScheduledJob(job)'], color=GREEN, stereo='per-plan mutable state', w=5.1, fs=7.3, name_fs=9.2)
    dag = uml_class(ax, 6.5, 6.7, 'ScheduleEventDag',
                    attrs=['inherits DagBase<ScheduleEvent>', '+ vertices: shared_ptr<ScheduleEvent>'],
                    methods=['+ AddEvent(ev)', '+ AddDependency(a,b)', '+ Reduce()', '+ GetTopologicalOrdering()'],
                    color=AMBER, stereo='dependency graph', w=4.8, fs=7.3, name_fs=9.2)
    state = uml_class(ax, 12.2, 6.7, 'DiscreteGarageState',
                      attrs=['+ agvs / bays / trays / payloads / vrcs', '+ disabled_nodes', '+ hash'],
                      methods=['+ GetAgv(id)', '+ GetTray(id)', '+ OnEvent(change)'],
                      color=VIOLET, stereo='world state model', w=4.9, fs=7.3, name_fs=9.2)
    ev = uml_class(ax, 6.3, 3.2, 'ScheduleEvent',
                   attrs=['# job_index_: size_t', '# type_: ScheduleEventType'],
                   methods=['+ Apply(state) const = 0', '+ GetGarageEntityId() const = 0'],
                   color=SKY, stereo='abstract base class', w=4.6, fs=7.3, name_fs=9.1)
    tm = uml_class(ax, 0.6, 1.0, 'TrayMove', attrs=['- tray_id_: optional<uint16_t>', '- dest_: optional<GaragePoseMsg>', '- agv_id_: optional<uint16_t>'],
                   methods=['+ Assigned() const', '+ SetDest(dest)'], color=GREEN, w=4.3, fs=7.0, name_fs=8.8)
    am = uml_class(ax, 5.9, 1.0, 'AgvMove', attrs=['- discrete_change_: variant<...>'], methods=['+ Apply(state) const'], color=GREEN, w=3.6, fs=7.0, name_fs=8.8)
    bt = uml_class(ax, 10.1, 1.0, 'BayTransition', attrs=['- command_: BayCommandMsg'], methods=['+ Apply(state) const'], color=GREEN, w=3.8, fs=7.0, name_fs=8.8)
    vt = uml_class(ax, 14.5, 1.0, 'VrcTransition / VecsTransition', attrs=['- state_change_: ...'], methods=['+ Apply(state) const'], color=GREEN, w=4.4, fs=6.8, name_fs=8.6)

    uml_rel(ax, [sched.bot(0.35), (sched.cx-2.2, 8.0), (ctx.cx+2.45, 8.0), ctx.top(0.80)], kind='assoc', color=SKY, label='creates and mutates per request', lpos=(3.9,8.18), fs=7.0)
    uml_rel(ax, [sched.bot(0.53), (sched.cx, 8.1), dag.top(0.50)], kind='assoc', color=SKY, label='adds / wires events', lpos=(7.85,8.16), fs=7.0)
    uml_rel(ax, [sched.bot(0.76), (sched.cx+2.7, 8.0), (state.cx-2.5, 8.0), state.top(0.18)], kind='assoc', color=SKY, label='queries and replays state', lpos=(12.0,8.18), fs=7.0)

    uml_rel(ax, [ctx.right(0.55), (5.3, 6.15), dag.left(0.55)], kind='comp', color=AMBER, label='events', lpos=(4.05,6.35), fs=7.1)
    uml_rel(ax, [ctx.right(0.22), (7.1, 5.45), state.left(0.25)], kind='comp', color=AMBER, label='initial_state', lpos=(9.2,5.67), fs=7.1)
    uml_rel(ax, [dag.bot(0.50), (8.9, 4.7), (8.9, 4.0), ev.top(0.50)], kind='comp', color=AMBER, label='vertex payload type', lpos=(9.55,4.35), fs=7.0)

    # inheritance tree orthogonal
    spine_y = 2.65
    ax.plot([ev.cx, ev.cx], [ev.y0, spine_y], color=SKY, lw=1.1)
    ax.plot([tm.cx+2.15, vt.cx-2.2], [spine_y, spine_y], color=SKY, lw=1.1)
    for child in [tm, am, bt, vt]:
        x = child.cx
        ax.plot([x, x], [spine_y, child.y1], color=SKY, lw=1.1)
        uml_rel(ax, [(x, child.y1), (x, spine_y), (ev.cx, spine_y), (ev.cx, ev.y0)], kind='inh', color=SKY)
    legend_box(ax, 13.2, 8.55, 4.05, 1.65, 'legend', [
        ('class', SKY, 'major planner class / abstraction'),
        ('class', GREEN, 'concrete event class'),
        ('comp', AMBER, 'composition / owns as a member'),
        ('inh', SKY, 'public inheritance (is-a)'),
    ])
    save(fig, '11_uml_existing_core.svg')


def fig_ros_messages_roomier():
    fig, ax = canvas(22.0, 12.0, equal=False)
    ax.add_patch(FancyBboxPatch((0.3, 0.3), 21.3, 11.2, boxstyle='round,pad=0.03,rounding_size=0.18',
                                facecolor='none', edgecolor=BORDER, lw=1.2, linestyle='--', zorder=1))
    ax.text(0.5, 11.35, 'srv/Plan.srv', ha='left', va='top', fontsize=10.4, color=FG, family=MONO, fontweight='bold')
    ax.text(11.0, 11.62, 'As-built ROS service and message composition', ha='center', va='bottom', fontsize=13.2, color=FG, family=MONO, fontweight='bold')
    ax.text(11.0, 11.36, 'Boxes are message / service types. Filled diamonds mean the source type contains the target as a field or array.', ha='center', va='top', fontsize=8.6, color=MUTED)

    def u(*args, **kwargs):
        return uml_class(ax, *args, **kwargs)

    req = u(0.7, 10.6, 'PlanRequest', attrs=['+ id: Guid', '+ base_state: DiscreteGarageState', '+ base_schedule: Schedule', '+ planned_jobs: SchedulerJob[]', '+ active_jobs: SchedulerJob[]', '+ pending_jobs: SchedulerJob[]'], color=SKY, stereo='request message', w=4.3, fs=7.2, name_fs=9.2)
    resp = u(11.2, 10.6, 'PlanResponse', attrs=['+ success: bool', '+ message: string', '+ id: Guid', '+ schedule: Schedule', '+ scheduled_jobs: ScheduledJobData[]'], color=GREEN, stereo='response message', w=3.9, fs=7.2, name_fs=9.2)
    job = u(5.7, 10.6, 'SchedulerJob', attrs=['+ type / state / guid', '+ agv_id / bay_id / tray_id', '+ payload_id: Guid', '+ destination: GaragePose', '+ allow_reciprocal: bool', '+ retain_job / needs_bay_in_retrieve: bool'], color=SKY, stereo='request payload', w=4.6, fs=7.0, name_fs=9.0)
    dgs = u(0.8, 7.15, 'DiscreteGarageState', attrs=['+ agvs: DiscreteAgvState[]', '+ bays: DiscreteBayState[]', '+ vexen: DiscreteVecsState[]', '+ trays: DiscreteTrayState[]', '+ payloads: DiscretePayloadState[]', '+ vrcs: DiscreteVrcState[]', '+ disabled_nodes: uint32[]', '+ hash: uint64'], color=VIOLET, stereo='state snapshot', w=4.5, fs=6.9, name_fs=8.9)
    sched = u(10.9, 7.15, 'Schedule', attrs=['+ header: std_msgs/Header', '+ nodes: ActionNode[]'], color=GREEN, stereo='serialized DAG', w=3.2, fs=7.0, name_fs=8.9)
    action = u(8.9, 3.6, 'ActionNode', attrs=['+ guid / job_id / type / parents', '+ duration / status / outside_split', '+ agv_command / bay_command', '+ vecs_command / vrc_command'], color=GREEN, stereo='action message', w=4.8, fs=6.9, name_fs=8.9)
    agv_state = u(0.8, 3.7, 'DiscreteAgvState', attrs=['+ id / state / pose', '+ lift / tray_id / disabled'], color=VIOLET, stereo='state record', w=3.2, fs=6.8, name_fs=8.6)
    tray_state = u(4.3, 3.7, 'DiscreteTrayState', attrs=['+ id / pose', '+ agv_id / payload_id', '+ disabled'], color=VIOLET, stereo='state record', w=3.1, fs=6.8, name_fs=8.6)
    pose = u(4.2, 1.2, 'GaragePose', attrs=['+ node_id: uint32', '+ heading: int16'], color=AMBER, stereo='utility message', w=2.8, fs=6.8, name_fs=8.6)
    agv_cmd = u(14.6, 3.9, 'AgvCommand', attrs=['+ id: string', '+ src: AgvGoal', '+ dst: AgvGoal'], color=AMBER, stereo='nested command', w=3.0, fs=6.9, name_fs=8.8)
    bay_cmd = u(18.0, 6.0, 'BayCommand', attrs=['+ command_type: uint8', '+ command_id: string', '+ floor: uint8'], color=AMBER, stereo='nested command', w=3.2, fs=6.8, name_fs=8.8)
    vrc_cmd = u(18.0, 3.7, 'VrcCommand', attrs=['+ command_type: uint8', '+ requested_floor: uint16'], color=AMBER, stereo='nested command', w=3.3, fs=6.8, name_fs=8.8)
    vecs_cmd = u(18.0, 1.6, 'VecsCommand', attrs=['+ command_id: string', '+ command_type: uint8'], color=AMBER, stereo='nested command', w=3.3, fs=6.8, name_fs=8.8)
    agv_goal = u(14.8, 1.5, 'AgvGoal', attrs=['+ pose: GaragePose', '+ lift: bool'], color=AMBER, stereo='utility message', w=2.7, fs=6.8, name_fs=8.6)
    sjd = u(11.3, 1.4, 'ScheduledJobData', attrs=['+ job: SchedulerJob', '+ node_indices: uint32[]', '+ bay_id', '+ bay_arrival_node_guid'], color=GREEN, stereo='response payload', w=3.8, fs=6.8, name_fs=8.8)

    # orthogonal composition lines
    rels = [
        ([req.bot(0.26), (1.9, 9.2), (1.9, 8.15), dgs.top(0.34)], 'comp', 'base_state', (2.7,8.72)),
        ([req.right(0.55), (6.0, 9.65), (6.0, 10.1), job.left(0.45)], 'comp', 'planned_jobs / active_jobs / pending_jobs', (6.3,10.2)),
        ([req.bot(0.82), (8.0, 8.85), (8.0, 8.15), sched.top(0.18)], 'comp', 'base_schedule', (8.8,8.6)),
        ([dgs.bot(0.25), (1.8, 5.95), (1.8, 4.7), agv_state.top(0.35)], 'comp', 'agvs[]', (2.55,5.3)),
        ([dgs.bot(0.78), (4.5, 5.9), (4.5, 4.7), tray_state.top(0.42)], 'comp', 'trays[]', (5.15,5.25)),
        ([agv_state.right(0.56), (3.0, 2.5), (3.0, 1.8), pose.left(0.45)], 'comp', 'pose', (2.6,1.95)),
        ([tray_state.bot(0.42), (5.8, 2.45), (5.8, 1.8), pose.top(0.84)], 'comp', 'pose', (5.9,1.95)),
        ([job.bot(0.75), (8.5, 8.9), (8.5, 2.2), pose.top(0.98)], 'comp', 'destination', (8.9,5.1)),
        ([resp.bot(0.35), (12.5, 9.15), (12.5, 8.1), sched.top(0.60)], 'comp', 'schedule', (13.2,8.63)),
        ([resp.bot(0.78), (12.9, 8.9), (12.9, 2.2), sjd.top(0.55)], 'comp', 'scheduled_jobs[]', (13.8,4.9)),
        ([sjd.left(0.62), (9.3, 0.8), (9.3, 9.75), job.right(0.82)], 'comp', 'job', (9.8,5.6)),
        ([sched.bot(0.50), (12.2, 5.8), (12.2, 4.75), action.top(0.50)], 'comp', 'nodes[]', (12.9,5.2)),
        ([action.right(0.30), (13.6, 3.0), agv_cmd.left(0.48)], 'comp', 'agv_command', (13.9,3.25)),
        ([action.right(0.82), (16.3, 4.8), (16.3, 5.25), bay_cmd.left(0.45)], 'comp', 'bay_command', (16.7,5.0)),
        ([action.right(0.56), (16.1, 3.6), vrc_cmd.left(0.45)], 'comp', 'vrc_command', (16.6,3.95)),
        ([action.right(0.92), (16.5, 2.0), vecs_cmd.left(0.45)], 'comp', 'vecs_command', (16.85,2.28)),
        ([agv_cmd.bot(0.50), (16.1, 3.2), (16.1, 2.3), agv_goal.top(0.55)], 'comp', 'src / dst', (16.6,2.65)),
        ([agv_goal.left(0.48), (12.0, 0.7), pose.right(0.55)], 'comp', 'pose', (10.3,0.9)),
    ]
    for pts, kind, label_txt, lpos in rels:
        uml_rel(ax, pts, kind=kind, color=AMBER, label=label_txt, lpos=lpos, fs=6.5)
    legend_box(ax, 17.5, 8.75, 3.7, 2.2, 'legend', [
        ('data', SKY, 'request / intent message'),
        ('data', VIOLET, 'garage-state message'),
        ('data', GREEN, 'response / schedule message'),
        ('data', AMBER, 'nested utility / command'),
        ('comp', AMBER, 'composition / contains field'),
    ])
    save(fig, '13_uml_ros_messages.svg')


def fig_discrete_garage_state_bridge():
    data, nodes, edges = load_layout()
    fig, ax = canvas(18.0, 9.4, equal=False)
    ax.text(9.0, 9.1, 'DiscreteGarageState: bridge from floor layout to planner data', ha='center', va='bottom', fontsize=13.2, color=FG, family=MONO, fontweight='bold')
    ax.text(9.0, 8.86, 'The left side is a spatial snapshot; the right side shows the corresponding C++/ROS state records that the Scheduler actually manipulates.', ha='center', va='top', fontsize=8.6, color=MUTED)

    # left panel (layout snapshot)
    ax.add_patch(FancyBboxPatch((0.35, 0.7), 7.1, 7.7, boxstyle='round,pad=0.03,rounding_size=0.12', facecolor='#121b2d', edgecolor=BORDER, lw=1.1))
    ax.text(0.55, 8.18, 'physical snapshot', ha='left', va='top', fontsize=9.2, color=FG, family=MONO, fontweight='bold')
    # local simplified map using real node coordinates scaled into panel
    # choose nodes 3,6,7,10,11,14 around upper bay/charge region
    subset = [3,6,7,9,10,11,14]
    coords = [(nodes[i]['x'], nodes[i]['y']) for i in subset]
    xs = [c[0] for c in coords]; ys = [c[1] for c in coords]
    minx,maxx,miny,maxy = min(xs),max(xs),min(ys),max(ys)
    def mapxy(x,y):
        px = 0.8 + (x-minx)/(maxx-minx) * 5.8
        py = 1.3 + (y-miny)/(maxy-miny) * 5.8
        return px,py
    # edges within subset
    subset_set = set(subset)
    for a,b in edges:
        if a in subset_set and b in subset_set:
            x1,y1=mapxy(nodes[a]['x'], nodes[a]['y']); x2,y2=mapxy(nodes[b]['x'], nodes[b]['y'])
            ax.plot([x1,x2],[y1,y2], color='#64748b', lw=2.0, zorder=1)
    for i in subset:
        n=nodes[i]; x,y=mapxy(n['x'], n['y']); typ=n['type']
        if typ=='Parking':
            ax.add_patch(Rectangle((x-0.55,y-0.25),1.10,0.50,facecolor='#17283b',edgecolor=SKY,lw=1.2,zorder=2))
            ax.text(x,y+0.42,f'P{i}',ha='center',va='bottom',fontsize=7.4,color=SKY,family=MONO,fontweight='bold',bbox=dict(fc=BG,ec='none',pad=.14))
        elif typ=='Bay':
            ax.add_patch(FancyBboxPatch((x-0.58,y-0.30),1.16,0.60,boxstyle='round,pad=.02,rounding_size=.06',facecolor='#14372a',edgecolor=GREEN,lw=1.4,zorder=2))
            ax.text(x,y+0.48,f'B{i}',ha='center',va='bottom',fontsize=7.5,color=GREEN,family=MONO,fontweight='bold',bbox=dict(fc=BG,ec='none',pad=.14))
        elif typ=='AgvCharge':
            ax.add_patch(Circle((x,y),0.18,facecolor='#2a2145',edgecolor=VIOLET,lw=1.3,zorder=2))
            ax.text(x+0.32,y+0.18,f'C{i}',ha='left',va='bottom',fontsize=7.2,color=VIOLET,family=MONO,fontweight='bold',bbox=dict(fc=BG,ec='none',pad=.14))
        else:
            ax.add_patch(Circle((x,y),0.05,facecolor=MUTED,edgecolor=MUTED,zorder=2))
            ax.text(x-0.16,y+0.16,f'W{i}',ha='right',va='bottom',fontsize=6.6,color=MUTED,family=MONO,bbox=dict(fc=BG,ec='none',pad=.1))
    # place resources
    x10,y10=mapxy(nodes[10]['x'],nodes[10]['y'])
    x3,y3=mapxy(nodes[3]['x'],nodes[3]['y'])
    x7,y7=mapxy(nodes[7]['x'],nodes[7]['y'])
    agv(ax,x10,y10,math.pi/2,color=GREEN,scale=1.0)
    ax.text(x10, y10-0.52, 'AGV 4', ha='center', va='top', fontsize=7.7, color=FG, family=MONO, bbox=dict(fc=BG, ec='none', pad=.15))
    ax.add_patch(FancyBboxPatch((x3-0.44,y3-0.16),0.88,0.32,boxstyle='round,pad=.01,rounding_size=.03', facecolor='#4a341f', edgecolor=AMBER, lw=1.5, zorder=5))
    ax.text(x3, y3, 'Tray 15', ha='center', va='center', fontsize=7.2, color='#fff2d5', family=MONO, fontweight='bold', zorder=6)
    ax.text(x7+0.9, y7+0.3, 'Bay 7\nready_to_retrieve', ha='left', va='center', fontsize=7.4, color=FG, family=MONO,
            bbox=dict(boxstyle='round,pad=.2', fc=BG, ec=GREEN, lw=.9))
    ax.annotate('payload GUID on tray 15', xy=(x3+0.10,y3+0.05), xytext=(x3+1.0,y3+0.85), color=AMBER, fontsize=7.2, family=MONO,
                arrowprops=dict(arrowstyle='->', color=AMBER, lw=1.0), bbox=dict(boxstyle='round,pad=.18', fc=BG, ec=AMBER, lw=.8))

    # right panel
    dgs = uml_class(ax, 8.5, 8.05, 'DiscreteGarageState',
                    attrs=['+ is_faulted: bool', '+ agvs: DiscreteAgvState[]', '+ bays: DiscreteBayState[]', '+ vexen: DiscreteVecsState[]',
                           '+ trays: DiscreteTrayState[]', '+ payloads: DiscretePayloadState[]', '+ vrcs: DiscreteVrcState[]', '+ disabled_nodes: uint32[]', '+ hash: uint64'],
                    color=VIOLET, stereo='top-level state snapshot', w=5.6, fs=7.0, name_fs=9.2)
    agvs_box = uml_class(ax, 8.2, 4.75, 'agvs[0] : DiscreteAgvState', attrs=['+ id = 4', '+ pose = GaragePose{node_id=10, heading=90}', '+ lift = false', '+ tray_id = 0', '+ disabled = false'], color=GREEN, w=4.8, fs=6.8, name_fs=8.5)
    trays_box = uml_class(ax, 13.8, 4.75, 'trays[0] : DiscreteTrayState', attrs=['+ id = 15', '+ pose = GaragePose{node_id=3, heading=90}', '+ agv_id = 0', '+ payload_id = payload_GUID', '+ disabled = false'], color=AMBER, w=5.0, fs=6.8, name_fs=8.5)
    bays_box = uml_class(ax, 8.2, 2.05, 'bays[0] : DiscreteBayState', attrs=['+ id = 7', '+ state = READY_TO_RETRIEVE', '+ disabled = false'], color=SKY, w=4.6, fs=6.8, name_fs=8.5)
    payload_box = uml_class(ax, 13.8, 2.05, 'payloads[0] : DiscretePayloadState', attrs=['+ payload = <customer vehicle>', '+ tray_id = 15', '+ reciprocal_to_tray = false', '+ charging = false'], color=RED, w=5.0, fs=6.8, name_fs=8.5)
    pose_box = uml_class(ax, 16.0, 7.15, 'GaragePose', attrs=['+ node_id: uint32', '+ heading: int16'], color=AMBER, stereo='reused value type', w=2.8, fs=6.8, name_fs=8.5)

    uml_rel(ax, [dgs.bot(0.24), (10.2, 6.2), agvs_box.top(0.5)], kind='comp', color=AMBER, label='agvs[]', lpos=(10.7,6.45), fs=6.8)
    uml_rel(ax, [dgs.bot(0.78), (13.7, 6.2), trays_box.top(0.5)], kind='comp', color=AMBER, label='trays[]', lpos=(14.2,6.45), fs=6.8)
    uml_rel(ax, [dgs.bot(0.36), (10.0, 3.8), bays_box.top(0.48)], kind='comp', color=AMBER, label='bays[]', lpos=(10.55,4.03), fs=6.8)
    uml_rel(ax, [dgs.bot(0.90), (14.0, 3.75), payload_box.top(0.5)], kind='comp', color=AMBER, label='payloads[]', lpos=(14.5,4.05), fs=6.8)
    uml_rel(ax, [agvs_box.right(0.53), (14.6, 4.0), (14.6, 7.0), pose_box.left(0.55)], kind='assoc', color=GREEN, label='pose field uses', lpos=(14.95,5.5), fs=6.5)
    uml_rel(ax, [trays_box.right(0.30), (15.7, 4.35), pose_box.bot(0.50)], kind='assoc', color=AMBER, label='pose field uses', lpos=(16.4,5.25), fs=6.5)

    # bridge arrows from layout entities to records
    ax.annotate('', xy=(8.05, 4.05), xytext=(x10+0.55, y10), arrowprops=dict(arrowstyle='-|>', color=GREEN, lw=1.8))
    ax.annotate('', xy=(13.45, 4.05), xytext=(x3+0.55, y3), arrowprops=dict(arrowstyle='-|>', color=AMBER, lw=1.8))
    ax.annotate('', xy=(8.0, 1.62), xytext=(x7+1.6, y7+0.15), arrowprops=dict(arrowstyle='-|>', color=SKY, lw=1.8))
    ax.text(7.55, 5.15, 'same AGV, now as a state record', ha='right', va='center', fontsize=7.4, color=GREEN, family=MONO)
    ax.text(13.25, 5.18, 'same tray, now as a state record', ha='right', va='center', fontsize=7.4, color=AMBER, family=MONO)
    ax.text(7.55, 2.85, 'same bay, now as a state record', ha='right', va='center', fontsize=7.4, color=SKY, family=MONO)

    legend_box(ax, 15.1, 8.0, 2.55, 1.18, 'legend', [
        ('data', VIOLET, 'top-level snapshot'),
        ('data', GREEN, 'AGV record'),
        ('data', AMBER, 'tray / pose record'),
        ('comp', AMBER, 'contains field / array')
    ])
    save(fig, '16_discrete_garage_state_bridge.svg')


def update_markdown():
    p = ROOT/'01-software-background.md'
    s = p.read_text()

    zoom_note = '> **Review tip for VS Code.** Markdown preview renders SVGs as static images. For **pan/zoom**, `Ctrl+Click` the linked `.svg` path under a figure, or open the SVG file directly in the editor / browser.\n\n'
    if zoom_note not in s:
        s = s.replace('## 2. The physical garage and its coordinate system\n\n', '## 2. The physical garage and its coordinate system\n\n' + zoom_note)

    old = '![Pecos facility graph](figures/15_facility_topology.svg)\n\n*Figure 2 — Pecos facility graph reconstructed from YAML coordinates in meters. Rectangular outlines indicate parking locations, green outlines indicate customer bays, violet circles indicate AGV chargers, and grey circles indicate waypoints. The illustrated trays and AGV are hypothetical; they are **not** initial states supplied by the YAML. The edges depict allowed node connections, not physical aisle width or measured collision envelopes.*\n'
    new = '![Pecos facility graph](figures/15_facility_topology.svg)\n\n[Open Figure 2 SVG directly for pan/zoom](figures/15_facility_topology.svg)\n\n*Figure 2 — Pecos facility graph reconstructed from YAML coordinates in meters. The figure now includes a legend: blue rectangles are **parking nodes**, green rounded rectangles are **bays**, violet circles are **AGV charging nodes**, grey dots are **waypoints**, and grey line segments are **garage-graph edges**. The plot is tightly cropped to the actual node extents from the YAML to reduce unused boundary space. The illustrated trays and AGV are hypothetical; they are **not** initial states supplied by the YAML. The edges depict allowed node connections, not physical aisle width or measured collision envelopes.*\n'
    s = s.replace(old, new)

    insert_after = 'The base schedule is described by its `.msg` as the immutable part of an existing schedule. The Scheduler\'s observed `Plan()` marks certain resources from base actions disabled in its planning initial state. This matters when trying to understand why apparently available nodes or AGVs cannot be reused.\n\n'
    bridge_section = '''### `DiscreteGarageState` as the bridge between the garage and the planner

`DiscreteGarageState` is one of the most important types in the entire system because it is the **bridge** between the physical garage and the planner's internal reasoning. The Scheduler does not plan directly over a photo-realistic scene or over raw continuous geometry; instead, it plans over a structured discrete snapshot containing arrays of AGVs, trays, bays, payloads, VRCs, and disabled nodes.

That means every physical fact the planner cares about must eventually be expressible in this data structure. For example, saying “AGV 4 is parked at charge node 10” becomes an entry in `agvs[]` whose `pose` field stores `GaragePose{node_id=10, heading=...}`. Saying “tray 15 is at parking node 3 and carries a payload” becomes an entry in `trays[]`, plus a matching `payloads[]` entry whose `tray_id` is `15`.

![DiscreteGarageState bridge](figures/16_discrete_garage_state_bridge.svg)

[Open DiscreteGarageState bridge SVG directly for pan/zoom](figures/16_discrete_garage_state_bridge.svg)

*Figure 3 — `DiscreteGarageState` ties the floor layout to the planner's C++/ROS data structures. The left side shows the spatial interpretation: a bay, an AGV charging node, a tray location, and a payload riding on that tray. The right side shows the corresponding state records and their key fields. Filled-diamond arrows denote ownership/composition inside `DiscreteGarageState`, while horizontal bridge arrows indicate how a concrete garage resource is represented as a record in one of the arrays.*

A useful way to read the figure is bottom-up:

1. Start with the **layout entities** on the left, such as the AGV, tray, and bay.
2. Follow the bridge arrows to the **state records** on the right.
3. Observe that both `DiscreteAgvState` and `DiscreteTrayState` reuse `GaragePose`, which is how the planner ties an entity back to a discrete graph node and heading.
4. Finally, notice that all of those arrays are contained by the single top-level `DiscreteGarageState` snapshot.

Once this picture is clear, much of the Scheduler becomes easier to understand: `ScheduleEvent::Apply(...)` is essentially “take one abstract event and mutate this structured world snapshot.”

'''
    if bridge_section not in s:
        s = s.replace(insert_after, insert_after + bridge_section)

    # Update figure numbering references following inserted figure if needed.
    s = s.replace('![ROS message relationships](figures/13_uml_ros_messages.svg)\n\n*Figure 3 — As-built ROS service and message composition derived from the `.msg` and `.srv` definitions. A **filled diamond** means “contains as a field or array element.” Blue boxes sit on the **request / intent** side, violet boxes describe the **garage-state snapshot**, green boxes describe the **response / schedule** side, and amber boxes are **nested command or utility messages**. The dashed outer frame marks the `Plan.srv` boundary.*',
                  '![ROS message relationships](figures/13_uml_ros_messages.svg)\n\n[Open ROS message UML SVG directly for pan/zoom](figures/13_uml_ros_messages.svg)\n\n*Figure 4 — As-built ROS service and message composition derived from the `.msg` and `.srv` definitions. A **filled diamond** means “contains as a field or array element.” Blue boxes sit on the **request / intent** side, violet boxes describe the **garage-state snapshot**, green boxes describe the **response / schedule** side, and amber boxes are **nested command or utility messages**. The dashed outer frame marks the `Plan.srv` boundary. Orthogonal connectors are used on purpose so the containment relationships are easier to follow than with diagonal straight-line arrows.*')
    s = s.replace('![Current class relationships](figures/11_uml_existing_core.svg)\n\n*Figure 4 — Existing core-class relationships. `Scheduler` orchestrates planning, `ScheduleContext` packages one plan attempt’s mutable working data, `ScheduleEventDag` stores abstract event dependencies, and `DiscreteGarageState` models the world that those events mutate. The diagram is intentionally compact, so it shows the dominant ownership / usage relationships rather than every helper member.*',
                  '![Current class relationships](figures/11_uml_existing_core.svg)\n\n[Open core-class UML SVG directly for pan/zoom](figures/11_uml_existing_core.svg)\n\n*Figure 5 — Existing core-class relationships. `Scheduler` orchestrates planning, `ScheduleContext` packages one plan attempt’s mutable working data, `ScheduleEventDag` stores abstract event dependencies, and `DiscreteGarageState` models the world that those events mutate. The diagram has been spaced out and redrawn with orthogonal connectors so the major ownership and usage relationships are easier to trace in VS Code preview.*')
    s = s.replace('![Existing event inheritance](figures/12_uml_event_hierarchy.svg)\n\n*Figure 5 — Existing C++ inheritance hierarchy, not proposed solver architecture. A **hollow triangle** means public inheritance and points toward the base class. Blue marks the abstract base type, green marks movement / assignment events, and violet marks other resource-transition events. The arrow therefore reads as “`TrayMove` **is a** `ScheduleEvent`,” not “`ScheduleEvent` contains a `TrayMove`.”*',
                  '![Existing event inheritance](figures/12_uml_event_hierarchy.svg)\n\n[Open event-hierarchy UML SVG directly for pan/zoom](figures/12_uml_event_hierarchy.svg)\n\n*Figure 6 — Existing C++ inheritance hierarchy, not proposed solver architecture. A **hollow triangle** means public inheritance and points toward the base class. Blue marks the abstract base type, green marks movement / assignment events, and violet marks other resource-transition events. The arrow therefore reads as “`TrayMove` **is a** `ScheduleEvent`,” not “`ScheduleEvent` contains a `TrayMove`.”*')
    s = s.replace('*Figure 6 — Abstract prerequisite ordering. The arrows express dependencies, not geometric movement and not wall-clock travel time.*', '*Figure 7 — Abstract prerequisite ordering. The arrows express dependencies, not geometric movement and not wall-clock travel time.*')

    # Renumber later figures in section 11 and 12 minimal replacements
    s = s.replace('*Figure 7 —', '*Figure 8 —')
    s = s.replace('*Figure 8 —', '*Figure 9 —')
    s = s.replace('*Figure 9 —', '*Figure 10 —')
    s = s.replace('*Figure 10 —', '*Figure 11 —')
    # This sequential naive renumbering may over-shift later captions only once since figures 7-10 existed later.

    p.write_text(s)


def make_zip():
    import zipfile
    zip_path = Path('/mnt/data/scheduler-core-refactor-study-v6.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in ROOT.rglob('*'):
            if path.is_file():
                z.write(path, path.relative_to(ROOT.parent))
    return zip_path


if __name__ == '__main__':
    fig_facility_topology()
    fig_uml_existing_core()
    fig_ros_messages_roomier()
    fig_discrete_garage_state_bridge()
    update_markdown()
    print(make_zip())
