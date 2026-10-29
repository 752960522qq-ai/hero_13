"""Exact 2D plan from the final metric scene metadata, not a rendered scene."""
from pathlib import Path
import json,argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon as Patch,Rectangle
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--font',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
font_manager.fontManager.addfont(str(a.font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(a.font)).get_name();plt.rcParams['axes.unicode_minus']=False
p=json.loads(a.plan.read_text());fig=plt.figure(figsize=(18,12),facecolor='#f3f1eb');gs=fig.add_gridspec(2,2,width_ratios=[1.25,1.],height_ratios=[.65,1.05],wspace=.09,hspace=.19);axs=[fig.add_subplot(gs[:,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,1])]
colors={'CBD':'#6e8da0','APARTMENT':'#9a81ab','GOVERNMENT':'#be9065','VILLA':'#7c9b77'}
for ax in axs:
 ax.set_facecolor('#c5dfe4');ax.set_aspect('equal');ax.set_anchor('N');ax.grid(color='#8b989b',alpha=.15,linewidth=.5)
 for q in p['coasts'].values():ax.fill(*zip(*q),color='#e8e8db',zorder=0)
 ax.fill(*zip(*p['lake']),color='#c5dfe4',zorder=1)
 for key in ['municipal_campus','north_apartments','southwest_villas']:
  q=p['urban_areas_v14'][key]['polygon'];color={'municipal_campus':'#c79976','north_apartments':'#ac91bb','southwest_villas':'#8dab83'}[key];ax.fill(*zip(*q),facecolor=color,alpha=.25,zorder=1);ax.plot(*zip(*q),color=color,lw=1.4,zorder=2)
 for e in p['edges']:
  xy=np.array(e['points']);ax.plot(xy[:,0],xy[:,1],color='#8a918d',lw=max(.5,e['width']/13),zorder=2)
 for w in p['access_v14']:
  xy=np.array(w['route']);ax.plot(xy[:,0],xy[:,1],color='#d0b586',lw=1.1,zorder=3)
 for b in p['buildings']:ax.fill(*zip(*b['footprint']),color=colors.get(b['zone'],'#b5b6ab'),zorder=4,linewidth=.2,edgecolor='#80867c')
 for r in p['real_buildings']:ax.fill(*zip(*r['footprint_xy']),color=colors.get(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN'),'#8f9e9f'),zorder=5,linewidth=.4,edgecolor='#526c73')
 q=p['cbd_plan']['tianming']['polygon'];ax.fill(*zip(*q),color='#e7cd8f',edgecolor='#ae8d45',linewidth=1.3,zorder=4)
 q=np.array(p['cbd_plan']['boundary']);ax.plot(q[:,0],q[:,1],color='#718999',ls=(0,(4,3)),lw=1,zorder=5)
 xy=np.array(p['urban_areas_v14']['binhai_avenue']['centerline']);ax.plot(xy[:,0],xy[:,1],color='#d99242',lw=3.0,zorder=6)
 for spine in ax.spines.values():spine.set_color('#929b96')
 ax.tick_params(labelsize=9,colors='#52615b')
axs[0].set(xlim=(-1480,1240),ylim=(-1260,1270),title='三岛区域总览 · 米制世界坐标');axs[1].set(xlim=(-520,1010),ylim=(630,1245),title='主岛北部 · CBD / 市政府 / 公寓');axs[2].set(xlim=(-1225,-995),ylim=(-1045,-880),title='西南岛别墅区 · 9 个地块，约 2.52 万平方米')
def label(ax,text,xy,loc,color='#35433d'):
 ax.annotate(text,xy=xy,xytext=loc,fontsize=12,color=color,ha='left',va='center',arrowprops={'arrowstyle':'-','color':color,'lw':1},bbox={'boxstyle':'round,pad=.35','fc':'#f7f5ed','ec':'none','alpha':.94},zorder=10,clip_on=True)
label(axs[0],'滨海大道\n约 930 米临海步道',(-798,650),(-1430,790),'#955b25')
label(axs[0],'北侧公寓区\n3 栋素材高层 + 9 栋中层占位',(-130,1170),(-1420,1180),'#72597d')
label(axs[0],'市政府片区\n主楼 + 6 栋低层附属占位',(700,870),(450,480),'#90633e')
label(axs[0],'西南岛小型别墅区\n9 栋占位楼与庭院',(-1110,-960),(-1425,-1080),'#50734b')
label(axs[1],'天明大厦预留地\n172 × 195 米',(-289,832),(-470,692),'#84682d')
label(axs[1],'公寓区 · 12 座',(-130,1180),(120,1220),'#72597d')
label(axs[1],'市政府主楼 33',(697,904),(650,1030),'#90633e')
for i,b in enumerate(sorted([b for b in p['buildings'] if b['zone']=='VILLA'],key=lambda b:(-b['center'][1],b['center'][0]))):axs[2].text(*b['center'],str(i+1),fontsize=11,ha='center',va='center',zorder=8,color='white',clip_on=True)
for ax,x,y,l in [(axs[0],-1400,-1160,300),(axs[1],-465,661,200),(axs[2],-1210,-1038,50)]:
 ax.plot([x,x+l],[y,y],color='#40534b',lw=3,zorder=9);ax.text(x+l/2,y+7,str(l)+' m',ha='center',fontsize=9,color='#40534b',zorder=9)
fig.suptitle('城市 v14 · 四个片区落位与新增建筑部署',fontsize=23,x=.05,ha='left',y=.974,color='#2f433b');fig.text(.05,.938,'净陆地 3.25 km²  ·  全城 664 座  ·  CBD 29 座素材建筑，另预留天明大厦 1 座容量',fontsize=13,color='#53675c')
fig.text(.05,.027,'彩色建筑为本次重点片区；灰色为保留街区。规划图依据实际模型坐标绘制，地形起伏以 Blender 实景预览为准。',fontsize=11,color='#61736a')
fig.subplots_adjust(top=.90,bottom=.07,left=.05,right=.98)
a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=170,facecolor=fig.get_facecolor())
