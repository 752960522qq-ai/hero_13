"""Build a continuous outfit-specific neck bridge in Blender."""
import bpy,json,sys,numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from glb_shoe_utils import load,acc,ROOT
j,b=load(ROOT/'dist/assets/xiaqing_native_animated.glb')
def prim(name):
 n=next(n for n in j['nodes'] if n.get('name')==name and 'mesh' in n)
 while 'mesh' not in n:n=j['nodes'][n['children'][0]]
 return j['meshes'][n['mesh']]['primitives'][0]
p=prim('pl2001_pl2001_Face_Mat');q=prim('Neck_continuous_transition')
v=acc(j,b,p['attributes']['POSITION']);tv=acc(j,b,q['attributes']['POSITION']);data=np.load('/tmp/shirt-fit.npz');gv=data['positions'];bottom=gv[(gv[:,1]>1.4548)&(abs(gv[:,0])<.1)]
top=tv[tv[:,1]>1.473]
center=np.array([0,-.003])
def radii(points,angles):
 d=points[:,[0,2]]-center;a=np.arctan2(d[:,1],d[:,0]);r=np.linalg.norm(d,axis=1);out=[]
 for angle in angles:
  dist=np.abs(np.angle(np.exp(1j*(a-angle))));ids=np.argsort(dist)[:5];w=1/np.maximum(dist[ids],.01)**2;out.append(np.sum(r[ids]*w)/w.sum())
 # periodic smoothing prevents source triangle spacing from creating spikes
 out=np.array(out)
 for _ in range(3):out=(np.roll(out,1)+2*out+np.roll(out,-1))/4
 return out
N=96;angles=np.arange(N)*2*np.pi/N;rb=radii(bottom,angles)*.995;rt=radii(top,angles)*.96
positions=[]
for row in range(9):
 t=row/8;r=rb*(1-t)+rt*t
 for a,rad in zip(angles,r):positions.append([rad*np.cos(a),1.448+(1.479-1.448)*t,center[1]+rad*np.sin(a)])
positions=np.array(positions);faces=[]
for row in range(8):
 for i in range(N):
  a=row*N+i;c=row*N+(i+1)%N;d=c+N;e=a+N;faces.extend([[a,e,c],[c,e,d]])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
m=bpy.data.meshes.new('ContinuousNeckBridge');m.from_pydata(positions.tolist(),[],faces);m.update();o=bpy.data.objects.new('OutfitNeckBridge',m);bpy.context.collection.objects.link(o)
for poly in m.polygons:poly.use_smooth=True
# Blend native joint weights from the existing neck surfaces.
allv=np.concatenate([v,tv]);dist,near=cKDTree(allv).query(positions,k=8)
coef=1/np.maximum(dist,.002)**2;coef/=coef.sum(1,keepdims=True)
js=np.concatenate([acc(j,b,p['attributes']['JOINTS_0']),acc(j,b,q['attributes']['JOINTS_0'])]);ws=np.concatenate([acc(j,b,p['attributes']['WEIGHTS_0']),acc(j,b,q['attributes']['WEIGHTS_0'])]);ws/=np.maximum(ws.sum(1,keepdims=True),1e-12)
weights=np.zeros((len(positions),len(j['skins'][0]['joints'])))
for k in range(8):
 for c in range(4):np.add.at(weights,(np.arange(len(positions)),js[near[:,k],c]),coef[:,k]*ws[near[:,k],c])
order=np.argsort(weights,axis=1)[:,-4:];w=np.take_along_axis(weights,order,axis=1);w/=w.sum(1,keepdims=True)
# Smooth UV interpolation within the same original neck material.
dist,near=cKDTree(v).query(positions,k=4);coef=1/np.maximum(dist,.002)**2;coef/=coef.sum(1,keepdims=True)
uv=acc(j,b,p['attributes']['TEXCOORD_0']);attrs={'JOINTS_0':order,'WEIGHTS_0':w,'TEXCOORD_0':(uv[near]*coef[:,:,None]).sum(1)}
assert all(poly.area>1e-12 for poly in m.polygons)
config=ROOT/'dist/assets/wardrobe/shirt_trouser.json';d=json.loads(config.read_text());d.pop('neckPatchPositions',None);d['neckBridge']={'positions':positions.tolist(),'indices':faces,'uv':attrs['TEXCOORD_0'].tolist(),'joints':attrs['JOINTS_0'].tolist(),'weights':attrs['WEIGHTS_0'].tolist()};config.write_text(json.dumps(d,separators=(',',':')))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'qa/shirt-trouser/neck_transition.blend'));print('Blender bridge: 864 vertices, 1536 nondegenerate triangles')
