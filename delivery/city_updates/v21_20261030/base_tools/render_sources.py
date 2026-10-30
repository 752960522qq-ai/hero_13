import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]; base=R.parent
which=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
sources=json.load(open(R/'audit/sources.json'))
for src in sources:
 if which and src['id'] not in which:continue
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(base/'upload'/src['file']))
 bpy.context.view_layer.update()
 objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 pts=[o.matrix_world@Vector(v) for o in objs for v in o.bound_box];lo=Vector(tuple(min(p[k] for p in pts) for k in range(3)));hi=Vector(tuple(max(p[k] for p in pts) for k in range(3)));center=(hi+lo)/2;size=max(hi-lo)
 sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=8
 sc.render.use_simplify=True;sc.cycles.texture_limit_render='2048';sc.render.resolution_x=1000;sc.render.resolution_y=780;sc.render.resolution_percentage=100;sc.world=bpy.data.worlds.new('Day');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.72,.8,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
 light=bpy.data.lights.new('Sun','SUN');light.energy=2.5;light.angle=.15;ob=bpy.data.objects.new('Sun',light);sc.collection.objects.link(ob);ob.rotation_euler=(.5,-.35,-.4)
 camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);sc.collection.objects.link(cam);cam.location=center+Vector((1.0,-1.4,1.1))*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=size*1.35;camdata.clip_end=size*20;camdata.clip_start=max(size/10000,.001);sc.camera=cam
 sc.view_settings.view_transform='AgX';sc.render.filepath=str(R/'previews'/f"{src['id']}_source.png");bpy.ops.render.render(write_still=True)
 inv=[]
 for o in objs:
  pts=[o.matrix_world@Vector(v) for v in o.bound_box];b=[[min(p[k] for p in pts) for k in range(3)],[max(p[k] for p in pts) for k in range(3)]]
  chain=[];p=o
  while p:chain.append(p.name);p=p.parent
  inv.append(dict(name=o.name,chain=chain,bounds=b,verts=len(o.data.vertices),faces=len(o.data.polygons)))
 (R/'audit'/f"{src['id']}_blender.json").write_text(json.dumps(inv,ensure_ascii=False,indent=2));print('SOURCE_DONE',src['id'],flush=True)
