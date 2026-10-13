from pathlib import Path
import sys, math, yaml, zipfile
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon, Circle
from matplotlib.lines import Line2D

ROOT = Path('/mnt/data/scheduler_core_refactor')
FIG = ROOT/'figures'
SRC = ROOT/'sources'/'5675_pecos_combined.yaml'
sys.path.insert(0, str(ROOT/'scripts'))
from figstyle import plt, BG, CARD, FG, MUTED, BORDER, SKY, GREEN, AMBER, RED, VIOLET, MONO
from draw import canvas, agv

# ---------- shared light UML helpers (mimic the reference style more closely)
UML_BG = '#e7f4fb'
UML_HEAD = '#7ec2ea'
UML_LINE = '#222222'
UML_NOTE = '#c04d4d'

class Box:
    def __init__(self, x0,y0,x1,y1):
        self.x0,self.y0,self.x1,self.y1 = x0,y0,x1,y1
        self.cx=(x0+x1)/2; self.cy=(y0+y1)/2
    def top(self, frac=0.5):
        return (self.x0+(self.x1-self.x0)*frac, self.y1)
    def bot(self, frac=0.5):
        return (self.x0+(self.x1-self.x0)*frac, self.y0)
    def left(self, frac=0.5):
        return (self.x0, self.y0+(self.y1-self.y0)*frac)
    def right(self, frac=0.5):
        return (self.x1, self.y0+(self.y1-self.y0)*frac)


def lclass(ax, x, ytop, name, attrs=(), methods=(), stereo=None, w=3.8, fs=8.5, name_fs=10.2, italic=False):
    lh = 0.26
    header_h = 0.56 + (0.24 if stereo else 0)
    body_lines = len(attrs) + len(methods)
    body_h = body_lines*lh + (0.12 if attrs else 0) + (0.12 if methods else 0)
    h = header_h + body_h + 0.08
    y = ytop - h
    ax.add_patch(Rectangle((x,y), w, h, facecolor=UML_BG, edgecolor=UML_LINE, lw=1.1, zorder=2))
    ax.add_patch(Rectangle((x, ytop-header_h), w, header_h, facecolor=UML_HEAD, edgecolor=UML_LINE, lw=1.1, zorder=3))
    t = ytop-0.08
    if stereo:
        ax.text(x+w/2, t, f'<<{stereo}>>', ha='center', va='top', fontsize=fs-0.6, color=UML_LINE, family=MONO, zorder=5)
        t -= 0.23
    ax.text(x+w/2, t, name, ha='center', va='top', fontsize=name_fs, color=UML_LINE, family=MONO,
            fontweight='bold', style='italic' if italic else 'normal', zorder=5)
    yy = ytop-header_h-0.06
    if attrs:
        for line in attrs:
            ax.text(x+0.10, yy, line.replace(' ','\u00a0'), ha='left', va='top', fontsize=fs, color=UML_LINE, family=MONO, zorder=5)
            yy -= lh
        if methods:
            ax.plot([x, x+w], [yy+0.05, yy+0.05], color=UML_LINE, lw=0.8, zorder=4)
            yy -= 0.08
    for line in methods:
        ax.text(x+0.10, yy, line.replace(' ','\u00a0'), ha='left', va='top', fontsize=fs, color=UML_LINE, family=MONO, zorder=5)
        yy -= lh
    return Box(x,y,x+w,ytop)


def _arrow_head(ax, tip, frm, kind='assoc', color=UML_LINE, size=0.18):
    import numpy as np
    tip = np.asarray(tip,float); frm = np.asarray(frm,float)
    d = tip-frm; d = d/(np.linalg.norm(d)+1e-12)
    n = np.array([-d[1], d[0]])
    if kind == 'inh':
        pts=[tip, tip-d*size*1.2+n*size*0.7, tip-d*size*1.2-n*size*0.7]
        ax.add_patch(Polygon(pts, closed=True, facecolor='white', edgecolor=color, lw=1.1, zorder=6))
        return tuple(tip-d*size*1.2)
    if kind == 'comp':
        pts=[tip, tip-d*size+n*size*0.55, tip-d*size*2, tip-d*size-n*size*0.55]
        ax.add_patch(Polygon(pts, closed=True, facecolor='black', edgecolor=color, lw=1.0, zorder=6))
        return tuple(tip-d*size*2)
    if kind == 'agg':
        pts=[tip, tip-d*size+n*size*0.55, tip-d*size*2, tip-d*size-n*size*0.55]
        ax.add_patch(Polygon(pts, closed=True, facecolor='white', edgecolor=color, lw=1.0, zorder=6))
        return tuple(tip-d*size*2)
    # assoc/dep open arrow
    ax.plot([tip[0], tip[0]-d[0]*size+n[0]*size*0.55], [tip[1], tip[1]-d[1]*size+n[1]*size*0.55], color=color, lw=1.0, zorder=6)
    ax.plot([tip[0], tip[0]-d[0]*size-n[0]*size*0.55], [tip[1], tip[1]-d[1]*size-n[1]*size*0.55], color=color, lw=1.0, zorder=6)
    return tuple(tip)


def lrel(ax, pts, kind='assoc', dashed=False, label=None, lpos=None, fs=7.5):
    pts=[tuple(p) for p in pts]
    p=list(pts)
    if kind in ('assoc','dep','inh'):
        p[-1]=_arrow_head(ax, pts[-1], pts[-2], kind='assoc' if kind in ('assoc','dep') else 'inh')
    elif kind in ('comp','agg'):
        p[0]=_arrow_head(ax, pts[0], pts[1], kind=kind)
    xs,ys=zip(*p)
    ax.plot(xs,ys,color=UML_LINE,lw=1.05,ls='--' if dashed else '-',zorder=4)
    if label:
        lx,ly=lpos if lpos else ((pts[0][0]+pts[-1][0])/2,(pts[0][1]+pts[-1][1])/2)
        ax.text(lx,ly,label,ha='center',va='center',fontsize=fs,color=UML_NOTE,family=MONO,zorder=10,
                bbox=dict(fc='white',ec='none',pad=.08))


def legend_box_light(ax, x,y,w,h,title, lines):
    ax.add_patch(Rectangle((x,y), w,h, facecolor='white', edgecolor='#777', lw=1.0, zorder=1))
    ax.text(x+0.12, y+h-0.12, title, ha='left', va='top', fontsize=8.5, color=UML_LINE, family=MONO, fontweight='bold')
    yy=y+h-0.40
    for kind,text in lines:
        if kind=='comp':
            ax.add_patch(Polygon([(x+0.16,yy),(x+0.28,yy+0.08),(x+0.40,yy),(x+0.28,yy-0.08)], closed=True, facecolor='black', edgecolor='black', lw=1))
            ax.plot([x+0.40,x+0.62],[yy,yy],color='black',lw=1)
        elif kind=='assoc':
            ax.plot([x+0.16,x+0.58],[yy,yy],color='black',lw=1)
            _arrow_head(ax,(x+0.58,yy),(x+0.30,yy),'assoc',size=0.12)
        elif kind=='inh':
            ax.plot([x+0.16,x+0.52],[yy,yy],color='black',lw=1)
            _arrow_head(ax,(x+0.58,yy),(x+0.42,yy),'inh',size=0.12)
        elif kind=='msg':
            ax.add_patch(Rectangle((x+0.12,yy-0.10),0.46,0.20,facecolor=UML_BG,edgecolor='black',lw=1))
            ax.add_patch(Rectangle((x+0.12,yy),0.46,0.10,facecolor=UML_HEAD,edgecolor='black',lw=1))
        ax.text(x+0.74,yy,text,ha='left',va='center',fontsize=7.8,color=UML_LINE,family=MONO)
        yy -= 0.28


# ---------- data and facility drawing

def load_layout():
    data = yaml.safe_load(SRC.read_text())
    nodes = {n['id']: n for n in data['nodes']}
    edges = [(e['src'], e['dst']) for e in data['edges']]
    return data,nodes,edges


def draw_facility(ax, nodes, edges, scale=1.0, crop=None, alpha=1.0, label_fs=8.5, legend=False):
    if crop is None:
        xs=[n['x'] for n in nodes.values()]; ys=[n['y'] for n in nodes.values()]
        xmin,xmax=min(xs)-0.5,max(xs)+0.8
        ymin,ymax=min(ys)-0.6,max(ys)+0.8
    else:
        xmin,xmax,ymin,ymax=crop
    ax.set_xlim(xmin,xmax); ax.set_ylim(ymin,ymax); ax.set_aspect('equal')
    ax.set_facecolor('#0c1730')
    for spine in ax.spines.values(): spine.set_color('#5e6c84')
    ax.grid(color='#26334b', linewidth=.45, alpha=.30)
    ax.tick_params(colors=MUTED, labelsize=8*scale)
    ax.set_xlabel('x [m]', color=MUTED, family=MONO, fontsize=11*scale)
    ax.set_ylabel('y [m]', color=MUTED, family=MONO, fontsize=11*scale)
    for a,b in edges:
        p,q=nodes[a],nodes[b]
        ax.plot([p['x'],q['x']],[p['y'],q['y']],color='#909db3',lw=2.1*scale,alpha=0.82*alpha,zorder=1)
    # draw nodes by type
    for i,n in nodes.items():
        x,y,typ=n['x'],n['y'],n['type']
        if typ=='Parking':
            ax.add_patch(Rectangle((x-1.8,y-0.78),3.6,1.56,facecolor='#20314c',edgecolor='#6ab6ff',lw=1.5*scale,alpha=alpha,zorder=2))
            ax.text(x,y+0.98,f'P{i}',ha='center',va='bottom',fontsize=label_fs*scale,color='#9dd1ff',family=MONO,fontweight='bold',zorder=5,
                    bbox=dict(fc='#0c1730',ec='none',pad=.15,alpha=.88))
        elif typ=='Bay':
            ax.add_patch(FancyBboxPatch((x-1.95,y-0.88),3.9,1.76,boxstyle='round,pad=0.02,rounding_size=0.16',facecolor='#23402d',edgecolor='#76d06b',lw=1.8*scale,alpha=alpha,zorder=2))
            ax.plot([x+1.95,x+1.95],[y-0.6,y+0.6],color='#f3b34a',lw=3.0*scale,alpha=alpha,zorder=3)
            ax.text(x-0.05,y+1.02,f'B{i}',ha='center',va='bottom',fontsize=label_fs*scale,color='#8ee57e',family=MONO,fontweight='bold',zorder=5,
                    bbox=dict(fc='#0c1730',ec='none',pad=.15,alpha=.88))
        elif typ=='AgvCharge':
            ax.add_patch(Circle((x,y),0.48,facecolor='#392852',edgecolor='#b19cff',lw=1.8*scale,alpha=alpha,zorder=3))
            ax.text(x+0.62,y+0.28,f'C{i}',ha='left',va='bottom',fontsize=label_fs*scale,color='#c8bdff',family=MONO,fontweight='bold',zorder=5,
                    bbox=dict(fc='#0c1730',ec='none',pad=.15,alpha=.88))
        else:
            ax.add_patch(Circle((x,y),0.12,facecolor='#c2cbdb',edgecolor='#c2cbdb',alpha=alpha,zorder=3))
            ax.text(x-0.22,y+0.22,f'W{i}',ha='right',va='bottom',fontsize=(label_fs-1.0)*scale,color='#b4bfd0',family=MONO,zorder=5,
                    bbox=dict(fc='#0c1730',ec='none',pad=.1,alpha=.88))
    if legend:
        lx,ly = xmax-8.4, ymin+0.9
        box_w, box_h = 7.6, 2.4
        ax.add_patch(FancyBboxPatch((lx,ly),box_w,box_h,boxstyle='round,pad=.05,rounding_size=.12',facecolor='#15223b',edgecolor='#66748b',lw=1.0,zorder=20))
        ax.text(lx+0.18,ly+box_h-0.18,'legend',ha='left',va='top',fontsize=10.5,color='white',family=MONO,fontweight='bold',zorder=21)
        entries=[('parking','#6ab6ff','parking node / tray stall'),('bay','#76d06b','bay node / customer handoff'),('charge','#b19cff','AGV charging node'),('way','#c2cbdb','waypoint / connector node'),('edge','#909db3','undirected garage-graph edge')]
        yy=ly+box_h-0.55
        for kind,col,text in entries:
            if kind=='parking':
                ax.add_patch(Rectangle((lx+0.20,yy-0.12),0.35,0.18,facecolor='#20314c',edgecolor=col,lw=1.2,zorder=21))
            elif kind=='bay':
                ax.add_patch(FancyBboxPatch((lx+0.20,yy-0.13),0.36,0.20,boxstyle='round,pad=.01,rounding_size=.03',facecolor='#23402d',edgecolor=col,lw=1.2,zorder=21))
            elif kind=='charge':
                ax.add_patch(Circle((lx+0.38,yy-0.04),0.09,facecolor='#392852',edgecolor=col,lw=1.2,zorder=21))
            elif kind=='way':
                ax.add_patch(Circle((lx+0.38,yy-0.04),0.05,facecolor=col,edgecolor=col,zorder=21))
            else:
                ax.plot([lx+0.20,lx+0.56],[yy-0.04,yy-0.04],color=col,lw=2,zorder=21)
            ax.text(lx+0.76,yy-0.04,text,ha='left',va='center',fontsize=9.0,color='#d6dbe6',family=MONO,zorder=21)
            yy -= 0.36


def save(fig,name):
    fig.savefig(FIG/name, facecolor='white' if 'uml' in name else BG, bbox_inches='tight', pad_inches=0.05, metadata={'Date':None})
    plt.close(fig)

# ---------- figures

def fig_facility_topology():
    _,nodes,edges = load_layout()
    fig,ax = plt.subplots(figsize=(13.8,10.4))
    fig.patch.set_facecolor(BG)
    draw_facility(ax,nodes,edges,legend=True,label_fs=8.8)
    ax.set_title('Pecos facility topology', loc='left', color='white', fontsize=18, family=MONO, fontweight='bold', pad=14)
    ax.text(0.0,-0.10,'Larger labels and legend improve readability in VS Code Markdown preview. The SVG still preserves detail if you open it separately.',
            transform=ax.transAxes, ha='left', va='top', fontsize=10, color=MUTED, family=MONO)
    fig.subplots_adjust(left=.08,right=.985,top=.91,bottom=.14)
    save(fig,'15_facility_topology.svg')


def fig_uml_existing_core():
    fig,ax = plt.subplots(figsize=(16.6,10.8))
    ax.set_facecolor('white'); fig.patch.set_facecolor('white')
    ax.set_xlim(0,16.6); ax.set_ylim(0,10.8); ax.axis('off')
    ax.text(8.3,10.55,'Existing core planner relationships',ha='center',va='top',fontsize=14.5,color=UML_LINE,family=MONO,fontweight='bold')
    ax.text(8.3,10.25,'The connector style intentionally follows conventional UML: orthogonal lines, hollow triangles for inheritance, and diamonds for ownership.',ha='center',va='top',fontsize=8.8,color='#555',family=MONO)
    sched=lclass(ax,5.9,9.35,'Scheduler',attrs=['- layout_: GarageLayout','- gg_: GarageGraph','- table_: CollisionTable','- motion_cost_: MotionCostModel','- logger_: rclcpp::Logger'],methods=['+ Plan(request)','+ DoTrayAssignments(ctx)','+ DoAgvAssignments(ctx)','+ PlanMotions(ctx)'],stereo='orchestrator',w=4.8,fs=7.6,name_fs=9.5)
    ctx=lclass(ax,0.7,7.35,'ScheduleContext',attrs=['+ initial_state: DiscreteGarageState','+ events: ScheduleEventDag','+ scheduled_jobs: vector<...>','+ first_tray_event: map<...>','+ last_entity_event: map<...>'],methods=['+ PushBackScheduledJob(job)'],stereo='mutable per-plan state',w=4.8,fs=7.0,name_fs=9.1)
    dag=lclass(ax,6.0,7.35,'ScheduleEventDag',attrs=['+ vertices: shared_ptr<ScheduleEvent>','+ edges: dependency links'],methods=['+ AddEvent(ev)','+ AddDependency(a,b)','+ Reduce()','+ GetTopologicalOrdering()'],stereo='dependency graph',w=4.5,fs=7.0,name_fs=9.1)
    state=lclass(ax,11.3,7.35,'DiscreteGarageState',attrs=['+ agvs / bays / trays / payloads / vrcs','+ disabled_nodes','+ hash'],methods=['+ GetAgv(id)','+ GetTray(id)','+ OnEvent(change)'],stereo='world state model',w=4.5,fs=7.0,name_fs=9.0)
    ev=lclass(ax,5.9,4.25,'ScheduleEvent',attrs=['# job_index_: size_t','# type_: ScheduleEventType'],methods=['+ Apply(state) const = 0','+ GetGarageEntityId() const = 0'],stereo='abstract base class',w=4.8,fs=7.1,name_fs=9.2,italic=True)
    tm=lclass(ax,0.7,1.9,'TrayMove',attrs=['- tray_id_: optional<uint16_t>','- dest_: optional<GaragePoseMsg>','- agv_id_: optional<uint16_t>'],methods=['+ Assigned() const','+ SetDest(dest)'],w=3.9,fs=6.8,name_fs=8.7)
    am=lclass(ax,5.5,1.9,'AgvMove',attrs=['- discrete_change_: variant<...>'],methods=['+ Apply(state) const'],w=3.0,fs=6.8,name_fs=8.7)
    bt=lclass(ax,9.4,1.9,'BayTransition',attrs=['- command_: BayCommandMsg'],methods=['+ Apply(state) const'],w=3.2,fs=6.8,name_fs=8.7)
    vt=lclass(ax,13.4,1.9,'VecsTransition / VrcTransition',attrs=['- state_change_: ...'],methods=['+ Apply(state) const'],w=3.0,fs=6.5,name_fs=8.0)
    # relationships
    lrel(ax,[sched.bot(0.25),(7.1,8.2),(4.8,8.2),ctx.top(0.8)],kind='assoc',label='uses / mutates',lpos=(5.9,8.42))
    lrel(ax,[sched.bot(0.5),(8.3,8.15),dag.top(0.5)],kind='assoc',label='builds',lpos=(8.9,8.38))
    lrel(ax,[sched.bot(0.82),(10.3,8.2),(13.5,8.2),state.top(0.20)],kind='assoc',label='queries / replays',lpos=(12.0,8.45))
    lrel(ax,[ctx.right(0.48),(5.8,6.35),dag.left(0.5)],kind='comp',label='events',lpos=(4.8,6.60))
    lrel(ax,[ctx.right(0.18),(5.1,5.55),(10.8,5.55),state.left(0.22)],kind='comp',label='initial_state',lpos=(8.0,5.82))
    lrel(ax,[dag.bot(0.50),(8.25,5.2),(8.25,4.45),ev.top(0.50)],kind='comp',label='vertex payload type',lpos=(9.45,4.85))
    spine_y=3.15
    ax.plot([ev.cx,ev.cx],[ev.y0,spine_y],color=UML_LINE,lw=1.0)
    ax.plot([tm.cx,vt.cx],[spine_y,spine_y],color=UML_LINE,lw=1.0)
    for child in [tm,am,bt,vt]:
        x=child.cx
        ax.plot([x,x],[spine_y,child.y1],color=UML_LINE,lw=1.0)
        _arrow_head(ax,(x,child.y1),(x,spine_y),'inh',size=0.14)
    ax.text(12.75,3.35,'Generalization',ha='left',va='bottom',fontsize=8.6,color=UML_NOTE,family=MONO,fontweight='bold')
    ax.annotate('',xy=(13.0,3.12),xytext=(12.2,3.12),arrowprops=dict(arrowstyle='->',color=UML_NOTE,lw=1.0,ls='--'))
    legend_box_light(ax,12.4,8.55,3.7,1.75,'legend',[('assoc','association / usage'),('comp','composition / member ownership'),('inh','inheritance / is-a')])
    save(fig,'11_uml_existing_core.svg')


def fig_ros_messages():
    fig,ax = plt.subplots(figsize=(20.0,12.2))
    ax.set_facecolor('white'); fig.patch.set_facecolor('white')
    ax.set_xlim(0,20.0); ax.set_ylim(0,12.2); ax.axis('off')
    ax.text(10.0,12.0,'As-built ROS service and message composition',ha='center',va='top',fontsize=14.5,color=UML_LINE,family=MONO,fontweight='bold')
    ax.text(10.0,11.72,'This is a composition diagram, not a C++ inheritance diagram. Black diamonds mark contained fields or arrays.',ha='center',va='top',fontsize=8.7,color='#555',family=MONO)
    # outer frame
    ax.add_patch(Rectangle((0.3,0.45),19.4,11.0,facecolor='none',edgecolor='#888',lw=1.0,ls='--'))
    ax.text(0.45,11.2,'srv/Plan.srv',ha='left',va='bottom',fontsize=9.2,color=UML_LINE,family=MONO,fontweight='bold')
    req=lclass(ax,0.6,10.9,'PlanRequest',attrs=['+ id: Guid','+ base_state: DiscreteGarageState','+ base_schedule: Schedule','+ planned_jobs: SchedulerJob[]','+ active_jobs: SchedulerJob[]','+ pending_jobs: SchedulerJob[]'],stereo='request message',w=4.2,fs=7.2,name_fs=9.2)
    job=lclass(ax,5.5,10.9,'SchedulerJob',attrs=['+ type / state / guid','+ agv_id / bay_id / tray_id','+ payload_id: Guid','+ destination: GaragePose','+ allow_reciprocal: bool','+ retain_job / needs_bay_in_retrieve'],stereo='request payload',w=4.6,fs=7.0,name_fs=9.0)
    resp=lclass(ax,11.1,10.9,'PlanResponse',attrs=['+ success: bool','+ message: string','+ id: Guid','+ schedule: Schedule','+ scheduled_jobs: ScheduledJobData[]'],stereo='response message',w=3.8,fs=7.2,name_fs=9.2)
    dgs=lclass(ax,0.8,7.4,'DiscreteGarageState',attrs=['+ agvs: DiscreteAgvState[]','+ bays: DiscreteBayState[]','+ vexen: DiscreteVecsState[]','+ trays: DiscreteTrayState[]','+ payloads: DiscretePayloadState[]','+ vrcs: DiscreteVrcState[]','+ disabled_nodes: uint32[]','+ hash: uint64'],stereo='state snapshot',w=4.3,fs=6.8,name_fs=8.8)
    sched=lclass(ax,10.6,7.5,'Schedule',attrs=['+ header: std_msgs/Header','+ nodes: ActionNode[]'],stereo='serialized DAG',w=3.1,fs=6.9,name_fs=8.8)
    action=lclass(ax,8.0,4.1,'ActionNode',attrs=['+ guid / job_id / type / parents','+ duration / status / outside_split','+ agv_command / bay_command','+ vecs_command / vrc_command'],stereo='action message',w=4.8,fs=6.8,name_fs=8.7)
    agv_state=lclass(ax,0.8,4.3,'DiscreteAgvState',attrs=['+ id / state / pose','+ lift / tray_id / disabled'],stereo='state record',w=3.2,fs=6.7,name_fs=8.4)
    tray_state=lclass(ax,4.5,4.3,'DiscreteTrayState',attrs=['+ id / pose','+ agv_id / payload_id','+ disabled'],stereo='state record',w=3.0,fs=6.7,name_fs=8.4)
    pose=lclass(ax,4.2,1.8,'GaragePose',attrs=['+ node_id: uint32','+ heading: int16'],stereo='utility message',w=2.8,fs=6.7,name_fs=8.4)
    agv_cmd=lclass(ax,14.4,4.3,'AgvCommand',attrs=['+ id: string','+ src: AgvGoal','+ dst: AgvGoal'],stereo='nested command',w=3.0,fs=6.8,name_fs=8.5)
    bay_cmd=lclass(ax,17.5,6.4,'BayCommand',attrs=['+ command_type: uint8','+ command_id: string','+ floor: uint8'],stereo='nested command',w=2.2,fs=6.5,name_fs=8.2)
    vrc_cmd=lclass(ax,17.3,4.15,'VrcCommand',attrs=['+ command_type: uint8','+ requested_floor: uint16'],stereo='nested command',w=2.4,fs=6.3,name_fs=8.1)
    vecs_cmd=lclass(ax,17.1,1.85,'VecsCommand',attrs=['+ command_id: string','+ command_type: uint8'],stereo='nested command',w=2.6,fs=6.3,name_fs=8.1)
    agv_goal=lclass(ax,14.6,1.85,'AgvGoal',attrs=['+ pose: GaragePose','+ lift: bool'],stereo='utility message',w=2.6,fs=6.5,name_fs=8.2)
    sjd=lclass(ax,11.0,1.85,'ScheduledJobData',attrs=['+ job: SchedulerJob','+ node_indices: uint32[]','+ bay_id','+ bay_arrival_node_guid'],stereo='response payload',w=3.8,fs=6.6,name_fs=8.4)
    # relationships
    lrel(ax,[req.bot(0.24),(1.7,8.95),(1.7,8.0),dgs.top(0.34)],kind='comp',label='base_state',lpos=(2.7,8.42))
    lrel(ax,[req.right(0.56),(5.0,10.15),job.left(0.45)],kind='comp',label='planned_jobs / active_jobs / pending_jobs',lpos=(5.8,10.35),fs=6.8)
    lrel(ax,[req.bot(0.84),(8.3,9.0),(8.3,7.95),sched.top(0.18)],kind='comp',label='base_schedule',lpos=(9.05,8.46))
    lrel(ax,[dgs.bot(0.24),(1.8,6.0),(1.8,5.0),agv_state.top(0.40)],kind='comp',label='agvs[]',lpos=(2.6,5.45))
    lrel(ax,[dgs.bot(0.78),(5.0,6.0),(5.0,5.0),tray_state.top(0.42)],kind='comp',label='trays[]',lpos=(5.95,5.45))
    lrel(ax,[agv_state.right(0.58),(3.7,3.1),(3.7,2.3),pose.left(0.42)],kind='comp',label='pose',lpos=(3.15,2.52))
    lrel(ax,[tray_state.bot(0.40),(5.6,3.0),(5.6,2.25),pose.top(0.82)],kind='comp',label='pose',lpos=(5.95,2.55))
    lrel(ax,[job.bot(0.76),(8.4,8.7),(8.4,2.45),pose.top(0.98)],kind='comp',label='destination',lpos=(8.9,5.6))
    lrel(ax,[resp.bot(0.35),(12.4,9.0),(12.4,7.95),sched.top(0.62)],kind='comp',label='schedule',lpos=(13.05,8.45))
    lrel(ax,[resp.bot(0.78),(13.0,8.7),(13.0,2.35),sjd.top(0.55)],kind='comp',label='scheduled_jobs[]',lpos=(13.85,5.55))
    lrel(ax,[sjd.left(0.62),(9.7,1.1),(9.7,10.2),job.right(0.82)],kind='comp',label='job',lpos=(10.15,5.95))
    lrel(ax,[sched.bot(0.50),(12.15,6.2),(12.15,5.0),action.top(0.50)],kind='comp',label='nodes[]',lpos=(12.95,5.55))
    lrel(ax,[action.right(0.34),(13.7,3.25),agv_cmd.left(0.50)],kind='comp',label='agv_command',lpos=(14.2,3.55),fs=6.7)
    lrel(ax,[action.right(0.82),(16.2,5.2),(16.2,5.65),bay_cmd.left(0.50)],kind='comp',label='bay_command',lpos=(16.7,5.4),fs=6.7)
    lrel(ax,[action.right(0.55),(16.0,3.95),vrc_cmd.left(0.50)],kind='comp',label='vrc_command',lpos=(16.6,4.2),fs=6.7)
    lrel(ax,[action.right(0.92),(16.4,1.95),vecs_cmd.left(0.50)],kind='comp',label='vecs_command',lpos=(16.7,2.2),fs=6.7)
    lrel(ax,[agv_cmd.bot(0.50),(15.9,3.35),(15.9,2.45),agv_goal.top(0.55)],kind='comp',label='src / dst',lpos=(16.4,2.75),fs=6.7)
    lrel(ax,[agv_goal.left(0.50),(13.1,1.0),pose.right(0.55)],kind='comp',label='pose',lpos=(11.0,1.15),fs=6.7)
    legend_box_light(ax,16.1,8.7,3.2,2.0,'legend',[('msg','message type'),('comp','contains field / array'),('assoc','direction of read/use in captions')])
    save(fig,'13_uml_ros_messages.svg')


def fig_discrete_garage_state_bridge():
    _,nodes,edges = load_layout()
    fig = plt.figure(figsize=(18.0,10.2), facecolor=BG)
    gs = fig.add_gridspec(1,2,width_ratios=[1.15,0.85],wspace=0.08)
    axL = fig.add_subplot(gs[0,0])
    axR = fig.add_subplot(gs[0,1])
    # left reuses the facility figure style, but highlight specific resources
    draw_facility(axL,nodes,edges,legend=False,label_fs=8.4)
    axL.set_title('DiscreteGarageState mapped back onto the Pecos facility', loc='left', color='white', fontsize=16, family=MONO, fontweight='bold', pad=10)
    # choose example entities
    p_agv = nodes[10]; p_tray = nodes[3]; p_bay = nodes[7]; p_payload = nodes[3]
    agv(axL,p_agv['x'],p_agv['y']+0.05,math.pi/2,color=GREEN,scale=1.15,fill='#172a1a',lw=1.5)
    axL.text(p_agv['x']+0.9,p_agv['y']+1.1,'AGV 4',ha='left',va='bottom',fontsize=10,color='#d6ffe0',family=MONO,fontweight='bold',bbox=dict(fc='#0c1730',ec=GREEN,lw=.8,pad=.18))
    axL.add_patch(FancyBboxPatch((p_tray['x']-0.55,p_tray['y']-0.18),1.10,0.36,boxstyle='round,pad=.02,rounding_size=.04',facecolor='#5a3d19',edgecolor=AMBER,lw=1.6,zorder=6))
    axL.text(p_tray['x'],p_tray['y'],'Tray 15',ha='center',va='center',fontsize=9.0,color='#fff2d5',family=MONO,fontweight='bold',zorder=7)
    axL.text(p_bay['x']+2.4,p_bay['y']+0.85,'Bay 7\nREADY_TO_RETRIEVE',ha='left',va='center',fontsize=9.2,color='white',family=MONO,bbox=dict(boxstyle='round,pad=.24',fc='#0c1730',ec=GREEN,lw=1.0),zorder=7)
    axL.annotate('Payload GUID rides on tray 15',xy=(p_tray['x']+0.2,p_tray['y']+0.10),xytext=(35.2,24.6),color=AMBER,fontsize=9.0,family=MONO,
                 arrowprops=dict(arrowstyle='-|>',color=AMBER,lw=1.3),bbox=dict(boxstyle='round,pad=.18',fc='#0c1730',ec=AMBER,lw=.9))
    # right side light UML-ish summary
    axR.set_facecolor('white'); axR.set_xlim(0,8.2); axR.set_ylim(0,10.0); axR.axis('off')
    axR.text(4.1,9.82,'In-memory C++ / ROS state records',ha='center',va='top',fontsize=13.2,color=UML_LINE,family=MONO,fontweight='bold')
    dgs=lclass(axR,0.4,9.15,'DiscreteGarageState',attrs=['+ agvs: DiscreteAgvState[]','+ bays: DiscreteBayState[]','+ trays: DiscreteTrayState[]','+ payloads: DiscretePayloadState[]','+ vrcs: DiscreteVrcState[]','+ disabled_nodes: uint32[]'],stereo='top-level snapshot',w=6.8,fs=7.0,name_fs=9.0)
    agvb=lclass(axR,0.4,5.85,'agvs[0] : DiscreteAgvState',attrs=['+ id = 4','+ pose = GaragePose{node_id=10, heading=90}','+ lift = false','+ tray_id = 0'],w=6.8,fs=6.7,name_fs=8.4)
    trayb=lclass(axR,0.4,3.75,'trays[0] : DiscreteTrayState',attrs=['+ id = 15','+ pose = GaragePose{node_id=3, heading=90}','+ agv_id = 0','+ payload_id = payload_GUID'],w=6.8,fs=6.7,name_fs=8.4)
    bayb=lclass(axR,0.4,1.65,'bays[0] : DiscreteBayState',attrs=['+ id = 7','+ state = READY_TO_RETRIEVE','+ disabled = false'],w=3.3,fs=6.7,name_fs=8.4)
    payb=lclass(axR,4.0,1.65,'payloads[0] : DiscretePayloadState',attrs=['+ tray_id = 15','+ reciprocal_to_tray = false','+ charging = false'],w=3.2,fs=6.4,name_fs=8.0)
    lrel(axR,[dgs.bot(0.25),(1.8,6.8),agvb.top(0.5)],kind='comp',label='agvs[]',lpos=(2.7,7.05))
    lrel(axR,[dgs.bot(0.55),(4.1,5.0),trayb.top(0.5)],kind='comp',label='trays[]',lpos=(4.9,5.25))
    lrel(axR,[dgs.bot(0.18),(1.5,2.9),bayb.top(0.5)],kind='comp',label='bays[]',lpos=(2.2,3.15))
    lrel(axR,[dgs.bot(0.82),(5.8,2.9),payb.top(0.5)],kind='comp',label='payloads[]',lpos=(6.4,3.15))
    # dashed bridge note arrows inside right panel referencing left scene conceptually
    axR.text(4.1,0.18,'Each highlighted resource on the left becomes one record or field inside the single\nDiscreteGarageState snapshot on the right.',ha='center',va='bottom',fontsize=8.6,color='#555',family=MONO)
    fig.text(0.51,0.965,'The left panel reuses the Pecos facility drawing so the spatial scene and the state structure stay visually tied together.',ha='center',va='top',fontsize=9.2,color=MUTED,family=MONO)
    save(fig,'16_discrete_garage_state_bridge.svg')


def update_markdown():
    p = ROOT/'01-software-background.md'
    s = p.read_text()
    old_tip = '> **Review tip for VS Code.** Markdown preview renders SVGs as static images. For **pan/zoom**, `Ctrl+Click` the linked `.svg` path under a figure, or open the SVG file directly in the editor / browser.\n'
    new_tip = '> **Review tip for VS Code.** Native Markdown preview renders SVGs as **static images** and does **not** allow the JavaScript needed for true inline pan/zoom. So a built-in pan/zoom widget inside the preview is not realistically available in plain `.md` under the stock preview. I have therefore optimized the SVGs for readability in-preview (larger labels, roomier legends, less truncation) and kept direct SVG links for full-detail inspection.\n'
    s = s.replace(old_tip,new_tip)
    # clarify figure 3 recycled facility
    s = s.replace('The left side shows the spatial interpretation: a bay, an AGV charging node, a tray location, and a payload riding on that tray.',
                  'The left side reuses the Pecos facility drawing so the spatial interpretation is grounded in the same layout diagram: a bay, an AGV charging node, a tray location, and a payload riding on that tray.')
    p.write_text(s)


def make_zip():
    zip_path = Path('/mnt/data/scheduler-core-refactor-study-v7.zip')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for path in ROOT.rglob('*'):
            if path.is_file():
                z.write(path, path.relative_to(ROOT.parent))
    return zip_path

if __name__=='__main__':
    fig_facility_topology()
    fig_uml_existing_core()
    fig_ros_messages()
    fig_discrete_garage_state_bridge()
    update_markdown()
    print(make_zip())
