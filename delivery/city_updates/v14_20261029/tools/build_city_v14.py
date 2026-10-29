"""City v14: all 19 uploads, civic campus, northern apartments, coastal avenue,
and a nine-lot villa enclave. Native baseline is v13; world units are metres.
"""
import bpy,sys,json,math,hashlib,collections,shutil,csv,argparse,copy
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
ap=argparse.ArgumentParser()
for k in ['baseline','inputs','out','deps']:ap.add_argument('--'+k,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(a.deps.resolve()));sys.path.insert(0,str(a.baseline.resolve()/'tools'))
import shapely
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
from city_surface_sampling import HeightField
BASE=a.baseline.resolve();OUT=a.out.resolve();OUT.mkdir(parents=True,exist_ok=True);SRC=OUT/'source/buildings';SRC.mkdir(parents=True,exist_ok=True)
p=json.loads((BASE/'city_plan.json').read_text());baseline=copy.deepcopy(p)
assert len(p['buildings'])+len(p['real_buildings'])==652
bpy.ops.wm.open_mainfile(filepath=str(BASE/'huizhou_road_network.blend'));sc=bpy.context.scene;bpy.context.view_layer.update()
root=bpy.data.objects['Huizhou_Reconstructed_City_3p25km2'];sourceparent=bpy.data.objects['07_SOURCE_BUILDINGS'];footparent=bpy.data.objects['08_BUILDING_FOOTINGS'];walkparent=bpy.data.objects['10_PEDESTRIAN_NETWORK']
zoneparent=bpy.data.objects.new('11_URBAN_AREAS_V14',None);sc.collection.objects.link(zoneparent);zoneparent.parent=root
terrain_obs=[o for o in sc.objects if o.type=='MESH' and o.get('surface_type')=='terrain'];soil=HeightField(terrain_obs)
walk_names={r['name'] for r in p['pedestrian_alleys']}
walk_obs=[o for o in sc.objects if o.type=='MESH' and (o.get('surface_type') in ['sidewalk','pedestrian','source_access','backlane_entry_walk','backlane_seam_stitch','v12_access_walk','v13_access_walk'] or o.name in walk_names)]
oldwalk=HeightField(walk_obs)
concrete=bpy.data.materials['Bridge_Concrete'];atlas=bpy.data.materials['Road_Modular_Original_Atlas']
def material(name,color,rough=.8):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;return m
villa_mat=material('V14_Villa_Warm_Plaster',(.63,.58,.47));villa_roof=material('V14_Villa_Dark_Roof',(.17,.20,.21));apt_mat=material('V14_Apartment_Placeholder',(.55,.62,.67));garden_mat=material('V14_Garden_Lawn',(.16,.24,.12));tree_mat=material('V14_Coastal_Tree',(.08,.18,.10));trunk_mat=material('V14_Tree_Trunk',(.15,.105,.07));rail_mat=material('V14_Coastal_Railing',(.18,.22,.24),.45)
def mesh(name,v,f,mat,parent=footparent,uv=False):
 m=bpy.data.meshes.new(name);m.from_pydata(v,[],f);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=parent;o['added_in_version']='v14'
 if uv:
  layer=m.uv_layers.new(name='UVMap')
  for li,loop in enumerate(m.loops):
   q=m.vertices[loop.vertex_index].co;layer.data[li].uv=(.216+.055*((q.x/3)%1),.5989+.1777*((q.y/16.9048)%1))
 return o
def prism(poly,top,bottom,name,mat=concrete,parent=footparent):
 xy=np.array(shapely.orient_polygons(poly,exterior_cw=False).exterior.coords)[:-1];n=len(xy);v=np.r_[np.c_[xy,np.full(n,bottom)],np.c_[xy,np.full(n,top)]];f=[]
 for i in range(1,n-1):f.extend([[0,i+1,i],[n,n+i,n+i+1]])
 for i in range(n):j=(i+1)%n;f.extend([[i,j,j+n],[i,j+n,i+n]])
 return mesh(name,v.tolist(),f,mat,parent)
def hash_mesh(o):
 m=o.data;h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in m.vertices],dtype='<f4').tobytes())
 for f in m.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in m.uv_layers:h.update(np.array([x.uv[:] for x in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()
original_fingerprints={o.name:hash_mesh(o) for o in sc.objects if o.type=='MESH'}
original_source_metadata={r['instance_name']:copy.deepcopy(r) for r in p['real_buildings']}
uploads=[
 ('U31','urban skyscraper 3d model 31.glb','urban_skyscraper_31.glb',80.,'CBD'),
 ('A32','high-rise building 32.glb','apartment_highrise_32.glb',72.,'APARTMENT'),
 ('G33','government building 33.glb','government_33.glb',26.,'GOVERNMENT'),
 ('O34','tall office building 34.glb','tall_office_34.glb',82.,'CBD'),
 ('A35','high-rise building 35.glb','apartment_highrise_35.glb',78.,'APARTMENT'),
 ('A36','high-rise building 36.glb','apartment_highrise_36.glb',75.,'APARTMENT'),
 ('O37','modern office building 37.glb','modern_office_37.glb',36.,'CBD'),
 ('M38','modern building 38.glb','modern_building_38.glb',29.,'CBD'),
 ('O39','modern office building 39.glb','modern_office_39.glb',26.,'CBD'),
 ('O40','modern office building 40.glb','modern_office_40.glb',54.,'CBD'),
 ('G41','glass building 41.glb','glass_building_41.glb',24.,'CBD'),
 ('G42','glass building 42.glb','glass_building_42.glb',24.,'CBD'),
 ('O42','modern office building 42.glb','modern_office_42.glb',54.,'CBD'),
 ('O43','modern office building 43.glb','modern_office_43.glb',54.,'CBD'),
 ('G44','modern glass building 44.glb','modern_glass_44.glb',38.,'CBD'),
 ('G45','glass office building 45.glb','glass_office_45.glb',60.,'CBD'),
 ('O46','office building 46.glb','office_building_46.glb',28.,'CBD'),
 ('O47','modern office building 47.glb','modern_office_47.glb',28.,'CBD'),
 ('G48','glass office building 48.glb','glass_office_48.glb',62.,'CBD')]
templates={}
for key,original,file,height,zone in uploads:
 shutil.copy2(a.inputs/original,SRC/file);before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(SRC/file));bpy.context.view_layer.update();imported=set(sc.objects)-before;parts=[]
 for ob in imported:
  if ob.type=='MESH':data=ob.data.copy();data.transform(ob.matrix_world);parts.append(data)
 co=np.concatenate([np.array([v.co[:] for v in m.vertices]) for m in parts]);lo=co.min(0);hi=co.max(0);s=height/(hi[2]-lo[2])
 templates[key]={'parts':parts,'lo':lo,'hi':hi,'height':height,'scale':s,'width':(hi[0]-lo[0])*s,'depth':(hi[1]-lo[1])*s,'file':file,'original':original,'zone':zone}
 for ob in imported:bpy.data.objects.remove(ob,do_unlink=True)
 print('TEMPLATE',key,round(templates[key]['width'],2),round(templates[key]['depth'],2),height,flush=True)
land=unary_union([Polygon(c) for c in p['coasts'].values()]).difference(Polygon(p['lake']))
carriage=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['carriage_width']/2+.10) for e in p['edges']])
road_full=unary_union([LineString(np.array(e['points'])[:,:2]).buffer(e['width']/2+.08) for e in p['edges']])
protected_walks=unary_union([LineString(r['points']).buffer(r['width']/2+.01,cap_style=2) for r in p['pedestrian_alleys']]+[Polygon(r['polygon']) for r in p['rear_rows']]+[Polygon(r['polygon']) for k in ['infill_access_v12','cbd_access_v13'] for r in p[k]])
reservation=Polygon(p['cbd_plan']['tianming']['polygon']);cbd_boundary=Polygon(p['cbd_plan']['boundary'])
cbd_slots={b['name']:copy.deepcopy(b) for b in p['buildings'] if b['zone']=='CBD'};assert len(cbd_slots)==15
government_slot='MAIN_CIVIC_0003';removed_names=set(cbd_slots)|{government_slot}
villa_names={f'WEST_VILLAGE_{i:04d}' for i in range(39,48)};assert len(villa_names)==9
new_ph=[]
for b in p['buildings']:
 if b['name'] in villa_names:
  b['zone']='VILLA';b['typology']='villa_placeholder';b['height']=8.4;b['size']=[16.,22.,8.4];x,y=b['center'];b['footprint']=[[x-8,y-11],[x+8,y-11],[x+8,y+11],[x-8,y+11]];b['added_or_modified_in']='v14';new_ph.append(b)
 if b['zone']=='CIVIC' and b['center'][0]<820 and b['name']!=government_slot:b['zone']='GOVERNMENT';b['typology']='civic_support_placeholder';b['planning_area']='EAST_MUNICIPAL_CAMPUS'
p['buildings']=[b for b in p['buildings'] if b['name'] not in removed_names]
retained=[Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]
apartment_records=[]
def footprint(center,w,d,theta):
 c=np.array(center,float);u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);face=c+n*d/2-u*w/2
 return face,Polygon([face,face+u*w,face+u*w-n*d,face-n*d])
apt_candidates={
 'A32':[(-330,1105),(-345,1107),(-310,1106),(-275,1105)],
 'A35':[(-290,1182),(-300,1180),(-285,1185),(-320,1182)],
 'A36':[(170,1168),(210,1165),(150,1170),(180,1172),(230,1162)]}
for key in ['A32','A35','A36']:
 t=templates[key];chosen=None
 for center in apt_candidates[key]:
  for deg in ({'A32':[180,90,0,270],'A35':[180,0,90,270],'A36':[0,-12,90,180]}[key]):
   face,poly=footprint(center,t['width'],t['depth'],math.radians(deg));blocked=unary_union(retained+[reservation,cbd_boundary])
   if land.covers(poly.buffer(2.)) and not poly.buffer(2.).intersects(blocked) and not poly.buffer(.2).intersects(road_full):chosen=(center,deg,poly);break
  if chosen:break
 if not chosen:raise RuntimeError(('No apartment tower site',key))
 center,deg,poly=chosen;apartment_records.append({'key':key,'center':center,'preferred':deg,'poly':poly});retained.append(poly)
 print('APARTMENT_SITE',key,center,deg,flush=True)
apt_ph_candidates=[(-395,1175),(-365,1103),(-250,1103),(-440,1182),(-370,1187),(-210,1187),(-135,1184),(-60,1181),(10,1180),(85,1176),(155,1171),(345,1162),(420,1100),(-250,1105),(-105,1105),(300,1090)]
for center in apt_ph_candidates:
 if len([b for b in new_ph if b['zone']=='APARTMENT'])==9:break
 for deg in [0,180,90]:
  _,poly=footprint(center,22.,28.,math.radians(deg));blocked=unary_union(retained+[reservation,cbd_boundary])
  if land.covers(poly.buffer(1.)) and not poly.buffer(3.).intersects(blocked) and not poly.buffer(.2).intersects(road_full):break
 else:continue
 i=len([b for b in new_ph if b['zone']=='APARTMENT'])+1;height=[21.,24.,18.,27.,21.,24.,18.,24.,21.][i-1]
 b={'name':f'MAIN_NORTH_APARTMENT_{i:02d}','region':'MAIN','zone':'APARTMENT','center':list(center),'footprint':list(poly.exterior.coords)[:-1],'base':0.,'height':height,'size':[22.,28.,height],'block_id':1400+i,'typology':'midrise_apartment_placeholder','building_count_units':1,'rotation_degrees':deg,'added_or_modified_in':'v14','count_basis':'one independent apartment footprint'}
 p['buildings'].append(b);new_ph.append(b);retained.append(poly);print('APARTMENT_MIDRISE',b['name'],center,flush=True)
assert len([b for b in new_ph if b['zone']=='APARTMENT'])==9
goals=[]
for e in p['edges']:
 if e['region'] not in ['MAIN','WEST']:continue
 line=LineString(np.array(e['points'])[:,:2])
 for side in ['left','right']:
  goal=line.parallel_offset(e['carriage_width']/2+e['sidewalk_width']*.55,side,join_style=2)
  for part in shapely.get_parts(goal):
   if part.geom_type=='LineString':goals.append({'name':e['name']+'_'+side,'line':part,'region':e['region']})
def find_routes(start,blocked,region):
 options=[];start=np.array(start)
 for g in sorted((g for g in goals if g['region']==region),key=lambda g:g['line'].distance(Point(start)))[:14]:
  s=g['line'].project(Point(start))
  for off in [0.,-8.,8.,-20.,20.,-36.,36.]:
   end=np.array(g['line'].interpolate(np.clip(s+off,0,g['line'].length)).coords[0]);z=oldwalk.height(end);ground=soil.height(end)
   if z is None or (ground is not None and abs(z-ground)>2.5):continue
   variants=[[start,end],[start,np.array([start[0],end[1]]),end],[start,np.array([end[0],start[1]]),end]]
   for coords in variants:
    coords=np.array([q for i,q in enumerate(coords) if i==0 or np.linalg.norm(q-coords[i-1])>.01])
    if len(coords)<2:continue
    route=LineString(coords);nav=route.buffer(1.8,cap_style=2,join_style=2)
    if route.length>220 or nav.intersection(blocked).area>.002 or nav.intersection(carriage).area>.002 or not land.covers(nav):continue
    options.append((route.length,g,coords,z))
 return sorted(options,key=lambda v:v[0])
placed=[];new_walks=[];all_new_occupations=[]
def plan_access(name,poly,face,theta,w,region,blocked,kind='source'):
 u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]])
 # A level entrance apron must end before the existing sloping sidewalk.
 # Only its central access ramp meets the street, avoiding a long steep seam.
 clearance=poly.distance(road_full)
 if clearance<.85:return None
 fore_depth=min(4.2,clearance-.15)
 fore=Polygon([face-u*.01,face+u*(w+.01),face+u*(w+.01)+n*fore_depth,face-u*.01+n*fore_depth])
 if fore.intersection(blocked).area>.001 or fore.intersection(carriage).area>.001 or not land.covers(fore):return None
 routes=find_routes(face+u*w/2+n*min(2.,fore_depth*.5),unary_union([blocked,poly]),region)
 if not routes:return None
 L,g,coords,gz=routes[0];route=LineString(coords);goal=coords[-1];direction=coords[-1]-coords[-2];direction/=np.linalg.norm(direction);join=0.
 for d in np.arange(.1,min(5.,L),.1):
  if oldwalk.height(goal-direction*d) is None:break
  join=float(d)
 # Preserve the floor-reference calculation. finish_city_v14.py projects the
 # full apron before the final ramp mesh is accepted; both stages are required.
 ramp_start=max([route.project(Point(q)) for part in shapely.get_parts(route.intersection(fore)) if part.geom_type=='LineString' for q in part.coords] or [0.]);ramp_end=max(ramp_start+.3,L-join)
 center=np.array(poly.centroid.coords[0]);terrain_center=soil.height(center);allow=.026*max(.3,ramp_end-ramp_start);surface_floor=gz+.001+float(np.clip((terrain_center if terrain_center is not None else gz)-gz,-allow,allow))
 paving=unary_union([fore,route.buffer(1.8,cap_style=2,join_style=2)])
 grad=[]
 for axis in range(2):
  dd=np.zeros(2);dd[axis]=.12;z0=oldwalk.height(goal-dd);z1=oldwalk.height(goal+dd);grad.append((z1-z0)/.24 if z0 is not None and z1 is not None else 0.)
 return {'name':name+'_Entrance_Walk','polygon':paving,'fore':fore,'floor_surface':surface_floor,'goal':goal.tolist(),'goal_z':gz,'route':coords.tolist(),'clear_width_m':3.6,'kind':kind,'building':name,'ramp_start':ramp_start,'ramp_end':ramp_end,'goal_gradient':grad,'goal_name':g['name'],'route_length_m':L}
cbd_assignment=[
 ('O37','MAIN_CBD_0051',0),('M38','MAIN_CBD_0054',0),('G41','MAIN_CBD_0052',180),('G42','MAIN_CBD_0055',90),
 ('O34','MAIN_CBD_0011',270),('U31','MAIN_CBD_0093',270),('O40','MAIN_CBD_0066',270),('G45','MAIN_CBD_0076',90),
 ('O39','MAIN_CBD_0003',0),('O46','MAIN_CBD_0007',180),('G44','MAIN_CBD_0065',0),('O43','MAIN_CBD_0068',180),
 ('O47','MAIN_CBD_0055_UNUSED',0),('O42','MAIN_CBD_0074',90),('G48','MAIN_CBD_0006',270)]
# Every retained CBD slot is consumed once; O47 occupies the remaining eastern slot.
cbd_assignment=[(k,'MAIN_CBD_0083' if s=='MAIN_CBD_0055_UNUSED' else s,d) for k,s,d in cbd_assignment]
assert {s for k,s,d in cbd_assignment}==set(cbd_slots)
todo=[]
for key,slot,deg in cbd_assignment:todo.append({'key':key,'center':cbd_slots[slot]['center'],'preferred':deg,'slot':slot})
todo.append({'key':'G33','center':[697.,904.],'preferred':180,'slot':government_slot})
todo.extend({k:v for k,v in r.items() if k!='poly'} for r in apartment_records)
future_slots={s:Polygon(b['footprint']) for s,b in cbd_slots.items()};future_slots[government_slot]=Polygon(next(b['footprint'] for b in baseline['buildings'] if b['name']==government_slot))
for r in apartment_records:future_slots[r['key']]=r['poly']
for spec in todo:
 key=spec['key'];t=templates[key];zone=t['zone'];name=('CBD_V14_' if zone=='CBD' else 'GOV_V14_' if zone=='GOVERNMENT' else 'APT_V14_')+key;slot=spec.get('slot',key)
 others=[q for s,q in future_slots.items() if s!=slot];ret=[Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]+[Polygon(r['footprint_xy']) for r in placed]
 # Apartment source sites were only held as planning polygons, never duplicated in the final list.
 blocked=unary_union(ret+others+[reservation]);options=[]
 pref=spec['preferred'];degrees=list(dict.fromkeys([pref,pref+90,pref-90,pref+180]))
 for deg in degrees:
  theta=math.radians(deg)
  for dx,dy in [(0,0),(-3,0),(3,0),(0,-3),(0,3),(-6,0),(6,0),(0,-6),(0,6)]:
   center=np.array(spec['center'])+[dx,dy];face,poly=footprint(center,t['width'],t['depth'],theta)
   if poly.intersection(blocked).area>.001 or poly.intersection(road_full).area>.001 or poly.intersection(protected_walks).area>.001 or not land.covers(poly.buffer(.15)):continue
   if zone=='CBD' and not cbd_boundary.covers(poly.buffer(.1)):continue
   walk=plan_access(name,poly,face,theta,t['width'],'MAIN',blocked)
   if walk is None:continue
   penalty=0 if deg==pref else 18.;score=walk['route_length_m']+penalty+math.hypot(dx,dy)*1.3
   options.append((score,face,poly,theta,walk))
  if options and deg==pref:break
 if not options:raise RuntimeError(('No legal oriented building/access',key,spec))
 _,face,poly,theta,walk=min(options,key=lambda v:v[0]);floor=walk['floor_surface']+.028
 zz=[soil.height(q) for q in shapely.segmentize(poly,2).exterior.coords];zz=[v for v in zz if v is not None]
 rec={'instance_name':name,'file':t['file'],'source_filename':t['file'],'original_upload_name':t['original'],'source_key':key,'uniform_scale':t['scale'],'local_axis_scale':[1.,1.,1.],'target_height_m':t['height'],'source_bounds':[t['lo'].tolist(),t['hi'].tolist()],'source_floor_reference':float(t['lo'][2]),'anchor':face.tolist(),'theta':theta,'angle':math.degrees(theta),'center':list(poly.centroid.coords[0]),'region':'MAIN','zone':zone,'footprint_xy':list(poly.exterior.coords)[:-1],'pad_xy':list(poly.buffer(.08,join_style=2).exterior.coords),'floor':floor,'foundation_bottom_m':min([floor-.45,*zz])-.12,'building_count_units':1,'typology':'serviced_apartment_highrise' if zone=='APARTMENT' else 'municipal_government' if zone=='GOVERNMENT' else 'office_source_building','reuse_rotation_only_no_mirror':True,'added_in_version':'v14','replaces_placeholder_sites':[spec['slot']] if 'slot' in spec else [],'access_alley':walk['name'],'direct_sidewalk_frontage':False,'source_used_once':True}
 rec.update(left=0.,right=float(t['width']),front=0.,turn=0.,direct_alley_frontage=True)
 placed.append(rec);new_walks.append(walk);future_slots.pop(slot,None)
 print('SITE_READY',key,np.round(rec['center'],2).tolist(),'front_degrees',round(math.degrees(theta),1),'walk',round(walk['route_length_m'],1),flush=True)
assert len(placed)==19 and not future_slots
for b in new_ph:
 poly=Polygon(b['footprint']);center=np.array(b['center']);others=[Polygon(q['footprint']) for q in p['buildings'] if q['name']!=b['name']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']+placed]+[reservation];blocked=unary_union(others);candidates=[]
 w,d=b['size'][:2]
 for deg in [0,90,180,270]:
  # Use the matching face of the already accepted footprint, keeping every placeholder lot fixed.
  theta=math.radians(deg);u=np.array([math.cos(theta),math.sin(theta)]);n=np.array([u[1],-u[0]]);xy=np.array(poly.exterior.coords)[:-1];support=max((xy-center)@n);umin=min((xy-center)@u);umax=max((xy-center)@u);face=center+n*support+u*umin
  walk=plan_access(b['name'],poly,face,theta,umax-umin,b['region'],blocked,'villa_access' if b['zone']=='VILLA' else 'apartment_access')
  if walk:candidates.append((walk['route_length_m'],walk,deg))
 if not candidates:raise RuntimeError(('No placeholder access',b['name']))
 _,walk,deg=min(candidates,key=lambda x:x[0]);b['base']=walk['floor_surface']+.028;b['front_rotation_degrees']=deg;b['access_alley']=walk['name'];new_walks.append(walk)
 print('PLACEHOLDER_ACCESS',b['name'],round(walk['route_length_m'],1),flush=True)
# A broad forecourt is attached to the government entrance and the northern sidewalk.
gov=next(r for r in placed if r['zone']=='GOVERNMENT');gw=next(w for w in new_walks if w['building']==gov['instance_name'])
other_buildings=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']+placed])
court=box(671.,920.,728.,936.).difference(other_buildings.buffer(.4)).difference(road_full.buffer(.15))
court=unary_union([q for q in shapely.get_parts(court) if q.geom_type=='Polygon' and q.intersects(gw['polygon'])])
assert court.area>250.,('Municipal forecourt too small',court.area)
assert court.intersection(other_buildings).area<.001 and court.intersection(carriage).area<.001
gw['polygon']=unary_union([gw['polygon'],court]);gw['municipal_forecourt_area_m2']=court.area
# Remove only replaced/reshaped placeholder faces; remap retained global IDs.
old_ph=baseline['buildings'];new_index={b['name']:i for i,b in enumerate(p['buildings'])};drop_names=removed_names|villa_names;changed_original=set()
for ob in list(sc.objects):
 if ob.type!='MESH':continue
 attr=ob.data.attributes.get('source_building_index')
 if not attr:continue
 m=ob.data;ids=np.array([v.value for v in attr.data]);keep=np.array([old_ph[int(i)]['name'] not in drop_names for i in ids]);newids=np.array([new_index[old_ph[int(i)]['name']] for i,k in zip(ids,keep) if k],np.int32)
 if not keep.all():changed_original.add(ob.name)
 if not keep.any():bpy.data.objects.remove(ob,do_unlink=True);continue
 if keep.all():attr.data.foreach_set('value',newids)
 else:
  data=bpy.data.meshes.new(m.name+'_v14');data.from_pydata([v.co[:] for v in m.vertices],[],[list(q.vertices) for q,k in zip(m.polygons,keep) if k])
  for mat in m.materials:data.materials.append(mat)
  data.polygons.foreach_set('material_index',np.array([q.material_index for q,k in zip(m.polygons,keep) if k],np.int32));data.attributes.new(name='source_building_index',type='INT',domain='FACE').data.foreach_set('value',newids);data.update();ob.data=data
 ob['placeholder_lot_count']=len(set(newids))
for r in placed:
 t=templates[r['source_key']];inst=bpy.data.objects.new(r['instance_name'],None);sc.collection.objects.link(inst);inst.parent=sourceparent;inst.matrix_world=Matrix.Translation((*r['anchor'],r['floor']-.008))@Matrix.Rotation(r['theta'],4,'Z')@Matrix.Diagonal((r['uniform_scale'],r['uniform_scale'],r['uniform_scale'],1.))@Matrix.Translation(tuple(-t['lo']))
 for j,data in enumerate(t['parts']):ob=bpy.data.objects.new(r['instance_name']+f'_Source_Mesh_{j:02d}',data);sc.collection.objects.link(ob);ob.parent=inst;ob.matrix_basis=Matrix.Identity(4);ob['source_filename']=r['file']
 for k,v in {'is_building_instance':True,'source_filename':r['file'],'source_sha256':hashlib.sha256((SRC/r['file']).read_bytes()).hexdigest(),'target_height_m':r['target_height_m'],'building_count_units':1,'reuse_template_key':r['source_key'],'added_in_version':'v14','zone':r['zone']}.items():inst[k]=v
 prism(Polygon(r['pad_xy']),r['floor']-.018,r['foundation_bottom_m'],r['instance_name']+'_Foundation')
for b in new_ph:
 poly=Polygon(b['footprint']);base=b['base'];top=base+b['height'];bottom=min([base-.5]+[soil.height(q) or base-.5 for q in poly.exterior.coords])-.1
 ob=prism(poly,top,base,b['name'],villa_mat if b['zone']=='VILLA' else apt_mat,zoneparent);ob.data.attributes.new(name='source_building_index',type='INT',domain='FACE').data.foreach_set('value',np.full(len(ob.data.polygons),new_index[b['name']],np.int32));ob['placeholder_lot_count']=1;ob['typology']=b['typology'];ob['is_placeholder']=True;ob.data.materials.append(villa_roof)
 for fi in [1,3]:ob.data.polygons[fi].material_index=1
 prism(poly.buffer(.06,join_style=2),base-.018,bottom,b['name']+'_Foundation')
 if b['zone']=='VILLA':
  # One house per footprint; roof trim and garden are decorations, not extra units.
  roof=prism(poly.buffer(.18,join_style=2),top+.18,top-.12,b['name']+'_Roof_Trim',villa_roof,zoneparent);roof['building_count_units']=0
  x,y=b['center'];garden=box(x-11,y-14,x+11,y+14).difference(poly.buffer(.35,join_style=2)).difference(unary_union([w['polygon'].buffer(.05) for w in new_walks]));b['garden_polygon']=[list(q.exterior.coords) for q in shapely.get_parts(garden) if q.geom_type=='Polygon']
  for j,q in enumerate(shapely.get_parts(garden)):
   if q.geom_type=='Polygon':
    verts=[];faces=[]
    for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(q)):
     xy=np.array(tr.exterior.coords)[:3];k=len(verts);verts.extend([[*v,max(base-.05,(soil.height(v) or base-.05)+.025)] for v in xy]);faces.append([k,k+1,k+2])
    obg=mesh(b['name']+f'_Garden_{j}',verts,faces,garden_mat,zoneparent);obg['building_count_units']=0
# Build walking surfaces sequentially so intersecting new paths inherit identical heights.
def build_walk(walk):
 global oldwalk
 route=LineString(walk['route']);goal=np.array(walk['goal']);grad=np.array(walk.get('goal_gradient',[0.,0.]));floor=walk['floor_surface'];old_polys=[Polygon(tr[:,:2]) for tr in oldwalk.tri];tree=shapely.STRtree(old_polys)
 oldshape=unary_union([old_polys[i] for i in tree.query(walk['polygon']) if old_polys[i].intersects(walk['polygon'])])
 def height(xy):
  xy=np.array(xy);old=oldwalk.height(xy)
  if old is not None:return old+.001
  if walk['fore'].covers(Point(xy)):return floor
  s=route.project(Point(xy));t=float(np.clip((s-walk['ramp_start'])/max(.3,walk['ramp_end']-walk['ramp_start']),0,1));plane=walk['goal_z']+.001+float(grad@(xy-goal));return floor*(1-t)+plane*t
 v=[];f=[]
 pieces=[walk['polygon'].difference(oldshape),walk['polygon'].intersection(oldshape)];pieces=[part for q in pieces for part in [q.difference(walk['fore']),q.intersection(walk['fore'])]]
 for piece in pieces:
  if piece.is_empty:continue
  for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(piece,.85))):
   xy=np.array(tri.exterior.coords)[:3]
   if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
   k=len(v);v.extend([[*q,height(q)] for q in xy]);f.append([k,k+1,k+2])
 ob=mesh(walk['name'],v,f,atlas,walkparent,True);ob['surface_type']='v14_access_walk';ob['clear_width_m']=walk['clear_width_m'];ob['connects_to']=walk['goal_name'];walk_obs.append(ob);bpy.context.view_layer.update();oldwalk=HeightField(walk_obs);print('WALK_BUILT',walk['name'],len(f),flush=True)
for walk in new_walks:build_walk(walk)
# Preserve the existing coastal road, adding a continuous 7 m sea-facing sidewalk.
coastal_edges=[e for e in p['edges'] if e['name']=='MAIN_COASTAL_RING' and max(q[0] for q in e['points'])<-500 and min(q[1] for q in e['points'])>=200]
coastal_edges.sort(key=lambda e:e['points'][0][1]);pts=[]
for e in coastal_edges:
 e['display_name_zh']='滨海大道';pts.extend(e['points'] if not pts else e['points'][1:])
coastline=LineString(np.array(pts)[:,:2]);promenade=coastline.buffer(14.5,single_sided=True,join_style=2).difference(coastline.buffer(9.8,single_sided=True,join_style=2)).intersection(land.buffer(-.1)).difference(carriage).difference(other_buildings.buffer(.1))
assert promenade.area>3000
def coastal_sample(xy):
 s=coastline.project(Point(xy));q=np.array(coastline.interpolate(s).coords[0]);a0=np.array(coastline.interpolate(max(0,s-.15)).coords[0]);a1=np.array(coastline.interpolate(min(coastline.length,s+.15)).coords[0]);u=(a1-a0)/np.linalg.norm(a1-a0);n=np.array([-u[1],u[0]]);return s,q,u,n
def coastal_height(xy):
 z=oldwalk.height(xy)
 if z is not None:return z+.001
 s,q,u,n=coastal_sample(xy);z=oldwalk.height(q+n*9.9)
 if z is None:
  samples=[oldwalk.height(q+n*d) for d in [9.75,9.5,9.,8.5]];z=next((v for v in samples if v is not None),None)
 if z is None:raise RuntimeError(('No coastal sidewalk height',list(xy),s))
 return z-.012*max(0,float((np.array(xy)-q)@n)-9.9)+.001
old_polys=[Polygon(tr[:,:2]) for tr in oldwalk.tri];tree=shapely.STRtree(old_polys);oldshape=unary_union([old_polys[i] for i in tree.query(promenade) if old_polys[i].intersects(promenade)]);v=[];f=[]
for piece in [promenade.difference(oldshape),promenade.intersection(oldshape)]:
 for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(shapely.segmentize(piece,1.2))):
  xy=np.array(tr.exterior.coords)[:3]
  if np.cross(xy[1]-xy[0],xy[2]-xy[0])<0:xy=xy[::-1]
  k=len(v);v.extend([[*q,coastal_height(q)] for q in xy]);f.append([k,k+1,k+2])
prom_obj=mesh('MAIN_Binhai_Avenue_Promenade',v,f,atlas,walkparent,True);prom_obj['surface_type']='v14_coastal_promenade';prom_obj['clear_walking_width_m']=4.5;prom_obj['total_seaward_sidewalk_width_m']=7.;walk_obs.append(prom_obj)
plant_records=[]
for i,s in enumerate(np.arange(14,coastline.length-12,29.)):
 q=np.array(coastline.interpolate(s).coords[0]);_,_,u,n=coastal_sample(q);xy=q+n*13.25
 if not promenade.covers(Point(xy).buffer(.45)):continue
 z=coastal_height(xy)
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.16,depth=3.4,location=(*xy,z+1.7));tr=bpy.context.object;tr.name=f'MAIN_Binhai_Tree_{i:02d}_Trunk';tr.parent=zoneparent;tr.data.materials.append(trunk_mat);tr['building_count_units']=0
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=2.2,location=(*xy,z+5.0));cr=bpy.context.object;cr.name=f'MAIN_Binhai_Tree_{i:02d}_Crown';cr.scale=(.85,.85,1.05);cr.parent=zoneparent;cr.data.materials.append(tree_mat);cr['building_count_units']=0
 plant_records.append({'xy':xy.tolist(),'ground_z':z,'trunk_radius_m':.16,'crown_minimum_clearance_m':2.69})
rail_v=[];rail_f=[]
def beam(a0,b0,width,height):
 a0=np.array(a0);b0=np.array(b0);d=b0-a0;xy=np.array([-d[1],d[0],0.]);xy/=max(np.linalg.norm(xy),1e-12);side=xy*width/2;up=np.array([0,0,height/2]);k=len(rail_v)
 rail_v.extend([list(q) for q in [a0-side-up,a0+side-up,b0+side-up,b0-side-up,a0-side+up,a0+side+up,b0+side+up,b0-side+up]])
 rail_f.extend([[k+j for j in face] for face in [[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]]])
rail_points=[]
for s in np.linspace(1.,coastline.length-1.,int(coastline.length/4)+1):
 q=np.array(coastline.interpolate(s).coords[0]);_,_,u,n=coastal_sample(q);xy=q+n*14.28
 if not promenade.buffer(.03).covers(Point(xy)):continue
 z=coastal_height(xy);rail_points.append((s,xy,z));beam([*xy,z+.52],[*xy+u*.035,z+.52],.07,1.04)
for (s0,xy0,z0),(s1,xy1,z1) in zip(rail_points[:-1],rail_points[1:]):
 if s1-s0<5.:
  for h in [.42,1.05]:beam([*xy0,z0+h],[*xy1,z1+h],.045,.055)
railing=mesh('MAIN_Binhai_Avenue_Seaside_Railing',rail_v,rail_f,rail_mat,zoneparent);railing['building_count_units']=0
print('BINHAI_BUILT',coastline.length,promenade.area,'trees',len(plant_records),flush=True)
# Cut only occupied ground. Retaining faces close the edge to the original terrain.
cuts=unary_union([Polygon(r['pad_xy']) for r in placed]+[Polygon(b['footprint']).buffer(.08,join_style=2) for b in new_ph]+[w['polygon'].buffer(.012,join_style=2) for w in new_walks]+[promenade.buffer(.012,join_style=2)])
cut_count=0
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
 data=bpy.data.meshes.new(m.name+'_v14_cuts');data.from_pydata(v,[],f)
 for mat in m.materials:data.materials.append(mat)
 data.polygons.foreach_set('material_index',np.array(mat_indices,np.int32))
 if colors:data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(colors,np.float32).ravel())
 data.update();ob.data=data;cut_count+=changes;changed_original.add(ob.name);print('TERRAIN_CUT',ob.name,changes,flush=True)
bpy.context.view_layer.update();new_surfaces=HeightField([bpy.data.objects[r['instance_name']+'_Foundation'] for r in placed]+[bpy.data.objects[b['name']+'_Foundation'] for b in new_ph]+[bpy.data.objects[w['name']] for w in new_walks]+[prom_obj]);walls_v=[];walls_f=[];wall_missing=0
for poly in shapely.get_parts(shapely.orient_polygons(cuts,exterior_cw=False)):
 if poly.geom_type!='Polygon':continue
 for ring in [poly.exterior,*poly.interiors]:
  coords=np.array(shapely.segmentize(ring,1.).coords)
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
wallob=mesh('V14_Terrain_Cut_Retaining_Walls',walls_v,walls_f,concrete);wallob['surface_type']='terrain_cut_retaining_wall'
p['real_buildings'].extend(placed);p['schema']='hero13.city.regional-update.v14';p['access_v14']=[{k:(list(v.exterior.coords) if k in ['polygon','fore'] else v) for k,v in w.items()} for w in new_walks]
p['cbd_plan'].update(existing_buildings=29,source_buildings=29,placeholder_buildings=0,planned_total_including_tianming=30)
apartment_polygon=box(-495.,1080.,470.,1215.).intersection(land)
government_polygon=box(632.,770.,817.,940.)
villa_polygon=box(-1200.,-1030.,-1020.,-890.).intersection(land)
p['urban_areas_v14']={
 'municipal_campus':{'name_zh':'东侧市政府片区','polygon':list(government_polygon.exterior.coords),'area_m2':government_polygon.area,'main_building':gov['instance_name'],'support_buildings':[b['name'] for b in p['buildings'] if b['zone']=='GOVERNMENT'],'forecourt_area_m2':court.area,'government_facade_towards':'north / existing east-west avenue'},
 'north_apartments':{'name_zh':'北侧公寓区','polygon':list(apartment_polygon.exterior.coords),'area_m2':apartment_polygon.area,'source_towers':[r['instance_name'] for r in placed if r['zone']=='APARTMENT'],'midrise_placeholders':[b['name'] for b in p['buildings'] if b['zone']=='APARTMENT'],'building_units':12,'source_tower_use':'serviced apartments; existing uploaded highrise facade geometry retained'},
 'binhai_avenue':{'name_zh':'滨海大道','road_original_name':'MAIN_COASTAL_RING','centerline':pts,'length_m':coastline.length,'carriage_width_m':15.,'sea_side_sidewalk_total_width_m':7.,'clear_walking_width_m':4.5,'added_promenade_area_m2':promenade.area,'promenade_polygon':[list(g.exterior.coords) for g in shapely.get_parts(promenade) if g.geom_type=='Polygon'],'trees':plant_records,'road_geometry_preserved':True},
 'southwest_villas':{'name_zh':'西南岛别墅区','polygon':list(villa_polygon.exterior.coords),'area_m2':villa_polygon.area,'building_units':9,'placeholder_buildings':sorted(villa_names),'house_footprint_m':[16.,22.],'height_m':8.4,'source_villa_model_supplied':False,'connection_policy':'Existing island roads retained; every house receives a separate walking connection'}}
counts=collections.Counter(b['zone'] for b in p['buildings']);counts.update(r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN') for r in p['real_buildings'])
total=len(p['buildings'])+len(p['real_buildings']);assert total==664 and len(p['buildings'])==540 and len(p['real_buildings'])==124
p['stats'].update(buildings=total,placeholder_lots=len(p['buildings']),real_buildings=len(p['real_buildings']),source_asset_types=53,source_geometry_texture_types=51,cbd_buildings=29,building_count_by_zone=dict(counts),apartment_buildings=12,villa_buildings=9,government_area_buildings=7)
p['stats']['building_coverage_percent']=unary_union([Polygon(b['footprint']) for b in p['buildings']]+[Polygon(r['footprint_xy']) for r in p['real_buildings']]).area/p['stats']['land_area_m2']*100
root['version']='v14_regional_district_update';root['building_count']=total
for im in bpy.data.images:
 if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
  try:im.pack()
  except RuntimeError:pass
unchanged=[]
for name,fp in original_fingerprints.items():
 if name in changed_original:continue
 ob=bpy.data.objects.get(name);assert ob is not None and hash_mesh(ob)==fp,('Unexpected prior mesh modification',name);unchanged.append(name)
assert all(r==original_source_metadata[r['instance_name']] for r in p['real_buildings'][:105])
report={'status':'BUILT','version':'v14','city_buildings':total,'placeholders':540,'source_instances':124,'land_area_m2':p['stats']['land_area_m2'],'cbd_existing':29,'cbd_source_instances':29,'cbd_placeholders':0,'cbd_with_future_tianming':30,'new_input_instances':19,'new_offices':15,'new_apartment_towers':3,'new_government_buildings':1,'new_midrise_placeholders':9,'villa_lots_remodelled':9,'prior_source_instances_preserved':105,'unchanged_meshes':len(unchanged),'changed_original_meshes':sorted(changed_original),'terrain_triangles_cut':cut_count,'retaining_wall_triangles':len(walls_f),'unsampled_wall_segments':wall_missing,'walk_connections':len(new_walks),'road_graph_geometry_unchanged':True,'tianming_reservation_unchanged':True,'original_mesh_fingerprints':original_fingerprints,'unchanged_mesh_names':unchanged}
(OUT/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(OUT/'v14_build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(OUT/'new_building_descriptors.json').write_text(json.dumps(placed,ensure_ascii=False,indent=2));(OUT/'urban_areas_v14.json').write_text(json.dumps(p['urban_areas_v14'],ensure_ascii=False,indent=2));shutil.copy2(BASE/'tianming_reservation.json',OUT/'tianming_reservation.json');shutil.copy2(BASE/'rear_asset_pool.json',OUT/'rear_asset_pool.json')
with (OUT/'building_registry.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['id','kind','zone','typology','source_file','source_key','x','y','height_m','count_units']);w.writeheader()
 for b in p['buildings']:w.writerow({'id':b['name'],'kind':'placeholder','zone':b['zone'],'typology':b['typology'],'x':b['center'][0],'y':b['center'][1],'height_m':b['height'],'count_units':1})
 for r in p['real_buildings']:w.writerow({'id':r['instance_name'],'kind':'source','zone':r.get('zone','CBD' if r['instance_name'].startswith('CBD_') else 'OLDTOWN'),'typology':r.get('typology','retained_source'),'source_file':r['file'],'source_key':r.get('source_key',''),'x':r['center'][0],'y':r['center'][1],'height_m':r['target_height_m'],'count_units':1})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'huizhou_road_network.blend'),compress=True)
print('V14_NATIVE_BUILD_COMPLETE',json.dumps({k:v for k,v in report.items() if k not in ['original_mesh_fingerprints','unchanged_mesh_names']}),flush=True)
