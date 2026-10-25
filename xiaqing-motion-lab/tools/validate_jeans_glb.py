import struct,json,numpy as np
p='/workspace/sites/xiaqing-motion-lab/dist/assets/xiaqing_trousers_rigged.glb';f=open(p,'rb');f.read(12);n,t=struct.unpack('<II',f.read(8));j=json.loads(f.read(n));n,t=struct.unpack('<II',f.read(8));blob=f.read(n)
def arr(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];d={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];return np.frombuffer(blob,dtype=d,count=a['count']*dim,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],dim)
assert len(j['skins'])==1 and len(j['skins'][0]['joints'])==26
assert {a['name'] for a in j['animations']}=={'Idle','Walk','Run','HandTest','ArmRaise'}
for a in j['animations']:
 for s in a['samplers']:
  assert np.isfinite(arr(s['output'])).all()
 print(a['name'],'duration',round(float(max(arr(s['input']).max() for s in a['samplers'])),3))
for m in j['meshes']:
 for p in m['primitives']:
  w=arr(p['attributes']['WEIGHTS_0']);assert np.max(abs(w.sum(axis=1)-1))<1e-4
  assert arr(p['attributes']['JOINTS_0']).max()<26
print('PASS: all skinned vertices normalized, 5 valid animations, 26 bones')
