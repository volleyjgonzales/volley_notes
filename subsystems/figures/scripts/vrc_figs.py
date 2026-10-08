from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","17-vrc")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# Re-implementation of MockHWDriver::Move (common Motion1D bang-bang profile, dt = kMoveInterval = 50 ms).
# Defaults from launch/single.launch.py (floors 0,1,2 at 0,5,10 m) and MockHWDriverConfig (0.254 m/s, 0.2 m/s^2, gates 3 s).
Z={0:0.0,1:5.0,2:10.0}; V,A,DT,GATE=0.254,0.2,0.05,3.0
def move(frm,to):
    s=v=0.0; tot=abs(Z[to]-Z[frm]); d=1 if Z[to]>Z[frm] else -1; t=0; T=[0];H=[Z[frm]];F=[frm]
    while not (s>=tot-1e-9 and v<=1e-6):
        rem=tot-s; acc=-A if rem<=v*v/(2*A) else A
        v=min(max(v+acc*DT,0),V); s+=v*DT
        if s>=tot: s=tot; v=0
        t+=DT; h=Z[frm]+d*s; f=max(k for k,zz in Z.items() if zz<=h+1e-12) if h>=min(Z.values()) else min(Z)
        T.append(t);H.append(h);F.append(f)
    return np.array(T),np.array(H),np.array(F)
fig,axs=plt.subplots(2,2,figsize=(12,6.2),sharex="col",gridspec_kw=dict(height_ratios=[2,1]))
for c,(frm,to) in enumerate([(0,2),(2,0)]):
    T,H,F=move(frm,to); close0=GATE; T=T+close0  # gate closing first (ClosingState), then move
    tend=T[-1]; topen=tend+GATE
    succ=T[np.argmax(F==to)]
    ax=axs[0,c]; ax.plot(np.r_[0,T,topen],np.r_[Z[frm],H,Z[to]],color=C["s1"],lw=2,label="carriage height")
    for k,zz in Z.items(): ax.axhline(zz,color=C["aux"],ls=":",lw=.8); ax.text(topen+0.6,zz,f"floor {k}",va="center",ha="left",fontsize=8,color=C["aux"])
    ax.axvspan(0,close0,color=C["s2"],alpha=.12); ax.text(close0/2,11,"close\ngate",ha="center",fontsize=8,color=C["s2"])
    ax.axvspan(tend,topen,color=C["pt"],alpha=.12); ax.text((tend+topen)/2,11,"open\ngate",ha="center",fontsize=8,color=C["pt"])
    ax.axvline(succ,color=C["hl"],lw=2); ax.text(succ+0.5,6.5 if c==0 else 8.0,f"goal succeeds\n(t = {succ:.1f} s)",color=C["hl"],fontsize=8.5)
    ax.axvline(topen,color=C["pt"],lw=1.2,ls="--"); ax.text(topen-0.5,2.5 if c==0 else 6,f"actually done\n(t = {topen:.1f} s)",color=C["pt"],fontsize=8.5,ha="right")
    ax.set_xlim(-1,topen+6); ax.set_ylabel("height [m]"); ax.set_title(f"Move floor {frm} → {to}",fontsize=10); ax.set_ylim(-0.8,12.5)
    ax=axs[1,c]; ax.step(np.r_[0,T,topen],np.r_[frm,F,to],where="post",color=C["s2"],lw=2,label="driver current_floor")
    ax.axhline(to,color=C["hl"],ls=":",lw=1); ax.set_yticks([0,1,2]); ax.set_ylabel("current_floor"); ax.set_xlabel("time [s]")
    ax.axvline(succ,color=C["hl"],lw=2)
fig.suptitle("RosNode::UpdateCallback succeeds the VrcMove goal when current_floor == requested_floor (default launch geometry and kinematics)",fontsize=10,y=1.0)
fig.tight_layout(); go(fig,"move_goal_timing"); print("ok")
