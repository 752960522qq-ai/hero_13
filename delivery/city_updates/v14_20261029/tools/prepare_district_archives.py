"""Compress and split only the six changed districts, never the full city."""
from pathlib import Path
import concurrent.futures,hashlib,json,lzma,shutil,argparse
ap=argparse.ArgumentParser();ap.add_argument('--districts',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
m=json.loads((a.districts/'districts_manifest.json').read_text());chosen=[d for d in m['districts'] if d['id'] in m['exported_district_ids']];PART=8*1024*1024
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def pack(d):
 src=a.districts/d['file'];raw_sha=sha(src);assert raw_sha==d['sha256'];xz=a.out/(src.name+'.xz')
 with src.open('rb') as f,lzma.open(xz,'wb',preset=6) as out:shutil.copyfileobj(f,out,1024*1024)
 parts=[]
 with xz.open('rb') as f:
  for i,b in enumerate(iter(lambda:f.read(PART),b'')):
   p=a.out/(xz.name+f'.part{i:02d}');p.write_bytes(b);parts.append({'file':'districts/'+p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
 row={'id':d['id'],'name':d['name'],'file':d['file'],'bytes':src.stat().st_size,'sha256':raw_sha,'compression':'xz','compressed_bytes':xz.stat().st_size,'compressed_sha256':sha(xz),'parts':parts};xz.unlink()
 print('DISTRICT_PACKED',d['id'],row['bytes'],row['compressed_bytes'],len(parts),flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(pack,chosen))
report={'schema':'hero13.city.changed-district-archives.v1','districts':rows,'part_count':sum(len(d['parts']) for d in rows),'raw_bytes':sum(d['bytes'] for d in rows),'compressed_bytes':sum(d['compressed_bytes'] for d in rows)}
(a.out.parent/'district_archives.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('DELTA_ARCHIVES_READY',json.dumps({k:v for k,v in report.items() if k!='districts'}),flush=True)
