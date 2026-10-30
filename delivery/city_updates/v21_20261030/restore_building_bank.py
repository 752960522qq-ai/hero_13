from pathlib import Path
import json,lzma,hashlib,tarfile,io,argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();root=Path(__file__).resolve().parent;m=json.load(open(root/'manifest.json'))['building_bank'];data=bytearray()
for part in m['parts']:
 b=(root/part['file']).read_bytes();assert len(b)==part['bytes'] and hashlib.sha256(b).hexdigest()==part['sha256'];data.extend(b)
assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256'];a.out.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(lzma.decompress(data))) as tar:tar.extractall(a.out,filter='data')
print('Restored',m['asset_count'],'building models; maximum one map instance per model.')
