from style import *
import os; HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","04-vrc_interfaces")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# Illustrative VRC move: floor 0 -> floor 3. Floor heights, timings and gate behaviour are ASSUMED for illustration.
H=[0.0,3.5,7.0,10.5]; vmax,a=1.2,0.6
t0c,t0m=1.0,3.0
t1m=t0m+(10.5/vmax+vmax/a); t1o,tend=t1m+1.5,t1m+3.0
t=np.linspace(0,tend,1601)
def height(tt):
    if tt<t0m: return H[0]
    d=H[3]-H[0]; ta=vmax/a; T=d/vmax+ta; x=tt-t0m
    if x>=T: return H[3]
    if x<ta: return .5*a*x*x
    if x<T-ta: return .5*a*ta*ta+vmax*(x-ta)
    y=T-x; return d-.5*a*y*y
h=np.array([height(x) for x in t])
cur=np.array([max(i for i,hh in enumerate(H) if hh<=x+1e-9) for x in h])
req=np.where((t>=t0m)&(t<t1m),3,cur)  # literal reading of VrcReport comment: target only while STATE_MOVING, else = current_floor
fig,axs=plt.subplots(3,1,figsize=(11,7.2),sharex=True,gridspec_kw=dict(height_ratios=[3,1.6,1.3]))
ax=axs[0]; ax.plot(t,h,color=C["s1"],lw=2.5,label="carriage_height_m")
for i,hh in enumerate(H): ax.axhline(hh,color=C["aux"],lw=.7,ls=":"); ax.text(tend+.1,hh,f"floor {i}",va="center",fontsize=9,color=C["aux"])
for i in (1,2):
    tc=t[np.argmax(h>=H[i])]; ax.plot(tc,H[i],"o",color=C["s2"]); ax.annotate(f"passes floor {i}:\ncurrent_floor → {i}",xy=(tc,H[i]),xytext=(tc-3.4,H[i]+1.6),fontsize=8.5,color=C["s2"],arrowprops=dict(arrowstyle="->",color=C["s2"]))
ax.set_ylabel("height [m]"); ax.set_title("VrcReport fields during a move from floor 0 to floor 3 (illustrative)",loc="left"); ax.legend(loc="upper left",fontsize=9)
ax=axs[1]; ax.step(t,cur,where="post",color=C["s2"],lw=2,label="current_floor"); ax.step(t,req,where="post",color=C["pt"],lw=2,ls="--",label="requested_floor")
ax.set_yticks(range(4)); ax.set_ylabel("floor"); ax.legend(loc="upper left",fontsize=9); ax.set_ylim(-.4,3.6)
ax.annotate("during CLOSING the target is not\nvisible in the report (= current_floor)",xy=(2.0,0),xytext=(4.3,1.3),fontsize=8.5,color=C["pt"],arrowprops=dict(arrowstyle="->",color=C["pt"]))
ax=axs[2]; segs=[(0,t0c,"IDLE","#d8efdd"),(t0c,t0m,"CLOSING","#fde9c8"),(t0m,t1m,"MOVING","#d6e6f5"),(t1m,t1o,"OPENING","#fde9c8"),(t1o,tend,"IDLE","#d8efdd")]
for a_,b_,lab,col in segs: ax.add_patch(plt.Rectangle((a_,1.1),b_-a_,.8,fc=col,ec="white")); ax.text((a_+b_)/2,1.5,lab,ha="center",va="center",fontsize=8.5)
gates=[(0,t0c,"OPEN"),(t0c,t0m,"CLOSING"),(t0m,tend,"CLOSED")]; gates3=[(0,t1m,"CLOSED"),(t1m,t1o,"OPENING"),(t1o,tend,"OPEN")]
for row,(gs,y) in enumerate([(gates,.1),(gates3,-.9)]):
    for a_,b_,lab in gs: ax.add_patch(plt.Rectangle((a_,y),b_-a_,.8,fc="#eeeeee" if lab=="CLOSED" else "#fde9c8" if "ING" in lab else "#ffffff",ec=C["aux"],lw=.5)); ax.text((a_+b_)/2,y+.4,lab,ha="center",va="center",fontsize=8)
ax.set_yticks([1.5,.5,-.5]); ax.set_yticklabels(["VrcState","gate @ floor 0","gate @ floor 3"],fontsize=8.5); ax.set_ylim(-1,2)
ax.set_xlabel("time [s]   (state sequence and gate timing are inferred from the enum names, not defined by the interface)")
for a_ in axs: a_.set_xlim(0,tend+1.3)
fig.tight_layout(); go(fig,"vrc_move_timeline")
print("ok")
