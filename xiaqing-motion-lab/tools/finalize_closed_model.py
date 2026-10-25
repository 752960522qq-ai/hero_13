import bpy,bmesh,json,math
from mathutils import Matrix,Quaternion,Vector
OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/'
bpy.ops.wm.open_mainfile(filepath=OUT+'xiaqing_optimized.blend')
rig=bpy.data.objects['XiaQing_Rig'];body=bpy.data.objects['XiaQing_Body'];scene=bpy.context.scene
old=body.data.uv_layers.get('UVMap');new=body.data.uv_layers.get('ReprojectedUV')
if new:
 for face in body.data.polygons:
  mat=body.data.materials[face.material_index].name
  if mat not in ['tripo_part_7_material','tripo_part_9_material','tripo_part_12_material']:
   for li in face.loop_indices:old.data[li].uv=new.data[li].uv
 body.data.uv_layers.remove(new)
 body.data.uv_layers.active=old;old.active_render=True
# A continuous field across the waistband prevents abrupt torso-to-skirt weight jumps.
cloth=bpy.data.objects['XiaQing_Dress']
with bpy.data.libraries.load('/tmp/xiaqing_pretriang.blend',link=False) as (src,dst):dst.meshes=['XiaQing_Dress_Mesh']
cloth.data=dst.meshes[0]
cloth.vertex_groups.clear();groups={n:cloth.vertex_groups.new(name=n) for n in rig.data.bones.keys()}
def smooth(a,b,z):
 t=max(0,min(1,(z-a)/(b-a)));return t*t*(3-2*t)
def torso(z):
 if z<.58:return {'Hips':1}
 if z<.65:t=smooth(.58,.65,z);return {'Hips':1-t,'Spine':t}
 if z<.71:t=smooth(.65,.71,z);return {'Spine':1-t,'Spine1':t}
 t=smooth(.71,.78,z);return {'Spine1':1-t,'Spine2':t}
panels=['SkirtFront','SkirtFrontLeft','SkirtBackLeft','SkirtBack','SkirtBackRight','SkirtFrontRight']
for v in cloth.data.vertices:
 x,y,z=v.co;f=(1-smooth(.36,.62,z))*smooth(.035,.085,math.hypot(x,y-.005));w={n:a*(1-f) for n,a in torso(z).items()};theta=(math.atan2(y-.005,x)+math.pi/2)%(2*math.pi);t=theta/(math.pi/3);i=int(t)%6;u=t-int(t);u=u*u*(3-2*u);w[panels[i]]=f*(1-u);w[panels[(i+1)%6]]=f*u
 for n,a in w.items():
  if a>1e-7:groups[n].add([v.index],a,'REPLACE')
# Improve trailing-leg clearance while keeping coherent panel motion.
names=['SkirtFront','SkirtFrontLeft','SkirtBackLeft','SkirtBack','SkirtBackRight','SkirtFrontRight']
for action in bpy.data.actions:
 rig.animation_data.action=action
 for frame in range(int(action.frame_range[0]),int(action.frame_range[1])+1):
  scene.frame_set(frame);bpy.context.view_layer.update();hip=rig.pose.bones['Hips'];hipdef=hip.matrix@hip.bone.matrix_local.inverted();legangles=[]
  for side in ['Left','Right']:
   p=rig.pose.bones[side+'UpLeg'];v=hipdef.to_quaternion().inverted()@(p.tail-p.head);rest=p.bone.tail_local-p.bone.head_local;legangles.append(math.atan2(v.y,-v.z)-math.atan2(rest.y,-rest.z))
  front=max(-math.radians(22),min(0,min(legangles))*.45);back=min(math.radians(25),max(0,max(legangles))*.60)
  for i,name in enumerate(names):
   theta=-math.pi/2+i*math.pi/3;pitch=front*max(0,-math.sin(theta))+back*max(0,math.sin(theta));p=rig.pose.bones[name];base=p.bone.matrix_local
   spread=math.radians(3)*math.cos(theta)*(abs(front)+abs(back));q=Quaternion((1,0,0),pitch)@Quaternion((0,1,0),spread)
   p.matrix=hipdef@Matrix.Translation(base.translation)@q.to_matrix().to_4x4()@base.to_quaternion().to_matrix().to_4x4();p.rotation_mode='QUATERNION';bpy.context.view_layer.update()
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=frame,group=name)
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
for t in rig.animation_data.nla_tracks:t.mute=True
scene.frame_set(1)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'xiaqing_optimized.blend',compress=True)
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'xiaqing_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_anim_slide_to_zero=True,export_force_sampling=True,export_def_bones=True)
print('FINAL_MODEL_READY',flush=True)
