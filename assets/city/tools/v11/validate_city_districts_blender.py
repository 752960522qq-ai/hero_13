"""Reimport every exported district and compare it with the assigned geometry."""
from pathlib import Path
import argparse,gzip,hashlib,json,struct,sys
import bpy,numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--districts',type=Path,required=True);ap.add_argument('--expectations',type=Path,required=True);ap.add_argument('--master-glb',type=Path,required=True);ap.add_argument('--deps',type=Path);ap.add_argument('--report',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.deps:sys.path.insert(0,str(a.deps.resolve()))
from scipy.spatial import cKDTree
manifest=json.loads((a.districts/'districts_manifest.json').read_text());audit=json.loads(gzip.decompress((a.districts/'partition_audit.json.gz').read_bytes()))
def image_hashes(path):
    with path.open('rb') as f:
        magic,version,total,n,kind=struct.unpack('<4sIIII',f.read(20));assert magic==b'glTF' and version==2;meta=json.loads(f.read(n));size,kind=struct.unpack('<II',f.read(8));data=f.read(size)
    hashes=[]
    for im in meta.get('images',[]):
        assert 'bufferView' in im,'External image URI in a district GLB';v=meta['bufferViews'][im['bufferView']];i=v.get('byteOffset',0);hashes.append(hashlib.sha256(data[i:i+v['byteLength']]).hexdigest())
    return hashes
master_images=set(image_hashes(a.master_glb));assert len(manifest['districts'])==18;assert audit['triangle_assignment_complete'];assert sum(r['triangles'] for r in audit['sources'])==manifest['source_triangle_count']
for src in audit['sources']:assert sum(src['assigned'].values())==src['triangles']
checks=[];all_instances=[];total=0;largest_error=0
for i,d in enumerate(manifest['districts']):
    file=a.districts/d['file'];hashes=image_hashes(file);assert all(h in master_images for h in hashes)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(file.resolve()));bpy.context.view_layer.update();objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];expected=np.load(a.expectations/(Path(d['file']).stem+'.npz'));records={r['object']:r for r in audit['district_objects'][i]};assert len(objects)==len(records)
    maxerror=0;vertices=0;tris=0
    for obj in objects:
        assert obj.name in records,obj.name;record=records[obj.name];m=obj.data;m.calc_loop_triangles();assert len(m.loop_triangles)==record['triangles'];tris+=len(m.loop_triangles)
        co=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',co);co=co.reshape(-1,3).astype(float);M=np.asarray(obj.matrix_world);co=co@M[:3,:3].T+M[:3,3];target=expected[obj.name];tree=cKDTree(target);dist,_=tree.query(co,k=1,workers=1);err=float(dist.max(initial=0));maxerror=max(maxerror,err);assert err<.001,(obj.name,err);vertices+=len(co)
        if record['source_instance']:all_instances.append(record['source_instance']);assert obj.get('source_instance')==record['source_instance']
    assert tris==d['triangles'];total+=tris;largest_error=max(largest_error,maxerror);check={'id':d['id'],'file':d['file'],'meshes':len(objects),'triangles':tris,'vertices_checked':vertices,'maximum_world_position_error_m':maxerror,'embedded_images_checked':len(hashes),'reimport_passed':True};checks.append(check);print('DISTRICT_REIMPORT_CHECK',json.dumps(check),flush=True)
assert total==manifest['source_triangle_count'];expected_instances={name for d in manifest['districts'] for name in d['source_building_instances']};assert len(all_instances)==len(expected_instances) and set(all_instances)==expected_instances
report={'district_glbs_reimported':18,'land_districts':16,'shared_models':2,'source_triangle_count':manifest['source_triangle_count'],'district_triangle_count':total,'triangle_assignment_complete':True,'source_building_instances_checked':all_instances,'maximum_world_position_error_m':largest_error,'texture_images_match_master':True,'shared_coordinate_space':True,'districts':checks,'validation_passed':True,'limits':'Static geometry validation. Runtime loading, navigation and vehicle collisions are not configured by this export.'}
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('DISTRICTS_VALIDATION_COMPLETE',json.dumps({'files':18,'triangles':total,'max_error_m':largest_error}),flush=True)
