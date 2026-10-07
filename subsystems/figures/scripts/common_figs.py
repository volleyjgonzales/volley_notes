from style import *
from matplotlib.patches import Arc, Polygon, Rectangle, Circle
import os; HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","01-common")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
cross=lambda a,b: a[0]*b[1]-a[1]*b[0]

# 1. Angle wrapping and signed distance
fig,ax=plt.subplots(figsize=(6.2,5))
th=np.linspace(0,2*np.pi,400); ax.plot(np.cos(th),np.sin(th),color=C["aux"],lw=1)
ax.axhline(0,color=C["aux"],lw=.6); ax.axvline(0,color=C["aux"],lw=.6)
a,b=np.radians(150),np.radians(-160)
for ang,col,lab in [(a,C["s1"],"a = 150°"),(b,C["s2"],"b = −160°")]:
    arrow(ax,(0,0),(np.cos(ang),np.sin(ang)),col); ax.text(1.12*np.cos(ang)-.05,1.12*np.sin(ang),lab,color=col,ha="center")
ax.add_patch(Arc((0,0),.7,.7,theta1=150,theta2=200,color=C["pt"],lw=2.5))
ax.annotate("δ(a,b) = +50°\n(shortest way)",xy=(-.36,-.05),xytext=(-.05,-.45),color=C["pt"],fontsize=9,arrowprops=dict(arrowstyle="->",color=C["pt"]))
ax.add_patch(Arc((0,0),1.5,1.5,theta1=-160,theta2=150,color=C["aux"],lw=1.2,ls="--"))
ax.text(.55,.6,"raw b − a = −310°\n(long way, not used)",color=C["aux"],fontsize=9)
ax.plot([-1],[0],"o",ms=9,color=C["hl"]); ax.plot([-1],[0],"o",ms=4,color="white")
ax.annotate("±π: Wrap → +π (closed end)\n       wrapPi → −π",xy=(-1,0),xytext=(-1.75,-1.15),fontsize=9,color=C["hl"],arrowprops=dict(arrowstyle="->",color=C["hl"]))
ax.text(1.05,.05,"0",fontsize=9); ax.text(.03,1.05,"π/2",fontsize=9)
ax.set_title("Wrap to (−π, π] and SignedAngleDist")
clean(ax,((-1.9,1.6),(-1.35,1.35))); go(fig,"angle_wrap")

# 2. Body vs inertial frame (rotation only, as in BodyToInertial)
fig,ax=plt.subplots(figsize=(5.8,5))
psi=np.radians(35); R=np.array([[np.cos(psi),-np.sin(psi)],[np.sin(psi),np.cos(psi)]])
arrow(ax,(0,0),(3.2,0),"black",label=((3.25,-.15),"X (inertial)")); arrow(ax,(0,0),(0,3),"black",label=((-.2,3.1),"Y"))
xb=R@[3,0]; yb=R@[0,2.6]
arrow(ax,(0,0),xb,C["s1"],label=((xb[0]+.05,xb[1]),"x_body")); arrow(ax,(0,0),yb,C["s1"],label=((yb[0]-.5,yb[1]+.1),"y_body"))
pB=np.array([2.0,1.0]); pI=R@pB
arrow(ax,(0,0),pI,C["pt"],lw=2.5); ax.plot(*pI,"o",color=C["pt"])
ax.text(pI[0]+.08,pI[1]+.05,"p",color=C["pt"],fontsize=12)
ax.plot([pI[0],pI[0]],[0,pI[1]],":",color=C["aux"]); ax.plot([0,pI[0]],[pI[1],pI[1]],":",color=C["aux"])
ax.text(pI[0]-.1,-.3,f"x_I={pI[0]:.2f}",fontsize=9,color=C["aux"],ha="center"); ax.text(-.15,pI[1],f"y_I={pI[1]:.2f}",fontsize=9,color=C["aux"],ha="right",va="center")
f=R@[pB[0],0]; ax.plot([0,f[0]],[0,f[1]],color=C["s1"],lw=4,alpha=.25); ax.plot([f[0],pI[0]],[f[1],pI[1]],color=C["s1"],lw=4,alpha=.25)
ax.text(*(f/2+[.35,-.25]),"x_B = 2.0",color=C["s1"],fontsize=9); ax.text(*((f+pI)/2+[.12,-.1]),"y_B = 1.0",color=C["s1"],fontsize=9)
ax.add_patch(Arc((0,0),1.6,1.6,theta1=0,theta2=35,color=C["hl"],lw=1.5)); ax.text(.95,.08,"ψ = 35°",color=C["hl"])
ax.text(-0.2,-1.0,"p_I = R(ψ) p_B     p_B = R(−ψ) p_I",fontsize=10)
ax.set_title("BodyToInertial / InertialToBody (rotation only)")
clean(ax,((-2.2,3.9),(-1.2,3.3))); go(fig,"body_inertial_frames")

# 3. Segment intersection cases
def seg(ax,p,q,col,lab,lw=2.5):
    ax.plot([p[0],q[0]],[p[1],q[1]],color=col,lw=lw); ax.plot(*p,"o",color=col,ms=4); ax.plot(*q,"o",color=col,ms=4)
    if lab: ax.text(*lab[0],lab[1],color=col)
fig,axs=plt.subplots(2,2,figsize=(10,7.4))
ax=axs[0,0]; P1,P2,Q1,Q2=map(np.array,([0,0],[4,2],[1,2.6],[3,-.6]))
u,v,w=P2-P1,Q2-Q1,P1-Q1; D=cross(u,v); s=cross(v,w)/D; t=cross(u,w)/D; X=P1+s*u
seg(ax,P1,P2,C["s1"],((4.05,2),"s₁")); seg(ax,Q1,Q2,C["s2"],((3.05,-.7),"s₂"))
arrow(ax,Q1,P1,C["aux"],lw=1.2,label=((-.05,1.4),"w")); ax.plot(*X,"*",ms=15,color=C["pt"])
ax.text(X[0]+.35,X[1]-.6,f"x = p₁ + s·u\ns = {s:.2f}, t = {t:.2f}",color=C["pt"],fontsize=9)
ax.text(.1,2.9,"D = u×v ≠ 0 and s,t ∈ [0,1] → {x, none}",fontsize=9); ax.set_title("(a) Crossing")
clean(ax,((-.5,5),(-1,3.3)))
ax=axs[0,1]; P1,P2,Q1,Q2=map(np.array,([0,0],[2.2,1.1],[2.2,-1.2],[4.2,2.4]))
u,v,w=P2-P1,Q2-Q1,P1-Q1; D=cross(u,v); s=cross(v,w)/D; t=cross(u,w)/D; X=P1+s*u
seg(ax,P1,P2,C["s1"],((-.2,.3),"s₁")); seg(ax,Q1,Q2,C["s2"],((4.25,2.4),"s₂"))
ax.plot([P2[0],X[0]],[P2[1],X[1]],"--",color=C["s1"],lw=1); ax.plot(*X,"x",ms=10,color=C["hl"],mew=2)
ax.text(X[0]-.2,X[1]+.35,f"lines cross at s = {s:.2f} > 1",color=C["hl"],fontsize=9,ha="right")
ax.text(-.2,2.9,"D ≠ 0 but s ∉ [0,1] → {none, none}",fontsize=9); ax.set_title("(b) Lines cross outside the segment")
clean(ax,((-.5,5.5),(-1.5,3.3)))
ax=axs[1,0]; seg(ax,(0,0),(4,1.6),C["s1"],((4.05,1.6),"s₁")); seg(ax,(0,.9),(4,2.5),C["s2"],((4.05,2.5),"s₂"))
ax.text(-.2,3.2,"D = 0 and u×w ≠ 0 (parallel, offset)\n→ {none, none}",fontsize=9); ax.set_title("(c) Parallel, not collinear")
clean(ax,((-.5,5),(-.6,3.8)))
ax=axs[1,1]; y1,y2=.25,0
seg(ax,(0,y2),(4,y2),C["s2"],((-.5,-.25),"s₂")); seg(ax,(2.5,y1),(6,y1),C["s1"],((6.05,y1),"s₁"))
ax.plot([2.5,4],[-.25,-.25],color=C["pt"],lw=6,alpha=.6); ax.text(3.25,-.55,"returned overlap {a, b}",color=C["pt"],ha="center",fontsize=9)
for xv,lab in [(0,"0"),(4,"1"),(2.5,"t₀=0.625"),(6,"t₁=1.5 → clip 1")]:
    ax.plot([xv,xv],[.55,.65],color="black"); ax.text(xv,.75,lab,ha="center",fontsize=8.5)
ax.plot([0,6],[.6,.6],color="black",lw=.8); ax.text(-.2,.6,"t along s₂",ha="right",va="center",fontsize=8.5)
ax.text(-.6,1.5,"D = 0, collinear: project s₁ onto s₂, sort, clip to [0,1]\n(segments drawn vertically offset for clarity)",fontsize=9)
ax.set_title("(d) Collinear overlap"); clean(ax,((-1.6,6.8),(-.9,2.0)))
fig.suptitle("CalcLineSegmentsIntersection: u = s₁ direction, v = s₂ direction, w = p₁(s₁) − p₁(s₂)",fontsize=11)
fig.tight_layout(); go(fig,"segment_intersection")

# 4. Point–segment distance
fig,axs=plt.subplots(1,3,figsize=(12,3.9)); A=np.array([0,0]); B=np.array([4,1.5])
for ax,P,ttl in zip(axs,[np.array([1.4,2.6]),np.array([-1.6,1.6]),np.array([5.6,-.4])],["t* ∈ [0,1]: foot of perpendicular","t* < 0: clamp to a","t* > 1: clamp to b"]):
    d=B-A; traw=np.dot(P-A,d)/np.dot(d,d); tc=min(max(traw,0),1); F=A+traw*d; Q=A+tc*d
    L0,L1=A+(-0.6)*d,A+1.6*d; ax.plot([L0[0],L1[0]],[L0[1],L1[1]],"--",color=C["aux"],lw=.8)
    seg(ax,A,B,C["s1"],None); ax.text(A[0]-.15,A[1]-.4,"a",color=C["s1"]); ax.text(B[0]+.05,B[1]-.4,"b",color=C["s1"])
    ax.plot(*P,"o",color=C["s2"]); ax.text(P[0]+.1,P[1]+.1,"p",color=C["s2"])
    if not np.allclose(F,Q):
        ax.plot([P[0],F[0]],[P[1],F[1]],":",color=C["aux"]); ax.plot(*F,"o",mfc="white",color=C["aux"]); ax.text(F[0],F[1]-.45,f"t = {traw:.2f}",color=C["aux"],fontsize=8.5,ha="center")
    ax.plot([P[0],Q[0]],[P[1],Q[1]],color=C["pt"],lw=2.5); ax.plot(*Q,"s",color=C["pt"])
    ax.text(*((P+Q)/2+[.12,.05]),f"d = {np.linalg.norm(P-Q):.2f}",color=C["pt"],fontsize=9)
    ax.set_title(f"{ttl}\nt* = {tc:.2f}",fontsize=10); clean(ax,((-2.6,6.6),(-1.3,3.2)))
fig.suptitle("GetMinimumDistance: project p on the line through a,b, clamp t to [0,1]",fontsize=11); fig.tight_layout(); go(fig,"point_segment_distance")

# 5. Cohen–Sutherland outcodes
fig,ax=plt.subplots(figsize=(7.6,6.2)); xm,xM,ym,yM=0,4,0,3
ax.add_patch(Rectangle((xm,ym),xM-xm,yM-ym,fc=C["fill"],ec=C["box"],lw=2))
for gx in (xm,xM): ax.axvline(gx,color=C["aux"],lw=.6,ls=":")
for gy in (ym,yM): ax.axhline(gy,color=C["aux"],lw=.6,ls=":")
codes={(-1,1):"1001",(0,1):"1000",(1,1):"1010",(-1,0):"0001",(0,0):"0000",(1,0):"0010",(-1,-1):"0101",(0,-1):"0100",(1,-1):"0110"}
cx={-1:-1.6,0:2,1:5.6}; cy={-1:-1,0:1.5,1:4.1}
for (i,j),c in codes.items(): ax.text(cx[i],cy[j]-.55 if (i,j)==(0,0) else cy[j]+0.55 if j==-1 else cy[j]+.45,c,ha="center",fontsize=10,color=C["box"],family="DejaVu Sans Mono")
lines=[((1,1.2),(5.5,2.2),C["pt"],"A: p₁ inside → accept"),
       ((-1.8,.4),(5.6,.7),C["s1"],"B: codes L|R straddle → accept"),
       ((-.8,3.8),(5.2,4.6),C["hl"],"C: both TOP (AND≠0) → reject"),
       ((-1,1.5),(2.5,4.5),"#8e44ad","D: clip to y=3 → inside → accept"),
       ((-2.2,1.8),(.6,4.6),"#b8860b","E: clip to y=3 → still LEFT → reject")]
for p,q,col,lab in lines: ax.plot([p[0],q[0]],[p[1],q[1]],color=col,lw=2); ax.plot(*p,"o",color=col,ms=4); ax.plot(*q,"o",color=col,ms=4)
for p,q,col in [((-1,1.5),(2.5,4.5),"#8e44ad"),((-2.2,1.8),(.6,4.6),"#b8860b")]:
    xc=p[0]+(q[0]-p[0])/(q[1]-p[1])*(3-p[1]); ax.plot(xc,3,"D",color=col,ms=7,mfc="white",mew=2)
for k,(p,q,col,lab) in enumerate(lines): ax.text(6.6,4.6-k*.6,lab,color=col,fontsize=9)
ax.text(6.6,0.2,"bits: TOP=8 BOTTOM=4\n         RIGHT=2 LEFT=1\n◇ = clipped endpoint",fontsize=9,color=C["box"])
ax.set_title("DoesLineIntersectWithAABB: outcodes and the modified accept rule")
clean(ax,((-2.6,11.5),(-1.6,5.0))); go(fig,"cohen_sutherland")

# 6. Oriented box transform
fig,axs=plt.subplots(1,2,figsize=(10,4.3)); c=np.array([3,2]); psi=np.radians(30); L,W=3,1.6
R=lambda a: np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
corn=np.array([[-L/2,-W/2],[L/2,-W/2],[L/2,W/2],[-L/2,W/2]])
p,q=np.array([0.5,3.6]),np.array([5.2,1.2])
ax=axs[0]; ax.add_patch(Polygon((R(psi)@corn.T).T+c,fc=C["fill"],ec=C["box"],lw=2)); ax.plot(*c,"+",color=C["box"],ms=10)
seg(ax,p,q,C["s2"],((q[0]+.05,q[1]),"line")); ax.text(c[0]-.2,c[1]-.45,"c, ψ=30°",fontsize=9,color=C["box"]); ax.set_title("World frame"); clean(ax,((-.3,6.3),(-.5,4.3)))
ax=axs[1]; ax.add_patch(Rectangle((-L/2,-W/2),L,W,fc=C["fill"],ec=C["box"],lw=2)); pp,qq=R(-psi)@(p-c),R(-psi)@(q-c)
seg(ax,pp,qq,C["s2"],((qq[0]+.05,qq[1]),"line'")); ax.axhline(0,color=C["aux"],lw=.5); ax.axvline(0,color=C["aux"],lw=.5)
ax.text(-L/2,-W/2-.45,"[−L/2, L/2] × [−W/2, W/2] → AABB test",fontsize=9); ax.set_title("Box frame: p ↦ R(−ψ)(p − c)"); clean(ax,((-3.3,3.3),(-2.3,2.6)))
fig.suptitle("DoesLineIntersectWithBox",fontsize=11); fig.tight_layout(); go(fig,"oriented_box")

# 7. Perp-dot and collinearity
fig,axs=plt.subplots(1,2,figsize=(10,3.8))
ax=axs[0]; a_,b_=np.array([3,.6]),np.array([1,1.8])
ax.add_patch(Polygon([[0,0],a_,a_+b_,b_],fc=C["fill"],ec="none")); arrow(ax,(0,0),a_,C["s1"],label=((a_[0]+.05,a_[1]-.2),"a")); arrow(ax,(0,0),b_,C["s2"],label=((b_[0]-.3,b_[1]),"b"))
ax.text(1.4,1.1,f"a×b = {cross(a_,b_):.2f}\n(signed area)",fontsize=9,ha="center"); ax.set_title("Perp-dot = parallelogram area"); clean(ax,((-.4,4.6),(-.4,2.8)))
ax=axs[1]; P1,P2,Q1,Q2=map(np.array,([0,0],[2,.5],[3,.78],[5,1.25]))
seg(ax,P1,P2,C["s1"],((.0,.25),"s₁")); seg(ax,Q1,Q2,C["s2"],((4.6,1.4),"s₂"))
for Z in (Q1,Q2): ax.add_patch(Polygon([P1,P2,Z],fc=C["s1"],alpha=.12,ec=C["s1"],lw=.6,ls=":"))
ax.text(.2,1.6,"all four areas (each segment's direction ×\nthe other's endpoints) ≤ tol → collinear\ntolerance is an AREA (m²), default 0.01",fontsize=9)
ax.set_title("AreCollinear"); clean(ax,((-.4,5.6),(-.4,2.4))); fig.tight_layout(); go(fig,"perp_dot_collinear")

# 8. Trapezoidal profile (re-implementation of Motion1D)
def run(S,vmax=1.,amax=.5,dt=.1,brake_at=None):
    s=v=0.; tot=S; t=0.; T=[0];V=[0];X=[0]; braked=False
    for _ in range(10000):
        if s>=tot-1e-9 and v<=1e-6: break
        if brake_at is not None and not braked and t>=brake_at-1e-9: tot=s+v*v/(2*amax); braked=True
        rem=tot-s; acc=-amax if rem<=v*v/(2*amax) else amax
        v=min(max(v+acc*dt,0),vmax); s+=v*dt
        if s>=tot: s=tot; v=0.
        t+=dt; T.append(t);V.append(v);X.append(s)
    return np.array(T),np.array(V),np.array(X)
fig,axs=plt.subplots(1,2,figsize=(11,4))
for (S,ba,col,lab) in [(4,None,C["s1"],"S = 4 m (trapezoid)"),(1,None,C["s2"],"S = 1 m (triangle)"),(4,3.0,C["hl"],"S = 4 m, brakeNow() at t = 3 s")]:
    T,V,X=run(S,brake_at=ba); ls="--" if ba else "-"
    axs[0].step(T,V,where="post",color=col,ls=ls,label=f"{lab}: {len(T)-1} steps"); axs[1].plot(T,X,color=col,ls=ls,label=lab)
axs[0].axhline(1,color=C["aux"],lw=.6,ls=":"); axs[0].text(0.1,1.03,"v_max",fontsize=8,color=C["aux"])
axs[0].axvline(3,color=C["hl"],lw=.6,ls=":")
axs[0].set_xlabel("t [s]"); axs[0].set_ylabel("v [m/s]"); axs[0].set_title("Speed (dt = 0.1 s, v_max = 1, a_max = 0.5)"); axs[0].legend(fontsize=8,loc="upper left",bbox_to_anchor=(0,-.15),ncol=1)
axs[1].set_xlabel("t [s]"); axs[1].set_ylabel("s [m]"); axs[1].set_title("Distance travelled"); axs[1].legend(fontsize=8,loc="lower right")
for a in axs: a.grid(alpha=.3)
axs[0].annotate("bang-bang chatter",xy=(2.15,.37),xytext=(2.6,.12),fontsize=8,color=C["s2"],arrowprops=dict(arrowstyle="->",color=C["s2"]))
axs[0].annotate("final-step snap\n0.45 → 0 m/s",xy=(4.4,.3),xytext=(4.6,.55),fontsize=8,color=C["hl"],arrowprops=dict(arrowstyle="->",color=C["hl"]))
fig.tight_layout(); go(fig,"trapezoid_profile")

# 9. Heartbeat latency timeline
fig,ax=plt.subplots(figsize=(11,2.9)); hb=[.3,.9,1.4,2.2,6.5]; checks=np.arange(1,9)
ax.axhline(0,color="black",lw=.8)
for h in hb: ax.plot([h,h],[0,.6],color=C["pt"],lw=2)
ax.text(.3,.68,"Heartbeat()",color=C["pt"],fontsize=9)
heart=True; last=0
for k in checks:
    beat=any(last<h<=k for h in hb); last=k
    if beat: ax.plot(k,0,"o",color=C["s1"],ms=8)
    else: ax.plot(k,0,"X",color=C["hl"],ms=11); ax.annotate("callback",xy=(k,0),xytext=(k,-.55),ha="center",color=C["hl"],fontsize=8.5,arrowprops=dict(arrowstyle="->",color=C["hl"]))
ax.axvspan(3.2,4.2,ymin=.45,ymax=.6,color=C["hl"],alpha=.15); ax.text(3.7,.32,"(t_h+T, t_h+2T]",ha="center",fontsize=9,color=C["hl"])
ax.annotate("last heartbeat t_h",xy=(2.2,.6),xytext=(2.6,.95),fontsize=9,color=C["pt"],arrowprops=dict(arrowstyle="->",color=C["pt"]))
ax.set_xticks(range(0,9)); ax.set_xticklabels(["start"]+[f"{k}T" for k in range(1,9)])
ax.set_yticks([]); [ax.spines[s].set_visible(False) for s in ("left","right","top")]
ax.text(8.2,.3,"● check: flag was set, cleared\n✕ check: flag clear → callback",fontsize=9)
ax.set_xlim(-.2,10.6); ax.set_ylim(-.8,1.15); ax.set_title("HeartbeatMonitor: watchdog checks every T; reaction 1–2 periods after the last heartbeat")
go(fig,"heartbeat_latency")
print("done")
