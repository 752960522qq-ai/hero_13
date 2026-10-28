import bpy,sys,json,math,argparse
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--model-dir',type=Path,default=ROOT/'work_v11/model');ap.add_argument('--out',type=Path,default=ROOT/'work_v11/previews');ap.add_argument('--only');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else [])
OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.model_dir.resolve()/'huizhou_road_network.blend'));sc=bpy.context.scene
sc.render.engine='CYCLES';sc.cycles.samples=18;sc.cycles.use_denoising=True;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
sc.world.use_nodes=True;bg=sc.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.55,.68,.8,1);bg.inputs['Strength'].default_value=.8
sun=bpy.data.lights.new('V11_Sun','SUN');sun.energy=3;sun.angle=.13;o=bpy.data.objects.new(sun.name,sun);sc.collection.objects.link(o);o.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-28))
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.4
views=[('01_rear_five_added',(266,230,50),(274,266,16),93,(1900,1250)),('02_alley_eye_level',(244.5,258.9,12.1),(292,263,13.6),None,(1800,1150)),('03_reused_rear_houses',(-22,249,55),(11,279,16),104,(1800,1250)),('04_oldtown_overview',(10,-160,630),(110,285,12),1040,(1900,1400))]
if args.only:views=[v for v in views if v[0] in args.only.split(',')]
for name,loc,target,scale,res in views:
    data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);sc.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.clip_start=.04;data.clip_end=12000
    if scale:data.type='ORTHO';data.ortho_scale=scale
    else:data.lens=27
    sc.camera=cam;sc.render.resolution_x=res[0];sc.render.resolution_y=res[1];sc.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);print('V11_RENDER_DONE',name,flush=True)
(OUT/'render_cameras.json').write_text(json.dumps([{'name':v[0],'location':v[1],'target':v[2],'ortho_scale':v[3],'resolution':v[4]} for v in views],indent=2))
