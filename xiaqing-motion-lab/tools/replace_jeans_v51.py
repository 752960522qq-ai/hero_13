"""Fit the uploaded replacement mesh to existing five clips and a straight T pose.
Input base: extract v5.0 xiaqing_trousers.blend.zip into /tmp/current.
"""
import bpy,bmesh,math,json,zipfile
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets'
bpy.ops.wm.open_mainfile(filepath='/tmp/current/xiaqing_trousers.blend');r=bpy.data.objects['夏晴_牛仔裤'];old=bpy.data.objects['XiaQing_Jeans_Surface'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
# Disable expensive mesh evaluation during skeletal rebaking.
for ob in s.objects:
 for mod in ob.modifiers:
  if mod.type=='ARMATURE':mod.show_viewport=False
rest={b.name:b.matrix_local.copy() for b in r.data.bones};motions={}
for label in ['Idle','Walk','Run','ArmRaise','HandTest']:
 a=bpy.data.actions[label];r.animation_data.action=a;frames=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();frames.append({p.name:p.matrix.copy() for p in r.pose.bones})
 motions[label]=frames
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
# Transfer the established body weights; explicit arm weights below avoid torso leakage.
kd=KDTree(len(old.data.vertices));oldw=[];gn={g.index:g.name for g in old.vertex_groups}
for v in old.data.vertices:
 kd.insert(v.co,v.index);oldw.append({gn[g.group]:g.weight for g in v.groups})
kd.balance()
bpy.ops.object.select_all(action='DESELECT');before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(ROOT/'source-models/xiaqing_trousers_v51.glb'));imported=set(bpy.data.objects)-before;meshes=[o for o in imported if o.type=='MESH']
for ob in meshes:
 mat=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=mat;bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# Sample the actual skin centerline, retaining cross-section and the original fists.
centers={};bins=np.linspace(.145,.345,21)
for side,sign,idx in [('Left',1,11),('Right',-1,10)]:
 ob=next(o for o in meshes if o.name==f'tripo_part_{idx}');values=[]
 for x in bins:
  ps=[v.co for v in ob.data.vertices if abs(sign*v.co.x-x)<.007]
  assert ps
  values.append([(min(p[k] for p in ps)+max(p[k] for p in ps))*.5 for k in [1,2]])
 centers[side]=np.array(values)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
warped=0
for ob in meshes:
 for v in ob.data.vertices:
  x,y,z=v.co;ax=abs(x)
  if ax<=.105 or not .70<z<.83:continue
  side='Left' if x>0 else 'Right';blend=smooth(.105,.155,ax)
  for j,k,target in [(0,1,.002),(1,2,.788)]:v.co[k]+=blend*(target-float(np.interp(ax,bins,centers[side][:,j])))
  warped+=1
# Join and weld material borders so deformation cannot separate adjacent parts.
bpy.ops.object.select_all(action='DESELECT')
for ob in meshes:ob.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();body=meshes[0];body.name='Replacement_Surface';body.data.name='XiaQing_Jeans_v51_Mesh'
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000006);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bad=[e for e in bm.edges if len(e.link_faces)>2];bmesh.ops.split_edges(bm,edges=bad);open_before=sum(e.is_boundary for e in bm.edges);filled=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0).get('faces',[]);newfaces=set(filled);uv=bm.loops.layers.uv.active
for face in filled:
 for loop in face.loops:
  adjacent=next((l for l in loop.vert.link_loops if l.face not in newfaces),None)
  if adjacent:
   face.material_index=adjacent.face.material_index
   if uv:loop[uv].uv=adjacent[uv].uv
# Cap any residual branched source rims with local edge triangles.
remaining=[e for e in bm.edges if e.is_boundary]
print('RESIDUAL_RIM',len(remaining),flush=True)
while remaining:
 seed=remaining[0];component={seed};verts=set(seed.verts);changed=True
 while changed:
  added={e for e in remaining if e not in component and any(v in verts for v in e.verts)};changed=bool(added);component.update(added)
  for e in added:verts.update(e.verts)
 center=bm.verts.new(sum((v.co for v in verts),Vector())/len(verts))
 for e in component:
  face=bm.faces.new((e.verts[0],e.verts[1],center));neighbor=next((f for f in e.link_faces if f!=face),None)
  if neighbor:face.material_index=neighbor.material_index
  if uv and neighbor:
   for loop in face.loops:
    adjacent=next((l for l in neighbor.loops if l.vert==loop.vert),neighbor.loops[0]);loop[uv].uv=adjacent[uv].uv
 remaining=[e for e in remaining if e not in component]
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));open_after=sum(e.is_boundary for e in bm.edges);print('OPEN_AFTER',open_after,flush=True);bm.to_mesh(body.data);bm.free();assert open_after==0
# Fit shoulders, elbow and wrist to this mesh; rest arms remain exactly horizontal.
bpy.context.view_layer.objects.active=r;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for side,sign in [('Left',1),('Right',-1)]:
 eb=r.data.edit_bones;eb[side+'Shoulder'].tail=(sign*.12,.002,.788)
 for suffix,x0,x1 in [('Arm',.12,.235),('ForeArm',.235,.350),('Hand',.350,.405),('Elbow',.235,.260),('FingerCurl',.382,.405)]:
  b=eb[side+suffix];b.head=(sign*x0,.002,.788);b.tail=(sign*x1,.002,.788);b.align_roll(Vector((0,-1,0)))
bpy.ops.object.mode_set(mode='OBJECT');newrest={b.name:b.matrix_local.copy() for b in r.data.bones}
# Establish weights on the replacement. Face/jaw and fists remain rigid within their regions.
vg={b.name:body.vertex_groups.new(name=b.name) for b in r.data.bones};minsum=1;maxsum=1
for v in body.data.vertices:
 x,y,z=v.co;ax=abs(x);side='Left' if x>=0 else 'Right'
 nearest=kd.find_n(v.co,3);w={};total=0
 for co,idx,d in nearest:
  factor=1/max(d,.0002)**2;total+=factor
  for n,weight in oldw[idx].items():w[n]=w.get(n,0)+factor*weight
 w={n:value/total for n,value in w.items()}
 if ax>.12 and .70<z<.85:
  if ax<.235:
   t=smooth(.200,.235,ax);arm={side+'Arm':1-t,side+'Elbow':t}
  elif ax<.275:
   t=smooth(.235,.275,ax);arm={side+'Elbow':1-t,side+'ForeArm':t}
  else:
   t=smooth(.332,.362,ax);arm={side+'ForeArm':1-t,side+'Hand':t}
  blend=smooth(.12,.155,ax);w={n:value*(1-blend) for n,value in w.items()}
  for n,value in arm.items():w[n]=w.get(n,0)+blend*value
 if z>.831:w={'Head':1}
 elif z>.805 and ax<.052:
  t=smooth(.805,.831,z);w={'Neck':1-t,'Head':t}
 if z<.075:w={side+'Foot':1}
 w=sorted(((n,value) for n,value in w.items() if value>1e-7),key=lambda x:x[1],reverse=True)[:4];total=sum(value for _,value in w);assert total>0
 for n,value in w:vg[n].add([v.index],value/total,'REPLACE')
body.parent=r;body.matrix_world=Matrix.Identity(4);mod=body.modifiers.new('XiaQing_Skin','ARMATURE');mod.object=r;mod.show_viewport=False
# Remove all old character meshes, retaining only the new uploaded mesh and rig.
for ob in list(s.objects):
 if ob.type=='MESH' and ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
body.name='XiaQing_Jeans_Surface'
ordered=sorted(r.pose.bones,key=lambda p:len(p.parent_recursive))
for label,frames in motions.items():
 action=bpy.data.actions[label];r.animation_data.action=action
 for f,pose in enumerate(frames,1):
  s.frame_set(f);targets={}
  for p in ordered:
   n=p.name;parent=p.parent
   head=targets[parent.name]@newrest[parent.name].inverted()@newrest[n].translation if parent else pose[n].translation
   # Keep source animation orientation; changes are limited to rest proportions.
   targets[n]=Matrix.Translation(head)@pose[n].to_quaternion().to_matrix().to_4x4();p.matrix=targets[n];bpy.context.view_layer.update()
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=n)
 for fc in action.fcurves:
  for key in fc.keyframe_points:key.interpolation='LINEAR'
 print('BAKED',label,len(frames),flush=True)
mod.show_viewport=True;checks=[]
for label,frame in [('Idle',1),('Walk',10),('Run',9),('ArmRaise',60),('HandTest',23)]:
 r.animation_data.action=bpy.data.actions[label];s.frame_set(frame);bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());assert all(math.isfinite(c) for v in ev.data.vertices for c in v.co)
 angles=[]
 for side in ['Left','Right']:
  a=r.pose.bones[side+'Arm'];b=r.pose.bones[side+'ForeArm'];angles.append(math.degrees((a.tail-a.head).angle(b.tail-b.head)));assert (a.tail-b.head).length<1e-5;assert (b.tail-r.pose.bones[side+'Hand'].head).length<1e-5
 if label in ['Idle','Walk']:assert max(angles)<.1
 checks.append({'clip':label,'frame':frame,'elbow_degrees':angles,'finite_mesh':True})
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='5.1';r['source_model']='xiaqing_trousers(1).glb'
report={'version':'5.1','source':'xiaqing_trousers(1).glb','vertices':len(body.data.vertices),'arm_vertices_adjusted':warped,'open_edges_before':open_before,'open_edges_after':open_after,'rest_elbows_degrees':[0,0],'checks':checks,'walk_root_motion':'preserved v5.0 smoothed height curve'}
(OUT/'replacement-model-v51-report.json').write_text(json.dumps(report,indent=2));print('REPORT',report,flush=True)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
