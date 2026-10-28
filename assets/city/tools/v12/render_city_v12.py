import bpy,sys,json,math,argparse
from pathlib import Path
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--model',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--draft',action='store_true');ap.add_argument('--only');a=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
a.out.mkdir(parents=True,exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(a.model.resolve()/'huizhou_road_network.blend'));sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=6 if a.draft else 24;sc.cycles.use_denoising=True;sc.render.resolution_percentage=35 if a.draft else 100;sc.render.image_settings.file_format='PNG'
sc.world.use_nodes=True;bg=sc.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.55,.68,.8,1);bg.inputs['Strength'].default_value=.8
sun=bpy.data.lights.new('V12_Sun','SUN');sun.energy=3.;sun.angle=.13;o=bpy.data.objects.new(sun.name,sun);sc.collection.objects.link(o);o.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-28));sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.4
views=[('01_rear_new_models',(292,232,48),(295,266,16),110,(1800,1200)),('02_rear_infill',(-22,240,62),(15,279,17),112,(1800,1250)),('03_cbd_overview',(80,150,650),(45,870,43),1120,(1900,1450)),('04_cbd_gateway',(645,312,242),(245,748,48),460,(1800,1250)),('05_city_overview',(1650,-2200,2500),(-120,-200,25),4200,(1900,1450))]
all_views=list(views)
if a.only:views=[v for v in views if v[0] in a.only.split(',')]
for name,loc,target,scale,res in views:
 data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=scale;data.clip_start=.04;data.clip_end=12000;sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.filepath=str(a.out.resolve()/(name+'.png'));bpy.ops.render.render(write_still=True);print('V12_RENDER_DONE',name,flush=True)
(a.out/'render_cameras.json').write_text(json.dumps([{'name':v[0],'location':v[1],'target':v[2],'ortho_scale':v[3],'resolution':v[4]} for v in all_views],indent=2))
