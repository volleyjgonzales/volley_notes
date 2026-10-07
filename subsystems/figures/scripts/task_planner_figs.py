from style import *
import itertools, os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","09-task_planner")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
perms=list(itertools.permutations(range(4)))
def mx(C,p): return max(C[i,p[i]] for i in range(4))
def sm(C,p): return sum(C[i,p[i]] for i in range(4))
def heat(ax,C,p,ttl,rl,cl):
    ax.imshow(C,cmap="Blues",vmin=C.min()-3,vmax=C.max()+6)
    for i in range(4):
        for j in range(4):
            sel=p[i]==j
            ax.text(j,i,f"{C[i,j]:g}",ha="center",va="center",fontsize=11,weight="bold" if sel else "normal")
            if sel: ax.add_patch(plt.Rectangle((j-.45,i-.45),.9,.9,fill=False,ec="#c0392b",lw=2.5))
    ax.set_xticks(range(4)); ax.set_xticklabels(cl); ax.set_yticks(range(4)); ax.set_yticklabels(rl)
    ax.set_title(f"{ttl}\nmax = {mx(C,p):g}, sum = {sm(C,p):g}",fontsize=10)

# 1. Bottleneck vs sum objective (matrix chosen to make the difference visible)
C=np.array([[1,17,4,2],[18,18,19,18],[17,2,8,8],[19,19,18,4]],float)
code=(2,1,0,3)   # matching returned by BottleneckAssignment for this matrix (C++ run, g++ 13 / libstdc++)
b=min(mx(C,p) for p in perms); bopt=min([p for p in perms if mx(C,p)==b],key=lambda p:sm(C,p))
sopt=min(perms,key=lambda p:sm(C,p))
fig,axs=plt.subplots(1,3,figsize=(13,4.3))
rl=["AGV 1","AGV 2","AGV 3","AGV 4"]; cl=["T1","T2","T3","T4"]
heat(axs[0],C,code,"Returned by BottleneckAssignment",rl,cl)
heat(axs[1],C,bopt,"Best bottleneck-optimal (min sum among max = 18)",rl,cl)
heat(axs[2],C,sopt,"Minimum-sum assignment",rl,cl)
fig.suptitle("Same bottleneck (18) does not mean same quality: the code returns an arbitrary matching under the threshold",fontsize=11,y=1.02)
fig.tight_layout(); go(fig,"bottleneck_vs_sum")

# 2. Threshold search trace on the textbook example (Burkard et al. p.175), replicating the code's loop
T=np.array([[8,2,3,3],[2,7,5,8],[0,9,8,4],[2,5,6,3]],float)
def feas(t): return any(all(T[i,p[i]]<=t for i in range(4)) for p in perms)
costs=sorted(T.flatten()); lo,hi=min(costs),max(costs); bounded=list(costs); trace=[]
while bounded:
    v=sorted(bounded); n=len(v); med=v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2
    f=feas(med); trace.append((lo,hi,med,f,n)); lo,hi=(lo,med) if f else (med,hi); bounded=[c for c in costs if lo<c<hi]
fig,ax=plt.subplots(figsize=(11,3.2))
for k,(lo_,hi_,med,f,n) in enumerate(trace):
    y=len(trace)-k
    ax.plot([lo_,hi_],[y,y],color="#7a7a7a",lw=8,alpha=.3,solid_capstyle="butt")
    ax.plot(med,y,"o",ms=11,color="#2a9d4a" if f else "#c0392b")
    ax.text(9.4,y,(f"iteration {k+1}: all {n} costs" if k==0 else f"iteration {k+1}: {n} costs strictly inside bracket")+f", median {med:g} → "+("perfect matching exists: upper := median" if f else "no perfect matching: lower := median"),va="center",fontsize=8.5)
ax.plot(costs,[0.35]*len(costs),"|",color="black",ms=10); ax.text(-0.3,0.35,"edge costs",ha="right",va="center",fontsize=8.5)
ax.axvline(5,color="#1f6fb4",ls="--",lw=1.2); ax.text(5.1,len(trace)+.55,"z* = 5",color="#1f6fb4",fontsize=9)
ax.set_yticks([]); ax.set_xlim(-1.5,25); ax.set_ylim(0,len(trace)+.9); ax.set_xlabel("threshold (edge cost)")
ax.set_title("Threshold search on the textbook 4×4 example: bracket [lower, upper] (grey), median tested (dot)",loc="left",fontsize=10)
for s in ("left","right","top"): ax.spines[s].set_visible(False)
go(fig,"threshold_search"); print(trace)
