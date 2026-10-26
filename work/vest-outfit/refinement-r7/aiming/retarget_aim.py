"""Retarget the uploaded Mixamo aiming motion onto the unchanged Xia Qing rig."""
import bpy,json,math,shutil,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;R6=P.parent.parent/'refinement-r6'
SOURCE=P/'Rifle Aiming Idle.fbx'
if not SOURCE.exists():shutil.copy2('/workspace/attachments/0da78e4f-3ef1-4be8-b585-a3f8108f6acc/Rifle Aiming Idle.fbx',SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(R6/'vest_xiaqing_r6.blend'))
t=bpy.data.objects['Xiaqing_Native_Rig'];scene=bpy.context.scene;target_fps=scene.render.fps
for tr in t.animation_data.nla_tracks:tr.mute=True
t.animation_data.action=None;t.data.pose_position='REST'
for p in t.pose.bones:p.matrix_basis.identity()
before=set(bpy.data.objects);baseline_actions=set(bpy.data.actions)
bpy.ops.import_scene.fbx(filepath=str(SOURCE));source_objects=set(bpy.data.objects)-before
s=next(o for o in source_objects if o.type=='ARMATURE');source_action=s.animation_data.action;source_fps=scene.render.fps;scene.render.fps=target_fps
sr={b.name:s.matrix_world@b.matrix_local for b in s.data.bones};tr={b.name:t.matrix_world@b.matrix_local for b in t.data.bones}
prefix='mixamorig:';mapping={'COG':'Hips','hips':'Hips','spine_0':'Spine','spine_1':'Spine1','spine_2':'Spine2','neck_0':'Neck','neck_1':'Neck','head':'Head'}
child={'arm_clavicle':'arm_humerus','arm_humerus':'arm_radius','arm_radius':'arm_wrist','leg_femur':'leg_tibia','leg_tibia':'leg_ankle','leg_ankle':'leg_ball'}
source_child={'Shoulder':'Arm','Arm':'ForeArm','ForeArm':'Hand','UpLeg':'Leg','Leg':'Foot','Foot':'ToeBase'}
for side,long in [('l','Left'),('r','Right')]:
 for a,b in [('arm_clavicle','Shoulder'),('arm_humerus','Arm'),('arm_radius','ForeArm'),('arm_wrist','Hand'),('leg_femur','UpLeg'),('leg_tibia','Leg'),('leg_ankle','Foot'),('leg_ball','ToeBase')]:mapping[side+'_'+a]=long+b
 for digit,src in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('little','Pinky')]:
  for k in range(3):mapping[f'{side}_hand_{digit}_{k+1 if digit in ["ring","little"] else k}']=f'{long}Hand{src}{k+1}'
mapping={n:prefix+v for n,v in mapping.items() if n in tr and prefix+v in sr}
def rot(m):return m.to_quaternion().normalized().to_matrix()
def pos(d,n):return d[n].translation.copy()
alignment={n:Matrix.Identity(3) for n in mapping}
for side,long in [('l','Left'),('r','Right')]:
 for name,nextname in child.items():
  tn=side+'_'+name;tc=side+'_'+nextname;sn=mapping[tn];suffix=sn[len(prefix+long):];sc=prefix+long+source_child[suffix]
  alignment[tn]=(pos(tr,tc)-pos(tr,tn)).rotation_difference(pos(sr,sc)-pos(sr,sn)).to_matrix()
 def palm_basis(wrist,middle,index,little):
  x=(middle-wrist).normalized();y=index-little;y=(y-x*y.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
 tb=palm_basis(pos(tr,side+'_arm_wrist'),pos(tr,side+'_hand_middle_0'),pos(tr,side+'_hand_index_0'),pos(tr,side+'_hand_little_1'))
 sb=palm_basis(pos(sr,prefix+long+'Hand'),pos(sr,prefix+long+'HandMiddle1'),pos(sr,prefix+long+'HandIndex1'),pos(sr,prefix+long+'HandPinky1'))
 alignment[side+'_arm_wrist']=sb@tb.transposed()
 def frame(direction,normal):
  x=direction.normalized();y=(normal-x*normal.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
 for name,sname in mapping.items():
  if name.startswith(side+'_hand_'):
   tf=frame(tr[name].to_3x3().col[0]*(1 if side=='l' else -1),tb.col[2]);sf=frame(sr[sname].to_3x3().col[1],sb.col[2]);alignment[name]=sf@tf.transposed()
order=sorted(mapping,key=lambda n:len(t.data.bones[n].parent_recursive));t.data.pose_position='POSE'
# The transfer uses global rest-relative orientation; no FBX position, scale or
# mesh is copied. Frame sampling changes only clip timing by < one target frame.
duration=(source_action.frame_range[1]-source_action.frame_range[0])/source_fps;end=duration*target_fps;times=np.linspace(0,end,round(end)+1)
data={name:[] for name in order};hiploc=[];identity=Quaternion((1,0,0,0))
for f in times:
 sf=float(source_action.frame_range[0]+f/end*(source_action.frame_range[1]-source_action.frame_range[0]));scene.frame_set(int(sf),subframe=sf-int(sf))
 for p in t.pose.bones:p.matrix_basis.identity()
 bpy.context.view_layer.update()
 for name in order:
  pb=t.pose.bones[name];source_pose=s.matrix_world@s.pose.bones[mapping[name]].matrix;desired=rot(source_pose)@rot(sr[mapping[name]]).transposed()@alignment[name]@rot(tr[name]);head=pb.head.copy();pb.matrix=Matrix.Translation(head)@desired.to_4x4();bpy.context.view_layer.update();pb.scale=(1,1,1);q=pb.rotation_quaternion.copy().normalized()
  if name.endswith('_leg_ankle'):
   if q.w<0:q.negate()
   angle=float(q.angle);cap=math.radians(3);new=cap*math.tanh(.15*angle/cap);q=identity.slerp(q,new/angle if angle>1e-8 else .15);pb.rotation_quaternion=q;bpy.context.view_layer.update()
  if data[name]:q.make_compatible(Quaternion(data[name][-1]))
  data[name].append(list(q))
 hiploc.append([0.,0.,0.])
# Make the held aiming clip close smoothly if the source breathing loop has a
# small capture seam. Only the last 10 target frames are blended into frame0.
closure={}
for name,qs in data.items():
 closure[name]=float(Quaternion(qs[0]).rotation_difference(Quaternion(qs[-1])).angle)
 for j in range(max(1,len(qs)-11),len(qs)):
  a=(j-(len(qs)-11))/10;a=max(0,min(1,a));a=a*a*(3-2*a);q=Quaternion(qs[j]).slerp(Quaternion(qs[0]),a);q.make_compatible(Quaternion(qs[j-1]));qs[j]=list(q)
aim=bpy.data.actions.new('Aim');aim.use_fake_user=True;t.animation_data.action=aim
for name,qs in data.items():
 for component in range(4):
  fc=aim.fcurves.new(f'pose.bones["{name}"].rotation_quaternion',index=component,action_group=name);fc.keyframe_points.add(len(times));fc.keyframe_points.foreach_set('co',np.column_stack([times,np.array(qs)[:,component]]).ravel())
  for k in fc.keyframe_points:k.interpolation='LINEAR'
  fc.update()
# One mid-pose two-bone leg solve gives CONSTANT anatomical stance offsets.
# The same four offsets are applied to every key, preserving source breathing
# and avoiding frame-by-frame floor clamping. The shoes and calf remain rigid.
stance_height=-.025
cog=t.pose.bones['COG'];cog.location=cog.bone.matrix_local.to_3x3().inverted()@Vector((0,0,stance_height))
mid=len(times)//2;mf=float(times[mid]);scene.frame_set(int(mf),subframe=mf-int(mf));cog.location=cog.bone.matrix_local.to_3x3().inverted()@Vector((0,0,stance_height));bpy.context.view_layer.update()
stance_corrections={};floor=-.00964825950517234
for side in ['l','r']:
 upper=t.pose.bones[side+'_leg_femur'];lower=t.pose.bones[side+'_leg_tibia'];ankle=t.pose.bones[side+'_leg_ankle']
 for iteration in range(4):
  ob=bpy.data.objects['Shoe_'+side.upper()].evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();arr=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',arr);sole=float(arr.reshape(-1,3)[:,2].min());ob.to_mesh_clear();dz=floor-sole
  if abs(dz)<.00015:break
  h=upper.head.copy();k=lower.head.copy();a=ankle.head.copy();goal=a+Vector((0,0,dz));l1=(k-h).length;l2=(a-k).length;v=goal-h;distance=min(v.length,l1+l2-.00001);axis=v.normalized();goal=h+axis*distance;along=(l1*l1-l2*l2+distance*distance)/(2*distance);height=max(0,l1*l1-along*along)**.5;pole=k-h-axis*(k-h).dot(axis)
  if pole.length<1e-6:pole=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
  newk=h+axis*along+pole.normalized()*height
  correction=(k-h).rotation_difference(newk-h);upper.matrix=Matrix.Translation(h)@correction.to_matrix().to_4x4()@Matrix.Translation(-h)@upper.matrix.copy();bpy.context.view_layer.update()
  k=lower.head.copy();a=ankle.head.copy();correction=(a-k).rotation_difference(goal-k);lower.matrix=Matrix.Translation(k)@correction.to_matrix().to_4x4()@Matrix.Translation(-k)@lower.matrix.copy();bpy.context.view_layer.update()
 for name in [side+'_leg_femur',side+'_leg_tibia']:
  offset=t.pose.bones[name].rotation_quaternion.copy()@Quaternion(data[name][mid]).inverted();stance_corrections[name]=list(offset)
  updated=[]
  for oldq in data[name]:
   q=offset@Quaternion(oldq)
   if updated:q.make_compatible(Quaternion(updated[-1]))
   updated.append(list(q))
  data[name]=updated
  for fc in aim.fcurves:
   if fc.data_path!=f'pose.bones["{name}"].rotation_quaternion':continue
   fc.keyframe_points.foreach_set('co',np.column_stack([times,np.array(updated)[:,fc.array_index]]).ravel());fc.update()
# A single clip-wide root height seats the two planted shoes after adaptation.
sole_samples=[]
for frame in [times[0],times[len(times)//2],times[-1]]:
 scene.frame_set(int(frame),subframe=float(frame-int(frame)));t.pose.bones['COG'].location=cog.bone.matrix_local.to_3x3().inverted()@Vector((0,0,stance_height));bpy.context.view_layer.update();z=[]
 for name in ['Shoe_L','Shoe_R']:
  ob=bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();arr=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',arr);z.append(float(arr.reshape(-1,3)[:,2].min()));ob.to_mesh_clear()
 sole_samples.append(min(z))
delta=stance_height-.00964825950517234-min(sole_samples)
for frame in [times[0],times[-1]]:
 pb=t.pose.bones['COG'];pb.location=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,0,delta));pb.keyframe_insert('location',frame=float(frame),group='COG')
for fc in aim.fcurves:
 for k in fc.keyframe_points:k.interpolation='LINEAR'
for ob in source_objects:bpy.data.objects.remove(ob,do_unlink=True)
for a in list(bpy.data.actions):
 if a not in baseline_actions and a!=aim:bpy.data.actions.remove(a,do_unlink=True)
scene.frame_set(int(end/2),subframe=end/2-int(end/2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'aiming_candidate.blend'),compress=True)
np.savez_compressed(P/'aim_rotation_keys.npz',times=times,bone_names=np.array(order),quaternions=np.array([data[n] for n in order]).transpose((1,0,2)))
report={'source_fbx':SOURCE.name,'source_bones':len(sr),'source_fps':source_fps,'source_duration_s':duration,'target_fps':target_fps,'target_frames':len(times),'target_end_frame':float(end),'target_duration_s':end/target_fps,'target_bones':len(t.data.bones),'mapped_bones':mapping,'source_has_weapon':False,'mesh_rest_or_weights_changed':False,'root_travel_or_scale_transferred':False,'source_end_quaternion_angle_rad':closure,'ankle_motion_policy':'R6 rigid high-heel small-angle cap3 degrees','ground_policy':'one fixed COG vertical offset, constant four leg rotation offsets from one midpoint footplant solve, no per-frame floor clamp','fixed_vertical_offset_m':delta,'constant_leg_rotation_offsets':stance_corrections,'unshifted_sole_samples_m':sole_samples,'action':'Aim'}
(P/'retarget_report.json').write_text(json.dumps(report,indent=2));print('AIM_READY',end,len(mapping))
for ob in bpy.context.scene.objects:
 if ob.get('comparison_only'):ob.hide_render=True
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='TEXTURE';scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=False;scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
for label,offset,target,scale in [('front',(0,-3,.05),(0,0,.9),1.95),('side',(3,0,.05),(0,0,.9),1.95),('hands',(0,-3,.03),(0,-.2,1.25),.95)]:
 c=scene.camera;target=Vector(target);c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=scale;scene.render.filepath=str(P/('Aim_'+label+'.png'));bpy.ops.render.render(write_still=True)
