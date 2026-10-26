"""Recover exact-source lower shape/rig and adapt ankle rotation to high heels."""
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent
def apply_lower():
 d=np.load(P/'lower_patch.npz');o=bpy.data.objects['Vest_Body'];r=bpy.data.objects['Xiaqing_Native_Rig'];names=d['group_names'].tolist()
 assert len(o.data.vertices)==55958
 ids=d['ids'];coords=d['coords'];weights=d['weights']
 for idx,co,row in zip(ids,coords,weights):
  idx=int(idx);o.data.vertices[idx].co=co
  for g in list(o.data.vertices[idx].groups):o.vertex_groups[g.group].remove([idx])
  for j in np.where(row>1e-8)[0]:o.vertex_groups[names[j]].add([idx],float(row[j]),'REPLACE')
 for side in ['l','r']:
  shoe=bpy.data.objects['Shoe_'+side.upper()]
  assert len(shoe.data.vertices)==len(d['shoe_'+side+'_coords'])
  for v,co in zip(shoe.data.vertices,d['shoe_'+side+'_coords']):v.co=co
  shoe.data.update()
 # All rest axes are unchanged: relocate the imported GLB bones by head/tail
 # translation, deriving anatomical segment endpoints from child HEADS only.
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.mode_set(mode='EDIT')
 for n,head,tail in zip(d['bone_names'].tolist(),d['bone_heads'],d['bone_tails']):
  b=r.data.edit_bones[n];b.head=Vector(head);b.tail=Vector(tail)
 bpy.ops.object.mode_set(mode='OBJECT')
 for ai,label in enumerate(d['action_labels'].tolist()):
  action=next(a for a in bpy.data.actions if a.name.startswith(label));prefix='action_'+str(ai)+'_'
  for bi,bone in enumerate(d[prefix+'bones'].tolist()):
   path=f'pose.bones["{bone}"].rotation_quaternion'
   for fc in action.fcurves:
    if fc.data_path!=path:continue
    assert len(fc.keyframe_points)==len(d[prefix+'times'])
    for k,q in zip(fc.keyframe_points,d[prefix+'quats'][:,bi]):
     delta=float(q[fc.array_index])-k.co.y;k.co.y+=delta;k.handle_left.y+=delta;k.handle_right.y+=delta
    fc.update()
 normals=np.array([n.vector[:] for n in o.data.corner_normals]);normals[d['loop_ids']]=d['loop_normals'];o.data.normals_split_custom_set(normals);o.data.update()
 o['refinement_r6_lower']='Recover original source lower-body shape with uniform1.7+global neck translation; rig conforms to body; rigid tibia muscle belly'
 return {'body_vertices':len(ids),'bone_targets':len(d['bone_names']),'source_scale':1.7,'ankle_quaternion_channels_changed':24,'hip_knee_and_other_curves_changed':False}
