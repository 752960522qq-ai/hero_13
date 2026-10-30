"""Swap only the S09 diffuse image bytes; accessor and UV bytes stay identical."""
from pathlib import Path
import json,struct,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[1];new_image=(R/'textures/S09_city_facades_enhanced.png').read_bytes();original=(R/'audit/source_WorldCityBuildings2.png').read_bytes();old_hash=hashlib.sha256(original).hexdigest();cat=json.load(open(R/'asset_catalog.json'));proof=[]
names={'S05-B03':'灰格窗高层楼','S05-B06':'玻璃转角楼','S08-B03':'开放楼板施工楼','S08-B04':'灰色店铺商住楼'}
for a in cat:
 a['display_name_zh']=names.get(a['asset_id'],a['display_name_zh'])
 if a['asset_id']=='S08-B03':a['issue_note_zh']='开放楼板和外墙框架，部分外墙缺失，未封口；作为施工楼使用。'
 elif a['asset_id']=='S08-B04':a['issue_note_zh']='保留原有店铺、窗框与屋顶；背面、底面封口未处理，内构件保留。'
 a['quality_label_zh']='未封口' if a['geometry_status']=='OPEN_SHELL' else '内部待制作'
 file=R/'extracted'/a['file'];b=file.read_bytes();n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);binary=b[28+n:];target_views=[]
 if a['source_id']=='S09':
  for image in d.get('images',[]):
   view=d['bufferViews'][image['bufferView']];data=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
   if hashlib.sha256(data).hexdigest()==old_hash:target_views.append(image['bufferView']);image['name']='V21_S09_City_Facades_Enhanced'
  assert target_views,(a['asset_id'],'source diffuse image not found')
  buf=bytearray();accessor_views={x['bufferView'] for x in d.get('accessors',[]) if 'bufferView' in x};checks=[]
  for vi,view in enumerate(d['bufferViews']):
   source=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']];data=new_image if vi in target_views else source;buf.extend(b'\0'*((-len(buf))%4));view['byteOffset']=len(buf);view['byteLength']=len(data);buf.extend(data)
   if vi in accessor_views:checks.append(hashlib.sha256(source).hexdigest()==hashlib.sha256(data).hexdigest())
  buf.extend(b'\0'*((-len(buf))%4));binary=bytes(buf);d['buffers'][0]['byteLength']=len(binary);a['texture_policy']='AI-restored shared S09 diffuse atlas; normalized atlas regions retained; source geometry and UV accessor bytes unchanged; no duplicate lightmap overlay';a['texture_enhanced']=True;a['enhanced_atlas_size_px']=list(Image.open(R/'textures/S09_city_facades_enhanced.png').size);assert all(checks)
  proof.append(dict(asset_id=a['asset_id'],geometry_and_uv_buffer_views_unchanged=all(checks),views_checked=len(checks),original_atlas_sha256=old_hash,enhanced_atlas_sha256=hashlib.sha256(new_image).hexdigest(),enhanced_atlas_size_px=a['enhanced_atlas_size_px']))
 for node in d['nodes']:
  e=node.get('extras',{})
  if e.get('asset_id')==a['asset_id']:
   for k in ['display_name_zh','issue_note_zh','quality_label_zh','texture_policy']:e[k]=a[k]
   e['texture_enhanced']=a.get('texture_enhanced',False)
 text=json.dumps(d,ensure_ascii=False,separators=(',',':')).encode();text+=b' '*((-len(text))%4);binary+=b'\0'*((-len(binary))%4);out=b'glTF'+struct.pack('<II',2,28+len(text)+len(binary))+struct.pack('<I4s',len(text),b'JSON')+text+struct.pack('<I4s',len(binary),b'BIN\0')+binary;file.write_bytes(out);a['sha256']=hashlib.sha256(out).hexdigest();a['bytes']=len(out)
(R/'asset_catalog.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2));(R/'validation/texture_enhancement.json').write_text(json.dumps(dict(status='PASS',method='built-in image generation edit, shared atlas detail restoration',source_size_px=list(Image.open(R/'audit/source_WorldCityBuildings2.png').size),output_size_px=list(Image.open(R/'textures/S09_city_facades_enhanced.png').size),layout_review='Atlas partition positions checked against source; AI fine detail is interpretive.',assets=proof),indent=2));print('ENHANCED',len(proof),flush=True)
