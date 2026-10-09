from style import *
import os, heapq
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","21-planner_core")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# DAG from EventDagTests.TopoSortBigger (vertex label = job index)
E=[(1,2),(2,3),(1,3),(4,2),(5,6),(6,7)]
V=[1,2,3,4,5,6,7]
pos={1:(0,1.0),4:(0,-0.2),2:(1.3,0.4),3:(2.6,0.4),5:(0,-1.6),6:(1.3,-1.6),7:(2.6,-1.6)}
def reach(edges):
    succ={v:[b for a,b in edges if a==v] for v in V}; R={}
    def dfs(u,seen):
        for w in succ[u]:
            if w not in seen: seen.add(w); dfs(w,seen)
        return seen
    return {v:dfs(v,set()) for v in V}
R=reach(E)
red=[(u,v) for (u,v) in E if not any(w!=v and v in R[w] for (a,w) in E if a==u)]
removed=[e for e in E if e not in red]
# job-priority Kahn
indeg={v:0 for v in V}
for a,b in E: indeg[b]+=1
h=[v for v in V if indeg[v]==0]; heapq.heapify(h); order=[]
while h:
    u=heapq.heappop(h); order.append(u)
    for a,b in E:
        if a==u:
            indeg[b]-=1
            if indeg[b]==0: heapq.heappush(h,b)
rank={v:i+1 for i,v in enumerate(order)}
fig,axs=plt.subplots(1,2,figsize=(12,4.2))
for ax,(edges,ttl,hl) in zip(axs,[(E,"(a) DAG as built: edge 1→3 is implied by 1→2→3",removed),(red,"(b) After Reduce(): transitive reduction, labelled with topological rank",[])]):
    for (u,v) in edges:
        (x1,y1),(x2,y2)=pos[u],pos[v]
        col=C["hl"] if (u,v) in hl else C["box"]
        rad=-0.35 if (u,v)==(1,3) else 0.0
        ax.annotate("",xy=(x2-0.13*(x2-x1)/max(1e-9,np.hypot(x2-x1,y2-y1)),y2-0.13*(y2-y1)/max(1e-9,np.hypot(x2-x1,y2-y1))),xytext=(x1,y1),
                    arrowprops=dict(arrowstyle="->",color=col,lw=2 if (u,v) in hl else 1.4,ls="--" if (u,v) in hl else "-",connectionstyle=f"arc3,rad={rad}"))
    for v,(x,y) in pos.items():
        ax.add_patch(plt.Circle((x,y),0.13,fc=C["fill"],ec=C["s1"],lw=1.5)); ax.text(x,y,str(v),ha="center",va="center",fontsize=10)
        if ax is axs[1]: ax.text(x+0.17,y+0.15,f"#{rank[v]}",fontsize=8.5,color=C["pt"])
    ax.set_title(ttl,fontsize=10); clean(ax,((-0.5,3.1),(-2.0,1.6)))
axs[0].text(1.4,1.05,"redundant 1→3",color=C["hl"],fontsize=8.5)
axs[1].text(-0.45,-1.95,"order (min job index first): "+", ".join(map(str,order)),fontsize=8.5,color=C["pt"])
fig.suptitle("ScheduleEventDag example from EventDagTests.TopoSortBigger (node label = job index)",fontsize=10.5)
fig.tight_layout(); go(fig,"dag_reduce_topo"); print(order, removed)
