import json,struct,copy,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
j=None;binary=bytearray();anims=[]
for label in ['Idle','Walk','Run']:
 raw=(ROOT/'source-motions'/f'{label}_raw.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0];s=json.loads(raw[20:20+n]);b=raw[28+n:]
 if j is None:j=copy.deepcopy(s);j['accessors']=[];j['bufferViews']=[]
 else:
  assert j['nodes']==s['nodes'],'Source bind poses differ'
 ao=len(j['accessors']);vo=len(j['bufferViews']);binary.extend(b'\0'*((-len(binary))%4));offset=len(binary);binary.extend(b)
 for v in s['bufferViews']:v['byteOffset']=v.get('byteOffset',0)+offset;j['bufferViews'].append(v)
 for a in s['accessors']:a['bufferView']+=vo;j['accessors'].append(a)
 for a in s['animations']:
  a['name']=label
  for sam in a['samplers']:sam['input']+=ao;sam['output']+=ao
  anims.append(a)
j['animations']=anims;j['buffers']=[{'byteLength':len(binary)}];js=json.dumps(j,separators=(',',':')).encode();js+=b' '*((-len(js))%4);binary+=b'\0'*((-len(binary))%4)
(ROOT/'source-models/current_motion_reference.glb').write_bytes(struct.pack('<III',0x46546c67,2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary)
for label,name in [('Idle','girl_Idle(1).fbx'),('Walk','girl Walk(1).fbx'),('Run','Running(4).fbx')]:
 dest={'Idle':'girl_Idle.fbx','Walk':'girl_Walk.fbx','Run':'Running.fbx'}[label];shutil.copyfile(Path('/workspace/scratch/7b171b7361b3/upload')/name,ROOT/'source-motions'/dest)
print('Merged only the three raw uploaded clips; bind poses identical.')
