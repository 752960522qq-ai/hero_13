"""City v18: ten user assets, eight old-town replacements, and an eastern new-town plan."""
import bpy,sys,os,json,math,hashlib,copy,collections
from pathlib import Path
from mathutils import Matrix,Vector
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,os.environ.get('HERO13_CITY_DEPS',str(R.parent/'tools_runtime/blender_deps')));sys.path.insert(0,str(R/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
p=json.load(open(R/'baseline/city_plan.json'));old=copy.deepcopy(p);inputs=json.load(open(R/'source_inputs.json'));ids=[3,8]
bpy.ops.wm.read_factory_settings(use_empty=True)
for d in ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02d}_*.glb'))))
bpy.context.view_layer.update();sc=bpy.context.scene
for o in list(sc.objects):
 if o.type=='MESH':
  M=o.matrix_world.copy();o.data=o.data.copy();o.data.transform(M);o.parent=None;o.matrix_world=Matrix.Identity(4);o.data.update()
for o in list(sc.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
roots={}
for d in ids:
 o=bpy.data.objects.new(f'District_{d:02d}',None);sc.collection.objects.link(o);o['district_id']=d;roots[d]=o
for o in sc.objects:
 if o.type=='MESH':o.parent=roots[int(o.get('district_id'))];o.matrix_parent_inverse=Matrix.Identity(4)
def district(q):return 3 if q[1]<620 else 8
def co(o):
 a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a);a=a.reshape(-1,3).astype(float);M=np.array(o.matrix_world);return a@M[:3,:3].T+M[:3,3]
def fingerprint(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in o.data.vertices],dtype='<f4').tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in o.data.uv_layers:h.update(np.array([x.uv[:] for x in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()

def material(name,col):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=.86;return m

def newmesh(name,v,f,mat,d=None,props=None):
 m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o)
 if d is None:d=district(np.mean(np.asarray(v),axis=0))
 o.parent=roots[d];o['district_id']=d;o['source_object']=name;o['modified_in_version']='v18'
 for k,x in (props or {}).items():o[k]=x
 return o

def prism(poly,top,bottom,name,d=None,props=None):
 xy=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:-1];n=len(xy);v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]];f=[]
 for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
 return newmesh(name,v.tolist(),f,basemat,d,props)

def keep_faces(o,keep):
 m=o.data;fs=[f for f,k in zip(m.polygons,keep) if k]
 if not fs:bpy.data.objects.remove(o,do_unlink=True);return
 used=sorted({v for f in fs for v in f.vertices});mapping={v:i for i,v in enumerate(used)};nm=bpy.data.meshes.new(m.name+'_v18');nm.from_pydata([m.vertices[v].co[:] for v in used],[],[[mapping[v] for v in f.vertices] for f in fs])
 for mat in m.materials:nm.materials.append(mat)
 nm.polygons.foreach_set('material_index',np.array([f.material_index for f in fs],np.int32));nm.update()
 for uv in m.uv_layers:
  layer=nm.uv_layers.new(name=uv.name);layer.data.foreach_set('uv',np.array([uv.data[i].uv[:] for f in fs for i in f.loop_indices],np.float32).ravel())
 for col in m.color_attributes:
  layer=nm.color_attributes.new(name=col.name,type=col.data_type,domain=col.domain);values=[col.data[i].color[:] for i in used] if col.domain=='POINT' else [col.data[i].color[:] for f in fs for i in f.loop_indices];layer.data.foreach_set('color',np.array(values,np.float32).ravel())
 o.data=nm

def clip_ground(o,cut):
 m=o.data;m.calc_loop_triangles();xyz=co(o);local=cut.intersection(box(*np.r_[xyz[:,:2].min(0),xyz[:,:2].max(0)]))
 if local.is_empty:return
 vv=[];ff=[];mats=[];cols=[];uvs=[[] for x in m.uv_layers];color=m.color_attributes[0] if m.color_attributes else None;changed=0
 for tri in m.loop_triangles:
  q=xyz[list(tri.vertices)];shape=Polygon(q[:,:2]);parts=[q]
  if shape.area<1e-9:continue
  if shape.intersects(local):
   diff=shape.difference(local)
   if shape.area-diff.area>1e-8:
    changed+=1;parts=[]
    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
     xy=np.array(t.exterior.coords)[:3];weights=np.linalg.solve(np.vstack([q[:,:2].T,np.ones(3)]),np.vstack([xy.T,np.ones(3)]));parts.append(np.c_[xy,weights.T@q[:,2]])
  for a in parts:
   if np.cross(a[1,:2]-a[0,:2],a[2,:2]-a[0,:2])<0:a=a[::-1]
   weights=np.linalg.solve(np.vstack([q[:,:2].T,np.ones(3)]),np.vstack([a[:,:2].T,np.ones(3)]));k=len(vv);vv.extend(a.tolist());ff.append([k,k+1,k+2]);mats.append(m.polygons[tri.polygon_index].material_index)
   if color:
    ix=list(tri.vertices) if color.domain=='POINT' else list(tri.loops);cols.extend((weights.T@np.array([color.data[i].color[:] for i in ix])).tolist())
   for idx,uv in enumerate(m.uv_layers):uvs[idx].extend((weights.T@np.array([uv.data[i].uv[:] for i in tri.loops])).tolist())
 if changed:
  if not ff:bpy.data.objects.remove(o,do_unlink=True);return
  nm=bpy.data.meshes.new(m.name+'_graded_v18');nm.from_pydata(vv,[],ff)
  for mat in m.materials:nm.materials.append(mat)
  nm.polygons.foreach_set('material_index',np.array(mats,np.int32));nm.update()
  if cols:nm.color_attributes.new(name=color.name,type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(cols,np.float32).ravel())
  for uv,values in zip(m.uv_layers,uvs):nm.uv_layers.new(name=uv.name).data.foreach_set('uv',np.array(values,np.float32).ravel())
  o.data=nm;o['modified_in_version']='v18'
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain']);publicwalk=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 hit,_,idx,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=field.tri[idx];w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1.]);return float(w@tri[:,2])
land=Polygon(p['coasts']['MAIN']);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.015,join_style=2) for e in p['edges']]);carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.015,join_style=2) for e in p['edges']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
soilmat=material('V18_Graded_Landscape',(.52,.55,.48));pavemat=material('V18_Forecourt_Paving',(.56,.56,.51));basemat=material('V18_Light_Concrete',(.51,.52,.48))
heights={'H57':14.4,'58':13.4,'59':17.2,'60':11.,'61':11.5,'62':11.4,'63':11.8,'64':18.,'65':18.,'66':17.}
templates={}
for src in inputs:
 start=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(R/'sources'/src['file']));bpy.context.view_layer.update();imported=set(sc.objects)-start;parts=[]
 for o in imported:
  if o.type=='MESH':m=o.data.copy();m.transform(o.matrix_world);parts.append(m)
 xyz=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=xyz.min(0);hi=xyz.max(0);height=heights[src['key']];scale=height/(hi[2]-lo[2]);T=Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation((-(lo[0]+hi[0])/2,-lo[1],-lo[2]))
 for m in parts:m.transform(T)
 for o in imported:bpy.data.objects.remove(o,do_unlink=True)
 templates[src['key']]={'meshes':parts,'width':float((hi[0]-lo[0])*scale),'depth':float((hi[1]-lo[1])*scale),'height':height,'scale':float(scale),'source_bounds':[lo.tolist(),hi.tolist()],**src};print('TEMPLATE',src['key'],templates[src['key']]['width'],templates[src['key']]['depth'],flush=True)
# Use each uploaded building once. The previous pool remains unchanged.
choices=[];replaced=[];groupuse=collections.Counter();blockuse=collections.Counter();lots=[b for b in p['buildings'] if b['zone']=='OLDTOWN' and 80<b['center'][0]<350 and 195<b['center'][1]<410 and ':H' in b['frontage_group']]
for key in sorted([k for k in templates if k not in ['64','65']],key=lambda k:-templates[k]['width']):
 t=templates[key];options=[]
 for b in lots:
  if b['name'] in replaced:continue
  poly=Polygon(b['footprint']);xmin,ymin,xmax,ymax=poly.bounds
  if xmax-xmin<t['width']+.25 or ymax-ymin<t['depth']+.25:continue
  south=b['frontage_group'].endswith('H-1');theta=0. if south else math.pi;front=[b['center'][0],ymin+.08 if south else ymax-.08];u=np.array([math.cos(theta),math.sin(theta)]);v=np.array([-u[1],u[0]]);face=np.array(front)-u*t['width']/2;shape=Polygon([face,face+u*t['width'],face+u*t['width']+v*t['depth'],face+v*t['depth']]);assert poly.buffer(.001).covers(shape)
  cost=np.linalg.norm(np.array(b['center'])-[150,300])+groupuse[b['frontage_group']]*100+blockuse[b['block_id']]*45;options.append((cost,b,shape,front,theta))
 assert options,('no suitable old-town lot',key)
 _,b,shape,front,theta=min(options,key=lambda x:x[0]);choices.append({'key':key,'lot':b['name'],'poly':shape,'front':front,'theta':theta,'zone':'OLDTOWN','kind':'arcade_street_source','group':b['frontage_group']});replaced.append(b['name']);groupuse[b['frontage_group']]+=1;blockuse[b['block_id']]+=1
for key,center,kind in [('64',[680.,845.],'shopping_mall'),('65',[680.,910.],'police_headquarters')]:
 t=templates[key];theta=-math.pi/2;u=np.array([0.,-1.]);v=np.array([1.,0.]);front=np.array(center)-v*t['depth']/2;face=front-u*t['width']/2;shape=Polygon([face,face+u*t['width'],face+u*t['width']+v*t['depth'],face+v*t['depth']]);choices.append({'key':key,'lot':None,'poly':shape,'front':front.tolist(),'theta':theta,'zone':'NEW_TOWN','kind':kind,'group':'EAST_NEW_TOWN'})
# Remove complete constituent buildings from their original merged massing.
oldtownlots=[b for b in p['buildings'] if b['zone']=='OLDTOWN'];lotpolys=[Polygon(b['footprint']) for b in oldtownlots];tree=shapely.STRtree(lotpolys)
removed_triangles=0
for o in list(sc.objects):
 if o.type!='MESH' or 'MAIN_OLDTOWN_Massing_' not in o.get('source_object',''):continue
 xyz=co(o);keep=[];owners=set();name=o.name
 for f in o.data.polygons:
  pt=Point(xyz[list(f.vertices),:2].mean(0));idx=int(tree.nearest(pt));assert pt.distance(lotpolys[idx])<.06;owner=oldtownlots[idx]['name'];k=owner not in replaced;keep.append(k)
  if k:owners.add(owner)
 removed_triangles+=len(keep)-sum(keep)
 if not all(keep):keep_faces(o,keep)
 if name in sc.objects:sc.objects[name]['placeholder_lot_count']=len(owners)
p['buildings']=[b for b in p['buildings'] if b['name'] not in replaced]
# Flat plinths follow the road level at the old-town entrances; civic/commercial
# buildings sit on small terrain terraces, with access to the west-side street.
sites=[];newreal=[]
for c in choices:
 t=templates[c['key']];poly=c['poly'];front=np.array(c['front']);theta=c['theta'];outward=np.array([math.sin(theta),-math.cos(theta)])
 floor=nearest(publicwalk,front+outward*.15)+.035 if c['zone']=='OLDTOWN' else float(np.median([nearest(soil,q) for q in shapely.segmentize(poly.exterior,3).coords]))+.035
 name='OLDTOWN_V18_ARCADE_'+c['key'] if c['zone']=='OLDTOWN' else 'NEWTOWN_V18_'+('MALL_64' if c['key']=='64' else 'POLICE_HQ_65');T=Matrix.Translation((*front,floor))@Matrix.Rotation(theta,4,'Z')
 for k,m in enumerate(t['meshes']):
  ob=bpy.data.objects.new(name+f'_Source_Mesh_{k:02d}',m);sc.collection.objects.link(ob);ob.parent=roots[district(poly.centroid.coords[0])];ob.matrix_world=T
  for prop,val in {'district_id':district(poly.centroid.coords[0]),'source_object':ob.name,'source_instance':name,'source_filename':t['file'],'is_building_instance':True,'zone':c['zone'],'added_in_version':'v18'}.items():ob[prop]=val
  if c['zone']=='OLDTOWN':ob['arcade_pool_key']=c['key']
 r={'instance_name':name,'file':t['file'],'source_filename':t['file'],'source_sha256':t['sha256'],'original_upload_name':t['original_upload_name'],'uniform_scale':t['scale'],'local_axis_scale':[1,1,1],'source_bounds':t['source_bounds'],'source_floor_reference':t['source_bounds'][0][2],'target_height_m':t['height'],'floor':floor,'theta':theta,'angle':math.degrees(theta),'center':list(poly.centroid.coords[0]),'anchor':front.tolist(),'footprint_xy':list(poly.exterior.coords)[:-1],'pad_xy':list(poly.buffer(.035,join_style=2).exterior.coords),'region':'MAIN','zone':c['zone'],'typology':c['kind'],'building_count_units':1,'added_in_version':'v18','replaced_placeholder':c['lot'],'direct_sidewalk_frontage':c['zone']=='OLDTOWN','no_mirror':True,'access_alley':name+'_Entrance_Walk'}
 if c['zone']=='OLDTOWN':r['arcade_pool_key']=c['key'];r['frontage_group']=c['group']
 newreal.append(r);sites.append({'name':name,'key':c['key'],'kind':c['zone'],'poly':poly,'pad':poly.buffer(.35 if c['zone']=='OLDTOWN' else 2.4,join_style=2),'front':front.tolist(),'outward':outward.tolist(),'floor':floor,'height':t['height']})
p['real_buildings'].extend(newreal)
fixed=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['pad_xy']) for r in old['real_buildings']]);paths=[];goals=[]
for e in p['edges']:
 if e['region']!='MAIN':continue
 line=LineString(np.array(e['points'])[:,:2])
 for side in ['left','right']:
  for g in shapely.get_parts(line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((e['name']+'_'+side,g))
for rec in sites:
 start=np.array(rec['front']);normal=np.array(rec['outward']);w=templates[rec['key']]['width']
 if rec['kind']=='OLDTOWN':
  end=start+normal*1.6;route=LineString([start,end]);paths.append({'name':rec['name']+'_Entrance_Walk','building':rec['name'],'kind':'arcade_apron','route':route,'polygon':route.buffer(w/2+.06,cap_style=2),'floor':rec['floor']-.025,'goal_z':nearest(publicwalk,end)});continue
 start=start+normal*2.4;blocked=unary_union([fixed]+[r['poly'].buffer(.1,join_style=2) for r in sites if r['name']!=rec['name']]);options=[]
 for gn,g in sorted(goals,key=lambda x:x[1].distance(Point(start)))[:12]:
  for offset in [0.,-4.,4.]:
   end=np.array(g.interpolate(np.clip(g.project(Point(start))+offset,0,g.length)).coords[0]);route=LineString([start,end]);L=route.length;corr=route.buffer(2.,cap_style=2);gz=publicwalk.height(end)
   if gz is None or L<.4 or L>75 or (end-start)@normal/L<.7 or not land.covers(corr):continue
   if corr.intersection(carriage).area>.002 or corr.intersection(blocked).area>.002:continue
   grade=abs(rec['floor']-.025-gz)/L
   if grade>.14:continue
   options.append((L+grade*40,route,corr,float(gz),gn,grade))
 if not options:
  print('ACCESS_DEBUG',rec['name'],rec['floor'],start.tolist(),flush=True)
  for gn,g in sorted(goals,key=lambda x:x[1].distance(Point(start)))[:6]:
   end=np.array(g.interpolate(g.project(Point(start))).coords[0]);route=LineString([start,end]);corr=route.buffer(2.,cap_style=2);gz=publicwalk.height(end);print('GOAL_DEBUG',gn,end.tolist(),gz,route.length,corr.intersection(carriage).area,corr.intersection(blocked).area,flush=True)
 assert options,('No new-town entrance route',rec['name'])
 _,route,corr,gz,gn,grade=min(options,key=lambda x:x[0]);paths.append({'name':rec['name']+'_Entrance_Walk','building':rec['name'],'kind':'newtown_access','route':route,'polygon':corr,'floor':rec['floor']-.025,'goal_z':gz,'street':gn,'design_grade':grade})
# Rebuild one non-overlapping terrain/pavement skin per affected district.
aprons=unary_union([w['polygon'].buffer(.12,join_style=2) for w in paths if w['kind']=='arcade_apron']);newholes=unary_union([r['poly'].buffer(.035,join_style=2) for r in sites]);rawpatch=unary_union([r['pad'].buffer(3 if r['kind']=='OLDTOWN' else 12,join_style=2) for r in sites]+[w['polygon'].buffer(.35 if w['kind']=='arcade_apron' else 8,join_style=2) for w in paths]);patch=rawpatch.intersection(land).difference(roads.buffer(.002).difference(aprons)).difference(carriage.buffer(.01)).difference(fixed.buffer(.015)).difference(reserve.buffer(.02)).difference(newholes);cut=patch.union(newholes)
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type')=='terrain':clip_ground(o,cut)
 elif o.type=='MESH' and o.get('surface_type')=='sidewalk':clip_ground(o,cut.intersection(aprons))
wall_removed=0
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type')=='terrain_cut_retaining_wall':
  xyz=co(o);keep=[not cut.buffer(.08).covers(Point(xyz[list(f.vertices),:2].mean(0))) for f in o.data.polygons];wall_removed+=len(keep)-sum(keep)
  if not all(keep):keep_faces(o,keep)
cache={}
def groundz(q):
 key=tuple(round(float(x),5) for x in q)
 if key in cache:return cache[key]
 pt=Point(q);z=nearest(soil,q)
 for rec in sites:
  radius=3. if rec['kind']=='OLDTOWN' else 12.;dist=pt.distance(rec['pad'])
  if dist<radius:t=1-dist/radius;t=t*t*(3-2*t);z=z*(1-t)+(rec['floor']-.025)*t
 for w in paths:
  radius=.35 if w['kind']=='arcade_apron' else 8.;dist=pt.distance(w['polygon'])
  if dist>=radius:continue
  route=w['route'];s=route.project(pt);t=s/route.length
  if w['kind']=='arcade_apron':
   direction=np.array(route.coords[-1])-np.array(route.coords[0]);direction/=route.length;endpoint=np.array(q)+direction*(route.length-s);t=float(np.clip((s-.35)/(route.length-.35),0,1));h=w['floor']*(1-t)+nearest(publicwalk,endpoint)*t
  else:h=w['floor']*(1-t)+w['goal_z']*t
  mix=1-dist/radius;mix=mix*mix*(3-2*mix);z=z*(1-mix)+h*mix
 owners=[r for r in sites if r['pad'].covers(pt)]
 if owners:z=min(owners,key=lambda r:pt.distance(r['poly']))['floor']-.025
 cache[key]=z;return z
vp={d:[] for d in ids};fp={d:[] for d in ids};mi={d:[] for d in ids};xmin,ymin,xmax,ymax=patch.bounds
xgrid=sorted(set(np.arange(math.floor(xmin/3)*3,xmax+3,3).tolist()+[v for r in sites for v in [r['poly'].bounds[0],r['poly'].bounds[2],r['pad'].bounds[0],r['pad'].bounds[2]]]))
ygrid=sorted(set(np.arange(math.floor(ymin/3)*3,ymax+3,3).tolist()+[v for r in sites for v in [r['poly'].bounds[1],r['poly'].bounds[3],r['pad'].bounds[1],r['pad'].bounds[3]]]))
for x,xn in zip(xgrid,xgrid[1:]):
 for y,yn in zip(ygrid,ygrid[1:]):
  if xn-x<1e-6 or yn-y<1e-6:continue
  tile=box(x,y,xn,yn)
  if not patch.intersects(tile):continue
  for t in shapely.get_parts(shapely.constrained_delaunay_triangles(patch.intersection(tile))):
   xy=np.array(t.exterior.coords)[:3]
   if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
   mid=xy.mean(0);d=district(mid);k=len(vp[d]);vp[d].extend([[*q,groundz(q)] for q in xy]);fp[d].append([k,k+1,k+2]);pt=Point(mid);mi[d].append(int(any(r['pad'].covers(pt) for r in sites) or any(w['polygon'].covers(pt) for w in paths)))
for d in ids:
 o=newmesh('V18_Graded_Ground_'+str(d),vp[d],fp[d],soilmat,d,{'surface_type':'terrain','is_walkable_grading':True});o.data.materials.append(pavemat);o.data.polygons.foreach_set('material_index',np.array(mi[d],np.int32))
for rec in sites:
 bottom=min([nearest(soil,q) for q in rec['poly'].exterior.coords]+[rec['floor']-.5])-.2;prism(rec['poly'].buffer(.035,join_style=2),rec['floor']-.018,bottom,rec['name']+'_Foundation',props={'is_site_foundation':True,'site_building':rec['name']})
# Planning boundary follows the east-side roads. Existing residential massing
# is incorporated as an existing phase, not duplicated or relabelled as built assets.
newtown=Polygon([[600,420],[940,420],[940,650],[830,840],[730,940],[600,940]]).intersection(land.buffer(-10));existing_res=[b for b in p['buildings'] if b['region']=='MAIN' and b['zone']=='RESIDENTIAL' and newtown.covers(Polygon(b['footprint']))];transport=roads.buffer(4.);newbody=unary_union([r['poly'].buffer(3.,join_style=2) for r in sites if r['kind']=='NEW_TOWN']);parts=[]
for name,role,status,shape in [('Commercial_Center','commercial','initial_assets_placed',box(635,810,725,882)),('Public_Service','civic','initial_assets_placed',box(635,884,728,940)),('Existing_Residential','residential','existing_placeholder_massing',box(600,420,940,620)),('Future_Mixed_Use','mixed_use','reserved_unbuilt',box(700,715,815,880)),('Interchange_Green_Buffer','green_buffer','reserved_unbuilt',box(670,625,900,695))]:
 g=shape.intersection(newtown).difference(transport)
 if status=='reserved_unbuilt':g=g.difference(fixed.buffer(3.)).difference(newbody)
 for i,q in enumerate(shapely.get_parts(g)):
  if q.geom_type=='Polygon' and q.area>50:parts.append({'name':name+('_'+str(i+1) if len(shapely.get_parts(g))>1 else ''),'role':role,'status':status,'polygon':list(q.exterior.coords),'holes':[list(r.coords) for r in q.interiors],'area_m2':q.area})
pool=p['arcade_asset_pool']
for entry in pool:
 entry['replacements_in_v17']=entry.get('replacements_this_version',0);entry['replacements_this_version']=0;entry['replacements_in_v18']=0
for r in newreal:
 if r['zone']!='OLDTOWN':continue
 t=templates[r['arcade_pool_key']];pool.append({'key':r['arcade_pool_key'],'file':r['file'],'original_upload_name':r['original_upload_name'],'new_source':True,'sha256':r['source_sha256'],'total_instance_limit':3,'instances':[r['instance_name']],'instance_count':1,'replacements_this_version':1,'replacements_in_v18':1,'width_m':t['width'],'depth_m':t['depth'],'target_height_m':t['height'],'no_mirror':True,'scale_policy':'Uniform; source proportions and textures retained'})
p['access_v18']=[{k:(list(v.exterior.coords) if k=='polygon' else list(v.coords) if k=='route' else v) for k,v in w.items()} for w in paths];p['urban_areas_v18']={'new_town':{'name_zh':'东部新城区','island':'MAIN','polygon':list(newtown.exterior.coords),'area_m2':newtown.area,'boundary_basis':'East-side main-island neighborhoods north of MAIN_EW_410, organized along MAIN_NS_620 and MAIN_NS_830, inside the coastal road belt.','existing_residential_lots':[b['name'] for b in existing_res],'existing_residential_units':len(existing_res),'new_source_buildings':[r['instance_name'] for r in newreal if r['zone']=='NEW_TOWN'],'new_source_building_units':2,'building_units':len(existing_res)+2,'land_use_parcels':parts,'future_parcels_are_unbuilt':True},'oldtown_replacements':{'placeholder_names':replaced,'new_source_instances':[r['instance_name'] for r in newreal if r['zone']=='OLDTOWN'],'street_buildings':120,'rear_buildings':80}}
p['schema']='hero13.city.regional-update.v18';p['sources']['regional_update_v18']='delivery/city_updates/v18_20261030/tools/build_v18.py';cnt=collections.Counter(b['zone'] for b in p['buildings']);cnt.update(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN') for r in p['real_buildings']);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),building_count_by_zone=dict(cnt),arcade_pool_types=len(pool),arcade_source_instances=sum(r['instance_count'] for r in pool),source_asset_types=len({r['file'] for r in p['real_buildings']}),source_geometry_texture_types=old['stats']['source_geometry_texture_types']+10,new_town_area_m2=newtown.area,new_town_buildings=len(existing_res)+2)
p['stats']['oldtown_building_footprint_m2']=sum(Polygon(b['footprint']).area for b in p['buildings'] if b['zone']=='OLDTOWN')+sum(Polygon(r['footprint_xy']).area for r in p['real_buildings'] if r.get('zone')=='OLDTOWN' or r['instance_name'].startswith('OLDTOWN'));p['stats']['building_coverage_percent']=100*(sum(Polygon(b['footprint']).area for b in p['buildings'])+sum(Polygon(r['footprint_xy']).area for r in p['real_buildings']))/p['stats']['land_area_m2']
assert p['stats']['buildings']==543 and cnt['OLDTOWN']==200 and len(newreal)==10
features=[{'type':'Feature','properties':{'name':'Eastern New Town','name_zh':'东部新城区','role':'district_boundary','area_m2':newtown.area},'geometry':shapely.geometry.mapping(newtown)}]+[{'type':'Feature','properties':{k:v for k,v in q.items() if k not in ['polygon','holes']},'geometry':shapely.geometry.mapping(Polygon(q['polygon'],q['holes']))} for q in parts]
after={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'};report={'version':'v18','baseline_commit':'9ce7807e5da5532a841e9dafa0583a207068d938','districts':ids,'city_buildings':543,'oldtown_buildings':200,'oldtown_street_buildings':120,'new_asset_instances':10,'replaced_placeholder_names':replaced,'newtown_area_m2':newtown.area,'newtown_existing_residential_units':len(existing_res),'newtown_new_source_building_units':2,'source_inputs':inputs,'ground_patch_area_m2':patch.area,'ground_patch_triangles':sum(len(v) for v in fp.values()),'removed_massing_triangles':removed_triangles,'removed_retaining_wall_triangles':wall_removed,'changed_original_objects':[n for n,h in after.items() if n in before and h!=before[n]],'removed_objects':sorted(set(before)-set(after)),'unchanged_original_objects':{n:h for n,h in before.items() if after.get(n)==h},'new_objects':sorted(set(after)-set(before))}
(R/'model').mkdir(exist_ok=True);(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(R/'model/site_levels.json').write_text(json.dumps([{k:(list(v.exterior.coords) if k in ['poly','pad'] else v) for k,v in r.items()} for r in sites],indent=2));(R/'new_town_v18.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_system':'Blender world XY in metres; not geographic longitude/latitude','features':features},ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v18.blend'),compress=True);print('V18_BUILD_DONE',543,newtown.area,len(existing_res),flush=True)
