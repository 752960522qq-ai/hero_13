import bpy,bmesh,math,json
from mathutils import Vector,Matrix,Quaternion
ROOT='/workspace/scratch/7b171b7361b3/'
OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/'
bpy.ops.wm.open_mainfile(filepath='/tmp/old_xiaqing/xiaqing_optimized.blend')
old=bpy.data.objects['XiaQing_Rig'];names=[b.name for b in old.data.bones if not b.name.startswith('Skirt')];rest={n:old.data.bones[n].matrix_local.copy() for n in names};motions={}
for track in old.animation_data.nla_tracks:track.mute=True
for action in bpy.data.actions:
 old.animation_data.action=action;start,end=map(int,action.frame_range);frames=[]
 for f in range(start,end+1):
  bpy.context.scene.frame_set(f);frames.append(({n:old.pose.bones[n].matrix.to_quaternion().copy() for n in names},old.pose.bones['Hips'].matrix.translation.copy()))
 motions[action.name]=frames
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
bpy.ops.import_scene.gltf(filepath=ROOT+'upload/xiaqing_trousers.glb')
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
for o in meshes:
 world=o.matrix_world.copy();o.parent=None;o.matrix_world=world;bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# The input is a single surface partitioned into material islands. Weld shared
# borders into one continuous skin and retain every original texture/UV chart.
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();obj=meshes[0];obj.name='XiaQing_Jeans_Surface';obj.data.name='XiaQing_Jeans_Mesh'
bm=bmesh.new();bm.from_mesh(obj.data);before=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000006);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
openbefore=sum(e.is_boundary for e in bm.edges);result=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
# Fill UVs on tiny source punctures from adjacent surface loops.
uv=bm.loops.layers.uv.active
for face in result.get('faces',[]):
 for loop in face.loops:
  adjacent=next((l for l in loop.vert.link_loops if l.face not in result['faces']),None)
  if adjacent and uv:loop[uv].uv=adjacent[uv].uv;face.material_index=adjacent.face.material_index
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));closed=sum(e.is_boundary for e in bm.edges);nm=sum(not e.is_manifold for e in bm.edges);after=len(bm.verts);bm.to_mesh(obj.data);bm.free()
print('SURFACE',before,after,'before openings',openbefore,'after',closed,'nonmanifold',nm,flush=True)
data=bpy.data.armatures.new('XiaQing_Jeans_Skeleton');rig=bpy.data.objects.new('夏晴_牛仔裤',data);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
spec={'Hips':((0,.005,.535),(0,.005,.59),None),'Spine':((0,.005,.59),(0,.005,.665),'Hips'),'Spine1':((0,.005,.665),(0,.005,.73),'Spine'),'Spine2':((0,.005,.73),(0,.005,.795),'Spine1'),'Neck':((0,.005,.795),(0,.005,.84),'Spine2'),'Head':((0,.005,.84),(0,.005,.965),'Neck')}
for side,s in [('Left',1),('Right',-1)]:
 spec.update({side+'Shoulder':((s*.025,.005,.79),(s*.105,.002,.788),'Spine2'),side+'Arm':((s*.105,.002,.788),(s*.222,-.008,.772),side+'Shoulder'),side+'ForeArm':((s*.222,-.008,.772),(s*.323,-.026,.754),side+'Arm'),side+'Hand':((s*.323,-.026,.754),(s*.38,-.062,.752),side+'ForeArm'),side+'UpLeg':((s*.047,.005,.525),(s*.061,.002,.296),'Hips'),side+'Leg':((s*.061,.002,.296),(s*.060,.012,.082),side+'UpLeg'),side+'Foot':((s*.060,.012,.082),(s*.060,-.05,.029),side+'Leg'),side+'ToeBase':((s*.060,-.05,.029),(s*.060,-.083,.025),side+'Foot')})
for n,(h,t,p) in spec.items():
 b=data.edit_bones.new(n);b.head=h;b.tail=t
 if p:b.parent=data.edit_bones[p]
 if any(n.endswith(x) for x in ['Arm','ForeArm','Hand']):b.align_roll(Vector((0,-1,0)))
 else:b.align_roll(rest[n].to_quaternion()@Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,t):return {a:1-t,b:t}
def torso(z):
 if z<.58:return {'Hips':1}
 if z<.65:return mix('Hips','Spine',smooth(.58,.65,z))
 if z<.72:return mix('Spine','Spine1',smooth(.65,.72,z))
 if z<.785:return mix('Spine1','Spine2',smooth(.72,.785,z))
 if z<.825:return mix('Spine2','Neck',smooth(.785,.825,z))
 return mix('Neck','Head',smooth(.825,.855,z))
# Track surface material membership so long hair never follows the arm beneath it.
materials=[set() for _ in obj.data.vertices]
for face in obj.data.polygons:
 idx=int(obj.data.materials[face.material_index].name.split('_')[2])
 for vi in face.vertices:materials[vi].add(idx)
groups={n:obj.vertex_groups.new(name=n) for n in names}
for v in obj.data.vertices:
 x,y,z=v.co;a=abs(x);side='Left' if x>=0 else 'Right';mat=materials[v.index]
 hair=bool(mat & {0,12,13,14})
 if z>.855:w={'Head':1}
 elif hair and z>.64:w=mix('Spine2','Head',smooth(.68,.84,z))
 elif a>.08 and z>.69:
  if a<.20:arm={side+'Arm':1}
  elif a<.25:arm=mix(side+'Arm',side+'ForeArm',smooth(.20,.25,a))
  elif a<.30:arm={side+'ForeArm':1}
  else:arm=mix(side+'ForeArm',side+'Hand',smooth(.30,.34,a))
  f=smooth(.078,.125,a)*smooth(.69,.76,z);w={n:a*(1-f) for n,a in torso(z).items()}
  for n,value in arm.items():w[n]=w.get(n,0)+value*f
 elif z>.535:w=torso(z)
 elif z>.44:
  f=1-smooth(.44,.55,z);f*=1-.65*(1-smooth(.008,.04,a))*smooth(.43,.49,z);lr=smooth(-.018,.018,x);w={'Hips':1-f,'LeftUpLeg':f*lr,'RightUpLeg':f*(1-lr)}
 elif z>.325:w={side+'UpLeg':1}
 elif z>.265:w=mix(side+'Leg',side+'UpLeg',smooth(.265,.325,z))
 elif z>.105:w={side+'Leg':1}
 elif mat & {7,8}:w={side+'Foot':1}
 else:w=mix(side+'Foot',side+'Leg',smooth(.06,.105,z))
 top=sorted(((n,a) for n,a in w.items() if a>1e-8),key=lambda t:t[1],reverse=True)[:4];total=sum(a for n,a in top)
 for n,a in top:groups[n].add([v.index],a/total,'REPLACE')
mod=obj.modifiers.new('XiaQing_Jeans_Skin','ARMATURE');mod.object=rig;obj.parent=rig
rig.animation_data_create();scene=bpy.context.scene;scene.render.fps=30
newrest={n:data.bones[n].matrix_local.copy() for n in names}
# T-pose arms use the source's anatomical global orientation; torso/legs retain
# target rest alignment while receiving the same source motion delta.
shoeids=[i for i,m in enumerate(materials) if m & {7,8}]
for label,frames in motions.items():
 action=bpy.data.actions.new(label);rig.animation_data.action=action
 for f,(source,root) in enumerate(frames,1):
  scene.frame_set(f)
  for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4);p.rotation_mode='QUATERNION'
  for n in names:
   p=rig.pose.bones[n]
   if p.parent:head=p.parent.matrix@p.parent.bone.matrix_local.inverted()@p.bone.head_local
   else:head=p.bone.head_local+(root-rest['Hips'].translation)
   q=source[n]
   if any(n.endswith(x) for x in ['Arm','ForeArm','Hand']):
    sign=1 if n.startswith('Left') else -1;neutral=Quaternion((0,1,0),sign*math.radians(70))@newrest[n].to_quaternion();q=q@rest[n].to_quaternion().inverted()@neutral
   else:q=q@rest[n].to_quaternion().inverted()@newrest[n].to_quaternion()
   if n.endswith('Hand') and label!='HandTest':
    fore=n.replace('Hand','ForeArm');q=rig.pose.bones[fore].matrix.to_quaternion()@newrest[fore].to_quaternion().inverted()@newrest[n].to_quaternion()
   p.matrix=Matrix.Translation(head)@q.to_matrix().to_4x4();bpy.context.view_layer.update()
  # Ground using the evaluated sneaker vertices.
  ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());lo=min(ev.data.vertices[i].co.z for i in shoeids)
  p=rig.pose.bones['Hips'];p.location+=p.bone.matrix_local.to_quaternion().inverted()@Vector((0,0,-lo));bpy.context.view_layer.update()
  for p in rig.pose.bones:
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
 rig.animation_data.action=None;t=rig.animation_data.nla_tracks.new();t.name=label;t.strips.new(label,1,action);t.mute=True
 print('BAKED',label,len(frames),flush=True)
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);rig['character']='夏晴_牛仔裤';rig['version']='4.0';obj['character']='夏晴_牛仔裤'
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'xiaqing_trousers_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
with open(OUT+'jeans-report.json','w') as f:json.dump({'character':'夏晴_牛仔裤','bones':len(names),'clips':list(motions),'source_vertices':before,'welded_vertices':after,'open_edges_before_repair':openbefore,'open_edges_after_repair':closed,'nonmanifold_edges':nm},f,ensure_ascii=False,indent=2)
print('JEANS_RIG_COMPLETE',flush=True)
