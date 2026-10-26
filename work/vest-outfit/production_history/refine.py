import bpy,json,numpy as np,math,bmesh
from pathlib import Path
from scipy.sparse import csr_matrix
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'vest_xiaqing.blend'))
o=bpy.data.objects['Vest_Body'];bridge=bpy.data.objects['Vest_NeckBridge'];neck=bpy.data.objects['Neck_continuous_transition'];rig=bpy.data.objects['Xiaqing_Native_Rig'];rig.data.pose_position='REST';rig.animation_data.action=None
for ob in [o,bridge,neck]:
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
 for poly in ob.data.polygons:poly.use_smooth=True
N=len(o.data.vertices);G=len(o.vertex_groups);w=np.zeros((N,G));pos=np.array([v.co[:] for v in o.data.vertices]);labels=np.array([v.value for v in o.data.attributes['source_finger_id'].data])
for v in o.data.vertices:
 for g in v.groups:w[v.index,g.group]=g.weight
# Pelvis-to-thigh blend avoids inappropriate closest-surface donors in the crotch.
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for i,p in enumerate(pos):
 if .74<p[2]<1.025 and abs(p[0])<.24:
  thigh=smooth((.995-p[2])/.19);left=smooth((p[0]+.045)/.09);new=np.zeros(G)
  new[o.vertex_groups['hips'].index]=1-thigh;new[o.vertex_groups['l_leg_femur'].index]=thigh*left;new[o.vertex_groups['r_leg_femur'].index]=thigh*(1-left)
  blend=smooth((p[2]-.74)/.06)*smooth((1.025-p[2])/.04);w[i]=w[i]*(1-blend)+new*blend
edges=np.array([e.vertices[:] for e in o.data.edges]);a=np.r_[edges[:,0],edges[:,1],np.arange(N)];b=np.r_[edges[:,1],edges[:,0],np.arange(N)];adj=csr_matrix((np.ones(len(a)),(a,b)),shape=(N,N));adj=adj.multiply(1/np.array(adj.sum(1))).tocsr()
# Diffuse local discontinuities; protect the original per-finger ownership mask.
for _ in range(8):
 nw=adj@w;w=.55*w+.45*nw
 for lab in range(1,11):
  side='l' if lab<=5 else 'r';finger=['thumb','index','middle','ring','little'][(lab-1)%5];allow=np.array([g.name.startswith(f'{side}_hand_{finger}_') or g.name==f'{side}_arm_wrist' for g in o.vertex_groups]);ids=np.where(labels==lab)[0];w[np.ix_(ids,np.where(~allow)[0])]=0
 w/=np.maximum(w.sum(1,keepdims=True),1e-12)
for v,row in zip(o.data.vertices,w):
 for g in list(v.groups):o.vertex_groups[g.group].remove([v.index])
 ids=np.argsort(row)[-4:];total=row[ids].sum()
 for j in ids:
  if row[j]>1e-8:o.vertex_groups[int(j)].add([v.index],float(row[j]/total),'REPLACE')
seams=json.loads((P/'seam_pairs.json').read_text())
for bi,oi in seams['bottom']:
 v=bridge.data.vertices[bi]
 for g in list(v.groups):bridge.vertex_groups[g.group].remove([bi])
 for g in o.data.vertices[oi].groups:bridge.vertex_groups[o.vertex_groups[g.group].name].add([bi],g.weight,'REPLACE')
# Sample both boundary textures and bake a continuous collar gradient.
def colors(ob):
 uv=ob.data.uv_layers.active;result={};cache={}
 for mat in ob.data.materials:
  img=next((n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
  if img:cache[mat.name]=(np.array(img.pixels[:]).reshape(img.size[1],img.size[0],4),img.size[:])
 for f in ob.data.polygons:
  mat=ob.data.materials[f.material_index]
  if mat.name not in cache:continue
  pixels,(width,height)=cache[mat.name]
  for li in f.loop_indices:
   vi=ob.data.loops[li].vertex_index;u,v=uv.data[li].uv;col=pixels[min(height-1,int(v*height)%height),min(width-1,int(u*width)%width),:3];result.setdefault(vi,[]).append(col)
 return {i:np.mean(c,axis=0) for i,c in result.items()}
cs=colors(o);ct=colors(neck);N0=len(seams['bottom']);M=len(seams['top']);c0=np.array([cs[oi] for bi,oi in seams['bottom']]);c1=np.array([ct[ni] for bi,ni in seams['top']]);width,height=1024,64;arr=np.zeros((height,width,4),dtype=np.float32)
for x in range(width):
 u=x/(width-1);aa=np.array([np.interp(u,np.linspace(0,1,N0+1),np.r_[c0[:,k],c0[0,k]]) for k in range(3)]);bb=np.array([np.interp(u,np.linspace(0,1,M+1),np.r_[c1[:,k],c1[0,k]]) for k in range(3)])
 for y in range(height):t=y/(height-1);arr[y,x,:3]=aa*(1-t)+bb*t;arr[y,x,3]=1
img=bpy.data.images.new('Vest_neck_gradient',width=width,height=height);img.pixels.foreach_set(arr.ravel());img.pack();mat=bridge.data.materials[0];node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=img;mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);uv=bridge.data.uv_layers.new(name='NeckUV')
for f in bridge.data.polygons:
 values=[]
 for li in f.loop_indices:
  vi=bridge.data.loops[li].vertex_index;values.append((li,(vi/N0,0) if vi<N0 else ((vi-N0)/M,1)))
 seam=max(v[1][0] for v in values)-min(v[1][0] for v in values)>.5
 for li,(u,v) in values:uv.data[li].uv=(u+1 if seam and u<.5 else u,v)
# Average normals at shared seam coordinates, keeping exact geometry and weights.
for ob in [o,bridge,neck]:ob.data.update()
normalarrays={ob.name:[l.vector[:] for l in ob.data.corner_normals] for ob in [o,bridge,neck]}
loops={ob.name:{} for ob in [o,bridge,neck]}
for ob in [o,bridge,neck]:
 for l in ob.data.loops:loops[ob.name].setdefault(l.vertex_index,[]).append(l.index)
for pairs,other in [(seams['bottom'],o),(seams['top'],neck)]:
 for bi,oi in pairs:
  inds1=loops[bridge.name][bi];inds2=loops[other.name][oi];ns=[normalarrays[bridge.name][i] for i in inds1]+[normalarrays[other.name][i] for i in inds2];n=Vector(np.mean(ns,axis=0)).normalized()
  for i in inds1:normalarrays[bridge.name][i]=n[:]
  for i in inds2:normalarrays[other.name][i]=n[:]
for ob in [o,bridge,neck]:ob.data.normals_split_custom_set(normalarrays[ob.name])
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'vest_xiaqing.blend'),compress=True)
print('REFINE COMPLETE')
