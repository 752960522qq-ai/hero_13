import bpy,json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath='/workspace/attachments/ff4adad4-1835-458d-abce-de913ca05dd1/superman.glb')
for o in bpy.data.objects:
 if o.type in ['MESH','ARMATURE']:
  print('OBJ',o.name,o.type,'P',o.parent.name if o.parent else None,'MAT',list(o.matrix_world.translation),list(o.matrix_world.to_scale()))
  if o.type=='MESH':
   pts=[o.matrix_world@v.co for v in o.data.vertices];print('bounds',[min(v[i]for v in pts)for i in range(3)],[max(v[i]for v in pts)for i in range(3)],'mods',[(m.type,m.object.name if m.type=='ARMATURE'and m.object else None)for m in o.modifiers]);print('vg',[(g.name,g.index)for g in o.vertex_groups][:5])
   e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();pts=[e.matrix_world@v.co for v in me.vertices];print('evalbounds',[min(v[i]for v in pts)for i in range(3)],[max(v[i]for v in pts)for i in range(3)]);e.to_mesh_clear()
