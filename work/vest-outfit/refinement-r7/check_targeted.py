"""Only the reported hand clearance and Run neck posture, no broad regression suite."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'vest_xiaqing_r7.blend'));r=bpy.data.objects['Xiaqing_Native_Rig'];o=bpy.data.objects['Vest_Body'];s=bpy.context.scene;r.data.pose_position='POSE'
for t in r.animation_data.nla_tracks:t.mute=True
src=np.load(P.parent/'production_history/refinement-r4/source_vertices.npz')['v'];q=src[np.array([a.value for a in o.data.attributes['r2_vertex_id'].data])]
thigh=np.where((q[:,2]>.34)&(q[:,2]<.555)&(abs(q[:,0])<.15))[0];hands={side:np.where((q[:,0]*sg>.175)&(q[:,2]>.535)&(q[:,2]<.645))[0] for side,sg in [('l',1),('r',-1)]}
def faces(ii):
 m={int(i):j for j,i in enumerate(ii)};return [[m[i] for i in p.vertices] for p in o.data.polygons if all(i in m for i in p.vertices)]
tf=faces(thigh);hf={k:faces(v) for k,v in hands.items()};out={'Idle':[],'Run':[]}
for label,fractions in [('Idle',[0,.25,.35,.70,.9]),('Run',[0,.35,.7])]:
 a=next(a for a in bpy.data.actions if a.name.startswith(label));r.animation_data.action=a
 for frac in fractions:
  f=float(a.frame_range[0]+frac*(a.frame_range[1]-a.frame_range[0]));s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
  if label=='Idle':
   ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3);ev.to_mesh_clear();tree=BVHTree.FromPolygons([Vector(p) for p in v[thigh]],tf,all_triangles=False);row={'fraction':frac,'hands':{}}
   for side,ii in hands.items():
    ht=BVHTree.FromPolygons([Vector(p) for p in v[ii]],hf[side],all_triangles=False);intersections=len(tree.overlap(ht));distance=min(tree.find_nearest(Vector(p))[3] for p in v[ii]);row['hands'][side]={'triangle_intersections':intersections,'min_vertex_clearance_m':distance};assert intersections==0 and distance>.009,'Idle hand clearance insufficient'
  else:
   sp=r.pose.bones['spine_2'];pr=sp.matrix.to_3x3()@sp.bone.matrix_local.to_3x3().inverted();side=pr@Vector((1,0,0));side.z=0;side.normalize();front=side.cross(Vector((0,0,1)));vec=r.pose.bones['head'].head-r.pose.bones['neck_0'].head;row={'fraction':frac,'neck_forward_degrees':math.degrees(math.atan2(vec.dot(front),vec.z))}
  out[label].append(row)
(P/'targeted_checks.json').write_text(json.dumps(out,indent=2));print('TARGETED_CHECKS_PASS',json.dumps(out))
