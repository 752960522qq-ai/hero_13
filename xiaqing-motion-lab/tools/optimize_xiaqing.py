import bpy,bmesh,math,json,os
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/'
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_rigged.blend')
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(1)
parts={int(o.name.split('_')[-1]):o for o in bpy.data.objects if o.type=='MESH'}
report={'before_meshes':len(parts),'before_vertices':sum(len(o.data.vertices) for o in parts.values()),'removed_fragments':[]}
for idx,o in list(parts.items()):
 if idx>=16:
  report['removed_fragments'].append(o.name);bpy.data.objects.remove(o,do_unlink=True);del parts[idx];continue
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bmesh.ops.dissolve_degenerate(bm,dist=.0000001,edges=list(bm.edges));bm.to_mesh(o.data);bm.free()
# Replace corrupted distal right hand with the cleaner opposite hand, maintaining UV loops.
right=parts[4];left=parts[5]
reference=right.data.copy();reference.calc_loop_triangles()
refverts=[v.co.copy() for v in reference.vertices];reftris=list(reference.loop_triangles)
refbvh=BVHTree.FromPolygons(refverts,[t.vertices[:] for t in reftris],all_triangles=True)
def project_uv(co):
 hit,normal,idx,dist=refbvh.find_nearest(co)
 tri=reftris[idx];points=[refverts[i] for i in tri.vertices]
 uvs=[Vector((*reference.uv_layers.active.data[i].uv,0)) for i in tri.loops]
 return barycentric_transform(hit,*points,*uvs).xy
hand=left.copy();hand.data=left.data.copy();bpy.context.collection.objects.link(hand);hand.name='RightPalmRepair'
for v in hand.data.vertices:v.co.x=-v.co.x
for g in hand.vertex_groups:
 if g.name.startswith('Left'):g.name='Right'+g.name[4:]
def cut(obj,z,clear_inner,clear_outer,flip=False):
 bm=bmesh.new();bm.from_mesh(obj.data)
 if flip:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=clear_inner,clear_outer=clear_outer)
 bm.to_mesh(obj.data);bm.free()
cut(right,.545,True,False);cut(hand,.535,False,True,True)
def smooth(a,b,z):
 t=max(0,min(1,(z-a)/(b-a)));return t*t*(3-2*t)
def cross(obj,z):return [v for v in obj.data.vertices if abs(v.co.z-z)<1e-6]
a=cross(right,.545);b=cross(hand,.535)
ca=sum((v.co for v in a),Vector())/len(a);cb=sum((v.co for v in b),Vector())/len(b)
# Ease the graft into the original forearm shape, leaving palm proportions intact.
ra=[max(v.co[k] for v in a)-min(v.co[k] for v in a) for k in [0,1]];rb=[max(v.co[k] for v in b)-min(v.co[k] for v in b) for k in [0,1]]
for v in hand.data.vertices:
 t=smooth(.485,.535,v.co.z)
 for k in [0,1]:v.co[k]=(1-t)*v.co[k]+t*(ca[k]+(v.co[k]-cb[k])*ra[k]/rb[k])
bpy.ops.object.select_all(action='DESELECT');right.select_set(True);hand.select_set(True);bpy.context.view_layer.objects.active=right;bpy.ops.object.join()
bm=bmesh.new();bm.from_mesh(right.data);bm.verts.ensure_lookup_table()
# Bridge the two forearm boundary loops; this produces a continuous manifold graft.
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.545)<1e-6 or abs(v.co.z-.535)<1e-6 for v in e.verts)]
print('GRAFT_BOUNDARY',len(edges),flush=True)
result=bmesh.ops.bridge_loops(bm,edges=edges,use_pairs=True)
uv=bm.loops.layers.uv.active
for face in bm.faces:
 if face in result.get('faces',[]) or all(v.co.z>.515 for v in face.verts):
  if face.material_index!=0 or face in result.get('faces',[]):
   face.material_index=0
   for loop in face.loops:loop[uv].uv=project_uv(loop.vert.co)
band=[v for v in bm.verts if .532<v.co.z<.548]
for _ in range(5):bmesh.ops.smooth_vert(bm,verts=band,factor=.35,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(right.data);bm.free()
report['right_hand_repair']='Mirrored clean left palm; original proximal right arm retained; welded forearm bridge with preserved UVs.'
# Reweight from anatomical part identity instead of x sign (some parts cross the centerline).
def mix(a,b,w):return {a:1-w,b:w}
def torso(z):
 if z<.58:return {'Hips':1}
 if z<.65:return mix('Hips','Spine',smooth(.58,.65,z))
 if z<.71:return mix('Spine','Spine1',smooth(.65,.71,z))
 return mix('Spine1','Spine2',smooth(.71,.78,z))
def skirt(x,z):
 w=torso(z)
 if z>=.57:return w
 f=(1-smooth(.42,.57,z))*.72;side=smooth(-.065,.065,x)
 return {'Hips':1-f,'LeftUpLeg':f*side,'RightUpLeg':f*(1-side)}
for idx,o in parts.items():
 o.vertex_groups.clear();groups={n:o.vertex_groups.new(name=n) for n in rig.data.bones.keys()}
 for v in o.data.vertices:
  x,y,z=v.co
  if idx in [4,5]:
   s='Right' if idx==4 else 'Left'
   if z>.75:w=mix(s+'Arm',s+'Shoulder',smooth(.75,.81,z)*.55)
   elif z>.595:w=mix(s+'ForeArm',s+'Arm',smooth(.595,.67,z))
   else:w=mix(s+'Hand',s+'ForeArm',smooth(.475,.52,z))
  elif idx in [3,6,9,12]:
   s='Right' if idx in [3,9] else 'Left'
   if z>.30:w={s+'UpLeg':1}
   elif z>.245:w=mix(s+'Leg',s+'UpLeg',smooth(.245,.30,z))
   else:w=mix(s+'Foot',s+'Leg',smooth(.09,.145,z))
  elif idx in [8,11,13,14]:
   s='Left' if idx==8 else 'Right';w={s+'Foot':1}
  elif idx in [0,10]:w=skirt(x,z)
  elif idx==1:w=mix('Spine2','Head',smooth(.70,.84,z))
  elif idx==7:
   if z>.815:w={'Head':1}
   elif z>.775:w=mix('Neck','Head',smooth(.775,.815,z))
   else:w=torso(z)
  else:
   w=torso(z)
   if z>.745 and abs(x)>.055:
    s='Left' if x>0 else 'Right';f=smooth(.055,.105,abs(x))*smooth(.745,.79,z)
    w={k:a*(1-f) for k,a in w.items()};w[s+'Arm']=f*.65;w[s+'Shoulder']=f*.35
  for n,a in w.items():
   if a>1e-8:groups[n].add([v.index],a,'REPLACE')
# Logical meshes; weld only coincident seam vertices, never unrelated surfaces.
meshes=[]
for name,indices in [('Body',[3,4,5,6,7,9,12]),('Hair',[1]),('Dress',[0,2,10]),('Shoe_L',[8]),('Shoe_R',[11,13,14])]:
 objs=[parts[i] for i in indices];bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=objs[0];o.name='XiaQing_'+name;o.data.name=o.name+'_Mesh';meshes.append(o)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bmesh.ops.dissolve_degenerate(bm,dist=.0000001,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 for p in o.data.polygons:p.use_smooth=True
 o['part']=name;o['character']='夏晴';o['revision']='2.0'
 # Remove unused materials safely after grouping.
 bpy.ops.object.material_slot_remove_unused()
rig.name='XiaQing_Rig';rig.data.name='XiaQing_Skeleton';rig['character']='夏晴';rig['version']='2.0'
# Keep only the character in a clearly labeled collection.
col=bpy.data.collections.new('夏晴 / Character');bpy.context.scene.collection.children.link(col)
for o in [rig]+meshes:
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o)
for c in list(bpy.data.collections):
 if c!=col and not c.objects and not c.children:bpy.data.collections.remove(c)
# Dedicated right wrist check; no claim of individual finger articulation.
scene=bpy.context.scene;action=bpy.data.actions.new('HandTest');rig.animation_data.action=action
for f in range(1,92):
 scene.frame_set(f)
 for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4);p.rotation_mode='QUATERNION'
 phase=(f-1)/90*2*math.pi
 rig.pose.bones['RightArm'].rotation_quaternion=Quaternion(Vector((1,0,0)),math.radians(-22))
 rig.pose.bones['RightForeArm'].rotation_quaternion=Quaternion(Vector((1,0,0)),math.radians(-35))
 rig.pose.bones['RightHand'].rotation_quaternion=Quaternion(Vector((1,0,0)),math.radians(18)*math.sin(phase))@Quaternion(Vector((0,1,0)),math.radians(22)*math.sin(phase))
 for p in rig.pose.bones:
  for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
rig.animation_data.action=None;t=rig.animation_data.nla_tracks.new();t.name='HandTest';t.strips.new('HandTest',1,action);t.mute=True
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);scene.frame_end=91
report['after_meshes']=len(meshes);report['after_vertices']=sum(len(o.data.vertices) for o in meshes)
report['parts']=[{'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':len(o.data.materials)} for o in meshes]
report['bones']=len(rig.data.bones);report['animations']=[t.name for t in rig.animation_data.nla_tracks]
# Validate all exported skin weights.
for o in meshes:
 for v in o.data.vertices:
  weights=[g.weight for g in v.groups if g.weight>0]
  assert weights and len(weights)<=4 and abs(sum(weights)-1)<1e-5,(o.name,v.index,weights)
  assert all(math.isfinite(a) for a in v.co)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'xiaqing_optimized.blend',compress=True)
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT')
for o in [rig]+meshes:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'xiaqing_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_anim_slide_to_zero=True,export_force_sampling=True,export_def_bones=True)
with open(OUT+'optimization-report.json','w') as f:json.dump(report,f,indent=2,ensure_ascii=False)
print('OPTIMIZATION_COMPLETE',json.dumps(report,ensure_ascii=False),flush=True)
