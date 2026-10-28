"""Add two linked rear-house templates, 18 infill houses and eight unique CBD assets.

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
p=json.loads((BASE/'city_plan.json').read_text());old_count=len(p['buildings'])+len(p['real_buildings']);assert old_count==665
uploads=[
 ('27','rusty apartment building 27.glb','rusty_apartment_27.glb',15.7,'rear'),
 ('28','concrete apartment building 28.glb','concrete_apartment_28.glb',12.8,'rear'),
 ('21','modern glass office building 21.glb','modern_glass_office_21.glb',86.,'cbd'),
 ('22','glass office building 22.glb','glass_office_22.glb',90.,'cbd'),
 ('23','glass skyscraper 23.glb','glass_skyscraper_23.glb',96.,'cbd'),
 ('24','modern glass building 24.glb','modern_glass_24.glb',88.,'cbd'),
 ('25','high-rise building 25.glb','high_rise_25.glb',104.,'cbd'),
 ('26A','office building 3d model26.glb','office_building_26.glb',92.,'cbd'),
 ('26B','skyscraper 3d model26.glb','skyscraper_26.glb',86.,'cbd'),
 ('26C','modern office building 26.glb','modern_office_complex_26.glb',38.,'cbd')]
for key,original,name,height,kind in uploads:shutil.copy2(a.uploads/original,SRC/name)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'));sc=bpy.context.scene;bpy.context.view_layer.update()
root=bpy.data.objects['Huizhou_Reconstructed_City_3p25km2'];sourceparent=bpy.data.objects['07_SOURCE_BUILDINGS'];footparent=bpy.data.objects['08_BUILDING_FOOTINGS'];walkparent=bpy.data.objects['10_PEDESTRIAN_NETWORK']
terrain_obs=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'];soil=HeightField(terrain_obs)
walk_names={r['name'] for r in p['pedestrian_alleys']}
oldwalk_obs=[o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['sidewalk','backlane_entry_walk','backlane_seam_stitch'] or o.name in walk_names)]
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
 rec={'instance_name':name,'file':t['file'],'source_filename':t['file'],'original_upload_name':t['original'],'source_key':key,'uniform_scale':t['scale'],'local_axis_scale':[1.,1.,1.],'target_height_m':t['height'],'source_bounds':[t['lo'].tolist(),t['hi'].tolist()],'source_floor_reference':float(t['lo'][2]),'turn':0.,'left':0.,'right':w,'front':0.,'anchor':face.tolist(),'theta':theta,'angle':math.degrees(theta),'center':list(poly.centroid.coords[0]),'region':'MAIN','zone':zone,'footprint_xy':xy.tolist(),'pad_xy':list(poly.buffer(.08,join_style=2).exterior.coords),'floor':float(floor),'direct_sidewalk_frontage':False,'direct_alley_frontage':True,'building_count_units':1,'typology':'backlane_source_house' if zone=='OLDTOWN' else 'office_source_building','reuse_rotation_only_no_mirror':True,'added_in_version':'v12',**extra}
 return rec
def legal_house(poly,blocked,other_walks=None):
 if not land.covers(poly.buffer(.10)):return False
 if poly.intersection(blocked).area>1e-5 or poly.intersection(road_full).area>1e-5:return False
 if other_walks is not None and poly.intersection(other_walks).area>.005:return False
 return True
# Add both new types to the historic rear row, then distribute 16 infill buildings.
rows=[json.loads(json.dumps(r)) for r in p['rear_rows']];use=collections.Counter();blockuse=collections.Counter();used_sides=set()
def infill(row,side,key,seq):
 t=templates[key];face0=np.array(row['face']);u=np.array(row['u']);n=np.array(row['n']);width=float(row['width']);w=t['width'];d=t['depth'];theta=math.atan2(u[1],u[0])
 face=face0+u*(width+.12) if side=='right' else face0-u*(w+.12)
 poly=Polygon([face,face+u*w,face+u*w-n*d,face-n*d]);blocked=unary_union(all_buildings)
 if not legal_house(poly,blocked,oldped):return None
 goal=face0+u*(width-.45) + n*2.0 if side=='right' else face0+u*.45+n*2.0
 if row['core']:goal[1]=260.0
 gz=oldwalk.height(goal)
 if gz is None:return None
 start=face+u*w/2+n*2.0
 fore_left=face-u*.05 if side=='left' else face-u*.70
 fore_right=face+u*(w+.70) if side=='left' else face+u*(w+.05)
 fore=Polygon([fore_left,fore_right,fore_right+n*3.9,fore_left+n*3.9])
 if fore.intersection(blocked).area>.004 or fore.intersection(carriage).area>.004:return None
 if not land.covers(fore):return None
 corners=[soil.height(v) for v in poly.exterior.coords];corners=[v for v in corners if v is not None]
 floor=float(row['floor']);
 if row['core']:
  z=oldwalk.height(face+u*w/2+n*.1)
  if z is not None:floor=z+.028
 if corners and max(abs(c-floor) for c in corners)>2.5:return None
 name=f'OLDTOWN_Infill_{seq:02d}_Asset{key}';walkname=name+'_Entrance_Walk'
 rec=descriptor(key,name,face,theta,floor,'OLDTOWN',row_name=row['name'],access_alley=walkname,infill_side=side,continuous_rear_row=True,existing_row=row['name'])
 rec['foundation_bottom_m']=min([floor-.45,*corners])-.12
 # Existing overlap is sampled on its own height planes; the remaining terrace is flat.
 oldshape=unary_union([walk_tri_polys[i] for i in walk_tree.query(fore) if walk_tri_polys[i].intersects(fore)])
 walk={'name':walkname,'polygon':fore,'floor_surface':floor-.028,'goal':goal.tolist(),'goal_z':gz,'route':[start.tolist(),goal.tolist()],'clear_width_m':3.6,'kind':'rear_infill','oldshape':oldshape,'building':name,'source_key':key}
 placed.append(rec);new_walks.append(walk);all_buildings.append(poly);use[key]+=1;blockuse[row['block_id']]+=1
 if side=='right':
  seam=Polygon([face-u*.12,face,face-n*min(d,9.),face-u*.12-n*min(d,9.)])
 else:
  aa=face+u*w;seam=Polygon([aa,aa+u*.12,aa+u*.12-n*min(d,9.),aa-n*min(d,9.)])
 partywalls.append((seam,floor+min(t['height'],10.)-.25,floor-.02,'Infill_Partywall_'+name))
 return rec
core=rows[0]
for key in ['28','27']:
 rec=infill(core,'right',key,len(placed)+1)
 if rec is None:raise RuntimeError(('original rear row infill does not fit',key))
 core['width']+=templates[key]['width']+.12
 # The second addition connects through the first terrace.
 oldped=unary_union([oldped,new_walks[-1]['polygon']])
 oldwalk_obs_new=[]
 # For layout only, reuse the original alley beneath this continuous row.
print('CORE_INFILL_PLACED',flush=True)
pending=[r for r in rows[1:]]
while len(placed)<18:
 options=sorted(pending,key=lambda r:(blockuse[r['block_id']],sum(1 for v in p['rear_rows'] if v['block_id']==r['block_id']),r['name']))
 success=False
 for row in options:
  keys=sorted(['27','28'],key=lambda k:(use[k],k))
  for key in keys:
   if use[key]>=9:continue
   for side in ['right','left']:
    if (row['name'],side) in used_sides:continue
    if infill(row,side,key,len(placed)+1):
     used_sides.add((row['name'],side));pending.remove(row);success=True;break
   if success:break
  if success:break
 if not success:raise RuntimeError(('not enough clear infill frontage',len(placed),dict(use)))
assert use=={'27':9,'28':9};print('INFILL_LAYOUT',dict(use),dict(blockuse),flush=True)
# Replace eight CBD site groups: seven individual lots plus two merged campus lots.
cbd_sites={'21':[365],'22':[350],'23':[344],'24':[357],'25':[399],'26A':[376],'26B':[377],'26C':[346,362]}
removed=set(i for ids in cbd_sites.values() for i in ids);assert len(removed)==9
retained=[Polygon(b['footprint']) for i,b in enumerate(p['buildings']) if i not in removed]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]+[Polygon(r['footprint_xy']) for r in placed]
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
for key,ids in cbd_sites.items():
 t=templates[key];center=np.mean([p['buildings'][i]['center'] for i in ids],axis=0)
 if key=='26C':center[1]=688.5
 if key=='26B':center[0]+=10.0
 if key=='23':center[1]+=4.0
 blocked=unary_union(retained);options=[]
 for theta in [0.,math.pi/2,math.pi,-math.pi/2]:
  u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);face=center+n*t['depth']/2-u*t['width']/2;poly=Polygon([face,face+u*t['width'],face+u*t['width']-n*t['depth'],face-n*t['depth']])
  if not legal_house(poly,blocked):continue
  fore=Polygon([face-u*.02,face+u*(t['width']+.02),face+u*(t['width']+.02)+n*3.9,face-u*.02+n*3.9])
  if fore.intersection(blocked).area>.001 or fore.intersection(carriage).area>.001:continue
  routes=find_route(face+u*t['width']/2+n*2.0,unary_union([blocked,poly]))
  for L,g,coords,z in routes[:1]:
   options.append((L,theta,face,poly,fore,g,coords,z))
 if not options:raise RuntimeError(('CBD site has no fitting footprint and access',key,ids))
 L,theta,face,poly,fore,g,coords,gz=min(options,key=lambda v:v[0]);u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);route=LineString(coords);goal=coords[-1]
 direction=coords[-1]-coords[-2];direction/=np.linalg.norm(direction);join=0.
 for d in np.arange(.1,min(5.,L),.1):
  if oldwalk.height(goal-direction*d) is None:break
  join=float(d)
 ramp_start=max([route.project(Point(q)) for part in shapely.get_parts(route.intersection(fore)) if part.geom_type=='LineString' for q in part.coords] or [0.]);ramp_end=max(ramp_start+.25,L-join)
 terrain_center=soil.height(center);allow=.024*max(.25,ramp_end-ramp_start);surface_floor=gz+.001+float(np.clip((terrain_center if terrain_center is not None else gz)-gz,-allow,allow));floor=surface_floor+.028
 name='CBD_Imported_'+key;walkname=name+'_Entrance_Plaza';rec=descriptor(key,name,face,theta,floor,'CBD',access_alley=walkname,replaces_placeholder_sites=[p['buildings'][i]['name'] for i in ids],unique_cbd_use=True)
 zz=[soil.height(q) for q in shapely.segmentize(poly.buffer(.1,join_style=2),2).exterior.coords];zz=[v for v in zz if v is not None];rec['foundation_bottom_m']=min([floor-.45,*zz])-.12
 paving=unary_union([fore,route.buffer(1.8,cap_style=2,join_style=2)])
 assert paving.intersection(blocked).area<.004 and paving.intersection(carriage).area<.004
 grad=[]
 for axis in range(2):
  dd=np.zeros(2);dd[axis]=.12;z0=oldwalk.height(goal-dd);z1=oldwalk.height(goal+dd);grad.append((z1-z0)/.24 if z0 is not None and z1 is not None else 0.)
 oldshape=unary_union([walk_tri_polys[i] for i in walk_tree.query(paving) if walk_tri_polys[i].intersects(paving)])
 new_walks.append({'name':walkname,'polygon':paving,'fore':fore,'floor_surface':surface_floor,'goal':goal.tolist(),'goal_z':gz,'route':coords.tolist(),'clear_width_m':3.6,'kind':'cbd_plaza','oldshape':oldshape,'building':name,'source_key':key,'ramp_start':ramp_start,'ramp_end':ramp_end,'goal_gradient':grad,'goal_name':g['name']})
 placed.append(rec);retained.append(poly);print('CBD_SITE_READY',key,ids,'rotation',math.degrees(theta),'route',L,flush=True)
assert len(placed)==26
# Remove only the nine superseded massing identities. Reindex every retained face.
mapping={old:new for new,old in enumerate(i for i in range(len(p['buildings'])) if i not in removed)};removed_names=[p['buildings'][i]['name'] for i in sorted(removed)]
for ob in list(sc.objects):
 if ob.type!='MESH':continue
 attr=ob.data.attributes.get('source_building_index')
 if not attr:continue
 m=ob.data;ids=np.array([v.value for v in attr.data]);keep=~np.isin(ids,list(removed));newids=[mapping[int(v)] for v,k in zip(ids,keep) if k]
 if not keep.any():bpy.data.objects.remove(ob,do_unlink=True);continue
 if keep.all():attr.data.foreach_set('value',np.array(newids,np.int32))
 else:
  data=bpy.data.meshes.new(m.name+'_v12');data.from_pydata([v.co[:] for v in m.vertices],[],[list(q.vertices) for q,k in zip(m.polygons,keep) if k])
  for mat in m.materials:data.materials.append(mat)
  data.polygons.foreach_set('material_index',np.array([q.material_index for q,k in zip(m.polygons,keep) if k],np.int32));data.attributes.new(name='source_building_index',type='INT',domain='FACE').data.foreach_set('value',np.array(newids,np.int32));data.update();ob.data=data
 ob['placeholder_lot_count']=len(set(newids))
p['buildings']=[b for i,b in enumerate(p['buildings']) if i not in removed]
for r in placed:
 t=templates[r['source_key']];inst=bpy.data.objects.new(r['instance_name'],None);sc.collection.objects.link(inst);inst.parent=sourceparent;inst.matrix_world=Matrix.Translation((*r['anchor'],r['floor']-.008))@Matrix.Rotation(r['theta'],4,'Z')@Matrix.Diagonal((r['uniform_scale'],r['uniform_scale'],r['uniform_scale'],1.))@Matrix.Translation(tuple(-t['lo']))
 for j,data in enumerate(t['parts']):
  ob=bpy.data.objects.new(r['instance_name']+f'_Source_Mesh_{j:02d}',data);sc.collection.objects.link(ob);ob.parent=inst;ob.matrix_basis=Matrix.Identity(4);ob['source_filename']=r['file']
 for k,v in {'is_building_instance':True,'source_filename':r['file'],'source_sha256':hashlib.sha256((SRC/r['file']).read_bytes()).hexdigest(),'target_height_m':r['target_height_m'],'direct_alley_frontage':True,'building_count_units':1,'reuse_template_key':r['source_key'],'reuse_linked_mesh':True,'added_in_version':'v12'}.items():inst[k]=v
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
 ob=mesh(walk['name'],v,f,atlas,walkparent,True);ob['surface_type']='v12_access_walk';ob['clear_width_m']=3.6;ob['connects_to']=walk.get('goal_name','existing_rear_access');ob['added_in_version']='v12'
 print('ACCESS_BUILT',walk['name'],len(f),flush=True)
# Clip only new ground occupation; retaining faces cover exposed uphill terrain.
cuts=unary_union([Polygon(r['pad_xy']) for r in placed]+[w['polygon'].buffer(.012,join_style=2) for w in new_walks]);cut_count=0
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
 data=bpy.data.meshes.new(m.name+'_v12_cuts');data.from_pydata(v,[],f)
 for mat in m.materials:data.materials.append(mat)
 data.polygons.foreach_set('material_index',np.array(mat_indices,np.int32))
 if colors:data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(colors,np.float32).ravel())
 data.update();ob.data=data;cut_count+=changes;print('V12_TERRAIN_CUT',ob.name,changes,flush=True)
bpy.context.view_layer.update();new_surfaces=HeightField([bpy.data.objects[r['instance_name']+'_Foundation'] for r in placed]+[bpy.data.objects[w['name']] for w in new_walks]);walls_v=[];walls_f=[];wall_missing=0
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
ob=mesh('V12_Terrain_Cut_Retaining_Walls',walls_v,walls_f,concrete,footparent);ob['surface_type']='terrain_cut_retaining_wall';ob['added_in_version']='v12'
p['real_buildings'].extend(placed);p['schema']='hero13.city.infill-cbd.v12';p['infill_access_v12']=[{k:(list(v.exterior.coords) if k in ['polygon','fore'] else v) for k,v in w.items() if k!='oldshape'} for w in new_walks]
total=len(p['buildings'])+len(p['real_buildings']);assert total==682<700
p['stats'].update(buildings=total,placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),backlane_asset_instances=80,rear_asset_types=9,source_asset_types=30,infill_rear_instances_added=18,unique_cbd_assets_added=8,added_v12_access_links=len(new_walks),building_coverage_percent=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]).area/p['stats']['land_area_m2']*100)
p['stats']['building_count_by_zone']['OLDTOWN']+=18;p['stats']['building_count_by_zone']['CBD']-=1
p['stats'].pop('oldtown_coverage_percent',None)
p['stats']['oldtown_building_footprint_m2']=unary_union([Polygon(b['footprint']) for b in p['buildings'] if b['zone']=='OLDTOWN']+[Polygon(r['footprint_xy']) for r in p['real_buildings'] if r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN')=='OLDTOWN']).area
root['version']='v12_rear_infill_and_eight_unique_cbd';root['building_count']=total
for im in bpy.data.images:
 if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
build=json.loads((BASE/'validation/compact_build_report.json').read_text());build.update(schema='hero13.city.build.v12',stats=p['stats'],building_count=total,original_source_buildings=len(p['real_buildings']),rear_instances_total=80,rear_asset_types=9,source_asset_types=30,unique_cbd_assets_added=8,v12_terrain_triangles_cut=cut_count,v12_retaining_wall_triangles=len(walls_f),v12_unsampled_wall_segments=wall_missing)
pool_files={13:'old_apartment_13.glb',14:'apartment_14.glb',15:'historic_building_facade_15.glb',17:'old_building_17.glb',18:'apartment_building_18.glb',19:'old_italian_townhouse_19.glb',20:'urban_building_facade_20.glb','27':'rusty_apartment_27.glb','28':'concrete_apartment_28.glb'}
pool={'schema':'hero13.rear-asset-pool.v12','types':[{'key':str(k),'file':fn,'instances':sum(r['file']==fn for r in p['real_buildings']),'sha256':hashlib.sha256((SRC/fn).read_bytes()).hexdigest()} for k,fn in pool_files.items()],'instances':80,'linked_mesh_reuse':True,'new_type_reuse_counts':dict(use),'original_62_rear_instances_preserved':True}
(OUT/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(OUT/'compact_build_report.json').write_text(json.dumps(build,indent=2));(OUT/'new_building_descriptors.json').write_text(json.dumps(placed,indent=2));(OUT/'rear_asset_pool.json').write_text(json.dumps(pool,indent=2))
report={'status':'BUILT','city_buildings':total,'original_city_buildings':old_count,'rear_instances_before':62,'rear_instances_after':80,'rear_infill_added':18,'infill_new_source_reuse_counts':dict(use),'infill_count_by_block':dict(blockuse),'unique_new_cbd_models':8,'cbd_instances_each_model':1,'cbd_placeholders_replaced':9,'cbd_replaced_placeholder_names':removed_names,'retained_source_instances':75,'retained_road_geometry':True,'terrain_triangles_cut':cut_count,'retaining_wall_triangles':len(walls_f),'unsampled_wall_segments':wall_missing,'land_area_m2':p['stats']['land_area_m2']}
(OUT/'v12_build_report.json').write_text(json.dumps(report,indent=2))
with (OUT/'building_registry.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','kind','zone','typology','source_file','source_key','x','y','height_m','row','count_units']);w.writeheader()
 for b in p['buildings']:w.writerow({'id':b['name'],'kind':'placeholder','zone':b['zone'],'typology':b['typology'],'x':b['center'][0],'y':b['center'][1],'height_m':b['height'],'count_units':1})
 for r in p['real_buildings']:w.writerow({'id':r['instance_name'],'kind':'source','zone':r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN'),'typology':r.get('typology','retained_source'),'source_file':r['file'],'source_key':r.get('source_key',''),'x':r['center'][0],'y':r['center'][1],'height_m':r['target_height_m'],'row':r.get('row_name',''),'count_units':1})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain original textures.')
print('V12_BUILD_COMPLETE',json.dumps(report),flush=True)
