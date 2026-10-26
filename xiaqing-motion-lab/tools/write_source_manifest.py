"""Write a content inventory of the maintained site/source tree."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=[]
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.name=='SOURCE_MANIFEST.json' or '__pycache__' in p.parts:continue
 data=p.read_bytes();rows.append({'path':p.relative_to(root).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(root/'SOURCE_MANIFEST.json').write_text(json.dumps({'revision':'R6 unified wardrobe and cloth site','files':rows},ensure_ascii=False,indent=2)+'\n')
