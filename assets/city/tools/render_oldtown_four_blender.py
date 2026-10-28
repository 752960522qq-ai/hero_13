"""Render the actual four inserted buildings in the city context."""
import bpy,sys,json,math,argparse
from pathlib import Path
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--only');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100;sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.55,.68,.8,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
light=bpy.data.lights.new('Oldtown_Preview_Sun','SUN');light.energy=3.;light.angle=.18;o=bpy.data.objects.new(light.name,light);sc.collection.objects.link(o);o.rotation_euler=(math.radians(24),math.radians(-18),math.radians(145));sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.4
views=[('01_oldtown_context',(230,335,105),(277,251,9),190,(1800,1300)),('02_joined_shopfronts',(310,232.5,17),(310,219,14),63,(1800,740)),('03_backlane_apartments',(230,254,23),(230,270,15),42,(1600,1100))]
record=[]
for name,loc,target,ortho,res in views:
 if a.only and name not in a.only.split(','):continue
 o.rotation_euler.z=math.radians(-28 if name=='03_backlane_apartments' else 145)
 sc.render.use_border=name=='02_joined_shopfronts';sc.render.use_crop_to_border=True;sc.render.border_min_x=0.;sc.render.border_max_x=1.;sc.render.border_min_y=.13 if name=='02_joined_shopfronts' else 0.;sc.render.border_max_y=1.
 data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.clip_start=.08;data.clip_end=10000
 if ortho:data.type='ORTHO';data.ortho_scale=ortho
 else:data.type='PERSP';data.lens=21
 sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.filepath=str((a.out/(name+'.png')).resolve());bpy.ops.render.render(write_still=True);record.append({'name':name,'location':loc,'target':target,'ortho_scale':ortho,'resolution':res});print('OLDTOWN_PREVIEW',name,flush=True)
(a.out/'oldtown_four_cameras.json').write_text(json.dumps([{'name':n,'location':l,'target':t,'ortho_scale':o,'resolution':r} for n,l,t,o,r in views],indent=2))
