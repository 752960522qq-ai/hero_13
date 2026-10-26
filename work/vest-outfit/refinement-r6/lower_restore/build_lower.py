import bpy,numpy as np,json,runpy,math
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'refinement-r5/vest_xiaqing_r5.blend'))
o=bpy.data.objects['Vest_Body'];r=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
for tr in r.animation_data.nla_tracks:tr.mute=True
r.animation_data.action=None;r.data.pose_position='REST'
for pb in r.pose.bones:pb.matrix_basis.identity()
src=np.load(ROOT/'refinement-r4/source_vertices.npz')['v'];stable=np.array([a.value for a in o.data.attributes['r2_vertex_id'].data]);q=src[stable];old=np.array([v.co[:] for v in o.data.vertices]);T=np.array([-.00023407833465015,-.1259081221330608,-.00964825950517234]);target=q*1.7+T
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
factor=1-smooth((q[:,2]-.60)/.05);factor[abs(q[:,0])>=.155]=0
new=old+(target-old)*factor[:,None];names=[g.name for g in o.vertex_groups];gi={n:i for i,n in enumerate(names)};W=np.zeros((len(old),len(names)))
for v in o.data.vertices:
 for g in v.groups:W[v.index,g.group]=g.weight
bone_old={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in r.data.bones};bone_delta={};shoe_coords={};cuts={};seamids={};joint_targets={}
from scipy.spatial import cKDTree
for side,sign in [('l',1),('r',-1)]:
 shoe=bpy.data.objects['Shoe_'+side.upper()];si=np.array([a.value for a in shoe.data.attributes['source_vertex_id'].data]);shoe_coords[side]=src[si]*1.7+T
 dist,_=cKDTree(np.array([v.co[:] for v in shoe.data.vertices])).query(old);seamids[side]=np.where(dist<1e-7)[0];cuts[side]=float(q[seamids[side],2].max())
 hip=Vector(np.array([sign*.055,.081,.552])*1.7+T);knee=Vector(np.array([sign*.050,.074,.355])*1.7+T);ankle=Vector(target[seamids[side]].mean(0));ankle.z-=.015
 joint_targets[side]={'hip':list(hip),'knee':list(knee),'ankle':list(ankle)}
 anchors=[bone_old[side+'_leg_femur'][0],bone_old[side+'_leg_tibia'][0],bone_old[side+'_leg_ankle'][0]];ds=[hip-anchors[0],knee-anchors[1],ankle-anchors[2]]
 # Every leg helper is carried with its anatomical segment, including the
 # muscle offsets that are children of hips rather than of femur itself.
 for b in r.data.bones:
  if not b.name.startswith(side+'_leg_'):continue
  point=b.head_local
  if point.z>=anchors[1].z:
   a,bb=anchors[:2];u=float(np.clip((point-a).dot(bb-a)/(bb-a).length_squared,0,1));delta=ds[0]*(1-u)+ds[1]*u
  else:
   a,bb=anchors[1:];u=float(np.clip((point-a).dot(bb-a)/(bb-a).length_squared,0,1));delta=ds[1]*(1-u)+ds[2]*u
  bone_delta[b.name]=delta.copy()
 # Main segment pivots use exact anatomy, independent of helper placement.
 for n,d in zip(['femur','tibia','ankle'],ds):bone_delta[side+'_leg_'+n]=d.copy()
 for i in np.where((q[:,0]*sign>0)&(abs(q[:,0])<.155)&(q[:,2]<.585))[0]:
  i=int(i);z=float(q[i,2]);canonical=np.zeros(len(names));a=float(1-smooth((z-cuts[side])/(.222-cuts[side])));k=float(smooth((z-.345)/.030));h=float(smooth((z-.50)/.06))
  if z<.345:canonical[gi[side+'_leg_ankle']]=a;canonical[gi[side+'_leg_tibia']]=1-a
  elif z<.375:canonical[gi[side+'_leg_tibia']]=1-k;canonical[gi[side+'_leg_femur']]=k
  else:canonical[gi[side+'_leg_femur']]=1-h;canonical[gi['hips']]=h
  f=float(1-smooth((z-.54)/.045));row=W[i]*(1-f)+canonical*f;keep=np.argsort(row)[-4:];nr=np.zeros(len(names));nr[keep]=row[keep];nr/=nr.sum();W[i]=nr
 for i in seamids[side]:W[i]=0;W[i,gi[side+'_leg_ankle']]=1
ids=np.where(factor>1e-8)[0]
# Recover source corner normals by original face/vertex identity. No shading
# inherited from the distorted RBF surface survives on fully restored regions.
existing=set(bpy.data.objects)
with bpy.data.libraries.load(str(ROOT/'refinement-r3/shoes/source_processed.blend'),link=False) as (frm,to):to.objects=list(frm.objects)
donor=to.objects[0];assert len(donor.data.vertices)==68198
table={}
for poly in donor.data.polygons:
 key=tuple(sorted(poly.vertices));table[key]={donor.data.loops[li].vertex_index:np.array(donor.data.corner_normals[li].vector) for li in poly.loop_indices}
oldnorm=np.array([n.vector[:] for n in o.data.corner_normals]);newnorm=oldnorm.copy();normalids=[]
for poly in o.data.polygons:
 key=tuple(sorted(int(stable[i]) for i in poly.vertices));rec=table.get(key)
 if rec is None:continue
 for li in poly.loop_indices:
  vi=o.data.loops[li].vertex_index;f=float(factor[vi])
  if f<=1e-8:continue
  nv=rec[int(stable[vi])]*f+oldnorm[li]*(1-f);newnorm[li]=nv/np.linalg.norm(nv);normalids.append(li)
for ob in list(bpy.data.objects):
 if ob not in existing:bpy.data.objects.remove(ob,do_unlink=True)
normalids=np.array(normalids,dtype=np.int32)
action_data={};labels=['Idle','Walk','Run'];cap=math.radians(3.0)
for ai,label in enumerate(labels):
 action=next(a for a in bpy.data.actions if a.name.startswith(label));bones=['l_leg_ankle','r_leg_ankle'];times=None;quats=[]
 for bone in bones:
  fs=sorted([f for f in action.fcurves if f.data_path==f'pose.bones["{bone}"].rotation_quaternion'],key=lambda f:f.array_index);assert len(fs)==4
  if times is None:times=np.array([k.co.x for k in fs[0].keyframe_points])
  rows=[]
  for ki in range(len(times)):
   quat=Quaternion([f.keyframe_points[ki].co.y for f in fs]);quat.normalize()
   if quat.w<0:quat.negate()
   angle=float(quat.angle);new_angle=cap*math.tanh(.15*angle/cap);qq=Quaternion((1,0,0,0)).slerp(quat,new_angle/angle if angle>1e-8 else .15)
   if rows:qq.make_compatible(Quaternion(rows[-1]))
   rows.append(list(qq))
  quats.append(rows)
 prefix='action_'+str(ai)+'_';action_data[prefix+'bones']=np.array(bones);action_data[prefix+'times']=times;action_data[prefix+'quats']=np.array(quats).transpose((1,0,2))
np.savez_compressed(P/'lower_patch.npz',ids=ids,coords=new[ids],weights=W[ids],group_names=np.array(names),bone_names=np.array(list(bone_delta)),bone_heads=np.array([list(bone_old[n][0]+d) for n,d in bone_delta.items()]),bone_tails=np.array([list(bone_old[n][1]+d) for n,d in bone_delta.items()]),loop_ids=normalids,loop_normals=newnorm[normalids],shoe_l_coords=shoe_coords['l'],shoe_r_coords=shoe_coords['r'],action_labels=np.array(labels),**action_data)
runpy.run_path(str(P/'apply_lower.py'))['apply_lower']()
report={'source_similarity':{'scale':1.7,'translation':T.tolist()},'body_coords_changed':len(ids),'bone_targets':len(bone_delta),'source_normals_recovered':len(normalids),'joint_targets':joint_targets,'shoe_seam_vertices':{n:len(v) for n,v in seamids.items()},'source_cut_z':cuts,'ankle_blend_end_source_z':.222,'source_exact_below_z':.60,'upper_fade_end_z':.65,'hands_excluded_by_source_abs_x':.155,'muscle_belly_rigid_tibia_source_z':[.222,.345],'ankle_rotation_small_angle_factor':.15,'ankle_rotation_smooth_cap_degrees':3.0,'ankle_quaternion_channels_changed':24,'hip_knee_and_other_curves_changed':False,'review':{}}
r.data.pose_position='POSE';r.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));s.frame_set(70);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'lower_candidate.blend'),compress=True)
current=np.array([v.co[:] for v in o.data.vertices]);exact=(q[:,2]<=.60)&(abs(q[:,0])<.155);report['source_position_error_max_m']=float(np.linalg.norm(current[exact]-target[exact],axis=1).max())
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=900;s.render.resolution_y=1000;s.render.resolution_percentage=100
ed=np.array([e.vertices[:] for e in o.data.edges]);core=(q[:,2]>.236)&(q[:,2]<.344);ed=ed[core[ed[:,0]]&core[ed[:,1]]];base=np.linalg.norm(current[ed[:,1]]-current[ed[:,0]],axis=1)
for phase in ['Rest','Idle','Walk','Run']:
 if phase=='Rest':r.animation_data.action=None;r.data.pose_position='REST'
 else:r.data.pose_position='POSE';a=next(a for a in bpy.data.actions if a.name.startswith(phase));r.animation_data.action=a;s.frame_set(round(a.frame_range[1]*.35))
 bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pos=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();rat=np.linalg.norm(pos[ed[:,1]]-pos[ed[:,0]],axis=1)/base;row={'core_edge_ratio_min_max':list(map(float,[rat.min(),rat.max()])),'shoe_edge_ratio':{}}
 for side in ['l','r']:
  shoe=bpy.data.objects['Shoe_'+side.upper()];e=np.array([ee.vertices[:] for ee in shoe.data.edges]);orig=np.array([v.co[:] for v in shoe.data.vertices]);ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pp=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();ra=np.linalg.norm(pp[e[:,1]]-pp[e[:,0]],axis=1)/np.maximum(np.linalg.norm(orig[e[:,1]]-orig[e[:,0]],axis=1),1e-12);row['shoe_edge_ratio'][side]=list(map(float,[ra.min(),ra.max()]))
 report['review'][phase]=row
 for label,offset in [('front',(0,-3,.02)),('side',(3,0,.02))]:
  targetcam=Vector((0,0,.47));c=s.camera;c.location=targetcam+Vector(offset);c.rotation_euler=(targetcam-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=1.05;s.render.filepath=str(P/(phase+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
(P/'lower_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
