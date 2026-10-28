"""Draw an exact-coordinate district index map from the exported manifest."""
from pathlib import Path
import argparse,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from matplotlib.path import Path as MPath
ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
p=json.loads(a.plan.read_text());manifest=json.loads(a.manifest.read_text());palette=['#C3DBCF','#C9D8A5','#F1D4A3','#E7C4B1','#A8D2C3','#B7D7E8','#CDC9E6','#DAC5DB','#A6CBBC','#BFD3A2','#86BAC6','#B8DBD8','#D3BF92','#D7CEAA','#C8AF9E','#DFBF99','#D58D49','#C3DCE8'];fig=plt.figure(figsize=(16,11.4),facecolor='#f7f8f8');ax=fig.add_axes([.035,.095,.67,.81]);ax.set_facecolor('#dcecf2');ax.set_aspect('equal');ax.set_xlim(-2050,2050);ax.set_ylim(-2050,2050);ax.set_xticks(np.arange(-2000,2001,1000));ax.set_yticks(np.arange(-2000,2001,1000));ax.tick_params(labelsize=9,colors='#627078');ax.grid(alpha=.2,color='#78909C');ax.set_xlabel('Blender X / metres',fontsize=10,color='#52636d');ax.set_ylabel('Blender Y / metres',fontsize=10,color='#52636d')
for spine in ax.spines.values():spine.set_color('#a8bdc6')
regions=[]
for row in range(2):
    for col in range(4):regions.append(('MAIN',[-2000,-850,0,850,2000][col],[-2000,-850,0,850,2000][col+1],[-200,900,2050][row],[-200,900,2050][row+1]))
for region,xs,ys in [('WEST',[-2050,-1000,0],[-2050,-800,100]),('EAST',[0,1050,2050],[-2050,-1050,100])]:
    for row in range(2):
        for col in range(2):regions.append((region,xs[col],xs[col+1],ys[row],ys[row+1]))
clips={}
for region,coast in p['coasts'].items():
    patch=Polygon(coast,closed=True,facecolor='none',edgecolor='none');ax.add_patch(patch);clips[region]=patch
for i,(region,x0,x1,y0,y1) in enumerate(regions):
    patch=Rectangle((x0,y0),x1-x0,y1-y0,facecolor=palette[i],edgecolor='white',lw=1.8,zorder=2);patch.set_clip_path(clips[region]);ax.add_patch(patch)
lake=Polygon(p['lake'],closed=True,facecolor='#c3dce8',edgecolor='#8fafba',lw=.7,zorder=3);ax.add_patch(lake)
for e in p['edges']:
    xy=np.array(e['points']);ax.plot(xy[:,0],xy[:,1],color='#c57d35' if e['bridge'] else '#6c7b78',lw=1.35 if e['bridge'] else .45,alpha=.95 if e['bridge'] else .45,zorder=4)
for region,coast in p['coasts'].items():ax.add_patch(Polygon(coast,closed=True,fill=False,edgecolor='#55756f',lw=.9,zorder=5))
for i,(region,x0,x1,y0,y1) in enumerate(regions):
    gx,gy=np.meshgrid(np.linspace(x0,x1,45),np.linspace(y0,y1,45));xy=np.c_[gx.ravel(),gy.ravel()];valid=MPath(p['coasts'][region]).contains_points(xy)
    if region=='WEST':valid&=~MPath(p['lake']).contains_points(xy)
    pts=xy[valid];mean=pts.mean(0);center=pts[np.argmin(np.linalg.norm(pts-mean,axis=1))];ax.text(*center,f'{i+1:02d}',ha='center',va='center',fontsize=14,weight='bold',color='#233d45',bbox={'boxstyle':'round,pad=.23','facecolor':'white','edgecolor':'none','alpha':.92},zorder=8)
ax.text(-15,-890,'17',ha='center',fontsize=13,weight='bold',color='#8d4f1c',bbox={'boxstyle':'round,pad=.22','facecolor':'white','edgecolor':'#ce955b'},zorder=9);ax.text(50,-500,'18',ha='center',fontsize=13,weight='bold',color='#416a7a',bbox={'boxstyle':'round,pad=.22','facecolor':'white','edgecolor':'#9dbfcd'},zorder=9)
row=p['connected_arcades'];apt=p['oldtown_expansion']['apartment'];ax.scatter([row['front_origin'][0],apt['center'][0]],[row['front_origin'][1],apt['center'][1]],marker='*',s=130,c='#b33c2c',edgecolors='white',linewidths=.6,zorder=10)
ax.annotate('N',xy=(1875,1800),xytext=(1875,1430),ha='center',va='center',fontsize=12,weight='bold',arrowprops={'arrowstyle':'-|>','color':'#405560','lw':1.5},zorder=8)
legend=fig.add_axes([.735,.11,.25,.82]);legend.axis('off');legend.text(0,1.02,'DISTRICT FILES',fontsize=16,weight='bold',color='#203d48');short=['Main southwest','Main south-west centre','Old-town corner frontage','Main southeast','Main northwest','Main north-west centre','CBD / north-east centre','Main northeast','West island southwest','West island southeast','West island northwest','Lake / west northeast','East island southwest','East island southeast','East island northwest','Port / east northeast','Shared bridges + approaches','Shared sea + lake']
for i,d in enumerate(manifest['districts']):
    y=.965-i*.0477;legend.add_patch(Rectangle((0,y-.011),.031,.024,facecolor=palette[i],edgecolor='none',transform=legend.transAxes));legend.text(.05,y,f'{i+1:02d}  {short[i]}',fontsize=10.6,color='#314e59',va='center');legend.text(.99,y,(f"{d['file_size_bytes']/1024:.0f} KB" if d['file_size_bytes']<100000 else f"{d['file_size_bytes']/1e6:.1f} MB"),fontsize=9.7,color='#617883',ha='right',va='center')
legend.text(0,.055,'Stars: updated street and apartment',fontsize=10.1,color='#9a3b2d');legend.text(0,.005,'Shared files 17 and 18 can stay loaded.\nLand districts can be loaded separately.',fontsize=10.2,color='#536d77',linespacing=1.6)
fig.text(.04,.965,'HERO_13  /  CITY DISTRICT INDEX',fontsize=23,weight='bold',color='#203d48');fig.text(.04,.932,'16 land districts + 2 shared models  |  4 km x 4 km city  |  18 self-contained GLBs',fontsize=12,color='#5e7782');fig.text(.04,.035,'All files retain the same world coordinates. Place each imported root at (0, 0, 0); 1 unit = 1 metre.',fontsize=11,color='#526e79');fig.text(.04,.014,'Buildings and their foundations stay together. Surface triangles keep their original boundary coordinates.',fontsize=10,color='#6e858e')
for ext in ['png','svg']:fig.savefig(a.out/('city_districts_map.'+ext),dpi=160,facecolor=fig.get_facecolor())
svg_path=a.out/'city_districts_map.svg'
svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
plt.close(fig)
