"""Compare decoded source texture pixels with every new/moved exported instance."""
from pathlib import Path
import json,struct,hashlib,io
from PIL import Image
R=Path(__file__).resolve().parents[1]
def image_maps(path):
 b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);start=20+n+8;hashes={}
 for i,im in enumerate(j.get('images',[])):
  assert 'bufferView' in im and 'uri' not in im,(path,im)
  view=j['bufferViews'][im['bufferView']];off=start+view.get('byteOffset',0);raw=b[off:off+view['byteLength']]
  with Image.open(io.BytesIO(raw)) as pic:
   rgba=pic.convert('RGBA');hashes[i]={'dimensions':list(rgba.size),'rgba_sha256':hashlib.sha256(rgba.tobytes()).hexdigest()}
 result={}
 for node in j.get('nodes',[]):
  if 'mesh' not in node:continue
  name=node.get('extras',{}).get('source_instance',node.get('name','unnamed'));values=[]
  for primitive in j['meshes'][node['mesh']]['primitives']:
   mat=j.get('materials',[])[primitive['material']];tex=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture',{})
   if 'index' in tex:values.append(hashes[j['textures'][tex['index']]['source']])
  if values:result.setdefault(name,[]).extend(values)
 return result
baseline={}
for f in sorted((R/'baseline').glob('*.glb')):baseline.update(image_maps(f))
source={f.name:[v for vs in image_maps(f).values() for v in vs] for f in (R/'sources').glob('*.glb')}
exported={}
for f in sorted((R/'districts').glob('*.glb')):exported.update(image_maps(f))
p=json.load(open(R/'model/city_plan.json'));records=[r for r in p['real_buildings'] if r.get('added_in_version')=='v18'];checks=[]
def canonical(values):return sorted({(tuple(v['dimensions']),v['rgba_sha256']) for v in values})
for r in records:
 name=r['instance_name'];origin=r.get('source_template_instance') or (name if name in baseline else None);expected=baseline[origin] if origin else source[r['file']];actual=exported[name];passed=canonical(expected)==canonical(actual);checks.append({'instance':name,'template':origin or r['file'],'texture_count':len(canonical(actual)),'decoded_rgba_pixels_match':passed})
status='PASS' if all(r['decoded_rgba_pixels_match'] for r in checks) and len(checks)==10 else 'FAIL';out={'status':status,'instances_checked':len(checks),'original_source_textures_preserved':status=='PASS','checks':checks};(R/'validation/texture_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(status,len(checks));assert status=='PASS'
