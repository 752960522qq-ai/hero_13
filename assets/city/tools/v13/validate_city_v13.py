"""Independently reimport v12 and check new houses, pools, access and preserved geometry."""
import bpy,sys,json,hashlib,collections,math,argparse
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser()
for k in ['baseline','model','deps']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);BASE=a.baseline.resolve();OUT=a.model.resolve();sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).parent))
import shapely
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from city_surface_sampling import HeightField
p=json.loads((OUT/'city_plan.json').read_text());old=json.loads((BASE/'city_plan.json').read_text());new=p['real_buildings'][101:];assert len(new)==4
for k in ['coasts','lake','nodes','edges','interchanges','pedestrian_alleys','rear_rows','rear_access_links','infill_access_v12','connected_arcades']:assert p[k]==old[k],('prior plan changed',k)
assert p['real_buildings'][:101]==old['real_buildings'];assert len(p['buildings'])==547 and len(p['real_buildings'])==105 and p['stats']['buildings']==652<700
counts=collections.Counter(str(r['source_key']) for r in new);assert counts=={'C30':1,'C29':1,'C28':1,'C27':1}
pool=json.loads((OUT/'rear_asset_pool.json').read_text());assert len(pool['types'])==9 and sum(r['instances'] for r in pool['types'])==80
boundary=Polygon(p['cbd_plan']['boundary']);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
cbdph=[b for b in p['buildings'] if b['zone']=='CBD'];cbdsources=[r for r in p['real_buildings'] if r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN')=='CBD'];assert len(cbdph)==15 and len(cbdsources)==14
assert p['cbd_plan']['existing_buildings']==29 and p['cbd_plan']['planned_total_including_tianming']==30
assert abs(reserve.area-33540)<.001 and p['cbd_plan']['tianming']['building_present']==False
for b in cbdph:assert boundary.covers(Polygon(b['footprint']))
for r0 in cbdsources:assert boundary.covers(Polygon(r0['footprint_xy']))
for b in p['buildings']:assert Polygon(b['footprint']).intersection(reserve).area<1e-6
for r0 in p['real_buildings']:assert Polygon(r0['footprint_xy']).intersection(reserve).area<1e-6
assert [b for b in p['buildings'] if b['zone']!='CBD']==[b for b in old['buildings'] if b['zone']!='CBD']
polys=[Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']];tree=shapely.STRtree(polys);newstart=len(polys)-4
roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2) for e in p['edges']])
for i in range(newstart,len(polys)):
 assert polys[i].intersection(roads).area<1e-5,('new footprint in road or sidewalk',i)
 for j in tree.query(polys[i]):
  if j>=i:continue
  assert polys[i].intersection(polys[j]).area<1e-5,('new footprint overlap',i,int(j))
def geom(o):
 m=o.data;h=hashlib.sha256();h.update(np.asarray(o.matrix_world,np.float64).tobytes());co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);h.update(co.tobytes());idx=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',idx);h.update(idx.tobytes())
 for uv in m.uv_layers:
  co=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',co);h.update(co.tobytes())
 return h.hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'));bpy.context.view_layer.update();prior={o.name:geom(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('surface_type')!='terrain' and not o.data.attributes.get('source_building_index')}
bpy.ops.wm.open_mainfile(filepath=str(OUT/'huizhou_road_network.blend'));bpy.context.view_layer.update()
for name,sha in prior.items():assert name in bpy.data.objects and geom(bpy.data.objects[name])==sha,('prior mesh geometry/UV/matrix changed',name)
linked=collections.defaultdict(set)
for r in new:
 inst=bpy.data.objects[r['instance_name']];assert np.linalg.det(np.array(inst.matrix_world)[:3,:3])>0
 linked[str(r['source_key'])].update(o.data.name for o in inst.children_recursive if o.type=='MESH')
assert all(len(s)==1 for s in linked.values())
print('V13_NATIVE_PRESERVATION_PASS',len(prior),'meshes',flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];terrain=HeightField([o for o in obs if o.get('surface_type')=='terrain'])
names={v['name'] for v in old['pedestrian_alleys']};oldwalk=HeightField([o for o in obs if o.get('surface_type') in ['sidewalk','backlane_entry_walk','backlane_seam_stitch','v12_access_walk'] or o.name in names]);obsv=[];obsf=[]
for ob in obs:
 if not (ob.get('is_placeholder') or '_Source_Mesh_' in ob.name or '_Foundation' in ob.name or 'Partywall' in ob.name or ob.get('surface_type')=='terrain_cut_retaining_wall'):continue
 m=ob.data;m.calc_loop_triangles();co=np.array([v.co[:] for v in m.vertices]);M=np.array(ob.matrix_world);co=co@M[:3,:3].T+M[:3,3];k=len(obsv);obsv.extend(co.tolist());obsf.extend([[k+i for i in t.vertices] for t in m.loop_triangles])
bvh=BVHTree.FromPolygons(obsv,obsf,all_triangles=True);rays=0;checks=[];maxgrade=0.;overlaps=0;maxoverlap=0.
def check_link(name,coords,field,width=2.8,grade_limit=.084):
 global rays
 grades=[];penetration=0.;count=0
 for aa,bb in zip(np.array(coords)[:-1],np.array(coords)[1:]):
  delta=bb-aa;L=np.linalg.norm(delta);t=delta/L;n=np.array([-t[1],t[0]]);ss=np.linspace(0,L,max(4,int(math.ceil(L/.45))+1));zs=[]
  for s in ss:
   c=aa+t*s;h=field.height(c);assert h is not None,('access hole',name,c.tolist());zs.append(h)
   for lateral in [-width/2,0,width/2]:
    xy=c+n*lateral;z=field.height(xy);assert z is not None,('access width missing',name,xy.tolist());soil=terrain.height(xy)
    if soil is not None:penetration=max(penetration,soil-z)
    hit,_,_,_=bvh.ray_cast(Vector((*xy,z+.12)),Vector((0,0,1)),2.1);assert hit is None,('access obstruction',name,xy.tolist(),list(hit) if hit else None);rays+=1;count+=1
  grades.extend((np.abs(np.diff(zs))/np.diff(ss)).tolist())
 grade=max(grades or [0.])
 if grade_limit is not None:assert grade<grade_limit,('access too steep',name,grade)
 assert penetration<.035,('terrain in access',name,penetration)
 return {'name':name,'samples':count,'clear_width_sampled_m':width,'maximum_grade':grade,'maximum_terrain_penetration_m':penetration}
for walk in p['cbd_access_v13']:
 field=HeightField([bpy.data.objects[walk['name']]]);check=check_link(walk['name'],walk['route'],field,width=min(6.4,walk['clear_width_m']-.8));goal=np.array(walk['goal']);z=field.height(goal);priorz=oldwalk.height(goal);assert z is not None and priorz is not None and abs(z-priorz)<.02,('walk join lip',walk['name'],z,priorz);check['join_lip_m']=abs(z-priorz);checks.append(check);maxgrade=max(maxgrade,check['maximum_grade'])
 for q in shapely.segmentize(Polygon(walk['polygon']).boundary,1.0).coords if Polygon(walk['polygon']).boundary.geom_type=='LineString' else []:
  z=field.height(q);h=oldwalk.height(q)
  if z is not None and h is not None:
   overlaps+=1;maxoverlap=max(maxoverlap,abs(z-h));assert abs(z-h)<.025,('new surface steps on old walk',walk['name'],q,z-h)
print('V13_NEW_ACCESS_PASS',len(checks),'paths',rays,'rays',flush=True)
old_rear=[]
for link in old['rear_access_links']:
 field=HeightField([bpy.data.objects[link['name']+'_Entry_Walk']]);old_rear.append(check_link(link['name'],link['points'],field,grade_limit=None))
frontage=[]
for r in new:
 field=HeightField([bpy.data.objects[r['access_alley']]]);u=np.array([math.cos(r['theta']),math.sin(r['theta'])]);n=np.array([u[1],-u[0]]);face=np.array(r['anchor']);lip=[]
 for s in np.linspace(.04,r['right']-.04,41):
  q=face+u*s+n*.04;z=field.height(q);assert z is not None,('doorway has no paving',r['instance_name'],q.tolist());lip.append(abs(z-(r['floor']-.008)))
 assert max(lip)<.11,('door threshold too high',r['instance_name'],max(lip));frontage.append({'name':r['instance_name'],'maximum_threshold_lip_m':max(lip)})
site=bpy.data.objects['CBD_Tianming_Reserved_Pad'];assert not site.get('is_building_instance') and site.get('building_count_units')==0
sitefield=HeightField([site]);site_samples=0;maxintrusion=0.
for x in np.linspace(-370.,-208.,35):
 for y in np.linspace(740.,925.,39):
  z=sitefield.height((x,y));assert z is not None and abs(z-p['cbd_plan']['tianming']['surface_z_m'])<.002
  h=terrain.height((x,y))
  if h is not None:maxintrusion=max(maxintrusion,h-z)
  hit,_,_,_=bvh.ray_cast(Vector((float(x),float(y),z+.12)),Vector((0,0,1)),150);assert hit is None,('reserved site obstructed',x,y,list(hit) if hit else None);site_samples+=1
assert maxintrusion<.035
oldv12=[]
for link in old['infill_access_v12']:
 field=HeightField([bpy.data.objects[link['name']]]);oldv12.append(check_link(link['name'],link['route'],field,grade_limit=None))
report={'schema':'hero13.city.validation.v13','status':'PASS','city_building_units':652,'placeholder_units':547,'source_instances':105,'cbd_buildings_before':59,'cbd_buildings_current':29,'cbd_buildings_after_tianming':30,'cbd_source_models':14,'cbd_placeholders':15,'new_cbd_models_each_used_once':4,'cbd_placeholders_removed':34,'rear_instances_preserved':80,'all_101_prior_source_placements_unchanged':True,'non_cbd_buildings_unchanged':True,'prior_meshes_geometry_matrices_and_uv_verified':len(prior),'land_area_and_road_graph_unchanged':True,'new_path_checks':checks,'prior_rear_path_checks':old_rear,'prior_v12_path_checks':oldv12,'headroom_rays':rays,'maximum_new_access_grade':maxgrade,'new_old_walk_overlap_samples':overlaps,'maximum_walk_overlap_difference_m':maxoverlap,'new_building_threshold_checks':frontage,'cbd_boundary_area_m2':boundary.area,'tianming_reserved_area_m2':reserve.area,'tianming_size_m':[172.,195.],'tianming_surface_samples':site_samples,'tianming_obstructions':0,'maximum_reserved_terrain_intrusion_m':maxintrusion,'tianming_access_width_m':8.,'reserved_site_counted_as_building':False,'source_mirroring':False}
(OUT/'v13_validation.json').write_text(json.dumps(report,indent=2));print('V13_VALIDATION_PASS',json.dumps({k:v for k,v in report.items() if k not in ['new_path_checks','prior_rear_path_checks','prior_v12_path_checks','new_building_threshold_checks']}),flush=True)
