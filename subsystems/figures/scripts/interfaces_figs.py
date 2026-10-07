from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","11-interfaces")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# Illustrative Schedule: ActionNode list with parents (indices) and durations [s]. Not taken from real data.
nodes=[
 ("AGV 3: move to tray 12",            "AGV", [],    18),
 ("AGV 3: lift up (carry tray 12)",    "AGV", [0],    6),
 ("Bay 2: transition to retrieve",     "BAY", [],    25),
 ("VRC 1: move to floor 2",            "VRC", [],    14),
 ("AGV 3: drive onto VRC 1",           "AGV", [1,3], 12),
 ("VRC 1: move to floor 1",            "VRC", [4],   16),
 ("AGV 3: drive to bay 2",             "AGV", [5,2], 20),
 ("AGV 3: lift down in bay 2",         "AGV", [6],    6),
 ("Bay 2: process retrieve",           "BAY", [7], float("inf")),
]
es=[0.0]*len(nodes)
for i,(_,_,par,_) in enumerate(nodes): es[i]=max([es[p]+nodes[p][3] for p in par],default=0.0)
# critical path to node 7 (last finite)
crit=set(); i=7
while True:
    crit.add(i); par=nodes[i][2]
    if not par: break
    i=max(par,key=lambda p: es[p]+nodes[p][3])
col={"AGV":C["s1"],"BAY":C["s2"],"VRC":C["pt"]}
fig,ax=plt.subplots(figsize=(11.5,4.6))
for i,(lab,typ,par,d) in enumerate(nodes):
    y=len(nodes)-1-i; dd=d if np.isfinite(d) else 22
    ax.barh(y,dd,left=es[i],color=col[typ],alpha=.85 if i in crit else .35,edgecolor="black" if i in crit else "none",height=.6)
    ax.text(es[i]+dd+.8,y,f"[{i}] {lab}" + ("  (duration ∞)" if not np.isfinite(d) else ""),va="center",fontsize=8.5)
    for p in par:
        yp=len(nodes)-1-p; ax.annotate("",xy=(es[i],y),xytext=(es[p]+nodes[p][3],yp),arrowprops=dict(arrowstyle="->",color=C["aux"],lw=.8))
mk=es[7]+nodes[7][3]
ax.axvline(mk,color=C["hl"],ls="--",lw=1); ax.text(mk+.5,len(nodes)-.4,f"vehicle in bay at t = {mk:g} s",color=C["hl"],fontsize=9)
ax.set_yticks([]); ax.set_xlabel("time [s] (earliest start from parents and durations)"); ax.set_xlim(0,150)
for s in ("left","right","top"): ax.spines[s].set_visible(False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=v,label=f"{k} command") for k,v in col.items()],fontsize=8,loc="upper right"); ax.set_title("A Schedule as a DAG of ActionNodes (illustrative): arrows = parents, outlined = critical path",loc="left",fontsize=10)
go(fig,"schedule_dag"); print(es, mk, sorted(crit))
