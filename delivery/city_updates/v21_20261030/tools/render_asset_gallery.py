from pathlib import Path
import sys,json,math
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deps311'))
import bpy,numpy as np
from mathutils import Vector
cat=json.load(open(R/'asset_catalog.json'));out=R/'renders/assets';out.mkdir(parents=True,exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for a in cat:
 if args and a['source_id'] not in args:continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'extracted'/a['file']));bpy.context.view_layer.update();sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=8;sc.cycles.use_denoising=True;sc.render.threads_mode='FIXED';sc.render.threads=6;sc.render.resolution_x=520;sc.render.resolution_y=520;sc.render.resolution_percentage=100;sc.render.film_transparent=False;sc.render.use_simplify=True;sc.cycles.texture_limit_render='2048';sc.world=bpy.data.worlds.new('Day');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.77,.82,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.85
 ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.8;ld.angle=.17;ob=bpy.data.objects.new('Sun',ld);sc.collection.objects.link(ob);ob.rotation_euler=(.4,-.3,-.5)
 sz=np.array(a['normalized_size_m']);s=float(max(sz));c=Vector((0,0,sz[2]*.48));n=np.array(a['source_front']);t=np.array([-n[1],n[0]]);xy=(n*.95+t*.7)*s;cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);sc.collection.objects.link(cam);cd.type='ORTHO';cd.ortho_scale=max(s*1.5,np.linalg.norm(sz[:2])*1.15);cd.clip_end=2000;cam.location=c+Vector((*xy,s*.55));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();sc.camera=cam;sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.render.filepath=str(out/(a['asset_id']+'.png'));bpy.ops.render.render(write_still=True);print('ASSET_RENDERED',a['asset_id'],flush=True)
print('ASSET_GALLERY_READY',flush=True)
