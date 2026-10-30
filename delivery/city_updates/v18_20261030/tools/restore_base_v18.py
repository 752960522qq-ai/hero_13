"""Restore precise v17 composed inputs from a full offline repository checkout."""
from pathlib import Path
import argparse,json,hashlib,lzma,gzip,shutil,os
ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--context',action='store_true');a=ap.parse_args();repo=a.repo_root.resolve();work=a.work.resolve();update=repo/'delivery/city_updates/v18_20261030';work.mkdir(parents=True,exist_ok=True);sources=json.load(open(repo/'design/city/districts/current_sources_v17.json'))
ids=[3,8]+([1,2,4,5,6,7] if a.context else []);cache={}
for d in sources:
 if d['id'] not in ids:continue
 version=d['version'];base=repo/f'delivery/city_updates/{version}_20261029'
 if version not in cache:cache[version]=json.load(open(base/'manifest.json'))
 entry=next(x for x in cache[version]['changed_districts'] if x['id']==d['id']);pieces=[]
 for part in entry['parts']:
  b=(base/part['file']).read_bytes();assert len(b)==part['bytes'] and hashlib.sha256(b).hexdigest()==part['sha256'];pieces.append(b)
 compressed=b''.join(pieces);assert hashlib.sha256(compressed).hexdigest()==entry['compressed_sha256'];b=lzma.decompress(compressed);assert hashlib.sha256(b).hexdigest()==d['sha256'];dest=work/('baseline' if d['id'] in [3,8] else 'context')/d['file'];dest.parent.mkdir(exist_ok=True);temp=dest.with_suffix('.tmp')
 with temp.open('wb') as f:
  for i in range(0,len(b),1024*1024):f.write(b[i:i+1024*1024])
  f.flush();os.fsync(f.fileno())
 assert hashlib.sha256(temp.read_bytes()).hexdigest()==d['sha256'];temp.replace(dest);print('Verified',d['file'])
base=repo/'delivery/city_updates/v17_20261029';(work/'baseline/city_plan.json').write_bytes(gzip.decompress((base/'metadata/city_plan.json.gz').read_bytes()));(work/'baseline_districts_manifest.json').write_text(json.dumps(json.load(open(base/'manifest.json'))['resolved_districts_manifest'],ensure_ascii=False,indent=2));shutil.copy2(update/'metadata/source_inputs.json',work/'source_inputs.json')
for folder in ['sources','tools']:shutil.copytree(update/folder,work/folder,dirs_exist_ok=True)
print('Ready:',work,'— build_v18.py, validate_v18.py, export_verify_v18.py')
