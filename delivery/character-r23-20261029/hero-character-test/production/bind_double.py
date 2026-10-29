import bpy,json,math,re,os,shutil,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
P=Path(__file__).resolve().parent;AS=P.parent/'dist/assets';SRC=P/'superman_anim/superman_clean.blend';TARGET=str(P/'inputs/double stars have head.glb')
bpy.ops.wm.open_mainfile(filepath=str(SRC));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');source=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE'for m in o.modifiers)]
for o in source:
 for mo in o.modifiers:
  if mo.type=='ARMATURE':mo.show_viewport=False;mo.show_render=False
rig.animation_data_clear();rig.data.pose_position='REST';bpy.context.view_layer.update()
old={b.name:b.matrix_local.copy()for b in rig.data.bones};heads={b.name:b.head_local.copy()for b in rig.data.bones};tails={b.name:b.tail_local.copy()for b in rig.data.bones}
find=lambda pre:next(n for n in old if re.sub(r'_\d+$','',n)==pre)
anchors={}
for side,sgn in [('l',1),('r',-1)]:
 for pre,point in [('upperarm',(sgn*.21,.04,1.345)),('lowerarm',(sgn*.39,.025,1.10)),('hand',(sgn*.505,-.05,.965)),('thigh',(sgn*.09,0,.93)),('calf',(sgn*.147,.02,.535)),('foot',(sgn*.19,.03,.12)),('ball',(sgn*.197,-.10,.04))]:anchors[find(pre+'_'+side)]=Vector(point)

def along(p,a,b,ta,tb):
 axis=b-a;t=(p-a).dot(axis)/axis.length_squared;return ta+(tb-ta)*t+(p-(a+axis*t))
def warp(n,p):
 if n in anchors and (p-heads[n]).length<1e-7:return anchors[n].copy()
 stem=re.sub(r'_\d+$','',n)
 side='l'if '_l'in stem else 'r'if '_r'in stem else None
 if not side:return p.copy()
 H,E,W=[find(a+'_'+side)for a in ['upperarm','lowerarm','hand']]
 if any(a in stem for a in ['metacarpal','index_','middle_','ring_','pinky_','thumb_','hand_']):
  delta=p-heads[W];return anchors[W]+delta*.9
 if 'lowerarm'in stem or 'elbow'in stem:return along(p,heads[E],heads[W],anchors[E],anchors[W])
 if 'upperarm'in stem:return along(p,heads[H],heads[E],anchors[H],anchors[E])
 if 'clavicle'in stem:return along(p,heads[n],heads[H],heads[n],anchors[H])
 T,K,F,B=[find(a+'_'+side)for a in ['thigh','calf','foot','ball']]
 if 'thigh'in stem:return along(p,heads[T],heads[K],anchors[T],anchors[K])
 if 'calf'in stem:return along(p,heads[K],heads[F],anchors[K],anchors[F])
 if 'foot'in stem or 'ball'in stem:return along(p,heads[F],heads[B],anchors[F],anchors[B])
 return p.copy()
# Warp the transferred bone rest frame to the target proportions without moving target vertices.
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in rig.data.edit_bones:
 b.head=warp(b.name,heads[b.name]);b.tail=warp(b.name,tails[b.name]);
 if (b.tail-b.head).length<.001:b.tail=b.head+Vector((0,0,.005))
bpy.ops.object.mode_set(mode='OBJECT');rig.data.pose_position='POSE';rig.name='DoubleStarsRig';new={b.name:b.matrix_local.copy()for b in rig.data.bones};deforms={n:new[n]@old[n].inverted()for n in old}
# Weight source vertices are warped with the same copied skeleton. Search is restricted
# by anatomy so the hand cannot accidentally inherit torso/leg weights.
records=[];regions={x:[]for x in ['torso','head','arm_l','arm_r','hand_l','hand_r','leg_l','leg_r']}
for o in source:
 names={g.index:g.name for g in o.vertex_groups}
 for vert in o.data.vertices:
  weights=[(names[g.group],g.weight)for g in vert.groups if g.weight>1e-6 and names[g.group]in deforms]
  if not weights:continue
  pos=o.matrix_world@vert.co;warped=sum((deforms[n]@pos*w for n,w in weights),Vector())/sum(w for n,w in weights)
  dominant=max(weights,key=lambda x:x[1])[0];stem=re.sub(r'_\d+$','',dominant);side='l'if '_l'in stem else'r'if '_r'in stem else None
  region='hand_'+side if side and any(t in stem for t in ['hand','metacarpal','index','middle','pinky','ring','thumb'])else'arm_'+side if side and any(t in stem for t in ['arm','elbow','clavicle'])else'leg_'+side if side and any(t in stem for t in ['thigh','calf','foot','ball'])else'head'if any(t in stem for t in ['head','neck','eye','lip','brow','face','nose','cheek','jaw'])else'torso'
  idx=len(records);records.append((warped,weights));regions[region].append(idx)
# Limb pools include joint overlap, but never the opposite limb.
regions['arm_l']+=regions['hand_l'];regions['arm_r']+=regions['hand_r']
regions['all']=list(range(len(records)));trees={}
for key,indices in regions.items():
 tree=KDTree(len(indices))
 for i in indices:tree.insert(records[i][0],i)
 tree.balance();trees[key]=tree
oldobjs=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=TARGET);target=[o for o in set(bpy.data.objects)-oldobjs if o.type=='MESH'];scale=1.675/0.9783934354782104
stats={};allgroups=list(old);headbone=find('head');neckbone=find('neck_02')
for o in target:
 mw=o.matrix_world.copy();o.parent=None;o.matrix_world.identity()
 for v in o.data.vertices:v.co=(mw@v.co)*scale
 for g in list(o.vertex_groups):o.vertex_groups.remove(g)
 groups={n:o.vertex_groups.new(name=n)for n in allgroups};unweighted=0;max_inf=0
 for v in o.data.vertices:
  p=v.co;sgn='l'if p.x>=0 else'r';x=abs(p.x)
  if p.z>1.49:
   groups[headbone].add([v.index],1,'REPLACE');continue
  if p.z>1.40 and x<.13:
   a=max(0,min(1,(p.z-1.40)/.09));groups[headbone].add([v.index],a,'REPLACE');groups[neckbone].add([v.index],1-a,'REPLACE');continue
  key='hand_'+sgn if x>.445 and p.z<1.015 else'arm_'+sgn if x>.235 and p.z>.90 else'leg_'+sgn if p.z<.89 else'torso'
  nearest=trees[key].find_n(p,4);acc={}
  for co,idx,d in nearest:
   fac=1/max(.003,d)**2
   for n,w in records[idx][1]:acc[n]=acc.get(n,0)+w*fac
  acc=sorted(acc.items(),key=lambda a:-a[1])[:4];total=sum(w for n,w in acc)
  if total<=0:unweighted+=1;acc=[(find('pelvis'),1)];total=1
  for n,w in acc:groups[n].add([v.index],w/total,'REPLACE')
  max_inf=max(max_inf,len(acc))
 o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted();mod=o.modifiers.new('Transferred Superman skin','ARMATURE');mod.object=rig
 stats[o.name]={'vertices':len(o.data.vertices),'unweighted':unweighted,'max_influences':max_inf}
for o in source:bpy.data.objects.remove(o,do_unlink=True)
for o in list(bpy.data.objects):
 if o.type not in ['ARMATURE','MESH']:bpy.data.objects.remove(o,do_unlink=True)
rig.data.pose_position='POSE';bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'double_stars_bound.blend'),compress=True)
(P/'transfer_report.json').write_text(json.dumps({'source_skeleton':'superman UE skeleton','bone_count':len(rig.data.bones),'mesh_count':len(target),'height_m':1.675,'uniform_source_asset_scale':scale,'source_weights':'4-neighbor anatomically restricted surface interpolation after skeleton rest warp','target_mesh_edited':False,'stats':stats,'target_joint_anchors':{n:list(v)for n,v in anchors.items()}},indent=2))
print('DOUBLE_BOUND',len(target),sum(s['vertices']for s in stats.values()),flush=True)
