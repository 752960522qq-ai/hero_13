"""Restore source shoulder-elbow-wrist directions and hand rotation for Idle/Run."""
import bpy,math,json,zipfile
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets';sources={}
for label,filename in [('Idle','girl_Idle.fbx'),('Walk','girl_Walk.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(ROOT/'source-motions'/filename));r=next(o for o in bpy.data.objects if o.type=='ARMATURE');world=r.matrix_world.copy();rest={b.name.split(':')[-1]:world@b.matrix_local for b in r.data.bones}
 frames=[]
 for f in range(int(r.animation_data.action.frame_range[0]),int(r.animation_data.action.frame_range[1])+1):
  bpy.context.scene.frame_set(f);frames.append({p.name.split(':')[-1]:world@p.matrix for p in r.pose.bones})
 sources[label]=(rest,frames)
bpy.ops.wm.open_mainfile(filepath='/tmp/natural-arms/xiaqing_trousers.blend');r=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True

bpy.context.view_layer.objects.active=r;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);r.animation_data.action=None
bpy.ops.object.mode_set(mode='EDIT')
for side in ['Left','Right']:
 hand=r.data.edit_bones[side+'Hand'];axis=(hand.tail-hand.head).normalized();b=r.data.edit_bones.new(side+'FingerCurl');b.head=hand.head+axis*.032;b.tail=b.head+axis*.035;b.align_roll(hand.z_axis);b.parent=hand
bpy.ops.object.mode_set(mode='OBJECT')
matids=[set() for v in o.data.vertices]
for p in o.data.polygons:
 idx=int(o.data.materials[p.material_index].name.split('_')[2])
 for i in p.vertices:matids[i].add(idx)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for side in ['Left','Right']:
 g=o.vertex_groups.new(name=side+'FingerCurl');h=o.vertex_groups[side+'Hand'];b=r.data.bones[side+'Hand'];axis=(b.tail_local-b.head_local).normalized()
 for v in o.data.vertices:
  if (10 if side=='Left' else 9) not in matids[v.index]:continue
  d=(v.co-b.head_local).dot(axis);w=smooth(.024,.047,d)
  old=next((x.weight for x in v.groups if x.group==h.index),0);weight=w*old
  if weight>0:g.add([v.index],weight,'REPLACE');h.add([v.index],old-weight,'REPLACE')

rest={b.name:b.matrix_local.copy() for b in r.data.bones};report=[]
for label,(src,frames) in sources.items():
 action=bpy.data.actions[label];r.animation_data.action=action;maxangle=0
 for f,frame in enumerate(frames,1):
  s.frame_set(f);bpy.context.view_layer.update()
  for side in ['Left','Right']:
   for suffix in ['Arm','ForeArm','Hand']:
    n=side+suffix;p=r.pose.bones[n]
    # Align neutral segment axes before applying the source's complete rotation,
    # including wrist articulation and forearm pronation.
    targetaxis=rest[n].to_quaternion()@Vector((0,1,0));sourceaxis=src[n].to_quaternion()@Vector((0,1,0))
    align=targetaxis.rotation_difference(sourceaxis)
    delta=frame[n].to_quaternion()@src[n].to_quaternion().inverted()
    q=delta@align@rest[n].to_quaternion()
    head=p.parent.matrix@p.parent.bone.matrix_local.inverted()@p.bone.head_local
    p.matrix=Matrix.Translation(head)@q.to_matrix().to_4x4();bpy.context.view_layer.update()
    v=p.matrix.to_quaternion()@Vector((0,1,0));ref=frame[n].to_quaternion()@Vector((0,1,0));maxangle=max(maxangle,v.angle(ref))
    for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=n)
   # Reduce the source's lateral arm spread for this character's wider shoulders.
   pivot=r.pose.bones[side+'Arm'].matrix.translation.copy()
   relax=Quaternion((0,1,0),(1 if side=='Left' else -1)*math.radians(5 if label=='Walk' else 2))
   adjusted={side+x:Matrix.Translation(pivot+relax@(r.pose.bones[side+x].matrix.translation-pivot))@(relax@r.pose.bones[side+x].matrix.to_quaternion()).to_matrix().to_4x4() for x in ['Arm','ForeArm','Hand']}
   for n,m in adjusted.items():
    p=r.pose.bones[n];p.matrix=m;bpy.context.view_layer.update()
    for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=n)
   an=side+'Arm';fn=side+'ForeArm';en=side+'Elbow'
   qa=r.pose.bones[an].matrix.to_quaternion()@rest[an].to_quaternion().inverted();qf=r.pose.bones[fn].matrix.to_quaternion()@rest[fn].to_quaternion().inverted()
   p=r.pose.bones[en];p.matrix=Matrix.Translation(r.pose.bones[fn].matrix.translation)@(qa.slerp(qf,.5)@rest[en].to_quaternion()).to_matrix().to_4x4();bpy.context.view_layer.update()
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=en)
 report.append({'clip':label,'frames':len(frames),'source_direction_error_before_relaxation_degrees':math.degrees(maxangle)})
 assert maxangle<.002
for action in bpy.data.actions:
 r.animation_data.action=action
 for f in range(int(action.frame_range[0]),int(action.frame_range[1])+1):
  s.frame_set(f)
  for side in ['Left','Right']:
   p=r.pose.bones[side+'FingerCurl'];p.rotation_mode='QUATERNION'
   angle=(17 if action.name=='Idle' else 12) if action.name in ['Idle','Walk'] else 0
   b=p.bone;forward=(b.tail_local-b.head_local).normalized();axis=b.matrix_local.to_quaternion().inverted()@forward.cross(Vector((0,0,-1))).normalized();p.rotation_quaternion=Quaternion(axis,math.radians(angle));p.keyframe_insert('rotation_quaternion',frame=f,group=p.name)
# Required focused deformation checks, not a full mesh sweep.
for label,f in [('Idle',1),('Idle',126),('Walk',9),('Walk',27)]:
 r.animation_data.action=bpy.data.actions[label];s.frame_set(f);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 for v in ev.data.vertices:
  assert all(math.isfinite(c) for c in v.co)
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='4.5'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
(OUT/'natural-idle-walk-report.json').write_text(json.dumps(report,indent=2));print('SOURCE_MATCH',report,flush=True)
