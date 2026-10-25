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
