import bpy, math, json
from mathutils import Vector, Matrix
BASE='/workspace/scratch/7b171b7361b3/'
OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/xiaqing_rigged.glb'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
motions={};restq={}
for label,filename in [('Walk','Female Walk.fbx'),('Run','Running(3).fbx')]:
 bpy.ops.import_scene.fbx(filepath=BASE+'upload/'+filename)
 src=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
 act=src.animation_data.action;start,end=map(int,act.frame_range);frames=[]
 for f in range(start,end+1):
  bpy.context.scene.frame_set(f)
  frames.append({b.name.replace('mixamorig:',''):(src.matrix_world@b.matrix).to_quaternion().copy() for b in src.pose.bones})
 root=[]
 for f in range(start,end+1):
  bpy.context.scene.frame_set(f);root.append((src.matrix_world@src.pose.bones['mixamorig:Hips'].matrix).translation.z)
 if not restq:restq={b.name.replace('mixamorig:',''):(src.matrix_world@b.matrix_local).to_quaternion().copy() for b in src.data.bones}
 motions[label]=(frames,root)
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.ops.import_scene.gltf(filepath=BASE+'upload/xiaqing.glb')
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in meshes:
 o.matrix_world=o.matrix_world.copy();o.parent=None
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.select_set(False)
rigdata=bpy.data.armatures.new('XiaQingSkeleton');rig=bpy.data.objects.new('夏晴',rigdata);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
spec={
'Hips':((0,.005,.535),(0,.005,.59),None),
'Spine':((0,.005,.59),(0,.005,.665),'Hips'),
'Spine1':((0,.005,.665),(0,.005,.725),'Spine'),
'Spine2':((0,.005,.725),(0,.005,.79),'Spine1'),
'Neck':((0,.005,.79),(0,.005,.84),'Spine2'),
'Head':((0,.005,.84),(0,.005,.96),'Neck')}
for side,sgn in [('Left',1),('Right',-1)]:
 spec.update({
 side+'Shoulder':((sgn*.025,.005,.78),(sgn*.10,.005,.785),'Spine2'),
 side+'Arm':((sgn*.10,.005,.785),(sgn*.126,-.006,.63),side+'Shoulder'),
 side+'ForeArm':((sgn*.126,-.006,.63),(sgn*.132,-.025,.485),side+'Arm'),
 side+'Hand':((sgn*.132,-.025,.485),(sgn*.132,-.032,.427),side+'ForeArm'),
 side+'UpLeg':((sgn*.043,.005,.525),(sgn*.043,-.003,.278),'Hips'),
 side+'Leg':((sgn*.043,-.003,.278),(sgn*.039,.012,.105),side+'UpLeg'),
 side+'Foot':((sgn*.039,.012,.105),(sgn*.039,-.04,.035),side+'Leg'),
 side+'ToeBase':((sgn*.039,-.04,.035),(sgn*.039,-.075,.028),side+'Foot')})
for n,(h,t,p) in spec.items():
 b=rigdata.edit_bones.new(n);b.head=h;b.tail=t
 if p:b.parent=rigdata.edit_bones[p]
 b.align_roll(restq[n]@Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')
def smooth(a,b,z):
 t=max(0,min(1,(z-a)/(b-a)));return t*t*(3-2*t)
def mix(n1,n2,w):return {n1:1-w,n2:w}
def leg(x,z):
 side='Left' if x>=0 else 'Right'
 if z>.30:return {side+'UpLeg':1}
 if z>.25:return mix(side+'Leg',side+'UpLeg',smooth(.25,.30,z))
 if z>.13:return {side+'Leg':1}
 return mix(side+'Foot',side+'Leg',smooth(.085,.13,z))
def torso(z):
 if z<.58:return {'Hips':1}
 if z<.65:return mix('Hips','Spine',smooth(.58,.65,z))
 if z<.71:return mix('Spine','Spine1',smooth(.65,.71,z))
 if z<.78:return mix('Spine1','Spine2',smooth(.71,.78,z))
 return mix('Spine2','Neck',smooth(.78,.825,z))
counts={}
for o in meshes:
 idx=int(o.name.split('_')[-1]);groups={n:o.vertex_groups.new(name=n) for n in spec}
 for v in o.data.vertices:
  x,y,z=v.co
  if idx==1:w=mix('Spine2','Head',smooth(.70,.84,z))
  elif idx==7:
   if z>.815:w={'Head':1}
   elif z>.775:w=mix('Neck','Head',smooth(.775,.815,z))
   else:w=torso(z)
  elif idx in [4,5]:
   side='Left' if x>=0 else 'Right'
   if z>.75:w=mix(side+'Arm',side+'Shoulder',smooth(.75,.81,z)*.55)
   elif z>.60:w=mix(side+'ForeArm',side+'Arm',smooth(.60,.66,z))
   elif z>.505:w={side+'ForeArm':1}
   else:w=mix(side+'Hand',side+'ForeArm',smooth(.465,.505,z))
  elif idx in [3,6,8,9,11,12,13,14]:w=leg(x,z)
  elif idx==0:
   if z>.55:w=torso(z)
   else:
    influence=1-smooth(.42,.55,z)
    side='Left' if x>=0 else 'Right'
    w={'Hips':1-influence,side+'UpLeg':influence}
  elif idx==2:
   w=torso(min(z,.779))
   if z>.745 and abs(x)>.055:
    side='Left' if x>=0 else 'Right';a=smooth(.055,.105,abs(x))*smooth(.745,.79,z)
    w={k:v*(1-a) for k,v in w.items()};w[side+'Arm']=a*.65;w[side+'Shoulder']=a*.35
  elif idx==10:w={'Hips':1}
  else:w={'Hips':1}
  for n,val in w.items():
   if val>1e-5:groups[n].add([v.index],val,'REPLACE')
 mod=o.modifiers.new('XiaQingSkin','ARMATURE');mod.object=rig;o.parent=rig
 o.name='夏晴_'+str(idx).zfill(2);counts[o.name]=len(o.data.vertices)
rig.animation_data_create();scene=bpy.context.scene;scene.render.fps=30
names=list(spec)
# Fit source global rotations to the target's rest-position proportions.
for label,(frames,roots) in motions.items():
 action=bpy.data.actions.new(label);rig.animation_data.action=action
 for f,source in enumerate(frames,1):
  scene.frame_set(f)
  for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
  bpy.context.view_layer.update()
  for n in names:
   pb=rig.pose.bones[n]
   if pb.parent:head=pb.parent.matrix@pb.parent.bone.matrix_local.inverted()@pb.bone.head_local
   else:head=pb.bone.head_local+Vector((0,0,(roots[f-1]-sum(roots)/len(roots))*.54))
   pb.matrix=Matrix.Translation(head)@source[n].to_matrix().to_4x4();bpy.context.view_layer.update()
  # Ground the high-heeled model using evaluated shoe geometry.
  dg=bpy.context.evaluated_depsgraph_get();lo=1e9
  for shoe in [o for o in meshes if o.name in ['夏晴_08','夏晴_09','夏晴_11','夏晴_12','夏晴_13','夏晴_14']]:
   ev=shoe.evaluated_get(dg);lo=min(lo,min((ev.matrix_world@v.co).z for v in ev.data.vertices))
  rig.pose.bones['Hips'].location+=rig.data.bones['Hips'].matrix_local.to_quaternion().inverted()@Vector((0,0,-lo))
  bpy.context.view_layer.update()
  for pb in rig.pose.bones:
   pb.rotation_mode='QUATERNION';pb.keyframe_insert('location',frame=f,group=pb.name);pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name);pb.keyframe_insert('scale',frame=f,group=pb.name)
 rig.animation_data.action=None
 track=rig.animation_data.nla_tracks.new();track.name=label;strip=track.strips.new(label,1,action);track.mute=True
# Idle with gentle breathing, retaining the source model's relaxed arms.
idle=bpy.data.actions.new('Idle');rig.animation_data.action=idle
for f in range(1,62):
 scene.frame_set(f)
 for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
 phase=math.sin((f-1)/60*2*math.pi)
 rig.pose.bones['Spine1'].rotation_quaternion=Vector((1,0,0)).rotation_difference(Vector((1,0,.006*phase)))
 for pb in rig.pose.bones:pb.keyframe_insert('location',frame=f,group=pb.name);pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name);pb.keyframe_insert('scale',frame=f,group=pb.name)
rig.animation_data.action=None;track=rig.animation_data.nla_tracks.new();track.name='Idle';track.strips.new('Idle',1,idle);track.mute=True
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);scene.frame_start=1;scene.frame_end=61
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_rigged.blend')
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_anim_slide_to_zero=True,export_force_sampling=True,export_def_bones=True)
print('RIG_COMPLETE',len(spec),'bones',sum(counts.values()),'vertices',[(a.name,len(a.layers)) for a in bpy.data.actions]);print('OUT',OUT)
