"""Deploy three original shop-house assets as one connected arcade street."""
from pathlib import Path
import argparse,hashlib,json,math,sys
import bpy,numpy as np
from mathutils import Matrix,Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--sites',type=Path,required=True);ap.add_argument('--models',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.view_layer.update();sc=bpy.context.scene
p=json.loads(a.plan.read_text());cfg=json.loads(a.sites.read_text());site=cfg['site'];origin=np.array(site['front_origin']);u=np.array(site['u']);v=np.array(site['v']);rot=np.column_stack([u,v]);angle=math.atan2(u[1],u[0]);top=site['foundation_top_m'];bottom=site['foundation_bottom_m'];xmin,xmax=cfg['local_x_range'];back=cfg['local_back_m']
root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout']
def empty(name,parent):
    o=bpy.data.objects.new(name,None);sc.collection.objects.link(o);o.parent=parent;return o
buildings=empty('20_OLDTOWN_CONNECTED_ARCADES',root);ground=empty('21_OLDTOWN_ARCADE_SITE',root)
def fingerprint(objects):
    h=hashlib.sha256()
    for o in sorted(objects,key=lambda o:o.name):
        h.update(o.name.encode());co=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',co);h.update(co.tobytes());ids=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',ids);h.update(ids.tobytes());h.update(np.asarray(o.matrix_world,np.float32).tobytes())
        if o.data.uv_layers.active:
            uv=np.empty(len(o.data.loops)*2,np.float32);o.data.uv_layers.active.data.foreach_get('uv',uv);h.update(uv.tobytes())
    return h.hexdigest()
protected=[o for o in sc.objects if o.type=='MESH' and any(t in o.name for t in ['_Cell_','Junction_Repair','Port_Service_'])]
before=fingerprint(protected)
def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);node=m.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=.91;return m
concrete=material('Oldtown_Arcade_Level_Concrete',(.35,.34,.30));plaster=material('Oldtown_Arcade_Link_Stucco',(.47,.43,.35))
walkmat=bpy.data.materials.get('Road_Modular_Original_Atlas.001') or bpy.data.materials['Road_Modular_Original_Atlas']
cubev=[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)];cubef=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def cube(name,x,y,z,w,d,h,mat):
    m=bpy.data.meshes.new(name);m.from_pydata(cubev,[],cubef);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=ground;xy=origin+u*x+v*y;o.location=(float(xy[0]),float(xy[1]),z);o.scale=(w,d,h);o.rotation_euler[2]=angle;return o
def mesh(name,vertices,faces,mat,atlas=False,uv_coords=None):
    m=bpy.data.meshes.new(name);m.from_pydata(vertices,[],faces);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=ground
    if atlas or uv_coords is not None:
        co=np.asarray(vertices);ids=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',ids);uv=m.uv_layers.new(name='UVMap');arr=np.asarray(uv_coords) if uv_coords is not None else np.c_[.216+.055*np.mod(co[:,0]/5,1),.599+.1777*np.mod(co[:,1]/16.9048,1)];uv.data.foreach_set('uv',arr[ids].astype(np.float32).ravel())
    return o
foundation=cube('Oldtown_Arcade_Shared_Foundation',(xmin+xmax)/2,(back-3.45)/2,(top+bottom)/2,xmax-xmin,back+3.45,top-bottom,concrete)
# The top surface forms a single level pedestrian strip across every seam.
floor_vertices=[];floor_faces=[];floor_uv=[];cuts=np.r_[np.arange(xmin,xmax,16.9048),xmax]
for i,(x0,x1) in enumerate(zip(cuts[:-1],cuts[1:])):
    local=np.array([[x0,-3.44],[x1,-3.44],[x1,.15],[x0,.15]]);xy=local@rot.T+origin;k=len(floor_vertices)
    floor_vertices.extend(np.c_[xy,np.full(4,top+.004)].tolist());floor_faces.extend([[k,k+1,k+2],[k,k+2,k+3]])
    v0=.599;v1=.599+.1777*(x1-x0)/16.9048;floor_uv.extend([(.216,v0),(.216,v1),(.271,v1),(.271,v0)])
floor=mesh('Oldtown_Arcade_Continuous_Floor',floor_vertices,floor_faces,walkmat,uv_coords=floor_uv);floor['walkable']=True;floor['clear_width_m']=2.6
canopy=cube('Oldtown_Arcade_Continuous_Canopy',(xmin+xmax)/2,-1.60,top+3.91,xmax-xmin,3.5,.22,plaster);canopy['purpose']='Continuous weather cover joining the supplied storefronts';canopy['underside_height_m']=3.8
cube('Oldtown_Arcade_Canopy_Fascia',(xmin+xmax)/2,-3.30,top+3.94,xmax-xmin,.16,.30,plaster)
openings=[float((np.array(r['start_xy'])-origin)@u) for r in site['ramp_profiles']]
column_x=[float(x) for x in np.linspace(xmin+.25,xmax-.25,int(math.ceil((xmax-xmin-.5)/4.6))+1) if all(abs(x-c)>1.3 for c in openings)]
for c in openings:
    for x in [c-1.35,c+1.35]:
        if xmin+.2<x<xmax-.2 and min(abs(x-q) for q in column_x)>.65:column_x.append(x)
column_x=np.array(sorted(column_x))
for i,x in enumerate(column_x):cube('Oldtown_Arcade_Column_%02d'%i,float(x),-3.16,top+1.90,.26,.28,3.80,plaster)
records=[]
for i,r in enumerate(cfg['models']):
    source=a.models/r['file'];oldset=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(source.resolve()));bpy.context.view_layer.update();imported=set(sc.objects)-oldset;parts=[o for o in imported if o.type=='MESH'];assert len(parts)==1
    instance=empty(r['instance_name'],buildings);scale=r['uniform_scale'];tx=r['local_x_translation'];instance.matrix_world=Matrix.Translation((float(origin[0]),float(origin[1]),top-.008))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation((tx,0,0))@Matrix.Scale(scale,4)@Matrix.Translation((0,-r['source_front_reference'],-r['source_floor_reference']))
    for o in imported:
        if o.parent not in imported:
            old=o.matrix_world.copy();o.parent=instance;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=old
    instance['is_building_instance']=True;instance['source_filename']=r['file'];instance['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();instance['district']='OLDTOWN';instance['region']='MAIN';instance['target_height_m']=r['target_height_m'];instance['uniform_scale']=scale;instance['connected_arcade_row']='M19_Connected_Arcade_Row';instance['is_placeholder']=False
    for j,o in enumerate(parts):o.name=r['instance_name']+f'_Source_Mesh_{j:02d}';o['source_filename']=r['file'];o['is_placeholder']=False
    lo,hi=np.array(r['source_bounds']);rect=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]);rect=(rect-np.array([0,r['source_front_reference']]))*scale+np.array([tx,0]);world=rect@rot.T+origin;center=world.mean(0);access=site['ramp_profiles'][i]
    record={'instance_name':r['instance_name'],'source_filename':r['file'],'file':r['file'],'center':center.tolist(),'target_height_m':r['target_height_m'],'uniform_scale':scale,'source_dimensions_m':r['source_dimensions'],'placed_dimensions_m':(np.array(r['source_dimensions'])*scale).tolist(),'angle':angle,'footprint_xy':world.tolist(),'foundation_top_m':top,'foundation_bottom_m':bottom,'building_base_m':top-.008-r['source_floor_reference']*scale,'source_floor_reference':r['source_floor_reference'],'source_sha256':instance['source_sha256'],'source_mesh_count':len(parts),'district':'OLDTOWN','region':'MAIN','connected_arcade_row':'M19_Connected_Arcade_Row','access_start_xy':access['start_xy'],'access_end_xy':access['end_xy'],'access_width_m':2.,'access_length_m':access['length_m'],'access_maximum_grade':access['maximum_grade']}
    records.append(record)
# Fill only the interior party-wall seams; original textured source meshes and
# UVs remain untouched. The stepped original rooflines are retained.
seams=[]
for i in range(2):
    left,right=cfg['models'][i:i+2];x1=left['source_core_right']*left['uniform_scale']+left['local_x_translation'];x2=right['source_core_left']*right['uniform_scale']+right['local_x_translation'];x=(x1+x2)/2
    h=min(left['target_height_m']-left['source_floor_reference']*left['uniform_scale'],right['target_height_m']-right['source_floor_reference']*right['uniform_scale'])-.3
    depth=min((left['source_bounds'][1][1]-left['source_front_reference'])*left['uniform_scale'],(right['source_bounds'][1][1]-right['source_front_reference'])*right['uniform_scale'])
    cube('Oldtown_Arcade_Shared_Wall_Seam_%02d'%i,x,depth/2,top+h/2,.16,depth+.12,h,plaster)
    seams.append({'left':left['instance_name'],'right':right['instance_name'],'core_wall_overlap_m':float(x1-x2),'local_x':float(x),'shared_wall_height_m':float(h)})
ramps=[]
for i,r in enumerate(site['ramp_profiles']):
    xy=np.array(r['xy']);z=np.array(r['z']);rows,cols=z.shape;nv=z.size;floorz=r['ground_floor'];co=np.dstack([xy,z]).reshape(-1,3).tolist()+np.dstack([xy,np.full_like(z,floorz)]).reshape(-1,3).tolist();faces=[]
    for row in range(rows-1):
        for col in range(cols-1):
            k=row*cols+col;l=(row+1)*cols+col
            for f in [[k,l,l+1],[k,l+1,k+1]]:faces.extend([f,[j+nv for j in f[::-1]]])
    ring=list(range(cols))+[j*cols+cols-1 for j in range(1,rows)]+list(range(nv-2,nv-cols-1,-1))+[j*cols for j in range(rows-2,0,-1)]
    for j,k in zip(ring,ring[1:]+ring[:1]):faces.append([j,k,k+nv,j+nv])
    stations=np.linspace(0,r['length_m'],rows);uv=[(.271-.055*j/(cols-1),.7766-.1777*stations[k]/16.9048) for k in range(rows) for j in range(cols)]+[(.216,.67)]*nv
    name='Oldtown_Arcade_Sidewalk_Ramp_%02d'%i;o=mesh(name,co,faces,walkmat,uv_coords=uv);o['walkable']=True;o['width_m']=2.;o['maximum_grade']=r['maximum_grade'];ramps.append({k:v for k,v in r.items() if k not in ['xy','z']});ramps[-1]['name']=name
for name in site['removed_placeholders']:
    old=bpy.data.objects.get(name);assert old is not None and old.get('is_placeholder');bpy.data.objects.remove(old,do_unlink=True)
p['buildings']=[b for b in p['buildings'] if b['name'] not in site['removed_placeholders']];p['real_buildings'].extend(records);p['stats']['placeholder_buildings']=len(p['buildings']);p['stats']['real_buildings']=len(p['real_buildings']);p['stats']['buildings']=len(p['buildings'])+len(p['real_buildings']);p['stats']['connected_arcade_source_models']=3
row={'name':'M19_Connected_Arcade_Row','road':site['road'],'front_origin':origin.tolist(),'u':u.tolist(),'v':v.tolist(),'length_m':cfg['row_length_m'],'local_x_range':[xmin,xmax],'pad_rectangle':site['pad_rectangle'],'foundation_top_m':top,'foundation_bottom_m':bottom,'terrain_range_m':site['terrain_max_m']-site['terrain_min_m'],'canopy_underside_height_m':3.8,'clear_corridor_width_m':2.6,'covered_floor_local_y_range':[-2.95,-.35],'ramps':ramps,'seams':seams,'column_local_x':column_x.tolist(),'instances':[r['instance_name'] for r in records]}
p['connected_arcades']=row;root['real_building_count']=len(p['real_buildings']);root['placeholder_building_count']=len(p['buildings'])
bpy.context.view_layer.update();after=fingerprint(protected);assert before==after,'Protected road, sidewalk or terrain changed'
report={'row':row,'instances':records,'removed_placeholders':site['removed_placeholders'],'original_road_sidewalk_terrain_unchanged':True,'protected_geometry_sha256':before,'source_model_count':3,'original_texture_images_preserved_on_import':True}
(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(a.out/'connected_arcades.json').write_text(json.dumps(report,indent=2))
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
        try:im.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str((a.out/'huizhou_road_network.blend').resolve()),compress=True)
bpy.ops.export_scene.gltf(filepath=str((a.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular: mortalityrexotable, CC BY 4.0. User-supplied building assets retain source textures.')
print('CONNECTED_ARCADES_COMPLETE',json.dumps({'instances':len(records),'row_length_m':cfg['row_length_m'],'removed':site['removed_placeholders'],'glb_bytes':(a.out/'huizhou_road_network.glb').stat().st_size}),flush=True)
