"""R3: original source neck with similarity only, Xia Qing skull cut at jaw, minimal rim join."""
import bpy,bmesh,numpy as np,json,math
from pathlib import Path
from scipy.spatial import cKDTree
from mathutils import Vector
P=Path(__file__).resolve().parent;B=P.parent.parent
bpy.ops.wm.open_mainfile(filepath=str(B/'refinement-r2/vest_xiaqing_r2.blend'))
rig=bpy.data.objects['Xiaqing_Native_Rig'];body=bpy.data.objects['Vest_Body'];rig.animation_data.action=None;rig.data.pose_position='REST'
for t in rig.animation_data.nla_tracks:t.mute=True
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update()
orig_actions=set(bpy.data.actions);orig_objects=set(bpy.data.objects)
headparts=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('tripo_part_')];hair=bpy.data.objects['Xiaqing_fitted_bob']
for name in ['Vest_NeckBridge','Neck_continuous_transition']:
 if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
# Give every retained R2 body point a stable merge identity.
def intattr(ob,name,values):
 a=ob.data.attributes.get(name) or ob.data.attributes.new(name,'INT','POINT');a.data.foreach_set('value',np.asarray(values,dtype=np.int32));return a
intattr(body,'r2_vertex_id',np.arange(len(body.data.vertices)));intattr(body,'r3_source_neck',np.zeros(len(body.data.vertices),dtype=int))
oldbody=np.array([v.co[:] for v in body.data.vertices]);oldnormals=[v.vector[:] for v in body.data.corner_normals]
seams=json.loads((B/'seam_pairs.json').read_text());ringids=np.array([j for _,j in seams['bottom']],dtype=int)
# Import source and perform the same weld as initial production preparation.
bpy.ops.import_scene.gltf(filepath=str(B/'vest_source.glb'));src=next(o for o in bpy.context.scene.objects if o not in orig_objects and o.type=='MESH');bpy.ops.object.select_all(action='DESELECT');src.select_set(True);bpy.context.view_layer.objects.active=src;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(src.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=2e-6)
# Recreate original body cut solely to recover exact source correspondence.
low=bm.copy();bmesh.ops.bisect_plane(low,geom=list(low.verts)+list(low.edges)+list(low.faces),dist=1e-6,plane_co=(0,0,.847),plane_no=(0,0,1),clear_outer=True);bmesh.ops.delete(low,geom=[v for v in low.verts if not v.link_faces],context='VERTS');low.verts.ensure_lookup_table();sourcebelow=np.array([v.co[:] for v in low.verts]);assert len(sourcebelow)==len(oldbody),(len(sourcebelow),len(oldbody));low.free()
SCALE=1.7;translation=None
# Original neck, from its existing root to an anatomical sloping jaw cut.
SLOPE=.5;SRC_INTERCEPT=.831;HEAD_INTERCEPT=1.503;HEAD_SCALE=1.01901766065119;offset_2d=np.array([-4.373939814857699e-05,-.0066381913378333515])
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,.847),plane_no=(0,0,1),clear_inner=True)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,SRC_INTERCEPT),plane_no=(0,-SLOPE,1),clear_outer=True)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(src.data);bm.free();src.name='Vest_SourceNeck';rawneck=np.array([v.co[:] for v in src.data.vertices]);intattr(src,'r2_vertex_id',np.full(len(rawneck),-1));intattr(src,'r3_source_neck',np.ones(len(rawneck),dtype=int));a=src.data.attributes.new('r3_source_position','FLOAT_VECTOR','POINT');a.data.foreach_set('vector',rawneck.ravel())
sourcebottom=np.where(abs(rawneck[:,2]-.847)<5e-6)[0];sourcetop=np.where(abs(rawneck[:,2]-SLOPE*rawneck[:,1]-SRC_INTERCEPT)<5e-6)[0];assert len(sourcebottom)==len(ringids),(len(sourcebottom),len(ringids))
translation=oldbody[ringids].mean(0)-rawneck[sourcebottom].mean(0)*SCALE
for v,p in zip(src.data.vertices,rawneck*SCALE+translation):v.co=p
# Restore the old body opening to the exact unchanged source neck opening.
newpoints=rawneck[sourcebottom]*SCALE+translation;center=oldbody[ringids].mean(0);oldsort=np.argsort(np.arctan2(oldbody[ringids,1]-center[1],oldbody[ringids,0]-center[0]));newsort=np.argsort(np.arctan2(newpoints[:,1]-center[1],newpoints[:,0]-center[0]));best=min(range(len(ringids)),key=lambda shift:np.sum((newpoints[newsort]-oldbody[ringids[np.roll(oldsort,shift)]])**2));bodymatching=np.empty(len(ringids),dtype=int);bodymatching[newsort]=ringids[np.roll(oldsort,best)]
newbottom=rawneck[sourcebottom]*SCALE+translation;displacements=newbottom-oldbody[bodymatching]
kd=cKDTree(oldbody[bodymatching]);D=np.zeros_like(oldbody);protect=np.zeros(len(oldbody),dtype=int)
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
for i,p in enumerate(oldbody):
 if p[2]<1.398 or abs(p[0])>.088:continue
 dist,j=kd.query(p,k=5);weights=1/(dist+.002)**2;delta=np.sum(displacements[j]*weights[:,None],axis=0)/weights.sum();fade=smooth((p[2]-1.398)/.029);D[i]=delta*fade
 if fade>1e-5:protect[i]=1
for i,p in zip(bodymatching,newbottom):D[i]=p-oldbody[i];protect[i]=1
for v,delta in zip(body.data.vertices,D):v.co+=Vector(delta)
intattr(body,'r3_neck_preserve',protect)
# Local body-root skinning approaches neck_0 smoothly; all other weights preserved.
for i in np.where(protect>0)[0]:
 fade=smooth((oldbody[i,2]-1.398)/.029)
 if i in set(bodymatching.tolist()):fade=1
 v=body.data.vertices[int(i)];ww={body.vertex_groups[g.group].name:g.weight*(1-fade) for g in v.groups};ww['neck_0']=ww.get('neck_0',0)+fade
 for g in list(v.groups):body.vertex_groups[g.group].remove([int(i)])
 keep=sorted(ww.items(),key=lambda it:(-it[1],it[0]))[:4];total=sum(w for n,w in keep)
 for n,w in keep:
  if w>1e-9:body.vertex_groups[n].add([int(i)],float(w/total),'REPLACE')
# Clip all native skin head partitions at the actual jaw slope; preserve chin/face.
head_rings={};removed={}
for ob in headparts:
 n0=len(ob.data.vertices);bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,HEAD_INTERCEPT),plane_no=(0,-SLOPE,1),clear_inner=True);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free();pp=np.array([v.co[:] for v in ob.data.vertices]);ids=np.where(abs(pp[:,2]-SLOPE*pp[:,1]-HEAD_INTERCEPT)<5e-6)[0];head_rings[ob.name]=ids.tolist();removed[ob.name]=n0-len(pp)
# Unique top cut coordinates, retaining every coincident material partition reference.
refs={}
for name,ids in head_rings.items():
 for i in ids:
  p=np.array(bpy.data.objects[name].data.vertices[i].co);refs.setdefault(tuple(np.round(p,6)),[]).append((name,i))
keys=list(refs);hp=np.array(keys);hc=hp.mean(0);st=np.array([src.data.vertices[int(i)].co[:] for i in sourcetop]);sc=st.mean(0);planeoffset=np.array([offset_2d[0],offset_2d[1]/np.sqrt(1+SLOPE*SLOPE),SLOPE*offset_2d[1]/np.sqrt(1+SLOPE*SLOPE)]);headtarget=sc+planeoffset
for ob in headparts+[hair]:
 for v in ob.data.vertices:v.co=Vector((np.array(v.co)-hc)*HEAD_SCALE+headtarget)
 ob['r3_head_similarity_scale']=HEAD_SCALE;ob['r3_neck_removed']=ob!=hair
# Match skinning at the tiny upper rim. Native facial weights remain away from cut.
for ob in headparts:
 if 'head' not in ob.vertex_groups:ob.vertex_groups.new(name='head')
 for v in ob.data.vertices:
  # Plane distance after head similarity, in original coordinates.
  original=(np.array(v.co)-headtarget)/HEAD_SCALE+hc;height=original[2]-SLOPE*original[1]-HEAD_INTERCEPT;fade=1-smooth(height/.008)
  if fade<1e-8:continue
  ww={ob.vertex_groups[g.group].name:g.weight*(1-fade) for g in v.groups};ww['head']=ww.get('head',0)+fade
  for g in list(v.groups):ob.vertex_groups[g.group].remove([v.index])
  keep=sorted(ww.items(),key=lambda t:(-t[1],t[0]))[:4];total=sum(w for n,w in keep)
  for n,w in keep:
   if w>1e-9:ob.vertex_groups[n].add([v.index],float(w/total),'REPLACE')
# Bind original source neck smoothly, without any shoulder/deltoid drivers.
for b in rig.data.bones:src.vertex_groups.new(name=b.name)
for i,p in enumerate(rawneck):
 f=np.clip((p[2]-.847)/max(SRC_INTERCEPT+SLOPE*p[1]-.847,.001),0,1)
 ww={'neck_0':(1-f)**2,'neck_1':2*f*(1-f),'head':f*f};total=sum(ww.values())
 for n,w in ww.items():
  if w>1e-9:src.vertex_groups[n].add([i],float(w/total),'REPLACE')
# Exact lower-rim skin copy ensures no animated root crack.
for ni,bi in zip(sourcebottom,bodymatching):
 for g in list(src.data.vertices[int(ni)].groups):src.vertex_groups[g.group].remove([int(ni)])
 for g in body.data.vertices[int(bi)].groups:src.vertex_groups[body.vertex_groups[g.group].name].add([int(ni)],g.weight,'REPLACE')
mod=src.modifiers.new('Native source neck skinning','ARMATURE');mod.object=rig;src.parent=rig;src.matrix_parent_inverse=rig.matrix_world.inverted();src['vest_outfit']=True;src['source_head_removed']=True;src['r3_neck_policy']='Original source neck; similarity transform only; no RBF or contour warp';src['r3_source_scale']=SCALE;src['r3_source_translation']=translation.tolist()
# A single narrow ring: boundary positions only, no tall fabricated neck bridge.
sp=np.array([src.data.vertices[int(i)].co[:] for i in sourcetop]);headpoints=np.array([bpy.data.objects[refs[k][0][0]].data.vertices[refs[k][0][1]].co[:] for k in keys]);center=(sp.mean(0)+headpoints.mean(0))/2
angle=lambda p:math.atan2((p[1]-center[1])*np.sqrt(1+SLOPE*SLOPE),p[0]-center[0])
so=sorted(range(len(sp)),key=lambda i:angle(sp[i]));ho=sorted(range(len(headpoints)),key=lambda i:angle(headpoints[i]));sv=sp[so];hv=headpoints[ho];sa=np.array([angle(p) for p in sv]);ha=np.array([angle(p) for p in hv]);N=len(sv);M=len(hv);verts=sv.tolist()+hv.tolist();faces=[];i=j=0
while i<N or j<M:
 ns=sa[(i+1)%N]+(2*np.pi if i+1>=N else 0) if i<N else float('inf');nh=ha[(j+1)%M]+(2*np.pi if j+1>=M else 0) if j<M else float('inf')
 if ns<=nh:faces.append((i%N,(i+1)%N,N+j%M));i+=1
 else:faces.append((i%N,N+(j+1)%M,N+j%M));j+=1
me=bpy.data.meshes.new('R3_JawRim_mesh');me.from_pydata(verts,[],faces);me.update();rim=bpy.data.objects.new('R3_JawRim',me);bpy.context.collection.objects.link(rim);rim.vertex_groups.new(name='head');rim.vertex_groups['head'].add(list(range(len(verts))),1,'REPLACE');mod=rim.modifiers.new('Native head seam','ARMATURE');mod.object=rig;rim.parent=rig;rim.matrix_parent_inverse=rig.matrix_world.inverted();rim['vest_outfit']=True;rim['r3_patch_policy']='Single narrow jaw-edge strip; no independent neck volume'
# Vertex-color endpoint samples blend the small material seam without painted geometry.
pixel_cache={}
def colors(ob):
 out=np.zeros((len(ob.data.vertices),4));ct=np.zeros(len(out));uv=ob.data.uv_layers.active
 for poly in ob.data.polygons:
  mat=ob.data.materials[min(poly.material_index,len(ob.data.materials)-1)];imgs=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if mat and mat.use_nodes else [];img=imgs[0] if imgs else None
  if img:
   
   if img.name not in pixel_cache:pixel_cache[img.name]=np.array(img.pixels[:]).reshape(img.size[1],img.size[0],4)
   pixels=pixel_cache[img.name]
  for li in poly.loop_indices:
   vi=ob.data.loops[li].vertex_index
   if img and uv:
    u,v=uv.data[li].uv;col=pixels[int(v*img.size[1])%img.size[1],int(u*img.size[0])%img.size[0]]
   else:col=np.array(mat.diffuse_color if mat else (.4,.25,.2,1))
   out[vi]+=col;ct[vi]+=1
 return out/np.maximum(ct[:,None],1)
# Cache sampling once per object (source uses same original texture as body).
cs=colors(src);ch={name:colors(bpy.data.objects[name]) for name in head_rings if head_rings[name]};cc=[]
for oi in so:cc.append(cs[int(sourcetop[oi])])
for oi in ho:
 rr=refs[keys[oi]];cc.append(np.mean([ch[n][idx] for n,idx in rr],axis=0))
attr=me.color_attributes.new(name='R3_seam_color',type='FLOAT_COLOR',domain='POINT');attr.data.foreach_set('color',np.array(cc,dtype=np.float32).ravel());mat=bpy.data.materials.new('R3 small jaw seam skin');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.8;node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='R3_seam_color';mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color']);mat.diffuse_color=tuple(np.mean(cc,axis=0));me.materials.append(mat)
# Bake the same sampled rim colors to UV so Workbench and glTF see matching skin.
ww,hh=1024,8;pix=np.ones((hh,ww,4),dtype=np.float32);u_source=(sa+np.pi)/(2*np.pi);u_head=(ha+np.pi)/(2*np.pi);ca=np.array(cc[:N]);cb=np.array(cc[N:]);ux=np.linspace(0,1,ww)
def angular_colors(u,col):
 return np.stack([np.interp(ux,np.r_[u[-1]-1,u,u[0]+1],np.r_[col[-1,k],col[:,k],col[0,k]]) for k in range(4)],axis=1)
aa=angular_colors(u_source,ca);bb=angular_colors(u_head,cb)
for iy,t in enumerate(np.linspace(0,1,hh)):pix[iy]=aa*(1-t)+bb*t
img=bpy.data.images.new('R3_tiny_jaw_seam_color',width=ww,height=hh);img.pixels.foreach_set(pix.ravel());img.pack();tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img;mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);uv=me.uv_layers.new(name='JawRimUV');u_all=np.r_[u_source,u_head]
for poly in me.polygons:
 us=[u_all[me.loops[li].vertex_index] for li in poly.loop_indices];wrap=max(us)-min(us)>.5
 for li,u in zip(poly.loop_indices,us):
  vi=me.loops[li].vertex_index;uv.data[li].uv=(u+1 if wrap and u<.5 else u,0 if vi<N else 1)

# Preserve existing custom normals away from changed root, recompute locally.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
body.data.update();newnormals=[v.vector[:] for v in body.data.corner_normals]
for l in body.data.loops:
 if not protect[l.vertex_index]:newnormals[l.index]=oldnormals[l.index]
body.data.normals_split_custom_set(newnormals)
for ob in [src,rim]+headparts:
 for poly in ob.data.polygons:poly.use_smooth=True
 ob.data.update()
# Consistent endpoint normals across the original body/neck and tiny jaw strip.
objects=[body,src,rim]+headparts;normals={ob.name:[v.vector[:] for v in ob.data.corner_normals] for ob in objects};buckets={}
for ob in objects:
 for v in ob.data.vertices:
  if v.co.z>1.398 and abs(v.co.x)<.09:buckets.setdefault(tuple(np.round(v.co,6)),[]).append((ob.name,v.index,np.zeros(3) if ob==rim else np.array(v.normal)))
shared={}
for k,rr in buckets.items():
 if len(rr)>1:
  nn=np.sum([r[2] for r in rr],axis=0);nn/=max(np.linalg.norm(nn),1e-12)
  for n,idx,_ in rr:shared[(n,idx)]=nn
for ob in objects:
 for loop in ob.data.loops:
  key=(ob.name,loop.vertex_index)
  if key in shared:normals[ob.name][loop.index]=shared[key]
 ob.data.normals_split_custom_set(normals[ob.name])
# Exact cross-object boundary evidence for downstream tests and GLB roundtrip.
manifest={'source_neck':'Vest_SourceNeck','rim':'R3_JawRim','root_body':'Vest_Body','root_pairs':[[int(ni),int(bi)] for ni,bi in zip(sourcebottom,bodymatching)],'rim_source_pairs':[[int(i),int(sourcetop[oi])] for i,oi in enumerate(so)],'rim_head_pairs':[[N+j,n,int(idx)] for j,oi in enumerate(ho) for n,idx in refs[keys[oi]]],'source_neck_similarity':{'scale':SCALE,'translation':translation.tolist()},'head_similarity':{'scale':HEAD_SCALE,'original_center':hc.tolist(),'target_center':headtarget.tolist()},'head_cut_plane':{'slope_y':SLOPE,'intercept_z':HEAD_INTERCEPT},'source_jaw_cut_plane':{'slope_y':SLOPE,'intercept_z':SRC_INTERCEPT}}
(P/'seam_manifest.json').write_text(json.dumps(manifest,indent=2))
q=cKDTree(sp).query(headpoints)[0];qq=cKDTree(headpoints).query(sp)[0]
report={'neck_vertices':len(src.data.vertices),'new_rim_vertices':len(rim.data.vertices),'new_rim_faces':len(rim.data.polygons),'source_neck_similarity_max_error_m':float(np.max(np.linalg.norm(np.array([v.co[:] for v in src.data.vertices])-(rawneck*SCALE+translation),axis=1))),'head_parts_removed_vertices':removed,'root_vertices_adjusted':int(sum(protect>0)),'root_max_displacement_mm':float(np.max(np.linalg.norm(D,axis=1))*1000),'root_boundary_max_displacement_mm':float(np.max(np.linalg.norm(displacements,axis=1))*1000),'jaw_rim_width_max_mm':float(max(q.max(),qq.max())*1000),'jaw_rim_width_mean_mm':float((q.mean()+qq.mean())*500),'source_similarity':manifest['source_neck_similarity'],'head_similarity':manifest['head_similarity'],'old_neck_objects_removed':['Vest_NeckBridge','Neck_continuous_transition'],'bone_rest_or_animation_changed':False,'protected_body_points_attribute':'r3_neck_preserve','immutable_neck_attribute':'r3_source_neck','r2_vertex_identity_retained':True}
for img in bpy.data.images:
 if img.source=='FILE' and not img.packed_file:
  try:img.pack()
  except:pass
for a in list(bpy.data.actions):
 if a not in orig_actions:bpy.data.actions.remove(a,do_unlink=True)
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'neck_rebuilt.blend'),compress=True);(P/'neck_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
