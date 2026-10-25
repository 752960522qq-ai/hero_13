"""Convert Blender bone-axis conventions to the live character's bind axes."""
from glb_shoe_utils import *
from footwear_glb import append,save
n,nb=load(ROOT/'dist/assets/xiaqing_native_animated.glb');world=evaluate(n,nb,{'channels':[]},0);byname={node.get('name'):world[i] for i,node in enumerate(n['nodes'])}
path=ROOT/'dist/assets/wardrobe/shirt_trouser_rigged.glb';j,b=load(path);b=bytearray(b)
for sk in j['skins']:
 inverse=[]
 for i in sk['joints']:
  node=j['nodes'][i];w=byname[node['name']];inverse.append(np.linalg.inv(w).T.reshape(16))
  for key in ['translation','rotation','scale']:node.pop(key,None)
  node['matrix']=w.T.reshape(16).tolist()
 sk['inverseBindMatrices']=append(j,b,inverse,'MAT4')
save(j,b,path)
print('Live bind axes synchronized')
