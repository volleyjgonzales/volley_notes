from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","24-central")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# Illustrative schedule (topological order): (label, entity, duration [s], parents, status)
N=[("a1 drive",   "a1", 8.0, [],     "received"),
   ("a1 drive",   "a1", 6.0, [0],    "received"),
   ("a1 lift up", "a1", 6.0, [1],    "not received"),
   ("b7 open",    "b7",20.0, [],     "not received"),
   ("a1 drive",   "a1",12.0, [2],    "not received"),
   ("a2 drive",   "a2", 9.0, [],     "completed"),
   ("a2 drive",   "a2",14.0, [5,1],  "not received"),
   ("a1 drive",   "a1",10.0, [4,3],  "not received"),
   ("a1 lift dn", "a1", 5.5, [7],    "not received"),
   ("b7 patron",  "b7",float("inf"),[8],"not received"),
   ("a2 drive",   "a2", 7.0, [6,9],  "not received")]
def start_times(nodes):   # verbatim logic of Schedule::GetNodeStartTimes
    st=[0.0]*len(nodes)
    for i,(_,_,_,par,status) in enumerate(nodes):
        if status=="completed": continue
        for p in par:
            if nodes[p][4]=="completed": continue
            st[i]=max(st[i], st[p]+nodes[p][2])
    return st
T=start_times(N); H=30.0
rows={"a1":2,"a2":1,"b7":0}; col={"completed":C["aux"],"received":C["pt"],"not received":C["s1"]}
fig,ax=plt.subplots(figsize=(12,3.8))
for i,(lab,ent,d,par,status) in enumerate(N):
    if status=="completed": continue
    y=rows[ent]; dd=min(d,75-T[i]) if np.isfinite(d) else 75-T[i]
    if not np.isfinite(T[i]): continue
    inside=T[i]<=H
    ax.barh(y,dd,left=T[i],height=0.55,color=col[status],alpha=0.85 if inside else 0.3,edgecolor="black",lw=0.6,hatch=None if inside else "//")
    ax.text(T[i]+0.4,y,f"{i}: {lab}" + (" (∞)" if not np.isfinite(d) else ""),va="center",fontsize=7.5,color="white" if inside else "black")
ax.axvline(H,color=C["hl"],lw=2,ls="--"); ax.text(H+0.5,1.45,"command horizon / split: 30 s",color=C["hl"],fontsize=8.5)
ax.set_yticks([0,1,2]); ax.set_yticklabels(["bay b7","AGV a2","AGV a1"]); ax.set_xlim(0,75); ax.set_xlabel("estimated start time t_v [s] (longest path through incomplete parents)")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=col["received"],label="received (sent, acknowledged)"),Patch(color=col["not received"],label="not received"),Patch(facecolor="white",edgecolor="black",hatch="//",label="outside the split: not sent during a plan call")],fontsize=7.5,loc="lower right")
ax.set_title("Schedule::GetNodeStartTimes on an illustrative schedule (node 5 already completed, so node 6 waits only for node 1)",fontsize=9.5,loc="left"); ax.grid(axis="x",alpha=.3)
fig.tight_layout(); go(fig,"schedule_start_times")
print([round(t,1) if np.isfinite(t) else "inf" for t in T])
