"""Restore the exact v15 inputs, v16 source models and scripts without network access."""
from pathlib import Path
import argparse,json,hashlib,lzma,gzip,shutil
ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--context',action='store_true',help='Also restore unchanged main-island districts 01-05 for rendering');a=ap.parse_args();repo=a.repo_root.resolve();update=repo/'delivery/city_updates/v16_20261029';base=repo/'delivery/city_updates/v15_20261029';work=a.work.resolve();work.mkdir(parents=True,exist_ok=True)
def digest(b):return hashlib.sha256(b).hexdigest()
m=json.load(open(base/'manifest.json'));ids=[6,7,8]+([1,2,3,4,5] if a.context else [])
for d in m['changed_districts']:
 if d['id'] not in ids:continue
 chunks=[]
 for part in d['parts']:
  data=(base/part['file']).read_bytes();assert len(data)==part['bytes'] and digest(data)==part['sha256'],part['file'];chunks.append(data)
 compressed=b''.join(chunks);assert digest(compressed)==d['compressed_sha256'];data=lzma.decompress(compressed);assert len(data)==d['bytes'] and digest(data)==d['sha256'];dest=work/('baseline' if d['id'] in [6,7,8] else 'context')/d['file'];dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
(work/'baseline/city_plan.json').write_bytes(gzip.decompress((base/'metadata/city_plan.json.gz').read_bytes()));shutil.copy2(base/'manifest.json',work/'v15_manifest.json')
for folder in ['sources','tools']:shutil.copytree(update/folder,work/folder,dirs_exist_ok=True)
for n in ['layout_v16.json','asset_inspection.json','black_edge_diagnosis.json']:shutil.copy2(update/'metadata'/n,work/n)
for asset in json.load(open(update/'metadata/asset_pool.json')):assert digest((work/asset['file']).read_bytes())==asset['sha256'],asset['file']
print('Restored verified v15 districts and v16 editing inputs to',work)
print('Run Blender with --background --python',work/'tools/build_v16.py')
