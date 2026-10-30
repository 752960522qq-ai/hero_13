"""Restore the 26 complete GLBs from the verified solid building bank."""
from pathlib import Path
import argparse,json,hashlib,tarfile,lzma,io
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('restored_building_bank'));a=ap.parse_args();root=Path(__file__).resolve().parent/'building_bank';m=json.load(open(root/'manifest.json'));b=bytearray()
for part in m['parts']:
 p=root/part['file'];q=p.read_bytes();assert len(q)==part['bytes'] and hashlib.sha256(q).hexdigest()==part['sha256'];b.extend(q)
assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256'];dest=a.out.resolve();dest.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(b),mode='r:xz') as tf:
 for member in tf.getmembers():
  p=(dest/member.name).resolve();assert p.is_relative_to(dest) and not member.issym() and not member.islnk()
 tf.extractall(dest,filter='data')
for row in m['models']:
 p=dest/row['file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
print('PASS: 26 building models and provenance annotations restored:',dest)
