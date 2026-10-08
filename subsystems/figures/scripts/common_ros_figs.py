from style import *
from matplotlib.patches import Polygon as MPoly, Circle as MCircle
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","18-common_ros")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
IN=0.0254; L,W=157.5*IN,73.5*IN   # common/constants.hpp kAgvLength, kAgvWidth
def rect(width,length):   # verbatim vertex order of RectangleFromSize(width, length): x-extent = length, y-extent = width
    return np.array([[-length/2,-width/2],[length/2,-width/2],[length/2,width/2],[-length/2,width/2]])
def rot(P,deg,cw):        # boost rotate_transformer rotates clockwise for +deg
    a=np.radians(-deg if cw else deg); R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]]); return P@R.T
from scipy.spatial import ConvexHull
fig,axs=plt.subplots(1,3,figsize=(14,4.8))
# (a) heading convention
ax=axs[0]; base=rect(L,W)   # AgvEntity: RectangleFromSize(kAgvLength, kAgvWidth) -> long axis along body y
for deg,cw,col,lab in [(30,False,C["pt"],"intended: +30° CCW (garage convention)"),(30,True,C["hl"],"computed: boost rotate +30° = clockwise")]:
    P=rot(base,deg,cw); ax.add_patch(MPoly(P,closed=True,fc=col,alpha=.18,ec=col,lw=2,label=lab))
    fwd=rot(np.array([[0,L/2]]),deg,cw)[0]; arrow(ax,(0,0),fwd,col,lw=1.5)
ax.add_patch(MPoly(base,closed=True,fill=False,ec=C["aux"],ls=":",lw=1,label="heading 0 (long axis = body +y)"))
ax.set_title("(a) Footprint at a 30° heading",fontsize=10); ax.legend(fontsize=7.5,loc="lower center",bbox_to_anchor=(.5,-.32)); clean(ax,((-3,3),(-3,3)))
# (b) swept edge = convex hull of footprints at both poses
ax=axs[1]; s=np.array([0,0]); d=np.array([2.6,1.2]); P0=base+s; P1=base+d
hull=ConvexHull(np.vstack([P0,P1])); H=np.vstack([P0,P1])[hull.vertices]
ax.add_patch(MPoly(H,closed=True,fc=C["s2"],alpha=.15,ec=C["s2"],lw=2,label="PolyAtEdge: convex hull"))
for P in (P0,P1): ax.add_patch(MPoly(P,closed=True,fill=False,ec=C["s1"],lw=1.5))
ax.plot(*s,"o",color=C["s1"]); ax.plot(*d,"o",color=C["s1"]); ax.text(.15,-.3,"src node",fontsize=8); ax.text(d[0]+.15,d[1]-.3,"dst node",fontsize=8)
cen=(s+d)/2; r=np.linalg.norm(d-s)/2+np.hypot(L,W)/2
ax.add_patch(MCircle(cen,r,fill=False,ec=C["aux"],ls="--",lw=1,label="CircleAtEdge (prefilter)"))
ax.set_title("(b) Translation between two nodes",fontsize=10); ax.legend(fontsize=7.5,loc="lower center",bbox_to_anchor=(.5,-.32)); clean(ax,((-3,6),(-4,5.5)))
# (c) rotation node: circumscribed 32-gon around half the largest vertex distance
ax=axs[2]; maxd=np.hypot(L,W); r=maxd/2; n=32; rb=r/np.cos(np.pi/n); th=np.linspace(0,2*np.pi,n+1)
ax.add_patch(MPoly(np.c_[rb*np.cos(-th),rb*np.sin(-th)],closed=True,fc=C["pt"],alpha=.15,ec=C["pt"],lw=2,label="RotationCirclePoly (32-gon)"))
for deg in (0,45,90): ax.add_patch(MPoly(rot(base,deg,False),closed=True,fill=False,ec=C["s1"],lw=1,alpha=.7))
ax.add_patch(MCircle((0,0),r,fill=False,ec=C["aux"],ls=":",lw=1,label="radius = diagonal / 2"))
ax.text(0,-2.75,f"r = ½·√(L²+W²) = {r:.2f} m,  polygon radius r / cos(π/32)",ha="center",fontsize=8)
ax.set_title("(c) Rotation in place",fontsize=10); ax.legend(fontsize=7.5,loc="lower center",bbox_to_anchor=(.5,-.32)); clean(ax,((-3,3),(-3.2,3)))
fig.suptitle("CollisionEntity geometry for the AGV footprint (157.5 in × 73.5 in)",fontsize=11)
fig.tight_layout(); go(fig,"collision_geometry"); print("ok", L, W, r)
