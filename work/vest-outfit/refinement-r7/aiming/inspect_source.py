import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/workspace/attachments/0da78e4f-3ef1-4be8-b585-a3f8108f6acc/Rifle Aiming Idle.fbx')
d={'objects':[],'actions':[],'fps':bpy.context.scene.render.fps}
for o in bpy.context.scene.objects:
 row={'name':o.name,'type':o.type,'matrix':list(map(list,o.matrix_world))}
 if o.type=='ARMATURE':row['bones']={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None,'matrix':list(map(list,b.matrix_local))} for b in o.data.bones}
 if o.type=='MESH':row['vertices']=len(o.data.vertices)
 d['objects'].append(row)
for a in bpy.data.actions:d['actions'].append({'name':a.name,'range':list(a.frame_range),'curves':len(a.fcurves)})
(P/'source_inspection.json').write_text(json.dumps(d,indent=2));print(json.dumps({k:v for k,v in d.items() if k!='objects'}));print([(o['name'],o['type']) for o in d['objects']])
bpy.ops.wm.save_as_mainfile(filepath=str(P/'source_inspect.blend'),compress=True)
