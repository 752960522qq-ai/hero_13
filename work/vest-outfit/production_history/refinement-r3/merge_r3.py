"""Combine independently reviewed R3 neck, shoulder and rigid-foot patches."""
import bpy,runpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'neck/neck_rebuilt.blend'))
rig=bpy.data.objects['Xiaqing_Native_Rig'];body=bpy.data.objects['Vest_Body'];original_actions=set(bpy.data.actions)
rig.animation_data.action=None;rig.data.pose_position='REST'
for tr in rig.animation_data.nla_tracks:tr.mute=True
for pb in rig.pose.bones:pb.matrix_basis.identity()
data=np.load(P/'shoulders/shoulder_patch.npz');lookup={int(i):j for j,i in enumerate(data['ids'])};names=data['group_names'].tolist();deltas=data['delta'];weights=data['weights']
preserve=body.data.attributes.get('r3_neck_preserve')
changed=set()
for v,rid in zip(body.data.vertices,body.data.attributes['r2_vertex_id'].data):
 i=lookup.get(int(rid.value))
 if i is None or (preserve and preserve.data[v.index].value):continue
 v.co+=__import__('mathutils').Vector(deltas[i]);changed.add(v.index)
 for g in list(v.groups):body.vertex_groups[g.group].remove([v.index])
 for j in np.where(weights[i]>1e-8)[0]:
  group=body.vertex_groups.get(names[j]) or body.vertex_groups.new(name=names[j]);group.add([v.index],float(weights[i,j]),'REPLACE')
# Updated surface normals confined to shoulder-patch vertices.
oldn=[n.vector[:] for n in body.data.corner_normals]
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
body.data.update();newn=[n.vector[:] for n in body.data.corner_normals]
for loop in body.data.loops:
 if loop.vertex_index not in changed:newn[loop.index]=oldn[loop.index]
body.data.normals_split_custom_set(newn)
if not body.data.attributes.get('source_vertex_id'):
 source_ids=body.data.attributes.new('source_vertex_id','INT','POINT')
 source_ids.data.foreach_set('value',np.array([a.value for a in body.data.attributes['r2_vertex_id'].data],dtype=np.int32))
runpy.run_path(str(P/'shoes/apply_patch.py'))
manifest=json.loads((P/'neck/seam_manifest.json').read_text())
idmap={int(v.value):i for i,v in enumerate(body.data.attributes['r2_vertex_id'].data)}
stable=manifest.get('root_body_r2_vertex_id',[j for i,j in manifest['root_pairs']])
manifest['root_pairs']=[[int(pair[0]),idmap[int(rid)]] for pair,rid in zip(manifest['root_pairs'],stable)]
manifest['root_body_r2_vertex_id']=stable
manifest['index_scope']='Final combined R3, after lower-body topology changes'
(P/'seam_manifest.json').write_text(json.dumps(manifest,indent=2))
for a in list(bpy.data.actions):
 if a not in original_actions:bpy.data.actions.remove(a,do_unlink=True)
# The pose fix relaxes both Idle clavicles in the local spine frame.
runpy.run_path(str(P/'shoulders/idle_clavicle_fix.py'))['apply_idle_clavicle_patch'](rig)
for image in bpy.data.images:
 if image.source=='FILE' and not image.packed_file:
  try:image.pack()
  except RuntimeError:pass
body['refinement_r3']='Relaxed shoulder line and Idle clavicle; original rigid high heels; source neck with original head neck removed'
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'vest_xiaqing_r3.blend'),compress=True)
(P/'merge_report.json').write_text(json.dumps({'neck_source':'neck/neck_rebuilt.blend','shoulder_patch_vertices':len(changed),'shoes':['Shoe_L','Shoe_R'],'bone_count':len(rig.data.bones),'actions':[a.name for a in bpy.data.actions],'publication':'local_only_not_deployed'},indent=2))
print('R3 MERGE COMPLETE')
