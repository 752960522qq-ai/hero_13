"""v4.2: isolate elbow skin from torso; keep jaw rigid with head."""
import bpy,bmesh,json,math,zipfile
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend')
o=bpy.data.objects['XiaQing_Jeans_Surface'];r=bpy.data.objects['夏晴_牛仔裤'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
mats=[set() for v in o.data.vertices]
for p in o.data.polygons:
 idx=int(o.data.materials[p.material_index].name.split('_')[2])
 for i in p.vertices:mats[i].add(idx)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def assign(v,w):
 for g in o.vertex_groups:g.remove([v.index])
 for n,a in w.items():
  if a>1e-8:o.vertex_groups[n].add([v.index],a,'REPLACE')
elbows=[];heads=[]
for v in o.data.vertices:
 x,y,z=v.co;a=abs(x);side='Left' if x>0 else 'Right'
 if mats[v.index]&{5,6} and .15<a<.26:
  # Wide anatomical bend zone; no torso contribution beyond upper arm.
  b=r.data.bones[side+'Arm'];axis=(b.tail_local-b.head_local).normalized();d=(v.co-b.tail_local).dot(axis)
  t=smooth(-.032,.032,d);assign(v,{side+'Arm':1-t,side+'ForeArm':t});elbows.append(v.index)
 if 11 in mats[v.index] and z>.79:
  # Entire jaw/face rigid; transition confined to lower neck.
  t=smooth(.79,.818,z);assign(v,{'Neck':1-t,'Head':t});heads.append(v.index)
checks=[]
for label,f in [('Walk',18),('Run',9),('ArmRaise',61)]:
 r.animation_data.action=bpy.data.actions[label];s.frame_set(f);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 H=r.pose.bones['Head'].matrix@r.data.bones['Head'].matrix_local.inverted()
 err=max((ev.data.vertices[i].co-H@o.data.vertices[i].co).length for i in heads if o.data.vertices[i].co.z>=.818)
 assert err<1e-5
 assert all(all(math.isfinite(c) for c in ev.data.vertices[i].co) for i in elbows)
 checks.append({'clip':label,'frame':f,'jaw_rigid_error':err})
for i in elbows:
 assert all(o.vertex_groups[g.group].name.endswith(('Arm','ForeArm')) for g in o.data.vertices[i].groups)
b=bmesh.new();b.from_mesh(o.data);boundary=sum(e.is_boundary for e in b.edges);b.free();assert boundary==0
r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
s.frame_set(1);r['version']='4.2'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
out='/workspace/sites/xiaqing-motion-lab/dist/assets/'
with zipfile.ZipFile(out+'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in r.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);r.select_set(True)
bpy.ops.export_scene.gltf(filepath=out+'xiaqing_trousers_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
report={'version':'4.2','elbow_vertices':len(elbows),'head_neck_vertices':len(heads),'boundary_edges':boundary,'checks':checks}
with open(out+'elbow-head-fix-report.json','w') as f:json.dump(report,f,indent=2)
print('FIX_RESULT',report)
