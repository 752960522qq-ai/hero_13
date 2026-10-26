"""Targeted pose edits only: modest Idle arm inset and Run neck retraction."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d,minimum_filter1d
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'refinement-r6/vest_xiaqing_r6.blend'))
r=bpy.data.objects['Xiaqing_Native_Rig'];o=bpy.data.objects['Vest_Body'];s=bpy.context.scene
for t in r.animation_data.nla_tracks:t.mute=True
r.data.pose_position='POSE'
source=np.load(ROOT/'production_history/refinement-r4/source_vertices.npz')['v'];stable=np.array([v.value for v in o.data.attributes['r2_vertex_id'].data]);q=source[stable]
thigh=np.where((q[:,2]>.34)&(q[:,2]<.555)&(abs(q[:,0])<.15))[0]
hands={side:np.where((q[:,0]*sign>.175)&(q[:,2]>.535)&(q[:,2]<.645))[0] for side,sign in [('l',1),('r',-1)]}
def faces_for(ii):
 remap={int(i):j for j,i in enumerate(ii)};return [[remap[i] for i in p.vertices] for p in o.data.polygons if all(i in remap for i in p.vertices)]
tf=faces_for(thigh);hf={side:faces_for(ii) for side,ii in hands.items()}
def pose(frame):
 s.frame_set(int(frame),subframe=float(frame-int(frame)));bpy.context.view_layer.update()
def coords():
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);ev.to_mesh_clear();return v.reshape(-1,3)
def axis():
 sp=r.pose.bones['spine_2'];pr=sp.matrix.to_3x3()@sp.bone.matrix_local.to_3x3().inverted();return (pr@Vector((0,1,0))).normalized()
def closest_and_intersects(points,tree,faces):
 distance=min(tree.find_nearest(Vector(p))[3] for p in points)
 if distance<.018:return distance,True
 ht=BVHTree.FromPolygons([Vector(p) for p in points],faces,all_triangles=False)
 return distance,bool(tree.overlap(ht))
def write_quats(action,paths,times,quats):
 for bi,path in enumerate(paths):
  for fc in action.fcurves:
   if fc.data_path!=path:continue
   assert len(fc.keyframe_points)==len(times)
   for k,rows in zip(fc.keyframe_points,quats):
    d=float(rows[bi][fc.array_index])-k.co.y;k.co.y+=d;k.handle_left.y+=d;k.handle_right.y+=d
   fc.update()
idle=next(a for a in bpy.data.actions if a.name.startswith('Idle'));r.animation_data.action=idle
paths=[f'pose.bones["{side}_arm_humerus"].rotation_quaternion' for side in ['l','r']]
times=np.array([k.co.x for k in next(fc for fc in idle.fcurves if fc.data_path==paths[0] and fc.array_index==0).keyframe_points])
knots=np.unique(np.r_[times[::8],times[-1]]);raw=[];fit_report=[]
for frame in knots:
 pose(frame);points=coords();tree=BVHTree.FromPolygons([Vector(v) for v in points[thigh]],tf,all_triangles=False);ax=axis();row=[]
 for side,sign in [('l',1),('r',-1)]:
  head=r.pose.bones[side+'_arm_humerus'].head.copy();hand=points[hands[side]];lower,upper=0.,7.
  for _ in range(7):
   angle=(lower+upper)/2;rotation=Quaternion(ax,sign*math.radians(angle)).to_matrix();candidate=(hand-np.array(head))@np.array(rotation).T+np.array(head);distance,bad=closest_and_intersects(candidate,tree,hf[side])
   if not bad:lower=angle
   else:upper=angle
  row.append(lower)
 raw.append(row)
raw=np.array(raw);raw[0]=raw[-1]=np.minimum(raw[0],raw[-1])
safe=np.minimum(raw,gaussian_filter1d(minimum_filter1d(raw,size=3,axis=0,mode='nearest'),sigma=.6,axis=0,mode='nearest'));safe[0]=safe[-1]=np.minimum(safe[0],safe[-1])
fits=[PchipInterpolator(knots,safe[:,i]) for i in range(2)];quats=[]
for frame in times:
 pose(frame);ax=axis();row=[]
 for bi,(side,sign) in enumerate([('l',1),('r',-1)]):
  pb=r.pose.bones[side+'_arm_humerus'];head=pb.head.copy();degrees=float(fits[bi](frame));rotation=Quaternion(ax,sign*math.radians(degrees));pb.matrix=Matrix.Translation(head)@rotation.to_matrix().to_4x4()@Matrix.Translation(-head)@pb.matrix.copy();bpy.context.view_layer.update();quat=pb.rotation_quaternion.copy()
  if quats:quat.make_compatible(Quaternion(quats[-1][bi]))
  row.append(list(quat))
 quats.append(row)
write_quats(idle,paths,times,quats)
report={'idle':{'maximum_inward_degrees':float(safe.max()),'minimum_inward_degrees':float(safe.min()),'clearance_target_m':.018,'fitting_knots':knots.tolist(),'safe_inward_angles':safe.tolist(),'changed_channels':8},'run':{}}
run=next(a for a in bpy.data.actions if a.name.startswith('Run'));r.animation_data.action=run
path='pose.bones["neck_0"].rotation_quaternion';rt=np.array([k.co.x for k in next(fc for fc in run.fcurves if fc.data_path==path and fc.array_index==0).keyframe_points]);rows=[];angles=[]
for frame in rt:
 pose(frame);sp=r.pose.bones['spine_2'];pr=sp.matrix.to_3x3()@sp.bone.matrix_local.to_3x3().inverted();side=pr@Vector((1,0,0));side.z=0;side.normalize();front=side.cross(Vector((0,0,1)));v=r.pose.bones['head'].head-r.pose.bones['neck_0'].head;before=math.degrees(math.atan2(v.dot(front),v.z));correction=max(0,min(18,before-28.))
 pb=r.pose.bones['neck_0'];head=pb.head.copy();rot=Quaternion(side,-math.radians(correction));pb.matrix=Matrix.Translation(head)@rot.to_matrix().to_4x4()@Matrix.Translation(-head)@pb.matrix.copy();bpy.context.view_layer.update();quat=pb.rotation_quaternion.copy()
 if rows:quat.make_compatible(Quaternion(rows[-1][0]))
 # Share the correction with the head so neck retraction does not make the
 # character lift her chin excessively while running.
 hp=r.pose.bones['head'];hh=hp.head.copy();comp=Quaternion(side,math.radians(correction*.5));hp.matrix=Matrix.Translation(hh)@comp.to_matrix().to_4x4()@Matrix.Translation(-hh)@hp.matrix.copy();bpy.context.view_layer.update();hq=hp.rotation_quaternion.copy()
 if rows:hq.make_compatible(Quaternion(rows[-1][1]))
 rows.append([list(quat),list(hq)]);angles.append({'frame':float(frame),'before_forward_degrees':before,'back_correction_degrees':correction,'head_compensation_degrees':correction*.5})
write_quats(run,[path,'pose.bones["head"].rotation_quaternion'],rt,rows);report['run']={'neck_forward_limit_degrees':28.,'changed_channels':8,'samples':angles}
report['geometry_rest_bones_weights_changed']=False;report['deployed']=False
(P/'pose_report.json').write_text(json.dumps(report,indent=2));s.frame_set(6);r.animation_data.action=run;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'pose_candidate.blend'),compress=True)
print('IDLE_RUN_POSE_REPAIR_SAVED',report['idle']['maximum_inward_degrees'])
