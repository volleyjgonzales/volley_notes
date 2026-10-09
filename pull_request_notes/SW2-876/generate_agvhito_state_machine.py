#!/usr/bin/env python3
"""Render the original AGVHITO state diagram from the supplied Repomix snapshot.

Requires Python 3.10+ and matplotlib. No network, Library access, or document
mutation. The hand-routed layout targets this nine-state snapshot; validation
rejects a graph that does not match it instead of silently dropping new edges.
"""
from pathlib import Path
import argparse
import re
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon


def generate(repo_path: Path, output_dir: Path, dpi: int = 160) -> None:
    root = output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    repo=repo_path.read_text(encoding='utf-8')
    decl=re.search(r'^## File: include/agvhito/sm/state_strings.hpp\n```[^\n]*\n(.*?)\n```',repo,re.M|re.S).group(1)
    constants=dict(re.findall(r'inline constexpr auto (k\w+) \{"([^"]+)"\}',decl))
    constants['yasminx::kOutcomeCanceled']='canceled'
    classes={'booting':'BootingState','localizing':'LocalizingState','stopped':'StoppedState','idle':'IdleState','executing-order':'ExecutingOrderState','execution-paused':'ExecutionPausedState','execution-recovery':'ExecutionRecoveryState','canceling-order':'CancelingOrderState','error':'ErrorState'}
    maps={'kBootingTransitions':'booting','kLocalizingTransitions':'localizing','kStoppedTransitions':'stopped','kIdleTransitions':'idle','kExecutingOrderTransitions':'executing-order','kExecutionPausedTransitions':'execution-paused','kExecutionRecoveryTransitions':'execution-recovery','kCancelingOrderTransitions':'canceling-order','kErrorTransitions':'error'}
    expected=[]
    for name,body in re.findall(r'inline const yasmin::Transitions (k\w+) \{(.*?)\n\};',decl,re.S):
        for outcome,dest in re.findall(r'\{([^,]+),\s*([^}]+)\}',body):expected.append((maps[name],constants[outcome.strip()],constants[dest.strip()]))
    assert len(expected)==36
    W,H=2400,2960
    BG='#F8FAFC';INK='#0F172A';MUTED='#475569';BORDER='#E2E8F0';BLUE='#2563EB';TEAL='#0F766E';ROSE='#BE123C';CANCEL='#475569'
    plt.rcParams.update({'font.family':'Nimbus Sans','svg.fonttype':'path'})
    fig=plt.figure(figsize=(24,29.6),dpi=100,facecolor=BG)
    ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,W);ax.set_ylim(H,0);ax.axis('off')
    def txt(x,y,t,size=16,color=INK,weight='normal',ha='left',mono=False,**kwargs):
        return ax.text(x,y,t,fontsize=size,color=color,fontweight=weight,ha=ha,va='center',fontfamily='Nimbus Mono PS' if mono else 'Nimbus Sans',zorder=8,**kwargs)
    def rect(x,y,w,h,fill='white',stroke=BORDER,r=18,z=2,lw=1.5):
        p=FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={r}',facecolor=fill,edgecolor=stroke,linewidth=lw,zorder=z) if r else Rectangle((x,y),w,h,facecolor=fill,edgecolor=stroke,lw=lw,zorder=z)
        ax.add_patch(p);return p
    def card(x,y,w,h):
        rect(x,y+5,w,h,'#E8EDF3','#E8EDF3',24,z=0)
        rect(x,y,w,h,'white',BORDER,24,z=1)
    def badge(x,y,label,color,fill,width):
        rect(x,y-16,width,32,fill,fill,10,z=6)
        txt(x+width/2,y,label,10,color,'bold','center')
    def node(s,x,y,w=370,h=100,compact=False):
        ordinary=s=='booting';color=BLUE if ordinary else TEAL
        rect(x,y,w,h,'#FFFFFF',color,0 if ordinary else 15,z=4,lw=2)
        ax.plot([x+18,x+18],[y+19,y+h-19],color=color,lw=4,zorder=5)
        if compact:
            txt(x+35,y+h/2-15,s,13,INK,'bold',mono=True)
            txt(x+35,y+h/2+17,classes[s],12,MUTED)
        else:
            txt(x+36,y+29,s,16,INK,'bold',mono=True)
            txt(x+36,y+60,classes[s],13,MUTED)
            txt(x+w-18,y+84,'STATE' if ordinary else 'LIFECYCLE',9,color,'bold','right')

    drawn=[];heads=[]
    def edge(a,outcome,b,points,labelpos,color=BLUE,labelha='center',fontsize=13,label_fill=True):
        key=(a,outcome,b);assert key in expected and key not in drawn,key
        drawn.append(key)
        # Deliberately no point-based shrinking: every endpoint is an explicit
        # external node port. Polygon heads are drawn above boxes and line masks.
        xs,ys=zip(*points)
        line,=ax.plot(xs,ys,color=color,lw=2.3,zorder=3,solid_capstyle='round',solid_joinstyle='round')
        line.set_gid('edge-'+a+'-'+outcome+'-'+b)
        px,py=points[-2];x,y=points[-1];dx,dy=x-px,y-py
        length=math.hypot(dx,dy);assert length>=22,key
        ux,uy=dx/length,dy/length
        poly=Polygon([(x,y),(x-17*ux+7*uy,y-17*uy-7*ux),(x-17*ux-7*uy,y-17*uy+7*ux)],facecolor=color,edgecolor=color,zorder=10)
        poly.set_gid('arrowhead-'+a+'-'+outcome+'-'+b)
        ax.add_patch(poly);heads.append(poly)
        txt(*labelpos,outcome,fontsize,color,ha=labelha,mono=True,bbox=dict(facecolor='white',edgecolor='none',pad=3) if label_fill else None)

    txt(70,58,'ENGINEERING REFERENCE',11,BLUE,'bold')
    txt(70,115,'AGVHITO state machine',34,INK,'bold')
    txt(70,164,'Nine registered states. Every outcome route. Current repository behavior.',17,MUTED)
    badge(70,215,'DIRECT STATE',BLUE,'#DBEAFE',165)
    badge(255,215,'LIFECYCLE STATE',TEAL,'#CCFBF1',215)
    badge(490,215,'TERMINAL OUTCOME',ROSE,'#FFE4E6',230)
    txt(2330,215,'SOURCE  agvhito-repomix.md',13,MUTED,ha='right',mono=True)

    card(50,270,2300,1300)
    txt(90,320,'01',13,BLUE,'bold')
    txt(145,320,'Control flow & recovery',24,INK,'bold')
    txt(2300,320,'15 ROUTES',12,MUTED,'bold','right')
    txt(90,360,'Booting owns its Execute body; lifecycle states poll within an activation.',14,MUTED)
    pos={'booting':(180,400),'localizing':(180,620),'stopped':(180,840),'idle':(180,1080),'executing-order':(1050,1080),'execution-paused':(1720,620),'execution-recovery':(1720,1140),'canceling-order':(1050,1380),'error':(1050,400)}
    for s,p in pos.items():node(s,*p)
    txt(180,385,'INITIAL STATE',9,BLUE,'bold')
    edge('booting','booted','localizing',[(365,503),(365,617)],(365,557))
    edge('localizing','localized','stopped',[(365,723),(365,837)],(365,775))
    edge('stopped','not-localized','localizing',[(177,866),(100,866),(100,646),(177,646)],(105,750),labelha='left',fontsize=12)
    edge('stopped','activate-requested','idle',[(365,943),(365,1077)],(365,1009))
    edge('idle','controlled-stop-requested','stopped',[(177,1108),(90,1108),(90,909),(177,909)],(95,1045),labelha='left',fontsize=11)
    edge('idle','order-requested','executing-order',[(553,1110),(1047,1110)],(800,1110))
    edge('executing-order','order-complete','idle',[(1047,1145),(980,1145),(980,1260),(630,1260),(630,1145),(553,1145)],(795,1260))
    edge('executing-order','order-requested','executing-order',[(1180,1077),(1180,975),(1310,975),(1310,1077)],(1245,950))
    txt(1245,997,'next queued order',10,MUTED,ha='center')
    edge('executing-order','pause-requested','execution-paused',[(1423,1108),(1560,1108),(1560,646),(1717,646)],(1560,802),fontsize=12)
    edge('execution-paused','resumed','executing-order',[(1717,688),(1490,688),(1490,1025),(1370,1025),(1370,1077)],(1490,917))
    edge('executing-order','order-data-stale','execution-recovery',[(1423,1150),(1650,1150),(1650,1166),(1717,1166)],(1570,1131),fontsize=12)
    edge('execution-recovery','recovered','executing-order',[(1905,1243),(1905,1485),(1510,1485),(1510,1230),(1370,1230),(1370,1183)],(1745,1485))
    edge('executing-order','controlled-stop-requested','canceling-order',[(1235,1183),(1235,1377)],(1235,1308),fontsize=12)
    edge('canceling-order','canceled-order','stopped',[(1047,1430),(780,1430),(780,905),(553,905)],(780,1330),fontsize=12)
    edge('error','recovered','stopped',[(1047,450),(880,450),(880,804),(595,804),(595,866),(553,866)],(880,625))
    txt(1905,882,'Continue{}',17,TEAL,'bold','center',mono=True)
    txt(1905,920,'Stays inside the same activation.',13,MUTED,ha='center')
    txt(1905,950,'No exit, re-entry, or graph edge.',13,MUTED,ha='center')
    txt(1905,985,'Lifecycle poll: 100 ms',12,MUTED,ha='center')
    txt(1905,1015,'ROS feedback cycle: 50 ms',12,MUTED,ha='center')
    txt(90,1530,'Outcome labels are exact identifiers; the queued-order route is the only explicit self-transition.',13,MUTED)

    # Failure and cancellation panels use separate outcome ports. Even routes
    # sharing a source/target have individual lines and individually visible heads.
    for px,target,title,count,color in [(50,'error','Failure routing',12,ROSE),(1220,'terminal','Framework cancellation',9,CANCEL)]:
        card(px,1610,1130,1215)
        txt(px+40,1660,'02' if target=='error' else '03',13,color,'bold')
        txt(px+95,1660,title,22,INK,'bold')
        txt(px+1080,1660,f'{count} ROUTES',11,MUTED,'bold','right')
        txt(px+40,1702,'Each outcome has its own arrow and destination port.',12,MUTED)
        subset=[e for e in expected if e[2]==target]
        sources=[s for s in classes if any(e[0]==s for e in subset)]
        sx=px+35;sw=350;tx=px+920;tw=175
        rect(tx,1760,tw,975,'#FFF1F2' if target=='error' else '#F1F5F9',color,15,z=4,lw=2)
        txt(tx+tw/2,1795,target,16,color,'bold','center',mono=True)
        txt(tx+tw/2,1827,'ErrorState' if target=='error' else 'root outcome',12,MUTED,ha='center')
        txt(tx+tw/2,1854,'LifecycleState' if target=='error' else 'not a state',10,MUTED,ha='center')
        y=1775
        for s in sources:
            outcomes=[o for a,o,b in subset if a==s]
            height=140 if len(outcomes)==3 else 88
            node(s,sx,y,sw,height,compact=True)
            cy=y+height/2
            ports=[cy] if len(outcomes)==1 else [cy-40,cy,cy+40]
            for o,py in zip(outcomes,ports):
                edge(s,o,target,[(sx+sw+3,py),(tx-3,py)],((sx+sw+tx)/2,py),color,fontsize=11.5)
            y+=height+23
        txt(px+40,2785,'Declared routes include branches tolerated by current recovery hooks.' if target=='error' else 'canceled terminates the root; canceled-order means robot traversal completed.',10,MUTED)

    txt(70,2880,'36 / 36 mapped routes',14,INK,'bold')
    txt(70,2920,'Repeated state cards denote the same registered class. Proposed SW2-876 policy changes are not applied.',12,MUTED)
    txt(2330,2880,'VECTOR-FIRST  /  EXPLICIT ARROWHEADS',10,MUTED,'bold','right')
    assert set(drawn)==set(expected) and len(heads)==36
    fig.savefig(root/'agvhito-state-machine.png',dpi=dpi,facecolor=BG)
    fig.savefig(root/'agvhito-state-machine.svg',facecolor=BG)
    plt.close(fig)
    svg=(root/'agvhito-state-machine.svg').read_text()
    assert svg.count('id="arrowhead-')==36
    assert 'foreignObject' not in svg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).with_name('agvhito-repomix.md'))
    parser.add_argument('--out-dir', type=Path, default=Path('diagrams'))
    parser.add_argument('--dpi', type=int, default=160)
    args = parser.parse_args()
    if not args.repo.is_file():
        parser.error(f'Repomix input does not exist: {args.repo}')
    if args.dpi < 72:
        parser.error('--dpi must be at least 72')
    generate(args.repo, args.out_dir, args.dpi)
    print(f'Wrote original PNG/SVG to {args.out_dir.resolve()} (36 validated arrows).')


if __name__ == '__main__':
    main()
