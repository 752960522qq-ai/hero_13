"""City v17: capped arcade reuse, a smaller old town, and inland apartments.

Inputs are the exact v16 composed districts, the two supplied GLBs and layout.
No source facade is mirrored; existing sample street and civic/CBD assets remain.
"""
import bpy,sys,os,json,math,copy,hashlib,collections
from pathlib import Path
from mathutils import Matrix,Vector
import numpy as np
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,os.environ.get('HERO13_CITY_DEPS',str(R.parent/'tools_runtime/blender_deps')))
sys.path.insert(0,str(R/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
p=json.load(open(R/'baseline/city_plan.json'));old=copy.deepcopy(p);layout=json.load(open(R/'layout_v17.json'))
bpy.ops.wm.open_mainfile(filepath=str(R/'model/base_v16_partial.blend'));sc=bpy.context.scene
ids=[2,3,4,6,7];roots={}
for d in ids:
 o=bpy.data.objects.new(f'District_{d:02d}',None);sc.collection.objects.link(o);o['district_id']=d;roots[d]=o
for o in list(sc.objects):
 if o.type=='MESH':o.parent=roots[int(o.get('district_id'))];o.matrix_parent_inverse=Matrix.Identity(4)
def district(q):return (2 if q[0]<0 else 3 if q[0]<500 else 4)+(4 if q[1]>=620 else 0)
def co(o):
 x=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',x);x=x.reshape(-1,3).astype(float);M=np.array(o.matrix_world);return x@M[:3,:3].T+M[:3,3]
def fingerprint(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in o.data.vertices],dtype='<f4').tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in o.data.uv_layers:h.update(np.array([x.uv[:] for x in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()
before={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
publicwalk=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='sidewalk'])
def nearest(field,q):
 z=field.height(q)
 if z is not None:return z
 hit,_,idx,_=field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=field.tri[idx];w=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1.]);return float(w@tri[:,2])
land=Polygon(p['coasts']['MAIN']);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.015,join_style=2) for e in p['edges']]);carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.015,join_style=2) for e in p['edges']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
oldlots={b['name']:b for b in p['buildings']};realmap={b['instance_name']:b for b in p['real_buildings']}
def material(name,col):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=.86;return m
soilmat=material('V17_Graded_Landscape',(.52,.55,.48));pavemat=material('V17_Pedestrian_Paving',(.56,.56,.50));basemat=material('V17_Light_Concrete',(.51,.52,.48))
def newmesh(name,v,f,mat,d=None,props=None):
 m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o)
 if d is None:d=district(np.mean(np.asarray(v),axis=0))
 o.parent=roots[d];o['district_id']=d;o['source_object']=name;o['modified_in_version']='v17'
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
 used=sorted({v for f in fs for v in f.vertices});mapping={v:i for i,v in enumerate(used)};nm=bpy.data.meshes.new(m.name+'_v17');nm.from_pydata([m.vertices[v].co[:] for v in used],[],[[mapping[v] for v in f.vertices] for f in fs])
 for mat in m.materials:nm.materials.append(mat)
 nm.polygons.foreach_set('material_index',np.array([f.material_index for f in fs],np.int32));nm.update()
 for uv in m.uv_layers:
  layer=nm.uv_layers.new(name=uv.name);layer.data.foreach_set('uv',np.array([uv.data[i].uv[:] for f in fs for i in f.loop_indices],np.float32).ravel())
 for col in m.color_attributes:
  layer=nm.color_attributes.new(name=col.name,type=col.data_type,domain=col.domain);values=[col.data[i].color[:] for i in used] if col.domain=='POINT' else [col.data[i].color[:] for f in fs for i in f.loop_indices];layer.data.foreach_set('color',np.array(values,np.float32).ravel())
 o.data=nm

# Canonical copies derive from the original, already validated sample street.
# For its corner building the approved 90 degree turn/1.45 depth is retained.
pool_sources={'05':'OLDTOWN_Connected_Arcade_05','06':'OLDTOWN_Connected_Arcade_06','07':'OLDTOWN_Connected_Arcade_07','08':'OLDTOWN_Connected_Shop_08','09':'OLDTOWN_Connected_Shop_09','10':'OLDTOWN_Corner_Shop_10','12':'OLDTOWN_Joined_Storefront_12','13':'OLDTOWN_Joined_Urban_Shopfront_13'}
templates={}
for key,name in pool_sources.items():
 r=realmap[name];parts=[];theta=float(r['theta']);T=Matrix.Rotation(-theta,4,'Z')@Matrix.Translation((-r['center'][0],-r['center'][1],-r['floor']))
 for o in sc.objects:
  if o.type=='MESH' and o.get('source_instance')==name:
   m=o.data.copy();m.transform(T@o.matrix_world);parts.append(m)
 xyz=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=xyz.min(0);hi=xyz.max(0);C=Matrix.Translation((-(lo[0]+hi[0])/2,-lo[1],0))
 for m in parts:m.transform(C)
 templates[key]={'meshes':parts,'width':float(hi[0]-lo[0]),'depth':float(hi[1]-lo[1]),'height':float(hi[2]-lo[2]),'bottom':float(lo[2]),'source':name,'file':r['file'],'target_height':r['target_height_m'],'legacy_scale':r['uniform_scale'],'legacy_axis_scale':r.get('local_axis_scale',[1,1,1])}
for key,file,height in [('57','01-modern-storefront-building-3d-model-57.glb',10.2),('56','02-building-3d-model-56.glb',13.0)]:
 beforeobjs=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(R/'sources'/file));bpy.context.view_layer.update();imported=set(sc.objects)-beforeobjs;parts=[]
 for o in imported:
  if o.type=='MESH':m=o.data.copy();m.transform(o.matrix_world);parts.append(m)
 xyz=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=xyz.min(0);hi=xyz.max(0);scale=height/(hi[2]-lo[2]);T=Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation((-(lo[0]+hi[0])/2,-lo[1],-lo[2]))
 for m in parts:m.transform(T)
 for o in imported:bpy.data.objects.remove(o,do_unlink=True)
 templates[key]={'meshes':parts,'width':float((hi[0]-lo[0])*scale),'depth':float((hi[1]-lo[1])*scale),'height':height,'bottom':0.,'source':None,'file':file,'target_height':height,'legacy_scale':float(scale),'legacy_axis_scale':[1,1,1],'source_bounds':[lo.tolist(),hi.tolist()],'sha256':hashlib.sha256((R/'sources'/file).read_bytes()).hexdigest()}
 print('TEMPLATE',key,templates[key]['width'],templates[key]['depth'],flush=True)

# Four continuous, mixed street runs replace 22 retained placeholder units.
# Narrow facades join their neighbors instead of standing in oversized lots.
run_specs=[('85:H-1',6,['05','06','10','57','56','07']),('79:H-1',6,['05','06','10','57','56','09']),('85:H1',5,['07','08','09','12','13']),('79:H1',5,['08','12','13','57','56'])]
replaced=[];newreal=[];sites=[];runs=[]
keep_names=set(layout['retained_street_placeholder_names'])
for group,n,keys in run_specs:
 bs=sorted([oldlots[nm] for nm in keep_names if oldlots[nm]['frontage_group']==group],key=lambda b:b['center'][0]);assert len(bs)>=n,group;bs=bs[:n];replaced.extend(b['name'] for b in bs);union=unary_union([Polygon(b['footprint']) for b in bs]);xmin,ymin,xmax,ymax=union.bounds;south=group.endswith('H-1');theta=0 if south else math.pi;u=np.array([math.cos(theta),math.sin(theta)]);v=np.array([-u[1],u[0]])
 width=sum(templates[k]['width'] for k in keys)+.04*(len(keys)-1);assert width<xmax-xmin+.01,(group,width,xmax-xmin);startx=(xmin+xmax-width)/2 if south else (xmin+xmax+width)/2;front=np.array([startx,ymin if south else ymax]);cursor=0.;runnames=[]
 for j,key in enumerate(keys):
  t=templates[key];w=t['width'];d=t['depth'];face=front+u*cursor;mid=face+u*w/2;pts=np.array([face,face+u*w,face+u*w+v*d,face+v*d]);poly=Polygon(pts);floor=nearest(publicwalk,mid-v*.10)+.035;name=f'OLDTOWN_V17_ARCADE_{key}_{sum(r.get("arcade_pool_key")==key for r in newreal)+1:02d}';T=Matrix.Translation((*mid,floor))@Matrix.Rotation(theta,4,'Z')
  for k,m in enumerate(t['meshes']):
   o=bpy.data.objects.new(name+f'_Source_Mesh_{k:02d}',m);sc.collection.objects.link(o);o.parent=roots[district(poly.centroid.coords[0])];o.matrix_world=T;o['district_id']=district(poly.centroid.coords[0]);o['source_object']=o.name;o['source_instance']=name;o['source_filename']=t['file'];o['is_building_instance']=True;o['zone']='OLDTOWN';o['arcade_pool_key']=key;o['added_in_version']='v17'
  rec={'instance_name':name,'file':t['file'],'source_filename':t['file'],'source_template_instance':t['source'],'arcade_pool_key':key,'uniform_scale':t['legacy_scale'],'local_axis_scale':t['legacy_axis_scale'],'target_height_m':t['target_height'],'theta':theta,'angle':math.degrees(theta),'center':list(poly.centroid.coords[0]),'anchor':mid.tolist(),'floor':floor,'footprint_xy':pts.tolist(),'pad_xy':list(poly.buffer(.025,join_style=2).exterior.coords),'region':'MAIN','zone':'OLDTOWN','typology':'arcade_street_source','frontage_group':group,'street_run':group,'direct_sidewalk_frontage':True,'building_count_units':1,'added_in_version':'v17','no_mirror':True,'reuse_mesh_data':True,'front_outward_normal':(-v).tolist(),'entrance_offset_from_mesh_bottom_m':-t['bottom']}
  if t.get('sha256'):rec.update(source_sha256=t['sha256'],source_bounds=t['source_bounds'])
  newreal.append(rec);sites.append({'name':name,'kind':'ARCADE','poly':poly,'pad':poly.buffer(.35,join_style=2),'floor':floor,'bottom':t['bottom'],'height':t['height'],'front':mid.tolist(),'outward':(-v).tolist()});runnames.append(name);cursor+=w+.04
 runs.append({'frontage_group':group,'source_instances':runnames,'replaced_placeholder_names':[b['name'] for b in bs],'length_m':width,'south_facing':south,'front_line':[front.tolist(),(front+u*width).tolist()]})
assert len(replaced)==22 and len(newreal)==22
removed=set(layout['removed_street_placeholder_names']);deleted=removed|set(replaced)
lot_polys=[Polygon(b['footprint']) for b in p['buildings'] if b['zone']=='OLDTOWN'];lot_records=[b for b in p['buildings'] if b['zone']=='OLDTOWN'];tree=shapely.STRtree(lot_polys);removed_mass_triangles=0
for o in list(sc.objects):
 if o.type!='MESH' or 'MAIN_OLDTOWN_Massing_' not in o.get('source_object',''):continue
 xyz=co(o);keep=[];owners=set()
 for f in o.data.polygons:
  center=Point(xyz[list(f.vertices),:2].mean(0));idx=int(tree.nearest(center));assert center.distance(lot_polys[idx])<.06,(o.name,center);nm=lot_records[idx]['name'];k=nm not in deleted;keep.append(k)
  if k:owners.add(nm)
 removed_mass_triangles+=len(keep)-sum(keep)
 object_name=o.name
 if not all(keep):keep_faces(o,keep)
 if object_name in sc.objects:sc.objects[object_name]['placeholder_lot_count']=len(owners);sc.objects[object_name]['modified_in_version']='v17'
p['buildings']=[b for b in p['buildings'] if b['name'] not in deleted]
p['real_buildings'].extend(newreal)
for key,name in pool_sources.items():realmap[name]['arcade_pool_key']=key
print('OLDTOWN_REDUCED',len(removed),len(replaced),len(newreal),flush=True)

# Move all twelve apartments into the red-marked inland parcel. Six columns,
# two rows leave a central walking court; each color occupies adjacent columns.
apartments=[r for r in p['real_buildings'] if r.get('zone')=='APARTMENT'];oldapts={r['instance_name']:copy.deepcopy(r) for r in apartments};apt_names=set(oldapts);apt_templates={}
for group in ['YELLOW_50','PINK_53','GRAY_54']:
 r=next(r for r in apartments if r['asset_color_group']==group);obs=[o for o in sc.objects if o.type=='MESH' and o.get('source_instance')==r['instance_name']];parts=[];T=Matrix.Rotation(-r['theta'],4,'Z')@Matrix.Translation((-r['center'][0],-r['center'][1],-r['floor']))
 for o in obs:m=o.data.copy();m.transform(T@o.matrix_world);parts.append(m)
 apt_templates[group]=parts
for o in list(sc.objects):
 if o.type=='MESH' and o.get('source_object','').endswith('_Foundation') and (o.get('site_building') in apt_names or any(o.get('source_object','')==nm+'_Foundation' for nm in apt_names)):bpy.data.objects.remove(o,do_unlink=True)
profile_x=np.r_[np.arange(-492.,-198.,2.),-198.];profile_z=np.array([nearest(soil,[x,1032.]) for x in profile_x])
for j in range(1,len(profile_z)):profile_z[j]=min(profile_z[j],profile_z[j-1]+.085*(profile_x[j]-profile_x[j-1]))
for j in range(len(profile_z)-2,-1,-1):profile_z[j]=min(profile_z[j],profile_z[j+1]+.085*(profile_x[j+1]-profile_x[j]))
def court_height(x):return float(np.interp(x,profile_x,profile_z))
apt_sites=[]
for gi,group in enumerate(['YELLOW_50','PINK_53','GRAY_54']):
 for j,r in enumerate(sorted([r for r in apartments if r['asset_color_group']==group],key=lambda r:r['instance_name'])):
  x=[-443,-401,-359,-317,-275,-233][gi*2+j%2];y=1007 if j<2 else 1062;theta=math.pi if j<2 else 0.;parts=apt_templates[group];xyz=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=xyz.min(0);hi=xyz.max(0);w,d=hi[:2]-lo[:2];poly=box(x-w/2,y-d/2,x+w/2,y+d/2);floor=court_height(x)+.035;T=Matrix.Translation((x,y,floor))@Matrix.Rotation(theta,4,'Z');obs=sorted([o for o in sc.objects if o.type=='MESH' and o.get('source_instance')==r['instance_name']],key=lambda o:o.name)
  for o,m in zip(obs,parts):o.data=m;o.parent=roots[6];o.matrix_world=T;o['district_id']=6;o['modified_in_version']='v17'
  r.update(center=[x,y],anchor=[x,y-d/2],floor=floor,theta=theta,angle=math.degrees(theta),footprint_xy=list(poly.exterior.coords)[:-1],pad_xy=list(poly.buffer(.035,join_style=2).exterior.coords),modified_in_version='v17',access_alley='V17_Apartment_Court')
  rec={'name':r['instance_name'],'kind':'APARTMENT','poly':poly,'pad':poly.buffer(2.2,join_style=2),'floor':floor,'bottom':0.,'height':r['target_height_m'],'front':[x,y+(d/2 if j<2 else -d/2)],'outward':[0,1 if j<2 else -1]};apt_sites.append(rec)
sites.extend(apt_sites)

# Patch only affected terrain. Facade aprons share a single surface with the
# terrain and touch foundation sides, avoiding the old coplanar black rims.
paths=[]
for rec in sites:
 if rec['kind']!='ARCADE':continue
 start=np.array(rec['front']);end=start+np.array(rec['outward'])*1.6;line=LineString([start,end]);paths.append({'name':rec['name'],'route':line,'polygon':line.buffer(templates[next(r['arcade_pool_key'] for r in newreal if r['instance_name']==rec['name'])]['width']/2,cap_style=2),'floor':rec['floor']-.025,'goal_z':nearest(publicwalk,end)})
spine=LineString([[-468,1032],[-198,1032]])
for rec in apt_sites:
 start=np.array(rec['front'])+np.array(rec['outward'])*2.2;end=np.array([start[0],1032]);route=LineString([start,end]);paths.append({'name':rec['name'],'route':route,'polygon':route.buffer(1.65,cap_style=2),'floor':rec['floor']-.025,'goal_z':court_height(end[0])})
paths.append({'name':'Apartment_Court_Spine','route':spine,'polygon':spine.buffer(2.0,cap_style=2),'sample_court_profile':True})
goals=[]
for e in p['edges']:
 if e['region']!='MAIN':continue
 line=LineString(np.array(e['points'])[:,:2])
 for side in ['left','right']:
  for g in shapely.get_parts(line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((e['name']+'_'+side,g))
for start in [[-198,1032]]:
 opts=[]
 for name,line in sorted(goals,key=lambda t:t[1].distance(Point(start)))[:12]:
  end=np.array(line.interpolate(line.project(Point(start))).coords[0]);route=LineString([start,end]);corr=route.buffer(2.,cap_style=2);z=publicwalk.height(end)
  if z is None or route.length<.1 or corr.intersection(carriage).area>.002 or corr.intersects(reserve):continue
  if any(corr.intersects(r['poly']) for r in apt_sites):continue
  opts.append((route.length,route,corr,z,name))
 assert opts,('no apartment exit',start)
 _,route,corr,z,name=min(opts,key=lambda t:t[0]);paths.append({'name':'Apartment_Exit_'+str(start[0]),'route':route,'polygon':corr,'floor':court_height(start[0]),'goal_z':z,'street':name})
old_restore=unary_union([Polygon(r['footprint_xy']).buffer(12.,join_style=2) for r in oldapts.values()]+[LineString(w['route']).buffer(7.,cap_style=2) for w in old['access_v16'] if w['name'] in apt_names])
newpads=unary_union([r['pad'].buffer(10 if r['kind']=='APARTMENT' else 3.,join_style=2) for r in sites]);pathpatch=unary_union([w['polygon'].buffer(5. if w['name'].startswith('Apartment') or w['name'] in apt_names else .35,join_style=2) for w in paths]);newholes=unary_union([r['poly'].buffer(.035,join_style=2) for r in sites]);arcade_aprons=unary_union([w['polygon'].buffer(.12,join_style=2) for w in paths if w['name'].startswith('OLDTOWN_')]);patch=unary_union([old_restore,newpads,pathpatch]).intersection(land).difference(roads.buffer(.002).difference(arcade_aprons)).difference(carriage.buffer(.01)).difference(reserve.buffer(.02));fixed=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['pad_xy']) for r in p['real_buildings'] if r['instance_name'] not in apt_names and r not in newreal]);patch=patch.difference(fixed.buffer(.015));patch=patch.difference(newholes)
cut=patch.union(newholes)
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
  nm=bpy.data.meshes.new(m.name+'_graded_v17');nm.from_pydata(vv,[],ff)
  for mat in m.materials:nm.materials.append(mat)
  nm.polygons.foreach_set('material_index',np.array(mats,np.int32));nm.update()
  if cols:nm.color_attributes.new(name=color.name,type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(cols,np.float32).ravel())
  for uv,values in zip(m.uv_layers,uvs):nm.uv_layers.new(name=uv.name).data.foreach_set('uv',np.array(values,np.float32).ravel())
  o.data=nm;o['modified_in_version']='v17'
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type')=='terrain':clip_ground(o,cut)
 elif o.type=='MESH' and o.get('surface_type')=='sidewalk':clip_ground(o,cut.intersection(arcade_aprons))
wall_removed=0
for o in list(sc.objects):
 if o.type=='MESH' and o.get('surface_type')=='terrain_cut_retaining_wall':
  xyz=co(o);keep=[not cut.buffer(.08).covers(Point(xyz[list(f.vertices),:2].mean(0))) for f in o.data.polygons];wall_removed+=len(keep)-sum(keep)
  if not all(keep):keep_faces(o,keep)
heightcache={}
def groundz(q):
 key=tuple(round(float(x),5) for x in q);pt=Point(q)
 if key in heightcache:return heightcache[key]
 z=nearest(soil,q)
 for rec in sites:
  dist=pt.distance(rec['pad']);radius=10 if rec['kind']=='APARTMENT' else 3.
  if dist<radius:t=1-dist/radius;t=t*t*(3-2*t);z=z*(1-t)+(rec['floor']-.025)*t
 for w in paths:
  dist=pt.distance(w['polygon']);radius=5 if w['name'].startswith('Apartment') or w['name'] in apt_names else .35
  if dist>=radius:continue
  route=w['route'];s=route.project(pt);t=s/max(route.length,.01)
  h=court_height(q[0]) if w.get('sample_court_profile') else w['floor']*(1-t)+w['goal_z']*t
  if w['name'].startswith('OLDTOWN_'):
   direction=np.array(route.coords[-1])-np.array(route.coords[0]);direction/=route.length;endpoint=np.array(q)+direction*(route.length-s);ratio=float(np.clip((s-.35)/(route.length-.35),0,1));h=w['floor']*(1-ratio)+nearest(publicwalk,endpoint)*ratio
  mix=1-dist/radius;mix=mix*mix*(3-2*mix);z=z*(1-mix)+h*mix
 owners=[rec for rec in sites if rec['pad'].covers(pt)]
 if owners:z=min(owners,key=lambda r:pt.distance(r['poly']))['floor']-.025
 heightcache[key]=z;return z
vp={d:[] for d in ids};fp={d:[] for d in ids};mi={d:[] for d in ids};xmin,ymin,xmax,ymax=patch.bounds;count=0
xgrid=sorted(set(np.arange(math.floor(xmin/3)*3,xmax+3,3).tolist()+[v for r in sites for v in [r['poly'].bounds[0],r['poly'].bounds[2],r['pad'].bounds[0],r['pad'].bounds[2]]]));ygrid=sorted(set(np.arange(math.floor(ymin/3)*3,ymax+3,3).tolist()+[v for r in sites for v in [r['poly'].bounds[1],r['poly'].bounds[3],r['pad'].bounds[1],r['pad'].bounds[3]]]))
for x,xnext in zip(xgrid,xgrid[1:]):
 for y,ynext in zip(ygrid,ygrid[1:]):
  if xnext-x<1e-6 or ynext-y<1e-6:continue
  tile=box(x,y,xnext,ynext)
  if not patch.intersects(tile):continue
  for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(patch.intersection(tile))):
   xy=np.array(tri.exterior.coords)[:3]
   if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
   mid=xy.mean(0);d=district(mid);k=len(vp[d]);vp[d].extend([[*q,groundz(q)] for q in xy]);fp[d].append([k,k+1,k+2]);pt=Point(mid);paved=any(r['pad'].covers(pt) for r in sites) or any(w['polygon'].covers(pt) for w in paths);mi[d].append(int(paved));count+=1
for d in ids:
 if not fp[d]:continue
 o=newmesh('V17_Graded_Ground_'+str(d),vp[d],fp[d],soilmat,d,{'surface_type':'terrain','is_walkable_grading':True});o.data.materials.append(pavemat);o.data.polygons.foreach_set('material_index',np.array(mi[d],np.int32))
for rec in sites:
 bottom=min([nearest(soil,q) for q in rec['poly'].exterior.coords]+[rec['floor']+rec['bottom']-.25])-.2;prism(rec['poly'].buffer(.035,join_style=2),rec['floor']-.018,bottom,rec['name']+'_Foundation',props={'is_site_foundation':True,'site_building':rec['name']})
print('GROUND_PATCH',patch.area,count,flush=True)

p['access_v16']=[w for w in p['access_v16'] if w['name'] not in apt_names];p['access_v17']=[{k:(list(v.exterior.coords) if k=='polygon' else list(v.coords) if k=='route' else v) for k,v in w.items()} for w in paths]
alloldstreet=[Polygon(b['footprint']) for b in old['buildings'] if b['zone']=='OLDTOWN']+[Polygon(r['footprint_xy']) for r in old['real_buildings'] if r['instance_name'].startswith('OLDTOWN') and not ('Rear_' in r['instance_name'] or 'Infill_' in r['instance_name'] or 'Backlane_' in r['instance_name'])]
newstreet=[Polygon(b['footprint']) for b in p['buildings'] if b['zone']=='OLDTOWN']+[Polygon(r['footprint_xy']) for r in p['real_buildings'] if r['instance_name'].startswith('OLDTOWN') and not ('Rear_' in r['instance_name'] or 'Infill_' in r['instance_name'] or 'Backlane_' in r['instance_name'])]
oldarea=unary_union(alloldstreet).convex_hull.area;newarea=unary_union(newstreet).convex_hull.area;aptarea=unary_union([r['pad'] for r in apt_sites]).convex_hull.buffer(6.,join_style=2)
p['schema']='hero13.city.regional-update.v17';p['urban_areas_v17']={'oldtown':{'street_buildings_before':243,'street_buildings_after':120,'street_building_limit':120,'rear_buildings':80,'building_units':200,'street_envelope_before_m2':oldarea,'street_envelope_after_m2':newarea,'polygon':list(unary_union(newstreet).convex_hull.exterior.coords),'removed_peripheral_placeholder_names':sorted(removed),'replaced_placeholder_names':replaced,'street_runs':runs},'apartment_destination':{'polygon':list(aptarea.exterior.coords),'source':'User marked red region in IMG_20261029_212434.png','building_units':12,'moved_from_coast':True}}
p['urban_areas_v14']['north_apartments'].update(polygon=list(aptarea.exterior.coords),area_m2=aptarea.area,updated_in='v17',location_description='Inland parcel north of Tianming reservation, as marked by the user')
pool=[]
for key,t in templates.items():
 instances=[r['instance_name'] for r in p['real_buildings'] if r.get('arcade_pool_key')==key];assert len(instances)==3,(key,instances);pool.append({'key':key,'file':t['file'],'baseline_source_instance':t['source'],'source_district':3 if t['source'] else None,'new_source':t['source'] is None,'sha256':t.get('sha256'),'total_instance_limit':3,'instances':instances,'instance_count':len(instances),'replacements_this_version':sum(n.startswith('OLDTOWN_V17_') for n in instances),'width_m':t['width'],'depth_m':t['depth'],'target_height_m':t['target_height'],'no_mirror':True,'scale_policy':'Uniform; legacy corner adaptation retained in the approved template' if key=='10' else 'Uniform; source proportions and textures retained'})
p['arcade_asset_pool']=pool;p['sources']['regional_update_v17']='delivery/city_updates/v17_20261029/tools/build_v17.py'
cnt=collections.Counter(b['zone'] for b in p['buildings']);cnt.update(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN') for r in p['real_buildings']);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),building_count_by_zone=dict(cnt),oldtown_street_buildings=120,oldtown_rear_buildings=80,arcade_pool_types=10,arcade_source_instances=30,source_asset_types=len({r['file'] for r in p['real_buildings']}),source_geometry_texture_types=old['stats']['source_geometry_texture_types']+2)
p['stats'].update(building_coverage_percent=100*(sum(Polygon(b['footprint']).area for b in p['buildings'])+sum(Polygon(r['footprint_xy']).area for r in p['real_buildings']))/p['stats']['land_area_m2'],cbd_planned_total_including_landmark=p['cbd_plan']['planned_total_including_tianming'],cbd_boundary_area_m2=p['cbd_plan']['boundary_area_m2'])
p['stats']['oldtown_building_footprint_m2']=sum(Polygon(b['footprint']).area for b in p['buildings'] if b['zone']=='OLDTOWN')+sum(Polygon(r['footprint_xy']).area for r in p['real_buildings'] if r.get('zone')=='OLDTOWN' or r['instance_name'].startswith('OLDTOWN'))
after={o.name:fingerprint(o) for o in sc.objects if o.type=='MESH'}
report={'version':'v17','baseline_commit':'8b3d8f6249f3da25f681c1aeb1f00144d0605d3b','districts':ids,'city_buildings':p['stats']['buildings'],'street_buildings':120,'oldtown_total_buildings':cnt['OLDTOWN'],'oldtown_street_envelope_before_m2':oldarea,'oldtown_street_envelope_after_m2':newarea,'removed_peripheral_lots':sorted(removed),'replaced_lots':replaced,'arcade_pool':pool,'moved_apartments':sorted(apt_names),'removed_massing_triangles':removed_mass_triangles,'retaining_wall_triangles_removed':wall_removed,'ground_patch_area_m2':patch.area,'ground_patch_triangles':count,'changed_original_objects':[n for n,h in after.items() if n in before and before[n]!=h],'removed_objects':sorted(set(before)-set(after)),'unchanged_original_objects':{n:h for n,h in before.items() if after.get(n)==h},'new_objects':sorted(set(after)-set(before))}
assert p['stats']['buildings']==541 and cnt['OLDTOWN']==200
(R/'model/city_plan.json').write_text(json.dumps(p,ensure_ascii=False,separators=(',',':')));(R/'model/build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(R/'model/site_levels.json').write_text(json.dumps([{k:(list(v.exterior.coords) if k in ['poly','pad'] else v) for k,v in r.items()} for r in sites],indent=2));(R/'asset_pool.json').write_text(json.dumps(pool,ensure_ascii=False,indent=2));(R/'layout_v17_resolved.json').write_text(json.dumps({'retained_street_placeholder_names':[b['name'] for b in p['buildings'] if b['zone']=='OLDTOWN'],'deleted_lots':sorted(deleted),'runs':runs,'apartments':[{'name':r['instance_name'],'center':r['center'],'theta':r['theta'],'floor':r['floor']} for r in apartments]},ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/city_v17.blend'),compress=True);print('V17_BUILD_DONE',p['stats']['buildings'],flush=True)
