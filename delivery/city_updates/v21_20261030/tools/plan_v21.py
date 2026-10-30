"""Place newly mined source buildings along existing connected streets."""
from pathlib import Path
import sys,json,math,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'))
import numpy as np,shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
p=json.load(open(R/'baseline/city_plan.json'));cat={a['asset_id']:a for a in json.load(open(R/'asset_catalog.json'))}
removed=[b for b in p['buildings'] if b['region']=='WEST' and b.get('block_id') in [9,20]];rn={b['name'] for b in removed};fixed=[b for b in p['buildings'] if b['name'] not in rn]+p['real_buildings'];fixedpolys=[Polygon(b.get('footprint',b.get('footprint_xy'))) for b in fixed];fixedshape=unary_union(fixedpolys);lands={k:Polygon(v) for k,v in p['coasts'].items()};reserve=Polygon(p['cbd_plan']['tianming']['polygon']);nt=p['urban_areas_v18']['new_town'];green=unary_union([Polygon(a['polygon']) for a in nt['land_use_parcels'] if a['role']=='green_buffer']);ntshape=Polygon(nt['polygon']).difference(green.buffer(.4));westshape=unary_union([box(-1241,-854,-1040,-725),box(-794,-854,-626,-725)])
roadshape=unary_union([LineString(np.asarray(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in p['edges']]);props=json.load(open(R.parent/'work_v20/model/public_instances.json'));prop_shapes=[Point(a['center']).buffer(1.5 if a['type']=='tree' else .7) for a in props if 'center' in a];prop_shape=unary_union(prop_shapes)
edges=[e for e in p['edges'] if not e.get('bridge') and not e['layer'].startswith('ELEV') and 'RAMP' not in e['name'] and e['region'] in ['MAIN','WEST']];roads=[dict(e=e,line=LineString(np.asarray(e['points'])[:,:2])) for e in edges]
candidates=[]
for r in roads:
 line=r['line'];e=r['e']
 for s in np.arange(9,line.length-8,4.5):
  q=np.asarray(line.interpolate(s).coords[0]);t=np.asarray(line.interpolate(s+.5).coords[0])-np.asarray(line.interpolate(s-.5).coords[0]);t/=np.linalg.norm(t)
  for side in [-1,1]:candidates.append(dict(region=e['region'],street=e['name'],station=float(s),q=q,t=t,n=np.array([-t[1],t[0]])*side,width=e['width'],carriage=e['carriage_width'],sidewalk=e['sidewalk_width']))
placements=[];rejections=[]
candidates=[c for c in candidates if (ntshape if c['region']=='MAIN' else westshape).buffer(40).covers(Point(c['q']))]
fixedbuffer=fixedshape.buffer(.65)
def district(q):return (9 if q[0]<-950 else 10) if q[0]<-430 and q[1]<-300 else (4 if q[1]<620 else 8)
def choices(aid,reg,round_no):
 a=cat[aid];sf=np.array(a['source_front'])
 out=[]
 if reg=='MAIN':
  focus=np.array([867,738]) if aid.startswith('S05') else np.array([690,880]) if aid.startswith('S08') else np.array([865,485]) if aid.startswith('S09') else np.array([695,488])
 else:focus=np.array([-1163,-795]) if round_no==0 else np.array([-719,-795])
 if reg=='MAIN' and round_no:focus[1]=520 if focus[1]>650 else 810
 ranked=sorted([c for c in candidates if c['region']==reg],key=lambda c:float(np.linalg.norm(c['q']-focus)))
 others=unary_union([Polygon(b['footprint_xy']).buffer(.3) for b in placements])
 for scale in [1.,.93,.86]:
  for c in ranked:
   if c['region']!=reg:continue
   normal=-c['n'];angle=math.atan2(normal[1],normal[0])-math.atan2(sf[1],sf[0]);rot=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]]);w,d,h=np.asarray(a['placement_size_m'])*scale;depth=d if sf[1] else w
   setback=.85 if aid.startswith(('S07','S08')) else 1.45 if aid.startswith('S05') else .8
   center=c['q']+c['n']*(c['width']/2+depth/2+setback);allowed=ntshape if reg=='MAIN' else westshape
   if not allowed.covers(Point(center)):continue
   corners=np.array([[-w/2,-d/2],[w/2,-d/2],[w/2,d/2],[-w/2,d/2]])@rot.T+center;poly=Polygon(corners)
   if not allowed.buffer(.05).covers(poly) or not lands[reg].buffer(-.2).covers(poly):continue
   if poly.distance(roadshape)<.5 or poly.intersects(fixedbuffer) or poly.intersects(reserve) or poly.intersects(prop_shape):continue
   if any(poly.distance(Polygon(b['footprint_xy']))<2.0 for b in placements):continue
   front=center+normal*depth/2;goal=c['q']+c['n']*(c['carriage']/2+c['sidewalk']*.55);route=LineString([front,goal]);band=route.buffer(.65,cap_style=2)
   if band.intersects(fixedshape.buffer(.3)) or band.intersects(others) or band.intersects(prop_shape):continue
   # Vary locations across the neighborhood; tall shells sit behind the lower street faces.
   score=np.linalg.norm(center-focus)+(1-scale)*200
   # Slightly stagger repeated units along different road segments.
   score+=sum(80*math.exp(-Point(center).distance(Point(b['center']))/65) for b in placements if b['asset_id']==aid)
   return [(score,dict(a=a,scale=scale,center=center,normal=normal,angle=angle,poly=poly,c=c,route=route,height=h,front=front,goal=goal))]
 return sorted(out,key=lambda q:q[0])
requests=[]
for aid in cat:
 if aid.startswith(('S05','S08')) or aid in ['S09-B05','S09-B06']:
  requests.append((aid,'MAIN',0))
 elif aid.startswith('S07'):requests.append((aid,'WEST',1))
 else:requests.append((aid,'WEST',0))
# Reserve space for the larger footprints first.
requests.sort(key=lambda q:-(np.prod(cat[q[0]]['placement_size_m'][:2])))
for aid,reg,round_no in requests:
 opts=choices(aid,reg,round_no)
 if not opts:rejections.append(dict(asset_id=aid,region=reg,round=round_no));continue
 score,o=opts[0];a=o['a'];ix=1+sum(b.get('asset_id')==aid for b in p['real_buildings']+placements);iid=f'{aid}-I{ix:02}';c=o['c'];group='NT_SOURCE_SKYLINE' if reg=='MAIN' and aid.startswith('S05') else 'NT_CONSTRUCTION_COURTS' if reg=='MAIN' and aid.startswith('S08') else 'NT_MIXED_STREET' if reg=='MAIN' else 'WEST_SOURCE_COURTS'
 rec=dict(name=iid,instance_id=iid,instance_name=iid,asset_id=aid,display_name_zh=a['display_name_zh'],file=a['file'],source_id=a['source_id'],source_filename=a['source_filename'],source_node_name=a['source_node_name'],source_sha256=a['source_sha256'],asset_sha256=a['sha256'],geometry_status=a['geometry_status'],issue_note_zh=a['issue_note_zh'],low_resolution_texture=a['low_resolution_texture'],center=o['center'].tolist(),rotation_deg=math.degrees(o['angle']),scale=o['scale'],uniform_scale=o['scale'],height=float(o['height']),footprint_xy=list(o['poly'].exterior.coords),front=o['front'].tolist(),outward=o['normal'].tolist(),entrance_route=list(o['route'].coords),street=c['street'],region=reg,zone='NEW_TOWN' if reg=='MAIN' else 'VILLAGE',district_id=district(o['center']),group=group,layout_group=group,building_count_units=1,added_in_version='v21',replaces=[]);placements.append(rec);print('PLACE',iid,reg,[round(x,1) for x in rec['center']],flush=True)
assert len({b['asset_id'] for b in placements})==len(cat),('some new types unplaced',rejections)
assert all(n==1 for n in collections.Counter(b['asset_id'] for b in placements).values()),'Newly extracted models must appear once only.'
# Preserve every old placeholder that still fits beside the new geometry and entrances.
new_occupied=unary_union([Polygon(b['footprint_xy']).buffer(1.2) for b in placements]+[LineString(b['entrance_route']).buffer(.9) for b in placements])
removed=[b for b in removed if Polygon(b['footprint']).intersects(new_occupied)]
for old in removed:
 candidates_w=[b for b in placements if b['region']=='WEST'];new=min(candidates_w,key=lambda b:Point(b['center']).distance(Point(old['center'])));new['replaces'].append(old['name'])
out=dict(version='v21',baseline_version='v20',baseline_commit='61949bcf57384efdf237fc3169f72a3bbf40042b',changed_district_ids=sorted({b['district_id'] for b in placements}),new_roads=[],placements=placements,removed_placeholder_lots=removed,rejected_requests=rejections,city_building_units=p['stats']['buildings']-len(removed)+len(placements),maximum_instances_per_new_asset=1,groups=[dict(id='NT_SOURCE_SKYLINE',name_zh='新城多样楼群',region='MAIN'),dict(id='NT_CONSTRUCTION_COURTS',name_zh='新城街坊与施工楼',region='MAIN'),dict(id='NT_MIXED_STREET',name_zh='新城混合街面',region='MAIN'),dict(id='WEST_SOURCE_COURTS',name_zh='西岛异形街坊',region='WEST')],policy='Each newly extracted model is used exactly once. Open backs, missing roofs and facade shells are allowed and marked. No caps were created.')
(R/'layout.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('LAYOUT_DONE',len(placements),len(removed),out['city_building_units'],out['changed_district_ids'],collections.Counter(b['source_id'] for b in placements),flush=True)
