"""Create the guide's schematic from the sensor baselines in magnetic_guide_sensor.hpp."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc
plt.rcParams.update({'svg.fonttype':'none','font.family':'DejaVu Sans','font.size':11})
lf,lr=2.454,1.494
slope=0.04
bx,by=0.016,0.012
psi=np.arctan(slope)
f=by+lf*slope/2;b=-by+lf*slope/2
l=-bx+lr*slope/2;r=bx+lr*slope/2
fig,(ax,eq)=plt.subplots(1,2,figsize=(13.5,7.2),gridspec_kw={'width_ratios':[1.05,1]})
fig.subplots_adjust(left=.065,right=.97,top=.88,bottom=.11,wspace=.23)
fig.suptitle('Magnetic-guide alignment: sensor geometry and pair equations',fontsize=17,weight='bold')
# Display coordinates (u,v)=(-body_y,body_x): nose up, body +y left.
ax.set_aspect('equal');ax.set_xlim(-1.38,1.38);ax.set_ylim(-1.65,1.65);ax.axis('off')
ax.add_patch(Rectangle((-lr/2,-lf/2),lr,lf,facecolor='#eef4fa',edgecolor='#51728f',linewidth=1.5))
v=np.linspace(-1.49,1.49,150)
ax.plot(by+slope*v,v,'--',color='#d97706',linewidth=2,label='Longitudinal guide')
u=np.linspace(-1.13,1.13,150)
ax.plot(u,-bx-slope*u,'--',color='#008879',linewidth=2,label='Transverse guide')
sensors={'F':(0,lf/2),'B':(0,-lf/2),'L':(-lr/2,0),'R':(lr/2,0)}
for name,(u0,v0) in sensors.items():
 ax.scatter(u0,v0,s=72,color='#244a70',zorder=5)
 offsets={'F':(-.23,.08),'B':(-.23,-.15),'L':(-.2,.11),'R':(.08,.11)}
 du,dv=offsets[name];ax.text(u0+du,v0+dv,name,weight='bold',fontsize=13)
ax.scatter(0,0,s=36,color='#111827',zorder=6)
ax.annotate('O: robot centre',xy=(0,0),xytext=(-.63,-.50),arrowprops={'arrowstyle':'-','color':'#6b7280'},fontsize=11)
ax.annotate('',xy=(0,1.53),xytext=(0,1.30),arrowprops={'arrowstyle':'->','color':'#111827','lw':1.5})
ax.text(.07,1.5,'+x (forward)',fontsize=10)
ax.annotate('',xy=(-1.04,0),xytext=(-.82,0),arrowprops={'arrowstyle':'->','color':'#111827','lw':1.5})
ax.text(-1.26,-.13,'+y (left)',fontsize=10)
ax.annotate('',xy=(1.02,lf/2),xytext=(1.02,-lf/2),arrowprops={'arrowstyle':'<->','color':'#51728f'})
ax.text(1.09,0,'L_FB = 2.454 m',rotation=90,va='center',color='#244a70')
ax.annotate('',xy=(-lr/2,-1.46),xytext=(lr/2,-1.46),arrowprops={'arrowstyle':'<->','color':'#51728f'})
ax.text(0,-1.57,'L_LR = 1.494 m',ha='center',color='#244a70')
# Deviations are exaggerated only for arrow legibility; leader endpoints remain true schematic intersections.
for name,label,xy,xytext in [('F','f', (f,lf/2),(.40,.97)),('B','b',(-b,-lf/2),(.40,-.97)),('L','l',(-lr/2,l),(-1.12,.46)),('R','r',(lr/2,-r),(.93,-.47))]:
 ax.annotate(label,xy=xy,xytext=xytext,color='#7c3e00' if name in ('F','B') else '#006c61',fontsize=15,arrowprops={'arrowstyle':'->','color':'#6b7280','lw':.8})
# Clockwise guide tilt relative to forward body axis; psi has the estimator's opposite yaw convention.
ax.text(.35,.48,r'$s=\tan\psi$',color='#d97706',fontsize=13)
ax.text(-1.32,1.64,'Body frame and guide families',fontsize=12,weight='bold')
ax.legend(loc='lower left',bbox_to_anchor=(-.03,-.105),frameon=False,fontsize=9)
eq.axis('off');eq.set_xlim(0,1);eq.set_ylim(0,1)
eq.text(0,1.0,'Source-consistent signed measurement model',weight='bold',fontsize=12)
lines=[(r'$f=y_0+(L_{\rm FB}/2)s$',r'$b=-y_0+(L_{\rm FB}/2)s$'),(r'$l=-x_0+(L_{\rm LR}/2)s$',r'$r=x_0+(L_{\rm LR}/2)s$')]
y=.9
for first,second in lines:
 eq.text(0,y,first,fontsize=14);eq.text(0,y-.075,second,fontsize=14);y-=.20
eq.text(0,.47,'Sums cancel translation; differences isolate it.',fontsize=11)
eq.text(0,.39,r'$f+b=L_{\rm FB}s,\quad l+r=L_{\rm LR}s$',fontsize=14)
eq.text(0,.30,r'$f-b=2y_0,\quad r-l=2x_0$',fontsize=14)
eq.text(0,.19,r'$\psi=\arctan s,\quad x=x_0\cos\psi,\quad y=y_0\cos\psi$',fontsize=13)
eq.text(0,.075,'Signs follow the C++ conventions. Guide families are perpendicular.\nThe sketch is schematic: small offsets are labelled with leaders.\nIt is not an AGV mesh, calibration measurement, or ground-truth pose.',fontsize=10,linespacing=1.45,va='top')
fig.savefig('volley_magnetic_guide_geometry.svg',format='svg',facecolor='white')
fig.savefig('magnetic_guide_preview.png',dpi=130,facecolor='white')
print('Generated SVG and preview; example readings (mm):',np.round(np.array([f,b,l,r])*1000,2))
