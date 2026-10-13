from pathlib import Path
import sys, math
sys.path.insert(0,str(Path(__file__).parent))
import figstyle
from draw import *
from figstyle import *
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle
figstyle.OUT=Path(__file__).parent.parent/'figures'
figstyle.OUT.mkdir(exist_ok=True)

def axes(ax):
    arrow(ax,(0.7,0.7),(9.2,0.7),MUTED)
    arrow(ax,(0.7,0.7),(0.7,5.1),MUTED)
    label(ax,9.3,0.65,'x [m]  →',FG,fs=9,mono=True,ha='left')
    label(ax,0.7,5.35,'y [m]',FG,fs=9,mono=True)
    for x in range(2,10,2):
        ax.plot([x,x],[0.64,0.77],color=MUTED,lw=0.8)
    for y in range(2,6,2):
        ax.plot([0.64,0.77],[y,y],color=MUTED,lw=0.8)

def parking(ax,x,y,s='P',c=BORDER):
    ax.add_patch(Rectangle((x-.43,y-.38),.86,.76,facecolor=MUTED_BG,edgecolor=c,lw=1.2,linestyle='--',zorder=1))
    label(ax,x,y+.57,s,MUTED,fs=8,mono=True)

def tray(ax,x,y,id,color=AMBER):
    ax.add_patch(Rectangle((x-.33,y-.24),.66,.48,facecolor=CARD,edgecolor=color,lw=1.8,zorder=3))
    ax.add_patch(Rectangle((x-.26,y-.16),.52,.32,facecolor=color,alpha=.20,edgecolor='none',zorder=4))
    label(ax,x,y,f'T{id}',color,fs=9,mono=True,bold=True,z=7)

def fig_garage():
    fig,ax=canvas(11,6.4);axes(ax)
    for x in [2,4,6,8]:
        parking(ax,x,2,f'P{x}')
    tray(ax,4,2,'2');tray(ax,6,2,'3');agv(ax,2,2,0,SKY,scale=1.5,label='AGV 1')
    parking(ax,8,2,'GOAL',GREEN)
    ax.plot([2.5,3.5,4.5,5.5,6.5,7.6],[2]*6,color=AMBER,lw=2,ls=':',zorder=2)
    label(ax,5,3.2,'blocked route to target',AMBER,mono=True,fs=10)
    label(ax,5.3,5.5,'ILLUSTRATIVE GARAGE — NOT TO SCALE',FG,mono=True,fs=12)
    save(fig,'03_garage_xy')

def fig_reposition():
    fig,ax=canvas(11,6.4);axes(ax)
    for x in [2,4,6,8]: parking(ax,x,2,f'P{x}')
    agv(ax,2,2,0,SKY,scale=1.5,label='AGV 1')
    tray(ax,6,2,'7');parking(ax,8,4,'TARGET',GREEN)
    ax.plot([2.6,5.4],[2,2],lw=2,color=SKY,ls='--')
    arrow(ax,(6,2.5),(7.8,3.7),GREEN,lw=2)
    label(ax,3.7,2.52,'1. approach',SKY,fs=9,mono=True)
    label(ax,7.8,3.05,'2. lift + carry',GREEN,fs=9,mono=True)
    label(ax,5.1,5.5,'AGV REPOSITIONING + TRAY TRANSPORT',FG,fs=12,mono=True)
    save(fig,'05_agv_reposition')

def fig_blocking():
    fig,ax=canvas(11,6.4);axes(ax)
    for x in [2,4,6,8]: parking(ax,x,2,f'N{x}')
    parking(ax,4,4,'FREE',GREEN)
    tray(ax,2,2,'root',SKY); tray(ax,4,2,'block',AMBER)
    agv(ax,2,1.28,0,SKY,scale=1.10,label='')
    arrow(ax,(4,2.45),(4,3.6),AMBER,lw=2)
    arrow(ax,(2.55,2),(7.6,2),GREEN,lw=2)
    label(ax,5,3.65,'1. move blocking tray',AMBER,fs=9,mono=True)
    label(ax,6,1.42,'2. move root tray',GREEN,fs=9,mono=True)
    label(ax,5,5.5,'PREREQUISITE RELOCATION',FG,fs=12,mono=True)
    save(fig,'06_blocking_resolution')

def fig_collision():
    fig,ax=canvas(11,6.4);axes(ax)
    for x in [2,4,6,8]: parking(ax,x,2,f'N{x}')
    agv(ax,3.9,2,0,SKY,scale=1.7,label='AGV A')
    agv(ax,6.1,2,math.pi,RED,scale=1.7,label='AGV B')
    ax.add_patch(Circle((5,2),.64,facecolor=RED,edgecolor=RED,alpha=.14,lw=1.8))
    ax.plot([4.55,5.45],[2,2],color=RED,lw=2,ls='--')
    label(ax,5,3.25,'conflicting shared node / corridor',RED,fs=9,mono=True)
    label(ax,5.3,5.5,'ARRIVAL ORDER MUST BE ENFORCED',FG,mono=True,fs=12)
    save(fig,'07_agv_collision')

def fig_uml():
    fig,ax=canvas(13,6.3)
    i=uml_class(ax,.5,5.6,'TrayMoveSolver',[],['+ virtual Solve(request) : Result','+ virtual ~TrayMoveSolver()'],color=VIOLET,stereo='interface',w=5.3,fs=9)
    c=uml_class(ax,.5,3.25,'DefaultTrayMoveSolver',['- garage_graph_ : reference','- collision_table_ : reference'],['+ Solve(request) : Result'],color=SKY,w=5.3,fs=9)
    a=uml_class(ax,7.1,5.6,'Scheduler',['- tray_solver_ : solver reference'],['+ Plan(request) : PlanResponse'],color=GREEN,w=5.4,fs=9)
    uml_rel(ax,[c.top(),i.bot()],'real',VIOLET)
    uml_rel(ax,[a.left(.45),i.right(.5)],'assoc',GREEN,label='delegates',fs=8)
    label(ax,6.7,.55,'Design proposal: API and exact ownership remain subject to implementation review',MUTED,fs=9,mono=True)
    save(fig,'08_uml_solver')

def fig_sequence():
    fig,ax=canvas(12,6.4)
    s=Seq(ax,{'Scheduler':(1.8,GREEN,2.0,None),'TrayMoveSolver':(5.9,SKY,2.7,None),'Event DAG':(10,VIOLET,2.0,None)},top=5.8,bottom=.4,head_h=.65)
    s.msg('Scheduler','TrayMoveSolver',4.8,'Solve(context)',GREEN)
    s.msg('TrayMoveSolver','Event DAG',3.8,'topological_order()',SKY)
    s.msg('TrayMoveSolver','Event DAG',2.9,'add unblocking move + dependencies',SKY)
    s.note('TrayMoveSolver',2.3,'records first_tray_event',AMBER)
    s.msg('TrayMoveSolver','Scheduler',1.3,'success / diagnostic',SKY)
    save(fig,'09_sequence_tray')

for f in [fig_garage,fig_reposition,fig_blocking,fig_collision,fig_uml,fig_sequence]: f()
print('Generated figure set')
