"""Idle bilateral clavicle rest-slope correction; preserves source torso side lean.
Standalone creates an independent trial, patch, one after render, and audit report.
Merged scene: runpy.run_path(__file__)["apply_idle_clavicle_patch"](rig).
"""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path(__file__).resolve().parent
BONES=['l_arm_clavicle','r_arm_clavicle']
PATHS={n:f'pose.bones["{n}"].rotation_quaternion' for n in BONES}

def curves_digest(action,exclude_target=False):
 rows=[]
 for f in action.fcurves:
  if exclude_target and f.data_path in PATHS.values():continue
  rows.append([f.data_path,f.array_index,[[*k.co,*k.handle_left,*k.handle_right,k.interpolation] for k in f.keyframe_points]])
 return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def apply_idle_clavicle_patch(rig,patch_path=None):
 data=np.load(str(patch_path or P/'idle_clavicle_patch.npz'));a=next(x for x in bpy.data.actions if x.name.startswith('Idle'));times=data['times'];quats=data['quaternions'];bones=list(data['bones']);before=curves_digest(a,True)
 for bi,bone in enumerate(bones):
  path=PATHS[str(bone)];fs=[f for f in a.fcurves if f.data_path==path];assert len(fs)==4
  for f in fs:
   assert len(f.keyframe_points)==len(times)
   assert np.max(np.abs(np.array([k.co.x for k in f.keyframe_points])-times))<1e-4
   for k,t,q in zip(f.keyframe_points,times,quats[:,bi]):
    delta=float(q[f.array_index])-float(k.co.y);k.co.y+=delta;k.handle_left.y+=delta;k.handle_right.y+=delta
   f.update()
  rig.pose.bones[str(bone)].rotation_mode='QUATERNION'
 assert curves_digest(a,True)==before,'Other Idle curves changed'
 return {'action':a.name,'bones':bones,'samples':len(times),'changed_curves':8,'other_curves_unchanged':True}

def generate():
 bpy.ops.wm.open_mainfile(filepath=str(P/'shoulders_rebuilt.blend'));rig=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
 for t in rig.animation_data.nla_tracks:t.mute=True
 a=next(x for x in bpy.data.actions if x.name.startswith('Idle'));rig.animation_data.action=a;rig.data.pose_position='POSE'
 fs=[f for f in a.fcurves if f.data_path==PATHS[BONES[0]] and f.array_index==0];assert len(fs)==1
 times=np.array([k.co.x for k in fs[0].keyframe_points]);parent=rig.pose.bones['spine_2'];quats=[];rows=[];targets={}
 for side in ['l','r']:
  targets[side]=float((rig.data.bones[side+'_arm_humerus'].head_local-rig.data.bones[side+'_arm_clavicle'].head_local).z)
 source_digest=curves_digest(a);other_digest=curves_digest(a,True);other_action_digest={x.name:curves_digest(x) for x in bpy.data.actions if x!=a}
 # All source key samples are collected before modifying any curve.
 for f in times:
  s.frame_set(int(f),subframe=float(f-int(f)));bpy.context.view_layer.update();pr=parent.matrix.to_3x3()@parent.bone.matrix_local.to_3x3().inverted();frame_quats=[];row={'frame':float(f),'sides':{}}
  for bi,side in enumerate(['l','r']):
   clav=rig.pose.bones[side+'_arm_clavicle'];arm=rig.pose.bones[side+'_arm_humerus'];v=pr.inverted()@(arm.head-clav.head);target=v.copy();target.z=targets[side];xy=math.hypot(v.x,v.y);xy_target=math.sqrt(max(0,v.length_squared-target.z*target.z));target.x*=xy_target/xy;target.y*=xy_target/xy
   align=v.rotation_difference(target);armature_q=pr.to_quaternion()@align@pr.to_quaternion().inverted();head=clav.head.copy();row['sides'][side]={'before_head_z':float(arm.head.z),'before_spine_z':float(v.z),'target_spine_z':float(target.z)}
   clav.matrix=Matrix.Translation(head)@armature_q.to_matrix().to_4x4()@Matrix.Translation(-head)@clav.matrix.copy();bpy.context.view_layer.update();q=clav.rotation_quaternion.copy()
   if quats:q.make_compatible(Quaternion(quats[-1][bi]))
   frame_quats.append(list(q))
  quats.append(frame_quats);rows.append(row)
 quats=np.array(quats);np.savez(P/'idle_clavicle_patch.npz',times=times,quaternions=quats,bones=np.array(BONES),source_digest=np.array(source_digest),rest_target_z=np.array([targets['l'],targets['r']]))
 result=apply_idle_clavicle_patch(rig);assert curves_digest(a,True)==other_digest;assert all(curves_digest(x)==other_action_digest[x.name] for x in bpy.data.actions if x!=a)
 after=[]
 for f in times:
  s.frame_set(int(f),subframe=float(f-int(f)));bpy.context.view_layer.update();pr=parent.matrix.to_3x3()@parent.bone.matrix_local.to_3x3().inverted();row={'frame':float(f),'sides':{}}
  for side in ['l','r']:
   c=rig.pose.bones[side+'_arm_clavicle'];arm=rig.pose.bones[side+'_arm_humerus'];v=pr.inverted()@(arm.head-c.head);row['sides'][side]={'head_z':float(arm.head.z),'spine_z':float(v.z)}
  after.append(row)
 report={'method':'Idle BILATERAL clavicles only. Preserve horizontal shoulder-vector heading and length in deposed spine frame. Set each vertical vector component to its native Rest downward slope. The original spine side lean is preserved.','patch':result,'rest_target_z_m':targets,'before_max_abs_left_right_height_gap_mm':max(abs((x['sides']['l']['before_head_z']-x['sides']['r']['before_head_z'])*1000) for x in rows),'after_max_abs_left_right_height_gap_mm':max(abs((x['sides']['l']['head_z']-x['sides']['r']['head_z'])*1000) for x in after),'target_max_error_m':max(abs(x['sides'][side]['spine_z']-targets[side]) for x in after for side in ['l','r']),'quaternion_loop_angle_rad':{side:float(Quaternion(quats[0,i]).rotation_difference(Quaternion(quats[-1,i])).angle) for i,side in enumerate(['l','r'])},'quaternion_neighbor_max_angle_rad':{side:float(max(Quaternion(x[i]).rotation_difference(Quaternion(y[i])).angle for x,y in zip(quats[:-1],quats[1:]))) for i,side in enumerate(['l','r'])},'other_Idle_curves_unchanged':curves_digest(a,True)==other_digest,'other_actions_unchanged':True,'before':rows,'after':after}
 assert report['target_max_error_m']<1e-5;assert max(report['quaternion_loop_angle_rad'].values())<1e-4
 # Update the same independent trial, without creating additional large blends.
 s.frame_set(70);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'idle_clavicle_corrected.blend'),compress=True)
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100
 target=Vector((0,.015,1.32));c=s.camera;c.location=target+Vector((0,-3,.09));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=.72;s.render.filepath=str(P/'idle_clavicle_after_0.35.png');bpy.ops.render.render(write_still=True)
 (P/'idle_clavicle_report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['before','after']},indent=2))

if __name__=='__main__':generate()
