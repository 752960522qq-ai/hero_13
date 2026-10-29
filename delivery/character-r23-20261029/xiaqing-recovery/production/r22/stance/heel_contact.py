import bpy,json,math,struct,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;AS=(P.parents[2]/'dist/assets') if (P.parents[2]/'dist/assets').exists() else Path('/workspace/recovered-xiaqing-site/dist/assets');C=Matrix.Rotation(-math.pi/2,4,'X')
exec((P/'fix_stance.py').read_text().split('report={}')[0])
from mathutils import Matrix,Vector,Quaternion
C=Matrix.Rotation(-math.pi/2,4,'X')
def global_mats(j):
 ns=j['nodes'];parents={c:i for i,n in enumerate(ns)for c in n.get('children',[])};cache={}
 def g(i):
  if i in cache:return cache[i]
  n=ns[i];r=n.get('rotation',[0,0,0,1]);local=Matrix(np.array(n['matrix']).reshape(4,4).T.tolist())if'matrix'in n else Matrix.LocRotScale(Vector(n.get('translation',[0,0,0])),Quaternion((r[3],*r[:3])),Vector(n.get('scale',[1,1,1])));cache[i]=(g(parents[i])if i in parents else Matrix.Identity(4))@local;return cache[i]
 for i in range(len(ns)):g(i)
 return cache,parents
report={}
for outfit in ['school_uniform','floral_dress']:
 file=AS/(outfit+'_xiaqing.glb');baseline=P/(outfit+'_stance_baseline.glb');baseline.write_bytes(file.read_bytes());j,b=read(baseline);G,parents=global_mats(j);byname={n.get('name'):i for i,n in enumerate(j['nodes'])}
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(baseline));t=next(o for o in bpy.data.objects if o.type=='ARMATURE');scene=bpy.context.scene
 for tr in t.animation_data.nla_tracks:tr.mute=True
 a=next(a for a in bpy.data.actions if a.name=='Aim_'+t.name);t.animation_data.action=a;scene.frame_set(int(sum(a.frame_range)/2));bpy.context.view_layer.update();rest={n:t.matrix_world@bone.matrix_local for n,bone in t.data.bones.items()}
 def points(side):
  pts=[]
  for ob in scene.objects:
   if ob.type!='MESH'or not any(m.type=='ARMATURE'for m in ob.modifiers):continue
   eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh();pts.extend(tuple(eo.matrix_world@v.co)for v in me.vertices);eo.to_mesh_clear()
  pts=np.array(pts);pts=pts[pts[:,2]<.3];a=(t.matrix_world@t.pose.bones[side+'_leg_ankle'].matrix).translation;o=(t.matrix_world@t.pose.bones[('r'if side=='l'else'l')+'_leg_ankle'].matrix).translation;d=(pts[:,0]-a.x)**2+(pts[:,1]-a.y)**2;d2=(pts[:,0]-o.x)**2+(pts[:,1]-o.y)**2;return pts[(d<d2)&(d<.1)]
 def world(pb):return t.matrix_world@pb.matrix
 def setrot(pb,rot):
  p=world(pb).translation;pb.matrix=t.matrix_world.inverted()@Matrix.LocRotScale(p,rot,Vector((1,1,1)));bpy.context.view_layer.update()
 def solve(side,target,footrot):
  H,E,W=[t.pose.bones[side+x]for x in ['_leg_femur','_leg_tibia','_leg_ankle']];h,e,w=[world(x).translation for x in [H,E,W]];upper=(e-h).length;lower=(w-e).length;delta=target-h;d=delta.length;axis=delta.normalized();reach=min(d,upper+lower-.0001);along=(upper*upper-lower*lower+reach*reach)/(2*reach);height=math.sqrt(max(0,upper*upper-along*along));pole=e-h-axis*(e-h).dot(axis);pole.normalize();newE=h+axis*along+pole*height;newW=h+axis*reach
  setrot(H,(e-h).normalized().rotation_difference((newE-h).normalized())@world(H).to_quaternion());e2,w2=[world(x).translation for x in[E,W]];setrot(E,(w2-e2).normalized().rotation_difference((newW-e2).normalized())@world(E).to_quaternion());setrot(W,footrot)
 report[outfit]={}
 for side in ['l','r']:
  passes=[]
  for iteration in range(3):
   W=t.pose.bones[side+'_leg_ankle'];pts=points(side);lo,hi=np.quantile(pts[:,1],[.25,.75]);toes=pts[pts[:,1]<=lo];heels=pts[pts[:,1]>=hi];toe=Vector(toes[toes[:,2].argmin()]);heel=Vector(heels[heels[:,2].argmin()]);dy=heel.y-toe.y;dz=heel.z-toe.z;angle=math.atan2(-dz,dy);angle=max(-.35,min(.35,angle));old=world(W);rot=Quaternion((1,0,0),angle)@old.to_quaternion();setrot(W,rot)
   low=points(side)[:,2].min();target=world(W).translation+Vector((0,0,-float(low)));solve(side,target,rot)
   # All toe/foot children inherit the same rigid ankle swing; no local toe scaling or bending.
   after=points(side);lo,hi=np.quantile(after[:,1],[.25,.75]);passes.append({'ankle_pitch_deg':math.degrees(angle),'toe_bottom':float(after[after[:,1]<=lo,2].min()),'heel_bottom':float(after[after[:,1]>=hi,2].min()),'ankle_target_vertical_shift':-float(low)})
  report[outfit][side]={'correction_passes':passes}
 names=[n for n in rest if 'leg_'in n];current={byname[n]:C@(world(t.pose.bones[n])@rest[n].inverted())@C.inverted()@G[byname[n]]for n in rest if n in byname};locals={}
 for n in names:
  i=byname[n];par=parents.get(i);loc,rot,scale=(current.get(par,G.get(par,Matrix.Identity(4))).inverted()@current[i]).decompose();locals[n]={'translation':list(loc),'rotation':[rot.x,rot.y,rot.z,rot.w],'scale':list(scale)}
 for a in j['animations']:
  if a['name']not in STATIC:continue
  duration=max(float(accessor(j,b,s['input'])[-1])for s in a['samplers']);inp=append(j,b,[0,duration],'SCALAR');a['channels']=[c for c in a['channels']if j['nodes'][c['target']['node']].get('name')not in names]
  for n,row in locals.items():
   for path,arr in row.items():
    out=append(j,b,[arr,arr],'VEC4'if path=='rotation'else'VEC3');si=len(a['samplers']);a['samplers'].append({'input':inp,'output':out,'interpolation':'LINEAR'});a['channels'].append({'sampler':si,'target':{'node':byname[n],'path':path}})
 write(file,j,b);print('CORRECTED',outfit,report[outfit],flush=True)
(P/'heel_contact_report.json').write_text(json.dumps(report,indent=2))
