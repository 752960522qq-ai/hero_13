import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];catalog=json.load(open(R/'asset_catalog.json'));out=R/'previews/catalog';out.mkdir(exist_ok=True)
which=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for a in catalog:
 if which and a['asset_id'] not in which:continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'extracted'/a['file']));bpy.context.view_layer.update();obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];pts=[o.matrix_world@Vector(v) for o in obs for v in o.bound_box];lo=Vector([min(v[k] for v in pts) for k in range(3)]);hi=Vector([max(v[k] for v in pts) for k in range(3)]);target=(hi+lo)/2;size=max(hi-lo)
 sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=6;sc.render.use_simplify=True;sc.cycles.texture_limit_render='2048';sc.render.resolution_x=600;sc.render.resolution_y=600;sc.render.resolution_percentage=100
 sc.world=bpy.data.worlds.new('Day');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.75,.8,.86,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
 l=bpy.data.lights.new('Sun','SUN');l.energy=2.5;l.angle=.18;o=bpy.data.objects.new('Sun',l);sc.collection.objects.link(o);o.rotation_euler=(.45,-.3,-.4)
 c=bpy.data.cameras.new('Camera');o=bpy.data.objects.new('Camera',c);sc.collection.objects.link(o);direction=(.8,1.8,.9) if a['asset_id'] in ['S02-B03','S02-B05'] else (1.8,-.8,.9) if a['asset_id'] in ['S06-B04','S06-B05','S06-B06'] else (1.2,-1.6,.9);o.location=target+Vector(direction)*size;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=size*1.32;c.clip_start=.01;c.clip_end=3000;sc.camera=o
 sc.view_settings.view_transform='AgX';sc.render.filepath=str(out/(a['asset_id']+'.png'));bpy.ops.render.render(write_still=True);print('ASSET_RENDER',a['asset_id'],flush=True)
