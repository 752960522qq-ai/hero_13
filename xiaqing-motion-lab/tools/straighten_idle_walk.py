"""v4.6 modest elbow extension, preserving shoulder motion and wrist articulation."""
import bpy,math,json,zipfile
from pathlib import Path
from mathutils import Matrix,Quaternion
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_v45.blend');r=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
rest={b.name:b.matrix_local.copy() for b in r.data.bones};report=[]
for name in ['Idle','Walk']:
 a=bpy.data.actions[name];r.animation_data.action=a;stats=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update()
  for side in ['Left','Right']:
   arm=r.pose.bones[side+'Arm'];fore=r.pose.bones[side+'ForeArm'];hand=r.pose.bones[side+'Hand'];helper=r.pose.bones[side+'Elbow']
   upper=(arm.tail-arm.head).normalized();lower=(fore.tail-fore.head).normalized();before=upper.angle(lower)
   # Keep a soft bend; only reduce existing flexion, never hyperextend.
   desired=max(math.radians(4),before*.70) if before>math.radians(4) else before
   fraction=(before-desired)/before if before>1e-7 else 0
   turn=Quaternion().slerp(lower.rotation_difference(upper),fraction)
   pivot=fore.head.copy();fm=fore.matrix.copy();hm=hand.matrix.copy()
   fore.matrix=Matrix.Translation(pivot)@(turn@fm.to_quaternion()).to_matrix().to_4x4();bpy.context.view_layer.update()
   hand.matrix=Matrix.Translation(pivot+turn@(hm.translation-pivot))@(turn@hm.to_quaternion()).to_matrix().to_4x4();bpy.context.view_layer.update()
   qa=arm.matrix.to_quaternion()@rest[arm.name].to_quaternion().inverted();qf=fore.matrix.to_quaternion()@rest[fore.name].to_quaternion().inverted()
   helper.matrix=Matrix.Translation(pivot)@(qa.slerp(qf,.5)@rest[helper.name].to_quaternion()).to_matrix().to_4x4();bpy.context.view_layer.update()
   after=(arm.tail-arm.head).angle(fore.tail-fore.head);assert after<=before+.001
   assert (hand.head-fore.tail).length<1e-5
   for p in [fore,hand,helper]:
    for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
   stats.append((math.degrees(before),math.degrees(after)))
 report.append({'clip':name,'mean_elbow_bend_before':sum(x[0] for x in stats)/len(stats),'mean_elbow_bend_after':sum(x[1] for x in stats)/len(stats)})
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='4.6'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
(OUT/'elbow-extension-report.json').write_text(json.dumps(report,indent=2));print('ELBOW_EXTENSION',report)
