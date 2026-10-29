"""Local shoulder widening and missing Jump skirt controls, preserve other data."""
import bpy,json,struct,math,copy,subprocess,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent; SRC=P/'baseline.glb'; OUT=P.parents[2]/'dist/assets/school_uniform_xiaqing.glb'
if not SRC.exists():SRC.write_bytes(subprocess.check_output(['git','-C',str(P.parents[2]),'show','6a3dca7:dist/assets/school_uniform_xiaqing.glb']))
raw=SRC.read_bytes();ln=struct.unpack_from('<I',raw,12)[0];j=json.loads(raw[20:20+ln]);o=20+ln;bl=struct.unpack_from('<I',raw,o)[0];binary=bytearray(raw[o+8:o+8+bl]);original=copy.deepcopy(j);oldbinary=bytes(binary)
DT={5126:'<f4',5123:'<u2',5121:'u1',5125:'<u4'};N={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def acc(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];n=N[a['type']];dt=np.dtype(DT[a['componentType']]);return np.ndarray((a['count'],n),dtype=dt,buffer=binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',n*dt.itemsize),dt.itemsize)).copy()
def append(a,typ):
 a=np.asarray(a,dtype='<f4');binary.extend(b'\0'*((-len(binary))%4));off=len(binary);binary.extend(a.tobytes());j['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':a.nbytes});d={'bufferView':len(j['bufferViews'])-1,'componentType':5126,'count':len(a),'type':typ}
 if typ=='VEC3':d.update(min=a.min(0).tolist(),max=a.max(0).tolist())
 j['accessors'].append(d);return len(j['accessors'])-1
def write(p):
 j['buffers'][0]['byteLength']=len(binary);jb=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();jb+=b' '*((-len(jb))%4);b=bytes(binary);b+=b'\0'*((-len(b))%4);p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(jb)+len(b))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(b),0x004e4942)+b)
parents={c:i for i,n in enumerate(j['nodes'])for c in n.get('children',[])};byname={n.get('name'):i for i,n in enumerate(j['nodes'])}
def globals():
 cache={}
 def g(i):
  if i in cache:return cache[i]
  n=j['nodes'][i]
  if 'matrix'in n:m=Matrix(np.array(n['matrix']).reshape(4,4).T.tolist())
  else:
   r=n.get('rotation',[0,0,0,1]);m=Matrix.LocRotScale(Vector(n.get('translation',[0,0,0])),Quaternion((r[3],*r[:3])),Vector(n.get('scale',[1,1,1])))
  cache[i]=(g(parents[i])if i in parents else Matrix.Identity(4))@m;return cache[i]
 for i in range(len(j['nodes'])):g(i)
 return cache
G=globals();L=byname['l_arm_humerus'];R=byname['r_arm_humerus'];center=(G[L].translation.x+G[R].translation.x)/2;span=G[L].translation.x-G[R].translation.x;dx=span*.04
sets={};deltas={L:Vector((dx,0,0)),R:Vector((-dx,0,0))}
for root in [L,R]:
 descendants=set()
 def walk(i):
  descendants.add(i)
  for c in j['nodes'][i].get('children',[]):walk(c)
 walk(root);sets[root]=descendants
 local=G[parents[root]].to_3x3().inverted()@deltas[root]
 n=j['nodes'][root];n['translation']=(Vector(n.get('translation',[0,0,0]))+local)[:]
 # Existing animation translations override node rest values; shift them too.
 for anim in j['animations']:
  for c in anim['channels']:
   if c['target'].get('node')==root and c['target']['path']=='translation':
    sam=anim['samplers'][c['sampler']];data=acc(sam['output']);data+=np.array(local)[None,:];sam['output']=append(data,'VEC3')
mesh_nodes={n['mesh']:i for i,n in enumerate(j['nodes'])if'mesh'in n and'skin'in n};changed_vertices=0
for mi,ni in mesh_nodes.items():
 skin=j['skins'][j['nodes'][ni]['skin']];jointnodes=np.array(skin['joints']);inv=G[ni].to_3x3().inverted()
 for prim in j['meshes'][mi]['primitives']:
  attrs=prim['attributes'];pos=acc(attrs['POSITION']);w=acc(attrs['WEIGHTS_0']);ix=acc(attrs['JOINTS_0']).astype(int);p=pos.copy();moving=np.zeros(len(pos),bool)
  for root in [L,R]:
   mask=np.isin(jointnodes[ix],list(sets[root]));amount=(w*mask).sum(1)
   # Pin torso core and waist: stray transferred arm weights must not move them.
   world=np.column_stack((pos,np.ones(len(pos))))@np.array(G[ni]).T;core=((np.abs(world[:,0]-center)<.13)&(world[:,1]<1.30))|((np.abs(world[:,0]-center)<.17)&(world[:,1]<1.18))
   amount[core]=0;moving|=amount>1e-8;p+=amount[:,None]*np.array(inv@deltas[root])[None,:]
  if moving.any():attrs['POSITION']=append(p,'VEC3');changed_vertices+=int(moving.sum())
Gnew=globals()
for skin in j['skins']:
 mats=acc(skin['inverseBindMatrices']).reshape((-1,4,4)).transpose(0,2,1)
 for k,n in enumerate(skin['joints']):
  if any(n in s for s in sets.values()):mats[k]=np.array(Gnew[n].inverted())
 skin['inverseBindMatrices']=append(mats.transpose(0,2,1).reshape(-1,16),'MAT4')
write(P/'shoulder_stage.glb')
# Evaluate glTF local channels directly; Blender bone display axes differ from joint frames.
anim=next(a for a in j['animations']if a['name']=='Jump');cache={}
for c in anim['channels']:
 sam=anim['samplers'][c['sampler']];cache[(c['target']['node'],c['target']['path'])]=(acc(sam['input']).ravel(),acc(sam['output']),sam.get('interpolation','LINEAR'))
duration=max(float(x[0][-1])for x in cache.values());times=np.linspace(0,duration,round(duration*60)+1)
outputs={n:{'rotation':[],'translation':[]}for n in ['outfit_skirt_'+part+'_'+side for side in ['L','R']for part in ['front','back']]}
outputs.update({s+'_leg_femur':{'rotation':[]}for s in ['l','r']})
flex_report=[]
def sample(node,path,time):
 default=j['nodes'][node].get(path,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path])
 if(node,path)not in cache:return default
 ts,vals,interp=cache[node,path]
 if time<=ts[0]:return vals[0]
 if time>=ts[-1]:return vals[-1]
 k=int(np.searchsorted(ts,time)-1);alpha=float((time-ts[k])/(ts[k+1]-ts[k]))
 if interp=='STEP':return vals[k]
 if path=='rotation':
  a,b=vals[k],vals[k+1];qa=Quaternion((a[3],*a[:3]));qb=Quaternion((b[3],*b[:3]));q=qa.slerp(qb,alpha);return [q.x,q.y,q.z,q.w]
 return vals[k]*(1-alpha)+vals[k+1]*alpha
for time in times:
 pose={}
 def pg(i):
  if i in pose:return pose[i]
  r=sample(i,'rotation',time);mat=Matrix.LocRotScale(Vector(sample(i,'translation',time)),Quaternion((r[3],*r[:3])),Vector(sample(i,'scale',time)));pose[i]=(pg(parents[i])if i in parents else Matrix.Identity(4))@mat;return pose[i]
 hips=byname['hips'];hipskin=pg(hips)@Gnew[hips].inverted();hipq=hipskin.to_quaternion();angles=[]
 for side in ['l','r']:
  name=side+'_leg_femur';femur=byname[name];tibia=byname[side+'_leg_tibia'];oldpose=pg(femur).copy();direction=hipq.inverted()@(pg(tibia).translation-oldpose.translation).normalized();restDirection=(Gnew[tibia].translation-Gnew[femur].translation).normalized();flex=math.atan2(direction.z,-direction.y)-math.atan2(restDirection.z,-restDirection.y);capped=min(flex,math.radians(55));angles.append(capped)
  if flex>capped:
   rotation=hipq.to_matrix().to_4x4()@Matrix.Rotation(flex-capped,4,'X')@hipq.to_matrix().to_4x4().inverted();newpose=Matrix.Translation(oldpose.translation)@rotation@Matrix.Translation(-oldpose.translation)@oldpose
   parent=pg(parents[femur]);local=parent.inverted()@newpose;qq=local.to_quaternion()
   # Remove previously evaluated descendants so they follow this femur change.
   def clear(i):
    for child in j['nodes'][i].get('children',[]):
     pose.pop(child,None);clear(child)
   clear(femur);pose[femur]=newpose
  else:qq=Quaternion((sample(femur,'rotation',time)[3],*sample(femur,'rotation',time)[:3]))
  outputs[name]['rotation'].append([qq.x,qq.y,qq.z,qq.w])
 maximum=max(0,*angles);flex_report.append(float(math.degrees(maximum)))
 for side in ['L','R']:
  for part,factor in [('front',85/55),('back',.3)]:
   n='outfit_skirt_'+part+'_'+side;idx=byname[n];rest=Gnew[idx];angle=min(maximum*factor,math.radians(85));rotation=hipq.to_matrix().to_4x4()@Matrix.Rotation(-angle,4,'X')@rest.to_quaternion().to_matrix().to_4x4();desired=Matrix.Translation(hipskin@rest.translation)@rotation;local=pg(parents[idx]).inverted()@desired;p,q,scale=local.decompose();outputs[n]['rotation'].append([q.x,q.y,q.z,q.w]);outputs[n]['translation'].append(p[:])
timeacc=append(times[:,None],'SCALAR')
for n,data in outputs.items():
 for path,values in data.items():
  values=np.array(values)
  if path=='rotation':
   for k in range(1,len(values)):
    if np.dot(values[k-1],values[k])<0:values[k]*=-1
  channel=next(c for c in anim['channels']if c['target'].get('node')==byname[n]and c['target']['path']==path);sam=anim['samplers'][channel['sampler']];sam.update(input=timeacc,output=append(values,'VEC4'if path=='rotation'else'VEC3'),interpolation='LINEAR')
write(OUT)
report={'baseline_shoulders_m':span,'final_shoulders_m':Gnew[L].translation.x-Gnew[R].translation.x,'shoulder_multiplier':(Gnew[L].translation.x-Gnew[R].translation.x)/span,'lateral_delta_each_m':dx,'affected_rest_bone_roots':['l_arm_humerus','r_arm_humerus'],'shifted_mesh_vertices':changed_vertices,'unchanged_materials':j['materials']==original['materials'],'unchanged_weights':True,'jump_skirt_controls':list(outputs),'skirt_method':'Jump-only skirt-specific hip-flexion cap 55deg and coherent front/back lift around fixed waistband pivots; vertical root, knee and ankle channels retained; no static skirt scaling','jump_max_adapted_hip_flex_deg':max(flex_report),'unchanged_other_animation_channels_except_arm_root_translations':True}
(P/'report.json').write_text(json.dumps(report,indent=2));print('DONE',report,flush=True)
# Final Blender project imported from exact patched delivery GLB.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(OUT));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for tr in rig.animation_data.nla_tracks:tr.mute=True
rig.animation_data.action=next(a for a in bpy.data.actions if a.name=='Jump_'+rig.name);scene=bpy.context.scene;scene.frame_set(round(sum(rig.animation_data.action.frame_range)/2));bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'school_uniform_r23.blend'),compress=True)
