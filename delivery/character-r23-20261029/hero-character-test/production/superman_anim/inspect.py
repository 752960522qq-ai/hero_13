import bpy,json
bpy.ops.import_scene.gltf(filepath='/workspace/attachments/ff4adad4-1835-458d-abce-de913ca05dd1/superman.glb')
for o in bpy.data.objects:
 if o.type in ['MESH','ARMATURE']:print(o.name,o.type,'matrix',list(map(list,o.matrix_world)), 'parent',o.parent.name if o.parent else None)
t=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.view_layer.update();print('pelvis',list(t.data.bones['pelvis_126'].head_local),list(t.matrix_world@t.data.bones['pelvis_126'].head_local));print('mat',list(map(list,t.matrix_world)))
for n in ['GLTF_created_0_rootJoint','root_130','pelvis_126']:
 p=t.pose.bones.get(n)
 if p:print(n,'rest',list(p.bone.matrix_local.translation),'pose',list(p.matrix.translation),'basis',list(p.matrix_basis.translation),list(p.rotation_quaternion))
for o in bpy.data.objects:
 if o.name=='Object_7':
  eo=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();print('meshbbox',min((o.matrix_world@v.co).x for v in o.data.vertices),min((o.matrix_world@v.co).x for v in me.vertices));eo.to_mesh_clear()
