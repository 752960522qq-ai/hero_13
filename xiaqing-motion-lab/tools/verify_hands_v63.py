"""Verify actual glTF animation evaluation, native geometry, and finger directions."""
import json,struct,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R,Slerp
ROOT=Path(__file__).resolve().parent.parent

def load(p):
 raw=Path(p).read_bytes();n=struct.unpack_from('<I',raw,12)[0];return json.loads(raw[20:20+n]),raw[28+n:]
def acc(j,b,i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];dt={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']];k={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];return np.ndarray((a['count'],k),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*k),np.dtype(dt).itemsize)).copy()
def evaluate(j,b,anim,t):
 par={c:i for i,n in enumerate(j['nodes']) for c in n.get('children',[])};trs=[]
 for n in j['nodes']:
  if 'matrix' in n:
   m=np.array(n['matrix']).reshape(4,4).T;scale=np.linalg.norm(m[:3,:3],axis=0);trs.append([m[:3,3],R.from_matrix(m[:3,:3]/scale).as_quat(),scale])
  else:trs.append([np.array(n.get('translation',[0,0,0])),np.array(n.get('rotation',[0,0,0,1])),np.array(n.get('scale',[1,1,1]))])
 for c in anim['channels']:
  sam=anim['samplers'][c['sampler']];ts=acc(j,b,sam['input'])[:,0];v=acc(j,b,sam['output']);i=c['target']['node'];path=c['target']['path']
  if path=='rotation':trs[i][1]=Slerp(ts,R.from_quat(v))([np.clip(t,ts[0],ts[-1])]).as_quat()[0] if len(ts)>1 else v[0]
  elif path in ('translation','scale'):trs[i][0 if path=='translation' else 2]=np.array([np.interp(t,ts,v[:,k]) for k in range(3)])
 world={}
 def calc(i):
  if i not in world:
   p,q,sc=trs[i];m=np.eye(4);m[:3,:3]=R.from_quat(q).as_matrix()@np.diag(sc);m[:3,3]=p;world[i]=calc(par[i])@m if i in par else m
  return world[i]
 for i in range(len(trs)):calc(i)
 return world
j,b=load(ROOT/'dist/assets/xiaqing_native_animated.glb');old,ob=load('/tmp/xiaqing_before63.glb');original,origbin=load('/workspace/scratch/7b171b7361b3/upload/xiaqing_body_penis.glb')
assert j['skins']==original['skins'] and j['meshes']==original['meshes']
ids={i for mesh in j['meshes'] for p in mesh['primitives'] for i in p['attributes'].values()}|{sk['inverseBindMatrices'] for sk in j['skins']}
for i in ids:assert np.array_equal(acc(j,b,i),acc(original,origbin,i))
byname={n.get('name'):i for i,n in enumerate(j['nodes'])};maxerr=0;checks=0
for anim in j['animations']:
 prev=next(a for a in old['animations'] if a['name']==anim['name']);oldtracks={(c['target']['node'],c['target']['path']):prev['samplers'][c['sampler']] for c in prev['channels']}
 for c in anim['channels']:
  i=c['target']['node'];name=j['nodes'][i].get('name','');assert 'matrix' not in j['nodes'][i]
  if '_hand_' not in name and not name.endswith('_arm_wrist'):
   sam=anim['samplers'][c['sampler']];prior=oldtracks[(i,c['target']['path'])];assert np.array_equal(acc(j,b,sam['output']),acc(old,ob,prior['output'])),name
 sj,sb=load(ROOT/'source-motions'/f"{anim['name']}_raw.glb");sn={n.get('name'):i for i,n in enumerate(sj['nodes'])};sa=sj['animations'][0];times=acc(j,b,anim['samplers'][0]['input'])[:,0]
 for t in [times[0],times[len(times)//2],times[-1]]:
  tw=evaluate(j,b,anim,float(t));sw=evaluate(sj,sb,sa,float(t))
  for side,long in [('l','Left'),('r','Right')]:
   for finger,source in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('little','Pinky')]:
    for k in range(3):
     nk=k+1 if finger in ['ring','little'] else k;ti=byname[f'{side}_hand_{finger}_{nk}'];si=sn[f'{long}Hand{source}{k+1}'];a=tw[ti][:3,0]*(1 if side=='l' else -1);a/=np.linalg.norm(a);v=sw[si][:3,1];v/=np.linalg.norm(v);err=np.degrees(np.arccos(np.clip(a@v,-1,1)));maxerr=max(maxerr,err);assert err<.02,(anim['name'],side,finger,k,err);checks+=1
r=ROOT/'dist/assets/native-retarget-v63-report.json';report=json.loads(r.read_text());report['hand_validation']={'finger_directions_checked':checks,'max_source_direction_error_degrees':float(maxerr),'non_hand_animation_unchanged':True,'native_mesh_weights_bind_matrices_unchanged':True,'animated_nodes_use_trs':True};r.write_text(json.dumps(report,indent=2));print('PASS',report['hand_validation'])
