"""Refresh SHA256 inventory for this outfit delivery only."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
files=[]
for f in sorted(P.rglob('*')):
 if not f.is_file() or f.name=='INVENTORY.json' or '__pycache__' in f.parts or f.suffix=='.log' or f.name.endswith('_candidate.blend') or f.name=='source_inspect.blend':continue
 files.append({'path':f.relative_to(P).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(P/'INVENTORY.json').write_text(json.dumps({'format':1,'revision':'R7_local','files':files,'total_bytes':sum(f['bytes'] for f in files)},ensure_ascii=False,indent=2)+'\n')
print('INVENTORY',len(files),sum(f['bytes'] for f in files))
