from style import *
import os; HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","02-rclcppx")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# 1. Logging condition timeline (one call site, called every 0.25 s, duration 1 s)
calls=np.round(np.arange(0.25,5.01,0.25),2); d=1.0
expr=lambda t: 1.6<=t<=2.4 or t>=4.4
rows=[]
rows.append(("LOG_INFO",[True]*len(calls)))
rows.append(("LOG_INFO_ONCE",[i==0 for i in range(len(calls))]))
def thr(skip):
    last=0.0; first=True; out=[]
    for t in calls:
        ok = t >= last + d
        if ok:
            last=t
            if skip and first: first=False; out.append(False); continue
        out.append(ok)
    return out
rows.append(("LOG_INFO_THROTTLE(1s)",thr(False)))
rows.append(("LOG_INFO_SKIPFIRST_THROTTLE(1s)",thr(True)))
rows.append(("LOG_INFO_IF(expr)",[expr(t) for t in calls]))
fig,ax=plt.subplots(figsize=(11,3.9))
for r,(name,emit) in enumerate(rows):
    y=len(rows)-1-r; ax.axhline(y,color=C["aux"],lw=.4)
    for t,e in zip(calls,emit):
        ax.plot(t,y,"o",ms=8,color=C["pt"] if e else "white",mec=C["pt"] if e else C["aux"])
    ax.text(-.1,y,name,ha="right",va="center",fontsize=9,family="DejaVu Sans Mono")
ax.axvspan(1.6,2.4,ymin=0,ymax=.17,color=C["s2"],alpha=.15); ax.axvspan(4.4,5.1,ymin=0,ymax=.17,color=C["s2"],alpha=.15)
ax.text(2.0,-.62,"expr true",ha="center",fontsize=8,color=C["s2"]); ax.text(4.75,-.62,"expr true",ha="center",fontsize=8,color=C["s2"])
for k in range(1,6): ax.axvline(k,color=C["aux"],lw=.4,ls=":")
ax.set_yticks([]); ax.set_xlim(-3.3,5.3); ax.set_ylim(-.9,len(rows)-.2); ax.set_xticks(range(0,6)); ax.set_xlabel("clock time of each call [s]   (call site hit every 0.25 s; clock starts at 0, e.g. sim time)")
ax.annotate("throttle state starts at last_logged = 0:\nnothing before t = duration when the clock starts at 0",xy=(1.0,2),xytext=(1.25,2.45),fontsize=8,color=C["hl"],arrowprops=dict(arrowstyle="->",color=C["hl"]))
for s in ("left","right","top"): ax.spines[s].set_visible(False)
ax.plot([],[],"o",color=C["pt"],label="emitted"); ax.plot([],[],"o",color="white",mec=C["aux"],label="suppressed"); ax.legend(loc="upper right",fontsize=8,bbox_to_anchor=(1.0,1.12),ncol=2,frameon=False)
ax.set_title("Per-call-site emission rules of the LOG_* macro families",loc="left")
go(fig,"logging_conditions")

# 2. QoS compatibility matrix (reliability and durability rules)
profiles=["BestEffort","Reliable","Latched"]; rel={"BestEffort":0,"Reliable":1,"Latched":1}; dur={"BestEffort":0,"Reliable":0,"Latched":1}
fig,ax=plt.subplots(figsize=(6.4,4.6))
for i,p in enumerate(profiles):
    for j,s in enumerate(profiles):
        okr=rel[p]>=rel[s]; okd=dur[p]>=dur[s]; ok=okr and okd
        why="" if ok else ("reliability" if not okr else "")+(" + " if (not okr and not okd) else "")+("durability" if not okd else "")
        ax.add_patch(plt.Rectangle((j,2-i),1,1,fc="#d8efdd" if ok else "#f6d5d1",ec="white",lw=3))
        ax.text(j+.5,2-i+.58,"connects" if ok else "no match",ha="center",fontsize=10,weight="bold",color=C["pt"] if ok else C["hl"])
        ax.text(j+.5,2-i+.32,"" if ok else why,ha="center",fontsize=8,color=C["hl"])
        if ok and p=="Latched" and s!="Latched": ax.text(j+.5,2-i+.32,"(no history replay)",ha="center",fontsize=8,color=C["aux"])
        if ok and p=="Latched" and s=="Latched": ax.text(j+.5,2-i+.32,"late joiners get last N",ha="center",fontsize=8,color=C["aux"])
for k,n in enumerate(profiles):
    ax.text(k+.5,3.12,n,ha="center",fontsize=9.5,family="DejaVu Sans Mono"); ax.text(-.08,2-k+.5,n,ha="right",va="center",fontsize=9.5,family="DejaVu Sans Mono")
ax.text(1.5,3.45,"subscription profile",ha="center",weight="bold"); ax.text(-1.25,1.5,"publisher profile",rotation=90,va="center",weight="bold")
ax.set_xlim(-1.4,3.05); ax.set_ylim(-.05,3.65); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("rclcppx QoS presets: which publisher/subscription pairs match",fontsize=10.5)
go(fig,"qos_compatibility")
print("ok")
