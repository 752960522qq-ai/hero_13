from pathlib import Path
import json,struct,hashlib,shutil
from PIL import Image
R=Path(__file__).resolve().parents[1];hd=R/'textures/S04_FillerBuildings1_enhanced.png';hd.parent.mkdir(exist_ok=True)
source=R.parent/'generated_images/exec-3b787477-405f-4291-ac53-927799aa1ba7.png';shutil.copy2(source,hd)
catalog=json.load(open(R/'asset_catalog.json'));changed=[]
for a in catalog:
 p=R/'extracted'/a['file'];b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);binary=b[28+n:];targets=set()
 for m in d.get('materials',[]):
  if m.get('name','').startswith('FillerBuildings1'):
   t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
   if t:targets.add(d['images'][d['textures'][t['index']]['source']]['bufferView'])
 if targets:
  out=bytearray()
  for i,v in enumerate(d['bufferViews']):
   raw=hd.read_bytes() if i in targets else binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
   out.extend(b'\0'*((-len(out))%4));v['byteOffset']=len(out);v['byteLength']=len(raw);out.extend(raw)
  for im in d['images']:
   if im.get('bufferView') in targets:im['mimeType']='image/png'
  d['buffers'][0]['byteLength']=len(out);out.extend(b'\0'*((-len(out))%4));jb=json.dumps(d,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4);data=struct.pack('<III',0x46546c67,2,28+len(jb)+len(out))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(out),0x004e4942)+out;p.write_bytes(data)
  a['original_extracted_sha256']=a['sha256'];a['sha256']=hashlib.sha256(data).hexdigest();a['bytes']=len(data);a['texture_policy']='FillerBuildings1 atlas detail reconstructed with image generation; other images retain source pixels';a['enhancement']={'original_pixels':[1024,1024],'enhanced_pixels':list(Image.open(hd).size),'file':hd.name,'method':'imagegen UV-atlas detail reconstruction; no UV changes','generated_sha256':hashlib.sha256(hd.read_bytes()).hexdigest()};changed.append(a['asset_id'])
 if a['asset_id']=='S06-B01':a['status']='rejected_black_source_albedo';a['reason_zh']='原文件铸铁立面基础颜色图为纯黑，缺少有效外观信息，本轮不放入地图。'
(R/'asset_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2));(R/'audit/texture_enhancement.json').write_text(json.dumps({'changed_assets':changed,'original_pixels':[1024,1024],'enhanced_pixels':list(Image.open(hd).size),'uv_geometry_unchanged':True,'not_an_original_detail_recovery':True},ensure_ascii=False,indent=2));print(changed)
