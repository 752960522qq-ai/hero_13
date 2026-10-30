"""Inventory unused source city geometry; preserve source transforms and materials."""
from pathlib import Path
import sys,json,math,re,collections,hashlib
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'))
import bpy,numpy as np
from mathutils import Vector
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sources=[('S05',R.parent/'reference_models/city (1)(1).glb'),('S07',R.parent/'source_models_v21/city.glb'),('S08',R.parent/'upload/city_street(1).glb'),('S09',R.parent/'source_models_v21/london_city.glb')]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for sid,path in sources:
 if args and sid not in args:continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
 records=[];components=[]
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH':continue
  n=len(o.data.vertices);xyz=np.empty(n*3,dtype=np.float64);o.data.vertices.foreach_get('co',xyz);xyz=xyz.reshape(-1,3);M=np.array(o.matrix_world);xyz=xyz@M[:3,:3].T+M[:3,3]
  lo=xyz.min(0);hi=xyz.max(0);parent=o.parent.name if o.parent else ''
  rec=dict(name=o.name,parent=parent,vertices=n,polygons=len(o.data.polygons),triangles=sum(len(p.vertices)-2 for p in o.data.polygons),bounds=[lo.tolist(),hi.tolist()],size=(hi-lo).tolist(),materials=[m.name if m else None for m in o.data.materials])
  records.append(rec)
  # Weld UV seam vertices for connectivity analysis only. Source data is unchanged.
  if sid=='S08':continue
  ed=np.empty(len(o.data.edges)*2,dtype=np.int32);o.data.edges.foreach_get('vertices',ed);ed=ed.reshape(-1,2)
  _,ind=np.unique(np.round(xyz,6),axis=0,return_inverse=True);nn=int(ind.max())+1
  pair=ind[ed];g=coo_matrix((np.ones(len(pair)),(pair[:,0],pair[:,1])),shape=(nn,nn));count,lab=connected_components(g,directed=False);vlab=lab[ind]
  groups=collections.defaultdict(list)
  for f in o.data.polygons:groups[int(vlab[f.vertices[0]])].append(f.index)
  for ci,faces in groups.items():
   if len(faces)<4:continue
   verts=np.unique(np.concatenate([np.array(o.data.polygons[fi].vertices) for fi in faces]));pts=xyz[verts];bl=pts.min(0);bh=pts.max(0);sz=bh-bl
   if sz[2]<.07 or max(sz[:2])<.08:continue
   components.append(dict(object=o.name,parent=parent,component=ci,faces=len(faces),triangles=sum(len(o.data.polygons[fi].vertices)-2 for fi in faces),bounds=[bl.tolist(),bh.tolist()],size=sz.tolist(),face_ids=faces))
 images=[]
 for im in bpy.data.images:
  if im.name in ['Render Result','Viewer Node']:continue
  images.append(dict(name=im.name,size=list(im.size),channels=im.channels))
 data=dict(source_id=sid,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),objects=records,components=components,images=images)
 (R/'audit'/f'{sid}_geometry.json').write_text(json.dumps(data,ensure_ascii=False))
 print('INVENTORY',sid,len(records),len(components),flush=True)
 sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=10;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=8;sc.render.resolution_x=1500;sc.render.resolution_y=1300;sc.render.resolution_percentage=100;sc.render.use_simplify=True;sc.cycles.texture_limit_render='1024';sc.world=bpy.data.worlds.new('Day');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.73,.81,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.8
 ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.8;ld.angle=.15;ob=bpy.data.objects.new('Sun',ld);sc.collection.objects.link(ob);ob.rotation_euler=(.5,-.35,-.5)
 lo=np.array([r['bounds'][0] for r in records]).min(0);hi=np.array([r['bounds'][1] for r in records]).max(0);c=Vector((lo+hi)/2);s=float(max(hi-lo))
 cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);sc.collection.objects.link(cam);cd.type='ORTHO';cd.ortho_scale=s*1.15;cd.clip_end=s*20;sc.camera=cam
 cam.location=c+Vector((.7,-1.1,1.0))*s;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(R/'previews'/f'{sid}_source.png');bpy.ops.render.render(write_still=True)
 cam.location=(c.x,c.y,c.z+s*3);cam.rotation_euler=(0,0,0);cd.ortho_scale=s*1.07;sc.render.filepath=str(R/'previews'/f'{sid}_top.png');bpy.ops.render.render(write_still=True)
 (R/'audit'/f'{sid}_camera.json').write_text(json.dumps(dict(center=list(c),scale=cd.ortho_scale,resolution=[1500,1300])))
 print('AUDITED',sid,flush=True)
