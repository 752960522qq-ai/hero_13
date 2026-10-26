"""Preserve original neck under animation: rigid head binding, smooth existing body-root transition."""
import bpy,numpy as np,json,shutil
from pathlib import Path
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
P=Path(__file__).resolve().parent
base=P/'neck_pre_rigid.blend'
if not base.exists():shutil.copy2(P/'neck_rebuilt.blend',base)
bpy.ops.wm.open_mainfile(filepath=str(base));r=bpy.data.objects['Xiaqing_Native_Rig'];r.animation_data.action=None;r.data.pose_position='REST'
for t in r.animation_data.nla_tracks:t.mute=True
for b in r.pose.bones:b.matrix_basis.identity()
source=bpy.data.objects['Vest_SourceNeck'];body=bpy.data.objects['Vest_Body'];m=json.loads((P/'seam_manifest.json').read_text());rootids=np.array([j for i,j in m['root_pairs']],dtype=int)
for v in source.data.vertices:
 for g in list(v.groups):source.vertex_groups[g.group].remove([v.index])
 source.vertex_groups['head'].add([v.index],1,'REPLACE')
source['r3_skinning_policy']='Rigid original neck follows head; no shape deformation in any clip'
# Geodesic distance gives a continuous paint field with no hard X/Z palette cliff.
p=np.array([v.co[:] for v in body.data.vertices]);ed=np.array([e.vertices[:] for e in body.data.edges]);length=np.linalg.norm(p[ed[:,0]]-p[ed[:,1]],axis=1);rr=np.r_[ed[:,0],ed[:,1]];cc=np.r_[ed[:,1],ed[:,0]];A=csr_matrix((np.r_[length,length],(rr,cc)),shape=(len(p),len(p)));dist=dijkstra(A,indices=rootids,min_only=True,limit=.090);f=np.clip(1-dist/.090,0,1);f=f*f*(3-2*f);f[rootids]=1
existing_objects=set(bpy.data.objects);existing_actions=set(bpy.data.actions)
with bpy.data.libraries.load(str(P.parent.parent/'refinement-r2/vest_xiaqing_r2.blend'),link=False) as (frm,to):to.objects=['Vest_Body']
donor=to.objects[0];dn={g.index:g.name for g in donor.vertex_groups}
ids=np.where(f>1e-8)[0]
for i in ids:
 i=int(i);v=body.data.vertices[i];ww={dn[g.group]:g.weight*(1-f[i]) for g in donor.data.vertices[i].groups};ww['head']=ww.get('head',0)+f[i]
 for g in list(v.groups):body.vertex_groups[g.group].remove([i])
 top=sorted(ww.items(),key=lambda x:(-x[1],x[0]))[:4];total=sum(w for n,w in top)
 for n,w in top:
  if w>1e-9:body.vertex_groups[n].add([i],float(w/total),'REPLACE')

for ob in list(bpy.data.objects):
 if ob not in existing_objects:bpy.data.objects.remove(ob,do_unlink=True)
for ac in list(bpy.data.actions):
 if ac not in existing_actions:bpy.data.actions.remove(ac,do_unlink=True)
# Protect this head-root weight field during the external shoulder merge.
a=body.data.attributes.get('r3_neck_preserve');protect=np.array([v.value for v in a.data]);protect[ids]=1;a.data.foreach_set('value',protect.astype(np.int32))
# Source geometry and all rest-bone matrices are intentionally untouched.
report=json.loads((P/'neck_report.json').read_text());report.update({'rigid_source_neck':True,'source_neck_skinning':'head:1.0 for all vertices','body_root_head_blend_radius_m':.09,'body_root_weight_vertices':len(ids),'protected_body_points_total':int(sum(protect>0)),'bone_rest_or_animation_changed':False});(P/'neck_report.json').write_text(json.dumps(report,indent=2))
m['source_neck_skinning']='head:1.0';m['body_root_head_blend_radius_m']=.09;(P/'seam_manifest.json').write_text(json.dumps(m,indent=2))
r.data.pose_position='POSE';r.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'neck_rebuilt.blend'),compress=True);print('RIGID_NECK_READY',len(ids),int(sum(protect>0)))
