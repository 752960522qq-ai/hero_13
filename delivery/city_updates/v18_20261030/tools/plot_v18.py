"""Render the exact local-metre planning boundary; future parcels remain unbuilt."""
from pathlib import Path
import json,os,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,PathPatch,Patch
from matplotlib.path import Path as MPath
from matplotlib.font_manager import FontProperties
R=Path(__file__).resolve().parents[1];font=Path(os.environ.get('HERO13_MAP_FONT',str(R.parent/'tools_runtime/NotoSansCJKsc-Regular.otf')));cn=font.exists()
if cn:plt.rcParams['font.family']=FontProperties(fname=font).get_name();import matplotlib.font_manager as fm;fm.fontManager.addfont(str(font));plt.rcParams['axes.unicode_minus']=False
p=json.load(open(R/'model/city_plan.json'));town=p['urban_areas_v18']['new_town'];fig,axs=plt.subplots(1,2,figsize=(19,10),gridspec_kw={'width_ratios':[1.2,1]});fig.patch.set_facecolor('#f8f7f2')
colors={'commercial':'#efbd56','civic':'#80afca','residential':'#b5c89a','mixed_use':'#dec6a6','green_buffer':'#b9d2b0'}
for ax in axs:
 ax.set_facecolor('#d9e9ed');ax.add_patch(Polygon(p['coasts']['MAIN'],facecolor='#eeede5',edgecolor='#677d80',lw=1.2));ax.set_aspect('equal');ax.grid(alpha=.16,zorder=1);ax.tick_params(labelsize=9)
for ax in axs:
 ax.add_patch(Polygon(town['polygon'],facecolor='#d4c9ed',edgecolor='#7556a5',alpha=.24,lw=2.5,zorder=2))
 for q in town['land_use_parcels']:
  vs=[];cs=[]
  for ring in [q['polygon']]+q['holes']:
   vs.extend(ring);cs.extend([MPath.MOVETO]+[MPath.LINETO]*(len(ring)-2)+[MPath.CLOSEPOLY])
  ax.add_patch(PathPatch(MPath(vs,cs),facecolor=colors[q['role']],edgecolor='#8c887a',lw=.5,alpha=.65,hatch='///' if q['status']=='reserved_unbuilt' else None,zorder=3))
 for e in p['edges']:
  if e['region']!='MAIN':continue
  xy=np.array(e['points']);ax.plot(xy[:,0],xy[:,1],color='#fffefa',lw=2.8,zorder=4);ax.plot(xy[:,0],xy[:,1],color='#a2a49f',lw=.75,zorder=4)
 for b in p['buildings']:
  if b['region']!='MAIN':continue
  ax.add_patch(Polygon(b['footprint'],facecolor='#a3af9d' if b['name'] in town['existing_residential_lots'] else '#c7c5bb',edgecolor='none',zorder=5))
 for r in p['real_buildings']:
  if r.get('region')!='MAIN':continue
  new=r.get('added_in_version')=='v18';ax.add_patch(Polygon(r['footprint_xy'],facecolor='#bf603f' if new else '#708fa5',edgecolor='#8d402d' if new else 'none',lw=.65,zorder=6))
 for w in p['access_v18']:
  xy=np.array(w['route']);ax.plot(xy[:,0],xy[:,1],color='#8c739c',lw=1.5,zorder=5)
 ax.add_patch(Polygon(p['cbd_plan']['tianming']['polygon'],fill=False,edgecolor='#a375a5',lw=1.3,zorder=5))
 ax.add_patch(Polygon(town['polygon'],fill=False,edgecolor='#7556a5',lw=2,zorder=7))
axs[0].set(xlim=(-1000,1050),ylim=(-110,1280),title='北部主岛 · 城区关系' if cn else 'Main island: district context');axs[1].set(xlim=(560,1000),ylim=(385,1015),title='东部新城区 · 用地分区' if cn else 'Eastern new town: land use')
labels=[((-310,820),'天明预留地','Tianming reserved'),((60,1100),'CBD','CBD'),((-365,1110),'公寓区','Apartments'),((480,940),'市政区','Civic campus'),((200,260),'老城区','Old town')]
for xy,zh,en in labels:axs[0].text(*xy,zh if cn else en,fontsize=10,ha='center',bbox={'facecolor':'#fffefa','alpha':.85,'edgecolor':'none','pad':2},zorder=8)
for xy,zh,en in [((683,801),'商业中心 · 64号商场','Commercial: mall 64'),((685,958),'公共服务 · 65号警察总部','Civic: police HQ 65'),((755,550),f'原有居住片区 · {town["existing_residential_units"]}栋体块',f'Existing residential: {town["existing_residential_units"]} massing'),((755,825),'后续商务与居住用地\n预留，尚未建楼','Future mixed use\nReserved, unbuilt'),((760,685),'立交绿化缓冲带','Interchange green buffer')]:
 axs[1].text(*xy,zh if cn else en,fontsize=10,ha='center',bbox={'facecolor':'#fffefa','alpha':.88,'edgecolor':'none','pad':3},zorder=9)
for r in p['real_buildings']:
 if r.get('added_in_version')=='v18' and r['zone']=='OLDTOWN':axs[0].text(*r['center'],r['arcade_pool_key'],fontsize=6,color='#9d3920',zorder=9)
for ax in axs:ax.set_xlabel('世界坐标 X / m' if cn else 'World X / m');ax.set_ylabel('世界坐标 Y / m' if cn else 'World Y / m')
fig.suptitle(('城市 v18 · 10栋建筑落位与东部新城区划定' if cn else 'City v18: ten new source buildings and eastern new town')+'\n'+(f'新城区 {town["area_m2"]/1e6:.3f} km² · 老城沿街120栋保持 · 预留用地不计作已建建筑' if cn else f'New-town area {town["area_m2"]/1e6:.3f} km²; old-town street count stays 120; reserves are unbuilt'),fontsize=16,y=.98)
legend=[Patch(facecolor='#bf603f',label='本轮正式模型' if cn else 'New source buildings'),Patch(facecolor='#a3af9d',label='原有居住体块' if cn else 'Existing residential massing'),Patch(facecolor='#dec6a6',hatch='///',label='预留开发用地' if cn else 'Reserved development land')];fig.legend(handles=legend,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,.015));fig.tight_layout(rect=(0,.05,1,.92));(R/'renders').mkdir(exist_ok=True);fig.savefig(R/'renders/05_newtown_plan_v18.png',dpi=150)
