"""Restore the precise v16 editing inputs from a full repository checkout."""
from pathlib import Path
import argparse,json,hashlib,lzma,gzip,shutil
ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--context',action='store_true');a=ap.parse_args();repo=a.repo_root.resolve();work=a.work.resolve();update=repo/'delivery/city_updates/v17_20261029';work.mkdir(parents=True,exist_ok=True)
for version,ids in [('v15',[2,3,4]+([1,5] if a.context else [])),('v16',[6,7]+([8] if a.context else []))]:
 base=repo/f'delivery/city_updates/{version}_20261029';m=json.load(open(base/'manifest.json'))
 for d in m['changed_districts']:
  if d['id'] not in ids:continue
  chunks=[]
  for part in d['parts']:
   b=(base/part['file']).read_bytes();assert len(b)==part['bytes'] and hashlib.sha256(b).hexdigest()==part['sha256'];chunks.append(b)
  compressed=b''.join(chunks);assert hashlib.sha256(compressed).hexdigest()==d['compressed_sha256'];b=lzma.decompress(compressed);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256'];dest=work/('baseline' if d['id'] in [2,3,4,6,7] else 'context')/d['file'];dest.parent.mkdir(exist_ok=True);dest.write_bytes(b);print('Verified',d['file'])
base=repo/'delivery/city_updates/v16_20261029';(work/'baseline/city_plan.json').write_bytes(gzip.decompress((base/'metadata/city_plan.json.gz').read_bytes()));(work/'v16_districts_manifest.json').write_text(json.dumps(json.load(open(base/'manifest.json'))['resolved_districts_manifest'],ensure_ascii=False,indent=2));shutil.copy2(update/'metadata/layout_v17.json',work/'layout_v17.json')
for folder in ['sources','tools']:shutil.copytree(update/folder,work/folder,dirs_exist_ok=True)
print('Ready:',work,'— prepare_scene_v17.py, build_v17.py, validate_v17.py, export_verify_v17.py')
