"""Exact plan view of every replaced rear site, with the seven source types."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'.deps'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Patch as Legend
from shapely.geometry import Polygon,LineString
p=json.loads((ROOT/'work_v11/model/city_plan.json').read_text());out=ROOT/'work_v11/previews';out.mkdir(parents=True,exist_ok=True)
fig,ax=plt.subplots(figsize=(15,10));ax.set_facecolor('#eeebe3')
for e in p['edges']:
    if e['region']!='MAIN':continue
    q=LineString([v[:2] for v in e['points']]).buffer(e['width']/2)
    if q.bounds[0]>620 or q.bounds[2]<-240 or q.bounds[1]>540 or q.bounds[3]<5:continue
    ax.add_patch(Patch(q.exterior.coords,facecolor='#b9bcbf',edgecolor='none'))
for b in p['buildings']:
    if b['zone']=='OLDTOWN':ax.add_patch(Patch(b['footprint'],facecolor='#ccc2b6',edgecolor='white',lw=.35))
for a in p['pedestrian_alleys']:
    x,y=zip(*a['points']);ax.plot(x,y,color='#66888a',lw=1.2,zorder=2)
colors={20:'#6d8c55',19:'#b77641',18:'#5285ab',17:'#94714d',15:'#355da5',13:'#9a6998',14:'#b1516a'}
for r in p['real_buildings']:
    if r['instance_name'].startswith('CBD_'):continue
    key=r.get('source_key');color=colors.get(key,'#9b8e87')
    if 'Backlane_Apartment_13'in r['instance_name']:color=colors[13]
    if 'Backlane_Apartment_14'in r['instance_name']:color=colors[14]
    ax.add_patch(Patch(r['footprint_xy'],facecolor=color,edgecolor='#514b43',lw=.4,zorder=4))
for r in p['rear_access_links']:
    q=LineString(r['points']).buffer(1.8,cap_style=2,join_style=2);ax.add_patch(Patch(q.exterior.coords,facecolor='#e7a13b',edgecolor='none',zorder=3))
ax.set_xlim(-240,610);ax.set_ylim(5,540);ax.set_aspect('equal');ax.set_xlabel('East / metres');ax.set_ylabel('North / metres');ax.set_title('Old town v11 — all 35 rear sites replaced; 62 rear buildings\nWhole city: 665 buildings | Net land: 3.25 km²',pad=14)
handles=[Legend(facecolor=colors[k],label=f'Asset {k}') for k in [13,14,15,17,18,19,20]]+[Legend(facecolor='#e7a13b',label='New access links'),Legend(facecolor='#ccc2b6',label='Street placeholders')]
ax.legend(handles=handles,loc='lower left',ncol=3,fontsize=8,framealpha=.97);fig.tight_layout();fig.savefig(out/'05_rear_replacement_map.png',dpi=180)
print('V11_MAP_SAVED',flush=True)
