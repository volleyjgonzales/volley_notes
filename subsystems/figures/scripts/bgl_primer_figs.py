from style import *
from matplotlib.patches import FancyArrowPatch
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","primer-bgl")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# Tiny illustrative garage: A(0,0) headings {90}; B(4,0) headings {0,90}, rotation allowed; C(4,4) headings {0}
nodes={"A":(0,0),"B":(4,0),"C":(4,4)}
poses=[("A",-90),("A",90),("B",-90),("B",0),("B",90),("B",180),("C",0),("C",180)]  # lexicographic: node id, then heading
idx={p:i for i,p in enumerate(poses)}
def ppos(p,r=0.85):
    n,h=p; x,y=nodes[n]; a=np.radians(h+90)  # AGV faces body +y = heading + 90 deg
    return (x+r*np.cos(a), y+r*np.sin(a))
trans=[(("A",90),("B",90)),(("A",-90),("B",-90)),(("B",0),("C",0)),(("B",180),("C",180))]
rot=[(("B",-90),("B",0)),(("B",0),("B",90)),(("B",90),("B",180)),(("B",180),("B",-90))]
fig,axs=plt.subplots(1,2,figsize=(13,6))
ax=axs[0]
for a,b in [("A","B"),("B","C")]:
    ax.plot(*zip(nodes[a],nodes[b]),color=C["box"],lw=2.5)
for n,(x,y) in nodes.items():
    ax.add_patch(plt.Circle((x,y),0.35,fc=C["fill"],ec=C["s1"],lw=2)); ax.text(x,y,n,ha="center",va="center",fontsize=12,weight="bold")
ax.text(0,-0.9,"headings {90°}",ha="center",fontsize=8.5); ax.text(4.9,-0.6,"headings {0°, 90°}\nrotation allowed",fontsize=8.5); ax.text(4.5,4.5,"headings {0°}",fontsize=8.5)
ax.text(-1.2,3.6,"Layout::graph_\nadjacency_list<listS, vecS, undirectedS>\nvertex = index into nodes_\n|V| = 3, |E| = 2 (undirected)",fontsize=9,va="top",family="monospace")
ax.set_title("(a) Layout graph: nodes and undirected edges",fontsize=10); clean(ax,((-1.5,6.5),(-1.5,5.3)))
ax=axs[1]
cols={"A":0,"B":4,"C":8}; rows={-90:0,0:1,90:2,180:3}
def P(p): return (cols[p[0]], rows[p[1]]*1.4)
def arr(p,q,col,rad):
    a=FancyArrowPatch(P(p),P(q),arrowstyle="-|>",mutation_scale=11,color=col,lw=1.4,connectionstyle=f"arc3,rad={rad}",shrinkA=13,shrinkB=13); ax.add_patch(a)
for p,q in trans: arr(p,q,C["s1"],0.10); arr(q,p,C["s1"],0.10)
for p,q in rot:
    r=0.5 if (p[1],q[1])==(180,-90) else 0.25
    arr(p,q,C["pt"],r); arr(q,p,C["pt"],r)
for h,rw in rows.items(): ax.text(-3.2,rw*1.4,f"heading {h}°",va="center",fontsize=8.5,color=C["aux"])
for n,c in cols.items(): ax.text(c,-1.0,f"node {n}",ha="center",fontsize=9,color=C["aux"])
for p in poses:
    x,y=P(p); ax.add_patch(plt.Circle((x,y),0.32,fc=C["fill"],ec=C["s1"],lw=1.5)); ax.text(x,y,str(idx[p]),ha="center",va="center",fontsize=10,weight="bold")
    ax.text(x+0.38,y+0.25,f"{p[0]}@{p[1]}",fontsize=7.5,color=C["aux"])
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],color=C["s1"],lw=2,label="translation edge (here: locomote)"),Line2D([0],[0],color=C["pt"],lw=2,label="rotation edge (nearest heading each way)")],fontsize=8,loc="upper center",ncol=2,bbox_to_anchor=(0.5,1.0))
ax.text(-3.3,-2.4,"BoostPoseGraph = adjacency_list<vecS, vecS, bidirectionalS,\n    GaragePose, property<edge_index_t, size_t, Transition>>\n|V| = 8 poses (vertex descriptor = pose index),  |E| = 8 translation + 8 rotation = 16 directed edges",fontsize=8.3,family="monospace")
ax.set_title("(b) GarageGraph: one vertex per (node, heading), typed directed edges",fontsize=10); clean(ax,((-3.4,9.6),(-2.8,6.0)))
fig.tight_layout(); go(fig,"layout_vs_garage_graph"); print("ok")

# ---- Figure 2: vertex renumbering on removal (vecS vertex storage), as handled by planner_core::DagBase ----
fig,axs=plt.subplots(1,2,figsize=(12,3.3))
labels=["e_a","e_b","e_c","e_d","e_e"]
edges=[(0,1),(1,2),(2,3),(1,3),(3,4)]
def draw(ax,verts,E,ttl,hl=None):
    xs={v:i*1.6 for i,v in enumerate(verts)}
    for u,v in E:
        ax.annotate("",xy=(xs[v]-0.3,0),xytext=(xs[u]+0.3,0),arrowprops=dict(arrowstyle="->",color=C["box"],connectionstyle=f"arc3,rad={-0.5 if v-u>1 else 0}"))
    for i,v in enumerate(verts):
        ax.add_patch(plt.Circle((xs[v],0),0.3,fc=C["fill"],ec=C["hl"] if hl and v in hl else C["s1"],lw=2)); ax.text(xs[v],0,str(i),ha="center",va="center",fontsize=11,weight="bold")
        ax.text(xs[v],-0.6,labels[v],ha="center",fontsize=9,family="monospace")
    ax.set_title(ttl,fontsize=10); clean(ax,((-0.6,7.0),(-1.0,1.3)))
draw(axs[0],[0,1,2,3,4],edges,"(a) Before: vertex i holds event e_*; caller cached v = 3 for e_d",hl=[3])
draw(axs[1],[0,2,3,4],[(2,3),(3,4)],"(b) After RemoveVertex(1): Boost renumbers 2→1, 3→2, 4→3",hl=[4])
axs[1].text(-0.4,0.95,"ptr_to_vertex_ is updated by DagBase, but the cached v = 3 now means e_e, not e_d",fontsize=8.5,color=C["hl"])
fig.tight_layout(); go(fig,"vecs_vertex_renumbering")

# ---- Figure 3: admissibility of a straight-line time heuristic against the trapezoid edge cost ----
d=np.linspace(0,12,400); v,a=0.8,0.2
T=np.where(d<v*v/a, 2*np.sqrt(d/a), v/a+d/v)
fig,ax=plt.subplots(figsize=(8,4))
ax.plot(d,T,color=C["s1"],lw=2,label="edge cost  T(d), loaded locomote (v = 0.8 m/s, a = 0.2 m/s²)")
ax.plot(d,d/v,color=C["pt"],lw=2,ls="--",label="lower bound  d / v  (v = 0.8 m/s)")
ax.plot(d,d/1.0,color=C["hl"],lw=1,ls=":",label="heuristic  d / v_max  (v_max = 1.0 m/s, fastest mode)")
ax.fill_between(d,d/v,T,color=C["s1"],alpha=.08)
ax.set_xlabel("straight-line distance d [m]"); ax.set_ylabel("seconds"); ax.grid(alpha=.3); ax.legend(fontsize=8.5)
ax.set_title("T(d) ≥ d/v ≥ d/v_max: a Euclidean time heuristic never overestimates an edge's trapezoid cost",fontsize=9.5,loc="left")
go(fig,"heuristic_admissibility"); print("ok2")

# ---- Figure: the four steps of expanding 3 layout nodes into 8 poses and 16 edges ----
fig,axs=plt.subplots(1,4,figsize=(16,4.6))
NP={"A":(-2.0,0),"B":(4,0),"C":(4,4)}  # drawn with A moved left for legibility (not to scale)
stored={"A":[90],"B":[0,90],"C":[0]}
allowed={"A":[-90,90],"B":[-90,0,90,180],"C":[0,180]}
def base(ax,title):
    for a,b in [("A","B"),("B","C")]: ax.plot(*zip(NP[a],NP[b]),color=C["aux"],lw=1,ls=":")
    for n,(x,y) in NP.items():
        ax.add_patch(plt.Circle((x,y),0.25,fc=C["fill"],ec=C["box"],lw=1)); ax.text(x,y,n,ha="center",va="center",fontsize=9,weight="bold")
    ax.set_title(title,fontsize=9.5); clean(ax,((-3.8,6.2),(-2.8,5.8)))
def pose_tick(ax,n,h,col,lw=2,label=None):
    x,y=NP[n]; a=np.radians(h+90)
    ax.annotate("",xy=(x+1.0*np.cos(a),y+1.0*np.sin(a)),xytext=(x+0.28*np.cos(a),y+0.28*np.sin(a)),arrowprops=dict(arrowstyle="-|>",color=col,lw=lw))
    if label: ax.text(x+1.5*np.cos(a),y+1.5*np.sin(a)+0.25*abs(np.cos(a)),label,ha="center",va="center",fontsize=7.5,color=col)
base(axs[0],"1. Stored headings (0–179°) per node")
for n,hs in stored.items():
    for h in hs: pose_tick(axs[0],n,h,C["s1"],label=f"{h}°")
axs[0].text(-3.6,-2.6,"arrow = AGV drive direction (heading + 90°)",fontsize=7.5,color=C["aux"])
base(axs[1],"2. Add reciprocals, wrap to (−180°, 180°]: 8 poses")
order={("A",-90):0,("A",90):1,("B",-90):2,("B",0):3,("B",90):4,("B",180):5,("C",0):6,("C",180):7}
for n,hs in allowed.items():
    for h in hs: pose_tick(axs[1],n,h,C["s1"] if h in stored[n] else C["pt"],label=f"#{order[(n,h)]} {h}°")
axs[1].text(-3.6,-2.6,"blue = stored, green = added reciprocal; #i = vertex index",fontsize=7.5,color=C["aux"])
base(axs[2],"3. Translations keep the heading: 8 edges")
for (n,h),(m,h2) in [(("A",-90),("B",-90)),(("A",90),("B",90)),(("B",0),("C",0)),(("B",180),("C",180))]:
    (x1,y1),(x2,y2)=NP[n],NP[m]; off=0.18 if h in (90,180) else -0.18
    dx,dy=(x2-x1),(y2-y1); L=np.hypot(dx,dy); nx_,ny_=-dy/L*off,dx/L*off
    axs[2].annotate("",xy=(x2+nx_-dx/L*0.35,y2+ny_-dy/L*0.35),xytext=(x1+nx_+dx/L*0.35,y1+ny_+dy/L*0.35),arrowprops=dict(arrowstyle="<|-|>",color=C["s1"],lw=1.4))
    axs[2].text((x1+x2)/2+nx_*3.2,(y1+y2)/2+ny_*3.2,f"@{h}°",fontsize=7.5,color=C["s1"],ha="center")
axs[2].text(-3.6,-2.6,"B@0 has no partner at A (A has no 0° pose):\nno edge. Same for B@−90 ↔ C.",fontsize=7.5,color=C["hl"])
base(axs[3],"4. Rotations on B (rotation allowed): 8 edges")
x,y=NP["B"]
for h in allowed["B"]: pose_tick(axs[3],"B",h,C["s1"],lw=1.5,label=f"{h}°")
for k in range(4):
    a1=np.radians(allowed["B"][k]+90); a2=np.radians(allowed["B"][(k+1)%4]+90)
    if a2<a1: a2+=2*np.pi
    t=np.linspace(a1+0.25,a2-0.25,30); axs[3].plot(x+0.65*np.cos(t),y+0.65*np.sin(t),color=C["pt"],lw=1.5)
axs[3].text(-3.6,-2.6,"each pose: ROT_LEFT and ROT_RIGHT to the\nnearest heading each way (π/2 rad each)",fontsize=7.5,color=C["pt"])
fig.tight_layout(); go(fig,"expansion_steps"); print("ok3")
