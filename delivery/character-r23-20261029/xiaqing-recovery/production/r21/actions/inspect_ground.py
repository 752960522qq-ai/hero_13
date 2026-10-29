import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/workspace/recovered-xiaqing-site/dist/assets/vest_xiaqing.glb')
for o in bpy.context.scene.objects:
 if o.type=='MESH':print(o.name,len(o.data.vertices),[(m.type,getattr(m,'object',None).name if getattr(m,'object',None) else '') for m in o.modifiers],min((o.matrix_world@v.co).z for v in o.data.vertices))
