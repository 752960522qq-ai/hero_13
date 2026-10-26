"""Restore original shoulder proportions and match the upper-arm skin pivot locally."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path(__file__).resolve().parent;R3=P.parent/'refinement-r3'
bpy.ops.wm.open_mainfile(filepath=str(R3/'vest_xiaqing_r3.blend'))
r=bpy.data.objects['Xiaqing_Native_Rig'];o=bpy.data.objects['Vest_Body'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
r.animation_data.action=None;r.data.pose_position='REST'
for b in r.pose.bones:b.matrix_basis.identity()
s.frame_set(0);bpy.context.view_layer.update()
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
source=np.load(P/'source_vertices.npz')['v'];stable=np.array([x.value for x in o.data.attributes['r2_vertex_id'].data]);q=source[stable]
old=np.array([v.co[:] for v in o.data.vertices]);target=q*1.7+np.array([-.00023407833465015,-.1259081221330608,-.00964825950517234])
f=smooth((q[:,2]-.700)/.065)
# The original-source jaw/root ring is already coincident. Keep the ring bit-exact.
m=json.loads((R3/'seam_manifest.json').read_text());rootids=np.array([j for i,j in m['root_pairs']],dtype=int);f[rootids]=0
new=old+(target-old)*f[:,None]
for i in np.where(f>1e-8)[0]:o.data.vertices[int(i)].co=new[i]
# Rebind cap and upper-arm transition anatomically, without muscle auxiliary drivers.
# Medial chest stays on its existing spine/neck binding; outside cap transitions
# across the true shoulder joint into the humerus rather than all following it.
weightmask=smooth((np.abs(q[:,0])-.050)/.035)*smooth((q[:,2]-.715)/.045)
protected=np.array([v.value for v in o.data.attributes['r3_neck_preserve'].data])>0
weightmask[protected]=0
names={g.index:g.name for g in o.vertex_groups};modified=[]
for i in np.where(weightmask>1e-7)[0]:
 i=int(i);v=o.data.vertices[i];side='l' if q[i,0]>0 else 'r';pt=q[i].copy();pt[0]=abs(pt[0]);a=np.array([.100,.082,.798]);b=np.array([.198,.051,.705]);ab=b-a;t=float(np.dot(pt-a,ab)/np.dot(ab,ab))
 h=float(smooth((t+.35)/.65));c=float(smooth((pt[0]-.045)/.045));canonical={'spine_2':(1-c)*(1-h),side+'_arm_clavicle':c*(1-h),side+'_arm_humerus':h}
 base={names[g.group]:g.weight for g in v.groups};fac=float(weightmask[i]);out={n:w*(1-fac) for n,w in base.items()}
 for n,w in canonical.items():out[n]=out.get(n,0)+w*fac
 top=sorted(((n,w) for n,w in out.items() if w>1e-8),key=lambda z:-z[1])[:4];total=sum(w for n,w in top)
 for g in list(v.groups):o.vertex_groups[g.group].remove([i])
 for n,w in top:o.vertex_groups[n].add([i],w/total,'REPLACE')
 modified.append(i)
# Shoulder origins match the unwarped source body; correction fades to zero at
# the elbow so the existing forearm/wrist/finger rest positions remain exact.
oldbones={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in r.data.bones};deltas={}
for side,sign in [('l',1),('r',-1)]:
 start=oldbones[side+'_arm_humerus'][0];end=oldbones[side+'_arm_radius'][0];ab=end-start
 dest=Vector((sign*.100*1.7-.00023407833465015,.082*1.7-.1259081221330608,.798*1.7-.00964825950517234));delta=dest-start
 for bone in r.data.bones:
  if bone.name!=side+'_arm_humerus' and not any(p.name==side+'_arm_humerus' for p in bone.parent_recursive):continue
  t=float((bone.head_local-start).dot(ab)/ab.length_squared);fac=float(1-smooth(t));d=delta*fac
  if d.length>1e-8:deltas[bone.name]=d.copy()
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.mode_set(mode='EDIT')
for name,d in deltas.items():
 eb=r.data.edit_bones[name];eb.head=oldbones[name][0]+d;eb.tail=oldbones[name][1]+d
bpy.ops.object.mode_set(mode='OBJECT')
# Recompute only the eight Idle clavicle rotation channels for the new resting slope.
r.data.pose_position='POSE';action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));r.animation_data.action=action
paths={side:f'pose.bones["{side}_arm_clavicle"].rotation_quaternion' for side in ['l','r']}
times=np.array([k.co.x for k in next(fc for fc in action.fcurves if fc.data_path==paths['l'] and fc.array_index==0).keyframe_points]);quats=[]
for frame in times:
 s.frame_set(int(frame),subframe=float(frame-int(frame)));bpy.context.view_layer.update();parent=r.pose.bones['spine_2'];pr=parent.matrix.to_3x3()@parent.bone.matrix_local.to_3x3().inverted();row=[]
 for si,side in enumerate(['l','r']):
  clav=r.pose.bones[side+'_arm_clavicle'];arm=r.pose.bones[side+'_arm_humerus'];vec=pr.inverted()@(arm.head-clav.head);tar=vec.copy();tar.z=(arm.bone.head_local-clav.bone.head_local).z;xy=(vec.x*vec.x+vec.y*vec.y)**.5;newxy=max(0,vec.length_squared-tar.z*tar.z)**.5;tar.x*=newxy/xy;tar.y*=newxy/xy
  align=vec.rotation_difference(tar);rotation=pr.to_quaternion()@align@pr.to_quaternion().inverted();head=clav.head.copy();clav.matrix=Matrix.Translation(head)@rotation.to_matrix().to_4x4()@Matrix.Translation(-head)@clav.matrix.copy();bpy.context.view_layer.update();quat=clav.rotation_quaternion.copy()
  if quats:quat.make_compatible(Quaternion(quats[-1][si]))
  row.append(list(quat))
 quats.append(row)
for si,side in enumerate(['l','r']):
 for fc in action.fcurves:
  if fc.data_path!=paths[side]:continue
  for k,quat in zip(fc.keyframe_points,quats):
   d=quat[si][fc.array_index]-k.co.y;k.co.y+=d;k.handle_left.y+=d;k.handle_right.y+=d
  fc.update()
# Recompute only edited surface normals, preserving the rest of the mesh.
oldnorm=[n.vector[:] for n in o.data.corner_normals];bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
if o.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
o.data.update();norm=[n.vector[:] for n in o.data.corner_normals]
for loop in o.data.loops:
 if f[loop.vertex_index]<1e-7:norm[loop.index]=oldnorm[loop.index]
o.data.normals_split_custom_set(norm)
policy={'rest_bone_translations':{n:list(d) for n,d in deltas.items()},'allowed_action_channels':{'Idle':[[paths[side],j] for side in ['l','r'] for j in range(4)]},'description':'Source shoulder original proportions and pivot restored locally; forearm/wrist/fingers and all nonbody parts remain unchanged.'}
(P/'r4_change_policy.json').write_text(json.dumps(policy,indent=2))
(P/'seam_manifest.json').write_text(json.dumps(m,indent=2))
o['refinement_r4']='Original-source shoulder geometry, matching anatomical pivot and cap clavicle/humerus weight transition'
report={'geometry_vertices':int(sum(f>1e-8)),'weight_vertices':len(modified),'moved_bones':len(deltas),'max_geom_delta_m':float(np.linalg.norm(new-old,axis=1).max()),'rest_bone_translations':policy['rest_bone_translations'],'animation_channels_changed':8,'publication':'local_only'}
(P/'repair_report.json').write_text(json.dumps(report,indent=2))
r.animation_data.action=action;s.frame_set(1)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'vest_xiaqing_r4.blend'),compress=True)
print('R4 SAVED',json.dumps(report))
