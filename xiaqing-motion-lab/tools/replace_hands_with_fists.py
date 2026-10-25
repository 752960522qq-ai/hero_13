import bpy,bmesh,math,json,zipfile
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'dist/assets';BASE='/tmp/xiaqing_v48.blend';SRC='/workspace/scratch/7b171b7361b3/upload/xiaqing_trenchcoat.glb'
bpy.ops.wm.open_mainfile(filepath=BASE);rig=bpy.data.objects['夏晴_牛仔裤'];body=bpy.data.objects['XiaQing_Jeans_Surface'];scene=bpy.context.scene
# Skin material is shared by fist surfaces and the small wrist caps.
skin=bpy.data.materials.get('夏晴_自然肤色_拳头') or bpy.data.materials.new('夏晴_自然肤色_拳头');skin.diffuse_color=(0.58,0.36,0.29,1);skin.use_nodes=True;bs=next(n for n in skin.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(0.58,0.36,0.29,1);bs.inputs['Roughness'].default_value=.72
cap_index=len(body.data.materials);body.data.materials.append(skin)
# Remove only the old left/right hand islands; close each wrist end before fitting fists.
bm=bmesh.new();bm.from_mesh(body.data);materials=body.data.materials
handids=set()
for i,m in enumerate(materials):
 if m and any(k in m.name for k in ['tripo_part_9_material','tripo_part_10_material']):handids.add(i)
assert handids,[(i,m.name if m else '') for i,m in enumerate(materials)]
oldfaces=[f for f in bm.faces if f.material_index in handids]
assert oldfaces
bmesh.ops.delete(bm,geom=oldfaces,context='FACES')
bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_edges],context='VERTS')
boundary=[e for e in bm.edges if e.is_boundary]
filled=bmesh.ops.holes_fill(bm,edges=boundary,sides=0).get('faces',[])
for face in filled:face.material_index=cap_index
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
# Import source fists and retain their original skin material and UVs.
bpy.ops.import_scene.gltf(filepath=SRC)
sources={9:('Left',1),17:('Right',-1)};created=[];transforms=[]
for idx,(side,sign) in sources.items():
 src=next((o for o in scene.objects if o.type=='MESH' and o.name==f'tripo_part_{idx}'),None);assert src,idx
 world=src.matrix_world.copy()
 # Remove the short dark trenchcoat cuff at the fist root; the clipped edge
 # is capped and will overlap the character's forearm.
 sw=Vector((sign*.330,.018,.758));hand=rig.data.bones[side+'Hand'];start=hand.head_local.copy();end=hand.tail_local.copy();axis=(end-start).normalized();normal=Vector((0,0,1));lateral=normal.cross(axis).normalized()
 bm=bmesh.new();bm.from_mesh(src.data);drop=[]
 for face in bm.faces:
  center=world@face.calc_center_median()
  if (center-sw).dot(Vector((sign,0,0)))<.012:drop.append(face)
 bmesh.ops.delete(bm,geom=drop,context='FACES')
 bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_edges],context='VERTS')
 rim=[e for e in bm.edges if e.is_boundary];bmesh.ops.holes_fill(bm,edges=rim,sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(src.data);bm.free()
 pts=[world@v.co for v in src.data.vertices]
 srcAxis=Vector((sign,0,0));srcLat=Vector((0,sign,0));srcNorm=Vector((0,0,1));scale=1.0
 def fit(p):
  d=(p-sw)*scale
  return start+axis*d.dot(srcAxis)+lateral*d.dot(srcLat)+normal*d.dot(srcNorm)
 verts=[fit(p) for p in pts];faces=[tuple(p.vertices) for p in src.data.polygons]
 mesh=bpy.data.meshes.new(side+'_Fist_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
 # Preserve source UV map and material assignments.
 uvsrc=src.data.uv_layers.active;uv=mesh.uv_layers.new(name=uvsrc.name if uvsrc else 'UVMap')
 if uvsrc:
  for polyS,polyD in zip(src.data.polygons,mesh.polygons):
   for ls,ld in zip(polyS.loop_indices,polyD.loop_indices):uv.data[ld].uv=uvsrc.data[ls].uv
 mesh.materials.append(skin)
 ob=bpy.data.objects.new(side+'_拳头',mesh);scene.collection.objects.link(ob);ob.parent=rig;ob.matrix_world=Matrix.Identity(4)
 vg=ob.vertex_groups.new(name=side+'Hand');vg.add(list(range(len(verts))),1,'REPLACE')
 mod=ob.modifiers.new('Fist_Skin','ARMATURE');mod.object=rig
 ob['character']='夏晴_牛仔裤';ob['source']='xiaqing_trenchcoat.glb';created.append(ob);transforms.append({'side':side,'bone':side+'Hand','source_vertices':len(verts),'removed_old_faces':sum(1 for p in oldfaces)})
 bpy.data.objects.remove(src,do_unlink=True)
# Remove imports unrelated to the fists.
for o in list(scene.objects):
 if o.type=='MESH' and o.name.startswith('tripo_part_'):bpy.data.objects.remove(o,do_unlink=True)
# Focused bind checks: both fist objects follow their corresponding hand bones and stay finite.
checks=[]
for clip,frame in [('Idle',1),('Walk',18),('HandTest',23)]:
 for t in rig.animation_data.nla_tracks:t.mute=True
 action=bpy.data.actions[clip];rig.animation_data.action=action;scene.frame_set(frame);bpy.context.view_layer.update()
 for ob in created:
  ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());assert all(math.isfinite(c) for v in ev.data.vertices for c in v.co)
 checks.append({'clip':clip,'frame':frame,'fists_finite':True})
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis.identity()
scene.frame_set(1);rig['version']='4.9'
bpy.ops.wm.save_as_mainfile(filepath='/tmp/xiaqing_jeans_rigged.blend',compress=True)
with zipfile.ZipFile(OUT/'xiaqing_trousers.blend.zip','w',zipfile.ZIP_DEFLATED) as z:z.write('/tmp/xiaqing_jeans_rigged.blend','xiaqing_trousers.blend')
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True)
for ob in created:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'xiaqing_trousers_rigged.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_anim_slide_to_zero=True,export_def_bones=True)
(OUT/'fist-replacement-report.json').write_text(json.dumps({'fists':transforms,'wrist_cap_faces':len(filled),'pose_checks':checks},indent=2))
print('FIST_REPLACE',transforms,'caps',len(filled),'checks',checks,flush=True)
