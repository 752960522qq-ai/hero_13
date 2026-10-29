import bpy,sys,json,math
from pathlib import Path
from mathutils import Matrix,Vector
import numpy as np
R=Path(__file__).resolve().parents[1];bpy.ops.wm.read_factory_settings(use_empty=True)
for f in sorted((R/'baseline').glob('*.glb')):bpy.ops.import_scene.gltf(filepath=str(f))
bpy.context.view_layer.update();sc=bpy.context.scene;rec=[]
for o in list(sc.objects):
 if o.type=='MESH':
  o.data=o.data.copy();o.data.transform(o.matrix_world);o.parent=None;o.matrix_world=Matrix.Identity(4);o.data.update();co=np.array([v.co[:] for v in o.data.vertices]);rec.append({'name':o.name,'extras':dict(o.items()),'vertices':len(co),'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'bounds':[co.min(0).tolist(),co.max(0).tolist()]})
for o in list(sc.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
(R/'inspection').mkdir(exist_ok=True);(R/'model').mkdir(exist_ok=True);(R/'inspection/objects.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/base_v16_partial.blend'),compress=True)
