from style import *
from matplotlib.patches import Rectangle, Polygon as MPoly
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","22-agvhito")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
LFB,LLR=2454.0,1494.0     # magnetic_guide_sensor.hpp baselines [mm]
# ---- Figure 1: magnetic guide sensor geometry and the least-squares yaw ----
fig,axs=plt.subplots(1,2,figsize=(13,5.2))
ax=axs[0]
yaw=np.radians(1.2); y0=18.0; x0=-12.0     # illustrative true offsets of the AGV center (mm) and yaw
R=np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]])
body=np.array([[-LFB/2-150,-LLR/2-120],[LFB/2+150,-LLR/2-120],[LFB/2+150,LLR/2+120],[-LFB/2-150,LLR/2+120]])
pts=(R@body.T).T+[x0,y0]
ax.add_patch(MPoly(pts,closed=True,fc=C["fill"],ec=C["box"],lw=1.5))
ax.axhline(0,color=C["hl"],lw=3,alpha=.6); ax.axvline(0,color=C["hl"],lw=3,alpha=.6)
ax.text(LFB/2+250,60,"tape (x axis)",color=C["hl"],fontsize=8.5); ax.text(40,LLR/2+250,"tape (y axis)",color=C["hl"],fontsize=8.5)
sens={"F":(LFB/2,0),"B":(-LFB/2,0),"L":(0,LLR/2),"R":(0,-LLR/2)}
for k,(sx,sy) in sens.items():
    p=R@np.array([sx,sy])+[x0,y0]; ax.plot(*p,"s",ms=9,color=C["s1"]); ax.text(p[0]+40,p[1]+40,k,fontsize=10,weight="bold",color=C["s1"])
c=np.array([x0,y0]); ax.plot(*c,"o",color=C["pt"]); ax.text(c[0]+40,c[1]-120,"AGV center c",fontsize=8.5,color=C["pt"])
arrow(ax,tuple(c),tuple(c+R@np.array([700,0])),C["pt"],lw=1.5); ax.text(*(c+R@np.array([720,30])),"+x (forward)",fontsize=8,color=C["pt"])
arrow(ax,tuple(c),tuple(c+R@np.array([0,500])),C["pt"],lw=1.5); ax.text(*(c+R@np.array([30,520])),"+y (left)",fontsize=8,color=C["pt"])
ax.set_title("Sensor layout in the AGV body frame (HITO convention), over a tape crossing",fontsize=9.5)
ax.set_xlim(-1700,1900); ax.set_ylim(-1150,1250); ax.set_aspect("equal"); ax.set_xlabel("mm"); ax.set_ylabel("mm"); ax.grid(alpha=.2)
# right: yaw estimate vs noise, single-pair vs weighted least squares
ax=axs[1]; rng=np.random.default_rng(0); N=4000; sigma=1.0
true_t=np.tan(yaw)
dF=y0+LFB/2*true_t+rng.normal(0,sigma,N); dB=-y0+LFB/2*true_t+rng.normal(0,sigma,N)
dR=x0+LLR/2*true_t+rng.normal(0,sigma,N); dL=-x0+LLR/2*true_t+rng.normal(0,sigma,N)
Sfb=dF+dB; Slr=dR+dL
t_fb=Sfb/LFB; t_lr=Slr/LLR; t_ls=(LFB*Sfb+LLR*Slr)/(LFB**2+LLR**2)
for t,lab,col in [(t_lr,"left/right pair only",C["s2"]),(t_fb,"front/back pair only",C["s1"]),(t_ls,"weighted least squares (code)",C["pt"])]:
    ax.hist(np.degrees(np.arctan(t))-np.degrees(yaw),bins=60,histtype="step",lw=2,color=col,label=f"{lab}: σ = {np.std(np.degrees(np.arctan(t))):.4f}°")
ax.set_xlabel("yaw error [deg]  (1 mm sensor noise, illustrative)"); ax.set_ylabel("count"); ax.legend(fontsize=8); ax.grid(alpha=.3)
ax.set_title("Combining both pairs reduces the yaw error",fontsize=9.5)
fig.tight_layout(); go(fig,"mgs_geometry")
# ---- Figure 2: heading IIR filter ----
T=0.1; alpha=0.8; thr=0.5
t=np.arange(0,6,T); raw=np.where(t<1,0.0,np.where(t<3,0.2,0.2+0.6*(t-3)/3)); raw=np.where(t>=4.5,raw+0.7,raw)  # step, ramp, jump
raw_noisy=raw+np.random.default_rng(1).normal(0,0.01,len(t))
f=[]; h=None
for r in raw_noisy:
    if h is None: h=r
    else:
        d=np.arctan2(np.sin(r-h),np.cos(r-h))
        h = r if abs(d)>thr else np.arctan2(np.sin(h+alpha*d),np.cos(h+alpha*d))
    f.append(h)
fig,ax=plt.subplots(figsize=(10,3.6))
ax.plot(t,np.degrees(raw_noisy),".",ms=4,color=C["aux"],label="reported heading (state + visualization samples)")
ax.step(t,np.degrees(f),where="post",color=C["s1"],lw=2,label=f"PoseFilter output (α = {alpha}, jump threshold {thr} rad)")
ax.annotate("step: converges within 2–3 samples",xy=(1.3,11.2),xytext=(0.2,25),fontsize=8.5,arrowprops=dict(arrowstyle="->"))
ax.annotate("ramp: lag of (1−α)/α · ω·T",xy=(3.8,np.degrees(0.36)),xytext=(2.3,40),fontsize=8.5,arrowprops=dict(arrowstyle="->"))
ax.annotate("jump > 0.5 rad: filter bypassed",xy=(4.5,np.degrees(1.37)),xytext=(2.6,72),fontsize=8.5,arrowprops=dict(arrowstyle="->"))
ax.set_xlabel("time [s]  (T = 0.1 s between samples, illustrative)"); ax.set_ylabel("heading [deg]"); ax.grid(alpha=.3); ax.legend(fontsize=8,loc="upper left")
ax.set_title("Heading IIR in PoseFilter: ψ ← wrap(ψ + α·wrap(θ − ψ)) unless |wrap(θ − ψ)| > 0.5 rad",fontsize=9.5,loc="left")
go(fig,"pose_filter"); print("ok")

# ---- Figure 3: simulator braking envelope (verbatim logic of AgvMotion::StepTranslation) ----
def simulate(waypoints, vmax, a, dt=0.05):
    total=waypoints[-1][0]; trav=0.0; v=0.0; t=0.0; T=[0.0]; S=[0.0]; V=[0.0]; LIM=[]
    cap_of=lambda w: w[1] if w[1]>0 else vmax
    while total-trav>1e-9:
        rem=total-trav
        cap=vmax
        for w in waypoints:
            if w[0]>trav: cap=cap_of(w); break
        lim=min(cap, np.sqrt(2*a*rem))
        for i in range(len(waypoints)-1):
            d=waypoints[i][0]-trav
            if d<=0: continue
            nxt=cap_of(waypoints[i+1]); lim=min(lim, np.sqrt(nxt**2+2*a*d))
        v = min(lim, v+a*dt) if v<lim else max(lim, v-a*dt)
        mv=min(v*dt, rem); trav+=mv; t+=dt
        T.append(t); S.append(trav); V.append(v)
        if t>200: break
    return np.array(T),np.array(S),np.array(V)
wps=[(4.0,1.0),(8.0,0.4),(12.0,1.0)]   # distance [m], edge speed cap [m/s] (0.4 = restricted edge)
T,S,V=simulate(wps,1.0,0.2)
fig,axs=plt.subplots(1,2,figsize=(13,3.8))
ax=axs[0]; ax.plot(S,V,color=C["s1"],lw=2,label="simulated speed")
x=np.linspace(0,12,400)
cap=np.where(x<=4,1.0,np.where(x<=8,0.4,1.0)); ax.plot(x,cap,":",color=C["aux"],label="edge speed caps")
env=np.minimum.reduce([np.sqrt(2*0.2*np.maximum(12-x,0)), np.where(x<4,np.sqrt(0.4**2+2*0.2*np.maximum(4-x,0)),9), cap])
ax.plot(x,env,"--",color=C["hl"],lw=1,label="braking envelope min(cap, √(v²_next + 2a·d), √(2a·r))")
for d,_ in wps[:-1]: ax.axvline(d,color=C["aux"],lw=.5)
ax.set_xlabel("distance along the chain [m]"); ax.set_ylabel("speed [m/s]"); ax.legend(fontsize=7.5,loc="lower center"); ax.grid(alpha=.3)
ax.set_title("Speed versus distance: slows before the restricted edge",fontsize=9.5)
ax=axs[1]; ax.plot(T,V,color=C["s1"],lw=2); ax.set_xlabel("time [s]"); ax.set_ylabel("speed [m/s]"); ax.grid(alpha=.3)
ax.set_title(f"Speed versus time: 12 m in {T[-1]:.1f} s (dt = 50 ms)",fontsize=9.5)
fig.tight_layout(); go(fig,"sim_braking_envelope"); print("ok3", round(T[-1],2))
