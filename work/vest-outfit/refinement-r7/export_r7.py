import bpy,json,struct,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;O=P;bpy.ops.wm.open_mainfile(filepath=str(O/'vest_xiaqing_r7.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='POSE';rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for pb in rig.pose.bones:pb.matrix_basis.identity()
assert {a.name.split('_')[0] for a in bpy.data.actions}=={'Idle','Walk','Run','Aim'}
for a in bpy.data.actions:a.use_fake_user=True;a.name=a.name.split('_')[0]
bpy.context.scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if not o.get('comparison_only') and (o.type=='ARMATURE' or o.type=='MESH' and not o.hide_render):o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=rig
# Deterministic four-influence browser binding. Do not save changes to blend.
trimmed=0
for obj in bpy.context.scene.objects:
 if obj.type!='MESH' or obj.hide_render or obj.get('comparison_only'):continue
 names={g.index:g.name for g in obj.vertex_groups}
 for vertex in obj.data.vertices:
  groups=[(g.group,g.weight,names[g.group]) for g in vertex.groups if g.weight>0 and names[g.group] in rig.data.bones]
  groups.sort(key=lambda item:(-item[1],item[2]));keep=groups[:4];total=sum(item[1] for item in keep)
  if len(groups)>4:trimmed+=1
  if not keep:continue
  for index in [g.group for g in vertex.groups]:obj.vertex_groups[index].remove([vertex.index])
  for index,weight,name in keep:obj.vertex_groups[index].add([vertex.index],weight/total,'REPLACE')
print('Vertices trimmed to four influences',trimmed)

result=bpy.ops.export_scene.gltf(filepath=str(O/'vest_xiaqing_r7.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_bake_animation=True,export_force_sampling=True,export_frame_range=False,export_reset_pose_bones=True,export_def_bones=False,export_leaf_bone=False,export_all_influences=False,export_skins=True,export_extras=True,export_morph=False,export_yup=True)
raw=(O/'vest_xiaqing_r7.glb').read_bytes();jl=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+jl]);binary=raw[28+jl:];types={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'};counts={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16};finite=True
for ac in doc['accessors']:
 if 'bufferView' not in ac:continue
 view=doc['bufferViews'][ac['bufferView']];dtype=np.dtype(types[ac['componentType']]);count=counts[ac['type']];ar=np.ndarray((ac['count'],count),dtype=dtype,buffer=binary,offset=view.get('byteOffset',0)+ac.get('byteOffset',0),strides=(view.get('byteStride',count*dtype.itemsize),dtype.itemsize));finite=finite and bool(np.isfinite(ar).all())
report={'file':str(O/'vest_xiaqing_r7.glb'),'size':len(raw),'animations':[{'name':a['name'],'channels':len(a['channels'])} for a in doc.get('animations',[])],'mesh_count':len(doc.get('meshes',[])),'skin_joint_counts':[len(s['joints']) for s in doc.get('skins',[])],'finite':finite,'extra_influence_meshes':[m['name'] for m in doc['meshes'] if any('JOINTS_1' in p['attributes'] for p in m['primitives'])]}
report['vertices_trimmed']=trimmed
(O/'export_r7_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert finite;assert {a['name'] for a in doc.get('animations',[])}=={'Idle','Walk','Run','Aim'};assert all(len(s['joints'])==437 for s in doc['skins'])

weight_rows=[];maximum=0.0
for mesh in doc['meshes']:
 for primitive in mesh['primitives']:
  at=primitive['attributes'];assert 'JOINTS_1' not in at and 'WEIGHTS_1' not in at
  ac=doc['accessors'][at['WEIGHTS_0']];view=doc['bufferViews'][ac['bufferView']];dt=np.dtype(types[ac['componentType']]);a=np.ndarray((ac['count'],4),dtype=dt,buffer=binary,offset=view.get('byteOffset',0)+ac.get('byteOffset',0),strides=(view.get('byteStride',4*dt.itemsize),dt.itemsize));error=float(abs(a.sum(1)-1).max());maximum=max(maximum,error);assert error<1e-5;assert np.isfinite(a).all() and (a>=0).all();weight_rows.append({'mesh':mesh['name'],'vertices':len(a),'max_normalization_error':error})
report['weight_validation']=weight_rows;report['max_normalization_error']=maximum;report['four_influences_only']=True
(O/'export_r7_report.json').write_text(json.dumps(report,indent=2));print('NORMALIZATION CHECK',maximum)

import hashlib
report["sha256"]=hashlib.sha256(raw).hexdigest()
report["source_blend_sha256"]=hashlib.sha256((O/"vest_xiaqing_r7.blend").read_bytes()).hexdigest()
(O/"export_r7_report.json").write_text(json.dumps(report,indent=2))
