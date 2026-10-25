"""Match only exposed neck/wrist skin texels; preserve white shirt and denim."""
import io
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from glb_shoe_utils import ROOT,load,acc
j,b=load(ROOT/'source-models/shirt_trouser_original.glb');p=j['meshes'][0]['primitives'][0];a=p['attributes'];v=acc(j,b,a['POSITION']);uv=acc(j,b,a['TEXCOORD_0']);faces=acc(j,b,p['indices']).reshape(-1,3);c=v[faces].mean(1)
im=j['images'][j['textures'][0]['source']];bv=j['bufferViews'][im['bufferView']];img=Image.open(io.BytesIO(b[bv.get('byteOffset',0):bv.get('byteOffset',0)+bv['byteLength']])).convert('RGB');rgb=np.array(img,dtype=float);mask=Image.new('L',img.size);draw=ImageDraw.Draw(mask)
region=((c[:,1]>.785)&(c[:,1]<.85)&(abs(c[:,0])<.055))|((c[:,1]>.61)&(c[:,1]<.63)&(abs(c[:,0])>.195))
for face in faces[region]:draw.polygon([tuple(x) for x in uv[face]*img.size],fill=255)
area=np.array(mask.filter(ImageFilter.MaxFilter(5)),dtype=float)/255
# White cloth has almost neutral channels; do not recolor it.
hue=np.clip((rgb[:,:,0]-rgb[:,:,1]-7)/15,0,1)*np.clip((rgb[:,:,1]-rgb[:,:,2]-5)/10,0,1)
a=(area*hue)[:,:,None];tinted=np.clip(rgb*np.array([219/193,168/152,143/122]),0,255);out=rgb*(1-a)+tinted*a
Image.fromarray(out.astype('uint8')).save('/tmp/shirt-matched.jpg',quality=97)
print('Skin-only texture adjustment saved')
