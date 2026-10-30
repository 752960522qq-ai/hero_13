"""Build v19 in world metres. Only districts 04, 08, 09 and 14 are changed."""
import sys,os,json,math,copy,collections,heapq
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps'));sys.path.insert(0,str(R/'tools'))
import bpy,numpy as np,shapely
from mathutils import Vector,Matrix
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,polygonize
from city_surface_sampling import HeightField
from surface_utils import co,fingerprint,keep_faces,clip_ground
layout=json.load(open(R/'layout.json'));p=json.load(open(R/'baseline/city_plan.json'));old=copy.deepcopy(p);catalog={a['asset_id']:a for a in json.load(open(R/'asset_catalog.json'))};ids=layout['changed_district_ids'];bpy.ops.wm.read_factory_settings(use_empty=True)
for d in ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
bpy.context.view_layer.update();sc=bpy.context.scene
# Imported parent transforms are baked before comparing untouched world geometry.
for o in list(sc.objects):
 if o.type=='MESH':m=o.data.copy();m.transform(o.matrix_world);o.parent=None;o.data=m;o.matrix_world=Matrix.Identity(4);o.data.update()
for o in list(sc.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
roots={}
for d in ids:o=bpy.data.objects.new(f'District_{d:02}',None);sc.collection.objects.link(o);o['district_id']=d;roots[d]=o
for o in list(sc.objects):
 if o.type=='MESH':o.parent=roots[int(o['district_id'])]
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);walkfield=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 hit,_,idx,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=field.tri[idx];w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1]);return float(w@tri[:,2])
def region(q):return 'WEST' if q[0]<-700 and q[1]<0 else 'EAST' if q[0]>450 and q[1]<0 else 'MAIN'
def district(q):
 r=region(q)
 return 9 if r=='WEST' else 14 if r=='EAST' else 4 if q[1]<620 else 8
removed={b['name'] for b in layout['removed_placeholder_lots']};lotpolys=[Polygon(b['footprint']) for b in old['buildings']];tree=shapely.STRtree(lotpolys);removed_faces=0;removed_objects=[]
for o in list(sc.objects):
 if o.type!='MESH':continue
 source=o.get('source_object',o.name)
 if any(name in source for name in removed):removed_objects.append(o.name);bpy.data.objects.remove(o,do_unlink=True);continue
 if o.get('is_placeholder'):
  xyz=co(o);keep=[];owners=set()
  for f in o.data.polygons:
   pt=Point(xyz[list(f.vertices),:2].mean(0));i=int(tree.nearest(pt));owner=old['buildings'][i]['name'];assert pt.distance(lotpolys[i])<.1,(o.name,owner,pt.distance(lotpolys[i]));k=owner not in removed;keep.append(k)
   if k:owners.add(owner)
  if not all(keep):
   removed_faces+=len(keep)-sum(keep);name=o.name;keep_faces(o,keep)
   if name in sc.objects:sc.objects[name]['placeholder_lot_count']=len(owners);sc.objects[name]['modified_in_version']='v19'
p['buildings']=[b for b in p['buildings'] if b['name'] not in removed]
for k,v in list(p.items()):
 if k.startswith('access_') and isinstance(v,list):p[k]=[w for w in v if w.get('building',w.get('name')) not in removed]
fixed=[Polygon(b.get('footprint',b.get('footprint_xy'))) for b in p['buildings']+p['real_buildings']];fixedshape=unary_union(fixed);lands={k:Polygon(v) for k,v in p['coasts'].items()};roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.015,join_style=2) for e in p['edges']]);carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.025,join_style=2) for e in p['edges']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
def material(n,c):
 m=bpy.data.materials.new(n);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=.86;return m
soilmat=material('V19_Landscape',(.40,.47,.33));pavemat=material('V19_Warm_Pavers',(.53,.52,.47));gravel=material('V19_Service_Gravel',(.37,.39,.38));base=material('V19_Foundation',(.51,.51,.47));leafmat=material('V19_Tree_Foliage',(.12,.28,.10));bark=material('V19_Tree_Bark',(.25,.18,.11))
def newmesh(n,v,f,mat,d=None,props=None):
 if d is None:d=district(np.mean(np.asarray(v),axis=0))
 m=bpy.data.meshes.new(n);m.from_pydata(v,[],f);m.materials.append(mat);m.update();o=bpy.data.objects.new(n,m);sc.collection.objects.link(o);o.parent=roots[d];o['district_id']=d;o['source_object']=n;o['modified_in_version']='v19'
 for k,x in (props or {}).items():o[k]=x
 return o
templates={}
for aid in sorted({b['asset_id'] for b in layout['placements']}):
 start=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(R/'extracted'/catalog[aid]['file']));bpy.context.view_layer.update();obs=set(sc.objects)-start;meshes=[]
 for o in obs:
  if o.type=='MESH':m=o.data.copy();m.transform(o.matrix_world);meshes.append((o.name,m))
 for o in obs:bpy.data.objects.remove(o,do_unlink=True)
 templates[aid]=meshes
 print('TEMPLATE',aid,len(meshes),flush=True)
sites=[]
for b in layout['placements']:
 poly=Polygon(b['footprint_xy']);pad=poly.buffer(1.25,join_style=2);q=shapely.segmentize(poly.exterior,3.);zz=[nearest(soil,x) for x in q.coords];floor=max(zz)+.055
 rec={**b,'floor':floor,'poly':poly,'pad':pad};sites.append(rec);M=Matrix.Translation((*b['center'],floor))@Matrix.Rotation(math.radians(b['rotation_deg']),4,'Z')@Matrix.Diagonal((b['scale'],b['scale'],b['scale'],1))
 for i,(sname,m) in enumerate(templates[b['asset_id']]):
  n=b['instance_id']+f'__Part{i:03}';o=bpy.data.objects.new(n,m);sc.collection.objects.link(o);o.parent=roots[b['district_id']];o.matrix_world=M;o['district_id']=b['district_id'];o['asset_id']=b['asset_id'];o['instance_id']=b['instance_id'];o['source_instance']=b['instance_id'];o['source_filename']=b['source_filename'];o['source_node_name']=b['source_node_name'];o['source_mesh_name']=sname;o['replaces_lots']='|'.join(b['replaces']);o['layout_group']=b['group'];o['added_in_version']='v19'
 print('PLACED',b['instance_id'],floor,flush=True)
# Public footway goals use the actual current road plan, including curved street edges.
goals=[]
for e in p['edges']:
 if e.get('bridge') or e['layer'].startswith('ELEV') or 'RAMP' in e['name']:continue
 line=LineString(np.array(e['points'])[:,:2])
 for side in ['left','right']:
  for line2 in shapely.get_parts(line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)):
   if line2.geom_type=='LineString':goals.append((e['region'],e['name']+'_'+side,line2))
paths=[]
def astar_route(start,end,allowed):
 bounds=box(min(start[0],end[0])-35,min(start[1],end[1])-35,max(start[0],end[0])+35,max(start[1],end[1])+35)
 nav=allowed.intersection(bounds).buffer(-.62,join_style=2);shapely.prepare(nav);step=2.;target=np.array(end);origin=np.array(start);cost={(0,0):0};prev={};todo=[(float(np.linalg.norm(target-origin)),0.,(0,0))];closed=set();found=None
 for iteration in range(18000):
  if not todo:break
  _,dist,key=heapq.heappop(todo)
  if key in closed:continue
  closed.add(key);q=origin+np.array(key)*step
  if np.linalg.norm(q-target)<3.1 and nav.covers(LineString([q,target])):found=key;break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   k=(key[0]+dx,key[1]+dy)
   if k in closed:continue
   q2=origin+np.array(k)*step
   if not nav.covers(LineString([q,q2])):continue
   v=dist+step*math.hypot(dx,dy)
   if v>=cost.get(k,1e10):continue
   cost[k]=v;prev[k]=key;heapq.heappush(todo,(v+float(np.linalg.norm(q2-target)),v,k))
 if found is None:return None
 points=[target.tolist()];key=found
 while key!=(0,0):points.append((origin+np.array(key)*step).tolist());key=prev[key]
 points.append(origin.tolist());route=LineString(points[::-1]);simple=route.simplify(.45)
 return simple if allowed.buffer(.03).covers(simple.buffer(.6,cap_style=2,join_style=2)) else route
for rec in sites:
 poly=rec['poly'];normal=np.array(rec['outward']);center=np.array(rec['center']);edge=poly.boundary.intersection(LineString([center,center+normal*100.]));tip=np.array(list(edge.coords)[-1]);start=tip+normal*.65;blocked=unary_union([fixedshape.buffer(.45),reserve.buffer(.5)]+[s['poly'].buffer(.55,join_style=2) for s in sites if s['name']!=rec['name']]);allowed=lands[rec['region']].difference(blocked).difference(carriage).difference(poly)
 options=[]
 for _,gn,g in sorted([g for g in goals if g[0]==rec['region']],key=lambda g:g[2].distance(Point(start)))[:16]:
  end=np.array(g.interpolate(g.project(Point(start))).coords[0]);gz=walkfield.height(end)
  if gz is None:continue
  bends=[[],[start+normal*4],[[start[0],end[1]]],[[end[0],start[1]]]]
  for mids in bends:
   route=LineString([start,*mids,end]);corr=route.buffer(.60,cap_style=2,join_style=2)
   if route.length<.2 or route.length>100 or not allowed.buffer(.03).covers(corr):continue
   grade=abs(rec['floor']-.025-gz)/route.length
   if grade>.22:continue
   options.append((route.length+grade*12,route,corr,float(gz),gn))
 if not options:
  # A shared courtyard can require a short dogleg around a neighbor.
  for _,gn,g in sorted([g for g in goals if g[0]==rec['region']],key=lambda g:g[2].distance(Point(start)))[:8]:
   end=np.array(g.interpolate(g.project(Point(start))).coords[0]);gz=walkfield.height(end)
   if gz is None:continue
   for side in [-1,1]:
    tangent=np.array([-normal[1],normal[0]])*side
    for step in [4,8,12,18,25]:
     mid=start+normal*2+tangent*step;route=LineString([start,start+normal*2,mid,end]);corr=route.buffer(.6,cap_style=2,join_style=2)
     if route.length>115 or not allowed.buffer(.03).covers(corr):continue
     if abs(rec['floor']-.025-gz)/route.length>.22:continue
     options.append((route.length+3,route,corr,float(gz),gn))
 if not options:
  seen=set()
  for _,gn,g in sorted([g for g in goals if g[0]==rec['region']],key=lambda g:g[2].distance(Point(start))):
   if gn in seen:continue
   seen.add(gn)
   if len(seen)>10:break
   end=np.array(g.interpolate(g.project(Point(start))).coords[0]);gz=walkfield.height(end)
   if gz is None or np.linalg.norm(end-start)>120:continue
   route=astar_route(start,end,allowed)
   if route is None or route.length>150 or abs(rec['floor']-.025-gz)/route.length>.22:continue
   options.append((route.length,route,route.buffer(.6,cap_style=2,join_style=2),float(gz),gn));break
 assert options,('no pedestrian route',rec['name'],start.tolist())
 _,route,corr,gz,gn=min(options,key=lambda x:x[0]);full=LineString([tip,*list(route.coords)]);rec['front']=tip.tolist();paths.append({'name':rec['name']+'_Entrance','building':rec['name'],'route':full,'polygon':full.buffer(.65,cap_style=2,join_style=2),'floor':rec['floor']-.025,'goal_z':gz,'street':gn,'region':rec['region']});print('ACCESS',rec['name'],round(full.length,1),gn,flush=True)
# Grade every path through the pad boundaries and shared intersections. A linear
# height ramp starting at a doorway would otherwise drop abruptly after its pad.
for w in paths:
 knots={0.:w['floor'],w['route'].length:w['goal_z']}
 for s in sites:
  intersection=w['route'].intersection(s['pad'])
  for piece in shapely.get_parts(intersection):
   if piece.is_empty or piece.geom_type not in ['Point','LineString']:continue
   q=list(piece.coords)
   for pt in [q[0],q[-1]]:
    distance=w['route'].project(Point(pt));knots[float(distance)]=s['floor']-.025
 w['profile']=sorted([[float(k),float(v)] for k,v in knots.items()])
def path_height(w,dist):return float(np.interp(dist,np.array(w['profile'])[:,0],np.array(w['profile'])[:,1]))
junctions={}
for i,a in enumerate(paths):
 for j,b in enumerate(paths[:i]):
  for part in shapely.get_parts(a['route'].intersection(b['route'])):
   if part.is_empty or part.geom_type not in ['Point','LineString']:continue
   qq=list(part.coords)
   for q in [qq[0],qq[-1]]:
    key=tuple(round(float(v),5) for v in q);junctions.setdefault(key,set()).update([i,j])
for q,indices in junctions.items():
 pt=Point(q);owners=[s for s in sites if s['pad'].buffer(.0001).covers(pt)]
 z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.025 if owners else float(np.mean([path_height(paths[i],paths[i]['route'].project(pt)) for i in indices]))
 for i in indices:
  w=paths[i];ss=w['route'].project(pt);w['profile']=[row for row in w['profile'] if abs(row[0]-ss)>.001]+[[float(ss),z]];w['profile'].sort()
# Graded courtyards and entrances are cut into the old terrain, avoiding stacked coplanar slabs.
courts={g['id']:Polygon(g['court']) for g in layout['groups']};patches={};holes=unary_union([s['poly'].buffer(.035,join_style=2) for s in sites]);aprons=unary_union([w['polygon'] for w in paths]);raw=unary_union([s['pad'].buffer(8,join_style=2) for s in sites]+[Polygon(b['footprint']).buffer(3,join_style=2) for b in layout['removed_placeholder_lots']]+list(courts.values())+[w['polygon'].buffer(3,join_style=2) for w in paths]);allland=unary_union(list(lands.values()));patch=raw.intersection(allland).difference(roads.difference(aprons)).difference(carriage).difference(fixedshape.buffer(.02,join_style=2)).difference(reserve).difference(holes);cut=patch.union(holes)
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type')=='terrain':clip_ground(o,cut)
 elif o.type=='MESH' and o.get('surface_type')=='sidewalk':clip_ground(o,cut.intersection(aprons))
 elif o.type=='MESH' and o.get('surface_type')=='terrain_cut_retaining_wall':
  xyz=co(o);keep=[not cut.buffer(.04).covers(Point(xyz[list(f.vertices),:2].mean(0))) for f in o.data.polygons]
  if not all(keep):keep_faces(o,keep)
cache={}
def groundz(q):
 key=tuple(round(float(x),5) for x in q)
 if key in cache:return cache[key]
 pt=Point(q);z=nearest(soil,q)
 for s in sites:
  d=pt.distance(s['pad'])
  if d<8:t=1-d/8;t=t*t*(3-2*t);z=z*(1-t)+(s['floor']-.025)*t
 nearby=[(pt.distance(w['route']),w) for w in paths]
 if nearby:
  d,w=min(nearby,key=lambda q:q[0]);d=max(0.,d-.65)
  if d<3:
   h=path_height(w,w['route'].project(pt));t=1-d/3;t=t*t*(3-2*t);z=z*(1-t)+h*t
 owners=[s for s in sites if s['pad'].covers(pt)]
 if owners:z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.025
 cache[key]=z;return z
vp={d:[] for d in ids};fp={d:[] for d in ids};mi={d:[] for d in ids};pathlines=[shapely.segmentize(w['route'],.75) for w in paths];pathtree=shapely.STRtree(pathlines)
for reg,land in lands.items():
 shape=patch.intersection(land)
 if shape.is_empty:continue
 xmin,ymin,xmax,ymax=shape.bounds
 xgrid=sorted(set(np.arange(math.floor(xmin/3)*3,xmax+3,3).tolist()+[v for s in sites if s['region']==reg for v in [s['poly'].bounds[0],s['poly'].bounds[2],s['pad'].bounds[0],s['pad'].bounds[2]]]))
 ygrid=sorted(set(np.arange(math.floor(ymin/3)*3,ymax+3,3).tolist()+[v for s in sites if s['region']==reg for v in [s['poly'].bounds[1],s['poly'].bounds[3],s['pad'].bounds[1],s['pad'].bounds[3]]]))
 for x,xn in zip(xgrid,xgrid[1:]):
  for y,yn in zip(ygrid,ygrid[1:]):
   if xn-x<1e-6 or yn-y<1e-6:continue
   tile=box(x,y,xn,yn)
   if not shape.intersects(tile):continue
   inside=shape.intersection(tile);lines=[pathlines[int(i)].intersection(inside) for i in pathtree.query(tile)];pieces=list(polygonize(unary_union([inside.boundary]+lines))) if lines else [inside]
   triangles=[]
   for face in pieces:
    if face.is_empty or not inside.covers(face.representative_point()):continue
    triangles.extend(shapely.get_parts(shapely.constrained_delaunay_triangles(face)))
   for t in triangles:
    xy=np.array(t.exterior.coords)[:3]
    if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
    mid=xy.mean(0);d=district(mid);assert d in ids;k=len(vp[d]);vp[d].extend([[*q,groundz(q)] for q in xy]);fp[d].append([k,k+1,k+2]);pt=Point(mid)
    paved=any(s['pad'].covers(pt) for s in sites) or any(w['polygon'].covers(pt) for w in paths)
    if reg=='EAST':mat=2
    else:mat=1 if paved or (reg=='MAIN' and mid[1]>700) else 0
    mi[d].append(mat)
for d in ids:
 o=newmesh(f'V19_Graded_Ground_{d:02}',vp[d],fp[d],soilmat,d,{'surface_type':'terrain','walkable_surface':True});o.data.materials.append(pavemat);o.data.materials.append(gravel);o.data.polygons.foreach_set('material_index',np.array(mi[d],np.int32))
for rec in sites:
 poly=rec['poly'].buffer(.035,join_style=2);xy=np.array(shapely.orient_polygons(poly).exterior.coords)[:-1];n=len(xy);bottom=min([nearest(soil,q) for q in xy]+[rec['floor']-.4])-.15;v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,rec['floor']-.018)]];f=[]
 for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
 newmesh(rec['name']+'_Foundation',v.tolist(),f,base,rec['district_id'],{'site_building':rec['name'],'is_site_foundation':True})
# Small planted islands are native low-polygon geometry; excluded from the building budget.
plantings=[]
for group in layout['groups']:
 green=Polygon(group['court']).difference(holes.buffer(1.7)).difference(aprons.buffer(1.1)).difference(roads.buffer(.5)).difference(fixedshape.buffer(1))
 minx,miny,maxx,maxy=green.bounds
 rng=np.random.default_rng(1900+len(plantings));wanted={'NT_WEST_COURT':16,'NT_EAST_COURT':10,'NT_MIXED_PROMENADE':6,'WEST_GARDEN_LANES':7,'EAST_LOADING_COURT':0}[group['id']];chosen=[]
 for attempt in range(500):
   if len(chosen)>=wanted:break
   x=float(rng.uniform(minx+2,maxx-2));y=float(rng.uniform(miny+2,maxy-2))
   # Three loose clusters and clear walkways replace the artificial tree grid.
   if not green.covers(Point(x,y).buffer(1.5)) or any(math.hypot(x-q[0],y-q[1])<6.5 for q in chosen):continue
   chosen.append([x,y]);z=groundz([x,y]);d=district([x,y]);size=float(rng.uniform(3.2,4.6))
   bpy.ops.mesh.primitive_cone_add(vertices=7,radius1=.16,radius2=.12,depth=size*.8,location=(x,y,z+size*.4));trunk=bpy.context.object;trunk.name=f'V19_Tree_{len(plantings):03}_Trunk';trunk.data.materials.append(bark)
   bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=size*.5,location=(x,y,z+size));canopy=bpy.context.object;canopy.scale=(1,1,1.3);canopy.name=f'V19_Tree_{len(plantings):03}_Canopy';canopy.data.materials.append(leafmat)
   for o in [trunk,canopy]:o.parent=roots[d];o['district_id']=d;o['layout_group']=group['id'];o['landscape_only']=True;o['modified_in_version']='v19'
   plantings.append({'group':group['id'],'xy':[float(x),float(y)],'z':z})
newreal=[]
for rec in sites:
 b={k:v for k,v in rec.items() if k not in ['poly','pad','initial_center']};b['instance_name']=b['instance_id'];b['modified_in_version']='v19';b['uniform_scale']=b['scale'];b['source_asset_id']=b['asset_id'];newreal.append(b)
p['real_buildings'].extend(newreal);p['access_v19']=[{k:list(v.exterior.coords) if k=='polygon' else list(v.coords) if k=='route' else v for k,v in w.items()} for w in paths]
p['urban_areas_v19']={'groups':layout['groups'],'removed_placeholders':sorted(removed),'new_instances':[r['instance_name'] for r in newreal],'building_count_before':old['stats']['buildings'],'building_count_after':layout['city_building_units'],'plantings':plantings,'layout_inspiration':{'S05':'vary skyline heights and group buildings around streets','S06':'continuous corner street walls and internal yards','S04':'mixed service shop types and industrial courts','S07':'fine pedestrian passages; do not copy low-resolution near-view textures'}}
nt=p['urban_areas_v18']['new_town'];boundary=Polygon(nt['polygon']);inside=[r for r in p['real_buildings'] if boundary.covers(Polygon(r['footprint_xy']))];nt['original_placeholder_lots_v18']=nt['existing_residential_lots'];nt['existing_residential_lots']=[b['name'] for b in p['buildings'] if b['zone']=='RESIDENTIAL' and boundary.covers(Polygon(b['footprint']))];nt['existing_residential_units']=len(nt['existing_residential_lots']);nt['new_source_buildings']=[r['instance_name'] for r in inside];nt['new_source_building_units']=len(inside);nt['building_units']=len(inside)+nt['existing_residential_units'];nt['future_parcels_are_unbuilt']=False;nt['updated_in_version']='v19'
for parcel in nt['land_use_parcels']:
 if parcel['role']=='residential':parcel['status']='redeveloped_v19'
 if parcel['role']=='mixed_use':parcel['status']='partly_developed_v19';parcel['built_instances']=[r['instance_name'] for r in newreal if Polygon(parcel['polygon']).intersects(Polygon(r['footprint_xy']))]
cnt=collections.Counter(b['zone'] for b in p['buildings']);cnt.update(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN') for r in p['real_buildings']);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),building_count_by_zone=dict(cnt),source_asset_types=len({r['file'] for r in p['real_buildings']}),new_town_buildings=nt['building_units']);p['schema']='hero13.city.extracted-neighborhoods.v19';p['sources']['regional_update_v19']='delivery/city_updates/v19_20261030/tools/build_v19.py'
assert p['stats']['buildings']==layout['city_building_units']<700 and cnt['OLDTOWN']==200
after={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'};report={'version':'v19','baseline_commit':layout['baseline_commit'],'districts':ids,'city_buildings':p['stats']['buildings'],'removed_placeholders':sorted(removed),'new_asset_instances':len(sites),'new_asset_types':len(templates),'oldtown_street_buildings':120,'oldtown_rear_buildings':80,'removed_massing_faces':removed_faces,'ground_patch_m2':patch.area,'unchanged_original_objects':{n:h for n,h in before.items() if after.get(n)==h},'changed_original_objects':[n for n,h in before.items() if n in after and after[n]!=h],'removed_original_objects':sorted(set(before)-set(after)),'new_objects':sorted(set(after)-set(before))}
(R/'model').mkdir(exist_ok=True);(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(R/'model/site_levels.json').write_text(json.dumps([{k:list(v.exterior.coords) if k in ['poly','pad'] else v for k,v in s.items()} for s in sites],ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v19.blend'),compress=True);print('V19_BUILD_DONE',p['stats']['buildings'],len(sites),len(templates),len(plantings),flush=True)
