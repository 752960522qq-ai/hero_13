"""Export readable rig, full sparse skin weights and all action keys. No model writes.
Run: blender -b -t 4 --python extract_editable_data.py
The .blend remains authoritative for materials and packed textures.
"""
import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;OUT=P/'editable_data';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'vest_xiaqing_r7.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and not o.get('comparison_only'))
rig.animation_data.action=None;rig.data.pose_position='REST'
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
def matrix(m):return [list(row) for row in m]
bones=[]
for bone in rig.data.bones:
 bones.append({'name':bone.name,'parent':bone.parent.name if bone.parent else None,'head':list(bone.head_local),'tail':list(bone.tail_local),'matrix_local':matrix(bone.matrix_local),'use_deform':bone.use_deform,'inherit_scale':bone.inherit_scale,'use_connect':bone.use_connect})
(OUT/'rig_rest.json').write_text(json.dumps({'format':1,'coordinates':'Blender +X character-left, -Y forward, +Z up, meters','name':rig.name,'matrix_world':matrix(rig.matrix_world),'bones':bones},ensure_ascii=False,indent=2)+'\n')
arrays={};meshes=[]
for mi,obj in enumerate(o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render and not o.get('comparison_only')):
 mesh=obj.data;prefix=f'm{mi}_';pos=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',pos);arrays[prefix+'positions']=pos.reshape(-1,3)
 arrays[prefix+'loop_vertex_ids']=np.array([l.vertex_index for l in mesh.loops],np.int32)
 arrays[prefix+'polygon_loop_starts']=np.array([f.loop_start for f in mesh.polygons],np.int32)
 arrays[prefix+'polygon_loop_counts']=np.array([f.loop_total for f in mesh.polygons],np.int32)
 arrays[prefix+'polygon_material_ids']=np.array([f.material_index for f in mesh.polygons],np.int32)
 arrays[prefix+'corner_normals']=np.array([n.vector[:] for n in mesh.corner_normals],np.float32)
 offsets=[0];group_ids=[];weights=[]
 for vertex in mesh.vertices:
  for g in vertex.groups:group_ids.append(g.group);weights.append(g.weight)
  offsets.append(len(weights))
 arrays[prefix+'skin_offsets']=np.array(offsets,np.int32);arrays[prefix+'skin_group_ids']=np.array(group_ids,np.int32);arrays[prefix+'skin_weights']=np.array(weights,np.float32)
 uv=[]
 for ui,layer in enumerate(mesh.uv_layers):
  arrays[prefix+f'uv{ui}']=np.array([d.uv[:] for d in layer.data],np.float32);uv.append(layer.name)
 for attr in mesh.attributes:
  if attr.domain=='POINT' and attr.data_type=='INT':arrays[prefix+'attr_'+attr.name]=np.array([v.value for v in attr.data],np.int32)
 meshes.append({'name':obj.name,'prefix':prefix,'matrix_world':matrix(obj.matrix_world),'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'groups':[g.name for g in obj.vertex_groups],'uv_layers':uv,'materials':[m.name if m else None for m in mesh.materials],'armature_modifier':any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers)})
np.savez_compressed(OUT/'mesh_skin_data.npz',**arrays)
(OUT/'mesh_manifest.json').write_text(json.dumps({'format':1,'array_file':'mesh_skin_data.npz','skin_encoding':'CSR offsets per vertex; every original influence retained','meshes':meshes},ensure_ascii=False,indent=2)+'\n')
anim_arrays={};actions=[];interpolation={'CONSTANT':0,'LINEAR':1,'BEZIER':2}
for ai,action in enumerate(bpy.data.actions):
 if action.name.split('_')[0] not in ['Idle','Walk','Run']:continue
 channels=[]
 for ci,curve in enumerate(action.fcurves):
  prefix=f'a{ai}_c{ci}_';anim_arrays[prefix+'keys']=np.array([[*k.co,*k.handle_left,*k.handle_right] for k in curve.keyframe_points],np.float32)
  anim_arrays[prefix+'interpolation']=np.array([interpolation.get(k.interpolation,3) for k in curve.keyframe_points],np.uint8)
  channels.append({'prefix':prefix,'data_path':curve.data_path,'array_index':curve.array_index,'extrapolation':curve.extrapolation})
 actions.append({'name':action.name,'frame_range':list(action.frame_range),'channels':channels})
np.savez_compressed(OUT/'animation_keys.npz',**anim_arrays)
(OUT/'animation_manifest.json').write_text(json.dumps({'format':1,'fps':bpy.context.scene.render.fps,'fps_base':bpy.context.scene.render.fps_base,'keys_columns':['frame','value','left_handle_frame','left_handle_value','right_handle_frame','right_handle_value'],'interpolation_codes':interpolation,'array_file':'animation_keys.npz','actions':actions},ensure_ascii=False,indent=2)+'\n')
print('EDITABLE_DATA_EXPORTED',json.dumps({'bones':len(bones),'meshes':len(meshes),'actions':[a['name'] for a in actions]}))
