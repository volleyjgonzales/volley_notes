from style import *
from matplotlib.patches import Polygon, Arc
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","06-agv_interfaces")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
R=lambda a: np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
def agv(ax,p,psi,col,alpha=1.0,ls="-",label=None):
    L,W=0.9,0.55; c=np.array([[-L/2,-W/2],[L/2,-W/2],[L/2+.25,0],[L/2,W/2],[-L/2,W/2]])
    ax.add_patch(Polygon((R(psi)@c.T).T+p,fc=col,alpha=.12*alpha,ec=col,lw=1.6,ls=ls))
    ax.plot(*p,"o",color=col,ms=5,alpha=alpha)
    if label: ax.text(p[0]+.25,p[1]-.55,label,color=col,fontsize=9)
# Illustrative numbers
pn=np.array([0.0,0.0]); th=np.radians(90)          # node heading 90 deg = north (+y)
dpsi=np.radians(20); psi=th+dpsi                   # AGV yaw = node heading + yaw offset
dB=np.array([1.3,-0.8])                         # x_offset_m, y_offset_m in AGV frame
pa=pn+R(psi)@dB
fig,axs=plt.subplots(1,2,figsize=(12,5.6))
ax=axs[0]
arrow(ax,(-2.8,-2.4),(-2.0,-2.4),"black",lw=1.2); ax.text(-1.95,-2.5,"x: east",fontsize=8)
arrow(ax,(-2.8,-2.4),(-2.8,-1.6),"black",lw=1.2); ax.text(-2.75,-1.5,"y: north",fontsize=8)
ax.plot(*pn,"P",ms=11,color=C["s2"]); arrow(ax,pn,pn+1.3*np.array([np.cos(th),np.sin(th)]),C["s2"],lw=2)
ax.text(pn[0]-2.4,pn[1]+0.9,"node heading\nnode_heading_deg = 90",color=C["s2"],fontsize=9)
ax.text(pn[0]-.55,pn[1]-.45,"node origin",color=C["s2"],fontsize=9)
agv(ax,pa,psi,C["s1"],label="AGV reference point")
xb=R(psi)@[1,0]; yb=R(psi)@[0,1]
arrow(ax,pa,pa+1.2*xb,C["s1"],lw=1.6); ax.text(*(pa+1.3*xb+[-.15,.05]),"x_AGV",color=C["s1"],fontsize=9)
arrow(ax,pa,pa+0.9*yb,C["s1"],lw=1.6); ax.text(*(pa+1.0*yb+[-.5,0]),"y_AGV",color=C["s1"],fontsize=9)
# decomposition of d (node -> AGV) along AGV axes
f=pn+R(psi)@[dB[0],0]
ax.plot([pn[0],f[0]],[pn[1],f[1]],color=C["pt"],lw=3); ax.plot([f[0],pa[0]],[f[1],pa[1]],color=C["pt"],lw=3,ls="--")
ax.text(*((pn+f)/2+[.12,-.05]),f"x_offset_m = {dB[0]:.2f}",color=C["pt"],fontsize=9)
ax.text(*((f+pa)/2+[.15,-.1]),f"y_offset_m = {dB[1]:.2f}",color=C["pt"],fontsize=9)
ax.plot([pa[0],pa[0]+1.3*np.cos(th)],[pa[1],pa[1]+1.3*np.sin(th)],":",color=C["s2"],lw=1.2)
ax.add_patch(Arc(pa,1.6,1.6,theta1=np.degrees(th),theta2=np.degrees(psi),color=C["hl"],lw=1.6))
ax.text(pa[0]-1.9,pa[1]+.55,"yaw_offset_rad\n= +20° (CCW)",color=C["hl"],fontsize=9)
ax.set_title("Reading A: offset = AGV position − node origin,\nexpressed along the AGV's axes",fontsize=10)
clean(ax,((-3.0,2.8),(-2.6,2.8)))
ax=axs[1]
ax.plot(*pn,"P",ms=11,color=C["s2"]); arrow(ax,pn,pn+1.3*np.array([np.cos(th),np.sin(th)]),C["s2"],lw=2)
pA=pn+R(psi)@dB; pB=pn-R(psi)@dB; pC=pn+R(th)@dB
agv(ax,pA,psi,C["s1"],label="A: node→AGV, AGV axes")
agv(ax,pB,psi,C["hl"],ls="--",label="B: AGV→node, AGV axes")
agv(ax,pC,psi,"#8e44ad",ls=":",label="C: node→AGV, node axes")
ax.text(-2.9,-2.5,"Same message, three readings → reconstructed AGV positions\nspread by up to 2·|offset| = %.2f m"%(2*np.linalg.norm(dB)),fontsize=9)
ax.set_title("Why the sign and frame convention must be pinned down",fontsize=10)
clean(ax,((-3.0,2.8),(-2.6,2.8)))
fig.suptitle("NodeAccuracy geometry (illustrative values; garage frame x = east, y = north)",fontsize=11,y=1.03)
fig.tight_layout(); go(fig,"node_accuracy_geometry"); print("ok")
