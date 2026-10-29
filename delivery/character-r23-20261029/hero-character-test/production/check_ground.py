import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;result={}
for id,folder,name in [('double_stars','double_anim','double_stars_animated.blend'),('superman','superman_anim','superman_animated.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(P/folder/name));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');sc=bpy.context.scene
 for track in t.animation_data.nla_tracks:track.mute=True
 meshes=[o for o in bpy.data.objects if o.type=='MESH'];feet=[]
 for o in meshes:
  points=np.array([list(o.matrix_world@v.co)for v in o.data.vertices]);
  if points[:,2].max()<.3:feet.append(o)
 if not feet:feet=meshes
 ground={}
 for label in ['Idle','Walk','Run']:
  a=bpy.data.actions.get(label);t.animation_data.action=a;start,end=map(int,a.frame_range);mins=[]
  for f in range(start,end+1):
   sc.frame_set(f);low=1e9
   for ob in feet:
    eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();coords=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',coords);coords=coords.reshape((-1,3));low=min(low,float((coords@np.array(eo.matrix_world.to_3x3()).T+np.array(eo.matrix_world.translation))[:,2].min()));eo.to_mesh_clear()
   mins.append(low)
  ground[label]=-min(mins);print('GROUND',id,label,ground[label],flush=True)
 result[id]=ground
(P/'ground_final.json').write_text(json.dumps(result,indent=2))
manifest=json.loads((P.parent/'dist/assets/characters.json').read_text())
for id,ground in result.items():manifest[id]['ground']=ground
(P.parent/'dist/assets/characters.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
