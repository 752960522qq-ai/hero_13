"""Regrade new streets and entrances against their exact original street joins."""
from pathlib import Path
import sys,json,math,copy
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from mathutils import Matrix,Vector
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,polygonize
from city_surface_sampling import HeightField
from surface_utils import co,clip_ground,keep_faces
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v20.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));layout=json.load(open(R/'layout.json'));sites=json.load(open(R/'model/site_levels.json'));props=json.load(open(R/'model/public_instances.json'));ids=layout['changed_district_ids'];roots={d:bpy.data.objects[f'District_{d:02}'] for d in ids}
original=set(sc.objects)
for d in ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
bpy.context.view_layer.update();temps=set(sc.objects)-original
soil=HeightField([o for o in temps if o.type=='MESH' and o.get('surface_type')=='terrain']);oldstreet=HeightField([o for o in temps if o.type=='MESH' and o.get('surface_type') in ['pavement','road_kit']]);oldwalk=HeightField([o for o in temps if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
for o in temps:bpy.data.objects.remove(o,do_unlink=True)
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 hit,_,i,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=field.tri[i];w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1]);return float(w@tri[:,2])
old=json.load(open(R/'baseline/city_plan.json'));oldfull=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in old['edges']]);oldcar=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2,join_style=2) for e in old['edges']]);oldcartest=oldcar.buffer(.0003)
roads=[]
for row in layout['new_roads']:
 r=copy.deepcopy(row);r['line']=LineString(r['points']);r['full']=r['line'].buffer(r['width']/2,join_style=2);r['car']=r['line'].buffer(r['carriage_width']/2,join_style=2);line=r['line'];knots={0:nearest(oldstreet,line.coords[0]),line.length:nearest(oldstreet,line.coords[-1])}
 for q in shapely.get_parts(line.intersection(oldcar.boundary)):
  if q.geom_type=='Point':knots[line.project(q)]=nearest(oldstreet,q.coords[0])
 if 'Garden_Link' in r['name']:
  parent=roads[-1];knots[0]=float(np.interp(parent['line'].project(Point(line.coords[0])),*parent['profile']))
 else:
  if r['region']=='MAIN':
   target=LineString(layout['new_roads'][1]['points']);end=target.coords[-1];ss=line.project(Point(target.coords[0]));knots[ss]=nearest(oldstreet,end)+3.
 rec=sorted(knots.items());r['profile']=[[float(x) for x,y in rec],[float(y) for x,y in rec]];roads.append(r);print('PROFILE',r['name'],r['profile'],flush=True)
newfull=unary_union([r['full'] for r in roads]);newcar=unary_union([r['car'] for r in roads]);allcar=oldcar.union(newcar);roadtree=shapely.STRtree([r['line'] for r in roads]);roadcache={}
def roadz(q):
 key=tuple(round(float(x),6) for x in q)
 if key in roadcache:return roadcache[key]
 pt=Point(q);r=roads[int(roadtree.nearest(pt))];z=float(np.interp(r['line'].project(pt),*r['profile']))
 if oldcartest.covers(pt):
  zz=oldstreet.height(q)
  if zz is not None:z=zz
 roadcache[key]=z;return z
for s in sites:
 if s['group']!='NT_STEPPED_CAMPUS':
  z=roadz(s['front'])+.16;delta=z-s['floor'];s['floor']=z
  for o in sc.objects:
   if o.get('instance_id')==s['name']:
    M=o.matrix_world.copy();M.translation.z+=delta;o.matrix_world=M
   if o.get('site_building')==s['name']:
    xyz=co(o);oldtop=float(xyz[:,2].max());bottom=min(z-.35,nearest(soil,s['center'])-.15)
    for v in o.data.vertices:v.co.z=z-.018 if abs(v.co.z-oldtop)<.01 else bottom
    o.data.update()
 s['poly']=Polygon(s['poly']);s['pad']=s['poly'].buffer(1,join_style=2)
fixed=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in p['buildings']+p['real_buildings'] if b.get('added_in_version')!='v20']);lands=unary_union([Polygon(v) for v in p['coasts'].values()]);reserve=Polygon(p['cbd_plan']['tianming']['polygon']);newpolys=unary_union([s['poly'] for s in sites]);goals=[]
for r in roads:
 for side in ['left','right']:
  for line in shapely.get_parts(r['line'].parallel_offset(r['carriage_width']/2+r['sidewalk_width']*.55,side,join_style=2)):
   if line.geom_type=='LineString':goals.append((r['region'],r['name'],line))
for e in old['edges']:
 if e.get('bridge') or e['layer'].startswith('ELEV') or 'RAMP' in e['name']:continue
 for side in ['left','right']:
  for line in shapely.get_parts(LineString(np.array(e['points'])[:,:2]).parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)):
   if line.geom_type=='LineString':goals.append((e['region'],e['name'],line))
paths=[]
for s in sites:
 start=np.array(s['front']);normal=np.array(s['outward']);tangent=np.array([-normal[1],normal[0]]);blocked=fixed.buffer(.15).union(unary_union([q['poly'].buffer(.15) for q in sites if q is not s])).union(s['poly'].buffer(-.025));options=[]
 for reg,name,g in sorted([g for g in goals if g[0]==s['region']],key=lambda g:g[2].distance(Point(start)))[:24]:
  end=np.array(g.interpolate(g.project(Point(start))).coords[0]);choices=[([],end),([start+normal*2],end)]
  for sign in [-1,1]:
   for step in [3,6,10,16,24]:
    mid=start+normal*.72+tangent*step*sign;target=np.array(g.interpolate(g.project(Point(mid))).coords[0]);choices.append(([start+normal*.72,mid],target))
  for mids,target in choices:
   line=LineString([start,*mids,target]);band=line.buffer(.60,cap_style=2,join_style=2)
   if line.length<.15 or line.length>140 or line.intersection(blocked).length>.03 or band.intersection(blocked.difference(s['poly'])).area>.02 or band.intersection(allcar).area>.02:continue
   z=roadz(target)+.12 if newfull.covers(Point(target)) else oldwalk.height(target)
   if z is None or abs(s['floor']-.02-z)/max(line.length-1,1)>.22:continue
   options.append((line.length,line,band,float(z),name))
 assert options,('route',s['name'])
 _,line,band,z,name=min(options,key=lambda x:x[0]);knots={0:s['floor']-.02,line.length:z}
 for owner in sites:
  for piece in shapely.get_parts(line.intersection(owner['pad'])):
   if not piece.is_empty and piece.geom_type in ['LineString','Point']:
    xy=list(piece.coords)
    for q in [xy[0],xy[-1]]:knots[line.project(Point(q))]=owner['floor']-.02
 paths.append(dict(name=s['name']+'_Entrance',building=s['name'],route=line,polygon=band,profile=sorted(knots.items()),region=s['region'],street=name))
def pathz(w,s):a=np.array(w['profile']);return float(np.interp(s,a[:,0],a[:,1]))
for i,a in enumerate(paths):
 for b in paths[:i]:
  for piece in shapely.get_parts(a['route'].intersection(b['route'])):
   if piece.is_empty or piece.geom_type not in ['LineString','Point']:continue
   xy=list(piece.coords)
   for q in [xy[0],xy[-1]]:
    pt=Point(q);owners=[s for s in sites if s['pad'].covers(pt)];z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.02 if owners else (pathz(a,a['route'].project(pt))+pathz(b,b['route'].project(pt)))/2
    for w in [a,b]:ss=w['route'].project(pt);w['profile']=[x for x in w['profile'] if abs(x[0]-ss)>.001]+[[ss,z]];w['profile'].sort()
holes=unary_union([s['poly'].buffer(.035,join_style=2) for s in sites]);aprons=unary_union([w['polygon'] for w in paths]);raw=unary_union([s['pad'].buffer(12,join_style=2) for s in sites]+[Polygon(b['footprint']).buffer(3) for b in layout['removed_placeholder_lots']]+[newfull.buffer(12)]+[w['polygon'].buffer(3) for w in paths]);raw=raw.intersection(lands).difference(fixed.buffer(.03)).difference(reserve);asphalt=newcar.difference(oldcar);walk=newfull.difference(newcar).difference(oldfull).union(aprons.difference(oldcar).difference(newcar)).difference(holes);rest=raw.difference(newfull).difference(oldfull).difference(holes).difference(walk);cut=rest.union(walk).union(asphalt).union(holes)
for o in list(sc.objects):
 if o.name.startswith(('V20_Graded_Land_','V20_New_Street_Walks_')):bpy.data.objects.remove(o,do_unlink=True)
 elif o.type=='MESH' and o.get('surface_type')=='terrain':clip_ground(o,cut)
 elif o.type=='MESH' and o.get('surface_type')=='sidewalk':clip_ground(o,aprons.union(asphalt))
 elif o.type=='MESH' and o.name.startswith('V20_') and o.get('surface_type') in ['pavement','road_marking','curb']:
  st=o.get('surface_type')
  for v in o.data.vertices:
   if st=='pavement':delta=0
   elif st=='road_marking':delta=.019 if 'Crosswalk' in o.name else .015
   else:delta=.12 if v.index%2 else .005
   v.co.z=roadz(v.co[:2])+delta
  o.data.update()
padshapes=[s['pad'] for s in sites];padtree=shapely.STRtree(padshapes);pathlines=[w['route'] for w in paths];pathtree=shapely.STRtree(pathlines);cache={}
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def groundz(q):
 key=tuple(round(float(x),6) for x in q)
 if key in cache:return cache[key]
 pt=Point(q);z=nearest(soil,q);r=roads[int(roadtree.nearest(pt))];dist=pt.distance(r['line']);outer=r['width']/2
 if dist<outer+12:
  t=smooth(1-max(0,dist-outer)/12);z=z*(1-t)+(roadz(q)+.12)*t
 for i in padtree.query(pt.buffer(12)):
  s=sites[int(i)];d=pt.distance(s['pad'])
  if d<12:t=smooth(1-d/12);z=z*(1-t)+(s['floor']-.02)*t
 near=pathtree.query(pt.buffer(3.6))
 if len(near):
  i=min(near,key=lambda i:pt.distance(pathlines[int(i)]));w=paths[int(i)];d=max(0,pt.distance(w['route'])-.6);t=smooth(1-d/3);h=pathz(w,w['route'].project(pt));z=z*(1-t)+h*t
 owners=[sites[int(i)] for i in padtree.query(pt) if padshapes[int(i)].covers(pt)]
 if owners:z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.02
 if newfull.covers(pt) and pt.distance(newcar)<.10:z=roadz(q)+.12
 if oldfull.covers(pt) and not asphalt.buffer(.0001).covers(pt):
  zz=oldwalk.height(q)
  if zz is not None:z=zz
 cache[key]=z;return z
def district(q):return (9 if q[0]<-950 else 10) if q[0]<-430 and q[1]<-300 else (4 if q[1]<620 else 8)
constraints=[shapely.segmentize(w['route'],.7) for w in paths]+[s['pad'].boundary for s in sites];ctree=shapely.STRtree(constraints)
for name,shape,mat,stype in [('V20_Graded_Land',rest,bpy.data.materials['V20_Landscape'],'terrain'),('V20_New_Street_Walks',walk,bpy.data.materials['V20_Pavers'],'sidewalk')]:
 vv={d:[] for d in ids};ff={d:[] for d in ids}
 for part in shapely.get_parts(shape):
  if part.is_empty or part.area<1e-7:continue
  x0,y0,x1,y1=part.bounds;xs=sorted(set(np.arange(math.floor(x0/3)*3,x1+3,3).tolist()+[-950.]));ys=sorted(set(np.arange(math.floor(y0/3)*3,y1+3,3).tolist()+[620.]));xs=[x for x in xs if x0-3<=x<=x1+3];ys=[y for y in ys if y0-3<=y<=y1+3]
  for x,xn in zip(xs,xs[1:]):
   for y,yn in zip(ys,ys[1:]):
    tile=box(x,y,xn,yn)
    if not part.intersects(tile):continue
    inside=part.intersection(tile);segments=[constraints[int(i)].intersection(inside) for i in ctree.query(tile)];pieces=list(polygonize(unary_union([inside.boundary]+segments))) if segments else [inside]
    for face in pieces:
     if face.is_empty or not inside.covers(face.representative_point()):continue
     for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(face)):
      xy=np.array(tri.exterior.coords)[:3]
      if np.linalg.det(np.c_[xy,np.ones(3)])<0:xy=xy[::-1]
      d=district(xy.mean(0));k=len(vv[d]);vv[d].extend([[float(a),float(b),float(groundz([a,b]))] for a,b in xy]);ff[d].append([k,k+1,k+2])
 for d in ids:
  if not ff[d]:continue
  me=bpy.data.meshes.new(f'{name}_{d:02}');me.from_pydata(vv[d],[],ff[d]);me.materials.append(mat);me.update();o=bpy.data.objects.new(f'{name}_{d:02}',me);sc.collection.objects.link(o);o.parent=roots[d];o['district_id']=d;o['surface_type']=stype;o['modified_in_version']='v20';o['walkable_surface']=True
 print('REGRADED',name,sum(len(x) for x in ff.values()),flush=True)
# Put every furnishing back on the final graded ground; preserve its plan position.
for rec in props:
 if 'center' not in rec:continue
 q=rec['center'];z=groundz(q);zz=oldwalk.height(q)
 if oldfull.covers(Point(q)) and not newfull.covers(Point(q)) and zz is not None:z=zz
 delta=z-rec['z'];rec['z']=z
 for o in sc.objects:
  if o.get('public_instance_id')==rec['instance_id']:
   M=o.matrix_world.copy();M.translation.z+=delta;o.matrix_world=M
for rec in props:
 if rec['type']!='overhead_cable':continue
 a=next(x for x in props if x['instance_id']==rec['start']);b=next(x for x in props if x['instance_id']==rec['end']);o=next(o for o in sc.objects if o.get('public_instance_id')==rec['instance_id']);xyz=co(o);q0=np.array(a['center']);q1=np.array(b['center']);direction=q1-q0;length2=direction@direction;baseline_start=float(xyz[:,2].max());oldzs=[]
 # Each cable's sag shape is retained while endpoints follow their poles.
 for v in o.data.vertices:
  t=float(np.clip((np.array(v.co[:2])-q0)@direction/length2,0,1));v.co.z=(a['z']*(1-t)+b['z']*t)+8.18-4*.72*t*(1-t)
 o.data.update()
for e in p['edges']:
 if not e['name'].startswith('V20_'):continue
 e['points']=[[q[0],q[1],roadz(q[:2])] for q in e['points']];a=np.array(e['points']);e['range']=[float(a[:,2].min()),float(a[:,2].max())];e['max_grade']=float((np.abs(np.diff(a[:,2]))/np.maximum(np.linalg.norm(np.diff(a[:,:2],axis=0),axis=1),1e-7)).max(initial=0))
 for key,q in [('a',e['points'][0]),('b',e['points'][-1])]:p['nodes'][e[key]]['z']=q[2]
newby={s['name']:s for s in sites}
for b in p['real_buildings']:
 if b.get('added_in_version')=='v20':b['floor']=newby[b['name']]['floor']
p['access_v20']=[{k:list(v.coords) if k=='route' else list(v.exterior.coords) if k=='polygon' else v for k,v in w.items()} for w in paths];p['urban_areas_v20']['public_furniture']=props;(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));(R/'model/site_levels.json').write_text(json.dumps([{k:list(v.exterior.coords) if k in ['poly','pad'] else v for k,v in s.items()} for s in sites],ensure_ascii=False,indent=2));(R/'model/public_instances.json').write_text(json.dumps(props,ensure_ascii=False,indent=2));(R/'model/road_profiles.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ['line','full','car']} for r in roads],ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v20.blend'),compress=True);print('GRADE_REPAIR_DONE',flush=True)
