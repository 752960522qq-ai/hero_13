"""Blender R2: reduce lower-limb/foot swelling, preserve integrated sandals, repair two residual skin gradients."""
import bpy,numpy as np,json
from pathlib import Path
from scipy.interpolate import PchipInterpolator
from scipy.sparse import csr_matrix
P=Path(__file__).resolve().parent;BASE=P.parent;bpy.ops.wm.open_mainfile(filepath=str(BASE/'refinement-r1/vest_xiaqing_refined.blend'))
o=bpy.data.objects['Vest_Body'];rig=bpy.data.objects['Xiaqing_Native_Rig'];rig.animation_data.action=None;rig.data.pose_position='REST'
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis.identity()
heads={b.name:np.array(rig.matrix_world@b.head_local) for b in rig.data.bones};pos=np.array([v.co[:] for v in o.data.vertices]);before=pos.copy();N=len(pos);G=len(o.vertex_groups);gi={g.name:g.index for g in o.vertex_groups};W=np.zeros((N,G))
for v in o.data.vertices:
 for g in v.groups:W[v.index,g.group]=g.weight
originalW=W.copy();labels=np.array([x.value for x in o.data.attributes['source_finger_id'].data]);edges=np.array([e.vertices[:] for e in o.data.edges])
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
# Anatomical taper follows tibia/femur centerlines and fades into the existing shorts.
zs=[.12,.17,.27,.40,.535,.65,.75,.84,.89]
xs=PchipInterpolator(zs,[.87,.85,.88,.92,.87,.88,.90,.995,1])
ys=PchipInterpolator(zs,[.87,.87,.90,.965,.89,.91,.92,.997,1])
# Monotone foot-length warp keeps both ankle and ball joint Y anchors fixed.
for side,sign in [('l',1),('r',-1)]:
 hip=heads[side+'_leg_femur'];knee=heads[side+'_leg_tibia'];ankle=heads[side+'_leg_ankle'];ball=heads[side+'_leg_ball']
 foot_y=PchipInterpolator([-.25,-.19,float(ball[1]),float(ankle[1]),.15],[-.215,-.173,float(ball[1]),float(ankle[1]),.086],extrapolate=True)
 ids=np.where((pos[:,0]*sign>.015)&(pos[:,2]<.89))[0]
 for i in ids:
  p=before[i];z=p[2];zz=np.clip(z,.12,.89);center=np.array([np.interp(z,[ankle[2],knee[2],hip[2]],[ankle[a],knee[a],hip[a]]) for a in range(2)])
  leg=p.copy();leg[0]=center[0]+(p[0]-center[0])*float(xs(zz));leg[1]=center[1]+(p[1]-center[1])*float(ys(zz))
  foot=p.copy();foot[0]=ankle[0]+(p[0]-ankle[0])*.87;foot[1]=float(foot_y(p[1]))
  # Lower the instep dome gently, retaining the vertical heel and platform thickness.
  instep=smooth((z-.030)/.045)*smooth((.160-z)/.040)*smooth((.050-p[1])/.075)
  foot[2]-=.007*instep
  f=1-smooth((z-.16)/.13);pos[i]=leg*(1-f)+foot*f
# Diffuse only the sculpt displacement, retaining original surface detail and UVs.
rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]];A=csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(N,N));A=A.multiply(1/np.maximum(np.array(A.sum(1)),1)).tocsr();D=pos-before
for _ in range(10):D=.65*D+.35*(A@D)
pos=before+D
# Fade wrist contamination anatomically across labelled fingers AND legacy web labels.
# Topological metadata extends down some digits; it must not define a skinning cliff.
from scipy.spatial import cKDTree
finger_report={};digit_names=['thumb','index','middle','ring','little'];fadefield=np.zeros(N);assignment={};own_by_side={};fallbacks=0
for side in ['l','r']:
 own_by_side[side]=[g.index for g in o.vertex_groups if g.name.startswith(side+'_hand_')];wrist=gi[side+'_arm_wrist'];chains={};donors={}
 for finger in digit_names:
  start=1 if finger in ['ring','little'] else 0;last=3 if start else 2;names=[f'{side}_hand_{finger}_{j}' for j in range(start,last+1)];chain=np.array([heads[n] for n in names]);chain=np.vstack([chain,chain[-1]+(chain[-1]-chain[-2])*.8]);lengths=np.linalg.norm(np.diff(chain,axis=0),axis=1);cum=np.r_[0,np.cumsum(lengths)];ids=[g.index for g in o.vertex_groups if g.name.startswith(f'{side}_hand_{finger}_')];chains[finger]=(chain,lengths,cum,ids)
  candidate=np.where(W[:,ids].sum(1)>.05)[0];donors[finger]=(candidate,cKDTree(before[candidate]))
 for i in np.where(W[:,wrist]>1e-8)[0]:
  p=before[i];data=[]
  for finger,(chain,lengths,cum,ids) in chains.items():
   candidates=[]
   for j,(aa,bb) in enumerate(zip(chain[:-1],chain[1:])):
    t=np.clip((p-aa)@(bb-aa)/((bb-aa)@(bb-aa)),0,1);candidates.append((np.linalg.norm(p-aa-t*(bb-aa)),cum[j]+t*lengths[j]))
   dist,along=min(candidates,key=lambda it:it[0]);fade=float(smooth((along/lengths[0]-.70)/.80));mass=float(W[i,ids].sum());data.append((dist,fade,mass,finger,ids))
  own_total=sum(item[2] for item in data)
  if own_total>1e-8:
   fadefield[i]=sum(item[1]*item[2] for item in data)/own_total;assignment[i]=(side,None)
  else:
   dist,fade,_,finger,ids=min(data,key=lambda it:it[0]);fade*=smooth((.023-dist)/.012)
   if fade>1e-5:fadefield[i]=fade;assignment[i]=(side,finger);fallbacks+=1
# A shared smooth scalar field prevents ranking/label seams at finger roots.
for _ in range(3):fadefield=.70*fadefield+.30*(A@fadefield)
for i,(side,fallback) in assignment.items():
 wrist=gi[side+'_arm_wrist'];mass=W[i,wrist]*fadefield[i];own=own_by_side[side]
 if mass<1e-8:continue
 if W[i,own].sum()>1e-8:W[i,own]+=mass*W[i,own]/W[i,own].sum()
 else:
  ids=chains[fallback][3] if side=='r' else [g.index for g in o.vertex_groups if g.name.startswith(f'l_hand_{fallback}_')]
  # Interpolate the existing local digit ratios for pure-wrist islands.
  candidate=np.where(originalW[:,ids].sum(1)>.05)[0];tree=cKDTree(before[candidate]);ds,ii=tree.query(before[i],k=min(4,len(candidate)));ratios=np.zeros(len(ids))
  for d,j in zip(np.atleast_1d(ds),np.atleast_1d(ii)):
   row=originalW[candidate[int(j)],ids];ratios+=row/max(row.sum(),1e-12)/(float(d)+.001)**2
  ratios/=max(ratios.sum(),1e-12);W[i,ids]+=mass*ratios
 W[i,wrist]-=mass;finger_report[side]=finger_report.get(side,0)+1
finger_report['pure_wrist_islands_smoothed']=fallbacks
# Repair the lateral torso transition at the old shoulder palette boundary.
torso_count=0
for i,p in enumerate(before):
 if not (1.14<p[2]<1.28 and .060<abs(p[0])<.145):continue
 arm=sum(W[i,g.index] for g in o.vertex_groups if any(k in g.name.lower() for k in ['arm_','delt','clavicle','pec','trap','scap']))
 blend=smooth((abs(p[0])-.060)/.025)*smooth((.145-abs(p[0]))/.025)*smooth((p[2]-1.14)/.025)*smooth((1.28-p[2])/.025)*smooth((.20-arm)/.10)
 family=[g.index for g in o.vertex_groups if g.name in ['spine_1','spine_2'] or any(k in g.name.lower() for k in ['lata','serratus'])];mass=sum(W[i,j] for j in family)
 if mass<.2 or blend<1e-8:continue
 target=np.zeros(G);t=smooth((p[2]-1.17)/.07);target[gi['spine_1']]=mass*(1-t);target[gi['spine_2']]=mass*t
 W[i,family]*=1-blend;W[i]+=blend*target;torso_count+=1
# Deterministic four-influence weights; finger group ownership is preserved.
for v,p,row in zip(o.data.vertices,pos,W):
 v.co=p
 if np.max(np.abs(row-originalW[v.index]))>1e-10:
  for group in list(v.groups):o.vertex_groups[group.group].remove([v.index])
  ids=sorted(np.where(row>1e-8)[0],key=lambda j:(-row[j],o.vertex_groups[int(j)].name))[:4];total=sum(row[j] for j in ids)
  for j in ids:o.vertex_groups[int(j)].add([v.index],float(row[j]/total),'REPLACE')
# Recompute changed lower-body surface normals; preserve exact upper-body seam normals.
old_normals=[v.vector[:] for v in o.data.corner_normals];bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
if o.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
o.data.update();normals=[v.vector[:] for v in o.data.corner_normals]
for loop in o.data.loops:
 if before[loop.vertex_index,2]>.92:normals[loop.index]=old_normals[loop.index]
o.data.normals_split_custom_set(normals)
def dimensions(p):
 out={}
 for side,sign in [('l',1),('r',-1)]:
  q=p[(p[:,0]*sign>.02)&(p[:,2]<.09)];out[side]={'foot_length_mm':float(np.ptp(q[:,1])*1000),'foot_width_mm':float(np.ptp(q[:,0])*1000),'sole_min_z_mm':float(q[:,2].min()*1000)}
 return out
report={'before':dimensions(before),'after':dimensions(pos),'modified_vertices':int(sum(np.linalg.norm(D,axis=1)>1e-6)),'max_displacement_mm':float(np.max(np.linalg.norm(D,axis=1))*1000),'finger_wrist_weights_corrected':finger_report,'torso_gradient_vertices':torso_count,'geometry_policy':'shared foot/shoe warp, fixed ankle and ball Y anchors, sole/heel thickness retained, smooth displacement field'}
rig.data.pose_position='POSE';rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('Idle'));bpy.context.scene.frame_set(1);o['refinement_r2']='Lower-body taper, proportional foot+shoe fit, distal finger wrist fade, lateral torso gradient';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'vest_xiaqing_r2.blend'),compress=True);(P/'refinement_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
