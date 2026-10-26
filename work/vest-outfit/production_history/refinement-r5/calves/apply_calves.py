"""Call apply_calves() in the R4-based final scene, before saving."""
from pathlib import Path
import bpy,numpy as np
P=Path(__file__).resolve().parent
def apply_calves(body=None):
 body=body or bpy.data.objects['Vest_Body'];data=np.load(P/'calf_weights.npz');ids=data['ids'];weights=data['weights'];names=data['group_names'].tolist()
 assert len(body.data.vertices)==55958,'Unexpected body topology'
 for idx,row in zip(ids,weights):
  idx=int(idx)
  for g in list(body.data.vertices[idx].groups):body.vertex_groups[g.group].remove([idx])
  for j in np.where(row>1e-8)[0]:body.vertex_groups[names[j]].add([idx],float(row[j]),'REPLACE')
 rig=bpy.data.objects['Xiaqing_Native_Rig'];bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
 from mathutils import Vector
 for n,head,tail in zip(data['bone_names'].tolist(),data['bone_heads'],data['bone_tails']):
  bone=rig.data.edit_bones[n];bone.head=Vector(head);bone.tail=Vector(tail)
 bpy.ops.object.mode_set(mode='OBJECT')
 body.data.update();body['refinement_r5_calf']='Stable tibia binding; anatomical ankle pivot; localized ankle transition, original rest geometry retained'
 return {'modified_weight_vertices':len(ids),'rest_geometry_changed':False,'bone_translations':{n:d.tolist() for n,d in zip(data['bone_names'].tolist(),data['bone_deltas'])}}
