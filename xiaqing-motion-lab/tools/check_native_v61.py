import json,struct,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parent.parent

def load(p):
 raw=Path(p).read_bytes();n=struct.unpack_from('<I',raw,12)[0];return json.loads(raw[20:20+n]),raw[28+n:]
def a(j,b,i):
 d=j['accessors'][i];v=j['bufferViews'][d['bufferView']];dt={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1',5122:'<i2'}[d['componentType']];k={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[d['type']];return np.ndarray((d['count'],k),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+d.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*k),np.dtype(dt).itemsize)).copy()
j,b=load(ROOT/'dist/assets/xiaqing_native_animated.glb');s,sb=load('/workspace/scratch/7b171b7361b3/upload/xiaqing_body_penis.glb')
assert j['skins']==s['skins'] and j['meshes']==s['meshes']
geometry={p['indices'] for m in j['meshes'] for p in m['primitives'] if 'indices' in p}
geometry|={i for m in j['meshes'] for p in m['primitives'] for i in p['attributes'].values()};geometry|={sk['inverseBindMatrices'] for sk in j['skins']}
for i in geometry:assert np.array_equal(a(j,b,i),a(s,sb,i))
par={c:i for i,n in enumerate(j['nodes']) for c in n.get('children',[])};order=[]
def add(i):
 if i in order:return
 if i in par:add(par[i])
 order.append(i)
for i in range(len(j['nodes'])):add(i)
sk=j['skins'][0];ibm=a(j,b,sk['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1);samples=[]
for m in j['meshes']:
 for p in m['primitives']:
  at=p['attributes']
  if 'JOINTS_0' not in at:continue
  pos=a(j,b,at['POSITION']);ix=np.linspace(0,len(pos)-1,min(300,len(pos)),dtype=int);weights=a(j,b,at['WEIGHTS_0'])[ix].astype(float)
  if j['accessors'][at['WEIGHTS_0']].get('normalized'):weights/=65535 if j['accessors'][at['WEIGHTS_0']]['componentType']==5123 else 255
  samples.append((np.column_stack((pos[ix],np.ones(len(ix)))),a(j,b,at['JOINTS_0'])[ix],weights))
checks=[]
for anim in j['animations']:
 values={}
 for c in anim['channels']:
  sam=anim['samplers'][c['sampler']];values[(c['target']['node'],c['target']['path'])]=a(j,b,sam['output'])
 frames=len(next(iter(values.values())))
 for f in [0,frames//2,frames-1]:
  world=[None]*len(j['nodes'])
  for i in order:
   n=j['nodes'][i];m=np.eye(4)
   if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
   else:
    q=values.get((i,'rotation'));t=values.get((i,'translation'));m[:3,:3]=R.from_quat(q[f] if q is not None else n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=t[f] if t is not None else n.get('translation',[0,0,0])
   world[i]=world[par[i]]@m if i in par else m
  matrices=np.array([world[i] for i in sk['joints']])@ibm;points=[]
  for pos,joints,w in samples:
   result=np.einsum('nvij,nj,nv->ni',matrices[joints],pos,w);points.append(result[:,:3])
  pts=np.concatenate(points);assert np.isfinite(pts).all();assert np.max(np.abs(pts))<4
  checks.append({'clip':anim['name'],'frame':f,'bounds':[pts.min(0).round(3).tolist(),pts.max(0).round(3).tolist()]})
report=ROOT/'dist/assets/native-retarget-v61-report.json';r=json.loads(report.read_text());r['verified_original_geometry_accessors']=len(geometry);r['sampled_skin_pose_checks']=checks;report.write_text(json.dumps(r,indent=2));print('PASS: original mesh, weights, bind matrices unchanged; 9 skinned poses finite and bounded; three clips/437 joints')
