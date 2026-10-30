"""Construct explicit level building aprons and profiled entrance ribbons."""
from pathlib import Path
import json,sys,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union,polygonize
from mathutils import Vector
from surface_utils import co,clip_ground,fingerprint
from city_surface_sampling import HeightField
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v20.blend'));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.load(open(R/'model/city_plan.json'));old=json.load(open(R/'baseline/city_plan.json'));layout=json.load(open(R/'layout.json'));sites=json.load(open(R/'model/site_levels.json'));ids=layout['changed_district_ids'];roots={i:bpy.data.objects[f'District_{i:02}'] for i in ids}
basefield=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk']]);start=set(sc.objects)
for d in ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
bpy.context.view_layer.update();temps=set(sc.objects)-start;oldwalk=HeightField([o for o in temps if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
for o in temps:bpy.data.objects.remove(o,do_unlink=True)
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 hit,_,idx,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=field.tri[idx];w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1]);return float(w@tri[:,2])
oldfull=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in old['edges']]);car=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2,join_style=2) for e in p['edges']]);fixed=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in p['buildings']+p['real_buildings'] if b.get('added_in_version')!='v20']);lands=unary_union([Polygon(v) for v in p['coasts'].values()]);reserve=Polygon(p['cbd_plan']['tianming']['polygon']);roads=json.load(open(R/'model/road_profiles.json'));goals=[]
for s in sites:s['poly']=Polygon(s['poly']);s['apron']=s['poly'].buffer(.45,join_style=2)
for r in roads:
 r['line']=LineString(r['points']);r['full']=r['line'].buffer(r['width']/2,join_style=2)
 for side in ['left','right']:
  for g in shapely.get_parts(r['line'].parallel_offset(r['carriage_width']/2+r['sidewalk_width']*.55,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((r['region'],r['name'],g))
newfull=unary_union([r['full'] for r in roads])
for e in old['edges']:
 if e.get('bridge') or e['layer'].startswith('ELEV') or 'RAMP' in e['name']:continue
 for side in ['left','right']:
  for g in shapely.get_parts(LineString(np.array(e['points'])[:,:2]).parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((e['region'],e['name'],g))
def roadz(q):r=min(roads,key=lambda r:r['line'].distance(Point(q)));return float(np.interp(r['line'].project(Point(q)),*r['profile']))
paths=[]
for s in sites:
 start=np.array(s['front']);normal=np.array(s['outward']);tangent=np.array([-normal[1],normal[0]]);block=fixed.buffer(.1).union(unary_union([q['poly'].buffer(.1) for q in sites if q is not s]));options=[]
 for reg,name,g in sorted([x for x in goals if x[0]==s['region']],key=lambda x:x[2].distance(Point(start)))[:24]:
  end=np.array(g.interpolate(g.project(Point(start))).coords[0]);choices=[([],end),([start+normal*1.5],end),([start+normal*2.5],end)]
  for sign in [-1,1]:
   for step in [4,8,14,22,32]:
    mid=start+normal*1.5+tangent*step*sign;target=np.array(g.interpolate(g.project(Point(mid))).coords[0]);choices.append(([start+normal*1.5,mid],target))
  for mids,target in choices:
   initial=np.array(mids[0] if mids else target)-start
   if initial@normal<.35*np.linalg.norm(initial):continue
   line=LineString([start,*mids,target]);band=line.buffer(.60,cap_style=2,join_style=2)
   if line.length<.2 or line.length>150 or line.intersection(s['poly'].buffer(-.02)).length>.02 or band.intersection(block).area>.015 or band.intersection(car).area>.02:continue
   ze=roadz(target)+.12 if newfull.covers(Point(target)) else oldwalk.height(target)
   if ze is None:continue
   knots={0:s['floor']-.02,line.length:float(ze)}
   for owner in sites:
    for x in shapely.get_parts(line.intersection(owner['apron'])):
     if x.is_empty or x.geom_type not in ['Point','LineString']:continue
     q=list(x.coords)
     for xy in [q[0],q[-1]]:knots[line.project(Point(xy))]=owner['floor']-.02
   for x in shapely.get_parts(line.intersection(oldfull)):
    if x.is_empty or x.geom_type not in ['Point','LineString']:continue
    qq=list(x.coords)
    for q in [qq[0],qq[-1]]:
     h=oldwalk.height(q)
     if h is not None:knots[line.project(Point(q))]=h
   pr=np.array(sorted(knots.items()));ds=np.diff(pr[:,0]);grade=np.abs(np.diff(pr[:,1]))/np.maximum(ds,1e-7)
   if grade.max(initial=0)>.24:continue
   options.append((line.length,line,band,pr.tolist(),name))
 assert options,('no graded route',s['name'])
 _,line,band,profile,name=min(options,key=lambda x:x[0]);paths.append(dict(name=s['name']+'_Entrance',building=s['name'],region=s['region'],street=name,route=line,polygon=band,profile=profile))
def pathz(w,ss):a=np.array(w['profile']);return float(np.interp(ss,a[:,0],a[:,1]))
for i,a in enumerate(paths):
 for b in paths[:i]:
  for x in shapely.get_parts(a['route'].intersection(b['route'])):
   if x.is_empty or x.geom_type not in ['Point','LineString']:continue
   qq=list(x.coords)
   for q in [qq[0],qq[-1]]:
    pt=Point(q);owners=[s for s in sites if s['apron'].covers(pt)];z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.02 if owners else (pathz(a,a['route'].project(pt))+pathz(b,b['route'].project(pt)))/2
    for w in [a,b]:ss=w['route'].project(pt);w['profile']=[k for k in w['profile'] if abs(k[0]-ss)>.001]+[[ss,z]];w['profile'].sort()
aprons=unary_union([s['apron'] for s in sites]);ramps=unary_union([w['polygon'] for w in paths]);holes=unary_union([s['poly'].buffer(.035,join_style=2) for s in sites]);raw=aprons.buffer(1.2).union(ramps.buffer(2.5)).intersection(lands).difference(fixed.buffer(.035)).difference(car).difference(holes).difference(reserve);pavers=aprons.union(ramps).intersection(raw);grass=raw.difference(pavers)
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type') in ['terrain','sidewalk']:clip_ground(o,raw)
tree=shapely.STRtree([s['apron'] for s in sites]);ptree=shapely.STRtree([w['route'] for w in paths]);cache={};constraints=[shapely.segmentize(w['route'],.5) for w in paths]+[s['apron'].boundary for s in sites]
for w in paths:
 for ss,z in w['profile']:
  line=w['route'];q=np.array(line.interpolate(ss).coords[0]);a=np.array(line.interpolate(max(0,ss-.1)).coords[0]);b=np.array(line.interpolate(min(line.length,ss+.1)).coords[0]);t=b-a;t/=np.linalg.norm(t);n=np.array([-t[1],t[0]]);constraints.append(LineString([q-n*3.2,q+n*3.2]))
ctree=shapely.STRtree(constraints)
def height(q):
 key=tuple(round(float(x),6) for x in q)
 if key in cache:return cache[key]
 pt=Point(q);z=nearest(basefield,q);near=ptree.query(pt.buffer(3.2))
 if len(near):
  ix=min(near,key=lambda i:pt.distance(paths[int(i)]['route']));w=paths[int(ix)];d=max(0,pt.distance(w['route'])-.6);t=max(0,min(1,1-d/2.5));t=t*t*(3-2*t);zz=pathz(w,w['route'].project(pt));z=z*(1-t)+zz*t
 owners=[sites[int(i)] for i in tree.query(pt) if sites[int(i)]['apron'].covers(pt)]
 if owners:z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.02
 if oldfull.covers(pt):
  h=oldwalk.height(q)
  if h is not None:z=h
 cache[key]=z;return z
def district(q):return (9 if q[0]<-950 else 10) if q[0]<-430 and q[1]<-300 else (4 if q[1]<620 else 8)
for name,shape,mat,stype in [('V20_Entrance_Aprons',pavers,bpy.data.materials['V20_Pavers'],'sidewalk'),('V20_Entrance_Shoulders',grass,bpy.data.materials['V20_Landscape'],'terrain')]:
 vv={d:[] for d in ids};ff={d:[] for d in ids}
 for part in shapely.get_parts(shape):
  if part.is_empty or part.area<1e-6:continue
  x0,y0,x1,y1=part.bounds;xs=sorted(set(np.arange(math.floor(x0/2)*2,x1+2,2).tolist()+[-950.]));ys=sorted(set(np.arange(math.floor(y0/2)*2,y1+2,2).tolist()+[620.]));xs=[x for x in xs if x0-2<=x<=x1+2];ys=[y for y in ys if y0-2<=y<=y1+2]
  for x,xn in zip(xs,xs[1:]):
   for y,yn in zip(ys,ys[1:]):
    tile=box(x,y,xn,yn)
    if not part.intersects(tile):continue
    inside=part.intersection(tile);lines=[c.intersection(inside) for c in [constraints[int(i)] for i in ctree.query(tile)]];pieces=list(polygonize(unary_union([inside.boundary]+lines))) if lines else [inside]
    for face in pieces:
     if face.is_empty or not inside.buffer(1e-8).covers(face.representative_point()):continue
     for t in shapely.get_parts(shapely.constrained_delaunay_triangles(face)):
      xy=np.array(t.exterior.coords)[:3]
      if np.linalg.det(np.c_[xy,np.ones(3)])<0:xy=xy[::-1]
      if t.area<1e-9:continue
      d=district(xy.mean(0));k=len(vv[d]);vv[d].extend([[*q,height(q)] for q in xy]);ff[d].append([k,k+1,k+2])
 for d in ids:
  me=bpy.data.meshes.new(f'{name}_{d:02}');me.from_pydata(vv[d],[],ff[d]);me.materials.append(mat);me.update();o=bpy.data.objects.new(f'{name}_{d:02}',me);sc.collection.objects.link(o);o.parent=roots[d];o['district_id']=d;o['surface_type']=stype;o['modified_in_version']='v20'
 print('ENTRANCE_PATCH',name,sum(len(x) for x in ff.values()),flush=True)
p['access_v20']=[{k:list(v.coords) if k=='route' else list(v.exterior.coords) if k=='polygon' else v for k,v in w.items()} for w in paths];(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')))
report=json.load(open(R/'model/build_report.json'));legitimate=[]
for name,h in list(report['unchanged_original_objects'].items()):
 o=sc.objects.get(name)
 if o is not None and fingerprint(o)!=h:
  assert o.get('surface_type') in ['terrain','sidewalk'],('unexpected original change',name,o.get('surface_type'));legitimate.append(name);del report['unchanged_original_objects'][name]
report['changed_original_objects']=sorted(set(report['changed_original_objects'])|set(legitimate));report['additional_regraded_ground_objects']=legitimate;(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v20.blend'),compress=True);print('EXPLICIT_ENTRANCES_DONE',flush=True)
