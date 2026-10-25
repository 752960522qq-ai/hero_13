import bpy,bmesh,math,json
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/'
bpy.ops.wm.open_mainfile(filepath='/tmp/xiaqing_v2_input.blend')
rig=bpy.data.objects['XiaQing_Rig'];scene=bpy.context.scene
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
reference=bpy.data.objects['XiaQing_Body'].data.copy();reference.calc_loop_triangles()
refvs=[v.co.copy() for v in reference.vertices];reftris=list(reference.loop_triangles);refweights=[{g.group:g.weight for g in v.groups} for v in reference.vertices];refnames=[g.name for g in bpy.data.objects['XiaQing_Body'].vertex_groups]
refbvh=BVHTree.FromPolygons(refvs,[t.vertices[:] for t in reftris],all_triangles=True)
# Preserve face/neck and foot surface detail; close these thin layers separately.
body_source=bpy.data.objects['XiaQing_Body'];detail=body_source.copy();detail.data=body_source.data.copy();detail.name='PreservedFaceFeet';bpy.context.collection.objects.link(detail)
keep_mats={i for i,m in enumerate(body_source.data.materials) if m.name in ['tripo_part_7_material','tripo_part_9_material','tripo_part_12_material']}
for obj,keep in [(detail,True),(body_source,False)]:
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if (f.material_index in keep_mats)!=keep],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(obj.data);bm.free()
report={'version':3,'topology':{},'method':'Closed inner shells; reconstructed underlying torso and upper legs; independent skirt panel bones.'}
skin=bpy.data.materials.new('XiaQing_ReconstructedSkin');skin.diffuse_color=(.52,.38,.30,1);skin.use_nodes=True
bs=skin.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.52,.38,.30,1);bs.inputs['Roughness'].default_value=.68
# Close the visual parts as independent shells. Solidify preserves all outward faces/UVs.
for o in list(bpy.data.objects):
 if o.type!='MESH':continue
 bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
 bm=bmesh.new();bm.from_mesh(o.data)
 report['topology'][o.name]={'before_boundary':sum(e.is_boundary for e in bm.edges),'before_nonmanifold':sum(not e.is_manifold for e in bm.edges)}
 # Repair small accidental punctures, while keeping the wrap opening and neckline.
 boundaries=set(e for e in bm.edges if e.is_boundary)
 while boundaries:
  todo=[boundaries.pop()];edges=[]
  while todo:
   e=todo.pop();edges.append(e)
   for v in e.verts:
    for other in v.link_edges:
     if other in boundaries:boundaries.remove(other);todo.append(other)
  perimeter=sum(e.calc_length() for e in edges)
  if perimeter<.09 or 'Body' in o.name:
   result=bmesh.ops.holes_fill(bm,edges=edges,sides=0)
   for f in result.get('faces',[]):
    f.smooth=True
    if 'Body' in o.name:
     if skin.name not in o.data.materials:o.data.materials.append(skin)
     f.material_index=len(o.data.materials)-1
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 if 'Body' not in o.name:
  solid=o.modifiers.new('ClosedInnerSurface','SOLIDIFY');solid.thickness=.0010 if 'Hair' in o.name or o==detail else .0015;solid.offset=-1;solid.use_rim=True;solid.use_even_offset=False;solid.solidify_mode='NON_MANIFOLD';solid.nonmanifold_thickness_mode='FIXED';solid.nonmanifold_boundary_mode='FLAT';solid.thickness_clamp=.5
  bpy.ops.object.modifier_move_up(modifier=solid.name)
  bpy.ops.object.modifier_apply(modifier=solid.name)
 bm=bmesh.new();bm.from_mesh(o.data)
 # Fill any residual short open chains from degenerate source triangles.
 bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data)
 report['topology'][o.name].update({'after_boundary':sum(e.is_boundary for e in bm.edges),'after_nonmanifold':sum(not e.is_manifold for e in bm.edges),'vertices':len(bm.verts)})
 bm.free();o['revision']='3.0'
 print('CLOSED_PART',o.name,report['topology'][o.name],flush=True)
# Closed under-body, with sufficient hidden overlap at original fragmented shoulders/thighs.
verts=[];faces=[];tags=[]
def ring_volume(rings,tag,n=40):
 start=len(verts)
 for z,cx,cy,rx,ry in rings:
  for j in range(n):
   a=2*math.pi*j/n;verts.append((cx+rx*math.cos(a),cy+ry*math.sin(a),z));tags.append(tag)
 for r in range(len(rings)-1):
  for j in range(n):
   a=start+r*n+j;b=start+r*n+(j+1)%n;c=start+(r+1)*n+(j+1)%n;d=start+(r+1)*n+j;faces.append((a,b,c,d))
 faces.append(tuple(start+j for j in reversed(range(n))))
 faces.append(tuple(start+(len(rings)-1)*n+j for j in range(n)))
# Torso shape stays inside the original dress; smooth shoulder and neck cover.
ring_volume([(.48,0,.004,.061,.043),(.52,0,.004,.069,.050),(.56,0,.002,.071,.052),(.61,0,-.003,.061,.051),(.66,0,-.008,.061,.052),(.70,0,-.011,.071,.061),(.735,0,-.008,.080,.055),(.765,0,.001,.084,.045),(.787,0,.002,.066,.033),(.80,0,-.001,.034,.027),(.818,0,-.003,.027,.026),(.84,0,-.004,.024,.025)],'torso')
for side,x in [('Right',-.043),('Left',.043)]:
 ring_volume([(.405,x,-.015,.031,.033),(.44,x,-.008,.035,.040),(.48,x,.002,.037,.045),(.52,x,.005,.038,.045),(.55,x*.8,.005,.036,.043)],side+'UpLeg')
 # A closed shoulder/upper-arm core follows blended joint weights, bridging gaps beneath sleeves.
 s=-1 if side=='Right' else 1
 ring_volume([(.665,s*.122,-.004,.020,.024),(.71,s*.116,.003,.024,.026),(.755,s*.102,.006,.030,.030),(.785,s*.091,.006,.031,.030),(.80,s*.082,.006,.025,.027)],side+'ShoulderFill')
mesh=bpy.data.meshes.new('UnderlyingBodyMesh');mesh.from_pydata(verts,[],faces);mesh.update();fill=bpy.data.objects.new('UnderlyingBody',mesh);bpy.context.collection.objects.link(fill);fill.data.materials.append(skin)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
for p in mesh.polygons:p.use_smooth=True
# Dedicated skirt bones: smooth panel influence, never the two opposing thigh bones.
panel_names=['SkirtFront','SkirtFrontLeft','SkirtBackLeft','SkirtBack','SkirtBackRight','SkirtFrontRight']
angles=[-math.pi/2+i*math.pi/3 for i in range(6)]
bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name in panel_names:
 b=rig.data.edit_bones.new(name);b.head=(0,.005,.59);b.tail=(0,.005,.39);b.parent=rig.data.edit_bones['Hips']
bpy.ops.object.mode_set(mode='OBJECT')
def smooth(a,b,z):
 t=max(0,min(1,(z-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,t):return {a:1-t,b:t}
def torso(z):
 if z<.58:return {'Hips':1}
 if z<.65:return mix('Hips','Spine',smooth(.58,.65,z))
 if z<.71:return mix('Spine','Spine1',smooth(.65,.71,z))
 return mix('Spine1','Spine2',smooth(.71,.78,z))
def assign(o,weights):
 o.vertex_groups.clear();gs={n:o.vertex_groups.new(name=n) for n in rig.data.bones.keys()}
 for v in o.data.vertices:
  w=weights(v);total=sum(w.values())
  for name,value in w.items():
   if value>1e-7:gs[name].add([v.index],value/total,'REPLACE')
def fillweights(v):
 x,y,z=v.co;tag=tags[v.index]
 if tag=='torso':
  if z>.795:return mix('Spine2','Neck',smooth(.795,.83,z))
  return torso(z)
 if 'ShoulderFill' in tag:
  side=tag.replace('ShoulderFill','');arm=1-smooth(.71,.80,z)
  return {side+'Arm':.75*arm,side+'Shoulder':.25*arm+(1-arm)*.6,'Spine2':(1-arm)*.4}
 t=1-smooth(.48,.55,z);return {'Hips':1-t,tag:t}
# Voxel union only the hidden support and limb skin. Face/feet retain original topology.
body=bpy.data.objects['XiaQing_Body'];bpy.ops.object.select_all(action='DESELECT');body.select_set(True);fill.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
# Remove armature evaluation during the geometry operation; rebind after UV projection.
for mod in list(body.modifiers):body.modifiers.remove(mod)
body.data.remesh_voxel_size=.0010;body.data.remesh_voxel_adaptivity=.05;bpy.ops.object.voxel_remesh()
sm=body.modifiers.new('SmoothUnderlyingBody','SMOOTH');sm.factor=.45;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
dec=body.modifiers.new('PreserveSurfaceDensity','DECIMATE');dec.ratio=.30;dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
for layer in list(body.data.uv_layers):body.data.uv_layers.remove(layer)
uv=body.data.uv_layers.new(name='UVMap');uv.active_render=True
allowed={i for i,m in enumerate(body.data.materials) if m.name in ['tripo_part_3_material','tripo_part_4_material','tripo_part_5_material','tripo_part_6_material']}
skinindex=next(i for i,m in enumerate(body.data.materials) if m==skin)
# Reproject texture charts onto the repaired limb surfaces, with a uniform hidden inner skin.
matbvh={};matrefs={}
for mat in allowed:
 tris=[t for t in reftris if t.material_index==mat];matrefs[mat]=tris;matbvh[mat]=BVHTree.FromPolygons(refvs,[t.vertices[:] for t in tris],all_triangles=True)
for face in body.data.polygons:
 hit,normal,idx,dist=refbvh.find_nearest(face.center);tri=reftris[idx];mat=tri.material_index
 if mat not in allowed or dist>.006:face.material_index=skinindex;continue
 face.material_index=mat
 for li in face.loop_indices:
  co=body.data.vertices[body.data.loops[li].vertex_index].co;hit,no,i,d=matbvh[mat].find_nearest(co);t=matrefs[mat][i];points=[refvs[v] for v in t.vertices];uvs=[Vector((*reference.uv_layers.active.data[k].uv,0)) for k in t.loops]
  uv.data[li].uv=barycentric_transform(hit,*points,*uvs).xy
for f in body.data.polygons:f.use_smooth=True
mod=body.modifiers.new('XiaQingSkin','ARMATURE');mod.object=rig;body.parent=rig
print('CONTINUOUS_SKIN',len(body.data.vertices),len(body.data.polygons),flush=True)
def bodyweights(v):
 x,y,z=v.co
 if z>.815:procedural={'Head':1}
 elif z>.79:procedural=mix('Neck','Head',smooth(.79,.84,z))
 elif abs(x)>.072 and z>.65:
  side='Left' if x>0 else 'Right';a=smooth(.065,.115,abs(x))
  procedural={'Spine2':1-a,side+'Arm':a*.8,side+'Shoulder':a*.2}
 elif z<.55:
  side='Left' if x>0 else 'Right';a=1-smooth(.47,.55,z);procedural={'Hips':1-a,side+'UpLeg':a}
 else:procedural=torso(z)
 hit,normal,idx,dist=refbvh.find_nearest(v.co)
 if dist>.018:return procedural
 tri=reftris[idx];points=[refvs[i] for i in tri.vertices]
 bary=barycentric_transform(hit,*points,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));weights={}
 for vertex,w in zip(tri.vertices,bary):
  for group,weight in refweights[vertex].items():
   name=refnames[group];weights[name]=weights.get(name,0)+weight*max(0,w)
 t=smooth(.003,.018,dist);weights={n:a*(1-t) for n,a in weights.items()}
 for n,a in procedural.items():weights[n]=weights.get(n,0)+a*t
 largest=sorted(weights.items(),key=lambda a:a[1],reverse=True)[:4]
 return dict(largest)
assign(body,bodyweights)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);detail.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
report['topology'].pop('PreservedFaceFeet',None)
# Use shared position weights on both shell faces to prevent differential tearing.
dress=bpy.data.objects['XiaQing_Dress']
def clothweights(v):
 x,y,z=v.co
 if z>.61:return torso(z)
 f=1-smooth(.51,.61,z)
 a=(math.atan2(y-.005,x)+math.pi/2)%(2*math.pi);t=a/(math.pi/3);i=int(t)%6;u=t-int(t)
 u=u*u*(3-2*u)
 return {'Hips':1-f,panel_names[i]:f*(1-u),panel_names[(i+1)%6]:f*u}
assign(dress,clothweights)
# Bake an arm raise animation to explicitly exercise shoulder and underarm coverage.
action=bpy.data.actions.new('ArmRaise');rig.animation_data.action=action
for f in range(1,122):
 scene.frame_set(f);t=(f-1)/120;lift=math.sin(math.pi*t)**2
 for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4);p.rotation_mode='QUATERNION'
 for side,sgn in [('Right',1),('Left',-1)]:
  for suffix,factor in [('Shoulder',10),('Arm',145),('ForeArm',145),('Hand',145)]:
   p=rig.pose.bones[side+suffix];head=p.parent.matrix@p.parent.bone.matrix_local.inverted()@p.bone.head_local
   q=Quaternion((0,1,0),sgn*math.radians(factor)*lift)
   p.matrix=Matrix.Translation(head)@q.to_matrix().to_4x4()@p.bone.matrix_local.to_quaternion().to_matrix().to_4x4();bpy.context.view_layer.update()
 for p in rig.pose.bones:
  if p.name not in panel_names:
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=p.name)
rig.animation_data.action=None;track=rig.animation_data.nla_tracks.new();track.name='ArmRaise';track.strips.new('ArmRaise',1,action);track.mute=True
# Panel rotations follow gait envelope in pelvis coordinates. The front follows the leading
# thigh and back follows the trailing thigh; opposite legs never pull one skirt patch apart.
for action in list(bpy.data.actions):
 rig.animation_data.action=action;start,end=map(int,action.frame_range)
 for f in range(start,end+1):
  scene.frame_set(f);bpy.context.view_layer.update();hip=rig.pose.bones['Hips'];hipdef=hip.matrix@hip.bone.matrix_local.inverted();angles_legs=[]
  for side in ['Left','Right']:
   p=rig.pose.bones[side+'UpLeg'];v=hipdef.to_quaternion().inverted()@(p.tail-p.head);rest=p.bone.tail_local-p.bone.head_local
   angles_legs.append(math.atan2(v.y,-v.z)-math.atan2(rest.y,-rest.z))
  front=max(-math.radians(43),min(0,min(angles_legs))*.82);back=min(math.radians(45),max(0,max(angles_legs))*.98)
  for i,name in enumerate(panel_names):
   theta=angles[i];frontness=max(0,-math.sin(theta));backness=max(0,math.sin(theta));pitch=front*frontness+back*backness
   p=rig.pose.bones[name];base=p.bone.matrix_local
   # Small outward opening gives thighs clearance without stretching the panel roots.
   spread=math.radians(3.0)*math.cos(theta)*(abs(front)+abs(back))
   rot=Quaternion((1,0,0),pitch)@Quaternion((0,1,0),spread)
   p.matrix=hipdef@Matrix.Translation(base.translation)@rot.to_matrix().to_4x4()@base.to_quaternion().to_matrix().to_4x4();p.rotation_mode='QUATERNION';bpy.context.view_layer.update()
   for prop in ['location','rotation_quaternion','scale']:p.keyframe_insert(prop,frame=f,group=name)
 rig.animation_data.action=None
# Normalize all inherited groups after topology additions; inner faces must retain valid skinning.
for o in [o for o in bpy.data.objects if o.type=='MESH']:
 for v in o.data.vertices:
  good=[(g.group,g.weight) for g in v.groups if g.weight>1e-7]
  if not good:o.vertex_groups['Hips'].add([v.index],1,'REPLACE');continue
  top=sorted(good,key=lambda g:g[1],reverse=True)[:4];total=sum(g[1] for g in top);keep={g[0] for g in top}
  for g in list(v.groups):
   if g.group not in keep:o.vertex_groups[g.group].remove([v.index])
  for group,weight in top:o.vertex_groups[group].add([v.index],weight/total,'REPLACE')
 rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);scene.frame_end=121;rig['version']='3.0'
for o in [o for o in bpy.data.objects if o.type=='MESH']:
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);b=sum(e.is_boundary for e in bm.edges);nm=sum(not e.is_manifold for e in bm.edges)
 report['topology'][o.name].update({'final_boundary':b,'final_nonmanifold':nm,'vertices':len(bm.verts)})
 print('FINAL_TOPOLOGY',o.name,b,nm,flush=True);bm.free()
report['bones']=len(rig.data.bones);report['animations']=[a.name for a in bpy.data.actions]
bpy.ops.wm.save_as_mainfile(filepath=OUT+'xiaqing_optimized.blend',compress=True)
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'xiaqing_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_anim_slide_to_zero=True,export_force_sampling=True,export_def_bones=True)
with open(OUT+'closure-report.json','w') as f:json.dump(report,f,indent=2)
print('SEAL_COMPLETE',json.dumps(report),flush=True)
