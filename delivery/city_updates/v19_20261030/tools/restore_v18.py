"""Restore only verified current districts needed for a city change or its preview."""
from pathlib import Path
import json,hashlib,lzma,gzip,sys,os
R=Path(__file__).resolve().parents[1];repo=Path(os.environ.get('HERO13_REPO_ROOT',str(R.parent/'hero_13')));dest=R/'baseline';dest.mkdir(exist_ok=True)
refs=json.load(open(repo/'design/city/districts/current_sources_v18.json'))
ids=[int(x) for x in sys.argv[1:]] if len(sys.argv)>1 else list(range(1,17))
for d in refs:
 if d['id'] not in ids:continue
 out=dest/d['file']
 if out.exists() and hashlib.sha256(out.read_bytes()).hexdigest()==d['sha256']:continue
 src=d['source'];manifestpath=repo/src['manifest'];m=json.load(open(manifestpath));e=next(x for x in m['changed_districts'] if x['id']==d['id']);compressed=bytearray()
 for part in e['parts']:
  bb=(manifestpath.parent/part['file']).read_bytes();assert len(bb)==part['bytes'] and hashlib.sha256(bb).hexdigest()==part['sha256'];compressed.extend(bb)
 assert hashlib.sha256(compressed).hexdigest()==e['compressed_sha256'];bb=lzma.decompress(compressed);assert hashlib.sha256(bb).hexdigest()==d['sha256'];out.write_bytes(bb);print('RESTORED',d['id'],len(bb),flush=True)
(dest/'city_plan.json').write_bytes(gzip.decompress((repo/'delivery/city_updates/v18_20261030/metadata/city_plan.json.gz').read_bytes()))
