"""Build street-facing infill and continuous streets in the four changed districts."""
import sys,json,math,collections,copy
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'));sys.path.insert(0,str(R/'base_tools'))
import bpy,numpy as np,shapely
from mathutils import Vector,Matrix
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
from surface_utils import co,fingerprint,keep_faces,clip_ground
layout=json.load(open(R/'layout.json'));p=json.load(open(R/'baseline/city_plan.json'));old=copy.deepcopy(p);cat={a['asset_id']:a for a in json.load(open(R/'asset_catalog.json'))};ids=layout['changed_district_ids']
bpy.ops.wm.read_factory_settings(use_empty=True)
for d in ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02}_*.glb'))))
bpy.context.view_layer.update();sc=bpy.context.scene
for o in list(sc.objects):
 if o.type=='MESH':
  m=o.data.copy();m.transform(o.matrix_world);m.update();o.parent=None;o.data=m;o.matrix_world=Matrix.Identity(4)
for o in list(sc.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
roots={}
for d in ids:o=bpy.data.objects.new(f'District_{d:02}',None);sc.collection.objects.link(o);o['district_id']=d;roots[d]=o
for o in list(sc.objects):
 if o.type=='MESH':o.parent=roots[int(o['district_id'])]
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);streetfield=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type') in ['pavement','road_kit']]);walkfield=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 hit,_,idx,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=field.tri[idx];w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1]);return float(w@tri[:,2])
def district(q):
 if q[0]<-430 and q[1]<-300:return 9 if q[0]<-950 else 10
 return 4 if q[1]<620 else 8
removed={b['name'] for b in layout['removed_placeholder_lots']};lotpolys=[Polygon(b['footprint']) for b in old['buildings']];lot_tree=shapely.STRtree(lotpolys);removed_faces=0
for o in list(sc.objects):
 if o.type!='MESH':continue
 source=o.get('source_object',o.name)
 if any(n in source for n in removed):bpy.data.objects.remove(o,do_unlink=True);continue
 if o.get('is_placeholder'):
  xyz=co(o);keep=[];owners=set()
  for f in o.data.polygons:
   pt=Point(xyz[list(f.vertices),:2].mean(0));i=int(lot_tree.nearest(pt));owner=old['buildings'][i]['name'];assert pt.distance(lotpolys[i])<.12,(o.name,owner);keep.append(owner not in removed)
   if owner not in removed:owners.add(owner)
  if not all(keep):
   removed_faces+=len(keep)-sum(keep);name=o.name;keep_faces(o,keep)
   if name in sc.objects:sc.objects[name]['placeholder_lot_count']=len(owners);sc.objects[name]['modified_in_version']='v20'
p['buildings']=[b for b in p['buildings'] if b['name'] not in removed]
for k,v in list(p.items()):
 if k.startswith('access_') and isinstance(v,list):p[k]=[w for w in v if w.get('building',w.get('name')) not in removed]
oldfull=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2,join_style=2) for e in p['edges']]);oldcar=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2,join_style=2) for e in p['edges']]);lands=unary_union([Polygon(v) for v in p['coasts'].values()]);fixed=unary_union([Polygon(b.get('footprint',b.get('footprint_xy'))) for b in p['buildings']+p['real_buildings']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
newroads=[]
for r in layout['new_roads']:
 rec=copy.deepcopy(r);rec['line']=LineString(r['points']);rec['full']=rec['line'].buffer(r['width']/2,join_style=2);rec['car']=rec['line'].buffer(r['carriage_width']/2,join_style=2);line=rec['line'];ss=np.linspace(0,line.length,max(3,int(line.length/3)+1));zz=[]
 for s in ss:
  q=line.interpolate(s);base=nearest(soil,q.coords[0])+.02;d=q.distance(oldcar)
  if d<15:
   z=nearest(streetfield,q.coords[0]);t=max(0,1-d/15);base=base*(1-t)+z*t
  zz.append(base)
 rec['profile']=[ss.tolist(),zz];newroads.append(rec)
# Shared branch junctions use exactly the through-street elevation.
for i,r in enumerate(newroads):
 for a in newroads[:i]:
  x=r['line'].intersection(a['line'])
  for q in shapely.get_parts(x):
   if q.geom_type!='Point':continue
   s=r['line'].project(q);z=float(np.interp(a['line'].project(q),*a['profile']));idx=min(range(len(r['profile'][0])),key=lambda k:abs(r['profile'][0][k]-s));r['profile'][0][idx]=s;r['profile'][1][idx]=z
newfull=unary_union([r['full'] for r in newroads]);newcar=unary_union([r['car'] for r in newroads]);allcar=oldcar.union(newcar)
def roadz(q):
 pt=Point(q);z=streetfield.height(q) if oldcar.buffer(.0002).covers(pt) else None
 if z is not None:return z
 r=min(newroads,key=lambda r:pt.distance(r['line']));return float(np.interp(r['line'].project(pt),*r['profile']))
def material(n,c):
 m=bpy.data.materials.new(n);m.use_nodes=True;bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=.85;return m
mats={'land':material('V20_Landscape',(.34,.41,.25)),'walk':material('V20_Pavers',(.51,.50,.45)),'asphalt':material('V20_Asphalt',(.075,.082,.085)),'curb':material('V20_Concrete_Curb',(.58,.58,.53)),'foundation':material('V20_Foundation',(.48,.47,.42)),'white':material('V20_Road_White',(.84,.83,.72)),'yellow':material('V20_Road_Yellow',(.78,.57,.13)),'steel':material('V20_Public_Steel',(.11,.15,.15)),'wood':material('V20_Timber',(.31,.18,.09)),'pole':material('V20_Utility_Pole',(.43,.42,.36)),'wire':material('V20_Cable',(.035,.04,.042)),'bark':material('V20_Tree_Bark',(.23,.15,.08))}
leaves=[material('V20_Leaf_'+str(i),c) for i,c in enumerate([(.12,.25,.07),(.20,.32,.10),(.15,.29,.11)])]
def newmesh(n,v,f,mat,d=None,props=None):
 if not f:return None
 if d is None:d=district(np.mean(np.asarray(v),axis=0))
 me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.materials.append(mat);me.update();o=bpy.data.objects.new(n,me);sc.collection.objects.link(o);o.parent=roots[d];o['district_id']=d;o['source_object']=n;o['modified_in_version']='v20'
 for k,x in (props or {}).items():o[k]=x
 return o
templates={}
for aid in sorted({b['asset_id'] for b in layout['placements']}):
 start=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(R/'extracted'/cat[aid]['file']));bpy.context.view_layer.update();obs=set(sc.objects)-start;meshes=[]
 for o in obs:
  if o.type=='MESH':m=o.data.copy();m.transform(o.matrix_world);m.update();meshes.append((o.name,m))
 for o in obs:bpy.data.objects.remove(o,do_unlink=True)
 templates[aid]=meshes
sites=[]
for b in layout['placements']:
 poly=Polygon(b['footprint_xy']);pad=poly.buffer(1.0,join_style=2);sample=shapely.segmentize(poly.exterior,2.5);zs=[nearest(soil,q) for q in sample.coords];floor=max(zs)+.04
 roadpoint=min(newroads,key=lambda r:r['line'].distance(poly)).get('line');frontvec=np.array(b['outward']);center=np.array(b['center']);hit=poly.boundary.intersection(LineString([center,center+frontvec*100]));tip=np.array(list(hit.coords)[-1]);floor=max(floor,roadz(tip)+.14)
 rec={**b,'floor':floor,'poly':poly,'pad':pad,'front':tip.tolist()};sites.append(rec);M=Matrix.Translation((*b['center'],floor))@Matrix.Rotation(math.radians(b['rotation_deg']),4,'Z')@Matrix.Diagonal((b['scale'],b['scale'],b['scale'],1))
 for i,(sn,m) in enumerate(templates[b['asset_id']]):
  o=bpy.data.objects.new(f"{b['instance_id']}__Part{i:03}",m);sc.collection.objects.link(o);o.parent=roots[b['district_id']];o.matrix_world=M
  for k,v in dict(district_id=b['district_id'],asset_id=b['asset_id'],instance_id=b['instance_id'],source_instance=b['instance_id'],source_filename=b['source_filename'],source_node_name=b['source_node_name'],source_mesh_name=sn,replaces_lots='|'.join(b['replaces']),layout_group=b['group'],added_in_version='v20').items():o[k]=v
 print('BUILDING',b['instance_id'],round(floor,3),flush=True)
newpolys=unary_union([s['poly'] for s in sites]);paths=[]
goals=[]
for r in newroads:
 for side in ['left','right']:
  for g in shapely.get_parts(r['line'].parallel_offset(r['carriage_width']/2+r['sidewalk_width']*.55,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((r['region'],r['name'],g))
for e in old['edges']:
 if e.get('bridge') or e['layer'].startswith('ELEV') or 'RAMP' in e['name']:continue
 for side in ['left','right']:
  for g in shapely.get_parts(LineString(np.array(e['points'])[:,:2]).parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((e['region'],e['name'],g))
for s in sites:
 start=np.array(s['front']);normal=np.array(s['outward']);options=[]
 for reg,name,g in sorted([g for g in goals if g[0]==s['region']],key=lambda g:g[2].distance(Point(start)))[:18]:
  end=np.array(g.interpolate(g.project(Point(start))).coords[0]);dist=np.linalg.norm(end-start)
  if dist<.1 or dist>100:continue
  blockers=fixed.union(unary_union([q['poly'].buffer(.2) for q in sites if q['name']!=s['name']]))
  choices=[([],end),([start+normal*2],end),([[start[0],end[1]]],end),([[end[0],start[1]]],end)]
  tangent=np.array([-normal[1],normal[0]])
  for sign in [-1,1]:
   for step in [3,5,8,12]:
    mid=start+normal*.75+tangent*step*sign;end2=np.array(g.interpolate(g.project(Point(mid))).coords[0]);choices.append(([start+normal*.75,mid],end2))
  for mids,target in choices:
   line=LineString([start,*mids,target]);band=line.buffer(.60,cap_style=2,join_style=2)
   if band.intersection(blockers).area>.01 or band.intersection(allcar).area>.01:continue
   ze=walkfield.height(target)
   if newfull.buffer(.05).covers(Point(target)):ze=roadz(target)+.12
   if ze is None:continue
   if abs(s['floor']-.02-ze)/line.length>.22:continue
   options.append((line.length,line,band,float(ze),name))
 assert options,('no safe entrance',s['name'])
 _,line,band,zend,name=min(options,key=lambda x:x[0]);profile=[[0,s['floor']-.02],[min(1.2,line.length*.6),s['floor']-.02],[line.length,zend]];paths.append(dict(name=s['name']+'_Entrance',building=s['name'],route=line,polygon=band,profile=profile,region=s['region'],street=name))
 print('ENTRANCE',s['name'],round(line.length,2),flush=True)
holes=unary_union([s['poly'].buffer(.035,join_style=2) for s in sites]);raw=unary_union([s['pad'].buffer(6,join_style=2) for s in sites]+[Polygon(b['footprint']).buffer(3) for b in layout['removed_placeholder_lots']]+[newfull.buffer(5)]+[w['polygon'].buffer(2) for w in paths]);raw=raw.intersection(lands).difference(fixed.buffer(.03)).difference(reserve)
asphalt=newcar.difference(oldcar);walk=newfull.difference(newcar).difference(oldfull);rest=raw.difference(newfull).difference(oldfull).difference(holes);aprons=unary_union([w['polygon'] for w in paths]);walk=walk.union(aprons.difference(oldcar).difference(newcar)).difference(holes);rest=rest.difference(walk)
cut=rest.union(walk).union(asphalt).union(holes)
for o in list(sc.objects):
 if o.type!='MESH':continue
 st=o.get('surface_type')
 if st=='terrain':clip_ground(o,cut)
 elif st=='sidewalk':clip_ground(o,asphalt.union(aprons))
 elif st in ['curb','terrain_cut_retaining_wall','road_cut_retaining_wall']:
  xyz=co(o);hitshape=asphalt.buffer(.22) if st=='curb' else cut.buffer(.05);keep=[]
  for f in o.data.polygons:
   q=xyz[list(f.vertices),:2].mean(0);keep.append(not hitshape.covers(Point(q)))
  if not all(keep):keep_faces(o,keep)
cache={}
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def groundz(q):
 key=tuple(round(float(x),6) for x in q)
 if key in cache:return cache[key]
 pt=Point(q);z=nearest(soil,q);r=min(newroads,key=lambda r:pt.distance(r['line']));distance=pt.distance(r['line']);outer=r['width']/2
 if distance<outer+5:
  t=smooth(1-max(0,distance-outer)/5);rz=roadz(q)+(.12 if not newcar.covers(pt) else 0);z=z*(1-t)+rz*t
 for s in sites:
  d=pt.distance(s['pad'])
  if d<6:t=smooth(1-d/6);z=z*(1-t)+(s['floor']-.02)*t
 for w in paths:
  d=pt.distance(w['route'])
  if d<2.65:
   ss=w['route'].project(pt);pr=np.array(w['profile']);h=float(np.interp(ss,pr[:,0],pr[:,1]));t=smooth(1-max(0,d-.65)/2);z=z*(1-t)+h*t
 owners=[s for s in sites if s['pad'].buffer(.0001).covers(pt)]
 if owners:z=min(owners,key=lambda s:pt.distance(s['poly']))['floor']-.02
 # Preserve the original walk height on joins, including the mouths of new streets.
 if oldfull.buffer(.03).covers(pt) and not asphalt.buffer(.001).covers(pt):
  wz=walkfield.height(q)
  if wz is not None:z=wz
 cache[key]=z;return z
def surface(name,shape,fn,mat,stype,step=4):
 vv={d:[] for d in ids};ff={d:[] for d in ids}
 for part in shapely.get_parts(shape):
  if part.is_empty or part.area<1e-7:continue
  x0,y0,x1,y1=part.bounds;xs=sorted(set(np.arange(math.floor(x0/step)*step,x1+step,step).tolist()+[-950.]));ys=sorted(set(np.arange(math.floor(y0/step)*step,y1+step,step).tolist()+[620.]));xs=[x for x in xs if x0-step<=x<=x1+step];ys=[y for y in ys if y0-step<=y<=y1+step]
  for x,xn in zip(xs,xs[1:]):
   for y,yn in zip(ys,ys[1:]):
    tile=box(x,y,xn,yn)
    if not part.intersects(tile):continue
    inside=part.intersection(tile)
    for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(inside)):
     xy=np.array(tri.exterior.coords)[:3]
     if abs(np.linalg.det(np.c_[xy,np.ones(3)]))<1e-9:continue
     if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
     d=district(xy.mean(0));assert d in ids,(name,d,xy.mean(0));k=len(vv[d]);vv[d].extend([[float(a),float(b),float(fn([a,b]))] for a,b in xy]);ff[d].append([k,k+1,k+2])
 for d in ids:newmesh(f'{name}_{d:02}',vv[d],ff[d],mat,d,dict(surface_type=stype,walkable_surface=True))
 print('SURFACE',name,round(shape.area,1),sum(len(v) for v in ff.values()),flush=True)
surface('V20_Graded_Land',rest,groundz,mats['land'],'terrain',4)
surface('V20_New_Street_Walks',walk,groundz,mats['walk'],'sidewalk',2.5)
surface('V20_New_Street_Asphalt',asphalt,roadz,mats['asphalt'],'pavement',2.5)
for s in sites:
 xy=np.array(shapely.orient_polygons(s['poly'].buffer(.035,join_style=2)).exterior.coords)[:-1];n=len(xy);bottom=min([nearest(soil,q) for q in xy]+[s['floor']-.3])-.12;v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,s['floor']-.018)]];faces=[]
 for i in range(1,n-1):faces.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;faces.extend([[i,j,j+n],[i,j+n,i+n]])
 newmesh(s['name']+'_Foundation',v.tolist(),faces,mats['foundation'],s['district_id'],dict(site_building=s['name'],is_site_foundation=True))
# New curbs are interrupted at every junction; their tops share the sidewalk height.
for bi,line in enumerate(shapely.get_parts(newcar.boundary.difference(oldfull.buffer(.12)))):
 if line.geom_type!='LineString':continue
 xy=np.array(shapely.segmentize(line,2).coords);v=[];f=[]
 for q in xy:v.extend([[*q,roadz(q)+.005],[*q,roadz(q)+.12]])
 for i in range(len(xy)-1):f.extend([[2*i,2*i+2,2*i+3],[2*i,2*i+3,2*i+1]])
 for d in ids:
  fs=[x for x in f if district(np.array(v)[x,:2].mean(0))==d]
  if fs:newmesh(f'V20_Curb_{bi:02}_{d:02}',v,fs,mats['curb'],d,dict(surface_type='curb'))
# Clear two-way markings, stop lines and pedestrian crossings.
markings=[]
def mark(name,shape,mat,offset=.015):
 if shape.is_empty:return
 surface(name,shape,lambda q:roadz(q)+offset,mat,'road_marking',4);markings.append(name)
for ri,r in enumerate(newroads):
 line=r['line'];other=unary_union([q['car'].buffer(6) for q in newroads if q is not r]).union(oldfull.buffer(9))
 if r['carriage_width']>=6:
  for ss in np.arange(12,line.length-10,8):
   sub=shapely.ops.substring(line,ss,min(ss+3,line.length));shape=sub.buffer(.065,cap_style=2).difference(other);mark(f'V20_CenterDash_{ri}_{int(ss):03}',shape,mats['yellow'])
 for end in [False,True]:
  ss=13 if not end else line.length-13;q=np.array(line.interpolate(ss).coords[0]);t=np.array(line.interpolate(ss+.5).coords[0])-np.array(line.interpolate(ss-.5).coords[0]);t/=np.linalg.norm(t);normal=np.array([-t[1],t[0]])
  if Point(q).distance(oldfull)>16:continue
  for delta in np.arange(-2.2,2.3,1.1):
   c=q+t*delta;shape=LineString([c-normal*(r['carriage_width']/2-.55),c+normal*(r['carriage_width']/2-.55)]).buffer(.26,cap_style=2).intersection(newcar).difference(oldcar);mark(f'V20_Crosswalk_{ri}_{int(end)}_{int((delta+3)*10)}',shape,mats['white'],.019)
print('ROAD_GEOMETRY_DONE',flush=True)
# Furniture templates are native low-polygon meshes; instances share mesh data.
props=[];rng=np.random.default_rng(20030);templates_public={}
def boxpart(v,f,c,size):
 x,y,z=c;a,b,h=np.array(size)/2;k=len(v);v.extend([[x+sx*a,y+sy*b,z+sz*h] for sz in [-1,1] for sy in [-1,1] for sx in [-1,1]]);f.extend([[k+i for i in face] for face in [[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]]])
def cylinder(v,f,a,b,r,n=8):
 a=np.array(a);b=np.array(b);z=b-a;z/=np.linalg.norm(z);u=np.cross(z,[0,0,1])
 if np.linalg.norm(u)<.01:u=np.array([1.,0,0])
 u/=np.linalg.norm(u);w=np.cross(z,u);k=len(v)
 for c in [a,b]:
  for t in np.linspace(0,2*math.pi,n,endpoint=False):v.append((c+r*(math.cos(t)*u+math.sin(t)*w)).tolist())
 f.append([k+i for i in range(n-1,-1,-1)]);f.append([k+n+i for i in range(n)])
 for i in range(n):j=(i+1)%n;f.append([k+i,k+j,k+j+n,k+i+n])
def template(kind):
 if kind in templates_public:return templates_public[kind]
 pieces=[]
 if kind=='utility_pole':
  v=[];f=[];cylinder(v,f,[0,0,0],[0,0,8.4],.135,10);boxpart(v,f,[0,0,7.9],[2.0,.16,.16]);pieces.append((v,f,mats['pole']));v=[];f=[]
  for x in [-.72,0,.72]:cylinder(v,f,[x,0,7.96],[x,0,8.18],.065,8)
  pieces.append((v,f,mats['steel']))
 elif kind=='street_lamp':
  v=[];f=[];cylinder(v,f,[0,0,0],[0,0,6.7],.085);cylinder(v,f,[0,0,6.55],[0,1.1,6.85],.055);boxpart(v,f,[0,1.22,6.8],[.35,.7,.14]);pieces.append((v,f,mats['steel']))
 elif kind=='bench':
  v=[];f=[]
  for y in [-.22,-.075,.075,.22]:boxpart(v,f,[0,y,.46],[1.8,.12,.07])
  for z in [.7,.9]:boxpart(v,f,[0,.25,z],[1.8,.07,.13])
  pieces.append((v,f,mats['wood']));v=[];f=[]
  for x in [-.68,.68]:boxpart(v,f,[x,0,.24],[.07,.53,.44]);boxpart(v,f,[x,.25,.7],[.07,.07,.58])
  pieces.append((v,f,mats['steel']))
 elif kind=='bin':
  v=[];f=[];cylinder(v,f,[0,0,0],[0,0,.9],.27,10);pieces.append((v,f,mats['steel']))
 elif kind=='bollard':
  v=[];f=[];cylinder(v,f,[0,0,0],[0,0,.8],.085);pieces.append((v,f,mats['steel']))
 elif kind=='tree':
  v=[];f=[];cylinder(v,f,[0,0,0],[0,0,4.2],.14);pieces.append((v,f,mats['bark']))
  for i,c in enumerate([[0,0,4.7],[.8,.35,4.35],[-.7,-.25,4.1]]):
   bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1.55,location=c);ob=bpy.context.object;me=ob.data.copy();me.transform(ob.matrix_world);v=[v.co[:] for v in me.vertices];f=[p.vertices[:] for p in me.polygons];bpy.data.objects.remove(ob,do_unlink=True);pieces.append((v,f,leaves[i]))
 elif kind=='shrub':
  v=[];f=[];boxpart(v,f,[0,0,.22],[2.3,1.2,.44]);pieces.append((v,f,mats['curb']));bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(0,0,.7));o=bpy.context.object;o.scale=(1.05,.52,.5);bpy.context.view_layer.update();me=o.data.copy();me.transform(o.matrix_world);pieces.append(([v.co[:] for v in me.vertices],[f.vertices[:] for f in me.polygons],leaves[1]));bpy.data.objects.remove(o,do_unlink=True)
 out=[]
 for i,(v,f,m) in enumerate(pieces):
  me=bpy.data.meshes.new('V20_'+kind+f'_{i:02}');me.from_pydata(v,[],f);me.materials.append(m);me.update();out.append(me)
 templates_public[kind]=out;return out
occupied=[]
def public(kind,q,angle=0,group='',scale=1):
 q=np.array(q,float);pt=Point(q);radius={'tree':1.65,'shrub':1.35,'bench':.92,'bin':.3,'utility_pole':.36,'street_lamp':.32,'bollard':.1}[kind]
 if not lands.covers(pt.buffer(radius+.15)) or fixed.buffer(radius+.5).intersects(pt) or newpolys.buffer(radius+.6).intersects(pt) or allcar.buffer(radius+.35).intersects(pt) or reserve.buffer(radius).intersects(pt):return None
 if any(pt.distance(Point(a))<radius+b+.6 for a,b in occupied):return None
 if kind not in ['bollard'] and aprons.buffer(radius+.8).intersects(pt):return None
 z=groundz(q);wz=walkfield.height(q)
 if wz is not None and not newfull.covers(pt):z=wz
 iid=f'V20-P{len(props)+1:03}';d=district(q);M=Matrix.Translation((*q,z))@Matrix.Rotation(angle,4,'Z')@Matrix.Diagonal((scale,scale,scale,1))
 for i,me in enumerate(template(kind)):
  o=bpy.data.objects.new(iid+f'__{kind}_{i:02}',me);sc.collection.objects.link(o);o.parent=roots[d];o.matrix_world=M
  for k,v in dict(district_id=d,public_instance_id=iid,public_type=kind,layout_group=group,added_in_version='v20',source_asset_id='NATIVE-V20-'+kind,source_filename='procedural_public_furniture_v20',building_count_units=0).items():o[k]=v
 props.append(dict(instance_id=iid,type=kind,center=q.tolist(),z=z,rotation_deg=math.degrees(angle),scale=scale,district_id=d,group=group,source='native low polygon geometry v20',building_count_units=0));occupied.append((q.tolist(),radius));return props[-1]
for ri,r in enumerate(newroads):
 group='WEST_MARKET_STREET' if r['region']=='WEST' else 'NT_CRESCENT_SHOPFRONTS';line=r['line'];row=[]
 for s in np.arange(22,line.length-16,27):
  q=np.array(line.interpolate(s).coords[0]);t=np.array(line.interpolate(s+1).coords[0])-np.array(line.interpolate(s-1).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]]);angle=math.atan2(t[1],t[0]);offset=r['carriage_width']/2+.7
  if r['region']=='WEST':
   a=public('utility_pole',q+n*offset,angle,group)
   if a:row.append(a)
  else:public('street_lamp',q+n*offset,angle,group)
  public('tree',q-n*(r['width']/2+2.5),angle,group,float(rng.uniform(.85,1.15)))
  if int(s)//27%2==0:public('bench',q+n*(r['width']/2+2.2),angle,group);public('bin',q+n*(r['width']/2+2.2)+t*1.8,angle,group)
 for a,b in zip(row,row[1:]):
  if np.linalg.norm(np.array(a['center'])-b['center'])>43:continue
  aa=np.array([*a['center'],a['z']+8.18]);bb=np.array([*b['center'],b['z']+8.18]);v=[];f=[]
  for offset in [-.68,.68]:
   delta=bb[:2]-aa[:2];delta/=np.linalg.norm(delta);prev=None
   for t in np.linspace(0,1,13):
    c=aa*(1-t)+bb*t;c[:2]+=delta*offset;c[2]-=4*.72*t*(1-t)
    if prev is not None:cylinder(v,f,prev,c,.018,5)
    prev=c.copy()
  iid=f'V20-C{len([x for x in props if x["type"]=="overhead_cable"])+1:02}';newmesh(iid,v,f,mats['wire'],district((aa[:2]+bb[:2])/2),dict(public_instance_id=iid,public_type='overhead_cable',source_asset_id='NATIVE-V20-overhead_cable',building_count_units=0));props.append(dict(instance_id=iid,type='overhead_cable',start=a['instance_id'],end=b['instance_id'],minimum_cable_height_m=min(aa[2]-a['z'],bb[2]-b['z'])-.72,district_id=district((aa[:2]+bb[:2])/2),group=group,building_count_units=0))
# Pocket planting follows available corner spaces rather than covering every pavement.
for group,bounds in [('NT_STEPPED_CAMPUS',(620,670,700,795)),('WEST_MARKET_STREET',(-985,-985,-818,-886)),('NT_CRESCENT_SHOPFRONTS',(627,563,908,644))]:
 count=0
 for _ in range(260):
  q=[float(rng.uniform(bounds[0],bounds[2])),float(rng.uniform(bounds[1],bounds[3]))];pt=Point(q)
  if pt.distance(newfull)>17 and group!='NT_STEPPED_CAMPUS':continue
  if public('tree' if count%4 else 'shrub',q,float(rng.uniform(-math.pi,math.pi)),group,1):count+=1
  if count>=18:break
# Short bollards define two small pedestrian corners without blocking entrances.
for r in newroads[1::2]:
 s=r['line'].length-16;q=np.array(r['line'].interpolate(s).coords[0]);t=np.array(r['line'].interpolate(s+.5).coords[0])-np.array(r['line'].interpolate(s-.5).coords[0]);t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])
 for side in [-1,1]:public('bollard',q+n*(r['carriage_width']/2+.8)*side,0,r['name'])
print('PUBLIC',collections.Counter(x['type'] for x in props),flush=True)
# Build the plan graph by splitting old/new roads at actual junction coordinates.
original_edges=copy.deepcopy(p['edges']);newedges=[]
for r in newroads:
 rr={k:v for k,v in r.items() if k not in ['line','full','car','profile']};rr['points']=[[float(x),float(y),roadz([x,y])] for x,y in r['line'].coords];rr['source_reference']='S05';newedges.append(rr)
all_edges=original_edges+newedges;points_by_edge=[{0.,LineString(np.array(e['points'])[:,:2]).length} for e in all_edges];lines=[LineString(np.array(e['points'])[:,:2]) for e in all_edges]
for i in range(len(original_edges),len(all_edges)):
 for j in range(i):
  x=lines[i].intersection(lines[j])
  for q in shapely.get_parts(x):
   if q.geom_type=='Point':points_by_edge[i].add(lines[i].project(q));points_by_edge[j].add(lines[j].project(q))
nodes=copy.deepcopy(p['nodes'])
def node_at(q,z):
 for i,n in enumerate(nodes):
  pos=n.get('xy',n.get('position',n.get('point')))
  if pos is None:pos=[n.get('x',1e20),n.get('y',1e20)]
  if np.linalg.norm(np.asarray(pos)[:2]-q)<.005:return i
 nodes.append(dict(id=len(nodes),x=float(q[0]),y=float(q[1]),z=float(z),xy=[float(q[0]),float(q[1])],added_in_version='v20'));return len(nodes)-1
updated=[]
for i,(e,line,ss) in enumerate(zip(all_edges,lines,points_by_edge)):
 ss=sorted(ss)
 if i<len(original_edges) and len(ss)==2:updated.append(e);continue
 coords=np.array(e['points']);oldss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(coords[:,:2],axis=0),axis=1))]
 for a,b in zip(ss,ss[1:]):
  if b-a<.001:continue
  part=shapely.ops.substring(line,a,b);xy=np.array(part.coords);z=np.interp(np.r_[a,np.array([line.project(Point(q)) for q in xy[1:-1]]),b] if len(xy)>2 else [a,b],oldss,coords[:,2]);rec=copy.deepcopy(e);rec['points']=np.c_[xy,z].tolist();rec['a']=node_at(xy[0],z[0]);rec['b']=node_at(xy[-1],z[-1]);rec['length']=b-a;rec['range']=[float(z.min()),float(z.max())];rec['max_grade']=float(np.max(np.abs(np.diff(z))/np.maximum(np.linalg.norm(np.diff(xy,axis=0),axis=1),1e-7)));updated.append(rec)
for n in nodes:n['edges']=[]
for i,e in enumerate(updated):nodes[e['a']]['edges'].append(i);nodes[e['b']]['edges'].append(i)
p['nodes']=nodes;p['edges']=updated;p['real_buildings'].extend([{k:list(v.exterior.coords) if k in ['poly','pad'] else v for k,v in s.items() if k not in ['poly','pad']} for s in sites]);p['access_v20']=[{k:list(v.coords) if k=='route' else list(v.exterior.coords) if k=='polygon' else v for k,v in w.items()} for w in paths];p['urban_areas_v20']=dict(groups=layout['groups'],public_furniture=props,new_road_names=[r['name'] for r in newroads],layout_inspiration=layout['inspiration'])
counts=collections.Counter(b['zone'] for b in p['buildings']);counts.update(b.get('zone','OLDTOWN') for b in p['real_buildings']);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),building_count_by_zone=dict(counts),road_edges=len(updated),road_length_m=sum(LineString(np.array(e['points'])[:,:2]).length for e in updated),junctions=len(nodes),new_v20_buildings=len(sites),new_v20_public_instances=len(props));assert p['stats']['buildings']==layout['city_building_units']<700
after={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'};report=dict(version='v20',baseline_commit=layout['baseline_commit'],districts=ids,city_buildings=p['stats']['buildings'],removed_placeholders=sorted(removed),new_asset_instances=len(sites),new_asset_types=len(templates),removed_massing_faces=removed_faces,new_road_length_m=sum(r['line'].length for r in newroads),ground_patch_m2=raw.area,public_counts=dict(collections.Counter(x['type'] for x in props)),unchanged_original_objects={n:h for n,h in before.items() if after.get(n)==h},changed_original_objects=[n for n,h in before.items() if n in after and after[n]!=h],removed_original_objects=sorted(set(before)-set(after)),new_objects=sorted(set(after)-set(before)))
(R/'model').mkdir(exist_ok=True);(R/'validation').mkdir(exist_ok=True);(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(R/'model/site_levels.json').write_text(json.dumps([{k:list(v.exterior.coords) if k in ['poly','pad'] else v for k,v in s.items()} for s in sites],ensure_ascii=False,indent=2));(R/'model/public_instances.json').write_text(json.dumps(props,ensure_ascii=False,indent=2));(R/'model/road_profiles.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ['line','full','car']} for r in newroads],ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v20.blend'),compress=True);print('V20_BUILD_DONE',len(sites),p['stats']['buildings'],flush=True)
