"""Merge the reviewed Aim action while preserving R6 geometry, skin and rig rest."""
import bpy,json,hashlib,struct,numpy as np,re
from pathlib import Path
P=Path(__file__).resolve().parent
def fingerprints():
 result={}
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  a=np.empty(len(ob.data.vertices)*3,dtype=np.float32);ob.data.vertices.foreach_get('co',a);h=hashlib.sha256(a.tobytes());h.update(np.array([l.vertex_index for l in ob.data.loops],dtype=np.int32).tobytes())
  for v in ob.data.vertices:
   for g in v.groups:h.update(struct.pack('<IIf',v.index,g.group,g.weight))
  result[ob.name]=h.hexdigest()
 r=bpy.data.objects['Xiaqing_Native_Rig'];result['rig_rest']=hashlib.sha256(np.array([list(b.matrix_local) for b in r.data.bones],dtype=np.float32).tobytes()).hexdigest()
 return result
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'refinement-r6/vest_xiaqing_r6.blend'));baseline=fingerprints()
bpy.ops.wm.open_mainfile(filepath=str(P/'pose_adjustments/pose_candidate.blend'))
with bpy.data.libraries.load(str(P/'aiming/aiming_candidate.blend'),link=False) as (src,dst):dst.actions=[n for n in src.actions if n=='Aim']
assert len(dst.actions)==1 and dst.actions[0] is not None,'Aim action missing'
action=dst.actions[0];action.name='Aim';action.use_fake_user=True;r=bpy.data.objects['Xiaqing_Native_Rig']
for f in action.fcurves:
 match=re.search(r'pose.bones\["(.+?)"\]',f.data_path)
 if match:assert match.group(1) in r.data.bones,f.data_path
assert fingerprints()==baseline,'Unexpected geometry, skin or rest-rig mutation'
assert {a.name.split('_')[0] for a in bpy.data.actions}=={'Idle','Walk','Run','Aim'}
report={'geometry_skin_and_rest_bones_identical_to_r6':True,'bone_count':len(r.data.bones),'actions':[a.name for a in bpy.data.actions],'fingerprints':baseline,'deployment_performed':False}
(P/'merge_report.json').write_text(json.dumps(report,indent=2));r.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));r.data.pose_position='POSE';bpy.context.scene.frame_set(70);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'vest_xiaqing_r7.blend'),compress=True)
print('R7_MERGED_GEOMETRY_SKIN_REST_UNCHANGED')
