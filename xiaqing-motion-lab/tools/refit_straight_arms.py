"""v5.0: straight rest arms, body.glb fists, periodic walk root smoothing."""
import bpy,bmesh,math,json,zipfile
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/base/xiaqing_trousers.blend');r=bpy.data.objects['夏晴_牛仔裤'];body=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
rest={b.name:b.matrix_local.copy() for b in r.data.bones};lengths={b.name:b.length for b in r.data.bones};motions={}
for label in ['Idle','Walk','Run','ArmRaise','HandTest']:
 a=bpy.data.actions[label];r.animation_data.action=a;frames=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();frames.append({p.name:p.matrix.copy() for p in r.pose.bones})
 motions[label]=frames
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
# Rebuild horizontal rest chains, preserving limb lengths and shoulder anchors.
bpy.context.view_layer.objects.active=r;r.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for side,sign in [('Left',1),('Right',-1)]:
 eb=r.data.edit_bones;arm=eb[side+'Arm'];start=arm.head.copy();axis=Vector((sign,0,0))
 for suffix in ['Arm','ForeArm','Hand']:
  b=eb[side+suffix];b.head=start;b.tail=start+axis*lengths[b.name];b.align_roll(Vector((0,-1,0)));start=b.tail.copy()
 b=eb[side+'Elbow'];b.head=eb[side+'ForeArm'].head;b.tail=b.head+axis*.025;b.align_roll(Vector((0,-1,0)))
 b=eb[side+'FingerCurl'];b.head=eb[side+'Hand'].head+axis*.032;b.tail=b.head+axis*.035;b.align_roll(Vector((0,-1,0)))
bpy.ops.object.mode_set(mode='OBJECT');newrest={b.name:b.matrix_local.copy() for b in r.data.bones}
# Rebind mesh into the new rest skeleton with existing normalized weights.
trans={n:newrest[n]@rest[n].inverted() for n in rest};groups={g.index:g.name for g in body.vertex_groups}
for v in body.data.vertices:
 w=[(groups[g.group],g.weight) for g in v.groups if groups[g.group] in trans];total=sum(t for _,t in w)
 if total:v.co=sum((trans[n]@v.co*t for n,t in w),Vector())/total
# Flatten residual arm centerline curvature without altering the cross-section.
armids={i for i,m in enumerate(body.data.materials) if m and any(f'tripo_part_{n}_material' in m.name for n in [5,6])};ids=set(i for p in body.data.polygons if p.material_index in armids for i in p.vertices)
for side,sign in [('Left',1),('Right',-1)]:
 anchor=newrest[side+'Arm'].translation;vs=[v for v in body.data.vertices if v.index in ids and sign*v.co.x>.13]
 bins=np.linspace(.14,.32,19);centers=[]
 for x in bins:
  pts=[v.co for v in vs if abs(sign*v.co.x-x)<.006]
  centers.append([(min(p[k] for p in pts)+max(p[k] for p in pts))/2 if pts else anchor[k] for k in [1,2]])
 centers=np.array(centers)
 for v in vs:
  x=sign*v.co.x;blend=min(1,max(0,(x-.13)/.035))
  for j,k in enumerate([1,2]):v.co[k]+=blend*(anchor[k]-float(np.interp(x,bins,centers[:,j])))
# Replace previous fists. Source right fist is joined into the arm, so cut it at wrist.
for ob in list(s.objects):
 if '拳头' in ob.name:bpy.data.objects.remove(ob,do_unlink=True)
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(ROOT/'source-models/body.glb'));imports=set(bpy.data.objects)-before
skin=bpy.data.materials['夏晴_自然肤色_拳头'];created=[];fiststats=[]
for side,sign,parts in [('Left',1,[12]),('Right',-1,[12])]:
 chunks=[]
 for idx in parts:
  src=next(o for o in imports if o.name==f'tripo_part_{idx}');bm=bmesh.new();bm.from_mesh(src.data);bmesh.ops.transform(bm,matrix=src.matrix_world,verts=list(bm.verts))
  if sign<0:bmesh.ops.transform(bm,matrix=Matrix.Diagonal((-1,1,1,1)),verts=list(bm.verts))
  cut=.344
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(sign*cut,0,0),plane_no=(sign,0,0),clear_inner=True,clear_outer=False)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
  mesh=bpy.data.meshes.new(side+str(idx));bm.to_mesh(mesh);bm.free();chunks.append(mesh)
 verts=[];faces=[]
 wrist=newrest[side+'Hand'].translation
 for mesh in chunks:
  off=len(verts)
  for v in mesh.vertices:
   d=v.co-Vector((sign*.344,-.030,.761));verts.append(wrist+Vector((d.x-sign*.004,d.y,d.z)))
  faces += [tuple(off+i for i in p.vertices) for p in mesh.polygons]
 mesh=bpy.data.meshes.new(side+'_BodyFist');mesh.from_pydata(verts,[],faces);mesh.materials.append(skin)
 for p in mesh.polygons:p.use_smooth=True
 ob=bpy.data.objects.new(side+'_拳头',mesh);s.collection.objects.link(ob);ob.parent=r;ob.matrix_world=Matrix.Identity(4);vg=ob.vertex_groups.new(name=side+'Hand');vg.add(list(range(len(verts))),1,'REPLACE');mod=ob.modifiers.new('Skin','ARMATURE');mod.object=r;ob['source']='body.glb';created.append(ob)
 bm=bmesh.new();bm.from_mesh(mesh);fiststats.append({'side':side,'vertices':len(verts),'open_edges':sum(e.is_boundary for e in bm.edges)});assert fiststats[-1]['open_edges']==0;bm.free()
for ob in imports:bpy.data.objects.remove(ob,do_unlink=True)
# Remove per-frame grounding discontinuities with a small periodic root fit.
walk=motions['Walk'];oldz=np.array([p['Hips'].translation.z for p in walk]);N=len(walk)-1;phase=np.arange(N)*2*np.pi/N;X=np.column_stack([np.ones(N),np.sin(phase),np.cos(phase),np.sin(2*phase),np.cos(2*phase)])
coef=np.linalg.lstsq(X,oldz[:N],rcond=None)[0];coef[1:]*=.8;newz=X@coef;newz=np.r_[newz,newz[0]]
# Disable mesh evaluation while baking bone-only transforms.
for ob in [body]+created:
 for mod in ob.modifiers:
  if mod.type=='ARMATURE':mod.show_viewport=False
# Bake arm rotations against the straight rest rig, and use two-bone leg IK to retain feet.
ordered=sorted(r.pose.bones,key=lambda p:len(p.parent_recursive));checks=[]
for label,frames in motions.items():
 a=bpy.data.actions[label];r.animation_data.action=a
 for f,pose in enumerate(frames,1):
  s.frame_set(f);target={n:m.copy() for n,m in pose.items()}
  for side in ['Left','Right']:
   for suffix in ['Arm','ForeArm','Hand','Elbow','FingerCurl']:
    n=side+suffix;par=r.data.bones[n].parent.name;head=target[par]@newrest[par].inverted()@newrest[n].translation;target[n]=Matrix.Translation(head)@pose[n].to_quaternion().to_matrix().to_4x4()
  if label=='Walk':
   dz=float(newz[f-1]-oldz[f-1]);shift=Vector((0,0,dz))
   for n in target:target[n].translation+=shift
   for side in ['Left','Right']:
    un=side+'UpLeg';ln=side+'Leg';fn=side+'Foot';tn=side+'ToeBase';hip=target[un].translation.copy();ankle=pose[fn].translation.copy();d=ankle-hip;dist=d.length;axis=d.normalized();L1=lengths[un];L2=lengths[ln]
    along=(L1*L1-L2*L2+dist*dist)/(2*dist);height=math.sqrt(max(0,L1*L1-along*along));bend=pose[ln].translation-hip;perp=bend-axis*bend.dot(axis);perp.normalize();knee=hip+axis*along+perp*height
    for n,start,end in [(un,hip,knee),(ln,knee,ankle)]:
     oldaxis=pose[n].to_quaternion()@Vector((0,1,0));q=oldaxis.rotation_difference((end-start).normalized())@pose[n].to_quaternion();target[n]=Matrix.Translation(start)@q.to_matrix().to_4x4()
    target[fn]=pose[fn];target[tn]=pose[tn]
  for p in ordered:
   p.matrix=target[p.name];bpy.context.view_layer.update()
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
  if label in ['Idle','Walk']:
   for side in ['Left','Right']:
    a1=r.pose.bones[side+'Arm'];a2=r.pose.bones[side+'ForeArm'];assert (a1.tail-a1.head).angle(a2.tail-a2.head)<.002
  if label=='Walk':
   for side in ['Left','Right']:assert (r.pose.bones[side+'Foot'].head-pose[side+'Foot'].translation).length<1e-5
 # Linear samples avoid spline overshoot between baked frames.
 for fc in a.fcurves:
  for key in fc.keyframe_points:key.interpolation='LINEAR'
 checks.append({'clip':label,'frames':len(frames)})
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='5.0'
for ob in [body]+created:
 for mod in ob.modifiers:
  if mod.type=='ARMATURE':mod.show_viewport=True
report={'version':'5.0','fists':fiststats,'right_fist_source':'mirrored left fist from body.glb; right source surface malformed','rest_elbows_degrees':[math.degrees((r.data.bones[x+'Arm'].tail_local-r.data.bones[x+'Arm'].head_local).angle(r.data.bones[x+'ForeArm'].tail_local-r.data.bones[x+'ForeArm'].head_local)) for x in ['Left','Right']],'walk_max_vertical_step_before':float(max(abs(np.diff(oldz)))),'walk_max_vertical_step_after':float(max(abs(np.diff(newz)))),'walk_foot_positions_preserved':True,'clips':checks}
(OUT/'straight-arms-fists-walk-report.json').write_text(json.dumps(report,indent=2));print('REPORT',report,flush=True)
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,body]+created:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
