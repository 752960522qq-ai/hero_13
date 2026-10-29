import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from pathlib import Path
r=Path(__file__).resolve().parents[1];p=json.loads((r/'model/city_plan.json').read_text());fig,ax=plt.subplots(figsize=(15,10),facecolor='#f6f4ee');ax.set_facecolor('#f6f4ee')
for e in p['edges']:
 if e['region']!='MAIN':continue
 xy=e['points'];ax.plot([q[0] for q in xy],[q[1] for q in xy],color='#6e7376' if e['layer'].startswith('GROUND') else '#aa845b',lw=max(.9,e['width']*.14),zorder=1)
for b in p['buildings']:
 cbd=b['zone']=='CBD';ax.add_patch(Polygon(b['footprint'],fc='#a9afb1' if cbd else '#deded5',ec='#62696b' if cbd else '#c4c5bd',lw=.7,zorder=2))
for b in p['real_buildings']:
 cbd=b.get('zone','CBD' if b['instance_name'].startswith('CBD_') else 'OLDTOWN')=='CBD'
 if not cbd:continue
 new=b.get('added_in_version')=='v13';ax.add_patch(Polygon(b['footprint_xy'],fc='#238a85' if new else '#4e7896',ec='#20485c',lw=1.1,zorder=3));ax.text(*b['center'],str(b.get('source_key') or ('02' if 'Glass' in b['instance_name'] else '01')),ha='center',va='center',color='white',fontsize=8,zorder=4)
site=p['cbd_plan']['tianming'];ax.add_patch(Polygon(site['polygon'],fc='#d8bc8d',ec='#9b6b22',lw=2,zorder=3));ax.text(-289,832.5,'TIANMING TOWER\n172 × 195 m\n33,540 m² RESERVED',ha='center',va='center',color='#5a3c13',fontsize=12,fontweight='bold',zorder=5)
for w in p['cbd_access_v13']:
 ax.add_patch(Polygon(w['polygon'],fc='#dbcfa9',ec='#b5a773',lw=.6,zorder=2))
ax.add_patch(Polygon(p['cbd_plan']['boundary'],fill=False,ec='#a54336',lw=2,linestyle=(0,(5,3)),zorder=6))
ax.set(xlim=(-470,610),ylim=(610,1155),xlabel='East / metres',ylabel='North / metres',title='CBD v13: 29 buildings + 1 Tianming Tower reservation');ax.set_aspect('equal');ax.grid(alpha=.15)
ax.legend(handles=[Patch(fc='#4e7896',label='10 existing source buildings'),Patch(fc='#238a85',label='4 newly supplied offices'),Patch(fc='#a9afb1',label='15 placeholders'),Patch(fc='#d8bc8d',label='Tianming reservation'),Patch(fc='none',ec='#a54336',label='CBD boundary: 0.3655 km²')],loc='lower center',bbox_to_anchor=(.5,-.18),ncol=3,frameon=False);fig.tight_layout();fig.savefig(r/'previews/05_cbd_plan_v13.png',dpi=170,bbox_inches='tight');print('CBD_PLAN_RENDERED')
