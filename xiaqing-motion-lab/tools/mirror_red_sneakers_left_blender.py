"""Mirror the supplied right-foot asset about its local X plane in Blender."""
import bpy, json, struct
import numpy as np
from pathlib import Path
root=Path(__file__).resolve().parent.parent
src=root/'source-models/red_sneakers_original.glb'
raw=src.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
j=json.loads(raw[20:20+size]);data=bytearray(raw[28+size:])
def access(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];k={'VEC3':3,'SCALAR':1}[a['type']];dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
 return np.ndarray((a['count'],k),dtype=dt,buffer=data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*k),np.dtype(dt).itemsize))
seen=set()
for mesh in j['meshes']:
 for p in mesh['primitives']:
  for kind in ['POSITION','NORMAL']:
   i=p['attributes'][kind]
   if i in seen:continue
   seen.add(i);a=access(i);a[:,0]*=-1
   if kind=='POSITION':j['accessors'][i].update(min=a.min(0).tolist(),max=a.max(0).tolist())
  i=p['indices']
  if i not in seen:
   seen.add(i);a=access(i).reshape(-1,3);a[:]=a[:,[0,2,1]]
j['asset']['generator']='Blender right-to-left foot mirror; UV preserved; winding corrected'
text=json.dumps(j,separators=(',',':')).encode();text+=b' '*(-len(text)%4)
out=root/'source-models/red_sneakers_left.glb'
out.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(data))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(data),0x004e4942)+data)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(out))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'source-models/red_sneakers_left.blend'))
print('LEFT_MIRROR_READY',out)
