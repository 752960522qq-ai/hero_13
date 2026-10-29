import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P.parent/'inputs/superman.glb'));bpy.context.view_layer.update()
t=next(o for o in bpy.data.objects if o.type=='ARMATURE');meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE'for m in o.modifiers)]
cache={}
for o in meshes:
 eo=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();cache[o.name]=[v.co.copy()for v in me.vertices];eo.to_mesh_clear()
low=min((o.matrix_world@v).z for o in meshes for v in cache[o.name]);center=(t.matrix_world@t.pose.bones['pelvis_126'].matrix).translation;shift=Vector((-center.x,-center.y,-low))
for o in meshes:
 for v,co in zip(o.data.vertices,cache[o.name]):v.co=co
 o.data.update()
# Rest exactly follows the valid authored pose, including the original root offset.
bpy.context.view_layer.objects.active=t;t.select_set(True);bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
for o in [t]+meshes:
 mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw;o.matrix_world.translation+=shift
for o in list(bpy.data.objects):
 if o not in [t]+meshes:bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.update();t.animation_data_clear()
# Apply identity world transforms consistently on both skeleton and body.
bpy.ops.object.select_all(action='DESELECT')
for o in [t]+meshes:o.select_set(True)
bpy.context.view_layer.objects.active=t;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'superman_clean.blend'),compress=True)
(P/'clean_rest.json').write_text(json.dumps({n:list(map(list,t.matrix_world@b.matrix_local))for n,b in t.data.bones.items()},indent=2))
print('CLEAN_READY',flush=True)
