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
