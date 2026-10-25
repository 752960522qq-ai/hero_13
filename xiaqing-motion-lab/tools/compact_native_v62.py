import struct,json,io,hashlib
from pathlib import Path
from PIL import Image
p=Path(__file__).resolve().parent.parent/'dist/assets/xiaqing_native_animated.glb';raw=p.read_bytes();n=struct.unpack_from('<I',raw,12)[0];j=json.loads(raw[20:20+n]);start=28+n;binary=raw[start:];new=bytearray();images={im['bufferView']:im for im in j.get('images',[])};changed=0;protected=[]
for i,v in enumerate(j['bufferViews']):
 b=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
 if i in images:
  im=images[i];img=Image.open(io.BytesIO(b));alpha=img.getchannel('A').getextrema() if 'A' in img.getbands() else (255,255)
  if alpha==(255,255):
   out=io.BytesIO();img.convert('RGB').save(out,format='JPEG',quality=92,subsampling=0,optimize=True);candidate=out.getvalue()
   if len(candidate)<len(b):b=candidate;im['mimeType']='image/jpeg';changed+=1
 else:protected.append(hashlib.sha256(b).hexdigest())
 new.extend(b'\0'*((-len(new))%4));v['byteOffset']=len(new);v['byteLength']=len(b);new.extend(b)
j['buffers'][0]['byteLength']=len(new);js=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*((-len(js))%4);new+=b'\0'*((-len(new))%4)
p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(js)+len(new))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(new),0x004e4942)+new)
r=p.parent/'native-retarget-v62-report.json';report=json.loads(r.read_text());report['texture_compression']={'jpeg_quality':92,'images_reencoded':changed,'dimensions_preserved':True,'alpha_preserved':True};report['bytes']=p.stat().st_size;report['non_image_buffers_preserved']=True;r.write_text(json.dumps(report,indent=2));print('COMPACTED',p.stat().st_size,'images',changed)
assert p.stat().st_size<26214400,'Site single-file limit'
