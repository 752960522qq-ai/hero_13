import bpy,json,numpy as np
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath='/workspace/attachments/8a7efad6-6849-42a3-830a-eb33a604c716/double stars have head.glb')
for o in bpy.data.objects:
 if o.type=='MESH':
  a=np.array([list(o.matrix_world@v.co)for v in o.data.vertices])*1.713
  print(o.name,len(a),'lo',np.round(a.min(0),3),'hi',np.round(a.max(0),3),'center',np.round(np.median(a,0),3))
