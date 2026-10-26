"""Record the new stationary clip's fixed preview placement, preserving its motion."""
import bpy,numpy as np,json
from pathlib import Path
P=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'vest_xiaqing_r7.blend'));r=bpy.data.objects['Xiaqing_Native_Rig'];r.data.pose_position='POSE';a=bpy.data.actions.get('Aim');r.animation_data.action=a
for t in r.animation_data.nla_tracks:t.mute=True
rows=[]
for frac in [0,.25,.5,.75,1]:
 f=float(a.frame_range[0]+frac*(a.frame_range[1]-a.frame_range[0]));bpy.context.scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();z=[]
 for name in ['Shoe_L','Shoe_R']:
  ev=bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);z.append(float(v.reshape(-1,3)[:,2].min()));ev.to_mesh_clear()
 rows.append({'fraction':frac,'shoe_min_z':z})
out={'samples':rows,'fixed_preview_offset_m':-.0035-min(min(row['shoe_min_z']) for row in rows)};(P/'aiming/preview_ground.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
