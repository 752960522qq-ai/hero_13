"""Verify and restore changed GLBs, optionally resolving a complete district set.

Python standard library only. The v14 baseline is read, never modified.
"""
from pathlib import Path
import argparse,hashlib,json,lzma,shutil,tempfile,os
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
 return h.hexdigest()
def safe_child(root,name):
 p=(root/name).resolve()
 if not p.is_relative_to(root.resolve()):raise ValueError('Unsafe path in manifest: '+name)
 return p
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--baseline-dir',type=Path,help='v14 districts directory, for a complete 18-file resolved set');ap.add_argument('--out',type=Path,default=Path('resolved_districts'));a=ap.parse_args();root=Path(__file__).resolve().parent;manifest=json.loads((root/'manifest.json').read_text());out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if a.baseline_dir:
  base=a.baseline_dir.resolve()
  if out==base:raise ValueError('Choose a new output directory; the v14 baseline must be preserved')
  for d in manifest['all_districts']:
   file=safe_child(base,d['file']);assert file.is_file() and sha(file)==d['base_sha256'],('Baseline mismatch',d['file'])
  print('PASS: all 18 v14 baseline files verified')
 for d in manifest['changed_districts']:
  dest=safe_child(out,d['file'])
  if dest.exists():
   assert sha(dest)==d['sha256'],('Existing output differs; choose an empty output directory',d['file']);print('Already verified:',d['file']);continue
  fd,tmpname=tempfile.mkstemp(prefix='district_',suffix='.xz',dir=out);os.close(fd);compressed=Path(tmpname);decoded=compressed.with_suffix('.glb.tmp')
  try:
   h=hashlib.sha256();size=0
   with compressed.open('wb') as f:
    for part in d['parts']:
     file=safe_child(root,part['file']);assert file.stat().st_size==part['bytes'] and sha(file)==part['sha256'],('Part mismatch',part['file'])
     with file.open('rb') as src:
      for block in iter(lambda:src.read(1024*1024),b''):f.write(block);h.update(block);size+=len(block)
   assert size==d['compressed_bytes'] and h.hexdigest()==d['compressed_sha256'],('Compressed file mismatch',d['file'])
   with lzma.open(compressed,'rb') as src,decoded.open('wb') as f:shutil.copyfileobj(src,f,1024*1024)
   assert decoded.stat().st_size==d['bytes'] and sha(decoded)==d['sha256'],('GLB mismatch',d['file'])
   decoded.replace(dest);print('PASS:',d['file'],d['bytes'],'bytes')
  finally:
   compressed.unlink(missing_ok=True);decoded.unlink(missing_ok=True)
 if a.baseline_dir:
  changed={d['id'] for d in manifest['changed_districts']}
  for d in manifest['all_districts']:
   if d['id'] in changed:continue
   dest=safe_child(out,d['file'])
   if dest.exists():assert sha(dest)==d['sha256'],('Existing output differs',d['file'])
   else:shutil.copy2(safe_child(base,d['file']),dest)
  for d in manifest['all_districts']:assert sha(safe_child(out,d['file']))==d['sha256'],('Resolved set mismatch',d['file'])
  (out/'districts_manifest.json').write_text(json.dumps(manifest['resolved_districts_manifest'],ensure_ascii=False,indent=2))
  print('PASS: complete 18-district v15 set resolved; original v14 baseline untouched')
 else:print('PASS: changed districts restored; replace only the changed matching districts in your v15 set')
if __name__=='__main__':main()
