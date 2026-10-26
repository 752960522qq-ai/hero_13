import bpy,numpy as np,json,math
from pathlib import Path
from scipy.sparse import csr_matrix
from mathutils import Vector
P=Path(__file__).resolve().parent;O=P/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'vest_xiaqing.blend'));o=bpy.data.objects['Vest_Body'];bridge=bpy.data.objects['Vest_NeckBridge'];neck=bpy.data.objects['Neck_continuous_transition'];rig=bpy.data.objects['Xiaqing_Native_Rig'];rig.animation_data.action=None;rig.data.pose_position='REST'
N=len(o.data.vertices);G=len(o.vertex_groups);w=np.zeros((N,G));pos=np.array([v.co[:] for v in o.data.vertices]);labels=np.array([v.value for v in o.data.attributes['source_finger_id'].data]);edges=np.array([e.vertices[:] for e in o.data.edges])
for v in o.data.vertices:
 for g in v.groups:w[v.index,g.group]=g.weight
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for i,p in enumerate(pos):
 if 1.18<p[2]<1.48 and .075<abs(p[0])<.29:
  side='l' if p[0]>0 else 'r';arm=smooth((abs(p[0])-.09)/.15);new=np.zeros(G);new[o.vertex_groups['spine_2'].index]=1-arm;new[o.vertex_groups[side+'_arm_humerus'].index]=arm
  blend=smooth((p[2]-1.18)/.07)*smooth((.29-abs(p[0]))/.05);w[i]=w[i]*(1-blend)+new*blend
# Vertices shared by different digits are webbing and follow the palm first.
web=edges[(labels[edges[:,0]]>0)&(labels[edges[:,1]]>0)&(labels[edges[:,0]]!=labels[edges[:,1]])];front=set(web.ravel().tolist());visited=set();neighbors=[[] for _ in range(N)]
for a,b in edges:neighbors[a].append(b);neighbors[b].append(a)
for ring in range(5):
 nxt=set()
 for i in front-visited:
  side='l' if pos[i,0]>0 else 'r';blend=[1,.95,.75,.4,.15][ring];w[i]*=1-blend;w[i,o.vertex_groups[side+'_arm_wrist'].index]+=blend
  if ring<=1:labels[i]=0
  nxt.update(neighbors[i])
 visited.update(front);front=nxt-visited
r=np.r_[edges[:,0],edges[:,1],np.arange(N)];c=np.r_[edges[:,1],edges[:,0],np.arange(N)];adj=csr_matrix((np.ones(len(r)),(r,c)),shape=(N,N));adj=adj.multiply(1/np.array(adj.sum(1))).tocsr()
for _ in range(6):
 w=.65*w+.35*(adj@w)
 for lab in range(1,11):
  side='l' if lab<=5 else 'r';finger=['thumb','index','middle','ring','little'][(lab-1)%5];allow=np.array([g.name.startswith(f'{side}_hand_{finger}_') or g.name==f'{side}_arm_wrist' for g in o.vertex_groups]);ids=np.where(labels==lab)[0];w[np.ix_(ids,np.where(~allow)[0])]=0
 w/=np.maximum(w.sum(1,keepdims=True),1e-12)
o.data.attributes['source_finger_id'].data.foreach_set('value',labels)
for v,row in zip(o.data.vertices,w):
 for g in list(v.groups):o.vertex_groups[g.group].remove([v.index])
 ids=np.argsort(row)[-4:];total=row[ids].sum()
 for j in ids:
  if row[j]>1e-8:o.vertex_groups[int(j)].add([v.index],float(row[j]/total),'REPLACE')
seams=json.loads((P/'seam_pairs.json').read_text());n=len(seams['bottom']);m=len(seams['top']);bp=np.array([v.co[:] for v in bridge.data.vertices]);origin=np.array([0,.010]);angles=(np.arctan2(bp[:,1]-origin[1],bp[:,0]-origin[0])+np.pi)/(2*np.pi);bi=sorted(range(n),key=lambda i:angles[i]);ti=sorted(range(n,n+m),key=lambda i:angles[i]);faces=[];i=j=0
while i<n or j<m:
 nextb=angles[bi[(i+1)%n]]+(1 if i+1>=n else 0);nextt=angles[ti[(j+1)%m]]+(1 if j+1>=m else 0)
 if j==m or (i<n and nextb<=nextt):face=[bi[i%n],bi[(i+1)%n],ti[j%m]];i+=1
 else:face=[bi[i%n],ti[(j+1)%m],ti[j%m]];j+=1
 points=bp[face];normal=np.cross(points[1]-points[0],points[2]-points[0]);rad=points.mean(0)-[0,.01,points.mean(0)[2]]
 if normal@rad<0:face.reverse()
 faces.append(face)
old=bridge.data;weights=[[(bridge.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in old.vertices];mat=old.materials[0];me=bpy.data.meshes.new('NeckBridge_angular');me.from_pydata(bp,[],faces);me.materials.append(mat);bridge.data=me
for bone in rig.data.bones:
 if bone.name not in bridge.vertex_groups:bridge.vertex_groups.new(name=bone.name)
for idx,ws in enumerate(weights):
 for name,wt in ws:bridge.vertex_groups[name].add([idx],wt,'REPLACE')
for idx,oi in seams['bottom']:
 for g in list(me.vertices[idx].groups):bridge.vertex_groups[g.group].remove([idx])
 for g in o.data.vertices[oi].groups:bridge.vertex_groups[o.vertex_groups[g.group].name].add([idx],g.weight,'REPLACE')
# Bake boundary colors by actual angle rather than vertex count.
exec((P/'refine.py').read_text().split('def colors(ob):')[1].split('cs=colors')[0].join(['def colors(ob):','']))
cs=colors(o);ct=colors(neck);col=np.array([cs[oi] for _,oi in seams['bottom']]+[ct[ni] for _,ni in seams['top']]);ww,hh=1024,64;pixels=np.ones((hh,ww,4),dtype=np.float32)
for x in range(ww):
 u=x/(ww-1);colors2=[]
 for ids in [bi,ti]:
  aa=angles[ids];cc=col[ids];colors2.append(np.array([np.interp(u,np.r_[aa[-1]-1,aa,aa[0]+1],np.r_[cc[-1,k],cc[:,k],cc[0,k]]) for k in range(3)]))
 for y in range(hh):t=y/(hh-1);pixels[y,x,:3]=colors2[0]*(1-t)+colors2[1]*t
img=bpy.data.images.new('Vest_neck_matched',width=ww,height=hh);img.pixels.foreach_set(pixels.ravel());img.pack();node=next(node for node in mat.node_tree.nodes if node.type=='TEX_IMAGE');node.image=img;uv=me.uv_layers.new(name='NeckUV')
for f in me.polygons:
 f.use_smooth=True;us=[angles[me.loops[i].vertex_index] for i in f.loop_indices];wrap=max(us)-min(us)>.5
 for li,u in zip(f.loop_indices,us):uv.data[li].uv=(u+1 if wrap and u<.5 else u,0 if me.loops[li].vertex_index<n else 1)
# Discard transformed imported corner normals, recompute smooth geometry normals.
for ob in [o,bridge,neck]:
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
 ob.data.update()
# Use the smooth cylindrical tangent at the short transition; match both seam sides.
loops={ob.name:{} for ob in [o,bridge,neck]};normals={ob.name:[v.vector[:] for v in ob.data.corner_normals] for ob in [o,bridge,neck]}
for ob in [o,bridge,neck]:
 for l in ob.data.loops:loops[ob.name].setdefault(l.vertex_index,[]).append(l.index)
for i,v in enumerate(bridge.data.vertices):
 normal=Vector((v.co.x,(v.co.y-.010)*1.35,0)).normalized()
 for li in loops[bridge.name][i]:normals[bridge.name][li]=normal[:]
for pairs,ob in [(seams['bottom'],o),(seams['top'],neck)]:
 for a,b in pairs:
  nn=normals[bridge.name][loops[bridge.name][a][0]]
  for li in loops[ob.name][b]:normals[ob.name][li]=nn
for ob in [o,bridge,neck]:ob.data.normals_split_custom_set(normals[ob.name])
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(O/'vest_xiaqing.blend'),compress=True)
print('POLISH COMPLETE',len(web),'web edges')
