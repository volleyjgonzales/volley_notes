from style import *
import os
from collections import deque
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","23-bay")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
IN=0.0254; L=14*12*IN; MT=800.0                       # common/constants.hpp kTrayLength, kTrayMass
K_STD=1.5; MIN_VEH=500; MIN_AXLE=0.35*MIN_VEH; FRAC=0.15; WIN=10   # axle_counter.cpp / .hpp
class Window:
    def __init__(s): s.d=deque(maxlen=WIN)
    def reset(s): s.d.clear()
    def update(s,x): s.d.append(x)
    def full(s): return len(s.d)==WIN
    def mean(s): return float(np.mean(s.d)) if s.d else 0.0
    def std(s): return float(np.std(s.d,ddof=1)) if len(s.d)>1 else 0.0
class AxleCounter:   # line-for-line port of AxleCounter::Update
    def __init__(s):
        s.n=0; s.before=None; s.front=0.0; s.tray=None; s.wb=None; s.first=None; s.tot=Window(); s.diff=Window(); s.delta=0.0
    def two(s): return s.n==2 and s.before is None
    def one(s): return s.n==1 and s.before is None
    def payload(s):
        if s.n==2:
            total = s.before if s.before is not None else s.tot.mean()
            return max(total-(s.tray or 0),0.0)
        return 0.0
    def reset_vehicle(s): s.n=0; s.front=0.0; s.wb=None; s.first=None
    def update(s,sys_m,pat_m,blocked):
        if blocked:
            if s.tray is not None and s.before is None: s.before=s.tot.mean()
            s.tot.reset(); s.diff.reset()
        else:
            s.tot.update(sys_m+pat_m); s.diff.update(sys_m-pat_m)
        if s.before is None and s.tot.full():
            dm=FRAC*MT
            if s.tot.std()<dm:
                m=s.tot.mean()
                if MT-dm<=m<=MT+dm: s.tray=m; s.reset_vehicle()
                if m<dm: s.tray=None; s.reset_vehicle()
        if s.tray is not None and s.before is not None and s.tot.full():
            s.delta=max(K_STD*s.tot.std(),MIN_AXLE)
            if s.tot.mean()>s.before+s.delta: s.n+=1
            elif s.tot.mean()<s.before-s.delta: s.n-=1
            s.n=int(np.clip(s.n,0,2)); s.before=None
        if s.two() and s.wb is None:
            h=L/2; rear=s.payload()-s.front; ymin=s.first or 0
            y=(h*s.diff.mean()+rear*(h-ymin))/s.front; s.wb=h+y-ymin
        if s.one():
            s.front=s.tot.mean()-(s.tray or 0)
            if s.first is None:
                y=L*s.diff.mean()/(2*s.front); s.first=L/2+y
rng=np.random.default_rng(3)
mf,mr,wb_true,v=900.0,700.0,2.70,0.5; dt=0.02; sens=0.15; sigma=4.0
T=np.arange(0,14,dt); ac=AxleCounter()
rows=[]
for t in T:
    sf=min(-1.0+v*t, 3.55); sr=sf-wb_true    # front/rear axle positions from the patron edge [m]; the car stops when parked
    on=[(m,s) for m,s in ((mf,sf),(mr,sr)) if 0<=s<=L]
    sysm=MT/2+sum(m*s/L for m,s in on); patm=MT/2+sum(m*(1-s/L) for m,s in on)
    sysm+=rng.normal(0,sigma); patm+=rng.normal(0,sigma)
    blocked=any(abs(s)<sens or abs(s-L)<sens for s in (sf,sr))   # tire sensors at both tray edges
    ac.update(sysm,patm,blocked)
    rows.append((t,sysm+patm,blocked,ac.n,ac.wb))
R=np.array([(r[0],r[1],r[2],r[3],np.nan if r[4] is None else r[4]) for r in rows],float)
fig,axs=plt.subplots(2,1,figsize=(11,5.4),sharex=True,gridspec_kw={"height_ratios":[2,1]})
ax=axs[0]; ax.plot(R[:,0],R[:,1],color=C["s1"],lw=1,label="measured total mass (4 load cells, σ = 4 kg each side)")
for i in range(len(R)-1):
    if R[i,2]: ax.axvspan(R[i,0],R[i+1,0],color=C["hl"],alpha=.12,lw=0)
ax.axhline(MT,color=C["aux"],ls=":",lw=1); ax.text(0.1,MT+20,"tray 800 kg",fontsize=8,color=C["aux"])
ax.set_ylabel("kg"); ax.legend(fontsize=8,loc="upper left"); ax.grid(alpha=.3)
ax.set_title("AxleCounter (re-implemented): a 1600 kg car with 2.70 m wheelbase drives onto the tray at 0.5 m/s and stops",fontsize=9.5,loc="left")
ax.text(13.9,MT+1250,"shaded: tire sensor blocked",ha="right",fontsize=8,color=C["hl"])
ax=axs[1]; ax.step(R[:,0],R[:,3],where="post",color=C["pt"],lw=2,label="num_axles_on_tray")
wbi=np.where(~np.isnan(R[:,4]))[0]
if len(wbi): ax.text(R[wbi[0],0]+0.2,1.3,f"wheelbase estimate = {R[wbi[0],4]:.2f} m (true 2.70 m)",fontsize=8.5)
ax.set_ylim(-0.3,2.6); ax.set_yticks([0,1,2]); ax.set_xlabel("time [s]"); ax.grid(alpha=.3); ax.legend(fontsize=8,loc="upper left")
fig.tight_layout(); go(fig,"axle_counter"); print("wheelbase", R[wbi[0],4] if len(wbi) else None, "final axles", R[-1,3])
