"""Place two user-provided CBD buildings, preserving their proportions and UVs.

Run on the road-only .blend with its matching city plan. The supplied site
manifest pins the two replacement lots; each source model is imported once.
"""
from pathlib import Path
import argparse,hashlib,json,math,sys
import bpy,numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from city_surface_sampling import HeightField

ap=argparse.ArgumentParser();ap.add_argument('--base-blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--models',type=Path,required=True);ap.add_argument('--sites',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.base_blend.resolve()));sc=bpy.context.scene;bpy.context.view_layer.update()
plan=json.loads(args.plan.read_text());config=json.loads(args.sites.read_text())
root=bpy.data.objects['Huizhou_City_4000m_Road_Blockout']
def below(o,name):
    while o:
        if o.name==name:return True
        o=o.parent
    return False
def fingerprint(objects):
    h=hashlib.sha256()
    for o in sorted(objects,key=lambda o:o.name):
        h.update(o.name.encode());a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
        ids=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',ids);h.update(ids.tobytes());h.update(np.array(o.matrix_world,np.float32).tobytes())
        if o.data.uv_layers.active:
            uv=np.empty(len(o.data.loops)*2,np.float32);o.data.uv_layers.active.data.foreach_get('uv',uv);h.update(uv.tobytes())
    return h.hexdigest()
protected=[o for o in sc.objects if o.type=='MESH' and any(below(o,n) for n in ['01_TERRAIN','03_ROAD_NETWORK','06_SIDEWALKS'])]
before=fingerprint(protected)
def bvh(objects):
    v=[];f=[]
    for o in objects:
        offset=len(v);v.extend(o.matrix_world@q.co for q in o.data.vertices);o.data.calc_loop_triangles();f.extend(tuple(offset+i for i in t.vertices) for t in o.data.loop_triangles)
    return BVHTree.FromPolygons(v,f,all_triangles=True,epsilon=.001)
lands=[o for o in sc.objects if o.type=='MESH' and 'Sculpted_Terrain' in o.name]
terrain=HeightField(lands);walk=HeightField([o for o in sc.objects if o.type=='MESH' and below(o,'06_SIDEWALKS')])
def cast(tree,xy):
    if isinstance(tree,HeightField):return tree.height(xy)
    hit,*_=tree.ray_cast(Vector((float(xy[0]),float(xy[1]),500)),Vector((0,0,-1)),1000)
    return None if hit is None else float(hit.z)
terrain_tri=[]
for o in lands:
    if 'MAIN' not in o.name:continue
    vv=np.array([o.matrix_world@v.co for v in o.data.vertices]);o.data.calc_loop_triangles();ff=np.array([t.vertices[:] for t in o.data.loop_triangles],np.int32);terrain_tri.append(vv[ff])
terrain_tri=np.vstack(terrain_tri);tri_lo=terrain_tri[:,:,:2].min(1);tri_hi=terrain_tri[:,:,:2].max(1)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def clip_to_rect(triangle,rectangle):
    points=triangle.copy()
    for a,b in zip(rectangle,np.roll(rectangle,-1,0)):
        if len(points)<3:return np.empty((0,3))
        direction=b-a;out=[]
        for p,q in zip(points,np.roll(points,-1,0)):
            dp=cross(direction,p[:2]-a);dq=cross(direction,q[:2]-a)
            if dp>=-1e-8:out.append(p)
            if (dp>=0)!=(dq>=0):out.append(p+(q-p)*dp/(dp-dq))
        points=np.array(out)
    return points
def terrain_extents(rectangle):
    lo=rectangle.min(0);hi=rectangle.max(0);ids=np.where(np.all(tri_hi>=lo,1)&np.all(tri_lo<=hi,1))[0];heights=[]
    for i in ids:
        clipped=clip_to_rect(terrain_tri[i],rectangle)
        if len(clipped):heights.extend(clipped[:,2].tolist())
    assert heights,'No ground under selected CBD lot'
    return min(heights),max(heights)
def empty(name,parent):
    o=bpy.data.objects.new(name,None);sc.collection.objects.link(o);o.parent=parent;return o
buildings_group=empty('07_CBD_REAL_BUILDINGS',root);site_group=empty('08_CBD_SITE_ADAPTATION',root)
def mesh(name,v,f,mat,parent,uv_by_face=None):
    data=bpy.data.meshes.new(name);data.from_pydata(v,[],f);data.materials.append(mat);data.update();obj=bpy.data.objects.new(name,data);sc.collection.objects.link(obj);obj.parent=parent
    if uv_by_face:
        layer=data.uv_layers.new(name='UVMap')
        for poly,uvs in zip(data.polygons,uv_by_face):
            for li,uv in zip(poly.loop_indices,uvs):layer.data[li].uv=uv
    return obj
mat=bpy.data.materials.new('CBD_Level_Foundation_Concrete');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.42,.43,.41,1);bs.inputs['Roughness'].default_value=.9
walkmat=bpy.data.materials['Road_Modular_Original_Atlas']
records=[];removed=[]
for entry in config['instances']:
    name=entry['instance_name'];assert name not in bpy.data.objects,'Building already placed'
    old=bpy.data.objects.get(entry['placeholder']);assert old is not None and old.get('is_placeholder'),entry['placeholder']
    source=args.models/entry['file'];before_set=set(sc.objects);bpy.ops.import_scene.gltf(filepath=str(source.resolve()));bpy.context.view_layer.update()
    imported=set(sc.objects)-before_set;source_meshes=[o for o in imported if o.type=='MESH'];assert source_meshes
    points=np.vstack([np.array([o.matrix_world@v.co for v in o.data.vertices]) for o in source_meshes]);lo=points.min(0);hi=points.max(0);dims=hi-lo
    scale=entry['target_height_m']/dims[2];size=dims*scale;angle=float(entry['angle']);center=np.array(entry['center']);c,s=math.cos(angle),math.sin(angle);rot=np.array([[c,-s],[s,c]])
    front=rot@np.array([0.,-1.]);across=np.array([-front[1],front[0]])
    pad_size=size[:2]+2;local=np.array([[-pad_size[0]/2,-pad_size[1]/2],[pad_size[0]/2,-pad_size[1]/2],[pad_size[0]/2,pad_size[1]/2],[-pad_size[0]/2,pad_size[1]/2]])
    rectangle=local@rot.T+center;ground_min,ground_max=terrain_extents(rectangle)
    # Dense ray checks also catch narrow terrain fragments near the new apron
    # edge. Keep 80 mm of cover above their highest point, rather than relying
    # only on clipped triangle extrema at a lot boundary.
    uu=rectangle[1]-rectangle[0];vv=rectangle[3]-rectangle[0];sampled=[]
    for u0 in np.linspace(0,1,int(math.ceil(np.linalg.norm(uu)/.25))+1):
        for v0 in np.linspace(0,1,int(math.ceil(np.linalg.norm(vv)/.25))+1):
            z0=cast(terrain,rectangle[0]+u0*uu+v0*vv)
            assert z0 is not None,'New apron crosses an existing terrain cut'
            sampled.append(z0)
    ground_min=min(ground_min,min(sampled));ground_max=max(ground_max,max(sampled));pad_top=ground_max+.08;bottom=ground_min-.20
    # The original ground apron sinks 25 mm into a level, fully buried footing.
    body_base=pad_top-.025
    instance=empty(name,buildings_group)
    instance.matrix_world=Matrix.Translation((float(center[0]),float(center[1]),body_base))@Matrix.Rotation(angle,4,'Z')@Matrix.Scale(scale,4)@Matrix.Translation((-float((lo[0]+hi[0])/2),-float((lo[1]+hi[1])/2),-float(lo[2])))
    for o in imported:
        if o.parent not in imported:
            original=o.matrix_world.copy();o.parent=instance;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=original
    instance['is_building_instance']=True;instance['is_placeholder']=False;instance['source_filename']=entry['source_filename'];instance['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();instance['district']='CBD';instance['region']='MAIN';instance['target_height_m']=entry['target_height_m'];instance['uniform_scale']=scale;instance['replaces_placeholder']=entry['placeholder']
    for i,o in enumerate(source_meshes):o.name=name+f'_Source_Mesh_{i:02}';o['source_filename']=entry['source_filename'];o['is_placeholder']=False
    vertices=[[float(x),float(y),pad_top] for x,y in rectangle]+[[float(x),float(y),bottom] for x,y in rectangle]
    faces=[[0,1,2,3],[7,6,5,4]]+[[i,(i+1)%4,(i+1)%4+4,i+4] for i in range(4)]
    pad=mesh(name+'_Level_Foundation',vertices,faces,mat,site_group);pad['purpose']='Level foundation, buried below existing terrain; supports original model ground apron'
    # Connect the preserved entrance apron to the existing modular sidewalk.
    start=center+front*(pad_size[1]/2-.15);road=np.array(entry['road_nearest']);end=road-front*(entry['road_halfwidth']-1.4)
    L=float(np.linalg.norm(end-start));direction=(end-start)/L;across=np.array([-direction[1],direction[0]]);assert L>3
    width=3.;offsets=np.linspace(-width/2,width/2,7)
    end_xy=end[None,:]+offsets[:,None]*across
    end_walk=np.array([cast(walk,p) for p in end_xy],float);assert np.isfinite(end_walk).all(),'Access must meet the original sidewalk'
    end_center=float(end_walk.mean());crossfall=end_walk-end_center
    stations=np.unique(np.r_[np.linspace(0,L,int(math.ceil(L/.75))+1),np.arange(16.9048,L,16.9048)])
    xy=start[None,None,:]+stations[:,None,None]/L*(end-start)[None,None,:]+offsets[None,:,None]*across[None,None,:]
    surface_ground=np.array([[cast(terrain,p) for p in row] for row in xy],dtype=float)
    fraction=stations/L;roll=fraction[:,None]*crossfall[None,:]
    h=(pad_top+.004)*(1-fraction)+(end_center+.006)*fraction
    required=np.max(np.where(np.isfinite(surface_ground),surface_ground-roll+.025,-1e6),axis=1);h=np.maximum(h,required)
    for k in range(1,len(h)):h[k]=max(h[k],h[k-1]-.05*(stations[k]-stations[k-1]))
    for k in range(len(h)-2,-1,-1):h[k]=max(h[k],h[k+1]-.05*(stations[k+1]-stations[k]))
    assert abs(h[0]-pad_top-.004)<.012 and abs(h[-1]-end_center-.006)<.012,'Selected lot needs a longer accessible approach'
    z=h[:,None]+roll;nv=z.size;floor=float(np.nanmin(surface_ground))-.20
    top=np.dstack([xy,z]);v=top.reshape(-1,3).tolist()+np.dstack([xy,np.full_like(z,floor)]).reshape(-1,3).tolist();faces=[];uvs=[];cols=len(offsets)
    for row in range(len(stations)-1):
        tile=math.floor(((stations[row]+stations[row+1])/2)/16.9048)
        for col in range(cols-1):
            a=row*cols+col;b=(row+1)*cols+col
            for face in [[a,b,b+1],[a,b+1,a+1]]:
                faces.append(face);uvs.append([(.271-.055*(i%cols)/(cols-1),.7766-.1777*(stations[i//cols]-tile*16.9048)/16.9048) for i in face])
                faces.append([i+nv for i in face[::-1]]);uvs.append([(.216,.67)]*3)
    ring=list(range(cols))+[r*cols+cols-1 for r in range(1,len(stations))]+list(range(nv-2,nv-cols-1,-1))+[r*cols for r in range(len(stations)-2,0,-1)]
    for a,b in zip(ring,ring[1:]+ring[:1]):faces.append([a,b,b+nv,a+nv]);uvs.append([(.216,.67),(.216,.69),(.216,.69),(.216,.67)])
    ramp=mesh(name+'_Sidewalk_Access',v,faces,walkmat,site_group,uvs);ramp['walkable']=True;ramp['source_material']='Road Modular original sidewalk atlas';ramp['maximum_longitudinal_grade']=float(np.max(np.abs(np.diff(z,axis=0))/np.diff(stations)[:,None]))
    removed.append(old.name);bpy.data.objects.remove(old,do_unlink=True)
    record=dict(entry);record.update(uniform_scale=float(scale),source_dimensions_m=dims.tolist(),placed_dimensions_m=size.tolist(),foundation_top_m=pad_top,foundation_bottom_m=bottom,building_base_m=body_base,terrain_min_m=ground_min,terrain_max_m=ground_max,foundation_terrain_range_m=ground_max-ground_min,footprint_xy=rectangle.tolist(),source_sha256=instance['source_sha256'],source_mesh_count=len(source_meshes),access_start_xy=start.tolist(),access_end_xy=end.tolist(),access_length_m=L,access_width_m=width,access_maximum_grade=ramp['maximum_longitudinal_grade'],access_end_lip_m=float(np.max(np.abs(z[-1]-end_walk))),access_start_lip_m=float(abs(h[0]-pad_top)),access_end_samples_xyz=np.c_[end_xy,z[-1]].tolist())
    records.append(record);print('CBD_BUILDING_PLACED',json.dumps(record),flush=True)
bpy.context.view_layer.update();after=fingerprint(protected);assert before==after,'Road, sidewalk or terrain geometry changed unexpectedly'
root['description']='Three-island city with supplied Road Modular network, two user-provided CBD building assets, and replaceable box buildings.';root['placeholder_building_count']=len(plan['buildings'])-2;root['real_building_count']=2
plan['buildings']=[b for b in plan['buildings'] if b['name'] not in removed];plan['real_buildings']=records;plan['stats']['placeholder_buildings']=len(plan['buildings']);plan['stats']['real_buildings']=2;plan['stats']['buildings']=len(plan['buildings'])+2
report={'instances':records,'removed_placeholders':removed,'model_instance_count':2,'original_geometry_sha256_before':before,'original_geometry_sha256_after':after,'original_road_sidewalk_terrain_unchanged':before==after,'placeholder_buildings':len(plan['buildings']),'building_total':len(plan['buildings'])+2}
(args.out/'cbd_placements.json').write_text(json.dumps(report,indent=2));(args.out/'city_plan.json').write_text(json.dumps(plan,separators=(',',':')))
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>2 and not im.packed_file:
        try:im.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'huizhou_road_network.blend').resolve()),compress=True)
bpy.ops.export_scene.gltf(filepath=str((args.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_materials='EXPORT',export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. '+plan['sources']['road']['url']+' Two user-provided building assets added with preserved source proportions and UVs.')
print('CBD_EXPORT_COMPLETE',json.dumps({'bytes':(args.out/'huizhou_road_network.glb').stat().st_size,'instances':2,'placeholder_count':len(plan['buildings'])}),flush=True)
