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
p=json.loads((OUT/'city_plan.json').read_text());old=json.loads((BASE/'city_plan.json').read_text());new=p['real_buildings'][75:];assert len(new)==26
for k in ['coasts','lake','nodes','edges','interchanges','pedestrian_alleys','rear_rows','rear_access_links','connected_arcades']:assert p[k]==old[k],('prior plan changed',k)
assert p['real_buildings'][:75]==old['real_buildings'];assert len(p['buildings'])==581 and len(p['real_buildings'])==101 and p['stats']['buildings']==682<700
counts=collections.Counter(str(r['source_key']) for r in new);assert counts['27']==counts['28']==9
assert all(counts[k]==1 for k in ['21','22','23','24','25','26A','26B','26C'])
pool=json.loads((OUT/'rear_asset_pool.json').read_text());assert len(pool['types'])==9 and sum(r['instances'] for r in pool['types'])==80
polys=[Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']];tree=shapely.STRtree(polys);newstart=len(polys)-26
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
print('V12_NATIVE_PRESERVATION_PASS',len(prior),'meshes',flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];terrain=HeightField([o for o in obs if o.get('surface_type')=='terrain'])
names={v['name'] for v in old['pedestrian_alleys']};oldwalk=HeightField([o for o in obs if o.get('surface_type') in ['sidewalk','backlane_entry_walk','backlane_seam_stitch'] or o.name in names]);obsv=[];obsf=[]
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
for walk in p['infill_access_v12']:
 field=HeightField([bpy.data.objects[walk['name']]]);check=check_link(walk['name'],walk['route'],field);goal=np.array(walk['goal']);z=field.height(goal);priorz=oldwalk.height(goal);assert z is not None and priorz is not None and abs(z-priorz)<.02,('walk join lip',walk['name'],z,priorz);check['join_lip_m']=abs(z-priorz);checks.append(check);maxgrade=max(maxgrade,check['maximum_grade'])
 for q in shapely.segmentize(Polygon(walk['polygon']).boundary,1.0).coords if Polygon(walk['polygon']).boundary.geom_type=='LineString' else []:
  z=field.height(q);h=oldwalk.height(q)
  if z is not None and h is not None:
   overlaps+=1;maxoverlap=max(maxoverlap,abs(z-h));assert abs(z-h)<.025,('new surface steps on old walk',walk['name'],q,z-h)
print('V12_NEW_ACCESS_PASS',len(checks),'paths',rays,'rays',flush=True)
old_rear=[]
for link in old['rear_access_links']:
 field=HeightField([bpy.data.objects[link['name']+'_Entry_Walk']]);old_rear.append(check_link(link['name'],link['points'],field,grade_limit=None))
frontage=[]
for r in new:
 field=HeightField([bpy.data.objects[r['access_alley']]]);u=np.array([math.cos(r['theta']),math.sin(r['theta'])]);n=np.array([u[1],-u[0]]);face=np.array(r['anchor']);lip=[]
 for s in np.linspace(.04,r['right']-.04,41):
  q=face+u*s+n*.04;z=field.height(q);assert z is not None,('doorway has no paving',r['instance_name'],q.tolist());lip.append(abs(z-(r['floor']-.008)))
 assert max(lip)<.11,('door threshold too high',r['instance_name'],max(lip));frontage.append({'name':r['instance_name'],'maximum_threshold_lip_m':max(lip)})
report={'schema':'hero13.city.validation.v12','status':'PASS','city_building_units':682,'placeholder_units':581,'source_instances':101,'rear_instances_before':62,'rear_instances_after':80,'rear_pool_types':9,'new_rear_reuse_counts':{'27':9,'28':9},'new_cbd_models_each_used_once':8,'cbd_placeholders_replaced':9,'all_75_prior_source_placements_unchanged':True,'prior_meshes_geometry_matrices_and_uv_verified':len(prior),'land_area_and_road_graph_unchanged':True,'new_path_checks':checks,'prior_rear_path_checks':old_rear,'headroom_rays':rays,'maximum_new_access_grade':maxgrade,'new_old_walk_overlap_samples':overlaps,'maximum_walk_overlap_difference_m':maxoverlap,'new_building_threshold_checks':frontage,'linked_new_mesh_templates':len(linked),'source_mirroring':False}
(OUT/'v12_validation.json').write_text(json.dumps(report,indent=2));print('V12_VALIDATION_PASS',json.dumps({k:v for k,v in report.items() if k not in ['new_path_checks','prior_rear_path_checks','new_building_threshold_checks']}),flush=True)
