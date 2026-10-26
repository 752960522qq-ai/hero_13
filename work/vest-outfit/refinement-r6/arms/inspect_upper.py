import bpy,json,numpy as np,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
P=Path(__file__).resolve().parent;R4=P.parent.parent/'refinement-r4'
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
FILE=Path(argv[0]) if argv else R4/'vest_xiaqing_r4.blend'
bpy.ops.wm.open_mainfile(filepath=str(FILE))
o=bpy.data.objects['Vest_Body'];r=bpy.data.objects['Xiaqing_Native_Rig'];s=bpy.context.scene
src=np.load(R4/'source_vertices.npz')['v'];ids=np.array([a.value for a in o.data.attributes['r2_vertex_id'].data]);q=src[ids]
names={g.index:g.name for g in o.vertex_groups};w=[{names[g.group]:g.weight for g in v.groups} for v in o.data.vertices]
for t in r.animation_data.nla_tracks:t.mute=True
regions={'waist':(q[:,2]>.61)&(q[:,2]<.65)&(abs(q[:,0])<.13),'ribs':(q[:,2]>.68)&(q[:,2]<.73)&(abs(q[:,0])<.13),'chest':(q[:,2]>.75)&(q[:,2]<.78)&(abs(q[:,0])<.10)}
thighids=np.where((q[:,2]>.34)&(q[:,2]<.555)&(abs(q[:,0])<.15))[0];thighset=set(thighids)
triangles=[tuple(p.vertices) for p in o.data.polygons if all(i in thighset for i in p.vertices)]
hand={side:np.where((q[:,0]*sign>.175)&(q[:,2]>.535)&(q[:,2]<.645))[0] for side,sign in [('l',1),('r',-1)]}
handfaces={}
for side,ii in hand.items():
 hs=set(ii);handfaces[side]=[tuple(p.vertices) for p in o.data.polygons if all(i in hs for i in p.vertices)]
report={'weights':{},'samples':{}}
for name,mask in regions.items():
 ii=np.where(mask)[0];av={n:float(np.mean([w[i].get(n,0) for i in ii])) for n in names.values()};report['weights'][name]={k:v for k,v in av.items() if v>.001}
for phase in (['Rest','Idle'] if argv else ['Rest','Idle','Walk','Run']):
 if phase=='Rest':r.data.pose_position='REST';r.animation_data.action=None;frames=[0]
 else:
  r.data.pose_position='POSE';a=next(a for a in bpy.data.actions if a.name.startswith(phase));r.animation_data.action=a;frames=[float(a.frame_range[0]+fraction*(a.frame_range[1]-a.frame_range[0])) for fraction in ([0,.35,.7] if phase=='Idle' else [.35])]
 rows=[]
 for frame in frames:
  s.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pos=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear();tree=BVHTree.FromPolygons([Vector(v) for v in pos],triangles,all_triangles=False)
  row={'frame':frame,'torso':{},'hands':{}}
  for name,mask in regions.items():
   # Measure relative to torso orientation, excluding world-space lean.
   mat=r.pose.bones['spine_1'].matrix.to_3x3()@r.data.bones['spine_1'].matrix_local.to_3x3().inverted() if phase!='Rest' else __import__('mathutils').Matrix.Identity(3)
   local=pos[mask]@np.array(mat);row['torso'][name]={'width_m':float(np.ptp(local[:,0])),'depth_m':float(np.ptp(local[:,1]))}
  for side,ii in hand.items():
   signed=[]
   for i in ii:
    co,normal,fi,distance=tree.find_nearest(Vector(pos[i]));signed.append((float((Vector(pos[i])-co).dot(normal)),distance))
   ht=BVHTree.FromPolygons([Vector(v) for v in pos],handfaces[side],all_triangles=False)
   intersections=tree.overlap(ht)
   near=[x for x,d in signed if d<.06];row['hands'][side]={'vertices':len(ii),'near_penetrating':sum(x<-.001 for x in near),'deepest_m':min(near,default=0),'closest_distance_m':min(d for x,d in signed),'hand_thigh_triangle_intersections':len(intersections),'wrist':list(r.pose.bones[side+'_arm_wrist'].head)}
  rows.append(row)
 report['samples'][phase]=rows
(P/('upper_after.json' if argv else 'upper_diagnosis.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
