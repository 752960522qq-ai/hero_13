"""Fit one heel to Xia Qing, mirror its parameters, and skin a modular pair."""
import copy,json,struct,hashlib
import numpy as np
from pathlib import Path
from glb_shoe_utils import load,acc,evaluate,ROOT,R
ASSET=ROOT/'dist/assets/wardrobe';ASSET.mkdir(exist_ok=True)
ANGLE=25.;LIFT=.05

def save(j,b,path):
 j['buffers']=[{'byteLength':len(b)}];js=json.dumps(j,ensure_ascii=False,separators=(',',':')).encode();js+=b' '*(-len(js)%4);b=bytes(b)+b'\0'*(-len(b)%4)
 Path(path).write_bytes(struct.pack('<III',0x46546c67,2,28+len(js)+len(b))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(b),0x004e4942)+b)
def append(j,b,a,typ,component=5126):
 a=np.asarray(a,dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[component]);b.extend(b'\0'*(-len(b)%4));vi=len(j.setdefault('bufferViews',[]));j['bufferViews'].append({'buffer':0,'byteOffset':len(b),'byteLength':a.nbytes});b.extend(a.tobytes());idx=len(j.setdefault('accessors',[]));entry={'bufferView':vi,'componentType':component,'count':len(a),'type':typ}
 if typ=='VEC3':entry.update(min=a.min(0).tolist(),max=a.max(0).tolist())
 j['accessors'].append(entry);return idx

def posed_world(j,b,anim=None,t=0):
 w=evaluate(j,b,anim or {'channels':[]},t);names={n.get('name'):i for i,n in enumerate(j['nodes'])}
 def descend(i):
  yield i
  for c in j['nodes'][i].get('children',[]):yield from descend(c)
 for side in ['l','r']:
  for part,angle in [('ankle',ANGLE),('ball',-ANGLE)]:
   k=names[f'{side}_leg_{part}'];rot=np.eye(4);rot[:3,:3]=R.from_euler('x',angle,degrees=True).as_matrix();d=w[k]@rot@np.linalg.inv(w[k])
   for c in descend(k):w[c]=d@w[c]
 return w

def skin_points(j,b,prim,w):
 v=acc(j,b,prim['attributes']['POSITION']);js=acc(j,b,prim['attributes']['JOINTS_0']);ws=acc(j,b,prim['attributes']['WEIGHTS_0']);sk=j['skins'][0];ib=acc(j,b,sk['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);mat=np.array([w[i]@m for i,m in zip(sk['joints'],ib)]);vh=np.c_[v,np.ones(len(v))];pv=sum(ws[:,k,None]*np.einsum('nij,nj->ni',mat[js[:,k]],vh) for k in range(4))[:,:3]
 n=acc(j,b,prim['attributes']['NORMAL']);pn=sum(ws[:,k,None]*np.einsum('nij,nj->ni',mat[js[:,k],:3,:3],n) for k in range(4));pn/=np.maximum(np.linalg.norm(pn,axis=1,keepdims=True),1e-10)
 return pv,pn

def smooth(v,a,b):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t),np.where((v>a)&(v<b),6*t*(1-t)/(b-a),0)

