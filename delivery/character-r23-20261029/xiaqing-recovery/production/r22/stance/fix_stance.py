"""R22: reuse each outfit's native heel-aware lower-body poses for armed clips.
Run under Blender; edits glTF animation channels only, leaving original geometry,
rest transforms, skin weights and all unrelated clips untouched.
"""
import bpy,struct,json,math,hashlib,subprocess,numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector
P=Path(__file__).resolve().parent;AS=(P.parents[2]/'dist/assets') if (P.parents[2]/'dist/assets').exists() else Path('/workspace/recovered-xiaqing-site/dist/assets');P.mkdir(exist_ok=True,parents=True)
STATIC={'Aim','RifleIdle','Reload','Fire','PistolIdle'}
def read(p):
 raw=p.read_bytes();ln=struct.unpack_from('<I',raw,12)[0];j=json.loads(raw[20:20+ln]);off=20+ln;blen=struct.unpack_from('<I',raw,off)[0];return j,bytearray(raw[off+8:off+8+blen])
def accessor(j,b,i):
 a=j['accessors'][i];bv=j['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];dt=np.dtype({5126:'<f4',5123:'<u2',5121:'u1'}[a['componentType']]);x=np.ndarray((a['count'],n),dt,buffer=b,offset=bv.get('byteOffset',0)+a.get('byteOffset',0),strides=(bv.get('byteStride',n*dt.itemsize),dt.itemsize)).copy();return x.reshape(-1) if n==1 else x

def make_sampler(j,b,anim,node,path,cache):
 key=(node,path)
 if key not in cache:
  channel=next((c for c in anim['channels'] if c['target'].get('node')==node and c['target']['path']==path),None)
  if channel:
   sam=anim['samplers'][channel['sampler']];cache[key]=(accessor(j,b,sam['input']),accessor(j,b,sam['output']),sam.get('interpolation','LINEAR'))
  else:
   default={'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path];cache[key]=(np.array([0.]),np.array([j['nodes'][node].get(path,default)]),'STEP')
 return cache[key]

def sample(row,t,path):
 ts,vs,interp=row
 if t<=ts[0]:return vs[0].copy()
 if t>=ts[-1]:return vs[-1].copy()
 k=int(np.searchsorted(ts,t)-1);a=float((t-ts[k])/(ts[k+1]-ts[k]))
 if interp=='STEP':return vs[k].copy()
 if path=='rotation':
  l,r=vs[k],vs[k+1];qa=Quaternion((l[3],*l[:3]));qb=Quaternion((r[3],*r[:3]));q=qa.slerp(qb,a);return np.array([q.x,q.y,q.z,q.w])
 return vs[k]*(1-a)+vs[k+1]*a

def append(j,b,data,typ):
 a=np.asarray(data,dtype='<f4');b.extend(b'\0'*((-len(b))%4));j['bufferViews'].append({'buffer':0,'byteOffset':len(b),'byteLength':a.nbytes});b.extend(a.tobytes());ac={'bufferView':len(j['bufferViews'])-1,'componentType':5126,'count':len(a),'type':typ}
 if typ=='SCALAR':ac.update(min=[float(a.min())],max=[float(a.max())])
 j['accessors'].append(ac);return len(j['accessors'])-1

def write(p,j,b):
 j['buffers'][0]['byteLength']=len(b);jb=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();jb+=b' '*((-len(jb))%4);b+=b'\0'*((-len(b))%4);p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(jb)+len(b))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(b),0x004e4942)+b)

report={}
for outfit in ['floral_dress','school_uniform']:
 file=AS/(outfit+'_xiaqing.glb');backup=P/(outfit+'_r21_original.glb')
 if not backup.exists():backup.write_bytes(subprocess.check_output(['git','-C',str(AS.parents[1]),'show','e121f5d:dist/assets/'+file.name]))
 j,b=read(backup);oldj=json.loads(json.dumps(j));oldb=bytes(b);anims={a['name']:a for a in j['animations']};nodes=[i for i,n in enumerate(j['nodes'])if 'leg_'in n.get('name','') or n.get('name')in ['root','COG','hips']];report[outfit]={}
 for label in STATIC|{'RifleRun'}:
  a=anims.get(label)
  if not a:continue
  source=anims['Run' if label=='RifleRun' else 'Idle'];cache={};source_duration=max(float(accessor(j,b,s['input'])[-1])for s in source['samplers']);duration=max(float(accessor(j,b,s['input'])[-1])for s in a['samplers']);times=np.linspace(0,duration,max(2,round(duration*30)+1)) if label=='RifleRun' else np.array([0,duration]);inp=append(j,b,times,'SCALAR')
  a['channels']=[c for c in a['channels']if c['target']['node']not in nodes]
  for node in nodes:
   for path in ['translation','rotation','scale']:
    row=make_sampler(oldj,oldb,source,node,path,cache);data=[sample(row,float(t/duration*source_duration)if label=='RifleRun'else source_duration*.5,path)for t in times];out=append(j,b,data,'VEC4'if path=='rotation'else'VEC3');si=len(a['samplers']);a['samplers'].append({'input':inp,'output':out,'interpolation':'LINEAR'});a['channels'].append({'sampler':si,'target':{'node':node,'path':path}})
  report[outfit][label]={'source_lower_body':source['name'],'source_phase': 'normalized gait'if label=='RifleRun'else.5,'changed_nodes':len(nodes),'duration':duration}
 # Original rest geometry/material/skin payload is retained exactly.
 preserved=['meshes','skins','materials','images','textures','nodes'];assert all(j[k]==oldj[k]for k in preserved);assert b[:len(oldb)]==oldb
 for name in ['Idle','Run','Walk','Jump']:
  assert anims[name]==next(x for x in oldj['animations']if x['name']==name)
 write(file,j,b)
 report[outfit]['preservation']={'mesh_rest_skin_material_image_nodes_unchanged':True,'old_binary_prefix_unchanged':True,'Idle_Run_Walk_Jump_unchanged':True}
 print('PATCHED',outfit,flush=True)
(P/'patch_report.json').write_text(json.dumps(report,indent=2))
print('PATCH_DONE',flush=True)
