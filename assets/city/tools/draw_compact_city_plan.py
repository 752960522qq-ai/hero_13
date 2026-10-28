"""Metric planning and streaming district maps from the final model's actual geometry."""
import argparse,json,math,csv
from pathlib import Path
from compact_city_math import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Patch as LegendPatch
from matplotlib.collections import PatchCollection,LineCollection
from matplotlib.font_manager import FontProperties,fontManager
ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--font',type=Path,required=True);ap.add_argument('--districts',action='store_true')
a=ap.parse_args();p=json.loads(a.plan.read_text());a.out.mkdir(parents=True,exist_ok=True);fontManager.addfont(str(a.font));plt.rcParams['font.family']=FontProperties(fname=a.font).get_name();plt.rcParams['svg.fonttype']='path'
colors={'OLDTOWN':'#d7ae75','CBD':'#587e9a','RESIDENTIAL':'#adbbae','CIVIC':'#b09db7','UNIVERSITY':'#b7ba83','VILLAGE':'#b8be8f','INDUSTRIAL':'#8babad'}
fig,ax=plt.subplots(figsize=(13,12),facecolor='#f4f2e9');ax.set_facecolor('#c8dde0');islands={k:Polygon(v) for k,v in p['coasts'].items()};lake=Polygon(p['lake'])
if a.districts:
    palette=['#f0d7b0','#d5c8a9','#b8d3bf','#adcbd4','#dbc1b6','#b9cadf','#c2bcdf','#cdd8ab','#e7ccad','#c9d5aa','#b4cbc0','#b9dce0','#c0c8da','#dfc8c4','#b6ced6','#ccd5b8'];cuts={'MAIN':([-3000,-850,0,850,3000],[-3000,900,3000],0),'WEST':([-3000,-1000,3000],[-3000,-800,3000],8),'EAST':([-3000,1050,3000],[-3000,-1050,3000],12)}
    for reg,poly in islands.items():
        xs,ys,offset=cuts[reg]
        for j in range(len(ys)-1):
            for i in range(len(xs)-1):
                ix=offset+j*(len(xs)-1)+i;q=poly.intersection(shapely.box(xs[i],ys[j],xs[i+1],ys[j+1])).difference(lake)
                for part in shapely.get_parts(q):
                    if part.geom_type=='Polygon':ax.add_patch(Patch(np.asarray(part.exterior.coords),facecolor=palette[ix],edgecolor='#ffffff',linewidth=1.5))
                if not q.is_empty:
                    c=q.representative_point();ax.text(c.x,c.y,str(ix+1).zfill(2),fontsize=18,fontweight='bold',ha='center',va='center',color='#243c45',bbox=dict(facecolor='white',alpha=.78,edgecolor='none',pad=3))
else:
    for poly in islands.values():ax.add_patch(Patch(np.asarray(poly.exterior.coords),facecolor='#d6ddbf',edgecolor='#819b92',linewidth=.8))
    for zone,color in colors.items():
        shapes=[Patch(b['footprint']) for b in p['buildings'] if b['zone']==zone];ax.add_collection(PatchCollection(shapes,facecolor=color,edgecolor='none',alpha=.96))
ax.add_patch(Patch(np.asarray(lake.exterior.coords),facecolor='#b1d3d7',edgecolor='#729c9f',linewidth=.8))
for level in [6,7,9,15]:
    routes=[np.asarray(e['points'])[:,:2] for e in p['edges'] if e['carriage_width']==level];ax.add_collection(LineCollection(routes,colors='#5e6360' if level<15 else '#3e4c50',linewidths=.40 if level<9 else .65 if level<15 else 1.15,alpha=.9))
if not a.districts:ax.add_collection(LineCollection([r['points'] for r in p['pedestrian_alleys']],colors='#b26954',linewidths=.45))
ax.add_collection(PatchCollection([Patch(r['footprint_xy']) for r in p['real_buildings']],facecolor='#d76741',edgecolor='#613d33',linewidth=.35))
for ix,text,off in [(p['interchanges'][0],'中央立交 · 4 条连接匝道',(230,170)),(p['interchanges'][1],'东侧立交 · 2 条连接匝道',(170,-220))]:
    if a.districts:continue
    x,y=ix['center'];ax.plot(x,y,'o',color='#9c5444',ms=4);ax.annotate(text,(x,y),(x+off[0],y+off[1]),fontsize=10,color='#5e3c35',arrowprops=dict(arrowstyle='-',color='#9c5444',lw=.8),bbox=dict(facecolor='#fffaf0',edgecolor='none',alpha=.9,pad=3))
if not a.districts:
    for text,x,y in [('老城连续街区',-240,450),('CBD 高度核心',-300,1300),('大学及居住',-870,720),('市政文化区',1090,1130),('西岛村镇与湖区',-1250,-1250),('东岛工业与港区',1110,-1200)]:ax.text(x,y,text,fontsize=11,weight='bold',color='#2b464b',ha='center',bbox=dict(facecolor='#fffaf0',alpha=.85,edgecolor='none',pad=4))
    ax.legend(handles=[LegendPatch(facecolor=c,label={'OLDTOWN':'老城低层','CBD':'CBD 裙房与塔楼','RESIDENTIAL':'中层住宅','CIVIC':'市政文化','UNIVERSITY':'大学','VILLAGE':'村镇','INDUSTRIAL':'工业港区'}[k]) for k,c in colors.items()]+[LegendPatch(facecolor='#d76741',label='11 个原建筑素材')],loc='lower left',ncol=4,fontsize=9,framealpha=.92)
else:
    ax.text(-1660,-1710,'17 公共跨水桥梁　　18 公共海面与湖水\n各区块保留世界坐标；导入后位置与旋转归零、缩放为 1。',fontsize=10,color='#2e484e',va='top',bbox=dict(facecolor='white',edgecolor='none',pad=7,alpha=.95))
ax.plot([1150,1650],[-1750,-1750],color='#29464e',lw=3);ax.text(1400,-1710,'500 m',ha='center',fontsize=10,color='#29464e');ax.annotate('北',(-1700,1450),(-1700,1200),ha='center',fontsize=12,arrowprops=dict(arrowstyle='-|>',color='#29464e',lw=1.3),color='#29464e')
ax.set_xlim(-1850,1770);ax.set_ylim(-1900,1700);ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
for spine in ax.spines.values():spine.set_visible(False)
title='城市 18 区块索引' if a.districts else '5.8 km² 城市重构总图'
fig.suptitle(title,x=.07,y=.965,ha='left',fontsize=24,weight='bold',color='#263e45');fig.text(.07,.922,'净陆地 5.80 km²  ·  含跨水桥面约 5.84 km²  ·  水域不计入',fontsize=12,color='#49646b');fig.text(.07,.055,f"道路 {p['stats']['road_length_m']/1000:.1f} km　／　119 条街巷　／　2 处立交、6 条匝道　／　原建筑保持米制比例",fontsize=11,color='#49646b');fig.subplots_adjust(left=.04,right=.98,bottom=.08,top=.90)
stem='city_districts_map' if a.districts else 'compact_city_plan';fig.savefig(a.out/(stem+'.png'),dpi=190);fig.savefig(a.out/(stem+'.svg'));plt.close(fig)
