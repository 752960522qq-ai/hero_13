"""Consolidate the CBD to 29 buildings plus a protected Tianming landmark site.

Run in Blender 4.5: --baseline SNAPSHOT --uploads DIR --out DIR --sources DIR --deps DIR
All prior roads, source instances, arcades and access surfaces remain unchanged.
"""
import bpy,sys,json,math,hashlib,collections,shutil,csv,argparse
from pathlib import Path
import numpy as np
from mathutils import Matrix
ap=argparse.ArgumentParser()
for k in ['baseline','uploads','out','sources','deps']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(Path(__file__).parent))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
BASE=a.baseline.resolve();OUT=a.out.resolve();SRC=a.sources.resolve();OUT.mkdir(parents=True,exist_ok=True);SRC.mkdir(parents=True,exist_ok=True)
p=json.loads((BASE/'city_plan.json').read_text());old_count=len(p['buildings'])+len(p['real_buildings']);assert old_count==682
uploads=[
 ('C30','01-modern-office-building-3d-model-30.glb','cbd_office_30.glb',62.,'cbd'),
 ('C29','02-office-building-3d-model-29.glb','cbd_office_29.glb',30.,'cbd'),
 ('C28','03-modern-office-building-3d-model-28.glb','cbd_office_28.glb',32.,'cbd'),
 ('C27','04-modern-office-building-3d-model27.glb','cbd_office_27.glb',64.,'cbd')]
for f in (BASE/'source/buildings').glob('*.glb'):
 if not (SRC/f.name).exists():shutil.copy2(f,SRC/f.name)
for key,original,name,height,kind in uploads:shutil.copy2(a.uploads/original,SRC/name)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'));sc=bpy.context.scene;bpy.context.view_layer.update()
root=bpy.data.objects['Huizhou_Reconstructed_City_3p25km2'];sourceparent=bpy.data.objects['07_SOURCE_BUILDINGS'];footparent=bpy.data.objects['08_BUILDING_FOOTINGS'];walkparent=bpy.data.objects['10_PEDESTRIAN_NETWORK']
terrain_obs=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'];soil=HeightField(terrain_obs)
walk_names={r['name'] for r in p['pedestrian_alleys']}
oldwalk_obs=[o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['sidewalk','backlane_entry_walk','backlane_seam_stitch','v12_access_walk'] or o.name in walk_names)]
oldwalk=HeightField(oldwalk_obs)
walk_tri_polys=[Polygon(tr[:,:2]) for tr in oldwalk.tri];walk_tree=shapely.STRtree(walk_tri_polys)
concrete=bpy.data.materials['Bridge_Concrete'];atlas=bpy.data.materials['Road_Modular_Original_Atlas'];seammat=bpy.data.materials['Oldtown_Seam_Plaster']
def mesh(name,v,f,mat,parent,uv=False):
 m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=parent
 if uv:
  layer=m.uv_layers.new(name='UVMap')
  for li,loop in enumerate(m.loops):
   q=m.vertices[loop.vertex_index].co;layer.data[li].uv=(.216+.055*((q.x/3)%1),.5989+.1777*((q.y/16.9048)%1))
 return o
def prism(poly,top,bottom,name,mat=concrete):
 xy=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:-1];n=len(xy);v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]];f=[]
 for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
 return mesh(name,v.tolist(),f,mat,footparent)
templates={}
for key,original,file,height,kind in uploads:
 before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(SRC/file));bpy.context.view_layer.update();imported=set(sc.objects)-before;parts=[]
 for ob in imported:
  if ob.type!='MESH':continue
  data=ob.data.copy();data.transform(ob.matrix_world);parts.append(data)
 co=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=co.min(0);hi=co.max(0);s=height/(hi[2]-lo[2])
 templates[key]={'parts':parts,'lo':lo,'hi':hi,'dim':hi-lo,'height':height,'scale':s,'width':(hi[0]-lo[0])*s,'depth':(hi[1]-lo[1])*s,'file':file,'original':original,'kind':kind}
 for ob in imported:bpy.data.objects.remove(ob,do_unlink=True)
 print('NEW_TEMPLATE',key,height,templates[key]['width'],templates[key]['depth'],flush=True)
land=unary_union([Polygon(c) for c in p['coasts'].values()]).difference(Polygon(p['lake']))
carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.12) for e in p['edges'] if e['layer'].startswith('GROUND')])
road_full=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.10) for e in p['edges']])
oldped=unary_union([LineString(r['points']).buffer(r['width']/2+.005,cap_style=2) for r in p['pedestrian_alleys']]+[Polygon(r['polygon']) for r in p['rear_rows']])
all_buildings=[Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]
placed=[];new_walks=[];partywalls=[];candidate_log=[]
def descriptor(key,name,face,theta,floor,zone,**extra):
 t=templates[key];u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);w=t['width'];d=t['depth'];face=np.array(face);xy=np.array([face,face+u*w,face+u*w-n*d,face-n*d]);poly=Polygon(xy)
 rec={'instance_name':name,'file':t['file'],'source_filename':t['file'],'original_upload_name':t['original'],'source_key':key,'uniform_scale':t['scale'],'local_axis_scale':[1.,1.,1.],'target_height_m':t['height'],'source_bounds':[t['lo'].tolist(),t['hi'].tolist()],'source_floor_reference':float(t['lo'][2]),'turn':0.,'left':0.,'right':w,'front':0.,'anchor':face.tolist(),'theta':theta,'angle':math.degrees(theta),'center':list(poly.centroid.coords[0]),'region':'MAIN','zone':zone,'footprint_xy':xy.tolist(),'pad_xy':list(poly.buffer(.08,join_style=2).exterior.coords),'floor':float(floor),'direct_sidewalk_frontage':False,'direct_alley_frontage':True,'building_count_units':1,'typology':'backlane_source_house' if zone=='OLDTOWN' else 'office_source_building','reuse_rotation_only_no_mirror':True,'added_in_version':'v13',**extra}
 return rec
def legal_house(poly,blocked,other_walks=None):
 if not land.covers(poly.buffer(.10)):return False
 if poly.intersection(blocked).area>1e-5 or poly.intersection(road_full).area>1e-5:return False
 if other_walks is not None and poly.intersection(other_walks).area>.005:return False
 return True

cbd_boundary=box(-390.,650.,460.,1080.)
reservation=box(-375.,735.,-203.,930.)
keepnames={'MAIN_CBD_0011','MAIN_CBD_0054','MAIN_CBD_0055','MAIN_CBD_0051','MAIN_CBD_0052','MAIN_CBD_0003','MAIN_CBD_0007','MAIN_CBD_0006','MAIN_CBD_0066','MAIN_CBD_0076','MAIN_CBD_0065','MAIN_CBD_0068','MAIN_CBD_0074','MAIN_CBD_0093','MAIN_CBD_0083'}
removed={i for i,b in enumerate(p['buildings']) if b['zone']=='CBD' and b['name'] not in keepnames};assert len(removed)==34
assert len([b for b in p['buildings'] if b['name'] in keepnames])==15
retained=[Polygon(b['footprint']) for i,b in enumerate(p['buildings']) if i not in removed]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]
assert reservation.intersection(unary_union(retained)).area<1e-5
assert reservation.intersection(road_full).area<1e-5
oldped=unary_union([oldped]+[Polygon(w['polygon']) for w in p['infill_access_v12']])
goals=[]
for e in p['edges']:
 if e['region']!='MAIN' or not e['layer'].startswith('GROUND'):continue
 line=LineString(np.array(e['points'])[:,:2])
 for side in ['left','right']:
  goal=line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)
  if goal.geom_type=='LineString':goals.append({'name':e['name']+'_'+side,'line':goal})
def find_route(start,blocked):
 options=[];start=np.array(start)
 for g in sorted(goals,key=lambda g:g['line'].distance(Point(start)))[:16]:
  s=g['line'].project(Point(start))
  for off in [0,-6,6,-14,14,-26,26]:
   end=np.array(g['line'].interpolate(np.clip(s+off,0,g['line'].length)).coords[0]);variants=[[start,end],[start,np.array([start[0],end[1]]),end],[start,np.array([end[0],start[1]]),end]]
   for coords in variants:
    coords=np.array([q for i,q in enumerate(coords) if i==0 or np.linalg.norm(q-coords[i-1])>.01])
    if len(coords)<2:continue
    route=LineString(coords);nav=route.buffer(1.8,cap_style=2,join_style=2)
    if nav.intersection(blocked).area>1e-4 or nav.intersection(carriage).area>1e-4 or not land.covers(nav):continue
    z=oldwalk.height(end)
    if z is not None:options.append((route.length,g,coords,z))
 return sorted(options,key=lambda v:v[0])
for key,center in {'C30':[-154.,1040.],'C29':[-130.,852.],'C28':[311.,1005.],'C27':[411.,804.]}.items():
 t=templates[key];center=np.array(center,float)
 blocked=unary_union(retained+[reservation]);options=[]
 for theta in [0.,math.pi/2,math.pi,-math.pi/2]:
  u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);face=center+n*t['depth']/2-u*t['width']/2;poly=Polygon([face,face+u*t['width'],face+u*t['width']-n*t['depth'],face-n*t['depth']])
  if not legal_house(poly,blocked,oldped) or not cbd_boundary.covers(poly):continue
  fore=Polygon([face-u*.02,face+u*(t['width']+.02),face+u*(t['width']+.02)+n*3.9,face-u*.02+n*3.9])
  if fore.intersection(blocked).area>.001 or fore.intersection(carriage).area>.001:continue
  routes=find_route(face+u*t['width']/2+n*2.0,unary_union([blocked,poly]))
  for L,g,coords,z in routes[:1]:
   options.append((L,theta,face,poly,fore,g,coords,z))
 if not options:raise RuntimeError(('CBD site has no fitting footprint and access',key,center.tolist()))
 L,theta,face,poly,fore,g,coords,gz=min(options,key=lambda v:v[0]);u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);route=LineString(coords);goal=coords[-1]
 direction=coords[-1]-coords[-2];direction/=np.linalg.norm(direction);join=0.
 for d in np.arange(.1,min(5.,L),.1):
  if oldwalk.height(goal-direction*d) is None:break
  join=float(d)
 ramp_start=max([route.project(Point(q)) for part in shapely.get_parts(route.intersection(fore)) if part.geom_type=='LineString' for q in part.coords] or [0.]);ramp_end=max(ramp_start+.25,L-join)
 terrain_center=soil.height(center);allow=.024*max(.25,ramp_end-ramp_start);surface_floor=gz+.001+float(np.clip((terrain_center if terrain_center is not None else gz)-gz,-allow,allow));floor=surface_floor+.028
 name='CBD_Imported_Office'+key[1:];walkname=name+'_Entrance_Plaza';rec=descriptor(key,name,face,theta,floor,'CBD',access_alley=walkname,replaces_placeholder_sites=[b['name'] for i,b in enumerate(p['buildings']) if i in removed and Polygon(b['footprint']).intersects(poly)],unique_cbd_use=True)
 zz=[soil.height(q) for q in shapely.segmentize(poly.buffer(.1,join_style=2),2).exterior.coords];zz=[v for v in zz if v is not None];rec['foundation_bottom_m']=min([floor-.45,*zz])-.12
 paving=unary_union([fore,route.buffer(1.8,cap_style=2,join_style=2)])
 assert paving.intersection(blocked).area<.004 and paving.intersection(carriage).area<.004
 grad=[]
 for axis in range(2):
  dd=np.zeros(2);dd[axis]=.12;z0=oldwalk.height(goal-dd);z1=oldwalk.height(goal+dd);grad.append((z1-z0)/.24 if z0 is not None and z1 is not None else 0.)
 oldshape=unary_union([walk_tri_polys[i] for i in walk_tree.query(paving) if walk_tri_polys[i].intersects(paving)])
 new_walks.append({'name':walkname,'polygon':paving,'fore':fore,'floor_surface':surface_floor,'goal':goal.tolist(),'goal_z':gz,'route':coords.tolist(),'clear_width_m':3.6,'kind':'cbd_plaza','oldshape':oldshape,'building':name,'source_key':key,'ramp_start':ramp_start,'ramp_end':ramp_end,'goal_gradient':grad,'goal_name':g['name']})
 placed.append(rec);retained.append(poly);print('CBD_SITE_READY',key,center.tolist(),'rotation',math.degrees(theta),'route',L,flush=True)

assert len(placed)==4
# Keep one unobstructed, level plot for the future Tianming Tower.
entry_y=832.5
g=min(goals,key=lambda g:g['line'].distance(Point((-203.,entry_y))))
goal=np.array(g['line'].interpolate(g['line'].project(Point((-203.,entry_y)))).coords[0]);gz=oldwalk.height(goal)
assert gz is not None
site_level=float(gz+.025);entry_start=np.array([-203.,entry_y]);entry_route=LineString([entry_start,goal]);L=entry_route.length
assert L<15 and goal[0]>-203
entry_poly=Polygon([[-203.10,entry_y-4.],list(goal+np.array([0.,-4.])),list(goal+np.array([0.,4.])),[-203.10,entry_y+4.]])
assert entry_poly.intersection(unary_union(retained)).area<1e-5
oldshape=unary_union([walk_tri_polys[i] for i in walk_tree.query(entry_poly) if walk_tri_polys[i].intersects(entry_poly)])
grad=[]
for axis in range(2):
 dd=np.zeros(2);dd[axis]=.12;z0=oldwalk.height(goal-dd);z1=oldwalk.height(goal+dd);grad.append((z1-z0)/.24 if z0 is not None and z1 is not None else 0.)
direction=(goal-entry_start)/L;join=0.
for d in np.arange(.1,min(3.,L),.1):
 if oldwalk.height(goal-direction*d) is None:break
 join=float(d)
new_walks.append({'name':'CBD_Tianming_Reserved_Access','polygon':entry_poly,'fore':box(-203.10,entry_y-4.,-203.,entry_y+4.),'floor_surface':site_level,'goal':goal.tolist(),'goal_z':gz,'route':[entry_start.tolist(),goal.tolist()],'clear_width_m':8.,'kind':'cbd_plaza','oldshape':oldshape,'building':'TIANMING_RESERVED','source_key':'reserved','ramp_start':0.,'ramp_end':max(.2,L-join),'goal_gradient':grad,'goal_name':g['name']})
site_mat=bpy.data.materials.new('Tianming_Reserved_Gravel');site_mat.use_nodes=True;bs=site_mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.38,.34,.27,1);bs.inputs['Roughness'].default_value=.96
site_xy=np.array(reservation.exterior.coords)[:-1];site_obj=mesh('CBD_Tianming_Reserved_Pad',[[*q,site_level] for q in site_xy],[[0,1,2],[0,2,3]],site_mat,footparent);site_obj['surface_type']='reserved_landmark_plot';site_obj['is_building_instance']=False;site_obj['building_count_units']=0;site_obj['future_building_capacity']=1;site_obj['reserved_name']='Tianming Tower';site_obj['clear_area_m2']=reservation.area
site_record={'name':'Tianming Tower','object':'CBD_Tianming_Reserved_Pad','polygon':list(reservation.exterior.coords),'size_m':[172.,195.],'area_m2':reservation.area,'surface_z_m':site_level,'building_present':False,'existing_building_count_units':0,'future_building_capacity':1,'clearance_policy':'Keep this entire polygon and its access free of buildings until Tianming Tower is supplied.','access_object':'CBD_Tianming_Reserved_Access','road_goal':g['name'],'site_access_width_m':8.}
print('TIANMING_RESERVED',json.dumps(site_record),flush=True)
# Remove the 34 superseded CBD placeholders; keep every unrelated identity. Reindex every retained face.
mapping={old:new for new,old in enumerate(i for i in range(len(p['buildings'])) if i not in removed)};removed_names=[p['buildings'][i]['name'] for i in sorted(removed)]
for ob in list(sc.objects):
 if ob.type!='MESH':continue
 attr=ob.data.attributes.get('source_building_index')
 if not attr:continue
 m=ob.data;ids=np.array([v.value for v in attr.data]);keep=~np.isin(ids,list(removed));newids=[mapping[int(v)] for v,k in zip(ids,keep) if k]
 if not keep.any():bpy.data.objects.remove(ob,do_unlink=True);continue
 if keep.all():attr.data.foreach_set('value',np.array(newids,np.int32))
 else:
  data=bpy.data.meshes.new(m.name+'_v13');data.from_pydata([v.co[:] for v in m.vertices],[],[list(q.vertices) for q,k in zip(m.polygons,keep) if k])
  for mat in m.materials:data.materials.append(mat)
  data.polygons.foreach_set('material_index',np.array([q.material_index for q,k in zip(m.polygons,keep) if k],np.int32));data.attributes.new(name='source_building_index',type='INT',domain='FACE').data.foreach_set('value',np.array(newids,np.int32));data.update();ob.data=data
 ob['placeholder_lot_count']=len(set(newids))
p['buildings']=[b for i,b in enumerate(p['buildings']) if i not in removed]
for r in placed:
 t=templates[r['source_key']];inst=bpy.data.objects.new(r['instance_name'],None);sc.collection.objects.link(inst);inst.parent=sourceparent;inst.matrix_world=Matrix.Translation((*r['anchor'],r['floor']-.008))@Matrix.Rotation(r['theta'],4,'Z')@Matrix.Diagonal((r['uniform_scale'],r['uniform_scale'],r['uniform_scale'],1.))@Matrix.Translation(tuple(-t['lo']))
 for j,data in enumerate(t['parts']):
  ob=bpy.data.objects.new(r['instance_name']+f'_Source_Mesh_{j:02d}',data);sc.collection.objects.link(ob);ob.parent=inst;ob.matrix_basis=Matrix.Identity(4);ob['source_filename']=r['file']
 for k,v in {'is_building_instance':True,'source_filename':r['file'],'source_sha256':hashlib.sha256((SRC/r['file']).read_bytes()).hexdigest(),'target_height_m':r['target_height_m'],'direct_alley_frontage':True,'building_count_units':1,'reuse_template_key':r['source_key'],'reuse_linked_mesh':True,'added_in_version':'v13'}.items():inst[k]=v
 prism(Polygon(r['pad_xy']),r['floor']-.018,r['foundation_bottom_m'],r['instance_name']+'_Foundation')
for poly,top,bottom,name in partywalls:prism(poly,top,bottom,name,seammat)
for walk in new_walks:
 route=LineString(walk['route']);goal=np.array(walk['goal']);grad=np.array(walk.get('goal_gradient',[0.,0.]));floor=walk['floor_surface']
 def height(xy):
  xy=np.array(xy);old=oldwalk.height(xy)
  if old is not None:return old+.001
  if walk['kind']=='rear_infill':return floor
  if walk['fore'].covers(Point(xy)):return floor
  s=route.project(Point(xy));t=float(np.clip((s-walk['ramp_start'])/max(.25,walk['ramp_end']-walk['ramp_start']),0,1));plane=walk['goal_z']+.001+float(grad@(xy-goal));return floor*(1-t)+plane*t
 v=[];f=[]
 pieces=[walk['polygon'].difference(walk['oldshape']),walk['polygon'].intersection(walk['oldshape'])]
 if walk['kind']=='cbd_plaza':pieces=[part for q in pieces for part in [q.difference(walk['fore']),q.intersection(walk['fore'])]]
 for piece in pieces:
  if piece.is_empty:continue
  for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(piece,.8))):
   xy=np.array(tri.exterior.coords)[:3];aa=xy[1]-xy[0];bb=xy[2]-xy[0]
   if aa[0]*bb[1]-aa[1]*bb[0]<0:xy=xy[::-1]
   k=len(v);v.extend([[*q,height(q)] for q in xy]);f.append([k,k+1,k+2])
 ob=mesh(walk['name'],v,f,atlas,walkparent,True);ob['surface_type']='v13_access_walk';ob['clear_width_m']=3.6;ob['connects_to']=walk.get('goal_name','existing_rear_access');ob['added_in_version']='v13'
 print('ACCESS_BUILT',walk['name'],len(f),flush=True)
# Clip only new ground occupation; retaining faces cover exposed uphill terrain.
cuts=unary_union([reservation.buffer(.012,join_style=2)]+[Polygon(r['pad_xy']) for r in placed]+[w['polygon'].buffer(.012,join_style=2) for w in new_walks]);cut_count=0
for ob in terrain_obs:
 m=ob.data;m.calc_loop_triangles();co=np.array([v.co[:] for v in m.vertices]);tri=np.array([t.vertices[:] for t in m.loop_triangles]);local=cuts.intersection(box(co[:,0].min(),co[:,1].min(),co[:,0].max(),co[:,1].max()))
 if local.is_empty:continue
 oldcolors=np.array([c.color[:] for c in m.color_attributes[0].data]) if m.color_attributes else None;v=[];f=[];colors=[];changes=0;mat_indices=[]
 for tt,indices in zip(m.loop_triangles,tri):
  xyz=co[indices];q=Polygon(xyz[:,:2]);parts=[xyz]
  if q.intersects(local):
   diff=q.difference(local)
   if q.area-diff.area>1e-8:
    changes+=1;parts=[]
    if not diff.is_empty:
     for t in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
      xy=np.array(t.exterior.coords)[:3];A=np.vstack([xyz[:,:2].T,np.ones(3)]);weights=np.linalg.solve(A,np.vstack([xy.T,np.ones(3)]));parts.append(np.c_[xy,weights.T@xyz[:,2]])
  for part in parts:
   aa=part[1,:2]-part[0,:2];bb=part[2,:2]-part[0,:2]
   if aa[0]*bb[1]-aa[1]*bb[0]<0:part=part[::-1]
   k=len(v);v.extend(part.tolist());f.append([k,k+1,k+2]);mat_indices.append(m.polygons[tt.polygon_index].material_index)
   if oldcolors is not None:
    A=np.vstack([xyz[:,:2].T,np.ones(3)]);B=np.vstack([part[:,:2].T,np.ones(3)]);weights=np.linalg.lstsq(A,B,rcond=None)[0];colors.extend((weights.T@oldcolors[indices]).tolist())
 if not changes:continue
 data=bpy.data.meshes.new(m.name+'_v13_cuts');data.from_pydata(v,[],f)
 for mat in m.materials:data.materials.append(mat)
 data.polygons.foreach_set('material_index',np.array(mat_indices,np.int32))
 if colors:data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(colors,np.float32).ravel())
 data.update();ob.data=data;cut_count+=changes;print('V13_TERRAIN_CUT',ob.name,changes,flush=True)
bpy.context.view_layer.update();new_surfaces=HeightField([bpy.data.objects[r['instance_name']+'_Foundation'] for r in placed]+[bpy.data.objects[w['name']] for w in new_walks]+[site_obj]);walls_v=[];walls_f=[];wall_missing=0
for poly in shapely.get_parts(shapely.orient_polygons(cuts,exterior_cw=False)):
 if poly.geom_type!='Polygon':continue
 for ring in [poly.exterior,*poly.interiors]:
  coords=np.array(shapely.segmentize(ring,1.0).coords)
  for aa,bb in zip(coords[:-1],coords[1:]):
   delta=bb-aa;L=np.linalg.norm(delta)
   if L<1e-8:continue
   n=np.array([delta[1],-delta[0]])/L;mid=(aa+bb)/2;fm=None
   for off in [.03,.07,.15,.3]:
    fm=new_surfaces.height(mid-n*off)
    if fm is not None:break
   if fm is None:wall_missing+=1;continue
   heights=[]
   for q in [aa,bb]:
    z=new_surfaces.height(q-n*.06);z=fm if z is None else z;ground=None
    for off in [.04,.10,.25]:
     ground=soil.height(q+n*off)
     if ground is not None:break
    if ground is None:ground=z
    heights.append((z,ground))
   if max(abs(g-z) for z,g in heights)<.025:continue
   (za,ga),(zb,gb)=heights;k=len(walls_v);walls_v.extend([[*aa,min(za,ga)-.10],[*bb,min(zb,gb)-.10],[*bb,max(zb,gb)+.012],[*aa,max(za,ga)+.012]]);walls_f.extend([[k,k+1,k+2],[k,k+2,k+3]])
ob=mesh('V13_Terrain_Cut_Retaining_Walls',walls_v,walls_f,concrete,footparent);ob['surface_type']='terrain_cut_retaining_wall';ob['added_in_version']='v13'

p['real_buildings'].extend(placed);p['schema']='hero13.city.compact-cbd.v13'
p['cbd_access_v13']=[{k:(list(v.exterior.coords) if k in ['polygon','fore'] else v) for k,v in w.items() if k!='oldshape'} for w in new_walks]
p['cbd_plan']={'boundary':list(cbd_boundary.exterior.coords),'boundary_area_m2':cbd_boundary.area,'existing_buildings':29,'planned_total_including_tianming':30,'source_buildings':14,'placeholder_buildings':15,'tianming':site_record,'removed_placeholder_names':removed_names}
total=len(p['buildings'])+len(p['real_buildings']);assert total==652 and len(p['buildings'])==547 and len(p['real_buildings'])==105
p['stats'].update(buildings=total,placeholder_lots=547,real_buildings=105,source_asset_types=34,cbd_buildings=29,cbd_reserved_landmark_capacity=1,cbd_planned_total_including_landmark=30,cbd_boundary_area_m2=cbd_boundary.area,tianming_reserved_area_m2=reservation.area)
p['stats']['building_count_by_zone']['CBD']=29
p['stats']['building_coverage_percent']=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]).area/p['stats']['land_area_m2']*100
root['version']='v13_compact_cbd_tianming_reserve';root['building_count']=total
for im in bpy.data.images:
 if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
build=json.loads((BASE/'validation/compact_build_report.json').read_text());build.update(schema='hero13.city.build.v13',stats=p['stats'],building_count=total,original_source_buildings=105,source_asset_types=34,cbd_existing_buildings=29,cbd_planned_buildings=30,cbd_removed_placeholders=34,cbd_new_source_instances=4,tianming_reservation=site_record,v13_terrain_triangles_cut=cut_count,v13_retaining_wall_triangles=len(walls_f),v13_unsampled_wall_segments=wall_missing)
report={'status':'BUILT','city_buildings':total,'land_area_m2':p['stats']['land_area_m2'],'cbd_before':59,'cbd_after':29,'cbd_after_tianming':30,'removed_cbd_placeholders':34,'cbd_source_instances':14,'cbd_placeholders':15,'new_offices_each_used_once':4,'tianming':site_record,'retained_source_instances':101,'rear_instances_unchanged':80,'retained_roads':True,'unsampled_terrain_wall_segments':wall_missing}
(OUT/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(OUT/'compact_build_report.json').write_text(json.dumps(build,indent=2));(OUT/'v13_build_report.json').write_text(json.dumps(report,indent=2));(OUT/'new_building_descriptors.json').write_text(json.dumps(placed,indent=2));(OUT/'tianming_reservation.json').write_text(json.dumps(site_record,indent=2));shutil.copy2(BASE/'rear_asset_pool.json',OUT/'rear_asset_pool.json')
with (OUT/'building_registry.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','kind','zone','typology','source_file','source_key','x','y','height_m','row','count_units']);w.writeheader()
 for b in p['buildings']:w.writerow({'id':b['name'],'kind':'placeholder','zone':b['zone'],'typology':b['typology'],'x':b['center'][0],'y':b['center'][1],'height_m':b['height'],'count_units':1})
 for r in p['real_buildings']:w.writerow({'id':r['instance_name'],'kind':'source','zone':r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN'),'typology':r.get('typology','retained_source'),'source_file':r['file'],'source_key':r.get('source_key',''),'x':r['center'][0],'y':r['center'][1],'height_m':r['target_height_m'],'row':r.get('row_name',''),'count_units':1})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain original textures.')
print('V13_BUILD_COMPLETE',json.dumps(report),flush=True)
