from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","15-yasminx")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
T=100.0  # step period [ms], illustrative
fig,ax=plt.subplots(figsize=(11.5,3.4))
ax.axhline(0,color="black",lw=.8)
# OnEntry
ax.barh(0,25,left=0,height=.5,color=C["pt"]); ax.text(12.5,.42,"OnEntry",ha="center",fontsize=8.5,color=C["pt"])
steps=[(25,30),(125,70),(225,160),(385,20)]   # (start, duration): third step overruns the period
for k,(s,d) in enumerate(steps):
    ax.barh(0,d,left=s,height=.5,color=C["s1"],alpha=.85,edgecolor="white",lw=1.5); ax.text(s+d/2,-.42,f"Step {k+1}",ha="center",fontsize=8.5,color=C["s1"])
for k in range(5): ax.axvline(25+k*T,color=C["aux"],ls=":",lw=.8)
ax.text(25+2*T+3,.62,"period T",fontsize=8,color=C["aux"])
ax.annotate("Step 3 overruns T:\nno sleep, Step 4 starts at once",xy=(385,0.25),xytext=(250,0.85),fontsize=8.5,color=C["s2"],arrowprops=dict(arrowstyle="->",color=C["s2"]))
cancel=410
ax.axvline(cancel,color=C["hl"],lw=1.5); ax.text(cancel+4,.95,"cancel_state()",ha="left",fontsize=8.5,color=C["hl"])
det=405+T  # next loop check after sleep (Step 4 ends at 405, sleeps until 425? phase) -> computed below
nxt=485
ax.annotate("",xy=(nxt,-.7),xytext=(cancel,-.7),arrowprops=dict(arrowstyle="<->",color=C["hl"]))
ax.text(nxt+5,-.7,"cancel latency: up to T, plus any Step in progress",ha="left",fontsize=8.5,color=C["hl"])
ax.barh(0,30,left=nxt,height=.5,color=C["s2"]); ax.text(nxt+15,.42,"OnExit",ha="center",fontsize=8.5,color=C["s2"])
ax.text(nxt+40,0,"→ yasminx.canceled",va="center",fontsize=9,color=C["hl"])
ax.set_yticks([]); ax.set_xlim(-10,700); ax.set_ylim(-1.1,1.15); ax.set_xlabel("time [ms] (illustrative, T = 100 ms)")
for sp in ("left","right","top"): ax.spines[sp].set_visible(False)
ax.set_title("LifecycleState::Execute: OnEntry, Step at a fixed period, cancel detected before the next Step, OnExit",loc="left",fontsize=10)
go(fig,"lifecycle_timing"); print("ok")
