from pathlib import Path
import json,lzma,gzip,hashlib
R=Path(__file__).resolve().parents[1];repo=R.parent/'hero_13';dst=R/'baseline';dst.mkdir(exist_ok=True)
refs=json.load(open(repo/'design/city/districts/current_sources_v20.json'))
for d in refs:
 if d['source']['type']!='incremental_district_parts':continue
 out=dst/d['file']
 if out.exists() and hashlib.sha256(out.read_bytes()).hexdigest()==d['sha256']:continue
 mp=repo/d['source']['manifest'];m=json.load(open(mp));e=next(x for x in m['changed_districts'] if x['id']==d['id']);buf=bytearray()
 for x in e['parts']:
  b=(mp.parent/x['file']).read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256'];buf.extend(b)
 assert hashlib.sha256(buf).hexdigest()==e['compressed_sha256'];b=lzma.decompress(buf);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256'];out.write_bytes(b);print('RESTORED',d['id'],len(b),flush=True)
(dst/'city_plan.json').write_bytes(gzip.decompress((repo/'delivery/city_updates/v20_20261030/metadata/city_plan.json.gz').read_bytes()))
(R/'baseline_refs.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2))
