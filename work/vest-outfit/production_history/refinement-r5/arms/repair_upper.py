"""Skin/pose repair only. Keep every mesh coordinate and all rig rest matrices."""
import bpy,json,math,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path(__file__).resolve().parent;R4=P.parent.parent/'refinement-r4'
bpy.ops.wm.open_mainfile(filepath=str(R4/'vest_xiaqing_r4.blend'))
r=bpy.data.objects['Xiaqing_Native_Rig'];o=bpy.data.objects['Vest_Body'];s=bpy.context.scene
for tr in r.animation_data.nla_tracks:tr.mute=True
src=np.load(R4/'source_vertices.npz')['v'];ids=np.array([a.value for a in o.data.attributes['r2_vertex_id'].data]);q=src[ids]
def smooth(v):
 v=np.clip(v,0,1);return v*v*(3-2*v)
mask=smooth((.110-abs(q[:,0]))/.030)*smooth((q[:,2]-.650)/.055)*smooth((.825-q[:,2])/.040)
preserve=np.array([a.value for a in o.data.attributes['r3_neck_preserve'].data])>0;mask[preserve]=0
names={g.index:g.name for g in o.vertex_groups};changed=[]
for i in np.where(mask>1e-7)[0]:
 i=int(i);v=o.data.vertices[i];old={names[g.group]:g.weight for g in v.groups};spine={n:w for n,w in old.items() if n in ['hips','COG','spine_0','spine_1','spine_2','neck_0','neck_1','head']};total=sum(spine.values())
 if total<1e-5:spine={'spine_2':1.};total=1.
 other=sum(w for n,w in old.items() if n not in spine)
 if other<1e-7:continue
 target={n:w/total for n,w in spine.items()};fac=float(mask[i]);new={n:w*(1-fac)+fac*target.get(n,0) for n,w in old.items()}
 for n,w in target.items():
  if n not in new:new[n]=w*fac
 top=sorted(((n,w) for n,w in new.items() if w>1e-8),key=lambda z:-z[1])[:4];total=sum(w for n,w in top)
 for g in list(v.groups):o.vertex_groups[g.group].remove([i])
 for n,w in top:o.vertex_groups[n].add([i],float(w/total),'REPLACE')
 changed.append(i)
# Add a modest outward shoulder rotation to Idle only, leaving the existing
# breathing, sway, elbow, wrist and finger motion intact. No bone scale edits.
r.data.pose_position='POSE';action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));r.animation_data.action=action
paths={side:f'pose.bones["{side}_arm_humerus"].rotation_quaternion' for side in ['l','r']}
times=np.array([k.co.x for k in next(f for f in action.fcurves if f.data_path==paths['l'] and f.array_index==0).keyframe_points]);quats=[]
ANGLE=18.0
for frame in times:
 s.frame_set(int(frame),subframe=float(frame-int(frame)));bpy.context.view_layer.update();sp=r.pose.bones['spine_2'];pr=sp.matrix.to_3x3()@sp.bone.matrix_local.to_3x3().inverted();axis=pr@Vector((0,1,0));row=[]
 for si,(side,sign) in enumerate([('l',1),('r',-1)]):
  pb=r.pose.bones[side+'_arm_humerus'];head=pb.head.copy();rot=Quaternion(axis,-sign*math.radians(ANGLE));pb.matrix=Matrix.Translation(head)@rot.to_matrix().to_4x4()@Matrix.Translation(-head)@pb.matrix.copy();bpy.context.view_layer.update();quat=pb.rotation_quaternion.copy()
  if quats:quat.make_compatible(Quaternion(quats[-1][si]))
  row.append(list(quat))
 quats.append(row)
for si,side in enumerate(['l','r']):
 for f in action.fcurves:
  if f.data_path!=paths[side]:continue
  for k,qs in zip(f.keyframe_points,quats):
   d=float(qs[si][f.array_index])-k.co.y;k.co.y+=d;k.handle_left.y+=d;k.handle_right.y+=d
  f.update()
report={'torso_weight_vertices':len(changed),'idle_humerus_outward_degrees':ANGLE,'changed_action_channels':[[paths[side],j] for side in ['l','r'] for j in range(4)],'mesh_coordinates_modified':False,'rest_bones_modified':False,'scale_channels_modified':False,'publication':'local_only'}
(P/'upper_repair_report.json').write_text(json.dumps(report,indent=2));s.frame_set(70);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'upper_candidate.blend'),compress=True)
print('UPPER_REPAIR_SAVED',json.dumps(report))
