import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'refinement-r5/vest_xiaqing_r5.blend'))
r=bpy.data.objects['Xiaqing_Native_Rig'];o=bpy.data.objects['Vest_Body'];s=bpy.context.scene
src=np.load(ROOT/'refinement-r4/source_vertices.npz')['v'];ids=np.array([a.value for a in o.data.attributes['r2_vertex_id'].data]);q=src[ids];rest=np.array([v.co[:] for v in o.data.vertices]);edges=np.array([e.vertices[:] for e in o.data.edges]);out={'rig_object_matrix':np.array(r.matrix_world).tolist(),'calves':{},'scale_curves':{},'bones':{},'poses':{}}
def sim(a,b):
 ac=a-a.mean(0);bc=b-b.mean(0);u,d,vt=np.linalg.svd(ac.T@bc);rot=u@vt
 if np.linalg.det(rot)<0:u[:,-1]*=-1;rot=u@vt
 scale=float(np.sum((ac@rot)*bc)/np.sum(ac*ac));trans=b.mean(0)-a.mean(0)@rot*scale;err=np.linalg.norm(a@rot*scale+trans-b,axis=1)
 affine=np.linalg.lstsq(np.c_[a,np.ones(len(a))],b,rcond=None)[0]
 return {'uniform_scale':scale,'translation':trans.tolist(),'residual_mm_mean_p95_max':(np.array([err.mean(),np.percentile(err,95),err.max()])*1000).tolist(),'affine_singular_values':np.linalg.svd(affine[:3],compute_uv=False).tolist()}
calfids={};calfedges={}
for side,sign in [('l',1),('r',-1)]:
 mask=(q[:,0]*sign>0)&(q[:,2]>.215)&(q[:,2]<.345);ii=np.where(mask)[0];calfids[side]=ii;ed=edges[mask[edges[:,0]]&mask[edges[:,1]]];calfedges[side]=ed
 lens=np.linalg.norm(rest[ed[:,1]]-rest[ed[:,0]],axis=1);orig=np.linalg.norm(q[ed[:,1]]-q[ed[:,0]],axis=1)*1.7;rat=lens/np.maximum(orig,1e-12)
 row={'vertices':len(ii),'best_source_similarity':sim(q[ii],rest[ii]),'rest_edge_length_vs_source1p7_p01_p50_p99':np.percentile(rat,[1,50,99]).tolist(),'slices':[]}
 for z in [.23,.25,.28,.31,.335]:
  jj=np.where(mask&(abs(q[:,2]-z)<.006))[0]
  row['slices'].append({'source_z':z,'n':len(jj),'source1p7_center':(q[jj].mean(0)*1.7).tolist(),'current_center':rest[jj].mean(0).tolist(),'source1p7_xy_span':(np.ptp(q[jj,:2],axis=0)*1.7).tolist(),'current_xy_span':np.ptp(rest[jj,:2],axis=0).tolist()})
 out['calves'][side]=row
 for name in [side+'_leg_femur',side+'_leg_tibia',side+'_leg_ankle',side+'_leg_tibia_twist_0_H',side+'_leg_tibia_twist_1_H',side+'_leg_tibia_twist_2_H']:
  b=r.data.bones.get(name)
  if b:out['bones'][name]={'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None,'inherit_scale':b.inherit_scale}
for a in bpy.data.actions:
 rows={}
 for f in a.fcurves:
  if f.data_path.endswith('.scale') and any(t in f.data_path for t in ['leg_','hips','COG','spine_']):
   v=np.array([k.co.y for k in f.keyframe_points]);rows[f.data_path+f'[{f.array_index}]']=[float(v.min()),float(v.max())]
 out['scale_curves'][a.name]=rows
for t in r.animation_data.nla_tracks:t.mute=True
for phase in ['Idle','Walk','Run']:
 a=next(a for a in bpy.data.actions if a.name.startswith(phase));r.data.pose_position='POSE';r.animation_data.action=a;out['poses'][phase]=[]
 for frac in [0,.35,.70]:
  f=float(a.frame_range[0]+frac*(a.frame_range[1]-a.frame_range[0]));s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pos=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();row={'fraction':frac,'bones':{},'calves':{}}
  for name in out['bones']:
   pb=r.pose.bones[name];m=pb.matrix@pb.bone.matrix_local.inverted();sv=np.linalg.svd(np.array(m)[:3,:3],compute_uv=False);row['bones'][name]={'sv':sv.tolist(),'det':float(np.linalg.det(np.array(m)[:3,:3])),'head':list(pb.head),'scale':list(pb.scale)}
  for side,ii in calfids.items():
   ed=calfedges[side];rat=np.linalg.norm(pos[ed[:,1]]-pos[ed[:,0]],axis=1)/np.maximum(np.linalg.norm(rest[ed[:,1]]-rest[ed[:,0]],axis=1),1e-12);row['calves'][side]={'dynamic_edge_ratio_p01_p50_p99':np.percentile(rat,[1,50,99]).tolist(),'current_posed_best_source_similarity':sim(q[ii],pos[ii]),'rest_to_pose_best_similarity':sim(rest[ii],pos[ii])}
  out['poses'][phase].append(row)
(P/'leg_diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
