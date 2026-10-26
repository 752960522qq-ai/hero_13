"""Matched, small visual review of the two requested pose edits."""
import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
after=P/'vest_xiaqing_r7.blend'
if not after.exists():after=P/'pose_adjustments/pose_candidate.blend'
for tag,file in [('before',P.parent/'refinement-r6/vest_xiaqing_r6.blend'),('after',after)]:
 bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
 for ob in bpy.context.scene.objects:
  if ob.get('comparison_only'):ob.hide_render=True
 for t in r.animation_data.nla_tracks:t.mute=True
 r.data.pose_position='POSE';s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=900;s.render.resolution_y=1100;s.render.resolution_percentage=100
 for label,phase,frac,target,scale,offset in [('Idle_full','Idle',.35,(0,0,.82),1.97,(0,-3,.02)),('Idle_late','Idle',.70,(0,0,.82),1.97,(0,-3,.02)),('Run_front','Run',.35,(0,-.06,1.30),.85,(0,-3,.02)),('Run_profile','Run',.70,(0,-.08,1.43),.60,(3,0,.01))]:
  a=next(a for a in bpy.data.actions if a.name.startswith(phase));r.animation_data.action=a;f=float(a.frame_range[0]+frac*(a.frame_range[1]-a.frame_range[0]));s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();target=Vector(target);c=s.camera;c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=scale;s.render.filepath=str(P/(tag+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
print('POSE_COMPARISON_SAVED')
