"""Compose distinct neighborhoods using explicit initial anchors and collision-constrained adjustment."""
from pathlib import Path
import json,math,collections
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from scipy.optimize import linear_sum_assignment
R=Path(__file__).resolve().parents[1];p=json.load(open(R/'baseline/city_plan.json'));catalog={a['asset_id']:a for a in json.load(open(R/'asset_catalog.json'))}
removed=[b for b in p['buildings'] if (b['zone']=='RESIDENTIAL' and b['block_id'] in [89,94]) or (b['region']=='WEST' and b['block_id']==13) or b['name'] in ['EAST_INDUSTRIAL_0043','EAST_INDUSTRIAL_0044','EAST_INDUSTRIAL_0046','EAST_INDUSTRIAL_0047']]
removed_names={b['name'] for b in removed};fixed=[b for b in p['buildings'] if b['name'] not in removed_names]+p['real_buildings'];fixedpoly=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in fixed]);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.45,join_style=2) for e in p['edges']]);lands={k:Polygon(v) for k,v in p['coasts'].items()};reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
rows=[]
def add(group,sid,xy,angle=0,scale=1):rows.append({'group':group,'asset_id':sid,'initial_center':xy,'rotation_deg':angle,'scale':scale})
for row in [
('S02-B01',[644,451],-90),('S02-B02',[644,472],-90),('S02-B04',[644,493],-90),
('S06-B03',[676,435],0),('S06-B04',[695.8,435],-90),('S06-B06',[710.5,435],-90),('S04-B03',[727,435],0),
('S06-B02',[754,466],90),('S06-B05',[754,487],0),('S04-B04',[754,511],90),('S02-B03',[682,528],0),('S04-B05',[718,529],180)]:add('NT_WEST_COURT',*row)
for row in [
('S04-B01',[850,444],-90),('S02-B03',[850,470],90),('S04-B06',[850,490],-90),('S06-B04',[850,510],180),('S04-B08',[850,532],-90),
('S06-B03',[914,446],0),('S06-B05',[923,471],0),('S02-B02',[918,498],90),('S06-B06',[913,527],0),('S04-B04',[901,553],180)]:add('NT_EAST_COURT',*row)
for row in [('S03-B03',[777,841],0),('S03-B05',[739,824],-90),('S03-B02',[790,787],0),('S03-B04',[801,755],0),('S04-B02',[775,868],0),('S04-B07',[729,731],0)]:add('NT_MIXED_PROMENADE',*row)
for row in [
('S02-B05',[-1158,-920],0,1),('S02-B05',[-1131,-920],0,1),('S02-B03',[-1097,-918],0,.68),('S02-B04',[-1052,-922],90,.65),
('S02-B05',[-1145,-960],180,1),('S02-B05',[-1108,-963],180,1),('S04-B04',[-1052,-963],90,.6),
('S04-B08',[-1091,-1003],0,.8),('S04-B10',[-1053,-1004],0,.8)]:add('WEST_GARDEN_LANES',*row)
for row in [('S04-B09',[860,-839],0,.9),('S04-B09',[939,-896],0,.9),('S04-B05',[939,-837],-90,.9),('S04-B02',[855,-892],0,.9)]:add('EAST_LOADING_COURT',*row)
def region(group):return 'WEST' if group.startswith('WEST') else 'EAST' if group.startswith('EAST') else 'MAIN'
def district(r,xy):
 if r=='MAIN':return 4 if xy[1]<620 else 8
 if r=='WEST':return 9
 return 14
placements=[]
for row in rows:
 a=catalog[row['asset_id']];r=region(row['group']);w,d,h=np.array(a['normalized_size_m'])*row['scale'];ang=math.radians(row['rotation_deg']);u=np.array([math.cos(ang),math.sin(ang)]);v=np.array([-u[1],u[0]]);delta=np.array([u*-w/2+v*-d/2,u*w/2+v*-d/2,u*w/2+v*d/2,u*-w/2+v*d/2]);c0=np.array(row['initial_center']);opts=[]
 # Initial anchors carry the layout intent; adjustments only resolve real geometry conflicts.
 for radius in [0,2,4,6,8,10,12,16,20,26]:
  offsets=[(0,0)] if radius==0 else [(radius*math.cos(t),radius*math.sin(t)) for t in np.linspace(0,2*math.pi,24,endpoint=False)]
  for off in offsets:
   c=c0+off;poly=Polygon(delta+c)
   if not lands[r].buffer(-.1).covers(poly) or poly.intersection(roads).area>.001 or poly.intersection(fixedpoly.buffer(.3)).area>.001 or poly.intersection(reserve).area>.001:continue
   if any(poly.distance(Polygon(b['footprint_xy']))<2.2 for b in placements):continue
   opts.append((np.linalg.norm(c-c0),c,poly))
  if opts:break
 assert opts,('no collision-free building anchor',row)
 _,c,poly=min(opts,key=lambda x:x[0]);aid=row['asset_id'];index=1+sum(b['asset_id']==aid for b in placements);name=f'{aid}-I{index:02}';front_local=np.array([0,-1])
 if aid in ['S02-B03','S02-B05']:front_local=-front_local
 # Source world axes have been retained; these front normals are verified from source previews.
 if aid in ['S06-B04','S06-B05','S06-B06']:front_local=np.array([1,0])
 frontvec=np.column_stack([u,v])@front_local
 rec={**row,'instance_id':name,'name':name,'display_name_zh':a['display_name_zh'],'source_filename':a['source_filename'],'source_node_name':a['source_node_name'],'file':a['file'],'source_sha256':a['source_sha256'],'asset_sha256':a['sha256'],'center':c.tolist(),'footprint_xy':list(poly.exterior.coords),'height':float(h),'region':r,'zone':'NEW_TOWN' if r=='MAIN' else 'VILLA' if r=='WEST' else 'INDUSTRIAL','district_id':district(r,c),'outward':frontvec.tolist(),'building_count_units':1,'added_in_version':'v19','replaces':[]}
 placements.append(rec)
# One-to-one attribution where possible; all removed lots also belong to a named redevelopment group.
for group,blockids in [('NT_WEST_COURT',[89]),('NT_EAST_COURT',[94]),('WEST_GARDEN_LANES',[13]),('EAST_LOADING_COURT',[])]:
 old=[b for b in removed if (b['region']=='EAST' if group.startswith('EAST') else b['block_id'] in blockids)];new=[b for b in placements if b['group']==group];cost=np.array([[np.linalg.norm(np.array(a['center'])-b['center']) for b in new] for a in old]);ix,jx=linear_sum_assignment(cost)
 for i,j in zip(ix,jx):new[j]['replaces'].append(old[i]['name'])
 for i in set(range(len(old)))-set(ix):new[int(cost[i].argmin())]['replaces'].append(old[i]['name'])
for b in placements:
 if b['group']=='NT_MIXED_PROMENADE':b['replaces']=[]
groups=[{'id':'NT_WEST_COURT','name_zh':'西侧围合商住街坊','strategy':'南侧连续商街、西侧亚洲沿街楼、东侧较高公寓，中央留共享庭院','focus':[705,482],'court':[[662,456],[735,456],[735,512],[662,512]],'region':'MAIN'},
 {'id':'NT_EAST_COURT','name_zh':'东侧错落住宅街坊','strategy':'街角较高、内侧较低，缩减两栋体块，留出中央口袋花园','focus':[884,485],'court':[[868,459],[903,459],[903,535],[868,535]],'region':'MAIN'},
 {'id':'NT_MIXED_PROMENADE','name_zh':'弧线商务步行组团','strategy':'沿既有弯路布置不同高度的商务楼与板式公寓，配开放步行广场','focus':[761,815],'court':[[719,801],[767,802],[781,818],[751,849],[716,850]],'region':'MAIN'},
 {'id':'WEST_GARDEN_LANES','name_zh':'西岛花园巷','strategy':'坡顶住宅围绕共享绿院，低层店铺位于巷口，形成细尺度生活街区','focus':[-1112,-945],'court':[[-1166,-941],[-1066,-941],[-1066,-950],[-1166,-950]],'region':'WEST'},
 {'id':'EAST_LOADING_COURT','name_zh':'东岛厂房装卸院','strategy':'厂房、办公室、服务楼围绕开放装卸场，打破相同大盒子排列','focus':[902,-865],'court':[[884,-879],[928,-879],[928,-856],[884,-856]],'region':'EAST'}]
out={'version':'v19','baseline_commit':'6a69d2b7d79dbc7d35570fd13cc96216e7472fad','changed_district_ids':[4,8,9,14],'removed_placeholder_lots':removed,'placements':placements,'groups':groups,'city_building_units':p['stats']['buildings']-len(removed)+len(placements)}
(R/'layout.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('PLANNED',len(removed),'removed',len(placements),'added',out['city_building_units'],'total');print('asset types',len({b['asset_id'] for b in placements}));print('moved',[(b['name'],round(np.linalg.norm(np.array(b['center'])-b['initial_center']),1)) for b in placements if np.linalg.norm(np.array(b['center'])-b['initial_center'])>.01])
