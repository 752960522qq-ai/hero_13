import sys,json,hashlib,math,collections
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'));sys.path.insert(0,str(R/'tools'))
import bpy,numpy as np,shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from city_surface_sampling import HeightField
from surface_utils import co,fingerprint
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v19.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));old=json.load(open(R/'baseline/city_plan.json'));layout=json.load(open(R/'layout.json'));sites=json.load(open(R/'model/site_levels.json'));report=json.load(open(R/'model/build_report.json'));checks=[];fail=[]
def check(n,ok,detail=None):
 checks.append({'check':n,'passed':bool(ok),'detail':detail})
 if not ok:fail.append(n)
check('counts_and_budget',len(p['buildings'])+len(p['real_buildings'])==547 and p['stats']['buildings']==547<700 and len(sites)==41 and len(report['removed_placeholders'])==37)
for k in ['coasts','lake','nodes','edges','interchanges','grade_separated_crossings','pedestrian_alleys','cbd_plan','arcade_asset_pool']:check('unchanged_'+k,p[k]==old[k])
check('existing_real_buildings_preserved',all(r in p['real_buildings'] for r in old['real_buildings']))
check('oldtown_unchanged',p['stats']['building_count_by_zone']['OLDTOWN']==200 and [b for b in old['buildings'] if b['zone']=='OLDTOWN']==[b for b in p['buildings'] if b['zone']=='OLDTOWN'])
check('oldtown_street_cap',report['oldtown_street_buildings']==120 and report['oldtown_rear_buildings']==80)
fpbad=[]
for n,h in report['unchanged_original_objects'].items():
 if n not in sc.objects or fingerprint(sc.objects[n])!=h:fpbad.append(n)
check('untouched_geometry_and_uv_fingerprints',not fpbad,{'objects':len(report['unchanged_original_objects']),'failures':fpbad})
allrecs=p['buildings']+p['real_buildings'];polys=[Polygon(b.get('footprint',b.get('footprint_xy'))) for b in allrecs];names=[b.get('name',b.get('instance_name')) for b in allrecs];tree=shapely.STRtree(polys);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.005,join_style=2) for e in p['edges']]);carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.005,join_style=2) for e in p['edges']]);lands={k:Polygon(v) for k,v in p['coasts'].items()};reserve=Polygon(p['cbd_plan']['tianming']['polygon']);geometrybad=[];annotationbad=[];levels=[];sourcebad=[];field=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk']])
for rec in sites:
 poly=Polygon(rec['poly']);n=rec['name'];errs=[]
 if not lands[rec['region']].covers(poly):errs.append('land')
 if poly.intersection(roads).area>.015:errs.append('road')
 if poly.intersection(reserve).area>.001:errs.append('reserve')
 for j in tree.query(poly.buffer(.01)):
  if names[j]!=n and poly.intersection(polys[j]).area>.015:errs.append('neighbor:'+names[j])
 if errs:geometrybad.append({'name':n,'errors':errs})
 obs=[o for o in sc.objects if o.type=='MESH' and o.get('instance_id')==n];xyz=np.concatenate([co(o) for o in obs]);height=float(np.ptp(xyz[:,2]));lo=xyz[:,:2].min(0);hi=xyz[:,:2].max(0);bounds=poly.bounds
 if abs(height-rec['height'])>.002 or np.max(np.abs(np.r_[lo,hi]-bounds))>.003:sourcebad.append({'name':n,'height':height,'expected':rec['height'],'bounds_error':float(np.max(np.abs(np.r_[lo,hi]-bounds)))})
 for o in obs:
  if o.get('asset_id')!=rec['asset_id'] or o.get('source_filename')!=rec['source_filename'] or not o.get('source_mesh_name') or o.get('replaces_lots')!='|'.join(rec['replaces']):annotationbad.append(o.name)
 q=shapely.segmentize(poly.buffer(.08,join_style=2).exterior,2);zz=[field.height(x) for x in q.coords];deviation=max([abs(z-(rec['floor']-.025)) for z in zz if z is not None],default=100);levels.append({'instance_id':n,'samples':len(zz),'missing':sum(z is None for z in zz),'maximum_floor_error_m':deviation})
check('land_roads_neighbors_and_reserved_lot_clear',not geometrybad,geometrybad)
check('proportions_heights_and_footprints',not sourcebad,sourcebad)
check('every_source_mesh_marked',not annotationbad,annotationbad)
check('foundation_perimeter_ground_continuity',all(x['missing']==0 and x['maximum_floor_error_m']<.075 for x in levels),levels)
walkfield=HeightField([o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['terrain','sidewalk'] or o.get('is_site_foundation'))]);walks=[];walkbad=[]
for w in p['access_v19']:
 line=LineString(w['route']);poly=Polygon(w['polygon']);s=next(s for s in sites if s['name']==w['building']);points=np.array(shapely.segmentize(line,.75).coords);zz=[walkfield.height(q) for q in points];z=np.array([x if x is not None else 0 for x in zz]);grades=np.abs(np.diff(z))/np.maximum(np.linalg.norm(np.diff(points,axis=0),axis=1),1e-9);over=[]
 for b,q in zip(names,polys):
  if line.intersection(q.buffer(-.03)).length>.06:over.append(b)
 detail={'name':w['name'],'length_m':line.length,'missing_samples':sum(x is None for x in zz),'maximum_surface_grade':float(grades.max(initial=0)),'carriage_overlap_m2':poly.intersection(carriage).area,'building_crossings':over};walks.append(detail)
 if detail['missing_samples'] or detail['maximum_surface_grade']>.32 or detail['carriage_overlap_m2']>.03 or over:walkbad.append(detail)
check('all_entrances_reach_public_walkways_without_crossing_buildings',not walkbad,walkbad)
check('all_used_assets_unique_and_traceable',len({s['asset_id'] for s in sites})==24 and len({s['instance_id'] for s in sites})==41)
for x in report['removed_placeholders']:check('removed_'+x,not any(b['name']==x for b in p['buildings']))
coverage=json.load(open(R/'validation/surface_coverage_validation.json'));check('no_visible_surface_voids_in_modified_sites',coverage['status']=='PASS' and not coverage['remaining_large_holes_m2'],coverage)
out={'status':'PASS' if not fail else 'FAIL','failures':fail,'checks':checks,'site_levels':levels,'walkways':walks,'changed_districts':layout['changed_district_ids'],'city_buildings':547,'new_instances':41,'new_types_used':24};(R/'validation').mkdir(exist_ok=True);(R/'validation/native_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(out['status'],fail,flush=True)
if fail:print(json.dumps([c for c in checks if not c['passed']],ensure_ascii=False,indent=2),flush=True)

if fail:raise SystemExit(1)
