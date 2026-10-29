"""Finish v14 access transitions and terrain retaining seams in the saved scene.

Conservative apron projections make the entire apron level before its access
ramp starts. Existing sidewalk heights are preserved at all crossings.
"""
import bpy,json,sys,math,argparse,hashlib,os
from pathlib import Path
import numpy as np
from mathutils import Vector
ap=argparse.ArgumentParser()
for k in ['model','baseline','deps']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);MODEL=a.model.resolve();BASE=a.baseline.resolve();sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(BASE/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'));soil=HeightField([o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
bpy.ops.wm.open_mainfile(filepath=str(MODEL/'huizhou_road_network.blend'));sc=bpy.context.scene;p=json.loads((MODEL/'city_plan.json').read_text());report=json.loads((MODEL/'v14_build_report.json').read_text());newreal=p['real_buildings'][105:];newph=[b for b in p['buildings'] if b.get('added_or_modified_in')=='v14']
walk_names={r['name'] for r in p['pedestrian_alleys']};base_walk_obs=[o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['sidewalk','pedestrian','source_access','backlane_entry_walk','backlane_seam_stitch','v12_access_walk','v13_access_walk'] or o.name in walk_names)]
oldwalk=HeightField(base_walk_obs);walk_obs=list(base_walk_obs);fixed=[]
for w in p['access_v14']:
 fore=Polygon(w['fore']);route=LineString(w['route']);goal=np.array(w['goal']);grad=np.array(w.get('goal_gradient',[0.,0.]));floor=w['floor_surface'];old_start=w['ramp_start'];w['ramp_start']=max(route.project(Point(q)) for q in fore.exterior.coords);w['ramp_end']=max(w['ramp_end'],w['ramp_start']+.3)
 def height(xy):
  xy=np.array(xy);old=oldwalk.height(xy)
  if old is not None:return old+.001
  if fore.buffer(.0002).covers(Point(xy)):return floor
  s=route.project(Point(xy));t=float(np.clip((s-w['ramp_start'])/max(.3,w['ramp_end']-w['ramp_start']),0,1));plane=w['goal_z']+.001+float(grad@(xy-goal));return floor*(1-t)+plane*t
 ob=bpy.data.objects[w['name']];co=np.array([v.co[:] for v in ob.data.vertices],np.float32);co[:,2]=[height(q[:2]) for q in co];ob.data.vertices.foreach_set('co',co.ravel());ob.data.update();walk_obs.append(ob);bpy.context.view_layer.update();oldwalk=HeightField(walk_obs)
 fixed.append({'name':w['name'],'previous_ramp_start_m':old_start,'final_ramp_start_m':w['ramp_start']});print('ACCESS_REPROFILED',w['name'],flush=True)
# Lower civic support volumes while keeping their existing sites and count.
support_changes=[]
for b in [b for b in p['buildings'] if b['zone']=='GOVERNMENT']:
 i=p['buildings'].index(b);oldh=b['height'];newh=9.6 if b['center'][1]>870 else 12.0;base=b['base']
 for ob in sc.objects:
  if ob.type!='MESH':continue
  attr=ob.data.attributes.get('source_building_index')
  if not attr:continue
  ids=np.array([v.value for v in attr.data]);take=np.flatnonzero(ids==i)
  if not len(take):continue
  used={vi for fi in take for vi in ob.data.polygons[int(fi)].vertices}
  for vi in used:
   v=ob.data.vertices[vi]
   if v.co.z>base+.001:v.co.z=base+(v.co.z-base)*newh/oldh
  ob.data.update()
  if ob.name not in report['changed_original_meshes']:report['changed_original_meshes'].append(ob.name)
  if ob.name in report['unchanged_mesh_names']:report['unchanged_mesh_names'].remove(ob.name)
 b['height']=newh;b['size'][2]=newh;b['height_adjusted_in']='v14';support_changes.append({'name':b['name'],'before_m':oldh,'after_m':newh})
report['unchanged_meshes']=len(report['unchanged_mesh_names'])
# Derive the exact same coastal corridor and cut union as the authoring step.
land=unary_union([Polygon(q) for q in p['coasts'].values()]).difference(Polygon(p['lake']));carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.10) for e in p['edges']]);other_buildings=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]);line=LineString(np.array(p['urban_areas_v14']['binhai_avenue']['centerline'])[:,:2]);promenade=line.buffer(14.5,single_sided=True,join_style=2).difference(line.buffer(9.8,single_sided=True,join_style=2)).intersection(land.buffer(-.1)).difference(carriage).difference(other_buildings.buffer(.1))
cuts=unary_union([Polygon(r['pad_xy']) for r in newreal]+[Polygon(b['footprint']).buffer(.08,join_style=2) for b in newph]+[Polygon(w['polygon']).buffer(.012,join_style=2) for w in p['access_v14']]+[promenade.buffer(.012,join_style=2)])
surfaces=HeightField([bpy.data.objects[r['instance_name']+'_Foundation'] for r in newreal]+[bpy.data.objects[b['name']+'_Foundation'] for b in newph]+[bpy.data.objects[w['name']] for w in p['access_v14']]+[bpy.data.objects['MAIN_Binhai_Avenue_Promenade']])
walls_v=[];walls_f=[];fallbacks=[];missing=[]
def nearest_surface(xy):
 choices=[]
 # At the two promenade end caps the cut margin lies under the retained
 # original sidewalk. That existing sidewalk is the correct upper support.
 for field in [surfaces,oldwalk]:
  hits=field.tree.find_nearest_range(Vector((float(xy[0]),float(xy[1]),0)),.45)
  if not hits:continue
  pt,normal,index,distance=min(hits,key=lambda r:r[3]);tri=field.tri[index];q=np.array(pt[:2]);v=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[q,1.]);choices.append((float(v@tri[:,2]),float(distance)))
 return min(choices,key=lambda r:r[1]) if choices else None
for poly in shapely.get_parts(shapely.orient_polygons(cuts,exterior_cw=False)):
 if poly.geom_type!='Polygon':continue
 for ring in [poly.exterior,*poly.interiors]:
  coords=np.array(shapely.segmentize(ring,1.).coords)
  for aa,bb in zip(coords[:-1],coords[1:]):
   delta=bb-aa;L=np.linalg.norm(delta)
   if L<1e-8:continue
   n=np.array([delta[1],-delta[0]])/L;mid=(aa+bb)/2;fm=None
   for off in [.03,.07,.15,.3,.012,.006]:
    fm=surfaces.height(mid-n*off)
    if fm is not None:break
   if fm is None:
    result=nearest_surface(mid)
    if result is None:missing.append({'a':aa.tolist(),'b':bb.tolist()});continue
    fm,distance=result;fallbacks.append({'midpoint':mid.tolist(),'nearest_support_distance_m':distance})
   heights=[]
   for q in [aa,bb]:
    z=surfaces.height(q-n*.06)
    if z is None:
     near=nearest_surface(q-n*.02);z=near[0] if near is not None else fm
    ground=None
    for off in [.04,.10,.25]:
     ground=soil.height(q+n*off)
     if ground is not None:break
    if ground is None:ground=z
    heights.append((z,ground))
   if max(abs(g-z) for z,g in heights)<.025:continue
   (za,ga),(zb,gb)=heights;k=len(walls_v);walls_v.extend([[*aa,min(za,ga)-.10],[*bb,min(zb,gb)-.10],[*bb,max(zb,gb)+.012],[*aa,max(za,ga)+.012]]);walls_f.extend([[k,k+1,k+2],[k,k+2,k+3]])
finish={'access_reprofiles':fixed,'civic_support_heights':support_changes,'retaining_wall_triangles':len(walls_f),'nearest_support_fallbacks':fallbacks,'unresolved_segments':missing}
(MODEL/'v14_finish_report.json').write_text(json.dumps(finish,ensure_ascii=False,indent=2));assert not missing,missing[:12]
ob=bpy.data.objects['V14_Terrain_Cut_Retaining_Walls'];data=bpy.data.meshes.new(ob.data.name+'_finished');data.from_pydata(walls_v,[],walls_f)
for mat in ob.data.materials:data.materials.append(mat)
data.update();ob.data=data;report['retaining_wall_triangles']=len(walls_f);report['unsampled_wall_segments']=0;report['finish_stage_applied']=True
(MODEL/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(MODEL/'v14_build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
# Refresh the registry's altered height values without changing its row identities.
import csv
with (MODEL/'building_registry.csv').open() as f:rows=list(csv.DictReader(f));fields=list(rows[0])
heights={b['name']:b['height'] for b in p['buildings']}
for row in rows:
 if row['id'] in heights:row['height_m']=heights[row['id']]
with (MODEL/'building_registry.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/'huizhou_road_network.blend'),compress=True)
print('V14_FINISH_COMPLETE',json.dumps({'support_buildings':len(support_changes),'retaining_triangles':len(walls_f),'unsampled_segments':len(missing),'fallback_samples':len(fallbacks)}),flush=True)
