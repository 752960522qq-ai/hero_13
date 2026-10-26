"""Combine the two localized skin/rig fixes without altering mesh geometry."""
import bpy,runpy,json,numpy as np,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
def geometry_hash(o):
 a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a)
 # Topology is unchanged by these patches; retain an independent fingerprint.
 loops=np.array([l.vertex_index for l in o.data.loops],dtype=np.int32)
 return hashlib.sha256(a.tobytes()+loops.tobytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'refinement-r4/vest_xiaqing_r4.blend'))
baseline={o.name:geometry_hash(o) for o in bpy.context.scene.objects if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=str(P/'arms/upper_candidate.blend'))
calf=runpy.run_path(str(P/'calves/apply_calves.py'))['apply_calves']()
after={o.name:geometry_hash(o) for o in bpy.context.scene.objects if o.type=='MESH'}
assert baseline==after,'Mesh geometry changed unexpectedly'
r=bpy.data.objects['Xiaqing_Native_Rig'];r.data.pose_position='POSE';r.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(70)
report={'mesh_geometry_exactly_unchanged_from_r4':True,'mesh_count_including_hidden_helpers':len(after),'geometry_sha256':after,'calf':calf,'upper':json.loads((P/'arms/upper_repair_report.json').read_text()),'deployed':False}
(P/'repair_report.json').write_text(json.dumps(report,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'vest_xiaqing_r5.blend'),compress=True)
print('R5_SAVED_MESH_UNCHANGED')
