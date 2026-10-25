"""Retarget five existing clips onto the uploaded, unchanged native skin/skeleton."""
import json,struct,copy,hashlib,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot,Slerp
ROOT=Path(__file__).resolve().parent.parent
UPLOAD=Path('/workspace/scratch/7b171b7361b3/upload/xiaqing_body_penis.glb')
def load(p):
 raw=Path(p).read_bytes();n=struct.unpack_from('<I',raw,12)[0];j=json.loads(raw[20:20+n]);off=20+n;size=struct.unpack_from('<I',raw,off)[0];return j,bytearray(raw[off+8:off+8+size])
sj,sbin=load(ROOT/'source-models/current_motion_reference.glb');tj,tbin=load(UPLOAD)
def acc(j,b,i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];dt={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];return np.ndarray((a['count'],n),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*n),np.dtype(dt).itemsize)).copy()
def setup(j):
 ns=j['nodes'];par={c:i for i,n in enumerate(ns) for c in n.get('children',[])};local=[]
 for n in ns:
  m=np.eye(4)
  if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
  else:m[:3,:3]=Rot.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
  local.append(m)
 order=[]
 def visit(i):
  if i in order:return
  if i in par:visit(par[i])
  order.append(i)
 for i in range(len(ns)):visit(i)
 world=[None]*len(ns)
 for i in order:world[i]=world[par[i]]@local[i] if i in par else local[i].copy()
 return par,local,world,order,{n.get('name'):i for i,n in enumerate(ns)}
sp,sl,sw,so,snames=setup(sj);tp,tl,tw,to,tnames=setup(tj)
mapping={'hips':'Hips','spine_0':'Spine','spine_1':'Spine1','spine_2':'Spine2','neck_0':'Neck','neck_1':'Neck','head':'Head'}
for short,long in [('l','Left'),('r','Right')]:
 for a,b in [('arm_clavicle','Shoulder'),('arm_humerus','Arm'),('arm_radius','ForeArm'),('arm_wrist','Hand'),('leg_femur','UpLeg'),('leg_tibia','Leg'),('leg_ankle','Foot'),('leg_ball','ToeBase')]:mapping[short+'_'+a]=long+b
mapping={tnames[t]:snames[s] for t,s in mapping.items() if t in tnames and s in snames}
child_names={'arm_clavicle':'arm_humerus','arm_humerus':'arm_radius','arm_radius':'arm_wrist','leg_femur':'leg_tibia','leg_tibia':'leg_ankle','leg_ankle':'leg_ball','leg_ball':'leg_ballEnd'}
schild={'Shoulder':'Arm','Arm':'ForeArm','ForeArm':'Hand','UpLeg':'Leg','Leg':'Foot','Foot':'ToeBase'}
def rotation(m):return Rot.from_matrix(m[:3,:3]).as_matrix()
def align(a,b):
 a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);c=np.dot(a,b)
 if c<-.999999:return Rot.from_rotvec(np.cross(a,[0,1,0] if abs(a[1])<.9 else [1,0,0])*np.pi).as_matrix()
 k=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]);return np.eye(3)+k+k@k/(1+c)
alignment={}
for ti,si in mapping.items():
 name=tj['nodes'][ti]['name'];dest=None;src=None
 for suffix,ch in child_names.items():
  if name.endswith(suffix):dest=tnames.get(name[:2]+ch)
 for suffix,ch in schild.items():
  if sj['nodes'][si]['name'].endswith(suffix):src=snames.get(sj['nodes'][si]['name'].replace(suffix,ch))
 if dest is not None and src is not None:alignment[ti]=align(tw[dest][:3,3]-tw[ti][:3,3],sw[src][:3,3]-sw[si][:3,3])
 else:alignment[ti]=np.eye(3)
# Match wrist roll to the corrected forearm basis.
for side in ['l','r']:alignment[tnames[side+'_arm_wrist']]=alignment[tnames[side+'_arm_radius']]
leg_scale=np.linalg.norm(tw[tnames['l_leg_femur']][:3,3]-tw[tnames['l_leg_ankle']][:3,3])/np.linalg.norm(sw[snames['LeftUpLeg']][:3,3]-sw[snames['LeftFoot']][:3,3])
def add(data,typ):
 a=np.asarray(data,dtype='<f4');padding=(-len(tbin))%4;tbin.extend(b'\0'*padding);offset=len(tbin);tbin.extend(a.tobytes());vi=len(tj['bufferViews']);tj['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':a.nbytes});ai=len(tj['accessors']);entry={'bufferView':vi,'componentType':5126,'count':len(a),'type':typ}
 if typ=='SCALAR':entry['min']=[float(a.min())];entry['max']=[float(a.max())]
 tj['accessors'].append(entry);return ai
out=[];report=[]
for anim in sj['animations']:
 tracks=[];duration=0
 for c in anim['channels']:
  sam=anim['samplers'][c['sampler']];times=acc(sj,sbin,sam['input'])[:,0];vals=acc(sj,sbin,sam['output']);tracks.append((c['target']['node'],c['target']['path'],times,vals));duration=max(duration,float(times[-1]))
 times=np.linspace(0,duration,round(duration*30)+1);quats={i:[] for i in mapping};hippos=[];maxerr=0
 for t in times:
  loc=[m.copy() for m in sl];trs={}
  for i,path,ts,vals in tracks:
   if i not in trs:
    n=sj['nodes'][i];trs[i]=[np.array(n.get('translation',[0,0,0]),float),np.array(n.get('rotation',[0,0,0,1]),float),np.array(n.get('scale',[1,1,1]),float)]
   if path=='rotation':trs[i][1]=Slerp(ts,Rot.from_quat(vals))([np.clip(t,ts[0],ts[-1])]).as_quat()[0]
   elif path in ('translation','scale'):trs[i][0 if path=='translation' else 2]=np.array([np.interp(t,ts,vals[:,k]) for k in range(vals.shape[1])])
  for i,(p,q,sc) in trs.items():loc[i]=np.eye(4);loc[i][:3,:3]=Rot.from_quat(q).as_matrix()@np.diag(sc);loc[i][:3,3]=p
  posed=[None]*len(sl)
  for i in so:posed[i]=posed[sp[i]]@loc[i] if i in sp else loc[i]
  target=[None]*len(tl)
  for i in to:
   m=target[tp[i]]@tl[i] if i in tp else tl[i].copy()
   if i in mapping:
    si=mapping[i];desired=rotation(posed[si])@rotation(sw[si]).T@alignment[i]@rotation(tw[i]);m[:3,:3]=desired
    if i==tnames['hips']:m[:3,3]=tw[i][:3,3]+(posed[si][:3,3]-sw[si][:3,3])*leg_scale
    parent=target[tp[i]] if i in tp else np.eye(4);local=np.linalg.inv(parent)@m;q=Rot.from_matrix(local[:3,:3]).as_quat()
    if quats[i] and np.dot(quats[i][-1],q)<0:q=-q
    quats[i].append(q)
    if i==tnames['hips']:hippos.append(local[:3,3])
   target[i]=m
  assert all(np.isfinite(m).all() for m in target)
 timeacc=add(times.reshape(-1,1),'SCALAR');new={'name':anim['name'],'samplers':[],'channels':[]}
 for i,qs in quats.items():
  idx=len(new['samplers']);new['samplers'].append({'input':timeacc,'output':add(qs,'VEC4'),'interpolation':'LINEAR'});new['channels'].append({'sampler':idx,'target':{'node':i,'path':'rotation'}})
 idx=len(new['samplers']);new['samplers'].append({'input':timeacc,'output':add(hippos,'VEC3'),'interpolation':'LINEAR'});new['channels'].append({'sampler':idx,'target':{'node':tnames['hips'],'path':'translation'}});out.append(new);report.append({'clip':anim['name'],'frames':len(times),'duration':duration})
 print('RETARGETED',report[-1],flush=True)
tj['animations']=out;tj['buffers'][0]['byteLength']=len(tbin);tj.setdefault('asset',{})['generator']='XiaQing native rig retarget v6.0';tj.setdefault('extras',{})['character_name']='夏晴'
# Preserve all mesh/material/skin data; only append animation buffers.
js=json.dumps(tj,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*((-len(js))%4);tbin+=b'\0'*((-len(tbin))%4);raw=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(tbin))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(tbin),0x004e4942)+tbin
path=ROOT/'dist/assets/xiaqing_native_animated.glb';path.write_bytes(raw)
report={'version':'6.0','source':UPLOAD.name,'native_joints':len(tj['skins'][0]['joints']),'mapped_joints':len(mapping),'meshes_preserved':len(tj['meshes']),'native_skin_and_geometry_unchanged':True,'leg_scale':leg_scale,'clips':report,'bytes':len(raw)}
(ROOT/'dist/assets/native-retarget-v60-report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
