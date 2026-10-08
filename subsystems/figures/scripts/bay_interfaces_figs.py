from style import *
from matplotlib.patches import Rectangle
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","13-bay_interfaces")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
IN=0.0254; L,W=14*12*IN,7*12*IN      # tray length/width from common/constants.hpp; load-cell spacing ASSUMED equal to the tray footprint
a,b=L/2,W/2
cells=[("0 SYSTEM_RIGHT",(+a,-b)),("1 PATRON_RIGHT",(-a,-b)),("2 PATRON_LEFT",(-a,+b)),("3 SYSTEM_LEFT",(+a,+b))]
mass=np.array([620.,540.,560.,700.])   # illustrative readings [kg] (tray + vehicle)
M=mass.sum(); x=sum(m*p[0] for m,(_,p) in zip(mass,cells))/M; y=sum(m*p[1] for m,(_,p) in zip(mass,cells))/M
fig,ax=plt.subplots(figsize=(10,5.6))
ax.add_patch(Rectangle((-a,-b),L,W,fc=C["fill"],ec=C["box"],lw=2))
for (lab,(px,py)),m in zip(cells,mass):
    ax.plot(px,py,"s",ms=14,color=C["s1"]); ax.text(px+(0.15 if px>0 else -0.15),py+(0.25 if py>0 else -0.35),f"[{lab}]\n{m:.0f} kg",ha="left" if px>0 else "right",fontsize=9,color=C["s1"])
ax.plot(0,0,"+",ms=14,color=C["box"]); ax.text(0.08,-0.25,"tray center",fontsize=8,color=C["box"])
ax.plot(x,y,"o",ms=11,color=C["hl"]); ax.text(x+0.12,y+0.12,f"center of mass\nx = {x:+.3f} m, y = {y:+.3f} m\nM = {M:.0f} kg",color=C["hl"],fontsize=9)
arrow(ax,(-a-1.3,0),(-a-0.4,0),C["pt"],lw=2); ax.text(-a-1.35,0.15,"patron side\n(car drives in)",fontsize=8.5,color=C["pt"],ha="left")
arrow(ax,(-0.6,-b-0.5),(0.6,-b-0.5),"black",lw=1.2); ax.text(0.65,-b-0.55,"+x (toward system)",fontsize=8.5)
arrow(ax,(a+0.5,-0.6),(a+0.5,0.6),"black",lw=1.2); ax.text(a+0.6,0.6,"+y (left, facing system)",fontsize=8.5)
ax.set_title("LoadCells.mass[i] → total mass and center of mass (illustrative readings; cell spacing assumed = tray footprint)",fontsize=10,loc="left")
clean(ax,((-a-1.6,a+2.4),(-b-0.9,b+0.8))); go(fig,"load_cell_com"); print(M,x,y)

# ---- Figure 7.2: free-body diagrams (side view: pitch balance; front view: roll balance) ----
g=9.81
RS=(mass[0]+mass[3]); RP=(mass[1]+mass[2]); RL=(mass[2]+mass[3]); RR=(mass[0]+mass[1])
fig,axs=plt.subplots(1,2,figsize=(12,4.6))
for ax,(lo,hi,lab_lo,lab_hi,Rlo,Rhi,xb,axis,ttl) in zip(axs,[
    (-a,a,"patron cells 1,2","system cells 0,3",RP,RS,x,"x","Side view: balance of moments about the y-axis"),
    (-b,b,"right cells 0,1","left cells 2,3",RR,RL,y,"y","System-end view (+y to the right): balance of moments about the x-axis")]):
    ax.plot([lo,hi],[0,0],color=C["box"],lw=6,solid_capstyle="butt")
    for p,R,lab in [(lo,Rlo,lab_lo),(hi,Rhi,lab_hi)]:
        ax.plot(p,-0.08,"^",ms=14,color=C["s1"])
        arrow(ax,(p,-0.95),(p,-0.12),C["s1"],lw=2)
        ax.text(p,-1.15,f"{lab}\nR = ({'m₁+m₂' if lab.startswith('patron') else 'm₀+m₃' if lab.startswith('system') else 'm₀+m₁' if lab.startswith('right') else 'm₂+m₃'})·g = {R:.0f} kg·g",ha="center",fontsize=8.5,color=C["s1"])
    arrow(ax,(xb,0.95),(xb,0.1),C["hl"],lw=2.5); ax.text(xb+0.05,1.0,f"M·g at {axis}̄ = {xb:+.3f} m",color=C["hl"],fontsize=9)
    ax.plot([0,0],[-0.3,0.3],":",color=C["aux"]); ax.text(0.02,0.32,"origin (tray center)",fontsize=8,color=C["aux"])
    ax.annotate("",xy=(hi,0.55),xytext=(0,0.55),arrowprops=dict(arrowstyle="<->",color=C["aux"])); ax.text(hi/2,0.6,"a" if axis=="x" else "b",ha="center",color=C["aux"])
    eq=(f"Σ moments about the y-axis:  a·(m₀+m₃) − a·(m₁+m₂) = M·x̄\n⇒ x̄ = a(m₀−m₁−m₂+m₃)/M" if axis=="x" else
        f"Σ moments about the x-axis:  b·(m₂+m₃) − b·(m₀+m₁) = M·ȳ\n⇒ ȳ = b(−m₀−m₁+m₂+m₃)/M")
    ax.text(lo,-1.75,eq,fontsize=9)
    ax.set_title(ttl,fontsize=10); clean(ax,((lo-0.6,hi+0.9),(-2.0,1.3)))
fig.tight_layout(); go(fig,"load_cell_free_body")

# ---- Figure 7.3: the four orthogonal load modes ----
modes=[("total  (1,1,1,1)",[1,1,1,1]),("pitch  s_x = (+1,−1,−1,+1)",[1,-1,-1,1]),("roll  s_y = (−1,−1,+1,+1)",[-1,-1,1,1]),("twist  t = s_x·s_y = (−1,+1,−1,+1)",[-1,1,-1,1])]
pos=[(+1,-1),(-1,-1),(-1,+1),(+1,+1)]
fig,axs=plt.subplots(1,4,figsize=(13,3.4))
for ax,(ttl,v) in zip(axs,modes):
    ax.add_patch(Rectangle((-1,-1),2,2,fc=C["fill"],ec=C["box"]))
    for i,((px,py),s) in enumerate(zip(pos,v)):
        ax.plot(px,py,"o",ms=22,color=C["s1"] if s>0 else C["hl"]); ax.text(px,py,f"{'+' if s>0 else '−'}",ha="center",va="center",color="white",fontsize=13,weight="bold")
        ax.text(px*1.42,py*1.38,str(i),ha="center",va="center",fontsize=9)
    dot=sum(s*m for s,m in zip(v,mass)); ax.set_title(ttl,fontsize=9)
    ax.text(0,-1.75,f"value for Fig. 7.1 readings: {dot:+.0f} kg",ha="center",fontsize=8.5)
    clean(ax,((-1.7,1.7),(-2.0,1.7)))
axs[0].text(-1.65,0.0,"patron",rotation=90,va="center",fontsize=8,color=C["aux"]); axs[0].text(1.5,0.0,"system",rotation=90,va="center",fontsize=8,color=C["aux"])
fig.suptitle("Any four readings = total + pitch + roll + twist (corner numbers = LoadCellId index; top = left, facing system)",fontsize=10,y=1.02)
fig.tight_layout(); go(fig,"load_cell_modes"); print("modes ok")
