import bpy,json
bpy.ops.import_scene.gltf(filepath='/workspace/recovered-xiaqing-site/dist/assets/vest_xiaqing.glb')
t=next(o for o in bpy.data.objects if o.type=='ARMATURE')
print('ARM',t.name,list(t.matrix_world),[(a.name,list(a.frame_range)) for a in bpy.data.actions]);print('REST',[(b.name,list(b.head_local),list(b.tail_local)) for b in t.data.bones][:25]);print('fps',bpy.context.scene.render.fps)
bpy.ops.import_scene.fbx(filepath='/workspace/attachments/f530cd62-7738-475e-af8a-298e0c8123fd/Jump.fbx')
s=[o for o in bpy.data.objects if o.type=='ARMATURE' and o!=t][0]
print('SRC',s.name,list(s.matrix_world),[(a.name,list(a.frame_range)) for a in bpy.data.actions][-3:]);print('SRCR',[(b.name,list(b.head_local)) for b in s.data.bones][:10]);print('fps',bpy.context.scene.render.fps)
