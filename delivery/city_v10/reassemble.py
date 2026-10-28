#!/usr/bin/env python3
"""Reassemble and verify the complete v10 snapshot with Python's standard library."""
import argparse,hashlib,json,tarfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);ap.add_argument('--extract',action='store_true');a=ap.parse_args();root=Path(__file__).resolve().parent;m=json.loads((root/'manifest.json').read_text());out=(a.out or root/m['archive']).resolve();out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix(out.suffix+'.tmp')
if out.exists():raise SystemExit(f'Output already exists: {out}; use another --out path.')
h=hashlib.sha256()
try:
 with tmp.open('xb') as dst:
  for rec in m['parts']:
   ph=hashlib.sha256();size=0
   with (root/rec['file']).open('rb') as src:
    while chunk:=src.read(1024*1024):dst.write(chunk);h.update(chunk);ph.update(chunk);size+=len(chunk)
   if size!=rec['bytes'] or ph.hexdigest()!=rec['sha256']:raise ValueError('Part checksum mismatch: '+rec['file'])
 if tmp.stat().st_size!=m['archive_bytes'] or h.hexdigest()!=m['archive_sha256']:raise ValueError('Archive checksum mismatch')
 tmp.rename(out)
except BaseException:
 if tmp.exists():tmp.unlink()
 raise
print('Verified archive:',out)
if a.extract:
 directory=out.parent/m['directory']
 if directory.exists():raise SystemExit(f'Archive saved; extraction directory exists: {directory}')
 with tarfile.open(out,'r:xz') as tar:
  if hasattr(tarfile,'data_filter'):tar.extractall(out.parent,filter='data')
  else:
   for member in tar.getmembers():
    rel=Path(member.name)
    if rel.is_absolute() or '..' in rel.parts or not (member.isfile() or member.isdir()):raise ValueError('Unsafe archive member')
   tar.extractall(out.parent)
 for rec in m['files']:
  f=directory/rec['file'];fh=hashlib.sha256()
  with f.open('rb') as src:
   while chunk:=src.read(1024*1024):fh.update(chunk)
  if f.stat().st_size!=rec['bytes'] or fh.hexdigest()!=rec['sha256']:raise ValueError('Extracted file mismatch: '+rec['file'])
 print('Verified all extracted files:',directory)
