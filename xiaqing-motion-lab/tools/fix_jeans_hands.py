"""Localized v4.1 wrist weights and wrist-test correction; no topology changes."""
import bpy, math, json, zipfile
from mathutils import Quaternion
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend')
r=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
fixed=[];before=0
for v in o.data.vertices:
 x,y,z=v.co;a=abs(x)
 if a<.26 or not .69<z<.82:continue
 side='Left' if x>0 else 'Right'
 before+=sum(g.weight for g in v.groups if o.vertex_groups[g.group].name not in (side+'ForeArm',side+'Hand'))>1e-6
 # Project the wrist blend along the forearm, keeping the distal palm rigid.
 fore=r.data.bones[side+'ForeArm'];axis=(fore.tail_local-fore.head_local).normalized()
 d=(v.co-fore.tail_local).dot(axis);t=max(0,min(1,(d+.015)/.03));t=t*t*(3-2*t)
 for g in o.vertex_groups:g.remove([v.index])
 if t<1:o.vertex_groups[side+'ForeArm'].add([v.index],1-t,'REPLACE')
 if t>0:o.vertex_groups[side+'Hand'].add([v.index],t,'REPLACE')
 fixed.append(v.index)
# Use the target wrist's local axes instead of the previous character's global hand rotation.
for action in bpy.data.actions:
 r.animation_data.action=action
 for f in range(int(action.frame_range[0]),int(action.frame_range[1])+1):
  s.frame_set(f)
  for side,sign in [('Left',1),('Right',-1)]:
   p=r.pose.bones[side+'Hand'];p.rotation_mode='QUATERNION'
   phase=2*math.pi*(f-1)/90
   p.rotation_quaternion=(Quaternion((1,0,0),math.radians(18)*math.sin(phase))@Quaternion((0,0,1),sign*math.radians(10)*math.sin(phase*2))) if action.name=='HandTest' else Quaternion()
   p.location=(0,0,0);p.scale=(1,1,1)
   for prop in ['rotation_quaternion','location','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
checks=[]
for name,f in [('Idle',1),('ArmRaise',61),('HandTest',23)]:
 r.animation_data.action=bpy.data.actions[name];s.frame_set(f);bpy.context.view_layer.update()
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 assert all(all(math.isfinite(c) for c in ev.data.vertices[i].co) for i in fixed)
 for i in fixed:
  v=o.data.vertices[i];side='Left' if v.co.x>0 else 'Right'
  assert all(o.vertex_groups[g.group].name in [side+'ForeArm',side+'Hand'] for g in v.groups)
  assert abs(sum(g.weight for g in v.groups)-1)<1e-6
 checks.append({'clip':name,'frame':f,'passed':True})
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='4.1'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
out='/workspace/sites/xiaqing-motion-lab/dist/assets/'
with zipfile.ZipFile(out+'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=out+'xiaqing_trousers_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
report={'version':'4.1','modified_vertices':len(fixed),'vertices_with_removed_torso_weights':before,'targeted_pose_checks':checks,'topology_changed':False}
with open(out+'hand-fix-report.json','w') as f:json.dump(report,f,indent=2)
print('HAND_FIX',report)
