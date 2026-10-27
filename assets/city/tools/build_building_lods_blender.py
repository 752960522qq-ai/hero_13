"""Export optional reduced-mesh building assets; the city keeps the originals.

These are authoring candidates, not automatic runtime LOD. Inspect them in the
target engine before assigning distance thresholds.
"""
from pathlib import Path
import argparse,hashlib,json,struct,sys
import bpy,numpy as np

ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,action='append',required=True)
ap.add_argument('--out',type=Path,required=True);args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
args.out.mkdir(parents=True,exist_ok=True)
def images(path):
    with path.open('rb') as f:
        magic,version,total,n,kind=struct.unpack('<4sIIII',f.read(20));assert magic==b'glTF' and version==2
        meta=json.loads(f.read(n));length,kind=struct.unpack('<II',f.read(8));blob=f.read(length)
    return [hashlib.sha256(blob[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]).hexdigest()
            for im in meta.get('images',[]) if 'bufferView' in im for v in [meta['bufferViews'][im['bufferView']]]]
def world_bounds(objects):
    coordinates=[]
    for obj in objects:
        a=np.empty(len(obj.data.vertices)*3,np.float32);obj.data.vertices.foreach_get('co',a);a=a.reshape(-1,3)
        m=np.asarray(obj.matrix_world);coordinates.append(a@m[:3,:3].T+m[:3,3])
    a=np.concatenate(coordinates);return np.vstack([a.min(0),a.max(0)])
records=[]
for source in args.source:
    source_images=sorted(images(source));assert source_images
    for label,ratio in [('lod1',.6),('lod2',.3)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
        objs=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert objs and all(o.data.uv_layers.active for o in objs)
        before_bounds=world_bounds(objs);before=sum(len(o.data.polygons) for o in objs)
        for obj in objs:
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
            mod=obj.modifiers.new('LOD_Decimate','DECIMATE');mod.decimate_type='COLLAPSE';mod.ratio=ratio
            mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        after=sum(len(o.data.polygons) for o in objs);after_bounds=world_bounds(objs)
        delta=float(np.max(np.abs(before_bounds-after_bounds)));height=float(np.max(before_bounds[1]-before_bounds[0]))
        assert after<before and delta/max(height,1e-6)<.025,(source.name,label,delta,height)
        dest=args.out/(source.stem+'_'+label+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(dest.resolve()),export_format='GLB',export_animations=False,export_image_format='AUTO')
        matching=sorted(images(dest))==source_images;assert matching,(source.name,label,'texture bytes changed')
        rec={'source':source.name,'file':dest.name,'ratio_requested':ratio,'triangles_before':before,'triangles_after':after,
             'relative_max_bounds_shift':delta/max(height,1e-6),'source_image_bytes_unchanged':matching}
        records.append(rec);print('BUILDING_LOD',json.dumps(rec),flush=True)
(args.out/'lod_validation.json').write_text(json.dumps({'automatic_switching_in_main_glb':False,'assets':records},indent=2))
print('LOD_COMPLETE',len(records),flush=True)
