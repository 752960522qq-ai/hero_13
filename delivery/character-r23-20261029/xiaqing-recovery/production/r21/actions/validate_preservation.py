import json,struct,hashlib
from pathlib import Path
P=Path(__file__).parent;A=Path('/workspace/recovered-xiaqing-site/dist/assets')
def read(p):
 b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0];return json.loads(b[20:20+n]),b[28+n:]
out={}
for old in (P/'originals').glob('*.glb'):
 j,b=read(old);new,nb=read(A/old.name)
 checks={key:new[key]==j[key] for key in ['meshes','nodes','skins','materials','textures','images']}
 checks['old_animation_channels_unchanged']=all(a in new['animations'] for a in j['animations'])
 checks['original_binary_bytes_preserved']=nb[:len(b)]==b
 checks['new_clips']=sorted(a['name'] for a in new['animations'] if a['name'] not in [a['name'] for a in j['animations']])
 assert all(v for k,v in checks.items() if k!='new_clips'),(old.name,checks)
 out[old.name]=checks
(P/'preservation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
