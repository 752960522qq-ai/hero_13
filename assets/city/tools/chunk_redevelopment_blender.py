"""Spatially partition city surfaces while preserving triangles and UV seams.

Faces are assigned intact to a 250 m cell by centroid, so shared boundaries
cannot introduce geometry holes. Each chunk keeps the same material and UVs.
"""
from pathlib import Path
import argparse,hashlib,json,sys
import bpy,numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cell-size',type=float,default=250)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()));sc=bpy.context.scene;bpy.context.view_layer.update()
plan=json.loads(args.plan.read_text())
targets=[
 'MAIN_Road_Modular_Repaired','EAST_Road_Modular_Repaired','WEST_Road_Modular_Repaired','BRIDGES_Road_Modular_Repaired',
 'Continuous_Pavement_Repaired','MAIN_Sidewalk_Modular_Continuous','EAST_Sidewalk_Modular_Continuous',
 'WEST_Sidewalk_Modular_Continuous','BRIDGES_Sidewalk_Modular_Continuous','Sidewalk_Continuous_Transition_Base',
 'MAIN_Sculpted_Terrain','EAST_Sculpted_Terrain','WEST_Sculpted_Terrain','CBD_Conforming_Concrete_Paving',
 'Junction_Repairs_Asphalt','Junction_Repairs_Sidewalk_OriginalAtlas','Junction_Repairs_Original_Road_Kit'
]
report=[]
for name in targets:
    obj=bpy.data.objects.get(name)
    if obj is None or obj.type!='MESH':continue
    old=obj.data;nv=len(old.vertices);nf=len(old.polygons)
    co=np.empty(nv*3,np.float32);old.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    indices=np.empty(len(old.loops),np.int32);old.loops.foreach_get('vertex_index',indices)
    totals=np.empty(nf,np.int32);old.polygons.foreach_get('loop_total',totals);assert np.all(totals==3),name
    faces=indices.reshape(-1,3)
    uv=None
    if old.uv_layers.active:
        uv=np.empty(len(old.loops)*2,np.float32);old.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,3,2)
    color=None
    if old.color_attributes.get('Color'):
        attr=old.color_attributes['Color'];assert attr.domain=='CORNER'
        color=np.empty(len(old.loops)*4,np.float32);attr.data.foreach_get('color',color);color=color.reshape(-1,3,4)
    material=np.empty(nf,np.int32);old.polygons.foreach_get('material_index',material)
    smooth=np.empty(nf,np.bool_);old.polygons.foreach_get('use_smooth',smooth)
    centroids=co[faces].mean(1);xy=np.floor(centroids[:,:2]/args.cell_size).astype(np.int32)
    cells,labels=np.unique(xy,axis=0,return_inverse=True)
    parent=obj.parent;transform=obj.matrix_basis.copy();props={k:obj[k] for k in obj.keys()}
    obj.name=name+'_UnchunkedSource'
    holder=bpy.data.objects.new(name,None);sc.collection.objects.link(holder);holder.parent=parent;holder.matrix_basis=transform
    for k,v in props.items():holder[k]=v
    holder['chunk_size_m']=args.cell_size;holder['chunk_count']=len(cells)
    count=0;signature=hashlib.sha256()
    for i,cell in enumerate(cells):
        select=np.flatnonzero(labels==i)
        if not len(select):continue
        local_faces=faces[select];used,inverse=np.unique(local_faces.ravel(),return_inverse=True)
        local_co=co[used];local_faces=inverse.reshape(-1,3).astype(np.int32)
        chunkname=name+'_Cell_%+03d_%+03d'%(int(cell[0]),int(cell[1]))
        m=bpy.data.meshes.new(chunkname)
        m.vertices.add(len(local_co));m.vertices.foreach_set('co',np.ascontiguousarray(local_co).ravel())
        m.loops.add(len(local_faces)*3);m.loops.foreach_set('vertex_index',local_faces.ravel())
        m.polygons.add(len(local_faces));m.polygons.foreach_set('loop_start',np.arange(len(local_faces),dtype=np.int32)*3)
        m.polygons.foreach_set('loop_total',np.full(len(local_faces),3,np.int32))
        m.polygons.foreach_set('material_index',np.ascontiguousarray(material[select],np.int32))
        m.polygons.foreach_set('use_smooth',np.ascontiguousarray(smooth[select],np.bool_))
        for mat in old.materials:m.materials.append(mat)
        if uv is not None:
            layer=m.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.ascontiguousarray(uv[select]).ravel())
        if color is not None:
            layer=m.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
            layer.data.foreach_set('color',np.ascontiguousarray(color[select]).ravel())
        m.update()
        chunk=bpy.data.objects.new(chunkname,m);sc.collection.objects.link(chunk);chunk.parent=holder
        chunk['source_object']=name;chunk['cell_x']=int(cell[0]);chunk['cell_y']=int(cell[1])
        for k,v in props.items():chunk[k]=v
        # Verify each chunk preserves the original ordered per-corner positions
        # and UV data exactly; partitioning does not simplify geometry.
        assert np.array_equal(local_co[local_faces],co[faces[select]])
        signature.update(np.ascontiguousarray(local_co[local_faces]).tobytes())
        if uv is not None:signature.update(np.ascontiguousarray(uv[select]).tobytes())
        count+=len(local_faces)
    assert count==nf
    bpy.data.objects.remove(obj,do_unlink=True)
    if old.users==0:bpy.data.meshes.remove(old)
    report.append({'source':name,'triangles_before':nf,'triangles_after':count,'cell_count':len(cells),'sha256':signature.hexdigest()})
    print('CHUNKED',json.dumps(report[-1]),flush=True)
plan['stats']['streaming_cell_size_m']=args.cell_size
plan['stats']['chunked_surface_objects']=sum(x['cell_count'] for x in report)
(args.out/'city_plan.json').write_text(json.dumps(plan,separators=(',',':')))
(args.out/'chunk_report.json').write_text(json.dumps(report,indent=2))
bpy.context.view_layer.update()
for image in bpy.data.images:
    if image.type=='IMAGE' and image.size[0]>2 and not image.packed_file:
        try:image.pack()
        except RuntimeError:pass
bpy.ops.wm.save_as_mainfile(filepath=str((args.out/'huizhou_road_network.blend').resolve()),compress=True)
bpy.ops.export_scene.gltf(filepath=str((args.out/'huizhou_road_network.glb').resolve()),export_format='GLB',export_yup=True,export_extras=True,
    export_animations=False,export_cameras=False,export_lights=False,export_materials='EXPORT',export_image_format='AUTO',
    export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. '+plan['sources']['road']['url']+' Four user-provided building assets.')
print('CHUNK_EXPORT_COMPLETE',json.dumps({'chunks':sum(x['cell_count'] for x in report),'glb_bytes':(args.out/'huizhou_road_network.glb').stat().st_size}),flush=True)
