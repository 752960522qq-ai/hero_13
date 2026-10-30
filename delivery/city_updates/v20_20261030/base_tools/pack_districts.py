from pathlib import Path
import json,hashlib,lzma,concurrent.futures
R=Path(__file__).resolve().parents[1];repo=R.parent/'hero_13';out=repo/'delivery/city_updates/v19_20261030';(out/'districts').mkdir(parents=True,exist_ok=True)
validation=json.load(open(R/'validation/districts_validation.json'));assert validation['status']=='PASS';refs=json.load(open(repo/'design/city/districts/current_sources_v18.json'));oldman=json.load(open(repo/'delivery/city_updates/v18_20261030/manifest.json'));resolved=json.load(open(R/'districts/districts_manifest.json'));counts={4:50,8:11,9:20,14:13}
def compress(d):
 prior=next(x for x in refs if x['id']==d);new=next(x for x in resolved['districts'] if x['id']==d);p=R/'districts'/prior['file'];b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==new['sha256'];compressed=lzma.compress(b,preset=6);parts=[]
 for n,i in enumerate(range(0,len(compressed),8*1024*1024)):
  raw=compressed[i:i+8*1024*1024];name='districts/'+p.name+f'.xz.part{n:03}';(out/name).write_bytes(raw);parts.append({'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 for old in (out/'districts').glob(p.name+'.xz.part*'):
  if str(old.relative_to(out)) not in {q['file'] for q in parts}:old.unlink()
 return {'id':d,'name':new['name'],'file':p.name,'bytes':len(b),'sha256':new['sha256'],'base_sha256':prior['sha256'],'compression':'xz','compressed_bytes':len(compressed),'compressed_sha256':hashlib.sha256(compressed).hexdigest(),'parts':parts,'building_units_before':prior['building_units'],'building_units_after':counts[d],'change_notes':'v19: labelled extracted buildings, neighborhood courtyards, continuous entrance grading, road-cut closures'}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:changed=list(ex.map(compress,[4,8,9,14]))
allrows=[];current=[]
for old in refs:
 new=next((x for x in changed if x['id']==old['id']),None);allrows.append({'id':old['id'],'file':old['file'],'base_sha256':old['sha256'],'sha256':new['sha256'] if new else old['sha256'],'changed':new is not None})
 if new:current.append({**old,'version':'v19','bytes':new['bytes'],'sha256':new['sha256'],'building_units':counts[old['id']],'source':{'type':'incremental_district_parts','manifest':'delivery/city_updates/v19_20261030/manifest.json'}})
 else:current.append(old)
manifest={'schema':'hero13.city.incremental.v19','update_id':'v19_20261030','date':'2026-10-30','baseline_version':'v18','baseline_commit':'6a69d2b7d79dbc7d35570fd13cc96216e7472fad','changed_district_ids':[4,8,9,14],'unchanged_district_ids':[i for i in range(1,19) if i not in [4,8,9,14]],'changed_districts':changed,'all_districts':allrows,'resolved_districts_manifest':resolved,'city_building_units':547,'oldtown_street_buildings':120,'oldtown_rear_buildings':80,'new_asset_types_used':24,'new_source_instances':41,'usable_extracted_types':26,'replaced_placeholder_units':37}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(R/'current_sources_v19.json').write_text(json.dumps(current,ensure_ascii=False,indent=2));s=(repo/'delivery/city_updates/v18_20261030/reassemble.py').read_text().replace('v17','v18').replace('v18 set','v19 set').replace('in your v19 set','in your v18 set');(out/'reassemble.py').write_text(s)
print('PACKED',[(d['id'],d['compressed_bytes'],len(d['parts'])) for d in changed],flush=True)
