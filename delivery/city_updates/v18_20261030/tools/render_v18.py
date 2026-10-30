import os
import bpy,sys,math,json,argparse
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];ap=argparse.ArgumentParser();ap.add_argument('--draft',action='store_true');ap.add_argument('--only');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(R/'model/city_v18.blend'));
# Preview context is read-only and is excluded from the changed district exports.
for context_file in sorted((R/'context').glob('*.glb')):
 bpy.ops.import_scene.gltf(filepath=str(context_file))
bpy.context.view_layer.update()
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=6 if a.draft else 20;sc.cycles.use_denoising=True;sc.render.use_simplify=True;sc.cycles.texture_limit_render='1024';sc.render.resolution_percentage=50 if a.draft else 100;sc.render.image_settings.file_format='PNG';sc.world=bpy.data.worlds.new('Daylight');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.6,.7,.8,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
sun=bpy.data.lights.new('Day_Sun','SUN');sun.energy=3;sun.angle=.13;ob=bpy.data.objects.new('Day_Sun',sun);sc.collection.objects.link(ob);ob.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-28));sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.4
# Context water is preview-only; district deliverables never include it.
mat=bpy.data.materials.new('Preview_Water');mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.12,.32,.4,1);bs.inputs['Roughness'].default_value=.6
bpy.ops.mesh.primitive_plane_add(size=10000,location=(0,0,.0));bpy.context.object.data.materials.append(mat)
views=[('01_oldtown_new_facades_v18',(500,60,220),(165,295,15),480,(1900,1250)),('02_eastern_newtown_v18',(1040,1130,600),(740,740,15),900,(1900,1300)),('03_newtown_public_buildings_v18',(450,1010,230),(680,875,17),350,(1900,1250)),('04_north_island_overview_v18',(1700,-1800,2100),(70,630,20),2350,(2000,1400)),('06_oldtown_shopfronts_v18',(-170,760,480),(175,280,14),270,(1900,1300))]
out=R/('drafts' if a.draft else 'renders');out.mkdir(exist_ok=True)
for name,loc,target,scale,res in views:
 if a.only and name not in a.only.split(','):continue
 c=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,c);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=scale;c.clip_start=.04;c.clip_end=12000;sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
