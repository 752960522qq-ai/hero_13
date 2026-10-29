"""Independent checks for the v14 additions against the saved native scene."""
import bpy,json,sys,math,argparse,hashlib,collections
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ap=argparse.ArgumentParser()
for k in ['model','baseline','deps','report']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(a.baseline.resolve()/'tools'))
from city_surface_sampling import HeightField
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
p=json.loads((a.model/'city_plan.json').read_text());old=json.loads((a.baseline/'city_plan.json').read_text());build=json.loads((a.model/'v14_build_report.json').read_text())
assert len(p['buildings'])==540 and len(p['real_buildings'])==124
assert len(p['buildings'])+len(p['real_buildings'])==664<700
assert p['coasts']==old['coasts'] and p['lake']==old['lake'] and p['nodes']==old['nodes']
assert [{k:v for k,v in e.items() if k!='display_name_zh'} for e in p['edges']]==old['edges']
for k in ['pedestrian_alleys','interchanges','grade_separated_crossings','connected_arcades','rear_rows','rear_access_links','infill_access_v12','cbd_access_v13']:assert p[k]==old[k],k
assert p['real_buildings'][:105]==old['real_buildings']
assert p['cbd_plan']['tianming']==old['cbd_plan']['tianming']
land=unary_union([Polygon(q) for q in p['coasts'].values()]).difference(Polygon(p['lake']));assert abs(land.area-3250000)<.001
added=p['real_buildings'][105:];assert len(added)==19 and len({r['file'] for r in added})==19
assert collections.Counter(r['zone'] for r in added)=={'CBD':15,'GOVERNMENT':1,'APARTMENT':3}
assert p['cbd_plan']['source_buildings']==29 and p['cbd_plan']['placeholder_buildings']==0
assert sum(b['zone']=='VILLA' for b in p['buildings'])==9
assert sum(b['zone']=='APARTMENT' for b in p['buildings'])==9
newph=[b for b in p['buildings'] if b.get('added_or_modified_in')=='v14'];assert len(newph)==18
names=[b['name'] for b in p['buildings']]+[r['instance_name'] for r in p['real_buildings']];assert len(names)==len(set(names))
allpoly=[(b['name'],Polygon(b['footprint'])) for b in p['buildings']]+[(r['instance_name'],Polygon(r['footprint_xy'])) for r in p['real_buildings']]
reserve=Polygon(p['cbd_plan']['tianming']['polygon']);boundary=Polygon(p['cbd_plan']['boundary'])
for name,poly in [(r['instance_name'],Polygon(r['footprint_xy'])) for r in added]+[(b['name'],Polygon(b['footprint'])) for b in newph]:
 assert land.covers(poly.buffer(.02)),('Building outside land',name)
 assert poly.intersection(reserve).area<.001
 assert all(poly.intersection(q).area<.002 for n,q in allpoly if n!=name),('Overlapping footprint',name)
for r in added:
 if r['zone']=='CBD':assert boundary.covers(Polygon(r['footprint_xy']))
rotations=collections.Counter(int(round(math.degrees(r['theta'])))%360 for r in added);assert len(rotations)>=4 and max(rotations.values())<=10
bpy.ops.wm.open_mainfile(filepath=str((a.model/'huizhou_road_network.blend').resolve()));bpy.context.view_layer.update();sc=bpy.context.scene
def world_vertices(ob):
 ar=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',ar);ar=ar.reshape(-1,3).astype(float);M=np.array(ob.matrix_world);return ar@M[:3,:3].T+M[:3,3]
def fingerprint(o):
 m=o.data;h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in m.vertices],dtype='<f4').tobytes())
 for f in m.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in m.uv_layers:h.update(np.array([x.uv[:] for x in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()
for name in build['unchanged_mesh_names']:assert fingerprint(bpy.data.objects[name])==build['original_mesh_fingerprints'][name],name
source_checks=[]
for r in added:
 inst=bpy.data.objects[r['instance_name']];meshes=[o for o in inst.children_recursive if o.type=='MESH'];co=np.concatenate([world_vertices(o) for o in meshes]);height=float(co[:,2].max()-co[:,2].min());assert abs(height-r['target_height_m'])<.002
 M=np.array(inst.matrix_world)[:3,:3];assert np.linalg.det(M)>0;scales=np.linalg.norm(M,axis=0)/r['uniform_scale'];assert np.max(abs(scales-1))<1e-5
 assert all(o.data.uv_layers for o in meshes)
 foundation=HeightField([bpy.data.objects[r['instance_name']+'_Foundation']]);assert abs(foundation.height(r['center'])-(r['floor']-.018))<.002
 source_checks.append({'name':r['instance_name'],'source_file':r['file'],'zone':r['zone'],'height_m':height,'rotation_degrees':math.degrees(r['theta'])%360,'uniform_axis_scales':scales.tolist()})
terrain=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
oldwalk_obs=[o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['sidewalk','pedestrian','source_access','backlane_entry_walk','backlane_seam_stitch','v12_access_walk','v13_access_walk'] or o.name in {r['name'] for r in p['pedestrian_alleys']})]
oldwalk=HeightField(oldwalk_obs)
walkfields={w['name']:HeightField([bpy.data.objects[w['name']]]) for w in p['access_v14']}
obstacles=[o for o in sc.objects if o.type=='MESH' and (o.get('is_placeholder') or '_Source_Mesh_' in o.name or '_Foundation' in o.name or o.name.startswith('Oldtown_Row_Partywall_') or o.name.endswith(('_Crown','_Trunk')))]
vv=[];ff=[];offset=0
for ob in obstacles:
 co=world_vertices(ob);ob.data.calc_loop_triangles();faces=np.array([t.vertices[:] for t in ob.data.loop_triangles]);vv.append(co);ff.append(faces+offset);offset+=len(co)
bvh=BVHTree.FromPolygons(np.concatenate(vv).tolist(),np.concatenate(ff).tolist(),all_triangles=True)
headroom_rays=0;walk_checks=[];failures=[];max_grade=0.;max_lip=0.;sampled=0
for w in p['access_v14']:
 field=walkfields[w['name']];line=LineString(w['route']);zs=[];distances=np.linspace(0,line.length,max(4,int(line.length/.7)+1));localgrade=0.;terrain_penetration=0.;count=0
 for s in distances:
  xy=np.array(line.interpolate(s).coords[0]);aa=np.array(line.interpolate(max(0,s-.05)).coords[0]);bb=np.array(line.interpolate(min(line.length,s+.05)).coords[0]);u=(bb-aa)/max(np.linalg.norm(bb-aa),1e-9);n=np.array([-u[1],u[0]]);z=field.height(xy)
  if z is None:failures.append({'kind':'walk_center_hole','walk':w['name'],'xy':xy.tolist()});continue
  zs.append((s,z))
  for off in [-1.25,0.,1.25]:
   q=xy+n*off;h=field.height(q)
   if h is None:failures.append({'kind':'walk_width_hole','walk':w['name'],'xy':q.tolist()});continue
   g=terrain.height(q)
   if g is not None:terrain_penetration=max(terrain_penetration,g-h)
   hit,_,_,_=bvh.ray_cast(Vector((*q,h+.14)),Vector((0,0,1)),2.1)
   if hit is not None:failures.append({'kind':'walk_obstruction','walk':w['name'],'xy':q.tolist(),'height':float(hit.z-h)})
   headroom_rays+=1;count+=1
 for (s0,z0),(s1,z1) in zip(zs[:-1],zs[1:]):
  if s1>s0:localgrade=max(localgrade,abs(z1-z0)/(s1-s0))
 goal=w['goal'];h=field.height(goal);oldh=oldwalk.height(goal);assert h is not None and oldh is not None
 lip=abs(h-oldh);max_lip=max(max_lip,lip);max_grade=max(max_grade,localgrade)
 if localgrade>.09:failures.append({'kind':'steep_walk','walk':w['name'],'grade':localgrade})
 if lip>.004:failures.append({'kind':'walk_join_lip','walk':w['name'],'lip':lip})
 if terrain_penetration>.035:failures.append({'kind':'terrain_in_walk','walk':w['name'],'penetration_m':terrain_penetration})
 sampled+=count;walk_checks.append({'name':w['name'],'samples':count,'maximum_grade':localgrade,'goal_lip_m':lip,'maximum_terrain_penetration_m':terrain_penetration})
 print('ACCESS_CHECK',w['name'],round(localgrade,5),round(lip,5),flush=True)
# Every supplied facade has a nearly flush, full-width entrance apron.
for r in added:
 field=walkfields[r['access_alley']];u=np.array([math.cos(r['theta']),math.sin(r['theta'])]);n=np.array([u[1],-u[0]]);lips=[]
 for s in np.linspace(.04,r['right']-.04,41):
  xy=np.array(r['anchor'])+u*s+n*.04;z=field.height(xy)
  if z is None:failures.append({'kind':'entrance_apron_hole','building':r['instance_name'],'xy':xy.tolist()});continue
  lips.append(abs(z-(r['floor']-.008)))
 if lips and max(lips)>.035:failures.append({'kind':'entrance_threshold','building':r['instance_name'],'lip':max(lips)})
 source_checks[[x['name'] for x in source_checks].index(r['instance_name'])]['maximum_threshold_lip_m']=max(lips,default=0.)
# Binhai Avenue's original carriageway remains intact; the walking corridor is clear.
avenue=p['urban_areas_v14']['binhai_avenue'];line=LineString(np.array(avenue['centerline'])[:,:2]);prom=bpy.data.objects['MAIN_Binhai_Avenue_Promenade'];coastalwalk=HeightField(oldwalk_obs+[prom]);coast_samples=0;coast_soil=0.;coast_grades=[]
for lateral in [8.5,10.6,11.9]:
 last=None
 for s in np.linspace(.5,line.length-.5,int(line.length/2)+1):
  xy=np.array(line.interpolate(s).coords[0]);aa=np.array(line.interpolate(max(0,s-.1)).coords[0]);bb=np.array(line.interpolate(min(line.length,s+.1)).coords[0]);u=(bb-aa)/np.linalg.norm(bb-aa);n=np.array([-u[1],u[0]]);q=xy+n*lateral;z=coastalwalk.height(q)
  if z is None:failures.append({'kind':'coastal_walk_hole','xy':q.tolist()});continue
  g=terrain.height(q)
  if g is not None:coast_soil=max(coast_soil,g-z)
  hit,_,_,_=bvh.ray_cast(Vector((*q,z+.14)),Vector((0,0,1)),2.1)
  if hit is not None:failures.append({'kind':'coastal_walk_obstruction','xy':q.tolist(),'height':float(hit.z-z)})
  if last:coast_grades.append(abs(z-last[1])/(s-last[0]))
  last=(s,z);coast_samples+=1;headroom_rays+=1
if coast_soil>.035:failures.append({'kind':'terrain_in_coastal_walk','penetration_m':coast_soil})
# The future landmark site is still level and completely unobstructed.
site=HeightField([bpy.data.objects['CBD_Tianming_Reserved_Pad']]);site_z=p['cbd_plan']['tianming']['surface_z_m'];site_samples=0
for x in np.linspace(-374,-204,35):
 for y in np.linspace(736,929,39):
  z=site.height([x,y]);assert z is not None and abs(z-site_z)<.001;hit,_,_,_=bvh.ray_cast(Vector((x,y,z+.14)),Vector((0,0,1)),500.)
  assert hit is None,('Tianming site occupied',x,y);site_samples+=1
report={'status':'PASS' if not failures else 'FAIL','city_buildings':664,'land_area_m2':land.area,'cbd_source_buildings':29,'cbd_placeholders':0,'planned_cbd_with_tianming':30,'new_source_instances':source_checks,'source_rotation_histogram_degrees':dict(rotations),'unchanged_prior_meshes':len(build['unchanged_mesh_names']),'prior_source_instances_preserved':105,'new_walks':walk_checks,'new_walk_surface_samples':sampled,'maximum_new_access_grade':max_grade,'maximum_new_sidewalk_join_lip_m':max_lip,'coastal_walk_samples':coast_samples,'maximum_coastal_walk_terrain_penetration_m':coast_soil,'maximum_coastal_walk_longitudinal_grade':max(coast_grades,default=0.),'headroom_rays':headroom_rays,'tianming_reserved_grid_samples':site_samples,'road_graph_geometry_unchanged':True,'failures':failures,'limits':'Native and exported static geometry checks; game collision, navigation, streaming and runtime FPS are not integrated.'}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2))
assert not failures,('V14 geometry failures',failures[:20],len(failures))
print('V14_NATIVE_VALIDATION_PASS',sampled,headroom_rays,'max grade',max_grade,flush=True)
