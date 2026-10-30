from pathlib import Path
import sys,json,collections,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from city_surface_sampling import HeightField
from surface_utils import co,fingerprint
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v20.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));old=json.load(open(R/'baseline/city_plan.json'));layout=json.load(open(R/'layout.json'));sites=json.load(open(R/'model/site_levels.json'));report=json.load(open(R/'model/build_report.json'));props=json.load(open(R/'model/public_instances.json'));checks=[];fail=[]
def check(n,ok,detail=None):
 checks.append(dict(check=n,passed=bool(ok),detail=detail))
 if not ok:fail.append(n)
check('count_budget',p['stats']['buildings']==layout['city_building_units']==len(p['buildings'])+len(p['real_buildings'])<700,dict(total=p['stats']['buildings'],new=len(sites),removed=len(layout['removed_placeholder_lots'])))
for key in ['coasts','lake','interchanges','grade_separated_crossings','pedestrian_alleys','cbd_plan','arcade_asset_pool']:check('preserve_'+key,p[key]==old[key])
check('existing_real_buildings_preserved',all(b in p['real_buildings'] for b in old['real_buildings']))
check('oldtown_120_street_80_rear',p['stats']['building_count_by_zone']['OLDTOWN']==200 and [b for b in old['buildings'] if b['zone']=='OLDTOWN']==[b for b in p['buildings'] if b['zone']=='OLDTOWN'])
bad=[n for n,h in report['unchanged_original_objects'].items() if n not in sc.objects or fingerprint(sc.objects[n])!=h];check('unchanged_geometry_and_uv',not bad,dict(objects=len(report['unchanged_original_objects']),failures=bad))
allrecords=p['buildings']+p['real_buildings'];polys=[Polygon(b.get('footprint',b.get('footprint_xy'))) for b in allrecords];names=[b.get('name',b.get('instance_name')) for b in allrecords];tree=shapely.STRtree(polys);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in p['edges']]);car=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2,join_style=2) for e in p['edges']]);lands={k:Polygon(v) for k,v in p['coasts'].items()};reserve=Polygon(p['cbd_plan']['tianming']['polygon']);bad=[];propbad=[];sizebad=[];annotationbad=[];levels=[]
field=HeightField([o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['terrain','sidewalk','pavement','road_kit'] or o.get('is_site_foundation'))])
for s in sites:
 poly=Polygon(s['poly']);errors=[]
 if not lands[s['region']].covers(poly):errors.append('land')
 if poly.intersection(roads).area>.04:errors.append('road')
 if poly.intersection(reserve).area>.001:errors.append('reserved')
 for j in tree.query(poly.buffer(.01)):
  if names[j]!=s['name'] and poly.intersection(polys[j]).area>.015:errors.append('neighbor:'+names[j])
 if errors:bad.append(dict(name=s['name'],errors=errors))
 obs=[o for o in sc.objects if o.type=='MESH' and o.get('instance_id')==s['name']];xyz=np.concatenate([co(o) for o in obs]);err=abs(float(np.ptp(xyz[:,2]))-s['height']);floorerr=abs(xyz[:,2].min()-s['floor'])
 if err>.003 or floorerr>.003:sizebad.append(dict(name=s['name'],height_error=err,floor_error=floorerr))
 for o in obs:
  if not all(o.get(k) for k in ['asset_id','source_filename','source_node_name','source_mesh_name','layout_group']) or o.get('replaces_lots')!='|'.join(s['replaces']):annotationbad.append(o.name)
 zs=[field.height(q) for q in shapely.segmentize(poly.buffer(.1,join_style=2).exterior,2).coords];levels.append(dict(name=s['name'],samples=len(zs),missing=sum(z is None for z in zs),max_floor_error_m=max([abs(z-s['floor']+.02) for z in zs if z is not None],default=100)))
check('new_buildings_land_road_neighbor_reserve_clear',not bad,bad);check('source_proportions_and_ground_level',not sizebad,sizebad);check('all_source_parts_annotated',not annotationbad,annotationbad);check('foundation_perimeters_continuous',all(x['missing']==0 and x['max_floor_error_m']<.09 for x in levels),levels)
walks=[];walkbad=[]
for w in p['access_v20']:
 line=LineString(w['route']);shape=Polygon(w['polygon']);xy=np.array(shapely.segmentize(line,.5).coords);zz=[field.height(q) for q in xy];z=np.array([x if x is not None else 0 for x in zz]);grades=np.abs(np.diff(z))/np.maximum(np.linalg.norm(np.diff(xy,axis=0),axis=1),1e-8);cross=[name for name,poly in zip(names,polys) if line.intersection(poly.buffer(-.035)).length>.06];rec=dict(name=w['name'],length_m=line.length,missing=sum(q is None for q in zz),max_grade=float(grades.max(initial=0)),carriage_overlap_m2=shape.intersection(car).area,building_crossings=cross);walks.append(rec)
 if rec['missing'] or rec['max_grade']>.34 or rec['carriage_overlap_m2']>.04 or cross:walkbad.append(rec)
check('all_building_entrances_walkable',not walkbad,walkbad)
for q in props:
 if 'center' not in q:continue
 pt=Point(q['center']);rad={'tree':1.55,'shrub':1.1,'bench':.8,'bin':.27,'utility_pole':.15,'street_lamp':.15,'bollard':.085}[q['type']]
 if car.intersects(pt.buffer(rad)) or reserve.intersects(pt.buffer(rad)) or any(polys[int(j)].intersects(pt.buffer(rad)) for j in tree.query(pt.buffer(rad))):propbad.append(q['instance_id'])
check('public_furniture_does_not_obstruct_roads_or_buildings',not propbad,propbad)
wireclear=[]
for q in props:
 if q['type']!='overhead_cable':continue
 ob=next(o for o in sc.objects if o.get('public_instance_id')==q['instance_id']);xyz=co(ob)[::10];clearances=[]
 for v in xyz:
  h=field.height(v[:2])
  if h is not None:clearances.append(float(v[2]-h))
 wireclear.append(dict(instance_id=q['instance_id'],minimum_measured_ground_clearance_m=min(clearances,default=0)))
check('cables_clearance',bool(wireclear) and all(x['minimum_measured_ground_clearance_m']>=6.5 for x in wireclear),wireclear)
# Every graph segment and adjacency points to the actual road network.
adj={i:set() for i in range(len(p['nodes']))};nodebad=[]
for i,e in enumerate(p['edges']):
 adj[e['a']].add(e['b']);adj[e['b']].add(e['a'])
 for key,q in [('a',e['points'][0]),('b',e['points'][-1])]:
  n=p['nodes'][e[key]]
  if np.linalg.norm(np.asarray(n['xy'])-np.asarray(q[:2]))>.01 or i not in n['edges']:nodebad.append(i)
remaining={i for i,a in adj.items() if a};components=[]
while remaining:
 seen={next(iter(remaining))};todo=list(seen)
 while todo:
  for n in adj[todo.pop()]-seen:seen.add(n);todo.append(n)
 remaining-=seen;components.append(len(seen))
check('road_graph_connections_and_adjacency',not nodebad and len(components)==1,dict(components=components,bad_edges=sorted(set(nodebad))))
newroadchecks=[]
for name in [r['name'] for r in layout['new_roads']]:
 edges=[e for e in p['edges'] if e['name']==name];maxgrade=max(e['max_grade'] for e in edges);allxy=np.concatenate([np.array(shapely.segmentize(LineString(np.array(e['points'])[:,:2]),1.5).coords) for e in edges]);zz=[field.height(q) for q in allxy];z=np.array([x if x is not None else 0 for x in zz]);ds=np.linalg.norm(np.diff(allxy,axis=0),axis=1);actual=float((np.abs(np.diff(z))[ds>.05]/ds[ds>.05]).max(initial=0));rec=dict(name=name,segments=len(edges),length_m=sum(e['length'] for e in edges),max_design_grade=maxgrade,max_actual_surface_grade=actual,missing_surface_samples=sum(z is None for z in zz));newroadchecks.append(rec)
check('new_roads_have_surfaces_and_reasonable_grades',all(x['missing_surface_samples']==0 and x['max_design_grade']<=.14 and x['max_actual_surface_grade']<=.20 for x in newroadchecks),newroadchecks)
# Sample a band around each modified street and each new building for visible holes.
samplearea=unary_union([LineString(r['points']).buffer(r['width']/2+4) for r in layout['new_roads']]+[Polygon(s['poly']).buffer(3) for s in sites]);obstacles=unary_union(polys).buffer(.03);shapely.prepare(obstacles);missing=[];samples=0
for reg in ['MAIN','WEST']:
 area=samplearea.intersection(lands[reg]);x0,y0,x1,y1=area.bounds
 for x in np.arange(x0,x1,2):
  for y in np.arange(y0,y1,2):
   q=Point(x,y)
   if not area.covers(q) or obstacles.covers(q):continue
   samples+=1
   if field.height([x,y]) is None:missing.append([float(x),float(y)])
check('surface_coverage_modified_areas',not missing,dict(samples=samples,missing_samples=missing[:60],total_missing=len(missing)))
out=dict(status='PASS' if not fail else 'FAIL',failures=fail,checks=checks,site_levels=levels,walkways=walks,new_roads=newroadchecks,public_counts=report['public_counts'],city_buildings=p['stats']['buildings'],changed_districts=layout['changed_district_ids']);(R/'validation/native_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(out['status'],fail,flush=True)
if fail:print(json.dumps([x for x in checks if not x['passed']],ensure_ascii=False,indent=2),flush=True);raise SystemExit(1)
