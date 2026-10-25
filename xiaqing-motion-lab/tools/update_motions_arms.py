import bpy,math,json,zipfile
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
BASE='/tmp/xiaqing_v42.blend';OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/'
# Read FBX world-space pose deltas; both source rigs use an anatomical T-pose.
sources={}
for label,file in [('Idle','girl_Idle.fbx'),('Walk','girl Walk.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(Path(__file__).resolve().parent.parent/'source-motions'/file.replace(' ','_')))
 a=next(o for o in bpy.data.objects if o.type=='ARMATURE');world=a.matrix_world.copy();rest={b.name.split(':')[-1]:world@b.matrix_local for b in a.data.bones};frames=[]
 start,end=map(int,a.animation_data.action.frame_range)
 for f in range(start,end+1):
  bpy.context.scene.frame_set(f);frames.append({p.name.split(':')[-1]:world@p.matrix for p in a.pose.bones})
 sources[label]=(rest,frames)
bpy.ops.wm.open_mainfile(filepath=BASE);r=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
names=[b.name for b in r.data.bones];rest={b.name:b.matrix_local.copy() for b in r.data.bones};motions={}
for action in bpy.data.actions:
 if action.name in sources:continue
 r.animation_data.action=action;frames=[]
 for f in range(int(action.frame_range[0]),int(action.frame_range[1])+1):
  s.frame_set(f);frames.append({p.name:p.matrix.copy() for p in r.pose.bones})
 motions[action.name]=frames
for label,(src,frames) in sources.items():
 result=[];scale=rest['Hips'].translation.z/src['Hips'].translation.z
 for frame in frames:
  pose={}
  for n in names:
   q=frame[n].to_quaternion()@src[n].to_quaternion().inverted()@rest[n].to_quaternion()
   parent=r.data.bones[n].parent
   head=(pose[parent.name]@rest[parent.name].inverted()@rest[n].translation) if parent else rest[n].translation+Vector((0,0,(frame[n].translation.z-src[n].translation.z)*scale))
   pose[n]=Matrix.Translation(head)@q.to_matrix().to_4x4()
  result.append(pose)
 motions[label]=result
r.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.context.view_layer.objects.active=r;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for side in ['Left','Right']:
 b=r.data.edit_bones.new(side+'Elbow');arm=r.data.edit_bones[side+'Arm'];fore=r.data.edit_bones[side+'ForeArm'];b.head=fore.head;b.tail=b.head+(arm.tail-arm.head).normalized()*.025;b.align_roll(arm.z_axis);b.parent=arm
bpy.ops.object.mode_set(mode='OBJECT');r.animation_data_create()
for side in ['Left','Right']:o.vertex_groups.new(name=side+'Elbow')
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
mats=[set() for v in o.data.vertices]
for p in o.data.polygons:
 idx=int(o.data.materials[p.material_index].name.split('_')[2])
 for i in p.vertices:mats[i].add(idx)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
modified=[]
for v in o.data.vertices:
 if not mats[v.index]&{5,6} or not .078<abs(v.co.x)<.30:continue
 side='Left' if v.co.x>0 else 'Right';arm=r.data.bones[side+'Arm'];axis=(arm.tail_local-arm.head_local).normalized();d=(v.co-arm.tail_local).dot(axis)
 if abs(v.co.x)<.125:
  t=smooth(.078,.125,abs(v.co.x));w={'Spine2':1-t,side+'Arm':t}
 elif d<=0:
  t=smooth(-.036,0,d);w={side+'Arm':1-t,side+'Elbow':t}
 else:
  t=smooth(0,.036,d);w={side+'Elbow':1-t,side+'ForeArm':t}
 for g in o.vertex_groups:g.remove([v.index])
 for n,value in w.items():
  if value>1e-8:o.vertex_groups[n].add([v.index],value,'REPLACE')
 modified.append(v.index)
shoes=[i for i,m in enumerate(mats) if m&{7,8}]
for label,frames in motions.items():
 action=bpy.data.actions.new(label);r.animation_data.action=action
 for f,pose in enumerate(frames,1):
  s.frame_set(f)
  # Remove relative forearm axial twist while preserving the original bend direction.
  for side in ['Left','Right']:
   an=side+'Arm';fn=side+'ForeArm';hn=side+'Hand';en=side+'Elbow'
   qa=pose[an].to_quaternion()@rest[an].to_quaternion().inverted()
   qf=pose[fn].to_quaternion()@rest[fn].to_quaternion().inverted()
   axis=(r.data.bones[fn].tail_local-r.data.bones[fn].head_local).normalized()
   swing=(qa@axis).rotation_difference(qf@axis);newf=swing@qa
   pose[fn]=Matrix.Translation(pose[fn].translation)@(newf@rest[fn].to_quaternion()).to_matrix().to_4x4()
   hhead=pose[fn]@rest[fn].inverted()@rest[hn].translation
   if label!='HandTest':pose[hn]=Matrix.Translation(hhead)@(newf@rest[hn].to_quaternion()).to_matrix().to_4x4()
   pose[en]=Matrix.Translation(pose[fn].translation)@(qa.slerp(newf,.5)@rest[en].to_quaternion()).to_matrix().to_4x4()
  # Parent order, including the new helper bones.
  ordered=sorted(r.pose.bones,key=lambda p:len(p.parent_recursive))
  for p in ordered:p.matrix=pose[p.name];bpy.context.view_layer.update()
  # Source root horizontal drift is removed; feet remain on the test ground.
  if label in sources:
   ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());lo=min(ev.data.vertices[i].co.z for i in shoes);p=r.pose.bones['Hips'];p.location+=p.bone.matrix_local.to_quaternion().inverted()@Vector((0,0,-lo));bpy.context.view_layer.update()
  for p in r.pose.bones:
   p.rotation_mode='QUATERNION'
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
 r.animation_data.action=None;t=r.animation_data.nla_tracks.new();t.name=label;t.strips.new(label,1,action);t.mute=True
 print('BAKED',label,len(frames),flush=True)
checks=[]
for label,f in [('Idle',126),('Walk',18),('Run',9),('Run',19)]:
 r.animation_data.action=bpy.data.actions[label];s.frame_set(f);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 assert all(all(math.isfinite(c) for c in ev.data.vertices[i].co) for i in modified)
 checks.append({'clip':label,'frame':f})
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='4.3'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT+'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'xiaqing_trousers_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
with open(OUT+'motion-arm-fix-report.json','w') as f:json.dump({'version':'4.3','bones':24,'sources':{'Idle':'girl_Idle.fbx','Walk':'girl Walk.fbx','Run':'previous Run, arm correction only'},'arm_vertices':len(modified),'checks':checks},f,indent=2)
