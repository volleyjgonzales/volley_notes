#!/usr/bin/env python3
"""Pecos YAML-derived background figures; scenario occupancy is illustrative."""
from pathlib import Path
import sys, math, yaml
sys.path.insert(0,str(Path(__file__).parent))
from draw import agv
from figstyle import plt, BG, CARD, BORDER, FG, MUTED, SKY, GREEN, AMBER, VIOLET, MONO
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, FancyBboxPatch
root=Path(__file__).resolve().parents[1]
d=yaml.safe_load(open(root/'sources'/'5675_pecos_combined.yaml'))
N={v['id']:v for v in d['nodes']}; E=[(e['src'],e['dst']) for e in d['edges']]
plt.rcParams.update({'svg.fonttype':'none','font.family':['DejaVu Sans'],'font.size':10})

def render(name, agvs=(), trays=(), paths=(), note=''):
 fig,ax=plt.subplots(figsize=(15,9));fig.patch.set_facecolor(BG);ax.set_facecolor(BG)
 ax.set_xlim(18,49);ax.set_ylim(4,29);ax.set_aspect('equal');ax.grid(color='#26334b',linewidth=.5,alpha=.55);ax.set_axisbelow(True)
 ax.set_xlabel('x — facility coordinates (m)',color=FG);ax.set_ylabel('y — facility coordinates (m)',color=FG)
 ax.tick_params(colors=MUTED,labelsize=8)
 # aisle shading only schematic to aid reading, not a measured footprint
 for yy in (8.2,12.78,17.17,21.74,24.02):
  ax.add_patch(Rectangle((29.6,yy-.42),15.3,.84,facecolor='#193149',edgecolor='none',alpha=.32,zorder=0))
 for a,b in E:
  p,q=N[a],N[b];ax.plot([p['x'],q['x']],[p['y'],q['y']],color='#64748b',lw=2.2,zorder=1)
 for i,n in N.items():
  x,y=n['x'],n['y'];typ=n['type']
  c={'Parking':SKY,'Bay':GREEN,'Waypoint':MUTED,'AgvCharge':VIOLET}.get(typ,AMBER)
  if typ=='Parking':
   ax.add_patch(Rectangle((x-2.05,y-.93),4.1,1.86,facecolor='#17283b',edgecolor=c,lw=1.1,alpha=.9,zorder=2))
  elif typ=='Bay':
   ax.add_patch(FancyBboxPatch((x-1.85,y-1.05),3.7,2.1,boxstyle='round,pad=.03,rounding_size=.22',facecolor='#133629',edgecolor=c,lw=2,zorder=2))
   ax.plot([x+1.87,x+1.87],[y-.72,y+.72],color=AMBER,lw=4,zorder=3)
  elif typ=='AgvCharge':
   ax.add_patch(Circle((x,y),.58,color='#2a2145',ec=c,lw=1.7,zorder=3))
  else: ax.add_patch(Circle((x,y),.16,color=c,zorder=3))
  # labels offset from node centers: parking above stalls, waypoint upper-left; never overlapping agents
  if typ in ('Parking','Bay'):
   ax.text(x,y+1.22,f'{"P" if typ=="Parking" else "B"}{i}',color=c,ha='center',va='bottom',fontsize=8.5,fontfamily='DejaVu Sans Mono',weight='bold',zorder=12,bbox=dict(fc=BG,ec='none',pad=.35))
  else:
   off=(-.55,.65) if typ=='Waypoint' else (1.25,.30)
   ax.text(x+off[0],y+off[1],f'{"W" if typ=="Waypoint" else "C"}{i}',color=c,ha='center',fontsize=7.5,zorder=12,bbox=dict(fc=BG,ec='none',pad=.3))
 for ids,color in paths:
  pts=[N[i] for i in ids]
  for a,b in zip(pts,pts[1:]):
   ax.add_patch(FancyArrowPatch((a['x'],a['y']),(b['x'],b['y']),arrowstyle='-|>',mutation_scale=18,color=color,linewidth=4.0,alpha=.9,zorder=6,shrinkA=12,shrinkB=12))
 for i,tray_label in trays:
  x,y=N[i]['x'],N[i]['y']
  ax.add_patch(FancyBboxPatch((x-1.1,y-.42),2.2,.84,boxstyle='round,pad=.02,rounding_size=.12',fc='#4a341f',ec=AMBER,lw=2.3,zorder=8))
  ax.text(x,y,tray_label,color=FG,fontsize=9,ha='center',va='center',zorder=9,fontfamily='DejaVu Sans Mono',weight='bold')
 for i,agv_label in agvs:
  x,y=N[i]['x'],N[i]['y'];agv(ax,x,y,math.pi/2,color=GREEN,L=.8,W=.62,scale=1.7,label=None)
  ax.text(x,y-1.05,agv_label,color=FG,fontsize=8,ha='center',va='top',zorder=12,bbox=dict(fc=BG,ec='none',pad=.5))
 ax.set_title('5675 Pecos — '+name,loc='left',color=FG,size=18,pad=20,weight='bold')
 ax.text(.01,-.13,'YAML geometry: node centers + graph edges. AGV and tray placement: illustrative scenario. '+note,transform=ax.transAxes,fontsize=10,color=MUTED,va='top')
 fig.subplots_adjust(left=.08,right=.98,top=.88,bottom=.19)
 dst=root/'figures'/('15_'+name.lower().replace(' ','_').replace('—','-')+'.svg');fig.savefig(dst,facecolor=BG,metadata={'Date':None});plt.close(fig);print(dst)
render('Facility topology',agvs=[(10,'AGV A')],trays=[(2,'T2'),(19,'T19')],note='No VRC node is defined.')
render('AGV approach and pickup',agvs=[(10,'AGV A')],trays=[(3,'T3')],paths=[([10,9,11,6,3],GREEN)],note='Charging-node departure and pickup are hypothetical.')
render('Blocking tray move',agvs=[(14,'AGV A')],trays=[(15,'ROOT'),(19,'BLOCK')],paths=[([19,23,22,18],AMBER),([15,19,23],GREEN)],note='Arrows depict graph routes, not validated collision-free schedules.')
