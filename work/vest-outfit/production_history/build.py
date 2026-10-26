import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
from scipy.interpolate import RBFInterpolator
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parent; O=P/'output';L=json.loads((P/'landmarks.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/workspace/hero_13/web-xiaqing-motion-lab/dist/assets/xiaqing_native_animated.glb')
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.name='Xiaqing_Native_Rig';rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
rig.data.pose_position='REST';body=bpy.data.objects['pl2020_Skin_Mat'];native=list(bpy.context.scene.objects)
for a in bpy.data.actions:a.use_fake_user=True
heads={b.name:np.array(rig.matrix_world@b.head_local) for b in rig.data.bones}
bpy.ops.import_scene.gltf(filepath=str(P/'vest_source.glb'));o=next(o for o in bpy.context.scene.objects if o not in native and o.type=='MESH');o.name='Vest_Body'
bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,L['neck_cut_z']),plane_no=(0,0,1),clear_outer=True)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free()
source=np.array([v.co[:] for v in o.data.vertices]);src=[];dst=[]
def add(a,b):src.append(a);dst.append(b)
for n in ['spine_0','spine_1','spine_2']:add(L['center'][n],heads[n])
add(L['center']['hips'],heads['hips']-np.array([0,0,.04]))
add(L['center']['neck_cut'],[0,.007,1.43])
# Neck contour guides prevent radial extrapolation near the cut.
for ang in np.linspace(0,2*np.pi,12,endpoint=False):
 add(np.array(L['center']['neck_cut'])+[.034*np.cos(ang),.027*np.sin(ang),0],[.060*np.cos(ang),.008+.050*np.sin(ang),1.43])
digit_names=['thumb','index','middle','ring','little'];chains={}
for side,sign in [('l',1),('r',-1)]:
 def mirror(v):return np.array(v)*[sign,1,1]
 for k,b in [('shoulder','arm_humerus'),('elbow','arm_radius'),('wrist','arm_wrist'),('hip','leg_femur'),('knee','leg_tibia'),('ankle','leg_ankle'),('ball','leg_ball'),('toe_tip','leg_ballEnd')]:add(mirror(L['left'][k]),heads[side+'_'+b])
 # Preserve sandal sole shape while fitting its foot to the barefoot ankle height.
 for xx,yy in [(-.025,.06),(.025,.06),(-.025,-.015),(.025,-.015)]:
  add([sign*(.061+xx),yy,0],[sign*(.111+xx*1.45),(yy-.045)*1.4,-.025])
 for finger in digit_names:
  chain=np.array([mirror(v) for v in L['left'][finger]]); names=[f'{side}_hand_{finger}_{i}' for i in range(len(chain)-1)];target=np.array([heads[n] for n in names]);tip=target[-1]+(target[-1]-target[-2])*.8;target=np.vstack([target,tip]);chains[(side,finger)]=(chain,target,names)
  for a,b in zip(chain,target):add(a,b)
# Thin plate displacement fitting preserves texture/triangles and fits all digit landmarks.
src=np.array(src);dst=np.array(dst);warp=RBFInterpolator(src,dst,kernel='thin_plate_spline',smoothing=1e-8,degree=1)
fitted=np.vstack([warp(v) for v in np.array_split(source,12)])
for v,pos in zip(o.data.vertices,fitted):v.co=pos
# Native weighted donor, allowing only anatomical body chains.
vpos=np.array([body.matrix_world@v.co for v in body.data.vertices]);weights=[]
allowed=lambda n:n in ['hips','COG','spine_0','spine_1','spine_2','neck_0','neck_1','head'] or n.startswith(('l_arm_','r_arm_','l_hand_','r_hand_','l_leg_','r_leg_'))
for v in body.data.vertices:weights.append({body.vertex_groups[g.group].name:g.weight for g in v.groups if allowed(body.vertex_groups[g.group].name)})
valid=[i for i,w in enumerate(weights) if sum(w.values())>.1];tree=cKDTree(vpos[valid])
for b in rig.data.bones:o.vertex_groups.new(name=b.name)
# Label distal fingers in original geometry, independent of transferred weights.
labels=np.zeros(len(source),dtype=int);finger_kd={};finger_indices={}
for si,side in enumerate(['l','r']):
 for fi,finger in enumerate(digit_names):
  ids=[i for i,w in enumerate(weights) if sum(v for k,v in w.items() if k.startswith(f'{side}_hand_{finger}_'))>.35];finger_indices[(side,finger)]=ids;finger_kd[(side,finger)]=cKDTree(vpos[ids])
for idx,p in enumerate(source):
 side='l' if p[0]>0 else 'r';scores=[]
 if abs(p[0])>.17 and p[2]<.632 and p[2]>.54 and p[1]<-.065:
  for fi,f in enumerate(digit_names):
   chain=chains[(side,f)][0];start=1 if f in ['ring','little'] else 0
   ds=[]
   for a,b in zip(chain[start:-1],chain[start+1:]):
    t=np.clip(np.dot(p-a,b-a)/np.dot(b-a,b-a),0,1);ds.append(np.linalg.norm(p-(a+t*(b-a))))
   # Finger starts beyond MCP; a narrow transition zone remains palm weighted.
   direction=chain[start+1]-chain[start];projection=np.dot(p-chain[start],direction)/np.linalg.norm(direction)
   if projection>-.005:scores.append((min(ds),fi,f))
  if scores:
   d,fi,f=min(scores)
   if d<.014:labels[idx]=1+fi+(0 if side=='l' else 5)
attribute=o.data.attributes.new('source_finger_id','INT','POINT');attribute.data.foreach_set('value',labels)
for idx,v in enumerate(o.data.vertices):
 lab=labels[idx];pos=fitted[idx];ww={}
 if lab:
  side='l' if lab<=5 else 'r';finger=digit_names[(lab-1)%5];ids=finger_indices[(side,finger)];ds,ii=finger_kd[(side,finger)].query(pos,k=4)
  donor=[ids[int(i)] for i in ii]
  permitted=lambda n:n.startswith(f'{side}_hand_{finger}_') or n==f'{side}_arm_wrist'
 else:
  ds,ii=tree.query(pos,k=4);donor=[valid[int(i)] for i in ii];permitted=lambda n:True
 for j,d in zip(donor,ds):
  for n,w in weights[j].items():
   if permitted(n):ww[n]=ww.get(n,0)+w/(float(d)+.002)**2
 top=sorted(ww.items(),key=lambda it:-it[1])[:4];total=sum(w for n,w in top)
 if total<1e-10:top=[('hips',1)];total=1
 for n,w in top:o.vertex_groups[n].add([idx],w/total,'REPLACE')
mod=o.modifiers.new('Native skinning','ARMATURE');mod.object=rig;o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
o['vest_outfit']=True;o['source_head_removed']=True;o['source_head_cut_z']=L['neck_cut_z'];o['source']='vest_source.glb';o['fit_method']='Anatomical landmark RBF, native skin transfer, isolated finger donors'
for p in o.data.polygons:p.use_smooth=True
# Retain the original Xia Qing head, hair and its lower neck transition.
keep=[]
for ob in native:
 if ob.type=='MESH' and (ob.name.startswith('tripo_part_') or ob.name in ['Xiaqing_fitted_bob','Neck_continuous_transition']):keep.append(ob)
 elif ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
# Build a shared-coordinate neck bridge between the source neck and original head.
neck=bpy.data.objects['Neck_continuous_transition'];nv=np.array([neck.matrix_world@v.co for v in neck.data.vertices]);zmin=nv[:,2].min();topids=np.where(nv[:,2]<zmin+.00001)[0]
def unique_ring(ids,vs):
 chosen={}
 for i in ids:chosen[tuple(np.round(vs[i],6))]=int(i)
 ids=list(chosen.values());c=np.mean(vs[ids],axis=0);return sorted(ids,key=lambda i:math.atan2(vs[i][1]-c[1],vs[i][0]-c[0]))
bottomids=unique_ring(np.where(source[:,2]>L['neck_cut_z']-.00001)[0],fitted);topids=unique_ring(topids,nv)
verts=[fitted[i] for i in bottomids]+[nv[i] for i in topids];N=len(bottomids);M=len(topids);faces=[];i=j=0
while i<N or j<M:
 if j==M or (i<N and (i+1)/N<=(j+1)/M):faces.append((i%N,(i+1)%N,N+j%M));i+=1
 else:faces.append((i%N,N+(j+1)%M,N+j%M));j+=1
me=bpy.data.meshes.new('NeckBridge');me.from_pydata(verts,[],faces);me.update();bridge=bpy.data.objects.new('Vest_NeckBridge',me);bpy.context.collection.objects.link(bridge)
for b in rig.data.bones:bridge.vertex_groups.new(name=b.name)
for i,idx in enumerate(bottomids):
 for g in o.data.vertices[idx].groups:bridge.vertex_groups[o.vertex_groups[g.group].name].add([i],g.weight,'REPLACE')
for i,idx in enumerate(topids):
 for g in neck.data.vertices[idx].groups:bridge.vertex_groups[neck.vertex_groups[g.group].name].add([N+i],g.weight,'REPLACE')
mod=bridge.modifiers.new('Native neck skinning','ARMATURE');mod.object=rig;bridge.parent=rig;bridge.matrix_parent_inverse=rig.matrix_world.inverted();bridge['vest_outfit']=True
mat=bpy.data.materials.new('Neck skin blend');mat.diffuse_color=(.42,.28,.21,1);mat.use_nodes=True;mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=mat.diffuse_color;mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.8;me.materials.append(mat)
for f in me.polygons:f.use_smooth=True
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
# Persist exact seam pairs for animation seam validation.
(P/'seam_pairs.json').write_text(json.dumps({'bottom':[[i,idx] for i,idx in enumerate(bottomids)],'top':[[N+i,idx] for i,idx in enumerate(topids)],'body':'Vest_Body','bridge':'Vest_NeckBridge','head':'Neck_continuous_transition'}))
# Render setup.
s=bpy.context.scene;s.world=bpy.data.worlds.new('Studio');s.world.color=(.22,.22,.22);s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.light='STUDIO';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.render.resolution_x=850;s.render.resolution_y=1100;s.render.resolution_percentage=100
bpy.ops.object.camera_add(location=(.4,-4,1.5));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.95;s.camera=cam
rig.data.pose_position='REST';s.render.filepath=str(O/'rest_front.png');bpy.ops.render.render(write_still=True)
rig.data.pose_position='POSE'
for action in bpy.data.actions:
 if not action.name.startswith(('Idle','Walk','Run')):continue
 rig.animation_data.action=action;s.frame_set(round(action.frame_range[1]*.35));s.render.filepath=str(O/(action.name.split('_')[0]+'_front.png'));bpy.ops.render.render(write_still=True)
rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));s.frame_set(1)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'vest_xiaqing.blend'),compress=True)
(P/'build_report.json').write_text(json.dumps({'source_vertices':79525,'body_vertices':len(source),'native_bones':len(rig.data.bones),'finger_labels':{str(k):int(sum(labels==k)) for k in range(1,11)},'neck_bottom':N,'neck_top':M,'landmark_max_error':float(np.max(np.linalg.norm(warp(src)-dst,axis=1)))},indent=2))
print('BUILD COMPLETE')
