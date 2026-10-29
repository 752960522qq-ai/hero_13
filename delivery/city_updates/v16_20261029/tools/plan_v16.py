import os
import sys,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'tools_runtime/pydeps'))
import numpy as np,shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
p=json.load(open(R/'baseline/city_plan.json'));assets={r['file']:r for r in json.load(open(R/'asset_inspection.json'))};land=Polygon(p['coasts']['MAIN']);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.12,join_style=2) for e in p['edges']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
removed={b['name'] for b in p['buildings'] if b['zone'] in ['APARTMENT','GOVERNMENT']};moving={'APT_V14_A36'}
fixed=[Polygon(b['footprint']) for b in p['buildings'] if b['name'] not in removed]+[Polygon(r['footprint_xy']) for r in p['real_buildings'] if r['instance_name'] not in moving];occupied=unary_union(fixed+[reserve]);sites=[]
def fp(c,w,d,theta):
 q=np.array([[-w/2,-d/2],[w/2,-d/2],[w/2,d/2],[-w/2,d/2]]);t=math.radians(theta);M=np.array([[math.cos(t),-math.sin(t)],[math.sin(t),math.cos(t)]]);return Polygon(q@M.T+np.array(c))
def place(name,center,w,d,kind,file=None,height=None,group=None,region=None):
 global occupied
 options=[];allowed=Polygon(p['urban_areas_v14']['north_apartments']['polygon']) if kind=='APARTMENT' else (box(-185,748,330,1085) if kind=='CBD' else box(400,780,580,925));free=allowed.difference(unary_union([roads.buffer(1.2),occupied.buffer(2.5)]));shapely.prepare(free)
 for deg in ([180,0] if kind=='APARTMENT' and center[1]<1150 else [0,180]):
  for dx in range(-20,21,5):
   for dy in range(-15,16,5):
    c=[center[0]+dx,center[1]+dy];q=fp(c,w,d,deg)
    if not free.covers(q):continue
    if region and not region.covers(q):continue
    options.append((dx*dx+dy*dy+(0 if deg==(180 if kind=='APARTMENT' and center[1]<1150 else 0) else .1),c,deg,q))
 if not options:raise RuntimeError(('No legal site',name,center,w,d))
 _,c,deg,q=min(options,key=lambda x:x[0]);occupied=unary_union([occupied,q.buffer(4.5)]);s={'id':name,'kind':kind,'center':c,'theta_degrees':deg,'footprint':list(q.exterior.coords)[:-1],'file':file,'target_height_m':height,'group':group};sites.append(s);print(name,c,deg,w,d,flush=True);return s
old=next(r for r in p['real_buildings'] if r['instance_name']=='APT_V14_A36');q=Polygon(old['footprint_xy']);lo=q.bounds;place('APT_V14_A36',[-45,1045],lo[2]-lo[0],lo[3]-lo[1],'CBD',height=75)
configs=[('YELLOW_50','05-apartment-building-50.glb',58,[(-430,1182),(-365,1182),(-430,1106),(-365,1106)],box(-485,1080,-315,1210)),('PINK_53','02-pink-high-rise-building-3d-model-53.glb',62,[(-260,1182),(-195,1182),(-260,1106),(-195,1106)],box(-305,1080,-145,1215)),('GRAY_54','01-apartment-building-54.glb',68,[(230,1168),(300,1168),(160,1168),(390,1145)],box(140,1080,470,1200))]
for group,file,h,centers,area in configs:
 a=assets[file];w=a['size'][0]/a['size'][2]*h;d=a['size'][1]/a['size'][2]*h
 for i,c in enumerate(centers,1):place('APT_V16_'+group+f'_{i:02d}',c,w,d,'APARTMENT',file,h,group,area)
for file,h,c,name in [('04-office-building-3d-model-51.glb',22,[480,815],'GOV_V16_OFFICE_51'),('03-hotel-building-3d-model-52.glb',17,[548,830],'GOV_V16_DORM_52')]:
 a=assets[file];place(name,c,a['size'][0]/a['size'][2]*h,a['size'][1]/a['size'][2]*h,'GOVERNMENT',file,h)
for i,c in enumerate([[425,810],[425,860],[445,895],[550,895]],1):place('GOV_V16_SUPPORT_'+str(i),c,30,34,'GOVERNMENT',height=10.5 if i%2 else 12)
# Retained civic main building participates in every collision check.
(R/'layout_v16.json').write_text(json.dumps({'sites':sites,'removed_placeholder_ids':sorted(removed),'retained_main':'GOV_V14_G33','apartment_groups':3,'instances_per_apartment_type':4},indent=2))
