import bpy,bmesh,json
from mathutils import Matrix
OUT='/workspace/sites/xiaqing-motion-lab/dist/assets/'
bpy.ops.wm.open_mainfile(filepath=OUT+'xiaqing_optimized.blend')
rig=bpy.data.objects['XiaQing_Rig'];dress=bpy.data.objects['XiaQing_Dress'];body=bpy.data.objects['XiaQing_Body']
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(1)
idx=next(i for i,m in enumerate(dress.data.materials) if m.name=='tripo_part_10_material')
patch=dress.copy();patch.data=dress.data.copy();patch.name='CorrectedRightLegSurface';bpy.context.collection.objects.link(patch)
for obj,keep in [(patch,True),(dress,False)]:
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if (f.material_index==idx)!=keep],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
patch.vertex_groups.clear();g=patch.vertex_groups.new(name='RightUpLeg');g.add(list(range(len(patch.data.vertices))),1,'REPLACE')
# Use one coherent skin tone on reconstructed joint surfaces. Keep original detailed
# face, feet and hands, rather than projecting across unrelated texture islands.
skin=bpy.data.materials['XiaQing_ReconstructedSkin'];skinindex=next(i for i,m in enumerate(body.data.materials) if m==skin)
for f in body.data.polygons:
 name=body.data.materials[f.material_index].name
 if name in ['tripo_part_3_material','tripo_part_6_material']:f.material_index=skinindex
 elif name in ['tripo_part_4_material','tripo_part_5_material'] and all(body.data.vertices[v].co.z>.505 for v in f.vertices):f.material_index=skinindex
patch.data.materials.clear();patch.data.materials.append(skin)
for f in patch.data.polygons:f.material_index=0;f.use_smooth=True
bpy.ops.object.select_all(action='DESELECT');patch.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
for o in [body,dress]:
 bm=bmesh.new();bm.from_mesh(o.data);b=sum(e.is_boundary for e in bm.edges);nm=sum(not e.is_manifold for e in bm.edges);print('PARTITION_CLOSURE',o.name,b,nm,flush=True);assert b==0 and nm==0;bm.free()
report=json.load(open(OUT+'closure-report.json'));report['corrected_partition']='tripo_part_10 moved from Dress to Body and bound to RightUpLeg';report['reconstructed_skin']='Unified reconstructed limb surfaces; original face, feet and hand textures retained.'
with open(OUT+'closure-report.json','w') as f:json.dump(report,f,indent=2)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'xiaqing_optimized.blend',compress=True)
for t in rig.animation_data.nla_tracks:t.mute=False
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for o in bpy.data.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT+'xiaqing_rigged.glb',export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_anim_slide_to_zero=True,export_force_sampling=True,export_def_bones=True)
