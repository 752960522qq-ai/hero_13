"""Export 16 land districts and two shared models in identical world coordinates.

Static surfaces are partitioned by intact triangles. Buildings and their site
adaptation stay together; no face is duplicated or dropped at a boundary.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,sys,time
import bpy,numpy as np
from mathutils import Matrix
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expectations',type=Path,required=True);ap.add_argument('--deps',type=Path)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
import shapely
from shapely.geometry import Polygon
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.view_layer.update();sc=bpy.context.scene;p=json.loads(a.plan.read_text());a.out.mkdir(parents=True,exist_ok=True);a.expectations.mkdir(parents=True,exist_ok=True)
names=['01_main_sw','02_main_south_west_center','03_main_south_east_center','04_main_se','05_main_nw','06_main_north_west_center','07_main_north_east_center','08_main_ne','09_west_sw','10_west_se','11_west_nw','12_west_ne','13_east_sw','14_east_se','15_east_nw','16_east_ne','17_shared_bridges','18_shared_water']
labels=['主岛西南','主岛南部偏西','主岛南部偏东／老城区街角','主岛东南','主岛西北','主岛北部偏西／CBD原建筑','主岛北部偏东／CBD','主岛东北','西岛西南','西岛东南','西岛西北','西岛东北／湖区','东岛西南','东岛东南','东岛西北','东岛东北／港区','公共桥梁及引道','公共海面与湖水']
roots=[];district_objects=[[] for _ in names];expected=[{} for _ in names];records=[[] for _ in names];source_audit=[];total_triangles=0
for i,n in enumerate(names):
    r=bpy.data.objects.new(n,None);sc.collection.objects.link(r);r['district_id']=i+1;r['district_name']=labels[i];r['coordinate_space']='Blender world, Z up, metres';roots.append(r)
coasts={k:Polygon(v) for k,v in p['coasts'].items()};real={b['instance_name']:b for b in p['real_buildings']};boxes={b['name']:b for b in p['buildings']};row=p['connected_arcades'];rowcenter=np.asarray(row['front_origin'])
def zones(xy,region):
    xy=np.asarray(xy);x=xy[:,0];y=xy[:,1]
    if region=='MAIN':return np.searchsorted(np.array([-500.,0.,500.]),x,side='right')+(y>=620)*4
    if region=='WEST':return 8+(x>=-950)+(y>=-720)*2
    if region=='EAST':return 12+(x>=750)+(y>=-800)*2
    raise ValueError(region)
def classify(xy,hint=None):
    if hint in coasts:return zones(xy,hint).astype(np.int32)
    xy=np.asarray(xy);result=np.full(len(xy),16,np.int32)
    for region,poly in coasts.items():
        mask=shapely.intersects_xy(poly,xy[:,0],xy[:,1]);result[mask]=zones(xy[mask],region)
    return result
def ancestry(o):
    out=[]
    while o:out.append(o.name);o=o.parent
    return out
def instance(o):
    while o:
        if o.get('is_building_instance'):return o.name
        o=o.parent
    return None
def extra_plain(v):
    if hasattr(v,'to_list'):return v.to_list()
    if hasattr(v,'to_dict'):return v.to_dict()
    return v
original=[o for o in sc.objects if o.type=='MESH'];started=time.time()
for oi,obj in enumerate(original):
    m=obj.data;m.calc_loop_triangles();n=len(m.loop_triangles)
    if not n:continue
    vertices=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',vertices);vertices=vertices.reshape(-1,3).astype(np.float64);M=np.asarray(obj.matrix_world,np.float64);world=vertices@M[:3,:3].T+M[:3,3]
    tri=np.empty(n*3,np.int32);m.loop_triangles.foreach_get('vertices',tri);tri=tri.reshape(-1,3);loops=np.empty(n*3,np.int32);m.loop_triangles.foreach_get('loops',loops);loops=loops.reshape(-1,3);polygon=np.empty(n,np.int32);m.loop_triangles.foreach_get('polygon_index',polygon)
    chain=ancestry(obj);inst=instance(obj);hint=None;atomic=None;fixed=None
    if '02_WATER' in chain:fixed=17
    elif '04_BRIDGE_STRUCTURES' in chain or obj.name.startswith(('BRIDGES_','WATER_BRIDGES_','Bridge_Approach_')):fixed=16
    elif inst in real:
        r=real[inst];atomic=int(zones(np.array([r['center']]),r.get('region','MAIN'))[0])
    else:
        for name,r in real.items():
            if obj.name.startswith(name+'_'):
                atomic=int(zones(np.array([r['center']]),r.get('region','MAIN'))[0]);break
        if atomic is None and obj.name.startswith(('Oldtown_Expanded_Row_','Oldtown_Open_Row_','Oldtown_Corner_Return_','Oldtown_Row_Partywall_')):atomic=int(zones(rowcenter[None,:],'MAIN')[0])
        if atomic is None and obj.name in boxes:
            r=boxes[obj.name];atomic=int(zones(np.array([r['center']]),r['region'])[0])
        if atomic is None and n<=24:atomic=int(classify(world.mean(0)[None,:2])[0])
    for region in ['MAIN','WEST','EAST']:
        if obj.name.startswith(region+'_'):hint=region;break
    if obj.name.startswith(('CBD_','Junction_Repair','Main_Southern_','Oldtown_Residential_','Oldtown_Apartment_')):hint='MAIN'
    if m.attributes.get('source_building_index'):
        lot_ids=np.empty(len(m.polygons),np.int32);m.attributes['source_building_index'].data.foreach_get('value',lot_ids)
        lot_districts=np.array([int(zones(np.array([b['center']]),b['region'])[0]) for b in p['buildings']],np.int32)
        assignment=lot_districts[lot_ids[polygon]]
    elif fixed is not None:assignment=np.full(n,fixed,np.int32)
    elif atomic is not None:assignment=np.full(n,atomic,np.int32)
    else:assignment=classify(world[tri].mean(1)[:,:2],hint)
    assert len(assignment)==n and assignment.min()>=0 and assignment.max()<18
    mats=np.empty(len(m.polygons),np.int32);m.polygons.foreach_get('material_index',mats);smooth=np.empty(len(m.polygons),np.bool_);m.polygons.foreach_get('use_smooth',smooth)
    uv_layers=[]
    for layer in m.uv_layers:
        ar=np.empty(len(m.loops)*2,np.float32);layer.data.foreach_get('uv',ar);uv_layers.append((layer.name,ar.reshape(-1,2)))
    colors=[]
    for attr in m.color_attributes:
        ar=np.empty(len(attr.data)*4,np.float32);attr.data.foreach_get('color',ar);colors.append((attr.name,attr.domain,attr.data_type,ar.reshape(-1,4)))
    normals=np.empty(len(m.corner_normals)*3,np.float32);m.corner_normals.foreach_get('vector',normals);normals=normals.reshape(-1,3).astype(np.float64);N=np.linalg.inv(M[:3,:3]);normals=normals@N;length=np.linalg.norm(normals,axis=1);normals/=np.maximum(length[:,None],1e-20)
    counts={}
    for zone in np.unique(assignment):
        take=np.flatnonzero(assignment==zone);chosen=tri[take];used,inverse=np.unique(chosen.ravel(),return_inverse=True);co=world[used].astype(np.float32);ff=inverse.reshape(-1,3);nm=f'D{zone+1:02d}_'+obj.name
        mesh=bpy.data.meshes.new(nm);mesh.vertices.add(len(co));mesh.vertices.foreach_set('co',co.ravel());mesh.loops.add(len(ff)*3);mesh.loops.foreach_set('vertex_index',ff.astype(np.int32).ravel());mesh.polygons.add(len(ff));mesh.polygons.foreach_set('loop_start',np.arange(len(ff),dtype=np.int32)*3);mesh.polygons.foreach_set('loop_total',np.full(len(ff),3,np.int32));mesh.polygons.foreach_set('material_index',mats[polygon[take]]);mesh.polygons.foreach_set('use_smooth',smooth[polygon[take]])
        for material in m.materials:mesh.materials.append(material)
        for name,ar in uv_layers:mesh.uv_layers.new(name=name).data.foreach_set('uv',np.ascontiguousarray(ar[loops[take]],np.float32).ravel())
        for name,domain,kind,ar in colors:
            values=ar[loops[take]] if domain=='CORNER' else ar[tri[take]];mesh.color_attributes.new(name=name,type=kind,domain='CORNER').data.foreach_set('color',np.ascontiguousarray(values,np.float32).ravel())
        mesh.update();mesh.normals_split_custom_set(np.ascontiguousarray(normals[loops[take]].reshape(-1,3),np.float32));clone=bpy.data.objects.new(nm,mesh);sc.collection.objects.link(clone);clone.parent=roots[int(zone)];clone.matrix_world=Matrix.Identity(4);clone['source_object']=obj.name;clone['district_id']=int(zone)+1
        for k,value in obj.items():
            if k not in ['_RNA_UI']:
                try:clone[k]=extra_plain(value)
                except (TypeError,ValueError):pass
        if inst in real:
            clone['source_instance']=inst;clone['source_filename']=real[inst].get('source_filename',real[inst].get('file',''));clone['is_building_instance']=True
        district_objects[int(zone)].append(clone);expected[int(zone)][clone.name]=co;counts[str(int(zone)+1)]=len(take);records[int(zone)].append({'object':clone.name,'source_object':obj.name,'triangles':len(take),'vertices':len(co),'source_instance':inst,'bounds_blender':[co.min(0).tolist(),co.max(0).tolist()]})
    assert sum(counts.values())==n;source_audit.append({'source':obj.name,'triangles':n,'assigned':counts});total_triangles+=n
    if oi%200==0:print('DISTRICT_PARTITION',oi,len(original),obj.name,flush=True)
manifest={'schema':'hero13.city.districts.v1','units':'metres','blender_axes':'X east, Y north, Z up','glb_axes':'X east, Y up, -Z north','placement':'Every GLB is already in city world coordinates. Keep imported root transforms at identity; do not center or add offsets.','common_models':[17,18],'land_district_count':16,'file_count':18,'source_mesh_count':len(source_audit),'source_triangle_count':total_triangles,'districts':[]}
for i,n in enumerate(names):
    assert district_objects[i],('empty district',n)
    bpy.ops.object.select_all(action='DESELECT');roots[i].select_set(True)
    for o in district_objects[i]:o.select_set(True)
    bpy.context.view_layer.objects.active=roots[i];dest=a.out/(n+'.glb');print('DISTRICT_EXPORT_START',n,len(district_objects[i]),flush=True)
    bpy.ops.export_scene.gltf(filepath=str(dest.resolve()),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. Building assets provided by the user. District coordinates are world space.')
    bounds=np.array([r['bounds_blender'] for r in records[i]]);lo=bounds[:,0].min(0);hi=bounds[:,1].max(0);inst=sorted({r['source_instance'] for r in records[i] if r['source_instance']});entry={'id':i+1,'name':labels[i],'file':dest.name,'file_size_bytes':dest.stat().st_size,'mesh_objects':len(records[i]),'triangles':sum(r['triangles'] for r in records[i]),'bounds_blender':[lo.tolist(),hi.tolist()],'bounds_glb':[[float(lo[0]),float(lo[2]),float(-hi[1])],[float(hi[0]),float(hi[2]),float(-lo[1])]],'source_building_instances':inst,'root_translation':[0,0,0],'common':i>=16};manifest['districts'].append(entry)
    np.savez_compressed(a.expectations/(n+'.npz'),**expected[i]);print('DISTRICT_EXPORT_DONE',n,dest.stat().st_size,flush=True)
assert sum(r['triangles'] for r in manifest['districts'])==total_triangles
(a.out/'districts_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));audit={'sources':source_audit,'district_objects':records,'triangle_assignment_complete':True,'source_triangles':total_triangles,'district_triangles':sum(r['triangles'] for r in manifest['districts'])}
with gzip.GzipFile(filename=str(a.out/'partition_audit.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(audit,separators=(',',':')).encode())
print('DISTRICTS_COMPLETE',json.dumps({'files':18,'triangles':total_triangles,'seconds':time.time()-started}),flush=True)
