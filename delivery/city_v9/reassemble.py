#!/usr/bin/env python3
"""Join city v9 archive parts and verify their byte identity and ZIP CRC."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);ap.add_argument('--extract',action='store_true');a=ap.parse_args()
root=Path(__file__).resolve().parent;manifest=json.loads((root/'manifest.json').read_text());out=(a.out or root/'huizhou_city_v9.zip').resolve();tmp=out.with_suffix(out.suffix+'.tmp');out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise SystemExit(f'Output already exists: {out}; choose a different --out path.')
whole=hashlib.sha256()
try:
 with tmp.open('xb') as target:
  for rec in manifest['parts']:
   path=root/rec['file'];h=hashlib.sha256();total=0
   with path.open('rb') as source:
    while chunk:=source.read(1024*1024):target.write(chunk);whole.update(chunk);h.update(chunk);total+=len(chunk)
   if total!=rec['bytes'] or h.hexdigest()!=rec['sha256']:raise ValueError(f'Part mismatch: {path.name}')
 if tmp.stat().st_size!=manifest['archive_bytes'] or whole.hexdigest()!=manifest['archive_sha256']:raise ValueError('Archive checksum mismatch')
 with zipfile.ZipFile(tmp) as archive:
  bad=archive.testzip()
  if bad:raise ValueError(f'ZIP CRC mismatch: {bad}')
 tmp.rename(out)
except BaseException:
 if tmp.exists():tmp.unlink()
 raise
print(f'Verified: {out}')
if a.extract:
 destination=out.parent/'huizhou_city_v9'
 if destination.exists():raise SystemExit(f'Archive saved; extraction directory already exists: {destination}')
 with zipfile.ZipFile(out) as archive:archive.extractall(destination)
 print(f'Extracted: {destination}')
