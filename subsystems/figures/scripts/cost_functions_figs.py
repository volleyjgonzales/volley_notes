from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","20-cost_functions")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
def trap(d,v,a):  # verbatim math of cost_functions.cpp Trapezoid
    return 2*np.sqrt(d/a) if d < v*v/a else v/a + d/v
def tad(s,L,v,a): # TimeAtDistance
    if s<=0: return 0.0
    if s>=L: return trap(L,v,a)
    if L < v*v/a:
        if s<=L/2: return np.sqrt(2*s/a)
        return 2*np.sqrt(L/a)-np.sqrt(2*(L-s)/a)
    da=0.5*v*v/a; ta=v/a
    if s<=da: return np.sqrt(2*s/a)
    if s<=L-da: return ta+(s-da)/v
    return v/a+L/v-np.sqrt(2*(L-s)/a)
v,a=1.0,0.2   # MotionCostParams default locomote (unloaded)
fig,axs=plt.subplots(1,3,figsize=(14,4.2))
ax=axs[0]
for L,col,lab in [(12.0,C["s1"],"12 m: trapezoid"),(3.0,C["s2"],"3 m: triangle (d < v²/a = 5 m)")]:
    T=trap(L,v,a); t=np.linspace(0,T,400)
    if L>=v*v/a: vel=np.minimum.reduce([a*t, np.full_like(t,v), a*(T-t)])
    else: vel=np.minimum(a*t,a*(T-t))
    ax.plot(t,vel,color=col,lw=2,label=f"{lab}, {T:.1f} s")
ax.axhline(v,color=C["aux"],ls=":",lw=1); ax.text(0.3,v+.02,"vmax = 1.0 m/s",fontsize=8,color=C["aux"])
ax.set_xlabel("time [s]"); ax.set_ylabel("speed [m/s]"); ax.set_title("(a) Velocity profiles (locomote defaults)",fontsize=10); ax.legend(fontsize=8,loc="lower center"); ax.grid(alpha=.3); ax.set_ylim(0,1.15)
ax=axs[1]; L=12.0; s=np.linspace(0,L,400); t=[tad(x,L,v,a) for x in s]
ax.plot(t,s,color=C["s1"],lw=2)
for node in (3.0,6.5,9.0):   # three intermediate nodes of a coalesced run
    tn=tad(node,L,v,a); ax.plot([tn,tn],[0,node],":",color=C["hl"]); ax.plot(tn,node,"o",color=C["hl"]); ax.text(tn+.3,node-.6,f"node at {node:g} m\nt = {tn:.2f} s",fontsize=8,color=C["hl"])
ax.set_xlabel("time [s]"); ax.set_ylabel("distance covered s [m]"); ax.set_title("(b) TimeAtDistance: per-node times in one run",fontsize=10); ax.grid(alpha=.3)
ax=axs[2]; N=np.arange(1,9); e=2.5
per=[n*trap(e,v,a) for n in N]; coal=[trap(n*e,v,a) for n in N]
ax.plot(N,per,"o-",color=C["s2"],label="per-edge sum (stop at every node)"); ax.plot(N,coal,"o-",color=C["s1"],label="coalesced MotionRun (one trapezoid)")
ax.set_xlabel("number of 2.5 m codirectional edges"); ax.set_ylabel("duration [s]"); ax.set_title("(c) Why runs are coalesced",fontsize=10); ax.legend(fontsize=8); ax.grid(alpha=.3)
for n,p,c in zip(N,per,coal):
    if n in (4,8): ax.text(n-.15,(p+c)/2,f"{p:.0f} s vs {c:.0f} s",fontsize=8,ha="right")
fig.tight_layout(); go(fig,"trapezoid_profiles"); print([round(x,2) for x in per],[round(x,2) for x in coal])
