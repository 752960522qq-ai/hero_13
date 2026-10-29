import bpy,json,math,re,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;AS=P.parents[1]/'dist/assets';AS.mkdir(parents=True,exist_ok=True)
SOURCES={'Idle':str(P.parent/'inputs/male_Idle.fbx'),'Walk':str(P.parent/'inputs/Walking.fbx'),'Run':str(P.parent/'inputs/Running.fbx')}
load_path=P.parent/'double_stars_bound.blend';load_path=load_path if load_path.exists()else P/'double_stars_animated.blend'
bpy.ops.wm.open_mainfile(filepath=str(load_path));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');t.animation_data_clear()
for pb in t.pose.bones:pb.matrix_basis.identity()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
bpy.context.view_layer.update();targetobjects=list(bpy.data.objects);scene=bpy.context.scene;scene.render.fps=30
skinmods=[mo for ob in targetobjects if ob.type=='MESH' for mo in ob.modifiers if mo.type=='ARMATURE']
for mo in skinmods:mo.show_viewport=False
rest={n:t.matrix_world@b.matrix_local for n,b in t.data.bones.items()};canon={re.sub(r'_\d+$','',n):n for n in rest}
def pos(d,n):return d[n].translation.copy()
def rot(m):return m.to_quaternion().normalized().to_matrix()
def palm(d,w,mid,idx,pinky):
 x=(pos(d,mid)-pos(d,w)).normalized();y=pos(d,idx)-pos(d,pinky);y=(y-x*y.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
def frame(direction,normal):
 x=direction.normalized();y=(normal-x*normal.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
reports={};allactions=[]
for label,filepath in SOURCES.items():
 t.animation_data_clear()
 for pb in t.pose.bones:pb.matrix_basis.identity()
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=filepath);added=set(bpy.data.objects)-before;s=next(o for o in added if o.type=='ARMATURE');sa=s.animation_data.action;sourcefps=scene.render.fps;start,end=map(float,sa.frame_range);duration=(end-start)/sourcefps;scene.render.fps=30
 sr={n:s.matrix_world@b.matrix_local for n,b in s.data.bones.items()};prefix=next(n[:-4] for n in sr if n.endswith('Hips'))
 base={'pelvis':'Hips','spine_01':'Spine','spine_02':'Spine','spine_03':'Spine1','spine_04':'Spine1','spine_05':'Spine2','neck_01':'Neck','neck_02':'Neck','head':'Head'}
 pairs={'clavicle':'Shoulder','upperarm':'Arm','lowerarm':'ForeArm','hand':'Hand','thigh':'UpLeg','calf':'Leg','foot':'Foot','ball':'ToeBase'}
 for side,long in [('l','Left'),('r','Right')]:
  for a,b in pairs.items():base[a+'_'+side]=long+b
  for digit,src in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
   for k in range(1,4):base[f'{digit}_{k:02d}_{side}']=f'{long}Hand{src}{k}'
 mapping={canon[k]:prefix+v for k,v in base.items() if k in canon and prefix+v in sr};align={n:Matrix.Identity(3) for n in mapping}
 for side,long in [('l','Left'),('r','Right')]:
  child={'clavicle':'upperarm','upperarm':'lowerarm','lowerarm':'hand','thigh':'calf','calf':'foot','foot':'ball'};schild={'Shoulder':'Arm','Arm':'ForeArm','ForeArm':'Hand','UpLeg':'Leg','Leg':'Foot','Foot':'ToeBase'}
  for a,b in child.items():
   tn=canon[a+'_'+side];tc=canon[b+'_'+side];sn=mapping[tn];sc=prefix+long+schild[pairs[a]];align[tn]=(pos(rest,tc)-pos(rest,tn)).rotation_difference(pos(sr,sc)-pos(sr,sn)).to_matrix()
  tb=palm(rest,canon['hand_'+side],canon['middle_01_'+side],canon['index_01_'+side],canon['pinky_01_'+side]);sb=palm(sr,prefix+long+'Hand',prefix+long+'HandMiddle1',prefix+long+'HandIndex1',prefix+long+'HandPinky1');align[canon['hand_'+side]]=sb@tb.transposed()
  for digit,src in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
   for k in range(1,4):
    n=canon[f'{digit}_{k:02d}_{side}'];sn=mapping[n];td=(pos(rest,canon[f'{digit}_{k+1:02d}_{side}'])-pos(rest,n)) if k<3 else t.data.bones[n].tail_local-t.data.bones[n].head_local;sd=s.data.bones[sn].tail_local-s.data.bones[sn].head_local;sd=s.matrix_world.to_3x3()@sd
    align[n]=frame(sd,sb.col[2])@frame(td,tb.col[2]).transposed()
 mapped=sorted(mapping,key=lambda n:len(t.data.bones[n].parent_recursive));order=sorted(rest,key=lambda n:len(t.data.bones[n].parent_recursive));fps=30;times=np.linspace(0,duration,round(duration*fps)+1)
 action=bpy.data.actions.new(label);action.use_fake_user=True;t.animation_data_create();t.animation_data.action=action
 scene.frame_set(int(start),subframe=start-int(start));s0=(s.matrix_world@s.pose.bones[prefix+'Hips'].matrix).translation.copy();scene.frame_set(int(end),subframe=end-int(end));s1=(s.matrix_world@s.pose.bones[prefix+'Hips'].matrix).translation.copy();ratio=rest[canon['pelvis']].translation.z/sr[prefix+'Hips'].translation.z
 mins=[];scales=[]
 for fi,time in enumerate(times):
  sf=start+time*sourcefps;scene.frame_set(int(sf),subframe=sf-int(sf))
  for pb in t.pose.bones:pb.matrix_basis.identity()
  bpy.context.view_layer.update()
  for n in mapped:
   pb=t.pose.bones[n];desired=rot(s.matrix_world@s.pose.bones[mapping[n]].matrix)@rot(sr[mapping[n]]).transposed()@align[n]@rot(rest[n]);worldhead=t.matrix_world@pb.head
   if n==canon['pelvis']:
    sp=(s.matrix_world@s.pose.bones[prefix+'Hips'].matrix).translation;delta=sp-s0;linear=(s1-s0)*(float(time)/max(duration,1e-6));delta.x-=linear.x;delta.y-=linear.y;worldhead=rest[n].translation+delta*ratio
   pb.matrix=t.matrix_world.inverted()@Matrix.Translation(worldhead)@desired.to_4x4();pb.scale=(1,1,1);bpy.context.view_layer.update()
  # Spread axial roll over the original UE helper chains.
  for side in ['l','r']:
   for seg,nextseg in [('upperarm','lowerarm'),('lowerarm','hand'),('thigh','calf'),('calf','foot')]:
    pn=canon[seg+'_'+side];nn=canon[nextseg+'_'+side];ps=(t.matrix_world@t.pose.bones[pn].matrix)@rest[pn].inverted();ns=(t.matrix_world@t.pose.bones[nn].matrix)@rest[nn].inverted();qa=ps.to_quaternion();qb=ns.to_quaternion()
    for k in [1,2]:
     cn=f'{seg}_twist_{k:02d}_{side}'
     if cn not in canon:continue
     n=canon[cn];pb=t.pose.bones[n];desiredR=(qa.slerp(qb,.2 if k==1 else .65)).to_matrix()@rot(rest[n]);head=t.matrix_world@pb.head;pb.matrix=t.matrix_world.inverted()@Matrix.Translation(head)@desiredR.to_4x4();pb.scale=(1,1,1)
   bpy.context.view_layer.update()
  frameNo=fi+1
  for n in order:
   pb=t.pose.bones[n];pb.rotation_mode='QUATERNION';pb.keyframe_insert('location',frame=frameNo,group=n);pb.keyframe_insert('rotation_quaternion',frame=frameNo,group=n);pb.keyframe_insert('scale',frame=frameNo,group=n);scales.append(max(abs(x-1) for x in pb.scale))
  if fi%15==0 or fi==len(times)-1:
   for mo in skinmods:mo.show_viewport=True
   bpy.context.view_layer.update()
   low=1e9
   for ob in targetobjects:
    if ob.type!='MESH':continue
    eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();coords=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',coords);coords=coords.reshape((-1,3));low=min(low,float((coords@np.array(eo.matrix_world.to_3x3()).T+np.array(eo.matrix_world.translation))[:,2].min()));eo.to_mesh_clear()
   mins.append(low)
   for mo in skinmods:mo.show_viewport=False
  if fi%30==0:print('FRAME',label,fi,len(times),flush=True)
 # Keep all clips in-place, ground offset given separately to viewer.
 action.frame_range=(1,len(times));allactions.append(action);reports[label]={'duration':duration,'frames':len(times),'mapped_bones':len(mapping),'ground':-min(mins),'sole_samples':mins,'max_scale_error':max(scales)}
 for ob in added:bpy.data.objects.remove(ob,do_unlink=True)
 scene.render.fps=30
 print('DONE',label,reports[label],flush=True)
for mo in skinmods:mo.show_viewport=True
bpy.context.view_layer.update()
# Compatible actions are exported, no extra source rigs or helper sphere.
t.animation_data.action=None
for action in allactions:
 track=t.animation_data.nla_tracks.new();track.name=action.name;track.strips.new(action.name,1,action)
for ob in targetobjects:ob.select_set(True)
bpy.context.view_layer.objects.active=t
scene.frame_set(1);bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'double_stars_animated.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(AS/'double_stars.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_frame_range=False,export_image_format='JPEG',export_jpeg_quality=95)
(P/'report.json').write_text(json.dumps(reports,indent=2));print('ALL_DONE',flush=True)
