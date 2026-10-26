import bpy,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent.parent/'refinement-r6/vest_xiaqing_r6.blend'))
r=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
out={}
for label in ['Rest','Run']:
 if label=='Rest':r.animation_data.action=None;r.data.pose_position='REST';fracs=[0]
 else:r.data.pose_position='POSE';a=next(a for a in bpy.data.actions if a.name.startswith(label));r.animation_data.action=a;fracs=[0,.35,.7]
 out[label]=[]
 for frac in fracs:
  frame=0 if label=='Rest' else float(a.frame_range[0]+frac*(a.frame_range[1]-a.frame_range[0]));s.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
  heads={n:list(r.pose.bones[n].head) for n in ['spine_2','neck_0','neck_1','head']};v=r.pose.bones['head'].head-r.pose.bones['neck_0'].head
  out[label].append({'fraction':frac,'heads':heads,'forward_lean_degrees':math.degrees(math.atan2(-v.y,v.z))})
(P/'neck_before.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
