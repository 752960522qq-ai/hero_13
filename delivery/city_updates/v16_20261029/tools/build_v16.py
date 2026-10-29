import os
"""Rebuild three v15 districts: color-grouped apartments, compact civic campus,
remaining office tower to CBD, and remove coplanar foundation/apron surfaces.
All source meshes retain UVs and uniform scale. City coordinates are metres.
"""
import bpy,sys,json,math,copy,hashlib,csv
from pathlib import Path
from mathutils import Matrix,Vector
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,os.environ.get('HERO13_CITY_DEPS',str(R.parent/'tools_runtime/blender_deps')));sys.path.insert(0,str(R/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
p=json.load(open(R/'baseline/city_plan.json'));old=copy.deepcopy(p);layout=json.load(open(R/'layout_v16.json'));sites=layout['sites'];removed=set(layout['removed_placeholder_ids']);scene_ids=[6,7,8]
bpy.ops.wm.read_factory_settings(use_empty=True)
for d in scene_ids:bpy.ops.import_scene.gltf(filepath=str(next((R/'baseline').glob(f'{d:02d}_*.glb'))))
bpy.context.view_layer.update();sc=bpy.context.scene
# Bake imported district transforms once; keep names and semantic extras.
for o in list(sc.objects):
 if o.type=='MESH':
  M=o.matrix_world.copy();o.data=o.data.copy();o.data.transform(M);o.parent=None;o.matrix_world=Matrix.Identity(4);o.data.update()
for o in list(sc.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
rootobjects={}
for d in scene_ids:
 root=bpy.data.objects.new(f'District_{d:02d}',None);sc.collection.objects.link(root);root['district_id']=d;rootobjects[d]=root
for o in sc.objects:
 if o.type=='MESH':o.parent=rootobjects[int(o.get('district_id',int(o.name[1:3])))];o.matrix_parent_inverse=Matrix.Identity(4)
def district(xy):return 6 if xy[0]<0 else 7 if xy[0]<500 else 8
def xyworld(o):return np.array([v.co[:] for v in o.data.vertices],float)
def projected(o):
 o.data.calc_loop_triangles();co=xyworld(o);return unary_union([Polygon(co[list(t.vertices),:2]) for t in o.data.loop_triangles if Polygon(co[list(t.vertices),:2]).area>1e-7])
def geometry_hash(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in o.data.vertices],dtype='<f4').tobytes())
 for t in o.data.polygons:h.update(np.array(t.vertices[:],dtype='<i4').tobytes())
 for uv in o.data.uv_layers:h.update(np.array([v.uv[:] for v in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()
before={o.name:geometry_hash(o) for o in sc.objects if o.type=='MESH'}
soil=HeightField([o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'])
walktypes={'sidewalk','pedestrian','source_access','backlane_entry_walk','backlane_seam_stitch','v12_access_walk','v13_access_walk','v14_access_walk','v15_access_walk'}
basewalk_names={w['name'] for w in p['pedestrian_alleys']}
def walk_obj(o):return o.type=='MESH' and (o.get('surface_type') in walktypes or o.get('source_object') in basewalk_names)
# Exclude site-specific surfaces when sampling actual public sidewalks.
streetwalk=HeightField([o for o in sc.objects if walk_obj(o) and o.get('surface_type') in ['sidewalk','pedestrian']])
land=Polygon(p['coasts']['MAIN']);roads=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.01,join_style=2) for e in p['edges']]);carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.05,join_style=2) for e in p['edges']]);reserve=Polygon(p['cbd_plan']['tianming']['polygon'])
realmap={r['instance_name']:r for r in p['real_buildings']};govold=[b for b in p['buildings'] if b['zone']=='GOVERNMENT'];aptold=[b for b in p['buildings'] if b['zone']=='APARTMENT'];oldsite_names={b['name'] for b in govold+aptold}|{'GOV_V14_G33','APT_V14_A36'}
restores=[]
for r in govold+aptold+[realmap['GOV_V14_G33'],realmap['APT_V14_A36']]:restores.append(Polygon(r.get('pad_xy',r.get('footprint',r.get('footprint_xy')))).buffer(.15,join_style=2))
for o in list(sc.objects):
 if o.type!='MESH':continue
 source=o.get('source_object','');remove=False
 if 'MAIN_CIVIC_Massing_' in source:remove=True
 if any(source==name or source.startswith(name+'_') for name in oldsite_names):
  if source.endswith('_Source_Mesh_00') and source.startswith(('GOV_V14_G33','APT_V14_A36')):continue
  if walk_obj(o):restores.append(projected(o).buffer(.02))
  remove=True
 if remove:bpy.data.objects.remove(o,do_unlink=True)
# Restore vacated sites, and remove obsolete civic retaining segments.
restore=unary_union(restores).difference(roads.buffer(.02)).difference(reserve.buffer(.02));oldgov=Polygon(old['urban_areas_v14']['municipal_campus']['polygon']);wallclean=unary_union([restore.buffer(.7),oldgov.buffer(1.)]);removed_wall_triangles=0
# Triangles here have no UVs; preserve material indices on all retained faces.
def simple_replace(o,verts,faces,mats):
 oldmesh=o.data;m=bpy.data.meshes.new(oldmesh.name+'_v16');m.from_pydata(verts,[],faces)
 for mat in oldmesh.materials:m.materials.append(mat)
 m.polygons.foreach_set('material_index',np.array(mats,np.int32));m.update();o.data=m
for o in list(sc.objects):
 if o.type!='MESH' or o.get('surface_type')!='terrain_cut_retaining_wall':continue
 co=xyworld(o);keep=[]
 for face in o.data.polygons:keep.append(not wallclean.covers(Point(co[list(face.vertices),:2].mean(0))))
 removed_wall_triangles+=len(keep)-sum(keep)
 if not all(keep):
  if not any(keep):bpy.data.objects.remove(o,do_unlink=True)
  else:simple_replace(o,co.tolist(),[list(f.vertices) for f,k in zip(o.data.polygons,keep) if k],[f.material_index for f,k in zip(o.data.polygons,keep) if k])
# Root cause fix: remove only foundation top area already occupied by the apron.
black_fixes=[]
for o in list(sc.objects):
 if o.type!='MESH' or not o.get('source_object','').endswith('_Foundation'):continue
 source=o['source_object'];name=source[:-len('_Foundation')];r=realmap.get(name)
 if not r:continue
 walks=[w for w in sc.objects if w.type=='MESH' and w.get('source_object','').startswith(name+'_') and w.get('surface_type')=='v15_access_walk']
 if not walks:continue
 co=xyworld(o);o.data.calc_loop_triangles();top=co[:,2].max();body=Polygon(r['footprint_xy']).buffer(.035,join_style=2);vv=[];ff=[];mats=[];removed_area=0.
 for tri in o.data.loop_triangles:
  q=co[list(tri.vertices)];parts=[q]
  if np.ptp(q[:,2])<.001 and abs(q[:,2].mean()-top)<.001:
   shape=Polygon(q[:,:2]);clipped=shape.intersection(body);removed_area+=shape.area-clipped.area;parts=[]
   if not clipped.is_empty:
    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(clipped)):
     xy=np.array(t.exterior.coords)[:3]
     if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
     parts.append(np.c_[xy,np.full(3,top)])
  for q in parts:k=len(vv);vv.extend(q.tolist());ff.append([k,k+1,k+2]);mats.append(o.data.polygons[tri.polygon_index].material_index)
 if removed_area>.01:simple_replace(o,vv,ff,mats);black_fixes.append({'foundation':o.name,'removed_coplanar_top_m2':removed_area})
print('BLACK_FIX',len(black_fixes),sum(x['removed_coplanar_top_m2'] for x in black_fixes),flush=True)
legacy_walks=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='v15_access_walk']
legacy_field=HeightField(legacy_walks)
legacy_shape=unary_union([projected(o) for o in legacy_walks])
legacy_bodies=unary_union([Polygon(r['footprint_xy']).buffer(.045,join_style=2) for r in p['real_buildings'] if r['instance_name'].startswith('CBD_') or r['instance_name'] in ['APT_V14_A32','APT_V14_A35']])
legacy_mask=unary_union([legacy_shape,legacy_bodies])
for o in list(sc.objects):
 if o.type=='MESH' and o.get('source_object','').startswith(('V15_Access_Retaining_Sides','V15_Site_Perimeter_Retaining_Walls')):
  removed_wall_triangles+=len(o.data.polygons);bpy.data.objects.remove(o,do_unlink=True)

def material(name,col):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=.85;return m
soilmat=material('V16_Landscape_Ground',(.52,.56,.48));pavemat=material('V16_Campus_Paving',(.53,.54,.49));baseMat=material('V16_Foundation_Concrete',(.43,.45,.42));placeholderMat=material('V16_Civic_Plaster',(.63,.63,.59))
def newmesh(name,verts,faces,mat,d=None,props=None):
 m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o)
 if d is None:d=district(np.mean(np.array(verts),axis=0)[:2])
 o.parent=rootobjects[d];o['district_id']=d;o['source_object']=name;o['modified_in_version']='v16'
 if props:
  for k,v in props.items():o[k]=v
 return o
# Load reusable source meshes once. Four apartments of each type share mesh data.
templates={}
for file in sorted({s['file'] for s in sites if s.get('file')}):
 beforeobjs=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(R/'sources'/file));bpy.context.view_layer.update();imported=set(sc.objects)-beforeobjs;data=[]
 for ob in imported:
  if ob.type=='MESH':m=ob.data.copy();m.transform(ob.matrix_world);data.append(m)
 co=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in data]);templates[file]={'meshes':data,'lo':co.min(0),'hi':co.max(0)}
 for ob in imported:bpy.data.objects.remove(ob,do_unlink=True)
def nearest_soil(q):
 z=soil.height(q)
 if z is not None:return z
 hit,_,idx,_=soil.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=soil.tri[idx];weights=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1.]);return float(weights@tri[:,2])
# Compact municipal campus keeps the main and four support volumes, replacing
# empty massing with the supplied office and dormitory models.
govsite=unary_union([Polygon(s['footprint']) for s in sites if s['kind']=='GOVERNMENT']+[Polygon(realmap['GOV_V14_G33']['footprint_xy'])]).convex_hull.buffer(5.,join_style=2)
def campus_plane(q):return 18.35+.002*(q[0]-490)-.003*(q[1]-850)
bodyrecords=[];newreal=[];newbox=[]
for s in sites:
 name=s['id'];poly=Polygon(s['footprint']);kind=s['kind'];xy=np.array(s['center'],float)
 if kind=='GOVERNMENT':floor=max(campus_plane(q) for q in poly.exterior.coords)+.055
 else:
  vals=[nearest_soil(q) for q in shapely.segmentize(poly.exterior,2.).coords];floor=float(np.median(vals))+.07
 rec={'name':name,'kind':kind,'center':s['center'],'poly':poly,'pad':poly.buffer(2.4,join_style=2),'floor':floor,'group':s.get('group'),'height':s['target_height_m']}
 bodyrecords.append(rec)
 if name=='APT_V14_A36':
  ob=next(o for o in sc.objects if o.type=='MESH' and o.get('source_instance')==name);co=xyworld(ob);oldcenter=np.array(realmap[name]['center']);theta=math.radians(s['theta_degrees']);oldtheta=realmap[name]['theta'];delta=theta-oldtheta;T=Matrix.Translation((*xy,floor))@Matrix.Rotation(delta,4,'Z')@Matrix.Translation((-oldcenter[0],-oldcenter[1],-float(co[:,2].min())));ob.data.transform(T);ob.parent=rootobjects[district(xy)];ob['district_id']=district(xy);ob['zone']='CBD';ob['modified_in_version']='v16';r=realmap[name];r.update(center=s['center'],anchor=s['footprint'][0],floor=floor,footprint_xy=s['footprint'],pad_xy=list(poly.buffer(.035,join_style=2).exterior.coords),theta=theta,angle=s['theta_degrees'],zone='CBD',typology='office_source_building',use_corrected_in='v16',modified_in_version='v16',access_alley='V16_Graded_Ground')
 elif s.get('file'):
  t=templates[s['file']];scale=s['target_height_m']/(t['hi'][2]-t['lo'][2]);theta=math.radians(s['theta_degrees']);mid=(t['lo']+t['hi'])/2;T=Matrix.Translation((*xy,floor))@Matrix.Rotation(theta,4,'Z')@Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation((-mid[0],-mid[1],-t['lo'][2]))
  for j,m in enumerate(t['meshes']):
   ob=bpy.data.objects.new(name+f'_Source_Mesh_{j:02d}',m);sc.collection.objects.link(ob);ob.parent=rootobjects[district(xy)];ob.matrix_world=T;ob['district_id']=district(xy);ob['source_object']=ob.name;ob['source_instance']=name;ob['source_filename']=s['file'];ob['zone']=kind;ob['is_building_instance']=True;ob['added_in_version']='v16'
  newreal.append({'instance_name':name,'file':s['file'],'source_filename':s['file'],'source_sha256':hashlib.sha256((R/'sources'/s['file']).read_bytes()).hexdigest(),'uniform_scale':scale,'local_axis_scale':[1,1,1],'source_bounds':[t['lo'].tolist(),t['hi'].tolist()],'target_height_m':s['target_height_m'],'source_floor_reference':float(t['lo'][2]),'theta':theta,'angle':s['theta_degrees'],'anchor':list(poly.exterior.coords)[0],'center':s['center'],'footprint_xy':s['footprint'],'pad_xy':list(poly.buffer(.035,join_style=2).exterior.coords),'floor':floor,'region':'MAIN','zone':kind,'typology':'municipal_dormitory' if 'DORM' in name else 'municipal_office' if 'OFFICE' in name else 'apartment_highrise','building_count_units':1,'asset_color_group':s.get('group'),'reuse_mesh_data':True,'added_in_version':'v16','access_alley':'V16_Graded_Ground'})
 else:
  newbox.append({'name':name,'region':'MAIN','zone':'GOVERNMENT','center':s['center'],'footprint':s['footprint'],'base':floor,'height':s['target_height_m'],'size':[30,34,s['target_height_m']],'typology':'civic_support_placeholder','building_count_units':1,'added_or_modified_in':'v16'})
# Lower the retained main to the same graded civic site, without altering it.
r=realmap['GOV_V14_G33'];poly=Polygon(r['footprint_xy']);floor=max(campus_plane(q) for q in poly.exterior.coords)+.055;ob=next(o for o in sc.objects if o.type=='MESH' and o.get('source_instance')=='GOV_V14_G33');co=xyworld(ob);ob.data.transform(Matrix.Translation((0,0,floor-float(co[:,2].min()))));r.update(floor=floor,pad_xy=list(poly.buffer(.035,join_style=2).exterior.coords),modified_in_version='v16',access_alley='V16_Graded_Ground');bodyrecords.append({'name':'GOV_V14_G33','kind':'GOVERNMENT','center':r['center'],'poly':poly,'pad':poly.buffer(2.4,join_style=2),'floor':floor,'height':r['target_height_m'],'group':None})
# Foundations expose a narrow plinth only. Ground and foundation have disjoint
# top polygons; no apron is superimposed on a foundation top surface.
def prism(poly,top,bottom,name,mat=baseMat,prop=None):
 xy=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:-1];n=len(xy);vv=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]];ff=[]
 for i in range(1,n-1):ff.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;ff.extend([[i,j,j+n],[i,j+n,i+n]])
 return newmesh(name,vv.tolist(),ff,mat,props=prop)
for rec in bodyrecords:
 poly=rec['poly'];floor=rec['floor'];bottom=min([nearest_soil(q) for q in poly.exterior.coords]+[floor-1.])-.2;prism(poly.buffer(.035,join_style=2),floor-.018,bottom,rec['name']+'_Foundation',prop={'is_site_foundation':True,'site_building':rec['name']})
 if rec['name'].startswith('GOV_V16_SUPPORT_'):prism(poly,floor+rec['height'],floor,rec['name'],placeholderMat,{'is_placeholder':True,'site_building':rec['name']})
# Apartment access paths run to the actual street sidewalk, not across traffic.
goals=[]
for e in p['edges']:
 if e['region']!='MAIN':continue
 line=LineString(np.array(e['points'])[:,:2])
 for side in ['left','right']:
  for g in shapely.get_parts(line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.60,side,join_style=2)):
   if g.geom_type=='LineString':goals.append((e['name']+'_'+side,g))
fixedfoot=unary_union([Polygon(b['footprint']) for b in p['buildings'] if b['name'] not in removed]+[Polygon(r['footprint_xy']) for r in p['real_buildings'] if r['instance_name'] not in ['APT_V14_A36','GOV_V14_G33']]+[reserve])
paths=[]
for rec in [r for r in bodyrecords if r['kind']!='GOVERNMENT']:
 poly=rec['poly'];coords=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:4];blocked=unary_union([fixedfoot]+[r['pad'].buffer(.10) for r in bodyrecords if r['name']!=rec['name']]);opts=[]
 for aa,bb in zip(coords,np.roll(coords,-1,axis=0)):
  mid=(aa+bb)/2;u=(bb-aa)/np.linalg.norm(bb-aa);normal=np.array([u[1],-u[0]]);start=mid+normal*2.45
  for gn,g in sorted(goals,key=lambda z:z[1].distance(Point(start)))[:12]:
   for offset in [0.,-4.,4.,-8.,8.]:
     end=np.array(g.interpolate(np.clip(g.project(Point(start))+offset,0,g.length)).coords[0]);route=LineString([start,end]);L=route.length
     if L<.4 or L>90 or (end-start)@normal/L<.70:continue
     corridor=route.buffer(1.6,cap_style=2)
     if corridor.intersection(carriage).area>.001 or corridor.intersection(blocked).area>.001 or corridor.intersection(poly).area>.001 or not land.covers(corridor):continue
     gz=streetwalk.height(end)
     if gz is None:continue
     grade=abs(rec['floor']-.025-gz)/max(.5,L)
     if grade>.18:continue
     opts.append((L+grade*40,route,gn,float(gz),grade))
 if not opts:raise RuntimeError(('No apartment/CBD access',rec['name']))
 _,route,gn,gz,grade=min(opts,key=lambda x:x[0]);paths.append({'name':rec['name'],'route':route,'polygon':route.buffer(1.6,cap_style=2),'floor':rec['floor']-.025,'goal_z':gz,'goal_name':gn,'grade':grade})
# Civic pedestrian links connect both existing side streets through the campus.
for start in [[405,835],[572,850]]:
 opts=[]
 for gn,g in sorted(goals,key=lambda z:z[1].distance(Point(start)))[:10]:
  end=np.array(g.interpolate(g.project(Point(start))).coords[0]);route=LineString([start,end]);corr=route.buffer(2.,cap_style=2);gz=streetwalk.height(end)
  if gz is None or route.length<4 or corr.intersection(carriage).area>.001 or corr.intersection(fixedfoot).area>.001:continue
  if any(corr.intersects(rec['poly']) for rec in bodyrecords):continue
  grade=abs(campus_plane(start)-gz)/route.length
  if grade>.12:continue
  opts.append((route.length,route,gn,float(gz),grade))
 if not opts:raise RuntimeError(('No civic pedestrian link',start))
 _,route,gn,gz,grade=min(opts,key=lambda x:x[0]);paths.append({'name':'Civic_Link_'+str(len(paths)),'route':route,'polygon':route.buffer(2.,cap_style=2),'floor':campus_plane(start),'goal_z':gz,'goal_name':gn,'grade':grade})
# One graded terrain/pavement skin replaces old holes and old large dark walls.
newpads=unary_union([r['pad'].buffer(7.,join_style=2) for r in bodyrecords]);pathareas=unary_union([w['polygon'].buffer(5.,join_style=2) for w in paths]);patch=unary_union([restore,newpads,pathareas,govsite.buffer(15.,join_style=2)]).intersection(land).difference(roads.buffer(.001)).difference(reserve.buffer(.015));newholes=unary_union([r['poly'].buffer(.045,join_style=2) for r in bodyrecords]);patch=unary_union([patch,legacy_shape.buffer(5.).difference(legacy_mask.buffer(.005))]).difference(newholes).difference(legacy_mask.buffer(.005)).difference(roads.buffer(.001)).difference(reserve.buffer(.015))
# Cut old terrain triangles with barycentric interpolation; retain colors.
for o in list(sc.objects):
 if o.type!='MESH' or o.get('surface_type')!='terrain':continue
 m=o.data;m.calc_loop_triangles();co=xyworld(o);local=patch.union(newholes).intersection(box(co[:,0].min(),co[:,1].min(),co[:,0].max(),co[:,1].max()))
 if local.is_empty:continue
 vv=[];ff=[];mats=[];cols=[];changes=0;color=m.color_attributes[0] if m.color_attributes else None
 for tr in m.loop_triangles:
  xyz=co[list(tr.vertices)];shape=Polygon(xyz[:,:2]);pieces=[xyz]
  if shape.area<1e-10:continue
  if shape.intersects(local):
   diff=shape.difference(local)
   if shape.area-diff.area>1e-8:
    changes+=1;pieces=[]
    for q in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
     xy=np.array(q.exterior.coords)[:3];weights=np.linalg.solve(np.vstack([xyz[:,:2].T,np.ones(3)]),np.vstack([xy.T,np.ones(3)]));pieces.append(np.c_[xy,weights.T@xyz[:,2]])
  for q in pieces:
   if np.cross(q[1,:2]-q[0,:2],q[2,:2]-q[0,:2])<0:q=q[::-1]
   k=len(vv);vv.extend(q.tolist());ff.append([k,k+1,k+2]);mats.append(m.polygons[tr.polygon_index].material_index)
   if color:
    ids=list(tr.vertices) if color.domain=='POINT' else list(tr.loops);cc=np.array([color.data[i].color[:] for i in ids]);weights=np.linalg.solve(np.vstack([xyz[:,:2].T,np.ones(3)]),np.vstack([q[:,:2].T,np.ones(3)]));cols.extend((weights.T@cc).tolist())
 if changes:
  simple_replace(o,vv,ff,mats)
  if cols:o.data.color_attributes.new(name=color.name,type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(cols,np.float32).ravel())
# Exact pixel geometry is sampled from a 3 m grid; platform perimeters are
# represented by the building cut boundary and stay above the finished skin.
soilcache={}
def oldheight(q):
 key=(round(float(q[0]),5),round(float(q[1]),5))
 if key not in soilcache:soilcache[key]=nearest_soil(q)
 return soilcache[key]
def ground_height(q):
 point=Point(q);z=oldheight(q);dist=point.distance(legacy_shape)
 if dist<5:
  hit,_,idx,_=legacy_field.tree.find_nearest(Vector((float(q[0]),float(q[1]),0)));tri=legacy_field.tri[idx];weights=np.linalg.solve(np.vstack([tri[:,:2].T,np.ones(3)]),np.r_[np.array(hit[:2]),1.]);h=float(weights@tri[:,2])-.015;t=1-dist/5;t=t*t*(3-2*t);z=z*(1-t)+h*t
 dist=point.distance(govsite)
 if dist<15:
  t=max(0,1-dist/15);t=t*t*(3-2*t);z=z*(1-t)+campus_plane(q)*t
 for rec in bodyrecords:
  d=point.distance(rec['pad'])
  if d<7:
   t=max(0,1-d/7);t=t*t*(3-2*t);z=z*(1-t)+(rec['floor']-.025)*t
 for w in paths:
  d=point.distance(w['polygon'])
  if d>=5:continue
  route=w['route'];s=route.project(point);t=float(np.clip(s/route.length,0,1));h=w['floor']*(1-t)+w['goal_z']*t;mix=max(0,1-d/5);mix=mix*mix*(3-2*mix);z=z*(1-mix)+h*mix
 for rec in bodyrecords:
  if rec['pad'].covers(point):return rec['floor']-.025
 return z
vparts={d:[] for d in scene_ids};fparts={d:[] for d in scene_ids};miparts={d:[] for d in scene_ids};xmin,ymin,xmax,ymax=patch.bounds;tiles=0
for x in np.arange(math.floor(xmin/3)*3,xmax,3):
 for y in np.arange(math.floor(ymin/3)*3,ymax,3):
  tile=box(x,y,x+3,y+3)
  if not patch.intersects(tile):continue
  piece=patch.intersection(tile)
  for t in shapely.get_parts(shapely.constrained_delaunay_triangles(piece)):
   xy=np.array(t.exterior.coords)[:3]
   if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
   mid=xy.mean(0);d=district(mid);k=len(vparts[d]);vparts[d].extend([[*q,ground_height(q)] for q in xy]);fparts[d].append([k,k+1,k+2]);pt=Point(mid);paved=govsite.covers(pt) or any(w['polygon'].covers(pt) for w in paths) or any(rec['pad'].covers(pt) for rec in bodyrecords);miparts[d].append(int(paved));tiles+=1
for d in scene_ids:
 if not fparts[d]:continue
 ob=newmesh('V16_Graded_Ground_'+str(d),vparts[d],fparts[d],soilmat,d,{'surface_type':'terrain','is_walkable_grading':True});ob.data.materials.append(pavemat);ob.data.polygons.foreach_set('material_index',np.array(miparts[d],np.int32))
print('GROUND_PATCH',tiles,patch.area,flush=True)
# Canonical source records and current district metadata.
p['buildings']=[b for b in p['buildings'] if b['name'] not in removed]+newbox;p['real_buildings'].extend(newreal)
for k in ['access_v14','access_v15','cbd_access_v13','infill_access_v12']:
 if k in p:p[k]=[w for w in p[k] if w.get('building',w.get('instance_name')) not in oldsite_names and not any(w.get('name','').startswith(n+'_') for n in oldsite_names)]
p['access_v16']=[{k:(list(v.exterior.coords) if k=='polygon' else list(v.coords) if k=='route' else v) for k,v in w.items()} for w in paths]
p['schema']='hero13.city.regional-update.v16';p['cbd_plan'].update(existing_buildings=32,source_buildings=32,planned_total_including_tianming=33,version='v16');p['urban_areas_v14']['north_apartments'].update(source_towers=[r['instance_name'] for r in newreal if r['zone']=='APARTMENT'],midrise_placeholders=[],building_units=12,source_tower_use='residential apartment towers grouped by source color',updated_in='v16',color_groups={g:[r['instance_name'] for r in newreal if r.get('asset_color_group')==g] for g in ['YELLOW_50','PINK_53','GRAY_54']});p['urban_areas_v14']['municipal_campus'].update(polygon=list(govsite.exterior.coords),area_m2=govsite.area,main_building='GOV_V14_G33',support_buildings=[b['name'] for b in newbox],office_building='GOV_V16_OFFICE_51',dormitory_building='GOV_V16_DORM_52',building_units=7,relocated_in='v16')
from collections import Counter
cnt=Counter(b['zone'] for b in p['buildings']);cnt.update(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN') for r in p['real_buildings']);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),cbd_buildings=32,apartment_buildings=12,government_area_buildings=7,building_count_by_zone=dict(cnt))
p['stats']['source_asset_types']=len({r['file'] for r in p['real_buildings']});p['stats']['source_geometry_texture_types']=old['stats'].get('source_geometry_texture_types',51)+5;p['sources']['regional_update_v16']='delivery/city_updates/v16_20261029/tools/build_v16.py'
assert p['stats']['buildings']==664 and len(newreal)==14
MODEL=R/'model';MODEL.mkdir(exist_ok=True);(MODEL/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(MODEL/'site_levels.json').write_text(json.dumps([{k:(list(v.exterior.coords) if k in ['poly','pad'] else v) for k,v in rec.items()} for rec in bodyrecords],indent=2));after={o.name:geometry_hash(o) for o in sc.objects if o.type=='MESH'}
report={'version':'v16','base_commit':'c07e0daefeef82c0d79274bef16ecf8b3b3d4f42','districts':[6,7,8],'city_buildings':664,'placeholder_count':len(p['buildings']),'source_instances':len(p['real_buildings']),'apartment_instances':12,'apartment_groups':3,'moved_to_CBD':'APT_V14_A36','black_edge_foundations_fixed':black_fixes,'obsolete_wall_triangles_removed':removed_wall_triangles,'municipal_area_before_m2':old['urban_areas_v14']['municipal_campus']['area_m2'],'municipal_area_after_m2':govsite.area,'ground_patch_area_m2':patch.area,'ground_patch_triangles':tiles,'changed_original_objects':[n for n,h in after.items() if n in before and h!=before[n]],'removed_objects':sorted(set(before)-set(after)),'unchanged_original_objects':{n:h for n,h in before.items() if after.get(n)==h},'new_objects':sorted(set(after)-set(before))}
(MODEL/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(MODEL/'city_v16.blend'),compress=True);print('V16_BUILD_DONE',len(bodyrecords),len(newreal),govsite.area,flush=True)
