"""Sparse calf skinning correction. No rest geometry, rig, or action mutations."""
import bpy,numpy as np,json,hashlib
from pathlib import Path
from mathutils import Vector
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parent;ROOT=P.parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'refinement-r4/vest_xiaqing_r4.blend'))
o=bpy.data.objects['Vest_Body'];r=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
names=[g.name for g in o.vertex_groups];gi={n:i for i,n in enumerate(names)}
stable=np.array([x.value for x in o.data.attributes['r2_vertex_id'].data]);q=np.load(ROOT/'refinement-r4/source_vertices.npz')['v'][stable]
rest=np.array([v.co[:] for v in o.data.vertices]);before=np.zeros((len(rest),len(names)))
for v in o.data.vertices:
 for g in v.groups:before[v.index,g.group]=g.weight
after=before.copy()
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
seams={};cuts={};bone_deltas={};bone_rest={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in r.data.bones}
for side in ['l','r']:
 shoe=bpy.data.objects['Shoe_'+side.upper()];tree=cKDTree(np.array([v.co[:] for v in shoe.data.vertices]));dist,_=tree.query(rest);seams[side]=np.where(dist<1e-7)[0];cuts[side]=float(q[seams[side],2].max())
 center=rest[seams[side]].mean(0);center[2]-=.015
 delta=Vector(center)-r.data.bones[side+'_leg_ankle'].head_local
 bone_deltas[side+'_leg_ankle']=delta;bone_deltas[side+'_leg_tibia_twist_2_H']=delta
 for i in np.where((q[:,0]*(1 if side=='l' else -1)>0)&(q[:,2]<.385))[0]:
  i=int(i);row=before[i].copy();factor=float(1-smooth((q[i,2]-.345)/.040));tibia=gi[side+'_leg_tibia'];ankle=gi[side+'_leg_ankle']
  target=row.copy()
  for j,n in enumerate(names):
   if n.startswith(side+'_leg_tibia_twist_'):target[tibia]+=target[j];target[j]=0
  if q[i,2]<.300:
   a=float(1-smooth((q[i,2]-cuts[side])/(.300-cuts[side])));old_a=target[ankle];target[ankle]=0
   total=target.sum()
   if total>1e-8:target*=((1-a)/total)
   else:target[tibia]=1-a
   target[ankle]=a
  after[i]=row*(1-factor)+target*factor
 for i in seams[side]:after[i]=0;after[i,gi[side+'_leg_ankle']]=1
ids=np.where(np.max(abs(after-before),axis=1)>1e-8)[0]
for i in ids:
 row=after[i];keep=np.argsort(row)[-4:];new=np.zeros(len(names));new[keep]=row[keep];new/=new.sum();after[i]=new
np.savez_compressed(P/'calf_weights.npz',ids=ids,weights=after[ids],group_names=np.array(names),bone_names=np.array(list(bone_deltas)),bone_deltas=np.array([list(d) for d in bone_deltas.values()]),bone_heads=np.array([list(bone_rest[n][0]+d) for n,d in bone_deltas.items()]),bone_tails=np.array([list(bone_rest[n][1]+d) for n,d in bone_deltas.items()]))
def set_bones(after):
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.mode_set(mode='EDIT')
 for n,d in bone_deltas.items():
  b=r.data.edit_bones[n];b.head=bone_rest[n][0]+(d if after else Vector());b.tail=bone_rest[n][1]+(d if after else Vector())
 bpy.ops.object.mode_set(mode='OBJECT')
def apply(weights):
 for idx in ids:
  idx=int(idx);v=o.data.vertices[idx]
  for g in list(v.groups):o.vertex_groups[g.group].remove([idx])
  for j in np.where(weights[idx]>1e-8)[0]:o.vertex_groups[int(j)].add([idx],float(weights[idx,j]),'REPLACE')
 o.data.update()
apply(after);set_bones(True)
for tr in r.animation_data.nla_tracks:tr.mute=True
r.data.pose_position='POSE';r.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));s.frame_set(1)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'calf_candidate.blend'),compress=True)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=900;s.render.resolution_y=1000;s.render.resolution_percentage=100
report={'mesh_coordinates_unchanged':bool(np.array_equal(rest,np.array([v.co[:] for v in o.data.vertices]))),'modified_weight_vertices':len(ids),'source_ankle_full_weight_boundary_z':cuts,'shoe_seam_vertices':{k:len(v) for k,v in seams.items()},'policy':'Consolidate calf tibia twist helpers into anatomical tibia; anatomical ankle pivot at strap connection; smooth ankle transition to sourceZ .300; exact source shoe seam ankle1. Existing knee blend retained above sourceZ .345-.385.','bone_translations':{n:list(d) for n,d in bone_deltas.items()},'actions_changed':False,'measurements':{}}
edges=np.array([e.vertices[:] for e in o.data.edges]);mask=(q[edges[:,0],2]>.215)&(q[edges[:,0],2]<.345)&(q[edges[:,1],2]>.215)&(q[edges[:,1],2]<.345);ed=edges[mask];base_lengths=np.linalg.norm(rest[ed[:,0]]-rest[ed[:,1]],axis=1)
for variant,weights in [('before',before),('after',after)]:
 apply(weights);set_bones(variant=='after')
 for phase in ['Rest','Idle','Walk','Run']:
  if phase=='Rest':r.animation_data.action=None;r.data.pose_position='REST'
  else:
   r.data.pose_position='POSE';a=next(a for a in bpy.data.actions if a.name.startswith(phase));r.animation_data.action=a;s.frame_set(round(a.frame_range[1]*.35))
  bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pts=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();rat=np.linalg.norm(pts[ed[:,0]]-pts[ed[:,1]],axis=1)/base_lengths
  report['measurements'][variant+'_'+phase]={'calf_edge_length_ratio_p01_p99':np.percentile(rat,[1,99]).tolist(),'calf_edge_ratio_max':float(rat.max())}
  for label,offset in [('front',(0,-3,.02)),('side',(3,0,.02))]:
   target=Vector((0,0,.37));c=s.camera;c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=.98;s.render.filepath=str(P/(variant+'_'+phase+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
(P/'calf_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
