"""Replace the added canopy with an open shop frontage and add four assets."""
from pathlib import Path
import argparse,hashlib,json,math,sys
import bpy,numpy as np
from mathutils import Matrix
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--sites',type=Path,required=True);ap.add_argument('--models',type=Path,required=True);ap.add_argument('--chunk-report',type=Path,required=True);ap.add_argument('--deps',type=Path);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
import shapely
from shapely.geometry import Polygon
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.loads(a.plan.read_text());cfg=json.loads(a.sites.read_text());root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout'];a.out.mkdir(parents=True,exist_ok=True)
def below(o,names):
    while o:
        if o.name in names:return True
        o=o.parent
    return False
def fingerprint(objects):
    h=hashlib.sha256()
    for o in sorted(objects,key=lambda o:o.name):
        h.update(o.name.encode());v=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',v);h.update(v.tobytes());ids=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',ids);h.update(ids.tobytes());h.update(np.asarray(o.matrix_world,np.float32).tobytes())
        if o.data.uv_layers.active:
            uv=np.empty(len(o.data.loops)*2,np.float32);o.data.uv_layers.active.data.foreach_get('uv',uv);h.update(uv.tobytes())
    return h.hexdigest()
protected=[o for o in sc.objects if o.type=='MESH' and any(n in o.name for n in ['_Road_','Sidewalk_Modular','Sidewalk_Continuous_Transition','Continuous_Pavement','Junction_Repairs_Asphalt','Junction_Repairs_Original_Road_Kit','Junction_Repairs_Sidewalk','Port_Service_'])];before=fingerprint(protected)
oldnames=set(p['connected_arcades']['instances']);oldgroups={'20_OLDTOWN_CONNECTED_ARCADES','21_OLDTOWN_ARCADE_SITE'};removed_cover=[o.name for o in sc.objects if o.name.startswith(('Oldtown_Arcade_Continuous_Canopy','Oldtown_Arcade_Canopy_Fascia','Oldtown_Arcade_Column_'))]
oldobjects=[o for o in sc.objects if below(o,oldgroups)]
for o in oldobjects:bpy.data.objects.remove(o,do_unlink=True)
p['real_buildings']=[b for b in p['real_buildings'] if b['instance_name'] not in oldnames]
def group(name):
    o=bpy.data.objects.new(name,None);sc.collection.objects.link(o);o.parent=root;return o
realgroup=group('20_OLDTOWN_EXPANDED_REAL_BUILDINGS');sitegroup=group('21_OLDTOWN_OPEN_STREET_ADAPTATION')
def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.91;return m
concrete=material('Oldtown_Expansion_Concrete',(.35,.34,.30));plaster=material('Oldtown_Expansion_Seam_Plaster',(.46,.43,.36));walkmat=bpy.data.materials.get('Road_Modular_Original_Atlas.001') or bpy.data.materials['Road_Modular_Original_Atlas']
cubev=[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)];cubef=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def cube(name,origin,u,v,x,y,z,w,d,h,mat):
    m=bpy.data.meshes.new(name);m.from_pydata(cubev,[],cubef);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=sitegroup;xy=origin+u*x+v*y;o.location=(*xy,z);o.scale=(w,d,h);o.rotation_euler[2]=math.atan2(u[1],u[0]);return o
def mesh(name,verts,faces,mat,uv=None):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);sc.collection.objects.link(o);o.parent=sitegroup
    if uv is not None:
        ids=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',ids);layer=m.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray(uv,np.float32)[ids].ravel())
    return o
def floor(name,origin,u,v,xmin,xmax,ymin,ymax,z):
    verts=[];faces=[];uv=[];cuts=np.r_[np.arange(xmin,xmax,16.9048),xmax]
    for x0,x1 in zip(cuts[:-1],cuts[1:]):
        local=np.array([[x0,ymin],[x1,ymin],[x1,ymax],[x0,ymax]]);xy=origin+local[:,0,None]*u+local[:,1,None]*v;k=len(verts);verts.extend(np.c_[xy,np.full(4,z)].tolist());faces.extend([[k,k+1,k+2],[k,k+2,k+3]]);v1=.599+.1777*(x1-x0)/16.9048;uv.extend([(.216,.599),(.216,v1),(.271,v1),(.271,.599)])
    o=mesh(name,verts,faces,walkmat,uv);o['walkable']=True;return o
def ramp(name,r):
    xy=np.array(r['xy']);z=np.array(r['z']);rows,cols=z.shape;nv=z.size;co=np.dstack([xy,z]).reshape(-1,3).tolist()+np.dstack([xy,np.full_like(z,r['ground_floor'])]).reshape(-1,3).tolist();faces=[]
    for k in range(rows-1):
        for j in range(cols-1):
            aa=k*cols+j;b=(k+1)*cols+j
            for f in [[aa,b,b+1],[aa,b+1,aa+1]]:faces.extend([f,[q+nv for q in f[::-1]]])
    ring=list(range(cols))+[k*cols+cols-1 for k in range(1,rows)]+list(range(nv-2,nv-cols-1,-1))+[k*cols for k in range(rows-2,0,-1)]
    for aa,b in zip(ring,ring[1:]+ring[:1]):faces.append([aa,b,b+nv,aa+nv])
    stations=np.linspace(0,r['length_m'],rows);uv=[(.271-.055*j/(cols-1),.7766-.1777*stations[k]/16.9048) for k in range(rows) for j in range(cols)]+[(.216,.67)]*nv;o=mesh(name,co,faces,walkmat,uv);o['walkable']=True;o['width_m']=r['width_m'];return dict({k:v for k,v in r.items() if k not in ['xy','z']},name=name)

# Replace terrain only under the new filled row foundation. The largest local
# grading depth in the selected site is a few centimetres; roads are protected.
pad=Polygon(cfg['row_site']['pad_rectangle']);ground_edits=[]
for o in [o for o in sc.objects if o.type=='MESH' and o.name.startswith('MAIN_Sculpted_Terrain_Cell_')]:
    m=o.data;m.calc_loop_triangles();co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3).astype(float);M=np.asarray(o.matrix_world);co=co@M[:3,:3].T+M[:3,3];ids=np.empty(len(m.loop_triangles)*3,np.int32);m.loop_triangles.foreach_get('vertices',ids);faces=ids.reshape(-1,3);tri=co[faces];lo=tri[:,:,:2].min(1);hi=tri[:,:,:2].max(1);b=pad.bounds;cand=np.flatnonzero((hi[:,0]>=b[0])&(lo[:,0]<=b[2])&(hi[:,1]>=b[1])&(lo[:,1]<=b[3]))
    if not len(cand):continue
    uv=None;color=None
    if m.uv_layers.active:
        uv=np.empty(len(m.loops)*2,np.float32);m.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
    if m.color_attributes.get('Color'):
        at=m.color_attributes['Color'];color=np.empty(len(m.loops)*4,np.float32);at.data.foreach_get('color',color);color=color.reshape(-1,3,4)
    selected=[];extra=[];old_material=np.array([p.material_index for p in m.polygons]);old_smooth=np.array([p.use_smooth for p in m.polygons])
    for i in cand:
        poly=Polygon(tri[i,:,:2])
        if poly.area<1e-9 or poly.intersection(pad).area<1e-9:continue
        selected.append(i);rest=poly.difference(pad)
        if rest.is_empty:continue
        attrs=np.concatenate([tri[i]]+([uv[i]] if uv is not None else [])+([color[i]] if color is not None else []),axis=1);aa=tri[i,0,:2];u=tri[i,1,:2]-aa;v=tri[i,2,:2]-aa;det=u[0]*v[1]-u[1]*v[0]
        for sub in shapely.get_parts(shapely.constrained_delaunay_triangles(rest)):
            if sub.is_empty or sub.area<1e-9:continue
            xy=np.asarray(sub.exterior.coords)[:3,:2];d=xy-aa;s=(d[:,0]*v[1]-d[:,1]*v[0])/det;t=(u[0]*d[:,1]-u[1]*d[:,0])/det;q=np.c_[1-s-t,s,t]@attrs
            if np.cross(q[1,:2]-q[0,:2],q[2,:2]-q[0,:2])<0:q=q[::-1]
            extra.append((q,int(old_material[i]),bool(old_smooth[i])))
    if not selected:continue
    kept=np.ones(len(faces),bool);kept[selected]=False;vv=co.tolist();ff=faces[kept].tolist();mm=old_material[kept].tolist();ss=old_smooth[kept].tolist();uu=uv[kept].reshape(-1,2).tolist() if uv is not None else [];cc=color[kept].reshape(-1,4).tolist() if color is not None else []
    for q,mat,smooth in extra:
        k=len(vv);vv.extend(q[:,:3].tolist());ff.append([k,k+1,k+2]);mm.append(mat);ss.append(smooth);col=3
        if uv is not None:uu.extend(q[:,col:col+2].tolist());col+=2
        if color is not None:cc.extend(q[:,col:col+4].tolist())
    new=bpy.data.meshes.new(m.name+'_SiteFit');new.from_pydata(vv,[],ff)
    for mat in m.materials:new.materials.append(mat)
    new.polygons.foreach_set('material_index',np.asarray(mm,np.int32));new.polygons.foreach_set('use_smooth',np.asarray(ss,np.bool_))
    if uv is not None:new.uv_layers.new(name='UVMap').data.foreach_set('uv',np.asarray(uu,np.float32).ravel())
    if color is not None:new.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER').data.foreach_set('color',np.asarray(cc,np.float32).ravel())
    new.update();o.data=new;o.matrix_world=Matrix.Identity(4);ground_edits.append({'object':o.name,'faces_before':len(faces),'faces_after':len(ff),'faces_cut':len(selected)})

records=[];row_site=cfg['row_site'];apt_site=cfg['apartment_site'];origin=np.array(row_site['front_origin']);u=np.array(row_site['u']);v=np.array(row_site['v']);top=row_site['foundation_top_m'];bottom=row_site['foundation_bottom_m'];xmin,xmax=cfg['row_local_x_range'];back=cfg['row_local_back_m'];rot=np.column_stack([u,v]);angle=math.atan2(u[1],u[0])
cube('Oldtown_Expanded_Row_Foundation',origin,u,v,(xmin+xmax)/2,(back-3.45)/2,(top+bottom)/2,xmax-xmin,back+3.45,top-bottom,concrete)
floor('Oldtown_Open_Row_Continuous_Floor',origin,u,v,xmin,xmax,-3.44,.15,top+.004)
floor('Oldtown_Corner_Return_Floor',origin,u,v,cfg['row_body_max_x']+.12,cfg['row_body_max_x']+2.18,-3.44,row_site['corner_depth_m']+.15,top+.006)
def place(r,site,tx):
    origin=np.array(site['front_origin']);u=np.array(site['u']);v=np.array(site['v']);rot=np.column_stack([u,v]);angle=math.atan2(u[1],u[0]);scale=r['uniform_scale'];axis=np.array(r['local_axis_scale']);top=site['foundation_top_m'];oldset=set(sc.objects);source=a.models/r['file'];bpy.ops.import_scene.gltf(filepath=str(source.resolve()));bpy.context.view_layer.update();imported=set(sc.objects)-oldset;parts=[o for o in imported if o.type=='MESH'];assert len(parts)==1
    inst=bpy.data.objects.new(r['instance_name'],None);sc.collection.objects.link(inst);inst.parent=realgroup;inst.matrix_world=Matrix.Translation((*origin,top-.008))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation((tx,0,0))@Matrix.Diagonal((*list(axis*scale),1.))@Matrix.Translation((0,-r['source_front_reference'],-r['source_floor_reference']))
    for o in imported:
        if o.parent not in imported:
            old=o.matrix_world.copy();o.parent=inst;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=old
    inst['is_building_instance']=True;inst['is_placeholder']=False;inst['source_filename']=r['file'];inst['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();inst['target_height_m']=r['target_height_m'];inst['local_axis_scale']=axis.tolist();inst['district']='OLDTOWN';inst['region']='MAIN'
    for i,o in enumerate(parts):o.name=r['instance_name']+f'_Source_Mesh_{i:02d}';o['source_filename']=r['file'];o['is_placeholder']=False
    lo,hi=np.array(r['source_bounds']);rr=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]);rr=(rr-np.array([0,r['source_front_reference']]))*(axis[:2]*scale)+np.array([tx,0]);xy=rr@rot.T+origin;rec={'instance_name':r['instance_name'],'source_filename':r['file'],'file':r['file'],'center':xy.mean(0).tolist(),'target_height_m':r['target_height_m'],'uniform_scale':scale,'local_axis_scale':axis.tolist(),'source_dimensions_m':r['source_dimensions'],'placed_dimensions_m':(np.array(r['source_dimensions'])*axis*scale).tolist(),'angle':angle,'footprint_xy':xy.tolist(),'foundation_top_m':top,'foundation_bottom_m':site['foundation_bottom_m'],'building_base_m':top-.008-r['source_floor_reference']*scale,'source_sha256':inst['source_sha256'],'source_mesh_count':len(parts),'district':'OLDTOWN','region':'MAIN'};records.append(rec);return rec
for r in cfg['models'][:6]:place(r,row_site,r['local_x_translation'])
seams=[]
for i in range(5):
    left,right=cfg['models'][i:i+2];x1=left['source_core_right']*left['uniform_scale']+left['local_x_translation'];x2=right['source_core_left']*right['uniform_scale']+right['local_x_translation'];h=min(left['target_height_m']-left['source_floor_reference']*left['uniform_scale'],right['target_height_m']-right['source_floor_reference']*right['uniform_scale'])-.3;depth=min((left['source_bounds'][1][1]-left['source_front_reference'])*left['uniform_scale']*left['local_axis_scale'][1],(right['source_bounds'][1][1]-right['source_front_reference'])*right['uniform_scale']*right['local_axis_scale'][1]);cube('Oldtown_Row_Partywall_%02d'%i,origin,u,v,(x1+x2)/2,depth/2,top+h/2,.16,depth+.12,h,plaster);seams.append({'left':left['instance_name'],'right':right['instance_name'],'overlap_m':x1-x2})
ramps=[ramp('Oldtown_Expanded_Row_Access_%02d'%i,r) for i,r in enumerate(row_site['ramps'])]
for i,r in enumerate(records):
    access=ramps[min(i//2,2)];r.update(access_start_xy=access['start_xy'],access_end_xy=access['end_xy'],access_width_m=access['width_m'],access_length_m=access['length_m'],access_maximum_grade=access['maximum_grade'],connected_arcade_row='M19_Expanded_Corner_Frontage')
apt=cfg['models'][-1];ao=np.array(apt_site['front_origin']);au=np.array(apt_site['u']);av=np.array(apt_site['v']);rect=np.array(apt_site['pad_rectangle']);local=(rect-ao)@np.column_stack([au,av]);alo=local.min(0);ahi=local.max(0);at=apt_site['foundation_top_m'];ab=apt_site['foundation_bottom_m'];cube('OLDTOWN_Apartment_11_Foundation',ao,au,av,*((alo+ahi)/2),(at+ab)/2,*(ahi-alo),at-ab,concrete);ar=place(apt,apt_site,-sum(np.array(apt['source_bounds'])[:,0])*apt['uniform_scale']/2);access=ramp('OLDTOWN_Apartment_11_Sidewalk_Access',apt_site['ramps'][0]);ar.update(access_start_xy=access['start_xy'],access_end_xy=access['end_xy'],access_width_m=3.,access_length_m=access['length_m'],access_maximum_grade=access['maximum_grade'])
removed=sorted(set(row_site['removed_placeholders']+apt_site['removed_placeholders']))
for name in removed:
    o=bpy.data.objects.get(name);assert o is not None and o.get('is_placeholder');bpy.data.objects.remove(o,do_unlink=True)
p['buildings']=[b for b in p['buildings'] if b['name'] not in removed];p['real_buildings'].extend(records);p['stats'].update(buildings=len(p['buildings'])+len(p['real_buildings']),placeholder_buildings=len(p['buildings']),real_buildings=len(p['real_buildings']),connected_arcade_source_models=6);root['real_building_count']=len(p['real_buildings']);root['placeholder_building_count']=len(p['buildings'])
row={'name':'M19_Expanded_Corner_Frontage','road':row_site['road'],'junction_node':row_site['junction_node'],'front_origin':origin.tolist(),'u':u.tolist(),'v':v.tolist(),'length_m':cfg['row_length_m'],'local_x_range':[xmin,xmax],'body_max_x':cfg['row_body_max_x'],'local_back_m':back,'pad_rectangle':row_site['pad_rectangle'],'foundation_top_m':top,'foundation_bottom_m':bottom,'open_walk_local_y_range':[-3.4,-.8],'clear_corridor_width_m':2.6,'ramps':ramps,'seams':seams,'instances':[r['instance_name'] for r in records[:6]],'added_canopy_present':False,'added_columns_present':False,'corner_instance':'OLDTOWN_Corner_Shop_10','corner_depth_scale':1.45,'corner_return_floor_width_m':2.06,'corner_depth_m':row_site['corner_depth_m']};p['connected_arcades']=row;p['oldtown_expansion']={'row':row,'apartment':ar,'removed_placeholders':removed,'ground_edits':ground_edits}
bpy.context.view_layer.update();after=fingerprint(protected);assert before==after,'Road or sidewalk geometry changed';assert not any(o.name.startswith(('Oldtown_Arcade_Continuous_Canopy','Oldtown_Arcade_Canopy_Fascia','Oldtown_Arcade_Column_')) for o in sc.objects)
chunk=json.loads(a.chunk_report.read_text())
for info in chunk:
    obs=[o for o in sc.objects if o.type=='MESH' and o.name.startswith(info['source']+'_Cell_')];info['triangles_after']=sum(len(o.data.polygons) for o in obs);info['cell_count']=len(obs)
report={'row':row,'instances':records,'removed_added_canopy_objects':removed_cover,'removed_placeholders':removed,'ground_edits':ground_edits,'maximum_local_ground_cut_m':row_site['site_cut_max_depth_m'],'road_sidewalk_geometry_unchanged':True,'protected_geometry_sha256':before,'apartment_access':access}
(a.out/'city_plan.json').write_text(json.dumps(p,separators=(',',':')));(a.out/'oldtown_expansion.json').write_text(json.dumps(report,indent=2));(a.out/'chunk_report.json').write_text(json.dumps(chunk,indent=2))
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
        try:im.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str((a.out/'huizhou_road_network.blend').resolve()),compress=True);bpy.ops.export_scene.gltf(filepath=str((a.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0; user-provided building assets.')
print('OLDTOWN_EXPANSION_COMPLETE',json.dumps({'real_buildings':len(p['real_buildings']),'removed_canopy_parts':len(removed_cover),'removed_placeholders':removed,'glb_bytes':(a.out/'huizhou_road_network.glb').stat().st_size}),flush=True)
