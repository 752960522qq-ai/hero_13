import bpy,sys,os,json,hashlib,math,collections
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,os.environ.get('HERO13_CITY_DEPS',str(R.parent/'tools_runtime/blender_deps')));sys.path.insert(0,str(R/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v17.blend'));bpy.context.view_layer.update();sc=bpy.context.scene
p=json.load(open(R/'model/city_plan.json'));old=json.load(open(R/'baseline/city_plan.json'));report=json.load(open(R/'model/build_report.json'));sites=json.load(open(R/'model/site_levels.json'));failures=[];checks=[]
def check(name,passed,detail=None):
 checks.append({'check':name,'passed':bool(passed),'detail':detail})
 if not passed:failures.append(name)
def fingerprint(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in o.data.vertices],dtype='<f4').tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in o.data.uv_layers:h.update(np.array([x.uv[:] for x in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()
check('global_and_zone_counts',p['stats']['buildings']==541 and p['stats']['building_count_by_zone']['OLDTOWN']==200 and len(p['buildings'])+len(p['real_buildings'])==541,p['stats']['building_count_by_zone'])
rear=[r for r in p['real_buildings'] if r['instance_name'].startswith(('OLDTOWN_Rear_','OLDTOWN_Infill_','OLDTOWN_Backlane_'))];street=[b for b in p['buildings'] if b['zone']=='OLDTOWN']+[r for r in p['real_buildings'] if r['instance_name'].startswith('OLDTOWN') and r not in rear]
check('oldtown_street_cap_includes_all_source_buildings',len(street)<=120,{'actual':len(street),'limit':120,'rear':len(rear)})
check('arcade_pool_cap_and_all_types_used',len(p['arcade_asset_pool'])==10 and all(r['instance_count']<=3 and r['replacements_this_version']>=2 for r in p['arcade_asset_pool']),{r['key']:r['instance_count'] for r in p['arcade_asset_pool']})
check('oldtown_envelope_reduced',p['urban_areas_v17']['oldtown']['street_envelope_after_m2']<p['urban_areas_v17']['oldtown']['street_envelope_before_m2'],p['urban_areas_v17']['oldtown'])
for k in ['coasts','lake','nodes','edges','interchanges','grade_separated_crossings','pedestrian_alleys','cbd_plan']:
 check('unchanged_'+k,p[k]==old[k])
check('municipal_campus_unchanged',p['urban_areas_v14']['municipal_campus']==old['urban_areas_v14']['municipal_campus'])
hash_fail=[]
for name,h in report['unchanged_original_objects'].items():
 o=sc.objects.get(name)
 if not o or fingerprint(o)!=h:hash_fail.append(name)
check('untouched_original_geometry_uv_and_transforms',not hash_fail,{'checked':len(report['unchanged_original_objects']),'failures':hash_fail})
land=Polygon(p['coasts']['MAIN']);reserve=Polygon(p['cbd_plan']['tianming']['polygon']);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.005,join_style=2) for e in p['edges']]);carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.005,join_style=2) for e in p['edges']]);allrecords=p['buildings']+p['real_buildings'];polys=[Polygon(r.get('footprint',r.get('footprint_xy'))) for r in allrecords];names=[r.get('name',r.get('instance_name')) for r in allrecords];tree=shapely.STRtree(polys);newnames={r['name'] for r in sites};collisions=[];surface_fail=[];source_fail=[];level_records=[]
field=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk']]);roadfield=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
for rec in sites:
 name=rec['name'];poly=Polygon(rec['poly']);errs=[]
 if not land.covers(poly):errs.append('outside_land')
 if poly.intersection(roads).area>.03:errs.append('road_overlap')
 if poly.intersection(reserve).area>.001:errs.append('tianming_overlap')
 for i in tree.query(poly.buffer(.01)):
  if names[i]!=name and poly.intersection(polys[i]).area>.02:errs.append('building_overlap:'+names[i])
 if errs:collisions.append({'name':name,'errors':errs})
 q=shapely.segmentize(poly.buffer(.09,join_style=2).exterior,1.5);exposed=[x for x in q.coords if not any(names[i]!=name and polys[i].buffer(.40).covers(Point(x)) for i in tree.query(Point(x).buffer(.40)))];values=[field.height(x) for x in exposed];missing=sum(z is None for z in values);deltas=[z-(rec['floor']-.025) for z in values if z is not None];maxdev=max(map(abs,deltas),default=100);level_records.append({'name':name,'samples':len(values),'missing':missing,'maximum_perimeter_floor_error_m':maxdev,'floor':rec['floor']})
 if missing or maxdev>.045:surface_fail.append(level_records[-1])
 obs=[o for o in sc.objects if o.type=='MESH' and o.get('source_instance')==name]
 xyz=[]
 for o in obs:
  M=np.array(o.matrix_world);x=np.array([v.co[:] for v in o.data.vertices]);xyz.append(x@M[:3,:3].T+M[:3,3]);scale=np.array(o.matrix_world.to_scale())
  if not o.data.uv_layers or min(scale)<=0 or max(scale)-min(scale)>1e-5:source_fail.append({'name':name,'error':'UV, scale or mirror'})
 x=np.concatenate(xyz);height=float(np.ptp(x[:,2]));expected=rec['height']
 if abs(height-expected)>.004:source_fail.append({'name':name,'height':height,'expected':expected})
check('changed_buildings_land_roads_reserved_lot_and_neighbors',not collisions,collisions)
check('changed_buildings_perimeter_ground_continuity',not surface_fail,surface_fail)
check('source_heights_uvs_and_uniform_nonmirrored_scale',not source_fail,source_fail)
for key in [r['key'] for r in p['arcade_asset_pool']]:
 obs=[o for o in sc.objects if o.type=='MESH' and o.get('arcade_pool_key')==key];check('new_arcade_mesh_reuse_'+key,len({o.data.as_pointer() for o in obs})==1,{'new_instances':len(obs)})
apts=[r for r in p['real_buildings'] if r.get('zone')=='APARTMENT'];red=Polygon([[-217.5449,1097.3525],[-181.3376,1032.603],[-231.0944,954.7264],[-365.0859,949.2082],[-446.1819,977.8445],[-493.4033,1046.8410],[-409.6146,1115.3573],[-307.6763,1136.9970]])
check('all_apartments_inside_marked_destination',len(apts)==12 and all(red.buffer(2).covers(Polygon(r['footprint_xy'])) for r in apts),[{'name':r['instance_name'],'center':r['center']} for r in apts])
groups={g:[r for r in apts if r['asset_color_group']==g] for g in ['YELLOW_50','PINK_53','GRAY_54']};check('four_of_each_color_grouped',all(len(rs)==4 for rs in groups.values()) and max(r['center'][0] for r in groups['YELLOW_50'])<min(r['center'][0] for r in groups['PINK_53']) and max(r['center'][0] for r in groups['PINK_53'])<min(r['center'][0] for r in groups['GRAY_54']))
walk_checks=[]
for w in p['access_v17']:
 if w['name'].startswith('OLDTOWN_'):continue
 route=LineString(w['route']);zs=[field.height(q) for q in shapely.segmentize(route,1.).coords];bad=sum(z is None for z in zs);xy=np.array(shapely.segmentize(route,1.).coords);zz=np.array([z if z is not None else 0 for z in zs]);grades=np.abs(np.diff(zz))/np.maximum(np.linalg.norm(np.diff(xy,axis=0),axis=1),1e-6);maxgrade=float(grades.max(initial=0));walk_checks.append({'name':w['name'],'missing_samples':bad,'maximum_grade':maxgrade,'length_m':route.length,'carriage_overlap_m2':Polygon(w['polygon']).intersection(carriage).area})
check('apartment_walks_connected_and_clear_of_traffic',all(w['missing_samples']==0 and w['carriage_overlap_m2']<.015 for w in walk_checks),walk_checks)
check('apartment_walk_grade',all(w['maximum_grade']<=.18 for w in walk_checks),walk_checks)
foundation_overlaps=[]
for rec in sites:
 o=next(o for o in sc.objects if o.type=='MESH' and o.get('site_building')==rec['name']);o.data.calc_loop_triangles();xyz=np.array([v.co[:] for v in o.data.vertices]);top=xyz[:,2].max();area=0.
 for tri in o.data.loop_triangles:
  q=xyz[list(tri.vertices)]
  if np.ptp(q[:,2])<.0001 and abs(q[:,2].mean()-top)<.001:area+=Polygon(q[:,:2]).difference(Polygon(rec['poly']).buffer(.036,join_style=2)).area
 if area>.001:foundation_overlaps.append({'name':rec['name'],'top_outside_body_m2':area})
check('no_wide_foundation_rims',not foundation_overlaps,foundation_overlaps)
out={'status':'PASS' if not failures else 'FAIL','failures':failures,'checks':checks,'building_perimeter_levels':level_records,'apartment_walks':walk_checks,'changed_buildings_checked':len(sites),'original_geometry_objects_checked':len(report['unchanged_original_objects'])};(R/'validation').mkdir(exist_ok=True);(R/'validation/native_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(out['status'],failures,flush=True)
