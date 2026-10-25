"""Restore source shoulder-elbow-wrist directions and hand rotation for Idle/Run."""
import bpy,math,json,zipfile
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets';sources={}
for label,filename in [('Idle','girl_Idle.fbx'),('Run','Running.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(ROOT/'source-motions'/filename));r=next(o for o in bpy.data.objects if o.type=='ARMATURE');world=r.matrix_world.copy();rest={b.name.split(':')[-1]:world@b.matrix_local for b in r.data.bones}
 frames=[]
 for f in range(int(r.animation_data.action.frame_range[0]),int(r.animation_data.action.frame_range[1])+1):
  bpy.context.scene.frame_set(f);frames.append({p.name.split(':')[-1]:world@p.matrix for p in r.pose.bones})
 sources[label]=(rest,frames)
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_v43.blend');r=bpy.data.objects['夏晴_牛仔裤'];o=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
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
   an=side+'Arm';fn=side+'ForeArm';en=side+'Elbow'
   qa=r.pose.bones[an].matrix.to_quaternion()@rest[an].to_quaternion().inverted();qf=r.pose.bones[fn].matrix.to_quaternion()@rest[fn].to_quaternion().inverted()
   p=r.pose.bones[en];p.matrix=Matrix.Translation(r.pose.bones[fn].matrix.translation)@(qa.slerp(qf,.5)@rest[en].to_quaternion()).to_matrix().to_4x4();bpy.context.view_layer.update()
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=en)
 report.append({'clip':label,'frames':len(frames),'max_segment_direction_error_degrees':math.degrees(maxangle)})
 assert maxangle<.002
# Required focused deformation checks, not a full mesh sweep.
for label,f in [('Idle',1),('Idle',126),('Run',9),('Run',19)]:
 r.animation_data.action=bpy.data.actions[label];s.frame_set(f);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 for v in ev.data.vertices:
  assert all(math.isfinite(c) for c in v.co)
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='4.4'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
(OUT/'source-hand-pose-report.json').write_text(json.dumps(report,indent=2));print('SOURCE_MATCH',report,flush=True)
