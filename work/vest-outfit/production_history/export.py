import bpy,json,struct,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;O=P/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'vest_xiaqing.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='POSE';rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for pb in rig.pose.bones:pb.matrix_basis.identity()
for a in bpy.data.actions:a.use_fake_user=True;a.name=a.name.split('_')[0]
bpy.context.scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type=='ARMATURE' or o.type=='MESH' and not o.hide_render:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=rig
result=bpy.ops.export_scene.gltf(filepath=str(O/'vest_xiaqing.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_bake_animation=True,export_force_sampling=True,export_frame_range=False,export_reset_pose_bones=True,export_def_bones=False,export_leaf_bone=False,export_all_influences=True,export_skins=True,export_extras=True,export_morph=False,export_yup=True)
raw=(O/'vest_xiaqing.glb').read_bytes();jl=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+jl]);binary=raw[28+jl:];types={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'};counts={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16};finite=True
for ac in doc['accessors']:
 if 'bufferView' not in ac:continue
 view=doc['bufferViews'][ac['bufferView']];dtype=np.dtype(types[ac['componentType']]);count=counts[ac['type']];ar=np.ndarray((ac['count'],count),dtype=dtype,buffer=binary,offset=view.get('byteOffset',0)+ac.get('byteOffset',0),strides=(view.get('byteStride',count*dtype.itemsize),dtype.itemsize));finite=finite and bool(np.isfinite(ar).all())
report={'file':str(O/'vest_xiaqing.glb'),'size':len(raw),'animations':[{'name':a['name'],'channels':len(a['channels'])} for a in doc.get('animations',[])],'mesh_count':len(doc.get('meshes',[])),'skin_joint_counts':[len(s['joints']) for s in doc.get('skins',[])],'finite':finite,'extra_influence_meshes':[m['name'] for m in doc['meshes'] if any('JOINTS_1' in p['attributes'] for p in m['primitives'])]}
(O/'export_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert finite;assert {a['name'] for a in doc.get('animations',[])}=={'Idle','Walk','Run'};assert all(len(s['joints'])==437 for s in doc['skins'])
