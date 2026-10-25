# Restore sub-millimeter cap triangles omitted by Blender's glTF tessellator.
# Reuse existing vertices and all their UV/skin attributes; source .blend stays manifold.
import struct,json,numpy as np
from collections import Counter,defaultdict
path='/workspace/sites/xiaqing-motion-lab/dist/assets/xiaqing_rigged.glb'
f=open(path,'rb');f.read(12);n,t=struct.unpack('<II',f.read(8));j=json.loads(f.read(n));n,t=struct.unpack('<II',f.read(8));blob=bytearray(f.read(n))
def read(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
 return np.frombuffer(blob,dtype=dtype,count=a['count']*dim,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],dim).copy()
patched=[]
for mesh in j['meshes']:
 keys={};reverse={};edges=Counter();directions={};prims=[]
 for p in mesh['primitives']:
  local={};lookup={}
  for i,v in enumerate(read(p['attributes']['POSITION'])):
   key=tuple(v.tolist());g=keys.setdefault(key,len(keys));reverse[g]=key;local[i]=g;lookup[g]=i
  indices=read(p['indices']).ravel();prims.append((p,indices,lookup))
  for a,b,c in indices.reshape(-1,3):
   tri=[local[a],local[b],local[c]]
   if len(set(tri))!=3:continue
   for k in range(3):
    a,b=tri[k],tri[(k+1)%3];edge=tuple(sorted((a,b)));edges[edge]+=1;directions[edge]=(a,b)
 boundary=set(e for e,n in edges.items() if n==1);extra=defaultdict(list)
 while boundary:
  todo=[boundary.pop()];group=[]
  while todo:
   e=todo.pop();group.append(e)
   neighbors=[n for n in boundary if set(n)&set(e)]
   for n in neighbors:boundary.remove(n);todo.append(n)
  vertices=set(x for e in group for x in e)
  assert len(group)==3 and len(vertices)==3,(mesh['name'],group)
  a,b=directions[group[0]];c=next(v for v in vertices if v not in [a,b]);tri=[b,a,c]
  found=False
  for index,(p,indices,lookup) in enumerate(prims):
   if all(v in lookup for v in tri):extra[index].extend(lookup[v] for v in tri);found=True;break
  assert found,'Cap vertices span incompatible material charts'
  patched.append({'mesh':mesh['name'],'coordinates':[reverse[x] for x in tri]})
 for index,extra_indices in extra.items():
  p,indices,_=prims[index];data=np.concatenate([indices,np.array(extra_indices,dtype=np.uint32)]).astype('<u4');offset=(len(blob)+3)//4*4;blob.extend(b'\0'*(offset-len(blob)));blob.extend(data.tobytes())
  j['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':data.nbytes,'target':34963});j['accessors'].append({'bufferView':len(j['bufferViews'])-1,'componentType':5125,'count':len(data),'type':'SCALAR','min':[int(data.min())],'max':[int(data.max())]});p['indices']=len(j['accessors'])-1
j['buffers'][0]['byteLength']=len(blob);metadata=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();metadata+=b' '*((-len(metadata))%4);blob+=b'\0'*((-len(blob))%4)
with open(path,'wb') as f:f.write(struct.pack('<III',0x46546c67,2,12+8+len(metadata)+8+len(blob)));f.write(struct.pack('<II',len(metadata),0x4e4f534a));f.write(metadata);f.write(struct.pack('<II',len(blob),0x004e4942));f.write(blob)
print('RESTORED_EXPORTED_CAPS',len(patched))
