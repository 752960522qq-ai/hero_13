"""Construct fitted modular garment and bind it in Blender, preserving UVs."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parent.parent
config=json.loads((ROOT/'dist/assets/wardrobe/shirt_trouser.json').read_text());data=np.load('/tmp/shirt-fit.npz')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=config['source']);source=next(o for o in bpy.context.scene.objects if o.type=='MESH');material=source.data.materials[0]
matched=Path('/tmp/shirt-matched.jpg')
if matched.exists():
 for node in material.node_tree.nodes:
  if node.type=='TEX_IMAGE':node.image=bpy.data.images.load(str(matched),check_existing=True);node.image.pack()
# Original source remains in source-models; rebuild only selected clothing faces.
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
arm=bpy.data.armatures.new('ShirtTrouserRig');rig=bpy.data.objects.new('ShirtTrouserRig',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,w in zip(config['boneNames'],data['bone_world']):
 bone=arm.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,0,.03);bone.matrix=C@Matrix(w.tolist())@C.inverted();bone.length=.03
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
pos=data['positions'][:,[0,2,1]].copy();pos[:,1]*=-1;faces=data['faces'];uv=data['uv'];joints=data['joints'];weights=data['weights']
normal=np.zeros_like(pos);fn=np.cross(pos[faces[:,1]]-pos[faces[:,0]],pos[faces[:,2]]-pos[faces[:,0]])
for k in range(3):np.add.at(normal,faces[:,k],fn)
_,weld=np.unique(np.round(pos,6),axis=0,return_inverse=True);summed=np.zeros((weld.max()+1,3));np.add.at(summed,weld,normal);normal=summed[weld];normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-10)
for slot in np.unique(data['face_slots']):
 fs=faces[data['face_slots']==slot];ids,remap=np.unique(fs,return_inverse=True);mesh=bpy.data.meshes.new(config['slots'][slot]['id']);mesh.from_pydata(pos[ids].tolist(),[],remap.reshape(-1,3).tolist());mesh.update();obj=bpy.data.objects.new('Suit_'+config['slots'][slot]['id'],mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material);layer=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  poly.use_smooth=True
  for li in poly.loop_indices:
   u=uv[ids[mesh.loops[li].vertex_index]];layer.data[li].uv=(float(u[0]),float(1-u[1]))
 mesh.normals_split_custom_set_from_vertices(normal[ids].tolist())
 for boneid in np.unique(joints[ids]):
  group=obj.vertex_groups.new(name=config['boneNames'][boneid]);rows,cols=np.where(joints[ids]==boneid)
  for row,col in zip(rows,cols):
   weight=float(weights[ids[row],col])
   if weight>1e-7:group.add([int(row)],weight,'REPLACE')
 mod=obj.modifiers.new('NativeCharacterBinding','ARMATURE');mod.object=rig;obj.parent=rig
 obj['bodyModule']=config['slots'][slot]['id'];obj.select_set(True)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
out=ROOT/'qa/shirt-trouser';out.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'shirt_trouser_fitted.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'dist/assets/wardrobe/shirt_trouser_rigged.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_yup=True,export_extras=True)
print('GARMENT_EXPORTED')
