"""Supplemental as-built parking-structure and UML figures for guide 01."""
import sys, math
from pathlib import Path
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle, FancyBboxPatch
sys.path.insert(0,str(Path(__file__).parent))
from figstyle import plt, BG, CARD, FG, MUTED, BORDER, SKY, GREEN, AMBER, RED, VIOLET, MONO
from draw import agv, canvas, node, uml_class, edge, Seq
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'figures'

def save(fig,name):
    fig.savefig(OUT/name, facecolor=BG, bbox_inches='tight',pad_inches=.12,metadata={'Date':None})
    plt.close(fig)

def txt(ax,x,y,s,size=10,color=FG,ha='center',weight='normal'):
    ax.text(x,y,s,fontsize=size,color=color,ha=ha,va='center',family=MONO,weight=weight,zorder=20)

def arrow(ax,start,end,color=GREEN,lw=2):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=15,color=color,lw=lw,zorder=16))

def parking(ax,x,y,ident,occupied=None, goal=False):
    col=GREEN if goal else BORDER
    ax.add_patch(Rectangle((x-.53,y-.75),1.06,1.5,facecolor='#1b2b35' if goal else '#17263b',edgecolor=col,lw=1.6,zorder=2))
    # top labels outside parking slot -> guaranteed no overlap with body/goal
    txt(ax,x,y+.99,f'P{ident}',9,FG)
    if occupied:  # tray, label outside footprint
        ax.add_patch(FancyBboxPatch((x-.38,y-.49),.76,.98,boxstyle='round,pad=.02,rounding_size=.07',facecolor='#7c5738',edgecolor=AMBER,lw=1.8,zorder=4))
        txt(ax,x,y,occupied,9,'#fff2d5',weight='bold')
    if goal:
        txt(ax,x,y-.99,'GOAL',9,GREEN,weight='bold')

def site(name,mode):
    fig,ax=plt.subplots(figsize=(13,8));fig.patch.set_facecolor(BG);ax.set_facecolor(BG)
    ax.set_xlim(-1.7,13.4);ax.set_ylim(-1.8,8.2);ax.set_aspect('equal');ax.axis('off')
    # floor, lanes, parking
    ax.add_patch(Rectangle((-.8,-.8),13.5,8.1,facecolor='#192230',edgecolor='#4e6174',lw=2))
    for y in (2.25,4.55):
        ax.add_patch(Rectangle((-.65,y-.55),12.9,1.1,facecolor='#303b4a',edgecolor='none'))
        for x in range(1,12):ax.plot([x-.22,x+.22],[y,y],color='#a7b8c8',lw=1,ls='--',alpha=.6)
    for j,x in enumerate((2.1,4.3,6.5,8.7)):
        parking(ax,x,6.14,8+j,occupied=('T8' if j==1 else None) if mode=='critical' else ('T8' if j==1 else ('T9' if j==2 else None)),goal=(j==3))
        parking(ax,x,.55,14+j,occupied='T14' if j==0 else None)
    # bay at left, exterior doors
    ax.add_patch(FancyBboxPatch((-.55,3.35),1.7,2.25,boxstyle='round,pad=.03,rounding_size=.09',facecolor='#213d4b',edgecolor=SKY,lw=2))
    txt(ax,.28,5.21,'BAY b1',11,SKY,weight='bold');txt(ax,.28,4.6,'CUSTOMER',8);txt(ax,.28,4.12,'DOOR',8)
    ax.plot([1.15,1.15],[3.35,5.6],color=AMBER,lw=3,ls='--')
    # vrc at right side, floor gates, second floor inset
    ax.add_patch(FancyBboxPatch((10.8,3.2),1.55,2.6,boxstyle='round,pad=.03,rounding_size=.09',facecolor='#29304a',edgecolor=VIOLET,lw=2))
    txt(ax,11.55,5.38,'VRC v1',10,VIOLET,weight='bold');txt(ax,11.55,4.83,'FLOOR 1',8);txt(ax,11.55,4.28,'LIFT',8)
    txt(ax,11.55,3.72,'F1 / F2',8);ax.plot([10.8,10.8],[3.27,5.73],color=VIOLET,lw=3,ls='--')
    # Charge point
    ax.add_patch(Circle((11.4,.66),.45,color='#154d47',ec=GREEN,lw=2));txt(ax,11.4,.68,'EV',10,GREEN,weight='bold');txt(ax,11.4,-.09,'VECS',9,GREEN)
    # center bot
    agv(ax,2.1,2.22,0,L=1.15,W=.7,scale=1.15);txt(ax,2.1,1.53,'AGV a1',10,SKY,weight='bold')
    if mode=='critical':
        # path arrow horizontal underneath slot labels, no overlap with GOAL
        arrow(ax,(3.0,3.0),(5.9,3.0),AMBER);arrow(ax,(6.05,3),(8.9,3),GREEN)
        txt(ax,5.45,3.42,'BLOCKED',10,AMBER,weight='bold');txt(ax,9.55,2.95,'TO GOAL',8,GREEN)
    else:
        arrow(ax,(2.1,2.84),(4.25,4.15),SKY);arrow(ax,(4.45,4.3),(8.7,5.02),GREEN)
        txt(ax,5.0,3.5,'REPOSITION',9,SKY);txt(ax,7.25,4.66,'CARRY',9,GREEN)
    # cartesian axes, outside roadway
    arrow(ax,(.2,-1.3),(1.35,-1.3),RED,1.6);txt(ax,1.53,-1.3,'+x',10,RED)
    arrow(ax,(.2,-1.3),(.2,-.3),GREEN,1.6);txt(ax,.2,-.07,'+y',10,GREEN)
    txt(ax,6.6,7.72,'ILLUSTRATIVE PARKING STRUCTURE / TOP VIEW',13,FG,weight='bold')
    txt(ax,6.55,-1.37,'NOT TO SCALE - NODE IDS ARE DIDACTIC, NOT REAL COORDINATES',8,MUTED)
    save(fig,name)

site('03_garage_xy.svg','critical')
site('10_parking_structure.svg','normal')

# Existing class model, partitioned for legibility
fig,ax=canvas(15,9, equal=False)
a=uml_class(ax,.45,8.35,'Scheduler',attrs=['- layout_: LayoutSPtr','- gg_: GarageGraph','- table_: CollisionTable','- cost_model_: MotionCostModel'],methods=['+ Plan(request, now)','+ DoTrayAssignments(ctx)','+ DoAgvAssignments(ctx)','+ PlanMotions(ctx)'],w=3.65)
b=uml_class(ax,5.2,8.35,'ScheduleContext',attrs=['+ initial_state: DiscreteGarageState','+ events: ScheduleEventDag','+ scheduled_jobs: vector<...>','+ first_tray_event: map<...>'],methods=['+ UpdateLastEntityEvent(...)','+ UpdateLeafDependencies(...)'],color=GREEN,w=4.25)
c=uml_class(ax,10.5,8.35,'ScheduleEventDag',attrs=['+ DagBase<ScheduleEvent>'],methods=['+ AddEvent(event)','+ AddDependency(a,b)','+ GetTopologicalOrdering()','+ Reduce()'],color=AMBER,w=3.9)
d=uml_class(ax,5.4,3.7,'DiscreteGarageState',attrs=['AGVs, bays, trays, payloads','VECS and VRC states'],methods=['+ GetAgv(...) / GetTray(...)','+ OnEvent(...)'],color=VIOLET,w=3.9)
e=uml_class(ax,10.4,3.7,'ScheduleEvent',attrs=['# type_','- job_idx_'],methods=['+ Apply(state) = 0','+ GetGarageEntityId() = 0','+ GetType()'],color=SKY,w=3.95,stereo='abstract')
arrow(ax,a.right(),b.left(),SKY)
arrow(ax,b.right(),c.left(),AMBER)
arrow(ax,b.bot(),d.top(),GREEN)
arrow(ax,c.bot(),e.top(),SKY)
txt(ax,7.5,.45,'AS BUILT: RELATIONSHIPS FROM SCHEDULER / PLANNER_CORE',11,MUTED)
save(fig,'11_uml_existing_core.svg')

fig,ax=canvas(15,9,equal=False)
base=uml_class(ax,5.6,8.45,'ScheduleEvent',attrs=['- type_: ScheduleEventType','- job_idx_: unsigned int'],methods=['+ Apply(state) const = 0','+ GetGarageEntityId() const = 0','+ ToString() const'],color=SKY,w=4)
children=[('TrayMove',['- tray_id_: optional<uint16_t>','- dest_: optional<GaragePose>','- agv_id_: optional<uint16_t>'],['+ Assigned()','+ SetTrayId() / SetDest()'],.35,4.95),('AgvMove',['- discrete_change_: variant<...>'],['+ GetAgvId()','+ GetSrc() / GetDest()'],5.1,4.95),('BayTransition',['- src_state_: DiscreteBayState','- command_: BayCommand'],['+ GetBayId()','+ GetCommand()'],9.7,4.95),('VecsTransition',['- state_change_: VecsStateChanged'],['+ GetVecsId()'],2.95,2.25),('VrcTransition',['- state_change_: VrcStateChanged','- from_vrc_node_id_','- to_vrc_node_id_'],['+ GetRequestedFloor()'],8.0,2.25)]
for name,attrs,methods,x,y in children:
    bb=uml_class(ax,x,y,name,attrs=attrs,methods=methods,color=GREEN if name=='TrayMove' else VIOLET,w=4.1)
    # dotted dependency indicates C++ inheritance, with explicit legend to avoid arrow ambiguity
    ax.plot([bb.cx,bb.cx],[bb.y1,bb.y1+.20],color=MUTED,lw=1.2)
txt(ax,7.5,.48,'AS BUILT: ALL FIVE TYPES PUBLICLY DERIVE FROM ScheduleEvent',10,MUTED)
save(fig,'12_uml_event_hierarchy.svg')

fig,ax=canvas(15,7.5,equal=False)
classes=[('PlanRequest',['id: Guid','base_state: DiscreteGarageState','pending_jobs: SchedulerJob[]','base_schedule: Schedule'],.3,6.8,3.4),('PlanResponse',['success: bool','message: string','schedule: Schedule','scheduled_jobs: ScheduledJobData[]'],4.45,6.8,3.5),('Schedule',['nodes: ActionNode[]'],8.65,6.8,2.9),('ActionNode',['type: uint8','parents: uint32[]','agv_command: AgvCommand','bay_command: BayCommand','vecs_command: VecsCommand','vrc_command: VrcCommand'],11.9,6.8,3)]
for name,attrs,x,y,w in classes:uml_class(ax,x,y,name,attrs=attrs,color=SKY if name in ('PlanRequest','PlanResponse') else GREEN,w=w,stereo='ROS message')
for x1,x2,y,s in [(3.7,4.42,4.85,'Plan()'),(7.95,8.62,4.85,'contains'),(11.6,11.85,4.85,'nodes')]:
 arrow(ax,(x1,y),(x2,y),AMBER)
 txt(ax,(x1+x2)/2,y+.43,s,8,AMBER)
txt(ax,7.5,1.1,'AS BUILT: ROS .msg FIELDS / NOT A C++ CLASS INHERITANCE TREE',10,MUTED)
save(fig,'13_uml_ros_messages.svg')

# vertically separated floor states
fig,ax=canvas(13,8,equal=False)
for x,lab,floor,color in [(1.7,'LEVEL F1','FLOOR 1',SKY),(8.0,'LEVEL F2','FLOOR 2',VIOLET)]:
 ax.add_patch(FancyBboxPatch((x,2.3),3.4,3.8,boxstyle='round,pad=.03,rounding_size=.2',facecolor=CARD,edgecolor=color,lw=2))
 txt(ax,x+1.7,5.6,lab,12,color,weight='bold')
 for j in range(3):
  ax.add_patch(Rectangle((x+.3+j,4.05),.85,1.0,facecolor='#202c42',edgecolor=BORDER))
  txt(ax,x+.72+j,4.6,f'P{j+1+3*(floor=="FLOOR 2")}',8,MUTED)
 txt(ax,x+1.7,3.2,'TRAVEL AISLE',10,MUTED)
 ax.add_patch(Rectangle((x+1.32,2.5),.8,.52,edgecolor=color,facecolor='#29334b'))
 txt(ax,x+1.72,2.8,'LIFT',8,color)
arrow(ax,(5.25,3.0),(7.65,3.0),AMBER,2.3);arrow(ax,(7.65,2.65),(5.25,2.65),AMBER,2.3)
txt(ax,6.43,3.5,'VRC',11,AMBER,weight='bold');txt(ax,6.5,2.15,'vertical transfer',9,MUTED)
txt(ax,6.5,7.3,'ONE LAYOUT CAN CONNECT MULTIPLE FLOORS',13,FG,weight='bold')
txt(ax,6.5,.8,'SIDE-BY-SIDE SCHEMATIC OF SEPARATE FLOORS; NOT A PLAN VIEW OF ONE FLOOR',9,MUTED)
save(fig,'14_vrc_floors.svg')
print('generated figures',len(list(OUT.glob('*.svg'))))
