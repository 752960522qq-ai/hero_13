"""Local R3 shoulder correction. Preserve rig and motion; emit an indexed merge patch."""
import bpy, json, numpy as np
from pathlib import Path
from scipy.sparse import csr_matrix
from mathutils import Vector

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'refinement-r2/vest_xiaqing_r2.blend'))
o=bpy.data.objects['Vest_Body']; rig=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
rig.animation_data.action=None;rig.data.pose_position='REST'
for t in rig.animation_data.nla_tracks:t.mute=True
for b in rig.pose.bones:b.matrix_basis.identity()
pos=np.array([v.co[:] for v in o.data.vertices]);base=pos.copy()
names=[g.name for g in o.vertex_groups];gi={n:i for i,n in enumerate(names)}
W=np.zeros((len(pos),len(names)))
for v in o.data.vertices:
 for g in v.groups:W[v.index,g.group]=g.weight
originalW=W.copy()
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
x=np.abs(pos[:,0]);z=pos[:,2]
# Drop the cap and lateral trapezius into a relaxed shoulder line.
# The source neck and central chest are excluded from this patch.
mask=smooth((x-.058)/.045)*smooth((.305-x)/.105)*smooth((z-1.225)/.110)*smooth((1.49-z)/.045)
D=np.zeros_like(pos);D[:,2]=-.030*mask
edges=np.array([e.vertices[:] for e in o.data.edges]);rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]]
A=csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(pos),len(pos)));A=A.multiply(1/np.maximum(np.asarray(A.sum(1)),1)).tocsr()
for _ in range(6):D=.7*D+.3*(A@D)
# Do not push neck vertices down when diffusion reaches their boundary.
D[x<.058]=0
pos+=D
weight_mask=smooth((x-.07)/.04)*smooth((.31-x)/.08)*smooth((z-1.23)/.085)*smooth((1.49-z)/.045)
for i in np.where(weight_mask>1e-6)[0]:
 side='l' if pos[i,0]>0 else 'r';factor=weight_mask[i];row=W[i].copy();target=np.zeros(len(names))
 for name,j in gi.items():
  value=row[j]
  if value<=1e-12:continue
  dest=name
  # Native muscle auxiliaries were driving the replacement shoulder cap upward.
  if name.startswith(side+'_delt') or name.startswith(side+'_arm_humerus'):dest=side+'_arm_humerus'
  elif name.startswith(side+'_') and any(k in name.lower() for k in ['pec','trap','scap']):dest=side+'_arm_clavicle'
  target[gi[dest]]+=value
 W[i]=row*(1-factor)+target*factor
# Smooth only the local transition field, preserving fingers and torso corrections.
for _ in range(5):W+=.30*weight_mask[:,None]*((A@W)-W)
ids=np.where((np.linalg.norm(D,axis=1)>1e-8)|(np.max(np.abs(W-originalW),axis=1)>1e-8))[0]
for i in ids:
 v=o.data.vertices[int(i)];v.co=pos[i]
 for g in list(v.groups):o.vertex_groups[g.group].remove([int(i)])
 keep=sorted(np.where(W[i]>1e-8)[0],key=lambda j:(-W[i,j],names[j]))[:4];values=W[i,keep].copy();values/=values.sum();W[i]=0
 for j,value in zip(keep,values):W[i,j]=value;o.vertex_groups[int(j)].add([int(i)],float(value),'REPLACE')
np.savez_compressed(P/'shoulder_patch.npz',ids=ids,delta=D[ids],weights=W[ids],group_names=np.array(names))
report={'affected_vertices':len(ids),'maximum_drop_mm':float(-D[:,2].min()*1000),'bone_rest_changed':False,'clips_changed':False,'policy':'3 cm smooth shoulder cap drop; deltoid/twist cap drivers consolidated into main upper-arm; neck center excluded','posed_cap':{}}
old_normals=[v.vector[:] for v in o.data.corner_normals]
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
if o.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
o.data.update();norms=[v.vector[:] for v in o.data.corner_normals]
for loop in o.data.loops:
 if mask[loop.vertex_index]<1e-6:norms[loop.index]=old_normals[loop.index]
o.data.normals_split_custom_set(norms)
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));s.frame_set(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'shoulders_rebuilt.blend'),compress=True)
# Matched front renders of the source and corrected shoulder poses.
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='TEXTURE';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False
s.render.resolution_x=1000;s.render.resolution_y=1000;s.render.resolution_percentage=100
def set_variant(after):
 for i in ids:
  v=o.data.vertices[int(i)];v.co=pos[i] if after else base[i]
  for g in list(v.groups):o.vertex_groups[g.group].remove([int(i)])
  row=W[i] if after else originalW[i]
  for j in np.where(row>1e-8)[0]:o.vertex_groups[int(j)].add([int(i)],float(row[j]),'REPLACE')
 o.data.update()
for variant in ['before','after']:
 set_variant(variant=='after')
 for phase in ['Rest','Idle','Walk','Run']:
  if phase=='Rest':rig.animation_data.action=None;rig.data.pose_position='REST'
  else:
   rig.data.pose_position='POSE';a=next(a for a in bpy.data.actions if a.name.startswith(phase));rig.animation_data.action=a;s.frame_set(round(a.frame_range[1]*.35))
  bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();q=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear()
  report['posed_cap'][variant+'_'+phase]={side:float(q[(base[:,0]*sign>.10)&(base[:,0]*sign<.22)&(base[:,2]>1.33)&(base[:,2]<1.47),2].max()) for side,sign in [('l',1),('r',-1)]}
  c=s.camera;target=Vector((0,.015,1.32));c.location=target+Vector((0,-3,.09));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=.72;s.render.filepath=str(P/(variant+'_'+phase+'_front.png'));bpy.ops.render.render(write_still=True)
(P/'shoulder_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

