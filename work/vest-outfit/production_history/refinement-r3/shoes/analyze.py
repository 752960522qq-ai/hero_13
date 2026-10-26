import bpy,bmesh,numpy as np,json
from pathlib import Path
from mathutils import Vector
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
P=Path(__file__).resolve().parent;BASE=P.parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(BASE/'vest_source.glb'));o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,.847),plane_no=(0,0,1),clear_outer=True);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free()
v=np.array([x.co[:] for x in o.data.vertices]);e=np.array([x.vertices[:] for x in o.data.edges]);A=csr_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(v),len(v)));n,lab=connected_components(A);comps=[]
for k in range(n):
 ids=np.where(lab==k)[0];p=v[ids];
 if p[:,2].min()<.16:comps.append({'label':k,'n':len(ids),'min':p.min(0).tolist(),'max':p.max(0).tolist()})
print('vertices',len(v),'components',n,comps);print('mats',[(m.name,len(m.node_tree.nodes)) for m in o.data.materials])
for im in bpy.data.images:
 if im.size[0]>1: im.filepath_raw=str(P/'source_texture.png');im.file_format='PNG';im.save()
np.savez(P/'source_mesh.npz',v=v,e=e,component=lab)
(P/'source_components.json').write_text(json.dumps(comps,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(P/'source_processed.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_cavity=False;s.display.shading.show_shadows=False;s.render.resolution_x=1200;s.render.resolution_y=900
c=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.22
for tag,offset in [('side',(1,0,.03)),('front',(0,-1,.06)),('top',(.1,-.2,1))]:
 target=Vector((.064,.045,.065));c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(P/f'source_{tag}.png');bpy.ops.render.render(write_still=True)
