"""Blender retarget FBX clips and append glTF animation buffers without re-exporting original geometry."""
import bpy,json,math,struct,hashlib,subprocess,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;AS=P.parents[2]/'dist/assets'
SOURCES={'Jump':P/'sources'/'Jump.fbx','Fire':P/'sources'/'Firing Rifle.fbx'}
C=Matrix.Rotation(-math.pi/2,4,'X')
def readglb(path):
 b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);o=20+n;ln=struct.unpack_from('<I',b,o)[0];return j,bytearray(b[o+8:o+8+ln])
def writeglb(path,j,b):
 j['buffers'][0]['byteLength']=len(b);jb=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();jb+=b' '*((-len(jb))%4);b+=b'\0'*((-len(b))%4);path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(jb)+len(b))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(b),0x004e4942)+b)
def globals(j):
 ns=j['nodes'];parents={k:i for i,n in enumerate(ns) for k in n.get('children',[])};cache={}
 def g(i):
  if i in cache:return cache[i]
  n=ns[i]
  if 'matrix' in n:l=Matrix(np.array(n['matrix']).reshape(4,4).T.tolist())
  else:
   q=n.get('rotation',[0,0,0,1]);l=Matrix.LocRotScale(Vector(n.get('translation',[0,0,0])),Quaternion((q[3],*q[:3])),Vector(n.get('scale',[1,1,1])))
  cache[i]=(g(parents[i]) if i in parents else Matrix.Identity(4))@l;return cache[i]
 for i in range(len(ns)):g(i)
 return cache,parents
reports={}
for outfit in ['vest','green_t','floral_dress','school_uniform']:
 file=AS/(outfit+'_xiaqing.glb');backup=P/'originals'/file.name;backup.parent.mkdir(exist_ok=True)
 if not backup.exists():backup.write_bytes(subprocess.check_output(['git','-C',str(AS.parents[1]),'show','868dc40:dist/assets/'+file.name]))
 j,binary=readglb(backup);G,parents=globals(j);byname={n.get('name'):i for i,n in enumerate(j['nodes'])}
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(backup));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');scene=bpy.context.scene
 t.animation_data_clear();t.data.pose_position='POSE'
 for pb in t.pose.bones:pb.matrix_basis.identity()
 rest={n:t.matrix_world@bone.matrix_local for n,bone in t.data.bones.items()};order=sorted(t.data.bones.keys(),key=lambda n:len(t.data.bones[n].parent_recursive));reports[outfit]={}
 for label,source in SOURCES.items():
  before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(source));added=set(bpy.data.objects)-before;s=next(o for o in added if o.type=='ARMATURE');sa=s.animation_data.action;fps=scene.render.fps;start,end=map(float,sa.frame_range);duration=(end-start)/fps
  sr={n:s.matrix_world@bone.matrix_local for n,bone in s.data.bones.items()};prefix='mixamorig:'
  mapping={'hips':'Hips','spine_0':'Spine','spine_1':'Spine1','spine_2':'Spine2','neck_0':'Neck','neck_1':'Neck','head':'Head'}
  child={'arm_clavicle':'arm_humerus','arm_humerus':'arm_radius','arm_radius':'arm_wrist','leg_femur':'leg_tibia','leg_tibia':'leg_ankle','leg_ankle':'leg_ball'};source_child={'Shoulder':'Arm','Arm':'ForeArm','ForeArm':'Hand','UpLeg':'Leg','Leg':'Foot','Foot':'ToeBase'}
  for side,long in [('l','Left'),('r','Right')]:
   for a,b in [('arm_clavicle','Shoulder'),('arm_humerus','Arm'),('arm_radius','ForeArm'),('arm_wrist','Hand'),('leg_femur','UpLeg'),('leg_tibia','Leg'),('leg_ankle','Foot'),('leg_ball','ToeBase')]:mapping[side+'_'+a]=long+b
   for digit,src in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('little','Pinky')]:
    for k in range(3):mapping[f'{side}_hand_{digit}_{k+1 if digit in ["ring","little"] else k}']=f'{long}Hand{src}{k+1}'
  mapping={n:prefix+v for n,v in mapping.items() if n in rest and prefix+v in sr};alignment={n:Matrix.Identity(3) for n in mapping}
  def pos(d,n):return d[n].translation.copy()
  def rot(m):return m.to_quaternion().normalized().to_matrix()
  def palm(w,mid,idx,little):
   x=(mid-w).normalized();y=idx-little;y=(y-x*y.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
  for side,long in [('l','Left'),('r','Right')]:
   for name,nextname in child.items():
    tn=side+'_'+name;tc=side+'_'+nextname;sn=mapping[tn];suffix=sn[len(prefix+long):];sc=prefix+long+source_child[suffix];alignment[tn]=(pos(rest,tc)-pos(rest,tn)).rotation_difference(pos(sr,sc)-pos(sr,sn)).to_matrix()
   tb=palm(pos(rest,side+'_arm_wrist'),pos(rest,side+'_hand_middle_0'),pos(rest,side+'_hand_index_0'),pos(rest,side+'_hand_little_1'));sb=palm(pos(sr,prefix+long+'Hand'),pos(sr,prefix+long+'HandMiddle1'),pos(sr,prefix+long+'HandIndex1'),pos(sr,prefix+long+'HandPinky1'));alignment[side+'_arm_wrist']=sb@tb.transposed()
   def frame(direction,normal):
    x=direction.normalized();y=(normal-x*normal.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
   for name,sname in mapping.items():
    if name.startswith(side+'_hand_'):alignment[name]=frame(sr[sname].to_3x3().col[1],sb.col[2])@frame(rest[name].to_3x3().col[0]*(1 if side=='l' else -1),tb.col[2]).transposed()
  mapped=sorted(mapping,key=lambda n:len(t.data.bones[n].parent_recursive));times=np.linspace(0,duration,round(duration*30)+1);values={name:{'translation':[],'rotation':[],'scale':[]} for name in order if name in byname};frames=[];sole=[]
  scene.frame_set(int(start),subframe=start-int(start));sourceZ=(s.matrix_world@s.pose.bones[prefix+'Hips'].matrix).translation.z;ratio=rest['hips'].translation.z/sr[prefix+'Hips'].translation.z
  for time in times:
   sf=start+time*fps;scene.frame_set(int(sf),subframe=sf-int(sf))
   for pb in t.pose.bones:pb.matrix_basis.identity()
   if label=='Jump':
    z=((s.matrix_world@s.pose.bones[prefix+'Hips'].matrix).translation.z-sourceZ)*ratio
    pb=t.pose.bones['COG'];pb.location=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,0,z))
   bpy.context.view_layer.update()
   for name in mapped:
    pb=t.pose.bones[name];desired=rot(s.matrix_world@s.pose.bones[mapping[name]].matrix)@rot(sr[mapping[name]]).transposed()@alignment[name]@rot(rest[name]);head=pb.head.copy();pb.matrix=t.matrix_world.inverted()@Matrix.Translation(t.matrix_world@head)@desired.to_4x4();pb.scale=(1,1,1)
    # Limit source flat-foot flexion for rigid platform heels. Shoe geometry is never edited.
    if name.endswith('_leg_ankle') and outfit=='vest':
     q=pb.rotation_quaternion.copy();q.negate() if q.w<0 else None;angle=q.angle;cap=math.radians(7 if label=='Jump' else 4);pb.rotation_quaternion=Quaternion().slerp(q,min(1,cap/max(angle,1e-8)))
    bpy.context.view_layer.update()
   # Twist helper rotations spread forearm roll, avoiding a single collapsed elbow seam.
   for side in ['l','r']:
    hn,en,wn=[side+x for x in ['_arm_humerus','_arm_radius','_arm_wrist']];skin={n:(t.matrix_world@t.pose.bones[n].matrix)@rest[n].inverted() for n in [hn,en,wn]};qr=skin[en].to_quaternion();qw=skin[wn].to_quaternion();rel=qr.inverted()@qw
    if rel.w<0:rel.negate()
    axis=(rest[wn].translation-rest[en].translation).normalized();projection=axis*Vector((rel.x,rel.y,rel.z)).dot(axis);tw=Quaternion((rel.w,*projection));tw.normalize()
    for k in range(4):
     name=side+'_arm_radius_twist_'+str(k)+'_H'
     if name not in rest:continue
     rotation=qr@Quaternion().slerp(tw,k/3);desired=Matrix.Translation((t.matrix_world@t.pose.bones[wn].matrix).translation)@rotation.to_matrix().to_4x4()@Matrix.Translation(-rest[wn].translation)@rest[name];t.pose.bones[name].matrix=t.matrix_world.inverted()@desired;bpy.context.view_layer.update()
    name=side+'_arm_humerus_twist_3_H'
    if name in rest:
     rotation=skin[hn].to_quaternion().slerp(qr,.5);desired=Matrix.Translation((t.matrix_world@t.pose.bones[en].matrix).translation)@rotation.to_matrix().to_4x4()@Matrix.Translation(-rest[en].translation)@rest[name];t.pose.bones[name].matrix=t.matrix_world.inverted()@desired;bpy.context.view_layer.update()
   current={byname[name]:C@((t.matrix_world@t.pose.bones[name].matrix)@rest[name].inverted())@C.inverted()@G[byname[name]] for name in values}
   for name,row in values.items():
    idx=byname[name];par=parents.get(idx);parmat=current.get(par,G.get(par,Matrix.Identity(4)));loc,quat,scale=(parmat.inverted()@current[idx]).decompose();xyzw=[quat.x,quat.y,quat.z,quat.w]
    if row['rotation'] and np.dot(xyzw,row['rotation'][-1])<0:xyzw=[-x for x in xyzw]
    row['translation'].append(list(loc));row['rotation'].append(xyzw);row['scale'].append(list(scale))
   # lowest skinned vertex of visible meshes at sampled source frame
   low=1e9
   if len(sole)%5==0 or time==times[-1]:
    for ob in bpy.context.scene.objects:
     if ob.type!='MESH' or ob in added or not any(m.type=='ARMATURE' for m in ob.modifiers):continue
     eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();low=min(low,min((eo.matrix_world@v.co).z for v in me.vertices));eo.to_mesh_clear()
   sole.append(low)
   print('FRAME',outfit,label,round(float(time),3),flush=True)
  def access(data,type):
   a=np.asarray(data,dtype='<f4');binary.extend(b'\0'*((-len(binary))%4));vi=len(j['bufferViews']);j['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':a.nbytes});binary.extend(a.tobytes());idx=len(j['accessors']);ac={'bufferView':vi,'componentType':5126,'count':len(a),'type':type}
   if type=='SCALAR':ac.update(min=[float(a.min())],max=[float(a.max())])
   j['accessors'].append(ac);return idx
  inp=access(times,'SCALAR');anim={'name':label,'samplers':[],'channels':[]}
  for name,row in values.items():
   for kind,arr in row.items():
    ai=access(arr,'VEC4' if kind=='rotation' else 'VEC3');si=len(anim['samplers']);anim['samplers'].append({'input':inp,'output':ai,'interpolation':'LINEAR'});anim['channels'].append({'sampler':si,'target':{'node':byname[name],'path':kind}})
  j['animations']=[a for a in j.get('animations',[]) if a['name']!=label]+[anim];reports[outfit][label]={'duration':duration,'mapped_bones':len(mapping),'key_samples':len(times),'ground':-min(sole),'vertical_root_motion':label=='Jump','mesh_rest_or_weights_changed':False,'groundSampleMin':min(sole)}
  # Keep the source action and a retargeted editable rig scene, plus exact generated samples.
  np.savez_compressed(P/(outfit+'_'+label+'.npz'),times=times,**{name+'_'+kind:arr for name,row in values.items() for kind,arr in row.items()})
  for ob in added:bpy.data.objects.remove(ob,do_unlink=True)
  print('DONE',outfit,label,flush=True)
 writeglb(file,j,binary)
 (P/'report.json').write_text(json.dumps(reports,indent=2))
print('ALL_DONE',flush=True)
